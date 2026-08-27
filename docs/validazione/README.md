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

---

## 1. La scala della forza probatoria, e dove possiamo arrivare

Dalla letteratura letta, sette livelli in ordine crescente:

| liv. | prova | chi lo fa nei 17 articoli | raggiungibile qui? |
|---|---|---|---|
| 0 | il programma gira | Cloud2FEM, art. segmentazione | già fatto |
| 1 | autoconsistenza geometrica (mesh contro nuvola sorgente) | 3 lavori, con C2C < 3 mm su >95% | **già fatto, da irrobustire** |
| 2 | misura diretta indipendente | calibro, volume per riempimento, check point GNSS | **sì — la tavola `MURO 1`** |
| 3 | convergenza numerica (in ASME è *verification*, non validation) | 2 lavori, con i tempi di calcolo | **sì** |
| 4 | auto-validazione incrociata | 3 lavori HBIM | **sì, ma non vale da sola** |
| 5 | prova sperimentale sulla stessa struttura (statica, modale, OMA) | 4 lavori | **no — nessuna prova disponibile** |
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

Ognuno con `file:riga` e con l'oracolo che oggi manca. Ordinati per rischio.

### 3.1 Difetti di correttezza

| # | difetto | dove | perché conta |
|---|---|---|---|
| D1 | `inverted_tets` filtra con `V <= 0.0`, e `nan <= 0.0` è `False`: una mesh con coordinate NaN passa `InvertedElementsError` e viene registrata con `inverted: 0` | `quality.py:48`, guardia a `volume.py:139` | **verde su una mesh corrotta.** Stessa classe che il cancello di finitezza ha chiuso in `solve.py`; `quality.py` non l'ha mai ricevuta |
| D2 | l'ordine delle colonne `.frd` (SXX,SYY,SZZ,SXY,SYZ,SZX) non è mai stato verificato contro un `.frd` di `ccx` vero | `solve.py:477` | gli `.frd` dei test li scrive il test, con trazione monoassiale: stato **invariante per permutazione**. Un ordine sbagliato darebbe un numero plausibile |
| D3 | `controlla_reazioni` confronta `RF` con il peso, ma sotto gravità `RF` **non** è la sola reazione | `solve.py:259` | documentato nel manuale CalculiX §6.11.5. È la causa dei 0,73575 N contro 2,943 attesi. Rimedio ufficiale: `*SECTION PRINT, SOF, SOM` |
| D4 | nessuna guardia sull'ampiezza degli spostamenti | `solve.py` | ccx su deck non vincolato esce **0**, senza warning: `spooles.c:225` scrive su `spooles.out`, e con `MAGIC_TAU = 100.0` la matrice viene fattorizzata lo stesso. La guardia è nostra, non sua |
| D5 | `vertex_deviation` su nuvola vuota rende `[inf, inf, inf]`, che finisce nella mappa colore | `quality.py:442` | non gestito |
| D6 | `build_node_sets` su nodi vuoti solleva `ValueError` grezzo | `abaqus.py:1184` | non guardato |
| D7 | `controlla_picco` su array vuoto solleva `ValueError` grezzo | `solve.py:393` | latente, non attivo |
| D8 | `element_volumes` accetta `colonne == 10`, ma `NODI_PER_ELEMENTO` non contiene più C3D10 dopo `66b526d` | `quality.py:164`, `abaqus.py:429` | ramo morto — **torna vivo se si ripristina C3D10** |

### 3.2 Grandezze senza oracolo

| # | grandezza | dove | stato |
|---|---|---|---|
| O1 | `tet_aspect_ratios` | `quality.py:222` | **zero test.** Il numero va in `metrics.json` e nel report |
| O2 | `boundary_spacing` | `abaqus.py:930` | zero chiamate dirette; sotto ci stanno tutti e sei i set di nodi |
| O3 | `export["volume"]` / `export["mass"]` | `abaqus.py:1463-1464` | in colonna nel report di confronto, nessuna asserzione di valore |
| O4 | `GRAVITY_MM_S2 = 9810.0` | `config.py:22` | nessun test lo asserisce |
| O5 | `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, ingombro/bbox | vari | solo regressione |

### 3.3 Guardie inerti

| # | guardia | dove | esito |
|---|---|---|---|
| G1 | `bimodal` con modi in bin contigui | `quality.py:574` | **falsa per costruzione**: l'ingresso che la fa scattare non esiste |
| G2 | `if not in_contact.any()` in `footprint_coverage` | `abaqus.py:1114` | irraggiungibile su qualunque mesh chiusa |
| G3 | `isfinite(minimo)` e `conteggio == 0` | `solve.py:431`, `:446` | inerti **per progetto e dichiarate tali**: non un difetto, ma nemmeno una difesa |

### 3.4 Nomi che collidono con definizioni standard

| # | metrica | divergenza | rimedio proposto |
|---|---|---|---|
| N1 | `scaled_jacobian` | prende il minimo su **8** angoli; Verdict ne usa **9**, includendo il centro con gli assi principali. Valore sistematicamente **più ottimistico** | **non toccare il codice**: dichiararlo in tesi e nella docstring. Aggiungere il nono punto sposterebbe tutti i numeri già pubblicati |
| N2 | `tet_aspect_ratios` | coincide con Verdict `L_max/(2√6·r)`, **ma non con Abaqus/CAE**, dove «aspect ratio» è spigolo max su spigolo min (l'`edge ratio` di Verdict) | dichiarare quale definizione è, ogni volta che si cita una soglia da manuale |
| N3 | `radius_edge_ratios` come unico vincolo di qualità | il default `-q` di TetGen impone radius-edge ≤ 2,0 e **angolo diedro minimo 0°**: il radius-edge è **cieco agli sliver per costruzione** | affiancare il **minimo angolo diedro**, già calcolato a `quality.py:208` ma non usato come vincolo. Range Verdict: [40°, 70,53°] |
| N4 | `hex_volumes` | non è la quadratura di Gauss che i solutori usano per integrare l'elemento | già dichiarato nella docstring; da citare se il volume finisce accanto a una massa del solutore |

### 3.5 Il difetto strutturale: C3D4

Non è un bug, è una scelta che la letteratura contraddice. Le prove, tutte in
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

Il commit `66b526d` aveva tolto C3D10 dall'esportazione. **Va rimesso.** Costa un
giro di nodi di mezzeria: TetGen produce già i vertici.

## 4. Il programma di validazione che ne discende

Sette blocchi, in ordine di dipendenza. Il dettaglio operativo di ciascuno sta nei
documenti di ricerca.

1. **Correzioni** — D1-D8, O1-O5, G1-G2, N1-N4. Sono la premessa: non si valida un
   programma le cui guardie non guardano.
2. **Ripristino di C3D10** — esportazione, soluzione, report, e il confronto
   C3D4/C3D10 sullo stesso maglio che quantifica lo scarto **sul nostro caso**.
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
