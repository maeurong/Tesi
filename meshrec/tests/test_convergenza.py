"""La macchina della GCI, con oracoli in forma chiusa (#71).

Su una serie costruita come `f(h) = f_esatto + C*h^p` la risposta si conosce
per costruzione: l'ordine osservato deve tornare `p` e l'estrapolato
`f_esatto`. Nessun numero registrato da una corsa: sono oracoli, non
regressioni.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from meshrec.core import convergenza

FATTORE = 1.25  # `gci_fattore_sicurezza` in core/soglie.py, Roache 1994


def serie(esatto: float, c: float, p: float, h: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(esatto + c * x**p for x in h)


def test_su_una_serie_di_potenza_esatta_ordine_ed_estrapolato_tornano():
    """L'oracolo portante: se la macchina non ritrova `p` e `f_esatto` su una
    serie costruita, ogni numero che produce su dati veri e' senza garanzia."""
    h = (1.0, 2.0, 4.0)
    esito = convergenza.stima(serie(1.0, 0.1, 2.0, h), h, fattore=FATTORE, ordine_formale=2.0)

    assert esito["esito"] == "asintotico"
    assert esito["ordine_osservato"] == pytest.approx(2.0, abs=1e-9)
    assert esito["estrapolato"] == pytest.approx(1.0, abs=1e-9)


def test_l_ordine_torna_anche_con_rapporti_di_raffinamento_diversi():
    """La meta' che distingue questa procedura da Richardson classico.

    Con `r21 != r32` la formula chiusa non basta e serve il punto fisso di
    Celik et al. (2008). E' il caso normale qui: TetGen non produce
    raffinamenti esatti, quindi due rapporti uguali non capitano quasi mai.
    Una macchina che usasse la formula a rapporti uguali passerebbe il test
    sopra e sbaglierebbe su ogni dato vero.
    """
    h = (1.0, 1.5, 2.1)  # r21 = 1,5 e r32 = 1,4
    esito = convergenza.stima(serie(5.0, 0.3, 1.0, h), h, fattore=FATTORE, ordine_formale=1.0)

    assert esito["r21"] == pytest.approx(1.5)
    assert esito["r32"] == pytest.approx(1.4)
    assert esito["ordine_osservato"] == pytest.approx(1.0, abs=1e-9)
    assert esito["estrapolato"] == pytest.approx(5.0, abs=1e-9)


def test_la_gci_racchiude_la_distanza_dall_estrapolato():
    """Che cosa la GCI **stima**, asserito invece che assunto: la distanza
    fra la griglia fine e la soluzione a maglio convergente, non quella dal
    vero. La differenza fra le due e' misurata su dati reali in
    `tests/validazione/test_convergenza_mensola.py`.
    """
    h = (1.0, 2.0, 4.0)
    valori = serie(1.0, 0.01, 2.0, h)
    esito = convergenza.stima(valori, h, fattore=FATTORE, ordine_formale=2.0)

    distanza = abs(valori[0] - esito["estrapolato"]) / abs(valori[0])
    assert distanza <= esito["gci_fine"], (distanza, esito["gci_fine"])


def test_l_indice_asintotico_tende_a_uno_al_ridursi_dell_errore():
    """Misurato, e va saputo: l'indice **non** vale 1 per il solo fatto che
    l'ordine sia giusto. Su serie di potenza esatte con p = 2 vale 0,79 con
    un errore del 10% sulla griglia fine e 0,997 allo 0,1%, perche' `e21` ed
    `e32` sono errori relativi normalizzati su valori diversi.

    Senza questo test qualcuno leggerebbe 0,79 come «non asintotico» su una
    serie il cui ordine e' esatto.
    """
    h = (1.0, 2.0, 4.0)
    indici = [
        convergenza.stima(serie(1.0, c, 2.0, h), h, fattore=FATTORE, ordine_formale=2.0)[
            "rapporto_asintotico"
        ]
        for c in (0.1, 0.01, 0.001)
    ]

    assert indici[0] < indici[1] < indici[2], indici
    assert indici[0] == pytest.approx(0.7857, abs=1e-3)
    assert indici[2] == pytest.approx(1.0, abs=5e-3)


def test_una_convergenza_non_monotona_si_dichiara_e_non_si_calcola():
    """Il caso LE10: la tensione nel punto d'angolo **peggiora** raffinando.
    Richardson presuppone il contrario, e li' la formula renderebbe un numero
    che non e' una stima d'errore. Il verdetto e' la parola, non il numero.
    """
    esito = convergenza.stima((7.05, 5.31, 5.60), (1.0, 1.6, 2.6),
                              fattore=FATTORE, ordine_formale=2.0)

    assert esito["esito"] == "non_monotono"
    assert esito["gci_fine"] is None
    assert esito["ordine_osservato"] is None


