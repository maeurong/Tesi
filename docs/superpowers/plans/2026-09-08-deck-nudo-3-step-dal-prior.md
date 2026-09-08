# Deck nudo, PR 3 di 4 — la geometria STEP dal prior: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `meshrec model` scrive, accanto al deck del modello parametrico, `modello.step`: il solido unico fuso dalle membrature del prior, per entrambi i tipi, con una metrica che dichiara quanti solidi contiene e quanto il volume scarta dall'analitico.

**Architecture:** una funzione nuova in `core/hexa.py`, `scrivi_step`, costruisce ogni prisma **non tagliato** nel kernel OpenCASCADE di gmsh direttamente in coordinate globali (`origine + u·e1 + v·e2`, estrusione lungo `asse·lunghezza`), fonde i volumi con `occ.fuse` a opzioni predefinite e scrive il file. `pipeline.genera_modello` la chiama dopo `export_model` e mette la metrica in `esito["step"]`. La mesh esaedrica e il suo deck non cambiano. Nessuna dipendenza nuova: gmsh 4.15.2 è già in `uv.lock` e scrive STEP AP214.

**Tech Stack:** Python 3.12, gmsh 4.15.2 (kernel `occ`), numpy, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-deck-nudo-e-step-dal-prior-design.md`, sezioni «La geometria STEP», «Testing Decisions» (voce «Lo STEP»), «Sequenza» punto 3. ADR: `docs/adr/2026-09-07-step-dal-prior-geometrico.md` (decisioni 1-5 e la misura del ticket #188). Esperimento di riferimento: ramo `research/fusione-fuori-piombo`, file `research/fusione-fuori-piombo/esperimento.py` (funzione `prisma`, righe 14-22: costruzione in `occ`; `fuse`/`write`/`importShapes` righe 152-163).

## Global Constraints

- Comandi dalla cartella `meshrec/` con `uv run`; percorsi assoluti; `git -C /Users/mario/GitHub/Tesi`. Questa PR gira in un **worktree separato** (`superpowers:using-git-worktrees`), in parallelo alla PR 2: i file che tocca (`hexa.py`, `pipeline.py` in `genera_modello`, `test_hexa.py`, `test_pipeline.py` nelle prove del modello) non sono quelli della PR 2 salvo `pipeline.py`, dove le righe sono diverse; il rebase finale è banale (verificato dall'architect sulle righe di `main` 8004950: la PR 2 tocca `pipeline.py:328-333` e `:356`, questa PR inserisce dopo `:362` e dopo `:377` — sei righe intatte fra i due hunk, git fonde senza conflitto; ordine di merge indifferente).
- **Il verde che mente** (`AGENTS.md`): suite onesta `uv run pytest -m "" -q` con `node` e `ccx` sul PATH; baseline su `main` 8004950: **1238 passati, 1 saltato**.
- Un esito **discreto** che dipende dalla piattaforma è un difetto: il numero di solidi e l'ordine dei volumi non devono dipendere dall'ordine di iterazione di gmsh; i volumi (continui) si confrontano con tolleranza relativa.
- Ogni numero mostrato ha un controllo che lo contraddice: la metrica porta `volume_analitico` e `scarto_relativo` accanto a `volume`.
- `gmsh.initialize()`/`finalize()` operano su stato globale: `scrivi_step` va chiamata serialmente, come già `mesh_prisma` (`hexa.py:144-256`), e mai con un modello gmsh già aperto.
- **Nessun parametro di tolleranza in `ModelConfig`** (ADR, decisione dal ticket #188): `occ.fuse` a opzioni predefinite. Niente `healShapes`, niente `fragment` prima del `fuse`, niente `removeAllDuplicates`.
- Unità mm. Formato AP214, l'unico che gmsh scrive: non si tocca `Geometry.OCCSTEPSchemaIdentifier`.
- Commit in italiano, Conventional Commits.

## Annotazione architect (08/09/2026, `main` 8004950)

| Task | Subagente | Sequenza | Skill-gate |
|------|-----------|----------|------------|
| 0 | thread principale (`superpowers:using-git-worktrees`) | prima di tutto | false: meccanico (worktree + `uv sync` + baseline) |
| 1 | `backend-engineer` | dopo Task 0 | **true** (TDD: le prove rosse prima della funzione) |
| 2 | `backend-engineer` | **dopo** Task 1: consuma `hexa.scrivi_step` | **true** (TDD) |
| 3 | thread principale: review in parallelo (`code-reviewer`, `test-writer`, `craft-reviewer`, `spec-reviewer`) | dopo Task 2 | n/a (revisori, sola lettura) |

Task 1 e 2 sono **sequenziali** (Task 2 importa la funzione del Task 1) e vanno in **un solo dispatch ciascuno** — prove e codice nello stesso brief, come nel Task 1 della PR 1 (non spezzati in 2a/2b: la funzione è di cinquanta righe e l'oracolo è già calcolato qui sotto). I file toccati dai due task sono disgiunti (`hexa.py`+`test_hexa.py` contro `pipeline.py`+`test_pipeline.py`), ma il vincolo di dipendenza vince sulla disgiunzione.

Premesse verificate su `main` 8004950 dall'architect (correzioni già riportate nei task): `hexa.py:16-25` **non importa `Path`** (import necessario); `hexa.costruisci` non muta né `membrature` né i `Prisma` — costruisce i propri prismi a `hexa.py:798` e `taglia_giunzioni` sostituisce le voci di `tagliati` con `Prisma` nuovi (`hexa.py:725-730`), mai in loco; `report.confronta` legge `modello.json` a `report.py:1168` e ne prende le chiavi con `.get` (`report.py:1231-1246`): una chiave `step` in più non rompe nulla, e le corse figlie già su disco senza `step` non vengono lette per quella chiave; `cli.py:236-248` (comando `model`) stampa l'`esito` intero in JSON, nessun riepilogo da toccare; l'helper di `tests/test_pipeline.py:1198` è `_scrivi_prior_telaio(cfg, telaio, spaziatura=20.0)` e la `cfg` delle prove vicine è `_config_cubo(tmp_path)` (`:20-40`).

**Geometria del test a T, ricalcolata e misurata** (`uv run python` + gmsh 4.15.2, scratchpad `prova_t.py`): `_base_del_piano((1,0,0))` = `e1 (0,1,0)`, `e2 (0,0,1)` — come scritto nel piano — quindi il contorno 300×500 centrato mette la trave in `y ∈ ±150`, `z ∈ [3000, 3500]`, e l'estrusione lungo `x` la porta da `x0` a `x0+4000`. Il pilastro (`_base_del_piano((0,0,1))` = `e1 (1,0,0)`, `e2 (0,1,0)`) occupa `x, y ∈ ±150`, `z ∈ [0, 3000]`. Con `x0 = 1850` la trave parte a `x = 1850`, **fuori** dalla pianta del pilastro (`x ≤ 150`): la faccia inferiore sta alla quota giusta ma non c'è sovrapposizione in pianta, e la misura dà `solidi == 2`. Con `x0 = -500` (la stessa origine dell'esperimento #188, `esperimento.py:33`) la trave copre `x ∈ [-500, 3500]` e la testa del pilastro sta interamente dentro la sua faccia inferiore: misurato `solidi == 1`, volume `870 000 000` = analitico, scarto `0.0`. Per l'asse a 2°: `_base_del_piano((sin2°, 0, cos2°))` = `e1 (0,1,0)`, `e2 (−cos2°, 0, sin2°)`; la testa sta a `x ≈ 3000·tan2° ≈ 105`, sempre sotto la trave con `x0 = -500`: misurato `solidi == 1`, ma lo scarto è **1,354e-4**, non `< 1e-6` — è il cuneo della testa inclinata dentro la trave, `B·tan θ·(B/2)²/2 = 117 857 mm³` (la stessa formula di `esperimento.py:caso_piombo`), su `870 164 577`. L'oracolo del quarto test è corretto di conseguenza: il numero col suo controllo, non una tolleranza che il fatto smentisce.

**Telaio sintetico del Task 2, misurato** (scratchpad `prova_telaio.py`, `_TELAIO_QUATTRO_MEMBRATURE` via `_scrivi_prior_telaio`): quattro membrature, **un solido** per entrambi i tipi; scarto **2,09 %** (`estruso`) e **1,78 %** (`primitive`) — sotto il tetto del 5 % del piano. Sono le compenetrazioni alle giunzioni che il prior misura; da registrare nel report della PR.

---

### Task 0: worktree e baseline

**Files:** nessuno modificato

- [ ] **Step 1: worktree da `main` aggiornato**

Con `superpowers:using-git-worktrees`, ramo `feat/step-dal-prior` da `main` 8004950. Poi `uv sync --frozen` nel `meshrec/` del worktree.

- [ ] **Step 2: baseline**

Run: `uv run pytest -m "" -q 2>&1 | tail -3`
Expected: 1238 passati, 1 saltato.

---

### Task 1: `scrivi_step` — il solido fuso dai prismi

**Files:**
- Modify: `src/meshrec/core/hexa.py` (dopo `prisma_di`, riga 276-329: la funzione nuova usa `Prisma` e `_base_del_piano`)
- Test: `tests/test_hexa.py`

**Interfaces:**
- Consumes: `Prisma` (`hexa.py:259-273`: `contorno` array (n,2) nel piano locale, `origine` (3,), `asse` (3,) unitario, `lunghezza` float); `_base_del_piano(asse) -> (e1, e2)` (`hexa.py:128-141`, deterministica); `_area_poligono(contorno)` (`hexa.py:99-125`).
- Produces:

```python
def scrivi_step(prismi: list[Prisma], percorso: Path) -> dict[str, object]:
    """Scrive `percorso` (STEP AP214) col solido fuso dei prismi; rende la metrica
    {"file": str, "schema": "AP214", "solidi": int, "volume": float,
     "volume_analitico": float, "scarto_relativo": float}.
    Zero prismi -> ValueError, nessun file."""
