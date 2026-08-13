# Fase 1 — esiti sulla scansione reale `lab_frame.pcd`

Documento di verifica della segmentazione automatica (step 2, `segment.method: auto`)
sui dati reali. Tutti i numeri qui riportati sono misurati, non stimati.

Macchina: Windows 11, 12 CPU logiche, 16 GB di RAM, con un secondo processo Python
attivo in parallelo che ne occupava fra 5 e 11 GB. Unità di lavoro: mm, N, MPa,
tonnellata, secondo.

## 1. Determinazione della scala

Prima esecuzione dello step 1 senza `expected_size`, con `scale: 1.0`, per leggere
l'ingombro grezzo:

| grandezza | valore |
| --- | --- |
| punti letti | 6 329 096 |
| punti scartati (coordinate non finite) | 0 |
| ingombro | 2,759 × 0,785 × 2,000 |
| spaziatura media al vicino più prossimo | 0,001192 |
| tempo di lettura | 10 s |

Un ambiente di laboratorio ha dimensioni dell'ordine dei metri, e un ingombro
dell'ordine delle unità non può che essere in metri: la nuvola è espressa in metri
e il fattore corretto è **`scale: 1000`**. Nelle unità di lavoro l'ingombro diventa
**2759 × 785 × 2000 mm** e la spaziatura media **1,192 mm**.

Va detto che la scala è dedotta dall'ordine di grandezza, non confermata: manca una
misura indipendente del muro, quindi `expected_size` è rimasto nullo e il controllo
di scala di `io.load_cloud` non è mai stato esercitato su questa nuvola. Una
misura in campo di una sola quota nota chiuderebbe la questione.

## 2. Che cosa contiene la scansione

Prima di giudicare la segmentazione serve sapere che cosa si sta segmentando. Le
mappe di occupazione per coppie di assi e la geometria dei piani estratti da RANSAC
danno un quadro univoco: la scansione non inquadra una stanza, ma **un singolo muro
di prova con una grande apertura**, ripreso su entrambe le facce.

- l'asse *x* corre lungo il muro (1697 → 4457 mm, lunghezza 2759 mm);
- l'asse *y* è lo spessore (−703 → 82 mm);
- l'asse *z* è l'altezza (−781 → 1219 mm, altezza 2000 mm).

Elementi riconosciuti, con i numeri che li identificano:

| elemento | evidenza |
| --- | --- |
| faccia posteriore | piano RANSAC a *y* ≈ −402, normale (0,005; 1,000; 0,002), estensione 2733 × 20 × 1965 mm |
| faccia anteriore | piano RANSAC a *y* ≈ −226, normale (0; −1; 0), estensione 2732 × 5 × 1970 mm |
| spessore del muro | distanza fra le due facce, **≈ 176 mm** |
| base orizzontale | piano RANSAC a *z* ≈ −510, normale (0,002; −0,005; 1,000), estensione 2731 × 742 × 11 mm; è più profonda del muro, quindi non è il muro ma il piano su cui poggia |
| intradosso dell'architrave | superficie orizzontale a *z* ≈ 1013, estensione 2093 × 168 × 46 mm: attraversa tutto lo spessore del muro |
| spalla dell'apertura | superficie verticale a *x* ≈ 1875, estensione 26 × 162 × 1400 mm |
| testate del muro | superfici verticali a *x* ≈ 4130 ÷ 4139, normale ≈ (1; 0; 0) |

L'apertura è quindi larga circa 2093 mm e alta circa 1400 mm: è il tratto della
scansione più rilevante per la Fase 2, perché è esattamente il caso che
`punch_holes` deve saper trattare.

## 3. Segmentazione automatica sulla nuvola intera

Configurazione: `segment.method: auto` con tutti i parametri ai valori predefiniti
di `SegmentConfig` (`outlier_neighbors: 20`, `outlier_std_ratio: 2.0`,
`plane_distance_factor: 3.0`, `plane_max_count: 4`, `plane_min_points_ratio: 0.05`,
`cluster_eps_factor: 4.0`, `cluster_min_points: 50`, `cluster_index: 0`), su tutti i
6 329 096 punti, senza alcun ritaglio.

**La segmentazione automatica arriva in fondo senza difficoltà.** Non è mai stato
necessario ridurre il costo: nessuna delle due strade previste dal mandato
(`voxel_size` esplicito o ritaglio preliminare) è servita per far girare lo step 2.

