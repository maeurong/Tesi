# Fase 5 — L'analisi strutturale

Data: 21/08/2026. Apre la Fase 5, dopo che
[`fase-4-prior-telaio.md`](../../fase-4-prior-telaio.md) ha chiuso la Fase 4 al
deck.

Documento di progetto, non di esiti: dice che cosa la fase deve costruire e
perché. Gli esiti li scriverà `docs/fase-5-analisi.md` alla chiusura.

## 0. La regola che governa questo documento

Ogni numero qui dentro è stato misurato **in questa sessione**, sulla cosa di
cui parla, eseguendo e non leggendo. Dove un numero viene da un file già su
disco, il file è nominato. Dove una cosa non è stata misurata, il documento lo
dice invece di tacere.

È la regola che la Fase 4 ha pagato undici volte, in tre varianti: affermazione
mai eseguita, misura scaduta dopo un cambio di codice, misura letta dalla
cartella sbagliata (`docs/fase-4-cantiere/README.md`). Aprendo questa fase ne è
emersa una dodicesima, in un docstring, ed è descritta al § 3.1.

## 1. Che cosa la fase consegna

La Fase 4 si ferma al deck: i controlli col solutore verificano che sia
leggibile e risolvibile, non producono un'analisi. La Fase 5 risolve davvero,
e per farlo deve prima riparare un difetto che solo un solutore poteva rendere
visibile.

Sei consegne:

1. **Uno step 13 nella pipeline** che esegue CalculiX sul deck della corsa e
   lascia risultati, grezzo del solutore e provenienza nella cartella della
   corsa.
2. **Un deck a quattro step** — peso proprio, spinta orizzontale, carico in
   sommità, modale — che il solutore legge **a zero avvisi**.
3. **La correzione dell'asse altezza e del set `BASE`** (§ 3), senza la quale
   su questa geometria non esiste un'analisi onesta.
4. **Una grandezza nuova che sorveglia il vincolo**, al posto di una che oggi
   dichiara `1.0` mentre metà degli appoggi non è vincolata.
5. **Il campo di spostamento e tensione nel viewport**, con la scala e
   l'amplificazione dichiarate.
6. **Il documento di esiti**, con il registro di ciò che i risultati non hanno
   il diritto di affermare (§ 7).

## 2. Il quadro di partenza, misurato aprendo la fase

`ccx` è CalculiX 2.22, in `/Users/mario/.local/bin/ccx` (`ccx -v`).

Il deck as-built usato per tutte le prove è
`runs/lab_telaio_v2/wall_model.inp`, la corsa madre della Fase 4: 14.103 nodi,
51.913 tetraedri C3D4, 0 invertiti, volume 217.728.361 mm³, massa 0,5443209 t,
materiale `CALCESTRUZZO_C25_30` (E 31500 MPa, ν 0,2, ρ 2,5e-9 t/mm³).
**Quella cartella vive oggi in un worktree** (`.claude/worktrees/fase-4-materiale/`)
e `runs/` è in `.gitignore`: la corsa madre va rigenerata in questo albero
prima di qualunque misura definitiva, altrimenti si ricade nella variante
"cartella sbagliata" del difetto (§ 0). Le prove di questo documento sono state
fatte copiando il deck fuori dalla corsa, senza scrivere dentro nessuna
cartella di corsa.

### 2.1 Il deck gira, e due card vengono scavalcate in silenzio

Eseguito `ccx` sul deck as-built così com'è: `Job finished`, returncode 0,
41.475 equazioni, 0,89 s di orologio. Due avvisi:

```
*WARNING reading *STEP: parameter not recognized: NAME=GRAVITA
*WARNING reading *OUTPUT: parameter not recognized: FIELD
```

Sono card Abaqus che CalculiX non conosce. Nessuno le legge, e la pipeline non
sa che esistono.

`.dat` prodotto: **0 byte** — il deck non ha `*NODE PRINT`. `.frd`: 3.186.570
byte, **binario**, perché `*NODE OUTPUT`/`*ELEMENT OUTPUT`, nel dialetto di
CalculiX, chiedono l'uscita binaria. Sostituendoli con `*NODE FILE`/`*EL FILE`
il `.frd` diventa ascii, 7.994.597 byte, 14.103 nodi per blocco.

### 2.2 Lo spostamento sotto peso proprio è di 15 mm

