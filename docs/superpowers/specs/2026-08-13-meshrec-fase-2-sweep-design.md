# MeshRec Fase 2 — Motore di sweep, fronte di Pareto e registro degli esperimenti

- **Data:** 13 agosto 2026
- **Stato:** design approvato in sessione di brainstorming
- **Dipende da:** Fase 1 completa e su `main`
- **Spec di riferimento:** [`2026-08-12-meshreconstructor-architettura-design.md`](2026-08-12-meshreconstructor-architettura-design.md) § 6, «Fase 2 — motore di sweep»

---

## 1. Perché questa fase esiste, e che cosa consegna

La Fase 1 ha prodotto una pipeline che arriva al deck su entrambe le nuvole di
riferimento, ma i suoi parametri sono stati scelti uno alla volta e a mano: due
soli documenti — [`fase-1-min-ratio.md`](../../../meshrec/docs/fase-1-min-ratio.md)
e [`fase-1-tolleranza-set.md`](../../../meshrec/docs/fase-1-tolleranza-set.md) —
misurano un parametro ciascuno, e ognuno è costato una giornata di lavoro
manuale con cartelle di lavoro create, popolate a mano e poi rimosse. Quel modo
non scala ai cinque parametri che restano, e soprattutto non lascia dietro di sé
una tabella.

La Fase 2 consegna **il motore che rende quel lavoro ripetibile e le
configurazioni di riferimento scelte con esso**. Non è solo infrastruttura: il
motore viene esercitato sulle due corse reali e il fronte di Pareto sceglie i
parametri di `muro.yaml` e `lab.yaml`, documentati con lo stesso rigore dei due
documenti citati — criterio di accettazione dichiarato, alternative scartate con
il numero che le scarta. Il registro degli esperimenti nasce già popolato da
quelle righe, ed è la tabella sperimentale della tesi.

### I tre principi che questa fase applica

Vengono dalla sezione 4 di
[`fase-1-debito.md`](../../../meshrec/docs/fase-1-debito.md) e sono requisiti di
progetto, non citazioni:

1. **Ogni metrica riportata ha un controllo che la smentisce se il risultato si
   degrada.** Il volume racchiuso negativo era in `metrics.json` da sempre e non
   lo guardava nessuno: una metrica scritta e non guardata non vale più di una
   metrica assente. La sezione 6 elenca ogni grandezza nuova accanto a ciò che
   la smentisce, e nessuna grandezza entra nella fase senza il proprio controllo.
2. **La grandezza da sorvegliare si sceglie prima della soglia.** Una soglia
   difficile da tarare è il sintomo di una grandezza sbagliata. La sezione 7
   sceglie tre sorveglianze che non richiedono alcuna taratura.
3. **Le geometrie sintetiche verificano che la catena non si spezzi, non che
   produca qualcosa di sensato.** Ogni criterio è misurato anche su `lab_crop`,
   dove le sette affermazioni false della Fase 1 sono emerse tutte. La sezione 8
   dice che cosa solo la scansione reale può stabilire.

---

## 2. Decisioni prese in brainstorming

| Domanda | Decisione | Motivo |
|---|---|---|
| Consegna della fase | Motore più configurazioni di riferimento scelte e documentate | Un motore non esercitato sul dato reale sarebbe infrastruttura non verificata, contro il terzo principio |
| Assi del fronte | Errore di spessore, numero di tetraedri, frazione di elementi fuori vincolo | Vedi § 5 |
| Contenuto di una riga del registro | Riga più config completo più impronte; artefatti conservati solo per il fronte | Vedi § 4 |
| Multi-fidelità | **Esclusa** | Vedi § 3.4 |
| Assi della griglia | `downsample.voxel_size`, `surface.poisson_depth`, `surface.density_quantile`, `tet.min_ratio`, `tet.nobisect` | Vedi § 3.5 |
| Formato del registro | JSONL tracciato da git, tabella piatta derivata | Vedi § 4.1 |
| Report | Minimo, senza miniature | Vedi § 9 |
| Esecuzione dei candidati | Sottoprocessi sopra la riga di comando esistente | Vedi § 3.2 |

---

## 3. Architettura ed esecuzione

### 3.1 Che cosa si aggiunge

