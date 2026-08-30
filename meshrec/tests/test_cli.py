"""Riga di comando minima: eseguire una configurazione e generarne una di esempio."""

import pydantic
import pytest

import json

from meshrec import cli
from meshrec.core import config, io, synth
from materiale import ANALISI, MATERIALE, _tre_cartelle_finte, crea_config


SIZE = (120.0, 60.0, 240.0)


def _config_cubo_su_disco(tmp_path):
    """Configurazione del cubo scritta su disco, come negli altri test di questo file.

    `to_step=12` esplicito: dalla Fase 8 (#140) coincide col predefinito di
    RunConfig, ma questi test esercitano il comando `run` e la ripresa, non il
    solutore, e non devono dipendere da come quel predefinito cambia -- stessa
    ragione di `_config_cubo` in test_pipeline.py."""
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))
    cfg = config.PipelineConfig(
        analysis=ANALISI,
        input=config.InputConfig(path=cloud_path, spacing_sample=2000),
        downsample=config.DownsampleConfig(voxel_size=8.0),
        surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
        run=config.RunConfig(out_dir=tmp_path / "out", to_step=12),
    )
    config.save_config(cfg, tmp_path / "config.yaml")
    return tmp_path / "config.yaml"


def test_init_writes_a_loadable_configuration(tmp_path):
    target = tmp_path / "config.yaml"
    assert (
        cli.main(
            [
                "init", str(target),
                "--input", "nuvola.ply",
                "--materiale", "CALCESTRUZZO_C25_30",
                "--young", "31500.0",
                "--poisson", "0.2",
                "--densita", "2.5e-9",
            ]
        )
        == 0
    )
    scritta = config.load_config(target)
    assert scritta.input.path.name == "nuvola.ply"
    assert scritta.analysis.material.name == "CALCESTRUZZO_C25_30"
    assert scritta.analysis.material.young == pytest.approx(31500.0)


def test_init_refuses_to_invent_a_material(capsys):
    """Senza materiale dichiarato `init` non scrive nulla: il programma non sceglie al posto tuo."""
    with pytest.raises(SystemExit):
        cli.main(["init", "config.yaml", "--input", "nuvola.ply"])
    assert "--materiale" in capsys.readouterr().err


def test_run_executes_the_pipeline_and_writes_the_deck(tmp_path):
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))
    cfg = crea_config(
        input=config.InputConfig(path=cloud_path, spacing_sample=2000),
        downsample=config.DownsampleConfig(voxel_size=8.0),
        surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
        # to_step=12: il test verifica che il comando run scriva il deck
        # (step 11), non che risolva -- stessa ragione di _config_cubo_su_disco.
        run=config.RunConfig(out_dir=tmp_path / "out", to_step=12),
    )
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 0
    assert (tmp_path / "out" / "wall_model.inp").exists()


def test_from_step_overrides_the_configuration(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cfg):
        seen["from_step"] = cfg.run.from_step
        return {}

    # Sul modulo e non su `cli.pipeline`: `cli` importa `pipeline` dentro il
    # ramo che lo usa e non piu' in testa al file, cosi' `meshrec dottore` --
    # che serve proprio quando una dipendenza e' rotta -- non muore all'import
    # di open3d.
    monkeypatch.setattr("meshrec.core.pipeline.run", fake_run)
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "5"]) == 0
    assert seen["from_step"] == 5


def test_a_failing_run_reports_the_error_without_a_traceback(tmp_path, capsys):
    cfg = crea_config(input=config.InputConfig(path=tmp_path / "assente.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 1
    err = capsys.readouterr().err
    assert "nessun punto letto" in err
    assert "Traceback" not in err


def test_from_step_out_of_domain_is_rejected_by_pydantic_not_a_keyerror(tmp_path, capsys):
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "10"]) == 1
    err = capsys.readouterr().err
    assert "KeyError" not in err
    assert "from_step" in err


