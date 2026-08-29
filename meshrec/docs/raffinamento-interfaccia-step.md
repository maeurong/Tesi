# Raffinamento dell'interfaccia, step per step

Registro delle modifiche decise durante la revisione step per step del
28/08/2026. Non è ancora una specifica: è l'elenco di ciò che l'utente ha
chiesto di cambiare, uno step alla volta, prima di scrivere il piano.

## Step 1 · Lettura

1. **`scale` diventa due menù a tendina, non una casella di testo.**
   - Primo menù: il fattore di scala del rilievo. Valori ammessi:
     `1, 2, 5, 10, 20, 50, 100, 1000`. Si leggono come rapporti — `1` è 1:1,
     `10` è 1:10.
   - Secondo menù: l'unità di misura a cui quel fattore si riferisce. Valori
     ammessi: `m`, `cm`, `mm`.
   - Lettura combinata: fattore `1` con unità `cm` significa «la nuvola è già
     in centimetri e ci resta».
   - Le due scelte insieme producono il numero che oggi si scrive a mano in
     `input.scale`.

2. **`expected_size` diventa tre caselle di testo libero**, una per misura
   reale, affiancate dall'unità di misura scelta nel menù di `scale`. Le tre
   caselle **possono restare vuote**: vuote significa «nessun controllo di
   scala richiesto», che è il comportamento predefinito di oggi
   (`expected_size = None`). Oggi il campo è in sola lettura nel pannello e si
   modifica solo dal `config.yaml`.

## Step 2 · Segmentazione

1. **`method` diventa un menù a tendina** con i due soli valori ammessi:
   `crop` e `auto`. Oggi è una casella di testo, come tutti gli altri campi.

2. **`plane_min_points_ratio` diventa uno slider** dal minimo al massimo del
   suo dominio (0 e 1), affiancato da una casella di testo che mostra il
   valore scelto e permette di scriverlo a mano.

3. **Aperto: il nome dello step.** Un tutor sostiene che «la segmentazione è
   un'altra cosa». Ricerca in letteratura affidata il 28/08/2026; l'esito va in
   `docs/validazione/ricerca-terminologia-segmentazione.md`. Se il tutor ha
   ragione, cambia il nome dello step — e con esso l'etichetta
   `02_segment`/«Segmentazione» nell'interfaccia.

### Esito della ricerca sul nome dello step 2

Documento: `docs/validazione/ricerca-terminologia-segmentazione.md`
(scritto il 28/08/2026, controllore dei riferimenti superato: 18 riferimenti,
0 rotti).

Verdetto: **il tutore ha ragione in parte.** `remove_outliers` e `crop_box` non
sono segmentazione in nessuna tassonomia — sono pre-processing. `extract_planes`
(RANSAC) e `cluster` (DBSCAN) lo sono senza ambiguità, e appartengono a due
delle cinque famiglie canoniche. Lo step non è invece *semantic segmentation*:
non assegna classi, sceglie un sottoinsieme.

Il difetto vero è la riga di interfaccia: `PROPOSITI["02_segment"]` descrive
solo la metà di pre-processing e tace RANSAC e DBSCAN. Correzione minima e
sufficiente: riscrivere quella frase perché nomini tutte e tre le cose che lo
step fa. Da decidere se cambiare anche `ETICHETTE["02_segment"]` da
«Segmentazione» a «Isolamento», che è il nome che la docstring del modulo già
usa.

## Step 5 · Superficie

1. **`method` diventa un campo bloccato** con scritto `poisson`. Ha un valore
   solo: una casella che si può scrivere e che rifiuta qualunque cosa le si
   scriva dentro è una casella che mente.

2. **`poisson_depth` diventa uno slider** da 4 a 14, gli estremi che il modello
   già impone. Valori interi.

3. **`density_quantile` diventa uno slider** da 0 a 1, affiancato da una casella
   di testo che mostra il valore e permette di scriverlo a mano.

*(Da confermare: se anche `poisson_depth` debba avere la casella di testo
accanto allo slider, come `density_quantile` e `plane_min_points_ratio`. Qui è
scritta solo per gli altri due.)*

## Step 6 · Riparazione

