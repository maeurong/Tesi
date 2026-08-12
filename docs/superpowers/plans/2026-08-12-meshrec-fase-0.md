# MeshRec Fase 0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire lo scheletro del progetto `meshrec` e chiudere con prove eseguibili tutte le incognite sulle dipendenze esterne, così che la Fase 1 parta senza scelte tecniche aperte.

**Architecture:** Pacchetto Python con layout `src/`, gestito da `uv`. Il nucleo geometrico è fatto di funzioni pure su array NumPy (nessuno stato globale, nessuna dipendenza dall'interfaccia). Le verifiche di fattibilità sono scritte come test `pytest` marcati `feasibility`: ogni dipendenza esterna ha un test che ne dimostra la capacità richiesta su una geometria sintetica con soluzione nota; l'esito, positivo o negativo, viene registrato in un documento di fase insieme alla decisione di ripiego.

**Tech Stack:** Python 3.12, uv, NumPy, SciPy, Open3D, TetGen, meshio, pydantic, pytest. In valutazione: PyMeshFix, wildmeshing (fTetWild), PyMeshLab, Gmsh, CalculiX.

## Global Constraints

- Piattaforma: Windows 11, Python 3.12 (`requires-python = ">=3.12,<3.13"`), ambiente gestito con `uv`.
- Sistema di unità di lavoro: **mm, N, MPa, tonnellata, secondo**. Densità in t/mm³ (1800 kg/m³ = `1.8e-9`), accelerazione di gravità `9810.0` mm/s².
- Radice del progetto: `C:\Users\mario\GitHub\Tesi\meshrec\`. Le spec vivono in `C:\Users\mario\GitHub\Tesi\docs\superpowers\specs\`.
- Layout: package in `src/meshrec/`, test in `tests/`, verifiche di fattibilità in `tests/feasibility/`.
- Identificatori, nomi di file e API in inglese; prose, commenti e documenti in italiano.
- Nessuna dipendenza oltre a quelle elencate nel Tech Stack. Le dipendenze in valutazione entrano nel gruppo opzionale `feasibility`, mai fra quelle obbligatorie.
- Ogni funzione geometrica riceve e restituisce `numpy.ndarray` di `float64` (coordinate) o `int64` (indici), con indici **0-based** dentro il codice; la conversione a 1-based avviene solo nella scrittura dell'`.inp`.
- I test non devono dipendere dai dati reali (`lab_frame.pcd`, `muro_generato.ply`): usano solo geometria sintetica generata dal codice.
- Marcatore pytest `feasibility` escluso dall'esecuzione predefinita; si lancia esplicitamente con `-m feasibility`.
- I test del nucleo sono divisi per modulo (`test_synth.py`, `test_quality.py`, `test_volume.py`, `test_abaqus.py`) invece del singolo `test_pipeline.py` citato nella spec: quel file nasce in Fase 1 insieme alla pipeline, quando esisterà una catena completa da provare end-to-end.
- Nessun file `__init__.py` dentro `tests/`: pytest inserisce la cartella del test in `sys.path`, quindi i moduli di supporto si importano per nome semplice.
- Un commit per task, messaggio in italiano, prefisso convenzionale (`chore:`, `feat:`, `test:`, `docs:`).
- Lavorare sul ramo `feat/meshrec-fase-0`, creato dal ramo `docs/meshrec-design`.

---

### Task 1: Scaffold del progetto e campionatore di superficie sintetica

**Files:**
- Create: `meshrec/pyproject.toml`
- Create: `meshrec/.gitignore`
- Create: `meshrec/src/meshrec/__init__.py`
- Create: `meshrec/src/meshrec/synth.py`
- Test: `meshrec/tests/test_synth.py`

**Interfaces:**
- Consumes: niente (primo task)
- Produces: `meshrec.synth.sample_box_surface(size: tuple[float, float, float], spacing: float, noise: float = 0.0, seed: int = 0) -> np.ndarray` con forma `(N, 3)`, `float64`

- [ ] **Step 1: Creare il ramo di lavoro**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git checkout docs/meshrec-design
git checkout -b feat/meshrec-fase-0
```

- [ ] **Step 2: Scrivere `meshrec/pyproject.toml`**

```toml
[project]
name = "meshrec"
version = "0.1.0"
description = "Pipeline riproducibile da nuvola di punti a modello FEM di muratura"
requires-python = ">=3.12,<3.13"
dependencies = [
    "numpy>=2.0",
    "scipy>=1.13",
    "open3d>=0.19",
    "tetgen>=0.6",
    "meshio>=5.3",
    "pydantic>=2.7",
]

[project.optional-dependencies]
feasibility = []

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/meshrec"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not feasibility'"
markers = [
    "feasibility: verifica di fattibilita di una dipendenza esterna (Fase 0)",
]
```

- [ ] **Step 3: Scrivere `meshrec/.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
runs/
*.egg-info/
```

- [ ] **Step 4: Creare il package vuoto e sincronizzare l'ambiente**

Creare `meshrec/src/meshrec/__init__.py` con una sola riga:

```python
"""MeshRec — pipeline da nuvola di punti a modello FEM."""
```

Poi:

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv sync
```

Atteso: l'ambiente virtuale viene creato e tutte le dipendenze si installano. Se `open3d` o `tetgen` non hanno wheel per Python 3.12 su Windows, **fermarsi e riportarlo**: è un risultato di Fase 0 che cambia le scelte a valle.

- [ ] **Step 5: Scrivere il test che fallisce**

Creare `meshrec/tests/test_synth.py`:

```python
import numpy as np
import pytest

from meshrec import synth

SIZE = (100.0, 40.0, 200.0)


def test_sample_box_surface_lies_on_the_box():
    points = synth.sample_box_surface(SIZE, spacing=10.0)

    assert points.ndim == 2 and points.shape[1] == 3
    assert points.dtype == np.float64
    assert len(points) > 100

    # ogni punto appartiene ad almeno una delle sei facce
    on_face = np.zeros(len(points), dtype=bool)
    for axis, length in enumerate(SIZE):
        on_face |= np.isclose(points[:, axis], 0.0)
        on_face |= np.isclose(points[:, axis], length)
    assert on_face.all()


def test_sample_box_surface_fills_the_bounding_box():
    points = synth.sample_box_surface(SIZE, spacing=10.0)

    assert points.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert points.max(axis=0) == pytest.approx(list(SIZE))


def test_sample_box_surface_is_deterministic_and_noise_is_bounded():
    a = synth.sample_box_surface(SIZE, spacing=10.0, noise=0.5, seed=7)
    b = synth.sample_box_surface(SIZE, spacing=10.0, noise=0.5, seed=7)
    clean = synth.sample_box_surface(SIZE, spacing=10.0)

    assert np.array_equal(a, b)
    assert a.shape == clean.shape
    assert np.abs(a - clean).max() < 5.0  # 10 sigma


def test_smaller_spacing_gives_more_points():
    coarse = synth.sample_box_surface(SIZE, spacing=20.0)
    fine = synth.sample_box_surface(SIZE, spacing=5.0)

    assert len(fine) > 4 * len(coarse)
```

- [ ] **Step 6: Eseguire il test e verificare che fallisca**

```bash
uv run pytest tests/test_synth.py -v
```

Atteso: FAIL con `ImportError: cannot import name 'synth' from 'meshrec'`.

- [ ] **Step 7: Implementare `src/meshrec/synth.py`**

```python
"""Geometrie sintetiche con soluzione nota, usate da test e verifiche."""

from __future__ import annotations

import numpy as np


def _face_grid(u_length: float, v_length: float, spacing: float) -> tuple[np.ndarray, np.ndarray]:
    """Griglia regolare su una faccia rettangolare u x v."""
    n_u = max(2, int(round(u_length / spacing)) + 1)
    n_v = max(2, int(round(v_length / spacing)) + 1)
    u, v = np.meshgrid(
        np.linspace(0.0, u_length, n_u),
        np.linspace(0.0, v_length, n_v),
        indexing="ij",
    )
    return u.ravel(), v.ravel()


def sample_box_surface(
    size: tuple[float, float, float],
    spacing: float,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Campiona le sei facce di un parallelepipedo con passo `spacing`.

    Il volume racchiuso vale esattamente lx*ly*lz: serve come verita di
    riferimento per validare la pipeline.
    """
    lx, ly, lz = (float(value) for value in size)
    faces: list[np.ndarray] = []

    a, b = _face_grid(lx, ly, spacing)
    for z in (0.0, lz):
        faces.append(np.column_stack([a, b, np.full_like(a, z)]))

    a, b = _face_grid(lx, lz, spacing)
    for y in (0.0, ly):
        faces.append(np.column_stack([a, np.full_like(a, y), b]))

    a, b = _face_grid(ly, lz, spacing)
    for x in (0.0, lx):
        faces.append(np.column_stack([np.full_like(a, x), a, b]))

    points = np.unique(np.round(np.vstack(faces), 9), axis=0)

    if noise > 0.0:
        rng = np.random.default_rng(seed)
        points = points + rng.normal(0.0, noise, points.shape)

    return np.ascontiguousarray(points, dtype=np.float64)
```

- [ ] **Step 8: Eseguire i test e verificare che passino**

```bash
uv run pytest tests/test_synth.py -v
```

Atteso: 4 test PASS.

- [ ] **Step 9: Verifica di funzionamento di Open3D**

Aggiungere in coda a `meshrec/tests/test_synth.py`:

```python
def test_open3d_reads_and_downsamples_a_synthetic_cloud(tmp_path):
    import open3d as o3d

    points = synth.sample_box_surface(SIZE, spacing=2.0)

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)

    path = tmp_path / "box.ply"
    assert o3d.io.write_point_cloud(str(path), cloud)

    reloaded = o3d.io.read_point_cloud(str(path))
    assert len(reloaded.points) == len(points)

    reduced = reloaded.voxel_down_sample(voxel_size=10.0)
    assert 0 < len(reduced.points) < len(points)
```

Eseguire:

```bash
uv run pytest tests/test_synth.py -v
```

Atteso: 5 test PASS. Se Open3D non si importa o va in crash, riportarlo: è un esito di Fase 0.

- [ ] **Step 10: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/pyproject.toml meshrec/.gitignore meshrec/uv.lock meshrec/src meshrec/tests
git commit -m "chore: scheletro del progetto meshrec e campionatore di superficie sintetica"
```

---

### Task 2: Primitive di qualità della mesh e mesh sintetica del parallelepipedo

**Files:**
- Create: `meshrec/src/meshrec/quality.py`
- Modify: `meshrec/src/meshrec/synth.py` (aggiunta di `box_mesh` e `punch_holes`)
- Test: `meshrec/tests/test_quality.py`

**Interfaces:**
- Consumes: `meshrec.synth.sample_box_surface` (Task 1)
- Produces:
  - `meshrec.synth.box_mesh(size: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]` — vertici `(8, 3)` float64 e triangoli `(12, 3)` int64 con normali uscenti
  - `meshrec.synth.punch_holes(faces: np.ndarray, remove: tuple[int, ...] = (0, 6)) -> np.ndarray` — triangoli senza quelli indicati
  - `meshrec.quality.boundary_edges(faces: np.ndarray) -> np.ndarray` — spigoli `(M, 2)` appartenenti a un solo triangolo
  - `meshrec.quality.is_watertight(faces: np.ndarray) -> bool`
  - `meshrec.quality.mesh_volume(vertices: np.ndarray, faces: np.ndarray) -> float` — volume con segno, positivo per normali uscenti

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `meshrec/tests/test_quality.py`:

```python
import numpy as np
import pytest

from meshrec import quality, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_box_mesh_has_eight_vertices_and_twelve_triangles():
    vertices, faces = synth.box_mesh(SIZE)

    assert vertices.shape == (8, 3)
    assert faces.shape == (12, 3)
    assert vertices.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert vertices.max(axis=0) == pytest.approx(list(SIZE))


def test_box_mesh_is_watertight_and_has_no_boundary_edges():
    _, faces = synth.box_mesh(SIZE)

    assert len(quality.boundary_edges(faces)) == 0
    assert quality.is_watertight(faces)


def test_box_mesh_volume_is_exact_and_positive():
    vertices, faces = synth.box_mesh(SIZE)

    assert quality.mesh_volume(vertices, faces) == pytest.approx(EXACT_VOLUME)


def test_punch_holes_opens_the_mesh():
    _, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    assert len(damaged) == 10
    # triangoli 0 e 6 condividono spigolo (1,2): sono adiacenti, quindi un
    # foro unico con 4 spigoli di bordo (non due fori separati da 3 ciascuno)
    assert len(quality.boundary_edges(damaged)) == 4
    assert not quality.is_watertight(damaged)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

```bash
uv run pytest tests/test_quality.py -v
```

Atteso: FAIL con `ImportError: cannot import name 'quality' from 'meshrec'`.

- [ ] **Step 3: Implementare `src/meshrec/quality.py`**

```python
"""Metriche topologiche e geometriche su mesh triangolari e tetraedriche."""

from __future__ import annotations

import numpy as np


def _edge_counts(faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spigoli unici (ordinati per indice) e numero di triangoli che li usano."""
    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.sort(edges, axis=1)
    return np.unique(edges, axis=0, return_counts=True)


def boundary_edges(faces: np.ndarray) -> np.ndarray:
    """Spigoli appartenenti a un solo triangolo: bordi aperti della mesh."""
    unique, counts = _edge_counts(np.asarray(faces))
    return unique[counts == 1]


def is_watertight(faces: np.ndarray) -> bool:
    """Vero se ogni spigolo e condiviso da esattamente due triangoli."""
    _, counts = _edge_counts(np.asarray(faces))
    return bool((counts == 2).all())


def mesh_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Volume racchiuso, con segno positivo se le normali sono uscenti.

    Teorema della divergenza applicato ai tetraedri origine-triangolo.
    """
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
```

- [ ] **Step 4: Aggiungere `box_mesh` e `punch_holes` a `src/meshrec/synth.py`**

Aggiungere in coda al file:

```python
_BOX_FACES = np.array(
    [
        [0, 2, 1], [0, 3, 2],   # z = 0
        [4, 5, 6], [4, 6, 7],   # z = lz
        [0, 1, 5], [0, 5, 4],   # y = 0
        [1, 2, 6], [1, 6, 5],   # x = lx
        [2, 3, 7], [2, 7, 6],   # y = ly
        [3, 0, 4], [3, 4, 7],   # x = 0
    ],
    dtype=np.int64,
)


def box_mesh(size: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    """Parallelepipedo come mesh triangolare chiusa con normali uscenti."""
    lx, ly, lz = (float(value) for value in size)
    vertices = np.array(
        [
            [0.0, 0.0, 0.0], [lx, 0.0, 0.0], [lx, ly, 0.0], [0.0, ly, 0.0],
            [0.0, 0.0, lz], [lx, 0.0, lz], [lx, ly, lz], [0.0, ly, lz],
        ],
        dtype=np.float64,
    )
    return vertices, _BOX_FACES.copy()


def punch_holes(faces: np.ndarray, remove: tuple[int, ...] = (0, 6)) -> np.ndarray:
    """Rimuove i triangoli indicati dalla mesh.

    Il numero di fori dipende dall'adiacenza dei triangoli rimossi, non dal
    loro numero: i due indici di default (0, 6) condividono lo spigolo (1, 2),
    quindi aprono un foro unico a cavallo delle due facce, con 4 spigoli di
    bordo (non due fori separati con tre spigoli ciascuno).
    """
    keep = np.ones(len(faces), dtype=bool)
    keep[list(remove)] = False
    return np.ascontiguousarray(np.asarray(faces)[keep])
```

- [ ] **Step 5: Eseguire i test e verificare che passino**

```bash
uv run pytest tests/test_quality.py -v
```

Atteso: 4 test PASS. Se `test_box_mesh_volume_is_exact_and_positive` dà volume negativo, l'orientamento di `_BOX_FACES` è invertito: scambiare le ultime due colonne di tutte le righe.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/src/meshrec/quality.py meshrec/src/meshrec/synth.py meshrec/tests/test_quality.py
git commit -m "feat: primitive di qualita della mesh e parallelepipedo sintetico"
```

---

### Task 3: Tetraedrizzazione con TetGen e metriche di volume

**Files:**
- Create: `meshrec/src/meshrec/volume.py`
- Modify: `meshrec/src/meshrec/quality.py` (aggiunta di `tet_volumes` e `inverted_tets`)
- Test: `meshrec/tests/test_volume.py`

**Interfaces:**
- Consumes: `meshrec.synth.box_mesh` (Task 2), `meshrec.quality.mesh_volume` (Task 2)
- Produces:
  - `meshrec.volume.tetrahedralize(vertices: np.ndarray, faces: np.ndarray, min_ratio: float = 1.1, max_volume: float | None = None) -> tuple[np.ndarray, np.ndarray]` — nodi `(N, 3)` float64 e tetraedri `(M, 4)` int64 0-based
  - `meshrec.quality.tet_volumes(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray` — volumi con segno, forma `(M,)`
  - `meshrec.quality.inverted_tets(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray` — indici dei tetraedri con volume non positivo

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `meshrec/tests/test_volume.py`:

```python
import numpy as np
import pytest

from meshrec import quality, synth, volume

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_tetrahedralize_fills_the_box():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    assert nodes.ndim == 2 and nodes.shape[1] == 3
    assert tets.ndim == 2 and tets.shape[1] == 4
    assert len(tets) > 10
    assert tets.max() < len(nodes)


def test_sum_of_tet_volumes_equals_the_exact_volume():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    total = np.abs(quality.tet_volumes(nodes, tets)).sum()
    assert total == pytest.approx(EXACT_VOLUME, rel=1e-6)


def test_no_inverted_elements():
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=50_000.0)

    assert len(quality.inverted_tets(nodes, tets)) == 0


def test_max_volume_controls_the_number_of_elements():
    vertices, faces = synth.box_mesh(SIZE)
    _, coarse = volume.tetrahedralize(vertices, faces, max_volume=200_000.0)
    _, fine = volume.tetrahedralize(vertices, faces, max_volume=20_000.0)

    assert len(fine) > len(coarse)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

```bash
uv run pytest tests/test_volume.py -v
```

Atteso: FAIL con `ImportError: cannot import name 'volume' from 'meshrec'`.

- [ ] **Step 3: Implementare `src/meshrec/volume.py`**

```python
"""Tetraedrizzazione della superficie chiusa."""

from __future__ import annotations

import numpy as np
import tetgen


def tetrahedralize(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_ratio: float = 1.1,
    max_volume: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Riempie di tetraedri lineari la superficie chiusa data.

    `min_ratio` e il rapporto raggio-spigolo massimo ammesso (piu basso =
    elementi piu regolari e piu numerosi); `max_volume` limita il volume del
    singolo elemento nelle unita di lavoro.
    """
    generator = tetgen.TetGen(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces, dtype=np.int32),
    )
    options: dict[str, object] = {"order": 1, "minratio": float(min_ratio)}
    if max_volume is not None:
        options["maxvolume"] = float(max_volume)

    nodes, tets = generator.tetrahedralize(**options)
    return (
        np.ascontiguousarray(nodes, dtype=np.float64),
        np.ascontiguousarray(tets, dtype=np.int64),
    )
```

- [ ] **Step 4: Aggiungere le metriche tetraedriche a `src/meshrec/quality.py`**

Aggiungere in coda al file:

```python
def tet_volumes(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni tetraedro; negativo se l'elemento e invertito."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a, b, c, d = n[t[:, 0]], n[t[:, 1]], n[t[:, 2]], n[t[:, 3]]
    return np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a)) / 6.0


