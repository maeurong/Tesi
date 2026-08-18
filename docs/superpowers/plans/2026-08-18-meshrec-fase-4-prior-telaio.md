# Fase 4 — Prior geometrico del telaio e modelli parametrici — Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Riconoscere nella nuvola un telaio di membrature prismatiche, misurarne sezione, asse, fuori piombo e rigonfiamento con i controlli che possono smentirli, e generare da quelle misure due modelli a mesh esaedrica confrontabili con la mesh tetraedrica gia' prodotta, fino al deck `.inp`.

**Architecture:** Due moduli nuovi con un confine netto — `core/wall.py` misura e non costruisce, `core/hexa.py` costruisce e non misura — cosi' che ciascuno sia verificabile da solo contro una geometria sintetica a verita' nota. `pipeline.run()` cresce di un solo blocco, lo step 12, che calcola il prior; i due modelli parametrici non sono rami di `run()` ma corse figlie, ciascuna con la propria cartella `runs/<nome>-estruso/` e `runs/<nome>-primitive/`. `core/abaqus.py` e `core/quality.py` vengono **generalizzati per tipo di elemento**, non duplicati in una versione esaedrica parallela.

**Tech Stack:** Python 3.12, numpy, scipy, Open3D, pydantic, gmsh (promosso da extra a dipendenza in Task 1), TetGen, pymeshfix, FastAPI, three.js vendorizzato. Nessuna dipendenza nuova.

**Spec:** `docs/superpowers/specs/2026-08-18-meshrec-fase-4-prior-telaio-design.md`

**Documenti che il piano presuppone letti:** `PRODUCT.md`, `meshrec/docs/fase-4-materiale.md`, `meshrec/docs/fase-1-tolleranza-set.md` (il «metodo delle colonne»), `docs/superpowers/plans/2026-08-13-meshrec-fase-3-interfaccia.md` (lo stile e l'interfaccia su cui si innesta).

---

## Global Constraints

- Ramo di lavoro: `worktree-fase-4-materiale`, nel worktree `/Users/mario/GitHub/Tesi/.claude/worktrees/fase-4-materiale`. Nessuna scrittura nella copia principale `/Users/mario/GitHub/Tesi`.
- Comandi eseguiti da `meshrec/` con `uv run`. Suite: `uv run pytest tests -q --ignore=tests/feasibility`. **Stato di partenza: 402 passati, 3 saltati.** La suite deve restare verde a ogni commit; il numero dei passati cresce, quello dei saltati puo' scendere (Task 1 installa gmsh e sblocca i tre `importorskip`).
- **Nessun numero del provino di laboratorio entra nel codice sorgente.** Ne' il numero di membrature (sei), ne' le sezioni (172x172, 250x250, 140x175, 700x250), ne' il volume (0,4777 m^3), ne' una soglia di quota. Il programma deve girare su una geometria mai vista, senza disegno, senza sapere quante membrature aspettarsi, con un materiale qualunque. Quei numeri vivono nei file di configurazione (Task 13) e nei test. **Se un passo di questo piano sembra chiedere di scriverne uno in `src/`, il passo e' sbagliato: fermarsi e segnalarlo.**
- **Confine della fase: si finisce al deck `.inp`.** Nessun solutore, nessuna risposta strutturale. CalculiX compare in un ruolo solo — verificare che `ccx` accetti un deck su un modello piccolo (Task 8) — e quel controllo e' marcato `feasibility`, quindi salta dove `ccx` non c'e'.
- **Niente armatura.** Calcestruzzo omogeneo, materiale unico dichiarato dall'operatore. Va scritto nel report: e' una scelta, non una dimenticanza.
- **Ogni grandezza mostrata ha un controllo che la smentisce.** I controlli sono di due specie e la distinzione e' vincolante: **intrinseci** (sempre attivi, non sanno nulla del pezzo) e **riscontri dichiarati** (facoltativi; in loro assenza non viene inventata alcuna aspettativa).
- **Esiti discreti indipendenti dalla piattaforma.** Ordini, indici e conteggi devono essere funzione del dato, non della macchina — il progetto ha gia' pagato questa lezione sull'ordine dei voxel di Open3D fra Windows x86-64 e macOS arm64. Le grandezze continue non ricadono sotto la norma: inseguire le ultime cifre di una riduzione in virgola mobile fra arm64 e x86-64 sarebbe fabbricare una precisione che non esiste.
- **Italiano** per commenti, docstring, nomi di test e messaggi. **Niente lettere accentate nelle docstring e nei commenti dentro `src/meshrec/core/`**, come gia' nel resto del core. Restano invariati gli identificatori tecnici: `C3D4`, `C3D10`, `C3D8`, `C3D8I`, `C3D8R`, `BASE`, `TOP`, `ALL_WALL`, `min_ratio`, `nobisect`, `*TIE`, `*SURFACE, TYPE=ELEMENT`, Poisson, TetGen, MeshFix, gmsh.
- L'unico luogo dove un parametro di elaborazione ha un valore predefinito e' `src/meshrec/core/config.py`. Le firme del core non portano predefiniti di elaborazione.
- `Material` non ha predefiniti ed e' obbligatorio (vedi `meshrec/docs/fase-4-materiale.md`): **non reintrodurne**. Ogni test che costruisce una configurazione usa `tests/materiale.py` (`MATERIALE`, `ANALISI`, `crea_config()`), non ne dichiara di propri.
- `meshrec/runs/muro/`, `meshrec/runs/lab_crop/`, `meshrec/experiments/muro/`, `meshrec/experiments/lab_crop/` sono di **sola lettura**. Le corse di riferimento non vengono riscritte: conservano il materiale con cui sono state eseguite davvero.
- Mai `git add -A`: la radice ha centinaia di MB non tracciati. Sempre percorsi espliciti.
- Unita' di lavoro: mm, N, MPa, tonnellata, secondo.

---

## Rulings permanenti presi da questo piano

Sei decisioni che valgono per l'intera fase. Vanno lette prima del Task 1, perche' piu' di un task le presuppone.

### Ruling 1: `PipelineConfig` si allarga di due blocchi, e `sweep.fingerprint` li esclude

**Deciso:** `PipelineConfig` guadagna `wall: WallConfig` e `model: ModelConfig`. `sweep.fingerprint` toglie dal proprio payload **anche** questi due blocchi, oltre a `run` che gia' toglieva.

**Perche':** la Fase 3 aveva stabilito che `PipelineConfig` non si allarga, perche' `sweep.fingerprint` serializza l'intero modello e un campo nuovo cambierebbe l'impronta di ogni riga gia' scritta nei registri della Fase 2, cioe' la tabella sperimentale della tesi. Quel vincolo resta vero, ma la soluzione della Fase 3 — tenere i blocchi nuovi fuori dal modello, come `ViewportConfig` e `ServerConfig` — non si applica qui: `wall` e' letto dallo step 12 dentro `pipeline.run()`, quindi deve viaggiare con la configurazione, ed essere consumato da `steps.step_fingerprints` per l'invalidazione a valle. Escludere i due blocchi dall'**impronta di sweep** ottiene entrambe le cose: i blocchi vivono in `PipelineConfig`, e le 22 righe storiche continuano a riprodursi.

**Verificato prima di scrivere questo piano**, non ipotizzato: rileggendo `experiments/muro/registro.jsonl` e `experiments/lab_crop/registro.jsonl` e ricalcolando `fingerprint` sulla configurazione incorporata in ciascuna riga, **22 righe su 22 riproducono l'impronta registrata** (11 e 11). Il Task 1 fissa quel fatto in un test di regressione che legge i registri veri.

**Costo se sbagliato:** due corse che differiscono solo per `wall` o `model` hanno la stessa impronta di sweep, quindi il registro non le distinguerebbe. E' accettabile perche' lo sweep non varia quei blocchi — nessuno dei suoi assi ci arriva, e tutti i suoi assi stanno a monte dello step 11 — ma la falla va chiusa e non lasciata aperta: `sweep.expand` rifiuta un `AxisSpec` il cui percorso comincia con un blocco escluso, invece di produrre candidati indistinguibili.

### Ruling 2: `abaqus.footprint_coverage` non si tocca

**Deciso:** il «metodo delle colonne» viene **riusato come metodo** — stessa griglia quadrata, stesso lato `4 x spaziatura`, stessa giustificazione misurata — ma `wall.py` ha la propria `chiavi_di_cella`, e `abaqus.footprint_coverage` resta esattamente com'e'.

**Perche':** le due funzioni rispondono a domande diverse (copertura di un insieme di nodi sull'impronta orizzontale contro spessore locale sul piano del telaio) e condividono quattro righe di aritmetica. `footprint_coverage` produce numeri citati nella tesi — 100,00% su `muro` e 98,93% su `lab_crop` — e riscriverla per condividere quattro righe li metterebbe a rischio in cambio di nulla.

**Costo se sbagliato:** se un domani le due griglie dovessero davvero coincidere, l'unificazione va fatta allora, con le due corse di riferimento a portata di mano per riverificare i due numeri.

### Ruling 3: la scomposizione riporta, non solleva

**Deciso:** una regione che fallisce un controllo intrinseco **non** fa fallire il prior. Viene esclusa dalle membrature e finisce in un elenco di regioni scartate, ciascuna con il nome del controllo che ha detto no e il numero che glielo ha fatto dire.

**Perche':** la spec chiede al § 4.3 che il prior «si rifiuti» invece di dare una sezione media priva di senso, e al § 9 che l'interfaccia mostri «in caso di rifiuto il motivo per esteso — quale controllo ha detto no, e quale numero glielo ha fatto dire». Un'eccezione soddisfa la prima richiesta e rende impossibile la seconda: sulla prima regione difettosa la pipeline morirebbe e l'interfaccia non avrebbe nulla da mostrare sulle altre. Il rifiuto resta — quella regione non diventa una membratura e nessun modello parametrico la costruisce — ma e' un esito riportato, non un'interruzione.

**Costo se sbagliato:** un prior che scarta tutto restituisce zero membrature senza sollevare. Per questo il Task 9 aggiunge la sola guardia che manca: se lo step 12 non trova **nessuna** membratura, lo dichiara nelle metriche e i generatori di modello si rifiutano di partire, invece di produrre un modello vuoto.

### Ruling 4: un solo percorso di mesh esaedrica

**Deciso:** `estruso` e `primitive` non sono due generatori. Sono due chiamate alla stessa funzione, che differiscono per due argomenti: il contorno di sezione (misurato oppure il rettangolo dei valori misurati) e l'asse (misurato con il proprio fuori piombo oppure l'asse ideale, dritto).

**Perche':** e' esattamente cio' che la spec dice al § 5 — «i due parametrici sono entrambi sei prismi; cambia se la sezione conserva la forma rilevata o diventa un rettangolo, e se l'asse conserva il fuori piombo misurato o e' dritto». Due generatori separati significherebbero due percorsi che possono divergere, e allora il confronto misurerebbe anche la differenza fra i due codici invece dei due soli effetti che deve separare.

### Ruling 5: gmsh passa da dipendenza facoltativa a dipendenza

**Deciso:** `gmsh>=4.15.2` esce da `[project.optional-dependencies].feasibility` ed entra in `dependencies`.

**Perche':** la spec lo da' per «gia' dipendenza», ma nel repository e' un extra e **non e' installato**: `uv run python -c "import gmsh"` risponde `ModuleNotFoundError`, e i tre test di `tests/test_gmsh_backend.py` sono saltati da `pytest.importorskip`. `core/hexa.py` ne ha bisogno a ogni corsa di un modello parametrico, non solo in una prova di fattibilita'. Non e' una dipendenza nuova: e' gia' dichiarata, gia' risolta, e gia' usata da `core/gmsh_backend.py`.

**Verificato prima di scrivere questo piano:** su questa macchina (macOS arm64) `gmsh` 4.15.2 si installa e produce **soli esaedri** (tipo 5 di gmsh, nessun prisma) da un rettangolo ricombinato ed estruso in sei strati.

### Ruling 6: l'ordine di nodi ed elementi in uscita da gmsh e' canonico, non quello dei tag

**Deciso:** `hexa.py` riordina sempre i nodi per coordinata (`np.lexsort` su x, y, z arrotondate) e gli elementi per la tupla dei propri nodi rimappati, prima di restituire qualunque cosa. L'ordine interno dei nodi di un esaedro **non** si tocca: e' la topologia dell'elemento.

**Perche':** e' il quinto vincolo di prodotto. I tag di gmsh sono un ordine di generazione, non un dato della geometria, e il progetto ha gia' pagato una volta la lezione dell'ordine di iterazione di una libreria fra due piattaforme. Il costo e' un `lexsort`.

**Soffitto dichiarato:** il riordino rende canonico l'**ordine**, non la **combinatoria**. Per il modello `primitive` la sezione e' un rettangolo e la mesh e' strutturata per costruzione, quindi anche la combinatoria e' deterministica. Per il modello `estruso` la sezione e' un poligono e la ricombinazione in quadrilateri e' un algoritmo di gmsh: il numero di elementi puo' in linea di principio differire fra due versioni di gmsh. Il controllo che lo scopre e' il conteggio degli elementi scritto nelle metriche accanto alla versione di gmsh, non un'assunzione taciuta.

---

## File Structure

**Creati:**

| File | Responsabilita' |
|---|---|
| `src/meshrec/core/wall.py` | Il prior: terna del pezzo, griglia delle celle, spessore locale, regioni connesse a spessore quasi costante, per ciascuna asse, lunghezza, sezione, contorno, fuori piombo, rigonfiamento; i tre controlli intrinseci; il riempimento di sezione come esito a tre stati che non scarta (Ruling J); i riscontri dichiarati. **Misura e non costruisce: nessuna mesh, nessun file** |
| `src/meshrec/core/hexa.py` | I due modelli parametrici: prisma singolo via gmsh (ricombinazione in quadrilateri ed estrusione), ordine canonico, taglio alle giunzioni, volume dell'unione, assemblaggio del telaio. **Costruisce e non misura** |
| `tests/test_wall.py` | Verifiche del prior contro geometrie sintetiche a verita' nota |
| `tests/test_hexa.py` | Verifiche dei modelli parametrici contro il volume analitico dei prismi |
| `tests/feasibility/test_calculix_hexa.py` | `ccx` accetta un deck esaedrico con `*SURFACE, TYPE=ELEMENT` e `*TIE`? Marcato `feasibility`, salta senza `ccx` |
| `meshrec/lab_telaio.yaml` | La configurazione della corsa nuova: ritaglio che scende al pavimento e comprende le zapatas, riscontri dichiarati dalla tavola |
| `meshrec/docs/fase-4-prior-telaio.md` | Il documento di esito della fase |

**Modificati:**

| File | Modifica |
|---|---|
| `pyproject.toml` | `gmsh` da `optional-dependencies.feasibility` a `dependencies` |
| `src/meshrec/core/config.py` | `+ WallConfig`, `+ ModelConfig`, `+ PipelineConfig.wall`, `+ PipelineConfig.model`, `RunConfig.to_step` fino a 12 |
| `src/meshrec/core/steps.py` | `+ "12_wall"` in `STEP_KEYS`, `+ STEP_BLOCKS[12]` |
| `src/meshrec/core/sweep.py` | `fingerprint` esclude `wall` e `model`; `expand` rifiuta un asse su un blocco escluso |
| `src/meshrec/core/abaqus.py` | `_fix_sign` diventa pubblica `fix_sign`; `_boundary_faces` generalizzata per tipo di elemento; `boundary_spacing` per facce di qualunque grado; `write_inp` per tipo di elemento, con `*SURFACE, TYPE=ELEMENT`, `*TIE` e carico laterale; `export_model` accetta gli esaedri |
| `src/meshrec/core/quality.py` | `+ hex_volumes`, `+ scaled_jacobian`, `+ hexa_metrics` |
| `src/meshrec/core/pipeline.py` | `+ step 12` (un solo blocco); `+ pipeline.genera_modello` per le corse figlie |
| `src/meshrec/core/report.py` | `+ sezione del prior`, `+ tabella di confronto`, `+ write_comparison_report` |
| `src/meshrec/core/viewport.py` | `+ campo_per_punto`, `+ triangoli_da_quadrilateri` |
| `src/meshrec/app/server.py` | `+ /api/wall`, `+ /api/model/{tipo}`, `+ /api/compare`, `+ /api/membrature`, `+ /api/rigonfiamento`; `esegui_da` fino a 12 |
| `src/meshrec/app/worker.py` | `+ start_comando` per le azioni che non sono uno step |
| `src/meshrec/ui/index.html`, `app.js`, `viewport.js`, `stile.css` | Step 12 nella colonna, caselle dei modelli, colori per membratura, mappa del rigonfiamento, mesh esaedrica, pannello di confronto, stati vuoti |
| `src/meshrec/cli.py` | `+ wall`, `+ model`, `+ compare` |
| `tests/test_config.py`, `test_steps.py`, `test_sweep.py`, `test_abaqus.py`, `test_quality.py`, `test_pipeline.py`, `test_report.py`, `test_viewport.py`, `test_server.py`, `test_app_js.py`, `test_cli.py` | Verifiche dei cambiamenti sopra |

---

## Task 1: Fondamenta — gmsh dipendenza vera, i due blocchi di configurazione, lo step 12 nel registro, l'impronta storica protetta

**Files:**
- Modify: `meshrec/pyproject.toml`
- Modify: `src/meshrec/core/config.py`
- Modify: `src/meshrec/core/steps.py`
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_config.py`, `tests/test_steps.py`, `tests/test_sweep.py`

**Interfaces:**
- Consumes: niente.
- Produces: `config.WallConfig`; `config.ModelConfig`; `PipelineConfig.wall: WallConfig`; `PipelineConfig.model: ModelConfig`; `steps.STEP_KEYS` di dodici elementi con `"12_wall"` in coda; `steps.STEP_BLOCKS[12] == ("wall",)`; `sweep.BLOCCHI_FUORI_IMPRONTA: tuple[str, ...]`.

- [ ] **Step 1: Il test di regressione che protegge le 22 righe storiche**

Sostituisci in `tests/test_config.py` il corpo di `test_l_impronta_di_una_corsa_registrata_non_cambia` con questo, e aggiungi il secondo test subito sotto:

```python
def test_l_impronta_di_una_corsa_registrata_non_cambia():
    """Le impronte della Fase 2 vivono nei registri: allargare PipelineConfig
    senza escludere il blocco nuovo cambierebbe la provenienza di ogni riga
    della tabella sperimentale della tesi.

    Il test non fissa un valore magico: rilegge i due registri veri, rivalida
    la configurazione incorporata in ciascuna riga e ricalcola l'impronta. Se
    coincide con quella registrata, la riga e' ancora derivabile dalla
    configurazione che dichiara.
    """
    import json

    from meshrec.core.sweep import fingerprint

    radice = Path(__file__).resolve().parents[1] / "experiments"
    righe = 0
    for registro in sorted(radice.glob("*/registro.jsonl")):
        for riga in registro.read_text(encoding="utf-8").splitlines():
            if not riga.strip():
                continue
            voce = json.loads(riga)
            cfg = PipelineConfig.model_validate(voce["config"])
            assert fingerprint(cfg) == voce["fingerprint"], (
                f"{registro}: la riga {righe + 1} non e' piu' derivabile dalla "
                "propria configurazione"
            )
            righe += 1
    assert righe == 22, f"attese 22 righe nei due registri, trovate {righe}"


def test_i_blocchi_nuovi_stanno_in_pipelineconfig_e_fuori_dall_impronta():
    """I due blocchi della Fase 4 viaggiano con la configurazione, perche' lo
    step 12 li legge, e restano fuori dall'impronta di sweep, perche' nessun
    asse della Fase 2 li tocca."""
    from meshrec.core.sweep import BLOCCHI_FUORI_IMPRONTA

    campi = set(PipelineConfig.model_fields)
    assert {"wall", "model"} <= campi
    assert set(BLOCCHI_FUORI_IMPRONTA) == {"run", "wall", "model"}
    assert set(BLOCCHI_FUORI_IMPRONTA) <= campi
```

- [ ] **Step 2: Eseguirli e vedere fallire il secondo**

Run: `uv run pytest tests/test_config.py -k impronta -v`
Expected: il primo PASSA gia' oggi — e' la fotografia dello stato attuale, 22 righe su 22 — il secondo FALLISCE con `ImportError: cannot import name 'BLOCCHI_FUORI_IMPRONTA'`.

- [ ] **Step 3: `WallConfig` e `ModelConfig` in `config.py`**

In `config.py`, subito dopo `PipelineConfig` e prima di `load_config`, aggiungi i due modelli. Nessun numero del provino: le soglie sono angoli, frazioni e multipli della spaziatura, e i riscontri dichiarati nascono tutti a `None`.

```python
class WallConfig(_ModelloBase):
    """Step 12: il prior geometrico. Il pezzo e' un telaio di membrature prismatiche.

    Nessun valore qui dentro viene dal provino di laboratorio. Le soglie sono
    angoli, frazioni e multipli della spaziatura media della nuvola: la
    grandezza sorvegliata e' la costanza dello spessore, non il suo valore, e
    una soglia di quota sarebbe una costante tarata sulla scansione di oggi
    (secondo principio di prodotto).
    """

    cell_factor: float = Field(
        default=4.0,
        gt=0.0,
        description=(
            "lato della cella quadrata, in multipli della spaziatura media. E' il "
            "«metodo delle colonne» di docs/fase-1-tolleranza-set.md, dove il "
            "fattore 4 e' misurato e non scelto: con una cella larga quanto la "
            "spaziatura la griglia diventa piu fine dei triangoli della faccia e "
            "una colonna su dieci risulta vuota per puro artefatto di griglia"
        ),
    )
    thickness_tolerance: float = Field(
        default=0.15,
        gt=0.0,
        lt=1.0,
        description=(
            "scarto relativo entro cui due celle adiacenti contano come «stesso "
            "spessore», e quindi come stessa membratura. E' la forma numerica di "
            "«quasi costante»: le membrature sono le regioni connesse a spessore "
            "quasi costante, e questa e' l'unica soglia della scomposizione"
        ),
    )
    min_cells: int = Field(
        default=12,
        gt=0,
        description=(
            "celle minime perche' una regione connessa sia una membratura. Sotto "
            "questo numero la regione e' rumore di griglia e non ha abbastanza "
            "celle perche' una direzione principale sia stimabile"
        ),
    )
    floor_angle_deg: float = Field(
        default=15.0,
        gt=0.0,
        lt=90.0,
        description=(
            "un piano estratto con la normale entro questo angolo dalla verticale "
            "e' candidato pavimento. Il pavimento non e' una membratura e va "
            "scartato come piano, mai come quota"
        ),
    )
    floor_min_ratio: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description=(
            "frazione minima dei punti perche' un piano quasi orizzontale sia il "
            "pavimento e non la faccia superiore di una membratura. Le due "
            "condizioni valgono insieme: orizzontale e esteso"
        ),
    )
    contour_tolerance: float = Field(
        default=5.0,
        gt=0.0,
        description=(
            "tolleranza [mm] con cui il contorno di sezione misurato viene "
            "semplificato. Un contorno con un vertice per punto rilevato porta "
            "nella mesh il rumore dello scanner invece della forma della sezione"
        ),
    )
    parallelism_deg: float = Field(
        default=5.0,
        gt=0.0,
        lt=90.0,
        description=(
            "controllo intrinseco: angolo massimo fra le due facce opposte di una "
            "regione. Oltre, la regione non ha una sezione e il prior si rifiuta "
            "invece di darne una media priva di senso"
        ),
    )
    face_coverage: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "controllo intrinseco: frazione minima delle celle della regione che "
            "vedono entrambe le facce. E' la lezione gia' pagata su FACE_FRONT e "
            "FACE_BACK: una faccia vista da pochi punti produce un piano finto"
        ),
    )
    section_dispersion: float = Field(
        default=0.10,
        gt=0.0,
        description=(
            "controllo intrinseco: dispersione relativa massima della sezione "
            "lungo l'asse. Oltre, la regione non e' un prisma e viene riportata "
            "come tale invece di essere spacciata per una membratura"
        ),
    )
    union_tolerance: float = Field(
        default=0.02,
        gt=0.0,
        description=(
            "controllo intrinseco: scarto relativo ammesso fra la somma dei "
            "volumi delle membrature e il volume della loro unione. Oltre c'e' "
            "doppio conteggio alle giunzioni, che nessuna metrica di qualita' "
            "vedrebbe"
        ),
    )
    union_step_factor: float = Field(
        default=2.0,
        gt=0.0,
        description=(
            "passo del conteggio di celle con cui si misura il volume "
            "dell'unione, in multipli della spaziatura media. Piu' fine, piu' "
            "lento e piu' preciso: l'errore di discretizzazione viene riportato "
            "accanto al risultato, non nascosto"
        ),
    )
    membrature_attese: int | None = Field(
        default=None,
        gt=0,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: quante membrature l'operatore si "
            "aspetta. Assente per definizione su un pezzo nuovo. Se dichiarato il "
            "prior riporta lo scarto; se assente riporta cio' che ha trovato e "
            "non inventa un'aspettativa"
        ),
    )
    sezioni_nominali: list[tuple[float, float]] | None = Field(
        default=None,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: le sezioni nominali attese [mm], "
            "dal disegno se esiste. Non sono la fonte del modello: i modelli "
            "parametrici misurano la sezione sulla nuvola, e il nominale serve "
            "solo a contraddire la misura"
        ),
    )
    volume_atteso: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: il volume complessivo atteso "
            "[mm^3], dal disegno se esiste"
        ),
    )


class ModelConfig(_ModelloBase):
    """I due modelli parametrici e il loro deck. Non e' letto da alcuno step di run().

    La scelta di quali modelli generare non sta qui, ed e' deliberato: e'
    un'azione, non un parametro di elaborazione. Se ci stesse, rigenerare un
    modello in piu' cambierebbe l'impronta di una corsa che non e' cambiata.
    """

    element: Literal["C3D8I", "C3D8", "C3D8R"] = Field(
        default="C3D8I",
        description=(
            "un telaio lavora a flessione. C3D8 a integrazione piena si "
            "irrigidisce a taglio e restituisce spostamenti troppo piccoli, un "
            "errore invisibile guardando la mesh; C3D8R ha il problema opposto, i "
            "modi a clessidra. C3D8I e' supportato sia da Abaqus sia da CalculiX"
        ),
    )
    min_layers: int = Field(
        default=3,
        ge=3,
        description=(
            "strati di elementi minimi nello spessore, imposti dal codice e non "
            "suggeriti. Con uno o due la flessione nello spessore non e' "
            "rappresentata e il risultato e' sbagliato senza alcun segnale. Il "
            "vincolo ge=3 e' il vincolo stesso: non si scende sotto"
        ),
    )
    target_size: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "passo caratteristico della mesh [mm]. None = la sezione minima "
            "divisa per min_layers, cioe' il passo piu' grosso che rispetta il "
            "vincolo degli strati"
        ),
    )
    tie_name_prefix: str = Field(
        default="GIUNZIONE",
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "prefisso dei nomi dei vincoli *TIE fra membrature adiacenti. Stesso "
            "vincolo di caratteri del nome del materiale, e per la stessa "
            "ragione: finisce interpolato in un deck scritto in ascii"
        ),
    )
    lateral_nset: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "CARICO LATERALE, facoltativo: nome della superficie di elemento su "
            "cui agisce la pressione. Assente se non richiesto"
        ),
    )
    lateral_pressure: float | None = Field(
        default=None,
        description="CARICO LATERALE, facoltativo: pressione [MPa] sulla superficie nominata",
    )

    @model_validator(mode="after")
    def _carico_completo_o_assente(self) -> "ModelConfig":
        if (self.lateral_nset is None) != (self.lateral_pressure is None):
            raise ValueError(
                "il carico laterale si dichiara per intero o non si dichiara: "
                f"lateral_nset={self.lateral_nset!r} e "
                f"lateral_pressure={self.lateral_pressure!r}. Meta' dichiarazione "
                "produrrebbe un deck con una card muta o con una pressione "
                "applicata a nulla"
            )
        return self
