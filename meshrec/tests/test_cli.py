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

    `to_step=12` esplicito: non coincide col predefinito di RunConfig, che dal
    perimetro del prodotto vale 11, e questi test esercitano il comando `run` e la ripresa, non il
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
    """13 e non 10: dal 30/08/2026 il tetto di `from_step` e' 12.

    Il valore era 10 perche' allora era il primo fuori dominio. Ora e' dentro,
    e con 10 questo test misurava un altro guasto -- l'artefatto mancante --
    invece del rifiuto di pydantic che gli da' il nome. Lo step 13 e' il primo
    fuori dominio oggi, e ci resta apposta: e' un'azione, non una ripresa.
    """
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "13"]) == 1
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


def _corsa_col_deck(tmp_path):
    """Una corsa portata fino al deck, che e' l'ingresso dello step 13."""
    from meshrec.core import pipeline

    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.to_step = 11
    config.save_config(cfg, percorso)
    pipeline.run(cfg)
    return percorso


def test_il_comando_solve_esegue_il_solo_step_13(tmp_path, capsys, monkeypatch):
    """Il solutore e' un'azione sugli artefatti presenti, come `wall`: non
    rifa' la pipeline e non ha bisogno di una ripresa.

    Il binario si finge utilizzabile e poi assente: cosi' il banco prova la
    strada intera -- riga di comando, `pipeline.risolvi_corsa`, `solve.risolvi`
    -- su una macchina che CalculiX non ce l'ha, che PRODUCT.md dichiara essere
    quella degli utenti successivi.
    """
    from meshrec.core import pipeline, solve

    percorso = _corsa_col_deck(tmp_path)
    monkeypatch.setattr(solve, "verifica", lambda _cfg: {"funziona": True, "solutore": "calculix"})
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)

    assert cli.main(["solve", str(percorso)]) == 0

    esito = json.loads(capsys.readouterr().out)
    assert esito["eseguito"] is False
    out = config.load_config(percorso).run.out_dir
    metriche = json.loads((out / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert metriche["13_solve"] == esito
    assert "11_export" in metriche


def test_il_comando_solve_senza_il_deck_dice_quale_step_lo_scrive(tmp_path, capsys):
    """Gemello di `test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca`:
    chi arriva dopo non conosce gli step, e un FileNotFoundError nudo non dice
    a nessuno che deve eseguire l'undici prima del tredici."""
    percorso = _config_cubo_su_disco(tmp_path)

    assert cli.main(["solve", str(percorso)]) == 1
    err = capsys.readouterr().err
    assert "wall_model.inp" in err
    assert "step 11" in err
    assert "--to-step 11" in err
    assert "Traceback" not in err


def test_il_comando_solve_su_una_cartella_che_non_esiste_lo_dichiara(tmp_path, capsys):
    """La cartella della corsa puo' non esserci affatto: e' lo stesso vuoto del
    deck mancante, e si dichiara con la stessa frase invece di cadere sul
    percorso."""
    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.out_dir = tmp_path / "mai-esistita"
    config.save_config(cfg, percorso)

    assert cli.main(["solve", str(percorso)]) == 1
    err = capsys.readouterr().err
    assert "step 11" in err
    assert "Traceback" not in err


def test_il_comando_solve_col_binario_assente_lo_dice_prima_di_cominciare(
    tmp_path, capsys, monkeypatch
):
    """`solve.verifica` esiste per questo: scoprirlo a meta' corsa vorrebbe
    dire aver gia' riletto il maglio. Il messaggio porta dove prendere il
    binario, che e' la sola cosa da fare per chi lo legge."""
    from meshrec.core import solve

    percorso = _corsa_col_deck(tmp_path)
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)

    assert cli.main(["solve", str(percorso)]) == 1
    err = capsys.readouterr().err
    assert solve.DOVE_PRENDERLO["calculix"] in err
    assert "Traceback" not in err


def test_il_comando_solve_riporta_codice_e_coda_di_un_binario_che_fallisce(
    tmp_path, capsys, monkeypatch
):
    """Il codice d'uscita non e' il segnale -- `ccx` esce 201 quando funziona --
    ma quando la verifica boccia, il codice e la coda di cio' che il binario ha
    scritto sono le due sole cose da cui si capisce perche'. Passano da
    `solve.verifica`, che le mette nel motivo, fino a video."""
    from meshrec.core import solve

    percorso = _corsa_col_deck(tmp_path)
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")

    class _Processo:
        returncode = 127
        stdout = b""
        stderr = b"error while loading shared libraries: libgomp.so.1\n"

    monkeypatch.setattr(solve.subprocess, "run", lambda *_a, **_k: _Processo())

    assert cli.main(["solve", str(percorso)]) == 1
    err = capsys.readouterr().err
    assert "127" in err
    assert "shared libraries" in err
    assert "Traceback" not in err


def test_il_comando_solve_su_opensees_chiede_il_prior_e_non_il_deck(
    tmp_path, capsys, monkeypatch
):
    """Il telaio non si costruisce sul deck dello step 11: si costruisce sul
    prior dello step 12. Chiedere `wall_model.inp` a chi risolve un telaio
    manderebbe a rifare l'undici per un file che quel ramo non apre.

    Questa corsa il prior non ce l'ha, e il rifiuto deve arrivare a video
    leggibile -- nominando `12_wall.json` e il comando che lo scrive -- non
    affiorare come un'eccezione nuda."""
    from meshrec.core import solve

    percorso = _corsa_col_deck(tmp_path)
    cfg = config.load_config(percorso)
    cfg.solutore = config.SolutoreConfig(nome="opensees")
    config.save_config(cfg, percorso)
    monkeypatch.setattr(solve, "verifica", lambda _cfg: {"funziona": True, "solutore": "opensees"})

    assert cli.main(["solve", str(percorso)]) == 1
    err = capsys.readouterr().err
    assert "12_wall.json" in err
    assert "meshrec wall" in err
    assert "Traceback" not in err


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


def test_la_porta_occupata_si_dice_prima_di_annunciare_l_ascolto(capsys):
    """Il difetto che ha fatto lavorare l'utente per ore sul codice vecchio.

    `serve` stampava «MeshRec in ascolto su ...» e apriva il browser PRIMA che
    uvicorn provasse il bind. Con la porta gia' occupata da un'altra copia
    rimasta viva, l'annuncio era falso e il browser si apriva su quella copia:
    l'utente vedeva l'interfaccia, la usava, e ogni correzione appena
    installata non era in quel processo.

    Il banco occupa davvero la porta con un socket, poi chiama `serve`.
    """
    import socket as _socket

    occupante = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    occupante.bind(("127.0.0.1", 0))
    porta = occupante.getsockname()[1]
    occupante.listen(1)
    try:
        codice = cli.main(["serve", "--port", str(porta), "--no-browser"])
    finally:
        occupante.close()

    assert codice == 1
    detto = capsys.readouterr().err
    assert f"la porta {porta} è già occupata" in detto
    assert "un'altra copia di MeshRec" in detto
    assert "--port" in detto
    # E soprattutto: non deve aver annunciato un ascolto che non c'e'.
    assert "in ascolto" not in detto


def test_un_errore_che_il_programma_non_ha_previsto_porta_la_propria_traccia(tmp_path, capsys):
    """Una riga sola non basta per un guasto che nessuno ha scritto.

    Misurato il 30/08/2026: `UnicodeDecodeError: 'utf-8' codec can't decode
    byte 0xe0 in position 79` e' arrivato all'utente senza dire quale file
    stesse leggendo. Senza la traccia non era diagnosticabile.

    Un `ValueError` resta invece una riga sola: e' il modo in cui questo
    programma parla all'operatore, e la traccia sopra lo seppellirebbe.
    """
    configurazione = tmp_path / "config.yaml"
    configurazione.write_bytes(b"input:\n  path: nuvola.ply\n  scale: 1.0\n")

    def esplode(_cfg):
        raise UnicodeDecodeError("utf-8", b"\xe0", 0, 1, "invalid continuation byte")

    import meshrec.core.pipeline as _pipeline

    originale = _pipeline.run
    _pipeline.run = esplode
    try:
        codice = cli.main(["run", str(configurazione)])
    finally:
        _pipeline.run = originale

    assert codice == 1
    detto = capsys.readouterr().err
    assert "UnicodeDecodeError" in detto
    assert "Traceback" in detto, "senza la traccia l'errore non dice che cosa leggeva"


def test_un_errore_scritto_dal_programma_resta_una_riga_sola(tmp_path, capsys):
    """La controprova: senza, basterebbe stampare sempre la traccia."""
    configurazione = tmp_path / "config.yaml"
    configurazione.write_bytes(b"input:\n  path: nuvola.ply\n  scale: 1.0\n")

    def rifiuta(_cfg):
        raise ValueError("la nuvola non ha punti: controlla input.path")

    import meshrec.core.pipeline as _pipeline

    originale = _pipeline.run
    _pipeline.run = rifiuta
    try:
        codice = cli.main(["run", str(configurazione)])
    finally:
        _pipeline.run = originale

    assert codice == 1
    detto = capsys.readouterr().err
    assert "controlla input.path" in detto
    assert "Traceback" not in detto
