# -*- coding: utf-8 -*-
"""Compoe um banner novo (texto em PT) reaproveitando as letras das texturas do jogo."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import banner
import numpy as np
from PIL import Image, ImageFilter

def biblioteca(fontes, f=None):
    """fontes = [(num, idx_dourada, idx_branca, texto)] -> {char: (dourada, branca)}"""
    lib = {}
    for num, ig, ib, txt in fontes:
        _, B = banner.carrega(num, ib, f)
        _, G = banner.carrega(num, ig, f) if ig is not None else (None, None)
        itens, _, _ = banner.mapear(B, txt)
        for c, x0, x1 in itens:
            if c in lib: continue
            lib[c] = (None if G is None else G[:, x0:x1].copy(), B[:, x0:x1].copy())
    return lib

def ajusta_brilho(mask_alpha, sigma, ganho, cor_bgr):
    """Recria uma variante de brilho a partir da silhueta nitida."""
    b = np.asarray(Image.fromarray(mask_alpha).filter(ImageFilter.GaussianBlur(sigma)), dtype=np.float32)
    inten = np.clip(b * ganho, 0, 255)
    out = np.zeros(mask_alpha.shape + (4,), dtype=np.uint8)
    out[..., 3] = inten.astype(np.uint8)
    for k in range(3):
        out[..., k] = np.clip(inten * cor_bgr[k], 0, 255).astype(np.uint8)
    return out

def ajusta_params(mask_alpha, alvo):
    """Estima (sigma, ganho, cor) que levam a silhueta ate a variante original."""
    src = Image.fromarray(mask_alpha)
    melhor = None
    for s in [x / 2 for x in range(1, 31)]:
        b = np.asarray(src.filter(ImageFilter.GaussianBlur(s)), dtype=np.float32)
        den = (b * b).sum()
        if den <= 0: continue
        k = (b * alvo[..., 3]).sum() / den
        err = np.abs(b * k - alvo[..., 3]).mean()
        if melhor is None or err < melhor[0]: melhor = (err, s, k)
    err, s, k = melhor
    a = alvo[..., 3].astype(np.float32)
    den = (a * a).sum()
    cor = [float((alvo[..., c].astype(np.float32) * a).sum() / den) for c in range(3)]
    return s, k, cor, err

def compor(lib, texto, gap, espaco, folga_orn, centro, forma, orn_g, orn_b):
    """Monta as matrizes (dourada, branca) do texto novo com ornamentos."""
    seq = [c for c in texto]
    larg = 0; itens = []
    for i, c in enumerate(seq):
        if c == ' ': larg += espaco; continue
        g, b = lib[c]
        itens.append((larg, c))
        larg += b.shape[1] + gap
    larg -= gap
    lo = orn_b.shape[1]
    total = lo + folga_orn + larg + folga_orn + lo
    x0 = int(round(centro - total / 2))
    G = np.zeros(forma, dtype=np.uint8); B = np.zeros(forma, dtype=np.uint8)
    def cola(dst, src, x):
        xa = max(0, x); xb = min(dst.shape[1], x + src.shape[1])
        s = src[:, xa - x: xb - x]
        alvo = dst[:, xa:xb]
        m = s[..., 3] > alvo[..., 3]
        alvo[m] = s[m]
    cola(G, orn_g, x0); cola(B, orn_b, x0)
    base = x0 + lo + folga_orn
    for dx, c in itens:
        g, b = lib[c]
        cola(G, g, base + dx); cola(B, b, base + dx)
    xf = base + larg + folga_orn
    cola(G, orn_g, xf); cola(B, orn_b, xf)
    return G, B


def biblioteca_janela(fontes, lim, folga=12, f=None):
    """Como biblioteca(), mas para faixas com brilho embutido: guarda uma
    janela larga em volta de cada letra (o halo vem junto).

    fontes = [(num, idx, texto)] -> {char: (janela, deslocamento_do_nucleo, largura_do_nucleo)}
    """
    lib = {}
    for num, i, txt in fontes:
        _, A = banner.carrega(num, i, f)
        chars = [c for c in txt if c != " "]
        segs = banner.segmentos_forcado(A, lim, len(chars))
        if len(segs) != len(chars): raise SystemExit("nao separou %d/%d em %d/%d" % (len(segs), len(chars), num, i))
        for c, (x0, x1) in zip(chars, segs):
            if c in lib: continue
            win, dentro = banner.recorta(A, x0, x1, folga)
            lib[c] = (win, dentro, x1 - x0)
    return lib


def metrica_janela(A, texto, lim):
    """gap entre nucleos, largura do espaco e folga ate o ornamento."""
    import numpy as np
    chars = [c for c in texto if c != " "]
    segs = banner.segmentos_forcado(A, lim, len(chars))
    gaps = []; esp = []; antes = None; k = 0
    for c in texto:
        if c == " ": antes = "e"; continue
        if k > 0:
            g = segs[k][0] - segs[k-1][1]
            (esp if antes == "e" else gaps).append(g)
        antes = None; k += 1
    letras = [s for c, s in zip(chars, segs) if c != "*"]
    orn = [s for c, s in zip(chars, segs) if c == "*"]
    folga_orn = letras[0][0] - orn[0][1]
    return segs, int(np.median(gaps)), int(np.median(esp)) if esp else 20, folga_orn


def compor_janela(lib, texto, gap, espaco, folga_orn, area, forma):
    """Monta a faixa nova colando as janelas com mistura 'maximo'.

    area = (x_inicial, x_final) do espaco util entre os ornamentos.
    Se o texto nao couber, ele e condensado na horizontal -- e o mesmo
    recurso que os artistas usaram nos idiomas de frase longa.
    """
    import numpy as np
    from PIL import Image
    letras = [c for c in texto if c != "*"]
    larg = 0; pos = []
    for c in letras:
        if c == " ": larg += espaco; continue
        pos.append((larg, c)); larg += lib[c][2] + gap
    larg -= gap
    bloco = np.zeros((forma[0], larg + 80, 4), dtype=np.uint8)
    def cola(dst, c, x):
        win, dentro, _ = lib[c]
        xa = x - dentro; ini = 0; fim = win.shape[1]
        if xa < 0: ini = -xa; xa = 0
        xb = xa + (fim - ini)
        if xb > dst.shape[1]: fim -= xb - dst.shape[1]; xb = dst.shape[1]
        if fim <= ini: return
        src = win[:, ini:fim]
        alvo = dst[:, xa:xb]
        m = src[..., 3] > alvo[..., 3]
        alvo[m] = src[m]
    for dx, c in pos: cola(bloco, c, 40 + dx)
    disp = area[1] - area[0]
    if larg > disp:
        esc = disp / larg
        nb = np.asarray(Image.fromarray(bloco, "RGBA").resize(
            (max(1, int(round(bloco.shape[1] * esc))), bloco.shape[0]), Image.LANCZOS))
        bloco = nb; larg = int(round(larg * esc)); borda = int(round(40 * esc))
    else:
        borda = 40
    out = np.zeros(forma, dtype=np.uint8)
    x0 = int(round(area[0] + (disp - larg) / 2)) - borda
    xa = max(0, x0); ini = xa - x0
    xb = min(out.shape[1], x0 + bloco.shape[1])
    out[:, xa:xb] = bloco[:, ini:ini + (xb - xa)]
    cola(out, "*", area[0] - folga_orn - lib["*"][2])
    cola(out, "*", area[1] + folga_orn)
    return out


def estilo_brilho(A, lim_core=190):
    """Aprende o estilo de uma faixa com brilho embutido.

    Devolve (sigma, ganho, cor_interna_por_linha, cor_do_brilho).
    """
    import numpy as np
    from PIL import Image, ImageFilter
    core = (A[..., 3] >= lim_core)
    src = Image.fromarray((core * 255).astype("uint8"))
    alvo = A[..., 3].astype(np.float32)
    melhor = None
    for sg in [x / 2 for x in range(1, 31)]:
        b = np.asarray(src.filter(ImageFilter.GaussianBlur(sg)), dtype=np.float32)
        den = (b * b).sum()
        if den <= 0: continue
        fora = ~core
        den = (b[fora] * b[fora]).sum()
        if den <= 0: continue
        k = (b[fora] * alvo[fora]).sum() / den
        err = np.abs(np.maximum(core * 255, np.clip(k * b, 0, 255)) - alvo).mean()
        if melhor is None or err < melhor[0]: melhor = (err, sg, k)
    err, sg, k = melhor
    linhas = np.zeros((A.shape[0], 3), dtype=np.float32)
    for y in range(A.shape[0]):
        m = core[y]
        if m.sum() >= 3: linhas[y] = A[y][m][..., :3].mean(0)
    ys = np.nonzero(linhas.any(1))[0]
    for y in range(A.shape[0]):
        if not linhas[y].any(): linhas[y] = linhas[min(max(y, ys[0]), ys[-1])]
    halo = (~core) & (A[..., 3] > 40)
    cor_halo = A[halo][..., :3].mean(0) if halo.sum() else np.array([255., 255., 255.])
    return sg, k, linhas, cor_halo, err


def pinta_brilho(mask, sigma, ganho, linhas, cor_halo):
    """Aplica o estilo aprendido sobre uma silhueta nova."""
    import numpy as np
    from PIL import Image, ImageFilter
    core = mask > 127
    b = np.asarray(Image.fromarray((core * 255).astype("uint8")).filter(
        ImageFilter.GaussianBlur(sigma)), dtype=np.float32)
    glow = np.clip(ganho * b, 0, 255)
    alpha = np.maximum(core * 255, glow)
    out = np.zeros(mask.shape + (4,), dtype=np.uint8)
    out[..., 3] = alpha.astype(np.uint8)
    # dentro da letra vale a cor da propria letra; fora, a cor do halo
    cor = np.where(core[..., None], linhas[:, None, :], cor_halo[None, None, :])
    out[..., :3] = np.clip(cor, 0, 255).astype(np.uint8)
    return out