Con il deck così com'è, gravità lungo `-z` del modello: **max |U| = 15,6436 mm**,
mediana 9,4098 mm, su un telaio in C25/30 alto 2,5 m. Non è plausibile: per la
sola compressione assiale l'ordine atteso è 10⁻³ mm.

Non è un artefatto puntuale: 6.871 nodi su 14.103 superano i 10 mm.

### 2.3 L'errore geometrico, e una cifra da correggere

Da `metrics.json`, `07_surface_quality.geometric_error.mesh_to_cloud`:

| corsa | RMS | massimo | campioni |
|---|---:|---:|---:|
| `lab_telaio_v2` (ritaglio completo, con zapatas) | 27,54 mm | 135,69 mm | 10.968 |
| `lab_crop` (solo telaio) | 4,36 mm | 72,24 mm | 9.659 |

Il massimo di 72 mm appartiene a `lab_crop`, non al ritaglio completo, il cui
massimo è 135,69 mm.

## 3. Il difetto trovato

### 3.1 Un docstring che afferma il falso

`abaqus.build_node_sets`, righe 625-626:

> `BASE` e `TOP` sono verificati: l'asse z e' il verticale reale (vedi
> `align_to_axes`), quindi il minimo e' davvero la base del solido.

Su `lab_telaio_v2` è falso. Misurata la rotazione salvata in
`metrics.json`, `11_export.transform`: l'asse z del modello sta **22,43°** fuori
dal verticale del sistema originale. Sulle altre due corse la stessa misura dà
`lab_crop` **0,39°** e `muro` **0,45°**: il calcolo funziona lì e cede qui.

Dodicesima istanza del difetto della fase precedente, variante "affermazione mai
eseguita". Il codice a valle è corretto **dato** quel presupposto, ed è ciò che
l'ha resa invisibile.

### 3.2 La catena, misurata

`align_to_axes` sceglie l'asse altezza fra le due direzioni principali che
restano dopo aver scartato lo spessore, prendendo quella più vicina al
verticale. Sul ritaglio completo le zapatas — larghe 700 mm nominali, tutte in
basso — spostano la PCA: la direzione scelta è la migliore delle due
disponibili ed è comunque a 22,43°.

`build_node_sets` costruisce poi `BASE` come i nodi entro la tolleranza dal
minimo di z-modello. Con il piano z=0 inclinato di 22,43° e i due piedi distanti
circa 2,4 m, il secondo piede finisce circa un metro più in alto in z-modello, e
la tolleranza di 134,97 mm non lo raggiunge mai.

Misurato sul deck: `BASE` sono **278 nodi su 14.103**, tutti in una toppa
x 337,6–527,1, y 574,0–807,6, z 0–134,8, su un modello che si estende in
y da 0 a 3144,2. **Un piede solo.** Il telaio è incastrato in un angolo.

Somma delle reazioni su `BASE`, dal `.dat`: (34,476; −2004,943; 4858,062) N,
modulo ≈ 5254 N contro un peso di 5339,8 N.

### 3.3 La prova della diagnosi

Ricostruito `BASE` prendendo i nodi bassi rispetto al verticale **del sistema
originale** invece che a quello del modello, con la stessa tolleranza:
**3.719 nodi**, estesi in x mondo da 1630,8 a 4312,3, cioè entrambi i piedi.

| modello | max \|U\| | mediana |
|---|---:|---:|
| `BASE` di oggi, un piede | 15,2544 mm | 9,8556 mm |
| `BASE` dal verticale vero, due piedi | **0,0367 mm** | 0,0055 mm |

Fattore 415 sul massimo. (Entrambe le corse con gravità già riorientata al
verticale vero, per isolare l'effetto del solo vincolo: riorientare la gravità
da sola cambia il risultato del 2%, da 15,6436 a 15,2544 mm. Il vincolo è la
causa, non la direzione del carico.)

### 3.4 La metrica che avrebbe dovuto dirlo

`metrics.json` porta `11_export.fixed_nset_coverage: 1.0`.

`abaqus.footprint_coverage` non ha un bug: ha una grandezza sbagliata, e il suo
stesso docstring lo dichiara — «la misura ha tre parametri impliciti — il lato
della cella, la banda di contatto e l'asse — ed è per questo che serve come
diagnosi e non come regola».

Il meccanismo: `in_contact` sono le colonne il cui nodo di bordo più basso sta
entro il 2% dell'altezza dal minimo globale. Su 2524,6 mm di altezza sono
50,5 mm. Col modello inclinato, solo un piede sta in quella banda; quel piede è
tutto ciò che la metrica vede; `BASE` lo raggiunge tutto; risultato 1,0.

