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

# Le tredici chiavi del registro degli step. Lo step 7 non ha artefatto proprio
# ma ha metriche, quindi c'e' anche lui. Lo step 12 e' il prior geometrico
# della Fase 4: chiude la corsa madre di elaborazione e non e' un punto di
# ripresa. Lo step 13 e' il solutore della Fase 5: legge il deck che lo step 11
# ha scritto, e nemmeno lui e' un punto di ripresa. E' anche l'unico step che
# paga un processo esterno vero, non lavoro in-process come tutti gli altri:
# RunConfig.to_step lo include nel predefinito (decisione dell'utente, ogni
# corsa risolve), ma chi elabora molti candidati -- lo sweep -- lo esclude
# esplicitamente con --to-step 12, per non pagarlo per ciascuno. is_complete()
# in sweep.py continua a non richiedere ne' "12_wall" ne' "13_solve" a un
# candidato perche' un candidato di sweep si confronta sulle sole undici
# misure di elaborazione: e' completo quando ha il proprio deck, non quando
# ha il prior o la soluzione.
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
    "12_wall",
    "13_solve",
)

# I blocchi di PipelineConfig che ogni step legge davvero. E' la tabella da cui
# discende l'invalidazione a valle: cambiare surface.poisson_depth non puo'
# invalidare lo step 3, e deve invalidare tutto da 5 in giu'.
#
# Lo step 13 non ripete "carichi": la catena di `step_fingerprints` e'
# cumulativa (l'impronta di ogni step incorpora quella del precedente), quindi
# un cambio ai carichi -- gia' entrato in catena allo step 11 -- invalida 12 e
# 13 comunque, senza bisogno di dichiararlo una seconda volta qui.
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
    11: ("tet", "analysis", "carichi", "selettori"),
    12: ("wall",),
    13: ("tet", "analysis"),
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


def write_state(
    out_dir: Path,
    numero: int,
    impronta: str,
    esito: str,
    artefatto: str | None,
    secondi: float,
) -> None:
    """Registra l'esito di un solo step, senza toccare gli altri.

    Rilegge e riscrive l'intero file a ogni step: sono tredici voci, il costo
    e' nullo, e cosi' lo stato su disco resta un solo documento coerente
    invece di tredici frammenti da ricomporre.
    """
    from meshrec.core.io import scrivi_atomico

    salvato = read_state(out_dir)
    salvato[STEP_KEYS[numero - 1]] = {
        "impronta": impronta,
        "esito": esito,
        "artefatto": artefatto,
        "secondi": float(secondi),
    }
    scrivi_atomico(
        Path(out_dir) / STATE_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(salvato, indent=2, ensure_ascii=False), encoding="utf-8"
        ),
    )


def run_state(out_dir: Path, cfg: PipelineConfig) -> list[dict[str, object]]:
    """Stato dei tredici step per la corsa in `out_dir` con la configurazione `cfg`.

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
                "artefatto": (voce if isinstance(voce, dict) else {}).get("artefatto"),
                "secondi": (voce if isinstance(voce, dict) else {}).get("secondi"),
            }
        )
    return stato
