import numpy as np
import pytest

from meshrec.core import config, quality, synth, volume

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_tetrahedralize_fills_the_box():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0, max_steiner_points=-1)

    assert nodes.ndim == 2 and nodes.shape[1] == 3
    assert tets.ndim == 2 and tets.shape[1] == 4
    assert len(tets) > 10
    assert tets.max() < len(nodes)


def test_sum_of_tet_volumes_equals_the_exact_volume():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0, max_steiner_points=-1)

    total = np.abs(quality.tet_volumes(nodes, tets)).sum()
    assert total == pytest.approx(EXACT_VOLUME, rel=1e-6)


def test_no_inverted_elements():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0, max_steiner_points=-1)

    assert len(quality.inverted_tets(nodes, tets)) == 0


def test_max_volume_controls_the_number_of_elements():
    vertices, faces = synth.box_mesh(SIZE)
    _, coarse = volume.tetrahedralize(vertices, faces, max_volume=200_000.0, max_steiner_points=-1)
    _, fine = volume.tetrahedralize(vertices, faces, max_volume=20_000.0, max_steiner_points=-1)

    assert len(fine) > len(coarse)


def test_an_open_surface_is_refused_before_tetgen_runs():
    """fTetWild non e' installabile su Windows: la guardia e' l'unica difesa."""
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    with pytest.raises(volume.NotWatertightError, match="4 spigoli di bordo"):
        volume.tetrahedralize(vertices, damaged, max_steiner_points=-1)


def test_with_metrics_reports_counts_and_time():
    vertices, faces = synth.box_mesh(SIZE)

    nodes, tets, metrics = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    assert metrics["nodes"] == len(nodes)
    assert metrics["tets"] == len(tets)
    assert metrics["seconds"] > 0.0
    assert metrics["element"] == "C3D4"


def test_inverted_elements_are_a_blocking_error(monkeypatch):
    """La spec chiede errore bloccante, non avviso: qui si esercita il sollevamento."""
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    flipped = np.array([[0, 2, 1, 3]])
    monkeypatch.setattr(volume, "tetrahedralize", lambda *args, **kwargs: (nodes, flipped))

    vertices, faces = synth.box_mesh(SIZE)
    with pytest.raises(volume.InvertedElementsError, match="invertiti"):
        volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())


def test_the_default_config_puts_no_ceiling_on_the_refinement():
    """Il tetto predefinito della libreria (100000) non deve tornare di nascosto."""
    assert config.TetConfig().max_steiner_points == -1


def test_an_exhausted_steiner_budget_is_reported_not_hidden():
    """Una mesh troncata non e' la mesh che i vincoli di qualita descrivono.

    Il budget e' fissato cosi basso da essere certamente esaurito: i punti
    aggiunti eguagliano il tetto, la metrica lo dichiara e l'avviso lo dice a
    voce. Senza questo, il troncamento resta invisibile perche' TetGen non lo
    segnala e la mesh troncata non ha elementi invertiti.
    """
    vertices, faces = synth.box_mesh(SIZE)
    cfg = config.TetConfig(max_volume=20_000.0, max_steiner_points=20)

    with pytest.warns(volume.TruncatedRefinementWarning):
        nodes, _, metrics = volume.tetrahedralize_with_metrics(vertices, faces, cfg)

    assert metrics["steiner_saturated"] is True
    assert metrics["steiner_points"] == 20
    assert metrics["max_steiner_points"] == 20
    assert len(nodes) == len(vertices) + 20


def test_without_a_ceiling_the_refinement_is_not_reported_as_truncated():
    vertices, faces = synth.box_mesh(SIZE)

    _, _, metrics = volume.tetrahedralize_with_metrics(
        vertices, faces, config.TetConfig(max_volume=20_000.0)
    )

    assert metrics["steiner_saturated"] is False
    assert metrics["max_steiner_points"] == -1
