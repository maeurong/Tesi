#!/usr/bin/env python
"""Rimisura le cifre citate da `core/convergenza.py` e da `tests/test_convergenza.py` (#86, #88).

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-7-cantiere/scarto-con-segno.py`.

    uv run python docs/fase-7-cantiere/punto-fisso-degenere.py

**Non legge nulla e non scrive nulla.** Il campione e' generato qui, e seme e
distribuzione stanno scritti sotto: `SEME`, `N`, `RAPPORTI`, `AMPIEZZA`. Prima
di questo script quelle cifre comparivano in tre punti dell'albero senza uno
straccio di provenienza -- ne' script, ne' comando, ne' seme -- ed erano
l'unico blocco di numeri del ramo a non averla.

**Che cosa asserisce, e perche' cosi'.** Non le cifre che stampa: il campione
e' una popolazione arbitraria, e la terza cifra decimale di una frazione non
regge nessuna decisione. Gli `assert` guardano i **fatti** che reggono le due
correzioni -- che prima del fix una frazione non trascurabile di triple
monotone facesse uscire un'eccezione in faccia al chiamante, che dopo il fix
non ne esca nessuna, e che il punto fisso che esaurisce i 200 giri non sia un
caso di scuola ma renda un ultimo iterato che sarebbe passato per un ordine
misurato. Quelli sono i fatti che #86 e #88 pretendono; la prova che le due
correzioni funzionano sta nei test, non qui.

Il corpo del ciclo **prima** della correzione e' ricopiato in
`_punto_fisso_prima`: e' l'unico modo di misurare un comportamento che non
esiste piu' nell'albero. La copia e' quella di `5e96688`, cioe' `f5d7166^`.
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "src"))

from meshrec.core import convergenza  # noqa: E402

SEME = 0
N = 200_000
RAPPORTI = (1.3, 3.0)  # r21 e r32 uniformi qui dentro: la banda che `stima` accetta
AMPIEZZA = 10.0  # f1 e le due differenze, uniformi in [-AMPIEZZA, AMPIEZZA]

# La banda di `stima` con l'ordine formale del C3D10, quello dei test.
ORDINE_FORMALE = 2.0
BANDA = tuple(fattore * ORDINE_FORMALE for fattore in convergenza._BANDA_ORDINE)


def triple(seme: int = SEME, n: int = N):
    """Triple **monotone**: `eps32` prende il segno di `eps21` per costruzione.

    Le non monotone non arrivano mai al punto fisso -- `stima` le rifiuta prima
    come `non_monotono` -- quindi contarle diluirebbe le frazioni con casi che
    la formula non vede.
    """
    rng = random.Random(seme)
    for _ in range(n):
        r21 = rng.uniform(*RAPPORTI)
        r32 = rng.uniform(*RAPPORTI)
        f1 = rng.uniform(-AMPIEZZA, AMPIEZZA)
        eps21 = rng.uniform(-AMPIEZZA, AMPIEZZA)
        eps32 = rng.uniform(0.0, AMPIEZZA) * (1.0 if eps21 > 0 else -1.0)
        yield f1, f1 + eps21, f1 + eps21 + eps32, r21, r32


def _punto_fisso_prima(f1, f2, f3, r21, r32):
    """Il corpo di `ordine_osservato` come stava a `5e96688`, prima di #86/#88.

    Rende `("crash", nome)` se l'eccezione sarebbe uscita al chiamante,
    `("converge", p)`, oppure `("esaurito", p, residuo)` con l'ultimo iterato e
    il residuo dell'ultimo giro -- il numero che il ciclo rendeva come se fosse
    un ordine misurato.
    """
    try:
        eps21, eps32 = f2 - f1, f3 - f2
        if eps21 == 0.0:
            return ("converge", math.inf)
        rapporto = eps32 / eps21
        s = 1.0 if rapporto > 0 else -1.0
        p = abs(math.log(abs(rapporto))) / math.log(r21)
        residuo = math.inf
        for _ in range(200):
            try:
                q = math.log((r21**p - s) / (r32**p - s))
            except ValueError:
                return ("converge", math.nan)
            nuovo = abs(math.log(abs(rapporto)) + q) / math.log(r21)
            residuo = abs(nuovo - p)
            if residuo < 1e-12:
                return ("converge", nuovo)
            p = nuovo
        return ("esaurito", p, residuo)
    except (ValueError, OverflowError, ZeroDivisionError) as errore:
        return ("crash", type(errore).__name__)


def main() -> None:
    print(f"campione: {N} triple monotone, seme {SEME}, "
          f"rapporti uniformi in [{RAPPORTI[0]}; {RAPPORTI[1]}]")
    print(f"banda di `stima` con ordine formale {ORDINE_FORMALE:g}: "
          f"[{BANDA[0]:g}, {BANDA[1]:g}]\n")

    crash: dict[str, int] = {}
    esauriti = 0
    scambiati_per_ordine = 0
    residui: list[float] = []
    crash_dopo: dict[str, int] = {}

    for f1, f2, f3, r21, r32 in triple():
        esito = _punto_fisso_prima(f1, f2, f3, r21, r32)
        if esito[0] == "crash":
            crash[esito[1]] = crash.get(esito[1], 0) + 1
        elif esito[0] == "esaurito":
            esauriti += 1
            residui.append(esito[2])
            # L'ultimo iterato non e' un ordine, ma dentro la banda `stima` lo
            # prendeva per tale e pubblicava una `gci_fine` numerica.
            if math.isfinite(esito[1]) and BANDA[0] <= esito[1] <= BANDA[1]:
                scambiati_per_ordine += 1

        try:
            convergenza.ordine_osservato(f1, f2, f3, r21, r32)
        except Exception as errore:  # noqa: BLE001 -- e' proprio cio' che si conta
            crash_dopo[type(errore).__name__] = crash_dopo.get(type(errore).__name__, 0) + 1

    totale_crash = sum(crash.values())
    per_tipo = ", ".join(f"{nome} {quante}" for nome, quante in sorted(crash.items()))
    print(f"prima del fix: {totale_crash} eccezioni al chiamante "
          f"({totale_crash / N:.2%}) -- {per_tipo}")
    print(f"dopo il fix:   {sum(crash_dopo.values())} eccezioni al chiamante")
    print(f"punto fisso esaurito ai 200 giri: {esauriti} ({esauriti / N:.2%})")
    print(f"  di cui l'ultimo iterato cade in banda e sarebbe passato per un "
          f"ordine: {scambiati_per_ordine} ({scambiati_per_ordine / N:.2%} del campione)")
    if residui:
        print(f"  residuo dell'ultimo giro: mediano {statistics.median(residui):.3g}, "
              f"massimo {max(residui):.3g}")

    assert totale_crash / N > 0.01, (
        f"prima del fix le eccezioni dovrebbero essere una frazione percentuale "
        f"del campione, non un caso di scuola: misurate {totale_crash} su {N}"
    )
    assert not crash_dopo, (
        f"dopo il fix nessuna eccezione deve raggiungere il chiamante, "
        f"ne sono uscite {crash_dopo}"
    )
    assert scambiati_per_ordine > 0, (
        "senza un solo ultimo iterato in banda il `return math.nan` finale "
        "sarebbe una guardia contro nulla"
    )

    print("\ntutti gli assert passati")


if __name__ == "__main__":
    main()