| fase | tempo | esito |
| --- | --- | --- |
| rimozione outlier statistici | 10 s | 244 304 punti rimossi, ne restano 6 084 792 |
| RANSAC iterativo (4 piani) | 64 s | 4 piani estratti, residuo 4 221 830 punti |
| DBSCAN sul residuo | 42 s | 3309 cluster, 2 452 663 punti classificati come rumore |
| **totale step 2** | **≈ 127 s** | — |

Metriche richieste dalla specifica:

| metrica | valore |
| --- | --- |
| piani estratti (`planes_found`) | 4 |
| punti per piano (`plane_points`) | 612 748 / 450 159 / 440 424 / 359 631 |
| soglia RANSAC (`plane_distance`) | 3,577 mm (= 3,0 × 1,192) |
| punti residui | 4 221 830 |
| cluster trovati (`clusters_found`) | 3309 |
| raggio DBSCAN (`cluster_eps`) | 4,769 mm (= 4,0 × 1,192) |
| punti di rumore | 2 452 663 |
| primi cluster per numerosità | 639 655 / 281 084 / 103 297 / 36 990 / 32 172 |
| punti nel cluster scelto (`cluster_points`) | 639 655 |
| planarità (`planarity_rms`) | 3,84 mm |
| spessore stimato (`thickness`) | 41,85 mm |
| normale del cluster scelto | (0,004; −0,008; 1,000) |

### Il muro isolato non è quello atteso

Il cluster restituito con `cluster_index: 0` è **orizzontale** — la sua normale è
diretta lungo *z* — ha estensione 2093 × 168 × 46 mm ed è centrato a *z* = 1013 mm:
è l'**intradosso dell'architrave dell'apertura**, non il muro.

La causa non è una taratura sbagliata dei parametri, ma il modo in cui il metodo è
costruito. `auto` estrae i piani dominanti con RANSAC, **li scarta**, e cerca il
muro fra i cluster di ciò che resta. Questo isola bene un oggetto non planare che
si stagli davanti a superfici planari, ed è esattamente ciò che accade nella scena
sintetica del test `test_auto_mode_isolates_the_wall`, dove il pavimento è il piano
dominante e il muro sopravvive nel residuo. Sui dati reali il rapporto si rovescia:
**le due facce del muro sono esse stesse i piani dominanti**, quindi finiscono nel
sacchetto degli scarti già alla prima e alla seconda iterazione di RANSAC (612 748 e
450 159 punti; il quarto piano, 359 631 punti a *y* ≈ −413, è una seconda falda
della stessa faccia posteriore). Nel residuo restano solo gli sguinci
dell'apertura, le testate e gli oggetti attorno, e il più numeroso fra questi è
l'intradosso dell'architrave.

Cambiare `cluster_index` non risolve: il secondo cluster (281 084 punti) è la spalla
dell'apertura, il terzo (103 297) è una testata. Nessun cluster del residuo contiene
il muro, perché il muro non è nel residuo.

Su questo punto una versione precedente di questo documento concludeva l'opposto,
cioè che `cluster_index: 1` isolasse un muro, leggendo la sua normale lungo *x* e la
sua planarità di 3,49 mm come quelle di una parete intonacata. I numeri erano gli
stessi qui riportati; la lettura no. Il riquadro di quel cluster è
x ∈ [1862,5; 1888,5], y ∈ [−394,5; −232,5], z ∈ [−206,5; 1193,5], cioè **26 mm di
larghezza, 162 mm di profondità e 1400 mm di altezza**. Una faccia di muro è estesa
in lunghezza e altezza e sottile nello spessore; questa superficie è sottile nella
lunghezza ed estesa esattamente quanto lo spessore del muro (162 mm contro 176 mm).
È la spalla dell'apertura vista di taglio, non una parete. La differenza fra le due
letture non sta in una misura in più, ma nell'avere guardato la geometria d'insieme
prima delle singole normali.

### Variante provata: ritaglio a box seguito da solo DBSCAN

Poiché il problema è l'estrazione dei piani, si è provata la combinazione che la
disattiva: `method: auto` con `plane_max_count: 0` e un ritaglio preliminare sulla
fascia del muro, `crop_min: [1690, −450, −480]`, `crop_max: [4460, −190, 1230]`.

