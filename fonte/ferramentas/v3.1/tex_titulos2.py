# -*- coding: utf-8 -*-
"""v3.1: 5401 MISIÓN COMPLETA -> MISSÃO COMPLETA (2 linhas, serif azul)
         5435 FIN DE LA PARTIDA -> FIM DA PARTIDA (serif decorativa; M de GAME OVER 5433)
         6389 SUPERVIVENCIA -> SOBREVIVÊNCIA (dourado; O de 6387, B de 6385)
         6379 Cuenta de bajas -> Contagem de mortes (serif regular; o,m,r de 6373, g de 6375)
Segmentação guiada por fonte TTF (letras serifadas se tocam). Variantes: a mais nítida é
composta; as de mesma forma recebem cor por linha/classe; as borradas, blur ajustado.
Uso: python tex_titulos2.py [teste|aplicar] [so=5401]"""
import sys, os
sys.path.insert(0, r"D:\ng_trad_work\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import texcomp as tc, texsint as ts, dbx, g1t, numpy as np
from PIL import Image, ImageFilter

args = sys.argv[1:]
modo = "aplicar" if "aplicar" in args else "teste"
so = [int(a.split("=")[1]) for a in args if a.startswith("so=")]
out = r"C:\Users\wende\AppData\Local\Temp\claude\C--Users-wende\189b77d5-b7c9-4488-b010-0f88e485cd68\scratchpad"
TIMESB = r"C:\Windows\Fonts\timesbd.ttf"; TIMES = r"C:\Windows\Fonts\times.ttf"


def grandes(num, w, h):
    g = g1t.parse(dbx.get(num))
    return [t['i'] for t in g['tex'] if t['w'] == w and t['h'] == h and t['fmt'] == 1]


def nitidez(num, i):
    a = tc.textura(num, i)[1]; lum = a[..., :3].astype(np.float32).mean(2) * (a[..., 3] / 255.0)
    return float(np.abs(np.diff(lum, axis=1)).mean())


def blur(alpha, s):
    if s <= 0: return alpha.astype(np.float32)
    return np.asarray(Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))).astype(np.float32)


def ajuste(a_nit, a_var):
    al = a_nit[..., 3].astype(np.float32); av = a_var[..., 3].astype(np.float32)
    sub = (slice(0, None, 2), slice(0, None, 2)); best = None
    for s in (0, 3, 5, 8, 11, 14, 18, 24, 30, 40, 55):
        b = blur(al, s); X = np.stack([al[sub].ravel(), b[sub].ravel()], 1); y = av[sub].ravel()
        coef, *_ = np.linalg.lstsq(X, y, rcond=None); err = np.abs(np.clip(X @ coef, 0, 255) - y).mean()
        if best is None or err < best[0]: best = (err, s, coef)
    err, s, coef = best; m = a_var[..., 3] > 100
    cor = np.median(a_var[m][..., :3], axis=0) if m.sum() else np.array([255, 255, 255])
    return s, float(coef[0]), float(coef[1]), cor, err


def escala_alpha(al, k):
    """Amplia/reduz o alfa em torno do centro da tinta, mantendo o tamanho da tela."""
    if abs(k - 1.0) < 1e-3: return al.astype(np.float32)
    H, W = al.shape
    ys = np.nonzero((al > 60).any(1))[0]; xs = np.nonzero((al > 60).any(0))[0]
    cy = (ys.min() + ys.max()) / 2 if len(ys) else H / 2; cx = (xs.min() + xs.max()) / 2 if len(xs) else W / 2
    im = Image.fromarray(al.astype(np.uint8)).resize((max(1, int(W * k)), max(1, int(H * k))), Image.BILINEAR)
    big = np.asarray(im).astype(np.float32)
    out = np.zeros((H, W), np.float32)
    # posiciona para que o centro da tinta coincida
    ox = int(round(cx * k - cx)); oy = int(round(cy * k - cy))
    ya, xa = max(0, -oy), max(0, -ox); yb, xb = min(H, big.shape[0] - oy), min(W, big.shape[1] - ox)
    out[ya:yb, xa:xb] = big[ya + oy:yb + oy, xa + ox:xb + ox]
    return out


def ajuste_escala(a_nit, a_var):
    best = None
    for k in (1.0, 1.1, 1.2, 1.3, 1.45, 1.6):
        an = a_nit.copy(); an[..., 3] = np.clip(escala_alpha(a_nit[..., 3], k), 0, 255).astype(np.uint8)
        s, a1, a2, cor, err = ajuste(an, a_var)
        if best is None or err < best[-1]: best = (k, s, a1, a2, cor, err)
    return best


def deriva_borrada(novo, s, a1, a2, cor, k=1.0):
    al = escala_alpha(novo[..., 3], k); alpha = np.clip(a1 * al + a2 * blur(al, s), 0, 255)
    r = np.zeros_like(novo); r[..., :3] = cor.astype(np.uint8); r[..., 3] = alpha.astype(np.uint8); return r


