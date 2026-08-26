"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

from pathlib import Path

import numpy as np
import pytest
import yaml
from pydantic import ValidationError

from meshrec.core import config
from meshrec.core.config import PipelineConfig
from materiale import ANALISI, MATERIALE, crea_config


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

    Dalla correzione dell'ingresso una configurazione puo' *nascere* senza
    analisi -- una corsa comincia dalla sola nuvola -- ma non puo' arrivare
    allo step che il materiale lo pretende: la guardia si e' spostata da
    `PipelineConfig` a `analisi_dichiarata`, non e' stata tolta.
    """
    senza_analisi = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    with pytest.raises(ValueError):
        senza_analisi.analisi_dichiarata(11)
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


def test_due_chiavi_omonime_nello_yaml_sono_rifiutate(tmp_path):
    """`safe_load` tiene l'ultima e la prima sparisce senza un segnale.

    E' l'unico ingresso degenere senza sintomo: gli altri almeno
    risolvono zero nodi. Un selettore corretto e riscritto sotto lo
    stesso nome verrebbe applicato nella versione che l'operatore
    credeva di aver sostituito.

    Mutazione che lo uccide: tornare a `yaml.safe_load`. Il file viene
    letto, `raggio` vale 9.0 e nessuno sa che il 5.0 c'era.
    """
    percorso = tmp_path / "config.yaml"
    percorso.write_text(
        "input:\n  path: nuvola.ply\n"
        "analysis:\n  material:\n    name: MURATURA\n    young: 1500.0\n"
        "    poisson: 0.2\n    density: 1.8e-9\n"
        "selettori:\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 5.0\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 9.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="angolo"):
        config.load_config(percorso)


def test_un_tag_python_object_nello_yaml_solleva(tmp_path):
    """Il loader e' sicuro per costruzione (`_LoaderChiaviUniche` eredita da
    `yaml.SafeLoader`), ma nessun test lo asserisce ancora: questo lo fa.

    Un `!!python/object/apply:...` con `yaml.Loader`/`yaml.UnsafeLoader`
    esegue la chiamata alla lettura del file; con un loader derivato da
    `SafeLoader` non c'e' alcun costruttore per quel tag, e `yaml.load`
    solleva prima di costruire nulla.

    Mutazione che lo uccide: sostituire `_LoaderChiaviUniche(yaml.SafeLoader)`
    con `_LoaderChiaviUniche(yaml.UnsafeLoader)` in `carica_yaml` -- il tag
    verrebbe costruito (ed eseguito) invece di sollevare.
    """
    percorso = tmp_path / "config.yaml"
    percorso.write_text(
        'input:\n  path: !!python/object/apply:os.system ["echo pwned"]\n',
        encoding="utf-8",
    )
    with pytest.raises(yaml.YAMLError):
        config.carica_yaml(percorso)


def test_anche_il_registro_degli_esperimenti_rifiuta_le_chiavi_omonime(tmp_path):
    """La stessa falla sta su due safe_load: si chiude in un punto e si usa in due.

    Il `name` duplicato e' la forma minima: `axes` e' una lista, e le
    chiavi omonime esistono solo dentro una mappa.

    Mutazione che lo uccide: passare il loader solo a `load_config`.
    Questo test cade, l'altro passa.
    """
    percorso = tmp_path / "experiment.yaml"
    percorso.write_text(
        "name: primo\n"
        "name: secondo\n"
        "base: base.yaml\n"
        "axes:\n  - path: tet.min_ratio\n    values: [1.6, 1.8]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="name"):
        config.load_experiment(percorso)


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


def test_lo_schema_non_sposta_l_impronta_dei_registri_in_silenzio():
    """Due sorveglianze sulle 22 righe della tabella sperimentale, non una.

    **Riga per riga**: la cartella di un candidato e' `fingerprint(cfg)[:12]`
    (`core/sweep.py`), quindi il basename di `out_dir` ancora l'impronta
    registrata alla riga che la porta. Regge a qualunque schema, perche' non
    ricalcola niente: cade se qualcuno scambia due config fra righe, o
    riscrive a mano un `fingerprint`.

    **In sequenza**: l'aggregato delle impronte che lo schema **corrente**
    produce da quelle stesse configurazioni, nell'ordine in cui le righe
    stanno sul disco. Cade se un campo entra o esce da un blocco dentro
    l'impronta, e cade anche se due config vengono scambiate fra righe.

    L'ordine non e' un dettaglio di resa: e' l'unica cosa che distingue le 22
    impronte da un mucchio. Ordinarle prima di hasharle -- come faceva la
    prima stesura di questa guardia -- rende il digest invariante allo
    scambio, e lo scambio e' proprio la mutazione che il legame per-riga,
    morto col cambio di schema, sorvegliava.

    Il campo `fingerprint` delle righe non si riscrive: e' un dato misurato.
    L'aggregato invece si aggiorna quando lo schema cambia apposta, e allora
    lo si dice nel commit.
    """
    import hashlib
    import json

    from meshrec.core.sweep import fingerprint

    radice = Path(__file__).resolve().parents[1] / "experiments"
    marchi = []
    for registro in sorted(radice.glob("*/registro.jsonl")):
        for numero, riga in enumerate(registro.read_text(encoding="utf-8").splitlines(), 1):
            if not riga.strip():
                continue
            voce = json.loads(riga)
            dove = f"{registro.parent.name}/registro.jsonl riga {numero}"
            assert "config" in voce, f"{dove}: la riga non porta la configurazione"
            # `out_dir` e' scritto dalla piattaforma che ha girato lo sweep e
            # puo' portare separatori di Windows: il basename si isola a mano.
            cartella = voce["out_dir"].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
            assert cartella == voce["fingerprint"][:12], (
                f"{dove}: la cartella '{cartella}' non e' quella che l'impronta "
                f"registrata nomina ({voce['fingerprint'][:12]})"
            )
            marchi.append(fingerprint(PipelineConfig.model_validate(voce["config"])))

    assert len(marchi) == 22, f"attese 22 righe nei due registri, trovate {len(marchi)}"
    aggregato = hashlib.sha256("\n".join(marchi).encode("utf-8")).hexdigest()
    assert aggregato == "9b409e2d30a7465e81ea1268f913c766316280db9d40983f258ffe7f7bf79bd6", (
        "lo schema della configurazione ha spostato l'impronta delle righe "
        "registrate: se e' voluto, aggiorna l'aggregato e dillo nel commit"
    )


@pytest.mark.parametrize(
    ("caso", "impronta"),
    [
        ("lab.yaml", "ee7308f7fc34962b54b118e9159c86fd8ae2af172e4ac93e155505727c368a55"),
        ("muro.yaml", "78f0cf059e50f08e7b6823d240def3bdc0ba2172e908d85e03d8b71350a6cda1"),
    ],
)
def test_l_impronta_delle_configurazioni_del_caso_studio_e_quella_misurata(caso, impronta):
    """Le due configurazioni da cui partono gli sweep di tesi, fissate al valore
    misurato dopo il taglio di `bpa`/`alpha`/`decimate`.

    Il test sopra rilegge i registri e non se ne accorgerebbe: ogni riga porta
    dentro di se' la configurazione con cui e' stata calcolata, quindi resta
    derivabile anche se la base da cui e' nata cambia. Una modifica a
    `casi/lab.yaml` o a `casi/muro.yaml` sposterebbe in silenzio le corse
    future fuori dalle cartelle di quelle gia' registrate: qui lo dice.
    """
    from meshrec.core.sweep import fingerprint

    percorso = Path(__file__).resolve().parents[1] / "casi" / caso

    assert fingerprint(config.load_config(percorso)) == impronta


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
    assert set(BLOCCHI_VUOTI_FUORI_IMPRONTA) == {"carichi", "selettori"}
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


def test_una_configurazione_nasce_senza_analisi():
    """Una corsa deve poter nascere dalla sola nuvola.

    `analysis` e' letto dai soli step 11 e 13 (`steps.STEP_BLOCKS`), quindi
    esigerlo alla nascita costringeva a dichiarare la classe del calcestruzzo
    prima di aver guardato un punto. Il materiale resta obbligatorio *dentro*
    `AnalysisConfig`: quell'invariante nasce da un difetto misurato e non si
    tocca.
    """
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))

    assert cfg.analysis is None


def test_una_configurazione_senza_analisi_sopravvive_al_giro_su_disco(tmp_path):
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert config.load_config(tmp_path / "config.yaml").analysis is None


def test_chiedere_l_analisi_mancante_nomina_il_campo_e_lo_step():
    """Il rifiuto deve insegnare: quale campo manca e quale step lo pretende."""
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))

    with pytest.raises(ValueError, match="analysis.material") as errore:
        cfg.analisi_dichiarata(11)
    assert "11" in str(errore.value)


def test_chiedere_l_analisi_dichiarata_la_restituisce():
    """Controprova: la guardia vieta l'assenza, non l'uso."""
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"), analysis=ANALISI)

    assert cfg.analisi_dichiarata(11) is ANALISI


def test_il_materiale_resta_obbligatorio_dentro_l_analisi():
    with pytest.raises(ValidationError):
        config.AnalysisConfig()


def test_i_quattro_selettori_si_dichiarano_per_nome():
    """Il blocco `selettori` accetta le quattro forme e le tiene per nome.

    Mutazione che lo uccide: dare a `SelettoreSfera.tipo` un letterale
    diverso da `"sfera"`. La dichiarazione della sfera non trova piu'
    alcun membro dell'unione che la accetti e la configurazione non nasce.

    **Non** lo uccide togliere `discriminator="tipo"`: misurato su
    pydantic 2.13.4, l'unione in modalita' smart sceglie comunque il
    modello giusto, perche' i quattro `Literal` sono valori esatti e
    distinti. Cio' che il discriminatore compra davvero e' la qualita'
    dell'errore, e ha il proprio test qui sotto.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={
            "piastra": {"tipo": "box", "min": [0.0, 0.0, 0.0], "max": [10.0, 10.0, 10.0]},
            "angolo": {"tipo": "sfera", "centro": [1.0, 2.0, 3.0], "raggio": 5.0},
            "punta": {"tipo": "nodo", "punto": [1.0, 2.0, 3.0]},
            "appoggio": {"tipo": "nset", "nome": "BASE"},
        },
    )
    assert isinstance(cfg.selettori["piastra"], config.SelettoreBox)
    assert isinstance(cfg.selettori["angolo"], config.SelettoreSfera)
    assert isinstance(cfg.selettori["punta"], config.SelettoreNodo)
    assert isinstance(cfg.selettori["appoggio"], config.SelettoreNset)
    assert cfg.selettori["angolo"].raggio == pytest.approx(5.0)