1. **`largest_component_only` diventa una casella da spuntare.** Oggi è una
   casella di testo in cui si batte `true` o `false`.

2. **`join_components` diventa una casella da spuntare.** Stesso motivo.

## Step 8 · Semplificazione

1. **`enabled` va rinominato**: il nome non dice che cosa si sta accendendo.
   Diventa una casella da spuntare, con un'etichetta che nomina l'operazione
   (per esempio «rifà i triangoli a misura uniforme»).

2. **`mode` diventa un campo bloccato** con scritto `remesh`. Stessa ragione di
   `method` allo step 5: un valore solo.

**Nota su come rinominare.** PRODUCT.md fissa già la regola: «una chiave non si
stampa mai, si stampa la sua etichetta». Oggi l'interfaccia stampa la chiave
grezza come etichetta di **ogni** parametro, e `enabled` è il caso in cui la
regola mancante fa più danno. Assunzione presa: si rinomina **l'etichetta a
video**, non la chiave `simplify.enabled` — che vive nei `config.yaml` delle
corse di riferimento, nei registri di sweep e nei test, e cambiarla romperebbe
la rileggibilità di corse già in tesi. Da confermare.

## Step 9 · Tetraedri

1. **`nobisect` diventa una casella da spuntare.**

2. **`element` diventa un menù a tendina** con `C3D10` e `C3D4`, i due soli
   valori ammessi.

3. **`reference_ratio` si sposta nel pannello dello step 10**, dove appartiene:
   è il metro con cui lo step 10 conta gli elementi fuori vincolo, e non tocca
   nulla di ciò che lo step 9 fa.

**Nota tecnica sullo spostamento.** `STEP_BLOCKS` in `core/steps.py` assegna il
blocco `tet` intero sia allo step 9 sia al 10, e `/api/schema` costruisce i
pannelli da quella tabella: per questo `reference_ratio` compare due volte.
La tabella **non va toccata** — è la stessa che governa l'invalidazione a valle,
e togliere `tet` dallo step 10 romperebbe la catena delle impronte. Lo
spostamento va fatto a grana di **campo** e non di blocco, cioè in
`/api/schema`: quali campi di un blocco appartengono a quale step.

## Step 10 · Qualità volume

1. **`reference_ratio` compare qui**, non nel pannello dello step 9 (vedi la
   nota tecnica dello step 9). Non sostituisce `min_ratio`: `min_ratio` è
   l'ordine dato a TetGen e cambia il maglio, `reference_ratio` è il metro con
   cui lo step 10 conta gli elementi fuori vincolo e non cambia nulla.

## Step 11 · Esportazione

### Correzioni al pannello (piccole)

1. **Togliere la sezione `tet`.** I parametri della tetraedrizzazione non si
   regolano da qui. Come per `reference_ratio`, lo spostamento va fatto a grana
   di campo in `/api/schema`, senza toccare `STEP_BLOCKS`.

2. **Togliere la sezione `selettori`.** È vuota per costruzione: `selettori` è
   un `dict[NomeSet, Selettore]` e non un modello con campi fissi, quindi
   `/api/schema` non ha niente da elencare. Una sezione che non può mai
   contenere nulla non deve comparire.

3. **Spostare la sezione `carichi` più avanti**, dove i carichi si dichiarano
   davvero.

4. **In `analysis` resta il solo `set_tolerance_factor`.**

   *Punto aperto:* `gravity`, `fixed_nset` e `step_name` sono gli altri tre
   campi di `analysis`, e lo step 11 li usa per scrivere il deck. Assunzione
   presa: seguono `carichi` nel pannello dei carichi, perché descrivono il caso
   di carico e non la geometria. Da confermare.

5. **Manca l'esportazione vera e propria.** Oggi lo step scrive
   `wall_model.inp` dentro `runs/<nome>/` e lì resta: `server.py` non ha nessuna
   tratta che consegni un file all'utente (le sole `FileResponse` servono
   `index.html` e gli statici dell'interfaccia). Per portare il deck in Abaqus
   bisogna andarselo a cercare nel filesystem. Serve un comando che consegni il
   file — «Salva il deck…» o equivalente.

### Il materiale: multimateriale con suddivisione e database