```
src/meshrec/core/sweep.py     # espansione della griglia, impronta, dominanza, registro
src/meshrec/core/report.py    # HTML e SVG generati dal registro
src/meshrec/core/config.py    # + SweepConfig, ExperimentConfig
src/meshrec/cli.py            # + comandi `sweep` e `sweep verify`
meshrec/experiments/<nome>.yaml   # dichiarazione dell'esperimento, tracciata da git
```

Il resto del core non si tocca, con una sola eccezione dichiarata: la misura di
spessore della § 5.1, che entra in `core/quality.py`.

`SweepConfig` vive in `config.py` come ogni altro parametro: resta vero che
l'unico luogo dove un parametro di elaborazione ha un valore predefinito è
`config.py`, e che le firme del core non portano predefiniti.

### 3.2 Come gira un candidato

Ogni candidato è una cartella `runs/<esperimento>/<impronta>/` con il proprio
`config.yaml`, eseguita come processo separato:

```
subprocess.run([sys.executable, "-m", "meshrec.cli", "run", <config>], ...)
```

Le corse di riferimento `runs/muro/` e `runs/lab_crop/` restano di sola lettura:
un esperimento non scrive mai al loro interno e le usa, se serve, solo come
sorgente da copiare.

Tre ragioni per i sottoprocessi invece di un pool in-process:

- **Isolamento reale.** La Fase 1 ha documentato un caso in cui il processo è
  stato ucciso dal sistema per esaurimento della memoria, senza sollevare alcuna
  eccezione. Un `ProcessPoolExecutor` che perde un worker così solleva
  `BrokenProcessPool` e porta giù lo sweep; un sottoprocesso lascia un codice di
  uscita e una riga di fallimento.
- **Riuso di ciò che è già verificato.** Il percorso eseguito è esattamente
  `meshrec run`, cioè il comando con cui sono stati prodotti tutti i numeri della
  Fase 1. Ogni candidato resta rieseguibile a mano con quel comando, e il
  registro lo riporta.
- **Costo trascurabile.** L'avvio di un interprete con Open3D importato costa
  pochi secondi contro i circa 150 secondi di una corsa completa.

Il parallelismo è ottenuto tenendo N sottoprocessi in volo insieme; i thread
dell'orchestratore attendono soltanto, non calcolano. `OMP_NUM_THREADS=1`,
fissato in `src/meshrec/__init__.py`, continua quindi a valere dentro ciascun
candidato, e la riproducibilità verificata in Fase 1 regge invariata. Questo è
un requisito e non un effetto collaterale: il parallelismo delle librerie è
dichiarato in `fase-1-esiti-lab-frame.md` § 6 come la principale minaccia alla
riproducibilità di questa pipeline.

### 3.3 Le due manopole di macchina

`sweep.workers`, predefinito **4**. Non è un numero arbitrario e non è il numero
di processori: TetGen ha un picco misurato di 1,35 GB sulla corsa del muro e la
macchina di sviluppo ha 16 GB con 7 liberi documentati. Quattro candidati in volo
sono circa 5,4 GB di picco. Il valore resta visibile e va tarato sulla macchina
che esegue: una macchina diversa ha un numero diverso, e nessun valore dedotto
dai processori logici sarebbe corretto qui.

`sweep.timeout_s`, predefinito **1800**. Un candidato patologico non deve poter
bloccare lo sweep; alla scadenza il processo viene terminato e la riga registra
il timeout come esito. Il riferimento è la corsa più lenta documentata in Fase 1,
circa 134 s, e il candidato più lento fra tutte le prove, i 186 s del solo step 9
sulla superficie raddrizzata a `min_ratio` 12,0: mezz'ora è più di dieci volte
tanto, cioè un tetto contro il patologico e non contro il lento.

### 3.4 Perché la multi-fidelità è esclusa

La spec di architettura la prevedeva: sweep su nuvola fortemente decimata e
riesecuzione a risoluzione piena solo dei primi k candidati. È esclusa per due
misure e un principio.

Il costo non la giustifica. Una corsa completa vale 98 s sul muro e circa 134 s
su `lab_crop`; con quattro processi in parallelo una griglia da qualche decina di
candidati costa dell'ordine dei venti minuti per corsa di riferimento. Non c'è un
budget da risparmiare.

