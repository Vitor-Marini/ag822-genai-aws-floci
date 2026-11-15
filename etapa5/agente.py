"""Agente de diagnóstico (Etapa 5): o modelo escolhe as ferramentas; escrita só com aprovação humana.

Uso: source ../env.sh && python agente.py ["pergunta"]
Credenciais: usa as do usuário IAM restrito agente-diagnostico (arquivo .chave-agente), não as de admin.
"""
import json, os, sys, time
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config

AQUI = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(AQUI, ".chave-agente")) as f:
    chave, segredo = f.read().split()
sessao = boto3.Session(aws_access_key_id=chave, aws_secret_access_key=segredo)
bedrock = sessao.client("bedrock-runtime", config=Config(read_timeout=300, retries={"max_attempts": 1}))
cloudwatch = sessao.client("cloudwatch")
autoscaling = sessao.client("autoscaling")
logs = sessao.client("logs")

MODELO = "anthropic.claude-3-haiku-20240307-v1:0"
ASG_PERMITIDO = "asg-campo"   # trava no código além do IAM (o Floci não avalia ARN de Auto Scaling)
MAX_ITERACOES = 6
LOG_GROUP, LOG_STREAM = "/agente/diagnostico", datetime.now(timezone.utc).strftime("execucao-%Y%m%d-%H%M%S")

SISTEMA = """Você é um agente de diagnóstico de infraestrutura AWS de uma aplicação de monitoramento de lavouras.
Investigue usando as ferramentas antes de concluir. Regras:
- Leia a série de métricas de vários minutos; nunca recomende escalar com base em um único ponto ou em poucos pontos isolados.
- Confira o estado do grupo de Auto Scaling e as atividades recentes antes de propor ajuste.
- Critério de escala: se a CPU ficou acima do limite do alarme em 3 ou mais minutos seguidos e desejado < máximo,
  chame ajustar_capacidade com desejado + 1 (um passo por vez). Com menos pontos acima do limite, não escale.
- A chamada de ajustar_capacidade não executa nada sozinha: um humano aprova ou nega antes.
Responda no fim em português com três seções: O que aconteceu, Causa provável, Ação recomendada."""


def _schema(props, obrigatorios):
    return {"json": {"type": "object", "properties": props, "required": obrigatorios}}


ASG = {"asg": {"type": "string", "description": "nome do grupo de Auto Scaling"}}
FERRAMENTAS = [
    {"toolSpec": {"name": "ler_metricas", "description": "Série de CPU média (%) por minuto de um grupo de Auto Scaling.",
                  "inputSchema": _schema({**ASG, "minutos": {"type": "integer", "description": "janela, padrão 15"}}, ["asg"])}},
    {"toolSpec": {"name": "descrever_asg", "description": "Capacidade mínima, máxima, desejada e instâncias do grupo.",
                  "inputSchema": _schema(ASG, ["asg"])}},
    {"toolSpec": {"name": "listar_atividades", "description": "Atividades recentes de escalonamento do grupo.",
                  "inputSchema": _schema(ASG, ["asg"])}},
    {"toolSpec": {"name": "ler_alarmes", "description": "Estado dos alarmes do CloudWatch.", "inputSchema": _schema({}, [])}},
    {"toolSpec": {"name": "ajustar_capacidade", "description": "ESCRITA: muda a capacidade desejada do grupo. Exige aprovação.",
                  "inputSchema": _schema({**ASG, "capacidade": {"type": "integer"}}, ["asg", "capacidade"])}},
]


def ler_metricas(asg, minutos=15):
    fim = datetime.now(timezone.utc)
    r = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2", MetricName="CPUUtilization", Dimensions=[{"Name": "AutoScalingGroupName", "Value": asg}],
        StartTime=fim - timedelta(minutes=int(minutos)), EndTime=fim, Period=60, Statistics=["Average"])
    pontos = sorted(r["Datapoints"], key=lambda p: p["Timestamp"])
    return {"asg": asg, "quantidade_de_pontos": len(pontos),
            "serie": [{"hora": p["Timestamp"].strftime("%H:%M"), "cpu": round(p["Average"], 1)} for p in pontos]}


def descrever_asg(asg):
    g = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])["AutoScalingGroups"]
    if not g:
        return {"erro": f"grupo {asg} não existe"}
    g = g[0]
    return {"asg": asg, "minimo": g["MinSize"], "maximo": g["MaxSize"], "desejado": g["DesiredCapacity"],
            "instancias": [i["InstanceId"] for i in g.get("Instances", [])]}


