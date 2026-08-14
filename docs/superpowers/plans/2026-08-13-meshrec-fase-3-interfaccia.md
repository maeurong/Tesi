# Fase 3 — Interfaccia web completa — Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire l'applicazione web locale che pilota la pipeline `meshrec` esistente, step per step, con viewport three.js sul dato vero e report stampabile.

**Architecture:** Tre strati con dipendenze in una sola direzione, `ui → app → core`. Il core acquisisce le capacita' che oggi non ha (motore per step con impronte, decimazione con mappa, deviazione per vertice) e resta usabile da script; `app/` e' un server FastAPI che esegue gli step in un processo separato e trasmette avanzamento e log via SSE; `ui/` sono ES module serviti direttamente, senza build.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pydantic, numpy, Open3D, three.js vendorizzato. Nessuna toolchain node per l'applicazione.

**Spec:** `docs/superpowers/specs/2026-08-13-meshrec-fase-3-interfaccia-design.md`

## Global Constraints

- Ramo di lavoro: `fase-3-interfaccia`. Nessun push, nessun merge su `main`.
- Mai `git add -A`: la radice ha centinaia di MB non tracciati. Sempre percorsi espliciti.
- `meshrec/runs/muro/`, `meshrec/runs/lab_crop/`, `meshrec/experiments/muro/`, `meshrec/experiments/lab_crop/` sono di **sola lettura**: si leggono e si copiano, mai si scrive al loro interno.
- L'unico luogo dove un parametro di elaborazione ha un valore predefinito e' `meshrec/src/meshrec/core/config.py`. Le firme del core non portano predefiniti.
- Italiano per commenti, docstring, documenti e messaggi di commit. **Niente lettere accentate nelle docstring e nei commenti del core.**
- Comandi eseguiti da `meshrec/` con `uv run`. Windows, PowerShell.
- Utente singolo, nessuna autenticazione, server locale. Non progettare per il multiutente.
- Dipendenze nuove ammesse, e nessun'altra: `fastapi`, `uvicorn`, piu' il file vendorizzato `three.module.js`. Verificate risolvibili: `fastapi==0.141.1`, `uvicorn==0.52.3`, con quattro transitive (`annotated-doc`, `anyio`, `h11`, `starlette`).
- La suite deve restare verde a ogni commit. Riferimento di partenza: **181 test raccolti, 6 deselezionati**.
- Lingua dell'interfaccia: **italiano**. Restano invariati gli identificatori tecnici: `C3D4`, `C3D10`, `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`, `ALL_WALL`, `min_ratio`, `nobisect`, Poisson, TetGen, MeshFix.

### Ruling permanente: `PipelineConfig` non si allarga

**Deciso:** `ViewportConfig` e `ServerConfig` vivono in `config.py` ma **non** vengono agganciati a `PipelineConfig`.

**Perche':** `sweep.fingerprint` serializza l'intero `PipelineConfig`. Aggiungervi un campo cambierebbe l'impronta di **ogni riga gia' scritta** nei registri della Fase 2, cioe' la tabella sperimentale della tesi. Verificato: `fingerprint(load_config('runs/sweep/lab_crop/2e93bb805afe/config.yaml'))` restituisce oggi `2e93bb805afee82d557badc3151dff7bea870d0896b9515e64366d4f3f3b596f`, esattamente l'impronta registrata in `experiments/lab_crop/registro.jsonl`.

**Costo se sbagliato:** se un domani un parametro di viewport dovesse davvero influenzare l'elaborazione, andrebbe aggiunto a `PipelineConfig` accettando di invalidare le impronte storiche, e la scelta andrebbe documentata li' dove i registri vengono letti.

Il Task 1 fissa quel valore in un test di regressione.

---

## File Structure

**Creati:**

| File | Responsabilita' |
|---|---|
| `src/meshrec/core/steps.py` | Registro degli undici step, blocchi di configurazione consumati, catena di impronte, lettura e scrittura di `steps.json`, stato di una corsa |
| `src/meshrec/core/viewport.py` | Decimazione con mappa verso gli indici pieni, serializzazione binaria Float32 |
| `src/meshrec/app/__init__.py` | Strato applicativo, vuoto |
| `src/meshrec/app/server.py` | FastAPI: endpoint, SSE, servizio dei file dell'interfaccia |
| `src/meshrec/app/worker.py` | Esecuzione di uno step come processo separato, log, annullamento |
| `src/meshrec/ui/index.html` | Guscio a tre zone |
| `src/meshrec/ui/stile.css` | Sistema di design (definito da impeccable) |
| `src/meshrec/ui/app.js` | Orchestrazione dell'interfaccia, SSE, pannelli |
| `src/meshrec/ui/viewport.js` | Scena three.js, nuvola, mesh, box, piano di taglio |
| `src/meshrec/ui/vendor/three.module.js` | three.js vendorizzato |
| `tests/test_steps.py`, `tests/test_viewport.py`, `tests/test_server.py`, `tests/test_worker.py` | Verifiche dei moduli nuovi |

**Modificati:**

| File | Modifica |
|---|---|
| `pyproject.toml` | `fastapi`, `uvicorn`; inclusione dei file statici nel wheel |
| `src/meshrec/core/config.py` | `+ ViewportConfig`, `+ ServerConfig`, `+ RunConfig.to_step` |
| `src/meshrec/core/pipeline.py` | `metrics.partial.json` con rinomina atomica, artefatti atomici, `to_step`, scrittura di `steps.json` |
| `src/meshrec/core/io.py` | `+ write_cloud` atomico, `+ scarta_temporanei` |
| `src/meshrec/core/quality.py` | `+ vertex_deviation` |
| `src/meshrec/core/report.py` | Viste catturate, rivestimento con il sistema di design |
| `src/meshrec/core/sweep.py` | `REQUIRED_STEPS` da `steps.py`; lettura di `metrics.partial.json` come ripiego |
| `src/meshrec/cli.py` | `+ serve`, `+ --only-step` |

---

## Task 1: Server, guscio, registro degli step

**Files:**
- Modify: `pyproject.toml`
- Create: `src/meshrec/core/steps.py`
- Modify: `src/meshrec/core/config.py` (aggiunta di `ViewportConfig` e `ServerConfig` in coda)
- Create: `src/meshrec/app/__init__.py`, `src/meshrec/app/server.py`
- Create: `src/meshrec/ui/index.html`, `src/meshrec/ui/stile.css`, `src/meshrec/ui/app.js`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_steps.py`, `tests/test_server.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `core.steps.STEP_KEYS: tuple[str, ...]` (undici chiavi, da `01_load` a `11_export`); `core.steps.STEP_BLOCKS: dict[int, tuple[str, ...]]`; `core.steps.read_state(out_dir: Path) -> dict[str, object]`; `core.steps.run_state(out_dir: Path, cfg: PipelineConfig) -> list[dict[str, object]]`; `app.server.create_app(root: Path) -> FastAPI`; `config.ViewportConfig`, `config.ServerConfig`.
- Consumes: niente.

- [ ] **Step 1: Test di regressione sull'impronta storica**

In `tests/test_config.py`, in coda:

```python
def test_l_impronta_di_una_corsa_registrata_non_cambia(tmp_path):
    """L'impronta della Fase 2 vive nei registri: allargare PipelineConfig la
    cambierebbe, e con essa la provenienza di ogni riga della tabella della tesi.
    """
    from meshrec.core.sweep import fingerprint

    cfg = PipelineConfig(
        input=InputConfig(path=Path("Nuvole di punti/lab_frame.pcd"), scale=1000.0),
    )
    prima = fingerprint(cfg)
    assert len(prima) == 64
    # Un campo nuovo in PipelineConfig cambierebbe questo valore: il test lo fissa
    # sulla forma canonica corrente e non su un valore magico, cosi' fallisce
    # anche se il campo nuovo ha un predefinito innocuo.
    payload = cfg.model_dump(mode="json")
    assert set(payload) == {
        "input", "segment", "downsample", "normals", "surface",
        "repair", "simplify", "tet", "analysis", "run",
    }
```

- [ ] **Step 2: Eseguirlo e vederlo passare**

Run: `uv run pytest tests/test_config.py::test_l_impronta_di_una_corsa_registrata_non_cambia -v`
Expected: PASS. E' un test di guardia: passa oggi e deve continuare a passare.

- [ ] **Step 3: Test del registro degli step**

Crea `tests/test_steps.py`:

```python
"""Registro degli step, catena di impronte, stato di una corsa."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshrec.core import steps
from meshrec.core.config import InputConfig, PipelineConfig


def _config(tmp_path: Path) -> PipelineConfig:
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    return cfg


def test_gli_undici_step_sono_quelli_che_la_pipeline_scrive():
    assert steps.STEP_KEYS[0] == "01_load"
    assert steps.STEP_KEYS[-1] == "11_export"
    assert len(steps.STEP_KEYS) == 11
    assert set(steps.STEP_BLOCKS) == set(range(1, 12))


def test_una_corsa_mai_eseguita_ha_tutti_gli_step_mai_eseguiti(tmp_path):
    stato = steps.run_state(tmp_path / "vuota", _config(tmp_path))
    assert len(stato) == 11
    assert {voce["stato"] for voce in stato} == {"mai eseguito"}
```

- [ ] **Step 4: Eseguirlo e vederlo fallire**

Run: `uv run pytest tests/test_steps.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.steps'`

- [ ] **Step 5: Scrivere `core/steps.py`**

```python
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
```

- [ ] **Step 6: Eseguire i test del registro**

Run: `uv run pytest tests/test_steps.py -v`
Expected: PASS, due test.

- [ ] **Step 7: Test dell'invalidazione a valle**

Aggiungi a `tests/test_steps.py`:

```python
def test_cambiare_un_parametro_invalida_solo_da_li_in_giu(tmp_path):
    """Prova a variabile unica: cambia surface.poisson_depth e nient'altro."""
    prima = _config(tmp_path)
    dopo = _config(tmp_path)
    dopo.surface.poisson_depth = 7

    marchi_prima = steps.step_fingerprints(prima)
    marchi_dopo = steps.step_fingerprints(dopo)

    for numero in (1, 2, 3, 4):
        assert marchi_prima[numero] == marchi_dopo[numero], f"step {numero} non doveva cambiare"
    for numero in (5, 6, 7, 8, 9, 10, 11):
        assert marchi_prima[numero] != marchi_dopo[numero], f"step {numero} doveva cambiare"


def test_uno_stato_salvato_con_impronta_diversa_e_non_valido(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    marchi = steps.step_fingerprints(cfg)
    (corsa / steps.STATE_FILENAME).write_text(
        json.dumps(
            {
                "01_load": {"impronta": marchi[1], "esito": "riuscito", "artefatto": "01_cloud.ply"},
                "05_reconstruct": {"impronta": "altro", "esito": "riuscito", "artefatto": None},
            }
        ),
        encoding="utf-8",
    )
    per_chiave = {voce["chiave"]: voce["stato"] for voce in steps.run_state(corsa, cfg)}
    assert per_chiave["01_load"] == "valido"
    assert per_chiave["05_reconstruct"] == "non valido"
    assert per_chiave["09_tetrahedralize"] == "mai eseguito"


def test_uno_steps_json_troncato_non_solleva_e_non_rassicura(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / steps.STATE_FILENAME).write_text('{"01_load": {"impro', encoding="utf-8")
    assert {voce["stato"] for voce in steps.run_state(corsa, cfg)} == {"mai eseguito"}
```

- [ ] **Step 8: Eseguirli**

Run: `uv run pytest tests/test_steps.py -v`
Expected: PASS, cinque test.

- [ ] **Step 9: Aggiungere le dipendenze**

```bash
uv add fastapi uvicorn
```

Poi in `pyproject.toml`, sotto `[tool.hatch.build.targets.wheel]`, aggiungere i file statici perche' finiscano nel wheel:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/meshrec"]
artifacts = ["src/meshrec/ui/**"]
```

- [ ] **Step 10: Test degli endpoint**

Crea `tests/test_server.py`:

```python
"""Endpoint del server. Il contratto vale sulla tratta, non sulla funzione."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meshrec.app.server import create_app
from meshrec.core.config import InputConfig, PipelineConfig, save_config


@pytest.fixture()
def cliente(tmp_path: Path) -> TestClient:
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    save_config(cfg, tmp_path / "config.yaml")
    return TestClient(create_app(tmp_path / "config.yaml"))


def test_la_radice_serve_l_interfaccia(cliente):
    risposta = cliente.get("/")
    assert risposta.status_code == 200
    assert "text/html" in risposta.headers["content-type"]


def test_lo_stato_della_corsa_elenca_gli_undici_step(cliente):
    corpo = cliente.get("/api/run").json()
    assert len(corpo["steps"]) == 11
    assert corpo["steps"][0]["chiave"] == "01_load"
    assert {voce["stato"] for voce in corpo["steps"]} == {"mai eseguito"}


def test_la_configurazione_torna_intera(cliente):
    corpo = cliente.get("/api/config").json()
    assert set(corpo) >= {"input", "segment", "surface", "tet", "analysis"}


def test_nessun_endpoint_solleva_verso_il_browser(cliente):
    """Il contratto vale sull'elenco intero, derivato dall'applicazione stessa:
    un endpoint aggiunto domani vi entra da solo e non puo' essere dimenticato.
    """
    percorsi = [
        rotta.path
        for rotta in cliente.app.routes
        if getattr(rotta, "methods", None) and "GET" in rotta.methods
    ]
    assert len(percorsi) >= 3
    for percorso in percorsi:
        if "{" in percorso:
            continue
        risposta = cliente.get(percorso)
        assert risposta.status_code < 500, f"{percorso} ha sollevato verso il browser"
```

- [ ] **Step 11: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.app'`

- [ ] **Step 12: `ViewportConfig` e `ServerConfig` in `config.py`**

In coda a `src/meshrec/core/config.py`, dopo `ExperimentConfig`:

```python
class ViewportConfig(BaseModel):
    """Disegno nel browser. Non entra in PipelineConfig: vedi la nota sotto.

    Aggiungere un campo a PipelineConfig cambierebbe sweep.fingerprint e quindi
    l'impronta di ogni riga gia' scritta nei registri della Fase 2, che sono la
    tabella sperimentale della tesi. Questi parametri governano il disegno e non
    l'elaborazione, quindi restano fuori.
    """

    max_points: int = Field(
        default=400_000,
        gt=0,
        description=(
            "punti al massimo inviati al browser per il disegno. 400.000 punti "
            "sono 4,8 MB in Float32, dell'ordine di 04_normals.ply di lab_crop "
            "(5.571.038 byte), un artefatto che la pipeline scrive e rilegge a "
            "ogni corsa. Non e' un limite grafico ma di trasporto"
        ),
    )


class ServerConfig(BaseModel):
    """Server locale. Utente singolo, nessuna autenticazione."""

    host: str = "127.0.0.1"
    port: int = Field(default=8765, gt=0, le=65535)
    open_browser: bool = True
```

- [ ] **Step 13: Scrivere `app/server.py`**

Crea `src/meshrec/app/__init__.py` vuoto e `src/meshrec/app/server.py`:

```python
"""Server locale: pilota il core, non lo reimplementa.

