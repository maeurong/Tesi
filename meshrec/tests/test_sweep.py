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
