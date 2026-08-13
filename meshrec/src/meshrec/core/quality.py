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


_TET_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
# Le sei combinazioni di due indici su quattro: valgono sia come coppie di facce
# (angoli diedri) sia come spigoli del tetraedro (rapporto d'aspetto).
_FACE_PAIRS = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def triangle_aspect_ratios(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei triangoli: 1 per l'equilatero, cresce coi degeneri."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    sides = np.stack(
        [
            np.linalg.norm(b - a, axis=1),
            np.linalg.norm(c - b, axis=1),
            np.linalg.norm(a - c, axis=1),
        ],
        axis=1,
    )
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    inradius = np.where(sides.sum(axis=1) > 0.0, 2.0 * area / sides.sum(axis=1), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sides.max(axis=1) / (2.0 * np.sqrt(3.0) * inradius)
    return np.where(np.isfinite(ratio), ratio, np.inf)


def _tet_face_normals(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Normali uscenti delle quattro facce di ogni tetraedro, forma (n, 4, 3)."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    normals = np.empty((len(t), 4, 3), dtype=np.float64)
    for index, (i, j, k) in enumerate(_TET_FACES):
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        face = np.cross(q - p, r - p)
        length = np.linalg.norm(face, axis=1, keepdims=True)
        normals[:, index] = np.divide(face, length, out=np.zeros_like(face), where=length > 0.0)
    return normals


def min_dihedral_angles(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Angolo diedro minimo di ogni tetraedro, in gradi.

    Un tetraedro regolare vale arccos(1/3) = 70,5288 gradi; valori vicini a
    zero indicano elementi schiacciati, numericamente inaffidabili.
    """
    normals = _tet_face_normals(nodes, tets)
    angles = np.empty((len(normals), len(_FACE_PAIRS)), dtype=np.float64)
    for index, (i, j) in enumerate(_FACE_PAIRS):
        cosine = np.clip(np.einsum("ij,ij->i", normals[:, i], normals[:, j]), -1.0, 1.0)
        angles[:, index] = 180.0 - np.degrees(np.arccos(cosine))
    return angles.min(axis=1)


def tet_aspect_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei tetraedri: 1 per il regolare, cresce coi degeneri."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    volume = np.abs(tet_volumes(n, t))
    area = np.zeros(len(t), dtype=np.float64)
    for i, j, k in _TET_FACES:
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        area += np.linalg.norm(np.cross(q - p, r - p), axis=1) / 2.0
    longest = np.max(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in _FACE_PAIRS], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        inradius = 3.0 * volume / area
        ratio = longest / (inradius * 2.0 * np.sqrt(6.0))
    return np.where(np.isfinite(ratio) & (inradius > 0.0), ratio, np.inf)


def radius_edge_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Raggio della sfera circoscritta diviso lo spigolo piu corto.

    E' la grandezza che TetGen limita con `minratio`: vale sqrt(6)/4 = 0,6124
    per il tetraedro regolare e cresce sugli elementi mal condizionati. Serve a
    verificare sul maglio prodotto un vincolo che finora era solo richiesto: dei
    parametri di TetConfig, `max_steiner_points` e `max_volume` sono controllati
    sul risultato, `min_ratio` no.

    Il centro della sfera circoscritta si ottiene risolvendo il sistema lineare
    che impone uguale distanza dai quattro vertici. Su un tetraedro degenere la
    matrice e singolare: il risultato e' infinito e non un'eccezione, cosi la
    metrica resta calcolabile su un maglio che contiene qualche elemento piatto.
    """
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a = n[t[:, 0]]
    spigoli = np.stack([n[t[:, i]] - a for i in (1, 2, 3)], axis=1)

    # 2 (p - a) . d = |p - a|^2 per ciascuno dei tre vertici restanti, con d il
    # centro riferito ad a.
    matrice = 2.0 * spigoli
    termine = np.einsum("ijk,ijk->ij", spigoli, spigoli)

    determinante = np.linalg.det(matrice)
    regolare = np.abs(determinante) > 0.0
    centri = np.zeros((len(t), 3), dtype=np.float64)
    if regolare.any():
        # Il termine noto porta un asse finale esplicito (colonna singola):
        # senza, quando il numero di tetraedri regolari coincide con 1 o con 3
        # (la dimensione della matrice), np.linalg.solve confonde il lotto con
        # un'unica matrice 3x3 condivisa invece di risolvere un sistema per
        # tetraedro, e sbaglia in silenzio anziche' sollevare un errore.
        centri[regolare] = np.linalg.solve(
            matrice[regolare], termine[regolare, :, None]
        )[..., 0]
    raggio = np.linalg.norm(centri, axis=1)

    piu_corto = np.min(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in _FACE_PAIRS], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        rapporto = raggio / piu_corto
    return np.where(regolare & (piu_corto > 0.0), rapporto, np.inf)


def _distribution(values: np.ndarray) -> dict[str, float | int | None]:
    """Riassunto di una distribuzione, per il report e per metrics.json.

    I valori non finiti sono esclusi dalle statistiche e contati in
    `non_finite`, perche' quanti se ne sono scartati e' parte del risultato: un
    riassunto calcolato su meta dei valori senza dirlo e' un numero plausibile e
    non verificabile.

    Quando non resta alcun valore finito le voci valgono `null` e non `NaN`:
    `NaN` non fa parte di JSON, e un `metrics.json` che lo contiene smette di
    essere leggibile da qualunque lettore che non sia quello di Python.
    """
    all_values = np.asarray(values, dtype=np.float64)
    finite = all_values[np.isfinite(all_values)]
    summary: dict[str, float | int | None] = {"non_finite": int(len(all_values) - len(finite))}
    if len(finite) == 0:
        return {"min": None, "median": None, "mean": None, "max": None, **summary}
    return {
        "min": float(finite.min()),
        "median": float(np.median(finite)),
        "mean": float(finite.mean()),
        "max": float(finite.max()),
        **summary,
    }


def surface_metrics(vertices: np.ndarray, faces: np.ndarray) -> dict[str, object]:
    """Step 7: chiusura, bordi, area, volume racchiuso, aspetto dei triangoli."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return {
        "vertices": int(len(v)),
        "triangles": int(len(f)),
        "watertight": is_watertight(f),
        "boundary_edges": int(len(boundary_edges(f))),
        "area": float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2.0),
        "volume": mesh_volume(v, f),
        "aspect_ratio": _distribution(triangle_aspect_ratios(v, f)),
    }


def volume_metrics(nodes: np.ndarray, tets: np.ndarray) -> dict[str, object]:
    """Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi, raggio-spigolo."""
    volumes = tet_volumes(nodes, tets)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "tets": int(len(np.asarray(tets))),
        "inverted": int(len(inverted_tets(nodes, tets))),
        "total_volume": float(volumes.sum()),
        "element_volume": _distribution(volumes),
        "min_dihedral_deg": _distribution(min_dihedral_angles(nodes, tets)),
        "aspect_ratio": _distribution(tet_aspect_ratios(nodes, tets)),
        "radius_edge_ratio": _distribution(radius_edge_ratios(nodes, tets)),
    }


def geometric_error(
    vertices: np.ndarray, faces: np.ndarray, cloud: np.ndarray
) -> dict[str, object]:
    """Errore geometrico bidirezionale fra superficie ricostruita e nuvola sorgente.

    Il campionamento della superficie e' delegato a PyMeshLab: una distanza
    calcolata sui soli vertici sovrastimerebbe l'errore dove i triangoli sono
    grandi, e la fedelta geometrica e' una delle metriche riportate in tesi.
    """
    import pymeshlab

    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(
        pymeshlab.Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces)), "mesh"
    )
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(cloud, dtype=np.float64)), "cloud")

    cloud_to_mesh = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=1, targetmesh=0))
    mesh_to_cloud = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=0, targetmesh=1))
    for name, result in (("cloud_to_mesh", cloud_to_mesh), ("mesh_to_cloud", mesh_to_cloud)):
        missing = {"max", "RMS"} - set(result)
        if missing:
            raise RuntimeError(f"get_hausdorff_distance non ha restituito {missing} per {name}")

    return {
        "cloud_to_mesh": cloud_to_mesh,
        "mesh_to_cloud": mesh_to_cloud,
        "hausdorff": max(float(cloud_to_mesh["max"]), float(mesh_to_cloud["max"])),
    }


def thickness(points: np.ndarray, bin_width: float) -> dict[str, object]:
    """Spessore come distanza fra i due modi lungo la direzione di minore estensione.

    Si applica indifferentemente a una nuvola e ai vertici di una superficie:
    e' il requisito che rende la misura verificabile, perche' il valore letto
    sulla ricostruzione si confronta con quello letto sulla sorgente.

    L'ingombro non risponde alla stessa domanda. Sul ritaglio di lab_frame
    l'estensione lungo lo spessore vale 231 mm mentre le due facce del muro
    distano 176 mm: il rumore e gli sguinci allargano la scatola, non il muro.

    La divisione fra i due modi cade al punto medio dell'estensione, che per
    una lastra sta fra le due facce: nessuna finestra da tarare. Se fra i due
    modi non c'e' una valle la distribuzione non e' bimodale, la misura non
    e' valida e `bimodal` lo dichiara invece di restituire un numero comunque:
    su una nuvola piena i due massimi cadrebbero comunque da qualche parte, e
    la loro distanza non sarebbe uno spessore.
    """
    values = np.asarray(points, dtype=np.float64)
    centred = values - values.mean(axis=0)
    # eigh su una 3x3: costo indipendente dal numero di punti, al contrario
    # di una SVD sulla matrice intera, che su 6,3 milioni di punti materializza
    # una U da oltre 150 MB per restituire le stesse tre direzioni.
    _, directions = np.linalg.eigh(centred.T @ centred)
    projected = centred @ directions
    extents = np.ptp(projected, axis=0)
    axis = int(np.argmin(extents))

    along = projected[:, axis]
    edges = np.arange(along.min(), along.max() + bin_width, bin_width)
    counts, _ = np.histogram(along, bins=edges)
    centres = (edges[:-1] + edges[1:]) / 2.0
    split = len(counts) // 2

    lower = int(np.argmax(counts[:split]))
    upper = split + int(np.argmax(counts[split:]))
    # La valle fra i due modi deve essere almeno mezza vuota rispetto al modo
    # piu basso. Non e' una soglia tarata ma un'affermazione qualitativa: se
    # fra i due massimi il conteggio non cala, non ci sono due facce.
    valley = int(counts[lower + 1 : upper].min()) if upper > lower + 1 else int(counts[lower])
    bimodal = bool(valley < 0.5 * min(counts[lower], counts[upper]))

    return {
        "thickness": float(centres[upper] - centres[lower]),
        "axis": axis,
        "extent": float(extents[axis]),
        "bimodal": bimodal,
    }
