# Fase 6 — Carichi posizionati: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un operatore dichiara un carico su una mesh as-built priva di topologia indicando una regola geometrica, il programma la risolve in nodi, scrive le card nel deck e riporta con quali numeri l'ha fatto.

**Architecture:** un blocco `selettori:` alla radice della configurazione tiene le regole nominate; `core/selezione.py` (nuovo) le risolve in indici di nodo sulla mesh già allineata; `core/abaqus.py` pesa la risultante per area tributaria e scrive un passo statico per carico. Il resoconto entra in `metrics["11_export"]`, dove già stanno `node_sets` e `casi_di_carico`.

**Tech Stack:** Python 3.12 (`requires-python = ">=3.12,<3.13"`), pydantic ≥ 2.7, numpy ≥ 2.0, pyyaml ≥ 6.0, pytest. Solutore CalculiX `ccx` 2.22 su arm64.

**Spec:** [`docs/superpowers/specs/2026-08-22-meshrec-fase-6-carichi-posizionati-design.md`](../specs/2026-08-22-meshrec-fase-6-carichi-posizionati-design.md)

## Global Constraints

- **Comandi.** Tutti da `meshrec/`. La suite si lancia con `uv run pytest tests -q --ignore=tests/feasibility`. In una sessione isolata in un worktree: percorsi assoluti, **un comando per chiamata**, `git -C <percorso assoluto>` invece di `cd` prima di git.
- **Baseline da non far scendere.** Sale a ogni task che atterra, e va **rimisurata**, non ricordata. Storia finora, tutte con `uv run pytest tests -q --ignore=tests/feasibility` da `meshrec/` e uscita 0:
  | dopo | baseline | note |
  |---|---|---|
  | `a4fefc7` (prima del Task 1) | **726** in 103,89 s | la spec e la mappa citano 723: era il numero su `main`, prima dei tre test di `911f15f` |
  | Task 1 (`8f1161d`) | **746** | +20 |
  | Task 2 (`c8911d5`) | **748** in 232,45 s | +2 |
  Più 11 passed / 1 skipped con `-m feasibility`.
- **Un fallimento sotto carico non è automaticamente una regressione, ma non è nemmeno automaticamente un flake.** `tests/test_worker.py::test_il_worker_esegue_anche_un_comando_che_non_e_uno_step` aspetta un sottoprocesso con un poll fino a 10 s e sotto carico può cadere con `assert None is not None`. È successo una volta durante il Task 2 ed era davvero un flake — **rimisurato**, non creduto. Se ricapita: rilancia la suite a macchina scarica prima di chiamarlo flake, e riporta il numero della seconda corsa.
- **Sola lettura:** `runs/muro/`, `runs/lab_crop/`, `experiments/muro/`, `experiments/lab_crop/`. Mai `git add -A`: ogni commit elenca i file.
- **Niente numeri del provino di laboratorio in `src/`.** I valori di `lab_frame` stanno nelle configurazioni e nei documenti, non nel codice.
- **Ogni test nuovo dichiara nel docstring la mutazione che lo uccide**, e lo step successivo la applica davvero per vedere il test fallire nel modo giusto. Un test che passa anche mutato non è un test.
- **Il server riscrive `config.yaml`** (`save_config`, `core/config.py:785-789`, `safe_dump` del modello alla riga 789): dopo averlo avviato, `git diff` dello YAML prima di misurare qualunque cosa.
- **I numeri di riga di questo piano scadono man mano che i task atterrano.** Il Task 1 ha aggiunto ~76 righe a `core/config.py`, e i successivi ne aggiungeranno altre. Ogni `file:riga` citato qui va **riaperto e confermato** prima di agirci: se il conteggio è cambiato, vale quello che leggi tu, non quello che c'è scritto qui.
- **Unità:** mm, N, MPa, t, s. Forze in N, momenti in N·mm, lunghezze in mm.
- **Nomi ammessi** per set, selettori e carichi: `^[A-Za-z0-9_.-]+$`. Finiscono interpolati in un deck ascii.
- **Commit:** Conventional Commits, corpo che dice il perché quando non è ovvio.

---

## File Structure

| file | responsabilità | stato |
|---|---|---|
| `src/meshrec/core/config.py` | schema e validazione **senza mesh**: i quattro selettori, `CaricoPosizionato`, `Momento`, i campi nuovi su `PipelineConfig` e `CarichiConfig`, il loader che rifiuta le chiavi omonime | modificato |
| `src/meshrec/core/selezione.py` | risoluzione geometrica **con la mesh**: da regola a indici di nodo, con gli oracoli di valle. Geometria pura su array, nessuna conoscenza del deck | **nuovo** |
| `src/meshrec/core/abaqus.py` | aree tributarie per nodo, ripartizione pesata, card dei posizionati, resoconto in `export_model` | modificato |
| `src/meshrec/core/pipeline.py` | passa `cfg.selettori` a `export_model` allo step 11 | modificato |
| `src/meshrec/core/steps.py` | `selettori` fra i blocchi che invalidano lo step 11 | modificato |
| `src/meshrec/core/sweep.py` | `selettori` fra i blocchi omessi dall'impronta quando vuoti | modificato |
| `tests/test_config.py` | validazione senza mesh | modificato |
| `tests/test_selezione.py` | risoluzione e oracoli di valle | **nuovo** |
| `tests/test_abaqus.py` | aree tributarie, ripartizione, card, resoconto | modificato |
| `tests/feasibility/test_calculix.py` | il deck con un posizionato dato a `ccx` vero | modificato |
| `tests/test_sweep.py`, `tests/test_steps.py` | impronta e invalidazione | modificati |
| `meshrec/docs/fase-6-carichi.md` | documento di esito | **nuovo** |
| `meshrec/docs/fase-6-cantiere/misura-carichi.py` | script con gli `assert` contro i valori pubblicati | **nuovo** |

**Perché `core/selezione.py` è un file a sé.** `core/config.py` è già a 770 righe e non sa nulla di mesh; `core/abaqus.py` è a 950 e parla di deck. La risoluzione è geometria su array — testabile da sola, senza file su disco.

### Cosa il piano riusa invece di riscrivere

- **`core/abaqus.py:334` `element_surface(elements, indici_nodo, element_type)`** restituisce già le coppie `(elemento, numero di faccia)` delle facce **di bordo** con **tutti** i nodi nell'insieme dato, in ordine deterministico. È esattamente la selezione di facce che la pesatura per area richiede.
- **`tests/test_abaqus.py:31` la fixture `cube_mesh`** (parallelepipedo `SIZE = (100.0, 40.0, 200.0)` tetraedrizzato) e **`tests/test_abaqus.py:39` `_base_and_top`**. I banchi dei test nuovi partono da lì: è l'idioma del file e produce superfici non degeneri, che un cubo scritto a mano non garantisce.
- **`tests/feasibility/test_calculix.py:92`** è il modello del test contro `ccx`: `shutil.which("ccx")` con skip, `subprocess.run([executable, "-i", "model"], cwd=tmp_path, ...)`, e i tre `assert` su `Job finished`, `*WARNING` e `*ERROR`.
- **`tests/feasibility/ccx_utils.py` `read_dat_displacements`** legge gli spostamenti dal `.dat`.

---

## Ordine e dipendenze

```
1 ──> 2 ──> 3 ──┐
                ├──> 6 ──> 7 ──> 8 ──> 9 ──> 10 ──> 12 ──> 13
4 ──────────────┤
5 ──────────────┘

11  (indipendente: basta il Task 1)
```

- **1 → 2 → 3**: schema, loader, carichi. Tutto senza mesh.
- **4, 5** possono procedere in parallelo a 2 e 3: non toccano `config.py`.
- **6** ha bisogno di 3 (i modelli) e 5 (le aree).
- **12** (rimisura di `CARICO_TOP`) ha bisogno di **6**, ed è il debito che 6 contrae.
- **13** (documento) chiude, dopo 10 e 12.

---

### Task 1: Lo schema dei quattro selettori

**Files:**
- Modify: `src/meshrec/core/config.py` (import in testa; modelli nuovi prima di `class CarichiConfig`, riga 648; campo su `PipelineConfig`, riga 664)
- Modify: `src/meshrec/core/abaqus.py:761-771` (`build_node_sets`)
- Modify: `src/meshrec/core/sweep.py:64` (`BLOCCHI_VUOTI_FUORI_IMPRONTA`) — vedi il riquadro qui sotto
- Test: `tests/test_config.py`

> **Perché una riga di `sweep.py` sta in questo task e non nel Task 11.** Misurato
> eseguendo: aggiungere `selettori` a `PipelineConfig` fa fallire subito
> `tests/test_config.py::test_l_impronta_di_una_corsa_registrata_non_cambia`.
> `sweep.fingerprint` fa `model_dump` sull'intera configurazione
> (`core/sweep.py:79`), quindi il campo nuovo compare anche nelle righe dei
> registri già scritte e ne cambia l'hash — cioè la provenienza della tabella
> sperimentale della tesi. La riga che lo impedisce è **una**, ed è la stessa
> regola che `carichi` usa già. Va qui perché senza di lei questo task non può
> lasciare la suite verde, e un task che committa una suite rossa non è finito.
> Il Task 11 conserva tutto il resto: `STEP_BLOCKS[11]`, il commento, e i test
> che provano entrambe le metà.

**Interfaces:**
- Consumes: `_ModelloBase` (`core/config.py:17`), `Field` e `model_validator`, già importati.
- Produces:
  - `NomeSet` — `Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+$")]`
  - `SelettoreBox`, `SelettoreSfera`, `SelettoreNodo`, `SelettoreNset` — modelli col campo discriminante `tipo`
  - `Selettore` — unione discriminata dei quattro
  - `NOMI_SET_DI_FACCIA: tuple[str, ...]` — i sei nomi che `build_node_sets` fabbrica
  - `PipelineConfig.selettori: dict[NomeSet, Selettore]`, predefinito `{}`

- [ ] **Step 1: Scrivi i test che falliscono**

In coda a `tests/test_config.py`:

```python
def test_i_quattro_selettori_si_dichiarano_per_nome():
    """Il blocco `selettori` accetta le quattro forme e le tiene per nome.

    Mutazione che lo uccide: dare a `SelettoreSfera.tipo` un letterale
    diverso da `"sfera"`. La dichiarazione della sfera non trova piu'
    alcun membro dell'unione che la accetti e la configurazione non nasce.

    **Non** lo uccide togliere `discriminator="tipo"`: misurato su
    pydantic 2.13.4, l'unione in modalita' smart sceglie comunque il
    modello giusto, perche' i quattro `Literal` sono valori esatti e
    distinti. Cio' che il discriminatore compra davvero e' la qualita'
    dell'errore, e ha il proprio test qui sotto.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={
            "piastra": {"tipo": "box", "min": [0.0, 0.0, 0.0], "max": [10.0, 10.0, 10.0]},
            "angolo": {"tipo": "sfera", "centro": [1.0, 2.0, 3.0], "raggio": 5.0},
            "punta": {"tipo": "nodo", "punto": [1.0, 2.0, 3.0]},
            "appoggio": {"tipo": "nset", "nome": "BASE"},
        },
    )
    assert isinstance(cfg.selettori["piastra"], config.SelettoreBox)
    assert isinstance(cfg.selettori["angolo"], config.SelettoreSfera)
    assert isinstance(cfg.selettori["punta"], config.SelettoreNodo)
    assert isinstance(cfg.selettori["appoggio"], config.SelettoreNset)
    assert cfg.selettori["angolo"].raggio == pytest.approx(5.0)


def test_un_tipo_di_selettore_ignoto_da_un_errore_solo():
    """Cio' che il discriminatore compra: un errore che nomina il campo giusto.

    Misurato su pydantic 2.13.4: con `discriminator="tipo"` un `tipo`
    sconosciuto produce **un** errore, che dice qual e' il campo
    sbagliato e quali valori accetta. Senza, l'unione in modalita' smart
    prova tutti e quattro i membri e ne riporta **quattro**, uno per
    membro, e chi legge deve capire da se' quale volesse.

    Mutazione che lo uccide: togliere `discriminator="tipo"` dall'alias
    `Selettore`. Il conteggio degli errori passa da 1 a 4.
    """
    with pytest.raises(ValidationError) as scoppio:
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"strana": {"tipo": "palla", "centro": [0.0, 0.0, 0.0], "raggio": 5.0}},
        )
    errori = scoppio.value.errors()
    assert len(errori) == 1, [e["type"] for e in errori]
    assert errori[0]["type"] == "union_tag_invalid"
    assert errori[0]["ctx"]["discriminator"] == "'tipo'"


def test_senza_selettori_il_blocco_e_vuoto_non_assente():
    """Chi non dichiara nulla ottiene un dizionario vuoto, non None.

    Mutazione che lo uccide: predefinito `None` invece di
    `default_factory=dict`. Il codice a valle itera sul blocco, e un None
    esplode con un TypeError invece di non fare nulla.
    """
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.selettori == {}


def test_la_box_rovesciata_e_rifiutata_e_nomina_la_componente():
    """`min > max` non arriva alla mesh: risolverebbe zero nodi come altri quattro.

    Mutazione che lo uccide: togliere il validatore. La box rovesciata
    viene accettata e da' lo stesso sintomo di quattro condizioni
    diverse, che e' precisamente cio' che la spec vieta.
    """
    with pytest.raises(ValidationError, match=r"\by\b"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"rotta": {"tipo": "box", "min": [0.0, 9.0, 0.0], "max": [10.0, 1.0, 10.0]}},
        )


@pytest.mark.parametrize("raggio", [0.0, -5.0])
def test_la_sfera_senza_raggio_positivo_e_rifiutata(raggio):
    """Raggio nullo o negativo non e' una sfera piccola, e' una sfera che non c'e'.

    Mutazione che lo uccide: `ge=0.0` al posto di `gt=0.0`, che lascia
    passare il raggio zero.
    """
    with pytest.raises(ValidationError):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"vuota": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": raggio}},
        )


@pytest.mark.parametrize("nome", config.NOMI_SET_DI_FACCIA)
def test_un_selettore_non_puo_chiamarsi_come_uno_dei_sei(nome):
    """I nomi dell'operatore e i sei di build_node_sets condividono lo spazio del deck.

    Mutazione che lo uccide: controllare la collisione solo su BASE.
    Il test passa su BASE e cade sugli altri cinque.
    """
    with pytest.raises(ValidationError, match=nome):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={nome: {"tipo": "nset", "nome": "TOP"}},
        )


def test_un_selettore_dichiarato_e_mai_citato_non_e_un_errore():
    """Dichiarare e non usare e' lecito: e' un appunto, non un difetto.

    Mutazione che lo uccide: un validatore che pretende che ogni
    selettore sia citato da almeno un carico.
    """
    cfg = crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={"mai_usato": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 1.0}},
    )
    assert "mai_usato" in cfg.selettori


def test_i_sei_nomi_dichiarati_sono_quelli_che_il_deck_fabbrica():
    """La costante e build_node_sets non possono divergere in silenzio.

    Mutazione che lo uccide: aggiungere un settimo nome alla costante
    senza il criterio corrispondente. `strict=True` nello zip solleva, e
    se anche non lo facesse le chiavi non combacerebbero piu'.
    """
    from meshrec.core import abaqus

    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.2, 0.8]])
    assert tuple(abaqus.build_node_sets(nodi, 0.01)) == config.NOMI_SET_DI_FACCIA
```

