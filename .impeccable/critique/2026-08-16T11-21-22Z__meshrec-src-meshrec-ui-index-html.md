---
target: meshrec/src/meshrec/ui/index.html
total_score: 21
p0_count: 2
p1_count: 3
timestamp: 2026-08-16T11-21-22Z
slug: meshrec-src-meshrec-ui-index-html
---
Method: dual-agent (A: design review, con ispezione dal vivo in Chrome · B: detector deterministico + misure di contrasto + evidenza dal browser). Nessuna sovrapposizione: A e B non si sono visti, e due volte sono arrivati allo stesso fatto per strade indipendenti.

Bersaglio: `meshrec/src/meshrec/ui/index.html`, con `stile.css`, `app.js` e `viewport.js` come superficie reale. Registro: **product** (il disegno serve il prodotto).

## Design Health Score — giro 3

| # | Euristica | G2 | G3 | Rilievo che tiene fermo il numero |
|---|---|---|---|---|
| 1 | Visibilita' dello stato | 2 | 2 | Nessuno stato di caricamento su nessuna lettura asincrona. Cliccare uno step costa 27-34 s a freddo (R21/R23) e nulla lo dice: per mezzo minuto la vista mostra la mesh dello step precedente, `#conteggi` i suoi conteggi, e il pannello i parametri del nuovo. `EventSource` resta senza `onerror`. |
| 2 | Sistema e mondo reale | 2 | 3 | `#in-corso` scrive `step 9 in corso` — un numero nudo, mentre la colonna accanto mostra i nomi e `ETICHETTE` e' li'. 6 campi su 11 di `SegmentConfig` non hanno `description` in `config.py`, quindi lo spazio dell'aiuto si stampa vuoto. Le metriche non portano unita'. |
| 3 | Controllo e liberta' | 2 | 2 | Nessun annullamento. Ogni `change` su un parametro scrive su disco. `inquadra` (viewport.js:201) e' esportata e legata a niente: dopo un'orbita storta l'unico rimedio e' ricaricare, che ributta via i 27 s di geometria. |
| 4 | Coerenza e standard | 2 | 2 | `.step` ha selezione a due canali; i bottoni della Galleria non hanno nessuno stato scelto. `#registro` ha `tabindex="0"` con otto righe di commento a difenderlo; `#galleria-tabella`, che scorre in orizzontale e non contiene nulla di focalizzabile, non ha niente. `annullaLaCorsa` e' l'unica fetch senza `.catch(serverMuto)`. |
| 5 | Prevenzione dell'errore | 2 | 2 | I sei campi del ritaglio ingoiano l'ingresso non valido in silenzio (app.js:542), e «Applica» poi manda l'ultimo array **valido**: cio' che si scrive sul disco non e' cio' che il campo mostra. I due «Esegui» restano vivi durante una corsa e si affidano al 400 del worker. |
| 6 | Riconoscere invece che ricordare | 2 | 2 | `/api/schema` manda il `default` di ogni campo e l'interfaccia non lo rende: in un prodotto la cui tesi e' la riproducibilita', non c'e' un solo segno di «questo valore e' cambiato dal predefinito». |
| 7 | Flessibilita' ed efficienza | 1 | 1 | Zero scorciatoie. Nessun Invio-per-eseguire sullo step col fuoco. Nessuna selezione multipla. Il cursore del taglio ha 1000 passi: a frecce sono 1000 pressioni. `/api/cluster` e' un endpoint completo e funzionante che nessun comando raggiunge. |
| 8 | Estetica e minimalismo | 3 | 3 | La gerarchia e' piatta e in parte rovesciata: i `.zona h2` stanno a 13px, il gradino piu' piccolo della scala, mentre il corpo sta a 16. Tutti i `.bottone` sono un unico ceto a 14px, quindi «Esegui da qui in giu'» ha lo stesso aspetto del filtro «muro». |
| 9 | Recupero dall'errore | 2 | 2 | La macchina e' ottima — `role="alert"` che preesiste nel markup, rifiuto a tre canali, `ragioneDelRifiuto`, `serverMuto` — ma **una corsa fallita non alza nessun allarme**: `exit_code` e `annullato` arrivano in ogni frame SSE (server.py:679-682) e `app.js` non li legge. |
| 10 | Aiuto e documentazione | 2 | 2 | Gli stati vuoti che ci sono insegnano davvero. Ma «non valido» — il concetto piu' importante dello strumento — non e' spiegato in nessun punto, la maggior parte dei parametri non ha descrizione, e `meshrec/README.md` non nomina mai `serve`. |
| | **Totale** | **20/40** | **21/40** | Acceptable |

