# Validazione del programma — quadro d'insieme

Aperto il 26/08/2026. Quattro ricerche indipendenti, condotte in parallelo su
`main` a `a07071a`, hanno prodotto i documenti di questa cartella:

| documento | cosa contiene |
|---|---|
| [`ricerca-vv-standard.md`](ricerca-vv-standard.md) | ASME V&V 10/10.1/40, AIAA G-077, benchmark NAFEMS con valori di riferimento verificati, patch test, MMS, GCI, metriche Verdict con le formule esatte |
| [`ricerca-letteratura-scan-to-fem.md`](ricerca-letteratura-scan-to-fem.md) | i 17 articoli di `Articoli/` letti uno per uno, più letteratura esterna: come questo dominio valida, e cosa non fa |
| [`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md) | qualificazione di CalculiX, suite di verifica ufficiale, comportamento su ingressi degeneri letto sul sorgente, e il dossier sul tetraedro lineare |
| [`inventario-grandezze.md`](inventario-grandezze.md) | ogni grandezza che il programma calcola, la formula implementata, e con quale oracolo è verificata — o se non lo è |

Questo file è la sintesi. Non ripete i numeri: li indirizza.

**Notazione numerica, valida per tutti i documenti di questa cartella.** La
virgola separa i decimali, **sempre**, anche nei valori ripresi da fonti inglesi:
44,092 Hz, non 44.092. Il punto separa le migliaia — 148.689 cubi — oppure le
migliaia non si separano affatto (20 000); mai con la virgola.

Tre esenzioni, tutte per la stessa ragione: lì il numero non è una misura di
questi documenti.

1. **Dentro una citazione verbatim** — fra « », fra " ", in un blockquote citato,
   in una trascrizione marcata `[V]` — il numero resta **come la fonte lo
   scrive**: «nu = 0.20 for each concrete class», «Density = 0.1»,
   «E = 10,000,000» con la virgola americana delle migliaia, entrambe le
   convenzioni nella stessa citazione se la fonte fa così. Un'affermazione su
   *come* una fonte scrive un numero diventa falsa se si riscrive il numero.
2. **I numeri che sono nomi e non misure**, per categoria e non per esempio:
   numeri di sezione, di clausola, di espressione, di figura, di tabella, di
   volume e di pagina; versioni di programma e di formato; identificatori
   bibliografici e normativi — DOI, arXiv, `DOE O 414.1C`. Un intervallo resta
   intero: `Tab. 3.2–3.4`, mai `3.2–3,4`.
3. **Dentro un blocco di codice** `così` resta com'è scritto nel sorgente:
   `GRAVITY_MM_S2 = 9810.0` è codice, e `9810,0` in Python è una tupla. La prosa
   italiana fuori dal code span segue la regola normale, anche nella stessa frase.

Due cifre restano **dichiaratamente ambigue** e sono marcate in loco col motivo:
il `705` della Tabella 2 del manuale CalculiX e i secondi di CPU di Tadepalli
2011, entrambe in
[`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md).

---

## 1. La scala della forza probatoria, e dove possiamo arrivare

Dalla letteratura letta, sette livelli in ordine crescente:

| liv. | prova | chi lo fa nei 17 articoli | raggiungibile qui? |
|---|---|---|---|
| 0 | il programma gira | Cloud2FEM, art. segmentazione | già fatto |
| 1 | autoconsistenza geometrica (mesh contro nuvola sorgente) | 3 lavori, con C2C < 3 mm su >95% | **già fatto, da irrobustire** |
| 2 | misura diretta indipendente | calibro, volume per riempimento, check point GNSS | **sì — la tavola `MURO 1`** |
| 3 | convergenza numerica (in ASME è *verification*, non validation) | 4 lavori, con i tempi di calcolo | **sì** |
| 4 | auto-validazione incrociata | 3 lavori HBIM | **sì, ma non vale da sola** |
| 5 | prova sperimentale sulla stessa struttura (statica, modale, OMA) | 3 lavori | **no — nessuna prova disponibile** |
| 6 | prova distruttiva contro benchmark round-robin | 1 solo su 17 (6,59 MN misurati contro 6,56 predetti) | no |

