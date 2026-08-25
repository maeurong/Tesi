"""Decimazione per il disegno: e' onesta solo se ogni punto pieno e' raggiungibile."""

from __future__ import annotations

import os

import numpy as np
import pytest

from meshrec.core import io, viewport


def _nuvola(quanti: int, seme: int = 0) -> np.ndarray:
    return np.random.default_rng(seme).random((quanti, 3)) * 1000.0


def test_la_mappa_copre_ogni_punto_pieno_senza_ripetizioni():
    """La sorveglianza della spec: un punto pieno che non sta in alcun gruppo
    e' una zona su cui il clic non agisce, e non lo si vedrebbe guardando il
    disegno. Deve essere zero, e zero non e' una soglia scelta."""
    punti = _nuvola(100_000)
    ridotti, gruppi, _voxel = viewport.decimate(punti, max_points=20_000, spacing=1.0)
    assert len(ridotti) == len(gruppi)
    tutti = np.concatenate([np.asarray(gruppo) for gruppo in gruppi])
    assert len(np.unique(tutti)) == len(punti), "punti pieni non raggiungibili dalla mappa"
    assert len(tutti) == len(punti), "un punto pieno compare in piu' di un gruppo"


def test_il_conteggio_disegnato_resta_sotto_il_budget():
    punti = _nuvola(100_000)
    ridotti, _gruppi, _voxel = viewport.decimate(punti, max_points=5_000, spacing=1.0)
    assert len(ridotti) <= 5_000


def test_una_nuvola_gia_sotto_il_budget_non_viene_toccata():
    punti = _nuvola(500)
    ridotti, gruppi, voxel = viewport.decimate(punti, max_points=5_000, spacing=1.0)
    assert len(ridotti) == 500
    assert voxel == 0.0, "nessuna decimazione applicata, e la funzione lo dichiara"
    assert [list(gruppo) for gruppo in gruppi[:2]] == [[0], [1]]


def test_i_byte_sono_float32_little_endian():
    punti = np.array([[1.0, 2.0, 3.0]], dtype=np.float64)
    grezzi = viewport.to_float32(punti)
    assert len(grezzi) == 12
    assert np.frombuffer(grezzi, dtype="<f4").tolist() == [1.0, 2.0, 3.0]


def test_la_stima_iniziale_rispetta_budget_e_copertura():
    """Il primo tentativo salta piu' passi (vedi _ESPONENTE_DENSITA), ma il
    contratto resta quello di sempre: sotto budget, mappa completa e senza
    ripetizioni."""
    punti = _nuvola(200_000)
    ridotti, gruppi, _voxel = viewport.decimate(punti, max_points=5_000, spacing=1.0)
    assert len(ridotti) <= 5_000
    tutti = np.concatenate([np.asarray(gruppo) for gruppo in gruppi])
    assert len(np.unique(tutti)) == len(punti), "punti pieni non raggiungibili dalla mappa"
    assert len(tutti) == len(punti), "un punto pieno compare in piu' di un gruppo"


def test_l_ordine_dei_gruppi_non_dipende_dall_implementazione_di_open3d():
    """Un indice disegnato deve significare lo stesso punto su ogni macchina.

    voxel_down_sample_and_trace restituisce i voxel nell'ordine di iterazione
    di una std::unordered_map interna a Open3D: e' stabile dentro una stessa
    build, ma dipende dall'implementazione della libreria standard (libc++ su
    macOS, STL Microsoft su Windows). decimate lo propaga tale e quale, quindi
    'il punto disegnato numero 0' indica un pezzo di nuvola diverso a seconda
    della piattaforma, e nessuna metrica lo smentisce: il disegno e' identico,
    solo rinumerato.

    Misurato su questa macchina (macOS arm64, Open3D 0.19.0): con la nuvola
    dei test di /api/cluster (3 000 punti fitti nell'origine piu' 1 000 punti
    radi a 500 mm) il gruppo 0 e' l'indice pieno 3995, cioe' il blocco rado,
    che DBSCAN classifica interamente come rumore. Che su Windows lo stesso
    gruppo 0 cadesse nel blocco fitto e' invece *dedotto* dai test allora
    verdi, non misurato, e non e' piu' misurabile da qui. Da lì i quattro
    fallimenti di tests/test_server.py sull'endpoint POST /api/cluster.

    L'ordine preteso qui e' quello indotto dal dato: i gruppi crescono per
    indice pieno minimo. Qualunque ordine totale derivato dalla nuvola
    andrebbe bene, ma un test deve nominarne uno; questo e' il piu' economico
    (interi gia' disponibili, nessun confronto in virgola mobile) e coincide
    con l'identita' gia' pretesa a budget non raggiunto (vedi
    test_una_nuvola_gia_sotto_il_budget_non_viene_toccata).
    """
    punti = _nuvola(100_000)
    ridotti, gruppi, voxel = viewport.decimate(punti, max_points=20_000, spacing=1.0)
    assert voxel > 0.0, "precondizione: la decimazione deve essere davvero avvenuta"

    minimi = [int(np.asarray(gruppo).min()) for gruppo in gruppi]
    # La premessa prima della conclusione: "ordinato" equivale a "determinato
    # dal dato" solo se le chiavi sono uniche. Con minimi ripetuti l'ordine dei
    # pari resterebbe quello di Open3D e questo test resterebbe verde.
    assert len(set(minimi)) == len(minimi), (
        "minimi non unici: l'ordinamento da solo non basta a fissare l'ordine"
    )
    assert minimi == sorted(minimi), (
        "l'ordine dei gruppi non e' derivato dalla nuvola: e' quello della hash "
        "map di Open3D, e cambia con la piattaforma"
    )

    # Riordinare i gruppi senza riordinare i punti disegnati slaccerebbe la
    # mappa in silenzio: il punto disegnato deve restare dentro il voxel del
    # proprio gruppo, non solo esserci un gruppo per ogni punto.
    for disegnato, gruppo in zip(ridotti, gruppi, strict=True):
        pieni = punti[np.asarray(gruppo)]
        assert (disegnato >= pieni.min(axis=0) - 1e-9).all(), "punto disegnato fuori dal suo gruppo"
        assert (disegnato <= pieni.max(axis=0) + 1e-9).all(), "punto disegnato fuori dal suo gruppo"


