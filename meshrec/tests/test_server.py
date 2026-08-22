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
from materiale import ANALISI


@pytest.fixture()
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"), analysis=ANALISI)
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


def test_lo_stato_della_corsa_elenca_i_tredici_step(cliente):
    """Variante scaduta dalla Fase 5 (Task 6): lo step 13 (solutore) allunga
    STEP_KEYS a tredici voci, e /api/run le elenca tutte."""
    corpo = cliente.get("/api/run").json()
    assert len(corpo["steps"]) == 13
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


def _nuvola_un_cluster_e_rumore():
    """3.000 punti fitti nell'origine, 1.000 radi a 500 mm.

    Il secondo blocco e' disperso su 10 mm, quindi con eps = 4 x spaziatura
    DBSCAN non ci trova nessun nucleo: e' rumore, non un secondo cluster.
    Misurato: un cluster da 2.992 punti e 1.008 punti di rumore. Un clic che
    ricada li' dentro DEVE ottenere 400.

    Esiste come funzione, e non copiata in ogni test, perche' tre docstring
    affermano "stessa nuvola" l'una dell'altra: cosi' l'affermazione e' vera
    per costruzione invece che per manutenzione.
    """
    import numpy as np

    primo = np.random.default_rng(0).random((3_000, 3)) * 10.0
    secondo = np.random.default_rng(1).random((1_000, 3)) * 10.0 + 500.0
    return np.vstack([primo, secondo])


def _nuvola_due_cluster():
    """Come sopra, ma il secondo blocco e' disperso su 7 mm invece che 10.

    Tre millimetri di differenza cambiano la natura del dato, non la sua
    taglia: a 7 mm il secondo blocco supera min_points e diventa un cluster
    vero, quindi esiste un cluster_index 1 su cui puntare. Serve ai test che
    devono distinguere una scrittura corretta da un "scrivi sempre 0", che
    sulla nuvola a 10 mm resterebbe invisibile per coincidenza.
    """
    import numpy as np

    primo = np.random.default_rng(0).random((3_000, 3)) * 10.0
    secondo = np.random.default_rng(1).random((1_000, 3)) * 7.0 + 500.0
    return np.vstack([primo, secondo])


def _prepara_click_semplice(cliente, corsa: Path, punti) -> None:
    """Scrive la stessa nuvola come ingresso grezzo (step 1, ARTIFACTS[1]) e
    come uscita segmentata (step 2, ARTIFACTS[2]): dopo l'allineamento
    (task-11b), /api/cluster legge sempre ARTIFACTS[1] e rifa'
    remove_outliers -> crop_box -> extract_planes -> cluster (vedi
    server.scegli_cluster). I test di questa sezione, tranne quello
    dell'allineamento stesso, esercitano solo la REGOLA DI VOTO sul gruppo
    disegnato: con plane_max_count=0 e un outlier_std_ratio enorme quella
    tratta diventa un non-operazione, e la nuvola che arriva davvero a
    segment.cluster torna a essere esattamente quella scritta qui, come lo
    era prima dell'allineamento (quando l'endpoint clusterizzava
    ARTIFACTS[2] senza altro).
    """
    from meshrec.core import io, pipeline

    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)
    attuale = cliente.get("/api/config").json()
    attuale["segment"]["plane_max_count"] = 0
    attuale["segment"]["outlier_std_ratio"] = 1_000_000.0
    risposta = cliente.put("/api/config", json=attuale)
    assert risposta.status_code == 200


def _clusterizza_come_l_endpoint(corsa: Path, cfg):
    """Rifa', fuori dall'endpoint, esattamente il calcolo che /api/cluster fa
    dopo l'allineamento: stessa base di spaziatura (ARTIFACTS[1], grezzo) e
    la stessa sequenza remove_outliers -> crop_box -> extract_planes ->
    cluster. Oracolo indipendente per i test che pretendono un
    cluster_index preciso, senza duplicare la logica dell'endpoint a mano.
    """
    from meshrec.core import io, pipeline, segment

    grezzi, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[1])
    spaziatura = io.mean_spacing(grezzi, cfg.input.spacing_sample, cfg.input.seed)
    puliti, _metriche_outlier = segment.remove_outliers(grezzi, cfg.segment)
    ritagliati, _metriche_crop = segment.crop_box(puliti, cfg.segment)
    _piani, residuo, _metriche_piani = segment.extract_planes(ritagliati, cfg.segment, spaziatura)
    insiemi, metriche = segment.cluster(residuo, cfg.segment, spaziatura)
    return insiemi, metriche, spaziatura


def test_il_clic_risolve_il_punto_disegnato_a_un_cluster(cliente, tmp_path):
    """Un clic dentro il blocco fitto risolve al cluster che lo contiene.

    Attenzione a come e' fatta la nuvola, perche' e' la stessa dei tre test
    piu' sotto: il secondo blocco NON e' un secondo cluster. Mille punti
    sparsi in dieci millimetri cubi sono troppo radi per l'eps che
    segment.cluster deriva dalla spaziatura, e DBSCAN li classifica in blocco
    come rumore (misurato: un solo cluster da 2992 punti, 1008 di rumore).
    Un clic che ci cadesse dentro dovrebbe dare 400, non un secondo cluster.

    Il punto disegnato 0 cade nel blocco fitto perche' viewport.decimate
    ordina i gruppi per indice pieno minimo, e l'indice pieno 0 e' del primo
    blocco: senza quel contratto l'indice 0 dipenderebbe dalla hash map di
    Open3D e quindi dalla piattaforma.
    """

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_un_cluster_e_rumore())

    cliente.get("/api/cloud/2?max_points=2000")     # popola la mappa
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    # Zero e non "0 oppure 1": su questa nuvola DBSCAN trova un cluster solo
    # (misurato sopra), quindi ammettere un 1 contraddirebbe la docstring.
    assert corpo["cluster_index"] == 0
    assert corpo["cluster_points"] > 0


def test_un_clic_senza_mappa_caricata_non_solleva(cliente):
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 400


def test_un_clic_senza_mappa_solleva_anche_con_la_nuvola_gia_su_disco(cliente, tmp_path):
    """Isola la sola variabile della mappa: qui, a differenza del test sopra,
    02_segmented.ply esiste davvero ed e' leggibile. Senza questo test la
    guardia sulla mappa mancante puo' sparire dall'endpoint senza che la
    suite se ne accorga: il 400 del test sopra arriva anche da un file
    assente (io.read_cloud solleva comunque), non prova la guardia. Qui
    l'unica cosa che manca e' che /api/cloud/2 non e' mai stato chiamato, e
    deve bastare a dare 400: se la guardia venisse tolta, la lettura andrebbe
    a buon fine e la richiesta risponderebbe 200.
    """
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((200, 3)) * 10.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 400


def test_il_clic_sul_gruppo_piccolo_risolve_al_cluster_piccolo(cliente, tmp_path):
    """Il controllo che smentisce (brief task-11a): il primo test passerebbe
    identico anche se l'endpoint ignorasse la mappa e rispondesse sempre col
    cluster piu' numeroso. Qui si clicca un indice disegnato che la mappa di
    decimazione fa risalire SOLO a indici del gruppo piccolo, e si pretende
    cluster_index == 1: nel ritorno di segment.cluster i gruppi sono
    ordinati per numerosita' decrescente (core/segment.py), quindi il gruppo
    piccolo non puo' mai finire in 0.

    Il gruppo piccolo qui e' 1 000 punti in un cubo da 7 mm e non da 10 mm
    come nel test del piano: con lo stesso cubo di 10 mm la densita' locale
    del gruppo piccolo (1 000 punti / 1000 mm^3) resta sotto la soglia che
    DBSCAN userebbe con cluster_min_points=50 e l'eps calcolato sulla
    spaziatura media DELLA NUVOLA MISTA (dominata dal gruppo grande, piu'
    denso): misurato, il gruppo piccolo cadrebbe intero nel rumore invece che
    in un proprio cluster, e il test non avrebbe piu' un cluster piccolo da
    pretendere. A 7 mm la densita' dei due gruppi e' paragonabile
    (3 000/1000mm^3 contro 1 000/343mm^3) e DBSCAN, coi predefiniti di
    SegmentConfig e senza toccare core.segment.cluster, trova davvero due
    cluster: misurato qui, 2 747 e 792 punti.

    L'indice disegnato non si legge da uno stato interno del server: si
    ricalcola con la stessa funzione (viewport.decimate) sugli stessi
    argomenti che l'endpoint /api/cloud/2 ha gia' usato (spacing_sample=20000,
    seed=0, i predefiniti di InputConfig che 'cliente' non sovrascrive), sulla
    nuvola riletta da disco esattamente come la rilegge il server: read_cloud
    passa per Open3D e non garantisce di restituire gli stessi byte scritti.
    """
    from meshrec.core import io, pipeline, viewport

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_due_cluster())

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=2000")
    assert risposta_nuvola.status_code == 200

    punti_letti, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[2])
    spaziatura = io.mean_spacing(punti_letti, 20_000, 0)
    _ridotti, gruppi, _voxel = viewport.decimate(punti_letti, 2_000, spaziatura)
    # Solo un gruppo i cui indici pieni appartengono TUTTI al secondo blocco:
    # i due blocchi sono a 500 mm di distanza e il voxel di decimazione e'
    # microscopico al confronto, quindi nessun gruppo dovrebbe mischiarli, ma
    # 'all' (e non 'any') lo pretende invece di assumerlo.
    disegnato = next(i for i, gruppo in enumerate(gruppi) if (gruppo >= 3_000).all())

    risposta = cliente.post("/api/cluster", json={"punto": disegnato})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["cluster_index"] == 1
    assert corpo["cluster_points"] < 2_000


def test_il_clic_sul_gruppo_a_cavallo_risolve_alla_maggioranza(cliente, tmp_path):
    """Task 11a, giro 2 (bloccante misurato in task-11a-review.md): un gruppo
    di decimazione a cavallo di un confine fra due cluster deve risolvere al
    cluster della MAGGIORANZA dei suoi punti pieni, non al primo.

    max_points=1 forza tutta la nuvola in un solo punto disegnato: il gruppo
    unico contiene sia il blocco minoranza (indici 0-799, primi nell'array)
    sia il blocco maggioranza (indici 800-3799). Misurato fuori dal test:
    DBSCAN trova due cluster, 2 875 punti (maggioranza, dal blocco grande) e
    238 punti (minoranza, dal blocco piccolo), e il PRIMO indice del gruppo
    (0) appartiene al cluster di minoranza (238). Con `pieno = gruppi[0][0]`
    (il codice del primo giro) la risposta sarebbe cluster_index=1 (238
    punti): questo test pretende il cluster di maggioranza, indice 0.
    """
    import numpy as np

    corsa = tmp_path / "corsa"
    minoranza = np.random.default_rng(1).random((800, 3)) * 7.0
    maggioranza = np.random.default_rng(2).random((3_000, 3)) * 10.0 + 500.0
    _prepara_click_semplice(cliente, corsa, np.vstack([minoranza, maggioranza]))

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["cluster_index"] == 0
    assert corpo["cluster_points"] > 2_000


def test_il_clic_sul_gruppo_in_pareggio_risolve_al_cluster_piu_popoloso_in_assoluto(cliente, tmp_path):
    """Il pareggio che la maggioranza da sola non decide (dichiarato in
    server.py, scegli_cluster): due copie traslate dello stesso blocco
    danno per costruzione due cluster della stessa numerosita' (misurato:
    1 375 e 1 375). A parita' di voti nel gruppo vince il cluster piu'
    popoloso IN ASSOLUTO; qui i due sono identici, quindi vince l'indice
    piu' basso (0), la scelta deterministica dichiarata.
    """
    import numpy as np

    corsa = tmp_path / "corsa"
    base = np.random.default_rng(0).random((1_500, 3)) * 10.0
    copia = base.copy()
    copia[:, 0] += 500.0
    _prepara_click_semplice(cliente, corsa, np.vstack([base, copia]))

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    # Precondizione: il pareggio e' avvenuto davvero, non solo per fortuna.
    assert corpo["clusters_found"] == 2
    assert corpo["cluster_sizes"][0] == corpo["cluster_sizes"][1]
    assert corpo["cluster_index"] == 0


def test_il_clic_sul_pareggio_esatto_fra_rumore_e_cluster_risolve_al_cluster(cliente, tmp_path):
    """Mutazione D del revisore (task-11a-fix-2-review.md): il commento di
    scegli_cluster dichiara "a parita' fra il cluster piu' votato e il
    rumore vince il cluster", ma nessun test costruiva il confine ESATTO
    (tutti i test esistenti hanno o rumore strettamente minoritario o
    maggioranza schiacciante). Qui un blocco di 55 punti fitti (stesso
    raggio 3 mm del test della maggioranza-rumore, sopra cluster_min_points
    =50) forma un cluster vero, e una catena di ESATTAMENTE 55 punti isolati
    (passo 50 mm, oltre l'eps calcolato sulla spaziatura mista) resta tutta
    rumore: misurato fuori dal test, voti-cluster=55 e voti-rumore=55, un
    pareggio esatto, non una minoranza. Con max_points=1 l'intera nuvola
    (110 punti) e' un solo gruppo disegnato, come nel test della
    maggioranza-rumore sopra. La richiesta deve rispondere 200 col cluster:
    con `>=` al posto di `>` (la mutazione D) il pareggio si leggerebbe come
    rumore in maggioranza e risponderebbe 400.
    """
    import numpy as np

    corsa = tmp_path / "corsa"
    denso = np.random.default_rng(0).random((55, 3)) * 3.0
    catena = np.zeros((55, 3))
    catena[:, 0] = 300.0 + np.arange(55) * 50.0
    _prepara_click_semplice(cliente, corsa, np.vstack([denso, catena]))

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    # Precondizione: il pareggio e' avvenuto davvero (55 voti-cluster contro
    # 55 voti-rumore), non un rumore minoritario che sarebbe accettato
    # comunque anche senza la regola del confine.
    assert corpo["clusters_found"] == 1
    assert corpo["cluster_sizes"][0] == 55
    assert corpo["noise_points"] == 55
    assert corpo["cluster_index"] == 0


