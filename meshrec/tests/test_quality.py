import inspect
import json

import numpy as np
import pytest

from meshrec.core import quality, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_box_mesh_has_eight_vertices_and_twelve_triangles():
    vertices, faces = synth.box_mesh(SIZE)

    assert vertices.shape == (8, 3)
    assert faces.shape == (12, 3)
    assert vertices.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert vertices.max(axis=0) == pytest.approx(list(SIZE))


def test_box_mesh_is_watertight_and_has_no_boundary_edges():
    _, faces = synth.box_mesh(SIZE)

    assert len(quality.boundary_edges(faces)) == 0
    assert quality.is_watertight(faces)


def test_box_mesh_volume_is_exact_and_positive():
    vertices, faces = synth.box_mesh(SIZE)

    assert quality.mesh_volume(vertices, faces) == pytest.approx(EXACT_VOLUME)


def test_punch_holes_opens_the_mesh():
    _, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    assert len(damaged) == 10
    # triangoli 0 e 6 condividono spigolo (1,2): sono adiacenti, quindi 4 spigoli di bordo
    assert len(quality.boundary_edges(damaged)) == 4
    assert not quality.is_watertight(damaged)


def test_regular_tetrahedron_has_the_textbook_dihedral_angle():
    """Il tetraedro regolare ha tutti i diedri a arccos(1/3) = 70,5288 gradi."""
    nodes = np.array(
        [[1.0, 1.0, 1.0], [1.0, -1.0, -1.0], [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] == pytest.approx(70.5288, abs=1e-3)


def test_flattened_tetrahedron_has_a_small_dihedral_angle():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.001]])
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] < 1.0


def test_aspect_ratio_of_an_equilateral_triangle_is_one():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, np.sqrt(3.0) / 2.0, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] == pytest.approx(1.0, abs=1e-6)


def test_aspect_ratio_of_a_sliver_triangle_is_large():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.001, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] > 100.0


def test_surface_metrics_on_a_closed_box():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, faces)
    assert metrics["watertight"] is True
    assert metrics["boundary_edges"] == 0
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0)
    assert metrics["area"] == pytest.approx(2 * (100 * 40 + 100 * 200 + 40 * 200))
    assert metrics["triangles"] == 12


def test_surface_metrics_on_a_punched_box_reports_the_opening():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, synth.punch_holes(faces))
    assert metrics["watertight"] is False
    assert metrics["boundary_edges"] == 4


def test_volume_metrics_flag_inverted_elements():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    good = np.array([[0, 1, 2, 3]])
    flipped = np.array([[0, 2, 1, 3]])
    assert quality.volume_metrics(nodes, good, reference_ratio=1.8)["inverted"] == 0
    assert quality.volume_metrics(nodes, flipped, reference_ratio=1.8)["inverted"] == 1


def test_geometric_error_of_a_cloud_sampled_on_its_own_mesh_is_small():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0)

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] < 1.0
    assert error["cloud_to_mesh"]["RMS"] < 1.0
    assert error["mesh_to_cloud"]["max"] < 6.0


def test_geometric_error_grows_with_a_displaced_cloud():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0) + np.array([0.0, 0.0, 10.0])

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] > 5.0


def test_a_summary_without_finite_values_stays_valid_json():
    """`NaN` non fa parte di JSON: un metrics.json che lo contiene non si rilegge.

    Il riassunto dichiara anche quanti valori ha scartato, perche' una statistica
    calcolata su una frazione dei valori senza dirlo e' un numero plausibile e
    non verificabile.
    """
    summary = quality._distribution(np.array([np.nan, np.inf, -np.inf]))

    assert summary == {"min": None, "median": None, "mean": None, "max": None, "non_finite": 3}
    assert json.loads(json.dumps(summary)) == summary

    partial = quality._distribution(np.array([1.0, np.nan, 3.0]))
    assert partial["non_finite"] == 1
    assert partial["median"] == pytest.approx(2.0)


def test_radius_edge_ratio_of_the_regular_tetrahedron():
    """Il tetraedro regolare vale sqrt(6)/4: e' il minimo possibile."""
    nodi = np.array(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ]
    )
    tetraedri = np.array([[0, 1, 2, 3]])

    rapporti = quality.radius_edge_ratios(nodi, tetraedri)

    assert rapporti == pytest.approx([np.sqrt(6.0) / 4.0], rel=1e-9)


def test_radius_edge_ratio_grows_on_a_flattened_tetrahedron():
    """Uno schiacciato ha rapporto alto: e' la grandezza che min_ratio limita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.001]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert quality.radius_edge_ratios(nodi, tetraedri)[0] > 10.0


def test_a_degenerate_tetrahedron_is_infinite_not_a_crash():
    """Quattro punti complanari: nessuna sfera circoscritta finita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert not np.isfinite(quality.radius_edge_ratios(nodi, tetraedri)[0])


def test_thickness_measures_the_distance_between_the_two_faces():
    """Su una lastra campionata su entrambe le facce lo spessore e' la distanza fra i modi.

    L'ingombro non risponde alla stessa domanda: con rumore sulle facce e'
    sistematicamente piu grande della distanza fra i piani medi, ed e' il
    motivo per cui la misura e' un istogramma e non un bounding box.
    """
    rng = np.random.default_rng(0)
    n = 20_000
    y = rng.normal(0.0, 2.0, n) + np.where(rng.random(n) < 0.5, 0.0, 176.0)
    points = np.column_stack([rng.uniform(0.0, 2700.0, n), y, rng.uniform(0.0, 2000.0, n)])

    measured = quality.thickness(points, bin_width=1.0)

    assert measured["bimodal"] is True
    assert measured["thickness"] == pytest.approx(176.0, abs=3.0)
    assert measured["extent"] > measured["thickness"]


def test_thickness_declares_itself_invalid_on_a_solid_without_two_faces():
    """Una nuvola piena non ha due modi: la misura lo dichiara invece di restituire un numero."""
    rng = np.random.default_rng(1)
    # n grande per tenere il rumore di conteggio per bin sotto la soglia della
    # valle: con 5.000 punti (media ~56 per bin) capita per caso un avvallamento
    # che supera il 50% e fa dichiarare bimodale una nuvola piena.
    points = rng.uniform(0.0, 1.0, (50_000, 3)) * np.array([2700.0, 176.0, 2000.0])

    measured = quality.thickness(points, bin_width=2.0)

    assert measured["bimodal"] is False


def test_the_reference_fraction_does_not_depend_on_the_requested_min_ratio():
    """L'asse di qualita' del fronte usa un metro unico per tutti i candidati.

    Se contasse gli elementi che violano il min_ratio richiesto da ciascun
    candidato, un candidato lasco supererebbe facilmente un vincolo lasco e
    il confronto sarebbe privo di senso.
    """
    nodes = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])

    lasco = quality.fraction_over_ratio(nodes, tets, limit=100.0)
    severo = quality.fraction_over_ratio(nodes, tets, limit=0.1)

    assert lasco == pytest.approx(0.0)
    assert severo == pytest.approx(1.0)
    assert quality.volume_metrics(nodes, tets, reference_ratio=100.0)[
        "radius_edge_over_reference"
    ] == pytest.approx(0.0)


def test_the_reference_ratio_default_lives_in_config():
    from meshrec.core import config

    assert config.TetConfig().reference_ratio == pytest.approx(1.8)
    parameters = inspect.signature(quality.volume_metrics).parameters
    assert parameters["reference_ratio"].default is inspect.Parameter.empty