**Sul confronto fra i tre numeri.** 25 → 20 → 21 non e' una misura: i tre giri sono stati assegnati da tre valutatori diversi con criteri di severita' diversi, e il giro 1 era per sua stessa ammissione degradato. Il principio 3 del prodotto vale anche qui: non fabbricare precisione che non esiste. Cio' che si puo' dire con certezza e' **quali difetti sono chiusi e quali no**, ed e' scritto sotto.

**Carico cognitivo: 6 falliti su 8 — critico.** Falliti: focus singolo (la colonna destra impila parametri, registro e Galleria della Fase 2, tre lavori diversi in uno scorrimento); blocchi <= 4 (il fieldset `segment` rende 11 campi di fila, `surface` 9, lo step 11 ne rende 12 fra `tet` e `analysis`); gerarchia visiva; scelte minime (il pannello dello step 2 presenta 19 comandi); memoria di lavoro (lo scorrimento orizzontale della Galleria porta via insieme la colonna `impronta` e la didascalia, che sta dentro la scatola che scorre); divulgazione progressiva. Passano: raggruppamento e una-cosa-alla-volta.

## Anti-Patterns Verdict

**Valutazione LLM: non e' slop, e non e' nemmeno vicino.** Passa il test del registro product: un utente pratico di Linear o Raycast si siederebbe qui e si fiderebbe. Una scala di caratteri, un raggio, un accento, tre tinte di stato, due durate di movimento, stack di sistema. Nessun testo in gradiente, nessun vetro decorativo (`--velo` e' una lastra traslucida semplice, senza `backdrop-filter`), nessun blocco metrica-eroe, nessuna griglia di schede uguali, nessuna affordance inventata. Ogni scostamento da un valore predefinito del browser e' argomentato in un commento, e i commenti sono veri.

Il modo di fallire e' l'opposto dello slop: **l'interfaccia e' sotto-disegnata dove il prodotto e' lento, e sovra-ingegnerizzata dove e' gia' corretto.** `app.js` porta tre contatori di generazione indipendenti perche' una risposta tardiva non contraddica mai una didascalia — e poi non mostra nulla per i 27-34 secondi in cui quella risposta arriva.

**Sul divieto delle barre laterali.** Due usi, due giudizi diversi:
- `.step[aria-current="true"]` (stile.css:184): **legittimo**. 2px, su una riga sola, appaiato a `aria-current` e a un cambio di fondo, su un elenco dove i nomi si somigliano davvero (Superficie / Semplificazione / Riparazione). E' un indicatore di navigazione, non un accento.
- `.galleria-tabella tr.fronte` (stile.css:228): **non decorativo, ma difettoso in altro modo**. `fronte` non e' una selezione: e' una **classificazione del dato** (appartenenza al fronte di Pareto), applicata a N righe. Colore e fondo sono i suoi unici due canali — `on_front` non arriva mai all'albero di accessibilita' — e la didascalia «La riga di fronte e' evidenziata» e' inservibile a chi non vede la tinta (WCAG 1.4.1). Peggio, misurato a video: **scorrendo la tabella a destra il filetto `inset` esce dalla vista**, perche' e' ancorato al bordo sinistro della riga. Il doppio canale degrada a tinta sola esattamente quando i numeri diventano visibili.

**Scansione deterministica: pulita, e la pulizia e' verificata.** `detect.mjs --json` su `index.html`, `app.js`, `viewport.js` e sulla cartella intera: `[]`, exit 0, in tutte e quattro le forme. Poiche' un risultato vuoto non si distingue da uno scanner rotto, B ha validato lo strumento con un file di controllo contenente anti-pattern noti: exit 2, 2 rilievi (`overused-font`, `bounce-easing`). Lo scanner funziona; il vuoto e' reale. Nessun `.impeccable/config.json` e nessun `DESIGN.md` sotto `meshrec/`: la pulizia non e' il prodotto di una deroga configurata. Nessun rilievo sul vendored three.js, quindi nessun falso positivo da derubricare.

**Sovrapposizioni visive: non disponibili, e non ce ne sono.** Il preflight di iniezione e' fallito perche' nel corredo di B non esiste nessuno strumento di esecuzione JavaScript, ne' mutante ne' in sola lettura. `live-server.mjs` non e' mai stato avviato e `detect.js` non e' mai stato iniettato. **Nessuna sovrapposizione e' visibile nel browser.** Segnale di ripiego, non risultato parziale. L'evidenza visiva raccolta e' altra: schermate a 1408px e a 700px, lettura della console (zero messaggi, nessun errore), e le misure di contrasto qui sotto.

## Overall Impression

Questo e' un lavoro artigianale serio con un buco preciso. Il sistema visivo e' misurato e le misure reggono; la disciplina sulle corse concorrenti e' migliore di quella di gran parte del software commerciale; il vocabolario di stato e' ricalcolato e non asserito. E poi il prodotto tace nei due momenti in cui l'utente ha piu' bisogno di sentirlo parlare: mentre aspetta mezzo minuto, e quando qualcosa e' andato storto.

La singola occasione piu' grande non e' visiva. `exit_code` e' nel carico SSE da quando esiste il worker; `default` e' in `/api/schema` per ogni campo; `secondi` e' in `run_state`. **Tre informazioni che il prodotto gia' possiede, gia' trasmette al browser, e non dice.** Non serve disegnare niente di nuovo per chiuderle: serve leggerle.

## What's Working

1. **Il vocabolario di stato e' verificato, non asserito.** `steps.run_state` (steps.py:122-154) ricalcola la catena di impronte e ne deriva quattro parole, dove «valido» significa che l'impronta salvata coincide con quella ricalcolata dalla configurazione corrente — non «una volta e' uscito 0». «non valido» come stato di prima classe, sempre visibile, e' raro in qualunque strumento ed e' la primitiva giusta per un prodotto sulla riproducibilita'. L'interfaccia rende esattamente quelle quattro parole e non ne inventa nessuna.

2. **La disciplina sulle corse come proprieta' di disegno.** Tre contatori indipendenti — `generazione`, `ultimaGeometria`, `ultimaBattutaDelCampo` — con la guardia messa uniformemente dopo l'ultimo `await` e prima della prima scrittura. `superata()` e' pura e di primo livello, quindi si prova senza DOM. La conseguenza che l'utente sente: la vista non puo' mostrare la mesh dello step 9 sotto la didascalia dello step 1, e una PUT che ha perso la corsa non puo' resuscitare un valore vecchio dentro la PUT successiva di un altro campo. Quasi tutti i prodotti spediscono questo difetto per sempre.

3. **I rapporti dichiarati nei commenti sono veri.** Ricalcolati tutti e tredici in modo indipendente: undici combaciano alla seconda cifra, due sono scostati di 0,03 e **entrambi in senso conservativo** (il commento dichiara meno di quanto la coppia valga davvero). Un commento che dichiara un numero sbagliato sarebbe peggio di nessun commento; questi sono giusti.

## Priority Issues

### [P0] Nessuno stato di caricamento, e la vista afferma un accoppiamento falso mentre carica
**Che cosa.** Cliccare uno step lancia `ricaricaVista` e `apriDettaglio`. Nessuna delle due scrive niente prima del proprio `await`. Sulla scansione vera `/api/cloud/{n}` costa 27-34 s a freddo. In quella finestra la tela mostra la geometria dello step precedente, `#conteggi` i suoi numeri, e il pannello con `aria-current` gia' il nuovo step. In piu' `apriDettaglio` mette in fila `/api/config` e poi `/api/metrics` (app.js:831-832) senza ragione.
**Perche' conta.** Mezzo minuto e' ben oltre il punto in cui si conclude che il clic non e' passato, quindi si clicca un altro step e si butta via il lavoro. E soprattutto: lo schermo sta **affermando** che i parametri dello step 9 vanno con la mesh dello step 5. E' esattamente il difetto «vista che contraddice la didascalia» che questo codice ha combattuto e vinto ovunque altrove.
**Rimedio.** In `mostraStep`/`mostraNuvolaDelloStep`, prima della fetch: `vista.svuota()` e `#conteggi` a «caricamento dello step N…» (e' gia' `aria-live="polite"`, quindi l'annuncio e' gratis). Stessa guardia `superata()` sul rientro. `aria-busy="true"` su `#viewport`. `Promise.all` al posto dei due await in fila.
**Comando:** `/impeccable harden`

### [P0] Una corsa fallita o annullata non e' annunciata da niente
**Che cosa.** `server.py:679-682` manda `exit_code` e `annullato` in ogni frame `stato`. `app.js:107-141` legge solo `in_corso`, `da_secondi`, `step`, `steps`. A uscita non nulla la riga che pulsa semplicemente sparisce, la regione `role="alert"` resta vuota, e il motivo sta solo in `#registro`, che e' `aria-live="off"` per scelta giusta e verso cui nulla indirizza.
**Perche' conta.** E' lo scenario dell'utente successivo confermato in PRODUCT.md, ed e' il peggiore: si aspetta 34 s, l'animazione si ferma, e non c'e' modo di distinguere «fallito» da «finito». La voce dichiarata dal progetto — *distinguere un esito negativo documentato da un fallimento* — non e' onorabile da un'interfaccia che non annuncia ne' l'uno ne' l'altro.
**Rimedio.** Sul fronte di discesa di `in_corso`: se `annullato`, riga neutra; se `exit_code !== 0`, `dichiaraErrore` con il codice e il rimando alle ultime righe del registro; se `exit_code === 0`, scrivere la **durata misurata** che `run_state` gia' possiede in `secondi`. E' l'unico momento di conclusione onesto e guadagnato che il prodotto ha, e oggi finisce in silenzio.
**Comando:** `/impeccable harden`

### [P1] La Galleria non mostra nessuno dei dati per cui esiste
**Che cosa (misurato a video, `lab_crop`: 11 righe x 8 colonne, 82 KB di risposta).** `#galleria-tabella` sta in una colonna di 22rem, ha 8 colonne `white-space: nowrap`, e apre con l'`impronta` SHA-256 da 64 caratteri. **Quella sola colonna sfonda la barra laterale**, quindi le altre sette sono fuori schermo. Scorrendo a destra compaiono `tetraedri / fuori vincolo / diedro` e insieme spariscono l'`impronta` (le righe perdono identita'), il filetto del fronte, e la didascalia «lab_crop: 11 candidati, 1 sul fronte», che sta dentro la scatola che scorre. Il contenitore non ha `tabindex`: irraggiungibile da tastiera, lo stesso identico difetto che `#registro` ha risolto con otto righe di commento.
**Perche' conta.** Questo pannello **e'** la tabella sperimentale della tesi. Oggi mostra zero delle otto grandezze per cui esiste, e la riga del fronte di Pareto — la risposta all'intera domanda della Fase 2 — e' leggibile solo come una tinta pallida su un hash.
**Rimedio.** Riordinare per questa larghezza: `esito`, errore di spessore, `tetraedri`, fuori vincolo, diedro, durata, assi, e `impronta` **ultima**, troncata a 8 caratteri con il valore pieno in `title`. `tabindex="0" role="region" aria-label` su `#galleria-tabella`, come `#registro`. Portare la didascalia fuori dalla scatola che scorre. Un canale testuale per `on_front` (il server manda gia' il flag). `scope="col"` sui `th` e un `caption`. `aria-pressed` sui bottoni degli esperimenti.
**Comando:** `/impeccable layout`

### [P1] Le scritture irreversibili sono indistinguibili da un filtro
**Che cosa.** Tutti i `.bottone` sono un unico ceto da 14px con lo stesso contorno e lo stesso fondo. «Esegui da qui in giu'» (riscrive gli step N..11, minuti di calcolo), «Applica il ritaglio» (scrive `crop_min`/`crop_max`) e «muro» (carica una tabella in sola lettura) sono visivamente identici. Nessuno dei tre chiede conferma. I due «Esegui» restano abilitati durante una corsa e rispondono con un 400.
**Perche' conta.** Alex non vuole conferme sulle azioni economiche, e oggi non ne ha — ma non ne ha nemmeno su quelle care. Chi arriva dopo non puo' capire dall'interfaccia quale bottone costa 40 ms e quale costa sei minuti e sovrascrive sette artefatti.
**Rimedio.** Una sola variante primaria (riempimento `--accento`, testo bianco: 7,49:1, gia' misurato) per «Esegui questo step». «Esegui da qui in giu'» resta secondario ma dichiara la portata nell'etichetta («Esegui dallo step 9 all'11»). Spegnere entrambi mentre `stato.in_corso` — si fa gia' per `Annulla`, ed e' lo stesso carico. Conferma solo su «da qui in giu'», in linea e non in una finestra modale.
**Comando:** `/impeccable clarify`

### [P1] I campi del ritaglio ingoiano l'ingresso non valido, e poi «Applica» scrive altro
**Che cosa.** `app.js:542`: `if (input.value.trim() === "" || !Number.isFinite(scritto)) return;`. Si scrive `abc` o si svuota un campo e la scatola 3D smette semplicemente di muoversi. Nessun messaggio, nessun `aria-invalid`, nessun contorno rosso — mentre `.campo-rifiutato` e `segnalaCampo` esistono gia' due funzioni piu' in la'. Poi «Applica il ritaglio» manda `valori`, l'ultimo array **valido**: la configurazione scritta sul disco non e' quella che i sei campi mostrano, e il messaggio di successo riporta un conteggio di punti per una scatola che non e' a schermo.
**Perche' conta.** E' il principio 1 del prodotto rovesciato: si mostra un numero, se ne usa un altro, e nessun controllo lo smentisce. E' anche l'unico punto dell'applicazione dove lo stato mostrato e lo stato persistito possono discordare in silenzio.
**Rimedio.** Riusare `segnalaCampo` sui sei campi — la funzione e' gia' generica su `(input, messaggio, rifiuto)`. Marcare il campo e spegnere «Applica» finche' uno dei sei e' marcato. `_estremi_finiti` resta il fermo lato server.
**Comando:** `/impeccable harden`

## Persona Red Flags

**Alex (utente esperto impaziente).** Zero scorciatoie: per eseguire lo step 9 deve cliccare la riga a sinistra e poi attraversare ~1100 px per cliccare «Esegui questo step». Nessuna esecuzione in blocco: `/api/step/{n}/from` fa N→11, non puo' fare 3-6 ne' i soli non validi. I due «Esegui» mentono sulla disponibilita': restano vivi durante una corsa e la risposta e' un 400. Nessun reinquadramento della vista: `inquadra` e' esportata e legata a niente. Il cursore ha 1000 passi, quindi a frecce e' inservibile. E trovera' `/api/cluster` nel pannello di rete: un endpoint completo, con il dizionario `mappe` popolato a ogni `/api/cloud`, per una funzione che nessun comando invoca.

**Sam (lettore di schermo, sola tastiera).** **I 34 secondi sono interamente inudibili**: `#in-corso` non ha `aria-live`, `#registro` e' `aria-live="off"` (giustamente), `exit_code` non e' letto. Inizio, fine e fallimento dell'operazione piu' lunga del prodotto non producono nessun annuncio. `#galleria-tabella` e' irraggiungibile (WCAG 2.1.1, livello A). Le righe del fronte non hanno canale non visivo. Dopo una PUT riuscita `input.value` si riscrive da solo — «9.0» diventa «9» — senza annuncio. Il messaggio di attesa del ritaglio non e' una regione viva: 30 s di niente, poi un risultato. Niente `caption`, niente `scope` sui `th`. **In piu', misurato da B: `#registro` e' l'unico elemento interattivo statico senza nome accessibile** — `role="log"`, `tabindex="0"`, e nessun `aria-label` ne' `aria-labelledby`; l'`h2 Registro` che lo precede e' adiacente ma non associato. A video il lettore annuncia «log» e basta.

**Riley (collaudatore metodico).** Ucciso il server a corsa viva, `EventSource` non ha `onerror`: ritenta in silenzio, `#in-corso` si congela sull'ultimo conteggio ricevuto, `Annulla` resta acceso. L'interfaccia afferma un tempo trascorso che nessuno sta piu' misurando — un numero fabbricato per omissione. Pagina aperta a server spento: `caricaStato()` e' chiamata nuda (app.js:94), unica lettura senza `.catch(serverMuto)`; rifiuto non gestito, elenco vuoto per sempre, zero messaggi. Zero esperimenti: `caricaGalleria` esce in silenzio, ma la didascalia fissa in `index.html:78` continua a descrivere una tabella che non c'e'. Doppio clic su «Applica»: due ritagli da ~26 s girano davvero, il bottone non si spegne mai. **E, misurato da B: due 500 lato server su clic ordinari** — `FileNotFoundError` non gestita in `server.py:490` (`nuvola`) e `server.py:638` (`mesh`) cliccando uno step mai eseguito. L'interfaccia degrada bene («nessun artefatto per questo step»); il server stampa un traceback ASGI per clic.

**Giulia (tesista che non ha mai visto la pipeline — l'utente successivo confermato).** **Il comando documentato non parte.** PRODUCT.md dice `uv run meshrec serve`; `cli.py:66` richiede un `config` posizionale, e `meshrec/README.md` non nomina mai `serve`. Verificato tre volte in modo indipendente: il suo primo contatto col prodotto e' un errore di argparse, prima di qualunque stato vuoto le sia stato promesso. Poi: undici righe che dicono tutte «mai eseguito», nessun segno che si comincia da 1, e il 55% della finestra e' un rettangolo vuoto senza didascalia. «non valido» non e' spiegato da nessuna parte e lo leggera' come «rotto». Il pannello dello step 2 — il primo che le serve — stampa `method`, `outlier_neighbors`, `outlier_std_ratio` come snake_case nudo con lo spazio dell'aiuto vuoto. E dentro lo stesso pannello: `crop_min` dice «si modifica dal file di configurazione», e ~300 px sotto c'e' un fieldset RITAGLIO che lo modifica dall'interfaccia.

## Minor Observations

**Contrasto: undici asserzioni su tredici combaciano, due scostate di 0,03 in senso conservativo.** Ma B ha misurato una coppia che i commenti non coprono: il commento difende `--bordo-comando` sotto WCAG 1.4.11 dichiarandolo sopra 3:1 su «entrambe le superfici» (3,25 e 3,11). Su `.bottone:hover` il fondo diventa `--evidenza`, che e' una **terza** superficie, e li' lo stesso contorno misura **2,88 — sotto 3:1**. E' il contorno che il commento stesso definisce «l'unico indizio del comando». Coppia piu' sottile del sistema: `.conteggi` sopra una zona densa della nuvola, 4,55:1, passa con 0,05 di margine.

**Accenti italiani mancanti nelle stringhe mostrate.** «Qualita superficie», «Qualita volume» (app.js:6-7), «piu numeroso» (config.py:70), «Esegui da qui in giu'». Che i sorgenti siano ASCII e' una convenzione di repository difendibile; le stringhe **proiettate davanti a una commissione** non ereditano quel vincolo.

**Tipografia per il caso proiettato.** Il pavimento della scala e' difeso in un commento, la distribuzione no: 13px porta `.aiuto` (il testo che insegna), `.errore-campo`, `.registro` e tutti e quattro gli `h2`; 14px porta ogni etichetta di bottone, ogni metrica, `.step-stato`, `.conteggi` e il comando del taglio. I titoli strutturali sono il testo piu' piccolo dell'interfaccia e i bersagli da cliccare stanno un gradino sotto il corpo.

**Responsive.** `18rem 1fr 22rem` fa 640 px di cornice fissa. Il solo punto di rottura a `60rem` e' troppo basso: fra ~961 e ~1250 px la colonna centrale — la vista 3D, la ragione per cui l'applicazione esiste — e' piu' stretta di entrambe le barre laterali. Sam a 200% su uno schermo da 2560 px atterra esattamente in quella fascia. Alzare a ~75rem, o barre `minmax(14rem, 18rem)` / `minmax(18rem, 22rem)`.

**Cose piccole.** `#registro` vuoto rende una striscia bordata alta 1px che si legge come un campo di testo rotto: merita lo stesso trattamento che `.conteggi:empty` ha gia' avuto. `.stato-mai-eseguito` non ha nessuna regola CSS, quindi lo stato iniziale di tutti e undici gli step e' l'unico senza ruolo di colore. `preserveDrawingBuffer: true` (viewport.js:13) paga una copia per fotogramma, per sempre, per sostenere `cattura()`, che nessuno chiama. `stato.replace(" ", "-")` (app.js:83) sostituisce solo il primo spazio: corretto per i quattro stati di oggi, silenziosamente sbagliato per un futuro stato di tre parole. Il pannello dello step 10 modifica il blocco `tet`, cioe' i parametri dello step 9, senza che nulla lo dica. Lo scorrimento automatico del registro (app.js:158) strappa in fondo due volte al secondo chi sta leggendo a meta'. `analysis.material` e' un input `readOnly` da 14px contenente il JSON del modello: modulo di Young e densita', le due cose che una tesista strutturale vorra' cambiare per prime, non sono modificabili dall'interfaccia.

**Movimento.** `prefers-reduced-motion` c'e' e copre esattamente le due animazioni a fotogrammi chiave, lasciando in piedi le tre transizioni di solo colore. Corretto: chi ha chiesto meno movimento non ha chiesto meno informazione. Totale del foglio: 2 animazioni, 3 transizioni. Nessun movimento decorativo. Console del browser: zero messaggi, nessun errore.

## Questions to Consider

1. Il codice ha speso tre contatori di generazione e ~80 righe di commento perche' una risposta tardiva non contraddica mai una didascalia — e poi lascia una finestra di 34 secondi in cui vista, conteggi e pannello descrivono dimostrabilmente due step diversi. Perche' l'invariante e' stata imposta contro le **scritture** vecchie e mai contro le **letture** vecchie ancora a schermo?

2. `exit_code` e' nel carico SSE da quando esiste il worker. Che cosa sarebbe costato leggerlo, e che cosa dice che l'unica cosa che l'interfaccia non annuncia mai sia proprio quella che l'utente ha piu' bisogno di sentire?

3. Il principio 3 vieta di inventare una percentuale di avanzamento. Vieta anche di dire «sto leggendo l'artefatto dello step 9»? Rifiutarsi di fabbricare un numero non e' la stessa cosa che rifiutarsi di parlare, e la lettura attuale confonde le due.

4. `report._COLUMNS` e' riusato alla lettera perche' la tabella a schermo non possa divergere dall'appendice stampata. L'istinto e' giusto — ma l'appendice e' una pagina intera e il pannello e' 22rem, e la conseguenza e' che a schermo si vede solo un hash. E' davvero l'**ordine** delle colonne a far parte del contratto con l'appendice, o soltanto l'**insieme**?

5. `/api/schema` porta un `default` per ogni campo, e ogni parametro che l'utente ha cambiato rispetto a quello e' esattamente la storia che la tesi racconta. Perche' l'unica interfaccia costruita intorno alla riproducibilita' non sa mostrare, a colpo d'occhio, che cosa e' stato cambiato?
