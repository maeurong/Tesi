"""Il motore di sweep: impronta, griglia, registro, dominanza."""

from pathlib import Path

import pytest

from meshrec.core import config, sweep


def _base() -> config.PipelineConfig:
    return config.PipelineConfig(input=config.InputConfig(path="nuvola.ply", scale=1000.0))


def test_the_fingerprint_ignores_where_the_run_is_written():
    """out_dir e from_step non cambiano il risultato, quindi non cambiano l'identita'.

    Includerli renderebbe diverse due corse identiche, che e' esattamente cio'
    che l'impronta esiste per impedire.
    """
    here = _base()
    elsewhere = _base()
    elsewhere.run.out_dir = Path("runs/altrove")
    elsewhere.run.from_step = 9

    assert sweep.fingerprint(here) == sweep.fingerprint(elsewhere)


def test_the_fingerprint_changes_with_any_processing_parameter():
    changed = sweep.with_override(_base(), "tet.min_ratio", 2.5)

    assert sweep.fingerprint(changed) != sweep.fingerprint(_base())
    assert changed.tet.min_ratio == pytest.approx(2.5)
    assert _base().tet.min_ratio == pytest.approx(1.8)


def test_one_axis_at_a_time_does_not_multiply_the_levels():
    """Tre livelli su due assi sono cinque candidati, non nove: uno per livello piu la base."""
    experiment = config.ExperimentConfig(
        name="prova",
        base=Path("muro.yaml"),
        axes=[
            config.AxisSpec(path="tet.min_ratio", values=[1.7, 1.8, 2.0]),
            config.AxisSpec(path="surface.poisson_depth", values=[8, 9, 10]),
        ],
    )

    candidates = sweep.expand(experiment, _base())

    assert len(candidates) == 5
    assert len({sweep.fingerprint(cfg) for _, cfg in candidates}) == 5
    assert any(axes == {} for axes, _ in candidates)


def test_a_declared_pair_is_crossed_in_full():
    experiment = config.ExperimentConfig(
        name="prova",
        base=Path("muro.yaml"),
        axes=[
            config.AxisSpec(path="tet.min_ratio", values=[1.8, 2.0]),
            config.AxisSpec(path="tet.nobisect", values=[False, True]),
        ],
        pairs=[("tet.min_ratio", "tet.nobisect")],
    )

    candidates = sweep.expand(experiment, _base())
    marks = {sweep.fingerprint(cfg) for _, cfg in candidates}
    atteso = {
        sweep.fingerprint(
            sweep.with_override(sweep.with_override(_base(), "tet.min_ratio", a), "tet.nobisect", b)
        )
        for a in (1.8, 2.0)
        for b in (False, True)
    }

    # Le quattro combinazioni della coppia esistono tutte fra i candidati. Non
    # si contano le etichette `axes` con due voci: una combinazione della
    # coppia che coincide con la base, o con una voce a un asse solo, viene
    # deduplicata per impronta e sopravvive con l'etichetta piu corta.
    assert atteso <= marks
    assert len(marks) == len(candidates)


def test_a_partial_metrics_file_is_not_complete():
    """Il blocco finally di pipeline.run scrive un dizionario parziale quando una corsa muore.

    Quel file e' oggi indistinguibile da uno completo, ed e' il motivo per cui
    un candidato entra nel fronte solo se porta tutte le chiavi di step.
    """
    completo = {name: {} for name in sweep.REQUIRED_STEPS}

    assert sweep.is_complete(completo) is True
    assert sweep.is_complete({"01_load": {}, "08_simplify": {}}) is False
    assert sweep.is_complete({}) is False


def test_the_registry_is_append_only_and_reads_back(tmp_path):
    path = tmp_path / "registro.jsonl"

    sweep.append_row(path, {"fingerprint": "aaa", "outcome": "riuscito"})
    sweep.append_row(path, {"fingerprint": "bbb", "outcome": "fallito"})

    rows = sweep.load_registry(path)
    assert [row["fingerprint"] for row in rows] == ["aaa", "bbb"]
    assert path.read_text(encoding="utf-8").count("\n") == 2