Risponde correttamente a una domanda diversa da quella che serve.

## 4. Le decisioni prese in brainstorming

| # | decisione | scelta |
|---|---|---|
| D1 | casi di carico | peso proprio, spinta orizzontale, carico in sommità, modale |
| D2 | portata della correzione | asse altezza **e** set `BASE` — il modello sta dritto |
| D3 | la metrica cieca | è un task della fase, non solo una nota nel documento |
| D4 | dove gira il solutore | step 13 dentro `run`, non un comando a sé |
| D5 | portata UI | i risultati arrivano al viewport |
| D6 | forma dei risultati | artefatto nuovo `13_solution.vtu` (approccio C) |
| D7 | deficit di volume | task che lo misura e lo scompone |

Le tre alternative valutate per D6:

- **A**, campi solo nel `.frd`: scartata perché ogni consumatore dovrebbe
  riallineare i nodi del `.frd` ai vertici del contorno estratti dal `.vtu`, in
  due punti diversi. È la forma d'errore che questa fase esiste per evitare.
- **B**, campi dentro `wall_model.vtu`: scartata perché uno step riscriverebbe
  l'artefatto di un altro, e `wall_model.vtu` porta un'impronta nel registro di
  sweep.
- **C**, artefatto proprio: corrispondenza per costruzione senza toccare
  artefatti altrui. Scelta.

Sul registro di sweep, verificato: le undici righe di
`experiments/lab_crop/registro.jsonl` portano l'impronta di `wall_model.inp` e
di `wall_model.vtu`, ma hanno `artifacts_kept: false` — i file non esistono più
e nessuna riga è riverificabile oggi. `docs/fase-4-materiale.md` aveva già
dichiarato quel registro irraggiungibile da `lab.yaml` dopo il cambio di
materiale. Il ponte era già bruciato prima di questa fase.

## 5. Il design

### 5.1 Lo step 13

Esegue `ccx` sul deck dello step 11, nella cartella della corsa. Artefatti:

| artefatto | contenuto |
|---|---|
| `13_solution.vtu` | nodi ed elementi del deck, più `point_data`: spostamenti e tensioni nodali per caso di carico, forme modali. È l'artefatto del progetto. |
| `13_solution.frd` | grezzo del solutore, ascii |
| `13_solution.dat` | reazioni su `BASE`, autovalori |
| `13_solver.log` | stdout completo di `ccx` |

`metrics.json["13_solve"]` porta **solo scalari**; i campi stanno nel `.vtu`.

**Senza `ccx`** lo step non fa fallire la corsa: scrive
`{"eseguito": false, "solutore": "assente"}` e nient'altro. Un esito misurato,
non un fallimento. Nessun ripiego, nessuna simulazione: se il solutore manca,
non c'è analisi e il programma lo dice. `PRODUCT.md` dichiara utenti successivi
confermati che non avranno necessariamente CalculiX.

**Gli avvisi si leggono.** Il deck di progetto è a zero avvisi (§ 5.2, misurato).
Lo step conta le righe `*WARNING` e `*ERROR` nello stdout e le porta in
`metrics.json`. Un avviso nuovo è un difetto per costruzione. Stesso meccanismo
con cui il Ruling AH della Fase 4 contava i `no tied MPC`.

**Lo sweep non risolve.** `13_solve` resta fuori da `sweep.REQUIRED_STEPS`,
come `12_wall` per il Ruling D.

**Configurazione.** Il blocco `analysis` cresce con i casi di carico, **senza
predefiniti**, per la stessa ragione di `config.Material`: la spinta e il carico
in sommità sono decisioni di chi analizza, non grandezze deducibili dalla
nuvola. Chi non li dichiara ottiene il solo peso proprio, che è l'unico caso
derivabile da densità e gravità già presenti.

### 5.2 Il deck

Un deck, quattro step, un'esecuzione. Verificato: `ccx` li accetta in fila,
`Job finished`, **0 avvisi e 0 errori**.

| step | carichi |
|---|---|
| `GRAVITA` | `*DLOAD, GRAV` lungo `-z`, che dopo la correzione del § 5.3 è il verticale vero |
| `SPINTA_ORIZZONTALE` | gravità più una seconda `*DLOAD, GRAV` orizzontale, coefficiente dichiarato |
| `CARICO_TOP` | gravità più `*CLOAD` sui nodi di `TOP`, risultante dichiarata e ripartita |
| `MODALE` | `*FREQUENCY`, numero di modi dichiarato |