def inverted_tets(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Indici dei tetraedri degeneri o invertiti (volume non positivo)."""
    return np.flatnonzero(tet_volumes(nodes, tets) <= 0.0)
```

- [ ] **Step 5: Eseguire i test e verificare che passino**

```bash
uv run pytest tests/test_volume.py -v
```

Atteso: 4 test PASS. Se `test_no_inverted_elements` fallisce con tutti i volumi negativi, TetGen emette la connettività con orientamento opposto: invertire due colonne in `tetrahedralize` prima di restituire, non nel test.

Se la versione installata di `tetgen` rifiuta i parametri per nome, passare gli interruttori nella forma testuale equivalente e annotarlo:

```python
switches = f"pq{min_ratio}"
if max_volume is not None:
    switches += f"a{max_volume}"
nodes, tets = generator.tetrahedralize(switches=switches)
```

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/src/meshrec/volume.py meshrec/src/meshrec/quality.py meshrec/tests/test_volume.py
git commit -m "feat: tetraedrizzazione con TetGen e metriche di volume"
```

---

### Task 4: Scrittura del file `.inp` per Abaqus

**Files:**
- Create: `meshrec/src/meshrec/config.py`
- Create: `meshrec/src/meshrec/abaqus.py`
- Test: `meshrec/tests/test_abaqus.py`

**Interfaces:**
- Consumes: `meshrec.volume.tetrahedralize` (Task 3), `meshrec.synth.box_mesh` (Task 2)
- Produces:
  - `meshrec.config.Material` — modello pydantic con `name: str = "MURATURA"`, `young: float = 1500.0` (MPa), `poisson: float = 0.2`, `density: float = 1.8e-9` (t/mm³)
  - `meshrec.abaqus.write_inp(path: Path, nodes: np.ndarray, tets: np.ndarray, *, node_sets: dict[str, np.ndarray], material: Material, fixed_nset: str = "BASE", print_nsets: tuple[str, ...] = (), gravity: float = 9810.0, elset: str = "ALL_WALL", step_name: str = "GRAVITA") -> None`

Nota di ambito: la spec colloca il writer completo in Fase 1. Qui se ne scrive la parte minima indispensabile, perché senza un `.inp` la verifica di CalculiX (Task 9) non è eseguibile. La Fase 1 vi aggiungerà superfici di elemento e set di faccia.

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `meshrec/tests/test_abaqus.py`:

```python
import meshio
import numpy as np
import pytest

from meshrec import abaqus, synth, volume
from meshrec.config import Material

SIZE = (100.0, 40.0, 200.0)


@pytest.fixture
def cube_mesh():
    vertices, faces = synth.box_mesh(SIZE)
    return volume.tetrahedralize(vertices, faces, max_volume=100_000.0)


def _base_and_top(nodes: np.ndarray, tolerance: float = 1e-6) -> dict[str, np.ndarray]:
    z = nodes[:, 2]
    return {
        "BASE": np.flatnonzero(z <= z.min() + tolerance),
        "TOP": np.flatnonzero(z >= z.max() - tolerance),
    }


def test_inp_is_readable_by_meshio(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=_base_and_top(nodes),
        material=Material(),
    )

    mesh = meshio.read(path)
    assert len(mesh.points) == len(nodes)
    assert sum(len(block.data) for block in mesh.cells if block.type == "tetra") == len(tets)


def test_inp_contains_sets_material_and_gravity_step(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    sets = _base_and_top(nodes)
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=sets,
        material=Material(),
        print_nsets=("TOP",),
    )
    text = path.read_text(encoding="ascii")

    assert "*ELEMENT, TYPE=C3D4, ELSET=ALL_WALL" in text
    assert "*NSET, NSET=BASE" in text
    assert "*NSET, NSET=TOP" in text
    assert "*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=MURATURA" in text
    assert "1500.0, 0.2" in text
    assert "1.8e-09" in text
    assert "BASE, 1, 3" in text
    assert "ALL_WALL, GRAV, 9810.0, 0.0, 0.0, -1.0" in text
    assert "*NODE PRINT, NSET=TOP" in text


def test_node_and_element_indices_are_one_based(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    path = tmp_path / "model.inp"

    abaqus.write_inp(
        path, nodes, tets,
        node_sets=_base_and_top(nodes),
        material=Material(),
    )
    lines = path.read_text(encoding="ascii").splitlines()

    node_start = lines.index("*NODE") + 1
    assert lines[node_start].split(",")[0].strip() == "1"

    element_header = next(i for i, line in enumerate(lines) if line.startswith("*ELEMENT"))
    first_element = [int(value) for value in lines[element_header + 1].split(",")]
    assert first_element[0] == 1
    assert min(first_element[1:]) >= 1
    assert max(first_element[1:]) <= len(nodes)


def test_base_set_holds_only_the_lowest_nodes(tmp_path, cube_mesh):
    nodes, tets = cube_mesh
    sets = _base_and_top(nodes)

    assert len(sets["BASE"]) >= 4
    assert np.allclose(nodes[sets["BASE"], 2], nodes[:, 2].min())
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

```bash
uv run pytest tests/test_abaqus.py -v
```

Atteso: FAIL con `ImportError: cannot import name 'abaqus' from 'meshrec'`.

- [ ] **Step 3: Implementare `src/meshrec/config.py`**

```python
"""Modelli di configurazione: unico luogo dove un parametro ha un valore predefinito.

Sistema di unita di lavoro: mm, N, MPa, tonnellata, secondo.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

GRAVITY_MM_S2: float = 9810.0


class Material(BaseModel):
    """Materiale elastico isotropo. Valori indicativi per muratura."""

    name: str = "MURATURA"
    young: float = Field(default=1500.0, gt=0.0, description="modulo elastico [MPa]")
    poisson: float = Field(default=0.2, ge=0.0, lt=0.5, description="coefficiente di Poisson")
    density: float = Field(default=1.8e-9, gt=0.0, description="densita [t/mm^3]")
```

- [ ] **Step 4: Implementare `src/meshrec/abaqus.py`**

```python
"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from meshrec.config import GRAVITY_MM_S2, Material

_SET_ITEMS_PER_LINE = 8


def _set_lines(indices: np.ndarray) -> list[str]:
    """Indici 0-based in righe di numeri 1-based, otto per riga."""
    one_based = np.asarray(indices, dtype=np.int64) + 1
    return [
        ", ".join(str(value) for value in one_based[start : start + _SET_ITEMS_PER_LINE])
        for start in range(0, len(one_based), _SET_ITEMS_PER_LINE)
    ]


def write_inp(
    path: Path,
    nodes: np.ndarray,
    tets: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    fixed_nset: str = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    step_name: str = "GRAVITA",
) -> None:
    """Scrive un modello pronto all'analisi statica sotto peso proprio."""
    if fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")

    nodes = np.asarray(nodes, dtype=np.float64)
    tets = np.asarray(tets, dtype=np.int64)

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE=C3D4, ELSET={elset}")
    lines += [
        f"{index + 1}, {a + 1}, {b + 1}, {c + 1}, {d + 1}"
        for index, (a, b, c, d) in enumerate(tets)
    ]

    for name, indices in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(indices)

    lines += [
        f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC",
        f"{material.young}, {material.poisson}",
        "*DENSITY",
        f"{material.density:.9g}",
        "*BOUNDARY",
        f"{fixed_nset}, 1, 3",
        f"*STEP, NAME={step_name}",
        "*STATIC",
        "*DLOAD",
        f"{elset}, GRAV, {gravity}, 0.0, 0.0, -1.0",
    ]

    for name in print_nsets:
        lines += [f"*NODE PRINT, NSET={name}", "U"]

    lines += ["*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP", ""]

    Path(path).write_text("\n".join(lines), encoding="ascii")
```

- [ ] **Step 5: Eseguire i test e verificare che passino**

```bash
uv run pytest tests/test_abaqus.py -v
```

Atteso: 4 test PASS.

Se `meshio.read` solleva un errore su una parola chiave che non riconosce (`*SOLID SECTION`, `*STEP`), è un limite del lettore, non del deck: annotarlo nel documento di Fase 0 e sostituire quell'unico test con la lettura del solo blocco di nodi ed elementi, verificando i conteggi sul testo. Gli altri tre test restano invariati.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/src/meshrec/config.py meshrec/src/meshrec/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat: scrittura del deck Abaqus con set, materiale, vincoli e step"
```

---

### Task 5: Verifica di fattibilità — PyMeshFix

**Files:**
- Create: `meshrec/tests/feasibility/test_pymeshfix.py`
- Modify: `meshrec/pyproject.toml` (gruppo opzionale `feasibility`)

**Interfaces:**
- Consumes: `meshrec.synth.box_mesh`, `meshrec.synth.punch_holes`, `meshrec.quality.is_watertight`, `meshrec.quality.mesh_volume` (Task 2)
- Produces: esito registrato per la riparazione garantita della superficie

- [ ] **Step 1: Installare la dipendenza in valutazione**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv add --optional feasibility pymeshfix
```

Se l'installazione fallisce, non insistere: annotare il messaggio d'errore e proseguire dal Passo 3 (il test resterà saltato ed è comunque un esito valido).

- [ ] **Step 2: Creare la cartella `meshrec/tests/feasibility/`**

Senza `__init__.py`: i moduli di supporto verranno importati per nome semplice.

- [ ] **Step 3: Scrivere la verifica**

Creare `meshrec/tests/feasibility/test_pymeshfix.py`:

```python
"""Fase 0 — PyMeshFix riesce a chiudere una superficie forata?"""

import numpy as np
import pytest

from meshrec import quality, synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_pymeshfix_closes_a_punched_box():
    pymeshfix = pytest.importorskip("pymeshfix")

    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))
    assert not quality.is_watertight(damaged)

    fixer = pymeshfix.MeshFix(np.asarray(vertices), np.asarray(damaged, dtype=np.int32))
    fixer.repair()

    repaired_vertices = np.asarray(fixer.v, dtype=np.float64)
    repaired_faces = np.asarray(fixer.f, dtype=np.int64)

    assert len(repaired_faces) > 0
    assert quality.is_watertight(repaired_faces)
    assert abs(quality.mesh_volume(repaired_vertices, repaired_faces)) == pytest.approx(
        EXACT_VOLUME, rel=0.05
    )
