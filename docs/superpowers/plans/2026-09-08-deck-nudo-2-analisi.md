# Deck nudo, PR 2 — via analisi e materiali, entra `export` (assorbe la PR 4, interfaccia): piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il deck è nudo per costruzione — `*HEADING`, `*NODE`, `*ELEMENT`, i sei `*NSET` delle facce, un `*ELSET` per regione — perché materiali, sezioni, vincolo e passo di gravità escono da configurazione, deck, catalogo e riga di comando; l'unico parametro superstite, la tolleranza degli insiemi di facce, vive nel blocco nuovo `export`; un yaml vecchio viene rifiutato con un messaggio che nomina il blocco tolto.

**Architecture:** stesso ordine della PR 1, dall'alto verso il basso e suite verde a ogni commit. Prima `write_inp` smette di scrivere sezioni, materiali, `*BOUNDARY` e `*STEP` e il patch test si porta da sé le card che gli servono; poi `export_model` perde `AnalysisConfig` e prende `ExportConfig`, la metrica `mass` cade, le `regioni` arrivano come soli indici; poi la configurazione: via `analysis`, `Material`, `MaterialeDichiarato`, `NOMI_PASSO_RISERVATI`, il catalogo `materiali.py`, `meshrec init`; entra `ExportConfig` con `set_tolerance_factor` e il validatore `BLOCCHI_RIMOSSI`; `STEP_BLOCKS[11] = ("tet", "export", "regioni")`; infine server (rotta `/api/materiali`, `_FUORI_DAL_PANNELLO`), file di caso e prosa. Il pannello del materiale in `app.js` esce **qui**, prima della configurazione (Task 5, decisione dell'architect: le sue prove chiudono sul server vero e sarebbero rosse dopo il Task 3): la PR 4 è assorbita e non si apre.

**Tech Stack:** Python 3.12, pydantic 2, numpy, pytest; `node` e `ccx` per la suite onesta.

**Spec:** `docs/superpowers/specs/2026-09-07-deck-nudo-e-step-dal-prior-design.md`, sezioni «Il deck nudo», «La configurazione», «La prosa», «Sequenza» punto 2. ADR: `docs/adr/2026-09-07-deck-nudo-via-analisi-carichi-selettori.md` (decisione, approcci, appendice «Errori» e «File»).

## Global Constraints

- Comandi dalla cartella `meshrec/` con `uv run`; percorsi assoluti; `git -C /Users/mario/GitHub/Tesi`.
- **Il verde che mente** (`AGENTS.md`): suite onesta `uv run pytest -m "" -q` con `node` e `ccx`; baseline su `main` 8004950: **1238 passati, 1 saltato**. Il patch test in `tests/validazione/` deve girare con `ccx` a ogni commit.
- Un esito discreto che dipende dalla piattaforma è un difetto; le grandezze continue si confrontano con tolleranza.
- Ogni numero mostrato ha un controllo che lo contraddice: `base_coverage` resta con `UnconstrainedModelWarning`, misurata su `BASE` fisso.
- Messaggi di commit in italiano, Conventional Commits.
- Unità: mm, N, MPa, t, s.
- Non toccare: `core/attribuzione.py` (resta, con le regioni come soli indici), `regioni.<nome>.membratura`, il validatore delle regioni contro `ALL_WALL` (`config.py:942-961`), `*TIE`/`*SURFACE` del modello parametrico, `hexa.py`, `genera_modello` oltre alla chiamata a `export_model` (la PR 3 aggiunge righe subito dopo: non riordinare quella funzione).
- Una **prova sposta** questa PR: `test_i_vecchi_kwarg_non_hanno_piu_un_ramo_di_compatibilita` da `tests/test_condizioni_imposte.py` a `tests/test_abaqus.py` (ruling della PR 1).
- Il messaggio del rifiuto nominato porta: il nome del blocco, la data `08/09/2026`, la PR (`#190` per `carichi`/`selettori`, questa PR per `analysis`), e la frase «`set_tolerance_factor` sta ora in `export`».

## Annotazione architect (08/09/2026, su `main` 8004950, ogni riga letta)

**Ordine di esecuzione: 0 → 1a → 1b → 2 → 5 → 3a → 3b → 4 → 6.** Tutto sequenziale: ogni task tocca un file del precedente (`abaqus.py` fra 1 e 2; `test_app_js.py` fra 5 e 3; `config.py` fra 2 e 3). Nessun gruppo parallelo dentro questa PR. Il Task 5 **non è facoltativo** e va **prima** del Task 3: motivo nella sua annotazione.

**Premesse del piano corrette qui (dette una volta, applicate nei task):**
- `tests/validazione/test_patch_test.py` ha **una** chiamata a `write_inp`, dentro `_risolvi` (`:172-178`); le righe 287-291 e 368-373 chiamano `_risolvi`. Cambia un posto, non tre.
- Le due varianti passano `fixed_nset="ANCORA"` (`:289`, `:370`): nel deck oggi finiscono `ANCORA, 1, 3` in `*BOUNDARY` e `*NODE PRINT, NSET=ANCORA` + `RF`. Nella variante B quella riga toglie il sesto moto rigido (`:348-354`): senza, `ccx` esce zero senza avviso. La `_appendi_analisi` del piano non la scriveva: corretta nel Task 1.
- La guardia sulla regione vuota sta a `abaqus.py:233-241`, non «474-480»; `UnconstrainedModelWarning` a `:22`; la chiamata `write_inp` dentro `export_model` a `:1209-1222`; `_passo_statico` a `:35-74`.
- `tests/materiale.py` **non si cancella**: lo importano 12 file (`test_abaqus:9`, `test_app_js:40`, `test_attribuzione:17`, `test_cli:10`, `test_config:12`, `test_ingresso:21`, `test_pipeline:12`, `test_report:17`, `test_server:20`, `test_steps:13`, `test_sweep:9,826`, `test_worker:15`). Si svuota di `MATERIALE`/`ANALISI`/`crea_config` e resta con `_tre_cartelle_finte` (Task 3b).
- `meshrec/docs/fase-8-*.md` non esiste; i documenti di fase sono `fase-4-materiale.md`, `fase-5-analisi.md`, `fase-6-carichi.md`; della fase 8 esiste solo la spec `2026-08-29-…-fase-8-prior-esteso-design.md` (Task 4).
- Nessun `runs/*/config.yaml` porta `solutore:` (grep su `meshrec/runs/*/config.yaml`: solo `analysis:` e `carichi:`; `runs/geoandgeo/config.yaml:51` porta `analysis: null`). La premessa «lo portano ancora» del Task 3 è falsa; la decisione resta la stessa per un altro motivo (vedi Task 3).
- **Baseline locale falsa finché esiste il worktree** `.claude/worktrees/feat-step-dal-prior`: `docs/validazione/controlla-riferimenti.py:56` (`SALTA = {".git", "node_modules", ".venv", "__pycache__"}`) indicizza anche il worktree e `tests/test_riferimenti_documenti.py` cade con «modulo ambiguo» (misurato: `uv run pytest tests/test_riferimenti_documenti.py -q` → **2 failed** da `meshrec/`, ramo `feat/deck-nudo-analisi`, HEAD 8004950). In CI non c'è il worktree. Rimedio in Task 0, Step 3.
- Gli script `meshrec/docs/fase-6-cantiere/misura-carichi.py`, `fase-7-cantiere/modi-per-la-normativa.py`, `fase-7-cantiere/scarto-c3d4-c3d10.py` chiamano `write_inp`/`export_model`/`Material`/`AnalysisConfig`: sono già «documento di cantiere, non più eseguibile» dalla PR 1 e nessuna prova li importa. **Niente da fare**, dichiarato qui perché la PR 1 li ha scoperti a review fatta.
- `docs/validazione/inventario-grandezze.md:114,136-139,344-345` e `docs/validazione/README.md:170-171` citano `config.GRAVITY_MM_S2`, `config.AnalysisConfig.gravity`, `config.Material.density`, `config.Material.young`, `test_oracoli_mancanti.test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola`, `test_oracoli_mancanti.test_la_gravita_…`, `test_oracoli_mancanti.test_densita_per_volume_per_gravita_da_newton`. Il checker (`controlla-riferimenti.py:62`, regex sui backtick `modulo.simbolo`) li dichiara **rotti** quando il simbolo sparisce → `test_riferimenti_documenti` rosso. Quelle righe si toccano **nello stesso commit** che toglie il simbolo (Task 2 per `mass`, Task 3b per gravità/Material), non nel Task 4.
- `tests/test_accenti.py:130` pretende `len(descrizioni) > 40` sullo schema; misurato oggi: **45** (`uv run python -c` su `PipelineConfig.model_json_schema()`), di cui 9 su `Material`(1)/`AnalysisConfig`(1)/`MaterialeDichiarato`(5)/`RegioneConfig.materiale`(1)/`PipelineConfig.analysis`(1); `ExportConfig` ne porta 1. Dopo il Task 3: ~37 → la soglia scende a 30 (Task 3b), col motivo nel commit.
- `test_config.py:222-274` (`test_lo_schema_non_sposta_l_impronta_dei_registri_in_silenzio`, aggregato `9b409e2d…`) e `:277-312` (impronte di `lab.yaml`/`muro.yaml`) **cadono due volte**: al Task 2 (`export` entra nel dump con il suo predefinito) e al Task 3b (`analysis` esce). Si aggiornano due volte, e lo si dice nei due commit — è la classe dichiarata da `sweep.py:66-67`.
- `CONTINUO_CONFINATO` (`abaqus.py:92`, scritto nel deck a `:328`, in `metrics.json` da `pipeline.py:844`) parla delle sezioni per regione: senza sezioni non ha più soggetto. Esce nel Task 1 tutto insieme: deck, costante, e la chiave `continuo` in `pipeline.py:838-845` (la sola riga di `pipeline.py` che il Task 1 tocca: la costante cancellata la lascerebbe con un `AttributeError`); prove: `test_abaqus.py:1715-1742`, `test_pipeline.py:1500`, `:1569`.

