#!/usr/bin/env python
"""Rimisura i numeri di `docs/validazione/scarto-c3d4-c3d10-telaio.md` (#45).

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-6-cantiere/misura-carichi.py`. Ogni valore che il documento
pubblica porta qui il proprio `assert`: se qualcosa si muove, questo script
cade invece di stampare in silenzio un numero diverso da quello scritto.

    uv run python docs/fase-7-cantiere/scarto-c3d4-c3d10.py [cartella-runs]

**Legge e non scrive dentro `runs/`.** Parte dalla superficie gia' riparata
della corsa di riferimento (`runs/lab_telaio_v2/06_repaired.ply`) e scrive le
due corse del confronto in una cartella temporanea. Le corse in `runs/` non
si rigenerano: i documenti delle Fasi 5 e 6 ne citano i numeri campo per
campo (decisione di #41).

**Perche' partire dalla superficie e non dalla nuvola.** Il confronto vuole
lo *stesso maglio* con due elementi diversi. TetGen con `order=2` tiene gli
stessi tetraedri e aggiunge i sei nodi di lato, quindi tetraedrizzare due
volte la stessa superficie cambiando il solo ordine e' letteralmente lo
stesso maglio -- e lo script lo **verifica**, pretendendo lo stesso numero di
elementi e di punti di Steiner. Ripetere Poisson sui 6,3 milioni di punti
della nuvola introdurrebbe una seconda differenza fra i due modelli.

**Questi numeri valgono su macOS arm64.** #66 ha misurato che TetGen produce
magli diversi fra architetture a parita' di versione e di ingresso, quindi su
Linux i conteggi -- e con essi i valori -- sarebbero altri. E' la ragione per
cui questo script sta sotto `docs/` e non fra i test: non e' portabile per
costruzione, ed e' una riproduzione su questa macchina.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
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
    SpintaOrizzontale,
    TetConfig,
)

# La cartella delle corse si puo' passare come primo argomento: `runs/` non e'
# versionata, quindi in un worktree o su un secondo dispositivo non sta accanto
# al codice.
CORSE = Path(sys.argv[1]) if len(sys.argv) > 1 else RADICE / "runs"
SORGENTE = CORSE / "lab_telaio_v2"

# Identici a runs/lab_telaio_v2/config.yaml: il confronto cambia l'elemento e
# nient'altro. Senza `carico_sommita`: su C3D10 `ripartisci` solleva di
# proposito, perche' su una faccia a sei nodi il vettore dei carichi
# consistenti da' **zero** ai vertici e la ripartizione per area tributaria
# darebbe loro tutto, conservando la risultante -- un errore che
# `controlla_reazioni` non vedrebbe. Gravita' e spinta sono `*DLOAD, GRAV`,
# cioe' forze di massa, e non passano da li'.
MATERIALE = Material(
    name="CALCESTRUZZO_C25_30", young=31500.0, poisson=0.2, density=2.5e-09
)
ANALISI = AnalysisConfig(
    material=MATERIALE, gravity=9810.0, fixed_nset="BASE",
    step_name="GRAVITA", set_tolerance_factor=6.0,
)
CARICHI = CarichiConfig(
    spinta=SpintaOrizzontale(coefficiente=0.1, asse="y"),
    modale=Modale(modi=20),
)


def leggi_superficie(percorso: Path) -> tuple[np.ndarray, np.ndarray]:
    import meshio

    m = meshio.read(percorso)
    facce = np.vstack([b.data for b in m.cells if b.type == "triangle"])
    return np.asarray(m.points, dtype=np.float64), np.asarray(facce, dtype=np.int64)


def corri(elemento: str, vertici, facce, fuori: Path) -> dict:
    fuori.mkdir(parents=True, exist_ok=True)
    cfg_tet = TetConfig(
        min_ratio=1.8, max_volume=None, max_steiner_points=-1,
        nobisect=True, reference_ratio=1.8, element=elemento,
    )
    nodi, tet, metriche = volume.tetrahedralize_with_metrics(vertici, facce, cfg_tet)
    export = abaqus.export_model(
        fuori / "wall_model.inp", fuori / "wall_model.vtu",
        nodi, tet, ANALISI, cfg_tet, reference=vertici, carichi=CARICHI,
    )
    # I casi li dichiara l'esportazione, non questo script: stessa regola di
    # origine unica che `solve.risolvi` gia' impone.
    casi = list(export["casi_di_carico"])

    avvio = time.perf_counter()
    esito = solve.risolvi(
        fuori, fuori / "wall_model.inp", ANALISI, nodi, tet, elemento,
        casi_di_carico=casi,
        vincolo_in_pianta=export["constraint_plan_extent"],
        trasformata=export["transform"],
    )
    secondi = time.perf_counter() - avvio

    umax, vmmax, quota = {}, {}, {}
    for blocco in solve.leggi_frd(Path(esito["frd"])):
        if blocco.modale:
            continue
        dati = np.asarray(blocco.dati, dtype=np.float64)
        caso = casi[blocco.passo - 1]
        if blocco.grandezza == "DISP":
            umax[caso] = float(np.max(np.linalg.norm(dati[:, :3], axis=1)))
        elif blocco.grandezza == "STRESS":
            vm = solve.von_mises(dati[:, :6])
            indice = int(np.argmax(vm))
            vmmax[caso] = float(vm[indice])
            quota[caso] = float(nodi[blocco.nodi[indice] - 1][2])

    return {
        "nodi": len(nodi),
        "elementi": len(tet),
        "gradi": len(nodi) * 3,
        "massa": float(MATERIALE.density) * solve._volume_totale(nodi, tet),
        "secondi": secondi,
        "steiner": metriche["steiner_points"],
        "u": umax,
        "vm": vmmax,
        "quota": quota,
        "frequenze": list(esito["frequenze_hz"]),
    }


def vicino(atteso: float, ottenuto: float, rel: float = 5e-5) -> bool:
    return abs(ottenuto - atteso) <= rel * abs(atteso)


def main() -> int:
    if shutil.which("ccx") is None:
        print("ccx non e' nel PATH: il confronto non e' eseguibile")
        return 1
    if not (SORGENTE / "06_repaired.ply").exists():
        print(f"manca {SORGENTE / '06_repaired.ply'}: serve la corsa di riferimento")
        return 1

    vertici, facce = leggi_superficie(SORGENTE / "06_repaired.ply")
    assert len(vertici) == 10968, len(vertici)
    assert len(facce) == 21932, len(facce)

    with tempfile.TemporaryDirectory() as tmp:
        a = corri("C3D4", vertici, facce, Path(tmp) / "C3D4")
        b = corri("C3D10", vertici, facce, Path(tmp) / "C3D10")

    # Lo stesso maglio: stessi tetraedri, stessi punti di Steiner. Se questo
    # cade, il confronto sta misurando due magli e non due elementi.
    assert a["elementi"] == b["elementi"] == 51913, (a["elementi"], b["elementi"])
    assert a["steiner"] == b["steiner"] == 3135, (a["steiner"], b["steiner"])
    assert a["nodi"] == 14103 and b["nodi"] == 91084, (a["nodi"], b["nodi"])
    assert a["gradi"] == 42309 and b["gradi"] == 273252

    # La massa e' geometria e non formulazione: deve coincidere esattamente.
    assert a["massa"] == b["massa"], (a["massa"], b["massa"])
    assert vicino(0.5443209031, a["massa"]), a["massa"]

    # La corsa C3D4 riproduce i numeri gia' pubblicati in fase 5: senza questo
    # il confronto misurerebbe anche la distanza da quella corsa.
    assert vicino(0.036730, a["u"]["GRAVITA"]), a["u"]["GRAVITA"]
    assert vicino(0.505579, a["vm"]["GRAVITA"]), a["vm"]["GRAVITA"]
    assert vicino(21.19324, a["frequenze"][0]), a["frequenze"][0]

    scarto = lambda x, y: (x - y) / y * 100.0  # noqa: E731

    coppie = [
        ("|u|max gravita", a["u"]["GRAVITA"], b["u"]["GRAVITA"], -12.36),
        ("|u|max spinta", a["u"]["SPINTA_ORIZZONTALE"], b["u"]["SPINTA_ORIZZONTALE"], -12.07),
        ("vM max gravita", a["vm"]["GRAVITA"], b["vm"]["GRAVITA"], -65.56),
        ("vM max spinta", a["vm"]["SPINTA_ORIZZONTALE"], b["vm"]["SPINTA_ORIZZONTALE"], -55.62),
        ("1a frequenza", a["frequenze"][0], b["frequenze"][0], 7.07),
    ]
    print(f"{'grandezza':22s} {'C3D4':>14s} {'C3D10':>14s} {'scarto %':>10s}")
    for nome, x, y, atteso in coppie:
        s = scarto(x, y)
        print(f"{nome:22s} {x:14.6f} {y:14.6f} {s:9.2f}%")
        assert abs(s - atteso) < 0.01, (nome, s, atteso)

    # Le due firme dell'elemento troppo rigido, nella direzione che la teoria
    # prevede: spostamenti minori, frequenze maggiori. Se uscisse il
    # contrario sarebbe il confronto a essere sbagliato, non la letteratura.
    assert a["u"]["GRAVITA"] < b["u"]["GRAVITA"]
    assert all(x > y for x, y in zip(a["frequenze"][:8], b["frequenze"][:8]))

    # Il picco sta nello stesso posto: il lineare sbaglia quanto, non dove.
    assert abs(a["quota"]["GRAVITA"] - b["quota"]["GRAVITA"]) < 2.0

    print("\ntutti gli assert passati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