```

- [ ] **Step 4: Eseguire la verifica e annotare l'esito**

```bash
uv run pytest tests/feasibility/test_pymeshfix.py -v -m feasibility
```

Tre esiti possibili, tutti validi come risultato di fase:
- PASS → PyMeshFix adottato per la riparazione garantita.
- SKIP (pacchetto non installabile) → ripiego: riparazione con Open3D più chiusura fori propria.
- FAIL → annotare l'errore; se il volume ricostruito è fuori tolleranza, ripetere con `remove=(0,)` per capire se il limite sia sui fori multipli.

Annotare versione del pacchetto (`uv pip show pymeshfix`) ed esito: serviranno al Task 10.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/tests/feasibility
git commit -m "test: verifica di fattibilita di PyMeshFix"
```

---

### Task 6: Verifica di fattibilità — fTetWild (wildmeshing)

**Files:**
- Create: `meshrec/tests/feasibility/test_wildmeshing.py`
- Modify: `meshrec/pyproject.toml` (gruppo opzionale `feasibility`)

**Interfaces:**
- Consumes: `meshrec.synth.box_mesh`, `meshrec.synth.punch_holes` (Task 2), `meshrec.quality.tet_volumes` (Task 3)
- Produces: esito registrato sulla tetraedrizzazione robusta di ingressi difettosi

