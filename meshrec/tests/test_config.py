"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

from pathlib import Path

import pytest

from meshrec.core import config
from materiale import ANALISI, MATERIALE


def test_defaults_are_in_working_units():
    cfg = config.PipelineConfig(
        analysis=ANALISI,
        input=config.InputConfig(path="nuvola.ply"),
    )
    assert cfg.analysis.gravity == pytest.approx(9810.0)
    assert cfg.input.scale == pytest.approx(1.0)


def test_the_material_has_no_defaults_and_must_be_declared():
    """Il materiale non si eredita in silenzio: senza dichiarazione la configurazione non nasce.

    E' la regola che manca a `lab.yaml` prima della correzione, dove il
    predefinito muratura a 1500 MPa era finito sul telaio in calcestruzzo
    senza che nessuno lo scegliesse.

    I quattro campi si provano uno per uno perche' il difetto reale era un
    predefinito su un campo solo: un `young` che torna a 1500 MPa dentro un
    materiale per il resto dichiarato passa inosservato a un controllo che ne
    omette due insieme, ed e' proprio il parametro sbagliato di venti volte
    sul telaio in calcestruzzo.
    """
    with pytest.raises(ValueError):
        config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    with pytest.raises(ValueError):
        config.AnalysisConfig()

    completo = {"name": "CALCESTRUZZO", "young": 31500.0, "poisson": 0.2, "density": 2.5e-9}
    for mancante in completo:
        parziale = {campo: valore for campo, valore in completo.items() if campo != mancante}
        with pytest.raises(ValueError):
            config.Material(**parziale)


def test_yaml_round_trip_preserves_every_field(tmp_path):
    cfg = config.PipelineConfig(
        analysis=ANALISI,
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


def test_il_nome_del_materiale_non_puo_iniettare_nel_deck():
    """Il nome finisce interpolato in `*MATERIAL, NAME=...` di un file scritto in ascii.

    Senza vincolo un accento romperebbe l'esportazione allo step 11, cioe' dopo
    l'intera pipeline, e un a capo scriverebbe card in piu' nel deck senza che
    nulla se ne accorga. Ora entrambi sono rifiutati alla nascita.
    """
    resto = {"young": 31500.0, "poisson": 0.2, "density": 2.5e-9}
    for cattivo in ("Calcestruzzo C25/30 \u2013 armato", "X\n*BOUNDARY\nBASE, 1, 3", "con spazio"):
        with pytest.raises(ValueError):
            config.Material(name=cattivo, **resto)
    assert config.Material(name="CALCESTRUZZO_C25_30", **resto).name == "CALCESTRUZZO_C25_30"


def test_i_valori_decimali_normali_arrivano_ancora_a_destinazione():
    """Il controllo che smentisce: un vincolo che rifiuta tutto passerebbe il test sopra."""
    resto = {"name": "MURATURA", "poisson": 0.2, "density": 1.8e-9}
    assert config.Material(young="2.5", **resto).young == pytest.approx(2.5)
    assert config.Material(young="1e3", **resto).young == pytest.approx(1000.0)
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
        analysis=ANALISI,
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
