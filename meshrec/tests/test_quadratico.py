"""Il tetraedro quadratico: i nodi di lato stanno dove Abaqus li aspetta.

Ticket https://github.com/maeurong/Tesi/issues/45. C3D10 non e' un ripristino:
il commit `66b526d` aveva tolto un'opzione dichiarabile il cui unico effetto
era sollevare `NotImplementedError` dopo l'intera tetraedrizzazione, con la
motivazione «TetGen produce i nodi di lato con order=2, ma il deck scrive i
soli vertici». Qui il writer impara a scrivere i dieci nodi.

**Il difetto contro cui questo file esiste.** TetGen numera i nodi di lato in
un ordine suo, che non e' quello di Abaqus. Applicare la permutazione sbagliata
-- o dimenticarla -- non produce alcun errore: produce una mesh che all'occhio
e' perfetta e una rigidezza falsa. E' la stessa classe dell'ordine delle
colonne del `.frd` (#39), e il modo peggiore di sbagliare.

**Due oracoli indipendenti**, come deciso in #41:

- **geometrico**, qui: ogni nodo di lato dev'essere il punto medio dello
  spigolo che la convenzione Abaqus gli assegna. Non serve il solutore, e
  quindi gira nella suite normale;
- **patch test**, in `tests/validazione/test_patch_test.py`: un elemento con i
  nodi di lato al posto sbagliato non riproduce piu' un campo lineare.

Il primo dice *dove sono i punti*, il secondo dice *come si comporta
l'elemento*. Nessuno dei due implica l'altro.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import abaqus, synth, volume

LATO = (60.0, 60.0, 60.0)

# Convenzione Abaqus C3D10, dal manuale, in indici a base zero: il nodo 5 sta a
# meta' dello spigolo 1-2, il 6 di 2-3, il 7 di 3-1, l'8 di 1-4, il 9 di 2-4,
# il 10 di 3-4.
SPIGOLI_DI_LATO = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def _maglio(order: int) -> tuple[np.ndarray, np.ndarray]:
    vertici, facce = synth.box_mesh(LATO)
    return volume.tetrahedralize(
        vertici, facce,
        max_volume=4000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=order,
    )


def _scarto_dai_punti_medi(nodi: np.ndarray, tets: np.ndarray) -> float:
    """Quanto ogni nodo di lato dista dal punto medio del proprio spigolo."""
    peggiore = 0.0
    for colonna, (a, b) in enumerate(SPIGOLI_DI_LATO, start=4):
        atteso = 0.5 * (nodi[tets[:, a]] + nodi[tets[:, b]])
        distanze = np.linalg.norm(nodi[tets[:, colonna]] - atteso, axis=1)
        peggiore = max(peggiore, float(distanze.max()))
    return peggiore


def test_il_secondo_ordine_produce_dieci_colonne():
    nodi, tets = _maglio(order=2)
    assert tets.shape[1] == 10
    assert len(nodi) > len(_maglio(order=1)[0]), (
        "il secondo ordine deve aggiungere i nodi di lato"
    )


def test_ogni_nodo_di_lato_e_il_punto_medio_del_proprio_spigolo():
    """Il primo oracolo. Tolleranza in millimetri, non relativa: e' una
    coincidenza di punti nello spazio, e su un provino di 60 mm un decimo di
    micron e' gia' oltre qualunque errore di arrotondamento.

    Mutazione che lo uccide: togliere la permutazione in
    `volume.TETGEN_A_ABAQUS`, o scambiarne due elementi qualunque.
    """
    nodi, tets = _maglio(order=2)
    assert _scarto_dai_punti_medi(nodi, tets) < 1e-7


def test_senza_la_permutazione_il_controllo_geometrico_cade():
    """La permutazione **porta carico**: non e' un riordino cosmetico.

    Se l'ordine di TetGen coincidesse con quello di Abaqus, questo test
    fallirebbe -- e sarebbe la prova che la permutazione si puo' togliere. Che
    fallisca **non** e' quindi un dettaglio: e' cio' che giustifica l'esistenza
    di `TETGEN_A_ABAQUS`.
    """
    nodi, tets = _maglio(order=2)
    # Si disfa la permutazione, tornando all'ordine grezzo di TetGen.
    inversa = np.argsort(np.array(volume.TETGEN_A_ABAQUS))
    grezzi = tets[:, inversa]
    assert _scarto_dai_punti_medi(nodi, grezzi) > 1.0, (
        "l'ordine grezzo di TetGen coincide con quello di Abaqus: la "
        "permutazione non servirebbe, e va tolta invece che documentata"
    )


def test_la_permutazione_e_una_permutazione():
    """Ingresso degenere al contrario: dieci indici distinti, nessuno perso.

    Un refuso che duplicasse un indice farebbe sparire un nodo dall'elemento
    senza che nulla protesti -- il tetraedro resterebbe a dieci colonne.
    """
    assert sorted(volume.TETGEN_A_ABAQUS) == list(range(10))


def test_i_vertici_non_si_spostano():
    """Le prime quattro colonne restano i vertici, in ordine.

    Ci contano `quality.element_volumes`, `solve._volume_totale` e tutte le
    metriche di qualita', che leggono `elements[:, :4]`.
    """
    assert volume.TETGEN_A_ABAQUS[:4] == (0, 1, 2, 3)


def test_il_vocabolario_conosce_il_quadratico():
    assert abaqus.NODI_PER_ELEMENTO["C3D10"] == 10
    assert abaqus.ANGOLI_PER_ELEMENTO["C3D10"] == 4, (
        "un C3D10 ha dieci nodi ma quattro vertici: chi cerca le facce usa i vertici"
    )


def test_un_ordine_che_tetgen_non_conosce_e_rifiutato():
    vertici, facce = synth.box_mesh(LATO)
    with pytest.raises(ValueError, match="ordine"):
        volume.tetrahedralize(
            vertici, facce, 4000.0,
            min_ratio=1.8, max_steiner_points=-1, nobisect=False, order=3,
        )


def test_il_volume_del_maglio_quadratico_e_quello_della_scatola():
    """Oracolo indipendente: i nodi di lato non cambiano il volume.

    Stanno a meta' di spigoli diritti, quindi il solido e' lo stesso del
    maglio lineare. Se il volume cambiasse, la permutazione avrebbe mescolato
    vertici e nodi di lato.
    """
    from meshrec.core import quality

    nodi, tets = _maglio(order=2)
    volumi = quality.element_volumes(nodi, tets)
    atteso = LATO[0] * LATO[1] * LATO[2]
    assert float(np.abs(volumi).sum()) == pytest.approx(atteso, rel=1e-6)


def test_un_carico_distribuito_su_facce_quadratiche_si_ferma_invece_di_mentire():
    """L'errore che nessun controllo di equilibrio vedrebbe.

    Su una faccia a 6 nodi la ripartizione per area tributaria mette tutto il
    carico sui **vertici**, mentre la formula consistente per pressione
    uniforme da' **zero ai vertici** e un terzo dell'area a ciascun nodo di
    lato -- Abaqus Theory Guide §3.2.6.

    La risultante resterebbe giusta, perche' `ripartisci` normalizza sul
    totale: l'errore e' **autoequilibrato**, con risultante e momento nulli, e
    attraverserebbe `controlla_reazioni` indenne. Sarebbe un numero plausibile
    e falso proprio sui vertici, dove si legge il picco di tensione.

    Mutazione che lo uccide: togliere la guardia e lasciar ripartire.
    """
    nodi, tets = _maglio(order=2)
    bordo = np.unique(abaqus.boundary_faces(tets))
    with pytest.raises(NotImplementedError, match="consistenti"):
        abaqus.ripartisci(1000.0, nodi, tets, bordo, "C3D10", nome="PROVA")


def test_sul_lineare_la_ripartizione_resta_quella_di_sempre():
    """Regressione: su un triangolo a 3 nodi un terzo per nodo **e'** la
    formula consistente, e la guardia non deve toccarla."""
    nodi, tets = _maglio(order=1)
    bordo = np.unique(abaqus.boundary_faces(tets))
    quote, resoconto = abaqus.ripartisci(1000.0, nodi, tets, bordo, "C3D4", nome="PROVA")
    assert float(quote.sum()) == pytest.approx(1000.0)
    assert resoconto["area_totale"] > 0.0