- [ ] **Step 1: Installare la dipendenza in valutazione**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv add --optional feasibility wildmeshing
```

Se non esiste una wheel per Windows con Python 3.12 l'installazione fallisce: annotare il messaggio esatto e proseguire dal Passo 2. È l'esito che decide se il vincolo "superficie chiusa prima della tetraedrizzazione" resta o cade.

- [ ] **Step 2: Scrivere la verifica**

Creare `meshrec/tests/feasibility/test_wildmeshing.py`:

```python
"""Fase 0 — fTetWild tetraedrizza una superficie difettosa senza ripararla prima?"""

import numpy as np
import pytest

from meshrec import quality, synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_ftetwild_meshes_a_punched_box():
    wildmeshing = pytest.importorskip("wildmeshing")

    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    tetrahedralizer = wildmeshing.Tetrahedralizer(stop_quality=10)
    tetrahedralizer.set_mesh(
        np.asarray(vertices, dtype=np.float64),
        np.asarray(damaged, dtype=np.int32),
    )
    tetrahedralizer.tetrahedralize()

    result = tetrahedralizer.get_tet_mesh()
    nodes = np.asarray(result[0], dtype=np.float64)
    tets = np.asarray(result[1], dtype=np.int64)

    assert len(tets) > 10
    total = np.abs(quality.tet_volumes(nodes, tets)).sum()
    assert total == pytest.approx(EXACT_VOLUME, rel=0.10)
