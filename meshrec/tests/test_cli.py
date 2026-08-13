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


def test_the_sweep_command_runs_a_two_candidate_grid_on_the_synthetic_cube(tmp_path):
    """Prova end-to-end del motore: griglia, sottoprocessi, registro, fronte.

    Il cubo e' l'unica geometria su cui la catena intera sta dentro la suite.
    Verifica che la catena non si spezzi, non che produca qualcosa di
    sensato: quello si misura sulle due corse reali, fuori dai test.
    """
    import yaml

    from meshrec.core import config, io, synth, sweep

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    base = config.PipelineConfig(
        input=config.InputConfig(path=str(cloud)),
        surface=config.SurfaceConfig(poisson_depth=6),
    )
    base_path = tmp_path / "base.yaml"
    config.save_config(base, base_path)

    experiment = config.ExperimentConfig(
        name="cubo",
        base=base_path,
        axes=[config.AxisSpec(path="tet.min_ratio", values=[2.0])],
        sweep=config.SweepConfig(
            workers=2, runs_root=tmp_path / "runs", registry_root=tmp_path / "experiments"
        ),
    )
    experiment_path = tmp_path / "cubo.yaml"
    experiment_path.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )

    # Con due soli candidati confrontabili il fronte li contiene entrambi:
    # e' il caso "non discrimina" gia' previsto da check_sweep, atteso qui.
    with pytest.warns(sweep.SweepDiagnosticWarning, match="non discrimina"):
        assert cli.main(["sweep", str(experiment_path)]) == 0

    registry = tmp_path / "experiments" / "cubo" / "registro.jsonl"
    rows = sweep.load_registry(registry)
    assert len(rows) == 2
    assert all(row["outcome"] == "riuscito" for row in rows)
    assert any(row["on_front"] for row in rows)

    assert cli.main(["sweep-verify", str(registry)]) == 0
    assert cli.main(["sweep-report", str(registry), "--out", str(tmp_path / "r.html")]) == 0
    assert (tmp_path / "r.html").exists()


def test_sweep_verify_reports_a_nonzero_exit_when_an_artifact_row_is_stale(tmp_path):
    """sweep-verify deve fermare uno script quando il registro non torna piu' col disco."""
    from meshrec.core import sweep

    out_dir = tmp_path / "run"
    out_dir.mkdir()
    artifact = out_dir / "wall_model.inp"
    artifact.write_text("originale", encoding="utf-8")

    registry = tmp_path / "registro.jsonl"
    sweep.append_row(
        registry,
        {
            "fingerprint": "deadbeef0000",
            "out_dir": str(out_dir),
            "artifacts": {"wall_model.inp": sweep.file_digest(artifact)},
            "artifacts_kept": True,
        },
    )

    # L'artefatto cambia dopo la scrittura della riga: l'impronta non torna piu'.
    artifact.write_text("alterato", encoding="utf-8")

    assert cli.main(["sweep-verify", str(registry)]) == 1


def test_the_sweep_command_reports_the_thickness_gate_failure(tmp_path, capsys):
    """Il cancello sulla misura di spessore ferma lo sweep prima di partire.

    L'uscita e' 1 e il messaggio del cancello compare su stderr: che dica
    perche' si ferma conta quanto il fatto che si fermi.
    """
    import yaml

    from meshrec.core import config, io, synth

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    base = config.PipelineConfig(
        input=config.InputConfig(path=str(cloud)),
        surface=config.SurfaceConfig(poisson_depth=6),
    )
    base_path = tmp_path / "base.yaml"
    config.save_config(base, base_path)

    experiment = config.ExperimentConfig(
        name="cubo",
        base=base_path,
        axes=[config.AxisSpec(path="tet.min_ratio", values=[2.0])],
        known_thickness=1.0,  # incoerente con il cubo sintetico: scarto oltre il 5%
        sweep=config.SweepConfig(
            workers=2, runs_root=tmp_path / "runs", registry_root=tmp_path / "experiments"
        ),
    )
    experiment_path = tmp_path / "cubo.yaml"
    experiment_path.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )

    result = cli.main(["sweep", str(experiment_path)])
    err = capsys.readouterr().err
    assert result == 1
    assert "la misura di spessore non riproduce il valore noto" in err