**PR 3 (`feat/step-dal-prior`, worktree già a 8004950):** tocca `pipeline.genera_modello` **dopo** `:362` e `:377`; questa PR tocca `:335` (`analisi = cfg.analisi_dichiarata(…)`) e `:356` (`analisi,` → `cfg.export,`). Sei righe intatte in mezzo: git fonde da sé. In `test_pipeline.py` la PR 3 inserisce a `:1216` circa e usa `_config_cubo` (`:20-39`, che porta `analysis=ANALISI`): se la PR 3 entra **prima**, la scopa del Task 3b su `_config_cubo` copre anche le sue prove nuove; se entra dopo, il suo rebase non deve toccare nulla perché `_config_cubo` è già sistemata. **Consiglio: PR 3 prima** (mezza sessione, worktree pronto), poi questa. Un solo effetto: il conteggio atteso della suite (+6).

**Stima per task (contesto da 100K per dispatch, non per sessione: con `subagent-driven-development` ogni task è un contesto fresco):** Task 1 entra solo spezzato in 1a/1b; Task 2 entra; Task 5 entra; Task 3 entra solo spezzato in 3a/3b, e 3b in due dispatch (codice / scopa delle prove) sullo stesso commit; Task 4 entra; Task 6 entra. La PR 4 viene **assorbita** (vedi Task 5): la stima della spec «una sessione» diventa tre sessioni di thread principale, o una con sei dispatch e report sotto le 60 righe.

---

### Task 0: ramo e baseline

**Files:** nessuno

- [ ] **Step 1**: `git -C /Users/mario/GitHub/Tesi checkout main && git -C /Users/mario/GitHub/Tesi pull --ff-only && git -C /Users/mario/GitHub/Tesi checkout -b feat/deck-nudo-analisi`
- [ ] **Step 2**: `uv run pytest -m "" -q 2>&1 | tail -3` → 1238 / 1 **solo senza il worktree** `.claude/worktrees/feat-step-dal-prior`; con il worktree: 1236 / 1 / 2 rossi in `test_riferimenti_documenti.py` (vedi annotazione).
- [ ] **Step 3** (thread principale, skill-gate **false**: una riga): `docs/validazione/controlla-riferimenti.py:56` → `SALTA = {".git", ".claude", "node_modules", ".venv", "__pycache__"}`. Commit a parte: `fix(riferimenti): il controllo dei riferimenti salta i worktree in .claude`. Poi Step 2 di nuovo → 1238 / 1 col worktree presente.

**Annotazione architect — Task 0.** Subagente: nessuno (thread principale). Skill-gate **false** (comandi git e una costante).

## Ingressi degeneri
- nessun ingresso esterno

---

### Task 1: `write_inp` scrive il deck nudo; il patch test si porta le sue card

