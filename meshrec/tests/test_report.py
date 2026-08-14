"""Il report si genera dal registro e non da altro."""

import inspect
import json
import struct
import zlib
from pathlib import Path

from meshrec.core import pipeline, report, steps, sweep
from meshrec.core.config import InputConfig, PipelineConfig, save_config


def _png_minimo() -> bytes:
    """Un PNG 1x1 vero, costruito qui: la sola firma non e' un'immagine.

    La fixture precedente scriveva gli otto byte della firma, e il report li
    incorporava: un riquadro rotto stampato in appendice. Un PNG minimo lo si
    costruisce con la libreria standard, senza dipendenze e senza blob opachi.
    """

    def pezzo(tipo: bytes, dati: bytes) -> bytes:
        lunghezza = struct.pack(">I", len(dati))
        return lunghezza + tipo + dati + struct.pack(">I", zlib.crc32(tipo + dati))

    intestazione = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + pezzo(b"IHDR", intestazione)
        + pezzo(b"IDAT", zlib.compress(b"\x00\x00", 0))
        + pezzo(b"IEND", b"")
    )


def _paragrafo(testo: str, ago: str) -> str:
    """Il solo paragrafo che contiene `ago`.

    Cercare un nome di step in tutto il documento non prova niente: compare
    anche nelle intestazioni delle metriche. Le asserzioni sui conteggi devono
    guardare dentro un paragrafo solo.
    """
    prima, dopo = testo.split(ago, 1)
    return prima.rsplit("<p", 1)[1] + ago + dopo.split("</p>", 1)[0]


def test_the_report_lists_every_row_and_marks_the_front(tmp_path):
    registry = tmp_path / "registro.jsonl"
    for mark, error, tets, on_front in (("aaa", 2.0, 1000, True), ("bbb", 40.0, 9000, False)):
        sweep.append_row(
            registry,
            {
                "fingerprint": mark,
                "axes": {"tet.min_ratio": 1.8},
                "outcome": "riuscito",
                "complete": True,
                "on_front": on_front,
                "thickness_error": error,
                "duration_s": 12.0,
                "metrics": {
                    "10_volume_quality": {
                        "tets": tets,
                        "radius_edge_over_reference": 0.08,
                        "min_dihedral_deg": {"median": 38.0},
                    }
                },
            },
        )

    out = report.write_report(registry, tmp_path / "report.html")
    html = out.read_text(encoding="utf-8")

    assert "aaa" in html and "bbb" in html
    # "fronte" compare anche nella prosa statica del report: contare la
    # parola non prova che la marcatura funzioni. tr.fronte e' la classe che
    # write_report assegna solo alle righe con on_front=True (report.py:85),
    # quindi contarne le occorrenze e' l'unica prova che una riga (aaa) e'
    # marcata e l'altra (bbb) no.
    assert html.count("<tr class='fronte'>") == 1
    assert "<svg" in html


def test_the_histogram_is_svg_without_any_chart_library():
    svg = report.histogram_svg([1.0, 2.0, 2.0, 3.0], title="prova", bins=3)

    assert svg.startswith("<svg")
    assert svg.count("<rect") >= 3
    assert "prova" in svg


def test_the_histogram_handles_no_values():
    svg = report.histogram_svg([], title="vuoto", bins=3)

    assert svg.startswith("<svg")
    assert "vuoto" in svg


def test_the_histogram_handles_a_single_value():
    svg = report.histogram_svg([5.0], title="singolo", bins=3)

    assert svg.startswith("<svg")
    assert "<rect" in svg


def test_the_histogram_handles_a_constant_axis():
    svg = report.histogram_svg([5.0, 5.0, 5.0], title="costante", bins=3)

    assert svg.startswith("<svg")
    assert "<rect" in svg


# --- report di una singola corsa ------------------------------------------
#
# Un generatore di documenti si sbaglia producendo qualcosa che *sembra*
# completo: un riquadro vuoto, una riga mancante che si legge come uno zero.
# Nessuno di questi test si ferma a `percorso.exists()`, che passerebbe anche
# con un file vuoto: ognuno smentisce una forma precisa di buco silenzioso.