```

- [ ] **Step 3: Eseguire la verifica e annotare l'esito**

```bash
uv run pytest tests/feasibility/test_wildmeshing.py -v -m feasibility
```

- PASS → la riparazione diventa opzionale e la guardia "superficie chiusa" sparisce dalla Fase 1.
- SKIP o errore di installazione → si resta su TetGen più PyMeshFix, con la guardia mantenuta.
- Errore di firma su `get_tet_mesh()` o `set_mesh()` → adattare lo spacchettamento alla firma effettiva della versione installata (`help(wildmeshing.Tetrahedralizer)`) e riprovare una volta sola; se la API differisce in modo sostanziale, trattarlo come esito negativo.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/tests/feasibility/test_wildmeshing.py
git commit -m "test: verifica di fattibilita di fTetWild"
```

---

### Task 7: Verifica di fattibilità — PyMeshLab

**Files:**
- Create: `meshrec/tests/feasibility/test_pymeshlab.py`
- Modify: `meshrec/pyproject.toml` (gruppo opzionale `feasibility`)

**Interfaces:**
- Consumes: `meshrec.synth.box_mesh` (Task 2)
- Produces: esito registrato su remeshing isotropo e distanza di Hausdorff

- [ ] **Step 1: Installare la dipendenza in valutazione**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv add --optional feasibility pymeshlab
```

- [ ] **Step 2: Scrivere la verifica**

Creare `meshrec/tests/feasibility/test_pymeshlab.py`:

```python
"""Fase 0 — PyMeshLab offre remeshing isotropo e distanza di Hausdorff?"""

