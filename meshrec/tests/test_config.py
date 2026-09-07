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

    E' l'unico ingresso degenere senza sintomo: gli altri almeno risolvono
    zero elementi. Una regione corretta e riscritta sotto lo stesso nome
    verrebbe scritta nel deck nella versione che l'operatore credeva di aver
    sostituito.

    Mutazione che lo uccide: tornare a `yaml.safe_load`. Il file viene letto,
    `membratura` vale 1 e nessuno sa che lo 0 c'era.
    """
    percorso = tmp_path / "config.yaml"
    percorso.write_text(
        "input:\n  path: nuvola.ply\n"
        "analysis:\n  material:\n    name: MURATURA\n    young: 1500.0\n"
        "    poisson: 0.2\n    density: 1.8e-9\n"
        "regioni:\n"
        "  pilastro:\n    membratura: 0\n"
        "    materiale:\n      material:\n        name: MURATURA\n"
        "        young: 1500.0\n        poisson: 0.2\n        density: 1.8e-9\n"
        "      provenienza: a_mano\n      norma: NTC 2018 Tab. 4.1.I\n"
        "  pilastro:\n    membratura: 1\n"
        "    materiale:\n      material:\n        name: MURATURA\n"
        "        young: 1500.0\n        poisson: 0.2\n        density: 1.8e-9\n"
        "      provenienza: a_mano\n      norma: NTC 2018 Tab. 4.1.I\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pilastro"):
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
        ("lab.yaml", "3e72227dcbb1dc20bf14763402aab60c1a65893e78321b8f8fc013b9a966b097"),
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

    **L'impronta di `lab.yaml` e' cambiata apposta il 30/08/2026**, e questo e'
    il posto in cui si dichiara. La densita' del calcestruzzo e' passata da
    2,5e-9 a 2,5493e-9 t/mm^3, che e' il valore di norma per il calcestruzzo
    ARMATO (NTC 2018 Tab. 3.1.I, 25,0 kN/m^3) e quello che il catalogo dei
    materiali gia' porta: il provino di `lab_frame` e' un telaio in cemento
    armato, quindi il valore di prima era quello sbagliato di 1,972%. Deciso
    dall'utente.

    Il prezzo, e va saputo: uno sweep lanciato da oggi su questa base produce
    cartelle diverse da quelle delle ventidue righe gia' registrate. Le righe
    restano valide e leggibili -- ognuna porta la propria configurazione -- ma
    non si rigenerano piu' da qui. `casi/muro.yaml` non e' toccato: e'
    muratura, e 1,8e-9 e' il suo valore giusto.
    """
    from meshrec.core.sweep import fingerprint

    percorso = Path(__file__).resolve().parents[1] / "casi" / caso

    assert fingerprint(config.load_config(percorso)) == impronta


def test_i_blocchi_nuovi_stanno_in_pipelineconfig_e_nella_lista_di_esclusione_giusta():
    """I blocchi che viaggiano con la configurazione ma non entrano
    nell'impronta allo stesso modo.

    `wall` e `model` ne restano sempre fuori: nessun asse della Fase 2 li tocca
    e non cambiano il deck.

    L'ultima asserzione e' quella che smentisce: un blocco nelle due liste
    insieme sarebbe una contraddizione, "sempre fuori" e "fuori solo se vuoto".

    `solutore` stava nell'esclusione **secca** ed e' uscito col blocco (mappa
    #161): l'esclusione era secca, quindi la sua uscita non muove le ventidue
    righe -- che e' precisamente la ragione per cui ci stava.

    `regioni` (#135, #141, #136) e' l'unico rimasto nell'esclusione
    **condizionata**: STEP_BLOCKS[11] lo legge e cambia il deck, quindi due
    candidati con regioni diverse sono esperimenti diversi. E' un `dict` che
    nasce `{}` -- cioe' falso -- ed e' per questo che il blocco e' un
    dizionario a chiavi libere e non un modello con campi: un modello
    porterebbe i propri predefiniti, e basta un campo truthy fra quelli perche'
    l'omissione non scatti mai. Misurato il 22/08/2026 sulle 22 righe di
    experiments/muro e experiments/lab_crop: l'esclusione condizionata ne
    cambia 0 su 22, l'inclusione secca 22 su 22.
    """
    from meshrec.core.sweep import BLOCCHI_FUORI_IMPRONTA, BLOCCHI_VUOTI_FUORI_IMPRONTA

    campi = set(PipelineConfig.model_fields)
    assert {"wall", "model"} <= campi
    assert set(BLOCCHI_FUORI_IMPRONTA) == {"run", "wall", "model"}
    assert set(BLOCCHI_VUOTI_FUORI_IMPRONTA) == {"regioni"}
    assert set(BLOCCHI_FUORI_IMPRONTA) <= campi
    assert set(BLOCCHI_VUOTI_FUORI_IMPRONTA) <= campi
    assert not set(BLOCCHI_FUORI_IMPRONTA) & set(BLOCCHI_VUOTI_FUORI_IMPRONTA)


