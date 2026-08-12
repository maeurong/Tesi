"""Tetraedrizzazione della superficie chiusa."""

from __future__ import annotations

import numpy as np
import tetgen


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
