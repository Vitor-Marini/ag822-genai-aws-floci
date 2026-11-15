#!/usr/bin/env bash
# Inventário de S3, DynamoDB e IAM — revisado a partir de inventario.original.sh (gerado pela IA).
set -euo pipefail
# A IA não usou --endpoint-url nem conferiu a conta: sem o env.sh carregado, rodaria na conta real.
CONTA=$(aws sts get-caller-identity --query Account --output text)
[ "$CONTA" = "000000000000" ] || { echo "Conta $CONTA não é o Floci (000000000000). Abortando."; exit 1; }
echo "Endpoint: ${AWS_ENDPOINT_URL:-<nenhum>}   Conta: $CONTA"
echo; echo "== Buckets S3 =="
aws s3api list-buckets --query "Buckets[].Name" --output text | tr '\t' '\n'
echo; echo "== Tabelas DynamoDB =="
aws dynamodb list-tables --query "TableNames" --output text | tr '\t' '\n'
echo; echo "== Usuários IAM =="
aws iam list-users --query "Users[].UserName" --output text | tr '\t' '\n'
