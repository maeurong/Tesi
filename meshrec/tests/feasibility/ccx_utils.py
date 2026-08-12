"""Lettura minima del file .dat prodotto da CalculiX."""

from __future__ import annotations

from pathlib import Path


def read_dat_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    """Spostamenti nodali dell'ultimo blocco 'displacements' del file .dat.

    Le righe utili hanno quattro campi: numero di nodo e tre componenti.
    """
    displacements: dict[int, tuple[float, float, float]] = {}
    for line in Path(path).read_text(encoding="ascii", errors="ignore").splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        try:
            node = int(fields[0])
            components = tuple(float(value) for value in fields[1:])
        except ValueError:
            continue
        displacements[node] = components  # type: ignore[assignment]
    return displacements
