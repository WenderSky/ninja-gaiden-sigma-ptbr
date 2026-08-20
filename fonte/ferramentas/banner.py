# -*- coding: utf-8 -*-
"""Recompoe faixas de texto (banners) do menu reaproveitando as letras
ja desenhadas nas texturas do proprio jogo.

Cada letra e recortada com folga e colada com mistura 'maximo', o que
preserva o brilho/gradiente das variantes borradas.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import dbx, g1t
import numpy as np

LIM = 20          # limiar de alfa para considerar "tinta"

def carrega(num, idx, f=None, original=True):
    d = dbx.get(num, f, original=original); g = g1t.parse(d)
    t = [x for x in g['tex'] if x['i'] == idx][0]
    assert t['fmt'] == 1
    a = np.frombuffer(d[t['data']:t['data']+t['w']*t['h']*4], dtype=np.uint8).reshape(t['h'], t['w'], 4)
    return t, a.copy()

def segmentos(a, lim=LIM):
    col = (a[..., 3] > lim).any(0)
    segs = []; ini = None
    for x in range(len(col)):
        if col[x] and ini is None: ini = x
        elif not col[x] and ini is not None: segs.append((ini, x)); ini = None
    if ini is not None: segs.append((ini, len(col)))
    return segs

def faixa_y(a, lim=LIM):
    ys = np.nonzero((a[..., 3] > lim).any(1))[0]
    return int(ys.min()), int(ys.max()) + 1

def mapear(a, texto, lim=LIM):
    """Casa os segmentos com o texto ('*' = ornamento, ' ' = espaco).

    Devolve (lista de (char, x0, x1), gap_medio, largura_do_espaco).
    """
    segs = segmentos(a, lim)
    chars = [c for c in texto if c != ' ']
    if len(segs) != len(chars):
        raise SystemExit("segmentos=%d chars=%d -> %s" % (len(segs), len(chars), segs))
    itens = list(zip(chars, [s[0] for s in segs], [s[1] for s in segs]))
    # medir gaps entre letras vizinhas (sem espaco no meio) e a largura do espaco
    gaps = []; espacos = []
    k = 0; antes = None
    for c in texto:
        if c == ' ':
            antes = 'espaco'; continue
        if k > 0:
            g = itens[k][1] - itens[k-1][2]
            (espacos if antes == 'espaco' else gaps).append(g)
        antes = None; k += 1
    return itens, (int(np.median(gaps)) if gaps else 8), (int(np.median(espacos)) if espacos else 20)

def recorta(a, x0, x1, folga):
    """Janela da letra com folga lateral (para nao cortar o brilho)."""
    xa = max(0, x0 - folga); xb = min(a.shape[1], x1 + folga)
    return a[:, xa:xb].copy(), x0 - xa

def compoe(alvo_shape, pecas, lim=LIM):
    """pecas = [(janela, x_destino_da_borda_esquerda_da_letra, deslocamento_interno)]"""
    out = np.zeros(alvo_shape, dtype=np.uint8)
    for win, xdest, dentro in pecas:
        xa = xdest - dentro
        xb = xa + win.shape[1]
        if xa < 0: win = win[:, -xa:]; xa = 0
        if xb > out.shape[1]: win = win[:, :out.shape[1]-xa]; xb = out.shape[1]
        alvo = out[:, xa:xb]
        m = win[..., 3] > alvo[..., 3]
        alvo[m] = win[m]
    return out


def segmentos_forcado(a, lim, esperado):
    """Como segmentos(), mas quebra os blocos colados ate bater a contagem.

    Serve para as faixas em que o brilho embutido gruda letras vizinhas:
    o corte sai na coluna de menor tinta dentro do bloco mais largo.
    """
    import numpy as np
    segs = segmentos(a, lim)
    col = (a[..., 3] > lim).sum(0)
    tentativas = 0
    while len(segs) < esperado and tentativas < 40:
        tentativas += 1
        k = max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])
        x0, x1 = segs[k]
        m = 6
        if x1 - x0 < 2 * m + 2: break
        janela = col[x0 + m:x1 - m]
        corte = x0 + m + int(np.argmin(janela))
        segs = segs[:k] + [(x0, corte), (corte, x1)] + segs[k + 1:]
    return segs
