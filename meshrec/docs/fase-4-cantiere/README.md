# Il cantiere della Fase 4

Questa cartella è il **come**, non il **cosa**. Il risultato della fase sta in
`docs/fase-4-prior-telaio.md`; qui c'è il lavoro che lo ha prodotto, conservato
perché una parte non è ricostruibile dalla storia di git.

Non è documentazione da leggere in ordine. Serve a tre cose:

1. **Rispondere a «perché è così».** Il registro porta trentanove decisioni con
   la loro ragione e il costo se sono sbagliate, comprese quelle poi **corrette**
   da una decisione successiva.
2. **Non ripetere lavoro già fatto.** Diverse strade sono state provate,
   misurate e scartate. Chi riprende deve sapere contro cosa confrontarsi.
3. **Dire quanto valgono i numeri.** Ogni misura qui dentro dice quando è stata
   presa e su quale codice. In questa fase è successo tre volte che un numero
   fosse vero quando è stato scritto e falso poche ore dopo.

## Che cosa c'è

| File | Che cos'è |
|---|---|
| `progress.md` | **Il registro.** Ordine cronologico: cosa è stato dispacciato, cosa è tornato, ogni decisione presa e ogni mutazione applicata per verificarla. È il file da aprire per primo. |
| `rulings-fase-4.md` | Le sole righe di decisione estratte dal registro, con il numero di riga d'origine. |
| `setaccio-task-8-15.md` | Il **setaccio**: quarantaquattro difetti trovati nel piano *prima* di eseguirlo, undici bloccanti. Con la prova per ciascuno. |
| `task-N-brief.md` | I requisiti di ciascun task. Da 8 in poi hanno in testa una sezione di correzioni vincolanti che sovrascrive il corpo: il corpo è la prima stesura, la testa è ciò che è stato verificato nel codice. |
| `task-N-report.md` | Cosa ha fatto chi ha eseguito, con le mutazioni applicate e il loro esito. |
| `task-8-fix-*.md` | I giri di correzione del Task 8, che ne ha avuti sei. Il più istruttivo della fase. |
| `correzioni-finali.md` | I ventuno rilievi della revisione finale del ramo, e cosa è stato deciso per ciascuno. |
| `preambolo-dispaccio.md` | Il preambolo obbligatorio di ogni dispaccio. |

I file `review-*.diff` **non** sono conservati: erano pacchetti di revisione, e
`git diff` li rigenera esattamente.

## Le tre cose che varrebbe la pena leggere

**Il Task 8, dal rapporto ai sei giri di correzione.** È partito «conforme con
riserva» ed è passato per quattro difetti che nessuna revisione aveva trovato:
una sovrapposizione d'angolo contata due volte in silenzio, il criterio di taglio
sbagliato su un portale normale, il cuneo dovuto al fuori squadra, e un `*TIE`
che il solutore accettava senza legare il 77% dei nodi. Tre su quattro sono
emersi **eseguendo** il codice su un telaio a quattro membrature invece di
leggerlo. Il quarto solo perché un solutore vero ha letto il deck.

**Il setaccio.** Quarantaquattro difetti trovati leggendo il piano contro il
codice, prima di scrivere una riga. Undici erano bloccanti — fra cui una funzione
che sollevava su ogni insieme di modelli, e una grandezza che il confronto
chiamava «il perno» e che nessuno scriveva. Il costo di trovarli dopo sarebbe
stato molto più alto.

**Il difetto che si ripete.** Undici volte in questa fase un'affermazione scritta
in prosa si è rivelata falsa, in tre varianti: mai eseguita, **scaduta** dopo un
cambio di codice, o misurata sulla **cartella sbagliata**. Ogni volta l'ha
trovata chi eseguiva invece di leggere. La regola che ne è uscita è nel registro
e vale più di qualunque altra cosa qui dentro: *ogni numero o l'hai misurato tu,
adesso, sulla cosa di cui stai parlando, oppure non lo scrivi.*

## Che cosa è stato provato e non funziona

Perché nessuno rifaccia questi due tentativi:

- **PCA sull'occupazione** per separare le membrature per direzione invece che
  per spessore. Due formulazioni, entrambe misurate sulla nuvola vera. Sui centri
  di cella dà anisotropia mediana 0,000 a raggio piccolo e regioni identiche a
  quelle di oggi a raggio 30; invertendo la regola sulle giunzioni arriva a tre
  membrature accettate, ma con sezioni da 47 mm su membrature nominali da
  172-250, cioè **lamine di superficie**. Sui punti veri: anisotropia mediana
  0,087, zero accettate. La ragione è la stessa da due lati: per una sagoma
  **piena** la PCA locale è isotropa nell'interno a qualunque scala, finché il
  raggio non supera la larghezza della striscia — e a quel raggio la giunzione
  prende dentro entrambe. La strada che resta è **l'asse mediale** della sagoma.
- **Allargare la tolleranza del solutore** per legare più nodi dipendenti. A
  30 mm gli avvisi scenderebbero da 24 a 8, ed è stato **rifiutato**: a quella
  scala la tolleranza è dello stesso ordine del passo di mesh, e il solutore
  legherebbe un nodo alla faccia più vicina, che può non essere quella di
  contatto. Un vincolo sbagliato è peggio di un vincolo mancante — quello
  mancante lo conta un numero e lo stampa il solutore, quello sbagliato non lo
  vede nessuno.
