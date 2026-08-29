# Fase 8 — Il prior estende ciò che misura

**Data:** 29 agosto 2026
**Ticket:** [#142](https://github.com/maeurong/Tesi/issues/142), [#143](https://github.com/maeurong/Tesi/issues/143), figli della mappa [#127](https://github.com/maeurong/Tesi/issues/127)
**Sottosistema:** A della decomposizione di Fase 8

## Perché

La Fase 8 aggiunge a MeshRec un modello a telaio con sezioni a fibre, accanto al solido as-built che resta il modello della tesi. Quel telaio nasce dalle membrature che `wall.prior` già scompone.

Ma il prior oggi **misura più di quanto restituisca**, e ciò che tiene per sé è esattamente ciò che il telaio pretende. Questo sottosistema non aggiunge misure: fa uscire quelle che esistono, e ne aggiunge una sola nuova — il nodo in cui due membrature si incontrano.

Non tocca solutori, interfaccia, materiali. Cambia `12_wall.json` e nient'altro.

## Che cosa esiste oggi, verificato

**`wall.misura` affetta già la membratura.** `_FETTE_LUNGO_ASSE = 20` fette equispaziate lungo l'asse; per ciascuna calcola le due estensioni trasversali e le accumula in `per_fetta`. Da quelle ricava `medie` (che alimenta `volume`) e `sezione_dispersione`. **`per_fetta` è una variabile locale e non esce dalla funzione.**

La scelta delle fette equispaziate è già argomentata nel codice: «fette a passo uguale, e non quantili, perché una fetta vuota deve restare vuota invece di essere riempita da punti di un'altra». E la fetta povera è già decisa: `if dentro.sum() < 4: continue`, nessuna misura inventata.

**`wall.misura` costruisce già la base del piano di sezione.** `e1` ed `e2`, ancorate alla terna del pezzo e non alla SVD della regione, con la ragione scritta accanto: «due membrature parallele devono avere lo stesso piano di sezione, o le loro sezioni non sono confrontabili». Anche questa resta locale.

**`hexa.taglia_giunzioni` trova già le coppie che si incontrano.** Restituisce, per ogni incontro, `maggiore`, `minore`, `accorciamento`, `cuneo`, `posizione_tolleranza`. Il ruolo lo decide il **Ruling AD** — cede la membratura il cui asse baricentrico entra nell'altra — tramite `_asse_baricentrico_invaso`, con lo spareggio per area già incorporato nell'ordinamento. Solleva su attraversamento da parte a parte e su contenimento completo, con diagnosi distinte.

**Tetraedri e membrature vivono nello stesso sistema di coordinate.** Il prior misura `02_segmented.ply`; `abaqus.align_to_axes` interviene solo allo step 11.

## Che cosa cambia

### 1. Le sezioni di fetta escono dalla funzione

`Membratura` acquista tre campi, tutti con predefinito perché `pipeline._ricostruisci_membrature` costruisce l'oggetto per parola chiave e non deve rompersi:

- `sezioni_fette` — le estensioni misurate fetta per fetta.
- `quote_fette` — la coordinata lungo l'asse del centro di ciascuna fetta, misurata da `origine`. Una sezione senza la propria stazione non colloca nulla.
- `base_sezione` — le due righe `e1` ed `e2` del piano di sezione.

Il numero di fette **non diventa un parametro**. `_FETTE_LUNGO_ASSE` resta una costante e la sua docstring resta vera: «non è un parametro di elaborazione: è la risoluzione con cui si guarda una grandezza già definita». Le fette misurate saranno gli elementi del telaio, uno a uno — deciso in #142, e la proprietà che ha deciso è che **non esiste un numero da tarare**, quindi non serve lo studio di convergenza che nessuna fonte pubblica.

Le fette scartate perché povere **non lasciano un buco**: `quote_fette` dice a quale stazione ogni sezione appartiene, quindi una fetta mancante è visibile come una quota assente e non come una sezione spostata.

### 2. Il prior scrive le nuove misure

Le tre grandezze entrano in `12_wall.json`, dentro la voce di ciascuna membratura, con i nomi dei campi.

### 3. L'adiacenza diventa una misura del prior

La scoperta delle coppie si estrae dal punto in cui vive oggi e va **in un posto solo**, che sia il prior sia `hexa` chiamano. `hexa.taglia_giunzioni` continua a fare il proprio mestiere — il taglio — e smette di essere l'unico luogo in cui si sa chi incontra chi.

Il prior scrive l'adiacenza in `12_wall.json` come elenco di incontri, ciascuno con gli indici delle due membrature e il ruolo deciso dal Ruling AD.

**Il soffitto si eredita.** Attraversamento da parte a parte e contenimento completo continuano a sollevare, con le stesse diagnosi. La via d'aggiornamento resta quella già nominata in `hexa.taglia_giunzioni`: le operazioni booleane di gmsh, valutate e scartate in `docs/fase-4-prior-telaio.md`.

### 4. Il nodo di giunzione, e la sua distanza

È l'unica misura nuova. Su una geometria rilevata gli assi di due membrature che si incontrano **non si intersecano quasi mai**: passano vicini e si scansano.

Il nodo è la **proiezione del minore sull'asse del maggiore** — il traverso continuo con il montante che vi si innesta, che è la convenzione del calcolo strutturale e coincide col ruolo che il Ruling AD ha già assegnato.

**La distanza fra l'asse proiettato e quello misurato va scritta accanto al nodo.** Non è un dettaglio: uno spostamento silenzioso sarebbe una correzione della geometria rilevata spacciata per la geometria rilevata, cioè l'opposto dello scopo del programma. Se un montante deve spostarsi di quaranta millimetri per raggiungere l'asse del traverso, quel numero si vede.

La distanza è candidata a diventare una soglia di `core/soglie.py`, ma **non si ratifica qui**: quel registro pretende una fonte esterna e questa grandezza non ce l'ha ancora. Per ora si misura e si mostra.

## Compatibilità all'indietro

`runs/muro/` e `runs/lab_crop/` sono corse di riferimento in sola lettura, e i loro `12_wall.json` sono stati scritti senza le chiavi nuove. Chi rilegge un prior vecchio:

- **non deve rompersi**;
- **non deve fabbricare** ciò che nessuno ha misurato. Assente vuol dire assente, non zero e non una stima.

I due luoghi che rileggono il prior sono `pipeline._ricostruisci_membrature`, che costruisce `Membratura` dal dizionario, e la tratta `/api/wall` del server, che lo serve così com'è.

## Che cosa questo sottosistema non fa

- Non costruisce nessun modello a telaio: le misure servono a chi lo costruirà.
- Non tocca `PipelineConfig`, quindi **non sposta l'impronta** delle ventidue righe dei registri di sweep. `Membratura` è un dataclass di lavoro, non un blocco di configurazione.
- Non tocca la numerazione degli step né gli artefatti degli altri.
- Non decide come le membrature diventino elementi: quello è il sottosistema D.

## Invariante da non rompere

Le ventidue righe di `experiments/muro/registro.jsonl` e `experiments/lab_crop/registro.jsonl` devono conservare la propria impronta. Questo sottosistema non tocca `PipelineConfig` e quindi non dovrebbe poterla muovere; va verificato lo stesso dopo l'attuazione, perché è l'invariante che governa tutta la Fase 8.
