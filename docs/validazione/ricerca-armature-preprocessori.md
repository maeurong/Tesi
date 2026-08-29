# Come i preprocessori strutturali fanno inserire le armature in una sezione

Ricerca sull'interfaccia e sul modello dei dati esposto all'utente dai programmi affini. Non riguarda il motore di calcolo.

**Provenienza.** cwd `/mnt/c/Users/mario/GitHub/Tesi`, repo `/mnt/c/Users/mario/GitHub/Tesi`, branch `main`, HEAD `787fdeb`, data 2026-08-28.
Fonti raccolte con `curl` (rete diretta) e con `WebFetch`. In questa macchina **non** sono disponibili `pdftotext`, `qpdf`, `pypdf`, `pdfminer`: il testo dei PDF è stato estratto con uno script Python di sola libreria standard (`zlib` per i flussi FlateDecode, RC4 a 40 bit per i PDF cifrati con security handler standard, rev. 2 — il manuale di Response-2000 è cifrato con password utente vuota). Lo script vive in `/tmp` e non è versionato: serviva solo a leggere le fonti.

**Marcatore di verifica.** Ogni voce porta uno di questi:

- **[L]** — *letto direttamente*: ho aperto la fonte primaria e le frasi citate sono trascritte da lì.
- **[P]** — *parziale*: la fonte primaria è stata aperta ma copre solo una parte di ciò che serviva.
- **[C]** — *solo citato*: la fonte primaria non è stata raggiunta; riporto ciò che dichiara il produttore altrove, oppure dichiaro l'assenza.

Le citazioni in inglese sono trascritte **verbatim** dai manuali, non tradotte, perché la forma esatta del nome di un campo è il dato che interessa.

---

## 1. Censimento dei programmi

### 1.1 Tabella compatta

