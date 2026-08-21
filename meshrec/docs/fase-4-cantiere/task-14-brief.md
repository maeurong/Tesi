> ## LEGGI QUESTO PRIMA DEL RESTO — correzioni vincolanti del 20/08/2026
>
> Il corpo del brief qui sotto e' la prima stesura: contiene **un difetto
> bloccante** e due seri. Dove questa sezione e il corpo divergono, **vale
> questa**.
>
> I due difetti seri hanno la stessa forma, e vale la pena riconoscerla perche'
> e' la piu' insidiosa di tutte: **codice che ha l'aspetto di funzionare e non
> puo' funzionare**, lasciato nel piano accanto alla propria smentita. Un
> `or True` alla fine di un'asserzione. Un `&& false` in una condizione di ciclo.
> Chi copia il blocco e prosegue non arriva mai alla nota che lo corregge.
>
> Se una delle affermazioni qui sotto ti risulta falsa, **fermati e dillo con la
> prova**: in questa fase e' successo otto volte che avesse ragione chi eseguiva
> e non chi scriveva il piano.
>
> ### F1 (BLOCCANTE) — `illeggibile` non esiste
>
> Il corpo scrive `if (superata(ordine) || corpo === illeggibile) return;` in due
> funzioni. **`illeggibile` non e' un identificatore di `app.js`**: compare una
> volta sola in tutto il file, **dentro un commento** (riga 479, «Fuori scala si
> comporta come illeggibile»). Le due funzioni solleverebbero `ReferenceError`
> alla prima risposta ricevuta.
>
> Il sentinella vero e' `undefined`, che `corpoLetto` restituisce nel `catch`
> (`app.js:448-454`), e l'idioma gia' usato nel file e' `if (corpo == null)`
> (`app.js:598`, `:822`) — con `==` e non `===`, per prendere anche il `null`.
>
> ```javascript
>   const corpo = await corpoLetto(risposta);
>   // == e non ===: un corpo intero non e' mai un null legittimo su questo
>   // endpoint, e corpoLetto marca con undefined cio' che non si e' letto.
>   if (superata(ordine) || corpo == null) return;
> ```
>
> ### F2 (SERIO) — un'asserzione che non puo' fallire
>
> Il corpo scrive:
>
> ```python
>     assert "prior-vuoto" not in _senza_commenti_js(_modulo()).split("createElement")[0] or True
> ```
>
> `X or True` vale `True` per qualunque `X`. **Quell'asserzione non puo' fallire
> in nessuna condizione**, e sta in un test la cui docstring promette di
> sorvegliare proprio la lezione della regione d'errore: «uno stato vuoto creato
> nell'istante in cui ci si scrive dentro non preesiste a cio' che annuncia».
> E' decorazione con la forma di un controllo, ed e' peggio di un test assente
> perche' chi legge smette di cercare.
>
> Scrivi la proprieta' vera, che e' «il modulo non crea l'elemento, lo trova»:
>
> ```python
>     modulo = _senza_commenti_js(_modulo())
>     corpo = _sorgente_di("caricaPrior", modulo)
>     assert 'getElementById("prior-vuoto")' in corpo
>     assert "createElement" not in corpo, (
>         "caricaPrior deve trovare lo stato vuoto nel markup, non fabbricarlo"
>     )
> ```
>
> ### F3 (SERIO) — il ciclo dei due modelli e' codice morto
>
> Il corpo scrive `while ((await (await fetch("/api/run")).json()) && false) break;`.
> `X && false` e' sempre falso: il corpo del ciclo **non si esegue mai**, e la
> `fetch` viene emessa e scartata. Il corpo del brief lo dichiara in grassetto
> subito sotto — il che e' onesto — ma lascia nel piano un blocco che si puo'
> incollare senza leggere oltre.
>
> Togli la riga inerte e mettici un segnaposto **che non compili per sbaglio**:
>
> ```javascript
>       await fetch(`/api/model/${tipo}`, { method: "POST" });
>       // DA SCRIVERE: attendere la fine del primo modello prima del secondo.
>       // Il worker esegue un solo sottoprocesso e la seconda POST solleverebbe
>       // RuntimeError. L'attesa si legge dal flusso SSE gia' aperto, sullo
>       // stesso stato che il pannello degli step usa per sapere che una corsa
>       // e' finita. Senza, il secondo modello non parte e l'interfaccia tace.
>       await attendiFineComando();
> ```
>
> cosi' che l'assenza di `attendiFineComando` fermi chi copia, invece di
> lasciar passare un `while` che non fa niente. **Poi scrivila davvero**: e' la
> funzione che rende utilizzabile la generazione dei due modelli, non un
> dettaglio.
>
> ### F4 — cosa e' cambiato nel Task 13, che questo brief non poteva sapere
>
> Il Task 13 e' stato dispacciato con sei correzioni proprie. Due ti riguardano:
>
> - **`/api/step/{numero}/from` ora arriva a 12, non a 11.** Era fermo a 11 in
>   due punti scritti a mano, quindi il dodicesimo step non partiva da «esegui da
>   qui in poi». Tu aggiungi `"12_wall": "Prior geometrico"` alla colonna: senza
>   quella correzione l'utente avrebbe visto la riga dodici restare «mai
>   eseguito» dopo aver premuto il pulsante, senza spiegazione.
> - **Il corpo di un errore ha le chiavi `errore` e `messaggio`**, non `detail`.
>   Se leggi un errore dal server nel lato browser, sono quelle.
>
> ### F5 — quello che nel corpo e' gia' vero, e non va ricontrollato a naso
>
> Verificato nel codice, non ricordato:
>
> - `disegnaStep` (`app.js:67-89`) legge `steps.length` e non conta a mano:
>   **regge dodici voci senza modifiche**;
> - `ETICHETTE` (`app.js:3-9`) arriva a `"11_export"` e non ha `"12_wall"`:
>   l'aggiunta chiesta e' quella giusta;
> - `markup.count('class="viewport"') == 1` e' vero oggi (`index.html:27`,
>   unica occorrenza), quindi il test coglierebbe davvero un secondo contenitore;
> - `_elemento` e `_sorgente_di` hanno la firma con cui il corpo li chiama;
> - i due gestori dello Step 4 mettono `bottone.disabled = true` **prima** della
>   prima `await fetch(`, quindi passano gia' lo scanner di
>   `test_ogni_gestore_che_scrive_dopo_un_attesa_si_difende`
>   (`tests/test_app_js.py:570`).
>
> ---

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

