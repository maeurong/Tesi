"""Verifica di Fase 1: il parallelepipedo a soluzione nota attraversa tutta la catena."""

import json

import numpy as np
import pytest
from pydantic import ValidationError

from meshrec.core import config, io, pipeline, quality, solve, steps, synth
from materiale import ANALISI, MATERIALE, crea_config


SIZE = (120.0, 60.0, 240.0)
SPACING = 4.0
EXACT_VOLUME = 120.0 * 60.0 * 240.0


def _config_cubo(tmp_path):
    """Configurazione del cubo di prova, la stessa della fixture run_dir.

    `to_step=12` esplicito: dalla Fase 5 il predefinito di RunConfig e' 13
    (il solutore fa parte di ogni corsa, decisione dell'utente), ma questo
    banco serve gran parte della suite per esercitare l'elaborazione
    geometrica (1-12), non il solutore -- e su una macchina con `ccx`
    installato lasciarlo al predefinito farebbe girare un processo esterno
    vero a ogni singola chiamata. Stessa ragione, stesso numero, di
    `sweep.run_candidate`."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))
    return config.PipelineConfig(
        analysis=ANALISI,
        input=config.InputConfig(path=cloud_path, spacing_sample=5000),
        downsample=config.DownsampleConfig(voxel_size=SPACING),
        surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
        tet=config.TetConfig(min_ratio=1.2),
        run=config.RunConfig(out_dir=tmp_path / "out", to_step=12),
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
    """Esegue la pipeline una volta sola: e' il test piu lento della suite.

    `to_step=12`: questa fixture serve i test sui passi 1-11 (superficie,
    volume, deck), non il solutore -- stessa ragione di `_config_cubo`."""
    pytest.importorskip("pymeshfix")
    base = tmp_path_factory.mktemp("run")
    cloud_path = base / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))

    cfg = crea_config(
        input=config.InputConfig(path=cloud_path, spacing_sample=5000),
        downsample=config.DownsampleConfig(voxel_size=SPACING),
        surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
        tet=config.TetConfig(min_ratio=1.2),
        run=config.RunConfig(out_dir=base / "out", to_step=12),
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
            run=config.RunConfig(out_dir=tmp_path / name, to_step=12),
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
            run=config.RunConfig(out_dir=tmp_path / "out", from_step=from_step, to_step=12),
        )

    pipeline.run(makecfg(1))
    resumed = pipeline.run(makecfg(9))
    assert resumed["09_tetrahedralize"]["nodes"] > 0
    assert resumed["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)


def test_una_corsa_completa_lascia_i_dodici_step_di_elaborazione_validi(tmp_path):
    """Dal Task 9 (Fase 4) lo step 12 (prior geometrico) e' parte della corsa
    madre: una corsa intera non lascia piu' nulla di "mai eseguito" nel nucleo
    di elaborazione. Lo step 13 (solutore, Fase 5) qui resta "mai eseguito"
    perche' `_config_cubo` fissa `to_step=12` (vedi il suo docstring): il
    predefinito vero di RunConfig e' 13, provato altrove
    (test_lo_step_13_gira_per_difetto_in_una_corsa_intera)."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    stato = steps.run_state(cfg.run.out_dir, cfg)
    per_numero = {voce["numero"]: voce["stato"] for voce in stato}
    assert all(per_numero[n] == "valido" for n in range(1, 13))
    assert per_numero[13] == "mai eseguito"


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


def test_lo_step_13_gira_per_difetto_in_una_corsa_intera(tmp_path, monkeypatch):
    """Decisione dell'utente all'apertura della Fase 5 (scelta 2 fra le tre
    proposte, scartata la 3 -- step opzionale acceso dalla configurazione):
    ogni corsa risolve e scrive spostamenti e tensioni accanto alle altre
    metriche, non e' un'azione a parte da chiedere. `RunConfig.to_step` e'
    quindi predefinito a 13, non 12.

    Qui il predefinito *bare*: `_config_cubo` lo fissa esplicitamente a 12
    per il resto della suite (vedi il suo docstring), quindi questo test
    ricostruisce `cfg.run` senza quella fissazione, sugli stessi artefatti
    geometrici. Senza `ccx` (simulato, cosi' la suite principale non dipende
    da un solutore installato sulla macchina) l'esito resta negativo e
    documentato, ma la chiave `13_solve` compare comunque -- e' questo il
    punto: nessuno l'ha chiesta esplicitamente."""
    from meshrec.core import pipeline

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)
    cfg = _config_cubo(tmp_path)
    cfg.run = config.RunConfig(out_dir=cfg.run.out_dir)
    assert cfg.run.to_step == 13, "il predefinito bare di RunConfig deve restare 13"

    metriche = pipeline.run(cfg)

    assert metriche["13_solve"] == {"eseguito": False, "solutore": "assente"}