Ogni step statico stampa `RF` su `BASE` con `*NODE PRINT`: è il controllo di
conservazione, e sta nel deck perché è lì che il solutore lo può dare.

**Dialetto.** `*NODE FILE`/`*EL FILE` sostituiscono `*OUTPUT, FIELD` +
`*NODE OUTPUT` + `*ELEMENT OUTPUT`: sono keyword Abaqus legacy, valide, e sono
quelle che CalculiX vuole per l'uscita ascii. Il nome del passo scende a
commento (`** NOME PASSO: GRAVITA`), perché CalculiX rifiuta `NAME=` e un avviso
benigno tollerato è un avviso che nasconde quello vero.

Costo dichiarato: i nomi dei passi spariscono dal lato Abaqus. Non c'è licenza
per verificarlo, quindi il documento di esiti non affermerà nulla su Abaqus.

**Misurato su `lab_telaio_v2` con `BASE` riparato**, deck a quattro step:

| caso | max \|U\| | mediana \|U\| | von Mises max | von Mises mediana |
|---|---:|---:|---:|---:|
| peso proprio | 0,0367 mm | 0,0055 mm | 0,5056 MPa | 0,0544 MPa |
| + spinta 0,1 g | 0,0446 mm | 0,0136 mm | 0,6763 MPa | 0,0537 MPa |
| + carico *di sonda* 10 kN su `TOP` | 0,2985 mm | 0,1527 mm | 3,1111 MPa | 0,2675 MPa |

I 10 kN sono un valore di **sonda**, servito solo a far girare il deck: non è un
carico dichiarato e non deve comparire in nessun esito.

Modale, 6 modi, `U^T·M·U = 1` su tutti e sei:

| modello | f₁ |
|---|---:|
| `BASE` riparato, due piedi | 21,19 Hz |
| `BASE` di oggi, un piede | 4,03 Hz |

Fattore 5,3. **Il controllo modale avrebbe trovato il difetto del § 3 da solo.**

### 5.3 La correzione dell'asse e del set

`align_to_axes` smette di far decidere l'altezza alla PCA:

- **z = il verticale del sistema originale**, senza eccezioni;
- **x = lo spessore**, dalla PCA a due dimensioni sulla proiezione orizzontale
  del riferimento: la direzione orizzontale con estensione minore, segno da
  `fix_sign` come oggi;
- **y = z × x.**

Non è solo una correzione: è il codice che fa quello che il suo docstring già
dichiara — «lo scanner è livellato, l'unica ambiguità è l'imbardata». Oggi lo
dichiara e poi lascia decidere l'altezza a una PCA tridimensionale. Dopo,
l'imbardata è letteralmente l'unica cosa che resta da stimare.

**`build_node_sets` non si tocca.** Raddrizzato l'asse, prende i piedi giusti da
sola: meno codice, non di più. Il docstring del § 3.1 diventa vero per
costruzione invece che per assunzione.

Costi dichiarati:

- `muro` (0,45°) e `lab_crop` (0,39°) si raddrizzano; i loro `.inp` rigenerati
  cambiano. Le cartelle su disco non si toccano: sono di sola lettura;
- su un pezzo davvero fuori piombo, `BASE` diventa un taglio orizzontale invece
  della base del pezzo. Per un'analisi a gravità è la cosa giusta, ma cambia
  cosa significano `BASE` e `TOP` e va scritto negli esiti;
- se le due estensioni orizzontali fossero vicine, l'assegnazione x/y diventa
  instabile. Su `lab_crop` sono 176 contro 2759 mm, quindi non è il caso qui —
  ma il task lo **misura**, non lo presume.

### 5.4 La grandezza che sorveglia il vincolo

Principio 2 di `PRODUCT.md`: la grandezza si sceglie prima della soglia. Non si
ritara la banda del 2% di `footprint_coverage`: si cambia grandezza.

**Estensione in pianta dell'insieme vincolato contro estensione in pianta del
pezzo.** Misurata oggi sul modello di oggi: `BASE` occupa x 337,6–527,1 e
y 574,0–807,6, su un pezzo che in pianta va da 0 a 875 e da 0 a 3144,2.
Rapporti **0,22 e 0,074**.

