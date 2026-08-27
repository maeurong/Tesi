# Verification & Validation per codici FEM strutturali — ricerca su fonti primarie

Data: 2026-08-26. Autore della raccolta: agente `researcher` (sola lettura).
Scopo: fornire riferimenti citabili in tesi su norme, benchmark, metriche di qualità mesh
e limiti noti degli elementi tetraedrici lineari.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte primaria (PDF/pagina ufficiale scaricata in questa sessione).
- **[V-sec]** = verificato su fonte secondaria affidabile (mirror di manuale ufficiale, report di
  laboratorio nazionale che cita la norma), perché la fonte primaria è a pagamento.
- **[INF]** = inferenza mia, non letta su fonte. Da non citare come fatto.
- **[NON TROVATO]** = valore o dettaglio che non ho trovato pubblicato in chiaro. Non l'ho inventato.

Caveat generale: le norme ASME V&V e i benchmark NAFEMS sono **documenti a pagamento**. Il loro
testo integrale non è accessibile in rete. Dove serviva il contenuto, ho usato:
(a) la sintesi firmata dal presidente del comitato ASME (Schwer 2007, peer-reviewed);
(b) i manuali di verifica dei codici commerciali, che ripubblicano geometrie e valori target NAFEMS
su licenza. Questi ultimi sono fonti secondarie *di alta affidabilità* ma non sostituiscono
la pubblicazione NAFEMS originale: **se la tesi cita un valore target, la citazione formale deve
essere la pubblicazione NAFEMS**, non il manuale del solutore.

---

## 1. Norme e guide formali

### 1.1 ASME V&V 10 — Computational Solid Mechanics

**Estremi.** ASME V&V 10-2019 (R2025), *Standard for Verification and Validation in Computational
Solid Mechanics*, The American Society of Mechanical Engineers, New York.
Prima edizione: ASME V&V 10-2006, *Guide for Verification and Validation in Computational Solid
Mechanics* (approvata dal comitato il 13 luglio 2006). Nel 2019 il titolo passa da "Guide" a
"Standard". URL editore: <https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics>. [V-sec]

