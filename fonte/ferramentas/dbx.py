# -*- coding: utf-8 -*-
"""Leitor do databin do Ninja Gaiden Sigma (Master Collection).

Formato: registros de 32 bytes a partir de 0x13180 (rec[0] = dummy),
dados comprimidos zlib a partir da base 0x4601c.
"""
import glob, struct, zlib, os

DB = glob.glob(r"D:\SteamLibrary\steamapps\common\*NINJA*GAIDEN*\databin\databin")[0]
REC = 0x13180
DATA = 0x4601c

def count():
    with open(DB, "rb") as f:
        f.seek(0x20); return struct.unpack("<I", f.read(4))[0]

def rec(num, f=None):
    """Devolve (offset_absoluto, tam_comprimido, tam_descomprimido)."""
    own = f is None
    if own: f = open(DB, "rb")
    f.seek(REC + (num + 1) * 32)
    r = struct.unpack("<8I", f.read(32))
    if own: f.close()
    return DATA + r[0], r[3], r[2]

def raw(num, f=None):
    own = f is None
    if own: f = open(DB, "rb")
    off, comp, unc = rec(num, f)
    f.seek(off); d = f.read(comp)
    if own: f.close()
    return d

# blocos originais guardados antes de qualquer patch de textura
BACKUPS = ["D:/ng_trad_work/menu/backup/bloco_%05d.bin",
           "D:/ng_trad_work/fonte/backup_%05d_block.bin"]

def get(num, f=None, original=False):
    """Conteudo descomprimido do arquivo num.

    Com original=True usa o bloco de backup (pre-patch), se existir.
    """
    if original:
        for pat in BACKUPS:
            p = pat % num
            if os.path.exists(p):
                return zlib.decompress(open(p, "rb").read())
    return zlib.decompress(raw(num, f))

def ext(data):
    for m, name in MAGICS:
        if data.startswith(m): return name
    return data[:4].decode("ascii", "replace")