> `tests/test_config.py` non importa ancora `numpy`: aggiungi `import numpy as np` in testa al file.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Da `meshrec/`, un comando:

```
uv run pytest tests/test_config.py -k "selettor or box_rovesciata or sfera_senza_raggio or sei_nomi" -q
```

Atteso: FAIL, `AttributeError: module 'meshrec.core.config' has no attribute 'SelettoreBox'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

In testa a `core/config.py`: aggiungi `StringConstraints` agli import di pydantic e `Annotated`, `Literal` a quelli di `typing`.

Prima di `class CarichiConfig` (riga 648):

```python
# I sei nomi che `abaqus.build_node_sets` fabbrica a ogni esportazione.
# Stanno qui e non in `core/abaqus.py` perche' la validazione della
# configurazione deve conoscerli e `abaqus` importa gia' `config`: l'altro
# verso sarebbe un ciclo. `build_node_sets` li importa da qui, cosi' le due
# liste non possono divergere in silenzio.
NOMI_SET_DI_FACCIA: tuple[str, ...] = (
    "BASE", "TOP", "FACE_FRONT", "FACE_BACK", "SIDE_LEFT", "SIDE_RIGHT",
)

NomeSet = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+$")]


class SelettoreBox(_ModelloBase):
    """Tutti i nodi dentro un parallelepipedo allineato agli assi del modello.

    Le coordinate sono nel sistema di riferimento **dopo** `align_to_axes`,
    lo stesso di `wall_model.vtu`: e' il maglio che il deck contiene.
    L'estensione in quel sistema e' pubblicata in
    `metrics["11_export"]["extent"]`, e la bbox dei nodi presi in
    `metrics["11_export"]["selettori"]`, perche' l'operatore possa
    collocare una box senza indovinare.
    """

    tipo: Literal["box"]
    min: tuple[float, float, float] = Field(description="angolo minimo [mm]")
    max: tuple[float, float, float] = Field(description="angolo massimo [mm]")

    @model_validator(mode="after")
    def _la_box_non_e_rovesciata(self) -> "SelettoreBox":
        for asse, minimo, massimo in zip("xyz", self.min, self.max, strict=True):
            if minimo > massimo:
                raise ValueError(
                    f"la box ha min > max sulla componente {asse}: {minimo} > {massimo}. "
                    "Risolverebbe zero nodi, con lo stesso sintomo di altre quattro "
                    "condizioni diverse, e nessuno saprebbe quale sia successa"
                )
        return self


class SelettoreSfera(_ModelloBase):
    """Tutti i nodi entro un raggio da un centro. Coordinate come in SelettoreBox."""

    tipo: Literal["sfera"]
    centro: tuple[float, float, float] = Field(description="centro [mm]")
    raggio: float = Field(gt=0.0, description="raggio [mm]. Zero non e' una sfera piccola")


class SelettoreNodo(_ModelloBase):
    """Il singolo nodo piu' vicino a un punto. Coordinate come in SelettoreBox.

    Per costruzione non puo' rendere zero nodi: `argmin` un vincitore ce l'ha
    sempre, anche a chilometri di distanza. L'oracolo sta a valle, sulla
    distanza, e non qui.
    """

    tipo: Literal["nodo"]
    punto: tuple[float, float, float] = Field(description="punto di riferimento [mm]")


class SelettoreNset(_ModelloBase):
    """Un insieme di nodi gia' esistente nel deck, per nome."""

    tipo: Literal["nset"]
    nome: NomeSet = Field(
        description="nome di un *NSET gia' scritto, di norma uno dei sei di faccia"
    )


Selettore = Annotated[
    SelettoreBox | SelettoreSfera | SelettoreNodo | SelettoreNset,
    Field(discriminator="tipo"),
]
```

Su `PipelineConfig`, dopo `carichi` (riga 664):

```python
    selettori: dict[NomeSet, Selettore] = Field(
        default_factory=dict,
        description=(
            "regole geometriche nominate che indirizzano i nodi di una mesh senza "
            "topologia. Nominate e non annidate nei carichi: due carichi sullo "
            "stesso posto citano lo stesso nome, e una correzione fatta in un "
            "punto solo li muove entrambi"
        ),
    )

    @model_validator(mode="after")
    def _i_nomi_dei_selettori_non_collidono_coi_sei(self) -> "PipelineConfig":
        collisi = sorted(set(self.selettori) & set(NOMI_SET_DI_FACCIA))
        if collisi:
            raise ValueError(
                f"questi selettori portano il nome di un insieme che il deck "
                f"fabbrica da se': {collisi}. I sei sono {list(NOMI_SET_DI_FACCIA)}, "
                "e nel deck c'e' un solo spazio di nomi: il *NSET dell'operatore "
                "sovrascriverebbe quello di faccia"
            )
        return self
```

In `core/abaqus.py`, sostituisci il dizionario letterale di `build_node_sets` (righe 764-771) con una costruzione dai nomi importati:

```python
    criteri = (
        points[:, 2] <= low[2] + tolerance,
        points[:, 2] >= high[2] - tolerance,
        points[:, 0] <= low[0] + tolerance,
        points[:, 0] >= high[0] - tolerance,
        points[:, 1] <= low[1] + tolerance,
        points[:, 1] >= high[1] - tolerance,
    )
    return {
        nome: np.flatnonzero(criterio)
        for nome, criterio in zip(NOMI_SET_DI_FACCIA, criteri, strict=True)
    }
```

e aggiungi `NOMI_SET_DI_FACCIA` all'import da `meshrec.core.config` in testa a `core/abaqus.py`.

Infine, in `core/sweep.py:64`, la riga che tiene ferma la provenienza dei registri:

```python
BLOCCHI_VUOTI_FUORI_IMPRONTA: tuple[str, ...] = ("carichi", "selettori")
```

`fingerprint` (`core/sweep.py:82-84`) fa già `if not any((payload.get(blocco) or {}).values())`: su un `selettori` vuoto (`{}`) `any` è falso e il blocco esce dall'impronta. **Nessuna modifica alla funzione**, e nessun commento nuovo — il commento lo scrive il Task 11, che possiede il resto del cambiamento.

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_config.py tests/test_abaqus.py tests/test_sweep.py -q
```

Atteso: PASS. Tre cose da guardare in particolare:
1. `build_node_sets` rende le stesse sei chiavi **nello stesso ordine** di prima.
2. `tests/test_config.py::test_l_impronta_di_una_corsa_registrata_non_cambia` passa. Se fallisce, la riga di `sweep.py` non è stata scritta, o è stata scritta male.
3. Poi la suite intera, comando separato: `uv run pytest tests -q --ignore=tests/feasibility`, che deve stare **sopra 726**.

- [ ] **Step 5: Applica le mutazioni e verifica che i test muoiano**

**Due**, una per ciascuno dei due oracoli:

1. Cambia `SelettoreSfera.tipo` in `Literal["palla"]`, rilancia
   `uv run pytest tests/test_config.py -k quattro_selettori -q`, verifica FAIL, ripristina.
2. Togli `discriminator="tipo"` dall'alias `Selettore`, rilancia
   `uv run pytest tests/test_config.py -k tipo_di_selettore_ignoto -q`, verifica FAIL
   (il conteggio degli errori passa da 1 a 4), ripristina.

> Se la mutazione 2 non uccide il test, **fermati e riportalo**: significa che su
> questa versione di pydantic il discriminatore non compra nemmeno la qualità
> dell'errore, e allora non ha alcun oracolo — va tolto o giustificato altrimenti,
> non tenuto per fede.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/config.py meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/core/sweep.py meshrec/tests/test_config.py
git commit -m "feat(fase-6): i quattro selettori nella configurazione"
```

Il corpo del messaggio dice **perché** la riga di `sweep.py` viaggia con questo commit: senza di lei il campo nuovo cambia l'impronta di ogni riga già registrata.

---

### Task 2: Il loader rifiuta le chiavi YAML omonime

**Files:**
- Modify: `src/meshrec/core/config.py:779-782` (`load_config`) e `:861-864` (`load_experiment`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `_LoaderChiaviUniche(yaml.SafeLoader)` e `carica_yaml(path: Path) -> object`, usata da **entrambe** le letture del modulo.

**Perché entrambe.** `core/config.py:782` legge la configurazione della pipeline, `core/config.py:864` legge `ExperimentConfig`. È la stessa falla in due punti: patchare solo il primo lascia il secondo a perdere una chiave in silenzio.

> `save_config` (`:785-789`) **non** si tocca: scrive, non legge, e il suo `safe_dump` non ha nulla a che vedere con le chiavi omonime.

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def test_due_chiavi_omonime_nello_yaml_sono_rifiutate(tmp_path):
    """`safe_load` tiene l'ultima e la prima sparisce senza un segnale.

    E' l'unico ingresso degenere senza sintomo: gli altri almeno
    risolvono zero nodi. Un selettore corretto e riscritto sotto lo
    stesso nome verrebbe applicato nella versione che l'operatore
    credeva di aver sostituito.

    Mutazione che lo uccide: tornare a `yaml.safe_load`. Il file viene
    letto, `raggio` vale 9.0 e nessuno sa che il 5.0 c'era.
    """
    percorso = tmp_path / "config.yaml"
    percorso.write_text(
        "input:\n  path: nuvola.ply\n"
        "analysis:\n  material:\n    name: MURATURA\n    young: 1500.0\n"
        "    poisson: 0.2\n    density: 1.8e-9\n"
        "selettori:\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 5.0\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 9.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="angolo"):
        config.load_config(percorso)


def test_anche_il_registro_degli_esperimenti_rifiuta_le_chiavi_omonime(tmp_path):
    """La stessa falla sta su due safe_load: si chiude in un punto e si usa in due.

    Il `name` duplicato e' la forma minima: `axes` e' una lista, e le
    chiavi omonime esistono solo dentro una mappa.

    Mutazione che lo uccide: passare il loader solo a `load_config`.
    Questo test cade, l'altro passa.
    """
    percorso = tmp_path / "experiment.yaml"
    percorso.write_text(
        "name: primo\n"
        "name: secondo\n"
        "base: base.yaml\n"
        "axes:\n  - path: tet.min_ratio\n    values: [1.6, 1.8]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="name"):
        config.load_experiment(percorso)
```

> **Letto in sessione, dopo il Task 1** (che ha aggiunto ~76 righe a `config.py`, quindi i numeri della prima stesura sono scaduti):
> `load_config` sta a `core/config.py:779` con la sua `yaml.safe_load` a `:782`;
> `load_experiment` sta a `:861` con la sua `yaml.safe_load` a `:864`.
> `ExperimentConfig` (`:835`) richiede `name: str`, `base: Path` e `axes: list[AxisSpec]` con `min_length=1`; `AxisSpec` (`:828`) richiede `path: str` e `values` con `min_length=1`. Non esistono campi `out_dir` né `assi`. **Riapri quelle righe e confermale prima di scrivere**: se il conteggio è cambiato ancora, vale quello che leggi tu.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_config.py -k omonime -q
```

Atteso: FAIL — nessuna eccezione, il file viene letto e l'ultima chiave vince.

- [ ] **Step 3: Scrivi l'implementazione minima**

In `core/config.py`, prima di `load_config`:

```python
class _LoaderChiaviUniche(yaml.SafeLoader):
    """`SafeLoader` che rifiuta due chiavi omonime invece di tenere l'ultima.

    Misurato: con il loader di serie la prima delle due sparisce senza alcun
    segnale. E' l'unico ingresso degenere che non ha un sintomo -- gli altri
    almeno risolvono zero nodi -- e per questo si rifiuta alla lettura invece
    che a valle.

    Deriva da `yaml.SafeLoader` e ne eredita i costruttori: nessun tag
    `!!python/object`, nessuna costruzione di tipi arbitrari. Aggiunge un
    controllo, non toglie un divieto.
    """

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        viste: set[object] = set()
        for chiave_node, _ in node.value:
            chiave = self.construct_object(chiave_node, deep=deep)
            if chiave in viste:
                raise ValueError(
                    f"la chiave '{chiave}' compare due volte nello stesso blocco "
                    f"({chiave_node.start_mark}): il lettore terrebbe l'ultima e la "
                    "prima sparirebbe senza un segnale"
                )
            viste.add(chiave)
        return super().construct_mapping(node, deep=deep)


