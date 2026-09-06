# -*- coding: utf-8 -*-
"""v3.1 (varredura final de texturas):
  A. letreiro da loja 6162/13 "Armas y herramientas de MURAMASA" -> "Armas e ferramentas de MURAMASA"
  B. rótulo "Menú" (idx 17) -> cópia do "Menu" (idx 15) nos blocos 6156/6158/6160/6162
  C. "Nuevo Récord" 5401/20 e 6379/18 -> "Novo Recorde" (e de "New Record" 6371/18)
  D. "Muertos" 6399 (12 texturas 1024x256) -> "Mortos"
  E. "MISIÓN" 5417/2,5 e 5409/0-4 -> "MISSÕES" (E de MISSIONE 5415, O de MISSIONS 5411)
  F. "Sí"/"No" 5435 (256x256) -> "Sim"/"Não" (síntese Times bold)
  G. "Nivel" 4323/8 -> "Nível"
Uso: python tex_final.py [teste|aplicar] [so=A,B,...]"""
import sys, os
sys.path.insert(0, r"D:\ng_trad_work\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import texcomp as tc, texsint as ts, dbx, g1t, numpy as np
from PIL import Image, ImageFilter

args = sys.argv[1:]
modo = "aplicar" if "aplicar" in args else "teste"
so = [a.split("=")[1].split(",") for a in args if a.startswith("so=")]
so = so[0] if so else list("ABCDEFG")
out = r"C:\Users\wende\AppData\Local\Temp\claude\C--Users-wende\189b77d5-b7c9-4488-b010-0f88e485cd68\scratchpad\tex"
TIMESB = r"C:\Windows\Fonts\timesbd.ttf"
previas = []
OUTD = os.path.join(r"D:" + chr(92) + "ng_trad_work", "fix_v31", "final_out"); os.makedirs(OUTD, exist_ok=True)
_grav = tc.gravar
def gravar_salva(num, texturas, modo="teste"):
    for i, px in texturas.items(): np.save(os.path.join(OUTD, "%d_%d.npy" % (num, i)), px)
    return _grav(num, texturas, modo)
tc.gravar = gravar_salva


def inverte(a):
    """Cópia com luminância invertida (texto escuro vira claro) e alfa opaco, só para segmentar."""
    b = a.copy(); b[..., :3] = 255 - b[..., :3]; b[..., 3] = 255; return b


def blur(alpha, s):
    if s <= 0: return alpha.astype(np.float32)
    return np.asarray(Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))).astype(np.float32)


def ajuste(a_nit, a_var):
    al = a_nit[..., 3].astype(np.float32); av = a_var[..., 3].astype(np.float32)
    sub = (slice(0, None, 2), slice(0, None, 2)); best = None
    for s in (0, 3, 5, 8, 11, 14, 18, 24, 30):
        b = blur(al, s); X = np.stack([al[sub].ravel(), b[sub].ravel()], 1); y = av[sub].ravel()
        coef, *_ = np.linalg.lstsq(X, y, rcond=None); err = np.abs(np.clip(X @ coef, 0, 255) - y).mean()
        if best is None or err < best[0]: best = (err, s, coef)
    err, s, coef = best; m = a_var[..., 3] > 100
    cor = np.median(a_var[m][..., :3], axis=0) if m.sum() else np.array([255, 255, 255])
    return s, float(coef[0]), float(coef[1]), cor, err


def deriva_borrada(novo, s, a1, a2, cor):
    al = novo[..., 3].astype(np.float32); alpha = np.clip(a1 * al + a2 * blur(al, s), 0, 255)
    r = np.zeros_like(novo); r[..., :3] = cor.astype(np.uint8); r[..., 3] = alpha.astype(np.uint8); return r


def deriva_mesma_forma(novo, a_nit, a_var, claro=170):
    r = novo.copy(); H = novo.shape[0]
    def classes(a):
        lum = a[..., :3].mean(2); op = a[..., 3] > 60; return op & (lum > claro), op & (lum <= claro)
    co, so_ = classes(a_nit); cn, sn = classes(novo)
    def perfil(mask):
        p = [None] * H
        for y in range(H):
            if mask[y].sum() >= 3: p[y] = np.median(a_var[y][mask[y]], axis=0)
        ys = [k for k in range(H) if p[k] is not None]
        for y in range(H):
            if p[y] is None: p[y] = p[min(ys, key=lambda k: abs(k - y))] if ys else np.array([128, 128, 128, 255])
        return p
    pc, ps = perfil(co), perfil(so_)
    for y in range(H):
        r[y][cn[y], :3] = pc[y][:3]; r[y][sn[y], :3] = ps[y][:3]
    ao = a_nit[..., 3].astype(float); av = a_var[..., 3].astype(float)
    k = (av[ao > 100].mean() / max(1.0, ao[ao > 100].mean())) if (ao > 100).any() else 1.0
    r[..., 3] = np.clip(novo[..., 3].astype(float) * k, 0, 255).astype(np.uint8)
    return r


