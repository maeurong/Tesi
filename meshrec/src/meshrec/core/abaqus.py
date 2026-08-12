"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from meshrec.core.config import GRAVITY_MM_S2, AnalysisConfig, Material, TetConfig

_SET_ITEMS_PER_LINE = 8


def _set_lines(indices: np.ndarray) -> list[str]:
    """Indici 0-based in righe di numeri 1-based, otto per riga."""
    one_based = np.asarray(indices, dtype=np.int64) + 1
    return [
        ", ".join(str(value) for value in one_based[start : start + _SET_ITEMS_PER_LINE])
        for start in range(0, len(one_based), _SET_ITEMS_PER_LINE)
    ]


def write_inp(
    path: Path,
    nodes: np.ndarray,
    tets: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    fixed_nset: str = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    step_name: str = "GRAVITA",
) -> None:
    """Scrive un modello pronto all'analisi statica sotto peso proprio."""
    if fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")

    nodes = np.asarray(nodes, dtype=np.float64)
    tets = np.asarray(tets, dtype=np.int64)

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE=C3D4, ELSET={elset}")
    lines += [
        f"{index + 1}, {a + 1}, {b + 1}, {c + 1}, {d + 1}"
        for index, (a, b, c, d) in enumerate(tets)
    ]

    for name, indices in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(indices)

    lines += [
        f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC",
        f"{material.young}, {material.poisson}",
        "*DENSITY",
        f"{material.density:.9g}",
        "*BOUNDARY",
        f"{fixed_nset}, 1, 3",
        f"*STEP, NAME={step_name}",
        "*STATIC",
        "*DLOAD",
        f"{elset}, GRAV, {gravity}, 0.0, 0.0, -1.0",
    ]

    for name in print_nsets:
        lines += [f"*NODE PRINT, NSET={name}", "U"]

    lines += [
        "*OUTPUT, FIELD",
        "*NODE OUTPUT",
        "U",
        "*ELEMENT OUTPUT",
        "S, E",
        "*END STEP",
        "",
    ]

    Path(path).write_text("\n".join(lines), encoding="ascii")


def _fix_sign(direction: np.ndarray) -> np.ndarray:
    """Convenzione deterministica di segno: componente di modulo massimo positiva.

    Le direzioni principali restituite dalla SVD hanno segno arbitrario: senza
    una convenzione, due esecuzioni sulla stessa nuvola possono produrre assi
    opposti e quindi set di faccia scambiati.
    """
    direction = np.asarray(direction, dtype=np.float64)
    return direction if direction[int(np.argmax(np.abs(direction)))] >= 0.0 else -direction