def test_il_clic_sul_pareggio_di_voti_fra_cluster_di_taglia_diversa_risolve_al_piu_popoloso(
    cliente, tmp_path, monkeypatch
):
    """Mutazione E del revisore (task-11a-fix-2-review.md), la piu'
    istruttiva: il test ufficiale del pareggio (sopra) costruisce due
    cluster di taglia ASSOLUTA identica, quindi passa anche senza il
    criterio di spareggio dichiarato (`-kv[0]` nel key del max()), per
    coincidenza fra le taglie e l'ordine di iterazione del Counter — non
    perche' la regola "vince il cluster piu' popoloso IN ASSOLUTO" sia
    verificata.

    Qui i due cluster hanno taglia assoluta DIVERSA (misurato: 2 781 e 797
    punti su questa nuvola), ma il gruppo disegnato e' costruito a mano
    (patch di viewport.decimate_file, non la voxelizzazione vera) con
    ESATTAMENTE 5 voti a testa nel gruppo: un pareggio nei VOTI, non nella
    taglia. Gli indici del cluster PICCOLO stanno PRIMA di quelli del
    cluster GRANDE nell'array del gruppo, apposta: il Counter costruito
    iterando il gruppo incontra il piccolo per primo, quindi un max() senza
    lo spareggio esplicito (la mutazione E) risponderebbe il cluster
    piccolo, indice 1 — l'ordine di iterazione da solo non puo' dare la
    risposta corretta. La regola dichiarata pretende il piu' popoloso in
    assoluto, indice 0 (2 781 punti): solo lo spareggio esplicito lo
    garantisce contro quest'ordine avverso.
    """
    import numpy as np
    from meshrec.core import io, pipeline
    from meshrec.core.config import load_config

    corsa = tmp_path / "corsa"
    grande = np.random.default_rng(2).random((3_000, 3)) * 10.0
    piccolo = np.random.default_rng(1).random((1_000, 3)) * 7.0 + 500.0
    _prepara_click_semplice(cliente, corsa, np.vstack([grande, piccolo]))

    # Stesso calcolo che l'endpoint rifara' alla POST (ARTIFACTS[1] ->
    # remove_outliers -> crop_box -> extract_planes -> cluster, coi
    # predefiniti salvati da _prepara_click_semplice): gli indici scelti
    # qui devono restare validi in quel momento.
    cfg = load_config(tmp_path / "config.yaml")
    insiemi, metriche, _spaziatura = _clusterizza_come_l_endpoint(corsa, cfg)
    assert metriche["clusters_found"] == 2
    # Precondizione: le taglie ASSOLUTE sono diverse (altrimenti questo test
    # sarebbe solo una copia del pareggio-di-taglia-uguale sopra).
    assert metriche["cluster_sizes"][0] > metriche["cluster_sizes"][1]

    # Il gruppo disegnato e' un indice nella nuvola SERVITA (ARTIFACTS[2]),
    # non nel residuo: la stessa distinzione che fa l'endpoint.
    punti, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[2])

    def cluster_del_punto_pieno(indice_pieno: int) -> int | None:
        coordinata = punti[indice_pieno]
        return next(
            (
                indice
                for indice, insieme in enumerate(insiemi)
                if np.isclose(insieme, coordinata).all(axis=1).any()
            ),
            None,
        )

    grande_idx: list[int] = []
    piccolo_idx: list[int] = []
    for i in range(len(punti)):
        c = cluster_del_punto_pieno(i)
        if c == 0 and len(grande_idx) < 5:
            grande_idx.append(i)
        elif c == 1 and len(piccolo_idx) < 5:
            piccolo_idx.append(i)
        if len(grande_idx) == 5 and len(piccolo_idx) == 5:
            break
    assert len(grande_idx) == 5 and len(piccolo_idx) == 5

    # Il piccolo prima del grande: l'ordine di iterazione del Counter, da
    # solo, indicherebbe il piccolo.
    gruppo_avverso = np.array(piccolo_idx + grande_idx, dtype=np.int64)

    def decimate_file_finto(*_args, **_kwargs):
        return np.zeros((1, 3), dtype=np.float32), [gruppo_avverso], 1.0

    monkeypatch.setattr(server.viewport, "decimate_file", decimate_file_finto)

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["cluster_index"] == 0
    assert corpo["cluster_points"] == metriche["cluster_sizes"][0]


def test_il_clic_sul_gruppo_a_maggioranza_rumore_solleva_come_rumore(cliente, tmp_path):
    """La maggioranza-rumore che la maggioranza da sola non decide
    (dichiarato in server.py, scegli_cluster): un blocco di 55 punti
    fitti forma un cluster valido (>= cluster_min_points=50), ma una
    catena di 70 punti isolati (troppo radi per il min_points, anche se
    a coppie dentro l'eps globale) resta tutta rumore. Misurato fuori dal
    test: clusters_found=1, cluster_sizes=[55], noise_points=70 — il
    rumore e' in maggioranza STRETTA sul gruppo (70 contro 55).

    Il primo indice del gruppo (0) appartiene pero' al cluster valido: con
    `pieno = gruppi[0][0]` (il codice del primo giro) la risposta sarebbe
    200 col cluster da 55 punti, nascondendo che la maggioranza del gruppo
    e' rumore. Qui si pretende il rifiuto, e che nulla sia scritto su
    disco.
    """
    import numpy as np
    from meshrec.core.config import load_config

    corsa = tmp_path / "corsa"
    denso = np.random.default_rng(0).random((55, 3)) * 3.0
    catena = np.zeros((70, 3))
    catena[:, 0] = 300.0 + np.arange(70) * 50.0
    _prepara_click_semplice(cliente, corsa, np.vstack([denso, catena]))

    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    prima = load_config(tmp_path / "config.yaml")
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 400

    dopo = load_config(tmp_path / "config.yaml")
    assert dopo.segment.method == prima.segment.method
    assert dopo.segment.cluster_index == prima.segment.cluster_index


def test_un_indice_negativo_non_avvolge_al_gruppo_di_coda(cliente, tmp_path):
    """Mutazione A del revisore (task-11a-review.md): senza la guardia sui
    limiti, un indice negativo si indicizza da solo (regola di Python) e
    risponde il cluster di un gruppo che l'utente non ha cliccato, invece
    di rifiutare.

    Un solo blocco denso e non due, apposta: con due blocchi separati
    l'ultimo gruppo di decimazione (gruppi[-1]) e' quasi sempre rumore di
    bordo (misurato), e un 400 ottenuto cosi' non proverebbe la guardia,
    esattamente il rischio che il revisore segnala. Con 15 000 punti in
    un solo cubo, misurato fuori dal test, gruppi[-1] cade INTERO in un
    cluster vero (indice 0): senza la guardia la richiesta risponderebbe
    200, non 400, e questo test lo pretenderebbe rifiutato comunque.

    ARTIFACTS[1] scritto qui (con _prepara_click_semplice, non solo
    ARTIFACTS[2] come prima dell'allineamento): senza, dopo l'allineamento
    (task-11b) questo test passava per una ragione DIVERSA da quella che
    dichiara — la guardia nuova su ARTIFACTS[1] mancante avrebbe dato lo
    stesso 400 anche a guardia dei limiti RIMOSSA, e la mutazione A
    sarebbe rimasta invisibile (verificato per esecuzione: 74 passed con
    la guardia dei limiti tolta, prima di questa correzione).
    """
    import numpy as np

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((15_000, 3)) * 10.0
    _prepara_click_semplice(cliente, corsa, punti)

    cliente.get("/api/cloud/2?max_points=2000")
    risposta = cliente.post("/api/cluster", json={"punto": -1})
    assert risposta.status_code == 400


def test_il_cluster_index_scritto_su_disco_coincide_con_la_risposta(cliente, tmp_path):
    """Mutazione B del revisore: nessun test rileggeva config.yaml dopo la
    POST per verificare che cio' che finisce SUL DISCO sia cio' che torna
    NELLA RISPOSTA. E' la stessa specie di difetto che il ramo insegue da
    ieri (disco e schermo che divergono in silenzio).

    Serve un cluster_index DIVERSO da 0, altrimenti la mutazione
    'scrivi sempre 0' resterebbe invisibile per coincidenza: stessa nuvola
    di test_il_clic_sul_gruppo_piccolo_risolve_al_cluster_piccolo (7 mm,
    due cluster reali), click sul gruppo piccolo, cluster_index atteso 1.
    """
    from meshrec.core import io, pipeline, viewport
    from meshrec.core.config import load_config

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_due_cluster())

    cliente.get("/api/cloud/2?max_points=2000")
    punti_letti, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[2])
    spaziatura = io.mean_spacing(punti_letti, 20_000, 0)
    _ridotti, gruppi, _voxel = viewport.decimate(punti_letti, 2_000, spaziatura)
    disegnato = next(i for i, gruppo in enumerate(gruppi) if (gruppo >= 3_000).all())

    risposta = cliente.post("/api/cluster", json={"punto": disegnato})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["cluster_index"] == 1

    scritta = load_config(tmp_path / "config.yaml")
    assert scritta.segment.cluster_index == corpo["cluster_index"]
    assert scritta.segment.method == "auto"


def test_il_cluster_eps_e_sensibile_alla_spaziatura_vera(cliente, tmp_path):
    """Mutazione C del revisore: nessun test legava cluster_eps alla
    spaziatura calcolata sulla nuvola VERA. Il valore atteso e' ricalcolato
    qui in modo indipendente, sugli stessi punti e parametri che l'endpoint
    usa (spacing_sample=20000, seed=0, i predefiniti di InputConfig che
    'cliente' non sovrascrive); una spaziatura calcolata su un campione
    troncato (es. i primi 50 punti soli) darebbe un valore diverso.

    Sulla nuvola di _nuvola_un_cluster_e_rumore, che dichiara da se' perche'
    il secondo blocco sia rumore e non un secondo cluster. Il punto disegnato
    0 cade nel primo blocco perche' viewport.decimate ordina i gruppi per
    indice pieno minimo.
    """
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_un_cluster_e_rumore())

    cliente.get("/api/cloud/2?max_points=2000")
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()

    # La spaziatura vera si legge sull'ingresso GREZZO (ARTIFACTS[1]), non
    # sulla nuvola servita: e' la base su cui l'endpoint la ricalcola dopo
    # l'allineamento (task-11b), non piu' su ARTIFACTS[2].
    punti_letti, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[1])
    spaziatura_vera = io.mean_spacing(punti_letti, 20_000, 0)
    assert corpo["cluster_eps"] == pytest.approx(4.0 * spaziatura_vera)


def test_il_clic_dichiara_il_cambio_di_metodo(cliente, tmp_path):
    """Il cambio silenzioso crop -> auto (segnalato in task-11a-review.md,
    non verificabile dal browser): la risposta deve portare il metodo che
    c'era prima del clic e quello che c'e' dopo, cosi' chi mostra la UI
    puo' avvisare l'utente invece di lasciarlo scoprire il cambio da un
    file che non vede.

    Sulla nuvola di _nuvola_un_cluster_e_rumore, che dichiara da se' perche'
    il secondo blocco sia rumore e non un secondo cluster. Il punto disegnato
    0 cade nel primo blocco perche' viewport.decimate ordina i gruppi per
    indice pieno minimo.
    """

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_un_cluster_e_rumore())

    cliente.get("/api/cloud/2?max_points=2000")
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["method_before"] == "crop"
    assert corpo["method_after"] == "auto"


def test_il_secondo_clic_dichiara_auto_auto(cliente, tmp_path):
    """Buco minore segnalato in task-11a-fix-2-review.md (sezione 5): il
    test sopra copre solo il primo clic (crop -> auto). Un secondo clic
    sullo stesso gruppo, con cfg.segment.method gia' 'auto' dal primo, deve
    dichiarare method_before='auto' (letto davvero, non un valore stantio)
    e method_after='auto'.

    Sulla nuvola di _nuvola_un_cluster_e_rumore, che dichiara da se' perche'
    il secondo blocco sia rumore e non un secondo cluster. Il punto disegnato
    0 cade nel primo blocco perche' viewport.decimate ordina i gruppi per
    indice pieno minimo.
    """

    corsa = tmp_path / "corsa"
    _prepara_click_semplice(cliente, corsa, _nuvola_un_cluster_e_rumore())

    cliente.get("/api/cloud/2?max_points=2000")
    prima_risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert prima_risposta.status_code == 200
    assert prima_risposta.json()["method_after"] == "auto"

    seconda_risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert seconda_risposta.status_code == 200
    corpo = seconda_risposta.json()
    assert corpo["method_before"] == "auto"
    assert corpo["method_after"] == "auto"


def test_il_clic_senza_lo_step_1_non_solleva(cliente, tmp_path):
    """L'allineamento (task-11b) fa dipendere il clic da ARTIFACTS[1], non
    piu' solo da ARTIFACTS[2]: uno scenario nuovo, impossibile prima di
    questo giro, e' che la mappa sia popolata (02_segmented.ply esiste ed e'
    stato aperto nel viewport) ma 01_cloud.ply sia assente (una corsa mai
    arrivata allo step 1 con questo out_dir, o il file cancellato a mano).
    Deve fallire con un errore chiaro, non con l'eccezione grezza di
    io.read_cloud su un file mancante.
    """
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((200, 3)) * 10.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)  # niente ARTIFACTS[1]

    cliente.get("/api/cloud/2?max_points=200")
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] == "FileNotFoundError"
    assert pipeline.ARTIFACTS[1] in corpo["messaggio"]


