# Deck nudo, PR 1 di 4 — via carichi e selettori: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il deck del muro torna alla forma precedente alla Fase 5 — materiale unico, `*BOUNDARY`, un solo passo di gravità — perché carichi, selettori e pressione laterale escono da configurazione, deck e interfaccia.

**Architecture:** cancellazione dall'alto dello stack verso il basso, suite verde a ogni commit. Prima la pipeline smette di passare carichi, selettori e pressione al deck; poi `abaqus.py` perde i parametri, i blocchi di scrittura e le funzioni che servivano solo a loro, e `selezione.py` resta senza chiamanti e si cancella; infine la configurazione perde classi, campi e validatori, e con lei `steps.py`, `sweep.py`, le etichette dell'interfaccia e i file di caso. Ciò che il patch test usa (`spostamenti_imposti`, `carichi_nodali`, `print_nsets`) **resta** in questa PR: esce nella PR 2 insieme a `*BOUNDARY` e `*STEP`.

**Tech Stack:** Python 3.12, pydantic 2, numpy, pytest; `node` e `ccx` sul PATH per la forma onesta della suite.

**Spec:** `docs/superpowers/specs/2026-09-07-deck-nudo-e-step-dal-prior-design.md` (sezioni «Il deck nudo», «La configurazione», «Sequenza» punto 1). ADR: `docs/adr/2026-09-07-deck-nudo-via-analisi-carichi-selettori.md`. Glossario: `CONTEXT.md`.

## Global Constraints

- Tutti i comandi dalla cartella `meshrec/`, con `uv run`. Percorsi assoluti dentro i comandi; `git -C /Users/mario/GitHub/Tesi` al posto di `cd`.
- **Il verde che mente** (`AGENTS.md`): la suite onesta è `uv run pytest -m "" -q`, con `node` e `ccx` sul PATH; la forma breve `uv run pytest -q` esclude `feasibility` e `validazione`. Ogni task chiude con la forma onesta.
- Un esito **discreto** che dipende dalla piattaforma è un difetto; le grandezze continue si confrontano con tolleranza relativa.
- Ogni numero mostrato ha un controllo che lo contraddice se il risultato peggiora: una misura senza controllo non si aggiunge.
- Messaggi di commit in italiano, Conventional Commits, corpo che dice il perché.
- Unità in un punto solo: mm, N, MPa, t, s.
- Non toccare: `spostamenti_imposti`, `carichi_nodali`, `print_nsets`, `fixed_nset`, `gravity`, `step_name`, `_gradi_da_scrivere`, `NOMI_PASSO_RISERVATI`, `_materiali_del_deck`, il blocco `analysis`, le `regioni` con materiale, `tests/test_condizioni_imposte.py`, `tests/validazione/`. Sono della PR 2.
- Non toccare `ties`, `element_surfaces`, `tie_surface`, `element_surface`, `surface_area`, `aree_tributarie`, `_facce_di_bordo`, `fix_sign`: servono al modello parametrico (`*TIE`/`*SURFACE`) e a `wall.py`.

---

### Task 0: ramo e baseline della suite

**Files:**
- nessuno modificato

> **Annotazione architect (07/09/2026, su `main` 896c751).**
> - Subagente: **thread principale**. Nessun dispatch.
> - Sequenza: primo, da solo. Il numero di baseline e' l'oracolo di tutti i task dopo.
> - Skill-gate: **false** — due comandi git e un `pytest`, niente da progettare.
>

## Ingressi degeneri
- nessun ingresso esterno (non scrive codice)

- [ ] **Step 1: ramo da `main` aggiornato**

```bash
git -C /Users/mario/GitHub/Tesi checkout main
git -C /Users/mario/GitHub/Tesi pull --ff-only
git -C /Users/mario/GitHub/Tesi checkout -b feat/deck-nudo-carichi
```

- [ ] **Step 2: baseline della suite onesta**

Run: `uv run pytest -m "" -q 2>&1 | tail -3`
Expected: verde. Annotare il numero di test passati e saltati (il 02/09/2026 erano 1269 nella forma breve; senza `node` ne saltano 158, senza `ccx` 3). Questo numero è il termine di confronto dei task successivi: ogni test che sparisce deve sparire perché cancellato qui, non perché saltato.

---

### Task 1: la pipeline smette di passare carichi, selettori e pressione

