"""Il cancello di finitezza: cio' che non e' un numero non passa per buono.

La decisione sta in https://github.com/maeurong/Tesi/issues/36.

`core/solve.py` ha gia' attraversato questa classe di difetto e l'ha chiusa:
ogni suo controllo verifica `np.isfinite` prima di confrontare, e un valore non
finito produce un verdetto negativo invece di un numero plausibile.
`core/quality.py` non l'ha mai attraversata, e il buco misurato il 26/08/2026
era questo:

    tet_volumes(NaN)                -> array([nan])
    inverted_tets(NaN)              -> array([], dtype=int64)   # NON marcato
    volume_metrics(NaN)["inverted"] -> 0

`quality.py` filtrava con `V <= 0.0`, e `nan <= 0.0` e' `False`: il NaN cadeva
dalla parte permissiva. Conseguenza, `InvertedElementsError` non scattava e
`metrics.json` scriveva `inverted: 0` -- **verde su una mesh corrotta**.

La forma del difetto e' sempre la stessa: un confronto che decide «va bene»
quando il valore non e' confrontabile. Questo file la sorveglia in tutti i punti
dove e' stata misurata, in tre moduli -- `core/quality.py`, `core/abaqus.py`,
`core/solve.py` -- perche' e' una classe e non tre casi separati. Il quarto,
`core/volume.py`, non compare qui: la sua guardia
(`raise InvertedElementsError`) legge `inverted_tets`, quindi e' corretta a
monte e i suoi test stanno gia' in `test_volume.py`.

Il criterio adottato: **un elemento e' buono se e solo se la sua misura e'
finita e positiva.** Scritto cosi', e non come negazione di «non positiva», il
non finito cade dalla parte giusta per costruzione invece che per un caso in
piu' da ricordare.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import abaqus, quality

# Tetraedro di riferimento, volume positivo: 1/6.
NODI_SANI = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
TET = np.array([[0, 1, 2, 3]])

# Le quattro facce del tetraedro, orientate: ogni spigolo appartiene a due
# triangoli, quindi la superficie e' chiusa.
FACCE_CHIUSE = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])


def _nodi_con(valore: float) -> np.ndarray:
    """I nodi sani con l'ultima coordinata sostituita da `valore`."""
    nodi = NODI_SANI.copy()
    nodi[3, 2] = valore
    return nodi


# --- il difetto capofila: quality.inverted_tets --------------------------


@pytest.mark.parametrize("valore", [float("nan"), float("inf"), float("-inf")])
def test_una_coordinata_non_finita_e_marcata_degenere(valore):
    """Mutazione che lo uccide: tornare a `np.flatnonzero(volumi <= 0.0)`.

    Con quel confronto `nan <= 0.0` e' `False` e l'elemento passava per sano.

    **Tutti e tre questi casi passano per il ramo del `NaN`**, non tre rami
    diversi: misurato, una coordinata `±inf` produce un volume `nan`, perche'
    nel prodotto misto compare `0 * inf`. La meta' `isfinite` della guardia la
    prova il test successivo, non questo -- distinzione trovata da un audit per
    mutazione, che ha dimostrato come togliere `np.isfinite` sopravvivesse a
    tutti i test di questo file.
    """
    marcati = quality.inverted_tets(_nodi_con(valore), TET)
    assert marcati.tolist() == [0], f"volume da coordinata {valore} non marcato"


def test_un_volume_che_trabocca_a_infinito_e_marcato_degenere():
    """La meta' della guardia che il `NaN` da solo non prova.

    Coordinate grandi ma finite: il prodotto misto trabocca e il volume esce
    `+inf`, che **e' maggiore di zero**. Senza `np.isfinite` l'elemento
    passerebbe per sano -- misurato: `np.flatnonzero(volumi <= 0.0)` su questi
    nodi rende un insieme vuoto.

    Mutazione che lo uccide: `~(volumes > 0.0)`, cioe' la guardia senza il
    controllo di finitezza.
    """
    traboccante = np.array(
        [[0.0, 0.0, 0.0], [1e200, 0.0, 0.0], [0.0, 1e200, 0.0], [0.0, 0.0, 1e200]]
    )
    assert np.isinf(quality.tet_volumes(traboccante, TET)).all(), (
        "il provino non trabocca piu': il test non prova quello che dichiara"
    )
    assert quality.inverted_tets(traboccante, TET).tolist() == [0]