| metrica | valore |
| --- | --- |
| punti dopo il ritaglio | 4 229 538 |
| piani estratti | 0 (disattivati) |
| cluster trovati | 3314 |
| punti di rumore | 1 542 610 |
| punti nel cluster scelto | 1 505 970 |
| estensione del cluster scelto | 2340 × 209 × 1256 mm |
| planarità | 60,42 mm |
| spessore stimato | 295,4 mm |
| tempo | 63 s |

Neanche questa isola il muro: il cluster più numeroso raccoglie solo il 36% dei
punti del ritaglio e si ferma alla parte alta (centro a *z* = 922 mm, altezza
1256 mm contro i 1710 mm del box). Con `cluster_eps` a 4,769 mm il DBSCAN non
scavalca le lacune della scansione, e il muro si frantuma in 3314 pezzi invece di
restare un corpo unico. Alzare `cluster_eps_factor` fino a ricucire il muro
significherebbe alzarlo fino a ricucire anche tutto ciò che lo tocca, base
compresa: si tornerebbe a un unico cluster che contiene la scena intera.

## 4. Decisione

**Su questa scansione la segmentazione automatica non isola il muro, e non per
mancanza di risorse.** Lo step 2 in modalità `auto` gira per intero sui 6,3 milioni
di punti in circa due minuti e con una memoria compatibile con questa macchina: il
limite è semantico, non computazionale. Il metodo presuppone che il bersaglio sia
ciò che *non* è planare, mentre qui il bersaglio *è* la coppia di piani dominanti.

La strada realistica per questa nuvola è quindi **il ritaglio manuale a box**,
`segment.method: crop`, che è precisamente la ragione per cui il ritaglio esiste
nella pipeline. Con `crop_min: [1690, −470, −480]` e `crop_max: [4460, −180, 1230]`
il box trattiene 4 229 538 punti, ingombro 2471 × 231 × 1697 mm, direzione di minore
estensione (0,008; 1,000; −0,007), cioè lo spessore lungo *y* come atteso: entrambe
le facce del muro e gli sguinci dell'apertura restano dentro, la base e il pavimento
restano fuori.

Per la Fase 2 restano due indicazioni, entrambe ricavate da questi numeri:

1. `auto` non va tarato meglio, va **rovesciato**: per un muro la scelta naturale è
   tenere i piani estratti da RANSAC invece di scartarli, raggruppando i piani
   quasi paralleli e vicini fra loro (qui i piani 0, 3 a *y* ≈ −402 ÷ −413 e il
   piano 1 a *y* ≈ −226, che insieme descrivono un muro di 176 mm di spessore). È
   un cambiamento di criterio di selezione, non di algoritmo: `extract_planes` e
   `cluster` restano quelle che sono.
2. lo spessore di 176 mm e l'apertura di 2093 × 1400 mm sono le grandezze di
   riferimento con cui confrontare il modello ricostruito.

## 5. Fin dove arriva la pipeline sui dati reali

Stabilito che la via praticabile è il ritaglio, si è eseguita la pipeline completa
su `lab_frame.pcd` con `segment.method: crop`, il box indicato sopra,
`downsample.voxel_size: 10.0` esplicito e i parametri della tetraedrizzazione ai
**predefiniti attuali** (`tet.min_ratio: 1.8`, `tet.max_steiner_points: -1`).

**Fonte dei numeri di questa sezione:** `runs/lab_crop/metrics.json`, corsa dal
primo step del 13 agosto 2026 con il codice corrente. Sostituiscono
integralmente quelli che una versione precedente di questo documento riportava
qui, ottenuti con codice poi corretto e con `min_ratio: 1.1`: quella corsa
dichiarava un deck Abaqus completo e non lo era. La ricostruzione di che cosa
fosse davvero è nella sotto-sezione «La corsa superata», più sotto. Le sezioni
da 1 a 4 di questo documento non sono toccate: riguardano gli step 1 e 2, il cui
codice non è cambiato, e la corsa nuova ne riproduce i numeri identici
(6 329 096 punti letti, spaziatura 1,1923 mm, 4 229 538 punti dopo il ritaglio).

Il risultato è che **la pipeline non arriva in fondo su questa scansione**: gli
step da 1 a 8 girano regolarmente e in tempi modesti, e lo step 9 fallisce.