def test_un_tipo_di_selettore_ignoto_da_un_errore_solo():
    """Cio' che il discriminatore compra: un errore che nomina il campo giusto.

    Misurato su pydantic 2.13.4: con `discriminator="tipo"` un `tipo`
    sconosciuto produce **un** errore, che dice qual e' il campo
    sbagliato e quali valori accetta. Senza, l'unione in modalita' smart
    prova tutti e quattro i membri e ne riporta **quattro**, uno per
    membro, e chi legge deve capire da se' quale volesse.

    Mutazione che lo uccide: togliere `discriminator="tipo"` dall'alias
    `Selettore`. Il conteggio degli errori passa da 1 a 4.
    """
    with pytest.raises(ValidationError) as scoppio:
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"strana": {"tipo": "palla", "centro": [0.0, 0.0, 0.0], "raggio": 5.0}},
        )
    errori = scoppio.value.errors()
    assert len(errori) == 1, [e["type"] for e in errori]
    assert errori[0]["type"] == "union_tag_invalid"
    assert errori[0]["ctx"]["discriminator"] == "'tipo'"


def test_senza_selettori_il_blocco_e_vuoto_non_assente():
    """Chi non dichiara nulla ottiene un dizionario vuoto, non None.

    Mutazione che lo uccide: predefinito `None` invece di
    `default_factory=dict`. Il codice a valle itera sul blocco, e un None
    esplode con un TypeError invece di non fare nulla.
    """
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.selettori == {}


