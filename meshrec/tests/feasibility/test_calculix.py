"""Fase 0 — CalculiX accetta il nostro .inp e da' un risultato corretto?

Caso di prova: colonna a base quadrata incastrata al piede sotto peso proprio.
Accorciamento in sommita' in forma chiusa: u = rho * g * L^2 / (2 * E).
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import (
    GRAVITY_MM_S2,
    AnalysisConfig,
    CaricoDistribuito,
    CaricoPosizionato,
    CaricoSommita,
    CarichiConfig,
    Material,
    Modale,
    Momento,
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
    # `print_nsets=("TOP",)` mette nel .dat un blocco `displacements` per TOP
    # e uno `forces` per BASE, righe identiche in forma: solo i primi sono
    # spostamenti. I due set sono disgiunti, quindi prima del filtro il
    # dizionario portava le reazioni in newton sotto i nodi di BASE senza che
    # nulla lo dicesse.
    assert not set(displacements) & {int(n) + 1 for n in node_sets["BASE"]}, (
        "i nodi di BASE compaiono con le loro RF, non con uno spostamento"
    )

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


# Stesso caso misurato nel modulo `solve.py`: un passo statico con U richiesta
# su un insieme, seguito da un passo modale che non la richiede ne' la
# cancella. Non serve `ccx` per riprodurlo: e' testo scritto a mano, come
# DAT_REAZIONI_CONTAMINATO in tests/test_solve.py.
DAT_SPOSTAMENTI_CONTAMINATO = """\

                        S T E P       1


                                INCREMENT     1


 displacements (vx,vy,vz) for set TOP and time  0.1000000E+01

         1 -1.000000E-03  2.000000E-04  3.000000E-04
         2 -1.100000E-03  2.100000E-04  3.100000E-04

                        S T E P       2


     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00

                    E I G E N V A L U E    N U M B E R     1


 displacements (vx,vy,vz) for set TOP and time  0.2000000E+01

         1  2.145000E+02 -3.301000E+02  1.987000E+02
         2 -1.876000E+02  4.012000E+02 -2.204000E+02
