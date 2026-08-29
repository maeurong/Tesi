# OpenSees come secondo solutore, e la modellazione delle armature

Ricerca del 28/08/2026, su repo `main` a `787fdeb`. Domanda posta: se il
programma possa offrire **OpenSees** come alternativa a CalculiX scelta
dall'utente, e se in uno dei due si possano **inserire le armature** del telaio
in cemento armato rilevato al laser scanner.

Le fonti sono primarie: il sorgente di OpenSees su GitHub, la documentazione
ufficiale di OpenSeesPy, il wiki di Berkeley, il manuale ufficiale di CalculiX
scaricato da `dhondt.de`, e PyPI. Dove una domanda non si chiudeva leggendo, il
binario ufficiale di OpenSees è stato **scaricato ed eseguito** in questa
sessione, e la prova è riportata con il suo esito.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte primaria in questa sessione (pagina
  ufficiale, file di sorgente, metadati PyPI).
- **[M]** = misurato o eseguito in questa sessione. Non è una citazione: è un
  esperimento, e il comando che lo produce è riportato.
- **[INF]** = inferenza mia, non letta su fonte. Da non citare come fatto.
- **[NON TROVATO]** = non l'ho trovato pubblicato in chiaro. Non l'ho inventato.

## Artefatti consultati

| artefatto | provenienza | stato |
|---|---|---|
| sorgente OpenSees, ramo `master` a `2890cb3` (14/08/2026) | <https://github.com/OpenSees/OpenSees> | letto file per file [V] |
| tag `v3.8.0` dello stesso repo (rilascio del 18/02/2026) | idem | letto sui punti in cui il ramo `master` poteva divergere [V] |
| `openseespylinux-3.8.0.0-py3-none-any.whl`, 86,3 MB | PyPI | scaricato, estratto, **eseguito** [M] |
| manuale CalculiX 2.23, edizione HTML (`ccx_2.23.htm.tar.bz2`, 3.082.645 B) | <https://www.dhondt.de/> | scaricato ed estratto, 3832 file [V] |
| documentazione OpenSeesPy | <https://openseespydoc.readthedocs.io/> | letta pagina per pagina sui comandi citati [V] |
| wiki OpenSees, indice degli elementi | <https://opensees.berkeley.edu/wiki/index.php/Element_Command> | letto [V] |

**Premesse del committente, ricontrollate prima di ragionarci sopra.** Tutte e
sette risolvono: il deck è monomaterico (una sola riga `*SOLID SECTION` in
`abaqus.write_inp`), `abaqus.export_model` è lo step 11, `solve.leggi_frd` legge
il `.frd` di ccx, `config.TetConfig.element` ammette `C3D10` e `C3D4` con
predefinito `C3D10`, `config.ModelConfig.element` ammette i tre esaedri,
`wall.prior` scompone la nuvola in membrature prismatiche e `hexa.costruisci`
ne genera i modelli parametrici. Nessuna correzione da riportare. [V]

---

## 1. Elementi solidi 3D in OpenSees

### 1.1 Il catalogo documentato

L'indice ufficiale degli elementi — wiki di Berkeley e documentazione
OpenSeesPy, che concordano — elenca sotto «Brick Elements» e «Tetrahedron
Elements»: [V]

| elemento | nodi | note dalla documentazione |
|---|---|---|
| `stdBrick` | 8 | esaedro isoparametrico standard |
| `bbarBrick` | 8 | formulazione B-bar, per quasi incomprimibilità |
| `Twenty Node Brick` | 20 | esaedro quadratico |
| `Twenty Seven Node Brick` | 27 | presente solo nell'indice del wiki |
| `SSPbrick` | 8 | *stabilized single point*, un solo punto di Gauss |
| `FourNodeTetrahedron` | 4 | tetraedro lineare, **un punto di Gauss** |

Sul tetraedro la documentazione ufficiale è netta e va letta come sta: **elenca
un solo tetraedro, quello a 4 nodi**. Firma esatta, dalla pagina OpenSeesPy:
`element('FourNodeTetrahedron', eleTag, *eleNodes, matTag, <b1, b2, b3>)`, con
`b1, b2, b3` forze di volume — è così che si applica la gravità. [V]