def deriva_mesma_forma(novo, a_nit, a_var, claro=170):
    """Mesma silhueta: copia, por linha e por classe (núcleo claro / resto), a cor e o alfa relativo do original."""
    r = novo.copy(); H = novo.shape[0]
    def classes(a):
        lum = a[..., :3].mean(2); op = a[..., 3] > 60; return op & (lum > claro), op & (lum <= claro)
    co, so_ = classes(a_nit); cn, sn = classes(novo)
    def perfil(mask):
        p = [None] * H
        for y in range(H):
            if mask[y].sum() >= 3: p[y] = np.median(a_var[y][mask[y]], axis=0)   # RGBA
        ys = [k for k in range(H) if p[k] is not None]
        for y in range(H):
            if p[y] is None: p[y] = p[min(ys, key=lambda k: abs(k - y))] if ys else np.array([128, 128, 128, 255])
        return p
    pc, ps = perfil(co), perfil(so_)
    for y in range(H):
        r[y][cn[y], :3] = pc[y][:3]; r[y][sn[y], :3] = ps[y][:3]
    # alfa: mantém a silhueta nova, escalada pela relação de alfa do original
    ao = a_nit[..., 3].astype(float); av = a_var[..., 3].astype(float)
    k = (av[ao > 100].mean() / max(1.0, ao[ao > 100].mean())) if (ao > 100).any() else 1.0
    r[..., 3] = np.clip(novo[..., 3].astype(float) * k, 0, 255).astype(np.uint8)
    return r


def deriva_todas(num, ids, nitido, novo, claro=170, sint=None):
    """sint: função a_var -> textura nova sintetizada a partir daquela variante (quando não deriva bem)."""
    a_nit = tc.textura(num, nitido)[1]; saidas = {nitido: novo}
    for i in ids:
        if i == nitido: continue
        a_var = tc.textura(num, i)[1]
        if a_var.shape != a_nit.shape:
            print("   var %d: tamanho diferente %s, pulada" % (i, a_var.shape)); continue
        s, a1, a2, cor, err = ajuste(a_nit, a_var)
        if err >= 8:
            k, s2, b1, b2, cor2, err2 = ajuste_escala(a_nit, a_var)
            if err2 < 8 and k > 1.0:
                saidas[i] = deriva_borrada(novo, s2, b1, b2, cor2, k)
                print("   var %d: escala %.2f sigma %d erro %.1f" % (i, k, s2, err2)); continue
            if (num, i) in FORCAR_ESCALA:
                saidas[i] = deriva_borrada(novo, s2, b1, b2, cor2, k)
                print("   var %d: escala forçada %.2f sigma %d erro %.1f" % (i, k, s2, err2)); continue
            if err >= 20:
                print("   var %d: não é o mesmo texto (erro %.1f), mantida" % (i, err)); continue
            if sint is not None:
                saidas[i] = sint(a_var); print("   var %d: sintetizada do próprio original (erro %.1f)" % (i, err)); continue
        if s <= 3 and err < 8:
            saidas[i] = deriva_mesma_forma(novo, a_nit, a_var, claro); print("   var %d: mesma forma (erro %.1f)" % (i, err))
        else:
            saidas[i] = deriva_borrada(novo, s, a1, a2, cor); print("   var %d: sigma %d a1 %.2f a2 %.2f cor %s erro %.1f" % (i, s, a1, a2, cor.astype(int), err))
    return saidas


def linhas(a, lim=120, claro=None, n=2):
    m = tc.mascara(a, lim, claro).any(1); out_ = []; ini = None
    for y in range(len(m)):
        if m[y] and ini is None: ini = y
        elif not m[y] and ini is not None: out_.append((ini, y)); ini = None
    if ini is not None: out_.append((ini, len(m)))
    out_.sort(key=lambda l: l[1] - l[0], reverse=True)
    return sorted(out_[:n])


FORCAR_ESCALA = {(6379, 12)}
previas = []
def quer(num): return not so or num in so


# ---------------- 5401 MISSÃO COMPLETA ----------------
if quer(5401):
    ids = grandes(5401, 2048, 512); nit = max(ids, key=lambda i: nitidez(5401, i))
    a = tc.textura(5401, nit)[1]
    l1, l2 = linhas(a, 120, 170); print("5401 variantes", ids, "nítida", nit, "linhas", l1, l2)
    novo1 = ts.sintetiza(a, "MISIÓN", "MISSÃO", TIMESB, claro=170, rows=l1, debug=True)
    novo = a.copy(); ya, yb = max(0, l1[0] - 30), (l1[1] + l2[0]) // 2
    novo[ya:yb] = novo1[ya:yb]
    def sint5401(av):
        ls_ = linhas(av, 60, None)
        L1, L2 = (ls_[0], ls_[1]) if len(ls_) >= 2 else (l1, l2)
        n1 = ts.sintetiza(av, "MISIÓN", "MISSÃO", TIMESB, claro=170, rows=L1, debug=True)
        r = av.copy(); ya_, yb_ = max(0, L1[0] - 30), (L1[1] + L2[0]) // 2; r[ya_:yb_] = n1[ya_:yb_]; return r
    saidas = deriva_todas(5401, ids, nit, novo, sint=sint5401)
    previas += [a[:, :1300], novo[:, :1300]] + [saidas[i][:, :1300] for i in ids if i in saidas and i != nit]
    tc.gravar(5401, saidas, modo)

