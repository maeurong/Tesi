import itertools
import re

import meshio
import numpy as np
import pytest

from meshrec.core import abaqus, config, synth, volume
from meshrec.core.config import Material
from materiale import ANALISI, MATERIALE, crea_config


SIZE = (100.0, 40.0, 200.0)

TELAIO_PIEDI_ASIMMETRICI = [
    ((0.0,    0.0,    0.0), (200.0,  800.0,  200.0)),   # piede largo
    ((0.0, 2200.0,    0.0), (200.0,  300.0,  200.0)),   # piede stretto
    ((0.0,  300.0,  200.0), (200.0,  200.0, 1600.0)),   # montante sinistro
    ((0.0, 2300.0,  200.0), (200.0,  200.0, 1600.0)),   # montante destro
    ((0.0,  300.0, 1800.0), (200.0, 2200.0,  200.0)),   # traverso
]
"""Portale con i due piedi di larghezza diversa.

L'asimmetria in basso inclina la direzione principale senza che la nuvola sia
inclinata: e' la forma esatta del difetto misurato su `lab_frame.pcd`, dove le
zapatas larghe e basse portano l'asse altezza a 22,43 gradi dal verticale.
La struttura poggia su tutta la luce, quindi un vincolo corretto deve coprirla
tutta: e' cio' che distingue "appoggio mancante" da "vuoto in mezzo".
"""


# Questo file prova la logica **geometrica** dell'esportatore -- terna, set di
# nodi, impronta a terra, selettori, ripartizione dei carichi -- su magli
# lineari, che sono quelli che le sue fixture producono. Dal ripristino del
# quadratico (#45) il predefinito di `TetConfig` e' C3D10, e una `TetConfig()`
# nuda accanto a un maglio a quattro colonne fa sollevare l'esportatore prima
# di arrivare a cio' che il test guarda. Dichiararlo qui, una volta, dice anche
# a chi legge che l'elemento non e' la variabile sotto esame.
TET_LINEARE = config.TetConfig(element="C3D4")


@pytest.fixture
def cube_mesh():
    vertices, faces = synth.box_mesh(SIZE)
    return volume.tetrahedralize(
        vertices, faces, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )


@pytest.fixture(scope="module")
def cube_mesh_fine():
    """Lo stesso banco di `cube_mesh`, con il doppio dei nodi.

    Serve un selettore in cui **un** nodo preso non tocchi alcuna faccia di
    bordo intera: sui 16 nodi di `cube_mesh` la faccia superiore ha i soli
    quattro vertici, e ogni sottoinsieme che ne tolga uno perde tutta l'area
    invece di lasciarne un nodo a secco.
    """
    vertices, faces = synth.box_mesh(SIZE)
    return volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )


# Un cubo in sei tetraedri (decomposizione di Kuhn), coi vertici numerati sui
# bit di (i, j, k).
_CUBO_IN_SEI = (
    (0, 1, 3, 7), (0, 1, 7, 5), (0, 5, 7, 4),
    (0, 3, 2, 7), (0, 6, 4, 7), (0, 2, 6, 7),
)


@pytest.fixture(scope="module")
def griglia_mesh():
    """Lo stesso banco di `cube_mesh`, ma **costruito a mano** invece che da TetGen.

    Esiste per #66. La CI su due piattaforme ha misurato che TetGen produce
    magli **diversi** fra Linux x86-64 e macOS arm64 a parita' di versione
    (0.8.4), di ingresso e di opzioni: sulla stessa scatola rende 16 nodi e
    **24** elementi su macOS contro 16 e **18** su Linux, e col vincolo di
    volume piu' stretto 30/48 contro 32/56, inserendo punti di Steiner a
    quote che sull'altra piattaforma non esistono. Il volume totale invece
    coincide **esatto** su entrambe: la geometria e' giusta, e' la
    discretizzazione a differire.

    I test che usano questa fixture non provano la meshatura: provano gli
    avvisi e il resoconto dei carichi che toccano il vincolo. Farli dipendere
    da un generatore che non e' riproducibile fra piattaforme li rendeva
    fragili senza aggiungere nulla -- su Linux uno dei tre non trovava
    nemmeno lo scenario che voleva provare (l'intersezione diventava totale e
    `export_model` sollevava invece di avvisare).

    Griglia 1x1x4 su (100, 40, 200): **20 nodi, 24 tetraedri**, volume
    esattamente 800000, quote a 0, 50, 100, 150 e 200. Nessun numero qui
    dipende dalla piattaforma.
    """
    xs, ys, zs = (
        np.linspace(0.0, SIZE[0], 2),
        np.linspace(0.0, SIZE[1], 2),
        np.linspace(0.0, SIZE[2], 5),
    )
    nodi = np.array([(x, y, z) for x in xs for y in ys for z in zs], dtype=np.float64)

    def indice(i, j, k):
        return (i * 2 + j) * 5 + k

    tetraedri = [
        [
            [
                indice(i + (n & 1), j + ((n >> 1) & 1), k + ((n >> 2) & 1))
                for n in range(8)
            ][c]
            for c in combo
        ]
        for i in range(1)
        for j in range(1)
        for k in range(4)
        for combo in _CUBO_IN_SEI
    ]
    return nodi, np.array(tetraedri, dtype=np.int64)


def _sommita_piu_il_nodo(nodi: np.ndarray, punto: tuple[float, float, float]) -> np.ndarray:
    """I nodi della faccia superiore, piu' quello che sta esattamente in `punto`.

    Il nodo in piu' sta sotto la faccia superiore, quindi nessuna faccia di
    bordo che lo tocchi ha tutti i propri nodi nell'insieme: la sua area
    tributaria e' zero, e il selettore ne ha esattamente uno.
    """
    alti = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    fuori = np.flatnonzero(np.linalg.norm(nodi - np.array(punto), axis=1) < 1e-6)
    assert fuori.size == 1, f"il banco non ha un solo nodo in {punto}: ne ha {fuori.size}"
    return np.sort(np.concatenate([alti, fuori]))


def _base_and_top(nodes: np.ndarray, tolerance: float = 1e-6) -> dict[str, np.ndarray]:
    z = nodes[:, 2]
    return {
        "BASE": np.flatnonzero(z <= z.min() + tolerance),
        "TOP": np.flatnonzero(z >= z.max() - tolerance),
    }


def test_inp_is_readable_by_meshio(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=_base_and_top(nodes),
        material=MATERIALE,
    )

    mesh = meshio.read(path)
    assert len(mesh.points) == len(nodes)
    reread_tets = np.vstack([block.data for block in mesh.cells if block.type == "tetra"])
    assert len(reread_tets) == len(tets)
    # meshio riconverte gli indici 1-based del file in 0-based in lettura:
    # il confronto coi tets di partenza (gia' 0-based) e' diretto, verificato.
    assert np.array_equal(reread_tets, tets)


def test_inp_contains_sets_material_and_gravity_step(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    sets = _base_and_top(nodes)
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=sets,
        material=MATERIALE,
        print_nsets=("TOP",),
    )
    text = path.read_text(encoding="ascii")

    assert "*ELEMENT, TYPE=C3D4, ELSET=ALL_WALL" in text
    assert "*NSET, NSET=BASE" in text
    assert "*NSET, NSET=TOP" in text
    assert "*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=MURATURA" in text
    assert "1500.0, 0.2" in text
    assert "1.8e-09" in text
    assert "BASE, 1, 3" in text
    assert "ALL_WALL, GRAV, 9810.0, 0.0, 0.0, -1.0" in text
    assert "*NODE PRINT, NSET=TOP" in text


def test_node_and_element_indices_are_one_based(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=_base_and_top(nodes),
        material=MATERIALE,
    )
    lines = path.read_text(encoding="ascii").splitlines()

    node_start = lines.index("*NODE") + 1
    assert lines[node_start].split(",")[0].strip() == "1"

    element_header = next(i for i, line in enumerate(lines) if line.startswith("*ELEMENT"))
    first_element = [int(value) for value in lines[element_header + 1].split(",")]
    assert first_element[0] == 1
    assert min(first_element[1:]) >= 1
    assert max(first_element[1:]) <= len(nodes)


def _read_nset(text: str, name: str) -> set[int]:
    """Rilegge un blocco *NSET dal testo dell'.inp, indici riconvertiti a 0-based."""
    lines = text.splitlines()
    header = lines.index(f"*NSET, NSET={name}") + 1
    data_lines = []
    for line in lines[header:]:
        if line.startswith("*"):
            break
        data_lines.append(line)
    return {
        int(value) - 1
        for line in data_lines
        for value in line.split(",")
    }


def test_base_set_written_matches_expected_and_holds_only_the_lowest_nodes(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    sets = _base_and_top(nodes)
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=sets,
        material=MATERIALE,
    )
    text = path.read_text(encoding="ascii")

    written_base = _read_nset(text, "BASE")

    assert written_base == set(sets["BASE"].tolist())
    assert len(written_base) >= 4
    assert np.allclose(nodes[sorted(written_base), 2], nodes[:, 2].min())


def test_material_values_round_trip_with_precision(tmp_path, cube_mesh):
    """Materiale con valori non predefiniti, scelti per mettere in difficolta la
    formattazione (young con molte cifre decimali, poisson diverso dal default,
    densita in notazione scientifica lontana dal default): i valori riletti dal
    testo devono coincidere numericamente con quelli di partenza, non solo
    'sembrare giusti' guardando le cifre stampate."""
    nodes, tets = cube_mesh
    material = Material(name="LATERIZIO", young=2750.123456789, poisson=0.27, density=7.654321e-6)
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=_base_and_top(nodes),
        material=material,
    )
    lines = path.read_text(encoding="ascii").splitlines()

    elastic_line = lines[lines.index("*ELASTIC") + 1]
    written_young, written_poisson = (float(value) for value in elastic_line.split(","))
    written_density = float(lines[lines.index("*DENSITY") + 1])

    assert written_young == pytest.approx(material.young)
    assert written_poisson == pytest.approx(material.poisson)
    assert written_density == pytest.approx(material.density)

    assert f"*MATERIAL, NAME={material.name}" in lines
    assert f"*SOLID SECTION, ELSET=ALL_WALL, MATERIAL={material.name}" in lines


def test_alignment_puts_thickness_on_x_length_on_y_height_on_z():
    """Muro 1000 lungo, 300 alto, 50 spesso, ruotato di 30 gradi attorno a z."""
    rng = np.random.default_rng(0)
    raw = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(2000, 3))
    angle = np.radians(30.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated = raw @ rotation.T + np.array([500.0, -200.0, 75.0])

    aligned, transform, metrics = abaqus.align_to_axes(rotated)
    extent = aligned.max(axis=0) - aligned.min(axis=0)

    assert extent[0] == pytest.approx(50.0, rel=0.1)     # spessore su x
    assert extent[1] == pytest.approx(1000.0, rel=0.1)   # lunghezza su y
    assert extent[2] == pytest.approx(300.0, rel=0.1)    # altezza su z
    assert aligned[:, 2].min() == pytest.approx(0.0, abs=1e-9)
    assert transform.shape == (4, 4)
    assert metrics["extent"] == pytest.approx(extent.tolist(), rel=0.1)


def test_the_transform_is_invertible_back_to_the_original_frame():
    rng = np.random.default_rng(1)
    original = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(500, 3))
    aligned, transform, _ = abaqus.align_to_axes(original)

    homogeneous = np.column_stack([aligned, np.ones(len(aligned))])
    back = (homogeneous @ np.linalg.inv(transform).T)[:, :3]

    assert back == pytest.approx(original, abs=1e-6)


def test_node_sets_cover_the_six_faces_of_a_box():
    nodes = np.array(
        [[x, y, z] for x in (0.0, 50.0) for y in (0.0, 1000.0) for z in (0.0, 300.0)]
    )
    sets = abaqus.build_node_sets(nodes, tolerance=1.0)

    assert sorted(sets) == ["BASE", "FACE_BACK", "FACE_FRONT", "SIDE_LEFT", "SIDE_RIGHT", "TOP"]
    assert len(sets["BASE"]) == 4
    assert nodes[sets["BASE"]][:, 2] == pytest.approx(0.0)
    assert nodes[sets["TOP"]][:, 2] == pytest.approx(300.0)
    assert nodes[sets["FACE_FRONT"]][:, 0] == pytest.approx(0.0)
    assert nodes[sets["FACE_BACK"]][:, 0] == pytest.approx(50.0)


def test_build_node_sets_ha_le_chiavi_della_costante():
    """Le chiavi di `build_node_sets` sono quelle di `NOMI_SET_DI_FACCIA`, non una lista a parte.

    `build_node_sets` e' scritta come dizionario letterale, non come uno
    `zip` posizionale con `NOMI_SET_DI_FACCIA`: un test contro una lista di
    stringhe copiate a mano (come sopra) non si accorgerebbe se qualcuno
    rinominasse una voce della costante altrove nel modulo. Confrontare
    contro la costante stessa lega il test alla fonte, non a una sua copia.

    Mutazione che lo uccide: rinominare una voce di `NOMI_SET_DI_FACCIA`
    senza rinominarla anche qui.
    """
    nodes = np.array([[x, y, z] for x in (0.0, 50.0) for y in (0.0, 1000.0) for z in (0.0, 300.0)])
    sets = abaqus.build_node_sets(nodes, tolerance=1.0)
    assert set(sets) == set(config.NOMI_SET_DI_FACCIA)