def test_la_box_rovesciata_e_rifiutata_e_nomina_la_componente():
    """`min > max` non arriva alla mesh: risolverebbe zero nodi come altri quattro.

    Mutazione che lo uccide: togliere il validatore. La box rovesciata
    viene accettata e da' lo stesso sintomo di quattro condizioni
    diverse, che e' precisamente cio' che la spec vieta.
    """
    with pytest.raises(ValidationError, match=r"\by\b"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"rotta": {"tipo": "box", "min": [0.0, 9.0, 0.0], "max": [10.0, 1.0, 10.0]}},
        )


@pytest.mark.parametrize("raggio", [0.0, -5.0])
def test_la_sfera_senza_raggio_positivo_e_rifiutata(raggio):
    """Raggio nullo o negativo non e' una sfera piccola, e' una sfera che non c'e'.

    Mutazione che lo uccide: `ge=0.0` al posto di `gt=0.0`, che lascia
    passare il raggio zero.
    """
    with pytest.raises(ValidationError):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"vuota": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": raggio}},
        )


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_un_selettore_non_puo_chiamarsi_come_uno_dei_sei(nome):
    """I nomi dell'operatore e i sei di build_node_sets condividono lo spazio del deck.

    Mutazione che lo uccide: controllare la collisione solo su BASE.
    Il test passa su BASE e cade sugli altri cinque.
    """
    with pytest.raises(ValidationError, match=nome):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={nome: {"tipo": "nset", "nome": "TOP"}},
        )


