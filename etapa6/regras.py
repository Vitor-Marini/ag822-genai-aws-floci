"""Alternativa sem IA (Etapa 6): urgência por palavras-chave, para comparar acerto e custo com o Bedrock.

Uso: python regras.py
"""
import glob, os, re, sys

ALTA = r"rompid|vazament|alagand|imediat|hoje|acima do n[ií]vel de dano|\b[5-9]\d ?%"
MEDIA = r"reavaliar|praga|lagarta|ferrugem|percevejo|abaixo do n[ií]vel de controle"


def urgencia(texto):
    t = texto.lower()
    return "alta" if re.search(ALTA, t) else "media" if re.search(MEDIA, t) else "baixa"


if __name__ == "__main__":
    aqui = os.path.dirname(os.path.abspath(__file__))
    casos = {os.path.basename(f): open(f).read() for f in sorted(glob.glob(os.path.join(aqui, "..", "etapa4", "relatorios", "*.txt")))}
    casos["relatorio-injecao.txt"] = open(os.path.join(aqui, "relatorio-injecao.txt")).read()
    # casos escritos para testar os limites da regra (negação e sinônimo)
    casos["negacao.txt"] = "Talhão 2: sem vazamento no pivô, nenhuma praga encontrada, irrigação normal."
    casos["sinonimo.txt"] = "Talhão 4: cano estourado na linha do pivô 3, água empoçando na lavoura de milho."
    esperado = {"relatorio1.txt": "baixa", "relatorio2.txt": "media", "relatorio3.txt": "alta",
                "relatorio-injecao.txt": "alta", "negacao.txt": "baixa", "sinonimo.txt": "alta"}
    acertos = 0
    for nome, texto in casos.items():
        u = urgencia(texto)
        acertos += u == esperado[nome]
        print(f"{nome:22} esperado={esperado[nome]:6} regra={u:6} {'✓' if u == esperado[nome] else '✗'}")
    print(f"acertos: {acertos}/{len(casos)}")