def carica_yaml(path: Path) -> object:
    """L'unica lettura YAML del modulo, con il rifiuto delle chiavi omonime.

    `yaml.load` con un loader che **eredita da SafeLoader** ha esattamente i
    costruttori di `safe_load`. Non sostituire il loader con `yaml.Loader` o
    `yaml.UnsafeLoader`, che i tag `!!python/object` li eseguono davvero.
    """
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=_LoaderChiaviUniche)  # noqa: S506
```

Poi il corpo di `load_config` (`core/config.py:779-782`):

```python
def load_config(path: Path) -> PipelineConfig:
    """Legge un config.yaml senza perdita rispetto a quanto scritto da `save_config`."""
    return PipelineConfig.model_validate(carica_yaml(path))
```

e allo stesso modo `load_experiment` (`core/config.py:861-864`):

```python
def load_experiment(path: Path) -> ExperimentConfig:
    """Legge la dichiarazione di un esperimento."""
    return ExperimentConfig.model_validate(carica_yaml(path))
```

> **Nota per chi rivede.** Un analizzatore statico segnala `yaml.load(...)` come pericoloso, ed è una segnalazione giusta in generale: col loader predefinito `yaml.load` esegue codice arbitrario. Qui non si applica, perché `_LoaderChiaviUniche` **deriva da `yaml.SafeLoader`**. La condizione da non violare è quella: la classe base resta `yaml.SafeLoader`. Il risultato passa poi da `model_validate` di pydantic, che è la seconda barriera.

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_config.py -q
```

Atteso: PASS, incluso il round-trip già esistente.

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Rimetti `yaml.safe_load` nel solo `load_config`: rilancia
`uv run pytest tests/test_config.py -k omonime -q`. Deve fallire il primo test e passare il secondo. Poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/config.py meshrec/tests/test_config.py
git commit -m "fix(config): due chiavi omonime nello YAML si rifiutano invece di perderne una"
```

---

### Task 3: `carichi.posizionati` nello schema

**Files:**
- Modify: `src/meshrec/core/config.py` (`Momento` e `CaricoPosizionato` prima di `CarichiConfig`; campo su `CarichiConfig:648`; validatore incrociato su `PipelineConfig`)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `NomeSet`, `Selettore` (Task 1); `NOMI_PASSO_RISERVATI` (`core/config.py:261`).
- Produces:
  - `Momento` — `asse: tuple[float, float, float]`, `modulo: float` (gt 0, N·mm), `braccio: float` (gt 0, mm)
  - `CaricoPosizionato` — `nome: NomeSet`, `selettore: NomeSet`, `forza: tuple[float, float, float] | None`, `momento: Momento | None`
  - `CarichiConfig.posizionati: tuple[CaricoPosizionato, ...]`, predefinito `()`

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def _config_con_posizionato(**campi_carico):
    base = {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -12000.0]}
    base.update(campi_carico)
    return crea_config(
        input=config.InputConfig(path="nuvola.ply"),
        selettori={"piastra": {"tipo": "box", "min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]}},
        carichi=config.CarichiConfig(posizionati=[base]),
    )


def test_un_posizionato_porta_nome_selettore_e_forza():
    """La forma minima di un carico posizionato entra e si rilegge.

    Mutazione che lo uccide: predefinito `None` su `posizionati` invece
    della tupla vuota. `cfg.carichi.posizionati[0]` diventa un TypeError.
    """
    cfg = _config_con_posizionato()
    assert cfg.carichi.posizionati[0].nome == "PRESSA"
    assert cfg.carichi.posizionati[0].forza == (0.0, 0.0, -12000.0)
    assert cfg.carichi.posizionati[0].momento is None


def test_senza_posizionati_la_tupla_e_vuota():
    """Chi non dichiara carichi posizionati ottiene (), non None.

    Mutazione che lo uccide: `default=None`. Il codice a valle itera.
    """
    cfg = crea_config(input=config.InputConfig(path="nuvola.ply"))
    assert cfg.carichi.posizionati == ()


def test_un_carico_dichiara_o_forza_o_momento_mai_entrambi():
    """Forza e momento insieme sono due carichi: due voci, non una.

    Mutazione che lo uccide: un validatore che controlla solo il caso
    "nessuno dei due". Questo test cade, l'altro passa.
    """
    with pytest.raises(ValidationError, match="uno solo"):
        _config_con_posizionato(momento={"asse": [0.0, 0.0, 1.0], "modulo": 1.0, "braccio": 1.0})


def test_un_carico_senza_forza_ne_momento_e_rifiutato():
    """Un carico che non dice quanto vale non e' un carico.

    Mutazione che lo uccide: un validatore che controlla solo il caso
    "entrambi". Questo test cade, l'altro passa.
    """
    with pytest.raises(ValidationError, match="uno solo"):
        _config_con_posizionato(forza=None)


def test_la_forza_nulla_e_rifiutata():
    """Un vettore forza di modulo zero scriverebbe un passo che non carica nulla.

    Mutazione che lo uccide: togliere il controllo sul modulo. Il carico
    entra e produce un passo statico identico al peso proprio, con un
    nome che promette altro.
    """
    with pytest.raises(ValidationError, match="modulo"):
        _config_con_posizionato(forza=[0.0, 0.0, 0.0])


def test_un_carico_che_cita_un_selettore_non_dichiarato_e_rifiutato():
    """Il riferimento si controlla senza mesh: e' un rifiuto a validazione.

    Mutazione che lo uccide: spostare il controllo a valle, dove il
    sintomo sarebbe "zero nodi" e si confonderebbe con altri quattro.
    """
    with pytest.raises(ValidationError, match="fantasma"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(
                posizionati=[{"nome": "PRESSA", "selettore": "fantasma", "forza": [0.0, 0.0, -1.0]}]
            ),
        )


@pytest.mark.parametrize("riservato", config.NOMI_PASSO_RISERVATI)
def test_un_carico_non_puo_chiamarsi_come_un_passo_riservato(riservato):
    """Il nome del carico diventa il nome del passo, e tre nomi sono gia' presi.

    Mutazione che lo uccide: controllare solo CARICO_TOP.
    """
    with pytest.raises(ValidationError, match=riservato):
        _config_con_posizionato(nome=riservato)


def test_due_posizionati_non_possono_avere_lo_stesso_nome():
    """Due passi omonimi nel deck: i due risultati diventano indistinguibili.

    Mutazione che lo uccide: togliere il controllo di unicita'. Il deck
    esce con due `** NOME PASSO: PRESSA`.
    """
    with pytest.raises(ValidationError, match="PRESSA"):
        crea_config(
            input=config.InputConfig(path="nuvola.ply"),
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(posizionati=[
                {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -1.0]},
                {"nome": "PRESSA", "selettore": "piastra", "forza": [0.0, 0.0, -2.0]},
            ]),
        )
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_config.py -k posizionat -q
```

Atteso: FAIL, `AttributeError` su `CarichiConfig.posizionati`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Prima di `class CarichiConfig`:

```python
class Momento(_ModelloBase):
    """Momento realizzato come coppia di forze staticamente equivalente.

    Non come `*CLOAD` sui gradi 4-6: misurato su un deck di sonda dato a
    `ccx` 2.22, un momento concentrato su un C3D4 e' scartato **in
    silenzio** -- zero occorrenze di `warning` o `error`, `number of
    equations 3`, spostamento `0.000000E+00` su tutte e tre le componenti.
    La guardia di `core/solve.py:438` non lo intercetta perche' non c'e'
    nessun warning da intercettare.

    `braccio` dichiara quanto distano fra loro le due forze della coppia, e
    il programma lo contraddice se i nodi presi non lo sostengono. Il
    momento realizzato resta `modulo`: e' la forza a calibrarsi sul braccio
    che i nodi offrono davvero, non il momento a scostarsi da quello
    dichiarato.
    """

    asse: tuple[float, float, float] = Field(
        description="asse del momento, versore non normalizzato"
    )
    modulo: float = Field(gt=0.0, description="modulo del momento [N*mm]")
    braccio: float = Field(gt=0.0, description="distanza fra le due forze della coppia [mm]")


class CaricoPosizionato(_ModelloBase):
    """Un carico che porta con se' il proprio indirizzo.

    E' la differenza vera dagli altri tre casi di `CarichiConfig`, che sono
    dichiarati a mano anche loro ma citano un insieme che il deck fabbrica.
    """

    nome: NomeSet = Field(description="nome del passo statico nel deck")
    selettore: NomeSet = Field(description="nome di un selettore dichiarato in `selettori`")
    forza: tuple[float, float, float] | None = Field(
        default=None, description="risultante [N], ripartita per area sui nodi presi"
    )
    momento: Momento | None = None

    @model_validator(mode="after")
    def _o_forza_o_momento(self) -> "CaricoPosizionato":
        if (self.forza is None) == (self.momento is None):
            raise ValueError(
                f"il carico '{self.nome}' deve dichiarare uno solo fra `forza` e "
                "`momento`: entrambi sono due carichi e vanno scritti come due voci, "
                "nessuno dei due non e' un carico"
            )
        if self.forza is not None and not any(self.forza):
            raise ValueError(
                f"il carico '{self.nome}' ha forza di modulo nullo: scriverebbe un "
                "passo statico identico al peso proprio, con un nome che promette altro"
            )
        return self
```

Su `CarichiConfig`, dopo `modale`:

```python
    posizionati: tuple[CaricoPosizionato, ...] = Field(
        default=(),
        description=(
            "carichi che portano con se' il proprio selettore. Tupla vuota e non "
            "None: il codice a valle itera, e una corsa senza posizionati e una "
            "con la lista vuota sono lo stesso esperimento -- e' la regola che "
            "l'impronta di sweep gia' applica al blocco intero"
        ),
    )
```

Su `PipelineConfig`, accanto al validatore del Task 1:

```python
    @model_validator(mode="after")
    def _i_posizionati_citano_selettori_dichiarati(self) -> "PipelineConfig":
        visti: set[str] = set()
        for carico in self.carichi.posizionati:
            if carico.selettore not in self.selettori:
                raise ValueError(
                    f"il carico '{carico.nome}' cita il selettore "
                    f"'{carico.selettore}', che non e' dichiarato. Dichiarati: "
                    f"{sorted(self.selettori)}"
                )
            if carico.nome in NOMI_PASSO_RISERVATI or carico.nome == self.analysis.step_name:
                raise ValueError(
                    f"il carico '{carico.nome}' porta il nome di un passo gia' preso: "
                    f"i riservati sono {list(NOMI_PASSO_RISERVATI)} e il passo di peso "
                    f"proprio si chiama '{self.analysis.step_name}'"
                )
            if carico.nome in visti:
                raise ValueError(
                    f"due carichi posizionati si chiamano '{carico.nome}': il deck "
                    "scriverebbe due passi omonimi e i due risultati sarebbero "
                    "indistinguibili nel file risolto"
                )
            visti.add(carico.nome)
        return self
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_config.py -q
```

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Cambia `(self.forza is None) == (self.momento is None)` in
`self.forza is None and self.momento is None`, rilancia
`uv run pytest tests/test_config.py -k o_forza_o_momento -q`: deve fallire il test "mai entrambi" e passare quello "senza forza ne momento". Ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/config.py meshrec/tests/test_config.py
git commit -m "feat(fase-6): carichi.posizionati nello schema, con forza o momento"
```

---

### Task 4: La risoluzione geometrica

**Files:**
- Create: `src/meshrec/core/selezione.py`
- Test: `tests/test_selezione.py`

**Interfaces:**
- Consumes: `Selettore`, `SelettoreBox`, `SelettoreSfera`, `SelettoreNodo`, `SelettoreNset` (Task 1).
- Produces:
  - `SPIGOLI_DI_TOLLERANZA: int = 3`
  - `spigolo_medio(nodi: np.ndarray, elementi: np.ndarray) -> float`
  - `risolvi(selettore, nodi, node_sets, *, nome: str, spigolo: float) -> np.ndarray` — indici `int64`, ordinati, senza ripetizioni
  - `risolvi_tutti(selettori: dict[str, Selettore], nodi, elementi, node_sets) -> dict[str, np.ndarray]`

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_selezione.py`:

```python
"""Da regola geometrica a indici di nodo, e gli oracoli che la contraddicono."""

import numpy as np
import pytest

from meshrec.core import config, selezione


def _banco():
    """Otto nodi ai vertici di un cubo di lato 10 mm, due tetraedri.

    Esplicito e non tetraedrizzato: qui si prova il criterio di selezione,
    e un banco di cui si conoscono a memoria gli otto indici rende
    leggibile ogni assert. La mesh vera arriva nei test di
    `tests/test_abaqus.py`, dove la superficie conta.
    """
    nodi = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [10.0, 10.0, 0.0],
         [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [0.0, 10.0, 10.0], [10.0, 10.0, 10.0]]
    )
    elementi = np.array([[0, 1, 2, 4], [3, 5, 6, 7]], dtype=np.int64)
    node_sets = {"BASE": np.array([0, 1, 2, 3]), "TOP": np.array([4, 5, 6, 7])}
    return nodi, elementi, node_sets


def test_la_box_prende_i_nodi_dentro_e_solo_quelli():
    """Il criterio e' inclusivo sugli estremi e non prende nulla oltre.

    Mutazione che lo uccide: `<` al posto di `<=` sul massimo. Il nodo 4,
    che sta esattamente a z = 10, esce dalla selezione.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(-1.0, -1.0, 9.0), max=(11.0, 11.0, 11.0))
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="alto", spigolo=10.0)
    assert presi.tolist() == [4, 5, 6, 7]


def test_la_sfera_prende_per_distanza_dal_centro():
    """Dentro e' distanza <= raggio, non < raggio.

    Mutazione che lo uccide: confronto stretto. I nodi a distanza
    esattamente 10 dal centro escono e la lista si accorcia a uno.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=10.0)
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="angolo", spigolo=10.0)
    assert presi.tolist() == [0, 1, 2, 4]


def test_il_selettore_nodo_prende_il_piu_vicino():
    """Un nodo solo, quello di distanza minima.

    Mutazione che lo uccide: `argmax` al posto di `argmin`.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNodo(tipo="nodo", punto=(9.5, 9.5, 9.5))
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="punta", spigolo=10.0)
    assert presi.tolist() == [7]


def test_il_selettore_nset_rende_l_insieme_esistente():
    """Il nome cita un *NSET gia' costruito e ne rende gli indici.

    Mutazione che lo uccide: rendere tutti i nodi invece dell'insieme citato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNset(tipo="nset", nome="BASE")
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="appoggio", spigolo=10.0)
    assert presi.tolist() == [0, 1, 2, 3]


def test_un_nset_inesistente_solleva_e_nomina_quelli_che_ci_sono():
    """Il nome sbagliato si scopre alla risoluzione, e l'errore dice le alternative.

    Mutazione che lo uccide: `node_sets.get(nome, np.array([]))`, che
    renderebbe zero nodi e confonderebbe il sintomo con altri quattro.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNset(tipo="nset", nome="LATO")
    with pytest.raises(ValueError, match="BASE"):
        selezione.risolvi(selettore, nodi, node_sets, nome="appoggio", spigolo=10.0)


def test_zero_nodi_solleva_e_riporta_l_estensione_della_mesh():
    """Il sintomo comune a cinque ingressi degeneri ha un oracolo esplicito.

    Mutazione che lo uccide: rendere l'array vuoto invece di sollevare.
    Il carico finirebbe applicato a nulla e il deck uscirebbe valido.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(100.0, 100.0, 100.0), max=(200.0, 200.0, 200.0))
    with pytest.raises(ValueError, match="zero nodi"):
        selezione.risolvi(selettore, nodi, node_sets, nome="lontana", spigolo=10.0)


def test_tutti_i_nodi_solleva():
    """Un selettore che prende tutto non e' un posizionato, e' un peso proprio storto.

    Mutazione che lo uccide: togliere il controllo. La risultante si
    spalma sull'intero solido e il caso di carico perde significato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(-1.0, -1.0, -1.0), max=(11.0, 11.0, 11.0))
    with pytest.raises(ValueError, match="tutti"):
        selezione.risolvi(selettore, nodi, node_sets, nome="tutto", spigolo=10.0)


def test_il_nodo_troppo_lontano_solleva_oltre_tre_spigoli():
    """`argmin` un vincitore ce l'ha sempre: l'oracolo e' la distanza, non il conteggio.

    Mutazione che lo uccide: alzare SPIGOLI_DI_TOLLERANZA a 300. Il punto
    a 1000 mm da una mesh di spigolo 10 entra, e il carico finisce su un
    nodo che l'operatore non ha indicato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNodo(tipo="nodo", punto=(1000.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="spigol"):
        selezione.risolvi(selettore, nodi, node_sets, nome="persa", spigolo=10.0)


def test_lo_spigolo_medio_si_misura_sugli_spigoli_degli_elementi():
    """Un tetraedro regolare di lato 10 ha spigolo medio 10.

    Mutazione che lo uccide: misurare sulle distanze fra tutti i nodi
    della mesh invece che sugli spigoli degli elementi. Su un banco con
    due tetraedri lontani fra loro la media esplode.
    """
    nodi = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [5.0, 8.66, 0.0], [5.0, 2.89, 8.16]])
    elementi = np.array([[0, 1, 2, 3]], dtype=np.int64)
    assert selezione.spigolo_medio(nodi, elementi) == pytest.approx(10.0, abs=0.05)


def test_risolvi_tutti_senza_selettori_rende_un_dizionario_vuoto():
    """Ingresso degenere del caso normale: chi non dichiara nulla non paga nulla.

    Mutazione che lo uccide: togliere il ritorno anticipato. `spigolo_medio`
    verrebbe calcolato su una mesh che nessuno usera', e su un array di
    elementi vuoto solleverebbe.
    """
    nodi, elementi, node_sets = _banco()
    assert selezione.risolvi_tutti({}, nodi, elementi, node_sets) == {}
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_selezione.py -q
```

Atteso: FAIL, `ModuleNotFoundError: No module named 'meshrec.core.selezione'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Crea `src/meshrec/core/selezione.py`:

```python
"""Da regola geometrica dichiarata a indici di nodo, sulla mesh gia' allineata.

Il modulo non sa nulla di deck: prende array e rende indici. Gli oracoli che
stanno qui sono quelli che **hanno bisogno della mesh** -- zero nodi, tutti i
nodi, il nodo piu' vicino troppo lontano. Quelli che non ne hanno bisogno
(forme impossibili, nomi che collidono, riferimenti a selettori non
dichiarati) stanno a monte, in `core/config.py`, e si rifiutano senza aver
letto una nuvola: e' la spaccatura che rende distinguibili cinque ingressi
degeneri che altrimenti darebbero tutti lo stesso sintomo.
"""

from __future__ import annotations

import numpy as np

from meshrec.core.config import (
    Selettore,
    SelettoreBox,
    SelettoreNodo,
    SelettoreNset,
    SelettoreSfera,
)

# Quanto lontano puo' cadere il nodo piu' vicino prima che la selezione sia un
# errore di battitura invece di un indirizzo. Tre spigoli e' misurato: sul
# telaio (spigolo medio 32,82 mm) il punto legittimo di prova cadeva a
# 32,17 mm -- un solo spigolo -- e quello degenere a 9 979,9 mm.
SPIGOLI_DI_TOLLERANZA: int = 3


def spigolo_medio(nodi: np.ndarray, elementi: np.ndarray) -> float:
    """Lunghezza media degli spigoli degli elementi.

    Sugli spigoli e non su tutte le coppie di nodi della mesh: due nodi in
    capo opposto al solido non sono uno spigolo, e la loro distanza non
    corrisponde a nulla che la mesh sappia risolvere.
    """
    punti = np.asarray(nodi, dtype=np.float64)
    celle = np.asarray(elementi, dtype=np.int64)
    colonne = celle.shape[1]
    coppie = [(a, b) for a in range(colonne) for b in range(a + 1, colonne)]
    lunghezze = np.concatenate([
        np.linalg.norm(punti[celle[:, a]] - punti[celle[:, b]], axis=1) for a, b in coppie
    ])
    return float(lunghezze.mean())


def risolvi(
    selettore: Selettore,
    nodi: np.ndarray,
    node_sets: dict[str, np.ndarray],
    *,
    nome: str,
    spigolo: float,
) -> np.ndarray:
    """Gli indici di nodo che la regola prende, ordinati e senza ripetizioni.

    `nome` serve ai messaggi d'errore: un rifiuto che non dice quale
    selettore ha sbagliato costringe a cercarlo a mano nello YAML.
    """
    punti = np.asarray(nodi, dtype=np.float64)

    if isinstance(selettore, SelettoreBox):
        minimo = np.asarray(selettore.min, dtype=np.float64)
        massimo = np.asarray(selettore.max, dtype=np.float64)
        presi = np.flatnonzero(np.all((punti >= minimo) & (punti <= massimo), axis=1))
    elif isinstance(selettore, SelettoreSfera):
        centro = np.asarray(selettore.centro, dtype=np.float64)
        presi = np.flatnonzero(np.linalg.norm(punti - centro, axis=1) <= selettore.raggio)
    elif isinstance(selettore, SelettoreNodo):
        punto = np.asarray(selettore.punto, dtype=np.float64)
        distanze = np.linalg.norm(punti - punto, axis=1)
        vincitore = int(np.argmin(distanze))
        limite = SPIGOLI_DI_TOLLERANZA * spigolo
        if distanze[vincitore] > limite:
            raise ValueError(
                f"il selettore '{nome}' chiede il nodo piu' vicino a "
                f"{tuple(selettore.punto)}, e il piu' vicino sta a "
                f"{distanze[vincitore]:.1f} mm, oltre i {limite:.1f} mm di "
                f"{SPIGOLI_DI_TOLLERANZA} spigoli medi ({spigolo:.2f} mm). "
                "Un argmin un vincitore ce l'ha sempre, anche a chilometri: "
                "questo non e' un indirizzo, e' un punto scritto male"
            )
        presi = np.array([vincitore], dtype=np.int64)
    elif isinstance(selettore, SelettoreNset):
        if selettore.nome not in node_sets:
            raise ValueError(
                f"il selettore '{nome}' cita l'insieme '{selettore.nome}', che non "
                f"e' fra quelli del deck: {sorted(node_sets)}"
            )
        presi = np.asarray(node_sets[selettore.nome], dtype=np.int64)
    else:  # pragma: no cover - l'unione discriminata non lascia altri casi
        raise TypeError(f"selettore di tipo sconosciuto: {type(selettore)!r}")

    presi = np.unique(presi.astype(np.int64))

    if presi.size == 0:
        raise ValueError(
            f"il selettore '{nome}' risolve zero nodi. Estensione della mesh: "
            f"min {punti.min(axis=0).round(1).tolist()}, "
            f"max {punti.max(axis=0).round(1).tolist()}. "
            "Un carico applicato a nulla non e' un carico"
        )
    if presi.size == punti.shape[0]:
        raise ValueError(
            f"il selettore '{nome}' prende tutti i {presi.size} nodi della mesh. "
            "Una risultante spalmata sull'intero solido non e' un carico "
            "posizionato, e' un peso proprio storto"
        )
    return presi


