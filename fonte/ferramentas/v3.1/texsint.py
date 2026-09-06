# -*- coding: utf-8 -*-
"""Síntese de texturas de texto a partir de uma fonte TTF, imitando o estilo do original.

Para as famílias em que as letras do jogo são renderizações (borradas/coloridas) de uma
fonte conhecida (Times New Roman), é mais fiel renderizar o texto novo com a própria
fonte e aplicar o mesmo acabamento: contorno, desfoque e cor por linha (núcleo/contorno)
medidos no par (texto original, textura original).

uso: novo = sintetiza(a_orig, "TEXTO ES", "TEXTO PT", fonte, claro=170)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _render(texto, fonte, tam, xscale=1.0, W=4096, H=1024):
    font = ImageFont.truetype(fonte, int(tam))
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).text((100, 100), texto, font=font, fill=255)
    a = np.asarray(im)
    ys = np.nonzero(a.any(1))[0]; xs = np.nonzero(a.any(0))[0]
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if abs(xscale - 1.0) > 1e-3:
        im2 = Image.fromarray(a).resize((max(1, int(round(a.shape[1] * xscale))), a.shape[0]), Image.LANCZOS)
        a = np.asarray(im2)
    return a


def _bbox(m):
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    return int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1


def _dilata(m, r):
    if r <= 0: return m.copy()
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r and (dx or dy):
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def _blur(a, s):
    if s <= 0: return a.astype(np.float32)
    return np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))).astype(np.float32)


def _coloca(mask_small, shape, x0, y0):
    out = np.zeros(shape[:2], dtype=np.uint8)
    h, w = mask_small.shape
    ya, xa = max(0, y0), max(0, x0)
    yb, xb = min(shape[0], y0 + h), min(shape[1], x0 + w)
    out[ya:yb, xa:xb] = mask_small[ya - y0:yb - y0, xa - x0:xb - x0]
    return out


def sintetiza(a_orig, texto_es, texto_pt, fonte, claro=170, rows=None, centro=True, lim_alpha=60, debug=None):
    """Devolve RGBA do tamanho de a_orig com texto_pt no estilo de a_orig."""
    a = a_orig.copy()
    if rows is not None:
        a[:rows[0]] = 0; a[rows[1]:] = 0
    alpha = a[..., 3].astype(np.float32)
    lum = a[..., :3].astype(np.float32).mean(2)
    op = alpha > lim_alpha
    core = op & (lum > claro)
    if core.sum() < 50: core = op & (lum > np.percentile(lum[op], 60))
    # silhueta inteira (alfa forte) para medir tamanho; o contorno é descontado depois do ajuste
    forte = alpha > 128
    X0, X1, Y0, Y1 = _bbox(forte)
    H0 = Y1 - Y0; W0 = X1 - X0
    r1 = _render(texto_es, fonte, 100)
    best = None
    for r in (0, 1, 2, 3, 4, 6, 8):
        tam = 100.0 * max(4, H0 - 2 * r) / r1.shape[0]
        r_es0 = _render(texto_es, fonte, tam)
        xscale = max(1, W0 - 2 * r) / r_es0.shape[1]
        r_es = _render(texto_es, fonte, tam, xscale)
        es_mask = _coloca((r_es > 127), a.shape, X0 + r, Y0 + r)
        d = _dilata(es_mask, r).astype(np.uint8) * 255
        for s in (0, 1, 2, 3, 4, 6):
            syn = _blur(d, s)
            g = alpha[op].mean() / max(1.0, syn[op].mean()) if op.any() else 1.0
            err = np.abs(np.clip(syn * g, 0, 255) - alpha).mean()
            if best is None or err < best[0]: best = (err, r, s, g, tam, xscale)
    err, r, s, g, tam, xscale = best
    Y0 = Y0 + r
    # perfis de cor por linha: núcleo (claro) e resto (contorno/sombra)
    Hh = a.shape[0]
    def perfil(mask):
        p = [None] * Hh
        for y in range(Hh):
            if mask[y].sum() >= 3: p[y] = np.median(a[y][mask[y]][..., :3], axis=0)
        ys = [k for k in range(Hh) if p[k] is not None]
        for y in range(Hh):
            if p[y] is None: p[y] = p[min(ys, key=lambda k: abs(k - y))] if ys else np.array([200, 200, 200])
        return p
    pc = perfil(core); ps = perfil(op & ~core)
    # texto novo
    r_pt = _render(texto_pt, fonte, tam, xscale)
    if r_pt.shape[1] > a.shape[1] - 4:
        r_pt = _render(texto_pt, fonte, tam, xscale * (a.shape[1] - 4) / r_pt.shape[1])
    x0 = (X0 + X1) // 2 - r_pt.shape[1] // 2 if centro else X0
    x0 = max(0, min(x0, a.shape[1] - r_pt.shape[1]))
    pt_mask = _coloca((r_pt > 127), a.shape, x0, Y0)
    pt_soft = _coloca(r_pt, a.shape, x0, Y0).astype(np.float32)
    d = _dilata(pt_mask, r).astype(np.uint8) * 255
    syn_alpha = np.clip(_blur(d, s) * g, 0, 255)
    # núcleo suave: antialias do próprio render
    core_n = pt_soft > 127
    out = np.zeros_like(a_orig)
    out[..., 3] = syn_alpha.astype(np.uint8)
    for y in range(Hh):
        sel = syn_alpha[y] > 0
        if not sel.any(): continue
        out[y][sel, :3] = ps[y]
        cn = core_n[y]
        out[y][cn, :3] = pc[y]
    # mistura no antialias do núcleo: interpola entre cor do contorno e do núcleo pela cobertura
    cov = (pt_soft / 255.0)[..., None]
    borda = (pt_soft > 20) & (pt_soft <= 127)
    for y in range(Hh):
        b = borda[y]
        if b.any():
            out[y][b, :3] = (np.array(ps[y]) * (1 - cov[y][b]) + np.array(pc[y]) * cov[y][b]).astype(np.uint8)
    if debug:
        ys_ = np.nonzero((syn_alpha > 128).any(1))[0]
        print("   sintese: fonte %.1f xscale %.2f contorno %d blur %d ganho %.2f erro %.1f | altura orig %d nova %d" % (
            tam, xscale, r, s, g, err, H0, (ys_.max() - ys_.min() + 1) if len(ys_) else -1))
    return out
