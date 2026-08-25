"""Step 3, 4, 5, 8: riduzione, normali, ricostruzione, semplificazione."""

import numpy as np
import pytest

from meshrec.core import config, quality, surface, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 4.0
EXACT_VOLUME = 100.0 * 40.0 * 200.0


@pytest.fixture(scope="module")
def cloud():
    return synth.sample_box_surface(SIZE, SPACING)


def test_downsample_reduces_the_point_count(cloud):
    reduced, metrics = surface.downsample(cloud, config.DownsampleConfig(), SPACING)
    assert len(reduced) < len(cloud)
    assert metrics["points_before"] == len(cloud)
    assert metrics["points_after"] == len(reduced)
    assert 0.0 < metrics["reduction"] < 1.0
    assert metrics["voxel_size"] == pytest.approx(2.0 * SPACING)


def test_explicit_voxel_size_wins_over_the_derived_one(cloud):
    _, metrics = surface.downsample(cloud, config.DownsampleConfig(voxel_size=25.0), SPACING)
    assert metrics["voxel_size"] == pytest.approx(25.0)


def test_normals_are_unit_length_and_axis_aligned_on_a_box(cloud):
    normals, metrics = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    assert len(normals) == len(cloud)
    assert np.linalg.norm(normals, axis=1) == pytest.approx(1.0, abs=1e-6)
    # su un parallelepipedo ogni normale e vicina a un asse: la componente massima domina
    assert np.abs(normals).max(axis=1).mean() > 0.9
    assert metrics["knn"] == 30


def test_poisson_reconstructs_a_closed_box_with_the_right_volume(cloud):
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    vertices, faces, metrics = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8)
    )
    assert metrics["method"] == "poisson"
    assert metrics["triangles"] == len(faces)
    assert abs(quality.mesh_volume(vertices, faces)) == pytest.approx(EXACT_VOLUME, rel=0.25)


def test_density_trimming_removes_vertices(cloud):
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    _, _, trimmed = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8, density_quantile=0.2)
    )
    _, _, kept = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8, density_quantile=0.0)
    )
    assert trimmed["vertices_trimmed"] > 0
    assert kept["vertices_trimmed"] == 0
    assert trimmed["triangles"] < kept["triangles"]


def test_poisson_reconstruction_is_deterministic(cloud):
    """A parita di ingresso, la stessa configurazione deve dare lo stesso risultato.

    n_threads di default (1 in SurfaceConfig) evita il riordinamento non deterministico
    che con thread multipli si propaga fino a TetGen (vedi task-6-report.md, round 1).
    """
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    cfg = config.SurfaceConfig(poisson_depth=8)
    vertices_a, faces_a, _ = surface.reconstruct(cloud, normals, cfg)
    vertices_b, faces_b, _ = surface.reconstruct(cloud, normals, cfg)
    assert np.array_equal(vertices_a, vertices_b)
    assert np.array_equal(faces_a, faces_b)


def test_disabled_simplification_is_a_no_op():
    vertices, faces = synth.box_mesh(SIZE)
    out_vertices, out_faces, metrics = surface.simplify(
        vertices, faces, config.SimplifyConfig(enabled=False)
    )
    assert out_faces.shape == faces.shape
    assert out_vertices.shape == vertices.shape
    assert metrics["enabled"] is False


def test_taubin_smoothing_does_not_collapse_the_volume():
    """Il laplaciano contrae il volume e assottiglia il muro: Taubin no."""
    vertices, faces = synth.box_mesh(SIZE)
    dense_vertices, dense_faces, _ = surface.simplify(
        vertices, faces, config.SimplifyConfig(enabled=True, mode="remesh", remesh_target_len_pct=2.0)
    )
    smooth_vertices, smooth_faces, _ = surface.simplify(
        dense_vertices,
        dense_faces,
        config.SimplifyConfig(enabled=True, mode="remesh", remesh_target_len_pct=2.0, taubin_iterations=10),
    )
    before = abs(quality.mesh_volume(dense_vertices, dense_faces))
    after = abs(quality.mesh_volume(smooth_vertices, smooth_faces))
    assert after == pytest.approx(before, rel=0.05)
