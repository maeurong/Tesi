# Fase 1 — Esiti della validazione su dati reali

- **Data di esecuzione:** 13 agosto 2026
- **Ambiente:** Windows 11, Python 3.12.10, 16 GB di RAM, 12 processori logici
- **Nuvola di riferimento:** `Nuvole di punti/muro_generato.ply`, il muro sintetico a geometria nota
- **Unità di lavoro:** mm, N, MPa, tonnellata, secondo

Questo documento riporta la validazione sul muro sintetico e il confronto fra i
due generatori di mesh di volume. Per la segmentazione automatica sulla
scansione di laboratorio (`lab_frame.pcd`) si rimanda a
[`fase-1-esiti-lab-frame.md`](fase-1-esiti-lab-frame.md), redatto in parallelo.

## Ingombro letto e fattore di scala

La nuvola è stata prima letta senza `expected_size`, cioè con il controllo di
scala disattivato, per misurarne l'ingombro effettivo. Alla scala unitaria i
611.008 punti occupano un parallelepipedo di 5,8234 × 1,2457 × 7,8026 unità:
valori di quest'ordine sono metri, non millimetri, e il fattore di conversione
verso le unità di lavoro è quindi **1000,0**.

Con `scale: 1000.0` l'ingombro diventa **5823,35 × 1245,73 × 7802,62 mm**, cioè
un muro lungo circa 5,82 m, alto circa 7,80 m e spesso circa 1,25 m. Questi tre
valori sono stati poi riscritti in `expected_size`, con la tolleranza
predefinita del 20%, così che il controllo di scala diventasse attivo per tutte
le esecuzioni successive: nel `metrics.json` della corsa finale il campo
`size_check` vale infatti `ok` e non più `non richiesto`. La spaziatura media
fra punti vicini risulta di 9,125 mm.

## Parametri finali e perché differiscono dai predefiniti

La prima esecuzione, lanciata con i valori predefiniti (`voxel_size: null`,
cioè due volte la spaziatura media, e `poisson_depth: 9`), non arrivava in
fondo: produceva gli artefatti fino a `05_surface.ply` e poi il processo veniva
ucciso dal sistema durante lo step 6, senza nemmeno scrivere il `metrics.json`
che `pipeline.run` produce nel blocco `finally`.

L'ipotesi iniziale era che PyMeshFix non reggesse in memoria una superficie da
908.118 triangoli. **L'ipotesi era sbagliata**, ed è utile registrarlo perché la
correzione è di natura completamente diversa. Riducendo la mesh e istrumentando
lo step 6 si è visto che il guasto non è nella riparazione vera e propria ma in
`repair.hole_loops`, la funzione che misura i fori *prima* della chiusura: il
cammino che ricostruisce i cicli di spigoli di bordo sceglie sempre il primo
vicino disponibile, e su una **giunzione non manifold** — un vertice con più di
due spigoli di bordo, che il trimming per densità del Poisson produce
regolarmente — entra in un circuito che non ripassa mai dal punto di partenza.
Il ciclo interno non ha condizione di uscita, la lista dei vertici cresce senza
limite e il processo esaurisce la memoria. Sulla superficie del muro il fenomeno
si innesca con soli 2285 spigoli di bordo: non è un problema di taglia, e a
depth 9 sarebbe accaduto lo stesso.

Con un tetto sulla lunghezza del ciclo, pari al numero di spigoli di bordo — un
ciclo non può essere più lungo del grafo che percorre — lo step 6 completa in
5,9 secondi su 221.369 triangoli. La correzione tocca `src/meshrec/core/repair.py`
e porta con sé una prova di non regressione in `tests/test_repair.py`.

Il tetto introduce però un caso nuovo, che va registrato onestamente: un cammino
interrotto perché ha raggiunto il tetto non è un foro, e contarlo fra i fori
significherebbe attribuirgli un'area calcolata su un ciclo troncato. I due casi
sono quindi tenuti distinti: `holes_before` e `hole_areas` riguardano solo i
cicli che si richiudono davvero, mentre i cammini che non si richiudono — per
vicolo cieco o per tetto raggiunto — sono contati a parte in
`open_boundary_paths`, che è il segnale che il bordo è non manifold.

I parametri effettivamente usati nella corsa finale si discostano dai predefiniti
in due punti, entrambi scelti per contenere la taglia della superficie:

| Parametro | Predefinito | Usato | Motivo |
|---|---|---|---|
| `downsample.voxel_size` | `null` (2 × spaziatura = 18,25 mm) | **25,0 mm** | riduce la nuvola da 593.728 a 200.296 punti, un terzo del carico a valle, senza scendere sotto la risoluzione utile per un muro di 1,25 m di spessore |
| `surface.poisson_depth` | 9 | **8** | dimezza il lato della cella dell'ottree e porta la superficie da 908.118 a 221.369 triangoli, cioè da 22 MB a 5,6 MB di artefatto |

