"""Gerador de artes 4:5 no padrão do Diário de Itupeva."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KIT = os.environ.get("KIT", "/tmp/kit")
W, H = 1080, 1350
FD = KIT + "/osf/fonts/ttf/"
BOLD, XB, REG = FD + "OpenSauceOne-Bold.ttf", FD + "OpenSauceOne-ExtraBold.ttf", FD + "OpenSauceOne-Regular.ttf"
BLUE, NAVY, BLACK, WHITE = (8, 147, 254), (28, 45, 58), (0, 0, 0), (255, 255, 255)
RED, DRED = (224, 36, 36), (90, 11, 11)
F = lambda p, s: ImageFont.truetype(p, s)


def _logo(white_letters):
    im = Image.open(KIT + "/logo.png").convert("RGBA")
    im = im.crop(im.getbbox())
    if white_letters:
        px = im.load(); w, h = im.size
        xs, ys = [], []
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r, g, b, a = px[x, y]
                if a > 200 and b > 200 and r < 60:
                    xs.append(x); ys.append(y)
        bx0, bx1, by0, by1 = min(xs) - 6, max(xs) + 6, min(ys) - 6, max(ys) + 6
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a and not (bx0 <= x <= bx1 and by0 <= y <= by1) and max(r, g, b) < 90:
                    px[x, y] = (255, 255, 255, a)
    lw = int(W * 0.20)
    return im.resize((lw, int(im.size[1] * lw / im.size[0])), Image.LANCZOS)


LOGO_W, LOGO_D = _logo(True), _logo(False)


def photo_bg(path):
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x0, y0, x0 + W, y0 + H))


def brand_bg(icon=None):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        c = tuple(int((BLUE[i] * 0.55 + NAVY[i] * 0.45) * (1 - t) + NAVY[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for k in range(-H, W, 70):
        od.line([(k, 0), (k + H, H)], fill=(255, 255, 255, 10), width=18)
    if icon:
        icon(od, W // 2, int(H * 0.30), (255, 255, 255, 46))
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    return im


def icon_pin(d, x, y, c):
    r = 120
    d.ellipse([x - r, y - r - 40, x + r, y + r - 40], fill=c)
    d.polygon([(x - r * .86, y + r * .5 - 40), (x + r * .86, y + r * .5 - 40), (x, y + r * 2.1 - 40)], fill=c)


def icon_info(d, x, y, c):
    d.ellipse([x - 150, y - 150, x + 150, y + 150], outline=c, width=26)
    d.ellipse([x - 24, y - 100, x + 24, y - 52], fill=c)
    d.rounded_rectangle([x - 22, y - 25, x + 22, y + 95], 11, fill=c)


def icon_road(d, x, y, c):
    d.polygon([(x - 60, y - 170), (x + 60, y - 170), (x + 210, y + 170), (x - 210, y + 170)], fill=c)
    for k in range(4):
        yy = y - 140 + k * 85
        d.rectangle([x - 8 - k * 3, yy, x + 8 + k * 3, yy + 45], fill=(28, 45, 58, 255))


def icon_mail(d, x, y, c):
    d.rounded_rectangle([x - 190, y - 125, x + 190, y + 125], 26, outline=c, width=24)
    d.line([(x - 175, y - 110), (x, y + 15), (x + 175, y - 110)], fill=c, width=24)


def fade(im):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    y0 = int(H * 0.42)
    for y in range(y0, H):
        t = min(1, (y - y0) / (H * 0.28))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * t)))
    return Image.alpha_composite(im.convert("RGBA"), ov)


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            out.append(cur); cur = w
    return out + ([cur] if cur else [])


def band(im, y_mid, lines, f, colors=(BLUE, NAVY), lh=1.12, padx=0):
    d = ImageDraw.Draw(im)
    hb = int(len(lines) * f.size * lh + 56)
    y0 = int(y_mid - hb / 2)
    x0, x1, sk = 85, W - 70, 46
    g = Image.new("RGB", (x1 - x0, hb)); gd = ImageDraw.Draw(g)
    for x in range(g.width):
        t = x / g.width
        gd.line([(x, 0), (x, hb)], fill=tuple(int(colors[0][i] * (1 - t) + colors[1][i] * t) for i in range(3)))
    m = Image.new("L", g.size, 0)
    ImageDraw.Draw(m).polygon([(sk, 0), (g.width, 0), (g.width - sk, hb), (0, hb)], fill=255)
    im.paste(g, (x0, y0), m)
    y = y0 + 28 - int(f.size * 0.06)
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=WHITE)
        y += int(f.size * lh)
    return y0 + hb


def centered(d, y, lines, f, fill=WHITE, lh=1.1):
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=fill)
        y += int(f.size * lh)
    return y


def credito_vertical(im, texto):
    """Credito da foto: minusculo, leve transparencia, na vertical, colado no canto direito (de baixo para cima)."""
    fc = F(REG, 17)
    tmp = ImageDraw.Draw(im)
    tw = int(tmp.textlength(texto, font=fc)) + 4
    layer = Image.new("RGBA", (tw, 26), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((2, 2), texto, font=fc, fill=(255, 255, 255, 150))
    rot = layer.rotate(90, expand=True)
    y = max(int(H * 0.06), int(H * 0.86) - rot.height)
    im.alpha_composite(rot, (W - rot.width - 10, y))


def chrome(im, dark_corner=None, page=None, swipe=False, fonte=None, credito=None):
    if dark_corner is None:
        x0, y0 = int(W * 0.105), int(H * 0.07)
        reg = im.convert("L").crop((x0, y0, x0 + LOGO_W.width, y0 + LOGO_W.height))
        dark_corner = sum(reg.tobytes()) / (reg.width * reg.height) < 140
    logo = LOGO_W if dark_corner else LOGO_D
    im.alpha_composite(logo, (int(W * 0.105), int(H * 0.07)))
    d = ImageDraw.Draw(im)
    fa = F(REG, 18)
    t = "@diariodeitupeva"
    d.text(((W - d.textlength(t, font=fa)) / 2, int(H * 0.935)), t, font=fa, fill=(225, 225, 225))
    if fonte:
        ff = F(REG, 22)
        d.text(((W - d.textlength(fonte, font=ff)) / 2, int(H * 0.905)), fonte, font=ff, fill=(200, 200, 200))
    if credito:
        credito_vertical(im, credito)
    if page:
        fp = F(BOLD, 26); tw = d.textlength(page, font=fp)
        d.rounded_rectangle([W - 75 - tw - 32, int(H * 0.07), W - 75, int(H * 0.07) + 46], 23, fill=(0, 0, 0, 160))
        d.text((W - 75 - tw - 16, int(H * 0.07) + 7), page, font=fp, fill=WHITE)
    if swipe:
        fs = F(BOLD, 28)
        d.text((W - 75 - d.textlength("Arraste ›", font=fs), int(H * 0.89)), "Arraste ›", font=fs, fill=WHITE)


def feed(bg, manchete, sub, out, fonte=None, urgente=False, page=None, swipe=False, credito=None):
    im = fade(bg)
    d = ImageDraw.Draw(im)
    fm = F(BOLD, 64)
    lines = ["URGENTE"] if urgente else wrap(d, manchete.upper(), fm, W - 260)
    assert len(lines) <= 2, ("manchete longa", manchete)
    fm2 = F(XB, 84) if urgente else fm
    band(im, int(H * 0.605), lines, fm2, colors=(RED, DRED) if urgente else (BLUE, NAVY))
    fs = F(REG, 54)
    sl = wrap(d, sub.upper(), fs, W - 200)
    assert len(sl) <= 4, ("subtitulo longo", sub)
    centered(d, int(H * 0.71), sl, fs)
    chrome(im, None, page, swipe, fonte, credito)
    im.convert("RGB").save(out)


def card(titulo, texto, out, page, fonte=None, urgente=False, extra=None):
    im = Image.new("RGBA", (W, H), NAVY + (255,))
    d = ImageDraw.Draw(im)
    fm = F(BOLD, 64)
    yb = band(im, int(H * 0.33), wrap(d, titulo.upper(), fm, W - 260)[:2], fm,
              colors=(RED, DRED) if urgente else (BLUE, NAVY))
    fs = F(REG, 54)
    y = centered(d, yb + 70, wrap(d, texto.upper(), fs, W - 200)[:5], fs)
    if extra:
        fe = F(BOLD, 40)
        centered(d, y + 40, [extra], fe, fill=(150, 205, 255))
    chrome(im, True, page, False, fonte)
    im.convert("RGB").save(out)


def icon_box(d, x, y, c):
    d.polygon([(x, y - 170), (x + 200, y - 70), (x, y + 30), (x - 200, y - 70)], fill=c)
    d.polygon([(x - 200, y - 40), (x - 15, y + 55), (x - 15, y + 200), (x - 200, y + 105)], fill=c)
    d.polygon([(x + 200, y - 40), (x + 15, y + 55), (x + 15, y + 200), (x + 200, y + 105)], fill=c)


def icon_grape(d, x, y, c):
    r = 46
    for row, n in enumerate([4, 3, 2, 1]):
        for k in range(n):
            cx = x + (k - (n - 1) / 2) * r * 2.05
            cy = y - 80 + row * r * 1.8
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    d.line([(x, y - 135), (x + 30, y - 200)], fill=c, width=16)
    d.ellipse([x + 30, y - 225, x + 140, y - 165], fill=c)


def icon_shield(d, x, y, c):
    d.polygon([(x, y - 190), (x + 170, y - 130), (x + 150, y + 60), (x, y + 190), (x - 150, y + 60), (x - 170, y - 130)], fill=c)


def photo_top(path, focus_y=0.0):
    """Foto paisagem: largura inteira no topo, fundo desfocado atrás."""
    src = Image.open(path).convert("RGB")
    base = photo_bg(path).filter(ImageFilter.GaussianBlur(40))
    base = Image.blend(base, Image.new("RGB", (W, H), BLACK), 0.45)
    w2 = W
    h2 = int(src.height * W / src.width)
    sharp = src.resize((w2, h2), Image.LANCZOS)
    m = Image.new("L", (w2, h2), 255)
    md = ImageDraw.Draw(m)
    for y in range(max(0, h2 - 120), h2):
        md.line([(0, y), (w2, y)], fill=int(255 * (h2 - y) / 120))
    base.paste(sharp, (0, int(focus_y)), m)
    return base


ICONS = {"pin": icon_pin, "info": icon_info, "estrada": icon_road, "email": icon_mail,
         "caixa": icon_box, "uva": icon_grape, "escudo": icon_shield, None: None}


def gerar(spec, out):
    """spec: {tipo: feed|card, manchete, sub, fonte?, foto?, credito?, icone?, urgente?, pagina?, arraste?, extra?}
    credito: texto do credito da foto, ex. "Foto: Prefeitura de Itupeva" ou "Imagem ilustrativa: Autor / Wikimedia Commons (CC BY-SA 4.0)"."""
    if spec.get("tipo", "feed") == "card":
        return card(spec["manchete"], spec["sub"], out, spec.get("pagina"), spec.get("fonte"),
                    spec.get("urgente", False), spec.get("extra"))
    if spec.get("foto"):
        im = Image.open(spec["foto"])
        bg = photo_top(spec["foto"], spec.get("desce", 110)) if im.width > im.height * 0.9 else photo_bg(spec["foto"])
    else:
        bg = brand_bg(ICONS.get(spec.get("icone", "pin")))
    feed(bg, spec["manchete"], spec["sub"], out, spec.get("fonte"), spec.get("urgente", False),
         spec.get("pagina"), spec.get("arraste", False), spec.get("credito") if spec.get("foto") else None)


if __name__ == "__main__":
    import json, sys
    specs = json.load(open(sys.argv[1]))
    for i, sp in enumerate(specs if isinstance(specs, list) else [specs], 1):
        o = sp.get("arquivo", f"arte_{i}.png")
        gerar(sp, o); print(o)
