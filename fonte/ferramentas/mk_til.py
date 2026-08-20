# -*- coding: utf-8 -*-
"""Constroi ã õ Ã Õ para o atlas 33 (grade 32x32) do arquivo 02771."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import g1t, fonte_glifos as F
import numpy as np
from PIL import Image

# (linha, coluna) na grade do atlas 33
CEL = dict(A_grave=(0,0), A_circ=(0,2), A_dier=(0,3), N_til=(0,14),
           O_circ=(1,1), O_dier=(1,2), a_circ=(1,12), a_dier=(1,13),
           n_til=(2,8), o_circ=(2,11), o_dier=(2,12))

TIL_MIN = (3, 10)    # faixa de linhas do til em ñ
TIL_MAI = (0, 6)     # faixa de linhas do til em Ñ

def recorta_til(blk, y0, y1):
    faixa = blk[y0:y1]
    bb = F.ink_bbox(faixa)
    x0, ty0, x1, ty1 = bb
    return faixa[ty0:ty1, x0:x1], y0 + ty0

def monta(base, til, til_y, limpa_ate):
    """base = celula com o corpo da letra; apaga o acento antigo e cola o til."""
    out = base.copy()
    out[:limpa_ate] = 0
    bb = F.ink_bbox(out)
    cx = (bb[0] + bb[2]) // 2
    th, tw = til.shape[:2]
    x = max(0, min(32 - tw, cx - tw // 2))
    out[til_y:til_y+th, x:x+tw] = np.maximum(out[til_y:til_y+th, x:x+tw], til)
    return out

def novos_glifos(d):
    g = g1t.parse(d)
    t33, a33 = F.tex_array(d, g, 33)
    tmin, ymin = recorta_til(F.get_cell(a33, *CEL['n_til']), *TIL_MIN)
    tmai, ymai = recorta_til(F.get_cell(a33, *CEL['N_til']), *TIL_MAI)
    novos = {
        'a_til': (CEL['a_dier'], monta(F.get_cell(a33, *CEL['a_dier']), tmin, ymin, 11)),
        'o_til': (CEL['o_dier'], monta(F.get_cell(a33, *CEL['o_dier']), tmin, ymin, 11)),
        'A_til': (CEL['A_dier'], monta(F.get_cell(a33, *CEL['A_dier']), tmai, ymai, 8)),
        'O_til': (CEL['O_dier'], monta(F.get_cell(a33, *CEL['O_dier']), tmai, ymai, 8)),
    }
    return t33, a33, novos
