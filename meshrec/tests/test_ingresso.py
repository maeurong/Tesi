"""Ingresso: avviare il programma senza una configurazione scritta a mano.

Il programma nasceva legato a uno yaml (`create_app` esigeva un percorso, e la
riga di comando un argomento obbligatorio). All'universita' arriva una nuvola di
punti, non uno yaml: questi test fissano la strada che parte dal file di punti e
finisce su una corsa in `runs/`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meshrec.app import server
from meshrec.app.server import create_app
from meshrec.core.config import InputConfig, PipelineConfig, load_config, save_config
from materiale import ANALISI


@pytest.fixture()
def nuvola(tmp_path: Path) -> Path:
    """Una nuvola vera ma minuscola: il server la legge solo per esistere."""
    from meshrec.core import io, synth

    percorso = tmp_path / "scansione.ply"
    io.write_cloud(percorso, synth.sample_box_surface((10.0, 10.0, 10.0), 5.0))
    return percorso


@pytest.fixture()
def slegato(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(server, "CACHE_DIR", tmp_path / "cache")
    return TestClient(
        create_app(
            None,
            radice_corse=tmp_path / "runs",
            radice_esperimenti=tmp_path / "experiments",
        ),
        raise_server_exceptions=False,
    )


def test_senza_configurazione_lo_stato_dice_che_non_c_e_una_corsa(slegato):
    """Prima schermata, non pagina d'errore: `legata` e' falso e basta."""
    corpo = slegato.get("/api/run").json()

    assert corpo["legata"] is False
    assert corpo.get("steps") is None


def test_l_elenco_delle_corse_di_una_radice_assente_e_vuoto(slegato):
    """Ingresso degenere: nessuna cartella runs/ sul disco."""
    corpo = slegato.get("/api/corse").json()

    assert corpo["corse"] == []
    assert corpo["corrente"] is None


def test_creare_una_corsa_scrive_il_config_e_lega_l_applicazione(slegato, nuvola, tmp_path):
    risposta = slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(nuvola)})

    assert risposta.status_code == 200
    scritto = load_config(tmp_path / "runs" / "provino" / "config.yaml")
    assert scritto.input.path == nuvola
    assert scritto.run.out_dir == tmp_path / "runs" / "provino"
    # Il materiale non e' stato chiesto e non e' stato inventato.
    assert scritto.analysis is None
    stato = slegato.get("/api/run").json()
    assert stato["legata"] is True
    assert len(stato["steps"]) == 13


def test_una_corsa_creata_compare_nell_elenco_con_la_sua_nuvola(slegato, nuvola):
    slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(nuvola)})

    corpo = slegato.get("/api/corse").json()

    assert [voce["nome"] for voce in corpo["corse"]] == ["provino"]
    assert corpo["corse"][0]["nuvola"] == str(nuvola)
    assert corpo["corse"][0]["errore"] is None
    assert corpo["corrente"] == "provino"


def test_un_nome_gia_occupato_e_rifiutato_invece_di_sovrascrivere(slegato, nuvola):
    """`runs/lab_crop` e `runs/muro` sono corse di riferimento di sola lettura:
    una sovrascrittura silenziosa qui cancellerebbe un risultato di tesi."""
    slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(nuvola)})

    risposta = slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(nuvola)})

    assert risposta.status_code == 400
    assert "provino" in risposta.json()["messaggio"]


def test_una_nuvola_inesistente_e_rifiutata_prima_di_scrivere(slegato, tmp_path):
    risposta = slegato.post(
        "/api/corse", json={"nome": "provino", "nuvola": str(tmp_path / "assente.ply")}
    )

    assert risposta.status_code == 400
    assert not (tmp_path / "runs" / "provino").exists()


def test_una_cartella_al_posto_della_nuvola_e_rifiutata(slegato, tmp_path):
    risposta = slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(tmp_path)})

    assert risposta.status_code == 400
    assert not (tmp_path / "runs" / "provino").exists()


def test_un_formato_non_letto_dal_programma_e_rifiutato(slegato, tmp_path):
    estranea = tmp_path / "scansione.e57"
    estranea.write_bytes(b"non importa")

    risposta = slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(estranea)})

    assert risposta.status_code == 400
    assert ".pcd" in risposta.json()["messaggio"]


@pytest.mark.parametrize("nome", ["..", "fuori/provino", "", "spazio vietato"])
def test_un_nome_di_corsa_fuori_tabella_e_rifiutato(slegato, nuvola, nome):
    """Il nome diventa una cartella: senza vincolo scrive fuori da `runs/`."""
    risposta = slegato.post("/api/corse", json={"nome": nome, "nuvola": str(nuvola)})

    assert risposta.status_code in (400, 422)


def test_aprire_una_corsa_esistente_la_lega(slegato, nuvola, tmp_path):
    slegato.post("/api/corse", json={"nome": "prima", "nuvola": str(nuvola)})
    slegato.post("/api/corse", json={"nome": "seconda", "nuvola": str(nuvola)})

    risposta = slegato.put("/api/corrente", json={"nome": "prima"})

    assert risposta.status_code == 200
    assert slegato.get("/api/corse").json()["corrente"] == "prima"
    assert slegato.get("/api/config").json()["run"]["out_dir"] == str(
        tmp_path / "runs" / "prima"
    )


def test_aprire_una_corsa_che_non_c_e_e_un_rifiuto_leggibile(slegato):
    risposta = slegato.put("/api/corrente", json={"nome": "mai-vista"})

    assert risposta.status_code == 400
    assert "mai-vista" in risposta.json()["messaggio"]


def test_una_corsa_col_config_illeggibile_non_nasconde_le_altre(slegato, nuvola, tmp_path):
    """Ingresso degenere: uno yaml troncato da un processo ucciso."""
    slegato.post("/api/corse", json={"nome": "sana", "nuvola": str(nuvola)})
    rotta = tmp_path / "runs" / "rotta"
    rotta.mkdir(parents=True)
    (rotta / "config.yaml").write_text("input: {path:", encoding="utf-8")

    corse = {voce["nome"]: voce for voce in slegato.get("/api/corse").json()["corse"]}

    assert corse["sana"]["errore"] is None
    assert corse["rotta"]["errore"]
    assert corse["rotta"]["nuvola"] is None


def test_una_cartella_senza_config_non_e_una_corsa(slegato, tmp_path):
    (tmp_path / "runs" / "artefatti-orfani").mkdir(parents=True)

    assert slegato.get("/api/corse").json()["corse"] == []


def test_con_una_configurazione_all_avvio_lo_stato_e_gia_legato(tmp_path, monkeypatch):
    """Controprova: la forma vecchia, `serve config.yaml`, continua a valere."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    save_config(cfg, tmp_path / "config.yaml")
    monkeypatch.setattr(server, "CACHE_DIR", tmp_path / "cache")
    cliente = TestClient(create_app(tmp_path / "config.yaml"), raise_server_exceptions=False)

    assert cliente.get("/api/run").json()["legata"] is True