import numpy as np
import pytest

from meshrec import synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)


def _percentage(pymeshlab, value: float):
    """Il tipo percentuale ha cambiato nome fra le versioni di PyMeshLab."""
    for attribute in ("PercentageValue", "Percentage"):
        if hasattr(pymeshlab, attribute):
            return getattr(pymeshlab, attribute)(value)
    raise AssertionError("nessun tipo percentuale trovato in pymeshlab")


def _apply_first_available(mesh_set, names: tuple[str, ...], **kwargs):
    """Applica il primo filtro esistente fra i nomi dati."""
    available = set(mesh_set.filter_list())
    for name in names:
        if name in available:
            return mesh_set.apply_filter(name, **kwargs)
    raise AssertionError(f"nessuno dei filtri {names} e disponibile")


def test_isotropic_remeshing_increases_triangle_regularity():
    pymeshlab = pytest.importorskip("pymeshlab")

    vertices, faces = synth.box_mesh(SIZE)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "box")

    before = mesh_set.current_mesh().face_number()
    _apply_first_available(
        mesh_set,
        ("meshing_isotropic_explicit_remeshing", "remeshing_isotropic_explicit_remeshing"),
        targetlen=_percentage(pymeshlab, 5.0),
    )
    after = mesh_set.current_mesh().face_number()

    assert after > before  # 12 triangoli grossolani diventano molti triangoli regolari


def test_hausdorff_distance_between_a_mesh_and_itself_is_zero():
    pymeshlab = pytest.importorskip("pymeshlab")

    vertices, faces = synth.box_mesh(SIZE)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "a")
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "b")

    result = _apply_first_available(
        mesh_set,
        ("get_hausdorff_distance", "hausdorff_distance"),
        sampledmesh=0,
        targetmesh=1,
    )

    assert result["max"] == pytest.approx(0.0, abs=1e-6)
