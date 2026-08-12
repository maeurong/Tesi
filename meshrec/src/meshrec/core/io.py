"""Step 1: lettura della nuvola, filtro dei non finiti, spaziatura e scala.

Il fattore di scala e' l'unica difesa contro un errore di unita, che non
produce alcun segnale a valle e falsa le tensioni di ordini di grandezza.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

from meshrec.core.config import InputConfig


class ScaleError(ValueError):
    """L'ingombro della nuvola non corrisponde alle dimensioni reali dichiarate."""


def read_cloud(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Legge .pcd/.ply/.xyz. Le normali sono restituite solo se presenti nel file."""
    cloud = o3d.io.read_point_cloud(str(path))
    points = np.asarray(cloud.points, dtype=np.float64)
    if len(points) == 0:
        raise ValueError(f"nessun punto letto da '{path}': file assente, vuoto o formato non riconosciuto")
    normals = np.asarray(cloud.normals, dtype=np.float64) if cloud.has_normals() else None
    return points, normals


def write_cloud(path: Path, points: np.ndarray, normals: np.ndarray | None = None) -> None:
    """Scrive un artefatto di nuvola, con le normali se disponibili."""
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))
    if normals is not None:
        cloud.normals = o3d.utility.Vector3dVector(np.asarray(normals, dtype=np.float64))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    o3d.io.write_point_cloud(str(path), cloud)


def mean_spacing(points: np.ndarray, sample: int, seed: int) -> float:
    """Distanza media al vicino piu prossimo, su un campione casuale."""
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        raise ValueError("servono almeno due punti per stimare la spaziatura")
    rng = np.random.default_rng(seed)
    size = min(sample, len(points))
    chosen = points[rng.choice(len(points), size=size, replace=False)]
    distances, _ = cKDTree(points).query(chosen, k=2)
    return float(distances[:, 1].mean())


def load_cloud(cfg: InputConfig) -> tuple[np.ndarray, dict[str, object]]:
    """Legge la nuvola, la porta nelle unita di lavoro e ne misura l'ingombro."""
    points, _ = read_cloud(cfg.path)
    points_read = len(points)

    finite = np.isfinite(points).all(axis=1)
    points = np.ascontiguousarray(points[finite])
    points_dropped = points_read - len(points)
    if len(points) == 0:
        raise ValueError(f"tutti i {points_read} punti letti hanno coordinate non finite")
    if len(points) > cfg.max_points:
        raise ValueError(
            f"{len(points)} punti oltre il limite max_points={cfg.max_points}: "
            "alza il limite o riduci la nuvola a monte"
        )

    points = points * cfg.scale
    bbox_min = points.min(axis=0)
    bbox_max = points.max(axis=0)
    extent = bbox_max - bbox_min

    size_check = "non richiesto"
    if cfg.expected_size is not None:
        expected = np.sort(np.asarray(cfg.expected_size, dtype=np.float64))
        measured = np.sort(extent)
        relative = np.abs(measured - expected) / expected
        if (relative > cfg.size_tolerance).any():
            raise ScaleError(
                f"ingombro misurato {np.round(measured, 1).tolist()} mm contro "
                f"{np.round(expected, 1).tolist()} mm attesi, scarto relativo "
                f"{np.round(relative, 3).tolist()} oltre la tolleranza {cfg.size_tolerance}: "
                "il fattore di scala e' probabilmente sbagliato"
            )
        size_check = "ok"

    metrics = {
        "points_read": points_read,
        "points_dropped": points_dropped,
        "points_kept": len(points),
        "scale": cfg.scale,
        "spacing": mean_spacing(points, cfg.spacing_sample, cfg.seed),
        "extent": extent.tolist(),
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "size_check": size_check,
    }
    return points, metrics