"""


def test_read_dat_displacements_non_prende_una_forma_modale(tmp_path):
    """Riparazione assegnata al Task 6: stessa falla di `solve.leggi_reazioni`,
    mai chiusa qui perche' nessun test di questo file aveva finora un passo
    modale nel deck. Senza il confine a `E I G E N V A L U E   O U T P U T`,
    "l'ultimo blocco a quattro campi vince" prenderebbe la forma modale
    (~10^2 mm) al posto dello spostamento fisico (~10^-3 mm)."""
    percorso = tmp_path / "prova.dat"
    percorso.write_text(DAT_SPOSTAMENTI_CONTAMINATO, encoding="ascii")

    spostamenti = read_dat_displacements(percorso)

    assert spostamenti[1] == pytest.approx((-1.000e-03, 2.000e-04, 3.000e-04))
    assert spostamenti.keys() == {1, 2}


def test_lo_step_13_risolve_il_deck_e_scrive_i_campi_nel_vtu(tmp_path):
    """Verifica di fattibilita' del Task 6: `solve.risolvi` chiama `ccx` vero,
    legge le sue uscite e scrive `13_solution.vtu` coi nomi di point_data che
    i Task 8/9 consumano -- `U_<CASO>`, `VM_<CASO>` per passo statico,
    `MODO_<n>` per il modale, quest'ultimo senza `U_`/`VM_` propri.
    """
    meshio = pytest.importorskip("meshio")
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
        modale=Modale(modi=3),
    )
    analysis = AnalysisConfig(material=material)

    abaqus.write_inp(
        tmp_path / "wall_model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        carichi=carichi,
    )

    # casi_di_carico esplicito, nello stesso ordine in cui i tre carichi sono
    # dichiarati sopra: dal giro di correzione della revisione, risolvi() non
    # deriva piu' l'ordine in proprio (era solve._casi_statici) -- lo riceve
    # gia' fatto, come fa pipeline.run leggendolo da
    # metrics["11_export"]["casi_di_carico"]. Qui non c'e' un export_model da
    # cui leggerlo (il deck e' scritto con write_inp direttamente), quindi e'
    # scritto a mano: la corrispondenza col deck vero e' verificata altrove
    # (tests/test_solve.py::test_casi_di_carico_segue_l_ordine_vero_scritto_da_write_inp),
    # non e' lo scopo di questo test, che verifica ccx vero.
    esito = solve.risolvi(
        tmp_path, tmp_path / "wall_model.inp", analysis, nodes, tets, "C3D4",
        casi_di_carico=["GRAVITA", "SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"],
        vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0},
        # Identita': qui il deck e' scritto con write_inp sugli stessi nodi
        # che risolvi riceve, senza passare da export_model, quindi campi e
        # punti sono gia' nello stesso telaio e non c'e' nulla da riportare.
        # Il caso con una rotazione vera e' in tests/test_solve.py (C1).
        trasformata=np.eye(4),
    )

    assert esito["eseguito"] is True
    assert esito["returncode"] == 0
    assert esito["errori"] == 0
    assert esito["modi"] == 3
    assert (tmp_path / "13_solution.vtu").exists()
    assert (tmp_path / "13_solver.log").exists()

    mesh = meshio.read(tmp_path / "13_solution.vtu")
    chiavi = set(mesh.point_data)
    # L'uguaglianza di insieme sotto fissa gia' l'assenza di U_MODO_n/VM_MODO_n
    # (non stanno nell'insieme atteso): un ciclo separato che lo riasserisse
    # sarebbe implicato da qui, non un controllo in piu' (rilievo Minor della
    # revisione).
    assert chiavi == {
        "U_GRAVITA", "VM_GRAVITA",
        "U_SPINTA_ORIZZONTALE", "VM_SPINTA_ORIZZONTALE",
        "U_CARICO_TOP", "VM_CARICO_TOP",
        "MODO_1", "MODO_2", "MODO_3",
    }

    # Solo l'insieme delle chiavi non basta: un'etichettatura scambiata fra
    # passi (SPINTA_ORIZZONTALE <-> CARICO_TOP) lascerebbe l'insieme identico.
    # Due controlli fisici ancorano ogni nome al passo giusto.
    top = node_sets["TOP"]
    ux_gravita = np.abs(mesh.point_data["U_GRAVITA"][top, 0]).mean()
    ux_spinta = np.abs(mesh.point_data["U_SPINTA_ORIZZONTALE"][top, 0]).mean()
    assert ux_spinta > 10.0 * ux_gravita, (
        "la spinta orizzontale su x deve muovere la sommita' molto piu' del "
        "solo peso proprio, simmetrico: se le etichette fossero scambiate con "
        "CARICO_TOP (verticale) questo non sarebbe vero"
    )

    uz_gravita = mesh.point_data["U_GRAVITA"][top, 2].mean()
    uz_carico = mesh.point_data["U_CARICO_TOP"][top, 2].mean()
    assert uz_carico < uz_gravita, (
        "il carico aggiuntivo in sommita' (peso proprio + risultante verticale) "
        "deve accorciare la colonna piu' del solo peso proprio"
    )


def test_un_posizionato_gira_a_zero_avvisi_e_sposta_qualcosa(tmp_path):
    """Il deck con un carico posizionato lo onora il solutore, non una lettura del testo.

    Non basta "zero avvisi": un momento su un C3D4 esce a zero avvisi e
    spostamento esattamente nullo. L'oracolo sullo spostamento verifica
    solo che qualcosa si sia mosso.

    L'oracolo che uccide davvero e' sulle **reazioni**, non sullo
    spostamento: `max|uz|` risponde sia a un carico verticale che a uno
    orizzontale (una colonna snella si inflette, e la flessione sposta
    la sommita' in z quanto o piu' del carico assiale corretto -- vedi
    sotto), quindi non puo' distinguere "la forza e' andata dove
    dichiarato" da "e' andata altrove". Le reazioni sono equilibrio, non
    inflessione: non dipendono dalla snellezza, e la loro somma sul set
    vincolato dice esattamente quale vettore il solutore ha applicato.

    Il passo letto e' il secondo (`passo=2`): il deck ha due passi
    statici, GRAVITA (il solo peso proprio, scritto sempre per primo da
    `write_inp`) e PRESSA (peso proprio piu' il carico posizionato,
    cumulativo come ogni passo di questa funzione). Il peso proprio
    atteso e' calcolato da massa e gravita' (`material.density * volume
    * GRAVITY_MM_S2`), non misurato da una corsa a parte: la colonna e'
    un box, il suo volume e' noto in forma chiusa senza bisogno della
    mesh.

    Mutazione che lo uccide: scrivere il grado del *CLOAD a 1 invece del
    grado vero (3, verticale). Misurato: somma reazioni corretto
    (fx,fy,fz)=(-9e-6, 2.2e-6, 1067.5) N, mutato (1000.0, -1.7e-5, 67.5)
    N -- la firma si ribalta netta, x prende il carico e z resta col
    solo peso, senza soglie da negoziare.

    Due mutazioni tentate prima, contro l'oracolo sullo spostamento, non
    uccidono e restano documentate perche' qualcuno non le riprovi:
    (1) nodo base zero invece di base uno -- il nodo 0 non cade nel
    selettore "piastra" (set TOP), lo shift di un'unita' sposta la forza
    su un nodo vicino ancora quasi sempre in TOP: max|uz| corretto
    0.0275 mm, mutato 0.0300 mm, stesso ordine, nessuna soglia separa.
    (2) grado 1 invece di 3 contro max|uz| (invece che contro le
    reazioni): la colonna e' snella (100x100x400 mm) e la forza fuori
    asse la inflette, spostando la sommita' in z per rotazione della
    sezione piu' del carico assiale corretto -- max|uz| corretto
    0.0274568 mm, mutato 0.223764 mm, rapporto ~8.1x, sotto l'ordine di
    grandezza per una soglia onesta. Stessa mutazione, oracolo sbagliato:
    la sostituzione dell'oracolo (reazioni al posto dello spostamento),
    non della mutazione, e' quello che l'ha resa netta.
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

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        print_nsets=("TOP",),
        nset_selettori={"piastra": node_sets["TOP"]},
        carichi=CarichiConfig(posizionati=[
            CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1000.0)),
        ]),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    spostamenti = read_dat_displacements(tmp_path / "model.dat")
    assert spostamenti, "il .dat non porta spostamenti: il carico non e' arrivato"
    assert max(abs(u[2]) for u in spostamenti.values()) > 0.0

    # Oracolo vero: la somma delle reazioni sul passo PRESSA (il secondo,
    # peso proprio incluso) e' esattamente il vettore applicato, in
    # equilibrio -- non dipende dalla snellezza della colonna come lo
    # spostamento sopra.
    reazioni = solve.leggi_reazioni(tmp_path / "model.dat", passo=2)
    assert reazioni, "il passo 2 (PRESSA) non porta reazioni"
    fx, fy, fz = np.array(list(reazioni.values())).sum(axis=0)
    peso_atteso = material.density * SIZE[0] * SIZE[1] * SIZE[2] * GRAVITY_MM_S2
    assert fz == pytest.approx(1000.0 + peso_atteso, rel=0.02), (
        "la reazione verticale non bilancia forza dichiarata + peso proprio: "
        "il carico non e' arrivato sul grado giusto"
    )
    assert abs(fx) < 1.0 and abs(fy) < 1.0, (
        "reazione orizzontale non trascurabile: il carico verticale dichiarato "
        "sta spingendo la struttura di lato, non e' sul grado 3"
    )


