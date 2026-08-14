"""Decimazione per il disegno, con la mappa verso gli indici della nuvola piena.

Senza la mappa il clic sul cluster e il box di ritaglio agirebbero su una
nuvola scollegata dal dato: e' la forma esatta del risultato plausibile che
nessuna metrica smentisce. Open3D la fornisce gia' con
voxel_down_sample_and_trace, verificato su 100.000 punti: copertura completa,
nessuna ripetizione.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d


def decimate(
    points: np.ndarray, max_points: int, spacing: float
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Punti da disegnare, gli indici pieni che ciascuno rappresenta, il voxel usato.

    Il passo non e' un numero scelto: si parte dalla spaziatura media della
    nuvola, che il core gia' calcola, e si raddoppia finche' il conteggio
    scende sotto il budget. La ricerca e' deterministica e non introduce alcun
    parametro da tarare.

    Voxel zero dichiara che nessuna decimazione e' stata applicata: la nuvola
    era gia' sotto il budget e i gruppi sono le identita'.
    """
    punti = np.ascontiguousarray(np.asarray(points, dtype=np.float64))
    if len(punti) <= max_points:
        return punti, [np.array([indice]) for indice in range(len(punti))], 0.0

    nuvola = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(punti))
    basso, alto = nuvola.get_min_bound(), nuvola.get_max_bound()
    voxel = float(spacing) if spacing > 0.0 else float(np.max(alto - basso)) / 1000.0
    for _ in range(64):
        ridotta, _indici, tracce = nuvola.voxel_down_sample_and_trace(voxel, basso, alto)
        if len(ridotta.points) <= max_points:
            gruppi = [np.asarray(traccia, dtype=np.int64) for traccia in tracce]
            return (
                np.ascontiguousarray(np.asarray(ridotta.points), dtype=np.float64),
                gruppi,
                voxel,
            )
        voxel *= 2.0
    # Sessantaquattro raddoppi portano il voxel oltre qualunque ingombro
    # fisico: se il budget non e' stato raggiunto il problema e' il budget,
    # non la nuvola, e dirlo e' meglio che restituire tutto in silenzio.
    raise ValueError(
        f"nessun passo di voxel porta {len(punti)} punti sotto il budget di {max_points}"
    )


def to_float32(array: np.ndarray) -> bytes:
    """Serializzazione binaria: 300.000 punti sono 3,6 MB contro i circa 18 in JSON."""
    return np.ascontiguousarray(np.asarray(array), dtype="<f4").tobytes()