def deriva(num, i, a_nit_idx, novo, claro=170):
    a_nit = tc.textura(num, a_nit_idx)[1]; a_var = tc.textura(num, i)[1]
    s, a1, a2, cor, err = ajuste(a_nit, a_var)
    if s <= 3 and err < 8: print("   var %d: mesma forma (%.1f)" % (i, err)); return deriva_mesma_forma(novo, a_nit, a_var, claro)
    print("   var %d: blur sigma %d erro %.1f" % (i, s, err)); return deriva_borrada(novo, s, a1, a2, cor)


# ---------------- A. letreiro da loja ----------------
if "A" in so:
    num, idx = 6162, 13
    Y0, Y1, X0, X1 = 76, 116, 70, 636          # faixa do texto no tabuão (medida na régua)
    _, a = tc.textura(num, idx); _, ade = tc.textura(6158, 13)
    def recorte_inv(src):
        inv = inverte(src); inv[:Y0] = 0; inv[Y1:] = 0; inv[:, :X0] = 0; inv[:, X1:] = 0; return inv
    tc._override[(num, idx)] = recorte_inv(a); tc._override[(6158, 13)] = recorte_inv(ade)
    lib = tc.Biblioteca(lim=120, claro=175)
    m = lib.add_guiado(num, idx, "Armas y herramientas de MURAMASA", TIMESB)
    m2 = lib.add_guiado(6158, 13, "Waffen und Ausrüstung MURAMASA", TIMESB)
    del tc._override[(num, idx)]; del tc._override[(6158, 13)]
    print("A: segs", [(b - x) for x, b in m['segs']], "gap", m['gap'], "esp", m['espaco'], "| DE", [(b - x) for x, b in m2['segs']])
    lum = a[..., :3].astype(int).mean(2)
    # 1) apaga o texto antigo por interpolação horizontal (o veio da madeira é horizontal)
    novo = a.copy()
    texto_mask = (lum < 95)
    for k in range(2): texto_mask |= np.roll(texto_mask, 1, 1) | np.roll(texto_mask, -1, 1) | np.roll(texto_mask, 1, 0) | np.roll(texto_mask, -1, 0)
    for y in range(Y0, Y1):
        row = novo[y, X0:X1].astype(float); msk = texto_mask[y, X0:X1]
        if not msk.any() or msk.all(): continue
        xs = np.arange(X1 - X0); good = ~msk
        for c in range(4): row[msk, c] = np.interp(xs[msk], xs[good], row[good, c])
        novo[y, X0:X1] = row.astype(np.uint8)
    # 2) renderiza a frase nova com Times Bold (a fonte do letreiro é uma serifada bold parecida),
    #    na mesma altura de caixa alta e centrada no mesmo ponto, e pinta a tinta escura sobre o tabuão limpo
    tinta = (lum < 95); ys_ = np.nonzero(tinta[Y0:Y1, X0:X1].any(1))[0]; xs_ = np.nonzero(tinta[Y0:Y1, X0:X1].any(0))[0]
    top, bot = Y0 + ys_.min(), Y0 + ys_.max() + 1; L0, L1 = X0 + xs_.min(), X0 + xs_.max() + 1
    cap = ts._render("ARMAS", TIMESB, 100).shape[0]
    ref = ts._render("Armas y herramientas de MURAMASA", TIMESB, 100)   # inclui descendente do y
    alt_tot = bot - top
    tam = 100.0 * alt_tot / ref.shape[0]
    r_es = ts._render("Armas y herramientas de MURAMASA", TIMESB, tam)
    xscale = (L1 - L0) / r_es.shape[1]
    r_pt = ts._render("Armas e ferramentas de MURAMASA", TIMESB, tam, xscale)
    cor_tinta = np.percentile(a[Y0:Y1, X0:X1][tinta[Y0:Y1, X0:X1]][..., :3], 25, axis=0)
    cx = (L0 + L1) // 2; x0 = cx - r_pt.shape[1] // 2; y0 = top
    h, w = r_pt.shape
    rp = r_pt.astype(float); rp = np.maximum(rp, np.roll(rp, 1, 1)); rp = np.maximum(rp, np.roll(rp, 1, 0))
    alfa = np.clip(rp / 255.0 * 1.15, 0, 1)
    reg = novo[y0:y0 + h, x0:x0 + w, :3].astype(float)
    novo[y0:y0 + h, x0:x0 + w, :3] = (reg * (1 - alfa[..., None]) + cor_tinta * alfa[..., None]).astype(np.uint8)
    print("A: tinta", cor_tinta.astype(int), "altura", alt_tot, "fonte %.1f xscale %.2f" % (tam, xscale))
    previas += [a[:, :1024], novo[:, :1024]]
    tc.gravar(num, {idx: novo}, modo)

