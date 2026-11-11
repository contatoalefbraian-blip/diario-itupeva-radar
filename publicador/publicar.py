"""Publicador do Diario de Itupeva: roda no GitHub Actions a cada 10 minutos.
Le os posts aprovados pelo Peter em fila/*.json e publica no Instagram (@diariodeitupeva) quando chega o horario.
O Facebook recebe pelo compartilhamento automatico do Instagram.

Formato de fila/<nome>.json:
  {"horario": "2026-11-11T09:00:00-03:00",
   "tipo": "feed" | "carrossel" | "reels",
   "midia": ["fila/<nome>.jpg"]            # feed: 1 JPEG; carrossel: 2 a 10 JPEG; reels: 1 MP4
   "legenda": "...",
   "pauta": "...", "aprovado_por": "Peter"}

Regras:
  - arquivo PAUSA na raiz do repositorio: nada e publicado;
  - post com mais de 3 horas de atraso nao e publicado (vai para fila/atrasados/ e o motivo fica registrado);
  - publicado: o .json vai para publicados/ com o id e o link do post; a midia sai da fila.
Nunca imprime o token.
"""
import datetime as dt, glob, json, os, shutil, sys, time, urllib.parse, urllib.request

TOKEN = os.environ.get("META_TOKEN", "")
IG = os.environ.get("META_IG_ID", "17841473503076065")
REPO = os.environ.get("GITHUB_REPOSITORY", "contatoalefbraian-blip/diario-itupeva-radar")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
API = "https://graph.facebook.com/v21.0/"
ATRASO_MAX = dt.timedelta(hours=3)


def chamar(metodo, caminho, **dados):
    dados["access_token"] = TOKEN
    corpo = urllib.parse.urlencode(dados).encode()
    if metodo == "GET":
        req = urllib.request.Request(API + caminho + "?" + corpo.decode())
    else:
        req = urllib.request.Request(API + caminho, data=corpo, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        erro = json.loads(e.read() or b"{}").get("error", {})
        raise RuntimeError(f"Meta {e.code}: {erro.get('message')} (code {erro.get('code')}, sub {erro.get('error_subcode')})")


def esperar(container, limite=300):
    fim = time.time() + limite
    while time.time() < fim:
        st = chamar("GET", container, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {st}")
        time.sleep(5)
    raise RuntimeError("container nao ficou pronto a tempo")


def publicar(post):
    midias = [RAW + urllib.parse.quote(m) for m in post["midia"]]
    tipo = post.get("tipo", "feed")
    legenda = post["legenda"]
    if tipo == "feed":
        c = chamar("POST", f"{IG}/media", image_url=midias[0], caption=legenda)["id"]
    elif tipo == "carrossel":
        filhos = [chamar("POST", f"{IG}/media", image_url=u, is_carousel_item="true")["id"] for u in midias]
        for f in filhos:
            esperar(f)
        c = chamar("POST", f"{IG}/media", media_type="CAROUSEL", children=",".join(filhos), caption=legenda)["id"]
    elif tipo == "reels":
        c = chamar("POST", f"{IG}/media", media_type="REELS", video_url=midias[0], caption=legenda,
                   share_to_feed="true")["id"]
    else:
        raise RuntimeError(f"tipo desconhecido: {tipo}")
    esperar(c, 600 if tipo == "reels" else 120)
    mid = chamar("POST", f"{IG}/media_publish", creation_id=c)["id"]
    link = chamar("GET", mid, fields="permalink").get("permalink")
    return mid, link


def main():
    if os.path.exists("PAUSA"):
        print("PAUSA ativa: nada publicado."); return
    if not TOKEN:
        print("META_TOKEN ausente."); sys.exit(1)
    agora = dt.datetime.now(dt.timezone.utc)
    os.makedirs("publicados", exist_ok=True)
    falhas = 0
    for arq in sorted(glob.glob("fila/*.json")):
        post = json.load(open(arq))
        quando = dt.datetime.fromisoformat(post["horario"])
        if quando > agora:
            print("aguardando:", arq, post["horario"]); continue
        nome = os.path.basename(arq)
        if agora - quando > ATRASO_MAX:
            os.makedirs("fila/atrasados", exist_ok=True)
            post["status"] = f"nao publicado: mais de 3h de atraso (verificado {agora.isoformat()})"
            json.dump(post, open(f"fila/atrasados/{nome}", "w"), ensure_ascii=False, indent=1)
            os.remove(arq)
            for m in post["midia"]:
                if os.path.exists(m):
                    os.remove(m)
            print("atrasado:", arq); continue
        try:
            mid, link = publicar(post)
        except Exception as e:
            falhas += 1
            print("FALHA:", arq, e)
            post.setdefault("tentativas", []).append(f"{agora.isoformat()} {e}")
            json.dump(post, open(arq, "w"), ensure_ascii=False, indent=1)
            continue
        post.update({"status": "publicado", "publicado_em": agora.isoformat(), "instagram_id": mid, "link": link})
        json.dump(post, open(f"publicados/{nome}", "w"), ensure_ascii=False, indent=1)
        os.remove(arq)
        for m in post["midia"]:
            if os.path.exists(m):
                os.remove(m)
        print("PUBLICADO:", nome, link)
    if falhas:
        sys.exit(2)


if __name__ == "__main__":
    main()
