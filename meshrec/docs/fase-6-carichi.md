# Fase 6 — carichi posizionati su una mesh senza topologia

Data di chiusura: 22 agosto 2026. Corsa dimostrativa: `runs/lab_telaio_v4_posizionati`,
generata in questa sessione sul ramo `feat/impronta-carichi` (HEAD `7d31c1d`)
a partire dagli stessi artefatti geometrici di `runs/lab_telaio_v2` — stessa
nuvola, stesso ritaglio, stessa superficie riparata, stessa tetraedrizzazione —
con in più il blocco `selettori` e due `carichi.posizionati` che questa fase
introduce. Ogni numero di questo documento porta accanto **il file e il campo
da cui viene**. Lo script che li riproduce tutti è
[`docs/fase-6-cantiere/misura-carichi.py`](fase-6-cantiere/misura-carichi.py):

```
uv run python docs/fase-6-cantiere/misura-carichi.py
```

Ogni valore che quello script stampa porta il proprio `assert` contro il
valore pubblicato qui, sul modello di
[`docs/fase-5-cantiere/misura-deficit.py`](fase-5-cantiere/misura-deficit.py):
se la corsa cambia, lo script cade invece di stampare in silenzio un numero
diverso da quello scritto.

---

## 1. Il problema

Un modello as-built ricostruito da una scansione non ha topologia: non esiste
una faccia nominata «trave superiore», né uno spigolo a cui appoggiarsi per
dire «qui». `runs/lab_telaio_v2/12_wall.json` lo dichiara nel proprio campo
`membrature`, vuoto — otto regioni trovate, zero membrature accettate. Il
programma non ha, e non può avere su questa geometria, un vocabolario di parti
nominate.

Gli unici indirizzi che il deck contiene oggi sono i sei insiemi di nodi che
`build_node_sets` (`core/abaqus.py:1078`) **ricalcola dalle coordinate a ogni
esportazione** — `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`,
`SIDE_RIGHT`. Non sono memorizzati da nessuna parte fra un'esportazione e
l'altra: sono il risultato di un criterio geometrico (minimo e massimo di ogni
asse più una tolleranza), riapplicato ex novo ogni volta che lo step 11 gira.
Una lista di indici di nodo scritta a mano, invece, non sopravviverebbe a un
remesh: gli indici cambierebbero significato in silenzio, e chi legge il
report non avrebbe modo di accorgersene.

La Fase 6 introduce un terzo modo di indirizzare i nodi, accanto ai sei
insiemi di faccia e a quelli che il prior geometrico potrebbe un giorno
scoprire: il **selettore**, una regola geometrica dichiarata dall'operatore
nella configurazione. Un selettore non è un elenco di indici: è una *regola*
— «i nodi dentro questo parallelepipedo», «il nodo più vicino a questo punto»
— che si scrive una volta nello YAML, si diffa come ogni altro campo della
configurazione, e viene **risolta di nuovo** a ogni esportazione sulla mesh
del momento. Se un remesh sposta gli indici, il selettore non se ne accorge:
richiede semplicemente di nuovo gli stessi nodi, con lo stesso criterio, sulla
geometria nuova. È un indirizzo durevole in un senso preciso: sopravvive alla
cosa che lo ha reso necessario, cioè l'assenza di topologia.

---

## 2. Il selettore

Il blocco `selettori:` vive alla radice della configurazione
(`PipelineConfig.selettori`, `core/config.py:824`), come un dizionario da nome
a regola. Quattro forme sono ammesse, tutte definite in `core/config.py:660-719`:

- **`box`** (`SelettoreBox`) — tutti i nodi dentro un parallelepipedo allineato
  agli assi del modello, dati `min` e `max`.
- **`sfera`** (`SelettoreSfera`) — tutti i nodi entro un raggio da un centro.
- **`nodo`** (`SelettoreNodo`) — il singolo nodo più vicino a un punto dato.
- **`nset`** (`SelettoreNset`) — un insieme di nodi già scritto nel deck, per
  nome (tipicamente uno dei sei di faccia).

Le coordinate delle prime tre forme sono nel sistema di riferimento **dopo**
`align_to_axes`, lo stesso di `wall_model.vtu` e del deck: è il maglio che il
solutore vede, non la nuvola grezza. La risoluzione vera e propria — da regola
a indici di nodo — vive in un modulo a sé, `core/selezione.py`, che non sa
nulla di deck: prende array di nodi ed elementi e rende indici (`risolvi`,
`core/selezione.py:67`; `risolvi_tutti`, `core/selezione.py:132`).

La corsa dimostrativa dichiara un selettore per ciascuna delle quattro forme,
su `lab_telaio_v4_posizionati.yaml`. I nodi risolti e la bbox reale, dal campo
`11_export.selettori` di `runs/lab_telaio_v4_posizionati/metrics.json`:

| selettore | tipo | regola dichiarata | nodi presi | bbox reale dei nodi presi [mm] |
|---|---|---|---:|---|
| `piastra` | box | `min=[300,1200,1650]`, `max=[600,1500,1799.73]` | **365** | x 340,8–529,8 · y 1200,7–1497,5 · z 1650,5–1796,4 |
| `angolo` | sfera | centro `[700,2400,1750]`, raggio 250 mm | **158** | x 459,6–521,5 · y 2225,3–2456,0 · z 1583,3–1797,6 |
| `punta` | nodo | punto `[418,46; 1956,82; 1798,73]` | **1** | il nodo a 1,73 mm dal punto dichiarato |
| `appoggio` | nset | `nome: BASE` | **3719** | x 0,0–875,2 · y 15,3–2698,2 · z 0,0–132,0 |

Il selettore `punta` merita una parola: per costruzione non può mai risolvere
zero nodi — un `argmin` un vincitore ce l'ha sempre, fosse anche a chilometri
di distanza (`core/selezione.py:89-102`) — quindi il suo oracolo non è «zero
nodi» ma «il vincitore è troppo lontano perché il punto dichiarato sia un
indirizzo e non un errore di battitura» (si veda la tabella del § 3). Nella
corsa dimostrativa il punto dichiarato è a 1,73 mm dal nodo più vicino, ben
dentro la soglia di 67,48 mm (tre spigoli medi da 22,49 mm, misurati sulla
stessa mesh — `core/selezione.py:36`, `SPIGOLI_DI_TOLLERANZA = 3`).

Il selettore `appoggio` mostra la quarta forma nel modo più diretto: cita
semplicemente `BASE`, e riceve gli stessi 3.719 nodi che `build_node_sets` ha
già costruito per il vincolo — nessun ricalcolo, nessuna duplicazione.

---

## 3. La validazione

Cinque ingressi diversi — una box con `min > max`, una box piatta, una box
fuori dai limiti della mesh, un raggio nullo, un raggio negativo — danno oggi
lo stesso identico sintomo se non vengono fermati prima: zero nodi risolti sui
14.103 della mesh. Un oracolo unico a valle non potrebbe dire quale delle
cinque condizioni è successa. La Fase 6 divide perciò la validazione in due
gruppi, secondo se serve o no la mesh per giudicare.

**A monte, in `core/config.py`, senza aver letto una nuvola.** Ogni riga di
questa tabella è stata effettivamente provocata in questa sessione, e il
messaggio è copiato dall'esecuzione vera (`docs/fase-6-cantiere/misura-carichi.py`
la riproduce):

| condizione | esito |
|---|---|
| `min > max` su una componente della box | *"la box ha min > max sulla componente y: 9.0 > 1.0. Risolverebbe zero nodi, con lo stesso sintomo di altre quattro condizioni diverse, e nessuno saprebbe quale sia successa"* |
| `raggio <= 0` sulla sfera | *"Input should be greater than 0"* (il vincolo `gt=0.0` di pydantic sul campo `raggio`) |
| nome di selettore uguale a uno dei sei di faccia, ignorando il caso | *"il selettore 'BASE' collide, ignorando le maiuscole, con il set di faccia 'BASE' che il deck fabbrica da se': nel deck c'e' un solo spazio di nomi, case-insensitive [...], e il \*NSET dell'operatore lo sovrascriverebbe"* |
| carico che cita un selettore non dichiarato | *"il carico 'PRESSA' cita il selettore 'fantasma', che non e' dichiarato. Dichiarati: ['piastra']"* |
| due chiavi YAML omonime sotto `selettori:` | *"la chiave 'angolo' compare due volte nello stesso blocco [...]: il lettore terrebbe l'ultima e la prima sparirebbe senza un segnale"* |
| nome di carico riservato (uguale a un passo già preso, ignorando il caso) | *"il carico 'CARICO_TOP' porta il nome del passo 'CARICO_TOP', gia' preso. I riservati sono ['SPINTA_ORIZZONTALE', 'CARICO_TOP', 'MODALE'] [...]"* |
| selettore dichiarato e mai citato da alcun carico | **non è un errore**: dichiarare e non usare è un appunto, non un difetto |

Sul confronto che ignora il caso vale una precisazione, perché non è
un'eleganza gratuita: è misurata. `docs/fase-6-cantiere/sonda-caso-nomi/README.md`
documenta che `ccx` 2.22 risolve un `*NSET` **senza distinguere le
maiuscole**: un selettore chiamato `base` collide comunque con `BASE` nel
deck, anche se le due stringhe Python sono diverse. Il validatore normalizza
perciò il confronto su entrambi i lati (`core/config.py:836-866` per i
selettori, `:868-906` per i nomi di carico), altrimenti rifiuterebbe un errore
di battitura in un caso e ne lascerebbe passare uno identico nell'altro.

Il rifiuto delle chiavi YAML omonime ha un posto a sé perché è, fra tutti
questi, l'unico ingresso degenere **senza un sintomo a valle**: gli altri
cinque almeno risolvono zero nodi, un fatto che si può controllare. Due chiavi
omonime, lette con `yaml.safe_load` di serie, si risolvono in silenzio — la
prima sparisce e nessuno se ne accorge finché il carico non si comporta in
modo inatteso. `core/config.py:911-935` sostituisce il lettore con
`_LoaderChiaviUniche`, una sottoclasse di `yaml.SafeLoader` — non di
`yaml.Loader` — che aggiunge il controllo senza aprire l'esecuzione di codice
arbitrario che il loader non sicuro permetterebbe. La stessa lettura
(`carica_yaml`, `core/config.py:938`) serve sia `load_config` sia
`load_experiment`: due funzioni, una sola porta d'ingresso.