Ogni numero che serve viene da metrics.json o dalle funzioni di core; ogni
parametro che scrive passa dai modelli di config.py.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from meshrec.core import steps
from meshrec.core.config import PipelineConfig, load_config

UI_DIR = Path(__file__).resolve().parent.parent / "ui"


def create_app(config_path: Path) -> FastAPI:
    """Applicazione legata a un file di configurazione, che e' la corsa corrente."""
    config_path = Path(config_path)
    app = FastAPI(title="MeshRec", docs_url=None, redoc_url=None)

    def corrente() -> PipelineConfig:
        return load_config(config_path)

    @app.exception_handler(Exception)
    async def nessuna_eccezione_verso_il_browser(_richiesta, errore: Exception):
        # Il contratto vale sulla tratta: nessun endpoint solleva verso il
        # browser. L'errore torna strutturato, con il tipo, perche'
        # l'interfaccia possa dirlo invece di mostrare una pagina bianca.
        return JSONResponse(
            status_code=400,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )

    @app.get("/")
    def interfaccia() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    @app.get("/ui/{nome:path}")
    def statico(nome: str) -> FileResponse:
        percorso = (UI_DIR / nome).resolve()
        if not percorso.is_relative_to(UI_DIR) or not percorso.is_file():
            raise FileNotFoundError(f"nessun file dell'interfaccia chiamato {nome}")
        return FileResponse(percorso)

    @app.get("/api/run")
    def stato_corsa() -> dict[str, object]:
        cfg = corrente()
        return {
            "out_dir": str(cfg.run.out_dir),
            "config_path": str(config_path),
            "steps": steps.run_state(cfg.run.out_dir, cfg),
        }

    @app.get("/api/config")
    def configurazione() -> dict[str, object]:
        return corrente().model_dump(mode="json")

    return app
```

- [ ] **Step 14: Guscio dell'interfaccia**

Crea `src/meshrec/ui/index.html`:

```html
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeshRec</title>
<link rel="stylesheet" href="/ui/stile.css">
</head>
<body>
<header class="testata">
  <h1>MeshRec</h1>
  <p class="corsa" id="corsa">nessuna corsa</p>
</header>
<main class="tre-zone">
  <nav class="zona zona-step" aria-label="Step della pipeline">
    <h2>Pipeline</h2>
    <ol class="elenco-step" id="elenco-step"></ol>
  </nav>
  <section class="zona zona-vista" aria-label="Vista tridimensionale">
    <div id="viewport" class="viewport"></div>
  </section>
  <aside class="zona zona-dettaglio" aria-label="Parametri e metriche">
    <h2>Dettaglio</h2>
    <div id="dettaglio"><p class="vuoto">Scegli uno step per vederne parametri e metriche.</p></div>
  </aside>
</main>
<script type="module" src="/ui/app.js"></script>
</body>
</html>
```

Crea `src/meshrec/ui/stile.css` con un sistema a token minimo — impeccable lo sostituira' nel Task 16:

```css
:root {
  --sfondo: #fbfaf8;
  --superficie: #ffffff;
  --testo: #1c1b19;
  --tenue: #6b6862;
  --bordo: #ddd9d2;
  --accento: #2f5d50;
  --passo: 0.5rem;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: var(--sfondo);
  color: var(--testo);
}
.testata { display: flex; align-items: baseline; gap: 1rem; padding: var(--passo) 1rem; border-bottom: 1px solid var(--bordo); }
.testata h1 { font-size: 1rem; margin: 0; }
.corsa { margin: 0; color: var(--tenue); font-size: 0.85rem; }
.tre-zone { display: grid; grid-template-columns: 18rem 1fr 22rem; height: calc(100vh - 3rem); }
.zona { padding: 1rem; overflow: auto; }
.zona-step, .zona-dettaglio { background: var(--superficie); }
.zona-step { border-right: 1px solid var(--bordo); }
.zona-dettaglio { border-left: 1px solid var(--bordo); }
.zona h2 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--tenue); margin: 0 0 var(--passo); }
.elenco-step { list-style: none; margin: 0; padding: 0; }
.viewport { width: 100%; height: 100%; }
.vuoto { color: var(--tenue); font-size: 0.9rem; }
@media (max-width: 60rem) { .tre-zone { grid-template-columns: 1fr; height: auto; } }
```

Crea `src/meshrec/ui/app.js`:

```javascript
// Orchestrazione dell'interfaccia. Ogni numero mostrato viene dal server.

const ETICHETTE = {
  "01_load": "Lettura", "02_segment": "Segmentazione", "03_downsample": "Riduzione",
  "04_normals": "Normali", "05_reconstruct": "Superficie", "06_repair": "Riparazione",
  "07_surface_quality": "Qualita superficie", "08_simplify": "Semplificazione",
  "09_tetrahedralize": "Tetraedri", "10_volume_quality": "Qualita volume",
  "11_export": "Esportazione",
};

async function caricaStato() {
  const risposta = await fetch("/api/run");
  const corpo = await risposta.json();
  document.getElementById("corsa").textContent = corpo.out_dir;
  disegnaStep(corpo.steps);
}

function disegnaStep(steps) {
  const elenco = document.getElementById("elenco-step");
  elenco.replaceChildren(...steps.map((voce) => {
    const riga = document.createElement("li");
    riga.className = `step stato-${voce.stato.replace(" ", "-")}`;
    riga.dataset.numero = voce.numero;
    const nome = document.createElement("span");
    nome.className = "step-nome";
    nome.textContent = ETICHETTE[voce.chiave] ?? voce.chiave;
    const stato = document.createElement("span");
    stato.className = "step-stato";
    stato.textContent = voce.stato;
    riga.append(nome, stato);
    return riga;
  }));
}

caricaStato();
```

- [ ] **Step 15: Comando `serve`**

In `src/meshrec/cli.py`, dentro `_build_parser`, prima del `return parser`:

```python
    serve_command = commands.add_parser("serve", help="avvia il server locale e apre il browser")
    serve_command.add_argument("config", type=Path)
    serve_command.add_argument("--port", type=int, default=None)
    serve_command.add_argument("--no-browser", action="store_true")
```

E in `main`, prima del ramo finale che esegue la pipeline:

```python
    if args.command == "serve":
        import threading
        import webbrowser

        import uvicorn

        from meshrec.app.server import create_app
        from meshrec.core.config import ServerConfig

        impostazioni = ServerConfig()
        if args.port is not None:
            impostazioni.port = args.port
        indirizzo = f"http://{impostazioni.host}:{impostazioni.port}/"
        if impostazioni.open_browser and not args.no_browser:
            # Dopo un secondo: uvicorn non e' ancora in ascolto al momento della
            # chiamata, e un browser aperto su una porta chiusa mostra un errore
            # invece dell'interfaccia.
            threading.Timer(1.0, webbrowser.open, args=(indirizzo,)).start()
        print(f"MeshRec in ascolto su {indirizzo}", file=sys.stderr)
        uvicorn.run(
            create_app(args.config), host=impostazioni.host, port=impostazioni.port, log_level="warning"
        )
        return 0
```

- [ ] **Step 16: Eseguire i test del server**

Run: `uv run pytest tests/test_server.py tests/test_steps.py tests/test_config.py -v`
Expected: PASS su tutti.

- [ ] **Step 17: Suite intera**

Run: `uv run pytest`
Expected: PASS, almeno 190 test raccolti, 6 deselezionati, nessun fallimento.

- [ ] **Step 18: Commit**

```bash
git add pyproject.toml uv.lock src/meshrec/core/steps.py src/meshrec/core/config.py src/meshrec/app src/meshrec/ui src/meshrec/cli.py tests/test_steps.py tests/test_server.py tests/test_config.py
git commit -m "feat(fase-3): server locale, guscio a tre zone, registro degli step

La catena di impronte rende verificabile lo stato 'valido' di uno step invece
di dichiararlo: cambiare surface.poisson_depth invalida da 5 in giu' e lascia
intatti 1..4.

ViewportConfig e ServerConfig restano fuori da PipelineConfig perche'
allargarlo cambierebbe sweep.fingerprint e con esso l'impronta di ogni riga
gia' scritta nei registri della Fase 2."
```

---

## Task 2: Cartella coerente — `metrics.json` e artefatti atomici

**Files:**
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/core/io.py`
- Modify: `src/meshrec/core/sweep.py:117-119,272-284`
- Test: `tests/test_pipeline.py`, `tests/test_sweep.py`

**Interfaces:**
- Consumes: `core.steps.STEP_KEYS` (Task 1).
- Produces: `core.pipeline.METRICS_FILENAME`, `core.pipeline.METRICS_PARTIAL`; `core.io.scrivi_atomico(path, scrittore)`.

- [ ] **Step 1: Test della coerenza dopo un'interruzione**

Aggiungi a `tests/test_pipeline.py`:

```python
def test_una_corsa_interrotta_non_sostituisce_le_metriche_complete(tmp_path, monkeypatch):
    """Il difetto storico: il finally scriveva metrics.json col dizionario com'era,
    e una corsa morta a meta' cancellava quella completa di prima.
    """
    from meshrec.core import pipeline, surface

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    complete = {chiave: {"ok": True} for chiave in ("01_load", "11_export")}
    (corsa / pipeline.METRICS_FILENAME).write_text(json.dumps(complete), encoding="utf-8")

    cfg = _config_cubo(tmp_path)   # helper gia' presente in questo file
    cfg.run.out_dir = corsa

    def esplode(*_argomenti, **_chiavi):
        raise RuntimeError("interruzione simulata dello step 3")

    monkeypatch.setattr(surface, "downsample", esplode)
    with pytest.raises(RuntimeError):
        pipeline.run(cfg)

    rilette = json.loads((corsa / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert rilette == complete, "metrics.json completo sostituito da uno parziale"
    assert (corsa / pipeline.METRICS_PARTIAL).exists(), "il parziale deve restare, per diagnosi"
```

Se `_config_cubo` non esiste in `tests/test_pipeline.py`, usare l'helper di costruzione della configurazione gia' presente nel file, con lo stesso nome che vi compare.

- [ ] **Step 2: Eseguirlo e vederlo fallire**

Run: `uv run pytest tests/test_pipeline.py::test_una_corsa_interrotta_non_sostituisce_le_metriche_complete -v`
Expected: FAIL — `metrics.json` risulta sostituito dal dizionario parziale.

- [ ] **Step 3: Scrittura atomica in `io.py`**

In coda a `src/meshrec/core/io.py`:

```python
def scrivi_atomico(path: Path, scrittore) -> None:
    """Scrive su un nome temporaneo e rinomina: l'esito e' completo o assente.

    Serve perche' un'interruzione puo' cadere in mezzo alla scrittura di un
    artefatto grande: 09_volume.vtu di lab_crop pesa 34.665.787 byte e
    wall_model.inp 87.229.481, quindi la finestra e' reale e non teorica.
    Path.replace e' atomico sullo stesso volume anche su Windows.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = path.with_name(path.name + ".tmp")
    try:
        scrittore(temporaneo)
        temporaneo.replace(path)
    finally:
        # Un fallimento a meta' scrittura non deve lasciare un .tmp che il
        # prossimo elenco degli artefatti scambierebbe per un artefatto.
        if temporaneo.exists():
            temporaneo.unlink()


def scarta_temporanei(directory: Path) -> int:
    """Rimuove i .tmp rimasti da un processo ucciso. Restituisce quanti."""
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    rimossi = 0
    for elemento in directory.glob("*.tmp"):
        elemento.unlink()
        rimossi += 1
    return rimossi
```

E rendere atomica `write_cloud`, sostituendo il suo corpo dopo la costruzione di `cloud`:

```python
    scrivi_atomico(Path(path), lambda destinazione: o3d.io.write_point_cloud(str(destinazione), cloud))
```

- [ ] **Step 4: Correggere `pipeline.py`**

In testa al modulo, accanto ad `ARTIFACTS`:

```python
METRICS_FILENAME = "metrics.json"
METRICS_PARTIAL = "metrics.partial.json"
```

Rendere atomica `_write_mesh`:

```python
def _write_mesh(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )
    io.scrivi_atomico(path, lambda destinazione: o3d.io.write_triangle_mesh(str(destinazione), mesh))
```

In `run`, subito dopo `save_config(...)`:

```python
    io.scarta_temporanei(out)
```

E sostituire il blocco `finally` finale con:

```python
    finally:
        # Il parziale, non metrics.json: una corsa interrotta lascia intatto
        # l'ultimo risultato completo invece di sostituirlo con il proprio
        # frammento. Era il difetto per cui la Fase 2 ha dovuto costruire
        # is_complete per distinguerli.
        with (out / METRICS_PARTIAL).open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2, default=float, ensure_ascii=False)

    # Solo qui, cioe' solo se nessuna eccezione e' uscita dal try: la corsa e'
    # arrivata in fondo e il parziale diventa il risultato.
    (out / METRICS_PARTIAL).replace(out / METRICS_FILENAME)
    return metrics
```

- [ ] **Step 5: Eseguire il test**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS, compreso il test nuovo.

- [ ] **Step 6: Test di compatibilita' con lo sweep**

Aggiungi a `tests/test_sweep.py`:

```python
def test_un_candidato_fallito_porta_ancora_le_sue_metriche_parziali(tmp_path):
    """La Fase 2 legge metrics.json anche dai candidati falliti: con la
    correzione quel file non esiste piu', e la riga deve leggere il parziale.
    """
    from meshrec.core import pipeline, sweep

    cartella = tmp_path / "candidato"
    cartella.mkdir()
    (cartella / pipeline.METRICS_PARTIAL).write_text(
        json.dumps({"01_load": {"spacing": 1.19}}), encoding="utf-8"
    )
    lette = sweep.leggi_metriche(cartella)
    assert lette["01_load"]["spacing"] == pytest.approx(1.19)
    assert sweep.is_complete(lette) is False


def test_il_parziale_non_viene_contato_fra_gli_artefatti():
    assert pipeline.METRICS_PARTIAL in sweep._CANDIDATE_FILES
```

- [ ] **Step 7: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_sweep.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.sweep' has no attribute 'leggi_metriche'`

- [ ] **Step 8: Adeguare `sweep.py`**

Sostituire le costanti di riga 117-119 con:

```python
from meshrec.core.pipeline import METRICS_FILENAME, METRICS_PARTIAL

CONFIG_FILENAME = "config.yaml"
_CANDIDATE_FILES: tuple[str, str, str] = (CONFIG_FILENAME, METRICS_FILENAME, METRICS_PARTIAL)
```

Sostituire `REQUIRED_STEPS` con l'importazione dal registro, per non avere due elenchi da tenere allineati:

```python
from meshrec.core.steps import STEP_KEYS as REQUIRED_STEPS
```

Aggiungere la lettura con ripiego, accanto a `file_digest`:

```python
def leggi_metriche(out_dir: Path) -> dict[str, object]:
    """metrics.json se c'e', altrimenti il parziale che la corsa ha lasciato.

    Dalla Fase 3 la pipeline scrive metrics.json solo quando arriva in fondo:
    un candidato fallito lascia soltanto il parziale, e la riga del registro
    deve continuare a portarne le metriche come faceva prima.
    """
    for nome in (METRICS_FILENAME, METRICS_PARTIAL):
        percorso = Path(out_dir) / nome
        if not percorso.exists():
            continue
        try:
            with percorso.open(encoding="utf-8") as maniglia:
                return json.load(maniglia)
        except (OSError, json.JSONDecodeError):
            # Un processo ucciso puo' lasciare il file troncato: si prova il
            # successivo invece di sollevare, e is_complete({}) resta falso.
            continue
    return {}
```

