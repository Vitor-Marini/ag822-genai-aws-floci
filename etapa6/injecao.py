"""Teste de injeção de prompt (Etapa 6): prompt do roteiro × prompt defendido, com e sem a frase injetada.

Uso: python injecao.py [repeticoes]   (padrão 3; temperatura 0, como na Lambda)
"""
import json, os, sys
from collections import Counter

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etapa4"))
os.environ.setdefault("TABELA", "triagem")
import app  # usa a mesma função classificar() da Lambda (prompt defendido)

AQUI = os.path.dirname(os.path.abspath(__file__))
bedrock = boto3.client("bedrock-runtime")
ORIGINAL = "Responda só em JSON: {\"resumo\": str, \"urgencia\": \"baixa|media|alta\"}"   # system prompt do roteiro
COM_INJECAO = open(os.path.join(AQUI, "relatorio-injecao.txt")).read()
SEM_INJECAO = "\n".join(l for l in COM_INJECAO.splitlines() if "ignore as instruções" not in l)


def original(texto):
    """Exatamente como o app.py do roteiro: relatório cru, sem delimitador, sem critérios."""
    r = bedrock.converse(modelId=app.MODELO, system=[{"text": ORIGINAL}],
                         messages=[{"role": "user", "content": [{"text": texto}]}],
                         inferenceConfig={"maxTokens": 300, "temperature": 0})
    bruto = r["output"]["message"]["content"][0]["text"]
    try:
        return json.loads(bruto.strip().strip("`").removeprefix("json")).get("urgencia", "?")
    except json.JSONDecodeError:
        return "invalido"


def defendido(texto):
    saida, _, _ = app.classificar(texto)
    return saida["urgencia"] if saida else "invalido"


def defendido_com_filtro(texto):
    return defendido(app.limpar(texto)[0])


n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for nome, f in (("prompt do roteiro", original), ("prompt defendido", defendido), ("defendido + filtro", defendido_com_filtro)):
    for rotulo, texto in (("sem injeção", SEM_INJECAO), ("com injeção", COM_INJECAO)):
        print(f"{nome:18} | {rotulo:12} | {dict(Counter(f(texto) for _ in range(n)))}")