Perché questa e non un'altra:

- vale 1 per un muro, e **vale 1 anche per un telaio a due piedi**, perché i due
  piedi coprono l'intera lunghezza pur essendo vuoti in mezzo. Non confonde
  "vuoto in mezzo" con "manca un appoggio";
- crolla a 0,074 quando si tiene un angolo di una cosa larga. Tredici volte di
  divario: **la soglia non è delicata**, che per il principio 2 è il segno che
  la grandezza è quella giusta;
- non ha parametri impliciti: nessun lato di cella, nessuna banda, nessun asse.

Soglia proposta 0,5. Il task che la implementa **deve misurarla su `muro`,
`lab_crop` e `lab_telaio` e mostrare la struttura del margine** — dove regge,
qual è il primo valore che non regge, dove crolla. Stessa disciplina con cui
`set_tolerance_factor` è arrivata a 6 e `min_ratio` al suo valore. Nessuna
soglia senza la tabella che la giustifica.

**`footprint_coverage` non si cancella:** resta come diagnosi, che è ciò per cui
è scritta. Le due insieme raccontano il caso meglio di ciascuna da sola:
«l'insieme copre tutto l'appoggio che vede, e vede il 7% del pezzo».

**Il verdetto viaggia coi risultati.** Ogni spostamento e ogni tensione in
`metrics.json`, nel report e nel viewport porta accanto l'esito del vincolo.
Sotto soglia i risultati restano scritti — non si nascondono — marcati come non
citabili.

Via d'aggiornamento dichiarata, se un giorno l'estensione in pianta non
bastasse: contare gli appoggi distinti come componenti connesse delle celle di
contatto. Coglie "un piede su due" in modo diretto, costa
un'etichettatura di componenti connesse, e non serve per il caso misurato.

### 5.5 L'estrazione

| grandezza | fonte | perché lì |
|---|---|---|
| spostamenti, tensioni, forme modali | `.frd` ascii | unico posto con il campo per nodo |
| reazioni su `BASE` | `.dat` | già sommabili; `tests/feasibility/ccx_utils.py` legge già questo formato |
| frequenze | `.dat` **e** `.frd` | doppia lettura: devono coincidere, ed è un controllo gratis |
| avvisi ed errori | stdout | unico posto dove `ccx` li scrive |

**Tre trappole nel parser `.frd`, tutte misurate:**

1. **L'attribuzione blocco→step si legge, non si conta.** Il record `100CL`
   porta il numero di step, e nei blocchi modali porta la frequenza al posto del
   tempo (verificato: 21,19324067, identica al `.dat`). Contare i blocchi in
   ordine sembra funzionare e cade appena si aggiunge uno step o si cambiano le
   uscite richieste. Su questo deck i blocchi `DISP` sono nove per quattro step:
   tre statici più sei modi.
2. **Colonne fisse, non `split()`.** Nei blocchi modali il campo esce come
   `4MODAL`, numero di step e tipo di analisi incollati. Un `split()` legge un
   token solo e l'attribuzione salta in silenzio.
3. **Le tensioni dei blocchi modali non sono tensioni.** Le forme sono
   normalizzate sulla massa. Calcolarci sopra una von Mises dà numeri fino a
   **88,5 MPa**, misurati: plausibili per un calcestruzzo e privi di significato
   fisico. Il parser marca i blocchi `MODAL` come forme, e da lì non escono né
   millimetri né MPa.

La terza è la bugia più facile dell'intera fase: un numero grande, plausibile,
uscito da un'analisi vera, con la provenienza in ordine, che non significa
nulla.

### 5.6 Il viewport

`app.server._contorno_del_volume` restituisce `(vertici, facce)` e **butta via**
la corrispondenza verso i nodi originali, che `np.unique(..., return_inverse)`
calcola già al suo interno. Senza quella, un campo per nodo non sa a quale
vertice del contorno appartiene: è la trappola d'allineamento descritta al § 4 (approccio A), viva.

Correzione: `_contorno_del_volume` torna `(vertici, facce, indici)` e
`VERSIONE_CONTORNO` passa a 2, così la cache vecchia si sfratta da sola. Il
campo sul contorno diventa `valori[indici]` — corrispondenza per costruzione.

