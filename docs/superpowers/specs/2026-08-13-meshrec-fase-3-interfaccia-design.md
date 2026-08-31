# MeshRec Fase 3 — Interfaccia web completa

- **Data:** 13 agosto 2026
- **Stato:** design approvato in sessione di brainstorming
- **Dipende da:** Fase 2 completa e su `main` (`62889cf`)
- **Spec di riferimento:** [`2026-08-12-meshreconstructor-architettura-design.md`](2026-08-12-meshreconstructor-architettura-design.md) § 7, «Interfaccia (Fase 3)»

---

## 1. Perché questa fase esiste, e che cosa consegna

Dopo la Fase 1 esiste la pipeline, dopo la Fase 2 esiste il metodo. La Fase 3
consegna **l'applicazione**: il programma che sostituisce `MeshReconstructorPro`
e che si presenta in discussione. È anche la fase che chiude il primo requisito
elencato nella spec di architettura — esecuzione batch e parametri salvati con la
corsa — dal lato opposto: qui l'interfaccia
c'è, ma il batch resta e i parametri sono già tracciati, perché l'interfaccia
pilota il core esistente invece di sostituirlo.

**L'interfaccia non reimplementa nulla di ciò che sta in `core/`.** Ogni numero
che mostra viene da `metrics.json`, ogni parametro che scrive passa dai modelli
di `config.py`, ogni elaborazione che avvia è la stessa `pipeline` con cui sono
stati prodotti tutti i numeri delle Fasi 1 e 2. Dove il core non sa fare una
cosa, la cosa si aggiunge al core e non all'interfaccia: la § 4 elenca i cinque
punti in cui questo accade, misurati prima di essere scritti.

### 1.1 I cinque principi che questa fase applica

Vengono dalla § 4 di [`fase-1-debito.md`](../../../meshrec/docs/fase-1-debito.md)
e dagli esiti della Fase 2. Sono requisiti di progetto, non citazioni: ognuno ha
una sezione che lo attua.

1. **Ogni metrica riportata ha un controllo che la smentisce.** La § 9 elenca
   ogni grandezza nuova accanto a ciò che la contraddice. Nessuna grandezza entra
   nella fase senza il proprio controllo. Un'interfaccia è il luogo dove questo
   principio è più facile da violare, perché mostrare un numero è già sembrare di
   averlo verificato.
2. **La grandezza sorvegliata si sceglie prima della soglia.** La § 10 sceglie
   tre sorveglianze, tutte qualitative, nessuna tarata.
3. **Le geometrie sintetiche verificano che la catena non si spezzi.** La § 11
   dice che cosa solo `lab_crop` può stabilire: 6.329.096 punti letti, 4.229.538
   dopo la segmentazione, non il cubo.
4. **Un contratto vale sul percorso, non sulla funzione.** La § 8.4 lo attua: il
   contratto «nessun endpoint solleva» vale su tutti gli endpoint della tratta,
   verificato su tutti e non su uno.
5. **Ogni numero di questo documento è ricavato da una lettura.** Le letture sono
   citate riga per riga. Le due misure nuove fatte durante il brainstorming — il
   renderer di Open3D e la traccia della decimazione — sono nella § 4.

---

## 2. Decisioni prese in brainstorming

| Domanda | Decisione | Motivo |
|---|---|---|
| Ampiezza | Non è lavoro di sola interfaccia: tre capacità nuove nel core, una correzione di un difetto, uno strato `app/` che non esiste | § 4 |
| Motore per step | Cache per impronta completa, con invalidazione a valle | § 6 |
| Backend | FastAPI più uvicorn | § 3.1 |
| Progresso e log | SSE, non WebSocket | § 3.2 |
| Trasporto dei punti | Binario Float32, non JSON | § 3.3 |
| Frontend | ES module senza build, three.js vendorizzato in repo | § 3.4 |
| Cattura delle viste | Canvas three.js, non renderer lato Python | § 3.5 |
| Decimazione | `voxel_down_sample_and_trace` di Open3D, che restituisce già la mappa | § 8.1 |
| Ordine di priorità | Dodici punti, si taglia dal fondo | § 12 |
| Criterio di chiusura del design | `impeccable audit` e `impeccable critique` al punteggio massimo | § 13 |

---

## 3. Lo stack, con le alternative scartate e il numero che le scarta

Lo stack è fissato. Non è rivedibile in corso d'opera.

### 3.1 Backend: FastAPI più uvicorn

Entrambi sono già dichiarati nella § 10 della spec di architettura come
dipendenze in ingresso, e **nessuno dei due è in `pyproject.toml`** oggi: questa
fase li aggiunge. Sono le uniche due dipendenze Python nuove.

