"""Ferramentas manuais do publicador (acionadas pelo workflow 'ferramentas', so a pedido do Alef).

acao=apagar  alvo="ig:<id>,fb:<id>,..."  apaga posts do Instagram (ig) e do Facebook (fb).
acao=baixar  alvo=<url da imagem>  nome=<arquivo.jpg>  baixa a imagem para registro/baixadas/<nome>.
O resultado fica em registro/ferramentas.jsonl.
"""
import datetime as dt, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import publicar as P

acao, alvo, nome = os.environ.get("ACAO", ""), os.environ.get("ALVO", ""), os.environ.get("NOME", "")
saida = {"quando": dt.datetime.now(dt.timezone.utc).isoformat(), "acao": acao, "alvo": alvo, "resultado": []}


def apagar(item):
    rede, _, pid = item.strip().partition(":")
    req_tok = P.TOKEN if rede == "ig" else P.token_pagina()
    url = P.API + pid + "?access_token=" + req_tok
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="DELETE"), timeout=60) as r:
            return {"id": item, "ok": True, "resposta": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        return {"id": item, "ok": False, "erro": (json.loads(e.read() or b"{}").get("error") or {}).get("message")}


if acao == "apagar":
    saida["resultado"] = [apagar(i) for i in alvo.split(",") if i.strip()]
elif acao == "baixar":
    os.makedirs("registro/baixadas", exist_ok=True)
    req = urllib.request.Request(alvo, headers={"User-Agent": "Mozilla/5.0 (DiarioDeItupeva)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        open(os.path.join("registro/baixadas", nome), "wb").write(r.read())
    saida["resultado"] = [{"arquivo": "registro/baixadas/" + nome, "ok": True}]
print(json.dumps(saida, ensure_ascii=False))
open("registro/ferramentas.jsonl", "a").write(json.dumps(saida, ensure_ascii=False) + "\n")
