#!/usr/bin/env python
"""Rimisura i numeri di `docs/validazione/modi-per-la-normativa.md`.

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-7-cantiere/scarto-con-segno.py`.

    uv run python docs/fase-7-cantiere/modi-per-la-normativa.py [cartella-runs]

**Legge e non scrive dentro `runs/`.** Prende la superficie riparata di due
corse e la rimaglia in una cartella temporanea; nessun artefatto delle corse
viene riscritto.

**Che cosa asserisce, e perche' cosi'.** Non i valori percentuali: il maglio
cambia con la piattaforma (TetGen e gmsh danno maglie diverse su Linux x86-64
e macOS arm64 a parita' di versione e di ingresso, #66), quindi una
percentuale incollata qui fallirebbe altrove per un motivo che non e' un
difetto. Gli `assert` guardano i **fatti** che reggono la scelta del
predefinito -- chi sta sotto il 90% e chi lo supera -- che sono l'unica cosa
che il documento pretende. E' la stessa lezione di
`tests/validazione/test_convergenza_mensola.py`, dove una soglia tarata su
una piattaforma sola e' stata bocciata dalla CI.

Serve `ccx` sul PATH.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "src"))

from meshrec.core import abaqus, solve, volume  # noqa: E402
from meshrec.core.config import (  # noqa: E402
    AnalysisConfig,
    CarichiConfig,
    Material,
    Modale,
    TetConfig,
)

CORSE = Path(sys.argv[1]) if len(sys.argv) > 1 else RADICE / "runs"

# I due corpi con una superficie riparata utilizzabile. Non sono indipendenti,
# e il documento lo dichiara: `lab_crop` e' il ritaglio della stessa scena che
# contiene il telaio, e scalare il modulo elastico non cambia le forme modali.
# Concordare era atteso; non e' una seconda conferma.
CORPI = {
    "telaio": (
        CORSE / "lab_telaio_v2" / "06_repaired.ply",
        Material(name="CALCESTRUZZO_C25_30", young=31500.0, poisson=0.2, density=2.5e-09),
    ),
    "ritaglio": (
        CORSE / "lab_crop" / "06_repaired.ply",
        Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-09),
    ),
}

CFG_TET = TetConfig(
    min_ratio=1.8, max_volume=None, max_steiner_points=-1,
    nobisect=True, reference_ratio=1.8, element="C3D4",
)

# I quattro punti che il documento cita: il valore storico, l'ultimo che non
# regge, il primo che regge, e il predefinito.
STORICO, ULTIMO_CHE_NON_REGGE, PRIMO_CHE_REGGE = 20, 31, 32
PREDEFINITO = Modale.model_fields["modi"].default


def leggi_superficie(percorso: Path) -> tuple[np.ndarray, np.ndarray]:
    import meshio

    m = meshio.read(percorso)
    facce = np.vstack([b.data for b in m.cells if b.type == "triangle"])
    return np.asarray(m.points, dtype=np.float64), np.asarray(facce, dtype=np.int64)


def frazione_peggiore(cartella: Path, nodi, tet, analisi, modi: int) -> float:
    """Frazione di massa partecipante della direzione traslazionale peggiore."""
    fuori = cartella / f"m{modi}"
    fuori.mkdir(parents=True, exist_ok=True)
    export = abaqus.export_model(
        fuori / "m.inp", fuori / "m.vtu", nodi, tet, analisi, CFG_TET,
        reference=None, carichi=CarichiConfig(modale=Modale(modi=modi)),
    )
    esito = solve.risolvi(
        fuori, fuori / "m.inp", analisi, nodi, tet, "C3D4",
        casi_di_carico=list(export["casi_di_carico"]),
        vincolo_in_pianta=export["constraint_plan_extent"],
        trasformata=export["transform"],
    )
    verdetto = solve.controlla_massa_modale(solve.leggi_massa_modale(Path(esito["dat"])))
    return float(verdetto["frazione_minima"])


def main() -> None:
    soglia = solve._FRAZIONE_MASSA_MINIMA
    print(f"soglia di norma: {soglia:.0%} (EN 1998-1 §4.3.3.3.1(3), NTC 2018 §7.3.3.1)")
    print(f"predefinito in `Modale.modi`: {PREDEFINITO}\n")

    banco = Path(tempfile.mkdtemp(prefix="modi-normativa-"))
    try:
        for nome, (superficie, materiale) in CORPI.items():
            analisi = AnalysisConfig(
                material=materiale, gravity=9810.0, fixed_nset="BASE",
                step_name="GRAVITA", set_tolerance_factor=6.0,
            )
            vertici, facce = leggi_superficie(superficie)
            nodi, tet, _ = volume.tetrahedralize_with_metrics(vertici, facce, CFG_TET)
            print(f"=== {nome}: {len(nodi)} nodi, {len(tet)} tetraedri")

            misure = {}
            for modi in (STORICO, ULTIMO_CHE_NON_REGGE, PRIMO_CHE_REGGE, PREDEFINITO):
                misure[modi] = frazione_peggiore(banco / nome, nodi, tet, analisi, modi)
                print(f"  {modi:3d} modi -> direzione peggiore {misure[modi]:7.2%}")

            assert misure[STORICO] < soglia, (
                f"{nome}: i {STORICO} modi storici dovrebbero stare sotto la soglia, "
                f"misurato {misure[STORICO]:.4%}"
            )
            assert misure[ULTIMO_CHE_NON_REGGE] < soglia, (
                f"{nome}: {ULTIMO_CHE_NON_REGGE} modi dovrebbero stare sotto la "
                f"soglia, misurato {misure[ULTIMO_CHE_NON_REGGE]:.4%}"
            )
            assert misure[PRIMO_CHE_REGGE] >= soglia, (
                f"{nome}: {PRIMO_CHE_REGGE} modi dovrebbero superare la soglia, "
                f"misurato {misure[PRIMO_CHE_REGGE]:.4%}"
            )
            assert misure[PREDEFINITO] >= soglia, (
                f"{nome}: il predefinito {PREDEFINITO} deve superare la soglia, "
                f"misurato {misure[PREDEFINITO]:.4%}"
            )
            # Il predefinito non sta sul bordo del gradino: e' la ragione per
            # cui non e' il piu' piccolo che regge.
            margine = misure[PREDEFINITO] - soglia
            margine_al_bordo = misure[PRIMO_CHE_REGGE] - soglia
            print(f"  margine del predefinito {margine:.2%}, "
                  f"del piu' piccolo che regge {margine_al_bordo:.2%}")
            assert margine > margine_al_bordo, (
                f"{nome}: il predefinito dovrebbe avere piu' margine del bordo del "
                f"gradino ({margine:.4%} contro {margine_al_bordo:.4%})"
            )
            print()
    finally:
        shutil.rmtree(banco, ignore_errors=True)

    print("tutti gli assert passati")


if __name__ == "__main__":
    main()