| step | esito |
| --- | --- |
| 1 lettura | 6 329 096 punti, nessuno scartato, spaziatura media 1,1923 mm, ingombro 2759,0 × 785,0 × 2000,0 mm |
| 2 ritaglio | 244 304 punti isolati rimossi, 4 229 538 punti dentro il box |
| 3 riduzione a voxel (10 mm) | da 4 229 538 a 116 059 punti, riduzione del 97,3% |
| 4 normali | nessuna normale degenere |
| 5 Poisson (profondità 9) | 10 521 vertici scartati al quantile di densità 0,05 (soglia 8,1796), 199 891 vertici e 398 044 triangoli |
| 6 riparazione | 3 vertici coincidenti saldati, 6 triangoli degeneri e 39 duplicati rimossi, 126 componenti ridotte a 1, 1354 vertici orfani; **7 cicli chiusi** e **41 cammini di bordo aperti** prima della chiusura; dopo MeshFix superficie chiusa, 213 154 vertici e 426 600 triangoli |
| 7 qualità di superficie | chiusa, 0 spigoli di bordo, area 4,489 m²; rapporto d'aspetto dei triangoli: mediana 1,399, media 4,030, massimo 34 973 |
| 8 semplificazione | disabilitata: 426 600 triangoli in ingresso e in uscita |
| 9 tetraedrizzazione | **fallita**, `RefinementFailedError`: il raffinamento non converge |
| 10, 11 | non raggiunti |

L'intera corsa si ferma dopo **134 s**, cioè ben dentro il limite di venti minuti
per esecuzione che mi ero imposto: il limite qui non è il tempo né la memoria.

Errore geometrico fra superficie riparata e nuvola segmentata dello step 2,
riportato per intero perché il massimo e la media dicono cose diverse dall'RMS:

| direzione | campioni | media | RMS | massimo |
| --- | --- | --- | --- | --- |
| nuvola → mesh | 4 229 538 | 3,854 mm | 4,897 mm | 29,191 mm |
| mesh → nuvola | 213 154 | 1,955 mm | 3,898 mm | **77,361 mm** |

La distanza di Hausdorff, cioè il massimo dei due massimi, vale **77,36 mm**.
Rapportata alla diagonale dell'ingombro, circa 3006 mm, è il **2,6%**: un valore
molto più alto del 0,55% del muro sintetico. Che l'errore massimo cada dove la
chiusura di MeshFix ha inventato superficie sui bordi aperti del ritaglio — cioè
dove per costruzione non esistono punti di riferimento — è la spiegazione
plausibile e coerente con il caso del muro sintetico, ma non è stata verificata
localizzando i campioni peggiori: va presa come ipotesi. Riportare qui il solo
RMS di 3,90 mm, come faceva la versione precedente, nascondeva comunque un errore
massimo venti volte più grande.

### I fori: 7 cicli chiusi e 41 cammini aperti, non 48 fori

Una versione precedente di questa sezione riportava «48 fori chiusi». Il numero
veniva da `holes_before` prima della correzione di `repair.hole_loops`, quando la
funzione contava fra i fori anche i cammini di bordo che non si richiudono. La
distinzione, in una riga: **un ciclo chiuso è un foro** e ha un'area misurabile;
**un cammino aperto** finisce in un vicolo cieco o su una giunzione non manifold,
non delimita nulla, e qualunque area gli si attribuisca è calcolata su un
poligono che non si chiude.

Rimisurato con il codice corrente sulla stessa superficie dello step 5:

| grandezza | valore |
| --- | --- |
| cicli chiusi (`holes_before`) | **7**, di area 54,81 / 90,69 / 792,97 / 4407,65 / 31 012,34 / 34 670,18 / 279 816,08 mm² |
| cammini aperti (`open_boundary_paths`) | **41**, di cui **39 di lunghezza 2** e 2 di lunghezza 1620 |

I 48 «fori» del registro archiviato erano esattamente 7 + 41, e nel file
archiviato **39 delle 48 aree valevano esattamente zero**: sono i cammini di
lunghezza 2, due soli vertici, che non racchiudono alcuna superficie. Le due voci
da 256 320 mm² erano invece i due cammini lunghi, cioè le due grandi aperture del
bordo del ritaglio, la cui area è indicativa e non misurata. Il registro ora le
tiene separate, ed è per questo che quel registro è diventato onesto.

