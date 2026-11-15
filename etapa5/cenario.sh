#!/usr/bin/env bash
# Monta o cenário da Etapa 5 no Floci: ASG asg-campo, ASG asg-outro (para testar o IAM), alarme → SNS → SQS e o incidente de CPU.
set -euo pipefail
aws sts get-caller-identity --query Account --output text | grep -qx 000000000000 || { echo "Não é o Floci. Abortando."; exit 1; }
aws autoscaling create-launch-configuration --launch-configuration-name lc-campo --image-id ami-12345678 --instance-type t3.micro
for g in asg-campo asg-outro; do
  aws autoscaling create-auto-scaling-group --auto-scaling-group-name $g --launch-configuration-name lc-campo \
    --min-size 1 --max-size 4 --desired-capacity 1 --availability-zones us-east-1a
done
T=$(aws sns create-topic --name alarmes-campo --query TopicArn --output text)
Q=$(aws sqs create-queue --queue-name alarmes-campo --query QueueUrl --output text)
QA=$(aws sqs get-queue-attributes --queue-url "$Q" --attribute-names QueueArn --query Attributes.QueueArn --output text)
aws sns subscribe --topic-arn "$T" --protocol sqs --notification-endpoint "$QA" >/dev/null
aws cloudwatch put-metric-alarm --alarm-name cpu-alta-asg-campo --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=asg-campo --statistic Average --period 60 --evaluation-periods 3 \
  --threshold 80 --comparison-operator GreaterThanThreshold --alarm-actions "$T"
aws logs create-log-group --log-group-name /agente/diagnostico 2>/dev/null || true
"$(dirname "$0")/incidente.sh"
echo "cenário pronto"
