#!/usr/bin/env python
"""Rimisura i numeri di `docs/validazione/scarto-con-segno.md` (#73).

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-6-cantiere/misura-carichi.py`. Ogni valore che il documento
pubblica porta qui il proprio `assert`.

    uv run python docs/fase-7-cantiere/scarto-con-segno.py [cartella-runs]

**Legge e non scrive dentro `runs/`.** Prende la nuvola segmentata e la
superficie riparata della corsa di riferimento e le confronta; nessun
artefatto viene riscritto.

**La controprova che rende citabili i numeri**: il modulo dello scarto con
segno deve riprodurre **esattamente** il `cloud_to_mesh` che quella stessa
corsa ha gia' pubblicato in `metrics.json`. Se non lo riproducesse, la
decomposizione starebbe misurando un'altra cosa e il segno sarebbe attaccato
al numero sbagliato.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "src"))

from meshrec.core import io, quality  # noqa: E402

CORSE = Path(sys.argv[1]) if len(sys.argv) > 1 else RADICE / "runs"
SORGENTE = CORSE / "lab_telaio_v2"
TOLLERANZA = 5.0  # errore_geometrico_max, ratificata in #35


def leggi_superficie(percorso: Path) -> tuple[np.ndarray, np.ndarray]:
    import meshio

    m = meshio.read(percorso)
    facce = np.vstack([b.data for b in m.cells if b.type == "triangle"])
    return np.asarray(m.points, dtype=np.float64), np.asarray(facce, dtype=np.int64)


def main() -> int:
    if not (SORGENTE / "06_repaired.ply").exists():
        print(f"manca {SORGENTE}: serve la corsa di riferimento")
        return 1

    vertici, facce = leggi_superficie(SORGENTE / "06_repaired.ply")
    nuvola, _ = io.read_cloud(SORGENTE / "02_segmented.ply")
    assert len(vertici) == 10968 and len(facce) == 21932, (len(vertici), len(facce))
    assert len(nuvola) == 4269608, len(nuvola)

    esito = quality.scarto_con_segno(vertici, facce, nuvola, tolleranza=TOLLERANZA)

    # La controprova: modulo e massimo devono coincidere con il cloud_to_mesh
    # gia' pubblicato dalla corsa, cifra per cifra.
    metriche = json.loads((SORGENTE / "metrics.json").read_text())
    pubblicato = metriche["07_surface_quality"]["geometric_error"]["cloud_to_mesh"]
    assert esito["modulo_rms"] == pytest_approx(pubblicato["RMS"], 1e-6), (
        esito["modulo_rms"], pubblicato["RMS"]
    )
    assert esito["mancante_max"] == pytest_approx(pubblicato["max"], 1e-6), (
        esito["mancante_max"], pubblicato["max"]
    )
    assert esito["punti"] == pubblicato["n_samples"]

    print(f"tolleranza {TOLLERANZA:.1f} mm (errore_geometrico_max, #35)")
    # #90: se questo esce falso, la decomposizione mancante/inventata pubblicata
    # sotto non ha un segno definito e il documento non puo' citarla.
    print(f"segno definito (superficie chiusa e orientata): {esito['segno_definito']}")
    assert esito["segno_definito"], (
        "segno non definito: i numeri stampati sotto restano un modulo, ma la "
        "decomposizione fra «mancante» e «inventata» non e' citabile"
    )
    print(f"punti {esito['punti']}  vertici {esito['vertici']}\n")
    print("MATERIA MANCANTE (il rilievo sta fuori dal modello)")
    print(f"  frazione {esito['mancante_frazione'] * 100:7.3f} %"
          f"   RMS {esito['mancante_rms']:7.3f} mm   max {esito['mancante_max']:8.3f} mm")
    print("MATERIA INVENTATA (il modello sta oltre il rilievo)")
    print(f"  frazione {esito['inventata_frazione'] * 100:7.3f} %"
          f"   RMS {esito['inventata_rms']:7.3f} mm   max {esito['inventata_max']:8.3f} mm")
    print(f"\nbilancio medio con segno {esito['bilancio_medio']:+8.4f} mm")
    print(f"modulo RMS               {esito['modulo_rms']:8.4f} mm")
    print(f"recall                   {esito['recall'] * 100:7.3f} %")
    print(f"precision                {esito['precision'] * 100:7.3f} %")

    # I numeri pubblicati nel documento.
    assert esito["mancante_frazione"] == pytest_approx(0.48135, 1e-3)
    assert esito["mancante_rms"] == pytest_approx(12.413, 1e-3)
    assert esito["inventata_frazione"] == pytest_approx(0.51864, 1e-3)
    assert esito["inventata_rms"] == pytest_approx(5.473, 1e-3)
    assert esito["inventata_max"] == pytest_approx(30.681, 1e-3)
    assert esito["bilancio_medio"] == pytest_approx(0.0718, 1e-2)
    assert esito["recall"] == pytest_approx(0.65544, 1e-3)
    assert esito["precision"] == pytest_approx(0.75018, 1e-3)

    # Il reperto, asserito e non solo stampato: il bilancio con segno e' due
    # ordini di grandezza sotto il modulo. Un RMS senza segno racconterebbe
    # 9,47 mm di errore e non direbbe che i due modi quasi si annullano.
    assert abs(esito["bilancio_medio"]) < 0.01 * esito["modulo_rms"], (
        esito["bilancio_medio"], esito["modulo_rms"]
    )
    # E le due code sono di natura diversa: quella mancante ha un massimo di
    # due ordini di grandezza piu' alto.
    assert esito["mancante_max"] > 20.0 * esito["inventata_max"]

    print("\ntutti gli assert passati")
    return 0


def pytest_approx(atteso: float, rel: float) -> object:
    """Confronto relativo senza dipendere da pytest: questo e' uno script."""

    class _Vicino:
        def __eq__(self, altro: object) -> bool:
            return abs(float(altro) - atteso) <= rel * abs(atteso)

        def __repr__(self) -> str:
            return f"{atteso} +- {rel:g} rel"

    return _Vicino()


if __name__ == "__main__":
    raise SystemExit(main())