def test_decimate_file_la_seconda_chiamata_da_lo_stesso_risultato(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    prima = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    seconda = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    np.testing.assert_array_equal(prima[0], seconda[0])
    assert len(prima[1]) == len(seconda[1])
    for gruppo_a, gruppo_b in zip(prima[1], seconda[1]):
        np.testing.assert_array_equal(gruppo_a, gruppo_b)
    assert prima[2] == seconda[2]


def test_decimate_file_la_seconda_chiamata_non_ricalcola(tmp_path, monkeypatch):
    """Non si usa il tempo come prova: e' instabile. Si dimostra sostituendo
    decimate con una funzione che solleva, e verificando che la seconda
    chiamata riesca comunque perche' legge dalla cache."""
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)

    def _esplode(*_args, **_kwargs):
        raise AssertionError("decimate non deve essere richiamata a cache calda")

    monkeypatch.setattr(viewport, "decimate", _esplode)
    ridotti, _gruppi, _voxel = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    assert len(ridotti) <= 5_000


def test_decimate_file_sorgente_modificata_invalida_la_cache(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000, seme=1))
    cache_dir = tmp_path / "cache"
    prima = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    assert sum(len(gruppo) for gruppo in prima[1]) == 50_000

    io.write_cloud(sorgente, _nuvola(60_000, seme=2))
    stato = sorgente.stat()
    os.utime(sorgente, ns=(stato.st_atime_ns, stato.st_mtime_ns + 1_000_000))
    dopo = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    assert sum(len(gruppo) for gruppo in dopo[1]) == 60_000, "la cache non si e' accorta della sorgente cambiata"


def test_decimate_file_cache_corrotta_non_solleva(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    percorso = next(cache_dir.glob("*.npz"))
    percorso.write_bytes(os.urandom(200))

    ridotti, _gruppi, _voxel = viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    assert len(ridotti) <= 5_000


def test_decimate_file_non_scrive_dentro_la_cartella_della_corsa(tmp_path):
    corsa = tmp_path / "runs" / "lab_crop"
    corsa.mkdir(parents=True)
    sorgente = corsa / "02_segmented.ply"
    io.write_cloud(sorgente, _nuvola(10_000))
    prima = {percorso.name for percorso in corsa.iterdir()}

    cache_dir = tmp_path / ".cache" / "viewport"
    viewport.decimate_file(sorgente, 2_000, 20_000, 0, cache_dir)

    dopo = {percorso.name for percorso in corsa.iterdir()}
    assert dopo == prima, "la cache ha scritto dentro la cartella della corsa"


def test_il_campo_per_punto_esce_in_float32_come_le_coordinate():
    """Stessa macchina delle mappe di deviazione della Fase 3: cambia il campo
    scalare, non il trasporto."""
    valori = np.array([0.0, 1.5, -2.25])

    corpo = viewport.campo_per_punto(valori)

    assert len(corpo) == 3 * 4
    assert np.frombuffer(corpo, dtype="<f4") == pytest.approx(valori)


def test_decimate_file_pulisce_la_voce_vecchia_anche_se_cambia_il_budget(tmp_path):
    """I-3/fix-1: la pulizia e' per sola sorgente, non per sorgente+budget, cosi'
    la cache resta a una voce per file anche quando max_points cambia fra una
    richiesta e la successiva (es. ?max_points= diverso dal browser)."""
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    viewport.decimate_file(sorgente, 5_000, 20_000, 0, cache_dir)
    viewport.decimate_file(sorgente, 2_000, 20_000, 0, cache_dir)
    assert len(list(cache_dir.glob("*.npz"))) == 1, "e' rimasta piu' di una voce per la stessa sorgente"
