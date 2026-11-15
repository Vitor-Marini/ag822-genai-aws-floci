# Etapa 2 — Assistentes de IA para operar a AWS

**Entrega:** diário de prompts com correções.

## Preparação

| Passo do roteiro | Como foi feito |
|---|---|
| Terminal do assistente herda o Floci | `source env.sh` (equivale ao perfil `floci` do roteiro); `aws sts get-caller-identity` → conta `000000000000` ([print](../evidencias/etapa0-compose-ps.png)) |
| Cliente de IA com MCP | um **assistente de IA de linha de comando** que opera o terminal; **qwen2.5:7b** (via Bedrock do Floci) como o modelo cujas respostas são auditadas |
| Servidor de documentação sem credenciais | **AWS Documentation MCP Server** (`uvx awslabs.aws-documentation-mcp-server@latest`), conectado por um cliente MCP stdio em Python ([`consulta_mcp.py`](consulta_mcp.py)): o mesmo protocolo que Kiro e VS Code usam |
| Recursos para o assistente encontrar | [`recursos-partida.sh`](recursos-partida.sh): buckets `relatorios` e `imagens-drone`, tabela `sensores`, usuário `tecnico-campo` |
| Aprovação antes de escrita | [`.claude/settings.json`](../.claude/settings.json) faz o assistente **pedir aprovação** antes de `delete`, `rm`, `rb`, `terminate`, `--force`, `aws iam`, `set-desired-capacity`, `cloudformation deploy/delete-stack` e dos scripts de deploy/destruição (vale em qualquer modo de permissão que pergunte); além disso, todo script de escrita aborta se a conta não for `000000000000` |

Para usar no **VS Code (Copilot, modo Agent)** ou no **Kiro**, a configuração do roteiro funciona sem mudança; os
servidores que acessam recursos precisam de `AWS_ENDPOINT_URL=http://localhost:4566` e das credenciais `test` no bloco `env`.

## Atividade 1 — Consulta guiada por documentação (com e sem MCP)

Mesmo modelo (qwen2.5:7b), mesma pergunta, temperatura 0. A versão "com MCP" recebe os trechos que o servidor de
documentação devolveu (`search_documentation` → `read_documentation` da página
[Compare security groups and network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html)).

```bash
python consulta_mcp.py      # gera sem-mcp.txt, com-mcp.txt e contexto-mcp.txt
```

| Fato | Correto (documentação AWS) | Sem MCP ([`sem-mcp.txt`](sem-mcp.txt)) | Com MCP ([`com-mcp.txt`](com-mcp.txt)) |
|---|---|---|---|
| Nível | SG: instância · NACL: sub-rede | ✓ | ✓ |
| Estado | SG stateful · NACL stateless | ✓ | ✓ |
| Tipos de regra | SG **só allow** · NACL allow e deny | ✗ disse que SG tem deny | ✓ |
| Avaliação | SG avalia **todas** · NACL em ordem crescente de número até a 1ª correspondência | ✗ "ordem de prioridade, allow antes de deny" para os dois | ✓ |
| SGs por interface | **5** por padrão, até 16 | ✗ "até 50" | não citou |
| NACLs por sub-rede | **uma** NACL por sub-rede (uma NACL pode atender várias sub-redes) | ✗ "até 10" | ✗ "uma ou mais" |
| Link citado | página de comparação da VPC | ✗ link de NAT Gateway para NACL | ✓ |

**6 erros sem MCP → 1 erro com MCP.** O erro que sobrou é de um fato que **não estava** no trecho recuperado (a página de
comparação não diz quantas NACLs uma sub-rede aceita): o modelo completou de memória. Conferi os dois números na
documentação pelo próprio servidor MCP ([`verificacao-fatos.txt`](verificacao-fatos.txt)): "a subnet can be associated
with only one network ACL at a time" e "Security groups per network interface: 5 (up to 16)".
Evidência: [`etapa2-mcp.png`](../evidencias/etapa2-mcp.png).

## Atividade 2 — Inventário

A IA recebeu o pedido **sem mencionar o Floci** ([`prompt-inventario.txt`](prompt-inventario.txt)) e gerou
[`inventario.original.sh`](inventario.original.sh).

