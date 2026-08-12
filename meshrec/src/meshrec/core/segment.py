"""Step 2: isolamento del muro dalla scena.

In Fase 1 la selezione avviene da configurazione; in Fase 3 diventa un clic
nel viewport, ma il core resta lo stesso.
"""

from __future__ import annotations

import ctypes
import os

import numpy as np
import open3d as o3d

from meshrec.core.config import SegmentConfig

# Il RANSAC di Open3D (segment_plane) e' parallelo via OpenMP: con piu thread
# l'ordine di scoperta del piano migliore dipende dallo scheduling, quindi
# o3d.utility.random.seed da solo NON basta a rendere l'estrazione riproducibile
# (verificato: due run della stessa config davano un numero diverso di punti
# residui). Stesso principio gia' in uso per Poisson (SurfaceConfig.poisson_n_threads,
# default 1), qui applicato all'unico punto dove Open3D non offre un parametro
# esplicito per il numero di thread.
#
# La sola variabile d'ambiente OMP_NUM_THREADS letta all'import non basta: se
# un'altra libreria ha gia' fatto partire il pool di thread di OpenMP nello
# stesso processo (verificato con l'intera `pytest`, dove test_pipeline.py
# gira prima di test_segment.py), la lettura tardiva dell'env var arriva
# troppo tardi. Va quindi richiamato anche a runtime, subito prima del RANSAC.
# ponytail: il nome della dll (vcomp140, runtime OpenMP di MSVC) e' specifico
# a Windows/questo wheel di Open3D (verificato: risolve anche il caso in cui
# `pytest` esegue prima test_pipeline.py, che scalda il pool con piu thread).
# Su un runtime diverso il pin a runtime fallisce silenziosamente e resta solo
# l'env var, affidabile quando segment_cloud e' la prima operazione Open3D del
# processo (vero per l'uso reale via CLI e per `pytest tests/test_segment.py`
# da solo).
os.environ.setdefault("OMP_NUM_THREADS", "1")


def _pin_openmp_to_one_thread() -> None:
    """Rende un solo thread OpenMP anche se il pool era gia' partito con piu' thread."""
    if os.name == "nt":
        try:
            ctypes.CDLL("vcomp140.dll").omp_set_num_threads(1)
        except OSError:
            pass


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


def _as_cloud(points: np.ndarray) -> o3d.geometry.PointCloud:
    return o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))


def extract_planes(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[list[np.ndarray], np.ndarray, dict[str, object]]:
    """Estrazione iterativa di piani con RANSAC: pavimento e pareti via dal residuo.

    Il seme fissato rende l'estrazione riproducibile: senza, la stessa
    configurazione produrrebbe segmentazioni diverse a ogni esecuzione.
    """
    _pin_openmp_to_one_thread()
    o3d.utility.random.seed(0)
    threshold = cfg.plane_distance_factor * spacing
    minimum = max(3, int(cfg.plane_min_points_ratio * len(points)))

    planes: list[np.ndarray] = []
    residual = np.asarray(points, dtype=np.float64)
    for _ in range(cfg.plane_max_count):
        if len(residual) < minimum:
            break
        _, inliers = _as_cloud(residual).segment_plane(
            distance_threshold=threshold, ransac_n=3, num_iterations=1000
        )
        if len(inliers) < minimum:
            # sotto questa soglia il piano e' rumore adattato, non una superficie reale
            break
        mask = np.zeros(len(residual), dtype=bool)
        mask[np.asarray(inliers, dtype=np.int64)] = True
        planes.append(np.ascontiguousarray(residual[mask]))
        residual = np.ascontiguousarray(residual[~mask])

    metrics = {
        "planes_found": len(planes),
        "plane_distance": float(threshold),
        "plane_points": [int(len(plane)) for plane in planes],
        "residual_points": int(len(residual)),
    }
    return planes, residual, metrics


def cluster(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[list[np.ndarray], dict[str, object]]:
    """DBSCAN sul residuo. I gruppi tornano ordinati per numerosita decrescente."""
    eps = cfg.cluster_eps_factor * spacing
    labels = np.asarray(
        _as_cloud(points).cluster_dbscan(eps=eps, min_points=cfg.cluster_min_points)
    )
    groups = [
        np.ascontiguousarray(np.asarray(points)[labels == label])
        for label in np.unique(labels[labels >= 0])
    ]
    groups.sort(key=len, reverse=True)
    metrics = {
        "clusters_found": len(groups),
        "cluster_eps": float(eps),
        "cluster_sizes": [int(len(group)) for group in groups],
        "noise_points": int((labels < 0).sum()),
    }
    return groups, metrics


def _plane_metrics(points: np.ndarray) -> dict[str, object]:
    """Planarita e spessore del cluster scelto, lungo la sua direzione piu sottile."""
    centred = np.asarray(points, dtype=np.float64) - np.mean(points, axis=0)
    _, _, principal = np.linalg.svd(centred, full_matrices=False)
    projection = centred @ principal[2]
    return {
        "planarity_rms": float(np.sqrt(np.mean(projection**2))),
        "thickness": float(np.ptp(projection)),
        "normal": principal[2].tolist(),
    }


def segment_cloud(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 2 completo. `method='auto'` isola il muro con RANSAC piu DBSCAN."""
    cleaned, outlier_metrics = remove_outliers(points, cfg)
    cropped, crop_metrics = crop_box(cleaned, cfg)
    metrics: dict[str, object] = {"method": cfg.method, **outlier_metrics, **crop_metrics}

    if cfg.method == "auto":
        _, residual, plane_metrics = extract_planes(cropped, cfg, spacing)
        groups, cluster_metrics = cluster(residual, cfg, spacing)
        metrics.update(plane_metrics)
        metrics.update(cluster_metrics)
        if cfg.cluster_index >= len(groups):
            raise ValueError(
                f"cluster_index={cfg.cluster_index} ma sono stati trovati {len(groups)} cluster: "
                "allenta cluster_eps_factor o abbassa cluster_min_points"
            )
        chosen = groups[cfg.cluster_index]
        metrics["cluster_points"] = int(len(chosen))
        metrics.update(_plane_metrics(chosen))
        cropped = chosen

    metrics["points_before"] = int(len(points))
    metrics["points_after"] = int(len(cropped))
    return cropped, metrics