def test_lindice_del_clic_coincide_con_quello_della_corsa_vera(cliente, tmp_path, monkeypatch):
    """La prova che l'allineamento (task-11b) tiene: l'indice che il clic
    sceglie e quello che la corsa 'auto' assegnerebbe DAVVERO allo stesso
    punto devono coincidere. Prima di questo giro non coincidevano: il clic
    clusterizzava 02_segmented.ply intero (senza extract_planes), mentre la
    corsa clusterizza il residuo DOPO extract_planes (core/segment.py,
    segment_cloud, righe 146-150) — sul dato vero (lab_crop) 4293 gruppi
    (il clic, sbagliato) contro 2447 (la corsa), vedi
    task-11b-allineamento.md.

    Qui un "pavimento" piatto (2 000 punti a z=0 su 30x30 mm, un piano vero)
    sta sopra la soglia di estrazione (plane_min_points_ratio=0.05 di 4 000
    punti = 200), e due "pareti" (1 500 e 500 punti, cubi separati fra loro
    e lontani dal pavimento) restano nel residuo. Con plane_max_count=1
    l'estrazione si ferma dopo il pavimento, deterministica: il residuo e'
    ESATTAMENTE le due pareti, 2 000 punti.

    La differenza e' osservabile, misurata (non solo dedotta): con
    cluster_eps_factor=8 (vedi sotto) il pavimento e' denso abbastanza da
    formare DBSCAN un cluster vero anche SENZA extract_planes (il difetto),
    non solo rumore — la scelta che rende la mutazione visibile invece di
    silenziosamente innocua (un pavimento troppo rado, misurato in un primo
    tentativo, finiva sempre in rumore in entrambi i casi, e la mutazione
    passava lo stesso test per coincidenza). Cosi' DBSCAN sull'intera nuvola
    (pavimento+pareti) trova TRE cluster ordinati per numerosita'
    decrescente (2000, 1500, 500), zero rumore: un clic sulla parete
    piccola risolverebbe all'indice 2 — il pavimento occuperebbe lo 0. CON
    extract_planes (questo giro), il residuo ha solo le due pareti: lo
    stesso clic deve risolvere all'indice 1, che e' anche l'indice che la
    clusterizzazione REALE (ricalcolata qui sotto, indipendentemente
    dall'endpoint, con la stessa sequenza che la corsa 'auto' esegue)
    assegna allo stesso punto.
    """
    import numpy as np
    from meshrec.core import io, pipeline, segment
    from meshrec.core.config import load_config

    corsa = tmp_path / "corsa"
    rng_pavimento = np.random.default_rng(3)
    pavimento = np.zeros((2_000, 3))
    pavimento[:, 0] = rng_pavimento.random(2_000) * 30.0
    pavimento[:, 1] = rng_pavimento.random(2_000) * 30.0
    parete_grande = np.random.default_rng(4).random((1_500, 3)) * 10.0 + np.array(
        [0.0, 0.0, 2_000.0]
    )
    parete_piccola = np.random.default_rng(5).random((500, 3)) * 7.0 + np.array(
        [500.0, 0.0, 2_000.0]
    )
    nuvola = np.vstack([pavimento, parete_grande, parete_piccola])

    io.write_cloud(corsa / pipeline.ARTIFACTS[1], nuvola)
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], nuvola)

    attuale = cliente.get("/api/config").json()
    attuale["segment"]["plane_max_count"] = 1
    attuale["segment"]["outlier_std_ratio"] = 1_000_000.0
    # plane_distance_factor piccolo: col predefinito (3.0) la soglia
    # (~5,8 mm, misurato) e' comparabile all'estensione dei cubi delle
    # pareti (10 e 7 mm) e RANSAC trova per rumore un "piano" che ne
    # cattura una fetta — misurato, 1 951 dei 2 025 punti del piano
    # spurio venivano dalle pareti, non dal pavimento. A 0.1 la soglia
    # (~0,04 mm, misurato con questa spaziatura) e' trascurabile rispetto
    # ai cubi e cattura solo il pavimento, che e' esattamente a z=0 e
    # quindi a distanza zero da qualunque soglia positiva.
    attuale["segment"]["plane_distance_factor"] = 0.1
    # cluster_eps_factor piu' largo del predefinito (4): misurato, e'
    # cio' che serve perche' il pavimento denso (30x30 mm, 2000 punti)
    # formi un cluster DBSCAN vero invece di cadere in rumore — la
    # condizione che rende la mutazione (saltare extract_planes) visibile.
    attuale["segment"]["cluster_eps_factor"] = 8.0
    risposta_cfg = cliente.put("/api/config", json=attuale)
    assert risposta_cfg.status_code == 200

    # Oracolo: la clusterizzazione REALE, calcolata fuori dall'endpoint,
    # con la stessa sequenza di segment_cloud quando method='auto'
    # (core/segment.py:146-150): remove_outliers -> crop_box ->
    # extract_planes -> cluster, sullo stesso ingresso grezzo che
    # l'endpoint legge.
    cfg = load_config(tmp_path / "config.yaml")
    grezzi, _normali = io.read_cloud(corsa / pipeline.ARTIFACTS[1])
    spaziatura = io.mean_spacing(grezzi, cfg.input.spacing_sample, cfg.input.seed)
    puliti, _metriche_outlier = segment.remove_outliers(grezzi, cfg.segment)
    ritagliati, _metriche_crop = segment.crop_box(puliti, cfg.segment)
    _piani, residuo, metriche_piani = segment.extract_planes(ritagliati, cfg.segment, spaziatura)
    # Precondizione: il pavimento e' stato estratto come piano vero, e il
    # residuo sono esattamente le due pareti.
    assert metriche_piani["planes_found"] == 1
    assert metriche_piani["residual_points"] == 2_000
    insiemi_reali, metriche_reali = segment.cluster(residuo, cfg.segment, spaziatura)
    assert metriche_reali["clusters_found"] == 2
    assert metriche_reali["cluster_sizes"] == [1_500, 500]

    # Il punto cliccato: un punto della parete piccola, individuato per
    # coordinate nel residuo reale (indice 1 dell'oracolo), non per
    # posizione nell'array di partenza.
    punto_parete_piccola = insiemi_reali[1][0]
    indice_pieno = int(np.where((nuvola == punto_parete_piccola).all(axis=1))[0][0])

    def decimate_file_finto(*_args, **_kwargs):
        return (
            np.zeros((1, 3), dtype=np.float32),
            [np.array([indice_pieno], dtype=np.int64)],
            1.0,
        )

    monkeypatch.setattr(server.viewport, "decimate_file", decimate_file_finto)
    risposta_nuvola = cliente.get("/api/cloud/2?max_points=1")
    assert risposta_nuvola.status_code == 200

    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    # La prova che conta: l'indice del clic coincide con l'indice che la
    # clusterizzazione REALE assegna allo stesso punto. Prima
    # dell'allineamento l'endpoint avrebbe risposto 2 (la parete piccola e'
    # la terza per numerosita' clusterizzando pavimento+pareti insieme,
    # senza extract_planes): questo test fallisce con quel codice (vedi
    # mutazione nel rapporto).
    assert corpo["cluster_index"] == 1
    assert corpo["cluster_points"] == 500


def _scrivi_volume(corsa: Path, punti, tetraedri) -> None:
    """Un .vtu allo step 9, come lo scriverebbe abaqus.write_vtu."""
    import meshio
    import numpy as np

    from meshrec.core import pipeline

    corsa.mkdir(exist_ok=True)
    meshio.write_points_cells(
        corsa / pipeline.ARTIFACTS[9], np.asarray(punti), [("tetra", np.asarray(tetraedri))]
    )


def _mesh_dalla_risposta(risposta):
    """Vertici e facce ricostruiti dal corpo binario come fa il browser."""
    import numpy as np

    vertici = int(risposta.headers["X-Vertices"])
    triangoli = int(risposta.headers["X-Triangles"])
    assert len(risposta.content) == vertici * 3 * 4 + triangoli * 3 * 4
    return (
        np.frombuffer(risposta.content, dtype="<f4", count=vertici * 3).reshape(vertici, 3),
        np.frombuffer(risposta.content, dtype="<u4", offset=vertici * 3 * 4).reshape(triangoli, 3),
    )