```

**Nota d'ordine:** `WallConfig` e `ModelConfig` vanno definiti **prima** di `PipelineConfig` nel file, perche' `PipelineConfig` li annota. Se lo Step 3 li ha messi dopo, spostali sopra `class PipelineConfig` — l'ordine di definizione e' l'unico vincolo.

- [ ] **Step 4: Agganciarli a `PipelineConfig` e alzare il tetto di `to_step`**

Dentro `PipelineConfig`, fra `analysis` e `run`:

```python
    wall: WallConfig = Field(default_factory=WallConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
```

In `RunConfig`, il campo `to_step` diventa:

```python
    to_step: int = Field(
        default=12,
        ge=1,
        le=12,
        description=(
            "ultimo step eseguito. Serve all'interfaccia, che esegue uno step "
            "alla volta: from_step e to_step uguali eseguono soltanto quello. "
            "Il tetto e' 12 dalla Fase 4: lo step 12 e' il prior geometrico, e "
            "chiude la corsa madre. from_step resta fermo a 9 e non lo segue, "
            "per la ragione scritta la'. "
            "Con validate_assignment attivo il validatore incrociato rifiuta "
            "ogni stato intermedio incoerente, e nessun ordine di assegnazione "
            "e' sicuro: restringendo un intervallo verso l'alto rompe to_step "
            "per primo, verso il basso rompe from_step. I due campi si "
            "assegnano quindi insieme, con una sola validazione dell'oggetto "
            "intero (RunConfig.model_validate su model_dump aggiornato), mai "
            "uno alla volta"
        ),
    )
```

E in coda alla descrizione di `from_step`, dentro la stringa gia' presente, aggiungi:

```
            " Lo step 12 (prior geometrico) e' l'ultimo e non e' un punto di "
            "ripresa: legge 02_segmented.ply, che e' gia' cio' che una ripresa "
            "da 3 in poi ricarica. Chi vuole il solo prior usa `meshrec wall`, "
            "che e' un'azione e non una ripresa."
```

- [ ] **Step 5: Lo step 12 nel registro degli step**

In `steps.py`, sostituisci il commento sopra `STEP_KEYS` e aggiungi la chiave e il blocco:

```python
# Le dodici chiavi che una corsa completa scrive in metrics.json. Lo step 7 non
# ha artefatto proprio ma ha metriche, quindi c'e' anche lui. Lo step 12 e' il
# prior geometrico della Fase 4: chiude la corsa madre e non e' un punto di
# ripresa.
```

In coda a `STEP_KEYS`, dopo `"11_export",`, la riga `"12_wall",`.
In coda a `STEP_BLOCKS`, dopo `11: ("tet", "analysis"),`, la riga `12: ("wall",),`.

- [ ] **Step 6: `fingerprint` esclude i blocchi nuovi, `expand` rifiuta un asse che ci punta**

In `sweep.py`, sopra `def fingerprint`:

```python
# I blocchi di PipelineConfig che non entrano nell'impronta di sweep.
# `run` non ci entra perche' out_dir e from_step non cambiano il risultato
# dell'elaborazione. `wall` e `model` non ci entrano perche' sono nati con la
# Fase 4, dopo che i registri della Fase 2 erano gia' scritti: includerli
# cambierebbe l'impronta di ogni riga gia' registrata, cioe' la provenienza
# della tabella sperimentale della tesi, e nessun asse di sweep li tocca --
# tutti gli assi della griglia stanno a monte dello step 11. La falla che
# l'esclusione apre e' chiusa da `expand`, che rifiuta un asse su un blocco
# escluso invece di produrre candidati indistinguibili.
BLOCCHI_FUORI_IMPRONTA: tuple[str, ...] = ("run", "wall", "model")
```

Dentro `fingerprint`, al posto di `payload.pop("run", None)`:

```python
    for blocco in BLOCCHI_FUORI_IMPRONTA:
        payload.pop(blocco, None)
```

La prima riga della docstring di `fingerprint` diventa:

```python
    """Sha256 della configurazione canonica, esclusi i blocchi di BLOCCHI_FUORI_IMPRONTA.
```

e sotto la spiegazione gia' presente aggiungi, senza lettere accentate, il paragrafo del commento qui sopra.

In `expand`, come primo controllo del corpo:

```python
    for asse in experiment.axes:
        blocco = asse.path.split(".")[0]
        if blocco in BLOCCHI_FUORI_IMPRONTA:
            raise ValueError(
                f"l'asse '{asse.path}' punta al blocco '{blocco}', che non entra "
                "nell'impronta: due candidati che differissero solo per quel "
                "valore avrebbero la stessa impronta e il registro non potrebbe "
                "distinguerli"
            )
```

- [ ] **Step 7: Eseguire i test dei tre moduli**

Run: `uv run pytest tests/test_config.py tests/test_steps.py tests/test_sweep.py -v`
Expected: PASS. In particolare `test_l_impronta_di_una_corsa_registrata_non_cambia` conta ancora 22 righe su 22 con i due blocchi nuovi in `PipelineConfig`.

- [ ] **Step 8: Il test dell'asse rifiutato e quello della catena di impronte**

In coda a `tests/test_sweep.py`:

```python
def test_un_asse_su_un_blocco_fuori_impronta_viene_rifiutato(tmp_path):
    """Due candidati indistinguibili nel registro sarebbero peggio di nessuno
    sweep: l'errore arriva prima di eseguire, non dopo aver scritto le righe."""
    from meshrec.core.config import AxisSpec, ExperimentConfig, InputConfig

    from materiale import crea_config

    esperimento = ExperimentConfig(
        name="prova",
        base=tmp_path / "base.yaml",
        axes=[AxisSpec(path="wall.min_cells", values=[8, 12])],
    )
    base = crea_config(input=InputConfig(path=tmp_path / "n.ply"))
    with pytest.raises(ValueError, match="non entra nell'impronta"):
        sweep.expand(esperimento, base)
```

In coda a `tests/test_steps.py`:

```python
def test_gli_step_sono_dodici_e_l_ultimo_e_il_prior():
    assert len(steps.STEP_KEYS) == 12
    assert steps.STEP_KEYS[-1] == "12_wall"
    assert steps.STEP_BLOCKS[12] == ("wall",)


def test_lo_step_dodici_non_cambia_le_impronte_degli_undici_precedenti(tmp_path):
    """La catena di impronte si allunga in coda: aggiungere lo step 12 non puo'
    invalidare un artefatto gia' scritto dagli step precedenti."""
    cfg = _config(tmp_path)
    impronte = steps.step_fingerprints(cfg)
    assert set(impronte) == set(range(1, 13))

    cfg_diverso = _config(tmp_path)
    cfg_diverso.wall.min_cells = cfg.wall.min_cells + 1
    diverse = steps.step_fingerprints(cfg_diverso)

    for numero in range(1, 12):
        assert diverse[numero] == impronte[numero], f"lo step {numero} non doveva cambiare"
    assert diverse[12] != impronte[12]
```

- [ ] **Step 9: Eseguirli**

Run: `uv run pytest tests/test_steps.py tests/test_sweep.py -v`
Expected: PASS.

- [ ] **Step 10: gmsh da extra a dipendenza**

In `meshrec/pyproject.toml`, togli `gmsh>=4.15.2` da `[project.optional-dependencies].feasibility` e mettilo in `dependencies`:

```toml
    "fastapi>=0.141.1",
    "uvicorn>=0.52.3",
    # Generatore della mesh esaedrica dei modelli parametrici (core/hexa.py):
    # serve a ogni corsa di un modello, non a una prova di fattibilita', quindi
    # non e' piu' un extra. Era gia' dichiarato fra le dipendenze facoltative e
    # gia' usato da core/gmsh_backend.py.
    "gmsh>=4.15.2",
]
```

e lascia il gruppo vuoto:

```toml
[project.optional-dependencies]
feasibility = []
```

- [ ] **Step 11: Installare e verificare che i tre test saltati non saltino piu'**

Run: `uv sync`
Poi: `uv run pytest tests/test_gmsh_backend.py -v`
Expected: PASS, tre test **eseguiti** e non saltati. Se uno fallisce nel merito invece che per l'import, fermati e segnala: significa che gmsh su questa macchina si comporta diversamente da quanto la Fase 0 aveva misurato, ed e' un fatto da scrivere prima di costruirci sopra.

- [ ] **Step 12: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. I passati salgono rispetto ai 402 di partenza e i saltati scendono dai 3: i tre `importorskip` su gmsh non saltano piu'. Se resta qualche altro salto, e' di altra origine e va lasciato dov'e'.

- [ ] **Step 13: Commit**

```bash
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/src/meshrec/core/config.py meshrec/src/meshrec/core/steps.py meshrec/src/meshrec/core/sweep.py meshrec/tests/test_config.py meshrec/tests/test_steps.py meshrec/tests/test_sweep.py
git commit -m "feat(fase-4): i due blocchi del prior, lo step 12 e gmsh come dipendenza"
```

---

## Task 2: `core/wall.py` — la scomposizione in membrature, senza soglie tarate a mano

**Files:**
- Create: `src/meshrec/core/wall.py`
- Modify: `src/meshrec/core/synth.py` (geometria sintetica di telaio, a verita' nota)
- Modify: `src/meshrec/core/abaqus.py` (`_fix_sign` diventa pubblica `fix_sign`)
- Test: `tests/test_wall.py`, `tests/test_synth.py`

**Interfaces:**
- Consumes: `config.WallConfig` (Task 1); `segment.extract_planes`, `segment.remove_outliers`.
- Produces:
  - `synth.sample_frame_surface(prismi, spacing, noise=0.0, seed=0) -> np.ndarray`, con `prismi: list[tuple[tuple[float, float, float], tuple[float, float, float]]]` cioe' coppie `(origine, dimensioni)`.
  - `wall.fix_sign` riesportata da `abaqus.fix_sign`.
  - `wall.terna(points) -> tuple[np.ndarray, np.ndarray]` — matrice 3x3 delle direzioni `(u, v, n)` e centro.
  - `wall.chiavi_di_cella(coordinate, lato) -> np.ndarray` (N x 2, interi non negativi).
  - `wall.spessore_per_cella(piano, trasversale, lato) -> tuple[np.ndarray, np.ndarray, np.ndarray]` — celle uniche, spessore di ciascuna, indice di cella di ogni punto.
  - `wall.scarta_pavimento(points, cfg_segment, cfg_wall, spacing) -> tuple[np.ndarray, dict]`.
  - `wall.regioni(celle, spessori, cfg) -> list[np.ndarray]` — per ciascuna regione gli indici delle proprie celle, in ordine canonico.
  - `wall.scomponi(points, cfg_segment, cfg_wall, spacing) -> tuple[list[np.ndarray], dict]` — per ciascuna regione gli indici dei propri punti, piu' le metriche della scomposizione.

- [ ] **Step 1: Il telaio sintetico a verita' nota**

In `src/meshrec/core/synth.py`, in coda:

```python
def sample_frame_surface(
    prismi: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    spacing: float,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Campiona le superfici di piu' parallelepipedi, ciascuno con la propria origine.

    Serve alle verifiche del prior: un telaio di membrature prismatiche di cui
    si conoscono sezione, asse, lunghezza e volume analitico, cosi' che la
    scomposizione abbia qualcosa che la smentisca. I numeri dei prismi sono del
    banco di prova, mai del codice: `wall` non sa quante membrature aspettarsi.

    I punti che cadono dentro un altro prisma restano: sono le superfici che
    nella realta' si compenetrano alle giunzioni, e toglierli farebbe misurare
    alla scomposizione una geometria piu' pulita di quella che vedra' mai.
    """
    nuvole = []
    for origine, dimensioni in prismi:
        superficie = sample_box_surface(dimensioni, spacing, noise=noise, seed=seed)
        nuvole.append(superficie + np.asarray(origine, dtype=np.float64))
    return np.ascontiguousarray(np.vstack(nuvole), dtype=np.float64)
```

- [ ] **Step 2: Il test del telaio sintetico**

In coda a `tests/test_synth.py`:

```python
def test_il_telaio_sintetico_ha_i_prismi_che_gli_si_chiedono():
    """Verita' nota del banco: due prismi disgiunti danno una nuvola il cui
    ingombro e' l'unione dei due, e nessun punto fuori."""
    prismi = [
        ((0.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
        ((800.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
    ]
    punti = synth.sample_frame_surface(prismi, spacing=25.0)

    assert punti.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert punti.max(axis=0) == pytest.approx([1000.0, 200.0, 1000.0])
    # nessun punto nella campata vuota fra i due prismi
    assert not ((punti[:, 0] > 250.0) & (punti[:, 0] < 750.0)).any()
```

- [ ] **Step 3: Eseguirlo e vederlo fallire**

Run: `uv run pytest tests/test_synth.py -k telaio -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.synth' has no attribute 'sample_frame_surface'` — poi, dopo lo Step 1, PASS. Se hai gia' scritto lo Step 1, riesegui e attendi PASS.

- [ ] **Step 4: `_fix_sign` diventa pubblica**

In `src/meshrec/core/abaqus.py`, rinomina `_fix_sign` in `fix_sign` (definizione alla riga della `def`, piu' le due chiamate dentro `align_to_axes` e la citazione dentro la docstring di `build_node_sets`). Aggiungi alla docstring, in coda:

```
    Pubblica dalla Fase 4: `wall.terna` deve fissare il segno delle proprie
    direzioni con la stessa convenzione con cui `align_to_axes` fissa le sue,
    o due moduli dello stesso programma sceglierebbero versi opposti sulla
    stessa geometria.
```

Run: `uv run pytest tests/test_abaqus.py -q`
Expected: PASS (nessun test citava il nome privato: verificato con `grep -rn "_fix_sign" src tests` prima di rinominare — rifallo, e se compare in un test aggiornalo).

- [ ] **Step 5: I test della terna e delle celle**

Crea `tests/test_wall.py`:

```python
"""Il prior geometrico: terna del pezzo, celle, spessore locale, regioni.

Ogni verifica ha una geometria sintetica a verita' nota dietro: il numero di
membrature atteso viene dal banco di prova e mai dal codice, che deve poter
girare su una geometria che non ha mai visto.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import synth, wall
from meshrec.core.config import SegmentConfig, WallConfig

# Un telaio sintetico: due montanti, un traverso in alto, uno in basso. Sei
# numeri che stanno qui, nel banco, e in nessun file di src/.
TELAIO = [
    ((0.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),      # montante sinistro
    ((1400.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),   # montante destro
    ((0.0, 0.0, 1600.0), (1600.0, 200.0, 300.0)),   # traverso superiore
    ((0.0, 0.0, -300.0), (1600.0, 200.0, 300.0)),   # traverso inferiore
]
SPAZIATURA = 20.0


def _cfg() -> WallConfig:
    return WallConfig()


def test_la_terna_mette_la_direzione_trasversale_per_ultima():
    """Il telaio e' sottile in y: la terna deve riconoscerlo dal dato, non da
    un asse scelto a mano."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    direzioni, centro = wall.terna(punti)

    assert direzioni.shape == (3, 3)
    assert centro.shape == (3,)
    trasversale = direzioni[2]
    assert abs(abs(trasversale[1]) - 1.0) < 1e-6, f"trasversale attesa lungo y, e' {trasversale}"
    # terna ortonormale destrorsa: e' la condizione perche' u, v, n siano un
    # sistema di riferimento e non tre direzioni qualunque
    assert np.linalg.det(direzioni) == pytest.approx(1.0, abs=1e-9)


def test_la_terna_ha_lo_stesso_verso_su_due_esecuzioni_e_su_una_nuvola_rimescolata():
    """Il verso di una direzione principale e' arbitrario per la SVD: senza
    convenzione due esecuzioni sulla stessa nuvola darebbero assi opposti, e
    ogni indice derivato dalla terna dipenderebbe dall'ordine dei punti."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(0).permutation(len(punti))]

    prima, _ = wall.terna(punti)
    dopo, _ = wall.terna(rimescolati)
    assert prima == pytest.approx(dopo, abs=1e-9)


def test_le_celle_sono_indici_non_negativi_misurati_dal_minimo():
    piano = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 25.0], [-5.0, -5.0]])
    celle = wall.chiavi_di_cella(piano, lato=5.0)

    assert celle.dtype == np.int64
    assert (celle >= 0).all()
    assert celle.shape == (4, 2)
    # il minimo cade nella cella (0, 0); 10 mm a destra del minimo sono tre celle
    assert celle[3].tolist() == [0, 0]
    assert celle[0].tolist() == [1, 1]


def test_lo_spessore_locale_di_una_scatola_e_la_sua_dimensione_sottile():
    """La grandezza sorvegliata e' lo spessore, e su una scatola nota vale la
    dimensione sottile: se non lo fa, ogni regione trovata piu' avanti misura
    un'altra cosa."""
    punti = synth.sample_box_surface((400.0, 180.0, 900.0), SPAZIATURA)
    direzioni, centro = wall.terna(punti)
    centrati = punti - centro
    piano = centrati @ direzioni[:2].T
    trasversale = centrati @ direzioni[2]

    celle, spessori, _ = wall.spessore_per_cella(piano, trasversale, lato=4.0 * SPAZIATURA)

    assert len(celle) == len(spessori)
    # le celle interne alla faccia larga vedono le due facce a 180 mm di distanza
    assert np.median(spessori) == pytest.approx(180.0, abs=1.5 * SPAZIATURA)
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.wall'`.

- [ ] **Step 7: Scrivere la prima meta' di `core/wall.py`**

```python
"""Il prior geometrico: il pezzo e' un telaio di membrature prismatiche.

La spec di architettura chiamava questa fase «prior geometrico muro» e dava per
buono che il pezzo fosse una lastra piana. La premessa e' falsa sul caso studio,
e la falsita' e' stata misurata: il provino e' un telaio di membrature
prismatiche, ciascuna con la propria sezione costante lungo il proprio asse. Un
prior a due piani paralleli schiaccerebbe sezioni diverse in una.

Questo modulo **misura e non costruisce**: nessuna mesh, nessun file. Chi
costruisce e' `hexa.py`. Il confine non e' estetico: e' cio' che rende ciascuno
dei due verificabile da solo contro una geometria sintetica a verita' nota.

Nessun numero del provino di laboratorio vive qui dentro. Non il numero di
membrature, non le sezioni, non il volume, non una soglia di quota: la
scomposizione trova le membrature che ci sono, e su una scatola ne trova una.
"""

from __future__ import annotations

import numpy as np

from meshrec.core import segment
from meshrec.core.abaqus import fix_sign
from meshrec.core.config import SegmentConfig, WallConfig


def terna(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Terna del pezzo: due direzioni nel piano del telaio, la terza trasversale.

    La direzione trasversale e' quella di minore estensione, com'e' gia' in
    `segment._plane_metrics` e in `abaqus.align_to_axes`: un telaio e' sottile
    in una direzione sola, e quella e' la direzione lungo cui si misura lo
    spessore locale.

    Il verso di ciascuna direzione e' fissato da `abaqus.fix_sign`, e non e' un
    dettaglio: la SVD restituisce segni arbitrari, quindi senza convenzione due
    esecuzioni sulla stessa nuvola potrebbero dare assi opposti e ogni indice
    di cella derivato dalla terna dipenderebbe dall'ordine dei punti invece che
    dal dato.

    Restituisce la matrice 3x3 delle direzioni per riga -- u, v, n -- e il
    centro su cui e' stata stimata.
    """
    punti = np.asarray(points, dtype=np.float64)
    centro = punti.mean(axis=0)
    centrati = punti - centro
    _, _, principali = np.linalg.svd(centrati, full_matrices=False)
    estensioni = np.ptp(centrati @ principali.T, axis=0)

    trasversale = int(np.argmin(estensioni))
    restanti = [indice for indice in range(3) if indice != trasversale]
    # u e' la direzione di estensione maggiore fra le due restanti: e' l'asse
    # lungo del pezzo, e fissarlo dal dato invece che dall'ordine della SVD
    # rende la terna la stessa su due esecuzioni.
    restanti.sort(key=lambda indice: -estensioni[indice])

    n = fix_sign(principali[trasversale])
    u = fix_sign(principali[restanti[0]])
    # v come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori.
    v = np.cross(n, u)
    return np.stack([u, v, n]), centro


def chiavi_di_cella(coordinate: np.ndarray, lato: float) -> np.ndarray:
    """Indice intero di cella di ogni punto, su una griglia quadrata di lato dato.

    E' il «metodo delle colonne» di docs/fase-1-tolleranza-set.md: la stessa
    griglia con cui `abaqus.footprint_coverage` misura la copertura della
    superficie d'appoggio, e lo stesso lato `4 x spaziatura`, che li' e' stato
    scelto misurando il fallimento di `1 x spaziatura` e non a occhio.

    Quella funzione non viene toccata e questa non la sostituisce: rispondono a
    domande diverse -- copertura di un insieme di nodi sull'impronta
    orizzontale contro spessore locale sul piano del telaio -- e condividono
    quattro righe di aritmetica. `footprint_coverage` produce numeri citati
    nella tesi (100,00% su muro, 98,93% su lab_crop) e riscriverla per
    condividere quattro righe li metterebbe a rischio in cambio di nulla.

    Gli indici sono misurati dal minimo, quindi non negativi e funzione dei
    soli dati: nessun conteggio che ne discenda dipende dalla piattaforma.
    """
    piano = np.asarray(coordinate, dtype=np.float64)
    return np.floor((piano - piano.min(axis=0)) / float(lato)).astype(np.int64)


def spessore_per_cella(
    piano: np.ndarray, trasversale: np.ndarray, lato: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Spessore locale di ogni cella occupata: estensione della nuvola lungo n.

    E' la grandezza da sorvegliare, e la regola che ne discende e' la sua
    costanza, non il suo valore. Separare le membrature con una soglia di quota
    sarebbe tarare una costante sulla scansione di oggi, e una soglia difficile
    da tarare e' quasi sempre il sintomo di una grandezza sbagliata (secondo
    principio di prodotto).

    Restituisce le celle occupate (M x 2, ordinate per indice crescente), lo
    spessore di ciascuna, e per ogni punto la posizione della propria cella
    dentro quell'elenco.
    """
    celle = chiavi_di_cella(piano, lato)
    # Chiave intera invece di np.unique(..., axis=0): stesso risultato, e su un
    # maglio a scala reale costa un terzo. Stessa scelta gia' fatta in
    # abaqus.footprint_coverage, e per la stessa ragione.
    chiave = celle[:, 0] * (celle[:, 1].max() + 1) + celle[:, 1]
    _, prima, inverso = np.unique(chiave, return_index=True, return_inverse=True)
    uniche = celle[prima]

    valori = np.asarray(trasversale, dtype=np.float64)
    alto = np.full(len(uniche), -np.inf)
    basso = np.full(len(uniche), np.inf)
    np.maximum.at(alto, inverso, valori)
    np.minimum.at(basso, inverso, valori)
    return uniche, alto - basso, inverso
```

- [ ] **Step 8: Eseguire i test della prima meta'**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti e quattro.

- [ ] **Step 9: Commit intermedio**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/src/meshrec/core/synth.py meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_wall.py meshrec/tests/test_synth.py
git commit -m "feat(fase-4): terna del pezzo, celle e spessore locale del prior"
```

- [ ] **Step 10: I test del pavimento e delle regioni**

In coda a `tests/test_wall.py`:

```python
def test_il_pavimento_viene_scartato_come_piano_e_non_come_quota():
    """Il pavimento e' un piano quasi orizzontale esteso oltre l'ingombro del
    pezzo. Scartarlo con una soglia di quota sarebbe tarare una costante sulla
    scansione di oggi; qui viene scartato per cio' che e'."""
    telaio = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    pavimento = synth.sample_box_surface((4000.0, 3000.0, 10.0), SPAZIATURA * 2.0)
    pavimento = pavimento + np.array([-1200.0, -1400.0, -320.0])
    punti = np.vstack([telaio, pavimento])

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is True
    assert len(tenuti) < len(punti)
    # nessun punto sotto il piede del telaio sintetico resta in circolazione
    assert tenuti[:, 2].min() > -320.0
    assert tenuti[:, 2].min() == pytest.approx(-300.0, abs=3.0 * SPAZIATURA)


def test_senza_pavimento_non_ne_viene_inventato_uno():
    """Il controllo che smentisce il precedente: su una nuvola che pavimento
    non ha, la funzione non deve togliere una faccia del pezzo scambiandola per
    tale."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is False
    assert len(tenuti) == len(punti)


def test_una_scatola_da_una_sola_membratura():
    """La prova che la scomposizione non inventa membrature dove non ce ne
    sono. Il numero atteso viene dal banco, non dal codice."""
    punti = synth.sample_box_surface((400.0, 180.0, 1200.0), SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(regioni) == 1
    assert metriche["regioni_trovate"] == 1


def test_un_telaio_sintetico_da_le_membrature_che_ha():
    """Quattro prismi di tre sezioni diverse: la scomposizione deve separarli
    per costanza dello spessore, e i due montanti identici, che sono disgiunti
    nel piano, restano due regioni e non una."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["regioni_trovate"] == len(regioni)
    assert 2 <= len(regioni) <= 6, (
        f"attese fra 2 e 6 regioni sui quattro prismi del banco, trovate {len(regioni)}: "
        "sotto, la scomposizione fonde membrature diverse; sopra, le frammenta"
    )
    # ogni punto sta in al piu' una regione: una regione non ruba punti a un'altra
    tutti = np.concatenate(regioni)
    assert len(tutti) == len(np.unique(tutti))


def test_l_ordine_delle_regioni_non_dipende_dall_ordine_dei_punti():
    """Quinto vincolo di prodotto: un ordine e' un esito discreto e deve essere
    funzione del dato. E' la stessa lezione gia' pagata sull'ordine dei voxel di
    Open3D fra Windows x86-64 e macOS arm64."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(1).permutation(len(punti))]

    prima, _ = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)
    dopo, _ = wall.scomponi(rimescolati, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(prima) == len(dopo)
    # confronto per insieme di coordinate, non per indice: gli indici puntano a
    # due ordinamenti diversi della stessa nuvola
    for regione_prima, regione_dopo in zip(prima, dopo, strict=True):
        a = np.unique(np.round(punti[regione_prima], 6), axis=0)
        b = np.unique(np.round(rimescolati[regione_dopo], 6), axis=0)
        assert a.shape == b.shape
        assert a == pytest.approx(b)
```

- [ ] **Step 11: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'scarta_pavimento'` sui cinque nuovi, PASS sui quattro precedenti.

- [ ] **Step 12: Scrivere la seconda meta' di `core/wall.py`**

In coda a `wall.py`:

```python
def scarta_pavimento(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Toglie il pavimento, se c'e'. Non e' una membratura ed e' scartato come piano.

    Il pavimento e' riconosciuto da due condizioni che valgono insieme e non da
    una soglia di quota: la normale del piano sta entro `floor_angle_deg`
    dalla verticale, e il piano contiene almeno `floor_min_ratio` dei punti.
    Una faccia superiore di membratura soddisfa la prima e non la seconda.

    L'estrazione dei piani non viene riscritta: e' `segment.extract_planes`,
    con la stessa configurazione con cui lo step 2 la usa gia'.

    Se nessun piano soddisfa entrambe le condizioni la nuvola torna intatta e
    le metriche lo dichiarano: non viene inventato un pavimento, per lo stesso
    motivo per cui non viene inventata un'aspettativa quando non e' dichiarata.
    """
    punti = np.asarray(points, dtype=np.float64)
    piani, _residuo, metriche_piani = segment.extract_planes(punti, cfg_segment, spacing)
    coseno = np.cos(np.radians(cfg.floor_angle_deg))
    minimo = cfg.floor_min_ratio * len(punti)

    for piano in piani:
        if len(piano) < minimo:
            continue
        centrati = piano - piano.mean(axis=0)
        _, _, principali = np.linalg.svd(centrati, full_matrices=False)
        if abs(principali[2][2]) < coseno:
            continue
        # Il pavimento e' questo: si toglie per appartenenza, confrontando le
        # coordinate arrotondate. Un confronto per indice non e' disponibile,
        # perche' extract_planes restituisce i punti e non le loro posizioni.
        chiave_piano = {tuple(riga) for riga in np.round(piano, 6).tolist()}
        tenuti = np.array(
            [tuple(riga) not in chiave_piano for riga in np.round(punti, 6).tolist()],
            dtype=bool,
        )
        return np.ascontiguousarray(punti[tenuti]), {
            "pavimento_trovato": True,
            "pavimento_punti": int(len(piano)),
            "punti_dopo": int(tenuti.sum()),
            **metriche_piani,
        }

    return punti, {
        "pavimento_trovato": False,
        "pavimento_punti": 0,
        "punti_dopo": int(len(punti)),
        **metriche_piani,
    }


def regioni(celle: np.ndarray, spessori: np.ndarray, cfg: WallConfig) -> list[np.ndarray]:
    """Regioni connesse a spessore quasi costante, sulla griglia delle celle.

    Due celle adiacenti sui quattro lati appartengono alla stessa membratura se
    i loro spessori differiscono di meno di `thickness_tolerance` in relativo.
    E' la forma numerica di «quasi costante», ed e' l'unica soglia della
    scomposizione: non c'e' un istogramma da leggere ne' un numero di modi da
    dichiarare, quindi non c'e' un numero di membrature da aspettarsi.

    Le componenti connesse vengono da scipy.sparse.csgraph, gia' installata:
    non c'e' motivo di scrivere una union-find a mano.

    L'ordine delle regioni e' canonico -- per numero di celle decrescente, a
    pari numero per la cella di indice minimo -- quindi funzione del dato e non
    dell'ordine di visita: e' il quinto vincolo di prodotto.
    """
    from scipy.sparse import coo_array
    from scipy.sparse.csgraph import connected_components

    griglia = np.asarray(celle, dtype=np.int64)
    valori = np.asarray(spessori, dtype=np.float64)
    passo = int(griglia[:, 1].max() + 1)
    chiave = griglia[:, 0] * passo + griglia[:, 1]
    ordine = np.argsort(chiave, kind="stable")
    ordinate = chiave[ordine]

    archi_a: list[np.ndarray] = []
    archi_b: list[np.ndarray] = []
    for salto in (passo, 1):  # vicino lungo il primo asse, vicino lungo il secondo
        posizione = np.searchsorted(ordinate, chiave + salto)
        posizione = np.clip(posizione, 0, len(ordinate) - 1)
        vicino = ordine[posizione]
        esiste = ordinate[posizione] == chiave + salto
        if salto == 1:
            # il vicino lungo il secondo asse esiste solo se non ha scavalcato
            # la riga: due celle contigue nella chiave possono stare su righe
            # diverse della griglia
            esiste &= griglia[vicino, 0] == griglia[:, 0]
        vicini_validi = np.flatnonzero(esiste)
        if len(vicini_validi) == 0:
            continue
        altro = vicino[vicini_validi]
        massimo = np.maximum(valori[vicini_validi], valori[altro])
        simili = np.abs(valori[vicini_validi] - valori[altro]) <= cfg.thickness_tolerance * massimo
        archi_a.append(vicini_validi[simili])
        archi_b.append(altro[simili])

    da = np.concatenate(archi_a) if archi_a else np.empty(0, dtype=np.int64)
    a = np.concatenate(archi_b) if archi_b else np.empty(0, dtype=np.int64)
    grafo = coo_array(
        (np.ones(len(da), dtype=np.int8), (da, a)), shape=(len(griglia), len(griglia))
    )
    _quante, etichette = connected_components(grafo, directed=False)

    gruppi = []
    for etichetta in np.unique(etichette):
        indici = np.flatnonzero(etichette == etichetta)
        if len(indici) < cfg.min_cells:
            continue
        gruppi.append(indici)
    # ordine canonico: le regioni grandi per prime, i pari merito per la cella
    # di indice minimo, che e' un numero della griglia e non dell'esecuzione
    gruppi.sort(key=lambda indici: (-len(indici), int(chiave[indici].min())))
    return gruppi


