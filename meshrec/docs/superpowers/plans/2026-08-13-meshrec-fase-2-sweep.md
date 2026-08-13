# Fase 2 — Motore di sweep, fronte di Pareto e registro: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire il motore che spazza una griglia di parametri su sottoprocessi, seleziona i candidati per dominanza di Pareto e scrive un registro degli esperimenti tracciato da git, e usarlo per scegliere le configurazioni di riferimento di `muro.yaml` e `lab.yaml`.

**Architecture:** Due moduli nuovi nel core — `sweep.py` (griglia, impronta, esecuzione, registro, dominanza) e `report.py` (HTML e SVG dal registro) — più due misure nuove in `quality.py`. Ogni candidato e' una cartella con il proprio `config.yaml`, eseguita come `meshrec run` in un processo separato: il core esistente non viene toccato, tranne il passaggio del limite di riferimento a `volume_metrics`.

**Tech Stack:** Python 3.12, pydantic, numpy, PyYAML, `subprocess` e `concurrent.futures` della libreria standard, pytest. Nessuna dipendenza nuova.

**Spec:** [`docs/superpowers/specs/2026-08-13-meshrec-fase-2-sweep-design.md`](../../../../docs/superpowers/specs/2026-08-13-meshrec-fase-2-sweep-design.md)

## Global Constraints

- Tutti i comandi si eseguono dalla cartella `meshrec/` con `uv run`. Piattaforma Windows, PowerShell.
- **Mai `git add -A`**: la radice del repository ha centinaia di MB non tracciati. Ogni `git add` elenca percorsi espliciti.
- `runs/muro/` e `runs/lab_crop/` sono le corse di riferimento: si leggono e si copiano, **mai** si scrive al loro interno. Ogni esperimento va in una cartella nuova sotto `runs/`, che e' in `.gitignore`.
- L'unico luogo dove un parametro di elaborazione ha un valore predefinito e' `src/meshrec/core/config.py`. Le firme del core **non** portano predefiniti; `tests/test_volume.py::test_no_processing_default_lives_in_the_signature` lo verifica e questo piano estende la verifica ai moduli nuovi.
- Italiano per commenti, docstring, documenti e messaggi di commit. **Niente lettere accentate nelle docstring del core**: si scrive `e'`, `puo'`, `piu`, `gia'`.
- Unita di lavoro: mm, N, MPa, tonnellata, secondo.
- Suite di partenza: 126 passati, 6 deselezionati, 2 avvisi legittimi e asseriti. Ogni task la lascia verde.
- `OMP_NUM_THREADS=1` e' fissato in `src/meshrec/__init__.py` e non va toccato: e' la difesa della riproducibilita. Il parallelismo del motore e' **solo** per processi separati; nessun calcolo gira nei thread dell'orchestratore.

---

## Struttura dei file

| File | Responsabilita |
|---|---|
| `src/meshrec/core/quality.py` (modifica) | Aggiunge `thickness` (misura di fedelta) e `fraction_over_ratio` (asse di qualita); `volume_metrics` riceve il limite di riferimento |
| `src/meshrec/core/config.py` (modifica) | Aggiunge `TetConfig.reference_ratio`, `SweepConfig`, `AxisSpec`, `ExperimentConfig`, `load_experiment` |
| `src/meshrec/core/sweep.py` (nuovo) | Impronta, espansione della griglia, esecuzione per sottoprocessi, riga e registro, dominanza, potatura, verifica |
| `src/meshrec/core/report.py` (nuovo) | HTML statico e istogrammi SVG generati dal registro |
| `src/meshrec/cli.py` (modifica) | Comandi `sweep`, `sweep-verify`, `sweep-report` |
| `src/meshrec/core/pipeline.py` (modifica) | Passa `cfg.tet.reference_ratio` a `volume_metrics` |
| `tests/test_sweep.py` (nuovo) | Impronta, griglia, registro, dominanza, potatura, verifica |
| `tests/test_report.py` (nuovo) | Il report si genera dal registro e contiene le righe |
| `tests/test_quality.py` (modifica) | `thickness` e `fraction_over_ratio` |
| `meshrec/experiments/` (nuovo, tracciato) | Dichiarazioni degli esperimenti e registri JSONL |
| `meshrec/docs/fase-2-sweep.md` (nuovo) | Esiti, criterio di scelta, alternative scartate con il numero |

---

### Task 1: La misura di spessore, e il controllo che la smentisce

Questa e' la fedelta del fronte. La spec la mette per prima perche' se non riproduce i valori noti sulla nuvola sorgente la fase si ferma qui.

La forma scelta: lungo la direzione di minore estensione, l'istogramma dei punti di un muro e' **bimodale**, un modo per faccia. Lo spessore e' la distanza fra i due modi. La divisione fra i due modi avviene al punto medio dell'estensione, che per una lastra cade fra le due facce: nessuna finestra da tarare, nessun parametro nascosto oltre alla larghezza del bin. L'ingombro non va bene al suo posto: sul ritaglio di `lab_frame` l'estensione lungo lo spessore vale 231 mm mentre le due facce distano 176 mm.

**Files:**
- Modify: `src/meshrec/core/quality.py` (in fondo al file)
- Test: `tests/test_quality.py`

**Interfaces:**
- Consumes: nulla
- Produces: `quality.thickness(points: np.ndarray, bin_width: float) -> dict[str, object]`, con chiavi `thickness`, `axis` (indice della direzione principale di minore estensione, **nel sistema principale e non in quello della nuvola**), `extent` (l'ingombro lungo quella direzione), `bimodal` (bool: falso se fra i due modi non c'e' una valle, cioe' se la distribuzione non e' bimodale e la misura non e' valida).

- [ ] **Step 1: Scrivere il test che fallisce**

In fondo a `tests/test_quality.py`:

```python
def test_thickness_measures_the_distance_between_the_two_faces():
    """Su una lastra campionata su entrambe le facce lo spessore e' la distanza fra i modi.

    L'ingombro non risponde alla stessa domanda: con rumore sulle facce e'
    sistematicamente piu grande della distanza fra i piani medi, ed e' il
    motivo per cui la misura e' un istogramma e non un bounding box.
    """
    rng = np.random.default_rng(0)
    n = 20_000
    y = rng.normal(0.0, 2.0, n) + np.where(rng.random(n) < 0.5, 0.0, 176.0)
    points = np.column_stack([rng.uniform(0.0, 2700.0, n), y, rng.uniform(0.0, 2000.0, n)])

    measured = quality.thickness(points, bin_width=1.0)

    assert measured["bimodal"] is True
    assert measured["thickness"] == pytest.approx(176.0, abs=3.0)
    assert measured["extent"] > measured["thickness"]


def test_thickness_declares_itself_invalid_on_a_solid_without_two_faces():
    """Una nuvola piena non ha due modi: la misura lo dichiara invece di restituire un numero."""
    rng = np.random.default_rng(1)
    points = rng.uniform(0.0, 1.0, (5000, 3)) * np.array([2700.0, 176.0, 2000.0])

    measured = quality.thickness(points, bin_width=2.0)

    assert measured["bimodal"] is False
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_quality.py -k thickness -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.quality' has no attribute 'thickness'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In fondo a `src/meshrec/core/quality.py`:

```python
def thickness(points: np.ndarray, bin_width: float) -> dict[str, object]:
    """Spessore come distanza fra i due modi lungo la direzione di minore estensione.

    Si applica indifferentemente a una nuvola e ai vertici di una superficie:
    e' il requisito che rende la misura verificabile, perche' il valore letto
    sulla ricostruzione si confronta con quello letto sulla sorgente.

    L'ingombro non risponde alla stessa domanda. Sul ritaglio di lab_frame
    l'estensione lungo lo spessore vale 231 mm mentre le due facce del muro
    distano 176 mm: il rumore e gli sguinci allargano la scatola, non il muro.

    La divisione fra i due modi cade al punto medio dell'estensione, che per
    una lastra sta fra le due facce: nessuna finestra da tarare. Se fra i due
    modi non c'e' una valle la distribuzione non e' bimodale, la misura non
    e' valida e `bimodal` lo dichiara invece di restituire un numero comunque:
    su una nuvola piena i due massimi cadrebbero comunque da qualche parte, e
    la loro distanza non sarebbe uno spessore.
    """
    values = np.asarray(points, dtype=np.float64)
    centred = values - values.mean(axis=0)
    # eigh su una 3x3: costo indipendente dal numero di punti, al contrario
    # di una SVD sulla matrice intera, che su 6,3 milioni di punti materializza
    # una U da oltre 150 MB per restituire le stesse tre direzioni.
    _, directions = np.linalg.eigh(centred.T @ centred)
    projected = centred @ directions
    extents = np.ptp(projected, axis=0)
    axis = int(np.argmin(extents))

    along = projected[:, axis]
    edges = np.arange(along.min(), along.max() + bin_width, bin_width)
    counts, _ = np.histogram(along, bins=edges)
    centres = (edges[:-1] + edges[1:]) / 2.0
    split = len(counts) // 2

    lower = int(np.argmax(counts[:split]))
    upper = split + int(np.argmax(counts[split:]))
    # La valle fra i due modi deve essere almeno mezza vuota rispetto al modo
    # piu basso. Non e' una soglia tarata ma un'affermazione qualitativa: se
    # fra i due massimi il conteggio non cala, non ci sono due facce.
    valley = int(counts[lower + 1 : upper].min()) if upper > lower + 1 else int(counts[lower])
    bimodal = bool(valley < 0.5 * min(counts[lower], counts[upper]))

    return {
        "thickness": float(centres[upper] - centres[lower]),
        "axis": axis,
        "extent": float(extents[axis]),
        "bimodal": bimodal,
    }
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_quality.py -k thickness -v`
Expected: PASS, 2 test

- [ ] **Step 5: Verificare la misura sui dati reali, che e' il controllo della spec § 6.1**

Da `meshrec/`, con uno script usa-e-getta che non scrive nulla dentro `runs/`:

```powershell
uv run python -c @'
import numpy as np
from meshrec.core import io, quality
for name, path, spacing, known in (
    ("muro", "runs/muro/02_segmented.ply", 9.125, 1245.7),
    ("lab_crop", "runs/lab_crop/02_segmented.ply", 1.192, 176.0),
):
    points, _ = io.read_cloud(path)
    measured = quality.thickness(points, bin_width=spacing)
    error = abs(measured["thickness"] - known) / known
    print(name, measured, f"noto={known} scarto={error:.1%}")
