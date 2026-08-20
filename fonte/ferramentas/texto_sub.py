# -*- coding: utf-8 -*-
"""Troca no databin os caracteres sem glifo pelos glifos repintados.

MAPA_FINAL e a regra definitiva da traducao: cada caractere que a fonte do
jogo nao tem foi repintado em cima de um glifo que nenhum idioma usa, e o
texto passa a escrever o glifo hospedeiro (mesmo tamanho em bytes).

  python texto_sub.py "<estado atual>" "<estado desejado>"
      cada estado e uma lista de chaves de MAPA_FINAL, separadas por virgula
      ("" = texto cru, sem nenhuma troca)
"""
import sys, os, json, zlib
sys.path.insert(0, os.path.dirname(__file__))
import dbx
sys.stdout.reconfigure(encoding="utf-8")

MAPA_FINAL = {
    "til":     {"ã": "ä", "õ": "ö", "Ã": "Ä", "Õ": "Ö"},   # repintados no atlas 33
    "ordinal": {"º": "ý", "ª": "ÿ"},
}

def aplica(s, chaves):
    for k in chaves:
        for a, b in MAPA_FINAL[k].items(): s = s.replace(a, b)
    return s

if __name__ == "__main__":
    de = [x for x in sys.argv[1].split(",") if x]
    para = [x for x in sys.argv[2].split(",") if x]
    patch = json.load(open(r"D:\ng_trad_work\patch_ptbr.json", encoding="utf-8"))
    f = open(dbx.DB, "r+b")
    tot = blocos = nao = 0; estouros = []
    for num_s in sorted(patch, key=int):
        ent = [e for e in patch[num_s] if aplica(e[2], de) != aplica(e[2], para)]
        if not ent: continue
        num = int(num_s)
        off, comp, unc = dbx.rec(num, f)
        f.seek(off); raw = f.read(comp)
        try: d = bytearray(zlib.decompress(raw))
        except Exception: continue
        mud = 0
        for offset, es, pt in ent:
            a = aplica(pt, de).encode("utf-8"); b = aplica(pt, para).encode("utf-8")
            if len(a) != len(b): nao += 1; continue
            if bytes(d[offset:offset+len(a)]) != a: nao += 1; continue
            d[offset:offset+len(a)] = b; mud += 1
        if not mud: continue
        nc = zlib.compress(bytes(d), 9)
        if len(nc) > comp: estouros.append(num); continue
        f.seek(off); f.write(nc + b"\x00" * (comp - len(nc)))
        tot += mud; blocos += 1
    f.flush(); os.fsync(f.fileno()); f.close()
    print("%s -> %s: %d strings em %d blocos | nao bateram %d" % (de or "cru", para, tot, blocos, nao))
    if estouros: print("  ESTOUROS:", estouros)