Il tetraedro a 4 nodi di OpenSees è lo stesso oggetto che
[`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md) qualifica per
CalculiX: un tetraedro lineare, qui per giunta a **un solo punto di
integrazione**, cioè con una regola ancora più povera di quella del C3D4 di ccx.
Tutte le obiezioni raccolte in quel documento — 31,5% di errore sullo
spostamento e 21,2% sulla tensione nella mensola di Benzley, tensione che non
migliora raffinando — valgono qui a maggior ragione. [INF, ma l'inferenza è solo
il trasporto: i numeri sono quelli già verificati]

### 1.2 Il tetraedro a 10 nodi esiste, e non è documentato

La documentazione dice che non c'è. Il sorgente dice il contrario.

`SRC/element/tetrahedron/` contiene sei file: `CMakeLists.txt`, `Makefile`,
`FourNodeTetrahedron.cpp`, `FourNodeTetrahedron.h`, **`TenNodeTetrahedron.cpp`**
e **`TenNodeTetrahedron.h`**. Presenti sia sul ramo `master` sia sui tag
`v3.7.1` e `v3.8.0`. [V]

L'intestazione di `TenNodeTetrahedron.h` dice, verbatim:

> «Implements a standard 10-node tetrahedron element. This element has 4 Gauss
> points of integration.»

Autori dichiarati: «2022 By Jose Abell and José Larenas @ Universidad de los
Andes, Chile». Ultima modifica del `.cpp`: 23/04/2024, commit `c2e9245`. [V]

L'elemento è **registrato in entrambi gli interpreti**, e questo è ciò che lo
rende invocabile: `SRC/interpreter/OpenSeesElementCommands.cpp` lo mette nella
propria `functionMap` sotto la chiave `"TenNodeTetrahedron"`, e
`SRC/element/TclElementCommands.cpp` ha il proprio ramo `strcmp` per la stessa
stringa. La sintassi la dichiara il messaggio d'errore dell'elemento stesso,
verbatim:

> «Want: element TenNodeTetrahedron eleTag? Node1? Node2? Node3? Node4? Node5?
> Node6? Node7? Node8? Node9? Node10? matTag? <doInitDisp?>»

Quattro punti di Gauss, regola simmetrica a quattro punti sul tetraedro,
`wg[0] = 1.0/24.0`. Un `NDMaterial` per punto. [V]

**Quanto vale «non documentato», misurato.** Sulla pagina ufficiale degli
elementi di OpenSeesPy, conteggio delle occorrenze: `FourNodeTetrahedron` 2,
`stdBrick` 2, `bbarBrick` 4, `SSPbrick` 4, **`TenNode` 0**. Zero anche per
`ASDEmbedded`, `EmbeddedBeam`, `FiberOverlay`. L'indice degli elementi del wiki
di Berkeley non lo nomina. [M]

**Verifica che esista anche nel binario distribuito.** Il wheel ufficiale
`openseespylinux-3.8.0.0` è stato scaricato da PyPI ed estratto; il modulo
compilato **opensees.so** pesa 254.608.632 B. Conteggio delle occorrenze della
stringa nel binario: `TenNodeTetrahedron` 320, `FourNodeTetrahedron` 314,
`ASDEmbeddedNodeElement` 350, `Brick8FiberOverlay` 163, `ReinforcingSteel` 208,
`PlateRebar` 296. L'elemento non è solo nel sorgente: è nella ruota che si
installa con `pip`. [M]

**E funziona.** Un solo tetraedro quadratico, spigoli di 100 mm, materiale
`ElasticIsotropic` con E = 30 000 MPa e ν = 0,20, faccia di base incastrata,
1000 N verticali sul vertice libero, `analyze(1)` rende 0 e lo spostamento del
vertice caricato vale −0,0675096774193546 mm. Lo stesso modello con il
tetraedro a 4 nodi rende −0,0018 mm: **trentasette volte più rigido**, che è
esattamente la patologia del tetraedro lineare descritta in
[`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md), e qui si misura in
casa su un elemento singolo. [M]

### 1.3 La numerazione dei nodi di lato **non** è quella di Abaqus

Questo è il punto che decide se un deck si possa tradurre.

Le funzioni di forma di `TenNodeTetrahedron` sono scritte in chiaro nel `.cpp`,
come derivate rispetto alle quattro coordinate di volume. Integrandole:

| nodo | funzione di forma | spigolo |
|---|---|---|
| 5 | 4·ζ1·ζ2 | 1-2 |
| 6 | 4·ζ2·ζ3 | 2-3 |
| 7 | 4·ζ1·ζ3 | 1-3 |
| 8 | 4·ζ1·ζ4 | 1-4 |
| 9 | 4·ζ3·ζ4 | **3-4** |
| 10 | 4·ζ2·ζ4 | **2-4** |

La convenzione di Abaqus, quella che questo repository ha misurato per conto
proprio ed è scritta nel commento di `volume.TETGEN_A_ABAQUS`, vuole il nodo 9
sullo spigolo 2-4 e il nodo 10 sullo spigolo 3-4. **Gli ultimi due nodi di lato
sono scambiati.** [V, per lettura; l'integrazione delle derivate è meccanica]

Che non sia un caso lo dice il sorgente stesso: sotto ogni riga attiva c'è la
riga commentata con la convenzione opposta, e le righe attive sono marcate con
un `// *`. Qualcuno ha scelto, e ha lasciato in vista che cosa ha scartato.

Conseguenza pratica: la permutazione `volume.TETGEN_A_ABAQUS` che il programma
già applica **non basta** per OpenSees. Servirebbe una seconda permutazione, che
scambia gli ultimi due nodi. Sbagliarla non produce un errore: produce un
maglio valido all'occhio e una rigidezza falsa — la stessa classe di difetto
dell'ordine delle colonne del `.frd` (D2 nel registro del
[`README.md`](README.md)), e va sorvegliata dagli stessi oracoli: controllo
geometrico del punto medio e patch test.

**Caveat sulla verifica della convenzione Abaqus.** Il manuale di CalculiX
descrive la numerazione del C3D10 rimandando alla Figura 63, che è
un'**immagine**: il testo non la enuncia. La convenzione qui usata è quella che
questo repository ha misurato riconoscendo ogni nodo di lato come punto medio
del proprio spigolo, ed è già sotto due oracoli indipendenti
(`tests/test_quadratico.py` e il patch test). Non è una lettura, è una misura
che sta in albero. [V del rimando alla figura; la convenzione è [M] di un'altra
sessione, non di questa]

### 1.4 Leggere le tensioni dal tetraedro a 10 nodi corrompe la memoria