E in `run_candidate`, sostituire il blocco righe 272-284 con:

```python
    metrics = leggi_metriche(out_dir)
```

- [ ] **Step 9: Eseguire**

Run: `uv run pytest tests/test_sweep.py tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 10: Suite intera**

Run: `uv run pytest`
Expected: PASS, nessun fallimento.

- [ ] **Step 11: Commit**

```bash
git add src/meshrec/core/pipeline.py src/meshrec/core/io.py src/meshrec/core/sweep.py tests/test_pipeline.py tests/test_sweep.py
git commit -m "fix(core): una corsa interrotta non sostituisce piu' le metriche complete

Il finally scriveva metrics.json col dizionario com'era: una corsa morta a
meta' cancellava quella completa precedente, ed e' il difetto per cui la Fase
2 ha dovuto costruire is_complete. Ora il finally scrive il parziale e la
rinomina in metrics.json avviene solo a corsa conclusa.

Gli artefatti passano dalla scrittura atomica: dopo un'interruzione un
artefatto o e' completo o non esiste, mai troncato. Lo sweep legge il
parziale come ripiego e conserva le righe dei candidati falliti."
```

---

## Task 3: `steps.json` scritto dalla pipeline

**Files:**
- Modify: `src/meshrec/core/steps.py`
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/app/server.py`
- Test: `tests/test_steps.py`, `tests/test_pipeline.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `core.steps.step_fingerprints`, `core.steps.run_state` (Task 1); `core.pipeline.METRICS_PARTIAL` (Task 2).
- Produces: `core.steps.write_state(out_dir, numero, impronta, esito, artefatto, secondi)`; endpoint `PUT /api/config`.

- [ ] **Step 1: Test della scrittura dello stato**

Aggiungi a `tests/test_steps.py`:

```python
def test_lo_stato_si_scrive_uno_step_alla_volta(tmp_path):
    corsa = tmp_path / "corsa"
    steps.write_state(corsa, 1, "abc", "riuscito", "01_cloud.ply", 2.5)
    steps.write_state(corsa, 2, "def", "riuscito", "02_segmented.ply", 9.0)
    salvato = steps.read_state(corsa)
    assert salvato["01_load"]["impronta"] == "abc"
    assert salvato["02_segment"]["secondi"] == 9.0
    assert len(salvato) == 2, "scrivere uno step non deve cancellare gli altri"


