# MeshRec Fase 3.5 — Continuità del viewport e ritorno indietro: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Il viewport smette di ripartire da zero a ogni step, dichiara che cosa un passaggio ha tolto e da quale step viene la geometria che mostra, e le modifiche di configurazione si annullano con Ctrl+Z.

**Architecture:** Tre pezzi indipendenti. La camera e il pan stanno in `ui/viewport.js` e si provano come funzioni pure eseguite in `node`. La risoluzione «quale artefatto per quale step» sta in `app/server.py`, dove `cfg.simplify.enabled` già vive, e viaggia verso il browser in una intestazione nuova `X-Da-Step`. Lo storico è un modulo nuovo `app/storico.py` che deposita versioni su disco, innestato nel server e non in `core.config.save_config`. Nessun file del `core/` cambia.

**Tech Stack:** Python 3.12 + FastAPI + pydantic (server), JavaScript a moduli ES + three.js vendorizzato (browser), pytest + `subprocess` su `node` (test del JavaScript), Open3D (lettura artefatti). Nessuna dipendenza nuova, nessuno strumento di build.

**Spec:** `docs/superpowers/specs/2026-08-16-meshrec-fase-3-5-viewport-design.md`

---

## Global Constraints

- **Lingua.** Interfaccia, messaggi d'errore, nomi di funzione e commenti in italiano. Nessun accento nei sorgenti `.js` e `.py` (il codice esistente scrive `perche'`, `piu'`, `gia'`): i documenti `.md` invece gli accenti li portano.
- **Commit.** Conventional Commits in italiano, via la skill `caveman:caveman-commit`. Trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Sola lettura, mai toccare.** `meshrec/runs/muro/`, `meshrec/runs/lab_crop/`, `meshrec/experiments/muro/`, `meshrec/experiments/lab_crop/` sono corse di riferimento. `meshrec/runs/` non è nel repository (gitignored) e **non esiste dentro il worktree**: nessun test può leggerlo. I test costruiscono corse sintetiche in `tmp_path`, come già fa `tests/test_server.py`.
- **Il contratto della tratta.** Nessun endpoint solleva verso il browser: il gestore generico di `app/server.py` risponde 400 con `{"errore", "messaggio"}`. Vale anche per i due endpoint nuovi.
- **`core/` non si tocca.** In particolare `core/config.py:284` (`save_config`), che è chiamata anche da `pipeline` e `sweep`.
- **Nessun colore scritto a mano nel CSS.** `tests/test_stile.py` lo sorveglia: ogni colore passa da un token `var(--...)` già dichiarato.
- **Comandi.** Test: `cd meshrec && uv run pytest`. Un solo file: `uv run pytest tests/test_viewport_js.py -v`. Server: `uv run meshrec serve`. Su macOS non esiste `timeout`: usare il parametro del proprio strumento.
- **Base.** Il ramo parte da `59ab9c9` (punta di `fase-3-interfaccia`). Al commit `ade3658` la suite è **402 selezionati su 408 raccolti, 6 deselezionati**. Rileggere il numero all'inizio del lavoro: la critica del giro 3 ne aggiunge, e il piano non deve citare un conteggio invecchiato.

## Scostamenti dalla spec, dichiarati

Tre punti in cui il piano non segue la spec alla lettera. Sono decisioni prese leggendo il codice vero, non semplificazioni silenziose.

1. **La tabella step → artefatto sta nel server, non in `ui/app.js`.** La spec la assegna ad `app.js` (§ 3), ma la riga dello step 8 della sua stessa tabella (§ 5) sceglie fra due *nomi di file* in base a `cfg.simplify.enabled`. Oggi il browser non conosce nessun nome di artefatto e non ha la configurazione caricata all'avvio (`ui/app.js:391`, `configurazione` resta `null` finché non si apre un pannello). Metterla lì significherebbe insegnare al browser i nomi dei file e aggiungere una richiesta all'avvio. Nel server la decisione è a costo zero. Il browser riceve il risultato nell'intestazione `X-Da-Step` e lo dichiara: il contenuto della § 5 è rispettato per intero.

2. **Il fantasma nasce solo dove serve, e l'interruttore con lui.** La spec (§ 6) accende il fantasma di default sugli step 2, 3 e 8 e lascia «un interruttore» altrove. Il piano ferma il fantasma a quei tre step e mostra l'interruttore solo lì. Sugli step 7, 10 e 11 la geometria corrente *è già* quella dello step precedente (dopo il Task 3), quindi il fantasma disegnerebbe la stessa cosa due volte; sul 5 contro il 6 è lo z-fighting che la spec stessa cita. L'interruttore su uno step dove il fantasma non esiste sarebbe un comando che non fa nulla. Se all'uso i tre step si rivelano pochi, la tabella `FANTASMA_DI` è una riga.

3. **Il messaggio dell'undo esce dalla regione `role="alert"`.** L'interfaccia ne ha una sola (`#errore`), e non ha una regione neutra. Il precedente citato dalla spec — il bottone Annulla — fu chiuso spegnendo il bottone, non con un messaggio, quindi non c'è un posto già pronto. Riusare `#errore` è la strada corta e l'annuncio è garantito. Resta come debito nel Task 8.

---

## File Structure

| File | Responsabilità | Task |
|---|---|---|
| `meshrec/src/meshrec/ui/viewport.js` | Scena. Guardia della camera, pan, gruppo del fantasma | 1, 2, 5 |
| `meshrec/src/meshrec/ui/app.js` | Orchestrazione. Didascalia, fantasma, Ctrl+Z | 4, 5, 8 |
| `meshrec/src/meshrec/ui/index.html` | Markup dei comandi nuovi | 2, 5 |
| `meshrec/src/meshrec/ui/stile.css` | Una regola per il blocco dei comandi | 2 |
| `meshrec/src/meshrec/app/server.py` | Risoluzione step → artefatto, `scrivi_config`, due endpoint | 3, 7 |
| `meshrec/src/meshrec/app/storico.py` | **Nuovo.** Deposito, cursore, tetto. Nessun HTTP | 6 |
| `meshrec/tests/test_viewport_js.py` | **Nuovo.** Le decisioni pure di `viewport.js`, eseguite | 1, 2 |
| `meshrec/tests/test_storico.py` | **Nuovo.** Il deposito, senza server | 6 |
| `meshrec/tests/test_app_js.py` | Le funzioni di `app.js` sul DOM finto | 2, 4, 5, 8 |
| `meshrec/tests/test_server.py` | Gli endpoint | 3, 5, 7 |

---

### Task 1: La camera non si azzera

**Files:**
- Modify: `meshrec/src/meshrec/ui/viewport.js` (aggiungere in cima al modulo; sostituire `inquadra()` a `:187` e `:199`)
- Create: `meshrec/tests/test_viewport_js.py`

**Interfaces:**
- Consumes: niente da task precedenti.
- Produces: `export function fuoriDallaVista(centro, vecchioCentro, raggio) -> boolean` — `centro` e `vecchioCentro` sono terne `[x, y, z]` in millimetri, `raggio` uno scalare. Funzione interna `inquadraSeServe()`. Il Task 2 estende lo stesso file di test.

- [ ] **Step 1: Scrivere il file di test con il banco e i due controlli che si smentiscono**

Creare `meshrec/tests/test_viewport_js.py`:

```python
"""Il modulo della vista dalla parte del browser: le decisioni pure, eseguite.

`ui/viewport.js` non e' importabile da qui, e le sue funzioni interne stanno
dentro la chiusura di creaViewport, che `node` non puo' aprire senza un
three.js finto. Percio' le decisioni che questa fase aggiunge sono funzioni
pure di primo livello: si estraggono dal sorgente e si eseguono davvero,
esattamente come tests/test_app_js.py fa con le funzioni di app.js.

Un controllo che cerca una sottostringa nel sorgente passa anche quando la
logica e' capovolta, e su questo ramo e' gia' successo (vedi il docstring di
tests/test_app_js.py). Qui la logica si esegue; le sole asserzioni sul testo
sono quelle che sorvegliano *chi chiama chi*, che eseguendo non si vedrebbe.

ponytail: il banco (_node, _esegui, _sorgente_di) e' ricopiato da
tests/test_app_js.py invece di essere condiviso in un conftest. Condividerlo
vorrebbe dire toccare le trenta chiamate di quel file, che e' lungo 2049 righe
e non ne guadagna niente. Se nasce un terzo file di questa famiglia, allora
conftest.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from meshrec.app.server import UI_DIR


def _node() -> str:
    percorso = shutil.which("node")
    if percorso is None:
        pytest.skip("node non installato: la logica resta verificata a mano")
    return percorso


def _esegui(tmp_path: Path, sorgente: str) -> str:
    """Il banco: scrive il modulo di prova e lo esegue. Rosso e' l'assert di
    `node` che salta, e il suo messaggio arriva qui dentro."""
    prova = tmp_path / "prova.mjs"
    prova.write_text(sorgente, encoding="utf-8")
    esito = subprocess.run([_node(), str(prova)], capture_output=True, text=True)
    assert esito.returncode == 0, esito.stderr
    return esito.stdout


def _modulo() -> str:
    return (UI_DIR / "viewport.js").read_text(encoding="utf-8")


def _senza_commenti(modulo: str) -> str:
    return "\n".join(r for r in modulo.splitlines() if not r.lstrip().startswith("//"))


def _sorgente_di(nome: str, testo: str) -> str:
    """Il corpo di una funzione di primo livello, dalla firma alla graffa che
    la chiude in prima colonna. `export` cade: serve a chi importa il modulo,
    non a chi ne esegue una funzione da sola."""
    assert f"function {nome}(" in testo, f"il modulo non ha una funzione {nome}"
    corpo = testo.split(f"function {nome}(", 1)[1]
    return f"function {nome}(" + corpo.split("\n}\n", 1)[0] + "\n}"


def _funzioni(*nomi: str) -> str:
    testo = _modulo()
    return "\n".join(_sorgente_di(nome, testo) for nome in nomi)


_INTESTAZIONE = "import assert from 'node:assert/strict';\n"


def test_un_ingombro_dentro_la_vista_non_fa_reinquadrare(tmp_path):
    """Criterio 1 della spec: passando dallo step 3 al 4 la camera resta dove
    l'utente l'aveva messa. Il centro nuovo cade dentro la sfera che la camera
    sta gia' guardando, quindi la geometria e' visibile e spostare la camera
    non aggiungerebbe niente se non la sensazione di ricominciare da capo."""
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("fuoriDallaVista") + """
assert.equal(fuoriDallaVista([10, 0, 0], [0, 0, 0], 100), false);
assert.equal(fuoriDallaVista([0, 0, 0], [0, 0, 0], 100), false);
// Il confine: a distanza pari al raggio il centro sta SULLA sfera, non fuori,
// e la geometria e' ancora inquadrata.
assert.equal(fuoriDallaVista([100, 0, 0], [0, 0, 0], 100), false);
""")


def test_un_ingombro_fuori_dalla_vista_fa_reinquadrare(tmp_path):
    """Criterio 2. Senza questo, il test qui sopra si soddisfa anche non
    reinquadrando mai: e' il difetto opposto e altrettanto reale, perche'
    cambiando corsa la camera resterebbe puntata sul vuoto senza che nulla lo
    spieghi."""
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("fuoriDallaVista") + """
assert.equal(fuoriDallaVista([1000, 0, 0], [0, 0, 0], 100), true);
// Le tre componenti contano tutte: una distanza calcolata sul solo asse x
// direbbe «dentro» a una corsa spostata in profondita'.
assert.equal(fuoriDallaVista([0, 0, 1000], [0, 0, 0], 100), true);
assert.equal(fuoriDallaVista([60, 60, 60], [0, 0, 0], 100), true);
""")


def test_i_due_disegni_non_azzerano_piu_la_camera():
    """La funzione pura decide bene solo se qualcuno la interroga. Le due
    strade che disegnano devono passare dalla guardia: una chiamata diretta a
    inquadra() rimetterebbe l'azzeramento senza toccare fuoriDallaVista, e i
    due controlli qui sopra resterebbero verdi.

    Si conta invece di cercare: dopo la modifica `inquadra();` compare due
    volte, ed entrambe dentro inquadraSeServe. Una terza e' una delle due
    strade che e' tornata ad azzerare.
    """
    testo = _senza_commenti(_modulo())
    assert testo.count("inquadraSeServe();") == 2, (
        "le due strade che disegnano devono passare dalla guardia"
    )
    assert testo.count("inquadra();") == 2, (
        "inquadra() e' chiamata da qualcuno oltre a inquadraSeServe: "
        "la camera torna ad azzerarsi a ogni step"
    )
```