```

- [ ] **Step 3: Eseguire la verifica e annotare l'esito**

```bash
uv run pytest tests/feasibility/test_pymeshlab.py -v -m feasibility
```

- PASS → PyMeshLab adottato per remeshing isotropo ed errore geometrico.
- SKIP o FAIL → ripiego: decimazione quadric di Open3D e distanza punto-superficie calcolata con KD-tree di SciPy.

Annotare nel documento di fase i **nomi effettivi** dei filtri trovati: serviranno alla Fase 1.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/tests/feasibility/test_pymeshlab.py
git commit -m "test: verifica di fattibilita di PyMeshLab"
```

---

### Task 8: Verifica di fattibilità — Gmsh come ottimizzatore di qualità

**Files:**
- Create: `meshrec/tests/feasibility/test_gmsh.py`
- Modify: `meshrec/pyproject.toml` (gruppo opzionale `feasibility`)

**Interfaces:**
- Consumes: `meshrec.synth.box_mesh` (Task 2)
- Produces: esito registrato sul miglioramento della qualità degli elementi

- [ ] **Step 1: Installare la dipendenza in valutazione**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv add --optional feasibility gmsh
```

- [ ] **Step 2: Scrivere la verifica**

Creare `meshrec/tests/feasibility/test_gmsh.py`:

```python
"""Fase 0 — Gmsh genera e migliora una mesh tetraedrica partendo da una STL?"""

import meshio
import numpy as np
import pytest

from meshrec import synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)


def _write_stl(path) -> None:
    vertices, faces = synth.box_mesh(SIZE)
    meshio.write_points_cells(path, np.asarray(vertices), [("triangle", np.asarray(faces))])


def test_gmsh_meshes_and_optimizes_a_box(tmp_path):
    gmsh = pytest.importorskip("gmsh")

    stl_path = tmp_path / "box.stl"
    _write_stl(str(stl_path))

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

        gmsh.model.mesh.generate(3)
        _, tags, _ = gmsh.model.mesh.getElements(3)
        before = np.asarray(gmsh.model.mesh.getElementQualities(tags[0]))

        gmsh.model.mesh.optimize("Netgen")
        _, tags_after, _ = gmsh.model.mesh.getElements(3)
        after = np.asarray(gmsh.model.mesh.getElementQualities(tags_after[0]))

        assert len(before) > 10
        assert before.min() > 0.0
        assert after.min() >= before.min() - 1e-9
    finally:
        gmsh.finalize()
```

- [ ] **Step 3: Eseguire la verifica e annotare l'esito**

```bash
uv run pytest tests/feasibility/test_gmsh.py -v -m feasibility
```

- PASS → Gmsh disponibile come ottimizzatore post-mesh in Fase 1; annotare il guadagno di qualità minima osservato.
- SKIP o FAIL → nessuna ottimizzazione post-mesh: la qualità si governa con i parametri di TetGen.
- Se `optimize("Netgen")` non è disponibile nella build installata, riprovare una volta con `gmsh.model.mesh.optimize("")` e annotare quale funziona.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/tests/feasibility/test_gmsh.py
git commit -m "test: verifica di fattibilita di Gmsh"
```

---

### Task 9: Verifica di fattibilità — CalculiX come solutore in batch

**Files:**
- Create: `meshrec/tests/feasibility/ccx_utils.py`
- Create: `meshrec/tests/feasibility/test_calculix.py`

**Interfaces:**
- Consumes: `meshrec.abaqus.write_inp`, `meshrec.config.Material` (Task 4), `meshrec.volume.tetrahedralize` (Task 3), `meshrec.synth.box_mesh` (Task 2)
- Produces:
  - `ccx_utils.read_dat_displacements(path: Path) -> dict[int, tuple[float, float, float]]` (modulo di supporto, importato per nome semplice)
  - esito registrato sulla compatibilità dell'`.inp` generato con CalculiX

- [ ] **Step 1: Verificare la presenza dell'eseguibile**

```bash
where ccx
```

Se non è presente, installarlo: la distribuzione Windows più semplice è quella inclusa in PrePoMax, oppure i binari `ccx` di bConverged. L'eseguibile va reso raggiungibile dal PATH. Se non lo si ottiene in tempi brevi, non insistere: il test resterà saltato ed è un esito valido, con ripiego su Abaqus.

- [ ] **Step 2: Scrivere il lettore del file dei risultati**

Creare `meshrec/tests/feasibility/ccx_utils.py`:

```python
"""Lettura minima del file .dat prodotto da CalculiX."""

from __future__ import annotations

from pathlib import Path


def read_dat_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    """Spostamenti nodali dell'ultimo blocco 'displacements' del file .dat.

    Le righe utili hanno quattro campi: numero di nodo e tre componenti.
    """
    displacements: dict[int, tuple[float, float, float]] = {}
    for line in Path(path).read_text(encoding="ascii", errors="ignore").splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        try:
            node = int(fields[0])
            components = tuple(float(value) for value in fields[1:])
        except ValueError:
            continue
        displacements[node] = components  # type: ignore[assignment]
    return displacements
```

- [ ] **Step 3: Scrivere la verifica**

Creare `meshrec/tests/feasibility/test_calculix.py`:

```python
"""Fase 0 — CalculiX accetta il nostro .inp e da un risultato corretto?

Caso di prova: colonna a base quadrata incastrata al piede sotto peso proprio.
Accorciamento in sommita in forma chiusa: u = rho * g * L^2 / (2 * E).
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec import abaqus, synth, volume
from meshrec.config import GRAVITY_MM_S2, Material
from ccx_utils import read_dat_displacements

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 100.0, 400.0)  # mm


def test_calculix_solves_a_column_under_self_weight(tmp_path):
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    material = Material()
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(vertices, faces, max_volume=20_000.0)

    z = nodes[:, 2]
    node_sets = {
        "BASE": np.flatnonzero(z <= z.min() + 1e-6),
        "TOP": np.flatnonzero(z >= z.max() - 1e-6),
    }

    abaqus.write_inp(
        tmp_path / "model.inp", nodes, tets,
        node_sets=node_sets,
        material=material,
        print_nsets=("TOP",),
    )

    process = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-2000:] + process.stderr[-2000:]

    displacements = read_dat_displacements(tmp_path / "model.dat")
    assert displacements, "nessuno spostamento letto dal file .dat"

    top_uz = np.array([displacements[node + 1][2] for node in node_sets["TOP"]])
    expected = material.density * GRAVITY_MM_S2 * SIZE[2] ** 2 / (2.0 * material.young)

    assert (top_uz < 0.0).all()  # la colonna si accorcia
    assert abs(top_uz.mean()) == pytest.approx(expected, rel=0.20)
```

