# MeshRec Fase 1 — Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** portare `meshrec` da nuvola di punti a file `.inp` pronto all'analisi statica lineare, eseguibile da riga di comando, senza interfaccia grafica.

**Architecture:** dieci moduli in `src/meshrec/core/`, ciascuno con una responsabilità sola e nessuna conoscenza degli altri. Ogni step riceve un artefatto più i propri parametri e restituisce un artefatto più un dizionario di metriche. La sequenza vive soltanto in `core/pipeline.py`; `src/meshrec/cli.py` è l'unico consumatore e resta fuori dal core.

**Tech Stack:** Python 3.12, numpy 2.5, scipy 1.18, open3d 0.19, pymeshfix 0.18.1, pymeshlab 2025.7, tetgen 0.8.4, meshio 5.3.5, pydantic 2.13, PyYAML 6.0, pytest 8.

## Global Constraints

- **Unità di lavoro:** mm, N, MPa, tonnellata, secondo. Gravità `9810.0` mm/s², densità in t/mm³. Vivono in `core/config.py` e da nessun'altra parte.
- **Unico luogo dei valori predefiniti:** `core/config.py`. Nessuna funzione del core può avere un valore numerico predefinito nella propria firma se quel valore è un parametro di elaborazione. I parametri arrivano dal chiamante.
- **Contratto degli step:** ogni funzione di step restituisce `(artefatto, metrics: dict[str, object])`. Nessuno step importa un altro step. Solo `pipeline.py` conosce la sequenza.
- **Lingua:** codice, commenti, docstring e messaggi di commit in italiano, senza lettere accentate nei file sorgente `.py` (il repository segue già questa convenzione: si scrive `qualita`, non `qualità`). I documenti `.md` usano le accentate normalmente.
- **Deviazioni di API accertate in Fase 0, vincolanti:**
  - `tetgen.TetGen.tetrahedralize()` restituisce quattro valori: destrutturare con `nodes, tets, *_ =`.
  - `maxvolume` è inerte da solo: richiede `fixedvolume=True` nella stessa chiamata.
  - `pymeshfix.MeshFix` espone il risultato come `.points` e `.faces`, non `.v`/`.f`.
  - `pymeshlab.filter_list()` è una funzione di modulo, non un metodo di `MeshSet`.
  - Il tipo percentuale di PyMeshLab è `pymeshlab.PercentageValue`.
  - Filtri PyMeshLab: `meshing_isotropic_explicit_remeshing`, `get_hausdorff_distance`.
- **Guardia di superficie chiusa mantenuta:** fTetWild non è installabile su Windows, quindi la tetraedrizzazione deve rifiutare un ingresso non chiuso invece di produrre un risultato silenziosamente sbagliato.
- **Elementi invertiti = errore bloccante,** non avviso.
- **Commit:** mai `git add -A`. La radice del repository contiene 1,1 GB di file non tracciati. Ogni commit elenca i percorsi esatti.
- **Test:** si eseguono da `meshrec/` con `uv run pytest`. I test marcati `feasibility` sono esclusi per impostazione predefinita.
- **Dati reali:** `Nuvole di punti/muro_generato.ply` e `Nuvole di punti/lab_frame.pcd` stanno nella radice del repository, sono in `.gitignore` e non vanno mai aggiunti a un commit.

## Ordine di esecuzione e parallelismo

| Onda | Task | Parallelizzabile |
|---|---|---|
| 0 | Task 1 | no |
| 1 | Task 2, 3, 4, 5 | sì, quattro insieme |
| 2 | Task 6, 7, 8 | sì, tre insieme |
| 3 | Task 9, poi Task 10 | no |
| 4 | Task 11, 12 | sì, due insieme |

Un solo proprietario per file dentro ogni onda: nessun task di una stessa onda tocca un file toccato da un altro.

---

### Task 1: Spostamento in `core/` e configurazione completa

**Files:**
- Move: `src/meshrec/{config,synth,quality,volume,abaqus}.py` → `src/meshrec/core/`
- Create: `src/meshrec/core/__init__.py`
- Modify: `src/meshrec/core/config.py` (riscritto), `src/meshrec/core/abaqus.py:9` (import), `pyproject.toml`
- Modify: `tests/test_abaqus.py`, `tests/test_quality.py`, `tests/test_synth.py`, `tests/test_volume.py`, `tests/feasibility/test_calculix.py`, `tests/feasibility/test_gmsh.py`, `tests/feasibility/test_pymeshfix.py`, `tests/feasibility/test_pymeshlab.py`, `tests/feasibility/test_wildmeshing.py` (import `from meshrec import X` → `from meshrec.core import X`)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: niente.
- Produces: `meshrec.core.config.PipelineConfig` e i suoi sotto-modelli `InputConfig`, `SegmentConfig`, `DownsampleConfig`, `NormalsConfig`, `SurfaceConfig`, `RepairConfig`, `SimplifyConfig`, `TetConfig`, `AnalysisConfig`, `RunConfig`, più `Material`, `GRAVITY_MM_S2`, `load_config(path) -> PipelineConfig`, `save_config(cfg, path) -> None`. Ogni altro task importa da `meshrec.core.config`.

- [ ] **Step 1: Spostare i moduli e creare il pacchetto**

```bash
cd meshrec
mkdir src/meshrec/core
git mv src/meshrec/config.py src/meshrec/core/config.py
git mv src/meshrec/synth.py src/meshrec/core/synth.py
git mv src/meshrec/quality.py src/meshrec/core/quality.py
git mv src/meshrec/volume.py src/meshrec/core/volume.py
git mv src/meshrec/abaqus.py src/meshrec/core/abaqus.py
```

Creare `src/meshrec/core/__init__.py` con una sola riga:

```python
"""Geometria pura: nessuna dipendenza dall'interfaccia."""
```

- [ ] **Step 2: Correggere gli import**

In `src/meshrec/core/abaqus.py` riga 9:

```python
from meshrec.core.config import GRAVITY_MM_S2, Material
```

Nei nove file di test elencati sopra, sostituire `from meshrec import ...` con `from meshrec.core import ...`. Nessun'altra modifica ai test.

- [ ] **Step 3: Verificare che la suite esistente passi ancora**

Run: `cd meshrec && uv run pytest -v`
Expected: PASS, stesso numero di test di prima dello spostamento.

- [ ] **Step 4: Aggiungere PyYAML a pyproject**

PyYAML è già presente nell'ambiente come dipendenza transitiva, ma il core lo importerà direttamente, quindi va dichiarato. In `pyproject.toml`, dentro `dependencies`, aggiungere:

```toml
    "pyyaml>=6.0",
```

Poi: `cd meshrec && uv sync`

- [ ] **Step 5: Scrivere il test della configurazione**

Creare `tests/test_config.py`:

```python
"""La configurazione e l'unico luogo dei valori predefiniti, e sopravvive al round-trip YAML."""

import pytest

from meshrec.core import config


def test_defaults_are_in_working_units():
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.analysis.gravity == pytest.approx(9810.0)
    assert cfg.analysis.material.density == pytest.approx(1.8e-9)
    assert cfg.analysis.material.young == pytest.approx(1500.0)
    assert cfg.input.scale == pytest.approx(1.0)


def test_yaml_round_trip_preserves_every_field(tmp_path):
    cfg = config.PipelineConfig(
        input=config.InputConfig(path="nuvola.ply", scale=1000.0),
        surface=config.SurfaceConfig(poisson_depth=11, density_quantile=0.1),
        tet=config.TetConfig(min_ratio=1.4, max_volume=250.0),
    )
    path = tmp_path / "config.yaml"
    config.save_config(cfg, path)
    assert config.load_config(path) == cfg


def test_invalid_values_are_rejected():
    with pytest.raises(ValueError):
        config.InputConfig(path="nuvola.ply", scale=0.0)
    with pytest.raises(ValueError):
        config.SurfaceConfig(density_quantile=1.5)
```

- [ ] **Step 6: Eseguire il test per vederlo fallire**

Run: `cd meshrec && uv run pytest tests/test_config.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.config' has no attribute 'PipelineConfig'`

- [ ] **Step 7: Riscrivere `core/config.py`**

```python
"""Modelli di configurazione: unico luogo dove un parametro ha un valore predefinito.

Sistema di unita di lavoro: mm, N, MPa, tonnellata, secondo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

GRAVITY_MM_S2: float = 9810.0


class Material(BaseModel):
    """Materiale elastico isotropo. Valori indicativi per muratura."""

    name: str = "MURATURA"
    young: float = Field(default=1500.0, gt=0.0, description="modulo elastico [MPa]")
    poisson: float = Field(default=0.2, ge=0.0, lt=0.5, description="coefficiente di Poisson")
    density: float = Field(default=1.8e-9, gt=0.0, description="densita [t/mm^3]")


class InputConfig(BaseModel):
    """Step 1: ingresso e scala."""

    path: Path
    scale: float = Field(default=1.0, gt=0.0, description="fattore verso i mm")
    max_points: int = Field(default=20_000_000, gt=0)
    expected_size: tuple[float, float, float] | None = Field(
        default=None, description="dimensioni reali misurate del muro [mm], per il controllo di scala"
    )
    size_tolerance: float = Field(default=0.2, gt=0.0, description="scarto relativo ammesso")
    spacing_sample: int = Field(default=20_000, gt=1, description="punti campionati per la spaziatura")
    seed: int = 0


class SegmentConfig(BaseModel):
    """Step 2: segmentazione."""

    method: Literal["crop", "auto"] = "crop"
    outlier_neighbors: int = Field(default=20, gt=0)
    outlier_std_ratio: float = Field(default=2.0, gt=0.0)
    crop_min: tuple[float, float, float] | None = None
    crop_max: tuple[float, float, float] | None = None
    plane_distance_factor: float = Field(default=3.0, gt=0.0, description="x spaziatura media")
    plane_max_count: int = Field(default=4, ge=0)
    plane_min_points_ratio: float = Field(default=0.05, gt=0.0, le=1.0)
    cluster_eps_factor: float = Field(default=4.0, gt=0.0, description="x spaziatura media")
    cluster_min_points: int = Field(default=50, gt=0)
    cluster_index: int = Field(default=0, ge=0, description="0 = cluster piu numeroso")


class DownsampleConfig(BaseModel):
    """Step 3: riduzione a voxel."""

    voxel_size: float | None = Field(default=None, description="None = 2 x spaziatura media")
    voxel_factor: float = Field(default=2.0, gt=0.0)


class NormalsConfig(BaseModel):
    """Step 4: normali."""

    knn: int = Field(default=30, gt=2)
    orient_knn: int = Field(default=30, gt=2)


class SurfaceConfig(BaseModel):
    """Step 5: ricostruzione della superficie."""

    method: Literal["poisson", "bpa", "alpha"] = "poisson"
    poisson_depth: int = Field(default=9, ge=4, le=14)
    poisson_width: float = Field(default=0.0, ge=0.0)
    poisson_scale: float = Field(default=1.1, gt=0.0)
    density_quantile: float = Field(
        default=0.05, ge=0.0, lt=1.0, description="quantile di densita sotto il quale i vertici sono scartati"
    )
    bpa_radius_factors: tuple[float, ...] = (1.0, 2.0, 4.0)
    alpha_factor: float = Field(default=5.0, gt=0.0, description="x spaziatura media")


class RepairConfig(BaseModel):
    """Step 6: riparazione."""

    largest_component_only: bool = True
    max_hole_area: float | None = Field(
        default=None, description="area [mm^2] oltre la quale un foro chiuso viene segnalato"
    )
    join_components: bool = False


class SimplifyConfig(BaseModel):
    """Step 8: semplificazione, opzionale."""

    enabled: bool = False
    mode: Literal["decimate", "remesh"] = "remesh"
    target_faces: int | None = Field(default=None, gt=0)
    remesh_target_len_pct: float = Field(default=1.0, gt=0.0, description="percentuale della diagonale")
    taubin_iterations: int = Field(default=0, ge=0)


class TetConfig(BaseModel):
    """Step 9: tetraedrizzazione."""

    min_ratio: float = Field(default=1.1, gt=0.0, description="rapporto raggio-spigolo massimo")
    max_volume: float | None = Field(default=None, gt=0.0, description="volume massimo elemento [mm^3]")
    element: Literal["C3D4", "C3D10"] = "C3D4"


class AnalysisConfig(BaseModel):
    """Materiale e analisi."""

    material: Material = Field(default_factory=Material)
    gravity: float = Field(default=GRAVITY_MM_S2, gt=0.0)
    fixed_nset: str = "BASE"
    step_name: str = "GRAVITA"
    set_tolerance_factor: float = Field(
        default=0.5, gt=0.0, description="x dimensione media dell'elemento, per l'estrazione dei set"
    )


class RunConfig(BaseModel):
    """Esecuzione: percorsi e ripresa."""

    out_dir: Path = Path("runs/default")
    from_step: int = Field(default=1, ge=1, le=11)


class PipelineConfig(BaseModel):
    """Configurazione completa di un'elaborazione."""

    input: InputConfig
    segment: SegmentConfig = Field(default_factory=SegmentConfig)
    downsample: DownsampleConfig = Field(default_factory=DownsampleConfig)
    normals: NormalsConfig = Field(default_factory=NormalsConfig)
    surface: SurfaceConfig = Field(default_factory=SurfaceConfig)
    repair: RepairConfig = Field(default_factory=RepairConfig)
    simplify: SimplifyConfig = Field(default_factory=SimplifyConfig)
    tet: TetConfig = Field(default_factory=TetConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    run: RunConfig = Field(default_factory=RunConfig)


def load_config(path: Path) -> PipelineConfig:
    """Legge un config.yaml senza perdita rispetto a quanto scritto da `save_config`."""
    with Path(path).open(encoding="utf-8") as handle:
        return PipelineConfig.model_validate(yaml.safe_load(handle))


def save_config(cfg: PipelineConfig, path: Path) -> None:
    """Scrive la configurazione completa, compresi i valori lasciati ai predefiniti."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg.model_dump(mode="json"), handle, sort_keys=False, allow_unicode=True)
```

- [ ] **Step 8: Eseguire tutti i test**

Run: `cd meshrec && uv run pytest -v`
Expected: PASS, compresi i tre nuovi test di `tests/test_config.py`.

- [ ] **Step 9: Commit**

```bash
cd meshrec
git add src/meshrec/core tests/test_config.py tests/test_abaqus.py tests/test_quality.py tests/test_synth.py tests/test_volume.py tests/feasibility pyproject.toml uv.lock
git commit -m "refactor(meshrec): sposta i moduli in core/ e completa la configurazione"
```