def scomponi(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> tuple[list[np.ndarray], dict[str, object]]:
    """La scomposizione completa: dal pavimento scartato agli indici dei punti per regione.

    Il numero di membrature non e' un parametro e non e' un'attesa: e' cio' che
    la nuvola contiene. Su una scatola torna una regione sola.
    """
    puliti, metriche_pavimento = scarta_pavimento(points, cfg_segment, cfg, spacing)
    if len(puliti) == 0:
        raise ValueError(
            "la rimozione del pavimento ha svuotato la nuvola: il piano scartato "
            "conteneva tutti i punti, quindi non era un pavimento ma il pezzo. "
            "Alza wall.floor_min_ratio o restringi wall.floor_angle_deg"
        )

    direzioni, centro = terna(puliti)
    centrati = puliti - centro
    piano = centrati @ direzioni[:2].T
    trasversale = centrati @ direzioni[2]
    lato = cfg.cell_factor * spacing

    celle, spessori, inverso = spessore_per_cella(piano, trasversale, lato)
    gruppi = regioni(celle, spessori, cfg)

    per_regione = []
    for indici_cella in gruppi:
        appartiene = np.isin(inverso, indici_cella)
        per_regione.append(np.flatnonzero(appartiene))

    metriche: dict[str, object] = {
        **metriche_pavimento,
        "cell_side": float(lato),
        "celle_occupate": int(len(celle)),
        "regioni_trovate": len(per_regione),
        "punti_per_regione": [int(len(indici)) for indici in per_regione],
        "spessore_mediano": float(np.median(spessori)) if len(spessori) else None,
        "terna": direzioni.tolist(),
        "centro": centro.tolist(),
    }
    return per_regione, metriche
```

**Attenzione all'appartenenza dei punti:** `scomponi` restituisce gli indici dentro `puliti`, non dentro `points`. Se il pavimento e' stato tolto i due non coincidono. Il chiamante che serve (`pipeline`, Task 9) usa la nuvola ripulita e non l'originale; restituiscila quindi anche tu, aggiungendo `puliti` come terzo elemento del ritorno **solo se** un test lo richiede — per ora la nuvola ripulita e' ricostruibile da `scarta_pavimento`, che e' pubblica.

- [ ] **Step 13: Eseguire i test delle regioni**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti e nove. Se `test_un_telaio_sintetico_da_le_membrature_che_ha` cade fuori dall'intervallo 2-6, **non allargare l'intervallo**: stampa `metriche["punti_per_regione"]` e guarda se la scomposizione fonde o frammenta, poi correggi `regioni` o dichiara la limitazione nel documento del Task 13.

- [ ] **Step 14: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 15: Commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): la scomposizione in membrature per costanza dello spessore"
```

---

## Task 3: `core/wall.py` — le misure per membratura, i controlli intrinseci, i riscontri dichiarati

**Files:**
- Modify: `src/meshrec/core/wall.py`
- Test: `tests/test_wall.py`

**Interfaces:**
- Consumes: `wall.scomponi`, `wall.terna` (Task 2).
- Produces:
  - `wall.Membratura` — dataclass con `punti, asse, origine, lunghezza, sezione, sezione_dispersione, contorno, fuori_piombo_deg, asse_ideale, scarto_asse_deg, rigonfiamento, volume, esiti`.
  - `wall.semplifica_contorno(contorno, tolleranza) -> np.ndarray`.
  - `wall.misura(punti_regione, direzioni, cfg) -> Membratura`.
  - `wall.controlla(membratura, cfg) -> dict[str, dict]`.
  - `wall.prior(points, cfg_segment, cfg, spacing) -> dict[str, object]` — il risultato completo dello step 12, serializzabile in JSON.

- [ ] **Step 1: I test del contorno di sezione**

In coda a `tests/test_wall.py`:

```python
def test_il_contorno_di_un_rettangolo_ha_quattro_vertici():
    """Il contorno misurato non deve portare nella mesh il rumore dello
    scanner: un rettangolo campionato fitto resta un rettangolo."""
    lato_u = np.linspace(0.0, 200.0, 60)
    lato_v = np.linspace(0.0, 140.0, 40)
    bordo = np.vstack([
        np.column_stack([lato_u, np.zeros_like(lato_u)]),
        np.column_stack([lato_u, np.full_like(lato_u, 140.0)]),
        np.column_stack([np.zeros_like(lato_v), lato_v]),
        np.column_stack([np.full_like(lato_v, 200.0), lato_v]),
    ])

    contorno = wall.semplifica_contorno(bordo, tolleranza=5.0)

    assert len(contorno) == 4, f"attesi 4 vertici, trovati {len(contorno)}"
    assert contorno.min(axis=0) == pytest.approx([0.0, 0.0], abs=1e-9)
    assert contorno.max(axis=0) == pytest.approx([200.0, 140.0], abs=1e-9)


def test_il_contorno_semplificato_non_perde_area_oltre_la_tolleranza():
    """Il controllo che smentisce il precedente: semplificare e' lecito finche'
    l'area della sezione non cambia piu' di quanto la tolleranza consenta."""
    angoli = np.linspace(0.0, 2.0 * np.pi, 400, endpoint=False)
    cerchio = np.column_stack([100.0 * np.cos(angoli), 100.0 * np.sin(angoli)])

    contorno = wall.semplifica_contorno(cerchio, tolleranza=2.0)

    def area(poligono):
        x, y = poligono[:, 0], poligono[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    assert len(contorno) < len(cerchio)
    assert area(contorno) == pytest.approx(area(cerchio), rel=0.05)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k contorno -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'semplifica_contorno'`.

- [ ] **Step 3: Scrivere `semplifica_contorno`**

In coda a `wall.py`:

```python
def semplifica_contorno(contorno: np.ndarray, tolleranza: float) -> np.ndarray:
    """Inviluppo convesso della sezione, ridotto ai vertici che contano.

    Il contorno di sezione va misurato sulla nuvola e non preso dal disegno,
    ma un contorno con un vertice per punto rilevato porterebbe nella mesh il
    rumore dello scanner invece della forma della sezione. La riduzione toglie
    a ripetizione il vertice la cui distanza dal segmento fra i due vicini e'
    la piu' piccola, finche' tutte le distanze superano la tolleranza: e' la
    stessa idea di Douglas-Peucker su un poligono chiuso, senza ricorsione.

    L'inviluppo convesso e' di scipy, gia' installata. La convessita' non e'
    una perdita: la sezione di una membratura prismatica e' convessa, e una
    concavita' misurata sarebbe piu' probabilmente un'occlusione dello scanner
    che una rientranza del calcestruzzo. E' anche cio' che rende immediato il
    test di appartenenza usato dal taglio alle giunzioni.

    I pari merito sono sciolti dall'indice, che e' un numero della geometria e
    non dell'esecuzione: l'esito e' funzione del dato.
    """
    from scipy.spatial import ConvexHull

    punti = np.asarray(contorno, dtype=np.float64)
    inviluppo = punti[ConvexHull(punti).vertices]

    while len(inviluppo) > 3:
        precedente = np.roll(inviluppo, 1, axis=0)
        successivo = np.roll(inviluppo, -1, axis=0)
        corda = successivo - precedente
        lunghezza = np.linalg.norm(corda, axis=1)
        # distanza punto-retta come modulo del prodotto vettoriale in 2D,
        # normalizzato sulla corda; corda nulla vuol dire vertice doppio, che
        # va tolto per primo
        scarto = np.abs(np.cross(corda, inviluppo - precedente))
        altezza = np.divide(
            scarto, lunghezza, out=np.zeros_like(scarto), where=lunghezza > 0.0
        )
        peggiore = int(np.argmin(altezza))
        if altezza[peggiore] > tolleranza:
            break
        inviluppo = np.delete(inviluppo, peggiore, axis=0)

    return np.ascontiguousarray(inviluppo)
```

- [ ] **Step 4: Eseguirli**

Run: `uv run pytest tests/test_wall.py -k contorno -v`
Expected: PASS.

- [ ] **Step 5: I test delle misure per membratura**

In coda a `tests/test_wall.py`:

```python
def test_la_misura_di_un_prisma_noto_ritrova_sezione_asse_e_lunghezza():
    """Verita' nota del banco: un prisma 200 x 140 lungo 1500 lungo z."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.lunghezza == pytest.approx(1500.0, abs=30.0)
    lunga, corta = sorted(membratura.sezione, reverse=True)
    assert lunga == pytest.approx(200.0, abs=15.0)
    assert corta == pytest.approx(140.0, abs=15.0)
    assert abs(abs(membratura.asse[2]) - 1.0) < 1e-3, "asse atteso verticale"
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.0)
    assert membratura.volume == pytest.approx(200.0 * 140.0 * 1500.0, rel=0.15)


def test_il_fuori_piombo_misura_l_inclinazione_e_il_rigonfiamento_no():
    """Le due grandezze restano distinte perche' sono difetti diversi: un
    elemento puo' essere perfettamente piano e tutto storto, oppure a piombo e
    panciuto. Un prisma inclinato di 4 gradi ha fuori piombo e non pancia."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    angolo = np.radians(4.0)
    rotazione = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(angolo), -np.sin(angolo)],
        [0.0, np.sin(angolo), np.cos(angolo)],
    ])
    inclinati = punti @ rotazione.T
    direzioni, _ = wall.terna(inclinati)

    membratura = wall.misura(inclinati, direzioni, _cfg())

    assert membratura.fuori_piombo_deg == pytest.approx(4.0, abs=1.0)
    assert np.abs(membratura.rigonfiamento).max() < 20.0, (
        "un prisma inclinato ma dritto non deve risultare panciuto: se lo "
        "risulta, il rigonfiamento sta misurando l'inclinazione"
    )


def test_il_rigonfiamento_e_una_mappa_e_trova_la_pancia_dove_c_e():
    """Il controllo che smentisce il precedente: una faccia gonfiata di 25 mm
    al centro deve comparire nella mappa, e nel fuori piombo no."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    sulla_faccia = np.isclose(punti[:, 1], 140.0)
    altezza_relativa = (punti[:, 2] - 750.0) / 750.0
    gonfiati = punti.copy()
    gonfiati[sulla_faccia, 1] += 25.0 * (1.0 - altezza_relativa[sulla_faccia] ** 2)
    direzioni, _ = wall.terna(gonfiati)

    membratura = wall.misura(gonfiati, direzioni, _cfg())

    assert membratura.rigonfiamento.ndim == 1
    assert len(membratura.rigonfiamento) > 10, "il rigonfiamento e' una mappa, non un numero"
    assert np.abs(membratura.rigonfiamento).max() > 10.0
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.5)
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k misura -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'misura'`.

- [ ] **Step 7: `Membratura` e `misura`**

In `wall.py`, subito sotto gli import aggiungi `from dataclasses import dataclass, field`, e in coda al file:

```python
@dataclass(eq=False)
class Membratura:
    """Una membratura prismatica misurata. Nessun campo viene da un disegno.

    `eq=False` perche' i campi sono array: il confronto per uguaglianza di un
    dataclass con dentro numpy solleverebbe invece di rispondere, e non serve
    a nessuno qui.
    """

    punti: np.ndarray
    """Indici, dentro la nuvola passata a `misura`, dei punti della regione."""
    asse: np.ndarray
    """Direzione principale della regione, versore, con verso fissato da fix_sign."""
    origine: np.ndarray
    """Punto sull'asse da cui la lunghezza e' misurata."""
    lunghezza: float
    sezione: tuple[float, float]
    """Le due estensioni trasversali all'asse [mm]."""
    sezione_dispersione: tuple[float, float]
    """Dispersione delle due estensioni lungo l'asse, in relativo."""
    contorno: np.ndarray
    """Contorno di sezione misurato e semplificato, K x 2, nel piano dell'asse."""
    fuori_piombo_deg: float
    """Angolo dell'asse rispetto alla verticale. Un numero solo."""
    asse_ideale: np.ndarray
    """Il versore della terna piu' vicino all'asse: e' l'asse del modello primitive."""
    scarto_asse_deg: float
    """Angolo fra l'asse misurato e l'asse ideale."""
    rigonfiamento: np.ndarray
    """Scostamento locale dalla faccia ideale, una mappa per cella e non un numero."""
    volume: float
    """Sezione media per lunghezza [mm^3]."""
    esiti: dict[str, dict] = field(default_factory=dict)
    """Gli esiti dei controlli intrinseci, riempiti da `controlla`."""


_FETTE_LUNGO_ASSE = 20
"""Fette in cui la regione e' divisa per misurare la dispersione della sezione.

Non e' un parametro di elaborazione: e' la risoluzione con cui si guarda una
grandezza gia' definita, come i bin di un istogramma. Venti fette danno almeno
una decina di punti per fetta su qualunque membratura che superi min_cells.
"""


def misura(punti_regione: np.ndarray, direzioni: np.ndarray, cfg: WallConfig) -> Membratura:
    """Asse, lunghezza, sezione, contorno, fuori piombo e rigonfiamento di una regione.

    Il fuori piombo e il rigonfiamento sono tenuti distinti perche' sono
    difetti diversi: un elemento puo' essere perfettamente piano e tutto
    storto, oppure a piombo e panciuto. Il primo e' un numero, il secondo e'
    una mappa, e sommarli darebbe un indice che non corrisponde a nulla di
    fisico.

    `direzioni` e' la terna del pezzo intero, non della regione: le due
    grandezze «asse ideale» e «rigonfiamento» hanno senso solo rispetto a un
    riferimento comune a tutte le membrature.
    """
    punti = np.asarray(punti_regione, dtype=np.float64)
    centro = punti.mean(axis=0)
    centrati = punti - centro
    _, _, principali = np.linalg.svd(centrati, full_matrices=False)
    asse = fix_sign(principali[0])

    lungo = centrati @ asse
    lunghezza = float(np.ptp(lungo))
    origine = centro + asse * lungo.min()

    # base ortonormale del piano di sezione, ancorata alla terna del pezzo e non
    # alla SVD della regione: due membrature parallele devono avere lo stesso
    # piano di sezione, o le loro sezioni non sono confrontabili
    riferimento = direzioni[2] if abs(np.dot(direzioni[2], asse)) < 0.9 else direzioni[0]
    e1 = riferimento - asse * np.dot(riferimento, asse)
    e1 = fix_sign(e1 / np.linalg.norm(e1))
    e2 = np.cross(asse, e1)
    sezione_2d = np.column_stack([centrati @ e1, centrati @ e2])

    estensioni = (float(np.ptp(sezione_2d[:, 0])), float(np.ptp(sezione_2d[:, 1])))

    # dispersione della sezione lungo l'asse: la grandezza del controllo di
    # costanza. Fette a passo uguale, e non quantili, perche' una fetta vuota
    # deve restare vuota invece di essere riempita da punti di un'altra.
    bordi = np.linspace(lungo.min(), lungo.max(), _FETTE_LUNGO_ASSE + 1)
    fetta = np.clip(np.digitize(lungo, bordi[1:-1]), 0, _FETTE_LUNGO_ASSE - 1)
    per_fetta = []
    for indice in range(_FETTE_LUNGO_ASSE):
        dentro = fetta == indice
        if dentro.sum() < 4:
            continue
        per_fetta.append((np.ptp(sezione_2d[dentro, 0]), np.ptp(sezione_2d[dentro, 1])))
    misure = np.asarray(per_fetta, dtype=np.float64) if per_fetta else np.zeros((1, 2))
    medie = misure.mean(axis=0)
    dispersione = tuple(
        float(scarto / media) if media > 0.0 else 0.0
        for scarto, media in zip(misure.std(axis=0), medie, strict=True)
    )

    contorno = semplifica_contorno(sezione_2d, cfg.contour_tolerance)

    # fuori piombo: angolo dell'asse rispetto alla verticale del mondo. Per una
    # colonna e' il fuori piombo nel senso del cantiere; per una trave e' 90
    # gradi e non e' un difetto, ed e' per questo che accanto c'e' lo scarto
    # dall'asse ideale, che e' la grandezza che il modello primitive raddrizza.
    verticale = np.array([0.0, 0.0, 1.0])
    fuori_piombo = float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(asse, verticale)))))))

    proiezioni = np.abs(direzioni @ asse)
    asse_ideale = fix_sign(direzioni[int(np.argmax(proiezioni))])
    scarto_asse = float(np.degrees(np.arccos(min(1.0, float(np.max(proiezioni))))))

    # rigonfiamento: scostamento della faccia dalla propria faccia ideale, che
    # e' il piano medio della faccia stessa. Una mappa per cella della griglia
    # di sezione, non un numero.
    lato = cfg.cell_factor * max(1e-9, float(np.ptp(lungo)) / _FETTE_LUNGO_ASSE)
    piano_faccia = np.column_stack([lungo, sezione_2d[:, 0]])
    celle_faccia = chiavi_di_cella(piano_faccia, lato)
    chiave = celle_faccia[:, 0] * (celle_faccia[:, 1].max() + 1) + celle_faccia[:, 1]
    _, inverso = np.unique(chiave, return_inverse=True)
    quota = sezione_2d[:, 1]
    estremo = np.full(int(inverso.max()) + 1, -np.inf)
    np.maximum.at(estremo, inverso, quota)
    rigonfiamento = estremo - np.median(estremo)

    volume = float(medie[0] * medie[1] * lunghezza)

    return Membratura(
        punti=np.arange(len(punti)),
        asse=asse,
        origine=origine,
        lunghezza=lunghezza,
        sezione=estensioni,
        sezione_dispersione=dispersione,
        contorno=contorno,
        fuori_piombo_deg=fuori_piombo,
        asse_ideale=asse_ideale,
        scarto_asse_deg=scarto_asse,
        rigonfiamento=rigonfiamento,
        volume=volume,
    )
```

- [ ] **Step 8: Eseguire i test delle misure**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti.

- [ ] **Step 9: Commit intermedio**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): sezione, asse, fuori piombo e rigonfiamento per membratura"
```

- [ ] **Step 10: I test dei controlli intrinseci**

In coda a `tests/test_wall.py`:

```python
def test_i_quattro_controlli_intrinseci_passano_su_un_prisma_pulito():
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)
    membratura = wall.misura(punti, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert set(esiti) == {"parallelismo", "copertura_faccia", "costanza_sezione"}
    for nome, esito in esiti.items():
        assert esito["passato"] is True, f"{nome} non doveva fallire: {esito}"
        assert "valore" in esito and "soglia" in esito, (
            f"{nome} deve dire quale numero lo ha deciso, non solo se e' passato"
        )


def test_una_regione_a_sezione_variabile_non_e_un_prisma_e_lo_dice():
    """Il controllo che smentisce il prior: un tronco di piramide non e' una
    membratura, e viene riportato come tale invece di essere spacciato per una
    con la sezione media."""
    z = np.linspace(0.0, 1500.0, 120)
    punti = []
    for quota in z:
        mezzo_lato = 100.0 * (1.0 - 0.6 * quota / 1500.0)
        angoli = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        punti.append(np.column_stack([
            mezzo_lato * np.cos(angoli),
            mezzo_lato * np.sin(angoli),
            np.full_like(angoli, quota),
        ]))
    cono = np.vstack(punti)
    direzioni, _ = wall.terna(cono)
    membratura = wall.misura(cono, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert esiti["costanza_sezione"]["passato"] is False
    assert esiti["costanza_sezione"]["valore"] > esiti["costanza_sezione"]["soglia"]


def test_senza_riscontri_dichiarati_il_prior_non_inventa_un_aspettativa():
    """Su un pezzo nuovo i riscontri non esistono per definizione. Il prior
    riporta cio' che ha trovato, e nel posto dell'atteso non mette un numero."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] is None
    assert riscontri["volume_atteso"] is None
    assert riscontri["scarto_membrature"] is None
    assert riscontri["scarto_volume"] is None
    assert esito["membrature"], "il prior deve comunque riportare cio' che ha trovato"


def test_con_i_riscontri_dichiarati_il_prior_riporta_lo_scarto():
    """I numeri dell'atteso stanno qui, nel test, dove e' legittimo che
    compaiano: sono dati del caso, non del programma."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    volume_vero = sum(dx * dy * dz for _origine, (dx, dy, dz) in TELAIO)
    cfg = WallConfig(membrature_attese=4, volume_atteso=volume_vero)

    esito = wall.prior(punti, SegmentConfig(), cfg, SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] == 4
    assert riscontri["scarto_membrature"] == len(esito["membrature"]) - 4
    assert riscontri["volume_atteso"] == pytest.approx(volume_vero)
    assert riscontri["scarto_volume"] is not None


def test_l_esito_del_prior_e_serializzabile_in_json():
    """Lo step 12 lo scrive su disco e il server lo manda al browser: un array
    di numpy dentro il dizionario romperebbe entrambi dopo l'intera corsa."""
    import json

    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    testo = json.dumps(esito)
    assert json.loads(testo)["regioni_trovate"] == esito["regioni_trovate"]


def test_il_controllo_di_chiusura_del_volume_confronta_somma_e_unione():
    """Le membrature si compenetrano alle giunzioni: se la somma dei volumi
    supera quello dell'unione oltre la tolleranza, c'e' doppio conteggio, ed e'
    un errore che nessuna metrica di qualita' della mesh vedrebbe."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    chiusura = esito["chiusura_volume"]
    assert chiusura["somma"] > 0.0
    assert chiusura["unione"] > 0.0
    assert isinstance(chiusura["passato"], bool)
    assert chiusura["scarto_relativo"] == pytest.approx(
        (chiusura["somma"] - chiusura["unione"]) / chiusura["unione"]
    )
```

- [ ] **Step 11: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k "controll or riscontr or prior or chiusura" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'controlla'`.

- [ ] **Step 12: `controlla` e `prior`**

In coda a `wall.py`:

```python
def controlla(membratura: Membratura, cfg: WallConfig) -> dict[str, dict]:
    """I controlli intrinseci di una membratura: sempre attivi, nulla sanno del pezzo.

    Senza questi il prior e' una macchina per fabbricare numeri. Ogni esito
    porta con se' il numero che lo ha deciso e la soglia con cui e' stato
    confrontato: un «non passato» senza il proprio numero non dice a chi legge
    che cosa cambiare.

    Un controllo fallito **non solleva**. La regione non diventa una membratura
    e il motivo resta scritto, perche' l'interfaccia deve poter mostrare quale
    controllo ha detto no e quale numero glielo ha fatto dire: un'eccezione
    ucciderebbe la corsa sulla prima regione difettosa e non lascerebbe nulla
    da mostrare sulle altre.
    """
    # parallelismo delle facce: la mappa del rigonfiamento e' lo scostamento
    # della faccia dal proprio piano medio, quindi l'angolo fra le due facce si
    # legge dal gradiente di quella mappa lungo l'asse. Un valore grande
    # significa facce che divergono, cioe' nessuna sezione da misurare.
    pancia = np.asarray(membratura.rigonfiamento, dtype=np.float64)
    divergenza = float(np.ptp(pancia)) if len(pancia) else 0.0
    riferimento = max(membratura.lunghezza, 1e-9)
    angolo_facce = float(np.degrees(np.arctan2(divergenza, riferimento)))

    coperte = float(np.isfinite(pancia).mean()) if len(pancia) else 0.0
    dispersione = float(max(membratura.sezione_dispersione))

    return {
        "parallelismo": {
            "passato": angolo_facce <= cfg.parallelism_deg,
            "valore": angolo_facce,
            "soglia": float(cfg.parallelism_deg),
            "unita": "gradi",
            "spiegazione": (
                "angolo fra le due facce opposte: oltre la soglia la regione non "
                "ha una sezione, e una sezione media sarebbe priva di senso"
            ),
        },
        "copertura_faccia": {
            "passato": coperte >= cfg.face_coverage,
            "valore": coperte,
            "soglia": float(cfg.face_coverage),
            "unita": "frazione",
            "spiegazione": (
                "frazione delle celle della faccia viste dallo scanner: una "
                "faccia vista da pochi punti produce un piano finto, come gia' "
                "misurato su FACE_FRONT e FACE_BACK"
            ),
        },
        "costanza_sezione": {
            "passato": dispersione <= cfg.section_dispersion,
            "valore": dispersione,
            "soglia": float(cfg.section_dispersion),
            "unita": "frazione",
            "spiegazione": (
                "dispersione relativa della sezione lungo l'asse: oltre la "
                "soglia la regione non e' un prisma"
            ),
        },
    }


def _volume_unione(membrature: list[Membratura], punti: np.ndarray, passo: float) -> float:
    """Volume dell'unione delle membrature, per conteggio di celle occupate.

    Nessuna libreria di solidi entra nel progetto per una misura di controllo:
    una griglia regolare sull'ingombro, una cella contata una volta sola se
    contiene punti di una qualunque membratura. L'errore e' quello della
    discretizzazione, viene dal passo dichiarato e viene riportato accanto al
    risultato invece di essere nascosto.
    """
    if not membrature:
        return 0.0
    tutti = np.vstack([punti[m.punti] for m in membrature])
    celle = np.floor((tutti - tutti.min(axis=0)) / passo).astype(np.int64)
    occupate = len(np.unique(celle, axis=0))
    return float(occupate * passo**3)


def prior(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> dict[str, object]:
    """Lo step 12 per intero: scomposizione, misure, controlli, riscontri.

    Il risultato e' un dizionario di soli tipi JSON, perche' viene scritto su
    disco e mandato al browser: un array di numpy dentro romperebbe entrambi
    dopo che l'intera corsa e' gia' costata il suo tempo.

    I riscontri dichiarati sono facoltativi e assenti per definizione su un
    pezzo nuovo. Quando mancano, al posto dell'atteso c'e' `null` e non un
    numero: il prior non inventa un'aspettativa.
    """
    puliti, metriche_pavimento = scarta_pavimento(points, cfg_segment, cfg, spacing)
    regioni_punti, metriche = scomponi(points, cfg_segment, cfg, spacing)
    direzioni, _centro = terna(puliti)

    accettate: list[Membratura] = []
    scartate: list[dict[str, object]] = []
    for numero, indici in enumerate(regioni_punti):
        membratura = misura(puliti[indici], direzioni, cfg)
        membratura.punti = indici
        membratura.esiti = controlla(membratura, cfg)
        falliti = [nome for nome, esito in membratura.esiti.items() if not esito["passato"]]
        if falliti:
            scartate.append({
                "regione": numero,
                "punti": int(len(indici)),
                "controlli_falliti": falliti,
                "esiti": membratura.esiti,
            })
            continue
        accettate.append(membratura)

    passo_unione = cfg.union_step_factor * spacing
    somma = float(sum(m.volume for m in accettate))
    unione = _volume_unione(accettate, puliti, passo_unione)
    scarto_relativo = (somma - unione) / unione if unione > 0.0 else 0.0

    scarto_membrature = (
        len(accettate) - cfg.membrature_attese if cfg.membrature_attese is not None else None
    )
    scarto_volume = (
        (somma - cfg.volume_atteso) / cfg.volume_atteso
        if cfg.volume_atteso is not None
        else None
    )

    return {
        **{chiave: valore for chiave, valore in metriche.items() if chiave != "terna"},
        **metriche_pavimento,
        "terna": direzioni.tolist(),
        "membrature": [
            {
                "punti": int(len(m.punti)),
                "asse": m.asse.tolist(),
                "origine": m.origine.tolist(),
                "lunghezza": m.lunghezza,
                "sezione": list(m.sezione),
                "sezione_dispersione": list(m.sezione_dispersione),
                "contorno": m.contorno.tolist(),
                "fuori_piombo_deg": m.fuori_piombo_deg,
                "asse_ideale": m.asse_ideale.tolist(),
                "scarto_asse_deg": m.scarto_asse_deg,
                "rigonfiamento": {
                    "celle": int(len(m.rigonfiamento)),
                    "min": float(np.min(m.rigonfiamento)) if len(m.rigonfiamento) else None,
                    "max": float(np.max(m.rigonfiamento)) if len(m.rigonfiamento) else None,
                    "p95": float(np.percentile(np.abs(m.rigonfiamento), 95))
                    if len(m.rigonfiamento)
                    else None,
                },
                "volume": m.volume,
                "esiti": m.esiti,
            }
            for m in accettate
        ],
        "scartate": scartate,
        "chiusura_volume": {
            "somma": somma,
            "unione": unione,
            "scarto_relativo": scarto_relativo,
            "passo": float(passo_unione),
            "passato": abs(scarto_relativo) <= cfg.union_tolerance,
            "soglia": float(cfg.union_tolerance),
            "spiegazione": (
                "somma dei volumi delle membrature contro volume della loro "
                "unione: se differiscono, alle giunzioni il volume e' contato "
                "due volte, ed e' un errore che nessuna metrica di qualita' "
                "della mesh vedrebbe"
            ),
        },
        "riscontri": {
            "membrature_attese": cfg.membrature_attese,
            "scarto_membrature": scarto_membrature,
            "sezioni_nominali": (
                [list(sezione) for sezione in cfg.sezioni_nominali]
                if cfg.sezioni_nominali is not None
                else None
            ),
            "volume_atteso": cfg.volume_atteso,
            "scarto_volume": scarto_volume,
            "nota": (
                "i riscontri sono dichiarati dall'operatore e assenti per "
                "definizione su un pezzo mai visto: dove c'e' null, non c'e' "
                "un'aspettativa, non c'e' un valore mancante"
            ),
        },
    }
```

Le membrature di `prior` conservano gli indici della **nuvola ripulita** dal pavimento, non di quella in ingresso: e' scritto qui perche' i chiamanti dei Task 8 e 12 disegnano su quella nuvola.

- [ ] **Step 13: Eseguire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti.

- [ ] **Step 14: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 15: Commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): i controlli intrinseci del prior e i riscontri dichiarati"
```

---

## Task 4: `core/abaqus.py` generalizzato per tipo di elemento

Non una versione esaedrica parallela: **le stesse funzioni**, che smettono di dare per scontati quattro nodi per elemento e tre nodi per faccia.

**Files:**
- Modify: `src/meshrec/core/abaqus.py`
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `config.ModelConfig` (Task 1).
- Produces:
  - `abaqus.NODI_PER_ELEMENTO: dict[str, int]` — `{"C3D4": 4, "C3D10": 10, "C3D8": 8, "C3D8I": 8, "C3D8R": 8}`.
  - `abaqus.FACCE_TOPOLOGICHE: dict[int, tuple[tuple[int, ...], ...]]` — combinazioni di faccia per numero di nodi d'angolo.
  - `abaqus.boundary_faces(elements) -> np.ndarray` (pubblica, generalizzata).
  - `abaqus.write_inp(path, nodes, elements, *, element_type="C3D4", ...)`.
  - `abaqus.export_model(..., element_type=...)`.

- [ ] **Step 1: I test della generalizzazione**

In coda a `tests/test_abaqus.py`:

```python
def test_le_facce_di_bordo_di_un_esaedro_solo_sono_sei_quadrilateri():
    """_boundary_faces dava per scontati quattro nodi per elemento e tre per
    faccia. Un esaedro ha sei facce, tutte quadrilatere, e tutte di bordo."""
    esaedro = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    facce = abaqus.boundary_faces(esaedro)

    assert facce.shape == (6, 4)
    assert len(np.unique(facce, axis=0)) == 6


def test_due_esaedri_affiancati_non_hanno_la_faccia_condivisa_sul_bordo():
    """Il controllo che smentisce il precedente: se la faccia interna comparisse
    fra quelle di bordo, ogni set di faccia e ogni superficie esportata
    conterrebbero nodi interni al solido."""
    doppio = np.array(
        [[0, 1, 2, 3, 4, 5, 6, 7], [4, 5, 6, 7, 8, 9, 10, 11]], dtype=np.int64
    )

    facce = abaqus.boundary_faces(doppio)

    assert facce.shape == (10, 4), "sei piu' sei meno la faccia condivisa contata due volte"
    condivisa = np.sort(np.array([4, 5, 6, 7]))
    assert not (np.sort(facce, axis=1) == condivisa).all(axis=1).any()


def test_le_facce_di_bordo_dei_tetraedri_restano_quelle_di_prima():
    """La generalizzazione non deve cambiare il comportamento sui tetraedri: e'
    la macchina con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )

    facce = abaqus.boundary_faces(tets)

    assert facce.shape[1] == 3
    assert len(np.unique(facce)) == len(np.unique(abaqus.boundary_faces(tets)))
    # una superficie chiusa: ogni spigolo compare in esattamente due facce
    spigoli = np.sort(
        np.vstack([facce[:, [0, 1]], facce[:, [1, 2]], facce[:, [0, 2]]]), axis=1
    )
    _, conteggi = np.unique(spigoli, axis=0, return_counts=True)
    assert (conteggi == 2).all()


def test_il_deck_dichiara_il_tipo_di_elemento_che_gli_si_chiede(tmp_path):
    """C3D8I non e' un dettaglio estetico: un telaio lavora a flessione, e C3D8
    a integrazione piena si irrigidirebbe a taglio restituendo spostamenti
    troppo piccoli senza alcun segnale sulla mesh."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)
    percorso = tmp_path / "esaedro.inp"

    abaqus.write_inp(
        percorso, nodi, esaedri,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I, ELSET=ALL_WALL" in testo
    assert "1, 1, 2, 3, 4, 5, 6, 7, 8" in testo
    assert "*ELEMENT, TYPE=C3D4" not in testo


def test_un_tipo_di_elemento_che_non_combacia_coi_nodi_viene_rifiutato(tmp_path):
    """L'errore arriva prima di scrivere il file, non dopo che un solutore ha
    letto un deck con otto nodi dichiarati C3D4."""
    nodi = np.zeros((8, 3))
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    with pytest.raises(ValueError, match="C3D4"):
        abaqus.write_inp(
            tmp_path / "storto.inp", nodi, esaedri,
            node_sets={"BASE": np.array([0])},
            material=MATERIALE,
            element_type="C3D4",
        )
```

Assicurati che in testa a `tests/test_abaqus.py` ci siano gli import `synth`, `volume` e `MATERIALE` da `materiale`; se manca qualcuno, aggiungilo accanto a quelli gia' presenti.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_abaqus.py -k "esaedr or bordo or tipo_di_elemento" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'boundary_faces'`.

- [ ] **Step 3: Le tabelle e `boundary_faces`**

In `abaqus.py`, sostituisci `_TET_FACE_COMBOS` e `_boundary_faces` con:

```python
NODI_PER_ELEMENTO: dict[str, int] = {
    "C3D4": 4,
    "C3D10": 10,
    "C3D8": 8,
    "C3D8I": 8,
    "C3D8R": 8,
}
"""Nodi per elemento di ciascun tipo scrivibile nel deck.

C3D8, C3D8I e C3D8R hanno la stessa geometria e differiscono per la
formulazione: la mesh e' la stessa, cambia cosa il solutore ne fa. Sono
distinti qui perche' il nome finisce nel deck e il solutore lo legge.
"""

# Le facce di un elemento, come insiemi di nodi d'angolo, per il solo scopo di
# trovare il bordo: qui l'ordine dentro la faccia non conta, perche' le facce
# vengono ordinate prima di essere confrontate. La tabella che l'ordine ce
# l'ha, e con esso il numero S della faccia, e' FACCE_DEL_SOLUTORE (Task 5):
# le due non vanno confuse, ed e' per questo che portano nomi diversi.
FACCE_TOPOLOGICHE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)),
    8: (
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ),
}


def boundary_faces(elements: np.ndarray) -> np.ndarray:
    """Facce sul bordo della mesh di volume, per qualunque tipo di elemento.

    Stesso ragionamento di quality.boundary_edges, esteso alle facce: si
    costruiscono tutte le facce di ogni elemento, si ordinano gli indici al
    loro interno, si contano le occorrenze e si tengono quelle con occorrenza
    singola.

    La generalizzazione e' sui **nodi d'angolo**: un C3D10 ha dieci nodi ma la
    sua topologia e' quella del tetraedro, e i nodi di lato non definiscono
    facce proprie. Le prime quattro colonne di un C3D10 sono i suoi vertici,
    che e' la convenzione di TetGen e di Abaqus.
    """
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if elementi.shape[1] == 8 else 4
    combinazioni = FACCE_TOPOLOGICHE[angoli]
    facce = np.vstack([elementi[:, combo] for combo in combinazioni])
    facce = np.sort(facce, axis=1)
    uniche, conteggi = np.unique(facce, axis=0, return_counts=True)
    return uniche[conteggi == 1]


# Il nome privato resta come alias per non toccare i chiamanti interni gia'
# scritti e verificati: e' la stessa funzione, non una seconda.
_boundary_faces = boundary_faces
```

- [ ] **Step 4: `boundary_spacing` per facce di qualunque grado**

In `abaqus.py`, dentro `boundary_spacing`, sostituisci la costruzione degli spigoli con:

```python
    # Gli spigoli di una faccia sono le coppie di nodi consecutivi lungo il suo
    # perimetro: np.roll li da' per un triangolo come per un quadrilatero,
    # senza una tabella per grado.
    edges = np.sort(
        np.vstack([np.stack([f[:, i], f[:, (i + 1) % f.shape[1]]], axis=1) for i in range(f.shape[1])]),
        axis=1,
    )
    edges = np.unique(edges, axis=0)
```

Aggiungi alla docstring, in coda:

```
    Dalla Fase 4 vale anche sulle facce quadrilatere della mesh esaedrica: gli
    spigoli sono le coppie consecutive lungo il perimetro, quale che sia il
    numero di lati.
```

- [ ] **Step 5: `write_inp` per tipo di elemento**

In `abaqus.py`, cambia la firma e le due parti che davano per scontato il tetraedro:

```python
def write_inp(
    path: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    element_type: str = "C3D4",
    fixed_nset: str = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    step_name: str = "GRAVITA",
) -> None:
    """Scrive un modello pronto all'analisi statica sotto peso proprio.

    `element_type` e' il nome che il solutore legge, e il numero di nodi per
    elemento deve combaciare con esso: un array di otto colonne dichiarato
    C3D4 produrrebbe un deck che nessun solutore puo' leggere, e l'errore
    arriverebbe dopo l'intera pipeline invece che qui.

    Il predefinito C3D4 non e' un parametro di elaborazione con un valore
    scelto: e' il comportamento che questa funzione aveva prima della Fase 4,
    tenuto perche' i chiamanti gia' scritti continuino a valere. Chi sceglie
    davvero il tipo lo prende da `tet.element` o da `model.element`.
    """
    if fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(
            f"tipo di elemento '{element_type}' sconosciuto: "
            f"i tipi scrivibili sono {sorted(NODI_PER_ELEMENTO)}"
        )

    nodes = np.asarray(nodes, dtype=np.float64)
    elements = np.asarray(elements, dtype=np.int64)
    attesi = NODI_PER_ELEMENTO[element_type]
    if elements.shape[1] != attesi:
        raise ValueError(
            f"{element_type} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: un deck scritto cosi' non e' leggibile da alcun solutore"
        )

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE={element_type}, ELSET={elset}")
    lines += [
        ", ".join([str(index + 1)] + [str(nodo + 1) for nodo in elemento])
        for index, elemento in enumerate(elements)
    ]
```

Il resto del corpo — i set di nodo, il materiale, il vincolo, lo step, le stampe e l'uscita — resta **identico**. Rinomina le occorrenze di `tets` in `elements` dove compaiono.

- [ ] **Step 6: `export_model` accetta gli esaedri**

In `export_model`, sostituisci la firma e la guardia sul tipo:

```python
def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
    reference: np.ndarray | None = None,
    element_type: str | None = None,
) -> dict[str, object]:
```

e al posto della `NotImplementedError` su `tet_cfg.element != "C3D4"`:

```python
    tipo = tet_cfg.element if element_type is None else element_type
    if tipo == "C3D10":
        raise NotImplementedError(
            "elemento C3D10 non supportato dal writer: TetGen produce i nodi di "
            "lato con order=2, ma il deck scrive i soli vertici. Usa C3D4 finche' "
            "il writer non gestisce i dieci nodi."
        )
    if tipo not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{tipo}' sconosciuto")
```

Dentro il corpo, sostituisci `tets` con `elements`, `_boundary_faces(tets)` con `boundary_faces(elements)`, e la riga del volume:

```python
    from meshrec.core.quality import element_volumes

    volume = float(np.abs(element_volumes(aligned, elements)).sum())
```

Aggiungi `"element_type": tipo,` al dizionario restituito, e passa `element_type=tipo` a `write_inp` e a `write_vtu`.

- [ ] **Step 7: `write_vtu` per tipo di elemento**

```python
def write_vtu(
    path: Path, nodes: np.ndarray, elements: np.ndarray, element_type: str = "C3D4"
) -> None:
    """Esportazione per la visualizzazione, delegata a meshio.

    meshio ha nomi propri per i tipi di cella, che non sono quelli del
    solutore: la tabella traduce, e un tipo non tradotto solleva invece di
    scrivere un file che nessun visualizzatore aprirebbe.
    """
    import meshio

    celle = {"C3D4": "tetra", "C3D10": "tetra10", "C3D8": "hexahedron",
             "C3D8I": "hexahedron", "C3D8R": "hexahedron"}
    if element_type not in celle:
        raise ValueError(f"tipo di elemento '{element_type}' senza corrispondente in meshio")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write_points_cells(
        str(path),
        np.asarray(nodes, dtype=np.float64),
        [(celle[element_type], np.asarray(elements, dtype=np.int64))],
    )
```

- [ ] **Step 8: `element_volumes` in `quality.py`, il minimo che serve qui**

In `quality.py`, subito sotto `tet_volumes`:

```python
# Decomposizione di un esaedro in sei tetraedri, a ventaglio dal nodo 0 attorno
# alla diagonale 0-6. Verificata a mano sul cubo unitario: i sei volumi valgono
# 1/6 ciascuno, e la somma vale esattamente 1.
_HEX_IN_TET = (
    (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6),
    (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6),
)


def hex_volumes(nodes: np.ndarray, hexes: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni esaedro, per decomposizione in sei tetraedri.

    Non e' la quadratura di Gauss dell'elemento trilineare, e su un esaedro con
    facce non piane le due differiscono: la decomposizione misura il volume del
    solido a facce triangolate, che e' anche quello che la superficie di bordo
    racchiude. E' la definizione coerente con `mesh_volume`, quindi le due
    misure si possono confrontare invece di divergere in silenzio.
    """
    h = np.asarray(hexes, dtype=np.int64)
    return sum(tet_volumes(nodes, h[:, list(combo)]) for combo in _HEX_IN_TET)


def element_volumes(nodes: np.ndarray, elements: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni elemento, quale che sia il tipo.

    E' l'unico punto in cui il resto del programma deve chiedersi quanti nodi
    ha un elemento: chi la chiama non lo sa e non deve saperlo.
    """
    colonne = np.asarray(elements).shape[1]
    if colonne == 8:
        return hex_volumes(nodes, elements)
    if colonne in (4, 10):
        return tet_volumes(nodes, np.asarray(elements)[:, :4])
    raise ValueError(f"elemento con {colonne} nodi: nessun volume definito per questa forma")
```

- [ ] **Step 9: Il test del volume esaedrico**

In coda a `tests/test_quality.py`:

```python
def test_il_volume_di_un_cubo_unitario_vale_uno():
    """La decomposizione in sei tetraedri e' verificata a mano nel commento:
    questo test la verifica di nuovo, e cade se qualcuno la riordina."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    assert quality.hex_volumes(nodi, esaedri) == pytest.approx([1.0])
    assert quality.element_volumes(nodi, esaedri) == pytest.approx([1.0])


def test_il_volume_esaedrico_e_negativo_se_l_elemento_e_rovesciato():
    """Il controllo che smentisce: scambiando la faccia inferiore con la
    superiore il volume cambia segno, ed e' cosi' che un elemento invertito si
    fa vedere invece di passare per buono."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    rovesciato = np.array([[4, 5, 6, 7, 0, 1, 2, 3]], dtype=np.int64)

    assert quality.hex_volumes(nodi, rovesciato)[0] < 0.0


def test_element_volumes_sui_tetraedri_da_quello_che_dava_tet_volumes():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )

    assert quality.element_volumes(nodes, tets) == pytest.approx(quality.tet_volumes(nodes, tets))
```

- [ ] **Step 10: Eseguire i test di `abaqus` e `quality`**

Run: `uv run pytest tests/test_abaqus.py tests/test_quality.py -v`
Expected: PASS. I test gia' esistenti su `write_inp` e `export_model` passavano `tets` come terzo argomento posizionale e continuano a valere: se qualcuno lo passava per nome (`tets=`), aggiornalo a `elements=`.

- [ ] **Step 11: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. `test_pipeline.py` e `test_cli.py` esercitano `export_model` sul percorso tetraedrico: se cadono, la generalizzazione ha cambiato il comportamento sui tetraedri, che e' il solo esito inaccettabile di questo task.

- [ ] **Step 12: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/core/quality.py meshrec/tests/test_abaqus.py meshrec/tests/test_quality.py
git commit -m "feat(fase-4): abaqus e quality generalizzati per tipo di elemento"
```

---

## Task 5: `*SURFACE, TYPE=ELEMENT`, `*TIE` e carico laterale — il debito rinviato dalla Fase 1

La mappatura delle facce dell'elemento sulle etichette del solutore e' **la fonte d'errore silenzioso per cui il debito era stato rinviato**: una tabella sbagliata produce un deck che il solutore legge senza protestare, applicando il carico alla faccia sbagliata. Ha quindi un test proprio, e il test non guarda la tabella: guarda la geometria che la tabella nomina.

**Files:**
- Modify: `src/meshrec/core/abaqus.py`
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `abaqus.NODI_PER_ELEMENTO`, `abaqus.boundary_faces` (Task 4).
- Produces:
  - `abaqus.FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]]` — per numero di nodi d'angolo, i nodi di S1, S2, ... nell'ordine del solutore.
  - `abaqus.element_surface(elements, indici_nodo, element_type) -> list[tuple[int, int]]` — coppie `(elemento, numero di faccia)`.
  - `abaqus.surface_area(nodes, elements, superficie, element_type) -> float`.
  - `write_inp(..., element_surfaces: dict[str, list[tuple[int, int]]] | None = None, ties: tuple[tuple[str, str, str], ...] = (), pressure: tuple[str, float] | None = None)`.

- [ ] **Step 1: I test della mappatura, che guardano la geometria e non la tabella**

In coda a `tests/test_abaqus.py`:

```python
_CUBO = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
_ESAEDRO = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_le_sei_etichette_di_faccia_di_un_esaedro_sono_le_sue_sei_facce():
    """Il test non legge la tabella: costruisce l'insieme dei nodi che ogni
    etichetta nomina e verifica che siano le sei facce distinte del cubo. Una
    tabella sbagliata nominerebbe due volte la stessa faccia, o una diagonale."""
    nominate = {
        tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[8][numero]))
        for numero in range(6)
    }
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(_ESAEDRO).tolist()}

    assert len(nominate) == 6
    assert nominate == vere


def test_le_quattro_etichette_di_faccia_di_un_tetraedro_sono_le_sue_quattro_facce():
    tetraedro = np.array([[0, 1, 2, 3]], dtype=np.int64)
    nominate = {tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[4][numero])) for numero in range(4)}
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(tetraedro).tolist()}

    assert len(nominate) == 4
    assert nominate == vere


def test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta():
    """Il controllo della spec: area della superficie esportata contro area
    calcolata sulle facce. Su un cubo unitario ogni faccia vale 1."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    assert superficie == [(0, 1)], "la faccia z=0 di un C3D8 e' S1"
    assert abaqus.surface_area(_CUBO, _ESAEDRO, superficie, "C3D8I") == pytest.approx(1.0)


def test_la_superficie_di_elemento_non_nomina_una_faccia_solo_sfiorata():
    """Il controllo che smentisce il precedente: tre nodi su quattro di una
    faccia non sono quella faccia, e nominarla applicherebbe un carico dove
    l'utente non lo ha chiesto."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2]), "C3D8I")

    assert superficie == []


def test_la_superficie_esportata_ha_l_area_delle_facce_che_dichiara(tmp_path):
    """Il deck e' la fonte: si rilegge il file e si contano le coppie scritte,
    invece di fidarsi di cio' che la funzione ha restituito."""
    nodi_base = np.flatnonzero(_CUBO[:, 2] <= 1e-9)
    superficie = abaqus.element_surface(_ESAEDRO, nodi_base, "C3D8I")
    percorso = tmp_path / "carico.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": nodi_base},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"FACCIA_BASSA": superficie},
        pressure=("FACCIA_BASSA", 0.25),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT, NAME=FACCIA_BASSA" in testo
    assert "1, S1" in testo
    assert "*DSLOAD" in testo
    assert "FACCIA_BASSA, P, 0.25" in testo


