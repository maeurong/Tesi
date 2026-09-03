# Storico delle esecuzioni e pannello «Modello» — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ctrl+Z annulla anche le esecuzioni (artefatti, stato e metriche tornano quelli di prima), un pannello sotto la pipeline descrive il modello al fronte, il registro si chiude in un `<details>`, la galleria di curazione esce, e sei correzioni piccole entrano una per commit.

**Architecture:** `app/storico.py` resta una lista lineare di versioni con cursore; le versioni di esecuzione portano una cartella di scambio `.storico/NNNN/` e lo scambio (`rename`) è la propria inversa, quindi indietro e avanti usano la stessa funzione. Il server deposita **prima** di avviare il worker e rifiuta con 409 un ritorno mentre un worker gira. Il pannello del modello legge `/api/metrics` e si aggiorna quando cambia la terna `(numero, impronta, secondi)` del fronte, che è lo step valido di numero più alto.

**Tech Stack:** Python 3.12, FastAPI, pydantic, numpy, open3d; interfaccia in JavaScript senza framework (moduli ES), three.js già in `ui/vendor`; test con pytest e, per `app.js`, con `node` su un DOM finto (`tests/test_app_js.py`).

**Spec:** `docs/superpowers/specs/2026-09-03-storico-esecuzioni-pannello-modello-design.md`

## Global Constraints

- **Worktree, non il checkout condiviso.** `/mnt/c/Users/mario/GitHub/Tesi` è in uso da un'altra sessione. Tutto il lavoro sta in `/home/mario/worktrees/storico-esecuzioni`, ramo `feat/storico-esecuzioni` da `main`. Percorsi assoluti, un comando per chiamata Bash, `git -C <worktree>` al posto di `cd`.
- **Comando dei test** (da qualunque cwd; `W` sta per il worktree):

  ```
  LD_LIBRARY_PATH=/home/mario/.local/pkg/root/usr/lib/x86_64-linux-gnu PYTHONPATH=/home/mario/worktrees/storico-esecuzioni/meshrec/src TMPDIR=/home/mario/.tmp-fix /home/mario/.venvs/meshrec/bin/python -m pytest -c /home/mario/worktrees/storico-esecuzioni/meshrec/pyproject.toml --rootdir /home/mario/worktrees/storico-esecuzioni/meshrec /home/mario/worktrees/storico-esecuzioni/meshrec/tests/<file>::<test> -q
  ```

  Mai `uv run` (reinstalla il pacchetto nel venv condiviso). Nei task sotto il comando è abbreviato in `PYTEST <file>::<test>`.
- **Prosa in italiano** nei commenti, nei docstring e nei messaggi al browser, nello stile dei file toccati: il commento dice il *perché*, non il *cosa*.
- **Commit**: Conventional Commits in italiano (`feat(storico): ...`), un commit per task, con i trailer:

  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1
  ```
- **Nomi già decisi** (usati da più task): `storico.deposita(out_dir, testo, endpoint, campi, scambio=None)`, `storico.scambia(out_dir, numero) -> dict | None`, `storico.cursore(out_dir) -> int`, `steps.dimentica(out_dir, numeri)`, file `scambio.json` dentro `.storico/NNNN/`, risposta di indietro/avanti con `tipo` («configurazione» | «esecuzione») e, per le esecuzioni, `da` e `a`.
- **Ordine**: Task 1 (togliere la galleria) prima di tutto; i Task 2-4 sono il nucleo e vanno in sequenza; Task 5-6 dopo il 4; i Task 7.x sono indipendenti fra loro e dal nucleo, ma vanno dopo il Task 1 (toccano `app.js` e `index.html`).

## Sequenza di dispatch

Annotazione dell'`architect` (03/09/2026, dal checkout `/mnt/c/Users/mario/GitHub/Tesi`, branch `main`, HEAD `8fb83a6`). Ogni task porta sotto il titolo un blocco **Dispatch** (agente dal roster in `~/.claude/agents/`, skill-gate, sequenza) e un blocco **Ingressi degeneri** (condizione → oracolo): il primo dice a chi va il lavoro, il secondo che cosa il codice deve sopravvivere, e `test-writer` al Task 8 risponde riga per riga.

**Grafo.** Task 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7.1 → 7.2 → 7.3 → 7.4 → 7.5 → 7.6 → 8. Una catena sola, per la ragione sotto.

- Il nucleo (2 → 3 → 4 → 5 → 6) è sequenziale per dipendenza: il 3 consuma `deposita(..., scambio=)`/`scambia`/`cursore` del 2, il 5 legge le chiavi che il 4 scrive, il 6 legge `tipo`/`da`/`a` che il 3 risponde. Il 4 tocca solo `pipeline.py` e potrebbe girare in parallelo al 2-3, ma non c'è un secondo worktree (vedi sotto).
- I Task 7.1-7.6 sono indipendenti **per logica** (un commit ciascuno, si toglie uno senza toccare gli altri) ma non **per file**: 7.1, 7.2, 7.3, 7.4, 7.6 scrivono tutti `app.js` e appendono in coda a `test_app_js.py`; 7.2, 7.3, 7.4 scrivono `index.html`; 7.1, 7.3, 7.6 scrivono `stile.css`. 7.5 tocca `server.py` nella rotta che il Task 3 riscrive (`_avvia(numero, 12, ...)`), quindi va dopo il 3 in ogni caso.
- **Un solo worktree, un agente alla volta.** Tutto il lavoro sta in `/home/mario/worktrees/storico-esecuzioni`. Due agenti che editano `app.js` nella stessa working tree si pestano: l'`Edit` del secondo parte da un file che il primo ha già cambiato, e un `git add -A` (Task 1) o un commit di uno porta dentro le modifiche a metà dell'altro. L'alternativa — un worktree per ogni 7.x e poi rebase su `feat/storico-esecuzioni` — costerebbe sei rebase con conflitto garantito sulla coda di `test_app_js.py` (tutti appendono nello stesso punto) e nessun guadagno reale: i 7.x sono task S, da pochi minuti l'uno, e l'attesa in serie è minore del costo di sei risoluzioni di conflitto. **Scelta: serializzati sullo stesso worktree, nell'ordine 7.1 → 7.2 → 7.3 → 7.4 → 7.5 → 7.6, dopo il Task 6.** Se uno dei 7.x viene tolto dal lotto, i successivi scalano senza altre modifiche.
- **Parallelo vero, solo al Task 8:** i quattro revisori (`security-reviewer`, `code-reviewer`, `test-writer`, `craft-reviewer`) sono in sola lettura e indipendenti, e vanno dispacciati in un solo messaggio. Le correzioni che ne escono tornano in serie, un agente alla volta, un commit per correzione.

**Regole comuni a ogni dispatch.** Il brief nomina `skill-gate`, `caveman` e — per chi scrive codice — `ponytail` (l'hook `dispatch-gate.py` nega il dispatch se mancano). Ogni brief cita almeno un `file:riga` letto nella sessione che dispaccia, oppure dichiara «nessuna premessa sul codice». Il blocco **Ingressi degeneri** del task va copiato tale e quale nel brief. `coder` non ha lo strumento `Skill`: per lui lo skill-gate è «nessuna» per costruzione, e il brief lo dice invece di fingerlo.

**Nota sul banco di `app.js` (vale per i Task 5, 6, 7.1, 7.2, 7.3, 7.6).** In `tests/test_app_js.py` i banchi che chiamano `assert.*` o `document.*` partono da `_DOM + _funzioni(...)` (righe 413, 443, 474, 541): `_DOM` porta `import assert from 'node:assert/strict'`, il DOM finto, `elemento` e `STEP_DEL_PRIOR`. I banchi scritti nei task sotto usano `_funzioni(...)` da sola e quindi, così come sono, cadono su `ReferenceError: assert is not defined` — un rosso che non parla del comportamento. Chi implementa antepone `_DOM +` ai banchi che ne hanno bisogno. In più, `_costante` (riga 315) estrae solo costanti **su una riga** (`^const X = .*;$`): `RIGHE_DEL_MODELLO`, `RIGHE_DELLA_SUPERFICIE` e `NON_MISURATO` del Task 5 vanno portate nel banco in un altro modo (per esempio estraendole dal sorgente con lo stesso taglio che `_etichette_metriche` del Task 7.6 fa per `ETICHETTE_METRICHE`), e `fronteDelloStato` ha bisogno di `STEP_DEL_PRIOR`, che `_DOM` già porta. Non è una modifica ai passi: è il modo in cui il banco va montato perché il rosso del passo 2 sia quello atteso.

---

### Task 0: Il worktree

> **Dispatch.** Agente: thread principale (nessun subagente: due comandi git, nessun file del repository). Skill-gate: `superpowers:using-git-worktrees` per il thread; per un subagente sarebbe «nessuna» — task meccanico, un comando, dichiarato. Sequenza: primo di tutti; nessun parallelo.
>
> **Ingressi degeneri.**
> - nessun ingresso esterno: crea un worktree da `main` e lancia la suite, non scrive codice. Se `/home/mario/worktrees/storico-esecuzioni` esiste già (worktree fermo di una sessione precedente), `git worktree add` rifiuta: si guarda `git -C /mnt/c/Users/mario/GitHub/Tesi worktree list` e si rimuove con `worktree remove` prima, non si sceglie un nome nuovo.

**Files:** nessuno del repository.

- [ ] **Step 1: Crea il worktree dal `main` aggiornato**

```bash
git -C /mnt/c/Users/mario/GitHub/Tesi worktree add -b feat/storico-esecuzioni /home/mario/worktrees/storico-esecuzioni main
```

- [ ] **Step 2: Verifica che la suite parta**

Run: `PYTEST tests/test_storico.py`
Expected: `15 passed`.

---

### Task 1: La galleria di curazione esce

> **Dispatch.** Agente: `backend-engineer` (le rotte e la firma di `create_app` sono la parte con logica; le rimozioni in `ui/` sono cancellazioni di blocchi già delimitati per riga, senza scelte di interfaccia — non vale un secondo dispatch a `frontend-engineer`). Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` (il banco del passo 1 prima delle rimozioni); `senior-backend` non pertinente (nessuna API nuova, solo rimozione), salto da dichiarare nel report. Sequenza: dopo il Task 0, prima di tutto il resto; nessun parallelo (tocca `app.js`, `index.html`, `stile.css`, `server.py` e tre file di test).
>
> **Ingressi degeneri.**
> - `GET /api/experiments` e `GET /api/experiments/<qualunque>` → 404, e nessuna rotta con prefisso `/api/experiments` in `app.routes` (banco del passo 1)
> - chiamante residuo di `create_app(..., radice_esperimenti=...)` → `TypeError` alla costruzione della fixture: sono **quattro** e non uno — `tests/test_server.py:45` (fixture `cliente`), `tests/test_server.py:3670` (fixture `cliente_con_regioni`), `tests/test_ingresso.py:48` — e vanno tolti tutti nello stesso commit, altrimenti il passo 6 è rosso su un file che il piano non nomina; `cli.py:308` chiama `create_app(args.config)` senza il parametro e non si tocca
> - `grep -n "galleria\|Galleria\|experiments"` su `app.js`, `index.html`, `stile.css` dopo il passo 4 → zero righe (i due commenti alle righe 206 e 1268 riscritti); `grep -n "report\."` su `server.py` → zero righe, altrimenti l'import di `report` resta
> - `tests/test_stile.py:269` senza `.galleria-tabella` → il banco delle famiglie con `:focus-visible` resta verde con una voce in meno, non salta

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py:731-760` (firma di `create_app` e docstring), `:1521-1572` (le due rotte)
- Modify: `meshrec/src/meshrec/ui/index.html:267-282` (galleria) e `:169-170` (commento sui «tre vuoti»)
- Modify: `meshrec/src/meshrec/ui/app.js:3288-3399`
- Modify: `meshrec/src/meshrec/ui/stile.css:714-730`
- Modify: `meshrec/tests/test_server.py:22-56` (fixture `cliente`), `:2853-2975` (i tre banchi della galleria), `:3642-3672` (fixture `cliente_con_regioni`, passa anch'essa `radice_esperimenti`)
- Modify: `meshrec/tests/test_ingresso.py:45-48` (passa `radice_esperimenti`)
- Modify: `meshrec/tests/test_app_js.py:3141-3242`
- Modify: `meshrec/tests/test_stile.py:269`

**Interfaces:**
- Produces: `create_app(config_path=None, radice_corse=Path("runs"))` — senza `radice_esperimenti`. Nessun altro task dipende dalla galleria.

- [ ] **Step 1: Scrivi il banco che sorveglia l'assenza**

In `meshrec/tests/test_server.py`, al posto dei tre banchi `test_la_galleria_elenca_gli_esperimenti_esistenti`, `test_la_galleria_non_scrive_mai_nei_registri`, `test_la_galleria_mostra_il_candidato_di_fronte_su_lab_crop` (righe 2853-2975, compreso il commento «Task 14: galleria di curazione»):

```python
# --------------------------------------------------------------------------
# La galleria di curazione e' uscita il 03/09/2026: era una finestra sui
# registri di sweep della Fase 2, e chi usa il programma non la apriva. Il
# core dello sweep resta; a sparire sono le rotte e la colonna.
# --------------------------------------------------------------------------


def test_le_rotte_della_galleria_non_esistono_piu(cliente):
    """Una rotta che sopravvive alla propria interfaccia e' codice che nessuno
    esercita e che continua a leggere il disco: va via con lei."""
    assert cliente.get("/api/experiments").status_code == 404
    assert cliente.get("/api/experiments/qualunque").status_code == 404
    assert not any(
        getattr(rotta, "path", "").startswith("/api/experiments")
        for rotta in cliente.app.routes
    )
```

E nella fixture `cliente` (riga 45) togli la riga `radice_esperimenti=tmp_path / "experiments",` e le quattro righe di commento sopra che la spiegano («Le due radici esplicite: ... non tmp_path.»). Lo stesso argomento lo passano anche la fixture `cliente_con_regioni` (`test_server.py:3670`) e `tests/test_ingresso.py:48`: vanno tolti nello stesso commit, altrimenti quei banchi cadono con `TypeError` al passo 6.

- [ ] **Step 2: Esegui il banco e vedilo fallire**

Run: `PYTEST tests/test_server.py::test_le_rotte_della_galleria_non_esistono_piu`
Expected: FAIL — `create_app()` accetta ancora `radice_esperimenti`? No: fallisce perché `/api/experiments` risponde 200.

- [ ] **Step 3: Togli le rotte e il parametro dal server**

In `meshrec/src/meshrec/app/server.py`:
- Firma di `create_app`: togli `radice_esperimenti: Path = Path("experiments"),` e la riga `radice_esperimenti = Path(radice_esperimenti)`. Nel docstring togli la frase da «`radice_esperimenti` quella dei registri di sweep della galleria.» fino a «sparisse senza dire perche'.» e lascia: «`radice_corse` e' la cartella dove le corse nascono e dove vengono cercate, relativa come `run.out_dir` e `CACHE_DIR`: risolta rispetto alla cartella da cui gira il server, non rispetto al file di configurazione.»
- Cancella per intero le due rotte `@app.get("/api/experiments")` e `@app.get("/api/experiments/{nome}")` (righe 1521-1568).
- `report` in `from meshrec.core import (...)`: dopo la rimozione non ha più usi (`grep -n "report\." server.py` deve tornare vuoto): togli il nome dall'import. `sweep` resta (`sweep.leggi_metriche`, `sweep.append_row` in storico).

- [ ] **Step 4: Togli il markup, lo script e lo stile**

`meshrec/src/meshrec/ui/index.html`: cancella dalla riga `<h2>Galleria di curazione</h2>` fino al `</div>` di `#galleria-tabella` compreso (righe 267-282). Nel commento dello stato vuoto della vista (righe 169-170) «Gli altri tre vuoti di questa pagina (le corse, il dettaglio, la galleria)» diventa «Gli altri due vuoti di questa pagina (le corse, il dettaglio)».