def test_the_digest_of_a_file_changes_with_its_content(tmp_path):
    path = tmp_path / "artefatto.ply"
    path.write_bytes(b"uno")
    prima = sweep.file_digest(path)
    path.write_bytes(b"due")

    assert sweep.file_digest(path) != prima
    assert len(prima) == 64


def test_provenance_records_the_code_that_produced_the_row():
    """Il commit e' leggibile, o dirty e' sconosciuto: mai un dirty fabbricato accanto a un commit assente.

    Su una macchina dove git non riesce a partire (sandbox che nega l'avvio del
    processo) commit vale "sconosciuto" e dirty deve restare None, non un bool
    inventato. Dove git parte, valgono le garanzie piene.
    """
    provenance = sweep.provenance()

    if provenance["commit"] == "sconosciuto":
        assert provenance["dirty"] is None
    else:
        assert len(provenance["commit"]) >= 7
        assert isinstance(provenance["dirty"], bool)
    assert "open3d" in provenance["versions"]
    assert "tetgen" in provenance["versions"]


def test_provenance_when_git_cannot_start_reports_dirty_as_unknown_not_false(monkeypatch):
    """Se git non parte, dirty deve restare sconosciuto, non fabbricato a False.

    bool("") e' False: se il fallimento venisse letto come uno stdout vuoto,
    un albero sporco si scriverebbe pulito con apparente certezza. E' precisamente
    il difetto che questo registro esiste per impedire, riprodotto dentro la riga.
    """
    def _raise(*args, **kwargs):
        raise OSError("git non trovato")

    monkeypatch.setattr(sweep.subprocess, "run", _raise)

    with pytest.warns(sweep.GitUnavailableWarning):
        provenance = sweep.provenance()

    assert provenance["dirty"] is None
    assert provenance["commit"] == "sconosciuto"


def test_a_candidate_that_fails_becomes_a_row_and_not_an_exception(tmp_path):
    """Un buco nel registro sarebbe indistinguibile da un candidato mai provato.

    Qui il fallimento e' provocato con una nuvola inesistente, che e' il modo
    piu rapido di far uscire `meshrec run` con codice diverso da zero.
    """
    cfg = config.PipelineConfig(input=config.InputConfig(path=str(tmp_path / "assente.ply")))

    row = sweep.run_candidate({}, cfg, tmp_path / "candidato", timeout_s=120.0)

    assert row["outcome"] == "fallito"
    assert row["exit_code"] != 0
    assert row["stderr"]
    assert row["complete"] is False
    assert row["fingerprint"] == sweep.fingerprint(cfg)


def test_a_candidate_that_succeeds_records_its_artifacts(tmp_path):
    """Sul cubo sintetico la catena intera gira in pochi secondi ed e' l'unico
    caso in cui il motore puo' essere provato end-to-end dentro la suite."""
    from meshrec.core import io, synth

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    cfg = config.PipelineConfig(
        input=config.InputConfig(path=str(cloud)),
        surface=config.SurfaceConfig(poisson_depth=6),
    )

    row = sweep.run_candidate({"tet.min_ratio": 1.8}, cfg, tmp_path / "candidato", timeout_s=600.0)

    assert row["outcome"] == "riuscito"
    assert row["complete"] is True
    assert row["axes"] == {"tet.min_ratio": 1.8}
    assert row["input_digest"] == sweep.file_digest(cloud)
    assert "09_volume.vtu" in row["artifacts"]
    assert row["duration_s"] > 0.0


def test_a_truncated_metrics_file_does_not_raise_and_becomes_incomplete(tmp_path, monkeypatch):
    """pipeline.run scrive metrics.json in un blocco finally: un processo ucciso
    a meta' (timeout, memoria esaurita) lo lascia troncato. json.JSONDecodeError
    non deve salire qui: e' esattamente il caso che questa funzione esiste per
    assorbire.

    Il sottoprocesso reale e' sostituito con uno finto, cosi' il file troncato
    scritto a mano sopravvive fino alla lettura che questo test verifica.
    """
    out_dir = tmp_path / "candidato"
    out_dir.mkdir()
    (out_dir / "metrics.json").write_text('{"01_load": {"n":', encoding="utf-8")

    def _fake_run(cmd, **kwargs):
        return sweep.subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="ucciso")

    monkeypatch.setattr(sweep.subprocess, "run", _fake_run)

    row = sweep.run_candidate({}, _base(), out_dir, timeout_s=120.0)

    assert row["metrics"] == {}
    assert row["complete"] is False
    assert row["fingerprint"] == sweep.fingerprint(_base())