def test_lo_step_13_con_to_step_esplicito_non_dichiara_un_artefatto_assente(
    tmp_path, monkeypatch
):
    """Stesso esito del test sopra, ma chiesto esplicitamente con
    `to_step=13` invece di ereditarlo dal predefinito -- e' la via che
    l'interfaccia userebbe per rieseguire il solo step 13 su una corsa gia'
    fatta fino all'undici. Senza `ccx` (simulato) l'esito e' negativo e
    `registra()` non deve dichiarare un artefatto che non esiste."""
    from meshrec.core import pipeline

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)
    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 13

    metriche = pipeline.run(cfg)

    assert metriche["13_solve"] == {"eseguito": False, "solutore": "assente"}
    stato = {voce["chiave"]: voce for voce in steps.run_state(cfg.run.out_dir, cfg)}
    assert stato["13_solve"]["stato"] == "valido"
    assert stato["13_solve"]["artefatto"] is None


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


def test_la_corsa_figlia_ha_cartella_configurazione_deck_e_metriche_proprie(tmp_path):
    """Ogni modello e' la propria cartella: la provenienza e' parte del
    risultato, e un modello senza la configurazione che lo ha prodotto non e'
    ricostruibile a distanza di mesi.

    Mutazione che deve morire: cancellare `save_config(cfg, out / "config.yaml")`
    in `genera_modello` -- la prima asserzione non troverebbe piu' il file.
    """
    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-estruso"

    esito = pipeline.genera_modello(cfg, "estruso", figlia)

    assert (figlia / "config.yaml").exists()
    assert (figlia / "wall_model.inp").exists()
    assert (figlia / pipeline.MODEL_FILENAME).exists()
    assert esito["tipo"] == "estruso"
    assert esito["sorgente"] == str(cfg.run.out_dir)
    assert esito["hexa"]["hexes"] > 0
    assert esito["hexa"]["inverted"] == 0


def test_lo_scostamento_dalla_nuvola_prende_i_nodi_e_la_nuvola_giusti(tmp_path):
    """Giro di correzione 2: questo test **non verifica l'aritmetica** di
    `quality.vertex_deviation` -- e' gia' protetta altrove (mutare
    `quality.py:469` uccide quattro test in `tests/test_quality.py`, fra cui
    `test_su_una_calotta_il_campionamento_dei_soli_vertici_sottostima_l_errore`).
    Verifica solo il **cablaggio**: che `esito["scostamento_nuvola"]` venga
    davvero dai nodi del modello e dalla nuvola segmentata della madre, e non
    da qualcos'altro o da nessuna parte. Ricostruisce qui, indipendentemente,
    nodi e nuvola dagli stessi file su disco e ricalcola, invece di rileggere
    il numero che `genera_modello` ha appena scritto.

    Mutazione che deve morire (quella del giro di correzione 1): rinominare la
    chiave `"scostamento_nuvola"` in `genera_modello`, per esempio in
    `"scostamento_nuvola_assente"` -- il primo accesso a
    `esito["scostamento_nuvola"]` solleva `KeyError`.
    """
    from meshrec.core import hexa

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)

    esito = pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")

    with (cfg.run.out_dir / pipeline.WALL_FILENAME).open(encoding="utf-8") as handle:
        prior = json.load(handle)
    membrature = pipeline._ricostruisci_membrature(prior)
    modello_indipendente = hexa.costruisci(membrature, "estruso", cfg.model)
    nuvola, _ = io.read_cloud(cfg.run.out_dir / pipeline.ARTIFACTS[2])
    scarti = quality.vertex_deviation(modello_indipendente["nodi"], nuvola)

    scostamento = esito["scostamento_nuvola"]
    assert scostamento["rms"] == pytest.approx(float(np.sqrt(np.mean(scarti ** 2))))
    assert scostamento["max"] == pytest.approx(float(scarti.max()))
    assert scostamento["rms"] >= 0.0


