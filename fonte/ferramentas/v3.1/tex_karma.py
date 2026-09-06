# -*- coding: utf-8 -*-
"""v3.1: títulos de karma/rank (fonte sans bold, 2048x256, 5 variantes por bloco).

Só a variante NÍTIDA é composta letra a letra; as outras são derivadas dela:
  - cinza (mesma forma): cor por linha e por classe (núcleo/sombra) copiada do original;
  - borradas: alpha = a1*alpha + a2*blur(alpha, sigma) ajustado por mínimos quadrados
    no par original (nítida -> variante), cor constante mediana.
Uso: python tex_karma.py [teste|aplicar]"""
import sys, os, collections
sys.path.insert(0, r"D:\ng_trad_work\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import texcomp as tc, dbx, g1t, numpy as np
from PIL import Image, ImageFilter

modo = sys.argv[1] if len(sys.argv) > 1 else "teste"
out = r"C:\Users\wende\AppData\Local\Temp\claude\C--Users-wende\189b77d5-b7c9-4488-b010-0f88e485cd68\scratchpad"
ARIAL = r"C:\Windows\Fonts\arialbd.ttf"

ALVOS = [  # (bloco, texto ES, texto PT, grupo de fonte, blocos extras de letras)
    (6115, "CAZADOR NOVATO", "CAÇADOR NOVATO", "h", []),
    (6123, "CAZADOR VETERANO", "CAÇADOR VETERANO", "h", []),
    (6131, "CAZADOR LEGENDARIO", "CAÇADOR LENDÁRIO", "h", []),
    (6139, "CAZADOR EXPERTO", "CAÇADOR EXPERIENTE", "h", [(6147, "CAZADOR INEXPERTO")]),
    (6147, "CAZADOR INEXPERTO", "CAÇADOR INEXPERIENTE", "h", []),
    (5459, "NINJA MAYOR", "NINJA MAIOR", "n", []),
    (5475, "MAESTRO NINJA", "MESTRE NINJA", "n", []),
]
CLARO = 175


def variantes(num):
    g = g1t.parse(dbx.get(num))
    ids = [t['i'] for t in g['tex'] if t['w'] == 2048 and t['h'] == 256 and t['fmt'] == 1]
    def nit(i):
        a = tc.textura(num, i)[1]; lum = a[..., :3].astype(np.float32).mean(2) * (a[..., 3] / 255.0)
        return float(np.abs(np.diff(lum, axis=1)).mean())
    ids.sort(key=nit, reverse=True)
    return ids


# ---- 1ª passada: tabela de larguras por grupo de fonte (segmentações limpas) ----
larg = {"h": collections.defaultdict(list), "n": collections.defaultdict(list)}
limpos = {}
for num, es, pt, grp, extras in ALVOS:
    for nb, tb in [(num, es)] + extras:
        v = variantes(nb)
        lib = tc.Biblioteca(lim=120, claro=CLARO)
        try:
            m = lib.add(nb, v[0], tb, forcar=False)
            for c, (x0, x1) in zip([c for c in tb if c != ' '], m['segs']): larg[grp][c].append(x1 - x0)
            limpos[nb] = True
        except SystemExit:
            limpos[nb] = False
tab = {g: {c: int(np.median(v)) for c, v in d.items()} for g, d in larg.items()}
print("larguras:", tab)


def cor_sombra(win):
    m = win[..., 3] > 200
    esc = m & (win[..., :3].mean(2) < 170)
    return tuple(int(v) for v in np.median(win[esc][..., :3], axis=0)) if esc.sum() > 20 else (60, 40, 40)


def blur(alpha, s):
    if s <= 0: return alpha.astype(np.float32)
    return np.asarray(Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))).astype(np.float32)


def ajuste_variante(a_nit, a_var):
    """Devolve (sigma, a1, a2, cor, erro) tal que alpha_var ≈ a1*alpha + a2*blur(alpha, sigma)."""
    al = a_nit[..., 3].astype(np.float32); av = a_var[..., 3].astype(np.float32)
    sub = (slice(0, None, 2), slice(0, None, 2))
    best = None
    for s in (0, 3, 5, 8, 11, 14, 18, 24, 30):
        b = blur(al, s)
        X = np.stack([al[sub].ravel(), b[sub].ravel()], 1); y = av[sub].ravel()
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = np.clip(X @ coef, 0, 255); err = np.abs(pred - y).mean()
        if best is None or err < best[0]: best = (err, s, coef)
    err, s, coef = best
    m = a_var[..., 3] > 100
    cor = np.median(a_var[m][..., :3], axis=0) if m.sum() else np.array([255, 255, 255])
    return s, float(coef[0]), float(coef[1]), cor, err


