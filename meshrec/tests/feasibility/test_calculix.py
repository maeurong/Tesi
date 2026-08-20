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


def test_i_tie_del_telaio_a_quattro_membrature_legano_davvero(tmp_path):
    """Task 8, giro di correzione 5 — il controllo non circolare.

    Nessun controllo interno al progetto puo' dire se un `*TIE` lega
    davvero: puo' solo dire che la superficie che gli passiamo ha facce.
    CalculiX invece, per ciascun nodo della superficie dipendente, o lo lega
    o stampa `*WARNING in gentiedmpc: no tied MPC` senza fallire il job -- un
    deck accettato e un vincolo parzialmente assente allo stesso tempo, che
    nessun controllo interno vedrebbe. E' per questo che resta l'unico
    controllo qui elencato che non dipende dalla stessa geometria che genera
    cio' che verifica.

    **Misurato in questa sessione, e il test e' rosso**: `tie constraints: 4`
    (i quattro *TIE sono tutti registrati) ma il solutore stampa comunque
    `no tied MPC` -- decine di volte, per singoli nodi della superficie
    dipendente che non si proiettano sull'indipendente entro la tolleranza
    propria di CalculiX. Non e' una regressione di questo giro: con il
    criterio per nodi del giro precedente (due sole giunzioni legate secondo
    il controllo interno) il solutore stampava comunque `no tied MPC` decine
    di volte sulle stesse due giunzioni -- confrontato in questa sessione,
    codice non toccato dal commit. Il divario fra "la nostra superficie ha
    facce" e "CalculiX lega ogni nodo" e' precedente a questo giro e a
    Ruling AF, e resta aperto: la via d'aggiornamento e' probabilmente una
    `POSITION TOLERANCE` sulla card `*TIE`, che oggi il deck non scrive e che
    non e' stata toccata qui, essendo una decisione fuori dallo scopo di
    questo giro.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    from meshrec.core import hexa, wall
    from meshrec.core.config import ModelConfig, SegmentConfig, WallConfig

    # Stesso telaio sintetico di tests/test_hexa.py e tests/test_wall.py: due
    # montanti, due traversi. I numeri del banco stanno nei test, non in src/.
    telaio = [
        ((0.0, -90.0, 0.0), (200.0, 180.0, 1600.0)),
        ((1400.0, -130.0, 0.0), (200.0, 260.0, 1600.0)),
        ((0.0, -70.0, 1600.0), (1600.0, 140.0, 300.0)),
        ((0.0, -170.0, -300.0), (1600.0, 340.0, 300.0)),
    ]
    spaziatura = 20.0
    punti = synth.sample_frame_surface(telaio, spaziatura)
    cfg_segment = SegmentConfig()
    cfg_wall = WallConfig()

    puliti, _ = wall.scarta_pavimento(punti, cfg_segment, cfg_wall, spaziatura)
    regioni_punti, _ = wall.scomponi(puliti, cfg_segment, cfg_wall, spaziatura)
    direzioni, _ = wall.terna(puliti)
    accettate = []
    for indici in regioni_punti:
        membratura = wall.misura(puliti[indici], direzioni, cfg_wall)
        membratura.punti = indici
        membratura.esiti = wall.controlla(membratura, cfg_wall)
        if all(esito["passato"] for esito in membratura.esiti.values()):
            accettate.append(membratura)

    cfg = ModelConfig()
    modello = hexa.costruisci(accettate, "estruso", cfg)
    assert modello["ties"], "il telaio deve avere almeno un *TIE da verificare col solutore"

    z = modello["nodi"][:, 2]
    node_sets = {"BASE": np.flatnonzero(z <= z.min() + 1e-6)}

    abaqus.write_inp(
        tmp_path / "model.inp", modello["nodi"], modello["elementi"],
        node_sets=node_sets,
        material=Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9),
        element_type=cfg.element,
        element_surfaces=modello["superfici"],
        ties=modello["ties"],
    )

    process = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-2000:] + process.stderr[-2000:]
    assert "no tied MPC" not in process.stdout, (
        "il solutore ha accettato il deck ma per almeno un nodo della superficie "
        "dipendente non ha generato il vincolo (`*WARNING in gentiedmpc: no tied "
        "MPC`): un *TIE parzialmente inefficace che nessun controllo interno "
        "vedrebbe, esattamente cio' che questo test esiste per cercare"
    )