Tutto il resto è rimasto ai valori predefiniti. In particolare `simplify` è
rimasto **disabilitato**: nella sequenza della pipeline la semplificazione è lo
step 8 e viene *dopo* la riparazione, quindi non avrebbe potuto alleggerire lo
step 6, che era il punto di rottura. È una precisazione che vale la pena
lasciare scritta, perché la si potrebbe supporre il contrario leggendo l'elenco
dei parametri invece dell'ordine degli step.

Con questi parametri la pipeline completa gira in **circa 98 secondi**, dalla
lettura della nuvola alla scrittura del deck, di cui una quarantina nella sola
tetraedrizzazione. Il valore è il tempo di parete di due corse consecutive dal
primo step, misurate attorno al comando `meshrec run muro.yaml`: 97,5 s e 98,1 s.

Questa configurazione è ora tracciata da git in `meshrec/muro.yaml`: il file
non è più una nota a margine ma la copia esatta, emessa dalla pipeline stessa,
dei parametri della corsa qui documentata, così che rieseguire `meshrec run
muro.yaml` riproduca questi numeri e non una configurazione andata perduta.

Un solo parametro della tetraedrizzazione è stato poi misurato per conto suo,
riprendendo la pipeline dallo step 9 su questa stessa superficie riparata:
`tet.min_ratio`, il cui margine è riportato in `fase-1-min-ratio.md`. Ne è
uscito che il predefinito 1,8 non è il valore più severo che converge — lo è
1,7 — e che sotto 1,7 il raffinamento si interrompe.

## Metriche di ogni step

I numeri seguenti vengono da `runs/muro/metrics.json` di una corsa pulita
dall'inizio, eseguita il 13 agosto 2026 con il codice corrente. Quando un numero
in questo documento viene da una misura fatta a parte, e non da quel file, è
detto sul posto.

**Step 1 — lettura e scala.** 611.008 punti letti, nessuno scartato per
coordinate non finite, fattore di scala 1000,0, spaziatura media 9,125 mm,
ingombro 5823,35 × 1245,73 × 7802,62 mm, controllo di scala superato.

**Step 2 — segmentazione.** Metodo `crop` senza estremi assegnati, quindi il
ritaglio non viene applicato e lo step agisce come solo filtro statistico dei
punti isolati: 17.280 punti rimossi, 593.728 rimasti.

**Step 3 — riduzione a voxel.** Passo di 25,0 mm, da 593.728 a 200.296 punti,
riduzione del 66,3%.

**Step 4 — normali.** Vicinato di 30 punti per la stima e altrettanti per
l'orientamento coerente; nessuna normale degenere.

**Step 5 — ricostruzione.** Poisson a profondità 8, scala 1,1, con trimming al
quantile di densità 0,05: 5882 vertici scartati sopra la soglia di densità
8,0702, superficie risultante di 111.744 vertici e 221.369 triangoli.

**Step 6 — riparazione.** Nessun vertice coincidente da saldare, nessun
triangolo degenere o duplicato; tre componenti connesse, di cui viene tenuta
solo la maggiore, con 37 vertici orfani rimossi. Prima della chiusura si contano
**87 fori**, cioè cicli di bordo che si richiudono, il maggiore di 4,63 m² e i
successivi di 0,244 e 0,140 m², più **2 cammini di bordo aperti**
(`open_boundary_paths`), che non sono fori. Dopo MeshFix la superficie è
**chiusa** (`watertight_after: true`), con 116.967 vertici e 233.930 triangoli.
Il volume racchiuso passa da 46,17 m³ prima della chiusura a 53,87 m³ dopo:
l'incremento è quasi tutto la materia aggiunta chiudendo le due facce aperte del
muro.

I due cammini aperti sono proprio quelli che percorrono le facce aperte
passando per giunzioni non manifold e non si richiudono mai. Contarli fra i fori
li avrebbe fatti apparire come due lacune da circa 23,0 m² ciascuna — un valore
calcolato su un cammino troncato, cioè un'area priva di significato. Il registro
li tiene ora separati: `holes_before` conta solo i cicli chiusi e `hole_areas`
ha esattamente un'area per ciascuno di essi, mentre `open_boundary_paths`
segnala che il bordo è non manifold senza attribuirgli una superficie. La
chiusura la esegue comunque MeshFix, ed è verificata.

Questa separazione ha però reso cieca, per un tratto, la guardia
`repair.max_hole_area`: `holes_over_threshold` scandiva i soli cicli chiusi, e
proprio qui le due aperture maggiori — 22,989 e 23,005 m² di area indicativa —
sono cammini aperti. Una soglia pensata perché un'apertura grande non passi
inosservata non poteva essere l'unica cosa che non le vedeva. Le metriche
riportano ora anche `open_paths_over_threshold`, con le aree indicative dei
cammini oltre soglia, tenute in una voce a parte per non confondersi con le aree
misurate dei fori veri. In questa corsa `max_hole_area` è nullo, quindi entrambe
le liste sono vuote.

