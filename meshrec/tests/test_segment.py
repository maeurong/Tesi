"""Step 2, prima parte: outlier statistici e ritaglio a box."""

import numpy as np
import pytest

from meshrec.core import config, segment, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 5.0


def test_isolated_points_are_removed():
    points = synth.sample_box_surface(SIZE, SPACING)
    strays = np.array([[500.0, 500.0, 500.0], [-400.0, -400.0, -400.0]])
    dirty = np.vstack([points, strays])

    clean, metrics = segment.remove_outliers(dirty, config.SegmentConfig())

    assert metrics["outliers_removed"] >= 2
    assert clean.max() < 400.0


def test_crop_box_keeps_only_the_points_inside():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0))

    cropped, metrics = segment.crop_box(points, cfg)

    assert cropped[:, 2].max() <= 100.0
    assert len(cropped) < len(points)
    assert metrics["points_after"] == len(cropped)


def test_il_ritaglio_dice_quanto_toglie_e_da_quale_faccia():
    """Il caso vero da cui viene: su lab_crop il box toglieva il 30,8% della
    nuvola -- fra cui tutta la base del portale, cioe' i due appoggi -- e a
    video non compariva niente che lo facesse sospettare. `points_before` e
    `points_after` c'erano gia', ma la loro differenza dice un numero, non
    quale piano di taglio ha incontrato qualcosa.

    Qui il box taglia da UNA faccia sola, quella alta in Z: e' l'oracolo che
    distingue «il box ha tolto» da «il box ha tolto DA LI'».
    """
    # Un piano fitto a z = 0, piu' un piano a z = 200 che sta sopra il box.
    piano = np.array([[x, y, 0.0] for x in range(10) for y in range(10)])
    sopra = piano + np.array([0.0, 0.0, 200.0])
    points = np.vstack([piano, sopra])
    cfg = config.SegmentConfig(crop_min=(-1.0, -1.0, -1.0), crop_max=(100.0, 100.0, 100.0))

    _, metrics = segment.crop_box(points, cfg)

    assert metrics["cropped_points"] == len(sopra)
    assert metrics["cropped_fraction"] == pytest.approx(0.5)
    # Una faccia sola nominata, e con il proprio conteggio: le altre cinque non
    # compaiono, perche' sei zeri nascondono l'unica riga che conta.
    assert metrics["cropped_by_face"] == {"sopra_z": len(sopra)}


def test_un_ritaglio_che_non_toglie_niente_non_lascia_righe_a_video():
    """Un box piu' largo della nuvola e' un ritaglio che non ritaglia. Sei
    conteggi a zero sarebbero rumore in un pannello dove ogni riga si legge."""
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(-1e4, -1e4, -1e4), crop_max=(1e4, 1e4, 1e4))

    _, metrics = segment.crop_box(points, cfg)

    assert metrics["cropped_points"] == 0
    assert metrics["cropped_fraction"] == 0.0
    assert "cropped_by_face" not in metrics


def test_un_punto_puo_uscire_da_piu_facce_e_i_conteggi_non_lo_nascondono():
    """Le facce sono sei domande separate, non una ripartizione: un punto
    fuori da un angolo esce da tre facce e va contato in tutte e tre.

    Dichiararlo con un test invece che col solo commento: chi somma le facce e
    trova piu' di `cropped_points` deve trovare qui perche', invece di
    sospettare un difetto.
    """
    dentro = np.zeros((3, 3))
    angolo = np.array([[-5.0, -5.0, -5.0]])
    points = np.vstack([dentro, angolo])
    cfg = config.SegmentConfig(crop_min=(-1.0, -1.0, -1.0), crop_max=(1.0, 1.0, 1.0))

    _, metrics = segment.crop_box(points, cfg)

    assert metrics["cropped_points"] == 1
    assert metrics["cropped_by_face"] == {"sotto_x": 1, "sotto_y": 1, "sotto_z": 1}
    assert sum(metrics["cropped_by_face"].values()) > metrics["cropped_points"]


def test_crop_without_bounds_is_a_no_op():
    points = synth.sample_box_surface(SIZE, SPACING)
    cropped, metrics = segment.crop_box(points, config.SegmentConfig())
    assert len(cropped) == len(points)
    assert metrics["cropped"] is False


def test_crop_that_empties_the_cloud_raises():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(1000.0, 1000.0, 1000.0), crop_max=(2000.0, 2000.0, 2000.0))
    with pytest.raises(ValueError, match="nessun punto"):
        segment.crop_box(points, cfg)


