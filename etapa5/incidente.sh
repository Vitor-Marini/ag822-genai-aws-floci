#!/usr/bin/env bash
# Simula o incidente: publica a série de CPU dos últimos 10 minutos para o asg-campo.
set -euo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci (conta 000000000000). Abortando."; exit 1; }
# incidente: CPU subindo de 30% para 95% nos últimos 10 minutos (um ponto por minuto)
VALORES=(30 34 41 48 57 66 78 86 91 95)
for i in "${!VALORES[@]}"; do
  ts=$(date -u -d "-$((9 - i)) minutes" +%Y-%m-%dT%H:%M:%SZ)
  aws cloudwatch put-metric-data --namespace AWS/EC2 --metric-name CPUUtilization \
    --dimensions AutoScalingGroupName=asg-campo --value "${VALORES[$i]}" --unit Percent --timestamp "$ts"
done
