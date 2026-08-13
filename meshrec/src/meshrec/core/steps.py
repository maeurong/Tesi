"""Registro degli step: che cosa consuma ciascuno, e se il suo risultato vale ancora.

La spec di architettura prometteva che gli step a valle di una modifica fossero
marcati non validi; il codice non lo faceva e la ripresa, come diceva la sua
docstring, si fidava dell'operatore. Qui la promessa diventa una condizione
ricontrollabile.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from meshrec.core.config import PipelineConfig

# Le undici chiavi che una corsa completa scrive in metrics.json. Lo step 7 non
# ha artefatto proprio ma ha metriche, quindi c'e' anche lui.
STEP_KEYS: tuple[str, ...] = (
    "01_load",
    "02_segment",
    "03_downsample",
    "04_normals",
    "05_reconstruct",
    "06_repair",
    "07_surface_quality",
    "08_simplify",
    "09_tetrahedralize",
    "10_volume_quality",
    "11_export",
)

# I blocchi di PipelineConfig che ogni step legge davvero. E' la tabella da cui
# discende l'invalidazione a valle: cambiare surface.poisson_depth non puo'
# invalidare lo step 3, e deve invalidare tutto da 5 in giu'.
STEP_BLOCKS: dict[int, tuple[str, ...]] = {
    1: ("input",),
    2: ("segment",),
    3: ("downsample",),
    4: ("normals",),
    5: ("surface",),
    6: ("repair",),
    7: (),
    8: ("simplify",),
    9: ("tet",),
    10: ("tet",),
    11: ("tet", "analysis"),
}

STATE_FILENAME = "steps.json"


def step_fingerprints(cfg: PipelineConfig) -> dict[int, str]:
    """Impronta di ogni step, concatenata a quella dello step precedente.

    La catena e' cio' che produce l'invalidazione a valle senza scriverla a
    mano: cambiare un blocco cambia l'impronta dello step che lo consuma e di
    tutti quelli dopo, e lascia intatte quelle prima.

    Il blocco `run` non entra, per la stessa ragione per cui non entra
    nell'impronta di candidato dello sweep: out_dir e from_step non cambiano il
    risultato dell'elaborazione.
    """
    payload = cfg.model_dump(mode="json")
    catena = ""
    marchi: dict[int, str] = {}
    for numero in sorted(STEP_BLOCKS):
        blocchi = {nome: payload[nome] for nome in STEP_BLOCKS[numero]}
        canonico = json.dumps(blocchi, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        catena = hashlib.sha256((catena + canonico).encode("utf-8")).hexdigest()
        marchi[numero] = catena
    return marchi


def read_state(out_dir: Path) -> dict[str, object]:
    """Rilegge steps.json. Una corsa mai eseguita non ce l'ha: dizionario vuoto."""
    percorso = Path(out_dir) / STATE_FILENAME
    if not percorso.exists():
        return {}
    try:
        with percorso.open(encoding="utf-8") as maniglia:
            contenuto = json.load(maniglia)
    except (OSError, json.JSONDecodeError):
        # Un processo ucciso puo' lasciare il file troncato a meta' scrittura.
        # Uno stato illeggibile e' uno stato assente: tutti gli step tornano
        # "mai eseguito", che e' pessimista e mai falsamente rassicurante.
        return {}
    return contenuto if isinstance(contenuto, dict) else {}


def run_state(out_dir: Path, cfg: PipelineConfig) -> list[dict[str, object]]:
    """Stato dei undici step per la corsa in `out_dir` con la configurazione `cfg`.

    "valido" significa una cosa sola e verificabile: l'impronta salvata coincide
    con quella ricalcolata dalla configurazione corrente. Non e' un'etichetta
    scritta dopo un'esecuzione riuscita e poi creduta sulla parola.
    """
    out_dir = Path(out_dir)
    salvato = read_state(out_dir)
    attesi = step_fingerprints(cfg)

    stato: list[dict[str, object]] = []
    for numero, chiave in enumerate(STEP_KEYS, start=1):
        voce = salvato.get(chiave)
        if not isinstance(voce, dict):
            corrente = "mai eseguito"
        elif voce.get("esito") == "fallito":
            corrente = "fallito"
        elif voce.get("impronta") != attesi[numero]:
            corrente = "non valido"
        else:
            corrente = "valido"
        stato.append(
            {
                "numero": numero,
                "chiave": chiave,
                "stato": corrente,
                "impronta": attesi[numero],
                "artefatto": (voce or {}).get("artefatto"),
                "secondi": (voce or {}).get("secondi"),
            }
        )
    return stato