def deriva_borrada(novo, s, a1, a2, cor):
    al = novo[..., 3].astype(np.float32)
    alpha = np.clip(a1 * al + a2 * blur(al, s), 0, 255)
    r = np.zeros_like(novo); r[..., :3] = cor.astype(np.uint8); r[..., 3] = alpha.astype(np.uint8)
    return r


def deriva_cinza(novo, a_nit, a_cinza):
    """Mesma forma: cor por linha e por classe (núcleo claro / sombra) copiada do par original."""
    r = novo.copy()
    lum_o = a_nit[..., :3].mean(2); core_o = (a_nit[..., 3] > 100) & (lum_o > 170); somb_o = (a_nit[..., 3] > 100) & ~core_o
    lum_n = novo[..., :3].mean(2); core_n = (novo[..., 3] > 100) & (lum_n > 170); somb_n = (novo[..., 3] > 100) & ~core_n
    H = novo.shape[0]
    def perfil(mask):
        p = [None] * H
        for y in range(H):
            sel = mask[y]
            if sel.sum() >= 3: p[y] = np.median(a_cinza[y][sel][..., :3], axis=0)
        ys = [k for k in range(H) if p[k] is not None]
        for y in range(H):
            if p[y] is None: p[y] = p[min(ys, key=lambda k: abs(k - y))] if ys else np.array([128, 128, 128])
        return p
    pc = perfil(core_o); ps = perfil(somb_o)
    for y in range(H):
        r[y][core_n[y], :3] = pc[y]; r[y][somb_n[y], :3] = ps[y]
    return r


previas = []
for num, es, pt, grp, extras in ALVOS:
    ids = variantes(num); nitido = ids[0]
    print("bloco", num, es, "->", pt, "| variantes", ids, "nítida", nitido, "| limpo" if limpos[num] else "| colado")
    lib = tc.Biblioteca(lim=120, claro=CLARO)
    m = lib.add(num, nitido, es, forcar=True, larguras=tab[grp])
    for (nb, tb) in extras:
        lib.add(nb, variantes(nb)[0], tb, forcar=True, larguras=tab[grp])
    print("   segs", [(b - a) for a, b in m['segs']], "gap", m['gap'], "esp", m['espaco'])
    folga = (0, 12); limpar = 8
    ext = {}
    if "Ç" in pt:
        cw, _, dc = lib.pega("C", (num, nitido), folga, limpar)
        ext["Ç"] = (tc.com_acento(cw, "¸", claro=CLARO, frac=0.42, dy=-6, embaixo=True, fonte=ARIAL,
                                  sombra=(5, 5), grosso=2, cor=(245, 245, 245), cor_sombra=cor_sombra(cw)), dc, folga[1])
    if "Á" in pt:
        aw, _, da = lib.pega("A", (num, nitido), folga, limpar)
        ext["Á"] = (tc.com_acento(aw, "´", claro=CLARO, frac=0.45, dy=-4, fonte=ARIAL, sombra=(5, 5), grosso=2,
                                  cor=(245, 245, 245), cor_sombra=cor_sombra(aw)), da, folga[1])
    novo = tc.compor(lib, pt, ref=(num, nitido), folga=folga, limpar=limpar, extras=ext, pref=(num, nitido))
    a_nit = tc.textura(num, nitido)[1]
    saidas = {nitido: novo}
    for i in ids[1:]:
        a_var = tc.textura(num, i)[1]
        s, a1, a2, cor, err = ajuste_variante(a_nit, a_var)
        if err < 0.5 and (s == 0 or abs(a2) < 0.05):
            saidas[i] = deriva_cinza(novo, a_nit, a_var); print("   var %d: cinza (mesma forma)" % i)
        else:
            saidas[i] = deriva_borrada(novo, s, a1, a2, cor)
            print("   var %d: sigma %d a1 %.2f a2 %.2f cor %s erro %.1f" % (i, s, a1, a2, cor.astype(int), err))
    previas.append(a_nit[:, :1500]); previas.append(novo[:, :1500])
    for i in ids[1:]: previas.append(saidas[i][:, :1500])
    tc.gravar(num, saidas, modo)
tc.previa(previas, os.path.join(out, "p_karma.png"), escala=0.4)
print("previa ok")