def risolvi_tutti(
    selettori: dict[str, Selettore],
    nodi: np.ndarray,
    elementi: np.ndarray,
    node_sets: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Tutti i selettori dichiarati, risolti una volta sola sulla stessa mesh.

    Il ritorno anticipato non e' una micro-ottimizzazione: senza di esso
    `spigolo_medio` verrebbe calcolato anche su una corsa che non dichiara
    selettori, cioe' su tutte quelle gia' fatte.
    """
    if not selettori:
        return {}
    spigolo = spigolo_medio(nodi, elementi)
    return {
        nome: risolvi(selettore, nodi, node_sets, nome=nome, spigolo=spigolo)
        for nome, selettore in selettori.items()
    }
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_selezione.py -q
```

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Porta `SPIGOLI_DI_TOLLERANZA` a `300`, rilancia
`uv run pytest tests/test_selezione.py -k troppo_lontano -q`, verifica FAIL, poi rimetti `3`.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/selezione.py meshrec/tests/test_selezione.py
git commit -m "feat(fase-6): risoluzione dei selettori in indici di nodo"
```

---

### Task 5: Le aree tributarie per nodo

**Files:**
- Modify: `src/meshrec/core/abaqus.py` (nuova funzione subito dopo `surface_area`, che finisce alla riga 465)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `FACCE_DEL_SOLUTORE` (`core/abaqus.py:294`), `_ANGOLI_PER_COLONNE` (`:309`), `NODI_PER_ELEMENTO`, `element_surface` (`:334`), `surface_area` (`:440`).
- Produces: `aree_tributarie(nodes, elements, superficie: list[tuple[int, int]], element_type: str) -> np.ndarray` — array lungo `len(nodes)`, area in mm² per nodo, zero dove il nodo non tocca alcuna faccia della superficie.

- [ ] **Step 1: Scrivi i test che falliscono**

In coda a `tests/test_abaqus.py`:

```python
def test_le_aree_tributarie_sommano_all_area_della_superficie(cube_mesh):
    """La ripartizione non crea ne' perde area: la somma e' quella di surface_area.

    Mutazione che lo uccide: dare a ogni nodo l'area intera del triangolo
    invece di un terzo. La somma diventa tripla.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    superficie = abaqus.element_surface(tetraedri, sets["TOP"], "C3D4")
    assert superficie, "la faccia superiore del banco e' vuota: banco inadatto"
    aree = abaqus.aree_tributarie(nodi, tetraedri, superficie, "C3D4")
    assert aree.shape == (len(nodi),)
    assert aree.sum() == pytest.approx(abaqus.surface_area(nodi, tetraedri, superficie, "C3D4"))


def test_solo_i_nodi_della_superficie_hanno_area(cube_mesh):
    """Chi non tocca alcuna faccia della superficie prende zero, non una quota.

    Mutazione che lo uccide: inizializzare l'array a un valore diverso da
    zero, o ripartire il totale su tutti i nodi della mesh.
    """
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    superficie = abaqus.element_surface(tetraedri, sets["TOP"], "C3D4")
    aree = abaqus.aree_tributarie(nodi, tetraedri, superficie, "C3D4")
    con_area = set(np.flatnonzero(aree > 0).tolist())
    assert con_area, "nessun nodo ha area: la superficie e' vuota"
    assert con_area <= set(sets["TOP"].tolist())


def test_una_superficie_vuota_da_aree_tutte_nulle(cube_mesh):
    """Ingresso degenere: nessuna faccia, nessuna area, e nessuna eccezione qui.

    L'oracolo del totale nullo sta in `ripartisci`, dove c'e' un carico da
    applicare e un nome da mettere nel messaggio: questa funzione misura e
    basta.

    Mutazione che lo uccide: sollevare qui invece di rendere zeri. Il
    chiamante perderebbe la possibilita' di dire quale carico ha fallito.
    """
    nodi, tetraedri = cube_mesh
    aree = abaqus.aree_tributarie(nodi, tetraedri, [], "C3D4")
    assert aree.shape == (len(nodi),)
    assert not aree.any()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_abaqus.py -k tributari -q
```

Atteso: FAIL, `AttributeError: module 'meshrec.core.abaqus' has no attribute 'aree_tributarie'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Subito dopo `surface_area` in `core/abaqus.py`:

```python
def aree_tributarie(
    nodes: np.ndarray,
    elements: np.ndarray,
    superficie: list[tuple[int, int]],
    element_type: str,
) -> np.ndarray:
    """L'area della superficie ripartita sui suoi nodi, un terzo per triangolo.

    Gemella di `surface_area`: stesso ciclo, stesse tabelle, stesso ventaglio
    dal primo nodo per una faccia di piu' di tre nodi. Cambia solo dove
    l'area finisce -- in un array indicizzato per nodo invece che in uno
    scalare -- e la somma dell'array e' per costruzione il valore che
    `surface_area` rende sulla stessa superficie.

    Serve alla ripartizione di una risultante: uniforme per nodo il carico
    si concentra dove i nodi sono piu' fitti, che e' una proprieta' del
    maglio e non della struttura.

    Un nodo che non appartiene ad alcuna faccia della superficie resta a
    zero. Non e' un errore qui: e' un fatto che il chiamante deve poter
    riportare.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = _ANGOLI_PER_COLONNE[NODI_PER_ELEMENTO[element_type]]

    aree = np.zeros(punti.shape[0], dtype=np.float64)
    for elemento, numero in superficie:
        nodi = [elementi[elemento][indice] for indice in FACCE_DEL_SOLUTORE[angoli][numero - 1]]
        for primo, secondo in zip(nodi[1:-1], nodi[2:], strict=True):
            lato_a = punti[primo] - punti[nodi[0]]
            lato_b = punti[secondo] - punti[nodi[0]]
            area = float(np.linalg.norm(np.cross(lato_a, lato_b)) / 2.0)
            for nodo in (nodi[0], primo, secondo):
                aree[nodo] += area / 3.0
    return aree
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_abaqus.py -q
```

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Cambia `area / 3.0` in `area`, rilancia
`uv run pytest tests/test_abaqus.py -k tributarie_sommano -q`, verifica FAIL (somma tripla), poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-6): aree tributarie per nodo, gemella di surface_area"
```

---

### Task 6: La ripartizione pesata, e `carico_sommita` ci passa

**Files:**
- Modify: `src/meshrec/core/abaqus.py` (nuova funzione dopo `aree_tributarie`; `write_inp:211-222`, il ramo `carico_sommita`)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `aree_tributarie` (Task 5), `element_surface` (`core/abaqus.py:334`).
- Produces: `ripartisci(risultante: float, nodes, elements, indici: np.ndarray, element_type: str, *, nome: str) -> tuple[np.ndarray, dict[str, object]]` — le quote per nodo, allineate a `indici`, somma esattamente `risultante`, e il resoconto con le chiavi `nodi`, `area_totale`, `nodi_ad_area_nulla`.

**Questo task cambia numeri pubblicati.** `CARICO_TOP` su `runs/lab_telaio_v2` non sarà più 3.036 righe uguali. La ripubblicazione è il **Task 12**: non farla qui, ma non dimenticarla.

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def test_la_ripartizione_pesata_conserva_la_risultante(cube_mesh):
    """Le quote sommano esattamente alla risultante dichiarata.

    Mutazione che lo uccide: togliere la normalizzazione sul totale e
    usare `risultante * area`. La somma smette di chiudere.
    """
    nodi, tetraedri = cube_mesh
    indici = _base_and_top(nodi)["TOP"]
    quote, _ = abaqus.ripartisci(1200.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.shape == indici.shape
    assert quote.sum() == pytest.approx(1200.0)


def test_la_ripartizione_pesata_non_e_uniforme(cube_mesh):
    """E' il punto della pesatura: un nodo interno alla faccia prende piu' di uno d'angolo.

    Il banco e' il parallelepipedo tetraedrizzato, dove la faccia
    superiore ha nodi di grado diverso: e' la condizione reale, non una
    costruita per l'occasione.

    Mutazione che lo uccide: rendere `risultante / len(indici)`, cioe' la
    ripartizione uniforme di prima. Le quote diventano tutte uguali e lo
    scarto fra massimo e minimo si annulla.
    """
    nodi, tetraedri = cube_mesh
    indici = _base_and_top(nodi)["TOP"]
    quote, _ = abaqus.ripartisci(1200.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.max() > quote.min() * 1.05


def test_i_nodi_ad_area_nulla_prendono_zero_e_sono_contati(cube_mesh):
    """La quota nulla e' un fatto da riportare, non da nascondere.

    Al set TOP si aggiunge un nodo interno, che nessuna faccia di bordo
    interamente contenuta tocca: prende zero, e il resoconto lo conta.

    Mutazione che lo uccide: contare i nodi ad area nulla con `>= 0`
    invece che `== 0`. Il resoconto direbbe che sono tutti a zero.
    """
    nodi, tetraedri = cube_mesh
    top = _base_and_top(nodi)["TOP"]
    interno = int(np.argmin(np.linalg.norm(nodi - nodi.mean(axis=0), axis=1)))
    assert interno not in top.tolist(), "il baricentro cade sulla faccia: banco inadatto"
    indici = np.append(top, interno)
    quote, resoconto = abaqus.ripartisci(900.0, nodi, tetraedri, indici, "C3D4", nome="PROVA")
    assert quote.sum() == pytest.approx(900.0)
    assert resoconto["nodi"] == indici.size
    assert resoconto["nodi_ad_area_nulla"] == 1
    assert quote[-1] == pytest.approx(0.0)


def test_area_tributaria_totale_nulla_solleva_e_nomina_il_carico(cube_mesh):
    """Nessuna faccia di bordo contenuta: la pesatura non ha su cosa pesare.

    Un selettore tutto interno al solido e' il caso reale. Scrivere zero
    ovunque produrrebbe un passo statico che non carica nulla, con un nome
    che promette altro.

    Mutazione che lo uccide: rendere quote nulle invece di sollevare.
    """
    nodi, tetraedri = cube_mesh
    interno = int(np.argmin(np.linalg.norm(nodi - nodi.mean(axis=0), axis=1)))
    with pytest.raises(ValueError, match="INTERNO"):
        abaqus.ripartisci(10.0, nodi, tetraedri, np.array([interno]), "C3D4", nome="INTERNO")


def test_il_carico_in_sommita_ora_e_pesato(cube_mesh, tmp_path):
    """CARICO_TOP passa alla stessa ripartizione dei posizionati.

    Una sola ripartizione nel programma: due carichi che fanno la stessa
    cosa non possono farla in due modi diversi.

    Mutazione che lo uccide: lasciare `per_nodo = risultante / len(nodi)`
    nel ramo del carico in sommita'. I valori distinti del *CLOAD tornano
    a uno solo.
    """
    nodi, tetraedri = cube_mesh
    percorso = tmp_path / "deck.inp"
    abaqus.write_inp(
        percorso, nodi, tetraedri,
        node_sets=_base_and_top(nodi),
        material=MATERIALE,
        carichi=config.CarichiConfig(
            carico_sommita=config.CaricoSommita(risultante=1200.0, nset="TOP")
        ),
    )
    valori = [
        float(riga.split(", ")[2])
        for riga in percorso.read_text(encoding="ascii").splitlines()
        if riga.count(", ") == 2 and riga.split(", ")[1] == "3" and not riga.startswith("*")
    ]
    assert len(set(valori)) > 1, "la ripartizione e' tornata uniforme"
    assert sum(valori) == pytest.approx(-1200.0)
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_abaqus.py -k "ripartizione or area_nulla or area_tributaria_totale or sommita_ora" -q
```

Atteso: FAIL, `AttributeError: ... 'ripartisci'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Dopo `aree_tributarie`:

```python
def ripartisci(
    risultante: float,
    nodes: np.ndarray,
    elements: np.ndarray,
    indici: np.ndarray,
    element_type: str,
    *,
    nome: str,
) -> tuple[np.ndarray, dict[str, object]]:
    """La risultante divisa fra i nodi dell'insieme, in proporzione all'area tributaria.

    La superficie su cui si pesa e' quella che `element_surface` gia'
    costruisce: le facce **di bordo** con **tutti** i nodi nell'insieme. Una
    faccia interna non entra -- il carico finirebbe applicato dentro il
    solido -- e nemmeno una con tre nodi su quattro nell'insieme, perche'
    non e' quella faccia.

    Le quote sono normalizzate sul totale, quindi la loro somma e'
    esattamente `risultante` anche quando qualche nodo dell'insieme non
    tocca alcuna faccia e resta a zero.
    """
    indici = np.asarray(indici, dtype=np.int64)
    superficie = element_surface(elements, indici, element_type)
    aree = aree_tributarie(nodes, elements, superficie, element_type)[indici]
    totale = float(aree.sum())
    if totale <= 0.0:
        raise ValueError(
            f"il carico '{nome}' agisce su {indici.size} nodi che non formano alcuna "
            "faccia di bordo: nessuna area su cui ripartire la risultante. Un "
            "selettore tutto interno al solido produce questo, e un carico applicato "
            "a nulla non e' un carico"
        )
    quote = risultante * aree / totale
    resoconto: dict[str, object] = {
        "nodi": int(indici.size),
        "area_totale": totale,
        "nodi_ad_area_nulla": int((aree == 0.0).sum()),
    }
    return quote, resoconto
```

Poi il ramo `carico_sommita` di `write_inp` (`core/abaqus.py:211-222`), tenendo la guardia esistente:

```python
    if carichi is not None and carichi.carico_sommita is not None:
        sommita = carichi.carico_sommita
        if sommita.nset not in node_sets or len(node_sets[sommita.nset]) == 0:
            raise ValueError(
                f"il carico in sommita nomina l'insieme '{sommita.nset}', che non e' "
                f"fra quelli scritti nel deck ({sorted(node_sets)}) o e' vuoto: il "
                f"solutore leggerebbe un carico applicato a nulla"
            )
        nodi_carico = np.asarray(node_sets[sommita.nset], dtype=np.int64)
        # Pesata per area tributaria dalla Fase 6, uniforme per nodo fino alla
        # Fase 5: e' lo stesso carico dei posizionati e non puo' ripartire in
        # un altro modo. I numeri di CARICO_TOP pubblicati in
        # docs/fase-5-analisi.md sono cambiati per questo, ed e' scritto li'.
        quote, _ = ripartisci(
            sommita.risultante, nodes, elements, nodi_carico, element_type, nome="CARICO_TOP",
        )
        righe_cload = ["*CLOAD"] + [
            f"{int(n) + 1}, 3, {-quota:.9e}"
            for n, quota in zip(nodi_carico, quote, strict=True)
        ]
        lines += passo_statico("CARICO_TOP", [peso] + righe_cload)
```

> A quel punto di `write_inp`, `nodes` ed `elements` sono già gli array numpy convertiti (riga 144-145).

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_abaqus.py tests/test_solve.py -q
```

Atteso: PASS. Se un test esistente asserisce il valore uniforme o un `*CLOAD` a righe identiche, **aggiornalo** scrivendo nel docstring che la ripartizione è cambiata e perché — non allentare l'assert.

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Rimetti `per_nodo = sommita.risultante / len(nodi_carico)` nel ramo del carico in sommità, rilancia `uv run pytest tests/test_abaqus.py -k sommita_ora -q`, verifica FAIL, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-6): ripartizione pesata per area, anche per carico_sommita"
```

---

### Task 7: Le card dei posizionati nel deck

**Files:**
- Modify: `src/meshrec/core/abaqus.py` (firma di `write_inp:57-74`; scrittura degli `*NSET` dopo la riga 167; ramo nuovo dopo `carico_sommita`)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `ripartisci` (Task 6), `CaricoPosizionato` (Task 3).
- Produces: due parametri nuovi di `write_inp` —
  `nset_selettori: dict[str, np.ndarray] | None = None` (nome del selettore → indici risolti) e
  `resoconto_carichi: dict[str, object] | None = None` (riempito in loco: `write_inp` continua a rendere `None`, il resoconto viaggia via `export_model`).

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def _con_posizionati(percorso, cube_mesh, posizionati, resoconto=None):
    """Scrive un deck col set TOP offerto come selettore 'piastra'."""
    nodi, tetraedri = cube_mesh
    sets = _base_and_top(nodi)
    abaqus.write_inp(
        percorso, nodi, tetraedri, node_sets=sets, material=MATERIALE,
        nset_selettori={"piastra": sets["TOP"]},
        carichi=config.CarichiConfig(posizionati=posizionati),
        resoconto_carichi=resoconto,
    )
    return percorso.read_text(encoding="ascii")


def _forze_del_passo(testo: str, passo: str, quanti_nodi: int) -> np.ndarray:
    """Le forze nodali scritte dentro un passo, per nodo e componente."""
    forze = np.zeros((quanti_nodi, 3))
    dentro = False
    for riga in testo.splitlines():
        if riga.startswith(f"** NOME PASSO: {passo}"):
            dentro = True
        elif riga == "*END STEP":
            dentro = False
        elif dentro and not riga.startswith("*") and riga.count(", ") == 2:
            nodo, grado, valore = riga.split(", ")
            forze[int(nodo) - 1, int(grado) - 1] += float(valore)
    return forze


def test_un_posizionato_scrive_il_nset_del_selettore_e_il_passo_del_carico(cube_mesh, tmp_path):
    """Il selettore diventa un *NSET col suo nome, il carico un passo col suo.

    Mutazione che lo uccide: scrivere il *NSET col nome del carico invece
    che con quello del selettore. Due carichi sullo stesso selettore
    scriverebbero due set identici, che e' il nome fabbricato che la
    forma nominata esiste per togliere di mezzo.
    """
    testo = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
    ])
    assert "*NSET, NSET=piastra" in testo
    assert "** NOME PASSO: PRESSA" in testo


def test_le_forze_di_un_posizionato_sommano_alla_risultante(cube_mesh, tmp_path):
    """Il deck realizza la forza dichiarata, componente per componente.

    Mutazione che lo uccide: scrivere la quota su un grado fisso invece
    che sui tre della forza. La somma sulla x resta a zero.
    """
    nodi, _ = cube_mesh
    testo = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(300.0, 0.0, -1200.0)),
    ])
    somma = _forze_del_passo(testo, "PRESSA", len(nodi)).sum(axis=0)
    assert somma == pytest.approx([300.0, 0.0, -1200.0])


def test_ogni_posizionato_e_un_passo_a_se_col_peso_proprio(cube_mesh, tmp_path):
    """Due carichi, due passi, e il peso proprio in entrambi.

    Un passo senza peso proprio descriverebbe una struttura che non pesa:
    e' la stessa ragione per cui SPINTA_ORIZZONTALE e CARICO_TOP lo
    ripetono gia'.

    Mutazione che lo uccide: sommare i due carichi in un passo solo.
    Il conteggio dei passi scende a due.
    """
    testo = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
        config.CaricoPosizionato(nome="TIRO", selettore="piastra", forza=(0.0, 0.0, 800.0)),
    ])
    assert testo.count("** NOME PASSO: ") == 3  # GRAVITA, PRESSA, TIRO
    assert testo.count("ALL_WALL, GRAV, ") == 3


def test_il_resoconto_riporta_la_forza_effettiva(cube_mesh, tmp_path):
    """Il programma dice con quali numeri ha fatto quello che ha fatto.

    Mutazione che lo uccide: riportare la forza dichiarata al posto di
    quella effettiva. Le due coincidono qui, ma la chiave diventa una
    copia dell'ingresso e smette di poter contraddire alcunche': cambia
    l'assert in uno che confronta il resoconto con il deck letto.
    """
    nodi, _ = cube_mesh
    resoconto: dict[str, object] = {}
    testo = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
    ], resoconto=resoconto)
    dal_deck = _forze_del_passo(testo, "PRESSA", len(nodi)).sum(axis=0)
    assert resoconto["PRESSA"]["forza_effettiva"] == pytest.approx(dal_deck)
    assert resoconto["PRESSA"]["nodi"] > 0


def test_un_posizionato_che_cita_un_selettore_non_risolto_solleva(cube_mesh, tmp_path):
    """Il deck non si scrive a meta': se il selettore non e' arrivato, si ferma qui.

    Mutazione che lo uccide: `nset_selettori.get(nome, np.array([]))`, che
    scriverebbe un *NSET vuoto e un carico applicato a nulla.
    """
    nodi, tetraedri = cube_mesh
    with pytest.raises(ValueError, match="piastra"):
        abaqus.write_inp(
            tmp_path / "deck.inp", nodi, tetraedri,
            node_sets=_base_and_top(nodi), material=MATERIALE,
            nset_selettori={},
            carichi=config.CarichiConfig(posizionati=[
                config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1.0)),
            ]),
        )
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_abaqus.py -k posizionat -q
```