@pytest.mark.parametrize("nome", ["base", "Top", "Face_Front"])
def test_un_selettore_non_puo_chiamarsi_come_uno_dei_sei_ignorando_il_caso(nome):
    """Il deck e' case-insensitive sui *NSET (misurato,
    docs/fase-6-cantiere/sonda-caso-nomi/README.md): un selettore che
    differisce solo per maiuscole da uno dei sei collide comunque nel deck.

    Mutazione che lo uccide: tornare al confronto diretto
    `set(self.selettori) & set(NOMI_SET_DI_FACCIA)`, senza casefold. Il
    test sui sei nomi esatti (uppercase) continuerebbe a passare, questi
    tre cadrebbero.
    """
    atteso = next(s for s in config.NOMI_SET_DI_FACCIA if s.casefold() == nome.casefold())
    with pytest.raises(ValidationError, match=atteso):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={nome: {"tipo": "nset", "nome": "TOP"}},
        )


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_selettore_nset_canonicalizza_il_nome_dei_sei(nome):
    """`SelettoreNset.nome` in caso non canonico (`top`) diventa il caso
    canonico dei sei (`TOP`): un confronto esatto a valle
    (`core/selezione.py`) fallirebbe altrimenti su un nome che collide
    solo ignorando le maiuscole.

    Mutazione che lo uccide: ritipare `SelettoreNset.nome` da
    `NomeSetDiFaccia` a `NomeSet`, cioe' togliere la normalizzazione. Nessun
    test in questo file la copriva prima che questo esistesse: toglierla non
    faceva cadere nulla.
    """
    selettore = config.SelettoreNset(tipo="nset", nome=nome.casefold())
    assert selettore.nome == nome


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_fixed_nset_canonicalizza_il_nome_dei_sei(nome):
    """`fixed_nset: base` nello YAML non deve morire dopo la tetraedralizzazione.

    Misurato prima di questa correzione: `AnalysisConfig(fixed_nset='base')`
    passava la validazione, faceva girare la mesh di volume per minuti, e
    solo allora `export_model` sollevava -- mentre `SelettoreNset(nome='base')`
    era gia' normalizzato a `BASE` a validazione. Stesso spazio di nomi,
    stesso `ccx` che risolve gli `*NSET` senza distinguere le maiuscole
    (`docs/fase-6-cantiere/sonda-caso-nomi/README.md`), tre campi e tre
    comportamenti diversi. La guardia in `abaqus.write_inp` dichiarava nel
    proprio messaggio di conoscere la trappola e la lasciava aperta.

    Mutazione che lo uccide: ritipare `fixed_nset` da `NomeSetDiFaccia` a
    `NomeSet`. Il nome resta minuscolo e l'errore torna a valle.
    """
    analisi = config.AnalysisConfig(material=MATERIALE, fixed_nset=nome.casefold())
    assert analisi.fixed_nset == nome


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_il_nset_del_carico_in_sommita_canonicalizza_il_nome_dei_sei(nome):
    """Terzo campo dello stesso spazio di nomi, stessa regola.

    `CaricoSommita(nset='top')` era accettato e sollevava dentro `write_inp`,
    a mesh gia' costruita.

    Mutazione che lo uccide: ritipare `CaricoSommita.nset` da
    `NomeSetDiFaccia` a `NomeSet`.
    """
    carico = config.CaricoSommita(risultante=1000.0, nset=nome.casefold())
    assert carico.nset == nome