`meshrec/src/meshrec/ui/app.js`: cancella da `async function caricaGalleria()` (riga 3291, con il commento sopra che inizia alla 3288) fino alla chiusura dell'ascoltatore su `#galleria-elenco` (riga 3399) compresa. Verifica con `grep -n "galleria\|Galleria\|experiments" app.js`: devono restare solo i commenti che citano la galleria come esempio storico (riga ~206 «eventi, galleria» e ~1268 «`caricaGalleria` la guardia ce l'aveva gia'»): riscrivili senza il riferimento — alla 206 togli «, galleria»; alla 1268 sostituisci «`caricaGalleria` la guardia ce l'aveva gia'; le» con «Le».

`meshrec/src/meshrec/ui/stile.css`: cancella il blocco da «/* La colonna della galleria e' stretta» fino a `.galleria-tabella tr.fronte {...}` compreso (righe 714-730).

- [ ] **Step 5: Togli i banchi del browser e dello stile**

`meshrec/tests/test_app_js.py`: cancella da riga 3141 (`# ----` sopra «Task 14: galleria di curazione») a riga 3242 (chiusura di `test_mostraEsperimento_dichiara_il_rifiuto_del_server`), lasciando intatta la riga 3243 «# ----» che apre il blocco «Task 14: step 12».

`meshrec/tests/test_stile.py:269`: la tupla delle famiglie perde `".galleria-tabella"`: la riga diventa `".registro",`.

- [ ] **Step 6: Esegui i banchi toccati**

Run: `PYTEST tests/test_server.py tests/test_app_js.py tests/test_stile.py`
Expected: tutti verdi; nessun test nomina più `experiments`.

- [ ] **Step 7: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add -A
git -C /home/mario/worktrees/storico-esecuzioni commit -m "refactor(interfaccia): la galleria di curazione esce, e con lei le sue rotte" -m "Era una finestra sui registri di sweep della Fase 2: chi usa il programma non la apriva, e la colonna Dettaglio la portava sotto la piega. Il core dello sweep non si tocca." -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 2: La cartella di scambio in `storico.py`

> **Dispatch.** Agente: `backend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` (sei banchi prima del codice, passo 1-2); `senior-backend` non pertinente (modulo di file, nessuna API), salto da dichiarare. Sequenza: dopo il Task 1; nessun parallelo (il Task 3 consuma la firma che questo produce).
>
> **Ingressi degeneri.**
> - nome in `sposta` o `copia` assente nella corsa al deposito (prima esecuzione di uno step) → nessuna eccezione, il nome resta in `scambio.json["file"]` e la versione si deposita
> - cartella `NNNN/` senza `scambio.json`, oppure versione di sola configurazione (nessuna cartella) → `scambia` torna `None` e nessun file della corsa cambia (banco `test_una_versione_di_configurazione_non_scambia_niente`)
> - `scambio.json` illeggibile (troncato: `scrivi_atomico` lascia `scambio.tmp.json` se il processo muore, `core/io.py:143-150`) → `scambia` solleva `ValueError` **prima** del primo `rename`, nessun file della corsa spostato (il parse sta sopra il ciclo)
> - nome in `file` presente né nella corsa né nella cartella → saltato, gli altri nomi si scambiano lo stesso, la chiamata torna `{"da", "a"}`
> - deposito nuovo con cursore arretrato su versioni di esecuzione → le cartelle oltre il cursore spariscono insieme ai `.yaml`; tetto `TETTO` superato → le cartelle più vecchie spariscono con le loro versioni (banco `test_la_troncatura_e_il_tetto_cancellano_anche_le_cartelle`)
> - `out_dir` senza `.storico/` al primo deposito → la cartella nasce (`scrivi_atomico` crea i genitori, `core/io.py:143`), nessun `FileNotFoundError`
> - `scambia` chiamata due volte sulla stessa versione → identità: ogni file dove stava (banco `test_lo_scambio_e_la_propria_inversa`)

**Files:**
- Modify: `meshrec/src/meshrec/app/storico.py`
- Test: `meshrec/tests/test_storico.py`

**Interfaces:**
- Produces:
  - `deposita(out_dir: Path, testo: str, endpoint: str, campi: list[str], scambio: dict | None = None) -> int`. `scambio = {"da": int, "a": int, "sposta": list[str], "copia": list[str]}`: i nomi in `sposta` si spostano dalla corsa alla cartella, quelli in `copia` si copiano; l'ordine di scambio è `sposta + copia`.
  - `scambia(out_dir: Path, numero: int) -> dict | None`: scambia i file elencati in `.storico/NNNN/scambio.json` fra corsa e cartella; torna `{"da", "a"}` oppure `None` se la versione non ha cartella.
  - `cursore(out_dir: Path) -> int`: il numero della versione corrente (0 se nessuna).
  - `SCAMBIO = "scambio.json"`.

- [ ] **Step 1: Scrivi i banchi**

In coda a `meshrec/tests/test_storico.py`:

```python
def _scambio(da=2, a=2, sposta=("02_segmented.ply",), copia=("steps.json",)):
    return {"da": da, "a": a, "sposta": list(sposta), "copia": list(copia)}


def test_depositare_un_esecuzione_sposta_gli_artefatti_e_copia_lo_stato(tmp_path: Path):
    """Spostare e non copiare: un rename sullo stesso filesystem costa zero byte
    anche per un artefatto da cento megabyte. Lo stato invece si copia, perche'
    la ripresa lo rilegge per aggiungere la voce nuova: spostato via, gli step
    a monte risulterebbero «mai eseguito» a esecuzione finita."""
    (tmp_path / "02_segmented.ply").write_bytes(b"mesh")
    (tmp_path / "steps.json").write_text("{}", encoding="utf-8")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    cartella = tmp_path / storico.CARTELLA / f"{numero:04d}"
    assert not (tmp_path / "02_segmented.ply").exists(), "l'artefatto non e' stato spostato"
    assert (cartella / "02_segmented.ply").read_bytes() == b"mesh"
    assert (tmp_path / "steps.json").exists(), "lo stato doveva restare nella corsa"
    assert (cartella / "steps.json").read_text(encoding="utf-8") == "{}"
    dichiarato = json.loads((cartella / storico.SCAMBIO).read_text(encoding="utf-8"))
    assert dichiarato == {"da": 2, "a": 2, "file": ["02_segmented.ply", "steps.json"]}


def test_un_artefatto_assente_non_ferma_il_deposito(tmp_path: Path):
    """Uno step mai eseguito non ha artefatto: e' il caso normale della prima
    esecuzione, non un guasto."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    assert (tmp_path / storico.CARTELLA / f"{numero:04d}" / storico.SCAMBIO).exists()


def test_lo_scambio_e_la_propria_inversa(tmp_path: Path):
    """Indietro e avanti sono la stessa operazione: dopo due scambi ogni file e'
    dove stava. Tre casi in un colpo: presente da entrambe le parti, solo nella
    corsa, solo nella cartella."""
    (tmp_path / "02_segmented.ply").write_bytes(b"prima")
    (tmp_path / "steps.json").write_text("prima", encoding="utf-8")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(
        tmp_path, "uno\n", "POST /api/step/2", [],
        scambio=_scambio(sposta=("02_segmented.ply", "metrics.partial.json"), copia=("steps.json",)),
    )
    # L'esecuzione scrive la corsa nuova; il parziale esiste solo dopo.
    (tmp_path / "02_segmented.ply").write_bytes(b"dopo")
    (tmp_path / "steps.json").write_text("dopo", encoding="utf-8")
    (tmp_path / "metrics.partial.json").write_text("parziale", encoding="utf-8")

    assert storico.scambia(tmp_path, numero) == {"da": 2, "a": 2}
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"prima"
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "prima"
    assert not (tmp_path / "metrics.partial.json").exists()
    cartella = tmp_path / storico.CARTELLA / f"{numero:04d}"
    assert (cartella / "02_segmented.ply").read_bytes() == b"dopo"
    assert (cartella / "metrics.partial.json").read_text(encoding="utf-8") == "parziale"

    assert storico.scambia(tmp_path, numero) == {"da": 2, "a": 2}
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"dopo"
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "dopo"
    assert (tmp_path / "metrics.partial.json").read_text(encoding="utf-8") == "parziale"
    assert not (cartella / "metrics.partial.json").exists()


def test_una_versione_di_configurazione_non_scambia_niente(tmp_path: Path):
    (tmp_path / "02_segmented.ply").write_bytes(b"resta")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    assert storico.scambia(tmp_path, numero) is None
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"resta"


def test_la_troncatura_e_il_tetto_cancellano_anche_le_cartelle(tmp_path: Path, monkeypatch):
    """Le cartelle oltre il cursore portano gli artefatti del futuro scartato:
    tenerle sarebbe disco occupato da cio' che nessun comando puo' piu'
    raggiungere. Il tetto pota le piu' vecchie con la stessa regola."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    (tmp_path / "02_segmented.ply").write_bytes(b"x")
    seconda = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    (tmp_path / "02_segmented.ply").write_bytes(b"y")
    terza = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    storico.indietro(tmp_path)
    storico.indietro(tmp_path)
    storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["a"])
    assert not (tmp_path / storico.CARTELLA / f"{seconda:04d}").exists()
    assert not (tmp_path / storico.CARTELLA / f"{terza:04d}").exists()

    monkeypatch.setattr(storico, "TETTO", 2)
    (tmp_path / "02_segmented.ply").write_bytes(b"z")
    storico.deposita(tmp_path, "tre\n", "POST /api/step/2", [], scambio=_scambio())
    storico.deposita(tmp_path, "quattro\n", "PUT /api/config", ["b"])
    superstiti = sorted(p.name for p in (tmp_path / storico.CARTELLA).iterdir())
    assert not any(nome == "0001.yaml" for nome in superstiti)
    assert not any(nome.isdigit() and int(nome) < storico.cursore(tmp_path) - 1 for nome in superstiti)


def test_il_cursore_e_pubblico(tmp_path: Path):
    assert storico.cursore(tmp_path) == 0
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    assert storico.cursore(tmp_path) == 1
```

- [ ] **Step 2: Esegui e vedili fallire**

Run: `PYTEST tests/test_storico.py`
Expected: i sei banchi nuovi falliscono (`TypeError: deposita() got an unexpected keyword argument 'scambio'`, `AttributeError: ... has no attribute 'scambia'`); i 15 vecchi restano verdi.

- [ ] **Step 3: Implementa**

In `meshrec/src/meshrec/app/storico.py`, aggiungi `import shutil` agli import e, sotto `CARTELLA = ".storico"`:

```python
# Il file che ogni cartella di scambio porta: gli step che l'esecuzione ha
# coperto e i nomi dei file che lo scambio governa. Sta nella cartella e non
# nel registro perche' lo scambio deve funzionare anche con registro.jsonl
# toccato a mano: il registro e' provenienza, questo e' meccanismo.
SCAMBIO = "scambio.json"


def _cartella_di_scambio(out_dir: Path, numero: int) -> Path:
    return _cartella(out_dir) / f"{numero:04d}"


def _scarta_versione(out_dir: Path, numero: int) -> None:
    """Toglie una versione con la sua cartella, se ne ha una: contiene o gli
    artefatti di un futuro scartato o quelli di un passato oltre il tetto, e
    in entrambi i casi nessun comando li puo' piu' raggiungere."""
    _percorso(out_dir, numero).unlink()
    cartella = _cartella_di_scambio(out_dir, numero)
    if cartella.is_dir():
        shutil.rmtree(cartella)


def cursore(out_dir: Path) -> int:
    """La versione su cui siamo. Pubblica perche' il server deve sapere QUALE
    versione un «indietro» sta per togliere, e lo sa solo prima di chiamarlo."""
    return _cursore(out_dir)
```

Sostituisci il corpo di `_applica_tetto` e il ciclo di troncatura in `deposita` con `_scarta_versione`:

```python
def _applica_tetto(out_dir: Path) -> None:
    numeri = _numeri(out_dir)
    if len(numeri) <= TETTO:
        return
    for numero in numeri[: len(numeri) - TETTO]:
        _scarta_versione(out_dir, numero)
```

e in `deposita`:

```python
    for numero in _numeri(out_dir):
        if numero > corrente:
            _scarta_versione(out_dir, numero)
```

Cambia la firma di `deposita` in
`def deposita(out_dir: Path, testo: str, endpoint: str, campi: list[str], scambio: dict | None = None) -> int:`
e, subito dopo la scrittura del `.yaml` e prima di `sweep.append_row`, aggiungi:

```python
    file_scambiati: list[str] = []
    if scambio is not None:
        # Un'esecuzione. Gli artefatti si SPOSTANO nella cartella -- un rename
        # sullo stesso filesystem, zero byte scritti anche per cento megabyte
        # -- e lo stato e le metriche si COPIANO: la ripresa li rilegge per
        # aggiungervi la voce nuova, e spostati via lascerebbero gli step a
        # monte «mai eseguito» a esecuzione finita. Chi manca non e' un
        # guasto: e' uno step mai eseguito, cioe' la prima esecuzione.
        cartella = _cartella_di_scambio(out_dir, nuovo)
        cartella.mkdir(parents=True, exist_ok=True)
        for nome in scambio["sposta"]:
            sorgente = Path(out_dir) / nome
            if sorgente.exists():
                sorgente.replace(cartella / nome)
        for nome in scambio["copia"]:
            sorgente = Path(out_dir) / nome
            if sorgente.exists():
                shutil.copy2(sorgente, cartella / nome)
        file_scambiati = [*scambio["sposta"], *scambio["copia"]]
        io.scrivi_atomico(
            cartella / SCAMBIO,
            lambda destinazione: destinazione.write_text(
                json.dumps({"da": scambio["da"], "a": scambio["a"], "file": file_scambiati}),
                encoding="utf-8",
            ),
        )
```

Nel dizionario passato ad `append_row` aggiungi `"artefatti": file_scambiati,`.

In coda al modulo:

```python
def scambia(out_dir: Path, numero: int) -> dict | None:
    """Scambia i file di una versione di esecuzione fra la corsa e la sua
    cartella. Torna gli step coperti, o None se la versione e' di sola
    configurazione.

    E' la propria inversa: dopo un «indietro» la cartella contiene cio' che
    l'esecuzione aveva prodotto, e un «avanti» lo rimette con la stessa
    chiamata. Per questo il modulo non ha due funzioni.

    ponytail: lo scambio non e' atomico fra file. Ogni rename lo e', la
    sequenza no: un processo ucciso a meta' lascia una parte dei file
    scambiata. Il server mette steps.json per ULTIMO nell'elenco, cosi' uno
    stato a meta' porta ancora le impronte di prima e gli step risultano «non
    valido» invece di «valido» su artefatti misti.
    """
    cartella = _cartella_di_scambio(out_dir, numero)
    dichiarazione = cartella / SCAMBIO
    if not dichiarazione.exists():
        return None
    letto = json.loads(dichiarazione.read_text(encoding="utf-8"))
    for nome in letto["file"]:
        nella_corsa = Path(out_dir) / nome
        nella_cartella = cartella / nome
        if nella_corsa.exists() and nella_cartella.exists():
            parcheggio = cartella / f"{nome}.scambio"
            nella_corsa.replace(parcheggio)
            nella_cartella.replace(nella_corsa)
            parcheggio.replace(nella_cartella)
        elif nella_corsa.exists():
            nella_corsa.replace(nella_cartella)
        elif nella_cartella.exists():
            nella_cartella.replace(nella_corsa)
    return {"da": letto["da"], "a": letto["a"]}
```

Aggiorna il docstring del modulo: dopo «sulla prima versione non c'e' niente prima, e risponde None.» aggiungi un paragrafo: «Dal 03/09/2026 una versione puo' essere un'esecuzione: porta una cartella `NNNN/` con cio' che l'esecuzione ha sostituito, e `scambia` la permuta con la corsa. Indietro e avanti restano funzioni del solo testo; lo scambio lo chiede il server, che sa quale versione sta togliendo.»

- [ ] **Step 4: Esegui i banchi**

Run: `PYTEST tests/test_storico.py`
Expected: `21 passed`.

- [ ] **Step 5: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add meshrec/src/meshrec/app/storico.py meshrec/tests/test_storico.py
git -C /home/mario/worktrees/storico-esecuzioni commit -m "feat(storico): una versione puo' portare una cartella di scambio" -m "Gli artefatti di un'esecuzione si spostano con un rename e tornano con lo stesso scambio: indietro e avanti sono la stessa operazione." -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 3: Il server deposita prima di eseguire, e lo scambio entra nel ritorno

> **Dispatch.** Agente: `backend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development`; `senior-backend` pertinente (cambia il contratto di quattro rotte: 409 nuovo, campi nuovi nella risposta) — almeno la lettura del workflow «API Design» prima del passo 6, e la verifica reale con `curl -i` su `/api/storico/indietro` a worker fermo e su `/api/step/2`, come il file dell'agente prescrive per ogni endpoint modificato. Sequenza: dopo il Task 2; nessun parallelo. Il Task 7.5 riscrive la rotta `/from` che questo passo introduce, quindi 7.5 sta dopo.
>
> **Ingressi degeneri.**
> - `metrics.json` illeggibile al deposito (troncato, non UTF-8, non oggetto) → `_dimentica_metriche` non solleva e **non lo riscrive**; la copia nella cartella di scambio è quella rotta, e l'esecuzione parte lo stesso
> - `metrics.json` o `steps.json` assenti al deposito → nessuno dei due viene creato (`steps.dimentica` con stato vuoto torna senza scrivere: banco `test_dimentica_senza_stato_non_crea_il_file`), il worker parte
> - `numero` fuori da 1..12 su `POST /api/step/{numero}` o `/from` → **oggi nessuna guardia** (`server.py:1573-1600` passa il numero al Worker tale quale); con `_avvia` diventa peggio: `steps.dimentica(range(0, 1))` fa `STEP_KEYS[-1]` e toglie in silenzio la voce del prior, `range(13, 14)` solleva `IndexError` dopo aver già depositato una versione. Oracolo: rifiuto 400 con `errore` prima del deposito, nessuna versione nuova in `.storico/`, worker fermo
> - `storico.deposita` solleva (`OSError`, disco pieno) → 400 con il motivo nel `messaggio`, `Worker.start` mai chiamato (banco `test_un_deposito_che_solleva_non_avvia_il_worker`)
> - worker in corso su `/api/storico/indietro` o `/avanti` → 409 `InCorso`, cursore fermo, nessun file scambiato; worker in corso su `/api/step/N` → il rifiuto di oggi (`RuntimeError` → 400), nessun deposito
> - `_ripristina` rifiuta prima dello scambio (testo `None`, versione illeggibile, `out_dir` di un'altra corsa) → nessun `rename` eseguito: lo scambio parte solo dopo la scrittura di `config.yaml` (spec §3.4)
> - «indietro» su una versione di esecuzione la cui cartella è stata cancellata a mano (`README`: `.storico/` si cancella quando serve spazio) → `scambia` torna `None`, la risposta dice `tipo: "configurazione"`, nessuna eccezione
> - esecuzione fallita poi annullata → `metrics.partial.json` finisce nella cartella, l'artefatto di prima torna nella corsa, lo step risponde «valido» (banco `test_annullare_un_esecuzione_fallita_rimette_lo_stato_di_prima`)
> - `steps.json` va **ultimo** in `scambio.json["file"]` → banco `test_eseguire_uno_step_deposita_prima_di_avviare` lo asserisce; se un giorno l'ordine cambia, uno scambio interrotto lascia «valido» su artefatti misti (spec §3.7)

**Files:**
- Modify: `meshrec/src/meshrec/core/steps.py` (dopo `write_state`)
- Modify: `meshrec/src/meshrec/app/server.py:1202-1333` (`_ripristina`, indietro, avanti), `:1573-1600` (le due rotte di esecuzione)
- Test: `meshrec/tests/test_steps.py`, `meshrec/tests/test_server.py`

**Interfaces:**
- Consumes: `storico.deposita(..., scambio=...)`, `storico.scambia`, `storico.cursore` (Task 2).
- Produces: `steps.dimentica(out_dir: Path, numeri: Iterable[int]) -> None`; risposta di `/api/storico/indietro` e `/avanti` con `tipo` e, per le esecuzioni, `da`/`a`; **409** con corpo `{"errore": "InCorso", "messaggio": ...}` quando il worker gira; `POST /api/step/N` e `/from` depositano prima di avviare.

- [ ] **Step 1: Banco per `steps.dimentica`**

In coda a `meshrec/tests/test_steps.py`:

```python
def test_dimentica_toglie_solo_le_voci_chieste(tmp_path):
    """Uno step che sta per essere rieseguito e' davvero «mai eseguito» finche'
    il worker non lo riscrive; gli altri restano com'erano."""
    steps.write_state(tmp_path, 1, "a", "riuscito", "01_cloud.ply", 1.0)
    steps.write_state(tmp_path, 2, "b", "riuscito", "02_segmented.ply", 1.0)
    steps.write_state(tmp_path, 3, "c", "riuscito", "03_downsampled.ply", 1.0)
    steps.dimentica(tmp_path, range(2, 4))
    assert set(steps.read_state(tmp_path)) == {"01_load"}


def test_dimentica_senza_stato_non_crea_il_file(tmp_path):
    steps.dimentica(tmp_path, [1])
    assert not (tmp_path / steps.STATE_FILENAME).exists()
```

(Se `test_steps.py` importa `steps` con un altro nome, adegua il nome: `from meshrec.core import steps` è la forma da usare se manca.)

- [ ] **Step 2: Esegui e vedili fallire**

Run: `PYTEST tests/test_steps.py`
Expected: due FAIL con `AttributeError: module 'meshrec.core.steps' has no attribute 'dimentica'`.

- [ ] **Step 3: Implementa `dimentica`**

In `meshrec/src/meshrec/core/steps.py`, dopo `write_state`:

```python
def dimentica(out_dir: Path, numeri: Iterable[int]) -> None:
    """Toglie le voci degli step `numeri`, lasciando le altre.

    Serve a chi sta per rieseguire quegli step dopo aver messo da parte i loro
    artefatti: finche' il worker non li riscrive sono «mai eseguito», e
    un'esecuzione da N a 12 che fallisce al passo k non deve lasciare
    «riuscito» sugli step k+1..12 con gli artefatti spostati altrove.
    """
    from meshrec.core.io import scrivi_atomico

    salvato = read_state(out_dir)
    if not salvato:
        return
    for numero in numeri:
        salvato.pop(STEP_KEYS[numero - 1], None)
    scrivi_atomico(
        Path(out_dir) / STATE_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(salvato, indent=2, ensure_ascii=False), encoding="utf-8"
        ),
    )
```

Aggiungi `from collections.abc import Iterable` agli import del modulo.

Run: `PYTEST tests/test_steps.py` — Expected: verdi.

- [ ] **Step 4: Banchi del server**

In coda a `meshrec/tests/test_server.py`:

```python
def _corsa_con_lo_step_2_eseguito(cliente, tmp_path: Path) -> Path:
    """Una corsa con un artefatto e uno stato scritti a mano, come li lascia
    un'esecuzione riuscita dello step 2. Senza worker: qui si prova il deposito
    e lo scambio, non la pipeline."""
    from meshrec.core import steps
    out_dir = tmp_path / "corsa"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "02_segmented.ply").write_bytes(b"voxel 2")
    cfg = load_config(tmp_path / "config.yaml")
    impronte = steps.step_fingerprints(cfg)
    steps.write_state(out_dir, 1, impronte[1], "riuscito", "01_cloud.ply", 1.0)
    steps.write_state(out_dir, 2, impronte[2], "riuscito", "02_segmented.ply", 1.0)
    (out_dir / "metrics.json").write_text(
        json.dumps({"01_load": {"points_kept": 10}, "02_segment": {"points_after": 5}}),
        encoding="utf-8",
    )
    return out_dir


def test_eseguire_uno_step_deposita_prima_di_avviare(cliente, tmp_path, monkeypatch):
    """Il deposito sta PRIMA di `lavoratore.start`: un'esecuzione senza deposito
    e' un'esecuzione non annullabile, ed e' proprio il caso da togliere."""
    from meshrec.app import storico
    out_dir = _corsa_con_lo_step_2_eseguito(cliente, tmp_path)
    avviati = []
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: avviati.append(argomenti))
    assert cliente.post("/api/step/2").status_code == 200
    assert avviati == [(tmp_path / "config.yaml", 2, 2)]
    numero = storico.cursore(out_dir)
    cartella = out_dir / storico.CARTELLA / f"{numero:04d}"
    assert (cartella / "02_segmented.ply").read_bytes() == b"voxel 2"
    assert not (out_dir / "02_segmented.ply").exists()
    dichiarato = json.loads((cartella / storico.SCAMBIO).read_text(encoding="utf-8"))
    assert dichiarato["da"] == 2 and dichiarato["a"] == 2
    assert dichiarato["file"][-1] == "steps.json", "steps.json va scambiato per ultimo"
    stato = json.loads((out_dir / "steps.json").read_text(encoding="utf-8"))
    assert "02_segment" not in stato and "01_load" in stato
    metriche = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert "02_segment" not in metriche and "01_load" in metriche


def test_un_deposito_che_solleva_non_avvia_il_worker(cliente, tmp_path, monkeypatch):
    from meshrec.app import storico
    _corsa_con_lo_step_2_eseguito(cliente, tmp_path)
    avviati = []
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: avviati.append(argomenti))

    def esplode(*_argomenti, **_parole):
        raise OSError("disco pieno")

    monkeypatch.setattr(storico, "deposita", esplode)
    risposta = cliente.post("/api/step/2")
    assert risposta.status_code == 400
    assert "disco pieno" in risposta.json()["messaggio"]
    assert avviati == []


def test_annullare_un_esecuzione_rimette_artefatto_stato_e_metriche(cliente, tmp_path, monkeypatch):
    out_dir = _corsa_con_lo_step_2_eseguito(cliente, tmp_path)
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: None)
    assert cliente.post("/api/step/2").status_code == 200
    # L'esecuzione «finisce»: scrive l'artefatto nuovo e lo stato nuovo.
    from meshrec.core import steps
    cfg = load_config(tmp_path / "config.yaml")
    (out_dir / "02_segmented.ply").write_bytes(b"voxel 5")
    steps.write_state(out_dir, 2, steps.step_fingerprints(cfg)[2], "riuscito", "02_segmented.ply", 2.0)
    (out_dir / "metrics.json").write_text(
        json.dumps({"01_load": {"points_kept": 10}, "02_segment": {"points_after": 3}}),
        encoding="utf-8",
    )

    indietro = cliente.post("/api/storico/indietro").json()
    assert indietro["annullato"] is True
    assert indietro["tipo"] == "esecuzione"
    assert (indietro["da"], indietro["a"]) == (2, 2)
    assert (out_dir / "02_segmented.ply").read_bytes() == b"voxel 2"
    assert json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))["02_segment"] == {"points_after": 5}
    stato = next(voce for voce in indietro["steps"] if voce["numero"] == 2)
    assert stato["secondi"] == 1.0, "lo stato rimesso e' quello di prima"

    avanti = cliente.post("/api/storico/avanti").json()
    assert avanti["annullato"] is True and avanti["tipo"] == "esecuzione"
    assert (out_dir / "02_segmented.ply").read_bytes() == b"voxel 5"


def test_annullare_un_esecuzione_fallita_rimette_lo_stato_di_prima(cliente, tmp_path, monkeypatch):
    out_dir = _corsa_con_lo_step_2_eseguito(cliente, tmp_path)
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: None)
    assert cliente.post("/api/step/2").status_code == 200
    from meshrec.core import steps
    cfg = load_config(tmp_path / "config.yaml")
    steps.write_state(out_dir, 2, steps.step_fingerprints(cfg)[2], "fallito", None, 0.0)
    (out_dir / "metrics.partial.json").write_text("{}", encoding="utf-8")

    indietro = cliente.post("/api/storico/indietro").json()
    assert indietro["annullato"] is True
    assert (out_dir / "02_segmented.ply").read_bytes() == b"voxel 2"
    assert not (out_dir / "metrics.partial.json").exists()
    assert next(voce for voce in indietro["steps"] if voce["numero"] == 2)["stato"] == "valido"


def test_annullare_una_configurazione_dice_il_proprio_tipo(cliente):
    corpo = cliente.get("/api/config").json()
    corpo["tet"]["min_ratio"] = 1.9
    assert cliente.put("/api/config", json=corpo).status_code == 200
    indietro = cliente.post("/api/storico/indietro").json()
    assert indietro["tipo"] == "configurazione"
    assert "da" not in indietro


def test_uno_step_fuori_intervallo_e_rifiutato_prima_del_deposito(cliente, tmp_path, monkeypatch):
    """Senza guardia `steps.dimentica(range(0, 1))` fa `STEP_KEYS[-1]` e toglie
    in silenzio la voce del prior; 13 solleva `IndexError` a versione già
    depositata. Il rifiuto sta prima del deposito: nessuna versione nuova."""
    from meshrec.app import storico
    out_dir = _corsa_con_lo_step_2_eseguito(cliente, tmp_path)
    avviati = []
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: avviati.append(argomenti))
    for percorso in ("/api/step/0", "/api/step/13", "/api/step/13/from"):
        risposta = cliente.post(percorso)
        assert risposta.status_code == 400, percorso
        assert "fra 1 e 12" in risposta.json()["messaggio"]
    assert not storico.esiste(out_dir)
    assert avviati == []


def test_lo_storico_rifiuta_con_409_mentre_un_worker_gira(cliente, monkeypatch):
    """Scambiare file sotto un processo che li sta scrivendo non ha un esito
    buono. 409 e non 400: la richiesta e' formata bene, e' il momento sbagliato."""
    monkeypatch.setattr(server.Worker, "is_running", lambda self: True)
    for verso in ("indietro", "avanti"):
        risposta = cliente.post(f"/api/storico/{verso}")
        assert risposta.status_code == 409, verso
        assert "interrompi il calcolo" in risposta.json()["messaggio"]
```

- [ ] **Step 5: Esegui e vedili fallire**

Run: `PYTEST tests/test_server.py -k "deposita_prima or non_avvia or rimette or dice_il_proprio_tipo or 409 or fuori_intervallo"`
Expected: sette FAIL (nessun deposito, nessun `tipo`, 200 invece di 409, nessun rifiuto su 0 e 13).

- [ ] **Step 6: Implementa nel server**

In `meshrec/src/meshrec/app/server.py`, dentro `create_app`, subito prima di `def _ripristina(...)`:

```python
    def _elenco_di_scambio(da: int, a: int) -> dict[str, object]:
        """I file che un'esecuzione da `da` ad `a` puo' riscrivere.

        Gli artefatti numerati vengono da `pipeline.ARTIFACTS`; gli step senza
        artefatto numerato scrivono il deck con il suo .vtu (11) e il prior
        (12). Il parziale delle metriche si sposta: lo lascia solo
        un'esecuzione fallita, e appartiene a lei. Stato e metriche si copiano,
        e steps.json sta per ULTIMO: e' l'ordine dello scambio, e uno scambio
        interrotto a meta' deve lasciare le impronte di prima.
        """
        sposta = [pipeline.ARTIFACTS[n] for n in range(da, a + 1) if n in pipeline.ARTIFACTS]
        if a >= 11:
            sposta += [pipeline.DECK_FILENAME, "wall_model.vtu"]
        if a >= 12:
            sposta.append(pipeline.WALL_FILENAME)
        sposta.append(pipeline.METRICS_PARTIAL)
        return {
            "da": da,
            "a": a,
            "sposta": sposta,
            "copia": [pipeline.METRICS_FILENAME, steps.STATE_FILENAME],
        }

    def _dimentica_metriche(out_dir: Path, numeri: range) -> None:
        percorso = out_dir / pipeline.METRICS_FILENAME
        if not percorso.exists():
            return
        try:
            letto = json.loads(percorso.read_text(encoding="utf-8"))
        except ValueError:
            return
        if not isinstance(letto, dict):
            return
        for numero in numeri:
            letto.pop(steps.STEP_KEYS[numero - 1], None)
        scrivi_atomico(
            percorso,
            lambda destinazione: destinazione.write_text(
                json.dumps(letto, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
            ),
        )

    def _avvia(da: int, a: int, endpoint: str) -> dict[str, object]:
        """Deposita, poi avvia. In quest'ordine e sotto lo stesso lucchetto
        dello storico: un'esecuzione senza deposito non si puo' annullare, e
        un deposito che solleva lascia il worker fermo con il motivo in
        risposta."""
        corrente()
        # La guardia sta PRIMA del deposito: `steps.dimentica(range(0, 1))`
        # farebbe `STEP_KEYS[-1]` e toglierebbe in silenzio la voce del prior,
        # e 13 solleverebbe `IndexError` a versione gia' depositata.
        if not (1 <= da <= a <= 12):
            raise ValueError(
                f"lo step va scelto fra 1 e 12 (chiesto {da}"
                + (f", fino a {a}" if a != da else "")
                + ")"
            )
        non_in_sola_lettura(f"eseguire lo step {da}" if da == a else f"eseguire dallo step {da} in giù")
        with _LUCCHETTO_STORICO:
            if lavoratore.is_running():
                raise RuntimeError("uno step sta già girando: annullalo prima di avviarne un altro")
            out_dir = Path(corrente().run.out_dir)
            if not storico.esiste(out_dir):
                storico.deposita(out_dir, config_path.read_text(encoding="utf-8"), "avvio", [])
            _deposita_le_modifiche_fatte_a_mano(out_dir)
            storico.deposita(
                out_dir, config_path.read_text(encoding="utf-8"), endpoint, [],
                scambio=_elenco_di_scambio(da, a),
            )
            steps.dimentica(out_dir, range(da, a + 1))
            _dimentica_metriche(out_dir, range(da, a + 1))
            lavoratore.start(config_path, da, a)
        return {"avviato": da, "fino_a": a}

    def _in_corso() -> JSONResponse | None:
        if not lavoratore.is_running():
            return None
        return JSONResponse(
            status_code=409,
            content={
                "errore": "InCorso",
                "messaggio": "uno step sta girando: aspetta la fine, oppure interrompi il calcolo",
            },
        )
```

`_avvia` deve stare **dopo** `lavoratore = Worker()` (riga 1567): mettila subito sotto quella riga, con `_elenco_di_scambio`, `_dimentica_metriche` e `_in_corso`. `_ripristina` invece resta dov'è: aggiungile il parametro `scambio: int` e, dopo `cfg_dopo = corrente()`:

```python
        esecuzione = storico.scambia(Path(cfg_dopo.run.out_dir), scambio)
        risposta: dict[str, object] = {
            "annullato": True,
            "tipo": "esecuzione" if esecuzione else "configurazione",
            "steps": steps.run_state(cfg_dopo.run.out_dir, cfg_dopo),
        }
        if esecuzione:
            risposta.update(esecuzione)
        return risposta
```

(al posto del `return {"annullato": True, "steps": ...}`; il commento sopra su «Gli artefatti restano sul disco» va riscritto: «Se la versione era un'esecuzione, i suoi artefatti tornano con lo scambio; per una configurazione restano, e la catena di impronte li marca da se'.») `_ripristina` è definita prima di `lavoratore`, ma usa solo `storico`: nessun problema di ordine.

Le due rotte dello storico:

```python
    @app.post("/api/storico/indietro")
    def storico_indietro() -> dict[str, object]:
        # docstring com'e' oggi
        with _LUCCHETTO_STORICO:
            non_in_sola_lettura("annullare una modifica")
            if (rifiuto := _in_corso()) is not None:
                return rifiuto
            out_dir = Path(corrente().run.out_dir)
            _deposita_le_modifiche_fatte_a_mano(out_dir)
            # Il numero PRIMA di muovere il cursore: e' la versione che
            # «indietro» toglie, e la sola che puo' avere una cartella da
            # scambiare.
            da_togliere = storico.cursore(out_dir)
            return _ripristina(
                storico.indietro(out_dir),
                "niente da annullare",
                lambda: storico.avanti(out_dir),
                scambio=da_togliere,
            )

    @app.post("/api/storico/avanti")
    def storico_avanti() -> dict[str, object]:
        with _LUCCHETTO_STORICO:
            non_in_sola_lettura("rifare una modifica")
            if (rifiuto := _in_corso()) is not None:
                return rifiuto
            out_dir = Path(corrente().run.out_dir)
            coda_tolta = _deposita_le_modifiche_fatte_a_mano(out_dir)
            vuoto = (... come oggi ...)
            testo = storico.avanti(out_dir)
            # Il numero DOPO: «avanti» rimette la versione su cui e' arrivato.
            return _ripristina(
                testo,
                vuoto,
                lambda: storico.indietro(out_dir),
                scambio=storico.cursore(out_dir),
            )
```

Le rotte di esecuzione diventano:

```python
    @app.post("/api/step/{numero}")
    def esegui_step(numero: int) -> dict[str, object]:
        return _avvia(numero, numero, f"POST /api/step/{numero}")

    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        # commento di oggi sul tetto 12: resta finche' il Task 7.5 lo porta a 11
        return _avvia(numero, 12, f"POST /api/step/{numero}/from")
```

Le rotte dello storico stanno prima di `lavoratore = Worker()` nel file: sposta `_in_corso` **sopra** `_ripristina` e falle leggere `lavoratore` per nome — è definita dopo ma usata a richiesta, quindi la chiusura la trova. Se `lavoratore` è definito dopo le rotte dello storico, sposta la riga `lavoratore = Worker()` subito dopo `def corrente()` (riga ~765): il Worker non dipende da nulla.

- [ ] **Step 6b: Il disco, dichiarato nel README**

In `meshrec/README.md`, nella sezione che descrive la cartella di una corsa (cerca «.storico» o «config.yaml»; se nessuna la nomina, sotto la sezione sull'interfaccia), aggiungi un paragrafo:

> `.storico/` tiene ogni versione della configurazione e, per ogni esecuzione fatta dall'interfaccia, gli artefatti che quell'esecuzione ha sostituito: è ciò che Ctrl+Z rimette. Non ha un tetto sugli artefatti recenti — cinquanta esecuzioni dello step 2 tengono cinquanta `02_segmented.ply` — e si cancella a mano quando serve spazio; cancellarla costa solo l'annullamento.

- [ ] **Step 7: Esegui i banchi del server**

Run: `PYTEST tests/test_server.py`
Expected: tutti verdi. Se `test_avviare_uno_step_risponde_senza_bloccare` (riga 131) fallisce perché ora `/api/step/1` deposita dentro `tmp_path / "corsa"` che non esiste ancora: `scrivi_atomico` crea i genitori (`core/io.py:143`, `path.parent.mkdir(parents=True, exist_ok=True)`), quindi `.storico/` nasce con il primo `.yaml` e la causa è un'altra: cercala nel banco, non in `deposita`.

- [ ] **Step 8: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add meshrec/src/meshrec/core/steps.py meshrec/src/meshrec/app/server.py meshrec/tests/test_steps.py meshrec/tests/test_server.py
git -C /home/mario/worktrees/storico-esecuzioni commit -m "feat(server): un'esecuzione si deposita prima di partire, e Ctrl+Z la annulla" -m "Artefatti, stato e metriche tornano quelli di prima con lo scambio; indietro e avanti rispondono 409 mentre un worker gira." -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 4: Gli step 5, 6 e 8 misurano la superficie

> **Dispatch.** Agente: `coder` (core numerico senza superficie API né UI; per il brief del progetto pipeline/README vanno a lui). Skill-gate: nessuna — `coder` non ha lo strumento `Skill` (`~/.claude/agents/coder.md`); il brief nomina `caveman` e `ponytail` come stile e ladder, non come skill da invocare; il banco prima del codice resta obbligatorio (sezione «Logica non banale» del suo file). Sequenza: dopo il Task 3; **potrebbe** girare in parallelo ai Task 2-3 (tocca solo `pipeline.py` e `test_pipeline.py`) ma non c'è un secondo worktree, quindi resta in catena. Attenzione al tempo: la fixture `run_dir` esegue la pipeline intera (~1 minuto per invocazione).
>
> **Ingressi degeneri.**
> - `faces` vuoto (lo step 6 può riscrivere una superficie vuota: `tests/test_pipeline.py:295-305` documenta il caso) → `step_metrics` tornano inalterate, `surface_metrics` non viene chiamata, nessun `IndexError` su `f[:, 0]`
> - chiave già scritta dallo step (`vertices`, `triangles`, `watertight_after` del 6) → vince il valore dello step, non quello di `surface_metrics` (banco: `metrics["06_repair"]["watertight_after"] == metrics["06_repair"]["watertight"]`, e `vertices` del 5 uguale a prima)
> - `area` o `volume` non finiti (superficie degenere) → `finito_o_none` (`core/quality.py:451-452`) li rende `None`; `metrics.json` resta serializzabile e uguale al dizionario tornato (`test_metrics_json_is_the_same_as_the_returned_dictionary`)
> - step 8 con `simplify.enabled = False` → `08_simplify` porta le misure della superficie **non** semplificata (la stessa del 6): è il comportamento atteso, non un errore, e il pannello del Task 5 lo mostra come fronte 8

**Files:**
- Modify: `meshrec/src/meshrec/core/pipeline.py:686-742`
- Test: `meshrec/tests/test_pipeline.py`

**Interfaces:**
- Produces: `metrics["05_reconstruct"]`, `["06_repair"]`, `["08_simplify"]` con le chiavi `vertices`, `triangles`, `watertight`, `boundary_edges`, `area`, `volume`, `aspect_ratio` in più (mai in sostituzione di una chiave che lo step scrive già).

- [ ] **Step 1: Banco sulla fixture `run_dir`**

In `meshrec/tests/test_pipeline.py`, dopo `test_the_run_directory_holds_config_metrics_and_the_deck`:

```python
def test_ogni_step_che_scrive_una_superficie_dice_se_e_chiusa(run_dir):
    """Il pannello del modello descrive il fronte, e il fronte puo' fermarsi al
    5: senza queste chiavi un fronte al 5 non saprebbe dire «aperta». Le chiavi
    proprie dello step non si toccano: `watertight_after` del 6 resta."""
    _out, metrics = run_dir
    for chiave in ("05_reconstruct", "06_repair", "08_simplify"):
        for misura in ("vertices", "triangles", "watertight", "boundary_edges", "area", "volume"):
            assert misura in metrics[chiave], f"{chiave} non porta {misura}"
    assert metrics["06_repair"]["watertight_after"] == metrics["06_repair"]["watertight"]
```

- [ ] **Step 2: Esegui e vedilo fallire**

Run: `PYTEST tests/test_pipeline.py::test_ogni_step_che_scrive_una_superficie_dice_se_e_chiusa`
Expected: FAIL su `05_reconstruct non porta watertight`. (La fixture esegue la pipeline intera: ~1 minuto.)

- [ ] **Step 3: Implementa**

In `pipeline.py`, sopra `def run(`:

```python
def _con_le_misure_della_superficie(
    step_metrics: dict[str, object], vertices: np.ndarray, faces: np.ndarray
) -> dict[str, object]:
    """Le misure di `surface_metrics` che lo step non ha gia' scritto.

    Il pannello del modello descrive il fronte, e il fronte puo' fermarsi a
    uno qualunque degli step che scrivono una superficie: senza queste chiavi
    un fronte al 5 non saprebbe dire «aperta». Le chiavi proprie dello step
    vincono: `watertight_after` del 6 resta com'e'.
    """
    if len(faces) == 0:
        return step_metrics
    return {**quality.surface_metrics(vertices, faces), **step_metrics}
```

E le tre assegnazioni diventano:

```python
            metrics["05_reconstruct"] = _con_le_misure_della_superficie(step_metrics, vertices, faces)
```

```python
            metrics["06_repair"] = _con_le_misure_della_superficie(step_metrics, vertices, faces)
```

```python
            metrics["08_simplify"] = _con_le_misure_della_superficie(step_metrics, vertices, faces)
```

`len(faces) == 0`: lo step 6 può riscrivere una superficie vuota (test_pipeline.py:300 lo documenta) e `surface_metrics` su zero facce indicizzerebbe un array vuoto.

- [ ] **Step 4: Esegui i banchi della pipeline**

Run: `PYTEST tests/test_pipeline.py`
Expected: tutti verdi, compreso `test_metrics_json_is_the_same_as_the_returned_dictionary`.

- [ ] **Step 5: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add meshrec/src/meshrec/core/pipeline.py meshrec/tests/test_pipeline.py
git -C /home/mario/worktrees/storico-esecuzioni commit -m "feat(pipeline): ogni step che scrive una superficie dice se e' chiusa" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 5: Il pannello «Modello» sotto la pipeline

> **Dispatch.** Agente: `frontend-engineer`, in modalità coordinatore (task aperto: markup + script + stile). Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `impeccable` (almeno `critique` o `audit` sulla zona `.zona-step` prima di scrivere il markup: è una sezione nuova nella colonna di sinistra, e il file dell'agente li prescrive), `superpowers:test-driven-development` per le tre funzioni pure. Verifica nel browser obbligatoria (passo 7). Sequenza: dopo il Task 4 (legge le chiavi che il 4 scrive); nessun parallelo. Vedi la «Nota sul banco di `app.js`» in cima: i quattro banchi del passo 1 vanno montati con `_DOM +` e con le costanti multi-riga estratte a parte.
>
> **Ingressi degeneri.**
> - `steps` vuoto, o senza nessuno step «valido», o con il solo `12_wall` valido → `fronteDelloStato` torna `null`, il pannello mostra «Nessuno step valido: esegui lo step 1», **nessuna** fetch a `/api/metrics`
> - `/api/metrics` risponde `{}` (file assente **o** rotto: `sweep.leggi_metriche`, `core/sweep.py:253-271`, torna `{}` in entrambi i casi e non solleva) → ogni riga «non misurato», nessuna eccezione. Nota: la spec §4.3 chiede «metriche non leggibili» per file assente o rotto, ma il server non distingue `{}` da «rotto»; il piano com'è scritto mostra «non misurato» su ogni riga e riserva «metriche non leggibili» al corpo che non è un oggetto o alla fetch fallita. Da dichiarare nel commit, non da risolvere qui
> - `/api/metrics` con corpo che non è un oggetto (`null`, testo non JSON via `corpoLetto`) oppure fetch fallita (`serverMuto`) → il pannello scrive «metriche non leggibili», `#modello-fronte` porta comunque il fronte, `#modello-righe` resta nascosto
> - percorso annidato interrotto a metà (`07_surface_quality.geometric_error` senza `cloud_to_mesh`, o `geometric_error` che è un numero) → «non misurato», non `TypeError: cannot read properties of undefined`
> - chiave del fronte senza tabella in `RIGHE_DEL_MODELLO` (`12_wall` è escluso a monte; una chiave futura) → `righeDelModello` torna `[]`, il `<dl>` è vuoto e visibile, nessuna eccezione
> - `fronte.impronta` o `fronte.secondi` `undefined` nello stato (step valido mai cronometrato) → `chiaveDelFronte` produce una stringa comunque e il confronto con la precedente non solleva
> - due cambi di fronte in rapida successione, la prima risposta arriva dopo la seconda → `superata(ordine, ultimoModello)` scarta la prima, il pannello mostra la seconda (stesso schema di `chiediStorico`)
> - valore non numerico né booleano (`method: "poisson"`, `element_type: "C3D4"`) → `String(valore)`; `extent` array → «2.759 × 785 × 2.000»; `watertight` con forma `chiusura` → «chiusa»/«aperta», non «sì»/«no»

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:125-137` (dentro `<nav class="zona zona-step">`, dopo `</ol>` alla riga 131)
- Modify: `meshrec/src/meshrec/ui/app.js` (nuove funzioni pure vicino a `disegnaStep`, riga ~495; chiamata in `disegnaStep`)
- Modify: `meshrec/src/meshrec/ui/stile.css` (dopo `.metriche dd.metrica-larga`)
- Test: `meshrec/tests/test_app_js.py`, `meshrec/tests/test_stile.py`

**Interfaces:**
- Consumes: `/api/metrics` (già esiste), `ultimoStato` (l'elenco degli step che `disegnaStep` riceve), `STEP_DEL_PRIOR`, `ETICHETTE`, `elemento`, `serverMuto`, `corpoLetto`.
- Produces: `fronteDelloStato(steps) -> voce | null`; `righeDelModello(fronte, metriche) -> Array<[etichetta, testo]>`; `aggiornaModello(steps)` chiamata da `disegnaStep`.

- [ ] **Step 1: Banchi sulle funzioni pure**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# Il pannello «Modello»: descrive il fronte, cioe' lo step valido di numero
# piu' alto, con i numeri che metrics.json porta gia'.
# --------------------------------------------------------------------------


def _tratto(inizio: str, fine: str) -> str:
    """Un tratto del modulo fra due ancore, per le costanti su piu' righe che
    `_costante` (una riga sola) non vede. Preso dal sorgente vero, per la
    stessa ragione di `_costante`."""
    testo = _modulo()
    return inizio + testo.split(inizio, 1)[1].split(fine, 1)[0]


# Le costanti e il formattatore del pannello, da `const NON_MISURATO` fino
# alla riga prima di `righeDelModello`: NON_MISURATO, valoreDelModello,
# RIGHE_DELLA_SUPERFICIE, RIGHE_DEL_MODELLO.
def _tabella_del_modello() -> str:
    return _tratto("const NON_MISURATO = ", "\n// Le righe del pannello") + "\n"


def test_il_fronte_e_lo_step_valido_di_numero_piu_alto(tmp_path):
    _esegui(tmp_path, _DOM + _funzioni("fronteDelloStato") + """
const steps = [
  { numero: 1, chiave: "01_load", stato: "valido" },
  { numero: 2, chiave: "02_segment", stato: "valido" },
  { numero: 3, chiave: "03_downsample", stato: "non valido" },
  { numero: 4, chiave: "04_normals", stato: "valido" },
  { numero: 5, chiave: "05_reconstruct", stato: "fallito" },
  { numero: 12, chiave: "12_wall", stato: "valido" },
];
assert.equal(fronteDelloStato(steps).numero, 4, "il fronte e' il valido piu' alto, prior escluso");
assert.equal(fronteDelloStato(steps.map((v) => ({ ...v, stato: "mai eseguito" }))), null);
assert.equal(fronteDelloStato([]), null);
""")


def test_le_righe_del_modello_leggono_le_chiavi_vere_e_dicono_non_misurato(tmp_path):
    _esegui(tmp_path, _DOM + _tabella_del_modello() + _funzioni("righeDelModello") + """
const metriche = {
  "05_reconstruct": { vertices: 1234, triangles: 2468, watertight: false, boundary_edges: 12, area: 1.5, volume: 0 },
  "01_load": { points_kept: 1000000, spacing: 1.19, extent: [2759, 785, 2000] },
};
const superficie = righeDelModello({ numero: 5, chiave: "05_reconstruct" }, metriche);
const perNome = Object.fromEntries(superficie);
assert.equal(perNome["vertici"], "1.234");
assert.equal(perNome["superficie"], "aperta");
assert.equal(perNome["spigoli di bordo"], "12");
const nuvola = Object.fromEntries(righeDelModello({ numero: 1, chiave: "01_load" }, metriche));
assert.equal(nuvola["punti"], "1.000.000");
assert.equal(nuvola["ingombro [mm]"], "2.759 × 785 × 2.000");
const vecchia = Object.fromEntries(righeDelModello({ numero: 6, chiave: "06_repair" }, { "06_repair": { vertices: 3 } }));
assert.equal(vecchia["vertici"], "3");
assert.equal(vecchia["superficie"], "non misurato", "una corsa vecchia non inventa la chiusura");
assert.deepEqual(righeDelModello({ numero: 7, chiave: "07_surface_quality" }, {}).map(([, v]) => v).every((v) => v === "non misurato"), true);
""")


def test_il_pannello_del_modello_sta_nel_markup_con_il_proprio_vuoto():
    markup = _senza_commenti_html(_markup())
    assert 'id="modello"' in markup
    vuoto = _elemento(markup, "modello-vuoto")
    assert "hidden" not in vuoto, "lo stato vuoto nasce visibile: a corsa aperta il fronte non c'e' ancora"
    assert 'id="modello-righe"' in markup


def test_il_modello_si_rilegge_solo_quando_il_fronte_cambia(tmp_path):
    """Il flusso SSE arriva ogni mezzo secondo; una fetch a ogni fotogramma
    sarebbero due richieste al secondo per niente. La terna (numero, impronta,
    secondi) e' cio' che cambia nei tre casi che contano: esecuzione finita,
    annullamento, parametro modificato."""
    _esegui(tmp_path, _DOM + _funzioni("fronteDelloStato", "chiaveDelFronte") + """
const a = { numero: 6, impronta: "abc", secondi: 12.5 };
assert.equal(chiaveDelFronte(a), chiaveDelFronte({ ...a }));
assert.notEqual(chiaveDelFronte(a), chiaveDelFronte({ ...a, secondi: 13 }));
assert.notEqual(chiaveDelFronte(a), chiaveDelFronte({ ...a, impronta: "abd" }));
assert.equal(chiaveDelFronte(null), "");
""")
```

- [ ] **Step 2: Esegui e vedili fallire**

Run: `PYTEST tests/test_app_js.py -k "fronte or modello"`
Expected: quattro FAIL (`IndexError` da `_sorgente_di`: la funzione non esiste; markup senza `id="modello"`).

- [ ] **Step 3: Il markup**

In `index.html`, dentro `<nav class="zona zona-step" ...>`, subito dopo `</ol>` e prima del commento sulla colonna che si chiude sullo step 11:

```html
    <!-- Il modello al fronte, cioe' allo step valido di numero piu' alto.
         Sta QUI, sotto la pipeline, perche' e' la risposta alla domanda che
         quella colonna fa nascere -- «e adesso che cosa ho in mano?» -- e
         perche' e' l'unico posto della schermata che era vuoto.
         I numeri vengono da metrics.json, che il server serve tal quale
         (/api/metrics): il pannello non ne calcola, come la colonna del
         dettaglio. Nel markup e non fabbricato da app.js, per la stessa
         ragione degli altri due vuoti di questa pagina. Nessun aria-live: il
         cambiamento lo annuncia gia' #conteggi. -->
    <section class="modello" id="modello" aria-labelledby="modello-titolo">
      <h2 id="modello-titolo">Modello</h2>
      <p class="aiuto" id="modello-fronte"></p>
      <p class="vuoto" id="modello-vuoto">Nessuno step valido: esegui lo step 1.</p>
      <dl class="metriche" id="modello-righe" hidden></dl>
    </section>
```

- [ ] **Step 4: Lo script**

In `app.js`, subito sopra `function disegnaStep(steps)`:

```js
// --- Il modello al fronte ---------------------------------------------------

// Lo step valido di numero piu' alto, prior escluso: e' cio' che si ha in
// mano adesso. Pura: si prova senza DOM.
function fronteDelloStato(steps) {
  let fronte = null;
  for (const voce of steps) {
    if (voce.stato !== "valido" || voce.chiave === STEP_DEL_PRIOR) continue;
    if (fronte === null || voce.numero > fronte.numero) fronte = voce;
  }
  return fronte;
}

// Cio' che, cambiando, chiede una rilettura di /api/metrics: un'esecuzione
// finita cambia i secondi, un annullamento l'impronta o il numero, un
// parametro modificato l'impronta. Il flusso SSE arriva ogni mezzo secondo,
// e rileggere a ogni fotogramma sarebbero due richieste al secondo per niente.
function chiaveDelFronte(fronte) {
  if (fronte === null) return "";
  return `${fronte.numero}|${fronte.impronta}|${fronte.secondi}`;
}

const NON_MISURATO = "non misurato";

// Un valore di metrics.json reso come testo del pannello. `chiusura` e' il
// solo booleano che si legge come stato e non come si'/no.
function valoreDelModello(valore, forma) {
  if (valore === undefined || valore === null) return NON_MISURATO;
  if (forma === "chiusura") return valore ? "chiusa" : "aperta";
  if (typeof valore === "boolean") return valore ? "sì" : "no";
  if (Array.isArray(valore)) return valore.map((v) => valoreDelModello(v)).join(" × ");
  if (typeof valore !== "number") return String(valore);
  if (Number.isInteger(valore)) return valore.toLocaleString("it");
  return valore.toLocaleString("it", { maximumSignificantDigits: 4 });
}

// [etichetta, percorso nelle metriche, forma]. Il percorso parte dalla chiave
// dello step: alcune righe leggono lo step a monte (il 4 non conta i punti,
// li ha contati il 3). Le chiavi sono quelle che pipeline.py scrive davvero,
// verificate su runs/lab_telaio_v2/metrics.json il 03/09/2026.
const RIGHE_DELLA_SUPERFICIE = (chiave) => [
  ["vertici", [chiave, "vertices"]],
  ["triangoli", [chiave, "triangles"]],
  ["superficie", [chiave, "watertight"], "chiusura"],
  ["spigoli di bordo", [chiave, "boundary_edges"]],
  ["area [mm²]", [chiave, "area"]],
  ["volume racchiuso [mm³]", [chiave, "volume"]],
];

const RIGHE_DEL_MODELLO = {
  "01_load": [
    ["punti", ["01_load", "points_kept"]],
    ["spaziatura media [mm]", ["01_load", "spacing"]],
    ["ingombro [mm]", ["01_load", "extent"]],
  ],
  "02_segment": [
    ["punti", ["02_segment", "points_after"]],
    ["punti tolti come rumore", ["02_segment", "outliers_removed"]],
    ["punti ritagliati", ["02_segment", "cropped_points"]],
  ],
  "03_downsample": [
    ["punti", ["03_downsample", "points_after"]],
    ["voxel [mm]", ["03_downsample", "voxel_size"]],
    ["riduzione", ["03_downsample", "reduction"]],
  ],
  "04_normals": [
    ["punti", ["03_downsample", "points_after"]],
    ["normali degeneri", ["04_normals", "degenerate_normals"]],
  ],
  "05_reconstruct": RIGHE_DELLA_SUPERFICIE("05_reconstruct"),
  "06_repair": RIGHE_DELLA_SUPERFICIE("06_repair"),
  "07_surface_quality": [
    ...RIGHE_DELLA_SUPERFICIE("07_surface_quality"),
    ["scarto dalla nuvola, RMS [mm]", ["07_surface_quality", "geometric_error", "cloud_to_mesh", "RMS"]],
    ["scarto dalla nuvola, massimo [mm]", ["07_surface_quality", "geometric_error", "cloud_to_mesh", "max"]],
  ],
  "08_simplify": RIGHE_DELLA_SUPERFICIE("08_simplify"),
  "09_tetrahedralize": [
    ["nodi", ["09_tetrahedralize", "nodes"]],
    ["tetraedri", ["09_tetrahedralize", "tets"]],
    ["punti di Steiner", ["09_tetrahedralize", "steiner_points"]],
    ["Steiner saturato", ["09_tetrahedralize", "steiner_saturated"]],
  ],
  "10_volume_quality": [
    ["nodi", ["10_volume_quality", "nodes"]],
    ["tetraedri", ["10_volume_quality", "tets"]],
    ["volume totale [mm³]", ["10_volume_quality", "total_volume"]],
    ["diedro minimo [°]", ["10_volume_quality", "min_dihedral_deg", "min"]],
    ["elementi rovesciati", ["10_volume_quality", "inverted"]],
  ],
  "11_export": [
    ["tipo di elemento", ["11_export", "element_type"]],
    ["nodi", ["10_volume_quality", "nodes"]],
    ["tetraedri", ["10_volume_quality", "tets"]],
    ["massa [t]", ["11_export", "mass"]],
    ["volume [mm³]", ["11_export", "volume"]],
  ],
};

// Le righe del pannello per il fronte dato: coppie [etichetta, testo]. Pura.
function righeDelModello(fronte, metriche) {
  const righe = RIGHE_DEL_MODELLO[fronte.chiave] ?? [];
  return righe.map(([etichetta, percorso, forma]) => {
    let valore = metriche;
    for (const passo of percorso) {
      valore = valore !== null && typeof valore === "object" ? valore[passo] : undefined;
    }
    return [etichetta, valoreDelModello(valore, forma)];
  });
}

let fronteMostrato = "";
let ultimoModello = 0;

function apriModello() {
  ultimoModello += 1;
  return ultimoModello;
}

async function aggiornaModello(steps) {
  const fronte = fronteDelloStato(steps);
  const chiave = chiaveDelFronte(fronte);
  if (chiave === fronteMostrato) return;
  fronteMostrato = chiave;
  const vuoto = document.getElementById("modello-vuoto");
  const righe = document.getElementById("modello-righe");
  const titolo = document.getElementById("modello-fronte");
  if (fronte === null) {
    titolo.textContent = "";
    vuoto.textContent = "Nessuno step valido: esegui lo step 1.";
    vuoto.hidden = false;
    righe.hidden = true;
    return;
  }
  const ordine = apriModello();
  const risposta = await fetch("/api/metrics").catch(serverMuto);
  const metriche = risposta.ok ? await corpoLetto(risposta) : null;
  if (superata(ordine, ultimoModello)) return;
  titolo.textContent = `dopo lo step ${fronte.numero}, ${ETICHETTE[fronte.chiave] ?? fronte.chiave}`;
  if (metriche === null || typeof metriche !== "object") {
    vuoto.textContent = "metriche non leggibili";
    vuoto.hidden = false;
    righe.hidden = true;
    return;
  }
  righe.replaceChildren(...righeDelModello(fronte, metriche).flatMap(([etichetta, testo]) => [
    elemento("dt", { textContent: etichetta }),
    elemento("dd", { textContent: testo }),
  ]));
  vuoto.hidden = true;
  righe.hidden = false;
}
```

`superata(ordine, ultimo)` è la funzione già usata dalle altre tratte (vedi `chiediStorico`): stessa firma a due argomenti.

In `disegnaStep`, dopo `segnaStepAperto(stepAperto);` aggiungi `aggiornaModello(steps);`. In `chiediStorico`, dopo `await caricaStato();` non serve altro: `caricaStato` chiama `disegnaStep`.

- [ ] **Step 5: Lo stile**

In `stile.css`, dopo `.metriche dd.metrica-larga { ... }`:

```css
/* Il pannello del modello, sotto la pipeline. Riusa .metriche per le righe:
   stessa griglia e stesse cifre tabulari della colonna del dettaglio, cosi'
   «vertici 1.234» si legge uguale nelle due colonne. Solo lo stacco dal
   titolo e' suo: e' la seconda sezione della zona, e il primo titolo della
   zona non ha niente sopra da cui staccarsi. */