@pytest.mark.parametrize("riservato", ["SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"])
def test_step_name_non_puo_ripetere_un_nome_di_caso_di_carico(riservato):
    """M13 della revisione finale: i tre nomi erano le etichette che il deck
    assegnava da se' agli altri passi, e che indicizzano i campi per nodo del
    file risolto. Col deck nudo nessun passo li scrive piu', ma un `.vtu` di
    una corsa vecchia li porta ancora: con `analysis.step_name:
    SPINTA_ORIZZONTALE` la chiave non direbbe piu' quale passo l'ha prodotta.
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


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_fixed_nset_canonicalizza_il_nome_dei_sei(nome):
    """`fixed_nset: base` nello YAML non deve morire dopo la tetraedralizzazione.

    Misurato prima di questa correzione: `AnalysisConfig(fixed_nset='base')`
    passava la validazione, faceva girare la mesh di volume per minuti, e
    solo allora `export_model` sollevava. `ccx` risolve gli `*NSET` senza
    distinguere le maiuscole (`docs/fase-6-cantiere/sonda-caso-nomi/README.md`)
    e il nome va normalizzato dove si dichiara, non dove si usa. La guardia in
    `abaqus.write_inp` dichiarava nel proprio messaggio di conoscere la
    trappola e la lasciava aperta.

    Mutazione che lo uccide: ritipare `fixed_nset` da `NomeSetDiFaccia` a
    `NomeSet`. Il nome resta minuscolo e l'errore torna a valle.
    """
    analisi = config.AnalysisConfig(material=MATERIALE, fixed_nset=nome.casefold())
    assert analisi.fixed_nset == nome


def test_un_nome_di_set_che_non_e_fra_i_sei_resta_come_scritto():
    """La normalizzazione tocca i sei nomi di faccia, non ogni stringa.

    `NomeSetDiFaccia` non e' un `Literal`: un nome fuori dai sei passa
    intatto e chi lo rifiuta e' la guardia a valle, che sa quali insiemi il
    deck contiene davvero e li elenca nel messaggio.

    Mutazione che lo uccide: rendere il caso canonico incondizionatamente,
    per esempio con `.upper()`. `montante` diventerebbe `MONTANTE`.
    """
    assert config.AnalysisConfig(material=MATERIALE, fixed_nset="montante").fixed_nset == "montante"


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


def test_una_configurazione_si_rilegge_con_e_senza_i_blocchi_che_non_esistono_piu(tmp_path):
    """La cerniera regge in tutte e due i versi.

    Un blocco **aggiunto** non puo' rendere illeggibile cio' che e' gia' stato
    scritto: e' la regola dell'omissione che tiene ferme le 22 righe dei
    registri. Un blocco **tolto** nemmeno, ed e' la meta' che serve adesso: le
    `config.yaml` gia' su disco portano un `solutore:` che la mappa #161 ha
    tolto, e i blocchi che il deck nudo ha tolto con la PR 1 -- `carichi:`,
    `selettori:`, e le due chiavi laterali dentro `model:`. Devono continuare
    ad aprirsi: `runs/geoandgeo-lab/config.yaml` li porta ancora tutti.

    Ignorati e non rifiutati, in questa PR: il rifiuto nominato dei blocchi
    usciti e' un'altra decisione e arriva dopo.

    Mutazione che lo uccide: `extra="forbid"` su `_ModelloBase`.
    """
    minima = tmp_path / "minima.yaml"
    minima.write_text("input:\n  path: nuvola.ply\n", encoding="utf-8")
    cfg = config.load_config(minima)
    assert cfg.regioni == {}

    # I blocchi usciti, come li scrivono le corse gia' fatte: `solutore:` con
    # la mappa #161, gli altri col deck nudo.
    vecchia = tmp_path / "vecchia.yaml"
    vecchia.write_text(
        "input:\n  path: nuvola.ply\n"
        "solutore:\n  nome: calculix\n  percorso: null\n"
        "carichi:\n"
        "  spinta:\n    coefficiente: 0.1\n    asse: y\n"
        "  carico_sommita:\n    risultante: 1200.0\n    nset: TOP\n"
        "  modale: {}\n"
        "selettori:\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 5.0\n"
        "model:\n  lateral_nset: LATO\n  lateral_pressure: 0.05\n",
        encoding="utf-8",
    )
    riletta = config.load_config(vecchia)
    for uscito in ("solutore", "carichi", "selettori"):
        assert not hasattr(riletta, uscito), f"il blocco {uscito} e' uscito e non deve tornare"
    assert not hasattr(riletta.model, "lateral_nset")
    assert not hasattr(riletta.model, "lateral_pressure")
    assert riletta.regioni == {}


def _materiale_dichiarato(**campi) -> dict:
    """Un `MaterialeDichiarato` come lo scrive l'operatore, coi minimi ammessi."""
    return {
        "material": MATERIALE.model_dump(),
        "provenienza": "a_mano",
        "norma": "NTC 2018 Tab. 4.1.I",
        **campi,
    }


