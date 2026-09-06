# -*- coding: utf-8 -*-
"""Composição de texturas de texto reaproveitando as letras já desenhadas.

Fluxo: lib = Biblioteca(lim, claro); lib.add(num, idx, "TEXTO DA TEXTURA") para
cada textura-fonte (segmentação por colunas; com `claro` só o núcleo branco da
letra conta, ignorando sombra/brilho; ' ' é espaço). Depois
compor(lib, "NOVO TEXTO", ref=(num, idx), folga=(esq, dir)) devolve um RGBA do
tamanho da textura de referência, com o novo texto na mesma linha de base,
mesmo espaçamento e mesmo início à esquerda (ou centralizado em `centro`).

Backups dos blocos originais ficam em D:\\ng_trad_work\\fix_v31\\tex_backup e
são a fonte de leitura quando existem (idempotente).
"""
import os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbx, g1t
import numpy as np

LIM = 20
BAK = r"D:\ng_trad_work\fix_v31\tex_backup"
os.makedirs(BAK, exist_ok=True)
_cache = {}
_override = {}   # (num, idx) -> array, para segmentar recortes (ex. só a linha de cima)


def bloco(num):
    if num in _cache:
        return _cache[num]
    p = os.path.join(BAK, "bloco_%05d.bin" % num)
    if os.path.exists(p):
        d = zlib.decompress(open(p, "rb").read())
    else:
        raw = dbx.raw(num)
        open(p, "wb").write(raw)
        d = zlib.decompress(raw)
    _cache[num] = d
    return d


def textura(num, idx):
    d = bloco(num); g = g1t.parse(d)
    t = g['tex'][idx]
    assert t['fmt'] == 1 and t['i'] == idx
    if (num, idx) in _override:
        return t, _override[(num, idx)].copy()
    a = np.frombuffer(d[t['data']:t['data'] + t['w'] * t['h'] * 4], dtype=np.uint8).reshape(t['h'], t['w'], 4)
    return t, a.copy()


def mascara(a, lim=LIM, claro=None):
    m = a[..., 3] > lim
    if claro is not None:
        m &= a[..., :3].astype(np.int16).mean(axis=2) > claro
    return m


def segmentos(a, lim=LIM, claro=None):
    col = mascara(a, lim, claro).any(0)
    segs = []; ini = None
    for x in range(len(col)):
        if col[x] and ini is None: ini = x
        elif not col[x] and ini is not None: segs.append((ini, x)); ini = None
    if ini is not None: segs.append((ini, len(col)))
    return segs


def _quebra(a, segs, esperado, lim, claro):
    segs = list(segs)
    while len(segs) < esperado:
        k = max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])
        x0, x1 = segs[k]
        col = mascara(a[:, x0:x1], lim, claro).sum(0).astype(float)
        m = int(0.2 * (x1 - x0))
        if x1 - x0 - 2 * m < 3: raise SystemExit("nao consigo quebrar segmento %s" % (segs[k],))
        c = x0 + m + int(np.argmin(col[m:x1 - x0 - m]))
        segs[k:k + 1] = [(x0, c), (c, x1)]
    return segs


def _quebra_largura(segs, chars, larguras, padrao=68):
    """Atribui as letras aos segmentos pela largura esperada e divide os blocos colados na proporção."""
    W = [float(larguras.get(c, padrao)) for c in chars]
    n = len(chars)
    escala = sum(x1 - x0 for x0, x1 in segs) / max(1.0, sum(W))
    We = [w * escala for w in W]
    out = []; k = 0
    for si, (x0, x1) in enumerate(segs):
        w = x1 - x0; rem = len(segs) - si - 1
        if si == len(segs) - 1:
            j = n
        else:
            j = k; soma = 0.0
            while j < n - rem:
                if j > k and soma + We[j] * 0.55 > w: break
                soma += We[j]; j += 1
            if j == k: j = k + 1
        grupo = We[k:j]; tot = sum(grupo); x = x0
        for gi, gw in enumerate(grupo):
            xe = x1 if gi == len(grupo) - 1 else x + int(round(w * gw / tot))
            out.append((x, xe)); x = xe
        k = j
    return out