Il numero che decide: `config.py` ha **316 righe** di modelli pydantic già
scritti, validati e coperti da test. FastAPI li accetta come schema di richiesta
e di risposta senza una riga di codice nuova. Qualunque alternativa richiede di
riscrivere a mano la validazione di quei modelli, o di rinunciarvi.

Scartate:

- **Flask.** È nella lista delle dipendenze escluse dal bundle attuale (§ 10
  della spec di architettura), non ha validazione da modelli e non ha un supporto
  nativo per gli eventi in streaming. Riporterebbe dentro una libreria che il
  progetto ha già deciso di lasciare fuori.
- **`http.server` della libreria standard.** È la scelta più povera, e sarebbe la
  preferibile se il conto tornasse. Non torna: servono instradamento a mano per
  circa dodici endpoint, gestione del corpo binario, gestione dello streaming e
  la riscrittura della validazione dei 316 righe di modelli. Due dipendenze
  contro tutto questo.
- **Django.** Fuori scala di due ordini per un'applicazione a utente singolo
  senza database e senza autenticazione.

### 3.2 Progresso e log: SSE

Il traffico è a senso unico, dal server al browser: avanzamento, righe di log,
cambio di stato di uno step. L'annullamento viaggia su una `POST` ordinaria,
perché è un comando singolo e raro.

Il numero che decide: **una direzione su due**. WebSocket aggiungerebbe un
secondo protocollo, la sua libreria e la sua gestione della riconnessione per
trasportare traffico in una sola direzione. SSE è HTTP semplice e riconnette da
solo con `EventSource`, che è nel browser e non si installa.

### 3.3 Trasporto dei punti: binario Float32

I punti viaggiano come corpo binario grezzo, letti nel browser come
`Float32Array`, non come JSON.

Il numero che decide: 300.000 punti sono **3,6 MB** in Float32 (300.000 × 3 × 4
byte) contro circa **18 MB** in JSON, ipotizzando venti caratteri per coordinata
fra cifre, punto decimale, virgola e segno. Fattore cinque sul trasporto, più il
costo di analisi sintattica che sparisce del tutto.

### 3.4 Frontend: nessun build, three.js vendorizzato

ES module serviti direttamente, nessun `package.json`, nessun bundle. Il build
ESM di three.js — un file, circa 1,2 MB — è committato in
`src/meshrec/ui/vendor/` e servito dal server locale.

Il numero che decide: la distribuzione dichiarata nella § 3 della spec di
architettura è **«repository più `uv sync`»**. Una toolchain node introduce un
secondo gestore di pacchetti e un artefatto di build in un repository Python, e
rompe quella riga.

Scartate:

- **Import map verso CDN.** Il server è locale e l'applicazione deve funzionare
  senza rete: senza CDN raggiungibile l'interfaccia non parte affatto. In sede di
  discussione della tesi è un rischio che non si controlla.
- **Vite più React o Svelte.** Danno ricarica a caldo e tree shaking, che per un
  viewport e tre pannelli non pagano il prezzo detto sopra.

`node` resta usato in questa fase per un solo scopo, il rilevatore di
`impeccable` (`node --version` dà **v24.19.0** su questa macchina): è uno
strumento di verifica del design, non una dipendenza dell'applicazione, e non
entra nella distribuzione.

### 3.5 Cattura delle viste: il canvas, non un renderer lato Python

Il browser esporta il canvas WebGL in PNG e lo invia al server, che lo salva
nella cartella della corsa e lo incorpora nel report.

La misura che sostiene la scelta è nella § 4.5, e ha due metà. Il renderer nuovo
di Open3D non parte su questa macchina; quello legacy funziona. Quindi la scelta
**non** è fra «si può» e «non si può», ed è per questo che va scritto il motivo
vero: due motori di disegno significano due estetiche nello stesso report e due
percorsi di codice da mantenere, e le viste prodotte da Open3D non sono quelle
che l'operatore ha inquadrato né portano il sistema di design della fase.

Costo dichiarato: `meshrec report` da riga di comando produce il report **senza
viste**, e lo dichiara nel documento invece di lasciare riquadri muti. Si riapre
se e quando servirà un report generato in automatico senza browser, per esempio
in un batch di Fase 5.

---

## 4. Che cosa manca al core oggi

Cinque punti, ognuno verificato prima di essere scritto. È il rilievo che
stabilisce che questa fase non è lavoro di sola interfaccia.

### 4.1 Esecuzione per singolo step: parziale, e manca il pezzo che conta

`pipeline.run` (`core/pipeline.py:68`) è una funzione sola. `cfg.run.from_step`
salta gli step precedenti secondo due tabelle di ripresa esplicite
(`_RESUME_POINTS` e `_RESUME_MESH`, righe 38 e 45). Mancano tre cose:

1. **Nessuna API per eseguire un solo step.** Il ciclo vive dentro `run()` e non
   ha appigli intermedi: il server non può chiedere «esegui lo step 5 e fermati».