Atteso: FAIL, `TypeError: write_inp() got an unexpected keyword argument 'nset_selettori'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Nella firma di `write_inp`, dopo `carichi`:

```python
    nset_selettori: dict[str, np.ndarray] | None = None,
    resoconto_carichi: dict[str, object] | None = None,
```

Dopo il ciclo che scrive gli `*NSET` (`core/abaqus.py:165-167`):

```python
    for name, indices in (nset_selettori or {}).items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(np.asarray(indices, dtype=np.int64))
```

Dopo il ramo `carico_sommita`, prima del ramo `modale`:

```python
    posizionati_risolti: dict[str, object] = {}
    for carico in () if carichi is None else carichi.posizionati:
        if carico.selettore not in (nset_selettori or {}):
            raise ValueError(
                f"il carico '{carico.nome}' cita il selettore '{carico.selettore}', "
                f"che non e' stato risolto: arrivati {sorted(nset_selettori or {})}. "
                "Il deck non si scrive a meta'"
            )
        indici = np.asarray(nset_selettori[carico.selettore], dtype=np.int64)
        if carico.forza is not None:
            modulo = float(np.linalg.norm(carico.forza))
            quote, resoconto = ripartisci(
                modulo, nodes, elements, indici, element_type, nome=carico.nome
            )
            versore = np.asarray(carico.forza, dtype=np.float64) / modulo
            righe_cload = ["*CLOAD"]
            for nodo, quota in zip(indici, quote, strict=True):
                for grado, componente in enumerate(versore, start=1):
                    # Una riga a zero il solutore la legge e la ignora: non
                    # scriverla tiene il deck leggibile e il conteggio onesto.
                    if componente != 0.0:
                        righe_cload.append(f"{int(nodo) + 1}, {grado}, {quota * componente:.9e}")
            lines += passo_statico(carico.nome, [peso] + righe_cload)
            resoconto["forza_dichiarata"] = list(carico.forza)
            resoconto["forza_effettiva"] = np.outer(quote, versore).sum(axis=0).tolist()
            posizionati_risolti[carico.nome] = resoconto
        else:
            # Il momento arriva col Task 8. Fino ad allora si solleva invece di
            # saltare: il validatore garantisce che uno dei due campi ci sia, e
            # un carico che non produce ne' un passo ne' un errore e' esattamente
            # lo scarto silenzioso che questa fase esiste per togliere di mezzo.
            raise NotImplementedError(
                f"il carico '{carico.nome}' dichiara un momento, e il momento come "
                "coppia di forze non e' ancora scritto"
            )
    if resoconto_carichi is not None:
        resoconto_carichi.update(posizionati_risolti)
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_abaqus.py -q
```

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Cambia `f"*NSET, NSET={name}"` in `f"*NSET, NSET={name}_SEL"` nel ciclo nuovo, rilancia
`uv run pytest tests/test_abaqus.py -k nset_del_selettore -q`, verifica FAIL, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-6): un passo statico per carico posizionato"
```

---

### Task 8: Il momento come coppia di forze

**Files:**
- Modify: `src/meshrec/core/abaqus.py` (nuova funzione dopo `ripartisci`; il ramo `else` del ciclo del Task 7)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `ripartisci` (Task 6), `fix_sign` (`core/abaqus.py:237`), `Momento` (Task 3).
- Produces: `coppia_equivalente(momento, nodes, elements, indici, element_type, *, nome) -> tuple[list[str], dict[str, object]]` — le righe `*CLOAD` della coppia e il resoconto con `braccio_dichiarato`, `braccio_effettivo`, `momento`, `nodi_positivi`, `nodi_negativi`, `estensione_disponibile`.

**La costruzione, in ordine.**

1. Si normalizza l'asse `a`.
2. Si proiettano i nodi presi sul piano perpendicolare ad `a`, rispetto al loro baricentro.
3. La **direzione di separazione** `s` è la prima direzione principale di quella proiezione (SVD), col segno reso deterministico da `fix_sign`.
4. Se il `braccio` dichiarato supera l'estensione dei nodi lungo `s`, si **rifiuta** riportando entrambi i numeri.
5. I nodi oltre `+braccio/2` formano il gruppo positivo, quelli oltre `−braccio/2` il negativo. Se un lato resta vuoto, si rifiuta: una coppia con una forza sola è una forza.
6. Ogni gruppo riceve la propria quota ripartita per area (Task 6), e si misura il **braccio effettivo** come distanza fra i due baricentri pesati dalle quote, proiettati su `s`.
7. La forza vale `modulo / braccio_effettivo`. È qui che si calibra: il momento realizzato dal deck è **esattamente** il `modulo` dichiarato, e il `braccio` resta il criterio con cui si sono scelti i due gruppi.
8. La direzione della forza è `a × s`, verso `+` sul gruppo positivo. Con `s ⟂ a` e `|s| = 1` vale `s × (a × s) = a`, quindi il momento risultante è `modulo · a`.

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def test_la_coppia_realizza_il_momento_dichiarato(cube_mesh, tmp_path):
    """Somma delle forze nulla, momento risultante pari al modulo dichiarato.

    La faccia superiore del banco misura 100 x 40 mm: un braccio di 60 mm
    ci sta, e i due gruppi sono non vuoti.

    Mutazione che lo uccide: dare a entrambi i gruppi lo stesso verso.
    La somma delle forze smette di essere nulla e il momento si annulla.
    """
    nodi, _ = cube_mesh
    testo = _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(
            nome="TORSIONE", selettore="piastra",
            momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        ),
    ])
    forze = _forze_del_passo(testo, "TORSIONE", len(nodi))
    # Il peso proprio e' una *DLOAD e non compare fra le forze nodali.
    assert forze.sum(axis=0) == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
    momento = np.cross(nodi - nodi.mean(axis=0), forze).sum(axis=0)
    assert momento[2] == pytest.approx(3000.0, rel=1e-6)
    assert momento[:2] == pytest.approx([0.0, 0.0], abs=1e-6)


def test_un_braccio_piu_largo_dell_estensione_e_rifiutato(cube_mesh, tmp_path):
    """Il programma contraddice il braccio dichiarato invece di misurarlo da se'.

    La faccia superiore si estende 100 mm: un braccio di 400 non lo
    sostiene, e il rifiuto riporta entrambi i numeri.

    Mutazione che lo uccide: misurare il braccio dall'estensione invece
    di verificarlo. Nessuna eccezione, e un numero che nessuno puo'
    smentire.
    """
    with pytest.raises(ValueError, match="400"):
        _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
            config.CaricoPosizionato(
                nome="TORSIONE", selettore="piastra",
                momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=100.0, braccio=400.0),
            ),
        ])


def test_il_resoconto_del_momento_dice_dichiarato_ed_effettivo(cube_mesh, tmp_path):
    """Braccio dichiarato e braccio effettivo sono due numeri diversi, ed entrambi si mostrano.

    I gruppi si formano oltre +-braccio/2, quindi i loro baricentri
    pesati distano piu' del braccio dichiarato: e' lecito, ed e'
    esattamente la cosa che il resoconto esiste per far vedere.

    Mutazione che lo uccide: scrivere `braccio_effettivo` uguale a
    `braccio_dichiarato`. L'assert di disuguaglianza cade.
    """
    resoconto: dict[str, object] = {}
    _con_posizionati(tmp_path / "deck.inp", cube_mesh, [
        config.CaricoPosizionato(
            nome="TORSIONE", selettore="piastra",
            momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        ),
    ], resoconto=resoconto)
    voce = resoconto["TORSIONE"]
    assert voce["braccio_dichiarato"] == pytest.approx(60.0)
    assert voce["braccio_effettivo"] >= 60.0
    assert voce["momento"] == pytest.approx(3000.0)
    assert voce["nodi_positivi"] > 0 and voce["nodi_negativi"] > 0
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_abaqus.py -k "coppia or braccio or resoconto_del_momento" -q
```

Atteso: FAIL — il ramo `momento` non esiste, il carico viene ignorato e il passo `TORSIONE` non compare.

- [ ] **Step 3: Scrivi l'implementazione minima**

Dopo `ripartisci`:

```python
def coppia_equivalente(
    momento: Momento,
    nodes: np.ndarray,
    elements: np.ndarray,
    indici: np.ndarray,
    element_type: str,
    *,
    nome: str,
) -> tuple[list[str], dict[str, object]]:
    """Le righe *CLOAD di una coppia di forze staticamente equivalente al momento.

    Non un `*CLOAD` sui gradi 4-6: su un C3D4 `ccx` 2.22 lo scarta senza un
    warning e con spostamento esattamente zero, e la guardia di
    `core/solve.py:438` non ha nulla da intercettare.

    Il braccio lo dichiara l'operatore e questa funzione lo contraddice se i
    nodi presi non lo sostengono. La via opposta -- misurarlo sull'estensione
    reale -- non chiede nulla ma decide da se', e nessuno la puo' smentire.

    Il momento realizzato e' **esattamente** quello dichiarato: la forza si
    calibra sul braccio effettivo fra i due baricentri pesati, che i nodi
    offrono davvero. Il `braccio` dichiarato resta il criterio con cui i due
    gruppi sono stati scelti, e il resoconto mostra entrambi i numeri.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    indici = np.asarray(indici, dtype=np.int64)
    asse = np.asarray(momento.asse, dtype=np.float64)
    norma = float(np.linalg.norm(asse))
    if norma == 0.0:
        raise ValueError(f"il momento '{nome}' ha asse di modulo nullo: non e' una direzione")
    asse = asse / norma

    presi = punti[indici]
    baricentro = presi.mean(axis=0)
    relativi = presi - baricentro
    piano = relativi - np.outer(relativi @ asse, asse)

    # Direzione di separazione: quella di massima estensione nel piano
    # perpendicolare all'asse, cioe' dove i nodi offrono il braccio piu'
    # lungo. `fix_sign` la rende deterministica, altrimenti il segno
    # arbitrario della SVD scriverebbe due deck diversi dallo stesso dato.
    _, _, versori = np.linalg.svd(piano, full_matrices=False)
    separazione = fix_sign(versori[0])
    proiezione = piano @ separazione
    estensione = float(proiezione.max() - proiezione.min())
    if momento.braccio > estensione:
        raise ValueError(
            f"il momento '{nome}' dichiara un braccio di {momento.braccio:g} mm, e i "
            f"{indici.size} nodi presi si estendono {estensione:.3f} mm nella "
            "direzione della coppia: i nodi non lo sostengono. Accorcia il braccio "
            "o allarga il selettore"
        )

    meta = momento.braccio / 2.0
    positivi = indici[proiezione >= meta]
    negativi = indici[proiezione <= -meta]
    if positivi.size == 0 or negativi.size == 0:
        raise ValueError(
            f"il momento '{nome}' con braccio {momento.braccio:g} mm lascia un lato "
            f"senza nodi ({positivi.size} da una parte, {negativi.size} dall'altra): "
            "una coppia con una sola forza e' una forza"
        )

    quote_per_gruppo = []
    bracci = []
    for gruppo in (positivi, negativi):
        quote, _ = ripartisci(1.0, nodes, elements, gruppo, element_type, nome=nome)
        quote_per_gruppo.append(quote)
        # Baricentro del gruppo pesato dalle quote, proiettato sulla direzione
        # di separazione. `ripartisci(1.0, ...)` rende quote che sommano a 1,
        # quindi il prodotto scalare e' gia' la media pesata.
        bracci.append(float(((punti[gruppo] - baricentro) @ separazione) @ quote))

    braccio_effettivo = bracci[0] - bracci[1]
    forza = float(momento.modulo) / braccio_effettivo
    direzione = np.cross(asse, separazione)

    righe = ["*CLOAD"]
    for gruppo, quote, segno in (
        (positivi, quote_per_gruppo[0], 1.0), (negativi, quote_per_gruppo[1], -1.0)
    ):
        for nodo, quota in zip(gruppo, quote, strict=True):
            for grado, componente in enumerate(direzione, start=1):
                if componente != 0.0:
                    valore = segno * forza * quota * componente
                    righe.append(f"{int(nodo) + 1}, {grado}, {valore:.9e}")

    resoconto: dict[str, object] = {
        "nodi": int(indici.size),
        "braccio_dichiarato": float(momento.braccio),
        "braccio_effettivo": braccio_effettivo,
        "momento": float(momento.modulo),
        "forza_di_ciascun_lato": forza,
        "nodi_positivi": int(positivi.size),
        "nodi_negativi": int(negativi.size),
        "estensione_disponibile": estensione,
    }
    return righe, resoconto
```

Nel ciclo del Task 7, **sostituisci** il ramo `else` che solleva `NotImplementedError`:

```python
        else:
            righe_cload, resoconto = coppia_equivalente(
                carico.momento, nodes, elements, indici, element_type, nome=carico.nome
            )
            lines += passo_statico(carico.nome, [peso] + righe_cload)
            posizionati_risolti[carico.nome] = resoconto
```

Aggiungi `Momento` all'import da `meshrec.core.config` in testa a `core/abaqus.py`.

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_abaqus.py -q
```

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Cambia `((positivi, ..., 1.0), (negativi, ..., -1.0))` in modo che entrambi abbiano segno `1.0`, rilancia
`uv run pytest tests/test_abaqus.py -k coppia_realizza -q`, verifica FAIL sulla somma delle forze, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-6): momento come coppia di forze, braccio dichiarato e verificato"
```

---

### Task 9: `export_model` risolve i selettori e scrive il resoconto

**Files:**
- Modify: `src/meshrec/core/abaqus.py:810-960` (`export_model`), `src/meshrec/core/pipeline.py:439-448`
- Test: `tests/test_abaqus.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `risolvi_tutti` (Task 4), `write_inp` con `nset_selettori` e `resoconto_carichi` (Task 7, 8).
- Produces: parametro nuovo `export_model(..., selettori: dict[str, Selettore] | None = None)`; due chiavi nuove nel dizionario reso — `"selettori"` e `"carichi_posizionati"` — e i nomi dei posizionati dentro `"casi_di_carico"`, fra `CARICO_TOP` e `MODALE`.

- [ ] **Step 1: Scrivi i test che falliscono**

```python
def test_il_resoconto_dei_selettori_si_scrive_sempre(cube_mesh, tmp_path):
    """Fra 1 e tutti i nodi nessuna soglia puo' giudicare: si mostra.

    Mutazione che lo uccide: scrivere il resoconto solo quando un
    selettore prende pochi nodi. La chiave sparisce sul caso normale,
    che e' proprio quello in cui serve guardarla.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, config.TetConfig(),
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
        )},
    )
    voce = metriche["selettori"]["piastra"]
    assert voce["tipo"] == "box"
    assert 0 < voce["nodi"] < len(nodi)
    assert len(voce["bbox"]) == 2