'@
```

Criterio di accettazione, dichiarato qui perche' sia contestabile: **scarto entro il 5% del valore noto su entrambe le nuvole, e `bimodal` vero su entrambe**. Se non regge, fermarsi e riportare i numeri: la spec § 6.1 dice che senza questa misura la fase non prosegue, perche' spazzerebbe su una fedelta che non misura la fedelta.

- [ ] **Step 6: Commit**

```powershell
git add src/meshrec/core/quality.py tests/test_quality.py
git commit -m "feat: lo spessore si misura fra i due modi, non con l'ingombro"
```

---

### Task 2: La frazione fuori vincolo a limite fisso

`tet.min_ratio` e' un asse della griglia, quindi contare gli elementi che violano *il proprio* vincolo confronta candidati contro vincoli diversi. Serve un metro unico.

**Files:**
- Modify: `src/meshrec/core/quality.py` (`volume_metrics`, riga 210)
- Modify: `src/meshrec/core/config.py` (`TetConfig`, riga 111)
- Modify: `src/meshrec/core/pipeline.py:166`
- Test: `tests/test_quality.py`

**Interfaces:**
- Consumes: `quality.radius_edge_ratios(nodes, tets) -> np.ndarray` (esiste)
- Produces: `quality.fraction_over_ratio(nodes, tets, limit: float) -> float`; `quality.volume_metrics(nodes, tets, reference_ratio: float)` con la chiave nuova `radius_edge_over_reference`; `config.TetConfig.reference_ratio: float = 1.8`

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_quality.py`:

```python
def test_the_reference_fraction_does_not_depend_on_the_requested_min_ratio():
    """L'asse di qualita' del fronte usa un metro unico per tutti i candidati.

    Se contasse gli elementi che violano il min_ratio richiesto da ciascun
    candidato, un candidato lasco supererebbe facilmente un vincolo lasco e
    il confronto sarebbe privo di senso.
    """
    nodes = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])

    lasco = quality.fraction_over_ratio(nodes, tets, limit=100.0)
    severo = quality.fraction_over_ratio(nodes, tets, limit=0.1)

    assert lasco == pytest.approx(0.0)
    assert severo == pytest.approx(1.0)
    assert quality.volume_metrics(nodes, tets, reference_ratio=100.0)[
        "radius_edge_over_reference"
    ] == pytest.approx(0.0)


def test_the_reference_ratio_default_lives_in_config():
    from meshrec.core import config

    assert config.TetConfig().reference_ratio == pytest.approx(1.8)
    parameters = inspect.signature(quality.volume_metrics).parameters
    assert parameters["reference_ratio"].default is inspect.Parameter.empty
```

Aggiungere `import inspect` in cima a `tests/test_quality.py` se non c'e'.

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_quality.py -k reference -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.quality' has no attribute 'fraction_over_ratio'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/quality.py`, prima di `volume_metrics`:

```python
def fraction_over_ratio(nodes: np.ndarray, tets: np.ndarray, limit: float) -> float:
    """Frazione di elementi con rapporto raggio-spigolo oltre `limit`.

    `limit` e' un metro esterno e non il vincolo chiesto a TetGen: nel motore
    di sweep min_ratio e' una variabile, e contare le violazioni del proprio
    vincolo confronterebbe candidati contro vincoli diversi.

    La grandezza distingue una mesh sana da una troncata scambiata per
    riuscita: 8,10% sul muro e 9,55% su lab_frame contro l'86,36% della mesh
    tagliata dal tetto ereditato ai punti di Steiner.
    """
    ratios = radius_edge_ratios(nodes, tets)
    finite = ratios[np.isfinite(ratios)]
    return float((finite > limit).mean()) if len(finite) else 1.0
```

In `volume_metrics` cambiare la firma e aggiungere la chiave:

```python
def volume_metrics(nodes: np.ndarray, tets: np.ndarray, reference_ratio: float) -> dict[str, object]:
    """Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi, raggio-spigolo.

    `reference_ratio` e' il metro fisso con cui si conta la frazione fuori
    vincolo: non ha predefinito in firma perche' il suo unico predefinito
    vive in TetConfig.
    """
```

e dentro il dizionario restituito, dopo `"radius_edge_ratio"`:

```python
        "radius_edge_over_reference": fraction_over_ratio(nodes, tets, reference_ratio),
        "reference_ratio": float(reference_ratio),
```

In `src/meshrec/core/config.py`, dentro `TetConfig` dopo `nobisect`:

```python
    reference_ratio: float = Field(
        default=1.8,
        gt=0.0,
        description=(
            "metro fisso con cui lo step 10 conta la frazione di elementi fuori "
            "vincolo raggio-spigolo. Non e' il vincolo chiesto a TetGen: nel "
            "motore di sweep min_ratio e' una variabile della griglia, e una "
            "frazione contata contro il proprio min_ratio confronterebbe "
            "candidati contro vincoli diversi. Il valore 1.8 coincide con il "
            "predefinito di min_ratio perche' e' il metro con cui sono state "
            "misurate le due corse di riferimento (8,10% e 9,55%)"
        ),
    )
```

In `src/meshrec/core/pipeline.py:166`:

```python
        metrics["10_volume_quality"] = quality.volume_metrics(nodes, tets, cfg.tet.reference_ratio)
```

- [ ] **Step 4: Eseguire la suite intera, perche' la firma cambiata ha altri chiamanti**

Run: `uv run pytest -q`
Expected: tutti verdi. Se un test chiama `volume_metrics` con due argomenti, aggiornarlo passando `reference_ratio=1.8` e non aggiungendo un predefinito alla firma.

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/quality.py src/meshrec/core/config.py src/meshrec/core/pipeline.py tests/test_quality.py
git commit -m "feat: la frazione fuori vincolo si conta contro un metro fisso"
```

---

### Task 3: La configurazione dell'esperimento

**Files:**
- Modify: `src/meshrec/core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.SweepConfig` (`workers=4`, `timeout_s=1800`, `runs_root=Path("runs")`, `registry_root=Path("experiments")`, `keep_dominated_artifacts=False`), `config.AxisSpec` (`path: str`, `values: list`), `config.ExperimentConfig` (`name`, `base: Path`, `axes: list[AxisSpec]`, `pairs: list[tuple[str, str]]`, `known_thickness: float | None`, `sweep: SweepConfig`), `config.load_experiment(path) -> ExperimentConfig`

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_config.py`:

```python
def test_experiment_round_trip_and_defaults(tmp_path):
    """L'esperimento sopravvive al round-trip e i suoi predefiniti vivono qui."""
    import yaml

    experiment = config.ExperimentConfig(
        name="muro_ricostruzione",
        base=Path("muro.yaml"),
        axes=[config.AxisSpec(path="tet.min_ratio", values=[1.7, 1.8, 2.0])],
        known_thickness=1245.7,
    )
    assert experiment.sweep.workers == 4
    assert experiment.sweep.timeout_s == 1800
    assert experiment.sweep.keep_dominated_artifacts is False

    path = tmp_path / "esperimento.yaml"
    path.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    assert config.load_experiment(path) == experiment


def test_an_axis_with_no_values_is_rejected():
    with pytest.raises(ValueError):
        config.AxisSpec(path="tet.min_ratio", values=[])
```

Aggiungere `from pathlib import Path` in cima a `tests/test_config.py` se non c'e'.

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_config.py -k experiment -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.config' has no attribute 'ExperimentConfig'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/config.py`, dopo `PipelineConfig`:

```python
class SweepConfig(BaseModel):
    """Motore di sweep: risorse di macchina e politica sugli artefatti."""

    workers: int = Field(
        default=4,
        gt=0,
        description=(
            "candidati in volo insieme, come processi separati. Non e' il numero "
            "di processori: TetGen ha un picco misurato di 1,35 GB sulla corsa "
            "del muro e la macchina di sviluppo ha 7 GB liberi, quindi quattro "
            "candidati sono circa 5,4 GB di picco. Va tarato sulla macchina che "
            "esegue: nessun valore dedotto dai processori logici e' corretto qui"
        ),
    )
    timeout_s: float = Field(
        default=1800.0,
        gt=0.0,
        description=(
            "tetto al tempo di un singolo candidato, perche' uno patologico non "
            "blocchi lo sweep. La corsa completa piu lenta documentata vale 134 s "
            "e il singolo step piu lento 186 s: e' un tetto contro il patologico, "
            "non contro il lento"
        ),
    )
    runs_root: Path = Path("runs")
    registry_root: Path = Path("experiments")
    keep_dominated_artifacts: bool = Field(
        default=False,
        description=(
            "gli artefatti dei candidati dominati vengono rimossi a sweep "
            "concluso; config.yaml e metrics.json restano sempre. Una corsa "
            "completa pesa circa 300 MB"
        ),
    )


class AxisSpec(BaseModel):
    """Un asse della griglia: il percorso puntato del parametro e i suoi livelli."""

    path: str = Field(description="percorso puntato dentro PipelineConfig, es. tet.min_ratio")
    values: list[float | int | bool | None] = Field(min_length=1)


class ExperimentConfig(BaseModel):
    """Dichiarazione di un esperimento. Tracciata da git accanto al proprio registro."""

    name: str
    base: Path = Field(description="configurazione di partenza, es. muro.yaml")
    axes: list[AxisSpec] = Field(min_length=1)
    pairs: list[tuple[str, str]] = Field(
        default_factory=list,
        description=(
            "coppie di assi da incrociare in fattoriale, oltre allo sweep a un "
            "asse alla volta. Si dichiarano solo le coppie che la misura mostra "
            "interagenti: un fattoriale pieno su cinque assi a tre livelli sono "
            "162 candidati"
        ),
    )
    known_thickness: float | None = Field(
        default=None,
        description=(
            "spessore reale misurato [mm], contro cui si controlla la misura "
            "letta sulla nuvola sorgente. E' il controllo che smentisce l'asse "
            "di fedelta: 176 su lab_frame, 1245.7 su muro_generato"
        ),
    )
    sweep: SweepConfig = Field(default_factory=SweepConfig)


def load_experiment(path: Path) -> ExperimentConfig:
    """Legge la dichiarazione di un esperimento."""
    with Path(path).open(encoding="utf-8") as handle:
        return ExperimentConfig.model_validate(yaml.safe_load(handle))
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/config.py tests/test_config.py
git commit -m "feat: l'esperimento e' una configurazione come le altre"
```

---

### Task 4: L'impronta e l'espansione della griglia

**Files:**
- Create: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: `config.PipelineConfig`, `config.ExperimentConfig`, `config.load_config`
- Produces: `sweep.fingerprint(cfg: PipelineConfig) -> str` (sha256 esadecimale); `sweep.with_override(cfg, path: str, value) -> PipelineConfig`; `sweep.expand(experiment: ExperimentConfig, base: PipelineConfig) -> list[tuple[dict[str, object], PipelineConfig]]`, dove il dizionario porta i valori degli assi che distinguono il candidato

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `tests/test_sweep.py`:

```python
"""Il motore di sweep: impronta, griglia, registro, dominanza."""

from pathlib import Path

import pytest

from meshrec.core import config, sweep


def _base() -> config.PipelineConfig:
    return config.PipelineConfig(input=config.InputConfig(path="nuvola.ply", scale=1000.0))


def test_the_fingerprint_ignores_where_the_run_is_written():
    """out_dir e from_step non cambiano il risultato, quindi non cambiano l'identita'.

    Includerli renderebbe diverse due corse identiche, che e' esattamente cio'
    che l'impronta esiste per impedire.
    """
    here = _base()
    elsewhere = _base()
    elsewhere.run.out_dir = Path("runs/altrove")
    elsewhere.run.from_step = 9

    assert sweep.fingerprint(here) == sweep.fingerprint(elsewhere)


def test_the_fingerprint_changes_with_any_processing_parameter():
    changed = sweep.with_override(_base(), "tet.min_ratio", 2.5)

    assert sweep.fingerprint(changed) != sweep.fingerprint(_base())
    assert changed.tet.min_ratio == pytest.approx(2.5)
    assert _base().tet.min_ratio == pytest.approx(1.8)


def test_one_axis_at_a_time_does_not_multiply_the_levels():
    """Tre livelli su due assi sono cinque candidati, non nove: uno per livello piu la base."""
    experiment = config.ExperimentConfig(
        name="prova",
        base=Path("muro.yaml"),
        axes=[
            config.AxisSpec(path="tet.min_ratio", values=[1.7, 1.8, 2.0]),
            config.AxisSpec(path="surface.poisson_depth", values=[8, 9, 10]),
        ],
    )

    candidates = sweep.expand(experiment, _base())

    assert len(candidates) == 5
    assert len({sweep.fingerprint(cfg) for _, cfg in candidates}) == 5
    assert any(axes == {} for axes, _ in candidates)


def test_a_declared_pair_is_crossed_in_full():
    experiment = config.ExperimentConfig(
        name="prova",
        base=Path("muro.yaml"),
        axes=[
            config.AxisSpec(path="tet.min_ratio", values=[1.8, 2.0]),
            config.AxisSpec(path="tet.nobisect", values=[False, True]),
        ],
        pairs=[("tet.min_ratio", "tet.nobisect")],
    )

    candidates = sweep.expand(experiment, _base())
    marks = {sweep.fingerprint(cfg) for _, cfg in candidates}
    atteso = {
        sweep.fingerprint(
            sweep.with_override(sweep.with_override(_base(), "tet.min_ratio", a), "tet.nobisect", b)
        )
        for a in (1.8, 2.0)
        for b in (False, True)
    }

    # Le quattro combinazioni della coppia esistono tutte fra i candidati. Non
    # si contano le etichette `axes` con due voci: una combinazione della
    # coppia che coincide con la base, o con una voce a un asse solo, viene
    # deduplicata per impronta e sopravvive con l'etichetta piu corta.
    assert atteso <= marks
    assert len(marks) == len(candidates)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.sweep'`

- [ ] **Step 3: Scrivere l'implementazione minima**

Creare `src/meshrec/core/sweep.py`:

```python
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
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: PASS, 4 test

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: la griglia si espande un asse alla volta e l'impronta ignora il percorso"
```