2. **Nessuna impronta per step, quindi nessuna invalidazione a valle.** La § 4
   della spec di architettura promette che «gli step a valle di una modifica sono
   marcati non validi ed evidenziati; un risultato ottenuto con parametri diversi
   non viene mai riutilizzato in silenzio». Il codice non lo fa: la docstring di
   `run` dice che la ripresa «si fida dell'operatore» e non verifica nemmeno che
   gli artefatti esistano.
3. Gli step 10 e 11 si rieseguono sempre, per scelta dichiarata e senza costo.

### 4.2 Annullamento: difetto confermato, già aggirato una volta

`core/pipeline.py:180-183`: il blocco `finally` scrive `metrics.json` con il
dizionario così com'è. Una corsa interrotta allo step 5 **sostituisce** il
`metrics.json` completo della corsa precedente con uno parziale, e i due file
sono indistinguibili all'occhio.

Non è un rischio teorico: la Fase 2 ha dovuto costruire `is_complete`
(`core/sweep.py:122`) esattamente per distinguerli, e la § 6.1 della sua spec lo
elenca fra i controlli che smentiscono. La Fase 3 lo corregge alla radice invece
di aggiungere il secondo aggiramento.

Non esiste inoltre alcun meccanismo di annullamento: `app/worker.py`, elencato
nella § 4 della spec di architettura, non è mai stato scritto. La cartella
`src/meshrec/app/` non esiste.

### 4.3 Decimazione con mappa verso l'indice pieno: assente, ma Open3D la offre

`surface.downsample` (`core/surface.py:32`) usa `voxel_down_sample`, che
restituisce i punti e **non** gli indici: la corrispondenza con la nuvola piena è
persa.

Le dimensioni in gioco, lette da `runs/lab_crop/`: `01_cloud.ply` pesa
**151.898.454 byte**, `02_segmented.ply` **101.509.062 byte**. Da
`runs/lab_crop/metrics.json`: 6.329.096 punti letti, **4.229.538** dopo la
segmentazione, 116.059 dopo la riduzione a voxel da 10 mm. Al browser la nuvola
piena non arriva, e senza mappa degli indici il clic sul cluster e il box di
ritaglio agirebbero su una nuvola scollegata dal dato.

La misura che risolve il punto, fatta durante il brainstorming:
`voxel_down_sample_and_trace` **esiste già** in Open3D 0.19.0 e restituisce la
mappa. Provato su 100.000 punti casuali con voxel da 40: 15.595 punti ridotti e
15.595 gruppi di traccia, ognuno con gli indici originali che vi ricadono. Il
lavoro nel core è una funzione sottile sopra una capacità che la libreria ha già,
non un algoritmo nuovo.

### 4.4 Campo di deviazione per vertice: assente

`quality.geometric_error` (`core/quality.py:248`) delega a PyMeshLab
`get_hausdorff_distance` e restituisce **soltanto aggregati**: `max` e `RMS` nelle
due direzioni. Una mappa di colore richiede uno scalare per vertice.

`scipy.spatial.cKDTree` è già dipendenza e già in uso (`core/io.py:13`, per la
spaziatura media): la funzione nuova è la distanza da ogni vertice della
superficie al punto più vicino della nuvola sorgente, poche righe, nessuna
dipendenza aggiunta.

### 4.5 Cattura offscreen: la misura ha due metà

Il renderer nuovo di Open3D non parte su questa macchina:

```
open3d 0.19.0
OFFSCREEN FAIL RuntimeError [Open3D Error]
  ...FilamentEngine.cpp:104: EGL Headless is not supported on this platform.
```

Il visualizzatore legacy con finestra nascosta, invece, cattura:

```
create_window visible=False -> True
LEGACY OK (480, 640, 3) media 0.9092 non-sfondo 269360
```

269.360 pixel su 307.200 non sono sfondo: la geometria è stata disegnata davvero,
e il controllo non è «il file esiste» ma «l'immagine contiene qualcosa». Il
sospetto della § 9 della spec di Fase 2 — «richiedono il rendering offscreen di
Open3D su Windows, che in questo progetto non è mai stato provato» — è quindi
sciolto in entrambe le direzioni, ed è scritto qui perché nessuno rifaccia la
prova.

Due postille dichiarate e **non** verificate: `visible=False` apre comunque una
finestra vera nella sessione desktop, quindi su una macchina senza desktop
fallisce e in un test può rubare il fuoco.

L'applicazione Open3D installata a
`C:\Users\mario\Downloads\open3d-app-windows-amd64-0.19.0\Open3D.exe` non entra:
è il visualizzatore grafico, non ha modo di essere pilotato per produrre
un'immagine.

---

## 5. Architettura: che cosa si aggiunge

