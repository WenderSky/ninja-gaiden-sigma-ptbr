# -*- coding: utf-8 -*-
"""Confere o NG_PTBR.dados contra o databin traduzido, byte a byte.

Se cada bloco do pacote for identico ao que esta no databin, entao instalar
sobre este computador e uma operacao nula -- o que prova que o pacote leva
exatamente o estado que ja foi testado no jogo.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbx  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

PACOTE = r"D:\ng_trad_work\pacote\NG_PTBR.dados"
MAGIC = b"NGPTBR03"


def main():
    p = open(PACOTE, "rb")
    if p.read(8) != MAGIC:
        raise SystemExit("magic errado")
    versao, tam_ref, n = struct.unpack("<IQI", p.read(16))
    tam_real = os.path.getsize(dbx.DB)
    print("versao do pacote : %d" % versao)
    print("databin esperado : %d bytes" % tam_ref)
    print("databin daqui    : %d bytes  %s"
          % (tam_real, "OK" if tam_real == tam_ref else "DIFERENTE!"))
    print("blocos no pacote : %d\n" % n)

    iguais = difs = 0
    with open(dbx.DB, "rb") as f:
        for _ in range(n):
            num, off, comp = struct.unpack("<IQI", p.read(16))
            dados = p.read(comp)
            f.seek(off)
            atual = f.read(comp)
            if atual == dados:
                iguais += 1
            else:
                difs += 1
                print("   DIFERE: bloco %d (off %d, %d bytes)" % (num, off, comp))
    p.close()
    print("identicos: %d | diferentes: %d" % (iguais, difs))
    print("\n%s" % ("PACOTE CONFERE" if difs == 0 else "PACOTE COM PROBLEMA"))


if __name__ == "__main__":
    main()
