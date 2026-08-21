# -*- coding: utf-8 -*-
"""Capa quadrada para o guia da Comunidade Steam.

A Steam pede uma imagem quadrada de no minimo 195x195 e encolhe ela para esse
tamanho na listagem de guias -- entao o que importa e continuar legivel
pequeno. Por isso o texto e curto e grande, e a arte fica so como fundo.

Sai em 512x512, bem acima do minimo, em duas variantes:
  capa-guia-A.png   logo + PT-BR            (mais legivel no tamanho pequeno)
  capa-guia-B.png   igual, com TRADUCAO em cima

O material e a arte oficial do proprio jogo, do cache da biblioteca da Steam.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ART = r"C:/Program Files (x86)/Steam/appcache/librarycache/1580780"
OUT = r"D:/ng_trad_work/promo"
LADO = 512


def fonte(nome, tam):
    return ImageFont.truetype(r"C:/Windows/Fonts/" + nome, tam)


def texto_centro(draw, xy, s, fnt, cor, contorno=(0, 0, 0), esp=6):
    draw.text(xy, s, font=fnt, fill=cor, anchor="mm",
              stroke_width=esp, stroke_fill=contorno)


def monta(com_rotulo):
    # fundo: recorte quadrado da arte do heroi, escurecido
    hero = Image.open(os.path.join(ART, "library_hero.jpg")).convert("RGB")
    lado = min(hero.size)
    esq = (hero.width - lado) // 2
    topo = max(0, (hero.height - lado) // 3)     # um pouco acima do centro
    cv = hero.crop((esq, topo, esq + lado, topo + lado)).resize(
        (LADO, LADO), Image.LANCZOS)

    # escurece de baixo para cima, para o texto respirar
    grad = Image.new("L", (1, LADO), 0)
    for y in range(LADO):
        grad.putpixel((0, y), int(235 * (y / LADO) ** 1.4))
    cv = Image.composite(Image.new("RGB", (LADO, LADO), (6, 6, 9)), cv,
                         grad.resize((LADO, LADO)))

    # vinheta nas bordas
    vig = Image.new("L", (LADO, LADO), 0)
    ImageDraw.Draw(vig).rectangle([46, 46, LADO - 46, LADO - 46], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(60))
    cv = Image.composite(cv, Image.new("RGB", (LADO, LADO), (6, 6, 9)), vig)

    draw = ImageDraw.Draw(cv)

    # logo oficial do jogo
    logo = Image.open(os.path.join(ART, "logo.png")).convert("RGBA")
    lw = 380
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    cv.paste(logo, ((LADO - lw) // 2, 108 if com_rotulo else 132), logo)

    if com_rotulo:
        texto_centro(draw, (LADO // 2, 74), "TRADUÇÃO",
                     fonte("segoeuib.ttf", 40), (232, 232, 236), esp=5)

    # PT-BR: o que precisa sobreviver ao encolhimento para 195x195
    texto_centro(draw, (LADO // 2, 372), "PT-BR",
                 fonte("impact.ttf", 138), (226, 26, 32), esp=8)
    texto_centro(draw, (LADO // 2, 460), "texto  ·  menu  ·  acentos",
                 fonte("segoeuib.ttf", 27), (214, 214, 220), esp=5)
    return cv


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "imagens"), exist_ok=True)
    for nome, rotulo in (("A", False), ("B", True)):
        img = monta(rotulo)
        caminho = os.path.join(OUT, "imagens", "capa-guia-%s.png" % nome)
        img.save(caminho)
        # previa de como a Steam mostra na listagem
        img.resize((195, 195), Image.LANCZOS).save(
            os.path.join(OUT, "imagens", "previa-195-%s.png" % nome))
        print("gerada:", caminho, img.size)