Il resto è riuso: `13_solution.vtu` entra in `pipeline.ARTIFACTS`, il server lo
serve come ogni altro `.vtu`, `viewport.campo_per_punto` codifica lo scalare.
Nuovo in `viewport.js` c'è una funzione sola, `mostraMeshPerCampo(vertici,
facce, valori)`: è `mostraMesh` più il blocco di colori per vertice che
`mostraNuvolaPerMembratura` ha già.

Tre trappole visive:

- **La scala schiacciata.** max/p99 = 2,16 sul peso proprio, misurato: una scala
  lineare da 0 al massimo comprime 14.103 nodi in basso perché uno solo sta in
  cima. La scala si taglia al p99, chi lo supera prende un colore dichiarato, e
  la legenda dice dov'è il taglio e quanti nodi sono sopra. Principio 3: un nodo
  non decide la scala di tutti gli altri.
- **L'amplificazione.** 0,0367 mm su 2,5 m non si vede a 1:1, e qualunque
  amplificazione fa sembrare vera una deformazione inventata. Il fattore si
  **deriva dal dato** — quello per cui lo spostamento massimo vale il 2% della
  diagonale del modello — e si scrive **sempre** accanto alla vista, insieme
  allo spostamento vero in millimetri.
- **Le forme modali.** Si mostrano con etichetta fissa: forma, ampiezza
  arbitraria, frequenza. Mai un numero in mm o in MPa accanto a una forma
  modale. Nel viewport è più facile cadere che altrove, perché la vista è
  identica a quella di un caso vero.

Il verdetto del vincolo (§ 5.4) si vede sopra il modello: un campo di colore è
la cosa più persuasiva che questo programma produce, e in discussione viene
proiettato.

## 6. I controlli che smentiscono

Cinque, ciascuno con cosa coglie.

**a. Somma delle reazioni = ρVg, come vettore.** Coglie carico perso, vincoli
non intenzionali, densità sbagliata. Misurato sul modello rotto: (34,476;
−2004,943; 4858,062) N contro 5339,8 N di peso. Il task misura lo scarto sul
modello riparato e **dichiara la tolleranza con la misura che la giustifica**.

**b. Estensione in pianta del vincolo** (§ 5.4). Coglie la struttura tenuta per
un angolo: 0,074 contro 1.

**c. Autovalori reali, positivi, nessuno vicino a zero.** Coglie il modello che
è un meccanismo. Costa zero: la modale c'è già.

**d. Zero avvisi, zero errori.** Coglie ogni card che il solutore scavalca.
Misurato che il deck di progetto può stare a zero, quindi qualunque avviso è un
difetto e non rumore.

**e. Dove sta il picco, e quanto è appuntito.** Due grandezze senza parametri:
il rapporto max/p99 della von Mises, e la frazione dei nodi sopra il p99 che
cade entro la banda di vincolo. Misurati sul peso proprio: rapporto 2,16, e
**0% dei 142 nodi sopra il p99 sta sotto z = 200 mm** (banda scelta e dichiarata
qui). Il picco sta a z = 2286 mm, non sull'incastro. Qualificano l'elemento che
porta il picco riusando `aspect_ratio` e `min_dihedral_deg` già calcolati allo
step 10: nessuna macchina nuova.

**Il controllo che NON si adotta:** lo stimatore d'errore di CalculiX. Chiesto
con `ERR` in `*EL FILE`, il blocco `ERROR` esce **a zero su tutti e nove i
blocchi**, misurato. L'ipotesi che sia perché i tetraedri sono lineari resta
**un'ipotesi non verificata** e va scritta come tale. Se il modello passasse un
giorno a C3D10, è la prima cosa da riprovare.

**Il controllo che esiste già e resta:** colonna incastrata sotto peso proprio
contro forma chiusa, `tests/feasibility/test_calculix.py`, passa.

### 6.1 Le mutazioni obbligatorie

Ogni test nuovo dichiara la mutazione che lo uccide **e la applica**. Queste
quattro sono vincolanti, perché coprono i modi di fallimento toccati aprendo la
fase:

| test | mutazione che deve ucciderlo |
|---|---|
| attribuzione blocco→step | invertire l'ordine dei blocchi nel `.frd` di prova |
| lettura a colonne fisse | spostare l'offset di una colonna |
| blocchi modali marcati come forme | togliere il marchio: un test deve accorgersi che escono MPa da una forma |
| somma delle reazioni | scalare la densità del 10% nel deck: lo scarto deve superare la tolleranza |

## 7. Cosa il documento di esiti avrà il diritto di affermare

1. **Il confronto ha una colonna sola.** Zero membrature accettate significa
   nessun modello parametrico su questa geometria: solo l'as-built. Non si mette
   accanto il telaio sintetico a quattro membrature e non lo si chiama
   validazione: quello è un banco, non il pezzo.
2. **Nessuna armatura.** Calcestruzzo omogeneo, scelta dichiarata. Nessuna
   verifica normativa, nessun confronto con `f_ck`. Le tensioni sotto peso
   proprio (mediana 0,054 MPa, massimo 0,506) sono piccole rispetto a qualunque
   resistenza: dire "verifica soddisfatta" sarebbe promuovere a esito un carico
   che non sollecita.
3. **La base è dove abbiamo tagliato.** `crop_min[2] = -498` sta sopra il
   pavimento misurato a −498,5. Dopo la correzione l'incastro prende entrambi i
   piedi, il che è meglio, ma resta un incastro perfetto su una superficie di
   taglio. Vale la formula di `report.NOTE_NON_GEOMETRICHE`, identica.
4. **L'errore geometrico.** 27,54 mm RMS e 135,69 mm di massimo contro uno
   spessore mediano di 192 mm: 14% e 71%. La sezione locale è incerta a quella
   scala, e σ = F/A. Nessuna tensione con tre decimali.
5. **Il modello pesa meno della metà del pezzo.** Volume 217.728.361 mm³ contro
   477.700.000 mm³ nominali dalla tavola `MURO 1`: **45,6%**. Massa 0,5443 t
   contro 1,194 t. Sotto peso proprio le tensioni scalano con la massa. Il
   § 8, task D7, misura e scompone questo deficit.
6. **`TOP` è un set per tolleranza.** Il carico in sommità si ripartisce sui 397
   nodi in modo uniforme e si concentra dove i nodi sono più fitti.
7. **Abaqus non entra.** Nessuna licenza. Nulla si afferma su Abaqus, e si dice
   in più che i nomi dei passi sono scesi a commento per tenere CalculiX a zero
   avvisi.
8. **La scomposizione resta al suo soffitto.** L'asse mediale è la via
   dichiarata. Spessore e PCA locale sono già stati provati e misurati: chi
   riprende non li rifaccia.

## 8. Il deficit di volume (D7)

Un task quantifica quanta parte dei 260 milioni di mm³ mancanti è la porzione
interrata esclusa dal ritaglio — `crop_min[2]` sta sopra il pavimento per
costruzione, e il § 8 di `fase-4-prior-telaio.md` dichiara che la zapata è
visibile solo per il tratto sopra il pavimento — e quanta è assottigliamento
della ricostruzione, confrontando il solido con i prismi nominali della tavola
sopra il piano di taglio.

Guadagno: le tensioni sotto peso proprio, che è il caso di carico principale,
acquistano un fattore di scala noto invece di un'incertezza aperta.

Se una delle due parti non risultasse misurabile, si scrive quanto si sa e si
dichiara non attribuito il resto. Non si stima.

## 9. Fuori portata

- **Nessuna verifica normativa.** Nessun confronto con resistenze di progetto,
  nessun coefficiente parziale, nessuna combinazione di carico da norma.
- **Nessuna armatura**, né come barre né come rigidezza equivalente.
- **Nessuna non linearità**: materiale elastico lineare, piccoli spostamenti.
- **Nessuna mesh conforme alle giunzioni**, e nessun modello parametrico: non
  sono generabili su questa geometria (Fase 4, § 6).
- **Nessuna riscrittura delle corse di riferimento**: `runs/muro/`,
  `runs/lab_crop/`, `experiments/muro/`, `experiments/lab_crop/` restano di sola
  lettura.
- **Nessun numero del provino di laboratorio in `src/`.**
- **Nessuna validazione con Abaqus.**

## 10. Ipotesi non verificate, elencate come tali

1. Che il blocco `ERROR` di CalculiX esca a zero perché i tetraedri sono lineari
   (§ 6). Misurato lo zero, non la causa.
2. Che il deficit di volume del § 7.5 sia in parte la porzione interrata delle
   zapatas. La causa è plausibile e dichiarata al § 8 della Fase 4, ma la
   ripartizione non è misurata: è ciò che il task D7 deve chiudere.
3. Che l'assegnazione x/y dopo la correzione dell'asse resti stabile su tutte e
   tre le geometrie. Il task la misura.