Il Task 2 alza questa soglia a 3: il tasto `f` e' un chiamante esplicito e voluto. Non alzarla adesso.

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_viewport_js.py -v`
Expected: FAIL. I primi due con `AssertionError: il modulo non ha una funzione fuoriDallaVista`; il terzo con `assert 0 == 2`.

- [ ] **Step 3: Scrivere la funzione pura e la guardia**

In `meshrec/src/meshrec/ui/viewport.js`, subito dopo `import * as THREE from "/ui/vendor/three.module.js";` e **fuori** da `creaViewport`:

```js
// Il centro del nuovo ingombro cade fuori dalla sfera che la camera sta
// guardando? Dentro, la geometria nuova e' gia' visibile e non c'e' ragione di
// spostare la camera; fuori, non lo e', e lasciarla ferma mostrerebbe uno
// schermo vuoto senza che nulla lo spieghi.
// Pura e di primo livello apposta: e' la sola decisione di questa camera, e
// cosi' si prova da fuori senza costruire un three.js finto.
// centro e vecchioCentro sono terne in millimetri, raggio uno scalare.
export function fuoriDallaVista(centro, vecchioCentro, raggio) {
  return Math.hypot(
    centro[0] - vecchioCentro[0],
    centro[1] - vecchioCentro[1],
    centro[2] - vecchioCentro[2],
  ) > raggio;
}
```

Dentro `creaViewport`, accanto alla dichiarazione di `orbita` (`viewport.js:54`):

```js
  // Il primo disegno dopo l'avvio inquadra; dal secondo in poi la camera resta
  // dove l'utente l'ha messa. Era il «di passaggio in passaggio si riparte da
  // zero»: la stessa nuvola inquadrata da un altro punto sembra un'altra
  // nuvola, e mostraNuvola/mostraMesh riscrivevano centro e raggio a ogni step.
  let inquadrataAlmenoUnaVolta = false;
```

Sostituire `inquadra()` (`viewport.js:145-151`) con la coppia:

```js
  function inquadra() {
    const scatola = scatolaDelGruppo();
    if (scatola.isEmpty()) return;
    scatola.getCenter(orbita.centro);
    orbita.raggio = scatola.getSize(new THREE.Vector3()).length() * 1.2;
    inquadrataAlmenoUnaVolta = true;
    aggiornaCamera();
  }

  function inquadraSeServe() {
    if (!inquadrataAlmenoUnaVolta) {
      inquadra();
      return;
    }
    const scatola = scatolaDelGruppo();
    if (scatola.isEmpty()) return;
    const centro = scatola.getCenter(new THREE.Vector3());
    if (fuoriDallaVista(centro.toArray(), orbita.centro.toArray(), orbita.raggio)) {
      inquadra();
    }
  }
```

In `mostraNuvola` (`viewport.js:187`) e `mostraMesh` (`viewport.js:199`) sostituire `inquadra();` con `inquadraSeServe();`.

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_viewport_js.py -v`
Expected: PASS, 3 test.

- [ ] **Step 5: Eseguire la suite intera**

Run: `cd meshrec && uv run pytest -q`
Expected: nessun fallimento nuovo rispetto alla base misurata all'inizio.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/ui/viewport.js meshrec/tests/test_viewport_js.py
git commit -m "feat(viewport): la camera non riparte da zero a ogni step"
```

---

### Task 2: Pan della camera e comando «Inquadra»

**Files:**
- Modify: `meshrec/src/meshrec/ui/viewport.js` (`pointermove` a `:90-96`, `keydown` a `:105-119`, costante `COMANDI` a `:31`)
- Modify: `meshrec/src/meshrec/ui/index.html` (blocco nuovo dentro `.zona-vista`)
- Modify: `meshrec/src/meshrec/ui/stile.css` (una regola)
- Modify: `meshrec/src/meshrec/ui/app.js` (legare il bottone)
- Modify: `meshrec/tests/test_viewport_js.py`
- Modify: `meshrec/tests/test_app_js.py`

**Interfaces:**
- Consumes: `inquadra()` interna e `inquadraSeServe()` del Task 1; `fuoriDallaVista` resta invariata.
- Produces: `export function scalaDelloSpostamento(raggio, altezzaTela, fovGradi) -> number` (millimetri per pixel). Elemento `#inquadra` nel markup e classe CSS `.comandi-vista`, che il Task 5 riusa per l'interruttore del fantasma.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `meshrec/tests/test_viewport_js.py`:

```python
def test_lo_spostamento_segue_il_cursore(tmp_path):
    """Un trascinamento lungo quanto la tela sposta la vista di tutta l'altezza
    visibile a quella distanza: e' cio' che rende il gesto «il punto sotto il
    dito resta sotto il dito» invece di una velocita' scelta a caso.

    Con fov 50 gradi (viewport.js:8) e raggio 1000, l'altezza visibile e'
    2 * 1000 * tan(25 gradi).
    """
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("scalaDelloSpostamento") + """
const altezzaTela = 600;
const scala = scalaDelloSpostamento(1000, altezzaTela, 50);
const attesa = 2 * 1000 * Math.tan((25 * Math.PI) / 180);
assert.ok(
  Math.abs(scala * altezzaTela - attesa) < 1e-9,
  `un trascinamento di tutta la tela sposta ${scala * altezzaTela}, atteso ${attesa}`,
);
// Piu' lontano si guarda, piu' un pixel vale: senza, sul telaio largo 2.759 mm
// il gesto sarebbe microscopico da lontano e violento da vicino.
assert.ok(scalaDelloSpostamento(2000, altezzaTela, 50) > scala);
// Una tela piu' alta mostra la stessa scena su piu' pixel, quindi ogni pixel
// vale meno.
assert.ok(scalaDelloSpostamento(1000, 1200, 50) < scala);
""")


def _comandi() -> str:
    trovato = re.search(r'const COMANDI = "([^"]*)"', _modulo())
    assert trovato is not None, "la costante COMANDI non e' piu' nel modulo"
    return trovato.group(1)


def test_l_etichetta_della_tela_dichiara_i_comandi_nuovi():
    """L'aria-label e' il contenuto testuale equivalente della tela: se
    dichiara meno di quanto la tela fa, chi non vede la scena non sa che il
    comando esiste (viewport.js:25-31)."""
    comandi = _comandi()
    for parola in ("ruotare", "spostare", "zoom", "inquadrare"):
        assert parola in comandi, f"l'etichetta della tela non nomina «{parola}»"


def test_la_traslazione_e_legata_a_maiusc_sia_col_mouse_sia_da_tastiera():
    """Le due strade sono due, e provarne una sola lascia l'altra scoperta: chi
    non usa il mouse resterebbe senza pan, che e' il difetto che questa fase
    chiude."""
    testo = _senza_commenti(_modulo())
    assert "evento.shiftKey" in testo, "nessun comando e' legato a maiusc"
    assert testo.count("trasla(") >= 5, (
        "le cinque strade attese sono il trascinamento e le quattro frecce"
    )
```

Aggiungere in coda a `meshrec/tests/test_app_js.py`:

```python
def test_il_bottone_inquadra_esiste_nel_markup_ed_e_legato():
    """L'uscita di sicurezza del pan: qualunque smarrimento si chiude con un
    clic. Nel markup e non creato da codice, come ogni comando di questa
    interfaccia, e legato davvero — un bottone senza gestore e' un comando che
    non fa nulla e non lo dice."""
    elemento = _elemento(_senza_commenti_html(_markup()), "inquadra")
    assert "<button" in elemento, f"#inquadra non e' un bottone: {elemento}"
    modulo = _senza_commenti_js(_modulo())
    assert 'getElementById("inquadra")' in modulo, "il bottone non e' preso dal markup"
    assert "vista.inquadra()" in modulo, "il bottone non chiama il comando della vista"
```

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_viewport_js.py tests/test_app_js.py::test_il_bottone_inquadra_esiste_nel_markup_ed_e_legato -v`
Expected: FAIL. `il modulo non ha una funzione scalaDelloSpostamento`; `l'etichetta della tela non nomina «spostare»`; `nessun comando e' legato a maiusc`; `nessun elemento con id=inquadra nel markup`.

- [ ] **Step 3: Scrivere la funzione pura**

In `meshrec/src/meshrec/ui/viewport.js`, accanto a `fuoriDallaVista` e fuori da `creaViewport`:

```js
// Quanto vale un pixel di trascinamento, in unita' di scena, alla distanza a
// cui la camera sta guardando. 2*raggio*tan(fov/2) e' l'altezza visibile a
// quella distanza; divisa per l'altezza della tela da' i millimetri per pixel,
// ed e' cio' che fa restare sotto il cursore il punto che ci stava.
// fovGradi arriva da camera.fov, non e' riscritto qui: due copie dello stesso
// angolo si slacciano in silenzio il giorno che una cambia.
export function scalaDelloSpostamento(raggio, altezzaTela, fovGradi) {
  return (2 * raggio * Math.tan((fovGradi * Math.PI) / 360)) / altezzaTela;
}
```

- [ ] **Step 4: Traslare il centro nel piano della camera**

Dentro `creaViewport`, dopo `aggiornaCamera()` (`viewport.js:72-80`):

```js
  // Quaranta pixel per pressione: l'ordine di grandezza di un trascinamento
  // corto, cosi' il comando da tastiera e quello col mouse spostano la vista
  // dello stesso passo percepito.
  const PASSO_TASTIERA = 40;

  // I tre assi della camera, riusati invece di riallocarli a ogni movimento del
  // puntatore: pointermove scatta a ogni fotogramma mentre si trascina.
  const destra = new THREE.Vector3();
  const alto = new THREE.Vector3();
  const avanti = new THREE.Vector3();

  // Sposta il centro dell'orbita nel piano della camera. Gli assi vengono dalla
  // matrice della camera e non da un sistema fisso: ruotata l'orbita, «destra»
  // non e' piu' l'asse x della scena, e traslare lungo quello farebbe scorrere
  // la vista di traverso rispetto al gesto.
  // updateMatrixWorld prima di leggerla: lookAt scrive il quaternione, ma la
  // matrice del mondo three.js la ricalcola al disegno, quindi senza questa
  // riga si leggerebbero gli assi del fotogramma precedente.
  function trasla(dx, dy) {
    const scala = scalaDelloSpostamento(orbita.raggio, tela.clientHeight || 1, camera.fov);
    camera.updateMatrixWorld();
    camera.matrixWorld.extractBasis(destra, alto, avanti);
    orbita.centro.addScaledVector(destra, -dx * scala);
    orbita.centro.addScaledVector(alto, dy * scala);
  }
```

Sostituire il gestore `pointermove` (`viewport.js:90-96`):

```js
  tela.addEventListener("pointermove", (evento) => {
    if (!premuto) return;
    const dx = evento.clientX - ultimo.x;
    const dy = evento.clientY - ultimo.y;
    ultimo = { x: evento.clientX, y: evento.clientY };
    // Maiusc trasla, altrimenti ruota: sul telaio largo 2.759 mm senza pan non
    // si raggiunge uno spigolo, perche' orbita.centro cambiava solo dentro
    // inquadra().
    if (evento.shiftKey) trasla(dx, dy);
    else {
      orbita.theta -= dx * 0.005;
      orbita.phi = Math.min(Math.PI - 0.01, Math.max(0.01, orbita.phi - dy * 0.005));
    }
    aggiornaCamera();
  });
