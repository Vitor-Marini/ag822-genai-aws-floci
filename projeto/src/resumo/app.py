"""Resumo diário: lê os alertas do dia no DynamoDB, pede ao Bedrock um resumo para o gerente e envia por SNS."""
import boto3, json, os
from boto3.dynamodb.conditions import Attr
from datetime import datetime, timezone

s3 = boto3.client("s3")
sns = boto3.client("sns")
bedrock = boto3.client("bedrock-runtime")
tabela = boto3.resource("dynamodb").Table(os.environ["TABELA"])
MODELO = os.environ.get("MODELO", "anthropic.claude-3-haiku-20240307-v1:0")


def handler(event, context):
    dia = (event or {}).get("data") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    itens = tabela.scan(FilterExpression=Attr("data").eq(dia))["Items"]
    if not itens:
        texto = f"Nenhum alerta de irrigação registrado em {dia}."
    else:
        ordem = {"alta": 0, "revisao_humana": 1, "media": 2, "baixa": 3}
        itens.sort(key=lambda i: ordem.get(i["urgencia"], 9))
        linhas = "\n".join(f"- [{i['urgencia']}] talhão {i['talhao']}, {i['sensor']}: {i['resumo']} Ação: {i.get('acao', '')}"
                           for i in itens)
        resp = bedrock.converse(
            modelId=MODELO,
            system=[{"text": "Você escreve o resumo diário de irrigação para o gerente da fazenda, em português, "
                             "em até 8 linhas. Comece por 'Ação hoje:' listando TODOS os alertas marcados [alta] ou [revisao_humana], "
                             "depois 'Próximos dias:' com os [media] e 'Normal:' com os [baixa]. "
                             "Não mude a urgência de nenhum alerta. Use só os alertas fornecidos."}],
            messages=[{"role": "user", "content": [{"text": f"Alertas de {dia}:\n{linhas}"}]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0},
        )
        texto = resp["output"]["message"]["content"][0]["text"]
    s3.put_object(Bucket=os.environ["BUCKET"], Key=f"resumos/{dia}.txt", Body=texto.encode())
    sns.publish(TopicArn=os.environ["TOPICO"], Subject=f"Resumo diário de irrigação {dia}", Message=texto)
    print(json.dumps({"evento": "resumo", "data": dia, "alertas": len(itens)}, ensure_ascii=False))
    return {"data": dia, "alertas": len(itens), "resumo": texto}
