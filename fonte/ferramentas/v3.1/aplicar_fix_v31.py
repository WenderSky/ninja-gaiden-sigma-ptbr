# -*- coding: utf-8 -*-
"""Correções v3.1 (06/09/2026): linhas de cutscene, nomes de área e itens que o
lote original deixou em espanhol. Edição in-place no databin ATUAL (já traduzido),
mesma regra de sempre: nunca cresce, preenche com NUL, bloco recomprimido tem de
caber no espaço original. Guarda o bloco comprimido anterior em fix_v31/backup.

  python tools/aplicar_fix_v31.py teste     -> só confere
  python tools/aplicar_fix_v31.py           -> grava
  python tools/aplicar_fix_v31.py reverter  -> devolve os blocos do backup
"""
import sys, os, json, zlib, collections
sys.path.insert(0, os.path.dirname(__file__))
import dbx
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sub(s):
    return (s.replace("ã", "ä").replace("õ", "ö").replace("Ã", "Ä")
             .replace("Õ", "Ö").replace("º", "ý").replace("ª", "ÿ"))


modo = sys.argv[1] if len(sys.argv) > 1 else "aplicar"
BAK = r"D:\ng_trad_work\fix_v31\backup"
os.makedirs(BAK, exist_ok=True)

if modo == "reverter":
    f = open(dbx.DB, "r+b")
    for nome in sorted(os.listdir(BAK)):
        num = int(nome[6:11])
        off_abs, comp, unc = dbx.rec(num, f)
        raw = open(os.path.join(BAK, nome), "rb").read()
        assert len(raw) == comp
        f.seek(off_abs); f.write(raw)
        print("revertido", num)
    f.close(); sys.exit()

M = json.load(open(r"D:\ng_trad_work\fix_v31_master.json", encoding="utf-8"))
audit = json.load(open(r"D:\ng_trad_work\audit_faltam.json", encoding="utf-8"))
trocas = collections.defaultdict(list)
for num, off, es, pt in M["rtm"] + M["messtr"]:
    trocas[num].append((off, es, pt))
for num, kind, off, n, es in audit:
    if kind == "dlg" and es in M["dlg"]:
        trocas[num].append((off, es, M["dlg"][es]))

f = open(dbx.DB, "r+b")
ok = erros = blocos = 0
estouro = []
for num in sorted(trocas):
    off_abs, comp, unc = dbx.rec(num, f)
    raw = dbx.raw(num, f)
    data = bytearray(zlib.decompress(raw))
    apl = 0
    for off, es, pt in trocas[num]:
        esb = es.encode("utf-8"); ptb = sub(pt).encode("utf-8")
        atual = bytes(data[off:off + len(esb)])
        if atual != esb:
            print("  ERRO %d@%d: esperado %r, achei %r" % (num, off, es, atual.decode("utf-8", "replace")))
            erros += 1; continue
        if len(ptb) > len(esb):
            print("  ESTOURO %d@%d: %r tem %d bytes, cabe %d" % (num, off, pt, len(ptb), len(esb)))
            erros += 1; continue
        nxt = data[off + len(esb)]
        pad = b"\x00"
        if nxt != 0:
            print("  AVISO %d@%d: byte seguinte nao e NUL (%#x); uso espaco" % (num, off, nxt))
            pad = b" "
        data[off:off + len(esb)] = ptb + pad * (len(esb) - len(ptb))
        apl += 1
    nc = zlib.compress(bytes(data), 9)
    if len(nc) > comp:
        estouro.append(num)
        print("  BLOCO %d nao cabe: %d > %d" % (num, len(nc), comp))
        continue
    if modo != "teste" and apl:
        p = os.path.join(BAK, "bloco_%05d.bin" % num)
        if not os.path.exists(p):
            open(p, "wb").write(raw)
        f.seek(off_abs); f.write(nc + b"\x00" * (comp - len(nc)))
    ok += apl; blocos += 1
f.flush(); os.fsync(f.fileno()); f.close()
print("%s: %d trocas em %d blocos | erros %d | estouros %s" % (modo, ok, blocos, erros, estouro))
