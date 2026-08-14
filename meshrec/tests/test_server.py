"""Endpoint del server. Il contratto vale sulla tratta, non sulla funzione."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meshrec.app import server
from meshrec.app.server import create_app
from meshrec.core.config import InputConfig, PipelineConfig, save_config


@pytest.fixture()
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    save_config(cfg, tmp_path / "config.yaml")
    # I-5 della revisione: CACHE_DIR e' una costante di modulo che punta a
    # meshrec/.cache/viewport/ per davvero. Senza questo dirottamento, ogni
    # test che chiama /api/cloud lascia una voce che nessuna pulizia
    # raggiungera' mai (la sorgente e' sotto tmp_path e sparisce col test).
    monkeypatch.setattr(server, "CACHE_DIR", tmp_path / "cache")
    # raise_server_exceptions=False: il gestore generico in server.py risponde
    # con 400 e corpo strutturato, ma starlette rilancia comunque l'eccezione
    # al chiamante quando questo flag e' vero (e' il predefinito), per dare a
    # chi testa la scelta di vederla. Qui si vuole il contratto HTTP che vede
    # il browser, non l'eccezione interna.
    return TestClient(create_app(tmp_path / "config.yaml"), raise_server_exceptions=False)


def test_la_radice_serve_l_interfaccia(cliente):
    risposta = cliente.get("/")
    assert risposta.status_code == 200
    assert "text/html" in risposta.headers["content-type"]


def test_lo_stato_della_corsa_elenca_gli_undici_step(cliente):
    corpo = cliente.get("/api/run").json()
    assert len(corpo["steps"]) == 11
    assert corpo["steps"][0]["chiave"] == "01_load"
    assert {voce["stato"] for voce in corpo["steps"]} == {"mai eseguito"}


def test_la_configurazione_torna_intera(cliente):
    corpo = cliente.get("/api/config").json()
    assert set(corpo) >= {"input", "segment", "surface", "tet", "analysis"}


def test_scrivere_la_configurazione_invalida_gli_step_a_valle(cliente, tmp_path):
    prima = cliente.get("/api/config").json()
    prima["surface"]["poisson_depth"] = 7
    risposta = cliente.put("/api/config", json=prima)
    assert risposta.status_code == 200
    assert risposta.json()["surface"]["poisson_depth"] == 7
    assert cliente.get("/api/config").json()["surface"]["poisson_depth"] == 7


def test_una_configurazione_fuori_dominio_non_solleva_ma_spiega(cliente):
    guasta = cliente.get("/api/config").json()
    guasta["surface"]["poisson_depth"] = 99   # il modello ammette 4..14
    risposta = cliente.put("/api/config", json=guasta)
    assert risposta.status_code == 422
    assert "poisson_depth" in risposta.text


# /api/events e' un generatore SSE senza fine: una GET secca lo terrebbe
# aperto e bloccherebbe la suite. Ha il proprio test dedicato, con un tetto
# agli eventi emessi. Tenere questo insieme corto: cio' che vi entra esce
# dal contratto.
STREAMING = {"/api/events"}


def test_avviare_uno_step_risponde_senza_bloccare(cliente):
    risposta = cliente.post("/api/step/1")
    assert risposta.status_code == 200
    assert risposta.json()["avviato"] == 1


def test_annullare_quando_non_gira_nulla_non_solleva(cliente):
    risposta = cliente.post("/api/cancel")
    assert risposta.status_code == 200
    assert risposta.json()["annullato"] is False


def test_lo_stream_degli_eventi_manda_lo_stato_e_si_chiude(cliente):
    with cliente.stream("GET", "/api/events?max_eventi=1") as risposta:
        assert risposta.status_code == 200
        assert "text/event-stream" in risposta.headers["content-type"]
        testo = "".join(risposta.iter_text())
    assert "event: stato" in testo
    assert '"in_corso"' in testo


def test_la_nuvola_dichiara_sempre_entrambi_i_conteggi(cliente, tmp_path):
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((50_000, 3)) * 100.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)

    risposta = cliente.get("/api/cloud/1?max_points=1000")
    assert risposta.status_code == 200
    assert int(risposta.headers["X-Points-Total"]) == 50_000
    disegnati = int(risposta.headers["X-Points-Drawn"])
    assert disegnati <= 1000
    assert len(risposta.content) == disegnati * 3 * 4


def test_la_seconda_richiesta_della_stessa_nuvola_non_ricalcola(cliente, tmp_path, monkeypatch):
    """I-1 della revisione: il guadagno del Task 6-bis vive nell'endpoint, non
    nella funzione. Un test che chiama solo decimate_file lascerebbe scoperte
    proprio le tre righe che lo producono in server.py."""
    import numpy as np
    from meshrec.core import io, pipeline, viewport

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((50_000, 3)) * 100.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)

    prima = cliente.get("/api/cloud/2?max_points=1000")
    assert prima.status_code == 200

    def _non_chiamarmi(*_args, **_kwargs):
        raise AssertionError("decimate non deve essere richiamata a cache calda")

    monkeypatch.setattr(viewport, "decimate", _non_chiamarmi)
    poi = cliente.get("/api/cloud/2?max_points=1000")
    # status_code == 200 e non solo "non solleva": con raise_server_exceptions
    # =False un errore diventa comunque un 400, che passerebbe inosservato
    # senza questa asserzione esplicita.
    assert poi.status_code == 200
    assert poi.content == prima.content
    assert poi.headers["X-Points-Drawn"] == prima.headers["X-Points-Drawn"]
    assert poi.headers["X-Points-Total"] == prima.headers["X-Points-Total"]


def test_max_points_zero_o_negativo_e_rifiutato_con_messaggio_chiaro(cliente, tmp_path):
    """M-11 della revisione: prima della guardia, max_points=0 dava
    ZeroDivisionError e un negativo TypeError su un numero complesso — la
    tratta reggeva (400 in entrambi i casi) ma il messaggio era opaco."""
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((100, 3)) * 10.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)

    for valore in (0, -5):
        risposta = cliente.get(f"/api/cloud/1?max_points={valore}")
        assert risposta.status_code == 400
        corpo = risposta.json()
        assert corpo["errore"] not in ("ZeroDivisionError", "TypeError")
        assert str(valore) in corpo["messaggio"]
        assert "positivo" in corpo["messaggio"]


def test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva(cliente):
    risposta = cliente.get("/api/cloud/9")
    assert risposta.status_code == 400
    assert "errore" in risposta.json()


def test_chiedere_la_nuvola_di_uno_step_fuori_intervallo_spiega_quali_esistono(cliente):
    """Prima della guardia, uno step fuori intervallo faceva sollevare
    pipeline.ARTIFACTS[numero] con un KeyError generico ('99', senza
    contesto), che il gestore trasformava in un messaggio inutile per
    l'utente. Deve dire quali step esistono."""
    risposta = cliente.get("/api/cloud/99")
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] != "KeyError"
    assert "99" in corpo["messaggio"]
    # "8" e' uno step valido e non e' una sottostringa di "99": a differenza
    # di "9", puo' davvero far fallire il test se l'elenco sparisse dal
    # messaggio (M-8 della revisione).
    assert "8" in corpo["messaggio"]


