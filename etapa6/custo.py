"""Custo projetado (Etapa 6) a partir dos tokens medidos na Etapa 4 e de preços oficiais da AWS (us-east-1).

Fontes: AWS Price List API (AmazonBedrockFoundationModels e AmazonBedrock, publicados em 09–11/11/2026; AWSLambda em
11/11/2026); g4dn.xlarge: instances.vantage.sh (consulta em 15/11/2026). Uso: python custo.py
"""
TOKENS_IN, TOKENS_OUT = 232, 34              # média medida por relatório (etapa4/resultados.tsv)
POR_MES = 500 * 30                           # 500 relatórios por dia
PRECO_1M = {                                 # US$ por 1 milhão de tokens (entrada, saída), on-demand
    "Claude 3 Haiku": (0.25, 1.25),
    "Claude Haiku 4.5 (global)": (1.00, 5.00),
    "Amazon Nova Lite": (0.06, 0.24),
    "Amazon Nova Micro": (0.035, 0.14),
}
LAMBDA_REQ, LAMBDA_GBS = 0.20 / 1e6, 0.0000166667
LAMBDA_MEM_GB, LAMBDA_S_IA, LAMBDA_S_REGRA = 0.128, 2.0, 0.1   # 128 MB; ~2 s esperando o Bedrock; regra ~0,1 s
GPU_HORA, HORAS_MES = 0.526, 730             # g4dn.xlarge on-demand (NVIDIA T4 16 GB)


def lambda_mes(segundos):
    return POR_MES * (LAMBDA_REQ + segundos * LAMBDA_MEM_GB * LAMBDA_GBS)


print(f"Volume: {POR_MES} relatórios/mês; tokens por relatório: {TOKENS_IN} entrada + {TOKENS_OUT} saída\n")
print(f"{'Opção':28} {'US$/relatório':>14} {'Modelo/mês':>11} {'Lambda/mês':>11} {'Total/mês':>10} {'Empate GPU (rel./dia)':>22}")
gpu_mes = GPU_HORA * HORAS_MES
for nome, (pin, pout) in PRECO_1M.items():
    por_rel = TOKENS_IN * pin / 1e6 + TOKENS_OUT * pout / 1e6
    total = por_rel * POR_MES + lambda_mes(LAMBDA_S_IA)
    print(f"{nome:28} {por_rel:14.7f} {por_rel * POR_MES:11.2f} {lambda_mes(LAMBDA_S_IA):11.3f} {total:10.2f} {gpu_mes / por_rel / 30:22,.0f}")
print(f"{'Regras fixas (sem IA)':28} {0:14.7f} {0:11.2f} {lambda_mes(LAMBDA_S_REGRA):11.3f} {lambda_mes(LAMBDA_S_REGRA):10.3f} {'—':>22}")
print(f"{'Modelo local em g4dn.xlarge':28} {gpu_mes / POR_MES:14.7f} {gpu_mes:11.2f} {'—':>11} {gpu_mes:10.2f} {'—':>22}")
print("\nLambda antes do nível gratuito (400 mil GB-s/mês cobrem estes volumes); S3 e DynamoDB fora da conta.")