```

Sostituire il gestore `keydown` (`viewport.js:105-119`):

```js
  // Orbita, zoom, traslazione e inquadratura da tastiera, per chi non usa il
  // mouse. Stessi gesti, solo discretizzati. Maiusc piu' frecce trasla, le
  // frecce da sole ruotano: la stessa distinzione del trascinamento.
  tela.addEventListener("keydown", (evento) => {
    const traslazioni = {
      ArrowLeft: () => trasla(-PASSO_TASTIERA, 0),
      ArrowRight: () => trasla(PASSO_TASTIERA, 0),
      ArrowUp: () => trasla(0, -PASSO_TASTIERA),
      ArrowDown: () => trasla(0, PASSO_TASTIERA),
    };
    const rotazioni = {
      ArrowLeft: () => { orbita.theta -= 0.1; },
      ArrowRight: () => { orbita.theta += 0.1; },
      ArrowUp: () => { orbita.phi = Math.max(0.01, orbita.phi - 0.1); },
      ArrowDown: () => { orbita.phi = Math.min(Math.PI - 0.01, orbita.phi + 0.1); },
      "+": () => { orbita.raggio *= 0.9; },
      "-": () => { orbita.raggio *= 1.1; },
      // L'uscita di sicurezza dalla tastiera, gemella del bottone «Inquadra».
      f: () => { inquadra(); },
    };
    const passo = evento.shiftKey ? traslazioni[evento.key] : rotazioni[evento.key];
    if (!passo) return;
    evento.preventDefault();
    passo();
    aggiornaCamera();
  });
```

Estendere la costante `COMANDI` (`viewport.js:31`):

```js
  const COMANDI = "frecce per ruotare, maiusc piu' frecce o maiusc piu' trascinamento per spostare, piu' e meno per lo zoom, f per inquadrare";
```

**Il tasto `f` aggiunge un terzo chiamante legittimo di `inquadra()`**, e `test_i_due_disegni_non_azzerano_piu_la_camera` del Task 1 ne conta due. Alzare la soglia lì, con la ragione:

```python
    assert testo.count("inquadra();") == 3, (
        "inquadra() e' chiamata da qualcuno oltre a inquadraSeServe e al tasto f: "
        "la camera torna ad azzerarsi a ogni step"
    )
```

Alzarla è lecito solo perché il chiamante nuovo è un comando esplicito dell'utente, che è esattamente ciò che la § 4 della spec ammette. Un quarto `inquadra();` va guardato prima di alzarla ancora: la soglia serve a costringere a quello sguardo, non a essere aggiornata per far tornare il verde.

- [ ] **Step 5: Aggiungere il bottone al markup, allo stile e al modulo**

In `meshrec/src/meshrec/ui/index.html`, dentro `<section class="zona zona-vista">`, subito dopo `<p class="conteggi" ...>`:

```html
    <!-- I comandi della vista. Nascono visibili, a differenza del taglio: non
         dipendono da che cosa e' disegnato, e «Inquadra» e' l'uscita di
         sicurezza di chi si e' perso spostando la vista. -->
    <div class="comandi-vista" id="comandi-vista">
      <button type="button" id="inquadra" class="bottone">Inquadra</button>
    </div>
```

In `meshrec/src/meshrec/ui/stile.css`, accanto alla regola `.taglio` (`:160`):

```css
.comandi-vista { position: absolute; top: var(--passo-2); right: var(--passo-2); display: flex; align-items: center; gap: var(--passo-2); padding: var(--passo-2); background: var(--velo); border: 1px solid var(--bordo-comando); border-radius: var(--raggio); font-size: var(--tipo-dato); line-height: var(--interlinea-riga); }
.comandi-vista :focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
```

In `meshrec/src/meshrec/ui/app.js`, accanto agli altri gestori dei comandi della vista (dopo `asseTaglio.addEventListener(...)`, `app.js:353`):

```js
// L'uscita di sicurezza del pan. La camera non si reinquadra piu' da sola a
// ogni step (viewport.js, inquadraSeServe), quindi il ritorno all'ingombro
// deve essere un comando che si vede.
document.getElementById("inquadra").addEventListener("click", () => vista.inquadra());
```

- [ ] **Step 6: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_viewport_js.py tests/test_stile.py tests/test_app_js.py -q`
Expected: PASS. `test_stile.py` verifica che la regola nuova non abbia colori fuori dai token.

- [ ] **Step 7: Commit**

```bash
git add meshrec/src/meshrec/ui/viewport.js meshrec/src/meshrec/ui/index.html \
        meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js \
        meshrec/tests/test_viewport_js.py meshrec/tests/test_app_js.py
git commit -m "feat(viewport): spostare la vista, e un comando per ritrovarla"
```

---

### Task 3: Ogni step ha una geometria da mostrare

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py` (tabella nuova a livello di modulo, prima di `create_app` a `:261`; endpoint `/api/mesh/{numero}` a `:625`)
- Modify: `meshrec/tests/test_server.py`

**Interfaces:**
- Consumes: `pipeline.ARTIFACTS` (`core/pipeline.py:31-40`), `PipelineConfig.simplify.enabled` (`core/config.py:129`).
- Produces: `sorgente_geometria(numero: int, cfg: PipelineConfig) -> int`, di modulo e importabile. Intestazione HTTP `X-Da-Step` sulla risposta di `GET /api/mesh/{numero}`, che il Task 4 legge.

**Da non rompere.** Tre test esistenti dipendono dai messaggi di questo endpoint: `test_chiedere_la_mesh_di_uno_step_fuori_intervallo_spiega_quali_esistono` (`tests/test_server.py:210`) vuole `"99"` e `"8"` dentro il messaggio; `test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva` (`:204`) vuole 400; il test a `:1136` chiede `/api/mesh/1` e vuole `"0 triangoli"` nel messaggio. Il codice qui sotto li tiene tutti e tre verdi: `/api/cloud` **non si tocca**, e `/api/mesh` accetta 1..11 risolvendo 1..4 su sé stessi.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `meshrec/tests/test_server.py`:

```python
@pytest.mark.parametrize("numero", range(1, 12))
def test_ogni_step_ha_un_artefatto_da_mostrare(numero):
    """La tabella risolve 1..11 senza KeyError, con entrambi i valori di
    simplify.enabled. Era il «avanzando lungo la pipeline la geometria sparisce
    del tutto»: gli step 7, 10 e 11 non hanno un artefatto proprio, e il
    browser riceveva un errore e svuotava la scena."""
    from meshrec.app.server import sorgente_geometria
    from meshrec.core import pipeline

    for abilitata in (False, True):
        cfg = PipelineConfig(input=InputConfig(path=Path("nuvola.ply")))
        cfg.simplify.enabled = abilitata
        da = sorgente_geometria(numero, cfg)
        assert da in pipeline.ARTIFACTS, f"lo step {numero} rimanda a un artefatto che non esiste"


def test_lo_step_8_senza_semplificazione_mostra_la_superficie_dello_step_6():
    """08_simplified.ply esiste solo con la semplificazione abilitata, che nel
    config di lavoro e' `false`: oggi lo step 8 mostra un viewport vuoto pur
    essendo uno step riuscito. E' la stessa dipendenza che pipeline.run() ha
    per from_step=9 (core/pipeline.py:57-58)."""
    from meshrec.app.server import sorgente_geometria

    cfg = PipelineConfig(input=InputConfig(path=Path("nuvola.ply")))
    cfg.simplify.enabled = False
    assert sorgente_geometria(8, cfg) == 6
    cfg.simplify.enabled = True
    assert sorgente_geometria(8, cfg) == 8


def test_gli_step_che_solo_misurano_rimandano_a_chi_ha_prodotto():
    """Lo step 7 misura la superficie del 6; il 10 e l'11 misurano ed esportano
    il volume del 9. Scritti a mano e non calcolati: core/pipeline.py:42-48
    documenta che un calcolo equivalente su ARTIFACTS era gia' sbagliato in due
    punti, e uno di quei due era proprio ARTIFACTS[7], che non esiste."""
    from meshrec.app.server import sorgente_geometria

    cfg = PipelineConfig(input=InputConfig(path=Path("nuvola.ply")))
    assert sorgente_geometria(7, cfg) == 6
    assert sorgente_geometria(10, cfg) == 9
    assert sorgente_geometria(11, cfg) == 9


def test_la_mesh_di_uno_step_che_solo_misura_dichiara_da_dove_viene(cliente, tmp_path):
    """Mostrare l'artefatto di un altro step senza dirlo sarebbe esattamente il
    risultato plausibile che nessuna metrica smentisce. Il numero che
    l'interfaccia dichiara e' questo, non uno che il browser deduce."""
    import open3d as o3d

    from meshrec.core import pipeline

    corsa = tmp_path / "corsa"
    corsa.mkdir()
    cubo = o3d.geometry.TriangleMesh.create_box(1.0, 1.0, 1.0)
    o3d.io.write_triangle_mesh(str(corsa / pipeline.ARTIFACTS[6]), cubo)

    risposta = cliente.get("/api/mesh/7")
    assert risposta.status_code == 200
    assert risposta.headers["X-Da-Step"] == "6"

    # Lo step 8 col config predefinito (simplify.enabled = False) passa dalla
    # stessa strada, e va provato per la tratta e non solo per la funzione.
    risposta = cliente.get("/api/mesh/8")
    assert risposta.status_code == 200
    assert risposta.headers["X-Da-Step"] == "6"

    # Lo step che ha una geometria propria dichiara se stesso: senza questo, un
    # X-Da-Step scritto a caso passerebbe i due controlli qui sopra.
    risposta = cliente.get("/api/mesh/6")
    assert risposta.status_code == 200
    assert risposta.headers["X-Da-Step"] == "6"


def test_uno_step_il_cui_artefatto_a_monte_manca_nomina_lo_step_da_eseguire(cliente):
    """Resta distinto da «non c'e'»: lo step 7 senza il 6 eseguito non tace, e
    non nomina se stesso — nomina lo step che deve girare per primo."""
    risposta = cliente.get("/api/mesh/7")
    assert risposta.status_code == 400
    messaggio = risposta.json()["messaggio"]
    assert "6" in messaggio
    assert "06_repaired.ply" in messaggio
```

`Path` e `InputConfig` sono già importati in cima a `tests/test_server.py`; `PipelineConfig` pure.

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_server.py -k "sorgente or dichiara or misura or artefatto_da_mostrare or a_monte" -v`
Expected: FAIL con `ImportError: cannot import name 'sorgente_geometria'` sui primi tre, e `assert 400 == 200` sul quarto.

- [ ] **Step 3: Scrivere la tabella**

In `meshrec/src/meshrec/app/server.py`, a livello di modulo, subito prima di `def create_app(config_path: Path) -> FastAPI:` (`:261`):

```python
# Da quale step viene la geometria che si mostra quando si chiede uno step.
# Esplicita e non calcolata: core/pipeline.py:42-48 documenta che un calcolo
# equivalente su ARTIFACTS era gia' sbagliato in due punti, uno dei quali era
# ARTIFACTS[7], che non esiste. Stesso errore, stessa cura, stessa forma di
# _RESUME_POINTS.
# Gli step 7, 10 e 11 misurano ed esportano: non producono geometria propria.
_SORGENTE_GEOMETRIA: dict[int, int] = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 6, 8: 8, 9: 9, 10: 9, 11: 9,
}


def sorgente_geometria(numero: int, cfg: PipelineConfig) -> int:
    """Lo step il cui artefatto si disegna quando si chiede `numero`.

    Il numero che torna di qui finisce nell'intestazione X-Da-Step, e
    l'interfaccia lo dichiara sotto il viewport. Mostrare l'artefatto di un
    altro step senza dirlo sarebbe il risultato plausibile che nessuna metrica
    smentisce, percio' la ricaduta a monte e la sua dichiarazione sono un punto
    solo e non due.
    """
    if numero not in _SORGENTE_GEOMETRIA:
        raise ValueError(
            f"lo step {numero} non esiste: la pipeline ha gli step "
            f"{sorted(_SORGENTE_GEOMETRIA)}"
        )
    # 08_simplified.ply esiste solo con la semplificazione abilitata, che nel
    # config di lavoro e' `false`: e' la stessa dipendenza che pipeline.run()
    # ha per from_step=9 (core/pipeline.py:57-58). Senza questo ramo lo step 8
    # mostra un viewport vuoto pur essendo uno step riuscito.
    if numero == 8 and not cfg.simplify.enabled:
        return 6
    return _SORGENTE_GEOMETRIA[numero]
```