def test_segment_cloud_in_crop_mode_chains_both_operations():
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[500.0, 500.0, 500.0]]])
    cfg = config.SegmentConfig(
        method="crop", crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0)
    )

    result, metrics = segment.segment_cloud(dirty, cfg, SPACING)

    assert result[:, 2].max() <= 100.0
    assert metrics["method"] == "crop"
    assert metrics["outliers_removed"] >= 1
    assert metrics["points_after"] == len(result)


def test_crop_box_with_inverted_bounds_raises():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(100.0, 0.0, 0.0), crop_max=(0.0, 40.0, 100.0))
    with pytest.raises(ValueError, match="non e maggiore"):
        segment.crop_box(points, cfg)


def test_remove_outliers_that_empties_the_cloud_raises():
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    cfg = config.SegmentConfig(outlier_neighbors=1, outlier_std_ratio=1e-9)
    with pytest.raises(ValueError, match="svuotato"):
        segment.remove_outliers(points, cfg)


def test_segment_cloud_reports_original_points_before_not_intermediate():
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[500.0, 500.0, 500.0]]])
    cfg = config.SegmentConfig(
        method="crop", crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0)
    )

    result, metrics = segment.segment_cloud(dirty, cfg, SPACING)

    assert metrics["points_before"] == len(dirty)
    assert metrics["points_after"] == len(result)


def _scene():
    """Pavimento orizzontale piu un muro verticale: la struttura di lab_frame.pcd in piccolo."""
    rng = np.random.default_rng(0)
    floor = np.column_stack(
        [
            rng.uniform(-500.0, 500.0, 4000),
            rng.uniform(-500.0, 500.0, 4000),
            rng.normal(0.0, 1.0, 4000),
        ]
    )
    wall = np.column_stack(
        [
            rng.normal(200.0, 12.0, 3000),
            rng.uniform(-300.0, 300.0, 3000),
            rng.uniform(0.0, 400.0, 3000),
        ]
    )
    return np.vstack([floor, wall])


def test_ransac_finds_the_floor_plane():
    points = _scene()
    planes, residual, metrics = segment.extract_planes(
        points, config.SegmentConfig(plane_max_count=1), spacing=8.0
    )
    assert metrics["planes_found"] == 1
    assert len(planes[0]) > 2000
    assert len(residual) < len(points)


def test_auto_mode_isolates_the_wall():
    points = _scene()
    # cluster_min_points=100 (valore del brief) svuota il DBSCAN su questa scena:
    # con eps=4*spacing=32 il muro sintetico non ha densita locale per 100 vicini
    # (verificato: 0 cluster trovati). 25 e' il valore piu alto per cui il muro
    # resta un cluster unico su questa nuvola sintetica.
    cfg = config.SegmentConfig(method="auto", plane_max_count=1, cluster_min_points=25)

    wall, metrics = segment.segment_cloud(points, cfg, spacing=8.0)

    assert metrics["method"] == "auto"
    assert metrics["clusters_found"] >= 1
    assert len(wall) > 1000
    # il muro sta attorno a x = 200 ed e sottile: il pavimento e sparito
    assert wall[:, 0].mean() == pytest.approx(200.0, abs=30.0)
    assert metrics["thickness"] < 120.0
    assert metrics["planarity_rms"] < 40.0


def test_choosing_a_cluster_index_beyond_the_last_raises():
    points = _scene()
    cfg = config.SegmentConfig(method="auto", plane_max_count=1, cluster_index=99)
    with pytest.raises(ValueError, match="cluster_index"):
        segment.segment_cloud(points, cfg, spacing=8.0)


def test_auto_mode_is_reproducible_across_runs():
    """Criterio di accettazione della Fase 1: stessa config, stesso risultato.

    RANSAC in Open3D e' multithread: senza OMP_NUM_THREADS=1 impostato
    all'import del pacchetto (vedi meshrec/__init__.py) o3d.utility.random.seed
    non basta, e due run della stessa config estraggono piani diversi.
    """
    points = _scene()
    cfg = config.SegmentConfig(method="auto", plane_max_count=1, cluster_min_points=25)

    first, first_metrics = segment.segment_cloud(points, cfg, spacing=8.0)
    second, second_metrics = segment.segment_cloud(points, cfg, spacing=8.0)

    assert np.array_equal(first, second)
    assert first_metrics["cluster_points"] == second_metrics["cluster_points"]
    assert first_metrics["planarity_rms"] == second_metrics["planarity_rms"]
