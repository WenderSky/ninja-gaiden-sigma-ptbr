# -*- coding: utf-8 -*-
"""Monta glifos acentuados para os banners (Ç, Õ, Ã) que nao existem nas texturas.

O sinal e recortado da fonte serifada do proprio jogo (atlas 02771/34),
redimensionado para a letra do banner e pintado com a cor da propria letra.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import g1t, fonte_glifos as F, banner
import numpy as np
from PIL import Image

_ATLAS = None
def _atlas():
    global _ATLAS
    if _ATLAS is None:
        d = open(r"D:\ng_trad_work\fonte\02771.bin", "rb").read()
        g = g1t.parse(d)
        _ATLAS = F.tex_array(d, g, 34)[1]
    return _ATLAS

def _glifo(y0, y1, k):
    a = _atlas(); sub = a[y0:y1]
    x0, x1 = banner.segmentos(sub)[k]
    return a[y0:y1, x0:x1]

# (linha do atlas, indice, faixa de linhas do sinal, largura da letra base no atlas)
SINAIS = {
    "til":     dict(cel=(128, 167, 19), linhas=(1, 7), base=23),   # de Õ, base = O
    "cedilha": dict(cel=(128, 167, 7), linhas=(32, 39), base=22),  # de Ç, base = C
    "circunflexo": dict(cel=(128, 167, 10), linhas=(0, 8), base=21),  # de Ê, base = E
}

def sinal(nome, larg_letra):
    s = SINAIS[nome]
    gl = _glifo(*s["cel"])
    faixa = gl[s["linhas"][0]:s["linhas"][1]]
    bb = F.ink_bbox(faixa)
    peca = faixa[bb[1]:bb[3], bb[0]:bb[2], 3]        # so o alfa
    escala = larg_letra / s["base"]
    nw = max(2, int(round(peca.shape[1] * escala)))
    nh = max(2, int(round(peca.shape[0] * escala)))
    return np.asarray(Image.fromarray(peca).resize((nw, nh), Image.LANCZOS))

def cor_da_letra(letra, topo=True, n=6):
    """Cor por coluna, tirada das linhas de tinta mais proximas da borda.

    Usa so o miolo (alfa alto) para nao pegar a cor lavada da borda serrilhada.
    """
    m = letra[..., 3] > 200
    if not m.any(): m = letra[..., 3] > 100
    ys = np.nonzero(m.any(1))[0]
    faixa = ys[:n] if topo else ys[-n:]
    nucleo = letra[faixa][m[faixa]][..., :3].mean(0)
    porcol = np.tile(nucleo, (letra.shape[1], 1))
    for x in range(letra.shape[1]):
        col = np.nonzero(m[:, x])[0]
        if len(col) == 0: continue
        sel = col[:n] if topo else col[-n:]
        porcol[x] = letra[sel, x, :3].mean(0)
    return nucleo, porcol

def acentua(letra, nome, folga=1):
    """Devolve a letra com o sinal aplicado (mesma largura, tela mais alta se preciso)."""
    out = letra.copy()
    m = letra[..., 3] > 40
    ys = np.nonzero(m.any(1))[0]
    xs = np.nonzero(m.any(0))[0]
    lw = xs.max() - xs.min() + 1
    sg = sinal(nome, lw)
    nucleo, porcol = cor_da_letra(letra, topo=(nome != "cedilha"))
    cx = (xs.min() + xs.max()) // 2
    x = max(0, min(out.shape[1] - sg.shape[1], cx - sg.shape[1] // 2))
    if nome in ("til", "circunflexo"):
        y = ys.min() - folga - sg.shape[0]
    else:
        y = ys.max() - 1
    y = max(0, min(out.shape[0] - sg.shape[0], y))
    alvo = out[y:y+sg.shape[0], x:x+sg.shape[1]]
    troca = sg > alvo[..., 3]
    alvo[..., 3][troca] = sg[troca]
    cols = porcol[x:x+sg.shape[1]]
    for k in range(3):
        canal = alvo[..., k]
        base = np.broadcast_to(cols[:, k], sg.shape)
        canal[troca] = np.clip(base[troca] * sg[troca] / 255.0, 0, 255).astype(np.uint8)
    return out


def tira_acento(letra, topo_cap):
    """Remove o sinal de cima (ex.: Ó -> O), apagando tudo acima da altura de caixa alta."""
    out = letra.copy()
    out[:topo_cap] = 0
    return out

def topo_de(letra, lim=40):
    m = letra[..., 3] > lim
    return int(np.nonzero(m.any(1))[0].min())