Il difetto più grave trovato, e sta nell'unica via per avere le tensioni.

`TenNodeTetrahedron::setResponse` dichiara per `"stresses"` un
`ElementResponse(this, 3, Vector(6*4))`, cioè 24 valori: sei componenti per
ciascuno dei quattro punti di Gauss, etichettate `sigma11 sigma22 sigma33
sigma12 sigma23 sigma13`. Ma `TenNodeTetrahedron::getResponse` apre con

    static Vector stresses(6);

e poi scrive **ventiquattro** valori in quel vettore da sei, con un contatore
`cnt` che non si azzera fra i punti di Gauss. Diciotto `double` finiscono oltre
la fine dell'allocazione. Identico per `"strains"`. [V]

Non è teoria. Eseguito sul binario ufficiale, `eleResponse(1, 'stresses')` su un
`TenNodeTetrahedron` **abortisce il processo**:

    malloc(): unaligned tcache chunk detected
    Aborted (exit 134)

Lo stesso `eleResponse(1, 'forces')` sullo stesso elemento rende regolarmente 30
valori; e `eleResponse(1, 'stresses')` su un `FourNodeTetrahedron` rende
regolarmente 6 valori, perché lì i punti di Gauss sono uno solo e il vettore da
sei basta. Il difetto è specifico del tetraedro a 10 nodi. [M]

> Allo stato del ramo `master` a `2890cb3` e del rilascio `v3.8.0`, **le
> tensioni del tetraedro quadratico di OpenSees non si possono leggere**. Il
> comando che le chiede termina il processo.

### 1.5 Il registratore PVD non conosce il tetraedro a 10 nodi

`SRC/recorder/PVDRecorder.cpp` tiene una mappa da tag di classe a tipo di cella
VTK. Contiene `ELE_TAG_FourNodeTetrahedron` → `VTK_TETRA`. **Non contiene
`ELE_TAG_TenNodeTetrahedron`**, che pure esiste in `SRC/classTags.h` col
valore 256. Quando il tag non è in mappa, il codice fa: [V]

    int type = vtktypes[ctag];
    if (type == 0) {
        opserr<<"WARNING: the element type cannot be assigned a VTK type\n";
        return -1;
    }

Cioè avvisa e non scrive il file. Il registratore `PVD` — l'unica uscita
ParaView nativa di OpenSees, `recorder('PVD', filename, '-precision',
precision=10, '-dT', dT=0.0, *res)` — **non può esportare un modello di
tetraedri quadratici**. [V]

### 1.6 Una stampa di debug rimasta in `getInitialStiff`

`TenNodeTetrahedron::getInitialStiff` contiene, dentro il doppio ciclo sulle
funzioni di forma:

    std::cout << shp[p][q] << std::endl;

Presente sia sul ramo `master` sia sul tag `v3.8.0`. Sono 4 × 10 × 4 numeri su
stdout per ogni chiamata. Nella stessa funzione più in basso la stampa gemella
è commentata: qualcuno l'ha spenta in un posto e non nell'altro. [V]

Nella prova eseguita — analisi statica lineare con `algorithm('Linear')` — su
stdout non è comparsa **nessuna** riga: quel percorso chiama la rigidezza
tangente, non quella iniziale. La stampa esce quando qualcosa chiede la
rigidezza iniziale (per esempio un `Newton -initial`, o un'analisi agli
autovalori a seconda di come è impostata). Il fatto è verificato, il suo
innesco è delimitato ma non esaurito. [M per l'assenza nella prova fatta; [NON
TROVATO] l'elenco completo dei percorsi che la fanno scattare]

### 1.7 Riepilogo della domanda (a)

Un equivalente del `C3D10` **c'è**, si chiama `TenNodeTetrahedron`, ha quattro
punti di Gauss come il C3D10 di CalculiX, ed è nella distribuzione binaria. Ma:
non è documentato in nessuna delle due fonti ufficiali; numera i nodi di lato
in modo diverso da Abaqus sugli ultimi due; le sue tensioni non si possono
leggere senza terminare il processo; e non si può scrivere in ParaView col
registratore nativo.

Se il tetraedro quadratico non lo si vuole usare, l'alternativa dentro OpenSees
non è un altro tetraedro: è **l'esaedro**, `stdBrick` a 8 nodi, `bbarBrick`, o
il quadratico a 20 nodi. Il che porta il confronto sul terreno di
`hexa.costruisci`, che i modelli a esaedri già li genera, e non su quello di
`volume.tetrahedralize_with_metrics`.

---

## 2. Le armature in OpenSees

Vanno tenuti separati due mondi, perché le risposte sono opposte.

### 2.1 Modelli a telaio, sezione a fibre: strada maestra, pienamente documentata

È il terreno per cui OpenSees è stato scritto, ed è documentato per intero.

Una `section('Fiber', secTag, '-GJ', GJ)` — oppure `'-torsion', torsionMatTag` —
è, verbatim dalla documentazione: [V]

> «Each FiberSection object is composed of Fibers, with each fiber containing a
> UniaxialMaterial, an area and a location (y,z).»

Le fibre si generano con tre comandi da chiamare **dopo** il comando di sezione:
`fiber`, `patch` (per il calcestruzzo, a griglia) e `layer` (per le barre). La
firma di `layer` è, verbatim: [V]

    layer('straight', matTag, numFiber, areaFiber, *start, *end)
    layer('circ', matTag, numFiber, areaFiber, *center, radius, *ang=[0.0, 360.0-360/numFiber])