def test_il_deck_non_contiene_piu_card_che_calculix_scavalca(tmp_path):
    """Zero avvisi non e' cosmesi: e' cio' che rende leggibile un avviso vero.

    Misurato il 21/08/2026 sul deck as-built: `ccx` 2.22 emette due avvisi,
    "parameter not recognized: NAME=GRAVITA" e "parameter not recognized:
    FIELD". Sono card Abaqus che CalculiX non conosce, e nessuno le leggeva.
    Un avviso benigno tollerato e' un avviso che nasconde quello vero.

    `*NODE FILE` e `*EL FILE` sono keyword Abaqus legacy, valide, e sono quelle
    che CalculiX vuole per l'uscita ascii: il cambio non perde la validita' del
    lato Abaqus. Il nome del passo scende a commento.

    Sostituisce `test_output_requests_are_in_the_modern_form`, che asseriva il
    contrario: la forma «moderna» *OUTPUT, FIELD e' proprio quella che
    CalculiX scarta con un avviso.

    `synth.box_mesh` da' la sola superficie triangolare (il brief la passava
    diretta a `write_inp`, che pero' vuole C3D4 a quattro nodi): qui si
    tetraedrizza prima, come fa il resto del file.
    """
    vertices, faces = synth.box_mesh((100.0, 100.0, 100.0))
    nodi, elementi = volume.tetrahedralize(
        vertices, faces, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets={"BASE": np.array([0])}, material=MATERIALE, step_name="GRAVITA",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*OUTPUT" not in testo
    assert "*NODE OUTPUT" not in testo
    assert "*ELEMENT OUTPUT" not in testo
    assert "*STEP, NAME=" not in testo
    assert "** NOME PASSO: GRAVITA" in testo
    assert "*NODE FILE" in testo
    assert "*EL FILE" in testo


def test_i_tre_casi_statici_e_la_modale_diventano_quattro_passi(tmp_path):
    """Un deck, quattro passi, un'esecuzione.

    Misurato il 21/08/2026: `ccx` accetta i quattro in fila e chiude con
    "Job finished", zero avvisi e zero errori.
    """
    vertices, faces = synth.box_mesh((100.0, 100.0, 100.0))
    nodi, elementi = volume.tetrahedralize(
        vertices, faces, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    carichi = config.CarichiConfig(
        spinta=config.SpintaOrizzontale(coefficiente=0.1, asse="y"),
        carico_sommita=config.CaricoSommita(risultante=1000.0, nset="TOP"),
        modale=config.Modale(modi=6),
    )
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets=_base_and_top(nodi),
        material=MATERIALE, carichi=carichi,
    )

    # Le asserzioni contano RIGHE INTERE, non sottostringhe: `GRAV` compare
    # anche dentro il commento `** NOME PASSO: GRAVITA` che questo stesso task
    # introduce, e un conteggio per sottostringa direbbe 5 dove il deck ha 4
    # carichi. Un test che conta la cosa sbagliata e' verde per caso.
    righe = percorso.read_text(encoding="ascii").splitlines()
    testo = "\n".join(righe)
    assert righe.count("*STEP") == 4
    assert righe.count("*END STEP") == 4
    # la riga subito dopo *FREQUENCY, non una sottostringa nell'intero deck:
    # "\n6\n" nel testo intero passerebbe anche se il 6 fosse dentro un *NSET,
    # e sarebbe verde per coincidenza (RULING M, stessa famiglia del difetto
    # sopra sulle righe intere).
    assert righe[righe.index("*FREQUENCY") + 1] == "6"
    assert "*CLOAD" in testo
    # la spinta e' una seconda GRAV nello stesso passo, non un passo a se':
    # senza il peso proprio accanto, la spinta descriverebbe una struttura che
    # non pesa
    carichi_grav = [riga for riga in righe if riga.startswith("ALL_WALL, GRAV,")]
    assert len(carichi_grav) == 4, carichi_grav  # peso proprio nei 3 passi statici + spinta
    # ogni passo statico stampa le reazioni: e' il controllo di conservazione
    assert righe.count("*NODE PRINT, NSET=BASE") == 3
    assert righe.count("RF") == 3


def test_le_forme_modali_non_chiedono_tensioni(tmp_path):
    """Da un passo *FREQUENCY non escono MPa.

    Le forme sono normalizzate sulla massa, e una von Mises calcolata su una
    forma da' numeri plausibili e privi di significato: fino a 88,5 MPa,
    misurati il 21/08/2026. Il deck non le chiede nemmeno.
    """
    vertices, faces = synth.box_mesh((100.0, 100.0, 100.0))
    nodi, elementi = volume.tetrahedralize(
        vertices, faces, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    carichi = config.CarichiConfig(modale=config.Modale(modi=4))
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets=_base_and_top(nodi), material=MATERIALE, carichi=carichi,
    )

    passo_modale = percorso.read_text(encoding="ascii").split("** NOME PASSO: MODALE")[1]
    assert "*EL FILE" not in passo_modale
    assert "*NODE FILE" in passo_modale


def test_la_pressione_si_ripete_in_ogni_passo_statico_con_carichi(tmp_path):
    """`pressure` e' una condizione permanente del modello, non un caso di
    carico fra gli altri: si ripete in ogni passo statico esattamente come il
    peso proprio (vedi il docstring di `write_inp`, Important A del giro di
    revisione). Qui i passi statici sono due (peso proprio + spinta): la
    `*DSLOAD` deve comparire in entrambi, non solo nel primo. Senza `OP=NEW`:
    `ccx` 2.21 non riconosce quel parametro su questa card e ne fa due avvisi
    (misurato in CI, #84)."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")
    carichi = config.CarichiConfig(spinta=config.SpintaOrizzontale(coefficiente=0.1, asse="x"))
    percorso = tmp_path / "con_pressione.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"FACCIA_BASSA": superficie},
        pressure=("FACCIA_BASSA", 0.25),
        carichi=carichi,
    )

    righe = percorso.read_text(encoding="ascii").splitlines()
    assert righe.count("*STEP") == 2
    assert righe.count("*DSLOAD") == 2
    assert righe.count("FACCIA_BASSA, P, 0.25") == 2


def test_il_carico_in_sommita_rifiuta_un_insieme_vuoto(tmp_path):
    """Zero nodi nell'insieme e' lo stesso problema silenzioso della chiave
    mancante appena sopra nel codice (un carico applicato a nulla), non un
    `ZeroDivisionError` grezzo: stessa guardia, stesso registro di errore."""
    carichi = config.CarichiConfig(carico_sommita=config.CaricoSommita(risultante=1000.0, nset="TOP"))

    with pytest.raises(ValueError, match="TOP"):
        abaqus.write_inp(
            tmp_path / "vuoto.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3]), "TOP": np.array([], dtype=np.int64)},
            material=MATERIALE,
            element_type="C3D8I",
            carichi=carichi,
        )


def test_export_model_writes_both_files_and_reports_mass(tmp_path):
    meshio = pytest.importorskip("meshio")
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        TET_LINEARE,
    )

    assert (tmp_path / "wall_model.inp").exists()
    assert (tmp_path / "wall_model.vtu").exists()
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0, rel=0.02)
    assert metrics["mass"] == pytest.approx(metrics["volume"] * 1.8e-9, rel=1e-6)
    assert metrics["node_sets"]["BASE"] > 0
    read_back = meshio.read(tmp_path / "wall_model.vtu")
    assert len(read_back.points) == len(nodes)


def test_export_model_elenca_i_casi_di_carico_dichiarati(tmp_path):
    """`casi_di_carico` e' derivato da `carichi`, non da `cfg` (Task 3 li ha
    separati in blocchi di primo livello distinti): un elenco che leggesse i
    tre campi da `cfg` solleverebbe un `AttributeError`, non un elenco corto."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)
    carichi = config.CarichiConfig(spinta=config.SpintaOrizzontale(coefficiente=0.1, asse="x"))

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        TET_LINEARE,
        carichi=carichi,
    )

    assert metrics["casi_di_carico"] == ["GRAVITA", "SPINTA_ORIZZONTALE"]


def test_export_model_senza_carichi_elenca_il_solo_peso_proprio(tmp_path):
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        TET_LINEARE,
    )

    assert metrics["casi_di_carico"] == ["GRAVITA"]


def _yaw(angle_deg: float) -> np.ndarray:
    """Rotazione attorno a z: lo z del sistema d'ingresso resta il verticale vero."""
    angle = np.radians(angle_deg)
    return np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )


def test_rotation_matrix_is_always_right_handed():
    rng = np.random.default_rng(3)
    base = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(800, 3))

    for angle_deg in (0.0, 15.0, 61.0, 123.0, 250.0):
        cloud = base @ _yaw(angle_deg).T + np.array([10.0, 20.0, 30.0])
        _, transform, _ = abaqus.align_to_axes(cloud)

        assert np.linalg.det(transform[:3, :3]) == pytest.approx(1.0)


def test_extent_is_invariant_to_the_input_rotation():
    rng = np.random.default_rng(4)
    base = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(1000, 3))

    aligned_a, _, _ = abaqus.align_to_axes(base @ _yaw(10.0).T + np.array([500.0, -100.0, 20.0]))
    aligned_b, _, _ = abaqus.align_to_axes(base @ _yaw(200.0).T + np.array([-300.0, 400.0, -50.0]))

    extent_a = aligned_a.max(axis=0) - aligned_a.min(axis=0)
    extent_b = aligned_b.max(axis=0) - aligned_b.min(axis=0)

    assert extent_a == pytest.approx(extent_b, rel=1e-6)


def test_align_to_axes_ignores_interior_nodes_when_given_boundary_reference():
    """Riproduce il difetto misurato sul muro reale: i punti di Steiner interni
    aggiunti da TetGen, mediati con quelli di bordo, ruotavano il riferimento
    di oltre 13 gradi dal verticale vero. Se la stima torna a usare tutti i
    nodi, questo test deve fallire."""
    corners = np.array(
        [[x, y, z] for x in (0.0, 50.0) for y in (0.0, 1000.0) for z in (0.0, 300.0)]
    )
    index = {tuple(point): position for position, point in enumerate(corners)}

    def idx(x: float, y: float, z: float) -> int:
        return index[(x, y, z)]

    # decomposizione standard di un cuboide in sei tetraedri lungo la
    # diagonale principale (000)-(111): sei permutazioni degli assi.
    o = idx(0.0, 0.0, 0.0)
    full = idx(50.0, 1000.0, 300.0)
    x1 = idx(50.0, 0.0, 0.0)
    y1 = idx(0.0, 1000.0, 0.0)
    z1 = idx(0.0, 0.0, 300.0)
    xy = idx(50.0, 1000.0, 0.0)
    xz = idx(50.0, 0.0, 300.0)
    yz = idx(0.0, 1000.0, 300.0)

    hex_tets = [
        (o, x1, xy, full),
        (o, x1, xz, full),
        (o, y1, xy, full),
        (o, y1, yz, full),
        (o, z1, xz, full),
        (o, z1, yz, full),
    ]

    # il primo tetraedro viene spaccato in quattro, introducendo un nodo
    # interno fortemente sbilanciato verso uno dei suoi vertici: come i punti
    # di Steiner di TetGen, non appartiene mai a una faccia di bordo.
    a, b, c, d = hex_tets[0]
    steiner = 0.85 * corners[a] + 0.05 * corners[b] + 0.05 * corners[c] + 0.05 * corners[d]
    nodes = np.vstack([corners, steiner])
    steiner_index = len(corners)

    tets = np.array(
        [
            (steiner_index, b, c, d),
            (steiner_index, a, c, d),
            (steiner_index, a, b, d),
            (steiner_index, a, b, c),
        ]
        + hex_tets[1:]
    )

    boundary = np.unique(abaqus.boundary_faces(tets))
    assert steiner_index not in boundary

    _, _, metrics_boundary_only = abaqus.align_to_axes(nodes, reference=nodes[boundary])
    _, _, metrics_all_nodes = abaqus.align_to_axes(nodes)

    assert metrics_boundary_only["extent"] == pytest.approx([50.0, 1000.0, 300.0], rel=1e-6)
    assert metrics_all_nodes["extent"] != pytest.approx([50.0, 1000.0, 300.0], rel=0.05)


def test_the_triad_follows_the_surface_not_the_distribution_of_nodes():
    """Il riferimento e' una proprieta della geometria, non del maglio.

    I nodi interni sono addensati lungo la diagonale del solido, come fa un
    raffinamento che infittisce dove i triangoli sono grandi: una PCA sui nodi
    ne esce ruotata, una PCA sulla superficie no. Se qualcuno rimette la stima
    sui nodi, questo test deve fallire.
    """
    superficie = np.array(
        [[x, y, z] for x in (0.0, 50.0) for y in (0.0, 1000.0) for z in (0.0, 300.0)]
    )
    passo = np.linspace(0.0, 1.0, 2000)[:, None]
    interni = passo * np.array([[50.0, 1000.0, 300.0]])

    nodi = np.vstack([superficie, interni])

    allineati, _, con_superficie = abaqus.align_to_axes(nodi, reference=superficie)
    _, _, sui_nodi = abaqus.align_to_axes(nodi)

    assert con_superficie["extent"] == pytest.approx([50.0, 1000.0, 300.0], rel=1e-6)
    assert sui_nodi["extent"] != pytest.approx([50.0, 1000.0, 300.0], rel=0.05)

    # Lo scostamento al primo ottante si calcola sui nodi trasformati, non sul
    # riferimento: senza questo, BASE non corrisponderebbe alla base del solido.
    assert allineati.min(axis=0) == pytest.approx([0.0, 0.0, 0.0], abs=1e-9)


def test_l_asse_altezza_e_il_verticale_anche_se_la_pca_pende():
    """La terna non lascia decidere l'altezza alla PCA.

    Sul banco a piedi asimmetrici la direzione principale piu' vicina al
    verticale sta 13,58 gradi fuori (misurato prima della correzione), e da li'
    discende il set BASE su un piede solo. Dopo la correzione l'asse altezza e'
    il verticale in ingresso per costruzione, e l'unica cosa ancora stimata e'
    l'imbardata, che e' quanto il docstring ha sempre dichiarato.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)

    _allineati, transform, _metriche = abaqus.align_to_axes(punti, reference=punti)

    assert transform[2, :3] == pytest.approx([0.0, 0.0, 1.0], abs=1e-12)
    # terna destrorsa e ortonormale: il determinante non e' un dettaglio, un -1
    # scambierebbe SIDE_LEFT con SIDE_RIGHT senza che nulla se ne accorga
    assert np.linalg.det(transform[:3, :3]) == pytest.approx(1.0, abs=1e-12)
    assert transform[:3, :3] @ transform[:3, :3].T == pytest.approx(np.eye(3), abs=1e-12)


def test_i_nodi_bassi_dopo_l_allineamento_coprono_tutta_la_luce():
    """Il vincolo prende entrambi i piedi, non uno.

    Misurato sul banco: prima della correzione i nodi entro 60 mm dal minimo di
    z-modello sono 131 e coprono lo 0,088 della lunghezza; dopo sono 654 e la
    coprono per intero.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)

    allineati, _transform, _metriche = abaqus.align_to_axes(punti, reference=punti)

    bassi = allineati[allineati[:, 2] <= allineati[:, 2].min() + 60.0]
    rapporto = float(np.ptp(bassi[:, 1]) / np.ptp(allineati[:, 1]))
    assert rapporto > 0.95, f"il vincolo copre solo {rapporto:.3f} della luce"


def test_export_model_estimates_the_triad_on_the_reference_it_is_given(tmp_path):
    """Il riferimento arriva fino al deck: e' la strada che usa la pipeline."""
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )

    metrics = abaqus.export_model(
        tmp_path / "m.inp",
        tmp_path / "m.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        TET_LINEARE,
        reference=vertices,
    )

    assert metrics["extent"] == pytest.approx(sorted(SIZE), rel=1e-6)
    assert metrics["node_sets"]["BASE"] > 0


def test_the_tolerance_follows_the_boundary_spacing_not_the_element_volume(cube_mesh):
    """La tolleranza si lega alla geometria, non a un artefatto del raffinamento.

    L'euristica precedente derivava dal volume medio dell'elemento, che su una
    distribuzione a coda pesante e' dominato da pochi tetraedri enormi
    dell'interno: sul muro reale la mediana vale 14,6 mm^3 contro una media di
    30.735, un fattore duemila. La scala che conta e' la spaziatura dei nodi sul
    bordo del maglio di volume, perche' e' li che i set vengono estratti ed e'
    quella la scala su cui la faccia ricostruita ondula.

    Il parallelepipedo sintetico non puo' dimostrarlo: ha maglia uniforme,
    quindi le due scale vi coincidono quasi. Qui si fissa la definizione; la
    misura che ha scartato l'euristica precedente e le due candidate e' su dati
    reali, in docs/fase-1-tolleranza-set.md.
    """
    nodes, tets = cube_mesh
    facce = abaqus.boundary_faces(tets)
    spigoli = np.unique(
        np.sort(np.vstack([facce[:, [0, 1]], facce[:, [1, 2]], facce[:, [0, 2]]]), axis=1), axis=0
    )
    atteso = np.median(np.linalg.norm(nodes[spigoli[:, 0]] - nodes[spigoli[:, 1]], axis=1))

    assert abaqus.set_tolerance(nodes, tets, 6.0) == pytest.approx(6.0 * atteso)
    assert abaqus.set_tolerance(nodes, tets, 1.0) == pytest.approx(atteso)


def test_the_footprint_is_fully_covered_on_a_flat_base(cube_mesh):
    """Su una base piana l'insieme vincolato copre tutta la superficie d'appoggio."""
    nodes, tets = cube_mesh
    bordo = np.unique(abaqus.boundary_faces(tets))
    spaziatura = abaqus.set_tolerance(nodes, tets, 1.0)
    insieme = abaqus.build_node_sets(nodes, 6.0 * spaziatura)["BASE"]

    assert abaqus.footprint_coverage(nodes, bordo, insieme, spaziatura) == 1.0


def test_the_coverage_counts_columns_of_the_footprint_not_nodes():
    """Contare i nodi di un insieme non dice se copra la faccia che deve coprire.

    4738 nodi su una faccia coperta al 55,78% e 4738 su una coperta al 100%
    sono lo stesso numero in metrics.json: e' il difetto per cui un `BASE` da 9
    nodi produceva un deck formalmente valido per un modello non vincolato.

    La griglia e' esplicita e non tetraedrizzata perche' il parallelepipedo
    sintetico non serve allo scopo: con la sua maglia l'impronta intera entra in
    una cella sola, e la copertura vi vale 1 per costruzione qualunque cosa
    accada. E' lo stesso motivo per cui la regola e' stata scelta su dati reali.
    """
    passo = 10.0
    x, y = np.meshgrid(np.arange(10) * passo, np.arange(10) * passo, indexing="ij")
    bassi = np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)])
    nodes = np.vstack([bassi, bassi + [0.0, 0.0, 500.0]])
    bordo = np.arange(len(nodes))

    # celle di lato 4 x 5 = 20 mm su un'impronta di 90 x 90: venticinque colonne,
    # tutte a contatto. Il vincolo copre il solo angolo, cioe' una colonna.
    angolo = np.flatnonzero((nodes[:, 2] == 0.0) & (nodes[:, 0] < 20.0) & (nodes[:, 1] < 20.0))
    tutti = np.flatnonzero(nodes[:, 2] == 0.0)

    assert len(angolo) == 4
    assert abaqus.footprint_coverage(nodes, bordo, angolo, 5.0) == pytest.approx(1.0 / 25.0)
    assert abaqus.footprint_coverage(nodes, bordo, tutti, 5.0) == 1.0


