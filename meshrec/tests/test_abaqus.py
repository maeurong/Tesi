import itertools

import meshio
import numpy as np
import pytest

from meshrec.core import abaqus, config, synth, volume
from meshrec.core.config import Material
from materiale import ANALISI, MATERIALE


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
# nodi, impronta a terra -- su magli lineari, che sono quelli che le sue
# fixture producono. Dal ripristino del
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
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT, NAME=FACCIA_BASSA" in testo
    assert "1, S1" in testo




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


def test_un_elemento_che_cita_un_nodo_inesistente_non_scrive_un_deck(tmp_path):
    """Il gemello del maglio senza elementi, un piano piu' in la' (#124).

    Misurato prima della guardia: `nodes` a zero righe con un elemento
    `[0, 1, 2, 3]` scriveva **406 byte** senza sollevare, e il deck portava un
    `*NODE` senza righe e subito sotto un elemento che cita quattro nodi che
    non esistono. `ccx` lo accetta o lo rifiuta per ragioni sue, e in entrambi
    i casi il programma che l'ha scritto non ha detto nulla.

    I nodi vuoti sono un caso di un invariante piu' largo: **ogni indice di
    elemento deve cadere in `[0, len(nodes))`**. La guardia sta su quello, non
    sul solo caso vuoto -- un maglio con un riferimento pendente in mezzo e'
    lo stesso difetto, e una guardia sul vuoto lo lascerebbe passare.

    Ordine dichiarato fra le guardie: forma, colonne, righe degli elementi,
    poi i nodi. Con elementi E nodi vuoti parlano gli elementi: «non c'e' un
    maglio» viene prima di «gli elementi citano nodi che non ci sono».

    Mutazione che lo uccide: togliere il controllo sui limiti degli indici.
    """
    percorso = tmp_path / "pendente.inp"
    elementi = np.array([[0, 1, 2, 3]], dtype=np.int64)
    base = dict(node_sets={"BASE": np.zeros(0, dtype=np.int64)}, material=MATERIALE, element_type="C3D4")

    # nodi vuoti, elementi no: il caso dell'issue
    with pytest.raises(ValueError, match=r"nod[oi].*non esist") as errore:
        abaqus.write_inp(percorso, np.zeros((0, 3)), elementi, **base)
    assert not percorso.exists(), "il deck non si scrive a meta'"
    assert "3" in str(errore.value), "il messaggio nomina l'indice piu' alto citato"

    # quattro nodi, ma un elemento ne cita un quinto: stesso invariante
    with pytest.raises(ValueError, match=r"nod[oi].*non esist"):
        abaqus.write_inp(percorso, np.zeros((4, 3)), np.array([[0, 1, 2, 4]]), **base)
    assert not percorso.exists()

    # un indice negativo e' fuori dallo stesso intervallo
    with pytest.raises(ValueError, match=r"nod[oi].*non esist"):
        abaqus.write_inp(percorso, np.zeros((4, 3)), np.array([[0, 1, 2, -1]]), **base)
    assert not percorso.exists()

    # elementi E nodi vuoti: parlano gli elementi
    with pytest.raises(ValueError, match="nessun elemento"):
        abaqus.write_inp(percorso, np.zeros((0, 3)), np.zeros((0, 4), dtype=np.int64), **base)
    assert not percorso.exists()


def test_elementi_monodimensionali_danno_un_messaggio_e_non_uno_stack(tmp_path):
    """Difetto minore di #124: `np.zeros((0,))` cadeva su `elements.shape[1]`
    con `IndexError: tuple index out of range` -- uno stack al posto di una
    frase. Nessun chiamante di produzione passa quella forma, ma un errore che
    non nomina la causa e' un errore che tocca leggere nel codice.

    La forma parla per prima: prima delle colonne, che su un array a una
    dimensione non si possono nemmeno contare.

    Mutazione che lo uccide: togliere il controllo su `ndim`.
    """
    percorso = tmp_path / "piatto.inp"
    with pytest.raises(ValueError, match="due dimensioni"):
        abaqus.write_inp(
            percorso, np.zeros((4, 3)), np.zeros((0,), dtype=np.int64),
            node_sets={"BASE": np.zeros(0, dtype=np.int64)},
            material=MATERIALE, element_type="C3D4",
        )
    assert not percorso.exists()