def test_lo_scostamento_dalla_nuvola_e_esatto_su_una_nuvola_spostata_di_una_distanza_nota(tmp_path):
    """Geometria di risposta nota, calcolata su carta prima di eseguire il
    codice: la nuvola sorgente e' i nodi del modello, gli stessi che
    `genera_modello` ricostruira' internamente dallo stesso prior, spostati di
    un offset costante lungo x. L'offset (0,001 mm) e' molto sotto il passo di
    mesh del cubo di prova (~20 mm, vedi `hexa.passo_di_mesh`): nessun nodo
    spostato puo' essere piu' vicino al proprio vicino del proprio gemello
    spostato. Quindi ogni nodo ha distanza esatta `offset` dal punto piu'
    vicino della nuvola, e per un campione a valore costante RMS = max =
    offset, per definizione, senza bisogno di eseguire nulla per saperlo.

    Mutazione che deve morire: `distanze * 2.0` in
    `quality.vertex_deviation` (`quality.py:469`, quella del revisore) -- RMS
    e max uscirebbero il doppio dell'offset atteso.
    """
    from meshrec.core import hexa

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)

    with (cfg.run.out_dir / pipeline.WALL_FILENAME).open(encoding="utf-8") as handle:
        prior = json.load(handle)
    membrature = pipeline._ricostruisci_membrature(prior)
    nodi = hexa.costruisci(membrature, "estruso", cfg.model)["nodi"]

    offset = 0.001
    nuvola_nota = nodi + np.array([offset, 0.0, 0.0])
    io.write_cloud(cfg.run.out_dir / pipeline.ARTIFACTS[2], nuvola_nota)

    esito = pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia-nota")

    assert esito["scostamento_nuvola"]["rms"] == pytest.approx(offset, abs=1e-9)
    assert esito["scostamento_nuvola"]["max"] == pytest.approx(offset, abs=1e-9)


def test_il_deck_della_corsa_figlia_e_esaedrico(tmp_path):
    """Mutazione che deve morire: scambiare `cfg.model.element` con `cfg.tet.element`
    nella chiamata a `abaqus.export_model` dentro `genera_modello` -- il deck
    tornerebbe a scrivere C3D4, e la prima asserzione fallirebbe."""
    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-primitive"

    pipeline.genera_modello(cfg, "primitive", figlia)

    testo = (figlia / "wall_model.inp").read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I" in testo
    assert "TYPE=C3D4" not in testo


_TELAIO_QUATTRO_MEMBRATURE = [
    ((0.0, -90.0, 0.0), (200.0, 180.0, 1600.0)),
    ((1400.0, -130.0, 0.0), (200.0, 260.0, 1600.0)),
    ((0.0, -70.0, 1600.0), (1600.0, 140.0, 300.0)),
    ((0.0, -170.0, -300.0), (1600.0, 340.0, 300.0)),
]
"""Stesso telaio sintetico di tests/test_wall.py:33-38 e tests/feasibility/test_calculix.py.

I numeri del banco stanno qui, non in src/: e' la stessa convenzione gia'
seguita da test_calculix.py, che li duplica invece di importarli da un altro
file di test."""