**A valle, con la mesh già risolta.** Fra 1 e 14.103 nodi nessuna soglia può
giudicare da sola se un selettore è ragionevole: si può solo mostrare quanti
nodi ha preso, ed è per questo che il resoconto dei selettori (§ 7) si scrive
**sempre**, anche quando la risoluzione passa senza incidenti.

| condizione | esito |
|---|---|
| il selettore risolve **0 nodi** | *"il selettore 'lontana' risolve zero nodi. Estensione della mesh: min [0.0, 0.0, 0.0], max [10.0, 10.0, 10.0]. Un carico applicato a nulla non e' un carico"* |
| il selettore prende **tutti** i nodi | *"il selettore 'tutto' prende tutti i 8 nodi della mesh. Una risultante spalmata sull'intero solido non e' un carico posizionato, e' un peso proprio storto"* |
| `tipo: nodo`, il più vicino oltre tre spigoli medi | *"il selettore 'persa' chiede il nodo piu' vicino a (1000.0, 0.0, 0.0), e il piu' vicino sta a 990.0 mm, oltre i 30.0 mm di 3 spigoli medi (10.00 mm). Un argmin un vincitore ce l'ha sempre, anche a chilometri: questo non e' un indirizzo, e' un punto scritto male"* |
| area tributaria totale nulla (il selettore non tocca alcuna faccia di bordo intera) | *"il carico 'interno' agisce su 1 nodi che non formano alcuna faccia di bordo: nessuna area su cui ripartire la risultante. Un selettore tutto interno al solido produce questo, e un carico applicato a nulla non e' un carico"* |

Sulla mesh reale del caso studio, lo spigolo medio misurato è **22,49 mm**
(`runs/lab_telaio_v2/metrics.json`, `11_export.boundary_spacing`), quindi la
soglia dei tre spigoli vale **67,48 mm**: un punto scritto per errore a
qualche centinaio o migliaio di millimetri di distanza — il caso tipico di un
segno sbagliato o di un'unità confusa — cade ben oltre.

---

## 4. La ripartizione

Fino alla Fase 5, l'unico carico applicato a un insieme di nodi (`carico_sommita`)
si ripartiva **uniformemente per nodo**: `core/abaqus.py` divideva la
risultante dichiarata per il numero di nodi dell'insieme, e ogni nodo riceveva
la stessa quota. Il docstring di `CaricoSommita` lo dichiarava già come un
limite noto: la ripartizione si concentra dove i nodi sono più fitti, che è
una proprietà del maglio della mesh, non della struttura reale. Due zone della
stessa superficie, una scansionata più densamente dell'altra, avrebbero
ricevuto quote diverse pur essendo fisicamente equivalenti.

La Fase 6 passa alla **pesatura per area tributaria**, e la applica sia ai
nuovi `carichi.posizionati` sia a `carico_sommita`: un programma non può
ripartire in due modi diversi due carichi che fanno la stessa cosa. Il calcolo
(`aree_tributarie`, `core/abaqus.py:567`) è gemello di `surface_area`
(`core/abaqus.py:539`, già esistente dalla Fase 4): stesso ciclo sulle facce
di bordo, stesse tabelle di elemento, stesso ventaglio triangolare dal primo
nodo di ogni faccia — ma l'accumulo va in un array indicizzato per nodo invece
che in uno scalare, un terzo dell'area di ogni triangolo a ciascuno dei suoi
tre nodi. Le facce su cui si somma sono quelle di bordo **interamente
contenute** nell'insieme del selettore (`element_surface`, già esistente): una
faccia con tre nodi su quattro nell'insieme non entra, perché non è quella
faccia. `ripartisci` (`core/abaqus.py:605`) normalizza le quote sul totale,
così la somma delle forze scritte nel deck è sempre esattamente la risultante
dichiarata — verificato con un `assert` sul deck scritto, non per fede.

Un nodo dentro l'insieme ma non toccato da alcuna faccia di bordo intera
prende zero, e il resoconto lo conta (§ 7); se **nessun** nodo tocca una
faccia — un selettore tutto interno al solido, per esempio — l'area totale è
nulla e la funzione solleva (tabella del § 3): pesare su zero non ha nulla su
cui pesare, e scrivere zero ovunque descriverebbe un carico applicato a
nulla, non un carico piccolo.

Il costo del cambiamento è la rimisura di `CARICO_TOP` sulla corsa
`runs/lab_telaio_v2`, che la Fase 5 aveva pubblicato con la ripartizione
vecchia. Il confronto, misurato in questa sessione su
`runs/lab_telaio_v3_pesata/wall_model.inp` (stessa geometria e stessa
configurazione di `lab_telaio_v2`, risolta di nuovo con la sola ripartizione
di `CARICO_TOP` cambiata):

| | prima (uniforme per nodo) | dopo (area tributaria) |
|---|---|---|
| righe `*CLOAD` | 3.036 | 3.036 |
| valore per riga | uno solo, **−0,395257 N** (1200 / 3036, `runs/lab_telaio_v2/config.yaml:77` e `metrics.json`, `11_export.node_sets.TOP`) | **2.334 valori distinti**, da 0 a **−0,867866 N** |
| somma | −1.200,000000 N | **−1.200,000000 N** (verificato, scarto sotto 1e-3 N) |
| nodi ad area tributaria nulla | *(nessun concetto: tutti ricevevano una quota)* | **703** su 3.036 |

