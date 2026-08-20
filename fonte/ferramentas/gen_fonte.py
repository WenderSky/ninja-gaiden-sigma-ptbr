# -*- coding: utf-8 -*-
"""Gera fonte_ptbr.json: as celulas ã õ Ã Õ ja prontas, em base64.

Sempre monta a partir de fonte/02771.bin (copia PRISTINA do bloco),
para o resultado nao depender de quantas vezes o patch foi aplicado.
"""
import sys, os, json, base64, zlib
sys.path.insert(0, os.path.dirname(__file__))
import g1t, mk_til, mk_ordinal, fonte_glifos as F

PRISTINO = r"D:\ng_trad_work\fonte\02771.bin"
SAIDA = r"D:\ng_trad_work\fonte_ptbr.json"

d = open(PRISTINO, "rb").read()
t33, a33, novos = mk_til.novos_glifos(d)
novos.update(mk_ordinal.novos(d))
larg = t33['w']
base = t33['data']          # offset do inicio dos pixels dentro do bloco descomprimido

linhas = []                 # [offset_absoluto, base64] por linha de 32 px
for nome, ((r, c), blk) in novos.items():
    for y in range(32):
        px = a33[r*32 + y, c*32:(c+1)*32]        # linha original (para conferir)
        off = base + ((r*32 + y) * larg + c*32) * 4
        linhas.append([off, base64.b64encode(blk[y].tobytes()).decode(),
                       base64.b64encode(px.tobytes()).decode()])

json.dump({"arquivo": 2771, "textura": 33, "linhas": linhas},
          open(SAIDA, "w", encoding="utf-8"))
print("fonte_ptbr.json: %d linhas de pixels (%d glifos)" % (len(linhas), len(novos)))
print("offset base da textura 33 no bloco:", base, "| tam bloco:", len(d))
