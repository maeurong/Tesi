# Fase 6 — carichi posizionati su una mesh senza topologia

Data di chiusura: 22 agosto 2026. Corsa dimostrativa: `runs/lab_telaio_v4_posizionati_top`,
generata in questa sessione sul ramo `feat/impronta-carichi` a partire dagli
stessi artefatti geometrici di `runs/lab_telaio_v2` — stessa nuvola, stesso
ritaglio, stessa superficie riparata, stessa tetraedrizzazione — con in più il
blocco `selettori` e due `carichi.posizionati` che questa fase introduce. Ogni
numero di questo documento porta accanto **il file e il campo da cui viene**.
Lo script che li riproduce tutti è
[`docs/fase-6-cantiere/misura-carichi.py`](fase-6-cantiere/misura-carichi.py):

```
uv run python docs/fase-6-cantiere/misura-carichi.py
```

Ogni valore che quello script stampa porta il proprio `assert` contro il
valore pubblicato qui, sul modello di
[`docs/fase-5-cantiere/misura-deficit.py`](fase-5-cantiere/misura-deficit.py):
se la corsa cambia, lo script cade invece di stampare in silenzio un numero
diverso da quello scritto.

Una seconda cartella, `runs/lab_telaio_v4_posizionati` (senza suffisso), è
tenuta apposta accanto alla prima: è una configurazione quasi identica,
risolta **prima** che il § 5.4 correggesse un difetto trovato durante la
scrittura di questo stesso documento — vi manca solo lo spostamento del
selettore del momento, dal set vincolato alla sommità, che il § 5.4 stesso
racconta. Ogni numero fuori dal § 5.4 viene dalla corsa corretta.

---

## 1. Il problema

Un modello as-built ricostruito da una scansione non ha topologia: non esiste
una faccia nominata «trave superiore», né uno spigolo a cui appoggiarsi per
dire «qui». `runs/lab_telaio_v2/12_wall.json` lo dichiara nel proprio campo
`membrature`, vuoto — otto regioni trovate, zero membrature accettate. Il
programma non ha, e non può avere su questa geometria, un vocabolario di parti
nominate.

Gli unici indirizzi che il deck contiene oggi sono i sei insiemi di nodi che
`build_node_sets` (`core/abaqus.py:1090`) **ricalcola dalle coordinate a ogni
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

La corsa dimostrativa dichiara un selettore per ciascuna delle quattro forme
— più un secondo esempio di `nset`, per la ragione che il § 5 spiega — su
`lab_telaio_v4_posizionati_top.yaml`. I nodi risolti e la bbox reale, dal
campo `11_export.selettori` di `runs/lab_telaio_v4_posizionati_top/metrics.json`:

| selettore | tipo | regola dichiarata | nodi presi | bbox reale dei nodi presi [mm] |
|---|---|---|---:|---|
| `piastra` | box | `min=[300,1200,1650]`, `max=[600,1500,1799.73]` | **365** | x 340,8–529,8 · y 1200,7–1497,5 · z 1650,5–1796,4 |
| `angolo` | sfera | centro `[700,2400,1750]`, raggio 250 mm | **158** | x 459,6–521,5 · y 2225,3–2456,0 · z 1583,3–1797,6 |
| `punta` | nodo | punto `[418,46; 1956,82; 1798,73]` | **1** | il nodo a 1,73 mm dal punto dichiarato |
| `appoggio` | nset | `nome: BASE` | **3719** | x 0,0–875,2 · y 15,3–2698,2 · z 0,0–132,0 |
| `sommita` | nset | `nome: TOP` | **3036** | x 336,2–529,8 · y 2,4–2456,0 · z 1664,9–1799,7 |

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
già costruito per il vincolo — nessun ricalcolo, nessuna duplicazione. Non è
citato da alcun carico in questa corsa: è il caso «selettore dichiarato e mai
citato», legittimo per contratto (§ 3), non un residuo dimenticato. Il
selettore `sommita` cita `TOP` allo stesso modo, ed è quello che il § 5
sceglie per il momento — la ragione per cui il momento non poteva stare su
`appoggio` è la stessa ragione per cui `appoggio` resta senza carico.

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
(`aree_tributarie`, `core/abaqus.py:581`) ripartisce l'area di ogni triangolo,
un terzo a ciascuno dei suoi tre nodi, in un array indicizzato per nodo.
`surface_area` (`core/abaqus.py:559`, già esistente dalla Fase 4) non ha più
un ciclo proprio: dopo la fusione dei due, è la somma di quell'array
(`aree_tributarie(...).sum()`), non più una funzione gemella che ripete lo
stesso ciclo a mano. Le facce su cui si somma sono quelle di bordo
**interamente contenute** nell'insieme del selettore (`element_surface`, già
esistente): una faccia con tre nodi su quattro nell'insieme non entra, perché
non è quella faccia. `ripartisci` (`core/abaqus.py:617`) normalizza le quote
sul totale, così la somma delle forze scritte nel deck è sempre esattamente
la risultante dichiarata — verificato con un `assert` sul deck scritto, non
per fede.

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
«I cinque controlli, e i loro esiti»). `GRAVITA`, `SPINTA_ORIZZONTALE` e `MODALE` non usano
questa ripartizione e non cambiano.