```
src/meshrec/core/pipeline.py     # spezzato in registro di step; run() resta e li chiama
src/meshrec/core/steps.py        # + catena di impronte, stato degli step, invalidazione
src/meshrec/core/viewport.py     # + decimazione con mappa, serializzazione binaria
src/meshrec/core/quality.py      # + deviazione per vertice
src/meshrec/core/config.py       # + ViewportConfig, ServerConfig
src/meshrec/core/report.py       # + viste catturate, rivestito dal sistema di design
src/meshrec/app/__init__.py      # nuovo strato
src/meshrec/app/server.py        # FastAPI: endpoint, SSE, servizio dell'interfaccia
src/meshrec/app/worker.py        # esecuzione di uno step come processo separato
src/meshrec/ui/                  # HTML, CSS, ES module, viewport three.js
src/meshrec/ui/vendor/three.module.js
src/meshrec/cli.py               # + comando `serve`
```

Dipendenze in una sola direzione, `ui → app → core`, invariata rispetto alla § 4
della spec di architettura. Il core resta utilizzabile da script e da riga di
comando senza che il server esista.

**`config.py` resta l'unico luogo dove un parametro di elaborazione ha un valore
predefinito.** `ViewportConfig` e `ServerConfig` vivono lì come ogni altro
blocco, e le firme del core continuano a non portare predefiniti: il test che lo
verifica resta valido senza modifiche.

### 5.1 Gli endpoint

| Metodo e percorso | Che cosa fa |
|---|---|
| `GET /` | serve l'interfaccia |
| `GET /api/run` | stato della corsa: i dodici step, il loro stato, le loro impronte |
| `GET /api/config` | il `PipelineConfig` corrente |
| `PUT /api/config` | scrive il config e ricalcola quali step diventano non validi |
| `POST /api/step/{n}` | esegue lo step `n` nel worker |
| `POST /api/step/{n}/from` | esegue dallo step `n` in giù |
| `POST /api/cancel` | annulla lo step in corso |
| `GET /api/events` | SSE: avanzamento, righe di log, cambi di stato |
| `GET /api/cloud/{step}` | punti decimati, binario Float32, più la mappa |
| `GET /api/mesh/{step}` | vertici e facce, binario |
| `GET /api/deviation` | campo di deviazione per vertice, binario Float32 |
| `POST /api/crop` | applica un box alla nuvola piena tramite la mappa |
| `POST /api/cluster` | seleziona un cluster da un punto cliccato |
| `POST /api/view` | riceve un PNG catturato dal canvas |
| `POST /api/report` | genera `report.html` |
| `GET /api/experiments` | registri di sweep, per la galleria di curazione |

---

## 6. Il motore per step: impronta, stato, invalidazione

È il pezzo che la § 4 della spec di architettura promette e che il codice non ha
mai avuto, ed è la ragione per cui l'interfaccia può dire onestamente che cosa è
ancora valido.

### 6.1 La catena di impronte

Ogni step dichiara **quali blocchi di configurazione consuma**:

| Step | Blocchi consumati |
|---|---|
| 01 load | `input` |
| 02 segment | `segment` |
| 03 downsample | `downsample` |
| 04 normals | `normals` |
| 05 reconstruct | `surface` |
| 06 repair | `repair` |
| 07 surface quality | nessuno |
| 08 simplify | `simplify` |
| 09 tetrahedralize | `tet` |
| 10 volume quality | `tet` |
| 11 export | `tet`, `analysis` |

L'impronta di uno step è lo sha256 della serializzazione canonica dei propri
blocchi **concatenata all'impronta dello step precedente**. La catena è ciò che
produce l'invalidazione a valle senza scriverla a mano: cambiare
`surface.poisson_depth` cambia l'impronta dello step 5, e con essa quelle di 6,
7, 8, 9, 10 e 11, mentre 1, 2, 3 e 4 restano identiche e i loro artefatti restano
riusabili.

La forma è la stessa dell'impronta di candidato della Fase 2
(`core/sweep.py:27`), che esclude il blocco `run` perché `out_dir` e `from_step`
non cambiano il risultato. Qui vale la stessa esclusione, per la stessa ragione.

### 6.2 Lo stato salvato

Un file `steps.json` nella cartella della corsa, accanto a `config.yaml` e
`metrics.json`, porta per ogni step: impronta, esito, istante, e il nome
dell'artefatto prodotto con la sua impronta di file.

Gli stati sono cinque: **mai eseguito**, **valido**, **non valido**, **in corso**,
**fallito**. «Valido» significa una cosa sola e verificabile: l'impronta
ricalcolata dal config corrente coincide con quella salvata **e** l'artefatto
dichiarato esiste con l'impronta di file dichiarata. Non è un'etichetta che si
scrive dopo un'esecuzione riuscita e poi si crede sulla parola: è una condizione
che si ricontrolla, ed è la ragione per cui la § 9 può elencarne il controllo che
la smentisce.

