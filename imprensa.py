"""Monitor da Imprensa Oficial de Itupeva (Diario Oficial do Municipio).

Le as edicoes novas pela API publica do DOSP, extrai o texto do PDF e separa os atos
que podem dar materia: contratacao direta (dispensa, inexigibilidade, emergencia),
aditivos, valores altos, leis, decretos, concursos e processos seletivos.
Nomeacoes e exoneracoes entram so como contagem (politica de Itupeva: sempre com o Alef).

Saidas (lidas pela Friday nas edicoes):
- registro/imprensa/AAAA-MM-DD-edNNNN.md  relatorio de cada edicao
- registro/imprensa/alertas.json          atos marcados dos ultimos 30 dias
- registro/imprensa/vistos.json           edicoes ja lidas

Uso: python3 imprensa.py            (le as edicoes novas)
     python3 imprensa.py --teste N  (so imprime as N ultimas edicoes, nao grava nada)
"""
import base64, json, os, re, subprocess, sys, time, unicodedata, urllib.request

API = "https://dosp.com.br/api/index.php/dioe.js/4924?callback=dioe"
UA = {"User-Agent": "Mozilla/5.0 (radar Diario de Itupeva)"}
PASTA = "registro/imprensa"
VALOR_ALTO = 500_000      # R$: acima disso o ato e marcado como valor alto
DIAS_ALERTAS = 30
MAX_EDICOES = 5           # por rodada (a primeira rodada nao reprocessa o historico todo)

CABECALHOS = ("LEI ", "LEI COMPLEMENTAR", "DECRETO", "PORTARIA", "EXTRATO", "AUTORIZACAO DE CONTRATACAO",
              "AVISO", "EDITAL", "TERMO ADITIVO", "ADITAMENTO", "HOMOLOGACAO", "RATIFICACAO", "ATA ",
              "RESOLUCAO", "COMUNICADO", "CONVOCACAO", "AUTO DE INFRACAO", "DESPACHO")
MARCAS = {
    "contratacao direta": ["contratacao direta", "dispensa de licitacao", "dispensa eletronica", "inexigibilidade",
                           "emergencial", "situacao de emergencia", "art. 75", "art. 74"],
    "aditivo": ["termo aditivo", "aditamento", "acrescimo", "prorrogacao de prazo", "reequilibrio", "reajuste contratual"],
    "concurso/selecao": ["concurso publico", "processo seletivo", "convocacao de aprovados", "classificacao final"],
    "audiencia publica": ["audiencia publica", "consulta publica"],
}
NOMEACOES = ["nomeia", "nomear", "exonera", "exonerar"]


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def get(url, tentativas=3):
    for i in range(tentativas):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(10)


def edicoes():
    raw = get(API).decode("utf-8", "replace")
    return json.loads(raw[raw.index("(") + 1: raw.rindex(")")]).get("data", [])


def link_de(e):
    return e.get("link") or "https://dosp.com.br/exibe_do.php?i=" + base64.b64encode(str(e["iddo"]).encode()).decode()


def texto_por_pagina(pdf):
    open("/tmp/ed.pdf", "wb").write(pdf)
    t = subprocess.run(["pdftotext", "/tmp/ed.pdf", "-"], capture_output=True, text=True).stdout
    return unicodedata.normalize("NFKC", t).split("\f")


def valores(t):
    out = []
    for v in re.findall(r"R\$\s*([\d.]+,\d{2})", t):
        try:
            out.append(float(v.replace(".", "").replace(",", ".")))
        except ValueError:
            pass
    return out


def atos(paginas):
    """Divide o texto em atos pelos cabecalhos em caixa alta. Devolve (pagina, titulo, texto)."""
    lista, atual = [], None
    for n, pag in enumerate(paginas, 1):
        for linha in pag.splitlines():
            l = linha.strip()
            if not l or l.startswith(("IMPRENSA OFICIAL", "Diário Oficial assinado", "Publicação Oficial",
                                      "Município de Itupeva - SP", "Diário Oficial")) or re.match(r"^(Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)-?feira?,? \d", l):
                continue
            nl = norm(l).upper()
            if l.isupper() and len(l) >= 6 and nl.startswith(CABECALHOS):
                atual = [n, l, []]
                lista.append(atual)
            elif atual:
                atual[2].append(l)
    return [(p, tit, " ".join(corpo)) for p, tit, corpo in lista]