---

### Task 2: Caricamento della nuvola e fattore di scala (step 1)

**Files:**
- Create: `src/meshrec/core/io.py`
- Test: `tests/test_io.py`

**Interfaces:**
- Consumes: `meshrec.core.config.InputConfig`, `meshrec.core.synth.sample_box_surface`.
- Produces:
  - `mean_spacing(points: np.ndarray, sample: int, seed: int) -> float`
  - `load_cloud(cfg: InputConfig) -> tuple[np.ndarray, dict]` — punti `(N, 3)` float64 già in mm, e metriche con chiavi `points_read`, `points_dropped`, `points_kept`, `scale`, `spacing`, `extent`, `bbox_min`, `bbox_max`, `size_check`.
  - `write_cloud(path, points, normals=None) -> None` e `read_cloud(path) -> tuple[np.ndarray, np.ndarray | None]` — usati da `pipeline.py` per gli artefatti.
  - `ScaleError` — eccezione sollevata quando l'ingombro non corrisponde a `expected_size`.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_io.py`:

```python
"""Step 1: caricamento, filtro dei non finiti, spaziatura, scala."""

import numpy as np
import pytest

from meshrec.core import config, io, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 10.0


def _write_ply(path, points):
    open3d = pytest.importorskip("open3d")
    cloud = open3d.geometry.PointCloud(open3d.utility.Vector3dVector(np.asarray(points)))
    open3d.io.write_point_cloud(str(path), cloud)


def test_mean_spacing_matches_a_regular_grid():
    points = synth.sample_box_surface(SIZE, SPACING)
    assert io.mean_spacing(points, sample=5000, seed=0) == pytest.approx(SPACING, rel=0.2)


def test_non_finite_points_are_dropped_and_counted(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[np.nan, 0.0, 0.0], [np.inf, 1.0, 2.0]]])
    path = tmp_path / "sporca.ply"
    _write_ply(path, dirty)

    loaded, metrics = io.load_cloud(config.InputConfig(path=path))

    assert metrics["points_dropped"] == 2
    assert metrics["points_kept"] == len(loaded) == len(points)
    assert np.isfinite(loaded).all()


def test_scale_factor_converts_the_extent(tmp_path):
    """Nuvola in metri: scale=1000 la porta in mm e l'ingombro lo dimostra."""
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    _, metrics = io.load_cloud(config.InputConfig(path=path, scale=1000.0))

    assert metrics["extent"] == pytest.approx(SIZE, rel=1e-3)


def test_extent_far_from_expected_size_raises(tmp_path):
    """La difesa contro l'errore di unita: silenzioso e di ordini di grandezza."""
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    with pytest.raises(io.ScaleError, match="ingombro"):
        io.load_cloud(config.InputConfig(path=path, scale=1.0, expected_size=SIZE))


def test_expected_size_is_satisfied_when_scale_is_right(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING) / 1000.0
    path = tmp_path / "metri.ply"
    _write_ply(path, points)

    _, metrics = io.load_cloud(
        config.InputConfig(path=path, scale=1000.0, expected_size=SIZE)
    )

    assert metrics["size_check"] == "ok"


def test_too_many_points_raises(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    path = tmp_path / "nuvola.ply"
    _write_ply(path, points)

    with pytest.raises(ValueError, match="max_points"):
        io.load_cloud(config.InputConfig(path=path, max_points=10))


def test_cloud_round_trip_preserves_points_and_normals(tmp_path):
    points = synth.sample_box_surface(SIZE, SPACING)
    normals = np.tile([0.0, 0.0, 1.0], (len(points), 1))
    path = tmp_path / "con_normali.ply"

    io.write_cloud(path, points, normals)
    back, back_normals = io.read_cloud(path)

    assert back == pytest.approx(points, abs=1e-3)
    assert back_normals == pytest.approx(normals, abs=1e-3)
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_io.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.io'`

- [ ] **Step 3: Scrivere `core/io.py`**

Note vincolanti per l'implementazione:
- `open3d.io.read_point_cloud` restituisce una nuvola vuota, senza sollevare, se il percorso non esiste o il formato non è riconosciuto: va controllato esplicitamente e trasformato in errore.
- Il conteggio dei punti scartati si ottiene confrontando la lunghezza prima e dopo il filtro dei non finiti, applicato su numpy (non su Open3D) perché il numero va riportato nelle metriche.
- La spaziatura media si calcola su un campione casuale con `scipy.spatial.cKDTree.query(..., k=2)`, prendendo la seconda colonna (il vicino più prossimo diverso da sé).
- La scala si applica prima di calcolare spaziatura e ingombro: le metriche sono sempre in mm.

```python
"""Step 1: lettura della nuvola, filtro dei non finiti, spaziatura e scala.

Il fattore di scala e' l'unica difesa contro un errore di unita, che non
produce alcun segnale a valle e falsa le tensioni di ordini di grandezza.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

from meshrec.core.config import InputConfig


class ScaleError(ValueError):
    """L'ingombro della nuvola non corrisponde alle dimensioni reali dichiarate."""


def read_cloud(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Legge .pcd/.ply/.xyz. Le normali sono restituite solo se presenti nel file."""
    cloud = o3d.io.read_point_cloud(str(path))
    points = np.asarray(cloud.points, dtype=np.float64)
    if len(points) == 0:
        raise ValueError(f"nessun punto letto da '{path}': file assente, vuoto o formato non riconosciuto")
    normals = np.asarray(cloud.normals, dtype=np.float64) if cloud.has_normals() else None
    return points, normals


def write_cloud(path: Path, points: np.ndarray, normals: np.ndarray | None = None) -> None:
    """Scrive un artefatto di nuvola, con le normali se disponibili."""
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))
    if normals is not None:
        cloud.normals = o3d.utility.Vector3dVector(np.asarray(normals, dtype=np.float64))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    o3d.io.write_point_cloud(str(path), cloud)


def mean_spacing(points: np.ndarray, sample: int, seed: int) -> float:
    """Distanza media al vicino piu prossimo, su un campione casuale."""
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        raise ValueError("servono almeno due punti per stimare la spaziatura")
    rng = np.random.default_rng(seed)
    size = min(sample, len(points))
    chosen = points[rng.choice(len(points), size=size, replace=False)]
    distances, _ = cKDTree(points).query(chosen, k=2)
    return float(distances[:, 1].mean())


def load_cloud(cfg: InputConfig) -> tuple[np.ndarray, dict[str, object]]:
    """Legge la nuvola, la porta nelle unita di lavoro e ne misura l'ingombro."""
    points, _ = read_cloud(cfg.path)
    points_read = len(points)

    finite = np.isfinite(points).all(axis=1)
    points = np.ascontiguousarray(points[finite])
    points_dropped = points_read - len(points)
    if len(points) == 0:
        raise ValueError(f"tutti i {points_read} punti letti hanno coordinate non finite")
    if len(points) > cfg.max_points:
        raise ValueError(
            f"{len(points)} punti oltre il limite max_points={cfg.max_points}: "
            "alza il limite o riduci la nuvola a monte"
        )

    points = points * cfg.scale
    bbox_min = points.min(axis=0)
    bbox_max = points.max(axis=0)
    extent = bbox_max - bbox_min

    size_check = "non richiesto"
    if cfg.expected_size is not None:
        expected = np.sort(np.asarray(cfg.expected_size, dtype=np.float64))
        measured = np.sort(extent)
        relative = np.abs(measured - expected) / expected
        if (relative > cfg.size_tolerance).any():
            raise ScaleError(
                f"ingombro misurato {np.round(measured, 1).tolist()} mm contro "
                f"{np.round(expected, 1).tolist()} mm attesi, scarto relativo "
                f"{np.round(relative, 3).tolist()} oltre la tolleranza {cfg.size_tolerance}: "
                "il fattore di scala e' probabilmente sbagliato"
            )
        size_check = "ok"

    metrics = {
        "points_read": points_read,
        "points_dropped": points_dropped,
        "points_kept": len(points),
        "scale": cfg.scale,
        "spacing": mean_spacing(points, cfg.spacing_sample, cfg.seed),
        "extent": extent.tolist(),
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "size_check": size_check,
    }
    return points, metrics
```

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_io.py -v`
Expected: PASS, sette test.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/io.py tests/test_io.py
git commit -m "feat(meshrec): caricamento nuvola con filtro dei non finiti e fattore di scala"
```

---

### Task 3: Metriche di qualità ed errore geometrico (step 7 e 10)

**Files:**
- Modify: `src/meshrec/core/quality.py` (aggiunte in coda, nulla di esistente viene cambiato)
- Modify: `tests/test_quality.py` (aggiunte in coda)

**Interfaces:**
- Consumes: `meshrec.core.synth.box_mesh`.
- Produces:
  - `triangle_aspect_ratios(vertices, faces) -> np.ndarray`
  - `tet_aspect_ratios(nodes, tets) -> np.ndarray`
  - `min_dihedral_angles(nodes, tets) -> np.ndarray` — gradi, uno per tetraedro
  - `surface_metrics(vertices, faces) -> dict`
  - `volume_metrics(nodes, tets) -> dict`
  - `geometric_error(vertices, faces, cloud) -> dict`
- Le funzioni già presenti (`boundary_edges`, `is_watertight`, `mesh_volume`, `tet_volumes`, `inverted_tets`) restano invariate.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `tests/test_quality.py`:

```python
def test_regular_tetrahedron_has_the_textbook_dihedral_angle():
    """Il tetraedro regolare ha tutti i diedri a arccos(1/3) = 70,5288 gradi."""
    nodes = np.array(
        [[1.0, 1.0, 1.0], [1.0, -1.0, -1.0], [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] == pytest.approx(70.5288, abs=1e-3)


def test_flattened_tetrahedron_has_a_small_dihedral_angle():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.001]])
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] < 1.0


def test_aspect_ratio_of_an_equilateral_triangle_is_one():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, np.sqrt(3.0) / 2.0, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] == pytest.approx(1.0, abs=1e-6)


def test_aspect_ratio_of_a_sliver_triangle_is_large():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.001, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] > 100.0


def test_surface_metrics_on_a_closed_box():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, faces)
    assert metrics["watertight"] is True
    assert metrics["boundary_edges"] == 0
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0)
    assert metrics["area"] == pytest.approx(2 * (100 * 40 + 100 * 200 + 40 * 200))
    assert metrics["triangles"] == 12


def test_surface_metrics_on_a_punched_box_reports_the_opening():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, synth.punch_holes(faces))
    assert metrics["watertight"] is False
    assert metrics["boundary_edges"] == 4


def test_volume_metrics_flag_inverted_elements():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    good = np.array([[0, 1, 2, 3]])
    flipped = np.array([[0, 2, 1, 3]])
    assert quality.volume_metrics(nodes, good)["inverted"] == 0
    assert quality.volume_metrics(nodes, flipped)["inverted"] == 1


def test_geometric_error_of_a_cloud_sampled_on_its_own_mesh_is_small():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0)

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] < 1.0
    assert error["cloud_to_mesh"]["RMS"] < 1.0
    assert error["mesh_to_cloud"]["max"] < 6.0


def test_geometric_error_grows_with_a_displaced_cloud():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0) + np.array([0.0, 0.0, 10.0])

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] > 5.0
```

`tests/test_quality.py` importa già `numpy as np`, `pytest` e `from meshrec.core import quality, synth`: verificarlo prima di aggiungere, e completare gli import se manca qualcosa.

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_quality.py -v`
Expected: FAIL, i test già esistenti passano, i nove nuovi falliscono con `AttributeError`.

- [ ] **Step 3: Implementare le metriche in `core/quality.py`**

Note vincolanti:
- L'angolo diedro fra due facce di un tetraedro è l'angolo fra le loro normali uscenti, preso come `180° - angolo(n_i, n_j)`. Le sei coppie di facce vanno enumerate esplicitamente.
- Il rapporto d'aspetto del triangolo è `lato_massimo / (2 * sqrt(3) * area / perimetro)`, cioè lato massimo diviso il raggio del cerchio inscritto normalizzato: vale 1 per l'equilatero e cresce per i triangoli degeneri.
- Il rapporto d'aspetto del tetraedro è `lato_massimo / (raggio della sfera inscritta * 2 * sqrt(6))`, normalizzato a 1 per il tetraedro regolare.
- `geometric_error` usa PyMeshLab e va importato dentro la funzione, non in testa al modulo: le altre metriche devono restare utilizzabili senza PyMeshLab.
- Il dizionario restituito da `get_hausdorff_distance` va inserito nelle metriche così com'è. Il task richiede la presenza delle chiavi `max` e `RMS`, verificate in Fase 0; se PyMeshLab espone anche `mean` o `median`, arrivano da sole. Non inventare chiavi assenti.

```python
_TET_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
_FACE_PAIRS = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def triangle_aspect_ratios(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei triangoli: 1 per l'equilatero, cresce coi degeneri."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    sides = np.stack(
        [
            np.linalg.norm(b - a, axis=1),
            np.linalg.norm(c - b, axis=1),
            np.linalg.norm(a - c, axis=1),
        ],
        axis=1,
    )
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    inradius = np.where(sides.sum(axis=1) > 0.0, 2.0 * area / sides.sum(axis=1), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sides.max(axis=1) / (2.0 * np.sqrt(3.0) * inradius)
    return np.where(np.isfinite(ratio), ratio, np.inf)


def _tet_face_normals(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Normali uscenti delle quattro facce di ogni tetraedro, forma (n, 4, 3)."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    normals = np.empty((len(t), 4, 3), dtype=np.float64)
    for index, (i, j, k) in enumerate(_TET_FACES):
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        face = np.cross(q - p, r - p)
        length = np.linalg.norm(face, axis=1, keepdims=True)
        normals[:, index] = np.divide(face, length, out=np.zeros_like(face), where=length > 0.0)
    return normals


def min_dihedral_angles(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Angolo diedro minimo di ogni tetraedro, in gradi.

    Un tetraedro regolare vale arccos(1/3) = 70,5288 gradi; valori vicini a
    zero indicano elementi schiacciati, numericamente inaffidabili.
    """
    normals = _tet_face_normals(nodes, tets)
    angles = np.empty((len(normals), len(_FACE_PAIRS)), dtype=np.float64)
    for index, (i, j) in enumerate(_FACE_PAIRS):
        cosine = np.clip(np.einsum("ij,ij->i", normals[:, i], normals[:, j]), -1.0, 1.0)
        angles[:, index] = 180.0 - np.degrees(np.arccos(cosine))
    return angles.min(axis=1)


def tet_aspect_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei tetraedri: 1 per il regolare, cresce coi degeneri."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    volume = np.abs(tet_volumes(n, t))
    area = np.zeros(len(t), dtype=np.float64)
    for i, j, k in _TET_FACES:
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        area += np.linalg.norm(np.cross(q - p, r - p), axis=1) / 2.0
    edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    longest = np.max(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in edges], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        inradius = 3.0 * volume / area
        ratio = longest / (inradius * 2.0 * np.sqrt(6.0))
    return np.where(np.isfinite(ratio) & (inradius > 0.0), ratio, np.inf)


def _distribution(values: np.ndarray) -> dict[str, float]:
    """Riassunto di una distribuzione, per il report e per metrics.json."""
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if len(finite) == 0:
        return {"min": float("nan"), "median": float("nan"), "mean": float("nan"), "max": float("nan")}
    return {
        "min": float(finite.min()),
        "median": float(np.median(finite)),
        "mean": float(finite.mean()),
        "max": float(finite.max()),
    }


def surface_metrics(vertices: np.ndarray, faces: np.ndarray) -> dict[str, object]:
    """Step 7: chiusura, bordi, area, volume racchiuso, aspetto dei triangoli."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return {
        "vertices": int(len(v)),
        "triangles": int(len(f)),
        "watertight": is_watertight(f),
        "boundary_edges": int(len(boundary_edges(f))),
        "area": float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2.0),
        "volume": mesh_volume(v, f),
        "aspect_ratio": _distribution(triangle_aspect_ratios(v, f)),
    }


def volume_metrics(nodes: np.ndarray, tets: np.ndarray) -> dict[str, object]:
    """Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi."""
    volumes = tet_volumes(nodes, tets)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "tets": int(len(np.asarray(tets))),
        "inverted": int(len(inverted_tets(nodes, tets))),
        "total_volume": float(volumes.sum()),
        "element_volume": _distribution(volumes),
        "min_dihedral_deg": _distribution(min_dihedral_angles(nodes, tets)),
        "aspect_ratio": _distribution(tet_aspect_ratios(nodes, tets)),
    }


