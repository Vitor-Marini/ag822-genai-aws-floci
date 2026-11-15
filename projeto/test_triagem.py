"""Testes da triagem sem Floci: python projeto/test_triagem.py"""
import json, os, sys, types
os.environ.update(TABELA="t", TOPICO="arn:t", AWS_DEFAULT_REGION="us-east-1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "triagem"))
import app

def roda(alerta, respostas):
    fila, gravado, publicado = list(respostas), {}, []
    app.bedrock = types.SimpleNamespace(converse=lambda **k: {"output": {"message": {"content": [{"text": fila.pop(0)}]}},
                                                             "usage": {"inputTokens": 1, "outputTokens": 1}})
    app.s3 = types.SimpleNamespace(get_object=lambda **k: {"Body": types.SimpleNamespace(read=lambda: json.dumps(alerta).encode())})
    app.tabela = types.SimpleNamespace(put_item=lambda Item: gravado.update(Item))
    app.sns = types.SimpleNamespace(publish=lambda **k: publicado.append(k))
    app.handler({"Records": [{"s3": {"bucket": {"name": "b"}, "object": {"key": "alertas/x.json"}}}]}, None)
    return gravado, publicado

def test_faixa():
    assert app.situacao_faixa({"valor": 27, "faixa": [22, 35]}) == "dentro"
    assert app.situacao_faixa({"valor": 0.6, "faixa": [2.5, 4]}) == "abaixo"
    assert app.situacao_faixa({"valor": 5, "faixa": [2.5, 4]}) == "acima"
    assert app.situacao_faixa({"valor": "x"}) == "desconhecida"

def test_piso():
    assert app.piso_urgencia({"situacao_faixa": "dentro"}) == "baixa"
    assert app.piso_urgencia({"situacao_faixa": "abaixo", "valor": 2.1, "faixa": [2.5, 4]}) == "media"
    assert app.piso_urgencia({"situacao_faixa": "abaixo", "valor": 11, "faixa": [22, 35]}) == "alta"
    assert app.piso_urgencia({"situacao_faixa": "acima", "valor": 50, "faixa": [22, 35]}) == "alta"

def test_ia_nao_rebaixa_abaixo_do_piso():
    g, p = roda({"sensor": "s", "valor": 11, "faixa": [22, 35]}, ['{"resumo": "r", "urgencia": "media", "acao": "a"}'])
    assert g["urgencia"] == "alta" and g["urgencia_ia"] == "media" and len(p) == 1

def test_alta_publica_no_sns():
    g, p = roda({"sensor": "s", "valor": 0.6, "faixa": [2.5, 4]}, ['{"resumo": "r", "urgencia": "alta", "acao": "a"}'])
    assert g["urgencia"] == "alta" and len(p) == 1

def test_baixa_nao_publica():
    g, p = roda({"sensor": "s", "valor": 27, "faixa": [22, 35]}, ['{"resumo": "r", "urgencia": "baixa", "acao": "a"}'])
    assert g["urgencia"] == "baixa" and p == []

def test_invalido_vai_para_humano_e_avisa():
    g, p = roda({"sensor": "s"}, ["lixo", "mais lixo"])
    assert g["urgencia"] == "revisao_humana" and len(p) == 1

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f()
    print("ok")