La validità è dubbia proprio qui. `downsample.voxel_size` è uno degli assi della
griglia, quindi lo screening decimato altera la variabile stessa sotto misura, e
l'ipotesi che l'ordinamento a bassa fedeltà sopravviva alla risoluzione piena
sarebbe un'assunzione non verificata **dentro il meccanismo che produce la tabella
della tesi**. È la forma esatta delle sette affermazioni false della Fase 1: un
risultato plausibile che nessuna metrica smentisce.

Verificarla costerebbe più di quanto faccia risparmiare: servirebbe un
esperimento dedicato che esegua un sottoinsieme a entrambe le fedeltà e misuri la
correlazione di rango, con un criterio dichiarato sotto il quale lo screening
viene abbandonato. Si riapre se e quando una griglia misurata risulterà troppo
cara.

### 3.5 Gli assi della griglia

Cinque: `downsample.voxel_size`, `surface.poisson_depth`,
`surface.density_quantile`, `tet.min_ratio`, `tet.nobisect`.

I primi tre governano la ricostruzione, cioè l'errore di spessore; gli ultimi due
governano il compromesso fra numero di elementi e qualità. Insieme coprono i tre
assi del fronte, e nessun asse del fronte resta senza un parametro che lo muova.

Il metodo è **un asse alla volta attorno alla configurazione di riferimento**, e
passano a un fattoriale ridotto solo le coppie che la misura mostra interagenti,
cioè quelle in cui l'effetto di un asse cambia al variare dell'altro.
I cinque assi hanno livelli 3, 3, 3, 4 e 2, non tutti uguali: un fattoriale pieno
sono 3×3×3×4×2 = 216 candidati, cioè circa cento minuti per corsa di riferimento e
più di tre ore per entrambe, in gran parte spesi su combinazioni che nessuno leggerà. Il fronte di Pareto si costruisce su
qualunque insieme di candidati, quindi non richiede una griglia cartesiana per
essere valido.

`simplify` resta **fuori dagli assi**. Non è una svista di ambito: in Fase 1 il
remeshing isotropo ha portato la superficie da 426.600 a 89.772 triangoli
introducendovi **16 autointersezioni dove non ce n'erano**, spostando il
fallimento di TetGen più a monte, nel recupero del bordo, dove nemmeno
`min_ratio` 12,0 salvava. Metterlo fra gli assi significherebbe spendere metà
della griglia su candidati di cui è già misurato che peggiorano. Resta il debito
noto che nulla rivalida la superficie dopo lo step 8, ma è un debito della
sequenza degli step, non una domanda da sweep.

### 3.6 Un candidato che fallisce

Fallire è un esito, non un'eccezione da gestire. Un candidato che si interrompe —
`RefinementFailedError`, uccisione per memoria, timeout — produce **una riga con
il proprio errore**, il codice di uscita e lo stderr catturato, e lo sweep
prosegue. Un buco nel registro sarebbe indistinguibile da un candidato mai
provato, e la distinzione fra «provato e fallito» e «mai provato» è metà del
valore diagnostico della tabella: lo sweep di `min_ratio` su `lab_frame` vale
proprio per le sei righe fallite.

---

## 4. Il registro degli esperimenti

Il registro è la tabella sperimentale della tesi, quindi il requisito è che **la
provenienza di ogni riga sia ricostruibile a distanza di mesi**. Il problema è
concreto e già accaduto: in Fase 1 sono stati persi tempo e fiducia su
configurazioni non tracciate, artefatti di corse superate scambiati per correnti
e numeri finiti nel codice da una mesh di provenienza ignota. Il caso peggiore è
documentato: nella cartella `runs/lab_crop/` un `wall_model.inp` prodotto da una
corsa superata è rimasto accanto a un `metrics.json` fermo a `08_simplify`, e
niente nei due file diceva che non appartenessero alla stessa elaborazione.

### 4.1 Forma e collocazione

`meshrec/experiments/<nome>/registro.jsonl`, **tracciato da git**, in sola
aggiunta. Non può stare sotto `runs/`, che è in `.gitignore`.