---

### Task 5: La riga del registro, e la completezza che il fronte richiede

La riga si costruisce prima di saperla eseguire: e' la parte che porta la provenienza, ed e' testabile senza lanciare un solo sottoprocesso.

**Files:**
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: `sweep.fingerprint`
- Produces: `sweep.file_digest(path) -> str`; `sweep.provenance() -> dict[str, object]` (commit, albero sporco, versioni delle librerie); `sweep.is_complete(metrics: dict) -> bool`; `sweep.append_row(path, row) -> None`; `sweep.load_registry(path) -> list[dict]`; costante `sweep.REQUIRED_STEPS`. La riga completa la costruisce `run_candidate` nel Task 6.

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_sweep.py`:

```python
def test_a_partial_metrics_file_is_not_complete():
    """Il blocco finally di pipeline.run scrive un dizionario parziale quando una corsa muore.

    Quel file e' oggi indistinguibile da uno completo, ed e' il motivo per cui
    un candidato entra nel fronte solo se porta tutte le chiavi di step.
    """
    completo = {name: {} for name in sweep.REQUIRED_STEPS}

    assert sweep.is_complete(completo) is True
    assert sweep.is_complete({"01_load": {}, "08_simplify": {}}) is False
    assert sweep.is_complete({}) is False


def test_the_registry_is_append_only_and_reads_back(tmp_path):
    path = tmp_path / "registro.jsonl"

    sweep.append_row(path, {"fingerprint": "aaa", "outcome": "riuscito"})
    sweep.append_row(path, {"fingerprint": "bbb", "outcome": "fallito"})

    rows = sweep.load_registry(path)
    assert [row["fingerprint"] for row in rows] == ["aaa", "bbb"]
    assert path.read_text(encoding="utf-8").count("\n") == 2


def test_the_digest_of_a_file_changes_with_its_content(tmp_path):
    path = tmp_path / "artefatto.ply"
    path.write_bytes(b"uno")
    prima = sweep.file_digest(path)
    path.write_bytes(b"due")

    assert sweep.file_digest(path) != prima
    assert len(prima) == 64


def test_provenance_records_the_code_that_produced_the_row():
    provenance = sweep.provenance()

    assert len(provenance["commit"]) >= 7
    assert isinstance(provenance["dirty"], bool)
    assert "open3d" in provenance["versions"]
    assert "tetgen" in provenance["versions"]
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -k "registry or digest or provenance or partial" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'REQUIRED_STEPS'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/sweep.py`, aggiungere gli import `subprocess`, `sys` e `from importlib.metadata import version, PackageNotFoundError`, `from pathlib import Path`, e in fondo:

```python
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


