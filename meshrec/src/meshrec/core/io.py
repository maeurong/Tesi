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


# I formati che `read_cloud` legge davvero. Sta qui, accanto alla funzione che
# li legge, perche' l'interfaccia deve poter rifiutare un file prima di creare
# una corsa attorno a esso: senza questo elenco, un `.e57` verrebbe scoperto
# solo allo step 1, con una cartella gia' scritta sul disco.
ESTENSIONI_NUVOLA = (".pcd", ".ply", ".xyz")


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
    scrivi_atomico(Path(path), lambda destinazione: o3d.io.write_point_cloud(str(destinazione), cloud))


def nn_distances(points: np.ndarray, sample: int, seed: int) -> np.ndarray:
    """Distanze al vicino piu prossimo, su un campione casuale.

    La media di queste distanze e' la spaziatura; la loro dispersione dice
    quanto quella media descrive davvero la nuvola, e chi ne ha bisogno le
    prende da qui invece di ricostruire un secondo albero.
    """
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        raise ValueError("servono almeno due punti per stimare la spaziatura")
    rng = np.random.default_rng(seed)
    size = min(sample, len(points))
    chosen = points[rng.choice(len(points), size=size, replace=False)]
    distances, _ = cKDTree(points).query(chosen, k=2)
    return distances[:, 1]


def mean_spacing(points: np.ndarray, sample: int, seed: int) -> float:
    """Distanza media al vicino piu prossimo, su un campione casuale."""
    return float(nn_distances(points, sample, seed).mean())


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


def scrivi_atomico(path: Path, scrittore) -> None:
    """Scrive su un nome temporaneo e rinomina: l'esito e' completo o assente.

    Serve perche' un'interruzione puo' cadere in mezzo alla scrittura di un
    artefatto grande: 01_cloud.ply di lab_crop pesa 151.898.454 byte e
    wall_model.inp di muro 35.931.310, quindi la finestra e' reale e non
    teorica. Path.replace e' atomico sullo stesso volume anche su Windows.

    Rimisurato il 16/08/2026 sulle corse di riferimento. La versione prima
    citava 34.665.787 byte per 09_volume.vtu di lab_crop e 87.229.481 per il
    suo wall_model.inp: valori veri quando furono scritti, falsi dopo che lo
    sweep di Fase 2 adotto' poisson_depth=7 e i due artefatti scesero a
    938.012 e 2.545.069 byte, cioe' trentacinque volte meno.

    Da qui una regola per chi cita una taglia in una docstring: un artefatto
    a valle di un parametro dello sweep cambia quando il fronte cambia, e il
    numero invecchia in silenzio. 01_cloud.ply e' lo step 1 e non dipende da
    nessun parametro adottato, quindi e' la citazione che regge nel tempo.

    Il nome temporaneo porta ".tmp" prima dell'estensione, non dopo
    (box.tmp.ply, non box.ply.tmp): write_triangle_mesh di open3d non ha un
    parametro di formato esplicito e lo deduce dall'ultima estensione del
    nome file, quindi "box.ply.tmp" verrebbe scritto come formato "tmp"
    sconosciuto, fallirebbe in silenzio (restituisce False, non solleva) e
    la successiva replace() troverebbe un file mai creato.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = path.with_name(path.stem + ".tmp" + path.suffix)
    try:
        scrittore(temporaneo)
        temporaneo.replace(path)
    finally:
        # Un fallimento a meta' scrittura non deve lasciare un .tmp che il
        # prossimo elenco degli artefatti scambierebbe per un artefatto.
        if temporaneo.exists():
            temporaneo.unlink()


def scarta_temporanei(directory: Path) -> int:
    """Rimuove i temporanei rimasti da un processo ucciso. Restituisce quanti.

    Il nome porta ".tmp" prima dell'estensione (vedi scrivi_atomico), quindi
    il pattern e' "*.tmp.*" e non "*.tmp".
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    rimossi = 0
    for elemento in directory.glob("*.tmp.*"):
        elemento.unlink()
        rimossi += 1
    return rimossi
