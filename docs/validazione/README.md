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

**Riferimenti al codice verificati contro `main` a `a6e9f81`**, e scritti per **nome** — `quality.mesh_volume`, `solve.controlla_reazioni` — non per
numero di riga: un nome non slitta quando si fonde un ramo. Vedi §3.

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

Aperto il 26/08/2026 su `a07071a`. **Richiuso quasi per intero il 27/08/2026**:
delle venti voci, tredici sono chiuse, una lo è in parte, una l'hanno superata i
fatti, cinque restano vere. **Ogni riferimento di questa sezione è verificato
contro `a6e9f81`**; il dettaglio voce per voce, con l'oracolo che ciascuna ha
oggi, sta in [`inventario-grandezze.md`](inventario-grandezze.md) §6.

**Si cita per nome, non per numero di riga.** La stesura precedente citava
`fed1872` per riga, e la fusione dei sette rami ha spostato 43 di quei
riferimenti su un testo diverso: non rotti, peggio — atterravano su una riga che
*esiste* e dice un'altra cosa. Un nome non slitta a ogni merge, e dove un
simbolo esiste è il simbolo a essere citato.

I riferimenti si ricontrollano a macchina, per riga **e** per nome:
`python docs/validazione/controlla-riferimenti.py docs/validazione/README.md`.
Lo script porta i propri assert in `--autoprova`, e la suite li lancia:
`meshrec/tests/test_riferimenti_documenti.py` chiama quella funzione e passa lo
script su tutti i documenti di questa cartella, così il controllore non resta un
controllore che nessuno controlla.

### 3.1 Difetti di correttezza

| # | difetto | dove oggi | stato |
|---|---|---|---|
| D1 | `inverted_tets` filtrava con `V <= 0.0`, e `nan <= 0.0` è `False`: una mesh con coordinate NaN passava `InvertedElementsError` e veniva registrata con `inverted: 0` | `quality.inverted_tets` | **chiuso** (`757429c`, `69465e1`): il criterio è scritto in positivo, `~(isfinite(V) & (V > 0))`, e copre anche il volume `+inf`. Prova in `tests/test_cancello_finitezza.py` |
| D2 | l'ordine delle colonne `.frd` (SXX,SYY,SZZ,SXY,SYZ,SZX) non era mai stato verificato contro un `.frd` di `ccx` vero | `solve.von_mises` | **chiuso** (`87c7d7c`): uno stato con tutte e sei le componenti distinte, confrontate una per una con Hooke, e tutte e 719 le permutazioni respinte — `tests/validazione/test_ordine_frd.py` |
| D3 | `controlla_reazioni` confronta `RF` con il peso, ma sotto gravità `RF` **non** è la sola reazione | `solve.controlla_reazioni` | **ancora vero, e gestito**: `risolvi` somma la quota tributaria (`solve._quota_tributaria_gravita`) prima del confronto, e l'invariante chiude a rel 1e-6 — `test_solve.test_somma_reazioni_su_un_tetraedro_piu_la_quota_tributaria_eguaglia_il_peso`. Resta il limite documentato nel manuale CalculiX §6.11.5 |
| D4 | nessuna guardia sull'ampiezza degli spostamenti | `solve.controlla_spostamenti` | **chiuso** (`c8d9084`): `controlla_spostamenti` è il sesto verdetto, con rapporto spostamento/dimensione — `test_solve.test_risolvi_porta_il_sesto_verdetto_col_rapporto_calcolabile_a_mano` |
| D5 | `vertex_deviation` su nuvola vuota rendeva `[inf, inf, inf]`, che finiva nella mappa colore | `quality.vertex_deviation` | **chiuso**: solleva `ValueError` col proprio messaggio |
| D6 | `build_node_sets` su nodi vuoti sollevava `ValueError` grezzo | `abaqus.build_node_sets` | **chiuso**: messaggio proprio, e una seconda guardia sui nodi non finiti, che facevano uscire due set **vuoti** in silenzio |
| D7 | `controlla_picco` su array vuoto sollevava `ValueError` grezzo | `solve.controlla_picco` | **chiuso** (`587d138`): messaggio proprio, dichiarato errore del chiamante |
| D8 | `element_volumes` accetta `colonne == 10`, ma `NODI_PER_ELEMENTO` non conteneva più C3D10 dopo `66b526d` | `quality.element_volumes`, `abaqus.NODI_PER_ELEMENTO` | **superato dai fatti** (`479d671`, `76bbc00`): C3D10 è tornato, e quel ramo è vivo |

