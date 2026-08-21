# Task 14 -- report

Stato: **DONE_WITH_CONCERNS**

Commit:
- `a00c91a` -- `feat(fase-4): step 12, caselle dei modelli e pannello di confronto nell'interfaccia`

(worktree `fase-4-materiale`, branch `worktree-fase-4-materiale`)

## F1-F3 -- verificate nel codice, poi applicate

- **F1** (bloccante) -- confermato: `illeggibile` non e' mai stato un identificatore di
  `app.js`. Grep sul modulo prima di scrivere: una sola occorrenza, dentro un commento (riga
  479, «Fuori scala si comporta come illeggibile»). Le due funzioni del corpo del brief
  (`caricaPrior`, `caricaConfronto`) sono state scritte con `corpo == null`, l'idioma gia' in
  uso (`app.js:598`, `:822`), non con `corpo === illeggibile`. Test dedicato aggiunto
  (`test_nessuna_lettura_di_illeggibile_nel_modulo`) che fallisce se la stringa `"illeggibile"`
  torna a comparire nel sorgente eseguibile del modulo.
- **F2** (serio) -- l'asserzione `... or True` del corpo non e' stata scritta. Il test
  `test_lo_stato_vuoto_del_prior_e_nel_markup_e_non_lo_fabbrica_il_modulo` usa la proprieta'
  vera prescritta dalla correzione: estrae il corpo di `caricaPrior` ed asserisce
  `'getElementById("prior-vuoto")' in corpo` e `"createElement" not in corpo`.
- **F3** (serio) -- il `while ((await (await fetch("/api/run")).json()) && false) break;` non e'
  stato scritto. Implementata `attendiFineComando()`, che risolve sul primo evento SSE `"stato"`
  con `in_corso: false` sullo stesso `flusso` che il pannello degli step gia' guarda, poi si
  toglie da sola come ascoltatore. Usata sia nel ciclo dei due modelli sia nel bottone «Calcola
  il prior». Due test la mettono alla prova (vedi sezione Mutazioni).

## F4/F5 -- lette, non riverificate a naso dove F5 lo garantiva

- `"12_wall": "Prior geometrico"` aggiunta a `ETICHETTE`; `disegnaStep` non e' stata toccata,
  regge dodici voci leggendo `steps.length` come F5 affermava.
