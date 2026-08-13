"""Riga di comando minima: eseguire una configurazione e generarne una di esempio."""

import pydantic
import pytest

from meshrec import cli
from meshrec.core import config, io, synth

SIZE = (120.0, 60.0, 240.0)


def test_init_writes_a_loadable_configuration(tmp_path):
    target = tmp_path / "config.yaml"
    assert cli.main(["init", str(target), "--input", "nuvola.ply"]) == 0
    assert config.load_config(target).input.path.name == "nuvola.ply"


def test_run_executes_the_pipeline_and_writes_the_deck(tmp_path):
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))
    cfg = config.PipelineConfig(
        input=config.InputConfig(path=cloud_path, spacing_sample=2000),
        downsample=config.DownsampleConfig(voxel_size=8.0),
        surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
        run=config.RunConfig(out_dir=tmp_path / "out"),
    )
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 0
    assert (tmp_path / "out" / "wall_model.inp").exists()


def test_from_step_overrides_the_configuration(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cfg):
        seen["from_step"] = cfg.run.from_step
        return {}

    monkeypatch.setattr(cli.pipeline, "run", fake_run)
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "5"]) == 0
    assert seen["from_step"] == 5


def test_a_failing_run_reports_the_error_without_a_traceback(tmp_path, capsys):
    cfg = config.PipelineConfig(input=config.InputConfig(path=tmp_path / "assente.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 1
    err = capsys.readouterr().err
    assert "nessun punto letto" in err
    assert "Traceback" not in err


def test_from_step_out_of_domain_is_rejected_by_pydantic_not_a_keyerror(tmp_path, capsys):
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "10"]) == 1
    err = capsys.readouterr().err
    assert "KeyError" not in err
    assert "from_step" in err


def test_run_config_rejects_an_out_of_domain_assignment(tmp_path):
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    with pytest.raises(pydantic.ValidationError):
        cfg.run.from_step = 999
