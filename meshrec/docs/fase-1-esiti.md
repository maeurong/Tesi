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

Con questi parametri la pipeline completa gira in **circa 60 secondi**, dalla
lettura della nuvola alla scrittura del deck.

## Metriche di ogni step

I numeri seguenti vengono da `runs/muro/metrics.json` di una corsa pulita
dall'inizio.

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

**Step 7 — qualità della superficie.** 116.967 vertici, 233.930 triangoli,
superficie chiusa con zero spigoli di bordo, area 121,57 m², volume racchiuso
53,87 m³. Il rapporto d'aspetto dei triangoli ha mediana 1,394 e media 2,009,
con un massimo di 3968: la coda di triangoli molto allungati è quella lasciata
dalla chiusura, e non impedisce la tetraedrizzazione.

**Step 8 — semplificazione.** Disabilitata: 233.930 triangoli in ingresso e in
uscita.

**Step 9 — tetraedrizzazione.** TetGen con rapporto raggio-spigolo 1,1 e nessun
vincolo di volume massimo: 216.967 nodi e **635.336 tetraedri** in 12,77
secondi.

**Step 10 — qualità del volume.** **Zero elementi invertiti**, volume totale
53,87 m³ coerente con quello della superficie. L'angolo diedro minimo ha mediana
6,04° e media 15,08°, con un minimo di 0,00084°; il rapporto d'aspetto ha
mediana 20,82 e massimo 2,1 × 10⁵. La mesh è dunque valida ma con una coda di
elementi molto schiacciati, che è esattamente il problema su cui interviene il
confronto con Gmsh più avanti.

**Step 11 — esportazione.** Deck scritto in `wall_model.inp` (37,5 MB) e
`wall_model.vtu`. Volume 53,87 m³, massa **96,97 t** con la densità di 1,8 ×
10⁻⁹ t/mm³. Insiemi di nodi estratti con tolleranza 44,80 mm: `BASE` 382,
`TOP` 452, `FACE_FRONT` 82.837, `FACE_BACK` 49.918, `SIDE_LEFT` 435,
`SIDE_RIGHT` 390.

Su quest'ultimo step va segnalata un'anomalia che merita un controllo in Fase 2.
L'allineamento ai piani principali riporta un ingombro di 1270,4 × 7422,1 ×
8887,6 mm, mentre la nuvola sorgente misura 1247,0 × 5823,8 × 7802,1 mm anche
calcolando le sue direzioni principali, che coincidono con gli assi globali. La
matrice di rototraslazione contiene una rotazione di circa 13,4° nel piano del
muro, e i due ingombri anomali sono esattamente quelli che un rettangolo di
5823 × 7802 mm produce se il riferimento viene ruotato di quell'angolo
(5823·cos13,4° + 7802·sin13,4° ≈ 7473, e 5823·sin13,4° + 7802·cos13,4° ≈ 8939).
Le direzioni principali calcolate sui nodi del volume non ritrovano quindi gli
assi del muro. Lo squilibrio fra `FACE_FRONT` (82.837 nodi) e `FACE_BACK`
(49.918) punta nella stessa direzione. Poiché il deck vincola l'insieme `BASE`,
che con questo allineamento conta appena 382 nodi, la questione tocca la
validità dell'analisi e non solo l'estetica del riferimento: va chiarita prima
di dare per buoni i risultati tensionali.

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

Resta da correggere, nel documento di Fase 0, l'attribuzione della misura: quei
due numeri riguardano l'ottimizzatore interno di Gmsh e un indice di qualità
adimensionale, non il confronto con TetGen sull'angolo diedro. Il confronto con
TetGen è quello riportato qui.

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
tempo, su una ricostruzione che pesa comunque meno del 10% dei circa 60 secondi
dell'intera pipeline. Il conteggio di vertici e triangoli coincide fra le due
configurazioni: a cambiare con più thread è l'ordine, non la taglia del
risultato. **Il valore predefinito resta 1**: questa misura documenta un
compromesso accettato, non lo mette in discussione.

## Stato del controllo dei dati con Abaqus

Il controllo dei dati con Abaqus (`*DATACHECK`) è **non eseguito**, perché
Abaqus non è disponibile su questa macchina. Resta dovuto, ed è la sola verifica
del deck ancora aperta.

Il deck prodotto è però verificato per altre due vie, entrambe eseguite:

- **in lettura da `meshio`**, direttamente sul file di questa esecuzione:
  `runs/muro/wall_model.inp` viene riletto senza errori, restituendo 216.967
  punti, 635.336 elementi `tetra` e i sei insiemi di nodi `BASE`, `TOP`,
  `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`;
- **in soluzione da CalculiX 2.22**, tramite la prova di fattibilità
  `tests/feasibility/test_calculix.py`, che risolve un deck scritto dallo stesso
  `abaqus.export_model` e ne rilegge gli spostamenti. La prova passa su questa
  macchina.

La soluzione con CalculiX del deck completo del muro, 635.336 elementi e circa
650.000 gradi di libertà, non è stata tentata: con 16 GB di RAM, di cui 7
liberi, un solutore diretto su un sistema di quella taglia rischia di finire in
swap, e la macchina è condivisa con un'altra elaborazione in corso. È un
controllo utile ma rinviabile, perché la validità del formato è già coperta
dalle due verifiche sopra.

## Riepilogo dei criteri di accettazione

| Criterio | Esito |
|---|---|
| Il test di integrazione passa | Sì: 99 test passati, 5 prove di fattibilità passate, 1 saltata (`wildmeshing` non installabile su Windows) |
| Le metriche di errore geometrico sono calcolate e riportate | Sì: `07_surface_quality.geometric_error`, Hausdorff 54,18 mm, RMS 5,16 e 9,77 mm |
| La pipeline arriva in fondo sul muro sintetico | Sì, in circa 60 secondi, dopo la correzione di `repair.hole_loops` |
| La segmentazione automatica su `lab_frame.pcd` | Vedi [`fase-1-esiti-lab-frame.md`](fase-1-esiti-lab-frame.md) |
| La stessa configurazione rieseguita dà lo stesso risultato | Coperto da `test_the_same_configuration_run_twice_gives_the_same_result`; il costo della scelta è misurato qui sopra |
| Il deck è valido | Parziale: `meshio` e CalculiX sì, controllo dei dati Abaqus dovuto |
