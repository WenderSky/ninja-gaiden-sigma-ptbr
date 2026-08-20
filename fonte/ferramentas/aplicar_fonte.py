# -*- coding: utf-8 -*-
"""Aplica (ou reverte) o patch da fonte no bloco 2771 do databin.

  python aplicar_fonte.py            -> aplica
  python aplicar_fonte.py reverter   -> volta ao original
"""
import sys, os, json, base64, zlib, struct
sys.path.insert(0, os.path.dirname(__file__))
import dbx
sys.stdout.reconfigure(encoding="utf-8")

NUM = 2771
BAK = r"D:\ng_trad_work\fonte\backup_2771_block.bin"
PATCH = r"D:\ng_trad_work\fonte_ptbr.json"
rev = len(sys.argv) > 1 and sys.argv[1] == "reverter"

f = open(dbx.DB, "r+b")
off, comp, unc = dbx.rec(NUM, f)
f.seek(off); raw = f.read(comp)

if rev:
    if not os.path.exists(BAK): sys.exit("sem backup do bloco 2771")
    orig = open(BAK, "rb").read()
    assert len(orig) == comp, (len(orig), comp)
    f.seek(off); f.write(orig); f.flush(); os.fsync(f.fileno()); f.close()
    print("bloco 2771 revertido ao original")
    raise SystemExit

if not os.path.exists(BAK):
    open(BAK, "wb").write(raw)
    print("backup do bloco 2771 salvo (%d bytes)" % len(raw))

d = bytearray(zlib.decompress(raw))
assert len(d) == unc
p = json.load(open(PATCH, encoding="utf-8"))
mud = 0
for o, novo_b64, orig_b64 in p["linhas"]:
    novo = base64.b64decode(novo_b64)
    if bytes(d[o:o+len(novo)]) != novo:
        d[o:o+len(novo)] = novo; mud += 1

nc = zlib.compress(bytes(d), 9)
if len(nc) > comp: sys.exit("ESTOUROU: %d > %d" % (len(nc), comp))
f.seek(off); f.write(nc + b"\x00" * (comp - len(nc)))
f.flush(); os.fsync(f.fileno())
f.seek(off); assert zlib.decompress(f.read(comp)) == bytes(d)
f.close()
print("fonte aplicada: %d linhas alteradas | comp %d/%d (folga %d)" % (mud, len(nc), comp, comp - len(nc)))