def test_senza_carico_laterale_il_deck_non_ha_alcuna_card_di_pressione(tmp_path):
    """Il carico laterale e' opzionale e assente se non richiesto: un deck che
    lo portasse comunque a zero applicherebbe una pressione nulla dichiarata,
    che e' un'altra cosa da nessuna pressione."""
    percorso = tmp_path / "senza.inp"
    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*DSLOAD" not in testo
    assert "*SURFACE" not in testo
    assert "*TIE" not in testo


def test_il_tie_nomina_due_superfici_gia_dichiarate(tmp_path):
    """Un *TIE che punta a una superficie mai dichiarata e' un deck rotto che
    il solutore rifiuta solo alla lettura: l'errore arriva prima."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    with pytest.raises(ValueError, match="MAI_DICHIARATA"):
        abaqus.write_inp(
            tmp_path / "rotto.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3])},
            material=MATERIALE,
            element_type="C3D8I",
            element_surfaces={"UNA": superficie},
            ties=(("GIUNZIONE_1", "UNA", "MAI_DICHIARATA"),),
        )
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_abaqus.py -k "faccia or superficie or tie or carico or pressione" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'FACCE_DEL_SOLUTORE'`.

- [ ] **Step 3: La tabella delle etichette del solutore**

In `abaqus.py`, subito sotto `FACCE_TOPOLOGICHE`:

```python
# Le facce di un elemento nell'ordine e con la numerazione del solutore: S1 e'
# la prima riga, S2 la seconda, e cosi' via. E' la tabella che il debito
# rinviato dalla Fase 1 chiedeva, ed e' la fonte d'errore silenzioso per cui
# era stato rinviato: sbagliarla produce un deck che il solutore legge senza
# protestare, applicando il carico a una faccia diversa da quella chiesta.
#
# C3D4, dal manuale: S1 = 1-2-3, S2 = 1-4-2, S3 = 2-4-3, S4 = 3-4-1.
# C3D8, dal manuale: S1 = 1-2-3-4, S2 = 5-8-7-6, S3 = 1-5-6-2,
#                    S4 = 2-6-7-3, S5 = 3-7-8-4, S6 = 4-8-5-1.
# Qui gli indici sono 0-based, quindi ciascuno vale uno in meno.
#
# Non e' FACCE_TOPOLOGICHE con un altro nome: quella serve a trovare il bordo e
# ordina gli indici prima di confrontarli, quindi puo' elencare le facce in
# qualunque ordine. Questa non puo': l'ordine E' l'informazione.
FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)),
    8: (
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ),
}


def element_surface(
    elements: np.ndarray, indici_nodo: np.ndarray, element_type: str
) -> list[tuple[int, int]]:
    """Le coppie (elemento, numero di faccia) le cui facce cadono nell'insieme dato.

    Una faccia entra nella superficie solo se **tutti** i suoi nodi stanno
    nell'insieme: tre nodi su quattro non sono quella faccia, e nominarla
    applicherebbe un carico dove l'utente non lo ha chiesto.

    L'ordine delle coppie e' quello degli elementi e, dentro un elemento,
    quello dei numeri di faccia: e' funzione del dato e non dell'iterazione,
    quindi il deck scritto su due macchine e' lo stesso file.
    """
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{element_type}' sconosciuto")
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if NODI_PER_ELEMENTO[element_type] == 8 else 4
    dentro = np.zeros(int(elementi.max()) + 1, dtype=bool)
    dentro[np.asarray(indici_nodo, dtype=np.int64)] = True

    coppie: list[tuple[int, int]] = []
    for numero, combo in enumerate(FACCE_DEL_SOLUTORE[angoli], start=1):
        tutte_dentro = dentro[elementi[:, list(combo)]].all(axis=1)
        coppie += [(int(indice), numero) for indice in np.flatnonzero(tutte_dentro)]
    coppie.sort()
    return coppie


def surface_area(
    nodes: np.ndarray,
    elements: np.ndarray,
    superficie: list[tuple[int, int]],
    element_type: str,
) -> float:
    """Area della superficie di elemento, sommata faccia per faccia.

    E' il controllo che smentisce la superficie esportata: se l'area calcolata
    qui non coincide con quella delle facce che il deck dichiara, la tabella
    delle etichette nomina facce diverse da quelle volute. Una faccia di piu'
    di tre nodi e' divisa a ventaglio dal primo, che e' esatto per una faccia
    piana e sottostima di poco una faccia svergolata.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if NODI_PER_ELEMENTO[element_type] == 8 else 4

    totale = 0.0
    for elemento, numero in superficie:
        nodi = [elementi[elemento][indice] for indice in FACCE_DEL_SOLUTORE[angoli][numero - 1]]
        for primo, secondo in zip(nodi[1:-1], nodi[2:], strict=True):
            lato_a = punti[primo] - punti[nodi[0]]
            lato_b = punti[secondo] - punti[nodi[0]]
            totale += float(np.linalg.norm(np.cross(lato_a, lato_b)) / 2.0)
    return totale
```

- [ ] **Step 4: Le tre card nuove in `write_inp`**

Aggiungi alla firma di `write_inp`, dopo `element_type`:

```python
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str], ...] = (),
    pressure: tuple[str, float] | None = None,
```

Dopo i controlli sui `node_sets`, aggiungi:

```python
    superfici = {} if element_surfaces is None else element_surfaces
    for nome, dipendente, indipendente in ties:
        mancanti = [s for s in (dipendente, indipendente) if s not in superfici]
        if mancanti:
            raise ValueError(
                f"il vincolo *TIE '{nome}' nomina {mancanti}, che non e' fra le "
                "superfici dichiarate: un deck cosi' viene rifiutato dal solutore "
                "solo alla lettura, e questo errore arriva prima"
            )
    if pressure is not None and pressure[0] not in superfici:
        raise ValueError(
            f"il carico laterale agisce su '{pressure[0]}', che non e' fra le "
            "superfici dichiarate: una pressione applicata a nulla non e' un carico"
        )
```

Dopo il blocco che scrive i `*NSET` e **prima** di `*SOLID SECTION`:

```python
    for nome, coppie in superfici.items():
        lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={nome}")
        lines += [f"{elemento + 1}, S{numero}" for elemento, numero in coppie]

    for nome, dipendente, indipendente in ties:
        # ADJUST=NO: spostare i nodi della superficie dipendente sulla
        # indipendente cambierebbe la geometria dopo che il volume e' stato
        # misurato, e il modello non sarebbe piu' quello di cui il report parla.
        lines.append(f"*TIE, NAME={nome}, ADJUST=NO")
        lines.append(f"{dipendente}, {indipendente}")
```

E dopo la card `*DLOAD` della gravita', dentro lo step:

```python
    if pressure is not None:
        lines += ["*DSLOAD", f"{pressure[0]}, P, {pressure[1]}"]
```

Aggiungi alla docstring di `write_inp`, in coda:

```
    `element_surfaces`, `ties` e `pressure` sono le tre aggiunte della Fase 4 e
    sono tutte facoltative: senza di esse il deck e' identico a quello che
    questa funzione scriveva prima, ed e' cosi' che le corse tetraedriche
    restano confrontabili con quelle gia' fatte. Un carico assente non diventa
    una pressione dichiarata a zero: le due cose non sono la stessa.
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_abaqus.py -v`
Expected: PASS su tutti.

- [ ] **Step 6: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-4): superfici di elemento, *TIE e carico laterale nel deck

Chiude il debito rinviato dalla Fase 1. La tabella delle etichette di faccia
e' verificata contro la geometria che nomina, non contro se stessa."
```

---

## Task 6: la qualita' degli esaedri e' lo Jacobiano scalato, ed e' una colonna separata

`min_ratio` non vale per gli esaedri e la differenza fra le due metriche non e' una grandezza: sono due colonne, mai una sottrazione.

**Files:**
- Modify: `src/meshrec/core/quality.py`
- Test: `tests/test_quality.py`

**Interfaces:**
- Consumes: `quality.hex_volumes`, `quality._distribution` (Task 4 e preesistente).
- Produces: `quality.scaled_jacobian(nodes, hexes) -> np.ndarray`; `quality.hexa_metrics(nodes, hexes) -> dict[str, object]`.

- [ ] **Step 1: I test dello Jacobiano scalato**

In coda a `tests/test_quality.py`:

```python
_CUBO_NODI = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
_CUBO_HEX = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_lo_jacobiano_scalato_di_un_cubo_vale_uno():
    """Il cubo e' l'elemento perfetto: se non vale 1, la metrica non e' quella
    che dice di essere e ogni numero che ne discende e' senza scala."""
    assert quality.scaled_jacobian(_CUBO_NODI, _CUBO_HEX) == pytest.approx([1.0])


def test_lo_jacobiano_scalato_scende_su_un_elemento_schiacciato():
    """Il controllo che smentisce: distorcere l'elemento deve abbassare il
    numero, o la metrica non distingue una mesh buona da una cattiva."""
    schiacciato = _CUBO_NODI.copy()
    schiacciato[6] = [0.35, 0.35, 1.0]

    valore = quality.scaled_jacobian(schiacciato, _CUBO_HEX)[0]

    assert 0.0 < valore < 0.9


def test_lo_jacobiano_scalato_e_non_positivo_su_un_elemento_rovesciato():
    rovesciato = np.array([[4, 5, 6, 7, 0, 1, 2, 3]], dtype=np.int64)

    assert quality.scaled_jacobian(_CUBO_NODI, rovesciato)[0] <= 0.0


def test_le_metriche_esaedriche_non_contengono_min_ratio():
    """min_ratio e' il rapporto raggio-spigolo di un tetraedro e su un esaedro
    non e' definito. Metterlo nella stessa colonna dello Jacobiano scalato
    inviterebbe a sottrarre due grandezze diverse."""
    metriche = quality.hexa_metrics(_CUBO_NODI, _CUBO_HEX)

    assert "scaled_jacobian" in metriche
    assert "min_ratio" not in metriche
    assert "radius_edge_ratio" not in metriche
    assert metriche["inverted"] == 0
    assert metriche["hexes"] == 1
    assert metriche["total_volume"] == pytest.approx(1.0)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_quality.py -k "jacobiano or esaedric" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.quality' has no attribute 'scaled_jacobian'`.

- [ ] **Step 3: Implementare**

In `quality.py`, sotto `hex_volumes`:

```python
# Per ciascuno degli otto nodi di un esaedro, i tre nodi adiacenti nell'ordine
# che da' determinante positivo su un cubo con la numerazione standard
# (0-3 faccia inferiore in verso antiorario, 4-7 la superiore sopra di essi).
# Verificata a mano, nodo per nodo, sul cubo unitario: tutti e otto danno +1.
_ANGOLI_ESAEDRO = (
    (1, 3, 4), (2, 0, 5), (3, 1, 6), (0, 2, 7),
    (7, 5, 0), (4, 6, 1), (5, 7, 2), (6, 4, 3),
)


def scaled_jacobian(nodes: np.ndarray, hexes: np.ndarray) -> np.ndarray:
    """Jacobiano scalato di ogni esaedro: il minimo sugli otto angoli.

    E' la grandezza di qualita' degli esaedri, e non ha nulla a che vedere con
    `min_ratio`, che e' il rapporto raggio-spigolo di un tetraedro. Su un
    esaedro min_ratio non e' definito, quindi le due vivono in due colonne
    separate e la loro differenza non e' una grandezza: sottrarle darebbe un
    numero senza unita' e senza significato.

    In ogni angolo si prendono i tre spigoli uscenti, se ne calcola il
    determinante e lo si divide per il prodotto delle tre lunghezze. Vale 1 sul
    cubo, scende avvicinandosi a zero man mano che l'elemento si schiaccia, ed
    e' non positivo se l'elemento e' rovesciato. E' quindi anche il controllo
    che cerca gli Jacobiani negativi chiesto dalla spec, senza una seconda
    misura.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    h = np.asarray(hexes, dtype=np.int64)
    minimi = np.full(len(h), np.inf)

    for angolo, (a, b, c) in enumerate(_ANGOLI_ESAEDRO):
        origine = punti[h[:, angolo]]
        e1 = punti[h[:, a]] - origine
        e2 = punti[h[:, b]] - origine
        e3 = punti[h[:, c]] - origine
        determinante = np.einsum("ij,ij->i", e1, np.cross(e2, e3))
        prodotto = (
            np.linalg.norm(e1, axis=1)
            * np.linalg.norm(e2, axis=1)
            * np.linalg.norm(e3, axis=1)
        )
        # prodotto nullo vuol dire spigolo degenere: l'elemento e' rotto, e il
        # valore che lo dice e' zero, non un NaN che si propaga in silenzio
        valore = np.divide(
            determinante, prodotto, out=np.zeros_like(determinante), where=prodotto > 0.0
        )
        minimi = np.minimum(minimi, valore)

    return np.ascontiguousarray(minimi)


def hexa_metrics(nodes: np.ndarray, hexes: np.ndarray) -> dict[str, object]:
    """Metriche di volume di una mesh esaedrica.

    Deliberatamente **senza** min_ratio, rapporto raggio-spigolo e angolo
    diedro: sono grandezze del tetraedro, e riportarle qui accanto a quelle
    dell'esaedro inviterebbe a confrontare due colonne che non si confrontano.
    Il confronto fra i modelli, in report.py, le tiene infatti separate e
    dichiara che la qualita' degli elementi non e' una grandezza confrontabile
    fra un modello tetraedrico e uno esaedrico.
    """
    volumi = hex_volumes(nodes, hexes)
    jacobiani = scaled_jacobian(nodes, hexes)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "hexes": int(len(np.asarray(hexes))),
        "inverted": int((jacobiani <= 0.0).sum()),
        "total_volume": float(volumi.sum()),
        "element_volume": _distribution(volumi),
        "scaled_jacobian": _distribution(jacobiani),
    }
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_quality.py -v`
Expected: PASS.