def test_il_secondo_posizionato_non_eredita_il_cload_del_primo(tmp_path):
    """Un *CLOAD dichiarato in un passo statico resta attivo nel passo dopo, se nessuno lo azzera.

    Misurato con la sonda in `docs/fase-6-cantiere/sonda-cload-persiste/`:
    un `*CLOAD` di un passo statico si legge ancora nelle reazioni del
    passo successivo, a meno che quel passo non apra con `*CLOAD, OP=NEW`.
    Fino a questa fase nessun deck aveva mai due passi statici consecutivi
    che dichiarano entrambi un `*CLOAD` (`SPINTA_ORIZZONTALE` usa `*DLOAD`,
    `CARICO_TOP` era sempre l'ultimo passo statico prima di `MODALE`, che
    e' `*FREQUENCY`): due carichi posizionati sono la prima configurazione
    che li mette in sequenza, ed e' per questo che nessun test lo aveva
    ancora colto -- incluso quello sopra
    (`test_un_posizionato_gira_a_zero_avvisi_e_sposta_qualcosa`), che ha un
    solo posizionato e non puo' vedere il difetto.

    I due carichi stanno su **selettori disgiunti** (`piastra`=TOP verticale,
    `lato`=una faccia laterale) e su **gradi diversi** (z e x): un primo
    tentativo con lo stesso selettore per entrambi risultava verde anche col
    difetto presente, perche' il default Abaqus/CalculiX per `*CLOAD` senza
    `OP=NEW` e' `OP=MOD` -- il valore nuovo *sovrascrive* quello vecchio sullo
    stesso nodo/grado, e due carichi sullo stesso nodo/grado si sovrascrivono
    a vicenda anche senza `OP=NEW`. Il difetto e' visibile solo quando il
    secondo passo non ridichiara affatto il nodo/grado del primo: e' esattamente
    il caso di `carico_sommita` seguito da un posizionato su un altro selettore,
    o due posizionati su selettori diversi.

    Mutazione che lo uccide: togliere ``OP=NEW`` dal `*CLOAD` che
    `write_inp` scrive per ogni carico posizionato con `forza`. Misurato
    applicando davvero la mutazione: la reazione fz del passo TIRO sale da
    ~67,5 N (il solo peso proprio misurato al passo 1: TIRO e' tutto
    orizzontale) a ~1067,5 N (1000 N verticali di PRESSA, mai azzerati, +
    peso proprio) -- il *CLOAD di PRESSA su TOP resta applicato nel passo
    di TIRO, che non lo tocca.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    material = Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    x, z = nodes[:, 0], nodes[:, 2]
    node_sets = {
        "BASE": np.flatnonzero(z <= z.min() + 1e-6),
        "TOP": np.flatnonzero(z >= z.max() - 1e-6),
    }
    # Faccia laterale a x minimo, esclusa la sommita' e la base: disgiunta da
    # TOP per costruzione, cosi' il *CLOAD di PRESSA (su TOP) non viene mai
    # ridichiarato -- ne' quindi sovrascritto -- dal *CLOAD di TIRO (su LATO).
    lato = np.flatnonzero((x <= x.min() + 1e-6) & (z < z.max() - 1e-6) & (z > z.min() + 1e-6))
    assert not set(node_sets["TOP"].tolist()) & set(lato.tolist()), "TOP e LATO devono essere disgiunti"

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        print_nsets=("TOP",),
        nset_selettori={"piastra": node_sets["TOP"], "lato": lato},
        carichi=CarichiConfig(posizionati=[
            CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1000.0)),
            CaricoPosizionato(nome="TIRO", selettore="lato", forza=(300.0, 0.0, 0.0)),
        ]),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    # Il peso proprio si misura dal passo 1 (GRAVITA, il solo peso, scritto
    # sempre per primo da write_inp) invece che da rho*V*g sul volume
    # nominale del box: la tetraedrizzazione approssima quel volume (misurato
    # qui: scarto ~4,4%), e un oracolo tarato sul valore nominale avrebbe una
    # soglia falsamente larga proprio dove serve stretta (passo 3, dove il
    # solo peso proprio e' l'intera reazione attesa).
    reazioni_gravita = solve.leggi_reazioni(tmp_path / "model.dat", passo=1)
    peso_misurato = float(np.array(list(reazioni_gravita.values())).sum(axis=0)[2])

    # Passo 2 (PRESSA): peso proprio + PRESSA (verticale), nessun TIRO ancora.
    reazioni_pressa = solve.leggi_reazioni(tmp_path / "model.dat", passo=2)
    fx, fy, fz = np.array(list(reazioni_pressa.values())).sum(axis=0)
    assert fz == pytest.approx(1000.0 + peso_misurato, rel=0.02)
    assert abs(fx) < 1.0 and abs(fy) < 1.0

    # Passo 3 (TIRO): l'oracolo vero. TIRO e' tutto orizzontale (x): la
    # reazione verticale deve tornare al solo peso proprio, non portare
    # ancora i -1000 N verticali di PRESSA.
    reazioni_tiro = solve.leggi_reazioni(tmp_path / "model.dat", passo=3)
    fx, fy, fz = np.array(list(reazioni_tiro.values())).sum(axis=0)
    assert fz == pytest.approx(peso_misurato, rel=0.02), (
        f"fz={fz:.3f} N: il passo TIRO porta ancora il *CLOAD verticale di "
        f"PRESSA (atteso ~{1000.0 + peso_misurato:.1f} N se non azzerato, "
        f"contro il solo peso proprio {peso_misurato:.1f} N misurato al passo 1)"
    )
    assert fx == pytest.approx(-300.0, rel=0.02), "la reazione orizzontale deve bilanciare TIRO"
    assert abs(fy) < 1.0


def test_carico_top_non_eredita_la_spinta_del_dload(tmp_path):
    """Un *DLOAD (GRAV) dichiarato in un passo statico resta attivo nel passo dopo, come il *CLOAD.

    Misurato con la sonda in
    `docs/fase-6-cantiere/sonda-cload-persiste/sonda-dload-ridichiarato.inp`:
    il peso proprio si ridichiara identico a ogni passo e non raddoppia, ma
    la spinta orizzontale (`SPINTA_ORIZZONTALE`), dichiarata una volta sola
    nel suo passo, restava attiva in ogni passo statico successivo prima
    che `_passo_statico` aprisse `*DLOAD` con `OP=NEW`. `CARICO_TOP` e' il
    primo passo dove la combinazione `spinta` + `carico_sommita` e'
    verificabile: senza il fix la sua reazione orizzontale sarebbe quella
    di `SPINTA_ORIZZONTALE`, non quella del solo peso.

    L'oracolo e' sulle reazioni orizzontali, non sul testo del deck: un
    `*DLOAD, OP=NEW` scritto ma letto male da `ccx` non lo smentirebbe un
    controllo sulla sola stringa.

    Mutazione che lo uccide: togliere ``, OP=NEW`` dalla riga ``*DLOAD`` di
    `_passo_statico`. Misurato applicando davvero la mutazione: la reazione
    fx del passo CARICO_TOP resta quella di SPINTA_ORIZZONTALE (~-98 N)
    invece di tornare a quella del solo peso proprio (~0 N).
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

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        carichi=CarichiConfig(
            spinta=SpintaOrizzontale(coefficiente=0.1, asse="x"),
            carico_sommita=CaricoSommita(risultante=500.0, nset="TOP"),
        ),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    # Passo 1: GRAVITA (solo peso). Passo 2: SPINTA_ORIZZONTALE (peso + spinta
    # orizzontale). Passo 3: CARICO_TOP (peso + *CLOAD in sommita').
    reazioni_gravita = solve.leggi_reazioni(tmp_path / "model.dat", passo=1)
    fx_peso, fy_peso, _ = np.array(list(reazioni_gravita.values())).sum(axis=0)

    reazioni_spinta = solve.leggi_reazioni(tmp_path / "model.dat", passo=2)
    fx_spinta, _, _ = np.array(list(reazioni_spinta.values())).sum(axis=0)
    assert abs(fx_spinta - fx_peso) > 1.0, "la spinta non ha spostato la reazione orizzontale: il deck non esercita il codice da coprire"

    reazioni_top = solve.leggi_reazioni(tmp_path / "model.dat", passo=3)
    fx_top, fy_top, _ = np.array(list(reazioni_top.values())).sum(axis=0)
    assert fx_top == pytest.approx(fx_peso, abs=1.0), (
        f"fx={fx_top:.3f} N: il passo CARICO_TOP porta ancora la spinta orizzontale "
        f"del passo precedente (atteso ~{fx_spinta:.1f} N se non azzerata, contro "
        f"il solo peso proprio ~{fx_peso:.1f} N misurato al passo 1)"
    )
    assert fy_top == pytest.approx(fy_peso, abs=1.0)