def test_un_tetraedro_sano_non_e_marcato():
    assert quality.inverted_tets(NODI_SANI, TET).size == 0


def test_un_tetraedro_rovesciato_resta_marcato():
    rovesciato = np.array([[0, 2, 1, 3]])
    assert quality.inverted_tets(NODI_SANI, rovesciato).tolist() == [0]


def test_un_tetraedro_complanare_resta_marcato():
    """Volume esattamente zero: comportamento gia' corretto, da non regredire."""
    complanare = _nodi_con(0.0)
    assert quality.inverted_tets(complanare, TET).tolist() == [0]


def test_un_insieme_vuoto_di_elementi_non_marca_nulla():
    """Ingresso degenere: nessun elemento -> nessun indice, non un errore."""
    assert quality.inverted_tets(NODI_SANI, np.empty((0, 4), dtype=int)).size == 0


# --- cio' che il difetto lasciava scrivere in metrics.json ---------------


def test_le_metriche_non_dichiarano_zero_invertiti_su_una_mesh_corrotta():
    """Il numero che finiva verde in `metrics.json` su una mesh con NaN."""
    metriche = quality.volume_metrics(_nodi_con(float("nan")), TET, reference_ratio=2.0)
    assert metriche["inverted"] == 1


def test_un_volume_totale_non_finito_esce_come_none_non_come_nan():
    """`metrics.json` non ammette NaN, e `_distribution` proteggeva solo le distribuzioni.

    Il volume totale usciva `nan` e finiva nel file. La convenzione del modulo
    e' gia' `None` per un aggregato non calcolabile: qui si applica anche a
    questo campo.
    """
    metriche = quality.volume_metrics(_nodi_con(float("nan")), TET, reference_ratio=2.0)
    assert metriche["total_volume"] is None


def test_un_volume_totale_finito_resta_un_numero():
    metriche = quality.volume_metrics(NODI_SANI, TET, reference_ratio=2.0)
    assert metriche["total_volume"] == pytest.approx(1.0 / 6.0)


# --- la stessa perdita nel percorso esaedrico ----------------------------

