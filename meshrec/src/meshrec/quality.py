"""Metriche topologiche e geometriche su mesh triangolari e tetraedriche."""

from __future__ import annotations

import numpy as np


def _edge_counts(faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spigoli unici (ordinati per indice) e numero di triangoli che li usano."""
    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.sort(edges, axis=1)
    return np.unique(edges, axis=0, return_counts=True)


def boundary_edges(faces: np.ndarray) -> np.ndarray:
    """Spigoli appartenenti a un solo triangolo: bordi aperti della mesh."""
    unique, counts = _edge_counts(np.asarray(faces))
    return unique[counts == 1]


def is_watertight(faces: np.ndarray) -> bool:
    """Vero se ogni spigolo e condiviso da esattamente due triangoli."""
    _, counts = _edge_counts(np.asarray(faces))
    return bool((counts == 2).all())


def mesh_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Volume racchiuso, con segno positivo se le normali sono uscenti.

    Teorema della divergenza applicato ai tetraedri origine-triangolo.
    """
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def tet_volumes(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni tetraedro; negativo se l'elemento e invertito."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a, b, c, d = n[t[:, 0]], n[t[:, 1]], n[t[:, 2]], n[t[:, 3]]
    return np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a)) / 6.0


def inverted_tets(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Indici dei tetraedri degeneri o invertiti (volume non positivo)."""
    return np.flatnonzero(tet_volumes(nodes, tets) <= 0.0)