def test_a_candidate_whose_folder_cannot_be_created_becomes_a_row_and_not_an_exception(tmp_path):
    """Permessi negati o collisione con un file omonimo non devono far salire
    OSError: il candidato diventa comunque una riga, con esito 'errore'.

    Qui la collisione e' un file normale creato al percorso dove out_dir
    dovrebbe nascere: mkdir(exist_ok=True) solleva se il percorso esiste ma
    non e' una cartella.
    """
    blocked = tmp_path / "candidato"
    blocked.write_text("non e' una cartella", encoding="utf-8")

    cfg = _base()
    row = sweep.run_candidate({}, cfg, blocked, timeout_s=120.0)

    assert row["outcome"] == "errore"
    assert row["stderr"]
    assert row["fingerprint"] == sweep.fingerprint(cfg)


def _row(fingerprint_: str, thickness_error: float, tets: int, over: float, **extra):
    row = {
        "fingerprint": fingerprint_,
        "outcome": "riuscito",
        "complete": True,
        "thickness_error": thickness_error,
        "metrics": {
            "10_volume_quality": {"tets": tets, "radius_edge_over_reference": over},
        },
        "artifacts_kept": True,
    }
    row.update(extra)
    return row


def test_a_dominated_candidate_leaves_the_front():
    peggiore = _row("a", thickness_error=20.0, tets=2_000_000, over=0.20)
    migliore = _row("b", thickness_error=5.0, tets=1_000_000, over=0.08)

    front = sweep.pareto_front([peggiore, migliore])

    assert [row["fingerprint"] for row in front] == ["b"]


def test_a_candidate_better_on_one_axis_survives():
    """Il fronte non sceglie: scarta solo chi e' battuto su tutto."""
    leggero = _row("a", thickness_error=20.0, tets=500_000, over=0.20)
    fedele = _row("b", thickness_error=2.0, tets=2_000_000, over=0.09)

    front = sweep.pareto_front([leggero, fedele])

    assert {row["fingerprint"] for row in front} == {"a", "b"}


def test_an_incomplete_candidate_never_enters_the_front():
    parziale = _row("a", thickness_error=1.0, tets=1, over=0.0)
    parziale["complete"] = False
    normale = _row("b", thickness_error=9.0, tets=900_000, over=0.10)

    assert [row["fingerprint"] for row in sweep.pareto_front([parziale, normale])] == ["b"]


def test_a_front_as_large_as_the_grid_is_reported():
    """Se nessun candidato e' dominato gli assi non discriminano, e senza
    questa sorveglianza il caso si presenterebbe come un fronte ricco."""
    rows = [
        _row("a", thickness_error=1.0, tets=3, over=0.3),
        _row("b", thickness_error=2.0, tets=2, over=0.2),
        _row("c", thickness_error=3.0, tets=1, over=0.1),
    ]

    with pytest.warns(sweep.SweepDiagnosticWarning, match="non discrimina"):
        report = sweep.check_sweep(rows, sweep.pareto_front(rows))

    assert report["front_is_whole_grid"] is True


def test_more_than_half_failing_is_reported():
    """Con un solo candidato confrontabile il fronte e' anche largo quanto
    la griglia comparabile: scattano entrambi gli avvisi, e vanno asseriti
    entrambi, altrimenti quello che sfugge non conta piu' nella suite."""
    rows = [
        _row("a", thickness_error=1.0, tets=1, over=0.1),
        {"fingerprint": "b", "outcome": "fallito", "complete": False},
        {"fingerprint": "c", "outcome": "timeout", "complete": False},
    ]

    with pytest.warns(sweep.SweepDiagnosticWarning) as record:
        report = sweep.check_sweep(rows, sweep.pareto_front(rows))

    messages = [str(warning.message) for warning in record]
    assert any("griglia" in message for message in messages)
    assert any("non discrimina" in message for message in messages)
    assert report["failed_fraction"] == pytest.approx(2 / 3)


