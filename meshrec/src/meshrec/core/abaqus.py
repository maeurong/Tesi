"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from meshrec.core.config import GRAVITY_MM_S2, Material

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

    lines += ["*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP", ""]

    Path(path).write_text("\n".join(lines), encoding="ascii")
