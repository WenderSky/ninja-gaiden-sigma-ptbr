# -*- coding: utf-8 -*-
"""Monta os glifos ordinais º e ª repintando ý e ÿ (nunca usados em EN/FR/DE/IT/ES).

Base: as letras 'o' e 'a' do atlas ASCII (02771/1), reduzidas e elevadas
ate a altura dos digitos.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import g1t, fonte_glifos as F
import numpy as np
from PIL import Image

ESCALA = 0.56

def cel_ascii(cp):
    """(linha, coluna) do caractere no atlas 1, que comeca no espaco (0x20)."""
    i = cp - 0x20
    return i // 16, i % 16

def topo_digito(a1):
    d = F.get_cell(a1, *cel_ascii(ord("1")))
    return int(np.nonzero((d[..., 3] > 20).any(1))[0].min())

def monta(a1, letra_cp):
    base = F.get_cell(a1, *cel_ascii(letra_cp))
    bb = F.ink_bbox(base)
    rec = base[bb[1]:bb[3], bb[0]:bb[2]]
    nw = max(3, int(round(rec.shape[1] * ESCALA)))
    nh = max(3, int(round(rec.shape[0] * ESCALA)))
    peq = np.asarray(Image.fromarray(rec, "RGBA").resize((nw, nh), Image.LANCZOS))
    out = np.zeros_like(base)
    y = topo_digito(a1)
    x = bb[0]
    out[y:y+nh, x:x+nw] = peq
    return out

def novos(d):
    g = g1t.parse(d)
    a1 = F.tex_array(d, g, 1)[1]
    return {"ord_masc": ((3, 3), monta(a1, ord("o"))),    # celula do ý
            "ord_fem":  ((3, 4), monta(a1, ord("a")))}    # celula do ÿ
