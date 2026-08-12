import numpy as np
import pytest

from meshrec.core import config, quality, synth, volume

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_tetrahedralize_fills_the_box():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    assert nodes.ndim == 2 and nodes.shape[1] == 3
    assert tets.ndim == 2 and tets.shape[1] == 4
    assert len(tets) > 10
    assert tets.max() < len(nodes)


def test_sum_of_tet_volumes_equals_the_exact_volume():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    total = np.abs(quality.tet_volumes(nodes, tets)).sum()
    assert total == pytest.approx(EXACT_VOLUME, rel=1e-6)


def test_no_inverted_elements():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    assert len(quality.inverted_tets(nodes, tets)) == 0


def test_max_volume_controls_the_number_of_elements():
    vertices, faces = synth.box_mesh(SIZE)
    _, coarse = volume.tetrahedralize(vertices, faces, max_volume=200_000.0)
    _, fine = volume.tetrahedralize(vertices, faces, max_volume=20_000.0)

    assert len(fine) > len(coarse)


def test_an_open_surface_is_refused_before_tetgen_runs():
    """fTetWild non e' installabile su Windows: la guardia e' l'unica difesa."""
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    with pytest.raises(volume.NotWatertightError, match="4 spigoli di bordo"):
        volume.tetrahedralize(vertices, damaged)


def test_with_metrics_reports_counts_and_time():
    vertices, faces = synth.box_mesh(SIZE)

    nodes, tets, metrics = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    assert metrics["nodes"] == len(nodes)
    assert metrics["tets"] == len(tets)
    assert metrics["seconds"] > 0.0
    assert metrics["element"] == "C3D4"


def test_inverted_elements_are_a_blocking_error():
    """La spec chiede errore bloccante, non avviso: qui lo si verifica sul percorso reale."""
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())
    assert len(quality.inverted_tets(nodes, tets)) == 0