def _regione(**campi) -> dict:
    return {"membratura": 0, "materiale": _materiale_dichiarato(), **campi}


def test_le_regioni_vuote_escono_dall_impronta_e_dal_payload():
    """`regioni` nasce `{}`, cioe' falso: e' la ragione per cui il blocco e' un
    dizionario e non un modello con campi.

    Il predicato di `sweep.fingerprint` e' `not any(payload[blocco].values())`:
    un modello con anche un solo campo dal predefinito truthy renderebbe il
    blocco sempre non vuoto, l'omissione non scatterebbe mai, e le ventidue
    righe dei registri si muoverebbero.
    """
    from meshrec.core.sweep import fingerprint

    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))

    assert cfg.regioni == {}
    assert cfg.model_dump(mode="json")["regioni"] == {}
    # Il blocco esce dal payload che l'impronta hasha: e' l'omissione a
    # tenere ferme le ventidue righe, non un caso.
    assert "regioni" not in _payload_dell_impronta(cfg)
    assert fingerprint(cfg) == fingerprint(config.PipelineConfig.model_validate(
        {k: v for k, v in cfg.model_dump(mode="json").items() if k != "regioni"}
    ))


def _payload_dell_impronta(cfg) -> dict:
    """I blocchi che `sweep.fingerprint` hasha davvero, ricostruiti come li' dentro."""
    from meshrec.core.sweep import BLOCCHI_FUORI_IMPRONTA, BLOCCHI_VUOTI_FUORI_IMPRONTA

    payload = cfg.model_dump(mode="json")
    for blocco in BLOCCHI_FUORI_IMPRONTA:
        payload.pop(blocco, None)
    for blocco in BLOCCHI_VUOTI_FUORI_IMPRONTA:
        if not any((payload.get(blocco) or {}).values()):
            payload.pop(blocco, None)
    return payload