- [ ] **Step 4: Eseguire la verifica e annotare l'esito**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv run pytest tests/feasibility/test_calculix.py -v -m feasibility
```

- PASS → il batch di Fase 5 può girare senza licenza Abaqus; annotare la versione di CalculiX e lo scarto percentuale osservato rispetto alla soluzione analitica.
- SKIP → eseguibile assente: ripiego su Abaqus con un numero ridotto di esecuzioni.
- FAIL con errore di sintassi del deck → annotare la riga rifiutata: è un difetto del nostro writer da correggere in Fase 1, e va segnalato come tale.

Se il test fallisce perché `model.dat` non viene prodotto, verificare che `print_nsets=("TOP",)` sia effettivamente presente nel deck: senza `*NODE PRINT` CalculiX non scrive il file `.dat`.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/tests/feasibility/ccx_utils.py meshrec/tests/feasibility/test_calculix.py
git commit -m "test: verifica di fattibilita di CalculiX come solutore in batch"
```

---

### Task 10: Documento degli esiti e chiusura della fase

**Files:**
- Create: `meshrec/docs/fase-0-esiti.md`
- Create: `meshrec/README.md`
- Modify: `meshrec/pyproject.toml` (fissaggio delle dipendenze confermate)

**Interfaces:**
- Consumes: esiti dei Task 5-9
- Produces: decisioni tecniche vincolanti per la Fase 1

- [ ] **Step 1: Eseguire l'intera suite**

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv run pytest -v
uv run pytest -v -m feasibility
```

Atteso: la prima esecuzione passa interamente (test del core); la seconda riporta l'esito di ciascuna verifica, con eventuali salti.

- [ ] **Step 2: Scrivere `meshrec/docs/fase-0-esiti.md`**

Compilare questo documento con i risultati effettivi osservati, sostituendo ogni cella con l'esito reale e la versione installata:

```markdown
# Fase 0 — Esiti delle verifiche di fattibilità

- **Data di esecuzione:** <data>
- **Ambiente:** Windows 11, Python 3.12.x, uv <versione>

## Dipendenze obbligatorie

| Pacchetto | Versione | Esito | Note |
|---|---|---|---|
| numpy | | | |
| scipy | | | |
| open3d | | | |
| tetgen | | | |
| meshio | | | |
| pydantic | | | |

## Dipendenze in valutazione

| Pacchetto | Versione | Esito | Decisione |
|---|---|---|---|
| pymeshfix | | PASS / SKIP / FAIL | adottato oppure ripiego su Open3D |
| wildmeshing (fTetWild) | | PASS / SKIP / FAIL | adottato oppure TetGen + PyMeshFix con guardia di chiusura |
| pymeshlab | | PASS / SKIP / FAIL | adottato oppure decimazione Open3D + KD-tree SciPy |
| gmsh | | PASS / SKIP / FAIL | ottimizzatore post-mesh oppure solo parametri TetGen |
| CalculiX | | PASS / SKIP / FAIL | batch libero oppure solo Abaqus |

## Nomi di API osservati

Annotare qui i nomi effettivi dei filtri PyMeshLab e le firme dei metodi
wildmeshing riscontrati, perché differiscono fra versioni.

## Conseguenze sulla Fase 1

- Riparazione della superficie: <strumento scelto>
- Tetraedrizzazione: <strumento scelto>, guardia di chiusura <mantenuta / rimossa>
- Errore geometrico: <strumento scelto>
- Ottimizzazione della qualità: <strumento scelto / nessuna>
- Solutore per il batch: <strumento scelto>
```

- [ ] **Step 3: Scrivere `meshrec/README.md`**

```markdown
# MeshRec

Pipeline riproducibile da nuvola di punti a modello FEM di muratura, sviluppata
come strumento della tesi. Sostituisce `MeshReconstructorPro`.

Spec: `../docs/superpowers/specs/2026-08-12-meshreconstructor-architettura-design.md`

## Requisiti

Python 3.12 e [uv](https://docs.astral.sh/uv/).

## Avvio

```bash
uv sync
uv run pytest                 # test del nucleo
uv run pytest -m feasibility  # verifiche sulle dipendenze esterne (Fase 0)
```

## Unità

Tutto il codice lavora in **mm, N, MPa, tonnellata, secondo**. Le densità sono
in t/mm³ (1800 kg/m³ = 1.8e-9) e la gravità vale 9810 mm/s².

## Stato

Fase 0 completata: scheletro, primitive geometriche, scrittura del deck Abaqus
e verifiche di fattibilità. Esiti in `docs/fase-0-esiti.md`.
```

- [ ] **Step 4: Fissare le dipendenze confermate**

In `meshrec/pyproject.toml`, spostare fra le `dependencies` obbligatorie i soli pacchetti in valutazione che hanno dato PASS **e** che la Fase 1 userà; lasciare gli altri nel gruppo `feasibility` o rimuoverli. Poi:

```bash
cd "C:/Users/mario/GitHub/Tesi/meshrec"
uv sync
uv run pytest -v
```

Atteso: la suite del nucleo continua a passare.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/mario/GitHub/Tesi"
git add meshrec/docs/fase-0-esiti.md meshrec/README.md meshrec/pyproject.toml meshrec/uv.lock
git commit -m "docs: esiti delle verifiche di Fase 0 e decisioni per la Fase 1"
```

- [ ] **Step 6: Criteri di accettazione della fase**

Verificare tutti i punti prima di dichiarare chiusa la Fase 0:

- `uv sync` completa su ambiente pulito.
- `uv run pytest` passa interamente.
- Ogni dipendenza in valutazione ha un esito registrato e una decisione scritta.
- `docs/fase-0-esiti.md` non contiene celle vuote né segnaposto.
- Le dipendenze obbligatorie della Fase 1 sono fissate in `pyproject.toml`.