**Step 7 — qualità della superficie.** 116.967 vertici, 233.930 triangoli,
superficie chiusa con zero spigoli di bordo, area 121,57 m², volume racchiuso
53,87 m³. Il rapporto d'aspetto dei triangoli ha mediana 1,394 e media 2,009,
con un massimo di 3968: la coda di triangoli molto allungati è quella lasciata
dalla chiusura, e non impedisce la tetraedrizzazione.

**Step 8 — semplificazione.** Disabilitata: 233.930 triangoli in ingresso e in
uscita.

**Step 9 — tetraedrizzazione.** TetGen con rapporto raggio-spigolo 1,8, nessun
vincolo di volume massimo e **nessun tetto ai punti di Steiner**: 420.547 nodi e
**1.752.795 tetraedri** in **43,77 secondi**, con 303.580 punti aggiunti e
`steiner_saturated: false`. Il tempo è quello del `metrics.json` citato sopra; è
la sola grandezza dello step che varia fra corse identiche, misurata fra 40,2 e
44,3 secondi su tre esecuzioni della stessa configurazione. Nodi, tetraedri e
punti aggiunti sono invece riprodotti identici.

Rapporto raggio-spigolo 1,8 e assenza di tetto sono ora entrambi i predefiniti di
`TetConfig`, cambiati per il motivo spiegato nella sezione «La mesh troncata»,
più sotto: fino a poco fa questo step produceva 216.967 nodi e 635.336 tetraedri
in 12,77 secondi, ma quella mesh era troncata.

**Step 10 — qualità del volume.** **Zero elementi invertiti**, volume totale
coerente con quello della superficie. L'angolo diedro minimo ha **mediana
38,26°** e media 36,94°, con un minimo di 0,0025° e un massimo di 68,87°. Per confronto, la mesh troncata che questo
step produceva prima aveva mediana 6,04°: la differenza dà la misura di quanto
la troncatura degradasse la mesh senza che nulla lo segnalasse.

**Step 11 — esportazione.** Deck scritto in `wall_model.inp` e
`wall_model.vtu`. Volume 53,873 m³, massa **96,97 t** con la densità di 1,8 ×
10⁻⁹ t/mm³. Ingombro allineato **1224,1 × 5854,3 × 7823,6 mm**, con tolleranza
dei set di 31,95 mm e insiemi di nodi `BASE` **4738**, `TOP` 3468,
`FACE_FRONT` 224.875, `FACE_BACK` 122.728, `SIDE_LEFT` 4272, `SIDE_RIGHT` 4085.

Questo step portava fino a poco fa un'anomalia seria, **ora risolta**. Il
sistema di riferimento del modello veniva stimato con una PCA sui nodi della
mesh di volume, e ne usciva ruotato: la prima direzione principale si scostava
dal verticale di 21,44°, l'ingombro allineato risultava 1301,3 × 7633,4 × 9011,0
mm contro i 1245,7 × 5823,4 × 7802,6 mm della nuvola, e `BASE` raccoglieva 387
nodi sulla base di un muro largo 5,8 m e spesso 1,2 m. La causa era che una PCA
pesa ogni nodo allo stesso modo, mentre la densità dei nodi non è una proprietà
della forma: dipende da dove il raffinamento ha infittito, cioè da un artefatto
del maglio.

La terna si stima ora sui **vertici della superficie riparata**, che è la
geometria vera, e la trasformazione si applica a tutti i nodi del volume; lo
scostamento al primo ottante continua a calcolarsi sui nodi trasformati, così
che la quota minima dei nodi valga zero e `BASE` corrisponda davvero alla base.
I numeri prima e dopo:

| Grandezza | Terna stimata sui nodi | Terna stimata sulla superficie |
|---|---|---|
| Scarto della prima direzione principale dal verticale | 21,44° | **0,45°** |
| Ingombro allineato [mm] | 1301,3 × 7633,4 × 9011,0 | **1224,1 × 5854,3 × 7823,6** |
| `BASE` | 387 nodi | **4738 nodi** |
| `SIDE_LEFT` / `SIDE_RIGHT` | 350 / 295 | **4272 / 4085** |

Sulla **tolleranza dei set** resta invece un limite dichiarato e non risolto. I
31,95 mm derivano dal lato del tetraedro regolare di volume *medio*, e la
distribuzione dei volumi ha una coda pesantissima: mediana 14,6 mm³ contro media
30.735 mm³, un fattore duemila. La tolleranza che decide quali nodi finiscono in
`BASE` dipende quindi da una manciata di elementi enormi. Il passaggio alla
mediana è stato provato e misurato: la tolleranza scende a 2,50 mm e `BASE`
passa da 4738 nodi a **9** su 420.547, cioè a un vincolo puntiforme sotto un muro
da 97 t. Il motivo è che nessuna delle due statistiche descrive l'elemento
tipico — la mediana è dominata dai tetraedri minuscoli lasciati dal raffinamento
sulla superficie (lato equivalente 5,0 mm), la media dai pochi elementi enormi
dell'interno (63,9 mm) — mentre la scala che conterebbe è la spaziatura dei nodi
sul bordo, che vale 13,7 mm di mediana. Legare la tolleranza al volume
dell'elemento è l'euristica sbagliata in partenza. Finché non viene sostituita
resta la media, che è la sola sotto cui i set sono stati verificati utilizzabili;
il numero di nodi di ogni set è comunque scritto in `metrics.json`, quindi un set
degenere sarebbe visibile e non silenzioso.

