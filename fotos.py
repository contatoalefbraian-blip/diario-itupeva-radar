"""Fotos do Diario de Itupeva: roda no GitHub Actions logo depois do radar.py.
Para as pautas mais relevantes de pautas.json:
  1. descobre o endereco real da materia (o link do Google Noticias e um redirecionamento);
  2. le a imagem principal da pagina (og:image / twitter:image, tentando a versao original sem recorte);
  3. so aceita imagem em HD (lado maior >= 1280 e lado menor >= 720). Credito: "Foto: <veiculo>";
  4. sem imagem HD, baixa uma IMAGEM ILUSTRATIVA livre do Wikimedia Commons, com autor e licenca no credito.
As imagens ficam no ramo "fotos" do repositorio (reescrito a cada rodada, sem acumular historico).
pautas.json ganha, em cada pauta tratada: foto, credito, foto_tipo (materia | ilustrativa), foto_tamanho.
Uso: python3 fotos.py <pasta_do_ramo_fotos>
"""
import hashlib, html, io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from PIL import Image

PASTA = sys.argv[1] if len(sys.argv) > 1 else "fb"
TOP = 25           # quantas pautas do topo recebem foto
NOVAS_MAX = 25     # quantas pautas novas processar por rodada (limita o tempo)
MIN_LONGO, MIN_CURTO, MAX_LARG = 1000, 560, 1600
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "pt-BR,pt;q=0.9"}
UA_WIKI = {"User-Agent": "DiarioItupevaRadar/1.0 (https://github.com/contatoalefbraian-blip/diario-itupeva-radar)"}

# termo de busca no Wikimedia Commons para a imagem ilustrativa (palavra no titulo -> busca)
TEMAS = [
    (["acidente", "colisao", "capot", "atropel"], "ambulance Brazil"),
    (["incendio", "fogo", "bombeiro"], "Corpo de Bombeiros São Paulo"),
    (["chuva", "temporal", "alagamento", "enchente", "tempestade"], "heavy rain street"),
    (["frio", "frente fria", "geada"], "cold weather fog São Paulo"),
    (["calor", "onda de calor", "seca"], "sun heat summer Brazil"),
    (["previsao do tempo", "clima", "defesa civil"], "storm clouds sky"),
    (["golpe", "fraude", "pix", "caixa eletronico"], "ATM cash machine"),
    (["policia", "preso", "presa", "operacao", "crime", "tiroteio", "homicidio", "delegacia"], "police car lights night"),
    (["bandeirantes"], "Rodovia dos Bandeirantes"),
    (["anhanguera"], "Rodovia Anhanguera"),
    (["rodovia", "transito", "congestionamento", "pedagio", "ipva"], "highway traffic São Paulo"),
    (["hospital", "saude", "upa", "dengue", "vacina", "surto"], "hospital Brazil"),
    (["escola", "aula", "enem", "educacao", "aluno"], "classroom Brazil school"),
    (["vagas", "emprego", "concurso", "trabalho"], "job interview office"),
    (["coleta", "lixo", "reciclagem"], "garbage truck Brazil"),
    (["agua", "sabesp", "dae"], "water tap"),
    (["energia", "luz", "apagao", "cpfl"], "power lines electricity Brazil"),
    (["iptu", "imposto", "prefeitura", "prefeito", "camara", "vereador"], "Brazilian real money"),
    (["tarcisio", "governo de sao paulo", "alesp"], "Palácio dos Bandeirantes"),
    (["itupeva"], "Itupeva"),
    (["jundiai"], "Jundiaí"),
    (["louveira"], "Louveira"),
    (["vinhedo"], "Vinhedo"),
    (["cabreuva"], "Cabreúva"),
    (["jarinu"], "Jarinu"),
]


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def get(url, headers=UA, limite=12_000_000, timeout=20):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limite), r.geturl()


def url_real(link):
    """Converte o link do Google Noticias no endereco da materia."""
    if "news.google.com" not in link:
        return link
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(link, interval=1)
        if (r.get("status") or r.get("success")) and r.get("decoded_url"):
            return r["decoded_url"]
        print("  decoder sem url:", str(r)[:160])
    except Exception as e:
        print("  decoder:", str(e)[:120])
    return None


def imagens_da_pagina(url):
    corpo, final = get(url, limite=3_000_000)
    pag = corpo.decode("utf-8", "ignore")
    achadas = []
    for prop in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
        for m in re.finditer(r"<meta[^>]+>", pag, re.I):
            tag = m.group(0)
            if re.search(r'(property|name)\s*=\s*["\']' + re.escape(prop) + r'["\']', tag, re.I):
                c = re.search(r'content\s*=\s*["\']([^"\']+)["\']', tag, re.I)
                if c:
                    achadas.append(urllib.parse.urljoin(final, html.unescape(c.group(1).strip())))
    saida = []
    for u in achadas:
        orig = re.sub(r"-\d{2,4}x\d{2,4}(?=\.(jpe?g|png|webp)\b)", "", u, flags=re.I)  # WordPress: versao original
        for v in (orig, u):
            if v not in saida:
                saida.append(v)
    return saida


def hd(im):
    return max(im.size) >= MIN_LONGO and min(im.size) >= MIN_CURTO