**Regola di composizione, dalla letteratura: i livelli si impilano, non si
sostituiscono.** Il livello 4 è complemento, mai sostituto — due modelli con la
stessa geometria e gli stessi materiali assunti concordano anche se sbagliano
entrambi.

**Il tetto raggiungibile in questa tesi è 1 + 2 + 3 + 4, più una quinta prova che
la scala della letteratura non contempla: la verifica incrociata fra codici**
(CalculiX contro Abaqus sullo stesso deck, licenza disponibile su macchina
Windows). Non è validazione sperimentale e non va chiamata così. È *code
verification* nel vocabolario ASME, ed è più forte dell'auto-validazione
incrociata perché i due solutori sono indipendenti davvero.

**Questo tetto non è basso.** Sette dei 17 articoli letti non confrontano mai con
un esperimento, e tre di questi sono proprio i lavori HBIM su patrimonio. Uno
chiama «validation» un pushover proprio che conferma un'analisi spettrale
propria.

## 2. Le cinque lacune della letteratura che diventano il nostro margine

Misurate sui 17 articoli, non supposte:

1. **Nessuno cita ASME V&V 10** — la norma che separa *verification* da
   *validation*. Adottarne il vocabolario, e dichiarare che i livelli 3 e 4 sono
   verification e non validation, ci mette sopra la media del campo.
2. **M3C2 zero occorrenze. Chamfer zero. Precision/recall a soglia zero.**
   Hausdorff compare 2 volte, C2C 2, C2M 1. M3C2 (Lague et al. 2013, ISPRS J.
   82:10-26) è l'unica metrica con **segno** e con test di significatività punto
   per punto. Precision/recall a soglia è l'unica cosa che separa *materia
   inventata* da *materia mancante* — la domanda esatta da porre quando Poisson
   chiude un buco.
3. **Le soglie si dichiarano quasi sempre dopo aver visto il numero.** Uno solo su
   17 le fissa prima, con la fonte. Una soglia decisa dopo non è un test, è una
   descrizione.
4. **Nessuno separa l'errore del materiale da quello geometrico.** Per una tesi il
   cui contributo è *geometrico* questa è la lacuna letale: un 5% di scarto sulla
   freccia non prova nulla se un 20% di incertezza su E può produrne uno identico.
   Serve un'analisi di sensibilità che li separi.
5. **La pipeline Poisson → MeshFix → TetGen è quasi assente dalla letteratura
   civile.** Sui 17: «MeshFix» 0 occorrenze, «TetGen» 0, «watertight» 0, «Poisson»
   3 e tutte in citazioni introduttive. Il resto usa **esaedri**, shell o beam.
   Conseguenze: non esiste un termine di paragone pubblicato — va costruito; le
   patologie specifiche vanno cercate nella computer graphics, non nel dominio; e
   **la scelta dei tetraedri va giustificata esplicitamente contro l'alternativa
   esaedrica**, perché una commissione del settore si aspetta esaedri. Il repo ha
   già `core/hexa.py`: il confronto si può misurare in casa.

E la frase che vale da sola come cornice, verbatim da ASME V&V 10:

> «The lack of mesh-refinement studies in solid mechanics may be the largest
> omission in the verification process.»

## 3. Il registro dei difetti trovati

Aperto il 26/08/2026 su `a07071a`. **Richiuso quasi per intero il 27/08/2026 su
`fed1872`**: delle venti voci, tredici sono chiuse, una lo è in parte, una
l'hanno superata i fatti, cinque restano vere. Ogni `file:riga` di questa
sezione è verificato contro `fed1872`; il dettaglio voce per voce, con
l'oracolo che ciascuna ha oggi, sta in
[`inventario-grandezze.md`](inventario-grandezze.md) §6.

I riferimenti si ricontrollano a macchina:
`python docs/validazione/controlla-riferimenti.py docs/validazione/README.md`.

### 3.1 Difetti di correttezza

