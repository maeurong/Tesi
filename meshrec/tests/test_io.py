"""Step 1: caricamento, filtro dei non finiti, spaziatura, scala."""

import numpy as np
import pytest

from meshrec.core import config, io, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 10.0


def _write_ply(path, points):
    open3d = pytest.importorskip("open3d")
    cloud = open3d.geometry.PointCloud(open3d.utility.Vector3dVector(np.asarray(points)))
    open3d.io.write_point_cloud(str(path), cloud)


def test_mean_spacing_matches_a_regular_grid():
    points = synth.sample_box_surface(SIZE, SPACING)
    assert io.mean_spacing(points, sample=5000, seed=0) == pytest.approx(SPACING, rel=0.2)


def test_non_finite_points_are_dropped_and_counted(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[np.nan, 0.0, 0.0], [np.inf, 1.0, 2.0]]])
    path = tmp_path / "sporca.ply"
    _write_ply(path, dirty)

    loaded, metrics = io.load_cloud(config.InputConfig(path=path))

    assert metrics["points_dropped"] == 2
    assert metrics["points_kept"] == len(loaded) == len(points)
    assert np.isfinite(loaded).all()


def test_scale_factor_converts_the_extent(tmp_path):
    """Nuvola in metri: scale=1000 la porta in mm e l'ingombro lo dimostra."""
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    _, metrics = io.load_cloud(config.InputConfig(path=path, scale=1000.0))

    assert metrics["extent"] == pytest.approx(SIZE, rel=1e-3)


def test_extent_far_from_expected_size_raises(tmp_path):
    """La difesa contro l'errore di unita: silenzioso e di ordini di grandezza."""
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    with pytest.raises(io.ScaleError, match="ingombro"):
        io.load_cloud(config.InputConfig(path=path, scale=1.0, expected_size=SIZE))


def test_expected_size_is_satisfied_when_scale_is_right(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    _, metrics = io.load_cloud(
        config.InputConfig(path=path, scale=1000.0, expected_size=SIZE)
    )

    assert metrics["size_check"] == "ok"


def test_too_many_points_raises(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    path = tmp_path / "nuvola.ply"
    _write_ply(path, points)

    with pytest.raises(ValueError, match="max_points"):
        io.load_cloud(config.InputConfig(path=path, max_points=10))


def test_cloud_round_trip_preserves_points_and_normals(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    normals = np.tile([0.0, 0.0, 1.0], (len(points), 1))
    path = tmp_path / "con_normali.ply"

    io.write_cloud(path, points, normals)
    back, back_normals = io.read_cloud(path)

    assert back == pytest.approx(points, abs=1e-3)
    assert back_normals == pytest.approx(normals, abs=1e-3)


def test_missing_file_raises_with_message(tmp_path):
    """open3d.io.read_point_cloud non solleva su file assente: va controllato a mano."""
    path = tmp_path / "assente.ply"

    with pytest.raises(ValueError, match="nessun punto letto"):
        io.load_cloud(config.InputConfig(path=path))


def test_all_points_non_finite_raises_with_message(tmp_path):
    """Se il filtro dei non finiti svuota la nuvola, l'errore deve dirlo esplicitamente."""
    points = np.full((5, 3), np.nan)
    path = tmp_path / "tutta_non_finita.ply"
    _write_ply(path, points)

    with pytest.raises(ValueError, match="coordinate non finite"):
        io.load_cloud(config.InputConfig(path=path))