def test_export_warns_when_the_constrained_set_misses_the_footprint(tmp_path, cube_mesh, monkeypatch):
    """La guardia sul set vuoto era cieca su tutto cio' che non era vuoto.

    La copertura e' sostituita perche' costruire una geometria che la faccia
    scendere richiederebbe una scansione reale: sul parallelepipedo sintetico la
    base e' un piano esatto e la copertura vale 1 per qualunque tolleranza.
    """
    nodes, tets = cube_mesh
    monkeypatch.setattr(abaqus, "footprint_coverage", lambda *args: 0.3)

    with pytest.warns(abaqus.UnconstrainedModelWarning, match="appoggio"):
        metrics = abaqus.export_model(
            tmp_path / "wall_model.inp",
            tmp_path / "wall_model.vtu",
            nodes,
            tets,
            config.AnalysisConfig(material=MATERIALE),
            TET_LINEARE,
        )

    assert metrics["fixed_nset_coverage"] == 0.3


def test_export_reports_how_much_of_the_footprint_is_constrained(tmp_path, cube_mesh):
    nodes, tets = cube_mesh

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        TET_LINEARE,
    )

    assert metrics["fixed_nset_coverage"] == 1.0
    assert metrics["boundary_spacing"] > 0.0
    assert metrics["set_tolerance"] == pytest.approx(6.0 * metrics["boundary_spacing"])


def test_l_estensione_in_pianta_del_vincolo_vale_uno_su_due_piedi():
    """Un telaio a due piedi e' ben vincolato anche se e' vuoto in mezzo.

    E' la proprieta' che distingue questa grandezza da footprint_coverage: i due
    piedi coprono l'intera luce, quindi il rapporto vale 1 pur essendoci un
    vuoto fra loro. Se valesse meno di 1, la grandezza confonderebbe "vuoto in
    mezzo" con "manca un appoggio" e sarebbe inutilizzabile su un portale.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)
    allineati, _t, _m = abaqus.align_to_axes(punti, reference=punti)
    bassi = np.flatnonzero(allineati[:, 2] <= allineati[:, 2].min() + 60.0)

    esteso = abaqus.constraint_plan_extent(allineati, bassi)

    # Tre asserzioni indipendenti, ciascuna contro un oracolo esterno.
    # `minimo == min(x, y)` sarebbe tautologica: ricalcola la formula sui
    # valori appena restituiti invece di confrontarli con cio' che ci si
    # aspetta, e un errore che sbagliasse `x` passerebbe inosservato
    # (dimostrato per iniezione: `x` sbagliato di un fattore 0,3 fa scendere
    # `minimo` a 0,3 e il test resta verde).
    assert esteso["x"] == pytest.approx(1.0, abs=0.05)
    assert esteso["y"] == pytest.approx(1.0, abs=0.05)
    assert esteso["minimo"] == pytest.approx(1.0, abs=0.05)


def test_l_estensione_in_pianta_crolla_se_il_vincolo_tiene_un_angolo():
    """Un insieme ammucchiato in un angolo si vede, e footprint_coverage no.

    Misurato sul deck as-built del 21/08/2026: BASE aveva 278 nodi in una toppa
    y 574-808 su un pezzo lungo 3144, cioe' un rapporto di 0,074, mentre
    fixed_nset_coverage dichiarava 1,0. E' il caso che questa grandezza esiste
    per cogliere.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)
    allineati, _t, _m = abaqus.align_to_axes(punti, reference=punti)
    # un solo piede: i nodi bassi con y sotto il primo quarto della luce
    limite = allineati[:, 1].min() + 0.25 * np.ptp(allineati[:, 1])
    un_piede = np.flatnonzero(
        (allineati[:, 2] <= allineati[:, 2].min() + 60.0) & (allineati[:, 1] <= limite)
    )

    esteso = abaqus.constraint_plan_extent(allineati, un_piede)

    assert esteso["minimo"] < 0.5


def test_l_estensione_in_pianta_crolla_anche_quando_e_x_l_asse_stretto():
    """Il buco lasciato dal Task 2: sui due banchi esistenti y e' sempre
    l'asse piu' stretto, quindi `minimo = min(x, y)` e un'implementazione
    sbagliata `minimo := y` sono indistinguibili -- un vincolo stretto sul
    solo asse x passerebbe inosservato. Qui x e' l'asse stretto: se
    `minimo` seguisse `y` invece che il minimo vero, uscirebbe 1.0 invece di
    seguire x.

    Muore se: il corpo di `constraint_plan_extent` diventa
    `rapporti["minimo"] = rapporti["y"]`.
    """
    nodi = np.array(
        [[x, y, 0.0] for x in (0.0, 10.0, 100.0) for y in (0.0, 100.0)]
    )
    stretto_su_x = np.flatnonzero(nodi[:, 0] <= 10.0)  # x in [0, 10], y intera

    esteso = abaqus.constraint_plan_extent(nodi, stretto_su_x)

    assert esteso["x"] == pytest.approx(0.1)
    assert esteso["y"] == pytest.approx(1.0)
    assert esteso["minimo"] == pytest.approx(0.1)


def test_le_facce_di_bordo_di_un_esaedro_solo_sono_sei_quadrilateri():
    """boundary_faces dava per scontati quattro nodi per elemento e tre per
    faccia. Un esaedro ha sei facce, tutte quadrilatere, e tutte di bordo."""
    esaedro = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    facce = abaqus.boundary_faces(esaedro)

    assert facce.shape == (6, 4)
    assert len(np.unique(facce, axis=0)) == 6


def test_due_esaedri_affiancati_non_hanno_la_faccia_condivisa_sul_bordo():
    """Il controllo che smentisce il precedente: se la faccia interna comparisse
    fra quelle di bordo, ogni set di faccia e ogni superficie esportata
    conterrebbero nodi interni al solido."""
    doppio = np.array(
        [[0, 1, 2, 3, 4, 5, 6, 7], [4, 5, 6, 7, 8, 9, 10, 11]], dtype=np.int64
    )

    facce = abaqus.boundary_faces(doppio)

    assert facce.shape == (10, 4), "sei piu' sei meno la faccia condivisa contata due volte"
    condivisa = np.sort(np.array([4, 5, 6, 7]))
    assert not (np.sort(facce, axis=1) == condivisa).all(axis=1).any()


def test_le_facce_di_bordo_dei_tetraedri_restano_quelle_di_prima():
    """La generalizzazione non deve cambiare il comportamento sui tetraedri: e'
    la macchina con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )

    facce = abaqus.boundary_faces(tets)

    assert facce.shape[1] == 3
    assert len(np.unique(facce)) == len(np.unique(abaqus.boundary_faces(tets)))
    # una superficie chiusa: ogni spigolo compare in esattamente due facce
    spigoli = np.sort(
        np.vstack([facce[:, [0, 1]], facce[:, [1, 2]], facce[:, [0, 2]]]), axis=1
    )
    _, conteggi = np.unique(spigoli, axis=0, return_counts=True)
    assert (conteggi == 2).all()


def test_il_deck_dichiara_il_tipo_di_elemento_che_gli_si_chiede(tmp_path):
    """C3D8I non e' un dettaglio estetico: un telaio lavora a flessione, e C3D8
    a integrazione piena si irrigidirebbe a taglio restituendo spostamenti
    troppo piccoli senza alcun segnale sulla mesh."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)
    percorso = tmp_path / "esaedro.inp"

    abaqus.write_inp(
        percorso, nodi, esaedri,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I, ELSET=ALL_WALL" in testo
    assert "1, 1, 2, 3, 4, 5, 6, 7, 8" in testo
    assert "*ELEMENT, TYPE=C3D4" not in testo


def test_un_tipo_di_elemento_che_non_combacia_coi_nodi_viene_rifiutato(tmp_path):
    """L'errore arriva prima di scrivere il file, non dopo che un solutore ha
    letto un deck con otto nodi dichiarati C3D4."""
    nodi = np.zeros((8, 3))
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    with pytest.raises(ValueError, match="C3D4"):
        abaqus.write_inp(
            tmp_path / "storto.inp", nodi, esaedri,
            node_sets={"BASE": np.array([0])},
            material=MATERIALE,
            element_type="C3D4",
        )


def test_boundary_faces_rifiuta_un_numero_di_nodi_sconosciuto():
    """Prima il dispatch era un ternario: qualunque conteggio diverso da 8
    veniva trattato come tetraedro. Un conteggio non previsto deve fermarsi
    con un errore, non produrre un bordo sbagliato in silenzio."""
    elementi_a_sei_nodi = np.array([[0, 1, 2, 3, 4, 5]], dtype=np.int64)

    with pytest.raises(ValueError, match="6"):
        abaqus.boundary_faces(elementi_a_sei_nodi)


def test_export_model_rifiuta_l_incoerenza_tipo_nodi_prima_di_qualunque_calcolo(
    tmp_path, monkeypatch, cube_mesh
):
    """Il controllo su tipo e numero di nodi deve fermarsi prima di qualunque
    calcolo geometrico: se arrivasse dopo, un tipo dichiarato non coerente coi
    nodi potrebbe far girare l'allineamento e la copertura su una topologia
    interpretata male prima di fallire.

    `element_type="C3D8"` passa per il parametro esplicito e non per
    `tet_cfg.element`, che accetta il solo 'C3D4': e' l'unica via per
    dichiarare un tipo esaedrico su un array di tetraedri senza che la
    validazione di pydantic intercetti il caso prima ancora di arrivare a
    `export_model`."""
    nodes, tets = cube_mesh

    def non_dovrebbe_arrivare_qui(*args, **kwargs):
        raise AssertionError("align_to_axes chiamata prima della validazione del tipo")

    monkeypatch.setattr(abaqus, "align_to_axes", non_dovrebbe_arrivare_qui)

    with pytest.raises(ValueError, match="C3D8"):
        abaqus.export_model(
            tmp_path / "m.inp",
            tmp_path / "m.vtu",
            nodes,
            tets,
            config.AnalysisConfig(material=MATERIALE),
            TET_LINEARE,
            element_type="C3D8",
        )


_CUBO = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
_ESAEDRO = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_le_sei_etichette_di_faccia_di_un_esaedro_sono_le_sue_sei_facce():
    """Il test non legge la tabella: costruisce l'insieme dei nodi che ogni
    etichetta nomina e verifica che siano le sei facce distinte del cubo. Una
    tabella sbagliata nominerebbe due volte la stessa faccia, o una diagonale."""
    nominate = {
        tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[8][numero]))
        for numero in range(6)
    }
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(_ESAEDRO).tolist()}

    assert len(nominate) == 6
    assert nominate == vere


def test_facce_del_solutore_c3d8_sono_cicli_di_perimetro_non_diagonali():
    """F3 del giro di correzione finale: FACCE_DEL_SOLUTORE porta l'ordine dei
    nodi, e l'ordine E' l'informazione (vedi il commento sopra la tabella) --
    ne' `test_le_sei_etichette_...` (sorted()) ne' `test_ogni_etichetta_di_
    faccia_dell_esaedro_nomina_il_baricentro_giusto` (baricentro) lo vedono:
    entrambi buttano via l'ordine. Su faccia svergolata questo pesa su
    `nodi_dipendenti_legati`, il numero che il confronto pubblica.

    Deriva gli spigoli veri dell'esaedro da FACCE_TOPOLOGICHE senza copiare il
    manuale del solutore: una coppia di nodi e' uno spigolo se compare insieme
    in esattamente due delle sei facce topologiche (un spigolo separa due
    facce; una diagonale ne attraversa una sola).

    Mutazione che deve morire: S2 da (4, 7, 6, 5) a (4, 7, 5, 6) -- non piu'
    un perimetro ma una farfalla, con 7-5 e 6-4 diagonali della faccia.
    """
    facce_topologiche = abaqus.FACCE_TOPOLOGICHE[8]
    spigoli = {
        frozenset((a, b))
        for faccia in facce_topologiche
        for a, b in itertools.combinations(faccia, 2)
        if sum(a in f and b in f for f in facce_topologiche) == 2
    }

    for faccia in abaqus.FACCE_DEL_SOLUTORE[8]:
        for i in range(len(faccia)):
            lato = frozenset((faccia[i], faccia[(i + 1) % len(faccia)]))
            assert lato in spigoli, f"{faccia}: {tuple(lato)} non e' uno spigolo, e' una diagonale"


def test_le_quattro_etichette_di_faccia_di_un_tetraedro_sono_le_sue_quattro_facce():
    tetraedro = np.array([[0, 1, 2, 3]], dtype=np.int64)
    nominate = {tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[4][numero])) for numero in range(4)}
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(tetraedro).tolist()}

    assert len(nominate) == 4
    assert nominate == vere


def test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta():
    """Il controllo della spec: area della superficie esportata contro area
    calcolata sulle facce. Su un cubo unitario ogni faccia vale 1."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    assert superficie == [(0, 1)], "la faccia z=0 di un C3D8 e' S1"
    assert abaqus.surface_area(_CUBO, _ESAEDRO, superficie, "C3D8I") == pytest.approx(1.0)


def test_la_superficie_di_elemento_non_nomina_una_faccia_solo_sfiorata():
    """Il controllo che smentisce il precedente: tre nodi su quattro di una
    faccia non sono quella faccia, e nominarla applicherebbe un carico dove
    l'utente non lo ha chiesto."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2]), "C3D8I")

    assert superficie == []


def test_la_superficie_esportata_ha_l_area_delle_facce_che_dichiara(tmp_path):
    """Il deck e' la fonte: si rilegge il file e si contano le coppie scritte,
    invece di fidarsi di cio' che la funzione ha restituito."""
    nodi_base = np.flatnonzero(_CUBO[:, 2] <= 1e-9)
    superficie = abaqus.element_surface(_ESAEDRO, nodi_base, "C3D8I")
    percorso = tmp_path / "carico.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": nodi_base},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"FACCIA_BASSA": superficie},
        pressure=("FACCIA_BASSA", 0.25),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT, NAME=FACCIA_BASSA" in testo
    assert "1, S1" in testo
    assert "*DSLOAD" in testo
    assert "FACCIA_BASSA, P, 0.25" in testo


def test_senza_carico_laterale_il_deck_non_ha_alcuna_card_di_pressione(tmp_path):
    """Il carico laterale e' opzionale e assente se non richiesto: un deck che
    lo portasse comunque a zero applicherebbe una pressione nulla dichiarata,
    che e' un'altra cosa da nessuna pressione."""
    percorso = tmp_path / "senza.inp"
    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*DSLOAD" not in testo
    assert "*SURFACE" not in testo
    assert "*TIE" not in testo


