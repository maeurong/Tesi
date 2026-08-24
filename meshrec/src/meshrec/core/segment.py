"""Step 2: isolamento del muro dalla scena.

In Fase 1 la selezione avviene da configurazione; in Fase 3 diventa un clic
nel viewport, ma il core resta lo stesso.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d

from meshrec.core.config import SegmentConfig

# Il RANSAC di segment_plane e' parallelo via OpenMP: con piu thread l'ordine di
# scoperta del piano migliore dipende dallo scheduling, quindi
# o3d.utility.random.seed da solo non basta a rendere l'estrazione riproducibile.
# Il numero di thread e' fissato in meshrec/__init__.py, che Python esegue prima
# di questo modulo e quindi prima che Open3D avvii il proprio pool: vedi il
# commento la' per il motivo per cui non puo' stare qui.


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
            "controlla che le coordinate siano nelle unità di lavoro (mm) e nel sistema della nuvola"
        )
    return np.ascontiguousarray(points[inside]), {
        "cropped": True,
        "points_after": int(inside.sum()),
        **_cosa_toglie_il_box(points, low, high, inside),
    }


def _cosa_toglie_il_box(
    points: np.ndarray, low: np.ndarray, high: np.ndarray, inside: np.ndarray
) -> dict[str, object]:
    """Quanto il box ha tolto, e da quale faccia.

    `points_before` e `points_after` c'erano gia', ma la loro differenza dice
    solo un numero: non dice che il ritaglio ha portato via un pezzo di
    struttura. Su lab_crop toglieva il 30,8% della nuvola -- fra cui tutta la
    base del portale, i due appoggi -- e a video non compariva niente che lo
    facesse sospettare. Le facce lo dicono: 1.944.686 punti sotto la faccia Z
    e' un piano di taglio che ha incontrato qualcosa, non una rifinitura dei
    bordi.

    Un punto puo' uscire da piu' facce, quindi la somma delle facce puo'
    superare il totale tolto: sono sei domande separate («quanti punti stanno
    sotto questa faccia»), non una ripartizione.

    Le facce che non tolgono niente non compaiono: sei zeri sono rumore che
    nasconde l'unica riga che conta.
    """
    tolti = int((~inside).sum())
    per_faccia: dict[str, int] = {}
    for asse, nome in enumerate("xyz"):
        sotto = int((points[:, asse] < low[asse]).sum())
        sopra = int((points[:, asse] > high[asse]).sum())
        if sotto:
            per_faccia[f"sotto_{nome}"] = sotto
        if sopra:
            per_faccia[f"sopra_{nome}"] = sopra

    metriche: dict[str, object] = {
        "cropped_points": tolti,
        # Sul totale in ingresso al ritaglio, che e' la nuvola gia' ripulita
        # dagli outlier: e' il denominatore su cui il box ha davvero agito.
        "cropped_fraction": float(tolti / len(points)) if len(points) else 0.0,
    }
    # Un box che non toglie niente non lascia un dizionario vuoto a video.
    if per_faccia:
        metriche["cropped_by_face"] = per_faccia
    return metriche


def _as_cloud(points: np.ndarray) -> o3d.geometry.PointCloud:
    return o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))


def extract_planes(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[list[np.ndarray], np.ndarray, dict[str, object]]:
    """Estrazione iterativa di piani con RANSAC: pavimento e pareti via dal residuo.

    Il seme fissato rende l'estrazione riproducibile: senza, la stessa
    configurazione produrrebbe segmentazioni diverse a ogni esecuzione.
    """
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
