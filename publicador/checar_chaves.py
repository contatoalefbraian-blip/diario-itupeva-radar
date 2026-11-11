"""Checagem semanal das chaves da Meta. Falha (e o GitHub manda e-mail ao dono) se alguma chave
estiver invalida ou a menos de 20 dias de vencer. Nunca imprime os tokens."""
import datetime as dt, json, os, sys, urllib.parse, urllib.request

LIMITE = dt.timedelta(days=20)


def debug(tok):
    url = "https://graph.facebook.com/v21.0/debug_token?" + urllib.parse.urlencode({"input_token": tok, "access_token": tok})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read()).get("data", {})
    except Exception as e:
        return {"erro": str(e)}


problemas = []
agora = dt.datetime.now(dt.timezone.utc)
for nome in ("META_TOKEN", "META_FB_TOKEN"):
    tok = os.environ.get(nome, "")
    if not tok:
        problemas.append(f"{nome}: ausente"); continue
    d = debug(tok)
    if not d.get("is_valid"):
        problemas.append(f"{nome}: invalida ({d.get('erro') or d.get('error', {}).get('message')})"); continue
    for campo, rotulo in (("expires_at", "vence"), ("data_access_expires_at", "acesso aos dados expira")):
        t = d.get(campo)
        if t:
            quando = dt.datetime.fromtimestamp(t, dt.timezone.utc)
            print(f"{nome}: {rotulo} em {quando:%d/%m/%Y}")
            if quando - agora < LIMITE:
                problemas.append(f"{nome}: {rotulo} em {quando:%d/%m/%Y}. Gere uma nova chave e atualize o secret.")
        else:
            print(f"{nome}: {rotulo}: nunca")
if problemas:
    print("ATENCAO:\n" + "\n".join(problemas)); sys.exit(1)
print("Chaves OK.")