I 703 nodi ad area nulla sono la parte più concreta del cambiamento: sono
nodi dentro la fascia `TOP` (spessa 134,97 mm, non una faccia) che non toccano
alcuna faccia di bordo intera — per esempio perché stanno sotto la cresta
della fascia, coperti da altri nodi più esterni. Con la ripartizione vecchia
ciascuno di quei 703 nodi riceveva comunque 0,395257 N, per un totale di
circa **278 N** (703 × 0,395257) assegnati a nodi senza superficie su cui
reggerli — il **23%** dei 1.200 N dichiarati, appoggiato su un fatto
geometrico della mesh e non della struttura. Con la ripartizione nuova quei
nodi ricevono zero, e la stessa risultante si concentra sui 2.333 nodi che
hanno davvero una faccia da cui prenderla.

Il picco di von Mises sotto `CARICO_TOP`, misurato sulla stessa corsa
(`13_solution.vtu`, campo `VM_CARICO_TOP`): **0,9811 → 0,9809 MPa**, uno
scostamento dello **0,03%** — praticamente immobile, a fronte di una
ridistribuzione tutt'altro che piccola dei singoli valori nodali. Non è
un'omissione, è un risultato coerente con dove vive il picco: sullo stesso
nodo delle altre due condizioni di carico, nella trave superiore, fuori dalla
fascia `TOP` che la ripartizione ridisegna (`docs/fase-5-analisi.md`, §
«I cinque controlli»). `GRAVITA`, `SPINTA_ORIZZONTALE` e `MODALE` non usano
questa ripartizione e non cambiano.

---

## 5. Il momento

### 5.1 Perché non un `*CLOAD` sui gradi 4-6

Un elemento solido C3D4 ha tre gradi di libertà per nodo — le tre traslazioni
— e nessun grado rotazionale. Scrivere un `*CLOAD` sui gradi 4, 5 o 6 di un
tale elemento è sintatticamente valido, e `ccx` 2.22 lo **scarta in
silenzio**: zero occorrenze di `warning` o `error`, `number of equations 3`
(le sole traslazioni sono viste come incognite), spostamento
`0.000000E+00` su tutte e tre le componenti. La guardia del progetto contro i
deck sospetti — zero `*WARNING` da `ccx` o i numeri non sono citabili
(`core/solve.py:438`) — non può intercettare questo caso, perché non c'è
alcun avviso da intercettare: il deck è valido, gira, e non fa nulla.

Il momento si realizza perciò come **coppia di forze staticamente
equivalente**, scritta con le stesse card `*CLOAD` di un carico concentrato
(`coppia_equivalente`, `core/abaqus.py:646`), non come un momento vero e
proprio.

### 5.2 Il braccio dichiarato, il braccio effettivo

Due vie erano aperte: il programma misura da sé il braccio della coppia
sull'estensione reale dei nodi presi, oppure l'operatore lo dichiara e il
programma lo verifica. La seconda vince — un numero mostrato senza un
controllo che lo possa smentire non vale più di un numero assente, e la prima
via non chiederebbe nulla ma deciderebbe da sé, senza che nessuno la possa
contraddire.

Il controllo: proiettati i nodi del selettore sul piano perpendicolare
all'asse dichiarato, si trova per via di SVD la direzione di massima
estensione in quel piano — la direzione lungo cui i nodi si separano meglio —
e si misura quanto i nodi si estendono in quella direzione. Se il `braccio`
dichiarato supera quell'estensione, la funzione solleva e riporta entrambi i
numeri (dichiarato e disponibile), perché l'operatore possa correggere il
dato giusto. Superato il controllo, i nodi si dividono in due gruppi — quelli
oltre `+braccio/2` e quelli oltre `−braccio/2` lungo la direzione scelta — e
dentro ciascun gruppo la forza si ripartisce per area come al § 4. Se un lato
resta senza nodi, o senza area tributaria, la funzione solleva: una coppia con
una sola forza è una forza, non un momento.

**Il momento realizzato è esattamente quello dichiarato, ma il braccio no.**
I due gruppi raccolgono nodi *oltre* metà del braccio dichiarato in ciascuna
direzione, quindi i loro baricentri pesati distano fra loro **più** del
braccio dichiarato — è il **braccio effettivo**. La forza di ciascun lato si
calibra su di esso (`modulo / braccio_effettivo`), non sul braccio dichiarato:
così il `modulo` che l'operatore ha scritto è esattamente quello che il deck
applica, e il `braccio` dichiarato conserva il solo ruolo che gli compete —
scegliere i due gruppi, non fissare la leva della forza. Il resoconto (§ 7)
scrive entrambi i bracci accanto al momento, perché la differenza fra i due
è una cosa da guardare, non da nascondere.