dove `areaFiber` è «area of each fiber» e `start`/`end` sono «y & z-coordinates
of first/last fiber in line (local coordinate system)». Cioè: **le barre si
posano una per una, con l'area e le coordinate vere**, non come strato spalmato.

I materiali monoassiali per farlo ci sono tutti e sono documentati:
`Concrete01`, `Concrete02`, `Concrete04`, `Steel01`, `Steel02`,
`ReinforcingSteel`, `Hysteretic`. La sezione va poi su un elemento
beam-column (`forceBeamColumn`, `dispBeamColumn`). [V]

**Per questo progetto**: `wall.prior` già misura di ogni membratura asse,
origine, lunghezza, sezione e contorno. Sono esattamente i dati che servono per
scrivere un `layer('straight', ...)` con il copriferro giusto. La via è corta e
non richiede nulla di non documentato.

### 2.2 Modelli continui a elementi solidi: nessun `*REBAR`

Non esiste in OpenSees un comando che dichiari armatura dentro un elemento
solido come fa `*REBAR` di Abaqus. Quello che c'è, in ordine di vicinanza:

**a) `nDMaterial PlateRebar`, con `section LayeredShell`.** Documentato. È
l'armatura **spalmata** in uno strato di guscio: un materiale che rappresenta
barre orientate a un angolo, da impilare in una sezione a strati insieme a
`PlateFromPlaneStress`. È l'analogo del `*REBAR` di Abaqus **per i gusci**, non
per i solidi. Serve pareti e setti, non travi e pilastri di volume. [V]

**b) `Brick8FiberOverlay`.** Registrato in entrambi gli interpreti, **zero
occorrenze nella documentazione**. Sovrappone a un esaedro un fascio di fibre
di area `Af` e direzione data da quattro parametri, con un `UniaxialMaterial`.
Sviluppato a UW nel 2011 per il calcestruzzo fibrorinforzato. Limite che decide:
**funziona su esaedri a 8 nodi** (esiste il gemello `Quad4FiberOverlay` per il
quadrilatero). Non c'è la versione tetraedrica. [V]

**c) `ASDEmbeddedNodeElement`.** È la cosa più vicina agli *embedded elements*
di Abaqus, e merita attenzione perché **funziona**. Registrato in entrambi gli
interpreti, **zero occorrenze nella documentazione**. Sintassi verbatim dal
sorgente:

> «Want: element ASDEmbeddedNodeElement $tag $Cnode $Rnode1 $Rnode2 $Rnode3
> <$Rnode4> <-rot> <-p> <-K $K> <-KP $KP>»

Vincola un nodo `Cnode` a seguire l'interpolazione dei nodi `Rnode`, con una
penalità di rigidezza `K` predefinita a `1.0e18`, scalata dentro l'elemento per
la radice cubica del volume. Con tre nodi ritenuti il supporto è un triangolo,
con quattro un tetraedro. Autore: Massimo Petracca, ASDEA. [V]

Lo schema d'uso per armare un continuo è: si creano nodi di barra dove passa il
ferro, si collegano con elementi `Truss` (acciaio), e ogni nodo di barra si
annega nel tetraedro che lo contiene con un `ASDEmbeddedNodeElement`.

**Provato, e funziona — con una trappola che va conosciuta prima.** Su un
tetraedro lineare con base incastrata e vertice caricato, due nodi interni
collegati da un `Truss` e annegati con `ASDEmbeddedNodeElement`: [M]

- passando il quarto nodo ritenuto come **intero Python**,
  `element('ASDEmbeddedNodeElement', 3, 11, 1,2,3,4)`, i nodi annegati restano a
  spostamento **esattamente zero**, la barra non prende forza, e **non viene
  emesso alcun avviso**;
- passando lo stesso nodo come **stringa**,
  `element('ASDEmbeddedNodeElement', 3, 11, 1,2,3,'4')`, il vincolo si attiva:
  gli spostamenti dei nodi annegati coincidono con l'interpolazione lineare del
  tetraedro e la barra prende −95,45 N;
- con tre soli nodi ritenuti (supporto triangolare) il vincolo si attiva sempre,
  e riproduce l'interpolazione a dodici cifre.

La causa è leggibile nel sorgente: il quarto nodo è opzionale e viene letto con
`OPS_GetString()` seguito da `std::stoi`, dentro un `try/catch` che in caso di
fallimento pone `has_N4 = false` **in silenzio**. Chi passa un intero da Python
ottiene il costruttore a tre nodi ritenuti, cioè un altro modello. [V per la
lettura, [M] per il comportamento]

> Questa è la peggiore categoria di difetto per un programma che **genera**
> modelli: nessun errore, nessun avviso, un modello diverso da quello chiesto.