- Il corpo di un errore ha `{errore, messaggio}`: gia' cosi' in `ragioneDelRifiuto` (nessun
  cambiamento necessario li'), e nessuna nuova lettura di corpo d'errore aggiunta da questo
  task usa `detail` come chiave primaria.
- `markup.count('class="viewport"') == 1` verificato vero anche dopo le mie modifiche
  (non ho aggiunto un secondo contenitore per il confronto, come richiesto).

## Un difetto della stessa famiglia (F1/F2/F3), trovato nel brief, non coperto da F1-F5:
## lo scanner strutturale di `test_server.py` non passava sul codice del brief

Il brief del corpo scrive i due gestori `calcola-prior`/`genera-modelli` come funzioni freccia
asincrone che contengono `await fetch(` senza mai contenere la sottostringa `superata(`. Questo
non e' della stessa forma esatta di F2/F3 (non e' una guardia resa inerte con `|| true` o
`&& false`), ma e' imparentato: e' codice che *sembra* passare la sorveglianza del progetto sulla
regola dell'ordine, e non la passa. `tests/test_server.py::
test_ogni_tratta_che_interroga_il_server_si_scarta_se_e_stata_superata` estrae **ogni** corpo di
funzione freccia asincrona nel modulo (non solo quelle nominate) e pretende che ognuna che
contenga `await fetch(` contenga anche `superata(`, senza eccezioni per nome (le eccezioni per
nome esistono solo per le funzioni *nominate*, come `annullaLaCorsa`). Copiato cosi' com'e', il
codice del brief avrebbe fatto fallire questo test pre-esistente.

Non era decorazione da aggiungere per zittire lo scanner: c'era una violazione vera dietro.
`mostraMembratureNelViewport` (aggiunta da questo task, vedi sotto) scrive nello stesso viewport
condiviso di `mostraStep`. Se l'utente clicca uno step della pipeline mentre «Calcola il prior»
sta ancora aspettando la fine del comando, la mappa delle membrature -- piu' vecchia di quel
clic -- non deve scrivere sopra la vista che l'utente ha appena chiesto. Corretto catturando
`const ordine = generazione;` **prima** dell'attesa in entrambi i gestori, e passandolo
esplicitamente a `caricaPrior(ordine)`/`caricaConfronto(ordine)` dentro un
`if (!superata(ordine))`.

## Un difetto vero, non annunciato da nessuna sezione del brief, trovato guardando nel browser

`caricaConfronto`, copiato dal corpo del brief, non controllava `risposta.ok` prima di leggere
`corpo[grandezza]`. Alla primissima apertura della pagina (nessuna corsa madre ancora eseguita,
ne' `12_wall.json` ne' `modello.json` in nessuna cartella) `GET /api/compare` rifiuta con **400**
(`report.confronta`, gia' cosi' dal Task 12) e un corpo JSON valido `{"errore", "messaggio"}` --
quindi non e' `corpo == null` a fermarlo, e il pannello solleva un `TypeError` fuori da ogni
catch (`Cannot use 'in' operator to search for 'as-built' in undefined`), visto **davvero** in
console durante la verifica nel browser, non dedotto leggendo. E' esattamente lo stesso genere di
guasto che questo file esiste per impedire su ogni altra tratta (`corpoLetto`, `ragioneDelRifiuto`,
la disciplina `superata`), e non era coperto da nessuno dei miei test finche' non l'ho visto
succedere. Corretto: un ramo `if (!risposta.ok)` che mostra lo stato vuoto del confronto (e' lo
stato normale prima che la prima corsa esista, non un guasto da annunciare nella riga d'errore
globale) invece di proseguire a leggere un corpo di rifiuto come se fosse la scheda del
confronto. Test di regressione aggiunto:
`test_caricaConfronto_non_crolla_prima_che_la_corsa_madre_esista`.

## Una lacuna del brief, colmata: `/api/membrature` non era mai chiamato da nessuna parte

Il corpo del brief aggiunge `mostraNuvolaPerMembratura` a `viewport.js` (Step 6) ma non scrive
mai il codice in `app.js` che chiama `GET /api/membrature` e passa il risultato a quel metodo --
l'unico consumo di quell'endpoint nell'intero progetto sarebbe rimasto assente. Aggiunta
`mostraMembratureNelViewport(ordine)`, chiamata da `caricaPrior` dopo `disegnaMembrature`/
`disegnaScartate` quando il prior e' calcolato: prende le posizioni da `GET /api/cloud/2` (stessa
decimazione, stessa chiave di cache di `/api/membrature` -- `viewport.decimate_file` con gli
stessi argomenti in `server.py`, verificato leggendo il codice) e le etichette da
`GET /api/membrature`, combina le due risposte e le passa a `vista.mostraNuvolaPerMembratura`.
Condivide `apriGeometria`/`ultimaGeometria` con `mostraStep`/`mostraNuvolaDelloStep` (lo stesso
arbitro del viewport, non un contatore nuovo per la stessa domanda). Chiama anche
`riallineaTaglio(null)` dopo il disegno: la mappa delle membrature non ha un comando di taglio
proprio, e senza questa riga il comando del taglio sarebbe rimasto a video puntato su un ingombro
che non e' piu' quello disegnato.

## Un difetto minore, visto nel browser, corretto: «step null in corso»

`stato.step` e' `null` per un comando che non e' uno step della pipeline (`worker.start_comando`,
usata sia dal prior sia dai modelli): la riga «in corso» dell'intestazione, scritta prima di
questo task per i soli step numerati, avrebbe mostrato letteralmente «step null in corso, N s»
al primo clic su «Calcola il prior». Verificato **dal vivo**: prima della correzione il testo
sarebbe stato quello; con la correzione (un ternario su `stato.step !== null`) il browser ha
mostrato «un comando e' in corso, 0 s», poi il registro con la ragione del fallimento (vedi
sotto), poi lo stato tornato normale.

## File toccati

- `src/meshrec/ui/index.html` -- casella dei modelli, `#prior-vuoto`/`#calcola-prior`/
  `#prior-membrature`/`#prior-scartate`, `#confronto`/`#confronto-vuoto`/`#confronto-tabella`.
- `src/meshrec/ui/app.js` -- `ETICHETTE["12_wall"]`, il testo dell'indicatore «in corso» per
  `stato.step === null`, `attendiFineComando`, `caricaPrior`, `disegnaMembrature`,
  `disegnaScartate`, `mostraMembratureNelViewport`, `caricaConfronto` (con il ramo `!risposta.ok`),
  i due gestori dei bottoni (con l'ordine catturato prima dell'attesa e il disable incrociato fra
  i due bottoni -- il worker esegue un solo sottoprocesso, e senza il disable incrociato un clic
  sull'altro bottone durante l'attesa avrebbe sollevato un `RuntimeError` lato server).
- `src/meshrec/ui/viewport.js` -- `mostraNuvolaPerMembratura`, il commento sopra `mostraMesh`
  sulla mesh esaedrica gia' triangolata dal server.
- `src/meshrec/ui/stile.css` -- `.modelli`, `.confronto-tabella`, `#prior-membrature p`,
  `.rifiuto` (bordo a sinistra oltre alla tinta, WCAG 1.4.1).
- `tests/test_app_js.py` -- 4 test strutturali del brief (con F1/F2 gia' applicate), 1 test che
  `"illeggibile"` non torni nel modulo, 3 test funzionali su `caricaPrior` (stato vuoto, prior
  calcolato con mappa nel viewport, risposta superata scartata), 1 test su `caricaConfronto`
  (modelli mancanti nominati), 1 di mia iniziativa sul rifiuto di `/api/compare` prima della
  corsa madre, 1 su `attendiFineComando` in isolamento, 1 di integrazione sul gestore
  `genera-modelli` (il secondo modello non parte prima che il primo finisca).
- `tests/test_stile.py` -- non toccato: le tre sorveglianze esistenti (graffe bilanciate,
  variabili dichiarate, nessun colore fuori da `:root`) passano gia' sulle classi nuove senza
  bisogno di aggiunte.

## Test

Suite completa (`uv run pytest -q`, dalla radice `meshrec/`): letta io stessa, **555 passati**
(baseline dichiarata 543 + 12 nuovi). `-m feasibility`: **8 passati, 1 skipped** (invariato).

### Mutazioni applicate davvero, non solo dichiarate

| Test | Mutazione applicata | Esito osservato |
|---|---|---|
| `test_genera_modelli_aspetta_il_primo_prima_di_lanciare_il_secondo` | `attendiFineComando()` sostituita col `while ((await (await fetch("/api/run")).json()) && false) break;` originale del corpo del brief (F3) | `AssertionError: il gestore non aspetta piu' fra un modello e l'altro` -- uccisa, sul controllo strutturale che precede l'esecuzione |
| `test_attendiFineComando_risolve_solo_al_fronte_di_discesa` | `attendiFineComando` sostituita con `function attendiFineComando() { return Promise.resolve(); }` (risolve subito, ignora il flusso) | `AssertionError [ERR_ASSERTION]: risolve mentre il comando gira ancora` -- uccisa |

Le altre asserzioni nuove leggono lo stato reale di un DOM finto dopo aver eseguito la funzione
vera con risposte controllate a mano (compreso l'ordine di arrivo, per `caricaPrior` con
`ordine`/`generazione` avanzata a meta' della richiesta): una regressione sulla logica che
sorvegliano (il ramo `!corpo.calcolato`, la mappa punti/etichette, `voce.regione + 1`, il ramo
`!risposta.ok` di `caricaConfronto`) le farebbe fallire per costruzione, perche' leggono il
risultato scritto nel DOM finto e non una forma testuale del sorgente.

### Un test scartato durante la scrittura perche' non poteva fallire nel modo giusto

La prima versione di `test_genera_modelli_aspetta_il_primo_prima_di_lanciare_il_secondo` usava
`await Promise.resolve()` ripetuto un numero fisso di volte per far avanzare la coda dei
microtask fra una `fetch` e l'altra. Contando i turni a mano si rompeva in modo silenzioso (il
numero di turni reali dipende da quante promesse annidate il motore deve smaltire, non e' un
dettaglio stabile): la prima esecuzione e' bastata a fallire per un conteggio sbagliato, non per
un difetto del codice. Riscritta con un `aspetta(condizione, messaggio)` che fa girare i
microtask finche' la condizione non e' vera (con un tetto per non restare appesa se
l'implementazione si rompe davvero) -- verificato che la versione riscritta uccide comunque la
mutazione F3 sopra.

## Verifica nel browser

`uv run meshrec serve lab.yaml --no-browser --port 8731` da questo worktree (in background),
poi navigazione reale con l'estensione Chrome.

**Golden path visto:**
1. La colonna ha dodici step, l'ultimo si chiama «Prior geometrico».
2. Prima del calcolo il pannello dice che il prior non c'e' e come ottenerlo (il testo statico
   del markup, uguale a quello che il server manderebbe come `motivo`).
3. Le tre caselle dei modelli: as-built spuntata e disabilitata, estruso/primitive libere,
   bottone «Genera i modelli spuntati» presente.
4. Il pannello del confronto mostra correttamente «Nessun modello parametrico generato» (dopo
   la correzione del difetto trovato qui sotto -- prima, un `TypeError` in console).
5. Un clic su uno step della pipeline (Lettura) apre ancora il suo pannello normalmente: nessuna
   regressione visibile sul codice condiviso toccato da questo task.

**Edge case visti:**
- Clic su «Calcola il prior» con nessuno step ancora eseguito: l'intestazione mostra «un comando
  e' in corso, 0 s» (non «step null in corso»), il comando fallisce dopo ~4 secondi con
  `FileNotFoundError: manca runs/lab_c25/02_segmented.ply: ...` mostrato nel registro, il
  bottone si riabilita, nessun errore in console.
- Clic su «Genera i modelli spuntati» con nessuna casella spuntata: nessuna richiesta di rete
  (il ciclo non ha niente da fare), nessun errore, il pannello del confronto resta coerente.

**Non visto, e va detto:** lo stato «prior calcolato» (membrature colorate nel viewport, una
regione scartata con nome del controllo e numero, il confronto con numeri veri) non e' stato
visto nel browser. `lab.yaml` punta a `../Nuvole di punti/lab_frame.pcd`, che da questo worktree
isolato risolve fuori dall'albero del worktree e non esiste (`ls` conferma: il dato vero sta in
`/Users/mario/GitHub/Tesi/Nuvole di punti/`, un livello sopra la radice di questo worktree, non
raggiungibile con un percorso relativo da qui). Eseguire l'intera pipeline fino allo step 12 sul
dato vero non era comunque alla portata di questa sessione per tempo. Questo stato e' coperto
invece da `test_caricaPrior_disegna_membrature_e_mappa_il_viewport_quando_calcolato`, con corpi
di risposta shape-fedeli a quanto restituiscono davvero `wall.py`/`server.py` (verificato
leggendo `wall.py` righe 712-760 e `server.py` righe 691-736 prima di scrivere il test, non
indovinato).

## Il riporto del Task 13: il ciclo Python di `/api/membrature` sulla corsa reale

**Non misurato in questa sessione.** Per lo stesso motivo del punto sopra: il dato vero
(`lab_frame.pcd`) non e' raggiungibile da questo worktree isolato con un percorso relativo, e
costruire una corsa fino allo step 2 (il minimo per avere `02_segmented.ply` e poter chiamare
`/api/membrature` sul serio) non rientrava nel tempo di questa sessione. Il commento `ponytail:`
lasciato dal Task 13 in `wall.py`/`server.py` resta quindi non verificato sul banco reale: la
decisione se vettorizzare resta aperta per chi ha accesso al dato vero (probabilmente il Task 15,
che lavora fuori da questo worktree o con un percorso che risolve).

## Preoccupazioni

- **DONE_WITH_CONCERNS** e non DONE per due ragioni: (1) un difetto vero trovato guardando nel
  browser (`caricaConfronto` che non controllava `risposta.ok`), non coperto da nessuna sezione
  del brief ne' dai miei test finche' non l'ho visto in console; (2) lo stato «prior calcolato»
  del golden path non e' stato verificato con gli occhi sul dato vero, per l'isolamento del
  worktree rispetto a `../Nuvole di punti/` -- coperto da test funzionali con corpi shape-fedeli,
  non da un browser reale.
- Il riporto del Task 13 sul ciclo Python di `/api/membrature` resta senza misura: nessuno lo ha
  ancora misurato sulla corsa reale, e questa sessione non aveva accesso al dato per farlo.