def provenance() -> dict[str, object]:
    """Commit del codice, stato dell'albero e versioni delle librerie che contano.

    Senza queste tre cose una riga non e' ricostruibile a distanza di mesi:
    la stessa configurazione su un codice diverso e' un altro esperimento.
    """
    def _git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
        return result.stdout.strip()

    versions: dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "assente"

    return {
        "commit": _git("rev-parse", "HEAD") or "sconosciuto",
        "dirty": bool(_git("status", "--porcelain")),
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
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: la riga del registro porta impronte, commit e versioni"
```

---

### Task 6: L'esecuzione di un candidato, con il fallimento come esito

**Files:**
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: tutto il Task 5
- Produces: `sweep.run_candidate(axes: dict, cfg: PipelineConfig, out_dir: Path, timeout_s: float) -> dict[str, object]`, che restituisce la riga completa e non solleva mai per un candidato fallito

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_sweep.py`:

```python
def test_a_candidate_that_fails_becomes_a_row_and_not_an_exception(tmp_path):
    """Un buco nel registro sarebbe indistinguibile da un candidato mai provato.

    Qui il fallimento e' provocato con una nuvola inesistente, che e' il modo
    piu rapido di far uscire `meshrec run` con codice diverso da zero.
    """
    cfg = config.PipelineConfig(input=config.InputConfig(path=str(tmp_path / "assente.ply")))

    row = sweep.run_candidate({}, cfg, tmp_path / "candidato", timeout_s=120.0)

    assert row["outcome"] == "fallito"
    assert row["exit_code"] != 0
    assert row["stderr"]
    assert row["complete"] is False
    assert row["fingerprint"] == sweep.fingerprint(cfg)


def test_a_candidate_that_succeeds_records_its_artifacts(tmp_path):
    """Sul cubo sintetico la catena intera gira in pochi secondi ed e' l'unico
    caso in cui il motore puo' essere provato end-to-end dentro la suite."""
    from meshrec.core import io, synth

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    cfg = config.PipelineConfig(
        input=config.InputConfig(path=str(cloud)),
        surface=config.SurfaceConfig(poisson_depth=6),
    )

    row = sweep.run_candidate({"tet.min_ratio": 1.8}, cfg, tmp_path / "candidato", timeout_s=600.0)

    assert row["outcome"] == "riuscito"
    assert row["complete"] is True
    assert row["axes"] == {"tet.min_ratio": 1.8}
    assert row["input_digest"] == sweep.file_digest(cloud)
    assert "09_volume.vtu" in row["artifacts"]
    assert row["duration_s"] > 0.0
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -k candidate -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'run_candidate'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/sweep.py`, aggiungere l'import `import time` e in fondo:

```python
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
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg.model_copy(deep=True)
    cfg.run.out_dir = out_dir
    config_path = out_dir / "config.yaml"
    save_config(cfg, config_path)

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
        with metrics_path.open(encoding="utf-8") as handle:
            metrics = json.load(handle)

    artifacts = {
        item.name: file_digest(item)
        for item in sorted(out_dir.iterdir())
        if item.is_file() and item.name not in ("config.yaml", "metrics.json")
    }
    input_path = Path(cfg.input.path)

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
        "input_digest": file_digest(input_path) if input_path.exists() else None,
        "artifacts": artifacts,
        "artifacts_kept": True,
        "out_dir": str(out_dir),
        "rerun": f"uv run meshrec run {config_path}",
        "metrics": metrics,
        "provenance": provenance(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -k candidate -v`
Expected: PASS, 2 test. Il secondo impiega alcune decine di secondi: e' una corsa vera della pipeline.

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: un candidato che fallisce e' una riga, non un'eccezione"
```

---

### Task 7: Il fronte di Pareto e le tre sorveglianze

**Files:**
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: `sweep.is_complete`
- Produces: `sweep.objectives(row) -> tuple[float, float, float] | None`; `sweep.pareto_front(rows) -> list[dict]`; `sweep.SweepDiagnosticWarning`; `sweep.check_sweep(rows, front) -> dict[str, object]`

Gli obiettivi, tutti da minimizzare: errore di spessore, numero di tetraedri, frazione fuori vincolo contro il metro fisso. L'errore di spessore si legge dalla riga come `abs(spessore ricostruito - spessore della sorgente)`, entrambi misurati con `quality.thickness` e scritti nella riga dal Task 9.

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_sweep.py`:

```python
def _row(fingerprint_: str, thickness_error: float, tets: int, over: float, **extra):
    row = {
        "fingerprint": fingerprint_,
        "outcome": "riuscito",
        "complete": True,
        "thickness_error": thickness_error,
        "metrics": {
            "10_volume_quality": {"tets": tets, "radius_edge_over_reference": over},
        },
    }
    row.update(extra)
    return row


def test_a_dominated_candidate_leaves_the_front():
    peggiore = _row("a", thickness_error=20.0, tets=2_000_000, over=0.20)
    migliore = _row("b", thickness_error=5.0, tets=1_000_000, over=0.08)

    front = sweep.pareto_front([peggiore, migliore])

    assert [row["fingerprint"] for row in front] == ["b"]


def test_a_candidate_better_on_one_axis_survives():
    """Il fronte non sceglie: scarta solo chi e' battuto su tutto."""
    leggero = _row("a", thickness_error=20.0, tets=500_000, over=0.20)
    fedele = _row("b", thickness_error=2.0, tets=2_000_000, over=0.09)

    front = sweep.pareto_front([leggero, fedele])

    assert {row["fingerprint"] for row in front} == {"a", "b"}


def test_an_incomplete_candidate_never_enters_the_front():
    parziale = _row("a", thickness_error=1.0, tets=1, over=0.0)
    parziale["complete"] = False
    normale = _row("b", thickness_error=9.0, tets=900_000, over=0.10)

    assert [row["fingerprint"] for row in sweep.pareto_front([parziale, normale])] == ["b"]


def test_a_front_as_large_as_the_grid_is_reported():
    """Se nessun candidato e' dominato gli assi non discriminano, e senza
    questa sorveglianza il caso si presenterebbe come un fronte ricco."""
    rows = [
        _row("a", thickness_error=1.0, tets=3, over=0.3),
        _row("b", thickness_error=2.0, tets=2, over=0.2),
        _row("c", thickness_error=3.0, tets=1, over=0.1),
    ]

    with pytest.warns(sweep.SweepDiagnosticWarning, match="non discrimina"):
        report = sweep.check_sweep(rows, sweep.pareto_front(rows))

    assert report["front_is_whole_grid"] is True


def test_more_than_half_failing_is_reported():
    rows = [
        _row("a", thickness_error=1.0, tets=1, over=0.1),
        {"fingerprint": "b", "outcome": "fallito", "complete": False},
        {"fingerprint": "c", "outcome": "timeout", "complete": False},
    ]

    with pytest.warns(sweep.SweepDiagnosticWarning, match="griglia"):
        report = sweep.check_sweep(rows, sweep.pareto_front(rows))

    assert report["failed_fraction"] == pytest.approx(2 / 3)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -k "front or dominated or failing or axis" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'pareto_front'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/sweep.py`, aggiungere l'import `import warnings` e in fondo:

```python
class SweepDiagnosticWarning(UserWarning):
    """Lo sweep e' arrivato in fondo ma il suo esito non e' utilizzabile cosi' com'e'."""


def objectives(row: dict[str, object]) -> tuple[float, float, float] | None:
    """I tre assi del fronte, tutti da minimizzare, o None se la riga non ne ha.

    Errore di spessore, numero di tetraedri, frazione di elementi oltre il
    metro fisso. La fedelta' e' lo spessore e non l'errore bidirezionale
    perche' quello resta piccolo mentre Poisson ingrassa il muro reale da
    176 a 214 mm: e' cieco proprio sull'errore che governa la rigidezza.
    """
    if row.get("outcome") != "riuscito" or not row.get("complete"):
        return None
    volume = row.get("metrics", {}).get("10_volume_quality")
    if volume is None or row.get("thickness_error") is None:
        return None
    return (
        float(row["thickness_error"]),
        float(volume["tets"]),
        float(volume["radius_edge_over_reference"]),
    )


def _dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def pareto_front(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Righe non dominate. Nessun punteggio pesato, nessun peso arbitrario.

    Un candidato cade se un altro lo eguaglia o lo batte su tutti e tre gli
    assi e lo batte su almeno uno. I candidati falliti o incompleti non
    entrano: restano righe, ma non sono confrontabili.
    """
    # ponytail: confronto O(n^2), adeguato a decine di candidati; se la
    # griglia crescera' di un ordine, ordinare per il primo asse e potare.
    scored = [(row, objectives(row)) for row in rows]
    valid = [(row, score) for row, score in scored if score is not None]
    return [
        row
        for row, score in valid
        if not any(_dominates(other, score) for _, other in valid if other != score)
    ]


def check_sweep(
    rows: list[dict[str, object]], front: list[dict[str, object]]
) -> dict[str, object]:
    """Le due sorveglianze sull'esito complessivo dello sweep.

    Nessuna delle due e' tarata: sono affermazioni qualitative, come la
    soglia a meta di min_ratio e quella della copertura d'appoggio. Quando
    piu di meta della griglia non arriva in fondo e' la griglia a stare nel
    posto sbagliato; quando nessun candidato e' dominato gli assi non stanno
    discriminando e il fronte non sta scartando nulla.
    """
    failed = [row for row in rows if row.get("outcome") != "riuscito"]
    comparable = [row for row in rows if objectives(row) is not None]
    failed_fraction = len(failed) / len(rows) if rows else 0.0
    front_is_whole_grid = bool(comparable) and len(front) == len(comparable)

    if failed_fraction > 0.5:
        warnings.warn(
            f"il {failed_fraction:.0%} dei candidati non arriva in fondo: "
            "e' la griglia a stare nel posto sbagliato, non i candidati",
            SweepDiagnosticWarning,
            stacklevel=2,
        )
    if front_is_whole_grid:
        warnings.warn(
            f"il fronte contiene tutti e {len(front)} i candidati confrontabili: "
            "non discrimina, e non sta scartando nulla",
            SweepDiagnosticWarning,
            stacklevel=2,
        )

    return {
        "candidates": len(rows),
        "failed": len(failed),
        "failed_fraction": failed_fraction,
        "comparable": len(comparable),
        "front": len(front),
        "front_is_whole_grid": front_is_whole_grid,
    }
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: il fronte scarta per dominanza e dichiara quando non discrimina"
```

---

### Task 8: Lo sweep completo, con lo spessore misurato e la potatura

**Files:**
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: tutti i task precedenti, `quality.thickness`
- Produces: `sweep.measure_thickness_error(row, source_thickness: float) -> float | None`; `sweep.prune(rows, front) -> int` (numero di file rimossi); `sweep.run_experiment(experiment: ExperimentConfig, base: PipelineConfig) -> dict[str, object]`

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_sweep.py`:

```python
def test_pruning_keeps_config_and_metrics_and_marks_the_row(tmp_path):
    """Una corsa completa pesa circa 300 MB: i dominati conservano la riga, non i file."""
    dominato = tmp_path / "dominato"
    dominato.mkdir()
    for name in ("config.yaml", "metrics.json", "09_volume.vtu", "wall_model.inp"):
        (dominato / name).write_text("x", encoding="utf-8")
    sopravvive = tmp_path / "fronte"
    sopravvive.mkdir()
    (sopravvive / "09_volume.vtu").write_text("x", encoding="utf-8")

    scartato = _row("a", thickness_error=20.0, tets=2, over=0.5, out_dir=str(dominato))
    tenuto = _row("b", thickness_error=1.0, tets=1, over=0.1, out_dir=str(sopravvive))

    removed = sweep.prune([scartato, tenuto], [tenuto])

    assert removed == 2
    assert (dominato / "config.yaml").exists()
    assert (dominato / "metrics.json").exists()
    assert not (dominato / "09_volume.vtu").exists()
    assert (sopravvive / "09_volume.vtu").exists()
    assert scartato["artifacts_kept"] is False
    assert tenuto["artifacts_kept"] is True
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -k pruning -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'prune'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/core/sweep.py`, aggiungere `from concurrent.futures import ThreadPoolExecutor` e in fondo:

```python
def measure_thickness_error(row: dict[str, object], source_thickness: float) -> float | None:
    """Scarto fra lo spessore ricostruito e quello della nuvola sorgente [mm].

    Lo spessore ricostruito si misura sui vertici della superficie riparata,
    cioe' sulla geometria che entra nella tetraedrizzazione, con la stessa
    funzione usata sulla sorgente: e' il confronto a misura unica che rende
    l'asse verificabile.
    """
    from meshrec.core import quality

    repaired = Path(row["out_dir"]) / "06_repaired.ply"
    if not repaired.exists():
        return None
    import open3d as o3d

    mesh = o3d.io.read_triangle_mesh(str(repaired))
    vertices = np.asarray(mesh.vertices)
    spacing = float(row["metrics"]["01_load"]["spacing"])
    measured = quality.thickness(vertices, bin_width=spacing)
    row["thickness_reconstructed"] = measured["thickness"]
    row["thickness_bimodal"] = measured["bimodal"]
    if not measured["bimodal"]:
        return None
    return abs(measured["thickness"] - source_thickness)


def prune(rows: list[dict[str, object]], front: list[dict[str, object]]) -> int:
    """Rimuove gli artefatti dei dominati; config.yaml e metrics.json restano.

    La riga dichiara `artifacts_kept: false` e porta gia' il comando che li
    rigenera: config completo piu impronta del codice rendono la
    riesecuzione un comando, non una ricostruzione.
    """
    kept = {row["fingerprint"] for row in front}
    removed = 0
    for row in rows:
        if row["fingerprint"] in kept or not row.get("out_dir"):
            continue
        for item in Path(row["out_dir"]).iterdir():
            if item.is_file() and item.name not in ("config.yaml", "metrics.json"):
                item.unlink()
                removed += 1
        row["artifacts_kept"] = False
    return removed


def run_experiment(
    experiment: ExperimentConfig, base: PipelineConfig
) -> dict[str, object]:
    """Espande la griglia, esegue i candidati in parallelo, scrive il registro.

    I thread attendono soltanto i sottoprocessi e non calcolano nulla, quindi
    OMP_NUM_THREADS=1 continua a valere dentro ciascun candidato e la
    riproducibilita verificata in Fase 1 regge invariata.
    """
    from meshrec.core import io, quality, segment

    root = Path(experiment.sweep.runs_root) / experiment.name
    registry = Path(experiment.sweep.registry_root) / experiment.name / "registro.jsonl"

    # La sorgente si legge con load_cloud, che applica input.scale: read_cloud
    # non lo fa, e su una configurazione con scale 1000 la misura uscirebbe in
    # metri contro un valore noto in millimetri. Si segmenta poi con i
    # parametri della base perche' la segmentazione non e' un asse, quindi e'
    # comune a tutti i candidati, ed e' la stessa nuvola su cui si misura lo
    # spessore ricostruito.
    source, load_metrics = io.load_cloud(base.input)
    spacing = float(load_metrics["spacing"])
    source, _ = segment.segment_cloud(source, base.segment, spacing)
    source_thickness = quality.thickness(source, bin_width=spacing)
    if experiment.known_thickness is not None:
        scarto = abs(source_thickness["thickness"] - experiment.known_thickness)
        if not source_thickness["bimodal"] or scarto / experiment.known_thickness > 0.05:
            raise ValueError(
                "la misura di spessore non riproduce il valore noto sulla nuvola "
                f"sorgente: letto {source_thickness['thickness']:.1f} mm contro "
                f"{experiment.known_thickness:.1f} mm noti, bimodale="
                f"{source_thickness['bimodal']}. L'asse di fedelta non e' "
                "utilizzabile e lo sweep non parte"
            )

    candidates = expand(experiment, base)
    with ThreadPoolExecutor(max_workers=experiment.sweep.workers) as pool:
        rows = list(
            pool.map(
                lambda item: run_candidate(
                    item[0],
                    item[1],
                    root / fingerprint(item[1])[:12],
                    experiment.sweep.timeout_s,
                ),
                candidates,
            )
        )

    for row in rows:
        row["thickness_source"] = source_thickness["thickness"]
        row["thickness_error"] = measure_thickness_error(row, source_thickness["thickness"])

    front = pareto_front(rows)
    summary = check_sweep(rows, front)
    if not experiment.sweep.keep_dominated_artifacts:
        summary["pruned_files"] = prune(rows, front)

    front_marks = {row["fingerprint"] for row in front}
    for row in rows:
        row["on_front"] = row["fingerprint"] in front_marks
        append_row(registry, row)

    return {"summary": summary, "rows": rows, "front": front, "registry": str(registry)}
```

Aggiungere `import numpy as np` in cima al modulo.

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: lo sweep misura lo spessore, seleziona il fronte e pota i dominati"
```

---

### Task 9: `sweep verify`, il controllo che smentisce il registro

**Files:**
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_sweep.py`

**Interfaces:**
- Produces: `sweep.verify_registry(path: Path) -> list[dict[str, object]]`, una voce per riga con `fingerprint`, `stale` (bool) e `reason`

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_sweep.py`:

```python
def test_verify_declares_stale_a_row_whose_artifact_changed(tmp_path):
    """La prova a variabile unica: si altera un artefatto e la riga deve cadere.

    E' il caso della Fase 1 in cui un wall_model.inp di una corsa superata e'
    rimasto accanto a un metrics.json fermo a 08_simplify, e niente nei due
    file diceva che non appartenessero alla stessa elaborazione.
    """
    out_dir = tmp_path / "candidato"
    out_dir.mkdir()
    artefatto = out_dir / "wall_model.inp"
    artefatto.write_text("corsa corrente", encoding="utf-8")

    registry = tmp_path / "registro.jsonl"
    sweep.append_row(
        registry,
        {
            "fingerprint": "aaa",
            "out_dir": str(out_dir),
            "artifacts_kept": True,
            "artifacts": {"wall_model.inp": sweep.file_digest(artefatto)},
        },
    )

    assert all(voce["stale"] is False for voce in sweep.verify_registry(registry))

    artefatto.write_text("corsa superata", encoding="utf-8")
    esito = sweep.verify_registry(registry)

    assert esito[0]["stale"] is True
    assert "wall_model.inp" in esito[0]["reason"]


def test_verify_does_not_call_pruned_rows_stale(tmp_path):
    registry = tmp_path / "registro.jsonl"
    sweep.append_row(
        registry,
        {
            "fingerprint": "bbb",
            "out_dir": str(tmp_path / "assente"),
            "artifacts_kept": False,
            "artifacts": {"wall_model.inp": "0" * 64},
        },
    )

    esito = sweep.verify_registry(registry)

    assert esito[0]["stale"] is False
    assert "potati" in esito[0]["reason"]
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_sweep.py -k verify -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'verify_registry'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In fondo a `src/meshrec/core/sweep.py`:

```python
def verify_registry(path: Path) -> list[dict[str, object]]:
    """Ricalcola le impronte degli artefatti e marca stantia ogni riga che non torna.

    E' il primo principio applicato al registro stesso: senza questo controllo
    una riga e i file che dice di descrivere possono divergere in silenzio, ed
    e' esattamente cio' che e' accaduto in Fase 1.

    Una riga potata non e' stantia: dichiara di non avere piu artefatti, e
    quella dichiarazione e' coerente con il disco.
    """
    esito: list[dict[str, object]] = []
    for row in load_registry(path):
        if not row.get("artifacts_kept", True):
            esito.append(
                {"fingerprint": row["fingerprint"], "stale": False, "reason": "artefatti potati"}
            )
            continue

        mancanti: list[str] = []
        diversi: list[str] = []
        for name, digest in row.get("artifacts", {}).items():
            item = Path(row["out_dir"]) / name
            if not item.exists():
                mancanti.append(name)
            elif file_digest(item) != digest:
                diversi.append(name)

        reason = ""
        if diversi:
            reason = f"impronta diversa: {', '.join(sorted(diversi))}"
        elif mancanti:
            reason = f"artefatti assenti: {', '.join(sorted(mancanti))}"
        esito.append(
            {
                "fingerprint": row["fingerprint"],
                "stale": bool(diversi or mancanti),
                "reason": reason or "coerente",
            }
        )
    return esito
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_sweep.py -k verify -v`
Expected: PASS, 2 test

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/sweep.py tests/test_sweep.py
git commit -m "feat: sweep verify rilegge le impronte e dichiara stantie le righe che non tornano"
```

---

### Task 10: Il report, generato dal registro

**Files:**
- Create: `src/meshrec/core/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `sweep.load_registry`, `sweep.pareto_front`
- Produces: `report.histogram_svg(values: list[float], title: str, bins: int) -> str`; `report.write_report(registry_path: Path, out_path: Path) -> Path`

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `tests/test_report.py`:

```python
"""Il report si genera dal registro e non da altro."""

from meshrec.core import report, sweep


def test_the_report_lists_every_row_and_marks_the_front(tmp_path):
    registry = tmp_path / "registro.jsonl"
    for mark, error, tets, on_front in (("aaa", 2.0, 1000, True), ("bbb", 40.0, 9000, False)):
        sweep.append_row(
            registry,
            {
                "fingerprint": mark,
                "axes": {"tet.min_ratio": 1.8},
                "outcome": "riuscito",
                "complete": True,
                "on_front": on_front,
                "thickness_error": error,
                "duration_s": 12.0,
                "metrics": {
                    "10_volume_quality": {
                        "tets": tets,
                        "radius_edge_over_reference": 0.08,
                        "min_dihedral_deg": {"median": 38.0},
                    }
                },
            },
        )

    out = report.write_report(registry, tmp_path / "report.html")
    html = out.read_text(encoding="utf-8")

    assert "aaa" in html and "bbb" in html
    assert "fronte" in html.lower()
    assert "<svg" in html


def test_the_histogram_is_svg_without_any_chart_library():
    svg = report.histogram_svg([1.0, 2.0, 2.0, 3.0], title="prova", bins=3)

    assert svg.startswith("<svg")
    assert svg.count("<rect") >= 3
    assert "prova" in svg
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_report.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.report'`

- [ ] **Step 3: Scrivere l'implementazione minima**

Creare `src/meshrec/core/report.py`:

```python
"""Report statico generato dal registro: tabella, fronte, istogrammi SVG.

Nessuna libreria di grafici: per pochi istogrammi non si giustifica, ed e'
gia' escluso dalla spec di architettura. Nessuna miniatura e nessun
rendering 3D: il confronto visivo arriva con il viewport della Fase 3, che
rivestira' questo report invece di riscriverlo.
"""

from __future__ import annotations

import html
from pathlib import Path

from meshrec.core.sweep import load_registry

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "impronta"),
    ("axes", "assi"),
    ("outcome", "esito"),
    ("thickness_error", "errore di spessore [mm]"),
    ("tets", "tetraedri"),
    ("over", "fuori vincolo"),
    ("dihedral", "diedro min., mediana"),
    ("duration_s", "durata [s]"),
)


def histogram_svg(values: list[float], title: str, bins: int) -> str:
    """Istogramma come SVG scritto a mano, senza dipendenze."""
    if not values:
        return f"<svg width='320' height='140'><text x='8' y='20'>{html.escape(title)}: vuoto</text></svg>"

    low, high = min(values), max(values)
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    tallest = max(counts) or 1

    bars = "".join(
        f"<rect x='{8 + index * (300 / bins):.1f}' y='{120 - 100 * count / tallest:.1f}' "
        f"width='{300 / bins - 2:.1f}' height='{100 * count / tallest:.1f}' fill='#456'/>"
        for index, count in enumerate(counts)
    )
    return (
        f"<svg width='320' height='140' role='img'>"
        f"<text x='8' y='14' font-size='11'>{html.escape(title)}</text>{bars}"
        f"<text x='8' y='134' font-size='10'>{low:.3g}</text>"
        f"<text x='260' y='134' font-size='10'>{high:.3g}</text></svg>"
    )


def _cell(row: dict[str, object], key: str) -> str:
    volume = row.get("metrics", {}).get("10_volume_quality", {})
    if key == "tets":
        value = volume.get("tets")
    elif key == "over":
        value = volume.get("radius_edge_over_reference")
    elif key == "dihedral":
        value = volume.get("min_dihedral_deg", {}).get("median")
    else:
        value = row.get(key)

    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, dict):
        return ", ".join(f"{name}={item}" for name, item in value.items()) or "base"
    return html.escape(str(value)) if value is not None else ""


def write_report(registry_path: Path, out_path: Path) -> Path:
    """Scrive il report HTML a partire dal solo registro.

    Il registro e' l'unica rappresentazione autoritativa: la tabella piatta
    per l'appendice si genera da qui e non si mantiene a mano, che e' il modo
    in cui in Fase 1 numeri di corse diverse sono finiti fianco a fianco.
    """
    rows = load_registry(registry_path)
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in _COLUMNS)
    body = "".join(
        "<tr class='{}'>{}</tr>".format(
            "fronte" if row.get("on_front") else "",
            "".join(f"<td>{_cell(row, key)}</td>" for key, _ in _COLUMNS),
        )
        for row in rows
    )

    errors = [row["thickness_error"] for row in rows if isinstance(row.get("thickness_error"), float)]
    tets = [
        float(row["metrics"]["10_volume_quality"]["tets"])
        for row in rows
        if row.get("metrics", {}).get("10_volume_quality")
    ]

    document = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Sweep — {html.escape(registry_path.parent.name)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
table {{ border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: right; }}
th {{ background: #eee; }}
tr.fronte td {{ background: #eaf3ea; font-weight: 600; }}
</style></head><body>
<h1>Sweep — {html.escape(registry_path.parent.name)}</h1>
<p>{len(rows)} candidati. Le righe evidenziate sono il <strong>fronte</strong> di Pareto:
errore di spessore, numero di tetraedri e frazione fuori vincolo, tutti da minimizzare.</p>
<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<h2>Distribuzioni</h2>
{histogram_svg(errors, "errore di spessore [mm]", bins=12)}
{histogram_svg(tets, "tetraedri", bins=12)}
</body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS, 2 test

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/core/report.py tests/test_report.py
git commit -m "feat: il report nasce dal registro, in HTML e SVG senza dipendenze"
```

---

### Task 11: I comandi, e la prova end-to-end sul cubo sintetico

**Files:**
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `sweep.run_experiment`, `sweep.verify_registry`, `report.write_report`, `config.load_experiment`, `config.load_config`
- Produces: i comandi `meshrec sweep <esperimento.yaml>`, `meshrec sweep-verify <registro.jsonl>`, `meshrec sweep-report <registro.jsonl> --out <file.html>`

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_cli.py`:

```python
def test_the_sweep_command_runs_a_two_candidate_grid_on_the_synthetic_cube(tmp_path):
    """Prova end-to-end del motore: griglia, sottoprocessi, registro, fronte.

    Il cubo e' l'unica geometria su cui la catena intera sta dentro la suite.
    Verifica che la catena non si spezzi, non che produca qualcosa di
    sensato: quello si misura sulle due corse reali, fuori dai test.
    """
    import yaml

    from meshrec.core import config, io, synth, sweep

    cloud = tmp_path / "cubo.ply"
    io.write_cloud(cloud, synth.sample_box_surface(size=(100.0, 40.0, 200.0), spacing=4.0))
    base = config.PipelineConfig(
        input=config.InputConfig(path=str(cloud)),
        surface=config.SurfaceConfig(poisson_depth=6),
    )
    base_path = tmp_path / "base.yaml"
    config.save_config(base, base_path)

    experiment = config.ExperimentConfig(
        name="cubo",
        base=base_path,
        axes=[config.AxisSpec(path="tet.min_ratio", values=[2.0])],
        sweep=config.SweepConfig(
            workers=2, runs_root=tmp_path / "runs", registry_root=tmp_path / "experiments"
        ),
    )
    experiment_path = tmp_path / "cubo.yaml"
    experiment_path.write_text(
        yaml.safe_dump(experiment.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )

    assert cli.main(["sweep", str(experiment_path)]) == 0

    registry = tmp_path / "experiments" / "cubo" / "registro.jsonl"
    rows = sweep.load_registry(registry)
    assert len(rows) == 2
    assert all(row["outcome"] == "riuscito" for row in rows)
    assert any(row["on_front"] for row in rows)

    assert cli.main(["sweep-verify", str(registry)]) == 0
    assert cli.main(["sweep-report", str(registry), "--out", str(tmp_path / "r.html")]) == 0
    assert (tmp_path / "r.html").exists()
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_cli.py -k sweep -v`
Expected: FAIL con `SystemExit: 2` — `argument command: invalid choice: 'sweep'`

- [ ] **Step 3: Scrivere l'implementazione minima**

In `src/meshrec/cli.py`, dentro `_build_parser` prima del `return`:

```python
    sweep_command = commands.add_parser("sweep", help="esegue una griglia di candidati")
    sweep_command.add_argument("experiment", type=Path)

    verify_command = commands.add_parser(
        "sweep-verify", help="ricontrolla le impronte degli artefatti di un registro"
    )
    verify_command.add_argument("registry", type=Path)

    report_command = commands.add_parser("sweep-report", help="genera il report da un registro")
    report_command.add_argument("registry", type=Path)
    report_command.add_argument("--out", type=Path, required=True)
```

In `main`, dopo il ramo `init` e prima di `cfg = load_config(args.config)`:

```python
    if args.command == "sweep":
        from meshrec.core import sweep

        experiment = load_experiment(args.experiment)
        try:
            result = sweep.run_experiment(experiment, load_config(experiment.base))
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False, default=float))
        print(f"registro in {result['registry']}", file=sys.stderr)
        return 0

    if args.command == "sweep-verify":
        from meshrec.core import sweep

        esito = sweep.verify_registry(args.registry)
        print(json.dumps(esito, indent=2, ensure_ascii=False))
        stantie = [voce for voce in esito if voce["stale"]]
        if stantie:
            print(f"{len(stantie)} righe stantie", file=sys.stderr)
            return 1
        return 0

    if args.command == "sweep-report":
        from meshrec.core import report

        print(f"report in {report.write_report(args.registry, args.out)}")
        return 0
