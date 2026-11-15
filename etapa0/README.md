# Etapa 0 — Ambiente local com Floci e Ollama

**Entrega:** print do `converse` respondendo e do `docker compose ps` com os dois serviços ativos.

| Print | O que mostra |
|---|---|
| [`etapa0-compose-ps.png`](../evidencias/etapa0-compose-ps.png) | `cloud-floci-1` (healthy) e `cloud-ollama-1` ativos; `aws sts get-caller-identity` → conta `000000000000` |
| [`etapa0-converse.png`](../evidencias/etapa0-converse.png) | `aws s3 mb` + `bedrock-runtime converse` com `model-id` do Claude 3 Haiku respondido pelo qwen2.5:7b local (`stopReason: end_turn`, `usage`, `latencyMs`) |

## O que foi montado (raiz do repositório)

| Item | Onde | Diferença em relação ao roteiro e por quê |
|---|---|---|
| Floci + Ollama | [`docker-compose.yml`](../docker-compose.yml) | Portas só em `127.0.0.1` (não expõe a AWS emulada na rede da faculdade); Ollama publicado na **11435** porque a 11434 já era usada por um Ollama instalado no sistema |
| Modelo | `qwen2.5:7b` | Mais preciso que o `llama3.2` sugerido (ver diário); trocável com `MODELO=…` |
| Timeout do proxy | `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_REQUEST_TIMEOUT_SECONDS: 300` | O padrão de 60 s corta respostas longas (Etapa 3) |
| Estado persistente | `FLOCI_STORAGE_MODE: persistent` | Sem isso, religar o Floci para ativar o IAM apaga todos os recursos |
| IAM | `FLOCI_SERVICES_IAM_ENFORCEMENT_ENABLED: ${IAM_ENFORCEMENT:-false}` | Liga com `IAM_ENFORCEMENT=true docker compose up -d` (Etapas 2, 5 e 6) |
| GPU (opcional) | [`compose.gpu.yml`](../compose.gpu.yml) | Só com placa NVIDIA + nvidia-container-toolkit; fora disso o compose padrão roda em CPU |
| Variáveis AWS | [`env.sh`](../env.sh) (`source env.sh`) | Equivale ao perfil `floci` do roteiro, mas vale só no terminal atual e isola `~/.aws` real (`AWS_CONFIG_FILE` e `AWS_SHARED_CREDENTIALS_FILE` apontam para a pasta `tools/`) |
| AWS CLI v2, Python 3.12 + boto3 + cfn-lint + mcp, uv | `tools/`, `.venv/` | Instalados dentro da pasta do projeto: apagar a pasta remove tudo |

## Desempenho medido (notebook com GTX 1650 4 GB, 16 GB RAM)

| Modelo | Só CPU | Com GPU | Onde roda |
|---|---|---|---|
| llama3.2 (3B) | 19 tokens/s | 42 tokens/s | 100 % GPU |
| qwen2.5:3b | 20 tokens/s | 42 tokens/s | 100 % GPU |
| qwen2.5:7b | 9 tokens/s | ~14 tokens/s | 80 % GPU / 20 % CPU (não cabe nos 4 GB) |

Medido com `docker compose exec ollama ollama run <modelo> --verbose "…"` (linha `eval rate`).

## Floci × AWS real nos serviços deste roteiro

Ver o mapa da [Etapa 1](../etapa1/README.md#mapa-papéis-da-ia--serviços--o-que-o-floci-emula), com o que foi observado em cada etapa.

## Diário de prompts

| Pedido | Resposta | Erro encontrado | Correção |
|---|---|---|---|
| `converse`: "Em uma frase: o que é IaaS?" com **llama3.2** | Começou com "**PaaS** é um acrônimo que significa Platform as a Service…" e só depois falou de IaaS | Fugiu da pergunta, falou de outro modelo de serviço | Troca para **qwen2.5:7b**, que respondeu direto: "IaaS significa Infraestrutura como Serviço…" |
| (assistente) subir o compose do roteiro | Porta 11434 ocupada | Já havia um Ollama do sistema escutando nela | Ollama do compose na 11435; o Floci fala com ele pela rede interna (`ollama:11434`) |
| (assistente) religar o Floci com IAM ligado | Recursos criados antes sumiram | Floci guarda estado só em memória por padrão | `FLOCI_STORAGE_MODE: persistent` |
| (assistente) GPU no container | `ollama ps` mostrava `100% CPU` | Faltava o nvidia-container-toolkit | Toolkit instalado + `compose.gpu.yml` opcional |