def test_una_regione_dichiarata_entra_nell_impronta():
    """L'altra meta' dell'omissione: il blocco che porta qualcosa conta.

    Due candidati con regioni diverse sono esperimenti diversi -- lo step 11
    li legge e il deck cambia -- e senza questa distinzione il secondo
    sovrascriverebbe il primo in silenzio, con la stessa cartella
    `fingerprint(cfg)[:12]`.
    """
    from meshrec.core.sweep import fingerprint

    vuota = crea_config(input=config.InputConfig(path="nuvola.ply"))
    piena = crea_config(input=config.InputConfig(path="nuvola.ply"), regioni={"pilastro": _regione()})

    assert "regioni" in _payload_dell_impronta(piena)
    assert fingerprint(piena) != fingerprint(vuota)


def test_una_regione_e_una_membratura_e_il_suo_materiale():
    """Due campi e basta: il prisma e cio' che il deck gli scrive dentro.

    Portava una `sezione` con tre materiali e l'armatura, perche' una sezione a
    fibre se li porta dentro. Uscito il solutore a fibre con la mappa #161, di
    quei quattro il deck ne leggeva uno.

    Mutazione che lo uccide: rimettere un secondo materiale che nessuno legge.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        regioni={"trave": _regione()},
    )

    regione = cfg.regioni["trave"]
    assert regione.membratura == 0
    assert regione.materiale.material.name
    assert set(config.RegioneConfig.model_fields) == {"membratura", "materiale"}


def test_il_materiale_dichiarato_non_ha_una_veste_da_scegliere():
    """#141 senza eccezioni: le voci sono **sempre** caratteristiche.

    Il programma deriva i valori di progetto applicando i coefficienti di
    norma. Un campo che permettesse di dichiarare «questo valore e' gia'
    ridotto» aprirebbe la strada a una doppia riduzione o a nessuna, senza che
    nulla se ne accorga. Le parole «gia' ridotte» di #146 riguardano il fattore
    di confidenza e il livello di conoscenza, che valgono sulla muratura e non
    su un calcestruzzo.

    Il test guarda il comportamento e non la prosa: asserire sottostringhe di
    una `description` si sarebbe rotto riscrivendo quella descrizione senza che
    nulla cambiasse, e sarebbe restato verde con un campo `veste` chiamato in
    un altro modo.

    Mutazione che lo uccide: reintrodurre un campo qualsiasi su
    `MaterialeDichiarato` -- il modello smette di rifiutare la chiave in piu'.
    """
    # L'insieme esatto dei campi, non la sola assenza di `veste`: un campo che
    # facesse la stessa cosa sotto un altro nome («qualita», «stato»...)
    # passerebbe un `not in` e non passa questo.
    assert set(config.MaterialeDichiarato.model_fields) == {
        "material", "f_k", "provenienza", "classe", "norma",
    }
    # `f_k` e' e resta caratteristica: il dominio che lo dice e' il positivo
    # stretto, non la prosa. Togliere `gt=0.0` lasciava la suite verde.
    assert config.MaterialeDichiarato.model_validate(
        _materiale_dichiarato(f_k=25.0)
    ).f_k == 25.0
    for storto in (0.0, -25.0):
        with pytest.raises(ValidationError):
            config.MaterialeDichiarato.model_validate(_materiale_dichiarato(f_k=storto))


def test_la_provenienza_da_catalogo_pretende_la_classe_e_a_mano_la_rifiuta():
    """I due campi si dichiaravano indipendenti: `provenienza='catalogo'` senza
    `classe` passava, e `provenienza='a_mano'` con `classe` pure.

    E' il difetto preciso che #141 esiste per impedire: in onda 2 si cercherebbe
    nel catalogo una classe `None`, oppure la tabella di provenienza della tesi
    direbbe «da catalogo» senza dire quale voce.

    Mutazione che lo uccide: togliere il validatore. Entrambe le chiamate
    passano e la provenienza smette di essere verificabile.
    """
    with pytest.raises(ValidationError, match="catalogo"):
        config.MaterialeDichiarato.model_validate(
            _materiale_dichiarato(provenienza="catalogo")
        )
    with pytest.raises(ValidationError, match="catalogo"):
        config.MaterialeDichiarato.model_validate(
            _materiale_dichiarato(provenienza="a_mano", classe="C25/30")
        )
    dal_catalogo = config.MaterialeDichiarato.model_validate(
        _materiale_dichiarato(provenienza="catalogo", classe="C25/30")
    )
    assert dal_catalogo.classe == "C25/30"
    assert config.MaterialeDichiarato.model_validate(
        _materiale_dichiarato(provenienza="a_mano")
    ).classe is None


@pytest.mark.parametrize("vuota", ["", "   "])
def test_la_norma_di_un_materiale_dichiarato_non_puo_essere_vuota(vuota):
    """Per la sua stessa descrizione `norma` e' cio' che distingue un valore di
    norma da uno inventato: vuota, passava e finiva in tabella.

    Mutazione che lo uccide: togliere `min_length=1` dal vincolo di `norma`.
    """
    with pytest.raises(ValidationError):
        config.MaterialeDichiarato.model_validate(_materiale_dichiarato(norma=vuota))


def test_due_regioni_che_differiscono_solo_per_maiuscole_sono_rifiutate():
    """Misurata in docs/fase-6-cantiere/sonda-caso-nomi/: `ccx` risolve i nomi di insieme
    senza distinguere le maiuscole, quindi due chiavi distinte nel dizionario
    python sono un solo nome nel deck.
    """
    with pytest.raises(ValidationError, match="maiuscole") as rifiuto:
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            regioni={"pilastro": _regione(), "PILASTRO": _regione(membratura=1)},
        )
    assert "le regioni" in str(rifiuto.value)


@pytest.mark.parametrize("nome", ["ALL_WALL", "all_wall", "All_Wall"])
def test_una_regione_che_collide_con_lelset_fabbricato_e_rifiutata(nome):
    """`ALL_WALL` e' l'unico `*ELSET` che il deck fabbrica da se'
    (`abaqus.write_inp`, parametro `elset`, scritto in `*ELEMENT` e in
    `*SOLID SECTION`): e' l'insieme che le regioni partizionano, e una regione
    omonima farebbe prendere alla `*SOLID SECTION` la partizione sbagliata --
    il muro intero riceverebbe il materiale di una regione.

    Mutazione che lo uccide: rimettere `NOMI_SET_DI_FACCIA` come lista
    confrontata anche per gli `*ELSET`. Tutte e tre le varianti passano.
    """
    with pytest.raises(ValidationError, match="collide") as rifiuto:
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            regioni={nome: _regione()},
        )
    # Il messaggio si legge a video, in `/api/config`: «il regione» no.
    assert "la regione" in str(rifiuto.value)
    assert "*ELSET" in str(rifiuto.value)
    assert "ALL_WALL" in str(rifiuto.value)


@pytest.mark.parametrize("nome", ["BASE", "top", "Side_Left"])
def test_una_regione_puo_chiamarsi_come_un_set_di_faccia(nome):
    """I sei di faccia sono `*NSET` e una regione e' un `*ELSET`: nel deck sono
    due spazi di nomi distinti, e rifiutare qui il nome innocuo mentre passava
    `ALL_WALL` era il controllo esattamente rovesciato.

    Sta accanto al test del rifiuto apposta: senza, «confronta con i nomi
    fabbricati del proprio tipo di set» e «confronta con tutti i nomi
    fabbricati» sarebbero indistinguibili.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        regioni={nome: _regione()},
    )
    assert nome in cfg.regioni


