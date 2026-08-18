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


_BOX_FACES = np.array(
    [
        [0, 2, 1], [0, 3, 2],   # z = 0
        [4, 5, 6], [4, 6, 7],   # z = lz
        [0, 1, 5], [0, 5, 4],   # y = 0
        [1, 2, 6], [1, 6, 5],   # x = lx
        [2, 3, 7], [2, 7, 6],   # y = ly
        [3, 0, 4], [3, 4, 7],   # x = 0
    ],
    dtype=np.int64,
)


def box_mesh(size: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    """Parallelepipedo come mesh triangolare chiusa con normali uscenti."""
    lx, ly, lz = (float(value) for value in size)
    vertices = np.array(
        [
            [0.0, 0.0, 0.0], [lx, 0.0, 0.0], [lx, ly, 0.0], [0.0, ly, 0.0],
            [0.0, 0.0, lz], [lx, 0.0, lz], [lx, ly, lz], [0.0, ly, lz],
        ],
        dtype=np.float64,
    )
    return vertices, _BOX_FACES.copy()


def punch_holes(faces: np.ndarray, remove: tuple[int, ...] = (0, 6)) -> np.ndarray:
    """Rimuove i triangoli indicati dalla mesh.

    Il numero di fori dipende dall'adiacenza dei triangoli rimossi, non dal
    loro numero: i due indici di default (0, 6) condividono lo spigolo (1, 2),
    quindi aprono un foro unico a cavallo delle due facce, con 4 spigoli di
    bordo (non due fori separati con tre spigoli ciascuno).
    """
    keep = np.ones(len(faces), dtype=bool)
    keep[list(remove)] = False
    return np.ascontiguousarray(np.asarray(faces)[keep])


def sample_frame_surface(
    prismi: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    spacing: float,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Campiona le superfici di piu' parallelepipedi, ciascuno con la propria origine.

    Serve alle verifiche del prior: un telaio di membrature prismatiche di cui
    si conoscono sezione, asse, lunghezza e volume analitico, cosi' che la
    scomposizione abbia qualcosa che la smentisca. I numeri dei prismi sono del
    banco di prova, mai del codice: `wall` non sa quante membrature aspettarsi.

    I punti che cadono dentro un altro prisma restano: sono le superfici che
    nella realta' si compenetrano alle giunzioni, e toglierli farebbe misurare
    alla scomposizione una geometria piu' pulita di quella che vedra' mai.
    """
    nuvole = []
    for origine, dimensioni in prismi:
        superficie = sample_box_surface(dimensioni, spacing, noise=noise, seed=seed)
        nuvole.append(superficie + np.asarray(origine, dtype=np.float64))
    return np.ascontiguousarray(np.vstack(nuvole), dtype=np.float64)
