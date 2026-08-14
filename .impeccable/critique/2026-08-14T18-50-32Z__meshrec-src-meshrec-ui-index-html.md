---
target: meshrec/src/meshrec/ui/index.html
total_score: 20
max_score: 40
na_heuristics: 
p0_count: 2
p1_count: 3
timestamp: 2026-08-14T18-50-32Z
slug: meshrec-src-meshrec-ui-index-html
---
Method: dual-agent (A: design review · B: detector + evidenza statica). Nessun passaggio nel browser.

Modo: **Operate**. Bersaglio `meshrec/src/meshrec/ui/index.html`, con `stile.css` e `app.js` come superficie reale.

## Design Health Score — giro 2

| # | Euristica | Prima | Dopo | Rilievo che tiene fermo il numero |
|---|---|---|---|---|
| 1 | Visibilita' dello stato | 2 | 2 | `EventSource` senza `onerror`: a server morto la pagina congela e il pallino continua a dichiarare lavoro |
| 2 | Sistema e mondo reale | 2 | 2 | Nomi dei parametri e chiavi delle metriche in inglese di macchina; «non valido» si legge «sbagliato» e significa «da rieseguire» |
| 3 | Controllo e liberta' | 2 | 2 | Nessun annullamento in tutto il prodotto: la PUT del campo e il ritaglio scrivono su disco e non si ritirano |
| 4 | Coerenza e standard | 2 | 2 | `select` per l'asse del taglio ma testo libero per i quattro enum; booleani come parole digitate |
| 5 | Prevenzione dell'errore | 2 | 2 | «Esegui da qui in giu'» riscrive centinaia di MB a un clic, senza conferma e senza dire quanti step tocca |
| 6 | Riconoscere invece che ricordare | 2 | 2 | `/api/schema` manda gia' il `default` di ogni campo e il modulo lo scarta |
| 7 | Flessibilita' ed efficienza | 1 | 1 | Nessuna scorciatoia; lo sweep e il fronte di Pareto, che sono il posizionamento del prodotto, non compaiono |
| 8 | Estetica e minimalismo | 3 | 3 | Il blocco Metriche resta un dump a precisione piena; `input.title` duplica l'aiuto gia' stampato |
| 9 | Recupero dall'errore | 2 | 2 | `caricaStato()` e il flusso SSE sono le due sole strade senza gestione d'errore, e portano su l'intera applicazione |
| 10 | Aiuto e documentazione | 2 | 2 | Nessuna legenda dei quattro stati, nessuna spiegazione delle metriche |
| | **Totale** | **20/40** | **20/40** | Acceptable |

**Carico cognitivo: da 6 falliti su 8 a 4 su 8.** Rientrano «una cosa alla volta» e «divulgazione progressiva». Restano falliti: focus singolo, blocchi <= 4, scelte minime, memoria di lavoro.

## Design Specificity Verdict

Specifica dove decide, generica dove nomina. Le decisioni d'interazione non sono copiabili — il rifiuto della percentuale fabbricata, l'intervallo del cursore derivato dall'ingombro misurato, `role="log" aria-live="off"` perche' TetGen parla per 34 secondi e coprirebbe l'unico annuncio che conta. Il linguaggio testuale del pannello invece parla pydantic dentro un guscio italiano.

**Scansione deterministica:** `detect.mjs --json` su tutti e tre i file, `[]`, exit 0, prima e dopo. Nessun falso positivo da derubricare.

**Evidenza da browser:** non raccolta, in nessuna delle due misure.

## Che cosa e' cambiato fra le due misure

Chiusi: le undici righe adesso sono comandi raggiungibili da tastiera; lo step aperto e' marcato con `aria-current`; la regione `role="alert"` vive nel markup e non viene piu' distrutta; il registro non annuncia piu' addosso; `Annulla` segue la corsa; i parametri numerici hanno un vincolo d'ingresso; il registro ha un tetto.

Aperti dopo la misura d'arrivo, e chiusi subito dopo: l'elenco si ricostruiva a ogni evento e, da quando lo step e' focalizzabile, buttava via il fuoco due volte al secondo.

## Priority Issues residui

- **[P0]** `EventSource` senza `onerror` (`app.js`): a server fermo la pagina afferma per sempre una corsa che non esiste.
- **[P0]** `caricaStato()` non guarda `risposta.ok` (`app.js`): un 500 lascia `undefined` in testata e l'elenco vuoto per sempre, senza un messaggio.
- **[P1]** Il tipo del campo lo decide il valore a runtime e non lo schema: booleani come testo, enum come testo libero, `crop_min` modificabile da vuoto e in sola lettura da pieno.
- **[P1]** Il pannello non dice mai a quale step appartiene: sotto i 60rem le zone si impilano e si scrive con l'elenco fuori schermo.
- **[P1]** «Esegui da qui in giu'» non dichiara cosa riscrive.

## Persona

**Sam:** adesso raggiunge gli undici step, li attiva con Invio e Spazio, sente il rifiuto senza che il registro glielo copra, e sa quale step e' aperto. Restano: `role="application"` sulla tela, l'auto-scorrimento del registro che gli strappa la riga che sta leggendo, i booleani da digitare a parole.

**Alex:** nessuna scorciatoia, nessun ripristino del predefinito, nessun reinquadramento della vista, e il suo lavoro vero — sweep e fronte di Pareto — non e' nell'interfaccia.

**Il tesista successivo:** «non valido» continua a sembrargli un guasto; le metriche gli arrivano come chiavi inglesi a precisione piena; nulla dice che gli step siano ordinati.