L'ingombro allineato coincide ora con quello della nuvola sorgente entro il 2%,
e i set laterali, prima squilibrati e minuscoli, sono diventati simmetrici fra
loro e di taglia sensata. **I set di faccia sono finalmente utilizzabili per
un'analisi vera**: `BASE`, che è l'insieme vincolato dal deck, raccoglie 4738
nodi distribuiti sulla base reale del muro invece di 387 nodi raccolti su uno
spigolo obliquo, e con quel vincolo il carico di gravità scarica dove deve.

### Lo squilibrio fra le due grandi facce nasce nella pipeline, non nel dato

Resta uno squilibrio fra `FACE_FRONT` (224.875 nodi) e `FACE_BACK` (122.728): il
primo insieme ha l'**83% di nodi in più** del secondo. Non è un difetto di
allineamento, ma **non è nemmeno una proprietà del dato**, come una versione
precedente di questa sezione affermava attribuendolo alla scansione. Quella
lettura era sbagliata due volte. Anzitutto `muro_generato.ply` non è una
scansione: è il muro **sintetico** a geometria nota, generato, quindi non esiste
alcun punto di vista che ne abbia visto una faccia meglio dell'altra. E poi i
dati per verificarlo sono nel repository, e dicono il contrario.

Misurando quanti punti cadono entro la stessa banda ai due estremi dello spessore
— la banda è la tolleranza dei set, 31,95 mm, applicata dopo la stessa
trasformazione di allineamento — lo squilibrio compare **solo all'ultimo
passaggio**:

| stadio | verso *x* minimo | verso *x* massimo | eccesso del maggiore |
|---|---|---|---|
| nuvola segmentata (`02_segmented.ply`, 593.728 punti) | 214.543 | 210.064 | **2,1%** |
| superficie riparata (`06_repaired.ply`, 116.967 vertici) | 46.031 | 43.012 | **7,0%** |
| nodi del deck (`wall_model.vtu`, 420.547 nodi) | 224.875 | 122.728 | **83,2%** |

Allargando la banda al doppio, la nuvola segmentata dà 223.435 contro 223.114
punti, cioè è simmetrica allo **0,14%**: la sorgente è, a tutti gli effetti,
bilanciata. Lo squilibrio è quindi introdotto dalla pipeline, e per la quasi
totalità dall'ultimo passo: **è il raffinamento di bordo di TetGen** a infittire
una faccia molto più dell'altra, dopo che la ricostruzione di Poisson e la
chiusura ne avevano già introdotto una frazione modesta: il 7,0% dello step 6
contro l'83,2% del deck, cioè circa un dodicesimo dello squilibrio finale.

Non è nemmeno un effetto della tolleranza che seleziona i set. I due strati sono
piani: la normale ai minimi quadrati dei nodi di `FACE_FRONT` si scosta di
**0,030°** dal piano a *x* costante e quella di `FACE_BACK` di **0,042°**, con
dispersione in spessore di 4,1 mm su entrambi. Le due facce sono ugualmente
piatte e ugualmente dentro la banda; a differire è solo quanti nodi TetGen ci ha
messo.

### I nomi dei set di faccia sono una convenzione, non un'identificazione

`BASE` e `TOP` sono verificati: l'asse *z* del modello allineato è il verticale
reale, quindi il minimo è davvero la base del solido, ed è su questo che poggia
il vincolo del deck.

`FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT` e `SIDE_RIGHT` **no**. Sono etichette
assegnate per convenzione al minimo e al massimo di *x* e di *y* dopo
l'allineamento, e il verso di quegli assi viene da una regola deterministica di
segno (`abaqus._fix_sign`), scelta perché due esecuzioni non producano assi
opposti — non da un riferimento preso sul muro. Nessuna verifica in questo
progetto stabilisce quale delle due grandi facce sia l'«anteriore» del muro
fisico, né quale sia il lato «sinistro». La coppia è affidabile come coppia (le
due facce opposte sono quelle giuste); il singolo nome no. Ovunque in questo
documento e in [`fase-1-esiti-lab-frame.md`](fase-1-esiti-lab-frame.md) si legga
`FACE_FRONT` o `SIDE_LEFT`, va inteso come «uno dei due estremi lungo quell'asse»
e nulla di più. Chi userà questi set per confrontare il modello con misure fatte
in campo dovrà prima verificare l'orientamento sul file allineato.