def test_il_contorno_restituisce_gli_indici_dei_nodi_originali(tmp_path):
    """Senza la corrispondenza, un campo per nodo non sa dove va.

    `np.unique(..., return_inverse)` la calcola gia' dentro `_contorno_del_volume`
    e fino alla Fase 5 la buttava via. Riallinearla a valle, in ogni consumatore,
    sarebbe la forma d'errore che la Fase 5 esiste per non commettere: un indice
    che scivola e nessuna metrica che lo smentisce.

    Il nodo isolato (indice 2) resta fuori dal contorno: senza di lui `indici`
    coinciderebbe con `np.arange`, e la mutazione dello step 6 non morderebbe.
    """
    import numpy as np

    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [9.0, 9.0, 9.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    corsa = tmp_path / "corsa"
    _scrivi_volume(corsa, punti, [[0, 1, 3, 4]])

    from meshrec.core import pipeline

    vertici, _facce, indici = server._contorno_del_volume(corsa / pipeline.ARTIFACTS[9])

    assert len(indici) == len(vertici)
    assert vertici == pytest.approx(punti[indici])


def test_una_voce_di_contorno_con_indici_di_lunghezza_sbagliata_e_rifiutata(tmp_path):
    """M10 del giro finale: `_leggi_contorno` negava `facce.max() >= len(vertici)`
    ma non `len(indici) != len(vertici)`.

    `indici` e' l'unico dei tre che indicizza un array **diverso**
    (`griglia.point_data`, non `vertici`), quindi l'argomento del commento
    accanto vale di piu' per lui, non di meno: `/api/campo` lo usa per
    ritagliare il campo sui nodi del contorno. Lungo o corto con valori tutti
    in dominio, numpy non solleva; il colore si posa sfalsato di un nodo e
    nessuno lo dice.

    Mutazione che uccide: togliere la guardia `len(indici) != len(vertici)`.
    Senza, `_leggi_contorno` restituisce la voce e l'assert cade.
    """
    import numpy as np

    vertici = np.zeros((4, 3), dtype="<f4")
    facce = np.array([[0, 1, 2]], dtype="<u4")
    voce = tmp_path / "voce.npz"

    # Corta: tre indici per quattro vertici. Tutti in dominio su point_data.
    np.savez(voce, vertici=vertici, facce=facce, indici=np.array([0, 1, 2], dtype="<u4"))
    assert server._leggi_contorno(voce) is None

    # Lunga: cinque indici per quattro vertici.
    np.savez(voce, vertici=vertici, facce=facce, indici=np.arange(5, dtype="<u4"))
    assert server._leggi_contorno(voce) is None

    # Giusta: la voce sana continua a passare, altrimenti la guardia avrebbe
    # solo spento la cache.
    np.savez(voce, vertici=vertici, facce=facce, indici=np.arange(4, dtype="<u4"))
    assert server._leggi_contorno(voce) is not None


def test_il_campo_legge_il_vtu_una_volta_sola(cliente, tmp_path, monkeypatch):
    """I3 del giro finale, differito due volte.

    `campo()` faceva `meshio.read(percorso)` per i campi di soluzione e poi
    chiamava `_contorno_del_volume(percorso)`, che a cache fredda rileggeva lo
    stesso file. Due letture intere per richiesta: su 13_solution.vtu di
    runs/lab_telaio_v2, 8,58 MB misurati il 22/08/2026, e su lab_crop il
    commento a VERSIONE_CONTORNO dichiara «circa 15 s e oltre un gigabyte di
    picco». Tutto sul primo clic del pannello Campo, che e' quello della
    dimostrazione.

    Mutazione che uccide: rimettere `_contorno_del_volume(percorso)` senza la
    griglia. Il contatore arriva a 2 e l'assert cade.
    """
    import meshio
    import numpy as np

    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [9.0, 9.0, 9.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    _scrivi_soluzione(
        tmp_path / "corsa", punti, [[0, 1, 3, 4]], {"VM_GRAVITA": np.arange(5.0)}
    )

    letture = []
    vera = meshio.read

    def contata(percorso, *resto, **chiavi):
        letture.append(Path(percorso).name)
        return vera(percorso, *resto, **chiavi)

    monkeypatch.setattr(meshio, "read", contata)

    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 200
    assert letture.count("13_solution.vtu") == 1, (
        f"il .vtu e' stato letto {letture.count('13_solution.vtu')} volte: {letture}"
    )


def test_il_contorno_del_volume_porta_solo_i_vertici_che_disegna(cliente, tmp_path):
    """X-Vertices deve contare i vertici che il browser disegna davvero.

    griglia.points contiene anche i nodi interni della tetraedralizzazione,
    che nessuna faccia di contorno tocca: qui il nodo isolato non appartiene ad
    alcun tetraedro, e se finisse nella risposta il conteggio mostrato a video
    non sarebbe sostenuto da nessuna lettura.

    Il nodo isolato sta all'indice 2, in mezzo, e non in coda: con l'intruso in
    fondo la rimappatura sarebbe l'identita' e il test non distinguerebbe una
    mappa corretta da un semplice troncamento della coda dei nodi, che e'
    proprio il modo in cui la compattazione puo' essere disfatta per sbaglio.
    """
    import numpy as np

    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [9.0, 9.0, 9.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    _scrivi_volume(tmp_path / "corsa", punti, [[0, 1, 3, 4]])

    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 200
    # Le quattro facce del solo tetraedro, sui suoi soli quattro nodi.
    assert (risposta.headers["X-Vertices"], risposta.headers["X-Triangles"]) == ("4", "4")
    vertici, facce = _mesh_dalla_risposta(risposta)
    # Le coordinate, non il conteggio: sono i nodi 0, 1, 3, 4 e non i primi
    # quattro dell'array, che comprenderebbero l'intruso.
    assert np.array_equal(vertici, punti[[0, 1, 3, 4]].astype("<f4"))
    # Rimappati sui vertici mandati: un indice fuori intervallo non disegna.
    assert facce.max() < len(vertici)


def test_il_contorno_del_volume_torna_con_le_facce_uscenti(cliente, tmp_path):
    """Il verso delle facce, che np.sort perde e return_index conserva.

    Il criterio e' il volume con segno racchiuso dalle facce restituite: con
    le facce ordinate invece che orientate il conto da' un altro numero (su
    lab_crop, -1.202.490 contro 173.282.926). Il tetraedro e' traslato lontano
    dall'origine apposta: nell'origine mesh_volume vale 1/6 in entrambi i casi
    e il test non morderebbe.
    """
    import numpy as np

    from meshrec.core import quality

    base = np.array([10.0, 10.0, 10.0])
    punti = base + np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_volume(tmp_path / "corsa", punti, [[0, 1, 2, 3]])

    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 200
    vertici, facce = _mesh_dalla_risposta(risposta)
    # Positivo e pari al volume del tetraedro: le quattro facce sono uscenti.
    # Con le facce ordinate lo stesso conto darebbe 6,833333.
    assert quality.mesh_volume(vertici, facce) == pytest.approx(1.0 / 6.0)


def test_la_seconda_richiesta_del_contorno_non_riestrae(cliente, tmp_path, monkeypatch):
    """I-3 della revisione: l'estrazione costa 14,9 s e oltre un gigabyte di
    picco su lab_crop, e senza cache si rifa' identica a ogni clic. La prova e'
    osservabile e non temporale, come per /api/cloud: la seconda richiesta deve
    riuscire anche se leggere il file adesso solleva.
    """
    import meshio
    import numpy as np

    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    _scrivi_volume(tmp_path / "corsa", punti, [[0, 1, 2, 3]])

    prima = cliente.get("/api/mesh/9")
    assert prima.status_code == 200

    def _non_chiamarmi(*_args, **_kwargs):
        raise AssertionError("il contorno non deve essere riestratto a cache calda")

    monkeypatch.setattr(meshio, "read", _non_chiamarmi)
    poi = cliente.get("/api/mesh/9")
    assert poi.status_code == 200
    assert poi.content == prima.content
    assert poi.headers["X-Vertices"] == prima.headers["X-Vertices"]
    assert poi.headers["X-Triangles"] == prima.headers["X-Triangles"]


def test_una_voce_di_cache_incoerente_non_arriva_al_browser(cliente, tmp_path):
    """BL-2: una voce formalmente valida ma con un indice oltre i vertici.

    np.load la legge senza un rumore e nessun indice fuori misura solleva in
    numpy: il 200 arriva al browser con una faccia che punta oltre l'array di
    vertici appena mandato, three.js disegna fuori dall'attributo position e
    non lo dice a nessuno. Una voce cosi' si tratta come corrotta e si
    ricalcola, la stessa cura che _leggi_cache da' al suo offsets.
    """
    import numpy as np

    from meshrec.core import pipeline

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_volume(tmp_path / "corsa", punti, [[0, 1, 2, 3]])
    assert cliente.get("/api/mesh/9").status_code == 200

    voce = server._percorso_contorno(tmp_path / "corsa" / pipeline.ARTIFACTS[9])
    assert voce.exists(), "la prima richiesta non ha scritto la voce che il test avvelena"
    np.savez(
        str(voce),
        vertici=np.zeros((4, 3), dtype="<f4"),
        facce=np.full((1, 3), 99, dtype="<u4"),
    )

    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 200
    vertici, facce = _mesh_dalla_risposta(risposta)
    # Il contorno vero del tetraedro, non la voce avvelenata.
    assert (risposta.headers["X-Vertices"], risposta.headers["X-Triangles"]) == ("4", "4")
    assert facce.max() < len(vertici), "un indice oltre i vertici e' arrivato al browser"


def test_cambiare_la_versione_della_cache_del_contorno_fa_ricalcolare(
    cliente, tmp_path, monkeypatch
):
    """BL-2, l'altra meta': la chiave (sorgente, mtime) non registra il codice.

    Il verso delle facce (quality._TET_FACES) e la regola di compattazione dei
    vertici decidono il risultato e nella chiave non ci sono: se cambiano, ogni
    voce gia' su disco risponde col risultato vecchio per tutta la vita del
    file sorgente. La versione nel nome le sfratta, perche' la pulizia per
    marchio non guarda che cosa segue il marchio.

    La forma osservabile e' quella di test_la_seconda_richiesta_del_contorno_non_riestrae,
    al contrario: con la lettura del volume che solleva, la richiesta deve
    fallire: se riesce, ha riusato la voce della versione precedente.
    """
    import meshio
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_volume(tmp_path / "corsa", punti, [[0, 1, 2, 3]])
    assert cliente.get("/api/mesh/9").status_code == 200

    monkeypatch.setattr(server, "VERSIONE_CONTORNO", server.VERSIONE_CONTORNO + 1)

    def _riestrazione(*_args, **_kwargs):
        raise RuntimeError("riestratto")

    monkeypatch.setattr(meshio, "read", _riestrazione)
    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 400, "la voce della versione precedente e' stata riusata"
    assert risposta.json()["errore"] == "RuntimeError"


def test_un_volume_senza_tetraedri_dice_che_cosa_contiene(cliente, tmp_path):
    """M-2: cells_dict["tetra"] dava un KeyError nudo ("'tetra'"), la stessa
    forma inutile che la guardia sullo step ha appena tolto."""
    import meshio
    import numpy as np

    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    meshio.write_points_cells(
        corsa / pipeline.ARTIFACTS[9],
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        [("triangle", np.array([[0, 1, 2]]))],
    )

    risposta = cliente.get("/api/mesh/9")
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] != "KeyError"
    assert "tetra" in corpo["messaggio"] and "triangle" in corpo["messaggio"]


def test_una_nuvola_chiesta_come_mesh_e_rifiutata_invece_di_tornare_vuota(cliente, tmp_path):
    """M-3: 01_cloud.ply letto con read_triangle_mesh da' vertici e zero facce.
    Un 200 con X-Triangles: 0 farebbe disegnare un solido vuoto."""
    import numpy as np

    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((100, 3)) * 10.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)

    risposta = cliente.get("/api/mesh/1")
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert "triangoli" in corpo["messaggio"]
    assert "0 triangoli" in corpo["messaggio"]


def _scrivi_soluzione(corsa: Path, punti, tetraedri, point_data: dict) -> None:
    """13_solution.vtu come lo scriverebbe solve.risolvi (Task 6): stesso
    schema di _scrivi_volume, con i campi per nodo del contratto di solve.py."""
    from meshrec.core import abaqus, pipeline

    corsa.mkdir(exist_ok=True)
    abaqus.write_vtu(corsa / pipeline.ARTIFACTS[13], punti, tetraedri, point_data=point_data)


def test_il_campo_risponde_i_valori_del_contorno_col_proprio_massimo(cliente, tmp_path):
    """Il nodo isolato (indice 2) non e' un vertice del contorno: se il campo
    filtrato dagli indici sbagliasse, o la lunghezza del corpo non tornerebbe
    (4 vertici, non 5) o il massimo dichiarato includerebbe il suo valore (99),
    che qui e' fuori scala apposta."""
    import numpy as np

    punti = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [9.0, 9.0, 9.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    vm_gravita = np.array([1.0, 2.0, 99.0, 3.0, 4.0])
    _scrivi_soluzione(
        tmp_path / "corsa", punti, [[0, 1, 3, 4]], {"VM_GRAVITA": vm_gravita}
    )

    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 200
    valori = np.frombuffer(risposta.content, dtype="<f4")
    # Nodi 0, 1, 3, 4 nell'ordine dei vertici del contorno (non 0..3): il
    # nodo isolato (indice 2, valore 99) resta fuori.
    assert valori == pytest.approx([1.0, 2.0, 3.0, 4.0])
    # 4.0 e non 99: il nodo isolato non e' un vertice del contorno e non
    # partecipa al massimo.
    assert float(risposta.headers["X-Max"]) == pytest.approx(4.0)
    # Il taglio della scala (p99) lo calcola il browser sui valori che riceve,
    # in viewport.scalaDelCampo: X-Min, X-P99 e X-Sopra-P99 c'erano e nessuno
    # le leggeva. Un dato che il client ignora invecchia in silenzio.
    assert "X-Min" not in risposta.headers
    assert "X-P99" not in risposta.headers
    assert "X-Sopra-P99" not in risposta.headers


def test_il_campo_u_e_la_magnitudine_dello_spostamento(cliente, tmp_path):
    """U_<caso> e' un vettore (spostamento nodale): un corpo con tre float per
    vertice romperebbe la corrispondenza 1-a-1 coi vertici del contorno che
    l'intestazione X-Vertices di /api/mesh promette. La magnitudine e' l'unica
    riduzione a scalare che non butta via nessuna direzione piu' delle altre."""
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    u_gravita = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    _scrivi_soluzione(tmp_path / "corsa", punti, [[0, 1, 2, 3]], {"U_GRAVITA": u_gravita})

    risposta = cliente.get("/api/campo/GRAVITA/U")

    assert risposta.status_code == 200
    valori = np.frombuffer(risposta.content, dtype="<f4")
    assert valori == pytest.approx([5.0, 0.0, 0.0, 0.0])


@pytest.mark.parametrize("caso, grandezza", [
    ("PIPPO", "VM"),
    ("GRAVITA", "PIPPO"),
    ("%2e%2e", "VM"),
])
def test_caso_o_grandezza_inesistenti_tornano_quattrocento_non_keyerror(
    cliente, tmp_path, caso, grandezza
):
    """Ingressi degeneri: nessuno di questi valori esiste in point_data, e
    nessuno di essi costruisce un percorso sul filesystem (la chiave e' solo
    una voce di un dict gia' in memoria) -- '%2e%2e' (".." con caratteri
    percent-encoded, che arriva decodificato al parametro di rotta) non fa
    quindi leggere nulla fuori dalla cartella della corsa.

    Un ".." letterale non arriva nemmeno qui: la normalizzazione dell'URL lato
    client collassa il segmento prima ancora di spedire la richiesta, e
    FastAPI risponde 404 di suo perche' nessuna rotta corrisponde -- una
    protezione precedente alla mia, non verificabile da questo test.
    """
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_soluzione(
        tmp_path / "corsa", punti, [[0, 1, 2, 3]], {"VM_GRAVITA": np.ones(4)}
    )

    risposta = cliente.get(f"/api/campo/{caso}/{grandezza}")

    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] != "KeyError"


def test_un_modo_chiesto_come_u_o_vm_e_rifiutato_con_un_messaggio(cliente, tmp_path):
    """MODO_<n> non ha ne' U_ ne' VM_: e' una forma normalizzata sulla massa,
    non uno spostamento fisico (solve.py:185-190). Il messaggio deve dirlo,
    non limitarsi a "non trovato"."""
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_soluzione(
        tmp_path / "corsa", punti, [[0, 1, 2, 3]], {"MODO_1": np.ones((4, 3))}
    )

    risposta = cliente.get("/api/campo/MODO_1/VM")

    assert risposta.status_code == 400
    corpo = risposta.json()
    assert "massa" in corpo["messaggio"]


def test_soluzione_assente_torna_quattrocento_dichiarato(cliente):
    """Una corsa fermata allo step 12 (normale in uno sweep) non ha
    13_solution.vtu: deve dirlo, non tornare una traccia di stack."""
    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 400
    corpo = risposta.json()
    assert set(corpo) == {"errore", "messaggio"}
    assert corpo["errore"] == "FileNotFoundError"


def test_vtu_senza_point_data_torna_quattrocento_non_attributeerror(cliente, tmp_path):
    """Un .vtu scritto senza campi (point_data=None) non deve far esplodere
    la lettura di point_data con un AttributeError."""
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_soluzione(tmp_path / "corsa", punti, [[0, 1, 2, 3]], {})

    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 400
    assert risposta.json()["errore"] != "AttributeError"


def test_contorno_con_zero_vertici_risponde_vuoto_senza_indexerror(cliente, tmp_path, monkeypatch):
    """Un volume senza tetraedri (sweep interrotto a meta' scrittura, o un
    caso limite geometrico) da' un contorno vuoto: _contorno_del_volume non
    solleva (verificato con numpy direttamente), ma il campo endpoint deve
    anche lui restare in piedi invece di sollevare da np.percentile su un
    array vuoto."""
    import meshio
    import numpy as np

    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    percorso = corsa / pipeline.ARTIFACTS[13]
    percorso.write_bytes(b"non importa: meshio.read e' rimpiazzata")

    class _MeshVuota:
        cells_dict = {"tetra": np.zeros((0, 4), dtype=np.int64)}
        points = np.zeros((4, 3))
        point_data = {"VM_GRAVITA": np.zeros((4,))}

    monkeypatch.setattr(meshio, "read", lambda _percorso: _MeshVuota())

    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 200
    assert risposta.content == b""
    assert risposta.headers["X-Max"] == "0.0"


def test_campo_costante_risponde_il_proprio_massimo_senza_divisione(cliente, tmp_path):
    """max == min: se l'intestazione nascesse da una normalizzazione
    (valore - min) / (max - min), qui dividerebbe per zero. Qui non c'e' alcuna
    divisione, e questo test lo pin-na: il massimo di un campo costante e' la
    costante stessa."""
    import numpy as np

    punti = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _scrivi_soluzione(
        tmp_path / "corsa", punti, [[0, 1, 2, 3]], {"VM_GRAVITA": np.full(4, 7.0)}
    )

    risposta = cliente.get("/api/campo/GRAVITA/VM")

    assert risposta.status_code == 200
    assert float(risposta.headers["X-Max"]) == pytest.approx(7.0)


def test_il_clic_sullo_step_sceglie_fra_nuvola_e_mesh_senza_perdere_il_pannello():
    """Il gestore del clic apre anche il pannello dei parametri (Task 8): una
    riscrittura che ne sostituisce l'intero corpo lo perderebbe in silenzio."""
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    # La fetta finisce dove finisce il gestore. Senza il secondo split prendeva
    # tutto il file che segue, e i due asserti erano vacui tutti e due:
    # `ricaricaVista` chiama `mostraStep` piu' sotto, e `apriDettaglio(numero`
    # trovava la **propria definizione**. Provato: svuotando del tutto il
    # gestore del clic, il test passava lo stesso.
    gestore = testo.split('getElementById("elenco-step").addEventListener', 1)[1]
    gestore = gestore.split("\n});", 1)[0]
    # Il numero d'ordine del giro 2 (I-4) aggiunge un argomento a entrambe: cio'
    # che il test difende e' che il clic le chiami tutte e due sullo step
    # cliccato, non quanti argomenti passi. La geometria passa da ricaricaVista,
    # che e' l'unico punto in cui e' chiesta.
    assert re.search(r"ricaricaVista\(numero[,)]", gestore), gestore
    assert re.search(r"apriDettaglio\(numero[,)]", gestore), gestore


def _sorgente_di(nome: str, testo: str) -> str:
    """Il corpo di una funzione di primo livello, dalla firma alla graffa che la
    chiude in prima colonna. I moduli dell'interfaccia non sono importabili da
    qui (importano percorsi serviti dal server), quindi si estrae il testo.

    `async` va tenuto: senza, il testo estratto resta leggibile ma non e' piu'
    eseguibile — `await` dentro una funzione non asincrona e' un errore di
    sintassi, e il banco che esegue queste funzioni morirebbe prima di provare
    qualcosa.
    """
    corpo = testo.split(f"function {nome}(", 1)[1]
    prefisso = "async " if f"async function {nome}(" in testo else ""
    return f"{prefisso}function {nome}(" + corpo.split("\n}\n", 1)[0] + "\n}"


def test_una_risposta_superata_si_scarta_e_una_corrente_no():
    """I-4. La regola dell'ordine sta in una funzione pura apposta perche' si
    possa provare senza un motore di DOM. Se la sua polarita' si invertisse, o
    ogni risposta verrebbe buttata (la vista non cambierebbe piu') o nessuna (il
    difetto tornerebbe): entrambe passerebbero un test solo testuale."""
    from meshrec.app.server import UI_DIR

    node = shutil.which("node")
    if node is None:
        pytest.skip("node non installato: la regola resta verificata a mano")
    sorgente = _sorgente_di("superata", (UI_DIR / "app.js").read_text(encoding="utf-8"))
    prova = Path(__file__).parent / "_prova_ordine.mjs"
    prova.write_text(
        sorgente + "\n"
        "import assert from 'node:assert/strict';\n"
        # Una risposta partita prima di un clic successivo e' superata.
        "assert.equal(superata(1, 2), true);\n"
        # Quella della generazione in corso passa, ed e' l'unica.
        "assert.equal(superata(2, 2), false);\n"
        # Anche la prima in assoluto, che non deve restare bloccata.
        "assert.equal(superata(1, 1), false);\n",
        encoding="utf-8",
    )
    try:
        esito = subprocess.run([node, str(prova)], capture_output=True, text=True)
        assert esito.returncode == 0, esito.stderr
    finally:
        prova.unlink()


def _corpi_freccia_asincroni(testo: str) -> list[str]:
    """I corpi dei gestori `async (...) => {` e `async x => {`, contando le graffe.

    Il regex delle funzioni nominate non li vede: un gestore inline non ha un
    nome e non chiude in prima colonna, quindi la regola dell'ordine vi
    resterebbe scoperta con l'aria di essere coperta. L'alternanza copre anche
    il parametro singolo senza parentesi, che e' la forma piu' comune delle
    tre che restavano invisibili.

    Il tetto vero, misurato caso per caso (I-2 della revisione), perche' quello
    dichiarato prima non era questo:
    - una graffa **aperta** spaiata in una stringa o in un commento non fa
      finire il corpo nel posto sbagliato: fa sparire la tratta dall'elenco
      senza estrarre niente, in silenzio;
    - una graffa **chiusa** spaiata tronca il corpo, e li' si', la guardia
      potrebbe restare fuori da cio' che si legge;
    - restano invisibili il corpo conciso (`async () => (await f()).json()`) e
      le parentesi dentro i parametri (`async ({ a = (1) }) => {`);
    - le frecce annidate sono contate due volte, quindi l'interna pretende una
      guardia sua anche quando l'esterna ce l'ha.

    La soglia finale `interrogano >= 6` pareggia il numero vero di tratte, e
    copre **una sola** di queste direzioni: se una tratta sparisce dall'elenco,
    per una graffa spaiata o per una cancellazione, il conteggio scende e la
    soglia lo dice. Non copre l'altra, che era il caso di I-2: una tratta
    **aggiunta** in una delle forme invisibili non fa scendere niente —
    `interrogano` resta 6, `>= 6` resta vero, e il test resta verde con un
    gestore senza guardia dentro il modulo. Per quella direzione la rete e' il
    riconoscimento della forma, cioe' l'alternanza qui sopra, e le forme che
    l'alternanza non riconosce restano scoperte.
    """
    corpi = []
    for avvio in re.finditer(r"async\s*(?:\([^)]*\)|\w+)\s*=>\s*\{", testo):
        profondita = 0
        for posizione in range(avvio.end() - 1, len(testo)):
            profondita += {"{": 1, "}": -1}.get(testo[posizione], 0)
            if profondita == 0:
                corpi.append(testo[avvio.start() : posizione + 1])
                break
    return corpi


def test_lo_scanner_vede_anche_la_freccia_senza_parentesi():
    """I-2. `async evento => { ... }` e' la forma piu' comune delle tre che
    restavano invisibili, e un gestore scritto cosi' entrava nel modulo senza
    guardia lasciando il test verde: la tratta non veniva vista e il conteggio
    non cambiava. Il tetto residuo e' dichiarato in _corpi_freccia_asincroni.
    """
    con_parentesi = 'async () => { await fetch("/api/x"); superata(o); }'
    senza_parentesi = 'async evento => { await fetch("/api/y"); esito.textContent = "fatto"; }'
    assert len(_corpi_freccia_asincroni(con_parentesi)) == 1
    assert len(_corpi_freccia_asincroni(senza_parentesi)) == 1, "la freccia senza parentesi e' invisibile"
    # E il corpo estratto arriva intero fino alla graffa che lo chiude: se si
    # fermasse prima, la guardia potrebbe restare fuori da cio' che si legge.
    assert _corpi_freccia_asincroni(senza_parentesi)[0].endswith('"fatto"; }')


def test_ogni_tratta_che_interroga_il_server_si_scarta_se_e_stata_superata():
    """I-4, sulla tratta e non sulla funzione: l'elenco non e' scritto a mano ma
    ricavato dal modulo, cosi' una tratta aggiunta domani vi entra da sola e non
    puo' essere dimenticata. Le funzioni freccia asincrone entrano nell'elenco
    quanto quelle nominate: la meta' dei gestori dell'interfaccia sono inline, e
    lasciarle fuori teneva aperto un buco con l'aria di essere chiuso.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    # caricaStato e caricaGalleria partono una volta sola all'avvio della
    # pagina e non da un clic: non c'e' nessuna generazione che possa
    # superarle. annullaLaCorsa non scrive nulla dopo l'attesa, quindi non ha
    # niente da contraddire; ha un nome apposta per poter comparire qui invece
    # di non essere mai incontrata.
    senza_ordine = {"caricaStato", "annullaLaCorsa", "caricaGalleria"}
    tratte = [
        (nome, _sorgente_di(nome, testo))
        for nome in re.findall(r"^async function (\w+)\(", testo, re.MULTILINE)
        if nome not in senza_ordine
    ]
    tratte += [("una funzione freccia asincrona", corpo) for corpo in _corpi_freccia_asincroni(testo)]
    interrogano = 0
    for nome, sorgente in tratte:
        if "await fetch(" not in sorgente:
            continue
        interrogano += 1
        assert "superata(" in sorgente, f"{nome} scrive senza guardare l'ordine:\n{sorgente}"
    # Senza questo, cancellare le funzioni farebbe passare il test a vuoto. Ed
    # e' anche l'unica rete che resta quando l'estrazione per graffe fallisce
    # (vedi il tetto di _corpi_freccia_asincroni): le tratte reali sono 5
    # nominate (mostraNuvolaDelloStep, mostraStep, scriviParametro,
    # apriDettaglio, mostraEsperimento) piu' 2 freccia, quindi la soglia
    # pareggia il numero vero. Se ne aggiungi una, alza la soglia invece di
    # lasciarla indietro.
    assert interrogano >= 7, "le tratte attese sono sparite dal modulo"


def test_due_geometrie_in_volo_nella_stessa_generazione_non_si_arbitrano_per_arrivo():
    """Il ricaricamento dal fronte di discesa non apre una generazione — aprirla
    butterebbe via il clic che l'utente ha appena fatto — quindi porta lo stesso
    ordine di una risposta partita prima, e con un contatore solo `superata()`
    non puo' dire quale delle due vince: vince chi arriva ultimo.

    Ingresso concreto: step 9 aperto, «Esegui questo step», e riclic sullo step
    9 mentre gira. Se la risposta del clic — che porta il contorno vecchio —
    arriva per ultima, il viewport torna indietro. E' IM-4 per un'altra strada.

    Sono due requisiti diversi e servono due contatori: la generazione ordina i
    clic, la richiesta di geometria ordina le geometrie. La regola resta
    `superata`, che e' pura e ha gia' il suo test eseguito: qui si sorveglia che
    ogni strada apra esattamente una richiesta e la guardi prima di scrivere.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    for nome in ("mostraNuvolaDelloStep", "mostraStep"):
        sorgente = _sorgente_di(nome, testo)
        assert sorgente.count("apriGeometria()") == 1, f"{nome} non apre una richiesta sola"
        assert "superata(emissione, ultimaGeometria)" in sorgente, (
            f"{nome} scrive senza guardare se una geometria piu' nuova e' gia' partita"
        )
    # La delega di mostraStep sta prima del contatore: se stesse dopo, la strada
    # della nuvola aprirebbe due richieste e batterebbe se stessa, e nessuna
    # nuvola verrebbe piu' disegnata.
    mostra = _sorgente_di("mostraStep", testo)
    assert mostra.index("mostraNuvolaDelloStep(numero") < mostra.index("apriGeometria()"), mostra
    # E il cursore del taglio si rifa' solo se questa risposta ha scritto: sulla
    # geometria di qualcun altro sarebbe una taratura che nessuna lettura regge.
    ricarica = _sorgente_di("ricaricaVista", testo)
    assert re.search(r"if \(disegnato && !superata\(ordine\)\)", ricarica), ricarica


# Il banco che esegue l'arbitraggio invece di guardarlo. Lo stub finisce qui:
# sotto ci vanno le funzioni vere di app.js, e il caso da riprodurre.
# `generazione` e `ultimaGeometria` sono dichiarate qui perche' in app.js sono
# variabili di modulo e non funzioni: e' la sola parte di stato che il banco
# rifa'. STEP_CON_MESH tiene il solo step 9: __NUMERO__ decide se il caso cade
# dentro (tratta della mesh) o fuori (tratta della nuvola) — e' il medesimo
# banco per tutte e due le tratte, non due banchi.
_BANCO_ORDINE = """import assert from 'node:assert/strict';

let generazione = 1;
let ultimaGeometria = 0;
const STEP_CON_MESH = new Set([9]);
const scritture = [];
const vista = {
  svuota() {},
  mostraNuvola(vertici) { scritture.push(`nuvola:${vertici.length / 3}`); },
  mostraMesh(vertici) { scritture.push(`mesh:${vertici.length / 3}`); },
};
const document = { getElementById: () => ({ textContent: '' }) };
function riallineaTaglio(numero) { scritture.push(`riallinea:${numero}`); }

// Ogni richiesta resta sospesa finche' il banco non la sblocca: l'ordine di
// arrivo e' l'ingresso della prova, non un caso.
const sospese = [];
let partite = 0;
globalThis.fetch = () => {
  const marcatore = ++partite;
  return new Promise((risolvi) => sospese.push(() => risolvi({
    ok: true,
    // Il marcatore viaggia come numero di vertici (tratta della mesh) o come
    // un terzo del numero di numeri in virgola mobile (tratta della nuvola,
    // che legge il buffer intero): sull'una o sull'altra tratta la scrittura
    // nel viewport dice comunque quale delle due geometrie l'ha fatta.
    headers: { get: (nome) => (nome === 'X-Vertices' ? marcatore : 0) },
    arrayBuffer: async () => new ArrayBuffer(marcatore * 12),
  })));
};
const giro = async () => { for (let i = 0; i < 8; i += 1) await Promise.resolve(); };

__FUNZIONI__

// Step __NUMERO__ aperto, «Esegui questo step», riclic sullo stesso step
// mentre gira.
ricaricaVista(__NUMERO__, generazione);   // il clic: apre la richiesta 1
await giro();
ricaricaVista(__NUMERO__);                // il fronte di discesa: stessa generazione, richiesta 2
await giro();
assert.equal(sospese.length, 2, 'le due richieste non sono partite');
sospese[1]();                    // il contorno nuovo arriva per primo
await giro();
sospese[0]();                    // la risposta del clic, col contorno vecchio, arriva per ultima
await giro();

assert.deepEqual(scritture, [__ATTESO__],
  'scritture nel viewport: ' + JSON.stringify(scritture));
"""


@pytest.mark.parametrize(
    ("numero", "atteso"),
    [
        # 9 sta in STEP_CON_MESH del banco: mostraStep gira la tratta della
        # mesh davvero, senza delegare.
        pytest.param(9, "'mesh:2', 'riallinea:9'", id="mesh"),
        # 2 non sta in STEP_CON_MESH del banco: mostraStep delega subito a
        # mostraNuvolaDelloStep, che e' la tratta che il giro 2 non eseguiva
        # mai — il suo banco usava solo lo step 9.
        pytest.param(2, "'nuvola:2', 'riallinea:2'", id="nuvola"),
    ],
)
def test_fra_due_geometrie_della_stessa_generazione_vince_chi_e_partita_dopo(numero, atteso):
    """IMP-1. L'arbitraggio **eseguito**, non letto, su tutte e due le tratte.

    I tre asserti testuali del test qui sopra guardano la forma — una
    `apriGeometria()` per strada, la guardia presente, la delega prima del
    contatore — e restano tutti e tre veri se `const emissione =
    apriGeometria();` si sposta **dopo** la `fetch`, in una tratta o
    nell'altra: `mostraStep` e `mostraNuvolaDelloStep` hanno la stessa forma.
    Ma spostata li' l'emissione smette di essere il numero di **partenza** e
    diventa quello di **arrivo**, cioe' esattamente cio' che il secondo
    contatore doveva togliere di mezzo: le due risposte tornano ad arbitrarsi
    per arrivo e il contorno vecchio si riposa sopra quello nuovo.

    Un banco che esercitasse solo lo step 9 proverebbe solo `mostraStep`:
    lo spostamento nell'altra funzione passerebbe intatto con la suite
    intera verde, perche' nessuna riga eseguirebbe mai
    `mostraNuvolaDelloStep`. Da qui il parametro: stesso banco, uno step
    dentro `STEP_CON_MESH` e uno fuori.

    Qui le funzioni vere girano davvero, sopra una quarantina di righe di stub
    e senza nessun motore di DOM, ed e' lo stesso idioma di
    `test_una_risposta_superata_si_scarta_e_una_corrente_no` e
    `test_l_ingombro_non_conta_il_box_di_ritaglio`. Con quello spostamento, sulla
    tratta toccata, il banco stampa due scritture in piu': la geometria vecchia
    scrive per seconda e il cursore del taglio si rifa' due volte.
    """
    from meshrec.app.server import UI_DIR

    node = shutil.which("node")
    if node is None:
        pytest.skip("node non installato: l'arbitraggio resta verificato a mano")
    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    funzioni = "\n".join(
        _sorgente_di(nome, testo)
        for nome in (
            "superata",
            "apriGeometria",
            "didascaliaDellaVista",
            "mostraNuvolaDelloStep",
            "mostraStep",
            "ricaricaVista",
        )
    )
    banco = (
        _BANCO_ORDINE.replace("__FUNZIONI__", funzioni)
        .replace("__NUMERO__", str(numero))
        .replace("__ATTESO__", atteso)
    )
    # Nome per step: due prove dello stesso modulo, in parallelo con -n, non
    # devono scriversi addosso lo stesso file .mjs.
    prova = Path(__file__).parent / f"_prova_arbitraggio_{numero}.mjs"
    prova.write_text(banco, encoding="utf-8")
    try:
        esito = subprocess.run([node, str(prova)], capture_output=True, text=True)
        assert esito.returncode == 0, esito.stderr
    finally:
        prova.unlink()


def test_svuota_libera_i_buffer_e_non_tocca_i_piani_di_taglio():
    """I-5. gruppo.clear() toglie dalla scena e non libera: senza dispose ogni
    passaggio fra step lascia i suoi buffer sulla scheda. E i piani di taglio
    non sono una risorsa da liberare: sono condivisi apposta perche'
    sopravvivano alla geometria (Task 13), e azzerarli qui farebbe nascere la
    geometria nuova senza taglio mentre il comando lo dichiara attivo."""
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "viewport.js").read_text(encoding="utf-8")
    corpo = testo.split("svuota() {", 1)[1].split("\n    },", 1)[0]
    assert "geometry?.dispose()" in corpo
    assert "material?.dispose()" in corpo
    righe = [r for r in corpo.splitlines() if not r.strip().startswith("//")]
    assert not any("pianiTaglio" in r for r in righe), "svuota() tocca i piani di taglio"