# ---------------- B. Menú -> Menu ----------------
if "B" in so:
    for num in (6156, 6158, 6160, 6162):
        _, menu = tc.textura(num, 15); _, menu_es = tc.textura(num, 17)
        previas += [menu_es[:, :256], menu[:, :256]]
        tc.gravar(num, {17: menu.copy()}, modo)

# ---------------- C. Nuevo Récord -> Novo Recorde ----------------
if "C" in so:
    for num, idx in ((5401, 20), (6379, 18)):
        lib = tc.Biblioteca(lim=120, claro=170)
        m = lib.add(num, idx, "Nuevo Récord", forcar=True); lib.add(6371, 18, "New Record", forcar=True)
        print("C: %d segs" % num, [(b - x) for x, b in m['segs']], "gap", m['gap'], "esp", m['espaco'])
        cx = (m['x0'] + m['x1']) // 2
        novo = tc.compor(lib, "Novo Recorde", ref=(num, idx), folga=(0, 6), limpar=4, centro=cx, pref=[(num, idx), (6371, 18)])
        previas += [tc.textura(num, idx)[1], novo]
        tc.gravar(num, {idx: novo}, modo)

# ---------------- D. Muertos -> Mortos ----------------
if "D" in so:
    num = 6399; g = g1t.parse(dbx.get(num)); saidas = {}
    for t in g['tex']:
        if not (t['w'] == 1024 and t['h'] == 256 and t['fmt'] == 1): continue
        _, a = tc.textura(num, t['i'])
        cl = 170 if (a[a[..., 3] > 120][..., :3].mean() > 150) else 90
        col = tc.mascara(a, 120, cl).any(0)
        runs = []; ini = None; folga = 0
        for x in range(a.shape[1] + 1):
            on = x < a.shape[1] and col[x]
            if on and ini is None: ini = x
            if on: folga = 0
            elif ini is not None:
                folga += 1
                if folga > 10: runs.append((ini, x - folga)); ini = None; folga = 0
        if not runs or runs[-1][1] - runs[-1][0] < 150: continue
        if 'WX' not in globals(): WX = runs[-1]
        wx0, wx1 = WX
        ov = a.copy(); ov[:, :wx0 - 2] = 0; ov[:, wx1 + 2:] = 0
        tc._override[(num, t['i'])] = ov
        lib = tc.Biblioteca(lim=120, claro=cl)
        m = lib.add_guiado(num, t['i'], "Muertos", TIMESB.replace("timesbd", "times"))
        del tc._override[(num, t['i'])]
        cand = m['segs']
        if len(saidas) == 0: print("D: %d/%d palavra %d-%d segs" % (num, t['i'], wx0, wx1), [(b - x) for x, b in cand])
        novo = tc.compor(lib, "Mortos", ref=(num, t['i']), folga=(0, 8), limpar=6, inicio=cand[0][0])
        # mantém tudo à esquerda do M (fragmento do número) e limpa o resto
        res = a.copy(); res[:, cand[0][0] - 2:] = 0
        m2 = novo[..., 3] > res[..., 3]; res[m2] = novo[m2]
        saidas[t['i']] = res
        if len(saidas) <= 3: previas += [a[:, :700], res[:, :700]]
    print("D: texturas Muertos:", sorted(saidas))
    tc.gravar(num, saidas, modo)