## La mesh troncata: un tetto ereditato da una libreria

Il numero tondo di 100.000 nodi interni notato nel rapporto sull'allineamento
non era una coincidenza. Il pacchetto `tetgen` ha come predefinito
`steinerleft = 100000`, cioè un tetto al numero di punti che TetGen può
aggiungere per raffinare, e `core/volume.py` non lo impostava mai: il valore
arrivava dalla libreria senza che nessuno lo avesse scelto.

### La verifica, prima della correzione

Il tetto è stato fatto variare sulla superficie riparata del muro, lasciando
tutto il resto invariato:

| `steinerleft` | Nodi | Tetraedri | Punti aggiunti | Esito |
|---|---|---|---|---|
| 25.000 | 141.967 | 439.180 | **25.000** | esaurito |
| 50.000 | 166.967 | 501.700 | **50.000** | esaurito |
| 100.000 (predefinito ereditato) | 216.967 | 635.336 | **100.000** | esaurito |
| 120.000 | 236.967 | 691.227 | **120.000** | esaurito |
| 150.000 | 266.967 | 777.643 | **150.000** | esaurito |
| 175.000 | 291.967 | 848.506 | **175.000** | esaurito |
| 200.000 e senza limite | — | — | — | errore interno di TetGen |

I punti aggiunti eguagliano il tetto **esattamente**, a ogni livello e mai per
difetto: il raffinamento non finiva perché era completo, finiva perché il budget
era esaurito. La diagnosi è confermata, e questo conteggio è anche l'indizio su
cui si appoggia la nuova metrica, visto che TetGen non dichiara in alcun modo di
essersi fermato per esaurimento.

### Quanto era grave

Molto più di quanto la parola «troncata» suggerisca. Contando quali nodi
appartengono a facce che compaiono una sola volta, cioè quali stanno sul bordo
del solido:

| Mesh | Nodi | Tetraedri | Nodi di bordo | Nodi interni |
|---|---|---|---|---|
| Troncata (predefinito ereditato, `min_ratio` 1,1) | 216.967 | 635.336 | 216.967 | **0** |
| Completa (nessun tetto, `min_ratio` 1,8) | 420.547 | 1.752.795 | 258.581 | **161.966** |

La mesh che la pipeline ha prodotto finora aveva **zero nodi interni**: un muro
pieno riempito con 635.336 tetraedri, e non un solo vertice dentro il volume.
L'intero budget di 100.000 punti era stato consumato a suddividere la
superficie, e il riempimento non era mai cominciato. Nessuna metrica lo
segnalava: non c'erano elementi invertiti, il volume tornava, e la mediana
dell'angolo diedro di 6,04° si poteva scambiare per una mesh semplicemente
mediocre invece che per una mesh interrotta a metà. Sulla mesh completa la
mediana sale a 38,26°.

Questo spiega anche perché correggere l'allineamento perché stimasse la terna
sui soli nodi di bordo non cambiava nulla sul muro: su quella mesh **tutti** i
nodi erano di bordo, quindi selezionarli non selezionava niente.

### Il limite vero: la qualità richiesta non è raggiungibile

Tolto il tetto, viene alla luce un secondo problema che il tetto stesso nascondeva.
Con `min_ratio` 1,1 — il predefinito di allora, molto più severo del 2,0 di
TetGen — il raffinamento **non converge**: TetGen si interrompe con un errore
interno (`split_subface` o `split_segment`) dopo pochi secondi. Provando a
scendere per gradi, sulla superficie del muro:

| `min_ratio` | Senza tetto ai punti di Steiner |
|---|---|
| 1,1 / 1,2 / 1,4 / 1,5 / 1,6 | errore interno di TetGen dopo ~6 s |
| **1,8** | **420.547 nodi, 1.752.795 tetraedri, 303.580 punti aggiunti, 40,8 s, 1,35 GB** |
| 2,0 | 372.068 nodi, 1.498.226 tetraedri, 255.101 punti aggiunti, 33,2 s, 1,39 GB |

I tempi e le occupazioni di memoria di questa tabella vengono dalla prova
comparativa, eseguita a parte sulla sola superficie riparata e non attraverso la
pipeline: il 40,8 s della riga 1,8 non è quindi il 43,77 s dello step 9 riportato
sopra, che è il tempo della corsa completa in `runs/muro/metrics.json`. Le due
misure sono della stessa configurazione e differiscono per la sola variabilità
fra esecuzioni.

Il tetto, insomma, mascherava una configurazione che non poteva funzionare: si
fermava prima che TetGen arrivasse alla configurazione degenere, e restituiva
una mesh a metà con l'aria di un successo. 1,8 è il valore più severo che porti
a termine il lavoro su questa geometria, ed è quello usato per l'esecuzione
riportata qui.

### Che cosa è cambiato nel codice