Sulla corsa dimostrativa, il carico `TORSIONE` (momento sull'asse z, modulo
500.000 N·mm, braccio dichiarato 800 mm, sul selettore `appoggio` = `BASE`,
3.719 nodi): **559 nodi** nel gruppo positivo, **218** nel negativo, braccio
effettivo **2.116,40 mm** — 2,6 volte il dichiarato, perché `BASE` si
estende su tutta la larghezza del telaio e i due gruppi, presi oltre ±400 mm
dal centro, arrivano quasi ai due estremi (`runs/lab_telaio_v4_posizionati/metrics.json`,
`11_export.carichi_posizionati.TORSIONE`).

### 5.3 La prova su `ccx` vero: la coppia sposta, la card sul grado 4 no

La differenza fra un momento scritto come coppia e uno scritto (per errore)
sui gradi 4-6 non si vede leggendo il deck: si vede solo dando entrambi a un
solutore vero. Rigiocati in questa sessione i due banchi di
`tests/feasibility/test_calculix.py` (colonna 100×100×400 mm, materiale di
prova, `ccx` 2.22 su questa macchina arm64):

- **Una forza posizionata** (−1.000 N verticali sulla sommità): il deck esce
  `Job finished`, zero `*WARNING`, zero `*ERROR`. Le reazioni sul passo che
  porta il carico: **(−9e-6, 2,2e-6, 1067,534) N** — contro i 1.000 N
  dichiarati più 70,63 N di peso proprio atteso in forma chiusa
  (1.070,63 N): lo scarto, 0,29%, è la discretizzazione tetraedrica del box,
  che non riproduce il volume esatto del solido continuo.