def test_candidates_tied_on_every_axis_all_survive():
    """Due tuple uguali non si dominano a vicenda: ne' _dominates ne'
    other != score le fa cadere, in nessuna delle due direzioni."""
    prima = _row("a", thickness_error=5.0, tets=1_000_000, over=0.10)
    seconda = _row("b", thickness_error=5.0, tets=1_000_000, over=0.10)

    front = sweep.pareto_front([prima, seconda])

    assert {row["fingerprint"] for row in front} == {"a", "b"}


def test_pruning_keeps_config_and_metrics_and_marks_the_row(tmp_path):
    """Una corsa completa pesa circa 300 MB: i dominati conservano la riga, non i file."""
    dominato = tmp_path / "dominato"
    dominato.mkdir()
    for name in ("config.yaml", "metrics.json", "09_volume.vtu", "wall_model.inp"):
        (dominato / name).write_text("x", encoding="utf-8")
    sopravvive = tmp_path / "fronte"
    sopravvive.mkdir()
    (sopravvive / "09_volume.vtu").write_text("x", encoding="utf-8")

    scartato = _row("a", thickness_error=20.0, tets=2, over=0.5, out_dir=str(dominato))
    tenuto = _row("b", thickness_error=1.0, tets=1, over=0.1, out_dir=str(sopravvive))

    removed = sweep.prune([scartato, tenuto], [tenuto])

    assert removed == 2
    assert (dominato / "config.yaml").exists()
    assert (dominato / "metrics.json").exists()
    assert not (dominato / "09_volume.vtu").exists()
    assert (sopravvive / "09_volume.vtu").exists()
    assert scartato["artifacts_kept"] is False
    assert tenuto["artifacts_kept"] is True


def _experiment(tmp_path, known_thickness):
    return config.ExperimentConfig(
        name="prova",
        base=Path("muro.yaml"),
        axes=[config.AxisSpec(path="tet.min_ratio", values=[1.8, 2.0])],
        known_thickness=known_thickness,
        sweep=config.SweepConfig(
            runs_root=tmp_path / "runs", registry_root=tmp_path / "experiments"
        ),
    )


def test_the_gate_raises_when_the_thickness_error_exceeds_five_percent(tmp_path, monkeypatch):
    """Il cancello ferma lo sweep prima di eseguire candidati, coi numeri nel messaggio.

    run_candidate e' sostituito con uno che solleva se chiamato: se il cancello
    non fermasse lo sweep prima di expand(), pytest.raises vedrebbe
    AssertionError al posto di ValueError e il test fallirebbe da solo, senza
    bisogno di una quarta asserzione o di un contatore di chiamate.
    """
    import numpy as np

    monkeypatch.setattr("meshrec.core.io.load_cloud", lambda cfg: (np.zeros((4, 3)), {"spacing": 1.0}))
    monkeypatch.setattr("meshrec.core.segment.segment_cloud", lambda points, cfg, spacing: (points, {}))
    monkeypatch.setattr(
        "meshrec.core.quality.thickness",
        lambda points, bin_width: {"thickness": 120.0, "axis": 0, "extent": 10.0, "bimodal": True},
    )

    def _boom(*args, **kwargs):
        raise AssertionError("run_candidate chiamato: il cancello non ha fermato lo sweep")

    monkeypatch.setattr(sweep, "run_candidate", _boom)

    with pytest.raises(ValueError, match="120.0 mm contro 100.0 mm"):
        sweep.run_experiment(_experiment(tmp_path, known_thickness=100.0), _base())


def test_the_gate_raises_when_the_source_distribution_is_not_bimodal(tmp_path, monkeypatch):
    """Anche a scarto piccolo, senza due modi la misura non e' utilizzabile: il cancello scatta lo stesso."""
    import numpy as np

    monkeypatch.setattr("meshrec.core.io.load_cloud", lambda cfg: (np.zeros((4, 3)), {"spacing": 1.0}))
    monkeypatch.setattr("meshrec.core.segment.segment_cloud", lambda points, cfg, spacing: (points, {}))
    monkeypatch.setattr(
        "meshrec.core.quality.thickness",
        lambda points, bin_width: {"thickness": 100.5, "axis": 0, "extent": 10.0, "bimodal": False},
    )

    with pytest.raises(ValueError, match="bimodale=False"):
        sweep.run_experiment(_experiment(tmp_path, known_thickness=100.0), _base())


