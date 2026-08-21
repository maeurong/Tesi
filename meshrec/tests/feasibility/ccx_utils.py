"""Lettura minima del file .dat prodotto da CalculiX."""

from __future__ import annotations

from pathlib import Path


def read_dat_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    """Spostamenti nodali dell'ultimo blocco 'displacements' del file .dat.

    Le righe utili hanno quattro campi: numero di nodo e tre componenti, e
    stanno dopo l'intestazione degli spostamenti -- non dopo una qualunque.
    Con `print_nsets` non vuoto il `.dat` porta anche un blocco `forces` (le
    `RF` sul set vincolato), righe identiche in forma: senza il filtro,
    newton e millimetri finiscono nello stesso dizionario. Stessa correzione
    di `solve.leggi_reazioni` (I2 della revisione finale della Fase 5), qui
    a specchio.

    Si ferma a `E I G E N V A L U E   O U T P U T`, stesso pattern di
    `solve.leggi_reazioni`: la richiesta di stampa di un passo statico
    (`*NODE PRINT, U`) resta attiva anche in un passo modale successivo, che
    non la cancella. `ccx` ristampa quindi un blocco a quattro campi anche
    sotto quell'intestazione, con valori tre o quattro ordini di grandezza
    sopra lo spostamento fisico -- una forma modale, non uno spostamento.
    Senza questo confine, "l'ultimo blocco vince" prenderebbe quello.
    """
    displacements: dict[int, tuple[float, float, float]] = {}
    inside = False
    for line in Path(path).read_text(encoding="ascii", errors="ignore").splitlines():
        if "E I G E N V A L U E   O U T P U T" in line:
            break
        if " for set " in line:
            inside = line.strip().startswith("displacements")
            continue
        if not inside:
            continue
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