def test_griglie_troppo_vicine_si_dichiarano_invece_di_amplificare_il_rumore():
    """La formula divide per `r**p - 1`: sotto il rapporto minimo quel
    denominatore va a zero e la GCI misura il rumore del solutore."""
    esito = convergenza.stima((1.10, 1.12, 1.15), (1.0, 1.1, 1.2),
                              fattore=FATTORE, ordine_formale=2.0)

    assert esito["esito"] == "rapporto_troppo_piccolo"
    assert esito["gci_fine"] is None


def test_un_ordine_assurdo_dichiara_che_non_si_e_nel_campo_asintotico():
    """Tre valori che non seguono una legge di potenza danno un `p` enorme.
    Stampare la GCI che ne discende sarebbe stampare un numero preciso e
    privo di significato.
    """
    esito = convergenza.stima((1.0, 1.0000001, 9.0), (1.0, 2.0, 4.0),
                              fattore=FATTORE, ordine_formale=2.0)

    assert esito["esito"] == "fuori_campo"
    assert esito["gci_fine"] is None
    # il numero resta scritto: si marca, non si nasconde
    assert esito["ordine_osservato"] > 3.0 * 2.0


def test_le_dimensioni_devono_andare_dalla_fine_alla_grossolana():
    """Invertirle non da' un errore piu' avanti: da' una stima del contrario,
    con i rapporti minori di 1 e il logaritmo di segno opposto."""
    with pytest.raises(ValueError, match="dalla griglia fine"):
        convergenza.stima((1.0, 2.0, 3.0), (4.0, 2.0, 1.0),
                          fattore=FATTORE, ordine_formale=2.0)


@pytest.mark.parametrize("anomalo", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("posizione", ["valore", "dimensione", "fattore", "ordine"])
def test_ogni_ingresso_non_finito_viene_rifiutato(anomalo, posizione):
    """Dodici combinazioni. La regola del progetto e' enumerare gli ingressi
    che raggiungono un confronto invece di ragionare su quali possano davvero
    degenerare -- stessa tabella di `tests/test_solve.py`.
    """
    valori, h, fattore, ordine = (1.1, 1.4, 2.6), (1.0, 2.0, 4.0), FATTORE, 2.0
    if posizione == "valore":
        valori = (anomalo, 1.4, 2.6)
    elif posizione == "dimensione":
        h = (1.0, anomalo, 4.0)
    elif posizione == "fattore":
        fattore = anomalo
    else:
        ordine = anomalo

    with pytest.raises(ValueError):
        convergenza.stima(valori, h, fattore=fattore, ordine_formale=ordine)


def test_l_ordine_osservato_da_solo_e_esatto_sui_rapporti_uguali():
    """`ordine_osservato` e' pubblica e va provata da sola: con rapporti
    uguali il termine `q` si annulla e resta la formula classica di
    Richardson, che qui deve tornare esatta."""
    h = (1.0, 3.0, 9.0)
    f1, f2, f3 = serie(2.0, 0.5, 1.5, h)

    p = convergenza.ordine_osservato(f1, f2, f3, 3.0, 3.0)

    assert p == pytest.approx(1.5, abs=1e-9)
    assert math.isfinite(p)


def test_due_valori_identici_non_dividono_per_zero():
    """`eps21 = 0` significa che la griglia fine e la media danno lo stesso
    numero: non c'e' pendenza da cui stimare un ordine."""
    p = convergenza.ordine_osservato(1.0, 1.0, 2.0, 2.0, 2.0)

    assert math.isinf(p)
    esito = convergenza.stima((1.0, 1.0, 2.0), (1.0, 2.0, 4.0),
                              fattore=FATTORE, ordine_formale=2.0)
    assert esito["esito"] == "non_monotono"


def test_i_numeri_restano_scritti_anche_quando_la_stima_non_si_fa():
    """Si marca, non si nasconde: chi legge deve poter vedere i tre valori e i
    due rapporti che hanno prodotto il rifiuto."""
    esito = convergenza.stima((7.05, 5.31, 5.60), (1.0, 1.6, 2.6),
                              fattore=FATTORE, ordine_formale=2.0)

    assert esito["valori"] == [7.05, 5.31, 5.60]
    assert esito["r21"] == pytest.approx(1.6)
    assert np.isfinite(esito["r32"])
    assert esito["spiegazione"]
