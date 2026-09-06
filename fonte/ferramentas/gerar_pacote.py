# -*- coding: utf-8 -*-
"""Monta o arquivo de dados da traducao a partir do databin ja traduzido.

A ideia: como a traducao nunca mexeu no INDICE do databin -- todo bloco foi
regravado dentro do mesmo espaco, com enchimento de zeros quando sobrava --
os offsets e tamanhos continuam iguais aos do jogo virgem. Entao basta
carregar os blocos ja comprimidos e o instalador so precisa gravar bytes no
lugar certo: nada de zlib, nada de recompor, nada que possa nao caber.

Sai daqui o NG_PTBR.dados, com um cabecalho que carimba o tamanho do databin
de referencia. Se a Steam atualizar o jogo, os offsets mudam, o carimbo nao
bate e o instalador se recusa a escrever em vez de estragar o arquivo.

Formato:
  "NGPTBR03"            8 bytes
  versao                uint32
  tam_databin           uint64
  n_blocos              uint32
  por bloco:  num uint32 | off uint64 | comp uint32 | comp bytes
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbx  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

MAGIC = b"NGPTBR03"
VERSAO = 31
SAIDA = r"D:\ng_trad_work\pacote\NG_PTBR.dados"

# Vem do blocos_mudados.py. Deixado explicito de proposito: e a lista que
# define o pacote, e melhor ela estar a vista do que ser recalculada a cada
# geracao (a varredura leva minutos e depende do databin local).
BLOCOS = [
    5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33, 34, 35, 36, 37, 38, 49, 50, 2771,
    2773, 2775, 2777, 2781, 2783, 2784, 2821, 2822, 2826, 2827, 2832, 2837,
    2838, 2839, 2841, 2842, 2844, 2845, 2846, 2847, 2858, 2861, 2874, 2875,
    2878, 3228, 3229, 3288, 3293, 3382, 3414, 3415, 3417, 3418, 3419, 3420,
    3426, 3428, 3445, 3446, 3447, 3449, 3450, 3451, 3452, 3453, 3457, 3495,
    3508, 3538, 3540, 3541, 3542, 3561, 3573, 3577, 3632, 3633, 3634, 3639,
    3640, 3641, 3646, 3647, 3648, 3650, 3652, 3653, 3654, 3655, 3656, 3657,
    3658, 3659, 3660, 3661, 3672, 3676, 3682, 3684, 3685, 3754, 4041, 4042,
    4043, 4058, 4125, 4128, 4144, 4235, 4312, 4313, 4314, 4315, 4316, 4317,
    4319, 4320, 4323, 4326, 4327, 4328, 4329, 4331, 4332, 4362, 4364, 4366,
    4368, 4370, 4372, 4374, 4376, 4378, 4380, 4382, 4384, 4386, 4388, 4390,
    4392, 4411, 4412, 4438, 4439, 4440, 4443, 4445, 4529, 4554, 4555, 4556,
    4808, 4810, 4848, 4850, 4852, 5351, 5397, 5401, 5409, 5417, 5425, 5435,
    5459, 5475, 5885, 5953, 5954, 5958, 6115, 6123, 6131, 6139, 6147, 6156,
    6158, 6160, 6162, 6234, 6235, 6239, 6240, 6241, 6242, 6243, 6244, 6245,
    6246, 6247, 6248, 6249, 6251, 6252, 6253, 6309, 6330, 6334, 6335, 6336,
    6337, 6339, 6340, 6343, 6344, 6346, 6379, 6389, 6399,
]


def main():
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    tam = os.path.getsize(dbx.DB)
    print("databin de referencia: %s" % dbx.DB)
    print("tamanho: %d bytes (%.2f GB)" % (tam, tam / 1073741824.0))

    corpo = bytearray()
    total = 0
    with open(dbx.DB, "rb") as f:
        for num in BLOCOS:
            off, comp, unc = dbx.rec(num, f)
            f.seek(off)
            dados = f.read(comp)
            if len(dados) != comp:
                raise SystemExit("bloco %d: li %d de %d bytes" % (num, len(dados), comp))
            corpo += struct.pack("<IQI", num, off, comp) + dados
            total += comp

    with open(SAIDA, "wb") as s:
        s.write(MAGIC)
        s.write(struct.pack("<IQI", VERSAO, tam, len(BLOCOS)))
        s.write(corpo)

    print("\nblocos: %d" % len(BLOCOS))
    print("dados : %.1f MB" % (total / 1048576.0))
    print("saida : %s (%.1f MB)" % (SAIDA, os.path.getsize(SAIDA) / 1048576.0))


if __name__ == "__main__":
    main()
