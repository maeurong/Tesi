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
import subprocess
import sys
import time
import warnings
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

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


# Le undici chiavi che una corsa completa scrive in metrics.json. Lo step 7
# non ha artefatto proprio ma ha metriche, quindi c'e' anche lui.
REQUIRED_STEPS: tuple[str, ...] = (
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

_TRACKED_PACKAGES: tuple[str, ...] = ("open3d", "tetgen", "pymeshfix", "pymeshlab", "numpy")


def is_complete(metrics: dict[str, object]) -> bool:
    """Vero se il metrics.json porta tutte le chiavi di step.

    pipeline.run scrive metrics.json in un blocco finally, quindi una corsa
    uccisa lascia un dizionario parziale che nessun controllo distingueva da
    uno completo. Un candidato incompleto non puo' entrare nel fronte.
    """
    return all(step in metrics for step in REQUIRED_STEPS)


def file_digest(path: Path) -> str:
    """Sha256 di un file, letto a blocchi: gli artefatti arrivano a 101 MB."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GitUnavailableWarning(UserWarning):
    """git non e' partito: la riga scrive provenienza incompleta, non fabbricata."""


def provenance() -> dict[str, object]:
    """Commit del codice, stato dell'albero e versioni delle librerie che contano.

    Senza queste tre cose una riga non e' ricostruibile a distanza di mesi:
    la stessa configurazione su un codice diverso e' un altro esperimento.
    """
    def _git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args], capture_output=True, text=True, check=False
            )
        except OSError as exc:
            # git assente, o l'avvio del processo negato dall'ambiente: in ogni
            # caso None e' distinto da "" (comando riuscito, output vuoto),
            # altrimenti un albero sporco letto a vuoto si scriverebbe pulito.
            warnings.warn(f"git non avviabile, provenienza incompleta: {exc}", GitUnavailableWarning)
            return None
        return result.stdout.strip()

    versions: dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "assente"

    dirty_raw = _git("status", "--porcelain")

    return {
        "commit": _git("rev-parse", "HEAD") or "sconosciuto",
        "dirty": None if dirty_raw is None else bool(dirty_raw),
        "python": sys.version.split()[0],
        "versions": versions,
    }


def append_row(path: Path, row: dict[str, object]) -> None:
    """Aggiunge una riga al registro. In sola aggiunta: nessuna riga viene riscritta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=float) + "\n")


def load_registry(path: Path) -> list[dict[str, object]]:
    """Rilegge il registro riga per riga."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_candidate(
    axes: dict[str, object],
    cfg: PipelineConfig,
    out_dir: Path,
    timeout_s: float,
) -> dict[str, object]:
    """Esegue un candidato come processo separato e ne restituisce la riga.

    Il sottoprocesso, e non un pool in memoria, per una ragione misurata: in
    Fase 1 il processo e' stato ucciso dal sistema per esaurimento della
    memoria senza sollevare alcuna eccezione. Un worker perso cosi' rompe un
    ProcessPoolExecutor e porta giu' lo sweep; un sottoprocesso lascia un
    codice di uscita e una riga di fallimento.

    Non solleva mai per un candidato che fallisce: fallire e' un esito, e un
    buco nel registro sarebbe indistinguibile da un candidato mai provato.
    """
    from meshrec.core.config import save_config

    out_dir = Path(out_dir)
    cfg = cfg.model_copy(deep=True)
    cfg.run.out_dir = out_dir
    config_path = out_dir / "config.yaml"

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        save_config(cfg, config_path)
    except OSError as exc:
        # La cartella del candidato non si e' potuta preparare (permessi
        # negati, collisione con un file omonimo): nessun sottoprocesso e'
        # partito, ma la riga esiste comunque. L'impronta si calcola senza
        # toccare il disco, quindi resta valida anche qui.
        return {
            "fingerprint": fingerprint(cfg),
            "axes": axes,
            "outcome": "errore",
            "exit_code": None,
            "duration_s": 0.0,
            "complete": False,
            "stderr": f"preparazione della cartella del candidato fallita: {exc}",
            "config": cfg.model_dump(mode="json"),
            "input_digest": None,
            "artifacts": {},
            "artifacts_kept": False,
            "out_dir": str(out_dir),
            "rerun": f"uv run meshrec run {config_path}",
            "metrics": {},
            "provenance": provenance(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "meshrec.cli", "run", str(config_path)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        exit_code, stderr = completed.returncode, completed.stderr
        outcome = "riuscito" if exit_code == 0 else "fallito"
    except subprocess.TimeoutExpired as expired:
        exit_code, outcome = None, "timeout"
        stderr = f"nessuna uscita entro {timeout_s} s\n{expired.stderr or ''}"
    duration = time.monotonic() - started

    metrics_path = out_dir / "metrics.json"
    metrics: dict[str, object] = {}
    if metrics_path.exists():
        try:
            with metrics_path.open(encoding="utf-8") as handle:
                metrics = json.load(handle)
        except (OSError, json.JSONDecodeError):
            # Il blocco finally di pipeline.run scrive questo file: un
            # processo ucciso (timeout, memoria esaurita) puo' lasciarlo
            # troncato a meta' scrittura. is_complete({}) e' gia' falso,
            # quindi la riga dice la verita' da sola senza sollevare qui.
            metrics = {}

    artifacts: dict[str, str | None] = {}
    for item in sorted(out_dir.iterdir()):
        try:
            if not item.is_file() or item.name in ("config.yaml", "metrics.json"):
                continue
            artifacts[item.name] = file_digest(item)
        except OSError:
            # File cancellato o illeggibile fra l'elenco e la lettura: la
            # riga registra che l'impronta manca invece di sollevare qui.
            artifacts[item.name] = None
    input_path = Path(cfg.input.path)
    input_digest: str | None = None
    if input_path.exists():
        try:
            input_digest = file_digest(input_path)
        except OSError:
            # Stesso principio dell'elenco artefatti: l'impronta manca, la
            # riga lo registra invece di sollevare qui.
            input_digest = None

    return {
        "fingerprint": fingerprint(cfg),
        "axes": axes,
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_s": duration,
        "complete": is_complete(metrics),
        # stderr e' dove finiscono TruncatedRefinementWarning,
        # IneffectiveVolumeLimitWarning e UnconstrainedModelWarning: qui
        # diventano un campo della riga invece di una riga su un terminale
        # che nel frattempo si e' chiuso.
        "stderr": stderr.strip(),
        "config": cfg.model_dump(mode="json"),
        "input_digest": input_digest,
        "artifacts": artifacts,
        "artifacts_kept": True,
        "out_dir": str(out_dir),
        "rerun": f"uv run meshrec run {config_path}",
        "metrics": metrics,
        "provenance": provenance(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