- [ ] **Step 4: Passare la risoluzione all'endpoint della mesh**

In `meshrec/src/meshrec/app/server.py`, dentro `def mesh(numero: int) -> Response:` (`:626`), sostituire la guardia e le due righe che seguono:

```python
        cfg = corrente()
        # /api/cloud non passa di qui apposta: gli step 1..4 hanno tutti un
        # artefatto proprio, non c'e' nessuna ricaduta da risolvere, e toccarlo
        # cambierebbe il messaggio di guardie che altri controlli sorvegliano.
        da = sorgente_geometria(numero, cfg)
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[da]
        if not percorso.exists():
            # Nomina lo step a monte, non quello chiesto: e' quello che deve
            # girare per primo, e dirlo distingue «non c'e' ancora» da «questo
            # step non produce geometria».
            raise FileNotFoundError(
                f"lo step {da} non ha ancora prodotto {pipeline.ARTIFACTS[da]}"
            )
```

E nella `Response` finale dello stesso endpoint:

```python
        return Response(
            content=corpo,
            media_type="application/octet-stream",
            headers={
                "X-Vertices": str(len(vertici)),
                "X-Triangles": str(len(facce)),
                "X-Da-Step": str(da),
            },
        )
```

- [ ] **Step 5: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_server.py -q`
Expected: PASS, compresi i tre test preesistenti citati sopra.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/app/server.py meshrec/tests/test_server.py
git commit -m "feat(server): gli step che solo misurano mostrano la geometria di chi ha prodotto"
```

---

### Task 4: La didascalia dichiara la provenienza e il passo del voxel

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js` (`mostraNuvolaDelloStep` a `:214-242`, `STEP_CON_MESH` a `:247`, `mostraStep` a `:249-280`)
- Modify: `meshrec/tests/test_app_js.py`

**Interfaces:**
- Consumes: `X-Da-Step` dal Task 3; `X-Voxel` che `app/server.py:510` manda già.
- Produces: `function scriviConteggi(testo, chiesto, da = chiesto)` di primo livello in `app.js`, che il Task 5 riusa; variabile di modulo `sorgenteMostrata`, che il Task 5 legge per decidere se il fantasma ha senso.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere in coda a `meshrec/tests/test_app_js.py`:

```python
def test_la_didascalia_dichiara_lo_step_da_cui_viene_la_geometria(tmp_path):
    """Criterio 3 della spec. Il viewport che mostra la superficie dello step 6
    mentre l'elenco a sinistra dice «step 7» e' una vista che contraddice la
    propria didascalia: peggio di una vista vuota, che almeno non afferma
    niente."""
    _esegui(tmp_path, _DOM + """
const conteggi = document.getElementById("conteggi");
""" + _funzioni("scriviConteggi") + """
scriviConteggi("9.659 vertici, 19.314 triangoli", 7, 6);
assert.match(conteggi.textContent, /9\\.659 vertici/);
assert.match(conteggi.textContent, /step 7/);
assert.match(conteggi.textContent, /step 6/);

// Uno step con geometria propria non dichiara niente in piu': una didascalia
// che dice «mostrata quella dello step 3» sullo step 3 e' rumore.
scriviConteggi("116.059 punti disegnati su 4.229.538", 3, 3);
assert.equal(conteggi.textContent, "116.059 punti disegnati su 4.229.538");

// E il predefinito e' «propria»: /api/cloud non manda X-Da-Step, e il
// chiamante passa due argomenti soli.
scriviConteggi("100 punti disegnati su 100", 2);
assert.equal(conteggi.textContent, "100 punti disegnati su 100");
""")


def test_gli_step_senza_geometria_propria_chiedono_la_mesh_e_non_la_nuvola():
    """Lo step 7 chiede /api/mesh/7, che il server risolve sulla superficie
    dello step 6. Restasse fra gli step «nuvola» chiederebbe /api/cloud/7, che
    non esiste, e la scena tornerebbe vuota: la ricaduta del server non
    arriverebbe mai al viewport."""
    trovato = re.search(r"const STEP_CON_MESH = new Set\(\[([^\]]*)\]\)", _modulo())
    assert trovato is not None, "STEP_CON_MESH non e' piu' nel modulo"
    numeri = {int(pezzo) for pezzo in trovato.group(1).split(",") if pezzo.strip()}
    assert numeri == {5, 6, 7, 8, 9, 10, 11}, (
        f"gli step che chiedono la mesh sono {numeri}: dal 5 in poi la geometria "
        "e' sempre una superficie o un volume"
    )


def test_il_passo_del_voxel_di_disegno_finisce_nella_didascalia(tmp_path):
    """La densita' disegnata salta fra lo step 2 (4.229.538 punti decimati di
    circa dieci volte) e lo step 3 (116.059 disegnati interi). Il passo che lo
    spiega il server lo calcola gia' e lo manda in X-Voxel (app/server.py:510),
    dove il modulo lo buttava senza leggerlo: un fatto misurato che si perdeva.

    Zero non e' un passo: viewport.decimate lo restituisce per dire «nessuna
    decimazione applicata» (tests/test_viewport.py), e scriverlo come «voxel di
    disegno 0 mm» sarebbe una misura inventata.
    """
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
        + _funzioni("passoDiDisegno") + """
assert.equal(passoDiDisegno(0), "");
assert.match(passoDiDisegno(10.5), /10,5/);
assert.match(passoDiDisegno(10.5), /voxel/);
""")
```

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_app_js.py -k "didascalia or senza_geometria_propria or voxel_di_disegno" -v`
Expected: FAIL. `IndexError` dentro `_sorgente_di` per `scriviConteggi` e `passoDiDisegno`; `assert {5, 6, 8, 9} == {5, 6, 7, 8, 9, 10, 11}`.

- [ ] **Step 3: Scrivere le due funzioni e riscrivere le didascalie**

In `meshrec/src/meshrec/ui/app.js`, subito prima di `async function mostraNuvolaDelloStep` (`:214`):

```js
// Il testo sotto la vista, scritto in un punto solo: le due strade che
// disegnano devono dichiarare le stesse cose nello stesso modo, e scriverlo
// due volte lascerebbe che una delle due smetta di dichiararne una.
// `da` diverso da `chiesto` vuol dire che questo step non produce geometria
// propria e sta mostrando quella di un altro (app/server.py, X-Da-Step).
function scriviConteggi(testo, chiesto, da = chiesto) {
  document.getElementById("conteggi").textContent = da === chiesto
    ? testo
    : `${testo} — lo step ${chiesto} non produce geometria propria: mostrata quella dello step ${da}`;
}

// Il passo del voxel con cui il disegno e' stato decimato, per la didascalia.
// Stringa vuota a zero: viewport.decimate restituisce 0 per dire «nessuna
// decimazione applicata», e scrivere «voxel di disegno 0 mm» sarebbe una
// misura inventata al posto di un'assenza.
function passoDiDisegno(voxel) {
  return voxel > 0 ? `, voxel di disegno ${voxel.toLocaleString("it")} mm` : "";
}
```

Dentro `mostraNuvolaDelloStep`, sostituire la lettura delle intestazioni (`:226-227`) e la scrittura della didascalia (`:236-237`):

```js
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const voxel = Number(risposta.headers.get("X-Voxel"));
```

```js
  // Sempre entrambi: una nuvola decimata che non lo dichiara e' un dato falso.
  // E accanto il passo che spiega di quanto: il salto di densita' fra uno step
  // e il successivo e' il salto della decimazione, non quello del dato.
  scriviConteggi(
    `${disegnati.toLocaleString("it")} punti disegnati su ${pieni.toLocaleString("it")}${passoDiDisegno(voxel)}`,
    numero,
  );
  // Gli step 1..4 hanno tutti un artefatto proprio: /api/cloud non risolve
  // nessuna ricaduta, quindi qui la sorgente e' sempre lo step chiesto.
  sorgenteMostrata = numero;
```

Sostituire `STEP_CON_MESH` (`:244-247`):

```js
// Gli step la cui geometria e' una superficie o un volume: dal 5 in poi
// l'artefatto non e' piu' una nuvola, e disegnarne i soli vertici mostrerebbe
// punti dove c'e' un solido. Il 7, il 10 e l'11 ci stanno dentro pur non
// producendo geometria propria: /api/mesh li risolve sullo step che l'ha
// prodotta (app/server.py, sorgente_geometria), e chiederli a /api/cloud
// lascerebbe la scena vuota.
const STEP_CON_MESH = new Set([5, 6, 7, 8, 9, 10, 11]);

// Lo step da cui viene la geometria disegnata adesso. Diverso da stepMostrato
// sugli step che solo misurano, ed e' cio' che dice se un fantasma del
// passaggio precedente avrebbe senso o disegnerebbe due volte la stessa cosa.
let sorgenteMostrata = null;
```

Dentro `mostraStep`, dopo la lettura di `X-Triangles` (`:265`):

```js
  const da = Number(risposta.headers.get("X-Da-Step"));
```

e sostituire la scrittura della didascalia (`:277-278`):

```js
  // I conteggi sono quelli che il server ha contato sull'artefatto: per lo
  // step 9 sono i vertici e i triangoli del contorno, non i nodi del volume.
  scriviConteggi(
    `${vertici.toLocaleString("it")} vertici, ${triangoli.toLocaleString("it")} triangoli`,
    numero,
    da,
  );
  sorgenteMostrata = da;
```

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_app_js.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "feat(interfaccia): la didascalia dice da dove viene la geometria e con che voxel"
```

---

### Task 5: Il fantasma del passaggio precedente

**Files:**
- Modify: `meshrec/src/meshrec/ui/viewport.js` (`scatolaDelGruppo` a `:137-143`, `svuota` a `:154-178`, due metodi nuovi)
- Modify: `meshrec/src/meshrec/ui/app.js` (tabella nuova, `ricaricaVista` a `:378-385`, gestore dell'interruttore)
- Modify: `meshrec/src/meshrec/ui/index.html` (interruttore dentro `.comandi-vista`)
- Modify: `meshrec/tests/test_app_js.py`
- Modify: `meshrec/tests/test_server.py`

**Interfaces:**
- Consumes: la variabile di modulo `sorgenteMostrata` dal Task 4 (non `scriviConteggi`: il fantasma appende alla didascalia già scritta, non la riscrive); il contenitore `.comandi-vista` dal Task 2; `X-Points-Total`, `X-Vertices` e `X-Triangles` dal server.
- Produces: `vista.mostraFantasma(vertici, facce = null)` e `vista.togliFantasma()` in `viewport.js`; `async function mostraFantasmaDelloStep(numero, ordine)` in `app.js`.

- [ ] **Step 1: Scrivere il test del conteggio onesto, lato server**

Il conteggio che il fantasma dichiara è quello **pieno**, e deve coincidere con la misura dello step che l'ha prodotto. Su `lab_crop` sono i 6.329.096 punti dello step 1 (`01_load.points_kept`) e i 4.229.538 dello step 2 (`02_segment.points_after`), ma `runs/` non è nel repository: la grandezza sorvegliata è la stessa, la corsa è sintetica.

Aggiungere in coda a `meshrec/tests/test_server.py`:

```python
def test_il_conteggio_pieno_non_e_quello_disegnato(cliente, tmp_path):
    """Il fantasma dichiara il conteggio PIENO dello step che l'ha prodotto, e
    quel numero e' quello che metrics.json porta: su lab_crop 6.329.096 per lo
    step 1 (points_kept) e 4.229.538 per il 2 (points_after).

    Il disegnato no, ed e' giusto: anche il fantasma passa dal budget dei
    400.000 punti, e confrontare due decimazioni fra loro sarebbe confrontare
    due approssimazioni invece che il dato con la sua misura. Un fantasma che
    disegna una nuvola diversa da quella che dichiara e' la forma esatta del
    risultato plausibile contro cui e' costruito tutto il progetto.
    """
    import numpy as np

    from meshrec.core import io, pipeline

    corsa = tmp_path / "corsa"
    punti = np.random.default_rng(0).random((5_000, 3)) * 1000.0
    io.write_cloud(corsa / pipeline.ARTIFACTS[1], punti)

    risposta = cliente.get("/api/cloud/1?max_points=200")
    assert risposta.status_code == 200
    assert int(risposta.headers["X-Points-Total"]) == 5_000, (
        "il conteggio pieno non e' quello del dato: e' quello del disegno"
    )
    assert int(risposta.headers["X-Points-Drawn"]) <= 200
    assert int(risposta.headers["X-Points-Drawn"]) < 5_000, (
        "precondizione: la decimazione deve essere davvero avvenuta, "
        "altrimenti i due conteggi coinciderebbero per caso"
    )
