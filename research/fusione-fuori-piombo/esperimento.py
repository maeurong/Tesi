"""Issue #188: `occ.fuse` di due prismi fuori piombo -> un solido o N?

Prismi costruiti come fara' `scrivi_step` (ADR 2026-09-07): contorno nel piano
locale -> coordinate globali origine + u*e1 + v*e2 -> addPlaneSurface -> extrude
lungo asse*L. Unita' mm. Esegui dalla radice del repo:

    uv run --project meshrec python research/fusione-fuori-piombo/esperimento.py
"""
import math
import pathlib
import tempfile
import time

import gmsh

B, H_TRAVE, L_TRAVE, H_PIL = 300.0, 500.0, 4000.0, 3000.0
V_TRAVE = B * H_TRAVE * L_TRAVE  # 600e6
SEZ = [(-B / 2, -B / 2), (B / 2, -B / 2), (B / 2, B / 2), (-B / 2, B / 2)]
SEZ_TRAVE = [(-B / 2, 0.0), (B / 2, 0.0), (B / 2, H_TRAVE), (-B / 2, H_TRAVE)]


def prisma(contorno, origine, e1, e2, asse, lunghezza):
    occ = gmsh.model.occ
    punti = [occ.addPoint(*(origine[k] + u * e1[k] + v * e2[k] for k in range(3)))
             for u, v in contorno]
    linee = [occ.addLine(punti[i], punti[(i + 1) % len(punti)]) for i in range(len(punti))]
    sup = occ.addPlaneSurface([occ.addCurveLoop(linee)])
    out = occ.extrude([(2, sup)], *(a * lunghezza for a in asse))
    return [t for d, t in out if d == 3][0]


def trave():
    return prisma(SEZ_TRAVE, (-500.0, 0.0, H_PIL), (0, 1, 0), (0, 0, 1), (1, 0, 0), L_TRAVE)


def pilastro(theta_deg=0.0, lunghezza=None):
    th = math.radians(theta_deg)
    L = H_PIL / math.cos(th) if lunghezza is None else lunghezza
    # asse inclinato di theta attorno a y; e1 nel piano xz, e2 = y
    return prisma(SEZ, (0.0, 0.0, 0.0), (math.cos(th), 0, -math.sin(th)), (0, 1, 0),
                  (math.sin(th), 0, math.cos(th)), L), L


# --- casi: ogni costruttore rende ([tag volumi], volume analitico atteso, solidi attesi)
def caso_contatto():
    p, _ = pilastro(0.0)
    return [p, trave()], B * B * H_PIL + V_TRAVE, 1


def caso_piombo(theta):
    # testa del pilastro centrata su z=3000: meta' compenetra la trave (cuneo),
    # meta' resta sotto. Cuneo = B * tan(th) * (B/2)^2 / 2.
    def f():
        p, L = pilastro(theta)
        cuneo = B * math.tan(math.radians(theta)) * (B / 2) ** 2 / 2
        return [p, trave()], B * B * L + V_TRAVE - cuneo, 1
    return f


def caso_piombo_tangente(theta):
    # spigolo alto della testa esattamente sull'intradosso: contatto di spigolo, non di faccia
    def f():
        th = math.radians(theta)
        L = (H_PIL - B / 2 * math.sin(th)) / math.cos(th)
        p, _ = pilastro(theta, L)
        return [p, trave()], B * B * L + V_TRAVE, 2
    return f


def caso_compenetrazione(mm):
    # mm > 0 compenetra, mm < 0 lascia un gioco; il volume atteso e' quello geometrico
    def f():
        p, _ = pilastro(0.0, H_PIL + mm)
        v = B * B * H_PIL + V_TRAVE if mm >= 0 else B * B * (H_PIL + mm) + V_TRAVE
        return [p, trave()], v, 1 if mm >= 0 else 2
    return f


def caso_identici():
    a, _ = pilastro(0.0)
    b, _ = pilastro(0.0)
    return [a, b], B * B * H_PIL, 1


CASI = [
    ("1 contatto", caso_contatto),
    ("2 piombo 1 deg", caso_piombo(1.0)),
    ("2 piombo 2 deg", caso_piombo(2.0)),
    ("2 piombo 3 deg", caso_piombo(3.0)),
    ("2t tangente 2 deg", caso_piombo_tangente(2.0)),
    ("3 compenetra 3 mm", caso_compenetrazione(3.0)),
    ("G gioco 0.05 mm", caso_compenetrazione(-0.05)),
    ("G gioco 0.5 mm", caso_compenetrazione(-0.5)),
    ("D disgiunti 10 mm", caso_compenetrazione(-10.0)),
    ("D identici", caso_identici),
]


# --- varianti: (nome, opzioni prima della costruzione, passo fra costruzione e fuse)
def _noop(v):
    return v


