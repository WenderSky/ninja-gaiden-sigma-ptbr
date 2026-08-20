# -*- coding: utf-8 -*-
"""Aplica (ou reverte) as texturas de menu em PT-BR no databin.

  python aplicar_menu.py teste      -> so mede se cabe no slot
  python aplicar_menu.py            -> aplica
  python aplicar_menu.py reverter   -> volta ao original
"""
import sys, os, json, base64, zlib
sys.path.insert(0, os.path.dirname(__file__))
import dbx, g1t
sys.stdout.reconfigure(encoding="utf-8")

PATCH = r"D:\ng_trad_work\menu_ptbr.json"
BAKDIR = r"D:\ng_trad_work\menu\backup"
modo = sys.argv[1] if len(sys.argv) > 1 else "aplicar"
os.makedirs(BAKDIR, exist_ok=True)

patch = json.load(open(PATCH))
f = open(dbx.DB, "r+b")
for num_s, texturas in patch.items():
    num = int(num_s)
    off, comp, unc = dbx.rec(num, f)
    bak = os.path.join(BAKDIR, "bloco_%05d.bin" % num)
    f.seek(off); raw = f.read(comp)
    if modo == "reverter":
        if not os.path.exists(bak): print("  sem backup de", num); continue
        orig = open(bak, "rb").read(); assert len(orig) == comp
        f.seek(off); f.write(orig); print("  bloco %d revertido" % num); continue
    if modo == "aplicar" and not os.path.exists(bak):
        open(bak, "wb").write(raw)
    d = bytearray(zlib.decompress(raw))
    g = g1t.parse(bytes(d))
    for idx_s, b64 in texturas.items():
        t = [x for x in g['tex'] if x['i'] == int(idx_s)][0]
        px = zlib.decompress(base64.b64decode(b64))
        assert len(px) == t['w']*t['h']*4, (len(px), t['w'], t['h'])
        d[t['data']:t['data']+len(px)] = px
    nc = zlib.compress(bytes(d), 9)
    print("  arq %d: %d texturas | comp %d/%d (%s %d)" % (
        num, len(texturas), len(nc), comp,
        "folga" if len(nc) <= comp else "ESTOUROU", abs(comp - len(nc))))
    if modo == "teste": continue
    if len(nc) > comp:
        print("     -> nao aplicado"); continue
    f.seek(off); f.write(nc + b"\x00" * (comp - len(nc)))
f.flush(); os.fsync(f.fileno()); f.close()
print(modo, "concluido")
