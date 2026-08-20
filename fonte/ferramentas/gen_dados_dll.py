# -*- coding: utf-8 -*-
"""Transforma exe_ptbr.json num cabecalho C para embutir na DLL.

Formato: um blob unico com, para cada entrada, os bytes ESPANHOIS seguidos
dos bytes PORTUGUESES. A tabela guarda o RVA, os dois tamanhos e o offset no
blob. O espanhol vai junto de proposito: a DLL confere que a string esperada
esta mesmo no lugar ANTES de escrever -- se o jogo for atualizado e os
enderecos mudarem, ela simplesmente nao escreve nada.
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")

tab = json.load(open(r"D:\ng_trad_work\exe_ptbr.json", encoding="utf-8"))
entradas = []
blob = bytearray()
for rva_s in sorted(tab, key=int):
    v = tab[rva_s]
    es = v["es"].encode("utf-8"); pt = v["pt"].encode("utf-8")
    # o espaco util e o ORCAMENTO (string + NULs de alinhamento), nao o
    # tamanho da string espanhola: 87 traducoes sao maiores que o original
    # e cabem so por causa desse preenchimento.
    assert len(pt) <= v["orc"], rva_s
    entradas.append((int(rva_s), len(es), len(pt), v["orc"], len(blob)))
    blob += es + pt

linhas = []
linhas.append("/* gerado por gen_dados_dll.py -- nao editar a mao */")
linhas.append("#define N_ENTRADAS %d" % len(entradas))
linhas.append("typedef struct { unsigned int rva; unsigned short nes, npt, orc; unsigned int off; } Entrada;")
linhas.append("static const unsigned char DADOS[] = {")
for i in range(0, len(blob), 24):
    linhas.append("  " + ",".join(str(b) for b in blob[i:i+24]) + ",")
linhas.append("};")
linhas.append("static const Entrada ENTRADAS[N_ENTRADAS] = {")
for rva, nes, npt, orc, off in entradas:
    linhas.append("  {0x%08x,%d,%d,%d,%d}," % (rva, nes, npt, orc, off))
linhas.append("};")

saida = r"D:\ng_trad_work\dll\patch_dados.h"
open(saida, "w", encoding="ascii").write("\n".join(linhas) + "\n")
print("entradas: %d | blob: %d bytes | cabecalho: %.1f KB"
      % (len(entradas), len(blob), os.path.getsize(saida) / 1024))
