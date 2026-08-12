"""Tetraedrizzazione della superficie chiusa."""

from __future__ import annotations

import time

import numpy as np
import tetgen

from meshrec.core.config import TetConfig
from meshrec.core.quality import boundary_edges, inverted_tets, is_watertight


class NotWatertightError(ValueError):
    """La superficie non e chiusa: TetGen non puo tetraedrizzarla."""


class InvertedElementsError(ValueError):
    """La mesh di volume contiene elementi invertiti o degeneri."""


def tetrahedralize(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_ratio: float = 1.1,
    max_volume: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Riempie di tetraedri lineari la superficie chiusa data.

    `min_ratio` e il rapporto raggio-spigolo massimo ammesso (piu basso =
    elementi piu regolari e piu numerosi); `max_volume` limita il volume del
    singolo elemento nelle unita di lavoro.
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
    options: dict[str, object] = {"order": 1, "minratio": float(min_ratio)}
    if max_volume is not None:
        # Non e' un bug: e' una trappola dell'API di tetgen 0.8.4, per scelta
        # di progetto della libreria. maxvolume da solo e' inerte; il flag
        # booleano fixedvolume=True e' l'interruttore separato che attiva
        # l'opzione -a di TetGen e la rende effettiva.
        options["maxvolume"] = float(max_volume)
        options["fixedvolume"] = True

    # tetgen 0.8.4 restituisce (node, elem, attributes, triface_markers): teniamo solo i primi due.
    nodes, tets, *_ = generator.tetrahedralize(**options)
    return (
        np.ascontiguousarray(nodes, dtype=np.float64),
        np.ascontiguousarray(tets, dtype=np.int64),
    )


def tetrahedralize_with_metrics(
    vertices: np.ndarray, faces: np.ndarray, cfg: TetConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 9 completo: tetraedrizza, cronometra e rifiuta gli elementi invertiti."""
    start = time.perf_counter()
    nodes, tets = tetrahedralize(vertices, faces, cfg.min_ratio, cfg.max_volume)
    seconds = time.perf_counter() - start

    inverted = inverted_tets(nodes, tets)
    if len(inverted) > 0:
        raise InvertedElementsError(
            f"{len(inverted)} tetraedri invertiti o degeneri su {len(tets)}: "
            "risultato inutilizzabile per l'analisi, non un avviso"
        )

    metrics = {
        "nodes": int(len(nodes)),
        "tets": int(len(tets)),
        "seconds": float(seconds),
        "element": cfg.element,
        "min_ratio": cfg.min_ratio,
        "max_volume": cfg.max_volume,
    }
    return nodes, tets, metrics
