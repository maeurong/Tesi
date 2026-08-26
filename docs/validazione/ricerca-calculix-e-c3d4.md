# CalculiX come codice di calcolo, e i limiti del tetraedro lineare

Ricerca del 26/08/2026, su repo `main` a `a07071a`. Ogni affermazione porta la
propria fonte. Le misure marcate «misurato» sono state eseguite in questa
sessione sugli archivi ufficiali scaricati da `dhondt.de`, non sono citazioni.

Artefatti scaricati e ispezionati: `ccx_2.22.pdf` (6.224.727 B),
`ccx_2.22.src.tar.bz2` (1.536.859 B), `ccx_2.22.test.tar.bz2` (13.418.054 B).
Le righe di sorgente citate sono di `CalculiX/ccx_2.22/src/`; il numero di riga
vale per la 2.22.

---

## 1. Qualificazione di CalculiX

### 1.1 La suite di verifica ufficiale esiste, è gratis, e non contiene un solo C3D4

Manuale ufficiale, §11 «Verification examples»: «The verification examples are
simple examples suitable to test distinct features. They can be used to check
whether the installation of CalculiX is correct». Archivio
`ccx_2.22.test.tar.bz2`.

Inventario **misurato** sull'archivio estratto:

| grandezza | valore |
|---|---|
| deck `.inp` | 610 |
| riferimenti `.dat.ref` | 605 |
| riferimenti `.frd.ref` | 212 |
| deck con `*STATIC` | 328 |
| deck con `*FREQUENCY` | 89 |
| deck con `*CLOAD` | 231 |
| deck con `*BOUNDARY` | 583 |
| deck con `*DLOAD` | 147 |
| deck con `GRAV` | 50 |

Esecuzione tramite lo script `test/compare`: per ogni `.inp` lancia ccx, poi
verifica (a) esistenza di `.dat`/`.dat.ref`, (b) stesso numero di righe,
(c) assenza di `NaN`, (d) `datcheck.pl`, (e) idem su `.frd` con `frdcheck.pl`.
**Soglia numerica letta in `datcheck.pl`: errore relativo 1e-3 (0,1%)** rispetto
al valore massimo del blocco. Caveat: lo script punta a `~/CalculiX/src/CalculiX`
cablato e va adattato; in `datcheck.pl` la stampa dell'errore relativo al valore
puntuale (`error1`) è commentata, viene riportato solo `error2`.

**Copertura di C3D4: zero.** `grep -hic 'c3d4' *.inp` su 610 deck → **0
occorrenze**. Tally per tipo: `TYPE=C3D10` 4360 righe su 18 deck, `TYPE=C3D8`
1624 su 92, `TYPE=C3D20R` 210 su 210, `TYPE=C3D20` 102 su 71, `C3D6` 2 deck,
`C3D15` 1.

> Il tetraedro lineare non è verificato dalla suite del proprio autore. Fatto
> misurato, non inferito.

Deck riusabili: `beamf.inp` (frequenze, citato dal manuale §5.2),
`segmenttet.inp` / `segmenttetsms.inp` (unici C3D10 con `*FREQUENCY`),
`achtelg.inp` e altri 49 per `GRAV`.

### 1.2 Documentazione ufficiale, riferimenti citabili

- G. Dhondt, *CalculiX CrunchiX USER'S MANUAL version 2.22*, 5 agosto 2024,
  <https://www.dhondt.de/ccx_2.22.pdf>. La 2.23 è del 19/10/2025.
- Libro canonico, riferimento [24] della bibliografia del manuale:
  **Dhondt, G., *The Finite Element Method for Three-Dimensional Thermomechanical
  Applications*, John Wiley & Sons, 2004**, ISBN 0-470-85752-8,
  DOI 10.1002/0470021217.
- Il manuale rimanda per il metodo a Zienkiewicz & Taylor [112] e Hughes [39].
  Le funzioni di forma di C3D4 e C3D10 sono attribuite a [112].

### 1.3 Confronti pubblicati, con numeri