def test_l_ingombro_non_conta_il_box_di_ritaglio():
    """I-1. Il Box3Helper sta dentro `gruppo` perche' svuota() lo liberi con gli
    altri, ma `gruppo` e' anche cio' che `ingombro()` e `inquadra()` misurano.
    Contandolo, `ingombro()` smette di restituire l'ingombro della geometria e
    restituisce l'unione con un rettangolo che l'utente allarga a piacere: il
    Task 13 ci tara l'intervallo del cursore del taglio, e `pannelloRitaglio`
    ci riprecompila i sei campi, allargandosi a ogni giro senza tornare
    indietro.

    Eseguito, non letto: `box.visible = false` — la correzione piu' corta che
    la revisione suggeriva — qui si vedrebbe passare, perche'
    `Box3.expandByObject` non guarda `visible` (vendor/three.core.js:9730). La
    funzione vera del viewport gira sopra il three.js vendorizzato, che e' lo
    stesso che il browser riceve.
    """
    from meshrec.app.server import UI_DIR

    node = shutil.which("node")
    if node is None:
        pytest.skip("node non installato: l'ingombro resta verificato a mano")
    testo = (UI_DIR / "viewport.js").read_text(encoding="utf-8")
    # scatolaDelGruppo sta dentro creaViewport, quindi non chiude in prima
    # colonna: si taglia sulla graffa al suo livello di rientro.
    sorgente = "function scatolaDelGruppo" + testo.split("function scatolaDelGruppo", 1)[1].split(
        "\n  }\n", 1
    )[0] + "\n  }"
    prova = Path(__file__).parent / "_prova_ingombro.mjs"
    prova.write_text(
        f"import * as THREE from {(UI_DIR / 'vendor' / 'three.core.js').as_uri()!r};\n"
        "import assert from 'node:assert/strict';\n"
        "const gruppo = new THREE.Group();\n"
        "const box = new THREE.Box3Helper(new THREE.Box3(), new THREE.Color(0xc4671b));\n"
        "box.box.set(new THREE.Vector3(-1000, -1000, -1000), new THREE.Vector3(1000, 1000, 1000));\n"
        "function punti(coordinate) {\n"
        "  const geometria = new THREE.BufferGeometry();\n"
        "  geometria.setAttribute('position',"
        " new THREE.BufferAttribute(new Float32Array(coordinate), 3));\n"
        "  return new THREE.Points(geometria, new THREE.PointsMaterial());\n"
        "}\n"
        "gruppo.add(punti([0, 0, 0, 10, 20, 30]));\n"
        + sorgente + "\n"
        "const solaNuvola = scatolaDelGruppo();\n"
        "assert.deepEqual(solaNuvola.min.toArray(), [0, 0, 0]);\n"
        "assert.deepEqual(solaNuvola.max.toArray(), [10, 20, 30]);\n"
        # Il box entra nel gruppo e viene reso: e' dopo un fotogramma che
        # Box3Helper.updateMatrixWorld scrive position e scale dal proprio box,
        # ed e' quello che setFromObject leggerebbe.
        "gruppo.add(box);\n"
        "box.updateMatrixWorld(true);\n"
        "const conIlBox = scatolaDelGruppo();\n"
        "assert.deepEqual(conIlBox.min.toArray(), solaNuvola.min.toArray(),"
        " 'il box di ritaglio e entrato nell ingombro');\n"
        "assert.deepEqual(conIlBox.max.toArray(), solaNuvola.max.toArray(),"
        " 'il box di ritaglio e entrato nell ingombro');\n"
        # E cambia quando cambia la geometria: senza questo, un ingombro
        # sempre vuoto passerebbe gli asserti qui sopra.
        "gruppo.add(punti([-5, -5, -5]));\n"
        "assert.deepEqual(scatolaDelGruppo().min.toArray(), [-5, -5, -5],"
        " 'l ingombro non segue piu la geometria');\n",
        encoding="utf-8",
    )
    try:
        esito = subprocess.run([node, str(prova)], capture_output=True, text=True)
        assert esito.returncode == 0, esito.stderr
    finally:
        prova.unlink()