def _junta(segs, esperado):
    segs = list(segs)
    while len(segs) > esperado:
        k = min(range(len(segs) - 1), key=lambda i: segs[i + 1][0] - segs[i][1])
        segs[k:k + 2] = [(segs[k][0], segs[k + 1][1])]
    return segs


class Biblioteca:
    def __init__(self, lim=LIM, claro=None):
        self.lim = lim; self.claro = claro
        self.gl = {}
        self.metr = {}

    def add(self, num, idx, texto, forcar=True, rows=None, larguras=None, padrao=68):
        """rows=(y0, y1): considera só essa faixa de linhas (texturas com duas linhas de texto).
        larguras: dict char->largura esperada; blocos de letras coladas são divididos na proporção."""
        t, a = textura(num, idx)
        if rows is not None:
            a = a.copy(); a[:rows[0]] = 0; a[rows[1]:] = 0
        chars = [c for c in texto if c != ' ']
        segs = [s for s in segmentos(a, self.lim, self.claro) if s[1] - s[0] >= 3]   # ignora pixels soltos
        if len(segs) < len(chars) and larguras is not None:
            segs = _quebra_largura(segs, chars, larguras, padrao)
        if len(segs) < len(chars) and forcar: segs = _quebra(a, segs, len(chars), self.lim, self.claro)
        if len(segs) > len(chars) and forcar: segs = _junta(segs, len(chars))
        if len(segs) != len(chars):
            raise SystemExit("%d/%d: segmentos=%d chars=%d %s" % (num, idx, len(segs), len(chars), segs))
        gaps = []; esp = []; k = 0; antes_esp = False
        for c in texto:
            if c == ' ': antes_esp = True; continue
            if k > 0:
                g = segs[k][0] - segs[k - 1][1]
                (esp if antes_esp else gaps).append(g)
            antes_esp = False
            self.gl.setdefault(c, []).append((num, idx, segs[k][0], segs[k][1], rows))
            k += 1
        ys = np.nonzero(mascara(a, self.lim, self.claro).any(1))[0]
        self.metr[(num, idx, rows) if rows else (num, idx)] = dict(
            gap=int(np.median(gaps)) if gaps else 6, espaco=int(np.median(esp)) if esp else 20,
            y0=int(ys.min()), y1=int(ys.max()) + 1, x0=segs[0][0], x1=segs[-1][1], segs=segs, texto=texto, rows=rows)
        if rows: self.metr.setdefault((num, idx), self.metr[(num, idx, rows)])
        return self.metr[(num, idx, rows) if rows else (num, idx)]

    def add_guiado(self, num, idx, texto, fonte=r"C:\Windows\Fonts\timesbd.ttf", rows=None, refino=0.3,
                   maiusc_grandes=None):
        """Segmentação guiada por uma fonte TTF parecida: as proporções das letras dão o chute
        inicial e cada corte é refinado para a coluna de menos tinta na vizinhança.
        maiusc_grandes: índices de letras (ex. primeira/última) desenhadas maiores (fator 1.35)."""
        from PIL import ImageFont
        t, a = textura(num, idx)
        if rows is not None:
            a = a.copy(); a[:rows[0]] = 0; a[rows[1]:] = 0
        m = mascara(a, self.lim, self.claro)
        col = m.sum(0).astype(float)
        xs = np.nonzero(m.any(0))[0]; X0, X1 = int(xs.min()), int(xs.max()) + 1
        font = ImageFont.truetype(fonte, 100)
        chars = list(texto)
        adv = []
        for k, c in enumerate(chars):
            w = font.getlength(c if c != ' ' else ' ')
            if maiusc_grandes and k in maiusc_grandes: w *= 1.35
            adv.append(w)
        tot = sum(adv); esc = (X1 - X0) / tot
        bordas = [X0]
        for w in adv: bordas.append(bordas[-1] + w * esc)
        segs = []
        for k, c in enumerate(chars):
            if c == ' ': continue
            b0, b1 = bordas[k], bordas[k + 1]
            lw = b1 - b0
            # refina o corte esquerdo e o direito no vale de tinta mais próximo (exceto extremos)
            def vale(b, prev_space, next_space):
                lo = int(max(X0, b - lw * refino)); hi = int(min(X1, b + lw * refino))
                if hi <= lo + 1: return int(b)
                seg = col[lo:hi]
                return lo + int(np.argmin(seg))
            x0 = X0 if k == 0 or (k > 0 and chars[k - 1] == ' ' and False) else vale(b0, False, False)
            x1 = X1 if k == len(chars) - 1 else vale(b1, False, False)
            if k > 0 and chars[k - 1] == ' ':
                # após espaço: começa na primeira coluna com tinta depois do vale
                z = np.nonzero(col[x0:int(b1)] > 0)[0]; x0 = x0 + int(z[0]) if len(z) else x0
            if k < len(chars) - 1 and chars[k + 1] == ' ':
                z = np.nonzero(col[int(b0):x1] > 0)[0]; x1 = int(b0) + int(z[-1]) + 1 if len(z) else x1
            if x1 <= x0: x1 = x0 + 1
            segs.append((int(x0), int(x1)))
        # registra como add()
        gaps = []; esp = []; k = 0; antes_esp = False
        for c in texto:
            if c == ' ': antes_esp = True; continue
            if k > 0:
                g = segs[k][0] - segs[k - 1][1]
                (esp if antes_esp else gaps).append(g)
            antes_esp = False
            self.gl.setdefault(c, []).append((num, idx, segs[k][0], segs[k][1], rows))
            k += 1
        ys = np.nonzero(m.any(1))[0]
        key = (num, idx, rows) if rows else (num, idx)
        self.metr[key] = dict(gap=int(np.median(gaps)) if gaps else 0, espaco=int(np.median(esp)) if esp else 20,
                              y0=int(ys.min()), y1=int(ys.max()) + 1, x0=segs[0][0], x1=segs[-1][1], segs=segs,
                              texto=texto, rows=rows)
        if rows: self.metr.setdefault((num, idx), self.metr[key])
        return self.metr[key]

    def clonar(self, num, idx_src, idx_dst):
        """Reaproveita a segmentação de uma variante nítida para outra variante (borrada) do mesmo texto."""
        for key in list(self.metr):
            if key[:2] == (num, idx_src):
                self.metr[(num, idx_dst) + key[2:]] = dict(self.metr[key])
        for c, lst in list(self.gl.items()):
            for (n, i, x0, x1, rows) in list(lst):
                if (n, i) == (num, idx_src): lst.append((num, idx_dst, x0, x1, rows))

    def pega(self, c, pref=None, folga=(0, 0), limpar=0):
        """(janela com folga, origem, deslocamento do núcleo dentro da janela).
        limpar=k: zera o que não é núcleo nem sombra própria (núcleo deslocado até k px p/ baixo-direita)."""
        if c not in self.gl: raise KeyError(c)
        opts = self.gl[c]
        prefs = [] if pref is None else (pref if isinstance(pref, list) else [pref])
        esc = None
        for p in prefs:
            for o in opts:
                if (o[0], o[1]) == p: esc = o; break
            if esc: break
        num, idx, x0, x1, rows = esc or opts[0]
        t, a = textura(num, idx)
        xa = max(0, x0 - folga[0]); xb = min(a.shape[1], x1 + folga[1])
        win = a[:, xa:xb].copy()
        if rows is not None:
            win[:rows[0]] = 0; win[rows[1]:] = 0
        if limpar:
            full = mascara(win, self.lim, self.claro)
            core = full.copy()
            core[:, :x0 - xa] = False; core[:, x1 - xa:] = False   # só o núcleo da própria letra
            viz = full & ~core                                      # núcleo das letras vizinhas
            # halo/sombra própria: dilatação em todas as direções até `limpar` px
            keep = core.copy(); k = int(limpar)
            for dy in range(-k, k + 1):
                for dx in range(-k, k + 1):
                    if dy or dx:
                        keep |= np.roll(np.roll(core, dy, 0), dx, 1)
            vizd = viz.copy()
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    vizd |= np.roll(np.roll(viz, dy, 0), dx, 1)
            keep &= ~vizd
            win[~keep] = 0
        return win, (num, idx, x0, x1), x0 - xa


