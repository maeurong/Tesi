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
    edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    longest = np.max(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in edges], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        inradius = 3.0 * volume / area
        ratio = longest / (inradius * 2.0 * np.sqrt(6.0))
    return np.where(np.isfinite(ratio) & (inradius > 0.0), ratio, np.inf)


def _distribution(values: np.ndarray) -> dict[str, float]:
    """Riassunto di una distribuzione, per il report e per metrics.json."""
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if len(finite) == 0:
        return {"min": float("nan"), "median": float("nan"), "mean": float("nan"), "max": float("nan")}
    return {
        "min": float(finite.min()),
        "median": float(np.median(finite)),
        "mean": float(finite.mean()),
        "max": float(finite.max()),
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
    """Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi."""
    volumes = tet_volumes(nodes, tets)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "tets": int(len(np.asarray(tets))),
        "inverted": int(len(inverted_tets(nodes, tets))),
        "total_volume": float(volumes.sum()),
        "element_volume": _distribution(volumes),
        "min_dihedral_deg": _distribution(min_dihedral_angles(nodes, tets)),
        "aspect_ratio": _distribution(tet_aspect_ratios(nodes, tets)),
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