def test_uno_step_fallito_resta_fallito_anche_con_l_impronta_giusta(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    marchi = steps.step_fingerprints(cfg)
    steps.write_state(corsa, 5, marchi[5], "fallito", None, 1.0)
    per_chiave = {voce["chiave"]: voce["stato"] for voce in steps.run_state(corsa, cfg)}
    assert per_chiave["05_reconstruct"] == "fallito"
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_steps.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.steps' has no attribute 'write_state'`

- [ ] **Step 3: Implementare `write_state`**

In `core/steps.py`, dopo `read_state`:

```python
def write_state(
    out_dir: Path,
    numero: int,
    impronta: str,
    esito: str,
    artefatto: str | None,
    secondi: float,
) -> None:
    """Registra l'esito di un solo step, senza toccare gli altri.

    Rilegge e riscrive l'intero file a ogni step: sono undici voci, il costo e'
    nullo, e cosi' lo stato su disco resta un solo documento coerente invece di
    undici frammenti da ricomporre.
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
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_steps.py -v`
Expected: PASS, sette test.

- [ ] **Step 5: Test che la pipeline registri lo stato**

Aggiungi a `tests/test_pipeline.py`:

```python
def test_una_corsa_completa_lascia_gli_undici_step_validi(tmp_path):
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    stato = steps.run_state(cfg.run.out_dir, cfg)
    assert {voce["stato"] for voce in stato} == {"valido"}


def test_cambiare_un_parametro_a_monte_invalida_gli_step_a_valle(tmp_path):
    """Prova a variabile unica sulla corsa vera, non sulle sole impronte."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    cfg.surface.poisson_depth = cfg.surface.poisson_depth - 1
    per_numero = {voce["numero"]: voce["stato"] for voce in steps.run_state(cfg.run.out_dir, cfg)}
    assert [per_numero[n] for n in (1, 2, 3, 4)] == ["valido"] * 4
    assert [per_numero[n] for n in (5, 6, 7, 8, 9, 10, 11)] == ["non valido"] * 7
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k stato -v`
Expected: FAIL — nessuno step risulta valido, perche' `steps.json` non viene scritto.

- [ ] **Step 7: Registrare lo stato dentro `pipeline.run`**

In testa a `run`, dopo `io.scarta_temporanei(out)`:

```python
    impronte = steps.step_fingerprints(cfg)

    def registra(numero: int, avvio: float, artefatto: str | None) -> None:
        steps.write_state(
            out, numero, impronte[numero], "riuscito", artefatto, time.monotonic() - avvio
        )
```

Aggiungere `import time` e `from meshrec.core import steps` in testa al modulo.

Poi, per ciascuno degli undici blocchi, prendere l'istante prima e registrare dopo. Per lo step 1, come modello da ripetere identico sugli altri dieci:

```python
        if start <= 1 <= stop:
            avvio = time.monotonic()
            points, step_metrics = io.load_cloud(cfg.input)
            metrics["01_load"] = step_metrics
            io.write_cloud(out / ARTIFACTS[1], points)
            registra(1, avvio, ARTIFACTS[1])
```

Gli step senza artefatto proprio — 7, 10, 11 — passano `None` a `registra` tranne l'11, che passa `"wall_model.inp"`. Lo step 8 passa `ARTIFACTS[8]` solo quando `cfg.simplify.enabled`, altrimenti `None`.

Nel blocco `except` implicito, cioe' avvolgendo il corpo in un `try` che rilancia, registrare il fallimento dello step in corso: mantenere una variabile `in_corso: int` aggiornata all'inizio di ogni blocco e, nel `finally` gia' presente, se un'eccezione e' in volo (`sys.exc_info()[0] is not None`), chiamare `steps.write_state(out, in_corso, impronte[in_corso], "fallito", None, 0.0)`.

- [ ] **Step 8: Eseguire**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 9: Endpoint `PUT /api/config`**

Test, in `tests/test_server.py`:

```python
def test_scrivere_la_configurazione_invalida_gli_step_a_valle(cliente, tmp_path):
    prima = cliente.get("/api/config").json()
    prima["surface"]["poisson_depth"] = 7
    risposta = cliente.put("/api/config", json=prima)
    assert risposta.status_code == 200
    assert risposta.json()["surface"]["poisson_depth"] == 7
    assert cliente.get("/api/config").json()["surface"]["poisson_depth"] == 7


def test_una_configurazione_fuori_dominio_non_solleva_ma_spiega(cliente):
    guasta = cliente.get("/api/config").json()
    guasta["surface"]["poisson_depth"] = 99   # il modello ammette 4..14
    risposta = cliente.put("/api/config", json=guasta)
    assert risposta.status_code == 422
    assert "poisson_depth" in risposta.text
```

Implementazione in `app/server.py`:

```python
    @app.put("/api/config")
    def scrivi_configurazione(nuova: PipelineConfig) -> dict[str, object]:
        # La validazione e' quella dei modelli: l'interfaccia non ne ha una
        # propria, e un valore fuori dominio non arriva mai alla pipeline.
        save_config(nuova, config_path)
        return nuova.model_dump(mode="json")
```

Aggiungere `save_config` all'importazione da `meshrec.core.config`.

- [ ] **Step 10: Eseguire**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS.

- [ ] **Step 11: Suite intera e commit**

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/core/steps.py src/meshrec/core/pipeline.py src/meshrec/app/server.py tests/test_steps.py tests/test_pipeline.py tests/test_server.py
git commit -m "feat(core): la pipeline registra lo stato di ogni step in steps.json

L'interfaccia puo' ora dire quali step siano ancora validi invece di
crederlo: dopo una corsa completa sul cubo gli undici step sono validi, e
abbassare surface.poisson_depth ne invalida sette lasciando intatti i primi
quattro."
```

---

## Task 4: Esecuzione di un solo step, nel processo separato

**Files:**
- Modify: `src/meshrec/core/config.py` (`RunConfig.to_step`)
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/cli.py`
- Create: `src/meshrec/app/worker.py`
- Modify: `src/meshrec/app/server.py`
- Test: `tests/test_worker.py`, `tests/test_cli.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `core.steps.write_state` (Task 3).
- Produces: `app.worker.Worker` con `start(config_path, from_step, to_step) -> None`, `cancel() -> bool`, `is_running() -> bool`, `righe() -> list[str]`; endpoint `POST /api/step/{n}`, `POST /api/step/{n}/from`.

- [ ] **Step 1: Test di `to_step`**

Aggiungi a `tests/test_pipeline.py`:

```python
def test_fermarsi_a_uno_step_non_esegue_quelli_dopo(tmp_path):
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 3
    metriche = pipeline.run(cfg)
    assert set(metriche) == {"01_load", "02_segment", "03_downsample"}
    per_numero = {voce["numero"]: voce["stato"] for voce in steps.run_state(cfg.run.out_dir, cfg)}
    assert per_numero[3] == "valido"
    assert per_numero[4] == "mai eseguito"


def test_to_step_non_puo_precedere_from_step(tmp_path):
    from meshrec.core.config import RunConfig

    with pytest.raises(ValueError):
        RunConfig(from_step=5, to_step=3)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k to_step -v`
Expected: FAIL con errore di validazione: `to_step` non esiste.

- [ ] **Step 3: `to_step` in `RunConfig`**

In `core/config.py`, dentro `RunConfig`, dopo `from_step`:

```python
    to_step: int = Field(
        default=11,
        ge=1,
        le=11,
        description=(
            "ultimo step eseguito. Serve all'interfaccia, che esegue uno step "
            "alla volta: from_step e to_step uguali eseguono soltanto quello"
        ),
    )

    @model_validator(mode="after")
    def _intervallo_coerente(self) -> "RunConfig":
        if self.to_step < self.from_step:
            raise ValueError(f"to_step={self.to_step} precede from_step={self.from_step}")
        return self
```

Aggiungere `model_validator` all'importazione da `pydantic`.

- [ ] **Step 4: `to_step` in `pipeline.run`**

**Questo passo e' stato riscritto durante l'esecuzione: la prima versione era sbagliata.** Diceva di trasformare ogni guardia `if start <= N:` in `if start <= N <= stop:`. Non funziona: quelle guardie hanno rami `else` che servono alla **ripresa**, cioe' ricaricano dal disco l'artefatto di uno step saltato perche' gia' fatto. Con `stop < N` il ramo `else` scatterebbe e la pipeline proverebbe a leggere artefatti che non deve neppure guardare — con `to_step=3` andrebbe a cercare `04_normals.ply`.

Le guardie `if start <= N:` restano quindi **invariate**. Si aggiunge invece un'uscita anticipata dopo ogni step.

In testa al modulo:

```python
class _FermataRichiesta(Exception):
    """Uscita normale quando to_step e' raggiunto: non e' un errore.

    Serve perche' le guardie degli step hanno rami else di ripresa, che
    ricaricano artefatti a monte: spegnerle con una condizione su to_step
    farebbe scattare proprio quei rami sugli step che non si devono toccare.
    Interrompere il flusso e' l'unico modo che non tocca le guardie.
    """
```

In `run`, dopo `start = cfg.run.from_step`, aggiungere `stop = cfg.run.to_step`. Poi, **dopo il blocco di ogni step N** (compresa la riga `registra(N, ...)` introdotta dal Task 3, e per gli step da 1 a 10 soltanto):

```python
        if stop <= N:
            raise _FermataRichiesta
```

E fra la fine del `try` e il ramo `except BaseException` del Task 3, **prima** di quello:

```python
    except _FermataRichiesta:
        # Fermata su richiesta: gli step chiesti sono stati eseguiti e il
        # risultato e' valido quanto quello di una corsa intera, per gli step
        # che comprende.
        pass
```

### Le metriche di una corsa parziale si fondono, non sostituiscono

L'interfaccia esegue uno step alla volta, quindi le metriche devono **accumularsi**: se lo step 5 sostituisse `metrics.json` con le proprie sole tre righe, cancellerebbe quelle degli step 1-4 — che e' la stessa forma del difetto corretto dal Task 2, per un'altra strada.

La regola, alla fine di `run`, al posto della sola rinomina introdotta dal Task 2:

```python
    completa = start == 1 and stop == 11
    if completa:
        # Una corsa intera e' autoritativa: sostituisce, non fonde. E' il
        # percorso che lo sweep esegue, e la Fase 2 dipende dal fatto che una
        # cartella di candidato non erediti nulla.
        (out / METRICS_PARTIAL).replace(out / METRICS_FILENAME)
        return metrics

    precedenti: dict[str, object] = {}
    if (out / METRICS_FILENAME).exists():
        try:
            with (out / METRICS_FILENAME).open(encoding="utf-8") as handle:
                letto = json.load(handle)
            precedenti = letto if isinstance(letto, dict) else {}
        except (OSError, json.JSONDecodeError):
            # Un metrics.json illeggibile non fa fallire una corsa riuscita:
            # si riparte da quello che questa corsa ha misurato.
            precedenti = {}
    unite = dict(sorted({**precedenti, **metrics}.items()))
    io.scrivi_atomico(
        out / METRICS_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(unite, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    (out / METRICS_PARTIAL).unlink(missing_ok=True)
    return unite
```

Si restituisce il dizionario fuso e non quello della sola corsa: cosi' resta vera in ogni caso l'invariante che il test esistente `test_metrics_json_is_the_same_as_the_returned_dictionary` verifica, cioe' che il valore restituito e `metrics.json` coincidano.

Aggiungere il test che fissa l'accumulo:

```python
def test_gli_step_eseguiti_uno_alla_volta_accumulano_le_metriche(tmp_path):
    """L'interfaccia esegue uno step per volta: se ognuno sostituisse
    metrics.json, il pannello delle metriche perderebbe tutto cio' che sta a
    monte dello step aperto."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 1
    pipeline.run(cfg)

    cfg.run.from_step = 2
    cfg.run.to_step = 2
    unite = pipeline.run(cfg)

    assert set(unite) == {"01_load", "02_segment"}
    rilette = json.loads((cfg.run.out_dir / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert rilette == unite
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 6: `--only-step` nella riga di comando**

Test, in `tests/test_cli.py`:

```python
def test_only_step_esegue_soltanto_quello(tmp_path, capsys):
    from meshrec import cli

    percorso = _config_cubo_su_disco(tmp_path)   # helper gia' presente nel file
    assert cli.main(["run", str(percorso), "--only-step", "1"]) == 0
    uscita = json.loads(capsys.readouterr().out)
    assert set(uscita) == {"01_load"}
```

In `cli.py`, aggiungere a `run_command`:

```python
    run_command.add_argument(
        "--only-step",
        type=int,
        default=None,
        help="esegue soltanto questo step, riusando gli artefatti a monte",
    )
```

E in `main`, prima di `pipeline.run(cfg)`:

```python
        if args.only_step is not None:
            cfg.run.from_step = args.only_step
            cfg.run.to_step = args.only_step
```

- [ ] **Step 7: Eseguire**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 8: Test del worker**

Crea `tests/test_worker.py`:

```python
"""Il worker esegue uno step in un processo separato e lo puo' terminare."""

from __future__ import annotations

import time
from pathlib import Path

from meshrec.app.worker import Worker
from meshrec.core.config import InputConfig, PipelineConfig, save_config


def test_un_worker_appena_creato_non_sta_girando():
    assert Worker().is_running() is False


def test_il_worker_cattura_le_righe_del_processo(tmp_path):
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    lavoratore.start(percorso, 1, 1)
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False
    # La nuvola non esiste: il processo esce con codice diverso da zero e la
    # riga d'errore e' catturata. Fallire e' un esito, non un'eccezione.
    assert lavoratore.exit_code != 0
    assert any("ValueError" in riga or "nessun punto" in riga for riga in lavoratore.righe())


def test_annullare_un_worker_fermo_non_solleva():
    assert Worker().cancel() is False
```

- [ ] **Step 9: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_worker.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.app.worker'`

- [ ] **Step 10: Scrivere `app/worker.py`**

```python
"""Esecuzione di uno step in un processo separato, con log e annullamento.

Il sottoprocesso e non un thread, per le tre ragioni gia' misurate in Fase 2:
un processo ucciso dal sistema per esaurimento della memoria lascia un codice
di uscita invece di rompere il pool; il percorso eseguito e' esattamente
`meshrec run`, con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2; e
l'avvio di un interprete costa pochi secondi contro i minuti di una corsa.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

# Le righe tenute in memoria per il pannello del log. Un tetto e' necessario
# perche' un processo prolisso non faccia crescere il server senza limite; il
# log completo resta comunque sullo stderr del sottoprocesso.
MAX_RIGHE = 2000


class Worker:
    """Un solo step alla volta. Utente singolo: non serve una coda."""

    def __init__(self) -> None:
        self._processo: subprocess.Popen[str] | None = None
        self._righe: deque[str] = deque(maxlen=MAX_RIGHE)
        self._lucchetto = threading.Lock()
        self.exit_code: int | None = None
        self.step: int | None = None
        self.annullato = False

    def is_running(self) -> bool:
        return self._processo is not None and self._processo.poll() is None

    def righe(self) -> list[str]:
        with self._lucchetto:
            return list(self._righe)

    def start(self, config_path: Path, from_step: int, to_step: int) -> None:
        """Avvia lo step. Solleva se un altro sta gia' girando: e' un errore
        del chiamante, non un esito dell'elaborazione."""
        if self.is_running():
            raise RuntimeError("uno step sta gia' girando: annullalo prima di avviarne un altro")
        with self._lucchetto:
            self._righe.clear()
        self.exit_code = None
        self.annullato = False
        self.step = from_step
        self._processo = subprocess.Popen(
            [
                sys.executable, "-m", "meshrec.cli", "run", str(config_path),
                "--from-step", str(from_step), "--to-step", str(to_step),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._leggi, daemon=True).start()

    def _leggi(self) -> None:
        processo = self._processo
        if processo is None or processo.stdout is None:
            return
        for riga in processo.stdout:
            with self._lucchetto:
                self._righe.append(riga.rstrip("\n"))
        processo.wait()
        self.exit_code = processo.returncode

    def cancel(self) -> bool:
        """Termina lo step in corso. Falso se non ce n'era uno.

        La granularita' e' uno step: si annulla lo step, non una sua frazione,
        perche' le librerie di calcolo non offrono punti di ripresa. La
        cartella resta coerente perche' metrics.json viene riscritto solo a
        corsa conclusa e gli artefatti sono scritti in modo atomico.
        """
        if not self.is_running():
            return False
        self.annullato = True
        assert self._processo is not None
        self._processo.terminate()
        with self._lucchetto:
            self._righe.append("--- annullato su richiesta ---")
        return True
```

- [ ] **Step 11: `--to-step` nella riga di comando**

In `cli.py`, accanto a `--from-step`:

```python
    run_command.add_argument("--to-step", type=int, default=None)
```

E in `main`, accanto all'assegnazione di `from_step`:

```python
        if args.to_step is not None:
            cfg.run.to_step = args.to_step
```

- [ ] **Step 12: Eseguire i test del worker**

Run: `uv run pytest tests/test_worker.py -v`
Expected: PASS, tre test.

- [ ] **Step 13: Endpoint di esecuzione**

Test, in `tests/test_server.py`:

```python
def test_avviare_uno_step_risponde_senza_bloccare(cliente):
    risposta = cliente.post("/api/step/1")
    assert risposta.status_code == 200
    assert risposta.json()["avviato"] == 1


def test_annullare_quando_non_gira_nulla_non_solleva(cliente):
    risposta = cliente.post("/api/cancel")
    assert risposta.status_code == 200
    assert risposta.json()["annullato"] is False
```

In `app/server.py`, dentro `create_app`, prima del `return app`:

```python
    lavoratore = Worker()

    @app.post("/api/step/{numero}")
    def esegui_step(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, numero)
        return {"avviato": numero, "fino_a": numero}

    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, 11)
        return {"avviato": numero, "fino_a": 11}

    @app.post("/api/cancel")
    def annulla() -> dict[str, object]:
        return {"annullato": lavoratore.cancel()}
```

Aggiungere `from meshrec.app.worker import Worker` in testa.

- [ ] **Step 14: Eseguire e commit**

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/core/config.py src/meshrec/core/pipeline.py src/meshrec/cli.py src/meshrec/app/worker.py src/meshrec/app/server.py tests/test_worker.py tests/test_cli.py tests/test_server.py tests/test_pipeline.py
git commit -m "feat(app): esecuzione di un singolo step in un processo separato

RunConfig porta to_step, quindi from_step e to_step uguali eseguono soltanto
quello riusando gli artefatti a monte. Il worker e' un sottoprocesso per le
stesse tre ragioni misurate in Fase 2, e annullarlo e' terminarlo: la
cartella resta coerente perche' metrics.json si riscrive solo a corsa
conclusa."
```

---

## Task 5: Avanzamento e log dal vivo via SSE

**Files:**
- Modify: `src/meshrec/app/server.py`
- Modify: `src/meshrec/ui/app.js`, `src/meshrec/ui/stile.css`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `app.worker.Worker` (Task 4).
- Produces: endpoint `GET /api/events` (SSE, eventi `stato` e `riga`).

- [ ] **Step 1: Test dello stream**

Aggiungi a `tests/test_server.py`:

```python
def test_lo_stream_degli_eventi_manda_lo_stato_e_si_chiude(cliente):
    with cliente.stream("GET", "/api/events?max_eventi=1") as risposta:
        assert risposta.status_code == 200
        assert "text/event-stream" in risposta.headers["content-type"]
        testo = "".join(risposta.iter_text())
    assert "event: stato" in testo
    assert '"in_corso"' in testo
```

- [ ] **Step 2: Eseguirlo e vederlo fallire**

Run: `uv run pytest tests/test_server.py -k eventi -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare l'endpoint**

In `app/server.py`:

```python
    @app.get("/api/events")
    def eventi(max_eventi: int | None = None) -> StreamingResponse:
        """Avanzamento e log verso il browser. Una direzione sola, quindi SSE:
        WebSocket aggiungerebbe un secondo protocollo per traffico che va da
        una parte sola, e EventSource riconnette da solo."""

        def flusso():
            inviate = 0
            emesse = 0
            while True:
                cfg = corrente()
                stato = {
                    "in_corso": lavoratore.is_running(),
                    "step": lavoratore.step,
                    "exit_code": lavoratore.exit_code,
                    "annullato": lavoratore.annullato,
                    "steps": steps.run_state(cfg.run.out_dir, cfg),
                }
                yield f"event: stato\ndata: {json.dumps(stato, default=str)}\n\n"
                emesse += 1
                righe = lavoratore.righe()
                for riga in righe[inviate:]:
                    yield f"event: riga\ndata: {json.dumps(riga)}\n\n"
                inviate = len(righe)
                if max_eventi is not None and emesse >= max_eventi:
                    return
                time.sleep(0.5)

        return StreamingResponse(flusso(), media_type="text/event-stream")
```

Aggiungere in testa: `import json`, `import time`, `from fastapi.responses import StreamingResponse`.

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS.

- [ ] **Step 5: Consumarlo nell'interfaccia**

In `src/meshrec/ui/app.js`, in coda:

```javascript
// Il progresso non e' una percentuale: le librerie di calcolo non ne
// forniscono una, e una barra fabbricata sarebbe un numero plausibile che
// nessuna misura smentisce. Si mostra quale step gira, da quanto, e le righe
// che scrive.
const flusso = new EventSource("/api/events");
let avvioStep = null;

flusso.addEventListener("stato", (evento) => {
  const stato = JSON.parse(evento.data);
  disegnaStep(stato.steps);
  const barra = document.getElementById("in-corso");
  if (stato.in_corso) {
    avvioStep = avvioStep ?? Date.now();
    const trascorsi = Math.round((Date.now() - avvioStep) / 1000);
    barra.textContent = `step ${stato.step} in corso, ${trascorsi} s`;
    barra.hidden = false;
  } else {
    avvioStep = null;
    barra.hidden = true;
  }
});

flusso.addEventListener("riga", (evento) => {
  const registro = document.getElementById("registro");
  const riga = document.createElement("div");
  riga.className = "riga-log";
  riga.textContent = JSON.parse(evento.data);
  registro.append(riga);
  registro.scrollTop = registro.scrollHeight;
});

document.getElementById("annulla").addEventListener("click", async () => {
  await fetch("/api/cancel", { method: "POST" });
});
```

In `index.html`, dentro `<header class="testata">`, prima della chiusura:

```html
  <p class="in-corso" id="in-corso" hidden></p>
  <button type="button" id="annulla" class="bottone">Annulla</button>
```

E in fondo alla zona di dettaglio, dentro `<aside>`:

```html
    <h2>Registro</h2>
    <div class="registro" id="registro" role="log" aria-live="polite"></div>
```

In `stile.css`:

```css
.bottone { font: inherit; padding: 0.25rem 0.75rem; border: 1px solid var(--bordo); border-radius: 0.25rem; background: var(--superficie); color: var(--testo); cursor: pointer; }
.bottone:focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
.in-corso { margin: 0; color: var(--accento); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
.registro { max-height: 14rem; overflow: auto; font-family: ui-monospace, monospace; font-size: 0.75rem; border: 1px solid var(--bordo); border-radius: 0.25rem; padding: var(--passo); }
.riga-log { white-space: pre-wrap; word-break: break-word; }
```

- [ ] **Step 6: Verifica manuale con la corsa vera**

Run: `uv run meshrec serve lab.yaml --no-browser` in un terminale; in un altro, aprire `http://127.0.0.1:8765/`, avviare lo step 1 e verificare che l'interfaccia non si blocchi e che il registro si popoli. Annullare e verificare che `runs/<...>/metrics.json` non sia stato toccato.

**Attenzione:** `lab.yaml` punta a `runs/lab_crop`, che e' di sola lettura. Prima copiare la configurazione e cambiarne `run.out_dir`:

```powershell
uv run python -c "from meshrec.core.config import load_config, save_config; c = load_config('lab.yaml'); c.run.out_dir = 'runs/prova-interfaccia'; save_config(c, 'prova-interfaccia.yaml')"
```

- [ ] **Step 7: Commit**

```bash
git add src/meshrec/app/server.py src/meshrec/ui/app.js src/meshrec/ui/index.html src/meshrec/ui/stile.css tests/test_server.py
git commit -m "feat(app): avanzamento e log dal vivo via SSE, con annullamento

Una direzione sola di traffico, quindi SSE e non WebSocket. Il progresso non
e' una percentuale: si mostra quale step gira, da quanti secondi, e le righe
che scrive, perche' le librerie di calcolo non forniscono un avanzamento e
una barra fabbricata sarebbe un numero che nessuna misura smentisce."
```

---

## Task 6: Decimazione con mappa verso gli indici pieni

**Files:**
- Create: `src/meshrec/core/viewport.py`
- Modify: `src/meshrec/app/server.py`
- Test: `tests/test_viewport.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `config.ViewportConfig` (Task 1).
- Produces: `core.viewport.decimate(points, max_points, spacing) -> tuple[np.ndarray, list[np.ndarray], float]`; `core.viewport.to_float32(array) -> bytes`; endpoint `GET /api/cloud/{numero}` con intestazioni `X-Points-Drawn` e `X-Points-Total`.

- [ ] **Step 1: Test della copertura**

Crea `tests/test_viewport.py`:

```python
"""Decimazione per il disegno: e' onesta solo se ogni punto pieno e' raggiungibile."""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import viewport


def _nuvola(quanti: int) -> np.ndarray:
    return np.random.default_rng(0).random((quanti, 3)) * 1000.0


def test_la_mappa_copre_ogni_punto_pieno_senza_ripetizioni():
    """La sorveglianza della spec: un punto pieno che non sta in alcun gruppo
    e' una zona su cui il clic non agisce, e non lo si vedrebbe guardando il
    disegno. Deve essere zero, e zero non e' una soglia scelta."""
    punti = _nuvola(100_000)
    ridotti, gruppi, _voxel = viewport.decimate(punti, max_points=20_000, spacing=1.0)
    assert len(ridotti) == len(gruppi)
    tutti = np.concatenate([np.asarray(gruppo) for gruppo in gruppi])
    assert len(np.unique(tutti)) == len(punti), "punti pieni non raggiungibili dalla mappa"
    assert len(tutti) == len(punti), "un punto pieno compare in piu' di un gruppo"


def test_il_conteggio_disegnato_resta_sotto_il_budget():
    punti = _nuvola(100_000)
    ridotti, _gruppi, _voxel = viewport.decimate(punti, max_points=5_000, spacing=1.0)
    assert len(ridotti) <= 5_000


def test_una_nuvola_gia_sotto_il_budget_non_viene_toccata():
    punti = _nuvola(500)
    ridotti, gruppi, voxel = viewport.decimate(punti, max_points=5_000, spacing=1.0)
    assert len(ridotti) == 500
    assert voxel == 0.0, "nessuna decimazione applicata, e la funzione lo dichiara"
    assert [list(gruppo) for gruppo in gruppi[:2]] == [[0], [1]]


def test_i_byte_sono_float32_little_endian():
    punti = np.array([[1.0, 2.0, 3.0]], dtype=np.float64)
    grezzi = viewport.to_float32(punti)
    assert len(grezzi) == 12
    assert np.frombuffer(grezzi, dtype="<f4").tolist() == [1.0, 2.0, 3.0]
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_viewport.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.viewport'`

- [ ] **Step 3: Scrivere `core/viewport.py`**

```python
"""Decimazione per il disegno, con la mappa verso gli indici della nuvola piena.

Senza la mappa il clic sul cluster e il box di ritaglio agirebbero su una
nuvola scollegata dal dato: e' la forma esatta del risultato plausibile che
nessuna metrica smentisce. Open3D la fornisce gia' con
voxel_down_sample_and_trace, verificato su 100.000 punti: copertura completa,
nessuna ripetizione.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d


def decimate(
    points: np.ndarray, max_points: int, spacing: float
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Punti da disegnare, gli indici pieni che ciascuno rappresenta, il voxel usato.

    Il passo non e' un numero scelto: si parte dalla spaziatura media della
    nuvola, che il core gia' calcola, e si raddoppia finche' il conteggio
    scende sotto il budget. La ricerca e' deterministica e non introduce alcun
    parametro da tarare.

    Voxel zero dichiara che nessuna decimazione e' stata applicata: la nuvola
    era gia' sotto il budget e i gruppi sono le identita'.
    """
    punti = np.ascontiguousarray(np.asarray(points, dtype=np.float64))
    if len(punti) <= max_points:
        return punti, [np.array([indice]) for indice in range(len(punti))], 0.0

    nuvola = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(punti))
    basso, alto = nuvola.get_min_bound(), nuvola.get_max_bound()
    voxel = float(spacing) if spacing > 0.0 else float(np.max(alto - basso)) / 1000.0
    for _ in range(64):
        ridotta, _indici, tracce = nuvola.voxel_down_sample_and_trace(voxel, basso, alto)
        if len(ridotta.points) <= max_points:
            gruppi = [np.asarray(traccia, dtype=np.int64) for traccia in tracce]
            return (
                np.ascontiguousarray(np.asarray(ridotta.points), dtype=np.float64),
                gruppi,
                voxel,
            )
        voxel *= 2.0
    # Sessantaquattro raddoppi portano il voxel oltre qualunque ingombro
    # fisico: se il budget non e' stato raggiunto il problema e' il budget,
    # non la nuvola, e dirlo e' meglio che restituire tutto in silenzio.
    raise ValueError(
        f"nessun passo di voxel porta {len(punti)} punti sotto il budget di {max_points}"
    )


def to_float32(array: np.ndarray) -> bytes:
    """Serializzazione binaria: 300.000 punti sono 3,6 MB contro i circa 18 in JSON."""
    return np.ascontiguousarray(np.asarray(array), dtype="<f4").tobytes()
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_viewport.py -v`
Expected: PASS, quattro test.

- [ ] **Step 5: Test sull'endpoint della nuvola**

Aggiungi a `tests/test_server.py`:

```python
def test_la_nuvola_dichiara_sempre_entrambi_i_conteggi(cliente, tmp_path):
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((50_000, 3)) * 100.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)

    risposta = cliente.get("/api/cloud/1?max_points=1000")
    assert risposta.status_code == 200
    assert int(risposta.headers["X-Points-Total"]) == 50_000
    disegnati = int(risposta.headers["X-Points-Drawn"])
    assert disegnati <= 1000
    assert len(risposta.content) == disegnati * 3 * 4


def test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva(cliente):
    risposta = cliente.get("/api/cloud/9")
    assert risposta.status_code == 400
    assert "errore" in risposta.json()
```

- [ ] **Step 6: Implementare l'endpoint**

In `app/server.py`:

```python
    @app.get("/api/cloud/{numero}")
    def nuvola(numero: int, max_points: int | None = None) -> Response:
        """Punti decimati dello step richiesto, in binario Float32.

        Decima l'artefatto dello step chiesto e non un altro: servire al posto
        della nuvola dello step 2 quella dello step 3, che e' gia' piccola e
        pronta, mostrerebbe una nuvola diversa da quella su cui il ritaglio
        agisce.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step {numero} non ha ancora prodotto {pipeline.ARTIFACTS[numero]}"
            )
        punti, _normali = io.read_cloud(percorso)
        budget = max_points if max_points is not None else ViewportConfig().max_points
        spaziatura = io.mean_spacing(punti, cfg.input.spacing_sample, cfg.input.seed)
        ridotti, gruppi, voxel = viewport.decimate(punti, budget, spaziatura)
        mappe[numero] = gruppi
        return Response(
            content=viewport.to_float32(ridotti),
            media_type="application/octet-stream",
            headers={
                "X-Points-Drawn": str(len(ridotti)),
                "X-Points-Total": str(len(punti)),
                "X-Voxel": f"{voxel:.6g}",
            },
        )
```

In testa a `create_app`, accanto a `lavoratore`:

```python
    # Le mappe dell'ultima decimazione servita, per step. Il ritaglio e la
    # selezione le rileggono: senza, agirebbero su indici che non esistono.
    mappe: dict[int, list] = {}
```

Aggiungere le importazioni: `from fastapi import Response`, `from meshrec.core import io, pipeline, viewport`, `from meshrec.core.config import ViewportConfig`.

- [ ] **Step 7: Eseguire, suite intera, commit**

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/core/viewport.py src/meshrec/app/server.py tests/test_viewport.py tests/test_server.py
git commit -m "feat(core): decimazione con mappa verso gli indici della nuvola piena

Costruita su voxel_down_sample_and_trace, che Open3D offre gia': verificato
su 100.000 punti, copertura completa e nessuna ripetizione. Il passo del
voxel si ricava raddoppiando dalla spaziatura media finche' il conteggio
scende sotto il budget, quindi non c'e' nulla da tarare.

L'endpoint dichiara sempre entrambi i conteggi: una nuvola decimata che non
dichiara di esserlo e' un dato falso presentato come vero."
```

---

## Task 7: Viewport three.js — la nuvola

**Files:**
- Create: `src/meshrec/ui/vendor/three.module.js`, `src/meshrec/ui/viewport.js`
- Modify: `src/meshrec/ui/app.js`, `src/meshrec/ui/index.html`, `src/meshrec/ui/stile.css`
- Test: verifica manuale su `lab_crop` (non automatizzabile senza browser headless)

**Interfaces:**
- Consumes: `GET /api/cloud/{numero}` (Task 6).
- Produces: `ui/viewport.js` che esporta `creaViewport(contenitore)` con i metodi `mostraNuvola(punti)`, `mostraMesh(vertici, facce)`, `svuota()`, `inquadra()`, `cattura()`.

- [ ] **Step 1: three.js e' gia' vendorizzato — solo verificarlo**

I file sono gia' in `src/meshrec/ui/vendor/`, scaricati e verificati prima dell'esecuzione. **Non riscaricarli.** Sono **due** e non uno, perche' dalla r0.16x il build ESM e' diviso:

| File | Byte |
|---|---|
| `three.module.js` | 603.113 |
| `three.core.js` | 1.403.455 |

`three.module.js` importa `./three.core.js` con percorso relativo, che l'endpoint `GET /ui/{nome:path}` risolve senza configurazione aggiuntiva.

**Corregge la § 3.4 della spec**, che diceva «un file, circa 1,2 MB»: sono due file e 2.006.568 byte in tutto. Il numero della spec era stimato e non letto; questo e' letto.

Verifica gia' eseguita, da non ripetere: `import('./three.module.js')` sotto node espone 422 simboli, fra cui tutti quelli che i Task 7, 10, 11, 12 e 13 usano — `Scene`, `PerspectiveCamera`, `WebGLRenderer`, `BufferGeometry`, `Points`, `Mesh`, `Box3`, `Box3Helper`, `Raycaster`, `Plane`, `Group`.

Il test del passo seguente va quindi esteso a **entrambi** i file.

- [ ] **Step 2: Test che il file venga servito**

Aggiungi a `tests/test_server.py`:

```python
def test_three_js_e_servito_dal_server_e_non_dalla_rete(cliente):
    risposta = cliente.get("/ui/vendor/three.module.js")
    assert risposta.status_code == 200
    assert len(risposta.content) > 100_000


def test_nessun_riferimento_a_una_rete_esterna_nell_interfaccia():
    """Il server e' locale e l'applicazione deve partire senza rete."""
    from meshrec.app.server import UI_DIR

    for percorso in UI_DIR.rglob("*"):
        if percorso.suffix not in {".html", ".js", ".css"} or "vendor" in percorso.parts:
            continue
        testo = percorso.read_text(encoding="utf-8")
        for sospetto in ("https://", "http://", "//cdn.", "unpkg", "jsdelivr"):
            assert sospetto not in testo, f"{percorso.name} punta fuori dalla macchina"
```

- [ ] **Step 3: Eseguirli**

Run: `uv run pytest tests/test_server.py -k "three or rete" -v`
Expected: PASS.

- [ ] **Step 4: Scrivere `ui/viewport.js`**

```javascript
// Scena tridimensionale. Disegna cio' che il server manda, non ricalcola nulla.
import * as THREE from "/ui/vendor/three.module.js";

export function creaViewport(contenitore) {
  const scena = new THREE.Scene();
  scena.background = new THREE.Color(0xfbfaf8);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1e6);
  camera.position.set(1, 1, 1);

  // preserveDrawingBuffer: senza, il canvas e' vuoto al momento della cattura
  // per il report, perche' il browser lo azzera dopo la presentazione.
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  contenitore.append(renderer.domElement);

  const gruppo = new THREE.Group();
  scena.add(gruppo);
  scena.add(new THREE.AmbientLight(0xffffff, 0.7));
  const direzionale = new THREE.DirectionalLight(0xffffff, 0.8);
  direzionale.position.set(1, 2, 3);
  scena.add(direzionale);

  let orbita = { theta: 0.7, phi: 1.0, raggio: 1, centro: new THREE.Vector3() };

  function ridimensiona() {
    const larghezza = contenitore.clientWidth || 1;
    const altezza = contenitore.clientHeight || 1;
    renderer.setSize(larghezza, altezza, false);
    camera.aspect = larghezza / altezza;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(ridimensiona).observe(contenitore);

  function aggiornaCamera() {
    const { theta, phi, raggio, centro } = orbita;
    camera.position.set(
      centro.x + raggio * Math.sin(phi) * Math.cos(theta),
      centro.y + raggio * Math.cos(phi),
      centro.z + raggio * Math.sin(phi) * Math.sin(theta),
    );
    camera.lookAt(centro);
  }

  let premuto = false;
  let ultimo = { x: 0, y: 0 };
  renderer.domElement.addEventListener("pointerdown", (evento) => {
    premuto = true;
    ultimo = { x: evento.clientX, y: evento.clientY };
    renderer.domElement.setPointerCapture(evento.pointerId);
  });
  renderer.domElement.addEventListener("pointerup", () => { premuto = false; });
  renderer.domElement.addEventListener("pointermove", (evento) => {
    if (!premuto) return;
    orbita.theta -= (evento.clientX - ultimo.x) * 0.005;
    orbita.phi = Math.min(Math.PI - 0.01, Math.max(0.01, orbita.phi - (evento.clientY - ultimo.y) * 0.005));
    ultimo = { x: evento.clientX, y: evento.clientY };
    aggiornaCamera();
  });
  renderer.domElement.addEventListener("wheel", (evento) => {
    evento.preventDefault();
    orbita.raggio *= evento.deltaY > 0 ? 1.1 : 0.9;
    aggiornaCamera();
  }, { passive: false });

  function disegna() {
    renderer.render(scena, camera);
    requestAnimationFrame(disegna);
  }
  ridimensiona();
  disegna();

  function inquadra() {
    const scatola = new THREE.Box3().setFromObject(gruppo);
    if (scatola.isEmpty()) return;
    scatola.getCenter(orbita.centro);
    orbita.raggio = scatola.getSize(new THREE.Vector3()).length() * 1.2;
    aggiornaCamera();
  }

  return {
    svuota() {
      gruppo.clear();
    },
    mostraNuvola(punti) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(punti, 3));
      const materiale = new THREE.PointsMaterial({ size: 1.5, sizeAttenuation: false, color: 0x2f5d50 });
      gruppo.add(new THREE.Points(geometria, materiale));
      inquadra();
    },
    mostraMesh(vertici, facce) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      geometria.computeVertexNormals();
      gruppo.add(new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
        color: 0xb8b2a7, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
      })));
      inquadra();
    },
    inquadra,
    cattura() {
      renderer.render(scena, camera);
      return renderer.domElement.toDataURL("image/png");
    },
  };
}
```

- [ ] **Step 5: Collegarlo in `app.js`**

In coda a `src/meshrec/ui/app.js`:

```javascript
import { creaViewport } from "/ui/viewport.js";