def test_il_tie_risolve_le_superfici_ignorando_le_maiuscole(tmp_path):
    """La guardia di membership del `*TIE` era rimasta al confronto esatto.

    `ccx` risolve i nomi senza distinguere le maiuscole (misurato in
    `docs/fase-6-cantiere/sonda-caso-nomi/`): una superficie dichiarata
    `PELLE` e un `*TIE` che la nomina `pelle` sono lo stesso `*SURFACE` per
    il solutore, e il deck si legge. Il rifiuto diceva invece «non è fra le
    superfici dichiarate», cioè accusava una causa che non c'era.

    Il deck scrive la grafia che il chiamante ha dato, non quella canonica:
    a cambiare è chi viene accettato, non che cosa viene scritto.

    Mutazione che lo uccide: rimettere `s not in superfici`. Solleva e il
    deck non si scrive.
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
    )

    testo = percorso.read_text(encoding="ascii")
    assert "pelle, Cuoio" in testo


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
    parametro assente non e' la stessa cosa di un parametro dichiarato zero."""
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
    stanno nell'insieme dato, senza controllare l'occorrenza), un *TIE
    finirebbe applicato dentro il solido invece che sulla sua pelle."""
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
    chiamante ci arriva oggi -- `write_inp` normalizza la forza per il suo
    modulo -- ma la funzione e' privata e chi la riusa deve sapere che rende
    `[]`.

    Mutazione che lo uccide: dividere per `np.abs(direzione).max()` invece di
    moltiplicare, cioe' scrivere la soglia come un rapporto. `ZeroDivisionError`
    o un `nan` che fa passare tutto.
    """
    assert abaqus._gradi_da_scrivere(np.zeros(3)) == []




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


# --- Le regioni nel deck (#135) --------------------------------------------
#
# `ALL_WALL` non si rinomina e non si toglie (PRODUCT.md lo elenca fra i
# letterali da preservare): resta l'insieme di tutti gli elementi, quello che
# la card *ELEMENT dichiara, e le regioni lo partizionano.


def test_senza_regioni_il_deck_scrive_la_sola_sezione_di_all_wall(tmp_path, cube_mesh):
    """Una corsa senza regioni produce il deck di prima, non uno nuovo.

    E' il vincolo piu' stretto della molteplicita': le ventidue righe dei
    registri sono la provenienza della tabella sperimentale, e un deck diverso
    a parita' di configurazione le renderebbe irriproducibili in silenzio.

    Mutazione che lo uccide: scrivere comunque un *ELSET, o una seconda riga
    *SOLID SECTION, quando `regioni` e' assente.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
    )
    righe = percorso.read_text(encoding="ascii").splitlines()

    assert [r for r in righe if r.startswith("*SOLID SECTION")] == [
        "*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=MURATURA"
    ]
    assert not [r for r in righe if r.startswith("*ELSET")]


def test_ogni_regione_ha_il_suo_elset_e_la_sua_sezione(tmp_path, cube_mesh):
    """Un *ELSET per regione, una *SOLID SECTION per ciascuno, indici 1-based.

    Mutazione che lo uccide: scrivere gli indici degli elementi 0-based, o una
    sola sezione per l'unione delle regioni.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={
            "PILASTRO": (np.array([0, 1, 2]), MATERIALE),
            "TRAVE": (np.arange(3, len(tetraedri)), MATERIALE),
        },
    )
    righe = percorso.read_text(encoding="ascii").splitlines()

    assert "*ELEMENT, TYPE=C3D4, ELSET=ALL_WALL" in righe
    assert righe[righe.index("*ELSET, ELSET=PILASTRO") + 1] == "1, 2, 3"
    assert "*ELSET, ELSET=TRAVE" in righe
    assert [r for r in righe if r.startswith("*SOLID SECTION")] == [
        "*SOLID SECTION, ELSET=PILASTRO, MATERIAL=MURATURA",
        "*SOLID SECTION, ELSET=TRAVE, MATERIAL=MURATURA",
    ]