**Files:**
- Modify: `src/meshrec/core/abaqus.py:145-163` (firma di `write_inp`), il corpo che scrive `*SOLID SECTION`/`*MATERIAL`/`*ELASTIC`/`*DENSITY` (fra `*ELSET` delle regioni e `*BOUNDARY`, righe 321-357), `*BOUNDARY` + `spostamenti_imposti` (358-378), `peso`/`_passo_statico` (380-383), `_passo_statico` intera (35-74), `_materiali_del_deck` (115-142), `CONTINUO_CONFINATO` (92-113, scritto a 328), la guardia sulla regione vuota (233-241), l'import di `GRAVITY_MM_S2`/`Material` (11-17), la chiamata a `write_inp` dentro `export_model` (1209-1222)
- Modify: `tests/validazione/test_patch_test.py:44-51` (import di `Material`, `MATERIALE`), `:163-188` (`_risolvi`, l'unica chiamata a `write_inp`)
- Modify: `tests/test_condizioni_imposte.py` (via il file; una prova si sposta), `tests/test_abaqus.py`, `tests/test_attribuzione.py:265-289`, `tests/test_pipeline.py:1380-1391, 1394-1441, 1551-1569`
- Test: `tests/test_abaqus.py`

**Annotazione architect — Task 1.** Subagente: `backend-engineer`. Due dispatch, un commit: **1a** prove (patch test con `_appendi_analisi`, `test_abaqus.py` riscritto, prova spostata; suite rossa alla fine, e va detto nel report quali prove sono rosse e perché) e **1b** codice (`abaqus.py` nudo, chiamata in `export_model`, `pipeline.py:838-845` senza la chiave `continuo` e il commento `:812-813`; le tuple `(indici, Material)` le spacchetta `export_model` fino al Task 2). Skill-gate **true** su entrambi. Sequenziale con il Task 2 (stesso `abaqus.py`).

## Ingressi degeneri
- `regioni={"TRAVE_1": np.array([], dtype=np.int64), "PILASTRO_1": <indici>}` → `RegioneVuotaWarning` che nomina `TRAVE_1`, nessun `*ELSET, ELSET=TRAVE_1`, `*ELSET, ELSET=PILASTRO_1` scritto, deck su disco
- `regioni={}` e `regioni=None` → deck byte-identico a quello senza regioni, nessuna riga `**` di commento
- `regioni` con indici fuori da `[0, len(elements))` → `IndexError`/`ValueError` prima di scrivere una riga, non un `*ELSET` con numeri inventati (oggi `attribuiti[indici_regione] = True` a `:322` solleva `IndexError` grezzo: basta una guardia con messaggio, stessa forma della guardia sui nodi a `:274-282`)
- `write_inp(..., material=…)`, `fixed_nset=`, `gravity=`, `step_name=`, `print_nsets=`, `spostamenti_imposti=`, `carichi_nodali=`, `carichi=`, `pressure=`, `nset_selettori=` → `TypeError`, nessun `**kwargs` (prova spostata, parametrizzata sui dieci nomi)
- `elements` vuoto, a una dimensione, con colonne sbagliate, con un nodo pendente → gli stessi quattro `ValueError` di oggi (`:244-282`), nello stesso ordine
- `ties` che nomina una superficie non dichiarata → `ValueError` come oggi (`:222-231`)
- patch test A (C3D4 e C3D10) e B con `ccx` → verdi: scarto ≤ `FATTORE·pavimento`, zero righe `*WARNING` nello stdout di `ccx` (oracoli invariati, `:183-185`, `:300`, `:377`)
- patch test senza `ccx` → `skip`, non verde (`_ccx_o_salta`, invariato)

**Interfaces:**
- Consumes: la firma attuale (`abaqus.py:145-163`): `write_inp(path, nodes, elements, *, node_sets, material, element_type, fixed_nset, print_nsets, gravity, elset, regioni: dict[str, tuple[ndarray, Material]], step_name, element_surfaces, ties, spostamenti_imposti, carichi_nodali) -> dict`.
- Produces:

```python
def write_inp(
    path: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    element_type: str = "C3D4",
    elset: str = "ALL_WALL",
    regioni: dict[str, np.ndarray] | None = None,
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str] | tuple[str, str, str, float], ...] = (),
) -> None:
```

Scrive: `*HEADING`, `*NODE`, `*ELEMENT`, `*NSET`×N, `*ELSET` per regione (solo quelle con almeno un elemento; regione vuota → `RegioneVuotaWarning`), `*SURFACE` e `*TIE` se passati. Niente altro. Rende `None`. Il patch test, che ha bisogno di materiale, `*BOUNDARY` con spostamenti imposti e un `*STEP` con `*CLOAD`, **appende** quelle card al file dopo `write_inp` con una funzione propria dentro `tests/validazione/test_patch_test.py` (una ventina di righe: `*SOLID SECTION`, `*MATERIAL`/`*ELASTIC`, `*BOUNDARY` nodo per nodo, `*STEP`/`*STATIC`/`*CLOAD`/`*NODE PRINT`/`*NODE FILE`/`*EL FILE`/`*END STEP`, copiate da come `_passo_statico` le scrive oggi).

- [ ] **Step 1: la prova del deck nudo, rossa**

In `tests/test_abaqus.py`, accanto a `test_il_deck_del_muro_porta_il_solo_passo_di_gravita` (che va **sostituita**: dalla PR 2 il deck non ha passi):

```python
def test_il_deck_del_muro_e_nudo(tmp_path):
    """Deck nudo per costruzione: intestazione, nodi, elementi, i sei insiemi di
    nodi, e basta. Nessuna sezione, materiale, vincolo, passo, carico."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)
    abaqus.export_model(
        tmp_path / "wall_model.inp", tmp_path / "wall_model.vtu",
        nodes, tets, config.ExportConfig(), TET_LINEARE,
    )
    card = [riga.split(",")[0] for riga in (tmp_path / "wall_model.inp").read_text().splitlines()
            if riga.startswith("*") and not riga.startswith("**")]
    assert card[:3] == ["*HEADING", "*NODE", "*ELEMENT"]
    assert set(card) == {"*HEADING", "*NODE", "*ELEMENT", "*NSET"}
    assert card.count("*NSET") == 6


def test_una_regione_vuota_avvisa_e_non_scrive_l_elset(tmp_path):
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)
    regioni = {"PILASTRO_1": np.arange(len(tets)), "TRAVE_1": np.array([], dtype=np.int64)}
    with pytest.warns(abaqus.RegioneVuotaWarning, match="TRAVE_1"):
        abaqus.export_model(
            tmp_path / "wall_model.inp", tmp_path / "wall_model.vtu",
            nodes, tets, config.ExportConfig(), TET_LINEARE, regioni=regioni,
        )
    deck = (tmp_path / "wall_model.inp").read_text()
    assert "*ELSET, ELSET=PILASTRO_1" in deck
    assert "TRAVE_1" not in deck
```

`config.ExportConfig` non esiste ancora: in questo task la prova usa `export_model` con la firma **nuova** (Task 2). Per tenere il commit verde, il Task 1 scrive la prova sul solo `write_inp`:

```python
def test_write_inp_scrive_il_solo_maglio(tmp_path):
    abaqus.write_inp(tmp_path / "nudo.inp", _CUBO, _ESAEDRO,
                     node_sets={"BASE": np.array([0, 1, 2, 3])}, element_type="C3D8I")
    card = [r.split(",")[0] for r in (tmp_path / "nudo.inp").read_text().splitlines()
            if r.startswith("*") and not r.startswith("**")]
    assert card == ["*HEADING", "*NODE", "*ELEMENT", "*NSET"]
```

e le due prove su `export_model` sopra si aggiungono nel Task 2, quando `ExportConfig` esiste.

- [ ] **Step 2: eseguirla, deve fallire**

Run: `uv run pytest tests/test_abaqus.py -k solo_maglio -q`
Expected: FAIL (`TypeError`: manca `material`).

- [ ] **Step 3: il patch test si porta le card**

In `tests/validazione/test_patch_test.py` cambia **un posto solo**: `_risolvi` (`:163-188`), l'unica chiamata a `write_inp`. Le due varianti (`:287-291`, `:368-373`) chiamano `_risolvi` e restano come sono. Oggi il deck del patch test, dopo `*NSET`, porta esattamente (letto su `abaqus.py:321-383` con `material=MATERIALE`, `gravity=0.0`, `print_nsets=("TUTTI",)`, `fixed_nset="ANCORA"`, nessuna regione):

```
*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=PROVA
*MATERIAL, NAME=PROVA
*ELASTIC
30000.0, 0.2
*DENSITY
2.4e-09
*BOUNDARY
ANCORA, 1, 3
<nodo>, <g>, <g>, <valore>        (uno per grado imposto)
** NOME PASSO: GRAVITA
*STEP
*STATIC
*DLOAD, OP=NEW
ALL_WALL, GRAV, 0.0, 0.0, 0.0, -1.0
*CLOAD                            (solo variante B)
<nodo>, <g>, <valore>
*NODE PRINT, NSET=TUTTI
U
*NODE PRINT, NSET=ANCORA
RF
*NODE FILE
U
*EL FILE
S, E
*END STEP
```

`_appendi_analisi` le riscrive tutte **tranne due**, dichiarate: `*DENSITY` e `*DLOAD … GRAV, 0.0` erano il peso proprio che `write_inp` imponeva e che il test azzerava (`gravity=0.0`, `:175`); un passo statico senza forze di volume non le legge. `ANCORA, 1, 3` **resta**: nella variante B è il sesto vincolo che toglie i moti rigidi (`:348-354`: su matrice singolare `ccx` esce zero senza avviso). `RF` su `ANCORA` resta: tiene nel `.dat` il blocco `forces` che il filtro di `read_dat_displacements` (`tests/ccx_utils.py`) esiste per saltare, e questo è l'unico test che lo esercita.

```python
from typing import NamedTuple


class _Materiale(NamedTuple):
    """Il materiale del provino. `config.Material` esce con la PR 2 del deck nudo:
    qui servono nome, modulo elastico e Poisson, e basta."""
    name: str
    young: float
    poisson: float


MATERIALE = _Materiale(name="PROVA", young=30000.0, poisson=0.2)


def _appendi_analisi(percorso, *, materiale, fixed_nset, print_nsets=(),
                     spostamenti_imposti=None, carichi_nodali=None):
    """Le card che il deck nudo non scrive piu' e che `ccx` pretende: sezione,
    materiale, `*BOUNDARY` (set vincolato, poi spostamenti nodo per nodo), un
    passo statico con le forze nodali e le stampe. Nell'ordine in cui
    `abaqus.write_inp` le scriveva fino al 08/09/2026 (commit 8004950).

    Non scritte apposta: `*DENSITY` e `*DLOAD ... GRAV, 0.0`, il peso proprio
    che il deck imponeva e questo test azzerava -- un passo statico senza
    forze di volume non le legge. `RF` sul set vincolato resta: tiene nel
    `.dat` il blocco `forces` che il filtro di `read_dat_displacements`
    esiste per saltare."""
    righe = [
        f"*SOLID SECTION, ELSET=ALL_WALL, MATERIAL={materiale.name}",
        f"*MATERIAL, NAME={materiale.name}", "*ELASTIC",
        f"{materiale.young}, {materiale.poisson}",
        "*BOUNDARY", f"{fixed_nset}, 1, 3",
    ]
    for nodo in sorted(spostamenti_imposti or {}):
        for grado in sorted(spostamenti_imposti[nodo]):
            righe.append(f"{int(nodo) + 1}, {grado}, {grado}, {spostamenti_imposti[nodo][grado]:.9e}")
    righe += ["** NOME PASSO: PATCH", "*STEP", "*STATIC"]
    if carichi_nodali:
        righe.append("*CLOAD")
        for nodo in sorted(carichi_nodali):
            for grado, valore in enumerate(carichi_nodali[nodo], start=1):
                if valore != 0.0:
                    righe.append(f"{int(nodo) + 1}, {grado}, {valore:.9e}")
    for nome in print_nsets:
        righe += [f"*NODE PRINT, NSET={nome}", "U"]
    righe += [f"*NODE PRINT, NSET={fixed_nset}", "RF",
              "*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP", ""]
    with open(percorso, "a", encoding="ascii") as deck:
        deck.write("\n".join(righe))


def _risolvi(tmp_path, nodi, tets, *, node_sets, fixed_nset, element_type="C3D4",
             spostamenti_imposti=None, carichi_nodali=None):
    """Il maglio passa per l'esportatore vero (`write_inp`): e' lui che questo
    test sorveglia. Le card dell'analisi le appende il test, perche' il deck
    nudo non le porta e qui e' l'unico posto in cui servono."""
    eseguibile = _ccx_o_salta()
    abaqus.write_inp(tmp_path / "patch.inp", nodi, tets,
                     node_sets=node_sets, element_type=element_type)
    _appendi_analisi(tmp_path / "patch.inp", materiale=MATERIALE, fixed_nset=fixed_nset,
                     print_nsets=("TUTTI",), spostamenti_imposti=spostamenti_imposti,
                     carichi_nodali=carichi_nodali)
    ... # da qui invariato (`:179-188`)
```

`from meshrec.core.config import Material` (`:46`) esce; le righe `:324-327` (`MATERIALE.young`/`.poisson`) restano come sono. Il file finisce con `\n` dopo `write_inp` (`lines.append("")` + `join`), quindi l'`append` non incolla la prima card all'ultimo `*NSET`.

- [ ] **Step 4: `write_inp` nudo**

In `abaqus.py`: nuova firma (Interfaces); cancellare `_passo_statico` (35-74), `CONTINUO_CONFINATO` (92-113) e la riga che lo scrive (328), `_materiali_del_deck` (115-142), il blocco `*SOLID SECTION`/`*MATERIAL`/`*ELASTIC`/`*DENSITY` (321-357), `*BOUNDARY` con `spostamenti_imposti` (358-378), `peso` e la chiamata a `_passo_statico` (380-383), le guardie su `fixed_nset`/`print_nsets` (207-211); `regioni` diventa `dict[str, np.ndarray]` (indici soli); una regione con zero indici → `warnings.warn(f"la regione '{nome}' non ha elementi attribuiti: nessun *ELSET scritto", RegioneVuotaWarning, stacklevel=2)` e si salta (definire `class RegioneVuotaWarning(UserWarning)` accanto a `UnconstrainedModelWarning`, riga 22); la guardia che oggi **solleva** su regione vuota (233-241) cade. Import (11-17): via `GRAVITY_MM_S2`, `Material`; `AnalysisConfig` resta fino al Task 2. Return `None`. La docstring riscritta in dieci righe: cosa scrive, cosa non scrive più e dove si assegna. In `export_model` (1209-1222) la chiamata perde `material=`, `fixed_nset=`, `gravity=`, `step_name=` e passa `regioni={nome: indici for nome, (indici, _) in (regioni or {}).items()}`; il resto di `export_model` (`cfg.fixed_nset`, `mass`) resta com'è fino al Task 2.

- [ ] **Step 5: le prove di `test_abaqus.py` e `test_condizioni_imposte.py`**

Liste da scansione AST su `main` 8004950 (script nello scratchpad dell'architect: per ogni `def`, i nomi e le stringhe che la PR toglie), non da grep. Righe = `main` 8004950.

`tests/test_abaqus.py` —
- **cancella** (provano card che il deck non ha più): `:76` `test_inp_contains_sets_material_and_gravity_step`, `:156` `test_material_values_round_trip_with_precision`, `:248` `test_il_deck_non_contiene_piu_card_che_calculix_scavalca`, `:312` `test_il_deck_del_muro_porta_il_solo_passo_di_gravita` (la sostituta è `test_il_deck_del_muro_e_nudo`, Task 2), `:1445` `test_senza_regioni_il_deck_scrive_la_sola_sezione_di_all_wall`, `:1511` `test_gli_orfani_tengono_la_sezione_di_all_wall`, `:1538` `test_senza_orfani_il_ripiego_non_si_scrive`, `:1591-1592` `CLS_C25`/`CLS_C30`, `:1595` `test_ogni_regione_scrive_il_proprio_materiale`, `:1632` `test_gli_orfani_restano_sul_materiale_unico_della_corsa`, `:1660` `test_due_regioni_sullo_stesso_materiale_scrivono_una_card_sola`, `:1690` `test_due_materiali_omonimi_ignorando_le_maiuscole_sono_rifiutati`, `:1715` `test_il_deck_a_regioni_dichiara_che_non_distingue_nucleo_e_copriferro`.
- **riscrivi**: `:1469` `test_ogni_regione_ha_il_suo_elset_e_la_sua_sezione` → `…_ha_il_suo_elset` (indici soli, asserisce `*ELSET` e **nessuna** `*SOLID SECTION`); `:1496` `test_una_regione_senza_elementi_e_rifiutata` → `…_avvisa_e_non_scrive_l_elset` su `write_inp` (`pytest.warns(RegioneVuotaWarning, match=nome)`, deck scritto, altri `*ELSET` presenti); `:1561` `test_export_model_porta_le_regioni_fino_al_deck` (tuple `(indici, MATERIALE)` restano fino al Task 2, asserisce `*ELSET` non `*SOLID SECTION`); `:1745` `test_un_dizionario_di_regioni_vuoto_scrive_il_deck_di_prima` (confronta byte a byte con il deck senza regioni, via `*MATERIAL`); nuova `test_write_inp_scrive_il_solo_maglio` (Step 1); la prova spostata da `test_condizioni_imposte.py:150-174`, con `NODI`/`TET`/`SET` (`:28-30`) portati insieme, parametrizzata sui dieci nomi (Ingressi degeneri), ramo `export_model` ancora con `AnalysisConfig(material=MATERIALE)` fino al Task 2.
- **togli i kwarg usciti** (`material=MATERIALE`, e dove ci sono `fixed_nset=`, `step_name=`, `print_nsets=`), nient'altro: `:57`, `:100`, `:137`, `:762`, `:786`, `:921`, `:941`, `:957`, `:1026`, `:1072`, `:1093`, `:1124`, `:1141`, `:1166`.
- **non toccare** in questo task (le sistema il Task 2 con `ExportConfig`): `:289`, `:335`, `:521`, `:606`, `:629`, `:811`, `:1000`, `:1389`, `:1416`. Gli import `:8-9` (`Material`, `ANALISI`, `MATERIALE`) restano fino al Task 3b.

`tests/test_condizioni_imposte.py` — `git rm`: `:53-138` (sette prove sulle card) cadono, la card la prova ora il patch test con `ccx`; `:150-174` si sposta come sopra.

`tests/test_attribuzione.py:265-289` `test_con_tutti_gli_elementi_orfani_il_deck_e_rifiutato_invece_che_monomaterico` — **ribalta**: `…_il_deck_avvisa_e_non_scrive_l_elset` (`pytest.warns(RegioneVuotaWarning, match="LONTANA")`, deck scritto senza `*ELSET, ELSET=LONTANA`); `regioni={"LONTANA": np.flatnonzero(etichette == 0)}`; via `material=MATERIALE`. `MATERIALE` a `:17` resta importata fino al Task 3a (`_regione`, `:51-58`).

`tests/test_pipeline.py` — `:1380-1391` `test_il_deck_dello_step_11_porta_un_solo_passo` → `…_e_nudo`: `"*STEP" not in deck`, `"*BOUNDARY" not in deck`, `"*SOLID SECTION" not in deck`, `"*MATERIAL" not in deck`; `:1394-1441` `test_una_config_yaml_vecchia_arriva_al_deck_a_un_passo` → stesso oracolo nudo (**in Task 3b si ribalta** in rifiuto); `:1551-1569` `test_senza_regioni_lo_step_11_non_rilegge_il_prior` → via l'asserzione su `CONTINUO_CONFINATO` (`:1569`), il resto resta; `:1467-1500` `test_lo_step_11_rilegge_il_prior_e_porta_il_materiale_della_regione_nel_deck` → via l'asserzione `:1500` su `resoconto["continuo"]` e quelle su `*MATERIAL`/`*SOLID SECTION`; resta l'`*ELSET` per regione; il Task 2 la rinomina (`…_e_porta_l_elset_della_regione_nel_deck`) e il Task 3a le toglie il materiale dalla `_regione`.

`export_model` in questo task: vedi Step 4 (kwarg tolti dalla chiamata, tuple spacchettate); di `pipeline.py` si tocca solo `:838-845` (via la chiave `continuo`) e il commento `:812-813`.

- [ ] **Step 6: verde**

Run: `uv run pytest tests/test_abaqus.py tests/test_attribuzione.py tests/test_pipeline.py tests/test_hexa.py -q`, poi `uv run pytest -m "" -q 2>&1 | tail -3` (il patch test **deve** girare: senza `ccx` salta e il verde mente; nel report il conteggio con `ccx` sul PATH, e `which ccx`).
Expected: verde; annotare il conteggio.

- [ ] **Step 7: commit**

```
refactor(abaqus): il deck e' nudo, il patch test si porta le sue card

write_inp scrive intestazione, nodi, elementi, insiemi di nodi e un
elset per regione: sezioni, materiali, vincolo e passo di gravita' si
assegnano in Abaqus (spec 2026-09-07). Una regione senza elementi
avvisa invece di sollevare. Il patch test appende da se' materiale,
vincoli e passo con le forze nodali, ed e' l'unico posto dove servono.
```

---

### Task 2: `export_model` legge `ExportConfig`; `mass` cade; le regioni sono indici

**Files:**
- Modify: `src/meshrec/core/config.py` (nuova classe `ExportConfig` accanto a `TetConfig`; `PipelineConfig.export`; `STEP_BLOCKS` in `steps.py:67` → `("tet", "export", "regioni")`)
- Modify: `src/meshrec/core/abaqus.py:1099-1248` (`export_model`: `cfg: ExportConfig`, `cfg.fixed_nset` → costante `"BASE"`, via `mass`), `src/meshrec/core/pipeline.py:800-837` (step 11: `cfg.export` al posto di `cfg.analisi_dichiarata("lo step 11")`, `regioni_deck` senza materiale), `pipeline.py:351-362` (`genera_modello`: `cfg.export`), `src/meshrec/core/attribuzione.py:38-75` (`prismi_delle_regioni` legge `RegioneConfig.membratura` sola — verificare che non legga `materiale`), `src/meshrec/core/report.py:1075, 1205-1235, 1257-1282` (riga «massa»), `src/meshrec/core/sweep.py` (ogni `analysis`), `src/meshrec/app/server.py:625` (`_FUORI_DAL_PANNELLO[11]` → `frozenset({"tet"})`)
- Test: `tests/test_abaqus.py` (le due prove su `export_model` dello Step 1 del Task 1), `tests/test_steps.py`, `tests/test_config.py`, `tests/test_pipeline.py`, `tests/test_report.py`, `tests/test_sweep.py`, `tests/test_server.py`

**Interfaces:**
- Produces:

```python
class ExportConfig(_ModelloBase):
    """Lo step 11: come si costruiscono gli insiemi di nodi delle facce."""
    set_tolerance_factor: float = Field(
        default=6.0, gt=0.0,
        title="tolleranza degli insiemi di faccia [multipli della spaziatura]",
        description="…copiare la description che oggi sta su AnalysisConfig.set_tolerance_factor (config.py:393-444)…",
    )
```

`PipelineConfig.export: ExportConfig = Field(default_factory=ExportConfig)`; `export_model(path_inp, path_vtu, nodes, elements, cfg: ExportConfig, tet_cfg, reference=None, element_type=None, element_surfaces=None, ties=(), regioni: dict[str, np.ndarray] | None = None) -> dict`; il set vincolato dei controlli di copertura è la costante `SET_DI_BASE = "BASE"` in `abaqus.py` (era `cfg.fixed_nset`; `base_coverage` e `constraint_plan_extent` restano su `BASE`, l'avviso `UnconstrainedModelWarning` nomina `export.set_tolerance_factor`); il dizionario reso perde `mass`.

**Annotazione architect — Task 2.** Subagente: `backend-engineer`, un dispatch, un commit. Skill-gate **true**. Sequenziale dopo 1b (`abaqus.py`) e prima del Task 5 (`/api/schema` serve `export` da qui: la legenda in `app.js` la mette il Task 5). Fatti letti che il piano non diceva: `attribuzione.prismi_delle_regioni` (`attribuzione.py:38-75`) rende `dict[str, hexa.Prisma]`, **nessun materiale**: non si tocca (solo il docstring `:113` che cita `analysis.material`); `sweep.fingerprint` (`sweep.py:94-115`) non cita `analysis` per nome — solo i commenti `:123-131` in `with_override`; `report.confronta` legge `mass` con `.get` (`report.py:1219`, `:1235`): un `metrics.json`/`modello.json` già su disco con `mass` non rompe nulla, la chiave viene ignorata. Due righe di JS meccaniche entrano qui (righe «massa» dell'interfaccia), non nel Task 5: `ui/modello.js:128` e `ui/etichette.js:191`.

**Files (corretti):** `config.py` (`ExportConfig` accanto a `TetConfig`; `PipelineConfig.export`), `steps.py:63-68` (commento e tupla), `abaqus.py:1099-1247` (`export_model`: firma, `SET_DI_BASE = "BASE"`, via la guardia `:1178-1185` — con `BASE` costante e `build_node_sets` che fabbrica sempre i sei, il ramo «non è fra gli insiemi» è morto; resta `:1186-1187` sul set vuoto; `:1198-1207` avviso che nomina `export.set_tolerance_factor`; `:1231-1232` copertura su `SET_DI_BASE`; `:1235` via `mass`; import `:11-17` via `AnalysisConfig`, entra `ExportConfig`), `pipeline.py:335` (via `analisi = cfg.analisi_dichiarata(...)`), `:351-362` (`cfg.export` al posto di `analisi`), `:805-837` (`regioni_deck = {nome: np.flatnonzero(etichette == posizione)}`, `cfg.export` al posto di `cfg.analisi_dichiarata("lo step 11")`, commento `:812-813`), `report.py:1075` (`CONFRONTABILI["massa"]`), `:1083` (docstring), `:1205,1219,1235,1257` (raccolta e chiave), `:1269` (`_ETICHETTE_GRANDEZZE`), `:1282` (docstring), `server.py:614-625` (`_FUORI_DAL_PANNELLO[11] = frozenset({"tet"})`, commento), `ui/modello.js:128`, `ui/etichette.js:191`, `tests/materiale.py:88,104` (`"mass"` nelle cartelle finte: via, è un dato che nessuna riga legge più), `docs/validazione/inventario-grandezze.md:114,344`, `docs/validazione/README.md:170` (la riga O3 diventa «volume» solo; rinomina della prova).

## Ingressi degeneri
- `ExportConfig(set_tolerance_factor=0.0)`, negativo, `inf`, `nan` → `ValidationError` alla costruzione (`gt=0.0` + `allow_inf_nan=False` di `_ModelloBase`), nessun deck
- yaml senza `export:` → `PipelineConfig(...).export.set_tolerance_factor == 6.0`, deck scritto
- `export_model` con `elements` vuoto → `ValueError(MAGLIO_VUOTO)` come oggi (`:1156-1157`)
- `BASE` vuoto per tolleranza minuscola → `ValueError` «il set vincolato 'BASE' e vuoto: tolleranza … troppo stretta» (`:1186-1187`), senza più citare `AnalysisConfig`
- copertura di `BASE` ≤ 0,5 → `UnconstrainedModelWarning` il cui testo contiene `export.set_tolerance_factor` (era `analysis.set_tolerance_factor`, `:1204`)
- `regioni` con un array vuoto passato da `export_model` → la stessa `RegioneVuotaWarning` del Task 1 arriva al chiamante (`export_model` non la inghiotte)
- `metrics.json` di una corsa vecchia con `11_export.mass` → `report.confronta` non stampa «massa», non solleva; `modello.json` figlia con `export.mass` → idem
- cambia `export.set_tolerance_factor` → `step_fingerprints` muove 11 e 12, non 9 e 10; cambia `tet.*` → muove 9-12 come oggi
- `sweep.with_override(cfg, "export.set_tolerance_factor", 4.0)` → configurazione rivalidata, `gt=0` rispettato; con `0.0` → `ValidationError`
- corsa già su disco con `steps.json` scritto prima → lo step 11 risulta «non valido» al primo `read_state`, rieseguibile; i registri `experiments/*/registro.jsonl` non si toccano (aggregato in `test_config.py:271` aggiornato e dichiarato nel commit)

**Liste di prove (AST, `main` 8004950):**

`tests/test_abaqus.py` — **riscrivi** con `config.ExportConfig()` al posto di `config.AnalysisConfig(material=MATERIALE)`: `:335`, `:521`, `:606` (`match="export.set_tolerance_factor"`), `:629`, `:811`, `:1000`, `:1561`, e il ramo `export_model` della prova spostata nel Task 1; `:289` `test_export_model_writes_both_files_and_reports_mass` → `…_writes_both_files`, via l'asserzione su `mass`, `"mass" not in esito`; **cancella** `:1389` `test_un_fixed_nset_sconosciuto_nomina_gli_insiemi_disponibili`, `:1416` `test_un_fixed_nset_in_minuscolo_arriva_al_deck_senza_sollevare` (non c'è più un `fixed_nset` da sbagliare); **nuove** `test_il_deck_del_muro_e_nudo`, `test_una_regione_vuota_avvisa_e_non_scrive_l_elset` (su `export_model`, Task 1 Step 1).

`tests/test_oracoli_mancanti.py:126-150` `test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola` → `test_il_volume_del_deck_e_quello_della_scatola`: `ExportConfig()`, via `Material`/`mass`; **nello stesso commit** le due righe dei documenti che la nominano (`inventario-grandezze.md:114,344`, `README.md:170`), o `test_riferimenti_documenti` cade.

`tests/test_config.py` — **nuova** `test_export_ha_la_tolleranza_e_rifiuta_zero`; `:222-274` aggregato dei registri: aggiornare l'hash e dirlo nel commit; `:277-312` impronte di `lab.yaml`/`muro.yaml`: aggiornare; `:315-347` resta verde com'è (`export` non sta in nessuna delle due liste, e non deve).

`tests/test_steps.py` — `:154-183` `test_cambiare_una_regione_invalida_lo_step_11`: `("tet", "export", "regioni")` e docstring senza `*SOLID SECTION`; `:241-244` → `test_lo_step_11_legge_tet_export_e_regioni`; **nuova** `test_cambiare_la_tolleranza_degli_insiemi_invalida_lo_step_11_e_non_il_9` (accanto a `:130-152`, che ha già la forma).

`tests/test_pipeline.py` — `:201-206` `test_the_mass_follows_from_density_and_volume` **cancella**; `:1467-1500` rinomina (`…_e_porta_l_elset_della_regione_nel_deck`).

`tests/test_report.py:1487-1510` `test_ogni_grandezza_numerica_porta_l_unita_nell_etichetta` → `len(numeriche) == 2`, docstring senza «massa» (la mutazione resta: togliere `[mm³]` da volume).

`tests/test_server.py:2523-2557` `test_il_pannello_dello_step_11_mostra_solo_i_blocchi_che_comanda` → `STEP_BLOCKS[11] == ("tet", "export", "regioni")`; `corpo["11"]["blocchi"] == ["export"]` (**non** `["export", "regioni"]`: la regola in `:2532-2534`, «una sezione che non può mai contenere nulla non compare», vale ancora per `regioni`); `set(corpo["11"]["campi"]["export"]) == {"set_tolerance_factor"}`; via le asserzioni su `gravity`/`fixed_nset`/`step_name`/`material`.

`tests/test_ingresso.py:338-347` `test_lo_schema_descrive_il_materiale_anche_se_il_blocco_e_opzionale` → **cancella**: la premessa (un blocco `X | None`) non ha più un soggetto dopo il Task 3, e già qui il pannello 11 legge `export`; `test_server.py:2523` copre `campi["export"]`.

`tests/test_app_js.py:6894-6945` resta verde (nessuna riga su `mass`); `tests/test_sweep.py` nessuna prova da toccare qui.

- [ ] **Step 1**: prove rosse — le liste sopra, prima le nuove. Run → FAIL.
- [ ] **Step 2**: `ExportConfig` + campo; `STEP_BLOCKS[11]`; `export_model` con la nuova firma, `SET_DI_BASE`, via `"mass"`; `pipeline.py` step 11 e `genera_modello`: `cfg.export`, `regioni_deck = {nome: indici}`; `report.py`: via la riga «massa» e la sua raccolta; `server.py:625`; `modello.js:128`, `etichette.js:191`; `sweep.py:123-131` solo il commento.
- [ ] **Step 3**: prove — le liste sopra; niente grep a tappeto.
- [ ] **Step 4**: `uv run pytest -m "" -q` verde. Corsa vera: `runs/geoandgeo-lab` copiata in `runs/geoandgeo-lab-pr2`, `--from-step 9 --to-step 11`; il deck ha **solo** `*HEADING`, `*NODE`, `*ELEMENT`, sei `*NSET`; `*NODE`/`*ELEMENT`/`*NSET` identici al baseline (`runs/geoandgeo-lab/wall_model.inp`, md5 `ba97f83be2f0d7b45f46e2f42f3bbfac` è del **file intero** di prima: confrontare le righe fino all'ultimo `*NSET` incluso, `sed -n '1,/^\*SOLID SECTION/p' | sed '$d'` sul vecchio contro il nuovo intero, e registrare i due md5). Il `config.yaml` di quella corsa ha ancora `analysis:` (letto, con `set_tolerance_factor` inutilizzato) e `carichi:` (ignorato dalla PR 1): il Task 3 li rifiuterà, e la corsa vera si ripete lì con i due blocchi tolti ed `export:` messo.
- [ ] **Step 5**: commit `feat(export): lo step 11 legge il blocco export, il deck perde massa e materiale`.

---

### Task 3: la configurazione perde `analysis`, `Material`, `MaterialeDichiarato`, il catalogo e `init`; entra il rifiuto nominato

**Files:**
- Modify: `src/meshrec/core/config.py:22` (`GRAVITY_MM_S2`), `121-154` (`Material`), `390` (`NOMI_PASSO_RISERVATI`), `393-444` (`AnalysisConfig`), `802-875` (`MaterialeDichiarato`), `878-903` (`RegioneConfig`: resta `membratura`, via `materiale`), `917-927` (`PipelineConfig.analysis`), `965-989` (`analisi_dichiarata`); nuovo: `BLOCCHI_RIMOSSI` e validatore `before` su `PipelineConfig` e su `RegioneConfig`
- Delete: `src/meshrec/core/materiali.py`, `tests/test_materiali.py`
- Modify: `tests/materiale.py` → **non si cancella** (12 importatori): via `MATERIALE`, `ANALISI`, `crea_config`; resta `_tre_cartelle_finte`; `git mv` in `tests/corse_finte.py` con docstring nuovo (i due importatori veri: `test_cli.py:10`, `test_report.py:17`); gli altri dieci import spariscono con la scopa
- Modify: `src/meshrec/cli.py:16-25` (import), `:51-62` (comando `init`: **via il comando intero**), `:164-181` (ramo in `main`); `src/meshrec/app/server.py:1410-1457` (rotta `/api/materiali`: via), `:940` e `:954` (`voce["materiale"] = cfg.analysis.material.name …` → via la chiave: dopo il Task 3 sarebbe un `AttributeError` su ogni `/api/corse`), `:537` e `:1478-1490` (commenti su `analysis`); `src/meshrec/core/hexa.py` **non cita `Material`** (verificato: `:312` è prosa) — non si tocca; `src/meshrec/core/report.py:793-794,814` (commenti su `analysis: null`); `src/meshrec/core/sweep.py:123-131` (commento); `src/meshrec/core/attribuzione.py:113` (docstring: via `analysis.material`)
- Modify: `casi/lab.yaml:55-64`, `casi/muro.yaml:52-61`, `casi/lab_telaio.yaml:69-81`, `casi/prova-interfaccia.yaml:56-65`: via il blocco `analysis:`, entra `export:\n  set_tolerance_factor: 6.0` (tutti e quattro valgono 6.0 oggi)
- Modify: `docs/validazione/inventario-grandezze.md:136-139,345`, `docs/validazione/README.md:171` (le righe O4 e «Conversioni di unità» che citano `config.GRAVITY_MM_S2`, `config.AnalysisConfig.gravity`, `config.Material.*`, e le due prove di gravità): «superato il 08/09/2026: il deck nudo non scrive la gravità, vedi ADR»; i backtick sui simboli usciti si tolgono, o il checker li dichiara rotti; `docs/validazione/controlla-riferimenti.py:11` (esempio nel docstring: `config.ExportConfig.set_tolerance_factor`)
- Test: vedi le liste nell'annotazione

**Interfaces:**
- Produces: `PipelineConfig` senza `analysis`; `RegioneConfig(membratura: int)`; `BLOCCHI_RIMOSSI: dict[str, str]` = `{"analysis": "…08/09/2026, PR feat/deck-nudo-analisi: materiali, vincoli e carichi si assegnano in Abaqus; set_tolerance_factor sta ora in export", "carichi": "…08/09/2026, PR #190…", "selettori": "…08/09/2026, PR #190…", "solutore": "…02/09/2026, mappa #161…"}`; validatore:

```python
@model_validator(mode="before")
@classmethod
def _rifiuta_i_blocchi_rimossi(cls, dati):
    if isinstance(dati, dict):
        for blocco, motivo in BLOCCHI_RIMOSSI.items():
            if blocco in dati:
                raise ValueError(
                    f"il blocco '{blocco}' non esiste piu' ({motivo}): toglilo dal config.yaml"
                )
    return dati
```

e lo stesso su `RegioneConfig` per `materiale`. Il validatore raccoglie **tutti** i blocchi rimossi presenti e li nomina in un solo messaggio (`runs/geoandgeo-lab/config.yaml` porta `analysis:` **e** `carichi:`; un rifiuto per volta costa una corsa a blocco).

**Decisione (a), `solutore:` in `BLOCCHI_RIMOSSI`: fuori, confermato — con un motivo diverso da quello del piano.** La premessa «le corse su disco lo portano ancora» è falsa: nessun `runs/*/config.yaml` ha `solutore:` (grep, 08/09/2026). Resta fuori perché: (1) la spec nomina tre blocchi e il rifiuto esiste per un pericolo preciso — un yaml che dichiara un materiale che nessuno usa più cambia significato in silenzio — e `solutore` non ha quel pericolo, dal 02/09 non produce nulla; (2) il messaggio del rifiuto deve dire «dove sta ora il parametro», e per `solutore` non c'è un dove; (3) `test_config.py:528-570` protegge da due settimane l'«ignorato», con una mutazione dichiarata. Un rifiuto che nessun file sul disco può innescare è codice con un test e senza un consumatore. Nella tupla va una riga di commento: «`solutore` (mappa #161) resta ignorato: nessun file lo porta, nessun parametro è migrato altrove; se un giorno entra `extra="forbid"` (ADR, approccio C) lo prende quello».

**Annotazione architect — Task 3.** Subagente: `backend-engineer`. **Due commit, tre dispatch**, sequenziali, tutti **dopo il Task 5** (che toglie il pannello finché la rotta e `analysis` esistono ancora: così ogni commit resta verde). Skill-gate **true** su tutti.

- **3a — le regioni portano la sola `membratura`; via catalogo, rotta, `init`** (un dispatch, commit `refactor(config): le regioni portano la sola membratura; via catalogo, /api/materiali e init`). Codice: `config.py:802-903` (`MaterialeDichiarato`, `RegioneConfig.materiale`; entra su `RegioneConfig` il validatore `before` che rifiuta la chiave `materiale` nominando la regione — la chiave la conosce solo il chiamante, quindi il messaggio dice «il campo `materiale` di una regione non esiste più (08/09/2026, PR feat/deck-nudo-analisi): il materiale si assegna in Abaqus sull'`*ELSET`»), `materiali.py`, `cli.py` (`init`), `server.py:1410-1457`. Prove: `test_materiali.py` (`git rm`); `test_config.py:596-607` (`_materiale_dichiarato` via, `_regione` → `{"membratura": 0, **campi}`), `:663-680` → `model_fields == {"membratura"}` + nuova prova del rifiuto di `materiale`, `:683-753` cancella (tre prove su `MaterialeDichiarato`), `:770-788` e `:837-850` togli `materiale`; `test_pipeline.py:1454-1464` (`_CLS_NUCLEO` via, `_regione(membratura)`), `:1467-1500` togli il materiale; `test_steps.py:154-183` togli `materiale` dal dizionario; `test_attribuzione.py:17,51-58` (`_regione(membratura)`, via l'import di `MATERIALE`); `test_server.py:91-117` e `:3612-3643` togli `materiale`, `:2313-2390` cancella (tre prove del catalogo); `test_cli.py:36-54` cancella, `:57-61` → `test_init_non_esiste_piu` (`pytest.raises(SystemExit)`, «invalid choice» in stderr, nessun file scritto).
- **3b — via `analysis`, `Material`, `AnalysisConfig`; entra `BLOCCHI_RIMOSSI`** (commit `refactor(config): via analysis e Material; un yaml vecchio viene rifiutato per nome`), in **due dispatch** sullo stesso commit: **3b-i** codice + `tests/materiale.py` + `casi/*.yaml` + i due `.md` di validazione (suite rossa, dichiarata nel report con l'elenco dei file rossi); **3b-ii** la scopa delle prove (liste sotto) fino al verde. Codice: `config.py:22` (`GRAVITY_MM_S2`), `:27-40` (`_caso_canonico_dei_sei`, `NomeSetDiFaccia`: l'unico utente è `fixed_nset`, `:402`), `:121-154`, `:390-444`, `:917-927`, `:965-989`; `BLOCCHI_RIMOSSI` + validatore su `PipelineConfig`; `server.py:940,954`; `cli.py:16-25` import; commenti in `report.py`, `sweep.py`, `attribuzione.py`, `server.py`; `tests/test_accenti.py:130` soglia `> 30` (misurato 45 → ~37: motivo nel commit).

**La scopa di 3b-ii** (conteggi da grep su `main` 8004950): `crea_config(` → `config.PipelineConfig(` in `test_cli.py` (7), `test_config.py` (9), `test_pipeline.py` (5), `test_sweep.py` (4 + `:826`); `analysis=ANALISI` → via il kwarg in `test_worker.py` (6: `:23,45,96,199,235,369`), `test_report.py` (`:469-503`, `:553-562`, `:849-870`, `:908-924`), `test_server.py` (`:25`, `:3621`, +1), `test_ingresso.py` (`:82-93`, `:192-200`, `:350-361`), `test_steps.py:16-19`, `test_app_js.py:40` e `:1345-1438`, `test_pipeline.py:20-39` (`_config_cubo`), `:912-932` (`corsa_all_undici`), `test_abaqus.py:8-9` (import `Material`, `ANALISI`, `MATERIALE` — `MATERIALE` è già senza usi dal Task 1).

`tests/test_config.py` (3b-ii) — **cancella**: `:24-52`, `:177-179`, `:188-199`, `:202-208`, `:351-365` (`step_name` ×2), `:368-407` (cinque prove su `analysis` assente / `analisi_dichiarata` / materiale obbligatorio), `:411-439` (`fixed_nset` ×2), `:478-492`; **riscrivi**: `:15-21` (`defaults`: `cfg.export.set_tolerance_factor == 6.0`, via `gravity`), `:55-64` (round trip senza `analysis`), `:100-128` (chiavi omonime: il testo yaml usa `tet` al posto di `analysis`), `:528-570` **ribalta** (`carichi:`/`selettori:` → `ValueError` che cita `#190`; `solutore:` e `model.lateral_*` restano ignorati; docstring e mutazione aggiornate), `:222-274` aggregato (seconda volta), `:277-312` impronte (seconda volta); **nuove**: rifiuto nominato per `analysis:` (anche `analysis: null`), `carichi:`, `selettori:`; un solo `ValueError` che nomina `analysis` **e** `carichi` quando ci sono entrambi; `"analysis" not in PipelineConfig.model_fields`; `not hasattr(config, "Material")`, `not hasattr(config, "AnalysisConfig")`, `not hasattr(config, "GRAVITY_MM_S2")`.

`tests/test_pipeline.py` (3b-ii) — `:1320-1377` **cancella** (quattro prove «senza materiale»: la corsa arriva allo step 11 senza dichiarare nulla — la nuova prova, accanto: `test_una_corsa_senza_export_arriva_al_deck_col_predefinito`); `:1394-1441` **ribalta**: lo yaml vecchio con `analysis:` viene rifiutato da `load_config` con il messaggio nominato, nessuna cartella scritta.

`tests/test_server.py` (3b-ii) — `:67-69` `{"input","segment","surface","tet","export"}`; `:3894-3950` **cancella** (due prove sui campi del materiale rifiutati per etichetta); `PUT /api/config` con `analysis` nel corpo → 422 e il messaggio che nomina il blocco (nuova, una).

`tests/test_oracoli_mancanti.py` (3b-ii) — `:27` import, `:156-176` **cancella** (le due prove sulla gravità: la costante esce con il suo unico consumatore); nello stesso commit le righe dei `.md` (Files).

`tests/test_report.py:1949-1986` — se il banco usa `analysis` come blocco «senza title», passare a un altro blocco; altrimenti resta.

`tests/test_app_js.py:2191-2207` `test_i_campi_di_un_blocco_assente_restano_in_sola_lettura` — resta verde (banco puro, `configurazione = { simplify: … }`); il docstring parla di `analysis`: ritocco nel Task 5, non qui.

## Ingressi degeneri (3a)
- yaml con `regioni.X.materiale:` → `ValidationError` il cui percorso è `regioni.X.materiale` e il cui messaggio nomina `materiale` e la data, nessuna `PipelineConfig`
- `regioni.X.membratura` fuori intervallo → `ValueError` come oggi (`attribuzione.py:52-57`); due regioni sulla stessa membratura → `ValueError` come oggi (`:58-64`)
- `meshrec init …` → `argparse` rifiuta («invalid choice»), exit 2, nessun file scritto
- `GET /api/materiali` → 404
- `PUT /api/config` con `regioni.X.materiale` nel corpo → 422 con il messaggio che nomina `X`

## Ingressi degeneri (3b)
- yaml con `analysis:` → `ValueError` che nomina `analysis`, `08/09/2026`, e «`set_tolerance_factor` sta ora in `export`»; nessuna `PipelineConfig`
- yaml con `analysis: null` (`runs/geoandgeo/config.yaml:51` è così) → stesso rifiuto: è la chiave che conta, non il valore
- yaml con `carichi:` o `selettori:` → stesso rifiuto, che cita `#190`
- yaml con `analysis:` **e** `carichi:` (`runs/geoandgeo-lab/config.yaml:56,66`) → un solo `ValueError` che li nomina entrambi
- yaml con `solutore:` → ignorato, nessun avviso; `model.lateral_nset` → ignorato (come oggi, `test_config.py:528-570`)
- `PUT /api/config` con `analysis` nel corpo → 422, corpo che nomina `analysis` (via `_rifiuto_leggibile`)
- `/api/corse` con una cartella il cui `config.yaml` porta `analysis:` → la corsa resta in elenco con `voce["errore"]` che nomina `analysis`, le altre si aprono, nessun 400 sull'elenco (`server.py:945-951`)
- `esperimento.yaml` con un asse `analysis.material.young` → `ValueError` che nomina l'asse e dice che il blocco non esiste, **non** un `KeyError` nudo (`sweep.with_override`, `sweep.py:118-135`: oggi la guardia copre solo `node is None`)
- `meshrec run` su `casi/*.yaml` → i quattro si leggono (impronte nuove registrate in `test_config.py:277-312`)

- [ ] **Step 1** (3a): prove rosse; poi codice; poi verde; commit.
- [ ] **Step 2** (3b-i): codice + `materiale.py` + `casi/*.yaml` + `.md`; report con l'elenco dei file di prova rossi.
- [ ] **Step 3** (3b-ii): la scopa; nuove prove del rifiuto; verde.
- [ ] **Step 4**: suite verde onesta. Corsa vera: `runs/geoandgeo-lab-pr2/config.yaml` con `analysis:` **e** `carichi:` → **rifiutato** col messaggio che nomina entrambi (registrarlo nel report); poi tolti i due blocchi e messo `export: {set_tolerance_factor: 6.0}`, `--from-step 9 --to-step 11` → deck nudo, `*NODE`/`*ELEMENT`/`*NSET` identici al baseline (`md5` sulle sole righe di mesh, non sul file: il deck nuovo è più corto di 20 righe).
- [ ] **Step 5**: commit di 3b.

---

### Task 4: la prosa dice il vero

**Files:**
- Modify: `PRODUCT.md:56-70, 106-112, 135` (perimetro: «dalla nuvola al deck nudo, che Abaqus completa; dal prior alla geometria STEP dei modelli parametrici», rimando alla spec del 31/08 e ai due ADR; `:106` «deck pronto all'analisi» → «deck nudo»), `AGENTS.md:64-72` (la frase su `STEP_KEYS`: «si chiude sul deck `.inp` **nudo** dello step 11»; `:48` dice già «il patch test, che e' l'unico rimasto a eseguirlo» — **niente da cambiare lì**, la premessa del piano era stantia), `docs/superpowers/specs/2026-08-31-perimetro-del-progetto-design.md` (un paragrafo di rimando in testa), `meshrec/docs/fase-4-materiale.md`, `fase-5-analisi.md`, `fase-6-carichi.md` (**`fase-8-*.md` non esiste**), e le spec `docs/superpowers/specs/2026-08-21-meshrec-fase-5-analisi-strutturale-design.md`, `2026-08-22-meshrec-fase-6-carichi-posizionati-design.md`, `2026-08-29-meshrec-fase-8-prior-esteso-design.md` (una riga in testa: «Superato il 08/09/2026: …, vedi `docs/adr/2026-09-07-deck-nudo-via-analisi-carichi-selettori.md`»)
- **Non qui**: `index.html:150` e `app.js:39` sono del Task 5 (un solo dispatch tocca `ui/`); i due `.md` di `docs/validazione` sono già usciti con i Task 2 e 3b (il checker li lega ai simboli)
- Test: `tests/test_riferimenti_documenti.py` (deve restare verde: i documenti di fase non stanno in `docs/validazione/`, quindi la riga in testa non passa dal checker — verificarlo con la suite, non darlo per detto)

**Annotazione architect — Task 4.** Subagente: **thread principale** (dieci file, una riga o un paragrafo ciascuno; il giudizio è sulle parole, e lo raccoglie `craft-reviewer` nel Task 6). Skill-gate **false**: prosa meccanica con un oracolo (`test_riferimenti_documenti`) e un revisore dedicato. Sequenziale dopo 3b (`PRODUCT.md` deve descrivere ciò che il codice fa a quel commit).

## Ingressi degeneri
- nessun ingresso esterno (solo testo; oracolo: `uv run pytest tests/test_riferimenti_documenti.py -q` verde, `craft-reviewer` nel Task 6)

- [ ] **Step 1**: le modifiche, una per file; `uv run pytest tests/test_riferimenti_documenti.py -q`.
- [ ] **Step 2**: commit `docs(prodotto): il perimetro e' il deck nudo e la geometria STEP`.

---

### Task 5: via il pannello del materiale (la PR 4 viene assorbita qui) — **obbligatorio, prima del Task 3**

**Decisione (b), letta su `tests/test_app_js.py` a 8004950.** `_banco_del_materiale` (`:1451-1511`) stubba `fetch` per `/api/materiali` (`:1490-1497`), **ma** le sei prove che lo usano (`:1520`, `:1554`, `:1599`, `:1663`, `:1706`, `:1765`) chiudono sul **server vero**: `cliente.get("/api/materiali")` (`:1574`, `:1629`, `:1682`), `cliente.put("/api/config", json=corpo)` con `analysis` nel corpo (`:1546`, `:1590`, `:1655`, `:1698`) e `load_config(percorso).analysis.material` (`:1548`, `:1595`, `:1659`, `:1744`). Idem `_catalogo_vero` (`:6521-6539`) e le prove del menù (`:6251-6844`, diciassette). Dopo il Task 3 sono rosse tre volte: 404 sulla rotta, 422 sulla PUT, `AttributeError` su `.analysis`. Quindi **il pannello esce in questa PR**, e per tenere verde ogni commit esce **prima** del Task 3, mentre rotta e blocco esistono ancora: togliere il pannello con le sue prove è verde da solo. Con il pannello escono qui anche etichette, aggancio, aiuto e CSS: **la PR 4 non ha più contenuto** e non si apre.

**Subagente: `frontend-engineer`**, un dispatch, un commit. Skill-gate **true**. Sequenziale: dopo il Task 2 (`/api/schema` serve già `export`, e la legenda va messa), prima del Task 3 (stesso `test_app_js.py`).

**Files:**
- Modify: `src/meshrec/ui/app.js:39` (descrizione dello step 11: «Scrive il deck .inp nudo per Abaqus: nodi, elementi, insiemi di nodi delle facce e un insieme di elementi per regione.»), `:213` (via il suffisso `corsa.materiale` / «materiale non dichiarato»: la riga della corsa mostra la sola nuvola), `:2725-2727` (commento su `analysis`), `:2854-3173` (`catalogoMateriali`, `nomeDellaClasse`, `valoriDellaClasse`, `pannelloMateriale`, `catalogoDeiMateriali`, `esitoDelMateriale` e i commenti che li introducono), `:3285` (`ETICHETTE_DEI_BLOCCHI`: via `analysis: "analisi"`, entra `export: "esportazione"`), `:3532-3538` (l'aggancio `voce.blocchi.includes("analysis")` e il commento)
- Modify: `src/meshrec/ui/stile.css:893-…` e `:917-…` (le due regole del riquadro «materiale»: leggere il blocco intero, togliere ciò che serviva solo a lui), `src/meshrec/ui/index.html:149-151` (aiuto: «Materiali, vincoli e carichi si assegnano in Abaqus sul deck.»)
- Test: `tests/test_app_js.py:1442-1821` **cancella** (`_banco_del_materiale`, `_ACCETTA_JS`, sei prove), `:6251-6844` **cancella** (`_catalogo_vero` e le diciassette prove del menù e delle avvertenze), `:1824-1875` togli `materiale: null` dalle due voci finte (facoltativo, ma il campo non esiste più), `:2191-2207` docstring senza `analysis` (la prova resta com'è: banco puro), `:3361-3388` se asserisce sul testo di `app.js:39`; **nuova**: la legenda del blocco `export` nel pannello 11 è «esportazione» (dallo schema servito, `test_server.py:2523` la copre lato server); `tests/test_stile.py` se asserisce sull'aiuto o sulle regole tolte; `grep -rn "materiali\|pannelloMateriale\|corsa.materiale" src/meshrec/ui/` → 0 righe a fine task

## Ingressi degeneri
- `/api/corse` con voci **senza** la chiave `materiale` (dal Task 3) o con `materiale: null` (server di oggi) → la riga della corsa mostra `nuvola` e basta, mai «materiale non dichiarato», mai `undefined`
- `/api/schema` con `export` fra i blocchi dello step 11 → legenda «esportazione», non `export` grezzo
- `voce.blocchi` senza `analysis` (dal Task 2) → nessun pannello montato, nessun errore in console (`read_console_messages` pulita all'apertura dello step 11)
- `campoParametro` su un blocco assente dalla configurazione → resta in sola lettura (`test_app_js.py:2191`, invariata)
- `fetch("/api/materiali")` → nessuna chiamata residua in `ui/*.js` (grep = 0)

- [ ] **Step 1**: prove — cancellazioni e la nuova sulla legenda; `uv run pytest tests/test_app_js.py -q` con `node` → la nuova rossa.
- [ ] **Step 2**: `app.js`, `stile.css`, `index.html`; `uv run pytest tests/test_app_js.py tests/test_stile.py tests/test_server.py -q` con `node` (senza `node` saltano 158 prove: dirlo nel report con `which node`).
- [ ] **Step 3**: commit `refactor(interfaccia): via il pannello del materiale; il blocco export ha la sua legenda`.

---

### Task 6: round di review e PR

Come la PR 1: `code-reviewer` (whole-branch, con triage dei Minor), `test-writer` (contratti per task, sotto), `craft-reviewer` (prosa: è la PR con più prosa di tutte, e ora anche l'interfaccia del Task 5), `spec-reviewer` (spec: «Il deck nudo», «La configurazione», «La prosa», «L'interfaccia» — la PR 4 è assorbita — «Sequenza» 2 e 4). `security-reviewer` non serve: nessuna superficie nuova, una rotta in meno. **In parallelo**, quattro dispatch in un messaggio. PR `feat/deck-nudo-analisi`, corpo con l'esito della corsa vera (rifiuto nominato + deck nudo + `md5` delle righe di mesh), merge `--squash` a CI verde su entrambe le piattaforme.

**Annotazione architect — Task 6.** Subagenti: i quattro revisori sopra, paralleli, sola lettura; thread principale per PR e merge. Skill-gate **true** per i revisori (ognuno ha le sue).

## Ingressi degeneri
- nessun ingresso esterno

## Ingressi degeneri (lista d'insieme; quelle vincolanti per i brief sono per task, sopra)

- yaml con `analysis:` (anche solo `analysis: null`) → `ValueError` che nomina `analysis`, la data 08/09/2026 e «`set_tolerance_factor` sta ora in `export`»; nessuna `PipelineConfig` costruita
- yaml con `carichi:` o `selettori:` → stesso rifiuto, che cita la PR #190
- yaml con `regioni.<nome>.materiale` → `ValueError` che nomina la regione e `materiale`
- yaml con `solutore:` → ignorato come oggi (fuori da `BLOCCHI_RIMOSSI`, salvo annotazione contraria)
- `export.set_tolerance_factor <= 0` o non finito → `ValidationError` alla lettura, nessun deck
- yaml senza `export:` → `set_tolerance_factor == 6.0`, deck scritto
- regione con zero elementi attribuiti → `RegioneVuotaWarning` che nomina la regione, `*ELSET` saltato, gli altri scritti, deck scritto
- nessuna regione → deck con `*HEADING`, `*NODE`, `*ELEMENT`, sei `*NSET` e nient'altro; `*NODE`/`*ELEMENT`/`*NSET` byte-identici al baseline `ba97f83b…`
- `write_inp(..., material=...)`, `fixed_nset=`, `gravity=`, `step_name=`, `print_nsets=`, `spostamenti_imposti=`, `carichi_nodali=` → `TypeError`, nessun ramo di compatibilità
- patch test con `ccx` → verde: le card che appende producono lo stesso campo di spostamento di prima (oracolo del patch test invariato)
- `export_model` su maglio vuoto → `ValueError` come oggi
- `meshrec init` → `argparse` rifiuta il comando («invalid choice»), nessun file scritto
- `GET /api/materiali` → 404
- corsa su disco con impronta vecchia dello step 11 → «non valido», rieseguibile; con `analysis:` nel suo `config.yaml` → la corsa non si apre finché il blocco non esce, e l'errore in `/api/corse` (`voce["errore"]`, `server.py:949-951`) dice quale blocco

## Self-review

- Spec «La configurazione», voce per voce: `analysis`/`carichi`/`selettori` via ✔ (Task 3 + PR 1); `Material`, `MaterialeDichiarato`, catalogo ✔ (Task 3); `lateral_*` ✔ (PR 1); `init` ✔ (Task 3); regioni con sola `membratura` ✔ (Task 2-3); `export` con `set_tolerance_factor` letto dallo step 11, `STEP_BLOCKS[11] = ("tet","export","regioni")` ✔ (Task 2); rifiuto nominato con blocco/data/PR/destinazione, niente migrazione, `extra="forbid"` non sufficiente ✔ (Task 3); impronte si muovono, registri intatti ✔ (decisione 7, corsa vera Task 2-3); yaml dei casi ✔ (Task 3).
- Spec «Il deck nudo»: card ✔ (Task 1); regione vuota → avviso ✔ (Task 1); modello parametrico con `*TIE`/`*SURFACE` senza sezioni ✔ (Task 1: `write_inp` unico); `mass` cade ✔ (Task 2); patch test si appende le card ✔ (Task 1).
- Spec «La prosa» ✔ (Task 4). «L'interfaccia» ✔ per intero (Task 5: pannello, etichette, aiuto; Task 2: `_FUORI_DAL_PANNELLO`; Task 3: rotta e `/api/corse`): la PR 4 è assorbita.
- Placeholder: le righe dei file sono quelle di `main` 8004950 lette oggi; dove il piano non ha la riga usa un `grep` con i nomi esatti. La `description` di `ExportConfig.set_tolerance_factor` si copia da `AnalysisConfig` (indicata la riga), non si inventa.
- Coerenza: `ExportConfig`/`cfg.export`/`export_model(cfg: ExportConfig)` uguali in Task 1-3; `SET_DI_BASE` definita in Task 2 e usata dai controlli di copertura; `RegioneVuotaWarning` definita in Task 1 e provata in Task 2.
