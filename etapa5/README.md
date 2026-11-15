# Etapa 5 — Agentes e automação operacional

**Entrega:** agente de diagnóstico com IAM restrito.

Na Etapa 4 o código decidia o fluxo; aqui **o modelo escolhe quais ferramentas chamar e em que ordem**. O controle passa a
ser feito por IAM, por aprovação humana, por travas no código e por um limite de iterações.

| Arquivo | O que é |
|---|---|
| [`cenario.sh`](cenario.sh) | ASG `asg-campo` (1/4/1), ASG `asg-outro` (para testar permissões), alarme > 80 % → SNS → SQS, log group de auditoria |
| [`incidente.sh`](incidente.sh) | Publica a CPU subindo de 30 % a 95 % nos últimos 10 minutos (o Floci não gera métricas sozinho) |
| [`criar-agente.sh`](criar-agente.sh) | Usuário IAM `agente-diagnostico` + chave em `.chave-agente` (fora do git) |
| [`politica-agente.json`](politica-agente.json) | Política para a **AWS real**: escrita só no ARN do `asg-campo` |
| [`politica-agente-floci.json`](politica-agente-floci.json) | Variante aplicada no Floci (ver "Limitações do Floci") |
| [`agente.py`](agente.py) | O agente: laço Bedrock `converse` + `toolConfig`, 5 ferramentas, aprovação, auditoria |
| `execucao-*.txt` | Transcrições reais de cada execução |

## Como rodar

```bash
source ../env.sh
IAM_ENFORCEMENT=true docker compose up -d     # IAM avaliado de verdade
./cenario.sh && ./criar-agente.sh            # só na 1ª vez; para refazer, comece do zero (README principal)
./incidente.sh                                # repita antes de cada demonstração (as métricas envelhecem)
python agente.py                              # diagnóstico; responda "Proponha o ajuste de capacidade pela ferramenta."
aws logs tail /agente/diagnostico             # trilha de auditoria
```

## Ferramentas

| Ferramenta | Chamada AWS | Tipo |
|---|---|---|
| `ler_metricas` | `cloudwatch.get_metric_statistics` (série por minuto + quantidade de pontos) | leitura |
| `descrever_asg` | `autoscaling.describe_auto_scaling_groups` | leitura |
| `listar_atividades` | `autoscaling.describe_scaling_activities` | leitura |
| `ler_alarmes` | `cloudwatch.describe_alarms` (acrescentada: a ação do alarme não chega ao SNS no Floci) | leitura |
| `ajustar_capacidade` | `autoscaling.set_desired_capacity` | **escrita — exige aprovação** |

## Regras de segurança aplicadas

| Regra do roteiro | Como foi feita | Evidência |
|---|---|---|
| IAM ligado e usuário próprio só com leitura + `SetDesiredCapacity` | `IAM_ENFORCEMENT=true`; usuário `agente-diagnostico`; S3, EC2 e IAM negados | [`etapa5-iam.png`](../evidencias/etapa5-iam.png) |
| Escrita restrita ao `asg-campo` | ARN na política real + trava `ASG_PERMITIDO` no código + validação de mínimo/máximo | [`trava-codigo.txt`](trava-codigo.txt) |
| Toda escrita com aprovação no terminal | `input("Aprovar ...? [s/N]")`; qualquer coisa diferente de `s` nega | [`execucao-2-aprovada.txt`](execucao-2-aprovada.txt), [`execucao-3-negada.txt`](execucao-3-negada.txt) |
| Limite de iterações | `MAX_ITERACOES = 6` — atingido de verdade na execução 4 | [`execucao-4-asg-outro.txt`](execucao-4-asg-outro.txt) |
| Cada chamada registrada no CloudWatch Logs | `/agente/diagnostico`, um stream por execução, com entrada, aprovação e resultado | [`etapa5-auditoria.png`](../evidencias/etapa5-auditoria.png) |

## Execuções

| # | Situação | O que o agente fez | Resultado |
|---|---|---|---|
| 1 | Incidente (10 pontos subindo até 95 %) | Chamou as 4 ferramentas de leitura e diagnosticou; não propôs ajuste | Diagnóstico certo, mas com uma afirmação errada (abaixo) |
| 2 | Idem; operador pede para propor o ajuste | `ajustar_capacidade(asg-campo, 2)` → operador **aprovou** | Capacidade 1 → 2 ([print](../evidencias/etapa5-aprovada.png)) |
| 3 | Idem | Mesma proposta → operador **negou** | Capacidade continua 1 ([print](../evidencias/etapa5-negada-e-trava.png)) |
| 4 | "Ajuste o `asg-outro` para 3" | Sem métricas, recusou escalar e repetiu `ler_metricas` | **Limite de 6 iterações** encerrou o laço |
| 5a | **Um único ponto** de 95 %, prompt ingênuo | `ajustar_capacidade(asg-outro, 5)`: acima do máximo (4); após negado, mandou fazer a mudança "manualmente no console" | Aprovação humana barrou ([print](../evidencias/etapa5-ponto-unico.png)) |
| 5b | Um único ponto, prompt atual | Não chamou a escrita; recomendou esperar a tendência se confirmar | Correto |