.modello { margin-top: var(--passo-6); }
.modello h2 { margin-top: 0; }
```

(Se `--passo-6` non esiste nel foglio, usa il passo più grande dichiarato in `:root`: `grep -n "^\s*--passo" stile.css`.)

- [ ] **Step 6: Esegui i banchi**

Run: `PYTEST tests/test_app_js.py tests/test_stile.py`
Expected: verdi. Se `test_stile.py` sorveglia che ogni classe usata nel markup abbia una regola (cerca «classi» nel file), `.modello` la ha.

- [ ] **Step 7: Prova a mano, una volta**

Avvia il server dal worktree su una corsa di prova e guarda che il pannello compaia e cambi dopo un'esecuzione. Comando (una riga):

```
LD_LIBRARY_PATH=/home/mario/.local/pkg/root/usr/lib/x86_64-linux-gnu PYTHONPATH=/home/mario/worktrees/storico-esecuzioni/meshrec/src /home/mario/.venvs/meshrec/bin/python -c "from meshrec.cli import main; main(['serve','--no-browser','--port','8765'])"
```

Poi `curl -s http://127.0.0.1:8765/ | grep -c 'id="modello"'` deve dare `1`. Ferma il server.

- [ ] **Step 8: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/app.js meshrec/src/meshrec/ui/stile.css meshrec/tests/test_app_js.py meshrec/tests/test_stile.py
git -C /home/mario/worktrees/storico-esecuzioni commit -m "feat(interfaccia): il modello al fronte si legge sotto la pipeline" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 6: Il registro si chiude, e Ctrl+Z dice che cosa ha annullato

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` per `fraseDelRitorno` e `ultimaRigaDelRegistro`; `impeccable` (`critique` sul `<details>` chiuso e sul `summary`: è un cambio di gerarchia della colonna Dettaglio, e il file dell'agente lo prescrive per un task aperto). Sequenza: dopo il Task 5 (stesso `app.js`, stesso `index.html`); nessun parallelo. I quattro banchi del passo 1 con `_DOM +` (nota in cima).
>
> **Ingressi degeneri.**
> - risposta di `/api/storico/*` senza `tipo` (versione di configurazione, o server che precede il Task 3) → `fraseDelRitorno(prima, dopo, null)` dice «configurazione ripristinata: …», nessuna eccezione su `corpo.da`
> - `esecuzione.da === esecuzione.a` → «dello step N»; `a === 11` → «all'11» (apostrofo, non «al 11»); `da < a < 11` → «dallo step N al M»
> - registro vuoto, o con sole righe bianche, al fronte di discesa di un fallimento → `ultimaRigaDelRegistro()` torna «nessun dettaglio», la frase in `#esito` resta completa
> - esecuzione riuscita → `#registro-dettagli.open` non cambia (né si apre, né si richiude se l'utente l'aveva aperto); esecuzione fallita → `open = true`
> - `#registro-dettagli` assente dal DOM (banco vecchio con `_DOM` che non lo dichiara) → i banchi esistenti del registro (`test_app_js.py:520-570`) restano verdi perché il `div#registro` non cambia; il nuovo ascoltatore legge l'elemento solo sul fronte di discesa con errore

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:58-59` (riga della testata), `:253-266` (registro)
- Modify: `meshrec/src/meshrec/ui/app.js:653-690` (`esitoDellaCorsa`), `:955-985` (`fraseDelRitorno`), `:1049` (chiamata in `chiediStorico`), `:1076-1089` (ascoltatore `riga`), `:876-886` (`aggiornaDaStato`, fronte di discesa)
- Test: `meshrec/tests/test_app_js.py`

**Interfaces:**
- Consumes: `tipo`, `da`, `a` nella risposta di `/api/storico/*` (Task 3).
- Produces: `fraseDelRitorno(prima, dopo, esecuzione = null)`; `ultimaRigaDelRegistro()`.

- [ ] **Step 1: Banchi**

In coda a `meshrec/tests/test_app_js.py`:

```python
def test_il_registro_sta_in_un_details_chiuso_alla_nascita():
    """Chiuso e non tolto: serve ancora a leggere perche' uno step e' fallito,
    ma a riposo non deve occupare quattordici righe della colonna."""
    markup = _senza_commenti_html(_markup())
    dettagli = _elemento(markup, "registro-dettagli")
    assert dettagli.startswith("<details"), dettagli
    assert " open" not in dettagli, "il registro nasce chiuso"
    assert 'tabindex="0"' in _elemento(markup, "registro")


def test_la_testata_nomina_le_esecuzioni_fra_le_cose_che_ctrl_z_annulla():
    assert "annulla l'ultima modifica o esecuzione" in _markup()


def test_la_frase_del_ritorno_antepone_l_esecuzione_annullata(tmp_path):
    # ETICHETTE e' su piu' righe: `_costante` non la vede, `_tratto` (Task 5) si'.
    _esegui(tmp_path, _DOM + _tratto("const ETICHETTE = ", "\n};\n") + "\n};\n" + _funzioni("fraseDelRitorno") + """
const prima = [{ numero: 2, chiave: "02_segment", stato: "non valido" }];
const dopo = [{ numero: 2, chiave: "02_segment", stato: "valido" }];
assert.match(fraseDelRitorno(prima, dopo), /^configurazione ripristinata/);
assert.match(fraseDelRitorno(prima, dopo, { da: 2, a: 2 }), /^esecuzione dello step 2 annullata/);
assert.match(fraseDelRitorno(prima, dopo, { da: 2, a: 11 }), /^esecuzione dallo step 2 all'11 annullata/);
""")


def test_un_fallimento_porta_l_ultima_riga_del_registro_e_lo_apre(tmp_path):
    _esegui(tmp_path, _DOM + _funzioni("esitoDellaCorsa", "ultimaRigaDelRegistro", "descrizioneDellaCorsa", "nomeDelloStep") + """
const registro = document.getElementById("registro");
for (const testo of ["Traceback", "", "ValueError: nessun punto"]) {
  const riga = document.createElement("div"); riga.textContent = testo; registro.append(riga);
}
assert.equal(ultimaRigaDelRegistro(), "ValueError: nessun punto");
const { errore } = esitoDellaCorsa({ exit_code: 1, annullato: false, step: 2, a_step: 2, steps: [] });
assert.match(errore, /ValueError: nessun punto/);
assert.match(errore, /nel registro/);
""")
```

Se `esitoDellaCorsa` usa altre funzioni oltre a `descrizioneDellaCorsa` e `nomeDelloStep` (leggi il suo corpo alle righe 640-690), aggiungile a `_funzioni`. Il DOM finto (`_DOM`) deve avere un elemento con id `registro`: se `document.getElementById` del finto legge da una mappa, registralo come fanno gli altri banchi del registro (riga 541-570).

- [ ] **Step 2: Esegui e vedili fallire**

Run: `PYTEST tests/test_app_js.py -k "details or ctrl_z or ritorno or fallimento"`
Expected: quattro FAIL.

- [ ] **Step 3: Markup**

`index.html`, riga 58-59:

```html
  <p class="aiuto scorciatoia"><kbd>Ctrl/Cmd</kbd>+<kbd>Z</kbd> annulla l'ultima
    modifica o esecuzione, con <kbd>Maiusc</kbd> la rifà.</p>
```

Registro (righe 253-266): l'`<h2>Registro</h2>` esce; il `div` resta e si avvolge:

```html
    <!-- Chiuso e non tolto. Serve a una cosa sola, leggere perche' uno step
         e' fallito, e per quella si apre da solo (app.js, fronte di discesa
         di un'esecuzione fallita). A riposo occupava quattordici righe della
         colonna per lo stdout di TetGen, che nessuno legge mentre gira. -->
    <details id="registro-dettagli" class="registro-dettagli">
      <summary>Registro dell'esecuzione</summary>
      <!-- i due commenti su tabindex e aria-live restano qui, invariati -->
      <div class="registro" id="registro" role="log" aria-live="off" tabindex="0"></div>
    </details>
```

- [ ] **Step 4: Script**

`app.js`: la frase del fallimento in `esitoDellaCorsa` diventa

```js
      errore: `${soggetto}: esecuzione fallita (codice ${stato.exit_code}). `
        + `Il motivo è nel registro, in fondo alla colonna Dettaglio: ${ultimaRigaDelRegistro()}`,
```

e sopra `esitoDellaCorsa`:

```js
// L'ultima riga non vuota che il flusso ha portato: quella che dice che cosa
// e' successo, senza le venti che dicono da dove. E' la riga che chi legge
// cercherebbe per prima, e chi non apre il registro la ha gia' in testata.
function ultimaRigaDelRegistro() {
  const righe = Array.from(document.getElementById("registro").children);
  for (let i = righe.length - 1; i >= 0; i -= 1) {
    const testo = righe[i].textContent.trim();
    if (testo !== "") return testo;
  }
  return "nessun dettaglio";
}
```

In `aggiornaDaStato`, nel ramo del fronte di discesa, dopo `mostraEsito(errore, esito);`:

```js
    // Il registro si apre solo quando c'e' un motivo da leggere: aperto a
    // ogni esecuzione riuscita sarebbe la sezione di prima con un clic in piu'.
    if (errore !== null) document.getElementById("registro-dettagli").open = true;
```

`fraseDelRitorno(prima, dopo, esecuzione = null)`: il `return` finale diventa

```js
  const stati = pezzi.length ? pezzi.join("; ") : "nessuno step cambia stato";
  if (esecuzione === null) return `configurazione ripristinata: ${stati}`;
  const dove = esecuzione.da === esecuzione.a
    ? `dello step ${esecuzione.da}`
    : `dallo step ${esecuzione.da} ${esecuzione.a === 11 ? "all'11" : `al ${esecuzione.a}`}`;
  return `esecuzione ${dove} annullata: ${stati}`;
```

e in `chiediStorico` la chiamata diventa
`mostraEsito(null, fraseDelRitorno(prima, corpo.steps, corpo.tipo === "esecuzione" ? { da: corpo.da, a: corpo.a } : null));`.
Il `ragioneDelRifiuto` di oggi legge già `messaggio` dal 409: nessuna modifica per il rifiuto.

Nel commento sopra `gestoDelloStorico` («ognuno qui e' un POST che riscrive config.yaml davvero») aggiungi «— e, per un'esecuzione, sposta anche gli artefatti».

- [ ] **Step 5: Stile**

In `stile.css`, accanto a `.registro`:

```css
/* Il riassunto del registro chiuso: un comando, e come gli altri comandi si
   vede dove sta il fuoco. */
