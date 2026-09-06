# -*- coding: utf-8 -*-
"""v3.1: 'Carregando...' (5409/9), rótulos da loja (5885: Essência 9/10,
Essência MÁX 14/15, Lançar 25) e prévia. Uso: python tex_loja.py [teste|aplicar]"""
import sys, os
sys.path.insert(0, r"D:\ng_trad_work\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import texcomp as tc, numpy as np

modo = sys.argv[1] if len(sys.argv) > 1 else "teste"
out = r"C:\Users\wende\AppData\Local\Temp\claude\C--Users-wende\189b77d5-b7c9-4488-b010-0f88e485cd68\scratchpad"
F = (5, 6)

# ---- Carregando... ----
lib = tc.Biblioteca(lim=120, claro=170)
lib.add(5409, 9, "Cargando..."); lib.add(5415, 9, "Caricamento...")
carreg = tc.compor(lib, "Carregando...", ref=(5409, 9), folga=F, limpar=5)

# ---- Essência (idx 10 ES e 9 EN) ----
lib2 = tc.Biblioteca(lim=120, claro=150)
lib2.add(5885, 10, "Esencia"); lib2.add(5885, 9, "Essence")
e_win, _, d0 = lib2.pega("e", (5885, 10), F, 2)
e_circ = tc.com_acento(e_win, "^", frac=0.6, dy=1, grosso=1)
ess = tc.compor(lib2, "Essência", ref=(5885, 10), folga=F, limpar=2, extras={"ê": (e_circ, d0, F[1])})

# ---- Essência MÁX: só a linha de cima (y < 25) de 15 (ES) e 14 (EN) ----
_, a15 = tc.textura(5885, 15); _, a14 = tc.textura(5885, 14)
top15 = a15.copy(); top15[25:] = 0
tc._override[(5885, 15)] = top15
lib3 = tc.Biblioteca(lim=120, claro=150)
m = lib3.add(5885, 15, "Esencia"); print("MAX ES linha de cima segs:", [(b - a) for a, b in m['segs']])
e2, _, d2 = lib3.pega("e", (5885, 15), F, 2)
e2c = tc.com_acento(e2, "^", frac=0.6, dy=1, grosso=1)
top_novo = tc.compor(lib3, "Essência", ref=(5885, 15), folga=F, limpar=2, extras={"ê": (e2c, d2, F[1])})
del tc._override[(5885, 15)]
essmax15 = a15.copy(); essmax15[:25] = top_novo[:25]
essmax14 = a14.copy(); essmax14[:25] = top_novo[:25]

# ---- Lançar (pílula): base Lancer(26), 5ª letra <- 'a' de Lanzar(25), cedilha sob o c ----
lib4 = tc.Biblioteca(lim=120, claro=150)
mz = lib4.add(5885, 25, "Lanzar"); mc = lib4.add(5885, 26, "Lancer")
print("Lanzar segs", mz['segs']); print("Lancer segs", mc['segs'])
_, az = tc.textura(5885, 25); _, ac_ = tc.textura(5885, 26)
res = ac_.copy()
za = mz['segs'][4]; ce = mc['segs'][4]
wa = za[1] - za[0]; x_dest = ce[0] + (ce[1] - ce[0] - wa) // 2
res[:, x_dest - 1:x_dest - 1 + wa + 2] = az[:, za[0] - 1:za[0] - 1 + wa + 2]
c0, c1 = mc['segs'][3]
janela = res[:, c0 - 2:c1 + 2].copy()
janela = tc.com_acento(janela, "¸", frac=0.55, dy=-2, embaixo=True, opaco=True)
res[:, c0 - 2:c1 + 2] = janela
lancar = res

_, esc = tc.textura(5885, 10); _, car = tc.textura(5409, 9)
tc.previa([car, carreg], os.path.join(out, "p_carreg.png"), escala=3.0)
tc.previa([esc, ess, a15, essmax15, az, lancar], os.path.join(out, "p_loja.png"), escala=4.0)
print("previas ok")

tc.gravar(5409, {9: carreg}, modo)
tc.gravar(5885, {9: ess, 10: ess, 14: essmax14, 15: essmax15, 25: lancar}, modo)
