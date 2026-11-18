"""Radar do Diario de Itupeva: le o RSS do Google Noticias, monta a lista de pautas do dia (pautas.json e pautas.md),
classifica por regiao e relevancia e destaca as urgentes. Quando surge uma urgente nova, abre uma issue
"URGENTE" neste repositorio, e essa issue aciona automaticamente a tarefa Urgente do Claude.
So usa a biblioteca padrao do Python. Usa o GITHUB_TOKEN do proprio Actions (sem segredos extras).
Opcional: CLAUDE_FIRE_URL e CLAUDE_FIRE_TOKEN, se a tarefa for configurada com gatilho por API.
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

BUSCAS = [  # (consulta, categoria)
    ("Itupeva", "itupeva"),
    ("Itupeva acidente OR incêndio OR morte OR polícia", "itupeva"),
    ("Itupeva prefeitura OR câmara OR saúde OR escola", "itupeva"),
    ("Itupeva falta de água OR sem energia OR alagamento", "itupeva"),
    ("Jundiaí", "regiao"),
    ("site:olharitupeva.com.br", "itupeva"),
    ("site:avozjundiai.com", "regiao"),
    ("Louveira OR Cabreúva OR Jarinu OR Vinhedo OR \"Várzea Paulista\"", "regiao"),
    ("Defesa Civil Jundiaí OR Itupeva", "regiao"),
    ("Bandeirantes Jundiaí OR Anhanguera Jundiaí OR \"Dom Gabriel\"", "regiao"),
    ("previsão do tempo Jundiaí", "regiao"),
    ("governo de São Paulo OR Tarcísio OR Alesp", "estado"),
    ("estado de São Paulo trânsito OR chuva OR saúde", "estado"),
    ("pedágio OR \"free flow\" OR concessão rodovia São Paulo", "estado"),
    ("imposto OR tributação OR alíquota governo federal", "brasil"),
    ("corte de gastos OR orçamento OR arcabouço fiscal governo", "brasil"),
    ("Câmara dos Deputados OR Senado aprova OR STF decide", "brasil"),
    ("", "brasil"),  # destaques do Google Noticias Brasil
]
# Feeds oficiais das prefeituras (sites que nao aparecem no Google Noticias). So os que aceitam leitura
# automatica: em 17/11/2026, Itupeva, Louveira, Cabreuva, Campo Limpo Paulista e Jarinu recusam (403)
# e nao sao contornados; para elas entram os Alertas do Google abaixo. (url, categoria, nome da fonte)
FEEDS_OFICIAIS = [
    ("https://jundiai.sp.gov.br/noticias/feed/", "regiao", "Prefeitura de Jundiaí"),
    # Alertas do Google em RSS (conta do Diario, criados em 17/11/2026) para as prefeituras que recusam
    # leitura automatica. A fonte de cada item e o site da noticia (dominio), nao o Google: e pista para a Friday.
    ("https://www.google.com/alerts/feeds/15379187071713204985/11482850764597301117", "itupeva", ""),  # "Prefeitura de Itupeva"
    ("https://www.google.com/alerts/feeds/15379187071713204985/15056536669026236059", "regiao", ""),   # "Prefeitura de Louveira"
    ("https://www.google.com/alerts/feeds/15379187071713204985/9171094383665045425", "regiao", ""),    # "Prefeitura de Cabreúva"
    ("https://www.google.com/alerts/feeds/15379187071713204985/15893226086898182290", "regiao", ""),   # "Prefeitura de Campo Limpo Paulista"
    ("https://www.google.com/alerts/feeds/15379187071713204985/3066979184139052867", "regiao", ""),    # "Prefeitura de Jarinu"
    # os mesmos municipios, so o que sai no proprio site da prefeitura
    ("https://www.google.com/alerts/feeds/15379187071713204985/8460752825947769775", "itupeva", "Prefeitura de Itupeva"),    # site:itupeva.sp.gov.br
    ("https://www.google.com/alerts/feeds/15379187071713204985/12269723186349176403", "regiao", "Prefeitura de Louveira"),    # site:louveira.sp.gov.br
    ("https://www.google.com/alerts/feeds/15379187071713204985/13905411093742048813", "regiao", "Prefeitura de Cabreúva"),    # site:cabreuva.sp.gov.br
    ("https://www.google.com/alerts/feeds/15379187071713204985/9222473183842410541", "regiao", "Prefeitura de Campo Limpo Paulista"),  # site:campolimpopaulista.sp.gov.br
    ("https://www.google.com/alerts/feeds/15379187071713204985/7981437324247305373", "regiao", "Prefeitura de Jarinu"),     # site:jarinu.sp.gov.br
    # Camara de Itupeva (site sem RSS): concursos e aprovacoes relevantes. Politica de Itupeva: sempre com o Alef.
    ("https://www.google.com/alerts/feeds/15379187071713204985/8065251760119095712", "itupeva", "Câmara de Itupeva"),  # site:itupeva.sp.leg.br
]
PESO = {"itupeva": 3, "regiao": 2, "estado": 1, "brasil": 1}
LOCAIS = ["itupeva", "jundiai", "louveira", "cabreuva", "jarinu", "vinhedo", "varzea paulista",
          "campo limpo paulista", "bandeirantes", "anhanguera", "dom gabriel"]
URGENTES = ["acidente", "morre", "morte", "morto", "morta", "incendio", "fogo", "alagamento", "enchente",
            "deslizamento", "temporal", "vendaval", "interdit", "bloquead", "falta de agua", "sem agua",
            "sem energia", "apagao", "desaparecid", "defesa civil", "alerta", "operacao", "tiroteio",
            "homicidio", "assassin", "explos", "surto", "suspensao das aulas"]
# Assuntos prioritarios da grade do Diario (somam pontos)
PRIORIDADES = {
    "clima": ["previsao do tempo", "chuva", "frio", "calor", "temporal", "frente fria", "onda de calor"],
    "transito": ["transito", "rodovia", "bandeirantes", "anhanguera", "dom gabriel", "interdi", "congestionamento",
                 "pedagio", "free flow", "concessao"],
    "prefeitura": ["prefeitura de itupeva", "camara de itupeva", "prefeito", "vereador"],
    "servico": ["vagas", "emprego", "vacina", "inscric", "concurso", "iptu", "ipva", "coleta", "agua", "energia"],
    "politica": ["governo de sao paulo", "governo federal", "governo lula", "lula", "haddad", "tarcisio", "alesp",
                 "assembleia", "congresso", "camara dos deputados", "senado", "stf", "imposto", "tributa", "aliquota",
                 "corte de gastos", "orcamento", "arcabouco", "secretario", "ministro"],
    "seguranca": ["policia", "preso", "presa", "operacao", "golpe"],
}
# Fontes (analise de 7 a 14/11/2026, 512 historias de Itupeva e regiao):
# agregadores que repetem noticia 14h+ depois dos jornais: ignorados
IGNORAR = ["novo dia", "novodianoticias", "portal sorocaba",
           "aprovaconcursos", "meupreparatorio", "ideablog"]  # os 3 ultimos: anuncios de cursos e blogs (Alertas do Google)
# fontes que costumam dar a noticia primeiro: +2 pontos (pesa nos urgentes)
RAPIDAS = ["g1", "prefeitura de"]
JANELA_HORAS = 3
ESTADO = "vistos.json"


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def ler_feed(q):
    base = {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
    if q:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:1d", **base})
    else:
        url = "https://news.google.com/rss?" + urllib.parse.urlencode(base)
    req = urllib.request.Request(url, headers={"User-Agent": "DiarioItupevaRadar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def ler_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "DiarioItupevaRadar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _texto(s):
    """Tira tags e entidades HTML (os Alertas do Google mandam o titulo com <b>)."""
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def _link_real(href):
    """Os Alertas do Google embrulham o link em google.com/url?...&url=LINK."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
    return q.get("url", [href])[0]