CUBO = np.array(
    [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
    dtype=float,
)
HEX = np.array([[0, 1, 2, 3, 4, 5, 6, 7]])


def test_un_volume_esaedrico_non_finito_non_finisce_nel_json():
    """Sistemare solo il percorso tetraedrico avrebbe **sembrato** finito.

    Su un esaedro con un nodo `NaN`, `scaled_jacobian` riporta gia' 0,0 e il
    conteggio degli invertiti era corretto anche prima -- ma `total_volume`
    usciva `nan` esattamente come nel percorso tetraedrico, e finiva in
    `modello.json`.
    """
    corrotto = CUBO.copy()
    corrotto[7, 2] = float("nan")
    metriche = quality.hexa_metrics(corrotto, HEX)
    assert metriche["total_volume"] is None


def test_un_esaedro_con_un_nodo_infinito_e_contato_fra_gli_invertiti():
    """Il caso su cui il conteggio esaedrico sbagliava davvero.

    Un audit per mutazione ha mostrato che l'assert sul `NaN` non poteva
    fallire: `scaled_jacobian` la' rende gia' 0,0, e `0 <= 0` era gia' vero col
    codice di prima. Con un nodo **`inf`** invece rende `nan`, e il vecchio
    `(jacobiani <= 0.0).sum()` contava **zero** invertiti su un esaedro
    corrotto. Misurato in entrambe le forme prima di scrivere questo test.

    Mutazione che lo uccide: tornare a `int((jacobiani <= 0.0).sum())`.
    """
    corrotto = CUBO.copy()
    corrotto[7, 2] = float("inf")
    assert np.isnan(quality.scaled_jacobian(corrotto, HEX)).all(), (
        "il provino non produce piu' un jacobiano NaN: il test non morde piu'"
    )
    assert quality.hexa_metrics(corrotto, HEX)["inverted"] == 1


def test_un_cubo_sano_resta_di_volume_unitario():
    metriche = quality.hexa_metrics(CUBO, HEX)
    assert metriche["total_volume"] == pytest.approx(1.0)
    assert metriche["inverted"] == 0


# --- la mesh vuota che si dichiarava chiusa ------------------------------


def test_una_mesh_vuota_non_e_chiusa():
    """Vacuamente vera non basta: `volume.py` la passava a TetGen invece di rifiutarla.

    `(counts == 2).all()` su un array vuoto rende `True`, e quel `True`
    attraversava il cancello che esiste per fermare le superfici aperte.
    """
    assert quality.is_watertight(np.empty((0, 3), dtype=int)) is False


def test_una_superficie_chiusa_resta_chiusa():
    assert quality.is_watertight(FACCE_CHIUSE) is True


def test_una_superficie_aperta_resta_aperta():
    assert quality.is_watertight(FACCE_CHIUSE[:3]) is False


def test_la_mesh_vuota_viene_rifiutata_con_il_proprio_messaggio():
    """Rifiutarla non basta: il messaggio deve dire la cosa giusta.

    Da quando la mesh vuota non e' piu' «chiusa», cade nel ramo delle
    superfici aperte, che le direbbe «non chiusa: 0 spigoli di bordo» -- una
    contraddizione -- e le suggerirebbe una riparazione che non ha facce su
    cui agire.
    """
    from meshrec.core import volume as modulo_volume

    with pytest.raises(modulo_volume.NotWatertightError, match="senza facce"):
        modulo_volume.tetrahedralize(
            np.empty((0, 3)),
            np.empty((0, 3), dtype=np.int64),
            None,
            min_ratio=1.8,
            max_steiner_points=-1,
            nobisect=True,
        )


def test_le_metriche_di_superficie_seguono_la_stessa_convenzione():
    """`surface_metrics` legge lo stesso predicato: la mesh vuota non e' chiusa."""
    metriche = quality.surface_metrics(NODI_SANI, np.empty((0, 3), dtype=int))
    assert metriche["watertight"] is False


# --- la nuvola vuota che produceva infiniti nella mappa di colore --------


def test_la_deviazione_rifiuta_una_nuvola_vuota():
    """`cKDTree` su una nuvola vuota rende `inf`, e quegli `inf` finivano a video.

    `pipeline.genera_modello` passa il risultato allo scalare per vertice della
    mappa di colore: un `inf` la' dentro non e' una misura, e' una scala
    rotta.
    """
    with pytest.raises(ValueError, match="vuota"):
        quality.vertex_deviation(NODI_SANI, np.empty((0, 3)))


def test_la_deviazione_su_un_solo_punto_resta_valida():
    """Un punto solo e' poco, ma e' una misura: non si rifiuta.

    Le quattro distanze sono note esattamente -- la nuvola e' l'origine e i
    vertici sono l'origine piu' i tre versori -- quindi si asseriscono. Un
    audit per mutazione ha mostrato che il solo `isfinite` non uccideva un
    `distanze + 1.0`: forma e finitezza non sono un oracolo.
    """
    scarti = quality.vertex_deviation(NODI_SANI, np.zeros((1, 3)))
    assert scarti == pytest.approx([0.0, 1.0, 1.0, 1.0])


def test_la_deviazione_e_zero_sui_punti_della_nuvola():
    """Regressione: l'oracolo esatto gia' esistente non deve muoversi."""
    scarti = quality.vertex_deviation(NODI_SANI, NODI_SANI)
    assert scarti == pytest.approx(np.zeros(4))


# --- gli errori grezzi di numpy che non dicono cosa fare -----------------


def test_i_set_di_nodi_rifiutano_un_insieme_vuoto():
    """Oggi: `ValueError: zero-size array to reduction operation minimum`.

    Il messaggio nomina una riduzione di numpy, non il fatto che non ci sono
    nodi da cui ricavare i sei set. Chi lo legge non sa cosa fare.
    """
    with pytest.raises(ValueError, match="nessun nodo"):
        abaqus.build_node_sets(np.empty((0, 3)), tolerance=1.0)


def test_i_set_di_nodi_rifiutano_una_coordinata_non_finita():
    """Il difetto che l'audit ha trovato in piu', della stessa classe.

    Misurato prima della guardia, su tre nodi con una x a `NaN`: nessun errore,
    sei set restituiti, e `FACE_FRONT` e `FACE_BACK` **entrambi vuoti**. Il
    minimo e il massimo di quell'asse sono `NaN`, ogni confronto contro `NaN`
    e' falso, e il deck riceve due `*NSET` senza nodi senza che nulla protesti.
    """
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [float("nan"), 0.5, 0.5]])
    with pytest.raises(ValueError, match="non finite"):
        abaqus.build_node_sets(nodi, tolerance=0.1)