```

## Ingressi degeneri (Task 1, per il brief e per `test-writer`)

- zero prismi → `ValueError` con «membratura» nel messaggio, sollevato **prima** di `gmsh.initialize`, nessun file
- un prisma solo → nessun `fuse` (vuole oggetto e strumento non vuoti), `solidi == 1`, `volume == volume_analitico` (rel 1e-9)
- due prismi a contatto di faccia (T con `x0 = -500`) → `solidi == 1`, `volume == volume_analitico` (rel 1e-9), `scarto_relativo == 0` (abs 1e-9)
- due prismi disgiunti (10 mm d'aria) → file scritto, `solidi == 2`, `volume == volume_analitico`, nessuna eccezione
- pilastro con 2° di fuori piombo sotto la trave (`x0 = -500`) → `solidi == 1`, `volume == volume_analitico − cuneo` (rel 1e-9) con `cuneo = 300·tan2°·150²/2`, quindi `scarto_relativo ≈ 1,354e-4`
- contorno con vertici in senso orario → `volume_analitico > 0` (`abs(_area_poligono)`) e solido valido: `occ.addPlaneSurface` non pretende l'orientamento (a differenza di `mesh_prisma`, che rovescia la sagoma per gli esaedri)
- cartella di destinazione inesistente → `gmsh.write` solleva `Exception: Could not create file '…'` (misurato, gmsh 4.15.2): si propaga, nessun `finally` la inghiotte, nessuna guardia da aggiungere
- `lunghezza` non finita o ≤ 0 → non è un ingresso raggiungibile: `hexa.costruisci` → `mesh_prisma` lo rifiuta prima (`hexa.py:170-174`) e `genera_modello` chiama `scrivi_step` dopo `costruisci`; `scrivi_step` non lo controlla

- [ ] **Step 1: le prove, rosse**

In `tests/test_hexa.py`, in fondo, aggiungere (gmsh si importa dentro le prove come già fanno le prove di `mesh_prisma`):

```python
def _prisma_scatola(origine, asse, lati, lunghezza):
    """Un parallelepipedo come Prisma: contorno rettangolare centrato nel piano locale."""
    a, b = lati
    contorno = np.array([[-a / 2, -b / 2], [a / 2, -b / 2], [a / 2, b / 2], [-a / 2, b / 2]])
    return hexa.Prisma(
        contorno=contorno, origine=np.asarray(origine, dtype=np.float64),
        asse=np.asarray(asse, dtype=np.float64), lunghezza=float(lunghezza),
    )