@pytest.mark.parametrize("nome", ["", "pi lastro", "regione!"])
def test_un_nome_di_regione_con_spazio_o_simbolo_e_rifiutato(nome):
    """Il nome di una regione finisce interpolato in un deck ascii, come
    `*ELSET`, e otto rami lo leggeranno.

    Mutazione che lo uccide: ritipare `regioni` da `dict[NomeSet, ...]` a
    `dict[str, ...]`. Il rifiuto oggi viene dal tipo e da nessuna prova.
    """
    with pytest.raises(ValidationError):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            regioni={nome: _regione()},
        )


def test_una_membratura_negativa_e_rifiutata_dalla_configurazione():
    """`membratura` e' un indice nel prior: negativo non e' un indice.

    Il tetto -- quante membrature il prior ha trovato davvero -- **non** e'
    verificabile qui: `12_wall.json` non e' visibile alla configurazione, che
    nasce prima che lo step 12 giri. Il rifiuto dell'indice fuori intervallo
    spetta a chi legge il prior, e questa configurazione non puo' fingere di
    saperlo.
    """
    with pytest.raises(ValidationError):
        config.RegioneConfig.model_validate(_regione(membratura=-1))
    assert config.RegioneConfig.model_validate(_regione(membratura=99)).membratura == 99