**a) Nel manuale stesso (§5.2, Tabella 2).** Trave C3D20R, `*FREQUENCY`, 10 modi,
CalculiX contro Abaqus:

| senza precarico — CalculiX | ABAQUS | con precarico — CalculiX | ABAQUS |
|---|---|---|---|
| 13.096 | 13.096 | 705 | 1.780 |
| 19.320 | 19.319 | 14.614 | 14.822 |
| 76.840 | 76.834 | 69.731 | 70.411 |
| 86.955 | 86.954 | 86.544 | 86.870 |
| 105.964 | 105.956 | 101.291 | 102.148 |
| 351.862 | 351.197 | 345.729 | 347.688 |

Senza precarico lo scarto peggiore è **0,19%**, i primi modi coincidono a cinque
cifre. Con `PERTURBATION` divergono forte sul modo più basso (705 contro 1.780).
Deck: `beamf.inp`.

**b) Peer-reviewed, tre codici contro prova sperimentale.** Pala eolica composita
da 13 m, prova statica e dinamica a scala reale, tre modelli indipendenti
Abaqus / ANSYS / CalculiX. Prima frequenza edgewise: **misurata 4,25 Hz**;
Abaqus 4,07 Hz, ANSYS 3,62 Hz, **CalculiX 4,68 Hz (+10,1%, l'unico che
sovrastima)**. Solo Abaqus prevedeva il modo torsionale, e male.
*Investigation and Validation of Numerical Models for Composite Wind Turbine
Blades*, J. Mar. Sci. Eng. 9(5):525, 2021, DOI 10.3390/jmse9050525, open access.

**c) NAFEMS LE11**, confronto CalculiX / ANSYS / Abaqus su
<http://www.bconverged.com/benchmarks/le11.php>, target −105 MPa.
**Caveat: i valori per codice stanno in un'immagine, non nel testo. Non citarli
senza aprire il grafico.**

Non risulta esistere uno studio peer-reviewed dedicato «CalculiX contro Abaqus su
NAFEMS» con tabella di scarti. La fonte b) è la più solida disponibile.

### 1.4 Differenze note rispetto ad Abaqus

**La più importante**, manuale §1, punto 3 delle raccomandazioni, verbatim:

> «USE QUADRATIC ELEMENTS (C3D10, C3D15, C3D20(R), ...) ... For linear elements
> this is not the case: linear elements exhibit all kind of weird behavior such
> as shear locking and volumetric locking. Therefore, most finite element
> programs modify the standard shape functions for linear elements to alleviate
> these problems. However, there is no standard way of doing this, so each vendor
> has created his own modifications without necessarily publishing them. This
> leads to a larger variation in the results if you use linear elements. **Since
> CalculiX uses the standard shape functions for linear elements too, the results
> must be considered with care.**»

Cioè: dove Abaqus applica correzioni proprietarie non pubblicate sugli elementi
lineari, CalculiX non ne applica nessuna. Un C3D4 in CalculiX è il tetraedro a
deformazione costante puro, un punto di integrazione (§6.2.6).

Altre differenze rilevanti ai keyword che il progetto usa:

- **C3D8**: sconsigliato (§6.2.1) per materiale isocoro e per flessione.
  **C3D8I** (§6.2.3), modi incompatibili, «should be used in all instances in
  which linear elements are subject to bending», ma «not very good when subjected
  to torsion». **C3D20R** (§6.2.5) è l'elemento raccomandato in generale.
- **C3D10T** (§6.2.8) non è un rimedio al locking: differisce da C3D10 solo per
  l'interpolazione lineare delle temperature iniziali.
- **`*FREQUENCY`**: le autofrequenze vanno automaticamente nel `.dat` (§5.2).
  §6.9: gli autovalori sono reali, ma positivi solo per matrice di rigidezza
  definita positiva; con precarico si possono avere frequenze immaginarie, cioè
  instabilità. Nel `.dat` finiscono anche fattori di partecipazione, massa modale
  efficace e massa efficace totale per i sei modi rigidi.
