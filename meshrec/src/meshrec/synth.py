"""Geometrie sintetiche con soluzione nota, usate da test e verifiche."""

from __future__ import annotations

import numpy as np


def _face_grid(u_length: float, v_length: float, spacing: float) -> tuple[np.ndarray, np.ndarray]:
    """Griglia regolare su una faccia rettangolare u x v."""
    n_u = max(2, int(round(u_length / spacing)) + 1)
    n_v = max(2, int(round(v_length / spacing)) + 1)
    u, v = np.meshgrid(
        np.linspace(0.0, u_length, n_u),
        np.linspace(0.0, v_length, n_v),
        indexing="ij",
    )
    return u.ravel(), v.ravel()


def sample_box_surface(
    size: tuple[float, float, float],
    spacing: float,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Campiona le sei facce di un parallelepipedo con passo `spacing`.

    Il volume racchiuso vale esattamente lx*ly*lz: serve come verita di
    riferimento per validare la pipeline.
    """
    lx, ly, lz = (float(value) for value in size)
    faces: list[np.ndarray] = []

    a, b = _face_grid(lx, ly, spacing)
    for z in (0.0, lz):
        faces.append(np.column_stack([a, b, np.full_like(a, z)]))

    a, b = _face_grid(lx, lz, spacing)
    for y in (0.0, ly):
        faces.append(np.column_stack([a, np.full_like(a, y), b]))

    a, b = _face_grid(ly, lz, spacing)
    for x in (0.0, lx):
        faces.append(np.column_stack([np.full_like(a, x), a, b]))

    points = np.unique(np.round(np.vstack(faces), 9), axis=0)

    if noise > 0.0:
        rng = np.random.default_rng(seed)
        points = points + rng.normal(0.0, noise, points.shape)

    return np.ascontiguousarray(points, dtype=np.float64)
