"""Chi e' il programma. Legge, non decide: la versione sta nel pacchetto,
il commit in git, il DOI in CITATION.cff. Ogni voce assente e' None, mai un
errore: il pie' di pagina non deve mai far cadere l'interfaccia."""

from __future__ import annotations

import importlib.metadata as metadata
import subprocess
from pathlib import Path

import yaml

NOME = "MeshRec"
LICENZA = "MIT"
REPOSITORY = "https://github.com/maeurong/meshrec"
# server.py -> app -> meshrec -> src -> meshrec -> radice del repo
RADICE_REPO = Path(__file__).resolve().parents[4]


def _versione() -> str:
    try:
        return metadata.version("meshrec")
    except metadata.PackageNotFoundError:
        return "sorgente"


def _commit(radice: Path) -> str | None:
    try:
        esito = subprocess.run(
            ["git", "-C", str(radice), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if esito.returncode != 0:
        return None
    return esito.stdout.strip() or None


def _doi(radice: Path) -> str | None:
    cff = radice / "CITATION.cff"
    if not cff.is_file():
        return None
    try:
        voci = yaml.safe_load(cff.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        return None
    doi = voci.get("doi") if isinstance(voci, dict) else None
    return str(doi) if doi else None


def informazioni(radice: Path | None = None) -> dict[str, object]:
    radice = RADICE_REPO if radice is None else Path(radice)
    doi = _doi(radice)
    return {
        "nome": NOME,
        "versione": _versione(),
        "commit": _commit(radice),
        "licenza": LICENZA,
        "doi": doi,
        # L'URL lo compone il server: niente indirizzi di rete in .html/.js/.css
        # (test_server.py, vincolo rete esterna).
        "doi_url": f"https://doi.org/{doi}" if doi else None,
        "repository": REPOSITORY,
    }