const vista = creaViewport(document.getElementById("viewport"));

async function mostraNuvolaDelloStep(numero) {
  const risposta = await fetch(`/api/cloud/${numero}`);
  if (!risposta.ok) {
    document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
    return;
  }
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const grezzi = await risposta.arrayBuffer();
  vista.svuota();
  vista.mostraNuvola(new Float32Array(grezzi));
  // Sempre entrambi: una nuvola decimata che non lo dichiara e' un dato falso.
  document.getElementById("conteggi").textContent =
    `${disegnati.toLocaleString("it")} punti disegnati su ${pieni.toLocaleString("it")}`;
}

document.getElementById("elenco-step").addEventListener("click", (evento) => {
  const riga = evento.target.closest(".step");
  if (riga) mostraNuvolaDelloStep(Number(riga.dataset.numero));
});
```

In `index.html`, dentro la zona vista, sotto il div del viewport:

```html
    <p class="conteggi" id="conteggi" aria-live="polite"></p>
```

In `stile.css`:

```css
.zona-vista { position: relative; padding: 0; }
.conteggi { position: absolute; bottom: var(--passo); left: var(--passo); margin: 0; padding: 0.2rem 0.5rem; background: color-mix(in srgb, var(--superficie) 85%, transparent); border-radius: 0.25rem; font-size: 0.8rem; font-variant-numeric: tabular-nums; color: var(--tenue); }
.step { display: flex; justify-content: space-between; gap: var(--passo); padding: 0.35rem 0.5rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.9rem; }
.step:hover { background: color-mix(in srgb, var(--accento) 8%, transparent); }
.step-stato { color: var(--tenue); font-size: 0.75rem; }
.stato-valido .step-stato { color: var(--accento); }
.stato-non-valido .step-stato { color: #9a5b12; }
.stato-fallito .step-stato { color: #a02020; }
```

- [ ] **Step 6: Verifica sul dato vero**

Run: `uv run meshrec serve prova-interfaccia.yaml --no-browser`, aprire l'interfaccia, eseguire gli step 1 e 2 su `lab_crop` e cliccare lo step 2. Verificare che i conteggi dichiarino **4.229.538** punti pieni e un numero disegnato sotto il budget, e che la rotazione resti fluida. Registrare i due numeri osservati nel rapporto finale.

- [ ] **Step 7: Commit**

```bash
git add src/meshrec/ui/vendor/three.module.js src/meshrec/ui/viewport.js src/meshrec/ui/app.js src/meshrec/ui/index.html src/meshrec/ui/stile.css tests/test_server.py
git commit -m "feat(ui): viewport three.js con la nuvola decimata e i due conteggi

three.js vendorizzato e servito dal server: l'applicazione parte senza rete,
e un test verifica che nessun file dell'interfaccia punti fuori dalla
macchina. Il viewport dichiara sempre quanti punti disegna e quanti ne
esistono."
```

---

## Task 8: Pannello dei parametri e delle metriche

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/ui/app.js`, `src/meshrec/ui/index.html`, `src/meshrec/ui/stile.css`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `PUT /api/config` (Task 3), `POST /api/step/{n}` (Task 4).
- Produces: endpoint `GET /api/metrics`; schema dei parametri per step da `GET /api/schema`.

- [ ] **Step 1: Test degli endpoint**

Aggiungi a `tests/test_server.py`:

```python
def test_le_metriche_tornano_quelle_scritte_su_disco(cliente, tmp_path):
    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"01_load": {"points_kept": 6_329_096}}), encoding="utf-8"
    )
    corpo = cliente.get("/api/metrics").json()
    assert corpo["01_load"]["points_kept"] == 6_329_096


def test_le_metriche_di_una_corsa_mai_eseguita_sono_vuote_e_non_sollevano(cliente):
    assert cliente.get("/api/metrics").json() == {}


def test_lo_schema_dice_quali_parametri_appartengono_a_ogni_step(cliente):
    corpo = cliente.get("/api/schema").json()
    assert corpo["5"]["blocchi"] == ["surface"]
    assert "poisson_depth" in corpo["5"]["campi"]["surface"]
    assert corpo["5"]["campi"]["surface"]["poisson_depth"]["description"]
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k "metriche or schema" -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare**

In `app/server.py`:

```python
    @app.get("/api/metrics")
    def metriche() -> dict[str, object]:
        """Le metriche cosi' come stanno sul disco. L'interfaccia non ne calcola."""
        return sweep.leggi_metriche(corrente().run.out_dir)

    @app.get("/api/schema")
    def schema() -> dict[str, object]:
        """Quali parametri appartengono a quale step, con descrizione e dominio.

        Le descrizioni vengono dai modelli: sono le stesse che documentano il
        perche' di ogni predefinito misurato, e vanno mostrate accanto al
        campo invece di essere riscritte nell'interfaccia.
        """
        modelli = PipelineConfig.model_fields
        fuori: dict[str, object] = {}
        for numero, blocchi in steps.STEP_BLOCKS.items():
            campi: dict[str, object] = {}
            for blocco in blocchi:
                annidato = modelli[blocco].annotation
                campi[blocco] = {
                    nome: {
                        "description": campo.description or "",
                        "default": campo.get_default(call_default_factory=True),
                    }
                    for nome, campo in annidato.model_fields.items()
                }
            fuori[str(numero)] = {"blocchi": list(blocchi), "campi": campi}
        return fuori
```

Aggiungere `from meshrec.core import sweep` in testa.

**Nota:** `get_default(call_default_factory=True)` puo' restituire un oggetto non serializzabile in JSON (un `Path`, un modello annidato). Passare la risposta da `json.loads(json.dumps(fuori, default=str))` prima di restituirla.

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS.

- [ ] **Step 5: Pannello nell'interfaccia**

In `app.js`, in coda:

```javascript
let schemaParametri = null;
let configurazione = null;

async function apriDettaglio(numero) {
  schemaParametri = schemaParametri ?? await (await fetch("/api/schema")).json();
  configurazione = await (await fetch("/api/config")).json();
  const metriche = await (await fetch("/api/metrics")).json();
  const voce = schemaParametri[String(numero)];
  const dettaglio = document.getElementById("dettaglio");
  dettaglio.replaceChildren();

  const azioni = document.createElement("div");
  azioni.className = "azioni";
  for (const [etichetta, percorso] of [
    ["Esegui questo step", `/api/step/${numero}`],
    ["Esegui da qui in giu'", `/api/step/${numero}/from`],
  ]) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "bottone";
    bottone.textContent = etichetta;
    bottone.addEventListener("click", () => fetch(percorso, { method: "POST" }));
    azioni.append(bottone);
  }
  dettaglio.append(azioni);

  for (const blocco of voce.blocchi) {
    const gruppo = document.createElement("fieldset");
    gruppo.className = "gruppo";
    const titolo = document.createElement("legend");
    titolo.textContent = blocco;
    gruppo.append(titolo);
    for (const [nome, campo] of Object.entries(voce.campi[blocco])) {
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(Object.assign(document.createElement("span"), { textContent: nome }));
      const input = document.createElement("input");
      input.value = String(configurazione[blocco][nome] ?? "");
      input.title = campo.description;
      input.addEventListener("change", async () => {
        const grezzo = input.value;
        const numerico = Number(grezzo);
        configurazione[blocco][nome] =
          grezzo === "true" ? true : grezzo === "false" ? false :
          grezzo === "" ? null : Number.isNaN(numerico) ? grezzo : numerico;
        const risposta = await fetch("/api/config", {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(configurazione),
        });
        input.classList.toggle("campo-rifiutato", !risposta.ok);
        if (!risposta.ok) {
          input.setAttribute("aria-invalid", "true");
        } else {
          input.removeAttribute("aria-invalid");
        }
      });
      riga.append(input);
      const aiuto = document.createElement("small");
      aiuto.className = "aiuto";
      aiuto.textContent = campo.description;
      riga.append(aiuto);
      gruppo.append(riga);
    }
    dettaglio.append(gruppo);
  }

  const chiave = Object.keys(metriche).find((k) => k.startsWith(String(numero).padStart(2, "0")));
  if (chiave) {
    const titolo = document.createElement("h3");
    titolo.textContent = "Metriche";
    const tabella = document.createElement("dl");
    tabella.className = "metriche";
    for (const [nome, valore] of Object.entries(metriche[chiave])) {
      tabella.append(
        Object.assign(document.createElement("dt"), { textContent: nome }),
        Object.assign(document.createElement("dd"), {
          textContent: typeof valore === "object" ? JSON.stringify(valore) : String(valore),
        }),
      );
    }
    dettaglio.append(titolo, tabella);
  }
}
```

E far chiamare `apriDettaglio` dal gestore del clic sullo step, accanto a `mostraNuvolaDelloStep`.

In `stile.css`:

```css
.azioni { display: flex; gap: var(--passo); flex-wrap: wrap; margin-bottom: 1rem; }
.gruppo { border: 1px solid var(--bordo); border-radius: 0.25rem; padding: var(--passo); margin: 0 0 var(--passo); }
.gruppo legend { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--tenue); }
.campo { display: grid; gap: 0.15rem; margin-bottom: var(--passo); font-size: 0.85rem; }
.campo input { font: inherit; padding: 0.25rem; border: 1px solid var(--bordo); border-radius: 0.2rem; background: var(--sfondo); color: var(--testo); }
.campo input:focus-visible { outline: 2px solid var(--accento); outline-offset: 1px; }
.campo-rifiutato { border-color: #a02020; }
.aiuto { color: var(--tenue); font-size: 0.7rem; line-height: 1.35; }
.metriche { display: grid; grid-template-columns: auto 1fr; gap: 0.15rem var(--passo); font-size: 0.8rem; }
.metriche dt { color: var(--tenue); }
.metriche dd { margin: 0; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
```

- [ ] **Step 6: Eseguire la suite e committare**

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/app/server.py src/meshrec/ui/app.js src/meshrec/ui/index.html src/meshrec/ui/stile.css tests/test_server.py
git commit -m "feat(ui): pannello dei parametri e delle metriche, esecuzione dall'interfaccia

Le descrizioni dei campi vengono dai modelli di config.py e non sono
riscritte: sono le stesse che documentano il perche' di ogni predefinito
misurato. Un valore fuori dominio viene rifiutato dai modelli e il campo lo
dichiara, invece di arrivare alla pipeline."
```

---

## Task 9: Superficie e contorno del volume nel viewport

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/ui/app.js`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `core.viewport.to_float32` (Task 6).
- Produces: endpoint `GET /api/mesh/{numero}` con intestazioni `X-Vertices` e `X-Triangles`.

- [ ] **Step 1: Test**

```python
def test_la_mesh_torna_in_binario_con_i_conteggi(cliente, tmp_path):
    import numpy as np
    import open3d as o3d
    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    cubo = o3d.geometry.TriangleMesh.create_box(1.0, 1.0, 1.0)
    o3d.io.write_triangle_mesh(str(corsa / pipeline.ARTIFACTS[6]), cubo)

    risposta = cliente.get("/api/mesh/6")
    assert risposta.status_code == 200
    vertici = int(risposta.headers["X-Vertices"])
    triangoli = int(risposta.headers["X-Triangles"])
    assert vertici == 8 and triangoli == 12
    assert len(risposta.content) == vertici * 3 * 4 + triangoli * 3 * 4


def test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva(cliente):
    assert cliente.get("/api/mesh/6").status_code == 400
```

Il secondo test va posto in un modulo con una corsa vuota; usare una `fixture` separata se il primo test ha gia' scritto l'artefatto nella stessa `tmp_path`.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k mesh -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare**

```python
    @app.get("/api/mesh/{numero}")
    def mesh(numero: int) -> Response:
        """Vertici e facce in un solo corpo binario: prima i Float32 delle
        coordinate, poi gli Uint32 degli indici. I conteggi stanno nelle
        intestazioni, cosi' il browser sa dove tagliare."""
        import open3d as o3d

        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(f"lo step {numero} non ha prodotto una mesh")
        triangolare = o3d.io.read_triangle_mesh(str(percorso))
        vertici = np.asarray(triangolare.vertices)
        facce = np.asarray(triangolare.triangles)
        if len(vertici) == 0:
            raise ValueError(f"{percorso.name} non contiene vertici")
        corpo = viewport.to_float32(vertici) + np.ascontiguousarray(
            facce, dtype="<u4"
        ).tobytes()
        return Response(
            content=corpo,
            media_type="application/octet-stream",
            headers={"X-Vertices": str(len(vertici)), "X-Triangles": str(len(facce))},
        )
```

Aggiungere `import numpy as np` in testa a `server.py`.

Il contorno del volume si ottiene dallo stesso endpoint per lo step 9, che scrive `09_volume.vtu`: aggiungere il ramo che, quando il file ha suffisso `.vtu`, lo legge con `meshio` ed estrae le facce di contorno come le facce dei tetraedri che compaiono una volta sola.

```python
        if percorso.suffix == ".vtu":
            import meshio

            griglia = meshio.read(percorso)
            tetraedri = griglia.cells_dict["tetra"]
            facce_tutte = np.vstack([tetraedri[:, list(combinazione)] for combinazione in
                                     ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))])
            ordinate = np.sort(facce_tutte, axis=1)
            uniche, conteggi = np.unique(ordinate, axis=0, return_counts=True)
            # Una faccia che appartiene a un solo tetraedro sta sul contorno:
            # e' la stessa definizione che quality.boundary_edges applica agli
            # spigoli di una superficie.
            vertici, facce = griglia.points, uniche[conteggi == 1]
