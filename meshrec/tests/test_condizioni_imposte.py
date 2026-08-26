"""Spostamenti imposti e forze nodali nel deck: le due card che il patch test richiede.

Aggiunte per https://github.com/maeurong/Tesi/issues/46. Nessuna delle vie che
`write_inp` gia' offriva sa esprimerle:

- `fixed_nset` blocca un set intero a zero, e il patch test impone su ogni nodo
  di bordo un valore **diverso**, quello del campo lineare in quel punto;
- `ripartisci` distribuisce una risultante per area tributaria, mentre la
  trazione di uno stato tensionale costante da' un vettore per nodo che non e'
  proporzionale all'area.

I test qui guardano il **testo del deck**, non il solutore: sono veloci e
girano nella suite normale. Che quel deck poi dia il risultato giusto lo dice
`tests/validazione/test_patch_test.py`, che ha bisogno di `ccx`.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import abaqus
from meshrec.core.config import Material

MATERIALE = Material(name="PROVA", young=1000.0, poisson=0.25, density=1.0e-9)

# Un tetraedro solo: basta a produrre un deck, e tiene il testo leggibile.
NODI = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]])
TET = np.array([[0, 1, 2, 3]])
SET = {"BASE": np.array([0])}


def _righe(percorso) -> list[str]:
    return percorso.read_text(encoding="ascii").splitlines()


def _blocco(righe: list[str], keyword: str) -> list[str]:
    """Le righe che seguono `keyword` fino alla card successiva."""
    dentro = False
    raccolte: list[str] = []
    for riga in righe:
        if riga.startswith("*"):
            if dentro:
                break
            dentro = riga.split(",")[0].strip().upper() == keyword.upper()
            continue
        if dentro:
            raccolte.append(riga.strip())
    return raccolte


def test_uno_spostamento_imposto_finisce_nel_blocco_boundary(tmp_path):
    """Formato `*BOUNDARY`: nodo, primo grado, ultimo grado, valore.

    Il numero di nodo e' quello del deck, cioe' l'indice piu' uno: il deck e'
    a base uno e gli array a base zero, ed e' l'errore che si fa una volta
    sola ma si paga su ogni riga.
    """
    percorso = tmp_path / "m.inp"
    abaqus.write_inp(
        percorso, NODI, TET, node_sets=SET, material=MATERIALE,
        spostamenti_imposti={2: {1: 0.5, 3: -0.25}},
    )
    blocco = _blocco(_righe(percorso), "*BOUNDARY")
    assert "BASE, 1, 3" in blocco, "il set vincolato non deve sparire"
    assert "3, 1, 1, 5.000000000e-01" in blocco
    assert "3, 3, 3, -2.500000000e-01" in blocco


def test_senza_spostamenti_imposti_il_deck_non_cambia(tmp_path):
    """Regressione: il parametro nuovo e' opzionale e inerte se assente."""
    a, b = tmp_path / "a.inp", tmp_path / "b.inp"
    abaqus.write_inp(a, NODI, TET, node_sets=SET, material=MATERIALE)
    abaqus.write_inp(b, NODI, TET, node_sets=SET, material=MATERIALE, spostamenti_imposti={})
    assert a.read_text(encoding="ascii") == b.read_text(encoding="ascii")


def test_le_forze_nodali_finiscono_nel_blocco_cload(tmp_path):
    """Formato `*CLOAD`: nodo, grado, valore. Una riga per componente."""
    percorso = tmp_path / "m.inp"
    abaqus.write_inp(
        percorso, NODI, TET, node_sets=SET, material=MATERIALE,
        carichi_nodali={1: (3.0, 0.0, -7.5)},
    )
    blocco = _blocco(_righe(percorso), "*CLOAD")
    assert "2, 1, 3.000000000e+00" in blocco
    assert "2, 3, -7.500000000e+00" in blocco


def test_una_componente_nulla_non_produce_una_riga(tmp_path):
    """Una riga `*CLOAD` a zero non e' un carico: e' rumore in un file che
    finisce in appendice, e nasconde le righe che contano."""
    percorso = tmp_path / "m.inp"
    abaqus.write_inp(
        percorso, NODI, TET, node_sets=SET, material=MATERIALE,
        carichi_nodali={1: (3.0, 0.0, -7.5)},
    )
    blocco = _blocco(_righe(percorso), "*CLOAD")
    assert not any(riga.startswith("2, 2,") for riga in blocco)
    assert len(blocco) == 2


def test_senza_forze_nodali_il_deck_non_cambia(tmp_path):
    a, b = tmp_path / "a.inp", tmp_path / "b.inp"
    abaqus.write_inp(a, NODI, TET, node_sets=SET, material=MATERIALE)
    abaqus.write_inp(b, NODI, TET, node_sets=SET, material=MATERIALE, carichi_nodali={})
    assert a.read_text(encoding="ascii") == b.read_text(encoding="ascii")


def test_le_due_card_convivono_nello_stesso_deck(tmp_path):
    """Il patch test nella variante a carichi le usa insieme: vincoli minimi
    su alcuni gradi, forze sui nodi di bordo."""
    percorso = tmp_path / "m.inp"
    abaqus.write_inp(
        percorso, NODI, TET, node_sets=SET, material=MATERIALE,
        spostamenti_imposti={2: {2: 1.0}},
        carichi_nodali={3: (0.0, 0.0, 5.0)},
    )
    righe = _righe(percorso)
    assert "3, 2, 2, 1.000000000e+00" in _blocco(righe, "*BOUNDARY")
    assert "4, 3, 5.000000000e+00" in _blocco(righe, "*CLOAD")


@pytest.mark.parametrize("grado", [1, 2, 3])
def test_ogni_grado_di_liberta_e_esprimibile(grado):
    """Ingresso degenere al contrario: nessuno dei tre gradi deve essere
    dimenticato dalla scrittura."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as cartella:
        percorso = Path(cartella) / "m.inp"
        abaqus.write_inp(
            percorso, NODI, TET, node_sets=SET, material=MATERIALE,
            spostamenti_imposti={0: {grado: 2.0}},
        )
        assert f"1, {grado}, {grado}, 2.000000000e+00" in _blocco(_righe(percorso), "*BOUNDARY")