def test_il_tie_nomina_due_superfici_gia_dichiarate(tmp_path):
    """Un *TIE che punta a una superficie mai dichiarata e' un deck rotto che
    il solutore rifiuta solo alla lettura: l'errore arriva prima."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    with pytest.raises(ValueError, match="MAI_DICHIARATA"):
        abaqus.write_inp(
            tmp_path / "rotto.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3])},
            material=MATERIALE,
            element_type="C3D8I",
            element_surfaces={"UNA": superficie},
            ties=(("GIUNZIONE_1", "UNA", "MAI_DICHIARATA"),),
        )


def test_un_maglio_senza_elementi_non_scrive_un_deck(tmp_path):
    """`write_inp` controllava le **colonne** di `elements`, mai le righe.

    Misurato prima della guardia: `np.zeros((0, 10))` con `C3D10` scriveva
    391 byte e non sollevava. Un deck con zero elementi e' valido per `ccx`,
    che lo risolve in silenzio: reazioni nulle contro un peso nullo, e i
    verdetti di `core/solve.py` escono **verdi su nulla**. E' il caso in cui
    un controllo di conservazione non ha niente da conservare, e non
    distinguerlo da un modello sano e' peggio di non averlo.

    Questo test prova il percorso **diretto**: `write_inp` chiamata con gli
    argomenti gia' pronti. Il percorso di produzione passa da `export_model`,
    che col maglio vuoto non arriva mai fin qui e ha una guardia propria: la
    prova sta nel test subito sotto. I due non si fondono -- uccidono due
    guardie diverse in due funzioni diverse.

    Ordine dichiarato quando anche `element_type` e' ignoto: parla prima il
    tipo. Senza un tipo noto non si sa nemmeno quante colonne aspettarsi, e
    il numero di righe e' la meno interessante delle due notizie.

    Mutazione che lo uccide: togliere il controllo su `len(elements)`. Il
    deck si scrive e nessuna eccezione arriva.
    """
    percorso = tmp_path / "vuoto.inp"

    with pytest.raises(ValueError, match="nessun elemento"):
        abaqus.write_inp(
            percorso, np.zeros((0, 3)), np.zeros((0, 10), dtype=np.int64),
            node_sets={"BASE": np.zeros(0, dtype=np.int64)},
            material=MATERIALE, element_type="C3D10",
        )
    assert not percorso.exists()

    # zero righe **e** tipo ignoto: parla il tipo, non le righe
    with pytest.raises(ValueError, match="sconosciuto"):
        abaqus.write_inp(
            percorso, np.zeros((0, 3)), np.zeros((0, 10), dtype=np.int64),
            node_sets={"BASE": np.zeros(0, dtype=np.int64)},
            material=MATERIALE, element_type="C3D999",
        )
    assert not percorso.exists()


def test_export_model_col_maglio_vuoto_nomina_gli_elementi_non_i_nodi(tmp_path):
    """La porta di produzione rifiuta il maglio vuoto, e dice perche'.

    Misurato prima di questa guardia: `export_model` non raggiungeva affatto la
    guardia di `write_inp`. Con zero elementi `boundary_faces` non da' bordo, il
    riferimento per la terna resta vuoto e `align_to_axes` solleva per primo con
    «nessun nodo da allineare» -- un errore vero, ma sui **nodi**, mentre gli
    otto nodi passati qui ci sono tutti. Chi legge quel messaggio cerca il
    difetto nella nuvola invece che nel maglio.

    Mutazione che lo uccide: togliere il controllo su `len(elements)` da
    `export_model`. Il test torna rosso sul messaggio, non sul tipo di
    eccezione, perche' e' il messaggio la cosa che era sbagliata.
    """
    with pytest.raises(ValueError, match="nessun elemento"):
        abaqus.export_model(
            tmp_path / "m.inp",
            tmp_path / "m.vtu",
            np.zeros((8, 3)),
            np.zeros((0, 4), dtype=np.int64),
            config.AnalysisConfig(material=MATERIALE),
            TET_LINEARE,
        )
    assert list(tmp_path.iterdir()) == [], "niente sul disco: né il deck né il .vtu"


def test_tie_e_pressione_risolvono_le_superfici_ignorando_le_maiuscole(tmp_path):
    """Le due guardie di membership erano rimaste al confronto esatto.

    `ccx` risolve i nomi senza distinguere le maiuscole (misurato in
    `docs/fase-6-cantiere/sonda-caso-nomi/`): una superficie dichiarata
    `PELLE` e un `*TIE` che la nomina `pelle` sono lo stesso `*SURFACE` per
    il solutore, e il deck si legge. Il rifiuto diceva invece «non è fra le
    superfici dichiarate», cioè accusava una causa che non c'era -- la stessa
    categoria di difetto della guardia sui carichi distribuiti, corretta nel
    giro precedente.

    Il deck scrive la grafia che il chiamante ha dato, non quella canonica:
    a cambiare è chi viene accettato, non che cosa viene scritto.

    Mutazione che lo uccide: rimettere `s not in superfici` e `pressure[0]
    not in superfici`. Entrambe sollevano e il deck non si scrive.
    """
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")
    percorso = tmp_path / "caso.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"PELLE": superficie, "CUOIO": superficie},
        ties=(("GIUNZIONE_1", "pelle", "Cuoio"),),
        pressure=("PeLLe", 0.25),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "pelle, Cuoio" in testo
    assert "PeLLe, P, 0.25" in testo


def test_una_superficie_mai_dichiarata_resta_un_rifiuto_anche_col_casefold(tmp_path):
    """La metà che rende non vacuo il test sopra: allentare il confronto al
    `casefold` non deve spegnere la guardia. Un nome che non esiste in
    nessuna grafia resta un deck rotto, e l'errore arriva prima del solutore.
    """
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    with pytest.raises(ValueError, match="MAI_DICHIARATA"):
        abaqus.write_inp(
            tmp_path / "rotto.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3])},
            material=MATERIALE, element_type="C3D8I",
            element_surfaces={"PELLE": superficie},
            ties=(("GIUNZIONE_1", "pelle", "MAI_DICHIARATA"),),
        )

    with pytest.raises(ValueError, match="MAI_DICHIARATA"):
        abaqus.write_inp(
            tmp_path / "rotto2.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3])},
            material=MATERIALE, element_type="C3D8I",
            element_surfaces={"PELLE": superficie},
            pressure=("MAI_DICHIARATA", 0.25),
        )


def test_il_tie_con_tolleranza_scrive_position_tolerance(tmp_path):
    """Ruling AH (giro di correzione 6): il quarto elemento facoltativo della
    tupla di un *TIE e' la sua `POSITION TOLERANCE`, scritta sulla card. Un
    *TIE a tre elementi (retrocompatibile) non la scrive affatto -- un deck
    senza quel parametro non e' lo stesso di un deck con tolleranza zero.

    Muore se: la card smette di scrivere `POSITION TOLERANCE=` quando il
    quarto elemento e' dato."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")
    percorso = tmp_path / "con_tolleranza.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"UNA": superficie, "DUE": superficie},
        ties=(("GIUNZIONE_1", "UNA", "DUE", 3.5),),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "POSITION TOLERANCE=3.5" in testo
    assert "*TIE, NAME=GIUNZIONE_1, POSITION TOLERANCE=3.5, ADJUST=NO" in testo