# ---------------- E. MISIÓN -> MISSÕES ----------------
if "E" in so:
    def missoes(num, idx, num_it, idx_it, num_en, idx_en, claro=170):
        lib = tc.Biblioteca(lim=120, claro=claro)
        m = lib.add(num, idx, "MISIÓN", forcar=True)
        lib.add(num_it, idx_it, "MISSIONE", forcar=True); lib.add(num_en, idx_en, "MISSIONS", forcar=True)
        print("E: %d/%d segs" % (num, idx), [(b - x) for x, b in m['segs']], "gap", m['gap'])
        ow, _, do = lib.pega("O", (num_en, idx_en), (0, 8), 6)
        o_til = tc.com_acento(ow, "~", claro=claro, frac=0.85, dy=-3, fonte=TIMESB, sombra=(3, 3), grosso=3)
        cx = (m['x0'] + m['x1']) // 2
        return tc.compor(lib, "MISSÕES", ref=(num, idx), folga=(0, 8), limpar=6, extras={"Õ": (o_til, do, 8)}, centro=cx,
                         pref=[(num, idx), (num_it, idx_it), (num_en, idx_en)])
    # 5409 (0-4): nítidas 4 (branca) e 2/3 (azul); IT 5415, EN 5411 mesmos idx
    saidas = {}
    for idx, cl in ((4, 170), (3, 110), (2, 110)):
        try: saidas[idx] = missoes(5409, idx, 5415, idx, 5411, idx, claro=cl)
        except SystemExit as e: print("   falhou", idx, e)
    for idx in (0, 1):
        base = 4 if 4 in saidas else list(saidas)[0]
        saidas[idx] = deriva(5409, idx, base, saidas[base])
    previas += [tc.textura(5409, 4)[1], saidas[4]] + [saidas[i] for i in (3, 2, 0, 1) if i in saidas]
    tc.gravar(5409, saidas, modo)
    # grupo 5417-5431: ES = 5417 e 5425 (2 branca, 5 azul); IT = 5423/5431; EN = 5419/5427
    for num_es, num_it, num_en in ((5417, 5423, 5419), (5425, 5431, 5427)):
        saidas = {}
        for idx, cl in ((2, 170), (5, 110)):
            try: saidas[idx] = missoes(num_es, idx, num_it, idx, num_en, idx, claro=cl)
            except (SystemExit, AssertionError, KeyError, IndexError) as e: print("   %d/%d falhou: %s" % (num_es, idx, e))
        previas += [tc.textura(num_es, 2)[1]] + [saidas[i] for i in (2, 5) if i in saidas]
        if saidas: tc.gravar(num_es, saidas, modo)

# ---------------- F. Sí / No -> Sim / Não ----------------
if "F" in so:
    num = 5435; saidas = {}
    pares = {1: ("Sí", "Sim"), 2: ("No", "Não"), 9: ("Sí", "Sim"), 13: ("No", "Não")}
    for idx, (es, pt) in pares.items():
        _, a = tc.textura(num, idx)
        saidas[idx] = ts.sintetiza(a, es, pt, TIMESB, claro=(60 if idx in (1, 2) else 150), debug=True)
        previas += [a, saidas[idx]]
    for idx in (7, 8, 11, 12):
        best = None
        for base in (1, 2, 9, 13):
            s, a1, a2, cor, err = ajuste(tc.textura(num, base)[1], tc.textura(num, idx)[1])
            if best is None or err < best[0]: best = (err, base, s, a1, a2, cor)
        err, base, s, a1, a2, cor = best
        saidas[idx] = deriva_borrada(saidas[base], s, a1, a2, cor); print("F: var %d <- base %d sigma %d erro %.1f" % (idx, base, s, err))
        previas += [saidas[idx]]
    tc.gravar(num, saidas, modo)

# ---------------- G. Nivel -> Nível ----------------
if "G" in so:
    lib = tc.Biblioteca(lim=120, claro=170)
    m = lib.add(4323, 8, "Nivel", forcar=True); print("G: segs", [(b - x) for x, b in m['segs']])
    iw, _, di = lib.pega("i", (4323, 8), (0, 3), 2)
    # tira o pingo do i (componente de cima) e põe o acento no lugar dele
    core = (iw[..., 3] > 120) & (iw[..., :3].mean(2) > 170); rows = np.nonzero(core.any(1))[0]
    vazias = [y for y in range(rows.min(), rows.max()) if not core[y].any()]
    if vazias:
        corte = vazias[0]; iw = iw.copy(); iw[:corte + 1] = 0
    i_ac = tc.com_acento(iw, "´", claro=170, frac=1.6, dy=1, fonte=TIMESB, sombra=(1, 1), grosso=1)
    novo = tc.compor(lib, "Nível", ref=(4323, 8), folga=(0, 3), limpar=2, extras={"í": (i_ac, di, 3)})
    previas += [tc.textura(4323, 8)[1], novo]
    tc.gravar(4323, {8: novo}, modo)

tc.previa(previas, os.path.join(out, "p_final.png"), escala=0.7)
print("previa ok")
