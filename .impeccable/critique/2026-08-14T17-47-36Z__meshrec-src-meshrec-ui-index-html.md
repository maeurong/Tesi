---
target: meshrec/src/meshrec/ui/index.html
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
timestamp: 2026-08-14T17-47-36Z
slug: meshrec-src-meshrec-ui-index-html
---
⚠️ DEGRADED: single-context (il brief del giro 1 vieta esplicitamente di dispacciare sottoagenti; Assessment A e B eseguiti in sequenza nello stesso contesto)

Modo: **Operate**. Bersaglio: `meshrec/src/meshrec/ui/index.html`, con `stile.css` come verita' visiva incumbent e `app.js` letto in sola lettura perche' scrive gran parte del DOM.

## Design Health Score

| # | Euristica | Punteggio | Rilievo principale |
|---|-----------|-------|--------------|
| 1 | Visibilita' dello stato | 3 | Nessuno stato di selezione sullo step aperto; `Annulla` non conferma nulla |
| 2 | Sistema e mondo reale | 3 | Chiavi delle metriche mostrate grezze (`dt`, snake_case inglese) |
| 3 | Controllo e liberta' | 2 | Nessun annulla; rieseguire uno step sovrascrive a valle senza conferma |
| 4 | Coerenza e standard | 3 | Le righe step sono `li` cliccabili, non comandi; l'esito del ritaglio esce in `.aiuto` e non nella riga d'errore |
| 5 | Prevenzione dell'errore | 2 | I campi parametro sono `input` senza `type`: un numero e' testo libero |
| 6 | Riconoscere invece che ricordare | 3 | Ogni parametro porta la propria descrizione inline; manca lo stato di selezione |
| 7 | Flessibilita' ed efficienza | 1 | Zero scorciatoie da tastiera, zero navigazione da tastiera, nessuna azione cumulativa |
| 8 | Estetica e minimalismo | 3 | Il pannello dettaglio elenca tutti i campi in piano, nessuna divulgazione progressiva |
| 9 | Recupero dall'errore | 3 | La ragione del server arriva sempre; dice il problema, quasi mai la mossa successiva |
| 10 | Aiuto e documentazione | 2 | Nessuna spiegazione degli undici step per l'utente successivo confermato |
| **Totale** | | **25/40** | **Acceptable** |

## Design Specificity Verdict

**Autoriale, non intercambiabile.** Il foglio di stile e' il documento piu' specifico del progetto: quasi ogni regola non ovvia porta una ragione misurata (60,6 px di testata, i conteggi che si toccano a 700 px, il rifiuto del tema scuro legato a `0xfbfaf8` in `viewport.js`). I nomi delle classi sono di dominio (`.taglio`, `.conteggi`, `.zona-vista`, `.step-stato`). Nessun contenuto decorativo, nessuna metrica finta, nessun segnaposto. La voce della copia e' quella asciutta dei documenti del progetto.

**Scansione deterministica:** `detect.mjs --json` su `index.html` e `stile.css` restituisce `[]`, zero rilievi.

**Overlay visivi:** non prodotti. Nessun passaggio nel browser in questo giro; le misure a video citate vengono dal giro 16a sullo stesso CSS.

## Priority Issues

- **[P0] Le righe degli step non si raggiungono da tastiera.** `app.js:20-32` crea `li` senza `tabindex` ne' ruolo, con un gestore di click delegato sull'`ol`. Scegliere uno step e' l'azione primaria dell'intera interfaccia: chi non usa il mouse non entra. WCAG 2.1.1, livello A. *Vive in `app.js`.*
- **[P1] Nessuno stato di selezione sullo step aperto.** Il pannello destro cambia, la colonna sinistra no. Chi torna alla pagina dopo trenta secondi non sa quale step sta guardando. Serve una classe o `aria-current="true"` scritta da `app.js` e una regola nel foglio. *Vive in `app.js`.*
- **[P1] Rieseguire uno step sovrascrive gli artefatti a valle senza conferma e senza annulla.** Un click su «Esegui da qui in giu'» butta via il lavoro dal numero in poi. Nessuna guardia, nessun ritorno.
- **[P1] I campi parametro sono `input` senza `type`.** `app.js:541`: un valore numerico riceve una casella di testo libera. Nessun vincolo lato ingresso, nessuna tastiera numerica, nessun passo. La validazione c'e' ma e' tutta a valle, sul server. *Vive in `app.js`.*
- **[P2] Il progresso non e' annunciabile.** `.in-corso` riscrive il proprio testo a ogni evento, cioe' due volte al secondo: una regione viva li' sopra parlerebbe addosso a chi ascolta. Chi usa un lettore di schermo non sa che la macchina lavora. Il rimedio e' congiunto (`index.html` + `app.js`): una regione che porta il solo «step N in corso», e i secondi trascorsi `aria-hidden`.

## Persona Red Flags

**Sam (dipende dall'accessibilita'):** non raggiunge nessuno degli undici step da tastiera. Non sente partire una corsa. Fino a questo giro non poteva neppure scorrere il registro senza mouse — corretto qui. Contrasti tutti misurati e conformi, `aria-invalid` e `aria-errormessage` sui campi rifiutati, `role="alert"` sulla riga d'errore: l'impalcatura ARIA e' buona, la tastiera no.

**Alex (esperto impaziente):** e' l'utente primario di `PRODUCT.md`, apre il programma ogni giorno e conosce a memoria gli undici step. Non riceve una sola scorciatoia. Nessun modo di lanciare la pipeline intera con un tasto, nessun modo di saltare allo step N, nessuna azione cumulativa. Deve puntare e cliccare ogni volta.

**Jordan (prima volta):** e' l'utente successivo confermato di `PRODUCT.md`, e la pagina non gli dice mai che cosa sono gli undici step ne' in quale ordine vanno. Lo stato vuoto insegna una cosa sola («scegli uno step»). Le chiavi delle metriche arrivano grezze e in inglese.

## Minor Observations

- Il comando del taglio non ha un nome di gruppo: `select` e cursore galleggiano sulla vista senza un'etichetta che li unisca.
- Nessuna favicon: il server locale prende un 404 a ogni caricamento. Non corretta apposta — `PRODUCT.md` dichiara che non esiste un'identita' visiva da rispettare, e inventarne una sarebbe fabbricare un fatto.
- I bersagli tattili misurano 37,4 px (`.step`) e 36,2 px (`.bottone`): sopra i 24x24 che WCAG 2.2 2.5.8 chiede in AA, sotto i 44 di 2.5.5, che e' AAA. Il contesto d'uso dichiarato non ha dispositivi tattili.
- `role="alert"` sulla riga d'errore vive dentro `#dettaglio`, che `replaceChildren()` distrugge e ricrea a ogni apertura di pannello: la regione «sempre viva» lo e' solo dentro una sessione di pannello.

## Questions to Consider

- Se l'utente primario conosce a memoria gli undici step, perche' l'unico modo di lanciarne uno e' puntare col mouse una riga che la tastiera non vede?
- Che cosa distingue, a video, «questo step e' aperto» da «questo step e' semplicemente il primo dell'elenco»?
- Se «Esegui da qui in giu'» butta via il lavoro a valle, che cosa lo dice prima del click, e non dopo?