def _corsa(tmp_path, metriche=None, configurazione=None):
    """Cartella di corsa con i soli file richiesti dal caso in prova."""
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    if metriche is not None:
        (corsa / pipeline.METRICS_FILENAME).write_text(
            json.dumps(metriche), encoding="utf-8"
        )
    if configurazione is not None:
        (corsa / report.CONFIG_FILENAME).write_text(configurazione, encoding="utf-8")
    return corsa


def test_il_report_dichiara_le_viste_assenti(tmp_path):
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})

    percorso = report.write_run_report(corsa, viste=[])
    testo = percorso.read_text(encoding="utf-8")

    assert "nessuna vista catturata" in testo


def test_il_report_esce_anche_senza_metriche_e_lo_dichiara(tmp_path):
    """Una corsa mai eseguita non deve produrre un report che tace il fatto."""
    corsa = _corsa(tmp_path, configurazione="tet:\n  min_ratio: 1.8\n")

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{pipeline.METRICS_FILENAME} assente" in testo
    # nessuno step puo' comparire con una casella vuota, che si leggerebbe
    # come una metrica pari a zero invece che come una metrica mai misurata
    assert "<td></td>" not in testo


def test_il_report_esce_anche_senza_configurazione_e_lo_dichiara(tmp_path):
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{report.CONFIG_FILENAME} assente" in testo
    assert "points_kept" in testo


def test_il_report_elenca_gli_step_senza_metriche(tmp_path):
    """Il caso normale dell'interfaccia: uno step alla volta, gli altri mai."""
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    _, dichiarazione = testo.split(report.SENZA_METRICHE, 1)
    dichiarazione = dichiarazione.split("</p>", 1)[0]
    mancanti = [chiave for chiave in steps.STEP_KEYS if chiave != "01_load"]
    assert all(chiave in dichiarazione for chiave in mancanti)
    assert "01_load" not in dichiarazione


def test_una_vista_il_cui_file_non_esiste_non_diventa_immagine_rotta(tmp_path):
    """Un <img> che non carica e' un buco silenzioso stampato su carta."""
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})

    testo = report.write_run_report(
        corsa, viste=[corsa / "viste" / "fronte.png"]
    ).read_text(encoding="utf-8")

    assert "<img" not in testo
    assert "fronte.png" in testo and "assente" in testo
    assert "1 attese" in testo and "0 presenti" in testo


def test_le_viste_presenti_hanno_percorsi_relativi_al_report(tmp_path):
    """Il report deve restare apribile se la cartella viene spostata."""
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})
    (corsa / "viste").mkdir()
    (corsa / "viste" / "fronte.png").write_bytes(_png_minimo())

    testo = report.write_run_report(
        corsa, viste=[corsa / "viste" / "fronte.png"]
    ).read_text(encoding="utf-8")

    assert 'src="viste/fronte.png"' in testo
    assert str(corsa) not in testo
    assert "1 attese" in testo and "1 presenti" in testo


def test_una_vista_su_un_altra_unita_non_fa_fallire_il_report(tmp_path, monkeypatch):
    """Su Windows relpath solleva fra unita' diverse: il report esce lo stesso."""
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})
    (corsa / "viste").mkdir()
    vista = corsa / "viste" / "fronte.png"
    vista.write_bytes(_png_minimo())

    def _solleva(*_):
        raise ValueError("percorsi su unita' diverse")

    monkeypatch.setattr(report.os.path, "relpath", _solleva)
    testo = report.write_run_report(corsa, viste=[vista]).read_text(encoding="utf-8")

    assert f'src="{vista.as_posix()}"' in testo
    assert "1 presenti" in testo


def test_ogni_cifra_delle_metriche_viene_riletta_dal_disco(tmp_path):
    """Il quinto principio: derivata da una lettura, non ricordata.

    Due corse con lo stesso nome di metrica e valori diversi devono dare due
    report diversi: se il numero fosse scritto nel codice, il secondo report
    conterrebbe ancora il primo valore.
    """
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 6329096}})
    primo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    (corsa / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"01_load": {"points_kept": 41}}), encoding="utf-8"
    )
    secondo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "6329096" in primo and "41" not in primo
    assert "41" in secondo and "6329096" not in secondo


