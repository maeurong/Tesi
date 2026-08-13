"""Verifica di Fase 1: il parallelepipedo a soluzione nota attraversa tutta la catena."""

import json

import numpy as np
import pytest
from pydantic import ValidationError

from meshrec.core import config, io, pipeline, quality, synth

SIZE = (120.0, 60.0, 240.0)
SPACING = 4.0
EXACT_VOLUME = 120.0 * 60.0 * 240.0


def _config_cubo(tmp_path):
    """Configurazione del cubo di prova, la stessa della fixture run_dir."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))
    return config.PipelineConfig(
        input=config.InputConfig(path=cloud_path, spacing_sample=5000),
        downsample=config.DownsampleConfig(voxel_size=SPACING),
        surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
        tet=config.TetConfig(min_ratio=1.2),
        run=config.RunConfig(out_dir=tmp_path / "out"),
    )


def test_una_corsa_interrotta_non_sostituisce_le_metriche_complete(tmp_path, monkeypatch):
    """Il difetto storico: il finally scriveva metrics.json col dizionario com'era,
    e una corsa morta a meta' cancellava quella completa di prima.
    """
    from meshrec.core import pipeline, surface

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    complete = {chiave: {"ok": True} for chiave in ("01_load", "11_export")}
    (corsa / pipeline.METRICS_FILENAME).write_text(json.dumps(complete), encoding="utf-8")

    cfg = _config_cubo(tmp_path)
    cfg.run.out_dir = corsa

    def esplode(*_argomenti, **_chiavi):
        raise RuntimeError("interruzione simulata dello step 3")

    monkeypatch.setattr(surface, "downsample", esplode)
    with pytest.raises(RuntimeError):
        pipeline.run(cfg)

    rilette = json.loads((corsa / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert rilette == complete, "metrics.json completo sostituito da uno parziale"
    assert (corsa / pipeline.METRICS_PARTIAL).exists(), "il parziale deve restare, per diagnosi"


def test_from_step_beyond_tetrahedralize_is_rejected():
    """Gli step 10 e 11 non hanno lavoro costoso da saltare: from_step si ferma a 9."""
    with pytest.raises(ValidationError):
        config.RunConfig(from_step=10)


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    """Esegue la pipeline una volta sola: e' il test piu lento della suite."""
    pytest.importorskip("pymeshfix")
    base = tmp_path_factory.mktemp("run")
    cloud_path = base / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))

    cfg = config.PipelineConfig(
        input=config.InputConfig(path=cloud_path, spacing_sample=5000),
        downsample=config.DownsampleConfig(voxel_size=SPACING),
        surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
        tet=config.TetConfig(min_ratio=1.2),
        run=config.RunConfig(out_dir=base / "out"),
    )
    metrics = pipeline.run(cfg)
    return base / "out", metrics


def test_the_run_directory_holds_config_metrics_and_the_deck(run_dir):
    out, _ = run_dir
    assert (out / "config.yaml").exists()
    assert (out / "metrics.json").exists()
    assert (out / "wall_model.inp").exists()
    assert (out / "wall_model.vtu").exists()
    assert config.load_config(out / "config.yaml").tet.min_ratio == pytest.approx(1.2)


def test_the_surface_is_closed(run_dir):
    _, metrics = run_dir
    assert metrics["06_repair"]["watertight_after"] is True