def listar_atividades(asg):
    a = autoscaling.describe_scaling_activities(AutoScalingGroupName=asg, MaxRecords=5)["Activities"]
    return {"atividades": [{"descricao": x.get("Description"), "status": x.get("StatusCode")} for x in a]}


def ler_alarmes():
    return {"alarmes": [{"nome": a["AlarmName"], "estado": a["StateValue"], "limite": a["Threshold"]}
                        for a in cloudwatch.describe_alarms()["MetricAlarms"]]}


def ajustar_capacidade(asg, capacidade):
    if asg != ASG_PERMITIDO:
        return {"erro": f"o agente só pode alterar {ASG_PERMITIDO}"}
    g = descrever_asg(asg)
    if not g.get("minimo", 0) <= int(capacidade) <= g.get("maximo", 0):
        return {"erro": f"capacidade {capacidade} fora de [{g.get('minimo')}, {g.get('maximo')}]"}
    autoscaling.set_desired_capacity(AutoScalingGroupName=asg, DesiredCapacity=int(capacidade))
    return {"ok": True, "asg": asg, "nova_capacidade": int(capacidade)}


EXECUTORES = {f.__name__: f for f in (ler_metricas, descrever_asg, listar_atividades, ler_alarmes, ajustar_capacidade)}


def auditar(evento):
    """Grava cada chamada de ferramenta no CloudWatch Logs (trilha de auditoria)."""
    logs.put_log_events(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM,
                        logEvents=[{"timestamp": int(time.time() * 1000), "message": json.dumps(evento, ensure_ascii=False, default=str)}])


def executar(nome, entrada):
    try:
        return EXECUTORES[nome](**entrada)
    except Exception as e:  # erro de ferramenta (ex.: AccessDenied) volta para o modelo, não derruba o agente
        return {"erro": f"{type(e).__name__}: {e}"}


def main():
    pergunta = sys.argv[1] if len(sys.argv) > 1 else (
        "O alarme cpu-alta-asg-campo disparou. Diagnostique o grupo asg-campo e recomende uma ação.")
    logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    print(f"[auditoria] {LOG_GROUP} / {LOG_STREAM}\n[operador] {pergunta}\n")
    msgs = [{"role": "user", "content": [{"text": pergunta}]}]
    for iteracao in range(1, MAX_ITERACOES + 1):
        resp = bedrock.converse(modelId=MODELO, system=[{"text": SISTEMA}], messages=msgs,
                                toolConfig={"tools": FERRAMENTAS}, inferenceConfig={"temperature": 0, "maxTokens": 800})
        msg = resp["output"]["message"]
        msgs.append(msg)
        if resp["stopReason"] != "tool_use":
            texto = "".join(b.get("text", "") for b in msg["content"])
            auditar({"tipo": "resposta", "iteracao": iteracao, "texto": texto})
            print(f"[agente] {texto}\n")
            try:  # o operador pode responder (ex.: pedir que proponha o ajuste); Enter vazio encerra
                seguimento = input("[operador] ").strip()
            except EOFError:
                seguimento = ""
            print(seguimento)
            if not seguimento:
                return
            auditar({"tipo": "operador", "iteracao": iteracao, "texto": seguimento})
            msgs.append({"role": "user", "content": [{"text": seguimento}]})
            continue
        resultados = []
        for bloco in msg["content"]:
            if "toolUse" not in bloco:
                continue
            uso = bloco["toolUse"]
            print(f"[iteração {iteracao}] ferramenta {uso['name']}({json.dumps(uso['input'], ensure_ascii=False)})")
            aprovado = None
            if uso["name"] == "ajustar_capacidade":
                aprovado = input(f"  Aprovar ajustar_capacidade {uso['input']}? [s/N] ").strip().lower() == "s"
                print(f"  operador: {'APROVOU' if aprovado else 'NEGOU'}")
            resultado = executar(uso["name"], uso["input"]) if aprovado is not False else {"erro": "ação negada pelo operador"}
            print(f"  → {json.dumps(resultado, ensure_ascii=False, default=str)[:300]}")
            auditar({"tipo": "ferramenta", "iteracao": iteracao, "nome": uso["name"], "entrada": uso["input"],
                     "aprovado": aprovado, "resultado": resultado})
            resultados.append({"toolResult": {"toolUseId": uso["toolUseId"], "content": [{"json": resultado}]}})
        msgs.append({"role": "user", "content": resultados})
    auditar({"tipo": "limite_de_iteracoes", "iteracoes": MAX_ITERACOES})
    print(f"[agente] limite de {MAX_ITERACOES} iterações atingido sem conclusão")


if __name__ == "__main__":
    main()
