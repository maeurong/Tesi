"""Motore di sweep: griglia, impronta, esecuzione, registro, dominanza.

Ogni candidato e' una cartella con il proprio config.yaml, eseguita come
`meshrec run` in un processo separato. La pipeline non viene toccata: il
motore le sta sopra, e cio' che esegue e' esattamente il comando con cui
sono stati prodotti i numeri della Fase 1.
"""

from __future__ import annotations

import hashlib
import itertools
import json

from meshrec.core.config import ExperimentConfig, PipelineConfig


def fingerprint(cfg: PipelineConfig) -> str:
    """Sha256 della configurazione canonica, escluso il blocco `run`.

    out_dir e from_step non cambiano il risultato dell'elaborazione, e
    includerli renderebbe diverse due corse identiche: e' precisamente cio'
    che l'impronta esiste per impedire. Stessa impronta significa stesso
    esperimento.
    """
    payload = cfg.model_dump(mode="json")
    payload.pop("run", None)
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def with_override(cfg: PipelineConfig, path: str, value: object) -> PipelineConfig:
    """Copia della configurazione con un solo parametro cambiato, rivalidata.

    Passa dal dump e da model_validate invece di assegnare l'attributo:
    i modelli annidati non hanno validate_assignment, quindi un valore fuori
    dominio scritto per assegnazione arriverebbe intatto fino alla pipeline.
    """
    data = cfg.model_dump(mode="json")
    node = data
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    return PipelineConfig.model_validate(data)


def expand(
    experiment: ExperimentConfig, base: PipelineConfig
) -> list[tuple[dict[str, object], PipelineConfig]]:
    """Candidati della griglia: la base, un asse alla volta, poi le coppie dichiarate.

    Un fattoriale pieno su cinque assi a tre livelli sono 162 candidati, in
    gran parte combinazioni che nessuno leggera'. Il fronte di Pareto si
    costruisce su qualunque insieme di candidati e non richiede una griglia
    cartesiana per essere valido.

    I duplicati sono rimossi per impronta: un livello uguale al valore di
    base non produce un secondo candidato identico.
    """
    levels = {axis.path: axis.values for axis in experiment.axes}
    combinations: list[dict[str, object]] = [{}]

    for path, values in levels.items():
        combinations.extend({path: value} for value in values)

    for first, second in experiment.pairs:
        combinations.extend(
            {first: a, second: b} for a, b in itertools.product(levels[first], levels[second])
        )

    candidates: list[tuple[dict[str, object], PipelineConfig]] = []
    seen: set[str] = set()
    for axes in combinations:
        cfg = base
        for path, value in axes.items():
            cfg = with_override(cfg, path, value)
        mark = fingerprint(cfg)
        if mark not in seen:
            seen.add(mark)
            candidates.append((axes, cfg))
    return candidates