.registro-dettagli > summary { cursor: pointer; color: var(--tenue); font-weight: 600; margin-top: var(--passo-4); }
.registro-dettagli > summary:focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
```

Aggiungi `".registro-dettagli > summary"` alla tupla delle famiglie in `test_stile.py:269`.

- [ ] **Step 6: Esegui i banchi**

Run: `PYTEST tests/test_app_js.py tests/test_stile.py`
Expected: verdi; i banchi vecchi del registro (tabindex, aria-live, tetto) restano verdi perché il `div#registro` non è cambiato.

- [ ] **Step 7: Commit**

```bash
git -C /home/mario/worktrees/storico-esecuzioni add meshrec/src/meshrec/ui meshrec/tests/test_app_js.py meshrec/tests/test_stile.py
git -C /home/mario/worktrees/storico-esecuzioni commit -m "feat(interfaccia): il registro si chiude, e Ctrl+Z dice che cosa ha annullato" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1"
```

---

### Task 7.1: Il predefinito si vede, e si rimette

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` per `testoDellAiuto`; `impeccable` non richiesto (un bottone secondario dentro un pattern `.campo` già esistente: task S, si dichiara il salto nel report). Sequenza: dopo il Task 6, primo del lotto 7.x; serializzato sullo stesso worktree (vedi «Sequenza di dispatch»). Banco con `_DOM +`.
>
> **Ingressi degeneri.**
> - `campo.default` `undefined` o `null` → nessun «predefinito: …» nell'aiuto e nessun bottone «Riporta»
> - `campo.default` falsy ma presente (`0`, `false`, `""`) → «predefinito: 0» / «predefinito: false» / «predefinito: » compaiono, e il bottone c'è: il controllo è `!== undefined && !== null`, non `if (campo.default)`
> - campo non scalare (blocco, lista) → nessun bottone, l'aiuto dice «si modifica dal file di configurazione» come oggi
> - «Riporta» su corsa in sola lettura → `scriviValore` riceve il rifiuto del server e lo scrive nella riga del campo, come per un valore digitato; nessuna eccezione, il campo torna al valore di prima
> - `description` assente e `default` presente → l'aiuto dice solo «predefinito: X», senza « — » iniziale

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:2500-2515` (l'aiuto del campo), `:2125-2195` (`scriviValore`, letta e non modificata)
- Test: `meshrec/tests/test_app_js.py`

- [ ] **Step 1: Banco**

```python
def test_l_aiuto_del_campo_dice_il_predefinito(tmp_path):
    _esegui(tmp_path, _DOM + _funzioni("testoDellAiuto") + """
assert.equal(testoDellAiuto({ description: "profondità dell'albero", default: 8 }, true, false), "profondità dell'albero — predefinito: 8");
assert.equal(testoDellAiuto({ default: null }, true, false), "");
assert.equal(testoDellAiuto({ description: "x" }, false, false), "x — si modifica dal file di configurazione");
""")
```

(`testoDellAiuto` è pura e non usa altre funzioni del modulo.)

- [ ] **Step 2: Vedilo fallire** — Run: `PYTEST tests/test_app_js.py::test_l_aiuto_del_campo_dice_il_predefinito`. Expected: FAIL.

- [ ] **Step 3: Implementa**

Sopra la funzione che costruisce il campo (quella che contiene `aiuto.className = "aiuto"`), estrai:

```js
// Il testo dell'aiuto sotto un campo. Il predefinito si dice: chi ha girato
// min_ratio tre volte deve sapere da dove e' partito, e /api/schema lo manda
// gia' -- il pannello lo usava solo per piegare i campi fermi.
function testoDellAiuto(campo, scalare, bloccoAssente) {
  return [
    campo.description,
    campo.default !== undefined && campo.default !== null ? `predefinito: ${String(campo.default)}` : null,
    !scalare && !bloccoAssente ? "si modifica dal file di configurazione" : null,
  ].filter(Boolean).join(" — ");
}
```

e sostituisci `aiuto.textContent = [...].filter(Boolean).join(" — ");` con `aiuto.textContent = testoDellAiuto(campo, scalare, bloccoAssente);`.

Il bottone «Riporta»: dopo `riga.append(input);` e prima dell'aiuto:

```js
  if (scalare && campo.default !== undefined && campo.default !== null) {
    const riporta = elemento("button", { type: "button", className: "bottone riporta", textContent: "Riporta" });
    riporta.title = `riporta al predefinito (${String(campo.default)})`;
    riporta.addEventListener("click", () => {
      input.value = String(campo.default);
      scriviValore(blocco, nome, campo.default, input, messaggio, ordine);
    });
    riga.append(riporta);
  }
```

(usa i nomi delle variabili che quella funzione ha davvero per `blocco`, `nome`, `messaggio`, `ordine`: sono quelli passati a `scriviParametro` due righe sopra.) In `stile.css`, accanto alle regole di `.campo`: `.campo .riporta { justify-self: start; font-size: var(--tipo-nota); }`.

- [ ] **Step 4: Verdi** — Run: `PYTEST tests/test_app_js.py`.

- [ ] **Step 5: Commit** — `feat(interfaccia): ogni campo dice il proprio predefinito, e lo rimette`.

---

### Task 7.2: La scheda dice quando ha finito

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` per `titoloConEsito`; `impeccable` non richiesto (un bottone nella testata, task S; salto dichiarato). Sequenza: dopo 7.1, serializzato. Banco con `_DOM +`.
>
> **Ingressi degeneri.**
> - `Notification` non definita (DOM finto di `node`, browser senza l'API) → nessuna eccezione al caricamento del modulo, `#notifiche` nascosto, il titolo cambia lo stesso
> - `Notification.permission === "denied"` → bottone nascosto, nessuna notifica, nessuna richiesta di permesso
> - pagina a fuoco (`document.hasFocus()` vero) al fronte di discesa → nessuna notifica; titolo «✓ MeshRec» o «✗ MeshRec» e ritorno a «MeshRec» al `focus` successivo
> - fronte di discesa con `errore` e `esito` entrambi `null` → titolo «MeshRec», `notificaFuoriDallaScheda("")` non solleva e non manda una notifica vuota
> - clic su `#notifiche` con risposta «default» (finestra chiusa senza scegliere) → il bottone resta visibile e si può richiedere

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:870-880` (`aggiornaDaStato`, fronte di discesa), `:747-751` (`mostraEsito`)
- Modify: `meshrec/src/meshrec/ui/index.html` (testata, dopo «Interrompi il calcolo»)
- Test: `meshrec/tests/test_app_js.py`

- [ ] **Step 1: Banco**

```python
def test_il_titolo_della_scheda_porta_l_esito(tmp_path):
    _esegui(tmp_path, _DOM + _funzioni("titoloConEsito") + """
assert.equal(titoloConEsito(null, null), "MeshRec");
assert.equal(titoloConEsito(null, "Segmentazione: conclusa"), "✓ MeshRec");
assert.equal(titoloConEsito("Segmentazione: fallita", null), "✗ MeshRec");
""")


def test_il_permesso_di_notifica_si_chiede_con_un_bottone_e_mai_da_solo():
    testo = _modulo()
    assert "Notification.requestPermission" in testo
    assert 'getElementById("notifiche")' in testo, "il permesso si chiede da un bottone"
    assert 'id="notifiche"' in _markup()
```

- [ ] **Step 2: Vedili fallire**, poi **Step 3: implementa**

`app.js`, sopra `mostraEsito`:

```js
// Il titolo della scheda come segnale: chi ha cambiato finestra durante i
// minuti di uno step vede il segno nella barra delle schede. Torna «MeshRec»
// al fuoco sulla pagina.
function titoloConEsito(errore, esito) {
  if (errore) return "✗ MeshRec";
  if (esito) return "✓ MeshRec";
  return "MeshRec";
}

function notificaFuoriDallaScheda(testo) {
  // Solo se il permesso e' gia' stato dato dal bottone: chiederlo qui, nel
  // mezzo di un esito, e' la finestra che ogni sito apre senza motivo.
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  if (document.hasFocus()) return;
  new Notification("MeshRec", { body: testo });
}
```

In `aggiornaDaStato`, dopo `mostraEsito(errore, esito);` (fronte di discesa):

```js
    document.title = titoloConEsito(errore, esito);
    notificaFuoriDallaScheda(errore ?? esito ?? "");
```

In coda al modulo:

```js
window.addEventListener("focus", () => { document.title = "MeshRec"; });

document.getElementById("notifiche").addEventListener("click", async (evento) => {
  if (typeof Notification === "undefined") return;
  const permesso = await Notification.requestPermission();
  evento.currentTarget.hidden = permesso !== "default";
});
if (typeof Notification === "undefined" || Notification.permission !== "default") {
  document.getElementById("notifiche").hidden = true;
}
```

`index.html`, nella testata dopo il bottone «Interrompi il calcolo»:

```html
  <!-- Il permesso di notifica si chiede una volta, da qui, e il bottone
       sparisce con la risposta -- qualunque sia. Chiederlo da solo alla
       prima esecuzione e' la finestra che ogni sito apre senza motivo. -->
  <button type="button" id="notifiche" class="bottone">Avvisami a fine corsa</button>
```

- [ ] **Step 4: Verdi**, **Step 5: Commit** — `feat(interfaccia): la scheda e una notifica dicono quando la corsa e' finita`.

---

### Task 7.3: «Inquadra» e «Salva immagine»

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` per `nomeDellImmagine`; `impeccable` (`critique` o `layout` sui due bottoni sopra la tela: si sovrappongono a `#conteggi` e alla scala, e il posto va deciso guardando). Verifica nel browser: il PNG scaricato apre e non è nero (`preserveDrawingBuffer` in `viewport.js`). Sequenza: dopo 7.2, serializzato. Banco con `_DOM +`.
>
> **Ingressi degeneri.**
> - `stepScelto === null` (nessuno step scelto) → clic su «Salva immagine» non fa niente, nessuna eccezione, nessun download
> - didascalia vuota → nome senza il pezzo finale e senza trattino pendente (`corsa-05-superficie.png`); didascalia con accenti, virgole, unità (`scarto RMS 9,5 mm`) → solo `[a-z0-9-]`, senza trattini doppi né agli estremi
> - `outDir` con separatori Windows (`runs\\lab`), con slash finale, o vuoto → ultimo segmento non vuoto, altrimenti «corsa»
> - `ultimoStato` senza la voce di `stepScelto` → etichetta `step N`, non «undefined»
> - «Inquadra» senza modello caricato → `vista.inquadra()` non solleva (verificare in `viewport.js` che cosa fa a scena vuota; se solleva, la guardia sta nel bottone)

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:200-215` (dentro `#viewport`, prima del comando del taglio)
- Modify: `meshrec/src/meshrec/ui/app.js` (in coda; usa `vista.inquadra()`, `vista.cattura()`, `#didascalia-vista`, `stepScelto`, `ETICHETTE`, `ultimoStato`)
- Modify: `meshrec/src/meshrec/ui/stile.css`
- Test: `meshrec/tests/test_app_js.py`

- [ ] **Step 1: Banco**

```python
def test_il_nome_del_file_dell_immagine_porta_corsa_step_e_didascalia(tmp_path):
    _esegui(tmp_path, _DOM + _funzioni("nomeDellImmagine") + """
assert.equal(nomeDellImmagine("runs/lab_telaio_v2", 6, "Riparazione", "scarto RMS 9,5 mm"), "lab_telaio_v2-06-riparazione-scarto-rms-9-5-mm.png");
assert.equal(nomeDellImmagine("corsa", 5, "Superficie", ""), "corsa-05-superficie.png");
""")


def test_i_due_comandi_della_vista_stanno_nel_markup():
    markup = _senza_commenti_html(_markup())
    assert 'id="inquadra"' in markup and 'id="salva-immagine"' in markup
```

- [ ] **Step 2: Vedili fallire**, **Step 3: implementa**

`index.html`, dentro `#viewport` subito prima di `<label id="fantasma-comando" ...>`:

```html
      <!-- I due comandi della vista che mancavano: `inquadra` e `cattura`
           esistono in viewport.js da agosto e nessun bottone le chiamava;
           preserveDrawingBuffer era pagato per una cattura che non c'era.
           Il PNG lo scrive il browser, dove l'utente lo trova: nessuna rotta. -->
      <div class="comandi-vista">
        <button type="button" id="inquadra" class="bottone">Inquadra</button>
        <button type="button" id="salva-immagine" class="bottone">Salva immagine</button>
      </div>
```

`app.js`, in coda:

```js
// Il nome del file: corsa, step e didascalia, cosi' l'immagine in appendice
// dice da sola che cosa mostra. Solo lettere, cifre e trattini: e' un nome di
// file su tre sistemi diversi.
function nomeDellImmagine(outDir, numero, nome, didascalia) {
  const corsa = String(outDir).split(/[\\/]/).filter(Boolean).pop() ?? "corsa";
  const pezzi = [corsa, String(numero).padStart(2, "0"), nome, didascalia]
    .filter((pezzo) => pezzo !== "" && pezzo !== null && pezzo !== undefined)
    .map((pezzo) => String(pezzo).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  return `${pezzi.join("-")}.png`;
}

document.getElementById("inquadra").addEventListener("click", () => vista.inquadra());

document.getElementById("salva-immagine").addEventListener("click", () => {
  if (stepScelto === null) return;
  const voce = ultimoStato.find((v) => v.numero === stepScelto);
  const collegamento = document.createElement("a");
  collegamento.href = vista.cattura();
  collegamento.download = nomeDellImmagine(
    document.getElementById("corsa").textContent,
    stepScelto,
    ETICHETTE[voce?.chiave] ?? `step ${stepScelto}`,
    document.getElementById("didascalia-vista").textContent,
  );
  collegamento.click();
});
```

`vista` è l'oggetto che `app.js` crea da `viewport.js` (`grep -n "const vista" app.js`): usa quel nome. `stile.css`: `.comandi-vista { position: absolute; top: var(--passo-2); right: var(--passo-2); display: flex; gap: var(--passo-2); }` — verifica che `#viewport` sia `position: relative` (lo è per `#conteggi` e la scala: `grep -n "^.viewport" stile.css`).

- [ ] **Step 4: Verdi**, **Step 5: Commit** — `feat(vista): due bottoni inquadrano e salvano l'immagine`.

---

### Task 7.4: Invio crea la corsa

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: nessuna skill oltre `caveman:caveman` e `ponytail:ponytail` — task meccanico (un `<form>` attorno a markup esistente, un ascoltatore che cambia evento, corpo invariato), salto di `impeccable` e TDD dichiarato nel report; il banco del passo 1 è di sorveglianza sul sorgente, non di logica. Sequenza: dopo 7.3, serializzato.
>
> **Ingressi degeneri.**
> - Invio nel campo con nome vuoto o non valido → `ragioneLocale` scrive nella riga d'errore (`role="alert"`), nessuna richiesta a `/api/corse`, nessuna bolla del browser (`novalidate`)
> - Invio ripetuto mentre la richiesta è in volo → il bottone è già `disabled` (`app.js:375`) e il form non manda una seconda `POST`: una sola corsa creata; da verificare che `submit` da tastiera rispetti il `disabled` del bottone (lo fa: un form senza bottone di submit abilitato non si manda con Invio)
> - clic sul bottone → stesso percorso di Invio (`type="submit"` dentro il form), un solo ascoltatore

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:81-115`
- Modify: `meshrec/src/meshrec/ui/app.js:366-372` (ascoltatore di `#crea-corsa`)
- Test: `meshrec/tests/test_app_js.py`

- [ ] **Step 1: Banco**

```python
def test_l_ingresso_e_un_form_e_invio_lo_manda():
    markup = _senza_commenti_html(_markup())
    assert re.search(r'<form[^>]*id="nuova-corsa"', markup), "i due campi e il bottone stanno in un <form>"
    assert 'type="submit"' in _elemento(markup, "crea-corsa")
    assert 'getElementById("nuova-corsa").addEventListener("submit"' in _modulo()
```

- [ ] **Step 2: Vedilo fallire**, **Step 3: implementa**

`index.html`: avvolgi da `<label class="campo" for="nuova-nome">` fino al bottone «Crea la corsa» compreso in `<form id="nuova-corsa" novalidate>` … `</form>`; il bottone diventa `type="submit"`. `app.js`: `document.getElementById("crea-corsa").addEventListener("click", async (evento) => { const bottone = evento.currentTarget; ...` diventa

```js
document.getElementById("nuova-corsa").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const bottone = document.getElementById("crea-corsa");
```

con il resto del corpo invariato. `novalidate` perché la validazione la fa `ragioneLocale`, che scrive nella riga d'errore con `role="alert"`: la bolla del browser la coprirebbe.

- [ ] **Step 4: Verdi**, **Step 5: Commit** — `fix(ingresso): Invio crea la corsa`.

---

### Task 7.5: «Esegui da qui in giù» si ferma al deck

> **Dispatch.** Agente: `backend-engineer` (la modifica di sostanza è nel server; l'etichetta in `app.js:3075` è una stringa). Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` (banco del passo 1); `senior-backend` non pertinente (una costante), salto dichiarato. Sequenza: dopo il Task 3 (riscrive la rotta `/from` che il 3 introduce con `_avvia`) e dopo 7.4 nel lotto serializzato.
>
> **Ingressi degeneri.**
> - `POST /api/step/12/from` con il tetto a 11 → `da > a`: `range(12, 12)` è vuoto e `_elenco_di_scambio(12, 11)` produce un elenco quasi vuoto, ma il deposito avverrebbe lo stesso e il Worker partirebbe con `start(config, 12, 11)`. Oracolo: rifiuto 400 prima del deposito («lo step 12 non ha nulla a valle»), nessuna versione nuova; oppure si dichiara che il bottone non esiste per il 12 (la colonna lo nasconde) e la guardia sta in `_avvia` per `da > a`. Una delle due, scritta nel banco
> - `POST /api/step/3/from` → `{"avviato": 3, "fino_a": 11}` e `Worker.start(config, 3, 11)` (banco del passo 1)
> - banco esistente in `test_server.py` che asserisce `"fino_a": 12` → aggiornato a 11 con la stessa ragione, non cancellato
> - `POST /api/step/12` (singolo, non `/from`) → resta possibile: il prior si chiede esplicitamente, il tetto vale solo per «da qui in giù»

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py` (rotta `/from`, dal Task 3)
- Modify: `meshrec/src/meshrec/ui/app.js:3075` (etichetta del bottone)
- Test: `meshrec/tests/test_server.py`

- [ ] **Step 1: Banco**

```python
def test_da_qui_in_giu_si_ferma_al_deck(cliente, monkeypatch):
    """PRODUCT.md: il prior non gira per difetto, e la colonna non lo mostra.
    Farlo partire da un bottone che non lo nomina e' uno step invisibile che
    l'utente paga."""
    avviati = []
    monkeypatch.setattr(server.Worker, "start", lambda self, *argomenti: avviati.append(argomenti))
    assert cliente.post("/api/step/3/from").json() == {"avviato": 3, "fino_a": 11}
    assert avviati[0][2] == 11
```

- [ ] **Step 2: Vedilo fallire**, **Step 3: implementa**

`server.py`: `return _avvia(numero, 12, ...)` diventa `return _avvia(numero, 11, ...)`. Con il tetto a 11, `POST /api/step/12/from` ha `da > a` e la guardia `1 <= da <= a <= 12` di `_avvia` (Task 3) lo rifiuta con 400 prima del deposito: aggiungi al banco del passo 1 `assert cliente.post("/api/step/12/from").status_code == 400`. Il commento sopra («12 e non 11 dalla Fase 4...») si riscrive: «11, il deck: e' dove si chiude il perimetro del prodotto (PRODUCT.md) e dove finisce una corsa da riga di comando. Il prior (12) resta raggiungibile con `meshrec wall` e con `POST /api/step/12`, ma non parte da un bottone che non lo nomina.» In `app.js` l'etichetta `"Esegui da qui in giù"` diventa `"Esegui da qui fino al deck"`. Se un banco in `test_server.py` asserisce `"fino_a": 12`, aggiornalo a 11 con la stessa ragione.

- [ ] **Step 4: Verdi**, **Step 5: Commit** — `fix(server): «da qui in giù» si ferma al deck, come il perimetro dichiara`.

---

### Task 7.6: Le metriche degli altri step hanno un nome, e Steiner saturato è un avviso

> **Dispatch.** Agente: `frontend-engineer`. Skill-gate: `caveman:caveman`, `ponytail:ponytail`, `superpowers:test-driven-development` per `righeDellaMetrica`; `impeccable` (`critique` sulla classe d'avviso nella colonna del dettaglio: secondo canale oltre il testo, contrasto di `--guasto` su `.metriche dd`). Sequenza: ultimo del lotto, dopo 7.5, serializzato. Banco con `_DOM +`; `_etichette_metriche` valuta la tabella con `node`, quindi la tabella deve restare JavaScript valido senza riferimenti a costanti esterne.
>
> **Ingressi degeneri.**
> - `steiner_saturated: false` o assente → nessuna classe d'avviso (`dd.className === ""`)
> - `true` su una chiave che non è d'allarme (`watertight`, `enabled`) → nessuna classe d'avviso: il set `METRICHE_D_ALLARME` decide, non il tipo del valore
> - chiave senza etichetta nella tabella (una metrica che `pipeline.py` scriverà domani) → chiave grezza come oggi, non «undefined»; `ETICHETTE_METRICHE[chiave]` assente per uno step → `righeDellaMetrica` riceve `undefined` come tabella e non solleva (verificare il corpo a `app.js:3206`)
> - valore annidato per 05/06/08 (`aspect_ratio.min`) → le cinque righe copiate dallo step 7 lo etichettano; senza, resta la chiave composta come oggi
> - sorgente senza `const ETICHETTE_METRICHE = ` (rinominata) → `_etichette_metriche` fallisce con `IndexError` chiaro nel banco, non con un `SyntaxError` di `node`

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:34-102` (`ETICHETTE_METRICHE`), `:3206-3225` (`righeDellaMetrica`)
- Modify: `meshrec/src/meshrec/ui/stile.css`
- Test: `meshrec/tests/test_app_js.py`

- [ ] **Step 1: Banco**

```python
def test_le_metriche_che_contraddicono_hanno_un_etichetta_e_l_avviso(tmp_path):
    _esegui(tmp_path, _DOM + "\n".join(_costante(nome) for nome in ("VALORE_LARGO", "CLASSE_VALORE_LARGO", "METRICHE_D_ALLARME")) + "\n" + _funzioni("righeDellaMetrica", "valoreDellaMetrica") + f"""
const ETICHETTE_METRICHE = {json.dumps(_etichette_metriche())};
const righe = righeDellaMetrica("steiner_saturated", true, ETICHETTE_METRICHE["09_tetrahedralize"]);
assert.equal(righe[0].textContent, "punti di Steiner esauriti: mesh troncata");
assert.equal(righe[1].className, "metrica-avviso");
const quiete = righeDellaMetrica("steiner_saturated", false, ETICHETTE_METRICHE["09_tetrahedralize"]);
assert.equal(quiete[1].className, "");
for (const [chiave, nome] of [["01_load", "size_check"], ["06_repair", "watertight_after"], ["06_repair", "holes_over_threshold"], ["11_export", "fixed_nset_coverage"], ["02_segment", "points_after"], ["03_downsample", "voxel_size"]]) {{
  assert.ok(ETICHETTE_METRICHE[chiave]?.[nome], `${{chiave}}.${{nome}} senza etichetta`);
}}
""")
```

Aggiungi in cima al file di test, vicino a `_funzioni`:

```python
def _etichette_metriche() -> dict:
    """La tabella ETICHETTE_METRICHE letta dal sorgente, valutata con node."""
    testo = _modulo()
    corpo = "const ETICHETTE_METRICHE = " + testo.split("const ETICHETTE_METRICHE = ", 1)[1].split("\n};\n", 1)[0] + "\n};\n"
    esito = subprocess.run([_node(), "-e", corpo + "console.log(JSON.stringify(ETICHETTE_METRICHE))"], capture_output=True, text=True)
    assert esito.returncode == 0, esito.stderr
    return json.loads(esito.stdout)
```

- [ ] **Step 2: Vedilo fallire**, **Step 3: implementa**

In `ETICHETTE_METRICHE` aggiungi le voci (mantieni le due esistenti):

```js
  "01_load": {
    "points_read": "punti letti", "points_kept": "punti tenuti", "points_dropped": "punti scartati (non finiti)",
    "spacing": "spaziatura media [mm]", "extent": "ingombro [mm]", "bbox_min": "angolo minimo [mm]",
    "bbox_max": "angolo massimo [mm]", "scale": "fattore di scala", "size_check": "controllo dell'ingombro atteso",
  },
  "02_segment": {
    "points_before": "punti in ingresso", "points_after": "punti tenuti", "outliers_removed": "punti tolti come rumore",
    "cropped": "ritagliato", "cropped_points": "punti ritagliati", "cropped_fraction": "frazione ritagliata",
    "cropped_by_face": "punti ritagliati per faccia", "method": "metodo",
  },
  "03_downsample": {
    "points_before": "punti in ingresso", "points_after": "punti tenuti", "voxel_size": "lato del voxel [mm]", "reduction": "riduzione",
  },
  "04_normals": { "knn": "vicini per la normale", "orient_knn": "vicini per l'orientamento", "degenerate_normals": "normali degeneri", "spacing": "spaziatura usata [mm]" },
  "05_reconstruct": { "vertices": "vertici", "triangles": "triangoli", "watertight": "superficie chiusa", "boundary_edges": "spigoli di bordo", "area": "area della superficie [mm²]", "volume": "volume racchiuso [mm³]", "method": "metodo", "density_threshold": "soglia di densità", "vertices_trimmed": "vertici potati" },
  "06_repair": { "vertices": "vertici", "triangles": "triangoli", "watertight": "superficie chiusa", "watertight_after": "chiusa dopo la riparazione", "boundary_edges": "spigoli di bordo", "area": "area della superficie [mm²]", "volume": "volume racchiuso [mm³]", "volume_before": "volume prima [mm³]", "volume_after": "volume dopo [mm³]", "components_before": "componenti prima", "components_kept": "componenti tenute", "holes_before": "fori prima", "holes_over_threshold": "fori oltre la soglia, lasciati aperti", "open_boundary_paths": "bordi aperti", "open_paths_over_threshold": "bordi aperti oltre la soglia", "degenerate_faces_removed": "facce degeneri tolte", "duplicate_faces_removed": "facce duplicate tolte", "duplicate_vertices_merged": "vertici duplicati fusi", "orphan_vertices_removed": "vertici orfani tolti", "orientation_flipped": "orientamento rigirato" },
  "08_simplify": { "enabled": "abilitata", "mode": "modo", "triangles_before": "triangoli prima", "triangles_after": "triangoli dopo", "vertices": "vertici", "triangles": "triangoli", "watertight": "superficie chiusa", "boundary_edges": "spigoli di bordo", "area": "area della superficie [mm²]", "volume": "volume racchiuso [mm³]" },
  "09_tetrahedralize": { "nodes": "nodi", "tets": "tetraedri", "element": "elemento", "steiner_points": "punti di Steiner inseriti", "max_steiner_points": "punti di Steiner concessi", "steiner_saturated": "punti di Steiner esauriti: mesh troncata", "radius_edge_ratio_p99": "raggio-spigolo, 99º percentile", "radius_edge_ratio_over_limit": "tetraedri oltre il limite raggio-spigolo", "largest_element_volume": "volume dell'elemento più grande [mm³]", "min_ratio": "rapporto minimo chiesto", "max_volume": "volume massimo chiesto [mm³]", "nobisect": "senza bisezione", "seconds": "durata [s]" },
  "11_export": { "element_type": "tipo di elemento", "inp": "deck scritto", "vtu": "vtu scritto", "mass": "massa [t]", "volume": "volume [mm³]", "surface_area": "area della superficie [mm²]", "extent": "ingombro [mm]", "fixed_nset_coverage": "copertura del set di vincolo", "boundary_spacing": "spaziatura al contorno [mm]", "set_tolerance": "tolleranza dei set [mm]", "pressure": "pressione [MPa]", "casi_di_carico": "casi di carico" },
```

Le chiavi annidate (`aspect_ratio · min` ecc.) per 05/06/08 si aggiungono copiando le cinque righe già scritte per lo step 7.

`righeDellaMetrica`: dopo `const dd = elemento("dd", { textContent: testo });`:

```js
  // Il controllo che contraddice: un booleano vero su una chiave d'allarme e'
  // la «mesh troncata in silenzio» del primo principio di prodotto, e non
  // sta fra tredici righe uguali.
  if (METRICHE_D_ALLARME.has(nome) && valore === true) dd.className = "metrica-avviso";
```

e sopra la funzione: `const METRICHE_D_ALLARME = new Set(["steiner_saturated"]);`. `stile.css`, accanto a `.metriche dd`: `.metriche dd.metrica-avviso { color: var(--guasto); font-weight: 600; }` (secondo canale: il testo dell'etichetta dice già «mesh troncata»).

- [ ] **Step 4: Verdi**, **Step 5: Commit** — `feat(interfaccia): le metriche di ogni step hanno un nome, e Steiner saturato e' un avviso`.

---

### Task 8: Suite intera, review e PR

> **Dispatch.** Passo 1 (suite intera): thread principale o `backend-engineer`, uno solo. Passo 2: **in parallelo, un solo messaggio**, quattro agenti in sola lettura — `security-reviewer` (skill-gate: `security-review` built-in, poi `security-pen-testing` con `vulnerability_scanner.py` sui file toccati; `ai-security`, `senior-secops` compliance e `dependency-auditor` non pertinenti: nessun manifest cambiato, nessun LLM), `code-reviewer` (skill-gate: `code-reviewer` pass meccanico, poi `adversarial-reviewer`; `ponytail:ponytail-review` sul diff di `app.js`, che cresce di ~300 righe), `test-writer` (skill-gate: `tdd-guide`; risponde **riga per riga** agli Ingressi degeneri dei Task 1-7.6 con `coperta`/`scoperta`/`non pertinente`, tanti verdetti quante righe), `craft-reviewer` (skill-gate: `impeccable` sulla superficie UI — pannello Modello, `<details>` del registro, bottoni nuovi; lettura diretta su commenti, README e messaggi di commit). Le correzioni che emergono: un agente alla volta sullo stesso worktree, un commit per correzione, poi passo 3.
>
> **Ingressi degeneri.**
> - nessun ingresso esterno: il task non scrive codice. Le righe da chiudere sono quelle dei task sopra; a `security-reviewer` va detto in particolare che `_elenco_di_scambio` è una lista chiusa di nomi costruita dal server (nessun nome arriva dal browser), che `scambia` fa `Path(out_dir) / nome` senza `is_relative_to` (basta finché l'elenco è chiuso; un `scambio.json` scritto a mano con `../` uscirebbe dalla corsa — da dichiarare come limite o da chiudere), e che `numero` delle rotte di esecuzione non ha una guardia di intervallo (Task 3, terza riga).

- [ ] **Step 1: Suite intera dal worktree**

Run: `PYTEST tests` (senza `-k`).
Expected: tutto verde salvo i 6 skip noti (`wildmeshing`, `OpenSees`). Se `test_riferimenti_documenti.py` va rosso per «nome ambiguo», sono i worktree fermi sotto `.claude/worktrees/`: non è codice.

- [ ] **Step 2: Round di review in parallelo** — `security-reviewer` (lo scambio sposta file dentro `out_dir`: `_elenco_di_scambio` è una lista chiusa di nomi, nessuno dal browser), `code-reviewer`, `test-writer`, `craft-reviewer`. Correggi ciò che emerge, un commit per correzione.

- [ ] **Step 3: Push e PR**

```bash
git -C /home/mario/worktrees/storico-esecuzioni push -u origin feat/storico-esecuzioni
```

PR verso `main` con titolo «Lo storico annulla anche le esecuzioni, e il modello si legge sotto la pipeline», corpo che rimanda alla spec, e in coda:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01PoZG2uLV9Xpc5FJRcksTn1
```

- [ ] **Step 4:** Dopo il merge, `superpowers:finishing-a-development-branch`.