> **Nota successiva.** Il valore «dopo» qui sopra (0,9809 MPa) descriveva un
> caso di carico diverso da quello che `CARICO_TOP` promette: `runs/lab_telaio_v3_pesata`
> dichiara `spinta` insieme a `carico_sommita`, e un secondo difetto — il
> `*DLOAD` che non azzerava mai la spinta fra un passo statico e il
> successivo, § 5.4 qui sotto tratta il difetto gemello sul `*CLOAD` — la
> lasciava attiva anche in `CARICO_TOP`. Corretto: il picco vero, senza la
> spinta ereditata, è **0,8101 MPa** (`runs/lab_telaio_v3_pesata_dload_fix`).
> Le righe `*CLOAD` e la tabella qui sopra non cambiano: la correzione tocca
> il `*DLOAD`, non il `*CLOAD`. Dettagli in `docs/fase-5-analisi.md`, § «I
> risultati, per caso di carico», e in
> `docs/fase-6-cantiere/sonda-cload-persiste/README.md`.

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
(`coppia_equivalente`, `core/abaqus.py:658`), non come un momento vero e
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

**Condizione d'uso: la direzione scelta dalla SVD è instabile su un selettore
quasi isotropo.** `separazione` è il primo vettore singolare di `piano`
(`coppia_equivalente`, `core/abaqus.py`): ben definito quando il primo valore
singolare domina il secondo, ma quando i due sono vicini — un selettore la
cui estensione nel piano perpendicolare all'asse non ha una direzione
prevalente, per esempio quasi circolare o quadrata — la SVD non ha più un
vettore dominante da scegliere: un rumore numerico minimo (un nodo in più o
in meno, un arrotondamento di coordinate) può far scambiare quale dei due
vettori vince, e la direzione di separazione — quindi i due gruppi di nodi,
la forza per nodo, il deck scritto — cambia con esso. Non è un'ipotesi:
misurato sul selettore `TOP` reale usato in questo documento (§ 6.2), il
rapporto fra i due valori singolari vale **0,096** — un ordine di grandezza
di margine, il caso studio è al sicuro. Su un selettore vicino alla simmetria
(rapporto vicino a 1) lo stesso file, alla stessa versione, può scrivere deck
diversi da una corsa all'altra senza che nulla lo segnali: nessun avviso,
nessun errore, un `braccio_effettivo` e un `momento_effettivo` diversi nel
resoconto. Chi dichiara un momento su un selettore quasi simmetrico deve
verificare il rapporto fra i due valori singolari, non solo il rapporto fuori
asse del § 6.

Quel rapporto non è più un numero da rimisurare a mano: `coppia_equivalente`
lo scrive nel resoconto di ogni momento, come `rapporto_valori_singolari`
(§ 7), così si vede anche quando passa — e sopra
`SOGLIA_PAREGGIO_VALORI_SINGOLARI` **avvisa**, nominando il rapporto che ha
misurato. Avviso e non rifiuto: il deck che esce è valido, il momento attorno
all'asse è quello dichiarato, e applicare un momento a una piastra quadrata
resta legittimo — è la *direzione* a non essere più un dato della geometria.
Come la soglia è stata scelta, e perché non si lascia derivare con la ricetta
del § 6.3, sta nel § 9.1.

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

Il selettore giusto per un momento deve estendersi abbastanza, nella direzione
della coppia, da sostenere il braccio voluto: una box di 300×300 mm o una
sfera di raggio 250 mm — `piastra` e `angolo` di questa stessa corsa, § 2 —
non arrivano a qualche centinaio di millimetri di estensione, e un braccio
importante su uno dei due sarebbe stato rifiutato, giustamente. `TOP`, il set
di faccia, si estende invece per oltre due metri.