def test_i_set_di_nodi_su_un_solo_nodo_restano_calcolabili():
    """Un nodo solo: minimo e massimo coincidono, e i sei set lo contengono tutti."""
    insiemi = abaqus.build_node_sets(np.zeros((1, 3)), tolerance=1.0)
    assert set(insiemi) == {"BASE", "TOP", "FACE_FRONT", "FACE_BACK", "SIDE_LEFT", "SIDE_RIGHT"}
    for indici in insiemi.values():
        assert indici.tolist() == [0]


def test_le_metriche_di_superficie_non_scrivono_nan_nel_json():
    """Il difetto con la conseguenza piu' visibile di tutti.

    `area` e `volume` uscivano `nan` da una superficie con un vertice non
    finito. JSON non ammette `NaN`: `JSONResponse` solleva e `/api/metrics`
    risponde **500**, quindi l'interfaccia resta senza metriche; e
    `JSON.parse('{"area": NaN}')` nel browser e' un `SyntaxError`. Un campo a
    `null` dice «non calcolabile» e attraversa entrambi.
    """
    corrotti = NODI_SANI.copy()
    corrotti[3, 2] = float("nan")
    metriche = quality.surface_metrics(corrotti, FACCE_CHIUSE)
    assert metriche["area"] is None
    assert metriche["volume"] is None


def test_le_metriche_di_superficie_su_una_mesh_sana_restano_numeri():
    metriche = quality.surface_metrics(NODI_SANI, FACCE_CHIUSE)
    assert metriche["volume"] == pytest.approx(1.0 / 6.0)
    assert metriche["area"] > 0.0


def test_un_carico_non_si_ripartisce_su_un_area_non_calcolabile():
    """Il difetto piu' grave trovato dal giro di review: righe `*CLOAD` con `nan`.

    `totale <= 0.0` lasciava passare un'area `NaN`, le quote uscivano tutte
    `NaN` e finivano interpolate nel deck. Un `.inp` con `nan` al posto di una
    forza e' peggio di un deck mancante, perche' il solutore lo legge.
    """
    corrotti = NODI_SANI.copy()
    corrotti[0, 2] = float("nan")
    with pytest.raises(ValueError, match="non è un carico"):
        abaqus.ripartisci(100.0, corrotti, TET, [0, 1, 2], "C3D4", nome="PROVA")


def test_l_allineamento_rifiuta_un_insieme_vuoto():
    """La guardia va dove passano tutti i chiamanti, non solo dove l'avevo messa.

    Un giro di review ha mostrato che il controllo in `build_node_sets` non si
    raggiungeva mai dal flusso vero: `export_model` chiama prima
    `align_to_axes`, che moriva su `np.ptp` con «zero-size array to reduction
    operation maximum» -- esattamente il messaggio grezzo che quella guardia
    dichiarava di voler sostituire.
    """
    with pytest.raises(ValueError, match="nessun nodo"):
        abaqus.align_to_axes(np.empty((0, 3)))


