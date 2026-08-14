"""Il report si genera dal registro e non da altro."""

import inspect
import json
from pathlib import Path

from meshrec.core import pipeline, report, steps, sweep


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
    (corsa / "viste" / "fronte.png").write_bytes(b"\x89PNG\r\n\x1a\n")

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
    vista.write_bytes(b"\x89PNG\r\n\x1a\n")

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