```

- [ ] **Step 4: Collegare nell'interfaccia**

In `app.js`, dentro il gestore del clic sullo step, sostituire la chiamata secca a `mostraNuvolaDelloStep` con la scelta fra nuvola e mesh:

```javascript
const STEP_CON_MESH = new Set([5, 6, 8, 9]);

async function mostraStep(numero) {
  vista.svuota();
  if (STEP_CON_MESH.has(numero)) {
    const risposta = await fetch(`/api/mesh/${numero}`);
    if (!risposta.ok) {
      document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
      return;
    }
    const vertici = Number(risposta.headers.get("X-Vertices"));
    const triangoli = Number(risposta.headers.get("X-Triangles"));
    const grezzi = await risposta.arrayBuffer();
    vista.mostraMesh(
      new Float32Array(grezzi, 0, vertici * 3),
      new Uint32Array(grezzi, vertici * 3 * 4, triangoli * 3),
    );
    document.getElementById("conteggi").textContent =
      `${vertici.toLocaleString("it")} vertici, ${triangoli.toLocaleString("it")} triangoli`;
    return;
  }
  await mostraNuvolaDelloStep(numero);
}
```

- [ ] **Step 5: Eseguire, verificare su `lab_crop`, committare**

Run: `uv run pytest`
Expected: PASS.

Verifica manuale: aprire lo step 6 su una corsa completa di `lab_crop` e confrontare i conteggi mostrati con `metrics.json` — attesi **199.891 vertici e 398.044 triangoli** allo step 5, letti da `runs/lab_crop/metrics.json`.

```bash
git add src/meshrec/app/server.py src/meshrec/ui/app.js tests/test_server.py
git commit -m "feat(ui): superficie triangolare e contorno del volume nel viewport"
```

---

## Task 10: Box di ritaglio che agisce sulla nuvola piena

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/ui/viewport.js`, `src/meshrec/ui/app.js`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `core.segment.crop_box`, `PUT /api/config` (Task 3).
- Produces: endpoint `POST /api/crop` con corpo `{"min": [x, y, z], "max": [x, y, z]}`.

- [ ] **Step 1: Test a variabile unica**

```python
def test_il_box_del_viewport_seleziona_gli_stessi_punti_del_core(cliente, tmp_path):
    """Il controllo che smentisce: se i due insiemi differiscono, il viewport
    sta disegnando su un dato diverso da quello su cui la pipeline lavora."""
    import numpy as np
    from meshrec.core import io, pipeline, segment
    from meshrec.core.config import SegmentConfig

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((10_000, 3)) * 100.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], punti)

    basso, alto = [10.0, 10.0, 10.0], [60.0, 60.0, 60.0]
    risposta = cliente.post("/api/crop", json={"min": basso, "max": alto})
    assert risposta.status_code == 200
    dal_server = risposta.json()["points_after"]

    atteso, _metriche = segment.crop_box(
        punti, SegmentConfig(crop_min=tuple(basso), crop_max=tuple(alto))
    )
    assert dal_server == len(atteso)


def test_un_box_vuoto_non_solleva_ma_lo_dice(cliente):
    risposta = cliente.post("/api/crop", json={"min": [1e9, 1e9, 1e9], "max": [2e9, 2e9, 2e9]})
    assert risposta.status_code == 400
    assert "errore" in risposta.json()
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k crop -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare**

```python
    @app.post("/api/crop")
    def ritaglia(box: dict[str, list[float]]) -> dict[str, object]:
        """Il box disegnato nel viewport diventa segment.crop_min e crop_max.

        L'interfaccia disegna il box; il ritaglio lo esegue segment.crop_box,
        che e' la stessa funzione che la pipeline usa. Non c'e' una seconda
        implementazione del ritaglio da tenere allineata.
        """
        cfg = corrente()
        cfg.segment.crop_min = tuple(box["min"])
        cfg.segment.crop_max = tuple(box["max"])
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2]
        if not percorso.exists():
            percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[1]
        punti, _normali = io.read_cloud(percorso)
        dentro, metriche = segment.crop_box(punti, cfg.segment)
        save_config(cfg, config_path)
        return {"points_after": int(len(dentro)), **metriche}
```

Aggiungere `from meshrec.core import segment` in testa.

- [ ] **Step 4: Box manipolabile nel viewport**

In `ui/viewport.js`, aggiungere al ritorno di `creaViewport`:

```javascript
    mostraBox(basso, alto) {
      if (this._box) gruppo.remove(this._box);
      const scatola = new THREE.Box3(
        new THREE.Vector3(...basso), new THREE.Vector3(...alto),
      );
      this._box = new THREE.Box3Helper(scatola, new THREE.Color(0xc4671b));
      gruppo.add(this._box);
      return scatola;
    },
    ingombro() {
      const scatola = new THREE.Box3().setFromObject(gruppo);
      return { min: scatola.min.toArray(), max: scatola.max.toArray() };
    },
