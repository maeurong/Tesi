"""Step 3, 4, 5, 8: dalla nuvola segmentata alla superficie triangolare."""

from __future__ import annotations

import numpy as np
import open3d as o3d

from meshrec.core.config import DownsampleConfig, NormalsConfig, SimplifyConfig, SurfaceConfig


def _to_cloud(points: np.ndarray, normals: np.ndarray | None = None) -> o3d.geometry.PointCloud:
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))
    if normals is not None:
        cloud.normals = o3d.utility.Vector3dVector(np.asarray(normals, dtype=np.float64))
    return cloud


def _to_mesh(vertices: np.ndarray, faces: np.ndarray) -> o3d.geometry.TriangleMesh:
    return o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )


def _from_mesh(mesh: o3d.geometry.TriangleMesh) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.ascontiguousarray(np.asarray(mesh.vertices), dtype=np.float64),
        np.ascontiguousarray(np.asarray(mesh.triangles), dtype=np.int64),
    )


def downsample(
    points: np.ndarray, cfg: DownsampleConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 3: riduzione a voxel. Il passo predefinito deriva dai dati, non da una costante."""
    voxel = cfg.voxel_size if cfg.voxel_size is not None else cfg.voxel_factor * spacing
    reduced = np.asarray(_to_cloud(points).voxel_down_sample(voxel).points, dtype=np.float64)
    metrics = {
        "voxel_size": float(voxel),
        "points_before": int(len(points)),
        "points_after": int(len(reduced)),
        "reduction": float(1.0 - len(reduced) / len(points)),
    }
    return np.ascontiguousarray(reduced), metrics


def estimate_normals(
    points: np.ndarray, cfg: NormalsConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 4: normali con vicinato KNN e orientamento coerente su albero di supporto."""
    cloud = _to_cloud(points)
    cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=cfg.knn))
    cloud.orient_normals_consistent_tangent_plane(cfg.orient_knn)
    normals = np.ascontiguousarray(np.asarray(cloud.normals), dtype=np.float64)
    lengths = np.linalg.norm(normals, axis=1)
    metrics = {
        "knn": cfg.knn,
        "orient_knn": cfg.orient_knn,
        "spacing": float(spacing),
        "degenerate_normals": int((lengths < 0.5).sum()),
    }
    return normals, metrics


def reconstruct(
    points: np.ndarray,
    normals: np.ndarray | None,
    cfg: SurfaceConfig,
    spacing: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 5: ricostruzione della superficie, con trimming per densita nel Poisson."""
    cloud = _to_cloud(points, normals)
    metrics: dict[str, object] = {"method": cfg.method, "vertices_trimmed": 0}

    if cfg.method == "poisson":
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            cloud,
            depth=cfg.poisson_depth,
            width=cfg.poisson_width,
            scale=cfg.poisson_scale,
        )
        # Il trimming e' il rimedio diretto all'artefatto principale del programma
        # sostituito: Poisson chiude le zone non rilevate inventando superficie.
        if cfg.density_quantile > 0.0:
            densities = np.asarray(densities)
            threshold = float(np.quantile(densities, cfg.density_quantile))
            to_remove = densities < threshold
            metrics["vertices_trimmed"] = int(to_remove.sum())
            metrics["density_threshold"] = threshold
            mesh.remove_vertices_by_mask(to_remove)
    elif cfg.method == "bpa":
        radii = o3d.utility.DoubleVector([factor * spacing for factor in cfg.bpa_radius_factors])
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(cloud, radii)
        metrics["radii"] = [factor * spacing for factor in cfg.bpa_radius_factors]
    else:
        alpha = cfg.alpha_factor * spacing
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(cloud, alpha)
        metrics["alpha"] = float(alpha)

    mesh.remove_unreferenced_vertices()
    vertices, faces = _from_mesh(mesh)
    metrics["vertices"] = int(len(vertices))
    metrics["triangles"] = int(len(faces))
    return vertices, faces, metrics


def simplify(
    vertices: np.ndarray, faces: np.ndarray, cfg: SimplifyConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 8: decimazione o remeshing isotropo, con smoothing di Taubin.

    Lo smoothing laplaciano e' escluso: contrae il volume e assottiglia il muro,
    cioe' falsa proprio la grandezza che il modello deve misurare.
    """
    metrics: dict[str, object] = {
        "enabled": cfg.enabled,
        "mode": cfg.mode,
        "triangles_before": int(len(faces)),
    }
    if not cfg.enabled:
        metrics["triangles_after"] = int(len(faces))
        return np.asarray(vertices), np.asarray(faces), metrics

    if cfg.mode == "decimate":
        if cfg.target_faces is None:
            raise ValueError("mode='decimate' richiede target_faces")
        mesh = _to_mesh(vertices, faces).simplify_quadric_decimation(cfg.target_faces)
        out_vertices, out_faces = _from_mesh(mesh)
    else:
        import pymeshlab

        mesh_set = pymeshlab.MeshSet()
        mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces)), "in")
        mesh_set.apply_filter(
            "meshing_isotropic_explicit_remeshing",
            targetlen=pymeshlab.PercentageValue(cfg.remesh_target_len_pct),
        )
        current = mesh_set.current_mesh()
        out_vertices = np.ascontiguousarray(current.vertex_matrix(), dtype=np.float64)
        out_faces = np.ascontiguousarray(current.face_matrix(), dtype=np.int64)

    if cfg.taubin_iterations > 0:
        mesh = _to_mesh(out_vertices, out_faces).filter_smooth_taubin(
            number_of_iterations=cfg.taubin_iterations
        )
        out_vertices, out_faces = _from_mesh(mesh)

    metrics["triangles_after"] = int(len(out_faces))
    metrics["vertices"] = int(len(out_vertices))
    return out_vertices, out_faces, metrics