```

- [ ] **Step 2: Scrivere i test del modulo del browser**

Aggiungere in coda a `meshrec/tests/test_app_js.py`:

```python
def test_il_fantasma_viene_dal_passaggio_precedente_con_geometria_propria():
    """La tabella e' scritta a mano e non calcolata come «numero - 1»: sullo
    step 8 il precedente con geometria propria e' il 6, perche' il 7 misura e
    non produce niente. E' lo stesso errore che core/pipeline.py:42-48
    documenta, per la stessa strada."""
    trovato = re.search(r"const FANTASMA_DI = \{([^}]*)\}", _modulo())
    assert trovato is not None, "FANTASMA_DI non e' nel modulo"
    coppie = dict(
        (int(chiave), int(valore))
        for chiave, valore in re.findall(r"(\d+)\s*:\s*(\d+)", trovato.group(1))
    )
    assert coppie == {2: 1, 3: 2, 8: 6}, (
        f"le coppie del fantasma sono {coppie}: acceso solo dove il conteggio "
        "cala davvero — ritaglio, sfoltimento, semplificazione"
    )


def test_il_fantasma_dichiara_il_conteggio_pieno_e_non_quello_disegnato():
    """Il disegnato e' una decimazione come quella della geometria corrente, e
    metterli a confronto direbbe che due approssimazioni si somigliano, non che
    il dato e' quello che si dichiara."""
    modulo = _senza_commenti_js(_modulo())
    trovato = re.search(
        r"async function mostraFantasmaDelloStep\(.*?\n\}", modulo, flags=re.DOTALL
    )
    assert trovato is not None, "mostraFantasmaDelloStep non e' una funzione di primo livello"
    corpo = trovato.group(0)
    assert "X-Points-Total" in corpo
    assert "X-Points-Drawn" not in corpo, (
        "il fantasma dichiara il conteggio disegnato: e' il confronto sbagliato"
    )


def test_il_fantasma_non_si_disegna_dove_ripeterebbe_la_geometria_corrente(tmp_path):
    """Sullo step 8 senza semplificazione il server serve gia' la superficie
    dello step 6 (X-Da-Step = 6): sovrapporgli il fantasma dello step 6
    disegnerebbe due volte la stessa cosa, con lo z-fighting e nessuna
    informazione in piu'."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
        + _funzioni("fantasmaHaSenso") + """
// step 8 con la semplificazione: la geometria corrente e' propria, il fantasma
// dello step 6 dice quanto la semplificazione ha tolto.
assert.equal(fantasmaHaSenso(8, 8, true), true);
// step 8 senza: la geometria corrente E' gia' quella dello step 6.
assert.equal(fantasmaHaSenso(8, 6, true), false);
// step 7: nessuna coppia, e comunque mostra il 6.
assert.equal(fantasmaHaSenso(7, 6, true), false);
// interruttore spento.
assert.equal(fantasmaHaSenso(2, 2, false), false);
assert.equal(fantasmaHaSenso(2, 2, true), true);
""")
```

- [ ] **Step 3: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_server.py -k conteggio_pieno tests/test_app_js.py -k fantasma -v`
Expected: FAIL. Il test del server passa già (l'intestazione esiste) — è una rete, non un rosso: annotarlo e proseguire. I tre del modulo falliscono con `FANTASMA_DI non e' nel modulo`, `mostraFantasmaDelloStep non e' una funzione di primo livello`, `il modulo non ha una funzione fantasmaHaSenso`.

- [ ] **Step 4: Aggiungere il secondo gruppo al viewport**

In `meshrec/src/meshrec/ui/viewport.js`, accanto a `let box = null;` (`:48`):

```js
  // Il fantasma: la geometria del passaggio precedente, dietro quella corrente.
  // Dentro `gruppo` come il box di ritaglio, cosi' la stessa traversata di
  // svuota() ne libera i buffer. Fuori da scatolaDelGruppo() per la stessa
  // ragione del box: l'ingombro deve restare quello della geometria corrente,
  // altrimenti la guardia della camera e il cursore del taglio si tarerebbero
  // su una nuvola che non e' quella disegnata.
  let fantasma = null;
```

In `scatolaDelGruppo` (`:137-143`):

```js
    for (const figlio of gruppo.children) {
      if (figlio !== box && figlio !== fantasma) scatola.expandByObject(figlio);
    }
```

In `svuota()`, accanto a `box = null;` (`:176`):

```js
      fantasma = null;
```

Nell'oggetto restituito, dopo `mostraMesh`:

```js
    // Il passaggio precedente, dietro quello corrente. Grigio, quasi
    // trasparente, e senza depthWrite: deve lasciarsi attraversare da cio' che
    // sta davanti invece di occluderlo.
    // Un metodo solo per nuvola e superficie: `facce` a null da' dei punti, e
    // le tre coppie del fantasma sono due nuvole e una superficie.
    // Costo: il commento a svuota() misura 7,6 MB di attributi per geometria,
    // e questo li raddoppia. Su un budget di disegno di 400.000 punti resta
    // trascurabile.
    mostraFantasma(vertici, facce = null) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      if (facce === null) {
        fantasma = new THREE.Points(geometria, new THREE.PointsMaterial({
          size: 1.5, sizeAttenuation: false, color: 0x8a8579,
          transparent: true, opacity: 0.15, depthWrite: false,
          clippingPlanes: pianiTaglio,
        }));
      } else {
        geometria.setIndex(new THREE.BufferAttribute(facce, 1));
        geometria.computeVertexNormals();
        fantasma = new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
          color: 0x8a8579, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
          transparent: true, opacity: 0.15, depthWrite: false,
          clippingPlanes: pianiTaglio,
        }));
      }
      gruppo.add(fantasma);
    },
    // Spegnere l'interruttore libera davvero: togliere l'oggetto dalla scena
    // non cancella i suoi buffer, e' dispose a farlo (vedi svuota()).
    togliFantasma() {
      if (fantasma === null) return;
      fantasma.geometry.dispose();
      fantasma.material.dispose();
      gruppo.remove(fantasma);
      fantasma = null;
    },
```

- [ ] **Step 5: Chiedere e disegnare il fantasma dal modulo**

In `meshrec/src/meshrec/ui/app.js`, subito dopo la dichiarazione di `sorgenteMostrata` (Task 4):

```js
// Da quale step viene il fantasma. Acceso solo dove il conteggio cala davvero:
// il ritaglio dello step 2, lo sfoltimento del 3, la semplificazione dell'8.
// Scritte a mano e non calcolate come «numero - 1»: sullo step 8 il precedente
// con geometria propria e' il 6, perche' il 7 misura e non produce niente.
// Fuori da queste tre coppie due geometrie sovrapposte — il 5 contro il 6, per
// dire — fanno z-fighting e non informano nessuno.
const FANTASMA_DI = { 2: 1, 3: 2, 8: 6 };
let fantasmaAcceso = true;

// Pura apposta, cosi' la regola si guarda da fuori invece di dedurla dai punti
// in cui e' usata. `sorgente` e' lo step da cui viene la geometria corrente:
// quando non e' lo step chiesto, la geometria corrente e' gia' quella di un
// altro e il fantasma la ridisegnerebbe.
function fantasmaHaSenso(chiesto, sorgente, acceso) {
  return acceso && sorgente === chiesto && FANTASMA_DI[chiesto] !== undefined;
}

// Il passaggio precedente dietro quello corrente. E' la risposta al «di
// passaggio in passaggio si riparte da zero»: i due conteggi stanno uno
// accanto all'altro invece che uno al posto dell'altro, e quello che il
// ritaglio ha tolto si vede invece di sparire in silenzio.
async function mostraFantasmaDelloStep(numero, ordine) {
  const comando = document.getElementById("fantasma-comando");
  comando.hidden = FANTASMA_DI[numero] === undefined;
  if (!fantasmaHaSenso(numero, sorgenteMostrata, fantasmaAcceso)) return;
  const da = FANTASMA_DI[numero];
  const emissione = apriGeometria();
  const risposta = await fetch(da <= 4 ? `/api/cloud/${da}` : `/api/mesh/${da}`);
  // Un fantasma che non arriva non e' un errore da annunciare: lo step a monte
  // puo' semplicemente non essere ancora girato, e la geometria corrente resta
  // quella che e'. Il silenzio qui non nasconde niente che l'utente abbia
  // chiesto.
  if (!risposta.ok) return;
  const pieni = Number(risposta.headers.get(da <= 4 ? "X-Points-Total" : "X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await risposta.arrayBuffer();
  // Dopo l'ultima attesa e prima della prima scrittura, come le due strade che
  // disegnano: un fantasma partito per lo step 2 non deve posarsi sul 9.
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return;
  if (da <= 4) {
    vista.mostraFantasma(new Float32Array(grezzi));
  } else {
    vista.mostraFantasma(
      new Float32Array(grezzi, 0, pieni * 3),
      new Uint32Array(grezzi, pieni * 3 * 4, triangoli * 3),
    );
  }
  // Il conteggio PIENO, non quello disegnato: anche il fantasma passa dal
  // budget dei 400.000 punti, e mettere a confronto due decimazioni direbbe
  // che due approssimazioni si somigliano, non che il dato e' quello che si
  // dichiara. Su lab_crop sono i 6.329.096 punti dello step 1 contro i
  // 4.229.538 dello step 2: e' li' che si vede che cosa il ritaglio ha tolto.
  document.getElementById("conteggi").textContent +=
    ` — prima: ${pieni.toLocaleString("it")}`;
}
```

Sostituire `ricaricaVista` (`:378-385`):

```js
function ricaricaVista(numero, ordine = generazione) {
  // `disegnato` e' falso quando la risposta e' stata scartata: senza guardarlo,
  // il cursore si rifarebbe sull'ingombro di una geometria che qualcun altro
  // ha disegnato, cioe' su una lettura che non appartiene a questo numero.
  mostraStep(numero, ordine).then((disegnato) => {
    if (!disegnato || superata(ordine)) return;
    riallineaTaglio(numero);
    // Dopo, e non in parallelo: il fantasma appende alla didascalia che
    // mostraStep ha appena scritto, e partendo insieme potrebbe appendere a
    // quella di prima.
    mostraFantasmaDelloStep(numero, ordine);
  });
}
```

Accanto al gestore del bottone «Inquadra» (Task 2):

```js
document.getElementById("fantasma").addEventListener("change", (evento) => {
  fantasmaAcceso = evento.target.checked;
  if (!fantasmaAcceso) {
    vista.togliFantasma();
    return;
  }
  if (stepMostrato !== null) mostraFantasmaDelloStep(stepMostrato, generazione);
});
```

- [ ] **Step 6: Aggiungere l'interruttore al markup**

In `meshrec/src/meshrec/ui/index.html`, dentro `<div class="comandi-vista" id="comandi-vista">`, dopo il bottone:

```html
      <!-- Nasce nascosto e acceso: app.js lo mostra solo sugli step dove un
           fantasma esiste, cioe' dove il conteggio cala. Un interruttore su uno
           step senza fantasma sarebbe un comando che non fa nulla. -->
      <label id="fantasma-comando" hidden>
        <input type="checkbox" id="fantasma" checked>
        passaggio precedente
      </label>
```

- [ ] **Step 7: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_app_js.py tests/test_server.py tests/test_viewport_js.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/ui/viewport.js meshrec/src/meshrec/ui/app.js \
        meshrec/src/meshrec/ui/index.html meshrec/tests/test_app_js.py \
        meshrec/tests/test_server.py
git commit -m "feat(viewport): il passaggio precedente resta in vista dietro quello corrente"
```

---

### Task 6: Il deposito dello storico

**Files:**
- Create: `meshrec/src/meshrec/app/storico.py`
- Create: `meshrec/tests/test_storico.py`

**Interfaces:**
- Consumes: `core.io.scrivi_atomico(path, scrittore)` (`core/io.py:101`), che passa allo scrittore un percorso temporaneo e poi rinomina.
- Produces, tutte con `out_dir: Path` come primo argomento:
  - `TETTO: int = 200`
  - `esiste(out_dir) -> bool`
  - `deposita(out_dir, testo: str, endpoint: str, campi: list[str]) -> int`
  - `indietro(out_dir) -> str | None`
  - `avanti(out_dir) -> str | None`

Nessun import di FastAPI e nessuna conoscenza di HTTP: il Task 7 ci mette sopra gli endpoint.

**Il modello.** Il deposito tiene **ogni stato, compreso quello corrente**. La versione 1 è il config prima della prima modifica; ogni scrittura ne aggiunge una e sposta il cursore in avanti. «Indietro» arretra il cursore e restituisce il testo su cui è arrivato. Storico vuoto (cursore sulla prima versione) vuol dire che non c'è niente prima, e `indietro` risponde `None`.

- [ ] **Step 1: Scrivere i test**

Creare `meshrec/tests/test_storico.py`:

```python
"""Il deposito delle versioni di configurazione. Senza server e senza HTTP.