def salvar(dados, nome):
    im = Image.open(io.BytesIO(dados))
    im.load()
    if not hd(im):
        print("  abaixo de HD:", im.size)
        return None
    im = im.convert("RGB")
    if im.width > MAX_LARG:
        im = im.resize((MAX_LARG, round(im.height * MAX_LARG / im.width)), Image.LANCZOS)
    im.save(os.path.join(PASTA, nome), "JPEG", quality=85, optimize=True)
    return f"{im.width}x{im.height}"


def foto_materia(p, nome):
    real = url_real(p["link"])
    if not real:
        return None
    print("  materia:", real[:120])
    try:
        cands = imagens_da_pagina(real)
        print("  imagens:", len(cands), cands[:2])
    except Exception as e:
        print("  pagina:", str(e)[:120]); return None
    for u in cands[:6]:
        try:
            dados, _ = get(u)
            tam = salvar(dados, nome)
            if tam:
                return {"foto": nome, "credito": f"Foto: {p['fonte'] or urllib.parse.urlparse(real).netloc}",
                        "foto_tipo": "materia", "foto_tamanho": tam, "materia_url": real}
        except Exception as e:
            print("  imagem:", str(e)[:120])
    return None


def termos(p):
    t = norm(p["titulo"])
    lista = [busca for chaves, busca in TEMAS if any(k in t for k in chaves)]
    return lista or ["Jundiaí"]


# ilustrativa nunca mostra autoridade, evento politico ou pintura (evita associar pessoa real ao fato)
EVITAR = ["governador", "tarcisio", "prefeito", "secretari", "deputad", "vereador", "ministro", "presidente",
          "cerimonia", "entrega", "evento", "inauguracao", "visita", "reuniao", "painting", "pintura", "oil on canvas",
          "portrait", "retrato"]


def limpa(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def ilustrativa(p, nome, usadas):
    for q in termos(p)[:3]:
        api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": q + " filetype:bitmap", "gsrlimit": 20, "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata", "iiurlwidth": MAX_LARG})
        try:
            dados, _ = get(api, headers=UA_WIKI)
            paginas = json.loads(dados).get("query", {}).get("pages", {})
        except Exception as e:
            print("  commons:", str(e)[:120]); continue
        for pg in sorted(paginas.values(), key=lambda x: x.get("index", 99)):
            ii = (pg.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = limpa(meta.get("LicenseShortName", {}).get("value"))
            if ii.get("mime") != "image/jpeg" or ii.get("url") in usadas:
                continue
            if not hd(type("S", (), {"size": (ii.get("width", 0), ii.get("height", 0))})()):
                continue
            if not lic or "fair use" in lic.lower() or "non-free" in lic.lower():
                continue
            texto = norm(" ".join(limpa(meta.get(k, {}).get("value")) for k in
                                  ("ObjectName", "ImageDescription", "Categories", "Artist")) + " " + pg.get("title", ""))
            if any(e in texto for e in EVITAR):
                continue
            try:
                img, _ = get(ii.get("thumburl") or ii["url"], headers=UA_WIKI)
                tam = salvar(img, nome)
            except Exception as e:
                print("  baixar:", str(e)[:120]); continue
            if not tam:
                continue
            autor = limpa(meta.get("Artist", {}).get("value"))[:60] or "autor desconhecido"
            usadas.add(ii.get("url"))
            return {"foto": nome, "credito": f"Imagem ilustrativa: {autor} / Wikimedia Commons ({lic})",
                    "foto_tipo": "ilustrativa", "foto_tamanho": tam, "foto_origem": ii.get("descriptionurl"),
                    "url_ilustrativa": ii.get("url")}
    return None


def main():
    os.makedirs(PASTA, exist_ok=True)
    idx_path = os.path.join(PASTA, "indice.json")
    indice = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    dados = json.load(open("pautas.json"))
    pautas = dados["pautas"]
    topo = sorted(pautas, key=lambda p: -p.get("pontos", 0))[:TOP]
    usadas = {v.get("url_ilustrativa") for v in indice.values() if v}
    novas, manter = 0, {}
    for p in topo:
        chave = hashlib.sha1(b"v4" + re.sub(r"\s+-\s+[^-]+$", "", p["titulo"]).lower().encode()).hexdigest()[:12]
        if chave in indice:
            info = indice[chave]
        elif novas < NOVAS_MAX:
            novas += 1
            print("pauta:", p["titulo"][:90])
            nome = chave + ".jpg"
            info = foto_materia(p, nome) or ilustrativa(p, nome, usadas)
            print("  ->", (info or {}).get("foto_tipo", "sem foto"), (info or {}).get("credito", ""))
            if info is None:
                info = {}
            time.sleep(1)
        else:
            continue
        manter[chave] = info
        if info.get("foto"):
            p.update({k: v for k, v in info.items() if k in ("foto", "credito", "foto_tipo", "foto_tamanho", "materia_url")})
    # remove imagens de pautas que sairam da lista
    referenciadas = {i.get("foto") for i in manter.values() if i}
    for f in os.listdir(PASTA):
        if f.endswith(".jpg") and f not in referenciadas:
            os.remove(os.path.join(PASTA, f))
    json.dump(manter, open(idx_path, "w"), ensure_ascii=False, indent=1)
    json.dump(dados, open("pautas.json", "w"), ensure_ascii=False, indent=1)
    print(f"fotos: {len(referenciadas)} na lista, {novas} pautas novas processadas")


if __name__ == "__main__":
    main()
