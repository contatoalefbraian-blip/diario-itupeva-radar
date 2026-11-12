"""Teste: le perfis e hashtag pela API oficial (business discovery / hashtag search). Nao publica. Nunca imprime token."""
import json, os, urllib.parse, urllib.request
T = os.environ["META_TOKEN"]; IG = "17841473503076065"
def get(path, **p):
    p["access_token"] = T
    try:
        with urllib.request.urlopen("https://graph.facebook.com/v21.0/" + path + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ERRO": json.loads(e.read() or b"{}").get("error", {}).get("message")}
for u in ["coisasdaregiao", "ia_noticias", "jrjundiai", "avozdaregiao.jundiai", "jornaldejundiai", "expressao.jornal", "coisasdeitupeva", "avozdaregiao.itupeva"]:
    r = get(IG, fields=f"business_discovery.username({u}){{username,followers_count,media_count,media.limit(2){{caption,timestamp,permalink}}}}")
    if "ERRO" in r:
        print(u, "-> ERRO:", r["ERRO"][:150]); continue
    bd = r.get("business_discovery", {})
    m = bd.get("media", {}).get("data", [])
    print(u, "-> OK", bd.get("followers_count"), "seguidores |", (m[0]["timestamp"] + " " + (m[0].get("caption") or "")[:90].replace("\n", " ")) if m else "sem posts")
h = get("ig_hashtag_search", user_id=IG, q="itupeva")
print("hashtag itupeva:", h)
