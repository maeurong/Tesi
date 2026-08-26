"""Rende importabili gli aiutanti condivisi da qualunque sottocartella di test.

`ccx_utils` sta in `tests/` e serve sia a `tests/feasibility/` sia a
`tests/validazione/`. Senza questa riga l'import funziona solo per caso:
pytest inserisce in `sys.path` la cartella di ciascun file di test raccolto,
quindi `tests/` finisce sul percorso solo finche' la corsa raccoglie anche i
file che stanno li' dentro. `pytest tests/validazione/` da solo fallirebbe.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