def geometric_error(
    vertices: np.ndarray, faces: np.ndarray, cloud: np.ndarray
) -> dict[str, object]:
    """Errore geometrico bidirezionale fra superficie ricostruita e nuvola sorgente.

    Il campionamento della superficie e' delegato a PyMeshLab: una distanza
    calcolata sui soli vertici sovrastimerebbe l'errore dove i triangoli sono
    grandi, e la fedelta geometrica e' una delle metriche riportate in tesi.
    """
    import pymeshlab

    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(
        pymeshlab.Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces)), "mesh"
    )
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(cloud, dtype=np.float64)), "cloud")

    cloud_to_mesh = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=1, targetmesh=0))
    mesh_to_cloud = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=0, targetmesh=1))
    for name, result in (("cloud_to_mesh", cloud_to_mesh), ("mesh_to_cloud", mesh_to_cloud)):
        missing = {"max", "RMS"} - set(result)
        if missing:
            raise RuntimeError(f"get_hausdorff_distance non ha restituito {missing} per {name}")

    return {
        "cloud_to_mesh": cloud_to_mesh,
        "mesh_to_cloud": mesh_to_cloud,
        "hausdorff": max(float(cloud_to_mesh["max"]), float(mesh_to_cloud["max"])),
    }
```

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_quality.py -v`
Expected: PASS, esistenti più nove nuovi.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/quality.py tests/test_quality.py
git commit -m "feat(meshrec): angolo diedro, rapporto d'aspetto ed errore geometrico bidirezionale"
```

---

### Task 4: Riparazione della superficie con PyMeshFix (step 6)

**Files:**
- Create: `src/meshrec/core/repair.py`
- Test: `tests/test_repair.py`

**Interfaces:**
- Consumes: `meshrec.core.config.RepairConfig`, `meshrec.core.quality.{is_watertight, boundary_edges, mesh_volume}`, `meshrec.core.synth.{box_mesh, punch_holes}`.
- Produces: `repair_surface(vertices, faces, cfg: RepairConfig) -> tuple[np.ndarray, np.ndarray, dict]` con metriche `duplicate_vertices_merged`, `degenerate_faces_removed`, `duplicate_faces_removed`, `components_before`, `components_kept`, `holes_before`, `hole_areas`, `holes_over_threshold`, `watertight_after`, `volume_before`, `volume_after`.
- Produce anche `hole_loops(faces) -> list[np.ndarray]` e `component_labels(faces, n_vertices) -> np.ndarray`, usate dalle metriche.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_repair.py`:

```python
"""Step 6: riparazione deterministica e registrata."""

import numpy as np
import pytest

from meshrec.core import config, quality, repair, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_a_punched_box_comes_back_watertight():
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    fixed_vertices, fixed_faces, metrics = repair.repair_surface(
        vertices, damaged, config.RepairConfig()
    )

    assert quality.is_watertight(fixed_faces)
    assert metrics["watertight_after"] is True
    assert metrics["holes_before"] == 1
    assert abs(quality.mesh_volume(fixed_vertices, fixed_faces)) == pytest.approx(
        EXACT_VOLUME, rel=0.05
    )


def test_an_already_closed_box_is_left_alone():
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)

    _, fixed_faces, metrics = repair.repair_surface(vertices, faces, config.RepairConfig())

    assert metrics["holes_before"] == 0
    assert metrics["watertight_after"] is True
    assert len(fixed_faces) >= len(faces)


def test_a_hole_over_the_threshold_is_reported_not_hidden():
    """La chiusura avviene comunque, ma il foro grande finisce nelle metriche."""
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    _, _, metrics = repair.repair_surface(
        vertices, damaged, config.RepairConfig(max_hole_area=100.0)
    )

    assert len(metrics["holes_over_threshold"]) == 1
    assert metrics["holes_over_threshold"][0] > 100.0


def test_the_smaller_connected_component_is_dropped():
    vertices, faces = synth.box_mesh(SIZE)
    far_vertices = vertices + np.array([1000.0, 0.0, 0.0])
    both_vertices = np.vstack([vertices, far_vertices])
    both_faces = np.vstack([faces, faces + len(vertices)])

    labels = repair.component_labels(both_faces, len(both_vertices))
    assert len(np.unique(labels)) == 2

    pytest.importorskip("pymeshfix")
    _, kept_faces, metrics = repair.repair_surface(
        both_vertices, both_faces, config.RepairConfig(largest_component_only=True)
    )
    assert metrics["components_before"] == 2
    assert metrics["components_kept"] == 1
    assert len(kept_faces) < len(both_faces)


def test_degenerate_and_duplicate_faces_are_removed():
    vertices, faces = synth.box_mesh(SIZE)
    degenerate = np.array([[0, 0, 1]])
    duplicated = faces[:1]
    dirty = np.vstack([faces, degenerate, duplicated])

    _, clean_faces, metrics = repair.repair_surface(vertices, dirty, config.RepairConfig())

    assert metrics["degenerate_faces_removed"] == 1
    assert metrics["duplicate_faces_removed"] == 1
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_repair.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.repair'`

- [ ] **Step 3: Scrivere `core/repair.py`**

Note vincolanti:
- L'ordine è fissato e va rispettato: saldatura dei vertici coincidenti, rimozione dei degeneri e dei duplicati, selezione della componente maggiore, misura dei fori, chiusura con PyMeshFix, verifica finale. Le metriche sono raccolte man mano, prima che l'operazione successiva ne cancelli le tracce.
- I fori si misurano **prima** della chiusura: dopo, l'informazione non esiste più. L'area di un ciclo di bordo si approssima con la formula di Gauss applicata al poligono proiettato, cioè la norma della somma dei prodotti vettoriali `p_i × p_{i+1}` diviso due.
- `pymeshfix.MeshFix` vuole i triangoli come `int32` e restituisce `.points` / `.faces`.
- Le componenti connesse si trovano con `scipy.sparse.csgraph.connected_components` sul grafo spigolo-vertice.

```python
"""Step 6: riparazione topologica deterministica e registrata.

La chiusura garantita si appoggia a MeshFix (Attene 2010), algoritmo
pubblicato e deterministico: e' il requisito che rende la riparazione
citabile in tesi, al posto delle operazioni opache del programma sostituito.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from meshrec.core.config import RepairConfig
from meshrec.core.quality import boundary_edges, is_watertight, mesh_volume

_WELD_DECIMALS = 6


def component_labels(faces: np.ndarray, n_vertices: int) -> np.ndarray:
    """Etichetta di componente connessa per ogni vertice."""
    f = np.asarray(faces)
    rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    data = np.ones(len(rows), dtype=np.int8)
    graph = coo_matrix((data, (rows, cols)), shape=(n_vertices, n_vertices))
    _, labels = connected_components(graph, directed=False)
    return labels


def hole_loops(faces: np.ndarray) -> list[np.ndarray]:
    """Cicli chiusi di spigoli di bordo: un ciclo e' un foro."""
    edges = boundary_edges(faces)
    if len(edges) == 0:
        return []

    neighbours: dict[int, list[int]] = {}
    for a, b in edges:
        neighbours.setdefault(int(a), []).append(int(b))
        neighbours.setdefault(int(b), []).append(int(a))

    loops: list[np.ndarray] = []
    unvisited = set(neighbours)
    while unvisited:
        start = unvisited.pop()
        loop = [start]
        previous, current = start, neighbours[start][0]
        while current != start:
            unvisited.discard(current)
            loop.append(current)
            options = [node for node in neighbours[current] if node != previous]
            if not options:
                break
            previous, current = current, options[0]
        loops.append(np.array(loop, dtype=np.int64))
    return loops


def _loop_area(vertices: np.ndarray, loop: np.ndarray) -> float:
    """Area del poligono di bordo, formula di Gauss in tre dimensioni."""
    points = np.asarray(vertices, dtype=np.float64)[loop]
    return float(np.linalg.norm(np.cross(points, np.roll(points, -1, axis=0)).sum(axis=0)) / 2.0)


def repair_surface(
    vertices: np.ndarray, faces: np.ndarray, cfg: RepairConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Porta la superficie a chiusura manifold registrando ogni operazione."""
    import pymeshfix

    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    metrics: dict[str, object] = {"volume_before": mesh_volume(v, f)}

    # 1. saldatura dei vertici coincidenti
    _, first, inverse = np.unique(
        np.round(v, _WELD_DECIMALS), axis=0, return_index=True, return_inverse=True
    )
    metrics["duplicate_vertices_merged"] = int(len(v) - len(first))
    order = np.argsort(first)
    remap = np.empty(len(first), dtype=np.int64)
    remap[order] = np.arange(len(first))
    v = np.ascontiguousarray(v[first[order]])
    f = remap[inverse[f]]

    # 2. triangoli degeneri e duplicati
    non_degenerate = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])
    metrics["degenerate_faces_removed"] = int((~non_degenerate).sum())
    f = f[non_degenerate]
    _, unique_index = np.unique(np.sort(f, axis=1), axis=0, return_index=True)
    metrics["duplicate_faces_removed"] = int(len(f) - len(unique_index))
    f = np.ascontiguousarray(f[np.sort(unique_index)])

    # 3. componente connessa maggiore
    labels = component_labels(f, len(v))
    used = np.unique(f)
    metrics["components_before"] = int(len(np.unique(labels[used])))
    metrics["components_kept"] = metrics["components_before"]
    if cfg.largest_component_only and metrics["components_before"] > 1:
        counts = np.bincount(labels[used])
        biggest = int(np.argmax(counts))
        f = np.ascontiguousarray(f[labels[f[:, 0]] == biggest])
        metrics["components_kept"] = 1

    # 4. misura dei fori, prima che la chiusura ne cancelli la traccia
    loops = hole_loops(f)
    areas = sorted((_loop_area(v, loop) for loop in loops), reverse=True)
    metrics["holes_before"] = len(loops)
    metrics["hole_areas"] = areas
    metrics["holes_over_threshold"] = (
        [] if cfg.max_hole_area is None else [area for area in areas if area > cfg.max_hole_area]
    )

    # 5. chiusura garantita
    fixer = pymeshfix.MeshFix(v, np.ascontiguousarray(f, dtype=np.int32))
    fixer.repair(joincomp=cfg.join_components)
    v = np.ascontiguousarray(fixer.points, dtype=np.float64)
    f = np.ascontiguousarray(fixer.faces, dtype=np.int64)

    metrics["watertight_after"] = is_watertight(f)
    metrics["volume_after"] = mesh_volume(v, f)
    metrics["vertices"] = int(len(v))
    metrics["triangles"] = int(len(f))
    return v, f, metrics
```

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_repair.py -v`
Expected: PASS, cinque test.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/repair.py tests/test_repair.py
git commit -m "feat(meshrec): riparazione della superficie con PyMeshFix e registro delle operazioni"
```

---

### Task 5: Guardia di superficie chiusa nella tetraedrizzazione (step 9)

**Files:**
- Modify: `src/meshrec/core/volume.py`
- Modify: `tests/test_volume.py` (aggiunte in coda)

**Interfaces:**
- Consumes: `meshrec.core.quality.{is_watertight, boundary_edges, inverted_tets}`.
- Produces: `tetrahedralize(vertices, faces, min_ratio=1.1, max_volume=None) -> tuple[np.ndarray, np.ndarray]` — **firma invariata**, con l'aggiunta della guardia; `NotWatertightError`; `InvertedElementsError`; `tetrahedralize_with_metrics(vertices, faces, cfg: TetConfig) -> tuple[np.ndarray, np.ndarray, dict]`.
- Il chiamante dello step è `tetrahedralize_with_metrics`; `tetrahedralize` resta la primitiva usata dai test esistenti e dalle verifiche di fattibilità.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `tests/test_volume.py`:

```python
def test_an_open_surface_is_refused_before_tetgen_runs():
    """fTetWild non e' installabile su Windows: la guardia e' l'unica difesa."""
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    with pytest.raises(volume.NotWatertightError, match="4 spigoli di bordo"):
        volume.tetrahedralize(vertices, damaged)


def test_with_metrics_reports_counts_and_time():
    vertices, faces = synth.box_mesh(SIZE)

    nodes, tets, metrics = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    assert metrics["nodes"] == len(nodes)
    assert metrics["tets"] == len(tets)
    assert metrics["seconds"] > 0.0
    assert metrics["element"] == "C3D4"


def test_inverted_elements_are_a_blocking_error():
    """La spec chiede errore bloccante, non avviso: qui lo si verifica sul percorso reale."""
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())
    assert len(quality.inverted_tets(nodes, tets)) == 0
```

