# Etapa 3 — Infraestrutura como código gerada por IA

**Entrega:** template final, lista de problemas do template original da IA e o que mudou em cada um.

| Arquivo | O que é |
|---|---|
| [`especificacao.txt`](especificacao.txt) | Especificação em português (8 linhas), enviada como prompt |
| [`vpc.original.yaml`](vpc.original.yaml) | Resposta da IA **sem nenhuma edição** (qwen2.5:7b via `bedrock-runtime converse` do Floci, temperatura 0, 75 s) |
| [`vpc.yaml`](vpc.yaml) | Template revisado; cada correção está marcada no código com `# Pn` |

```bash
source ../env.sh
cfn-lint vpc.yaml                                                  # 0 erros, 0 avisos
aws cloudformation deploy --template-file vpc.yaml --stack-name lab-ia
aws cloudformation describe-stack-resources --stack-name lab-ia
aws ec2 describe-instances --filters Name=tag:Name,Values=lab-ia-web
aws cloudformation delete-stack --stack-name lab-ia
```

Evidências: [`deploy do revisado`](../evidencias/etapa3-deploy.png), [`cfn-lint do original + Floci aceitando`](../evidencias/etapa3-floci-aceita-original.png).

## Problemas encontrados no template da IA

| # | Problema | Como foi achado | Gravidade na AWS real | Correção |
|---|---|---|---|---|
| P1 | Resposta embrulhada em ```` ```yaml ```` apesar de "responda só com o YAML" | `cfn-lint` → `E0000 found character that cannot start any token` | Arquivo nem é YAML válido | Cercas removidas |
| P2 | Faltam propriedades obrigatórias: `GroupDescription` no Security Group e `DeviceIndex` na interface de rede | `cfn-lint` → `E3003` (2×) | **Stack falha** | Propriedades adicionadas |
| P3 | AMI fixa `ami-0c55b1c9cc9cbaf3b` | Checklist (AMI fixa?) | ID inventado ou de outra região → falha ou SO desatualizado | Parâmetro SSM público do Amazon Linux 2023 |
| P4 | Só tag `Name`; nenhuma tag de custo | Checklist (tags de custo?) | Custo não rastreável por projeto (Unidade II) | Parâmetro `Projeto` aplicado como tag em todos os recursos |
| P5 | `PublicRoute` e a instância sem `DependsOn` do `VPCGatewayAttachment` | Revisão manual | Corrida: rota/IP público criados antes do IGW anexado → falha intermitente | `DependsOn: VPCGatewayAttachment` |
| P6 | AZ fixa `us-east-1a` | `cfn-lint` → `W3010` | Quebra em outra região/conta onde a AZ não existe | `!Select [0, !GetAZs ""]` |
| P7 | `Fn::Sub` sem variáveis no UserData | `cfn-lint` → `W1020` | Inofensivo, mas confuso | `Fn::Base64` direto; `yum update -y` (lento, pode reiniciar serviços) removido, `dnf` do AL2023 |
| P8 | Bucket `relatorios-campo-lab` sem criptografia, sem bloqueio de acesso público, nome fixo | Revisão manual | Nome é global → colisão; risco de exposição | Sufixo `${AWS::AccountId}`, `PublicAccessBlockConfiguration`, SSE-AES256 |
| P9 | Instância sem IMDSv2 | Revisão manual | Metadados acessíveis por SSRF | `MetadataOptions.HttpTokens: required` |

Itens do checklist que a IA **acertou**: nenhuma porta além da 80 aberta (sem SSH 22), Outputs úteis (IP, bucket, ARN), nenhuma propriedade ou serviço inventado.

## Template ou emulador?

| Observação no Floci | Causa |
|---|---|
| O template **original**, com os 2 erros `E3003`, foi implantado com os 12 recursos em `CREATE_COMPLETE` | Limitação do emulador: o Floci não valida propriedades obrigatórias |
| `ImageId` da instância aparece como o texto `/aws/service/ami-amazon-linux-latest/...` | Limitação do emulador: não resolve parâmetros `AWS::SSM::Parameter::Value` |
| `HttpTokens` aparece `optional` apesar de `required` | Limitação do emulador: `MetadataOptions` ignorado |
| IP público `172.31.32.11`, fora de `10.0.1.0/24` | Limitação do emulador: endereçamento de instâncias emulado |

Nenhum recurso falhou por erro do template revisado.

## Pergunta de checagem

> Um template que implanta sem erro no Floci está pronto para a AWS real?

**Não.** Este próprio exercício provou: o Floci implantou um template com duas propriedades obrigatórias faltando. Coisas que só a AWS verificaria:

1. **Validação de esquema e existência de recursos:** propriedades obrigatórias (`GroupDescription`), se a AMI existe na região, se a AZ existe na conta.
2. **Cotas e permissões:** limite de VPCs/EIPs por região, se a role de quem implanta tem `ec2:RunInstances`, `iam:PassRole` etc.
3. **Custo:** a `t3.micro` e o bucket começam a cobrar assim que criados; o Floci não cobra nada.

Por isso, na AWS real: `aws cloudformation validate-template`, change set revisado antes do `deploy`, e apagar a stack ao fim do laboratório.

## Diário de prompts

| Prompt / pedido | Resposta da IA | Erro encontrado | Correção |
|---|---|---|---|
| [`especificacao.txt`](especificacao.txt) para o qwen2.5:7b | [`vpc.original.yaml`](vpc.original.yaml), 12 recursos | P1–P9 acima (2 erros que derrubariam a stack na AWS) | [`vpc.yaml`](vpc.yaml), lint limpo |
| (assistente) `scripts/pergunta.py` chamando o converse | `ModelTimeoutException: Proxy backend timed out` após 60 s | O proxy do Floci corta em 60 s; o 7b leva ~75 s para um template inteiro | Achei a chave `floci.services.bedrock-runtime.proxy.request-timeout-seconds` no binário do Floci e defini `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_REQUEST_TIMEOUT_SECONDS=300` no compose |
| (assistente) mesma chamada, de novo | `ReadTimeoutError (read timeout=60)` após 5 min | O boto3 também espera só 60 s e **repete a chamada** (5 tentativas em ~5 min), gerando o template várias vezes à toa | `Config(read_timeout=300, retries={"max_attempts": 1})` |