JSONL e non CSV perché regge l'annidamento di `metrics.json` così com'è, senza
appiattire né perdere le distribuzioni; in sola aggiunta perché ogni candidato
nuovo sia una riga di diff e nessuna riga esistente venga mai riscritta. La
tabella piatta per l'appendice della tesi si **genera** dal registro insieme al
report: una sola rappresentazione autoritativa, nessuna copia da tenere allineata
a mano, che è il modo in cui in Fase 1 numeri di corse diverse sono finiti fianco
a fianco.

### 4.2 Che cosa porta una riga

- **impronta** del candidato, e i valori degli assi che lo distinguono;
- **config completo**, come `save_config` lo scrive, compresi i valori lasciati ai predefiniti;
- **commit del codice**, e se l'albero di lavoro era sporco al momento della corsa;
- **versioni** di `open3d`, `tetgen`, `pymeshfix`, `pymeshlab`, `numpy`;
- **data e ora**, **codice di uscita**, **durata**;
- **sha256 della nuvola d'ingresso** e **sha256 di ogni artefatto prodotto**;
- **`metrics.json` per intero**;
- **stderr catturato** e gli avvisi che ne sono stati estratti (§ 6.2);
- **esito**: riuscito, oppure fallito con il tipo di errore;
- **`artifacts_kept`**, e il comando che rigenera gli artefatti se sono stati potati.

### 4.3 L'impronta

Sha256 della serializzazione canonica del config, **escluso il blocco `run`**.
`out_dir` e `from_step` non cambiano il risultato dell'elaborazione, e includerli
renderebbe diverse due corse identiche, che è esattamente ciò che l'impronta deve
impedire.

Stessa impronta significa stesso esperimento: il motore lo dichiara e non
rilancia. È anche la cache che la spec di architettura prometteva e che il codice
non ha mai avuto — `pipeline.run` oggi non verifica nulla, e `from_step`, come
dice la sua stessa docstring, «si fida dell'operatore».

### 4.4 `sweep verify`, il controllo che smentisce il registro

`meshrec sweep verify <nome>` rilegge il registro, ricalcola le impronte degli
artefatti ancora presenti su disco e **marca stantia ogni riga che non torna**.

È l'applicazione del primo principio al registro stesso. Con l'impronta
dell'ingresso registrata, la coppia «deck di una corsa superata accanto a un
`metrics.json` parziale» non può più passare per corrente: l'impronta non
corrisponde e il comando lo dice.

### 4.5 Potatura degli artefatti

Una corsa completa produce circa 300 MB di artefatti — `02_segmented.ply` di
`lab_crop` da solo pesa 101 MB — e uno sweep da trenta candidati a risoluzione
piena riempirebbe decine di GB.

A sweep concluso, gli artefatti dei candidati **dominati** vengono rimossi;
`config.yaml` e `metrics.json` restano sempre. I candidati del fronte conservano
tutto. La riga dichiara `artifacts_kept: false` e porta il comando che li
rigenera: config completo più impronta del codice rendono la riesecuzione un
comando, non una ricostruzione.

---

## 5. Il fronte di Pareto

Tre assi, tutti da minimizzare:

1. **errore di spessore** [mm];
2. **numero di tetraedri**;
3. **frazione di elementi fuori vincolo raggio-spigolo**, misurata a limite fisso.

Dominanza stretta: un candidato è scartato se un altro lo eguaglia o lo batte su
tutti e tre gli assi e lo batte su almeno uno. Nessun punteggio pesato, nessun
peso arbitrario. I candidati falliti non entrano nel fronte ma restano righe.

Tre assi e non quattro: su una griglia da qualche decina di candidati un quarto
asse lascerebbe quasi tutto non dominato, e un fronte che non scarta nulla
restituisce la curazione per intero all'operatore, cioè non fa il proprio lavoro.

### 5.1 Perché la fedeltà è lo spessore e non l'errore geometrico

L'errore bidirezionale adottato in Fase 1 è **cieco all'errore sistematico che
più conta**. Sulla scansione reale lo spessore ricostruito vale 214,0 mm contro i
176 mm misurati fra le due facce — Poisson ingrassa il muro di circa 19 mm per
faccia — e l'errore geometrico medio resta 3,85 mm, perché è una distanza
punto-superficie e un ispessimento simmetrico la lascia bassa. Per la rigidezza
di una muratura lo spessore è la grandezza che governa: un errore del 21% sullo
spessore non è un dettaglio di fedeltà geometrica, è il modello sbagliato.