def test_un_nome_di_set_che_non_e_fra_i_sei_resta_come_scritto():
    """La normalizzazione tocca i sei nomi di faccia, non ogni stringa.

    `NomeSetDiFaccia` non e' un `Literal`: un nome fuori dai sei passa
    intatto e chi lo rifiuta e' la guardia a valle, che sa quali insiemi il
    deck contiene davvero e li elenca nel messaggio.

    Mutazione che lo uccide: rendere il caso canonico incondizionatamente,
    per esempio con `.upper()`. `montante` diventerebbe `MONTANTE`.
    """
    assert config.AnalysisConfig(material=MATERIALE, fixed_nset="montante").fixed_nset == "montante"


def test_selettore_nset_gia_canonico_non_solleva_e_resta_intatto():
    """Ingresso degenere: un nome gia' nel caso canonico non e' toccato.

    Mutazione che lo uccide: far sollevare `_caso_canonico_dei_sei` quando la
    mappa restituisce il nome che ha ricevuto.
    """
    selettore = config.SelettoreNset(tipo="nset", nome="TOP")
    assert selettore.nome == "TOP"


def test_due_selettori_che_differiscono_solo_per_caso_collidono():
    """Due chiavi distinte nel dizionario Python sono lo stesso nome nel deck
    (stessa misura di docs/fase-6-cantiere/sonda-caso-nomi/README.md).

    Mutazione che lo uccide: controllare solo la collisione coi sei nomi
    di faccia, senza confrontare i selettori dell'operatore fra loro.
    """
    with pytest.raises(ValidationError) as scoppio:
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={
                "piastra": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 1.0},
                "PIASTRA": {"tipo": "sfera", "centro": [1.0, 1.0, 1.0], "raggio": 2.0},
            },
        )
    messaggio = str(scoppio.value)
    assert "piastra" in messaggio
    assert "PIASTRA" in messaggio


@pytest.mark.parametrize("nome", ["nome invalido", "piastra!"])
def test_un_nome_di_selettore_con_spazio_o_simbolo_e_rifiutato(nome):
    """`NomeSet` finisce interpolato in un deck ascii: spazi e simboli non ci stanno.

    Mutazione che lo uccide: allargare il pattern di `NomeSet` (per
    esempio a `.+` invece di `^[A-Za-z0-9_.-]+$`).
    """
    with pytest.raises(ValidationError):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={nome: {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 1.0}},
        )