| Programma | Che cosa offre per l'armatura di sezione | In che forma | Verifica |
|---|---|---|---|
| **SAP2000 / ETABS / CSiBridge — Section Designer** | Quattro *reinforcing shape*: `Single Bar`, `Line Pattern`, `Rectangular Pattern`, `Circular Pattern`. In più, le forme in calcestruzzo (Solid, Structural, Poly) portano un flag `Reinforcing` che genera automaticamente barre di bordo e barre d'angolo | Disegno col mouse sulla sezione + tasto destro sulla forma disegnata che apre `Shape Properties - Reinforcing` con i parametri numerici | **[L]** |
| **SAP2000 / ETABS — sezione telaio parametrica** | `Frame Section Property Reinforcement Data`: non disegno, ma form a campi. Colonna rettangolare o circolare, staffe `Ties` o `Spiral` | Form numerica, nessuna interazione grafica | **[L]** |
| **CSiCol** | "Add rebars of any size anywhere in the cross-section"; distribuzione delle barre "individually, in corners, in sides, peripherally, linearly and circularly" | Disegno + pattern | **[P]** (pagina prodotto ufficiale, non manuale) |
| **Response-2000** (Bentz, U. of Toronto) | *Quick Define Wizard* in 4 pagine + tre dialoghi separati: sezione, armatura longitudinale, armatura trasversale. Strati individuali o pattern (distribuiti e circolari) | Wizard + liste di strati (add / modify / delete), niente disegno col mouse | **[L]** |
| **XTRACT** (Chadwell, ex UCFyber; oggi TRC) | "Templates for Common Structural Shapes", "Ability to Define and Analyze Arbitrary Sections", "Automatic Fiber Mesh Generation", "'Remesher' Allows Modification of Discretized Sections" | Template + editor grafico; il dettaglio dei campi **non verificato** | **[P]** |
| **VecTor2 / FormWorks** (Vecchio, U. of Toronto) | Due strade nettamente separate: armatura **smeared** come componente del materiale calcestruzzo (percentuale), e armatura **discreta** come *reinforcement path* di elementi truss | Form a campi + percorsi definiti per vertici; nessun concetto di "barra nella sezione" | **[L]** |
| **STKO** (ASDEA Software, pre/post per OpenSees) | `Beam Fiber Section Editor`: si disegna la sezione come geometria CAD, si crea `Surface Fiber` per il calcestruzzo e `Make Punctual Fibers` per le barre | Disegno CAD nell'editor di sezione + dialogo con diametro, numero di barre per segmento, passo | **[L]** |
| **OpenSees Navigator** (Schellenberg, Yang — PEER/UC Berkeley) | GUI MATLAB con template per geometria, materiali, sezioni, elementi | Template a form; il dettaglio delle sezioni a fibre **non verificato** | **[C]** |
| **GiD** (CIMNE) | **Nulla di nativo.** Il *Reference Manual* v17 (388 pagine estratte, 73 945 righe di testo) contiene **zero** occorrenze di `reinforcement` e `rebar`, e zero di `concrete`. L'armatura esiste solo se la porta un *problem type* di terze parti | n/a | **[L]** |
| **Abaqus** (`*REBAR`, rebar layer, embedded region) | Tre meccanismi distinti: *rebar layers* in membrane/shell/surface (smeared), *rebar* nelle sezioni beam, ed *embedded elements* per i solidi | Tabella nell'editor di sezione (`Rebar Layers` dalla voce `Options`), oppure keyword | **[L]** su CAE e su §2.2.3–2.2.4 del manuale di analisi |
| **midas Civil** — `Section & Reinforcement` | Scheda `Reinforcement` accanto alla scheda `Section`: barre longitudinali definite per posizione lungo l'asta e per coordinate nella sezione | Tabella a righe | **[L]** |
| **SCIA Engineer** | Tre livelli dichiarati: *required*, *provided* (template teorico), *practical/user* (armatura reale). Template di armatura longitudinale e staffe per forma di sezione | Template + inserimento manuale grafico (`New reinforcement`, `New stirrups`, `New longitudinal bars`) | **[L]** sul tutorial ufficiale |
| **RC-SEC / "Sezioni in CA"** (GeoStru, italiano) | Quattro tipologie: *sezioni predefinite*, *sezioni generiche*, *sezioni rettangolari di pilastri*, *sezioni rettangolari di pareti*. Barre nei vertici, barre isolate, generazioni lineari di barre | Griglia numerica sincronizzata con finestra grafica; import da DXF | **[L]** sul manuale italiano ufficiale |
| **VcaSlu** (Gelfi, Università di Brescia — diffuso in ambito accademico italiano) | Sezione per rettangoli, trapezi, coordinate; circolare piena e cava; poligono regolare. Opzione `Solo Barre` | Griglia di coordinate + aree; per le forme predefinite: numero di barre uniformemente distribuite, diametro, copriferro | **[L]** sul file di aiuto ufficiale |
| **Sismicad** (Concrete, italiano) | Progetto automatico delle armature di travi, pilastri, pareti, plinti, scale, pali, piastre; correzione interattiva. "di ogni barra è nota l'esatta posizione all'interno del getto" | Progetto automatico + editing grafico "a sezione o a prospetto" | **[P]** (scheda tecnica ufficiale; manuale completo non pubblico) |
| **CDS Win** (STS, italiano) | Manipolazione delle armature di travi e pilastri (diametro e passo delle staffe, ferri d'angolo) | **[C]** — nessun manuale scaricabile dal sito del produttore | **[C]** |

### 1.2 Fonti, una per riga

| Programma | URL primario | Che cosa ho letto lì |
|---|---|---|
| Section Designer — reinforcing shapes | `https://docs.csiamerica.com/help-files/common-section-designer(from-sap-and-csibridge)/Menus/Draw/Draw_Reinforcing_Shapes/Draw_Reinforcing_Shape.htm` e le quattro pagine figlie `Single_Bar`, `Line_Pattern`, `Rectangular_Pattern`, `Circular_Pattern` | l'elenco completo dei parametri di ciascun tipo |
| Section Designer — bordi e angoli | `.../Draw_Reinforcing_Shapes/Edge_Reinforcing_Form.htm`, `.../Corner_Point_Reinforcing_Form.htm` | `Bar Size`, `Bar Spacing`, `Apply to All Edges`, `Apply to All Corners` |
| Section Designer — forma poligonale | `.../Menus/Draw/Draw_Poly_Shape.htm` | il flag `Reinforcing: Yes/No` |
| ETABS — sezione telaio | `https://docs.csiamerica.com/help-files/etabs/Menus/Define/Section_Properties/Frame_Sections/Frame_Section_Property_Reinforcement_Data_Form.htm` | i nomi dei campi di colonna e trave |
| CSiBridge — sezione telaio | `https://docs.csiamerica.com/help-files/csibridge/Components_tab/Properties_Type_panel/Frame_Sections/Reinforcement_Data_Form.htm` | conferma indipendente degli stessi nomi |
| ETABS — catalogo diametri | `https://docs.csiamerica.com/help-files/etabs/Menus/Define/Section_Properties/Reinforcing_Bar_Sizes.htm` | `Bar ID`, `Bar Diameter`, `Bar Area`, `Add Common Bar Set` |
| ETABS — SD Section | `https://docs.csiamerica.com/help-files/etabs/Menus/Define/Section_Properties/Frame_Sections/SD_Section.htm` | `Reinforcement to be Checked` vs `Reinforcement to be Designed` |
| CSiCol | `https://www.csiamerica.com/products/csicol/features` | elenco dei pattern di distribuzione |
| Response-2000 | `https://www.hadrianworks.com/uploads/1/2/6/7/126759793/appen_a.pdf` — Appendice A della tesi di dottorato di E. C. Bentz, *Sectional Analysis of Reinforced Concrete Members*, University of Toronto, 2000 | §2-1 Quick Define Wizard, §2-5 Longitudinal Reinforcement, §2-6 Transverse Reinforcement, §Cross Section (plot) |
| XTRACT | `http://www.trcbridgedesignsoftware.com/software-XTRACT.html` (il sito ha **certificato TLS scaduto**: raggiunto con `curl -k`) | elenco funzioni; Chadwell & Imbsen, *XTRACT: A Tool for Axial Force – Ultimate Curvature Interactions*, ASCE Structures Congress 2004 |
| VecTor2 / FormWorks | `https://vectoranalysisgroup.com/user_manuals/manual1.pdf` — *VecTor2 & FormWorks User's Manual*, seconda edizione, Wong, Vecchio, Trommels | capitolo materiali (Reinforcement Components), capitolo FormWorks (RC Regions, Reinforcement page) |
| STKO | *STKO User Manual*, distribuito da ASDEA via Google Drive, linkato da `https://asdea.eu/software/stko-documentation/` | §Beam Fiber Section Editor, §Fiber Beam Cross-Sections |
| GiD | `https://downloads.gidsimulation.com/GiD_Documentation/Docs/GiD17/GiD_17_Reference_Manual.pdf` | assenza totale di concetti di armatura |
| Abaqus CAE | `https://abaqus-docs.mit.edu/2017/English/SIMACAECAERefMap/simacae-t-prpsectionrebar.htm` | procedura `Defining rebar layers` |
| Abaqus analisi | `https://ceae-server.colorado.edu/v2016/books/usb/pt01ch02s02aus13.html` e `.../pt01ch02s02aus14.html` | §2.2.3 *Defining reinforcement*, §2.2.4 *Defining rebar as an element property* |
| midas Civil | `https://manual.midasuser.com/EN_Common/Civil/890/Start/04_Model/01_Structure_Wizerd/PSC/Section___Rebar.htm` | campi `Dia.`, `Number`, `Area`, `Ref.Y`, `Y`, `Ref.Z`, `Z` |
| SCIA Engineer | `https://kc.scia.net/Documentation/Content/Documentation/D&C/Concrete/TUT%20%5BEng%5D%20SCIA21.0%20-%20Tutorial%20-%201D%20reinforcement.pdf` | i tre livelli di armatura e il flusso di inserimento pratico |
| RC-SEC | `https://help.geostru.eu/pdf/RC-SEC_IT.pdf` | scheda dati sezioni, opzioni armature, staffe-duttilità |
| VcaSlu | `https://gelfi.unibs.it/software/Vcaslu-help.pdf` | introduzione, esempio guidato, esempi 2 e 3 |
| Sismicad | `https://www.concrete.it/download/docs/product/scheda_tecnica-sismicad.pdf` | dichiarazioni sul progetto e sulla correzione interattiva delle armature |
| OpenSees Navigator | `https://peer.berkeley.edu/opensees-navigator` | esistenza, autori, natura di GUI MATLAB |

**Nota su Abaqus.** La documentazione ufficiale Dassault (`help.3ds.com`) richiede registrazione. Le pagine lette sono **mirror accademici del testo ufficiale** (MIT per il manuale CAE 2017, University of Colorado per il manuale di analisi 2016). Il testo è quello del produttore, l'host no. Chi cita in tesi dovrebbe risalire alla versione ufficiale corrente e verificare che i nomi non siano cambiati fra la 2016/2017 e l'attuale.

---

## 2. Il gesto dell'utente: quattro modelli d'interazione

Dalla lettura incrociata emergono **quattro** modelli, non uno. Sono ricorrenti e, dove convivono, convivono in un ordine preciso.

### 2.1 Modello A — Form parametrica su sezione a catalogo ("compila la scheda")

L'utente sceglie una forma da un elenco chiuso (rettangolare, circolare, T, I…), e l'armatura è descritta da pochi numeri interi. Nessun disegno, nessuna coordinata.

Esempio canonico, ETABS/SAP2000, `Frame Section Property Reinforcement Data` **[L]**:

- `Rebar Material` (liste separate per `Longitudinal Bars` e `Confinement Bars`)
- `Design Type`: `Column` oppure `Beam`
- se colonna: `Reinforcement Configuration` = `Rectangular` | `Circular`; `Confinement Bars` = `Ties` | `Spiral`
- `Clear Cover for Confinement Bars`
- `Number of Longit. Bars Along 3-dir Face`, `Number of Longit. Bars Along 2-dir Face`
- `Longitudinal Bar Size`, `Corner Bar Size`
- `Confinement Bar Size`, `Longitudinal Spacing of Confinement Bars`, `Number of Confinement Bars in 3-dir`, `Number of Confinement Bars in the 2-dir`
- se trave: solo `Cover to Longitudinal Rebar Group Centroid` (Top) e (Bottom), più eventuali *overwrite* di area agli estremi

Il punto notevole: **per una trave, ETABS non chiede né il numero né la posizione delle barre.** Chiede due copriferri e basta. La trave è dimensionata dal post-processore, non descritta dall'utente.

Lo stesso modello, in italiano, in RC-SEC per le *sezioni predefinite* **[L]**: «per quelle circolari l'armatura deve essere definita da due file di armature (superiore ed inferiore) da assegnare mediante il numero di barre ed il relativo diametro e copriferro».

### 2.2 Modello B — Lista di strati ("aggiungi una riga alla tabella")

L'utente costruisce l'armatura come **elenco di strati**, ciascuno con una quota. Interfaccia a lista con i tre bottoni classici.

Response-2000 §2-5 **[L]**: «Each dialog box uses the traditional list of layers with the ability to add a new definition, modify an existing one or delete it.» Nell'esempio del manuale: «It has 3 bars defined each with a cross sectional area of 440 mm² and a centroid 38 mm above the bottom of the cross section.»

Cioè, per strato: **numero di barre**, **area**, **quota del baricentro dello strato misurata dal bordo inferiore**, **tipo di acciaio**. Membrane-2000 e Shell-2000 usano lo stesso dialogo ma «ask for spacing of bars rather than the number of bars».

Abaqus è lo stesso modello portato all'estremo: la tabella `Rebar Layers` ha una riga per strato con «the name of the rebar layer, the name of the material forming the rebar layer, the cross-sectional area per bar, the rebar spacing in the plane of the section, and the angular orientation of the rebar» **[L]**.

### 2.3 Modello C — Disegno diretto sulla sezione ("clicca dove va la barra")

L'utente disegna. È il modello di Section Designer, di CSiCol e di STKO.

Section Designer, `Single Bar` **[L]**: «Left click anywhere in the active window to locate the single rebar. […] Right click on the resulting rebar to display the `Shape Properties - Reinforcing` form.» I parametri esposti dopo il click sono `Type`, `Material`, `X Center`, `Y Center`, `Bar Size`, `Steel Model`.

Il dettaglio da rubare: **il click è approssimativo e la form è esatta.** Il manuale lo dice esplicitamente: «place the reinforcing at any location and use the `Reshape` mode to drag the reinforcing shape to the required location». Si clicca a occhio, poi si corregge il numero.

STKO fa lo stesso ma dentro un editor CAD **[L]**: si disegna un rettangolo interno, si sceglie `Make Punctual Fibers`, e «a Dialog box will appear in which the user may rename the rebars, insert Rebar data, specify the diameter, the number of rebars on each segment, and the spacing between the rebars».

### 2.4 Modello D — Griglia numerica accoppiata a una vista grafica

Non è né form né disegno: è una **tabella di coordinate** che si aggiorna in tempo reale su un disegno, e viceversa.

RC-SEC **[L]**: «Passando col mouse sui vertici del dominio poligonale vengono evidenziate nella apposita griglia le corrispondenti coordinate rendendo in tal modo semplice la loro modifica interattiva» e «L'inserimento o la modifica dei valori numerici delle coordinate nella griglia dati è riportato interattivamente nella finestra grafica».

VcaSlu, esempio guidato **[L]**: «Inserire il numero di barre e premere Enter» → «Inserire Aree e coordinate barre» → «Cliccare sullo schema per visualizzare la sezione in scala».

VecTor2/FormWorks è lo stesso modello, applicato ai vertici invece che alle barre: i campi sono `X`, `Y`, `Reps`, `Dx`, `Dy`, e si conferma con `+` dopo ogni vertice, `Close` dopo l'ultimo **[L]**.

### 2.5 Qual è il più diffuso

**Nessuno dei quattro da solo. Il più diffuso è la coppia A + qualcos'altro.**

Il conteggio su ciò che ho letto direttamente: 
- A (form su catalogo) è presente in **ETABS/SAP2000, CSiBridge, RC-SEC, VcaSlu, SCIA, Response-2000 (wizard), midas** — 7 su 7 dei programmi orientati alla progettazione;
- B (lista di strati) in **Response-2000, Abaqus, midas**;
- C (disegno diretto) in **Section Designer, CSiCol, STKO** — cioè i programmi orientati alla *sezione qualunque*;
- D (griglia + grafica) in **RC-SEC, VcaSlu, FormWorks**.

Il pattern architetturale ricorrente è: **A per partire, C o D per correggere.** Section Designer lo istituzionalizza: la forma disegnata nasce con `Reinforcing: Yes` e il programma «inserts edge reinforcing bars and corner bars in the shape»; solo mettendo il flag a `No` si passa al disegno barra per barra **[L]**. Response-2000 lo dice in modo ancora più esplicito: il *Quick Define Wizard* «will often be necessary to make slight changes to resulting section, as the default values in the programs may not match the desired ones» **[L]**.

Nessuno dei programmi letti obbliga a partire dal foglio bianco.

---

## 3. Il modello dei dati esposto

### 3.1 Che cosa viene chiesto, e in quale ordine

L'ordine è notevolmente stabile fra i programmi. Ricostruito da Response-2000 (wizard a 4 pagine), RC-SEC (schede), SCIA (tutorial), VcaSlu (esempio guidato) **[L]** su tutti e quattro:

1. **materiali** (calcestruzzo, acciaio longitudinale, acciaio delle staffe — spesso separabili)
2. **geometria della sezione** (forma da catalogo, poi dimensioni)
3. **armatura longitudinale**
4. **armatura trasversale** (staffe)
5. sollecitazioni / analisi

VcaSlu lo elenca come procedura **[L]**: «scelta della normativa → scelta dei materiali → scelta del tipo di sezione → input del titolo → input dei dati della sezione → input dell'azione assiale → input delle azioni flettenti».

RC-SEC pone un vincolo d'ordine esplicito **[L]**: «vanno assegnati tutti i dati dei domini di calcestruzzo prima di assegnare le armature».

**Le staffe vengono sempre dopo le barre longitudinali, e in un dialogo separato.** Non ho trovato nessun programma che le chieda insieme.

### 3.2 Le grandezze, per nome

| Grandezza | Nome in inglese | Nome in italiano (fonte primaria italiana) | Dove |
|---|---|---|---|
| copriferro | `Clear Cover for Confinement Bars`; `Cover to Longitudinal Rebar Group Centroid` (ETABS); `clear cover` (Response-2000) | `copriferro`, e nella scheda `C. ferro inf.` / `C. ferro sup.` (RC-SEC) | tutti |
| diametro | `Bar Size` (CSI), `Bar Diameter` (catalogo), `Reinforcement Diameter, Db` (VecTor2) | `diametro` (mm) | tutti |
| area della singola barra | `Bar Area`; `cross-sectional area per bar` (Abaqus); `area` (Response-2000) | `area` | Abaqus, Response-2000, midas, VcaSlu |
| numero di barre per lato | `Number of Longit. Bars Along 3-dir Face` / `Along 2-dir Face` | `numero di barre` | ETABS, CSiBridge |
| numero di barre totale | `Number of Longitudinal Bars`; `No. of Bars` | `numero di barre uniformemente distribuite` (VcaSlu) | sezioni circolari, ovunque |
| passo delle barre | `Bar Spacing` (CSI); `rebar spacing` (Abaqus); `spacing between the rebars` (STKO) | `interferro` per la distanza netta (RC-SEC) | tutti |
| diametro staffe | `Confinement Bar Size` | `diametro staffe` | ETABS, RC-SEC |
| passo staffe | `Longitudinal Spacing of Confinement Bars (Along 1-Axis)` | `passo` / `passo delle staffe` | ETABS, RC-SEC, SCIA |
| bracci | `Number of Confinement Bars in 3-dir` / `in the 2-dir` (ETABS); `number of cuts` (SCIA) | `bracci`: «staffe singole (2 bracci), doppie (4 bracci), + N legature» (RC-SEC) | ETABS, SCIA, RC-SEC |
| tipo di staffa | `Ties` / `Spiral` (CSI); `Closed Stirrups, Open Stirrups, Hoops, Single-Leg hooked bars, Single-Leg T-Headed bars` (Response-2000) | `staffe chiuse`, `legature` (RC-SEC) | tutti |
| posizione dello strato | `centroid … above the bottom of the cross section` (Response-2000); `position in the thickness direction` (Abaqus) | `coordinate` (cm) delle barre (RC-SEC, VcaSlu) | Response-2000, Abaqus |
| coordinate della barra | `X Center`, `Y Center` (Section Designer); `Ref.Y`, `Y`, `Ref.Z`, `Z` (midas) | `coordinate` (cm) | Section Designer, midas, RC-SEC, VcaSlu |

**Tre osservazioni sui nomi.**

1. **Il copriferro non è mai uno solo, e non è mai un dato senza ambiguità.** ETABS lo chiama `Clear Cover for Confinement Bars` per le colonne (netto, misurato dalla staffa) ma `Cover to Longitudinal Rebar Group Centroid` per le travi (al baricentro). Sono due grandezze diverse con lo stesso nome comune. RC-SEC lo dichiara nel manuale e fa i conti al posto dell'utente **[L]**: «Se ad esempio in condizioni ambientali ordinarie si utilizzano barre Ø 16 e staffe Ø 8, volendo assicurare alle staffe il copriferro netto di 2,5 cm (comprensivo della tolleranza di 0,5 cm prevista in normativa), il copriferro dal baricentro delle barre da assegnare nei dati del programma è pari a 2,5 + 0,8 + 1,6/2 = 4,1 cm». Poi restituisce come **risultato** «il copriferro netto minimo tra tutte le barre longitudinali». Cioè: chiede il copriferro nella forma comoda per posizionare, e **restituisce** quello nella forma richiesta dalla norma.

2. **Diametro o area, non entrambi, e la scelta è esplicita.** Response-2000 **[L]**: «steel may be selected by a named title (e.g. #5, 20M, etc.) or by supplying a cross sectional area by clicking on the `select by area` check box». Il catalogo dei diametri è una risorsa a parte, editabile: in ETABS è la form `Reinforcing Bar Sizes` con `Bar ID` / `Bar Diameter` / `Bar Area` e un bottone `Add Common Bar Set` che carica una serie standard; in Response-2000 è il file `Rebar.dat` (§5-8 del manuale) **[L]**.

3. **Il passo è quasi sempre "quello richiesto", non "quello vero".** Section Designer, `Line Pattern` **[L]**: «`Bar Spacing`: The specified (not necessarily actual) center to center spacing of bars along the specified line. Section Designer calculates the required number of bars by dividing the length of the line by the specified bar spacing and adding one to the result. […] If that fraction is greater than 0.1, Section Designer rounds the number of bars up; otherwise it rounds the number of bars down.» L'utente dà un passo desiderato, il programma restituisce un passo effettivo. La regola di arrotondamento è **dichiarata nel manuale**, non nascosta.

### 3.3 Il caso VecTor2: un modello dei dati diverso

Vale la pena isolarlo perché rompe lo schema. In VecTor2 l'armatura *smeared* non è un oggetto della sezione: è una **proprietà del materiale calcestruzzo**. I campi del gruppo `Reinforcement Component Properties` sono **[L]**:

`Reference Type`, `Out of Plane Reinforcement` (casella di spunta), `Direction from X-Axis` (gradi, 0–360), `Reinforcement Ratio, As` (percentuale), `Reinforcement Diameter, Db`, `Yield Strength, Fy`, `Ultimate Strength, Fu`, `Elastic Modulus, Es`, `Strain Hardening Modulus, Esh`, `Strain Hardening Strain, esh`, `Thermal Expansion Coefficient, Cs`, `Prestrain`.

Cioè: **nessuna posizione**. L'armatura diffusa è descritta da rapporto geometrico, diametro e direzione. La posizione compare solo per l'armatura discreta, che è un *reinforcement path* con `X`, `Y`, `Reps`, `Dx`, `Dy` e la spunta `Imperfect Bond`.

Abaqus fa la stessa distinzione con parole diverse: i rebar layer sono «treated as a smeared layer with a constant thickness equal to the area of each reinforcing bar divided by the reinforcing bar spacing» **[L]**.

---

## 4. Le scorciatoie che ricorrono in più programmi

Ordinate per numero di programmi in cui le ho verificate direttamente.

**1. «n barre per lato», per la sezione rettangolare.** — ETABS/SAP2000/CSiBridge (`Number of Longit. Bars Along 3-dir Face` + `Along 2-dir Face`), Section Designer (`Rectangular Pattern`), RC-SEC (sezioni predefinite: due file, superiore e inferiore), CSiCol («in sides»), STKO («the number of rebars on each segment»). **[L]** su tutti e cinque. È la scorciatoia più universale che ho trovato.

**2. «n barre su una circonferenza», per la sezione circolare.** — Section Designer (`Circular Pattern`: `Diameter`, `No. of Bars`, `Rotation`, `Bar Size`), ETABS (`Number of Longitudinal Bars` + `Circular`), Response-2000 (pattern circolari, «only available in Response-2000»), VcaSlu («il numero di barre uniformemente distribuite, il diametro delle barre, il copriferro (distanza baricentro barra da circonferenza circoscritta)»), RC-SEC, CSiCol. **[L]** su tutti.

**3. «barre d'angolo separate dalle barre di bordo».** — Section Designer ha due form distinte: `Edge Reinforcing Form` (`Bar Size`, `Bar Spacing`, `Apply to All Edges`) e `Corner Point Reinforcing Form` (`Bar Size`, `Apply to All Corners`). ETABS ha `Corner Bar Size and Area` separato da `Longitudinal Bar Size and Area`. RC-SEC ha l'«Opzione Barre nei vertici dei domini poligonali: consente la generazione automatica di una o tre barre in ogni vertice dei domini poligonali assegnati». **[L]** su tutti e tre. È una scorciatoia che un utente di CA si aspetta.

**4. «barre distribuite fra due barre già esistenti» (generazione lineare).** — Section Designer (`Line Pattern`, definito da `X1,Y1` `X2,Y2` + passo + `End Bars: Yes/No`), RC-SEC («una generazione lineare di barre è costituita da una o più barre dello stesso diametro da inserire all'interno dell'allineamento definito da due barre isolate già assegnate […] Le barre così generate sono equidistanti tra loro e con le barre di estremità»). **[L]** su entrambi. Il flag `End Bars` di Section Designer e la formulazione «equidistanti tra loro e con le barre di estremità» di RC-SEC risolvono lo stesso problema: se le barre agli estremi ci sono già, non vanno duplicate.

**5. «pattern esplodibile in barre singole».** — Response-2000 **[L]**: «The pattern lists have an additional button as well that allows the pattern to be exploded into individual layers.» Section Designer ottiene lo stesso risultato per altra via, con il flag `Reinforcing: No` sulla forma che disattiva le barre automatiche e lascia disegnare a mano. È la valvola di sfogo che rende accettabile una scorciatoia: **se il pattern non basta, lo si rompe e si edita il risultato.**

**6. «staffe a passo costante con tipologia da elenco».** — Response-2000 (`Open stirrups, closed stirrups, single-leg stirrup, t-headed single leg, hoop and interlocking hoops` + passo + tipo di barra), ETABS (`Ties`/`Spiral` + `Longitudinal Spacing of Confinement Bars`), SCIA (forma di staffa scelta da un elenco, modificabile: «The stirrup shape can be edited or a new one can be made. Therefore, user points may be added»), RC-SEC (`staffe singole (2 bracci), doppie (4 bracci), + N legature`). **[L]** su tutti e quattro.

**7. «zone di staffatura».** — SCIA **[L]**: «Different stirrup zones can be created when editing the stirrup distance». Il passo non è uno solo lungo l'asta. Questo però è un concetto **d'asta**, non di sezione: nessun programma di sola analisi sezionale (Response-2000, VcaSlu, XTRACT) lo espone.

**8. «semiprogetto: metti zero e ci penso io».** — RC-SEC **[L]**: «Se si assegna il valore nullo al diametro o al passo il programma effettua il semiprogetto automatico delle sole staffe». ETABS ha l'equivalente esplicito nel radio button `Reinforcement to be Designed` contro `Reinforcement to be Checked`. Sono la stessa scorciatoia con due gradi di onestà: RC-SEC la nasconde in un valore sentinella, ETABS la mette in un'opzione.

**9. «armatura simmetrica».** — Attesa dal brief, ma **verificata solo parzialmente**. SCIA ha un'opzione `Symmetrical` **[L]**, ma riguarda la simmetria delle *zone di staffatura* lungo la campata, non la disposizione nella sezione. Section Designer, ETABS, Response-2000 e RC-SEC ottengono la simmetria come **conseguenza** del pattern (rettangolare, circolare, «n per lato») e non hanno un flag chiamato "simmetrica". Non ho trovato in nessuna fonte primaria letta un comando etichettato *symmetric reinforcement* per la sezione. La premessa del brief su questo punto **non si è confermata nella forma in cui era posta**: la simmetria non è una scorciatoia a sé, è un effetto dei pattern.

**10. «import da DXF».** — RC-SEC **[L]**: «Sia il contorno poligonale che le barre di armature di sezioni generiche possono essere importate da file *.dxf». Section Designer e VcaSlu fanno l'inverso (export DXF). È una scorciatoia di una sola famiglia, non universale, ma nel contesto italiano è attesa.

---

## 5. La rappresentazione grafica

### 5.1 Che cosa viene disegnato

Il minimo comune, verificato ovunque: **la sezione in scala, con le barre come cerchi pieni nella posizione reale**. Non ho trovato nessun programma che disegni le barre schematicamente fuori posizione.

Response-2000 **[L]** aggiunge che il disegno è di prima classe: «Cliccare sullo schema per visualizzare la sezione in scala; doppio clic per plottare la sezione in una form ingrandibile» è la formulazione di VcaSlu, ma Response-2000 fa lo stesso.

### 5.2 Numerazione visibile delle barre

RC-SEC **[L]**: «Ogni barra generata viene numerata e visualizzata (insieme al suo numero) nella finestra grafica in modo da poter costituire un estremo per una successiva generazione lineare di barre.»

È il dettaglio operativamente più importante di tutta questa sezione. Il numero non serve a decorare: **serve a poter dire "genera 3 barre fra la 5 e la 6"**. Senza etichette visibili, la scorciatoia n. 4 (generazione lineare) non è utilizzabile.

### 5.3 Colore come stato, non come decorazione

Response-2000, sezione *Cross Section* dei 9 plot **[L]**:

> «The cross section is drawn darker in regions where the concrete has not cracked. Longitudinal reinforcement and stirrups are draw dark red if on the yield plateau, bright red if strain hardening, and dark and bright green for yielding in compression. […] for cases where part of the concrete is crushing, the section is redrawn in pink, and for sections where the cracks are slipping causing failure, the section is drawn in purple.»

Cioè: **quattro stati di snervamento sulle barre, e due stati di crisi sul calcestruzzo, tutti codificati a colore sulla stessa vista della sezione.** Questo è post-processing, non input; ma stabilisce che la vista della sezione è la stessa in ingresso e in uscita, e che ci si aspetta di guardarla.

Section Designer permette di scegliere il colore di riempimento di ogni forma (`Color`, che apre la form `Color`) **[L]**: il colore è usato per distinguere i **materiali** all'interno di una sezione composita.

### 5.4 Che cosa deve essere visibile perché l'utente veda un errore

Sintesi dalle fonti lette, con l'evidenza:

| Cosa deve vedersi | Perché | Chi lo fa |
|---|---|---|
| barre nella posizione reale, in scala | un copriferro sbagliato di un fattore 10 si vede solo se il disegno è in scala | tutti **[L]** |
| numero identificativo di ogni barra | è il prerequisito delle generazioni lineari, ed è come si nomina l'errore | RC-SEC **[L]** |
| distinzione grafica dei materiali/domini | in una sezione composita il calcestruzzo sbagliato assegnato a un dominio è invisibile senza colore | Section Designer, STKO **[L]** |
| il **risultato** del copriferro netto minimo | l'utente inserisce il copriferro al baricentro; l'errore normativo sta nel netto | RC-SEC **[L]**: «Tra i risultati del calcolo compare sempre il copriferro netto minimo tra tutte le barre longitudinali» |
| l'**interferro netto minimo** | due barre che si toccano sono un errore geometrico invisibile a occhio se il disegno è piccolo | RC-SEC **[L]**: «Al termine delle elaborazioni il programma espone il valore dell'interferro netto minimo tra i risultati del calcolo. Se l'interferro è inferiore a quello minimo fissato vanno aumentati i diametri delle barre o accoppiate…» |
| il passo **effettivo** delle staffe, non quello richiesto | dove il programma arrotonda, l'utente deve sapere che cosa è uscito | Section Designer **[L]** (per il `Line Pattern`) |

Le ultime tre righe sono la parte più trasferibile: **il controllo di errore migliore che ho trovato in questi programmi non è un disegno, è un numero restituito accanto al disegno** — copriferro netto minimo e interferro netto minimo, calcolati e mostrati dopo l'inserimento.

---

## 6. Che cosa NON fanno

### 6.1 Limiti dichiarati nei manuali

**GiD non ha alcun concetto di armatura.** Il *Reference Manual* v17 non contiene mai le parole `reinforcement`, `rebar`, `concrete` (verificato per conteggio: 0, 0, 0 su un testo dove `material` compare 79 volte) **[L]**. GiD è un mesher generico; l'armatura è responsabilità del *problem type*. Conseguenza per il progetto: GiD non è un modello da copiare per questa schermata, è un esempio di che cosa succede quando il preprocessore resta agnostico.

**Abaqus ha deprecato di fatto l'armatura nei solidi.** §2.2.4 **[L]**: «The preferred method for defining rebar in solids is embedding reinforced surface or membrane elements in 'host' solid elements». Il metodo diretto resta supportato ma è descritto come più faticoso. Cioè: nel programma FEM generalista più diffuso, **le barre dentro un solido non sono un oggetto di prima classe**.

**Section Designer non usa l'armatura per le proprietà di sezione.** La documentazione CSI dichiara che l'acciaio d'armatura non è considerato nel calcolo delle proprietà di sezione, incluso l'acciaio definito come *reinforcing shape* **[P]** — trovato come dichiarazione nel materiale CSI, non riletto nella pagina esatta: **da riverificare prima di citarlo in tesi**.

**Section Designer non lascia cambiare il modulo elastico dell'acciaio.** Su tutte e quattro le *reinforcing shape* **[L]**: «The modulus of elasticity of the reinforcing is always assumed to be 29000 ksi.» È un valore cablato (200 GPa circa), in un programma per il resto molto configurabile.

**Response-2000 non modella la lunghezza di ancoraggio.** §2-6 **[L]**: «Each kind of bar is assumed to be able to yield all the way to the end of the bar as entered (i.e. no development length). This is reasonable if there is a t-head or a hook at the end of the bar but means that a correction should be made for transverse bars that are not properly anchored.»

**Response-2000 decide da solo quando fare gli strati.** §2-1 **[L]**: «The bars will be placed into layers if there are too many to fit within the width of the cross section. Response-2000 uses bar spacing equal to the bar diameter to produce layers of steel.» Cioè, un'ipotesi geometrica implicita (passo = diametro) che l'utente non controlla dal wizard.

**Membrane-2000 e Shell-2000 non hanno pattern circolari** **[L]**; **Triax-2000 non ha armatura trasversale** perché «in a 3D block of concrete, the transverse direction is actually the longitudinal Z direction» **[L]**.

**ETABS non fa descrivere le barre di una trave.** Vedi §2.1: per `Design Type = Beam` chiede solo i due copriferri al baricentro del gruppo **[L]**.

**RC-SEC: le sezioni predefinite sono limitate alla flessione retta.** **[L]**: «Per tutte le sezioni predefinite il momento flettente da assegnare può avere solo la componente Mx». E le sezioni generiche, che permettono la flessione deviata, hanno «il solo calcolo di verifica», niente progetto. La comodità dell'input rapido si paga in generalità: è un compromesso dichiarato nel manuale, non un difetto nascosto.

**VecTor2 non fa mettere una barra in una sezione.** Non è un limite, è una scelta di modello: l'armatura o è una percentuale nel materiale, o è un percorso di elementi truss nel piano. Non esiste l'oggetto "barra alla quota y" **[L]**.

**FormWorks obbliga a definire i vertici in senso antiorario** **[L]**: «The vertices defining the region are entered in cyclic counter-clockwise order», e le regioni «cannot overlap», con l'avvertenza «Care should be taken to define the common vertices of regions with exactly the same coordinates». RC-SEC impone il **senso orario** per i vertici dei domini **[L]**. Due programmi, due convenzioni opposte, entrambe obbligatorie. È il tipo di vincolo che genera errori silenziosi.

### 6.2 Che cosa nessuno fa (fra i letti)

- **Nessuno espone la sagoma reale della staffa come poligono, con i raggi di piega, dentro la schermata di sezione.** SCIA ci va più vicino: la forma di staffa si sceglie da un elenco e «can be edited or a new one can be made. Therefore, user points may be added» **[L]**. Gli altri riducono la staffa a: tipo + diametro + passo + numero di bracci.
- **Nessuno dei programmi di sola analisi sezionale gestisce la variazione dell'armatura lungo l'asta.** È un concetto che compare solo dove c'è l'asta (SCIA, midas, Sismicad, CDS).
- **Nessuno chiede la posizione della barra in tre coordinate.** La sezione è sempre un piano, e la terza dimensione, quando c'è, è "posizione lungo l'asta" o "posizione nello spessore" (Abaqus), mai una coordinata libera.

---

## 7. Raccomandazione

**Questa sezione è una raccomandazione, non una decisione presa.** La scelta resta al progetto.

Se dovessi disegnare questa schermata per un'applicazione web locale, monoutente, in italiano, copierei **il modello A + C di Section Designer**, con la nomenclatura italiana di RC-SEC e i controlli di errore di RC-SEC. In concreto:

**1. Partire da un pattern, mai dal foglio bianco.** Tre pattern soli, che coprono la quasi totalità dei casi ed esistono in almeno cinque programmi ciascuno: *n barre per lato* (rettangolare), *n barre su circonferenza* (circolare), *fila di barre fra due punti* (lineare). L'utente sceglie un pattern e riempie 4–5 campi. È il gesto che il laboratorio e gli altri tesisti conosceranno già da qualunque programma abbiano usato.

**2. Rendere il pattern esplodibile.** Il bottone di Response-2000 che «allows the pattern to be exploded into individual layers», o l'equivalente flag `Reinforcing: No` di Section Designer. Senza questa valvola, il primo caso non standard blocca l'utente. Con questa valvola, il pattern è una comodità e non una gabbia.

**3. Il click posiziona, il numero corregge.** La regola di Section Designer — click approssimativo, poi `Reshape` o modifica di `X Center` / `Y Center` — è la sola che ho trovato ripetuta in tre programmi diversi (Section Designer, STKO, RC-SEC nella variante griglia↔grafica). In un'app web questo si traduce in: canvas cliccabile + tabella accanto, sincronizzati nei due versi. È anche il modello che degrada meglio: se il canvas non funziona, la tabella resta usabile.

**4. Chiedere il copriferro nella forma comoda, restituire quello normativo.** RC-SEC lo esplicita: si assegna il copriferro **al baricentro della barra** perché è comodo per posizionare, e si **restituisce** il copriferro netto minimo fra tutte le barre. Fare lo stesso, e nel campo di input scrivere accanto la formula, come fa il manuale RC-SEC: `2,5 + 0,8 + 1,6/2 = 4,1`. Costa una riga di testo e toglie l'errore più frequente del dominio.

**5. Numerare le barre nel disegno.** È il prerequisito della generazione lineare, ed è come l'utente nominerà l'errore quando lo segnalerà.

**6. Mostrare tre numeri di controllo sotto il disegno, sempre**: copriferro netto minimo, interferro netto minimo, area totale di armatura. I primi due vengono da RC-SEC, che li tratta come risultati di prima classe. Sono il modo più economico per rendere visibile un errore che il disegno da solo non mostra.

**7. Nomi italiani, presi dai manuali italiani letti, non tradotti da me**: `copriferro`, `interferro`, `diametro`, `numero di barre`, `passo`, `bracci`, `staffe`, `legature`, `barre nei vertici`, `barre isolate`. Sono i termini di RC-SEC e VcaSlu, cioè quelli che un tesista italiano e un laboratorio italiano hanno già visto.

**8. Che cosa non fare, sulla base del §6.** Non provare a modellare la sagoma della staffa con i raggi di piega (nessuno lo fa nella schermata di sezione, e SCIA che ci prova lo fa in un editor separato). Non provare a esporre la variazione dell'armatura lungo l'asta in questa schermata: è un concetto d'asta, e i programmi che lo hanno lo mettono altrove. Non cablare il modulo elastico dell'acciaio come fa Section Designer: è l'unico limite di quel programma che, letto oggi, sembra puramente storico.

**Perché questo modello e non un altro.** Il modello B puro (lista di strati alla Response-2000) è più veloce da implementare ma chiede all'utente di pensare per strati, che è la struttura del solutore, non quella del disegno esecutivo. Il modello D puro (griglia di coordinate alla VcaSlu) è il più semplice in assoluto e il più tollerante a sezioni strane, ma per una colonna 8Ø16 richiede otto righe di coordinate scritte a mano. La coppia A + C sposta il costo dove serve: gratis il caso comune, possibile il caso raro.

---

## 8. Caveat

- **Documentazione dietro registrazione o non pubblica.** Il manuale ufficiale Abaqus (`help.3ds.com`) richiede account: ho letto **mirror accademici** (MIT, University of Colorado) delle versioni 2016/2017. I nomi dei campi possono essere cambiati nelle versioni attuali. Il manuale completo di Sismicad e quello di CDS Win **non sono scaricabili dai siti dei produttori**: per Sismicad ho letto solo la scheda tecnica ufficiale, per CDS Win **nulla di primario** — le uniche copie trovate sono su siti di condivisione documenti e su siti di rivenditori, e non le ho usate.
- **XTRACT.** Il sito TRC ha il **certificato TLS scaduto** (raggiunto forzando la verifica). Il manuale è reperibile solo su Scribd/Slideshare/PDFCoffee: **non l'ho letto**, e quindi non riporto nomi di campi di XTRACT. Ciò che scrivo su XTRACT viene dall'elenco funzioni della pagina prodotto e dall'articolo ASCE Structures Congress 2004 di Chadwell & Imbsen, che è un lavoro sull'analisi, non sull'interfaccia.
- **OpenSees Navigator.** Verificato solo che esiste, chi lo ha scritto e che è una GUI MATLAB con template. Il PDF di presentazione su `openseesnavigator.berkeley.edu` che avevo individuato ha restituito 199 byte (redirect o rimozione). **Non ho verificato come si definisce una sezione a fibre nella sua GUI.**
- **STKO.** Il *User Manual* è ufficiale ma **distribuito via Google Drive**, non da un URL stabile del produttore: il link può cambiare senza preavviso. La versione scaricata riporta l'elenco comandi 3.2.0; non ho verificato se è l'ultima.
- **Section Designer, proprietà di sezione.** L'affermazione «l'acciaio d'armatura non è considerato nel calcolo delle proprietà di sezione» è **[P]**: l'ho vista dichiarata nella documentazione CSI ma non l'ho riletta nella pagina che la contiene. Da riverificare prima di usarla.
- **Estrazione del testo dai PDF.** Fatta con uno script proprio di sola libreria standard. Gestisce i flussi FlateDecode e la cifratura RC4 a 40 bit, **non** gestisce font CID/Type0 con mappe di codifica personalizzate. Il manuale RC-SEC è uscito con un glifo per riga (ricomposto togliendo i ritorni a capo) e alcuni caratteri accentati risultano assorbiti nella parola precedente: le citazioni da RC-SEC sono state ricontrollate a mano una per una, ma **le virgolette da quella fonte sono ricomposte, non copiate carattere per carattere**. Le citazioni da Response-2000, VecTor2, SCIA, STKO e VcaSlu sono estrazioni pulite.
- **Response-2000, età della fonte.** L'Appendice A letta è del **2000** (tesi di dottorato di Bentz). Il programma ha continuato a essere distribuito e la pagina Hadrian Software Works dichiara che «the programs have changed since the original documentation». I nomi di comando citati potrebbero non corrispondere alla versione corrente.
- **Conteggio dei modelli d'interazione (§2.5).** È un conteggio su ciò che **ho letto direttamente**, non un censimento del mercato. Con 14 programmi, di cui 11 verificati sulla fonte primaria, non è una statistica: è una rassegna. Le proporzioni non vanno riportate come percentuali.
- **La scorciatoia «armatura simmetrica» del brief non si è confermata** nella forma in cui era posta: vedi §4, voce 9. La simmetria risulta un effetto dei pattern, non un comando a sé. È una correzione a una premessa marginale, riportata qui e non aggirata.