### 6.3 Che cosa non cambia

`pipeline.run` resta e continua a fare esattamente ciò che fa oggi: esegue la
sequenza dall'inizio o da `from_step`. Diventa un chiamante del registro di step
invece di contenere il ciclo. Il criterio è che i comandi con cui sono stati
prodotti tutti i numeri delle Fasi 1 e 2 restino validi alla lettera, compreso
`uv run meshrec run <config>` che ogni riga di registro della Fase 2 porta nel
campo `rerun`.

---

## 7. Annullamento e coerenza della cartella

### 7.1 La correzione alla radice

`pipeline` scrive i risultati parziali in **`metrics.partial.json`** durante
l'elaborazione e rinomina il file in `metrics.json` **soltanto** quando la corsa
arriva in fondo. Una corsa interrotta lascia quindi intatto l'ultimo
`metrics.json` completo, che è precisamente ciò che oggi non accade.

La rinomina è la correzione lazy e insieme quella alla radice: tutti i chiamanti
passano da lì, e nessun chiamante deve imparare a distinguere un file completo da
uno parziale.

**Requisito di compatibilità con la Fase 2.** `sweep.run_candidate`
(`core/sweep.py:272`) legge `metrics.json` per costruire la riga di un candidato,
compreso un candidato fallito, e `measure_thickness_error`
(`core/sweep.py:468`) ne legge `metrics["01_load"]["spacing"]`. Con la correzione,
un candidato fallito non avrebbe più alcun `metrics.json`: lo sweep legge quindi
`metrics.json` e, se assente, `metrics.partial.json`. `is_complete` resta
invariato e continua a funzionare. Un test verifica che una riga di registro di
un candidato fallito porti le stesse informazioni di oggi.

### 7.2 Artefatti scritti in modo atomico

L'annullamento di uno step lungo può cadere in mezzo alla scrittura di un
artefatto: `01_cloud.ply` di `lab_crop` pesa 151.898.454 byte e `wall_model.inp`
di `muro` 35.931.310 byte, quindi la finestra è reale e non teorica. Ogni artefatto si
scrive su un nome temporaneo nella stessa cartella e si rinomina a scrittura
conclusa. Dopo un annullamento l'artefatto di uno step o è completo o non esiste:
non esiste il terzo caso, che è quello che rende una cartella incoerente.

> **Numeri corretti il 16/08/2026.** La stesura originale citava 34.665.787 byte
> per `09_volume.vtu` di `lab_crop` e 87.229.481 per il suo `wall_model.inp`.
> Erano veri quando furono misurati e sono diventati falsi quando lo sweep di
> Fase 2 ha adottato `poisson_depth=7`: oggi quei due artefatti pesano 938.012 e
> 2.545.069 byte, trentacinque volte meno. L'argomento non cambia — la finestra
> di scrittura resta reale — ma la citazione ora usa uno step a monte del fronte
> adottato, che non invecchia quando il fronte cambia.

### 7.3 Granularità e onestà del progresso

Il worker è un **processo separato**, come i candidati della Fase 2 e per le
stesse tre ragioni misurate (isolamento reale da un'uccisione per memoria, riuso
di un percorso già verificato, costo di avvio trascurabile). L'annullamento è la
terminazione di quel processo, quindi la granularità è **uno step**: si annulla
lo step in corso, non una sua frazione.

**Il progresso non è una percentuale.** Gli step sono chiamate a Open3D, PyMeshLab
e TetGen che non offrono callback di avanzamento. L'interfaccia mostra quale step
è in corso, da quanto tempo, e le righe che il processo scrive; non mostra una
barra che avanza, perché una percentuale fabbricata è esattamente un numero
plausibile che nessuna metrica smentisce. Il riferimento temporale che si può
dare onestamente è la durata dell'esecuzione precedente dello stesso step, letta
da `steps.json`, dichiarata come tale: su `lab_crop` lo step 9 è durato **34,39
secondi** (`runs/lab_crop/metrics.json`, `09_tetrahedralize.seconds`).

---

## 8. Il viewport

### 8.1 Decimazione con mappa

`core/viewport.py` espone una decimazione che restituisce i punti ridotti **e**,
per ognuno, gli indici della nuvola piena che vi ricadono, costruita sopra
`voxel_down_sample_and_trace` (§ 4.3).

Il passo del voxel non è un numero scelto: si ricava dal budget di punti
dichiarato in `ViewportConfig`. Si parte dalla spaziatura media della nuvola,
che il core già calcola (`io.mean_spacing`), e si raddoppia il passo finché il
conteggio scende sotto il budget. La ricerca è deterministica, costa pochi
passaggi e non introduce alcun parametro da tarare.

