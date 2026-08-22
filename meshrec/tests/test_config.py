"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from meshrec.core import config
from meshrec.core.config import PipelineConfig
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


def test_l_impronta_di_una_corsa_registrata_non_cambia():
    """Le impronte della Fase 2 vivono nei registri: allargare PipelineConfig
    senza escludere il blocco nuovo cambierebbe la provenienza di ogni riga
    della tabella sperimentale della tesi.

    Il test non fissa un valore magico: rilegge i due registri veri, rivalida
    la configurazione incorporata in ciascuna riga e ricalcola l'impronta. Se
    coincide con quella registrata, la riga e' ancora derivabile dalla
    configurazione che dichiara.
    """
    import json

    from meshrec.core.sweep import fingerprint

    radice = Path(__file__).resolve().parents[1] / "experiments"
    righe = 0
    for registro in sorted(radice.glob("*/registro.jsonl")):
        for riga in registro.read_text(encoding="utf-8").splitlines():
            if not riga.strip():
                continue
            voce = json.loads(riga)
            cfg = PipelineConfig.model_validate(voce["config"])
            assert fingerprint(cfg) == voce["fingerprint"], (
                f"{registro}: la riga {righe + 1} non e' piu' derivabile dalla "
                "propria configurazione"
            )
            righe += 1
    assert righe == 22, f"attese 22 righe nei due registri, trovate {righe}"


def test_i_blocchi_nuovi_stanno_in_pipelineconfig_e_nella_lista_di_esclusione_giusta():
    """I tre blocchi della Fase 4 e 5 viaggiano con la configurazione, perche'
    gli step 12 e 13 li leggono, ma non sono esclusi dall'impronta allo stesso
    modo.

    `wall` e `model` ne restano sempre fuori: nessun asse della Fase 2 li tocca
    e non cambiano il deck. `carichi` ne esce solo quando e' vuoto, perche'
    STEP_BLOCKS[11] lo legge e cambia il deck, che e' artefatto richiesto di
    ogni candidato. Misurato il 22/08/2026 sulle 22 righe di experiments/muro e
    experiments/lab_crop: l'esclusione condizionata ne cambia 0 su 22,
    l'inclusione secca 22 su 22.

    L'ultima asserzione e' quella che smentisce: un blocco nelle due liste
    insieme sarebbe una contraddizione, "sempre fuori" e "fuori solo se vuoto".
    """
    from meshrec.core.sweep import BLOCCHI_FUORI_IMPRONTA, BLOCCHI_VUOTI_FUORI_IMPRONTA

    campi = set(PipelineConfig.model_fields)
    assert {"wall", "model", "carichi"} <= campi
    assert set(BLOCCHI_FUORI_IMPRONTA) == {"run", "wall", "model"}
    assert set(BLOCCHI_VUOTI_FUORI_IMPRONTA) == {"carichi"}
    assert set(BLOCCHI_FUORI_IMPRONTA) <= campi
    assert set(BLOCCHI_VUOTI_FUORI_IMPRONTA) <= campi
    assert not set(BLOCCHI_FUORI_IMPRONTA) & set(BLOCCHI_VUOTI_FUORI_IMPRONTA)


def test_i_casi_di_carico_non_hanno_valori_predefiniti():
    """La spinta e il carico si dichiarano, come il materiale.

    Stessa ragione di config.Material: un predefinito di muratura a 1500 MPa
    era finito in silenzio nella configurazione di un telaio in calcestruzzo, e
    nessuno l'aveva scelto. Un coefficiente di spinta predefinito sarebbe lo
    stesso errore su una grandezza che nessun dato puo' suggerire.

    Il test verifica che ogni campo di ogni modello e' obbligatorio campo per
    campo, non solo che l'istanziazione a vuoto fallisce (il quale potrebbe
    fallire per il motivo sbagliato, e.g. se solo asse restasse obbligatorio).
    """
    for modello, campi_attesi in (
        (config.SpintaOrizzontale, {"coefficiente", "asse"}),
        (config.CaricoSommita, {"risultante", "nset"}),
        (config.Modale, {"modi"}),
    ):
        for nome_campo, info_campo in modello.model_fields.items():
            assert nome_campo in campi_attesi, (
                f"{modello.__name__}.{nome_campo} non era nel set atteso"
            )
            assert info_campo.is_required(), (
                f"{modello.__name__}.{nome_campo} ha un predefinito, "
                "dovrebbe essere obbligatorio"
            )
        assert set(modello.model_fields) == campi_attesi, (
            f"{modello.__name__} ha campi extra: "
            f"{set(modello.model_fields) - campi_attesi}"
        )


def test_un_analisi_senza_casi_dichiarati_ha_il_solo_peso_proprio():
    """Chi non dichiara nulla ottiene l'unico caso derivabile dai dati.

    Densita' e gravita' sono gia' nella configurazione, quindi il peso proprio
    non e' un predefinito indovinato: e' l'unica cosa che il programma sa gia'.
    I tre casi di carico sono nullabili e restano None se non dichiarati.
    """
    carichi = config.CarichiConfig()

    assert carichi.spinta is None
    assert carichi.carico_sommita is None
    assert carichi.modale is None


def test_il_coefficiente_di_spinta_rifiuta_lo_zero_e_il_negativo():
    with pytest.raises(ValidationError):
        config.SpintaOrizzontale(coefficiente=0.0, asse="y")
    with pytest.raises(ValidationError):
        config.SpintaOrizzontale(coefficiente=-0.1, asse="y")


@pytest.mark.parametrize("riservato", ["SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"])
def test_step_name_non_puo_ripetere_un_nome_di_caso_di_carico(riservato):
    """M13 della revisione finale: `abaqus.export_model` assegna da se' i nomi
    degli altri casi di carico, e `solve.risolvi` usa quel nome come chiave di
    `point_data`. Con `analysis.step_name: SPINTA_ORIZZONTALE` due passi
    finiscono sulla stessa etichetta, il secondo sovrascrive il primo e un
    caso di carico sparisce dal `.vtu` senza errore.
    """
    with pytest.raises(ValidationError, match="riservato"):
        config.AnalysisConfig(material=MATERIALE, step_name=riservato)


def test_lo_step_name_predefinito_e_i_nomi_liberi_restano_accettati():
    """Controprova: la guardia sopra vieta tre nomi, non i nomi."""
    assert config.AnalysisConfig(material=MATERIALE).step_name == "GRAVITA"
    assert config.AnalysisConfig(material=MATERIALE, step_name="PESO_PROPRIO").step_name == "PESO_PROPRIO"