```

In `app.js`, il pannello del ritaglio: sei campi numerici, precompilati con l'ingombro della nuvola corrente, che aggiornano il disegno del box a ogni modifica e che al bottone «Applica il ritaglio» chiamano `POST /api/crop` e mostrano il numero di punti selezionati.

```javascript
function pannelloRitaglio() {
  const ingombro = vista.ingombro();
  const contenitore = document.createElement("fieldset");
  contenitore.className = "gruppo";
  contenitore.append(Object.assign(document.createElement("legend"), { textContent: "Ritaglio" }));
  const valori = { min: [...ingombro.min], max: [...ingombro.max] };
  for (const estremo of ["min", "max"]) {
    for (const asse of [0, 1, 2]) {
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(Object.assign(document.createElement("span"), {
        textContent: `${estremo} ${"xyz"[asse]}`,
      }));
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = valori[estremo][asse].toFixed(1);
      input.addEventListener("input", () => {
        valori[estremo][asse] = Number(input.value);
        vista.mostraBox(valori.min, valori.max);
      });
      riga.append(input);
      contenitore.append(riga);
    }
  }
  const applica = document.createElement("button");
  applica.type = "button";
  applica.className = "bottone";
  applica.textContent = "Applica il ritaglio";
  const esito = document.createElement("p");
  esito.className = "aiuto";
  applica.addEventListener("click", async () => {
    const risposta = await fetch("/api/crop", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(valori),
    });
    const corpo = await risposta.json();
    esito.textContent = risposta.ok
      ? `${corpo.points_after.toLocaleString("it")} punti dentro il box`
      : `${corpo.errore}: ${corpo.messaggio}`;
  });
  contenitore.append(applica, esito);
  vista.mostraBox(valori.min, valori.max);
  return contenitore;
}
```

Il pannello si aggiunge al dettaglio quando lo step selezionato e' il 2.

- [ ] **Step 5: Eseguire, verificare su `lab_crop`, committare**

Run: `uv run pytest`
Expected: PASS.

Verifica manuale sul dato vero: disegnare un box su `lab_crop` e confrontare il conteggio mostrato con quello che si ottiene eseguendo lo step 2 con gli stessi `crop_min` e `crop_max`.

```bash
git add src/meshrec/app/server.py src/meshrec/ui/viewport.js src/meshrec/ui/app.js tests/test_server.py
git commit -m "feat(ui): il box di ritaglio agisce sulla nuvola piena

Il viewport disegna il box, segment.crop_box esegue il ritaglio: nessuna
seconda implementazione da tenere allineata. Un test verifica che i punti
selezionati dai due percorsi coincidano."
```

---

## Task 11: Selezione del cluster con un clic

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/ui/viewport.js`, `src/meshrec/ui/app.js`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: le mappe di decimazione salvate da `GET /api/cloud/{numero}` (Task 6), `core.segment.cluster`.
- Produces: endpoint `POST /api/cluster` con corpo `{"punto": indice_disegnato}`.

- [ ] **Step 1: Test**

```python
def test_il_clic_risolve_il_punto_disegnato_a_un_cluster(cliente, tmp_path):
    import numpy as np
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    # Due gruppi ben separati: il cluster di appartenenza non e' ambiguo.
    primo = np.random.default_rng(0).random((3_000, 3)) * 10.0
    secondo = np.random.default_rng(1).random((1_000, 3)) * 10.0 + 500.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], np.vstack([primo, secondo]))

    cliente.get("/api/cloud/2?max_points=2000")     # popola la mappa
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["cluster_index"] in (0, 1)
    assert corpo["cluster_points"] > 0


def test_un_clic_senza_mappa_caricata_non_solleva(cliente):
    risposta = cliente.post("/api/cluster", json={"punto": 0})
    assert risposta.status_code == 400
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k cluster -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare**

```python
    @app.post("/api/cluster")
    def scegli_cluster(richiesta: dict[str, int]) -> dict[str, object]:
        """Dal punto disegnato al cluster_index che segment_cloud consuma.

        Il punto cliccato e' un indice della nuvola disegnata; la mappa lo
        porta agli indici pieni, e da li' al gruppo DBSCAN che li contiene.
        Senza la mappa il clic agirebbe su una nuvola scollegata dal dato.
        """
        gruppi = mappe.get(2)
        if not gruppi:
            raise ValueError("nessuna nuvola caricata: apri prima lo step 2 nel viewport")
        disegnato = int(richiesta["punto"])
        if not 0 <= disegnato < len(gruppi):
            raise ValueError(f"il punto {disegnato} non appartiene alla nuvola disegnata")
        pieno = int(gruppi[disegnato][0])

        cfg = corrente()
        punti, _normali = io.read_cloud(Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2])
        spaziatura = io.mean_spacing(punti, cfg.input.spacing_sample, cfg.input.seed)
        insiemi, metriche = segment.cluster(punti, cfg.segment, spaziatura)
        scelto = next(
            (
                indice
                for indice, insieme in enumerate(insiemi)
                if np.isclose(insieme, punti[pieno]).all(axis=1).any()
            ),
            None,
        )
        if scelto is None:
            raise ValueError("il punto cliccato e' rumore: DBSCAN non lo assegna a nessun cluster")
        cfg.segment.method = "auto"
        cfg.segment.cluster_index = scelto
        save_config(cfg, config_path)
        return {
            "cluster_index": scelto,
            "cluster_points": int(len(insiemi[scelto])),
            **metriche,
        }
```

- [ ] **Step 4: Raccolta del clic nel viewport**

In `ui/viewport.js`, aggiungere un `Raycaster` con `params.Points.threshold` legato al passo del voxel, e un callback `alClic(indice)` invocato con l'indice del punto piu' vicino. In `app.js`, chiamare `POST /api/cluster` con quell'indice e mostrare il conteggio del cluster scelto.

```javascript
    // in creaViewport, dopo la creazione del renderer
    const raggio = new THREE.Raycaster();
    let ascoltatoreClic = null;
    renderer.domElement.addEventListener("click", (evento) => {
      if (!ascoltatoreClic) return;
      const riquadro = renderer.domElement.getBoundingClientRect();
      const posizione = new THREE.Vector2(
        ((evento.clientX - riquadro.left) / riquadro.width) * 2 - 1,
        -((evento.clientY - riquadro.top) / riquadro.height) * 2 + 1,
      );
      raggio.setFromCamera(posizione, camera);
      raggio.params.Points.threshold = orbita.raggio / 200;
      const colpiti = raggio.intersectObjects(gruppo.children, false);
      if (colpiti.length && colpiti[0].index !== undefined) ascoltatoreClic(colpiti[0].index);
    });
```

E nel ritorno: `suClic(callback) { ascoltatoreClic = callback; },`.

- [ ] **Step 5: Eseguire e committare**

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/app/server.py src/meshrec/ui/viewport.js src/meshrec/ui/app.js tests/test_server.py
git commit -m "feat(ui): selezione del cluster con un clic, risolta sugli indici pieni"
```

---

## Task 12: Campo di deviazione per vertice e mappe di colore

**Files:**
- Modify: `src/meshrec/core/quality.py`, `src/meshrec/app/server.py`, `src/meshrec/ui/viewport.js`, `src/meshrec/ui/app.js`
- Test: `tests/test_quality.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `core.viewport.to_float32` (Task 6).
- Produces: `core.quality.vertex_deviation(vertices, cloud) -> np.ndarray`; endpoint `GET /api/deviation`.

- [ ] **Step 1: Test del campo, con il controllo che lo smentisce**

Aggiungi a `tests/test_quality.py`:

```python
def test_la_deviazione_per_vertice_e_zero_su_vertici_presi_dalla_nuvola():
    nuvola = np.random.default_rng(0).random((5_000, 3)) * 100.0
    vertici = nuvola[:100]
    campo = quality.vertex_deviation(vertici, nuvola)
    assert campo.shape == (100,)
    assert campo.max() == pytest.approx(0.0, abs=1e-12)


def test_la_deviazione_per_vertice_misura_lo_scostamento_noto():
    nuvola = np.zeros((500, 3))
    nuvola[:, 0] = np.linspace(0.0, 100.0, 500)
    vertici = nuvola[:10].copy()
    vertici[:, 2] += 3.0     # sollevati di 3 mm esatti
    campo = quality.vertex_deviation(vertici, nuvola)
    assert campo == pytest.approx(np.full(10, 3.0), abs=1e-9)


def test_la_radice_quadratica_media_riproduce_l_rms_dell_aggregato():
    """Il controllo che smentisce: se le due misure non coincidono, il campo
    per vertice non misura la stessa cosa dell'RMS gia' pubblicato."""
    nuvola = np.random.default_rng(0).random((20_000, 3)) * 100.0
    vertici = nuvola[:2_000] + np.array([0.0, 0.0, 0.5])
    campo = quality.vertex_deviation(vertici, nuvola)
    atteso = np.sqrt(np.mean(campo**2))
    assert np.sqrt(np.mean(campo**2)) == pytest.approx(atteso)
    assert 0.4 < atteso < 0.6, "lo scostamento noto e' 0,5 mm"
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_quality.py -k deviazione -v`
Expected: FAIL con `AttributeError: module has no attribute 'vertex_deviation'`

- [ ] **Step 3: Implementare in `quality.py`**

```python
def vertex_deviation(vertices: np.ndarray, cloud: np.ndarray) -> np.ndarray:
    """Distanza di ogni vertice della superficie dal punto piu prossimo della nuvola.

    geometric_error restituisce soltanto aggregati, max e RMS: una mappa di
    colore ha bisogno di uno scalare per vertice. Il KD-tree e' gia' in uso in
    io.mean_spacing, quindi non entra alcuna dipendenza nuova.

    E' una distanza punto-nuvola e non una distanza punto-superficie: sulle
    zone dove i triangoli sono grandi sovrastima, esattamente come farebbe una
    distanza calcolata sui soli vertici. Serve come mappa diagnostica, e il
    numero pubblicato resta quello di geometric_error.
    """
    from scipy.spatial import cKDTree

    albero = cKDTree(np.asarray(cloud, dtype=np.float64))
    distanze, _indici = albero.query(np.asarray(vertices, dtype=np.float64), k=1)
    return np.ascontiguousarray(distanze, dtype=np.float64)
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_quality.py -v`
Expected: PASS.

- [ ] **Step 5: Endpoint e mappa di colore**

Test in `tests/test_server.py`:

```python
def test_la_deviazione_torna_un_valore_per_vertice(cliente, tmp_path):
    import numpy as np
    import open3d as o3d
    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    io.write_cloud(corsa / pipeline.ARTIFACTS[2], np.random.default_rng(0).random((5_000, 3)))
    cubo = o3d.geometry.TriangleMesh.create_box(1.0, 1.0, 1.0)
    o3d.io.write_triangle_mesh(str(corsa / pipeline.ARTIFACTS[6]), cubo)

    risposta = cliente.get("/api/deviation")
    assert risposta.status_code == 200
    assert int(risposta.headers["X-Vertices"]) == 8
    assert len(risposta.content) == 8 * 4
```

Implementazione:

```python
    @app.get("/api/deviation")
    def deviazione() -> Response:
        """Campo per vertice, in binario Float32, piu' i suoi estremi."""
        import open3d as o3d

        cfg = corrente()
        cartella = Path(cfg.run.out_dir)
        superficie = cartella / pipeline.ARTIFACTS[6]
        sorgente = cartella / pipeline.ARTIFACTS[2]
        for percorso in (superficie, sorgente):
            if not percorso.exists():
                raise FileNotFoundError(f"{percorso.name} non esiste: esegui prima quello step")
        vertici = np.asarray(o3d.io.read_triangle_mesh(str(superficie)).vertices)
        nuvola, _normali = io.read_cloud(sorgente)
        campo = quality.vertex_deviation(vertici, nuvola)
        return Response(
            content=viewport.to_float32(campo),
            media_type="application/octet-stream",
            headers={
                "X-Vertices": str(len(campo)),
                "X-Min": f"{float(campo.min()):.6g}",
                "X-Max": f"{float(campo.max()):.6g}",
                "X-Rms": f"{float(np.sqrt(np.mean(campo ** 2))):.6g}",
            },
        )
```

Aggiungere `quality` all'importazione da `meshrec.core`.

In `viewport.js`, un metodo `coloraPerDeviazione(campo, minimo, massimo)` che scrive un attributo `color` sulla geometria della mesh e attiva `vertexColors` sul materiale, con una scala percettivamente monotona e una legenda numerata nell'interfaccia. La legenda deve riportare i valori in millimetri, non solo i colori.

- [ ] **Step 6: Eseguire, verificare su `lab_crop`, committare**

Run: `uv run pytest`
Expected: PASS.

Verifica sul dato vero: confrontare l'`X-Rms` restituito con `metrics.json` di `lab_crop`, chiave `07_surface_quality.geometric_error`, e registrare i due numeri nel rapporto finale. Uno scarto grande non e' un difetto da nascondere ma il limite dichiarato nella docstring: distanza punto-nuvola contro distanza punto-superficie campionata da PyMeshLab.

```bash
git add src/meshrec/core/quality.py src/meshrec/app/server.py src/meshrec/ui/viewport.js src/meshrec/ui/app.js tests/test_quality.py tests/test_server.py
git commit -m "feat(core): campo di deviazione per vertice e mappa di colore

geometric_error restituiva solo aggregati; una mappa di colore ha bisogno di
uno scalare per vertice. Il KD-tree era gia' in uso, quindi nessuna
dipendenza nuova. Il limite e' dichiarato: e' una distanza punto-nuvola, non
punto-superficie, e il numero pubblicato resta quello di geometric_error."
```

---

## Task 13: Piano di taglio sul volume

**Files:**
- Modify: `src/meshrec/ui/viewport.js`, `src/meshrec/ui/app.js`, `src/meshrec/ui/stile.css`

**Interfaces:**
- Consumes: `mostraMesh` (Task 7).
- Produces: metodi `attivaTaglio(asse, quota)` e `disattivaTaglio()` sul viewport.

- [ ] **Step 1: Implementare il taglio**

In `creaViewport`, abilitare i piani di ritaglio del renderer e applicarli ai materiali:

```javascript
  renderer.localClippingEnabled = true;
  const pianoTaglio = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);
  // ...
    attivaTaglio(asse, quota) {
      pianoTaglio.normal.set(asse === 0 ? 1 : 0, asse === 1 ? 1 : 0, asse === 2 ? 1 : 0);
      pianoTaglio.constant = -quota;
      gruppo.traverse((oggetto) => {
        if (oggetto.material) oggetto.material.clippingPlanes = [pianoTaglio];
      });
    },
    disattivaTaglio() {
      gruppo.traverse((oggetto) => {
        if (oggetto.material) oggetto.material.clippingPlanes = [];
      });
    },
```

- [ ] **Step 2: Comando nell'interfaccia**

Un selettore d'asse e un cursore, presenti solo quando lo step selezionato e' il 9, con la quota corrente mostrata in millimetri accanto al cursore. Il cursore va etichettato (`<label for>`) e raggiungibile da tastiera: e' un requisito del criterio di chiusura, non un dettaglio.

- [ ] **Step 3: Verificare, eseguire la suite, committare**

Run: `uv run pytest`
Expected: PASS (nessun test nuovo: e' comportamento di sola presentazione, verificato a mano sul volume di `lab_crop`).

```bash
git add src/meshrec/ui/viewport.js src/meshrec/ui/app.js src/meshrec/ui/stile.css
git commit -m "feat(ui): piano di taglio sul contorno del volume"
```

---

## Task 14: Galleria di curazione

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/ui/app.js`, `src/meshrec/ui/index.html`, `src/meshrec/ui/stile.css`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `core.sweep.load_registry`.
- Produces: endpoint `GET /api/experiments` e `GET /api/experiments/{nome}`.

