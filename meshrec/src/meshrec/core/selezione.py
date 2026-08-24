"""Da regola geometrica dichiarata a indici di nodo, sulla mesh gia' allineata.

Il modulo non sa nulla di deck: prende array e rende indici. Gli oracoli che
stanno qui sono quelli che **hanno bisogno della mesh** -- zero nodi, tutti i
nodi, il nodo piu' vicino troppo lontano. Quelli che non ne hanno bisogno
(forme impossibili, nomi che collidono, riferimenti a selettori non
dichiarati) stanno a monte, in `core/config.py`, e si rifiutano senza aver
letto una nuvola: e' la spaccatura che rende distinguibili cinque ingressi
degeneri che altrimenti darebbero tutti lo stesso sintomo.
"""

from __future__ import annotations

import numpy as np

from meshrec.core.config import (
    Selettore,
    SelettoreBox,
    SelettoreNodo,
    SelettoreNset,
    SelettoreSfera,
)

# Quanto lontano puo' cadere il nodo piu' vicino prima che la selezione sia un
# errore di battitura invece di un indirizzo.
#
# Tre spigoli non e' un numero scelto a occhio: e' la soglia piu' stretta che
# separa il punto legittimo di prova dal caso degenere sulla mesh del caso
# studio, con un margine di due ordini di grandezza fra i due. Le misure che
# la fissano stanno nel documento di fase (`docs/fase-6-carichi.md`), non qui:
# un numero di laboratorio dentro `src/` lega il programma a una geometria
# sola, ed e' precisamente cio' che questo progetto non fa.
#
# La soglia e' adimensionale apposta. Si scala con la mesh, quindi vale anche
# su una geometria con spigoli dieci volte piu' grandi.
SPIGOLI_DI_TOLLERANZA: int = 3


def spigolo_medio(nodi: np.ndarray, elementi: np.ndarray) -> float:
    """Lunghezza media degli spigoli degli elementi.

    Sugli spigoli e non su tutte le coppie di nodi della mesh: due nodi in
    capo opposto al solido non sono uno spigolo, e la loro distanza non
    corrisponde a nulla che la mesh sappia risolvere.

    ponytail: media su tutte le coppie di nodi **dentro un elemento**, che
    coincide con gli spigoli solo per un simplex -- il tetraedro a quattro
    nodi, l'unico tipo che arriva qui. Su un esaedro conterebbe anche le
    diagonali di faccia e di corpo, alzando la media e allentando la soglia
    dei tre spigoli senza che nulla lo segnali. Non e' un caso raggiungibile
    oggi: l'unico chiamante e' `risolvi_tutti`, e i selettori arrivano solo
    dal percorso as-built (`core/pipeline.py:439`), che e' tetraedrico; il
    percorso esaedrico (`:190`) non li passa. Se un giorno li passasse, la
    via d'uscita e' la tabella delle facce che `core/abaqus.py` gia' tiene,
    da cui ricavare gli spigoli veri per tipo di elemento.
    """
    punti = np.asarray(nodi, dtype=np.float64)
    celle = np.asarray(elementi, dtype=np.int64)
    colonne = celle.shape[1]
    coppie = [(a, b) for a in range(colonne) for b in range(a + 1, colonne)]
    lunghezze = np.concatenate([
        np.linalg.norm(punti[celle[:, a]] - punti[celle[:, b]], axis=1) for a, b in coppie
    ])
    return float(lunghezze.mean())


def risolvi(
    selettore: Selettore,
    nodi: np.ndarray,
    node_sets: dict[str, np.ndarray],
    *,
    nome: str,
    spigolo: float,
) -> np.ndarray:
    """Gli indici di nodo che la regola prende, ordinati e senza ripetizioni.

    `nome` serve ai messaggi d'errore: un rifiuto che non dice quale
    selettore ha sbagliato costringe a cercarlo a mano nello YAML.
    """
    punti = np.asarray(nodi, dtype=np.float64)

    if isinstance(selettore, SelettoreBox):
        minimo = np.asarray(selettore.min, dtype=np.float64)
        massimo = np.asarray(selettore.max, dtype=np.float64)
        presi = np.flatnonzero(np.all((punti >= minimo) & (punti <= massimo), axis=1))
    elif isinstance(selettore, SelettoreSfera):
        centro = np.asarray(selettore.centro, dtype=np.float64)
        presi = np.flatnonzero(np.linalg.norm(punti - centro, axis=1) <= selettore.raggio)
    elif isinstance(selettore, SelettoreNodo):
        punto = np.asarray(selettore.punto, dtype=np.float64)
        distanze = np.linalg.norm(punti - punto, axis=1)
        vincitore = int(np.argmin(distanze))
        limite = SPIGOLI_DI_TOLLERANZA * spigolo
        if distanze[vincitore] > limite:
            raise ValueError(
                f"il selettore '{nome}' chiede il nodo più vicino a "
                f"{tuple(selettore.punto)}, e il più vicino sta a "
                f"{distanze[vincitore]:.1f} mm, oltre i {limite:.1f} mm di "
                f"{SPIGOLI_DI_TOLLERANZA} spigoli medi ({spigolo:.2f} mm). "
                "Un argmin un vincitore ce l'ha sempre, anche a chilometri: "
                "questo non è un indirizzo, è un punto scritto male"
            )
        presi = np.array([vincitore], dtype=np.int64)
    elif isinstance(selettore, SelettoreNset):
        if selettore.nome not in node_sets:
            raise ValueError(
                f"il selettore '{nome}' cita l'insieme '{selettore.nome}', che non "
                f"è fra quelli del deck: {sorted(node_sets)}"
            )
        presi = np.asarray(node_sets[selettore.nome], dtype=np.int64)
    else:  # pragma: no cover - l'unione discriminata non lascia altri casi
        raise TypeError(f"selettore di tipo sconosciuto: {type(selettore)!r}")

    presi = np.unique(presi.astype(np.int64))

    if presi.size == 0:
        raise ValueError(
            f"il selettore '{nome}' risolve zero nodi. Estensione della mesh: "
            f"min {punti.min(axis=0).round(1).tolist()}, "
            f"max {punti.max(axis=0).round(1).tolist()}. "
            "Un carico applicato a nulla non è un carico"
        )
    if presi.size == punti.shape[0]:
        raise ValueError(
            f"il selettore '{nome}' prende tutti i {presi.size} nodi della mesh. "
            "Una risultante spalmata sull'intero solido non è un carico "
            "posizionato, è un peso proprio storto"
        )
    return presi


def risolvi_tutti(
    selettori: dict[str, Selettore],
    nodi: np.ndarray,
    elementi: np.ndarray,
    node_sets: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Tutti i selettori dichiarati, risolti una volta sola sulla stessa mesh.

    Il ritorno anticipato non e' una micro-ottimizzazione: senza di esso
    `spigolo_medio` verrebbe calcolato anche su una corsa che non dichiara
    selettori, cioe' su tutte quelle gia' fatte.
    """
    if not selettori:
        return {}
    spigolo = spigolo_medio(nodi, elementi)
    return {
        nome: risolvi(selettore, nodi, node_sets, nome=nome, spigolo=spigolo)
        for nome, selettore in selettori.items()
    }