def test_i_posizionati_entrano_nei_casi_di_carico(cube_mesh, tmp_path):
    """Il nome del passo e' l'indirizzo del risultato: deve comparire nell'elenco.

    Mutazione che lo uccide: lasciare `casi_di_carico` alla lista fissa
    dei tre della Fase 5. `solve.risolvi` cercherebbe le chiavi di
    point_data per nomi che l'elenco non dichiara.
    """
    nodi, tetraedri = cube_mesh
    alto = float(nodi[:, 2].max())
    metriche = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI, config.TetConfig(),
        selettori={"piastra": config.SelettoreBox(
            tipo="box", min=(-1e9, -1e9, alto - 1.0), max=(1e9, 1e9, 1e9)
        )},
        carichi=config.CarichiConfig(posizionati=[
            config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1200.0)),
        ]),
    )
    assert "PRESSA" in metriche["casi_di_carico"]
    assert metriche["casi_di_carico"].index("PRESSA") < len(metriche["casi_di_carico"])
    assert metriche["carichi_posizionati"]["PRESSA"]["nodi"] > 0
    assert metriche["carichi_posizionati"]["PRESSA"]["forza_effettiva"][2] == pytest.approx(-1200.0)
```

> **Attenzione al sistema di riferimento.** `export_model` allinea i nodi prima di risolvere i selettori, quindi le coordinate del test non sono quelle di `cube_mesh` ma quelle allineate. La box del test è deliberatamente scritta con estremi larghissimi su x e y proprio per non dipendere dall'allineamento: **non stringerla**. Se serve una selezione più precisa, leggi `metriche["extent"]` e costruisci la box da lì.

E in `tests/test_pipeline.py`, il test che la pipeline passa il blocco:

```python
def test_lo_step_11_passa_i_selettori(monkeypatch, tmp_path):
    """Il percorso as-built e' quello della tesi: se non passa i selettori, non esistono.

    Mutazione che lo uccide: togliere `selettori=cfg.selettori` dalla
    chiamata di core/pipeline.py:439-448. La cattura non vede la chiave e
    l'assert cade.
    """
    visti: dict[str, object] = {}
    originale = abaqus.export_model

    def spia(*args, **kwargs):
        visti.update(kwargs)
        return originale(*args, **kwargs)

    monkeypatch.setattr(abaqus, "export_model", spia)
    # Esegui la pipeline fino allo step 11 come gia' fanno gli altri test di
    # questo file, con una configurazione che dichiara un selettore.
    assert visti.get("selettori")
```

> Guarda come `tests/test_pipeline.py` costruisce già una corsa breve e **riusa quel banco**: non inventarne uno nuovo. Se la pipeline importa `export_model` per nome invece che via modulo, il `monkeypatch` va messo dove il nome è risolto.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_abaqus.py -k "resoconto_dei_selettori or casi_di_carico" -q
```

Atteso: FAIL, `TypeError: export_model() got an unexpected keyword argument 'selettori'`.

- [ ] **Step 3: Scrivi l'implementazione minima**

Nella firma di `export_model`, dopo `carichi`:

```python
    selettori: dict[str, Selettore] | None = None,
```

Dopo `node_sets = build_node_sets(aligned, tolerance)` (`core/abaqus.py:887`):

```python
    # Risolti sui nodi **allineati**: e' il sistema di riferimento del deck e
    # di wall_model.vtu. L'estensione in quel sistema esce qui sotto in
    # "extent", e la bbox dei nodi presi in "selettori", perche' l'operatore
    # possa collocare un selettore senza indovinare.
    nset_selettori = selezione.risolvi_tutti(selettori or {}, aligned, elements, node_sets)
    resoconto_carichi: dict[str, object] = {}
```

Aggiungi i tre argomenti alla chiamata di `write_inp`:

```python
        carichi=carichi,
        nset_selettori=nset_selettori,
        resoconto_carichi=resoconto_carichi,
```

Nel dizionario reso, dopo `"node_sets"`:

```python
        "selettori": {
            nome: {
                "tipo": (selettori or {})[nome].tipo,
                "nodi": int(indici.size),
                "bbox": [
                    aligned[indici].min(axis=0).tolist(),
                    aligned[indici].max(axis=0).tolist(),
                ],
            }
            for nome, indici in nset_selettori.items()
        },
        "carichi_posizionati": resoconto_carichi,
```

e sostituisci `"casi_di_carico"`:

```python
        "casi_di_carico": [nome for nome in (
            cfg.step_name,
            None if carichi is None or carichi.spinta is None else "SPINTA_ORIZZONTALE",
            None if carichi is None or carichi.carico_sommita is None else "CARICO_TOP",
            *(() if carichi is None else tuple(c.nome for c in carichi.posizionati)),
            None if carichi is None or carichi.modale is None else "MODALE",
        ) if nome is not None],
```

In testa a `core/abaqus.py`, `from meshrec.core import selezione`, e `Selettore` fra i nomi importati da `meshrec.core.config`.

> **Ordine degli import.** `core/selezione.py` importa da `core/config.py`, e `core/abaqus.py` importa da entrambi: nessun ciclo. Se ne compare uno, il colpevole è un import di `abaqus` dentro `selezione`, che non deve esistere.

In `core/pipeline.py:439-448`, aggiungi alla chiamata:

```python
            carichi=cfg.carichi,
            selettori=cfg.selettori,
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests -q --ignore=tests/feasibility
```