Completare gli import di `tests/test_volume.py` con `config`, `quality` e `synth` se non già presenti.

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_volume.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.volume' has no attribute 'NotWatertightError'`

- [ ] **Step 3: Modificare `core/volume.py`**

Aggiungere in testa al modulo, dopo gli import esistenti:

```python
import time

from meshrec.core.config import TetConfig
from meshrec.core.quality import boundary_edges, inverted_tets, is_watertight


class NotWatertightError(ValueError):
    """La superficie non e chiusa: TetGen non puo tetraedrizzarla."""


class InvertedElementsError(ValueError):
    """La mesh di volume contiene elementi invertiti o degeneri."""
```

Aggiungere la guardia come prime righe del corpo di `tetrahedralize`, prima della costruzione di `tetgen.TetGen`:

```python
    faces = np.asarray(faces)
    if not is_watertight(faces):
        open_edges = len(boundary_edges(faces))
        raise NotWatertightError(
            f"superficie non chiusa: {open_edges} spigoli di bordo. "
            "TetGen richiede un ingresso manifold chiuso; ripara la superficie "
            "con core.repair.repair_surface prima di tetraedrizzare."
        )
```

Aggiungere in coda al modulo:

```python
def tetrahedralize_with_metrics(
    vertices: np.ndarray, faces: np.ndarray, cfg: TetConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 9 completo: tetraedrizza, cronometra e rifiuta gli elementi invertiti."""
    start = time.perf_counter()
    nodes, tets = tetrahedralize(vertices, faces, cfg.min_ratio, cfg.max_volume)
    seconds = time.perf_counter() - start

    inverted = inverted_tets(nodes, tets)
    if len(inverted) > 0:
        raise InvertedElementsError(
            f"{len(inverted)} tetraedri invertiti o degeneri su {len(tets)}: "
            "risultato inutilizzabile per l'analisi, non un avviso"
        )

    metrics = {
        "nodes": int(len(nodes)),
        "tets": int(len(tets)),
        "seconds": float(seconds),
        "element": cfg.element,
        "min_ratio": cfg.min_ratio,
        "max_volume": cfg.max_volume,
    }
    return nodes, tets, metrics
```

Nota: `cfg.element == "C3D10"` non genera nodi di lato in questa fase. TetGen li produrrebbe con `order=2`, ma il writer del deck scrive elementi a quattro nodi: fino a quando il writer non supporta i dieci nodi, `element` viaggia soltanto nelle metriche e nel deck come nome del tipo. Chi implementa il Task 8 deve sollevare un errore esplicito se `element == "C3D10"`, invece di scrivere un deck incoerente.

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_volume.py -v`
Expected: PASS, esistenti più tre nuovi.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/volume.py tests/test_volume.py
git commit -m "feat(meshrec): guardia di superficie chiusa e metriche della tetraedrizzazione"
```

---

### Task 6: Riduzione, normali, ricostruzione e semplificazione (step 3, 4, 5, 8)

**Files:**
- Create: `src/meshrec/core/surface.py`
- Test: `tests/test_surface.py`

**Interfaces:**
- Consumes: `meshrec.core.config.{DownsampleConfig, NormalsConfig, SurfaceConfig, SimplifyConfig}`, `meshrec.core.synth.sample_box_surface`.
- Produces:
  - `downsample(points, cfg: DownsampleConfig, spacing: float) -> tuple[np.ndarray, dict]`
  - `estimate_normals(points, cfg: NormalsConfig, spacing: float) -> tuple[np.ndarray, dict]` — restituisce le normali `(N, 3)`
  - `reconstruct(points, normals, cfg: SurfaceConfig, spacing: float) -> tuple[np.ndarray, np.ndarray, dict]`
  - `simplify(vertices, faces, cfg: SimplifyConfig) -> tuple[np.ndarray, np.ndarray, dict]`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_surface.py`:

```python
"""Step 3, 4, 5, 8: riduzione, normali, ricostruzione, semplificazione."""

import numpy as np
import pytest

from meshrec.core import config, quality, surface, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 4.0
EXACT_VOLUME = 100.0 * 40.0 * 200.0


@pytest.fixture(scope="module")
def cloud():
    return synth.sample_box_surface(SIZE, SPACING)


def test_downsample_reduces_the_point_count(cloud):
    reduced, metrics = surface.downsample(cloud, config.DownsampleConfig(), SPACING)
    assert len(reduced) < len(cloud)
    assert metrics["points_before"] == len(cloud)
    assert metrics["points_after"] == len(reduced)
    assert 0.0 < metrics["reduction"] < 1.0
    assert metrics["voxel_size"] == pytest.approx(2.0 * SPACING)


def test_explicit_voxel_size_wins_over_the_derived_one(cloud):
    _, metrics = surface.downsample(cloud, config.DownsampleConfig(voxel_size=25.0), SPACING)
    assert metrics["voxel_size"] == pytest.approx(25.0)


def test_normals_are_unit_length_and_axis_aligned_on_a_box(cloud):
    normals, metrics = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    assert len(normals) == len(cloud)
    assert np.linalg.norm(normals, axis=1) == pytest.approx(1.0, abs=1e-6)
    # su un parallelepipedo ogni normale e vicina a un asse: la componente massima domina
    assert np.abs(normals).max(axis=1).mean() > 0.9
    assert metrics["knn"] == 30


def test_poisson_reconstructs_a_closed_box_with_the_right_volume(cloud):
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    vertices, faces, metrics = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8), SPACING
    )
    assert metrics["method"] == "poisson"
    assert metrics["triangles"] == len(faces)
    assert abs(quality.mesh_volume(vertices, faces)) == pytest.approx(EXACT_VOLUME, rel=0.25)


def test_density_trimming_removes_vertices(cloud):
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    _, _, trimmed = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8, density_quantile=0.2), SPACING
    )
    _, _, kept = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(poisson_depth=8, density_quantile=0.0), SPACING
    )
    assert trimmed["vertices_trimmed"] > 0
    assert kept["vertices_trimmed"] == 0
    assert trimmed["triangles"] < kept["triangles"]


def test_alpha_shape_produces_a_surface(cloud):
    vertices, faces, metrics = surface.reconstruct(
        cloud, None, config.SurfaceConfig(method="alpha"), SPACING
    )
    assert metrics["method"] == "alpha"
    assert len(faces) > 0
    assert len(vertices) > 0


def test_ball_pivoting_produces_a_surface(cloud):
    normals, _ = surface.estimate_normals(cloud, config.NormalsConfig(), SPACING)
    _, faces, metrics = surface.reconstruct(
        cloud, normals, config.SurfaceConfig(method="bpa"), SPACING
    )
    assert metrics["method"] == "bpa"
    assert len(faces) > 0


def test_disabled_simplification_is_a_no_op():
    vertices, faces = synth.box_mesh(SIZE)
    out_vertices, out_faces, metrics = surface.simplify(
        vertices, faces, config.SimplifyConfig(enabled=False)
    )
    assert out_faces.shape == faces.shape
    assert out_vertices.shape == vertices.shape
    assert metrics["enabled"] is False


def test_decimation_reaches_the_target_face_count():
    vertices, faces = synth.box_mesh(SIZE)
    # da 12 triangoli grossolani a molti triangoli regolari, poi giu a 100
    dense_vertices, dense_faces, _ = surface.simplify(
        vertices, faces, config.SimplifyConfig(enabled=True, mode="remesh", remesh_target_len_pct=2.0)
    )
    _, small_faces, metrics = surface.simplify(
        dense_vertices,
        dense_faces,
        config.SimplifyConfig(enabled=True, mode="decimate", target_faces=100),
    )
    assert len(small_faces) <= 120
    assert metrics["triangles_before"] > metrics["triangles_after"]


def test_taubin_smoothing_does_not_collapse_the_volume():
    """Il laplaciano contrae il volume e assottiglia il muro: Taubin no."""
    vertices, faces = synth.box_mesh(SIZE)
    dense_vertices, dense_faces, _ = surface.simplify(
        vertices, faces, config.SimplifyConfig(enabled=True, mode="remesh", remesh_target_len_pct=2.0)
    )
    smooth_vertices, smooth_faces, _ = surface.simplify(
        dense_vertices,
        dense_faces,
        config.SimplifyConfig(enabled=True, mode="remesh", remesh_target_len_pct=2.0, taubin_iterations=10),
    )
    before = abs(quality.mesh_volume(dense_vertices, dense_faces))
    after = abs(quality.mesh_volume(smooth_vertices, smooth_faces))
    assert after == pytest.approx(before, rel=0.05)
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_surface.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.surface'`

- [ ] **Step 3: Scrivere `core/surface.py`**

Note vincolanti:
- Le API Open3D 0.19 da usare: `PointCloud.voxel_down_sample`, `estimate_normals(KDTreeSearchParamKNN(knn))`, `orient_normals_consistent_tangent_plane(k)`, `TriangleMesh.create_from_point_cloud_poisson(...) -> (mesh, densities)`, `create_from_point_cloud_ball_pivoting(cloud, DoubleVector(radii))`, `create_from_point_cloud_alpha_shape(cloud, alpha)`, `TriangleMesh.remove_vertices_by_mask`, `simplify_quadric_decimation(target)`, `filter_smooth_taubin(number_of_iterations)`.
- Il trimming per densità: `create_from_point_cloud_poisson` restituisce anche un vettore di densità per vertice. La soglia è il quantile `density_quantile` di quel vettore; con `density_quantile == 0.0` non si rimuove nulla, e questo va garantito esplicitamente perché `np.quantile(x, 0.0)` vale il minimo e la maschera `<` lo escluderebbe comunque, ma solo per fortuna. Usare un ramo esplicito.
- Il remeshing isotropo passa per PyMeshLab (`meshing_isotropic_explicit_remeshing` con `targetlen=pymeshlab.PercentageValue(pct)`), la decimazione per Open3D. `pymeshlab` va importato dentro la funzione.
- `reconstruct` con `method="alpha"` non usa le normali: accettare `normals=None` senza sollevare.

```python
"""Step 3, 4, 5, 8: dalla nuvola segmentata alla superficie triangolare."""

from __future__ import annotations

import numpy as np
import open3d as o3d

from meshrec.core.config import DownsampleConfig, NormalsConfig, SimplifyConfig, SurfaceConfig


def _to_cloud(points: np.ndarray, normals: np.ndarray | None = None) -> o3d.geometry.PointCloud:
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))
    if normals is not None:
        cloud.normals = o3d.utility.Vector3dVector(np.asarray(normals, dtype=np.float64))
    return cloud


def _to_mesh(vertices: np.ndarray, faces: np.ndarray) -> o3d.geometry.TriangleMesh:
    return o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )


def _from_mesh(mesh: o3d.geometry.TriangleMesh) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.ascontiguousarray(np.asarray(mesh.vertices), dtype=np.float64),
        np.ascontiguousarray(np.asarray(mesh.triangles), dtype=np.int64),
    )


def downsample(
    points: np.ndarray, cfg: DownsampleConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 3: riduzione a voxel. Il passo predefinito deriva dai dati, non da una costante."""
    voxel = cfg.voxel_size if cfg.voxel_size is not None else cfg.voxel_factor * spacing
    reduced = np.asarray(_to_cloud(points).voxel_down_sample(voxel).points, dtype=np.float64)
    metrics = {
        "voxel_size": float(voxel),
        "points_before": int(len(points)),
        "points_after": int(len(reduced)),
        "reduction": float(1.0 - len(reduced) / len(points)),
    }
    return np.ascontiguousarray(reduced), metrics


def estimate_normals(
    points: np.ndarray, cfg: NormalsConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 4: normali con vicinato KNN e orientamento coerente su albero di supporto."""
    cloud = _to_cloud(points)
    cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=cfg.knn))
    cloud.orient_normals_consistent_tangent_plane(cfg.orient_knn)
    normals = np.ascontiguousarray(np.asarray(cloud.normals), dtype=np.float64)
    lengths = np.linalg.norm(normals, axis=1)
    metrics = {
        "knn": cfg.knn,
        "orient_knn": cfg.orient_knn,
        "spacing": float(spacing),
        "degenerate_normals": int((lengths < 0.5).sum()),
    }
    return normals, metrics


def reconstruct(
    points: np.ndarray,
    normals: np.ndarray | None,
    cfg: SurfaceConfig,
    spacing: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 5: ricostruzione della superficie, con trimming per densita nel Poisson."""
    cloud = _to_cloud(points, normals)
    metrics: dict[str, object] = {"method": cfg.method, "vertices_trimmed": 0}

    if cfg.method == "poisson":
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            cloud,
            depth=cfg.poisson_depth,
            width=cfg.poisson_width,
            scale=cfg.poisson_scale,
        )
        # Il trimming e' il rimedio diretto all'artefatto principale del programma
        # sostituito: Poisson chiude le zone non rilevate inventando superficie.
        if cfg.density_quantile > 0.0:
            densities = np.asarray(densities)
            threshold = float(np.quantile(densities, cfg.density_quantile))
            to_remove = densities < threshold
            metrics["vertices_trimmed"] = int(to_remove.sum())
            metrics["density_threshold"] = threshold
            mesh.remove_vertices_by_mask(to_remove)
    elif cfg.method == "bpa":
        radii = o3d.utility.DoubleVector([factor * spacing for factor in cfg.bpa_radius_factors])
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(cloud, radii)
        metrics["radii"] = [factor * spacing for factor in cfg.bpa_radius_factors]
    else:
        alpha = cfg.alpha_factor * spacing
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(cloud, alpha)
        metrics["alpha"] = float(alpha)

    mesh.remove_unreferenced_vertices()
    vertices, faces = _from_mesh(mesh)
    metrics["vertices"] = int(len(vertices))
    metrics["triangles"] = int(len(faces))
    return vertices, faces, metrics


def simplify(
    vertices: np.ndarray, faces: np.ndarray, cfg: SimplifyConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 8: decimazione o remeshing isotropo, con smoothing di Taubin.

    Lo smoothing laplaciano e' escluso: contrae il volume e assottiglia il muro,
    cioe' falsa proprio la grandezza che il modello deve misurare.
    """
    metrics: dict[str, object] = {
        "enabled": cfg.enabled,
        "mode": cfg.mode,
        "triangles_before": int(len(faces)),
    }
    if not cfg.enabled:
        metrics["triangles_after"] = int(len(faces))
        return np.asarray(vertices), np.asarray(faces), metrics

    if cfg.mode == "decimate":
        if cfg.target_faces is None:
            raise ValueError("mode='decimate' richiede target_faces")
        mesh = _to_mesh(vertices, faces).simplify_quadric_decimation(cfg.target_faces)
        out_vertices, out_faces = _from_mesh(mesh)
    else:
        import pymeshlab

        mesh_set = pymeshlab.MeshSet()
        mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces)), "in")
        mesh_set.apply_filter(
            "meshing_isotropic_explicit_remeshing",
            targetlen=pymeshlab.PercentageValue(cfg.remesh_target_len_pct),
        )
        current = mesh_set.current_mesh()
        out_vertices = np.ascontiguousarray(current.vertex_matrix(), dtype=np.float64)
        out_faces = np.ascontiguousarray(current.face_matrix(), dtype=np.int64)

    if cfg.taubin_iterations > 0:
        mesh = _to_mesh(out_vertices, out_faces).filter_smooth_taubin(
            number_of_iterations=cfg.taubin_iterations
        )
        out_vertices, out_faces = _from_mesh(mesh)

    metrics["triangles_after"] = int(len(out_faces))
    metrics["vertices"] = int(len(out_vertices))
    return out_vertices, out_faces, metrics
```

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_surface.py -v`
Expected: PASS, dieci test.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/surface.py tests/test_surface.py
git commit -m "feat(meshrec): riduzione a voxel, normali, ricostruzione con trimming e semplificazione"
```

