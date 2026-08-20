# -*- coding: utf-8 -*-
"""Descobre quais blocos do databin a traducao alterou.

Nao existe um databin virgem por perto para comparar, entao a lista e montada
cruzando tres fontes independentes:

  1. o backup do instalador de julho (databin.ptbr_patch_backup), que guarda
     offset + bytes ORIGINAIS de cada bloco que aquele patch tocou;
  2. os backups de bloco desta oficina (menu/backup e fonte/), das texturas
     e da fonte;
  3. uma varredura em TODOS os blocos procurando marcas de portugues -- pega
     qualquer bloco de texto mexido depois de julho pelos recalls.

O que sai daqui alimenta o gerador do pacote.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbx  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

BK_MAGIC = b"NGPTBRB1"
BK_JULHO = dbx.DB + ".ptbr_patch_backup"

# Trechos que so existem se o bloco passou pela traducao. O 'a' e o 'o' com
# trema vem da substituicao do til (os glifos foram repintados), entao sao
# assinatura forte de bloco nosso.
MARCAS = [
    "ção".replace("ã", "ä").encode("utf-8"),
    "ões".replace("õ", "ö").encode("utf-8"),
    b"Pergaminho",
    b"Guilhotina",
    b"Pressione",
    b"Voc\xc3\xaa",
]


def blocos_do_backup_julho():
    """Devolve {num_bloco: bytes_originais} a partir do backup de julho."""
    if not os.path.exists(BK_JULHO):
        return {}
    porof = {}
    with open(BK_JULHO, "rb") as f:
        if f.read(8) != BK_MAGIC:
            return {}
        n = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            off, ln = struct.unpack("<QI", f.read(12))
            porof[off] = f.read(ln)
    # traduz offset de arquivo para numero de bloco
    saida = {}
    with open(dbx.DB, "rb") as f:
        for num in range(dbx.count()):
            off, comp, unc = dbx.rec(num, f)
            if off in porof:
                saida[num] = porof[off]
    return saida


def varredura_pt():
    """Blocos cujo conteudo atual tem marca de portugues."""
    achados = []
    with open(dbx.DB, "rb") as f:
        for num in range(dbx.count()):
            try:
                d = dbx.get(num, f)
            except Exception:
                continue
            for m in MARCAS:
                if m in d:
                    achados.append(num)
                    break
    return achados


if __name__ == "__main__":
    julho = blocos_do_backup_julho()
    print("backup de julho: %d bloco(s) -> %s"
          % (len(julho), sorted(julho)[:20]))

    locais = []
    for padrao in dbx.BACKUPS:
        pasta = os.path.dirname(padrao)
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            for num in range(dbx.count()):
                pass
            break
    # os backups locais tem o numero no nome, e mais simples ler direto
    import glob
    for p in glob.glob(r"D:\ng_trad_work\menu\backup\bloco_*.bin"):
        locais.append(int(os.path.basename(p)[6:11]))
    if os.path.exists(r"D:\ng_trad_work\fonte\backup_2771_block.bin"):
        locais.append(2771)
    print("backups locais : %d bloco(s) -> %s" % (len(locais), sorted(locais)))

    print("\nvarrendo os %d blocos atras de portugues..." % dbx.count())
    pt = varredura_pt()
    print("com marca PT   : %d bloco(s) -> %s" % (len(pt), sorted(pt)))

    todos = sorted(set(julho) | set(locais) | set(pt))
    print("\n=== uniao: %d blocos alterados ===" % len(todos))
    print(todos)

    with open(dbx.DB, "rb") as f:
        soma = 0
        for num in todos:
            off, comp, unc = dbx.rec(num, f)
            soma += comp
        print("\npeso somado dos blocos (ja comprimidos): %.1f MB"
              % (soma / 1048576.0))