`TetConfig` ha ora un campo `max_steiner_points`, il cui **predefinito è -1,
cioè nessun limite**, dichiarato nel campo e nella sua descrizione. La scelta
dell'assenza di limite è deliberata: qualunque numero sarebbe stato arbitrario
quanto quello ereditato, e un tetto è precisamente ciò che ha reso il difetto
invisibile. `core/volume.py` passa il valore a TetGen esplicitamente, e la firma
di `tetrahedralize` **non** gli dà un valore predefinito, così che nessun
chiamante possa tornare a lasciarlo implicito.

Il troncamento non è più silenzioso: le metriche dello step 9 riportano ora
`max_steiner_points`, `steiner_points` e `steiner_saturated`, e quando il budget
si esaurisce viene emesso un `TruncatedRefinementWarning`. Poiché TetGen non
dichiara l'esaurimento, l'indizio usato è il conteggio dei punti aggiunti
confrontato con il tetto, verificato esatto ai sei livelli della tabella sopra.

Di conseguenza il **predefinito di `min_ratio` è stato portato da 1,1 a 1,8**:
1,1 era troppo vicino al limite teorico e faceva fallire la tetraedrizzazione su
geometria reale. Il margine resta però sottile, perché 1,8 è tarato su un solo
caso e già 1,6 non converge, quindi su un'altra geometria può non bastare. Il
rischio è dichiarato e mitigato, non nascosto: l'errore interno grezzo di TetGen
non risale più al chiamante così com'è, ma viene tradotto in un
`RefinementFailedError` che dice esplicitamente che il vincolo raggio-spigolo
può essere troppo severo per quella geometria e che va alzato. La descrizione del
campo in `TetConfig` avverte nello stesso senso.

## Errore geometrico rispetto alla nuvola sorgente

L'errore è bidirezionale, calcolato con PyMeshLab fra la superficie riparata e
la nuvola segmentata dello step 2, che è il riferimento fisso.

| Direzione | Campioni | Media | RMS | Massimo |
|---|---|---|---|---|
| Nuvola → mesh | 593.728 | **4,067 mm** | **5,156 mm** | 54,184 mm |
| Mesh → nuvola | 116.967 | **8,786 mm** | **9,774 mm** | 44,463 mm |

La distanza di Hausdorff, cioè il massimo dei due massimi, vale **54,18 mm**.
Rapportata alla diagonale dell'ingombro, circa 9810 mm, è lo **0,55%**; l'errore
medio nella direzione nuvola → mesh è lo 0,041% della diagonale. Il valore va
letto ricordando che il passo di voxel scelto è di 25 mm e che la profondità 8
del Poisson corrisponde a celle di circa 30 mm: un errore medio di 4 mm è
inferiore alla risoluzione con cui la superficie è stata costruita, mentre il
massimo di 54 mm si concentra dove la chiusura ha inventato superficie sulle due
facce aperte, cioè dove per costruzione non esistono punti di riferimento.

## Confronto Gmsh contro TetGen a parità di elementi

### Che cosa diceva la misura di Fase 0, e perché non reggeva

Il documento di Fase 0 riporta che «la qualità minima è passata da 0,037787 a
0,423365» con il numero di elementi che «è cambiato da 540 a 775 (+43,5%)», e
ne trae la cautela che il confronto non fosse a parità di elementi. Rileggendo
il test che ha prodotto quei numeri, `tests/feasibility/test_gmsh.py`, emerge
che il difetto è più profondo di così, su due punti.

Il primo: quella non è affatto una misura di Gmsh contro TetGen. I due valori
sono la qualità minima della mesh di **Gmsh prima** e della mesh di **Gmsh
dopo** la chiamata a `optimize("Netgen")`. TetGen non compare nella misura. Il
guadagno documentato è quindi quello dell'ottimizzatore interno di Gmsh su una
mesh di Gmsh, non un confronto fra due generatori, e la riga della tabella di
Fase 0 che presenta Gmsh come «ottimizzatore post-mesh opzionale accanto a
TetGen» sovrappone due cose diverse.

Il secondo: la grandezza misurata non è l'angolo diedro minimo ma il valore
restituito da `gmsh.model.mesh.getElementQualities`, un indice adimensionale in
[0, 1] proprio di Gmsh. Non è confrontabile con le metriche di `core/quality.py`,
e i due numeri non vanno letti come gradi.

Restano invece corretti, e sono stati riprodotti su questa macchina, i valori in
sé: `n_before=540 n_after=775 qmin_before=0.037787 qmin_after=0.423365`.

### Come è stato reso il confronto a parità di elementi

