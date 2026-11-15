# Etapa 4 — Bedrock em automação orientada a eventos

**Entrega:** fluxo S3 → Lambda → Bedrock → DynamoDB funcionando.

```
relatorio.txt ──► S3 relatorios-campo ──(ObjectCreated)──► Lambda triagem ──► Bedrock (Floci) ──► Ollama qwen2.5:7b
                                                                │
                                                                └──► DynamoDB triagem {arquivo, resumo, urgencia, tentativas, tokens_in, tokens_out}
```

## Como rodar

```bash
source ../env.sh
./deploy.sh                                       # bucket, tabela, role, função, notificação (só na 1ª vez; para refazer, comece do zero — ver README principal)
for f in relatorios/*.txt; do aws s3 cp $f s3://relatorios-campo/; done
aws dynamodb scan --table-name triagem            # ~20 s por relatório
aws logs tail /aws/lambda/triagem                 # se algo falhar
python test_app.py                                # testes do tratamento de JSON inválido (sem Floci)
```

## Resultado

| Arquivo | Conteúdo | Esperado | Obtido (v1, prompt do roteiro) | Obtido (v2, com critérios) |
|---|---|---|---|---|
| relatorio1.txt | soja sem pragas | baixa | baixa | baixa |
| relatorio2.txt | lagarta em 12%, reavaliar em 5 dias | media | **baixa** ✗ | media ✓ |
| relatorio3.txt | ferrugem em 60% + pivô vazando | alta | alta | alta |

Tokens medidos (v2) em [`resultados.tsv`](resultados.tsv): média de **232 de entrada / 34 de saída** por relatório (usados na Etapa 6).

Evidências: [`scan`](../evidencias/etapa4-dynamodb-scan.png), [`scan v1`](../evidencias/etapa4-dynamodb-scan-v1-sem-criterios.png),
[`testes`](../evidencias/etapa4-teste-json-invalido.png).

## O que mudou em relação ao `app.py` do roteiro

1. **JSON inválido (desafio extra):** remove cercas ```` ```json ````, valida `urgencia ∈ {baixa, media, alta}`, tenta de novo uma vez e, se falhar de novo, grava `urgencia = revisao_humana` com o texto bruto, em vez de derrubar a Lambda com `JSONDecodeError`. Coberto por `test_app.py`.
2. **Critérios de urgência no prompt de sistema:** sem eles o modelo classificou um problema presente (lagarta abaixo do nível de controle) como `baixa`.
3. **Relatório delimitado por `<relatorio>` e instrução de tratá-lo como dado:** defesa contra injeção de prompt, testada na Etapa 6.
4. **Coluna `tentativas`:** mostra quantas chamadas cada item precisou.
5. **Filtro de injeção (`limpar()`, Etapa 6):** linhas que tentam dar ordens ao sistema são removidas antes do modelo e o item ganha `suspeita_injecao: true`.
6. **Role com política mínima:** `deploy.sh` aplica [`etapa6/politica-lambda-triagem.json`](../etapa6/politica-lambda-triagem.json), necessária com o IAM ligado.

## Diário de prompts

| Prompt / pedido | Resposta da IA | Erro encontrado | Correção |
|---|---|---|---|
| Prompt de sistema do roteiro: "Responda só em JSON: {resumo, urgencia: baixa\|media\|alta}" + relatório 2 | `{"urgencia": "baixa", "resumo": "Nível baixo de infestação de lagarta…"}` | Confundiu "abaixo do nível de controle" com "sem urgência"; o técnico pediu reavaliação em 5 dias → `media` | Critérios explícitos para cada nível no prompt de sistema; relatório 2 passou a `media` sem afetar os outros dois |
| (assistente) transcrever o `app.py` e os comandos do PDF | Código copiado do texto extraído do PDF | O PDF quebrou linhas no meio de strings (`"2012-10-\n17"`, ARN `us-east-\n1`, comentário `# … modelo\nlocal`) → erro de sintaxe e JSON inválido | Linhas reunidas à mão e `app.py` validado com `ast.parse` antes do deploy |
| (assistente) `deploy.sh` rodado pela segunda vez | `zip` atualizou o `funcao.zip` existente | Risco de empacotar arquivos velhos junto | `rm -f funcao.zip` antes do `zip` |

## Na AWS real

O mesmo `app.py` roda sem mudança; muda o `modelId` (um modelo habilitado na conta), a role (com `bedrock:InvokeModel` restrito ao ARN do modelo, `s3:GetObject` no bucket e `dynamodb:PutItem` na tabela) e cada token custa dinheiro (Etapa 6).
