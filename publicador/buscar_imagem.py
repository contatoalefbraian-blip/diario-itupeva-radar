"""Busca de imagem por assunto, para a De (roda no GitHub Actions).
Le os pedidos em pedidos/*.json e baixa ate 6 candidatas de fontes livres (Wikimedia Commons,
que inclui o acervo da Agencia Brasil, de uso livre com credito).

Pedido (pedidos/<id>.json), escrito pela rotina:
  {"id": "2026-11-11-09h", "termos": ["Boate Kiss fachada", "Boate Kiss Santa Maria"], "evitar": ["vitima", "corpo"]}
Saida (ramo "imagens", pasta <id>/): c1.jpg ... c6.jpg e candidatas.json com titulo, credito, licenca e origem.
Uso: python3 publicador/buscar_imagem.py <pasta_do_ramo_imagens>
"""
import glob, html, io, json, os, re, sys, unicodedata, urllib.parse, urllib.request
from PIL import Image

SAIDA = sys.argv[1] if len(sys.argv) > 1 else "imgs"
UA = {"User-Agent": "DiarioItupevaRadar/1.0 (https://github.com/contatoalefbraian-blip/diario-itupeva-radar)"}
MIN_LONGO, MIN_CURTO, MAX_LARG, MAX_CAND = 700, 360, 1600, 6
SEMPRE_EVITAR = ["painting", "pintura", "oil on canvas", "corpse", "cadaver", "dead body", "gore", "blood"]


def norm(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def limpa(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read(15_000_000)


def commons(termo):
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": termo + " filetype:bitmap", "gsrlimit": 30, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": MAX_LARG})
    paginas = json.loads(get(api)).get("query", {}).get("pages", {})
    return sorted(paginas.values(), key=lambda p: p.get("index", 99))


def atender(pedido, pasta):
    os.makedirs(pasta, exist_ok=True)
    evitar = SEMPRE_EVITAR + [norm(e) for e in pedido.get("evitar", [])]
    vistas, cand = set(), []
    for termo in pedido.get("termos", [])[:4]:
        try:
            paginas = commons(termo)
        except Exception as e:
            print("  commons:", str(e)[:120]); continue
        for pg in paginas:
            if len(cand) >= MAX_CAND:
                break
            ii = (pg.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = limpa(meta.get("LicenseShortName", {}).get("value"))
            url = ii.get("url")
            if url in vistas or ii.get("mime") != "image/jpeg" or not lic:
                continue
            if "fair use" in lic.lower() or "non-free" in lic.lower():
                continue
            w, h = ii.get("width", 0), ii.get("height", 0)
            if max(w, h) < MIN_LONGO or min(w, h) < MIN_CURTO:
                continue
            desc = limpa(meta.get("ImageDescription", {}).get("value"))
            texto = norm(" ".join([pg.get("title", ""), desc, limpa(meta.get("Categories", {}).get("value"))]))
            if any(e in texto for e in evitar):
                continue
            vistas.add(url)
            try:
                im = Image.open(io.BytesIO(get(ii.get("thumburl") or url))).convert("RGB")
            except Exception as e:
                print("  baixar:", str(e)[:120]); continue
            if im.width > MAX_LARG:
                im = im.resize((MAX_LARG, round(im.height * MAX_LARG / im.width)), Image.LANCZOS)
            nome = f"c{len(cand) + 1}.jpg"
            im.save(os.path.join(pasta, nome), "JPEG", quality=88)
            autor = limpa(meta.get("Artist", {}).get("value"))[:60] or "autor desconhecido"
            cand.append({"arquivo": nome, "titulo": pg.get("title", "").replace("File:", ""),
                         "descricao": desc[:200], "tamanho": f"{im.width}x{im.height}", "termo": termo,
                         "credito": f"Foto: {autor} / Wikimedia Commons ({lic})", "origem": ii.get("descriptionurl")})
    json.dump({"pedido": pedido, "candidatas": cand}, open(os.path.join(pasta, "candidatas.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"pedido {pedido.get('id')}: {len(cand)} candidatas")
    return cand


def main():
    for arq in sorted(glob.glob("pedidos/*.json")):
        pedido = json.load(open(arq))
        pid = re.sub(r"[^A-Za-z0-9_-]", "", str(pedido.get("id") or os.path.basename(arq)[:-5]))
        if os.path.exists(os.path.join(SAIDA, pid, "candidatas.json")):
            continue
        atender(pedido, os.path.join(SAIDA, pid))


if __name__ == "__main__":
    main()