### 3.2 Grandezze senza oracolo

| # | grandezza | dove oggi | stato |
|---|---|---|---|
| O1 | `tet_aspect_ratios` | `quality.tet_aspect_ratios` | **chiuso** (`aa2716f`): regolare = 1, rettangolo in forma chiusa, degenere → ∞ — `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_regolare_vale_uno`, `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_rettangolo_ha_forma_chiusa`, `test_oracoli_mancanti.test_l_aspetto_di_un_tetraedro_degenere_e_infinito` |
| O2 | `boundary_spacing` | `abaqus.boundary_spacing` | **chiuso** (`aa2716f`): lato del tetraedro regolare, e scala col fattore 2 — `test_oracoli_mancanti.test_la_spaziatura_di_bordo_del_tetraedro_regolare_e_il_suo_lato`, `test_oracoli_mancanti.test_la_spaziatura_di_bordo_scala_con_la_geometria` |
| O3 | `export["volume"]` / `export["mass"]` | `abaqus.export_model` | **chiuso** (`aa2716f`): scatola nota, rel 1e-6 — `test_oracoli_mancanti.test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola` |
| O4 | `GRAVITY_MM_S2 = 9810.0` | `config.GRAVITY_MM_S2` | **chiuso** (`aa2716f`): asserita contro 9,81·1000, e ρ·V·g → N sull'acqua — `test_oracoli_mancanti.test_la_gravita_e_novecentootto_metri_al_secondo_quadro_in_millimetri`, `test_oracoli_mancanti.test_densita_per_volume_per_gravita_da_newton` |
| O5 | `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, ingombro/bbox | `volume.tetrahedralize_with_metrics`, `quality.thickness`, `solve._spostamento_massimo`, `io.load_cloud` | **chiuso in parte**: i primi tre hanno ora un oracolo (`test_oracoli_mancanti.test_l_ingombro_di_una_lastra_allineata_e_il_suo_spessore`, `test_oracoli_mancanti.test_il_percentile_del_raggio_spigolo_e_davvero_un_percentile`, `test_solve.test_risolvi_porta_il_sesto_verdetto_col_rapporto_calcolabile_a_mano`); ingombro/bbox resta solo regressione, ed è `max − min` per asse |

### 3.3 Guardie inerti

| # | guardia | dove oggi | stato |
|---|---|---|---|
| G1 | `bimodal` con modi in bin contigui, falsa per costruzione | `quality.thickness` | **chiuso** (`0a622a5`): la condizione è scritta come esito, `upper > lower + 1`, e il commento dice perché la forma precedente non poteva dare `True` |
| G2 | `if not in_contact.any()` in `footprint_coverage` | `abaqus.footprint_coverage` | **chiuso** (`0a622a5`): solleva invece di rendere `0.0`, che si sarebbe letto come «copre nulla». Il ramo resta irraggiungibile dalla pipeline, ma ora se ci si arriva si sa |
| G3 | `isfinite(minimo)` e `conteggio == 0` | `solve.controlla_vincolo_in_pianta`, `solve.controlla_avvisi` | **ancora vero**: inerti **per progetto e dichiarate tali** nelle docstring. Non un difetto, ma nemmeno una difesa |

### 3.4 Nomi che collidono con definizioni standard

| # | metrica | divergenza | stato |
|---|---|---|---|
| N1 | `scaled_jacobian` | prendeva il minimo su **8** angoli; Verdict ne usa **9**, includendo il centro con gli assi principali | **chiuso** (`0a622a5`): il nono punto c'è (`quality.scaled_jacobian`). La misura ha smentito il timore che l'aveva sconsigliato: **nessun numero pubblicato si è spostato**. La metà in albero è `test_guardie_e_nomi.test_su_magli_veri_il_nono_punto_non_sposta_nulla`, duecento esaedri; le cifre più grandi — 1644 esaedri di tre prismi gmsh, 148.689 cubi perturbati — sono state **misurate una volta il 26/08/2026 fuori dall'albero, nel giro di `0a622a5`, e non sono riproducibili qui**: nessuno script le genera |
| N2 | `tet_aspect_ratios` | coincide con Verdict `L_max/(2√6·r)`, **ma non con Abaqus/CAE**, dove «aspect ratio» è spigolo max su spigolo min (l'`edge ratio` di Verdict): sul rettangolo di lato 1, 1,366 contro 1,414 | **ancora vero**, e ora dichiarato nella docstring (`quality.tet_aspect_ratios`) oltre che nel registro delle soglie. Dichiarare quale definizione è, ogni volta che si cita una soglia da manuale |
| N3 | `radius_edge_ratios` come unico vincolo di qualità | il default `-q` di TetGen impone radius-edge ≤ 2,0 e **angolo diedro minimo 0°**: il radius-edge è **cieco agli sliver per costruzione** | **ancora vero**, e ora misurato nella docstring (`quality.radius_edge_ratios`): uno sliver dà 0,707 di raggio-spigolo e 0,162° di diedro. Affiancare il minimo angolo diedro, che `quality.min_dihedral_angles` già calcola ma che non è usato come vincolo. Range Verdict: [40°, 70,53°] |
| N4 | `hex_volumes` | non è la quadratura di Gauss che i solutori usano per integrare l'elemento | **ancora vero**, e già dichiarato nella docstring (`quality.hex_volumes`); da citare se il volume finisce accanto a una massa del solutore |

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
(`479d671`, `76bbc00`): `abaqus.NODI_PER_ELEMENTO` lo contiene di nuovo,
la permutazione da TetGen ad Abaqus sta in `volume.TETGEN_A_ABAQUS` con
due oracoli indipendenti — geometrico in `tests/test_quadratico.py`, patch test
in `tests/validazione/test_patch_test.py` — e la ripartizione della gravità sul
quadratico è corretta (`b7e8df9`, `solve._quota_tributaria_gravita`). Lo scarto sul nostro caso è
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

   **Parziale.** Fatte quattro voci su sette, ciascuna col proprio test su `ccx`
   vero: patch test A e B (`tests/validazione/test_patch_test.py`); mensola in
   **flessione** contro Eulero-Bernoulli e Timoshenko, e **prima frequenza**
   contro Hurty-Rubinstein (`tests/validazione/test_mensola.py`); **LE10**
   (`tests/validazione/test_nafems_le10.py`); **FV52** contro il set numerico
   (`tests/validazione/test_nafems_fv52.py`).

   Mancano tre voci, e nessuna è coperta da ciò che c'è:
   - **torsione** contro Timoshenko-Goodier: nessun deck e nessun test. Il
     docstring di `test_mensola.py` riporta due incoerenze **dentro** il paper di
     Benzley proprio sui numeri torsionali — la tensione tagliante stampata è il
     doppio di quella coerente coi suoi spostamenti, e il suo 2614 Hz torsionale
     corrisponde a ν = 0,49 — e rimanda a un ticket sulla torsione che non è
     stato aperto;
   - **sei modi rigidi nulli**: la soglia `modi_rigidi_numero` sta nel registro
     di `core/soglie.py` e vale **6**, ma nessun test la consuma. FV52 ne
     verifica **tre**, ed è un'altra cosa: quel modello lascia liberi x e y per
     costruzione, quindi tre moti rigidi sono ciò che deve uscire da *quel*
     problema. Il patch test i sei moti rigidi li **toglie** con tre ancore, non
     li misura. Serve un modello libero-libero;
   - **massa efficace totale contro ρV**: `solve.leggi_massa_modale` e
     `solve.controlla_massa_modale` esistono, ma confrontano la massa
     **catturata** con quella **disponibile**, entrambe lette dal `.dat` — è la
     frazione di massa che i modi prendono, non l'identità aritmetica contro
     ρ·V. La soglia `massa_efficace_relativo` è dichiarata nel registro e la sua
     nota la chiama «un'identità aritmetica contro ρ·V»; nessun test la consuma.
4. **Verifica del calcolo** (ASME: *calculation verification*) — studio di
   convergenza di maglio con estrapolazione di Richardson e GCI di Roache. È
   l'omissione che ASME chiama la più grande del settore.

   **Parziale.** Il metodo c'è ed è verificato: `core/convergenza.py` con
   l'ordine osservato, l'estrapolazione e la GCI col fattore di Roache,
   `tests/test_convergenza.py` sugli oracoli in forma chiusa e
   `tests/validazione/test_convergenza_mensola.py` su `ccx` vero. La misura sta
   in [`convergenza-di-maglio.md`](convergenza-di-maglio.md), che pubblica anche
   il risultato che serviva a non citarla male: su C3D10 la GCI **non** è una
   barra d'errore verso la verità.

   Manca sul **pezzo**, ed è misurato che raffinando il volume non si ottiene:
   con `nobisect=True` il limite di volume non viene applicato e i rapporti di
   raffinamento effettivi valgono 1,173 e 1,059 contro l'1,3 minimo di Celik;
   con `nobisect=False` TetGen fallisce. La manopola vera è la superficie, ma
   girarla cambia la geometria e le tre griglie non sarebbero più lo stesso
   solido. **È una decisione aperta, non un'esecuzione mancata**, e il documento
   la registra come tale.
5. **Verifica geometrica** — M3C2 con segno e significatività, precision/recall a
   soglia sulla materia inventata contro quella mancante, **soglie dichiarate
   prima con la loro fonte**, confronto contro il volume nominale della tavola
   `MURO 1` (477.744.760 mm³ ricalcolati).

   **Parziale.** Fatte due voci: la decomposizione con segno con
   precision/recall a soglia — `quality.scarto_con_segno`, misurata sul telaio
   in [`scarto-con-segno.md`](scarto-con-segno.md), con la controprova che
   riproduce cifra per cifra il `cloud_to_mesh` già pubblicato — e il registro
   delle soglie `core/soglie.py`, dove ognuna porta `fonte`, `origine` e la data
   in cui è stata fissata, `errore_geometrico_max` compresa.

   Mancano due voci:
   - **M3C2**: non è implementata, ed è una scelta dichiarata, non una
     dimenticanza. `scarto-con-segno.md` argomenta che la significatività locale
     di M3C2 serve fra due nuvole rumorose e non fra una nuvola e una superficie;
     ciò che se ne raccoglie è il principio del segno. Chi vorrà M3C2 vero deve
     riaprirla come decisione;
   - **confronto contro il volume nominale di `MURO 1`**: non esiste in albero,
     né come misura né come test. È il livello 2 della scala del §1, ed è
     l'unico anello che poggia su un dato **non versionato** (vedi §5).
6. **Verifica incrociata fra codici** — stesso deck su CalculiX e su Abaqus,
   macchina Windows, a mano. È la prova più forte disponibile senza sperimentale.

   **Da fare.** In albero c'è solo la soglia `incrociato_calculix_abaqus` del
   registro, che dichiara quanto i due solutori possano discostarsi; nessuna
   corsa l'ha ancora esercitata. Resta al futuro, coerentemente: la licenza
   Abaqus sta su un'altra macchina e il confronto si fa a mano.
7. **Analisi di sensibilità** — separare il contributo dell'incertezza sui
   materiali da quello dell'errore geometrico. Senza questa separazione nessun
   numero della tesi dimostra che il contributo è geometrico.

   **Parziale, ed è la metà che si poteva calcolare esattamente.** In elasticità
   lineare la propagazione è in forma chiusa e non campionata: freccia ∝ 1/E,
   frequenza ∝ √(E/ρ), densità ininfluente sulla freccia sotto carico imposto, ν
   trascurabile con lo 0,29% su tutto il suo intervallo. Le quattro leggi sono
   verificate su `ccx` vero in
   `tests/validazione/test_sensibilita_materiali.py`, e gli intervalli normativi
   stanno in [`materiali-intervallo.md`](materiali-intervallo.md): **±8%** su E a
   classe nota, **±34%** ad aggregato ignoto — ed è la seconda riga a valere,
   perché la tavola non dichiara né la classe né l'aggregato.

   Manca **il confronto con l'errore geometrico**, cioè esattamente la
   separazione che il blocco promette: c'è la banda dei materiali e c'è, dal
   blocco 5, l'errore geometrico, ma nessun documento li mette sullo stesso
   asse. Il docstring del test lo dichiara per primo — «cosa questo ticket NON
   chiude».

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