def test_una_regione_senza_elementi_e_rifiutata(tmp_path, cube_mesh):
    """Un *ELSET vuoto non ferma `ccx`: il modello gira senza quella sezione.

    Mutazione che lo uccide: scrivere la card e lasciarla senza righe.
    """
    nodi, tetraedri = cube_mesh

    with pytest.raises(ValueError, match="non contiene alcun elemento"):
        abaqus.write_inp(
            tmp_path / "model.inp", nodi, tetraedri,
            node_sets=_base_and_top(nodi), material=MATERIALE,
            regioni={"VUOTA": (np.array([], dtype=np.int64), MATERIALE)},
        )


def test_gli_orfani_tengono_la_sezione_di_all_wall(tmp_path, cube_mesh):
    """Un elemento senza regione resta senza materiale: `ccx` non lo accetta.

    Il ripiego e' la sezione su `ALL_WALL` col materiale unico della corsa, e
    sta **prima** delle regioni: chi ha una regione la sovrascrive.

    Mutazione che lo uccide: omettere il ripiego quando qualche elemento resta
    fuori dalle regioni, o scriverlo dopo di esse.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={"PILASTRO": (np.array([0, 1, 2]), MATERIALE)},
    )
    sezioni = [
        r for r in percorso.read_text(encoding="ascii").splitlines()
        if r.startswith("*SOLID SECTION")
    ]

    assert sezioni == [
        "*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=MURATURA",
        "*SOLID SECTION, ELSET=PILASTRO, MATERIAL=MURATURA",
    ]


def test_senza_orfani_il_ripiego_non_si_scrive(tmp_path, cube_mesh):
    """Nessun elemento fuori dalle regioni: nessuna sezione su `ALL_WALL`.

    Mutazione che lo uccide: scrivere il ripiego sempre, che lascerebbe nel
    deck una sezione che non attribuisce niente a nessuno.
    """
    nodi, tetraedri = cube_mesh
    meta = len(tetraedri) // 2
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={
            "PILASTRO": (np.arange(meta), MATERIALE),
            "TRAVE": (np.arange(meta, len(tetraedri)), MATERIALE),
        },
    )
    testo = percorso.read_text(encoding="ascii")

    assert "*SOLID SECTION, ELSET=ALL_WALL" not in testo
    assert testo.count("*SOLID SECTION") == 2


def test_export_model_porta_le_regioni_fino_al_deck(tmp_path, cube_mesh):
    """Le regioni si misurano fuori di qui e arrivano al deck da questo passaggio.

    Gli indici degli elementi non cambiano con `align_to_axes`, che sposta le
    coordinate e non l'ordine: e' per questo che l'attribuzione puo' essere
    misurata sui nodi non allineati che la pipeline ha in mano, e arrivare qui
    come soli indici.

    Mutazione che lo uccide: accettare `regioni` e non passarlo a `write_inp`.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "m.inp"

    abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
        regioni={"PILASTRO": (np.arange(len(tetraedri)), MATERIALE)},
    )
    testo = percorso.read_text(encoding="ascii")

    assert "*ELSET, ELSET=PILASTRO" in testo
    assert "*SOLID SECTION, ELSET=PILASTRO, MATERIAL=MURATURA" in testo


# --- Un materiale per regione (#135) ---------------------------------------
#
# Il continuo del modello solido e' il calcestruzzo confinato, e la scelta e'
# una limitazione dichiarata: un tetraedro non ha fibre, quindi il deck non
# rappresenta la distinzione fra nucleo e copriferro. Chi legge il deck fra sei
# mesi lo deve trovare scritto, o credera' che la distinzione ci sia.

