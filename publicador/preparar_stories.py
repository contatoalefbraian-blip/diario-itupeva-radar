"""Gera a versao Story (9:16) dos posts da fila que ja chegaram no horario, antes da publicacao.
A arte do feed (4:5) vai inteira no centro, sobre um fundo escuro feito da propria arte desfocada.
Desligar: criar o arquivo SEM_STORIES na raiz do repositorio. Reels nao ganham story."""
import datetime as dt, glob, json, os
from PIL import Image, ImageFilter, ImageEnhance

W, H = 1080, 1920
if os.path.exists("SEM_STORIES"):
    print("stories desligados (SEM_STORIES)"); raise SystemExit
agora = dt.datetime.now(dt.timezone.utc)
for arq in sorted(glob.glob("fila/*.json")):
    post = json.load(open(arq))
    if post.get("tipo", "feed") in ("reels", "so_story") or dt.datetime.fromisoformat(post["horario"]) - dt.timedelta(minutes=20) > agora:
        continue
    destino = arq[:-5] + "-story.jpg"
    if os.path.exists(destino) or not post.get("midia") or not os.path.exists(post["midia"][0]):
        continue
    arte = Image.open(post["midia"][0]).convert("RGB")
    fundo = arte.resize((W, round(arte.height * W / arte.width))).resize((W, H)).filter(ImageFilter.GaussianBlur(40))
    fundo = ImageEnhance.Brightness(fundo).enhance(0.45)
    a = arte.resize((W, round(arte.height * W / arte.width)), Image.LANCZOS)
    fundo.paste(a, (0, (H - a.height) // 2))
    fundo.save(destino, "JPEG", quality=92)
    print("story pronto:", destino)