```

Aggiornare l'import in cima: `from meshrec.core.config import InputConfig, PipelineConfig, load_config, load_experiment, save_config`.

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS. Poi la suite intera: `uv run pytest -q`, attesa verde.

- [ ] **Step 5: Commit**

```powershell
git add src/meshrec/cli.py tests/test_cli.py
git commit -m "feat: i comandi sweep, sweep-verify e sweep-report"
```

---

### Task 12: I due esperimenti reali, e il documento degli esiti

Questo task non aggiunge codice: e' il deliverable. Il motore va esercitato su entrambe le corse di riferimento, perche' un criterio misurato solo sul muro sintetico verifica che la catena non si spezzi, non che produca qualcosa di sensato.

**Files:**
- Create: `meshrec/experiments/muro/esperimento.yaml`, `meshrec/experiments/lab_crop/esperimento.yaml` (tracciati)
- Create: `meshrec/experiments/muro/registro.jsonl`, `meshrec/experiments/lab_crop/registro.jsonl` (tracciati, prodotti dalle corse)
- Create: `meshrec/docs/fase-2-sweep.md`
- Modify: `meshrec/muro.yaml`, `meshrec/lab.yaml` (solo se il fronte indica parametri diversi da quelli attuali)

- [ ] **Step 1: Scrivere le due dichiarazioni di esperimento**

`meshrec/experiments/muro/esperimento.yaml`:

```yaml
name: muro
base: muro.yaml
known_thickness: 1245.7
axes:
  - path: downsample.voxel_size
    values: [18.25, 25.0, 35.0]
  - path: surface.poisson_depth
    values: [7, 8, 9]
  - path: surface.density_quantile
    values: [0.0, 0.05, 0.12]
  - path: tet.min_ratio
    values: [1.7, 1.8, 2.0, 2.5]
  - path: tet.nobisect
    values: [false, true]