CLS_C25 = config.Material(name="CLS_C25", young=31476.0, poisson=0.2, density=2.5e-9)
CLS_C30 = config.Material(name="CLS_C30", young=32837.0, poisson=0.2, density=2.5e-9)


def test_ogni_regione_scrive_il_proprio_materiale(tmp_path, cube_mesh):
    """Due regioni di classe diversa, due *MATERIAL, due sezioni che li citano.

    E' la molteplicita' vera: senza di essa le regioni sarebbero soltanto
    insiemi, tutti con le stesse proprieta', e il deck acquisterebbe nomi
    invece che materiali.

    Mutazione che lo uccide: far citare a ogni *SOLID SECTION il materiale
    unico della corsa, che e' esattamente il comportamento di prima.
    """
    nodi, tetraedri = cube_mesh
    meta = len(tetraedri) // 2
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={
            "NUCLEO": (np.arange(meta), CLS_C25),
            "TESTA": (np.arange(meta, len(tetraedri)), CLS_C30),
        },
    )
    righe = percorso.read_text(encoding="ascii").splitlines()

    assert [r for r in righe if r.startswith("*SOLID SECTION")] == [
        "*SOLID SECTION, ELSET=NUCLEO, MATERIAL=CLS_C25",
        "*SOLID SECTION, ELSET=TESTA, MATERIAL=CLS_C30",
    ]
    assert [r for r in righe if r.startswith("*MATERIAL")] == [
        "*MATERIAL, NAME=CLS_C25",
        "*MATERIAL, NAME=CLS_C30",
    ]
    # Il modulo di ciascuno, non solo il nome: due card omonime con le stesse
    # proprieta' passerebbero la prima asserzione senza portare due materiali.
    assert righe[righe.index("*MATERIAL, NAME=CLS_C25") + 2] == "31476.0, 0.2"
    assert righe[righe.index("*MATERIAL, NAME=CLS_C30") + 2] == "32837.0, 0.2"