| # | difetto | dove oggi | stato |
|---|---|---|---|
| D1 | `inverted_tets` filtrava con `V <= 0.0`, e `nan <= 0.0` è `False`: una mesh con coordinate NaN passava `InvertedElementsError` e veniva registrata con `inverted: 0` | `quality.py:110` | **chiuso** (`757429c`, `69465e1`): il criterio è scritto in positivo, `~(isfinite(V) & (V > 0))`, e copre anche il volume `+inf`. Prova in `tests/test_cancello_finitezza.py` |
| D2 | l'ordine delle colonne `.frd` (SXX,SYY,SZZ,SXY,SYZ,SZX) non era mai stato verificato contro un `.frd` di `ccx` vero | `solve.py:827` | **chiuso** (`87c7d7c`): uno stato con tutte e sei le componenti distinte, confrontate una per una con Hooke, e tutte e 719 le permutazioni respinte — `tests/validazione/test_ordine_frd.py` |
| D3 | `controlla_reazioni` confronta `RF` con il peso, ma sotto gravità `RF` **non** è la sola reazione | `solve.py:380` | **ancora vero, e gestito**: `risolvi` somma la quota tributaria (`solve.py:863`) prima del confronto, e l'invariante chiude a rel 1e-6 — `test_solve.py:731`. Resta il limite documentato nel manuale CalculiX §6.11.5 |
| D4 | nessuna guardia sull'ampiezza degli spostamenti | `solve.py:611` | **chiuso** (`c8d9084`): `controlla_spostamenti` è il sesto verdetto, con rapporto spostamento/dimensione — `test_solve.py:461` |
| D5 | `vertex_deviation` su nuvola vuota rendeva `[inf, inf, inf]`, che finiva nella mappa colore | `quality.py:600-603` | **chiuso**: solleva `ValueError` col proprio messaggio |
| D6 | `build_node_sets` su nodi vuoti sollevava `ValueError` grezzo | `abaqus.py:1507-1510` | **chiuso**: messaggio proprio, e una seconda guardia sui nodi non finiti (`abaqus.py:1517-1521`), che facevano uscire due set **vuoti** in silenzio |
| D7 | `controlla_picco` su array vuoto sollevava `ValueError` grezzo | `solve.py:519-523` | **chiuso** (`587d138`): messaggio proprio, dichiarato errore del chiamante |
| D8 | `element_volumes` accetta `colonne == 10`, ma `NODI_PER_ELEMENTO` non conteneva più C3D10 dopo `66b526d` | `quality.py:267`, `abaqus.py:539` | **superato dai fatti** (`479d671`, `76bbc00`): C3D10 è tornato, e quel ramo è vivo |

### 3.2 Grandezze senza oracolo