- **Un momento come coppia** (modulo 50.000 N·mm sull'asse z, braccio 60 mm):
  zero `*WARNING`, zero `*ERROR`, e lo spostamento orizzontale
  massimo vale **0,056761 mm** — contro un rumore di fondo di **1,77e-5 mm**
  sotto la sola gravità sullo stesso banco (l'asimmetria della mesh muove
  qualcosa anche senza carichi orizzontali). La coppia sposta **circa 3.200
  volte** più del rumore.

La stessa combinazione scritta come `*CLOAD` sui gradi 4-6 di un C3D4, invece,
esce anch'essa a zero avvisi — ma con spostamento esattamente `0.000000E+00`:
il solutore l'ha letta, l'ha accettata, e non ha fatto nulla. È la prova che
questo documento doveva portare per intero: due deck ugualmente validi
agli occhi di `ccx`, uno dei quali non applica il carico che promette.

### 5.4 Un difetto trovato: il `*CLOAD` di un passo resta attivo nel successivo

La corsa dimostrativa di questo documento è la prima, in tutto il progetto, a
scrivere **due passi statici consecutivi che portano entrambi un `*CLOAD`**:
`PRESSA` (la forza posizionata) seguito da `TORSIONE` (il momento come
coppia). Fino a questa fase non era mai successo: `SPINTA_ORIZZONTALE` usa
`*DLOAD`, non `*CLOAD`, e `CARICO_TOP` è sempre stato l'ultimo passo statico
del deck, senza nulla dopo di sé che potesse risentirne.

Le reazioni misurate sul deck della corsa dimostrativa
(`runs/lab_telaio_v4_posizionati/13_solution.dat`) mostrano una cosa che il
progetto non si aspettava:

| passo | Σfz misurata |
|---|---:|
| `GRAVITA` | 4.162,392140 N |
| `PRESSA` (peso + forza da −1.000 N) | **5.162,392212 N** |
| `TORSIONE` (peso + coppia, risultante netta nulla) | **5.162,392212 N** |

Una coppia ha risultante netta nulla per costruzione: se il passo `TORSIONE`
portasse solo il proprio carico più il peso proprio, la sua reazione dovrebbe
tornare a **4.162,39 N**, uguale a `GRAVITA`. Invece coincide, a sette cifre,
con quella del passo `PRESSA` precedente: il `*CLOAD` da −1.000 N scritto per
`PRESSA` **è ancora attivo** durante la soluzione di `TORSIONE`, sommato al
carico che quel passo dichiara davvero.

Una sonda minima, isolata e committata
(`docs/fase-6-cantiere/sonda-cload-persiste/`), conferma la causa: un
tetraedro solo, tre passi statici identici a parte i carichi. Il primo
dichiara un `*CLOAD` di −100 N; il secondo **non dichiara alcun `*CLOAD`**; il
terzo dichiara `*CLOAD, OP=NEW` senza righe. Le reazioni misurate sul set
vincolato:

| passo | `*CLOAD` dichiarato | Σfz misurata |
|---|---|---:|
| 1 | −100 N | 100,0 N |
| 2 | *(nessuno)* | **100,0 N** |
| 3 | `OP=NEW` (vuoto) | **0,0 N** |

Il passo 2 eredita i 100 N del passo 1 pur non dichiarando nulla di suo: un
`*CLOAD` scritto in un passo statico **resta attivo in ogni passo successivo**
finché qualcosa non lo sostituisce o non lo azzera esplicitamente con
`*CLOAD, OP=NEW`. `write_inp` (`core/abaqus.py`) non scrive mai quella card
fra un passo e il successivo.

**Questo è un difetto del programma, non un limite dichiarato.** Il § 8 di
questo documento riporta, come lo riporta la configurazione approvata di
questa fase, che «ogni carico dichiarato è un passo statico a sé, col solo
peso proprio accanto» — ed è vero per come lo **schema** della configurazione
è fatto: non esiste un modo di chiedere che due carichi si sommino in un
passo solo. Ma il deck che `write_inp` scrive **non realizza** quella
promessa quando più di un carico basato su `*CLOAD` compare in sequenza — due
`carichi.posizionati`, oppure un `carico_sommita` seguito da un posizionato.
Ogni passo dopo il primo che porta un `*CLOAD` include, senza che nulla lo
segnali, anche il carico di ogni passo precedente che ne aveva scritto uno.
Zero avvisi, zero errori, spostamenti e reazioni tutti finiti e plausibili —
esattamente la forma di errore silenzioso che questa fase esiste per stanare,
questa volta prodotta dal programma stesso invece che da `ccx`.

Non è stato corretto in questa sessione: la correzione (una card
`*CLOAD, OP=NEW` prima di ogni passo che dichiara un carico posizionato o
`carico_sommita`, quando esiste un passo precedente con un `*CLOAD` proprio)
tocca `core/abaqus.py` ed è un cambio di codice, fuori dal perimetro di questo
compito. È il primo elemento della coda al § 9, e va risolto prima che una
configurazione con più di un carico basato su `*CLOAD` in sequenza sia
considerata affidabile.

---

## 6. Il momento fuori asse, e perché la sua soglia è quel numero

### 6.1 Da dove viene una componente fuori asse

`coppia_equivalente` sceglie i due gruppi della coppia proiettando i nodi del
selettore sul piano perpendicolare all'asse dichiarato, e separandoli lungo la
direzione di massima estensione in quel piano. Il momento che il deck scrive
**davvero** — ricostruito dalle stesse forze per nodo che finiscono nelle
righe `*CLOAD`, non dal `modulo` dichiarato — vale, per costruzione
geometrica:

```
momento_effettivo = forza · [(β₀ − β₁) · a + (α₁ − α₀) · s]
```

dove `a` è la direzione di separazione (l'estensione della coppia), `s` è
l'asse dichiarato, `β₀`/`β₁` sono le posizioni medie pesate dei due gruppi
lungo `a`, e `α₀`/`α₁` le loro posizioni medie lungo `s`. Il primo termine è
il momento voluto, in asse. Il secondo termine — quello che genera la
componente **fuori** asse — si annulla **solo se** `α₁ = α₀`: solo se i due
gruppi della coppia stanno, in media, alla **stessa quota lungo l'asse del
momento**. Geometricamente, solo se il selettore giace in un piano
perpendicolare all'asse. Non è un problema di sistema di riferimento: cambiare
la terna non tocca questo termine, perché `α₁ − α₀` è una proprietà della
distribuzione dei nodi lungo l'asse dichiarato, non del modo in cui le
coordinate sono scritte.

Un selettore **planare** rispetto all'asse (`TOP`, rispetto a un momento
sull'asse z, se `TOP` fosse un piano vero) ha `α₁ − α₀ = 0` per costruzione:
il secondo termine è esattamente zero. Un selettore **volumetrico** che si
estende lungo l'asse del momento no: i due gruppi, separati lungo la
direzione orizzontale, possono benissimo avere quote medie diverse lungo
l'asse, e il secondo termine non si annulla.

### 6.2 Le due misure, sulla mesh reale e su un caso volumetrico

**`TOP` sull'as-built non è un piano: è una banda di nodi spessa 134,97 mm**
(`runs/lab_telaio_v2/metrics.json`, `11_export.set_tolerance`), il risultato
di una tolleranza applicata a una superficie reale, non un piano geometrico
perfetto. Misurato in questa sessione chiamando `coppia_equivalente` vera
(non una formula a parte) su `runs/lab_telaio_v2/wall_model.vtu`, i 3.036 nodi
di `TOP`, a tre bracci diversi:

| braccio [mm] | nodi (+/−) | rapporto fuori asse |
|---:|---|---:|
| 490,7 | 1.197 / 1.285 | **0,003552** |
| 1.226,6 | 768 / 741 | 0,003388 |
| 1.962,6 | 368 / 316 | 0,002783 |

Il peggiore dei tre è **0,003552**: piccolo, ma non zero, ed è la banda a
renderlo tale — non un errore, una proprietà di ogni superficie as-built
scansionata.

**Un selettore volumetrico che si estende sull'intera altezza del modello**
mostra l'altro estremo. Un box che prende un montante intero — x pieno, una
banda di y larga circa 1 metro all'estremità dove il telaio è più massiccio,
z dallo 0 ai 1.799,73 mm dell'intera altezza — risolve **7.571 nodi** sulla
stessa mesh. La sua estensione nel piano perpendicolare all'asse z (calcolata
dalla stessa SVD) vale **1.010,12 mm**; a un braccio di **505,06 mm** (metà di
quell'estensione), la funzione **rifiuta** con questo messaggio, copiato
dall'esecuzione vera:

> *"il momento 'SONDA' scriverebbe nel deck un momento effettivo di
> [71,96; 2452,97; 3000,00] N·mm: la componente fuori dall'asse dichiarato
> vale 8,180e-01 volte il modulo, oltre la tolleranza di 5e-02. I due gruppi
> presi non stanno alla stessa quota lungo l'asse del momento: usa un
> selettore che giaccia in un piano perpendicolare all'asse"*

Il rapporto fuori asse vale **0,818**: due ordini di grandezza sopra il caso
`TOP`. È esattamente l'effetto previsto — un selettore con piena estensione
lungo l'asse del momento separa i suoi due gruppi anche in quota, non solo
in orizzontale, e il secondo termine della formula smette di essere
trascurabile.

### 6.3 La soglia, e perché è quel numero

La soglia in codice — `TOLLERANZA_MOMENTO_FUORI_ASSE`, `core/abaqus.py:46` —
vale **5e-2**. Non è un numero scelto a occhio: è la **media geometrica** dei
due estremi appena misurati,

```
sqrt(0,003552 · 0,818) ≈ 0,0539  →  arrotondata a 5e-2
```

con due margini asimmetrici e voluti:

- **sopra** il peggiore dei casi as-built (0,003552): **~14,1×**;
- **sotto** il selettore volumetrico rappresentativo (0,818): **~16,4×**.

I due margini non pesano uguale, ed è per questo che la soglia non sta a metà
strada aritmetica fra i due numeri. **Sotto** soglia, un deck sospetto passa
e scrive un momento storto **in silenzio** — il guasto che questo controllo
esiste per chiudere. **Sopra** soglia, un caso legittimo viene rifiutato, ma
con un messaggio che l'operatore vede subito: rumoroso, non silenzioso. Il
margine da difendere con più cura è quello sopra, perché un errore silenzioso
costa più di un rifiuto rumoroso — ed è per questo che conta quanto vale il
margine sopra il caso reale peggiore, non la posizione a metà strada fra i
due estremi.

### 6.4 La nota che conta più di tutte: la prima taratura era sul banco sbagliato

La primissima versione di questo controllo era stata tarata su un banco di
prova **sintetico**: un parallelepipedo di test, la cui faccia superiore è —
per come `synth.box_mesh` costruisce il solido — un **piano geometrico
perfetto**. Su quel banco, un selettore planare (`TOP` del cubo) dà un
rapporto fuori asse **esattamente 0,0**: nessun rumore, nessuna banda,
nessuna dispersione. La soglia scelta di conseguenza fu **1e-6** — comodamente
sopra lo zero esatto del caso planare sintetico, e comodamente sotto il caso
volumetrico sintetico (anch'esso misurato, rapporto 0,8333).

**Con `TOLLERANZA_MOMENTO_FUORI_ASSE = 1e-6`, il caso studio di questa tesi
sarebbe stato rifiutato dal proprio programma.** Il rapporto reale di `TOP`
sull'as-built — 0,003552 nel peggiore dei tre bracci misurati, non meno di
0,0028 in nessuno dei tre — supera quella soglia di oltre tre ordini di
grandezza. Un momento dichiarato sul selettore `TOP` della mesh reale, con
qualunque braccio ragionevole, sarebbe stato respinto come «troppo fuori
asse» — non perché il momento fosse sbagliato, ma perché la soglia era stata
misurata su una geometria che non assomiglia a nessuna superficie
scansionata.

È l'esempio più netto che questa fase abbia prodotto del perché un numero
misurato su geometria sintetica non descrive il programma su dati veri. Un
banco di prova sintetico è **fatto apposta** per essere pulito — un piano
vero, spigoli esatti, nessun rumore di ricostruzione — ed è prezioso per
isolare la logica che si vuole testare. Ma tarare una soglia numerica su
quella pulizia significa tarare il programma per un mondo che non esiste
fuori dal test: la prima superficie reale che il controllo avrebbe incontrato
era, per costruzione, più rumorosa di qualunque cosa il banco sintetico
potesse mostrare. La correzione non è stata «allentare la soglia finché il
test passa»: è stata **misurare il caso reale peggiore che si aveva a
disposizione**, misurare anche il caso volumetrico che il controllo deve
continuare a rifiutare, e mettere la soglia dove la media geometrica dei due
la colloca — con il margine più stretto dei due dalla parte del rischio più
costoso, il rifiuto silenzioso.

---

## 7. Il resoconto

`metrics["11_export"]` porta oggi due chiavi in più rispetto a quanto la
Fase 5 aveva pubblicato: `selettori` e `carichi_posizionati`, entrambe scritte
**sempre**, indipendentemente da quanti nodi ciascun selettore abbia preso —
perché fra un nodo solo e tutti i nodi della mesh nessuna soglia può
giudicare da sola, e mostrare è l'unica risposta onesta (§ 3).

Un estratto reale, da `runs/lab_telaio_v4_posizionati/metrics.json`:

```json
"selettori": {
  "piastra": {
    "tipo": "box",
    "nodi": 365,
    "bbox": [[340.82, 1200.72, 1650.51], [529.77, 1497.49, 1796.40]]
  },
  "appoggio": {
    "tipo": "nset",
    "nodi": 3719,
    "bbox": [[0.0, 15.27, 0.0], [875.24, 2698.16, 132.01]]
  }
},
"carichi_posizionati": {
  "PRESSA": {
    "nodi": 365,
    "area_totale": 118692.63,
    "nodi_ad_area_nulla": 76,
    "forza_dichiarata": [0.0, 0.0, -1000.0],
    "forza_effettiva": [0.0, 0.0, -999.9999999999992]
  },
  "TORSIONE": {
    "nodi": 3719,
    "braccio_dichiarato": 800.0,
    "braccio_effettivo": 2116.397907135251,
    "momento_dichiarato": [0.0, 0.0, 500000.0],
    "momento_effettivo": [65.24, 6580.13, 499999.99999999994],
    "forza_di_ciascun_lato": 236.25046987350228,
    "nodi_positivi": 559,
    "nodi_negativi": 218,
    "estensione_disponibile": 2685.28
  }
}
```

Ogni selettore riporta il proprio tipo, quanti nodi ha preso e la bbox reale
di quei nodi — non la regola dichiarata, ma dove i nodi presi *stanno
davvero*, perché l'operatore possa collocare un selettore senza indovinare
alla cieca. Ogni carico posizionato riporta, per una forza, i nodi coinvolti,
l'area tributaria totale, quanti nodi non hanno toccato alcuna faccia di
bordo, e la forza effettivamente scritta contro quella dichiarata (§ 4); per
un momento, entrambi i bracci, entrambi i momenti (dichiarato ed effettivo), e
i due gruppi della coppia (§ 5-6). Il precedente comportamentale, già nel
progetto, è `app/server.py:617` — l'endpoint `/api/cluster`: il server
calcola, scrive, e risponde dicendo **cosa ha scelto e con quali numeri**,
mai un semplice «fatto».

---

## 8. Cosa la Fase 6 dichiara di non fare

Riportato per intero e alla lettera, come approvato in fase di progetto:

- **non ricostruisce topologia.** Nessuna faccia nominata, nessuno spigolo,
  nessuna membratura. Il selettore prende nodi per criterio geometrico, e
  basta.
- **non applica alcun carico distribuito sull'as-built.** Né una pressione
  vera né un carico direzionale. `ccx` 2.22 rifiuta la card `*DLOAD, TRVEC`
  con un errore fatale (misurato in una fase precedente), e un carico
  distribuito vero richiede di aprire `element_surfaces` sul percorso
  as-built, che oggi non li passa: è il primo cantiere della coda.
- **non identifica fisicamente le facce.** I nomi `FACE_FRONT`, `SIDE_LEFT` e
  compagni restano nomi di convenzione, come il docstring di `build_node_sets`
  già dichiara (`core/abaqus.py:1078`): la coppia di facce opposte è
  affidabile come coppia, l'attribuzione del singolo nome no.
- **non scrive momenti concentrati.** Un `*CLOAD` sui gradi 4-6 su un
  elemento solido è scartato in silenzio: si veda il § 5.
- **non combina due posizionati in un passo solo.** Ogni carico dichiarato è
  **pensato** come un passo statico a sé, col solo peso proprio accanto. Lo
  schema della configurazione non ha modo di chiedere una combinazione, e
  questa fase non gliene aggiunge uno — **ma**, come il § 5.4 documenta con
  le prove, il deck che il programma scrive oggi non realizza questa
  isolamento quando più di un carico basato su `*CLOAD` compare in sequenza:
  è un difetto trovato, non un limite scelto, e resta il primo elemento
  urgente della coda al § 9.

---

## 9. La coda

Cinque cantieri erano già stati lasciati fuori dal perimetro di questa fase,
in ordine di priorità dichiarata:

1. **Un carico distribuito vero sull'as-built** — richiede di passare
   `element_surfaces` anche sul percorso as-built (oggi non lo fa) e una
   decisione di prodotto in più su come dichiarare una pressione su una
   superficie senza nome.
2. **Guardie sul modello mal vincolato** — verifica indipendente dai
   posizionati, che completa il controllo già esistente su quanto
   dell'impronta d'appoggio sia coperta dal vincolo.
3. **Selezione col mouse** — l'interfaccia oggi fa solo orbita sul modello:
   nessun raycast esiste per trasformare un clic in un punto 3D, e il server
   scarta già gli indici che il contorno del volume gli restituirebbe.
4. **Vista deformata** — un endpoint che serva un campo vettoriale (gli
   spostamenti), più il rifiuto delle chiavi assenti che il server già fa
   per i campi scalari.
5. **Round-trip dello YAML che preservi i commenti** — la scrittura oggi
   passa per un dumper che non li conserva, e la libreria che li
   preserverebbe non è fra le dipendenze dichiarate.

A questi cinque si aggiunge, con priorità sopra tutti, il difetto trovato in
questa stessa sessione:

0. **Il `*CLOAD` di un passo statico resta attivo in quello successivo**
   (§ 5.4), e nulla nel programma lo azzera fra un carico basato su `*CLOAD`
   e il successivo. Va corretto — verosimilmente con una card
   `*CLOAD, OP=NEW` scritta prima di ogni passo che introduce un nuovo
   carico posizionato o `carico_sommita`, quando un passo precedente ne ha
   già scritto uno — prima che una configurazione con più di un carico
   `*CLOAD` in sequenza possa dirsi affidabile. La sonda che lo dimostra è
   committata in `docs/fase-6-cantiere/sonda-cload-persiste/`, ed è la prima
   cosa da rileggere per chi riprende questo lavoro.
