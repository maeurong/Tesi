# Chiusura dei rilievi della critica — giro 3

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chiudere i due P0 e i tre P1 della critica del 16/08/2026 sull'interfaccia MeshRec, piu' la divulgazione progressiva scelta dall'utente e la passata di rifinitura.

**Architecture:** Nessuna dipendenza nuova e nessun passo di build. Si lavora sui quattro file dell'interfaccia gia' esistenti (`index.html`, `stile.css`, `app.js`, `viewport.js`) piu' due punti del server. Il filo conduttore e' uno solo: **tre informazioni che il prodotto gia' possiede e gia' manda al browser — `exit_code`, `secondi`, `default` — non vengono lette.** La maggior parte delle task le legge invece di disegnare qualcosa di nuovo. Ogni logica nuova viene estratta in una funzione pura di primo livello, perche' e' l'unica forma che il banco di `tests/test_app_js.py` sa eseguire.

**Tech Stack:** Python 3.12 + FastAPI + pydantic lato server; JavaScript a moduli ES senza framework e senza toolchain lato browser; three.js vendorizzato; pytest, con un banco che esegue le funzioni vere di `app.js` su un DOM finto tramite `node`.

**Spec:** `.impeccable/critique/2026-08-16T11-21-22Z__meshrec-src-meshrec-ui-index-html.md`

## Global Constraints

Ogni task eredita implicitamente questa sezione.

- **Lingua dell'interfaccia: italiano.** Etichette, messaggi ed errori si scrivono in italiano.
- **Identificatori tecnici invariati, alla lettera:** `C3D4`, `C3D10`, `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`, `ALL_WALL`, `min_ratio`, `nobisect`, Poisson, TetGen, MeshFix, fronte di Pareto. Anche i nomi dei campi di configurazione (`crop_min`, `voxel_size`, `on_front`, …) sono identificatori.
- **Non fabbricare precisione che non esiste.** Nessuna percentuale d'avanzamento inventata, nessun numero mostrato che una misura non sostenga. Dove il dato manca, si dichiara che manca.
- **Un numero mostrato senza un controllo che lo smentisca non vale piu' di un numero assente.** Ogni logica nuova di questo piano lascia dietro di se' un test che fallisce se la logica si rompe.
- **Un parametro ha il proprio valore predefinito in un solo file:** `meshrec/src/meshrec/core/config.py`. Nessun predefinito si duplica nel browser.
- **Sorgenti in ASCII, con una sola eccezione dichiarata:** le stringhe **mostrate all'utente** portano gli accenti italiani veri (Task 5). I commenti, i nomi e il resto del codice restano ASCII come nel resto del repository.
- **Nessuna dipendenza nuova**, ne' Python ne' JavaScript. Nessun passo di build per l'interfaccia.
- **Voce del progetto:** registro asciutto e misurato. Si afferma cio' che e' stato verificato, si dichiara cio' che non lo e', e un esito negativo documentato non si confonde mai con un fallimento.
- **Comando dei test, da eseguire dalla cartella `meshrec/`:** `uv run pytest tests/test_app_js.py -q` (verificato funzionante: `uv run pytest tests/test_stile.py -q` → 3 passed in 1.69s).
- **Branch:** si lavora su `fase-3-interfaccia`, che e' il branch corrente. Un commit per task.

---

## File Structure

Nessun file nuovo di produzione. Il piano modifica sei file esistenti e ne estende tre di test.

| File | Responsabilita' | Task che lo toccano |
|---|---|---|
| `meshrec/src/meshrec/ui/index.html` | Lo scheletro statico e le regioni che devono preesistere a cio' che annunciano | 1, 4, 7 |
| `meshrec/src/meshrec/ui/stile.css` | Il sistema visivo: token, stati, movimento | 4, 5, 6, 7 |
| `meshrec/src/meshrec/ui/app.js` | Orchestrazione: flusso degli eventi, viewport, pannello, galleria | 1, 2, 3, 4, 5, 6, 7 |
| `meshrec/src/meshrec/app/server.py` | Le tratte HTTP | 8 |
| `meshrec/README.md` | Come si avvia il programma | 8 |
| `PRODUCT.md` | Il contesto di prodotto | 8 |
| `meshrec/tests/test_app_js.py` | Il banco dell'interfaccia: funzioni vere su DOM finto | 1, 2, 3, 4, 5, 6 |
| `meshrec/tests/test_stile.py` | Sorveglianza testuale del foglio di stile | 7 |
| `meshrec/tests/test_server.py` | Le tratte | 8 |

**Perche' `app.js` non si spezza in piu' file.** E' a 1056 righe e cresce di ~150 con questo piano. Spezzarlo vorrebbe dire introdurre moduli ES aggiuntivi serviti da `/ui/`, cioe' altre tratte statiche e un ordine di caricamento nuovo, per un file che una persona sola legge per intero. Il progetto non ha una convenzione di moduli multipli per l'interfaccia e questo piano non e' il posto per inventarla. Le funzioni nuove restano di primo livello, che e' il vincolo che conta davvero: e' l'unica forma che `_sorgente_di()` sa estrarre e che il banco sa eseguire.

### Il banco di `tests/test_app_js.py`, in breve

Le task 1–6 aggiungono test a questo file. Chi le esegue deve conoscerne tre attrezzi, gia' presenti in cima al file:

- `_funzioni("nome1", "nome2")` — torna il **sorgente** delle funzioni di primo livello con quei nomi, estratto da `app.js`. Si appoggia a `_sorgente_di()`, che taglia dalla firma alla prima graffa in **prima colonna**. Conseguenze vincolanti per il codice nuovo: la funzione deve essere di primo livello, e nessuna riga del suo corpo puo' essere una graffa a colonna zero.
- `_DOM` — una stringa che dichiara un DOM finto minimo (`Elemento`, `document`, `radice`, `perId`) piu' alcune variabili di modulo (`ETICHETTE`, `rigaErrore`, `stepAperto`, `configurazione`, `generazione`, `elenco`, `STEPS`, `marcati`). Non e' un browser: e' il minimo che le funzioni vere toccano.
- `_esegui(tmp_path, sorgente)` — scrive il sorgente in `prova.mjs`, lo esegue con `node`, e **asserisce che il codice d'uscita sia 0**. Il rosso e' un `assert` di `node:assert/strict` che salta dentro il modulo di prova; il suo messaggio arriva nel messaggio di fallimento di pytest.

Il modulo di prova si compone cosi': `_DOM + eventuali stub + _funzioni(...) + il corpo del controllo`.

**Nota su `ETICHETTE`:** `_DOM` la dichiara `const ETICHETTE = {}`. Non si puo' ridichiarare, ma si puo' **mutare**: `ETICHETTE["09_tetrahedralize"] = "Tetraedri";` e' il modo di darle contenuto in un test.

---

## Task 1: La fine di una corsa viene annunciata

Chiude il **P0** «Una corsa fallita o annullata non e' annunciata da niente». `server.py` manda `exit_code` e `annullato` in ogni frame `stato` (righe 673–679) e `run_state` mette `secondi` in ogni voce di step (`core/steps.py:150`). `app.js` non legge nessuno dei tre.

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:10-20` (testata)
- Modify: `meshrec/src/meshrec/ui/stile.css` (una regola nuova, accanto a `.in-corso`)
- Modify: `meshrec/src/meshrec/ui/app.js:3-9` (dopo `ETICHETTE`), `:107-141` (gestore `stato`)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: niente da task precedenti.
- Produces:
  - `nomeDelloStep(numero, steps = [])` → `string`. Il nome leggibile di uno step dal suo numero, usando `ETICHETTE` e la `chiave` che `run_state` mette in ogni voce. Ripiega su `` `step ${numero}` `` quando la voce non c'e'. **La Task 2 e la Task 5 la consumano.**
  - `esitoDellaCorsa(stato)` → `{ errore: string|null, esito: string|null }`. Pura. `errore` e' il testo per la regione `role="alert"`, `esito` quello per la riga neutra.
  - Elemento `#esito` nel markup, con `aria-live="polite"`.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# La fine di una corsa: exit_code e secondi arrivano e vanno detti.
# --------------------------------------------------------------------------


def test_la_riga_dell_esito_esiste_nel_markup_ed_e_una_regione_viva():
    """Come la regione role="alert": deve preesistere a cio' che annuncia.
    Creata nell'istante in cui ci si scrive dentro, l'annuncio non e'
    garantito."""
    elemento = _elemento(_senza_commenti_html(_markup()), "esito")
    assert 'aria-live="polite"' in elemento, f"la riga dell'esito non e' viva: {elemento}"
    assert "hidden" not in elemento, f"hidden la toglie dall'albero: {elemento}"


def test_la_fine_della_corsa_distingue_fallito_annullato_e_concluso(tmp_path):
    """Il rilievo peggiore del giro 3. `exit_code` e `annullato` sono nel carico
    SSE da quando esiste il worker, e il modulo leggeva solo `in_corso`: a uscita
    non nulla la riga che pulsa spariva e basta, e chi guardava non poteva
    distinguere «fallito» da «finito».

    Tre esiti, tre frasi diverse, e nessuna delle tre inventa un numero.
    """
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
const steps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido", secondi: 34.39 }];
""" + _funzioni("nomeDelloStep", "esitoDellaCorsa") + """
const rotto = esitoDellaCorsa({ step: 9, exit_code: 1, annullato: false, steps });
assert.equal(rotto.esito, null, "un fallimento non e' un esito neutro");
assert.match(rotto.errore, /Tetraedri/, "il nome dello step, non il suo numero");
assert.match(rotto.errore, /codice 1/, "il codice d'uscita e' l'unico indizio che il server manda");
assert.match(rotto.errore, /registro/, "senza un rimando, il motivo resta introvabile");

const fermo = esitoDellaCorsa({ step: 9, exit_code: -15, annullato: true, steps });
assert.equal(fermo.errore, null, "annullare e' una scelta dell'utente, non un guasto");
assert.match(fermo.esito, /annullat/, "e va detto");

const bene = esitoDellaCorsa({ step: 9, exit_code: 0, annullato: false, steps });
assert.equal(bene.errore, null);
assert.match(bene.esito, /34[.,]39/, "la durata misurata, che run_state gia' porta");

console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_una_corsa_conclusa_senza_durata_non_ne_inventa_una(tmp_path):
    """Principio 3. `secondi` viene dal file di stato e puo' mancare: una corsa
    conclusa senza misura si dichiara conclusa e nient'altro. Uno zero, o un
    trattino formattato come un numero, sarebbe una precisione fabbricata."""
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
const steps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido" }];
""" + _funzioni("nomeDelloStep", "esitoDellaCorsa") + """
const senza = esitoDellaCorsa({ step: 9, exit_code: 0, annullato: false, steps });
assert.equal(senza.esito, "Tetraedri concluso", `ha inventato una durata: ${senza.esito}`);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

Da `meshrec/`:

```bash
uv run pytest tests/test_app_js.py -q -k "esito or fine_della_corsa or senza_durata"
```

Atteso: FAIL. Il primo con `AssertionError: nessun elemento con id=esito nel markup`; gli altri due con un `IndexError` da `_sorgente_di` (la funzione non esiste ancora in `app.js`).

- [ ] **Step 3: Aggiungere la riga dell'esito al markup**

In `meshrec/src/meshrec/ui/index.html`, dentro `<header class="testata">`, subito dopo `<p class="in-corso" id="in-corso" hidden></p>`:

```html
  <!-- La riga dell'esito. Regione viva e senza hidden, per la stessa ragione
       della riga d'errore: una regione creata nell'istante in cui ci si scrive
       dentro non garantisce l'annuncio. Vuota non occupa spazio (.esito:empty
       in stile.css). Separata da #in-corso e non la stessa riga riusata: quella
       porta il pallino che pulsa, e un lavoro finito che continua a pulsare
       direbbe il contrario di cio' che e' successo. -->
  <p class="esito" id="esito" aria-live="polite"></p>
```

- [ ] **Step 4: Aggiungere la regola di stile**

In `meshrec/src/meshrec/ui/stile.css`, subito dopo la regola `.in-corso`:

```css
/* L'esito di una corsa finita. Colore del testo normale e non dell'accento: e'
   un fatto, non uno stato attivo, e a corsa ferma non c'e' niente da segnalare.
   Cifre tabulari perche' ci finisce dentro una durata misurata. */
.esito { margin: 0; font-size: var(--tipo-dato); line-height: var(--interlinea-riga); font-variant-numeric: tabular-nums; color: var(--tenue); }
.esito:empty { margin: 0; }
```

- [ ] **Step 5: Scrivere le due funzioni in `app.js`**

In `meshrec/src/meshrec/ui/app.js`, subito dopo la costante `ETICHETTE` (dopo la riga 9):

```js
// Il nome leggibile di uno step. La colonna di sinistra mostra i nomi, e la
// riga di stato diceva «step 9»: due lingue per la stessa cosa, e la traduzione
// a carico di chi guarda. La chiave sta in ogni voce di run_state, quindi il
// nome non va indovinato dall'ordine.
function nomeDelloStep(numero, steps = []) {
  const voce = steps.find((v) => v.numero === numero);
  const etichetta = voce ? ETICHETTE[voce.chiave] : undefined;
  return etichetta ?? `step ${numero}`;
}

// Che cosa dire quando una corsa finisce. Pura e di primo livello come
// superata() e valoreScritto(): e' la decisione che l'interfaccia non prendeva
// affatto, e presa dentro un gestore anonimo non la esegue nessun banco.
// I tre esiti sono distinti perche' sono tre fatti diversi, ed e' la voce del
// progetto: un annullamento e' una scelta di chi guarda, non un guasto.
// L'ordine dei rami conta: un annullamento arriva con un codice d'uscita non
// nullo (il segnale che lo ha fermato), quindi va guardato per primo, altrimenti
// ogni annullamento si annuncerebbe come un fallimento.
function esitoDellaCorsa(stato) {
  const nome = nomeDelloStep(stato.step, stato.steps ?? []);
  if (stato.annullato) return { errore: null, esito: `${nome} annullato` };
  if (stato.exit_code !== 0 && stato.exit_code !== null && stato.exit_code !== undefined) {
    return {
      errore: `${nome} e' fallito (codice ${stato.exit_code}). ` +
        "Il motivo e' nelle ultime righe del registro, qui sotto.",
      esito: null,
    };
  }
  // La durata la misura il server e la scrive nel file di stato: run_state la
  // rilegge da li'. Quando manca non si mette uno zero ne' un trattino formattato
  // come un numero — sarebbe una misura fabbricata — si dice solo che e' finito.
  const voce = (stato.steps ?? []).find((v) => v.numero === stato.step);
  const secondi = voce ? voce.secondi : undefined;
  if (typeof secondi !== "number") return { errore: null, esito: `${nome} concluso` };
  const misura = secondi.toLocaleString("it", { maximumFractionDigits: 2 });
  return { errore: null, esito: `${nome} concluso in ${misura} s` };
}
```

- [ ] **Step 6: Collegarle al flusso degli eventi**

In `meshrec/src/meshrec/ui/app.js`, dentro `flusso.addEventListener("stato", ...)`, sostituire il blocco del fronte di discesa (attuali righe 128–139) con:

```js
  const rigaEsito = document.getElementById("esito");
  // Sul fronte di salita si pulisce: l'esito della corsa precedente, lasciato
  // li', descriverebbe un lavoro diverso da quello che sta girando adesso.
  if (!eraInCorso && stato.in_corso) rigaEsito.textContent = "";
  if (eraInCorso && !stato.in_corso) {
    const { errore, esito } = esitoDellaCorsa(stato);
    // dichiaraErrore(null) su un esito buono e' voluto: un errore di prima
    // lasciato a video contraddirebbe la corsa che si e' appena conclusa bene.
    dichiaraErrore(errore);
    rigaEsito.textContent = esito ?? "";
    if (stepAperto !== null) apriDettaglio(stepAperto);
    // La vista quanto il pannello: senza questa riga lo step rieseguito mostra
    // a destra le metriche nuove e nel viewport il contorno vecchio, col
    // cursore del taglio tarato su un ingombro che non esiste piu'.
    // Una corsa partita dallo step N riscrive gli artefatti dall'N in giu',
    // quindi solo un numero >= N puo' essere scaduto: sotto non c'e' niente da
    // ricaricare, e ogni ricaricamento e' una richiesta in piu'.
    if (stepMostrato !== null && stato.step !== null && stepMostrato >= stato.step) {
      ricaricaVista(stepMostrato);
    }
  }
```

- [ ] **Step 7: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py -q
```

Atteso: PASS su tutto il file, compresi i controlli preesistenti.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "fix(ui): la fine di una corsa si annuncia, e la durata e' quella misurata

exit_code e annullato erano nel carico SSE da sempre e nessuno li leggeva: a
uscita non nulla la riga che pulsa spariva e basta, senza distinguere un
fallimento da un lavoro finito. Adesso i tre esiti sono tre frasi diverse, e
quando la durata manca non se ne inventa una."
```

---

## Task 2: La vista dichiara che sta caricando

Chiude il **P0** «Nessuno stato di caricamento, e la vista afferma un accoppiamento falso mentre carica». Su `lab_frame.pcd` la lettura di un artefatto costa 27–34 s a freddo, e in quella finestra tela, conteggi e pannello descrivono due step diversi.

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:67-92` (`disegnaStep`), `:214-280` (`mostraNuvolaDelloStep`, `mostraStep`), `:831-832` (le due fetch in fila)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: `nomeDelloStep(numero, steps)` dalla Task 1.
- Produces: `dichiaraCaricamento(numero)` — svuota la vista, scrive la didascalia di attesa e marca `aria-busy` sul viewport. Nessuna task successiva la consuma.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# L'attesa della geometria: mezzo minuto in cui la vista mentiva.
# --------------------------------------------------------------------------


def test_la_vista_si_svuota_e_si_dichiara_prima_di_aspettare(tmp_path):
    """La finestra dei 27-34 secondi era l'unico punto in cui la vista e la sua
    didascalia potevano descrivere due step diversi: tela e conteggi restavano
    sullo step precedente mentre il pannello mostrava gia' il nuovo.

    Non e' una percentuale fabbricata: e' il nome di cio' che si sta leggendo.
    """
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
let svuotate = 0;
const vista = { svuota() { svuotate += 1; } };
let ultimiSteps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido" }];
""" + _funzioni("nomeDelloStep", "dichiaraCaricamento") + """
dichiaraCaricamento(9);
assert.equal(svuotate, 1, "la geometria di prima e' rimasta a video");
const didascalia = document.getElementById("conteggi").textContent;
assert.match(didascalia, /Tetraedri/, `la didascalia non nomina lo step: ${didascalia}`);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), "true",
  "chi non vede la tela non sa che sta arrivando qualcosa",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_la_dichiarazione_precede_l_attesa_e_non_la_segue():
    """Il controllo di comportamento qui sopra passerebbe anche con la
    dichiarazione scritta dopo il `fetch`, che e' esattamente il difetto: una
    didascalia d'attesa che compare quando l'attesa e' finita non ha aspettato
    niente. Questo guarda l'ordine nel sorgente, come i controlli della regola
    delle generazioni.
    """
    corpo = _sorgente_di("mostraStep", _modulo())
    assert "dichiaraCaricamento(" in corpo, "mostraStep non dichiara piu' l'attesa"
    assert corpo.index("dichiaraCaricamento(") < corpo.index("await fetch"), (
        "la dichiarazione e' finita dopo l'attesa: comparirebbe quando non serve piu'"
    )


def test_la_configurazione_e_le_metriche_si_chiedono_insieme():
    """Erano due andate e ritorni in fila per due letture indipendenti: il
    pannello aspettava la somma di due latenze invece della maggiore."""
    corpo = _sorgente_di("apriDettaglio", _modulo())
    assert "Promise.all" in corpo, "le due letture sono tornate in fila"
    assert corpo.count("await fetch(\"/api/config\")") == 0, (
        "e' rimasta un'attesa separata su /api/config"
    )
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_app_js.py -q -k "caricamento or precede_l_attesa or chiedono_insieme"
```

Atteso: FAIL. Il primo con `IndexError` da `_sorgente_di` (`dichiaraCaricamento` non esiste), gli altri due con `AssertionError`.

- [ ] **Step 3: Rendere disponibili i nomi degli step al modulo**

In `meshrec/src/meshrec/ui/app.js`, dichiarare la variabile subito dopo `ETICHETTE` e le funzioni della Task 1:

```js
// L'ultimo elenco di step arrivato dal server. Serve ai nomi: la didascalia
// d'attesa nomina lo step che sta caricando, e il nome sta nella chiave che
// run_state porta in ogni voce.
let ultimiSteps = [];
```

e assegnarla in testa a `disegnaStep`, come prima riga del corpo (prima di `const elenco = ...`):

```js
  ultimiSteps = steps;