- **Usou `--endpoint-url`?** Não. **Usou a variável de ambiente?** Só implicitamente: o script depende de quem o executa.
- **O que aconteceria numa máquina com credenciais reais** (ex.: AWS Academy em `~/.aws/credentials`) e sem o `env.sh`:
  o script listaria os buckets, tabelas e usuários **da conta real**. Aqui é só leitura, mas o mesmo descuido num script
  com `delete`/`terminate` apagaria recursos reais.
- **Correção** ([`inventario.sh`](inventario.sh)): confere a conta com `sts get-caller-identity` e aborta se não for
  `000000000000`; mostra o endpoint em uso; `set -euo pipefail`. Evidência:
  [`etapa2-inventario.png`](../evidencias/etapa2-inventario.png) (segunda execução, sem as variáveis, aborta).

## Atividade 3 — Menor privilégio de verdade (IAM ligado)

```bash
IAM_ENFORCEMENT=true docker compose up -d
./teste-menor-privilegio.sh
```

A IA gerou [`politica-leitura.original.json`](politica-leitura.original.json); a versão revisada é
[`politica-leitura.json`](politica-leitura.json).

| Teste com a chave do `tecnico-campo` | Esperado | Obtido |
|---|---|---|
| `get-object relatorios/inspecao-001.txt` | passa | ✓ "Inspeção talhão 12: sem pragas" |
| `ls s3://relatorios/` | passa | ✓ |
| `put-object relatorios/hack.txt` | falha | ✓ `AccessDenied … s3:PutObject` |
| `rm relatorios/inspecao-001.txt` | falha | ✓ `AccessDenied … s3:DeleteObject` |
| `ls s3://imagens-drone/` | falha | ✓ `AccessDenied … s3:ListBucket` |

Evidência: [`etapa2-menor-privilegio.png`](../evidencias/etapa2-menor-privilegio.png). A chave criada para o teste é
apagada no fim do script (nenhuma credencial fica no repositório).

## Diário de prompts

| Atividade | Prompt | Resposta da IA | Erro encontrado | Correção |
|---|---|---|---|---|
| Consulta sem MCP | "Explique a diferença entre Security Group e NACL… cite as páginas" | [`sem-mcp.txt`](sem-mcp.txt) | 6 fatos errados (deny em SG, ordem de avaliação, limites 50 e 10, link de NAT Gateway) | Mesma pergunta com documentação via MCP |
| Consulta com MCP | Mesma + `<documentacao>` com a página de comparação | [`com-mcp.txt`](com-mcp.txt) | "Uma sub-rede pode ter um ou mais ACLs" (fato fora do trecho recuperado) | Conferido em `vpc-network-acls.html`: uma NACL por sub-rede |
| Inventário | [`prompt-inventario.txt`](prompt-inventario.txt) | [`inventario.original.sh`](inventario.original.sh) | Sem endpoint e sem conferir a conta; veio em markdown com instruções | [`inventario.sh`](inventario.sh) com trava de conta |
| Política só-leitura | [`prompt-politica.txt`](prompt-politica.txt) | [`politica-leitura.original.json`](politica-leitura.original.json) | `GetObject` e `ListBucket` misturados nos dois ARNs (cada ação só vale num deles); markdown em volta do JSON | Duas instruções, uma por ARN; testada com IAM ligado |
| (assistente) leitura do roteiro | Abrir o `.docx` do roteiro pelo nome exato | `No such file or directory` | O nome do arquivo usa caracteres Unicode diferentes do digitado | Abertura por curinga |
| (assistente) Etapa 0, primeira tentativa | `docker rm -f $(docker ps -aq --filter label=floci=true)` | `'docker rm' requires at least 1 argument` | O Floci já remove o container da Lambda ao apagar a função; a lista veio vazia | Passo desnecessário removido |
| (assistente) Etapa 0, Floci reiniciado | Bucket de teste criado antes de ligar o IAM | Bucket sumiu após o restart | Floci guarda estado só em memória por padrão | `FLOCI_STORAGE_MODE: persistent` no compose |

## Na AWS real

O caminho recomendado é o **AWS MCP Server do Agent Toolkit for AWS** (`aws configure agent-toolkit`, AWS CLI 2.35.0+),
que registra cada ação do agente no CloudTrail e usa permissões IAM. **Não foi executado aqui** porque opera uma conta real.