Su disco e non in memoria: una pila in memoria muore col processo, cioe'
proprio quando serve sapere che cosa si era cambiato.
"""

from __future__ import annotations

import json
from pathlib import Path

from meshrec.app import storico


def test_indietro_rimette_il_testo_di_prima_byte_per_byte(tmp_path: Path):
    """L'undo ripristina davvero: non «una configurazione equivalente», la
    stessa. Un ripristino che riscrive il file passando da un modello lo
    normalizza — ordine delle chiavi, virgolette, campi predefiniti resi
    espliciti — e il confronto direbbe «uguale» su un file diverso."""
    storico.deposita(tmp_path, "prima: 1\n", "avvio", [])
    storico.deposita(tmp_path, "dopo: 2\n", "PUT /api/config", ["surface.poisson_depth"])
    assert storico.indietro(tmp_path) == "prima: 1\n"


def test_uno_storico_senza_niente_prima_risponde_none(tmp_path: Path):
    """Il difetto opposto — un silenzio identico fra riuscita e nulla-da-fare —
    e' gia' stato prodotto e corretto una volta su questo progetto, sul bottone
    Annulla (ui/app.js:117-122). Qui l'assenza si distingue alla radice: None
    non e' una stringa vuota."""
    assert storico.indietro(tmp_path) is None
    storico.deposita(tmp_path, "sola: 1\n", "avvio", [])
    assert storico.indietro(tmp_path) is None


def test_avanti_torna_dove_si_era(tmp_path: Path):
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["b"])
    assert storico.indietro(tmp_path) == "due\n"
    assert storico.indietro(tmp_path) == "uno\n"
    assert storico.avanti(tmp_path) == "due\n"
    assert storico.avanti(tmp_path) == "tre\n"
    assert storico.avanti(tmp_path) is None