def test_un_selettore_dichiarato_e_mai_citato_non_e_un_errore():
    """Dichiarare e non usare e' lecito: e' un appunto, non un difetto.

    Mutazione che lo uccide: un validatore che pretende che ogni
    selettore sia citato da almeno un carico.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={"mai_usato": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 1.0}},
    )
    assert "mai_usato" in cfg.selettori


def test_i_sei_nomi_dichiarati_sono_quelli_che_il_deck_fabbrica():
    """La costante e build_node_sets non possono divergere in silenzio.

    Verifica la corrispondenza semantica, non solo l'insieme e l'ordine
    delle chiavi: ogni nodo di controllo sta all'estremo giusto su un solo
    asse, quindi finisce in un solo set atteso. Un controllo che guardasse
    solo `set(insiemi) == set(NOMI_SET_DI_FACCIA)` non lo scoprirebbe.

    Mutazione che lo uccide: scambiare due nomi adiacenti in
    NOMI_SET_DI_FACCIA senza toccare `criteri` in build_node_sets. Le
    chiavi restano le stesse sei nello stesso ordine, ma ciascuna riceve
    il criterio del vicino: BASE prenderebbe i nodi a z massima invece
    che minima, e solo un controllo per contenuto lo nota.
    """
    from meshrec.core import abaqus

    nodi = np.array([
        [5.0, 5.0, 0.0],  # z minima, altrove al centro -> solo BASE
        [5.0, 5.0, 10.0],  # z massima, altrove al centro -> solo TOP
        [0.0, 5.0, 5.0],  # x minima, altrove al centro -> solo FACE_FRONT
        [10.0, 5.0, 5.0],  # x massima, altrove al centro -> solo FACE_BACK
        [5.0, 0.0, 5.0],  # y minima, altrove al centro -> solo SIDE_LEFT
        [5.0, 10.0, 5.0],  # y massima, altrove al centro -> solo SIDE_RIGHT
        [5.0, 5.0, 5.0],  # centro su tutti e tre gli assi: in nessun set
    ])
    atteso = {
        "BASE": [0], "TOP": [1], "FACE_FRONT": [2], "FACE_BACK": [3],
        "SIDE_LEFT": [4], "SIDE_RIGHT": [5],
    }
    insiemi = abaqus.build_node_sets(nodi, 0.01)
    assert tuple(insiemi) == config.NOMI_SET_DI_FACCIA
    for nome, indici in atteso.items():
        assert sorted(insiemi[nome].tolist()) == indici, nome


def _config_con_posizionato(**campi_carico):
    base = {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -12000.0]}
    base.update(campi_carico)
    return crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={"piastra": {"tipo": "box", "min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]}},
        carichi=config.CarichiConfig(posizionati=[base]),
    )


def test_un_posizionato_porta_nome_selettore_e_forza():
    """La forma minima di un carico posizionato entra e si rilegge.

    Mutazione che lo uccide: predefinito `None` su `posizionati` invece
    della tupla vuota. `cfg.carichi.posizionati[0]` diventa un TypeError.
    """
    cfg = _config_con_posizionato()
    assert cfg.carichi.posizionati[0].nome == "PRESSA"
    assert cfg.carichi.posizionati[0].forza == (0.0, 0.0, -12000.0)
    assert cfg.carichi.posizionati[0].momento is None


def test_senza_posizionati_la_tupla_e_vuota():
    """Chi non dichiara carichi posizionati ottiene (), non None.

    Mutazione che lo uccide: `default=None`. Il codice a valle itera.
    """
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.carichi.posizionati == ()


def test_il_momento_rifiuta_modulo_o_braccio_non_positivi():
    """Un momento a modulo o braccio nullo o negativo non descrive una coppia.

    Stessa convenzione di `test_il_coefficiente_di_spinta_rifiuta_lo_zero_e_il_negativo`
    per `Field(gt=0.0)`.

    Mutazione che lo uccide: togliere `gt=0.0` da `Momento.modulo` o
    `Momento.braccio`. Entrambe le chiamate smettono di sollevare.
    """
    with pytest.raises(ValidationError):
        config.Momento(asse=[0.0, 0.0, 1.0], modulo=0.0, braccio=1.0)
    with pytest.raises(ValidationError):
        config.Momento(asse=[0.0, 0.0, 1.0], modulo=-1.0, braccio=1.0)
    with pytest.raises(ValidationError):
        config.Momento(asse=[0.0, 0.0, 1.0], modulo=1.0, braccio=0.0)
    with pytest.raises(ValidationError):
        config.Momento(asse=[0.0, 0.0, 1.0], modulo=1.0, braccio=-1.0)


def test_il_momento_rifiuta_lasse_nullo():
    """Un asse [0, 0, 0] non e' una direzione: si vede dalla configurazione, senza mesh.

    Mutazione che lo uccide: togliere il validatore sul modulo di `asse`.
    Il momento entra con una direzione che non esiste.
    """
    with pytest.raises(ValidationError, match="asse"):
        config.Momento(asse=[0.0, 0.0, 0.0], modulo=1.0, braccio=1.0)


def test_un_carico_dichiara_o_forza_o_momento_mai_entrambi():
    """Forza e momento insieme sono due carichi: due voci, non una.

    Mutazione che lo uccide: un validatore che controlla solo il caso
    "nessuno dei due". Questo test cade, l'altro passa.
    """
    with pytest.raises(ValidationError, match="uno solo"):
        _config_con_posizionato(momento={"asse": [0.0, 0.0, 1.0], "modulo": 1.0, "braccio": 1.0})


def test_un_carico_senza_forza_ne_momento_e_rifiutato():
    """Un carico che non dice quanto vale non e' un carico.

    Mutazione che lo uccide: un validatore che controlla solo il caso
    "entrambi". Questo test cade, l'altro passa.
    """
    with pytest.raises(ValidationError, match="uno solo"):
        _config_con_posizionato(forza=None)


def test_la_forza_nulla_e_rifiutata():
    """Un vettore forza di modulo zero scriverebbe un passo che non carica nulla.

    Mutazione che lo uccide: togliere il controllo sul modulo. Il carico
    entra e produce un passo statico identico al peso proprio, con un
    nome che promette altro.
    """
    with pytest.raises(ValidationError, match="modulo"):
        _config_con_posizionato(forza=[0.0, 0.0, 0.0])


def test_un_carico_che_cita_un_selettore_non_dichiarato_e_rifiutato():
    """Il riferimento si controlla senza mesh: e' un rifiuto a validazione.

    Mutazione che lo uccide: spostare il controllo a valle, dove il
    sintomo sarebbe "zero nodi" e si confonderebbe con altri quattro.
    """
    with pytest.raises(ValidationError, match="fantasma"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(
                posizionati=[{"nome": "PRESSA", "selettore": "fantasma", "forza": [0.0, 0.0, -1.0]}]
            ),
        )


def test_un_carico_puo_citare_il_selettore_cambiando_le_maiuscole():
    """Il selettore dichiarato 'piastra' e citato 'Piastra' sono lo stesso *NSET nel deck.

    Stessa regola del confronto sui riservati e sulla chiave di `visti`:
    ignora il caso, come misurato in docs/fase-6-cantiere/sonda-caso-nomi/.

    Il carico e' normalizzato al nome canonico dichiarato ('piastra', non
    'Piastra'): a valle (`core/abaqus.py`) il confronto con `nset_selettori`
    e' un'uguaglianza esatta, e senza questa normalizzazione un carico
    validato qui sollevava comunque in `write_inp` con un messaggio che
    negava una dichiarazione vera.

    Mutazione che lo uccide: togliere `.casefold()` dal confronto fra
    `carico.selettore` e le chiavi di `self.selettori`. Il carico verrebbe
    rifiutato con "non e' dichiarato", messaggio falso perche' dichiarato
    lo e' davvero.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
        carichi=config.CarichiConfig(
            posizionati=[{"nome": "PRESSA", "selettore": "Piastra", "forza": [0.0, 0.0, -1.0]}]
        ),
    )
    assert cfg.carichi.posizionati[0].selettore == "piastra"


