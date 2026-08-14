"""Decimazione per il disegno: e' onesta solo se ogni punto pieno e' raggiungibile."""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import viewport


def _nuvola(quanti: int) -> np.ndarray:
    return np.random.default_rng(0).random((quanti, 3)) * 1000.0


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