---

### Task 7: Rimozione degli outlier e ritaglio a box (step 2, prima parte)

**Files:**
- Create: `src/meshrec/core/segment.py`
- Test: `tests/test_segment.py`

**Interfaces:**
- Consumes: `meshrec.core.config.SegmentConfig`, `meshrec.core.synth.sample_box_surface`.
- Produces: `segment_cloud(points, cfg: SegmentConfig, spacing: float) -> tuple[np.ndarray, dict]`. Con `cfg.method == "crop"` esegue rimozione degli outlier più ritaglio; con `cfg.method == "auto"` solleva `NotImplementedError` fino al Task 11, che aggiunge la parte automatica **in questo stesso file**.
- Produce anche `remove_outliers(points, cfg) -> tuple[np.ndarray, dict]` e `crop_box(points, cfg) -> tuple[np.ndarray, dict]`, riusate dal Task 11.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_segment.py`:

```python
"""Step 2, prima parte: outlier statistici e ritaglio a box."""

import numpy as np
import pytest

from meshrec.core import config, segment, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 5.0


def test_isolated_points_are_removed():
    points = synth.sample_box_surface(SIZE, SPACING)
    strays = np.array([[500.0, 500.0, 500.0], [-400.0, -400.0, -400.0]])
    dirty = np.vstack([points, strays])

    clean, metrics = segment.remove_outliers(dirty, config.SegmentConfig())

    assert metrics["outliers_removed"] >= 2
    assert clean.max() < 400.0


def test_crop_box_keeps_only_the_points_inside():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0))

    cropped, metrics = segment.crop_box(points, cfg)

    assert cropped[:, 2].max() <= 100.0
    assert len(cropped) < len(points)
    assert metrics["points_after"] == len(cropped)


def test_crop_without_bounds_is_a_no_op():
    points = synth.sample_box_surface(SIZE, SPACING)
    cropped, metrics = segment.crop_box(points, config.SegmentConfig())
    assert len(cropped) == len(points)
    assert metrics["cropped"] is False


def test_crop_that_empties_the_cloud_raises():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(1000.0, 1000.0, 1000.0), crop_max=(2000.0, 2000.0, 2000.0))
    with pytest.raises(ValueError, match="nessun punto"):
        segment.crop_box(points, cfg)


def test_segment_cloud_in_crop_mode_chains_both_operations():
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[500.0, 500.0, 500.0]]])
    cfg = config.SegmentConfig(
        method="crop", crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0)
    )

    result, metrics = segment.segment_cloud(dirty, cfg, SPACING)

    assert result[:, 2].max() <= 100.0
    assert metrics["method"] == "crop"
    assert metrics["outliers_removed"] >= 1
    assert metrics["points_after"] == len(result)


def test_auto_mode_is_not_available_yet():
    points = synth.sample_box_surface(SIZE, SPACING)
    with pytest.raises(NotImplementedError):
        segment.segment_cloud(points, config.SegmentConfig(method="auto"), SPACING)
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_segment.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.segment'`

- [ ] **Step 3: Scrivere `core/segment.py`**

Note vincolanti:
- `PointCloud.remove_statistical_outlier(nb_neighbors, std_ratio)` restituisce `(cloud_filtrata, indici_tenuti)`.
- Il ritaglio è una maschera numpy, non serve Open3D.
- Una nuvola vuota dopo il ritaglio è un errore, non un risultato: significa che le coordinate del box sono nel sistema sbagliato.

```python
"""Step 2: isolamento del muro dalla scena.

In Fase 1 la selezione avviene da configurazione; in Fase 3 diventa un clic
nel viewport, ma il core resta lo stesso.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d

from meshrec.core.config import SegmentConfig


def remove_outliers(
    points: np.ndarray, cfg: SegmentConfig
) -> tuple[np.ndarray, dict[str, object]]:
    """Rimozione statistica degli outlier: punti isolati rispetto al vicinato."""
    cloud = o3d.geometry.PointCloud(
        o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    )
    filtered, _ = cloud.remove_statistical_outlier(
        nb_neighbors=cfg.outlier_neighbors, std_ratio=cfg.outlier_std_ratio
    )
    kept = np.ascontiguousarray(np.asarray(filtered.points), dtype=np.float64)
    if len(kept) == 0:
        raise ValueError("la rimozione degli outlier ha svuotato la nuvola: allenta std_ratio")
    return kept, {
        "points_before": int(len(points)),
        "outliers_removed": int(len(points) - len(kept)),
    }


def crop_box(points: np.ndarray, cfg: SegmentConfig) -> tuple[np.ndarray, dict[str, object]]:
    """Ritaglio a box allineato agli assi, definito da coordinate in configurazione."""
    points = np.asarray(points, dtype=np.float64)
    if cfg.crop_min is None or cfg.crop_max is None:
        return points, {"cropped": False, "points_after": int(len(points))}

    low = np.asarray(cfg.crop_min, dtype=np.float64)
    high = np.asarray(cfg.crop_max, dtype=np.float64)
    if (high <= low).any():
        raise ValueError(f"crop_max {cfg.crop_max} non e maggiore di crop_min {cfg.crop_min} su ogni asse")

    inside = ((points >= low) & (points <= high)).all(axis=1)
    if not inside.any():
        raise ValueError(
            f"nessun punto dentro il box {cfg.crop_min}-{cfg.crop_max}: "
            "controlla che le coordinate siano nelle unita di lavoro (mm) e nel sistema della nuvola"
        )
    return np.ascontiguousarray(points[inside]), {
        "cropped": True,
        "points_before": int(len(points)),
        "points_after": int(inside.sum()),
    }


def segment_cloud(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Step 2 completo. `method='auto'` arriva con la segmentazione automatica."""
    if cfg.method == "auto":
        raise NotImplementedError(
            "segmentazione automatica (RANSAC piu DBSCAN) non ancora disponibile: usa method='crop'"
        )

    cleaned, outlier_metrics = remove_outliers(points, cfg)
    cropped, crop_metrics = crop_box(cleaned, cfg)
    metrics: dict[str, object] = {"method": cfg.method, **outlier_metrics, **crop_metrics}
    metrics["points_before"] = int(len(points))
    metrics["points_after"] = int(len(cropped))
    return cropped, metrics
```

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_segment.py -v`
Expected: PASS, sei test.

- [ ] **Step 5: Commit**

```bash
cd meshrec
git add src/meshrec/core/segment.py tests/test_segment.py
git commit -m "feat(meshrec): rimozione outlier e ritaglio a box per isolare il muro"
```

---

### Task 8: Allineamento agli assi, set e deck completo (step 11)

**Files:**
- Modify: `src/meshrec/core/abaqus.py`
- Modify: `tests/test_abaqus.py` (aggiunte in coda; i test esistenti restano validi salvo l'asserzione sulle richieste di output, vedi Step 3)

**Interfaces:**
- Consumes: `meshrec.core.config.{AnalysisConfig, TetConfig, Material}`, `meshrec.core.quality.tet_volumes`.
- Produces:
  - `align_to_axes(nodes) -> tuple[np.ndarray, np.ndarray, dict]` — nodi allineati, matrice 4×4 della trasformazione, metriche
  - `build_node_sets(nodes, tolerance) -> dict[str, np.ndarray]`
  - `set_tolerance(nodes, tets, factor) -> float`
  - `export_model(path_inp, path_vtu, nodes, tets, cfg: AnalysisConfig, tet_cfg: TetConfig) -> dict` — orchestrazione dello step 11
  - `write_inp(...)` — firma invariata, richieste di output aggiornate
  - `write_vtu(path, nodes, tets) -> None`

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `tests/test_abaqus.py`:

```python
def test_alignment_puts_thickness_on_x_length_on_y_height_on_z():
    """Muro 1000 lungo, 300 alto, 50 spesso, ruotato di 30 gradi attorno a z."""
    rng = np.random.default_rng(0)
    raw = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(2000, 3))
    angle = np.radians(30.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated = raw @ rotation.T + np.array([500.0, -200.0, 75.0])

    aligned, transform, metrics = abaqus.align_to_axes(rotated)
    extent = aligned.max(axis=0) - aligned.min(axis=0)

    assert extent[0] == pytest.approx(50.0, rel=0.1)     # spessore su x
    assert extent[1] == pytest.approx(1000.0, rel=0.1)   # lunghezza su y
    assert extent[2] == pytest.approx(300.0, rel=0.1)    # altezza su z
    assert aligned[:, 2].min() == pytest.approx(0.0, abs=1e-9)
    assert transform.shape == (4, 4)
    assert metrics["extent"] == pytest.approx(extent.tolist(), rel=0.1)


def test_the_transform_is_invertible_back_to_the_original_frame():
    rng = np.random.default_rng(1)
    original = rng.uniform([0.0, 0.0, 0.0], [1000.0, 50.0, 300.0], size=(500, 3))
    aligned, transform, _ = abaqus.align_to_axes(original)

    homogeneous = np.column_stack([aligned, np.ones(len(aligned))])
    back = (homogeneous @ np.linalg.inv(transform).T)[:, :3]

    assert back == pytest.approx(original, abs=1e-6)


def test_node_sets_cover_the_six_faces_of_a_box():
    nodes = np.array(
        [[x, y, z] for x in (0.0, 50.0) for y in (0.0, 1000.0) for z in (0.0, 300.0)]
    )
    sets = abaqus.build_node_sets(nodes, tolerance=1.0)

    assert sorted(sets) == ["BASE", "FACE_BACK", "FACE_FRONT", "SIDE_LEFT", "SIDE_RIGHT", "TOP"]
    assert len(sets["BASE"]) == 4
    assert nodes[sets["BASE"]][:, 2] == pytest.approx(0.0)
    assert nodes[sets["TOP"]][:, 2] == pytest.approx(300.0)
    assert nodes[sets["FACE_FRONT"]][:, 0] == pytest.approx(0.0)
    assert nodes[sets["FACE_BACK"]][:, 0] == pytest.approx(50.0)


def test_output_requests_are_in_the_modern_form(tmp_path):
    """*NODE FILE produce .fil in Abaqus, non .odb: la Fase 1 usa *OUTPUT, FIELD."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())
    path = tmp_path / "modello.inp"

    abaqus.write_inp(
        path,
        nodes,
        tets,
        node_sets=abaqus.build_node_sets(nodes, tolerance=1.0),
        material=config.Material(),
    )
    text = path.read_text(encoding="ascii")

    assert "*OUTPUT, FIELD" in text
    assert "*NODE OUTPUT" in text
    assert "*ELEMENT OUTPUT" in text
    assert "*NODE FILE" not in text
    assert "*EL FILE" not in text


def test_export_model_writes_both_files_and_reports_mass(tmp_path):
    meshio = pytest.importorskip("meshio")
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp",
        tmp_path / "wall_model.vtu",
        nodes,
        tets,
        config.AnalysisConfig(),
        config.TetConfig(),
    )

    assert (tmp_path / "wall_model.inp").exists()
    assert (tmp_path / "wall_model.vtu").exists()
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0, rel=0.02)
    assert metrics["mass"] == pytest.approx(metrics["volume"] * 1.8e-9, rel=1e-6)
    assert metrics["node_sets"]["BASE"] > 0
    read_back = meshio.read(tmp_path / "wall_model.vtu")
    assert len(read_back.points) == len(nodes)


def test_c3d10_is_refused_until_the_writer_supports_it(tmp_path):
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())

    with pytest.raises(NotImplementedError, match="C3D10"):
        abaqus.export_model(
            tmp_path / "m.inp",
            tmp_path / "m.vtu",
            nodes,
            tets,
            config.AnalysisConfig(),
            config.TetConfig(element="C3D10"),
        )
```

Completare gli import di `tests/test_abaqus.py` con `config`, `synth`, `volume` se non già presenti. Se un test esistente asserisce la presenza di `*NODE FILE`, aggiornarlo alla forma moderna: è la modifica prevista da questo task, non una regressione.

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_abaqus.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'align_to_axes'`

- [ ] **Step 3: Modificare `core/abaqus.py`**

Note vincolanti:
- L'allineamento usa le componenti principali della nuvola di nodi. L'assegnazione degli assi non è per ordine di autovalore ma per significato: **la direzione di minore estensione diventa x** (lo spessore); fra le due restanti, quella più vicina al verticale originale diventa **z** (l'altezza), perché la gravità agisce lungo il verticale reale e non lungo un asse scelto per comodità; l'ultima diventa **y**.
- La matrice va resa destrorsa (`det == +1`): se il determinante è negativo, invertire il segno di una colonna, altrimenti la trasformazione è una riflessione e i tetraedri risultano tutti invertiti.
- Dopo la rotazione si trasla in modo che `z.min() == 0`, e che `x.min()` e `y.min()` siano zero: il modello sta nel primo ottante e i set si leggono senza sorprese.
- La tolleranza dei set deriva dalla dimensione media dell'elemento, calcolata come `(volume medio del tetraedro * 6 * sqrt(2)) ** (1/3)`, cioè il lato del tetraedro regolare di pari volume.
- `write_inp` cambia solo nelle ultime righe: `*NODE FILE`/`*EL FILE` diventano `*OUTPUT, FIELD` più `*NODE OUTPUT` con `U` e `*ELEMENT OUTPUT` con `S, E`. CalculiX 2.22 accetta questa forma.

```python
def align_to_axes(nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Rototraslazione ai piani principali: spessore su x, lunghezza su y, altezza su z.

    La trasformazione e' restituita come matrice 4x4 e va salvata nei metadati:
    e' l'unico modo per riportare i risultati nel sistema originale dello scanner.
    """
    points = np.asarray(nodes, dtype=np.float64)
    centre = points.mean(axis=0)
    centred = points - centre

    _, _, principal = np.linalg.svd(centred, full_matrices=False)
    extents = np.ptp(centred @ principal.T, axis=0)

    thickness_axis = int(np.argmin(extents))
    remaining = [index for index in range(3) if index != thickness_axis]
    # fra le due direzioni restanti, l'altezza e' quella piu vicina al verticale
    # originale: la gravita agisce lungo il verticale reale, non lungo l'asse
    # con l'estensione maggiore.
    verticality = [abs(principal[index][2]) for index in remaining]
    height_axis = remaining[int(np.argmax(verticality))]
    length_axis = remaining[1 - int(np.argmax(verticality))]

    rotation = np.stack(
        [principal[thickness_axis], principal[length_axis], principal[height_axis]]
    )
    if np.linalg.det(rotation) < 0.0:
        rotation[2] = -rotation[2]  # mantiene la terna destrorsa: una riflessione invertirebbe i tetraedri

    aligned = centred @ rotation.T
    shift = aligned.min(axis=0)
    aligned = aligned - shift

    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ centre - shift

    metrics = {
        "extent": (aligned.max(axis=0) - aligned.min(axis=0)).tolist(),
        "transform": transform.tolist(),
    }
    return np.ascontiguousarray(aligned), transform, metrics


def set_tolerance(nodes: np.ndarray, tets: np.ndarray, factor: float) -> float:
    """Tolleranza dei set derivata dalla dimensione media dell'elemento."""
    from meshrec.core.quality import tet_volumes

    mean_volume = float(np.abs(tet_volumes(nodes, tets)).mean())
    edge = (mean_volume * 6.0 * np.sqrt(2.0)) ** (1.0 / 3.0)
    return factor * edge


def build_node_sets(nodes: np.ndarray, tolerance: float) -> dict[str, np.ndarray]:
    """I sei set di faccia, sul modello gia allineato agli assi."""
    points = np.asarray(nodes, dtype=np.float64)
    low = points.min(axis=0)
    high = points.max(axis=0)
    return {
        "BASE": np.flatnonzero(points[:, 2] <= low[2] + tolerance),
        "TOP": np.flatnonzero(points[:, 2] >= high[2] - tolerance),
        "FACE_FRONT": np.flatnonzero(points[:, 0] <= low[0] + tolerance),
        "FACE_BACK": np.flatnonzero(points[:, 0] >= high[0] - tolerance),
        "SIDE_LEFT": np.flatnonzero(points[:, 1] <= low[1] + tolerance),
        "SIDE_RIGHT": np.flatnonzero(points[:, 1] >= high[1] - tolerance),
    }


def write_vtu(path: Path, nodes: np.ndarray, tets: np.ndarray) -> None:
    """Esportazione per la visualizzazione, delegata a meshio."""
    import meshio

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write_points_cells(
        str(path),
        np.asarray(nodes, dtype=np.float64),
        [("tetra", np.asarray(tets, dtype=np.int64))],
    )


def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    tets: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
) -> dict[str, object]:
    """Step 11: allinea, costruisce i set, scrive il deck e il file di visualizzazione."""
    from meshrec.core.quality import tet_volumes

    if tet_cfg.element != "C3D4":
        raise NotImplementedError(
            f"elemento {tet_cfg.element} non supportato dal writer: TetGen produce i nodi "
            "di lato con order=2, ma il deck scrive quattro nodi per elemento. "
            "Usa C3D4 finche il writer non gestisce i dieci nodi."
        )

    aligned, transform, align_metrics = align_to_axes(nodes)
    tolerance = set_tolerance(aligned, tets, cfg.set_tolerance_factor)
    node_sets = build_node_sets(aligned, tolerance)
    if len(node_sets[cfg.fixed_nset]) == 0:
        raise ValueError(f"il set vincolato '{cfg.fixed_nset}' e vuoto: tolleranza {tolerance:.3f} mm troppo stretta")

    write_inp(
        path_inp,
        aligned,
        tets,
        node_sets=node_sets,
        material=cfg.material,
        fixed_nset=cfg.fixed_nset,
        gravity=cfg.gravity,
        step_name=cfg.step_name,
    )
    write_vtu(path_vtu, aligned, tets)

    volume = float(np.abs(tet_volumes(aligned, tets)).sum())
    return {
        "transform": transform.tolist(),
        "extent": align_metrics["extent"],
        "set_tolerance": float(tolerance),
        "node_sets": {name: int(len(indices)) for name, indices in node_sets.items()},
        "volume": volume,
        "mass": volume * cfg.material.density,
        "inp": str(path_inp),
        "vtu": str(path_vtu),
    }
