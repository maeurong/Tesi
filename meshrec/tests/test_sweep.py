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
