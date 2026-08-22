"""Fase 0 — CalculiX accetta il nostro .inp e da un risultato corretto?

Caso di prova: colonna a base quadrata incastrata al piede sotto peso proprio.
Accorciamento in sommita in forma chiusa: u = rho * g * L^2 / (2 * E).
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import (
    GRAVITY_MM_S2,
    AnalysisConfig,
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
    spostamento esattamente nullo. L'oracolo e' che qualcosa si sia
    mosso.

    Mutazione dichiarata dal brief (base zero invece di base uno sul
    numero di nodo del *CLOAD): verificata inerte su questa mesh. Il nodo
    0 non cade nel selettore "piastra" (il set TOP), quindi lo shift di
    un'unita' non produce mai un riferimento a un nodo inesistente: sposta
    solo la forza su un nodo vicino, quasi sempre ancora in TOP o comunque
    ancora capace di far accorciare la colonna. Misurato: col codice
    corretto max|uz|=0.0275 mm, con la mutazione 0.0300 mm -- stesso
    ordine, nessuna soglia su questo oracolo li separa.

    Seconda mutazione tentata (grado 1 invece di 3 sul *CLOAD, forza
    dichiarata verticale scritta come orizzontale): non collassa al
    rumore di gravita' come atteso. Misurato: corretto max|uz|=0.0274568
    mm, mutato max|uz|=0.223764 mm -- l'ipotesi che la forza orizzontale
    lasci la colonna a subire solo il peso proprio e' falsa su questo
    banco: la colonna e' snella (100x100x400 mm), e una forza applicata
    fuori asse in sommita' la inflette, e la flessione su una sezione
    cosi' snella sposta la sommita' in z (per rotazione della sezione)
    piu' di quanto faccia il carico assiale corretto -- un rapporto di
    ~8.1x, sotto l'ordine di grandezza che separerebbe pulito senza una
    soglia stretta. Nessuna soglia scelta per questo motivo: nessuna
    delle due mutazioni tentate uccide questo test in modo netto.
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