def compor(lib, texto, ref, gap=None, espaco=None, inicio=None, centro=None, extras=None, pref=None,
           folga=(0, 0), deslocy=0, limpar=0):
    """extras: dict char -> RGBA ou (RGBA, deslocamento_do_nucleo, folga_dir). Cola com máximo de alfa."""
    m = lib.metr[ref]
    gap = m['gap'] if gap is None else gap
    espaco = m['espaco'] if espaco is None else espaco
    t, a_ref = textura(ref[0], ref[1])
    out = np.zeros_like(a_ref)
    pecas = []
    for c in texto:
        if c == ' ': pecas.append(None); continue
        if extras and c in extras:
            e = extras[c]
            win, dentro, fd = (e[0], e[1], e[2]) if isinstance(e, tuple) else (e, 0, 0)
        else:
            win, _, dentro = lib.pega(c, pref or ref, folga, limpar); fd = folga[1]
        pecas.append((win, dentro, win.shape[1] - dentro - fd))
    largura = 0; first = True
    for p in pecas:
        if p is None: largura += espaco; continue
        if not first: largura += gap
        largura += p[2]; first = False
    x = (centro - largura // 2) if centro is not None else (m['x0'] if inicio is None else inicio)
    first = True
    for p in pecas:
        if p is None: x += espaco; continue
        win, dentro, nw = p
        if not first: x += gap
        if deslocy: win = np.roll(win, deslocy, axis=0)
        xa = x - dentro; xb = xa + win.shape[1]
        if xa < 0: win = win[:, -xa:]; xa = 0
        if xb > out.shape[1]:
            if x + nw > out.shape[1]: raise SystemExit("texto nao cabe: %r em %d" % (texto, out.shape[1]))
            win = win[:, :out.shape[1] - xa]; xb = out.shape[1]
        alvo = out[:, xa:xb]
        msk = win[..., 3] > alvo[..., 3]
        alvo[msk] = win[msk]
        x += nw; first = False
    return out


def compacta(px, passo=4):
    """Deixa a textura mais compressível sem mudar o visual: alfa quantizado em `passo`
    níveis, pixels transparentes zerados. Só se aplica quando o bloco não cabe."""
    px = px.copy()
    a = px[..., 3].astype(np.int32)
    a = (a + passo // 2) // passo * passo
    a[a < 8] = 0
    px[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
    px[px[..., 3] == 0, :3] = 0
    return px


def gravar(num, texturas, modo="teste"):
    """Parte do bloco ATUAL do databin (não do backup), para que gravações sucessivas
    no mesmo bloco se acumulem. O backup do original é garantido por bloco()."""
    bloco(num)                                   # garante o backup do original
    d = bytearray(zlib.decompress(dbx.raw(num))); g = g1t.parse(bytes(d))
    off, comp, unc = dbx.rec(num)
    nc = None
    for passo in (0, 4, 8, 16):
        d2 = bytearray(d)
        for idx, px in texturas.items():
            t = g['tex'][idx]
            assert px.shape == (t['h'], t['w'], 4), (px.shape, t['w'], t['h'])
            p2 = compacta(px, passo) if passo else px
            d2[t['data']:t['data'] + p2.nbytes] = np.ascontiguousarray(p2).tobytes()
        nc = zlib.compress(bytes(d2), 9)
        if len(nc) <= comp:
            if passo: print("  bloco %d: alfa quantizado em %d niveis para caber" % (num, passo))
            break
    ok = len(nc) <= comp
    print("  bloco %d: %d texturas | comp %d/%d %s" % (num, len(texturas), len(nc), comp, "cabe" if ok else "ESTOUROU"))
    if modo == "teste" or not ok: return ok
    f = open(dbx.DB, "r+b"); f.seek(off); f.write(nc + b"\x00" * (comp - len(nc))); f.flush(); os.fsync(f.fileno()); f.close()
    return ok


def reverter(num):
    p = os.path.join(BAK, "bloco_%05d.bin" % num)
    raw = open(p, "rb").read(); off, comp, unc = dbx.rec(num); assert len(raw) == comp
    f = open(dbx.DB, "r+b"); f.seek(off); f.write(raw); f.close(); print("revertido", num)


def previa(arrs, path, fundo=(90, 90, 90), escala=1.0):
    from PIL import Image
    ims = []
    for a in arrs:
        im = Image.fromarray(np.ascontiguousarray(a), "RGBA")
        bg = Image.new("RGBA", im.size, fundo + (255,)); bg.alpha_composite(im); im = bg.convert("RGB")
        if escala != 1.0: im = im.resize((int(im.width * escala), int(im.height * escala)), Image.NEAREST)
        ims.append(im)
    W = max(i.width for i in ims); H = sum(i.height + 4 for i in ims)
    sheet = Image.new("RGB", (W, H), (20, 20, 20)); y = 0
    for i in ims: sheet.paste(i, (0, y)); y += i.height + 4
    sheet.save(path)
    return path


# ---------- acentos sintetizados ----------
def _glifo_fonte(ch, altura, fonte=r"C:\Windows\Fonts\timesbd.ttf"):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(fonte, int(altura * 2.4))
    im = Image.new("L", (int(altura * 6), int(altura * 6)), 0)
    ImageDraw.Draw(im).text((altura, 0), ch, font=font, fill=255)
    a = np.asarray(im); yy = np.nonzero(a.any(1))[0]; xx = np.nonzero(a.any(0))[0]
    return a[yy.min():yy.max() + 1, xx.min():xx.max() + 1]


def _pinta(win, mask, x0, y0, cor, sombra=(1, 1), cor_sombra=(25, 25, 25), opaco=False):
    from PIL import Image
    a = mask.astype(np.int32)
    for (ox, oy, c, alpha) in ((sombra[0], sombra[1], np.array(cor_sombra), 0.85), (0, 0, np.array(cor), 1.0)):
        for y in range(a.shape[0]):
            for x in range(a.shape[1]):
                v = int(a[y, x] * alpha); Y = y0 + y + oy; X = x0 + x + ox
                if v <= 8 or not (0 <= Y < win.shape[0] and 0 <= X < win.shape[1]): continue
                if opaco:
                    win[Y, X, :3] = (win[Y, X, :3].astype(int) * (255 - v) + c * v) // 255
                elif v > win[Y, X, 3]:
                    win[Y, X, :3] = c; win[Y, X, 3] = v
    return win


def com_acento(win, ch, claro=150, frac=0.65, dy=-1, sombra=(1, 1), opaco=False, fonte=None, embaixo=False,
               grosso=0, cor=None, cor_sombra=(25, 25, 25)):
    """Coloca o acento `ch` (ex. '^', '´', '~', '¸') sobre (ou sob) a letra da janela.
    grosso=k engrossa o traço em k px; cor força a cor (padrão: mediana do núcleo da letra)."""
    from PIL import Image
    win = win.copy()
    m = (win[..., 3] > 20) & (win[..., :3].mean(2) > claro)
    if m.sum() < 10:
        m = win[..., 3] > 100
    if m.sum() < 10:
        m = win[..., 3] > 20
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    top, bot = ys.min(), ys.max(); lx0, lx1 = xs.min(), xs.max() + 1
    alt = bot - top + 1
    g = _glifo_fonte(ch, alt, fonte) if fonte else _glifo_fonte(ch, alt)
    lw = max(3, int((lx1 - lx0) * frac)); lh = max(2, int(g.shape[0] * lw / g.shape[1]))
    a = np.asarray(Image.fromarray(g).resize((lw, lh), Image.LANCZOS)).astype(np.int32)
    for _ in range(grosso):
        b = a.copy()
        for dy_, dx_ in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            b = np.maximum(b, np.roll(np.roll(a, dy_, 0), dx_, 1))
        a = b
    if cor is not None:
        x0 = lx0 + ((lx1 - lx0) - lw) // 2
        y0 = (bot + 1 + dy) if embaixo else (top - lh + dy)
        if y0 < 0: a = a[-y0:]; y0 = 0
        return _pinta(win, a, x0, y0, np.array(cor), sombra, cor_sombra, opaco=opaco)
    x0 = lx0 + ((lx1 - lx0) - lw) // 2
    y0 = (bot + 1 + dy) if embaixo else (top - lh + dy)
    if y0 < 0: a = a[-y0:]; y0 = 0
    cor = np.median(win[m][..., :3], axis=0)
    return _pinta(win, a, x0, y0, cor, sombra, opaco=opaco)