def test_the_volume_matches_the_exact_value(run_dir):
    _, metrics = run_dir
    assert metrics["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)


def test_no_inverted_tetrahedra(run_dir):
    _, metrics = run_dir
    assert metrics["10_volume_quality"]["inverted"] == 0
    assert metrics["10_volume_quality"]["min_dihedral_deg"]["min"] > 0.0


def test_the_deck_is_readable_and_counts_agree(run_dir):
    meshio = pytest.importorskip("meshio")
    out, metrics = run_dir
    mesh = meshio.read(out / "wall_model.inp")
    assert len(mesh.points) == metrics["09_tetrahedralize"]["nodes"]
    assert sum(len(block.data) for block in mesh.cells) == metrics["09_tetrahedralize"]["tets"]


def test_the_base_set_holds_only_the_nodes_at_the_lowest_level(run_dir):
    out, metrics = run_dir
    text = (out / "wall_model.inp").read_text(encoding="ascii")
    assert "*NSET, NSET=BASE" in text
    assert metrics["11_export"]["node_sets"]["BASE"] > 0

    meshio = pytest.importorskip("meshio")
    points = meshio.read(out / "wall_model.inp").points
    lines = text.splitlines()
    start = lines.index("*NSET, NSET=BASE") + 1
    indices = []
    for line in lines[start:]:
        if line.startswith("*"):
            break
        indices += [int(value) - 1 for value in line.split(",") if value.strip()]
    tolerance = metrics["11_export"]["set_tolerance"]
    assert len(indices) == metrics["11_export"]["node_sets"]["BASE"]
    assert points[indices][:, 2].max() <= points[:, 2].min() + tolerance + 1e-9


def test_the_mass_follows_from_density_and_volume(run_dir):
    _, metrics = run_dir
    density = config.Material().density
    assert metrics["11_export"]["mass"] == pytest.approx(
        metrics["11_export"]["volume"] * density, rel=1e-9
    )


def test_geometric_error_against_the_source_cloud_is_reported(run_dir):
    pytest.importorskip("pymeshlab")
    _, metrics = run_dir
    error = metrics["07_surface_quality"]["geometric_error"]
    assert error["hausdorff"] > 0.0
    assert error["cloud_to_mesh"]["RMS"] < SPACING * 2.0


def test_metrics_json_is_the_same_as_the_returned_dictionary(run_dir):
    out, metrics = run_dir
    with (out / "metrics.json").open(encoding="utf-8") as handle:
        assert json.load(handle) == json.loads(json.dumps(metrics))


def test_the_same_configuration_run_twice_gives_the_same_result(tmp_path):
    """Criterio di accettazione: la stessa configurazione produce lo stesso risultato."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))

    def once(name):
        cfg = config.PipelineConfig(
            input=config.InputConfig(path=cloud_path, spacing_sample=2000),
            downsample=config.DownsampleConfig(voxel_size=8.0),
            surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
            run=config.RunConfig(out_dir=tmp_path / name),
        )
        return pipeline.run(cfg)

    first, second = once("a"), once("b")
    assert first["09_tetrahedralize"]["nodes"] == second["09_tetrahedralize"]["nodes"]
    assert first["09_tetrahedralize"]["tets"] == second["09_tetrahedralize"]["tets"]
    assert first["11_export"]["volume"] == pytest.approx(second["11_export"]["volume"], rel=1e-9)


def test_resuming_from_tetrahedralize_works_when_simplify_is_disabled(run_dir):
    """Configurazione predefinita (simplify.enabled=False): lo step 8 non scrive
    08_simplified.ply, quindi from_step=9 deve ricaricare la superficie riparata
    dello step 6, non l'artefatto (assente) dello step 8."""
    out, _ = run_dir
    cfg = config.load_config(out / "config.yaml")
    assert cfg.simplify.enabled is False
    cfg.run.from_step = 9

    resumed = pipeline.run(cfg)
    assert resumed["09_tetrahedralize"]["nodes"] > 0
    assert resumed["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)


def test_resuming_from_tetrahedralize_still_works_when_simplify_is_enabled(tmp_path):
    """La correzione per simplify disabilitato non deve rompere il caso abilitato."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))

    def make_cfg(from_step):
        return config.PipelineConfig(
            input=config.InputConfig(path=cloud_path, spacing_sample=5000),
            downsample=config.DownsampleConfig(voxel_size=SPACING),
            surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
            simplify=config.SimplifyConfig(enabled=True, mode="decimate", target_faces=500),
            run=config.RunConfig(out_dir=tmp_path / "out", from_step=from_step),
        )

    pipeline.run(make_cfg(1))
    resumed = pipeline.run(make_cfg(9))
    assert resumed["09_tetrahedralize"]["nodes"] > 0
    assert resumed["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)