@pytest.mark.parametrize("riservato", config.NOMI_PASSO_RISERVATI)
def test_un_carico_non_puo_chiamarsi_come_un_passo_riservato(riservato):
    """Il nome del carico diventa il nome del passo, e tre nomi sono gia' presi.

    Mutazione che lo uccide: controllare solo CARICO_TOP.
    """
    with pytest.raises(ValidationError, match=riservato):
        _config_con_posizionato(nome=riservato)


@pytest.mark.parametrize("variante", ["carico_top", "Modale", "Spinta_Orizzontale", "gravita"])
def test_il_nome_riservato_e_preso_anche_cambiando_le_maiuscole(variante):
    """Stessa regola dei selettori: il confronto sui nomi ignora il caso.

    `gravita` e' il predefinito di `analysis.step_name`, che non sta fra i
    riservati ma e' preso lo stesso.

    Mutazione che lo uccide: togliere `.casefold()` dal confronto coi
    riservati. Tutte e quattro le varianti passano la validazione.
    """
    with pytest.raises(ValidationError, match="già preso"):
        _config_con_posizionato(nome=variante)


def test_due_posizionati_che_differiscono_solo_per_caso_collidono():
    """Due passi omonimi a meno del caso sono indistinguibili nel rapporto.

    Mutazione che lo uccide: togliere `.casefold()` dalla chiave di
    `visti`. I due carichi passano e il deck esce con due passi che
    solo una lettura attenta distingue.
    """
    with pytest.raises(ValidationError, match="PRESSA"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(posizionati=[
                {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -1.0]},
                {"nome": "pressa", "selettore": "piastra", "forza": [0.0, 0.0, -2.0]},
            ]),
        )