def test_un_campo_del_ritaglio_lasciato_vuoto_non_muove_il_box():
    """M-1. `Number("")` e' 0, non NaN: cancellare il contenuto di «min x»
    portava quell'estremo a zero, il box saltava all'origine e «Applica il
    ritaglio» mandava 0 al server, che lo accettava. Nessun messaggio, e il
    numero che tornava era quello di un box che nessuno aveva disegnato.
    """
    from meshrec.app.server import UI_DIR

    sorgente = _sorgente_di("pannelloRitaglio", (UI_DIR / "app.js").read_text(encoding="utf-8"))
    assert "Number.isFinite" in sorgente, "un campo vuoto o a meta' muove ancora il box"
    assert not re.search(r"valori\[estremo\]\[asse\]\s*=\s*Number\(", sorgente), sorgente


def test_la_riga_d_errore_resta_nell_albero_anche_da_vuota():
    """M-3. La meta' funzionale di R75 vive in una regola di stile.css, file che
    nessun test sorvegliava: se una riscrittura del sistema visivo la perdesse,
    R75 regredirebbe in silenzio e la suite resterebbe verde.

    La regola deve esserci e non deve essere `display: none`: nascondere cosi'
    la regione `role="alert"` la toglie dall'albero di accessibilita', che e'
    esattamente il difetto che R75 chiedeva di chiudere. A contenuto vuoto il
    paragrafo non genera line box e ha altezza zero da solo: alla regola serve
    azzerare il margine, non toglierlo dal flusso.
    """
    from meshrec.app.server import UI_DIR

    foglio = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    assert re.search(r"\.errore:empty\s*\{", foglio), "la regola .errore:empty e' sparita da stile.css"
    regola = foglio.split(".errore:empty", 1)[1].split("}", 1)[0]
    assert "display" not in regola, f"display toglie la regione role=alert dall'albero: {regola}"
    # E nessun ramo del modulo la rimette dietro hidden, che e' la strada per
    # cui il difetto era arrivato la prima volta.
    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"rigaErrore\.hidden", testo), "un ramo nasconde di nuovo la riga d'errore"


def test_l_intervallo_del_cursore_di_taglio_esce_da_una_lettura_e_non_da_numeri_scritti():
    """Il cursore del taglio mostra una quota in millimetri: se i suoi estremi
    fossero scritti nel codice sarebbe una cifra che nessuna lettura sostiene, e
    sul muro di riferimento (2470,99 x 231,00 x 1697,00 mm) sarebbe sbagliata
    per due assi su tre. min, max e step devono venire dall'ingombro della
    geometria disegnata, che il viewport misura.

    MI-1 della revisione: la scansione e' testuale e vede solo il corpo di
    riallineaTaglio, quindi copre la cifra scritta accanto all'assegnamento e
    la costante scritta a mano dentro il corpo, che e' il modo naturale in cui
    un numero rientra dopo essere stato tolto. Non copre, e non puo' coprire
    senza interpretare il modulo, un `const QUOTA_MINIMA = 0` dichiarato fuori
    dalla funzione: quello lo prenderebbe solo un test che esegue il codice, e
    l'interfaccia non ha un motore JS sotto test.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    corpo = testo.split("function riallineaTaglio", 1)[1].split("\n}\n", 1)[0]
    assert "vista.ingombro()" in corpo
    for riga in corpo.splitlines():
        assegnamento = re.search(r"quotaTaglio\.(min|max|step|value)\s*=\s*(.+)", riga)
        if assegnamento:
            assert not re.match(r"-?\d", assegnamento.group(2)), riga
    # Nemmeno dietro un nome: un `const QUOTA_MINIMA = 0;` dichiarato nel corpo
    # e usato due righe sotto passerebbe intatto dalla scansione qui sopra.
    assert not re.search(r"\b(?:const|let|var)\s+\w+\s*=\s*-?\d", corpo), corpo

    # Nemmeno nel markup: scritti li' non li vedrebbe nessun test sul codice.
    pagina = (UI_DIR / "index.html").read_text(encoding="utf-8")
    cursore = pagina.split('id="taglio-quota"', 1)[0].rsplit("<input", 1)[1]
    for attributo in ("min", "max", "step", "value"):
        assert f"{attributo}=" not in cursore, cursore


def test_il_cursore_del_taglio_ha_una_posizione_spenta_e_ci_parte():
    """IM-2. `disattivaTaglio()` esisteva nel viewport e l'interfaccia non la
    raggiungeva: `riallineaTaglio` chiamava `applicaTaglio()` sempre, il taglio
    si accendeva da solo appena il comando compariva e l'unico modo di
    spegnerlo era uscire dallo step. Il primo scatto del cursore e' la
    posizione spenta, ed e' quella da cui si parte: il volume compare intero e
    ci si torna trascinando a sinistra, senza lasciare lo step.

    Spenta e non «un taglio che non toglie niente» (IM-3): alla quota del
    minimo il piano sarebbe complanare alla faccia estrema, e three.js tiene i
    punti con normale . punto + costante > 0. Cosi' invece nessuna quota
    tagliata e' complanare, perche' la prima vale minimo + passo.

    Tutto testuale: il resto e' `quota <= minimo`, un confronto, e una funzione
    pura che lo avvolge proverebbe il segno di minore, non il comportamento.
    Quello resta da guardare a video, e il rapporto dice come.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    applica = _sorgente_di("applicaTaglio", testo)
    assert "vista.disattivaTaglio()" in applica, "il cursore non puo' spegnere il taglio"
    # Spento e' una posizione del cursore, non un caso a parte: il confronto e'
    # con il minimo del cursore stesso, cosi' vale su ogni asse e ogni geometria.
    assert re.search(r"quotaTaglio\.min\b", applica), applica
    riallinea = _sorgente_di("riallineaTaglio", testo)
    # E si parte da li': min e value sono lo stesso estremo dell'ingombro.
    assert re.search(r"quotaTaglio\.min\s*=\s*minimo\b", riallinea), riallinea
    assert re.search(r"quotaTaglio\.value\s*=\s*minimo\b", riallinea), riallinea