La dimensione caratteristica che produce esattamente N tetraedri non è nota in
forma chiusa. La stima analitica usata in origine — il lato del tetraedro
regolare di volume medio V/N — sbagliava di un fattore sei, dando un rapporto di
5,61 invece di 1. In `core/gmsh_backend.py` la dimensione ora non si stima
soltanto, si **calibra**: si genera con la dimensione stimata, si contano i
tetraedri ottenuti, si riscala la dimensione del fattore
`(ottenuti / obiettivo)^(1/3)` — l'esponente viene dal fatto che il numero di
elementi scala con il cubo dell'inverso della dimensione — e si rigenera. Il
ciclo si ferma appena il rapporto rientra fra 0,85 e 1,2, con un tetto di quattro
tentativi; superato il tetto restituisce il tentativo con il rapporto migliore
invece di insistere, e lo dichiara nelle metriche. Sul caso in esame **due
tentativi** sono bastati.

Due dettagli tecnici sono stati necessari perché la calibrazione converga. Il
primo: con il solo `Mesh.MeshSizeMax` la taglia richiesta è un tetto senza
pavimento e resta inerte quando la risoluzione dedotta dal bordo è già più fine,
quindi vanno fissati anche `Mesh.MeshSizeMin` e la taglia sui punti, e vanno
spenti `MeshSizeExtendFromBoundary` e `MeshSizeFromCurvature`. Il secondo: ogni
tentativo ricostruisce il modello da capo a partire dall'STL, perché la
geometria prodotta da `classifySurfaces` più `createGeometry` è parametrizzata
sulla mesh d'appoggio dell'STL e `mesh.clear()` la distrugge, lasciando Gmsh a
rimagliare una superficie senza parametrizzazione — verificato, la generazione
successiva non termina.

Va registrato anche un limite trovato per via sperimentale. Il rimagliamento
della superficie in Gmsh ha un **pavimento**: sul parallelepipedo di prova non
scende sotto circa 190 tetraedri per quanto si allarghi la dimensione
caratteristica (195 a 100 mm e ancora 195 a 400 mm), mentre TetGen senza vincolo
di volume si ferma a 46, cioè alla decomposizione minima. A quella densità la
parità è irraggiungibile e il confronto non direbbe nulla sui due generatori. Il
confronto è quindi stato portato alla densità di lavoro, imponendo a TetGen un
volume massimo di elemento di 2000 mm³: si ottengono 914 tetraedri, lo stesso
ordine di grandezza della misura di Fase 0, e lì entrambi i generatori sono
liberi di scegliere la propria mesh. La tolleranza del test è rimasta quella
originale, fra 0,7 e 1,4: non è stata allargata.

### I numeri, e la conclusione

Parallelepipedo di 100 × 40 × 200 mm; TetGen con `max_volume = 2000 mm³`; Gmsh
calibrato su quel numero di elementi, dimensione finale 21,136 mm.

| | TetGen | Gmsh |
|---|---|---|
| Tetraedri | 914 | **866** |
| Nodi | 282 | 272 |
| Angolo diedro minimo | **2,302°** | **25,504°** |
| Angolo diedro, mediana | 46,167° | 47,320° |
| Rapporto d'aspetto, massimo | 25,35 | 2,58 |
| Rapporto d'aspetto, mediana | 1,438 | 1,477 |
| Elementi invertiti | 0 | 0 |

Il rapporto effettivo di elementi è **0,947**, cioè Gmsh produce il 5,3% di
elementi in meno di TetGen: il confronto è a parità, e questa volta davvero.

**La conclusione è che il guadagno di qualità sopravvive alla parità di
elementi, e non era un effetto del raffittimento.** Con il 5% di elementi in
meno, l'angolo diedro minimo passa da 2,302° a 25,504°, cioè migliora di un
fattore undici, e il rapporto d'aspetto peggiore scende da 25,35 a 2,58. È un
risultato positivo, ma va enunciato con precisione, perché il guadagno **non è
diffuso**: la mediana dell'angolo diedro è praticamente identica fra i due
generatori (46,17° contro 47,32°) e la mediana del rapporto d'aspetto è
leggermente peggiore in Gmsh (1,477 contro 1,438). Il vantaggio di Gmsh sta
tutto nella **coda**, cioè nell'eliminare gli elementi peggiori — che è però
proprio ciò che conta per il condizionamento del sistema in un calcolo agli
elementi finiti, dove è l'elemento peggiore a dettare il passo.

L'attribuzione della misura è stata **corretta nel documento di Fase 0**, sia nel
riquadro di rettifica a [`fase-0-esiti.md`](fase-0-esiti.md) § «Conseguenze sulla
Fase 1», sia nella riga della tabella delle dipendenze che presentava Gmsh come
«ottimizzatore post-mesh opzionale accanto a TetGen»: quella formula sovrapponeva
due cose diverse, perché Gmsh non ottimizza una mesh prodotta da TetGen, genera
la propria e semmai ottimizza quella. Le due fonti dicono ora la stessa cosa. Il
confronto vero fra i due generatori, a parità di elementi, è quello riportato
qui.

Una precisazione di ambito: questa misura è stata fatta sulla geometria
sintetica di prova, non sul muro ricostruito. Il percorso principale della
pipeline resta senza Gmsh — `pipeline.py` non importa `gmsh_backend` — e Gmsh
resta un generatore alternativo da valutare, non un passaggio obbligato.