def test_ogni_parametro_viene_riletto_da_config_yaml(tmp_path):
    corsa = _corsa(tmp_path, configurazione="tet:\n  min_ratio: 1.8\n")
    primo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    (corsa / report.CONFIG_FILENAME).write_text(
        "tet:\n  min_ratio: 2.7\n", encoding="utf-8"
    )
    secondo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "tet.min_ratio" in primo
    assert "1.8" in primo and "2.7" not in primo
    assert "2.7" in secondo and "1.8" not in secondo


def test_gli_istogrammi_nascono_dalle_liste_trovate_nelle_metriche(tmp_path):
    corsa = _corsa(
        tmp_path,
        metriche={"06_repair": {"hole_areas": [42120.4, 33986.0, 31702.6, 12231.8]}},
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "06_repair.hole_areas" in testo
    # non basta un <svg>: histogram_svg restituisce un riquadro con la sola
    # scritta "vuoto" quando non ha valori, e quel riquadro non ha barre
    assert "<rect" in testo


def test_la_firma_del_report_di_corsa_non_ha_predefiniti():
    """Regola del progetto: i predefiniti stanno in config.py, non nelle firme."""
    parametri = inspect.signature(report.write_run_report).parameters

    assert [nome for nome in parametri] == ["out_dir", "viste"]
    assert all(
        parametro.default is inspect.Parameter.empty for parametro in parametri.values()
    )


# --- coerenza fra i parametri mostrati e le metriche mostrate --------------
#
# metrics.json e' cumulativo: pipeline.run fonde le metriche di una corsa
# parziale con quelle precedenti. Una tabella di parametri affiancata a righe
# prodotte da parametri diversi afferma un legame che non esiste, e su carta
# nessuno puo' accorgersene. steps.json porta l'impronta con cui ogni step e'
# stato prodotto: e' quella la smentita.


def _corsa_con_impronte(tmp_path, impronte_scritte, chiavi=steps.STEP_KEYS, esiti=None):
    """Corsa con config.yaml valido e uno steps.json costruito a mano.

    `impronte_scritte` mappa la chiave di uno step all'impronta da salvare:
    scriverne una diversa da quella ricalcolata simula uno step prodotto con
    parametri che nel config.yaml corrente non ci sono piu'.

    `chiavi` sono le sole voci scritte, in steps.json e in metrics.json.
    Scrivendole sempre tutte e undici, il caso normale dell'interfaccia — uno
    step eseguito e gli altri mai — non si presenta in nessun test.
    `esiti` mappa la chiave all'esito salvato; per il resto vale "riuscito".
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    save_config(cfg, corsa / report.CONFIG_FILENAME)
    (corsa / pipeline.METRICS_FILENAME).write_text(
        json.dumps({chiave: {"misura": 1} for chiave in chiavi}), encoding="utf-8"
    )
    attese = dict(zip(steps.STEP_KEYS, steps.step_fingerprints(cfg).values()))
    (corsa / steps.STATE_FILENAME).write_text(
        json.dumps(
            {
                chiave: {
                    "impronta": impronte_scritte(chiave, attese[chiave]),
                    "esito": (esiti or {}).get(chiave, "riuscito"),
                    "artefatto": None,
                    "secondi": 1.0,
                }
                for chiave in chiavi
            }
        ),
        encoding="utf-8",
    )
    return corsa


def test_il_report_dichiara_quanti_step_sono_coerenti_con_i_parametri(tmp_path):
    corsa = _corsa_con_impronte(tmp_path, lambda _chiave, attesa: attesa)

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    totale = len(steps.STEP_KEYS)
    assert f"{totale} step su {totale} {report.COERENTI}." in testo
    assert report.NON_VERIFICABILE not in testo


def test_il_report_nomina_lo_step_prodotto_con_altri_parametri(tmp_path):
    """Il conteggio da solo passerebbe anche marcando lo step sbagliato."""
    corsa = _corsa_con_impronte(
        tmp_path,
        lambda chiave, attesa: "impronta-di-un-altra-corsa"
        if chiave == "03_downsample"
        else attesa,
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    totale = len(steps.STEP_KEYS)
    assert f"{totale - 1} step su {totale} {report.COERENTI}, 1 no:" in testo
    assert "03_downsample (non valido)" in testo
    assert "01_load (non valido)" not in testo
    # lo stato viaggia con la riga di metrica, non solo nel conteggio in cima
    assert "<h3>03_downsample [non valido]</h3>" in testo
    assert "<h3>01_load [valido]</h3>" in testo


def test_una_configurazione_non_valida_rende_la_coerenza_non_verificabile(tmp_path):
    """yaml.safe_load mostra comunque i parametri grezzi: il report non sparisce."""
    corsa = _corsa(
        tmp_path,
        metriche={"01_load": {"points_kept": 10}},
        configurazione="tet:\n  min_ratio: 1.8\n",
    )
    (corsa / steps.STATE_FILENAME).write_text("{}", encoding="utf-8")

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{report.NON_VERIFICABILE}: {report.CONFIG_FILENAME}" in testo
    assert "tet.min_ratio" in testo and "1.8" in testo
    assert report.COERENTI not in testo


def test_senza_steps_json_la_coerenza_non_e_verificabile(tmp_path):
    """Ogni corsa anteriore a steps.json cade qui: non e' un caso teorico."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})
    save_config(cfg, corsa / report.CONFIG_FILENAME)

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{report.NON_VERIFICABILE}: {steps.STATE_FILENAME}" in testo
    assert report.COERENTI not in testo


def test_il_report_di_corsa_non_usa_lettere_accentate(tmp_path):
    """Vincolo del core, qui verificato sul documento prodotto."""
    corsa = _corsa(
        tmp_path,
        metriche={"01_load": {"points_kept": 10}},
        configurazione="tet:\n  min_ratio: 1.8\n",
    )

    testo = report.write_run_report(corsa, viste=[Path("mancante.png")]).read_text(
        encoding="utf-8"
    )

    assert testo.isascii()


# --- tre categorie, non due -----------------------------------------------
#
# run_state restituisce quattro stati, non due: "mai eseguito", "fallito",
# "non valido", "valido". Contarli come "valido" contro "tutto il resto" fa
# dire al documento che le metriche di uno step mai eseguito vengono da altri
# parametri, mentre quelle metriche non esistono affatto.


def test_uno_step_mai_eseguito_non_e_anche_incoerente(tmp_path):
    """Il caso normale dell'interfaccia: uno step eseguito, gli altri mai.

    Un documento che chiama lo stesso step incoerente in un paragrafo e mai
    eseguito due paragrafi dopo si contraddice, e stampato non si corregge.
    """
    corsa = _corsa_con_impronte(
        tmp_path, lambda _chiave, attesa: attesa, chiavi=("01_load",)
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    coerenza = _paragrafo(testo, report.COERENTI)
    mai = len(steps.STEP_KEYS) - 1
    assert f"1 step su 1 {report.COERENTI}." in coerenza
    assert f"{mai} step {report.NON_ESEGUITI}" in coerenza
    # nessuno step mai eseguito puo' comparire fra quelli che non tornano
    assert all(chiave not in coerenza for chiave in steps.STEP_KEYS[1:])
    # e la dichiarazione che gia' esiste piu' sotto resta l'unica a nominarli
    assert "02_segment" in _paragrafo(testo, report.SENZA_METRICHE)


def test_uno_step_fallito_non_e_uno_step_prodotto_con_altri_parametri(tmp_path):
    """«fallito» e «non valido» sono due stati diversi di run_state."""
    corsa = _corsa_con_impronte(
        tmp_path,
        lambda _chiave, attesa: attesa,
        esiti={"05_reconstruct": "fallito"},
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    coerenza = _paragrafo(testo, report.COERENTI)
    totale = len(steps.STEP_KEYS)
    assert f"{totale - 1} step su {totale} {report.COERENTI}, 1 no:" in coerenza
    assert "05_reconstruct (fallito)" in coerenza
    assert "05_reconstruct (non valido)" not in coerenza
    assert "<h3>05_reconstruct [fallito]</h3>" in testo


def test_una_lista_vuota_non_diventa_una_cella_bianca(tmp_path):
    """Zero fori oltre soglia e' il risultato migliore possibile, non un buco.

    Stampata, una cella vuota accanto a holes_over_threshold non si distingue
    da un dato mancante. Le due liste sempre vuote compaiono in ogni
    metrics.json dell'albero: e' il caso normale, non un caso di laboratorio.
    """
    corsa = _corsa(
        tmp_path, metriche={"06_repair": {"holes_over_threshold": [], "buchi": 0}}
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "<td></td>" not in testo
    assert f"<th>holes_over_threshold</th><td>{report.LISTA_VUOTA}</td>" in testo
    # una lista vuota e uno zero numerico non sono la stessa cosa
    assert "<th>buchi</th><td>0</td>" in testo


def test_un_file_illeggibile_non_viene_dichiarato_assente(tmp_path):
    """steps.read_state documenta il processo ucciso a meta' scrittura.

    Un file troncato dichiarato assente manda il lettore a cercare una corsa
    mai fatta invece che un file da riscrivere.
    """
    corsa = _corsa(tmp_path, configurazione="a: [1, 2\n")
    (corsa / pipeline.METRICS_FILENAME).write_text("{non json", encoding="utf-8")

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{report.CONFIG_FILENAME} assente" not in testo
    assert f"{pipeline.METRICS_FILENAME} assente" not in testo
    assert f"{report.CONFIG_FILENAME} {report.ILLEGGIBILE}" in testo
    assert f"{pipeline.METRICS_FILENAME} {report.ILLEGGIBILE}" in testo


def test_un_file_di_forma_inattesa_non_viene_dichiarato_assente(tmp_path):
    """config.yaml che contiene «ciao», metrics.json che contiene una lista."""
    corsa = _corsa(tmp_path, configurazione="ciao\n")
    (corsa / pipeline.METRICS_FILENAME).write_text("[1,2,3]", encoding="utf-8")

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert f"{report.CONFIG_FILENAME} assente" not in testo
    assert f"{pipeline.METRICS_FILENAME} assente" not in testo
    assert f"{report.CONFIG_FILENAME} {report.FORMA_INATTESA}" in testo
    assert f"{pipeline.METRICS_FILENAME} {report.FORMA_INATTESA}" in testo


def test_una_lista_troppo_corta_per_un_istogramma_viene_dichiarata(tmp_path):
    """runs/sweep/lab_crop/51de6c2c9145 ha hole_areas con tre valori soli.

    E' una distribuzione vera, scartata perche' lunga come una terna di
    coordinate: la soglia resta dov'e', ma l'esclusione va detta.
    """
    corsa = _corsa(
        tmp_path, metriche={"06_repair": {"hole_areas": [42120.4, 33986.0, 31702.6]}}
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "<rect" not in testo
    assert report.ESCLUSE_CORTE in testo
    assert "06_repair.hole_areas" in _paragrafo(testo, report.ESCLUSE_CORTE)


def test_una_vista_che_non_e_un_png_leggibile_non_diventa_immagine_rotta(tmp_path):
    """Otto byte di firma passano exists() e in appendice sono un riquadro rotto."""
    corsa = _corsa(tmp_path, metriche={"01_load": {"points_kept": 10}})
    (corsa / "viste").mkdir()
    vista = corsa / "viste" / "fronte.png"
    vista.write_bytes(b"\x89PNG\r\n\x1a\n")

    testo = report.write_run_report(corsa, viste=[vista]).read_text(encoding="utf-8")

    assert "<img" not in testo
    assert f"vista fronte.png: {report.PNG_NON_LEGGIBILE}" in testo


def test_i_valori_logici_e_quelli_mancanti_sono_in_italiano(tmp_path):
    """None e True in un documento italiano sono lingua sbagliata, non dato."""
    corsa = _corsa(tmp_path, configurazione="tet:\n  max_volume: null\n  nobisect: true\n")

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "None" not in testo and "True" not in testo
    assert f"<th>tet.max_volume</th><td>{report.NON_IMPOSTATO}</td>" in testo
    assert "<th>tet.nobisect</th><td>si</td>" in testo


def test_un_numero_grande_non_passa_alla_notazione_esponenziale(tmp_path):
    """In una tabella stampata 1.68846e+08 si legge peggio dell'intero."""
    corsa = _corsa(
        tmp_path, metriche={"10_volume_quality": {"volume_mm3": 168845511.10290658}}
    )

    testo = report.write_run_report(corsa, viste=[]).read_text(encoding="utf-8")

    assert "e+08" not in testo
    assert "168846000" in testo