- **`*CLOAD` + `*DLOAD` GRAV, e l'uscita RF** — §6.11.5, verbatim:
  «With RF you get the sum of all external forces in a node. ... **selecting RF
  gives you the sum of the reaction forces and the loading forces. This is equal
  to the reaction forces only if the elements belonging to the selected nodes are
  not loaded by a `*DLOAD` card, and the nodes themselves are not loaded by a
  `*CLOAD` card.**» Alternativa documentata: `*SECTION PRINT, SURFACE=..., SOF,
  SOM`.

> Questa è la spiegazione ufficiale dell'anomalia già misurata nel progetto:
> 2,943 N attesi contro 0,73575 N stampati, con nodi vincolati sotto gravità.

### 1.5 Ingressi degeneri — comportamento letto sul sorgente

**Matrice singolare / vincoli insufficienti.** Il manuale non documenta nulla in
merito per il caso strutturale. Sul sorgente:

- `src/spooles.c:225` — se la fattorizzazione restituisce un chevron radice non
  nullo: `fprintf(pfi->msgFile, "\n\n matrix found to be singular\n"); exit(-1);`.
  `msgFile` è aperto a `src/spooles.c:475` su **`spooles.out`**, non su stdout.
  Messaggio in un file laterale, niente su stdout, exit code 255.
- Il pivoting SPOOLES gira con `MAGIC_TAU = 100.0`, `MAGIC_DTOL = 0.0`
  (`spooles.c:52-53`, usati a `:215`). **Una matrice singolare per moto rigido non
  vincolato non è esattamente singolare in aritmetica finita: viene fattorizzata
  lo stesso e produce spostamenti enormi con exit code 0.**
- `src/pardiso.c:306` — la variabile `error` restituita da PARDISO **non viene mai
  testata** (`grep "if(error" pardiso.c` → nessun match).
- Nessun controllo di modi rigidi non vincolati esiste nel sorgente per la
  matrice strutturale: i soli match su WARNING/ERROR sono `equationcheck.f:82`,
  `initialnet.f:469`, `radflowload.c:257,671` — reti e irraggiamento.

> Verificato: un deck senza vincoli sufficienti non è diagnosticato da ccx.
> Nessun `*WARNING`, nessun `*ERROR`, exit 0. La guardia va costruita a valle:
> ampiezza degli spostamenti ed equilibrio delle reazioni.

**Momento su elemento solido.** Comportamento a due facce, letto sul sorgente:

- `src/mafillsmforc.f:39`: `if(ndirforc(i).gt.mi(2)) cycle` — il carico viene
  **scartato in silenzio**. `mi(2)` è «max degree of freedom per node»; per un
  modello solido puramente meccanico vale 3.
- `src/rhsnodef.f:48`: `if(ndirforc(i).gt.3) cycle` — stesso scarto silenzioso sui
  percorsi modale e steady-state dynamics.
- Un `*WARNING` **esiste** — `src/gen3dforc.f:75-85`: «`*WARNING: in gen3dforc:
  node ... does not belong to a beam nor shell element and consequently has no
  rotational degrees of freedom`». Ma `gen3dforc` è chiamata solo da
  `gen3delem.f:484`, dentro `if(inoelfree.ne.0)` aperto a `gen3delem.f:437`, e
  `inoelfree=1` significa (commento a `gen3delem.f:104-105`) «there is at least
  one 1D or 2D element in the structure». **Su una mesh di soli C3D4/C3D10 quel
  warning non viene mai raggiunto.**
- Il manuale documenta i gradi 4-6 solo per nodi di guscio. **Non contiene una
  frase che dica «su solidi vengono ignorati».**

**Codici di uscita.** `src/stop.f`: `call exit(201)`, chiamata da 303 punti.
Nel sorgente 2015 occorrenze di `*ERROR` e 524 di `*WARNING`.
`stopwithout201.f` (exit 0) serve solo il percorso `SOLVER=MATRIXSTORAGE`.
Quindi: **0 = ok, 201 = errore diagnosticato, 255 = singolarità esatta rilevata
da SPOOLES**.