def test_run_config_rejects_an_out_of_domain_assignment(tmp_path):
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
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
    base = crea_config(
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


def test_only_step_esegue_soltanto_quello(tmp_path, capsys):
    from meshrec import cli

    percorso = _config_cubo_su_disco(tmp_path)   # helper gia' presente nel file
    assert cli.main(["run", str(percorso), "--only-step", "1"]) == 0
    uscita = json.loads(capsys.readouterr().out)
    assert set(uscita) == {"01_load"}


def test_uno_step_parte_anche_se_il_config_su_disco_e_gia_ristretto(tmp_path):
    """E' il caso del worker: ogni step passa da qui, e la configurazione sul
    disco puo' portare un to_step piu' piccolo dello step che si chiede."""
    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.to_step = 1
    config.save_config(cfg, percorso)

    assert cli.main(["run", str(percorso), "--only-step", "1"]) == 0
    assert cli.main(["run", str(percorso), "--from-step", "2", "--to-step", "2"]) == 0


def test_uno_step_parte_anche_se_il_config_su_disco_parte_piu_avanti(tmp_path):
    """L'altro verso dello stesso invariante, trovato usando il pannello.

    Dopo un "esegui da qui in giu'" dallo step 4 la configurazione sul disco
    porta from_step=4. Chiedere poi lo step 1 assegnava to_step=1 su uno stato
    che aveva ancora from_step=4, e la corsa moriva con un ValidationError che
    l'interfaccia non mostrava.
    """
    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.to_step = 11
    cfg.run.from_step = 4
    config.save_config(cfg, percorso)

    assert cli.main(["run", str(percorso), "--only-step", "1"]) == 0
    assert cli.main(["run", str(percorso), "--from-step", "1", "--to-step", "1"]) == 0


def test_the_sweep_command_reports_the_thickness_gate_failure(tmp_path, capsys):
    """Il cancello sulla misura di spessore ferma lo sweep prima di partire.

    L'uscita e' 1 e il messaggio del cancello compare su stderr: che dica
    perche' si ferma conta quanto il fatto che si fermi.
    """
    import yaml

    from meshrec.core import config, io, synth

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    base = crea_config(
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


def test_il_comando_wall_ricalcola_il_solo_prior(tmp_path, capsys):
    """Il prior e' un'azione e non una ripresa: legge l'artefatto dello step 2
    gia' sul disco e non rifa' nulla di cio' che sta a monte."""
    import json

    from meshrec.core import pipeline

    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.to_step = 2
    config.save_config(cfg, percorso)
    pipeline.run(cfg)

    assert cli.main(["wall", str(percorso)]) == 0

    scritto = json.loads(
        (cfg.run.out_dir / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert "membrature" in scritto
    assert json.loads(capsys.readouterr().out)["regioni_trovate"] == scritto["regioni_trovate"]


def test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca(tmp_path, capsys):
    """Chi arriva dopo non conosce gli step: l'errore dice quale artefatto
    manca e come ottenerlo, non solo che un file non c'e'."""
    percorso = _config_cubo_su_disco(tmp_path)

    assert cli.main(["wall", str(percorso)]) == 1
    assert "02_segmented.ply" in capsys.readouterr().err


def test_il_comando_model_scrive_la_cartella_col_suffisso_del_tipo(tmp_path):
    """La cartella predefinita e' quella della madre col suffisso: nessuna
    corsa figlia scrive dentro la cartella della madre, che e' il risultato di
    un'altra elaborazione.

    Mutazione che deve morire: in `cli.main`, cambiare
    `madre.with_name(f"{madre.name}-{args.tipo}")` in `madre` (nessun
    suffisso) -- la seconda asserzione noterebbe `modello.json` scritto nella
    cartella della madre.
    """
    from meshrec.core import pipeline

    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    pipeline.run(cfg)

    assert cli.main(["model", str(percorso), "--tipo", "primitive"]) == 0

    madre = cfg.run.out_dir
    figlia = madre.with_name(f"{madre.name}-primitive")
    assert (figlia / "wall_model.inp").exists()
    assert not (madre / pipeline.MODEL_FILENAME).exists()


def test_il_comando_model_senza_il_prior_dice_che_cosa_manca(tmp_path, capsys):
    """Gemello di `test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca`:
    il ramo d'errore del comando `model` non aveva copertura. `genera_modello`
    solleva `FileNotFoundError` ed e' testata direttamente in
    `test_pipeline.py`, ma nulla provava che `cli.main` la catturi ancora, con
    lo stesso codice d'uscita e lo stesso testo su stderr.

    Mutazione che deve morire: nel ramo `model` di `cli.main`, rimuovere il
    `try/except` (o farlo rilanciare invece di stampare e restituire 1) --
    `cli.main` solleverebbe l'eccezione invece di restituire 1, e la prima
    asserzione fallirebbe.
    """
    percorso = _config_cubo_su_disco(tmp_path)

    assert cli.main(["model", str(percorso), "--tipo", "estruso"]) == 1
    assert "12_wall.json" in capsys.readouterr().err


def test_il_comando_compare_scrive_la_pagina_e_nomina_i_modelli_assenti(tmp_path, capsys):
    """Stesso banco di test_report.py: una definizione sola in materiale.py,
    perche' tests/ non e' un pacchetto e un import fra file di test per nome
    puntato non risolverebbe."""
    cartelle = _tre_cartelle_finte(tmp_path)[:2]
    uscita = tmp_path / "confronto.html"

    assert cli.main(["compare", *[str(c) for c in cartelle], "--out", str(uscita)]) == 0
    assert "non generato" in uscita.read_text(encoding="utf-8")
    assert str(uscita) in capsys.readouterr().out


def _config_con_solutore(tmp_path, monkeypatch, nome, percorso=None):
    """Una configurazione che porta il blocco `solutore`, senza passare dal file.

    Il blocco lo dichiara l'onda 0 della Fase 8 e in `PipelineConfig` non c'e'
    ancora: `_ModelloBase` vieta i campi ignoti, quindi scriverlo nel YAML lo
    farebbe rifiutare a caricamento. Si sostituisce quindi `load_config`, cosi'
    il test prova `dottore` contro la forma dichiarata -- `cfg.solutore.nome` e
    `cfg.solutore.percorso` -- invece che contro lo schema di oggi.
    """
    percorso_yaml = tmp_path / "c.yaml"
    percorso_yaml.write_text("segnaposto\n", encoding="utf-8")

    class _Cfg:
        solutore = _SolutoreFinto(nome=nome, percorso=percorso)

    monkeypatch.setattr(cli, "load_config", lambda _p: _Cfg())
    return percorso_yaml


# --- `meshrec dottore` (#144, sottocomando: vedi §8.3 del sequenziamento) -----
from pathlib import Path  # noqa: E402
from typing import NamedTuple  # noqa: E402

from meshrec.core import solve  # noqa: E402


class _SolutoreFinto(NamedTuple):
    nome: str = "calculix"
    percorso: Path | None = None


def _niente_installato(monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)


def _solo_calculix(monkeypatch):
    monkeypatch.setattr(
        solve.shutil, "which", lambda nome: "/usr/bin/ccx" if nome == "ccx" else None
    )
    monkeypatch.setattr(
        solve.subprocess, "run",
        lambda *_a, **_k: _ProcessoFinto(201, b"This is Version 2.21\n", b""),
    )


class _ProcessoFinto(NamedTuple):
    returncode: int
    stdout: bytes
    stderr: bytes


def test_dottore_senza_nessun_solutore_lo_dice_e_nomina_cosa_scaricare(monkeypatch, capsys):
    _niente_installato(monkeypatch)

    codice = cli.main(["dottore"])

    uscita = capsys.readouterr().out
    assert codice == 1, "senza nessun solutore non si può risolvere niente"
    assert "dhondt.de" in uscita
    assert "opensees.berkeley.edu" in uscita


def test_dottore_con_solo_calculix_e_calculix_scelto_e_verde(tmp_path, monkeypatch, capsys):
    _solo_calculix(monkeypatch)
    percorso = _config_con_solutore(tmp_path, monkeypatch, "calculix")

    codice = cli.main(["dottore", str(percorso)])

    uscita = capsys.readouterr().out
    assert codice == 0
    assert "ccx" in uscita
    # OpenSees assente e non scelto: non è un errore, ed è scritto che va bene
    assert "va bene se non lo usi" in uscita


def test_dottore_con_solo_calculix_e_opensees_scelto_e_rosso(tmp_path, monkeypatch, capsys):
    _solo_calculix(monkeypatch)
    percorso = _config_con_solutore(tmp_path, monkeypatch, "opensees")

    codice = cli.main(["dottore", str(percorso)])

    uscita = capsys.readouterr().out
    assert codice == 1
    assert "opensees.berkeley.edu" in uscita


def test_dottore_dichiara_un_percorso_che_non_esiste_invece_di_tacerlo(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    inesistente = tmp_path / "Program Files" / "città" / "ccx.exe"
    percorso = _config_con_solutore(
        tmp_path, monkeypatch, "calculix", percorso=inesistente
    )

    codice = cli.main(["dottore", str(percorso)])

    uscita = capsys.readouterr().out
    assert codice == 1
    assert str(inesistente) in uscita
    assert "non ripiega sul PATH" in uscita


def test_dottore_su_una_configurazione_che_non_esiste_non_mostra_lo_stack(tmp_path, capsys):
    codice = cli.main(["dottore", str(tmp_path / "manca.yaml")])

    assert codice == 1
    assert "Traceback" not in capsys.readouterr().err