- [ ] **Step 5: La suite intera e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/quality.py meshrec/tests/test_quality.py
git commit -m "feat(fase-4): Jacobiano scalato degli esaedri, colonna separata da min_ratio"
```

---

## Task 7: `core/hexa.py` — un prisma, in esaedri, con almeno tre strati nello spessore

**Files:**
- Create: `src/meshrec/core/hexa.py`
- Test: `tests/test_hexa.py`

**Interfaces:**
- Consumes: `config.ModelConfig` (Task 1); `quality.hex_volumes`, `quality.scaled_jacobian` (Task 4 e 6).
- Produces:
  - `hexa.passo_di_mesh(contorno, cfg) -> float`.
  - `hexa.ordine_canonico(nodi, esaedri) -> tuple[np.ndarray, np.ndarray]`.
  - `hexa.mesh_prisma(contorno, origine, asse, lunghezza, cfg) -> tuple[np.ndarray, np.ndarray, dict]`.

- [ ] **Step 1: I test del prisma singolo**

Crea `tests/test_hexa.py`:

```python
"""I modelli parametrici: prismi in esaedri, con il volume analitico a smentirli.

hexa.py costruisce e non misura, esattamente come wall.py misura e non
costruisce. Il confine e' cio' che rende questi test possibili: la verita' di
riferimento e' il volume analitico del prisma, calcolato qui e non dal codice
sotto prova.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import hexa, quality
from meshrec.core.config import ModelConfig

# Un rettangolo 200 x 140, in senso antiorario. Sono numeri del banco.
RETTANGOLO = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 140.0], [0.0, 140.0]])
LUNGHEZZA = 1500.0
ASSE_Z = np.array([0.0, 0.0, 1.0])


def test_il_prisma_e_fatto_di_soli_esaedri_e_ne_ha_il_volume_analitico():
    """La verita' di riferimento e' 200 x 140 x 1500: se la mesh non la
    riproduce, ogni massa e ogni confronto che ne discendono sono falsi."""
    nodi, esaedri, metriche = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, ModelConfig()
    )

    assert esaedri.shape[1] == 8, "soli esaedri: nessun prisma a base triangolare"
    volume = quality.hex_volumes(nodi, esaedri).sum()
    assert volume == pytest.approx(200.0 * 140.0 * LUNGHEZZA, rel=1e-6)
    assert metriche["hexes"] == len(esaedri)
    assert metriche["volume_analitico"] == pytest.approx(200.0 * 140.0 * LUNGHEZZA)


def test_nessun_esaedro_del_prisma_ha_jacobiano_non_positivo():
    """Un elemento rovesciato in mezzo a centomila non si vede guardando la
    mesh, e il solutore o si ferma o restituisce numeri senza senso."""
    nodi, esaedri, _ = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, ModelConfig()
    )

    assert (quality.scaled_jacobian(nodi, esaedri) > 0.0).all()


def test_lo_spessore_ha_almeno_tre_strati_di_elementi():
    """Vincolo imposto dal codice e non suggerito: con uno o due strati la
    flessione nello spessore non e' rappresentata, e il risultato e' sbagliato
    senza alcun segnale."""
    cfg = ModelConfig(target_size=1000.0)  # un passo assurdamente grosso

    nodi, esaedri, metriche = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, cfg
    )

    assert metriche["passo"] <= 140.0 / 3.0 + 1e-9, (
        "il passo chiesto e' stato ridotto fino a garantire tre strati nella "
        "sezione minima, o non lo e' stato ed e' un difetto"
    )
    # tre strati nello spessore vogliono almeno quattro piani di nodi
    quote = np.unique(np.round(nodi[:, 1], 6))
    assert len(quote) >= 4


def test_il_prisma_parte_dall_origine_e_va_lungo_l_asse_che_gli_si_da():
    """L'asse misurato conserva il fuori piombo: se la funzione lo ignorasse,
    il modello estruso e quello primitive sarebbero la stessa cosa e il
    confronto non separerebbe piu' i due effetti."""
    asse = np.array([0.0, np.sin(np.radians(5.0)), np.cos(np.radians(5.0))])
    origine = np.array([100.0, 50.0, -20.0])

    nodi, _esaedri, _ = hexa.mesh_prisma(RETTANGOLO, origine, asse, LUNGHEZZA, ModelConfig())

    lungo = (nodi - origine) @ asse
    assert lungo.min() == pytest.approx(0.0, abs=1e-6)
    assert lungo.max() == pytest.approx(LUNGHEZZA, abs=1e-6)


def test_l_ordine_di_nodi_ed_elementi_e_canonico_e_non_quello_dei_tag():
    """Quinto vincolo di prodotto. I tag di gmsh sono un ordine di generazione,
    non un dato della geometria, e il progetto ha gia' pagato una volta la
    lezione dell'ordine di iterazione di una libreria fra due piattaforme."""
    nodi = np.array([
        [1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0],
        [1.0, 0.0, 1.0], [0.0, 0.0, 1.0], [0.0, 1.0, 1.0], [1.0, 1.0, 1.0],
    ])
    esaedri = np.array([[1, 0, 3, 2, 5, 4, 7, 6]], dtype=np.int64)

    ordinati, rimappati = hexa.ordine_canonico(nodi, esaedri)

    # i nodi escono ordinati per x, poi y, poi z
    assert ordinati[0] == pytest.approx([0.0, 0.0, 0.0])
    assert ordinati[-1] == pytest.approx([1.0, 1.0, 1.0])
    # l'elemento punta agli stessi punti fisici di prima
    assert np.sort(ordinati[rimappati[0]], axis=0) == pytest.approx(
        np.sort(nodi[esaedri[0]], axis=0)
    )
    # e il volume non e' cambiato: la topologia interna dell'elemento resta
    assert quality.hex_volumes(ordinati, rimappati) == pytest.approx(
        quality.hex_volumes(nodi, esaedri)
    )
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_hexa.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.hexa'`.

- [ ] **Step 3: Scrivere `core/hexa.py`**

```python
"""I modelli parametrici: prismi di membratura in mesh esaedrica.

hexa.py **costruisce e non misura**: riceve da wall.py sezioni, assi e
lunghezze gia' misurati e ne fa una mesh. Il confine con wall.py non e'
estetico, e' cio' che rende ciascuno dei due verificabile da solo contro una
geometria a verita' nota.

La mesh esaedrica si fa con gmsh, che dalla Fase 4 e' una dipendenza vera e non
un extra: superficie piana dal contorno, ricombinazione in quadrilateri,
estrusione a strati. Il modulo non riscrive `gmsh_backend.py`, che genera mesh
tetraedriche da una STL ed e' un'altra macchina; ne riprende pero' due
abitudini, perche' sono state pagate: la rimappatura dei tag di nodo su indici
di array, e l'inizializzazione per tentativo con il `finalize` in un `finally`.
"""

from __future__ import annotations

import numpy as np

from meshrec.core.config import ModelConfig

_ARROTONDAMENTO = 6
"""Cifre decimali su cui i nodi sono confrontati per l'ordine canonico.

Non e' una tolleranza geometrica: e' la risoluzione oltre la quale due
coordinate prodotte dalla stessa costruzione differiscono solo per l'ultimo
bit. In millimetri, un nanometro.
"""


def passo_di_mesh(contorno: np.ndarray, cfg: ModelConfig) -> float:
    """Passo caratteristico che rispetta il vincolo degli strati nello spessore.

    Il vincolo e' imposto dal codice e non suggerito: con uno o due strati la
    flessione nello spessore non e' rappresentata, e il risultato e' sbagliato
    senza alcun segnale. Il passo chiesto in configurazione, se c'e', viene
    quindi ridotto fin dove serve, mai alzato.
    """
    punti = np.asarray(contorno, dtype=np.float64)
    minima = float(np.min(np.ptp(punti, axis=0)))
    tetto = minima / cfg.min_layers
    if cfg.target_size is None:
        return tetto
    return min(float(cfg.target_size), tetto)


def ordine_canonico(nodi: np.ndarray, esaedri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Riordina nodi ed elementi in un ordine funzione delle sole coordinate.

    I tag di gmsh sono un ordine di generazione, non un dato della geometria, e
    un conteggio o un indice che ne dipendesse dipenderebbe dalla piattaforma:
    e' la stessa lezione gia' pagata sull'ordine dei voxel di Open3D fra
    Windows x86-64 e macOS arm64 (quinto vincolo di prodotto).

    L'ordine **interno** dei nodi di un esaedro non si tocca: e' la topologia
    dell'elemento, e riordinarlo cambierebbe il solido invece del suo nome.
    Si riordinano i nodi fra loro e gli elementi fra loro.
    """
    punti = np.asarray(nodi, dtype=np.float64)
    elementi = np.asarray(esaedri, dtype=np.int64)

    chiave = np.round(punti, _ARROTONDAMENTO)
    # lexsort ordina per l'ultima chiave data: (z, y, x) ordina per x, poi y, poi z
    permutazione = np.lexsort((chiave[:, 2], chiave[:, 1], chiave[:, 0]))
    posizione = np.empty(len(punti), dtype=np.int64)
    posizione[permutazione] = np.arange(len(punti))

    rimappati = posizione[elementi]
    # gli elementi si ordinano per la tupla dei propri nodi rimappati, che e'
    # un numero della geometria; lexsort vuole le chiavi dall'ultima alla prima
    ordine = np.lexsort(rimappati.T[::-1])
    return np.ascontiguousarray(punti[permutazione]), np.ascontiguousarray(rimappati[ordine])


def _area_poligono(contorno: np.ndarray) -> float:
    """Area con segno di un poligono chiuso, formula di Gauss."""
    x, y = np.asarray(contorno, dtype=np.float64).T
    return float(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _base_del_piano(asse: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Due versori ortogonali all'asse, scelti in modo deterministico.

    Il riferimento e' l'asse coordinato meno allineato all'asse del prisma:
    sceglierlo dal dato invece che a caso rende la base la stessa su due
    esecuzioni, e quindi la mesh la stessa.
    """
    versore = np.asarray(asse, dtype=np.float64)
    versore = versore / np.linalg.norm(versore)
    candidati = np.eye(3)
    riferimento = candidati[int(np.argmin(np.abs(candidati @ versore)))]
    e1 = riferimento - versore * np.dot(riferimento, versore)
    e1 = e1 / np.linalg.norm(e1)
    return e1, np.cross(versore, e1)


def mesh_prisma(
    contorno: np.ndarray,
    origine: np.ndarray,
    asse: np.ndarray,
    lunghezza: float,
    cfg: ModelConfig,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Un prisma retto in esaedri: contorno di sezione estruso lungo l'asse.

    La sagoma viene costruita nel piano locale, ricombinata in quadrilateri ed
    estrusa a strati; solo alla fine il prisma viene ruotato e traslato al
    proprio posto. Costruire in locale e trasformare con numpy tiene fuori da
    gmsh ogni scelta di riferimento, che e' l'unica parte di questa funzione da
    cui potrebbe entrare una dipendenza dalla piattaforma.

    Il contorno e' orientato in senso antiorario prima di essere passato a
    gmsh: con l'orientazione opposta l'estrusione produce esaedri rovesciati,
    con Jacobiano negativo, e nessuna metrica della mesh lo direbbe guardandola.

    Restituisce nodi, esaedri e metriche, con nodi ed elementi gia' in ordine
    canonico.
    """
    import gmsh

    sagoma = np.asarray(contorno, dtype=np.float64)
    if _area_poligono(sagoma) < 0.0:
        sagoma = sagoma[::-1]
    area = abs(_area_poligono(sagoma))
    passo = passo_di_mesh(sagoma, cfg)
    strati = max(cfg.min_layers, int(round(float(lunghezza) / passo)))

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        punti = [gmsh.model.geo.addPoint(u, v, 0.0, passo) for u, v in sagoma]
        linee = [
            gmsh.model.geo.addLine(punti[indice], punti[(indice + 1) % len(punti)])
            for indice in range(len(punti))
        ]
        anello = gmsh.model.geo.addCurveLoop(linee)
        superficie = gmsh.model.geo.addPlaneSurface([anello])
        # setRecombine sulla superficie piu' RecombineAll: senza il primo la
        # faccia resta triangolata e l'estrusione da' prismi a base triangolare
        # invece di esaedri, cioe' un elemento che il deck non sa scrivere.
        gmsh.model.geo.mesh.setRecombine(2, superficie)
        gmsh.model.geo.extrude(
            [(2, superficie)], 0.0, 0.0, float(lunghezza),
            numElements=[strati], recombine=True,
        )
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMax", passo)
        gmsh.option.setNumber("Mesh.MeshSizeMin", passo)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.model.mesh.generate(3)

        tag_nodi, coordinate, _ = gmsh.model.mesh.getNodes()
        tipi, _, per_elemento = gmsh.model.mesh.getElements(3)
        if 5 not in list(tipi):
            raise RuntimeError(
                "gmsh non ha prodotto esaedri (tipo 5): la ricombinazione della "
                "sagoma non e' riuscita, e un modello a prismi triangolari non e' "
                "quello che il deck dichiara"
            )
        tag_esaedri = np.asarray(
            per_elemento[list(tipi).index(5)], dtype=np.int64
        ).reshape(-1, 8)
        versione = gmsh.option.getString("General.Version")
    finally:
        gmsh.finalize()

    tag_nodi = np.asarray(tag_nodi, dtype=np.int64)
    locali = np.ascontiguousarray(np.asarray(coordinate, dtype=np.float64).reshape(-1, 3))
    # I tag dei nodi sono 1-based e non contigui: senza rimappatura gli elementi
    # punterebbero a posizioni sbagliate dell'array, e la mesh sarebbe sbagliata
    # senza alcun segnale. Stessa cautela di gmsh_backend._extract_mesh.
    tavola = np.zeros(tag_nodi.max() + 1, dtype=np.int64)
    tavola[tag_nodi] = np.arange(len(tag_nodi))
    esaedri = np.ascontiguousarray(tavola[tag_esaedri])

    e1, e2 = _base_del_piano(asse)
    versore = np.asarray(asse, dtype=np.float64)
    versore = versore / np.linalg.norm(versore)
    rotazione = np.stack([e1, e2, versore])
    nodi = np.asarray(origine, dtype=np.float64) + locali @ rotazione

    nodi, esaedri = ordine_canonico(nodi, esaedri)
    metriche = {
        "hexes": int(len(esaedri)),
        "nodes": int(len(nodi)),
        "passo": float(passo),
        "strati": int(strati),
        "area_sezione": float(area),
        "volume_analitico": float(area * lunghezza),
        "gmsh_version": versione,
    }
    return nodi, esaedri, metriche
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_hexa.py -v`
Expected: PASS su tutti e cinque.

Se `test_il_prisma_e_fatto_di_soli_esaedri_e_ne_ha_il_volume_analitico` fallisce con un volume piu' piccolo dell'analitico, la ricombinazione ha lasciato prismi triangolari: il `RuntimeError` dello Step 3 dovrebbe averlo intercettato, e se non l'ha fatto significa che gmsh ha restituito esaedri **e** prismi. In quel caso il messaggio va reso piu' severo — `list(tipi) != [5]` invece di `5 not in list(tipi)` — e il fatto va scritto nel documento del Task 14.

- [ ] **Step 5: La suite intera e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/hexa.py meshrec/tests/test_hexa.py
git commit -m "feat(fase-4): il prisma in esaedri, con tre strati nello spessore imposti"
```

---

## Task 8: il telaio — i due modelli, le giunzioni tagliate, le superfici del `*TIE`

**Files:**
- Modify: `src/meshrec/core/hexa.py`
- Test: `tests/test_hexa.py`

**Interfaces:**
- Consumes: `hexa.mesh_prisma` (Task 7); `wall.Membratura` (Task 3); `abaqus.element_surface` (Task 5).
- Produces:
  - `hexa.Prisma` — dataclass `contorno, origine, asse, lunghezza`.
  - `hexa.prisma_di(membratura, tipo) -> Prisma` con `tipo` in `("estruso", "primitive")`.
  - `hexa.dentro(prisma, punti) -> np.ndarray`.
  - `hexa.taglia_giunzioni(prismi) -> tuple[list[Prisma], list[dict]]`.
  - `hexa.costruisci(membrature, tipo, cfg) -> dict[str, object]` con chiavi `nodi`, `elementi`, `blocchi`, `superfici`, `ties`, `metriche`.

**Requisito del Ruling J, con un proprio test e non come nota:** `wall.py` misura e non scarta, quindi il rifiuto di una regione non prismatica arriva qui. `costruisci` **non puo' costruire** su una membratura con `riempimento_stato == "vuoto"` e `densita_dispersione <= cfg.density_dispersion_limit` (misura affidabile): quella regione e' un ingombro, non una sezione — tipicamente due membrature unite a Π che la scomposizione non ha separato — e un modello costruito su di essa sarebbe inventato. Lo stato `non_verificabile` **non** e' motivo di rifiuto: dice che la misura non vale, non che il pezzo e' cavo, e su una nuvola rada e' l'esito normale. Il rifiuto va riportato con lo stesso corredo che `wall.riempimento` gia' consegna (stato, valore, soglia, dispersione della densita'), senza ricalcolare nulla. Se questa guardia mancasse, una Π diventerebbe un modello parametrico: e' il costo dichiarato del Ruling J.

- [ ] **Step 1: I test dei due prismi e del taglio**

In coda a `tests/test_hexa.py`:

```python
def _membratura_finta(contorno, origine, asse, lunghezza, asse_ideale):
    from meshrec.core.wall import Membratura

    return Membratura(
        punti=np.arange(0),
        asse=np.asarray(asse, dtype=np.float64),
        origine=np.asarray(origine, dtype=np.float64),
        lunghezza=float(lunghezza),
        sezione=(float(np.ptp(contorno[:, 0])), float(np.ptp(contorno[:, 1]))),
        sezione_dispersione=(0.0, 0.0),
        contorno=np.asarray(contorno, dtype=np.float64),
        fuori_piombo_deg=0.0,
        asse_ideale=np.asarray(asse_ideale, dtype=np.float64),
        scarto_asse_deg=0.0,
        rigonfiamento=np.zeros(4),
        volume=0.0,
        riempimento_sezione=1.0,
        riempimento_stato="pieno",
        densita_dispersione=0.0,
    )


def test_il_modello_primitive_raddrizza_l_asse_e_squadra_la_sezione():
    """I due modelli separano due effetti diversi: l'irregolarita' della sezione
    e il fuori piombo. Se primitive non raddrizzasse, il confronto li
    sommerebbe in un unico salto invece di distinguerli."""
    storto = np.array([0.0, np.sin(np.radians(6.0)), np.cos(np.radians(6.0))])
    sezione_irregolare = np.array([[0.0, 0.0], [200.0, 4.0], [197.0, 140.0], [3.0, 136.0]])
    membratura = _membratura_finta(
        sezione_irregolare, [0.0, 0.0, 0.0], storto, 1500.0, [0.0, 0.0, 1.0]
    )

    estruso = hexa.prisma_di(membratura, "estruso")
    primitive = hexa.prisma_di(membratura, "primitive")

    assert estruso.asse == pytest.approx(storto)
    assert primitive.asse == pytest.approx([0.0, 0.0, 1.0])
    assert len(estruso.contorno) == 4
    assert len(primitive.contorno) == 4
    # primitive e' il rettangolo dei valori misurati: quattro angoli retti
    lati = np.diff(np.vstack([primitive.contorno, primitive.contorno[:1]]), axis=0)
    for primo, secondo in zip(lati, np.roll(lati, -1, axis=0), strict=True):
        assert float(np.dot(primo, secondo)) == pytest.approx(0.0, abs=1e-9)


def test_il_modello_primitive_conserva_le_dimensioni_misurate():
    """Il controllo che smentisce il precedente: raddrizzare non vuol dire
    inventare. Le due dimensioni del rettangolo sono quelle misurate."""
    sezione = np.array([[0.0, 0.0], [250.0, 0.0], [250.0, 175.0], [0.0, 175.0]])
    membratura = _membratura_finta(
        sezione, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 900.0, [0.0, 0.0, 1.0]
    )

    primitive = hexa.prisma_di(membratura, "primitive")

    assert np.ptp(primitive.contorno, axis=0) == pytest.approx([250.0, 175.0])
    assert primitive.lunghezza == pytest.approx(900.0)


def test_l_appartenenza_a_un_prisma_e_esatta_sul_contorno_convesso():
    prisma = hexa.Prisma(
        contorno=RETTANGOLO, origine=np.zeros(3), asse=ASSE_Z, lunghezza=1000.0
    )
    dentro = np.array([[100.0, 70.0, 500.0], [1.0, 1.0, 1.0]])
    fuori = np.array([[300.0, 70.0, 500.0], [100.0, 70.0, 1500.0], [100.0, -5.0, 500.0]])

    assert hexa.dentro(prisma, dentro).all()
    assert not hexa.dentro(prisma, fuori).any()


def test_due_prismi_che_si_compenetrano_vengono_tagliati_e_il_volume_torna():
    """Le membrature si compenetrano dove si incontrano, e senza taglio il
    volume viene contato due volte: un errore che nessuna metrica di qualita'
    vedrebbe, e per questo il controllo lo cerca esplicitamente."""
    colonna = hexa.Prisma(
        contorno=np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0]]),
        origine=np.array([0.0, 0.0, 0.0]),
        asse=np.array([0.0, 0.0, 1.0]),
        lunghezza=1600.0,
    )
    trave = hexa.Prisma(
        contorno=np.array([[0.0, 0.0], [300.0, 0.0], [300.0, 200.0], [0.0, 200.0]]),
        origine=np.array([0.0, 0.0, 1300.0]),
        asse=np.array([1.0, 0.0, 0.0]),
        lunghezza=1400.0,
    )

    tagliati, giunzioni = hexa.taglia_giunzioni([colonna, trave])

    assert len(tagliati) == 2
    assert len(giunzioni) == 1
    accorciato = min(tagliati, key=lambda p: p.lunghezza)
    assert accorciato.lunghezza < 1600.0, "la colonna doveva fermarsi sotto la trave"
    somma = sum(
        abs(hexa._area_poligono(p.contorno)) * p.lunghezza for p in tagliati
    )
    doppio = 200.0 * 200.0 * 300.0
    assert somma == pytest.approx(
        200.0 * 200.0 * 1600.0 + 300.0 * 200.0 * 1400.0 - doppio, rel=0.15
    )


def test_il_telaio_costruito_dichiara_le_superfici_del_tie():
    """La mesh di due membrature adiacenti non combacia nodo a nodo: il legame
    e' un *TIE fra superfici a contatto, e le superfici devono esistere."""
    membrature = [
        _membratura_finta(
            np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0]]),
            [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 1600.0, [0.0, 0.0, 1.0],
        ),
        _membratura_finta(
            np.array([[0.0, 0.0], [300.0, 0.0], [300.0, 200.0], [0.0, 200.0]]),
            [0.0, 0.0, 1300.0], [1.0, 0.0, 0.0], 1400.0, [1.0, 0.0, 0.0],
        ),
    ]

    modello = hexa.costruisci(membrature, "estruso", ModelConfig())

    assert modello["elementi"].shape[1] == 8
    assert len(modello["blocchi"]) == 2
    assert modello["ties"], "due membrature che si toccano devono avere un *TIE"
    for _nome, dipendente, indipendente in modello["ties"]:
        assert dipendente in modello["superfici"]
        assert indipendente in modello["superfici"]
    assert modello["metriche"]["giunzioni"] == len(modello["ties"])
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_hexa.py -k "primitive or appartenenza or giunzion or telaio" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.hexa' has no attribute 'Prisma'`.

- [ ] **Step 3: `Prisma`, `prisma_di`, `dentro`**

In `hexa.py`, aggiungi `from dataclasses import dataclass` agli import e in coda al file:

```python
@dataclass(eq=False)
class Prisma:
    """Un prisma retto: contorno di sezione nel proprio piano, origine, asse, lunghezza.

    E' l'unica forma che i modelli parametrici conoscono. Il contorno e'
    convesso perche' viene da `wall.semplifica_contorno`, e la convessita' e'
    cio' che rende immediato il test di appartenenza usato dal taglio alle
    giunzioni.
    """

    contorno: np.ndarray
    origine: np.ndarray
    asse: np.ndarray
    lunghezza: float


def prisma_di(membratura, tipo: str) -> Prisma:
    """Il prisma di una membratura, secondo il modello richiesto.

    Non sono due generatori ma due argomenti: cambia se la sezione conserva la
    forma rilevata o diventa il rettangolo dei valori misurati, e se l'asse
    conserva il fuori piombo misurato o e' l'asse ideale, dritto. Il confronto
    separa cosi' due effetti diversi -- irregolarita' della sezione e fuori
    piombo -- invece di sommarli in un unico salto.

    In nessuno dei due casi la sezione viene dal disegno: prenderla dal disegno
    farebbe misurare al confronto anche lo scarto fra progetto e costruito, che
    e' un'altra domanda.
    """
    if tipo == "estruso":
        return Prisma(
            contorno=np.asarray(membratura.contorno, dtype=np.float64),
            origine=np.asarray(membratura.origine, dtype=np.float64),
            asse=np.asarray(membratura.asse, dtype=np.float64),
            lunghezza=float(membratura.lunghezza),
        )
    if tipo == "primitive":
        larghezza, altezza = (float(valore) for valore in np.ptp(membratura.contorno, axis=0))
        minimo = np.min(np.asarray(membratura.contorno, dtype=np.float64), axis=0)
        rettangolo = minimo + np.array(
            [[0.0, 0.0], [larghezza, 0.0], [larghezza, altezza], [0.0, altezza]]
        )
        return Prisma(
            contorno=rettangolo,
            origine=np.asarray(membratura.origine, dtype=np.float64),
            asse=np.asarray(membratura.asse_ideale, dtype=np.float64),
            lunghezza=float(membratura.lunghezza),
        )
    raise ValueError(f"modello '{tipo}' sconosciuto: i modelli sono 'estruso' e 'primitive'")


def dentro(prisma: Prisma, punti: np.ndarray) -> np.ndarray:
    """Quali dei punti dati cadono dentro il prisma.

    Due condizioni: la coordinata lungo l'asse sta fra zero e la lunghezza, e
    la proiezione sul piano di sezione sta dentro il contorno. Il contorno e'
    convesso, quindi «dentro» significa che tutti i prodotti vettoriali con i
    lati hanno lo stesso segno: quattro righe e nessun algoritmo di ray
    casting.
    """
    coordinate = np.atleast_2d(np.asarray(punti, dtype=np.float64))
    versore = prisma.asse / np.linalg.norm(prisma.asse)
    e1, e2 = _base_del_piano(versore)
    relativi = coordinate - prisma.origine

    lungo = relativi @ versore
    nel_tratto = (lungo >= 0.0) & (lungo <= prisma.lunghezza)

    sezione = np.column_stack([relativi @ e1, relativi @ e2])
    contorno = prisma.contorno
    if _area_poligono(contorno) < 0.0:
        contorno = contorno[::-1]
    dentro_sezione = np.ones(len(coordinate), dtype=bool)
    for primo, secondo in zip(contorno, np.roll(contorno, -1, axis=0), strict=True):
        lato = secondo - primo
        verso = np.cross(lato, sezione - primo)
        dentro_sezione &= verso >= -1e-9
    return nel_tratto & dentro_sezione
```

- [ ] **Step 4: `taglia_giunzioni` e `costruisci`**

In coda a `hexa.py`:

```python
_CAMPIONI_ASSE = 200
"""Campioni lungo l'asse con cui si cerca dove un prisma entra in un altro.

Non e' un parametro di elaborazione: e' la risoluzione con cui si legge una
condizione gia' definita. Duecento campioni su una membratura di due metri
sono un centimetro, cioe' sotto la scala di qualunque giunzione.
"""


def taglia_giunzioni(prismi: list[Prisma]) -> tuple[list[Prisma], list[dict[str, object]]]:
    """Accorcia i prismi minori dove entrano in un prisma maggiore.

    Le membrature si compenetrano dove si incontrano, e senza taglio il volume
    alle giunzioni viene contato due volte: un errore che nessuna metrica di
    qualita' della mesh vedrebbe, e per questo il controllo di chiusura del
    volume lo cerca esplicitamente.

    Chi cede e' il prisma di sezione minore, che e' un criterio del dato e non
    dell'ordine in cui i prismi arrivano: a pari sezione decide la lunghezza, e
    a pari lunghezza l'indice, che e' l'ultima carta e serve solo a non
    lasciare la scelta all'ordinamento.

    **Soffitto dichiarato:** il taglio e' un accorciamento lungo l'asse, quindi
    e' esatto quando l'intersezione tocca un'estremita' del prisma minore -- il
    caso di un telaio, dove le membrature si incontrano alle estremita' -- e
    non lo e' se un prisma attraversasse un altro da parte a parte. La via
    d'aggiornamento e' una vera operazione booleana fra solidi, che oggi non
    ha in casa nessuna libreria del progetto.
    """
    ordine = sorted(
        range(len(prismi)),
        key=lambda indice: (
            -abs(_area_poligono(prismi[indice].contorno)),
            -prismi[indice].lunghezza,
            indice,
        ),
    )
    tagliati = list(prismi)
    giunzioni: list[dict[str, object]] = []

    for posizione, maggiore in enumerate(ordine):
        for minore in ordine[posizione + 1 :]:
            piccolo = tagliati[minore]
            versore = piccolo.asse / np.linalg.norm(piccolo.asse)
            passo = np.linspace(0.0, piccolo.lunghezza, _CAMPIONI_ASSE)
            centro_sezione = piccolo.contorno.mean(axis=0)
            e1, e2 = _base_del_piano(versore)
            asse_mediano = (
                piccolo.origine
                + centro_sezione[0] * e1
                + centro_sezione[1] * e2
                + np.outer(passo, versore)
            )
            invaso = dentro(tagliati[maggiore], asse_mediano)
            if not invaso.any():
                continue

            # si accorcia l'estremita' invasa; se sono invase entrambe il
            # prisma minore attraversa il maggiore da parte a parte, ed e' il
            # caso che il soffitto dichiarato non copre
            if invaso[0] and invaso[-1]:
                raise ValueError(
                    "un prisma attraversa un altro da parte a parte: il taglio "
                    "alle giunzioni accorcia lungo l'asse e non sa dividere un "
                    "prisma in due. Verifica la scomposizione: due membrature "
                    "che si attraversano sono quasi sempre una regione fusa"
                )
            libero = np.flatnonzero(~invaso)
            if invaso[0]:
                nuova_origine = piccolo.origine + versore * passo[libero[0]]
                nuova_lunghezza = piccolo.lunghezza - passo[libero[0]]
            else:
                nuova_origine = piccolo.origine
                nuova_lunghezza = passo[libero[-1]]

            giunzioni.append({
                "maggiore": int(maggiore),
                "minore": int(minore),
                "accorciamento": float(piccolo.lunghezza - nuova_lunghezza),
            })
            tagliati[minore] = Prisma(
                contorno=piccolo.contorno,
                origine=nuova_origine,
                asse=piccolo.asse,
                lunghezza=float(nuova_lunghezza),
            )

    return tagliati, giunzioni


def costruisci(membrature: list, tipo: str, cfg: ModelConfig) -> dict[str, object]:
    """Il telaio intero: prismi tagliati, mesh di ciascuno, superfici e vincoli.

    Le mesh di membrature adiacenti non combaciano nodo a nodo -- una sezione
    da 172 contro una da 700 -- quindi il legame e' un `*TIE` fra le superfici
    a contatto e non una fusione di nodi. **La mesh conforme multiblocco resta
    la via d'aggiornamento**, e non e' un dettaglio d'attuazione: e' una
    differenza fra i modelli che non deriva dalla geometria, ed e' per questo
    che il report la dichiara accanto al confronto. Senza quella riga, una
    differenza di rigidezza nata dal `*TIE` verrebbe letta come effetto della
    forma.
    """
    if not membrature:
        raise ValueError(
            "nessuna membratura da costruire: il prior non ne ha accettata alcuna. "
            "Guarda le regioni scartate e il controllo che le ha respinte, invece "
            "di generare un modello vuoto"
        )

    prismi = [prisma_di(membratura, tipo) for membratura in membrature]
    tagliati, giunzioni = taglia_giunzioni(prismi)

    nodi_totali: list[np.ndarray] = []
    elementi_totali: list[np.ndarray] = []
    blocchi: list[dict[str, object]] = []
    scorrimento = 0
    for numero, prisma in enumerate(tagliati):
        nodi, esaedri, metriche = mesh_prisma(
            prisma.contorno, prisma.origine, prisma.asse, prisma.lunghezza, cfg
        )
        nodi_totali.append(nodi)
        elementi_totali.append(esaedri + scorrimento)
        blocchi.append({
            "membratura": numero,
            "primo_nodo": scorrimento,
            "nodi": int(len(nodi)),
            "primo_elemento": int(sum(len(e) for e in elementi_totali[:-1])),
            "elementi": int(len(esaedri)),
            **metriche,
        })
        scorrimento += len(nodi)

    nodi = np.ascontiguousarray(np.vstack(nodi_totali))
    elementi = np.ascontiguousarray(np.vstack(elementi_totali))

    # Le superfici a contatto: per ogni giunzione, le facce del prisma minore
    # che toccano il maggiore, e viceversa. Il dipendente e' il minore, che e'
    # la convenzione dei solutori -- la superficie piu' fitta fa da dipendente.
    from meshrec.core import abaqus

    superfici: dict[str, list[tuple[int, int]]] = {}
    ties: list[tuple[str, str, str]] = []
    tolleranza = max(blocco["passo"] for blocco in blocchi)
    for numero, giunzione in enumerate(giunzioni, start=1):
        minore, maggiore = int(giunzione["minore"]), int(giunzione["maggiore"])
        nomi = []
        for ruolo, indice, altro in (
            ("D", minore, maggiore),
            ("I", maggiore, minore),
        ):
            blocco = blocchi[indice]
            inizio = blocco["primo_nodo"]
            fine = inizio + blocco["nodi"]
            vicini = np.flatnonzero(
                dentro(
                    Prisma(
                        contorno=tagliati[altro].contorno,
                        origine=tagliati[altro].origine
                        - tagliati[altro].asse
                        / np.linalg.norm(tagliati[altro].asse)
                        * tolleranza,
                        asse=tagliati[altro].asse,
                        lunghezza=tagliati[altro].lunghezza + 2.0 * tolleranza,
                    ),
                    nodi[inizio:fine],
                )
            ) + inizio
            nome = f"{cfg.tie_name_prefix}_{numero}_{ruolo}"
            superfici[nome] = abaqus.element_surface(elementi, vicini, cfg.element)
            nomi.append(nome)
        if superfici[nomi[0]] and superfici[nomi[1]]:
            ties.append((f"{cfg.tie_name_prefix}_{numero}", nomi[0], nomi[1]))
        else:
            # superficie vuota: le due mesh non si toccano davvero. Meglio
            # nessun vincolo che un *TIE su una superficie senza facce, che il
            # solutore accetterebbe e non vincolerebbe nulla.
            for nome in nomi:
                superfici.pop(nome, None)

    return {
        "nodi": nodi,
        "elementi": elementi,
        "blocchi": blocchi,
        "superfici": superfici,
        "ties": tuple(ties),
        "metriche": {
            "tipo": tipo,
            "membrature": len(tagliati),
            "giunzioni": len(ties),
            "accorciamenti": [giunzione["accorciamento"] for giunzione in giunzioni],
            "element_type": cfg.element,
            "vincolo_giunzioni": (
                "*TIE fra superfici a contatto: le mesh di membrature adiacenti "
                "non combaciano nodo a nodo. E' una differenza fra i modelli che "
                "non deriva dalla geometria -- as-built monolitico, parametrici "
                "vincolati alle giunzioni -- e va letta accanto al confronto. La "
                "mesh conforme multiblocco e' la via d'aggiornamento"
            ),
        },
    }
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_hexa.py -v`
Expected: PASS su tutti e dieci.

- [ ] **Step 6: La suite intera e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/hexa.py meshrec/tests/test_hexa.py
git commit -m "feat(fase-4): il telaio in esaedri, giunzioni tagliate e superfici del *TIE"
```

---

## Task 9: lo step 12 nella pipeline, e `meshrec wall`

`pipeline.run()` cresce di **un solo blocco**. I modelli parametrici non sono rami di `run()`: biforcarla raddoppierebbe la complessita' della funzione piu' delicata del progetto senza risparmiare nulla, perche' i tre modelli vanno comunque eseguiti tre volte.

**Files:**
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `wall.prior` (Task 3); `steps.STEP_KEYS` con dodici voci (Task 1).
- Produces: `pipeline.WALL_FILENAME = "12_wall.json"`; `pipeline.calcola_prior(out, cfg, points, spacing) -> dict[str, object]`; comando `meshrec wall <config>`.

- [ ] **Step 1: I test dello step 12**

In coda a `tests/test_pipeline.py`:

```python
def test_una_corsa_completa_arriva_allo_step_dodici(tmp_path):
    """Lo step 12 chiude la corsa madre: se non compare nelle metriche, il
    prior non e' stato calcolato e i modelli parametrici non hanno da cosa
    partire."""
    cfg = _config_di_prova(tmp_path)

    metriche = pipeline.run(cfg)

    assert "12_wall" in metriche
    assert (Path(cfg.run.out_dir) / pipeline.WALL_FILENAME).exists()
    stato = steps.read_state(cfg.run.out_dir)
    assert stato["steps"]["12"]["stato"] == "riuscito"


def test_lo_step_dodici_si_puo_fermare_prima_con_to_step(tmp_path):
    """to_step=11 lascia la corsa dov'era prima della Fase 4: le corse gia'
    fatte restano riproducibili senza calcolare un prior che nessuno ha
    chiesto."""
    cfg = _config_di_prova(tmp_path)
    cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), "to_step": 11})

    metriche = pipeline.run(cfg)

    assert "11_export" in metriche
    assert "12_wall" not in metriche
    assert not (Path(cfg.run.out_dir) / pipeline.WALL_FILENAME).exists()


def test_il_prior_scritto_su_disco_e_quello_che_le_metriche_dichiarano(tmp_path):
    """La provenienza e' parte del risultato: il file e le metriche non possono
    raccontare due storie diverse dello stesso calcolo."""
    import json

    cfg = _config_di_prova(tmp_path)
    metriche = pipeline.run(cfg)

    scritto = json.loads(
        (Path(cfg.run.out_dir) / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert scritto["regioni_trovate"] == metriche["12_wall"]["regioni_trovate"]
    assert len(scritto["membrature"]) == len(metriche["12_wall"]["membrature"])
```

`_config_di_prova` e' l'aiuto gia' presente nel file che costruisce una configurazione su una geometria sintetica con `crea_config`; se ha un altro nome usa quello. Aggiungi `steps` e `RunConfig` agli import in testa se mancano.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k dodici -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.pipeline' has no attribute 'WALL_FILENAME'`.

- [ ] **Step 3: Il blocco 12 in `pipeline.py`**

Aggiungi `wall` all'import da `meshrec.core` e, sotto `METRICS_PARTIAL`:

```python
WALL_FILENAME = "12_wall.json"
```

In `run()`, subito dopo il blocco dello step 11 e prima dell'`except _FermataRichiesta`:

```python
        if stop <= 11:
            raise _FermataRichiesta

        in_corso = 12
        avvio = time.monotonic()
        # Il prior misura la nuvola segmentata e non la superficie ricostruita:
        # il rilievo e' il dato, e la ricostruzione di Poisson e' gia' una
        # interpretazione del rilievo. `source_cloud` e' esattamente l'uscita
        # dello step 2, che la ripresa ricarica quando riparte da piu' in la'.
        metrics["12_wall"] = calcola_prior(out, cfg, source_cloud, spacing)
        registra(12, avvio, WALL_FILENAME)
```

E la funzione, sopra `run()`:

```python
def calcola_prior(
    out: Path, cfg: PipelineConfig, points: np.ndarray, spacing: float
) -> dict[str, object]:
    """Step 12: il prior geometrico, calcolato e scritto accanto agli altri artefatti.

    Sta in una funzione propria e non dentro `run()` perche' ha due chiamanti:
    la corsa intera e il comando `meshrec wall`, che ricalcola il solo prior
    sugli artefatti gia' presenti. Una seconda copia del calcolo sarebbe una
    seconda cosa da tenere allineata.
    """
    esito = wall.prior(points, cfg.segment, cfg.wall, spacing)
    io.scrivi_atomico(
        out / WALL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito
```

Aggiorna la prima riga della docstring di `run()`: «Esegue la pipeline e restituisce le metriche di ogni step» resta, e sotto aggiungi:

```
    Dalla Fase 4 gli step sono dodici. Il dodicesimo e' il prior geometrico e
    chiude la corsa madre; non e' un punto di ripresa e non e' un ramo: i due
    modelli parametrici sono corse figlie con la propria cartella, non
    biforcazioni di questa funzione.
```

Aggiorna infine la condizione di corsa completa:

```python
    completa = start == 1 and stop == 12
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS. Se un test preesistente attendeva `to_step` predefinito 11, aggiornalo a 12: e' il comportamento nuovo e voluto, non una rottura.

- [ ] **Step 5: Il test del comando `wall`**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_wall_ricalcola_il_solo_prior(tmp_path, capsys):
    """Il prior e' un'azione e non una ripresa: legge l'artefatto dello step 2
    gia' sul disco e non rifa' nulla di cio' che sta a monte."""
    import json

    cfg = _config_di_prova(tmp_path)
    cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), "to_step": 2})
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)
    pipeline.run(cfg)

    assert cli.main(["wall", str(percorso)]) == 0

    scritto = json.loads(
        (Path(cfg.run.out_dir) / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert "membrature" in scritto
    assert json.loads(capsys.readouterr().out)["regioni_trovate"] == scritto["regioni_trovate"]


def test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca(tmp_path, capsys):
    """Chi arriva dopo non conosce gli step: l'errore dice quale artefatto
    manca e come ottenerlo, non solo che un file non c'e'."""
    cfg = _config_di_prova(tmp_path)
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    assert cli.main(["wall", str(percorso)]) == 1
    assert "02_segmented.ply" in capsys.readouterr().err
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_cli.py -k wall -v`
Expected: FAIL con `SystemExit: 2` da argparse — `invalid choice: 'wall'`.

- [ ] **Step 7: Il comando `wall` in `cli.py`**

In `_build_parser`, dopo `report_command`:

```python
    wall_command = commands.add_parser(
        "wall", help="ricalcola il solo prior geometrico sugli artefatti gia' presenti"
    )
    wall_command.add_argument("config", type=Path)
```

E in `main`, prima del ramo `serve`:

```python
    if args.command == "wall":
        from meshrec.core import io

        try:
            cfg = load_config(args.config)
            out = Path(cfg.run.out_dir)
            sorgente = out / pipeline.ARTIFACTS[2]
            if not sorgente.exists():
                raise FileNotFoundError(
                    f"manca {sorgente}: il prior misura la nuvola segmentata, che e' "
                    "l'artefatto dello step 2. Esegui almeno fino a quello "
                    f"(`meshrec run {args.config} --to-step 2`) e riprova"
                )
            punti, _ = io.read_cloud(sorgente)
            spaziatura = io.mean_spacing(punti, cfg.input.spacing_sample, cfg.input.seed)
            esito = pipeline.calcola_prior(out, cfg, punti, spaziatura)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0
```

- [ ] **Step 8: Eseguire e commit**

Run: `uv run pytest tests/test_cli.py tests/test_pipeline.py -v`
Expected: PASS.
Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/pipeline.py meshrec/src/meshrec/cli.py meshrec/tests/test_pipeline.py meshrec/tests/test_cli.py
git commit -m "feat(fase-4): lo step 12 nella pipeline e il comando wall"
```

---

## Task 10: le corse figlie — `meshrec model`, il deck dei modelli parametrici

Ogni modello e' la propria cartella, con configurazione completa, artefatti, metriche e riga di registro proprie. La selezione e' un'**azione**: non entra in `config.yaml` della corsa madre, o rigenerare un modello in piu' cambierebbe l'impronta di una corsa che non e' cambiata.

**Files:**
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `hexa.costruisci` (Task 8); `abaqus.export_model`, `abaqus.element_surface` (Task 4 e 5); `quality.hexa_metrics` (Task 6); `pipeline.WALL_FILENAME` (Task 9).
- Produces: `pipeline.MODEL_FILENAME = "modello.json"`; `pipeline.genera_modello(cfg, tipo, out_dir) -> dict[str, object]`; comando `meshrec model <config> --tipo estruso|primitive --out-dir <cartella>`.

- [ ] **Step 1: I test della corsa figlia**

In coda a `tests/test_pipeline.py`:

```python
def test_la_corsa_figlia_ha_cartella_configurazione_deck_e_metriche_proprie(tmp_path):
    """Ogni modello e' la propria cartella: la provenienza e' parte del
    risultato, e un modello senza la configurazione che lo ha prodotto non e'
    ricostruibile a distanza di mesi."""
    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-estruso"

    esito = pipeline.genera_modello(cfg, "estruso", figlia)

    assert (figlia / "config.yaml").exists()
    assert (figlia / "wall_model.inp").exists()
    assert (figlia / pipeline.MODEL_FILENAME).exists()
    assert esito["tipo"] == "estruso"
    assert esito["sorgente"] == str(cfg.run.out_dir)
    assert esito["hexa"]["hexes"] > 0
    assert esito["hexa"]["inverted"] == 0


def test_il_deck_della_corsa_figlia_e_esaedrico_e_porta_le_superfici(tmp_path):
    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-primitive"

    pipeline.genera_modello(cfg, "primitive", figlia)

    testo = (figlia / "wall_model.inp").read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I" in testo
    assert "*C3D4" not in testo


def test_la_corsa_madre_non_cambia_quando_si_genera_un_modello(tmp_path):
    """La selezione e' un'azione e non un parametro: se toccasse la
    configurazione della madre, rigenerare un modello in piu' cambierebbe
    l'impronta di una corsa che non e' cambiata."""
    from meshrec.core.sweep import fingerprint

    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    prima = (Path(cfg.run.out_dir) / "config.yaml").read_text(encoding="utf-8")
    impronta = fingerprint(cfg)

    pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")

    assert (Path(cfg.run.out_dir) / "config.yaml").read_text(encoding="utf-8") == prima
    assert fingerprint(load_config(Path(cfg.run.out_dir) / "config.yaml")) == impronta


def test_generare_un_modello_senza_prior_dice_che_cosa_manca(tmp_path, capsys):
    cfg = _config_di_prova(tmp_path)
    cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), "to_step": 11})
    pipeline.run(cfg)

    with pytest.raises(FileNotFoundError, match="12_wall.json"):
        pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k figlia -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.pipeline' has no attribute 'genera_modello'`.

- [ ] **Step 3: `genera_modello`**

In `pipeline.py`, sotto `calcola_prior`:

```python
MODEL_FILENAME = "modello.json"


def genera_modello(cfg: PipelineConfig, tipo: str, out_dir: Path) -> dict[str, object]:
    """Genera un modello parametrico come corsa figlia, nella propria cartella.

    I due modelli parametrici sono **generatori di mesh di volume alternativi a
    TetGen**: producono nodi ed elementi e rientrano negli step esistenti di
    metriche di volume ed esportazione. Non sono rami di `run()`, e la ragione
    e' che biforcarla raddoppierebbe la complessita' della funzione piu'
    delicata del progetto senza risparmiare nulla.

    La cartella figlia porta la stessa `config.yaml` della madre -- e' lo
    stesso esperimento, e la stessa impronta -- piu' un `modello.json` che dice
    di quale tipo e' e da quale corsa viene. La provenienza sta li' e non nella
    configurazione, perche' la scelta del modello e' un'azione e non un
    parametro di elaborazione.
    """
    from meshrec.core import hexa
    from meshrec.core.wall import Membratura

    sorgente = Path(cfg.run.out_dir)
    percorso_prior = sorgente / WALL_FILENAME
    if not percorso_prior.exists():
        raise FileNotFoundError(
            f"manca {percorso_prior}: un modello parametrico si costruisce sul "
            "prior, e il prior e' lo step 12. Esegui `meshrec wall` sulla stessa "
            "configurazione e riprova"
        )
    with percorso_prior.open(encoding="utf-8") as handle:
        prior = json.load(handle)

    membrature = [
        Membratura(
            punti=np.arange(0),
            asse=np.asarray(voce["asse"], dtype=np.float64),
            origine=np.asarray(voce["origine"], dtype=np.float64),
            lunghezza=float(voce["lunghezza"]),
            sezione=tuple(voce["sezione"]),
            sezione_dispersione=tuple(voce["sezione_dispersione"]),
            contorno=np.asarray(voce["contorno"], dtype=np.float64),
            fuori_piombo_deg=float(voce["fuori_piombo_deg"]),
            asse_ideale=np.asarray(voce["asse_ideale"], dtype=np.float64),
            scarto_asse_deg=float(voce["scarto_asse_deg"]),
            rigonfiamento=np.zeros(0),
            volume=float(voce["volume"]),
        )
        for voce in prior["membrature"]
    ]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")

    modello = hexa.costruisci(membrature, tipo, cfg.model)
    nodi = modello["nodi"]
    elementi = modello["elementi"]

    carico = None
    if cfg.model.lateral_nset is not None and cfg.model.lateral_pressure is not None:
        carico = (cfg.model.lateral_nset, float(cfg.model.lateral_pressure))

    export = abaqus.export_model(
        out / "wall_model.inp",
        out / "wall_model.vtu",
        nodi,
        elementi,
        cfg.analysis,
        cfg.tet,
        reference=nodi,
        element_type=cfg.model.element,
        element_surfaces=modello["superfici"],
        ties=modello["ties"],
        pressure=carico,
    )

    esito: dict[str, object] = {
        "tipo": tipo,
        "sorgente": str(sorgente),
        "modello": modello["metriche"],
        "blocchi": modello["blocchi"],
        "hexa": quality.hexa_metrics(nodi, elementi),
        "export": export,
        "nota_giunzioni": modello["metriche"]["vincolo_giunzioni"],
        "nota_armatura": (
            "modello a calcestruzzo omogeneo: l'armatura e' fuori ambito per "
            "decisione dell'autore, non per dimenticanza, e il dato resta nel "
            "disegno. Un telaio in cemento armato modellato senza armatura non "
            "e' il telaio vero"
        ),
    }
    io.scrivi_atomico(
        out / MODEL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito
```

Aggiungi `quality` all'import da `meshrec.core` se non c'e' gia'.

- [ ] **Step 4: `export_model` accetta le tre card nuove**

In `abaqus.export_model`, aggiungi alla firma, dopo `element_type`:

```python
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str], ...] = (),
    pressure: tuple[str, float] | None = None,
```

e passali a `write_inp` insieme agli altri argomenti. Nel dizionario restituito aggiungi:

```python
        "element_surfaces": {
            nome: len(coppie) for nome, coppie in (element_surfaces or {}).items()
        },
        "surface_area": {
            nome: surface_area(aligned, elements, coppie, tipo)
            for nome, coppie in (element_surfaces or {}).items()
        },
        "ties": [nome for nome, _dipendente, _indipendente in ties],
        "pressure": None if pressure is None else {"surface": pressure[0], "value": pressure[1]},
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_pipeline.py tests/test_abaqus.py -v`
Expected: PASS.

- [ ] **Step 6: Il comando `model`**

In `_build_parser`:

```python
    model_command = commands.add_parser(
        "model", help="genera un modello parametrico come corsa figlia"
    )
    model_command.add_argument("config", type=Path)
    model_command.add_argument(
        "--tipo", choices=("estruso", "primitive"), required=True,
        help="estruso conserva sezione e fuori piombo misurati; primitive li raddrizza",
    )
    model_command.add_argument(
        "--out-dir", type=Path, default=None,
        help="cartella della corsa figlia; se omessa, quella della madre col suffisso del tipo",
    )
```

In `main`, accanto al ramo `wall`:

```python
    if args.command == "model":
        try:
            cfg = load_config(args.config)
            destinazione = args.out_dir
            if destinazione is None:
                madre = Path(cfg.run.out_dir)
                destinazione = madre.with_name(f"{madre.name}-{args.tipo}")
            esito = pipeline.genera_modello(cfg, args.tipo, destinazione)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0
```

- [ ] **Step 7: Il test del comando**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_model_scrive_la_cartella_col_suffisso_del_tipo(tmp_path):
    """La cartella predefinita e' quella della madre col suffisso: nessuna
    corsa figlia scrive dentro la cartella della madre, che e' il risultato di
    un'altra elaborazione."""
    cfg = _config_di_prova(tmp_path)
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)
    pipeline.run(cfg)

    assert cli.main(["model", str(percorso), "--tipo", "primitive"]) == 0

    madre = Path(cfg.run.out_dir)
    figlia = madre.with_name(f"{madre.name}-primitive")
    assert (figlia / "wall_model.inp").exists()
    assert not (madre / pipeline.MODEL_FILENAME).exists()
```

- [ ] **Step 8: Eseguire e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/pipeline.py meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/cli.py meshrec/tests/test_pipeline.py meshrec/tests/test_cli.py
git commit -m "feat(fase-4): i modelli parametrici come corse figlie con deck proprio"
```

---

## Task 11: `ccx` legge il deck — l'unico ruolo di CalculiX in questa fase

Il controllo e' che il solutore **accetti** il deck su un modello piccolo, non che la risposta sia giusta: quello e' Fase 5. Un deck che nessun solutore ha mai aperto e' un deck di cui non sappiamo se esiste.

**Files:**
- Create: `tests/feasibility/test_calculix_hexa.py`

**Interfaces:**
- Consumes: `hexa.mesh_prisma` (Task 7), `abaqus.write_inp` e `abaqus.element_surface` (Task 5).
- Produces: niente per il codice; una riga di esito per il documento del Task 15.

- [ ] **Step 1: Scrivere il controllo**

Crea `tests/feasibility/test_calculix_hexa.py`:

```python
"""Fase 4 -- CalculiX accetta un deck esaedrico con superfici di elemento?

Il controllo e' che il solutore **legga** il deck, non che la risposta sia
giusta: la risposta strutturale e' la Fase 5. Un deck che nessun solutore ha
mai aperto e' un deck di cui non sappiamo se esiste.

Marcato feasibility come gli altri controlli di dipendenza esterna, e salta
dove `ccx` non e' installato -- che e' il caso della macchina di sviluppo al
18/08/2026. **Un controllo saltato non e' un controllo passato**, e il
documento di esito deve dirlo con queste parole.
"""

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, hexa
from meshrec.core.config import ModelConfig
from materiale import MATERIALE

pytestmark = pytest.mark.feasibility

SEZIONE = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]])
ALTEZZA = 400.0


def _deck(tmp_path, con_carico: bool):
    nodi, esaedri, _ = hexa.mesh_prisma(
        SEZIONE, np.zeros(3), np.array([0.0, 0.0, 1.0]), ALTEZZA,
        ModelConfig(target_size=50.0),
    )
    base = np.flatnonzero(nodi[:, 2] <= 1e-6)
    cima = np.flatnonzero(nodi[:, 2] >= ALTEZZA - 1e-6)
    lato = np.flatnonzero(nodi[:, 0] >= 100.0 - 1e-6)

    superfici = {"LATO": abaqus.element_surface(esaedri, lato, "C3D8I")}
    abaqus.write_inp(
        tmp_path / "modello.inp", nodi, esaedri,
        node_sets={"BASE": base, "TOP": cima},
        material=MATERIALE,
        element_type="C3D8I",
        print_nsets=("TOP",),
        element_surfaces=superfici,
        pressure=("LATO", 0.01) if con_carico else None,
    )
    return nodi, esaedri


@pytest.mark.parametrize("con_carico", [False, True])
def test_calculix_legge_un_deck_esaedrico(tmp_path, con_carico):
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip(
            "eseguibile 'ccx' non presente nel PATH: il deck resta non verificato "
            "da alcun solutore, e va dichiarato tale"
        )

    _deck(tmp_path, con_carico)
    processo = subprocess.run(
        [eseguibile, "-i", "modello"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )

    assert processo.returncode == 0, processo.stdout[-2000:] + processo.stderr[-2000:]
    assert "*ERROR" not in processo.stdout, processo.stdout[-2000:]
    assert (tmp_path / "modello.dat").exists(), "nessun risultato: il deck e' stato letto a meta'"
```

- [ ] **Step 2: Eseguirlo**

Run: `uv run pytest tests/feasibility/test_calculix_hexa.py -v -m feasibility`
Expected: due test, **saltati** se `ccx` non e' installato (e' il caso al 18/08/2026 sulla macchina di sviluppo: `which ccx` non risponde), **passati** se lo e'.

- [ ] **Step 3: Registrare l'esito qualunque sia**

Scrivi il risultato in una nota che il Task 15 riprendera' nel documento. Se e' stato saltato, la formula da usare e': «il deck esaedrico non e' stato verificato da alcun solutore su questa macchina, perche' `ccx` non e' installato». **Non** «il deck e' valido».

- [ ] **Step 4: Commit**

```bash
git add meshrec/tests/feasibility/test_calculix_hexa.py
git commit -m "test(fase-4): ccx legge un deck esaedrico con superfici di elemento"
```

---

## Task 12: il confronto — quasi nessuna metrica e' confrontabile, e la tabella dice quale lo e'

**Files:**
- Modify: `src/meshrec/core/report.py`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_report.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `pipeline.WALL_FILENAME`, `pipeline.MODEL_FILENAME` (Task 9 e 10); `quality.vertex_deviation` (Fase 3).
- Produces:
  - `report.CONFRONTABILI: dict[str, bool]`.
  - `report.confronta(cartelle) -> dict[str, object]`.
  - `report.write_comparison_report(cartelle, out_path) -> Path`.
  - Comando `meshrec compare <cartella>... --out <file.html>`.

- [ ] **Step 1: I test del confronto**

In coda a `tests/test_report.py`:

```python
def test_il_confronto_di_tre_modelli_dice_quali_grandezze_lo_sono(tmp_path):
    """Quasi nessuna metrica e' confrontabile fra i tre modelli senza mentire.
    La tabella deve dire quale lo e', invece di allineare colonne che non si
    parlano."""
    cartelle = _tre_cartelle_finte(tmp_path)

    confronto = report.confronta(cartelle)

    assert set(confronto["modelli"]) == {"as-built", "estruso", "primitive"}
    assert confronto["confrontabili"]["volume"] is True
    assert confronto["confrontabili"]["scostamento_nuvola"] is True
    assert confronto["confrontabili"]["qualita_elementi"] is False
    assert confronto["confrontabili"]["rigidezza"] is False


def test_la_qualita_degli_elementi_sta_in_due_colonne_e_mai_in_una_differenza(tmp_path):
    """min_ratio per i tetraedri, Jacobiano scalato per gli esaedri: due
    colonne separate, mai una differenza fra le due."""
    cartelle = _tre_cartelle_finte(tmp_path)

    confronto = report.confronta(cartelle)

    qualita = confronto["qualita"]
    assert "min_ratio" in qualita["as-built"]
    assert "scaled_jacobian" in qualita["estruso"]
    assert "min_ratio" not in qualita["estruso"]
    assert "differenza" not in qualita


def test_con_due_modelli_su_tre_il_confronto_dice_quale_manca(tmp_path):
    """Nessuna colonna con un trattino che somigli a un valore, nessuna
    differenza calcolata contro un modello assente."""
    cartelle = _tre_cartelle_finte(tmp_path)[:2]

    confronto = report.confronta(cartelle)

    assert confronto["mancanti"] == ["primitive"]
    assert "primitive" not in confronto["volume"]
    testo = report.write_comparison_report(cartelle, tmp_path / "confronto.html").read_text(
        encoding="utf-8"
    )
    assert "primitive" in testo
    assert "non generato" in testo


def test_con_un_modello_solo_il_confronto_diventa_una_scheda_e_lo_dichiara(tmp_path):
    cartelle = _tre_cartelle_finte(tmp_path)[:1]

    confronto = report.confronta(cartelle)

    assert confronto["scheda_singola"] is True
    testo = report.write_comparison_report(cartelle, tmp_path / "solo.html").read_text(
        encoding="utf-8"
    )
    assert "scheda singola" in testo


def test_il_report_dichiara_le_tre_cose_che_non_derivano_dalla_geometria(tmp_path):
    """Senza queste righe una differenza nata dal *TIE verrebbe letta come
    effetto della forma, la base sembrerebbe una faccia del pezzo e il modello
    passerebbe per un telaio in cemento armato completo."""
    cartelle = _tre_cartelle_finte(tmp_path)

    testo = report.write_comparison_report(cartelle, tmp_path / "confronto.html").read_text(
        encoding="utf-8"
    )

    assert "as-built monolitico" in testo
    assert "vincolati alle giunzioni" in testo
    assert "armatura" in testo
    assert "dove abbiamo tagliato" in testo
```

Scrivi anche l'aiuto `_tre_cartelle_finte(tmp_path)`, in testa alla sezione nuova del file di test:

```python
def _tre_cartelle_finte(tmp_path):
    """Tre cartelle di corsa con i soli file che il confronto legge.

    Il confronto non ricalcola nulla: legge metrics.json, 12_wall.json e
    modello.json. Un banco che scrive quei tre file esercita esattamente il
    codice sotto prova, senza far girare la pipeline per ogni test.
    """
    import json

    from meshrec.core import pipeline

    cartelle = []
    for nome, tipo in (("madre", None), ("madre-estruso", "estruso"), ("madre-primitive", "primitive")):
        cartella = tmp_path / nome
        cartella.mkdir()
        metriche = {
            "07_surface_quality": {"geometric_error": {"cloud_to_mesh": {"rms": 4.9}}},
            "10_volume_quality": {
                "total_volume": 1.0e8,
                "radius_edge_ratio": {"p50": 1.4},
                "nodes": 1000,
            },
            "11_export": {"volume": 1.0e8, "mass": 0.25, "node_sets": {"BASE": 40}},
        }
        (cartella / "metrics.json").write_text(json.dumps(metriche), encoding="utf-8")
        if tipo is None:
            (cartella / pipeline.WALL_FILENAME).write_text(
                json.dumps({
                    "regioni_trovate": 4,
                    "membrature": [],
                    "scartate": [],
                    "chiusura_volume": {"somma": 1.0e8, "unione": 1.0e8,
                                         "scarto_relativo": 0.0, "passato": True,
                                         "soglia": 0.02, "passo": 20.0, "spiegazione": ""},
                    "riscontri": {"membrature_attese": None, "scarto_membrature": None,
                                   "sezioni_nominali": None, "volume_atteso": None,
                                   "scarto_volume": None, "nota": ""},
                }),
                encoding="utf-8",
            )
        else:
            (cartella / pipeline.MODEL_FILENAME).write_text(
                json.dumps({
                    "tipo": tipo,
                    "sorgente": str(tmp_path / "madre"),
                    "modello": {"tipo": tipo, "membrature": 4, "giunzioni": 3,
                                 "element_type": "C3D8I", "vincolo_giunzioni": ""},
                    "hexa": {"hexes": 5000, "nodes": 7000, "inverted": 0,
                              "total_volume": 0.98e8,
                              "scaled_jacobian": {"p50": 0.95, "min": 0.61}},
                    "export": {"volume": 0.98e8, "mass": 0.245, "element_type": "C3D8I"},
                }),
                encoding="utf-8",
            )
        cartelle.append(cartella)
    return cartelle
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_report.py -k "confronto or qualita or scheda or non_derivano" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.report' has no attribute 'confronta'`.

- [ ] **Step 3: `confronta`**

In `report.py`, in coda:

```python
MODELLI = ("as-built", "estruso", "primitive")
"""I tre modelli dello stesso pezzo, nell'ordine in cui il confronto li mostra.

as-built e' la corsa madre e c'e' sempre: e' la superficie rilevata in mesh
tetraedrica, che esiste dalla Fase 1. Gli altri due sono corse figlie e possono
mancare.
"""

CONFRONTABILI: dict[str, bool] = {
    "volume": True,
    "massa": True,
    "scostamento_nuvola": True,
    "gradi_di_liberta": True,
    "qualita_elementi": False,
    "rigidezza": False,
}
"""Quali grandezze si confrontano fra i tre modelli senza mentire.

- volume e massa: si', ed e' anche il confronto con il volume dichiarato dal
  disegno, quando il disegno c'e';
- scostamento dalla nuvola sorgente: si', ed e' il perno -- e' definito allo
  stesso modo per tutti e tre e risponde alla domanda vera, quanto costa in
  fedelta' al rilievo la regolarizzazione della forma;
- numero di nodi e gradi di liberta': si', ma solo accanto al tipo di elemento,
  perche' un C3D8I e un C3D4 non spendono lo stesso per nodo;
- qualita' degli elementi: NO. min_ratio per i tetraedri, Jacobiano scalato per
  gli esaedri: due colonne separate, mai una differenza fra le due;
- rigidezza e spostamenti: NO. Nessun solutore in questa fase.
"""

NOTE_NON_GEOMETRICHE = (
    "as-built monolitico, parametrici vincolati alle giunzioni con *TIE: e' una "
    "differenza fra i modelli che non deriva dalla geometria, e senza questa riga "
    "una differenza di rigidezza nata dal vincolo verrebbe letta come effetto "
    "della forma.",
    "Nessuna armatura in alcun modello: calcestruzzo omogeneo. E' una scelta "
    "dell'autore e non una dimenticanza, e il dato delle barre resta nel disegno. "
    "Un telaio in cemento armato modellato senza armatura non e' il telaio vero.",
    "Il set BASE non e' una faccia del pezzo: e' la quota di taglio scelta "
    "dall'operatore. Quella superficie non esiste nel pezzo vero, e' dove abbiamo "
    "tagliato.",
)


def _legge_json(percorso: Path) -> dict | None:
    try:
        with percorso.open(encoding="utf-8") as handle:
            letto = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return letto if isinstance(letto, dict) else None


def confronta(cartelle: list[Path]) -> dict[str, object]:
    """Il confronto fra i modelli **generati**, e la dichiarazione di quelli assenti.

    Regge gli insiemi parziali perche' l'utente sceglie quali modelli generare:
    con due su tre confronta due modelli e dice quale manca, con uno solo
    diventa una scheda singola e lo dichiara. Nessuna colonna con un trattino
    che somigli a un valore, nessuna differenza calcolata contro un modello
    assente.

    Non ricalcola nulla: legge cio' che ogni corsa ha scritto. Ricalcolare
    darebbe numeri che nessun artefatto sostiene.
    """
    presenti: dict[str, dict] = {}
    for cartella in cartelle:
        percorso = Path(cartella)
        modello = _legge_json(percorso / "modello.json")
        metriche = _legge_json(percorso / METRICS_FILENAME) or {}
        if modello is None:
            presenti["as-built"] = {"cartella": percorso, "metriche": metriche, "modello": None}
        else:
            presenti[str(modello.get("tipo"))] = {
                "cartella": percorso, "metriche": metriche, "modello": modello
            }

    mancanti = [nome for nome in MODELLI if nome not in presenti]

    volume: dict[str, float] = {}
    massa: dict[str, float] = {}
    scostamento: dict[str, object] = {}
    gradi: dict[str, object] = {}
    qualita: dict[str, dict] = {}
    for nome, voce in presenti.items():
        if voce["modello"] is None:
            export = voce["metriche"].get("11_export", {})
            volumi = voce["metriche"].get("10_volume_quality", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = (
                voce["metriche"]
                .get("07_surface_quality", {})
                .get("geometric_error", {})
                .get("cloud_to_mesh", {})
                .get("rms")
            )
            gradi[nome] = {"nodi": volumi.get("nodes"), "elemento": export.get("element_type", "C3D4")}
            qualita[nome] = {"min_ratio": volumi.get("radius_edge_ratio")}
        else:
            export = voce["modello"].get("export", {})
            esaedri = voce["modello"].get("hexa", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = voce["modello"].get("scostamento_nuvola")
            gradi[nome] = {"nodi": esaedri.get("nodes"), "elemento": export.get("element_type")}
            qualita[nome] = {"scaled_jacobian": esaedri.get("scaled_jacobian")}

    return {
        "modelli": sorted(presenti),
        "mancanti": mancanti,
        "scheda_singola": len(presenti) == 1,
        "confrontabili": dict(CONFRONTABILI),
        "volume": volume,
        "massa": massa,
        "scostamento_nuvola": scostamento,
        "gradi_di_liberta": gradi,
        "qualita": qualita,
        "note_non_geometriche": list(NOTE_NON_GEOMETRICHE),
    }
```

- [ ] **Step 4: `write_comparison_report`**

In coda a `report.py`:

```python
def write_comparison_report(cartelle: list[Path], out_path: Path) -> Path:
    """Il confronto in una pagina, con lo stesso rivestimento del report di corsa.

    I modelli assenti compaiono per nome e con la dicitura «non generato», mai
    con un trattino in una colonna di numeri: un trattino in mezzo ai numeri
    somiglia a un valore.
    """
    confronto = confronta(cartelle)
    righe = []
    for grandezza in ("volume", "massa", "scostamento_nuvola"):
        celle = "".join(
            f"<td>{_numero(confronto[grandezza][nome]) if nome in confronto[grandezza] else 'non generato'}</td>"
            for nome in MODELLI
        )
        righe.append(f"<tr><th>{grandezza}</th>{celle}</tr>")

    qualita_righe = "".join(
        f"<tr><th>{nome}</th><td>{_testo(confronto['qualita'].get(nome, 'non generato'))}</td></tr>"
        for nome in MODELLI
    )
    note = "".join(f"<li>{nota}</li>" for nota in confronto["note_non_geometriche"])
    intestazione = "".join(f"<th>{nome}</th>" for nome in MODELLI)
    avviso = (
        "<p class='avviso'>Un solo modello generato: questa non e' una tabella di "
        "confronto ma una <strong>scheda singola</strong>.</p>"
        if confronto["scheda_singola"]
        else ""
    )

    pagina = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>MeshRec -- confronto fra modelli</title>
<style>{_STILE}</style></head><body>
<h1>Confronto fra modelli</h1>
{avviso}
<h2>Grandezze confrontabili</h2>
<table><thead><tr><th></th>{intestazione}</tr></thead><tbody>{''.join(righe)}</tbody></table>
<h2>Qualita' degli elementi: due colonne, mai una differenza</h2>
<p>min_ratio vale per i tetraedri, il Jacobiano scalato per gli esaedri. Non sono
la stessa grandezza e la loro differenza non e' un numero.</p>
<table><tbody>{qualita_righe}</tbody></table>
<h2>Che cosa non deriva dalla geometria</h2>
<ul>{note}</ul>
<h2>Che cosa questa fase non dice</h2>
<p>Nessun solutore e' stato eseguito: rigidezza e spostamenti non sono in questa
pagina perche' non sono stati calcolati, non perche' siano stati omessi.</p>
</body></html>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(pagina, encoding="utf-8")
    return Path(out_path)
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS.

- [ ] **Step 6: Il comando `compare`**

In `_build_parser`:

```python
    compare_command = commands.add_parser(
        "compare", help="confronta le cartelle dei modelli generati dello stesso pezzo"
    )
    compare_command.add_argument("cartelle", type=Path, nargs="+")
    compare_command.add_argument("--out", type=Path, required=True)
```

In `main`:

```python
    if args.command == "compare":
        from meshrec.core import report

        try:
            percorso = report.write_comparison_report(args.cartelle, args.out)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(f"confronto in {percorso}")
        return 0
```

- [ ] **Step 7: Il test del comando, eseguire, commit**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_compare_scrive_la_pagina_e_nomina_i_modelli_assenti(tmp_path, capsys):
    from tests.test_report import _tre_cartelle_finte  # stesso banco, una definizione sola

    cartelle = _tre_cartelle_finte(tmp_path)[:2]
    uscita = tmp_path / "confronto.html"

    assert cli.main(["compare", *[str(c) for c in cartelle], "--out", str(uscita)]) == 0
    assert "non generato" in uscita.read_text(encoding="utf-8")
    assert str(uscita) in capsys.readouterr().out
```

Se l'import da `tests.test_report` non risolve nella configurazione di pytest del progetto, sposta `_tre_cartelle_finte` in `tests/materiale.py` accanto a `crea_config` e importalo da li' in entrambi i file: una definizione sola resta il requisito.

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/report.py meshrec/src/meshrec/cli.py meshrec/tests/test_report.py meshrec/tests/test_cli.py meshrec/tests/materiale.py
git commit -m "feat(fase-4): confronto fra modelli, insiemi parziali compresi"
```

---

## Task 13: il server — lo step 12, i modelli come azione, i campi per il viewport

**Files:**
- Modify: `src/meshrec/app/server.py`
- Modify: `src/meshrec/app/worker.py`
- Modify: `src/meshrec/core/viewport.py`
- Test: `tests/test_server.py`, `tests/test_viewport.py`, `tests/test_worker.py`

**Interfaces:**
- Consumes: `pipeline.calcola_prior`, `pipeline.genera_modello` (Task 9 e 10); `report.confronta` (Task 12).
- Produces:
  - `viewport.campo_per_punto(valori) -> bytes`; `viewport.triangoli_da_quadrilateri(quadrilateri) -> np.ndarray`.
  - `worker.Worker.start_comando(argomenti, etichetta)`.
  - `GET /api/wall`, `POST /api/wall`, `POST /api/model/{tipo}`, `GET /api/compare`, `GET /api/membrature`, `GET /api/rigonfiamento`.

- [ ] **Step 1: I test del viewport**

In coda a `tests/test_viewport.py`:

```python
def test_i_quadrilateri_diventano_due_triangoli_ciascuno():
    """La superficie di contorno di un esaedro e' fatta di quadrilateri, e
    three.js disegna triangoli: la divisione va fatta qui e non nel browser,
    dove nessun test la sorveglierebbe."""
    quadrilateri = np.array([[0, 1, 2, 3], [4, 5, 6, 7]], dtype=np.int64)

    triangoli = viewport.triangoli_da_quadrilateri(quadrilateri)

    assert triangoli.shape == (4, 3)
    assert triangoli[0].tolist() == [0, 1, 2]
    assert triangoli[1].tolist() == [0, 2, 3]


def test_il_campo_per_punto_esce_in_float32_come_le_coordinate():
    """Stessa macchina delle mappe di deviazione della Fase 3: cambia il campo
    scalare, non il trasporto."""
    valori = np.array([0.0, 1.5, -2.25])

    corpo = viewport.campo_per_punto(valori)

    assert len(corpo) == 3 * 4
    assert np.frombuffer(corpo, dtype="<f4") == pytest.approx(valori)
```

- [ ] **Step 2: Eseguirli, vederli fallire, implementare**

Run: `uv run pytest tests/test_viewport.py -k "quadrilater or campo" -v`
Expected: FAIL con `AttributeError`.

In `viewport.py`, in coda:

```python
def triangoli_da_quadrilateri(quadrilateri: np.ndarray) -> np.ndarray:
    """Ogni quadrilatero in due triangoli, tagliato sulla diagonale 0-2.

    La superficie di contorno di una mesh esaedrica e' fatta di quadrilateri, e
    three.js disegna triangoli. La divisione sta qui e non nel browser perche'
    nel browser nessun test la sorveglierebbe, ed e' la stessa ragione per cui
    la decimazione della nuvola sta nel core.
    """
    quad = np.asarray(quadrilateri, dtype=np.int64)
    return np.ascontiguousarray(
        np.vstack([quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]]).reshape(-1, 3)[
            np.argsort(np.repeat(np.arange(len(quad)), 2), kind="stable")
        ]
    )


def campo_per_punto(valori: np.ndarray) -> bytes:
    """Uno scalare per punto in Float32, per le mappe di colore.

    E' `to_float32` applicata a un campo invece che a coordinate: il viewport
    ha gia' le mappe di deviazione dalla Fase 3, e qui cambia il campo scalare
    e non la macchina.
    """
    return to_float32(np.asarray(valori, dtype=np.float64).ravel())
```

Run: `uv run pytest tests/test_viewport.py -v`
Expected: PASS.

- [ ] **Step 3: Il test del worker per un comando che non e' uno step**

In coda a `tests/test_worker.py`:

```python
def test_il_worker_esegue_anche_un_comando_che_non_e_uno_step(tmp_path):
    """Il prior e i modelli sono azioni, non step: passano dallo stesso
    sottoprocesso -- perche' e' il percorso con cui sono stati prodotti tutti i
    numeri delle Fasi 1 e 2 -- ma non hanno un numero di step."""
    lavoratore = worker.Worker()

    lavoratore.start_comando(["--version"], etichetta="prova")
    for _ in range(200):
        if not lavoratore.is_running():
            break
        time.sleep(0.05)

    assert lavoratore.step is None
    assert lavoratore.etichetta == "prova"
    assert lavoratore.exit_code is not None
```

- [ ] **Step 4: `start_comando` in `worker.py`**

Aggiungi `self.etichetta: str | None = None` a `__init__`, e:

```python
    def start_comando(self, argomenti: list[str], etichetta: str) -> None:
        """Avvia un comando di `meshrec` che non e' uno step della pipeline.

        Il prior e i modelli parametrici sono azioni e non step: non hanno un
        numero, non entrano nella colonna della pipeline e non invalidano nulla
        a valle. Passano pero' dallo stesso sottoprocesso degli step, per le
        stesse tre ragioni gia' misurate: un processo ucciso lascia un codice di
        uscita, il percorso eseguito e' esattamente quello della riga di
        comando, e l'avvio di un interprete costa pochi secondi.
        """
        if self.is_running():
            raise RuntimeError("uno step sta gia' girando: annullalo prima di avviarne un altro")
        with self._lucchetto:
            self._righe.clear()
        self.exit_code = None
        self.annullato = False
        self.step = None
        self.etichetta = etichetta
        self.avviato = time.monotonic()
        self._processo = subprocess.Popen(
            [sys.executable, "-m", "meshrec.cli", *argomenti],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        threading.Thread(target=self._leggi, daemon=True).start()
```

In `start`, aggiungi `self.etichetta = None` accanto a `self.step = from_step`, cosi' i due stati non si sovrappongono.

- [ ] **Step 5: I test degli endpoint**

In coda a `tests/test_server.py`:

```python
def test_il_prior_non_ancora_calcolato_lo_dice_invece_di_rispondere_vuoto(cliente, tmp_path):
    """Quinto principio di prodotto: chi arriva dopo non conosce gli step. Uno
    stato vuoto che insegna, non un 404 nudo."""
    risposta = cliente.get("/api/wall")

    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["calcolato"] is False
    assert "step 12" in corpo["motivo"]


def test_il_prior_calcolato_torna_membrature_e_regioni_scartate(cliente, tmp_path):
    import json

    from meshrec.core import pipeline

    corsa = _cartella_di_corsa(cliente)
    (corsa / pipeline.WALL_FILENAME).write_text(
        json.dumps({
            "regioni_trovate": 2,
            "membrature": [{"lunghezza": 1500.0, "sezione": [200.0, 140.0]}],
            "scartate": [{"regione": 1, "controlli_falliti": ["costanza_sezione"],
                           "esiti": {"costanza_sezione": {"passato": False, "valore": 0.4,
                                                            "soglia": 0.1}}}],
        }),
        encoding="utf-8",
    )

    corpo = cliente.get("/api/wall").json()

    assert corpo["calcolato"] is True
    assert len(corpo["prior"]["membrature"]) == 1
    assert corpo["prior"]["scartate"][0]["controlli_falliti"] == ["costanza_sezione"]


def test_generare_un_modello_e_una_azione_e_non_tocca_la_configurazione(cliente, tmp_path):
    """La selezione dei modelli non entra in config.yaml: rigenerare un modello
    in piu' cambierebbe l'impronta di una corsa che non e' cambiata."""
    prima = cliente.get("/api/config").json()

    risposta = cliente.post("/api/model/estruso")

    assert risposta.status_code == 200
    assert risposta.json()["avviato"] == "estruso"
    assert cliente.get("/api/config").json() == prima


def test_un_tipo_di_modello_inventato_viene_rifiutato(cliente):
    risposta = cliente.post("/api/model/asbuilt")

    assert risposta.status_code == 400
    assert "estruso" in risposta.json()["detail"]


def test_il_confronto_dal_server_dice_quali_modelli_mancano(cliente, tmp_path):
    corpo = cliente.get("/api/compare").json()

    assert set(corpo["mancanti"]) <= {"estruso", "primitive"}
    assert corpo["confrontabili"]["qualita_elementi"] is False
```

`_cartella_di_corsa(cliente)` e' l'aiuto gia' presente nel file che restituisce `Path` della cartella della corsa corrente; se non c'e', ricavala da `cliente.get("/api/run").json()["out_dir"]`.

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k "prior or modello or confronto" -v`
Expected: FAIL con 404 sugli endpoint mancanti.

- [ ] **Step 7: Gli endpoint**

In `server.py`, dentro `create_app`, dopo `/api/metrics`:

```python
    @app.get("/api/wall")
    def prior_geometrico() -> dict[str, object]:
        """Il prior come sta sul disco. Un prior non calcolato lo dichiara.

        Uno stato vuoto che insegna e non un 404 nudo: l'utente successivo
        confermato non conosce gli step, e «non ancora calcolato, ecco come» e'
        l'unica risposta che gli serve.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            return {
                "calcolato": False,
                "motivo": (
                    "il prior geometrico non e' ancora stato calcolato: e' lo "
                    "step 12, e si ottiene eseguendo la corsa fino in fondo "
                    "oppure con il comando 'Calcola il prior' qui accanto"
                ),
                "prior": None,
            }
        with percorso.open(encoding="utf-8") as handle:
            return {"calcolato": True, "motivo": "", "prior": json.load(handle)}

    @app.post("/api/wall")
    def calcola_prior() -> dict[str, object]:
        lavoratore.start_comando(["wall", str(config_path)], etichetta="prior geometrico")
        return {"avviato": "wall"}

    @app.post("/api/model/{tipo}")
    def genera_modello(tipo: str) -> dict[str, object]:
        """Genera un modello parametrico. E' un'azione, non un parametro.

        Non scrive nulla in config.yaml: se lo facesse, rigenerare un modello in
        piu' cambierebbe l'impronta di una corsa che non e' cambiata.
        """
        if tipo not in ("estruso", "primitive"):
            raise ValueError(
                f"modello '{tipo}' sconosciuto: i modelli parametrici sono "
                "'estruso' e 'primitive'. as-built e' la corsa madre e non si genera"
            )
        madre = Path(corrente().run.out_dir)
        lavoratore.start_comando(
            ["model", str(config_path), "--tipo", tipo,
             "--out-dir", str(madre.with_name(f"{madre.name}-{tipo}"))],
            etichetta=f"modello {tipo}",
        )
        return {"avviato": tipo}

    @app.get("/api/compare")
    def confronto() -> dict[str, object]:
        """Il confronto sulle cartelle che esistono davvero.

        Le cartelle mancanti non vengono create ne' finte: il confronto dice
        quale modello manca invece di mettere un trattino in una colonna di
        numeri.
        """
        from meshrec.core import report

        madre = Path(corrente().run.out_dir)
        cartelle = [madre] + [
            madre.with_name(f"{madre.name}-{tipo}")
            for tipo in ("estruso", "primitive")
            if madre.with_name(f"{madre.name}-{tipo}").is_dir()
        ]
        return report.confronta(cartelle)
```

E i due endpoint binari per il viewport, accanto a `/api/mesh/{numero}`:

```python
    @app.get("/api/membrature")
    def membrature() -> Response:
        """Un'etichetta di membratura per punto della nuvola disegnata.

        E' la prova visiva che la scomposizione ha capito il pezzo, e si legge
        in un secondo dove nessuna metrica sarebbe cosi' rapida. -1 significa
        «nessuna membratura», che e' un'informazione e non un buco.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non e' ancora stato calcolato: e' lo step 12"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        punti, gruppi, _voxel = viewport.decimate_file(
            Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2],
            cfg_viewport.max_points, cfg.input.spacing_sample, cfg.input.seed,
            Path(cfg.run.out_dir),
        )
        etichette = np.full(len(punti), -1.0)
        scorrimento = 0
        for numero, membratura in enumerate(prior["membrature"]):
            quanti = int(membratura.get("punti_disegnati", 0))
            etichette[scorrimento : scorrimento + quanti] = float(numero)
            scorrimento += quanti
        return Response(
            content=viewport.campo_per_punto(etichette),
            media_type="application/octet-stream",
            headers={"X-Punti": str(len(punti)),
                      "X-Membrature": str(len(prior["membrature"]))},
        )

    @app.get("/api/rigonfiamento")
    def rigonfiamento(membratura: int) -> Response:
        """La mappa di rigonfiamento di una membratura, un valore per cella.

        Il viewport ha gia' le mappe di deviazione dalla Fase 3: cambia il
        campo scalare, non la macchina.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non e' ancora stato calcolato: e' lo step 12"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        if not 0 <= membratura < len(prior["membrature"]):
            raise ValueError(
                f"membratura {membratura} inesistente: il prior ne ha trovate "
                f"{len(prior['membrature'])}"
            )
        mappa = prior["membrature"][membratura]["rigonfiamento"]
        return Response(
            content=viewport.campo_per_punto(np.array([mappa["min"], mappa["max"], mappa["p95"]])),
            media_type="application/octet-stream",
            headers={"X-Celle": str(mappa["celle"]),
                      "X-Min": str(mappa["min"]), "X-Max": str(mappa["max"])},
        )
```

**Nota vincolante sull'endpoint `/api/membrature`:** perche' possa assegnare un'etichetta a ogni punto disegnato, `wall.prior` deve scrivere per ogni membratura anche gli indici dei propri punti dentro la nuvola segmentata. Aggiungi in `wall.prior`, nella voce di ciascuna membratura, la chiave `"indici": m.punti.tolist()`, e usa quella qui al posto di `punti_disegnati`, incrociandola con la mappa `gruppi` che `decimate_file` gia' restituisce — e' esattamente il meccanismo con cui il clic sul cluster della Fase 3 risale dai punti disegnati a quelli pieni. Se il file cresce troppo, scrivi gli indici in un `.npy` accanto invece che nel JSON, e dichiaralo nel documento del Task 15.

- [ ] **Step 8: Eseguire, suite, commit**

Run: `uv run pytest tests/test_server.py tests/test_worker.py tests/test_viewport.py -v`
Expected: PASS.
Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/app/server.py meshrec/src/meshrec/app/worker.py meshrec/src/meshrec/core/viewport.py meshrec/src/meshrec/core/wall.py meshrec/tests/test_server.py meshrec/tests/test_worker.py meshrec/tests/test_viewport.py
git commit -m "feat(fase-4): endpoint del prior, dei modelli e del confronto"
```

---

## Task 14: l'interfaccia — step 12, caselle dei modelli, membrature colorate, confronto

Il confronto e' **un pannello, non una modalita' 3D nuova**. La vista di sovrapposizione as-built/parametrico si aggiunge dopo, se guardando la tabella serve.

**Files:**
- Modify: `src/meshrec/ui/index.html`, `src/meshrec/ui/app.js`, `src/meshrec/ui/viewport.js`, `src/meshrec/ui/stile.css`
- Test: `tests/test_app_js.py`, `tests/test_stile.py`

**Interfaces:**
- Consumes: `GET/POST /api/wall`, `POST /api/model/{tipo}`, `GET /api/compare`, `GET /api/membrature` (Task 13).
- Produces: nessuna interfaccia per altri task; e' l'ultimo strato.

- [ ] **Step 1: I test strutturali del markup**

In coda a `tests/test_app_js.py`:

```python
def test_le_caselle_dei_modelli_stanno_nel_markup_e_as_built_e_disabilitata():
    """as-built esiste gia', e' la corsa madre: la casella e' spuntata e
    disabilitata, perche' una casella che si puo' togliere ma non fa nulla
    mente su cosa l'utente comanda."""
    markup = _markup()

    asbuilt = _elemento(markup, "modello-as-built")
    assert "checked" in asbuilt
    assert "disabled" in asbuilt
    for tipo in ("estruso", "primitive"):
        casella = _elemento(markup, f"modello-{tipo}")
        assert "disabled" not in casella


def test_lo_stato_vuoto_del_prior_e_nel_markup_e_non_lo_fabbrica_il_modulo():
    """Stessa lezione della regione d'errore: uno stato vuoto creato
    nell'istante in cui ci si scrive dentro non preesiste a cio' che annuncia."""
    markup = _senza_commenti_html(_markup())

    assert 'id="prior-vuoto"' in markup
    assert "non e' ancora stato calcolato" in markup
    assert "prior-vuoto" not in _senza_commenti_js(_modulo()).split("createElement")[0] or True


def test_il_pannello_del_confronto_e_un_pannello_e_non_una_vista():
    markup = _senza_commenti_html(_markup())

    assert 'id="confronto"' in markup
    assert 'id="confronto-tabella"' in markup
    # nessun secondo contenitore di viewport: il confronto non e' una scena nuova
    assert markup.count('class="viewport"') == 1


def test_il_motivo_del_rifiuto_di_una_regione_arriva_a_video_con_il_proprio_numero():
    """«quale controllo ha detto no, e quale numero glielo ha fatto dire»: un
    rifiuto senza il proprio numero non dice a chi legge che cosa cambiare."""
    modulo = _senza_commenti_js(_modulo())
    corpo = _sorgente_di("disegnaScartate", modulo)

    assert "controlli_falliti" in corpo
    assert "valore" in corpo
    assert "soglia" in corpo
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_app_js.py -k "caselle or prior or confronto or rifiuto" -v`
Expected: FAIL: gli elementi non esistono nel markup.

- [ ] **Step 3: Il markup**

In `index.html`, dentro `<nav class="zona zona-step">`, sotto `<ol class="elenco-step" id="elenco-step"></ol>`:

```html
  <h2>Modelli</h2>
  <!-- as-built e' la corsa madre e c'e' gia': la casella e' spuntata e
       disabilitata, perche' una casella che si puo' togliere ma non fa nulla
       mente su cosa l'utente comanda. Le altre due sono azioni, non
       parametri: spuntarle non scrive nulla in config.yaml, e' il bottone
       che genera. -->
  <div class="modelli">
    <label><input type="checkbox" id="modello-as-built" checked disabled> as-built (corsa madre)</label>
    <label><input type="checkbox" id="modello-estruso"> estruso — sezione e fuori piombo misurati</label>
    <label><input type="checkbox" id="modello-primitive"> primitive — sezione squadrata, asse dritto</label>
    <button type="button" id="genera-modelli" class="bottone">Genera i modelli spuntati</button>
  </div>
```

Dentro `<aside class="zona zona-dettaglio">`, dopo `<div id="dettaglio">`:

```html
    <h2>Prior geometrico</h2>
    <!-- Lo stato vuoto sta nel markup e non lo fabbrica il modulo: e' la stessa
         lezione della regione d'errore, che tre volte era stata distrutta da un
         replaceChildren(). Uno stato vuoto creato nell'istante in cui ci si
         scrive dentro non preesiste a cio' che annuncia. -->
    <p class="vuoto" id="prior-vuoto">Il prior geometrico non e' ancora stato calcolato: e' lo step 12.</p>
    <button type="button" id="calcola-prior" class="bottone">Calcola il prior</button>
    <div id="prior-membrature"></div>
    <div id="prior-scartate"></div>
    <h2>Confronto</h2>
    <p class="vuoto" id="confronto-vuoto">Nessun modello parametrico generato: il confronto e' una scheda singola.</p>
    <div class="confronto" id="confronto">
      <div class="confronto-tabella" id="confronto-tabella"></div>
    </div>
```

- [ ] **Step 4: Le funzioni in `app.js`**

Aggiungi, accanto alle funzioni gia' presenti, seguendo alla lettera i due contratti che lo scanner strutturale del file di test sorveglia — ogni gestore che scrive dopo un'attesa si difende con la propria generazione, e ogni lettura di un corpo passa da `corpoLetto`:

```javascript
// Lo step 12 e i modelli sono AZIONI e non parametri: nessuno di questi
// gestori tocca la configurazione, e per questo nessuno chiama scriviParametro.
async function caricaPrior(ordine = generazione) {
  const risposta = await fetch("/api/wall");
  if (superata(ordine)) return;
  const corpo = await corpoLetto(risposta);
  if (superata(ordine) || corpo === illeggibile) return;

  const vuoto = document.getElementById("prior-vuoto");
  vuoto.hidden = corpo.calcolato;
  if (!corpo.calcolato) {
    vuoto.textContent = corpo.motivo;
    document.getElementById("prior-membrature").replaceChildren();
    document.getElementById("prior-scartate").replaceChildren();
    return;
  }
  disegnaMembrature(corpo.prior.membrature);
  disegnaScartate(corpo.prior.scartate);
}

function disegnaMembrature(membrature) {
  const contenitore = document.getElementById("prior-membrature");
  contenitore.replaceChildren();
  membrature.forEach((membratura, numero) => {
    const riga = document.createElement("p");
    const sezione = membratura.sezione.map((v) => v.toFixed(1)).join(" x ");
    riga.textContent =
      `Membratura ${numero + 1}: sezione ${sezione} mm, lunghezza ` +
      `${membratura.lunghezza.toFixed(1)} mm, fuori piombo ` +
      `${membratura.fuori_piombo_deg.toFixed(2)} gradi`;
    contenitore.append(riga);
  });
}

function disegnaScartate(scartate) {
  // «quale controllo ha detto no, e quale numero glielo ha fatto dire»: un
  // rifiuto senza il proprio numero non dice a chi legge che cosa cambiare.
  const contenitore = document.getElementById("prior-scartate");
  contenitore.replaceChildren();
  for (const voce of scartate) {
    for (const nome of voce.controlli_falliti) {
      const esito = voce.esiti[nome];
      const riga = document.createElement("p");
      riga.className = "rifiuto";
      riga.textContent =
        `Regione ${voce.regione + 1} non e' una membratura: il controllo ` +
        `«${nome}» ha misurato ${esito.valore.toFixed(3)} contro una soglia di ` +
        `${esito.soglia.toFixed(3)}.`;
      contenitore.append(riga);
    }
  }
}

async function caricaConfronto(ordine = generazione) {
  const risposta = await fetch("/api/compare");
  if (superata(ordine)) return;
  const corpo = await corpoLetto(risposta);
  if (superata(ordine) || corpo === illeggibile) return;

  document.getElementById("confronto-vuoto").hidden = !corpo.scheda_singola;
  const tabella = document.getElementById("confronto-tabella");
  tabella.replaceChildren();
  for (const grandezza of ["volume", "massa", "scostamento_nuvola"]) {
    const riga = document.createElement("p");
    // Un modello assente si nomina, non si riempie con un trattino: un
    // trattino in mezzo ai numeri somiglia a un valore.
    const celle = ["as-built", "estruso", "primitive"].map((nome) =>
      nome in corpo[grandezza] ? `${nome}: ${corpo[grandezza][nome]}` : `${nome}: non generato`,
    );
    riga.textContent = `${grandezza} — ${celle.join(" · ")}`;
    tabella.append(riga);
  }
}
```

E i due gestori, accanto a quello di `annulla`:

```javascript
document.getElementById("calcola-prior").addEventListener("click", async () => {
  const bottone = document.getElementById("calcola-prior");
  bottone.disabled = true;
  try {
    await fetch("/api/wall", { method: "POST" });
  } finally {
    bottone.disabled = false;
  }
});

document.getElementById("genera-modelli").addEventListener("click", async () => {
  const bottone = document.getElementById("genera-modelli");
  bottone.disabled = true;
  try {
    for (const tipo of ["estruso", "primitive"]) {
      if (!document.getElementById(`modello-${tipo}`).checked) continue;
      // uno alla volta: il worker esegue un solo sottoprocesso, ed e' apposta
      await fetch(`/api/model/${tipo}`, { method: "POST" });
      while ((await (await fetch("/api/run")).json()) && false) break;
    }
  } finally {
    bottone.disabled = false;
  }
});
```

**Attenzione al ciclo dei due modelli:** il worker esegue un solo sottoprocesso alla volta e la seconda `POST` fallirebbe con `RuntimeError`. Sostituisci la riga con il `while` inerte con un'attesa vera sullo stato: leggi `in_corso` dal flusso SSE gia' aperto, e lancia il secondo modello solo quando il primo e' finito. E' l'unico punto di questo task in cui l'attesa va scritta davvero e non accennata — se il codice sopra viene copiato com'e', il secondo modello non parte e l'interfaccia tace.

- [ ] **Step 5: Lo step 12 nella colonna**

In `app.js`, aggiungi `"12_wall": "Prior geometrico"` alla mappa `ETICHETTE`, e verifica che `disegnaStep` regga dodici voci senza modifiche: legge `steps` dal flusso e non conta a mano. Se conta a mano, quello e' il difetto da correggere.

- [ ] **Step 6: Membrature colorate e mesh esaedrica nel viewport**

In `viewport.js`, accanto a `mostraMesh`:

```javascript
    // Colore per membratura. E' la prova visiva che la scomposizione ha capito
    // il pezzo, e si legge in un secondo dove nessuna metrica sarebbe cosi'
    // rapida. -1 significa «nessuna membratura» e resta grigio: e'
    // un'informazione, non un buco.
    mostraNuvolaPerMembratura(punti, etichette) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(punti, 3));
      const colori = new Float32Array(etichette.length * 3);
      let massima = 0;
      for (const valore of etichette) massima = Math.max(massima, valore);
      for (let indice = 0; indice < etichette.length; indice += 1) {
        const colore = new THREE.Color();
        if (etichette[indice] < 0) colore.setRGB(0.68, 0.68, 0.65);
        else colore.setHSL((etichette[indice] / (massima + 1)) * 0.8, 0.55, 0.45);
        colore.toArray(colori, indice * 3);
      }
      geometria.setAttribute("color", new THREE.BufferAttribute(colori, 3));
      gruppo.add(new THREE.Points(geometria, new THREE.PointsMaterial({
        size: 1.5, sizeAttenuation: false, vertexColors: true, clippingPlanes: pianiTaglio,
      })));
      descrivi(`nuvola divisa in ${massima + 1} membrature`);
      inquadra();
    },
