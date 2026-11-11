"""Teste da chave da Meta (nao publica nada). Mostra o que o token alcanca e quando vence. Nunca imprime o token."""
import json, os, urllib.parse, urllib.request, datetime

T = os.environ["META_TOKEN"]
IG = os.environ.get("META_IG_ID", "17841473503076065")


def get(host, path, **params):
    params["access_token"] = T
    url = f"https://{host}/v21.0/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ERRO": e.code, "detalhe": json.loads(e.read() or b"{}").get("error", {}).get("message")}


print("tipo do token:", T[:3] + "...", "tamanho", len(T))
for host in ("graph.facebook.com", "graph.instagram.com"):
    print("\n==", host)
    print("me:", get(host, "me", fields="id,name"))
    print("instagram:", get(host, IG, fields="id,username,media_count"))
    print("limite de publicacao:", get(host, f"{IG}/content_publishing_limit", fields="config,quota_usage"))
d = get("graph.facebook.com", "debug_token", input_token=T).get("data", {})
if d:
    exp = d.get("expires_at")
    print("\nvalido:", d.get("is_valid"), "| tipo:", d.get("type"), "| escopos:", d.get("scopes"))
    print("vence em:", "nunca" if not exp else datetime.datetime.utcfromtimestamp(exp).isoformat() + "Z")
    print("granular:", [(g.get("scope"), g.get("target_ids")) for g in d.get("granular_scopes", [])])
print("\npaginas:", get("graph.facebook.com", "me/accounts", fields="id,name,tasks"))
