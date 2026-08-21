"""Fase 0 — CalculiX accetta il nostro .inp e da un risultato corretto?

Caso di prova: colonna a base quadrata incastrata al piede sotto peso proprio.
Accorciamento in sommita in forma chiusa: u = rho * g * L^2 / (2 * E).
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, synth, volume
from meshrec.core.config import (
    GRAVITY_MM_S2,
    CaricoSommita,
    CarichiConfig,
    Material,
    Modale,
    SpintaOrizzontale,
)
from ccx_utils import read_dat_displacements

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 100.0, 400.0)  # mm

# `extra` tollera avvisi noti e specifici del singolo test (es. "no tied MPC"
# sul telaio): dalla Fase 5 `write_inp` scrive sempre attraverso
# `_passo_statico`, e nessun percorso puo' piu' produrre "reading *STEP" o
# "reading *OUTPUT" -- l'elenco fisso che li tollerava e' stato tolto perche'
# tollerava avvisi che non possono piu' esistere, con un confronto per
# sottostringa che avrebbe inghiottito anche un avviso futuro diverso che
# contenesse per caso lo stesso testo.
def avvisi_inattesi(stdout: str, extra: tuple[str, ...] = ()) -> list[str]:
    return [
        riga for riga in stdout.splitlines()
        if "*WARNING" in riga and not any(n in riga for n in extra)
    ]


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
    assert not avvisi_inattesi(process.stdout), "\n".join(avvisi_inattesi(process.stdout))

    displacements = read_dat_displacements(tmp_path / "model.dat")
    assert displacements, "nessuno spostamento letto dal file .dat"

    top_uz = np.array([displacements[node + 1][2] for node in node_sets["TOP"]])
    expected = material.density * GRAVITY_MM_S2 * SIZE[2] ** 2 / (2.0 * material.young)

    assert (top_uz < 0.0).all()  # la colonna si accorcia
    assert abs(top_uz.mean()) == pytest.approx(expected, rel=0.20)


def test_il_deck_a_quattro_passi_gira_a_zero_avvisi(tmp_path):
    """Che le card siano giuste lo dice il solutore, non una lettura del testo.

    Un controllo interno partirebbe dalla stessa trascrizione che vorrebbe
    verificare (stesso principio del Ruling M della Fase 4). Misurato il
    21/08/2026 sul deck as-built del telaio: quattro passi, "Job finished",
    zero avvisi e zero errori, sei autovalori con U^T*M*U = 1.
    """
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
    carichi = CarichiConfig(
        spinta=SpintaOrizzontale(coefficiente=0.1, asse="x"),
        carico_sommita=CaricoSommita(risultante=1000.0, nset="TOP"),
        modale=Modale(modi=6),
    )

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        carichi=carichi,
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita


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
    assert not avvisi_inattesi(process.stdout), "\n".join(avvisi_inattesi(process.stdout))

    spostamenti = read_dat_displacements(tmp_path / "model.dat")

    # nodi in sommita' (z=150): 4 e 7 sono sul lato x=0 (non caricato),
    # 5 e 6 sono sul lato x=100 (caricato, S4).
    ux_caricato = np.mean([spostamenti[node + 1][0] for node in (5, 6)])
    ux_non_caricato = np.mean([spostamenti[node + 1][0] for node in (4, 7)])

    assert ux_caricato < 0.0, "la pressione su S4 deve spingere verso -x, non gonfiare il lato"
    assert ux_caricato < ux_non_caricato, "il lato caricato deve muoversi piu' del lato opposto"


def test_i_tie_del_telaio_a_quattro_membrature_legano_davvero(tmp_path):
    """Task 8, giro di correzione 6 — il controllo non circolare.

    Nessun controllo interno al progetto puo' dire se un `*TIE` lega
    davvero: puo' solo dire che la superficie che gli passiamo ha facce.
    CalculiX invece, per ciascun nodo della superficie dipendente, o lo lega
    o stampa `*WARNING in gentiedmpc: no tied MPC` senza fallire il job -- un
    deck accettato e un vincolo parzialmente assente allo stesso tempo, che
    nessun controllo interno vedrebbe. E' per questo che resta l'unico
    controllo qui elencato che non dipende dalla stessa geometria che genera
    cio' che verifica.

    Storia misurata, sessione per sessione: giro 5 (solo criterio per
    baricentro) → 61 avvisi. Giro 6, Ruling AH ("tocca" sul lato
    indipendente + `POSITION TOLERANCE` per giunzione) → **24 avvisi**,
    `tie constraints: 4` (tutti e quattro registrati). Il tetto qui sotto e'
    quel numero misurato, con un margine, non zero: il residuo e' un limite
    noto della mesh non conforme (le due mesh ai lati di una giunzione, a
    passo diverso, non condividono nodi -- vedi `hexa.costruisci`), non un
    difetto di questo giro da nascondere alzando la soglia finche' passa.

    La mesh conforme multiblocco (nodi condivisi alla giunzione, zero avvisi
    per costruzione) resta la via d'aggiornamento e non e' stata imboccata
    qui: renderla conforme fra sezioni di dimensioni diverse costringerebbe
    a una griglia comune finissima o a elementi di transizione non
    esaedrici, e il Ruling U di questo progetto vuole solo esaedri puri --
    e' un cambio di architettura della mesh, non un parametro di questo
    giro.
    """
    # Misurato in questa sessione: 24 avvisi con questo codice (Ruling AH),
    # contro 61 del giro precedente. Il margine sopra 24 assorbe piccola
    # variazione fra macchine (versione di CalculiX, libreria BLAS) senza
    # mascherare una vera regressione: 30 resta un decimo del numero che il
    # giro 5 aveva lasciato rosso.
    tetto_avvisi = 30
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

    puliti, _maschera, _ = wall.scarta_pavimento(punti, cfg_segment, cfg_wall, spaziatura)
    regioni_punti, *_ = wall.scomponi(puliti, cfg_segment, cfg_wall, spaziatura)
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
    assert modello["metriche"]["ties"] == 4, "le quattro giunzioni devono registrare un *TIE ciascuna"

    # "no tied MPC" e' l'avviso proprio di questo test, gia' governato dalla
    # soglia qui sotto: va esteso solo qui, non in AVVISI_NOTI globale, o la
    # soglia perde significato per gli altri due test.
    inattesi = avvisi_inattesi(process.stdout, extra=("no tied MPC",))
    assert not inattesi, "\n".join(inattesi)

    avvisi = process.stdout.count("no tied MPC")
    assert avvisi <= tetto_avvisi, (
        f"{avvisi} nodi della superficie dipendente non hanno generato il "
        f"vincolo (`*WARNING in gentiedmpc: no tied MPC`), sopra il tetto "
        f"dichiarato di {tetto_avvisi}: un *TIE parzialmente inefficace oltre "
        "il limite noto della mesh non conforme, non piu' un residuo atteso"
    )


def test_un_prisma_solo_di_mesh_prisma_e_letto_dal_solutore(tmp_path):
    """`hexa.mesh_prisma` arriva a CalculiX solo attraverso `hexa.costruisci`
    nel test del telaio sopra: la sua uscita piu' semplice, un prisma singolo,
    non era mai stata risolta da sola. `target_size` piccolo qui sotto forza
    molti elementi e piu' strati nello spessore di quanto farebbe il default.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    from meshrec.core import hexa
    from meshrec.core.config import ModelConfig

    # Materiale del banco, tre numeri: non e' il provino di laboratorio,
    # basta per un controllo di fattibilita' col solutore vero.
    materiale = Material(name="PROVA", young=1500.0, poisson=0.2, density=1.8e-9)
    contorno = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 140.0], [0.0, 140.0]])
    lunghezza = 800.0
    cfg = ModelConfig(target_size=40.0)  # passo fitto: piu' esaedri, piu' strati

    nodi, esaedri, _ = hexa.mesh_prisma(
        contorno, np.zeros(3), np.array([0.0, 0.0, 1.0]), lunghezza, cfg
    )

    z = nodi[:, 2]
    node_sets = {"BASE": np.flatnonzero(z <= z.min() + 1e-6)}

    abaqus.write_inp(
        tmp_path / "model.inp", nodi, esaedri,
        node_sets=node_sets,
        material=materiale,
        element_type=cfg.element,
        print_nsets=("BASE",),
    )

    process = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-2000:] + process.stderr[-2000:]
    assert "*ERROR" not in process.stdout
    assert not avvisi_inattesi(process.stdout), "\n".join(avvisi_inattesi(process.stdout))
    # Non basta che `model.dat` esista: CalculiX lo scrive comunque, anche vuoto,
    # se nessun *NODE PRINT gli ha chiesto dei risultati. Chiedere gli spostamenti
    # e' cio' che rende il controllo sensibile -- e' la stessa forma gia' usata
    # dagli altri due test di questo file.
    spostamenti = read_dat_displacements(tmp_path / "model.dat")
    assert spostamenti, "il .dat non contiene spostamenti: il deck e' stato risolto a vuoto"
