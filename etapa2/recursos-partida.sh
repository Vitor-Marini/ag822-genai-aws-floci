#!/usr/bin/env bash
# Recursos de partida da Etapa 2 (comandos do roteiro).
set -euo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci. Abortando."; exit 1; }
aws s3 mb s3://relatorios
aws s3 mb s3://imagens-drone
echo "Inspeção talhão 12: sem pragas" | aws s3 cp - s3://relatorios/inspecao-001.txt
aws dynamodb create-table --table-name sensores \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null
aws iam create-user --user-name tecnico-campo >/dev/null
aws s3 ls
aws dynamodb list-tables
aws iam list-users --query 'Users[].UserName'