def test_la_galleria_non_dipende_da_dove_sta_il_config(slegato, nuvola, tmp_path):
    """La galleria cercava `experiments/` accanto al file di configurazione.

    Ogni corsa creata dall'ingresso vive in `runs/<nome>/config.yaml`, quindi
    quella regola l'avrebbe fatta cercare in `runs/<nome>/experiments/` e
    l'avrebbe lasciata vuota per sempre, senza dire perche'. La radice degli
    esperimenti e' del progetto, non della corsa.
    """
    registro = tmp_path / "experiments" / "prova" / "registro.jsonl"
    registro.parent.mkdir(parents=True)
    registro.write_text('{"fingerprint": "aa", "on_front": true}\n', encoding="utf-8")
    slegato.post("/api/corse", json={"nome": "provino", "nuvola": str(nuvola)})

    assert slegato.get("/api/experiments").json()["esperimenti"] == ["prova"]
    assert slegato.get("/api/experiments/prova").json()["fronte"] == 1


def test_lo_schema_descrive_il_materiale_anche_se_il_blocco_e_opzionale(slegato):
    """`analysis` opzionale rende la sua annotazione un'unione con None: letta
    grezza faceva cadere /api/schema, cioe' il pannello degli step 11 e 13."""
    corpo = slegato.get("/api/schema").json()

    assert "material" in corpo["11"]["campi"]["analysis"]
    assert "material" in corpo["13"]["campi"]["analysis"]


def test_la_riga_di_comando_accetta_serve_senza_configurazione():
    from meshrec.cli import _build_parser

    assert _build_parser().parse_args(["serve"]).config is None
    assert _build_parser().parse_args(["serve", "config.yaml"]).config == Path("config.yaml")