def test_la_mesh_torna_in_binario_con_i_conteggi(cliente, tmp_path):
    import open3d as o3d

    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    cubo = o3d.geometry.TriangleMesh.create_box(1.0, 1.0, 1.0)
    o3d.io.write_triangle_mesh(str(corsa / pipeline.ARTIFACTS[6]), cubo)

    risposta = cliente.get("/api/mesh/6")
    assert risposta.status_code == 200
    vertici = int(risposta.headers["X-Vertices"])
    triangoli = int(risposta.headers["X-Triangles"])
    assert vertici == 8 and triangoli == 12
    assert len(risposta.content) == vertici * 3 * 4 + triangoli * 3 * 4


def test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva(cliente):
    risposta = cliente.get("/api/mesh/6")
    assert risposta.status_code == 400
    assert "errore" in risposta.json()


def test_chiedere_la_mesh_di_uno_step_fuori_intervallo_spiega_quali_esistono(cliente):
    """Stessa guardia di /api/cloud: senza, ARTIFACTS[99] darebbe un KeyError
    generico ('99', senza contesto) e il gestore lo mostrerebbe cosi'."""
    risposta = cliente.get("/api/mesh/99")
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] != "KeyError"
    assert "99" in corpo["messaggio"]
    # "8" e' uno step valido e non e' una sottostringa di "99".
    assert "8" in corpo["messaggio"]