Richiesta di Mario, 28/08/2026: il modello oggi è **monomaterico** — `write_inp`
scrive un solo `*SOLID SECTION, ELSET=ALL_WALL, MATERIAL=<nome>` — e deve
diventare multimateriale. Il programma deve suddividere la struttura in elementi
(o proporre una suddivisione che l'utente corregge), e a ciascun elemento
l'utente assegna un materiale preso da un **database** (i dati li fornirà Mario).
Tutto questo anche in vista di una futura integrazione di **OpenSees** come
secondo solutore.

**Non è una correzione dello step 11: è un sottosistema nuovo.** Vedi la nota di
classificazione nel corpo della revisione.

**Fatto utile, già nel repository:** lo step 12 (`wall.prior`) *già* scompone la
geometria in membrature, e per ciascuna misura asse, origine, lunghezza,
sezione, contorno, volume e stato di riempimento. La suggerimento di
suddivisione non nasce da zero — nasce da lì.

## Step 12 e 13 · Prior geometrico e analisi strutturale

Indicazione di Mario, 28/08/2026, in forma di direzione e non di dettaglio:

**L'analisi strutturale esce dalla finestra della pipeline.** Oggi lo step 13
vive nella stessa colonna degli altri dodici, come se fosse un passo di
elaborazione geometrica. Non lo è: è l'unico step che paga un processo esterno
vero (`ccx`), l'unico che legge un deck invece di una geometria, e l'unico i cui
risultati sono campi sul maglio e non artefatti della catena.

Va in una **finestra a parte**, che diventa il **pre e post processore** di due
solutori: **CalculiX** (già integrato) e **OpenSees** (da integrare).

Questo assorbe anche i punti lasciati aperti allo step 11: i carichi, `gravity`,
`fixed_nset` e `step_name` appartengono a quella finestra, non al pannello
dell'esportazione.

---

# Riepilogo: che cosa è bounded e che cosa non lo è

**Correzioni bounded**, tutte sui campi dell'interfaccia, indipendenti fra loro:

| Step | Correzione |
|---|---|
| 1 | `scale` in due menù a tendina (fattore, unità) |
| 1 | `expected_size` in tre caselle libere, vuote ammesse, con l'unità di `scale` |
| 2 | `method` a menù a tendina (`crop`, `auto`) |
| 2 | `plane_min_points_ratio` a slider 0–1 con casella |
| 2 | riscrivere `PROPOSITI["02_segment"]` (esito della ricerca) |
| 5 | `method` a campo bloccato |
| 5 | `poisson_depth` a slider 4–14 |
| 5 | `density_quantile` a slider 0–1 con casella |
| 6 | `largest_component_only` e `join_components` a casella da spuntare |
| 8 | `enabled` rinominato a video, a casella da spuntare |
| 8 | `mode` a campo bloccato |
| 9 | `nobisect` a casella da spuntare |
| 9 | `element` a menù a tendina (`C3D10`, `C3D4`) |
| 9→10 | `reference_ratio` spostato nel pannello dello step 10 |
| 11 | via le sezioni `tet` e `selettori` dal pannello |
| 11 | `carichi` spostati nella finestra dell'analisi |
| 11 | in `analysis` resta il solo `set_tolerance_factor` |
| 11 | comando che consegna il deck `.inp` all'utente |

Una regola le attraversa quasi tutte, ed è già scritta in PRODUCT.md: **«una
chiave non si stampa mai, si stampa la sua etichetta»**. Oggi `campoParametro`
stampa la chiave grezza come etichetta di ogni parametro e rende ogni campo come
casella di testo, perché `/api/schema` non manda il tipo. Le correzioni per step
sono, in fondo, un'unica correzione: far arrivare il tipo e l'etichetta dallo
schema, e far scegliere alla casella la propria forma.

**Non bounded**, e da aprire con `/wayfinder`:

1. **Multimateriale**: suddivisione della struttura in elementi, database dei
   materiali, assegnazione per elemento. Punto di partenza già nel repository:
   le membrature dello step 12.
2. **Finestra dell'analisi strutturale**: pre e post processore per CalculiX e
   OpenSees.

I due sono legati: il modello dei materiali che serve al primo è lo stesso che
il secondo deve scrivere in due dialetti diversi.