```

- [ ] **Step 4: Scrivere `dichiaraCaricamento`**

In `meshrec/src/meshrec/ui/app.js`, subito prima di `async function mostraNuvolaDelloStep(`:

```js
// Prima dell'attesa, non dopo. La lettura di un artefatto costa 27-34 secondi a
// freddo sulla scansione vera, e in quella finestra la tela mostrava la
// geometria dello step precedente, i conteggi i suoi numeri, e il pannello con
// aria-current gia' il nuovo: lo schermo affermava che i parametri di uno step
// vanno con la mesh di un altro. E' la stessa «vista che contraddice la sua
// didascalia» contro cui esistono le due generazioni, vista dall'altro capo: le
// generazioni difendono dalle scritture vecchie, questa dalle letture vecchie
// ancora a video.
// Nessuna percentuale: le librerie non ne danno una. Si dice che cosa si sta
// leggendo, che e' un fatto e non una stima.
function dichiaraCaricamento(numero) {
  vista.svuota();
  document.getElementById("conteggi").textContent =
    `caricamento di ${nomeDelloStep(numero, ultimiSteps)}...`;
  document.getElementById("viewport").setAttribute("aria-busy", "true");
}
```

- [ ] **Step 5: Chiamarla in testa a `mostraStep` e spegnere `aria-busy` a lavoro finito**

In `mostraStep`, come **prima riga del corpo**, sopra la delega a `mostraNuvolaDelloStep`:

```js
  // In testa e sopra la delega: ogni strada passa di qui una volta sola, e
  // metterla anche dentro mostraNuvolaDelloStep la eseguirebbe due volte sugli
  // step senza mesh.
  dichiaraCaricamento(numero);
```

Poi, in **tutti e quattro** i punti in cui una risposta ha superato la guardia dell'ordine e sta per scrivere — cioe' subito dopo ognuna delle quattro righe `if (superata(ordine) || superata(emissione, ultimaGeometria)) return ...;` in `mostraNuvolaDelloStep` e in `mostraStep` — inserire:

```js
  document.getElementById("viewport").removeAttribute("aria-busy");
```

Una risposta scartata non lo toglie: chi l'ha superata lo ha rimesso, e sara' lei a toglierlo.

- [ ] **Step 6: Chiedere configurazione e metriche insieme**

In `apriDettaglio`, sostituire le due righe in fila:

```js
  const rispostaConfig = await fetch("/api/config").catch(serverMuto);
  const rispostaMetriche = await fetch("/api/metrics").catch(serverMuto);
```

con:

```js
  // Insieme e non in fila: sono due letture indipendenti, e in fila il pannello
  // aspettava la somma delle due latenze invece della maggiore. `.catch` resta
  // su ciascuna, cosi' un server muto prende la forma del rifiuto su entrambe.
  const [rispostaConfig, rispostaMetriche] = await Promise.all([
    fetch("/api/config").catch(serverMuto),
    fetch("/api/metrics").catch(serverMuto),
  ]);
```

- [ ] **Step 7: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py -q
```

Atteso: PASS su tutto il file.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "fix(ui): la vista dichiara l'attesa invece di mostrare lo step di prima

Per i 27-34 secondi della lettura a freddo, tela e conteggi restavano sullo step
precedente mentre il pannello mostrava gia' il nuovo: lo schermo affermava un
accoppiamento falso. Le generazioni difendevano dalle scritture vecchie e non
dalle letture vecchie rimaste a video."
```

---

## Task 3: I campi del ritaglio dicono di no

Chiude il **P1** «I campi del ritaglio ingoiano l'ingresso non valido, e poi Applica scrive altro». Oggi `app.js:542` esce in silenzio, e «Applica» manda l'ultimo array **valido**: la configurazione scritta sul disco non e' quella che i sei campi mostrano.

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:496-630` (`pannelloRitaglio`)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: `segnalaCampo(input, messaggio, rifiuto)`, gia' esistente (`app.js:637`).
- Produces: niente di nuovo di primo livello. Cambia il comportamento interno di `pannelloRitaglio`.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# Il ritaglio: cio' che il campo mostra e cio' che finisce sul disco.
# --------------------------------------------------------------------------


def _stub_ritaglio() -> str:
    """Il minimo che pannelloRitaglio tocca: la vista con un ingombro noto e una
    configurazione senza ritaglio gia' applicato."""
    return """
const vista = {
  ingombro: () => ({ min: [0, 0, 0], max: [10, 20, 30] }),
  mostraBox() {},
};
configurazione = { segment: { crop_min: null, crop_max: null } };
function dichiaraErrore() {}
function superata() { return false; }
const campiDi = (pannello) =>
  pannello.figli.flatMap((f) => f.figli).filter((n) => n.tag === "input");
const bottoneDi = (pannello) =>
  pannello.figli.find((n) => n.tag === "button");
"""


def test_un_campo_del_ritaglio_illeggibile_si_dichiara_e_spegne_applica(tmp_path):
    """Il silenzio era doppio. Il box smetteva di muoversi senza dire perche',
    e «Applica» restava acceso e mandava l'ultimo array valido: sul disco
    finiva un estremo che i sei campi non mostravano piu'. E' il principio 1
    rovesciato — si mostra un numero, se ne usa un altro, e nessun controllo lo
    smentisce."""
    sorgente = _DOM + _stub_ritaglio() + _funzioni("segnalaCampo", "pannelloRitaglio") + """
const pannello = pannelloRitaglio(0);
const campi = campiDi(pannello);
assert.equal(campi.length, 6, `sei estremi, non ${campi.length}`);
const applica = bottoneDi(pannello);
assert.notEqual(applica, undefined, "il bottone Applica non c'e' piu'");
assert.notEqual(applica.disabled, true, "nasce spento senza che nulla sia rifiutato");

campi[0].value = "abc";
await campi[0].scatena("input");
assert.equal(applica.disabled, true, "Applica manderebbe un valore che il campo non mostra");
assert.ok(
  campi[0].className.split(" ").includes("campo-rifiutato"),
  `il rifiuto non ha un canale visivo: ${campi[0].className}`,
);
assert.equal(campi[0].getAttribute("aria-invalid"), "true", "e nessun canale per chi non vede");

campi[0].value = "1.5";
await campi[0].scatena("input");
assert.equal(applica.disabled, false, "corretto il campo, Applica resta spento per sempre");
assert.equal(campi[0].getAttribute("aria-invalid"), null, "il rifiuto risolto resta a video");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_solo_campo_rotto_su_sei_basta_a_spegnere_applica(tmp_path):
    """Il contatore e' per campo, non un booleano: risolto uno dei due rifiuti,
    un booleano avrebbe riacceso il bottone con l'altro campo ancora rotto."""
    sorgente = _DOM + _stub_ritaglio() + _funzioni("segnalaCampo", "pannelloRitaglio") + """
const pannello = pannelloRitaglio(0);
const campi = campiDi(pannello);
const applica = bottoneDi(pannello);
campi[0].value = "abc";
await campi[0].scatena("input");
campi[3].value = "";
await campi[3].scatena("input");
campi[0].value = "1";
await campi[0].scatena("input");
assert.equal(applica.disabled, true, "un campo e' ancora vuoto e Applica si e' riacceso");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_app_js.py -q -k "ritaglio_illeggibile or un_solo_campo_rotto"
```

Atteso: FAIL con `AssertionError: il bottone Applica non c'e' piu'` (oggi `applica` viene creato **dopo** il ciclo dei campi, quindi non e' fra i figli nell'ordine atteso) oppure con `Applica manderebbe un valore che il campo non mostra`.

- [ ] **Step 3: Spostare la creazione di «Applica» sopra il ciclo dei campi**

In `pannelloRitaglio`, spostare il blocco che oggi sta dopo il ciclo:

```js
  const applica = document.createElement("button");
  applica.type = "button";
  applica.className = "bottone";
  applica.textContent = "Applica il ritaglio";
```

subito **sopra** il `for (const estremo of ["min", "max"])`, e aggiungere accanto:

```js
  // Quali dei sei estremi non si leggono adesso. Un insieme e non un booleano:
  // con due campi rotti, risolverne uno riaccenderebbe il bottone mentre
  // l'altro e' ancora illeggibile.
  const rifiutati = new Set();
```

- [ ] **Step 4: Sostituire il gestore silenzioso**

Dentro il doppio ciclo, sostituire il blocco:

```js
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = valori[estremo][asse].toFixed(1);
      input.addEventListener("input", () => {
        const scritto = Number(input.value);
        if (input.value.trim() === "" || !Number.isFinite(scritto)) return;
        valori[estremo][asse] = scritto;
        vista.mostraBox(valori.min, valori.max);
      });
      riga.append(input);
```

con:

```js
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = valori[estremo][asse].toFixed(1);
      const messaggio = document.createElement("small");
      messaggio.className = "errore-campo";
      messaggio.id = `errore-ritaglio-${estremo}-${asse}`;
      messaggio.hidden = true;
      const chiave = `${estremo}${asse}`;
      input.addEventListener("input", () => {
        const scritto = Number(input.value);
        // Number("") e' 0, non NaN: senza questa guardia svuotare il campo
        // porterebbe l'estremo all'origine e il box salterebbe li'.
        // Prima usciva in silenzio, e li' finiva: il box smetteva di muoversi
        // senza dire perche', e «Applica» mandava comunque l'ultimo array
        // valido — cioe' un ritaglio diverso da quello che i campi mostravano,
        // scritto su disco con un messaggio di successo sopra.
        // Gli stessi tre canali dei campi di parametro, con la stessa funzione:
        // bordo, testo, e aria-invalid con aria-errormessage.
        if (input.value.trim() === "" || !Number.isFinite(scritto)) {
          rifiutati.add(chiave);
          segnalaCampo(input, messaggio, "serve un numero: il box non si muove e «Applica» resta spento.");
          applica.disabled = true;
          return;
        }
        rifiutati.delete(chiave);
        segnalaCampo(input, messaggio, null);
        // Non `false` secco: gli altri cinque campi possono essere ancora rotti.
        applica.disabled = rifiutati.size > 0;
        valori[estremo][asse] = scritto;
        vista.mostraBox(valori.min, valori.max);
      });
      riga.append(input, messaggio);
```

- [ ] **Step 5: Togliere la vecchia creazione del bottone**

Dopo il ciclo, dove oggi il bottone veniva creato, restano solo:

```js
  const esito = document.createElement("p");
  esito.className = "aiuto";
```

Le quattro righe che creavano `applica` sono state spostate al passo 3: verificare che non siano rimaste duplicate.

- [ ] **Step 6: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py -q
```

Atteso: PASS su tutto il file. Se un controllo preesistente sulla didascalia del ritaglio fallisce per la posizione dei figli, aggiornarlo: la posizione e' cambiata di proposito, il comportamento no.

- [ ] **Step 7: Commit**

```bash
git add meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "fix(ui): un estremo del ritaglio che non si legge lo dice, e Applica si spegne

Il campo usciva in silenzio e il bottone mandava l'ultimo array valido: sul
disco finiva un ritaglio che i sei campi non mostravano, con un messaggio di
successo sopra. Era l'unico punto in cui stato mostrato e stato persistito
potevano discordare senza che niente lo smentisse."
```

---

## Task 4: La Galleria mostra i suoi numeri

Chiude il **P1** «La Galleria non mostra nessuno dei dati per cui esiste». L'`impronta` SHA-256 da 64 caratteri apre la tabella e da sola sfonda i 22rem della colonna.

**Sulla domanda 4 della critica.** `report._COLUMNS` e' riusato perche' la tabella a video non possa divergere dall'appendice stampata. Questo piano tiene fermo l'**insieme** e cambia il **verso di lettura**: le colonne si riordinano scegliendole per `chiave` fra quelle che il server manda, e una chiave che l'ordine non nomina compare comunque, in coda. Una colonna aggiunta a `_COLUMNS` domani appare da sola, che e' la proprieta' per cui il riuso esiste. In piu' si antepone una colonna **derivata** da `on_front`, che nell'appendice e' gia' presente come classe di riga: e' lo stesso fatto reso in un mezzo diverso, non una grandezza in piu'.

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html:74-80` (blocco Galleria)
- Modify: `meshrec/src/meshrec/ui/stile.css` (regole `.galleria-tabella`)
- Modify: `meshrec/src/meshrec/ui/app.js:956-1056` (galleria)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: niente da task precedenti.
- Produces: `ORDINE_GALLERIA` (array di chiavi) e `colonneOrdinate(colonne)` → `Array<{colonna, indice}>`, dove `indice` e' la posizione **originale** della colonna, quella con cui indicizzare `corpo.celle[riga]`.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# La galleria: otto colonne in 22rem, e l'impronta che le sfondava tutte.
# --------------------------------------------------------------------------


def test_la_didascalia_della_galleria_sta_fuori_dal_riquadro_che_scorre():
    """Stava dentro .galleria-tabella, che ha overflow-x: auto. Scorrendo a
    destra per leggere i numeri, «11 candidati, 1 sul fronte» usciva dallo
    schermo insieme all'impronta: si perdeva insieme il conto e l'identita'
    delle righe."""
    markup = _senza_commenti_html(_markup())
    assert 'id="galleria-didascalia"' in markup, "la didascalia non ha un posto proprio"
    assert markup.index('id="galleria-didascalia"') < markup.index('id="galleria-tabella"'), (
        "la didascalia e' finita dopo il riquadro che scorre"
    )


def test_il_riquadro_che_scorre_e_raggiungibile_da_tastiera():
    """Lo stesso difetto per cui #registro ha un tabindex e otto righe di
    commento: un contenitore che scorre e non contiene nulla di focalizzabile
    e' irraggiungibile senza mouse su Chrome (WCAG 2.1.1, livello A)."""
    elemento = _elemento(_senza_commenti_html(_markup()), "galleria-tabella")
    assert 'tabindex="0"' in elemento, f"irraggiungibile senza mouse: {elemento}"
    assert "aria-label" in elemento, f"raggiungibile e senza nome: {elemento}"


def test_l_ordine_delle_colonne_mette_l_impronta_in_coda(tmp_path):
    """L'insieme resta quello di report._COLUMNS — si sceglie per chiave, e una
    colonna che l'ordine non nomina compare comunque — cambia il verso di
    lettura. L'indice originale torna insieme alla colonna, perche' e' quello
    con cui si indicizzano le celle della riga."""
    sorgente = _DOM + _funzioni("colonneOrdinate") + """
const ORDINE_GALLERIA = [
  "outcome", "thickness_error", "tets", "over", "dihedral", "duration_s", "axes", "fingerprint",
];
const colonne = [
  { chiave: "fingerprint", etichetta: "impronta" },
  { chiave: "axes", etichetta: "assi" },
  { chiave: "outcome", etichetta: "esito" },
  { chiave: "tets", etichetta: "tetraedri" },
  { chiave: "novita", etichetta: "colonna futura" },
];
const ordinate = colonneOrdinate(colonne, ORDINE_GALLERIA);
const chiavi = ordinate.map((v) => v.colonna.chiave);
assert.equal(chiavi[0], "outcome", `apre con ${chiavi[0]} invece che con l'esito`);
assert.equal(chiavi[chiavi.length - 1], "novita", "una chiave sconosciuta e' sparita invece di finire in coda");
assert.ok(chiavi.indexOf("fingerprint") > chiavi.indexOf("tets"), "l'impronta apre ancora la tabella");
assert.equal(chiavi.length, colonne.length, "il riordino ha perso o duplicato una colonna");
assert.equal(
  ordinate.find((v) => v.colonna.chiave === "fingerprint").indice, 0,
  "l'indice originale non torna: le celle finirebbero sotto la colonna sbagliata",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_la_riga_di_fronte_ha_un_canale_che_non_e_il_colore(tmp_path):
    """L'appartenenza al fronte di Pareto e' la risposta all'intera domanda
    della Fase 2, e a video era una tinta e un filetto: due canali visivi e
    nessun canale testuale (WCAG 1.4.1). Peggio, il filetto e' ancorato al
    bordo sinistro della riga ed esce dalla vista appena si scorre a destra,
    cioe' proprio quando i numeri diventano leggibili."""
    sorgente = _DOM + """
const ORDINE_GALLERIA = ["outcome", "fingerprint"];
""" + _funzioni("colonneOrdinate", "disegnaTabellaGalleria") + """
disegnaTabellaGalleria({
  nome: "lab_crop",
  fronte: 1,
  righe: [{ on_front: true }, { on_front: false }],
  colonne: [
    { chiave: "fingerprint", etichetta: "impronta" },
    { chiave: "outcome", etichetta: "esito" },
  ],
  celle: [["a".repeat(64), "ok"], ["b".repeat(64), "ok"]],
});
const tabella = document.getElementById("galleria-tabella").figli[0];
// figli[0] e' <caption>, figli[1] <thead>, figli[2] <tbody>.
const righe = tabella.figli[2].figli;
const testi = righe.map((r) => r.figli.map((c) => c.textContent));
assert.notEqual(testi[0][0], testi[1][0], "le due righe non si distinguono per testo");
assert.ok(testi[0].join(" ").includes("fronte"), `nessun canale testuale: ${testi[0]}`);
const impronta = testi[0][testi[0].length - 1];
assert.ok(impronta.length <= 12, `l'impronta piena sfonda ancora la colonna: ${impronta}`);
assert.equal(
  righe[0].figli[righe[0].figli.length - 1].getAttribute("title"), "a".repeat(64),
  "l'impronta troncata ha perso il valore pieno",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_app_js.py -q -k "galleria or fronte_ha_un_canale or colonne_mette"
```

Atteso: FAIL su tutti e quattro.

- [ ] **Step 3: Rifare il blocco Galleria nel markup**

In `meshrec/src/meshrec/ui/index.html`, sostituire le righe del blocco Galleria (dal commento «Sola lettura» a `<div class="galleria-tabella" id="galleria-tabella"></div>`) con:

```html
    <h2>Galleria di curazione</h2>
    <!-- Sola lettura: nessun clic qui scrive sul disco. I registri sono
         quelli della Fase 2 (experiments/), la tabella sperimentale della
         tesi. -->
    <p class="aiuto">Registri della Fase 2. I candidati sul fronte di Pareto sono segnati nella prima colonna.</p>
    <div class="azioni" id="galleria-elenco"></div>
    <!-- La didascalia sta FUORI dal riquadro che scorre. Dentro, «11 candidati,
         1 sul fronte» usciva dallo schermo appena si scorreva a destra per
         leggere i numeri: si perdeva il conto proprio mentre si guardavano le
         righe che conta. -->
    <p class="aiuto" id="galleria-didascalia"></p>
    <!-- tabindex="0" e aria-label per la stessa ragione del registro: il
         riquadro scorre in orizzontale e non contiene nulla su cui il fuoco
         possa posarsi, quindi senza questi attributi le sette colonne oltre la
         prima sono irraggiungibili senza mouse (WCAG 2.1.1, livello A).
         Chrome non lo fa da solo. -->
    <div class="galleria-tabella" id="galleria-tabella" role="region"
         aria-label="Registro dell'esperimento" tabindex="0"></div>
```

- [ ] **Step 4: Aggiungere le regole di stile**

In `meshrec/src/meshrec/ui/stile.css`, subito dopo la regola `.galleria-tabella { overflow-x: auto; }`:

```css
/* Raggiungibile da tastiera e senza contorno sarebbe una tappa cieca, cioe' un
   difetto al posto di una correzione. Stesso contorno del registro, non uno suo. */
.galleria-tabella:focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
```

e sostituire la regola della riga di fronte:

```css
.galleria-tabella tr.fronte { background: var(--evidenza); box-shadow: inset 2px 0 0 var(--accento); }
```

con:

```css
/* Il fondo resta, il filetto no: e' ancorato al bordo sinistro della riga e
   scorre fuori dalla vista appena si guarda a destra, cioe' proprio quando i
   numeri diventano leggibili. Un canale che sparisce quando serve non e' un
   canale. Il posto suo lo ha preso la prima colonna, che e' testo e non se ne
   va da nessuna parte. */
.galleria-tabella tr.fronte { background: var(--evidenza); }
.galleria-tabella tr.fronte td:first-child { font-weight: 600; color: var(--accento); }
```

- [ ] **Step 5: Scrivere l'ordine e la funzione di riordino**

In `meshrec/src/meshrec/ui/app.js`, subito prima di `function disegnaTabellaGalleria(`:

```js
// L'ordine dell'appendice stampata non e' l'ordine di una colonna da 22rem:
// l'impronta SHA-256 e' 64 caratteri che non vanno a capo, e da sola sfondava
// il riquadro, lasciando fuori schermo tutte e sette le grandezze per cui il
// pannello esiste.
// L'insieme resta quello di report._COLUMNS: qui si sceglie per chiave, e una
// chiave che questo elenco non nomina compare comunque, in coda. Una colonna
// aggiunta al server domani appare da sola, che e' la proprieta' per cui le
// colonne sono riusate invece di riscelte.
const ORDINE_GALLERIA = [
  "outcome", "thickness_error", "tets", "over", "dihedral", "duration_s", "axes", "fingerprint",
];

// Le colonne nel verso di lettura, ognuna con il proprio indice di partenza:
// e' quello con cui si indicizzano le celle, che il server manda nell'ordine
// suo. Perderlo vorrebbe dire mettere i numeri sotto l'intestazione sbagliata,
// che e' peggio di una tabella troppo larga.
function colonneOrdinate(colonne, ordine = ORDINE_GALLERIA) {
  const posizione = (colonna) => {
    const trovata = ordine.indexOf(colonna.chiave);
    return trovata === -1 ? ordine.length : trovata;
  };
  return colonne
    .map((colonna, indice) => ({ colonna, indice }))
    .sort((a, b) => posizione(a.colonna) - posizione(b.colonna) || a.indice - b.indice);
}
```

- [ ] **Step 6: Riscrivere `disegnaTabellaGalleria`**

Sostituire l'intero corpo di `disegnaTabellaGalleria` con:

```js
function disegnaTabellaGalleria(corpo) {
  const contenitore = document.getElementById("galleria-tabella");
  const didascalia = document.getElementById("galleria-didascalia");
  contenitore.replaceChildren();
  if (corpo.righe.length === 0) {
    didascalia.textContent = `${corpo.nome}: registro vuoto.`;
    return;
  }
  didascalia.textContent =
    `${corpo.nome}: ${corpo.righe.length} candidati, ${corpo.fronte} sul fronte.`;
  const ordinate = colonneOrdinate(corpo.colonne);
  const rigaTesta = document.createElement("tr");
  // La colonna del fronte e' derivata, non una grandezza in piu': nell'appendice
  // lo stesso fatto e' gia' li', come classe della riga. A video una classe non
  // si legge, e il colore da solo non basta (WCAG 1.4.1).
  const testaFronte = document.createElement("th");
  testaFronte.textContent = "fronte";
  testaFronte.setAttribute("scope", "col");
  rigaTesta.append(testaFronte);
  for (const { colonna } of ordinate) {
    const testa = document.createElement("th");
    testa.textContent = colonna.etichetta;
    // scope="col": senza, un lettore di schermo non lega la cella alla sua
    // intestazione, e otto numeri di fila non dicono di che cosa siano.
    testa.setAttribute("scope", "col");
    rigaTesta.append(testa);
  }
  const testa = document.createElement("thead");
  testa.append(rigaTesta);
  const corpoTabella = document.createElement("tbody");
  corpo.righe.forEach((riga, indice) => {
    const rigaHtml = document.createElement("tr");
    // "fronte", non un nuovo nome: e' la stessa classe che report.write_report
    // scrive sulla riga di fronte dell'appendice della tesi.
    if (riga.on_front) rigaHtml.className = "fronte";
    const cellaFronte = document.createElement("td");
    cellaFronte.textContent = riga.on_front ? "fronte" : "";
    rigaHtml.append(cellaFronte);
    for (const { colonna, indice: originale } of ordinate) {
      const testo = String(corpo.celle[indice][originale] ?? "");
      const cella = document.createElement("td");
      // L'impronta troncata, con il valore pieno nel titolo: e' un
      // identificatore da riconoscere, non da leggere, e otto caratteri di
      // SHA-256 bastano a distinguere undici candidati.
      if (colonna.chiave === "fingerprint") {
        cella.textContent = testo.slice(0, 8);
        cella.setAttribute("title", testo);
      } else {
        cella.textContent = testo;
      }
      rigaHtml.append(cella);
    }
    corpoTabella.append(rigaHtml);
  });
  const tabella = document.createElement("table");
  const nome = document.createElement("caption");
  nome.textContent = `Registro dell'esperimento ${corpo.nome}`;
  tabella.append(nome, testa, corpoTabella);
  contenitore.append(tabella);
}
```

`<caption>` sta per primo dentro `<table>`, come vuole l'HTML: il controllo del passo 1 legge il corpo da `tabella.figli[2]` proprio per questo.

- [ ] **Step 7: Marcare l'esperimento scelto**

In `caricaGalleria`, dentro la `map` che crea i bottoni, aggiungere dopo `bottone.dataset.nome = nome;`:

```js
    // Nessuno stato scelto: due bottoni identici e nessun segno di quale
    // tabella si sta guardando. .step ha aria-current e un doppio canale con
    // sei righe di commento a difenderlo; qui non c'era niente.
    bottone.setAttribute("aria-pressed", "false");
```

e nel gestore di clic in fondo al file, sostituire:

```js
document.getElementById("galleria-elenco").addEventListener("click", (evento) => {
  const bottone = evento.target.closest("button");
  if (!bottone) return;
  mostraEsperimento(bottone.dataset.nome);
});
```

con:

```js
document.getElementById("galleria-elenco").addEventListener("click", (evento) => {
  const bottone = evento.target.closest("button");
  if (!bottone) return;
  mostraEsperimento(bottone.dataset.nome).then((scritto) => {
    // Solo se questa richiesta ha davvero scritto: marcare un bottone la cui
    // risposta e' stata scartata direbbe che si sta guardando una tabella che
    // non e' a video.
    if (!scritto) return;
    for (const altro of document.querySelectorAll(".bottone")) {
      if (altro.dataset.nome !== undefined) {
        altro.setAttribute("aria-pressed", String(altro === bottone));
      }
    }
  });
});
```

- [ ] **Step 8: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py -q
```

Atteso: PASS su tutto il file.

- [ ] **Step 9: Commit**

```bash
git add meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "fix(ui): la galleria mostra le grandezze invece dell'impronta

Otto colonne in 22rem, aperte da uno SHA-256 di 64 caratteri: la tabella
sperimentale della tesi mostrava zero delle otto grandezze per cui esiste.
L'insieme delle colonne resta quello di report._COLUMNS, cambia il verso di
lettura; il fronte di Pareto prende un canale testuale, e il riquadro che
scorre diventa raggiungibile da tastiera."
```

---

## Task 5: Le esecuzioni si distinguono da un filtro

Chiude il **P1** «Le scritture irreversibili sono indistinguibili da un filtro». Tre bottoni identici da 14px: uno carica una tabella in sola lettura, uno riscrive gli artefatti dallo step aperto all'undicesimo.

**Files:**
- Modify: `meshrec/src/meshrec/ui/stile.css` (ceto primario)
- Modify: `meshrec/src/meshrec/ui/app.js:3-9` (etichette con l'accento), `:107-141` (gestore `stato`), `:870-907` (i due bottoni)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: niente da task precedenti.
- Produces:
  - `azioniDelloStep(numero, ordine)` → elemento `div.azioni` con i due bottoni. Estratta da `apriDettaglio` perche' dentro una funzione di centocinquanta righe non la esegue nessun banco — la stessa ragione per cui esistono `campoParametro` e `scriviParametro`.
  - `spegniLeEsecuzioni(inCorso)` — spegne o riaccende tutti i `.esecuzione`.
  - `let corsaInCorso` — variabile di modulo, vera mentre una corsa gira.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# I due «Esegui»: un ceto, una portata dichiarata, e la corsa che li spegne.
# --------------------------------------------------------------------------


def test_un_solo_ceto_primario_e_la_portata_e_scritta_nell_etichetta(tmp_path):
    """«Esegui da qui in giu'» riscrive gli artefatti dallo step aperto
    all'undicesimo — minuti di calcolo e centinaia di MB — e aveva lo stesso
    aspetto e la stessa etichetta generica del bottone che carica una tabella
    di sola lettura. La portata non era scritta da nessuna parte."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
""" + _funzioni("azioniDelloStep") + """
const azioni = azioniDelloStep(9, 0);
const bottoni = azioni.figli;
assert.equal(bottoni.length, 2, `due azioni, non ${bottoni.length}`);
const primari = bottoni.filter((b) => b.className.split(" ").includes("bottone-primario"));
assert.equal(primari.length, 1, "il ceto primario si e' moltiplicato o e' sparito");
assert.match(bottoni[1].textContent, /9/, "la portata non nomina lo step di partenza");
assert.match(bottoni[1].textContent, /11/, "ne' quello d'arrivo");
assert.ok(
  bottoni.every((b) => b.className.split(" ").includes("esecuzione")),
  "un'esecuzione senza la classe che la fa spegnere durante la corsa",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_le_esecuzioni_si_spengono_mentre_la_corsa_gira(tmp_path):
    """Restavano vive e si affidavano al 400 del worker: un rifiuto che si
    poteva evitare, e un bottone che risponde «no» non si distingue da uno che
    non ha fatto niente. Annulla lo faceva gia', dallo stesso carico."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
""" + _funzioni("azioniDelloStep", "spegniLeEsecuzioni") + """
const azioni = azioniDelloStep(9, 0);
radice.append(azioni);
spegniLeEsecuzioni(true);
assert.ok(azioni.figli.every((b) => b.disabled === true), "un Esegui e' rimasto vivo a corsa viva");
spegniLeEsecuzioni(false);
assert.ok(azioni.figli.every((b) => b.disabled === false), "restano spenti a corsa finita");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_le_etichette_mostrate_portano_gli_accenti_italiani():
    """I sorgenti in ASCII sono una convenzione del repository; le stringhe
    proiettate davanti a una commissione non la ereditano. Il registro che
    PRODUCT.md dichiara — asciutto e accademico — non regge «Qualita»."""
    modulo = _modulo()
    assert '"Qualità superficie"' in modulo, "l'etichetta dello step 7 e' senza accento"
    assert '"Qualità volume"' in modulo, "l'etichetta dello step 10 e' senza accento"
    # Senza i commenti: «riscrive gli artefatti dall'N in giu'» e' una
    # spiegazione, non un'etichetta, e vietare la stringa nei commenti
    # vieterebbe la spiegazione. E' la stessa ragione per cui
    # _senza_commenti_js esiste.
    assert "in giu'" not in _senza_commenti_js(modulo), (
        "un'etichetta mostrata dice ancora «da qui in giu'» invece della portata"
    )
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_app_js.py -q -k "ceto_primario or si_spengono or accenti_italiani"
```

Atteso: FAIL.

- [ ] **Step 3: Aggiungere il ceto primario al foglio di stile**

In `meshrec/src/meshrec/ui/stile.css`, subito dopo `.bottone:disabled:hover`:

```css
/* Un solo ceto primario in tutta l'interfaccia: l'esecuzione dello step aperto.
   Il contorno da solo non distingue un'azione che costa minuti e riscrive
   centinaia di MB da una che carica una tabella di sola lettura, e i tre
   bottoni piu' cari del prodotto avevano esattamente lo stesso aspetto del
   filtro della galleria. Testo su --accento: 7,49:1 misurato. */
.bottone-primario { background: var(--accento); border-color: var(--accento); color: var(--superficie); }
.bottone-primario:hover { background: color-mix(in srgb, var(--accento) 88%, black); }
.bottone-primario:active { background: color-mix(in srgb, var(--accento) 78%, black); }
/* Spento torna al ceto comune: un riempimento pieno su un comando che non si
   puo' premere e' un invito che mente. */
.bottone-primario:disabled { background: var(--spento); border-color: var(--bordo-comando); color: var(--tenue); }
```

- [ ] **Step 4: Correggere gli accenti nelle stringhe mostrate**

In `meshrec/src/meshrec/ui/app.js`, dentro `ETICHETTE`:

```js
  "07_surface_quality": "Qualità superficie",
  "10_volume_quality": "Qualità volume",
```

- [ ] **Step 5: Estrarre `azioniDelloStep` e scrivere `spegniLeEsecuzioni`**

In `meshrec/src/meshrec/ui/app.js`, subito prima di `async function apriDettaglio(`:

```js
// Vera mentre una corsa gira. La sa lo scorrere degli eventi, e serve ai due
// «Esegui»: un pannello aperto in mezzo a una corsa nasceva con i bottoni vivi.
let corsaInCorso = false;

// I due «Esegui» seguono la corsa come Annulla, e dallo stesso carico. Restare
// vivi e affidarsi al 400 del worker e' un rifiuto che si poteva evitare, e un
// bottone che risponde «no» non si distingue da uno che non ha fatto niente.
function spegniLeEsecuzioni(inCorso) {
  for (const bottone of document.querySelectorAll(".esecuzione")) {
    bottone.disabled = inCorso;
  }
}

// I due comandi d'esecuzione del pannello. Estratti da apriDettaglio per la
// stessa ragione di campoParametro e scriviParametro: dentro una funzione di
// centocinquanta righe non li esegue nessun banco, e qui c'e' una conferma da
// provare.
function azioniDelloStep(numero, ordine) {
  const azioni = document.createElement("div");
  azioni.className = "azioni";
  // I due bottoni condividono `ordine` (la generazione del pannello) e la
  // stessa rigaErrore: due clic — sullo stesso bottone o su quello diverso —
  // condividono `ordine` senza distinguersi fra loro. Un contatore per clic,
  // condiviso dai due perche' condividono il canale d'errore che protegge.
  let ultimaAzione = 0;
  function apriAzione() {
    ultimaAzione += 1;
    return ultimaAzione;
  }
  const comandi = [
    { etichetta: "Esegui questo step", percorso: `/api/step/${numero}`, primario: true },
    {
      // La portata sta nell'etichetta: «da qui in giu'» non dice quanti step
      // riscrive, e sono tutti quelli dallo step aperto all'undicesimo.
      etichetta: `Esegui dallo step ${numero} all'11`,
      percorso: `/api/step/${numero}/from`,
      primario: false,
    },
  ];
  for (const { etichetta, percorso, primario } of comandi) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = primario ? "bottone bottone-primario esecuzione" : "bottone esecuzione";
    bottone.textContent = etichetta;
    bottone.disabled = corsaInCorso;
    // Conferma in linea e non una finestra modale: la modale e' la risposta
    // pigra, e questa azione non e' distruttiva in astratto — riscrive
    // artefatti che si possono rifare — e' cara. Una seconda pressione basta a
    // separare il clic voluto da quello sbagliato di mira.
    let chiesta = false;
    bottone.addEventListener("click", async () => {
      if (!primario && !chiesta) {
        chiesta = true;
        bottone.textContent = `Confermi? riscrive dallo step ${numero} all'11`;
        return;
      }
      chiesta = false;
      bottone.textContent = etichetta;
      dichiaraErrore(null);
      const azione = apriAzione();
      const risposta = await fetch(percorso, { method: "POST" }).catch(serverMuto);
      if (risposta.ok) return;
      const ragione = await ragioneDelRifiuto(risposta);
      // rigaErrore e' quella del pannello aperto adesso: se nel frattempo ne e'
      // stato aperto un altro, o e' partito un secondo clic, questo rifiuto
      // finirebbe scritto sotto lo step o il clic sbagliato.
      if (superata(ordine) || superata(azione, ultimaAzione)) return;
      dichiaraErrore(ragione);
    });
    azioni.append(bottone);
  }
  return azioni;
}
```

Poi, dentro `apriDettaglio`, sostituire tutto il blocco che va da `const azioni = document.createElement("div");` fino a `dettaglio.append(azioni);` (comprese le due funzioni interne `apriAzione`/`ultimaAzione` e il ciclo `for (const [etichetta, percorso] of [...])`) con la sola riga:

```js
  dettaglio.append(azioniDelloStep(numero, ordine));
```

- [ ] **Step 6: Collegare lo stato della corsa**

Nel gestore `flusso.addEventListener("stato", ...)`, subito dopo la riga che spegne `Annulla`:

```js
  corsaInCorso = stato.in_corso;
  spegniLeEsecuzioni(stato.in_corso);
```

- [ ] **Step 7: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py -q
```

Atteso: PASS su tutto il file. Se un controllo preesistente cerca le stringhe `"Qualita superficie"` o `"Esegui da qui in giu'"`, aggiornarlo: sono cambiate di proposito.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "fix(ui): un'esecuzione non ha piu' l'aspetto di un filtro

Tre bottoni identici: uno carica una tabella di sola lettura, uno riscrive gli
artefatti dallo step aperto all'undicesimo senza dire quanti ne tocca. Adesso
c'e' un solo ceto primario, la portata sta nell'etichetta, la seconda pressione
conferma, e i due Esegui seguono la corsa come Annulla."
```

---

## Task 6: I parametri cambiati si vedono, gli altri si richiudono

E' la **divulgazione progressiva** scelta dall'utente. `/api/schema` manda gia' il `default` di ogni campo (`server.py:335-342`) e l'interfaccia lo scarta. Il taglio fra «aperto» e «richiudibile» **non lo decide il gusto**: e' cio' che questa corsa ha spostato dal predefinito. Un elenco base/avanzato inventato qui sarebbe una classificazione che nessun dato sostiene.

**Files:**
- Modify: `meshrec/src/meshrec/ui/stile.css` (segno del cambiato, piega)
- Modify: `meshrec/src/meshrec/ui/app.js:750-783` (`campoParametro`), `:909-919` (il ciclo dei blocchi)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: `campoParametro(blocco, nome, campo, ordine)`, gia' esistente.
- Produces:
  - `cambiatoDalPredefinito(valore, predefinito)` → `boolean`. Pura.
  - `gruppoDelBlocco(blocco, campi, ordine)` → elemento `fieldset.gruppo`.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
# --------------------------------------------------------------------------
# I predefiniti: erano sul filo e finivano nel cestino.
# --------------------------------------------------------------------------


def test_il_confronto_col_predefinito_e_sul_testo_reso(tmp_path):
    """Il campo mostra una stringa, e /api/schema serializza i predefiniti con
    default=str: un Path arriva come testo. Confrontare i valori grezzi
    segnerebbe come «cambiato» un parametro che nessuno ha toccato, solo perche'
    le due grafie dello stesso valore non sono lo stesso oggetto."""
    sorgente = _DOM + _funzioni("cambiatoDalPredefinito") + """
assert.equal(cambiatoDalPredefinito(9, 9), false, "lo stesso numero risulta cambiato");
assert.equal(cambiatoDalPredefinito(null, null), false, "due assenze risultano diverse");
assert.equal(cambiatoDalPredefinito(0.005, null), true, "un valore su un predefinito assente");
assert.equal(cambiatoDalPredefinito(9, 10), true, "due numeri diversi risultano uguali");
assert.equal(cambiatoDalPredefinito(false, false), false, "due booleani uguali");
assert.equal(cambiatoDalPredefinito([1, 2], [1, 2]), false, "due liste uguali");
assert.equal(cambiatoDalPredefinito([1, 2], [1, 3]), true, "due liste diverse");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_il_blocco_apre_sui_cambiati_e_richiude_i_predefiniti(tmp_path):
    """Il fieldset `segment` rendeva undici campi di fila, `surface` nove: molto
    oltre i quattro elementi che si tengono in mente insieme. Il taglio non e'
    inventato — e' cio' che questa corsa ha spostato dal predefinito, che e'
    anche la sola domanda che un prodotto sulla riproducibilita' deve saper
    rispondere a colpo d'occhio."""
    sorgente = _DOM + """
configurazione = { segment: { method: "auto", knn: 20, soglia: 0.01 } };
""" + _funzioni("cambiatoDalPredefinito", "campoParametro", "gruppoDelBlocco") + """
const campi = {
  method: { description: "come segmentare", default: "auto" },
  knn: { description: "vicini", default: 30 },
  soglia: { description: "soglia", default: 0.01 },
};
const gruppo = gruppoDelBlocco("segment", campi, 0);
const pieghe = gruppo.figli.filter((f) => f.tag === "details");
assert.equal(pieghe.length, 1, "i predefiniti non si richiudono");
const aperti = gruppo.figli.filter((f) => f.tag === "label");
assert.equal(aperti.length, 1, `aperto ${aperti.length} campi invece del solo cambiato`);
assert.equal(pieghe[0].figli.filter((f) => f.tag === "label").length, 2, "due predefiniti nella piega");
assert.notEqual(pieghe[0].open, true, "la piega e' aperta pur avendo un cambiato fuori");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_blocco_tutto_al_predefinito_nasce_aperto(tmp_path):
    """Alla prima corsa nessun parametro e' stato spostato, e un pannello che
    mostra solo una riga da cliccare non insegna niente a chi apre lo step per
    la prima volta. E' l'utente successivo confermato da PRODUCT.md."""
    sorgente = _DOM + """
configurazione = { segment: { knn: 30, soglia: 0.01 } };
""" + _funzioni("cambiatoDalPredefinito", "campoParametro", "gruppoDelBlocco") + """
const gruppo = gruppoDelBlocco("segment", {
  knn: { description: "vicini", default: 30 },
  soglia: { description: "soglia", default: 0.01 },
}, 0);
const piega = gruppo.figli.find((f) => f.tag === "details");
assert.equal(piega.open, true, "il primo avvio si apre su una riga da cliccare");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_campo_cambiato_dichiara_il_predefinito_per_iscritto(tmp_path):
    """Non il solo colore: «che cosa ho spostato dallo stock» e' la storia che la
    tesi racconta, e chi non distingue le tinte deve poterla leggere."""
    sorgente = _DOM + """
configurazione = { segment: { knn: 20 } };
""" + _funzioni("cambiatoDalPredefinito", "campoParametro") + """
const riga = campoParametro("segment", "knn", { description: "vicini", default: 30 }, 0);
const testo = riga.figli.map((f) => f.textContent).join(" ");
assert.match(testo, /30/, `il predefinito non e' scritto da nessuna parte: ${testo}`);
assert.ok(riga.className.split(" ").includes("campo-cambiato"), "manca il canale visivo");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_app_js.py -q -k "predefinit or blocco_apre or blocco_tutto"
```

Atteso: FAIL.

- [ ] **Step 3: Estendere il DOM finto con `<details>`**

Il banco non conosce `open` ne' il tag `details`, ma `Elemento` accetta proprieta' arbitrarie e `createElement` prende il tag: non serve nessuna modifica a `_DOM`. Verificare solo che `Elemento` esponga `.tag`, cosa che gia' fa. **Nessuna modifica da apportare in questo passo**; e' un controllo, non un intervento.

- [ ] **Step 4: Scrivere `cambiatoDalPredefinito`**

In `meshrec/src/meshrec/ui/app.js`, subito prima di `function campoParametro(`:

```js
// Se questa corsa ha spostato il parametro da cio' che il modello scrive quando
// nessuno tocca niente. /api/schema manda il predefinito di ogni campo e
// l'interfaccia lo buttava via: in un prodotto la cui tesi e' la
// riproducibilita', «che cosa ho cambiato dallo stock» e' la prima domanda, e
// la risposta era gia' nel browser.
// Il confronto e' sul testo reso e non sui valori: il campo mostra una stringa,
// e /api/schema serializza i predefiniti con default=str, quindi un Path arriva
// gia' come testo. Confrontare i valori grezzi segnerebbe come cambiato un
// parametro che nessuno ha toccato.
function cambiatoDalPredefinito(valore, predefinito) {
  const reso = (v) =>
    v === null || v === undefined
      ? ""
      : ["string", "number", "boolean"].includes(typeof v)
        ? String(v)
        : JSON.stringify(v);
  return reso(valore) !== reso(predefinito);
}
```

- [ ] **Step 5: Marcare il campo cambiato**

In `campoParametro`, subito prima di `return riga;`, aggiungere:

```js
  // Due canali: la classe per chi guarda, il predefinito scritto per chi legge.
  // Il colore da solo lascerebbe fuori chi non distingue le tinte, e il valore
  // di partenza e' l'informazione vera — sapere che «e' cambiato» senza sapere
  // «da che cosa» non chiude nessuna domanda.
  if (cambiatoDalPredefinito(valore, campo.default)) {
    riga.classList.toggle("campo-cambiato", true);
    const segno = document.createElement("small");
    segno.className = "aiuto segno-cambiato";
    const stock = campo.default === null || campo.default === undefined
      ? "nessuno"
      : String(campo.default);
    segno.textContent = `cambiato — predefinito: ${stock}`;
    riga.append(segno);
  }
```

- [ ] **Step 6: Scrivere `gruppoDelBlocco` e usarlo**

In `meshrec/src/meshrec/ui/app.js`, subito dopo `campoParametro`:

```js
// Il fieldset di un blocco. `segment` rende undici campi, `surface` nove: molto
// oltre i quattro elementi che si tengono in mente insieme, e senza nessun
// ordine dentro.
// Il taglio fra cio' che si apre e cio' che si richiude non lo decide il gusto:
// e' cio' che questa corsa ha spostato dal predefinito. Un elenco
// base/avanzato scritto qui sarebbe una classificazione che nessun dato
// sostiene, e i nomi dei parametri non ne portano una — la stessa ragione per
// cui l'ordine dei gruppi del viewport e' diventato funzione del dato.
// <details> nativo e non un pannello richiudibile scritto a mano: porta con se'
// il proprio ruolo, la propria tastiera e il proprio stato, e nessuno dei tre
// va reimplementato.
function gruppoDelBlocco(blocco, campi, ordine) {
  const gruppo = document.createElement("fieldset");
  gruppo.className = "gruppo";
  gruppo.append(Object.assign(document.createElement("legend"), { textContent: blocco }));
  const cambiati = [];
  const fermi = [];
  for (const [nome, campo] of Object.entries(campi)) {
    const riga = campoParametro(blocco, nome, campo, ordine);
    const spostato = cambiatoDalPredefinito(configurazione[blocco][nome], campo.default);
    (spostato ? cambiati : fermi).push(riga);
  }
  gruppo.append(...cambiati);
  if (fermi.length > 0) {
    const piega = document.createElement("details");
    const titolo = document.createElement("summary");
    titolo.textContent = fermi.length === 1
      ? "1 parametro al valore predefinito"
      : `${fermi.length} parametri al valore predefinito`;
    piega.append(titolo, ...fermi);
    // Aperta quando non c'e' nient'altro: alla prima corsa nessun parametro e'
    // stato spostato, e un pannello che mostra solo una riga da cliccare non
    // insegna niente a chi apre lo step per la prima volta.
    if (cambiati.length === 0) piega.open = true;
    gruppo.append(piega);
  }
  return gruppo;
}
```

Poi, in `apriDettaglio`, sostituire il ciclo dei blocchi:

```js
  for (const blocco of voce.blocchi) {
    const gruppo = document.createElement("fieldset");
    gruppo.className = "gruppo";
    const titolo = document.createElement("legend");
    titolo.textContent = blocco;
    gruppo.append(titolo);
    for (const [nome, campo] of Object.entries(voce.campi[blocco])) {
      gruppo.append(campoParametro(blocco, nome, campo, ordine));
    }
    dettaglio.append(gruppo);
  }
```

con:

```js
  for (const blocco of voce.blocchi) {
    dettaglio.append(gruppoDelBlocco(blocco, voce.campi[blocco], ordine));
  }
```

- [ ] **Step 7: Aggiungere le regole di stile**

In `meshrec/src/meshrec/ui/stile.css`, subito dopo la regola `.campo input[readonly]`:

```css
/* Il campo che questa corsa ha spostato dal predefinito. Nessun fondo pieno e
   nessuna barra laterale: un filetto sotto l'etichetta basta a farlo trovare
   scorrendo, e il fatto sta comunque scritto sotto il campo. */
.campo-cambiato > span:first-child { font-weight: 600; }
.segno-cambiato { color: var(--tenue); }
/* La piega dei predefiniti. Il triangolo resta quello del browser: e' un
   affordance standard, e riscriverlo sarebbe reinventare un comando che tutti
   riconoscono. */
.gruppo details { margin-top: var(--passo-2); }
.gruppo summary { font-size: var(--tipo-nota); line-height: var(--interlinea-riga); color: var(--tenue); cursor: pointer; padding: var(--passo-1) 0; }
.gruppo summary:focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
.gruppo details[open] summary { margin-bottom: var(--passo-2); }
```

- [ ] **Step 8: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_app_js.py tests/test_stile.py -q
```

Atteso: PASS su entrambi i file.

- [ ] **Step 9: Commit**

```bash
git add meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git commit -m "feat(ui): il pannello apre su cio' che la corsa ha cambiato

/api/schema manda il predefinito di ogni campo e l'interfaccia lo buttava via,
in un prodotto la cui tesi e' la riproducibilita'. Adesso i campi spostati
stanno in cima e dichiarano da che cosa, e gli altri si richiudono in un
details. Il taglio e' funzione del dato: un elenco base/avanzato inventato qui
sarebbe una classificazione che nessun dato sostiene."
```

---

## Task 7: La passata di rifinitura

I minori della critica che hanno un rimedio misurabile. **Due rilievi vengono esclusi di proposito**, e la ragione e' scritta qui perche' non tornino a ogni giro:

- **`.stato-mai-eseguito` senza regola CSS non e' un difetto.** `.step-stato` da' gia' `color: var(--tenue)` a tutti gli stati, e «mai eseguito» ha per ruolo di colore proprio quello neutro. Una regola in piu' direbbe la stessa cosa due volte.
- **`preserveDrawingBuffer: true` con `cattura()` mai chiamata resta.** Il costo e' una copia per fotogramma, la funzione serve a catturare le viste che finiscono in appendice, e toglierla per un guadagno non misurato romperebbe una strada dichiarata nel prodotto. Va misurata prima, non tolta adesso.

**Files:**
- Modify: `meshrec/src/meshrec/ui/stile.css` (token `--bordo-comando`, `.registro:empty`, colonne flessibili)
- Modify: `meshrec/src/meshrec/ui/index.html` (nome accessibile del registro)
- Modify: `meshrec/src/meshrec/ui/app.js:147-159` (scorrimento del registro)
- Test: `meshrec/tests/test_stile.py`, `meshrec/tests/test_app_js.py`

**Interfaces:**
- Consumes: niente.
- Produces: niente di consumato da altre task.

- [ ] **Step 1: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_stile.py`:

```python
def _luminanza(esadecimale: str) -> float:
    """Luminanza relativa sRGB, WCAG 2.x."""
    canali = [int(esadecimale[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def _rapporto(primo: str, secondo: str) -> float:
    a, b = _luminanza(primo), _luminanza(secondo)
    chiaro, scuro = max(a, b), min(a, b)
    return (chiaro + 0.05) / (scuro + 0.05)


def _token(nome: str) -> str:
    testo = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    trovato = re.search(rf"{nome}:\s*(#[0-9a-fA-F]{{6}})", testo)
    assert trovato is not None, f"il token {nome} non e' piu' un esadecimale in :root"
    return trovato.group(1)


def test_il_contorno_dei_comandi_regge_anche_sulla_superficie_del_passaggio():
    """Il commento difende --bordo-comando sopra 3:1 su due superfici (WCAG
    1.4.11) e ne dimentica una terza: al passaggio del puntatore il fondo di un
    bottone diventa --evidenza, e li' lo stesso contorno misurava 2,88. E' il
    contorno che quel commento chiama «l'unico indizio del comando»: sotto
    soglia proprio nel momento in cui si sta per premere."""
    bordo = _token("--bordo-comando")
    # --evidenza e' --accento all'8% sopra la superficie, composto qui.
    superficie, accento = _token("--superficie"), _token("--accento")
    composto = "#" + "".join(
        f"{round(int(superficie[i:i + 2], 16) * 0.92 + int(accento[i:i + 2], 16) * 0.08):02x}"
        for i in (1, 3, 5)
    )
    misura = _rapporto(bordo, composto)
    assert misura >= 3.0, f"il contorno misura {misura:.2f} sul fondo del passaggio, sotto 3:1"


def test_le_colonne_laterali_non_superano_la_vista():
    """18rem + 22rem sono 640 px di cornice fissa: fra ~961 e ~1250 px la
    colonna centrale — la vista 3D, la ragione per cui l'applicazione esiste —
    era piu' stretta di entrambe le laterali. A 200% su uno schermo grande si
    atterra esattamente in quella fascia."""
    testo = _senza_commenti()
    trovato = re.search(r"\.tre-zone\s*{[^}]*grid-template-columns:\s*([^;]+);", testo)
    assert trovato is not None, "la griglia delle tre zone non si trova piu'"
    assert "minmax(" in trovato.group(1), (
        f"le laterali sono ancora a larghezza fissa: {trovato.group(1).strip()}"
    )


def test_il_registro_vuoto_non_e_una_striscia_bordata():
    """Vuoto rendeva un rettangolo alto 1 px con un contorno intorno, che si
    legge come un campo di testo rotto. .conteggi:empty ha gia' lo stesso
    rimedio da un giro."""
    assert ".registro:empty" in _senza_commenti(), "il registro vuoto resta una striscia"
```

E in coda a `meshrec/tests/test_app_js.py`:

```python
def test_il_registro_ha_un_nome_accessibile():
    """role="log" con tabindex="0" e nessun nome: il lettore di schermo
    annunciava «log» e basta. L'h2 accanto e' adiacente, non associato."""
    markup = _senza_commenti_html(_markup())
    elemento = _elemento(markup, "registro")
    assert "aria-labelledby=" in elemento, f"raggiungibile e senza nome: {elemento}"
    assert 'id="titolo-registro"' in markup, "il titolo a cui puntare non esiste"


def test_il_registro_non_strappa_in_fondo_chi_sta_leggendo():
    """Lo scorrimento era incondizionato, due volte al secondo per i 34 secondi
    di uno step: chi leggeva a meta' veniva riportato in fondo a ogni riga."""
    corpo = _modulo().split('flusso.addEventListener("riga"', 1)[1].split("\n});", 1)[0]
    assert "scrollTop = registro.scrollHeight" in corpo, "il registro non segue piu' la coda"
    assert "clientHeight" in corpo, "lo scorrimento e' tornato incondizionato"
```

- [ ] **Step 2: Eseguire i controlli e verificare che falliscano**

```bash
uv run pytest tests/test_stile.py tests/test_app_js.py -q -k "contorno_dei_comandi or colonne_laterali or registro_vuoto or nome_accessibile or non_strappa"
```

Atteso: FAIL su tutti e cinque. `test_stile.py` va integrato con `import re` in cima se non c'e' gia' (c'e').

- [ ] **Step 3: Scurire il token del contorno e aggiornare i numeri del commento**

In `meshrec/src/meshrec/ui/stile.css`, sostituire:

```css
  --bordo-comando: #948e85;
```

con `#8a8479`, e riscrivere il commento che lo precede con i rapporti ricalcolati (verificati a mano: 3,71 su `--superficie`, 3,56 su `--sfondo`, 3,29 sul fondo del passaggio):

```css
  /* Linee. --bordo separa (1,41:1, non porta informazione); --bordo-comando
     disegna il contorno di cio' che si puo' toccare. Il riempimento dei campi e
     dei bottoni non li distingue dallo sfondo, quindi l'unico indizio del
     comando e' quel contorno, e WCAG 1.4.11 chiede 3:1.
     Le superfici sono TRE e non due: al passaggio del puntatore il fondo di un
     bottone diventa --evidenza, e li' il valore di prima misurava 2,88 —
     sotto soglia proprio nell'istante in cui si sta per premere. Ricalcolati:
     3,71 su --superficie, 3,56 su --sfondo, 3,29 su --evidenza. */
  --bordo: #ddd9d2;
  --bordo-comando: #8a8479;
```

- [ ] **Step 4: Dare un nome al registro**

In `meshrec/src/meshrec/ui/index.html`, sostituire `<h2>Registro</h2>` (quello che precede `#registro`) con:

```html
    <h2 id="titolo-registro">Registro</h2>
```

e aggiungere `aria-labelledby="titolo-registro"` all'elemento `#registro`:

```html
    <div class="registro" id="registro" role="log" aria-live="off" tabindex="0"
         aria-labelledby="titolo-registro"></div>
```

`aria-labelledby` e non `aria-label`: il nome accessibile resta la stessa parola che si legge a video, e non ne esistono due da tenere allineate.

- [ ] **Step 5: Togliere il contorno al registro vuoto e rendere flessibili le colonne**

In `meshrec/src/meshrec/ui/stile.css`, dopo la regola `.registro:focus-visible`:

```css
/* Vuoto era un rettangolo alto un pixel con un contorno intorno, che si legge
   come un campo di testo rotto. Stesso rimedio di .conteggi:empty: si toglie
   cio' che si vede, non l'elemento. */
.registro:empty { border: none; padding: 0; }
```

e sostituire la riga della griglia:

```css
.tre-zone { display: grid; grid-template-columns: 18rem 1fr 22rem; flex: 1; min-height: 0; }
```

con:

```css
/* minmax e non due larghezze fisse: 18rem + 22rem sono 640 px di cornice che
   non cede, e fra ~961 e ~1250 px la colonna centrale — la vista 3D, la ragione
   per cui l'applicazione esiste — restava piu' stretta di entrambe le laterali.
   A 200% di ingrandimento su uno schermo grande si atterra esattamente li'.
   Un punto di rottura in piu' avrebbe risolto una fascia sola; cedere le
   laterali risolve tutte le larghezze intermedie con una riga. */
.tre-zone { display: grid; grid-template-columns: minmax(12rem, 18rem) 1fr minmax(16rem, 22rem); flex: 1; min-height: 0; }
```

- [ ] **Step 6: Scorrere il registro solo per chi era gia' in fondo**

In `meshrec/src/meshrec/ui/app.js`, nel gestore `flusso.addEventListener("riga", ...)`, sostituire il corpo con:

```js
flusso.addEventListener("riga", (evento) => {
  const registro = document.getElementById("registro");
  // Letto PRIMA di appendere: dopo, scrollHeight e' gia' cresciuto e la
  // risposta e' sempre «no».
  // La soglia di due unita' assorbe l'arrotondamento subpixel che i browser
  // fanno su un contenitore che scorre: senza, «in fondo» risulterebbe falso
  // per una frazione di pixel e il registro non seguirebbe mai la coda.
  const inFondo =
    registro.scrollTop + registro.clientHeight >= registro.scrollHeight - 2;
  const riga = document.createElement("div");
  riga.className = "riga-log";
  riga.textContent = JSON.parse(evento.data);
  registro.append(riga);
  // Il registro cresceva senza tetto: una corsa lunga lascia nel DOM ogni riga
  // che il sottoprocesso ha scritto, e nessuna veniva mai tolta. Il tetto e'
  // sulle righe e non sui caratteri perche' e' cio' che si conta guardando, e
  // le piu' vecchie escono dalla testa, che e' il verso in cui si legge un log.
  while (registro.childElementCount > RIGHE_DEL_REGISTRO) registro.firstElementChild.remove();
  // Solo per chi ci era gia'. Incondizionato, riportava in fondo due volte al
  // secondo per i 34 secondi di uno step: la riga che si stava leggendo veniva
  // strappata via a meta'.
  if (inFondo) registro.scrollTop = registro.scrollHeight;
});
```

**Da fare nello stesso passo:** il DOM finto non espone `clientHeight`, quindi la somma varrebbe `NaN` e `inFondo` sarebbe sempre falso — un banco che non puo' vedere lo scorrimento avvenire. Aggiungere a `_DOM` in `tests/test_app_js.py`, dentro `class Elemento`, accanto a `get scrollHeight()`:

```js
  get clientHeight() { return this.figli.length; }
```

(Verificato in pre-flight: nessun controllo preesistente asserisce `scrollTop === scrollHeight`, quindi la riga non ne rompe nessuno.)

- [ ] **Step 7: Eseguire i controlli e verificare che passino**

```bash
uv run pytest tests/test_stile.py tests/test_app_js.py -q
```

Atteso: PASS su entrambi i file.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/app.js meshrec/tests/test_stile.py meshrec/tests/test_app_js.py
git commit -m "fix(ui): il contorno regge sulla terza superficie, e il registro ha un nome

Il commento difendeva --bordo-comando su due superfici e ne dimenticava una: al
passaggio del puntatore misurava 2,88, sotto 3:1, proprio quando si sta per
premere. Con lui: il registro prende un nome accessibile e non strappa piu' in
fondo chi sta leggendo, e le colonne laterali cedono invece di lasciare la vista
piu' stretta di entrambe."
```

---

## Task 8: Il comando documentato parte, e un artefatto mancante non e' un guasto

Due rilievi fuori dal perimetro dell'interfaccia, trovati nello stesso giro.

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py:268` (gestori d'eccezione)
- Modify: `meshrec/README.md`
- Modify: `PRODUCT.md` (sezione Operating Context)
- Test: `meshrec/tests/test_server.py`

**Interfaces:**
- Consumes: niente.
- Produces: niente.

- [ ] **Step 1: Verificare che cosa asseriscono oggi i test sulle tratte**

```bash
cd meshrec && grep -n "400" tests/test_server.py | head -30
```

Serve a sapere quali controlli esistenti danno per scontato il 400 su un artefatto mancante. **Questo passo non modifica niente**: e' la lettura che evita di rompere il file al passo successivo.

- [ ] **Step 2: Scrivere il controllo che fallisce**

In coda a `meshrec/tests/test_server.py`:

```python
def test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto(tmp_path):
    """Cliccare uno step mai eseguito faceva sollevare FileNotFoundError fino al
    gestore generico, che risponde 400 e poi rilancia: il browser riceveva la
    risposta giusta e il terminale un traceback ASGI per ogni clic.

    Un artefatto che non c'e' non e' un guasto del server: e' lo stato normale
    di uno step mai eseguito, e ha il proprio codice.
    """
    config = tmp_path / "prova.yaml"
    save_config(PipelineConfig(input=InputConfig(path=tmp_path / "vuota.ply")), config)
    with TestClient(create_app(config), raise_server_exceptions=False) as client:
        risposta = client.get("/api/cloud/1")
    assert risposta.status_code == 404, (
        f"un artefatto mancante risponde {risposta.status_code}"
    )
    corpo = risposta.json()
    assert corpo["errore"] == "FileNotFoundError", f"la forma del rifiuto e' cambiata: {corpo}"
    assert "messaggio" in corpo, f"il rifiuto non dice piu' perche': {corpo}"
```

Se `save_config`, `PipelineConfig`, `InputConfig`, `TestClient` e `create_app` non sono gia' importati in cima a `tests/test_server.py`, aggiungerli agli import esistenti.

- [ ] **Step 3: Eseguire il controllo e verificare che fallisca**

```bash
uv run pytest tests/test_server.py -q -k "artefatto_mai_prodotto"
```

Atteso: FAIL con `un artefatto mancante risponde 400`.

- [ ] **Step 4: Aggiungere il gestore dedicato**

In `meshrec/src/meshrec/app/server.py`, subito **prima** del gestore generico `nessuna_eccezione_verso_il_browser` (riga 268):

```python
    @app.exception_handler(FileNotFoundError)
    async def artefatto_mancante(_richiesta, errore: FileNotFoundError):
        # Un artefatto che non c'e' non e' un guasto del server: e' lo stato
        # normale di uno step mai eseguito, ed e' cio' che l'interfaccia
        # gia' sa leggere («nessun artefatto per questo step»).
        #
        # Senza questo gestore la FileNotFoundError arrivava a quello generico,
        # registrato su Exception: Starlette lo esegue dentro
        # ServerErrorMiddleware, che manda la risposta e poi **rilancia**
        # l'eccezione perche' il server la registri. Il browser riceveva la
        # risposta giusta e il terminale un traceback completo per ogni clic su
        # uno step non ancora eseguito. Registrato sul tipo, il rifiuto passa
        # invece da ExceptionMiddleware, che non rilancia.
        #
        # La forma del corpo resta la stessa del gestore generico, cosi'
        # ragioneDelRifiuto la legge senza sapere che e' successo.
        return JSONResponse(
            status_code=404,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )
```

- [ ] **Step 5: Eseguire i test del server e sanare le assunzioni che cambiano**

```bash
uv run pytest tests/test_server.py -q
```

Atteso: PASS. Ogni controllo preesistente che asseriva `400` su un artefatto mancante va portato a `404`: il codice e' cambiato di proposito, la forma del corpo no. Ogni controllo che asserisce 400 su un rifiuto **diverso** da un file mancante resta com'e'.

- [ ] **Step 6: Documentare il comando che avvia il programma**

In `meshrec/README.md`, aggiungere una sezione (adattando il livello di titolo a quelli gia' presenti nel file):

```markdown
## Avviare l'interfaccia

```bash
uv run meshrec serve lab.yaml
```

Il percorso della configurazione e' obbligatorio: e' la corsa su cui
l'interfaccia lavora, e senza non c'e' niente da mostrare. `--port` sceglie la
porta, `--no-browser` non apre il browser.

Le configurazioni gia' pronte nel repository sono `lab.yaml` (il caso studio),
`muro.yaml` (il muro sintetico) e `prova-interfaccia.yaml` (una corsa vuota, per
guardare l'interfaccia senza calcolare niente).
```

In `PRODUCT.md`, sezione **Operating Context**, sostituire la frase che cita il comando con:

```markdown
Applicazione **locale**, utente singolo, nessuna autenticazione, nessun server
remoto. Si avvia da riga di comando con `uv run meshrec serve <configurazione>.yaml`
e apre il browser. Il percorso della configurazione e' obbligatorio: e' la corsa
su cui l'interfaccia lavora.
```

Le altre occorrenze di `uv run meshrec serve` senza argomento in `PRODUCT.md` vanno corrette allo stesso modo:

```bash
grep -rn "meshrec serve" PRODUCT.md meshrec/README.md meshrec/docs/
```

- [ ] **Step 7: Verificare che il comando documentato parta davvero**

```bash
cd meshrec && uv run meshrec serve prova-interfaccia.yaml --no-browser --port 8799
```

Atteso: stampa `MeshRec in ascolto su http://127.0.0.1:8799/`. Fermarlo con Ctrl-C, oppure `pkill -f "meshrec serve"` da un'altra shell.

- [ ] **Step 8: Commit**

```bash
git add meshrec/src/meshrec/app/server.py meshrec/tests/test_server.py meshrec/README.md PRODUCT.md
git commit -m "fix(server,docs): un artefatto mancante e' un 404, e serve vuole la configurazione

FileNotFoundError arrivava al gestore generico, registrato su Exception:
Starlette lo esegue in ServerErrorMiddleware, che risponde e poi rilancia, e il
terminale prendeva un traceback per ogni clic su uno step mai eseguito.
E il comando documentato in PRODUCT.md non parte: serve vuole un percorso di
configurazione posizionale, e il README non lo nominava affatto."
```

---

## Chiusura

- [ ] **Rieseguire la suite intera**

```bash
cd meshrec && uv run pytest -q
```

- [ ] **Guardare l'applicazione girare** (skill `run`, oppure a mano)

```bash
cd meshrec && uv run meshrec serve lab.yaml --no-browser --port 8799
```

Da controllare a video, nell'ordine: cliccare uno step mai eseguito (didascalia d'attesa, poi «nessun artefatto per questo step», e **nessun traceback nel terminale**); eseguire uno step e guardare la riga dell'esito con la durata; annullarne uno e leggere la frase diversa; aprire lo step 2 e battere `abc` in un estremo del ritaglio; aprire la Galleria su `lab_crop` e leggere le grandezze senza scorrere.

- [ ] **Rimisurare**

```
/impeccable critique meshrec/src/meshrec/ui/index.html
```

Il punteggio fra giri con valutatori diversi non e' una misura: cio' che conta e' quali rilievi risultano chiusi.

---

## Self-Review

**1. Copertura della spec.** I due P0 → Task 1 e 2. I tre P1 → Task 3 (campi del ritaglio), 4 (Galleria), 5 (scritture irreversibili). La scelta dell'utente sulla divulgazione progressiva → Task 6. I minori con un rimedio misurabile (contrasto sulla terza superficie, nome accessibile del registro, `.registro:empty`, colonne che non cedono, scorrimento del registro, accenti nelle stringhe mostrate) → Task 5 e 7. I due rilievi fuori perimetro (500 sul server, comando documentato che non parte) → Task 8.

**Rilievi della spec deliberatamente non pianificati, con la ragione:** `EventSource` senza `onerror` e `caricaStato()` senza `.catch` — sono rilievi reali di Riley, ma appartengono alla famiglia «la pagina davanti a un server morto», che merita un giro suo con una spec propria invece di una coda in fondo a questo. `/api/cluster` senza comando, le scorciatoie da tastiera, `inquadra` non legata, i 1000 scatti del cursore — sono la persona Alex, cioe' funzionalita' nuova, non difetti: vanno da `superpowers:brainstorming`, non da un piano di chiusura. `analysis.material` non modificabile e le descrizioni mancanti in `config.py` toccano il modello, non l'interfaccia. `.stato-mai-eseguito` e `preserveDrawingBuffer` sono esclusi con la ragione scritta in testa alla Task 7.

**2. Segnaposto.** Nessun «TBD», nessun «gestire gli errori», nessun «simile alla Task N». Ogni passo che tocca codice porta il blocco vero. Il solo passo senza codice e' il primo della Task 8, che e' un `grep` di lettura e lo dichiara.

**3. Coerenza dei tipi.** `nomeDelloStep(numero, steps)` e' definita nella Task 1 con quella firma e chiamata con quella firma nella Task 2 (`nomeDelloStep(numero, ultimiSteps)`) e dentro `esitoDellaCorsa`. `colonneOrdinate(colonne, ordine)` torna `Array<{colonna, indice}>` ed e' consumata con `{ colonna }` e `{ colonna, indice: originale }` nella stessa task. `cambiatoDalPredefinito(valore, predefinito)` e' chiamata con la stessa coppia in `campoParametro` e in `gruppoDelBlocco`. `segnalaCampo(input, messaggio, rifiuto)` e' quella gia' esistente e non cambia firma. `spegniLeEsecuzioni(inCorso)` e `azioniDelloStep(numero, ordine)` sono definite e chiamate nella sola Task 5. `mostraEsperimento` gia' torna un booleano (`app.js:1030-1050`), che e' cio' su cui la Task 4 innesta `.then((scritto) => ...)`.

**Vincolo del banco, verificato su tutte le funzioni nuove:** ognuna e' di primo livello e nessuna ha una graffa in prima colonna nel proprio corpo, quindi `_sorgente_di()` le estrae per intero.