**d) `EmbeddedBeamInterfaceL` / `EmbeddedBeamInterfaceP` /
`EmbeddedEPBeamInterface`.** Esistono in `SRC/element/UWelements/`, nate per i
pali nel terreno. Zero occorrenze nella documentazione ufficiale. Non provate in
questa sessione. [V l'esistenza; [NON TROVATO] la sintassi documentata]

### 2.3 Che cosa è praticabile e che cosa no

| via | stato |
|---|---|
| armatura discreta su telaio a fibre | **praticabile**, documentata, materiali completi |
| armatura spalmata su gusci a strati (`PlateRebar`) | **praticabile**, documentata, ma è un modello a gusci |
| armatura spalmata su esaedri (`Brick8FiberOverlay`) | praticabile in linea di principio, **non documentata**, solo esaedri |
| armatura discreta annegata in tetraedri (`Truss` + `ASDEmbeddedNodeElement`) | **funziona**, ma non è documentata, e ha la trappola intero/stringa; il supporto tetraedrico interpola in modo **lineare** sui quattro vertici, quindi su un `TenNodeTetrahedron` ignora i nodi di lato [V dal sorgente: il costruttore accetta al più quattro nodi ritenuti] |
| un `*REBAR` di OpenSees | **non esiste** |

---

## 3. Lo stesso per CalculiX

### 3.1 `*REBAR`: non esiste

Ricerca su tutti i 3832 file dell'edizione HTML del manuale 2.23. La stringa
`rebar` compare in **un solo file**, `node376.html`, e non è una parola chiave:
sono due argomenti della subroutine utente `sigini.f`, dichiarati dal manuale
stesso inutilizzati, verbatim: [M sulla ricerca, [V] sulla citazione]

> «lrebar currently not used (value: 0)»
> «rebarn currently not used»

**CalculiX non ha la scheda `*REBAR`.** È un fatto, e decide.

### 3.2 Elementi annegati: non esistono

La stringa `embedded` compare **zero volte** in tutto il manuale. Nessuna
scheda di *embedded element*, nessun vincolo di annegamento. [M]

### 3.3 Quello che CalculiX offre al posto loro

**Il guscio composito, ed è il manuale stesso a proporlo.** §2.11 del manuale è
intitolato «Reinforced concrete cantilever beam» e risolve esattamente il nostro
problema, per il caso di una trave. La ricetta, dal deck riportato per intero
nel manuale: elementi `S8R`, materiale utente `COMPRESSION_ONLY` per il
calcestruzzo (due costanti: modulo di Young e massima trazione ammessa),
`ELASTIC` per l'acciaio, e undici strati sotto un'unica scheda
`*SHELL SECTION, ELSET=Eall, COMPOSITE` — dieci di calcestruzzo e uno d'acciaio
da 1 cm a 9,5 cm dall'estradosso. [V]

Il manuale dichiara da sé il limite del modello, verbatim:

> «in reality the steel is placed within the concrete in the form of bars. The
> modeling as a thin layer is an approximation. One has to make sure that the
> complete section of the bars equals the section of the layer»

e aggiunge due vincoli operativi: «Use of the S8R element or S6 element is
mandatory» e, sui compositi, «Notice that this feature is not (yet) available
for beam elements». Il risultato riportato: teoria della trave 152,3 MPa
nell'acciaio e 7,77 MPa di compressione massima nel calcestruzzo, calcolo agli
elementi finiti 152 MPa e 7,38 MPa. [V]

**Elementi truss.** `T3D2` e `T3D3` esistono. Il manuale, verbatim su `T3D2`:
«This element is similar to the B31 beam element except that it cannot sustain
bending. This is obtained by inserting hinges in each node of the element.» E
usa `*SOLID SECTION` invece di `*BEAM SECTION`. [V]

**Come si attaccano al solido.** Non per annegamento, ma per **nodi condivisi**.
CalculiX espande internamente gli elementi 1D e 2D in elementi di volume, e la
connessione con i veri elementi 3D viene ricostruita a mano dal codice sotto
forma di vincoli multipunto. Verbatim dal manuale, §«Connecting 1D and 2D
elements to 3D elements»:

> «Remember that the expanded elements contain new nodes only, so the connection
> between these elements and 3D elements, as defined by the user in the input
> deck, is lost. It must be reinstated by creating multiple point constraints.»

Cioè: una barra `T3D2` si lega al maglio di volume **solo se i suoi nodi sono
nodi del maglio**. Una barra che passa dentro un tetraedro, fuori dai nodi, non
ha modo di legarsi se non scrivendo a mano le `*EQUATION` con i pesi delle
funzioni di forma. [V]

### 3.4 La risposta secca alla domanda (c)

CalculiX **non supporta** `*REBAR` e **non supporta** elementi annegati. Chi
volesse armare un continuo tetraedrico in CalculiX dovrebbe: (i) far passare le
barre per nodi esistenti del maglio, il che significa condizionare la
generazione del maglio alla posizione dei ferri; oppure (ii) generare a mano le
equazioni di vincolo che legano ogni nodo di barra ai quattro (o dieci) nodi del
tetraedro che lo contiene, con i pesi delle funzioni di forma. La seconda è
tecnicamente possibile e non è supportata da nessuna scheda: è codice da
scrivere qui.

---

## 4. Formato d'ingresso e via di scrittura

### 4.1 Non c'è un file di modello: c'è un programma

La differenza più grande rispetto a CalculiX non è Tcl contro Python. È che
**OpenSees non ha un formato di deck**. CalculiX legge un `.inp`: un file di
dati, con `*NODE` e `*ELEMENT`, che `abaqus.write_inp` produce e che si può
diffare, versionare, rileggere. OpenSees si comanda: si chiama `node(...)` una
volta per nodo ed `element(...)` una volta per elemento, in Tcl o in Python. Il
modello vive nella memoria dell'interprete.

Conseguenza per un programma che genera: l'artefatto riproducibile non è più il
deck, è **lo script che lo costruisce**. Il che non è peggio — è diverso, e va
deciso a monte.

### 4.2 Tcl e Python

Sono due interpreti separati sopra lo stesso nucleo, con **due registri di
elementi distinti**: `SRC/element/TclElementCommands.cpp` per Tcl,
`SRC/interpreter/OpenSeesElementCommands.cpp` per l'interprete usato da
OpenSeesPy. Controllati su cinque nomi (`TenNodeTetrahedron`,
`ASDEmbeddedNodeElement`, `Brick8FiberOverlay`, `stdBrick`, `SSPbrick`): tutti
presenti in entrambi. Non è però garantito in generale, ed è la ragione per cui
un elemento va cercato in **entrambe** le liste prima di darlo per disponibile
nell'interprete che si userà. [M]

Differenze pratiche per chi genera:

- **Tcl** ha `source`, quindi uno script generato si può includere in un altro,
  e la generazione può produrre un file di testo che è, di fatto, un deck.
- **Python** dà il modello come stato globale del modulo: `wipe()` azzera. Un
  solo dominio per processo. Per una suite di prove che costruisce più modelli,
  vuol dire `wipe()` disciplinato o un processo per modello.
- **La trappola di §2.2 nasce qui**: in Tcl ogni argomento è una stringa e
  `OPS_GetString()` funziona sempre; da Python un intero fa fallire la lettura
  in silenzio. Gli argomenti opzionali letti come stringa sono un rischio
  specifico dell'interfaccia Python. [V]

### 4.3 Importare un maglio già fatto

**Non esiste** nel comando documentato un lettore di `.inp`, `.msh`, `.vtu` o
altro formato di maglio. La documentazione OpenSeesPy espone comandi di
costruzione, non di importazione. L'unico scarico strutturato del modello è
`printModel('-JSON', '-file', filename, ...)`, che **scrive** ma non rilegge.
[V per l'assenza nell'indice dei comandi; [INF] che non esista in assoluto —
non ho letto tutti i comandi]

In pratica: nodi ed elementi si riscrivono con un ciclo. Per il maglio di questo
progetto è un ciclo su array numpy che il programma ha già in mano dopo
`volume.tetrahedralize`, quindi il costo è basso; ma va scritto, e va verificato
con gli stessi oracoli del deck `.inp`.

### 4.4 Installabilità: verificato su PyPI oggi

`openseespy` 3.8.0.0 (caricato il 18/03/2026) è un **pacchetto ombrello**: la
sua unica ruota è `py3-none-any` e le sue dipendenze sono condizionate alla
piattaforma. Verbatim dai metadati PyPI: [V]

    openseespylinux>=3.8.0.0; platform_system == "Linux"
    openseespywin>=3.8.0.0;   platform_system == "Windows"
    openseespymac>=3.8.0.0;   platform_system == "Darwin"

Le ruote vere, alla data di oggi:

| pacchetto | ruota | Python richiesto | dimensione |
|---|---|---|---|
| `openseespywin` 3.8.0.0 | `py3-none-win_amd64` | `>=3.12` | 6,8 MB |
| `openseespymac` 3.8.0.0 | `py3-none-macosx_13_0_arm64` | `>=3.10` | 10,1 MB |
| `openseespylinux` 3.8.0.0 | `py3-none-any` | `>=3.12` | 86,3 MB |

Risposte secche alle due domande poste:

- **Windows**: sì, `win_amd64`. Nessuna ruota per Windows su ARM.
- **macOS Apple Silicon**: sì, ed è **l'unica** ruota macOS pubblicata per
  la 3.8.0.0 — `macosx_13_0_arm64`, quindi macOS 13 o superiore. **Non c'è più
  la ruota Intel**: un Mac x86_64 non installa questa versione.

Due incongruenze da conoscere: l'ombrello dichiara `>=3.10` ma la ruota Windows
richiede `>=3.12`, quindi il vincolo effettivo su Windows è 3.12; e fino alla
3.7.1.2 (21/02/2025) anche la ruota Windows era `py3-none-any`, la marcatura
per piattaforma è comparsa con la 3.8.0.0. [V]

---

## 5. Uscite e post-processing

### 5.1 Che cosa produce OpenSees

Non produce un file di risultati: produce quello che si chiede, dove si chiede,
tramite **registratori** dichiarati prima dell'analisi. La documentazione elenca
sette tipi: `Node`, `EnvelopeNode`, `Element`, `EnvelopeElement`, `PVD`,
`background`, `Collapse`. [V]

Firma verbatim del registratore di nodo: [V]

    recorder('Node', '-file', filename, '-xml', filename, '-binary', filename,
             '-tcp', inetAddress, port, '-precision', nSD=6, '-timeSeries', tsTag,
             '-time', '-dT', deltaT=0.0, '-closeOnWrite', '-node', *nodeTags=[],
             '-nodeRange', startNode, endNode, '-region', regionTag,
             '-dof', *dofs=[], respType)

Quattro formati alternativi: `-file` testuale, `-xml`, `-binary`, `-tcp` verso
un socket. `-precision` è il numero di cifre significative, predefinito 6 — che
per un confronto fra solutori è **troppo poco** e va alzato.

Il registratore `PVD` scrive `filename.pvd` più una cartella `filename/` che
«must pre-exist», con precisione predefinita 10. Grandezze registrabili
dichiarate: `disp`, `vel`, `accel`, `incrDisp`, `reaction`, `pressure`,
`unbalancedLoad`, `mass`, `eigen` — **tutte nodali**. E, come detto in §1.5, non
sa scrivere i tetraedri a 10 nodi. [V]

### 5.2 Quanto è diverso dal `.frd`

Molto, e in un punto solo poco.

| | CalculiX | OpenSees |
|---|---|---|
| che cos'è l'uscita | due file per corsa, `.frd` e `.dat`, autodescrittivi a blocchi | N file, uno per registratore, ciascuno una matrice di numeri senza intestazione (salvo `-xml`) |
| che cosa contiene | quello che chiedono `*NODE FILE` / `*EL FILE`, in blocchi nominati | solo le grandezze e i nodi che il registratore nomina |
| chi decide le colonne | il formato | chi scrive lo script |
| lettura | `solve.leggi_frd` riconosce i blocchi | va scritto un lettore per ogni registratore dichiarato |
| ParaView | il programma già scrive `wall_model.vtu` per conto proprio | registratore `PVD`, ma non per i tetraedri quadratici |

Il punto in cui sono vicini, ed è una buona notizia: **l'ordine delle
componenti di tensione coincide**. `TenNodeTetrahedron::setResponse` etichetta
`sigma11 sigma22 sigma33 sigma12 sigma23 sigma13`; l'ordine del `.frd` che
`solve.von_mises` consuma è `SXX SYY SZZ SXY SYZ SZX`. Stessa sequenza. Il
codice di von Mises non andrebbe riscritto. [V]

### 5.3 Che cosa dovrebbe avere in comune un modello di risultati per due solutori

Dalle differenze sopra, il minimo comune è: **spostamenti per nodo**,
**reazioni per nodo vincolato**, **tensioni per punto d'integrazione con
l'ordine delle sei componenti dichiarato**, **frequenze**, e i metadati che
rendono confrontabile il confronto (numero di nodi, numero di elementi, tipo di
elemento, unità, versione del solutore). I sei verdetti che `solve.risolvi` già
calcola — reazioni, autovalori, picco, vincolo in pianta, avvisi, spostamenti —
sono definiti su queste grandezze e non sul formato, quindi sopravvivono al
cambio di solutore. Ciò che non sopravvive è il lettore: `solve.leggi_frd` è
legato al `.frd` e servirebbe un secondo lettore, non una modifica di quello.
[INF: è una raccomandazione di progetto, non un fatto letto]

---

## 6. Unità

OpenSees è adimensionale come CalculiX, e lo dichiara. Due affermazioni
verbatim dal manuale utente ufficiale su opensees.berkeley.edu: [V]

> «The OpenSees interpreter does not process units.»

> «Notice should be taken that OpenSees is dimensionless, so the user must make
> sure that he uses a consistent system of units (e.g. SI).»

Il manuale aggiunge che le unità «can be used when entering values if these
units are defined previously», cioè come variabili Tcl definite dall'utente: è
una convenzione di scrittura degli script, non una funzione del programma.

**Trappole note per il sistema mm, N, MPa, tonnellata, secondo di questo
progetto.** Non ho trovato una pagina ufficiale che elenchi trappole di unità in
OpenSees. [NON TROVATO] Quello che si può affermare leggendo le firme dei
comandi:

- la gravità **non è una scheda**: non c'è un `*DLOAD, GRAV`. Si passa come
  forza di volume negli argomenti opzionali dell'elemento — `b1, b2, b3` di
  `FourNodeTetrahedron` e `TenNodeTetrahedron` — oppure come masse nodali più
  un carico. In mm/N/MPa/t la forza di volume vale ρ·g con ρ in t/mm³ e g in
  mm/s², cioè lo stesso prodotto che `config.GRAVITY_MM_S2` già sorveglia. [V
  per le firme, [INF] per la conseguenza]
- non essendoci una scheda di gravità, **non esiste il controllo di equilibrio
  che CalculiX offre gratis**: la quota tributaria che `solve.controlla_reazioni`
  confronta va ricostruita interamente da questa parte.
- la densità è il terzo argomento opzionale di `nDMaterial ElasticIsotropic`, e
  in mm/N/MPa/t vale 2,5e-9 per un calcestruzzo da 2500 kg/m³. È il valore usato
  nelle prove di questa sessione, e ha dato risultati coerenti. [M]

---

## 7. Riproducibilità

### 7.1 Misurato

Stesso script, stesso interprete, stesso `numberer`, quattro esecuzioni
consecutive: i file dei registratori sono **identici byte per byte** (stesso
md5). Cambiando solo il numeratore da `RCM` a `Plain`, gli spostamenti
cambiano nelle ultime cifre: −0,05593548387096758 contro −0,05593548387096729,
cioè uno scarto relativo dell'ordine di 1e-15. [M]

Lettura: a parità di script **e di scelte dell'analisi**, OpenSees è
deterministico. La sorgente di variazione misurata è l'ordinamento delle
equazioni, che cambia l'ordine delle somme in virgola mobile. È arrotondamento,
non instabilità.

### 7.2 Le scelte che entrano nel risultato

A differenza di un deck CalculiX, dove il solutore lo sceglie il codice, in
OpenSees fanno parte dello script — e quindi vanno versionate con esso, perché
sono ingressi a tutti gli effetti: `system` (il solutore lineare), `numberer`
(`Plain`, `RCM`, `AMD`, più le varianti parallele), `constraints` (`Plain`,
`Transformation`, `Penalty`, `Lagrange`), `algorithm`, `integrator`. Il
numeratore è documentato così, verbatim: «The DOF_Numberer object determines the
mapping between equation numbers and degrees-of-freedom». [V]

Due di queste scelte hanno effetto misurabile e prevedibile: il numeratore
sull'arrotondamento (§7.1), il gestore dei vincoli sulla **soluzione** quando ci
sono penalità in gioco — l'`ASDEmbeddedNodeElement` di §2.2 porta la propria
penalità `1.0e18`, e il risultato del vincolo dipende da quel numero.

### 7.3 Quello che non ho verificato

- Il wheel Linux distribuisce `libgomp.so.1` (OpenMP) accanto a BLAS e LAPACK di
  riferimento. Se qualche percorso sia multi-thread, e se lo sia in modo che
  cambi l'ordine delle somme, **non l'ho verificato**. [NON TROVATO]
- Il comportamento di `OpenSeesMP` / `OpenSeesSP` con partizionamento del
  dominio non è stato provato: lì l'ordine dipende dalla partizione, e
  l'aspettativa ragionevole è che il risultato cambi nelle ultime cifre al
  variare del numero di processi. [INF]
- Non ho verificato la riproducibilità **fra piattaforme** (Windows contro
  Linux contro macOS ARM), che con BLAS diversi non è scontata. [NON TROVATO]

---

## 8. Che cosa questo decide

### Strade chiuse dai fatti trovati

1. **Armare il modello continuo in CalculiX con una scheda dedicata.** Chiusa.
   `*REBAR` non esiste nel manuale 2.23, `embedded` compare zero volte. Non è
   una difficoltà: è un'assenza.
2. **Leggere le tensioni da un `TenNodeTetrahedron` di OpenSees, oggi.** Chiusa
   finché il difetto di `getResponse` sta in piedi: il comando termina il
   processo. Restano gli spostamenti, le reazioni e le forze nodali.
3. **Esportare in ParaView un modello OpenSees di tetraedri quadratici col
   registratore nativo.** Chiusa: il `PVDRecorder` non conosce quel tipo di
   cella e rifiuta di scrivere.
4. **Riusare la permutazione dei nodi che il programma già applica.** Chiusa:
   `volume.TETGEN_A_ABAQUS` porta alla convenzione Abaqus, e OpenSees scambia
   gli ultimi due nodi di lato.
5. **Trattare OpenSees come «un altro deck da scrivere».** Chiusa: non c'è un
   deck. C'è uno script da eseguire, e l'artefatto riproducibile cambia natura.

### Strade che restano aperte

1. **Armatura discreta su modello a telaio in OpenSees.** Aperta e larga: tutto
   documentato, `layer('straight', ...)` posa le barre con area e coordinate
   vere, e `wall.prior` fornisce già asse, sezione e contorno di ogni
   membratura. È la via su cui OpenSees è più forte di CalculiX, non più debole.
2. **Armatura spalmata in CalculiX su gusci compositi.** Aperta, ed è il manuale
   stesso a mostrarla nel §2.11 con i numeri di controllo. Ma è un modello a
   gusci `S8R`/`S6`, cioè un terzo tipo di modello accanto ai tetraedri e agli
   esaedri, e il manuale dichiara che il composito non è disponibile per gli
   elementi trave.
3. **Armatura discreta annegata in un continuo tetraedrico in OpenSees**
   (`Truss` più `ASDEmbeddedNodeElement`). Aperta, e **provata funzionante in
   questa sessione**, con tre riserve da mettere in conto: l'elemento non è
   documentato, ha la trappola intero/stringa che produce in silenzio un modello
   diverso, e interpola sui soli quattro vertici — quindi su un tetraedro
   quadratico ignora i nodi di lato.
4. **OpenSees a esaedri come secondo solutore.** Aperta e con meno spine:
   `stdBrick` e `bbarBrick` sono documentati, il `PVDRecorder` li conosce, e il
   repository ha già `hexa.costruisci`. Se il secondo solutore serve come
   verifica incrociata di codice — il quinto livello di prova del
   [`README.md`](README.md) — questa è la via che costa meno.
5. **Armatura discreta in CalculiX per nodi condivisi.** Aperta ma cara:
   richiede di far passare le barre per nodi del maglio, cioè di vincolare la
   generazione del maglio alla posizione dei ferri; oppure di scrivere a mano le
   `*EQUATION` con i pesi delle funzioni di forma.

### La domanda che questi fatti spostano

Il committente ha chiesto due cose come se fossero una: un secondo solutore, e
le armature. I fatti dicono che sono separate.

Per **il secondo solutore**, OpenSees ha un costo d'ingresso concreto ma
delimitato, e il tetraedro quadratico è il punto in cui costa di più: tre
difetti verificati, tutti in codice non documentato. Sugli esaedri costa molto
meno.

Per **le armature**, il fatto che decide non riguarda OpenSees: riguarda
CalculiX, che non ha né `*REBAR` né elementi annegati. Le armature non sono
una funzione da aggiungere al modello continuo esistente — sono una scelta di
tipo di modello. Discreta su telaio a fibre (OpenSees), spalmata su gusci
compositi (CalculiX), o annegata in un continuo con un elemento non documentato
(OpenSees). Tre modelli diversi, non tre opzioni dello stesso.

Nessuna di queste è una decisione: sono le strade che restano, con il prezzo di
ciascuna misurato dove si è potuto misurarlo.