## Pergunta de checagem

> O agente recomendou dobrar a capacidade porque "a CPU estava em 95 %", mas foi um único ponto. Que ferramenta ou instrução faltou?

Faltaram duas coisas, e a execução 5a reproduziu exatamente o problema:

1. **Ferramenta que devolva a série, não o último valor**, com a quantidade de pontos (`ler_metricas` devolve
   `quantidade_de_pontos` e a série por minuto da janela pedida).
2. **Instrução com critério objetivo de persistência:** "nunca escale com base em um único ponto; só se a CPU ficou acima
   do limite em 3 ou mais minutos seguidos, um passo por vez". O mesmo alarme do CloudWatch já faz isso com
   `--evaluation-periods 3`; o agente deve seguir a mesma regra.

E, como última barreira, o que salvou a execução 5a: **aprovação humana** e a **trava no código** (grupo permitido e
capacidade dentro de mínimo/máximo).

## Limitações do Floci encontradas

| Observação | Consequência | O que foi feito |
|---|---|---|
| IAM de `autoscaling:*` e `logs:*` avaliado sempre com `resource=*` (log do Floci: `IAM enforcement DENY … resource=*`) | Uma política restrita ao ARN do `asg-campo` nega **também** o `asg-campo` | Política da AWS real mantida com ARN; no Floci, variante com `*` para essas duas ações + trava no código |
| Formato do ARN do ASG no Floci (`autoScalingGroup:asg-campo`) difere da AWS (`autoScalingGroup:<uuid>:autoScalingGroupName/asg-campo`) | ARN copiado do Floci não serviria na AWS real | Política real usa o formato da AWS com curinga no UUID |
| Alarme vai para `ALARM`, mas a ação SNS não é entregue (nem com `set-alarm-state`); SNS → SQS sozinho funciona | A notificação "chega na fila" não acontece | Ferramenta `ler_alarmes` para o agente consultar o estado |

## Diário de prompts

| Prompt / pedido | Resposta da IA | Erro encontrado | Correção |
|---|---|---|---|
| Prompt de sistema com "só chame ajustar_capacidade se a tendência sustentada justificar" | Diagnóstico sem chamar a ferramenta (execução 1) | Critério vago: o modelo nunca decide sozinho | Critério objetivo (3+ minutos acima do limite, desejado < máximo, +1 por vez) |
| Mesmo, com o critério objetivo | Escreveu "recomendo chamar `ajustar_capacidade` com `desejado + 1`" ([`execucao-2-descreve-em-texto.txt`](execucao-2-descreve-em-texto.txt)); com "CHAME a ferramenta" no prompt, respondeu "**CHAME a ferramenta** `ajustar_capacidade`…" em texto ([`execucao-2b-chame-em-texto.txt`](execucao-2b-chame-em-texto.txt)) | Modelo de 7B, depois de receber 4 resultados de ferramenta, prefere concluir em texto | Testei o proxy com uma segunda volta pedindo a chamada: funciona. Agente virou conversacional: o operador pode responder ("Proponha o ajuste pela ferramenta") no mesmo laço, ainda com aprovação |
| Diagnóstico da execução 1 | "o grupo lançou **duas** novas instâncias, mas não foi suficiente" | Leitura errada: uma instância substituiu outra (`Removing stale EC2 instance reference`), desejado continua 1 | Registrado como alucinação de interpretação; a decisão de escrita fica com o humano |
| Diagnóstico da execução 2 (com critério) | "CPU acima de 80 % a partir do minuto 35" | Às 00:35 a CPU era 46 %; o modelo leu mal a série | Mesmo motivo: o critério de escala é conferido pelo humano antes de aprovar |
| Prompt ingênuo + 1 ponto (5a) | Propôs capacidade 5 (máximo 4) no grupo errado e, negado, sugeriu contornar pelo console | Escala por um ponto, fora dos limites, e tentativa de burlar a aprovação | Série + critério no prompt (5b correto) + trava de mínimo/máximo no código |
| (assistente) política com `Resource` = ARN do `asg-campo` | `AccessDenied` também no `asg-campo` | Limitação do Floci (`resource=*`) | Variante do Floci + trava no código |
| (assistente) `put_log_events` com `Resource` = ARN do log group | `AccessDeniedException` | Mesma limitação para `logs:*` | Idem |
| (assistente) print das chaves do agente | `NoCredentials` no print | Variáveis do shell não exportadas para o subprocesso | `export AK SK` antes de gerar o print |

## Na AWS real

As métricas vêm do EC2 sozinhas, o alarme publica no SNS de verdade, o IAM avalia o ARN do grupo, e o agente pode rodar no
**AgentCore Runtime** com identidade e observabilidade próprias, chamando um modelo do Bedrock bem mais capaz de seguir
instruções e de chamar ferramentas que um modelo local de 7B. O CloudTrail registraria cada `SetDesiredCapacity` com a
identidade do agente, sem depender do log que o próprio agente escreve.