def test_il_tie_senza_tolleranza_non_scrive_position_tolerance(tmp_path):
    """Il controllo che smentisce il precedente: un *TIE a tre elementi (la
    forma di prima di questo giro) non deve scrivere alcuna
    `POSITION TOLERANCE`, ne' a zero ne' a un valore predefinito -- un
    parametro assente non e' la stessa cosa di un parametro dichiarato zero
    (stessa regola gia' vera per `pressure` in questo modulo)."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")
    percorso = tmp_path / "senza_tolleranza.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"UNA": superficie, "DUE": superficie},
        ties=(("GIUNZIONE_1", "UNA", "DUE"),),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "POSITION TOLERANCE" not in testo
    assert "*TIE, NAME=GIUNZIONE_1, ADJUST=NO" in testo


def test_la_superficie_di_elemento_non_include_una_faccia_interna_condivisa():
    """RULING N: una faccia condivisa da due elementi adiacenti non e' di
    bordo. Se comparisse comunque nella superficie (perche' tutti i suoi nodi
    stanno nell'insieme dato, senza controllare l'occorrenza), un *TIE o un
    carico laterale finirebbero applicati dentro il solido invece che sulla
    sua pelle."""
    doppio = np.array(
        [[0, 1, 2, 3, 4, 5, 6, 7], [4, 5, 6, 7, 8, 9, 10, 11]], dtype=np.int64
    )
    tutti_i_nodi = np.arange(12)

    superficie = abaqus.element_surface(doppio, tutti_i_nodi, "C3D8I")

    assert len(superficie) == 10, "sei piu' sei meno la faccia condivisa contata due volte"
    condivisa = {4, 5, 6, 7}
    for elemento, numero in superficie:
        combo = abaqus.FACCE_DEL_SOLUTORE[8][numero - 1]
        nodi_faccia = set(doppio[elemento][list(combo)].tolist())
        assert nodi_faccia != condivisa, "la faccia interna condivisa non deve comparire"


def test_la_superficie_del_tie_nomina_la_faccia_il_cui_baricentro_e_dentro():
    """Ruling AF (giro di correzione 5): il criterio del `*TIE` e' diverso da
    quello di `element_surface` apposta -- vedi il docstring di
    `tie_surface`. Il cubo unitario ha la faccia S1 (z=0) con baricentro
    esatto (0.5, 0.5, 0.0): nessun nodo del cubo sta li' (sono tutti agli
    angoli), quindi un criterio per nodi non potrebbe mai nominare S1 da
    questo predicato -- solo un criterio per baricentro puo'.

    Muore se: `tie_surface` torna a un criterio per nodi (tipo
    `element_surface`) invece che per baricentro -- il predicato dato non
    coinciderebbe mai con un nodo reale e la superficie uscirebbe vuota."""
    def dentro_altro(punti):
        return np.linalg.norm(punti - np.array([0.5, 0.5, 0.0]), axis=1) < 0.1

    superficie = abaqus.tie_surface(_CUBO, _ESAEDRO, dentro_altro, "C3D8I")

    assert superficie == [(0, 1)], "S1 e' l'unica faccia col baricentro li' vicino"


def test_la_superficie_del_tie_non_include_una_faccia_interna_condivisa():
    """Stesso RULING N di `element_surface`, sulla nuova funzione: una faccia
    interna condivisa da due elementi non e' pelle, qualunque cosa dica il
    predicato del baricentro. Il predicato qui e' sempre vero apposta, cosi'
    il test isola il filtro sul bordo (`boundary_faces`) dal criterio del
    baricentro -- se il filtro sparisse, tutte e dodici le facce (sei per
    elemento) comparirebbero, non dieci.

    Muore se: il filtro sulle sole facce di bordo sparisce."""
    doppio = np.array(
        [[0, 1, 2, 3, 4, 5, 6, 7], [4, 5, 6, 7, 8, 9, 10, 11]], dtype=np.int64
    )
    coordinate = np.zeros((12, 3))  # il predicato ignora la geometria: e' sempre vero

    def dentro_altro(punti):
        return np.ones(len(punti), dtype=bool)

    superficie = abaqus.tie_surface(coordinate, doppio, dentro_altro, "C3D8I")

    assert len(superficie) == 10, "sei piu' sei meno la faccia condivisa contata due volte"


def test_la_superficie_del_tie_con_tocca_include_una_faccia_toccata_solo_a_un_nodo():
    """Ruling AH (giro di correzione 6): il lato indipendente ha facce piu'
    grandi (mesh piu' rada) che possono coprire solo in parte la zona di
    contatto -- il baricentro cade fuori pur toccando davvero. `tocca=True`
    include anche queste: la faccia S1 del cubo (nodi 0,1,2,3, baricentro
    (0.5, 0.5, 0.0)) tocca l'origine solo nel nodo 0, a distanza 0 dal
    predicato, ma il suo baricentro dista sqrt(0.5) ~= 0.707 -- ben oltre il
    raggio 0.1 del predicato.

    Muore se: `tocca=True` smette di aggiungere il criterio per nodo (torna
    equivalente a `tocca=False`) -- la superficie con `tocca=True` uscirebbe
    vuota come quella senza."""
    def dentro_altro(punti):
        return np.linalg.norm(punti - np.array([0.0, 0.0, 0.0]), axis=1) < 0.1

    solo_baricentro = abaqus.tie_surface(_CUBO, _ESAEDRO, dentro_altro, "C3D8I")
    assert solo_baricentro == [], "il baricentro di S1 e' troppo lontano dall'origine"

    con_tocca = abaqus.tie_surface(_CUBO, _ESAEDRO, dentro_altro, "C3D8I", tocca=True)
    assert (0, 1) in con_tocca, "S1 tocca l'origine nel nodo 0, e tocca=True deve vederlo"


_SCATOLA = np.array([
    [0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 3.0, 0.0], [0.0, 3.0, 0.0],
    [0.0, 0.0, 5.0], [2.0, 0.0, 5.0], [2.0, 3.0, 5.0], [0.0, 3.0, 5.0],
])
_UN_ESAEDRO = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_ogni_etichetta_di_faccia_dell_esaedro_nomina_il_baricentro_giusto():
    """RULING M(a): un confronto per insiemi non vede uno scambio fra due
    etichette (i due insiemi di facce restano gli stessi). Il baricentro
    invece e' diverso faccia per faccia: qui e' calcolato dalle coordinate del
    parallelepipedo (facce z minimo/massimo, y minimo/massimo, x minimo/
    massimo, dalla convenzione del manuale S1..S6), non dalla tabella.
    Il parallelepipedo e' asimmetrico apposta: su un cubo due facce potrebbero
    avere baricentri troppo simili per distinguere uno scambio."""
    basso, alto = _SCATOLA.min(axis=0), _SCATOLA.max(axis=0)
    cx, cy, cz = (basso + alto) / 2.0

    attesi = [
        np.array([cx, cy, basso[2]]),  # S1: faccia z minimo
        np.array([cx, cy, alto[2]]),   # S2: faccia z massimo
        np.array([cx, basso[1], cz]),  # S3: faccia y minimo
        np.array([alto[0], cy, cz]),   # S4: faccia x massimo
        np.array([cx, alto[1], cz]),   # S5: faccia y massimo
        np.array([basso[0], cy, cz]),  # S6: faccia x minimo
    ]

    for numero, atteso in enumerate(attesi):
        combo = abaqus.FACCE_DEL_SOLUTORE[8][numero]
        baricentro = _SCATOLA[list(combo)].mean(axis=0)
        assert baricentro == pytest.approx(atteso), f"S{numero + 1} non e' la faccia attesa"


_TETRAEDRO_ASIMMETRICO = np.array([
    [0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 5.0],
])


def test_ogni_etichetta_di_faccia_del_tetraedro_nomina_il_baricentro_giusto():
    """Stesso controllo del test precedente, sul tetraedro: dalla convenzione
    del manuale (S1=1-2-3, S2=1-4-2, S3=2-4-3, S4=3-4-1) ogni etichetta esclude
    un vertice preciso — S1 il quarto, S2 il terzo, S3 il primo, S4 il secondo
    — indipendente da come la tabella scrive la faccia."""
    escluso_per_numero = [3, 2, 0, 1]

    for numero, escluso in enumerate(escluso_per_numero):
        atteso = _TETRAEDRO_ASIMMETRICO[[i for i in range(4) if i != escluso]].mean(axis=0)
        combo = abaqus.FACCE_DEL_SOLUTORE[4][numero]
        baricentro = _TETRAEDRO_ASIMMETRICO[list(combo)].mean(axis=0)
        assert baricentro == pytest.approx(atteso), f"S{numero + 1} non e' la faccia attesa"


def test_le_aree_tributarie_sommano_all_area_della_superficie(cube_mesh):
    """La ripartizione non crea ne' perde area: la somma e' quella geometrica.

    L'oracolo e' l'area calcolata a mano sulla faccia nota, non
    `surface_area`: quella funzione **e'** `aree_tributarie(...).sum()`, e
    confrontare i due lati era una tautologia -- dare a ogni nodo l'area
    intera del triangolo invece di un terzo lasciava il test verde. La
    faccia superiore del banco misura 100 x 40 mm, e nessun altro numero.

    Mutazione che lo uccide: dare a ogni nodo l'area intera del triangolo
    invece di un terzo. La somma diventa tripla, 12000 mm2 invece di 4000.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    superficie = abaqus.element_surface(tetraedri, sets["TOP"], "C3D4")
    assert superficie, "la faccia superiore del banco e' vuota: banco inadatto"
    aree = abaqus.aree_tributarie(nodi, tetraedri, superficie, "C3D4")
    assert aree.shape == (len(nodi),)
    assert aree.sum() == pytest.approx(SIZE[0] * SIZE[1])


def test_solo_i_nodi_della_superficie_hanno_area(cube_mesh):
    """Chi non tocca alcuna faccia della superficie prende zero, non una quota.

    Mutazione che lo uccide: inizializzare l'array a un valore diverso da
    zero, o ripartire il totale su tutti i nodi della mesh.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    superficie = abaqus.element_surface(tetraedri, sets["TOP"], "C3D4")
    aree = abaqus.aree_tributarie(nodi, tetraedri, superficie, "C3D4")
    con_area = set(np.flatnonzero(aree > 0).tolist())
    assert con_area, "nessun nodo ha area: la superficie e' vuota"
    # I nodi che le facce della superficie toccano davvero. L'uguaglianza, e
    # non la sola inclusione: con `<=` una mutazione che azzera un vertice
    # per triangolo passerebbe, perche' toglierebbe nodi da un insieme che
    # deve solo restare dentro l'altro.
    toccati = {
        int(tetraedri[elemento][indice])
        for elemento, numero in superficie
        for indice in abaqus.FACCE_DEL_SOLUTORE[4][numero - 1]
    }
    assert con_area == toccati


def test_una_superficie_vuota_da_aree_tutte_nulle(cube_mesh):
    """Ingresso degenere: nessuna faccia, nessuna area, e nessuna eccezione qui.

    L'oracolo del totale nullo sta in `ripartisci`, dove c'e' un carico da
    applicare e un nome da mettere nel messaggio: questa funzione misura e
    basta.

    Mutazione che lo uccide: sollevare qui invece di rendere zeri. Il
    chiamante perderebbe la possibilita' di dire quale carico ha fallito.
    """
    nodi, tetraedri = cube_mesh
    aree = abaqus.aree_tributarie(nodi, tetraedri, [], "C3D4")
    assert aree.shape == (len(nodi),)
    assert not aree.any()


def test_una_faccia_a_quattro_nodi_si_divide_a_ventaglio_dal_primo():
    """Ingresso degenere non coperto dal banco tetraedrico del brief: qui la
    faccia ha quattro nodi (un C3D8), e il ventaglio parte dal primo come in
    `surface_area`.

    Sul quadrato unitario S1=(0,1,2,3) il ventaglio dal nodo 0 taglia lungo la
    diagonale 0-2: due triangoli rettangoli di area 0.5 ciascuno. I nodi 0 e 2
    stanno in entrambi (2 * 0.5/3 = 1/3), i nodi 1 e 3 in uno solo (0.5/3 =
    1/6).

    Mutazione che lo uccide: tagliare lungo l'altra diagonale (1-3) invece che
    dal primo nodo. La somma resterebbe 1.0 ma la distribuzione si scambia:
    [1/6, 1/3, 1/6, 1/3] invece di [1/3, 1/6, 1/3, 1/6].
    """
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")
    aree = abaqus.aree_tributarie(_CUBO, _ESAEDRO, superficie, "C3D8I")
    assert aree.shape == (len(_CUBO),)
    assert aree[:4] == pytest.approx([1 / 3, 1 / 6, 1 / 3, 1 / 6])
    assert aree[4:] == pytest.approx([0.0, 0.0, 0.0, 0.0])


def test_la_ripartizione_pesata_conserva_la_risultante(cube_mesh):
    """Le quote sommano esattamente alla risultante dichiarata.

    Mutazione che lo uccide: togliere la normalizzazione sul totale e
    usare `risultante * area`. La somma smette di chiudere.
    """
    nodi, tetraedri = cube_mesh
    indici = _base_and_top(nodi)["TOP"]
    quote, _ = abaqus.ripartisci(1200.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.shape == indici.shape
    assert quote.sum() == pytest.approx(1200.0)


def test_la_ripartizione_pesata_non_e_uniforme(cube_mesh):
    """E' il punto della pesatura: un nodo interno alla faccia prende piu' di uno d'angolo.

    Il banco e' il parallelepipedo tetraedrizzato, dove la faccia
    superiore ha nodi di grado diverso: e' la condizione reale, non una
    costruita per l'occasione.

    Mutazione che lo uccide: rendere `risultante / len(indici)`, cioe' la
    ripartizione uniforme di prima. Le quote diventano tutte uguali e lo
    scarto fra massimo e minimo si annulla.
    """
    nodi, tetraedri = cube_mesh
    indici = _base_and_top(nodi)["TOP"]
    quote, _ = abaqus.ripartisci(1200.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.max() > quote.min() * 1.05


def test_i_nodi_ad_area_nulla_prendono_zero_e_sono_contati(cube_mesh):
    """La quota nulla e' un fatto da riportare, non da nascondere.

    Al set TOP si aggiunge un nodo di BASE, che nessuna faccia di bordo
    interamente contenuta in TOP+quel nodo tocca: prende zero, e il
    resoconto lo conta.

    Non un "nodo interno" scelto per vicinanza al baricentro come nel brief:
    verificato su questo banco (`cube_mesh`, `max_volume=100_000.0`) che
    TetGen non aggiunge alcun punto di Steiner strettamente interno al
    parallelepipedo -- i 16 nodi sono tutti sul bordo (vertici e punti medi
    di spigolo/faccia) -- quindi il nodo piu' vicino al baricentro cade
    comunque su uno spigolo del solido e forma li' una faccia triangolare
    con tre nodi di TOP, con area non nulla. Un corner di BASE, sulla
    faccia opposta, non puo' condividere una faccia triangolare di bordo con
    tre nodi di TOP per costruzione geometrica (nessuna faccia piana del
    parallelepipedo tocca contemporaneamente z=0 e z=max), quindi da' area
    zero per certo e non per verifica sui dati di una singola corsa.

    Mutazione che lo uccide: contare i nodi ad area nulla con `>= 0`
    invece che `== 0`. Il resoconto direbbe che sono tutti a zero.
    """
    nodi, tetraedri = cube_mesh
    top = _base_and_top(nodi)["TOP"]
    base = _base_and_top(nodi)["BASE"]
    estraneo = int(base[0])
    assert estraneo not in top.tolist(), "BASE e TOP si sovrappongono: banco inadatto"
    indici = np.append(top, estraneo)
    quote, resoconto = abaqus.ripartisci(900.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.sum() == pytest.approx(900.0)
    assert resoconto["nodi"] == indici.size
    assert resoconto["nodi_ad_area_nulla"] == 1
    assert quote[-1] == pytest.approx(0.0)


def test_area_tributaria_totale_nulla_solleva_e_nomina_il_carico(cube_mesh):
    """Nessuna faccia di bordo contenuta: la pesatura non ha su cosa pesare.

    Il banco e' un solo nodo: con un nodo solo nessuna faccia triangolare puo'
    avere tutti e tre i suoi vertici dentro l'insieme, per combinatoria e non
    per posizione -- vale per qualunque nodo, interno o di bordo. Scrivere
    zero ovunque produrrebbe un passo statico che non carica nulla, con un
    nome che promette altro.

    Mutazione che lo uccide: rendere quote nulle invece di sollevare.
    """
    nodi, tetraedri = cube_mesh
    interno = int(np.argmin(np.linalg.norm(nodi - nodi.mean(axis=0), axis=1)))
    with pytest.raises(ValueError, match="INTERNO"):
        abaqus.ripartisci(10.0, nodi, tetraedri, np.array([interno]), "C3D4", nome="INTERNO")


def test_il_carico_in_sommita_ora_e_pesato(cube_mesh, tmp_path):
    """CARICO_TOP passa alla stessa ripartizione dei posizionati.

    Una sola ripartizione nel programma: due carichi che fanno la stessa
    cosa non possono farla in due modi diversi.

    Mutazione che lo uccide: lasciare `per_nodo = risultante / len(nodi)`
    nel ramo del carico in sommita'. I valori distinti del *CLOAD tornano
    a uno solo.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "deck.inp"
    abaqus.write_inp(
        percorso, nodi, tetraedri,
        node_sets=_base_and_top(nodi),
        material=MATERIALE,
        carichi=config.CarichiConfig(
            carico_sommita=config.CaricoSommita(risultante=1200.0, nset="TOP")
        ),
    )
    valori = [
        float(riga.split(", ")[2])
        for riga in percorso.read_text(encoding="ascii").splitlines()
        if riga.count(", ") == 2 and riga.split(", ")[1] == "3" and not riga.startswith("*")
    ]
    assert len(set(valori)) > 1, "la ripartizione e' tornata uniforme"
    assert sum(valori) == pytest.approx(-1200.0)


def _con_posizionati(percorso, cube_mesh, posizionati):
    """Scrive un deck col set TOP offerto come selettore 'piastra'.

    Ritorna il testo del deck e il resoconto: quello che `write_inp` rende,
    non un parametro d'uscita a parte (`resoconto_carichi`, tolto -- unico
    chiamante di produzione era gia' il valore di ritorno, il solo canale
    verificato era questo helper).
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    resoconto = abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=sets, material=MATERIALE,
        nset_selettori={"piastra": sets["TOP"]},
        carichi=config.CarichiConfig(posizionati=posizionati),
    )
    return percorso.read_text(encoding="ascii"), resoconto


def _forze_del_passo(testo: str, passo: str, quanti_nodi: int) -> np.ndarray:
    """Le forze nodali scritte dentro un passo, per nodo e componente."""
    forze = np.zeros((quanti_nodi, 3))
    dentro = False
    for riga in testo.splitlines():
        if riga.startswith(f"** NOME PASSO: {passo}"):
            dentro = True
        elif riga == "*END STEP":
            dentro = False
        elif dentro and not riga.startswith("*") and riga.count(", ") == 2:
            nodo, grado, valore = riga.split(", ")
            forze[int(nodo) - 1, int(grado) - 1] += float(valore)
    return forze


def _gradi_del_passo(testo: str, passo: str) -> set[str]:
    """I gradi di liberta per cui il passo scrive almeno una riga *CLOAD."""
    gradi: set[str] = set()
    dentro = False
    for riga in testo.splitlines():
        if riga.startswith(f"** NOME PASSO: {passo}"):
            dentro = True
        elif riga == "*END STEP":
            dentro = False
        elif dentro and not riga.startswith("*") and riga.count(", ") == 2:
            gradi.add(riga.split(", ")[1])
    return gradi


def test_un_posizionato_scrive_il_nset_del_selettore_e_il_passo_del_carico(cube_mesh, tmp_path):
    """Il selettore diventa un *NSET col suo nome, il carico un passo col suo.

    Mutazione che lo uccide: scrivere il *NSET col nome del carico invece
    che con quello del selettore. Due carichi sullo stesso selettore
    scriverebbero due set identici, che e' il nome fabbricato che la
    forma nominata esiste per togliere di mezzo.
    """
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
    ])
    # Riga intera, non sottostringa: "*NSET, NSET=piastra_SEL" contiene
    # "*NSET, NSET=piastra" come prefisso, e un `in` sulla stringa intera
    # lascerebbe passare un nome fabbricato che aggiunge un suffisso.
    assert "*NSET, NSET=piastra" in testo.splitlines()
    assert "** NOME PASSO: PRESSA" in testo


def test_le_forze_di_un_posizionato_sommano_alla_risultante(cube_mesh, tmp_path):
    """Il deck realizza la forza dichiarata, componente per componente.

    Mutazione che lo uccide: scrivere la quota su un grado fisso invece
    che sui tre della forza. La somma sulla x resta a zero.
    """
    nodi, _ = cube_mesh
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(300.0, 0.0, -1200.0)),
    ])
    somma = _forze_del_passo(testo, "PRESSA", len(nodi)).sum(axis=0)
    assert somma == pytest.approx([300.0, 0.0, -1200.0])


def test_ogni_posizionato_e_un_passo_a_se_col_peso_proprio(cube_mesh, tmp_path):
    """Due carichi, due passi, e il peso proprio in entrambi.

    Un passo senza peso proprio descriverebbe una struttura che non pesa:
    e' la stessa ragione per cui SPINTA_ORIZZONTALE e CARICO_TOP lo
    ripetono gia'.

    Mutazione che lo uccide: sommare i due carichi in un passo solo.
    Il conteggio dei passi scende a due.
    """
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
        config.CaricoPosizionato(nome="TIRO", selettore="piastra", forza=(0.0, 0.0, 800.0)),
    ])
    assert testo.count("** NOME PASSO: ") == 3  # GRAVITA, PRESSA, TIRO
    assert testo.count("ALL_WALL, GRAV, ") == 3


def test_due_carichi_sullo_stesso_selettore_scrivono_un_solo_nset(cube_mesh, tmp_path):
    """Due carichi che citano lo stesso selettore citano lo stesso nome: un solo *NSET.

    Riga del contratto non coperta dai test del brief: la parte "due passi"
    di quella riga la copre gia' il test sopra, questa copre la parte "un
    solo *NSET".

    Mutazione che lo uccide: scrivere il *NSET dentro il ciclo dei carichi
    invece che una volta per selettore in `nset_selettori`. Il conteggio
    salirebbe a due.
    """
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
        config.CaricoPosizionato(nome="TIRO", selettore="piastra", forza=(0.0, 0.0, 800.0)),
    ])
    # Righe intere: contare la sottostringa non distinguerebbe "piastra" da
    # un nome fabbricato tipo "piastra_PRESSA" e "piastra_TIRO".
    assert testo.splitlines().count("*NSET, NSET=piastra") == 1


def test_il_resoconto_riporta_la_forza_effettiva(cube_mesh, tmp_path):
    """Il programma dice con quali numeri ha fatto quello che ha fatto.

    Mutazione che lo uccide: scrivere le righe `*CLOAD` su un grado di
    liberta' fisso invece che sui tre della forza. Il resoconto continua a
    dire la cosa giusta -- lo ricava dalle quote, non dal file -- mentre il
    deck ne dice un'altra, e il confronto fra i due cade.

    **Non** lo uccide riportare `forza_dichiarata` al posto di
    `forza_effettiva`: `ripartisci` garantisce per costruzione che le quote
    sommino alla risultante, quindi le due sono lo stesso numero. E' il
    confronto col deck a dare a questo test un oracolo, non il resoconto
    da solo.
    """
    nodi, _ = cube_mesh
    testo, resoconto = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
    ])
    dal_deck = _forze_del_passo(testo, "PRESSA", len(nodi)).sum(axis=0)
    assert resoconto["PRESSA"]["forza_effettiva"] == pytest.approx(dal_deck)
    assert resoconto["PRESSA"]["nodi"] > 0


def test_un_posizionato_che_cita_un_selettore_non_risolto_solleva(cube_mesh, tmp_path):
    """Il deck non si scrive a meta': se il selettore non e' arrivato, si ferma qui.

    Mutazione che lo uccide: `nset_selettori.get(nome, np.array([]))`, che
    scriverebbe un *NSET vuoto e un carico applicato a nulla.
    """
    nodi, tetraedri = cube_mesh
    with pytest.raises(ValueError, match="piastra"):
        abaqus.write_inp(
            tmp_path / "deck.inp", nodi, tetraedri,
            node_sets=_base_and_top(nodi), material=MATERIALE,
            nset_selettori={},
            carichi=config.CarichiConfig(posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1.0)),
            ]),
        )


def test_selettore_non_risolto_nomina_anche_i_selettori_arrivati(cube_mesh, tmp_path):
    """Il messaggio non tace cosa e' arrivato: nomina anche i selettori risolti.

    Riga del contratto non coperta dai test del brief: quello sopra verifica
    solo che il nome del selettore mancante compaia, non che il messaggio
    elenchi anche gli arrivati.

    Mutazione che lo uccide: un messaggio generico ("selettore non
    risolto") che tace il contenuto di `nset_selettori`.
    """
    nodi, tetraedri = cube_mesh
    with pytest.raises(ValueError, match="altro"):
        abaqus.write_inp(
            tmp_path / "deck.inp", nodi, tetraedri,
            node_sets=_base_and_top(nodi), material=MATERIALE,
            nset_selettori={"altro": np.array([0])},
            carichi=config.CarichiConfig(posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1.0)),
            ]),
        )


def test_componente_nulla_non_scrive_riga_cload(cube_mesh, tmp_path):
    """Una componente che non conta rispetto alle sorelle non scrive la sua riga.

    Due percorsi, un contratto solo. Sulla **forza** la componente nulla
    arriva esatta dalla configurazione e il confronto con lo zero basta.
    Sul **momento** no: `np.cross(asse, separazione)` non produce mai uno
    zero esatto, e con un filtro assoluto meta' delle righe di una coppia
    erano rumore (misurato: `6, 1, -1.409807015e-16` accanto a
    `6, 2, 1.000000000e+01`, un grado che l'operatore non ha chiesto).

    L'uguaglianza fra insiemi, non tre `in` separati: l'assenza del grado
    trascurabile da sola non basta a dire che il filtro fa il suo lavoro
    sui gradi che contano -- un filtro che scartasse *tutte* le righe
    passerebbe il solo controllo di assenza.

    Mutazione che lo uccide: rimettere `componente != 0.0` al posto del
    confronto con `SOGLIA_COMPONENTE_RELATIVA`. Il passo TORSIONE torna a
    scrivere il grado 1 a 1e-16.
    """
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 5.0, -1200.0)),
        config.CaricoPosizionato(
            nome="TORSIONE", selettore="piastra",
            momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        ),
    ])
    assert _gradi_del_passo(testo, "PRESSA") == {"2", "3"}
    assert _gradi_del_passo(testo, "TORSIONE") == {"2"}


def test_la_coppia_realizza_il_momento_dichiarato(cube_mesh, tmp_path):
    """Somma delle forze nulla, momento risultante pari al modulo dichiarato.

    La faccia superiore del banco misura 100 x 40 mm: un braccio di 60 mm
    ci sta, e i due gruppi sono non vuoti.

    Mutazione che lo uccide: dare a entrambi i gruppi lo stesso verso.
    La somma delle forze smette di essere nulla e il momento si annulla.
    """
    nodi, _ = cube_mesh
    testo, _ = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(
            nome="TORSIONE", selettore="piastra",
            momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        ),
    ])
    forze = _forze_del_passo(testo, "TORSIONE", len(nodi))
    # Il peso proprio e' una *DLOAD e non compare fra le forze nodali.
    assert forze.sum(axis=0) == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
    momento = np.cross(nodi - nodi.mean(axis=0), forze).sum(axis=0)
    assert momento[2] == pytest.approx(3000.0, rel=1e-6)
    assert momento[:2] == pytest.approx([0.0, 0.0], abs=1e-6)


def test_ogni_cload_apre_il_passo_con_op_new(cube_mesh, tmp_path):
    """Un *CLOAD senza OP=NEW resta attivo nel passo successivo per ccx.

    Misurato eseguendo `ccx` su `docs/fase-6-cantiere/sonda-cload-persiste/`:
    un *CLOAD dichiarato in un passo statico eredita nel passo seguente se
    nessuno lo azzera, e il deck non ha mai scritto ``OP=NEW``. Con due
    posizionati in sequenza (o un carico in sommita' seguito da uno
    posizionato) il secondo passo applicherebbe anche il primo -- il
    contrario di quanto il docstring di `write_inp` dichiara ("ogni carico
    dichiarato e' un passo statico a se'").

    E' piu' debole della verifica di fattibilita' con `ccx` vero
    (`tests/feasibility/test_calculix.py`): guarda solo il testo del deck,
    non cosa il solutore applica davvero, ma gira nella suite ordinaria.

    Mutazione che lo uccide: togliere ``, OP=NEW`` da una qualunque delle
    tre righe ``*CLOAD`` che `write_inp`/`coppia_equivalente` scrivono (il
    ramo del carico in sommita', quello dei posizionati per forza, e
    `coppia_equivalente` per il momento) -- questo deck esercita tutti e tre.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    abaqus.write_inp(
        tmp_path / "deck.inp", nodi, tetraedri,
        node_sets=sets, material=MATERIALE,
        nset_selettori={"piastra": sets["TOP"]},
        carichi=config.CarichiConfig(
            carico_sommita=config.CaricoSommita(risultante=500.0, nset="TOP"),
            posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
                config.CaricoPosizionato(
                    nome="TORSIONE", selettore="piastra",
                    momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
                ),
            ],
        ),
    )
    testo = (tmp_path / "deck.inp").read_text(encoding="ascii")
    righe_cload = [riga for riga in testo.splitlines() if riga.startswith("*CLOAD")]
    assert righe_cload, "nessuna riga *CLOAD trovata: il deck non esercita il codice da coprire"
    assert all(riga == "*CLOAD, OP=NEW" for riga in righe_cload), righe_cload


def test_ogni_dload_apre_il_passo_con_op_new(cube_mesh, tmp_path):
    """Un *DLOAD senza OP=NEW resta attivo nel passo successivo per ccx, come il *CLOAD.

    Misurato in `docs/fase-6-cantiere/sonda-cload-persiste/sonda-dload-ridichiarato.inp`:
    un `*DLOAD` ridichiarato identico (il peso proprio, ripetuto a ogni passo)
    non raddoppia, ma una riga `GRAV` diversa (la spinta orizzontale) dichiarata
    in un passo e mai ripetuta resta attiva in ogni passo statico successivo.
    Con `spinta` e `carico_sommita` insieme -- la combinazione che questa fase
    rende possibile -- il passo `CARICO_TOP` includerebbe silenziosamente anche
    la spinta, senza che il nome del passo lo prometta.

    Mutazione che lo uccide: togliere ``, OP=NEW`` dalla riga ``*DLOAD`` che
    `_passo_statico` apre a ogni passo.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    abaqus.write_inp(
        tmp_path / "deck.inp", nodi, tetraedri,
        node_sets=sets, material=MATERIALE,
        carichi=config.CarichiConfig(
            spinta=config.SpintaOrizzontale(coefficiente=0.1, asse="x"),
            carico_sommita=config.CaricoSommita(risultante=500.0, nset="TOP"),
        ),
    )
    testo = (tmp_path / "deck.inp").read_text(encoding="ascii")
    righe_dload = [riga for riga in testo.splitlines() if riga.startswith("*DLOAD")]
    assert righe_dload, "nessuna riga *DLOAD trovata: il deck non esercita il codice da coprire"
    assert all(riga == "*DLOAD, OP=NEW" for riga in righe_dload), righe_dload


def test_un_braccio_piu_largo_dell_estensione_e_rifiutato(cube_mesh, tmp_path):
    """Il programma contraddice il braccio dichiarato invece di misurarlo da se'.

    La faccia superiore si estende 100 mm: un braccio di 400 non lo
    sostiene, e il rifiuto riporta entrambi i numeri.

    Mutazione che lo uccide: misurare il braccio dall'estensione invece
    di verificarlo. Nessuna eccezione, e un numero che nessuno puo'
    smentire.

    Il `match` cerca il messaggio **specifico** del controllo sull'estensione
    ("si estendono"), non solo "400": con braccio=400 anche il controllo sui
    gruppi vuoti solleva un `ValueError` che nomina "400" per caso (e' il
    braccio nel suo stesso messaggio), e un `match="400"` da solo passerebbe
    pure disattivando il controllo giusto e lasciando scattare quello sbagliato.
    """
    with pytest.raises(ValueError, match=r"braccio di 400 mm.*si estendono"):
        _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
            config.CaricoPosizionato(
                nome="TORSIONE", selettore="piastra",
                momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=100.0, braccio=400.0),
            ),
        ])


def test_il_rifiuto_del_braccio_riporta_anche_la_misura(cube_mesh, tmp_path):
    """Il rifiuto porta due numeri, non uno: dichiarato *e* misurato.

    Riga del contratto scoperta durante il task, non coperta dal test dato
    dal brief (che cerca solo "400" nel messaggio): un messaggio che
    tacesse il numero misurato lascerebbe l'operatore a indovinare quanto i
    nodi presi si estendono davvero.

    Mutazione che lo uccide: comporre il messaggio senza il valore di
    `estensione`. Il pattern sul numero misurato smette di trovare riscontro.
    """
    with pytest.raises(ValueError) as errore:
        _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
            config.CaricoPosizionato(
                nome="TORSIONE", selettore="piastra",
                momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=100.0, braccio=400.0),
            ),
        ])
    messaggio = str(errore.value)
    assert "400" in messaggio
    misurato = re.search(r"estendono ([\d.]+) mm", messaggio)
    assert misurato is not None, f"nessun numero misurato nel messaggio: {messaggio!r}"
    assert float(misurato.group(1)) < 400.0


def test_il_resoconto_del_momento_dice_dichiarato_ed_effettivo(cube_mesh, tmp_path):
    """Braccio dichiarato e braccio effettivo sono due numeri diversi, ed entrambi si mostrano.

    I gruppi si formano oltre +-braccio/2, quindi i loro baricentri
    pesati distano piu' del braccio dichiarato: e' lecito, ed e'
    esattamente la cosa che il resoconto esiste per far vedere.

    Mutazione che lo uccide: invertire l'ordine dei due baricentri nel
    calcolo del braccio effettivo (`bracci[1] - bracci[0]` invece di
    `bracci[0] - bracci[1]`). Il braccio effettivo diventa negativo e
    l'assert `>= braccio_dichiarato` cade: e' un errore di segno reale, non
    inventato.

    Non "scrivere braccio_effettivo uguale a braccio_dichiarato": il
    contratto vuole `>=`, non `>`, e l'uguaglianza e' legittima quando i due
    gruppi cadono esattamente su `+-braccio/2` -- quella mutazione non e'
    distinguibile dal comportamento corretto sotto questo oracolo, e non
    uccide il test.
    """
    _, resoconto = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(
            nome="TORSIONE", selettore="piastra",
            momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        ),
    ])
    voce = resoconto["TORSIONE"]
    assert voce["braccio_dichiarato"] == pytest.approx(60.0)
    assert voce["braccio_effettivo"] >= 60.0
    assert voce["momento_dichiarato"] == pytest.approx([0.0, 0.0, 3000.0])
    assert voce["nodi_positivi"] > 0 and voce["nodi_negativi"] > 0


def test_un_braccio_che_lascia_un_lato_senza_nodi_e_rifiutato():
    """Una coppia con una forza sola e' una forza: il lato vuoto si rifiuta.

    Riga del contratto non coperta da alcun test del brief. Punti disposti
    in modo asimmetrico attorno al proprio baricentro: un braccio che sta
    dentro l'estensione totale (15 mm) puo' comunque lasciare vuoto un
    lato, perche' l'estensione e' definita dagli estremi e non dalla loro
    distribuzione.

    Mutazione che lo uccide: togliere il controllo sui gruppi vuoti, o
    confondere `>=`/`<=` con `>`/`<` nelle soglie. Il ValueError smette di
    sollevarsi.
    """
    nodi = np.array([
        [-10.0, 0.0, 0.0],
        [-9.0, 0.0, 0.0],
        [-8.0, 0.0, 0.0],
        [5.0, 0.0, 0.0],
    ])
    indici = np.arange(4)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=100.0, braccio=14.0)
    with pytest.raises(ValueError, match="lato"):
        abaqus.coppia_equivalente(
            momento, nodi, np.zeros((0, 4), dtype=np.int64), indici, "C3D4", nome="TEST",
        )


def test_la_direzione_di_separazione_usa_fix_sign_non_il_segno_grezzo_della_svd(cube_mesh):
    """Il segno di `s` viene da `fix_sign`, non da quello arbitrario della SVD.

    Riga del contratto non coperta da alcun test del brief. Si forza la SVD
    a rendere il primo versore col segno capovolto rispetto a quello
    "vero": se il codice applica `fix_sign`, il risultato non cambia,
    perche' la convenzione lo riporta allo stesso segno; se usasse il segno
    grezzo, gruppo positivo e negativo si scambierebbero e il deck sarebbe
    diverso.

    Mutazione che lo uccide: togliere la chiamata a `fix_sign` sul
    risultato della SVD.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    indici = sets["TOP"]
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)

    righe_normali, resoconto_normale = abaqus.coppia_equivalente(
        momento, nodi, tetraedri, indici, "C3D4", nome="TORSIONE"
    )

    svd_reale = np.linalg.svd

    def svd_col_segno_capovolto(matrice, full_matrices=False):
        u, s, vh = svd_reale(matrice, full_matrices=full_matrices)
        vh = vh.copy()
        vh[0] = -vh[0]
        return u, s, vh

    abaqus.np.linalg.svd = svd_col_segno_capovolto
    try:
        righe_capovolte, resoconto_capovolto = abaqus.coppia_equivalente(
            momento, nodi, tetraedri, indici, "C3D4", nome="TORSIONE"
        )
    finally:
        abaqus.np.linalg.svd = svd_reale

    assert righe_capovolte == righe_normali
    assert resoconto_capovolto == resoconto_normale


def test_posizionati_vuoto_o_assente_lascia_il_deck_identico(cube_mesh, tmp_path):
    """Blocco `posizionati` assente o vuoto: il deck non cambia di una riga.

    Riga del contratto scoperta dal brief: l'invarianza della suite
    preesistente prova che nulla si e' rotto aggiungendo i due parametri, non
    che *questa* condizione regge -- sono due cose diverse, e la seconda non
    aveva una guardia sua.

    Mutazione che lo uccide: scrivere comunque un *NSET (anche vuoto) quando
    `nset_selettori` e' un dizionario vuoto, invece di trattarlo come
    l'assenza del parametro. La corsa con `nset_selettori={}` guadagnerebbe
    una riga che quella senza il parametro non ha.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    percorso_assente = tmp_path / "assente.inp"
    abaqus.write_inp(percorso_assente, nodi, tetraedri, node_sets=sets, material=MATERIALE)
    percorso_vuoto = tmp_path / "vuoto.inp"
    abaqus.write_inp(
        percorso_vuoto, nodi, tetraedri, node_sets=sets, material=MATERIALE,
        nset_selettori={}, carichi=config.CarichiConfig(posizionati=()),
    )
    assert percorso_assente.read_text(encoding="ascii") == percorso_vuoto.read_text(encoding="ascii")


def test_un_selettore_volumetrico_con_estensione_sull_asse_e_rifiutato(cube_mesh):
    """Un pezzo di solido che sconfina lungo l'asse scrive un momento anche fuori asse: si rifiuta.

    Riga del contratto segnalata dal coordinatore dopo la review: i due
    gruppi di uno spigolo del banco (x<=20, z<=100) non stanno alla stessa
    quota lungo l'asse z del momento, quindi la coppia realizzerebbe una
    componente y spuria di 2500 N*mm su un momento z dichiarato di 3000 --
    misurato a mano prima di scrivere il test: rapporto fuori-asse 0.833,
    oltre 16 volte sopra `TOLLERANZA_MOMENTO_FUORI_ASSE`.

    Mutazione che lo uccide: togliere il controllo sul rapporto fuori asse.
    Verificato che senza il controllo la chiamata **non solleva affatto**
    (ritorna righe e resoconto), non che sollevi un errore diverso per
    caso -- e' la stessa classe di difetto gia' trovata su questo task.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero((nodi[:, 0] <= 20.0) & (nodi[:, 2] <= 100.0))
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=30.0)
    with pytest.raises(ValueError, match="componente fuori dall'asse"):
        abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")


def test_un_selettore_planare_non_solleva_e_realizza_il_momento_in_asse(cube_mesh):
    """Un selettore che giace nel piano perpendicolare all'asse passa il controllo nuovo.

    TOP e' perpendicolare all'asse z del momento per costruzione: il
    rapporto fuori asse e' zero, ben sotto la tolleranza, e
    `momento_effettivo` combacia con `modulo * asse`.

    Mutazione che lo uccide: capovolgere il verso del controllo
    (`rapporto_fuori_asse < TOLLERANZA_MOMENTO_FUORI_ASSE` invece di `>`).
    Un controllo capovolto solleva proprio sul caso planare, che e' quello
    che deve passare.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, resoconto = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    assert resoconto["momento_effettivo"] == pytest.approx([0.0, 0.0, 3000.0], abs=1e-6)


def test_il_momento_effettivo_del_resoconto_e_coerente_con_le_forze_scritte(cube_mesh):
    """`momento_effettivo` non e' un secondo calcolo scollegato dalle righe *CLOAD.

    Si ricostruisce il momento dalle forze nodali effettivamente scritte in
    `righe` (non da `forza`/`quote` intermedi) e si confronta col valore nel
    resoconto: devono coincidere, perche' sono la stessa fisica letta in due
    punti diversi del programma.

    Mutazione che lo uccide: nel calcolo di `momento_effettivo`, dimenticare
    `segno *` sulle forze del lato negativo. Il resoconto continuerebbe a
    dichiarare un momento che le righe *CLOAD non realizzano davvero.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    righe, resoconto = abaqus.coppia_equivalente(
        momento, nodi, tetraedri, indici, "C3D4", nome="TEST"
    )
    forze = {}
    for riga in righe[1:]:
        nodo, grado, valore = riga.split(", ")
        forze.setdefault(int(nodo) - 1, [0.0, 0.0, 0.0])[int(grado) - 1] = float(valore)
    baricentro = nodi[indici].mean(axis=0)
    ricostruito = np.zeros(3)
    for nodo, forza_nodo in forze.items():
        ricostruito += np.cross(nodi[nodo] - baricentro, forza_nodo)
    assert ricostruito == pytest.approx(resoconto["momento_effettivo"], abs=1e-6)


def test_una_superficie_leggermente_irregolare_non_solleva(cube_mesh):
    """Un piccolo sbilanciamento lungo l'asse, come su una superficie as-built vera, non si rifiuta.

    TOP e' un piano perfetto per costruzione in questo banco sintetico
    (rapporto fuori-asse 0.0 esatto, verificato in Round 3): nessun test lo
    copriva per una superficie leggermente irregolare come quella reale, ed
    e' esattamente il caso che la prima soglia di questo task (1e-6) avrebbe
    rifiutato. Si sposta di 0.3 mm lungo z un solo nodo del gruppo positivo
    su un braccio di 60 mm: rapporto fuori-asse ~1e-3, lo stesso ordine di
    grandezza misurato sulla mesh reale (`runs/lab_telaio_v2`, vedi report),
    comodamente sotto `TOLLERANZA_MOMENTO_FUORI_ASSE` (5e-2, media geometrica
    dei due estremi misurati -- Round 5).

    Mutazione che lo uccide: abbassare `TOLLERANZA_MOMENTO_FUORI_ASSE` a
    1e-6 (il primo valore scelto per questa soglia, gia' scartato in Round 4
    perche' rifiutava il caso studio vero). Il rapporto ~1e-3 supera quella
    soglia e la chiamata solleva a torto.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    nodi_irregolari = nodi.copy()
    nodi_irregolari[indici[1], 2] += 0.3  # una superficie as-built non e' mai perfettamente piana
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, resoconto = abaqus.coppia_equivalente(
        momento, nodi_irregolari, tetraedri, indici, "C3D4", nome="TEST"
    )
    eff = np.array(resoconto["momento_effettivo"])
    assert abs(eff[0]) < 3000.0 * abaqus.TOLLERANZA_MOMENTO_FUORI_ASSE
    assert abs(eff[1]) < 3000.0 * abaqus.TOLLERANZA_MOMENTO_FUORI_ASSE
    assert eff[2] == pytest.approx(3000.0, rel=1e-3)


def test_il_momento_riporta_i_nodi_ad_area_nulla(cube_mesh_fine):
    """Il resoconto di `ripartisci` non si butta: il momento lo rende come CARICO_TOP.

    `coppia_equivalente` scartava il secondo valore di `ripartisci`
    (`quote_totale, _ =`), e un momento su un selettore con nodi ad area
    tributaria nulla non li contava ne' li riportava. Per CARICO_TOP quel
    campo esiste dalla Fase 5: e' la stessa correzione, regredita su un
    secondo percorso.

    L'oracolo e' **uno, non zero**. La prima stesura di questo test prendeva
    la sola faccia superiore, dove nessun nodo ha area nulla, e la sua
    docstring lo ammetteva: un `"nodi_ad_area_nulla": 0` costante lo lasciava
    verde. Qui il selettore e' la faccia superiore piu' un nodo che sta sotto
    di essa: quel nodo non ha alcuna faccia di bordo con tutti i propri nodi
    nell'insieme, quindi la sua area tributaria e' zero e il conteggio vale 1
    mentre gli altri sei stanno sulla faccia.

    Mutazione che lo uccide: scrivere `"nodi_ad_area_nulla": 0` invece di
    prenderlo da `resoconto_aree`.
    """
    nodi, tetraedri = cube_mesh_fine
    indici = _sommita_piu_il_nodo(nodi, (0.0, SIZE[1], SIZE[2] / 2.0))
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, resoconto = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    assert resoconto["nodi"] == 7
    assert resoconto["nodi_ad_area_nulla"] == 1


def test_il_momento_riporta_l_area_su_cui_ha_ripartito(cube_mesh_fine):
    """`area_totale` esce dal momento come esce dalla forza, o i due non si confrontano.

    Il commit `4d37579` ha recuperato `nodi_ad_area_nulla` dal resoconto di
    `ripartisci` e ha lasciato cadere `area_totale`, che il percorso della
    forza pubblica: nella corsa dimostrativa PRESSA porta l'area caricata e
    TORSIONE no, e chi legge lo stesso `metrics.json` non ha l'area del
    momento accanto a quella della forza.

    L'oracolo e' geometrico: l'unica faccia di bordo con tutti i nodi
    nell'insieme e' la faccia superiore del banco, 100 x 40 mm. Il nodo in
    piu' non ne aggiunge, ed e' proprio perche' non ne aggiunge che ha area
    nulla.

    Mutazione che lo uccide: togliere la chiave `area_totale` dal resoconto
    di `coppia_equivalente`. `KeyError` al posto del numero.
    """
    nodi, tetraedri = cube_mesh_fine
    indici = _sommita_piu_il_nodo(nodi, (0.0, SIZE[1], SIZE[2] / 2.0))
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, resoconto = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    assert resoconto["area_totale"] == pytest.approx(SIZE[0] * SIZE[1], rel=1e-12)


def test_il_momento_scrive_anche_le_righe_dei_nodi_ad_area_nulla(cube_mesh_fine):
    """Un nodo a quota nulla porta la sua riga `*CLOAD` a zero, e ci resta.

    `_gradi_da_scrivere` filtra le componenti della **direzione**, uguali per
    tutti i nodi, non il valore scritto `quota * componente`: un nodo ad area
    tributaria nulla ha quota zero e la sua riga finisce nel deck a
    `-0.000000000e+00`. Non e' un difetto da correggere qui.
    `docs/fase-6-carichi.md` § 4 pubblica una tabella con 3.036 righe
    `*CLOAD` per `CARICO_TOP`, di cui 703 a zero, e la corsa che la sostiene
    sta in `runs/`, in sola lettura: filtrare le righe mute porterebbe quel
    conteggio a 2.333 e invaliderebbe una tabella gia' pubblicata.

    Questo test esiste perche' quel comportamento non lo teneva nessuno:
    filtrare le righe a valore zero in entrambi gli scrittori lasciava la
    suite verde. Chi lo togliesse non saprebbe che il documento conta quelle
    righe.

    Attenzione allo zero **negativo**: un confronto sulla stringa
    `"0.000000000e+00"` non lo vede, `float(...) == 0.0` si'.

    Mutazione che lo uccide: filtrare le righe a valore zero nello scrittore
    di `coppia_equivalente`. Le due righe mute spariscono e ne restano otto.
    """
    nodi, tetraedri = cube_mesh_fine
    indici = _sommita_piu_il_nodo(nodi, (0.0, SIZE[1], SIZE[2] / 2.0))
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    righe, _ = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    valori = [float(riga.split(",")[2]) for riga in righe[1:]]
    assert len(valori) == 10
    assert [v for v in valori if v == 0.0] == [0.0, 0.0]


def test_il_momento_riporta_il_rapporto_dei_valori_singolari(cube_mesh, recwarn):
    """Quanto la direzione della coppia sia determinata si legge nel resoconto, e passa.

    `separazione` e' il primo vettore singolare di `piano`: ben definito
    quando il primo valore singolare domina il secondo, arbitrario quando i
    due pareggiano. Il rapporto fra i due e' la misura di quel margine, e
    finora stava solo in una nota di `docs/fase-6-carichi.md`: adesso esce
    accanto a `momento_effettivo`, cosi' il numero si vede su ogni corsa.

    La faccia superiore del banco misura 100 x 40 mm e i nodi presi sono i
    suoi quattro vertici: i due semiassi stanno come 40 sta a 100, quindi
    il rapporto vale 0,4 esatto -- oracolo geometrico, non un numero
    ricopiato dal programma.

    **La soglia non deve rifiutare una piastra con un asse maggiore vero.**
    E' il vincolo che ha tenuto aperta questa guardia per una tornata: la
    ricetta della media geometrica dei due estremi la piazzava a 0,310, e
    questo stesso banco -- rapporto 0,400 -- ci finiva sopra. Quella piastra
    sta 2,5 : 1 e la sua direzione e' stabile: tolto un nodo ruota di 0,49
    gradi nel caso peggiore. Una soglia che la segnala segnalerebbe
    geometrie sane, e un avviso che parte sempre non lo legge piu' nessuno.
    Il secondo `assert` sta qui e non in un test a parte perche' il primo era
    gia' la sua fixture, la sua chiamata e la sua prima asserzione, parola
    per parola.

    Mutazione che uccide la prima asserzione: rendere `valori[0] / valori[1]`
    invece di `valori[1] / valori[0]`. Il rapporto diventa 2,5.

    Mutazione che uccide la seconda: portare
    `SOGLIA_PAREGGIO_VALORI_SINGOLARI` a 0,31, la media geometrica. L'avviso
    parte sul banco.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, resoconto = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    assert resoconto["rapporto_valori_singolari"] == pytest.approx(SIZE[1] / SIZE[0], abs=1e-9)
    assert [w for w in recwarn if issubclass(w.category, abaqus.SelettoreIsotropoWarning)] == []


def test_un_selettore_quadrato_avvisa_che_la_direzione_non_e_determinata():
    """Su una faccia quadrata la coppia cade su un diametro qualsiasi.

    `separazione` e' il primo vettore singolare del piano: quando i due
    valori singolari pareggiano non c'e' un primo, e a scegliere resta il
    rumore dell'algoritmo. Il momento attorno all'asse non ne risente --
    la forza si calibra sul braccio effettivo, qualunque diametro esca --
    ma su quale diametro cada puo' cambiare fra un rimaglio e l'altro, e
    fra due macchine. Il deck si scrive lo stesso: e' un avviso, perche'
    applicare un momento a una piastra quadrata resta legittimo.

    La faccia superiore misura 100 x 100 mm: i due semiassi pareggiano e
    il rapporto vale 1 esatto -- oracolo geometrico, non un numero
    ricopiato dal programma.

    Mutazione che lo uccide: alzare `SOGLIA_PAREGGIO_VALORI_SINGOLARI`
    sopra 1. Nessun selettore la supera piu', l'avviso non parte mai.
    """
    vertici, facce = synth.box_mesh((100.0, 100.0, 200.0))
    nodi, tetraedri = volume.tetrahedralize(
        vertici, facce, max_volume=100_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    with pytest.warns(abaqus.SelettoreIsotropoWarning, match="1.000"):
        _, resoconto = abaqus.coppia_equivalente(
            momento, nodi, tetraedri, indici, "C3D4", nome="TEST"
        )
    assert resoconto["rapporto_valori_singolari"] == pytest.approx(1.0, abs=1e-9)


def test_il_resoconto_dei_selettori_si_scrive_sempre(cube_mesh, tmp_path):
    """Fra 1 e tutti i nodi nessuna soglia puo' giudicare: si mostra.

    Mutazione che lo uccide: scrivere il resoconto solo quando un
    selettore prende pochi nodi. La chiave sparisce sul caso normale,
    che e' proprio quello in cui serve guardarla.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
        )},
    )
    voce = metriche["selettori"]["piastra"]
    assert voce["tipo"] == "box"
    assert 0 < voce["nodi"] < len(nodi)
    assert len(voce["bbox"]) == 2


def test_i_posizionati_entrano_nei_casi_di_carico(cube_mesh, tmp_path):
    """Il nome del passo e' l'indirizzo del risultato: deve comparire nell'elenco.

    Mutazione che lo uccide: lasciare `casi_di_carico` alla lista fissa
    dei tre della Fase 5. `solve.risolvi` cercherebbe le chiavi di
    point_data per nomi che l'elenco non dichiara.

    `set_tolerance_factor` ridotto: col predefinito, su questo cubo di sole
    16 nodi, `BASE` copre l'intera altezza (tolleranza 424 mm su 200 mm di
    modello) e "piastra" -- la faccia superiore -- ne sarebbe un sottoinsieme,
    il caso che la guardia sul carico-sul-vincolo rifiuta.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
        )},
        carichi=config.CarichiConfig(posizionati=[
            config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
        ]),
    )
    assert "PRESSA" in metriche["casi_di_carico"]
    assert metriche["carichi_posizionati"]["PRESSA"]["nodi"] > 0
    assert metriche["carichi_posizionati"]["PRESSA"]["forza_effettiva"][2] == pytest.approx(-1200.0)