def test_un_momento_come_coppia_non_e_scartato_in_silenzio(tmp_path):
    """Il momento realizzato come coppia sposta davvero, a differenza della card muta.

    Misurato: un `*CLOAD` sul grado 4 di un C3D4 esce a zero avvisi e
    spostamento `0.000000E+00`. Questo test afferma il contrario sulla
    coppia, ed e' l'unico modo di distinguere le due cose.

    Soglia di 1e-3 mm, non zero: misurato che la sola gravita' (senza
    alcun momento) genera gia' fino a ~1.8e-5 mm di spostamento
    orizzontale per asimmetria della mesh -- un confronto con 0.0
    sarebbe soddisfatto anche da una card muta sul grado 4, che non
    sposta nulla di suo ma eredita quel rumore. La coppia vera qui
    misura ~0.05 mm, ~2700 volte sopra la soglia.

    Mutazione che lo uccide: scrivere il momento come `*CLOAD` sui gradi
    4-6 invece che come coppia. `ccx` esce a zero, senza warning, e gli
    spostamenti orizzontali restano al rumore di fondo della gravita'
    (~1.8e-5 mm), sotto la soglia.

    Perche' questo test guarda lo spostamento e il test del posizionato
    guarda le reazioni: una coppia ha forza netta nulla per costruzione,
    quindi le sue reazioni sono indistinguibili da quelle della sola
    gravita' -- l'oracolo sulle reazioni non direbbe nulla qui. La firma
    di una coppia e' lo spostamento orizzontale, non l'equilibrio delle
    forze. Non e' un'incoerenza da uniformare: sono due carichi diversi
    con due firme diverse.
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

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        print_nsets=("TOP",),
        nset_selettori={"piastra": node_sets["TOP"]},
        carichi=CarichiConfig(posizionati=[
            CaricoPosizionato(
                nome="TORSIONE", selettore="piastra",
                momento=Momento(asse=(0.0, 0.0, 1.0), modulo=50_000.0, braccio=60.0),
            ),
        ]),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    spostamenti = read_dat_displacements(tmp_path / "model.dat")
    assert spostamenti, "il .dat non porta spostamenti"
    orizzontali = max(max(abs(u[0]), abs(u[1])) for u in spostamenti.values())
    # 1e-3 mm, non 0.0: la sola gravita' (mesh non simmetrica) genera gia'
    # ~1.8e-5 mm di rumore orizzontale, che una card muta erediterebbe
    # superando un confronto con zero senza aver mosso nulla di suo.
    assert orizzontali > 1e-3, "la coppia non ha mosso nulla oltre il rumore: e' muta come la card sul grado 4"


def test_una_pressione_persiste_finche_non_la_si_ridichiara_a_zero(tmp_path):
    """La sonda di #84, della stessa forma di quella di `*CLOAD`.

    Un `*CLOAD` scritto in un passo statico **resta attivo** in ogni passo
    successivo finche' un `*CLOAD, OP=NEW` non lo azzera
    (`docs/fase-6-cantiere/sonda-cload-persiste/`). Per `*DSLOAD` la stessa
    domanda era rimasta senza misura, e la via ovvia -- copiare `OP=NEW` -- e'
    stata smentita in CI il 27/08/2026: `ccx` 2.21 non riconosce quel
    parametro su questa card e ne fa due avvisi, senza applicarlo.

    Quindi la persistenza si misura invece di dedurla. Quattro passi statici
    sullo stesso tetraedro incastrato:

    | passo | `*DSLOAD` dichiarato li' dentro | misurato in CI il 27/08/2026 |
    |---|---|---|
    | 1 | *(nessuno)* | `RF_y` 0,0 |
    | 2 | `PELLE, P, 1.0` | `RF_y` -1666,667152 |
    | 3 | *(nessuno)* | `RF_y` -1666,667152 — **persiste** |
    | 4 | `PELLE, P, 0.0` + `PELLE2, P, 1.0` | `RF_y` a zero, `RF_x` -1666,667152 |

    Le due pressioni agiscono su facce perpendicolari (`PELLE` su y = 0,
    `PELLE2` su x = 0) e il peso proprio non porta nulla ne' su x ne' su y:
    ogni componente isola la propria pressione **senza sottrazioni**, e le due
    aree sono esatte (100 x 100 / 2 = 5000 mm², per 1 MPa fanno 5000 N).

    Il numero stampato non e' pero' -5000 ma **-5000/3**, ed e' giusto cosi':
    sotto carico `RF` non e' la sola reazione ma «the sum of the reaction
    forces and the loading forces» (manuale CalculiX §6.11.5). La faccia
    caricata ha tre nodi, due dei quali stanno in `BASSO`: la reazione totale
    vale -5000 N, i due terzi del carico consistente (+3333,33 N) si sommano
    sui nodi stampati, e restano -1666,67 N. Il terzo nodo della faccia e'
    libero e non entra nella stampa.

    Il passo 4 e' la forma esatta che `write_inp` scrive dal 27/08/2026: una
    sola card `*DSLOAD` che azzera le superfici dei passi distribuiti
    precedenti e dichiara la propria. Prova tre cose insieme -- che la
    ridichiarazione **sostituisca** invece di sommarsi, che `P, 0.0` sia
    accettato senza avvisi, e che piu' righe dati sotto una card sola valgano.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    tetraedro = np.array([[0, 1, 2, 3]], dtype=np.int64)
    # I numeri di faccia non si indovinano: li da' la tabella del programma,
    # gia' provata contro il solutore dal test della pressione su S4.
    faccia_y = abaqus.element_surface(tetraedro, np.array([0, 1, 3]), "C3D4")
    faccia_x = abaqus.element_surface(tetraedro, np.array([0, 2, 3]), "C3D4")
    assert len(faccia_y) == 1 and len(faccia_x) == 1, "le due facce non sono una sola ciascuna"

    peso = "TUTTO, GRAV, 9810.0, 0.0, 0.0, -1.0"
    stampa = "*NODE PRINT, NSET=BASSO\nRF\n*END STEP"
    deck = f"""*HEADING
sonda #84: una pressione dichiarata in un passo agisce anche in quello dopo?
*NODE
1, 0.0, 0.0, 0.0
2, 100.0, 0.0, 0.0
3, 0.0, 100.0, 0.0
4, 0.0, 0.0, 100.0
*ELEMENT, TYPE=C3D4, ELSET=TUTTO
1, 1, 2, 3, 4
*NSET, NSET=BASSO
1, 2, 3
*SURFACE, TYPE=ELEMENT, NAME=PELLE
1, S{faccia_y[0][1]}
*SURFACE, TYPE=ELEMENT, NAME=PELLE2
1, S{faccia_x[0][1]}
*SOLID SECTION, ELSET=TUTTO, MATERIAL=ACCIAIO
*MATERIAL, NAME=ACCIAIO
*ELASTIC
210000.0, 0.3
*DENSITY
7.85e-9
*BOUNDARY
BASSO, 1, 3
** PASSO 1: solo peso proprio.
*STEP
*STATIC
*DLOAD
{peso}
{stampa}
** PASSO 2: peso proprio piu' la pressione su PELLE.
*STEP
*STATIC
*DLOAD
{peso}
*DSLOAD
PELLE, P, 1.0
{stampa}
** PASSO 3: peso proprio, e nessun *DSLOAD dichiarato qui dentro.
*STEP
*STATIC
*DLOAD
{peso}
{stampa}
** PASSO 4: PELLE ridichiarata a zero, PELLE2 dichiarata: una card sola.
*STEP
*STATIC
*DLOAD
{peso}
*DSLOAD
PELLE, P, 0.0
PELLE2, P, 1.0
{stampa}
"""
    (tmp_path / "sonda.inp").write_text(deck, encoding="ascii")

    processo = subprocess.run(
        [executable, "-i", "sonda"], cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert processo.returncode == 0, processo.stdout[-2000:] + processo.stderr[-2000:]
    # Anche la prova che un `*DSLOAD` senza parametri, e una riga `P, 0.0`,
    # non fanno rumore: e' la forma che `_passo_statico` scrive.
    assert not avvisi_inattesi(processo.stdout), "\n".join(avvisi_inattesi(processo.stdout))

    def reazione(passo: int) -> np.ndarray:
        reazioni = solve.leggi_reazioni(tmp_path / "sonda.dat", passo=passo)
        return np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)

    solo_peso, con_pressione, dopo, azzerata = (reazione(n) for n in (1, 2, 3, 4))
    atteso = -5000.0 / 3.0

    assert abs(solo_peso[1]) < 1e-6, f"il peso proprio non deve dare RF_y: {solo_peso}"
    assert con_pressione[1] == pytest.approx(atteso, rel=1e-5), (
        f"la pressione non arriva al solutore come dovrebbe: {con_pressione}"
    )
    assert dopo[1] == pytest.approx(atteso, rel=1e-5), (
        f"il passo 3 non dichiara alcun *DSLOAD e la sua RF_y vale {dopo[1]}: se "
        "fosse zero la pressione non persisterebbe, e #84 non sarebbe un difetto"
    )
    assert abs(azzerata[1]) < 1e-6, (
        f"ridichiarare `PELLE, P, 0.0` non azzera la pressione del passo 2: RF_y "
        f"vale {azzerata[1]} invece di zero. La ridichiarazione si somma invece di "
        "sostituire, e i passi distribuiti hanno bisogno di un altro rimedio (#84)"
    )
    assert azzerata[0] == pytest.approx(atteso, rel=1e-5), (
        f"la seconda pressione della stessa card non arriva: RF_x vale {azzerata[0]}"
    )