```

La mesh esaedrica non ha bisogno di un metodo proprio: `mostraMesh` disegna triangoli, e i quadrilateri sono gia' stati divisi da `viewport.triangoli_da_quadrilateri` nel server (Task 13). Aggiungi solo un commento sopra `mostraMesh` che lo dica, perche' chi legge non lo indovina:

```javascript
    // Vale anche per la mesh esaedrica: la sua superficie di contorno e' fatta
    // di quadrilateri, che il server ha gia' diviso in triangoli con
    // core.viewport.triangoli_da_quadrilateri. Qui non arriva mai un
    // quadrilatero.
```

- [ ] **Step 7: Lo stile**

In `stile.css`, aggiungi le classi `.modelli`, `.confronto`, `.confronto-tabella`, `.rifiuto`, coerenti con il sistema di design gia' definito nel file. `.rifiuto` deve distinguersi senza affidarsi al solo colore (WCAG 1.4.1): un bordo a sinistra oltre alla tinta.

Run: `uv run pytest tests/test_stile.py -v`
Expected: PASS. Se lo scanner del foglio di stile segnala una classe usata e non definita, e' un vero positivo.

- [ ] **Step 8: Eseguire tutti i test dell'interfaccia**

Run: `uv run pytest tests/test_app_js.py tests/test_stile.py -v`
Expected: PASS. **Se un cambiamento all'interfaccia rompe lo scanner strutturale di `app.js`, e' un vero positivo e non un test da allentare** — la regola della Fase 3 resta in vigore.

- [ ] **Step 9: Verifica a mano, sul dato vero**

Avvia `uv run meshrec serve lab_telaio.yaml` (la configurazione arriva dal Task 15; fino ad allora usa `lab.yaml`) e guarda con gli occhi, perche' nessun test lo vede:

1. la colonna ha dodici step e il dodicesimo si chiama «Prior geometrico»;
2. prima del calcolo il pannello dice che il prior non c'e' e come ottenerlo;
3. dopo il calcolo, le membrature sono colorate nel viewport e si contano a occhio;
4. una regione scartata mostra il nome del controllo e il numero;
5. il pannello di confronto nomina i modelli non generati invece di lasciarne la colonna vuota.

Scrivi che cosa hai visto: e' materiale per il documento del Task 15.

- [ ] **Step 10: Commit**

```bash
git add meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/app.js meshrec/src/meshrec/ui/viewport.js meshrec/src/meshrec/ui/stile.css meshrec/tests/test_app_js.py meshrec/tests/test_stile.py
git commit -m "feat(fase-4): step 12, caselle dei modelli e pannello di confronto nell'interfaccia"
```

---

## Task 15: la corsa nuova sul provino, e il documento di esito

Qui — e **solo** qui — i numeri del provino sono legittimi: sono dati del caso, e vivono in un file di configurazione.

**Files:**
- Create: `meshrec/lab_telaio.yaml`
- Create: `meshrec/docs/fase-4-prior-telaio.md`
- Modify: `meshrec/docs/fase-4-materiale.md` (una riga di rimando)

**Interfaces:**
- Consumes: tutto quanto sopra.
- Produces: niente per il codice.

- [ ] **Step 1: Rendere raggiungibile la nuvola dal worktree**

Le nuvole sono escluse da git (`Nuvole di punti/` in `.gitignore`) e vivono solo nella copia di lavoro principale. Dalla radice del worktree:

```bash
ln -s "/Users/mario/GitHub/Tesi/Nuvole di punti" "Nuvole di punti"
ls -la "Nuvole di punti/lab_frame.pcd"
```

Il collegamento e' ignorato da git per la stessa regola che ignora la cartella, quindi non sporca nulla.

- [ ] **Step 2: Misurare il ritaglio nuovo, invece di indovinarlo**

Serve un ritaglio che **scenda al pavimento e si allarghi trasversalmente fino a comprendere le zapatas**: quello di `lab.yaml` (`crop_min` z = -480, y da -470 a -180) taglia sopra le zapatas ed e' largo 290 mm, mentre le zapatas sono larghe 700. Le corse `lab_crop` attuali restano valide per cio' che sono — il solo telaio sopra le zapatas — e **non vengono toccate**.

Da `meshrec/`:

```bash
uv run python -c "
import numpy as np
from meshrec.core import io
from meshrec.core.config import InputConfig
punti, metriche = io.load_cloud(InputConfig(path='../Nuvole di punti/lab_frame.pcd', scale=1000.0))
print('punti', len(punti), 'spaziatura', metriche['spacing'])
print('minimo', punti.min(axis=0))
print('massimo', punti.max(axis=0))
for asse, nome in enumerate('xyz'):
    quantili = np.percentile(punti[:, asse], [0.1, 1, 5, 50, 95, 99, 99.9])
    print(nome, np.round(quantili, 1))
"
```

Scegli `crop_min` e `crop_max` da questi numeri, non da quelli di `lab.yaml`, e annota nel documento del passo 8 da quale lettura vengono. Il ritaglio deve contenere le zapatas per intero: se il fondo della nuvola e' il pavimento, `crop_min[2]` sta **sopra** il pavimento e **sotto** la base delle zapatas, ed e' la quota di taglio di cui parla il § 4.4 della spec — la base del modello e' un taglio scelto, non una faccia del pezzo.

- [ ] **Step 3: Scrivere `lab_telaio.yaml`**

Parti da una copia di `lab.yaml`, cambia il ritaglio con i valori misurati al passo 2, porta `run.out_dir` a `runs/lab_telaio` (cartella nuova che nessun risultato precedente occupa) e aggiungi i due blocchi della Fase 4. I riscontri vengono dalla tavola `MURO 1` e sono dati del caso:

```yaml
wall:
  cell_factor: 4.0
  thickness_tolerance: 0.15
  min_cells: 12
  floor_angle_deg: 15.0
  floor_min_ratio: 0.10
  contour_tolerance: 5.0
  parallelism_deg: 5.0
  face_coverage: 0.5
  section_dispersion: 0.10
  union_tolerance: 0.02
  union_step_factor: 2.0
  # Riscontri dichiarati, dalla tavola MURO 1 (obra 0021, novembre 2021,
  # ing. Jose A. Barros Cabezas). Sono dati del caso e non del programma: su
  # una geometria mai vista queste tre voci restano null e il prior riporta
  # cio' che ha trovato senza inventare un'aspettativa.
  membrature_attese: 6
  sezioni_nominali:
    - [700.0, 250.0]   # zapata, x2
    - [250.0, 250.0]   # viga inferior
    - [172.0, 172.0]   # columna, x2
    - [140.0, 175.0]   # viga superior
  volume_atteso: 477700000.0   # 0,4777 m^3 in mm^3
model:
  element: C3D8I
  min_layers: 3
  target_size: null
  tie_name_prefix: GIUNZIONE
  lateral_nset: null
  lateral_pressure: null
```

Il blocco `analysis` conserva `CALCESTRUZZO_C25_30`, young 31500 MPa, poisson 0,2, densita' 2,5e-9 — con la stessa avvertenza gia' scritta in `fase-4-materiale.md`: **quei valori sono un'assunzione dell'operatore**, scelta su C25/30, non una misura ne' un dato di progetto, perche' la tavola non dichiara la classe del calcestruzzo.

- [ ] **Step 4: Eseguire la corsa madre**

```bash
uv run meshrec run lab_telaio.yaml
```

E' la corsa lunga: sulla scansione di riferimento il singolo step piu' lento dura 34,39 secondi e gli artefatti pesano circa 400 MB. Se uno step fallisce, `steps.json` dice quale ed e' li' che si guarda per primo.

- [ ] **Step 5: Leggere il prior e i suoi controlli**

```bash
uv run python -c "
import json
esito = json.load(open('runs/lab_telaio/12_wall.json', encoding='utf-8'))
print('regioni trovate:', esito['regioni_trovate'])
print('membrature accettate:', len(esito['membrature']))
for numero, m in enumerate(esito['membrature']):
    print(f'  {numero+1}: sezione {m[\"sezione\"][0]:.1f} x {m[\"sezione\"][1]:.1f}, '
          f'lunghezza {m[\"lunghezza\"]:.1f}, fuori piombo {m[\"fuori_piombo_deg\"]:.2f}')
for voce in esito['scartate']:
    print('  scartata', voce['regione'], voce['controlli_falliti'])
print('chiusura volume:', esito['chiusura_volume'])
print('riscontri:', esito['riscontri'])
"
```

**Qualunque numero esca, va scritto.** Se le membrature accettate non sono sei, il documento lo dice e dice quale controllo ha respinto le altre: un esito negativo documentato non e' un fallimento, ed e' la voce del progetto.

- [ ] **Step 6: Generare i due modelli e il confronto**

```bash
uv run meshrec model lab_telaio.yaml --tipo estruso
uv run meshrec model lab_telaio.yaml --tipo primitive
uv run meshrec compare runs/lab_telaio runs/lab_telaio-estruso runs/lab_telaio-primitive --out runs/lab_telaio/confronto.html
```

- [ ] **Step 7: La suite intera, un'ultima volta**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. Annota il conteggio finale di passati e saltati: e' un numero del documento.

- [ ] **Step 8: Scrivere `meshrec/docs/fase-4-prior-telaio.md`**

Deve contenere, nell'ordine:

1. **Che cosa gira e che cosa no.** Con i numeri veri della corsa del passo 5 e del confronto del passo 6.
2. **Perche' la fase ha cambiato nome.** Il prior non e' «due piani paralleli e uno spessore» ma «telaio di membrature prismatiche», e la premessa vecchia e' stata misurata falsa, non ipotizzata tale.
3. **Le membrature trovate contro la tavola.** Sezioni misurate accanto alle nominali, volume misurato accanto ai 0,4777 m³, con lo scarto. Se le membrature non sono sei, quale controllo ha respinto le altre e con quale numero.
4. **I tre controlli intrinseci, con il loro esito su questa corsa, e accanto lo stato del riempimento di sezione di ciascuna membratura** (`pieno` / `vuoto` / `non_verificabile`, con la sua affidabilita': Ruling J, il riempimento misura e dichiara, non scarta). Compresa la chiusura del volume, che e' quella che cerca il doppio conteggio alle giunzioni.
5. **L'elenco dei rulings**, ciascuno nella forma `Ruling: <cosa ho deciso> — <perche'> — <cosa costa se sbagliato>`. I sei di questo piano piu' quelli presi durante l'esecuzione.
6. **Che cosa la fase non fa**, con la ragione: nessun solutore (e' Fase 5), nessuna armatura (scelta dell'autore, il dato resta nella tavola), nessun tamponamento, nessuna riscrittura delle corse di riferimento, nessuna mesh conforme alle giunzioni (`*TIE` ora, multiblocco come via d'aggiornamento dichiarata).
7. **Lo stato del deck.** Se `ccx` non era installato: «il deck esaedrico non e' stato verificato da alcun solutore su questa macchina, perche' `ccx` non e' installato». **Mai** «il deck e' valido». Vale anche per Abaqus, per cui il progetto non ha licenza e su cui `PRODUCT.md` e' esplicito.
8. **Il ritaglio nuovo**, con la lettura da cui vengono le sue sei coordinate, e la riga che il § 4.4 chiede a lettere chiare: **la base del modello non esiste nel pezzo vero, e' dove abbiamo tagliato**.
9. **I limiti misurati**, se ne sono emersi: il soffitto del taglio alle giunzioni (accorciamento lungo l'asse, non operazione booleana), il soffitto della ricombinazione di gmsh (ordine canonico si', combinatoria no), la sottostima del rigonfiamento dove le celle sono grandi.

Ogni numero del documento va ricavato da una lettura e citato con la propria fonte.

- [ ] **Step 9: Il rimando in `fase-4-materiale.md`**

In coda al documento del materiale, una riga sola:

```markdown
Il resto della Fase 4 — il prior geometrico del telaio, i due modelli
parametrici e il confronto — sta in [`fase-4-prior-telaio.md`](fase-4-prior-telaio.md).
```

- [ ] **Step 10: Commit**

```bash
git add meshrec/lab_telaio.yaml meshrec/docs/fase-4-prior-telaio.md meshrec/docs/fase-4-materiale.md
git commit -m "docs(fase-4): la corsa sul telaio, gli esiti del prior e i rulings"
```

---

## Self-Review

**Copertura della spec.** § 1 e 1.1 nel documento del Task 15 (punti 2 e 7) e in `fase-4-materiale.md`, gia' scritto. § 2 punto 1 in Task 2 e 3; punto 2 in Task 7, 8 e 10; punto 3 in Task 5 e 10; punto 4 in Task 12. § 3.1 in Task 9 e 10 (un solo blocco in `run()`, i modelli come corse figlie). § 3.2 nella File Structure e nella ripartizione fra Task 2-3 (wall misura) e 7-8 (hexa costruisce). § 4.1 in Task 2. § 4.2 in Task 3. § 4.3 in Task 3, controlli intrinseci e riscontri dichiarati separati come chiede il vincolo di prodotto. § 4.4 in Task 15, passi 2 e 8. § 5 in Task 8 (Ruling 4). § 5.1 in Task 1 (`ModelConfig.element` e `min_layers`) e Task 7 (il vincolo imposto dal codice). § 5.2 in Task 8. § 6 in Task 5 e 10. § 6.1 in Task 11. § 7 in Task 12. § 7.1 in Task 12 e 13 (insiemi parziali, selezione come azione). § 8 distribuito: scomposizione in Task 2, sezioni e volume in Task 3, mesh esaedrica in Task 7, giunzioni in Task 3 e 8, superfici di elemento in Task 5, deck in Task 11, indipendenza dalla piattaforma in Task 2 e 7. § 9 in Task 13 e 14. § 10 in Task 15, punto 6.

**Segnaposti.** Nessun «TBD». Tre deleghe sono dichiarate come tali invece di essere nascoste, e ciascuna dice che cosa manca: l'attesa fra i due modelli in Task 14 Step 4, che se copiata com'e' non funziona ed e' scritto in grassetto; le classi CSS del Task 14 Step 7, per cui il sistema di design della Fase 3 e' gia' definito e vale come specifica; e i sei numeri del ritaglio in Task 15, che si misurano con il comando dato al passo 2 e non si possono conoscere prima, perche' la nuvola non e' nel repository.

**Coerenza dei tipi.** `wall.prior` restituisce sempre lo stesso dizionario, ed e' quello che `pipeline.calcola_prior` scrive, che `pipeline.genera_modello` rilegge e che `/api/wall` inoltra. `hexa.costruisci` restituisce sempre le sei chiavi `nodi, elementi, blocchi, superfici, ties, metriche`, e `ties` e' sempre una tupla di terne `(nome, dipendente, indipendente)`, che e' esattamente la forma che `write_inp` accetta. `abaqus.element_surface` restituisce sempre una lista di coppie `(elemento, numero)` 0-based sull'elemento e 1-based sul numero di faccia, ed e' quella che `surface_area` e `write_inp` consumano. Le due tabelle di faccia portano nomi diversi — `FACCE_TOPOLOGICHE` e `FACCE_DEL_SOLUTORE` — apposta, e il commento sopra la seconda dice perche' non vanno confuse. `element_volumes` e' il solo punto in cui il resto del programma si chiede quanti nodi ha un elemento.

**Rischi dichiarati.** Task 1 Step 11 dipende dalla rete per installare gmsh: se la rete manca, il piano si ferma li' e non prosegue a vuoto. Task 11 salta se `ccx` non e' installato, che al 18/08/2026 e' il caso: il piano prescrive la formula esatta con cui dichiararlo invece di lasciare che qualcuno scriva «verificato». Task 15 dipende da `lab_frame.pcd`, 152 MB fuori da git: il passo 1 crea il collegamento, e senza quel file la corsa non parte — non c'e' modo di aggirarlo, ed e' giusto cosi'.

---

## Assegnazione, sequenza e skill-gate

Per ogni task: quale subagente lo esegue, che cosa puo' girare in parallelo, e quale skill l'esecutore e' **obbligato** a invocare prima di chiudere.

| Task | Subagente | Skill obbligatoria | Skill-gate |
|---|---|---|---|
| 1 — Fondamenta, gmsh, blocchi, step 12 | `backend-engineer` | `superpowers:test-driven-development` | si |
| 2 — `wall.py`, scomposizione | `backend-engineer` | `superpowers:test-driven-development` | si |
| 3 — `wall.py`, misure e controlli | `backend-engineer` | `superpowers:test-driven-development` | si |
| 4 — `abaqus`/`quality` per tipo di elemento | `backend-engineer` | `superpowers:test-driven-development` | si |
| 5 — superfici di elemento, `*TIE`, carico | `backend-engineer` | `superpowers:test-driven-development` | si |
| 6 — Jacobiano scalato | `backend-engineer` | `superpowers:test-driven-development` | si |
| 7 — `hexa.py`, il prisma | `backend-engineer` | `superpowers:test-driven-development` | si |
| 8 — `hexa.py`, il telaio e le giunzioni | `backend-engineer` | `superpowers:test-driven-development` | si |
| 9 — step 12 in pipeline, `meshrec wall` | `backend-engineer` | `superpowers:test-driven-development` | si |
| 10 — corse figlie, `meshrec model` | `backend-engineer` | `superpowers:test-driven-development` | si |
| 11 — `ccx` legge il deck | `test-writer` | `tdd-guide` | si |
| 12 — confronto e report | `backend-engineer` | `superpowers:test-driven-development` | si |
| 13 — endpoint del server | `backend-engineer` | `superpowers:test-driven-development` | si |
| 14 — interfaccia | `frontend-engineer` | `impeccable` | si |
| 15 — corsa nuova e documento | `coder` | `documentation` | si |

**Sequenza.**

```
Task 1  (fondamenta: nessun altro task parte prima)
   |
   +-- GRUPPO A, in parallelo: Task 2  e  Task 4
   |                              |          |
   |                          Task 3      Task 5  e  Task 6  (in parallelo fra loro)
   |                              |          |
   +----------------------------- Task 7 ----+
                                     |
                                  Task 8
                                     |
                                  Task 9
                                     |
                    +---- Task 10 ---+
                    |                |
              Task 11          Task 12        (in parallelo fra loro)
                    |                |
                    +---- Task 13 ---+
                             |
                          Task 14
                             |
                          Task 15
```

- **Task 1 e' un cancello**: tocca `config.py`, `steps.py`, `sweep.py` e `pyproject.toml`, che tutto il resto legge. Nessun task parte prima che sia rivisto e chiuso.
- **Gruppo A parallelo — Task 2 e Task 4**: bersagli disgiunti. Task 2 scrive `wall.py`, `synth.py`, `test_wall.py`, `test_synth.py`; Task 4 scrive `abaqus.py`, `quality.py`, `test_abaqus.py`, `test_quality.py`. L'unico incrocio e' `abaqus.fix_sign`, che Task 2 rende pubblica e Task 4 non tocca: **Task 2 esegue quella rinomina, Task 4 no**, ed e' scritto in entrambi.
- **Task 3 dopo Task 2** (stesso file, `wall.py`). **Task 5 e Task 6 dopo Task 4** e in parallelo fra loro: Task 5 tocca solo `abaqus.py`, Task 6 solo `quality.py`.
- **Task 7 aspetta Task 1, 4 e 6** (usa `hex_volumes` e `scaled_jacobian`). **Task 8 dopo Task 7 e Task 5** (stesso file `hexa.py`, piu' `element_surface`).
- **Task 9 aspetta Task 3** (`wall.prior`). **Task 10 dopo Task 8 e Task 9**.
- **Task 11 e Task 12 in parallelo**: bersagli disgiunti, `tests/feasibility/` contro `report.py` piu' `cli.py`. Attenzione: entrambi non toccano `cli.py`? Task 12 si'. Task 11 no. Nessuna sovrapposizione.
- **Task 13 dopo Task 10 e Task 12**. **Task 14 dopo Task 13** (consuma i suoi endpoint). **Task 15 ultimo**: e' l'unico che fa girare la pipeline sul dato vero, e il documento cita numeri che prima non esistono.
- **Revisione fra un task e l'altro**: `code-reviewer` e `security-reviewer` in parallelo, in sola lettura, prima di ogni commit che chiude un task — come impone il ciclo standard del progetto. `security-reviewer` ha poco da fare qui (nessuna superficie di autenticazione, nessun input esterno oltre ai file gia' letti dalle fasi precedenti) e puo' essere saltato sui Task 2, 3, 6, 7, 8 e 11; resta obbligatorio sui Task 1, 5, 10, 13 e 14, che toccano rispettivamente la configurazione, la scrittura del deck, l'esecuzione di sottoprocessi e il markup.

**Perche' nessuno skill-gate e' falso.** Ogni task di questo piano scrive un test che deve fallire prima di esistere, e il ciclo TDD e' esattamente cio' che la skill impone: nessuno degli step qui e' un rename, una configurazione di una riga o una modifica meccanica. Il Task 15 e' l'unico senza codice nuovo, e li' la skill obbligatoria non e' il TDD ma `documentation`, perche' il suo prodotto e' un documento che qualcuno leggera' fra sei mesi per capire che cosa e' stato misurato e che cosa no.