```

Sostituire l'ultima riga di `write_inp` (attualmente `lines += ["*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP", ""]`) con:

```python
    lines += [
        "*OUTPUT, FIELD",
        "*NODE OUTPUT",
        "U",
        "*ELEMENT OUTPUT",
        "S, E",
        "*END STEP",
        "",
    ]
```

Aggiungere agli import in testa al modulo: `from meshrec.core.config import GRAVITY_MM_S2, AnalysisConfig, Material, TetConfig`.

**Rinviato esplicitamente:** le superfici di elemento (`*SURFACE, TYPE=ELEMENT`) per `FACE_FRONT` e `FACE_BACK`, previste dalla spec di architettura §8 per i carichi di pressione. La Fase 1 applica soltanto il peso proprio, quindi nessun carico le userebbe, e la mappatura delle facce del tetraedro sulle etichette `S1`-`S4` di Abaqus è fonte di errori silenziosi. Arrivano con la Fase 4, che introduce i carichi laterali. I node set delle stesse facce esistono già e coprono vincoli e letture.

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_abaqus.py -v`
Expected: PASS, esistenti più sei nuovi.

- [ ] **Step 5: Verificare che CalculiX accetti ancora il deck**

Run: `cd meshrec && uv run pytest tests/feasibility/test_calculix.py -v -m feasibility`
Expected: PASS. Se fallisce, la forma moderna delle richieste di output non è accettata da CalculiX 2.22 e va segnalato come esito bloccante invece di essere aggirato.

- [ ] **Step 6: Commit**

```bash
cd meshrec
git add src/meshrec/core/abaqus.py tests/test_abaqus.py
git commit -m "feat(meshrec): allineamento agli assi, set di faccia e richieste di output moderne"
```

---

### Task 9: Sequenza della pipeline e test di integrazione

**Files:**
- Create: `src/meshrec/core/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: tutto il core dei Task 1-8.
- Produces: `run(cfg: PipelineConfig) -> dict[str, object]` — esegue la sequenza, scrive `config.yaml`, gli artefatti numerati e `metrics.json` dentro `cfg.run.out_dir`, restituisce il dizionario completo delle metriche. Più `ARTIFACTS: dict[int, str]`, la mappa da numero di step a nome del file di artefatto, usata da `cli.py` per la ripresa.

- [ ] **Step 1: Scrivere il test di integrazione**

Creare `tests/test_pipeline.py`:

```python
"""Verifica di Fase 1: il parallelepipedo a soluzione nota attraversa tutta la catena."""

import json

import numpy as np
import pytest

from meshrec.core import config, io, pipeline, quality, synth

SIZE = (120.0, 60.0, 240.0)
SPACING = 4.0
EXACT_VOLUME = 120.0 * 60.0 * 240.0


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    """Esegue la pipeline una volta sola: e' il test piu lento della suite."""
    pytest.importorskip("pymeshfix")
    base = tmp_path_factory.mktemp("run")
    cloud_path = base / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, SPACING))

    cfg = config.PipelineConfig(
        input=config.InputConfig(path=cloud_path, spacing_sample=5000),
        downsample=config.DownsampleConfig(voxel_size=SPACING),
        surface=config.SurfaceConfig(poisson_depth=8, density_quantile=0.02),
        tet=config.TetConfig(min_ratio=1.2),
        run=config.RunConfig(out_dir=base / "out"),
    )
    metrics = pipeline.run(cfg)
    return base / "out", metrics


def test_the_run_directory_holds_config_metrics_and_the_deck(run_dir):
    out, _ = run_dir
    assert (out / "config.yaml").exists()
    assert (out / "metrics.json").exists()
    assert (out / "wall_model.inp").exists()
    assert (out / "wall_model.vtu").exists()
    assert config.load_config(out / "config.yaml").tet.min_ratio == pytest.approx(1.2)


def test_the_surface_is_closed(run_dir):
    _, metrics = run_dir
    assert metrics["06_repair"]["watertight_after"] is True


def test_the_volume_matches_the_exact_value(run_dir):
    _, metrics = run_dir
    assert metrics["11_export"]["volume"] == pytest.approx(EXACT_VOLUME, rel=0.1)


def test_no_inverted_tetrahedra(run_dir):
    _, metrics = run_dir
    assert metrics["10_volume_quality"]["inverted"] == 0
    assert metrics["10_volume_quality"]["min_dihedral_deg"]["min"] > 0.0


def test_the_deck_is_readable_and_counts_agree(run_dir):
    meshio = pytest.importorskip("meshio")
    out, metrics = run_dir
    mesh = meshio.read(out / "wall_model.inp")
    assert len(mesh.points) == metrics["09_tetrahedralize"]["nodes"]
    assert sum(len(block.data) for block in mesh.cells) == metrics["09_tetrahedralize"]["tets"]


def test_the_base_set_holds_only_the_nodes_at_the_lowest_level(run_dir):
    out, metrics = run_dir
    text = (out / "wall_model.inp").read_text(encoding="ascii")
    assert "*NSET, NSET=BASE" in text
    assert metrics["11_export"]["node_sets"]["BASE"] > 0

    meshio = pytest.importorskip("meshio")
    points = meshio.read(out / "wall_model.inp").points
    lines = text.splitlines()
    start = lines.index("*NSET, NSET=BASE") + 1
    indices = []
    for line in lines[start:]:
        if line.startswith("*"):
            break
        indices += [int(value) - 1 for value in line.split(",") if value.strip()]
    tolerance = metrics["11_export"]["set_tolerance"]
    assert len(indices) == metrics["11_export"]["node_sets"]["BASE"]
    assert points[indices][:, 2].max() <= points[:, 2].min() + tolerance + 1e-9


def test_the_mass_follows_from_density_and_volume(run_dir):
    _, metrics = run_dir
    density = config.Material().density
    assert metrics["11_export"]["mass"] == pytest.approx(
        metrics["11_export"]["volume"] * density, rel=1e-9
    )


def test_geometric_error_against_the_source_cloud_is_reported(run_dir):
    pytest.importorskip("pymeshlab")
    _, metrics = run_dir
    error = metrics["07_surface_quality"]["geometric_error"]
    assert error["hausdorff"] > 0.0
    assert error["cloud_to_mesh"]["RMS"] < SPACING * 2.0


def test_metrics_json_is_the_same_as_the_returned_dictionary(run_dir):
    out, metrics = run_dir
    with (out / "metrics.json").open(encoding="utf-8") as handle:
        assert json.load(handle) == json.loads(json.dumps(metrics))


def test_the_same_configuration_run_twice_gives_the_same_result(tmp_path):
    """Criterio di accettazione: la stessa configurazione produce lo stesso risultato."""
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))

    def once(name):
        cfg = config.PipelineConfig(
            input=config.InputConfig(path=cloud_path, spacing_sample=2000),
            downsample=config.DownsampleConfig(voxel_size=8.0),
            surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
            run=config.RunConfig(out_dir=tmp_path / name),
        )
        return pipeline.run(cfg)

    first, second = once("a"), once("b")
    assert first["09_tetrahedralize"]["nodes"] == second["09_tetrahedralize"]["nodes"]
    assert first["09_tetrahedralize"]["tets"] == second["09_tetrahedralize"]["tets"]
    assert first["11_export"]["volume"] == pytest.approx(second["11_export"]["volume"], rel=1e-9)
```

- [ ] **Step 2: Eseguire il test per vederlo fallire**

Run: `cd meshrec && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.pipeline'`

- [ ] **Step 3: Scrivere `core/pipeline.py`**

Note vincolanti:
- Codice lineare, un blocco per step, nessun registro di step e nessuna astrazione: la sequenza è fissa e leggerla dall'alto in basso deve bastare a capirla.
- Le chiavi di `metrics` sono `"01_load"`, `"02_segment"`, `"03_downsample"`, `"04_normals"`, `"05_reconstruct"`, `"06_repair"`, `"07_surface_quality"`, `"08_simplify"`, `"09_tetrahedralize"`, `"10_volume_quality"`, `"11_export"`. Sono le stesse chiavi che il test di integrazione asserisce.
- `metrics.json` va scritto con `default=float` per gli scalari numpy che potessero sfuggire, e la scrittura avviene anche se uno step successivo fallisce: gli artefatti degli step precedenti restano intatti, come richiesto dalla spec di robustezza. Realizzarlo con `try/finally` attorno alla sequenza.
- `from_step` salta gli step precedenti e ricarica l'artefatto dello step `from_step - 1`. La ripresa si fida dell'operatore: non verifica che gli artefatti a monte siano stati prodotti con la configurazione corrente. Il docstring deve dirlo.
- L'errore geometrico dello step 7 confronta la superficie con la nuvola **segmentata** (uscita dello step 2), non con quella grezza.

