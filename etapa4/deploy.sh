#!/usr/bin/env bash
# Comandos da Etapa 4 do roteiro (linhas quebradas pelo PDF já corrigidas). Rode com: source ../env.sh && ./deploy.sh
set -e
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
cd "$(dirname "$0")"
aws s3 mb s3://relatorios-campo
aws dynamodb create-table --table-name triagem \
  --attribute-definitions AttributeName=arquivo,AttributeType=S \
  --key-schema AttributeName=arquivo,KeyType=HASH --billing-mode PAY_PER_REQUEST
aws iam create-role --role-name triagem-lambda \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
# política mínima construída na Etapa 6 (com IAM ligado, a role vazia leva AccessDenied)
aws iam put-role-policy --role-name triagem-lambda --policy-name minimo --policy-document file://../etapa6/politica-lambda-triagem.json
rm -f funcao.zip && zip -q funcao.zip app.py
aws lambda create-function --function-name triagem --runtime python3.12 \
  --handler app.handler --zip-file fileb://funcao.zip --timeout 120 \
  --role arn:aws:iam::000000000000:role/triagem-lambda \
  --environment Variables={TABELA=triagem}
aws s3api put-bucket-notification-configuration --bucket relatorios-campo \
  --notification-configuration '{"LambdaFunctionConfigurations":[{"LambdaFunctionArn":"arn:aws:lambda:us-east-1:000000000000:function:triagem","Events":["s3:ObjectCreated:*"]}]}'