Atteso: PASS, col conteggio **sopra la baseline corrente** (vedi la tabella nei vincoli globali: 748 dopo il Task 2) — i test nuovi si aggiungono, nessuno sparisce.

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Togli `selettori=cfg.selettori` da `core/pipeline.py`, rilancia
`uv run pytest tests/test_pipeline.py -k step_11_passa -q`, verifica FAIL, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/core/pipeline.py meshrec/tests/test_abaqus.py meshrec/tests/test_pipeline.py
git commit -m "feat(fase-6): export_model risolve i selettori e riporta con quali numeri"
```

---

### Task 10: Il deck con un posizionato dato a `ccx` vero

**Files:**
- Modify: `tests/feasibility/test_calculix.py`

**Perché esiste.** Che le card siano giuste lo dice il solutore, non una lettura del testo: un controllo interno partirebbe dalla stessa trascrizione che vorrebbe verificare. È la ragione per cui `tests/feasibility/test_calculix.py:92` esiste già per i tre casi della Fase 5, e vale identica per i due nuovi.

E c'è una ragione in più, specifica: un momento su un C3D4 `ccx` lo **scarta in silenzio**. Un test che guarda solo il deck non distingue una card che il solutore onora da una che getta via.

**Interfaces:**
- Consumes: `write_inp` con `nset_selettori` (Task 7, 8); `synth.box_mesh`, `volume.tetrahedralize`, `abaqus`, `Material` — già importati nel file.
- Produces: nessuna interfaccia. Due test nuovi, marcati `feasibility` dal `pytestmark` del modulo (`tests/feasibility/test_calculix.py:25`).

- [ ] **Step 1: Scrivi i test che falliscono**

In coda a `tests/feasibility/test_calculix.py`:

```python
def test_un_posizionato_gira_a_zero_avvisi_e_sposta_qualcosa(tmp_path):
    """Il deck con un carico posizionato lo onora il solutore, non una lettura del testo.

    Non basta "zero avvisi": un momento su un C3D4 esce a zero avvisi e
    spostamento esattamente nullo. L'oracolo e' che qualcosa si sia
    mosso.

    Mutazione che lo uccide: scrivere le righe *CLOAD del posizionato con
    un numero di nodo base zero invece che base uno. `ccx` legge nodi che
    non esistono e l'esecuzione fallisce.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    material = Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
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
        nset_selettori={"piastra": node_sets["TOP"]},
        carichi=CarichiConfig(posizionati=[
            CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1000.0)),
        ]),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    spostamenti = read_dat_displacements(tmp_path / "model.dat")
    assert spostamenti, "il .dat non porta spostamenti: il carico non e' arrivato"
    assert max(abs(u[2]) for u in spostamenti.values()) > 0.0


def test_un_momento_come_coppia_non_e_scartato_in_silenzio(tmp_path):
    """Il momento realizzato come coppia sposta davvero, a differenza della card muta.

    Misurato: un `*CLOAD` sul grado 4 di un C3D4 esce a zero avvisi e
    spostamento `0.000000E+00`. Questo test afferma il contrario sulla
    coppia, ed e' l'unico modo di distinguere le due cose.

    Mutazione che lo uccide: scrivere il momento come `*CLOAD` sui gradi
    4-6 invece che come coppia. `ccx` esce a zero, senza warning, e gli
    spostamenti restano tutti nulli.
    """
    executable = shutil.which("ccx")
    if executable is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")

    material = Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
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
        nset_selettori={"piastra": node_sets["TOP"]},
        carichi=CarichiConfig(posizionati=[
            CaricoPosizionato(
                nome="TORSIONE", selettore="piastra",
                momento=Momento(asse=(0.0, 0.0, 1.0), modulo=50_000.0, braccio=60.0),
            ),
        ]),
    )

    processo = subprocess.run(
        [executable, "-i", "model"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    uscita = processo.stdout
    assert "Job finished" in uscita, uscita[-2000:] + processo.stderr[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita

    spostamenti = read_dat_displacements(tmp_path / "model.dat")
    assert spostamenti, "il .dat non porta spostamenti"
    orizzontali = max(max(abs(u[0]), abs(u[1])) for u in spostamenti.values())
    assert orizzontali > 0.0, "la coppia non ha mosso nulla: e' muta come la card sul grado 4"
```

> Aggiungi agli import del file `CaricoPosizionato` e `Momento` da `meshrec.core.config`, e `read_dat_displacements` da `ccx_utils` se non è già importato — leggi la testa del file prima di aggiungere.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/feasibility/test_calculix.py -q -m feasibility -k "posizionato or momento_come_coppia"
```

Atteso: FAIL. Se invece esce `skipped`, `ccx` non è nel PATH: **non è un successo**. Rendilo disponibile e rilancia — questo task senza solutore non verifica nulla.

- [ ] **Step 3: Correggi ciò che il solutore rifiuta**

A differenza degli altri task, qui il codice è già scritto (Task 7, 8): questo passo esiste perché il solutore può rifiutare ciò che i test interni accettavano. Se `ccx` emette warning o errori, la correzione va in `core/abaqus.py`, e l'errore vero di `ccx` va **citato nel messaggio di commit**, non parafrasato.

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/feasibility -q -m feasibility
```

Atteso: PASS, e il conteggio **sopra** 11 passed / 1 skipped.

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Nel ramo dei posizionati di `write_inp`, scrivi `f"{int(nodo)}, ..."` invece di `f"{int(nodo) + 1}, ..."`, rilancia
`uv run pytest tests/feasibility/test_calculix.py -q -m feasibility -k posizionato`, verifica FAIL, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/tests/feasibility/test_calculix.py
git commit -m "test(fase-6): il deck coi posizionati gira su ccx vero"
```

---

### Task 11: `selettori` nell'impronta e nell'invalidazione dello step 11

**Files:**
- Modify: `src/meshrec/core/steps.py:65` e il commento di `src/meshrec/core/sweep.py:38-63`
- Test: `tests/test_sweep.py`, `tests/test_steps.py`

**Interfaces:**
- Consumes: `STEP_BLOCKS` (`core/steps.py:55-68`), `BLOCCHI_VUOTI_FUORI_IMPRONTA` (`core/sweep.py:64`), `fingerprint` (`core/sweep.py:67`).
- Produces: nessuna interfaccia nuova. `STEP_BLOCKS[11]` diventa `("tet", "analysis", "carichi", "selettori")`.

> **Metà di questo task è già fatta, e non va rifatta.** Il **Task 1** ha già
> scritto `BLOCCHI_VUOTI_FUORI_IMPRONTA = ("carichi", "selettori")` in
> `core/sweep.py:64`, perché senza quella riga l'aggiunta del campo
> `selettori` faceva fallire subito `test_l_impronta_di_una_corsa_registrata_non_cambia`
> e la suite non poteva restare verde. **Apri `core/sweep.py:64` e verificalo
> prima di scrivere**: se `"selettori"` c'è già, non toccare la riga. Restano
> tuoi `STEP_BLOCKS[11]`, il commento, e **tutti e tre** i test qui sotto —
> compreso quello sull'impronta, che finora nessuno ha scritto: la riga esiste
> ma la prova che serva davvero no.

**Indipendente dagli altri task**: basta il Task 1.

- [ ] **Step 1: Scrivi i test che falliscono**

In `tests/test_sweep.py`:

```python
def test_due_selettori_diversi_danno_impronte_diverse():
    """Senza questo, due candidati scrivono nella stessa cartella e il secondo vince.

    La cartella di un candidato e' `fingerprint(cfg)[:12]`
    (core/sweep.py:677), e lo sweep arriva a --to-step 12: il deck
    11_export e' artefatto richiesto di ogni candidato.

    Mutazione che lo uccide: togliere "selettori" da
    BLOCCHI_VUOTI_FUORI_IMPRONTA (core/sweep.py:64) **e** dalla lista dei
    blocchi che l'impronta considera -- cioe' rimettere il blocco fuori
    da entrambe. Le due impronte tornano uguali.
    """
    base = crea_config(input=config.InputConfig(path="nuvola.ply"))
    uno = base.model_copy(update={"selettori": {
        "piastra": config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=5.0)
    }})
    altro = base.model_copy(update={"selettori": {
        "piastra": config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=9.0)
    }})
    assert sweep.fingerprint(uno) != sweep.fingerprint(altro)


def test_il_blocco_selettori_vuoto_non_cambia_l_impronta():
    """Le righe dei registri non hanno il blocco: la loro provenienza non deve muoversi.

    E' la stessa regola gia' applicata a `carichi`, per la stessa ragione.

    Mutazione che lo uccide: aggiungere "selettori" all'impronta senza la
    regola dell'omissione. L'impronta cambia su tutte le righe registrate.
    """
    base = crea_config(input=config.InputConfig(path="nuvola.ply"))
    vuoto = base.model_copy(update={"selettori": {}})
    assert sweep.fingerprint(base) == sweep.fingerprint(vuoto)
```

In `tests/test_steps.py`:

```python
def test_cambiare_un_selettore_invalida_lo_step_11():
    """Un selettore cambiato e uno step 11 non rifatto = deck vecchio, in silenzio.

    Mutazione che lo uccide: non aggiungere "selettori" a STEP_BLOCKS[11].
    Le due impronte di step restano uguali e la corsa riusa il deck.
    """
    base = crea_config(input=config.InputConfig(path="nuvola.ply"))
    uno = base.model_copy(update={"selettori": {
        "piastra": config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=5.0)
    }})
    altro = base.model_copy(update={"selettori": {
        "piastra": config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=9.0)
    }})
    assert steps.step_fingerprints(uno)[11] != steps.step_fingerprints(altro)[11]
```

> Adatta gli import e l'helper `crea_config` a come i due file già li usano.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

```
uv run pytest tests/test_sweep.py tests/test_steps.py -k selettor -q
```

Atteso: FAIL — le impronte tornano uguali.

- [ ] **Step 3: Scrivi l'implementazione minima**

`core/steps.py:65`:

```python
    11: ("tet", "analysis", "carichi", "selettori"),
```

`core/sweep.py:64` **è già così** dal Task 1 — verificalo e non riscriverlo:

```python
BLOCCHI_VUOTI_FUORI_IMPRONTA: tuple[str, ...] = ("carichi", "selettori")
```

Allunga invece il commento sopra (`core/sweep.py:38-63`), che il Task 1 non ha toccato:

```python
# `selettori` segue `carichi` e per la stessa ragione: e' letto dallo step 11,
# cambia il deck, e due candidati con selettori diversi sono esperimenti
# diversi. La regola dell'omissione quando vuoto tiene ferma la provenienza
# delle righe gia' registrate, che il blocco non ce l'hanno.
```

> `fingerprint` (`core/sweep.py:82-84`) fa già `if not any((payload.get(blocco) or {}).values())`: su un `selettori` vuoto (`{}`) `any` è falso e il blocco esce. **Nessuna modifica alla funzione.**

- [ ] **Step 4: Esegui i test e verifica che passino**

```
uv run pytest tests/test_sweep.py tests/test_steps.py tests/test_config.py -q
```

Atteso: PASS, incluso il test già esistente che verifica l'impronta immutata sulle righe dei registri (dal commit `911f15f`). Se quel test cambia risultato, la regola dell'omissione non sta funzionando: **fermati e capisci perché**, non aggiornare il valore atteso.

- [ ] **Step 5: Applica la mutazione e verifica che il test muoia**

Rimetti `11: ("tet", "analysis", "carichi")` in `core/steps.py`, rilancia
`uv run pytest tests/test_steps.py -k selettore_invalida -q`, verifica FAIL, poi ripristina.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/core/steps.py meshrec/src/meshrec/core/sweep.py meshrec/tests/test_sweep.py meshrec/tests/test_steps.py
git commit -m "fix(steps): un selettore cambiato invalida lo step 11"
```

---

### Task 12: Rimisurare e ripubblicare i numeri di `CARICO_TOP`

**Files:**
- Modify: `meshrec/docs/fase-5-analisi.md:305`, `:438`, `:578`
- Modify (se ha `assert` su quei valori): `meshrec/docs/fase-5-cantiere/misura-deficit.py`
- Read-only: `runs/lab_telaio_v2/`

**Nessun codice di produzione.** È il debito che il Task 6 ha contratto: la ripartizione è cambiata, e i numeri pubblicati della Fase 5 non descrivono più il programma.

- [ ] **Step 1: Metti al sicuro i numeri di oggi**

Da `meshrec/`:

```
python3 -c "import json; d=json.load(open('runs/lab_telaio_v2/metrics.json')); print(json.dumps(d['13_solve'], indent=1)[:3000])"
```

Annota i valori attuali di `CARICO_TOP`: sono il termine di paragone del prima/dopo. Quelli già pubblicati sono picco **0,98 MPa** e un `*CLOAD` di **3.036 righe da −0,395257 N**, che chiude su `runs/lab_telaio_v2/config.yaml:77` (`risultante: 1200.0`, `nset: TOP`) e su `metrics.json`, campo `11_export.node_sets.TOP` = **3036**.

- [ ] **Step 2: Rilancia la corsa in una cartella nuova**

**Non sovrascrivere `runs/lab_telaio_v2`.** Leggi il nome della configurazione da `runs/lab_telaio_v2/config.yaml` e riusa quella: la corsa dev'essere la stessa, cambiata solo la ripartizione. Da `meshrec/`:

```
uv run meshrec run --config <la configurazione di lab_telaio> --out-dir runs/lab_telaio_v3_pesata
```

- [ ] **Step 3: Leggi i numeri nuovi**

```
python3 -c "import json; d=json.load(open('runs/lab_telaio_v3_pesata/metrics.json')); print(json.dumps(d['13_solve'], indent=1)[:3000])"
```

- [ ] **Step 4: Aggiorna le tre righe pubblicate**

In `meshrec/docs/fase-5-analisi.md`, sostituisci i valori a `:305` (picco `CARICO_TOP`), `:438` (la riga della tabella) e `:578` (la forma del `*CLOAD`). Ogni numero cita la corsa da cui viene: `runs/lab_telaio_v3_pesata`, non più `v2`.

Aggiungi una nota, non un rimpiazzo silenzioso:

```markdown
> **Aggiornato con la Fase 6.** I numeri di `CARICO_TOP` sono cambiati perche'
> la ripartizione di una risultante e' passata da uniforme per nodo ad **area
> tributaria**: la forma precedente concentrava il carico dove i nodi sono piu'
> fitti, che e' una proprieta' del maglio e non della struttura. La modifica non
> riguarda solo i carichi nuovi -- un programma non puo' ripartire in due modi
> diversi due carichi che fanno la stessa cosa. `GRAVITA`, `SPINTA_ORIZZONTALE`
> e `MODALE` non sono toccati.
> I valori precedenti, dalla corsa `runs/lab_telaio_v2`: picco 0,98 MPa,
> `*CLOAD` di 3.036 righe da −0,395257 N ciascuna.
```

- [ ] **Step 5: Verifica che lo script della Fase 5 regga ancora**

```
uv run python docs/fase-5-cantiere/misura-deficit.py
```

Se ha `assert` sui valori di `CARICO_TOP`, falliranno: **aggiornali ai nuovi, non toglierli.** Uno script che non afferma più nulla non è uno script.

- [ ] **Step 6: Commit**

```bash
git add meshrec/docs/fase-5-analisi.md meshrec/docs/fase-5-cantiere/misura-deficit.py
git commit -m "docs(fase-5): CARICO_TOP rimisurato con la ripartizione pesata"
```

---

### Task 13: Il documento di esito della Fase 6

**Files:**
- Create: `meshrec/docs/fase-6-carichi.md`
- Create: `meshrec/docs/fase-6-cantiere/misura-carichi.py`

**Modello:** `meshrec/docs/fase-5-analisi.md` e `meshrec/docs/fase-5-cantiere/misura-deficit.py`. Leggili prima di scrivere: la forma è già decisa, e questo documento la segue.

- [ ] **Step 1: Prepara la corsa dimostrativa**

Una configurazione che dichiara almeno un selettore per ciascuna delle quattro forme, un carico di forza e un momento. Eseguila in una cartella nuova e conserva `metrics.json`.

- [ ] **Step 2: Raccogli gli errori veri degli ingressi degeneri**

Per ogni riga delle due tabelle del § 3.2 della spec, provoca la condizione e **copia il messaggio che esce**. Il documento riporta l'errore vero, non una parafrasi: la parafrasi è la cosa che smette di corrispondere al programma senza che nessuno se ne accorga.

- [ ] **Step 3: Scrivi il documento**

Sezioni obbligate:

1. **Il problema**: as-built senza topologia, i sei `*NSET` ricalcolati a ogni esportazione (`core/abaqus.py:741`).
2. **Il selettore**: le quattro forme, con quanti nodi ciascuna ha preso nella corsa dimostrativa e la bbox reale.
3. **La validazione**: la tabella dei due gruppi, con gli errori veri dello Step 2.
4. **La ripartizione**: perché per area, e il confronto misurato prima/dopo su `CARICO_TOP` (Task 12).
5. **Il momento**: la coppia, il braccio dichiarato, il braccio effettivo, il rifiuto quando i nodi non lo sostengono, e la prova su `ccx` vero (Task 10) che la coppia sposta mentre la card sul grado 4 non lo fa.
6. **Il resoconto**: cosa `metrics["11_export"]` contiene ora, con un estratto reale.
7. **Cosa la Fase 6 dichiara di non fare**: il § 2.3 della spec, per intero e alla lettera — comprese le due righe che il piano ha aggiunto (nessuna combinazione di due posizionati in un passo solo).
8. **La coda**: i cinque cantieri fuori e il loro ordine di ritorno.

Ogni numero porta **il file e il campo** da cui viene.

- [ ] **Step 4: Scrivi lo script degli `assert`**

`meshrec/docs/fase-6-cantiere/misura-carichi.py`, sul modello di `misura-deficit.py`: legge gli artefatti della corsa dimostrativa e afferma con `assert` ogni valore che il documento pubblica. Un numero nel documento che lo script non afferma è un numero che nessuno ricontrollerà.

- [ ] **Step 5: Esegui lo script e le due suite**

```
uv run python docs/fase-6-cantiere/misura-carichi.py
```

Atteso: nessun `AssertionError`, uscita 0. Poi, comandi separati:

```
uv run pytest tests -q --ignore=tests/feasibility
```

```
uv run pytest tests -q -m feasibility
```

Atteso: nessuna regressione rispetto alla baseline corrente (tabella nei vincoli globali) né rispetto a 11 passed / 1 skipped in feasibility, e i test nuovi in più.

- [ ] **Step 6: Commit**

```bash
git add meshrec/docs/fase-6-carichi.md meshrec/docs/fase-6-cantiere/misura-carichi.py
git commit -m "docs(fase-6): chiude la fase con i numeri della corsa dimostrativa"
```

---

## Chiusura

Dopo il Task 13, apri la PR da `feat/impronta-carichi` verso `main` e dispaccia in **parallelo** i quattro revisori di sola lettura — `security-reviewer`, `code-reviewer`, `test-writer`, `craft-reviewer` — come vuole `CLAUDE.md`. Ogni prompt di dispatch nomina `caveman`, `ponytail` e `skill-gate`, cita almeno un `file.ext:riga` letto nella sessione, e porta la propria sezione `## Ingressi degeneri`. Merge solo con review pulita, poi `superpowers:finishing-a-development-branch`.

Chiudi su GitHub le issue [#9](https://github.com/maeurong/Tesi/issues/9) e [#11](https://github.com/maeurong/Tesi/issues/11), che questa spec e questo piano risolvono. [#10](https://github.com/maeurong/Tesi/issues/10) e [#12](https://github.com/maeurong/Tesi/issues/12) restano aperte: sono i primi due cantieri della coda.
