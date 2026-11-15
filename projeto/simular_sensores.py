"""Envia alertas simulados de sensores de irrigação para o bucket do projeto (alertas/AAAA-MM-DD/<sensor>-<n>.json)."""
import boto3, json, sys
from datetime import datetime, timezone

ALERTAS = [
    {"sensor": "umidade-solo-t3", "talhao": 3, "tipo": "umidade_solo", "valor": 27, "unidade": "%", "faixa": [22, 35],
     "obs": "leitura estável nas últimas 6 h"},
    {"sensor": "pivo-1-pressao", "talhao": 5, "tipo": "pressao_linha", "valor": 2.1, "unidade": "bar", "faixa": [2.5, 4.0],
     "obs": "queda gradual de 0,1 bar por dia desde segunda"},
    {"sensor": "pivo-2-pressao", "talhao": 7, "tipo": "pressao_linha", "valor": 0.6, "unidade": "bar", "faixa": [2.5, 4.0],
     "obs": "queda brusca em 10 min, vazão subiu 40%, possível rompimento da linha principal"},
    {"sensor": "umidade-solo-t9", "talhao": 9, "tipo": "umidade_solo", "valor": 11, "unidade": "%", "faixa": [22, 35],
     "obs": "pivô 4 parado há 2 dias por falha elétrica, milho em pendoamento"},
]

bucket = sys.argv[1] if len(sys.argv) > 1 else f"irrigacao-ia-{boto3.client('sts').get_caller_identity()['Account']}"
agora = datetime.now(timezone.utc)
s3 = boto3.client("s3")
for n, alerta in enumerate(ALERTAS, 1):
    alerta = {**alerta, "timestamp": agora.isoformat()}
    chave = f"alertas/{agora:%Y-%m-%d}/{alerta['sensor']}-{agora:%H%M%S}-{n}.json"
    s3.put_object(Bucket=bucket, Key=chave, Body=json.dumps(alerta, ensure_ascii=False).encode())
    print("enviado", chave)