def test_the_gate_reports_a_readable_message_when_the_source_thickness_is_not_measurable(
    tmp_path, monkeypatch
):
    """quality.thickness su una nuvola sorgente degenere restituisce thickness None.

    abs(None - known_thickness) romperebbe il cancello con un TypeError
    proprio mentre sta segnalando il problema: qui si verifica che il
    messaggio dichiari esplicitamente la nuvola non misurabile, senza
    stampare un numero fabbricato ne' sollevare l'eccezione sbagliata.
    """
    import numpy as np

    monkeypatch.setattr("meshrec.core.io.load_cloud", lambda cfg: (np.zeros((4, 3)), {"spacing": 1.0}))
    monkeypatch.setattr("meshrec.core.segment.segment_cloud", lambda points, cfg, spacing: (points, {}))
    monkeypatch.setattr(
        "meshrec.core.quality.thickness",
        lambda points, bin_width: {"thickness": None, "axis": 0, "extent": 10.0, "bimodal": False},
    )

    with pytest.raises(ValueError, match="non misurabile"):
        sweep.run_experiment(_experiment(tmp_path, known_thickness=100.0), _base())


def test_measure_thickness_error_returns_none_without_raising_when_metrics_is_empty(tmp_path):
    """06_repaired.ply esiste ma metrics.json non e' mai stato scritto: il candidato
    ucciso dopo la riparazione e prima del blocco finally che lo scrive. La riga
    resta comparabile a False, ma la funzione non deve sollevare KeyError."""
    import numpy as np
    import open3d as o3d

    out_dir = tmp_path / "candidato"
    out_dir.mkdir()
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    )
    mesh.triangles = o3d.utility.Vector3iVector(np.array([[0, 1, 2]]))
    o3d.io.write_triangle_mesh(str(out_dir / "06_repaired.ply"), mesh)

    row = {"out_dir": str(out_dir), "metrics": {}}

    assert sweep.measure_thickness_error(row, source_thickness=100.0) is None


def test_measure_thickness_error_returns_none_without_raising_on_a_degenerate_mesh(tmp_path):
    """06_repaired.ply esiste, metrics.json e' completo, ma la mesh riparata e'
    piatta: quality.thickness dichiara bimodal False (radice corretta in
    quality.py), non ValueError su np.argmax di una fetta vuota."""
    import numpy as np
    import open3d as o3d

    out_dir = tmp_path / "candidato"
    out_dir.mkdir()
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    )
    mesh.triangles = o3d.utility.Vector3iVector(np.array([[0, 1, 2]]))
    o3d.io.write_triangle_mesh(str(out_dir / "06_repaired.ply"), mesh)

    row = {"out_dir": str(out_dir), "metrics": {"01_load": {"spacing": 1.0}}}

    assert sweep.measure_thickness_error(row, source_thickness=100.0) is None


def test_measure_thickness_error_returns_none_without_raising_on_a_nan_vertex(tmp_path):
    """Prova end-to-end: un vertice NaN nella mesh riparata non deve fermare
    run_experiment dopo che tutti i candidati sono gia' stati eseguiti e
    prima di ogni append_row. Coordinate non finite possono uscire da una
    ricostruzione di Poisson andata male, da una chiusura dei fori o da una
    stima delle normali degenere: non e' un caso teorico."""
    import numpy as np
    import open3d as o3d

    out_dir = tmp_path / "candidato"
    out_dir.mkdir()
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(
        np.array([[np.nan, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    )
    mesh.triangles = o3d.utility.Vector3iVector(np.array([[0, 1, 2], [1, 2, 3]]))
    o3d.io.write_triangle_mesh(str(out_dir / "06_repaired.ply"), mesh)

    row = {"out_dir": str(out_dir), "metrics": {"01_load": {"spacing": 1.0}}}

    assert sweep.measure_thickness_error(row, source_thickness=100.0) is None