| # | grandezza | dove oggi | stato |
|---|---|---|---|
| O1 | `tet_aspect_ratios` | `quality.py:325` | **chiuso** (`aa2716f`): regolare = 1, rettangolo in forma chiusa, degenere → ∞ — `test_oracoli_mancanti.py:47-89` |
| O2 | `boundary_spacing` | `abaqus.py:1220` | **chiuso** (`aa2716f`): lato del tetraedro regolare, e scala col fattore 2 — `test_oracoli_mancanti.py:95-120` |
| O3 | `export["volume"]` / `export["mass"]` | `abaqus.py:1813-1814` | **chiuso** (`aa2716f`): scatola nota, rel 1e-6 — `test_oracoli_mancanti.py:149-150` |
| O4 | `GRAVITY_MM_S2 = 9810.0` | `config.py:22` | **chiuso** (`aa2716f`): asserita contro 9,81·1000, e ρ·V·g → N sull'acqua — `test_oracoli_mancanti.py:163`, `test_oracoli_mancanti.py:176` |
| O5 | `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, ingombro/bbox | `volume.py:279`, `quality.py:660`, `solve.py:581`, `io.py:110-112` | **chiuso in parte**: i primi tre hanno ora un oracolo (`test_oracoli_mancanti.py:197`, `test_oracoli_mancanti.py:254`, `test_solve.py:461`); ingombro/bbox resta solo regressione, ed è `max − min` per asse |

### 3.3 Guardie inerti

| # | guardia | dove oggi | stato |
|---|---|---|---|
| G1 | `bimodal` con modi in bin contigui, falsa per costruzione | `quality.py:714-716` | **chiuso** (`0a622a5`): la condizione è scritta come esito, `upper > lower + 1`, e il commento dice perché la forma precedente non poteva dare `True` |
| G2 | `if not in_contact.any()` in `footprint_coverage` | `abaqus.py:1417-1433` | **chiuso** (`0a622a5`): solleva invece di rendere `0.0`, che si sarebbe letto come «copre nulla». Il ramo resta irraggiungibile dalla pipeline, ma ora se ci si arriva si sa |
| G3 | `isfinite(minimo)` e `conteggio == 0` | `solve.py:563`, `solve.py:578` | **ancora vero**: inerti **per progetto e dichiarate tali** nelle docstring. Non un difetto, ma nemmeno una difesa |

### 3.4 Nomi che collidono con definizioni standard

| # | metrica | divergenza | stato |
|---|---|---|---|
| N1 | `scaled_jacobian` | prendeva il minimo su **8** angoli; Verdict ne usa **9**, includendo il centro con gli assi principali | **chiuso** (`0a622a5`): il nono punto c'è (`quality.py:198-224`). La misura ha smentito il timore che l'aveva sconsigliato: **nessun numero pubblicato si è spostato**. La metà in albero è `test_guardie_e_nomi.py:240`, duecento esaedri; le cifre più grandi — 1644 esaedri di tre prismi gmsh, 148.689 cubi perturbati — sono state **misurate una volta il 26/08/2026 fuori dall'albero, nel giro di `0a622a5`, e non sono riproducibili qui**: nessuno script le genera |
| N2 | `tet_aspect_ratios` | coincide con Verdict `L_max/(2√6·r)`, **ma non con Abaqus/CAE**, dove «aspect ratio» è spigolo max su spigolo min (l'`edge ratio` di Verdict): sul rettangolo di lato 1, 1,366 contro 1,414 | **ancora vero**, e ora dichiarato nella docstring (`quality.py:328-338`) oltre che nel registro delle soglie. Dichiarare quale definizione è, ogni volta che si cita una soglia da manuale |
| N3 | `radius_edge_ratios` come unico vincolo di qualità | il default `-q` di TetGen impone radius-edge ≤ 2,0 e **angolo diedro minimo 0°**: il radius-edge è **cieco agli sliver per costruzione** | **ancora vero**, e ora misurato nella docstring (`quality.py:370-379`): uno sliver dà 0,707 di raggio-spigolo e 0,162° di diedro. Affiancare il minimo angolo diedro, già calcolato a `quality.py:311` ma non usato come vincolo. Range Verdict: [40°, 70,53°] |
| N4 | `hex_volumes` | non è la quadratura di Gauss che i solutori usano per integrare l'elemento | **ancora vero**, e già dichiarato nella docstring (`quality.py:123-129`); da citare se il volume finisce accanto a una massa del solutore |

### 3.5 Il difetto strutturale: C3D4 — rimediato

Non era un bug, era una scelta che la letteratura contraddice. Le prove, tutte in
[`ricerca-calculix-e-c3d4.md`](ricerca-calculix-e-c3d4.md):

- **La suite di verifica ufficiale di CalculiX non contiene un solo deck C3D4**
  (0 occorrenze su 610 `.inp`). Il tetraedro lineare non è verificato dal proprio
  autore.
- Manuale CalculiX §6.2.6: «not suited for structural calculations... the element
  is too stiff. Please use the 10-node tetrahedral element instead.»
- Abaqus *Getting Started*: «You should not use a mesh containing only linear
  tetrahedral elements (C3D4).»
- Benzley et al. 1995, mensola con soluzione analitica: **31,5% di errore sullo
  spostamento e 21,2% sulla tensione** a maglio grossolano; a maglio fine lo
  spostamento scende a 10,5% ma **la tensione resta a 21,0%** — raffinare non
  salva il campo tensionale. Con ν = 0,49 si arriva a **71,7%**.
- Modale: **20-75%** di errore, e per Ritz-Galerkin è una **sovrastima** delle
  frequenze.
- Aggravante specifica di CalculiX: usa le funzioni di forma standard anche sugli
  elementi lineari, senza le correzioni proprietarie che Abaqus applica — e lo
  dichiara nel manuale.

Il commit `66b526d` aveva tolto C3D10 dall'esportazione. **È stato rimesso**
(`479d671`, `76bbc00`): `NODI_PER_ELEMENTO` lo contiene di nuovo
(`abaqus.py:539`), la permutazione da TetGen ad Abaqus sta in `volume.py:65` con
due oracoli indipendenti — geometrico in `tests/test_quadratico.py`, patch test
in `tests/validazione/test_patch_test.py` — e la ripartizione della gravità sul
quadratico è corretta (`b7e8df9`, `solve.py:863`). Lo scarto sul nostro caso è
misurato in
[`scarto-c3d4-c3d10-telaio.md`](scarto-c3d4-c3d10-telaio.md).

## 4. Il programma di validazione che ne discende

Sette blocchi, in ordine di dipendenza. Il dettaglio operativo di ciascuno sta nei
documenti di ricerca.

1. **Correzioni** — D1-D8, O1-O5, G1-G3, N1-N4. Erano la premessa: non si valida un
   programma le cui guardie non guardano. **Fatte tredici**; O5 è chiusa in
   parte, D8 l'hanno superata i fatti, e cinque restano vere e si dichiarano
   invece di correggersi (D3, G3, N2, N3, N4). Vedi §3.
2. **Ripristino di C3D10** — esportazione, soluzione, report, e il confronto
   C3D4/C3D10 sullo stesso maglio che quantifica lo scarto **sul nostro caso**.
   **Fatto**: vedi §3.5.
3. **Verifica del codice** (ASME: *code verification*) — patch test di
   Taylor-Simo-Zienkiewicz-Chan 1986; mensola in flessione, torsione e prima
   frequenza contro le soluzioni analitiche di Gere-Timoshenko,
   Timoshenko-Goodier e Hurty-Rubinstein, **le stesse tre che Benzley usa**, così
   che il confronto sia diretto; sei modi rigidi nulli; massa efficace totale
   contro ρV; benchmark NAFEMS LE10 (σ_yy = −5,38 MPa) e FV52 (44,092 Hz, set
   numerico). LE11 (σ_zz = −105 MPa) è ricostruibile ma Abaqus lo tabula solo
   per C3D20/C3D20R: nessun termine di paragone per i tetraedri.
4. **Verifica del calcolo** (ASME: *calculation verification*) — studio di
   convergenza di maglio con estrapolazione di Richardson e GCI di Roache. È
   l'omissione che ASME chiama la più grande del settore.
5. **Verifica geometrica** — M3C2 con segno e significatività, precision/recall a
   soglia sulla materia inventata contro quella mancante, **soglie dichiarate
   prima con la loro fonte**, confronto contro il volume nominale della tavola
   `MURO 1` (477.744.760 mm³ ricalcolati).
6. **Verifica incrociata fra codici** — stesso deck su CalculiX e su Abaqus,
   macchina Windows, a mano. È la prova più forte disponibile senza sperimentale.
7. **Analisi di sensibilità** — separare il contributo dell'incertezza sui
   materiali da quello dell'errore geometrico. Senza questa separazione nessun
   numero della tesi dimostra che il contributo è geometrico.

## 5. Cosa questo programma non potrà dire

Da dichiarare in tesi, non da aggirare:

- **Non c'è validazione sperimentale.** Nessuna prova di carico, nessuna analisi
  modale, nessun accelerometro sul telaio. I livelli 5 e 6 della scala restano
  fuori portata, e nulla va chiamato «validato» nel senso di ASME V&V 10.
- **La tavola `MURO 1` non è versionata** (`.gitignore` la esclude): chi clona il
  repository non ha la verità di riferimento su cui poggia il livello 2.
- **La tavola non dichiara la classe del calcestruzzo**: i parametri meccanici
  restano un'assunzione dell'operatore, ed è esattamente ciò che il blocco 7 deve
  quantificare invece di nascondere.
- **I nomi dei set di faccia sono convenzioni**, non identificazioni delle facce
  fisiche, e `FACE_FRONT`/`FACE_BACK` sono già misurati inutilizzabili sulla
  scansione reale.
