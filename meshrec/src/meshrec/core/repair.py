"""Step 6: riparazione topologica deterministica e registrata.

La chiusura garantita si appoggia a MeshFix (Attene 2010), algoritmo
pubblicato e deterministico: e' il requisito che rende la riparazione
citabile in tesi, al posto delle operazioni opache del programma sostituito.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from meshrec.core.config import RepairConfig
from meshrec.core.quality import boundary_edges, is_watertight, mesh_volume

_WELD_DECIMALS = 6


def component_labels(faces: np.ndarray, n_vertices: int) -> np.ndarray:
    """Etichetta di componente connessa per ogni vertice."""
    f = np.asarray(faces)
    rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    data = np.ones(len(rows), dtype=np.int8)
    graph = coo_matrix((data, (rows, cols)), shape=(n_vertices, n_vertices))
    _, labels = connected_components(graph, directed=False)
    return labels


def hole_loops(faces: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Cammini sugli spigoli di bordo, separati in cicli chiusi e cammini aperti.

    Solo un ciclo chiuso e' un foro, e solo di quello ha senso misurare l'area.
    Un cammino che non si richiude non lo e': o finisce in un vicolo cieco, o
    ha raggiunto il tetto di lunghezza. I due casi vanno tenuti distinti perche'
    il registro delle operazioni e' il prodotto di questo modulo, e un cammino
    troncato contato come foro sarebbe un foro fantasma con un'area inventata.
    """
    edges = boundary_edges(faces)
    if len(edges) == 0:
        return [], []

    neighbours: dict[int, list[int]] = {}
    for a, b in edges:
        neighbours.setdefault(int(a), []).append(int(b))
        neighbours.setdefault(int(b), []).append(int(a))

    loops: list[np.ndarray] = []
    open_paths: list[np.ndarray] = []
    unvisited = set(neighbours)
    while unvisited:
        start = unvisited.pop()
        loop = [start]
        previous, current = start, neighbours[start][0]
        closed = False
        # Un ciclo non puo' essere piu lungo del numero di spigoli di bordo.
        # Il tetto non e' prudenza: su una giunzione non manifold (un vertice
        # con piu di due spigoli di bordo, frequente sui bordi lasciati dal
        # trimming per densita del Poisson) scegliere sempre il primo vicino
        # disponibile puo' entrare in un circuito che non ripassa mai da
        # `start`, e la lista cresce fino a esaurire la memoria. Osservato
        # sulla superficie del muro sintetico: MemoryError dentro questo ciclo,
        # con 2285 soli spigoli di bordo.
        while len(loop) <= len(edges):
            if current == start:
                closed = True
                break
            unvisited.discard(current)
            loop.append(current)
            options = [node for node in neighbours[current] if node != previous]
            if not options:
                break
            previous, current = current, options[0]
        (loops if closed else open_paths).append(np.array(loop, dtype=np.int64))
    return loops, open_paths


def _loop_area(vertices: np.ndarray, loop: np.ndarray) -> float:
    """Area del poligono di bordo, formula di Gauss in tre dimensioni."""
    points = np.asarray(vertices, dtype=np.float64)[loop]
    return float(np.linalg.norm(np.cross(points, np.roll(points, -1, axis=0)).sum(axis=0)) / 2.0)


def repair_surface(
    vertices: np.ndarray, faces: np.ndarray, cfg: RepairConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Porta la superficie a chiusura manifold registrando ogni operazione."""
    import pymeshfix

    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    metrics: dict[str, object] = {"volume_before": mesh_volume(v, f)}

    # 1. saldatura dei vertici coincidenti
    _, first, inverse = np.unique(
        np.round(v, _WELD_DECIMALS), axis=0, return_index=True, return_inverse=True
    )
    metrics["duplicate_vertices_merged"] = int(len(v) - len(first))
    order = np.argsort(first)
    remap = np.empty(len(first), dtype=np.int64)
    remap[order] = np.arange(len(first))
    v = np.ascontiguousarray(v[first[order]])
    f = remap[inverse[f]]

    # 2. triangoli degeneri e duplicati
    non_degenerate = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])
    metrics["degenerate_faces_removed"] = int((~non_degenerate).sum())
    f = f[non_degenerate]
    _, unique_index = np.unique(np.sort(f, axis=1), axis=0, return_index=True)
    metrics["duplicate_faces_removed"] = int(len(f) - len(unique_index))
    f = np.ascontiguousarray(f[np.sort(unique_index)])

    # 3. componente connessa maggiore
    labels = component_labels(f, len(v))
    used = np.unique(f)
    metrics["components_before"] = int(len(np.unique(labels[used])))
    metrics["components_kept"] = metrics["components_before"]
    if cfg.largest_component_only and metrics["components_before"] > 1:
        counts = np.bincount(labels[used])
        biggest = int(np.argmax(counts))
        f = np.ascontiguousarray(f[labels[f[:, 0]] == biggest])
        metrics["components_kept"] = 1

    # I vertici della componente scartata resterebbero nell'array: MeshFix
    # riceverebbe punti non referenziati da alcun triangolo.
    referenced = np.unique(f)
    metrics["orphan_vertices_removed"] = int(len(v) - len(referenced))
    if len(referenced) < len(v):
        orphan_remap = np.full(len(v), -1, dtype=np.int64)
        orphan_remap[referenced] = np.arange(len(referenced))
        v = np.ascontiguousarray(v[referenced])
        f = np.ascontiguousarray(orphan_remap[f])

    # 4. misura dei fori, prima che la chiusura ne cancelli la traccia
    loops, open_paths = hole_loops(f)
    areas = sorted((_loop_area(v, loop) for loop in loops), reverse=True)
    metrics["holes_before"] = len(loops)
    metrics["hole_areas"] = areas
    # Cammini di bordo che non si richiudono: non sono fori e non hanno un'area
    # da riportare, ma sono il segnale che il bordo e' non manifold. Contarli
    # fra i fori gonfierebbe `holes_before` con voci di cui `hole_areas`
    # riporterebbe un'area priva di significato.
    metrics["open_boundary_paths"] = len(open_paths)
    metrics["holes_over_threshold"] = (
        [] if cfg.max_hole_area is None else [area for area in areas if area > cfg.max_hole_area]
    )

    # 5. chiusura garantita
    fixer = pymeshfix.MeshFix(v, np.ascontiguousarray(f, dtype=np.int32))
    fixer.repair(joincomp=cfg.join_components)
    v = np.ascontiguousarray(fixer.points, dtype=np.float64)
    f = np.ascontiguousarray(fixer.faces, dtype=np.int64)

    metrics["watertight_after"] = is_watertight(f)
    metrics["volume_after"] = mesh_volume(v, f)
    metrics["vertices"] = int(len(v))
    metrics["triangles"] = int(len(f))
    return v, f, metrics