def _dominio(url):
    d = urllib.parse.urlparse(url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def itens(xml_bytes, fonte_padrao=""):
    raiz = ET.fromstring(xml_bytes)
    for it in raiz.iter("item"):  # RSS (Google Noticias, sites oficiais)
        titulo = _texto(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        fonte = (it.findtext("source") or "").strip() or fonte_padrao
        try:
            quando = parsedate_to_datetime(it.findtext("pubDate")).timestamp()
        except Exception:
            quando = time.time()
        yield {"titulo": titulo, "link": link, "fonte": fonte, "quando": quando}
    A = "{http://www.w3.org/2005/Atom}"
    for it in raiz.iter(A + "entry"):  # Atom (Alertas do Google)
        titulo = _texto(it.findtext(A + "title"))
        el = it.find(A + "link")
        link = _link_real(el.get("href", "")) if el is not None else ""
        fonte = fonte_padrao or _dominio(link)
        try:
            from datetime import datetime
            quando = datetime.fromisoformat((it.findtext(A + "published") or it.findtext(A + "updated")).replace("Z", "+00:00")).timestamp()
        except Exception:
            quando = time.time()
        yield {"titulo": titulo, "link": link, "fonte": fonte, "quando": quando}


# assuntos que nunca sao urgentes (evitam issue e execucao a toa)
NAO_URGENTE = ["horoscopo", "signo", "novela", "receita", "bbb", "loteria", "mega-sena", "previsao do signo",
               "participa de estudo", "relembra", "anos apos", "aniversario de"]


def eh_urgente(titulo):
    t = norm(titulo)
    if any(x in t for x in NAO_URGENTE):
        return False
    return any(l in t for l in LOCAIS) and any(u in t for u in URGENTES)


def post(url, dados, headers):
    req = urllib.request.Request(url, data=json.dumps(dados).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read()[:300]


def chave_titulo(t):
    t = re.sub(r"\s+-\s+[^-]+$", "", t)  # tira " - Veiculo" do fim
    return norm(t)[:120]


EDICOES = [(7, 35), (10, 35), (16, 35)]  # horario (Brasilia) em que a Friday le a lista


def inicio_janela(agora):
    """Inicio da janela de pautas: a edicao anterior a que vai ler a lista agora.
    A lista so muda de janela 40 min depois de cada edicao comecar, para a Friday ler a lista completa."""
    ref = agora - 3 * 3600 - 40 * 60          # relogio de Brasilia, com 40 min de folga
    dia = int(ref // 86400) * 86400
    marcos = [dia - 86400 + h * 3600 + m * 60 for h, m in EDICOES] + [dia + h * 3600 + m * 60 for h, m in EDICOES]
    return max(t for t in marcos if t <= ref) + 3 * 3600   # volta para UTC


def main(xml_teste=None):
    vistos = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}
    agora = time.time()
    janela = 0 if xml_teste else inicio_janela(agora)
    feeds = [(xml_teste, "itupeva", "")] if xml_teste else []
    if not xml_teste:
        for q, cat in BUSCAS:
            try:
                feeds.append((ler_feed(q), cat, ""))
            except Exception as e:
                print("falha no feed:", q, e)
        for url, cat, nome in FEEDS_OFICIAIS:
            try:
                feeds.append((ler_url(url), cat, nome))
            except Exception as e:
                print("falha no feed oficial:", nome, e)
    pautas = {}
    for xb, cat, nome in feeds:
        for i in itens(xb, nome):
            if any(x in norm(i["fonte"]) for x in IGNORAR):
                continue
            if i["quando"] < janela and not (eh_urgente(i["titulo"]) and agora - i["quando"] <= JANELA_HORAS * 3600):
                continue
            k = chave_titulo(i["titulo"])
            if cat != "itupeva" and "itupeva" in norm(i["titulo"]):
                cat = "itupeva"
            p = pautas.setdefault(k, {**i, "categoria": cat, "fontes": set(), "urgente": eh_urgente(i["titulo"])})
            p["fontes"].add(i["fonte"])
            if PESO[cat] > PESO[p["categoria"]]:
                p["categoria"] = cat
    lista = []
    for k, p in pautas.items():
        p["fontes"] = sorted(f for f in p["fontes"] if f)
        t = norm(p["titulo"])
        p["assuntos"] = [a for a, termos in PRIORIDADES.items() if any(x in t for x in termos)]
        p["pontos"] = (PESO[p["categoria"]] * 2 + min(len(p["fontes"]), 4) + 2 * len(p["assuntos"])
                       + (5 if p["urgente"] else 0)
                       + (2 if any(norm(f) == "g1" or norm(f).startswith(tuple(RAPIDAS)) for f in p["fontes"]) else 0))
        p["hora"] = time.strftime("%d/%m %H:%M", time.gmtime(p["quando"] - 3 * 3600))
        lista.append(p)
    lista = [p for p in lista if p["categoria"] != "brasil" or p["assuntos"] or len(p["fontes"]) > 1]
    lista.sort(key=lambda p: (-p["pontos"], -p["quando"]))
    # cota por categoria: Itupeva nao pode empurrar estado e Brasil para fora da lista
    COTA = {"itupeva": 35, "regiao": 25, "estado": 15, "brasil": 15}
    usados = {c: 0 for c in COTA}
    escolhidos = []
    for p in lista:
        if usados[p["categoria"]] < COTA[p["categoria"]]:
            usados[p["categoria"]] += 1
            escolhidos.append(p)
    lista = escolhidos
    json.dump({"gerado": time.strftime("%d/%m/%Y %H:%M", time.gmtime(agora - 3 * 3600)),
               "desde": time.strftime("%d/%m/%Y %H:%M", time.gmtime(janela - 3 * 3600)) if janela else "",
               "pautas": lista},
              open("pautas.json", "w"), ensure_ascii=False, indent=1)
    with open("pautas.md", "w") as f:
        f.write("# Pautas do radar desde a edicao anterior, mais relevantes primeiro\n\n")
        for p in lista:
            f.write(f"- {'URGENTE ' if p['urgente'] else ''}[{p['categoria']}] ({p['pontos']} pts"
                    f"{', ' + ', '.join(p['assuntos']) if p['assuntos'] else ''}) {p['titulo']} "
                    f"({', '.join(p['fontes'])}, {p['hora']}) {p['link']}\n")
    novos = [p for p in lista if p["urgente"] and agora - p["quando"] <= JANELA_HORAS * 3600
             and chave_titulo(p["titulo"]) not in vistos]
    for p in novos:
        vistos[chave_titulo(p["titulo"])] = int(agora)
    vistos = {k: v for k, v in vistos.items() if agora - v < 3 * 86400}
    json.dump(vistos, open(ESTADO, "w"), ensure_ascii=False, indent=0)
    print(f"{len(lista)} pautas, {len(novos)} urgentes novas")
    if not novos:
        return []
    texto = "Radar do Diario de Itupeva captou possiveis urgencias (nao verificadas):\n" + "\n".join(
        f"- {p['titulo']} | {', '.join(p['fontes'])} | {p['link']}" for p in novos)
    print(texto)
    if xml_teste:
        return novos
    repo, gh = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if repo and gh:
        corpo = ("Pistas captadas pelo radar (NAO verificadas). A tarefa Urgente do Claude confere antes de "
                 "qualquer publicacao.\n\n" + "\n".join(
                     f"- {p['titulo']}\n  Fontes: {', '.join(p['fontes'])} | {p['hora']}\n  {p['link']}" for p in novos))
        titulo = "URGENTE: " + re.sub(r"\s+-\s+[^-]+$", "", novos[0]["titulo"])[:180]
        print("issue:", post(f"https://api.github.com/repos/{repo}/issues",
                             {"title": titulo, "body": corpo, "labels": ["urgente"]},
                             {"Authorization": "Bearer " + gh, "Accept": "application/vnd.github+json"}))
    if os.environ.get("CLAUDE_FIRE_URL") and os.environ.get("CLAUDE_FIRE_TOKEN"):
        print("claude:", post(os.environ["CLAUDE_FIRE_URL"], {"text": texto}, {
            "Authorization": "Bearer " + os.environ["CLAUDE_FIRE_TOKEN"],
            "anthropic-beta": "experimental-cc-routine-2026-04-01",
            "anthropic-version": "2023-06-01"}))
    return novos


if __name__ == "__main__":
    main()