def analisar(e, paginas):
    marcados, nomeacoes = [], 0
    for pag, titulo, corpo in atos(paginas):
        t = norm(titulo + " " + corpo)
        if any(x in t for x in NOMEACOES) and norm(titulo).startswith("portaria"):
            nomeacoes += 1
            continue
        tags = [m for m, termos in MARCAS.items() if any(x in t for x in termos)]
        nt = norm(titulo)
        if nt.startswith("decreto"):
            tags.append("decreto")
        elif nt.startswith("lei"):
            tags.append("lei")
        vs = valores(corpo)
        maior = max(vs) if vs else 0
        if maior >= VALOR_ALTO:
            tags.append("valor alto")
        if not tags:
            continue
        peso = (3 if "contratacao direta" in tags else 0) + (2 if "aditivo" in tags else 0) \
            + (3 if "valor alto" in tags else 0) + (1 if maior >= 5 * VALOR_ALTO else 0) + 1
        marcados.append({
            "data": e["data"], "edicao": e["edicao_do"], "pagina": pag, "titulo": titulo[:160],
            "marcas": tags, "maior_valor": round(maior, 2), "peso": peso,
            "trecho": re.sub(r"\s+", " ", corpo)[:700], "link": link_de(e) + f"#page={pag}",
        })
    marcados.sort(key=lambda a: (-a["peso"], -a["maior_valor"]))
    return marcados, nomeacoes


def relatorio(e, marcados, nomeacoes):
    linhas = [f"# Imprensa Oficial de Itupeva · edição {e['edicao_do']} · {e['data']}",
              f"PDF: {link_de(e)} ({e.get('pgtotal')} páginas)", "",
              "Dados de fonte oficial, mas o texto abaixo é extraído automaticamente: confira no PDF antes de usar.",
              "Matéria que sugira irregularidade (valor exagerado, contratação suspeita) e nomeações vão SEMPRE ao Alef.",
              "Não publicar nomes, CPFs ou matrículas de pessoas físicas (LGPD).", ""]
    if nomeacoes:
        linhas.append(f"- Portarias de nomeação/exoneração: {nomeacoes} (política de Itupeva: só com o Alef)\n")
    if not marcados:
        linhas.append("Nada marcado nesta edição.")
    for a in marcados:
        v = f" · maior valor R$ {a['maior_valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if a["maior_valor"] else ""
        linhas.append(f"## [{', '.join(a['marcas'])}] {a['titulo']}\npágina {a['pagina']}{v} · {a['link']}\n\n{a['trecho']}\n")
    return "\n".join(linhas)


def main():
    teste = "--teste" in sys.argv
    eds = edicoes()
    if teste:
        n = int(sys.argv[sys.argv.index("--teste") + 1]) if len(sys.argv) > sys.argv.index("--teste") + 1 else 3
        for e in eds[:n]:
            marcados, nom = analisar(e, texto_por_pagina(get(link_de(e))))
            print(relatorio(e, marcados, nom)[:6000], "\n" + "=" * 60)
        return
    os.makedirs(PASTA, exist_ok=True)
    arq_vistos, arq_alertas = f"{PASTA}/vistos.json", f"{PASTA}/alertas.json"
    vistos = json.load(open(arq_vistos)) if os.path.exists(arq_vistos) else []
    alertas = json.load(open(arq_alertas)) if os.path.exists(arq_alertas) else []
    novas = [e for e in eds if e["iddo"] not in vistos][:MAX_EDICOES]
    if not vistos:  # primeira rodada: so a ultima edicao; o resto do historico fica marcado como visto
        vistos = [e["iddo"] for e in eds[1:200]]
        novas = eds[:1]
    for e in reversed(novas):
        try:
            marcados, nom = analisar(e, texto_por_pagina(get(link_de(e))))
        except Exception as erro:
            print("falha na edicao", e.get("edicao_do"), erro)
            continue
        open(f"{PASTA}/{e['data']}-ed{e['edicao_do']}.md", "w").write(relatorio(e, marcados, nom))
        alertas = [a for a in alertas if a["edicao"] != e["edicao_do"]] + marcados
        vistos.append(e["iddo"])
        print("edicao", e["edicao_do"], e["data"], "| marcados:", len(marcados), "| nomeacoes:", nom)
    limite = time.strftime("%Y-%m-%d", time.gmtime(time.time() - DIAS_ALERTAS * 86400))
    alertas = sorted([a for a in alertas if a["data"] >= limite], key=lambda a: (a["data"], -a["peso"]), reverse=True)
    json.dump(alertas, open(arq_alertas, "w"), ensure_ascii=False, indent=1)
    json.dump(vistos[-400:], open(arq_vistos, "w"))


if __name__ == "__main__":
    main()
