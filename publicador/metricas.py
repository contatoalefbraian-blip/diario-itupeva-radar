"""Coleta diaria de metricas para a Karen (GitHub Actions, 23h). Grava uma linha por dia em registro/metricas.jsonl:
seguidores do Instagram e da pagina, e o desempenho de cada post publicado nos ultimos 8 dias.
Metricas que a chave nao alcanca (ex.: alcance, salvamentos) ficam como "sem permissao". Nunca imprime tokens."""
import datetime as dt, glob, json, os, urllib.parse, urllib.request

IG, PAGE = "17841473503076065", "1027608040724712"
T_IG, T_FB = os.environ.get("META_TOKEN", ""), os.environ.get("META_FB_TOKEN", "")


def get(tok, path, **p):
    p["access_token"] = tok
    try:
        with urllib.request.urlopen("https://graph.facebook.com/v21.0/" + path + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"erro": (json.loads(e.read() or b"{}").get("error", {}).get("message") or str(e.code))[:120]}


agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
linha = {"data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M"),
         "instagram": get(T_IG, IG, fields="followers_count,follows_count,media_count"),
         "facebook": get(T_FB, PAGE, fields="followers_count,fan_count"), "posts": []}
for arq in sorted(glob.glob("publicados/*.json")):
    p = json.load(open(arq))
    quando = dt.datetime.fromisoformat(p.get("publicado_em", p["horario"]))
    if (agora - quando).days > 8:
        continue
    item = {"arquivo": os.path.basename(arq), "pauta": p.get("pauta"), "publicado_em": p.get("publicado_em"), "link": p.get("link")}
    if p.get("instagram_id"):
        item["ig"] = get(T_IG, p["instagram_id"], fields="like_count,comments_count")
        ins = get(T_IG, f"{p['instagram_id']}/insights", metric="reach,saved,shares,total_interactions")
        item["ig_insights"] = {m["name"]: m["values"][0]["value"] for m in ins.get("data", [])} or "sem permissao"
    if p.get("facebook_id"):
        fb = get(T_FB, p["facebook_id"], fields="reactions.summary(total_count),comments.summary(total_count),shares")
        item["fb"] = {"reacoes": fb.get("reactions", {}).get("summary", {}).get("total_count"),
                      "comentarios": fb.get("comments", {}).get("summary", {}).get("total_count"),
                      "compartilhamentos": fb.get("shares", {}).get("count", 0), **({"erro": fb["erro"]} if "erro" in fb else {})}
    linha["posts"].append(item)
os.makedirs("registro", exist_ok=True)
with open("registro/metricas.jsonl", "a") as f:
    f.write(json.dumps(linha, ensure_ascii=False) + "\n")
print(json.dumps({k: linha[k] for k in ("instagram", "facebook")}, ensure_ascii=False), "| posts:", len(linha["posts"]))
for it in linha["posts"]:
    print(" ", it["arquivo"], it.get("ig"), it.get("ig_insights"), it.get("fb"))
