"""Modelli di configurazione: unico luogo dove un parametro ha un valore predefinito.

Sistema di unita di lavoro: mm, N, MPa, tonnellata, secondo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

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
        default=None,
        description=(
            "area [mm^2] oltre la quale un'apertura viene segnalata, sia essa un ciclo "
            "di bordo chiuso o un cammino aperto"
        ),
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

    min_ratio: float = Field(
        default=1.8,
        gt=0.0,
        description=(
            "rapporto raggio-spigolo massimo: valori piu bassi danno elementi piu "
            "regolari, ma il raffinamento puo' non convergere su geometrie difficili. "
            "Sul muro di riferimento 1.6 e valori inferiori interrompono TetGen con un "
            "errore interno mentre 1.7 converge: il predefinito 1.8 non e' quindi il "
            "valore piu severo che porta a termine il lavoro, ma quello che tiene un "
            "decimo di margine sopra di esso. Misura completa da 1.4 a 2.5 in "
            "docs/fase-1-min-ratio.md"
        ),
    )
    max_volume: float | None = Field(default=None, gt=0.0, description="volume massimo elemento [mm^3]")
    max_steiner_points: int = Field(
        default=-1,
        ge=-1,
        description=(
            "punti che TetGen puo' aggiungere per raffinare; -1 = nessun limite. "
            "Il predefinito della libreria tetgen e' 100000: su geometrie a scala "
            "reale quel tetto viene raggiunto e il raffinamento si ferma li, "
            "restituendo una mesh troncata che nessuna metrica segnalava"
        ),
    )
    nobisect: bool = Field(
        default=False,
        description=(
            "vieta a TetGen di suddividere le facce della superficie di ingresso. "
            "Serve dove la scala locale della superficie e' minuscola: la "
            "suddivisione per invasione ricorre fino alla distanza fra lembi "
            "opposti, e su lab_frame.pcd, che ha strozzature sotto il millimetro, "
            "il raffinamento non converge a nessun min_ratio finche' resta "
            "consentita. Attenzione: con nobisect attivo TetGen non aggiunge punti "
            "sul bordo, quindi su una superficie di ingresso grossolana max_volume "
            "puo' restare disatteso; il caso e' segnalato con "
            "IneffectiveVolumeLimitWarning. Vedi docs/fase-1-min-ratio.md"
        ),
    )
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
    element: Literal["C3D4", "C3D10"] = "C3D4"


class AnalysisConfig(BaseModel):
    """Materiale e analisi."""

    material: Material = Field(default_factory=Material)
    gravity: float = Field(default=GRAVITY_MM_S2, gt=0.0)
    fixed_nset: str = "BASE"
    step_name: str = "GRAVITA"
    set_tolerance_factor: float = Field(
        default=6.0,
        gt=0.0,
        description=(
            "moltiplica la spaziatura dei nodi sul bordo del maglio di volume e "
            "da' la tolleranza con cui i set di faccia sono estratti. Il "
            "predefinito 6 e' misurato: e' il piu piccolo intero che copre almeno "
            "il 95% della superficie d'appoggio su entrambe le corse di "
            "riferimento e per i quattro set utilizzabili. Il margine ha la "
            "stessa struttura di quello di tet.min_ratio: 5 e' il primo valore "
            "che non regge (SIDE_LEFT di lab_crop si ferma al 94,37%), 4 il primo "
            "che crolla (77,89%), e sopra 6 si compra copertura marginale a "
            "prezzo pieno (a 8 il BASE del muro cresce del 41% per l'1,58% di "
            "copertura). Il predefinito precedente, 0,5 volte il volume medio "
            "dell'elemento, lasciava BASE al 55,78% della base sul muro e al "
            "34,76% su lab_crop. Vedi docs/fase-1-tolleranza-set.md"
        ),
    )


class RunConfig(BaseModel):
    """Esecuzione: percorsi e ripresa."""

    # La riga di comando e, in Fase 3, l'interfaccia assegnano questi campi
    # direttamente: senza validate_assignment pydantic non li verifica e un
    # valore fuori dominio arriva silenziosamente fino alla pipeline.
    model_config = ConfigDict(validate_assignment=True)

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