Il budget predefinito è **400.000 punti**, cioè 4,8 MB in Float32, e il numero ha
un ancoraggio letto e non inventato: è dell'ordine di `04_normals.ply` di
`lab_crop`, **5.571.038 byte**, un artefatto che la pipeline scrive e rilegge di
routine a ogni corsa.

L'interfaccia mostra **sempre** entrambi i conteggi, quello disegnato e quello
pieno. Una nuvola decimata che non dichiara di esserlo è un dato falso presentato
come vero.

### 8.2 Ritaglio e selezione agiscono sul dato pieno

Il box di ritaglio disegnato nel viewport produce coordinate, non indici: il
server le passa a `segment.crop_box` (`core/segment.py:40`), che è la stessa
funzione che la pipeline usa oggi, e ne scrive il risultato in
`segment.crop_min` e `segment.crop_max` del config. L'interfaccia disegna il box;
il core esegue il ritaglio. Il clic sul cluster risolve il punto disegnato al suo
gruppo di traccia, quindi agli indici pieni, quindi al `cluster_index` che
`segment.segment_cloud` consuma.

Questo è il motivo per cui la mappa serve davvero, ed è anche il motivo per cui
il ritaglio conta più della selezione automatica: la § 1 della spec di
architettura documenta che su `lab_frame.pcd` non c'è un ambiente da cui isolare
il muro, e che la via praticabile è il ritaglio a box.

### 8.3 Deviazione per vertice

La funzione nuova in `core/quality.py` restituisce un array, uno scalare per
vertice della superficie: la distanza dal punto più prossimo della nuvola
sorgente. Il viewport lo riceve come Float32 e lo mappa a colore.

Il controllo che la smentisce è nella § 9 ed è il vincolo di progetto di questa
grandezza: la sua radice quadratica media deve riprodurre l'`RMS` che
`geometric_error` già restituisce. Se non lo riproduce, il campo per vertice non
misura la stessa cosa dell'aggregato pubblicato in `fase-1-esiti.md` e non è
utilizzabile.

### 8.4 Il contratto vale sulla tratta

In Fase 2 «non solleva mai» era stato applicato a una funzione su quattro sulla
stessa tratta, e le altre tre hanno fatto perdere il registro. Qui il contratto è
dichiarato sul percorso: **nessun endpoint solleva verso il browser**; ognuno
restituisce un errore strutturato con tipo, messaggio e lo step a cui si
riferisce. La verifica è su **tutti** gli endpoint elencati nella § 5.1, non su
un campione: un test parametrizzato sull'elenco degli endpoint, che fallisce se
un endpoint nuovo viene aggiunto senza entrare nell'elenco.

---

## 9. I controlli che smentiscono

| Grandezza nuova | Controllo che la smentisce |
|---|---|
| Stato «valido» di uno step | L'impronta ricalcolata dal config corrente e l'impronta di file dell'artefatto devono coincidere con quelle salvate in `steps.json`. Un test cambia un parametro a monte e verifica che gli step a valle passino a «non valido» e quelli a monte no — prova a variabile unica |
| Nuvola decimata nel viewport | L'unione dei gruppi di traccia deve coprire tutti gli indici della nuvola piena, senza ripetizioni. Un punto pieno che non sta in alcun gruppo è una zona su cui il clic non agisce, e non lo si vedrebbe guardando il disegno |
| Box di ritaglio | I punti che il box seleziona nel viewport e quelli che `segment.crop_box` seleziona sullo stesso box devono essere gli stessi, misurato su `lab_crop` e non sul cubo |
| Deviazione per vertice | La radice quadratica media del campo deve riprodurre l'`RMS` di `geometric_error` entro tolleranza dichiarata. Non riprodurlo significa che le due misure non misurano la stessa cosa |
| Cartella coerente dopo annullamento | Un test annulla uno step lungo davvero, non simulato, e verifica che `metrics.json` resti quello completo precedente e che nessun artefatto sia troncato |
| Vista catturata | Il PNG deve contenere pixel non di sfondo, con la stessa asserzione usata nella misura della § 4.5. Un canvas vuoto passerebbe qualunque controllo di sola esistenza del file |
| Report | Il report conta le viste attese e quelle presenti, e dichiara le assenti. Un report con riquadri vuoti non è distinguibile da uno completo se nessuno conta |
| Ogni endpoint | Il test parametrizzato della § 8.4, che copre l'elenco intero |

---

## 10. Le tre sorveglianze, scelte prima di ogni soglia

Nessuna richiede taratura. Tutte sono affermazioni qualitative, con la stessa
struttura della soglia a metà di `min_ratio` e di `footprint_coverage`.

