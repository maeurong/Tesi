# Benchmark NAFEMS — geometrie quotate, vincoli, target e fonti

Data: 2026-08-26. Raccolta: agente `researcher` (sola lettura), ticket
[#42](https://github.com/maeurong/Tesi/issues/42) della mappa
[#33](https://github.com/maeurong/Tesi/issues/33). Repo `Tesi`, branch `main`, HEAD `a07071a`.

Scopo: fornire tutto ciò che serve a **costruire i deck** LE1, LE2, LE10, LE11, FV32, FV52
senza aprire le pubblicazioni NAFEMS a pagamento. Sostituisce e completa il §2 di
[`ricerca-vv-standard.md`](ricerca-vv-standard.md), che aveva già i valori target ma non le quote.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte in questa sessione (pagina/PDF/file scaricato).
- **[V-sec]** = verificato su fonte secondaria affidabile (manuale ufficiale di un solutore).
- **[INF]** = inferenza mia, non letta su fonte. Da non citare come fatto.
- **[NON TROVATO]** = non trovato pubblicato in chiaro. Non inventato.

## Premessa corretta rispetto al ticket

Il ticket dice «le figure non erano estraibili». **Falso in senso operativo, e non blocca
nulla**: le figure sono estraibili e leggibili rasterizzando i PDF (`pdftoppm`) e scaricando
le GIF originali dalle riproduzioni ufficiali. Tutte le quote di questo documento vengono
da figure lette così, e sono state **incrociate con i coordinate dei nodi** dei deck Abaqus
pubblicati, che sono scaricabili in chiaro. Nessuna quota è inferita.

Seconda correzione: `ricerca-vv-standard.md:873` attribuisce FV52 ad Abbassian et al. 1987.
Abaqus lo attribuisce a **TNSB Rev. 3 (ottobre 1990)**, non al 1987. Vedi §7.

---

## 0. Le cinque fonti che portano il carico

| # | fonte | cosa dà | stato |
|---|---|---|---|
| F1 | **Caesar Systems**, riproduzione delle schede NAFEMS originali — <http://www.caesarsystems.co.uk/NAFEMS_benchmarks/standardbm.html> | scheda una-pagina *verbatim* per LE1…LE11: origine, data/issue, geometria quotata, carichi, vincoli, materiale, mesh, TARGET **con il qualificatore del target**. Più i file **STEP forniti da NAFEMS** | [V] |
| F2 | **Deck Abaqus `.inp` pubblici** — `https://abaqus-docs.mit.edu/2017/English/SIMAINPRefResources/<nome>.inp` | coordinate nodali esatte, vincoli DOF per DOF, carichi, materiale. È la quota **numerica** dietro le figure | [V] |
| F3 | **Abaqus Benchmarks Guide** (mirror MIT) — <https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-m-NAFEMSBenchmarks-sb.htm> | testo del problema, figure quotate, **tabelle di errore per tipo di elemento** | [V] |
| F3b | mirror indipendente della stessa guida (v2016), Univ. Colorado — <https://ceae-server.colorado.edu/v2016/books/bmk/ch04s04anf25.html> | conferma indipendente della tabella FV52 | [V] |
| F4 | **ESRD**, *Benchmarks Guide — The Standard NAFEMS Benchmarks: Linear Elastic Tests* (2018) — <https://www.esrd.com/wp-content/uploads/dlm_uploads/Benchmarks-Guide-Standard-NAFEMS-Benchmarks-Linear-Elastic-Tests.pdf> | figure quotate ridisegnate su licenza, per LE1/LE2/LE10/LE11 | [V] |
| F5 | **Altair OptiStruct** OS-V 0455 (FV52) — <https://help.altair.com/hwsolvers/os/topics/solvers/os/simply_supported_soid_square_plate_fv52_r.htm> e OS-V 0060 (LE10) | il **secondo set** di target FV52, esplicitamente etichettato «closed form solution» | [V] |

Fonti di appoggio: seamplex/FeenoX (LE10 in Gmsh, sorgente aperto)
<https://www.seamplex.com/fino/cases/012-nafems-le10/> [V];
SimScale/Code_Aster LE10 <https://www.simscale.com/docs/validation-cases/thick-plate-under-pressure/> [V];
bConverged (distributore CalculiX) <http://www.bconverged.com/benchmarks/le10.php> [V];
TechSoft3D HOOPS Solve <https://docs.techsoft3d.com/hoops/mesh/_static/benchmark_reports/benchmark_results_2.13.0.pdf> [V].

**Nota su F1.** Le schede Caesar Systems riportano `ORIGIN: NAFEMS report LSB2` (LE10, LE11),
`C1` (LE1), `TSBM` (LE2) e la data/issue di ciascuna scheda. Sono la riproduzione più vicina
all'originale che ho trovato in chiaro, e includono i file STEP **firmati NAFEMS**
(`FILE_NAME('le10abrp_v2.stp','2001-02-12',('R. Goult'),...)`), scaricati e verificati
integri in questa sessione: `le1abrep_v2.stp` 9754 B, `le10abrep_v2.stp` 9605 B,
`le11abrep_v3.stp` 13578 B, `le10fine.stp` 83023 B (AP209: mesh + carichi + vincoli + target). [V]

---

## 1. LE1 — Elliptic membrane (stato piano di tensione)

**Non serve al nostro esportatore 3D.** È 2D. Lo documento perché è la stessa pianta di LE10 e
perché serve come prova di sanità del generatore di geometria. [INF, sul «non serve»]

| voce | valore | fonte |
|---|---|---|
| origine scheda | NAFEMS report C1, Test LE1, data/issue 1986-07-01/1 | F1 `le1.html` [V] |
| tipo | piano di tensione (plane stress) | F1 [V] |
| ellisse interna AD | (x/2)² + y² = 1 | F4 p. 4 (fig.), F1 `le1_1.gif` [V] |
| ellisse esterna BC | (x/3,25)² + (y/2,75)² = 1 | idem [V] |
| punti | A = (0, 1), B = (0, 2,75), C = (3,25, 0), D = (2, 0) — tutto in metri | F4 fig. + deck `nle1xf8c.inp` nodi 1, 4001, 4801, 801 [V, incrociato] |
| quote a margine | OA = 1,0 m, AB = 1,75 m, OD = 2,0 m, DC = 1,25 m | F4 p. 4 [V] |
| spessore | T = 0,1 m | F4 («T=0.1 m» in figura) + F1 («thickness 0.1») + deck `*SOLID SECTION … 0.1` [V, tre fonti] |
| materiale | E = 210 · 10³ MPa = 210 GPa, ν = 0,3 | F1, F4, deck [V] |
| vincoli | AB: simmetria attorno all'asse y → u_x = 0. DC: simmetria attorno all'asse x → u_y = 0 | F1 (verbatim) [V] |
| carico | pressione uniforme **uscente** di 10 MPa sul bordo esterno BC. Bordo interno AD scarico | F1 (verbatim) [V] |
| lettura | tensione tangenziale di bordo σ_yy nel punto **D** = (2, 0) | F1, F4 [V] |
| **target** | **92,7 MPa** (nessun qualificatore sulla scheda) | F1 `TARGET 92.7 MPa` [V] |

**Verdetto: ricostruibile.** Geometria, vincoli, carico e target completi su due fonti indipendenti.

---

## 2. LE2 — Cylindrical shell bending patch test

**Non serve al nostro esportatore 3D.** È un test di **gusci** (`Quadrilateral shells` nella
scheda NAFEMS). Un esportatore di solidi non lo può eseguire senza cambiare formulazione. [V — il
tipo di elemento è dichiarato nella scheda]

| voce | valore | fonte |
|---|---|---|
| origine scheda | NAFEMS report TSBM, Test LE2, data/issue 1986-11-21/2 | F1 `le2.html` [V] |
| geometria | settore θ = 30° di guscio cilindrico, **spessore 0,01 m** | F1, F4 («T = 10 mm») [V] |
| raggio e lunghezza | R = 1,0 m, z ∈ [0, 0,5] m | deck `nle2x58c.inp`: `*NMAP TYPE=CYLINDRICAL` con nodi (r=1,0, θ=0…30°, z=0…0,5) [V] |
| materiale | E = 210 · 10³ MPa, ν = 0,3 | F1 [V] |
| vincoli | bordo AB: tutte le traslazioni e rotazioni nulle (incastro). Bordi AD e BC: simmetria attorno al piano r-θ (traslazione z e rotazioni normali nulle) | F1 (verbatim) [V] |
| carico, caso 1 | momento normale uniforme di **1,0 kN·m/m** sul bordo DC | F1 [V] |
| carico, caso 2 | pressione normale uscente 0,6 MPa sulla superficie media ABCD + pressione tangenziale uscente 60,0 MPa sul bordo DC | F1 [V] |
| lettura | tensione tangenziale (θ-θ) sulla superficie esterna (convessa) nel punto **E** | F1 [V] |
| **target** | **60,0 MPa, per entrambi i casi** | F1 [V] |

**[NON TROVATO]**: la posizione esatta del punto E sulla scheda è nella figura, che non ho
letto per LE2 (non serve al nostro caso). Il deck Abaqus stampa su tutti gli elementi.

**Verdetto: ricostruibile come guscio, non applicabile al nostro esportatore di solidi.**

---

## 3. LE10 — Thick plate under pressure ← **il benchmark statico per solidi 3D**

### Geometria

Quarto di piastra spessa a pianta ellittica anulare, estruso in z.

| voce | valore | fonte |
|---|---|---|
| origine scheda | NAFEMS report **LSB2**, Test LE10, data/issue **1990-06-15/2** | F1 `le10.html` [V] |
| ellisse interna AD | **(x/2)² + y² = 1** | F1 `le10_1.gif` (figura originale) + F4 p. 29 [V, due fonti] |
| ellisse esterna BC | **(x/3,25)² + (y/2,75)² = 1** | idem [V] |
| quote a margine | OA = 1,0 m, AB = 1,75 m, OD = 2,0 m, DC = 1,25 m | F1 `le10_1.gif`, F4 p. 29 [V] |
| **spessore** | **0,6 m** | F1 (`thickness 0.6`) + F1 `le10_2.gif` + F4 p. 29 [V] |
| convenzione lettere | **senza apice = superficie superiore** (quella caricata); **con apice = superficie inferiore** | F1 `le10_2.gif`: le frecce di pressione entrano nella faccia ABCD, e A′B′C′D′ stanno sotto [V] |
| coordinate dei vertici (origine sulla faccia **inferiore**) | A (0, 1, 0,6) · B (0, 2,75, 0,6) · C (3,25, 0, 0,6) · D (2, 0, 0,6) · A′ (0, 1, 0) · B′ (0, 2,75, 0) · C′ (3,25, 0, 0) · D′ (2, 0, 0) | SimScale, Tab. 1 [V]; concorde con seamplex, che scrive `D = (2 m, 0 m, 0.6 m)` [V]; concorde con il deck `nle10fkc.inp` (5 strati a z = 0, 0,15, 0,30, 0,45, 0,60) [V] |
| B″, C″ | punti medi degli spigoli BB′ e CC′, cioè z = 0,3 | SimScale [V]; Abaqus li chiama E, E′ [V] |

Tutte le dimensioni in **metri**. Il deck seamplex usa millimetri (a = 1000, b = 2750,
c = 3250, d = 2000, h = 600): stesso corpo, unità diverse.

### Vincoli — formulazione NAFEMS verbatim

> Face DCD′C′ zero y-displacement. Face ABA′B′ zero x-displacement. Face BCB′C′ x and y
> displacements fixed, z displacements fixed along mid-plane.
> — F1 `le10.html` [V]

In termini operativi:
- faccia DCD′C′ (il piano y = 0): **u_y = 0**
- faccia ABA′B′ (il piano x = 0): **u_x = 0**
- faccia esterna BCB′C′ (l'ellisse grande estrusa): **u_x = u_y = 0**
- **solo lo spigolo di mezzeria** B″C″ di quella faccia (z = 0,3): **u_z = 0**

Abaqus scrive lo stesso vincolo come «u_z = 0 on line EE′ (E midpoint of edge CC′, E′ midpoint
of BB′)» [V]. Il deck lo realizza con `*BOUNDARY / MID,3` dove `MID` è la riga di nodi a z = 0,30
sull'ellisse esterna [V].

> **Trappola nota.** ESRD annota: *«Since constraints along a line are incompatible with
> 3D-elasticity, the StressCheck results were obtained by fixing the z-displacement of the face
> BCB′C′»* (F4 p. 31) [V]. Chi vincola tutta la faccia invece della sola linea **non sta più
> risolvendo LE10**. Se il nostro deck lo fa, va dichiarato.

### Materiale e carico

- E = 210 · 10³ MPa = **210 GPa**, ν = **0,3**. F1, F3, F4 [V].
- Densità **7800 kg/m³** — la aggiunge solo Abaqus (serve a Abaqus/Explicit), **non è nella
  scheda NAFEMS** e non serve all'analisi statica. F3 [V].
- Carico: **pressione normale uniforme di 1,0 MPa sulla superficie superiore** (la faccia ABCD).
  F1, F3, F4 [V]. Nel deck: `*DLOAD / LOAD,P2, 1.0E6` sugli elementi dello strato superiore [V].

### Punto di lettura e target

- **Punto D = (2, 0, 0,6)**, cioè lo spigolo interno **sulla superficie caricata**.
  bConverged lo chiama «the inside top corner» [V]; seamplex scrive esplicitamente
  `sigmay(2000,0,600)` [V]; SimScale Tab. 1 mette D a z = 0,6 [V]. Tre fonti concordi.
- **Target: σ_yy = −5,38 MPa**, e la scheda NAFEMS lo qualifica **«(mesh refinement)»**:
  è un target **numerico**, non una soluzione chiusa. F1 [V]. SimScale lo conferma a parole:
  *«The reference solution … is of the numerical type»* [V].
- Il segno: la scheda NAFEMS e ESRD scrivono −5,38; Abaqus scrive «5.38 MPa» nel testo ma
  −6,72/−5,64 ecc. in tabella. È compressione. [V]

### Mesh prescritte dalla scheda

Coarse **3 × 2 × 2**, fine **6 × 4 × 2** («approx. halving of coarse mesh — in plane»),
solo nodi d'angolo dati. Tipi ammessi: **solid hexahedra, wedges and tetrahedra**. F1 [V].

### Tabelle di errore per tipo di elemento

**Abaqus/Standard** (F3, mirror MIT, sezione LE10) — σ_yy in D, differenza percentuale rispetto
a −5,38 MPa fra parentesi: [V]

| elemento | mesh coarse | mesh fine |
|---|---|---|
| C3D20 | −6,72 MPa (+25,00%) | −5,64 MPa (+4,83%) |
| C3D20R | −7,93 MPa (+47,39%) | −5,53 MPa (+2,78%) |
| **C3D10** | **−5,44 MPa (+1,15%)** | **−5,77 MPa (+7,24%)** |
| C3D10HS | −5,08 MPa (−3,72%) | −5,51 MPa (+2,42%) |
| **C3D10M** | **−5,57 MPa (+3,53%)** | **−5,89 MPa (+9,48%)** |

**Spiegazione ufficiale del non-monotono**, che vale la pena citare in tesi perché smonta
l'uso ingenuo di LE10 come studio di convergenza:

> *«The C3D10 and C3D10M elements are more accurate with the coarse mesh than with the fine mesh:
> in the coarse meshes four elements come together at the point of interest, giving a more accurate
> result after averaging to the nodes. In the more refined mesh, only one element contains the point
> of interest; therefore, the extrapolation to the nodes is less accurate.»* — F3 [V]

Cioè l'errore non è dell'elemento: è dell'**estrapolazione ai nodi in un punto d'angolo**.
Il §2.2 di `ricerca-vv-standard.md:275-279` lo aveva inferito; ora è confermato dal produttore. [V]

**Tetraedri lineari — il buco è colmato.** Abaqus non pubblica risultati C3D4 su LE10 [V, confermato].
Ma **SimScale** li pubblica, su Code_Aster: [V]

| caso SimScale | mesh | σ_yy in D | errore |
|---|---|---|---|
| A | **tetraedri di 1° ordine**, 63 381 nodi | 5,08010 MPa | **−5,57%** |
| B | tetraedri di 2° ordine, 476 858 nodi | 5,34163 MPa | −0,71% |
| C | hex/quad 1° ordine, 216 nodi | 3,79913 MPa | −29,38% |
| D | hex/quad 2° ordine, 389 nodi | 5,30337 MPa | −1,42% |
| G | hex/quad 2° ordine, 184 594 nodi | 5,35033 MPa | −0,55% |

Il caso C (esaedri lineari, mesh minima) sbaglia del **29%**: è il promemoria che il problema
è il grado dell'elemento e la fittezza, non solo la forma. [V per i numeri]

**Verdetto: ricostruibile, completamente, e con termine di paragone per tetraedri sia lineari
(SimScale) sia quadratici (Abaqus).** È il benchmark statico da adottare.

---

## 4. LE11 — Solid cylinder / taper / sphere, carico termico

### Geometria — settore di 90°, tutte le quote in metri

Corpo di rivoluzione: sfera alla base, raccordo tronco-conico, cilindro in cima. Si modella
**un quarto** (90°) sfruttando le due simmetrie.

Profilo nel piano meridiano (r, z), **z = asse di rivoluzione, z = 0 alla base**:

| curva | descrizione | quote | fonte |
|---|---|---|---|
| superficie **interna** bassa | arco di **sfera di raggio 1,0** da (r=1,0, z=0) fino a 45°, cioè fino a (0,7071, 0,7071) | R = 1,0, angolo 45° | F1 `le11_1.gif` + F4 p. 32 [V]; deck `nle11fkc.inp` nodi 1 = (1, 0, 0) e 13 = (0,7071, 0, 0,7071) [V] |
| superficie **interna** alta | cilindro di raggio **0,7071** da z = 0,7071 a z = **1,79** | 0,7071 | F1, F4, deck (nodo 21 = 0,7071, 0, 1,79) [V] |
| superficie **esterna** bassa | arco di **sfera di raggio 1,4** da (1,4, 0) a (1,2124, 0,7) | R = 1,4 | F1 fig., deck nodi 401 = (1,4, 0, 0), 409 = (1,2124, 0, 0,7) [V] |
| superficie **esterna**, raccordo | segmenti rettilinei (1,2124, 0,700) → (1,1062, 1,045) → (1,0, 1,390) | due tratti da **0,345** ciascuno | F1 fig. (0,345 + 0,345) + deck nodi 413, 417 [V, incrociato] |
| superficie **esterna** alta | cilindro di raggio **1,0** da z = 1,390 a z = **1,790** | tratto da **0,400** | F1 fig. + deck nodo 421 = (1,0, 0, 1,79) [V] |

Somma verticale della figura: 0,700 + 0,345 + 0,345 + 0,400 = **1,790** — coincide con la
quota z massima del deck Abaqus. Le due fonti si chiudono. [V]

Larghezze in cima: 0,7071 (interno) + 0,2929 (spessore) = **1,0** (esterno). Alla base:
1,0 (interno) + 0,4 (spessore) = **1,4** (esterno). F1 `le11_1.gif`, F4 p. 32 [V].

Estensione angolare: **90°**. F4 p. 32 (annotazione «90 degrees» fra E e D) [V]; il deck la
genera con `*NCOPY … MULTIPLE=12 … 7.5` = 12 × 7,5° = 90° [V].

**Attenzione agli assi.** ESRD (F4) ruota il modello: nel loro disegno l'asse di rivoluzione è
**y**, la temperatura è Δθ = √(x² + z²) + y e il target è σ_y. NAFEMS e Abaqus usano l'asse **z**.
Stesso corpo, stessi numeri, terna diversa. Usare la terna NAFEMS. [V]

### Vincoli — formulazione NAFEMS verbatim

> Symmetry on xz-plane, i.e. zero y-displacement. Symmetry on yz-plane, i.e. zero x-displacement.
> Face on xy-plane: zero z-displacement. Face HIH′I′: zero z-displacement.
> — F1 `le11.html` [V]

Cioè: u_y = 0 sul piano y = 0; u_x = 0 sul piano x = 0; u_z = 0 sulla faccia di base z = 0;
u_z = 0 anche sulla **faccia superiore HIH′I′** (z = 1,79). Abaqus dice esattamente lo stesso [V].
Il deck lo realizza con i set `XZPLANE,2` / `YZPLANE,1` / `XYPLANE,3` / `HI,3` [V].

> ESRD nomina la faccia superiore **BCDE** invece di HIH′I′ perché ha ruotato la terna. Non sono
> due specifiche diverse. La nomenclatura da usare è quella NAFEMS: la figura originale
> (`le11_2.gif`) etichetta A, B, C, D, E, F, G, H, I dal basso verso l'alto, e i primi (A′, B′, …)
> sull'altro piano di simmetria. **A sta in basso, sulla superficie interna, sul piano z = 0.** [V]

### Materiale e carico

- E = **210 GPa** (210 · 10³ MPa), ν = **0,3**, α = **2,3 · 10⁻⁴ /°C**. F1, F3, F4 [V].
- Nessuna densità: è un problema statico termo-elastico. [V]
- Carico: **campo di temperatura imposto**, gradiente lineare radiale e assiale
  **Δθ [°C] = √(x² + y²) + z**. F1 (verbatim), F3 [V].
  Abaqus lo impone con la subroutine utente `UTEMP` [V]; in un deck CalculiX si impone
  nodo per nodo con `*TEMPERATURE` calcolando il valore dalle coordinate. [INF — la via
  CalculiX è mia, la formula è verificata]
- **[NON TROVATO]** La temperatura di riferimento (stato scarico) non è dichiarata
  esplicitamente né sulla scheda né in Abaqus. Δθ è già un *incremento*: l'assunzione naturale
  è T_ref = 0. Non l'ho letta scritta.

### Punto di lettura e target

- **Punto A**: base del corpo (z = 0), sulla **superficie interna** (r = 1,0), su un piano di
  simmetria. Nel deck Abaqus è il nodo 1 = (1,0, 0, 0). F1 `le11_1.gif` + deck [V, incrociato].
- **Target: σ_zz = −105 MPa**, qualificato dalla scheda NAFEMS come **«(refined axisymmetric)»**
  — anche questo è un target **numerico**, ottenuto con un modello assialsimmetrico raffinato.
  F1 [V]. ESRD e Abaqus riportano lo stesso valore [V].

### Mesh prescritte dalla scheda

Coarse **5 × 1 × 3**, fine **10 × 2 × 3**. Tipi ammessi: solid hexahedra, wedges, tetrahedra. F1 [V].

### Tabelle di errore per tipo di elemento

**Abaqus/Standard** (F3, sezione LE11) — σ_zz in A: [V]

| elemento | mesh coarse | mesh fine |
|---|---|---|
| C3D20 | −96,71 MPa (−7,9%) | −103,26 MPa (−1,7%) |
| C3D20R | −93,04 MPa (−11,4%) | −99,60 MPa (−5,1%) |

> **[NON TROVATO] — e questo è il buco che conta.** Abaqus **non** pubblica LE11 per C3D10,
> C3D10M, C3D10HS né C3D4: la riga «Elements tested» della pagina LE11 elenca **solo C3D20 e
> C3D20R**. [V — verificato sulla pagina] Per LE11 **non esiste un termine di paragone Abaqus
> per tetraedri**, di nessun grado.

Surrogati disponibili, da altre fonti:

| fonte | elemento | σ_zz in A | errore |
|---|---|---|---|
| ESRD/StressCheck, F4 p. 33 | hexa p-version, 8 elementi | −105,2 MPa | 0,19% |
| ESRD/StressCheck, F4 p. 33 | hexa p-version, 216 elementi | −105,4 MPa | 0,38% |
| ESRD/StressCheck, F4 p. 33 | **tetra p-version, 317 elementi** | −105,5 MPa | 0,48% |
| ESRD/StressCheck, F4 p. 33 | **tetra p-version, 3531 elementi** | −105,4 MPa | 0,38% |
| TechSoft3D | HOOPS Solve | −93,47 MPa | −11,0% |
| TechSoft3D | MSC Nastran | −99,48 MPa | −5,3% |

Gli elementi ESRD sono **p-version StressCheck**, non tetraedri quadratici standard: non sono
un paragone diretto per C3D10. Vanno citati come tali. [V per i numeri, [INF] per il caveat]

**Verdetto: ricostruibile** (geometria, vincoli, carico, target completi e incrociati su tre
fonti). **Ma senza tabella Abaqus per tetraedri**: se serve un confronto per tipo di elemento,
LE10 lo dà e LE11 no.

---

## 5. FV32 — Cantilevered tapered membrane (analisi modale)

**È 2D** (membrana in stato piano). Non verifica un esportatore di solidi. Documentato perché
il ticket lo chiede e perché è il test modale su mesh distorta.

| voce | valore | fonte |
|---|---|---|
| pubblicazione | NAFEMS TNSB Rev. 3 (1990) secondo Abaqus; NAFEMS R0015 (1987) Test FV32 secondo TechSoft3D | F3, TechSoft3D [V] — vedi §7 |
| geometria | mensola rastremata: **lunghezza 10,0 m**; altezza **5,0 m** all'incastro (y ∈ [−2,5, +2,5]); altezza **1,0 m** all'estremo libero (y ∈ [−0,5, +0,5]) | figura Abaqus `bmkfv32.png` (quote 2,5 m, 1,0 m, 10,0 m) [V] + deck `nfv32f8c.inp` nodi (0,−2,5) (10,−0,5) (0,2,5) (10,0,5) [V, incrociato] |
| spessore | **0,05 m** | F3 testo («Plate thickness = 0.05 m») [V]. Irrilevante per le frequenze: massa e rigidezza scalano entrambe con t [INF] |
| materiale | E = **200 GPa**, ν = **0,3**, ρ = **8000 kg/m³** | F3, TechSoft3D [V, due fonti] |
| vincoli | **u_x = u_y = 0 lungo l'asse y** (il bordo incastrato x = 0); **u_z = 0 su tutti i nodi** | F3 e TechSoft3D, formulazione identica [V, due fonti] |
| carico | nessuno: analisi modale libera | [V] |
| lettura | prime 6 frequenze proprie | [V] |

**Target (Hz), modi 1–6:** [V su due fonti indipendenti che coincidono cifra per cifra]

| modo | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| NAFEMS | **44,623** | **130,03** | **162,70** | **246,05** | **379,90** | **391,44** |

Abaqus (F3) e TechSoft3D (colonna «Theory») danno **gli stessi identici valori**. Questo è
significativo per il §7: su FV32 i due set di target NAFEMS coincidono, o le due fonti hanno
scelto lo stesso. Su FV52 no.

Tabella di errore Abaqus, modo 1 / modo 4: [V]

| elemento | modo 1 | modo 2 | modo 3 | modo 4 | modo 5 | modo 6 |
|---|---|---|---|---|---|---|
| CPS4 | 44,782 (0,36) | 130,63 (0,46) | 162,59 (−0,07) | 246,79 (0,30) | 379,14 (−0,20) | 389,83 (−0,41) |
| CPS4I | 44,524 (−0,23) | 129,55 (−0,09) | 162,55 (−0,09) | 244,13 (−0,78) | 374,46 (−1,43) | 389,60 (−0,47) |
| CPS8 | 44,636 (0,04) | 130,14 (0,08) | 162,72 (0,01) | 246,63 (0,24) | 382,02 (0,56) | 391,55 (0,03) |
| CPS8R | 44,629 (0,02) | 130,11 (0,06) | 162,70 (0,00) | 246,42 (0,15) | 381,32 (0,37) | 391,51 (0,02) |
| CPS6 | 44,624 (0,00) | 130,04 (0,00) | 162,70 (0,00) | 246,09 (0,02) | 379,99 (0,02) | 391,45 (0,02) |
| CPS6M | 44,637 (0,03) | 129,88 (−0,12) | 162,67 (−0,02) | 245,29 (−0,31) | 377,64 (−0,59) | 390,98 (−0,12) |

**Verdetto: ricostruibile, ma 2D.** Se serve un test modale che eserciti l'esportatore di
solidi, è **FV52**, non FV32.

---

## 6. FV52 — Simply supported "solid" square plate ← **il benchmark modale per solidi 3D**

| voce | valore | fonte |
|---|---|---|
| numero corretto | **FV52** | NAFEMS Publications Guide, sezione Dynamics: *«3D solid elements: … simply supported solid square plate (52)»* <https://www.nafems.org/publications/pubguide/benchmarks/Page5/> [V] — è NAFEMS stessa. Confermato da Abaqus, Altair e Caesar Systems [V] |
| geometria | piastra quadrata **10,0 m × 10,0 m**, spessore **1,0 m** | figura Abaqus `bmkfv52.png` (tre quote: 10,0 m, 10,0 m, 1,0 m) [V] + deck `nfv52i8f.inp`, nodi da (0,0,−0,5) a (10,10,+0,5) [V, incrociato] |
| sistema di riferimento | **piano medio a z = 0**; superficie inferiore z = **−0,5**, superiore z = **+0,5**; x, y ∈ [0, 10] | deck [V] |
| materiale | E = **200 GPa**, ν = **0,3**, ρ = **8000 kg/m³** | F3, Altair, TechSoft3D [V, tre fonti] |
| **vincoli** | **u_z = 0 lungo i quattro spigoli sul piano z = −0,5**, e nient'altro | F3 (verbatim) [V]; TechSoft3D lo scrive identico: *«Z = 0 along the 4 edges on the plane Z = −0.5m»* [V] |
| carico | nessuno: analisi modale libera | [V] |
| modi 1–3 | **moti rigidi (RBM)**, frequenza nulla. Il vincolo è *cinematicamente incompleto* per costruzione: nessun grado in x e y è bloccato | F3 [V]; TechSoft3D lo dichiara: *«Kinematically incomplete suppressions»* [V] |
| mesh usate | **8 × 8 × 3** con esaedri a 8 nodi; **4 × 4 × 1** con esaedri a 20 nodi | Altair OS-V 0455 [V]; il deck `nfv52i8f.inp` genera esattamente 8 × 8 × 3 [V] |
| lettura | frequenze dei modi **4–10** | [V] |

> **Errore di stampa in Altair.** OS-V 0455 scrive «constrained at **Z = −5 m** plane». Il deck
> Abaqus, il testo Abaqus e TechSoft3D dicono tutti **z = −0,5 m**, coerente con spessore 1,0 m.
> È un refuso Altair. [V per la discordanza, [INF] per l'attribuzione a refuso]

### I due set di target — vedi §7 per lo scioglimento

**Set «numerico»** — quello che Abaqus chiama semplicemente `NAFEMS` (Hz): [V, due mirror indipendenti]

| modo | 1–3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| | RBM | **44,092** | **106,66** | **106,66** | **156,23** | **193,58** | **200,13** | **200,13** |

**Set «closed form»** — quello che Altair etichetta esplicitamente `f* = Closed form solution`
e che TechSoft3D chiama `Theory` (Hz): [V, due fonti indipendenti che coincidono]

| modo | 1–3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| | RBM | **45,897** | **109,44** | **109,44** | **167,89** | **193,59** | **206,19** | **206,19** |

### Tabella di errore per tipo di elemento (Abaqus, contro il set numerico)

[V, verificato su due mirror: MIT 2017 e Colorado 2016 — identici]

| elemento | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|
| C3D8I | 44,092 (0,0) | 106,66 (0,0) | 106,66 (0,0) | 156,23 (0,0) | 193,58 (0,0) | 200,13 (0,0) | 200,13 (0,0) |
| **C3D10** | **44,348 (0,58)** | 107,73 (1,00) | 107,73 (1,00) | **163,58 (4,70)** | 193,63 (0,02) | 204,74 (2,30) | 205,10 (2,48) |
| C3D10HS | 44,348 (0,58) | 107,73 (1,00) | 107,73 (1,00) | 163,58 (4,70) | 193,63 (0,02) | 204,74 (2,30) | 205,10 (2,48) |
| **C3D10M** | **42,687 (−3,19)** | 101,57 (−4,77) | 101,57 (−4,77) | **151,22 (−3,21)** | 192,89 (−0,35) | 203,76 (1,81) | 203,76 (1,81) |
| C3D20 | 44,796 (1,60) | 110,54 (3,64) | 110,54 (3,64) | 169,10 (8,24) | 193,92 (0,18) | 206,64 (3,25) | 206,64 (3,25) |

> **Avvertenza di Abaqus, da non perdere:** *«Element types C3D10, C3D10M, and C3D20 capture the
> same eigenmodes, but the order of eigenmodes 8 through 12 is different. For example, the same
> mode is captured as mode 12 by C3D10, as mode 11 by C3D10M, and as mode 9 by C3D20.»* [V]
> Confrontare le frequenze **per indice di modo** oltre il modo 7 è sbagliato: vanno appaiate
> per forma modale. Questo vincola il nostro confronto automatico. [V per la citazione]

**[NON TROVATO]:** nessun risultato **C3D4** pubblicato su FV52, in nessuna delle fonti consultate. [V]

**Verdetto: ricostruibile, completamente.** È il benchmark modale da adottare per i solidi 3D,
ed è **l'unico dei cinque che dia una tabella d'errore Abaqus per tetraedri quadratici in
analisi modale**.

---

## 7. La discrepanza FV52 / FV51 — **sciolta**

Il ticket la pone come «da sciogliere sul documento originale». Non ho aperto R0015 (a pagamento),
ma la questione si chiude comunque, su tre pilastri, **tutti su fonte**.

### 7.1 Il numero corretto è FV52. «FV51» è un errore di TechSoft3D.

NAFEMS pubblica in chiaro l'elenco numerato dei propri benchmark di dinamica: [V]

> **3D solid elements:** deep simply supported solid beam **(51)** · simply supported solid square
> plate **(52)** · simply supported solid annular plate with axisymmetric vibration (53)
> — <https://www.nafems.org/publications/pubguide/benchmarks/Page5/>

Quindi **51 = trave**, **52 = piastra quadrata**. TechSoft3D intitola la propria sezione
«Simply Supported Solid Square Plate» ma la referenzia come «Test No. FV51» — sta citando il
numero della trave per il test della piastra. Errore di un numero. [V]

Conferme incrociate: Abaqus indicizza «FV52: Simply supported "solid" square plate» [V];
Caesar Systems, nell'elenco dei Standard Benchmarks, ha «FV52 — Simply supported `solid` square
plate» [V]; Altair intitola «Test No. FV52» [V]. Tre a uno.

### 7.2 I due valori sono **due set di target diversi della stessa pubblicazione**. Ipotesi confermata.

La pagina prodotto di NAFEMS per R0015 lo dice testualmente: [V — è NAFEMS stessa, non un terzo]

> *«Full details of each test are given in a standard one-page format, comprising geometrical
> arrangements, boundary conditions, **two sets of 'target' frequencies (theoretical or numerical)**
> and a schematic presentation of mode shapes.»*
> — <https://www.nafems.org/publications/resource_center/r0015/>

E **Altair etichetta esplicitamente** la colonna 45,897 / 109,44 / 167,89 / 193,59 / 206,19 come
`f*` = **«Closed form solution»** [V]. TechSoft3D usa la stessa colonna e la chiama **«Theory»** [V].
Abaqus usa l'altra e la chiama solo «NAFEMS» [V].

Quindi:

| set | valori (modi 4, 5/6, 7, 8, 9/10) | natura | chi lo usa |
|---|---|---|---|
| **teorico / closed form** | 45,897 · 109,44 · 167,89 · 193,59 · 206,19 | soluzione analitica di piastra | Altair (`f*` closed form) [V], TechSoft3D («Theory») [V] |
| **numerico** | 44,092 · 106,66 · 156,23 · 193,58 · 200,13 | target numerico | Abaqus («NAFEMS») [V] |

**L'ipotesi del ticket è confermata.** Non sono due prove diverse e non è un errore di stampa:
sono i due set che R0015 pubblica per ogni prova.

### 7.3 Controprova numerica indipendente (mia)

**[INF — calcolo mio, non una fonte.]** Teoria di piastra di Mindlin (taglio + inerzia
rotazionale), con E = 200 GPa, ν = 0,3, ρ = 8000, h = 1, a = b = 10, κ = 5/6:

| modo (m,n) | Kirchhoff (piastra sottile) | **Mindlin** | set «closed form» NAFEMS |
|---|---|---|---|
| (1,1) | 47,534 | **45,892** | **45,897** |
| (1,2) | 118,836 | **109,300** | **109,44** |
| (2,2) | 190,138 | **167,317** | **167,89** |

Il set 45,897 **è** la soluzione analitica di piastra spessa: coincide col mio Mindlin a
**4 cifre significative** sul modo fondamentale (45,892 contro 45,897, scarto 0,011%). Il set 44,092, che nessuna teoria di piastra riproduce ma che
C3D8I 8×8×3 riproduce a **0,0%** su tutti e sette i modi, è il target numerico.

Lettura fisica: il vincolo reale di FV52 (solo u_z sui quattro spigoli **inferiori**) è più
cedevole dell'appoggio semplice idealizzato della teoria di piastra, che è definito sul piano
medio. Da qui il ~4% di scarto sui modi flessionali. Il modo 8 coincide fra i due set
(193,58 vs 193,59) perché non è flessionale e quindi non risente del dettaglio d'appoggio. **[INF]**

### 7.4 Quale set usare in tesi

**Raccomandazione (non decisione).** Usare il **set numerico 44,092 …** come target, e citare
l'altro come nota. Motivi: (a) è quello che Abaqus usa per la propria tabella d'errore per tipo
di elemento, che è il nostro termine di paragone per C3D10; (b) è quello coerente con il vincolo
effettivamente prescritto dalla scheda, mentre il closed form vale per un appoggio idealizzato
diverso. Se invece il confronto è con Altair o con letteratura che cita 45,897, dichiararlo.
**Non mescolare i due set nella stessa tabella.**

---

## 8. Accessibilità: cosa è ricostruibile e cosa no

### 8.1 Le pubblicazioni originali restano a pagamento

| pubblicazione | stato | prezzo |
|---|---|---|
| NAFEMS **P18** — *The Standard NAFEMS Benchmarks*, TNSB Rev. 3, ottobre 1990 (serie LE, TE, FV) | a pagamento | <https://www.nafems.org/publications/resource_center/p18/> [V-sec] |
| NAFEMS **R0015** — Abbassian, Dawswell & Knowles, *Selected Benchmarks for Natural Frequency Analysis*, novembre 1987 (serie FV, ~30 prove) | a pagamento | membri £17,50 / non membri **£52,50**; incluso nell'E-Library Corporate Subscription | [V — pagina prodotto letta] |

R0015 costa **£52,50**. Non è una barriera economica seria se la tesi ha bisogno della citazione
formale. **[INF]** Il ticket lo chiama «P09»: non ho trovato una pubblicazione NAFEMS con quel
codice pertinente ai benchmark qui trattati. I due codici che contano sono **P18** e **R0015**. [V]

### 8.2 Ma il contenuto tecnico è pubblicamente e legittimamente disponibile

Non serve comprare nulla per **costruire i deck**. In particolare:

- **NAFEMS stessa distribuisce in chiaro** i file di geometria STEP dei benchmark LE, tramite
  Caesar Systems: `le1abrep_v2.stp`, `le10abrep_v2.stp`, `le11abrep_v3.stp` (AP203 class 6,
  advanced b-rep, autore R. Goult, 2001) e `le10fine.stp` (**AP209 class 10: modello FE, carichi,
  vincoli e target result**). Scaricati e verificati in questa sessione. **La colonna "Provided by"
  di quelle tabelle dice NAFEMS.** [V]
- Le schede una-pagina LE1…LE11 sono riprodotte **verbatim** su Caesar Systems, con origine e
  data/issue. [V]
- I **deck Abaqus** dei benchmark sono pubblicati in chiaro dal produttore e contengono le
  coordinate nodali esatte. [V]
- ESRD ripubblica le figure quotate **su licenza**. [V]

**Regola di citazione, invariata da `ricerca-vv-standard.md:20`:** se la tesi cita un valore
target, la citazione formale è la pubblicazione NAFEMS (P18 o R0015), non il manuale del solutore.
I manuali servono a costruire il modello e a incrociare i numeri, non a sostituire il riferimento.

### 8.3 Verdetto per benchmark

| benchmark | ricostruibile? | note |
|---|---|---|
| **LE1** | **Sì** — geometria, vincoli, carico, target, spessore, tutto su ≥ 2 fonti | ma è **2D**: non esercita l'esportatore di solidi |
| **LE2** | **Sì come guscio** | richiede elementi shell: **fuori portata** per un esportatore di solidi |
| **LE10** | **Sì, senza riserve** | + tabella d'errore Abaqus per C3D20/C3D20R/C3D10/C3D10HS/C3D10M, + risultati tetra lineari e quadratici da SimScale/Code_Aster. **Il candidato statico** |
| **LE11** | **Sì** per geometria/vincoli/carico/target | **manca la tabella d'errore Abaqus per tetraedri**: LE11 è testato solo su C3D20/C3D20R. Richiede inoltre un campo di temperatura nodale calcolato dalle coordinate |
| **FV32** | **Sì** | ma è **2D** (membrana) |
| **FV52** | **Sì, senza riserve** | + tabella d'errore Abaqus per C3D8I/C3D10/C3D10HS/C3D10M/C3D20. **Il candidato modale.** Attenzione ai due set di target (§7) e al riordino dei modi ≥ 8 |

**Non ricostruibile: nessuno dei cinque.** Il vincolo reale non è l'accesso alle pubblicazioni:
è che **LE1, LE2 e FV32 non sono problemi di solidi 3D**. Per verificare un esportatore `.inp`
di tetraedri contro CalculiX, i due che servono sono **LE10** (statico) e **FV52** (modale).
**[INF — questa è una raccomandazione, non una decisione]**

---

## 9. Cosa resta non trovato

1. **[NON TROVATO]** Risultati **C3D4 / tetraedro lineare** su LE11 e FV52, in qualunque fonte.
   Su LE10 il buco è colmato da SimScale (tetra 1° ordine, −5,57%).
2. **[NON TROVATO]** Tabella d'errore Abaqus per **tetraedri su LE11**: la pagina testa solo
   C3D20 e C3D20R.
3. **[NON TROVATO]** Temperatura di riferimento (stato scarico) di LE11, dichiarata
   esplicitamente. Δθ è un incremento; T_ref = 0 è l'assunzione naturale ma non l'ho letta.
4. **[NON TROVATO]** Posizione quotata del punto **E** di LE2 (non cercata: LE2 è fuori portata).
5. **[NON TROVATO]** Il testo integrale di R0015 che elenca *quale* dei due set sia «theoretical»
   e quale «numerical» **per FV52 nominalmente**. L'attribuzione del §7.2 poggia sull'etichetta
   di Altair («closed form») e su NAFEMS che dichiara l'esistenza dei due set — non su R0015 letto.
6. **[NON TROVATO]** Una pubblicazione NAFEMS «P09» pertinente. I codici sono P18 e R0015.

---

## 10. Riferimenti

**Pubblicazioni NAFEMS (citazione formale in tesi):**

1. NAFEMS (1990), *The Standard NAFEMS Benchmarks*, Publication TNSB, Rev. 3, October 1990,
   NAFEMS, Glasgow. [pagina editore: <https://www.nafems.org/publications/resource_center/p18/>]
2. Abbassian, F., Dawswell, D. J. & Knowles, N. C. (1987), *Selected Benchmarks for Natural
   Frequency Analysis*, NAFEMS Publication **R0015**, Glasgow, November 1987.
   [<https://www.nafems.org/publications/resource_center/r0015/>]
3. NAFEMS, *Publications Guide — Benchmarks: Dynamics* (elenco numerato delle prove FV).
   <https://www.nafems.org/publications/pubguide/benchmarks/Page5/>

**Riproduzioni e manuali usati:**

4. Caesar Systems, *NAFEMS Standard Benchmarks* (schede verbatim + file STEP forniti da NAFEMS).
   <http://www.caesarsystems.co.uk/NAFEMS_benchmarks/standardbm.html>
5. Dassault Systèmes, *Abaqus Benchmarks Guide* (mirror MIT, 2017), sezioni LE1, LE2, LE10, LE11,
   FV32, FV52 e relativi file `.inp`.
   <https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-m-NAFEMSBenchmarks-sb.htm>
6. Idem, mirror v2016 Univ. of Colorado.
   <https://ceae-server.colorado.edu/v2016/books/bmk/ch04s04anf25.html>
7. ESRD Inc. (2018), *Benchmarks Guide — The Standard NAFEMS Benchmarks: Linear Elastic Tests*.
   <https://www.esrd.com/wp-content/uploads/dlm_uploads/Benchmarks-Guide-Standard-NAFEMS-Benchmarks-Linear-Elastic-Tests.pdf>
8. Altair, *OptiStruct Verification Problems* OS-V 0455 (FV52) <https://help.altair.com/hwsolvers/os/topics/solvers/os/simply_supported_soid_square_plate_fv52_r.htm> e OS-V 0060 (LE10) <https://help.altair.com/hwsolvers/os/topics/solvers/os/nafems_test_problem_le10_r.htm>.
   <https://help.altair.com/hwsolvers/os/topics/solvers/os/simply_supported_soid_square_plate_fv52_r.htm>
9. TechSoft3D, *The Standard NAFEMS Benchmark Tests for HOOPS Solve*, v2.13.0.
   <https://docs.techsoft3d.com/hoops/mesh/_static/benchmark_reports/benchmark_results_2.13.0.pdf>
10. SimScale, *Validation Case: Thick Plate Under Pressure* (Code_Aster).
    <https://www.simscale.com/docs/validation-cases/thick-plate-under-pressure/>
11. Seamplex, *NAFEMS LE10 thick plate pressure benchmark* (Fino/FeenoX, geometria Gmsh aperta).
    <https://www.seamplex.com/fino/cases/012-nafems-le10/>
12. bConverged (distributore CalculiX), *LE10 benchmark*.
    <http://www.bconverged.com/benchmarks/le10.php>