def _dup(v):
    gmsh.model.occ.removeAllDuplicates()
    return [t for d, t in gmsh.model.occ.getEntities(3)]


def _frag(v):
    out, _ = gmsh.model.occ.fragment([(3, v[0])], [(3, t) for t in v[1:]])
    return [t for d, t in out if d == 3]


def _heal(v):
    return [t for d, t in gmsh.model.occ.healShapes() if d == 3]


G = "Geometry."
VARIANTI = [
    ("default", [], _noop),
    ("Tolerance=0.1", [(G + "Tolerance", 0.1)], _noop),
    ("Tolerance=1.0", [(G + "Tolerance", 1.0)], _noop),
    ("ToleranceBoolean=0.1", [(G + "ToleranceBoolean", 0.1)], _noop),
    ("ToleranceBoolean=1.0", [(G + "ToleranceBoolean", 1.0)], _noop),
    ("removeAllDuplicates", [], _dup),
    ("fragment poi fuse", [], _frag),
    ("OCCFix*=1", [(G + "OCCFixDegenerated", 1), (G + "OCCFixSmallEdges", 1), (G + "OCCFixSmallFaces", 1)], _noop),
    ("healShapes", [], _heal),
]
# tolleranza > spessore minimo (300 mm): il tetto del parametro
DEGENERI_TOL = [
    ("ToleranceBoolean=400", [(G + "ToleranceBoolean", 400.0)], _noop),
    ("Tolerance=400", [(G + "Tolerance", 400.0)], _noop),
]
SEP = " " + chr(124) + " "  # ponytail: la barra del markdown, tenuta fuori dal sorgente


def esegui(costruttore, opzioni, passo, step):
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.Verbosity", 0)
        for nome, valore in opzioni:
            gmsh.option.setNumber(nome, valore)
        gmsh.model.add("x")
        vols, v_att, n_att = costruttore()
        gmsh.model.occ.synchronize()
        vols = passo(vols)
        t0 = time.perf_counter()
        out = [(3, vols[0])]
        if len(vols) > 1:
            out, _ = gmsh.model.occ.fuse([(3, vols[0])], [(3, t) for t in vols[1:]])
        ms = (time.perf_counter() - t0) * 1e3
        gmsh.model.occ.synchronize()
        solidi = [t for d, t in out if d == 3]
        v = sum(gmsh.model.occ.getMass(3, t) for t in solidi)
        facce, spigoli = gmsh.model.getEntities(2), gmsh.model.getEntities(1)
        # schegge: la faccia piu' piccola e lo spigolo piu' corto del risultato
        a_min = min(gmsh.model.occ.getMass(2, t) for _, t in facce)
        l_min = min(gmsh.model.occ.getMass(1, t) for _, t in spigoli)
        gmsh.write(str(step))
        gmsh.model.add("rilettura")
        letti = gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        s_letti = [t for d, t in letti if d == 3]
        v_letti = sum(gmsh.model.occ.getMass(3, t) for t in s_letti)
        riletto = "=" if len(s_letti) == len(solidi) and abs(v_letti - v) <= 1e-9 * v \
            else f"{len(s_letti)} solidi, {v_letti:.7g}"
        flag = "" if len(solidi) == n_att else " !!"
        return [f"{len(solidi)} ({n_att}){flag}", f"{(v - v_att) / v_att:+.2e}", len(facce), len(spigoli),
                f"{a_min:.4g}", f"{l_min:.4g}", f"{ms:.1f}", riletto]
    except Exception as e:  # ponytail: l'eccezione e' un risultato, non un guasto dello script
        return ["ERRORE " + type(e).__name__ + ": " + str(e).strip()[:70]] + [""] * 7
    finally:
        gmsh.finalize()


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="fuse188-"))
    print(f"gmsh {gmsh.__version__}, step in {tmp}\n")
    testa = ["caso", "variante", "solidi (attesi)", "scarto vol. rel.", "facce", "spigoli",
             "faccia min mm2", "spigolo min mm", "fuse ms", "riletto"]
    print(SEP.join([""] + testa + [""]).strip())
    print(SEP.join([""] + ["---"] * len(testa) + [""]).strip())
    piano = [(c, v) for c in CASI for v in VARIANTI]
    piano += [(c, v) for c in (CASI[0], CASI[5]) for v in DEGENERI_TOL]
    for (nome_c, costruttore), (nome_v, opzioni, passo) in piano:
        step = tmp / (nome_c + "-" + nome_v + ".step").replace(" ", "_").replace("*", "x")
        riga = esegui(costruttore, opzioni, passo, step)
        print(SEP.join(["", nome_c, nome_v] + [str(x) for x in riga] + [""]).strip())


if __name__ == "__main__":
    main()
