"""Stima dell'errore di discretizzazione: Richardson e GCI (#71).

ASME V&V la chiama «the largest omission in the verification process»: senza
questa stima ogni numero pubblicato e' un numero senza barra d'errore.

**Il metodo non si applica a tutto, ed e' il punto del modulo.** Richardson e
GCI presuppongono convergenza **monotona** in campo asintotico. Sul benchmark
NAFEMS LE10 la tensione nel punto d'angolo **peggiora raffinando** -- Abaqus
lo dichiara per il proprio C3D10 (1,15% -> 7,24%) e la nostra corsa lo
riproduce (+5,31% -> +7,05%), perche' nella maglia grossolana quattro
elementi convergono nel punto di lettura e nella fine uno solo. Applicare la
formula li' produrrebbe un numero, e quel numero non significherebbe nulla.

Per questo ogni via d'uscita degenere qui **dichiara** invece di calcolare:
non e' prudenza, e' che la formula ha ipotesi e fuori da quelle il suo
risultato non e' una stima con piu' incertezza, e' un'altra cosa.

Procedura: Celik, Ghia, Roache, Freitas, Coleman, Raad (2008), «Procedure for
Estimation and Reporting of Uncertainty Due to Discretization in CFD
Applications», Journal of Fluids Engineering 130(7):078001. Il fattore di
sicurezza sta in `core/soglie.py` (`gci_fattore_sicurezza` = 1,25, Roache
1994), non qui: e' una soglia dichiarata, e questo modulo la riceve.

**Limite dichiarato.** Richardson classico assume griglie **nidificate**, cioe'
che la fine contenga la grossolana. TetGen non le produce: raffinando con
`max_volume` si ottiene un maglio nuovo, non una suddivisione del precedente.
La procedura di Celik e' formulata proprio per griglie non strutturate e usa
una dimensione rappresentativa `h` invece del rapporto di suddivisione, ma
l'ipotesi resta piu' debole di quella del caso strutturato e va detto.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

# Rapporto di raffinamento minimo perche' la stima abbia senso.
#
# La formula divide per `r**p - 1`: con `r` vicino a 1 quel denominatore va a
# zero e la GCI esplode su differenze che sono rumore del solutore. Celik et
# al. (2008) raccomandano **r >= 1,3** in modo esplicito, e il valore e' quello
# -- `origine: letta`, non nostra.
_RAPPORTO_MINIMO = 1.3

# Quanto l'ordine osservato puo' allontanarsi dal formale prima che la stima
# si dichiari fuori campo asintotico.
#
# Non e' una taratura: e' il confine oltre il quale `p` smette di essere una
# misura dell'ordine del metodo. Celik et al. osservano che valori molto
# lontani da quello formale segnalano che le griglie non sono nel campo
# asintotico, oppure che la grandezza non converge in modo regolare. La banda
# larga -- da 0,5 a 3 volte l'ordine formale -- e' scelta per **non** far
# passare un `p` assurdo (negativo, o dieci volte il formale) e per non
# bocciare una convergenza reale ma imperfetta.
_BANDA_ORDINE = (0.5, 3.0)

# Sotto questa GCI la cifra non e' riproducibile e la `spiegazione` smette di
# citarla come numero (#101).
#
# `docs/validazione/convergenza-di-maglio.md` misura la stessa serie di griglie
# su due piattaforme: GCI 0,0015% su macOS arm64 e 0,0346% su Linux x86-64,
# ventitre' volte di scarto a fronte dello stesso errore vero (0,279% contro
# 0,271%). Sotto quella scala la GCI misura il **rumore del maglio** -- che
# dipende dalla piattaforma, #66 -- invece della discretizzazione, e il
# documento conclude che una GCI molto piccola va letta, non citata.
#
# `origine: nostra`. Lo 0,1% sta un fattore 3 sopra la maggiore delle due
# letture non riproducibili, scelto per coprirle entrambe con margine invece di
# ritagliarsi addosso a una delle due. Non sta in `core/soglie.py` perche' non
# e' un coefficiente del metodo che questo modulo riceve -- il fattore di
# sicurezza lo e', e infatti arriva come argomento: e' la regola con cui il
# modulo scrive il proprio testo.
_GCI_SOTTO_RUMORE = 1e-3

Esito = Literal[
    "asintotico", "non_monotono", "fuori_campo", "rapporto_troppo_piccolo", "valore_nullo"
]


def ordine_osservato(f1: float, f2: float, f3: float, r21: float, r32: float) -> float:
    """L'ordine di convergenza **misurato** sulle tre griglie, non assunto.

    Risolve per punto fisso l'equazione di Celik et al. (2008), eq. (2):

        p = |ln|eps32 / eps21| + q(p)| / ln(r21)
        q(p) = ln( (r21**p - s) / (r32**p - s) ),  s = segno(eps32 / eps21)

    Con rapporti uguali (`r21 == r32`) il termine `q` si annulla e la formula
    si riduce a quella classica di Richardson: e' il caso strutturato, che qui
    non capita quasi mai perche' TetGen non produce raffinamenti esatti.

    `f1` e' il valore sulla griglia **piu' fine**.

    Due uscite non sono numeri: `math.inf` quando `f1 == f2`, perche' senza
    pendenza non c'e' ordine da stimare, e `math.nan` quando il punto fisso non
    si risolve -- diverge, trabocca, o non converge nei 200 giri. `stima` le
    tratta entrambe come ordine non determinabile e dichiara `fuori_campo`.
    """
    if not r21 > 1.0:
        raise ValueError(
            f"il rapporto di raffinamento r21 deve essere maggiore di 1, è {r21!r}: "
            "la formula divide per ln(r21), e su griglie non raffinate quel "
            "denominatore è zero"
        )
    eps21, eps32 = f2 - f1, f3 - f2
    if eps21 == 0.0:
        return math.inf
    rapporto = eps32 / eps21
    s = 1.0 if rapporto > 0 else -1.0
    p = abs(math.log(abs(rapporto))) / math.log(r21)
    for _ in range(200):
        try:
            q = math.log((r21**p - s) / (r32**p - s))
        except (ValueError, OverflowError, ZeroDivisionError):
            # ValueError: il logaritmo esce dal dominio. OverflowError: `r21**p`
            # supera il massimo float perche' il punto fisso diverge.
            # ZeroDivisionError: `p = 0` rende `r32**p - s` esattamente nullo.
            # Tutte e tre dicono la stessa cosa -- l'ordine non si misura -- e
            # nessuna e' un errore del chiamante.
            return math.nan
        nuovo = abs(math.log(abs(rapporto)) + q) / math.log(r21)
        if abs(nuovo - p) < 1e-12:
            return nuovo
        p = nuovo
    # Non e' codice morto: misurato su 200.000 triple monotone con rapporti in
    # [1,3; 3,0], 4.336 non convergono (2,17%) e 1.319 di quelle uscivano
    # `asintotico` con una `gci_fine` numerica, residuo mediano 2,5e-3 e massimo
    # 17,4. L'ultimo iterato di un punto fisso che non converge non e' l'ordine.
    return math.nan


def stima(
    valori: tuple[float, float, float],
    dimensioni: tuple[float, float, float],
    *,
    fattore: float,
    ordine_formale: float,
) -> dict[str, object]:
    """La stima completa su tre griglie, o la dichiarazione che non si puo' fare.

    `valori` e `dimensioni` sono ordinati dalla griglia **piu' fine** alla piu'
    grossolana: `dimensioni[0] < dimensioni[1] < dimensioni[2]`.

    La chiave `esito` dice sempre che cosa e' successo, e le cinque uscite
    non sono intercambiabili:

    - `asintotico` -- la stima vale, e `gci_fine` e' la barra d'errore;
    - `non_monotono` -- i tre valori non sono ordinati, quindi la convergenza
      oscilla e Richardson non ha ipotesi. E' il caso di LE10;
    - `fuori_campo` -- l'ordine osservato e' assurdo o troppo lontano dal
      formale: le griglie non sono nel campo asintotico;
    - `rapporto_troppo_piccolo` -- le griglie sono troppo vicine fra loro
      perche' la differenza sia segnale invece che rumore;
    - `valore_nullo` -- il valore su una delle due griglie piu' fini e' zero:
      l'errore relativo non ha scala su cui riferirsi, e cio' che ne uscirebbe
      non e' un errore grande, e' un errore non definito.

    Fuori da `asintotico` le chiavi numeriche restano scritte -- si marcano,
    non si nascondono, come i verdetti di `core/solve.py` -- ma `gci_fine` e'
    `None`, perche' un numero li' verrebbe letto come una barra d'errore e non
    lo sarebbe.
    """
    f1, f2, f3 = (float(v) for v in valori)
    h1, h2, h3 = (float(h) for h in dimensioni)
    if not (h1 < h2 < h3):
        raise ValueError(
            f"le dimensioni devono crescere dalla griglia fine alla grossolana, "
            f"sono arrivate {dimensioni!r}: senza quest'ordine i rapporti di "
            "raffinamento escono minori di 1 e la stima misura il contrario"
        )
    if not all(np.isfinite(v) for v in (f1, f2, f3, h1, h2, h3, fattore, ordine_formale)):
        raise ValueError("valori, dimensioni, fattore e ordine formale devono essere finiti")

    r21, r32 = h2 / h1, h3 / h2
    comune: dict[str, object] = {
        "r21": r21,
        "r32": r32,
        "valori": [f1, f2, f3],
        "dimensioni": [h1, h2, h3],
        "fattore": float(fattore),
        "ordine_formale": float(ordine_formale),
    }

    if min(r21, r32) < _RAPPORTO_MINIMO:
        return {
            **comune, "esito": "rapporto_troppo_piccolo", "ordine_osservato": None,
            "estrapolato": None, "gci_fine": None, "gci_grossolana": None,
            "rapporto_asintotico": None,
            "spiegazione": (
                f"il rapporto di raffinamento minimo è {min(r21, r32):.3f}, sotto "
                f"{_RAPPORTO_MINIMO}: la formula divide per r**p - 1 e su griglie "
                "così vicine amplifica il rumore del solutore invece di misurare "
                "la discretizzazione"
            ),
        }

    # Monotonia: i tre valori devono andare nella stessa direzione. Se
    # `eps32/eps21` e' negativo la convergenza oscilla, ed e' esattamente cio'
    # che LE10 fa sulla tensione nel punto d'angolo.
    eps21, eps32 = f2 - f1, f3 - f2
    if eps21 == 0.0 or eps32 == 0.0 or (eps32 / eps21) < 0.0:
        return {
            **comune, "esito": "non_monotono", "ordine_osservato": None,
            "estrapolato": None, "gci_fine": None, "gci_grossolana": None,
            "rapporto_asintotico": None,
            "spiegazione": (
                "i tre valori non convergono in modo monotono: Richardson "
                "presuppone che l'errore cali con la stessa legge e con lo stesso "
                "segno, e senza quell'ipotesi la formula rende un numero che non "
                "è una stima d'errore"
            ),
        }

    # `e21` ed `e32` sono errori **relativi**, normalizzati su `f1` e su `f2`:
    # con uno dei due nullo non sono grandi, non esistono. Non e' `fuori_campo`
    # -- le griglie possono benissimo essere nel campo asintotico, e sulle serie
    # di potenza esatte l'ordine torna -- quindi l'esito ha un nome proprio
    # invece di essere forzato in uno dei quattro: a mancare e' la scala su cui
    # riferire l'errore, non l'ipotesi di Richardson.
    if f1 == 0.0 or f2 == 0.0:
        return {
            **comune, "esito": "valore_nullo", "ordine_osservato": None,
            "estrapolato": None, "gci_fine": None, "gci_grossolana": None,
            "rapporto_asintotico": None,
            "spiegazione": (
                "un valore della serie è nullo: la GCI è un errore relativo e "
                "senza una scala su cui riferirlo uscirebbe infinita, che non "
                "vuol dire errore grande, vuol dire errore non definito"
            ),
        }

    p = ordine_osservato(f1, f2, f3, r21, r32)
    basso, alto = _BANDA_ORDINE[0] * ordine_formale, _BANDA_ORDINE[1] * ordine_formale
    if not np.isfinite(p) or not (basso <= p <= alto):
        misura = (
            f"vale {p:.3f}" if np.isfinite(p)
            else "non è determinabile, perché il punto fisso di Celik non si risolve,"
        )
        return {
            **comune, "esito": "fuori_campo", "ordine_osservato": None if not np.isfinite(p) else p,
            "estrapolato": None, "gci_fine": None, "gci_grossolana": None,
            "rapporto_asintotico": None,
            "spiegazione": (
                f"l'ordine osservato {misura} contro un ordine formale di "
                f"{ordine_formale:g}, fuori dalla banda [{basso:g}, {alto:g}]: le "
                "griglie non sono nel campo asintotico, oppure la grandezza non "
                "converge con una legge di potenza"
            ),
        }

    estrapolato = (r21**p * f1 - f2) / (r21**p - 1.0)
    e21 = abs((f1 - f2) / f1) if f1 != 0.0 else math.inf
    e32 = abs((f2 - f3) / f2) if f2 != 0.0 else math.inf
    gci21 = fattore * e21 / (r21**p - 1.0)
    gci32 = fattore * e32 / (r32**p - 1.0)
    # Indice di campo asintotico: tende a 1 quando le due GCI stanno nel
    # rapporto che l'ordine osservato prevede.
    #
    # **Non vale 1 per il solo fatto che l'ordine sia giusto**, e leggerlo cosi'
    # porta fuori strada. Misurato su serie di potenza **esatte** con p = 2:
    # l'indice vale 0,786 quando l'errore sulla griglia fine e' il 10%, 0,971
    # all'1%, 0,997 allo 0,1% e 0,99997 allo 0,001%. Il motivo e' che `e21` ed
    # `e32` sono errori **relativi**, normalizzati su `f1` e su `f2`, che
    # coincidono solo quando l'errore e' piccolo. L'indice misura quindi due
    # cose insieme -- che la legge di potenza regga e che si sia abbastanza
    # vicini alla soluzione -- e un valore lontano da 1 su errori grossi non e'
    # di per se' una smentita dell'ordine.
    asintotico = gci32 / (r21**p * gci21) if gci21 != 0.0 else math.nan
    return {
        **comune,
        "esito": "asintotico",
        "ordine_osservato": p,
        "estrapolato": estrapolato,
        "gci_fine": gci21,
        "gci_grossolana": gci32,
        "rapporto_asintotico": asintotico,
        "spiegazione": (
            f"ordine osservato {p:.3f}, GCI sulla griglia fine "
            + (
                "sotto la soglia di rumore di questa serie di griglie"
                if gci21 < _GCI_SOTTO_RUMORE
                else f"{gci21 * 100:.3f}%"
            )
            + f", indice di campo asintotico {asintotico:.4f}"
        ),
    }