def test_senza_selettori_il_resoconto_e_vuoto(cube_mesh, tmp_path):
    """Riga del contratto non coperta dai due test sopra: nessun selettore
    dichiarato non e' un errore, ed e' la corsa piu' comune di tutte.

    Mutazione che lo uccide: far sollevare o restituire `None` invece di un
    dizionario vuoto quando `selettori` e' `None`.
    """
    nodi, tetraedri = cube_mesh
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
    )
    assert metriche["selettori"] == {}
    assert metriche["carichi_posizionati"] == {}


def test_i_posizionati_stanno_fra_carico_top_e_modale(cube_mesh, tmp_path):
    """L'ordine e' un contratto con `solve.risolvi`, che mappa i risultati per
    posizione: i posizionati vanno dopo CARICO_TOP e prima di MODALE, non solo
    "da qualche parte" nell'elenco.

    Mutazione che lo uccide: mettere i posizionati prima di CARICO_TOP (o
    dopo MODALE) nella tupla di `casi_di_carico`. L'ordine degli indici
    smette di rispettare la doppia disuguaglianza.

    `set_tolerance_factor` ridotto per lo stesso motivo del test sopra: col
    predefinito "piastra" sarebbe un sottoinsieme di `BASE` su questo cubo
    di sole 16 nodi.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
        )},
        carichi=config.CarichiConfig(
            carico_sommita=config.CaricoSommita(risultante=1000.0, nset="TOP"),
            posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
            ],
            modale=config.Modale(modi=3),
        ),
    )
    casi = metriche["casi_di_carico"]
    assert casi.index("CARICO_TOP") < casi.index("PRESSA") < casi.index("MODALE")


def test_un_carico_su_tutto_il_vincolo_solleva(cube_mesh, tmp_path):
    """Un carico i cui nodi sono tutti dentro il set vincolato non sposta nulla.

    La corsa dimostrativa della Fase 6 aveva il momento su BASE per errore
    di configurazione, e nulla se ne accorgeva: la forza finiva tutta in
    reazione, spostamenti e tensioni plausibili, zero avvisi da `ccx`.

    Col predefinito di `set_tolerance_factor` su questo cubo di sole 16
    nodi, `BASE` copre l'intera altezza (vedi i due test sopra): qualunque
    selettore non vuoto ne e' un sottoinsieme, ed e' esattamente il caso
    da rifiutare.

    Mutazione che lo uccide: confrontare `indici_carico` con `vincolati`
    usando `==` invece di `<=`, o non sollevare affatto quando l'insieme
    coincide.

    Il `match` e' sulla frase che identifica **questo** controllo, non sul
    solo nome 'BASE': col nome soltanto passava anche l'errore del set
    vincolato vuoto (bastava una tolleranza negativa a produrlo), cioe' un
    guasto diverso da quello che il test dichiara di coprire.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    with pytest.raises(ValueError, match="coincide per intero con l'insieme vincolato"):
        abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
            selettori={"piastra": config.SelettoreBox(
                tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
            )},
            carichi=config.CarichiConfig(posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
            ]),
        )