def test_il_contorno_del_volume_porta_solo_i_vertici_che_disegna(cliente, tmp_path):
    """X-Vertices deve contare i vertici che il browser disegna davvero.

    griglia.points contiene anche i nodi interni della tetraedralizzazione,
    che nessuna faccia di contorno tocca: qui il quinto nodo non appartiene ad
    alcun tetraedro, e se finisse nella risposta il conteggio mostrato a video
    non sarebbe sostenuto da nessuna lettura.
    """
    import meshio
    import numpy as np

    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [9.0, 9.0, 9.0]]
    )
    meshio.write_points_cells(
        corsa / pipeline.ARTIFACTS[9], punti, [("tetra", np.array([[0, 1, 2, 3]]))]
    )

    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 200
    vertici = int(risposta.headers["X-Vertices"])
    triangoli = int(risposta.headers["X-Triangles"])
    # Le quattro facce del solo tetraedro, sui suoi soli quattro nodi.
    assert (vertici, triangoli) == (4, 4)
    assert len(risposta.content) == vertici * 3 * 4 + triangoli * 3 * 4
    indici = np.frombuffer(risposta.content, dtype="<u4", offset=vertici * 3 * 4)
    # Rimappati sui vertici mandati: un indice fuori intervallo non disegna.
    assert indici.max() < vertici


def test_il_clic_sullo_step_sceglie_fra_nuvola_e_mesh_senza_perdere_il_pannello():
    """Il gestore del clic apre anche il pannello dei parametri (Task 8): una
    riscrittura che ne sostituisce l'intero corpo lo perderebbe in silenzio."""
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    gestore = testo.split('getElementById("elenco-step").addEventListener', 1)[1]
    assert "mostraStep(numero)" in gestore
    assert "apriDettaglio(numero)" in gestore