def test_due_posizionati_non_possono_avere_lo_stesso_nome():
    """Due passi omonimi nel deck: i due risultati diventano indistinguibili.

    Mutazione che lo uccide: togliere il controllo di unicita'. Il deck
    esce con due `** NOME PASSO: PRESSA`.
    """
    with pytest.raises(ValidationError, match="PRESSA"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(posizionati=[
                {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -1.0]},
                {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -2.0]},
            ]),
        )


@pytest.mark.parametrize("cattivo", ["con spazio", "BASE\n*BOUNDARY\nTOP, 1, 3", "base!"])
def test_fixed_nset_e_step_name_rifiutano_i_nomi_non_scrivibili(cattivo):
    """I due campi rimasti `str` nudi quando la fase ha introdotto `NomeSet`.

    `fixed_nset` finisce interpolato in `*BOUNDARY` e confrontato con i sei
    nomi di faccia; `step_name` finisce dopo `** NOME PASSO:` e in una
    chiave del `.vtu`, dove uno spazio o un a capo scrivono una riga
    vagante nel deck.

    Mutazione che lo uccide: riportare i due campi a `str`. Ogni nome
    passa e il rifiuto sparisce.
    """
    with pytest.raises(ValidationError):
        config.AnalysisConfig(material=MATERIALE, fixed_nset=cattivo)
    with pytest.raises(ValidationError):
        config.AnalysisConfig(material=MATERIALE, step_name=cattivo)


def test_il_quadratico_e_dichiarabile_ed_e_il_predefinito():
    """Il writer ha imparato a scrivere i dieci nodi (#45), e il rifiuto cade.

    Questo test sostituisce `test_c3d10_non_e_dichiarabile_finche_il_writer_non_lo_gestisce`,
    il cui stesso nome dichiarava di essere temporaneo. Il rifiuto era giusto
    finche' un deck C3D10 sarebbe uscito muto invece che sbagliato; ora la
    connettivita' passa per `volume.TETGEN_A_ABAQUS` e i nodi di lato finiscono
    dove il solutore li aspetta.

    Il predefinito e' il **quadratico**: il manuale CalculiX dice del lineare
    «not suited for structural calculations... the element is too stiff», e la
    suite di verifica ufficiale non contiene un solo deck C3D4 su 610.

    Mutazione che lo uccide: riportare il predefinito a `C3D4`.
    """
    assert config.TetConfig().element == "C3D10"
    assert config.TetConfig(element="C3D4").element == "C3D4", (
        "il lineare resta dichiarabile: serve a misurare quanto la sua rigidita' costi"
    )


def test_un_elemento_che_il_deck_non_sa_scrivere_e_rifiutato_prima_della_corsa():
    """Il rifiuto sta nella validazione della configurazione, non a valle.

    E' la meta' buona di `66b526d`, da non perdere: un tipo sconosciuto
    fermava la corsa **dopo** l'intera tetraedrizzazione, cioe' al punto di
    massimo spreco.
    """
    for sconosciuto in ("C3D20", "C3D10M", "TET4", ""):
        with pytest.raises(ValidationError):
            config.TetConfig(element=sconosciuto)