def test_un_carico_che_interseca_in_parte_il_vincolo_avvisa(griglia_mesh, tmp_path):
    """Un carico che include solo alcuni nodi del vincolo non e' rifiutato,
    ma l'operatore deve saperlo: quella quota finisce in reazione lo stesso.

    Il selettore prende i due strati piu' bassi (z <= 60 mm): sul maglio
    a griglia sono 8 nodi, di cui i 4 a z = 0 coincidono col vincolo. E' l'unico dei due
    controlli dove il carico resta valido -- il conteggio nell'avviso e'
    quello che permette all'operatore di giudicare se e' voluto.

    Mutazione che lo uccide: alzare l'avviso anche a intersezione vuota (il
    caso normale, che rumorerebbe ogni corsa), o non emetterlo affatto
    quando l'intersezione e' parziale.
    """
    nodi, tetraedri = griglia_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    with pytest.warns(abaqus.CaricoSulVincoloWarning, match="4 dei suoi 8"):
        abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
            selettori={"bordo_basso": config.SelettoreBox(
                tipo="box", min=(-1e9, -1e9, -1e9), max=(1e9, 1e9, 60.0)
            )},
            carichi=config.CarichiConfig(posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="bordo_basso", forza=(0.0, 0.0, -1200.0)),
            ]),
        )


def test_carico_sommita_su_tutto_il_vincolo_solleva(cube_mesh, tmp_path):
    """La guardia scorreva solo `carichi.posizionati`: `carico_sommita` non
    passava mai dal confronto col set vincolato.

    Col predefinito di `set_tolerance_factor` (vedi il test gemello sui
    posizionati) `BASE` copre l'intera altezza di questo cubo di 16 nodi:
    qualunque `carico_sommita.nset`, `BASE` compreso, ne e' un sottoinsieme
    completo.

    Mutazione che lo uccide: costruire l'elenco da controllare dal solo
    `carichi.posizionati`, senza includere `carico_sommita`.
    """
    nodi, tetraedri = cube_mesh
    with pytest.raises(ValueError, match=r"CARICO_TOP.*'BASE'"):
        abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
            carichi=config.CarichiConfig(
                carico_sommita=config.CaricoSommita(risultante=1000.0, nset="BASE"),
            ),
        )


def test_carico_sommita_che_interseca_in_parte_il_vincolo_avvisa(griglia_mesh, tmp_path):
    """Stesso controllo del test gemello sui posizionati, applicato a
    `carico_sommita`: a `set_tolerance_factor=0.5` `SIDE_LEFT` e `BASE`
    condividono solo l'angolo basso (2 nodi su 10 sul maglio a griglia), ne'
    l'uno sottoinsieme dell'altro.

    **Il conteggio deve anche uscire nel resoconto.** L'avviso va su stderr e
    si perde con la finestra del terminale; il § 7 di
    `docs/fase-6-carichi.md` promette `nodi_sul_vincolo` su **ogni** carico,
    e `CARICO_TOP` e' quello che rischia di restarne fuori perche' cita un
    `*NSET` per nome invece di un selettore risolto.

    Mutazione che uccide l'avviso: escludere `carico_sommita` dall'elenco
    controllato.

    Mutazione che uccide il resoconto: filtrare il ciclo che scrive
    `nodi_sul_vincolo` su `nome != "CARICO_TOP"`. La chiave sparisce e
    l'avviso resta.
    """
    nodi, tetraedri = griglia_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    with pytest.warns(abaqus.CaricoSulVincoloWarning, match=r"CARICO_TOP.*2 dei suoi 10.*'BASE'"):
        metriche = abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
            carichi=config.CarichiConfig(
                carico_sommita=config.CaricoSommita(risultante=1000.0, nset="SIDE_LEFT"),
            ),
        )
    sommita = metriche["carichi_posizionati"]["CARICO_TOP"]
    assert sommita["nodi"] == 10
    assert sommita["nodi_sul_vincolo"] == 2