sweep:
  workers: 4
  timeout_s: 1800.0
```

`meshrec/experiments/lab_crop/esperimento.yaml`: identico nella forma, con `base: lab.yaml`, `known_thickness: 176.0` e `downsample.voxel_size` sui livelli `[5.0, 10.0, 15.0]`, che sono l'intorno del valore che rende praticabile lo step 4 su quella nuvola.

- [ ] **Step 2: Eseguire i due sweep**

```powershell
uv run meshrec sweep experiments/muro/esperimento.yaml
uv run meshrec sweep experiments/lab_crop/esperimento.yaml
```

Attesa: circa venti minuti ciascuno con quattro processi. Se `run_experiment` si ferma subito con il `ValueError` sulla misura di spessore, **fermarsi qui**: e' il controllo della spec § 6.1 che ha fatto il proprio lavoro, e va riportato invece di aggirato.

- [ ] **Step 3: Leggere le sorveglianze prima dei risultati**

Il sommario stampato porta `failed_fraction` e `front_is_whole_grid`. Se la prima supera 0,5 o la seconda e' vera, l'esito dello sweep non e' utilizzabile cosi' com'e' e va riportato come tale: nel primo caso la griglia sta nel posto sbagliato, nel secondo gli assi non discriminano. In entrambi i casi si corregge la griglia e si rilancia, e **entrambe le corse restano nel registro**, perche' il registro e' in sola aggiunta.

- [ ] **Step 4: Generare i due report e scegliere le configurazioni**

```powershell
uv run meshrec sweep-report experiments/muro/registro.jsonl --out experiments/muro/report.html
uv run meshrec sweep-report experiments/lab_crop/registro.jsonl --out experiments/lab_crop/report.html
```

La scelta fra i candidati del fronte e' una decisione dichiarata, non un punteggio: si sceglie un criterio, lo si scrive, e si riportano gli scartati con il numero che li scarta. Il modello e' la sezione «Il predefinito 6 e il suo margine» di `fase-1-tolleranza-set.md`.

- [ ] **Step 5: Verificare i registri**

```powershell
uv run meshrec sweep-verify experiments/muro/registro.jsonl
uv run meshrec sweep-verify experiments/lab_crop/registro.jsonl
```

Poi la prova a variabile unica del criterio di accettazione 4: si altera di un byte un artefatto conservato di un candidato del fronte, si rilancia `sweep-verify`, si verifica che quella riga risulti stantia, e si ripristina l'artefatto rieseguendo il comando `rerun` della sua riga.

- [ ] **Step 6: Scrivere `meshrec/docs/fase-2-sweep.md`**

Struttura, sul modello di `fase-1-min-ratio.md`:

1. **Che cosa e' stato misurato e come** — le due dichiarazioni di esperimento, il numero di candidati, la macchina, la durata.
2. **La verifica della misura di spessore** — i valori letti sulle due nuvole sorgente contro i 1245,7 e 176 mm noti, con lo scarto. E' il controllo che rende l'asse di fedelta utilizzabile e va riportato per primo.
3. **Risultati** — la tabella dei candidati del fronte, con i tre assi e le metriche riportate accanto (Hausdorff, mediana del diedro minimo, copertura d'appoggio).
4. **Le sorveglianze** — frazione di falliti e taglia del fronte contro la griglia.
5. **La scelta, con il criterio dichiarato** — quale candidato diventa `muro.yaml` e quale `lab.yaml`, e perche'; gli scartati con il numero che li scarta.
6. **`nobisect`: leva giusta o solo quella che funziona** — se qualche taratura della ricostruzione elimina le strozzature sotto il millimetro, `tet.nobisect: false` converge su `lab_crop` e la domanda della Fase 1 ha risposta. Se nessuna lo fa, e' un **esito negativo documentato**, non un fallimento: `nobisect` resta la leva, con i numeri che lo sostengono.
7. **Che cosa questo lavoro non chiude** — nulla rivalida la superficie dopo lo step 8; `FACE_FRONT` e `FACE_BACK` restano decorativi su una scansione reale; i nomi dei set restano convenzioni; il controllo dei dati con Abaqus resta dovuto.

- [ ] **Step 7: Aggiornare `fase-1-debito.md`**

Le voci che questo lavoro chiude o precisa vanno aggiornate al loro posto, senza cancellare come ci si e' arrivati: e' la convenzione gia' seguita in quel documento.

- [ ] **Step 8: Commit**

```powershell
git add meshrec/experiments/muro/esperimento.yaml meshrec/experiments/muro/registro.jsonl meshrec/experiments/lab_crop/esperimento.yaml meshrec/experiments/lab_crop/registro.jsonl meshrec/docs/fase-2-sweep.md meshrec/docs/fase-1-debito.md
git commit -m "docs: il fronte di Pareto sceglie le configurazioni, e il registro porta la loro provenienza"
```

Se il fronte indica parametri diversi da quelli attuali, `meshrec/muro.yaml` e `meshrec/lab.yaml` vanno aggiornati in un commit separato, che dichiara quale riga del registro li giustifica.

---

## Criteri di accettazione della fase

Da verificare al termine del Task 12, con il comando che li dimostra accanto:

1. Due registri tracciati da git, uno per corsa di riferimento — `git ls-files meshrec/experiments`.
2. Il fronte e' piu piccolo della griglia su entrambe — campo `front` contro `comparable` nel sommario.
3. La misura di spessore riproduce i valori noti sulle nuvole sorgente — sezione 2 di `fase-2-sweep.md`.
4. `sweep-verify` dichiara stantia una riga resa stantia apposta — Task 12, Step 5.
5. Un candidato ucciso produce una riga e non interrompe lo sweep — `tests/test_sweep.py::test_a_candidate_that_fails_becomes_a_row_and_not_an_exception`, piu la verifica sulle corse reali se qualche candidato e' fallito davvero.
6. Le configurazioni scelte sono documentate con criterio dichiarato e alternative scartate col numero — sezione 5 di `fase-2-sweep.md`.
7. La suite passa — `uv run pytest -q`, attesa: i 126 di partenza piu i circa 20 nuovi.
