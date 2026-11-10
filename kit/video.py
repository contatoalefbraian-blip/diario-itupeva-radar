"""Video 9:16 narrado do Diario de Itupeva. Uso: python3 video.py roteiro.json saida.mp4
roteiro: {"faixa": ["RESUMO","DA SEMANA"], "data": "02 A 07/11", "blocos": ["ITUPEVA"], "abre": "fala", "fecha": "fala", "noticias": [{"bloco","titulo","sub","fonte","fala"}]}"""
import os, subprocess, sys, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))

W, H = 1080, 1920
KIT = os.environ.get("KIT", "/tmp/kit")
FD = KIT + "/osf/fonts/ttf/"
BOLD = FD + "OpenSauceOne-Bold.ttf"
XB = FD + "OpenSauceOne-ExtraBold.ttf"
REG = FD + "OpenSauceOne-Regular.ttf"
BLUE, NAVY, BLACK, WHITE = (8, 147, 254), (28, 45, 58), (0, 0, 0), (255, 255, 255)
OUT = os.environ.get("VIDEO_TMP", "/tmp/video_tmp")
os.makedirs(OUT, exist_ok=True)

R = json.load(open(sys.argv[1])) if __name__ == "__main__" else {}
DATA = R.get("data", "")
SEGS = R.get("noticias", [])
ABRE = R.get("abre", "")
FECHA = R.get("fecha", "Matérias completas no link da bio. Siga o Diário de Itupeva.")


def font(p, s):
    return ImageFont.truetype(p, s)


def logo_white():
    im = Image.open(KIT + "/logo.png").convert("RGBA")
    im = im.crop(im.getbbox())
    px = im.load()
    w, h = im.size
    # blue box bbox
    xs, ys = [], []
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            r, g, b, a = px[x, y]
            if a > 200 and b > 200 and r < 60:
                xs.append(x); ys.append(y)
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            inside = bx0 - 6 <= x <= bx1 + 6 and by0 - 6 <= y <= by1 + 6
            if a > 0 and not inside and r < 90 and g < 90 and b < 90:
                px[x, y] = (255, 255, 255, a)
    return im


LOGO = logo_white()
LOGO_W = 260
LOGO = LOGO.resize((LOGO_W, int(LOGO.size[1] * LOGO_W / LOGO.size[0])), Image.LANCZOS)


def background():
    bg = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        c = tuple(int(BLACK[i] * (1 - t) + NAVY[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    return bg


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    return lines


def band(img, y0, lines, f, colors=(BLUE, NAVY), pad=34, lh=1.12):
    d = ImageDraw.Draw(img)
    asc = f.size
    hband = int(len(lines) * asc * lh + pad * 2)
    x0, x1, sk = 70, W - 60, 40
    grad = Image.new("RGB", (x1 - x0 + sk, hband))
    gd = ImageDraw.Draw(grad)
    for x in range(grad.size[0]):
        t = x / grad.size[0]
        gd.line([(x, 0), (x, hband)], fill=tuple(int(colors[0][i] * (1 - t) + colors[1][i] * t) for i in range(3)))
    mask = Image.new("L", grad.size, 0)
    ImageDraw.Draw(mask).polygon([(sk, 0), (grad.size[0], 0), (grad.size[0] - sk, hband), (0, hband)], fill=255)
    img.paste(grad, (x0 - sk // 2, y0), mask)
    y = y0 + pad - int(asc * 0.08)
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=WHITE)
        y += int(asc * lh)
    return y0 + hband


def centered(d, y, lines, f, fill=WHITE, lh=1.1):
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=fill)
        y += int(f.size * lh)
    return y


def common(img, page=None):
    img.paste(LOGO, (90, 150), LOGO)
    d = ImageDraw.Draw(img)
    fa = font(REG, 30)
    t = "@diariodeitupeva"
    d.text(((W - d.textlength(t, font=fa)) / 2, 1560), t, font=fa, fill=(220, 220, 220))
    if page:
        fp = font(BOLD, 30)
        tw = d.textlength(page, font=fp)
        d.rounded_rectangle([W - 90 - tw - 36, 168, W - 90, 222], 27, fill=(0, 0, 0))
        d.text((W - 90 - tw - 18, 176), page, font=fp, fill=WHITE)


def slide_open():
    img = background(); d = ImageDraw.Draw(img)
    fb = font(XB, 92)
    yb = band(img, 560, R.get("faixa", ["RESUMO", "DO DIA"]), fb)
    y = centered(d, yb + 40, [DATA], font(BOLD, 54))
    fl = font(BOLD, 46)
    y += 50
    for i, b in enumerate(R.get("blocos", ["ITUPEVA", "REGIÃO", "ESTADO", "BRASIL"])):
        tw = d.textlength(b, font=fl)
        x = (W - 520) / 2
        d.rectangle([x, y, x + 520, y + 78], fill=BLUE if i == 0 else (40, 55, 68))
        d.text(((W - tw) / 2, y + 12), b, font=fl, fill=WHITE)
        y += 96
    common(img)
    return img


def slide_news(s, i, n):
    img = background(); d = ImageDraw.Draw(img)
    fl = font(BOLD, 40)
    tw = d.textlength(s["bloco"], font=fl)
    d.rectangle([(W - tw) / 2 - 30, 520, (W + tw) / 2 + 30, 590], fill=BLUE)
    d.text(((W - tw) / 2, 528), s["bloco"], font=fl, fill=WHITE)
    fm = font(BOLD, 65)
    yb = band(img, 640, wrap(d, s["titulo"].upper(), fm, W - 230), fm)
    fs = font(REG, 54)
    y = centered(d, yb + 50, wrap(d, s["sub"].upper(), fs, W - 190), fs)
    ff = font(REG, 30)
    centered(d, max(y + 40, 1440), [s["fonte"]], ff, fill=(200, 200, 200))
    common(img, f"{i}/{n}")
    return img


def slide_close():
    img = background(); d = ImageDraw.Draw(img)
    fm = font(BOLD, 65)
    yb = band(img, 700, ["MATÉRIAS COMPLETAS", "NO LINK DA BIO"], fm)
    centered(d, yb + 60, ["SIGA @DIARIODEITUPEVA"], font(REG, 54))
    common(img)
    return img


def render(version, final=None):
    from tts import synth
    slides = [("abre", slide_open(), ABRE)]
    for i, s in enumerate(SEGS, 1):
        slides.append((f"n{i}", slide_news(s, i, len(SEGS)), s["fala"]))
    slides.append(("fecha", slide_close(), FECHA))
    clips = []
    for name, img, fala in slides:
        png = f"{OUT}/{name}.png"; img.save(png)
        clip = f"{OUT}/{version}_{name}.mp4"
        if version == "narrado":
            wav = f"{OUT}/{name}.wav"
            dur = synth(fala, wav) + 0.7
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav,
                   "-af", "apad", "-t", f"{dur:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", clip]
        else:
            words = len(fala.split())
            dur = max(3.5, min(7.0, words / 4.0))
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png,
                   "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                   "-t", f"{dur:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", clip]
        subprocess.run(cmd, check=True)
        clips.append(clip)
    lst = f"{OUT}/{version}.txt"
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    final = final or f"resumo_{version}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", final], check=True)
    return final


if __name__ == "__main__":
    print(render("narrado", sys.argv[2] if len(sys.argv) > 2 else None))