def test_l_intervallo_del_cursore_di_taglio_esce_da_una_lettura_e_non_da_numeri_scritti():
    """Il cursore del taglio mostra una quota in millimetri: se i suoi estremi
    fossero scritti nel codice sarebbe una cifra che nessuna lettura sostiene, e
    sul muro di riferimento (2470,99 x 231,00 x 1697,00 mm) sarebbe sbagliata
    per due assi su tre. min, max e step devono venire dall'ingombro della
    geometria disegnata, che il viewport misura.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    corpo = testo.split("function riallineaTaglio", 1)[1].split("\n}\n", 1)[0]
    assert "vista.ingombro()" in corpo
    for riga in corpo.splitlines():
        assegnamento = re.search(r"quotaTaglio\.(min|max|step|value)\s*=\s*(.+)", riga)
        if assegnamento:
            assert not re.match(r"-?\d", assegnamento.group(2)), riga

    # Nemmeno nel markup: scritti li' non li vedrebbe nessun test sul codice.
    pagina = (UI_DIR / "index.html").read_text(encoding="utf-8")
    cursore = pagina.split('id="taglio-quota"', 1)[0].rsplit("<input", 1)[1]
    for attributo in ("min", "max", "step", "value"):
        assert f"{attributo}=" not in cursore, cursore


def test_i_moduli_dell_interfaccia_sono_sintatticamente_validi():
    """node --check prende gli errori di sintassi che altrimenti si scoprono
    solo aprendo la pagina, dove nessuna suite guarda."""
    from meshrec.app.server import UI_DIR

    node = shutil.which("node")
    if node is None:
        pytest.skip("node non installato: la sintassi resta verificata a mano")
    for percorso in sorted(UI_DIR.rglob("*.js")):
        if "vendor" in percorso.parts:
            continue
        esito = subprocess.run(
            [node, "--check", str(percorso)], capture_output=True, text=True,
        )
        assert esito.returncode == 0, f"{percorso.name}: {esito.stderr}"


def test_three_js_e_servito_dal_server_e_non_dalla_rete(cliente):
    for nome in ("three.module.js", "three.core.js"):
        risposta = cliente.get(f"/ui/vendor/{nome}")
        assert risposta.status_code == 200
        assert len(risposta.content) > 100_000


def test_nessun_riferimento_a_una_rete_esterna_nell_interfaccia():
    """Il server e' locale e l'applicazione deve partire senza rete."""
    from meshrec.app.server import UI_DIR

    for percorso in UI_DIR.rglob("*"):
        if percorso.suffix not in {".html", ".js", ".css"} or "vendor" in percorso.parts:
            continue
        testo = percorso.read_text(encoding="utf-8")
        for sospetto in ("https://", "http://", "//cdn.", "unpkg", "jsdelivr"):
            assert sospetto not in testo, f"{percorso.name} punta fuori dalla macchina"


def test_le_metriche_tornano_quelle_scritte_su_disco(cliente, tmp_path):
    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"01_load": {"points_kept": 6_329_096}}), encoding="utf-8"
    )
    # Lo stato per primo: con raise_server_exceptions=False un errore diventa
    # un 400 con corpo {"errore", "messaggio"}, e leggere il corpo darebbe un
    # KeyError che non nomina la causa vera (M-6 della revisione).
    risposta = cliente.get("/api/metrics")
    assert risposta.status_code == 200
    assert risposta.json()["01_load"]["points_kept"] == 6_329_096


def test_le_metriche_di_una_corsa_mai_eseguita_sono_vuote_e_non_sollevano(cliente):
    risposta = cliente.get("/api/metrics")
    assert risposta.status_code == 200
    assert risposta.json() == {}


def test_lo_schema_dice_quali_parametri_appartengono_a_ogni_step(cliente):
    risposta = cliente.get("/api/schema")
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["5"]["blocchi"] == ["surface"]
    assert "poisson_depth" in corpo["5"]["campi"]["surface"]
    assert corpo["5"]["campi"]["surface"]["poisson_depth"]["description"]
    # Un campo obbligatorio non ha un predefinito: deve uscire null e non la
    # stringa "PydanticUndefined", che somiglia a un valore (M-5).
    assert corpo["1"]["campi"]["input"]["path"]["default"] is None


def test_il_tempo_dello_step_viene_dal_server_e_non_dal_browser(cliente):
    risposta = cliente.get("/api/events?max_eventi=1")
    assert risposta.status_code == 200
    stato = json.loads(risposta.text.split("data: ", 1)[1].split("\n", 1)[0])
    # L'ordine conta: la chiave prima, cosi' che la sua assenza fallisca
    # dicendo cosa manca; poi il valore, che smentisce un tempo inventato
    # mentre non gira nulla (M-7).
    assert "da_secondi" in stato
    assert stato["da_secondi"] is None


def test_il_cronometro_non_puo_tornare_nel_browser():
    """Il tempo trascorso deve venire dal server, dove lo step parte davvero.

    Senza questo controllo una riscrittura futura potrebbe rimettere il
    cronometro nel browser in silenzio, con la suite verde: il tempo
    ripartirebbe da zero a ogni ricarica mentre il calcolo prosegue (M-2).
    """
    from meshrec.app.server import UI_DIR

    for percorso in UI_DIR.rglob("*.js"):
        if "vendor" in percorso.parts:
            continue
        testo = percorso.read_text(encoding="utf-8")
        assert "Date.now" not in testo, f"{percorso.name} misura il tempo nel browser"
        assert "avvioStep" not in testo, f"{percorso.name} ha di nuovo un cronometro locale"


def test_nessun_endpoint_solleva_verso_il_browser(cliente):
    """Il contratto vale sull'elenco intero, derivato dall'applicazione stessa:
    un endpoint aggiunto domani vi entra da solo e non puo' essere dimenticato.
    """
    percorsi = [
        rotta.path
        for rotta in cliente.app.routes
        if getattr(rotta, "methods", None) and "GET" in rotta.methods
    ]
    assert len(percorsi) >= 3
    for percorso in percorsi:
        if "{" in percorso or percorso in STREAMING:
            continue
        risposta = cliente.get(percorso)
        assert risposta.status_code < 500, f"{percorso} ha sollevato verso il browser"
