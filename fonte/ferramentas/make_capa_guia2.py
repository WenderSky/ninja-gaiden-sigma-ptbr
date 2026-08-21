# -*- coding: utf-8 -*-
"""Capa do guia da Steam a partir da arte da Master Collection.

A arte ja e quadrada. O credito entra numa faixa embaixo, no lugar do
"MASTER COLLECTION" -- assim o personagem e o logo ficam inteiros, e o texto
cai onde o olho ja procura o nome do jogo.

A Steam encolhe a capa para 195x195 na listagem de guias, entao "PT-BR" sai
maior que "TRADUCAO": e a parte que precisa sobreviver ao encolhimento. O
contorno das letras e fino de proposito -- grosso demais, ele engole a cedilha
do C.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ENTRADA = r"D:\ng_trad_work\promo\fonte_capa.jpg"
SAIDA = r"D:\ng_trad_work\promo\imagens"
LADO = 512
FAIXA = 92           # altura da faixa: para de subir antes do GAIDEN do logo


def fonte(nome, tam):
    return ImageFont.truetype(r"C:/Windows/Fonts/" + nome, tam)


def escurece_rodape(cv):
    veu = Image.new("L", (1, LADO), 0)
    ini = LADO - FAIXA
    for y in range(ini, LADO):
        t = (y - ini) / float(FAIXA)
        # chega ao opaco depressa: senao o "MASTER COLLECTION" fica
        # fantasmando atras do texto
        veu.putpixel((0, y), int(255 * min(1.0, t * 2.6)))
    veu = veu.resize((LADO, LADO))
    escuro = Image.new("RGB", (LADO, LADO), (5, 6, 9))
    return Image.composite(escuro, cv, veu)


def largura(draw, s, fnt):
    a, _, b, _ = draw.textbbox((0, 0), s, font=fnt)
    return b - a


def monta():
    arte = Image.open(ENTRADA).convert("RGB").resize((LADO, LADO), Image.LANCZOS)
    cv = escurece_rodape(arte)
    draw = ImageDraw.Draw(cv)

    f1 = fonte("segoeuib.ttf", 36)
    f2 = fonte("impact.ttf", 54)
    s1, s2 = "TRADUÇÃO ", "PT-BR"
    w1, w2 = largura(draw, s1, f1), largura(draw, s2, f2)
    x = (LADO - (w1 + w2)) // 2
    y = LADO - FAIXA // 2 - 4

    # contorno fino: o grosso fecha o vao da cedilha e vira "TRADUCAO"
    draw.text((x, y), s1, font=f1, fill=(238, 238, 242), anchor="lm",
              stroke_width=3, stroke_fill=(0, 0, 0))
    draw.text((x + w1, y), s2, font=f2, fill=(224, 28, 34), anchor="lm",
              stroke_width=3, stroke_fill=(0, 0, 0))
    return cv


if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    img = monta()
    caminho = os.path.join(SAIDA, "capa-guia-C.png")
    img.save(caminho)
    img.resize((195, 195), Image.LANCZOS).save(
        os.path.join(SAIDA, "previa-195-C.png"))
    print("gerada:", caminho, img.size)