- **Punti pieni non raggiungibili dalla mappa.** La grandezza non è «quanti punti
  disegnare», che richiederebbe una soglia tarata sul carico grafico, ma «quanti
  punti pieni non sono raggiungibili da alcun punto disegnato». Deve essere zero,
  e zero non è una soglia scelta: è la condizione perché il clic sia onesto.
- **Step marcati validi la cui impronta non torna.** Deve essere zero. Anche qui
  la grandezza è scelta prima: contare quanti step sono validi non dice nulla,
  contare quanti si dichiarano validi senza esserlo dice tutto.
- **La deviazione per vertice si confronta con una misura, non con una soglia.**
  Il riferimento è l'`RMS` già pubblicato, non un numero scelto: non c'è nulla da
  tarare, esattamente come per lo spessore nella Fase 2.

---

## 11. Che cosa deve dire `lab_crop`

Un criterio misurato solo sul cubo verifica che la catena non si spezzi, non che
produca qualcosa di sensato. Per questa fase «funziona» significa che funziona
sui numeri veri, letti da `runs/lab_crop/metrics.json`:

1. **Il viewport regge la scansione reale.** 6.329.096 punti letti, **4.229.538**
   dopo la segmentazione, contro i 116.059 della nuvola già ridotta a voxel da
   10 mm. `GET /api/cloud/{step}` decima l'artefatto dello step richiesto, e il
   requisito è che decimi davvero quello dello step 2 quando è lo step 2 a essere
   chiesto: servire al suo posto la nuvola dello step 3, che è già piccola e
   pronta, mostrerebbe una nuvola diversa da quella su cui il ritaglio agisce.
2. **Il ritaglio funziona dove la segmentazione automatica non funziona.** È
   l'unico modo praticabile su `lab_frame.pcd`, per la ragione documentata nella
   § 1 della spec di architettura.
3. **La deviazione per vertice si guarda dove l'aggregato era cieco.** Sulla
   scansione reale l'errore bidirezionale restava a 3,85 mm mentre lo spessore
   ricostruito valeva 214,0 mm contro 176 mm (§ 7 di
   [`fase-2-sweep.md`](../../../meshrec/docs/fase-2-sweep.md)). Una mappa di
   colore che mostri quell'errore distribuito è utile solo se misurata lì.
4. **I tempi si misurano lì.** Lo step 9 su `lab_crop` dura **34,39 secondi** e
   la superficie di partenza ha 199.891 vertici e 398.044 triangoli. Sul cubo
   tutto è istantaneo e nessuna decisione di interfaccia sull'attesa sarebbe
   informata.

Le corse di riferimento `runs/muro/` e `runs/lab_crop/` restano **di sola
lettura**: l'interfaccia le apre, le legge e ne copia il config, e non scrive mai
al loro interno. Vale identicamente per `experiments/muro/` e
`experiments/lab_crop/`, che portano i registri della Fase 2.

---

## 12. Ordine di priorità, e dove si taglia

L'ordine è dichiarato. Se il tempo non basta si taglia **dal fondo**, mai in
mezzo. Il design `impeccable` non è un punto della lista perché è continuo: il
criterio di chiusura è il punteggio massimo di `audit` e `critique`, e non si
riveste alla fine ciò che è nato storto.

| # | Punto | Perché qui |
|---|---|---|
| 1 | Server, comando di avvio, apertura del browser, guscio a tre zone, lista verticale degli step con stato | Senza questo non esiste niente da guardare |
| 2 | Core: `metrics.json` coerente sull'annullamento, motore per step con impronta e invalidazione a valle | Difetto noto più la capacità su cui poggiano 3, 5 e 7 |
| 3 | Processo separato: avanzamento, log dal vivo, annullamento | La § 7 promette che l'interfaccia non si blocca mai; è la promessa che regge o cade da sola |
| 4 | Core: decimazione con mappa degli indici, nuvola nel viewport | 4.229.538 punti; senza mappa il viewport disegna una nuvola finta |
| 5 | Pannello dei parametri e pannello delle metriche, esecuzione e riesecuzione da qui | Rende pilotabile ciò che 2 e 3 hanno costruito |
| 6 | Viewport: superficie triangolare e contorno del volume | La catena diventa ispezionabile fino in fondo |
| 7 | Box di ritaglio che agisce sulla nuvola piena | Usa la mappa del 4; è la via praticabile sulla scansione reale |
| 8 | Selezione del cluster con un clic | Stessa mappa, ma il ritaglio conta di più |
| 9 | Core: campo di deviazione per vertice, mappe di colore | Diagnostica: informa, non abilita |
| 10 | Piano di taglio sul volume | Ispezione interna, comoda e non necessaria |
| 11 | Galleria di curazione: registro e fronte di Pareto della Fase 2 nell'interfaccia | La § 6 della spec di architettura la elenca per questa fase; i dati esistono già, è lettura |
| 12 | Report: cattura delle viste dal canvas, `report.html` rivestito | Il report della Fase 2 esiste e funziona già senza |

