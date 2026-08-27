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


def elliptical_annulus_mesh(
    inner: tuple[float, float],
    outer: tuple[float, float],
    thickness: float,
    segments: int,
    layers: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Quarto di anello ellittico estruso, come mesh triangolare chiusa.

    E' la geometria del benchmark NAFEMS LE10 (vedi
    `docs/validazione/benchmark-nafems.md` §3): due ellissi concentriche di
    semiassi diversi, il settore con `x >= 0` e `y >= 0`, estruso in z da 0 a
    `thickness`. `inner` e `outer` sono le coppie di semiassi `(a, b)`.

    Il contorno e' **poligonale**, non curvo: TetGen riceve triangoli piani, e
    il volume del solido prodotto e' quello del poligono inscritto, che sta
    sotto quello dell'ellisse. Lo scarto va come `1/segments^2` e va
    dichiarato, non trascurato -- il confronto con LE10 e' su una tensione, che
    dipende dalla geometria del bordo.

    L'orientamento non e' costruito a mano faccia per faccia ma **imposto sul
    risultato**, dal segno del volume racchiuso: costruire dodici gruppi di
    triangoli con il verso giusto a memoria e' il genere di cosa che sembra
    corretta e non lo e', e il segno del volume e' l'oracolo che lo dice.
    """
    a_i, b_i = (float(v) for v in inner)
    a_o, b_o = (float(v) for v in outer)
    h = float(thickness)
    if segments < 3:
        raise ValueError(f"{segments} suddivisioni: due punti non fanno un arco, ne servono almeno tre")
    if h <= 0.0:
        raise ValueError(f"spessore {h}: un solido estruso ha spessore positivo")
    if a_i >= a_o or b_i >= b_o:
        raise ValueError(
            f"ellisse interna ({a_i}, {b_i}) non contenuta in quella esterna ({a_o}, {b_o}): "
            "la superficie si autointersecherebbe"
        )

    if layers < 1:
        raise ValueError(f"{layers} strati: l'estrusione ne vuole almeno uno")

    t = np.linspace(0.0, np.pi / 2.0, segments + 1)
    n = len(t)
    interno = np.column_stack([a_i * np.cos(t), b_i * np.sin(t)])
    esterno = np.column_stack([a_o * np.cos(t), b_o * np.sin(t)])
    quote = np.linspace(0.0, h, layers + 1)

    def anello(punti: np.ndarray, quota: float) -> np.ndarray:
        return np.column_stack([punti, np.full(len(punti), quota)])

    # Per ogni quota, prima l'anello interno poi quello esterno. Gli strati
    # servono a due cose: la qualita' del maglio, e -- con `layers` pari -- a
    # mettere davvero dei nodi sul **piano di mezzeria**, che il vincolo di
    # LE10 richiede e che un'estrusione a due sole quote non avrebbe.
    vertici = np.vstack(
        [blocco for z in quote for blocco in (anello(interno, z), anello(esterno, z))]
    )

    def ib(j: int) -> int:
        return j * 2 * n

    def ob(j: int) -> int:
        return j * 2 * n + n

    quad: list[tuple[int, int, int, int]] = []
    for k in range(n - 1):
        quad.append((ib(0) + k, ib(0) + k + 1, ob(0) + k + 1, ob(0) + k))
        alto = layers
        quad.append((ib(alto) + k, ob(alto) + k, ob(alto) + k + 1, ib(alto) + k + 1))
    for j in range(layers):
        for k in range(n - 1):
            # I due fianchi hanno verso **opposto** fra loro: la normale uscente
            # del fianco interno punta dentro il foro, quella dell'esterno punta
            # fuori. Scriverli con lo stesso avvolgimento e' l'errore che la
            # prima stesura ha fatto, e che `is_watertight` non vede -- conta
            # gli spigoli, non l'orientamento.
            quad.append((ib(j) + k, ib(j + 1) + k, ib(j + 1) + k + 1, ib(j) + k + 1))
            quad.append((ob(j) + k, ob(j) + k + 1, ob(j + 1) + k + 1, ob(j + 1) + k))
        # Le due facce radiali piane: il taglio a y = 0 e quello a x = 0.
        quad.append((ib(j), ob(j), ob(j + 1), ib(j + 1)))
        quad.append((ib(j) + n - 1, ib(j + 1) + n - 1, ob(j + 1) + n - 1, ob(j) + n - 1))

    facce = np.array(
        [tri for a, b, c, d in quad for tri in ((a, b, c), (a, c, d))], dtype=np.int64
    )

    from meshrec.core.quality import is_oriented, is_watertight, mesh_volume

    if not is_watertight(facce):
        raise ValueError("superficie non chiusa: la costruzione delle facce ha un difetto")
    if not is_oriented(facce):
        raise ValueError(
            "superficie chiusa ma non orientata: uno spigolo è percorso nello stesso "
            "verso da due facce, quindi le normali non sono tutte uscenti"
        )
    if mesh_volume(vertici, facce) < 0.0:
        facce = np.ascontiguousarray(facce[:, [0, 2, 1]])
    return np.ascontiguousarray(vertici), facce


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
    for indice, (origine, dimensioni) in enumerate(prismi):
        # seed distinto per prisma: con lo stesso seed per tutti, noise > 0
        # darebbe a ogni membratura la stessa sequenza di rumore invece di
        # sequenze indipendenti.
        superficie = sample_box_surface(dimensioni, spacing, noise=noise, seed=seed + indice)
        nuvole.append(superficie + np.asarray(origine, dtype=np.float64))
    return np.ascontiguousarray(np.vstack(nuvole), dtype=np.float64)