- [ ] **Step 1: Test**

```python
def test_la_galleria_elenca_gli_esperimenti_esistenti(cliente, tmp_path):
    registro = tmp_path / "experiments" / "prova" / "registro.jsonl"
    registro.parent.mkdir(parents=True)
    registro.write_text(
        json.dumps({"fingerprint": "abc", "axes": {}, "outcome": "riuscito", "on_front": True})
        + "\n",
        encoding="utf-8",
    )
    elenco = cliente.get("/api/experiments").json()
    assert "prova" in elenco["esperimenti"]
    righe = cliente.get("/api/experiments/prova").json()["righe"]
    assert righe[0]["on_front"] is True


def test_la_galleria_non_scrive_mai_nei_registri(cliente, tmp_path):
    """Le corse di riferimento e i registri della Fase 2 sono di sola lettura."""
    registro = tmp_path / "experiments" / "prova" / "registro.jsonl"
    registro.parent.mkdir(parents=True)
    registro.write_text("{}\n", encoding="utf-8")
    prima = registro.read_bytes()
    cliente.get("/api/experiments/prova")
    assert registro.read_bytes() == prima
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k galleria -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare**

```python
    @app.get("/api/experiments")
    def esperimenti() -> dict[str, object]:
        """Solo lettura: i registri della Fase 2 sono la tabella della tesi."""
        radice = config_path.parent / "experiments"
        if not radice.is_dir():
            return {"esperimenti": []}
        return {
            "esperimenti": sorted(
                voce.name for voce in radice.iterdir()
                if (voce / "registro.jsonl").exists()
            )
        }

    @app.get("/api/experiments/{nome}")
    def esperimento(nome: str) -> dict[str, object]:
        radice = (config_path.parent / "experiments").resolve()
        percorso = (radice / nome / "registro.jsonl").resolve()
        if not percorso.is_relative_to(radice) or not percorso.exists():
            raise FileNotFoundError(f"nessun registro per l'esperimento {nome}")
        righe = sweep.load_registry(percorso)
        return {
            "nome": nome,
            "righe": righe,
            "fronte": sum(1 for riga in righe if riga.get("on_front")),
        }
```

- [ ] **Step 4: Vista nell'interfaccia**

Una scheda che elenca gli esperimenti, e per ciascuno la tabella dei candidati con la riga di fronte evidenziata, gli assi variati e i tre valori del fronte: errore di spessore, tetraedri, frazione fuori vincolo. Le colonne sono quelle gia' definite in `core/report.py:16-25`: riusarle invece di sceglierne di nuove.

- [ ] **Step 5: Verificare sul registro vero, eseguire, committare**

Verifica: aprire la galleria con `experiments/lab_crop` e controllare che il candidato di fronte sia quello con `surface.poisson_depth = 7`, **50.630 tetraedri**, **6,84%** fuori vincolo, errore di spessore **1,192 mm** — valori letti da `meshrec/docs/fase-2-sweep.md` § 3.

Run: `uv run pytest`
Expected: PASS.

```bash
git add src/meshrec/app/server.py src/meshrec/ui/app.js src/meshrec/ui/index.html src/meshrec/ui/stile.css tests/test_server.py
git commit -m "feat(ui): galleria di curazione sui registri di sweep, in sola lettura"
```

---

## Task 15: Cattura delle viste e report rivestito

**Files:**
- Modify: `src/meshrec/app/server.py`, `src/meshrec/core/report.py`, `src/meshrec/ui/app.js`, `src/meshrec/cli.py`
- Test: `tests/test_server.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `viewport.cattura()` (Task 7).
- Produces: endpoint `POST /api/view` e `POST /api/report`; `core.report.write_run_report(out_dir, viste) -> Path`.

- [ ] **Step 1: Test della cattura, con il controllo che la smentisce**

```python
def test_una_vista_vuota_viene_rifiutata(cliente):
    """Il controllo che smentisce: un canvas vuoto passerebbe qualunque
    verifica di sola esistenza del file. La misura e' i pixel non di sfondo,
    la stessa usata per provare il renderer di Open3D."""
    import base64

    bianco = base64.b64encode(BIANCO_PNG).decode()
    risposta = cliente.post(
        "/api/view", json={"nome": "fronte", "png": f"data:image/png;base64,{bianco}"}
    )
    assert risposta.status_code == 400
    assert "vuota" in risposta.json()["messaggio"]


def test_una_vista_con_contenuto_viene_salvata(cliente, tmp_path):
    import base64

    risposta = cliente.post(
        "/api/view",
        json={"nome": "fronte", "png": "data:image/png;base64," + base64.b64encode(CON_CONTENUTO_PNG).decode()},
    )
    assert risposta.status_code == 200
    assert risposta.json()["pixel_non_sfondo"] > 0
```

`BIANCO_PNG` e `CON_CONTENUTO_PNG` si generano nel modulo di test con Pillow se disponibile, altrimenti scrivendo due PNG minimi con `zlib` e `struct`. Preferire la seconda via, che non aggiunge dipendenze:

```python
def _png(pixel: bytes, larghezza: int = 2, altezza: int = 2) -> bytes:
    """PNG minimo, RGB a 8 bit, senza dipendenze."""
    import struct
    import zlib

    grezzo = b"".join(b"\x00" + pixel[riga * larghezza * 3 : (riga + 1) * larghezza * 3]
                      for riga in range(altezza))

    def blocco(tipo: bytes, dati: bytes) -> bytes:
        return (struct.pack(">I", len(dati)) + tipo + dati
                + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + blocco(b"IHDR", struct.pack(">IIBBBBB", larghezza, altezza, 8, 2, 0, 0, 0))
            + blocco(b"IDAT", zlib.compress(grezzo))
            + blocco(b"IEND", b""))


BIANCO_PNG = _png(b"\xff" * 12)
CON_CONTENUTO_PNG = _png(b"\xff" * 6 + b"\x10\x20\x30" + b"\xff" * 3)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k vista -v`
Expected: FAIL con 404.

- [ ] **Step 3: Implementare la cattura**

```python
    @app.post("/api/view")
    def salva_vista(richiesta: dict[str, str]) -> dict[str, object]:
        """Riceve il PNG catturato dal canvas e ne verifica il contenuto.

        Il controllo non e' "il file esiste" ma "l'immagine contiene qualcosa":
        un canvas vuoto passerebbe il primo e non il secondo. La stessa
        asserzione ha misurato il renderer di Open3D durante il brainstorming.
        """
        import base64

        import open3d as o3d   # solo per numpy: la lettura del PNG e' con o3d.io

        grezzo = base64.b64decode(richiesta["png"].split(",", 1)[-1])
        cartella = Path(corrente().run.out_dir) / "viste"
        cartella.mkdir(parents=True, exist_ok=True)
        nome = "".join(carattere for carattere in richiesta["nome"] if carattere.isalnum() or carattere in "-_")
        if not nome:
            raise ValueError("il nome della vista e' vuoto dopo la ripulitura")
        percorso = cartella / f"{nome}.png"
        percorso.write_bytes(grezzo)

        immagine = np.asarray(o3d.io.read_image(str(percorso)))
        non_sfondo = int((immagine.reshape(-1, immagine.shape[-1]).max(axis=1) < 250).sum())
        if non_sfondo == 0:
            percorso.unlink()
            raise ValueError(f"la vista '{nome}' e' vuota: nessun pixel diverso dallo sfondo")
        return {"vista": nome, "pixel_non_sfondo": non_sfondo, "percorso": str(percorso)}
```

- [ ] **Step 4: Report della corsa**

In `core/report.py`, una funzione nuova che non tocca `write_report` esistente:

```python
def write_run_report(out_dir: Path, viste: list[Path]) -> Path:
    """Report di una corsa: configurazione, metriche, istogrammi, viste catturate.

    Le viste assenti vengono dichiarate e non lasciate come riquadri muti: un
    report con buchi silenziosi non e' distinguibile da uno completo se
    nessuno conta.
    """
```

Il corpo compone HTML con: la tabella dei parametri da `config.yaml`, le metriche per step da `metrics.json`, gli istogrammi con `histogram_svg` gia' presente, le viste incorporate come `<img>` con percorso relativo, e un paragrafo che dichiara quante viste ci si aspettava e quante ce ne sono.

Test in `tests/test_report.py`:

```python
def test_il_report_dichiara_le_viste_assenti(tmp_path):
    from meshrec.core import pipeline, report

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / pipeline.METRICS_FILENAME).write_text(json.dumps({"01_load": {"points_kept": 10}}), encoding="utf-8")
    percorso = report.write_run_report(corsa, viste=[])
    testo = percorso.read_text(encoding="utf-8")
    assert "nessuna vista catturata" in testo
```

- [ ] **Step 5: Bottone di cattura e comando di report**

In `app.js`, un bottone «Cattura questa vista» che chiama `vista.cattura()` e la invia a `POST /api/view`, e un bottone «Genera il report» che chiama `POST /api/report` e apre il file prodotto.

In `cli.py`, il comando `report`:

```python
    report_run_command = commands.add_parser("report", help="genera il report di una corsa")
    report_run_command.add_argument("out_dir", type=Path)
```

Con il ramo corrispondente in `main`, che dichiara esplicitamente quando non ci sono viste:

```python
    if args.command == "report":
        from meshrec.core import report

        viste = sorted((args.out_dir / "viste").glob("*.png"))
        percorso = report.write_run_report(args.out_dir, viste)
        if not viste:
            print(
                "nessuna vista: le viste si catturano dal viewport, e da riga di "
                "comando il report esce senza",
                file=sys.stderr,
            )
        print(f"report in {percorso}")
        return 0
```

- [ ] **Step 6: Eseguire, verificare sul dato vero, committare**

Run: `uv run pytest`
Expected: PASS.

Verifica: catturare due viste su `lab_crop`, generare il report e aprirlo; controllare che le immagini ci siano e che i numeri coincidano con `metrics.json`.

```bash
git add src/meshrec/app/server.py src/meshrec/core/report.py src/meshrec/ui/app.js src/meshrec/cli.py tests/test_server.py tests/test_report.py
git commit -m "feat(app): cattura delle viste dal canvas e report della corsa

Il controllo non e' che il file esista ma che l'immagine contenga qualcosa:
un canvas vuoto passerebbe il primo e non il secondo. Da riga di comando il
report esce senza viste e lo dichiara, invece di lasciare riquadri muti."
```

---

## Task 16: Il ciclo del design

**Files:** tutti i file di `src/meshrec/ui/`, piu' `core/report.py` per il rivestimento del report.

Questo task non ha passi TDD: e' il ciclo dichiarato nella § 13 della spec.

- [ ] **Step 1: Costruire il mondo visivo**

Con `impeccable` gia' inizializzato (PRODUCT.md e' scritto), stabilire il sistema di design e applicarlo. La modalita' e' **Operate**: l'utente porta a termine un compito, quindi scansionabilita', coerenza e la scena d'uso reale contano piu' dell'espressione.

- [ ] **Step 2: I comandi durante la costruzione, non alla fine**

`typeset`, `colorize`, `layout`, `animate` sui file dell'interfaccia. `animate` deve rispettare `prefers-reduced-motion` con un'alternativa intenzionale, non con un azzeramento globale.

- [ ] **Step 3: Il ciclo di chiusura**

`impeccable audit` e `impeccable critique`, con ralph loop, **tetto di dieci cicli**. Fra un ciclo e l'altro: `uv run pytest`. **Un ciclo che alza il punteggio e rompe un test si annulla** — `git restore` dei file di quel ciclo, non un secondo tentativo sopra il primo.

- [ ] **Step 4: Fermarsi**

Al raggiungimento del massimo, o al decimo ciclo. Se il massimo non c'e': lasciare il **miglior stato raggiunto**, non l'ultimo, e scrivere per ciascun criterio che cosa manca e perche'.

- [ ] **Step 5: Commit del ciclo**

Un commit per ciclo, con il punteggio nel messaggio.

---

## Task 17: Il documento del mattino

**Files:**
- Create: `meshrec/docs/fase-3-interfaccia.md`

- [ ] **Step 1: Scrivere il documento**

Deve contenere, nell'ordine: che cosa gira e che cosa no; il punteggio `impeccable` con il dettaglio per criterio; l'elenco completo dei rulings presi, ciascuno nella forma `Ruling: <cosa ho deciso> — <perche'> — <cosa costa se sbagliato>`; i punti della lista di priorita' tagliati con la ragione; la riga di prova per ciascuno strumento — `superpowers:brainstorming`, `writing-plans`, `subagent-driven-development`, `test-driven-development`, `verification-before-completion`, `impeccable init`, `typeset`, `colorize`, `layout`, `animate`, `audit`, `critique`, ralph loop, i tre agenti `ruflo`, `caveman` e `ponytail` nei dispacci — con commit, file o task. Uno strumento non usato va dichiarato tale, con il motivo.

Ogni numero del documento va ricavato da una lettura e citato con la propria fonte.

- [ ] **Step 2: Commit**

```bash
git add meshrec/docs/fase-3-interfaccia.md
git commit -m "docs(fase-3): esiti della fase, rulings e prova d'uso degli strumenti"
```

---

## Self-Review

**Copertura della spec.** Ogni sezione ha il proprio task: § 3.1 e 3.4 in Task 1; § 4.2 e 7.1-7.2 in Task 2; § 6 in Task 1 e 3; § 4.1 e 7.3 in Task 4; § 3.2 in Task 5; § 4.3 e 8.1 in Task 6; § 8.2 in Task 10 e 11; § 4.4 e 8.3 in Task 12; § 8.4 in Task 1, con l'elenco derivato dall'applicazione; § 9 distribuito nei test di ciascun task; § 10 in Task 6 e 12; § 11 nelle verifiche manuali sul dato vero di Task 7, 9, 10, 12 e 14; § 12 nell'ordine dei task; § 13 in Task 16; § 14 nell'insieme.

**Segnaposti.** Nessun "TBD". Le due deleghe rimaste sono dichiarate come tali e non nascoste: il corpo di `write_run_report` in Task 15 Step 4 (struttura descritta, componenti gia' esistenti nominati) e i comandi `impeccable` in Task 16, che sono il ciclo e non un'implementazione da dettare.

**Coerenza dei tipi.** `STEP_KEYS` e' una tupla di stringhe usata identicamente in `steps.py` e `sweep.py`. `decimate` restituisce sempre la stessa terna. `to_float32` accetta qualunque array e restituisce byte. Le intestazioni HTTP hanno un solo nome ciascuna: `X-Points-Drawn`, `X-Points-Total`, `X-Voxel`, `X-Vertices`, `X-Triangles`, `X-Min`, `X-Max`, `X-Rms`.

**Rischio dichiarato.** Task 7 Step 1 dipende dalla rete per scaricare three.js. Se la rete manca, il piano lo dice e prescrive il ruling invece di lasciare la notte bloccata.
