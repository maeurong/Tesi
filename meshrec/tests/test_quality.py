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
    assert quality.volume_metrics(nodes, good)["inverted"] == 0
    assert quality.volume_metrics(nodes, flipped)["inverted"] == 1


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