Quei due cammini sono anche il motivo per cui la guardia `repair.max_hole_area`
non poteva restare limitata ai cicli chiusi: le due aperture maggiori di questa
superficie sono cammini aperti, e una soglia che non le guardasse sarebbe cieca
proprio sul caso per cui esiste. Le metriche riportano ora anche
`open_paths_over_threshold`. Su questa corsa la soglia è nulla, quindi entrambe
le liste sono vuote.

### Lo step 9 non converge su questa superficie

TetGen si interrompe con il proprio errore interno (`split_subface`), tradotto
dalla pipeline in `RefinementFailedError`. Non è una questione di severità del
vincolo raggio-spigolo: il valore è stato fatto salire ben oltre il predefinito
di TetGen, che è 2,0, sulla superficie riparata `runs/lab_crop/06_repaired.ply`
e senza tetto ai punti di Steiner.

| `min_ratio` | esito |
| --- | --- |
| 1,8 (predefinito attuale) | errore interno dopo 36 s |
| 2,0 | errore interno dopo 36 s |
| 2,2 | errore interno dopo 38 s |
| 2,5 | errore interno dopo 35 s |
| 3,0 | errore interno dopo 30 s |
| 4,0 | errore interno dopo 25 s |

**Nessun valore provato porta a termine il lavoro.** Sul muro sintetico 1,8
bastava; qui non basta neanche 4,0, cioè un vincolo praticamente inerte. Il
problema non è quindi il parametro ma la superficie. L'indizio misurato è il
rapporto d'aspetto dei triangoli, che qui arriva a 34 973 contro i 3968 del muro
sintetico: la superficie porta schegge un ordine di grandezza peggiori. Che siano
proprio quelle la configurazione degenere su cui TetGen si arrende è l'ipotesi
naturale, non una verifica: il messaggio di TetGen non localizza il punto in cui
si interrompe. È comunque un esito legittimo e va scritto: **su questa scansione
la pipeline si ferma allo step 9**, e la prima via d'uscita da provare in Fase 2 è
il remeshing dello step 8, che è il passo che rimuove le schegge, non un'ulteriore
taratura di `min_ratio`.

### La corsa superata, e perché i suoi numeri non valevano

La versione precedente di questa sezione dichiarava che la pipeline arrivava in
fondo, con «313 154 nodi, 1 003 804 tetraedri in 10,4 s, nessun elemento
invertito» e un deck esportato. Quei numeri sono stati riprodotti esattamente,
sulla stessa superficie riparata, e la spiegazione è che erano il prodotto del
tetto ereditato di 100 000 punti di Steiner:

| configurazione | nodi | tetraedri | punti aggiunti | tempo |
| --- | --- | --- | --- | --- |
| `min_ratio` 1,1, tetto 100 000 (la corsa archiviata) | 313 154 | 1 003 804 | **100 000, esauriti** | 9,8 s |
| `min_ratio` 1,8, tetto 100 000 | 313 154 | 1 003 804 | **100 000, esauriti** | 9,9 s |
| `min_ratio` 1,8, nessun tetto (predefinito attuale) | — | — | — | errore interno |

313 154 nodi meno i 213 154 vertici della superficie fanno esattamente 100 000:
la firma dell'esaurimento del budget. Le due prime righe danno lo stesso identico
risultato proprio perché il tetto si esaurisce prima che `min_ratio` conti
qualcosa. Il tetto, cioè, fermava TetGen **prima** che arrivasse alla
configurazione degenere, e restituiva una mesh troncata con l'aria di un
successo: è lo stesso meccanismo documentato sul muro sintetico in
[`fase-1-esiti.md`](fase-1-esiti.md), con l'aggravante che qui nascondeva non un
degrado di qualità ma un fallimento completo. Il `metrics.json` archiviato di
quella corsa non aveva nemmeno le chiavi `max_steiner_points`, `steiner_points` e
`steiner_saturated`, perché la metrica che avrebbe segnalato la saturazione non
esisteva ancora.

Vanno considerati superati, insieme a quei numeri, anche il rapporto di forma
mediano 7,6 e l'angolo diedro minimo mediano 11,7° che la sezione riportava: sono
misure sulla mesh troncata, e non descrivono alcuna mesh che questa pipeline
produca oggi. La corsa superata era stata inoltre interrotta una prima volta dal
limite di venti minuti mentre era nello step 6, con l'altro processo Python della
macchina a 11 GB di RAM, e ripresa con `--from-step 6` a macchina più libera: la
lentezza di allora era contesa di memoria, non un blocco algoritmico, e infatti
la corsa nuova, a macchina libera, arriva allo step 9 in poco meno di cento
secondi e fallisce lì dopo altri trentasei.