def test_un_caso_misto_di_selettore_arriva_al_deck_scritto(cube_mesh, tmp_path):
    """Il selettore dichiarato 'piastra' e citato 'Piastra' arrivano fino al
    deck, non solo alla validazione della configurazione.

    Riproduce il difetto misurato in produzione: `PipelineConfig` accettava
    gia' il caso misto, ma `write_inp` sollevava comunque con un messaggio
    che negava una dichiarazione vera ("non e' stato risolto"). Passa per
    la `PipelineConfig` completa apposta, perche' e' li' che la
    normalizzazione al nome canonico avviene (`core/config.py`).

    Mutazione che lo uccide: normalizzare `carico.selettore` dentro
    `abaqus.write_inp` invece che nel validatore di `PipelineConfig`. Il
    selettore arriverebbe qui gia' 'Piastra' e la scrittura del deck
    solleverebbe di nuovo.
    """
    nodi, tetraedri = cube_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    cfg = config.PipelineConfig(
        input=config.InputConfig(path="nuvola.ply"),
        analysis=analisi,
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, float(nodi[:, 2].max()) - 1.0), max=(1e9, 1e9, 1e9)
        )},
        carichi=config.CarichiConfig(posizionati=[
            config.CaricoPosizionato(nome="PRESSA", selettore="Piastra", forza=(0.0, 0.0, -1.0)),
        ]),
    )
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri,
        cfg.analysis, TET_LINEARE, carichi=cfg.carichi, selettori=cfg.selettori,
    )
    testo = (tmp_path / "m.inp").read_text(encoding="ascii")
    assert "*NSET, NSET=piastra" in testo.splitlines()
    assert metriche["carichi_posizionati"]["PRESSA"]["nodi"] > 0


def test_il_carico_in_sommita_da_solo_riporta_i_nodi_ad_area_nulla(cube_mesh, tmp_path):
    """Il resoconto di CARICO_TOP non e' buttato: entra in `metrics.json`
    anche quando e' l'unico carico dichiarato, senza alcun posizionato.

    Prima della correzione, `write_inp` scartava il resoconto di
    `ripartisci` per CARICO_TOP (`quote, _ = ripartisci(...)`):
    `nodi_ad_area_nulla` -- il numero attorno a cui ruota meta' del
    documento della Fase 5 -- non arrivava mai in `metrics.json`.

    Mutazione che lo uccide: continuare a scartare il resoconto di
    CARICO_TOP invece di aggiungerlo al dizionario che la funzione rende.
    La chiave 'CARICO_TOP' sparirebbe da `metriche["carichi_posizionati"]`.

    `set_tolerance_factor` ridotto per lo stesso motivo degli altri test
    di questo file: col predefinito `TOP` e `BASE` collassano nello stesso
    insieme su questo cubo di 16 nodi, e la guardia carico-sul-vincolo
    (punto 1) rifiuterebbe un CARICO_TOP che qui non c'entra.
    """
    nodi, tetraedri = cube_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
        carichi=config.CarichiConfig(
            carico_sommita=config.CaricoSommita(risultante=1000.0, nset="TOP"),
        ),
    )
    top = metriche["carichi_posizionati"]["CARICO_TOP"]
    assert "nodi_ad_area_nulla" in top
    assert top["nodi"] > 0


def test_un_selettore_degenere_non_viene_inghiottito(cube_mesh, tmp_path):
    """L'eccezione di `core/selezione.py` deve arrivare intatta fino al
    chiamante: un `try` qui la trasformerebbe in un deck silenziosamente
    sbagliato. Una sfera lontanissima dalla mesh non prende nessun nodo, in
    qualunque sistema di riferimento la mesh venga allineata.

    Mutazione che lo uccide: avvolgere `selezione.risolvi_tutti` in un
    `try/except` che assorbe l'errore. La chiamata tornerebbe metriche
    invece di sollevare.
    """
    nodi, tetraedri = cube_mesh
    with pytest.raises(ValueError, match="zero nodi"):
        abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
            selettori={"vuoto": config.SelettoreSfera(
                tipo="sfera", centro=(1e6, 1e6, 1e6), raggio=1.0
            )},
        )


def _con_box(tmp_path, cube_mesh, minimo, massimo, nome="PIEDE"):
    """Un deck col solo carico posizionato su una box in coordinate allineate.

    Il banco allineato sta in x [0, 40], y [0, 100], z [0, 200] e ha nodi
    solo alle quote 0, 50, 100, 150 e 200: le box dei due test qui sotto
    sono scelte su quelle quote. `set_tolerance_factor` ridotto perche' col
    predefinito BASE inghiotte l'intero cubo di 16 nodi.
    """
    nodi, tetraedri = cube_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    return abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
        selettori={"fascia": config.SelettoreBox(tipo="box", min=minimo, max=massimo)},
        carichi=config.CarichiConfig(posizionati=[
            config.CaricoPosizionato(nome=nome, selettore="fascia", forza=(0.0, 0.0, -1200.0)),
        ]),
    )


def test_i_nodi_bloccati_dal_vincolo_arrivano_nel_resoconto(griglia_mesh, tmp_path):
    """L'avviso va su stderr, il numero deve andare in `metrics.json`.

    Un selettore a cavallo del vincolo non fa sollevare la guardia
    (l'inclusione totale e' falsa), stampa un avviso e la corsa prosegue:
    il terminale si chiude, il file resta, e `forza_effettiva` dichiara la
    risultante intera mentre il modello ne applica una frazione. Il
    conteggio era gia' calcolato per comporre la stringa dell'avviso: qui
    si pretende che finisca anche nel resoconto.

    La box prende le tre quote basse (12 nodi sul maglio a griglia), di cui
    i 4 a z = 0 sono l'insieme vincolato.

    Mutazione che lo uccide: lasciare il conteggio dentro il solo
    `warnings.warn`. La chiave sparisce e resta l'avviso.
    """
    with pytest.warns(abaqus.CaricoSulVincoloWarning):
        metriche = _con_box(tmp_path, griglia_mesh, (-1.0, -1.0, -1.0), (1e9, 1e9, 100.0))
    piede = metriche["carichi_posizionati"]["PIEDE"]
    assert piede["nodi"] == 12
    assert piede["nodi_sul_vincolo"] == 4


def test_un_carico_lontano_dal_vincolo_conta_zero_nodi_bloccati(cube_mesh, tmp_path):
    """Zero nodi bloccati e' un numero da scrivere, non una chiave da omettere.

    Chi legge `metrics.json` non puo' distinguere "nessun nodo sul
    vincolo" da "questa versione non lo contava" se la chiave compare solo
    quando l'intersezione non e' vuota.

    Mutazione che lo uccide: scrivere la chiave solo per i carichi che
    hanno almeno un nodo bloccato, cioe' calcolarla dopo il `continue`.
    """
    metriche = _con_box(tmp_path, cube_mesh, (-1.0, -1.0, 150.0), (1e9, 1e9, 1e9), nome="TESTA")
    testa = metriche["carichi_posizionati"]["TESTA"]
    assert testa["nodi"] == 6
    assert testa["nodi_sul_vincolo"] == 0


def test_una_forza_scrive_la_riga_del_nodo_ad_area_nulla(cube_mesh, tmp_path):
    """Anche sul percorso della forza la riga muta resta nel deck.

    Gemello di `test_il_momento_scrive_anche_le_righe_dei_nodi_ad_area_nulla`
    sull'altro scrittore: `_gradi_da_scrivere` filtra le componenti della
    direzione, uguali per tutti i nodi, e la quota del singolo nodo non passa
    di li'. Un selettore che unisca i quattro nodi di `BASE` e **un** nodo di
    `TOP` da' `nodi_ad_area_nulla == 1` -- l'unica faccia intera nell'insieme
    e' quella di base -- e cinque righe `*CLOAD`, l'ultima a zero.

    Il conteggio delle righe e' cio' che `docs/fase-6-carichi.md` § 4
    pubblica per `CARICO_TOP` (3.036, non 2.333) sulla base di una corsa in
    `runs/`, che e' in sola lettura: filtrare le righe mute la smentirebbe.

    Lo zero e' **negativo**: si confronta il `float`, non la stringa.

    Mutazione che lo uccide: filtrare le righe a valore zero nello scrittore
    della forza in `write_inp`. Restano quattro righe su cinque.
    """
    nodi, tetraedri = cube_mesh
    insiemi = _base_and_top(nodi)
    misto = np.concatenate([insiemi["BASE"], insiemi["TOP"][:1]])
    percorso = tmp_path / "m.inp"
    resoconto = abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=insiemi, material=MATERIALE,
        nset_selettori={"misto": misto},
        carichi=config.CarichiConfig(posizionati=[
            config.CaricoPosizionato(nome="PIEDE", selettore="misto", forza=(0.0, 0.0, -1200.0)),
        ]),
    )
    assert resoconto["PIEDE"]["nodi_ad_area_nulla"] == 1
    testo = percorso.read_text(encoding="ascii")
    corpo = testo[testo.index("** NOME PASSO: PIEDE"):].split("*CLOAD, OP=NEW\n")[1]
    righe = list(itertools.takewhile(lambda r: r and not r.startswith("*"), corpo.split("\n")))
    valori = [float(riga.split(",")[2]) for riga in righe]
    assert len(valori) == misto.size == 5
    assert [v for v in valori if v == 0.0] == [0.0]


def test_una_componente_minuscola_ma_vera_scrive_la_sua_riga():
    """La soglia relativa taglia il rumore del prodotto vettoriale, non un dato.

    Entrambi i chiamanti passano un versore, quindi la componente piu' grande
    non scende sotto 1/sqrt(3) e la soglia assoluta sta fra 5,8e-13 e 1e-12:
    e' quattro ordini di grandezza sopra l'arrotondamento di
    `np.cross(asse, separazione)` (~1e-16 relativo) e otto sotto qualunque
    componente che sposti un risultato. Una direzione con una componente a
    8,3e-10 del massimo e' una direzione dichiarata, non rumore, e la sua
    riga si scrive.

    Mutazione che lo uccide: portare `SOGLIA_COMPONENTE_RELATIVA` a 1e-3. La
    seconda componente sparisce e restano due gradi su tre.
    """
    gradi = abaqus._gradi_da_scrivere(np.array([1.0, 8.3e-10, -1.0]))
    assert [g for g, _ in gradi] == [1, 2, 3]


def test_il_filtro_delle_componenti_e_un_confronto_stretto():
    """Una componente esattamente sulla soglia non e' sopra la soglia.

    `abs(c) > soglia`, non `>=`: la soglia e' il confine del rumore e cio'
    che ci sta esattamente sopra e' rumore quanto cio' che ci sta sotto. Il
    caso e' costruibile esatto -- `1e-12 * 1.0` e' `1e-12` in doppia
    precisione -- e non serve cercare una geometria che ci caschi.

    Mutazione che lo uccide: `abs(c) >= soglia`. Il secondo grado torna
    dentro e i gradi diventano due.
    """
    direzione = np.array([1.0, abaqus.SOGLIA_COMPONENTE_RELATIVA, 0.0])
    assert direzione[1] == abaqus.SOGLIA_COMPONENTE_RELATIVA * abs(direzione).max()
    assert [g for g, _ in abaqus._gradi_da_scrivere(direzione)] == [1]


def test_una_direzione_tutta_nulla_non_scrive_alcun_grado():
    """Zero componenti utili sono zero righe, non una divisione per zero.

    La soglia e' relativa alla componente piu' grande: su un vettore nullo
    vale zero, e `abs(c) > 0.0` non passa per nessuna componente. Nessun
    chiamante ci arriva oggi -- `Momento` rifiuta l'asse nullo a validazione
    e `write_inp` normalizza la forza per il suo modulo -- ma la funzione e'
    privata e chi la riusa deve sapere che rende `[]`.

    Mutazione che lo uccide: dividere per `np.abs(direzione).max()` invece di
    moltiplicare, cioe' scrivere la soglia come un rapporto. `ZeroDivisionError`
    o un `nan` che fa passare tutto.
    """
    assert abaqus._gradi_da_scrivere(np.zeros(3)) == []


def test_un_rapporto_esattamente_pari_alla_soglia_non_avvisa(cube_mesh, recwarn, monkeypatch):
    """`rapporto > soglia`, non `>=`: il pareggio con la soglia passa.

    Il caso non esiste in doppia precisione su una geometria vera -- la
    piastra 100 x 80 rende 0,7999999999999997 sul reticolo 12 x 12 del § 5.5
    e 0,8000000000000002 sulla mesh a quattro vertici, due nuvole diverse --
    quindi la soglia si sposta sul rapporto misurato invece di cercare una
    geometria che ci cada sopra.

    Mutazione che lo uccide: `rapporto_singolari >= SOGLIA_PAREGGIO_VALORI_SINGOLARI`.
    L'avviso parte sul pareggio esatto.
    """
    nodi, tetraedri = cube_mesh
    indici = np.flatnonzero(nodi[:, 2] >= nodi[:, 2].max() - 1e-6)
    momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0)
    _, misurato = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    monkeypatch.setattr(
        abaqus, "SOGLIA_PAREGGIO_VALORI_SINGOLARI", misurato["rapporto_valori_singolari"]
    )
    _, resoconto = abaqus.coppia_equivalente(momento, nodi, tetraedri, indici, "C3D4", nome="TEST")
    assert resoconto["rapporto_valori_singolari"] == abaqus.SOGLIA_PAREGGIO_VALORI_SINGOLARI
    assert [w for w in recwarn if issubclass(w.category, abaqus.SelettoreIsotropoWarning)] == []


def test_un_fixed_nset_sconosciuto_nomina_gli_insiemi_disponibili(cube_mesh, tmp_path):
    """Un vincolo scritto male si rifiuta dicendo quali insiemi esistono.

    `export_model` indicizzava `node_sets[cfg.fixed_nset]` direttamente, e
    il controllo con messaggio civile di `write_inp` non veniva mai
    raggiunto: un `fixed_nset` sconosciuto produceva un `KeyError` nudo dopo
    che tutta la mesh era stata costruita.

    Il nome di prova era `base` (minuscolo), e non lo e' piu': dal momento in
    cui `fixed_nset` e' un `NomeSetDiFaccia`, `base` si normalizza a `BASE` a
    validazione e non arriva mai qui. Serviva un nome davvero fuori dai sei,
    ed e' il caso che questo controllo deve coprire: un errore di battitura,
    non una differenza di maiuscole.

    Mutazione che lo uccide: togliere la guardia di `export_model` (quella
    subito dopo `build_node_sets`, non quella di `write_inp`: si arriva prima
    alla prima) e tornare a indicizzare. L'errore torna a essere un
    `KeyError`, che `pytest.raises(ValueError)` non cattura.
    """
    nodi, tetraedri = cube_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, fixed_nset="BASAMENTO")
    with pytest.raises(ValueError, match="SIDE_RIGHT"):
        abaqus.export_model(
            tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
        )


def test_un_fixed_nset_in_minuscolo_arriva_al_deck_senza_sollevare(cube_mesh, tmp_path):
    """`fixed_nset: base` nello YAML non deve morire a mesh gia' costruita.

    Il gemello a monte sta in `tests/test_config.py`
    (`test_fixed_nset_canonicalizza_il_nome_dei_sei`) e guarda il solo campo;
    qui si pretende che la normalizzazione arrivi fino al deck scritto, cioe'
    che il `*BOUNDARY` nomini `BASE` e non `base`. E' lo stesso percorso che
    prima costava una tetraedralizzazione intera per poi sollevare.

    Mutazione che lo uccide: ritipare `AnalysisConfig.fixed_nset` da
    `NomeSetDiFaccia` a `NomeSet`. Torna il `ValueError` di `write_inp`.
    """
    nodi, tetraedri = cube_mesh
    analisi = config.AnalysisConfig(material=MATERIALE, fixed_nset="base")
    assert analisi.fixed_nset == "BASE"
    percorso = tmp_path / "m.inp"
    abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, analisi, TET_LINEARE,
    )
    assert "\nBASE, 1, 3\n" in percorso.read_text(encoding="ascii")
