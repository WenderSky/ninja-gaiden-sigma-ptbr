# -*- coding: utf-8 -*-
"""Gera as texturas de banner do menu em PT-BR e salva previa + patch."""
import sys, os, json, base64
sys.path.insert(0, os.path.dirname(__file__))
import banner, compor, diacritico
import numpy as np
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding="utf-8")

# fonte larga e fonte condensada nao se misturam
LARGA = [(2781, 26, 30, "*MENÚ PRINCIPAL*"), (2781, 56, 60, "*MENU PRINCIPALE*"),
         (2781, 46, 50, "*HAUPTMENÜ*")]
CONDENSADA = [(2781, 27, 34, "*SELECCIONAR DIFICULTAD*"), (2781, 47, 54, "*SCHWIERIGKEIT WÄHLEN*")]

ALVOS = [
    dict(num=2781, ouro=26, branca=30, azul=28, verde=29, cinza=31,
         orig="*MENÚ PRINCIPAL*", novo="MENU PRINCIPAL", fontes=LARGA),
    dict(num=2781, ouro=27, branca=34, azul=32, verde=33, cinza=35,
         orig="*SELECCIONAR DIFICULTAD*", novo="SELECIONAR DIFICULDADE", fontes=CONDENSADA),
    dict(num=2777, ouro=60, branca=63, azul=61, verde=62, cinza=64,
         orig="*OPCIONES*", novo="OPÇÕES", fontes=[(2777, 60, 63, "*OPCIONES*")],
         extra={"Ç": ("C", "cedilha"), "Õ": ("O", "til")}),
    dict(num=2783, ouro=132, branca=135, azul=133, verde=134, cinza=136,
         orig="*MISIONES*", novo="MISSÕES", fontes=[(2783, 132, 135, "*MISIONES*")],
         extra={"Õ": ("O", "til")}),
    dict(num=4808, ouro=22, branca=25, azul=23, verde=24, cinza=26,
         orig="*CLASIFICACIÓN*", novo="CLASSIFICAÇÃO",
         fontes=[(4808, 22, 25, "*CLASIFICACIÓN*")],
         extra={"O": ("Ó", "sem_acento"), "Ç": ("C", "cedilha"), "Ã": ("A", "til")}),
    dict(num=6346, ouro=96, branca=99, azul=97, verde=98, cinza=100,
         orig="*SUPERVIVENCIAS*", novo="SOBREVIVÊNCIA",
         fontes=[(6346, 96, 99, "*SUPERVIVENCIAS*"), (6346, 111, 114, "*SOPRAVVIVENZE*"),
                 (6346, 106, 109, "*ÜBERLEBEN*")],
         extra={"Ê": ("E", "circunflexo")}),
    dict(num=4810, ouro=22, branca=32, azul=30, verde=31, cinza=33,
         orig="*SELECCIONAR VESTIMENTA*", novo="SELECIONAR VESTIMENTA",
         fontes=[(4810, 22, 32, "*SELECCIONAR VESTIMENTA*")]),
]

def img(a):
    im = Image.fromarray(a[..., [2, 1, 0, 3]], "RGBA")
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
    return bg.convert("RGB")

def gerar(alvo):
    lib = compor.biblioteca(alvo["fontes"])
    ref = [c for c in alvo["orig"] if c not in "* " and c in lib and c not in "ÓÁÉÍÚÀÂÊÔÄÜ"][0]
    topo = diacritico.topo_de(lib[ref][1])
    for novo, (base, op) in alvo.get("extra", {}).items():
        g, b = lib[base]
        if op == "sem_acento":
            lib[novo] = (diacritico.tira_acento(g, topo), diacritico.tira_acento(b, topo))
        else:
            lib[novo] = (diacritico.acentua(g, op), diacritico.acentua(b, op))
    n = alvo["num"]
    _, B = banner.carrega(n, alvo["branca"]); _, G = banner.carrega(n, alvo["ouro"])
    itens, gap, esp = banner.mapear(B, alvo["orig"])
    orn = [it for it in itens if it[0] == "*"]
    letras = [it for it in itens if it[0] != "*"]
    folga = letras[0][1] - orn[0][2]
    nz = np.nonzero((B[..., 3] > banner.LIM).any(0))[0]
    centro = (nz.min() + nz.max()) / 2
    orn_b = B[:, orn[0][1]:orn[0][2]].copy(); orn_g = G[:, orn[0][1]:orn[0][2]].copy()
    nG, nB = compor.compor(lib, alvo["novo"], gap, esp, folga, centro, B.shape, orn_g, orn_b)
    saida = {"ouro": nG, "branca": nB}
    for key in ("azul", "verde", "cinza"):
        _, V = banner.carrega(n, alvo[key])
        # duas familias de variante: brilho puro (silhueta borrada) e
        # miolo nitido + halo. A segunda tem pixels de alfa alto.
        if (V[..., 3] >= 190).mean() > 0.002:
            sg, gan, linhas, halo, err = compor.estilo_brilho(V)
            saida[key] = compor.pinta_brilho(nB[..., 3], sg, gan, linhas, halo)
        else:
            sg, gan, cor, err = compor.ajusta_params(B[..., 3], V)
            saida[key] = compor.ajusta_brilho(nB[..., 3], sg, gan, cor)
    return saida

if __name__ == "__main__":
    linhas = []; patch = {}
    for alvo in ALVOS:
        print("%s -> %s" % (alvo["orig"].replace("*", ""), alvo["novo"]))
        novo = gerar(alvo)
        for key in ("ouro", "branca", "azul", "verde", "cinza"):
            idx = alvo[key]
            _, orig = banner.carrega(alvo["num"], idx)
            linhas.append(("%d/%d %s ANTES" % (alvo["num"], idx, key), img(orig)))
            linhas.append(("%d/%d %s DEPOIS" % (alvo["num"], idx, key), img(novo[key])))
            import zlib
            patch.setdefault(str(alvo["num"]), {})[str(idx)] = base64.b64encode(
                zlib.compress(novo[key].tobytes(), 9)).decode()
    json.dump(patch, open(r"D:\ng_trad_work\menu_ptbr.json", "w"))
    W = 620
    ims = [(l, i.resize((W, i.height*W//i.width))) for l, i in linhas]
    H = sum(i.height + 4 for _, i in ims)
    sheet = Image.new("RGB", (W+190, H), (35, 0, 0)); dr = ImageDraw.Draw(sheet); y = 0
    for l, i in ims:
        sheet.paste(i, (190, y)); dr.text((2, y+4), l, fill=(255, 220, 120)); y += i.height + 4
    sheet.save(r"D:\ng_trad_work\menu\previa_menu.png")
    print("previa:", sheet.size, "| texturas no patch:",
          sum(len(v) for v in patch.values()))
