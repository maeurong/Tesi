"""Fase 0 — CalculiX accetta il nostro .inp e da un risultato corretto?

Caso di prova: colonna a base quadrata incastrata al piede sotto peso proprio.
Accorciamento in sommita in forma chiusa: u = rho * g * L^2 / (2 * E).
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, synth, volume
from meshrec.core.config import GRAVITY_MM_S2, Material
from ccx_utils import read_dat_displacements

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 100.0, 400.0)  # mm


def test_calculix_solves_a_column_under_self_weight(tmp_path):
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    material = Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )

    z = nodes[:, 2]
    node_sets = {
        "BASE": np.flatnonzero(z <= z.min() + 1e-6),
        "TOP": np.flatnonzero(z >= z.max() - 1e-6),
    }

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        print_nsets=("TOP",),
    )

    process = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-2000:] + process.stderr[-2000:]

    displacements = read_dat_displacements(tmp_path / "model.dat")
    assert displacements, "nessuno spostamento letto dal file .dat"

    top_uz = np.array([displacements[node + 1][2] for node in node_sets["TOP"]])
    expected = material.density * GRAVITY_MM_S2 * SIZE[2] ** 2 / (2.0 * material.young)

    assert (top_uz < 0.0).all()  # la colonna si accorcia
    assert abs(top_uz.mean()) == pytest.approx(expected, rel=0.20)


def test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra(tmp_path):
    """Task 5, RULING M(b) — la controprova che rompe il cerchio.

    Il confronto per baricentri (in tests/test_abaqus.py) verifica che la
    tabella FACCE_DEL_SOLUTORE trascritta a mano rispetti la convenzione del
    manuale, ma parte comunque da quella trascrizione: se l'avessimo copiata
    male, l'attesa sarebbe sbagliata quanto la tabella e il test passerebbe
    comunque. Qui si chiede al solutore vero: si scrive una pressione su S4
    di un singolo esaedro e si verifica che il lato che si muove sia quello
    fisico a x massimo, non un altro.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    # densita' minima ammessa (Material la vuole positiva): il peso proprio
    # su un solo esaedro di queste dimensioni resta trascurabile rispetto
    # all'effetto della pressione laterale, gia' isolato dal confronto fra
    # lato caricato e lato opposto.
    materiale = Material(name="PROVA", young=1500.0, poisson=0.2, density=1e-12)
    nodi = np.array([
        [0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [100.0, 60.0, 0.0], [0.0, 60.0, 0.0],
        [0.0, 0.0, 150.0], [100.0, 0.0, 150.0], [100.0, 60.0, 150.0], [0.0, 60.0, 150.0],
    ])
    esaedro = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)
    base = np.array([0, 1, 2, 3])
    tutti = np.arange(8)

    superficie = abaqus.element_surface(esaedro, np.array([1, 2, 5, 6]), "C3D8I")
    assert superficie == [(0, 4)], "il lato x=100 di questo esaedro e' S4"

    abaqus.write_inp(
        tmp_path / "model.inp", nodi, esaedro,
        node_sets={"BASE": base, "TUTTI": tutti},
        material=materiale,
        element_type="C3D8I",
        print_nsets=("TUTTI",),
        element_surfaces={"LATERALE": superficie},
        pressure=("LATERALE", 2.0),
    )

    process = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-2000:] + process.stderr[-2000:]

    spostamenti = read_dat_displacements(tmp_path / "model.dat")

    # nodi in sommita' (z=150): 4 e 7 sono sul lato x=0 (non caricato),
    # 5 e 6 sono sul lato x=100 (caricato, S4).
    ux_caricato = np.mean([spostamenti[node + 1][0] for node in (5, 6)])
    ux_non_caricato = np.mean([spostamenti[node + 1][0] for node in (4, 7)])

    assert ux_caricato < 0.0, "la pressione su S4 deve spingere verso -x, non gonfiare il lato"
    assert ux_caricato < ux_non_caricato, "il lato caricato deve muoversi piu' del lato opposto"