def test_il_fronte_di_discesa_ricarica_anche_la_vista_e_non_solo_il_pannello():
    """IM-4. Si rieseguiva lo step aperto e il pannello mostrava le metriche
    nuove mentre il viewport teneva il contorno vecchio, col cursore del taglio
    tarato su un ingombro che non esisteva piu'. Le due avvertenze del giro 2
    valgono anche qui: il ricaricamento non apre una generazione (prende quella
    in corso, cosi' un clic dell'utente lo batte) e non chiede niente se cio'
    che e' disegnato non puo' essere stato riscritto.
    """
    from meshrec.app.server import UI_DIR

    testo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    corpo = testo.split('addEventListener("stato"', 1)[1].split("\n});", 1)[0]
    assert "apriDettaglio(stepAperto)" in corpo
    assert "ricaricaVista(stepMostrato)" in corpo, "la vista resta indietro sul fronte di discesa"
    assert "stepMostrato >= stato.step" in corpo, "chiede anche cio' che nessuna corsa ha toccato"
    assert "apriGenerazione" not in corpo, "il fronte di discesa annulla una geometria in volo"
    # Lo stesso punto serve il clic: se il clic smettesse di passarci, il
    # riallineamento del cursore resterebbe scritto per un solo chiamante.
    # Il solo corpo del gestore: fino alla graffa che lo chiude. Sul resto del
    # file la ricerca troverebbe la definizione di ricaricaVista, che sta piu'
    # sotto, e passerebbe anche con un clic che non ci passa piu'.
    gestore = testo.split('getElementById("elenco-step").addEventListener', 1)[1]
    gestore = gestore.split("\n});", 1)[0]
    assert re.search(r"ricaricaVista\(numero[,)]", gestore), gestore


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


def test_lo_schema_non_esplode_sul_blocco_selettori(cliente):
    """`selettori` (STEP_BLOCKS[11]) e' un `dict[NomeSet, Selettore]`, non un
    modello: non ha `model_fields` come `carichi` (un `BaseModel`), e prima
    della guardia lo endpoint lo tratta comunque cosi' e va in 400.

    Due mutazioni, due modi di fallire:

    1. togliere la guardia su `hasattr(annidato, "model_fields")` in
       `schema()` (core/app/server.py) e tornare a chiamare
       `annidato.model_fields` incondizionatamente -- l'AttributeError torna
       e la richiesta a `/api/schema` torna a rispondere 400.
    2. far rendere alla guardia un valore diverso da `{}` (per esempio
       `campi[blocco] = None`) -- resterebbe 200, e senza l'asserzione sul
       valore il test non se ne accorgerebbe.
    """
    risposta = cliente.get("/api/schema")
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["11"]["blocchi"] == ["tet", "analysis", "carichi", "selettori"]
    assert corpo["11"]["campi"]["selettori"] == {}


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


def test_la_cache_del_contorno_non_sfratta_quella_della_nuvola(cliente, tmp_path):
    """Le due cache condividono il marchio, e la pulizia cancella per marchio.

    Il marchio e' l'hash del solo percorso della sorgente, e
    viewport._rimuovi_voci_vecchie elimina ogni altra voce che lo porta. Nella
    stessa cartella, la nuvola e il contorno di uno stesso file si
    sfratterebbero a vicenda ad ogni scrittura, e il ricalcolo tornerebbe senza
    alcun segnale. Oggi non accade perche' read_cloud rifiuta un .vtu, cioe'
    per una ragione che sta in un altro modulo: questo test sorveglia la
    separazione, non quella ragione.
    """
    import numpy as np

    from meshrec.core import viewport

    sorgente = tmp_path / "corsa" / "09_volume.vtu"
    sorgente.parent.mkdir(parents=True, exist_ok=True)
    sorgente.write_bytes(b"non conta il contenuto: contano i nomi delle voci")

    voce_nuvola = viewport._cache_path(sorgente, 400_000, 20_000, 0, server.CACHE_DIR)
    voce_nuvola.parent.mkdir(parents=True, exist_ok=True)
    voce_nuvola.write_bytes(b"voce finta della nuvola")

    voce_contorno = server._percorso_contorno(sorgente)
    server._scrivi_contorno(
        voce_contorno,
        np.zeros((1, 3), dtype="<f4"),
        np.zeros((1, 3), dtype="<u4"),
        np.zeros((1,), dtype="<u4"),
    )
    viewport._rimuovi_voci_vecchie(voce_contorno.parent, voce_contorno)

    assert voce_contorno.exists()
    assert voce_nuvola.exists(), "scrivere il contorno ha cancellato la voce della nuvola"


def _nuvola_con_isolati(seme: int = 0):
    """Un ammasso denso piu' qualche punto isolato: remove_outliers ne toglie
    davvero, quindi la sua presenza o assenza si vede nel conteggio."""
    import numpy as np

    generatore = np.random.default_rng(seme)
    denso = generatore.random((5_000, 3)) * 20.0
    isolati = generatore.random((50, 3)) * 100.0
    return np.vstack([denso, isolati])


def test_l_anteprima_toglie_gli_outlier_prima_di_ritagliare_come_lo_step_2(cliente, tmp_path):
    """B-2. L'ordine e' quello dello step 2: remove_outliers e poi crop_box
    (core/segment.py:142-143). Il secondo asserto e' quello che morde: con un
    box che contiene tutto, saltare la pulizia darebbe il totale del file, cioe'
    un numero piu' alto di quello che lo step 2 produrrebbe."""
    from meshrec.core import io, pipeline, segment
    from meshrec.core.config import SegmentConfig

    punti = _nuvola_con_isolati()
    io.write_cloud(tmp_path / "corsa" / pipeline.ARTIFACTS[1], punti)

    tutto = {"min": [-1.0, -1.0, -1.0], "max": [101.0, 101.0, 101.0]}
    risposta = cliente.post("/api/crop", json=tutto)
    assert risposta.status_code == 200
    dal_server = risposta.json()["points_after"]

    puliti, _metriche = segment.remove_outliers(punti, SegmentConfig())
    assert dal_server == len(puliti)
    assert dal_server < len(punti), "l'anteprima non ha tolto nessun outlier: e' la nuvola grezza"


@pytest.mark.parametrize("metodo", ["crop", "auto"])
def test_l_anteprima_del_ritaglio_dice_esattamente_che_numero_e(cliente, tmp_path, metodo):
    """B-2 e BL-1. Il numero dell'anteprima, confrontato con lo step 2 eseguito.

    Il confronto «endpoint contro metrics.json» del primo giro era una
    tautologia: l'endpoint ritagliava 02_segmented.ply, cioe' l'uscita gia'
    ritagliata dello step 2, e ogni punto di quel file sta dentro il box che
    l'ha prodotto per costruzione. Qui il box chiesto all'anteprima e' piu'
    largo di quello che ha prodotto 02_segmented.ply: leggere l'uscita non puo'
    far tornare indietro i punti che quel file non contiene, quindi i due
    numeri divergono e il test lo dice.

    Lo step 2 viene eseguito davvero, non simulato: e' l'unico modo che il
    confronto ha di non essere un'altra tautologia.

    Parametrizzato su **tutti** i valori di `segment.method`, che e' un campo
    dello stesso pannello dell'anteprima: con `auto` lo step 2 prosegue dopo il
    ritaglio (extract_planes, cluster, `groups[cluster_index]`) e riscrive
    points_after, mentre l'anteprima si ferma al ritaglio. Fino al giro 2 la
    didascalia affermava lo stesso la coincidenza, e il test girava solo sul
    predefinito `crop`, quindi non poteva vederlo. La coincidenza si pretende
    dove esiste; dove non esiste si pretende che `completo` la neghi, e che i
    due numeri **divergano davvero** — senza quest'ultimo asserto una
    dichiarazione di incompletezza sarebbe verde anche su un'anteprima esatta,
    cioe' non direbbe niente.
    """
    from meshrec.core import io, pipeline
    from meshrec.core.config import RunConfig, load_config

    io.write_cloud(tmp_path / "corsa" / pipeline.ARTIFACTS[1], _nuvola_con_isolati())

    def esegui_lo_step_2(cfg) -> int:
        # from_step e to_step si assegnano insieme, con una sola validazione
        # dell'oggetto intero: e' quello che RunConfig documenta.
        cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), "from_step": 2, "to_step": 2})
        return pipeline.run(cfg)["02_segment"]["points_after"]

    # Il metodo entra nella configurazione della corsa prima della richiesta:
    # e' da li' che l'endpoint lo legge, come lo leggerebbe dal pannello.
    scelta = load_config(tmp_path / "config.yaml")
    scelta.segment.method = metodo
    save_config(scelta, tmp_path / "config.yaml")

    # Il box stretto passa sempre da `crop`: serve solo a provare che il box
    # largo e' piu' largo, cioe' che l'anteprima non sta leggendo un artefatto
    # gia' ritagliato. Farlo con `auto` misurerebbe un cluster e non un box.
    stretto = load_config(tmp_path / "config.yaml")
    stretto.segment.method = "crop"
    stretto.segment.crop_min, stretto.segment.crop_max = (0.0, 0.0, 0.0), (10.0, 10.0, 10.0)
    dallo_stretto = esegui_lo_step_2(stretto)

    largo = {"min": [0.0, 0.0, 0.0], "max": [20.0, 20.0, 20.0]}
    risposta = cliente.post("/api/crop", json=largo)
    assert risposta.status_code == 200
    corpo = risposta.json()
    anteprima = corpo["points_after"]
    assert anteprima > dallo_stretto, "il box largo non e' piu' largo: il confronto non morderebbe"

    # /api/crop ha scritto crop_min e crop_max: lo step 2 li rilegge da li',
    # quindi i due lati stanno guardando davvero lo stesso box.
    davvero = esegui_lo_step_2(load_config(tmp_path / "config.yaml"))
    if metodo == "crop":
        assert corpo["completo"] is True
        assert anteprima == davvero
    else:
        assert corpo["completo"] is False, (
            f"l'anteprima si dichiara completa con method={metodo}, "
            f"ma dice {anteprima} dove lo step 2 ne tiene {davvero}"
        )
        assert anteprima != davvero, (
            "l'anteprima coincide con lo step 2 anche con method=auto: "
            "allora la dichiarazione di incompletezza non e' provata da nulla"
        )


def test_un_box_vuoto_non_solleva_ma_lo_dice(cliente, tmp_path):
    """La nuvola va scritta davvero, altrimenti il test passa per la ragione
    sbagliata: senza artefatto la richiesta muore su io.read_cloud e il 400
    arriva da li', anche se il ramo del box vuoto non esistesse. Con la nuvola
    sul posto il rifiuto puo' venire solo da crop_box, e il suo messaggio deve
    arrivare intero fino al browser: e' quello che dice dove guardare.
    """
    from meshrec.core import io, pipeline

    io.write_cloud(tmp_path / "corsa" / pipeline.ARTIFACTS[1], _nuvola_con_isolati())
    risposta = cliente.post("/api/crop", json={"min": [1e9, 1e9, 1e9], "max": [2e9, 2e9, 2e9]})
    assert risposta.status_code == 400
    corpo = risposta.json()
    assert "errore" in corpo
    assert "nelle unita di lavoro (mm)" in corpo["messaggio"]


# Arita' sbagliata, valore non numerico, NaN e chiave mancante: le forme che
# l'endpoint accettava o rifiutava male. L'arita' 1 e' quella che passava del
# tutto, perche' numpy trasmette (N,3) >= (1,) senza lamentarsi.
# I corpi sono JSON grezzo e non dizionari: NaN non e' JSON valido e nessun
# codificatore di Python lo scrive senza forzatura, ma json.loads lo legge, e
# quindi lato server arriva come un float. E' il caso che l'interfaccia non
# produce e che un altro cliente puo' produrre: il confine deve reggerlo.
@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ('{"min": [10.0], "max": [60.0, 60.0, 60.0]}', "min"),
        ('{"min": [10.0, 10.0, 10.0], "max": [60.0, 60.0, 60.0, 60.0]}', "max"),
        ('{"min": [10.0, 10.0, "non un numero"], "max": [60.0, 60.0, 60.0]}', "min"),
        ('{"min": [NaN, 10.0, 10.0], "max": [60.0, 60.0, 60.0]}', "min"),
        ('{"min": [Infinity, 10.0, 10.0], "max": [60.0, 60.0, 60.0]}', "min"),
        ('{"min": [10.0, 10.0, 10.0]}', "max"),
        # MIN-1: bool e' sottotipo di int, quindi senza il controllo davanti
        # pydantic scriveva (1.0, 0.0, 1.0) in configurazione e rispondeva 200.
        ('{"min": [true, false, true], "max": [60.0, 60.0, 60.0]}', "min"),
    ],
)
def test_un_box_malformato_e_rifiutato_e_non_tocca_la_configurazione(cliente, tmp_path, corpo, campo):
    """B-1. Il rifiuto non basta: quello che rendeva il difetto permanente era
    la scrittura. `{"min":[10.0],"max":[60.0]}` rispondeva 200 e lasciava sul
    disco una tupla di uno in un campo dichiarato di tre; da li' in poi
    load_config rifiutava, e /api/config, /api/run e /api/crop stessa
    rispondevano 400 finche' qualcuno non riapriva config.yaml a mano.

    La nuvola va scritta davvero, altrimenti il test passa per la ragione
    sbagliata: senza artefatto la richiesta morirebbe comunque prima di
    scrivere, e passerebbe anche senza nessuna validazione al confine.

    Il confronto e' sui byte del file e non sul codice di stato: e' il file che
    governa la corsa, ed e' l'unica cosa che dice se la scrittura c'e' stata.
    """
    from meshrec.core import io, pipeline

    io.write_cloud(tmp_path / "corsa" / pipeline.ARTIFACTS[1], _nuvola_con_isolati())
    prima = (tmp_path / "config.yaml").read_bytes()

    risposta = cliente.post(
        "/api/crop", content=corpo, headers={"content-type": "application/json"}
    )
    assert risposta.status_code != 200, risposta.text
    assert campo in risposta.text, f"il rifiuto non dice quale campo: {risposta.text}"
    assert (tmp_path / "config.yaml").read_bytes() == prima, "il box rifiutato ha scritto lo stesso"
    # E la corsa resta leggibile: e' la conseguenza che rendeva il difetto
    # permanente invece che transitorio.
    assert cliente.get("/api/config").status_code == 200


# --------------------------------------------------------------------------
# Task 14: galleria di curazione. Due endpoint in sola lettura sui registri
# della Fase 2 (core.sweep.load_registry), colonne riusate da
# core.report._COLUMNS / core.report._cell.
# --------------------------------------------------------------------------