_TELAIO_A_SEZIONE_UNIFORME = [
    ((0.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),
    ((1400.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),
    ((0.0, 0.0, 1600.0), (1600.0, 200.0, 300.0)),
    ((0.0, 0.0, -300.0), (1600.0, 200.0, 300.0)),
]
"""Stesso telaio di tests/test_wall.py:442-445 (TELAIO_A_SEZIONE_UNIFORME): le
quattro sezioni uguali fondono la scomposizione in un'unica regione a Π, che
il riempimento dichiara «vuoto» e affidabile (vedi
test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata in
quel file) senza scartarla -- il rifiuto spetta a chi costruisce."""

_SPAZIATURA_TELAIO = 20.0


def _scrivi_prior_telaio(cfg, telaio, spaziatura=_SPAZIATURA_TELAIO):
    """Scrive `02_segmented.ply` e `12_wall.json` per un telaio sintetico, senza
    passare per `pipeline.run` (che su un telaio costerebbe Poisson piu'
    TetGen): chiama `wall.prior` direttamente, come il codice vero lo produce."""
    from meshrec.core import wall

    punti = synth.sample_frame_surface(telaio, spaziatura)
    out = cfg.run.out_dir
    out.mkdir(parents=True, exist_ok=True)
    io.write_cloud(out / pipeline.ARTIFACTS[2], punti)
    esito_prior = wall.prior(punti, cfg.segment, cfg.wall, spaziatura)
    (out / pipeline.WALL_FILENAME).write_text(
        json.dumps(esito_prior, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
    )
    return esito_prior


def test_il_deck_della_corsa_figlia_porta_le_superfici_e_i_tie(tmp_path):
    """Il cubo di `_config_cubo` da' una sola membratura, quindi zero
    giunzioni: le superfici e i `*TIE` si vedono solo su un telaio.

    Mutazione che deve morire: rimuovere `element_surfaces=modello["superfici"]`
    dalla chiamata a `abaqus.export_model` in `genera_modello` -- il deck non
    scriverebbe piu' `*SURFACE` e la prima asserzione fallirebbe.
    """
    cfg = _config_cubo(tmp_path)
    _scrivi_prior_telaio(cfg, _TELAIO_QUATTRO_MEMBRATURE)
    figlia = tmp_path / "figlia-telaio"

    pipeline.genera_modello(cfg, "estruso", figlia)

    testo = (figlia / "wall_model.inp").read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT" in testo
    assert "*TIE" in testo


def test_il_modello_json_porta_nota_giunzioni_e_conteggio_nodi_dipendenti(tmp_path):
    """C2 e C7: la nota sul `*TIE` e i due conteggi dei nodi dipendenti sono
    cio' che rende leggibile, nel confronto del Task 12, quanta della
    cedevolezza del parametrico viene dal vincolo e non dalla geometria. Un
    telaio a quattro membrature ha giunzioni vere, quindi nodi dipendenti
    diversi da zero: sul cubo di `_config_cubo` questo controllo sarebbe
    vuoto per costruzione (zero giunzioni) e non proverebbe nulla.

    Mutazione che deve morire (giro di correzione 2): sostituire il testo
    vero di `nota_giunzioni` con `"placeholder"` -- non vuoto, ma non dice
    nulla sul `*TIE`, quindi un'asserzione di sola non-vuotezza non lo vede.
    Cercare `"*TIE"` nel testo lo vede.
    """
    cfg = _config_cubo(tmp_path)
    _scrivi_prior_telaio(cfg, _TELAIO_QUATTRO_MEMBRATURE)

    esito = pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia-telaio")

    assert "*TIE" in esito["nota_giunzioni"]
    legati = esito["modello"]["nodi_dipendenti_legati"]
    totali = esito["modello"]["nodi_dipendenti_totali"]
    assert totali > 0, "il telaio a quattro membrature ha giunzioni vere: il denominatore non puo' essere zero"
    assert 0 <= legati <= totali


def test_la_ricostruzione_legge_riempimento_sezione_e_densita_dispersione_dalle_chiavi_giuste(tmp_path):
    """Giro di correzione 2: dei quindici campi di `Membratura`, dodici sono
    presi 1:1 dal JSON del prior e tre stanno annidati sotto `"riempimento"`.
    `riempimento_stato` e' gia' protetto dalla guardia del Ruling J (vedi
    sotto); `riempimento_sezione` e `densita_dispersione` no, perche' oggi
    nessuna funzione a valle li legge da una `Membratura` -- solo lo stato
    alimenta la guardia. Questo test chiude quel divario leggendo
    direttamente il risultato di `pipeline._ricostruisci_membrature`, invece
    di aspettare un consumatore a valle che oggi non esiste.

    Mutazione che deve morire (quella del revisore): leggere
    `riempimento_sezione` da `voce["riempimento"]["soglia"]` invece che da
    `["valore"]` -- sul cubo di prova le due chiavi hanno valori diversi (la
    soglia e' un parametro di configurazione, il valore e' la misura), quindi
    la prima asserzione fallirebbe.
    """
    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    with (cfg.run.out_dir / pipeline.WALL_FILENAME).open(encoding="utf-8") as handle:
        prior = json.load(handle)

    membrature = pipeline._ricostruisci_membrature(prior)

    voce = prior["membrature"][0]
    membratura = membrature[0]
    assert voce["riempimento"]["valore"] != voce["riempimento"]["soglia"], (
        "il banco deve dare due chiavi con valori diversi, o la mutazione non e' rilevabile"
    )
    assert membratura.riempimento_sezione == pytest.approx(voce["riempimento"]["valore"])
    assert membratura.densita_dispersione == pytest.approx(voce["riempimento"]["densita_dispersione"])
    assert membratura.riempimento_stato == voce["riempimento"]["stato"]


def test_la_guardia_del_ruling_j_rifiuta_una_membratura_vuota_dal_percorso_reale(tmp_path):
    """C1: `riempimento_stato` letto male dalla ricostruzione della `Membratura`
    lascerebbe muta la guardia di `hexa.costruisci` che rifiuta una sezione a
    Π. Il telaio a sezioni uguali fonde la scomposizione in un'unica regione
    che il riempimento dichiara «vuoto» e affidabile (vedi
    `test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata`
    in tests/test_wall.py): e' il percorso reale, non uno stato costruito a
    mano nel test.

    Mutazione che deve morire: in `genera_modello`, forzare
    `riempimento_stato="pieno"` invece di leggerlo da
    `voce["riempimento"]["stato"]` -- la guardia non scatterebbe piu' e
    `pytest.raises` non troverebbe l'eccezione.
    """
    cfg = _config_cubo(tmp_path)
    esito_prior = _scrivi_prior_telaio(cfg, _TELAIO_A_SEZIONE_UNIFORME)
    assert esito_prior["regioni_trovate"] == 1, "il banco deve restare il caso limite: una regione a Π sola"
    assert esito_prior["membrature"][0]["riempimento"]["stato"] == "vuoto"
    assert esito_prior["membrature"][0]["riempimento"]["affidabile"] is True

    with pytest.raises(ValueError, match="riempimento di sezione «vuoto»"):
        pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia-vuota")


def test_una_corsa_figlia_fallita_non_lascia_una_cartella_orfana(tmp_path):
    """F1: se `hexa.costruisci` solleva, la cartella figlia non deve restare
    con dentro il solo `config.yaml` -- /api/compare la includerebbe (e' una
    directory), non ci troverebbe ne' `modello.json` ne' `12_wall.json`, e la
    rifiuterebbe con lo stesso errore che oggi si legge alla prima apertura
    della pagina (vedi `report.confronta`).

    Mutazione che deve morire: in `genera_modello`, richiamare `save_config`
    prima di `hexa.costruisci` invece che dopo -- la cartella figlia
    conterrebbe `config.yaml` anche quando la generazione fallisce.
    """
    cfg = _config_cubo(tmp_path)
    esito_prior = _scrivi_prior_telaio(cfg, _TELAIO_A_SEZIONE_UNIFORME)
    assert esito_prior["membrature"][0]["riempimento"]["stato"] == "vuoto"

    figlia = tmp_path / "figlia-fallita"
    with pytest.raises(ValueError, match="riempimento di sezione «vuoto»"):
        pipeline.genera_modello(cfg, "estruso", figlia)

    assert not (figlia / "config.yaml").exists()


def test_la_corsa_madre_non_cambia_quando_si_genera_un_modello(tmp_path):
    """La selezione e' un'azione e non un parametro: se toccasse la
    configurazione della madre, rigenerare un modello in piu' cambierebbe
    l'impronta di una corsa che non e' cambiata.

    Il solo confronto testuale non basta: `save_config` e' deterministica,
    quindi riscrivere `config.yaml` della madre con lo stesso `cfg` invariato
    produrrebbe un testo bit-identico, e la mutazione piu' ovvia (scrivere su
    `sorgente / "config.yaml"` invece che su `out / "config.yaml"`, senza
    toccare `cfg`) passerebbe inosservata. Il tempo di modifica del file
    cambia a ogni scrittura, che ne cambi o no il contenuto: e' il sensore
    che il confronto testuale non e'.

    Mutazione che deve morire (giro di correzione 2): `save_config(cfg, out /
    "config.yaml")` -> `save_config(cfg, sorgente / "config.yaml")` in
    `genera_modello`, senza mutare `cfg` -- il testo resta identico ma il
    tempo di modifica del file della madre cambia, e la terza asserzione lo
    nota.
    """
    from meshrec.core.sweep import fingerprint

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    percorso_madre = cfg.run.out_dir / "config.yaml"
    prima = percorso_madre.read_text(encoding="utf-8")
    mtime_prima = percorso_madre.stat().st_mtime_ns
    impronta = fingerprint(cfg)

    figlia = tmp_path / "figlia"
    pipeline.genera_modello(cfg, "estruso", figlia)

    assert (figlia / "config.yaml").exists()
    assert percorso_madre.read_text(encoding="utf-8") == prima
    assert percorso_madre.stat().st_mtime_ns == mtime_prima, "config.yaml della madre e' stato riscritto"
    assert fingerprint(config.load_config(percorso_madre)) == impronta


def test_generare_un_modello_senza_prior_dice_che_cosa_manca(tmp_path):
    """Mutazione che deve morire: in `genera_modello`, cambiare il messaggio
    dell'eccezione sollevata quando manca `12_wall.json` togliendo il nome
    del file dal testo (per esempio `"manca il prior geometrico"` invece di
    citare `percorso_prior`) -- il `match` sotto smetterebbe di trovarlo."""
    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 11
    pipeline.run(cfg)

    with pytest.raises(FileNotFoundError, match="12_wall.json"):
        pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")