def align_to_axes(nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Rototraslazione ai piani principali: spessore su x, lunghezza su y, altezza su z.

    La trasformazione e' restituita come matrice 4x4 e va salvata nei metadati:
    e' l'unico modo per riportare i risultati nel sistema originale dello scanner.

    Assunzione: lo scanner e' livellato, cioe' la z della nuvola in ingresso
    e' gia' il verticale reale e l'unica ambiguita' e' l'imbardata. Se la
    nuvola e' inclinata fuori dal piano orizzontale (beccheggio o rollio),
    l'assegnazione dell'asse altezza non e' garantita.
    """
    points = np.asarray(nodes, dtype=np.float64)
    centre = points.mean(axis=0)
    centred = points - centre

    _, _, principal = np.linalg.svd(centred, full_matrices=False)
    extents = np.ptp(centred @ principal.T, axis=0)

    thickness_axis = int(np.argmin(extents))
    remaining = [index for index in range(3) if index != thickness_axis]
    # fra le due direzioni restanti, l'altezza e' quella piu vicina al verticale
    # originale: la gravita agisce lungo il verticale reale, non lungo l'asse
    # con l'estensione maggiore.
    verticality = [abs(principal[index][2]) for index in remaining]
    height_axis = remaining[int(np.argmax(verticality))]

    vertical = principal[height_axis]
    # L'altezza punta verso l'alto del sistema originale: la gravita agisce
    # lungo il verticale reale, e BASE deve restare l'estremita fisicamente
    # piu bassa. Se la nuvola e' quasi coricata il prodotto scalare non decide,
    # e si ricade sulla convenzione di segno deterministica.
    if abs(vertical[2]) > 1e-6:
        z_dir = vertical if vertical[2] > 0.0 else -vertical
    else:
        z_dir = _fix_sign(vertical)

    x_dir = _fix_sign(principal[thickness_axis])
    # y come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori, che
    # cambierebbe il verso di un asse gia deciso.
    y_dir = np.cross(z_dir, x_dir)

    rotation = np.stack([x_dir, y_dir, z_dir])

    aligned = centred @ rotation.T
    shift = aligned.min(axis=0)
    aligned = aligned - shift

    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ centre - shift

    metrics = {
        "extent": (aligned.max(axis=0) - aligned.min(axis=0)).tolist(),
        "transform": transform.tolist(),
    }
    return np.ascontiguousarray(aligned), transform, metrics


def set_tolerance(nodes: np.ndarray, tets: np.ndarray, factor: float) -> float:
    """Tolleranza dei set derivata dalla dimensione media dell'elemento."""
    from meshrec.core.quality import tet_volumes

    mean_volume = float(np.abs(tet_volumes(nodes, tets)).mean())
    edge = (mean_volume * 6.0 * np.sqrt(2.0)) ** (1.0 / 3.0)
    return factor * edge


def build_node_sets(nodes: np.ndarray, tolerance: float) -> dict[str, np.ndarray]:
    """I sei set di faccia, sul modello gia allineato agli assi."""
    points = np.asarray(nodes, dtype=np.float64)
    low = points.min(axis=0)
    high = points.max(axis=0)
    return {
        "BASE": np.flatnonzero(points[:, 2] <= low[2] + tolerance),
        "TOP": np.flatnonzero(points[:, 2] >= high[2] - tolerance),
        "FACE_FRONT": np.flatnonzero(points[:, 0] <= low[0] + tolerance),
        "FACE_BACK": np.flatnonzero(points[:, 0] >= high[0] - tolerance),
        "SIDE_LEFT": np.flatnonzero(points[:, 1] <= low[1] + tolerance),
        "SIDE_RIGHT": np.flatnonzero(points[:, 1] >= high[1] - tolerance),
    }


def write_vtu(path: Path, nodes: np.ndarray, tets: np.ndarray) -> None:
    """Esportazione per la visualizzazione, delegata a meshio."""
    import meshio

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write_points_cells(
        str(path),
        np.asarray(nodes, dtype=np.float64),
        [("tetra", np.asarray(tets, dtype=np.int64))],
    )


def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    tets: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
) -> dict[str, object]:
    """Step 11: allinea, costruisce i set, scrive il deck e il file di visualizzazione."""
    from meshrec.core.quality import tet_volumes

    if tet_cfg.element != "C3D4":
        raise NotImplementedError(
            f"elemento {tet_cfg.element} non supportato dal writer: TetGen produce i nodi "
            "di lato con order=2, ma il deck scrive quattro nodi per elemento. "
            "Usa C3D4 finche il writer non gestisce i dieci nodi."
        )

    aligned, transform, align_metrics = align_to_axes(nodes)
    tolerance = set_tolerance(aligned, tets, cfg.set_tolerance_factor)
    node_sets = build_node_sets(aligned, tolerance)
    if len(node_sets[cfg.fixed_nset]) == 0:
        raise ValueError(f"il set vincolato '{cfg.fixed_nset}' e vuoto: tolleranza {tolerance:.3f} mm troppo stretta")

    write_inp(
        path_inp,
        aligned,
        tets,
        node_sets=node_sets,
        material=cfg.material,
        fixed_nset=cfg.fixed_nset,
        gravity=cfg.gravity,
        step_name=cfg.step_name,
    )
    write_vtu(path_vtu, aligned, tets)

    volume = float(np.abs(tet_volumes(aligned, tets)).sum())
    return {
        "transform": transform.tolist(),
        "extent": align_metrics["extent"],
        "set_tolerance": float(tolerance),
        "node_sets": {name: int(len(indices)) for name, indices in node_sets.items()},
        "volume": volume,
        "mass": volume * cfg.material.density,
        "inp": str(path_inp),
        "vtu": str(path_vtu),
    }
