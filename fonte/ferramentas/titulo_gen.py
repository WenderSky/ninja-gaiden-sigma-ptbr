# -*- coding: utf-8 -*-
"""Refaz a faixa da tela de titulo (2773/27) e o cabecalho 'Menu' (2775).

A tela de titulo NAO e string: e textura. 'PRESIONA EL BOTÓN START' vira
'PRESSIONE O BOTÃO START', com o Ã montado a partir do A + til recortado da
fonte serifada do jogo.

O 'Menu' do menu de pausa tambem e textura, em tres variantes (Menu / Menū /
Menü). Como em portugues a palavra e 'Menu', as tres recebem a versao limpa.
"""
import sys, os, json, base64, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banner, compor, diacritico
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")

LIM = 200
ORIG = "PRESIONA EL BOTÓN START"
NOVO = "PRESSIONE O BOTÃO START"


def cores_das_letras(a, texto):
    chars = [c for c in texto if c != " "]
    segs = banner.segmentos_forcado(a, LIM, len(chars))
    if len(segs) != len(chars): raise SystemExit("segmentacao: %d/%d" % (len(segs), len(chars)))
    core = (a[..., 3] >= LIM).astype(np.uint8) * 255
    lib = {}
    for c, (x0, x1) in zip(chars, segs):
        lib.setdefault(c, core[:, x0:x1].copy())
    return lib, segs, chars


def metrica(segs, chars):
    gaps = []; esp = []
    antes = None; k = 0
    for c in ORIG:
        if c == " ": antes = "e"; continue
        if k > 0:
            g = segs[k][0] - segs[k-1][1]
            (esp if antes == "e" else gaps).append(g)
        antes = None; k += 1
    return int(np.median(gaps)), int(np.median(esp))


def silhueta(lib, texto, gap, espaco, forma, centro):
    larg = 0; pos = []
    for c in texto:
        if c == " ": larg += espaco; continue
        pos.append((larg, c)); larg += lib[c].shape[1] + gap
    larg -= gap
    bloco = np.zeros((forma[0], larg), dtype=np.uint8)
    for dx, c in pos:
        g = lib[c]
        np.maximum(bloco[:, dx:dx+g.shape[1]], g, out=bloco[:, dx:dx+g.shape[1]])
    out = np.zeros(forma[:2], dtype=np.uint8)
    x0 = max(0, int(round(centro - larg / 2)))
    x1 = min(out.shape[1], x0 + larg)
    out[:, x0:x1] = bloco[:, :x1-x0]
    return out


if __name__ == "__main__":
    patch = json.load(open(r"D:\ng_trad_work\menu_ptbr.json"))

    # --- tela de titulo ---
    _, A = banner.carrega(2773, 27)
    lib, segs, chars = cores_das_letras(A, ORIG)
    gap, espaco = metrica(segs, chars)
    # Ã = A + til (o til vem da fonte serifada 02771/34)
    letraA = np.zeros(A.shape[:2] + (4,), dtype=np.uint8)
    letraA[..., 3] = 0
    aa = lib["A"]
    tmp = np.zeros(aa.shape + (4,), dtype=np.uint8)
    tmp[..., 3] = aa
    for k in range(3): tmp[..., k] = aa
    lib["Ã"] = diacritico.acentua(tmp, "til")[..., 3]
    nz = np.nonzero((A[..., 3] > 20).any(0))[0]
    centro = (nz.min() + nz.max()) / 2
    mask = silhueta(lib, NOVO, gap, espaco, A.shape, centro)
    sg, gan, linhas, halo, err = compor.estilo_brilho(A, LIM)
    novo = compor.pinta_brilho(mask, sg, gan, linhas, halo)
    patch.setdefault("2773", {})["27"] = base64.b64encode(
        zlib.compress(novo.tobytes(), 9)).decode()
    print("titulo: %s -> %s  (gap %d, espaco %d, sigma %.1f, erro %.1f)"
          % (ORIG, NOVO, gap, espaco, sg, err))

    # --- cabecalho 'Menu' (as tres variantes recebem a limpa) ---
    _, M = banner.carrega(2775, 146)
    for idx in (146, 148, 149):
        patch.setdefault("2775", {})[str(idx)] = base64.b64encode(
            zlib.compress(M.tobytes(), 9)).decode()
    print("menu: 2775/146 copiado para 148 e 149")

    json.dump(patch, open(r"D:\ng_trad_work\menu_ptbr.json", "w"))
    print("texturas no patch:", sum(len(v) for v in patch.values()))

    # previa
    def img(x):
        im = Image.fromarray(x[..., [2, 1, 0, 3]], "RGBA")
        bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
        return bg.convert("RGB")
    sheet = Image.new("RGB", (760, 200), (0, 0, 0))
    sheet.paste(img(A).crop((0, 0, 700, 64)).resize((760, 70)), (0, 0))
    sheet.paste(img(novo).crop((0, 0, 700, 64)).resize((760, 70)), (0, 80))
    sheet.save(r"D:\ng_trad_work\menu\previa_titulo.png")
