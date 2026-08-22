"""Emette cubo.inc: cubo unitario in 6 C3D4, faccia z=0 fissa, z=1 libera.

Sintetico. Serve perche' un tet solo non separa la faccia caricata dalla
faccia vincolata, e `RF` non conta il carico che cade su un nodo gia' fisso.
"""
import itertools

N = {1:(0,0,0), 2:(1,0,0), 3:(1,1,0), 4:(0,1,0),
     5:(0,0,1), 6:(1,0,1), 7:(1,1,1), 8:(0,1,1)}
TETS = [(1,2,3,7), (1,3,4,7), (1,4,8,7), (1,8,5,7), (1,5,6,7), (1,6,2,7)]
FACCE = {1:(0,1,2), 2:(0,3,1), 3:(1,3,2), 4:(2,3,0)}  # 1-2-3, 1-4-2, 2-4-3, 3-4-1


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def volume(t):
    a, b, c, d = (N[i] for i in t)
    u, v, w = sub(b, a), sub(c, a), sub(d, a)
    cr = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    return sum(x*y for x, y in zip(cr, w)) / 6.0


tets = [t if volume(t) > 0 else (t[0], t[2], t[1], t[3]) for t in TETS]
assert all(volume(t) > 1e-12 for t in tets), "jacobiano non positivo"
assert abs(sum(volume(t) for t in tets) - 1.0) < 1e-12, "il cubo non fa volume 1"


def facce_sul_piano(quota, indice):
    """(elemento 1-based, numero di faccia) le cui tre punte stanno sul piano."""
    fuori = []
    for e, t in enumerate(tets, start=1):
        for numero, combo in FACCE.items():
            if all(N[t[i]][indice] == quota for i in combo):
                fuori.append((e, numero))
    return fuori


sotto, sopra = facce_sul_piano(0, 2), facce_sul_piano(1, 2)
assert len(sotto) == 2 and len(sopra) == 2, (sotto, sopra)

righe = ["** Cubo unitario sintetico, 6 C3D4. Nessun numero del provino.",
         "** Faccia z=0 vincolata (nodi 1-4), faccia z=1 caricata (nodi 5-8).",
         "** Area esatta di ciascuna delle due superfici: 1.0",
         "*NODE, NSET=NALL"]
righe += [f"{i}, {x}., {y}., {z}." for i, (x, y, z) in N.items()]
righe += ["*ELEMENT, TYPE=C3D4, ELSET=EALL"]
righe += [f"{e}, " + ", ".join(str(i) for i in t) for e, t in enumerate(tets, 1)]
righe += ["*NSET, NSET=FISSI", "1, 2, 3, 4", "*NSET, NSET=LIBERI", "5, 6, 7, 8"]
righe += ["*SURFACE, NAME=SOPRA, TYPE=ELEMENT"]
righe += [f"{e}, S{n}" for e, n in sopra]
righe += ["*SURFACE, NAME=LATO, TYPE=ELEMENT"]
righe += [f"{e}, S{n}" for e, n in facce_sul_piano(0, 1)]  # piano y=0
righe += ["*MATERIAL, NAME=ACCIAIO", "*ELASTIC", "210000.0, 0.3",
          "*SOLID SECTION, ELSET=EALL, MATERIAL=ACCIAIO"]

print("\n".join(righe))