```python
"""Sequenza degli step. E' l'unico modulo che conosce l'ordine.

Ogni step scrive il proprio artefatto numerato: la ripresa con `from_step`
ricarica l'artefatto precedente invece di rifare il lavoro.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from meshrec.core import abaqus, io, quality, repair, segment, surface, volume
from meshrec.core.config import PipelineConfig, save_config

ARTIFACTS: dict[int, str] = {
    1: "01_cloud.ply",
    2: "02_segmented.ply",
    3: "03_downsampled.ply",
    4: "04_normals.ply",
    5: "05_surface.ply",
    6: "06_repaired.ply",
    8: "08_simplified.ply",
    9: "09_volume.vtu",
}


def _write_mesh(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )
    o3d.io.write_triangle_mesh(str(path), mesh)


def _read_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    import open3d as o3d

    mesh = o3d.io.read_triangle_mesh(str(path))
    return (
        np.ascontiguousarray(np.asarray(mesh.vertices), dtype=np.float64),
        np.ascontiguousarray(np.asarray(mesh.triangles), dtype=np.int64),
    )


def run(cfg: PipelineConfig) -> dict[str, object]:
    """Esegue la pipeline e restituisce le metriche di ogni step.

    `cfg.run.from_step` riparte dagli artefatti gia sul disco. La ripresa si
    fida dell'operatore: non verifica che quegli artefatti siano stati prodotti
    con la configurazione corrente.
    """
    out = Path(cfg.run.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")
    metrics: dict[str, object] = {}
    start = cfg.run.from_step

    try:
        if start <= 1:
            points, step_metrics = io.load_cloud(cfg.input)
            metrics["01_load"] = step_metrics
            io.write_cloud(out / ARTIFACTS[1], points)
        else:
            points, _ = io.read_cloud(out / ARTIFACTS[min(start - 1, 4)])

        spacing = float(metrics.get("01_load", {}).get("spacing") or io.mean_spacing(
            points, cfg.input.spacing_sample, cfg.input.seed
        ))

        if start <= 2:
            points, step_metrics = segment.segment_cloud(points, cfg.segment, spacing)
            metrics["02_segment"] = step_metrics
            io.write_cloud(out / ARTIFACTS[2], points)
        source_cloud = points

        if start <= 3:
            points, step_metrics = surface.downsample(points, cfg.downsample, spacing)
            metrics["03_downsample"] = step_metrics
            io.write_cloud(out / ARTIFACTS[3], points)

        if start <= 4:
            normals, step_metrics = surface.estimate_normals(points, cfg.normals, spacing)
            metrics["04_normals"] = step_metrics
            io.write_cloud(out / ARTIFACTS[4], points, normals)
        else:
            points, normals = io.read_cloud(out / ARTIFACTS[4])

        if start <= 5:
            vertices, faces, step_metrics = surface.reconstruct(points, normals, cfg.surface, spacing)
            metrics["05_reconstruct"] = step_metrics
            _write_mesh(out / ARTIFACTS[5], vertices, faces)
        else:
            vertices, faces = _read_mesh(out / ARTIFACTS[min(start - 1, 8)])

        if start <= 6:
            vertices, faces, step_metrics = repair.repair_surface(vertices, faces, cfg.repair)
            metrics["06_repair"] = step_metrics
            _write_mesh(out / ARTIFACTS[6], vertices, faces)

        if start <= 7:
            step_metrics = quality.surface_metrics(vertices, faces)
            step_metrics["geometric_error"] = quality.geometric_error(vertices, faces, source_cloud)
            metrics["07_surface_quality"] = step_metrics

        if start <= 8:
            vertices, faces, step_metrics = surface.simplify(vertices, faces, cfg.simplify)
            metrics["08_simplify"] = step_metrics
            if cfg.simplify.enabled:
                _write_mesh(out / ARTIFACTS[8], vertices, faces)

        nodes, tets, step_metrics = volume.tetrahedralize_with_metrics(vertices, faces, cfg.tet)
        metrics["09_tetrahedralize"] = step_metrics
        abaqus.write_vtu(out / ARTIFACTS[9], nodes, tets)

        metrics["10_volume_quality"] = quality.volume_metrics(nodes, tets)

        metrics["11_export"] = abaqus.export_model(
            out / "wall_model.inp", out / "wall_model.vtu", nodes, tets, cfg.analysis, cfg.tet
        )
    finally:
        with (out / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2, default=float, ensure_ascii=False)

    return metrics
```

Chi implementa deve verificare che la ripresa da uno step qualsiasi ricarichi l'artefatto giusto: gli indici usati nelle chiamate a `ARTIFACTS[...]` vanno controllati con una prova manuale per ogni valore di `from_step` da 2 a 9, non solo per il caso 1. Se la logica di ricarica risulta contorta, semplificarla è preferibile a difenderla: la forma minima accettabile è una tabella esplicita da `from_step` all'artefatto da ricaricare.

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_pipeline.py -v`
Expected: PASS, dieci test.

- [ ] **Step 5: Eseguire tutta la suite**

Run: `cd meshrec && uv run pytest -v`
Expected: PASS, nessuna regressione sui task precedenti.

- [ ] **Step 6: Commit**

```bash
cd meshrec
git add src/meshrec/core/pipeline.py tests/test_pipeline.py
git commit -m "feat(meshrec): sequenza completa della pipeline e test di integrazione sul cubo"
```

---

### Task 10: Riga di comando

**Files:**
- Create: `src/meshrec/cli.py`
- Modify: `pyproject.toml` (sezione `[project.scripts]`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `meshrec.core.config.{load_config, save_config, PipelineConfig, InputConfig}`, `meshrec.core.pipeline.run`.
- Produces: `main(argv: list[str] | None = None) -> int`, comandi `run` e `init`.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_cli.py`:

```python
"""Riga di comando minima: eseguire una configurazione e generarne una di esempio."""

import pytest

from meshrec import cli
from meshrec.core import config, io, synth

SIZE = (120.0, 60.0, 240.0)


def test_init_writes_a_loadable_configuration(tmp_path):
    target = tmp_path / "config.yaml"
    assert cli.main(["init", str(target), "--input", "nuvola.ply"]) == 0
    assert config.load_config(target).input.path.name == "nuvola.ply"


def test_run_executes_the_pipeline_and_writes_the_deck(tmp_path):
    pytest.importorskip("pymeshfix")
    cloud_path = tmp_path / "box.ply"
    io.write_cloud(cloud_path, synth.sample_box_surface(SIZE, 8.0))
    cfg = config.PipelineConfig(
        input=config.InputConfig(path=cloud_path, spacing_sample=2000),
        downsample=config.DownsampleConfig(voxel_size=8.0),
        surface=config.SurfaceConfig(poisson_depth=7, density_quantile=0.02),
        run=config.RunConfig(out_dir=tmp_path / "out"),
    )
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 0
    assert (tmp_path / "out" / "wall_model.inp").exists()


def test_from_step_overrides_the_configuration(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cfg):
        seen["from_step"] = cfg.run.from_step
        return {}

    monkeypatch.setattr(cli.pipeline, "run", fake_run)
    cfg = config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml"), "--from-step", "5"]) == 0
    assert seen["from_step"] == 5


def test_a_failing_run_reports_the_error_without_a_traceback(tmp_path, capsys):
    cfg = config.PipelineConfig(input=config.InputConfig(path=tmp_path / "assente.ply"))
    config.save_config(cfg, tmp_path / "config.yaml")

    assert cli.main(["run", str(tmp_path / "config.yaml")]) == 1
    assert "nessun punto letto" in capsys.readouterr().err
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_cli.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.cli'`

- [ ] **Step 3: Scrivere `src/meshrec/cli.py`**

```python
"""Riga di comando minima, non definitiva: serve a lavorare nelle Fasi 1 e 2.

L'interfaccia vera arriva in Fase 3. Qui non vive alcun valore predefinito:
tutto viene dal file di configurazione.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meshrec.core import pipeline
from meshrec.core.config import InputConfig, PipelineConfig, load_config, save_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshrec", description="Da nuvola di punti a modello FEM")
    commands = parser.add_subparsers(dest="command", required=True)

    run_command = commands.add_parser("run", help="esegue la pipeline su un file di configurazione")
    run_command.add_argument("config", type=Path)
    run_command.add_argument(
        "--from-step",
        type=int,
        default=None,
        help=(
            "riparte dagli artefatti gia presenti nella cartella di elaborazione. "
            "Non verifica che siano stati prodotti con questa configurazione."
        ),
    )
    run_command.add_argument("--out-dir", type=Path, default=None)

    init_command = commands.add_parser("init", help="scrive una configurazione completa di esempio")
    init_command.add_argument("config", type=Path)
    init_command.add_argument("--input", type=Path, required=True, help="nuvola di partenza")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "init":
        save_config(PipelineConfig(input=InputConfig(path=args.input)), args.config)
        print(f"configurazione scritta in {args.config}")
        return 0

    cfg = load_config(args.config)
    if args.from_step is not None:
        cfg.run.from_step = args.from_step
    if args.out_dir is not None:
        cfg.run.out_dir = args.out_dir

    try:
        metrics = pipeline.run(cfg)
    except Exception as error:  # la riga di comando riporta il problema, non lo stack
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(json.dumps(metrics, indent=2, default=float, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Registrare il comando in `pyproject.toml`**

Aggiungere dopo la sezione `[project]`:

```toml
[project.scripts]
meshrec = "meshrec.cli:main"
```

Poi: `cd meshrec && uv sync`

- [ ] **Step 5: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_cli.py -v`
Expected: PASS, quattro test.

- [ ] **Step 6: Provare il comando a mano**

Run: `cd meshrec && uv run meshrec init /tmp/esempio.yaml --input nuvola.ply`
Expected: il file esiste e contiene tutti i gruppi di parametri.

- [ ] **Step 7: Commit**

```bash
cd meshrec
git add src/meshrec/cli.py tests/test_cli.py pyproject.toml uv.lock
git commit -m "feat(meshrec): riga di comando con esecuzione, ripresa da step e configurazione di esempio"
```

---

### Task 11: Segmentazione automatica con RANSAC e DBSCAN (step 2, seconda parte)

**Files:**
- Modify: `src/meshrec/core/segment.py`
- Modify: `tests/test_segment.py` (aggiunte in coda; il test `test_auto_mode_is_not_available_yet` va rimosso, è il segnaposto che questo task sostituisce)

**Interfaces:**
- Consumes: quanto prodotto dal Task 7 nello stesso file.
- Produces: `extract_planes(points, cfg, spacing) -> tuple[list[np.ndarray], np.ndarray, dict]`, `cluster(points, cfg, spacing) -> tuple[list[np.ndarray], dict]`, e `segment_cloud(..., method="auto")` funzionante con metriche `planes_found`, `clusters_found`, `cluster_points`, `planarity_rms`, `thickness`.

- [ ] **Step 1: Scrivere i test che falliscono**

Rimuovere `test_auto_mode_is_not_available_yet` e aggiungere in coda a `tests/test_segment.py`:

```python
def _scene():
    """Pavimento orizzontale piu un muro verticale: la struttura di lab_frame.pcd in piccolo."""
    rng = np.random.default_rng(0)
    floor = np.column_stack(
        [
            rng.uniform(-500.0, 500.0, 4000),
            rng.uniform(-500.0, 500.0, 4000),
            rng.normal(0.0, 1.0, 4000),
        ]
    )
    wall = np.column_stack(
        [
            rng.normal(200.0, 12.0, 3000),
            rng.uniform(-300.0, 300.0, 3000),
            rng.uniform(0.0, 400.0, 3000),
        ]
    )
    return np.vstack([floor, wall])


def test_ransac_finds_the_floor_plane():
    points = _scene()
    planes, residual, metrics = segment.extract_planes(
        points, config.SegmentConfig(plane_max_count=1), spacing=8.0
    )
    assert metrics["planes_found"] == 1
    assert len(planes[0]) > 2000
    assert len(residual) < len(points)


def test_auto_mode_isolates_the_wall():
    points = _scene()
    cfg = config.SegmentConfig(method="auto", plane_max_count=1, cluster_min_points=100)

    wall, metrics = segment.segment_cloud(points, cfg, spacing=8.0)

    assert metrics["method"] == "auto"
    assert metrics["clusters_found"] >= 1
    assert len(wall) > 1000
    # il muro sta attorno a x = 200 ed e sottile: il pavimento e sparito
    assert wall[:, 0].mean() == pytest.approx(200.0, abs=30.0)
    assert metrics["thickness"] < 120.0
    assert metrics["planarity_rms"] < 40.0


def test_choosing_a_cluster_index_beyond_the_last_raises():
    points = _scene()
    cfg = config.SegmentConfig(method="auto", plane_max_count=1, cluster_index=99)
    with pytest.raises(ValueError, match="cluster_index"):
        segment.segment_cloud(points, cfg, spacing=8.0)
```

- [ ] **Step 2: Eseguire i test per vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_segment.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.segment' has no attribute 'extract_planes'`

- [ ] **Step 3: Implementare in `core/segment.py`**

Note vincolanti:
- `PointCloud.segment_plane(distance_threshold, ransac_n=3, num_iterations)` restituisce `(modello, indici_inlier)`.
- `PointCloud.cluster_dbscan(eps, min_points)` restituisce un vettore di etichette con `-1` per il rumore.
- Il ciclo di estrazione dei piani si ferma quando il piano trovato ha meno di `plane_min_points_ratio` dei punti iniziali: continuare significherebbe estrarre piani inventati dal rumore.
- I cluster vanno ordinati per numero di punti decrescente, così `cluster_index=0` è il più numeroso.
- Planarità e spessore si misurano sul cluster scelto: la direzione di minore estensione (autovettore minore della matrice di covarianza) dà lo spessore come estensione lungo quella direzione, e lo scarto quadratico medio delle proiezioni dà la planarità.
- La determinazione delle soglie deriva dalla spaziatura: `plane_distance_factor * spacing` per RANSAC, `cluster_eps_factor * spacing` per DBSCAN.

- RANSAC è randomizzato: senza `o3d.utility.random.seed`, due esecuzioni della stessa configurazione danno risultati diversi e il criterio di riproducibilità della Fase 1 cade.

Aggiungere a `core/segment.py`:

```python
def _as_cloud(points: np.ndarray) -> o3d.geometry.PointCloud:
    return o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64)))


def extract_planes(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[list[np.ndarray], np.ndarray, dict[str, object]]:
    """Estrazione iterativa di piani con RANSAC: pavimento e pareti via dal residuo.

    Il seme fissato rende l'estrazione riproducibile: senza, la stessa
    configurazione produrrebbe segmentazioni diverse a ogni esecuzione.
    """
    o3d.utility.random.seed(0)
    threshold = cfg.plane_distance_factor * spacing
    minimum = max(3, int(cfg.plane_min_points_ratio * len(points)))

    planes: list[np.ndarray] = []
    residual = np.asarray(points, dtype=np.float64)
    for _ in range(cfg.plane_max_count):
        if len(residual) < minimum:
            break
        _, inliers = _as_cloud(residual).segment_plane(
            distance_threshold=threshold, ransac_n=3, num_iterations=1000
        )
        if len(inliers) < minimum:
            # sotto questa soglia il piano e' rumore adattato, non una superficie reale
            break
        mask = np.zeros(len(residual), dtype=bool)
        mask[np.asarray(inliers, dtype=np.int64)] = True
        planes.append(np.ascontiguousarray(residual[mask]))
        residual = np.ascontiguousarray(residual[~mask])

    metrics = {
        "planes_found": len(planes),
        "plane_distance": float(threshold),
        "plane_points": [int(len(plane)) for plane in planes],
        "residual_points": int(len(residual)),
    }
    return planes, residual, metrics


def cluster(
    points: np.ndarray, cfg: SegmentConfig, spacing: float
) -> tuple[list[np.ndarray], dict[str, object]]:
    """DBSCAN sul residuo. I gruppi tornano ordinati per numerosita decrescente."""
    eps = cfg.cluster_eps_factor * spacing
    labels = np.asarray(
        _as_cloud(points).cluster_dbscan(eps=eps, min_points=cfg.cluster_min_points)
    )
    groups = [
        np.ascontiguousarray(np.asarray(points)[labels == label])
        for label in np.unique(labels[labels >= 0])
    ]
    groups.sort(key=len, reverse=True)
    metrics = {
        "clusters_found": len(groups),
        "cluster_eps": float(eps),
        "cluster_sizes": [int(len(group)) for group in groups],
        "noise_points": int((labels < 0).sum()),
    }
    return groups, metrics


def _plane_metrics(points: np.ndarray) -> dict[str, object]:
    """Planarita e spessore del cluster scelto, lungo la sua direzione piu sottile."""
    centred = np.asarray(points, dtype=np.float64) - np.mean(points, axis=0)
    _, _, principal = np.linalg.svd(centred, full_matrices=False)
    projection = centred @ principal[2]
    return {
        "planarity_rms": float(np.sqrt(np.mean(projection**2))),
        "thickness": float(np.ptp(projection)),
        "normal": principal[2].tolist(),
    }
```

Sostituire il ramo `NotImplementedError` di `segment_cloud` con:

```python
    cleaned, outlier_metrics = remove_outliers(points, cfg)
    cropped, crop_metrics = crop_box(cleaned, cfg)
    metrics: dict[str, object] = {"method": cfg.method, **outlier_metrics, **crop_metrics}

    if cfg.method == "auto":
        _, residual, plane_metrics = extract_planes(cropped, cfg, spacing)
        groups, cluster_metrics = cluster(residual, cfg, spacing)
        metrics.update(plane_metrics)
        metrics.update(cluster_metrics)
        if cfg.cluster_index >= len(groups):
            raise ValueError(
                f"cluster_index={cfg.cluster_index} ma sono stati trovati {len(groups)} cluster: "
                "allenta cluster_eps_factor o abbassa cluster_min_points"
            )
        chosen = groups[cfg.cluster_index]
        metrics["cluster_points"] = int(len(chosen))
        metrics.update(_plane_metrics(chosen))
        cropped = chosen

    metrics["points_before"] = int(len(points))
    metrics["points_after"] = int(len(cropped))
    return cropped, metrics
```

Il numero di piani estratti, il numero di cluster, i punti del cluster scelto, la planarità e lo spessore stimato sono le metriche richieste dalla spec per lo step 2: compaiono tutte in `metrics`.

- [ ] **Step 4: Eseguire i test**

Run: `cd meshrec && uv run pytest tests/test_segment.py -v`
Expected: PASS, otto test (i cinque del Task 7 meno il segnaposto, più tre nuovi).

- [ ] **Step 5: Provare sulla scansione reale**

```bash
cd meshrec
uv run meshrec init lab.yaml --input "../Nuvole di punti/lab_frame.pcd"
```

Modificare `lab.yaml` mettendo `segment.method: auto` e la scala corretta, poi:

```bash
uv run meshrec run lab.yaml --out-dir runs/lab
```

Annotare in `docs/fase-1-esiti.md` (creandolo) il numero di piani estratti, i cluster trovati, i punti del cluster scelto, planarità e spessore, e se il muro isolato è quello atteso. Se la segmentazione non isola il muro, riportare i parametri provati e l'esito invece di dichiarare il task riuscito: il file `lab_frame.pcd` non va mai aggiunto a un commit.

- [ ] **Step 6: Commit**

```bash
cd meshrec
git add src/meshrec/core/segment.py tests/test_segment.py docs/fase-1-esiti.md
git commit -m "feat(meshrec): segmentazione automatica con RANSAC e DBSCAN"
```

---

### Task 12: Validazione su dati reali e confronto Gmsh a parità di elementi

**Files:**
- Create: `src/meshrec/core/gmsh_backend.py`
- Test: `tests/test_gmsh_backend.py`
- Create/Modify: `meshrec/docs/fase-1-esiti.md`

**Interfaces:**
- Consumes: `meshrec.core.config.TetConfig`, `meshrec.core.quality.{volume_metrics, min_dihedral_angles}`.
- Produces: `tetrahedralize_gmsh(vertices, faces, target_elements: int | None) -> tuple[np.ndarray, np.ndarray, dict]`.

**Perché un modulo a parte:** la verifica di Fase 0 non ottimizza una mesh già prodotta da TetGen — costruisce la mesh dentro Gmsh a partire dalla superficie e poi la ottimizza. È quindi un secondo generatore, non un post-processore, e tenerlo fuori da `volume.py` evita di far dipendere da Gmsh il percorso principale, che resta obbligatorio e senza Gmsh.

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `tests/test_gmsh_backend.py`:

```python
"""Gmsh come generatore alternativo: il confronto va fatto a parita di elementi."""

import numpy as np
import pytest

from meshrec.core import gmsh_backend, quality, synth, volume
from meshrec.core.config import TetConfig

SIZE = (100.0, 40.0, 200.0)


def test_gmsh_produces_a_valid_tetrahedral_mesh():
    pytest.importorskip("gmsh")
    vertices, faces = synth.box_mesh(SIZE)

    nodes, tets, metrics = gmsh_backend.tetrahedralize_gmsh(vertices, faces, target_elements=None)

    assert len(tets) > 10
    assert len(quality.inverted_tets(nodes, tets)) == 0
    assert metrics["tets"] == len(tets)


def test_gmsh_beats_tetgen_at_comparable_element_counts():
    """L'esito di Fase 0 confondeva il guadagno di qualita con un raffittimento."""
    pytest.importorskip("gmsh")
    vertices, faces = synth.box_mesh(SIZE)

    tetgen_nodes, tetgen_tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TetConfig())
    gmsh_nodes, gmsh_tets, _ = gmsh_backend.tetrahedralize_gmsh(
        vertices, faces, target_elements=len(tetgen_tets)
    )

    ratio = len(gmsh_tets) / len(tetgen_tets)
    assert 0.7 < ratio < 1.4, f"confronto non a parita di elementi: rapporto {ratio:.2f}"

    tetgen_min = quality.min_dihedral_angles(tetgen_nodes, tetgen_tets).min()
    gmsh_min = quality.min_dihedral_angles(gmsh_nodes, gmsh_tets).min()
    print(f"angolo diedro minimo: tetgen={tetgen_min:.3f} gmsh={gmsh_min:.3f} rapporto_elementi={ratio:.2f}")
    assert gmsh_min > 0.0
```

- [ ] **Step 2: Eseguire il test per vederlo fallire**

Run: `cd meshrec && uv run pytest tests/test_gmsh_backend.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.gmsh_backend'`

- [ ] **Step 3: Scrivere `core/gmsh_backend.py`**

Note vincolanti:
- La sequenza Gmsh è quella accertata in Fase 0 da `tests/feasibility/test_gmsh.py`, che va letto prima di scrivere questo modulo.
- Gmsh rinumera i nodi: `getNodes` restituisce tag 1-based non contigui, e gli elementi rimandano a quei tag. Vanno rimappati sugli indici dell'array con un vettore di ricerca. Saltare la rimappatura produce una mesh silenziosamente sbagliata.
- `target_elements` si realizza fissando `Mesh.MeshSizeMax` prima di `generate(3)`: per circa N tetraedri di volume medio `V/N`, il lato del tetraedro regolare corrispondente è `(V/N * 6 * sqrt(2)) ** (1/3)`. È una stima, non un vincolo, e il test ammette un rapporto fra 0,7 e 1,4 proprio per questo.
- `pipeline.py` non importa questo modulo: il percorso principale resta senza Gmsh.

```python
"""Gmsh come generatore alternativo di mesh tetraedrica.

Non e' un post-processore: Gmsh ricostruisce la geometria dalla superficie e
genera la propria mesh, quindi il confronto con TetGen ha senso solo a parita
di numero di elementi. La misura di Fase 0 non lo era.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from meshrec.core.quality import mesh_volume


def tetrahedralize_gmsh(
    vertices: np.ndarray, faces: np.ndarray, target_elements: int | None
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Genera e ottimizza una mesh tetraedrica con Gmsh a partire dalla superficie chiusa."""
    import gmsh
    import meshio

    with tempfile.TemporaryDirectory() as folder:
        stl_path = Path(folder) / "surface.stl"
        meshio.write_points_cells(
            str(stl_path),
            np.asarray(vertices, dtype=np.float64),
            [("triangle", np.asarray(faces, dtype=np.int64))],
        )

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.merge(str(stl_path))
            gmsh.model.mesh.classifySurfaces(np.pi / 4.0, True, True)
            gmsh.model.mesh.createGeometry()

            surfaces = [entity[1] for entity in gmsh.model.getEntities(2)]
            loop = gmsh.model.geo.addSurfaceLoop(surfaces)
            gmsh.model.geo.addVolume([loop])
            gmsh.model.geo.synchronize()

            size = None
            if target_elements is not None:
                enclosed = abs(mesh_volume(vertices, faces))
                size = (enclosed / target_elements * 6.0 * np.sqrt(2.0)) ** (1.0 / 3.0)
                gmsh.option.setNumber("Mesh.MeshSizeMax", size)
                gmsh.option.setNumber("Mesh.MeshSizeMin", 0.0)

            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")

            node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
            element_types, _, node_tags_per_element = gmsh.model.mesh.getElements(3)
            if 4 not in element_types:
                raise RuntimeError("Gmsh non ha prodotto tetraedri lineari (tipo 4)")
            tet_tags = np.asarray(node_tags_per_element[list(element_types).index(4)], dtype=np.int64)
        finally:
            gmsh.finalize()

    node_tags = np.asarray(node_tags, dtype=np.int64)
    nodes = np.ascontiguousarray(np.asarray(coordinates, dtype=np.float64).reshape(-1, 3))

    # I tag dei nodi sono 1-based e non contigui: senza rimappatura gli elementi
    # punterebbero a posizioni sbagliate dell'array, e la mesh sarebbe sbagliata
    # senza alcun segnale.
    lookup = np.zeros(node_tags.max() + 1, dtype=np.int64)
    lookup[node_tags] = np.arange(len(node_tags))
    tets = np.ascontiguousarray(lookup[tet_tags].reshape(-1, 4))

    metrics = {
        "nodes": int(len(nodes)),
        "tets": int(len(tets)),
        "target_elements": target_elements,
        "mesh_size_max": None if target_elements is None else float(size),
        "optimizer": "Netgen",
    }
    return nodes, tets, metrics
```

- [ ] **Step 4: Eseguire il test**

Run: `cd meshrec && uv run pytest tests/test_gmsh_backend.py -v`
Expected: PASS, due test. Il secondo stampa i due angoli diedri minimi e il rapporto di elementi.

- [ ] **Step 5: Eseguire la pipeline su `muro_generato.ply`**

```bash
cd meshrec
uv run meshrec init muro.yaml --input "../Nuvole di punti/muro_generato.ply"
```

Prima di eseguire: aprire `muro.yaml` e impostare `input.scale` dopo aver verificato l'ingombro. Il modo rapido è eseguire con `expected_size` non impostato, leggere `extent` in `metrics.json` e confrontarlo con le dimensioni reali del muro; poi impostare `expected_size` in modo che il controllo di scala diventi attivo per le esecuzioni successive.

```bash
uv run meshrec run muro.yaml --out-dir runs/muro
```

- [ ] **Step 6: Scrivere gli esiti in `meshrec/docs/fase-1-esiti.md`**

Il documento va scritto in italiano, in prosa, e deve contenere:
- ingombro letto, fattore di scala usato, dimensioni reali di riferimento;
- metriche di ogni step per l'esecuzione su `muro_generato.ply`, prese da `metrics.json`;
- l'errore geometrico bidirezionale rispetto alla nuvola sorgente, con i numeri;
- l'esito della segmentazione su `lab_frame.pcd` (dal Task 11) o il rinvio a quel task se non ancora eseguito;
- il confronto Gmsh contro TetGen a parità di elementi, con i due angoli diedri minimi e il rapporto di elementi effettivo, e la conclusione: se il guadagno sparisce a parità di elementi, dirlo, perché la misura di Fase 0 (0,037787 → 0,423365 con +43,5% di elementi) va corretta e non confermata;
- lo stato del controllo dei dati con Abaqus: non eseguito, e perché.

- [ ] **Step 7: Commit**

```bash
cd meshrec
git add src/meshrec/core/gmsh_backend.py tests/test_gmsh_backend.py docs/fase-1-esiti.md
git commit -m "feat(meshrec): generatore Gmsh alternativo ed esiti della validazione di Fase 1"
```

---

## Verifica finale della Fase 1

Al termine dei dodici task:

```bash
cd meshrec
uv run pytest -v
uv run pytest -v -m feasibility
```

Criteri della spec, da confermare uno per uno con i numeri alla mano:

| Criterio | Come si verifica |
|---|---|
| Il test di integrazione passa | `tests/test_pipeline.py`, dieci test |
| Le metriche di errore geometrico sono calcolate e riportate | `metrics.json`, chiave `07_surface_quality.geometric_error` |
| Su `lab_frame.pcd` la segmentazione isola il muro e la pipeline arriva in fondo | Task 11, annotato in `docs/fase-1-esiti.md` |
| La stessa configurazione, rieseguita, produce lo stesso risultato | `test_the_same_configuration_run_twice_gives_the_same_result` |
| Il deck è valido | `meshio` in lettura più CalculiX in soluzione; il controllo dei dati Abaqus resta dovuto |
