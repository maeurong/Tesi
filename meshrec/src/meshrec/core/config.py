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
    poisson_n_threads: int = Field(
        default=1, description="thread per il solutore Poisson; 1 = riproducibile, -1 = automatico"
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
    from_step: int = Field(
        default=1,
        ge=1,
        le=9,
        description=(
            "la ripresa arriva fino allo step 9 (tetraedrizzazione); gli step 10 e 11 "
            "sono metriche di volume ed esportazione, senza lavoro costoso da saltare, "
            "e vengono comunque rieseguiti a ogni corsa"
        ),
    )


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