def test_la_galleria_elenca_gli_esperimenti_esistenti(cliente, tmp_path):
    registro = tmp_path / "experiments" / "prova" / "registro.jsonl"
    registro.parent.mkdir(parents=True)
    registro.write_text(
        json.dumps({"fingerprint": "abc", "axes": {}, "outcome": "riuscito", "on_front": True})
        + "\n",
        encoding="utf-8",
    )
    elenco = cliente.get("/api/experiments").json()
    assert "prova" in elenco["esperimenti"]
    corpo = cliente.get("/api/experiments/prova").json()
    assert corpo["righe"][0]["on_front"] is True
    # Le colonne sono quelle di report._COLUMNS, non un elenco scelto qui:
    # se un giorno divergono, questo campo lo dice.
    from meshrec.core import report as report_modulo

    assert [voce["chiave"] for voce in corpo["colonne"]] == [chiave for chiave, _ in report_modulo._COLUMNS]
    assert len(corpo["celle"]) == 1
    assert len(corpo["celle"][0]) == len(report_modulo._COLUMNS)


def test_una_sottocartella_senza_registro_non_e_un_esperimento(cliente, tmp_path):
    """Una cartella d'esperimento a meta' (nessun registro ancora scritto) non
    e' un esperimento concluso: comparirebbe in elenco e /api/experiments/{nome}
    risponderebbe con un registro vuoto, che sembra un esperimento senza
    candidati invece di uno mai partito."""
    (tmp_path / "experiments" / "a_meta").mkdir(parents=True)
    elenco = cliente.get("/api/experiments").json()
    assert elenco["esperimenti"] == []


def test_un_esperimento_inesistente_risponde_quattrocento(cliente, tmp_path):
    (tmp_path / "experiments").mkdir()
    risposta = cliente.get("/api/experiments/non-esiste")
    assert risposta.status_code == 400
    assert "non-esiste" in risposta.json()["messaggio"]


def test_la_galleria_non_scrive_mai_nei_registri(cliente, tmp_path):
    """Le corse di riferimento e i registri della Fase 2 sono di sola lettura.

    Il piano guarda un file solo dopo una chiamata sola; qui la difesa vale
    su TUTTE le tratte /api/experiments* (scoperte dalle rotte dell'app, non
    elencate a mano: un endpoint aggiunto domani con questo prefisso ci
    entra da solo) e sul contenuto dell'intera cartella experiments/, non di
    un file scelto in anticipo.
    """
    radice_esperimenti = tmp_path / "experiments"
    for nome in ("prova", "seconda"):
        cartella = radice_esperimenti / nome
        cartella.mkdir(parents=True)
        (cartella / "registro.jsonl").write_text(
            json.dumps({"fingerprint": nome, "axes": {}, "outcome": "riuscito", "on_front": True})
            + "\n",
            encoding="utf-8",
        )
        # Un secondo file, non registro.jsonl: la difesa deve valere sulla
        # cartella intera, non sul solo file che gli endpoint leggono oggi.
        (cartella / "esperimento.yaml").write_text(f"nome: {nome}\n", encoding="utf-8")

    def istantanea() -> dict[str, bytes]:
        return {
            str(percorso.relative_to(radice_esperimenti)): percorso.read_bytes()
            for percorso in sorted(radice_esperimenti.rglob("*"))
            if percorso.is_file()
        }

    prima = istantanea()

    tratte_galleria = [
        rotta for rotta in cliente.app.routes
        if getattr(rotta, "path", "").startswith("/api/experiments")
    ]
    # Se domani sparisse /api/experiments/{nome} o l'intero prefisso non
    # comparisse piu' fra le rotte, questo test non proverebbe piu' niente
    # in silenzio: qui si accorge e si ferma.
    assert len(tratte_galleria) >= 2, "le rotte della galleria non si trovano piu' in app.routes"

    for rotta in tratte_galleria:
        bersaglio = re.sub(r"\{[^}]+\}", "prova", rotta.path)
        for metodo in rotta.methods:
            if metodo == "HEAD":
                continue
            cliente.request(metodo, bersaglio)

    assert istantanea() == prima, "la galleria ha scritto o cancellato qualcosa in experiments/"


def test_la_galleria_mostra_il_candidato_di_fronte_su_lab_crop():
    """Verifica sul dato vero, non su tmp_path: i quattro valori vengono da
    meshrec/docs/fase-2-sweep.md, paragrafo 3, riga del fronte
    (surface.poisson_depth = 7). Il client punta a lab.yaml e experiments/
    reali del repository: la tratta e' GET, quindi non scrive su nessuno dei due.
    """
    radice_repo = Path(__file__).resolve().parents[1]
    cliente_reale = TestClient(create_app(radice_repo / "lab.yaml"), raise_server_exceptions=False)
    corpo = cliente_reale.get("/api/experiments/lab_crop").json()
    indice_colonne = {voce["chiave"]: i for i, voce in enumerate(corpo["colonne"])}
    fronte = [i for i, riga in enumerate(corpo["righe"]) if riga.get("on_front")]
    assert len(fronte) == 1, f"atteso un solo candidato di fronte, trovati {len(fronte)}"
    celle = corpo["celle"][fronte[0]]

    assert celle[indice_colonne["axes"]] == "surface.poisson_depth=7"
    assert celle[indice_colonne["tets"]] == "50630"
    assert celle[indice_colonne["over"]] == "0.06844"
    assert celle[indice_colonne["thickness_error"]] == "1.192"


def _cartella_di_corsa(cliente) -> Path:
    return Path(cliente.get("/api/run").json()["out_dir"])


def test_il_prior_non_ancora_calcolato_lo_dice_invece_di_rispondere_vuoto(cliente, tmp_path):
    """Quinto principio di prodotto: chi arriva dopo non conosce gli step. Uno
    stato vuoto che insegna, non un 404 nudo."""
    risposta = cliente.get("/api/wall")

    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["calcolato"] is False
    assert "step 12" in corpo["motivo"]


def test_il_prior_calcolato_torna_membrature_e_regioni_scartate(cliente, tmp_path):
    import json

    from meshrec.core import pipeline

    corsa = _cartella_di_corsa(cliente)
    corsa.mkdir(parents=True, exist_ok=True)
    (corsa / pipeline.WALL_FILENAME).write_text(
        json.dumps({
            "regioni_trovate": 2,
            "membrature": [{"lunghezza": 1500.0, "sezione": [200.0, 140.0]}],
            "scartate": [{"regione": 1, "controlli_falliti": ["costanza_sezione"],
                           "esiti": {"costanza_sezione": {"passato": False, "valore": 0.4,
                                                            "soglia": 0.1}}}],
        }),
        encoding="utf-8",
    )

    corpo = cliente.get("/api/wall").json()

    assert corpo["calcolato"] is True
    assert len(corpo["prior"]["membrature"]) == 1
    assert corpo["prior"]["scartate"][0]["controlli_falliti"] == ["costanza_sezione"]


def test_generare_un_modello_e_una_azione_e_non_tocca_la_configurazione(cliente, tmp_path):
    """La selezione dei modelli non entra in config.yaml: rigenerare un modello
    in piu' cambierebbe l'impronta di una corsa che non e' cambiata."""
    prima = cliente.get("/api/config").json()

    risposta = cliente.post("/api/model/estruso")

    assert risposta.status_code == 200
    assert risposta.json()["avviato"] == "estruso"
    assert cliente.get("/api/config").json() == prima


def test_un_tipo_di_modello_inventato_viene_rifiutato(cliente):
    risposta = cliente.post("/api/model/asbuilt")

    assert risposta.status_code == 400
    corpo = risposta.json()
    assert corpo["errore"] == "ValueError"
    assert "estruso" in corpo["messaggio"]


def test_il_confronto_dal_server_dice_quali_modelli_mancano(cliente, tmp_path):
    """report.confronta rifiuta una cartella madre senza 12_wall.json leggibile
    (task-12, il segno positivo della corsa madre): senza questo fixture
    /api/compare risponderebbe 400 invece del confronto, perche' e' esattamente
    lo stato di una corsa appena creata che il client 'cliente' costruisce."""
    from meshrec.core import pipeline

    corsa = _cartella_di_corsa(cliente)
    corsa.mkdir(parents=True, exist_ok=True)
    (corsa / pipeline.WALL_FILENAME).write_text("{}", encoding="utf-8")

    corpo = cliente.get("/api/compare").json()

    assert set(corpo["mancanti"]) <= {"estruso", "primitive"}
    assert corpo["confrontabili"]["qualita_elementi"] is False


def test_lo_step_12_e_il_tetto_di_esegui_da_qui_in_poi(cliente):
    """Il tetto e' una scelta dell'interfaccia (server.py), non un'eredita' dal
    predefinito di RunConfig.to_step (13 dalla Fase 5: il solutore fa parte di
    ogni corsa). 'Riprendi da qui' nel pannello non deve far partire un
    processo esterno da solo. Fermo a 11 la riga 12 resterebbe 'mai eseguita'
    dietro 'esegui da qui in poi', senza spiegazione."""
    risposta = cliente.post("/api/step/9/from")

    assert risposta.json()["fino_a"] == 12


def test_membrature_rifiuta_un_prior_piu_vecchio_dello_step_2(cliente, tmp_path):
    """F5 del giro di correzione finale: /api/membrature legge gli indici da
    12_wall.json e la nuvola da 02_segmented.ply senza verificare che vengano
    dalla stessa configurazione. Se lo step 2 e' stato rifatto (un ritaglio
    diverso) senza rifare il 12, gli indici della membratura restano quelli
    della nuvola vecchia -- se la nuvola nuova e' piu' grande, restano dentro
    l'array e dipingono le etichette sui punti sbagliati in silenzio.
    `steps.step_fingerprints` esiste esattamente per vedere questo: qui lo
    steps.json della corsa dichiara per lo step 12 un'impronta che nessuna
    configurazione puo' produrre (non e' un digest sha256 vero), quindi non
    puo' combaciare con quella che il server ricalcola dalla configurazione
    corrente -- lo stesso segnale di un ritaglio diverso.

    Mutazione che deve morire: in /api/membrature, non controllare lo stato
    dello step 12 prima di disegnare -- la richiesta sotto risponderebbe 200
    invece di 400.
    """
    import numpy as np

    from meshrec.core import io, pipeline

    corsa = _cartella_di_corsa(cliente)
    corsa.mkdir(parents=True, exist_ok=True)
    punti = np.random.default_rng(0).normal(size=(200, 3)).astype(np.float64) * 100.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)
    (corsa / pipeline.WALL_FILENAME).write_text(
        json.dumps({
            "regioni_trovate": 1,
            "membrature": [{"lunghezza": 1.0, "sezione": [1.0, 1.0], "indici": [0, 1]}],
            "scartate": [],
        }),
        encoding="utf-8",
    )
    (corsa / "steps.json").write_text(
        json.dumps({
            "12_wall": {"impronta": "impronta-di-una-configurazione-diversa",
                        "esito": "riuscito", "artefatto": pipeline.WALL_FILENAME, "secondi": 0.1},
        }),
        encoding="utf-8",
    )

    risposta = cliente.get("/api/membrature")

    assert risposta.status_code == 400
    assert "12" in risposta.json()["messaggio"]


def test_le_membrature_etichettano_i_punti_anche_quando_il_pavimento_e_stato_tolto(cliente, tmp_path):
    """wall.prior misura sulla nuvola con il pavimento tolto: gli indici che
    'indici' scrive devono restare validi sulla nuvola segmentata intera
    (quella che /api/membrature decima), non sulla sola nuvola ripulita.
    Un pavimento messo PRIMA del telaio nell'ordine dei punti smaschera lo
    sfasamento: senza la correzione, gli indici della membratura cadrebbero
    sui punti del pavimento invece che su quelli del telaio."""
    import numpy as np

    from meshrec.core import io, pipeline, synth, wall
    from meshrec.core.config import SegmentConfig, WallConfig

    telaio_spec = [
        ((0.0, -90.0, 0.0), (200.0, 180.0, 1600.0)),
        ((1400.0, -130.0, 0.0), (200.0, 260.0, 1600.0)),
        ((0.0, -70.0, 1600.0), (1600.0, 140.0, 300.0)),
        ((0.0, -170.0, -300.0), (1600.0, 340.0, 300.0)),
    ]
    spaziatura = 20.0
    telaio = synth.sample_frame_surface(telaio_spec, spaziatura)
    pavimento = synth.sample_box_surface((4000.0, 3000.0, 10.0), spaziatura * 2.0)
    pavimento = pavimento + np.array([-1200.0, -1400.0, -320.0])
    punti = np.vstack([pavimento, telaio])  # pavimento prima: smaschera lo sfasamento

    corsa = _cartella_di_corsa(cliente)
    corsa.mkdir(parents=True, exist_ok=True)
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)
    esito = wall.prior(punti, SegmentConfig(), WallConfig(), spaziatura)
    assert esito["pavimento_trovato"] is True, "precondizione: il banco deve avere un pavimento da togliere"
    (corsa / pipeline.WALL_FILENAME).write_text(json.dumps(esito, default=float), encoding="utf-8")

    risposta = cliente.get("/api/membrature")

    assert risposta.status_code == 200
    corpo = risposta.headers
    etichette = np.frombuffer(risposta.content, dtype="<f4")
    assert (etichette != -1.0).any(), "nessun punto etichettato: gli indici non hanno trovato posto nella nuvola disegnata"
    # I punti che indici[0] designa devono cadere entro l'ingombro del telaio
    # sintetico, non del pavimento (che sta tutto sotto z=-310 e fuori dagli
    # assi x,y del telaio).
    indici_prima_membratura = esito["membrature"][0]["indici"]
    assert len(indici_prima_membratura) > 0
    coordinate = punti[indici_prima_membratura]
    assert coordinate[:, 2].max() > -300.0, (
        "gli indici della membratura cadono nel pavimento: lo sfasamento fra la "
        "nuvola ripulita e la nuvola segmentata non e' stato corretto"
    )
