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


def test_decimate_file_la_seconda_chiamata_da_lo_stesso_risultato(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    prima = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    seconda = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
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
    viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)

    def _esplode(*_args, **_kwargs):
        raise AssertionError("decimate non deve essere richiamata a cache calda")

    monkeypatch.setattr(viewport, "decimate", _esplode)
    ridotti, _gruppi, _voxel = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    assert len(ridotti) <= 5_000


def test_decimate_file_sorgente_modificata_invalida_la_cache(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000, seme=1))
    cache_dir = tmp_path / "cache"
    prima = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    assert sum(len(gruppo) for gruppo in prima[1]) == 50_000

    io.write_cloud(sorgente, _nuvola(60_000, seme=2))
    stato = sorgente.stat()
    os.utime(sorgente, ns=(stato.st_atime_ns, stato.st_mtime_ns + 1_000_000))
    dopo = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    assert sum(len(gruppo) for gruppo in dopo[1]) == 60_000, "la cache non si e' accorta della sorgente cambiata"


def test_decimate_file_cache_corrotta_non_solleva(tmp_path):
    sorgente = tmp_path / "nuvola.ply"
    io.write_cloud(sorgente, _nuvola(50_000))
    cache_dir = tmp_path / "cache"
    viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    percorso = viewport.cache_path(sorgente, 5_000, cache_dir)
    percorso.write_bytes(os.urandom(200))

    ridotti, _gruppi, _voxel = viewport.decimate_file(sorgente, 5_000, 1.0, cache_dir)
    assert len(ridotti) <= 5_000


def test_decimate_file_non_scrive_dentro_la_cartella_della_corsa(tmp_path):
    corsa = tmp_path / "runs" / "lab_crop"
    corsa.mkdir(parents=True)
    sorgente = corsa / "02_segmented.ply"
    io.write_cloud(sorgente, _nuvola(10_000))
    prima = {percorso.name for percorso in corsa.iterdir()}

    cache_dir = tmp_path / ".cache" / "viewport"
    viewport.decimate_file(sorgente, 2_000, 1.0, cache_dir)

    dopo = {percorso.name for percorso in corsa.iterdir()}
    assert dopo == prima, "la cache ha scritto dentro la cartella della corsa"
