#!/usr/bin/env bash
# Sobe o projeto inteiro no Floci por IaC. Uso: source ../env.sh && ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
cfn-lint template.yaml --ignore-checks W3002   # W3002: "Code: src/..." só funciona via package, que é o caso
ARTEFATOS=artefatos-irrigacao-ia
aws s3api head-bucket --bucket $ARTEFATOS 2>/dev/null || aws s3 mb s3://$ARTEFATOS
aws cloudformation package --template-file template.yaml --s3-bucket $ARTEFATOS --output-template-file .empacotado.yaml >/dev/null
aws cloudformation deploy --template-file .empacotado.yaml --stack-name irrigacao-ia --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset
aws cloudformation describe-stacks --stack-name irrigacao-ia --query 'Stacks[0].Outputs' --output table