# ---------------- 5435 FIM DA PARTIDA ----------------
if quer(5435):
    ids = grandes(5435, 2048, 256); nit = max(ids, key=lambda i: nitidez(5435, i))
    ids2 = grandes(5433, 2048, 256); nit2 = max(ids2, key=lambda i: nitidez(5433, i))
    print("5435 variantes", ids, "nítida", nit, "| 5433 nítida", nit2)
    lib = tc.Biblioteca(lim=120, claro=150)
    m = lib.add_guiado(5435, nit, "FIN DE LA PARTIDA", TIMESB, maiusc_grandes={0, 16})
    mg = lib.add_guiado(5433, nit2, "GAME OVER", TIMESB, maiusc_grandes={0, 8})
    print("   segs", [(b - x) for x, b in m['segs']], "gap", m['gap'], "esp", m['espaco'], "| GAME OVER", [(b - x) for x, b in mg['segs']])
    F = (0, 10)
    a_src = tc.textura(5435, nit)[1]; segs = m['segs']
    A_big = a_src[:, segs[-1][0]:min(a_src.shape[1], segs[-1][1] + 10)]
    cx = (m['x0'] + m['x1']) // 2
    novo = tc.compor(lib, "FIM DA PARTIDÂ", ref=(5435, nit), folga=F, limpar=6, extras={"Â": (A_big, 0, 10)}, centro=cx, espaco=40,
                     pref=[(5435, nit), (5433, nit2)])
    saidas = deriva_todas(5435, ids, nit, novo, claro=150)
    previas += [a_src[:, :1300], novo[:, :1300]] + [saidas[i][:, :1300] for i in ids if i in saidas and i != nit]
    tc.gravar(5435, saidas, modo)

# ---------------- 6389 SOBREVIVÊNCIA ----------------
if quer(6389):
    saidas_tot = {}
    for (w, h) in ((2048, 512), (2048, 256)):
        ids = grandes(6389, w, h)
        if not ids: continue
        nit = max(ids, key=lambda i: nitidez(6389, i))
        nO = max(grandes(6387, w, h), key=lambda i: nitidez(6387, i)); nB = max(grandes(6385, w, h), key=lambda i: nitidez(6385, i))
        print("6389 %dx%d variantes" % (w, h), ids, "nítida", nit, "| 6387", nO, "6385", nB)
        a_src0 = tc.textura(6389, nit)[1]
        novo = ts.sintetiza(a_src0, "SUPERVIVENCIA", "SOBREVIVÊNCIA", TIMESB, claro=150, debug=True)
        saidas = deriva_todas(6389, ids, nit, novo, claro=150,
                              sint=lambda av: ts.sintetiza(av, "SUPERVIVENCIA", "SOBREVIVÊNCIA", TIMESB, claro=150)); saidas_tot.update(saidas)
        a_src = tc.textura(6389, nit)[1]
        previas += [a_src[:, :1300], novo[:, :1300]] + [saidas[i][:, :1300] for i in ids if i in saidas and i != nit]
    tc.gravar(6389, saidas_tot, modo)

# ---------------- 6379 Contagem de mortes ----------------
if quer(6379):
    ids = grandes(6379, 2048, 512); nit = max(ids, key=lambda i: nitidez(6379, i))
    n73 = max(grandes(6373, 2048, 512), key=lambda i: nitidez(6373, i))
    n75 = max(grandes(6375, 2048, 512), key=lambda i: nitidez(6375, i))
    print("6379 variantes", ids, "nítida", nit, "| 6373", n73, "6375", n75)
    a_src0 = tc.textura(6379, nit)[1]
    novo = ts.sintetiza(a_src0, "Cuenta de bajas", "Contagem de mortes", TIMES, claro=170, centro=False, debug=True)
    saidas = deriva_todas(6379, ids, nit, novo, claro=170,
                          sint=lambda av: ts.sintetiza(av, "Cuenta de bajas", "Contagem de mortes", TIMES, claro=170, centro=False))
    a_src = tc.textura(6379, nit)[1]
    previas += [a_src[:, :1300], novo[:, :1300]] + [saidas[i][:, :1300] for i in ids if i in saidas and i != nit]
    tc.gravar(6379, saidas, modo)

tc.previa(previas, os.path.join(out, "p_tit2.png"), escala=0.45)
print("previa ok")
