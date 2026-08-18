import meshio
import numpy as np
import pytest

from meshrec.core import abaqus, config, synth, volume
from meshrec.core.config import Material
from materiale import ANALISI, MATERIALE, crea_config


SIZE = (100.0, 40.0, 200.0)


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


def test_output_requests_are_in_the_modern_form(tmp_path):
    """*NODE FILE produce .fil in Abaqus, non .odb: la Fase 1 usa *OUTPUT, FIELD."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())
    path = tmp_path / "modello.inp"

    abaqus.write_inp(
        path,
        nodes,
        tets,
        node_sets=abaqus.build_node_sets(nodes, tolerance=1.0),
        material=MATERIALE,
    )
    text = path.read_text(encoding="ascii")

    assert "*OUTPUT, FIELD" in text
    assert "*NODE OUTPUT" in text
    assert "*ELEMENT OUTPUT" in text
    assert "*NODE FILE" not in text
    assert "*EL FILE" not in text


def test_export_model_writes_both_files_and_reports_mass(tmp_path):
    meshio = pytest.importorskip("meshio")
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(material=MATERIALE),
        config.TetConfig(),
    )

    assert (tmp_path / "wall_model.inp").exists()
    assert (tmp_path / "wall_model.vtu").exists()
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0, rel=0.02)
    assert metrics["mass"] == pytest.approx(metrics["volume"] * 1.8e-9, rel=1e-6)
    assert metrics["node_sets"]["BASE"] > 0
    read_back = meshio.read(tmp_path / "wall_model.vtu")
    assert len(read_back.points) == len(nodes)


def test_c3d10_is_refused_until_the_writer_supports_it(tmp_path):
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    with pytest.raises(NotImplementedError, match="C3D10"):
        abaqus.export_model(
            tmp_path / "m.inp",
            tmp_path / "m.vtu",
            nodes,
            tets,
            config.AnalysisConfig(material=MATERIALE),
            config.TetConfig(element="C3D10"),
        )


def _yaw(angle_deg: float) -> np.ndarray:
    """Rotazione attorno a z: lo z del sistema d'ingresso resta il verticale vero."""
    angle = np.radians(angle_deg)
    return np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )


def test_height_axis_points_up_regardless_of_svd_sign():
    """Il verso di z deve seguire il verticale reale, non il segno arbitrario della SVD.

    Un punto isolato oltre la quota massima marca l'estremita fisicamente
    superiore del muro: dopo l'allineamento deve trovarsi sempre alla quota
    massima, mai alla minima, qualunque sia la rotazione (attorno a z) applicata
    in ingresso.
    """
    rng = np.random.default_rng(2)
    base = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(1500, 3))
    marker = np.array([[500.0, 25.0, 305.0]])  # oltre la quota massima del muro

    for angle_deg in (0.0, 47.0, 137.0, 200.0, 311.0):
        cloud = np.vstack([base, marker]) @ _yaw(angle_deg).T + np.array([100.0, -300.0, 50.0])

        aligned, _, _ = abaqus.align_to_axes(cloud)
        marker_z = aligned[-1, 2]

        assert marker_z == pytest.approx(aligned[:, 2].max())
        assert marker_z != pytest.approx(aligned[:, 2].min())


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

    boundary = abaqus._boundary_nodes(tets)
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
        config.TetConfig(),
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
    facce = abaqus._boundary_faces(tets)
    spigoli = np.unique(
        np.sort(np.vstack([facce[:, [0, 1]], facce[:, [1, 2]], facce[:, [0, 2]]]), axis=1), axis=0
    )
    atteso = np.median(np.linalg.norm(nodes[spigoli[:, 0]] - nodes[spigoli[:, 1]], axis=1))

    assert abaqus.set_tolerance(nodes, tets, 6.0) == pytest.approx(6.0 * atteso)
    assert abaqus.set_tolerance(nodes, tets, 1.0) == pytest.approx(atteso)


def test_the_boundary_nodes_are_the_nodes_of_the_boundary_faces(cube_mesh):
    """Le due funzioni non devono divergere: la seconda deriva dalla prima."""
    _, tets = cube_mesh

    assert np.array_equal(abaqus._boundary_nodes(tets), np.unique(abaqus._boundary_faces(tets)))


def test_the_footprint_is_fully_covered_on_a_flat_base(cube_mesh):
    """Su una base piana l'insieme vincolato copre tutta la superficie d'appoggio."""
    nodes, tets = cube_mesh
    bordo = abaqus._boundary_nodes(tets)
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
            config.TetConfig(),
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
        config.TetConfig(),
    )

    assert metrics["fixed_nset_coverage"] == 1.0
    assert metrics["boundary_spacing"] > 0.0
    assert metrics["set_tolerance"] == pytest.approx(6.0 * metrics["boundary_spacing"])