Hausdorff e RMS restano **metriche riportate in ogni riga**, e restano il ponte
con i numeri già pubblicati in `fase-1-esiti.md`. Semplicemente non sono assi.

**La misura di spessore va costruita e verificata prima di essere usata come
asse.** La forma da attuare è l'ingombro orientato lungo l'asse di minore
estensione, con `abaqus.align_to_axes`, che in Fase 1 ha già prodotto i 214,0 mm
citati sopra. Il vincolo è nella § 6.1: se applicata alla nuvola sorgente la
misura non riproduce i valori noti, non è utilizzabile e la fase si ferma lì
invece di spazzare su una fedeltà che non misura la fedeltà.

### 5.2 Perché il limite raggio-spigolo dell'asse di qualità è fisso

`tet.min_ratio` è un asse della griglia. La frazione di elementi che violano *il
proprio* vincolo confronterebbe quindi candidati contro vincoli diversi, ed è un
confronto privo di senso: un candidato lasco supera facilmente un vincolo lasco.

La frazione va misurata contro un **limite di riferimento fisso, 1,8, uguale per
tutti i candidati**, indipendente dal `min_ratio` che ciascuno ha chiesto.
`quality.radius_edge_ratios` misura già la distribuzione sul maglio prodotto; qui
cambia soltanto contro quale numero la si conta.

La grandezza è scelta secondo il secondo principio, e ha già dimostrato di
funzionare: distingue una mesh sana (8,10% sul muro, 9,55% su `lab_frame`) da una
mesh troncata scambiata per un successo (**86,36%**). La mediana dell'angolo
diedro minimo resta riportata in ogni riga, ma non è un asse: è una mediana, e
per il condizionamento di un sistema agli elementi finiti conta la coda.

---

## 6. I controlli che smentiscono

### 6.1 Tabella dei controlli

| Grandezza nuova | Controllo che la smentisce |
|---|---|
| Errore di spessore | La stessa misura, applicata alla nuvola sorgente, deve riprodurre **176 mm** su `lab_frame` e **1245,7 mm** su `muro`. Se non ci riesce, la misura non è utilizzabile come asse e la Fase 2 si ferma prima di spazzare |
| Appartenenza al fronte | Un candidato entra nel fronte solo se il suo `metrics.json` porta tutte le chiavi di step da `01_load` a `11_export`. Il blocco `finally` di `pipeline.run` scrive un dizionario parziale quando una corsa muore, e quel file è oggi indistinguibile da uno completo |
| Registro | `sweep verify` (§ 4.4) |
| Riga del registro | Ogni riga porta gli avvisi catturati (§ 6.2): un candidato che ha fatto scattare una guardia della Fase 1 lo dichiara |

### 6.2 Gli avvisi diventano colonne

`TruncatedRefinementWarning`, `IneffectiveVolumeLimitWarning`, la frazione fuori
vincolo, `footprint_coverage`, `orientation_flipped`: sono le guardie che la
Fase 1 ha aggiunto una alla volta, ognuna dopo un'affermazione falsa. Oggi gli
avvisi finiscono su stderr, che è già registrato fra il debito minore proprio
perché nessuno li rilegge.

Nel motore lo stderr del sottoprocesso è catturato e **diventa un campo della
riga**. Un candidato che ha fatto scattare un avviso lo porta scritto nel registro
per sempre, invece di averlo detto una volta a un terminale che nel frattempo si
è chiuso. È il primo principio applicato al meccanismo che raccoglie i risultati,
non solo alle singole metriche.

---

## 7. Le tre sorveglianze, scelte prima di ogni soglia

Nessuna delle tre richiede taratura; tutte sono affermazioni qualitative, con la
stessa struttura della soglia a metà di `min_ratio` e di `footprint_coverage`.

- **Frazione di candidati falliti oltre la metà.** Quando più di metà della
  griglia non arriva in fondo, è la griglia a stare nel posto sbagliato, non i
  candidati.
- **Fronte pari all'intera griglia.** Se nessun candidato è dominato, gli assi non
  stanno discriminando e il fronte non sta scartando nulla. È il fallimento
  silenzioso tipico di questo meccanismo, e senza questa sorveglianza si
  presenterebbe come un fronte ricco.
