import numpy as np
import pytest

from meshrec.core import synth

SIZE = (100.0, 40.0, 200.0)


def test_sample_box_surface_lies_on_the_box():
    points = synth.sample_box_surface(SIZE, spacing=10.0)

    assert points.ndim == 2 and points.shape[1] == 3
    assert points.dtype == np.float64
    assert len(points) > 100

    # ogni punto appartiene ad almeno una delle sei facce
    on_face = np.zeros(len(points), dtype=bool)
    for axis, length in enumerate(SIZE):
        on_face |= np.isclose(points[:, axis], 0.0)
        on_face |= np.isclose(points[:, axis], length)
    assert on_face.all()


def test_sample_box_surface_fills_the_bounding_box():
    points = synth.sample_box_surface(SIZE, spacing=10.0)

    assert points.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert points.max(axis=0) == pytest.approx(list(SIZE))


def test_sample_box_surface_is_deterministic_and_noise_is_bounded():
    a = synth.sample_box_surface(SIZE, spacing=10.0, noise=0.5, seed=7)
    b = synth.sample_box_surface(SIZE, spacing=10.0, noise=0.5, seed=7)
    clean = synth.sample_box_surface(SIZE, spacing=10.0)

    assert np.array_equal(a, b)
    assert a.shape == clean.shape
    assert np.abs(a - clean).max() < 5.0  # 10 sigma


def test_smaller_spacing_gives_more_points():
    coarse = synth.sample_box_surface(SIZE, spacing=20.0)
    fine = synth.sample_box_surface(SIZE, spacing=5.0)

    assert len(fine) > 4 * len(coarse)


def test_open3d_reads_and_downsamples_a_synthetic_cloud(tmp_path):
    import open3d as o3d

    points = synth.sample_box_surface(SIZE, spacing=2.0)

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)

    path = tmp_path / "box.ply"
    assert o3d.io.write_point_cloud(str(path), cloud)

    reloaded = o3d.io.read_point_cloud(str(path))
    assert len(reloaded.points) == len(points)

    reduced = reloaded.voxel_down_sample(voxel_size=10.0)
    assert 0 < len(reduced.points) < len(points)


def test_il_telaio_sintetico_ha_i_prismi_che_gli_si_chiedono():
    """Verita' nota del banco: due prismi disgiunti danno una nuvola il cui
    ingombro e' l'unione dei due, e nessun punto fuori."""
    prismi = [
        ((0.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
        ((800.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
    ]
    punti = synth.sample_frame_surface(prismi, spacing=25.0)

    assert punti.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert punti.max(axis=0) == pytest.approx([1000.0, 200.0, 1000.0])
    # nessun punto nella campata vuota fra i due prismi
    assert not ((punti[:, 0] > 250.0) & (punti[:, 0] < 750.0)).any()
