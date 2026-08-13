"""Sequenza degli step. E' l'unico modulo che conosce l'ordine.

Ogni step scrive il proprio artefatto numerato: la ripresa con `from_step`
ricarica l'artefatto precedente invece di rifare il lavoro.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from meshrec.core import abaqus, io, quality, repair, segment, surface, volume
from meshrec.core.config import PipelineConfig, save_config

ARTIFACTS: dict[int, str] = {
    1: "01_cloud.ply",
    2: "02_segmented.ply",
    3: "03_downsampled.ply",
    4: "04_normals.ply",
    5: "05_surface.ply",
    6: "06_repaired.ply",
    8: "08_simplified.ply",
    9: "09_volume.vtu",
}

# Tabelle esplicite da from_step all'artefatto da ricaricare, verificate a mano
# per ogni from_step da 2 a 9 (non solo il caso 1). Sostituiscono un calcolo
# con ARTIFACTS[min(from_step - 1, N)] che era sbagliato in due punti:
# - per from_step=8 chiedeva ARTIFACTS[7], che non esiste (KeyError);
# - per from_step=4..7 la nuvola di riferimento per l'errore geometrico dello
#   step 7 finiva per essere quella ridotta o normale, non quella segmentata.
# Una tabella e' piu facile da controllare a colpo d'occhio di un'espressione.

# Nuvola da ricaricare come ingresso dello step che riparte (usata anche solo
# per stimare la spaziatura quando lo step stesso legge il proprio artefatto).
_RESUME_POINTS: dict[int, int] = {2: 1, 3: 2, 4: 3, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4}

# Mesh (vertici/facce) da ricaricare come ingresso dello step che riparte.
# Lo step 7 non scrive un proprio artefatto (produce solo metriche), quindi
# from_step=8 riparte anch'esso dalla superficie riparata dello step 6.
# from_step=9 non e' qui: l'artefatto giusto dipende da cfg.simplify.enabled
# (vedi run()), perche' lo step 8 scrive 08_simplified.ply solo se abilitato.
_RESUME_MESH: dict[int, int] = {6: 5, 7: 6, 8: 6}


def _write_mesh(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )
    o3d.io.write_triangle_mesh(str(path), mesh)


def _read_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    import open3d as o3d

    mesh = o3d.io.read_triangle_mesh(str(path))
    return (
        np.ascontiguousarray(np.asarray(mesh.vertices), dtype=np.float64),
        np.ascontiguousarray(np.asarray(mesh.triangles), dtype=np.int64),
    )


def run(cfg: PipelineConfig) -> dict[str, object]:
    """Esegue la pipeline e restituisce le metriche di ogni step.

    `cfg.run.from_step` salta gli step precedenti e ricarica dal disco
    l'artefatto numerato che precede quello di ripartenza, secondo le tabelle
    `_RESUME_POINTS` e `_RESUME_MESH`. La ripresa si fida dell'operatore: non
    verifica che quegli artefatti siano stati prodotti con la configurazione
    corrente, e nemmeno che esistano. Unica eccezione governata da `cfg`
    invece che dalla tabella: `from_step=9` ricarica `08_simplified.ply` se
    `cfg.simplify.enabled` e' vero, altrimenti `06_repaired.ply`, perche' lo
    step 8 scrive il proprio artefatto solo quando la semplificazione e'
    abilitata (predefinito: disabilitata). Se l'operatore riparte da 9 con
    `simplify.enabled=True` ma la corsa precedente non aveva scritto
    `08_simplified.ply` (per esempio perche' era disabilitata in quella
    corsa), la ripresa fallisce con `FileNotFoundError` invece di indovinare.

    La ripresa arriva fino allo step 9 (tetraedrizzazione): `RunConfig.from_step`
    e' vincolato a 9 (vedi `config.py`). Gli step 10 e 11 sono il calcolo delle
    metriche di volume e l'esportazione del deck, senza lavoro costoso da
    saltare, quindi vengono sempre rieseguiti, qualunque sia `from_step`.
    """
    out = Path(cfg.run.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")
    metrics: dict[str, object] = {}
    start = cfg.run.from_step

    try:
        if start <= 1:
            points, step_metrics = io.load_cloud(cfg.input)
            metrics["01_load"] = step_metrics
            io.write_cloud(out / ARTIFACTS[1], points)
        else:
            points, _ = io.read_cloud(out / ARTIFACTS[_RESUME_POINTS[start]])

        spacing = float(
            metrics.get("01_load", {}).get("spacing")
            or io.mean_spacing(points, cfg.input.spacing_sample, cfg.input.seed)
        )

        if start <= 2:
            points, step_metrics = segment.segment_cloud(points, cfg.segment, spacing)
            metrics["02_segment"] = step_metrics
            io.write_cloud(out / ARTIFACTS[2], points)
            source_cloud = points
        else:
            # nuvola segmentata (uscita dello step 2), sempre ricaricata da qui
            # indipendentemente da cosa serva a `points` piu sotto: e' il
            # riferimento fisso per l'errore geometrico dello step 7.
            source_cloud, _ = io.read_cloud(out / ARTIFACTS[2])

        if start <= 3:
            points, step_metrics = surface.downsample(points, cfg.downsample, spacing)
            metrics["03_downsample"] = step_metrics
            io.write_cloud(out / ARTIFACTS[3], points)

        if start <= 4:
            normals, step_metrics = surface.estimate_normals(points, cfg.normals, spacing)
            metrics["04_normals"] = step_metrics
            io.write_cloud(out / ARTIFACTS[4], points, normals)
        else:
            points, normals = io.read_cloud(out / ARTIFACTS[4])

        if start <= 5:
            vertices, faces, step_metrics = surface.reconstruct(points, normals, cfg.surface, spacing)
            metrics["05_reconstruct"] = step_metrics
            _write_mesh(out / ARTIFACTS[5], vertices, faces)
        elif start == 9:
            # lo step 8 scrive 08_simplified.ply solo se la semplificazione e'
            # abilitata: con from_step=9 la mesh valida a monte e' quella
            # dello step 8 se abilitata, altrimenti quella riparata dello
            # step 6 (predefinito), mai un ripiego generico sull'ultimo file
            # esistente.
            resume_from = 8 if cfg.simplify.enabled else 6
            vertices, faces = _read_mesh(out / ARTIFACTS[resume_from])
        else:
            vertices, faces = _read_mesh(out / ARTIFACTS[_RESUME_MESH[start]])

        if start <= 6:
            vertices, faces, step_metrics = repair.repair_surface(vertices, faces, cfg.repair)
            metrics["06_repair"] = step_metrics
            _write_mesh(out / ARTIFACTS[6], vertices, faces)

        if start <= 7:
            step_metrics = quality.surface_metrics(vertices, faces)
            step_metrics["geometric_error"] = quality.geometric_error(vertices, faces, source_cloud)
            metrics["07_surface_quality"] = step_metrics

        if start <= 8:
            vertices, faces, step_metrics = surface.simplify(vertices, faces, cfg.simplify)
            metrics["08_simplify"] = step_metrics
            if cfg.simplify.enabled:
                _write_mesh(out / ARTIFACTS[8], vertices, faces)

        nodes, tets, step_metrics = volume.tetrahedralize_with_metrics(vertices, faces, cfg.tet)
        metrics["09_tetrahedralize"] = step_metrics
        abaqus.write_vtu(out / ARTIFACTS[9], nodes, tets)

        metrics["10_volume_quality"] = quality.volume_metrics(nodes, tets, cfg.tet.reference_ratio)

        # `vertices` e' la superficie da cui la mesh di volume e' stata
        # generata: e' quella, e non i nodi del volume, a definire il sistema
        # di riferimento del modello (vedi abaqus.align_to_axes).
        metrics["11_export"] = abaqus.export_model(
            out / "wall_model.inp",
            out / "wall_model.vtu",
            nodes,
            tets,
            cfg.analysis,
            cfg.tet,
            reference=vertices,
        )
    finally:
        with (out / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2, default=float, ensure_ascii=False)

    return metrics