**Files:**
- Modify: `src/meshrec/core/pipeline.py:349-358` (`genera_modello`: `carico` e il suo passaggio a `export_model`)
- Modify: `src/meshrec/core/pipeline.py:840-842` (step 11: `carichi=cfg.carichi, selettori=cfg.selettori`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `abaqus.export_model(..., carichi=None, selettori=None, pressure=None, ...)` — oggi accetta `None` per tutti e tre (default), quindi togliere gli argomenti dal chiamante non cambia il deck di una corsa senza carichi.
- Produces: `pipeline.run` e `pipeline.genera_modello` chiamano `export_model` senza `carichi`, `selettori`, `pressure`. Dal Task 2 quei parametri non esisteranno più.

> **Annotazione architect.**
> - Subagente: **`backend-engineer`** (pipeline + test, nessuna UI).
> - Sequenza: dopo Task 0, prima di Task 2 — Task 2 toglie i parametri che qui smettono di essere passati; invertire l'ordine rompe la suite fra i due commit. Dentro il task tutto sequenziale (Step 3 e 4 toccano lo stesso file).
> - Skill-gate: **true** su Step 1-2 (TDD: il test di regressione si scrive e si esegue prima di toccare il codice). **false** su Step 3-4-5 (cancellazioni meccaniche di righe nominate: nessuna skill, si cancella e si rilancia la suite). Step 6-7: verifica e commit, nessuna skill oltre `caveman-commit`.
> - Step 5, prove da cancellare — verificate con scansione AST su `main`, non a grep: `tests/test_pipeline.py:1380` `test_lo_step_11_passa_i_selettori` (dopo Step 3 fallisce: e' la prova della mutazione che questo task esegue di proposito) e `tests/test_pipeline.py:1409` `test_il_percorso_esaedrico_non_riceve_selettori` (dopo Step 3 **passa per il motivo sbagliato**: asserisce `"selettori" not in visti` e nessuno passa piu' `selettori` a nessuno — si cancella, non si lascia). Altre prove di `test_pipeline.py` su `carichi`/`lateral_pressure`: nessuna.
>

## Ingressi degeneri
- config senza `carichi:` ne' `selettori:` → deck con un solo `*STEP`, `*NODE`/`*ELEMENT`/sei `*NSET` identici a prima (Step 1 lo fissa)
- config **con** `carichi:` o `selettori:` (yaml vecchio, es. `runs/geoandgeo-lab/config.yaml:66,80`) → `pipeline.run` esegue, il blocco resta in `cfg` e nessuno lo legge: nessuna eccezione, deck a un passo
- `cfg.model.lateral_nset` e `lateral_pressure` entrambi dichiarati → `genera_modello` li ignora: nessun `*DSLOAD` nel deck figlio, nessun `pressure` in `metrics`
- percorso esaedrico (`hexa`) con `element_surfaces` e `ties` → `*SURFACE` e `*TIE` ancora nel deck (`tests/test_pipeline.py:157` resta verde)

- [ ] **Step 1: scrivere il test che fissa il comportamento**

In `tests/test_pipeline.py`, accanto alle prove dello step 11 sul cubo sintetico (cerca `def test_` che leggono `wall_model.inp` con `tmp_path`), aggiungere:

```python
def test_il_deck_dello_step_11_porta_un_solo_passo(tmp_path):
    """Dalla PR 1 del deck nudo la pipeline non passa piu' carichi al deck:
    un solo *STEP (la gravita'), nessun *CLOAD, nessun *DSLOAD, nessuna
    *SURFACE nel deck del muro."""
    cfg = _config_del_cubo(tmp_path)          # usa la fixture/helper che le prove vicine gia' usano
    pipeline.run(cfg)
    deck = (tmp_path / "wall_model.inp").read_text()
    assert deck.count("*STEP") == 1
    assert "*CLOAD" not in deck
    assert "*DSLOAD" not in deck
    assert "*SURFACE" not in deck
```

Sostituire `_config_del_cubo` con l'helper che il file usa davvero per costruire una `PipelineConfig` sul cubo sintetico (leggere le prime prove dello step 11 nel file: ne esiste già uno, non crearne un secondo).

- [ ] **Step 2: eseguire il test, deve passare già**

Run: `uv run pytest tests/test_pipeline.py -k un_solo_passo -q`
Expected: PASS (la config del cubo non dichiara carichi). È un test di regressione, non un test rosso: fissa il contratto prima di togliere il codice.

- [ ] **Step 3: togliere il passaggio dei carichi nello step 11**

In `src/meshrec/core/pipeline.py:840-842`, dentro la chiamata `abaqus.export_model(...)` dello step 11, cancellare le due righe:

```python
            carichi=cfg.carichi,
            selettori=cfg.selettori,
```

Lasciare `reference=vertices` e `regioni=regioni_deck`.

- [ ] **Step 4: togliere la pressione laterale dal modello parametrico**

In `src/meshrec/core/pipeline.py:349-358` (`genera_modello`), cancellare:

```python
    carico = None
    if cfg.model.lateral_nset is not None and cfg.model.lateral_pressure is not None:
        carico = (cfg.model.lateral_nset, float(cfg.model.lateral_pressure))
```

e nella chiamata `abaqus.export_model(...)` subito sotto togliere l'argomento `pressure=carico`. Lasciare `ties=` ed `element_surfaces=`.

- [ ] **Step 5: cancellare le prove della pipeline sui carichi**

Cancellare intere le due funzioni `test_lo_step_11_passa_i_selettori` (`tests/test_pipeline.py:1380-1406`) e `test_il_percorso_esaedrico_non_riceve_selettori` (`1409-1440`). Sono le sole due: verificato con scansione AST su `main` 896c751. La riga `test_pipeline.py:157` sulla superficie chiusa del modello parametrico **resta**: prova `*TIE`/`*SURFACE`, non un carico. Controllo finale: `grep -n "carichi\|selettori\|lateral_pressure\|casi_di_carico" tests/test_pipeline.py` vuoto.

- [ ] **Step 6: suite verde**

Run: `uv run pytest tests/test_pipeline.py tests/test_hexa.py -q`
Expected: PASS. Poi `uv run pytest -m "" -q 2>&1 | tail -3`: verde, con il conteggio della baseline meno le prove cancellate.

- [ ] **Step 7: commit**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/core/pipeline.py meshrec/tests/test_pipeline.py
git -C /Users/mario/GitHub/Tesi commit -m "refactor(pipeline): lo step 11 non passa piu' carichi ne' selettori al deck

Prima PR del deck nudo (spec 2026-09-07). Il deck del muro torna al solo
passo di gravita'; il modello parametrico perde la pressione laterale.
abaqus.py accetta ancora i parametri: escono col prossimo commit."
```

---

### Task 2: `abaqus.py` perde carichi, selettori e pressione; `selezione.py` si cancella

**Files:**
- Modify: `src/meshrec/core/abaqus.py` — firme di `write_inp` (324-344) e `export_model` (1959-1973); blocchi 540-569, 687-695, 704-767, 778-800, 812-853; 2066, 2075-2122, 2144-2200, 2206-2214, 2215-2232; funzioni `_passo_statico` (122-208, solo il parametro `pressure`), `_Azione` (210-226), `_riga_scalata` (229-292), `superficie_di_pressione` (1034-1134), `ripartisci` (1263-1333), `coppia_equivalente` (1335-1384); classi `CaricoSulVincoloWarning` (77), `SelettoreIsotropoWarning` (81); l'import di `selezione`
- Modify: `src/meshrec/ui/etichette.js:198-199` — le etichette `"pressure"` e `"casi_di_carico"` della tabella dello step 11: chiavi che il deck non produce piu' (nessun test le lega, ma un'etichetta senza metrica e' sedimento)
- Delete: `src/meshrec/core/selezione.py`, `tests/test_selezione.py`, `tests/test_carichi_distribuiti.py`
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: le chiamate dei Task 1 (nessun `carichi`, `selettori`, `pressure`).
- Produces: `write_inp(path, nodes, elements, *, node_sets, material, element_type="C3D4", fixed_nset="BASE", print_nsets=(), gravity=GRAVITY_MM_S2, elset="ALL_WALL", regioni=None, step_name="GRAVITA", element_surfaces=None, ties=(), spostamenti_imposti=None, carichi_nodali=None) -> dict`; `export_model(path_inp, path_vtu, nodes, elements, cfg, tet_cfg, reference=None, element_type=None, element_surfaces=None, ties=(), regioni=None) -> dict`. Il dizionario reso da `export_model` non ha più le chiavi `casi_di_carico`, `carichi_posizionati`, `carichi_distribuiti`, `selettori`, `pressure` (la chiave si chiama `pressure`, `abaqus.py:2213`, non `pressione`); conserva `ties`/`surface_area`/`element_surfaces` (superfici di `*TIE`), `volume`, `mass`, `node_sets`, `extent`, `base_coverage`, l'allineamento.

> **Annotazione architect.**
> - Subagente: **`backend-engineer`**, in **due dispatch** (2a, 2b) — vedi stima sotto. `etichette.js` e' due righe da togliere: resta a `backend-engineer`, non serve `frontend-engineer`.
> - Sequenza: dopo Task 1, prima di Task 3. **2a → 2b**, ogni meta' chiude con la suite onesta verde e un commit.
>   - **2a — solo prove** (Step 7 + `git rm` dei due file di test + commit `test(abaqus): via le prove dei carichi e dei selettori`). Cancella prove senza toccare codice: la suite non puo' che restare verde. Commit a se', il messaggio dice che il codice esce col commit successivo.
>   - **2b — codice** (Step 1 → 6, poi 8, 9). Il test nuovo dello Step 1 e' rosso finche' `casi_di_carico` esiste, verde dopo Step 5.
>   - 2a e' indipendente da Task 1 per file (test_abaqus.py contro pipeline.py/test_pipeline.py) e potrebbe correre in parallelo; su un ramo solo con commit in serie non conviene: sequenziale.
> - Skill-gate: **true** su 2b Step 1-2 (TDD, prova rossa prima del codice) e su 2b Step 4-5 (cancellazione dentro funzioni vive, `write_inp`/`export_model`: leggere il ramo prima di tagliarlo, `_passo_statico` resta chiamato dal patch test). **false** su 2a (cancellazioni di funzioni intere, nominate una per una) e su 2b Step 3, 6 (firme e funzioni senza chiamanti).
> - Metodo per 2a, vincolante: **uno script `ast`**, non 66 chiamate `Edit`. Lo script legge `tests/test_abaqus.py`, trova le `def` di primo livello per nome, cancella `[lineno, end_lineno]` dal basso verso l'alto, riscrive il file. Una chiamata Bash, nessuna eco del testo cancellato nel contesto. La riga vuota doppia che resta la sistema `ruff format` se e' configurato, altrimenti si lascia.
> - **Stima (il perche' dei due dispatch).** `abaqus.py` 2233 righe, `test_abaqus.py` 3579 righe (`wc -l` su `main` 896c751). Da cancellare in `test_abaqus.py`: **66 `def` per ~1570 righe** (scansione AST, `scan.py` in scratchpad), non 32 come il piano scriveva; in `abaqus.py` ~640 righe fra funzioni e blocchi, piu' `selezione.py` 206 righe. Leggere entrambi i file per intero costa ~80K token di solo input; 66 `Edit` con `old_string` di una funzione intera li raddoppiano. In una sessione da 100K non entra. Spezzato in 2a (script, ~15K) e 2b (lettura mirata di ~700 righe di `abaqus.py` + edit, ~50K) entra con margine.
>

## Ingressi degeneri
- `write_inp(..., carichi=...)`, `write_inp(..., pressure=...)`, `write_inp(..., nset_selettori=...)`, `export_model(..., selettori=...)` → `TypeError` di Python per argomento inatteso, nessun ramo di compatibilita' (`tests/test_condizioni_imposte.py:83-117` chiama `write_inp` senza quei kwarg e resta verde)
- `export_model` su maglio vuoto (zero elementi) → `ValueError` come oggi (`fix` 5b954c4, c731120: la guardia sta prima dei carichi e non si tocca)
- `ties` che nominano una superficie con grafia diversa (`pelle` contro `PELLE`) → risolta col casefold e `*TIE` scritto (`fix` 676cf07: la meta' `*TIE` della prova `test_abaqus.py:1300` resta, cade solo la meta' `pressure`)
- `ties` che nominano una superficie mai dichiarata → `ValueError` che nomina la superficie, deck non scritto (`test_abaqus.py:1335`, meta' `ties`)
- `carichi_nodali={}` o `spostamenti_imposti=None` → nessun `*CLOAD`/`*BOUNDARY` extra, deck del solo peso proprio (`test_condizioni_imposte.py:106`)
- `carichi_nodali` con una componente sotto `SOGLIA_COMPONENTE_RELATIVA` o direzione tutta nulla → `_gradi_da_scrivere` la filtra come oggi (`test_abaqus.py:2878-2925` restano)
- `element_surfaces` senza `ties` → `*SURFACE` scritta, `metrics["surface_area"]` con l'area, nessuna chiave `pressure`

- [ ] **Step 1: la prova del deck a un passo, sul maglio sintetico**

In `tests/test_abaqus.py`, accanto a `test_export_model_writes_both_files_and_reports_mass` (riga 491), aggiungere:

```python
def test_il_deck_del_muro_porta_il_solo_passo_di_gravita(tmp_path):
    """Deck nudo, PR 1: nessun carico oltre il peso proprio. Un *STEP, nessun
    *CLOAD ne' *DSLOAD ne' *SURFACE ne' *FREQUENCY; niente chiave dei casi
    di carico nelle metriche."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_LINEARE)
    metrics = abaqus.export_model(
        tmp_path / "wall_model.inp", tmp_path / "wall_model.vtu",
        nodes, tets, config.AnalysisConfig(material=MATERIALE), TET_LINEARE,
    )
    deck = (tmp_path / "wall_model.inp").read_text()
    assert deck.count("*STEP") == 1
    for card in ("*CLOAD", "*DSLOAD", "*SURFACE", "*FREQUENCY"):
        assert card not in deck
    assert "casi_di_carico" not in metrics
    assert "selettori" not in metrics
```

- [ ] **Step 2: eseguirla, deve fallire**

Run: `uv run pytest tests/test_abaqus.py -k solo_passo_di_gravita -q`
Expected: FAIL su `assert "casi_di_carico" not in metrics` (oggi `export_model` rende la lista ordinata dei passi anche senza carichi).

- [ ] **Step 3: togliere i parametri dalle firme**

In `write_inp` (`abaqus.py:324-344`) cancellare i parametri `pressure`, `carichi`, `nset_selettori`. In `export_model` (`abaqus.py:1959-1973`) cancellare `pressure`, `carichi`, `selettori`. Aggiornare le docstring dove nominano i tre (in `export_model` il paragrafo «`carichi` e' un parametro a se'…» cade intero). Nell'`import` da `meshrec.core.config` (`abaqus.py:14-23`) togliere `CarichiConfig`, `Momento`, `Selettore` — sono i tipi delle firme e di `coppia_equivalente`; lasciati, il Task 3 romperebbe l'import di `abaqus.py` cancellando le classi. Restano `GRAVITY_MM_S2`, `AnalysisConfig`, `Material`, `TetConfig`, `_mappa_casefold` (casefold dei `ties`).

- [ ] **Step 4: togliere i blocchi di scrittura dei carichi in `write_inp`**

Cancellare, nell'ordine dal basso verso l'alto per non spostare i numeri di riga mentre si lavora:

- 847-853: il passo `MODALE` (`*FREQUENCY`)
- 812-845: il ciclo delle combinazioni
- 778-800: il ciclo dei passi dei carichi distribuiti
- 735-767: il ciclo dei carichi posizionati
- 704-730: il carico in sommità (`CARICO_TOP`)
- 687-695: la spinta orizzontale
- il dizionario `azioni_del_deck` e la sua riga `azioni_del_deck[step_name] = _Azione(dload=(peso,))` (≈ 680-684): cancellare; lasciare `peso = ...` e `lines += passo_statico(step_name, [peso])`
- il dizionario `resoconto` (≈ 697-702) se dopo le cancellazioni nessuno lo riempie più: cancellarlo e togliere la sua chiave dal `return`
- 540-569: il blocco `carichi.distribuiti` che chiama `superficie_di_pressione` e riempie `superfici`/`resoconti_distribuiti`; **attenzione**: `superfici` è riempito anche da `element_surfaces` (le superfici di `*TIE` del modello parametrico): lasciare quella parte, togliere solo il ramo dei carichi distribuiti e `resoconti_distribuiti`
- il ciclo `for name, indices in (nset_selettori or {}).items()` che scrive un `*NSET` per selettore (≈ 583-590)
- in `functools.partial(_passo_statico, ...)` (≈ 672-676) togliere `pressure=pressure`

Poi in `_passo_statico` (122-208) cancellare il parametro `pressure` e il ramo che scrive `*DSLOAD` (con il commento lungo su `OP=NEW`). Lasciare `carichi_nodali` e il ramo `*CLOAD` delle forze nodali (serve al patch test).

- [ ] **Step 5: togliere i blocchi in `export_model`**

- 2215-2232: la costruzione di `casi_di_carico` e la sua chiave nel dizionario reso
- 2206-2214: lasciare le voci `element_surfaces`, `surface_area` (`surface_area(aligned, elements, coppie, tipo)`) e `ties`; togliere la voce `"pressure"` (`abaqus.py:2213`). In `src/meshrec/ui/etichette.js:198-199` togliere le due etichette `"pressure"` e `"casi_di_carico"` della tabella dello step 11.
- 2161-2200: le chiavi `carichi_posizionati`, `carichi_distribuiti`, `selettori` (con la bbox dei nodi presi)
- 2144-2160: nella chiamata a `write_inp` togliere `pressure=`, `carichi=`, `nset_selettori=`
- 2075-2122: il controllo «carico sul vincolo» (`vincolati`, `carichi_da_controllare`, `CaricoSulVincoloWarning`); **lasciare** il calcolo di `base_coverage` e `UnconstrainedModelWarning`, che riguardano il set vincolato e non un carico
- 2066: `nset_selettori = selezione.risolvi_tutti(...)` e il commento sopra

- [ ] **Step 6: cancellare le funzioni e le classi senza più chiamanti**

Run: `grep -n "ripartisci(\|coppia_equivalente(\|superficie_di_pressione(\|_riga_scalata(\|_Azione\|CaricoSulVincoloWarning\|SelettoreIsotropoWarning\|selezione\." src/meshrec/core/abaqus.py src/meshrec/core/*.py src/meshrec/app/*.py`
Expected: solo le definizioni. Poi cancellare in `abaqus.py`: `coppia_equivalente` (1335-1384), `ripartisci` (1263-1333), `superficie_di_pressione` (1034-1134), `_riga_scalata` (229-292), `_Azione` (210-226), `SelettoreIsotropoWarning` (81-83), `CaricoSulVincoloWarning` (77-79), l'`import` di `selezione` in testa al modulo e il commento 50-52 che parla della riga `*CLOAD` più grande. Lasciare `_gradi_da_scrivere` (85-111: lo usa il ramo delle forze nodali), `aree_tributarie`, `surface_area`, `element_surface`, `tie_surface`, `_facce_di_bordo`, `fix_sign`, `_materiali_del_deck`, `UnconstrainedModelWarning`.

Poi:

```bash
git -C /Users/mario/GitHub/Tesi rm meshrec/src/meshrec/core/selezione.py
```

(I due file di test sono gia' usciti col commit 2a.)

- [ ] **Step 7: cancellare le prove di `test_abaqus.py` sui carichi** (= Task 2a, primo commit)

> Corretto dall'architect: l'elenco originale di 32 righe era sbagliato in 7 voci su 32 (1148, 1361, 1386, 1430, 1449, 1471 provano `*TIE`/`tie_surface` e **restano**; 1300 e' mista e si riscrive) e ne mancavano ~40 (i test di `ripartisci`, dei momenti, delle combinazioni). Elenco qui sotto da scansione AST su `main` 896c751: ogni `def` di primo livello il cui corpo cita carichi/selettori/pressione/`ripartisci`/`coppia_equivalente`/`Momento`/combinazioni.

**Cancellare intere, con lo script `ast` (una chiamata), queste 66 `def` (riga di inizio su `main`):**

`griglia_mesh` 74 (fixture usata solo da prove che cadono: 2612, 2661, 2800, 3536) · 376 · 423 · 447 · 475 · 514 · 535 · 1130 · 1590 · 1627 · 1640 · 1657 · 1692 · 1709 · `_con_posizionati` 1738 · 1785 · 1803 · 1817 · 1835 · 1855 · 1878 · 1896 · 1918 · 1948 · 1972 · 2015 · 2045 · 2070 · 2095 · 2127 · 2154 · 2196 · 2221 · 2243 · 2262 · 2291 · 2323 · 2351 · 2375 · 2407 · 2447 · 2479 · 2500 · 2529 · 2544 · 2577 · 2612 · 2639 · 2661 · 2694 · 2730 · 2761 · `_con_box` 2781 · 2800 · 2823 · 2839 · 2928 · `_deck_con_combinazioni` 3360 · 3380 · 3401 · 3424 · 3437 · 3450 · 3472 · 3490 · 3536.

**Riscrivere (tolgono la meta' `pressure`, tengono la meta' `*TIE`/`*SURFACE`):**
- 1107 `test_la_superficie_esportata_ha_l_area_delle_facce_che_dichiara`: togliere `pressure=("FACCIA_BASSA", 0.25)` dalla chiamata; l'asserzione sull'area resta.
- 1300 `test_tie_e_pressione_risolvono_le_superfici_ignorando_le_maiuscole`: togliere `pressure=("PeLLe", 0.25)` e le asserzioni su `*DSLOAD`; rinominare senza «e_pressione»; la docstring parla del solo `*TIE`.
- 1335 `test_una_superficie_mai_dichiarata_resta_un_rifiuto_anche_col_casefold`: togliere la seconda chiamata `write_inp` (quella con `pressure=("MAI_DICHIARATA", 0.25)`); resta la prima, sui `ties`.

**Solo docstring (citano carichi o momenti come contesto, provano altro):** 1386 (`*TIE` senza tolleranza), 1409 (`element_surface`, cita «carico laterale»), 2912 (`_gradi_da_scrivere`, cita `Momento`).

**Restano intere:** 1148, 1361, 1430, 1449, 1471 (`*TIE`/`tie_surface`), 2878-2925 (`_gradi_da_scrivere`), tutte le prove su `spostamenti_imposti`, `carichi_nodali`, `regioni`, `_materiali_del_deck`, `UnconstrainedModelWarning`. Le costanti d'appoggio (`MATERIALE`, `TET_LINEARE`, `_CUBO`, `_ESAEDRO`, `cube_mesh`) restano.

Poi `git -C /Users/mario/GitHub/Tesi rm meshrec/tests/test_selezione.py meshrec/tests/test_carichi_distribuiti.py`.

Verifica: `grep -n "carichi\b\|selettor\|spinta\|carico_sommita\|combinazion\|superficie_di_pressione\|ripartisci\|coppia_equivalente\|pressure=\|Momento" tests/test_abaqus.py`
Expected: nessuna occorrenza, salvo `carichi_nodali`. Poi `uv run pytest tests/test_abaqus.py -q` verde (nessun codice e' cambiato) e commit `test(abaqus): via le prove dei carichi, dei selettori e della pressione` con corpo che dice che il codice esce col commit successivo.

- [ ] **Step 8: la prova nuova passa e la suite è verde**

Run: `uv run pytest tests/test_abaqus.py tests/test_hexa.py tests/test_condizioni_imposte.py -q`
Expected: PASS, compreso `test_il_deck_del_muro_porta_il_solo_passo_di_gravita`. Poi `uv run pytest -m "" -q 2>&1 | tail -3`: verde; il patch test in `tests/validazione/` gira ancora con `ccx`.

- [ ] **Step 9: commit**

```bash
git -C /Users/mario/GitHub/Tesi add -A meshrec/src/meshrec/core meshrec/src/meshrec/ui/etichette.js meshrec/tests/test_abaqus.py
git -C /Users/mario/GitHub/Tesi commit -m "refactor(abaqus): il deck scrive il solo passo di gravita'

Escono carichi posizionati e distribuiti, spinta, carico in sommita',
modale, combinazioni, selettori e pressione laterale: il tutor li assegna
in Abaqus (spec 2026-09-07, ADR deck nudo). selezione.py resta senza
chiamanti e si cancella. Restano le forze nodali e gli spostamenti
imposti del patch test, e le superfici di *TIE del modello parametrico."
```

---

### Task 3: la configurazione perde carichi, selettori e pressione laterale

**Files:**
- Modify: `src/meshrec/core/config.py:396-406` (`Natura`, `DESCRIZIONE_NATURA`), `409-515` (`SpintaOrizzontale`, `CaricoSommita`, `Modale`), `904-926` (`ModelConfig.lateral_nset`, `lateral_pressure`, `_carico_completo_o_assente`), `954-1214` (selettori, `Momento`, `CaricoPosizionato`, `CaricoDistribuito`, `Combinazione`, `CarichiConfig`), `1343-1351` (campi `carichi`, `selettori`), `1367-1381` (validatore selettori/facce), `1404-1479` (validatore carichi→selettori)
- Modify: `src/meshrec/core/steps.py:67`
- Modify: `src/meshrec/core/sweep.py:38-48, 71-72, 92`
- Modify: `src/meshrec/app/server.py:625, 1475, 1521`
- Modify: `src/meshrec/ui/app.js:3285`
- Modify: `casi/lab_telaio.yaml:92` (blocco `carichi:`) e `casi/lab_telaio.yaml:128-129` (`lateral_nset: null`, `lateral_pressure: null` dentro `model:` — il piano originale le dimenticava)
- Delete: `lab_telaio_v4_posizionati.yaml`, `lab_telaio_v4_posizionati_top.yaml` (radice di `meshrec/`: esistevano per i carichi posizionati della Fase 6)
- Test: `tests/test_config.py`, `tests/test_steps.py`, `tests/test_sweep.py`, `tests/test_server.py`; solo docstring in `tests/test_materiali.py:319`. **Non** `test_hexa.py`, `test_ingresso.py`, `test_worker.py`, `test_report.py`, `test_cli.py`, `test_wall.py`, `tests/materiale.py`, `test_app_js.py`: la scansione AST su `main` 896c751 non vi trova nessuna prova che costruisca o asserisca su carichi/selettori/`lateral_*` (i loro `grep` prendono «selettore» CSS o del file picker, «bimodale», «combinazione» in altro senso).

**Interfaces:**
- Consumes: niente in `core/` legge più `cfg.carichi`, `cfg.selettori`, `cfg.model.lateral_*` (Task 1 e 2).
- Produces: `PipelineConfig` senza `carichi` e `selettori`; `ModelConfig` senza `lateral_nset` e `lateral_pressure`; `STEP_BLOCKS[11] == ("tet", "analysis", "regioni")`; `sweep.BLOCCHI_VUOTI_FUORI_IMPRONTA == ("regioni",)`. Un yaml che dichiara `carichi:` o `selettori:` **passa ancora** in questa PR perché `_ModelloBase` non vieta i campi ignoti (`config.py:124`: `ConfigDict(allow_inf_nan=False)`, nessun `extra=`, quindi il predefinito pydantic `ignore` — verificato): il rifiuto nominato arriva nella PR 2 con `BLOCCHI_RIMOSSI`. Lo si dichiara nel commit.

> **Annotazione architect.**
> - Subagente: **`backend-engineer`**. `app.js:3285` e' una riga di etichette: non giustifica `frontend-engineer`.
> - Sequenza: dopo Task 2b, ultimo dei tre. Dentro il task: Step 3 (`config.py`) e Step 4 (`steps.py`, `sweep.py`, `server.py`, `app.js`, yaml) toccano file disgiunti e potrebbero correre in parallelo, ma la suite e' verde solo con entrambi fatti e sono pochi minuti ciascuno: un agente, in serie, Step 3 → 4 → 5.
> - Skill-gate: **true** su Step 1-2 (TDD, due prove rosse) e su Step 5 (le prove da **riscrivere**, non cancellare: richiedono di capire cosa provano — vedi elenco). **false** su Step 3, 4 (cancellazioni di classi/campi/righe nominate con la riga), Step 6-8 (verifica, corsa vera, commit).
> - **Trappola dello Step 1**: `tests/test_steps.py:12` importa `SelettoreSfera` a livello di modulo. Cancellare la classe senza toccare quell'import fa sparire l'intero file di prove per `ImportError`, non una prova sola. Insieme all'asserzione di riga 195 vanno tolti l'import e le due prove `test_cambiare_i_carichi_invalida_dall_undici_in_giu` (154-169) e `test_cambiare_un_selettore_invalida_lo_step_11` (172-183); `test_cambiare_una_regione_invalida_lo_step_11` (186-215) resta con l'asserzione di riga 195 aggiornata.
>

## Ingressi degeneri
- yaml con `carichi:` o `selettori:` popolati (come `runs/geoandgeo-lab/config.yaml:66,80`) → `load_config` restituisce una `PipelineConfig` senza quegli attributi (`not hasattr(cfg, "carichi")`), nessuna eccezione — estendere `test_config.py:1115` `test_una_configurazione_si_rilegge_con_e_senza_i_blocchi_che_non_esistono_piu`, che gia' fa lo stesso per `solutore:`, invece di scrivere una prova nuova
- yaml con `model.lateral_nset`/`lateral_pressure` (anche `null`) → ignorati, `ModelConfig` si costruisce
- yaml con due chiavi omonime dentro `regioni:` → `ValueError` che nomina la chiave (`test_config.py:100` oggi lo prova su `selettori:`: si riscrive su `regioni:`, la guardia `_LoaderChiaviUniche` resta)
- `PipelineConfig()` minima → `regioni == {}`, `model_fields` senza `carichi`/`selettori`, `set(BLOCCHI_VUOTI_FUORI_IMPRONTA) <= set(model_fields)` (`test_config.py:309` si riscrive con `{"regioni"}`)
- corsa su disco con impronta dello step 11 calcolata con i blocchi vecchi → `run_state` la dichiara «non valido» dallo step 11 in giu', non «valido» ne' errore; i registri di `experiments/` non si muovono (`test_sweep.py:924` confronta cartella e impronta **registrata**, non ricalcolata: resta verde)
- `/api/schema` per lo step 11 → 200, `corpo["11"]["blocchi"] == ["analysis"]`, nessuna chiave `carichi`/`selettori` (`test_server.py:2523` si riscrive nell'asserzione su `STEP_BLOCKS[11]`; `2575` si cancella perche' passerebbe per il motivo sbagliato)
- `regioni` con una sola regione dichiarata → entra nell'impronta e i pannelli la mostrano come oggi (`test_config.py:1194`, `test_server.py:3676` restano; solo docstring da aggiornare)

- [ ] **Step 1: la prova sulla tabella degli step**

In `tests/test_steps.py`: togliere `SelettoreSfera` dall'import di riga 12; cancellare intere `test_cambiare_i_carichi_invalida_dall_undici_in_giu` (154-169) e `test_cambiare_un_selettore_invalida_lo_step_11` (172-183); in `test_cambiare_una_regione_invalida_lo_step_11` (186-215) sostituire l'asserzione di riga 195 con la tupla nuova. Poi aggiungere:

```python
def test_lo_step_11_legge_tet_analysis_e_regioni():
    """Dalla PR 1 del deck nudo carichi e selettori non esistono piu': lo
    step 11 non puo' dichiarare di leggerli."""
    assert steps.STEP_BLOCKS[11] == ("tet", "analysis", "regioni")
```

e in `tests/test_config.py` aggiungere:

```python
def test_pipeline_config_non_ha_piu_carichi_ne_selettori():
    campi = set(config.PipelineConfig.model_fields)
    assert "carichi" not in campi
    assert "selettori" not in campi
    assert not hasattr(config, "CarichiConfig")
    assert not hasattr(config, "Selettore")
    assert "lateral_pressure" not in config.ModelConfig.model_fields
```

- [ ] **Step 2: eseguirle, devono fallire**

Run: `uv run pytest tests/test_steps.py tests/test_config.py -k "tet_analysis_e_regioni or non_ha_piu_carichi" -q`
Expected: FAIL (i campi esistono ancora).

- [ ] **Step 3: cancellare in `config.py`, dal basso verso l'alto**

- 1404-1479: `_i_carichi_col_selettore_citano_selettori_dichiarati`
- 1367-1381: `_i_nomi_dei_selettori_non_collidono_coi_sei` (**lasciare** 1383-1402, il validatore delle regioni contro `ALL_WALL`)
- 1343-1351: i campi `carichi` e `selettori` di `PipelineConfig`
- 954-1214: `SelettoreBox`, `SelettoreSfera`, `SelettoreNodo`, `SelettoreNset`, `Selettore`, `Momento`, `CaricoPosizionato`, `CaricoDistribuito`, `Combinazione`, `CarichiConfig`. **Lasciare** `NOMI_SET_DI_FACCIA` (937-939) e `NOMI_ELSET_FABBRICATI` (951): li usano `NomeSetDiFaccia` (riga 37) e il validatore delle regioni
- 904-926: `lateral_nset`, `lateral_pressure`, `_carico_completo_o_assente` in `ModelConfig`
- 409-515: `SpintaOrizzontale`, `CaricoSommita`, `Modale`
- 396-406: `Natura`, `DESCRIZIONE_NATURA`
- **Lasciare** `NOMI_PASSO_RISERVATI` (521): lo usa il validatore di `AnalysisConfig.step_name` (565-568). Se un commento accanto cita le combinazioni, aggiornarlo.

Poi: `grep -n "Natura\|Selettore\|Carico\|Combinazione\|lateral_\|spinta\|modale" src/meshrec/core/config.py` — devono restare solo `AnalysisConfig` e i suoi commenti; togliere gli import ora inutili (`Annotated`, `Literal` restano se altri li usano).

- [ ] **Step 4: `steps.py`, `sweep.py`, `server.py`, `app.js`**

- `src/meshrec/core/steps.py:67`: `11: ("tet", "analysis", "regioni"),` e aggiornare il commento sopra (45-51) e quello su `carichi` in testa a `STEP_BLOCKS` (40-44): lo step 12 non ha più nulla da ereditare dai carichi.
- `src/meshrec/core/sweep.py`: riga 92 e' `BLOCCHI_VUOTI_FUORI_IMPRONTA: tuple[str, ...] = ("carichi", "selettori", "regioni")` → `("regioni",)` (la `frozenset` `11: {...}` che il piano citava qui sta in `server.py:625`, non in `sweep.py`). Commenti da riscrivere su `regioni` sola: 36-40 (l'esclusione di `carichi` «sopravvissuta»), 46-63 (`carichi` letto dallo step 11, i 22 registri), 71-74 (`selettori` segue `carichi`), docstring 155-166 di `expand` («Non riguarda piu' `carichi`, uscito da BLOCCHI_FUORI_IMPRONTA»). La riga 420 («la selezione di Pareto») non c'entra: resta.
- `src/meshrec/app/server.py:625`: `11: frozenset({"tet", "carichi", "analysis.material"})` → `frozenset({"tet", "analysis.material"})`; commento 612-614 («i carichi non hanno ancora una sede propria») da riscrivere; commento 600-604 («toglierne un blocco romperebbe la catena delle impronte e invaliderebbe le corse di riferimento») da riscrivere: e' esattamente cio' che questa PR fa, accettato dalla spec (decisione 7). Righe 1475-1478 e 1521-1524: la guardia `hasattr(annidato, "model_fields")` ora serve a `regioni` (un `dict`): riscrivere i due commenti su `regioni`, la guardia resta. `grep -n "carichi\|selettori" src/meshrec/app/server.py src/meshrec/app/worker.py` deve tornare vuoto (la riga 1699 «selezione le rileggono» parla della selezione nella vista 3D: resta).
- `src/meshrec/ui/app.js:3285`: in `ETICHETTE_DEI_BLOCCHI` togliere `carichi: "carichi", selettori: "selettori",`.
- `casi/lab_telaio.yaml`: cancellare il blocco `carichi:` dalla riga 92 alla fine del blocco (fino a `wall:`), e le due righe `lateral_nset: null` / `lateral_pressure: null` (128-129) dentro `model:`. `runs/*/config.yaml` **non si toccano**: sono corse di riferimento in sola lettura e restano l'ingresso vivo del caso «yaml vecchio».
- `git -C /Users/mario/GitHub/Tesi rm meshrec/lab_telaio_v4_posizionati.yaml meshrec/lab_telaio_v4_posizionati_top.yaml`.

- [ ] **Step 5: le prove che citano ciò che non c'è più**

> Corretto dall'architect: il `grep` a tappeto su `tests/*.py` prende «selettore» CSS (`test_report.py:1529-2130`, `test_stile.py`), «selettore file» (`test_ingresso.py:385-539`, `test_server.py:3803-3868`), «bimodale» (`test_wall.py`, `test_quality.py`, `test_guardie_e_nomi.py`) e «combinazione» in altro senso (`test_hexa.py:370`, `test_app_js.py:4159, 4280`): tutte prove che **restano**. `test_hexa.py` non ha prove di `lateral_pressure` (grep `lateral` vuoto su `main`). Elenco esatto da scansione AST:

**`tests/test_config.py`** — cancellare intere (righe di inizio su `main`): 347, 406, 420, 433, 444, 454 (casi di carico, modale, spinta); 521, 550, 573, 584, 599, 613, 627, 646, 682, 708, 718, 739, 752 (selettori e `CaricoSommita.nset`); `_config_con_posizionato` 800, 810, 822, 831, 850, 860, 870, 880, 891, 907, 935, 945, 958, 976, 993, 1026, 1037 (posizionati, momenti, distribuiti); 1416, 1448, `_config_con_combinazione` 1474, 1494, 1505, 1515, 1533, 1547, 1562, 1574 (natura, combinazioni). **Attenzione a 662** `test_fixed_nset_canonicalizza_il_nome_dei_sei`: prova `fixed_nset` (resta) e cita `Selettore` solo nella docstring — resta, docstring da aggiornare. Riscrivere: 100 (`selettori:` duplicato → `regioni:` duplicato, stessa `ValueError`), 309 (`{"wall","model"} <= campi`, `BLOCCHI_VUOTI_FUORI_IMPRONTA == {"regioni"}`), 1115 (togliere `cfg.carichi.combinazioni == ()`; aggiungere al `vecchia.yaml` un blocco `carichi:` e uno `selettori:` accanto a `solutore:` e asserire `not hasattr(riletta, "carichi")` — e' l'oracolo dello «yaml vecchio»). Solo docstring: 1194, 1304.

**`tests/test_sweep.py`** — cancellare intere: `_carico_sommita` 59, 63, 81, 98, `_selettore_sfera` 124, 128. Riscrivere: nessuna — l'omissione dall'impronta per `regioni` e' gia' provata da `test_config.py:1194`. Solo docstring: 924 (cita i blocchi che le 22 righe non avevano). 640 («bimodale») resta.

**`tests/test_server.py`** — riscrivere 2523 `test_il_pannello_dello_step_11_mostra_solo_i_blocchi_che_comanda`: l'asserzione su `STEP_BLOCKS[11]` diventa `("tet", "analysis", "regioni")`, il resto resta; docstring da riscrivere (dice che `STEP_BLOCKS` «non si tocca»). Cancellare 2575 `test_lo_schema_non_esplode_sul_blocco_selettori`: dopo il Task 3 passerebbe per il motivo sbagliato (`selettori` non e' in `STEP_BLOCKS[11]`, la guardia non viene nemmeno esercitata da lui); la guardia resta provata da 3676 sul blocco `regioni`. Solo docstring: 3676.

**`tests/test_app_js.py`** — nessuna modifica: 7831 `test_ogni_blocco_della_pipeline_ha_un_titolo_che_non_e_la_chiave` legge `STEP_BLOCKS` e resta verde da solo.

**`tests/test_materiali.py:319`** — docstring cita `lab_telaio_v4_posizionati*.yaml`: togliere il riferimento ai due file cancellati.

Metodo: per le cancellazioni intere lo stesso script `ast` del Task 2a, un file per chiamata; per le riscritture `Edit` mirato. Dopo ogni file: `uv run pytest <file> -q`.

- [ ] **Step 6: le due prove nuove passano, la suite è verde**

Run: `uv run pytest -m "" -q 2>&1 | tail -3`
Expected: verde. `uv run pytest tests/test_app_js.py tests/test_server.py -q` deve **eseguire** (non saltare) le prove di `node`: verificare che il conteggio dei saltati non sia salito rispetto alla baseline del Task 0.

- [ ] **Step 7: una corsa vera, con le regioni**

Run: `uv run meshrec run /Users/mario/GitHub/Tesi/meshrec/runs/geoandgeo-lab/config.yaml --from-step 9 --to-step 11 --out-dir /Users/mario/GitHub/Tesi/meshrec/runs/geoandgeo-lab-pr1`
(prima copiare `06_repaired.ply`, `steps.json`, `metrics.json` da `runs/geoandgeo-lab` nella cartella nuova; il `config.yaml` di `geoandgeo-lab` ha ancora un blocco `carichi`: viene ignorato perché `_ModelloBase` non vieta i campi ignoti, ed è il comportamento dichiarato di questa PR).
Expected: il deck ha `*STEP` una volta sola; `*NODE`, `*ELEMENT` e i sei `*NSET` identici al baseline: `diff <(grep -A99999 '^\*NODE' runs/geoandgeo-lab/wall_model.inp | sed '/^\*SOLID SECTION/,$d') <(grep -A99999 '^\*NODE' runs/geoandgeo-lab-pr1/wall_model.inp | sed '/^\*SOLID SECTION/,$d')` vuoto.

- [ ] **Step 8: commit**

```bash
git -C /Users/mario/GitHub/Tesi add -A meshrec/src meshrec/tests meshrec/casi meshrec/lab_telaio_v4_posizionati.yaml meshrec/lab_telaio_v4_posizionati_top.yaml
git -C /Users/mario/GitHub/Tesi commit -m "refactor(config): via carichi, selettori e pressione laterale

I blocchi carichi e selettori escono da PipelineConfig con le loro
classi e validatori; ModelConfig perde lateral_nset e lateral_pressure.
STEP_BLOCKS[11] legge tet, analysis e regioni. Un yaml vecchio che li
dichiara passa ancora, ignorato: il rifiuto nominato arriva con la PR 2.
Le impronte dello step 11 si muovono: le corse su disco lo mostrano
«non valido» e lo rieseguono in secondi (spec 2026-09-07, decisione 7)."
```

---

### Task 4: round di review e PR

**Files:**
- nessuno modificato dal piano; le correzioni che il round chiede si fanno con un commit `fix(...)` a sé

> **Annotazione architect.**
> - Subagente: **thread principale** dispaccia il round: `code-reviewer`, `test-writer`, `craft-reviewer`, `spec-reviewer` in **parallelo**, un solo messaggio. `security-reviewer` fuori (solo cancellazioni). `norme-reviewer` fuori (nessun coefficiente normativo nel diff: `NOMI_PASSO_RISERVATI` e `AnalysisConfig` non si toccano).
> - Sequenza: dopo Task 3, ultimo.
> - Skill-gate: **false** per il thread (dispatch e `gh`); i revisori portano il proprio.
> - A `test-writer` passare gli `## Ingressi degeneri` dei Task 1, 2, 3 qui sopra, non la lista in fondo (che non c'e' piu': e' stata ridistribuita).
> - A `craft-reviewer` segnalare i commenti riscritti: `steps.py:40-51, 64-66`, `sweep.py:36-74, 155-166`, `server.py:600-614, 1475-1478, 1521-1524`, e le docstring di `test_server.py:2523`, `test_config.py:309, 1115`.
>

## Ingressi degeneri
- nessun ingresso esterno (non scrive codice)

- [ ] **Step 1: il diff intero**

Run: `git -C /Users/mario/GitHub/Tesi diff main...feat/deck-nudo-carichi --stat | tail -3`
Expected: circa 15 file, poche centinaia di righe aggiunte, qualche migliaio tolte.

- [ ] **Step 2: review in parallelo** (lo fa il thread principale, non l'esecutore del task): `code-reviewer`, `test-writer` (con il `## Ingressi degeneri` del brief), `craft-reviewer` (messaggi di commit, commenti riscritti in `steps.py`/`sweep.py`), `spec-reviewer` (contro la spec, sezione «Sequenza» punto 1 e «Il deck nudo»). `security-reviewer` non serve: nessun input esterno nuovo, solo cancellazioni.

- [ ] **Step 3: PR**

```bash
git -C /Users/mario/GitHub/Tesi push -u origin feat/deck-nudo-carichi
gh pr create --repo maeurong/Tesi --base main --head feat/deck-nudo-carichi \
  --title "refactor(deck): via carichi e selettori, il deck torna al solo passo di gravita'" \
  --body-file <file con: cosa esce, cosa resta per la PR 2, l'esito della corsa vera del Task 3 Step 7, link a spec e ADR>
```

Merge con `--squash` quando la CI è verde su **entrambe** le piattaforme e il round è pulito; poi `superpowers:finishing-a-development-branch`.

---

## Ingressi degeneri — dove stanno

Ridistribuiti per task nelle annotazioni architect (Task 1: pipeline; Task 2: `write_inp`/`export_model`; Task 3: configurazione, impronte, `/api/schema`). Una lista sola qui sarebbe una seconda fonte di verita' che diverge. Il brief di ogni dispatch copia la sezione del proprio task.

## Self-review

- **Copertura della spec, punto 1 della sequenza**: carichi ✔ (Task 2, 3), selettori ✔ (Task 2, 3), `lateral_*` ✔ (Task 1, 3), passi multipli del deck ✔ (Task 2), `selezione.py` ✔ (Task 2). «Materiali multipli del deck» (sezione per regione) restano qui e cadono nella PR 2 con `MaterialeDichiarato`: dichiarato nei Global Constraints.
- **Placeholder**: nessun «TBD»; i grep sostituiscono elenchi di righe dove il locatore ha dato conteggi e non righe (test_config, test_sweep, test_server, test_app_js).
- **Coerenza dei nomi**: `STEP_BLOCKS[11] == ("tet", "analysis", "regioni")` in Task 3 Step 1 e Step 4; `BLOCCHI_VUOTI_FUORI_IMPRONTA == ("regioni",)` in Interfaces e Step 4; le firme di `write_inp`/`export_model` in Task 2 Interfaces coincidono con i parametri lasciati in Step 3.

## Deviazioni in esecuzione (08/09/2026, ruling del controller)

- `_gradi_da_scrivere` e `SOGLIA_COMPONENTE_RELATIVA` sono **usciti in questa PR** (commit `fa0bd16`), non nella PR 2: la Global Constraint li proteggeva sulla premessa che il ramo delle forze nodali di `_passo_statico` li usasse; il ramo scrive le righe da sé. Servivano solo ai carichi.
- `ripartisci` è uscita (commit `5d9b635`): nessun chiamante di produzione; le tre prove che la provavano cadono con lei. `aree_tributarie` resta per `surface_area`.
- Gli script di cantiere `docs/fase-6-cantiere/misura-carichi.py` e `docs/fase-7-cantiere/modi-per-la-normativa.py` restano **intatti** con una testata «documento di cantiere, non piu' eseguibile», come `scarto-c3d4-c3d10.py`: la spec vuole i documenti di fase intatti.
- «I materiali multipli del deck» stanno nella PR 2 (spec corretta, commit `68e37c6`): sono la `*SOLID SECTION` per regione alimentata da `regioni.materiale`.
- Il Task 2 è stato eseguito in due dispatch (2a prove, 2b codice) come annotato dall'architect.
- La prova `test_i_vecchi_kwarg_non_hanno_piu_un_ramo_di_compatibilita` (gate degli ingressi, riga 5) e' finita in `tests/test_condizioni_imposte.py`, file che questo piano dichiarava intoccabile: e' corretta e resta li' per questa PR; la PR 2, che riscrive quel file, la sposta in `test_abaqus.py`.