- **Lo spessore si confronta con una misura, non con una soglia.** Il riferimento
  viene dalla nuvola sorgente, non da un numero scelto: non c'è nulla da tarare.

---

## 8. Che cosa deve dire `lab_crop`

Due esperimenti con gli stessi assi, uno per corsa di riferimento. Un criterio
misurato solo sul muro sintetico verifica che la catena non si spezzi, non che
produca qualcosa di sensato.

Tre cose che solo la scansione reale può stabilire:

1. **Se una taratura della ricostruzione elimina le strozzature sotto il
   millimetro.** Se le elimina, `tet.nobisect: false` torna a convergere e la
   domanda lasciata aperta dalla Fase 1 — «`nobisect` è la leva giusta o solo
   quella che funziona» — ha una risposta misurata. Il muro sintetico non scende
   mai sotto i 1190 mm di spessore locale e su questo tace del tutto.
2. **Se l'errore di spessore regge come asse** dove la verità nota è 176 mm e la
   ricostruzione ingrassa di 19 mm per faccia.
3. **Se il fronte discrimina su un telaio con apertura**, dove solo il 16,26%
   dell'impronta poggia a terra e i due set di faccia sono decorativi.

Se nessuna taratura rimuove le strozzature, quello è un **esito negativo
documentato**, non un fallimento della fase: `nobisect` resta la leva e il
documento lo dichiara con i numeri che lo sostengono.

---

## 9. Il report

HTML statico generato dal registro: tabella dei candidati con il fronte
evidenziato, istogrammi SVG scritti direttamente, configurazione e impronte di
ogni riga, e la tabella piatta destinata all'appendice.

Nessuna libreria di grafici — la spec di architettura la esclude già, e per pochi
istogrammi non si giustifica. **Nessuna miniatura e nessun rendering 3D**: la
spec di architettura le prevedeva, ma richiedono il rendering offscreen di Open3D
su Windows, che in questo progetto non è mai stato provato, e il confronto visivo
arriva comunque con il viewport della Fase 3. La Fase 3 riveste questo report con
il proprio sistema di design invece di riscriverlo.

---

## 10. Criteri di accettazione

1. Lo sweep gira su entrambe le corse di riferimento e produce due registri
   tracciati da git.
2. Il fronte è più piccolo della griglia su entrambe: gli assi discriminano.
3. La misura di spessore riproduce i valori noti sulla nuvola sorgente, su
   entrambe le corse.
4. `sweep verify` dichiara stantia una riga resa stantia apposta — prova a
   variabile unica.
5. Un candidato ucciso produce una riga e non interrompe lo sweep, verificato
   provocandolo e non dedotto dal codice.
6. Le configurazioni di riferimento scelte dal fronte sono documentate con il
   rigore di `fase-1-min-ratio.md` e `fase-1-tolleranza-set.md`: criterio di
   accettazione dichiarato, alternative scartate con il numero che le scarta.
7. La suite passa: i 126 test attuali più quelli nuovi.

---

## 11. Fuori scope

Ottimizzazione bayesiana (già esclusa dalla spec di architettura: lo spazio ha
poche dimensioni con pochi livelli sensati, la griglia lo copre ed è spiegabile).
Multi-fidelità (§ 3.4). Miniature e rendering (§ 9). `simplify` fra gli assi
(§ 3.5). CalculiX in batch e analisi di sensibilità, che sono la Fase 5.
Interfaccia web, che è la Fase 3.

### Debiti della Fase 1 che questa fase non chiude

Vanno detti perché nessuno li dia per chiusi leggendo che la Fase 2 è finita:

- **Nulla rivalida la superficie dopo lo step 8.** La riparazione garantisce
  chiusura e orientazione, lo step 7 le verifica, lo step 8 modifica la superficie
  e nessun controllo viene rieseguito. Tenere `simplify` fuori dagli assi evita di
  spendere griglia su di esso, non risolve il buco.
- **`FACE_FRONT` e `FACE_BACK` restano decorativi su una scansione reale**, per
  qualunque tolleranza.
- **I nomi dei set di faccia restano convenzioni**, non identificazioni delle
  facce fisiche.
- **Il controllo dei dati con Abaqus resta dovuto**, in attesa di una licenza.
