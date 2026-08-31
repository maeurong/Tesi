# La linea dell'analisi integrata

Il prodotto di tesi si chiude sul deck `.inp`: l'analisi strutturale si esegue in
Abaqus, a mano, e i suoi risultati stanno in `analisi-abaqus/`. Il perimetro è
scritto in [`PRODUCT.md`](../PRODUCT.md).

Esiste però una seconda linea, portata avanti in parallelo, che punta a fare
l'analisi **dentro** il programma: pre-processore, solutore e post-processore,
fino alle verifiche di norma. Questo documento dice dove vive, che cosa ha già
prodotto, e perché sta fuori dal perimetro invece che dentro.

## Che cosa è già nel tronco principale

Gli step 12 e 13 sono in `main` e funzionano. Il 12 è il prior geometrico, che
misura telaio, membrature e armature; il 13 è il solutore, e i suoi due rami
partono da artefatti diversi — CalculiX sul deck dello step 11, OpenSees sul
telaio costruito dal prior dello step 12. Li governa una schermata dedicata
dell'interfaccia. Nulla di tutto ciò è stato rimosso, e nulla verrà rimosso: è
codice funzionante, coperto da test, ed è la base su cui la linea prosegue.

Ciò che è cambiato è che cosa il progetto **dichiara**. `to_step` ha 11 come
predefinito, così una corsa senza argomenti si ferma dove il prodotto si ferma.
Chi vuole il prior o la soluzione li chiede — `meshrec wall`, `--to-step 12`,
`meshrec solve` — e li ottiene.

## Dove vive il lavoro non ancora nel tronco

Due rami, entrambi non fusi in `main`.

**`worktree-notte-analisi-strutturale`** — il lavoro più avanzato della linea, e
al momento **non pubblicato su GitHub**: il ramo esiste solo nel clone locale
dell'autore, quindi da questo repository non è raggiungibile. Contiene la lettura delle
risultanti dal file `.dat` del solutore, il passo statico che chiede le
sollecitazioni sulle sezioni dichiarate, la deduplicazione delle sezioni nel
deck, e una corsa di riferimento risolta per intero. Porta con sé una spec dell'analisi strutturale che va dal
telaio alle verifiche.

**`worktree-wayfinder-analisi-strutturale`** — nessun codice: la mappa, in
`.scratch/analisi-strutturale/`. Le issue vanno dal banco di prova al
post-processore, passando per i parametri sismici di sito, le verifiche dei
minimi d'armatura, di presso-flessione e di taglio, e una ricerca su quali
moduli esistenti si potrebbero integrare invece di scrivere.

## Come si legge la mappa alla luce del perimetro

Alcune issue della mappa dicono di costruire le verifiche di norma «in MeshRec».
La frase non distingue fra due cose diverse, e va letta così: **MeshRec-la-linea,
non MeshRec-il-prodotto-di-tesi**. Costruire le verifiche su questa linea non
contraddice il perimetro; portarle nel tronco e presentarle come capacità del
prodotto lo contraddirebbe.

## Perché la linea sta fuori, e a quali condizioni rientrerebbe

Due ragioni.

La prima è di tempo: pre-processore, solutore e post-processore sono la parte
del progetto che può non chiudere entro la tesi, perché dipende da eseguibili
esterni, dalla convergenza, e dall'interpretazione dei risultati — che è lavoro
strutturale e si giudica con criteri diversi da quelli di una pipeline.

La seconda è di prova. La tesi presenta risultati Abaqus. Se il programma ne
calcolasse altri con un solutore proprio, ogni scostamento fra i due motori
diventerebbe qualcosa da spiegare, a partire dal fatto che elementi e condizioni
al contorno non si comportano identici nei due. Fuori perimetro, quel problema
non si pone.

Dentro la linea, invece, un solutore libero ha un mestiere preciso e utile:
**verificare che il deck sia ben formato prima che venga aperto in Abaqus**. È
un controllo, non una fonte di numeri per la tesi — ed è esattamente il genere di
cosa che il resto del progetto già fa per ogni altra grandezza.

La linea rientrerebbe nel tronco quando i suoi risultati reggessero il confronto
con Abaqus sullo stesso deck, in modo documentato e ripetibile. Fino ad allora
resta qui.

## La CI

Il workflow ha due lavori. `suite` gira sulla matrice di piattaforme senza alcun
solutore esterno: copre il prodotto. `benchmark` installa `calculix-ccx`,
fallisce se manca, ed esegue la suite intera compresi i test che richiedono il
solutore: copre quindi **questa linea oltre al perimetro**, ed è il solo posto
dove i test del solutore girano davvero.