## Costo della riproducibilità nella ricostruzione di Poisson

Il campo `surface.poisson_n_threads` vale 1 e non il valore automatico di Open3D
perché con più thread l'ordine di riduzione della ricostruzione di Poisson
cambia a ogni chiamata, e la variazione si propaga a valle fino a TetGen,
facendo cadere il criterio di riproducibilità a parità di configurazione.

Cronometrando la sola ricostruzione sulla stessa nuvola — i 200.296 punti con
normali dello step 4 del muro, profondità 8, scala 1,1 — si ottiene:

| `poisson_n_threads` | Tempo | Vertici | Triangoli |
|---|---|---|---|
| **1** (riproducibile) | **5,10 s** | 117.636 | 235.268 |
| **-1** (automatico, 12 processori) | **2,63 s** | 117.636 | 235.268 |

La riproducibilità costa dunque **2,47 secondi**, cioè poco meno del doppio del
tempo, su una ricostruzione che pesa comunque poco più del 5% dei circa 98
secondi dell'intera pipeline misurati sopra. Il conteggio di vertici e triangoli coincide fra le due
configurazioni: a cambiare con più thread è l'ordine, non la taglia del
risultato. **Il valore predefinito resta 1**: questa misura documenta un
compromesso accettato, non lo mette in discussione.

## Stato del controllo dei dati con Abaqus

Il controllo dei dati con Abaqus (`*DATACHECK`) è **non eseguito**, perché
Abaqus non è disponibile su questa macchina. Resta dovuto, ed è la sola verifica
del deck ancora aperta.

Il deck prodotto è però verificato per altre due vie, entrambe eseguite:

- **in lettura da `meshio`**, direttamente sul file di questa esecuzione:
  `runs/muro/wall_model.inp` viene riletto senza errori, restituendo **420.547
  punti** e **1.752.795 elementi `tetra`**, cioè esattamente i conteggi dello
  step 9, e i sei insiemi di nodi con le taglie dichiarate dallo step 11:
  `BASE` 4738, `TOP` 3468, `FACE_FRONT` 224.875, `FACE_BACK` 122.728,
  `SIDE_LEFT` 4272, `SIDE_RIGHT` 4085. Sono **1.261.641 gradi di libertà** (tre
  per nodo), di cui 1.247.427 liberi dopo il vincolo dei 4738 nodi di `BASE`.
  Una versione precedente di questa sezione riportava qui 216.967 punti e
  635.336 elementi: erano i numeri della mesh troncata, rimasti dopo che il deck
  era stato rigenerato senza il tetto ai punti di Steiner, e la lettura è stata
  rifatta sul deck corrente;
- **in soluzione da CalculiX 2.22**, tramite la prova di fattibilità
  `tests/feasibility/test_calculix.py`, che risolve un deck scritto dallo stesso
  `abaqus.export_model` e ne rilegge gli spostamenti. La prova passa su questa
  macchina.

La soluzione con CalculiX del deck completo del muro, 1.752.795 elementi e
1.261.641 gradi di libertà, non è stata tentata: con 16 GB di RAM, di cui 7
liberi, un solutore diretto su un sistema di quella taglia rischia di finire in
swap, e la macchina è condivisa con un'altra elaborazione in corso. La taglia
reale è quasi il doppio di quella che questa sezione stimava prima della
rigenerazione del deck. È un controllo utile ma rinviabile, perché la validità
del formato è già coperta dalle due verifiche sopra.

## Riepilogo dei criteri di accettazione

| Criterio | Esito |
|---|---|
| Il test di integrazione passa | Sì: **111 test passati** in 22 s, 5 prove di fattibilità passate, 1 saltata (`wildmeshing` non installabile su Windows) |
| Le metriche di errore geometrico sono calcolate e riportate | Sì: `07_surface_quality.geometric_error`, Hausdorff 54,18 mm, RMS 5,16 e 9,77 mm |
| La pipeline arriva in fondo sul muro sintetico | Sì, in circa 98 secondi, dopo la correzione di `repair.hole_loops` e la rimozione del tetto ai punti di Steiner |
| La pipeline arriva in fondo sulla scansione reale `lab_frame.pcd` | **No**: gli step 1–8 girano, lo step 9 non converge con alcun `min_ratio` provato fino a 4,0. Esito misurato e documentato in [`fase-1-esiti-lab-frame.md`](fase-1-esiti-lab-frame.md) § 5 |
| La segmentazione automatica su `lab_frame.pcd` | Vedi [`fase-1-esiti-lab-frame.md`](fase-1-esiti-lab-frame.md) |
| La stessa configurazione rieseguita dà lo stesso risultato | Coperto da `test_the_same_configuration_run_twice_gives_the_same_result`; il costo della scelta è misurato qui sopra |
| Il deck è valido | Parziale: `meshio` e CalculiX sì, controllo dei dati Abaqus dovuto |
