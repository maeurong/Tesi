"""Verifica di Fase 1: il parallelepipedo a soluzione nota attraversa tutta la catena."""

import json

import numpy as np
import pytest
from pydantic import ValidationError

from meshrec.core import config, io, pipeline, quality, synth
from materiale import ANALISI, MATERIALE, crea_config


SIZE = (120.0, 60.0, 240.0)
SPACING = 4.0
EXACT_VOLUME = 120.0 * 60.0 * 240.0


def _config_cubo(tmp_path):
    """Configurazione del cubo di prova, la stessa della fixture run_dir."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))
    return config.PipelineConfig(
        analysis=ANALISI,
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


def test_una_corsa_piena_sostituisce_una_chiave_estranea_gia_sul_disco(tmp_path):
    """completa non puo' restare legata a stop == 11 scritto a mano: con
    RunConfig.to_step ora a 12 di default (Fase 4), una corsa piena dalla
    configurazione predefinita deve continuare a sostituire, non fondere,
    anche quando metrics.json porta gia' una chiave che questa corsa non
    riscrive. Con la condizione vecchia stop vale 12, completa risulta
    falso, e la chiave estranea sopravvive al posto di sparire.
    """
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    out = cfg.run.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"99_estranea": {"ok": True}}), encoding="utf-8"
    )

    pipeline.run(cfg)

    metriche = json.loads((out / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert "99_estranea" not in metriche


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

    cfg = crea_config(
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
    density = MATERIALE.density
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
        cfg = crea_config(
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

    def makecfg(from_step):
        return crea_config(
            input=config.InputConfig(path=cloud_path, spacing_sample=5000),
            downsample=config.DownsampleConfig(voxel_size=SPACING),
            surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
            simplify=config.SimplifyConfig(enabled=True, mode="decimate", target_faces=500),
            run=config.RunConfig(out_dir=tmp_path / "out", from_step=from_step),
        )

    pipeline.run(makecfg(1))
    resumed = pipeline.run(makecfg(9))
    assert resumed["09_tetrahedralize"]["nodes"] > 0
    assert resumed["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)


def test_una_corsa_completa_lascia_i_dodici_step_validi(tmp_path):
    """Dal Task 9 lo step 12 (prior geometrico) e' parte della corsa madre:
    una corsa intera non lascia piu' nulla di "mai eseguito"."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    stato = steps.run_state(cfg.run.out_dir, cfg)
    per_numero = {voce["numero"]: voce["stato"] for voce in stato}
    assert set(per_numero.values()) == {"valido"}
    assert all(per_numero[n] == "valido" for n in range(1, 13))