def test_le_regioni_convivono_con_un_analisi_assente():
    """`analysis` e' `X | None` e un validatore che lo legge diritto cade sulla
    nuvola appena caricata: e' gia' successo una volta.

    Una corsa nasce dalla sola nuvola: le regioni possono essere dichiarate
    prima che il materiale unico della corsa esista.
    """
    cfg = config.PipelineConfig(
        input=config.InputConfig(path="nuvola.ply"),
        regioni={"pilastro": _regione()},
    )

    assert cfg.analysis is None
    assert set(cfg.regioni) == {"pilastro"}


def test_le_regioni_sopravvivono_al_giro_su_disco(tmp_path):
    percorso = tmp_path / "config.yaml"
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        regioni={"pilastro": _regione()},
    )
    config.save_config(cfg, percorso)

    riletta = config.load_config(percorso)

    assert riletta.model_dump() == cfg.model_dump()


def test_una_corsa_di_pipeline_finisce_allo_step_11_e_il_tetto_e_il_dodici():
    """Il predefinito segue il perimetro del prodotto, non il tetto.

    Il prodotto va dalla nuvola al deck `.inp` e si chiude li', mentre il prior
    geometrico dello step 12 misura la scansione e sta fuori dal perimetro: il
    predefinito e' 11.

    Il tetto e' 12 da quando il solutore e' uscito con la mappa #161. Chi
    chiede il prior esplicitamente lo ottiene ancora: la capacita' non si
    perde, smette solo di essere cio' che accade senza chiederlo.

    `run` sta in BLOCCHI_FUORI_IMPRONTA, quindi questo cambio non puo' muovere
    l'impronta delle ventidue righe: lo verificano i due test dell'impronta,
    con i loro numeri intatti.

    Mutazione che lo uccide: riportare il predefinito a 12. Una corsa senza
    argomenti tornerebbe a calcolare il prior, che i documenti dichiarano fuori
    perimetro.
    """
    predefinito = config.RunConfig()

    assert predefinito.to_step == 11
    assert config.RunConfig(to_step=12).to_step == 12
    with pytest.raises(ValidationError):
        config.RunConfig(to_step=13)
    # from_step e to_step uguali eseguono soltanto quello step.
    solo_il_dodici = config.RunConfig(from_step=9, to_step=9)
    assert solo_il_dodici.from_step == solo_il_dodici.to_step == 9

    descrizione = config.RunConfig.model_fields["to_step"].description
    assert "il predefinito coincide con esso" not in descrizione, (
        "la descrizione afferma ancora una coincidenza col tetto che non c'e' piu'"
    )


def test_pipeline_config_non_ha_piu_carichi_ne_selettori():
    """Dalla PR 1 del deck nudo la configurazione non porta piu' carichi,
    selettori ne' pressione laterale: le classi stesse escono dal modulo."""
    campi = set(config.PipelineConfig.model_fields)

    assert "carichi" not in campi
    assert "selettori" not in campi
    assert not hasattr(config, "CarichiConfig")
    assert not hasattr(config, "Selettore")
    assert "lateral_pressure" not in config.ModelConfig.model_fields