def test_gli_orfani_restano_sul_materiale_unico_della_corsa(tmp_path, cube_mesh):
    """Il ripiego su `ALL_WALL` cita `analysis.material`, e resta dov'e' (#145).

    Il materiale della corsa e' il primo *MATERIAL scritto perche' la sua
    sezione e' la prima: su due sezioni sovrapposte `ccx` applica l'ultima
    senza un avviso, e il ripiego deve poter essere sovrascritto.

    Mutazione che lo uccide: far citare al ripiego il materiale di una regione.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={"NUCLEO": (np.array([0, 1, 2]), CLS_C25)},
    )
    righe = percorso.read_text(encoding="ascii").splitlines()

    assert [r for r in righe if r.startswith("*SOLID SECTION")] == [
        "*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=MURATURA",
        "*SOLID SECTION, ELSET=NUCLEO, MATERIAL=CLS_C25",
    ]
    assert [r for r in righe if r.startswith("*MATERIAL")] == [
        "*MATERIAL, NAME=MURATURA",
        "*MATERIAL, NAME=CLS_C25",
    ]


def test_due_regioni_sullo_stesso_materiale_scrivono_una_card_sola(tmp_path, cube_mesh):
    """Lo stesso materiale in due regioni e' un materiale, non due.

    `ccx` legge due *MATERIAL omonimi senza protestare e tiene l'ultimo: il
    deck resterebbe valido, ma porterebbe una card che non aggiunge nulla e un
    nome definito due volte. Una sola, e le due sezioni la citano.

    Mutazione che lo uccide: scrivere una card per regione invece che per
    materiale distinto.
    """
    nodi, tetraedri = cube_mesh
    meta = len(tetraedri) // 2
    percorso = tmp_path / "model.inp"

    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={
            "NUCLEO": (np.arange(meta), CLS_C25),
            "TESTA": (np.arange(meta, len(tetraedri)), CLS_C25),
        },
    )
    righe = percorso.read_text(encoding="ascii").splitlines()

    assert [r for r in righe if r.startswith("*MATERIAL")] == ["*MATERIAL, NAME=CLS_C25"]
    assert [r for r in righe if r.startswith("*SOLID SECTION")] == [
        "*SOLID SECTION, ELSET=NUCLEO, MATERIAL=CLS_C25",
        "*SOLID SECTION, ELSET=TESTA, MATERIAL=CLS_C25",
    ]


def test_due_materiali_omonimi_ignorando_le_maiuscole_sono_rifiutati(tmp_path, cube_mesh):
    """`ccx` risolve i nomi senza distinguere il caso: `cls_c25` e' `CLS_C25`.

    Due materiali diversi sotto lo stesso nome darebbero un deck che il
    solutore legge senza un avviso, applicando all'una e all'altra regione le
    proprieta' dell'ultima card. E' il difetto del caso dei nomi, gia' occorso
    quattro volte in questo repository.

    Mutazione che lo uccide: confrontare i nomi senza `casefold`.
    """
    nodi, tetraedri = cube_mesh
    meta = len(tetraedri) // 2
    minuscolo = config.Material(name="cls_c25", young=32837.0, poisson=0.2, density=2.5e-9)

    with pytest.raises(ValueError, match="senza distinguere le maiuscole"):
        abaqus.write_inp(
            tmp_path / "model.inp", nodi, tetraedri,
            node_sets=_base_and_top(nodi), material=MATERIALE,
            regioni={
                "NUCLEO": (np.arange(meta), CLS_C25),
                "TESTA": (np.arange(meta, len(tetraedri)), minuscolo),
            },
        )


def test_il_deck_a_regioni_dichiara_che_non_distingue_nucleo_e_copriferro(tmp_path, cube_mesh):
    """La limitazione sta scritta nel deck, non solo nella relazione.

    Chi apre il `.inp` fra sei mesi vede un calcestruzzo per regione: senza
    questa riga crederebbe che il modello distingua il nucleo confinato dal
    copriferro, che e' una distinzione della sezione a fibre e non di un
    solido a tetraedri.

    Mutazione che lo uccide: togliere il commento, o scriverlo anche quando le
    regioni non ci sono -- il deck di una corsa monomaterica non cambia.
    """
    nodi, tetraedri = cube_mesh
    con = tmp_path / "con.inp"
    senza = tmp_path / "senza.inp"

    abaqus.write_inp(
        con, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
        regioni={"NUCLEO": (np.arange(len(tetraedri)), CLS_C25)},
    )
    abaqus.write_inp(
        senza, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
    )

    assert f"** {abaqus.CONTINUO_CONFINATO}" in con.read_text(encoding="ascii").splitlines()
    assert abaqus.CONTINUO_CONFINATO not in senza.read_text(encoding="ascii")
    # `ccx` tronca le righe lunghe: un commento oltre la larghezza di lettura
    # arriverebbe al solutore spezzato, e la meta' orfana non e' piu' un commento.
    assert len(f"** {abaqus.CONTINUO_CONFINATO}") <= 132


def test_un_dizionario_di_regioni_vuoto_scrive_il_deck_di_prima(tmp_path, cube_mesh):
    """`regioni={}` e `regioni=None` sono lo stesso deck, byte per byte.

    E' il vincolo piu' stretto della fase: le ventidue righe dei registri sono
    la provenienza della tabella sperimentale, e una corsa che non dichiara
    regioni deve produrre il deck che ha gia' prodotto. Il confronto e' sui
    byte e non sulle card, perche' una riga in piu' in qualunque punto basta a
    rendere la corsa irriproducibile.

    Mutazione che lo uccide: scrivere il commento della limitazione, o
    riorganizzare i *MATERIAL, senza guardare se le regioni ci sono.
    """
    nodi, tetraedri = cube_mesh
    vuoto = tmp_path / "vuoto.inp"
    assente = tmp_path / "assente.inp"

    for percorso, regioni in ((vuoto, {}), (assente, None)):
        abaqus.write_inp(
            percorso, nodi, tetraedri, node_sets=_base_and_top(nodi), material=MATERIALE,
            regioni=regioni,
        )

    assert vuoto.read_bytes() == assente.read_bytes()


















