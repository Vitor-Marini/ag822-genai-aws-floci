#!/usr/bin/env bash
# Aplica a política só-leitura ao tecnico-campo, cria uma chave e testa o que passa e o que falha.
# Requer: IAM_ENFORCEMENT=true docker compose up -d
set -uo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
cd "$(dirname "$0")"
aws iam put-user-policy --user-name tecnico-campo --policy-name leitura-relatorios --policy-document file://politica-leitura.json
read -r AK SK < <(aws iam create-access-key --user-name tecnico-campo --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
tec() { AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK aws "$@"; }
sleep 2
echo "## get-object relatorios/inspecao-001.txt (deve PASSAR)";  tec s3 cp s3://relatorios/inspecao-001.txt - 2>&1
echo "## list relatorios (deve PASSAR)";                         tec s3 ls s3://relatorios/ 2>&1
echo "## put-object relatorios (deve FALHAR)";                   echo x | tec s3 cp - s3://relatorios/hack.txt 2>&1 | tail -1
echo "## delete-object relatorios (deve FALHAR)";                tec s3 rm s3://relatorios/inspecao-001.txt 2>&1 | tail -1
echo "## list imagens-drone (deve FALHAR)";                      tec s3 ls s3://imagens-drone/ 2>&1 | tail -1
aws iam delete-access-key --user-name tecnico-campo --access-key-id "$AK"   # chave descartável