def test_cambiare_un_parametro_a_monte_invalida_gli_step_a_valle(tmp_path):
    """Prova a variabile unica sulla corsa vera, non sulle sole impronte."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    cfg.surface.poisson_depth = cfg.surface.poisson_depth - 1
    per_numero = {voce["numero"]: voce["stato"] for voce in steps.run_state(cfg.run.out_dir, cfg)}
    assert [per_numero[n] for n in (1, 2, 3, 4)] == ["valido"] * 4
    assert [per_numero[n] for n in (5, 6, 7, 8, 9, 10, 11)] == ["non valido"] * 7


def test_fermarsi_a_uno_step_non_esegue_quelli_dopo(tmp_path):
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 3
    metriche = pipeline.run(cfg)
    assert set(metriche) == {"01_load", "02_segment", "03_downsample"}
    per_numero = {voce["numero"]: voce["stato"] for voce in steps.run_state(cfg.run.out_dir, cfg)}
    assert per_numero[3] == "valido"
    assert per_numero[4] == "mai eseguito"


def test_to_step_non_puo_precedere_from_step(tmp_path):
    from meshrec.core.config import RunConfig

    with pytest.raises(ValueError):
        RunConfig(from_step=5, to_step=3)


def test_una_corsa_interrotta_registra_quale_step_si_e_rotto(tmp_path, monkeypatch):
    """Il ramo che scrive lo stato 'fallito' va provato su una corsa vera:
    e' un'affermazione scritta su disco, e finora nulla la smentiva."""
    from meshrec.core import pipeline, steps, surface

    cfg = _config_cubo(tmp_path)

    def esplode(*_argomenti, **_chiavi):
        raise RuntimeError("interruzione simulata dello step 3")

    monkeypatch.setattr(surface, "downsample", esplode)
    with pytest.raises(RuntimeError):
        pipeline.run(cfg)

    salvato = steps.read_state(cfg.run.out_dir)
    assert salvato["03_downsample"]["esito"] == "fallito"
    assert salvato["02_segment"]["esito"] == "riuscito"
    assert "04_normals" not in salvato


def test_gli_step_eseguiti_uno_alla_volta_accumulano_le_metriche(tmp_path):
    """L'interfaccia esegue uno step per volta: se ognuno sostituisse
    metrics.json, il pannello delle metriche perderebbe tutto cio' che sta a
    monte dello step aperto."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 1
    pipeline.run(cfg)

    # to_step prima di from_step: con validate_assignment=True ogni riga
    # rivalida l'intero modello, e assegnare from_step=2 mentre to_step e'
    # ancora 1 (il valore lasciato dalla corsa precedente) violerebbe il
    # vincolo to_step >= from_step su uno stato intermedio che non esiste
    # mai nella configurazione finale.
    cfg.run.to_step = 2
    cfg.run.from_step = 2
    unite = pipeline.run(cfg)

    assert set(unite) == {"01_load", "02_segment"}
    rilette = json.loads((cfg.run.out_dir / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert rilette == unite


def test_una_corsa_completa_arriva_allo_step_dodici(tmp_path):
    """Lo step 12 chiude la corsa madre: se non compare nelle metriche, il
    prior non e' stato calcolato e i modelli parametrici non hanno da cosa
    partire."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)

    metriche = pipeline.run(cfg)

    assert "12_wall" in metriche
    assert (cfg.run.out_dir / pipeline.WALL_FILENAME).exists()
    stato = steps.read_state(cfg.run.out_dir)
    assert stato["12_wall"]["esito"] == "riuscito"


def test_lo_step_dodici_si_puo_fermare_prima_con_to_step(tmp_path):
    """to_step=11 lascia la corsa dov'era prima della Fase 4: le corse gia'
    fatte restano riproducibili senza calcolare un prior che nessuno ha
    chiesto."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 11

    metriche = pipeline.run(cfg)

    assert "11_export" in metriche
    assert "12_wall" not in metriche
    assert not (cfg.run.out_dir / pipeline.WALL_FILENAME).exists()


def test_una_corsa_fermata_all_undici_non_si_dichiara_completa(tmp_path):
    """Il gemello di `test_una_corsa_piena_sostituisce_una_chiave_estranea...`,
    dall'altro lato del confine: una corsa intera SOSTITUISCE metrics.json, una
    corsa parziale ci si FONDE, ed e' la distinzione da cui dipende lo sweep
    della Fase 2.

    Serve perche' senza di lui spostare o non spostare `pipeline_completa =
    True` lascia la suite verde in entrambi i casi. La chiave estranea
    sopravvive solo se la corsa si e' considerata parziale: e' un controllo
    indiretto ma non circolare, perche' non rilegge il valore che vuole
    provare.
    """
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 11
    out = cfg.run.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"99_estranea": {"ok": True}}), encoding="utf-8"
    )

    pipeline.run(cfg)

    metriche = json.loads((out / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert "99_estranea" in metriche


def test_il_prior_scritto_su_disco_e_quello_che_le_metriche_dichiarano(tmp_path):
    """La provenienza e' parte del risultato: il file e le metriche non possono
    raccontare due storie diverse dello stesso calcolo."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    metriche = pipeline.run(cfg)

    scritto = json.loads(
        (cfg.run.out_dir / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert scritto["regioni_trovate"] == metriche["12_wall"]["regioni_trovate"]
    assert len(scritto["membrature"]) == len(metriche["12_wall"]["membrature"])