def _rileggi_step(percorso):
    """Solidi e volume totale del file STEP, riletti con gmsh: e' l'oracolo, non la funzione."""
    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        entita = gmsh.model.occ.importShapes(str(percorso))
        gmsh.model.occ.synchronize()
        solidi = [tag for dim, tag in entita if dim == 3]
        return len(solidi), sum(gmsh.model.occ.getMass(3, tag) for tag in solidi)
    finally:
        gmsh.finalize()


def test_due_prismi_a_t_danno_un_solido_di_volume_analitico(tmp_path):
    """Pilastro verticale 300x300x3000 e trave 300x500x4000 appoggiata in testa,
    a contatto: un solido, volume = somma dei due (rel 1e-9)."""
    pilastro = _prisma_scatola((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (300.0, 300.0), 3000.0)
    trave = _prisma_scatola((-500.0, 0.0, 3250.0), (1.0, 0.0, 0.0), (300.0, 500.0), 4000.0)
    metrica = hexa.scrivi_step([pilastro, trave], tmp_path / "modello.step")
    atteso = 300.0 * 300.0 * 3000.0 + 300.0 * 500.0 * 4000.0
    assert metrica["solidi"] == 1
    assert metrica["volume_analitico"] == pytest.approx(atteso, rel=1e-9)
    assert metrica["volume"] == pytest.approx(atteso, rel=1e-9)
    assert metrica["scarto_relativo"] == pytest.approx(0.0, abs=1e-9)
    solidi, volume = _rileggi_step(tmp_path / "modello.step")
    assert solidi == 1
    assert volume == pytest.approx(atteso, rel=1e-9)


def test_due_prismi_disgiunti_restano_due_solidi_e_il_file_si_scrive(tmp_path):
    """Dieci millimetri d'aria: nessuna eccezione, `solidi == 2`, volume = somma."""
    a = _prisma_scatola((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (300.0, 300.0), 3000.0)
    b = _prisma_scatola((310.0, 0.0, 0.0), (0.0, 0.0, 1.0), (300.0, 300.0), 3000.0)
    metrica = hexa.scrivi_step([a, b], tmp_path / "modello.step")
    assert metrica["solidi"] == 2
    assert metrica["volume"] == pytest.approx(2 * 300.0 * 300.0 * 3000.0, rel=1e-9)
    assert _rileggi_step(tmp_path / "modello.step")[0] == 2


def test_zero_prismi_non_scrivono_un_file(tmp_path):
    with pytest.raises(ValueError, match="membratura"):
        hexa.scrivi_step([], tmp_path / "modello.step")
    assert not (tmp_path / "modello.step").exists()


def test_il_prisma_fuori_piombo_fonde_con_la_trave_e_lo_scarto_e_il_cuneo(tmp_path):
    """Due gradi di fuori piombo (misurato in #188: fonde a opzioni predefinite).
    La testa inclinata entra nella trave per un cuneo B*tan(theta)*(B/2)^2/2
    (la formula di esperimento.py, caso_piombo): il volume fuso e' l'analitico
    meno il cuneo, e lo scarto lo dichiara -- 1,35e-4, non zero."""
    theta = np.radians(2.0)
    asse = np.array([np.sin(theta), 0.0, np.cos(theta)])
    lunghezza = 3000.0 / np.cos(theta)
    pilastro = _prisma_scatola((0.0, 0.0, 0.0), asse, (300.0, 300.0), lunghezza)
    trave = _prisma_scatola((-500.0, 0.0, 3250.0), (1.0, 0.0, 0.0), (300.0, 500.0), 4000.0)
    metrica = hexa.scrivi_step([pilastro, trave], tmp_path / "modello.step")
    analitico = 300.0 * 300.0 * lunghezza + 300.0 * 500.0 * 4000.0
    cuneo = 300.0 * np.tan(theta) * 150.0 ** 2 / 2.0
    assert metrica["solidi"] == 1
    assert metrica["volume_analitico"] == pytest.approx(analitico, rel=1e-9)
    assert metrica["volume"] == pytest.approx(analitico - cuneo, rel=1e-9)
    assert metrica["scarto_relativo"] == pytest.approx(cuneo / analitico, rel=1e-6)
```

Posizione della trave, già calcolata e misurata (vedi «Annotazione architect»): `_base_del_piano((1,0,0))` = `(0,1,0)`,`(0,0,1)`, contorno centrato → `y ∈ ±150`, `z ∈ [3000, 3500]`; l'origine è l'**estremo** della trave lungo `x`, non il suo centro, quindi con `x0 = -500` la trave copre `x ∈ [-500, 3500]` e la testa del pilastro (`x, y ∈ ±150`) sta dentro la sua faccia inferiore. Il piano scritto prima portava `x0 = 1850`, che mette la trave fuori dalla pianta del pilastro e dà `solidi == 2`: corretto qui, non nella funzione. Con l'asse a 2° la testa sta a `x ≈ 105` e resta sotto la trave; lo scarto atteso è il cuneo, non zero.

- [ ] **Step 2: eseguirle, devono fallire**

Run: `uv run pytest tests/test_hexa.py -k "step or prismi" -q`
Expected: FAIL con `AttributeError: module 'meshrec.core.hexa' has no attribute 'scrivi_step'`.

- [ ] **Step 3: la funzione**

In `src/meshrec/core/hexa.py`, dopo `prisma_di`:

```python
MODEL_STEP_SCHEMA = "AP214"  # l'unico che gmsh scrive: dichiarato, non scelto


def scrivi_step(prismi: list[Prisma], percorso: Path) -> dict[str, object]:
    """Il solido fuso dei prismi, scritto in STEP; la metrica lo contraddice.

    I prismi sono quelli **non tagliati**: la fusione booleana toglie da se'
    la doppia contabilita' alle giunzioni, che `taglia_giunzioni` esiste per
    togliere alla mesh. Costruzione diretta in coordinate globali nel kernel
    OpenCASCADE, poi `occ.fuse` a opzioni predefinite: misurato il 07/09/2026
    (#188) che fino a 3 gradi di fuori piombo e 3 mm di compenetrazione
    fonde in un solido a volume esatto; prismi disgiunti, a contatto di solo
    spigolo o con un gioco sotto il decimo di millimetro restano solidi
    distinti, e la metrica lo dice con `solidi`.

    `volume_analitico` e' la somma area·lunghezza dei prismi cosi' come
    arrivano: sul telaio del prior i due volumi coincidono fino alla
    compenetrazione alle giunzioni, e lo scarto e' il numero da leggere.
    """
    if not prismi:
        raise ValueError(
            "nessuna membratura da scrivere in STEP: il prior non ne ha accettata "
            "alcuna. Guarda le regioni scartate e il controllo che le ha respinte"
        )
    import gmsh

    analitico = float(sum(
        abs(_area_poligono(np.asarray(p.contorno, dtype=np.float64))) * float(p.lunghezza)
        for p in prismi
    ))
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        occ = gmsh.model.occ
        volumi = []
        for p in prismi:
            asse = np.asarray(p.asse, dtype=np.float64)
            asse = asse / np.linalg.norm(asse)
            e1, e2 = _base_del_piano(asse)
            origine = np.asarray(p.origine, dtype=np.float64)
            punti = [
                occ.addPoint(*(origine + u * e1 + v * e2))
                for u, v in np.asarray(p.contorno, dtype=np.float64)
            ]
            linee = [
                occ.addLine(punti[i], punti[(i + 1) % len(punti)])
                for i in range(len(punti))
            ]
            superficie = occ.addPlaneSurface([occ.addCurveLoop(linee)])
            estruso = occ.extrude([(2, superficie)], *(asse * float(p.lunghezza)))
            volumi += [tag for dim, tag in estruso if dim == 3]
        if len(volumi) > 1:
            fusi, _ = occ.fuse([(3, volumi[0])], [(3, t) for t in volumi[1:]])
        else:
            fusi = [(3, volumi[0])]
        occ.synchronize()
        # Ordinati per tag: il conteggio e' discreto e non deve dipendere
        # dall'ordine in cui gmsh li restituisce.
        solidi = sorted(tag for dim, tag in fusi if dim == 3)
        volume = float(sum(occ.getMass(3, tag) for tag in solidi))
        gmsh.write(str(percorso))
    finally:
        gmsh.finalize()
    return {
        "file": str(percorso),
        "schema": MODEL_STEP_SCHEMA,
        "solidi": len(solidi),
        "volume": volume,
        "volume_analitico": analitico,
        "scarto_relativo": abs(volume - analitico) / analitico,
    }
```

`Path` **non** è importato in `hexa.py` (`hexa.py:16-25`: `warnings`, `dataclass`, `numpy`, `abaqus`, `ModelConfig`, `ruoli_dell_incontro`): aggiungere `from pathlib import Path` fra `from dataclasses import dataclass` e `import numpy as np`.

- [ ] **Step 4: le prove passano**

Run: `uv run pytest tests/test_hexa.py -k "step or prismi" -q`
Expected: 4 PASS (gli oracoli sono già stati misurati con la stessa costruzione: `solidi` 1/2/—/1, scarti 0 / 0 / — / 1,354e-4). Se un test differisce, la funzione differisce dalla costruzione del piano: guardare la funzione, non spostare gli oracoli.

- [ ] **Step 5: commit**

```bash
git -C <worktree> add meshrec/src/meshrec/core/hexa.py meshrec/tests/test_hexa.py
git -C <worktree> commit -m "feat(hexa): scrivi_step fonde i prismi del prior in un solido STEP

Costruzione diretta nel kernel OpenCASCADE in coordinate globali, fuse a
opzioni predefinite (misurato in #188: fino a 3 gradi di fuori piombo e
3 mm di compenetrazione un solido a volume esatto). La metrica porta
solidi, volume, volume analitico e scarto: il numero col suo controllo.
Zero prismi: ValueError e nessun file."
```

---

### Task 2: `genera_modello` scrive `modello.step` e la metrica

**Files:**
- Modify: `src/meshrec/core/pipeline.py:198` (accanto a `MODEL_FILENAME`), `pipeline.py:308-403` (`genera_modello`: dopo la chiamata a `export_model`, riga 351-362, e nella costruzione di `esito`, righe 372-393)
- `src/meshrec/cli.py:236-248` (comando `model`): **non si tocca** — stampa `json.dumps(esito)` intero, quindi `esito["step"]` esce da sé
- Test: `tests/test_pipeline.py`, **dopo** la definizione di `_scrivi_prior_telaio` (`:1198-1215`) e prima di `test_la_ricostruzione_legge_riempimento_sezione…` (`:1215`) — non accanto alla riga 1106 e non fra le prove `:1323-1375`, che la PR 2 riscrive (`cfg.analysis = None`); la `cfg` è `_config_cubo(tmp_path)` (`:20-40`), il telaio `_TELAIO_QUATTRO_MEMBRATURE` (`:1171`; **non** `_TELAIO_A_SEZIONE_UNIFORME`, che `costruisci` rifiuta come «vuoto», `:1260`)

**Interfaces:**
- Consumes: `hexa.scrivi_step(prismi, percorso)` (Task 1); `hexa.prisma_di(membratura, tipo) -> Prisma` (`hexa.py:276-329`); le `membrature` che `genera_modello` ha già in mano da `_membrature_del_prior` (`pipeline.py:326`) — `costruisci` non le muta (`hexa.py:798-799`: costruisce prismi propri; `taglia_giunzioni` sostituisce voci di `tagliati` con `Prisma` nuovi, `hexa.py:725-730`, mai in loco).

## Ingressi degeneri (Task 2, per il brief e per `test-writer`)

- prior senza membrature accettate → `hexa.costruisci` solleva prima («nessuna membratura da costruire», `hexa.py:769-773`): `scrivi_step` non viene chiamata, nessuna cartella figlia, nessun `modello.step` (già coperto da `test_una_corsa_figlia_fallita_non_lascia_una_cartella_orfana`, `:1248`)
- `scrivi_step` solleva dopo che il deck è scritto → l'eccezione si propaga e `modello.json` **non** viene scritto (la scrittura sta a `pipeline.py:397-402`, dopo): nessun `modello.json` che dichiara `step` senza file
- tipo `estruso` e tipo `primitive` sul telaio a quattro membrature → entrambi scrivono `modello.step`, `solidi == 1`, scarto misurato 2,09 % / 1,78 % (< 0,05), `riletto["step"]["file"]` finisce in `modello.step`
- `modello.json` di una figlia già su disco senza la chiave `step` → `report.confronta` non la legge (`report.py:1231-1246`, solo `.get` su altre chiavi): il confronto resta come oggi
- Produces: `MODEL_STEP_FILENAME = "modello.step"`; `esito["step"]` = la metrica di `scrivi_step`; il file `runs/<madre>-<tipo>/modello.step`.

- [ ] **Step 1: la prova, rossa**

In `tests/test_pipeline.py`, accanto a `test_…genera_modello…` (riga ~1106, che usa l'helper del telaio sintetico):

```python
@pytest.mark.parametrize("tipo", ["estruso", "primitive"])
def test_genera_modello_scrive_anche_la_geometria_step(tmp_path, tipo):
    """Accanto al deck, `modello.step`: un solido per il telaio sintetico, la
    metrica in `esito["step"]` e in modello.json, per entrambi i tipi."""
    cfg = _config_cubo(tmp_path)
    _scrivi_prior_telaio(cfg, _TELAIO_QUATTRO_MEMBRATURE)
    figlia = tmp_path / f"figlia-{tipo}"
    esito = pipeline.genera_modello(cfg, tipo, figlia)
    assert (figlia / pipeline.MODEL_STEP_FILENAME).exists()
    assert esito["step"]["solidi"] >= 1
    assert esito["step"]["volume"] > 0.0
    assert esito["step"]["scarto_relativo"] < 0.05
    riletto = json.loads((figlia / pipeline.MODEL_FILENAME).read_text(encoding="utf-8"))
    assert riletto["step"]["file"].endswith("modello.step")
```

Lo scarto del 5% è il tetto per il telaio sintetico: alle giunzioni i prismi non tagliati si compenetrano e il volume fuso è **minore** della somma. Misurato dall'architect sullo stesso telaio e la stessa costruzione: **2,09 %** (`estruso`), **1,78 %** (`primitive`), un solido in entrambi i casi. Registrare nel report i valori ottenuti dalla prova.

- [ ] **Step 2: eseguirla, deve fallire**

Run: `uv run pytest tests/test_pipeline.py -k geometria_step -q`
Expected: FAIL (`MODEL_STEP_FILENAME` non esiste).

- [ ] **Step 3: la costante e la chiamata**

In `pipeline.py`, accanto a `MODEL_FILENAME = "modello.json"` (riga 198):

```python
MODEL_STEP_FILENAME = "modello.step"
```

In `genera_modello`, dopo la chiamata a `abaqus.export_model(...)` (riga 351-362) e prima del calcolo dello scostamento dalla nuvola:

```python
    # La geometria per Abaqus, accanto al deck: i prismi NON tagliati -- la
    # fusione toglie da se' la doppia contabilita' alle giunzioni -- fusi in
    # un solido. E' una seconda uscita: la mesh esaedrica e il suo deck non
    # cambiano (spec 2026-09-07, ADR STEP dal prior geometrico).
    step = hexa.scrivi_step(
        [hexa.prisma_di(membratura, tipo) for membratura in membrature],
        out / MODEL_STEP_FILENAME,
    )
```

e nel dizionario `esito` la chiave `"step": step` dopo `"export": export`.

`membrature` a quel punto è ancora la lista intatta di `pipeline.py:326`: verificato dall'architect che `costruisci` non muta l'ingresso (`hexa.py:798-799` costruisce prismi propri; `taglia_giunzioni` rimpiazza voci di `tagliati` con `Prisma` nuovi, `hexa.py:725-730`). Nessuna copia da fare.

- [ ] **Step 4: la prova passa, la suite è verde**

Run: `uv run pytest tests/test_pipeline.py -k "geometria_step or genera_modello" -q`, poi `uv run pytest -m "" -q 2>&1 | tail -3`
Expected: verde; 1238 + 4 (Task 1) + 2 (parametrize) = **1244 passati, 1 saltato** — se il worktree è ancora su `main` 8004950. Dopo un rebase sulla PR 2 la baseline è quella della PR 2, e il delta resta **+6**.

- [ ] **Step 5: il comando `model` dal vero**

Sul telaio sintetico non serve: la prova lo copre. Sul dato reale il prior non accetta membrature (`runs/geoandgeo-lab`, ticket #189), quindi `meshrec model` rifiuta prima di arrivare allo STEP con l'errore già esistente: eseguire una volta `uv run meshrec model /Users/mario/GitHub/Tesi/meshrec/runs/geoandgeo-lab/config.yaml --tipo primitive` e registrare nel report che il messaggio è quello di `hexa.costruisci` («nessuna membratura da costruire», `hexa.py:769-773`), non un errore di `scrivi_step`. **Se la PR 2 è già entrata**, quel `config.yaml` porta ancora `analysis:` e viene rifiutato da `load_config` prima di tutto: allora usare la copia `runs/geoandgeo-lab-pr2` (con `export:` al posto di `analysis:`) che la PR 2 lascia sul disco, e registrare quale dei due rifiuti si è visto.

- [ ] **Step 6: commit**

```bash
git -C <worktree> add meshrec/src/meshrec/core/pipeline.py meshrec/tests/test_pipeline.py
git -C <worktree> commit -m "feat(model): il modello parametrico scrive anche modello.step

Seconda uscita di meshrec model accanto al deck, per entrambi i tipi:
Abaqus la importa come geometria e la mesha da se'. La metrica sta in
esito['step'] e in modello.json."
```

---

### Task 3: round di review, rebase e PR

- [ ] **Step 1**: `git -C <worktree> rebase main` se la PR 2 è già entrata. Ordine indifferente: la PR 2 tocca `pipeline.py:328-333` (via `analisi_dichiarata`) e `:356` (`analisi,` → `cfg.export,`), questa inserisce dopo `:362` e dopo `:377` — sei righe intatte in mezzo, git fonde da sé. In `test_pipeline.py` la PR 2 tocca `_config_cubo` (`:33`, `analysis=ANALISI`) e le prove `:1323-1375`; la prova nuova sta a `:1216` circa, fuori da entrambi. Unico effetto del rebase: il conteggio atteso della suite (delta +6, non 1244).
- [ ] **Step 2**: review in parallelo dal thread principale: `code-reviewer`, `test-writer` (contratto sotto), `craft-reviewer` (docstring e commit), `spec-reviewer` (spec «La geometria STEP», tutte le voci). `security-reviewer` non serve.
- [ ] **Step 3**: push, PR `feat/step-dal-prior`, corpo con: cosa scrive, la metrica, l'esito del Task 2 Step 5, il collaudo in CAE dello STEP sintetico già fatto dall'autore sul telaio dello spike (AP214 entra come part unica). Merge `--squash` a CI verde su entrambe le piattaforme.

## Ingressi degeneri

Ridistribuiti per task (annotazione architect): Task 1 sotto «Interfaces» del Task 1, Task 2 sotto «Interfaces» del Task 2. La riga «2° di fuori piombo → scarto < 1e-6» della prima stesura era falsa (misurato 1,354e-4, il cuneo): corretta lì.

## Self-review

- Spec «La geometria STEP», voce per voce: prismi non tagliati in `occ`, coordinate globali ✔ (Task 1 Step 3); fusione a opzioni predefinite, nessun parametro ✔; metrica con solidi/volume/analitico/scarto ✔; zero membrature → errore, nessun file ✔; entrambi i tipi ✔ (Task 2, parametrize); rilettura solo nel test ✔ (`_rileggi_step`); AP214 dichiarato ✔ (`MODEL_STEP_SCHEMA`).
- Placeholder: nessun «TBD»; l'helper del telaio sintetico è `_scrivi_prior_telaio` (`tests/test_pipeline.py:1198`), verificato.
- Coerenza dei nomi: `scrivi_step` (Task 1) chiamata in Task 2; `MODEL_STEP_FILENAME` definita in Task 2 Step 3 e usata nella prova di Step 1; chiavi della metrica identiche fra funzione, prove e spec.