Sulla corsa dimostrativa, il carico `TORSIONE` agisce sul selettore `sommita`
— `{tipo: nset, nome: TOP}`, gli stessi 3.036 nodi del set di faccia — con
asse z, modulo 500.000 N·mm e braccio dichiarato **490,7 mm**: lo stesso
braccio della riga «`TOP` as-built, braccio 490,7» che il § 6.2 misura per
tarare la soglia del momento fuori asse — si veda lì per la derivazione —
scritto qui per la prima volta in un deck vero invece che in una sonda.
L'estensione disponibile è **2.453,27 mm** (§ 6.2), ampiamente sopra il
braccio dichiarato:
la funzione non solleva, e divide i 3.036 nodi in **1.197** nel gruppo
positivo e **1.285** nel negativo, con braccio effettivo **1.491,16 mm**
(`runs/lab_telaio_v4_posizionati_top/metrics.json`,
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

### 5.4 Un difetto trovato e corretto: il `*CLOAD` di un passo restava attivo nel successivo

La corsa dimostrativa di questo documento è la prima, in tutto il progetto, a
scrivere **due passi statici consecutivi che portano entrambi un `*CLOAD`**:
`PRESSA` (la forza posizionata) seguito da `TORSIONE` (il momento come
coppia). Fino a questa fase non era mai successo: `SPINTA_ORIZZONTALE` usa
`*DLOAD`, non `*CLOAD`, e `CARICO_TOP` è sempre stato l'ultimo passo statico
del deck, senza nulla dopo di sé che potesse risentirne.

**Prima della correzione**, le reazioni misurate sul deck della prima corsa
(`runs/lab_telaio_v4_posizionati/13_solution.dat`, tenuta apposta come prova)
mostravano una cosa che il progetto non si aspettava:

| passo | Σfz misurata (prima) |
|---|---:|
| `GRAVITA` | 4.162,39 N |
| `PRESSA` (peso + forza da −1.000 N) | **5.162,39 N** |
| `TORSIONE` (peso + coppia, risultante netta nulla) | **5.162,39 N** |

Una coppia ha risultante netta nulla per costruzione: se il passo `TORSIONE`
portasse solo il proprio carico più il peso proprio, la sua reazione doveva
tornare a **4.162,39 N**, uguale a `GRAVITA`. Invece coincideva, a sette
cifre, con quella del passo `PRESSA` precedente: il `*CLOAD` da −1.000 N
scritto per `PRESSA` **restava attivo** durante la soluzione di `TORSIONE`,
sommato al carico che quel passo dichiarava davvero.

Una sonda minima, isolata e committata
(`docs/fase-6-cantiere/sonda-cload-persiste/`), ha isolato la causa: un
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
`*CLOAD, OP=NEW`. `write_inp` non scriveva mai quella card fra un passo e il
successivo.

**Era un difetto del programma, non un limite dichiarato.** Il § 8 di questo
documento riporta, come la riportava la configurazione approvata di questa
fase, che «ogni carico dichiarato è un passo statico a sé, col solo peso
proprio accanto» — vero per come lo **schema** della configurazione è fatto
(non esiste un modo di chiedere che due carichi si sommino in un passo solo),
ma il deck che `write_inp` scriveva **non realizzava** quella promessa quando
più di un carico basato su `*CLOAD` compariva in sequenza — due
`carichi.posizionati`, oppure un `carico_sommita` seguito da un posizionato.
Ogni passo dopo il primo che portava un `*CLOAD` includeva, senza che nulla
lo segnalasse, anche il carico di ogni passo precedente che ne aveva scritto
uno. Zero avvisi, zero errori, spostamenti e reazioni tutti finiti e
plausibili — esattamente la forma di errore silenzioso che questa fase esiste
per stanare, questa volta prodotta dal programma stesso invece che da `ccx`.

**La correzione**, commit `2fc0ae5`: ogni `*CLOAD` che `write_inp` scrive per
`carico_sommita`, per un posizionato a forza, o per la coppia di un momento
(`coppia_equivalente`) diventa `*CLOAD, OP=NEW` — la card che dichiara
esplicitamente «questi sono gli **unici** carichi concentrati attivi da qui in
poi», azzerando quelli dei passi precedenti invece di lasciarli attivi per
omissione. Il `*DLOAD` del peso proprio non tocca questa correzione: si
ridichiara identico a ogni passo e **sostituisce**, non somma — non ha mai
sofferto del difetto, ed è per questo che `GRAVITA` è sempre stato corretto.

Rigenerata la corsa dimostrativa con il codice corretto
(`runs/lab_telaio_v4_posizionati_top/`, stessi due carichi posizionati), le
reazioni tornano quelle attese:

| passo | Σfz misurata (dopo) |
|---|---:|
| `GRAVITA` | 4.162,39 N |
| `PRESSA` (peso + forza da −1.000 N) | **5.162,39 N** |
| `TORSIONE` (peso + coppia, risultante netta nulla) | **4.162,39 N** |

`TORSIONE` torna **esattamente** alla reazione di `GRAVITA` (a meno del
residuo numerico del solutore, sotto 4e-4 N su un carico di migliaia di
newton), com'è fisicamente dovuto per una coppia a risultante nulla;
`PRESSA`, il primo passo a dichiarare un `*CLOAD`, non cambia di una cifra
rispetto a prima — non aveva nulla da ereditare. Lo stesso vale per ogni
numero del § 2 e del § 7 che descrive *come il deck viene scritto* (nodi dei
selettori, area tributaria, braccio effettivo, momento effettivo): sono
fatti decisi in fase di scrittura del deck, prima che `ccx` lo risolva, e la
card `OP=NEW` non li tocca — solo la **soluzione** del passo `TORSIONE`
cambia, perché prima portava anche il carico di `PRESSA` e ora porta solo il
proprio. Sotto il codice corretto, `TORSIONE` sposta davvero qualcosa di
proprio: `u_max` **0,057308 mm** e `vm_max` **0,5695 MPa**
(`13_solve.casi.TORSIONE`), diversi sia da `GRAVITA` (0,036730 mm, 0,5056
MPa) sia da `PRESSA` (0,070417 mm, 0,9332 MPa) — una risposta strutturale
distinguibile, non un residuo del peso proprio.

**Un'osservazione da tenere, non solo un difetto da correggere**: un carico
applicato su un insieme di nodi **interamente vincolato** non sposta nulla,
in nessun punto del modello — l'intero suo effetto finisce nella reazione di
quei nodi, per costruzione dell'eliminazione dei gradi di libertà fissati.
Il selettore `appoggio` (l'insieme `BASE`, vincolato da `*BOUNDARY, BASE, 1,
3`) è esattamente un caso così, ed è per questo che il momento di questa
dimostrazione **non** agisce su di lui: agisce su `sommita` (`TOP`), che non
è vincolato. È un'informazione che vale per chiunque dichiari un momento, non
solo per questa corsa — un selettore coincidente, anche solo in parte, con
`fixed_nset` realizza sulla carta lo stesso braccio e lo stesso momento
effettivo (§ 5.2, § 7 li leggono dal deck scritto, prima che `ccx` risolva
nulla), ma non sposta la struttura di un millimetro.

Verificato che questa correzione (il `*CLOAD`, commit `2fc0ae5`) non tocchi
nulla di già pubblicato: allo stato di questa sezione lo script della Fase 5
(`docs/fase-5-cantiere/misura-deficit.py`) usciva a 0 sui numeri di
`runs/lab_telaio_v3_pesata`, che dichiara un solo carico basato su `*CLOAD`
(`CARICO_TOP`) e non aveva nulla da cui ereditare **per il `*CLOAD`** — il
`*DLOAD` di quella stessa corsa aveva invece un difetto gemello, corretto
dopo (vedi la nota al § 4 sopra): lo script punta oggi a
`runs/lab_telaio_v3_pesata_dload_fix`, non più a `runs/lab_telaio_v3_pesata`.
La sonda del difetto è committata anche come test di regressione (`tests/test_abaqus.py`,
`tests/feasibility/test_calculix.py`); il conteggio delle due suite alla
chiusura di questa fase — misurato in questa sessione, una fotografia e non
un invariante, perché cresce a ogni test che il progetto aggiunge altrove —
è **816 passed** sulla suite ordinaria e **14 passed, 1 skipped** sulla
fattibilità.

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

Questa non è rimasta una sonda a parte: è la stessa combinazione — selettore
`TOP`, braccio 490,7 mm — che il carico `TORSIONE` della corsa dimostrativa
scrive in un deck vero (§ 5.2). Il controllo del momento fuori asse vi passa
in silenzio (nessun `ValueError`, il deck si scrive), e il rapporto letto dal
resoconto reale coincide con la riga qui sopra: **0,003552**. La soglia non è
tarata solo su un caso costruito per la misura, è verificata sul caso reale
che la userà.

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

La soglia in codice — `TOLLERANZA_MOMENTO_FUORI_ASSE`, `core/abaqus.py:45` —
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

Il nome `carichi_posizionati` non è più preciso alla lettera: la chiave porta
anche la voce `CARICO_TOP`, quando `carico_sommita` è dichiarato, benché
`CARICO_TOP` non sia un elemento di `carichi.posizionati` (§ 4). È lo stesso
resoconto — nodi, area tributaria, forza dichiarata ed effettiva — e prima
della Fase 6 andava perso: farlo confluire qui, invece di in una chiave a
parte, ha tenuto il contratto a una sola voce di ritorno invece di due.

Un estratto reale, da `runs/lab_telaio_v4_posizionati_top/metrics.json`:

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
  },
  "sommita": {
    "tipo": "nset",
    "nodi": 3036,
    "bbox": [[336.19, 2.40, 1664.91], [529.77, 2455.95, 1799.73]]
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
    "nodi": 3036,
    "braccio_dichiarato": 490.7,
    "braccio_effettivo": 1491.1611523542952,
    "momento_dichiarato": [0.0, 0.0, 500000.0],
    "momento_effettivo": [8.51, -1776.06, 500000.00000000023],
    "forza_di_ciascun_lato": 335.30916441229925,
    "nodi_positivi": 1197,
    "nodi_negativi": 1285,
    "estensione_disponibile": 2453.2664114565505
  }
}
```

L'estratto è la corsa congelata e **precede tre chiavi** aggiunte dopo:
`rapporto_valori_singolari` e `nodi_ad_area_nulla` su ogni momento (il
secondo esisteva già per le forze e per `CARICO_TOP`, e sul momento veniva
buttato), e `nodi_sul_vincolo` su ogni carico, forze e momenti insieme.
Rilette sulla stessa mesh, `TORSIONE` porta un rapporto di **0,0961010** e
**703** nodi ad area nulla sui 3.036 presi: quasi un quarto del selettore non
tocca alcuna faccia di bordo e non riceve quota, un numero che il resoconto
del momento fino a ieri non mostrava affatto.

`appoggio` compare nel resoconto con i suoi 3.719 nodi anche se **nessun
carico lo cita**: è il caso «selettore dichiarato e mai citato», legittimo
per contratto (§ 3), e questa stessa corsa lo esercita davvero invece di
lasciarlo solo a un test.

Ogni selettore riporta il proprio tipo, quanti nodi ha preso e la bbox reale
di quei nodi — non la regola dichiarata, ma dove i nodi presi *stanno
davvero*, perché l'operatore possa collocare un selettore senza indovinare
alla cieca. Ogni carico posizionato riporta, per una forza, i nodi coinvolti,
l'area tributaria totale, quanti nodi non hanno toccato alcuna faccia di
bordo, e la forza effettivamente scritta contro quella dichiarata (§ 4); per
un momento, entrambi i bracci, entrambi i momenti (dichiarato ed effettivo),
i due gruppi della coppia (§ 5-6) e il rapporto fra i due valori singolari che
dice quanto la direzione della coppia sia determinata (§ 5.2). Per ogni
carico, forza o momento, anche `nodi_sul_vincolo`: quanti dei nodi presi
cadono pure nell'insieme vincolato, cioè quale frazione della risultante
finisce in reazione invece che in spostamento. Era già calcolato, ma viveva
solo nella stringa di un avviso su stderr — e un avviso si perde con la
finestra del terminale, mentre `forza_effettiva` resta nel file a dichiarare
la risultante intera. Il precedente comportamentale, già nel
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
  già dichiara (`core/abaqus.py:1090`): la coppia di facce opposte è
  affidabile come coppia, l'attribuzione del singolo nome no.
- **non scrive momenti concentrati.** Un `*CLOAD` sui gradi 4-6 su un
  elemento solido è scartato in silenzio: si veda il § 5.
- **non combina due posizionati in un passo solo.** Ogni carico dichiarato è
  un passo statico a sé, col solo peso proprio accanto. Lo schema della
  configurazione non ha modo di chiedere una combinazione, e questa fase non
  gliene aggiunge uno. Questa promessa non era mantenuta dal deck fino a
  questa stessa sessione — il § 5.4 racconta il difetto trovato scrivendo
  questo documento e la correzione (`2fc0ae5`) che lo ha chiuso: oggi l'isolamento fra passi è
  garantito sia dallo schema sia dal deck che `write_inp` scrive.

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

Nessuno di questi cinque è più urgente di prima. Il sesto elemento che questa
sessione avrebbe potuto lasciare in coda — il `*CLOAD` che restava attivo da
un passo al successivo (§ 5.4) — non ci sta: è stato trovato e **corretto**
mentre questo stesso documento veniva scritto, con la sonda che lo dimostra
committata (`docs/fase-6-cantiere/sonda-cload-persiste/`) e la corsa
dimostrativa rigenerata col codice giusto. È il risultato più concreto che
questa fase lascia, oltre ai quattro selettori e alla coppia di forze: uno
strumento pensato per dare a un operatore un indirizzo durevole su una mesh
senza topologia ha trovato, nel produrre il proprio esempio, un modo in cui
tradiva silenziosamente quello stesso indirizzo — e la correzione è stata
misurata, non presunta, prima di essere dichiarata chiusa.

### 9.1 La guardia sul pareggio dei valori singolari, e la soglia scelta

Come il `*CLOAD` persistente del § 5.4, anche questo è un elemento che la coda
non si tiene. Il § 5.2 dice che su un selettore isotropo la direzione della
coppia la sceglie il rumore numerico. Il rimedio ovvio è una guardia come
quella del § 6.3: segnalare quando `rapporto_valori_singolari` supera una
soglia. La soglia però, con la ricetta del § 6.3 — media geometrica dei due
estremi misurati — **non si lascia derivare**, e la ragione è misurata.

Su una piastra sintetica di 12 × 12 nodi lunga 100 mm, larga quanto serve a
fissare il rapporto, si toglie **un solo nodo** — la perturbazione che un
rimaglio produce davvero — e si guarda di quanto ruota la direzione di
separazione:

| piastra | rapporto | rotazione della direzione |
| --- | --- | --- |
| 100 × 100 | 1,0000 | oltre 45° (misurato 83,3°, ma su un pareggio il valore esatto non è riproducibile: non c'è un vettore da scegliere) |
| 100 × 99 | 0,9900 | 35,12° |
| 100 × 90 | 0,9000 | 1,44° |
| **100 × 80** | **0,8000** | **0,65°** |
| 100 × 40 | 0,4000 | 0,13° |
| 100 × 9,61 | 0,0961 | 0,027° |

Le due geometrie che contano cadono nelle ultime due righe: il banco sintetico
su cui girano i test di questa fase ha `TOP` di 100 × 40 mm, rapporto **0,400**,
e il `TOP` as-built del caso studio sta a **0,0961**.

**Perché la ricetta del § 6.3 non si trasferisce.** La media geometrica dei due
estremi che quel paragrafo userebbe — 0,0961 del caso studio e 1,0
dell'isotropo — vale `sqrt(0,0961010 · 1,0) ≈ 0,3100`: **sotto** lo 0,400 del
banco dei test, che la tabella misura stabile entro 0,13°. Una soglia lì
segnalerebbe una piastra 2,5 : 1, cioè una geometria con un asse maggiore
perfettamente determinato — e un avviso che parte anche sulle geometrie sane
non lo legge più nessuno. Là gli estremi erano due misure (0,003552 e 0,818) su
una scala aperta; qui l'estremo cattivo **non è una misura**: è il massimo che
il rapporto può assumere per definizione, e una media geometrica con un estremo
di frontiera cade dove capita. Né la colonna di destra offre un ginocchio da
leggere come soglia: la sensibilità cresce come `1/(1 − r²)`, liscia, fino al
salto dell'ultima riga.

**La soglia è quindi una scelta dichiarata, non una misura.** Il numero che
nasconde è *quanta rotazione della direzione si accetta*, e la scelta è
**0,65°**, cioè `SOGLIA_PAREGGIO_VALORI_SINGOLARI = 0,80`. Sopra quel rapporto
`coppia_equivalente` avvisa (`SelettoreIsotropoWarning`) nominando il rapporto
misurato; il deck si scrive lo stesso. I margini che ne restano: il banco dei
test passa con un fattore 2 (0,400 contro 0,800), il caso studio con un
fattore 8 (0,0961). La tabella è riprodotta a ogni corsa da
`docs/fase-6-cantiere/misura-carichi.py`, soglia compresa: se qualcuno la
sposta senza rimisurare, lo script cade.
