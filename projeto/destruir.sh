#!/usr/bin/env bash
# Apaga o projeto do Floci.
set -uo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
B=irrigacao-ia-$(aws sts get-caller-identity --query Account --output text)
aws s3 rm s3://$B --recursive >/dev/null
aws cloudformation delete-stack --stack-name irrigacao-ia && aws cloudformation wait stack-delete-complete --stack-name irrigacao-ia
aws s3 rb s3://artefatos-irrigacao-ia --force >/dev/null
echo "removido"
