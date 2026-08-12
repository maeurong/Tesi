"""Step 2: isolamento del muro dalla scena.

In Fase 1 la selezione avviene da configurazione; in Fase 3 diventa un clic
nel viewport, ma il core resta lo stesso.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d

from meshrec.core.config import SegmentConfig


def remove_outliers(
    points: np.ndarray, cfg: SegmentConfig
) -> tuple[np.ndarray, dict[str, object]]:
    """Rimozione statistica degli outlier: punti isolati rispetto al vicinato."""
    cloud = o3d.geometry.PointCloud(
        o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    )
    filtered, _ = cloud.remove_statistical_outlier(
        nb_neighbors=cfg.outlier_neighbors, std_ratio=cfg.outlier_std_ratio
    )
    kept = np.ascontiguousarray(np.asarray(filtered.points), dtype=np.float64)
    if len(kept) == 0:
        raise ValueError("la rimozione degli outlier ha svuotato la nuvola: allenta std_ratio")
    return kept, {
        "outliers_removed": int(len(points) - len(kept)),
    }


def crop_box(points: np.ndarray, cfg: SegmentConfig) -> tuple[np.ndarray, dict[str, object]]:
    """Ritaglio a box allineato agli assi, definito da coordinate in configurazione."""
    points = np.asarray(points, dtype=np.float64)
    if cfg.crop_min is None or cfg.crop_max is None:
        return points, {"cropped": False, "points_after": int(len(points))}

    low = np.asarray(cfg.crop_min, dtype=np.float64)
    high = np.asarray(cfg.crop_max, dtype=np.float64)
    if (high <= low).any():
        raise ValueError(f"crop_max {cfg.crop_max} non e maggiore di crop_min {cfg.crop_min} su ogni asse")

    inside = ((points >= low) & (points <= high)).all(axis=1)
    if not inside.any():
        raise ValueError(
            f"nessun punto dentro il box {cfg.crop_min}-{cfg.crop_max}: "
            "controlla che le coordinate siano nelle unita di lavoro (mm) e nel sistema della nuvola"
        )
    return np.ascontiguousarray(points[inside]), {
        "cropped": True,
        "points_after": int(inside.sum()),
    }


def segment_cloud(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 2 completo. `method='auto'` arriva con la segmentazione automatica."""
    if cfg.method == "auto":
        raise NotImplementedError(
            "segmentazione automatica (RANSAC piu DBSCAN) non ancora disponibile: usa method='crop'"
        )

    cleaned, outlier_metrics = remove_outliers(points, cfg)
    cropped, crop_metrics = crop_box(cleaned, cfg)
    metrics: dict[str, object] = {"method": cfg.method, **outlier_metrics, **crop_metrics}
    metrics["points_before"] = int(len(points))
    metrics["points_after"] = int(len(cropped))
    return cropped, metrics