### Che cosa resta valido per la Fase 2

Il `voxel_size: 10.0` esplicito è la scelta che rende praticabile lo step 4. Con
il valore derivato dai dati (`voxel_factor: 2.0`, cioè 2,4 mm) la riduzione lascia
milioni di punti, e `orient_normals_consistent_tangent_plane` costruisce un albero
di supporto minimo su tutti: è il punto in cui una precedente esecuzione sull'intera
nuvola era stata uccisa dal sistema per esaurimento della memoria, senza sollevare
alcuna eccezione — diagnosi confermata dall'assenza di `metrics.json`, che
`pipeline.run` scrive in un blocco `finally` anche quando uno step fallisce.

Lo spessore del modello ricostruito è **214,0 mm** contro i **176 mm** misurati
fra le due facce nella nuvola: la ricostruzione di Poisson ingrassa il muro di
circa 19 mm per faccia, e l'errore geometrico medio di 3,85 mm non lo rivela,
perché è una distanza punto-superficie e non una misura di spessore. Il valore è
l'ingombro orientato della superficie riparata (214,0 × 2468,8 × 1694,0 mm),
calcolato con `abaqus.align_to_axes` sui vertici di
`runs/lab_crop/06_repaired.ply`, e non viene da uno step 11 che questa corsa non
raggiunge.

## 6. Riproducibilità

Il criterio della Fase 1 è che due esecuzioni della stessa configurazione diano la
stessa segmentazione. RANSAC è randomizzato e `o3d.utility.random.seed` è la
difesa dichiarata, ma **da sola non basta**: `segment_plane` è parallelizzato con
OpenMP e con più thread l'ordine di scoperta del piano migliore dipende dallo
scheduling, non dal seme. Misurato: con il numero di thread lasciato libero, due
esecuzioni della stessa configurazione producevano un numero diverso di punti
residui.

Il rimedio è fissare il numero di thread di OpenMP a uno, e va fatto **prima che
Open3D avvii il proprio pool**, cioè prima che un qualunque modulo importi Open3D.
La riga vive quindi in `src/meshrec/__init__.py`, che Python esegue prima di ogni
sottomodulo del pacchetto:

```python
os.environ.setdefault("OMP_NUM_THREADS", "1")
```

`setdefault` e non assegnazione: chi preferisce la velocità alla riproducibilità
esporta la variabile dall'esterno e la riga si fa da parte.

Verifiche eseguite, tutte superate:

| verifica | esito |
| --- | --- |
| suite completa `pytest -v`, cioè nell'ordine in cui `test_pipeline.py` gira prima di `test_segment.py` e scalda il pool di thread | 111 test passati in 22 s, compreso `test_auto_mode_is_reproducible_across_runs` (erano 99 quando la verifica fu eseguita la prima volta) |
| due segmentazioni `auto` di seguito nello stesso processo, sulla scena sintetica, dopo una ricostruzione Poisson con `poisson_n_threads: -1` | `np.array_equal` vero, metriche identiche |
| due segmentazioni `auto` di seguito nello stesso processo, sulla nuvola reale `lab_frame.pcd` | `np.array_equal` vero, metriche identiche: 4 piani da 612 748 / 450 159 / 440 424 / 359 631 punti e cluster da 639 655 / 281 084 / 103 297 in entrambe le esecuzioni |
| `poisson_n_threads: -1` continua a usare più thread anche dopo una segmentazione automatica | 7,00 thread medi su processo fresco, 6,93 dopo la segmentazione; con `poisson_n_threads: 1` restano 1,02 |

L'ultima riga misura l'assenza di un effetto collaterale: il numero di thread è
fissato una volta sola tramite l'ambiente, quindi il parametro `poisson_n_threads`
resta libero di chiedere il parallelismo quando lo vuole. Il rapporto fra tempo di
CPU e tempo reale è la misura usata per contare i thread.

Vale la pena tenerlo scritto: **il parallelismo di queste librerie è la principale
minaccia alla riproducibilità di questa pipeline**, ed è la seconda volta che si
presenta dopo il caso di Poisson in Fase 0. Ogni nuovo passo che usi Open3D o una
libreria con OpenMP va verificato eseguendolo due volte, non dedotto dalla presenza
di una chiamata a `seed`.
