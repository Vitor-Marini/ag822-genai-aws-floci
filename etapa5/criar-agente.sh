#!/usr/bin/env bash
# Cria o usuário IAM do agente com a política do Floci e grava a chave em .chave-agente (fora do git).
set -euo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
cd "$(dirname "$0")"
aws iam create-user --user-name agente-diagnostico >/dev/null
aws iam put-user-policy --user-name agente-diagnostico --policy-name diagnostico-asg-campo \
  --policy-document file://politica-agente-floci.json
aws iam create-access-key --user-name agente-diagnostico \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text > .chave-agente
chmod 600 .chave-agente
echo "usuário agente-diagnostico criado; chave em etapa5/.chave-agente"