def test_la_pressione_permanente_agisce_anche_nel_passo_di_un_distribuito(tmp_path):
    """#111 e #119, la prova diretta: sul solutore, non sul testo del deck.

    La sonda di #84 qui sopra misura la persistenza di `*DSLOAD` su un deck
    scritto a mano, che apre i passi con `*DLOAD` liscio. Questa misura il deck
    che `write_inp` scrive davvero, dove ogni passo apre con `*DLOAD, OP=NEW`
    -- e quello, misurato in #119, cancella **anche** i carichi di superficie.
    Prima della correzione la permanente valeva -1666,667 nel primo passo e
    **0,0** nel passo del distribuito: spariva, col deck ancora valido e i
    numeri ancora plausibili. Nessun controllo sul testo del deck poteva
    vederlo, ed e' la ragione per cui questa prova sta qui e non fra i test
    che leggono il `.inp`.

    Le due pressioni agiscono su facce perpendicolari, PERMANENTE su y = 0 e
    VENTO su x = 0, e il peso proprio va in -z: ogni componente della reazione
    isola la propria pressione senza sottrazioni. Il valore atteso e' quello
    gia' derivato e misurato in #84 -- area 100 x 100 / 2 = 5000 mm² per
    1 MPa, di cui due terzi del carico consistente si risommano sui nodi
    stampati: -5000/3 N.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    nodi = np.array([
        [0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0],
    ])
    tetraedro = np.array([[0, 1, 2, 3]], dtype=np.int64)
    faccia_y = abaqus.element_surface(tetraedro, np.array([0, 1, 3]), "C3D4")
    percorso = tmp_path / "permanente.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedro,
        node_sets={"BASE": np.array([0, 1, 2])},
        material=Material(name="ACCIAIO", young=210000.0, poisson=0.3, density=7.85e-9),
        element_surfaces={"PERMANENTE": faccia_y},
        pressure=("PERMANENTE", 1.0),
        carichi=CarichiConfig(
            distribuiti=(
                CaricoDistribuito(nome="VENTO", selettore="FACCIA_X", pressione=1.0),
            )
        ),
        nset_selettori={"FACCIA_X": np.array([0, 2, 3])},
    )

    processo = subprocess.run(
        [executable, "-i", "permanente"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert processo.returncode == 0, processo.stdout[-2000:] + processo.stderr[-2000:]
    assert not avvisi_inattesi(processo.stdout), "\n".join(avvisi_inattesi(processo.stdout))

    def reazione(passo: int) -> np.ndarray:
        reazioni = solve.leggi_reazioni(tmp_path / "permanente.dat", passo=passo)
        return np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)

    atteso = -5000.0 / 3.0
    gravita, vento = reazione(1), reazione(2)

    assert gravita[1] == pytest.approx(atteso, rel=1e-5), (
        f"la permanente non arriva nemmeno al primo passo: RF_y vale {gravita[1]}"
    )
    assert vento[0] == pytest.approx(atteso, rel=1e-5), (
        f"il distribuito non arriva al suo passo: RF_x vale {vento[0]}"
    )
    assert vento[1] == pytest.approx(atteso, rel=1e-5), (
        f"la pressione permanente non agisce nel passo del distribuito: RF_y vale "
        f"{vento[1]} invece di {atteso}. E' la card riscritta per esteso che la "
        "tiene viva li' dentro (#119): il *DLOAD, OP=NEW in testa al passo cancella "
        "anche i *DSLOAD, quindi senza quella card una spinta del terreno si spegne "
        "in silenzio dal primo passo distribuito in poi"
    )
