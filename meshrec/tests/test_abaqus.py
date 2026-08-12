import meshio
import numpy as np
import pytest

from meshrec.core import abaqus, config, synth, volume
from meshrec.core.config import Material

SIZE = (100.0, 40.0, 200.0)


@pytest.fixture
def cube_mesh():
    vertices, faces = synth.box_mesh(SIZE)
    return volume.tetrahedralize(vertices, faces, max_volume=100_000.0)


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
        material=Material(),
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
        material=Material(),
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
        material=Material(),
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
        material=Material(),
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
        material=config.Material(),
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
        config.AnalysisConfig(),
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
            config.AnalysisConfig(),
            config.TetConfig(element="C3D10"),
        )