def test_una_scrittura_nuova_tronca_la_coda_oltre_il_cursore(tmp_path: Path):
    """Due futuri che convivono non sono uno storico, sono un albero, e nessun
    comando dell'interfaccia saprebbe quale ramo intende."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    storico.indietro(tmp_path)
    storico.deposita(tmp_path, "altro\n", "POST /api/crop", ["segment.crop_min"])
    assert storico.avanti(tmp_path) is None, "la coda scartata e' ancora raggiungibile"
    assert storico.indietro(tmp_path) == "uno\n"


def test_il_tetto_scarta_le_piu_vecchie_e_il_cursore_resta_coerente(tmp_path: Path):
    """Tetto misurato e non scelto: il config di lavoro pesa 1.328 byte, quindi
    duecento versioni costano 265,6 kB contro i circa 400 MB di artefatti che
    una corsa lascia."""
    for indice in range(storico.TETTO + 1):
        storico.deposita(tmp_path, f"versione: {indice}\n", "PUT /api/config", ["a"])
    rimaste = sorted((tmp_path / ".storico").glob("[0-9][0-9][0-9][0-9].yaml"))
    assert len(rimaste) == storico.TETTO
    assert rimaste[0].stem == "0002", "la prima versione doveva essere scartata"
    # Il cursore sta sull'ultima e «indietro» funziona ancora: un tetto che
    # lascia il cursore su un file cancellato romperebbe proprio il comando che
    # serve dopo una modifica di troppo.
    assert storico.indietro(tmp_path) == f"versione: {storico.TETTO - 1}\n"


def test_il_registro_tiene_una_riga_per_versione(tmp_path: Path):
    """Stessa forma in sola aggiunta del registro degli esperimenti della Fase
    2, per la stessa ragione: un file che si allunga non perde cio' che aveva.
    La provenienza e' parte del risultato, non un di piu'."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "POST /api/crop", ["segment.crop_min", "segment.crop_max"])
    righe = [
        json.loads(riga)
        for riga in (tmp_path / ".storico" / "registro.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [riga["versione"] for riga in righe] == [1, 2]
    assert righe[1]["endpoint"] == "POST /api/crop"
    assert righe[1]["campi"] == ["segment.crop_min", "segment.crop_max"]
    assert righe[1]["istante"].startswith("20")


def test_un_cursore_illeggibile_non_solleva(tmp_path: Path):
    """Uno stato illeggibile e' uno stato assente, come gia' fa
    core/steps.py:85 per lo stato della corsa. Sollevare qui vorrebbe dire che
    un file di servizio corrotto impedisce di annullare, cioe' proprio quando
    si sta cercando di rimediare a qualcosa."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    (tmp_path / ".storico" / "cursore.json").write_text("{non json", encoding="utf-8")
    assert storico.indietro(tmp_path) == "uno\n"


def test_esiste_dice_se_c_e_gia_una_versione(tmp_path: Path):
    assert storico.esiste(tmp_path) is False
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    assert storico.esiste(tmp_path) is True
```

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_storico.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.app.storico'`.

- [ ] **Step 3: Scrivere il modulo**

Creare `meshrec/src/meshrec/app/storico.py`:

```python
"""Storico delle modifiche di configurazione fatte dall'interfaccia.

Su disco e non in memoria: una pila in memoria muore col processo, cioe'
proprio quando serve sapere che cosa si era cambiato. Il deposito sta dentro
la cartella della corsa, accanto agli artefatti che quelle modifiche hanno
prodotto, cosi' la provenienza viaggia con il risultato.

Il deposito tiene ogni stato, compreso quello corrente: la versione 1 e' il
config prima della prima modifica, ogni scrittura ne aggiunge una e sposta il
cursore in avanti. «Indietro» arretra il cursore e restituisce il testo su cui
e' arrivato; sulla prima versione non c'e' niente prima, e risponde None.

Non sa niente di HTTP e non importa FastAPI: chi lo usa e' app/server.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from meshrec.core import io

# Quante versioni si tengono. Misurato e non scelto: il config di lavoro
# (meshrec/prova-interfaccia.yaml) pesa 1.328 byte, quindi il tetto costa
# 265,6 kB, contro i circa 400 MB di artefatti che una corsa lascia.
TETTO = 200

CARTELLA = ".storico"


def _cartella(out_dir: Path) -> Path:
    return Path(out_dir) / CARTELLA


def _percorso(out_dir: Path, numero: int) -> Path:
    return _cartella(out_dir) / f"{numero:04d}.yaml"


def _numeri(out_dir: Path) -> list[int]:
    """I numeri delle versioni presenti, in ordine. Il glob e' sulla forma del
    nome e non su "*.yaml": nella stessa cartella non deve poter entrare per
    sbaglio un file di configurazione e diventare una versione."""
    cartella = _cartella(out_dir)
    if not cartella.is_dir():
        return []
    return sorted(
        int(percorso.stem) for percorso in cartella.glob("[0-9][0-9][0-9][0-9].yaml")
    )


def _cursore(out_dir: Path) -> int:
    """Dove siamo adesso. Zero quando non c'e' ancora nessuna versione."""
    numeri = _numeri(out_dir)
    if not numeri:
        return 0
    try:
        salvato = int(
            json.loads((_cartella(out_dir) / "cursore.json").read_text(encoding="utf-8"))["versione"]
        )
    except (OSError, ValueError, KeyError, TypeError):
        # Uno stato illeggibile e' uno stato assente, come core/steps.py:85 per
        # lo stato della corsa: si riparte dall'ultima versione, che e' quella
        # che config.yaml porta.
        return numeri[-1]
    # Il tetto puo' aver scartato la versione su cui il cursore stava.
    return min(max(salvato, numeri[0]), numeri[-1])


def _scrivi_cursore(out_dir: Path, numero: int) -> None:
    io.scrivi_atomico(
        _cartella(out_dir) / "cursore.json",
        lambda destinazione: destinazione.write_text(
            json.dumps({"versione": numero}), encoding="utf-8"
        ),
    )


def _applica_tetto(out_dir: Path) -> None:
    numeri = _numeri(out_dir)
    if len(numeri) <= TETTO:
        return
    for numero in numeri[: len(numeri) - TETTO]:
        _percorso(out_dir, numero).unlink()


def esiste(out_dir: Path) -> bool:
    """C'e' gia' almeno una versione depositata."""
    return bool(_numeri(out_dir))


def deposita(out_dir: Path, testo: str, endpoint: str, campi: list[str]) -> int:
    """Aggiunge `testo` in coda come versione nuova e torna il suo numero.

    Una scrittura nuova tronca la coda oltre il cursore: due futuri che
    convivono non sono uno storico, sono un albero, e nessun comando
    dell'interfaccia saprebbe quale ramo intende.
    """
    cartella = _cartella(out_dir)
    cartella.mkdir(parents=True, exist_ok=True)
    corrente = _cursore(out_dir)
    for numero in _numeri(out_dir):
        if numero > corrente:
            _percorso(out_dir, numero).unlink()

    nuovo = corrente + 1
    io.scrivi_atomico(
        _percorso(out_dir, nuovo),
        lambda destinazione: destinazione.write_text(testo, encoding="utf-8"),
    )
    # In sola aggiunta, come il registro degli esperimenti della Fase 2: un file
    # che si allunga non perde cio' che aveva. L'istante e' UTC perche' un
    # registro che cambia significato col fuso orario di chi lo legge non e' una
    # provenienza.
    riga = json.dumps(
        {
            "versione": nuovo,
            "istante": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "endpoint": endpoint,
            "campi": campi,
        },
        ensure_ascii=False,
    )
    with (cartella / "registro.jsonl").open("a", encoding="utf-8") as file:
        file.write(riga + "\n")

    _scrivi_cursore(out_dir, nuovo)
    _applica_tetto(out_dir)
    return nuovo


def indietro(out_dir: Path) -> str | None:
    """Il testo della versione precedente, o None se non c'e' niente prima."""
    corrente = _cursore(out_dir)
    precedenti = [numero for numero in _numeri(out_dir) if numero < corrente]
    if not precedenti:
        return None
    _scrivi_cursore(out_dir, precedenti[-1])
    return _percorso(out_dir, precedenti[-1]).read_text(encoding="utf-8")


def avanti(out_dir: Path) -> str | None:
    """Il testo della versione successiva, o None se siamo gia' in coda."""
    corrente = _cursore(out_dir)
    successivi = [numero for numero in _numeri(out_dir) if numero > corrente]
    if not successivi:
        return None
    _scrivi_cursore(out_dir, successivi[0])
    return _percorso(out_dir, successivi[0]).read_text(encoding="utf-8")
```

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_storico.py -v`
Expected: PASS, 8 test.

- [ ] **Step 5: Commit**

```bash
git add meshrec/src/meshrec/app/storico.py meshrec/tests/test_storico.py
git commit -m "feat(storico): un deposito su disco per le versioni della configurazione"
```

---

### Task 7: Lo storico innestato nel server

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py` (import; `scrivi_config` nuova dentro `create_app`; le tre chiamate a `save_config` a `:307`, `:464`, `:616`; due endpoint nuovi)
- Modify: `meshrec/tests/test_server.py` (test nuovi; estendere `test_nessun_endpoint_solleva_verso_il_browser` a `:1777`)

**Interfaces:**
- Consumes: `storico.esiste/deposita/indietro/avanti` dal Task 6; `steps.run_state(out_dir, cfg)` (`core/steps.py:122`), che torna una lista di dizionari con `numero` e `stato` fra `"valido"`, `"non valido"`, `"mai eseguito"`, `"fallito"`.
- Produces: `POST /api/storico/indietro` e `POST /api/storico/avanti`, che rispondono `{"annullato": bool, "perche": str}` oppure `{"annullato": true, "invalidati": [int], "steps": [...]}`. Il Task 8 li chiama.

- [ ] **Step 1: Scrivere i test**

Aggiungere in coda a `meshrec/tests/test_server.py`:

```python
def test_indietro_rimette_il_config_di_prima_byte_per_byte(cliente, tmp_path):
    """Criterio 8 della spec. Byte per byte e non «equivalente»: un ripristino
    che ripassa dal modello normalizza ordine e predefiniti, e il confronto
    direbbe «uguale» su un file diverso da quello che l'utente aveva."""
    percorso = tmp_path / "config.yaml"
    prima = percorso.read_bytes()

    corpo = cliente.get("/api/config").json()
    corpo["surface"]["poisson_depth"] = 7
    assert cliente.put("/api/config", json=corpo).status_code == 200
    assert percorso.read_bytes() != prima, "precondizione: la modifica deve essere avvenuta"

    risposta = cliente.post("/api/storico/indietro")
    assert risposta.status_code == 200
    assert risposta.json()["annullato"] is True
    assert percorso.read_bytes() == prima


def test_avanti_rifa_cio_che_indietro_aveva_disfatto(cliente, tmp_path):
    percorso = tmp_path / "config.yaml"
    corpo = cliente.get("/api/config").json()
    corpo["surface"]["poisson_depth"] = 7
    cliente.put("/api/config", json=corpo)
    dopo = percorso.read_bytes()

    cliente.post("/api/storico/indietro")
    risposta = cliente.post("/api/storico/avanti")
    assert risposta.json()["annullato"] is True
    assert percorso.read_bytes() == dopo


def test_uno_storico_vuoto_risponde_invece_di_tacere(cliente):
    """Criterio 9. Un silenzio identico fra riuscita e nulla-da-fare e' gia'
    stato prodotto e corretto una volta su questo progetto, sul bottone Annulla
    (ui/index.html:14-19): non va rifatto per una seconda strada."""
    risposta = cliente.post("/api/storico/indietro")
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["annullato"] is False
    assert corpo["perche"] == "niente da annullare"

    corpo = cliente.post("/api/storico/avanti").json()
    assert corpo["annullato"] is False
    assert corpo["perche"] == "niente da rifare"


def test_indietro_elenca_gli_step_tornati_non_validi(cliente, tmp_path):
    """L'undo non cancella gli artefatti: la catena di impronte della Fase 3 li
    marca «non valido» da se', ed e' il comportamento giusto — restano sul
    disco, pronti a tornare validi se si preme «avanti».

    Ma un ritorno indietro che cambia in silenzio lo stato di sette step
    sarebbe una modifica invisibile, e questo elenco e' cio' che lo dice.
    """
    from meshrec.core import steps

    cfg = load_config(tmp_path / "config.yaml")
    corsa = Path(cfg.run.out_dir)
    corsa.mkdir(parents=True, exist_ok=True)
    # Uno stato salvato che dichiara validi tutti gli step con le impronte di
    # adesso: senza, sono tutti "mai eseguito" e nessuno puo' diventare "non
    # valido", che e' proprio la grandezza sorvegliata.
    for voce in steps.run_state(corsa, cfg):
        steps.write_state(corsa, int(voce["numero"]), str(voce["impronta"]), "riuscito", None, 0.0)

    corpo = cliente.get("/api/config").json()
    corpo["surface"]["poisson_depth"] = 7
    cliente.put("/api/config", json=corpo)

    invalidati = cliente.post("/api/storico/indietro").json()["invalidati"]
    assert invalidati, "l'undo non ha dichiarato nessuno step invalidato"
    assert all(isinstance(numero, int) for numero in invalidati)
    # Gli artefatti restano dove sono: l'undo non li cancella.
    assert corsa.exists()


def test_uno_sweep_non_lascia_nulla_nello_storico(cliente, tmp_path):
    """Lo storico e' dei gesti di una persona, e i gesti di una persona passano
    dal server. core.config.save_config la chiamano anche pipeline e sweep:
    agganciato li', uno sweep depositerebbe una versione per ogni candidato e
    lo storico dell'utente affogherebbe nel proprio rumore.
    """
    cfg = load_config(tmp_path / "config.yaml")
    for profondita in (6, 7, 8):
        cfg.surface.poisson_depth = profondita
        save_config(cfg, tmp_path / "config.yaml")
    assert not (Path(cfg.run.out_dir) / ".storico").exists()


def test_il_core_non_conosce_lo_storico():
    """La stessa regola guardata dalla mossa e non dal sintomo: il giorno che
    un import comparisse dentro core/, il test qui sopra resterebbe verde
    finche' qualcuno non chiama proprio quella strada."""
    from meshrec.core import config as modulo_config

    for modulo in (modulo_config,):
        sorgente = Path(modulo.__file__).read_text(encoding="utf-8")
        assert "storico" not in sorgente, f"{modulo.__name__} conosce lo storico"
```

`load_config` va aggiunta all'import in cima a `tests/test_server.py`:

```python
from meshrec.core.config import InputConfig, PipelineConfig, load_config, save_config
```

La firma di `steps.write_state` è `(out_dir, numero, impronta, esito, artefatto, secondi)`, sei argomenti posizionali senza predefiniti (`core/steps.py:91-98`); `"riuscito"` è il valore che `pipeline.registra` scrive (`core/pipeline.py:115-118`), e `run_state` tratta come fallito soltanto `"fallito"`.

Poi sostituire `test_nessun_endpoint_solleva_verso_il_browser` (`tests/test_server.py:1777`):

```python
def test_nessun_endpoint_solleva_verso_il_browser(cliente):
    """Il contratto vale sull'elenco intero, derivato dall'applicazione stessa:
    un endpoint aggiunto domani vi entra da solo e non puo' essere dimenticato.

    Anche i POST, da quando lo storico ne ha aggiunti due che non hanno corpo:
    limitato ai GET, l'elenco avrebbe smesso di essere «intero» proprio nel
    momento in cui e' cresciuto. Un POST senza corpo dove il corpo serve
    risponde 422, che e' un rifiuto spiegato e non un sollevamento.
    """
    chiamate = [
        (metodo, rotta.path)
        for rotta in cliente.app.routes
        for metodo in (getattr(rotta, "methods", None) or set())
        if metodo in {"GET", "POST"}
    ]
    assert len(chiamate) >= 3
    for metodo, percorso in chiamate:
        if "{" in percorso or percorso in STREAMING:
            continue
        risposta = cliente.request(metodo, percorso)
        assert risposta.status_code < 500, f"{metodo} {percorso} ha sollevato verso il browser"
```

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_server.py -k "storico or indietro or avanti or sweep_non_lascia or solleva_verso" -v`
Expected: FAIL con 404 sui due endpoint nuovi (`assert 404 == 200`).

- [ ] **Step 3: Scrivere il punto d'innesto unico**

In `meshrec/src/meshrec/app/server.py`, aggiungere all'import dei moduli dell'applicazione:

```python
from meshrec.app import storico
```

Dentro `create_app`, subito dopo `def corrente() -> PipelineConfig:` (`:266-267`):

```python
    def scrivi_config(nuova: PipelineConfig, endpoint: str, campi: list[str]) -> None:
        """L'unico punto del server che scrive config.yaml.

        core.config.save_config non si tocca: la chiamano anche pipeline e
        sweep, e agganciare lo storico li' depositerebbe una versione per ogni
        candidato di uno sweep. Il punto condiviso giusto e' il server, non il
        core: e' il server a servire i gesti di una persona, ed e' dei gesti di
        una persona che si tiene lo storico.
        """
        out_dir = Path(nuova.run.out_dir)
        # La versione di partenza, depositata pigramente alla prima modifica:
        # senza, il primo «indietro» non avrebbe niente a cui tornare e la prima
        # modifica sarebbe l'unica non annullabile. Pigra e non all'avvio
        # perche' aprire l'interfaccia senza toccare niente non e' un gesto da
        # registrare.
        if not storico.esiste(out_dir):
            storico.deposita(out_dir, config_path.read_text(encoding="utf-8"), "avvio", [])
        save_config(nuova, config_path)
        storico.deposita(out_dir, config_path.read_text(encoding="utf-8"), endpoint, campi)
```

Sostituire le tre chiamate dirette:

`:307` in `scrivi_configurazione`:
```python
        scrivi_config(nuova, "PUT /api/config", sorted(nuova.model_dump(mode="json")))
```

`:464` in `ritaglia` (dopo `_dentro, metriche = segment.crop_box(...)`):
```python
        scrivi_config(cfg, "POST /api/crop", ["segment.crop_min", "segment.crop_max"])
```

`:616` in `scegli_cluster`:
```python
        scrivi_config(cfg, "POST /api/cluster", ["segment.method", "segment.cluster_index"])
```

- [ ] **Step 4: Scrivere i due endpoint**

Dentro `create_app`, accanto agli altri endpoint della configurazione:

```python
    def _ripristina(testo: str | None, vuoto: str) -> dict[str, object]:
        if testo is None:
            return {"annullato": False, "perche": vuoto}
        cfg_prima = corrente()
        prima = {
            int(voce["numero"]): voce["stato"]
            for voce in steps.run_state(cfg_prima.run.out_dir, cfg_prima)
        }
        # Il testo si riscrive tale e quale, senza ripassare dal modello: la
        # versione depositata e' gia' per costruzione rileggibile (l'ha scritta
        # save_config), e ripassarci la normalizzerebbe, cioe' l'undo
        # restituirebbe un file diverso da quello che ha tolto.
        io.scrivi_atomico(
            config_path,
            lambda destinazione: destinazione.write_text(testo, encoding="utf-8"),
        )
        cfg_dopo = corrente()
        dopo = steps.run_state(cfg_dopo.run.out_dir, cfg_dopo)
        # Gli artefatti restano sul disco: la catena di impronte li marca «non
        # valido» da se', e questa fase eredita quel meccanismo invece di
        # duplicarlo. Ma dirlo e' obbligatorio: un ritorno indietro che cambia
        # in silenzio lo stato di sette step e' una modifica invisibile.
        invalidati = [
            int(voce["numero"])
            for voce in dopo
            if voce["stato"] == "non valido" and prima.get(int(voce["numero"])) != "non valido"
        ]
        return {"annullato": True, "invalidati": invalidati, "steps": dopo}

    @app.post("/api/storico/indietro")
    def storico_indietro() -> dict[str, object]:
        """Rimette la versione precedente della configurazione.

        Non tace mai: a storico vuoto risponde con il proprio «perche'», perche'
        un silenzio identico fra riuscita e nulla-da-fare e' gia' stato prodotto
        e corretto una volta su questo progetto (il bottone Annulla).
        """
        return _ripristina(
            storico.indietro(Path(corrente().run.out_dir)), "niente da annullare"
        )

    @app.post("/api/storico/avanti")
    def storico_avanti() -> dict[str, object]:
        return _ripristina(
            storico.avanti(Path(corrente().run.out_dir)), "niente da rifare"
        )
```

Verificare che `io` e `steps` siano già importati in `app/server.py` (lo sono: `steps.run_state` è usata a `:299`); aggiungere `from meshrec.core import io` se manca.

- [ ] **Step 5: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_server.py -q`
Expected: PASS.

- [ ] **Step 6: Eseguire la suite intera**

Run: `cd meshrec && uv run pytest -q`
Expected: nessun fallimento. Se `test_nessun_endpoint_solleva_verso_il_browser` esteso ai POST accende un endpoint che risponde 500, quello è un difetto vero e va corretto qui, non aggirato restringendo di nuovo l'elenco.

- [ ] **Step 7: Commit**

```bash
git add meshrec/src/meshrec/app/server.py meshrec/tests/test_server.py
git commit -m "feat(server): indietro e avanti sulle modifiche di configurazione"
```

---

### Task 8: Ctrl+Z nel browser

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js` (funzione nuova e un gestore globale)
- Modify: `meshrec/tests/test_app_js.py`

**Interfaces:**
- Consumes: `POST /api/storico/indietro` e `/avanti` dal Task 7; `corpoLetto(risposta)` (`app.js:449`), `ragioneDelRifiuto(risposta)` (`:405`), `caricaStato()` (`:11`), `ricaricaVista`, `apriDettaglio`, `rigaErrore`.
- Produces: niente per task successivi. È l'ultimo.

- [ ] **Step 1: Scrivere i test**

Aggiungere in coda a `meshrec/tests/test_app_js.py`:

```python
def test_ctrl_z_e_legato_e_non_ruba_i_comandi_della_tela():
    """Criterio 11 della spec. Gli unici tasti globali che questa fase aggiunge:
    i comandi della tela (frecce, +, -, f, maiusc) restano legati al canvas col
    fuoco sopra, e un gestore globale sulle frecce li rubere*bbe a chi orbita
    da tastiera."""
    modulo = _senza_commenti_js(_modulo())
    assert 'document.addEventListener("keydown"' in modulo, "nessun tasto globale legato"
    trovato = re.search(
        r'document\.addEventListener\("keydown".*?\n\}\);', modulo, flags=re.DOTALL
    )
    assert trovato is not None
    corpo = trovato.group(0)
    assert "ctrlKey" in corpo and "metaKey" in corpo, (
        "su macOS l'annullamento e' cmd+z: legato al solo ctrlKey non risponde"
    )
    for tasto in ("ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", '"+"', '"-"'):
        assert tasto not in corpo, f"il gestore globale intercetta {tasto}, che e' della tela"


def test_lo_storico_a_vuoto_mostra_il_perche_invece_di_tacere(tmp_path):
    """Il server risponde {"annullato": false, "perche": ...} e il modulo lo
    deve dire. Scartare quel corpo e' esattamente il difetto del bottone
    Annulla, per una seconda strada."""
    _esegui(tmp_path, _DOM + """
globalThis.fetch = async () => ({
  ok: true,
  status: 200,
  text: async () => JSON.stringify({ annullato: false, perche: "niente da annullare" }),
});
async function caricaStato() {}
function ricaricaVista() {}
async function apriDettaglio() {}
function apriGenerazione() { return 1; }
let stepMostrato = null;
""" + _funzioni("corpoLetto", "ragioneDelRifiuto", "chiediStorico") + """
await chiediStorico("indietro");
assert.equal(rigaErrore.textContent, "niente da annullare");
""")


def test_dopo_un_ritorno_indietro_l_interfaccia_elenca_gli_step_invalidati(tmp_path):
    """Gli artefatti restano sul disco e la catena di impronte li marca «non
    valido»: e' il comportamento giusto, ma cambiare in silenzio lo stato di
    sette step sarebbe una modifica invisibile."""
    _esegui(tmp_path, _DOM + """
let ricaricata = false;
globalThis.fetch = async () => ({
  ok: true,
  status: 200,
  text: async () => JSON.stringify({ annullato: true, invalidati: [5, 6, 7], steps: [] }),
});
async function caricaStato() {}
function ricaricaVista() { ricaricata = true; }
async function apriDettaglio() {}
function apriGenerazione() { return 1; }
let stepMostrato = 5;
""" + _funzioni("corpoLetto", "ragioneDelRifiuto", "chiediStorico") + """
await chiediStorico("indietro");
assert.match(rigaErrore.textContent, /5, 6, 7/);
assert.match(rigaErrore.textContent, /non valid/);
// La vista si rifa': il config e' cambiato sotto, e lasciare a schermo la
// geometria di prima con lo stato nuovo a sinistra e' la vista che contraddice
// la propria didascalia, per la terza strada.
assert.equal(ricaricata, true);
""")
```

Nota per chi esegue: `_DOM` (`tests/test_app_js.py:115-193`) dichiara già `rigaErrore`, `stepAperto`, `configurazione`, `generazione` ed `ETICHETTE`. Non dichiara `stepMostrato`, `apriGenerazione`, `caricaStato`, `ricaricaVista` né `apriDettaglio`: sono quelli che le prove qui sopra aggiungono, e non c'è ridichiarazione. `_sorgente_di` tiene il prefisso `async`, quindi `chiediStorico` esce eseguibile e il `await` di primo livello è lecito in un modulo `.mjs`.

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `cd meshrec && uv run pytest tests/test_app_js.py -k "ctrl_z or storico_a_vuoto or invalidati" -v`
Expected: FAIL con `nessun tasto globale legato` e `il modulo non ha una funzione chiediStorico`.

- [ ] **Step 3: Scrivere la funzione e il gestore**

In `meshrec/src/meshrec/ui/app.js`, dopo `ricaricaVista`:

```js
// Il ritorno indietro sulle modifiche di configurazione. «Annullamento», in
// tutti i documenti di questa interfaccia, ha sempre significato la
// terminazione dello step che sta girando (il bottone #annulla): questa e'
// un'altra cosa e sta apposta su un'altra strada.
async function chiediStorico(verso) {
  const risposta = await fetch(`/api/storico/${verso}`, { method: "POST" });
  if (!risposta.ok) {
    rigaErrore.textContent = await ragioneDelRifiuto(risposta);
    return;
  }
  const corpo = await corpoLetto(risposta);
  // Il corpo si legge anche quando la risposta e' riuscita: scartarlo qui
  // renderebbe il silenzio di «non c'era niente da annullare» identico a
  // quello di un annullamento riuscito, che e' il difetto gia' prodotto e
  // corretto una volta sul bottone Annulla.
  if (!corpo.annullato) {
    rigaErrore.textContent = corpo.perche;
    return;
  }
  // Gli artefatti restano sul disco: la catena di impronte li marca «non
  // valido» da se'. Dirlo e' il punto — un ritorno indietro che cambia in
  // silenzio lo stato di sette step sarebbe una modifica invisibile.
  // ponytail: il messaggio esce dalla regione role="alert", che e' l'unica
  // regione viva dell'interfaccia. Una regione neutra separata si aggiunge il
  // giorno che ci sia un secondo messaggio non d'errore da dare.
  rigaErrore.textContent = corpo.invalidati.length
    ? `configurazione ripristinata: gli step ${corpo.invalidati.join(", ")} sono ora «non validi»`
    : "configurazione ripristinata: nessuno step cambia stato";
  await caricaStato();
  const ordine = apriGenerazione();
  if (stepMostrato !== null) ricaricaVista(stepMostrato, ordine);
  if (stepAperto !== null) apriDettaglio(stepAperto, ordine);
}

// Gli unici tasti globali dell'interfaccia. I comandi della tela — frecce, +,
// -, f, maiusc — restano legati al canvas col fuoco sopra, quindi qui non si
// intercetta nient'altro che z: un gestore globale sulle frecce le
// rubere'bbe a chi orbita da tastiera.
// metaKey oltre a ctrlKey: su macOS l'annullamento e' cmd+z, e questo progetto
// e' su macOS dal 16/08/2026.
document.addEventListener("keydown", (evento) => {
  if (!(evento.ctrlKey || evento.metaKey)) return;
  if (evento.key.toLowerCase() !== "z") return;
  evento.preventDefault();
  chiediStorico(evento.shiftKey ? "avanti" : "indietro");
});
```

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `cd meshrec && uv run pytest tests/test_app_js.py -q`
Expected: PASS.

- [ ] **Step 5: Eseguire la suite intera**

Run: `cd meshrec && uv run pytest -q`
Expected: PASS. I 6 deselezionati restano deselezionati.

- [ ] **Step 6: Commit**

```bash
git add meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "feat(interfaccia): ctrl+z sulle modifiche di configurazione"
```

---

## Verifica finale, a mano, nel browser

I test coprono la logica; nessuno di loro apre una finestra. Questi undici criteri sono la spec (§ 11) e vanno guardati a video prima di dichiarare chiusa la fase, con `uv run meshrec serve` e il config di lavoro `meshrec/prova-interfaccia.yaml` sulla corsa `lab_crop`.

- [ ] **Verifica 1.** Passando dallo step 3 al 4 la camera resta dove l'utente l'aveva messa.
- [ ] **Verifica 2.** Cambiando corsa (da `muro` a `lab_crop`) la camera si reinquadra da sola e la geometria è visibile.
- [ ] **Verifica 3.** Gli step 7, 10 e 11 mostrano una geometria e dichiarano di quale step è.
- [ ] **Verifica 4.** Lo step 8 con `simplify.enabled: false` mostra la superficie dello step 6 e lo dichiara.
- [ ] **Verifica 5.** Sullo step 2 il fantasma mostra la nuvola dello step 1: dichiara 6.329.096 punti pieni, mentre la geometria corrente ne dichiara 4.229.538. Sono i valori di `runs/lab_crop/metrics.json`, `01_load.points_kept` e `02_segment.points_after`.
- [ ] **Verifica 6.** Accanto ai conteggi compare il passo del voxel di disegno, e sullo step 3 (116.059 punti, sotto il budget) non compare, perché lì non c'è decimazione.
- [ ] **Verifica 7.** Maiusc più trascinamento trasla la vista; «Inquadra» e il tasto `f` la riportano sull'ingombro.
- [ ] **Verifica 8.** Una modifica di parametro seguita da Ctrl+Z rimette il `config.yaml` precedente, e l'interfaccia elenca gli step tornati «non validi».
- [ ] **Verifica 9.** Ctrl+Z a storico vuoto dice che non c'è nulla da annullare.
- [ ] **Verifica 10.** Uno sweep di Fase 2 non lascia nulla in `runs/<nome>/.storico/`. Da eseguire su una corsa di prova, **mai** su `lab_crop` o `muro`.
- [ ] **Verifica 11.** La suite passa: i test attuali più quelli nuovi, con i 6 deselezionati che restano tali.

## Chiusura del ramo

- [ ] Aprire la PR verso `main` (`git push -u origin worktree-fase-3-5-viewport` è già stato fatto per la spec).
- [ ] Prima del merge, dispacciare in **parallelo** `security-reviewer`, `code-reviewer`, `test-writer` — sono di sola lettura e indipendenti fra loro.
- [ ] Merge solo con review pulita, poi `superpowers:finishing-a-development-branch`.
- [ ] Aggiungere al debito già aperto nella spec (§ 10.1) le voci nuove che questo piano lascia: la regione `role="alert"` usata anche per messaggi non d'errore (Task 8), e il banco `node` ricopiato in due file di test invece che in un `conftest.py` (Task 1).
- [ ] `graphify update` **non** serve: `Tesi/` non è fra i cinque grafi vivi.