I due tagli naturali: **sotto il 9** resta un'applicazione completa e onesta
senza diagnostica di colore; **sotto il 6** resta un'applicazione che esegue e
mostra ma non si comanda dal viewport. **Sotto il 4 non si taglia**: un viewport
che disegna una nuvola scollegata dal dato è la forma esatta del risultato
plausibile che nessuna metrica smentisce.

---

## 13. Il criterio di chiusura del design

L'aspetto visivo — sistema di design, tipografia, colore, gerarchia, stati,
micro-interazioni — è definito da `impeccable`, a partire da `impeccable init`.
Questa spec fissa che cosa deve esserci e come si comporta, non che aspetto ha.

Il criterio di chiusura non è negoziabile: **`impeccable audit` e `impeccable
critique` al punteggio massimo.** `audit` assegna 0-4 su cinque dimensioni
(accessibilità, prestazioni, temi, responsività, integrità dell'implementazione);
`critique` assegna 0-4 sulle dieci euristiche di Nielsen più il verdetto di
specificità del design. Massimo significa 4 su ogni dimensione e su ogni
euristica applicabile.

Il ciclo gira con ralph loop, con un **tetto di dieci cicli**. Al decimo, se il
massimo non c'è, ci si ferma: il lavoro resta nello **stato migliore raggiunto**,
non nell'ultimo, e il documento del mattino scrive che cosa manca a ciascun
criterio e perché. **Un ciclo che alza il punteggio e rompe un test si annulla**:
non si smonta codice funzionante per inseguire un punto.

---

## 14. Criteri di accettazione

1. `uv run meshrec serve` avvia il server e apre il browser sull'interfaccia.
2. L'interfaccia esegue la pipeline su `lab_crop` da capo a fondo, step per step,
   e i numeri che mostra coincidono con `metrics.json`.
3. Cambiando un parametro a monte, gli step a valle passano a «non valido» e
   quelli a monte no — prova a variabile unica.
4. La riesecuzione da uno step in giù riusa gli artefatti a monte: verificato dal
   fatto che gli step a monte non vengono rieseguiti e le loro impronte di file
   non cambiano.
5. Uno step lungo viene annullato davvero e la cartella resta coerente:
   `metrics.json` è ancora quello completo precedente, nessun artefatto è
   troncato.
6. Il viewport disegna la nuvola segmentata di `lab_crop` e dichiara entrambi i
   conteggi, disegnato e pieno.
7. Un box di ritaglio disegnato nel viewport seleziona gli stessi punti che
   `segment.crop_box` seleziona con le stesse coordinate, su `lab_crop`.
8. La radice quadratica media del campo di deviazione per vertice riproduce
   l'`RMS` di `geometric_error`.
9. Il report generato contiene almeno una vista catturata, con pixel non di
   sfondo, e dichiara le viste assenti.
10. `impeccable audit` e `impeccable critique` al punteggio massimo, oppure il
    documento del mattino elenca che cosa manca a ciascun criterio.
11. La suite passa: i 181 test attuali più quelli nuovi, con i 6 deselezionati
    che restano tali.

---

## 15. Fuori scope

Multiutente, autenticazione, esecuzione remota, impacchettamento in eseguibile:
già fuori dalla § 12 della spec di architettura e non riaperti qui. Modifica
della geometria dal viewport: il viewport ispeziona e seleziona, non scolpisce.
Editor di configurazione libero in forma di testo: i parametri si toccano dai
modelli, che li validano. Il prior «muro» e la mesh esaedrica sono la Fase 4; il
banco sintetico e CalculiX in batch sono la Fase 5.

### Debiti che questa fase non chiude

Vanno detti perché nessuno li dia per chiusi leggendo che la Fase 3 è finita:

- **Nulla rivalida la superficie dopo lo step 8.** Lo step 7 verifica chiusura e
  orientazione, lo step 8 modifica la superficie e nessun controllo viene
  rieseguito. Il motore per step rende il buco più visibile — lo step 8 avrà uno
  stato «valido» che non dice nulla sulla qualità di ciò che produce — e non lo
  chiude.
- **`FACE_FRONT` e `FACE_BACK` restano decorativi** su una scansione reale, per
  qualunque tolleranza, e l'interfaccia li mostrerà come gli altri set.
- **I nomi dei set di faccia restano convenzioni**, non identificazioni delle
  facce fisiche.
- **Il controllo dei dati con Abaqus resta dovuto**, in attesa di una licenza.
- **La griglia della Fase 2 resta a un asse per volta**: la galleria di curazione
  mostra ciò che il registro contiene, e il registro non contiene interazioni fra
  assi.