**Fonte primaria leggibile sul contenuto della prima edizione:**
Schwer, L. E. (2007), *An overview of the PTC 60/V&V 10: guide for verification and validation in
computational solid mechanics*, **Engineering with Computers**, 23(4):245–252,
DOI [10.1007/s00366-007-0072-z](https://doi.org/10.1007/s00366-007-0072-z).
Schwer era **Chair del comitato PTC 60/V&V 10**: è la descrizione autorevole del contenuto della Guide. [V]

**Cosa prescrive — testuale da Schwer 2007.** [V]

Principi chiave dichiarati nell'Abstract della Guide:

> - Verification must precede validation.
> - The need for validation experiments and the associated accuracy requirements for computational
>   model predictions are based on the intended use of the model and should be established as part
>   of V&V activities.
> - Validation of a complex system should be pursued in a hierarchical fashion from the component
>   level to the system level.
> - Validation is specific to a particular computational model for a particular intended use.
> - Validation must assess the predictive capability of the model in the physical realm of interest,
>   and it must address uncertainties that arise from both simulation results and experimental data.

Struttura in quattro sezioni: Introduction, Model development, Verification, Validation, più
Concluding Remarks e **Glossary** (il glossario è indicato dal comitato stesso come contributo
principale alla standardizzazione del linguaggio).

**Definizioni (verbatim, Schwer 2007 §8):**

> - **Verification**: The process of determining that a computational model accurately represents
>   the underlying mathematical model and its solution.
> - **Validation**: The process of determining the degree to which a model is an accurate
>   representation of the real world from the perspective of the intended uses of the model.

**La distinzione a due gambe della verification (verbatim):**

> 1. **Code verification** — establish confidence, through the collection of evidence, that the
>    mathematical model and solution algorithms are working correctly.
> 2. **Calculation verification** — establish confidence, through the collection of evidence, that
>    the discrete solution of the mathematical model is accurate.

Sintesi del comitato, citabile: *"verification is the domain of mathematics and validation is the
domain of physics"* (Schwer 2007 §8).

**Gerarchia dei modelli.** La Guide impone la catena
*reality of interest → Conceptual Model → Mathematical Model → Computational Model*, con definizioni
formali per ciascuno (Schwer 2007 §7). Il "conceptual model" è *"the collection of assumptions and
descriptions of physical processes representing the solid mechanics behavior of the reality of
interest"*. [V]

**Calibrazione ≠ validazione.** La Guide distingue esplicitamente `calibration` ("the process of
adjusting physical modeling parameters in the computational model to improve agreement with
experimental data") dalla validazione, e prescrive che **il modello usato nel confronto di
validazione non sia calibrato sui dati di validazione**; se servono parametri, vanno determinati con
un esperimento di calibrazione separato, a livello di sottosistema (Schwer 2007 §7). [V]

**Metriche di validazione.** La Guide non impone una metrica. Verbatim:

> Validation metric is the term used to describe the comparison of validation experiment and
> simulation outcomes. These metrics can range from simple binary metrics [...] to more complex
> comparisons involving magnitude and phase difference in wave forms [...] Whatever the form of the
> validation metric, the result should be a quantitative assessment of the agreement between the
> experiment and simulation.

Forma di riporto raccomandata, **a tre parti**: *"the relative error between the experiment and
simulations was 18 ± 6% with a 85% confidence level"* (Schwer 2007 §10). Questa è la forma da imitare
in tesi quando si riporta un confronto con misura. [V]

**Punto direttamente rilevante per una tesi su mesh.** Schwer 2007 §9.2, verbatim:

> The lack of mesh-refinement studies in solid mechanics may be the largest omission in the
> verification process. This is particularly distressing, since it is relatively easy to remedy.

**Il V&V Plan.** Tre elementi obbligatori: *system response features* (cosa si confronta e con quale
metrica), *validation testing* (l'insieme di esperimenti), *accuracy requirements* (soglie
quantitative di accettazione). Il Plan risponde alla domanda "what is a validated model?". [V]

**Roster del comitato** (utile se in tesi serve mostrare che la norma è consensuale e non di parte):
include W. L. Oberkampf e T. G. Trucano (Sandia), P. J. Roache, J. T. Oden, J. N. Reddy,
J. H. Fortna (ANSYS), L. Proctor (MSC Software) — Schwer 2007 §12.2. [V]

### 1.2 ASME V&V 10.1 — l'esempio applicato

**Estremi.** ASME V&V 10.1-2012 (R2022), *An Illustration of the Concepts of Verification and
Validation in Computational Solid Mechanics*, ASME, ISBN 9780791834152.
URL: <https://www.asme.org/codes-standards/find-codes-standards/an-illustration-of-the-concepts-of-verification-and-validation-in-computational-solid-mechanics>. [V-sec]

Contenuto: applica i concetti di V&V 10-2006 a un caso concreto — **trave a scatola rastremata,
elastica, a mensola, sotto carico statico non uniforme**; il problema di validazione usa un carico
uniforme su metà della lunghezza. È dichiarato come primo di una serie di documenti "more detailed
and practical" pensati per colmare il salto fra la Guide e un insieme di recommended practices. [V-sec]

Rilevanza per la tesi: **il caso didattico ufficiale ASME per la solid mechanics è una mensola.** Se
la tesi usa una mensola come caso di verifica, è allineata alla prassi normativa e lo si può dire
citando V&V 10.1. [INF sull'uso, V-sec sul contenuto]

### 1.3 ASME V&V 40 — credibilità e context of use

**Estremi.** ASME V&V 40-2018, *Assessing Credibility of Computational Modeling through Verification
and Validation: Application to Medical Devices*, ASME.
URL: <https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices>. [V-sec]

Cosa aggiunge rispetto a V&V 10:
- introduce il **context of use (COU)** e il **model risk** come determinanti del *quanto* V&V serve;
- il rigore delle attività V&V è graduato sul rischio, non uniforme;
- non è una procedura passo-passo né un metodo quantitativo per stabilire la credibilità: è un
  framework di giudizio ingegneristico documentato;
- è dichiarato come **complemento** a V&V 10 e V&V 20, non sostituto;
- sviluppato con FDA e industria dei dispositivi medici. [V-sec]

**Pertinenza a una tesi di meccanica strutturale.** Il framework COU/model risk è dominio-agnostico e
viene applicato fuori dal medicale in letteratura peer-reviewed; esempio citabile:
Nicolini et al., *Credibility assessment of computational models according to ASME V&V40*,
Computer Methods and Programs in Biomedicine (2023),
<https://www.sciencedirect.com/science/article/pii/S0169260723003930>. [V-sec]
Se la tesi non ha un dispositivo regolamentato, V&V 40 va citata come **fonte del concetto di
"credibilità graduata sul rischio"**, non come norma applicabile. [INF]

### 1.4 AIAA G-077 — l'antenato CFD

**Estremi.** AIAA G-077-1998 (R2002), *Guide for the Verification and Validation of Computational
Fluid Dynamics Simulations*, American Institute of Aeronautics and Astronautics, Reston VA.
DOI/URL editore: <https://arc.aiaa.org/doi/book/10.2514/4.472855>. Approvato dal CFD Committee on
Standards il 14/01/1998, accettato dall'AIAA Standards Executive Council il 06/05/1998. [V-sec]

Definizioni originarie (poi riprese e modificate da ASME):
- **Verification**: *"the process of determining if a computational simulation accurately represents
  the conceptual model, but no claim is made of the relationship of the simulation to the real world."*
- **Validation**: *"the process of determining if a computational simulation represents the real world."* [V-sec]

Nesso storico documentato in fonte primaria: Schwer 2007 §4 dichiara che **il comitato ASME nasce su
impulso della AIAA CFD Committee dopo il G-077 del 1998**, partendo dall'idea (poi rivelatasi
ingenua) di adattarlo alla meccanica dei solidi. [V]

Rassegna critica scaricabile del G-077, ospitata da NAFEMS:
<https://www.nafems.org/downloads/edocs/aiaa_guide_review.pdf>. [V-sec, non letta integralmente]

### 1.5 Oberkampf & Trucano / Roache — la letteratura fondativa

- Oberkampf, W. L. & Trucano, T. G. (2002), *Verification and validation in computational fluid
  dynamics*, **Progress in Aerospace Sciences**, 38(3):209–272,
  DOI [10.1016/S0376-0421(02)00005-2](https://doi.org/10.1016/S0376-0421(02)00005-2).
  Versione Sandia: SAND2002-0529. Contenuto: distinzione code verification / solution verification,
  model validation / solution validation, errore vs incertezza, rapporto validazione–predizione. [V-sec]
- Roache, P. J. (1998), *Verification and Validation in Computational Science and Engineering*,
  Hermosa Publishers, Albuquerque NM. Testo di riferimento per la verification; Roache è nel roster
  ASME PTC 60 (Schwer 2007 §12.2). [V-sec / V per il roster]
- Roache, P. J. (1994), *Perspective: A Method for Uniform Reporting of Grid Refinement Studies*,
  **Journal of Fluids Engineering**, 116(3):405–413,
  DOI [10.1115/1.2910291](https://doi.org/10.1115/1.2910291). Origine del GCI. [V-sec]
- Salari, K. & Knupp, P. (2000), *Code Verification by the Method of Manufactured Solutions*,
  **SAND2000-1444**, Sandia National Laboratories, Albuquerque NM.
  PDF libero: <https://www.osti.gov/servlets/purl/759450>. [V-sec]
  Tesi del report: MMS *"can identify any coding mistake that affects the order-of-accuracy of the
  numerical method"*, e testa il codice "in full generality" a differenza dei confronti con soluzioni
  analitiche specifiche. [V-sec]

### 1.6 Qualificazione del software di calcolo — ambito nucleare

**ASME NQA-1**, *Quality Assurance Requirements for Nuclear Facility Applications*, Part II,
Subpart 2.7: *Quality Assurance Requirements for Computer Software for Nuclear Facility Applications*
(edizione corrente 2024).
URL: <https://www.asme.org/codes-standards/find-codes-standards/quality-assurance-requirements-for-nuclear-facility-applications>. [V-sec]

Struttura della Subpart 2.7: General (100–102), General Requirements (200–204), Software Acquisition
(300–302), Software Engineering Method (400–407), Standards/Conventions/Work Practices (500),
Support Software (600–602), References (700). Copre acquisizione, V&V, e manutenzione del software. [V-sec]

Catena regolatoria correlata, documentata in fonti governative USA:
DOE O 414.1C/D (Quality Assurance) e 10 CFR 50 Appendix B; il DOE richiede che la gestione del
"safety software" includa verification and validation, inclusi inspection e testing —
vedi *Applying DOE O 414.1C and NQA-1 Requirements to ISM Software*,
<https://www.energy.gov/sites/prod/files/2014/05/f16/Applying%20DOE%20O%20414.1C%20and%20NQA-1%20Requirements%20to%20ISM%20Software.pdf>. [V-sec]

**[NON TROVATO]** Una norma ISO/IEC o EN *specifica per il software di calcolo strutturale*
(analoga a NQA-1 Subpart 2.7 ma in ambito civile europeo) non l'ho trovata. Gli Eurocodici
(EN 1990 e seguenti) non normano la qualificazione del software FEM. Quello che esiste in ambito
europeo è materiale NAFEMS (es. Quality System Supplement to ISO 9001) e ISO 9001/ISO-IEC 25010
generici — non li ho verificati su fonte primaria in questa sessione. **Non citarli come se fossero
norme di qualificazione del solutore.** [NON TROVATO]

---

## 2. Benchmark di verifica

### 2.1 NAFEMS — pubblicazioni di riferimento

Le due pubblicazioni da citare formalmente:

- **NAFEMS (1990)**, *The Standard NAFEMS Benchmarks*, Publication TNSB, Rev. 3, October 1990,
  NAFEMS, Glasgow. Contiene la serie LE (linear elastic) e TE (thermo-elastic).
  Riferimento confermato verbatim dal manuale di benchmark Abaqus: *"NAFEMS Publication TNSB, Rev. 3
  (October 1990)"*. Pagina editore: <https://www.nafems.org/publications/resource_center/p18/>. [V]
- **Abbassian, F., Dawswell, D. J. & Knowles, N. C. (1987)**, *Selected Benchmarks for Natural
  Frequency Analysis*, NAFEMS Publication, Glasgow, November 1987. Serie FV (free vibration),
  ~30 test, ciascuno in formato di una pagina con geometria, condizioni al contorno, **due set di
  frequenze "target"** e forme modali schematiche.
  Pagina editore: <https://www.nafems.org/publications/resource_center/r0015/>. [V-sec]

**Attenzione alla numerazione FV.** Ho trovato la stessa prova con **due numeri diversi** in due
manuali di solutori: la piastra quadrata "solid" semplicemente appoggiata è **FV52** in Abaqus e
**FV51** in HOOPS Solve; e i valori "Theory" citati differiscono (44,092 Hz vs 45,897 Hz per il primo
modo elastico). Vedi §2.3. Non risolvere la discrepanza a memoria: va sciolta sul documento NAFEMS
1987 originale. [V — discrepanza osservata direttamente su due fonti]

### 2.2 Serie LE — elasticità lineare

Fonte usata per geometria/materiale/target (ripubblicazione su licenza):
ESRD Inc. (2018), *Benchmarks Guide — The Standard NAFEMS Benchmarks: Linear Elastic Tests*,
<https://www.esrd.com/wp-content/uploads/dlm_uploads/Benchmarks-Guide-Standard-NAFEMS-Benchmarks-Linear-Elastic-Tests.pdf>. [V — PDF scaricato e letto]
Fonte incrociata per LE10/LE11: *Abaqus Benchmarks Guide*, sezioni LE10 e LE11,
<https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-c-le10.htm> e
<https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-c-le11.htm>. [V]

I test presenti nella guida ESRD: **LE1, LE2, LE3, LE5, LE6, LE7, LE8, LE10, LE11**. [V]

#### LE1 — Elliptic membrane (plane stress)
- Geometria: membrana a contorni ellittici ABCD, stato piano di tensione.
- Materiale: E = 210 GPa, ν = 0,3.
- Vincoli: simmetria lungo AB e DC.
- Carico: pressione uscente uniforme 10 MPa sul bordo esterno BC.
- **Target: tensione tangenziale di bordo σ_y = 92,7 MPa nel punto D.** [V]
- Riferimento di convergenza ESRD: quad 4 elementi → 92,75 MPa (0,05%); quad 144 elementi → 92,70 MPa (0,00%). [V]
- **Uso:** è 2D. Non serve a verificare un solutore 3D solido. [INF]

#### LE2 — Cylindrical shell bending patch test
- Settore di guscio cilindrico θ = 30°, spessore costante T = 10 mm.
- E = 210 GPa, ν = 0,3. Incastro su AB, simmetria su AD e BC.
- Momento flettente uniforme 1000 N·mm per unità di lunghezza su DC.
- **Target: tensione tangenziale sulla superficie esterna = 60 MPa.** [V]

#### LE10 — Thick plate under pressure  ← il più usato per solidi 3D
- Piastra spessa; E = 210 GPa, ν = 0,3, ρ = 7800 kg/m³ (la densità solo in Abaqus).
- Vincoli (formulazione Abaqus, più precisa di quella ESRD):
  u_y = 0 sulla faccia DCD′C′; u_x = 0 su ABA′B′; u_x = u_y = 0 su BCB′C′;
  u_z = 0 sulla linea EE′ (punti medi degli spigoli CC′ e BB′).
- Carico: pressione normale uniforme 1,0 MPa sulla superficie superiore.
- **Target: σ_yy = −5,38 MPa nel punto D.** (Abaqus lo scrive come "5.38 MPa"; ESRD e Altair come
  "−5.38 MPa": è compressione, il segno dipende dalla convenzione riportata.) [V su entrambe le fonti]
- Risultati pubblicati Abaqus (mesh coarse / fine):
  C3D20 −6,72 (+25,00%) / −5,64 (+4,83%); C3D20R −7,93 (+47,39%) / −5,53 (+2,78%);
  C3D10 −5,44 (+1,15%) / −5,77 (+7,24%); C3D10HS −5,08 (−3,72%) / −5,51 (+2,42%);
  C3D10M −5,57 (+3,53%) / −5,89 (+9,48%). [V]
- **Nota critica.** Nella tabella Abaqus l'errore di C3D10 **cresce** passando da coarse a fine
  (1,15% → 7,24%). Non è un errore di stampa nel senso che la fonte lo riporta così, ma **significa
  che il valore puntuale in D non è una quantità monotona convergente su queste due mesh**: LE10
  è un target di tensione in un punto singolare/di bordo. Se la tesi usa LE10 per uno studio di
  convergenza, va detto. [V per i numeri, INF per l'interpretazione]
- **[NON TROVATO]** Nessun risultato pubblicato per **C3D4** su LE10 nel manuale Abaqus consultato.

#### LE11 — Solid cylinder / taper / sphere, carico termico
- Solido cilindro-raccordo-sfera; E = 210 GPa, ν = 0,3, α = 2,3·10⁻⁴ /°C.
- Vincoli (terna NAFEMS): u_z = 0 sul piano z = 0; u_x = 0 sul piano x = 0; u_y = 0 sul piano
  y = 0; **u_z = 0 sulla faccia superiore HIH′I′**. ESRD chiama BCDE la stessa faccia perché
  ruota la terna: stessa faccia, stesso vincolo, non due specifiche diverse. Formulazione NAFEMS
  verbatim e nomenclatura in [`benchmark-nafems.md`](benchmark-nafems.md) § «Vincoli — formulazione
  NAFEMS verbatim» (righe 244-252). [V]
- Carico: gradiente termico lineare radiale e assiale, Δθ = √(x²+y²) + z (imposto in Abaqus via
  subroutine UTEMP).
- **Target: σ_zz = −105 MPa nel punto A.** [V su entrambe le fonti]
- Risultati ESRD: hex 8 elementi → −105,2 MPa (0,19%); hex 216 → −105,4 (0,38%);
  **tetra 317 elementi → −105,5 MPa (0,48%); tetra 3531 → −105,4 (0,38%)** (elementi p-version
  StressCheck, non tet lineari). [V]
- Risultati Abaqus: C3D20 −96,71 (−7,9%) coarse, −103,26 (−1,7%) fine; C3D20R −93,04 (−11,4%) /
  −99,60 (−5,1%). [V]
- Risultato indipendente utile come terzo punto: HOOPS Solve −93,47 MPa, MSC Nastran −99,48 MPa
  contro teoria −105,0 MPa (TechSoft3D, *The Standard NAFEMS Benchmark Tests for HOOPS Solve*,
  <https://docs.techsoft3d.com/hoops/mesh/_static/benchmark_reports/benchmark_results_2.13.0.pdf>). [V]

### 2.3 Serie FV — analisi modale

Fonte usata: TechSoft3D, *The Standard NAFEMS Benchmark Tests for HOOPS Solve* (PDF sopra) [V] e
*Abaqus Benchmarks Guide*, FV52 <https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-c-fv52.htm> [V].

#### FV32 — Cantilevered tapered membrane
- Membrana rastremata a mensola; E = 200 GPa, ν = 0,3, ρ = 8000 kg/m³.
- Vincoli: z = 0 su tutti i nodi, x = y = 0 lungo l'asse y.
- **Frequenze target (Hz), primi 6 modi: 44,623, 130,03, 162,7, 246,05, 379,9, 391,44.** [V]
- HOOPS Solve (quad 4 nodi): 44,631, 129,833, 162,618, 244,648, 375,251, 389,853. [V]
- È 2D (membrana). Serve a verificare distorsione di mesh e comportamento a taglio, non i solidi. [INF]

#### FV52 (= FV51 in HOOPS) — Simply supported "solid" square plate  ← il benchmark modale per solidi 3D
- Piastra quadrata di spessore 1,0 m modellata con elementi solidi;
  E = 200 GPa, ν = 0,3, ρ = 8000 kg/m³.
- Vincolo: u_z = 0 lungo i quattro spigoli sul piano z = −0,5.
- Modi 1–3 sono moti rigidi (RBM).
- **Frequenze di riferimento NAFEMS secondo Abaqus (Hz): modo 4 = 44,092; 5 = 106,66; 6 = 106,66;
  7 = 156,23; 8 = 193,58; 9 = 200,13; 10 = 200,13.** [V]
- **Frequenze "Theory" secondo TechSoft3D (test numerato FV51) (Hz): modo 4 = 45,897; 5 = 109,44;
  6 = 109,44; 7 = 167,89; 8 = 193,59; 9 = 206,19; 10 = 206,19.** [V]
- **⚠ Discrepanza reale fra le due fonti** (≈4% sui modi 4–7, ma il modo 8 coincide: 193,58 vs 193,59).
  Ipotesi non verificata: le due fonti stanno usando i **due diversi set di target** che la
  pubblicazione NAFEMS 1987 fornisce per ogni prova ("two sets of 'target' frequencies"). **[INF —
  da confermare sul documento NAFEMS originale prima di citarlo in tesi.]**
- Risultati Abaqus per tipo di elemento (modo 4 / modo 7):
  C3D8I 44,092 (0,0%) / 156,23 (0,0%); C3D10 44,348 (0,58%) / 163,58 (4,70%);
  C3D10HS 44,348 (0,58%) / 163,58 (4,70%); C3D10M 42,687 (−3,19%) / 151,22 (−3,21%);
  C3D20 44,796 (1,60%) / 169,10 (8,24%). [V]
- **[NON TROVATO]** Nessun risultato **C3D4** pubblicato su FV52.

### 2.4 Patch test di Irons

**Riferimenti canonici:**
- Irons, B. M. & Razzaque, A. (1972), *Experience with the patch test for convergence of finite
  elements*, in *The Mathematical Foundations of the Finite Element Method with Applications to
  Partial Differential Equations* (A. K. Aziz ed.), Academic Press, pp. 557–587.
  **[V-sec — riferimento standard, non l'ho letto in questa sessione]**
- **Taylor, R. L., Simo, J. C., Zienkiewicz, O. C. & Chan, A. C. H. (1986)**, *The patch test — a
  condition for assessing FEM convergence*, **International Journal for Numerical Methods in
  Engineering**, 22(1):39–62, DOI [10.1002/nme.1620220105](https://doi.org/10.1002/nme.1620220105).
  Questa è la fonte da citare per le **forme A, B, C**. [V-sec]
- Zienkiewicz, O. C. & Taylor, R. L. (1986), *The patch test for mixed formulations*, IJNME
  23(10):1873–1883, DOI [10.1002/nme.1620231007](https://doi.org/10.1002/nme.1620231007). [V-sec]

**Cosa dimostra.** Taylor et al. 1986: la soddisfazione del patch test è **condizione necessaria di
convergenza, equivalente alla consistency**; unita alla verifica di **stability** diventa anche
**sufficiente**. Il test ha due parti: (a) valutazione di consistency, (b) controllo di stability. [V-sec]

**Le tre forme (A, B, C).** Nella parte di consistency si impone come soluzione esatta un insieme di
polinomi essenziali linearmente indipendenti (tutti i termini fino all'ordine necessario a descrivere
il modello), e nel limite di patch → 0 il modello FEM deve soddisfarli esattamente. Le tre modalità
di imporlo sono le forme A, B, C. **Forma C** — tutte le condizioni al contorno naturali (trazioni,
per l'elasticità) tranne il numero minimo di condizioni essenziali necessarie a rendere unica la
soluzione (soppressione dei moti rigidi) — **è quella raccomandata**, perché testa insieme consistency
e stability. Sono necessari sia test a un elemento sia test a più elementi. Se il programma non
rileva da sé le deficienze di rango, la stabilità va testata contando gli autovalori nulli della
matrice di rigidezza. [V-sec — sintesi da ScienceDirect Topics "Patch Test", che riporta il contenuto
di Taylor et al.; **verificare sul paper originale prima di citare parola per parola in tesi**]

**Costruzione su tetraedri.** [INF, dichiarata come tale]
Non ho trovato una fonte primaria che descriva il patch test *specificamente su tetraedri lineari*.
Lo schema generale che discende da Taylor et al. 1986: si prende una patch di ≥ 4–5 tetraedri con
almeno **un nodo interno** (senza nodo interno il test è banale), si impone un campo di spostamento
lineare u = a + Bx, si applicano le condizioni al contorno secondo la forma scelta, e si verifica che
tutti i nodi — **incluso quello interno** — riproducano il campo lineare a meno della precisione di
macchina, e che le tensioni siano costanti in tutti gli elementi. Il C3D4 è a deformazione costante,
quindi **passa il patch test lineare per costruzione**: superarlo non dice nulla sull'accuratezza in
flessione. Questa ultima frase è la ragione per cui il patch test da solo non basta come verification.

### 2.5 Method of Manufactured Solutions (MMS)

**Riferimenti canonici:**
- Salari, K. & Knupp, P. (2000), *Code Verification by the Method of Manufactured Solutions*,
  SAND2000-1444, Sandia National Laboratories. PDF: <https://www.osti.gov/servlets/purl/759450>. [V-sec]
- Roache, P. J. (2002), *Code Verification by the Method of Manufactured Solutions*, **Journal of
  Fluids Engineering**, 124(1):4–10, DOI [10.1115/1.1436090](https://doi.org/10.1115/1.1436090). [V-sec]
- Knupp, P. & Salari, K. (2003), *Verification of Computer Codes in Computational Science and
  Engineering*, Chapman & Hall/CRC. [V-sec]

**Il meccanismo, descritto in fonte primaria ASME** (Schwer 2007 §9.1, verbatim): [V]

> Given a partial differential equation (PDE), and a code that provides general solutions of that
> PDE, an arbitrary solution to the PDE is manufactured, i.e., made up, then substituted into the
> PDE along with associated boundary and initial condition, also manufactured. The result is a
> forcing function (right-hand side) that is the exact forcing function to reproduce the originally
> selected (manufactured) solution.

L'esempio ASME è **strutturale**: trave EI·y⁗ = w(x), soluzione manufatta
y(x) = A·sin(ax/L) + B·exp(x/L) + C, da cui
w(x)/EI = A·(a⁴/L⁴)·sin(ax/L) + (B/L⁴)·exp(x/L). Il forcing risultante si dà in input al codice a
elementi trave e si confronta la soluzione discreta con y(x). [V]

**Cosa misura.** Non l'errore assoluto: **l'ordine di accuratezza osservato**. Il codice è verificato
osservando l'ordine di convergenza dell'errore numerico totale al raffinare della mesh. Un errore di
codifica che sporca l'ordine viene individuato; un errore che lascia l'ordine intatto no. [V-sec — Salari
& Knupp abstract]

**MMS applicato all'elasticità 3D — riferimento moderno e citabile:**
Aycock, K. I., Rebelo, N. & Craven, B. A. (2020), *Method of manufactured solutions code verification
of elastostatic solid mechanics problems in a commercial finite element solver*,
**Computers & Structures**, 229:106175,
DOI [10.1016/j.compstruc.2019.106175](https://doi.org/10.1016/j.compstruc.2019.106175);
preprint aperto arXiv:1902.07608, <https://arxiv.org/abs/1902.07608>. [V — abstract letto]
Contenuto verificato: il codice verificato è **Abaqus/Standard**; modelli costitutivi lineare
elastico, iperelastico neo-Hookean, quasi-iperelastico di Hencky; MMS applicata alla forma forte
delle equazioni dell'elasticità 3D in coordinate curvilinee; **termini sorgente generati con
Python/SymPy o Mathematica e imposti senza modificare il sorgente del solutore**; convergenza
osservata **del secondo ordine per lo spostamento** al raffinare della mesh, e **del primo ordine
rispetto al raffinamento dell'incremento** nei problemi a deformazione finita. [V]
**[NON TROVATO]** L'abstract non specifica i tipi di elemento usati (tet o hex) né gli ordini
osservati su tensione/deformazione: se questi dettagli servono in tesi, vanno presi dal full text.

Altro riferimento pertinente (shell, se serve):
Kamensky et al./Roohbakhshan et al. (2018), *Code verification examples based on the method of
manufactured solutions for Kirchhoff–Love and Reissner–Mindlin shell analysis*, Engineering with
Computers, DOI [10.1007/s00366-017-0572-4](https://doi.org/10.1007/s00366-017-0572-4). [V-sec —
titolo verificato in ricerca, contenuto non letto]

### 2.6 Convergenza di mesh, estrapolazione di Richardson, GCI

**Riferimenti:**
- Roache, P. J. (1994), *Perspective: A Method for Uniform Reporting of Grid Refinement Studies*,
  J. Fluids Eng. 116(3):405–413, DOI [10.1115/1.2910291](https://doi.org/10.1115/1.2910291). [V-sec]
- Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H. & Raad, P. E. (2008),
  *Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications*,
  **Journal of Fluids Engineering**, 130(7):078001,
  DOI [10.1115/1.2960953](https://doi.org/10.1115/1.2960953). È la **policy editoriale ASME**: la
  forma canonica in cui riportare uno studio di convergenza. [V-sec]
- NPARC Alliance CFD Verification and Validation, *Examining Spatial (Grid) Convergence*, NASA Glenn
  Research Center, <https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html>. [V — pagina letta]

**Formule (dalla pagina NASA, verificate):** [V]

Rapporto di raffinamento, con h₁ passo fine e h₂ passo grossolano:

    r = h₂ / h₁

Estrapolazione di Richardson per metodo di ordine p e r arbitrario:

    f_(h=0) = (r^p · f₁ − f₂) / (r^p − 1)

caso classico r = 2:

    f_(h=0) = (4·f₁ − f₂) / 3

Errore relativo:

    ε = (f₁ − f₂) / f₁

Grid Convergence Index sulla griglia fine e su quella grossolana:

    GCI₁₂ = F_s · |ε₁₂| / (r^p − 1) · 100 %
    GCI₂₃ = F_s · |ε₂₃| / (r^p − 1) · 100 %

Fattore di sicurezza, verbatim NASA: *"The factor of safety is recommended to be Fs = 3.0 for
comparisons of two grids and Fs = 1.25 for comparisons over three or more grids."*

Verifica di essere nel range asintotico:

    GCI₂₃ ≈ r^p · GCI₁₂     (il rapporto deve valere ≈ 1,0)

**Variante Celik et al. 2008** (safety factor fisso 1,25 con tre griglie, ordine *apparente* p
calcolato dai dati anziché assunto). Forma citata:

    GCI_fine^21 = 1,25 · e_a^21 · r^p / (r^p − 1)

**[NON TROVATO / da verificare]** Ho trovato questa forma della formula in una sintesi di ricerca,
non leggendo direttamente il PDF (il documento NRC ML090780152 che la ripubblica ha risposto 403).
**Prima di scriverla in tesi, leggere il paper.** Il punto da non confondere: nella pagina NASA il
numeratore è F_s·|ε|, in Celik compare in più il fattore r^p — sono due parametrizzazioni diverse
dello stesso stimatore e **non vanno mescolate**.

**Come si riporta in un lavoro accademico.** [INF, ma coerente con Celik 2008 e con la forma a tre
parti di ASME V&V 10]
Una tabella con: h₁/h₂/h₃ (o il numero di elementi e la dimensione caratteristica), il valore della
quantità di interesse su ciascuna griglia, i rapporti r₂₁ e r₃₂, l'ordine osservato p, il valore
estrapolato, e il GCI percentuale sulla griglia fine. Il GCI si presenta **come banda di incertezza
numerica**, non come "errore": è la stima di quanto il valore fine può ancora spostarsi.

---

## 3. Metriche di qualità della mesh — definizioni canoniche

> **Avvertenza che vale per tutta questa sezione.** Lo stesso nome indica formule diverse in librerie
> diverse. Le due prove concrete raccolte in questa sessione:
> (a) `aspect ratio` in Verdict per tetraedri è **L_max / (2√6·r)**, mentre in Abaqus/CAE è
> semplicemente **spigolo più lungo / spigolo più corto** (che in Verdict si chiama `edge ratio`);
> (b) `gamma` in Gmsh/HXT è **√24·r_in / |e_max|** (raggio inscritto su spigolo massimo), **non**
> il rapporto inscritta/circoscritta e **non** l'`aspect gamma` di Verdict.
> **Riportare sempre la formula, mai solo il nome.**

### 3.1 Sandia Verdict

**Estremi.** Stimpson, C. J., Ernst, C. D., Knupp, P., Pébay, P. P. & Thompson, D. (2007),
*The Verdict Geometric Quality Library*, **SAND2007-1751**, Sandia National Laboratories,
Albuquerque NM, marzo 2007.
PDF: <https://www.osti.gov/servlets/purl/901967/> e <https://coreform.com/papers/verdict_quality_library.pdf>.
Tutte le formule seguenti sono **[V]** — lette dal PDF, §6 (tetraedri) e §7 (esaedri).

**Notazione tetraedro (Verdict §6).** Vertici P₀…P₃; vettori spigolo
L₀ = P₁−P₀, L₁ = P₂−P₁, L₂ = P₀−P₂, L₃ = P₃−P₀, L₄ = P₃−P₁, L₅ = P₃−P₂.
Volume: V = ((L₂ × L₀) · L₃) / 6.
Area totale: A = ½·(|L₂×L₀| + |L₃×L₀| + |L₄×L₁| + |L₃×L₂|).
Raggio inscritto: r = 3V / A.
Raggio circoscritto: R = ( |L₃|²·(L₂×L₀) + |L₂|²·(L₃×L₀) + |L₀|²·(L₃×L₂) ) / (12V)  — norma del vettore.

#### Metriche tetraedriche (formula → range accettabile → valore per tet equilatero)

| Metrica Verdict | Formula esatta | Range accettabile | Equilatero | Funzione C |
|---|---|---|---|---|
| **edge ratio** | L_max / L_min | [1, 3] | 1 | `v_tet_edge_ratio` |
| **aspect δ (delta)** | q = min_i { C·h_i / √(A_jkl) }, C = ⁴√108/4 ≈ 0,805927; h_i altezza del vertice i sulla faccia opposta | [0,1, DBL_MAX] | 1 | non supportata |
| **aspect Frobenius** | numero di condizionamento in norma di Frobenius di A₀ = T₀W⁻¹, con T₀ = (L₀ L₁ L₂) e W matrice del tet regolare di riferimento; normalizzato a 1 sul regolare | [1, 1,3] | 1 | `v_tet_aspect_frobenius` |
| **aspect γ (gamma)** | q = R̄³·√2 / (12·\|V\|), con R̄ = √( Σᵢ₌₀⁵ \|Lᵢ\|² / 6 ) = lunghezza RMS degli spigoli | [1, 3] | 1 | `v_tet_aspect_gamma` |
| **aspect ratio** | **L_max / (2√6 · r)** | [1, 3] | 1 | `v_tet_aspect_ratio` |
| **collapse ratio** | q = min_i { h_i / max(\|L_jk\|, \|L_kl\|, \|L_lj\|) } | [0,1, DBL_MAX] | √6/3 | `v_tet_collapse_ratio` |
| **condition** | q = √(T₁·T₂) / (3·C_det), con C₁ = L₀, C₂ = −(2L₂+L₀)/√3, C₃ = (3L₃+L₂−L₀)/√6, C_det = C₁·(C₂×C₃), T₁ = ΣCᵢ·Cᵢ, T₂ = Σ\|Cᵢ×Cⱼ\|² | [1, 3] | 1 | `v_tet_condition` |
| **Jacobian** | q = (L₂ × L₀) · L₃  (dimensione L³) | [0, DBL_MAX] | √2/2 | `v_tet_jacobian` |
| **minimum dihedral angle** | αᵢ = (180/π)·arccos(n_i1 · n_i2) su ciascuno dei 6 spigoli; q = min αᵢ, in gradi | **[40°, 70,5288°]** | arccos(1/3) ≈ 70,528779° | `v_tet_minimum_angle` |
| **radius ratio** | **q = R / (3r)** = ( \|L₃\|²(L₂×L₀) + \|L₂\|²(L₃×L₀) + \|L₀\|²(L₃×L₂) )·A / (108·V²) | [1, 3] | 1 | `v_tet_radius_ratio` (alias deprecato: `v_tet_aspect_beta`) |
| **relative size squared** | R = V/V̄ (V̄ = volume medio dell'insieme); q = min(R, 1/R)² | [0,3, 1] | N/A | `v_tet_relative_size_squared` |
| **scaled Jacobian** | q = J·√2 / λ_max, con J il Jacobian sopra, λ₁=\|L₀\|\|L₂\|\|L₃\|, λ₂=\|L₀\|\|L₁\|\|L₄\|, λ₃=\|L₁\|\|L₂\|\|L₅\|, λ₄=\|L₃\|\|L₄\|\|L₅\|, λ_max = max(λ₁..λ₄, J) | **[0,5, √2/2 ≈ 0,7071]** | 1 | `v_tet_scaled_jacobian` |
| **shape** | q = 3·(J√2)^(2/3) / ( (3/2)·(L₀·L₀ + L₂·L₂ + L₃·L₃) − (L₀·(−L₂) + L₀·L₃ + (−L₂)·L₃) ) | [0,3, 1] | 1 | `v_tet_shape` |
| **shape and size** | q = shape × relative_size_squared | [0,2, 1] | dipende da V | `v_tet_shape_and_size` |
| **volume** | q = V | [0, DBL_MAX] | √2/12 | `v_tet_volume` |

**Tre punti da non sbagliare:** [V per i fatti, INF per l'enfasi]
1. **`aspect_beta` non esiste più come metrica autonoma**: Verdict dichiara che era il vecchio nome di
   `radius ratio` = R/(3r), mantenuto per retrocompatibilità e destinato alla rimozione.
   *"In previous versions of Verdict, it was named 'Aspect Ratio Beta'."*
2. Il range accettabile dello **scaled Jacobian tetraedrico ha come estremo superiore √2/2 ≈ 0,7071,
   non 1**, benché il tet equilatero valga 1. Il "Normal Range" è [−√2/2, √2/2]. La tabella della
   norma è così: se un tool riporta scaled Jacobian tet > 0,707, sta usando un'altra normalizzazione.
3. Verdict avverte esplicitamente che il **collapse ratio non individua tutti gli sliver**:
   *"slivers can have arbitrarily high collapse ratios"*, quando il vertice a minima altezza proietta
   fuori dal triangolo opposto. Per gli sliver la metrica giusta è il **minimum dihedral angle**.

#### Metriche esaedriche richieste (Verdict §7)

Notazione: X₁, X₂, X₃ sono gli **assi principali** dell'esaedro
(X₁ = (P₁−P₀)+(P₂−P₃)+(P₅−P₄)+(P₆−P₇), e cicliche); X_fg sono le **derivate incrociate**
(X₁₂ = (P₂−P₃)−(P₁−P₀)+(P₆−P₇)−(P₅−P₄), e cicliche). Aᵢ sono le 9 matrici Jacobiane 3×3 costruite
sui vettori spigolo agli 8 angoli più quella sugli assi principali; α̂ᵢ è il determinante della
versione **normalizzata** (colonne divise per la propria norma).

| Metrica | Formula | Range accettabile | Cubo unitario |
|---|---|---|---|
| **scaled Jacobian** | q = min_{i∈0..8} α̂ᵢ (min. determinante Jacobiano normalizzato, agli 8 angoli + centro) | **[0,5, 1]** | 1 |
| **skew** | q = max( \|X̂₁·X̂₂\|, \|X̂₁·X̂₃\|, \|X̂₂·X̂₃\| ), con X̂ᵢ = Xᵢ/\|Xᵢ\| | **[0, 0,5]** | 0 |
| **taper** | T_fg = \|X_fg\| / min(\|X_f\|, \|X_g\|); q = max(T₁₂, T₁₃, T₂₃) | **[0, 0,5]** | 0 |
| **diagonal** | q = D_min / D_max sulle 4 diagonali | [0,65, 1] | 1 |
| **stretch** | q = √3 · L_min / D_max | [0,25, 1] | 1 |

Tutte **[V]**.

**Provenienza delle definizioni Verdict** (bibliografia del report, utile per citare l'origine):
`aspect gamma`, `radius ratio`, `volume` ← Parthasarathy, V. N. et al. (1993), *A comparison of
tetrahedron quality measures*, **Finite Elements in Analysis and Design**, 15:255–261;
`aspect ratio` ← Frey, P. J. & George, P.-L. (2000), *Mesh Generation*, Hermes Science;
`aspect Frobenius`, `condition`, `scaled Jacobian` ← Knupp, P. (2000), *Achieving finite element mesh
quality via optimization of the Jacobian matrix norm and associated quantities*, **IJNME**,
48:1165–1185; `shape`, `relative size` ← Knupp, P. (2003), *Algebraic mesh quality metrics for
unstructured initial meshes*, **FEAD**, 39:217–241; `aspect delta`, `collapse ratio` ← MSC.PATRAN
Reference Manual vol. 3 (2003); `skew`, `taper` ← Taylor, L. M. & Flanagan, D. P. (1989),
*Pronto3D*, SAND87-1912. Tutte **[V]** — lette nella sezione References di SAND2007-1751.

### 3.2 Radius-edge ratio (Shewchuk) e le garanzie del Delaunay refinement

**Definizione.** Il **radius-edge ratio** ρ(τ) di un tetraedro è il rapporto fra il **raggio della
sfera circoscritta** R e la **lunghezza dello spigolo più corto** d:

    ρ = R / d_min

Minimo teorico ρ = √6/4 ≈ 0,612, raggiunto dal tetraedro regolare. [V-sec — riportato nella
documentazione TetGen/letteratura; **non l'ho letto sul paper di Shewchuk**, il server
people.eecs.berkeley.edu era irraggiungibile in questa sessione (302 verso una pagina di incidente)]

**Riferimenti da citare:**
- Shewchuk, J. R. (1998), *Tetrahedral Mesh Generation by Delaunay Refinement*, Proc. 14th Annual
  Symposium on Computational Geometry (SoCG '98), ACM, pp. 86–95,
  DOI [10.1145/276884.276894](https://doi.org/10.1145/276884.276894). [V-sec]
- Shewchuk, J. R. (2002), *What Is a Good Linear Finite Element? Interpolation, Conditioning,
  Anisotropy, and Quality Measures*, Proc. 11th International Meshing Roundtable / Technical Report,
  University of California at Berkeley. [V-sec]

**Cosa garantisce.** Gli algoritmi di Delaunay refinement inseriscono vertici finché ogni tetraedro
non rispetta il bound sul radius-edge ratio. **Cosa NON garantisce: gli sliver.** Uno sliver è un
tetraedro con i quattro vertici quasi complanari, disposti a "aquilone", con **angoli diedri
patologicamente piccoli ma radius-edge ratio piccolo** — cioè *accettabile* secondo il criterio.
Il criterio radius-edge è cieco agli sliver **per costruzione**. [V-sec]

**Conferma indipendente sulla documentazione TetGen** (fonte primaria del generatore):
Si, H. (2015), *TetGen, a Delaunay-Based Quality Tetrahedral Mesh Generator*, **ACM Transactions on
Mathematical Software**, 41(2), art. 11, DOI [10.1145/2629697](https://doi.org/10.1145/2629697).
Manuale: <https://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html>. [V]
- `-q` controlla **due** parametri: il **radius-edge ratio massimo, default 2,0**, e l'**angolo diedro
  minimo, default 0° (nessun vincolo)**. Sintassi `-q[radius-edge]/[dihedral]`, es. `-q1.2/10`.
- Il manuale dichiara il limite verbatim: *"If there are sharp features in the PLC, TetGen will
  ensure the desired quality constraints on most of the tetrahedra, but leave some bad-quality
  tetrahedra in the final mesh. Usually, they are near the sharp features."*
- **Conseguenza operativa:** chiedere `-q` senza il secondo parametro **non impone alcun vincolo sugli
  angoli diedri**, quindi non esclude gli sliver. È il default. [V]

### 3.3 Soglie documentate dai codici commerciali

#### Abaqus/CAE — criteri di verifica mesh
Fonte: *Abaqus/CAE User's Manual*, "Verifying your mesh" / "Verifying element quality", Tabella 17–2.
Mirror consultato: <https://ceae-server.colorado.edu/v2016/books/usi/pt03ch17s06s01.html>. [V]

Default per tetraedri:
- **shape factor: 0,0001** (evidenzia gli elementi sotto questo valore);
- **small face corner angle: 5°**;
- **large face corner angle: 170°**;
- **aspect ratio: 10** (definito come rapporto fra spigolo più lungo e più corto);
- **geometric deviation factor: 0,2**.

Definizione dello **shape factor tetraedrico** (verbatim dal manuale): il volume dell'elemento diviso
per *"the volume of an equilateral tetrahedron with the same circumradius as the element"*; vale 0
per l'elemento degenere, 1 per l'ottimo. Il criterio shape factor è disponibile **solo** per triangoli
e tetraedri. [V]

> **Nota critica per la tesi.** Il default di shape factor 0,0001 è **quattro ordini di grandezza sotto
> l'ottimo**: è una soglia di *degenerazione*, non di *qualità*. Superare la verifica mesh di
> Abaqus/CAE non significa avere una mesh buona. [INF]

#### ANSYS — mesh metrics
Fonte: *Ansys Meshing User's Guide*, pagine pubbliche `msh_Element_Quality_Metric.html` e la pagina
Skewness della documentazione Discovery/SpaceClaim v251. [V]

**Element Quality** — metrica composita in [0, 1], 1 = perfetto, 0 = degenere:

    3D:  Quality = C · V / [ Σ (lunghezza spigolo)² ]^(3/2)

con costanti C: **tetraedro 124,70765802**, esaedro 41,56921938, cuneo 62,35382905, piramide 96,
triangolo 6,92820323, quadrangolo 4,0. [V]
(Per il tetraedro questa è, a meno della normalizzazione, la **metrica di Joe–Liu**
η = 12·(3V)^(2/3)/Σl²_ij. **[INF — l'equivalenza non è dichiarata nella doc ANSYS che ho letto]**)

**Skewness** — *"determines how close to ideal (equilateral or equiangular) a face or cell is"*;
0 = equilatero, 1 = degenere. Due metodi:
- **Equilateral-Volume-Based Skewness** (triangoli e tetraedri): confronta il volume della cella con
  quello della cella equilatera avente **lo stesso circumraggio**;
- **Normalized Equiangular Skewness**: (θ_max − θ_min)/(θ_e − θ_min), con θ_e = 60° per triangoli,
  90° per quadrangoli.

**Tabella ufficiale skewness → qualità** [V]:

| Skewness | Giudizio |
|---|---|
| 0 | equilatero |
| >0 – 0,25 | excellent |
| 0,25 – 0,5 | good |
| 0,5 – 0,75 | fair |
| 0,75 – 0,9 | poor |
| 0,9 – <1 | **bad (sliver)** |
| 1 | degenerate |

La doc ANSYS aggiunge che mesh di qualità raggiungono tipicamente skewness ≈ 0,1 in 2D e **≈ 0,4 in
3D**. [V]

> Osservazione: la definizione ANSYS "equilateral-volume-based skewness" (volume vs cella equilatera
> con stesso circumraggio) è **la stessa idea dello shape factor Abaqus**, riscalata al contrario
> (0 buono vs 1 buono). Stessa geometria, due nomi, due orientamenti di scala. [INF]

#### Gmsh / HXT — attenzione al nome `gamma`
Fonte: Marot, C. & Remacle, J.-F. (2020), *Quality tetrahedral mesh generation with HXT*,
arXiv:2008.08508, <https://arxiv.org/abs/2008.08508>, Appendice A.3. [V — PDF letto]

    γ = √24 · 3V / ( |e_max| · (A₁+A₂+A₃+A₄) )  =  √24 · r_in / |e_max|      [r_in = 3V / ΣA_i]

verbatim dal paper: *"where V is the volume of the tetrahedron, |e_max| is the length of the longest
edge, A_i is the area of the i-th face and r_in is the inradius of the tetrahedron. The factor √24 is
added such that the optimal tetrahedron, which is a regular tetrahedron, has a quality γ = 1."*

**Soglia operativa dichiarata: Gmsh e HXT puntano a un γ minimo = 0,35.** [V]

Altre metriche Gmsh: **SICN** = inverso (con segno) del numero di condizionamento in norma di
Frobenius della mappa verso l'elemento di riferimento, range [−1, 1], negativo = elemento invalido;
**eta** = metrica di Joe–Liu; **SIGE** = inverso con segno dell'errore sul gradiente. [V-sec]

> **Questo è il caso da citare in tesi come esempio di collisione di nomi**: `gamma` in Gmsh è
> r_in/e_max normalizzato (grande = buono, 1 = ottimo), `aspect gamma` in Verdict è
> RMS(edge)³·√2/(12V) (**piccolo = buono**, 1 = ottimo, cresce verso l'infinito), e la "gamma" di
> altre librerie è ancora il rapporto inscritta/circoscritta. Tre formule, un nome. [V — le prime due
> lette su fonte; la terza è [INF]]

---

## 4. Il problema noto dei tetraedri lineari (C3D4)

### 4.1 Cosa dice il manuale Abaqus, verbatim

Fonte: *Abaqus Analysis User's Guide*, "Solid (continuum) elements", sezioni *Choosing between
first- and second-order elements*, *Choosing between triangles/tetrahedra and quadrilaterals/hexahedra*,
*Tetrahedral and wedge elements*, *Shear and volumetric locking*.
Mirror consultati (stesso contenuto, byte-identici): <https://abaqus-docs.mit.edu/2017/English/SIMACAEELMRefMap/simaelm-c-solidcont.htm>
e <https://abaqus.uclouvain.be/English/SIMACAEELMRefMap/simaelm-c-solidcont.htm>. [V]

> First-order triangular and tetrahedral elements should be avoided as much as possible in stress
> analysis problems; the elements are overly stiff and exhibit slow convergence with mesh refinement,
> which is especially a problem with first-order tetrahedral elements. If they are required, an
> extremely fine mesh may be needed to obtain results of sufficient accuracy.

> First-order triangles and tetrahedra are usually overly stiff, and extremely fine meshes are
> required to obtain accurate results. As mentioned earlier, fully integrated first-order triangles
> and tetrahedra in Abaqus/Standard also exhibit volumetric locking in incompressible problems. As a
> rule, these elements should not be used except as filler elements in noncritical areas.

> For stress/displacement analyses the first-order tetrahedral element C3D4 is a constant stress
> tetrahedron, which should be avoided as much as possible; the element exhibits slow convergence
> with mesh refinement. This element provides accurate results only in general cases with very fine
> meshing. Therefore, C3D4 is recommended only for filling in regions of low stress gradient in
> meshes of C3D8 or C3D8R elements, when the geometry precludes the use of C3D8 or C3D8R elements
> throughout the model. For tetrahedral element meshes the second-order or the modified tetrahedral
> elements, C3D10 or C3D10M, should be used.

Sul locking volumetrico, sempre verbatim:

> Volumetric locking occurs in fully integrated elements when the material behavior is (almost)
> incompressible. Spurious pressure stresses develop at the integration points, causing an element to
> behave too stiffly for deformations that should cause no volume changes.

> However, the first-order, fully integrated quadrilaterals and hexahedra use selectively reduced
> integration (reduced integration on the volumetric terms). Therefore, these elements do not lock
> with almost incompressible materials.

E su C3D10M:

> Modified triangular and tetrahedral elements work well in contact, exhibit minimal shear and
> volumetric locking, and are robust during finite deformation.

Diagnostica suggerita dal manuale, citabile come procedura: *"If volumetric locking is suspected,
check the pressure stress at the integration points [...] If the pressure values show a checkerboard
pattern, changing significantly from one integration point to the next, volumetric locking is
occurring."* [V]

**Punto da tenere fermo, verificato:** il C3D8 **non** locca in quasi-incomprimibile perché usa
integrazione selettivamente ridotta sui termini volumetrici; il C3D4 sì. Il confronto tet-vs-hex sul
locking **non** è "tetraedro vs esaedro" in astratto, è "simplesso a deformazione costante e
integrazione piena" vs "esaedro con integrazione selettiva". [V per i fatti, INF per la formulazione]

### 4.2 Origine teorica del locking dei simplessi

Nagtegaal, J. C., Parks, D. M. & Rice, J. R. (1974), *On numerically accurate finite element
solutions in the fully plastic range*, **Computer Methods in Applied Mechanics and Engineering**,
4(2):153–177, DOI [10.1016/0045-7825(74)90032-2](https://doi.org/10.1016/0045-7825(74)90032-2).
PDF aperto: <http://esag.harvard.edu/rice/050_NagtegaalParksRice_FE_CMAME74.pdf>. [V-sec]

Argomento: i campi di deformazione incrementale degli elementi tipici 2D e 3D sono **fortemente
vincolati** al carico limite; il vincolo di incomprimibilità impone un numero di condizioni
cinematiche sproporzionato ai gradi di libertà disponibili, e la risposta risulta troppo rigida —
le soluzioni FE "often exceed the limit load by substantial amounts". Il paper dà un **criterio
generale (constraint counting) per testare mesh con celle ripetute topologicamente simili** e conclude
che solo pochi tipi/disposizioni convenzionali sono adatti al regime completamente plastico. [V-sec —
abstract; il constraint ratio specifico per il tet lineare **non** l'ho letto sul PDF]

Riferimento complementare standard: Hughes, T. J. R. (1987/2000), *The Finite Element Method: Linear
Static and Dynamic Finite Element Analysis*, Prentice-Hall / Dover — trattazione del constraint ratio
e del locking. Citato da Benzley et al. 1995 come rif. [3] per il "mesh locking due to material
incompressibility". [V — la citazione dentro Benzley è verificata; il contenuto di Hughes no]

### 4.3 Numeri — quanto sbaglia un tet lineare su una mensola

**Fonte primaria con numeri, letta integralmente:**
Benzley, S. E., Perry, E., Merkley, K., Clark, B. & Sjaardema, G. (1995), *A Comparison of All
Hexahedral and All Tetrahedral Finite Element Meshes for Elastic and Elasto-Plastic Analysis*,
Proceedings of the 4th International Meshing Roundtable, Sandia National Laboratories, pp. 179–191.
PDF: <https://coreform.com/papers/hex_tet_comparison.pdf>. [V]

**Modello:** barra a sezione rettangolare 1×1×10, incastrata a un'estremità, E = 10 000 000,
ν = 0,3 e 0,49, ρ = 0,1. Mesh regolari 2×2 e 4×4 in sezione. Sigle: LH = hex lineari,
QH = hex quadratici, LT = tet lineari, QT = tet quadratici. [V]

**Soluzioni analitiche di riferimento** (teoria della trave / Timoshenko-Goodier):
flessione — spostamento 0,000125, tensione flessionale 30,0 (entrambe indipendenti da ν);
torsione — tensione tangenziale 6,8; spostamento rotazionale 0,000003269 (ν = 0,3) e
0,000003747 (ν = 0,49). [V]

**Tabella 2 — errori su mensola in flessione, ν = 0,3** [V]

| DOF | tipo | errore spostamento | errore tensione |
|---|---|---|---|
| 567 | LH | 0,72% | 0,00% |
| **666** | **LT** | **31,48%** | **21,23%** |
| 1863 | QH | 0,24% | 0,01% |
| 3075 | LH | 0,08% | 0,00% |
| **3615** | **LT** | **10,48%** | **21,00%** |
| 3894 | QT | 0,24% | 0,33% |
| 10995 | QH | 0,01% | 0,01% |
| 23613 | QT | 0,01% | 0,01% |

**Tabella 2 (seguito) — stessa mensola, ν = 0,49 (quasi incomprimibile)** [V]

| DOF | tipo | errore spostamento | errore tensione |
|---|---|---|---|
| 567 | LH | 6,56% | 0,01% |
| **666** | **LT** | **71,68%** | **66,77%** |
| 1863 | QH | 5,36% | 0,01% |
| 3075 | LH | 3,20% | 0,01% |
| **3615** | **LT** | **44,80%** | **35,23%** |
| 3894 | QT | 4,80% | 0,10% |
| 10995 | QH | 2,88% | 0,01% |
| 23613 | QT | 2,48% | 0,23% |

**Tabella 3 — torsione, ν = 0,3** [V]: LT 50,81% (666 DOF) e 22,39% (3615 DOF) sullo spostamento,
77,82% e 38,40% sulla tensione; LH 15,65% / 5,26% spostamento; QT 3,32% / 0,76%.

**Tabella 4 — frequenze proprie, ν = 0,3** [V]: modo flessionale (analitico 317,5 Hz) — LT 20,28%
a 666 DOF, 0,28% a 3615 DOF; modo torsionale (approssimato 2614 Hz) — LT 41,68% a 666 DOF,
0,36% a 3615 DOF.

**Autovalori della matrice di rigidezza di un cubo unitario** (E = 30 000 000, ν = 0,3): un cubo
meshato con **5 tetraedri simplessi** ha **sistematicamente autovalori maggiori** dello stesso cubo con
un esaedro — primo modo deformativo (autovalore 7): hex Nastran 1,667·10⁷, hex isoparametrico
1,923·10⁷, **5 tet 5,315·10⁷** (≈ 3× il Nastran). Poiché il FEM basato su spostamenti
**sovrastima** la rigidezza, autovalore più alto = elemento peggiore. [V]

I valori dell'**autovalore 21** sono in **quarantena**: le due letture in archivio sono
incompatibili fra loro. [`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md) § 2.3 «Quanto
sbagliano — numeri pubblicati» riportava tre colonne — 11,538 (hex Nastran) / 11,538 (hex
isoparametrico) / **38,276** (5 tet); [`ricerca-vv-standard.md`](ricerca-vv-standard.md) § 4.3
(questo documento) ne riportava due — 11,538 vs 13,915 e 37,500 vs 46,085 (×10⁷). Entrambe le
letture sono **non riscontrabili sulla fonte, da rileggere** sulla Tab. 1 del paper, che non è
versionato nel repository: fino ad allora nessuna delle due va citata.

**Conclusioni testuali degli autori** [V]:

> Note that in all cases, the linear tetrahedron element (LT) produces the maximum error.

> The evaluation substantiates a strong preference for linear displacement hexagonal finite elements
> when compared solely to linear tetrahedral finite elements. The use of quadratic displacement
> formulated finite elements significantly improve the performance of the tetrahedral as well as the
> hexahedral elements. The nonlinear elasto-plastic comparison indicates that linear hexahedral
> elements may be superior to even quadratic tetrahedrons when shear stress is dominant.

Gli autori avvertono anche che il vantaggio del LH in flessione è **amplificato dall'integrazione
selettiva** dell'elemento Nastran usato, mentre in torsione (dove l'integrazione selettiva non entra
in gioco) LH resta comunque superiore a LT. [V]

### 4.4 Il contrappunto moderno — quadratic tet ≈ hex

Schneider, T., Hu, Y., Gao, X., Dumas, J., Zorin, D. & Panozzo, D. (2022), *A Large-Scale Comparison
of Tetrahedral and Hexahedral Elements for Solving Elliptic PDEs with the Finite Element Method*,
**ACM Transactions on Graphics**, 41(3), art. 23, DOI [10.1145/3508372](https://doi.org/10.1145/3508372);
preprint <https://arxiv.org/abs/1903.09332>. [V-sec]

Conclusione riportata: per elementi di tipo Lagrange, **i tet lineari vanno male, ma i tet quadratici
sono equivalenti o migliori degli esaedri** sull'insieme di problemi e con i generatori di mesh
attualmente disponibili. [V-sec — abstract]

Riferimento storico citato dentro Benzley 1995 e ancora valido come conferma:
Cifuentes, A. O. & Kalbag, A. (1992), *A performance study of tetrahedral and hexahedral elements in
3-D finite element structural analysis*, **Finite Elements in Analysis and Design**, 12(3–4):313–318
— conclude che i tet **quadratici** sono equivalenti agli hex bilineari per accuratezza e tempo CPU. [V-sec]

### 4.5 Sintesi difendibile in tesi

Affermazioni che questa raccolta sostiene con fonte: [V dove indicato]
1. Il C3D4 è a tensione costante e il manuale del produttore ne **sconsiglia esplicitamente** l'uso
   fuori dalle zone di riempimento a basso gradiente. [V]
2. Su mensola in flessione, un tet lineare sbaglia **~31% sullo spostamento e ~21% sulla tensione**
   a parità di ordine di grandezza di DOF con un hex lineare che sbaglia <1%. Raffinando ×5,4 in DOF
   l'errore in spostamento scende a ~10% ma **quello in tensione resta al 21%**. [V]
3. Con ν = 0,49 gli stessi errori salgono a **~72% / ~67%** (666 DOF) e **~45% / ~35%** (3615 DOF):
   è il locking volumetrico, e la degradazione è di gran lunga maggiore per LT che per LH o QT. [V]
4. Il rimedio documentato dal produttore è **C3D10 o C3D10M**, non il raffinamento del C3D4. [V]
5. Sui benchmark NAFEMS pubblicati dal produttore (LE10, FV52) **non esistono risultati C3D4**: il
   costruttore non lo mette nemmeno nelle tabelle di verifica. [V — assenza osservata direttamente]

---

## 5. Tabella riassuntiva: benchmark → cosa verifica → valore di riferimento → fonte

| Benchmark / prova | Cosa verifica | Valore di riferimento | Fonte |
|---|---|---|---|
| **Patch test forma C** (Irons) | consistency + stability dell'elemento; condizione **necessaria** di convergenza | campo lineare riprodotto esattamente (errore ~ precisione macchina), tensione costante in tutti gli elementi; nessun autovalore nullo spurio | Taylor, Simo, Zienkiewicz & Chan 1986, IJNME 22:39–62, DOI 10.1002/nme.1620220105 |
| **NAFEMS LE1** — elliptic membrane (2D, plane stress) | tensione di bordo in stato piano; E=210 GPa, ν=0,3, pressione 10 MPa | **σ_y = 92,7 MPa** nel punto D | NAFEMS TNSB Rev.3 (1990); valore in ESRD Benchmarks Guide 2018, p. 4 |
| **NAFEMS LE2** — cylindrical shell bending patch test | flessione di guscio; settore 30°, T=10 mm, M=1000 N·mm/lungh. | **σ tangenziale superficie esterna = 60 MPa** | idem, p. 8 |
| **NAFEMS LE10** — thick plate under pressure (**3D solido**) | tensione diretta in piastra spessa; E=210 GPa, ν=0,3, p=1,0 MPa | **σ_yy = −5,38 MPa** nel punto D | NAFEMS TNSB Rev.3 (1990); Abaqus Benchmarks Guide LE10; ESRD p. 29 |
| **NAFEMS LE11** — solid cylinder/taper/sphere (**3D solido, termico**) | tensione da gradiente termico; E=210 GPa, ν=0,3, α=2,3e−4/°C, Δθ=√(x²+y²)+z | **σ_zz = −105 MPa** nel punto A | NAFEMS TNSB Rev.3 (1990); Abaqus Benchmarks Guide LE11; ESRD p. 32 |
| **NAFEMS FV32** — cantilevered tapered membrane (2D) | analisi modale su mesh distorta; E=200 GPa, ν=0,3, ρ=8000 kg/m³ | **44,623, 130,03, 162,7, 246,05, 379,9, 391,44 Hz** (modi 1–6) | Abbassian, Dawswell & Knowles 1987; valori in TechSoft3D HOOPS benchmark report |
| **NAFEMS FV52 / FV51** — simply supported solid square plate (**3D solido**) | analisi modale con elementi solidi, con 3 moti rigidi; t=1,0 m, E=200 GPa, ν=0,3, ρ=8000 | Abaqus: **44,092 / 106,66 / 106,66 / 156,23 / 193,58 / 200,13 / 200,13 Hz** (modi 4–10). TechSoft3D: **45,897 / 109,44 / 109,44 / 167,89 / 193,59 / 206,19 / 206,19 Hz**. **Discrepanza sciolta il 26/08/2026** (vedi [`benchmark-nafems.md`](benchmark-nafems.md)): il numero è **FV52**, «FV51» è un errore di TechSoft3D. I due set sono i due target che NAFEMS pubblica: **45,897 = soluzione in forma chiusa**, **44,092 = numerico**. **Usare 44,092**, contro cui Abaqus tabula gli errori per tipo di elemento. Non mescolarli. | NAFEMS **TNSB Rev.3 (1990)**, non Abbassian 1987; Abaqus Benchmarks Guide FV52; NAFEMS pubguide/benchmarks Page5 |
| **MMS su elasticità 3D** | **ordine di accuratezza osservato** del solutore, non l'errore assoluto | ordine osservato **2 sullo spostamento** in raffinamento di mesh (Abaqus/Standard, lin. elastico / neo-Hookean / Hencky) | Aycock, Rebelo & Craven 2020, Computers & Structures 229:106175, DOI 10.1016/j.compstruc.2019.106175 |
| **GCI / Richardson** | incertezza numerica residua della griglia fine | banda GCI in %; F_s = 1,25 (≥3 griglie) o 3,0 (2 griglie); range asintotico se GCI₂₃ ≈ r^p·GCI₁₂ | Roache 1994, JFE 116:405–413; Celik et al. 2008, JFE 130:078001; NASA NPARC "Examining Spatial (Grid) Convergence" |
| **Mensola Benzley** — flessione, ν=0,3 | penalità di rigidezza del tet lineare | analitico: spost. 1,25e−4, σ = 30,0. Errore **LT 31,48% / 21,23%** (666 DOF) vs **LH 0,72% / 0,00%** (567 DOF) | Benzley et al. 1995, Proc. 4th IMR, Tab. 2 |
| **Mensola Benzley** — flessione, ν=0,49 | locking volumetrico | Errore **LT 71,68% / 66,77%** (666 DOF), **44,80% / 35,23%** (3615 DOF) | idem |
| **Mensola Benzley** — torsione, ν=0,3 | rigidezza a taglio senza il vantaggio dell'integrazione selettiva | analitico τ = 6,8 (**sospetto**: vedi [`mensola-benzley.md`](mensola-benzley.md) §6, il paper non scioglie un fattore 2 fra tensione e spostamento torsionali). **LT 50,81% spost. / 77,82% tens.** (666 DOF); **LH 15,65% spost.** (567 DOF), tensione **da rileggere sulla fonte** | idem, Tab. 3 |
| **Autovalori cubo unitario** | sovrastima diretta di rigidezza del simplesso | primo modo deformativo: hex 1,667e7 vs **5 tet 5,315e7** | idem, Tab. 1 |
| **Verdict — min dihedral angle** | sliver detection (l'unica metrica del set che li vede) | accettabile **[40°, 70,5288°]** | Stimpson et al. 2007, SAND2007-1751, §6.10 |
| **Verdict — tet scaled Jacobian** | validità/qualità algebrica | accettabile **[0,5, √2/2 ≈ 0,7071]** | idem, §6.13 |
| **Verdict — tet radius ratio** (= vecchio `aspect_beta`) | R/(3r) | accettabile **[1, 3]** | idem, §6.11 |
| **Verdict — tet aspect ratio** | **L_max/(2√6·r)** | accettabile **[1, 3]** | idem, §6.5 |
| **Verdict — hex scaled Jacobian / skew / taper** | qualità esaedri | **[0,5, 1] / [0, 0,5] / [0, 0,5]** | idem, §7.11, §7.16, §7.18 |
| **TetGen `-q`** | bound Delaunay refinement | radius-edge ratio default **2,0**; angolo diedro minimo default **0° (nessun vincolo)** | Si 2015, ACM TOMS 41(2):11; manuale TetGen 1.5 §005 |
| **Gmsh/HXT `gamma`** | qualità tet nel generatore usato | **γ = √24·r_in/\|e_max\|**, target minimo **0,35** | Marot & Remacle 2020, arXiv:2008.08508, App. A.3 |
| **Abaqus/CAE mesh verification** | soglie di *degenerazione*, non di qualità | shape factor **0,0001**, angoli faccia **5°/170°**, aspect ratio **10**, geom. deviation **0,2** | Abaqus/CAE User's Manual, Tab. 17–2 |
| **ANSYS skewness** | qualità cella | excellent ≤0,25, good ≤0,5, fair ≤0,75, poor ≤0,9, **bad/sliver <1**, degenerate =1; mesh 3D buone ≈0,4 | Ansys Meshing User's Guide, pagina Skewness |
| **ANSYS Element Quality** | metrica composita [0,1] | 3D: **C·V/(Σ L²)^{3/2}**, C_tet = **124,70765802**, C_hex = 41,56921938 | Ansys Meshing User's Guide, Element Quality Metric |

---

## 6. Cosa NON ho trovato pubblicato in chiaro

Elenco esplicito, per non lasciare buchi che qualcuno riempia a memoria:

1. **Testo integrale di ASME V&V 10-2019, V&V 10.1-2012, V&V 40-2018, AIAA G-077-1998.** Tutti a
   pagamento. Contenuto ricostruito da Schwer 2007 (autore = Chair del comitato) e dalle pagine
   editore. Le *metriche di validazione specifiche* eventualmente prescritte da V&V 10-2019 (edizione
   2019, non 2006) **non le ho verificate**.
2. **Geometrie complete e quotate dei benchmark NAFEMS LE1/LE2/LE10/LE11 e FV32/FV52.** Ho materiale,
   vincoli, carichi e target; le **dimensioni** stanno nelle figure delle pubblicazioni NAFEMS e dei
   manuali, non nel testo estraibile.
3. **Risultati C3D4 su qualunque benchmark NAFEMS** nei manuali Abaqus consultati. Assenti.
4. **Il secondo set di frequenze target NAFEMS per FV52/FV51**, che spiegherebbe la discrepanza
   44,092 vs 45,897 Hz. Ipotesi non confermata.
5. **Il paper di Shewchuk** — server Berkeley irraggiungibile in questa sessione. Il bound √6/4 e la
   caratterizzazione degli sliver provengono da fonti che lo citano, non dall'originale.
6. **Il testo di Celik et al. 2008** — la ripubblicazione NRC risponde 403. La formula
   `GCI = 1.25·e_a·r^p/(r^p−1)` è **da confermare sul PDF** prima di citarla.
7. **La formula del constraint ratio di Nagtegaal-Parks-Rice specifica per il tetraedro lineare.**
   Ho letto solo l'abstract.
8. **Una norma ISO/EN di qualificazione del software FEM strutturale in ambito civile europeo.** Non
   risulta esistere un equivalente di NQA-1 Subpart 2.7. Gli Eurocodici non la coprono.
9. **Le varianti A/B/C del patch test parola per parola dal paper originale del 1986.** La descrizione
   in §2.4 viene da una sintesi che riporta il contenuto di Taylor et al., non dal PDF.

---

## 7. Bibliografia consolidata

**Norme**
1. ASME V&V 10-2019 (R2025), *Standard for Verification and Validation in Computational Solid Mechanics*, ASME, New York.
2. ASME V&V 10-2006, *Guide for Verification and Validation in Computational Solid Mechanics*, ASME, New York.
3. ASME V&V 10.1-2012 (R2022), *An Illustration of the Concepts of Verification and Validation in Computational Solid Mechanics*, ASME. ISBN 978-0-7918-3415-2.
4. ASME V&V 40-2018, *Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices*, ASME.
5. AIAA G-077-1998 (R2002), *Guide for the Verification and Validation of Computational Fluid Dynamics Simulations*, AIAA, Reston VA.
6. ASME NQA-1, *Quality Assurance Requirements for Nuclear Facility Applications*, Part II, Subpart 2.7 (ed. 2024), ASME.
7. NAFEMS (1990), *The Standard NAFEMS Benchmarks*, TNSB Rev. 3, NAFEMS, Glasgow.
8. Abbassian, F., Dawswell, D. J. & Knowles, N. C. (1987), *Selected Benchmarks for Natural Frequency Analysis*, NAFEMS, Glasgow.

**Articoli e report**
9. Schwer, L. E. (2007), Engineering with Computers 23(4):245–252. DOI 10.1007/s00366-007-0072-z.
10. Oberkampf, W. L. & Trucano, T. G. (2002), Progress in Aerospace Sciences 38(3):209–272. DOI 10.1016/S0376-0421(02)00005-2. (Sandia SAND2002-0529.)
11. Roache, P. J. (1994), J. Fluids Eng. 116(3):405–413. DOI 10.1115/1.2910291.
12. Roache, P. J. (1998), *Verification and Validation in Computational Science and Engineering*, Hermosa.
13. Roache, P. J. (2002), J. Fluids Eng. 124(1):4–10. DOI 10.1115/1.1436090.
14. Salari, K. & Knupp, P. (2000), SAND2000-1444, Sandia National Laboratories.
15. Knupp, P. & Salari, K. (2003), *Verification of Computer Codes in Computational Science and Engineering*, Chapman & Hall/CRC.
16. Celik, I. B. et al. (2008), J. Fluids Eng. 130(7):078001. DOI 10.1115/1.2960953.
17. Irons, B. M. & Razzaque, A. (1972), in Aziz (ed.), *The Mathematical Foundations of the FEM*, Academic Press, pp. 557–587.
18. Taylor, R. L., Simo, J. C., Zienkiewicz, O. C. & Chan, A. C. H. (1986), IJNME 22(1):39–62. DOI 10.1002/nme.1620220105.
19. Zienkiewicz, O. C. & Taylor, R. L. (1986), IJNME 23(10):1873–1883. DOI 10.1002/nme.1620231007.
20. Stimpson, C. J., Ernst, C. D., Knupp, P., Pébay, P. P. & Thompson, D. (2007), SAND2007-1751, Sandia National Laboratories.
21. Parthasarathy, V. N. et al. (1993), Finite Elements in Analysis and Design 15:255–261.
22. Knupp, P. (2000), IJNME 48:1165–1185.
23. Knupp, P. (2003), Finite Elements in Analysis and Design 39:217–241.
24. Frey, P. J. & George, P.-L. (2000), *Mesh Generation*, Hermes Science.
25. Shewchuk, J. R. (1998), Proc. 14th SoCG, ACM, pp. 86–95. DOI 10.1145/276884.276894.
26. Shewchuk, J. R. (2002), *What Is a Good Linear Finite Element?*, Proc. 11th International Meshing Roundtable.
27. Si, H. (2015), ACM Trans. Math. Softw. 41(2), art. 11. DOI 10.1145/2629697.
28. Marot, C. & Remacle, J.-F. (2020), *Quality tetrahedral mesh generation with HXT*, arXiv:2008.08508.
29. Nagtegaal, J. C., Parks, D. M. & Rice, J. R. (1974), CMAME 4(2):153–177. DOI 10.1016/0045-7825(74)90032-2.
30. Hughes, T. J. R. (1987), *The Finite Element Method*, Prentice-Hall (rist. Dover 2000).
31. Benzley, S. E., Perry, E., Merkley, K., Clark, B. & Sjaardema, G. (1995), Proc. 4th International Meshing Roundtable, pp. 179–191.
32. Cifuentes, A. O. & Kalbag, A. (1992), Finite Elements in Analysis and Design 12(3–4):313–318.
33. Schneider, T. et al. (2022), ACM Trans. Graph. 41(3), art. 23. DOI 10.1145/3508372.
34. Aycock, K. I., Rebelo, N. & Craven, B. A. (2020), Computers & Structures 229:106175. DOI 10.1016/j.compstruc.2019.106175.

**Manuali di codice**
35. Dassault Systèmes, *Abaqus Analysis User's Guide*, "Solid (continuum) elements". <https://abaqus-docs.mit.edu/2017/English/SIMACAEELMRefMap/simaelm-c-solidcont.htm>
36. Dassault Systèmes, *Abaqus Benchmarks Guide*, LE10 / LE11 / FV52. <https://abaqus-docs.mit.edu/2017/English/SIMACAEBMKRefMap/simabmk-m-NAFEMSBenchmarks-sb.htm>
37. Dassault Systèmes, *Abaqus/CAE User's Manual*, "Verifying your mesh", Tab. 17–2. <https://ceae-server.colorado.edu/v2016/books/usi/pt03ch17s06s01.html>
38. Ansys Inc., *Ansys Meshing User's Guide*, Mesh Metrics / Element Quality / Skewness. <https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_msh/msh_metrics.html>
39. Si, H., *TetGen 1.5 User's Manual*, §"-q". <https://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html>
40. ESRD Inc. (2018), *Benchmarks Guide — The Standard NAFEMS Benchmarks: Linear Elastic Tests*. <https://www.esrd.com/wp-content/uploads/dlm_uploads/Benchmarks-Guide-Standard-NAFEMS-Benchmarks-Linear-Elastic-Tests.pdf>
41. TechSoft3D, *The Standard NAFEMS Benchmark Tests for HOOPS Solve*, v2.13.0. <https://docs.techsoft3d.com/hoops/mesh/_static/benchmark_reports/benchmark_results_2.13.0.pdf>
42. NASA Glenn / NPARC Alliance, *Examining Spatial (Grid) Convergence*. <https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html>
