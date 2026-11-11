"""Teste das chaves da Meta (nao publica nada). Nunca imprime os tokens."""
import json, os, urllib.parse, urllib.request, datetime

IG = "17841473503076065"
PAGE = "1027608040724712"


def get(tok, path, **params):
    params["access_token"] = tok
    url = "https://graph.facebook.com/v21.0/" + path + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ERRO": e.code, "detalhe": json.loads(e.read() or b"{}").get("error", {}).get("message")}


def validade(tok):
    d = get(tok, "debug_token", input_token=tok).get("data", {})
    if not d:
        return "debug indisponivel"
    exp, dexp = d.get("expires_at"), d.get("data_access_expires_at")
    f = lambda t: "nunca" if not t else datetime.datetime.utcfromtimestamp(t).strftime("%d/%m/%Y")
    return f"valido={d.get('is_valid')} tipo={d.get('type')} vence={f(exp)} acesso_a_dados_ate={f(dexp)} escopos={d.get('scopes')}"


ig = os.environ.get("META_TOKEN", "")
fb = os.environ.get("META_FB_TOKEN", "")
print("== Instagram (META_TOKEN)")
print("conta:", get(ig, IG, fields="username"))
print("== Facebook (META_FB_TOKEN)", "tamanho", len(fb))
print("pagina:", get(fb, PAGE, fields="name,id"))
print("quem sou:", get(fb, "me", fields="id,name"))
print("validade:", validade(fb))

# Teste do carrossel: cria os containers e NAO publica (containers expiram sozinhos em 24h).
import time
RAW = "https://raw.githubusercontent.com/contatoalefbraian-blip/diario-itupeva-radar/main/teste/"
def post(tok, path, **p):
    p["access_token"] = tok
    req = urllib.request.Request("https://graph.facebook.com/v21.0/" + path, data=urllib.parse.urlencode(p).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ERRO": json.loads(e.read() or b"{}").get("error", {}).get("message")}
filhos = [post(ig, f"{IG}/media", image_url=RAW + f"c{i}.jpg", is_carousel_item="true").get("id") for i in (1, 2, 7)]
print("filhos:", filhos)
time.sleep(10)
car = post(ig, f"{IG}/media", media_type="CAROUSEL", children=",".join(f for f in filhos if f), caption="teste (nao publicado)")
print("carrossel:", car)
if car.get("id"):
    time.sleep(10)
    print("status:", get(ig, car["id"], fields="status_code"))