---

## 2. Il tetraedro lineare a 4 nodi

### 2.1 Cosa dice il manuale CalculiX (§6.2.6)

> «The C3D4 is a general purpose tetrahedral element (1 integration point)... This
> element is included for completeness, however, **it is not suited for structural
> calculations unless a lot of them are used (the element is too stiff). Please
> use the 10-node tetrahedral element instead.**»

Su C3D10 (§6.2.7): «The element behaves very well and is a good general purpose
element, although the C3D20R element yields still better results for the same
number of degrees of freedom.»

### 2.2 Cosa dicono i manuali Abaqus ufficiali

*Abaqus Analysis User's Guide*, «Solid (continuum) elements»
(<https://abaqus-docs.mit.edu/2017/English/SIMACAEELMRefMap/simaelm-c-solidcont.htm>):

- «First-order triangles and tetrahedra are usually **overly stiff**, and extremely
  fine meshes are required to obtain accurate results.»
- «The first-order tetrahedral element C3D4 is a constant stress tetrahedron,
  which **should be avoided as much as possible**; the element exhibits slow
  convergence with mesh refinement.»
- «C3D4 is recommended **only for filling in regions of low stress gradient** in
  meshes of C3D8 or C3D8R elements.»
- «Fully integrated first-order triangles and tetrahedra in Abaqus/Standard also
  **exhibit volumetric locking in incompressible problems**.»

*Getting Started with Abaqus*, «Selecting continuum elements»:

- «**You should not use a mesh containing only linear tetrahedral elements (C3D4):
  the results will be inaccurate unless you use an extremely large number of
  elements.**»
- «For tetrahedral element meshes the second-order or the modified tetrahedral
  elements, C3D10 or C3D10M, should be used.»

Motivo strutturale del confronto: **il C3D8 non locca perché usa integrazione
selettivamente ridotta sui termini volumetrici; il C3D4 no.**
Osservazione diretta: **nessun risultato C3D4 compare nelle tabelle di verifica
NAFEMS del manuale Abaqus.**

### 2.3 Quanto sbagliano — numeri pubblicati

**Benzley, Perry, Merkley, Clark, Sjaardama (1995), «A Comparison of All
Hexagonal and All Tetrahedral Finite Element Meshes for Elastic and Elasto-plastic
Analysis», 4th International Meshing Roundtable, pp. 179-191**
(<https://coreform.com/papers/hex_tet_comparison.pdf>). Barra a sezione
rettangolare incastrata, E = 10.000.000, ν = 0,3 e 0,49, soluzione analitica di
riferimento (spostamento 0,000125, tensione flessionale 30,0).
LH/QH = hex lineare/quadratico, LT/QT = tet lineare/quadratico.

Flessione, ν = 0,3:

| DOF | LH spost. | QH spost. | **LT spost.** | QT spost. | LH tens. | **LT tens.** |
|---|---|---|---|---|---|---|
| 567 | 0,72% | | | | 0,00% | |
| 666 | | | **31,48%** | | | **21,23%** |
| 1863 | | 0,24% | | | 0,01% | |
| 3075 | 0,08% | | | | 0,00% | |
| 3615 | | | **10,48%** | | | **21,00%** |
| 3894 | | | | 0,24% | | |

Flessione, ν = 0,49:

| DOF | LH | QH | **LT** | QT | LH tens. | **LT tens.** |
|---|---|---|---|---|---|---|
| 567 | 6,56% | | | | 0,01% | |
| 666 | | | **71,68%** | | | **66,77%** |
| 3075 | 3,20% | | | | 0,01% | |
| 3615 | | | **44,80%** | | | **35,23%** |
| 3894 | | | | 4,80% | | 0,10% |

Torsione, LT, ν = 0,3: 50,81% spostamento / 77,82% tensione a 666 DOF;
22,39% / 38,40% a 3615 DOF.

Conclusione degli autori, verbatim: «The comparison of linear static bending
situation indicated that **LT models produced errors between 10 to 70 percent in
both displacement and stress calculations. Such errors are obviously unacceptable
for stress analysis work.** ... **In all cases, the error was significantly
greater with a nearly incompressible material model (i.e. ν = .49).**»

**Nota che pesa più delle percentuali:** raffinando da 666 a 3615 DOF lo
spostamento migliora (31,48% → 10,48%) ma **la tensione resta ferma a ~21%**.
Raffinare non salva il campo tensionale.

Stessa fonte, Tabella 1: autovalori della matrice di rigidezza di un cubo unitario
modellato con un esaedro contro cinque tetraedri. Sei autovalori nulli in tutti i
casi (i modi rigidi), poi «the Nastran hexahedron always has the lesser and the 5
tetrahedron model always has the greater eigenvalue» — autovalore 7: 1,667 (hex
Nastran) / 1,923 (hex isoparametrico) / **5,315 (5 tet)**; autovalore 21:
11,538 / 11,538 / **38,276**. Prova diretta e misurata dell'eccesso di rigidezza.

**Tadepalli, Erdemir, Cavanagh (2011), «Comparison of hexahedral and tetrahedral
elements in finite element analysis of the foot and footwear», *J Biomech*
44(12):2337-2343, DOI 10.1016/j.jbiomech.2011.05.006** (PMC7458432, open access).
Materiale pienamente incomprimibile, elementi ibridi Abaqus:

| | Hex8 (C3D8H) | Tet4 (C3D4H) | Tet10 (C3D10I) |
|---|---|---|---|
| pressione di picco, 300 N | 439,1 kPa | 466 kPa (+6,1%) | 461,2 kPa (+5,0%) |
| pressione di picco, 700 N + 100 N taglio | 1303 kPa | 1434 kPa (+10,0%) | 1389 kPa (+6,6%) |
| elementi | 33.120 | 106.261 (3,2×) | 39.732 |
| CPU s | 66.555 | 44.032 | 162.973 |

**Cifuentes & Kalbag (1992)**, *Finite Elements in Analysis and Design*
12(3-4):313-318 — tet quadratici ed esaedri equivalenti per accuratezza e tempo
CPU. **Caveat: paywall, letti solo abstract e citazioni di terzi.**

**Schneider, Hu, Gao, Dumas, Zorin, Panozzo (2022), «A Large-Scale Comparison of
Tetrahedral and Hexahedral Elements for Solving Elliptic PDEs with the Finite
Element Method», *ACM Trans. Graph.*, DOI 10.1145/3508372**. Migliaia di
geometrie reali meshate automaticamente: «while **linear tetrahedral elements
perform poorly**, quadratic tetrahedral elements perform equally well or
outperform hexahedral elements». Su elasticità lineare: «trilinear hexahedral
elements outperform linear tetrahedral elements but the quadratic counterparts are
indistinguishable», e «for a given error, P2 discretization is around four times
faster than Q1».

### 2.4 Analisi modale — direzione e ampiezza dell'errore

Benzley et al. 1995, Tabella 4 (stessa barra; riferimento analitico: flessione
317,5 Hz da Hurty & Rubinstein, torsione ≈2614 Hz):

| DOF | LH | QH | **LT** | QT | caso |
|---|---|---|---|---|---|
| 567 | 0,06% | | | | flessione ν=0,3 |
| 666 | | | **20,28%** | | |
| 3615 | | | 0,28% | | |
| 567 | 2,68% | | | | flessione ν=0,49 |
| 666 | | | **75,12%** | | |
| 3615 | | | **23,87%** | | |
| 666 | | | **41,68%** | | torsione ν=0,3 |
| 3615 | | | 0,36% | | |

Commento degli autori: «The linear tetrahedron performs poorly in all cases.»

**Direzione dell'errore — inferita su base teorica, da marcare come tale.**
Benzley riporta moduli, non segni. La direzione segue dalla proprietà di limite
superiore del metodo agli spostamenti: il FEM conforme è un caso particolare di
Ritz-Galerkin, il quoziente di Rayleigh sul sottospazio discreto è maggiore o
uguale al minimo esatto, quindi **le frequenze calcolate sovrastimano quelle
vere**, e un elemento più rigido sovrastima di più. Riferimenti: Strang & Fix,
*An Analysis of the Finite Element Method*, capitolo sugli autovalori; Bathe,
*Finite Element Procedures* §10.2. Corroborazione misurata indipendente: la
Tabella 1 di Benzley (autovalori di rigidezza dei tet sempre maggiori) e il caso
b) di §1.3, dove CalculiX è l'unico dei tre a sovrastimare la prima frequenza
edgewise. **In tesi: dire «sovrastima» citando la teoria, non spacciarlo per una
misura di Benzley.**

### 2.5 Formulazioni migliorate esistono, CalculiX non le ha

- Bonet & Burton (1998), «A simple average nodal pressure tetrahedral element for
  incompressible and nearly incompressible dynamic explicit applications»,
  *Comm. Numer. Meth. Engng* 14(5):437-449.
- Dohrmann, Heinstein, Jung, Key, Witkowski (2000), «Node-based uniform strain
  elements for three-node triangular and four-node tetrahedral meshes»,
  *IJNME* 47(9):1549-1568.
- Puso & Solberg (2006), «A stabilized nodally integrated tetrahedral»,
  *IJNME* 67:841-867 — «overcomes both volumetric and shear locking».
- Taylor, «A Mixed-Enhanced Formulation for Tetrahedral Finite Elements»,
  UC Berkeley, report UCB/SEMM.
- Gee et al. (2009), «A uniform nodal strain tetrahedron with isochoric
  stabilization», *IJNME*, DOI 10.1002/nme.2493.
- Ostien et al. (2016) / Foulk III et al. (2021), tetraedro composito a 10 nodi,
  *IJNME* DOI 10.1002/nme.5218 e 10.1002/nme.6684.

**CalculiX non ne offre nessuna.** Nessun match per «B-bar», «F-bar»,
«selective(ly)» riferito ai tetraedri nel manuale 2.22; le sole mitigazioni sono
integrazione ridotta (C3D8R, C3D20R) e modi incompatibili (C3D8I), tutte su
esaedri. Coerente con il passo di §1.4. Abaqus per contro offre C3D10M e le
varianti ibride H.

---

## 3. Come si dimostra che un deck esportato è corretto

### 3.1 Controlli con appiglio nativo in CalculiX

1. **Equilibrio delle reazioni.** `*NODE PRINT, NSET=<vincolati>, TOTALS=ONLY` con
   `RF` (§5.18). **Attenzione al §6.11.5**: sotto gravità RF non è la sola
   reazione. La strada pulita è `*SECTION PRINT, SURFACE=..., NAME=...` con
   `SOF, SOM`.
2. **Modi rigidi.** In `*FREQUENCY` una struttura non vincolata deve dare **sei**
   autovalori nulli. Un settimo zero, o uno mancante, è un difetto del deck.
3. **Conservazione della massa in modale.** Il `.dat` contiene fattori di
   partecipazione, massa modale efficace e massa efficace totale (§6.9).
   Confronto con ρ·V calcolata dal maglio: controllo a costo zero.
4. **Stima d'errore di discretizzazione.** `*NODE FILE`/`ERR` — stimatore
   Zienkiewicz-Zhu (§6.12.1) e stimatore di gradiente (§6.12.2). Su C3D4 lo ZZ
   misura il salto di tensione fra elementi, che è **esattamente la patologia in
   esame**: indicatore utile, non garanzia.
5. **Regressione contro la suite ufficiale** (§1.1): qualifica il binario, non il
   proprio deck.

### 3.2 Riferimenti pubblicati, non folklore

- **Patch test**: Taylor, R.L., Simo, J.C., Zienkiewicz, O.C., Chan, A.C.H.
  (1986), «The patch test — a condition for assessing FEM convergence»,
  *IJNME* 22:39-62, DOI 10.1002/nme.1620220105.
- **Framework V&V normativo**: ASME **V&V 10-2019 (R2025)**, *Standard for
  Verification and Validation in Computational Solid Mechanics*.
- **Benchmark con soluzione di riferimento**: NAFEMS **R0015** (Abbassian,
  Dawswell, Knowles, 1987, *Selected Benchmarks for Natural Frequency Analysis*,
  ~30 benchmark); NAFEMS **P18** (TNSB Rev.3) — *non* «P09», che non esiste: correzione verificata il 26/08/2026, vedi [`benchmark-nafems.md`](benchmark-nafems.md); serie
  NAFEMS **LE** per elasticità lineare (LE1, LE10, LE11).
- **Soluzioni analitiche per la mensola**: Gere & Timoshenko, *Mechanics of
  Materials* (flessione); Timoshenko & Goodier, *Theory of Elasticity*
  (torsione); Hurty & Rubinstein, *Dynamics of Structures* (frequenza
  flessionale). Sono le tre fonti che Benzley et al. 1995 usano per costruire le
  tabelle di §2.3-2.4: **riusare le stesse rende il confronto diretto.**

### 3.3 Caveat sulle fonti

- Il manuale citato è la 2.22, coerente con il `ccx` in uso. Esiste la 2.23 del
  19/10/2025: verificare che §6.2.6 e §6.11.5 non siano cambiati prima di
  consegnare.
- I numeri di §1.1 sono misurati il 26/08/2026 sull'archivio 2.22, non citati.
- Le righe di sorgente valgono per la 2.22; il codice è stabile da molte versioni,
  il numero di riga no.
- Cifuentes & Kalbag e NAFEMS R0015 sono a pagamento: verificate citazione e tesi
  principale, non le tabelle.
- I valori LE11 per codice non sono stati estratti (stanno in un'immagine).

---

## 4. Verdetto — quanto è difendibile C3D4 in tesi

1. **Difendibile come scelta di pipeline, indifendibile come base di numeri
   tensionali.** Abaqus: «you should not use a mesh containing only linear
   tetrahedral elements». CalculiX: «not suited for structural calculations... too
   stiff. Please use the 10-node tetrahedral element instead.»
2. L'ordine di grandezza dell'errore è pubblicato e citabile: **10-70% su
   spostamento e tensione in flessione**, che sale con ν → 0,5.
3. Su **modale** l'errore misurato è 20-75% a maglio grossolano, ed è una
   **sovrastima** delle frequenze.
4. **CalculiX peggiora il quadro rispetto ad Abaqus**: funzioni di forma standard
   sugli elementi lineari, senza correzioni proprietarie — e lo dichiara.
5. **La suite di verifica ufficiale di CalculiX non contiene un solo deck C3D4.**
6. Come si difende comunque: dichiarare C3D4 come elemento di *fattibilità
   geometrica*, non di accuratezza, e portare un confronto C3D4 contro C3D10 sullo
   stesso maglio, misurato, che quantifichi lo scarto sul proprio caso.
7. Il passaggio a C3D10 costa un giro di nodi di mezzeria, non una
   riprogettazione: TetGen produce già i vertici.
8. **Test disponibili gratis**: la suite ufficiale, 610 deck con soglia 0,1%.
   Qualifica il binario, non il deck.
9. In più, ricostruibili in casa: mensola (Gere-Timoshenko), torsione
   (Timoshenko-Goodier), frequenza (Hurty-Rubinstein) — le tre di Benzley, che
   danno anche le tabelle di confronto già pubblicate.
10. Per il deck generato: somma reazioni contro somma carichi via
    `*SECTION PRINT/SOF,SOM` (non RF sotto gravità), sei modi rigidi nulli, massa
    efficace totale contro ρV, **e una guardia sull'ampiezza degli spostamenti**,
    perché ccx su deck non vincolato esce 0, senza warning, con il messaggio di
    singolarità sepolto in `spooles.out` — quando lo emette.
