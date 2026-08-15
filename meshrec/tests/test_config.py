"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

from pathlib import Path

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


def test_experiment_round_trip_and_defaults(tmp_path):
    """L'esperimento sopravvive al round-trip e i suoi predefiniti vivono qui."""
    import yaml

    experiment = config.ExperimentConfig(
        name="muro_ricostruzione",
        base=Path("muro.yaml"),
        axes=[config.AxisSpec(path="tet.min_ratio", values=[1.7, 1.8, 2.0])],
        known_thickness=1245.7,
    )
    assert experiment.sweep.workers == 4
    assert experiment.sweep.timeout_s == 1800
    assert experiment.sweep.keep_dominated_artifacts is False

    path = tmp_path / "esperimento.yaml"
    path.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    assert config.load_experiment(path) == experiment


def test_an_axis_with_no_values_is_rejected():
    with pytest.raises(ValueError):
        config.AxisSpec(path="tet.min_ratio", values=[])


# Due modelli distinti, non uno solo: la difesa deve stare sulla base comune
# e non su un singolo model_config scritto a mano dove il difetto e' stato visto.
@pytest.mark.parametrize("grafia", ["1e999", "Infinity", "inf", "nan", "NaN"])
def test_un_infinito_o_nan_su_material_young_e_rifiutato(grafia):
    with pytest.raises(ValueError, match="finite number"):
        config.Material(young=grafia)


@pytest.mark.parametrize("grafia", ["1e999", "Infinity", "inf", "nan", "NaN"])
def test_un_infinito_o_nan_su_tet_max_volume_e_rifiutato(grafia):
    with pytest.raises(ValueError, match="finite number"):
        config.TetConfig(max_volume=grafia)


def test_i_valori_decimali_normali_arrivano_ancora_a_destinazione():
    """Il controllo che smentisce: un vincolo che rifiuta tutto passerebbe il test sopra."""
    assert config.Material(young="2.5").young == pytest.approx(2.5)
    assert config.Material(young="1e3").young == pytest.approx(1000.0)
    assert config.TetConfig(max_volume="2.5").max_volume == pytest.approx(2.5)
    assert config.TetConfig(max_volume="1e3").max_volume == pytest.approx(1000.0)


def test_un_inf_gia_scritto_su_disco_non_si_rilegge(tmp_path):
    """Il verso della lettura: una configurazione con .inf non deve poter tornare dentro."""
    path = tmp_path / "config.yaml"
    path.write_text(
        "input:\n  path: nuvola.ply\ndownsample:\n  voxel_size: .inf\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="finite number"):
        config.load_config(path)


def test_l_impronta_di_una_corsa_registrata_non_cambia(tmp_path):
    """L'impronta della Fase 2 vive nei registri: allargare PipelineConfig la
    cambierebbe, e con essa la provenienza di ogni riga della tabella della tesi.
    """
    from meshrec.core.sweep import fingerprint

    cfg = config.PipelineConfig(
        input=config.InputConfig(path=Path("Nuvole di punti/lab_frame.pcd"), scale=1000.0),
    )
    prima = fingerprint(cfg)
    assert len(prima) == 64
    # Un campo nuovo in PipelineConfig cambierebbe questo valore: il test lo fissa
    # sulla forma canonica corrente e non su un valore magico, cosi' fallisce
    # anche se il campo nuovo ha un predefinito innocuo.
    payload = cfg.model_dump(mode="json")
    assert set(payload) == {
        "input", "segment", "downsample", "normals", "surface",
        "repair", "simplify", "tet", "analysis", "run",
    }
