"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

import pytest

from meshrec.core import config


def test_defaults_are_in_working_units():
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.analysis.gravity == pytest.approx(9810.0)
    assert cfg.analysis.material.density == pytest.approx(1.8e-9)
    assert cfg.analysis.material.young == pytest.approx(1500.0)
    assert cfg.input.scale == pytest.approx(1.0)


def test_yaml_round_trip_preserves_every_field(tmp_path):
    cfg = config.PipelineConfig(
        input=config.InputConfig(path="nuvola.ply", scale=1000.0),
        surface=config.SurfaceConfig(poisson_depth=11, density_quantile=0.1),
        tet=config.TetConfig(min_ratio=1.4, max_volume=250.0),
    )
    path = tmp_path / "config.yaml"
    config.save_config(cfg, path)
    assert config.load_config(path) == cfg


def test_invalid_values_are_rejected():
    with pytest.raises(ValueError):
        config.InputConfig(path="nuvola.ply", scale=0.0)
    with pytest.raises(ValueError):
        config.SurfaceConfig(density_quantile=1.5)
