"""Tetraedrizzazione della superficie chiusa."""

from __future__ import annotations

import time
import warnings

import numpy as np
import tetgen

from meshrec.core.config import TetConfig
from meshrec.core.quality import boundary_edges, inverted_tets, is_watertight


class NotWatertightError(ValueError):
    """La superficie non e chiusa: TetGen non puo tetraedrizzarla."""


class TruncatedRefinementWarning(UserWarning):
    """TetGen ha esaurito i punti di Steiner: la mesh e' troncata, non completa."""


class RefinementFailedError(RuntimeError):
    """Il raffinamento non converge: il vincolo di qualita e' troppo severo."""


class InvertedElementsError(ValueError):
    """La mesh di volume contiene elementi invertiti o degeneri."""


def tetrahedralize(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_ratio: float = 1.1,
    max_volume: float | None = None,
    *,
    max_steiner_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Riempie di tetraedri lineari la superficie chiusa data.

    `min_ratio` e il rapporto raggio-spigolo massimo ammesso (piu basso =
    elementi piu regolari e piu numerosi); `max_volume` limita il volume del
    singolo elemento nelle unita di lavoro; `max_steiner_points` limita i punti
    che TetGen puo' aggiungere per raffinare, e -1 toglie il limite.

    `max_steiner_points` non ha un valore predefinito qui apposta: il
    predefinito della libreria tetgen e' 100000, e lasciarlo implicito e'
    quello che ha prodotto mesh troncate senza che nulla lo segnalasse.
    """
    faces = np.asarray(faces)
    if not is_watertight(faces):
        open_edges = len(boundary_edges(faces))
        raise NotWatertightError(
            f"superficie non chiusa: {open_edges} spigoli di bordo. "
            "TetGen richiede un ingresso manifold chiuso; ripara la superficie "
            "con core.repair.repair_surface prima di tetraedrizzare."
        )

    generator = tetgen.TetGen(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces, dtype=np.int32),
    )
    options: dict[str, object] = {
        "order": 1,
        "minratio": float(min_ratio),
        "steinerleft": int(max_steiner_points),
    }
    if max_volume is not None:
        # Non e' un bug: e' una trappola dell'API di tetgen 0.8.4, per scelta
        # di progetto della libreria. maxvolume da solo e' inerte; il flag
        # booleano fixedvolume=True e' l'interruttore separato che attiva
        # l'opzione -a di TetGen e la rende effettiva.
        options["maxvolume"] = float(max_volume)
        options["fixedvolume"] = True

    # tetgen 0.8.4 restituisce (node, elem, attributes, triface_markers): teniamo solo i primi due.
    try:
        nodes, tets, *_ = generator.tetrahedralize(**options)
    except RuntimeError as errore:
        # L'errore grezzo della libreria ("Internal TetGen error within
        # `split_subface`") non dice nulla a chi lo riceve. Nella pratica arriva
        # quando il vincolo raggio-spigolo e' troppo severo per la geometria: il
        # raffinamento non converge e TetGen si arrende su una configurazione
        # degenere. Sul muro di riferimento accade con min_ratio fino a 1.6, non
        # con 1.8, quindi il margine e' sottile e su un'altra geometria puo' non
        # bastare.
        raise RefinementFailedError(
            f"TetGen si e' interrotto con min_ratio={min_ratio}: "
            "il vincolo raggio-spigolo puo' essere troppo severo per questa "
            "geometria, il raffinamento non converge. Alza min_ratio (valori piu "
            "alti = elementi meno regolari ma raffinamento che termina) e riprova. "
            f"Errore originale di TetGen: {errore}"
        ) from errore
    return (
        np.ascontiguousarray(nodes, dtype=np.float64),
        np.ascontiguousarray(tets, dtype=np.int64),
    )


def tetrahedralize_with_metrics(
    vertices: np.ndarray, faces: np.ndarray, cfg: TetConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 9 completo: tetraedrizza, cronometra e rifiuta gli elementi invertiti."""
    start = time.perf_counter()
    nodes, tets = tetrahedralize(
        vertices, faces, cfg.min_ratio, cfg.max_volume, max_steiner_points=cfg.max_steiner_points
    )
    seconds = time.perf_counter() - start

    inverted = inverted_tets(nodes, tets)
    if len(inverted) > 0:
        raise InvertedElementsError(
            f"{len(inverted)} tetraedri invertiti o degeneri su {len(tets)}: "
            "risultato inutilizzabile per l'analisi, non un avviso"
        )

    # TetGen non dichiara di aver esaurito il budget di punti di Steiner. L'indizio
    # utilizzabile e' il conteggio: i nodi che escono in piu rispetto ai vertici
    # della superficie sono i punti aggiunti, e quando il budget si esaurisce
    # eguagliano il tetto esattamente, mai per difetto. Verificato sul muro reale a
    # sei tetti diversi (25000, 50000, 100000, 120000, 150000, 175000): i punti
    # aggiunti sono risultati ogni volta pari al tetto in modo esatto.
    steiner_points = int(len(nodes) - len(np.asarray(vertices)))
    saturated = cfg.max_steiner_points > 0 and steiner_points >= cfg.max_steiner_points
    if saturated:
        warnings.warn(
            f"TetGen ha esaurito i {cfg.max_steiner_points} punti di Steiner concessi: "
            "il raffinamento e' stato troncato e la mesh non rispetta i vincoli di "
            "qualita richiesti. Alza max_steiner_points o portalo a -1.",
            TruncatedRefinementWarning,
            stacklevel=2,
        )

    metrics = {
        "nodes": int(len(nodes)),
        "tets": int(len(tets)),
        "seconds": float(seconds),
        "element": cfg.element,
        "min_ratio": cfg.min_ratio,
        "max_volume": cfg.max_volume,
        "max_steiner_points": cfg.max_steiner_points,
        "steiner_points": steiner_points,
        "steiner_saturated": bool(saturated),
    }
    return nodes, tets, metrics
