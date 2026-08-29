# «Segmentazione»: che cosa il termine significa in letteratura, e che cosa fa lo step 2

Data: 2026-08-28. Autore della raccolta: agente `researcher` (sola lettura).
Provenienza: cwd `/mnt/c/Users/mario/GitHub/Tesi`, branch `main`, HEAD `787fdeb`.
Scopo: stabilire, con fonti primarie, se le operazioni di `core/segment.py` si
chiamano «segmentazione» — la questione sollevata da un tutore.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte primaria (PDF scaricato o pagina
  ufficiale letta in questa sessione). La citazione riporta la sezione.
- **[V-loc]** = verificato leggendo un PDF della cartella `Articoli/`.
- **[CIT]** = visto solo citato altrove; estremi non verificati sull'originale.
- **[NON TROVATO]** = cercato e non trovato pubblicato in chiaro. Non inventato.

**Dove stanno i 17 articoli.** Non nel repository: `.gitignore` esclude
`Articoli/`, e `git log --all -- 'Articoli*'` è vuoto. Su questa macchina i 17
PDF stanno in
`/mnt/c/Users/mario/Università/OneDrive - Università degli Studi di Perugia/File di Pasquale Guarino - Mario Fiorenzoni/Articoli`.
Il testo è stato estratto con `pypdf` (nessun `pdftotext` disponibile in questo
ambiente). La numerazione `art. N` segue l'ordine alfabetico dei file ed è la
stessa di `ricerca-letteratura-scan-to-fem.md` §1.1 dove i due documenti
parlano dello stesso lavoro.

---

## 1. Che cosa fa davvero lo step 2

Letto in `core/segment.py`, per nome e non per riga.

`segment.segment_cloud` compone cinque operazioni in sequenza:

| # | operazione | simbolo | che cosa chiama |
|---|---|---|---|
| 1 | rimozione statistica degli outlier | `segment.remove_outliers` | `remove_statistical_outlier(nb_neighbors, std_ratio)` |
| 2 | ritaglio a box allineato agli assi | `segment.crop_box` | nessuna libreria: maschera booleana su `crop_min`/`crop_max` |
| 3 | estrazione iterativa di piani | `segment.extract_planes` | `segment_plane(distance_threshold, ransac_n=3, num_iterations=1000)`, in ciclo fino a `plane_max_count`, sul residuo |
| 4 | raggruppamento del residuo | `segment.cluster` | `cluster_dbscan(eps, min_points)`, gruppi ordinati per numerosità decrescente, etichetta `-1` scartata |
| 5 | scelta di un gruppo | `segment.segment_cloud` | `groups[cfg.cluster_index]` |

Le operazioni 3-5 girano solo con `method == "auto"`. Il modulo intitola
l'insieme «isolamento del muro dalla scena» nella propria docstring;
l'interfaccia lo intitola invece «Segmentazione» (`ETICHETTE` in `ui/app.js`).

**Nessuna delle cinque operazioni assegna un'etichetta a un punto.** Lo step non
produce classi: produce un sottoinsieme di punti e lo passa allo step 3.

## 2. Che cosa dice Open3D delle tre funzioni chiamate

Versione risolta nel lock del progetto: `open3d` **0.19.0**
(`meshrec/uv.lock`; `pyproject.toml` vincola `>=0.19`). La documentazione
consultata è quella della 0.19.0, quindi la versione corrisponde. [V]

- `remove_statistical_outlier(nb_neighbors, std_ratio, print_progress=False)` —
  «Removes points that are further away from their neighbors in average.»
  Nella documentazione a tutorial sta su una **pagina propria**, *Point cloud
  outlier removal*, non nella pagina *Point cloud* dove stanno le altre due. [V]
  <https://www.open3d.org/docs/release/python_api/open3d.geometry.PointCloud.html>
- `segment_plane(distance_threshold, ransac_n, num_iterations, probability=0.99999999)` —
  «Segments a plane in the point cloud using the RANSAC algorithm.» Nel tutorial
  la sezione si chiama **Plane segmentation**: «Open3D also supports
  segmententation of geometric primitives from point clouds using RANSAC.» [V]
- `cluster_dbscan(eps, min_points, print_progress=False)` — «Cluster PointCloud
  using the DBSCAN algorithm. Ester et al., "A Density-Based Algorithm for
  Discovering Clusters in Large Spatial Databases with Noise", 1996.» Rende
  un'etichetta per punto, dove **`-1` indica rumore**. Nel tutorial la sezione si
  chiama **DBSCAN clustering**, non «segmentation». [V]
  <https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html>

Nota di lettura: `segment.cluster` scarta le etichette `< 0`, cioè scarta
esattamente il rumore che DBSCAN dichiara tale. Coerente con la documentazione.

Nella pagina *Point cloud* di Open3D esiste anche una sezione **Crop point
cloud**, separata sia da *Plane segmentation* sia da *DBSCAN clustering*. La
libreria, quindi, tratta ritaglio, rimozione outlier e segmentazione come tre
cose distinte già a livello di indice della propria documentazione. [V]

## 3. (a) La definizione standard di «point cloud segmentation»

### 3.1 La definizione classica

Nguyen, A. e Le, B. (2013), *3D Point Cloud Segmentation: A survey*, in
**2013 6th IEEE Conference on Robotics, Automation and Mechatronics (RAM)**,
Manila, pp. 225–230. Il lavoro esiste e l'ho letto per intero: la copia
dell'autore è su <https://www.csc.liv.ac.uk/~anguyen/assets/pdfs/2013_PointCloudSeg_Survey.pdf>,
e il piè di pagina stampa «2013 6th IEEE Conference on Robotics, Automation and
Mechatronics (RAM) 227» e il codice ISBN «978-1-4799-1201-8/13». [V]
DOI 10.1109/RAM.2013.6758588 [CIT] — non stampato nella copia letta.

Abstract, prima frase:

> «3D point cloud segmentation is the process of classifying point clouds into
> multiple homogeneous regions, the points in the same region will have the same
> properties.»

Introduzione:

> «Given the set of point clouds, the objective of the segmentation process is to
> cluster points with similar characteristics into homogeneous regions. These
> isolated regions should be meaningful.»

Due requisiti, quindi, e sono i due che qualificano un'operazione come
segmentazione: **partizionare** l'insieme dei punti in regioni, e che le regioni
siano **omogenee rispetto a una proprietà** e significative. Non è richiesta
nessuna etichetta semantica.

### 3.2 Segmentazione contro classificazione

Grilli, E., Menna, F., Remondino, F. (2017), *A review of point clouds
segmentation and classification algorithms*, **The International Archives of the
Photogrammetry, Remote Sensing and Spatial Information Sciences**, Volume
XLII-2/W3, pp. 339–344, 3D-ARCH 2017, Nafplio, doi:10.5194/isprs-archives-XLII-2-W3-339-2017.
Esiste, l'ho letto per intero. [V]

Abstract:

> «Segmentation is the process of grouping point clouds into multiple homogeneous
> regions with similar properties whereas classification is the step that labels
> these regions.»

§3, prima frase:

> «Once a point cloud has been segmented, each segment (group) of points can be
> labelled with a class thus to give some semantic to the segment (hence point
> cloud classification is often called semantic segmentation or point labelling).»

**La separazione è netta e va tenuta**: raggruppare è segmentazione, etichettare
è classificazione. La seconda presuppone la prima; la prima non richiede la
seconda.

### 3.3 Segmentation, semantic, instance, panoptic

- **Segmentation (PCS)** — Xie, Y., Tian, J., Zhu, X. X. (2020), *Linking Points
  With Labels in 3D: A Review of Point Cloud Semantic Segmentation*, **IEEE
  Geoscience and Remote Sensing Magazine**, DOI 10.1109/MGRS.2019.2937630 (il
  DOI è stampato nella copia letta). Sezione «SEGMENTATION, CLASSIFICATION, AND
  SEMANTIC SEGMENTATION»: [V]

  > «PCS aims at grouping points with similar geometric/spectral characteristics
  > without considering semantic information.»

  e, sulla relazione fra le due:

  > «In the PCSS workflow, PCS (sometimes used as a presegmentation step) can
  > influence the final results.»

  Caveat: la copia letta è quella dell'autore depositata in elib.dlr.de, marcata
  «accepted for inclusion in a future issue», quindi **volume, numero e
  pagine non sono verificati sull'originale**. Gli estremi correnti sono vol. 8,
  n. 4, pp. 38–59, dicembre 2020 [CIT].

- **Semantic segmentation (PCSS)** — stesso lavoro, stessa sezione:

  > «we refer to the task of associating each point of a point cloud with a
  > semantic label as PCSS.»

  Con l'avvertenza terminologica utile a una tesi italiana di ingegneria:

  > «in photogrammetry and remote sensing, PCSS is usually called point cloud
  > classification [...] In some cases, this task is also called point labeling.»

- **Instance e part segmentation** — Guo, Y., Wang, H., Hu, Q., Liu, H., Liu, L.,
  Bennamoun, *Deep Learning for 3D Point Clouds: A Survey*, **IEEE Transactions
  on Pattern Analysis and Machine Intelligence**. §5: [V]

  > «According to the segmentation granularity, 3D point cloud segmentation
  > methods can be classified into three categories: semantic segmentation (scene
  > level), instance segmentation (object level) and part segmentation (part level).»

  §5.1: «the goal of semantic segmentation is to separate it into several subsets
  according to the semantic meanings of points». §5.2: la instance segmentation
  «not only needs to distinguish the points with different semantic meanings, but
  also separate instances with the same semantic meaning».

  Caveat: ho letto il **preprint arXiv 1912.12033**, non la versione di rivista.
  Gli estremi pubblicati sono vol. 43, n. 12, pp. 4338–4364, dicembre 2021,
  DOI 10.1109/TPAMI.2020.3005434 [CIT].

- **Panoptic segmentation** — Kirillov, A., He, K., Girshick, R., Rother, C.,
  Dollár, P., *Panoptic Segmentation*, **CVPR 2019**, arXiv:1801.00868: [V, dal
  solo abstract]

  > «panoptic segmentation unifies the typically distinct tasks of semantic
  > segmentation (assign a class label to each pixel) and instance segmentation
  > (detect and segment each object instance)»

  La definizione nasce in 2D. Il trasferimento a nuvole di punti esiste — Behley,
  Milioto, Stachniss (2021), *A Benchmark for LiDAR-based Panoptic Segmentation
  based on KITTI*, ICRA 2021 [CIT: non letto].

### 3.4 Che cosa qualifica un'operazione come segmentazione

Dalle definizioni sopra, tre condizioni cumulative:

1. l'ingresso è **partizionato**: ogni punto finisce in un segmento (o
   dichiaratamente in nessuno, come il rumore di DBSCAN);
2. il criterio di partizione è una **proprietà omogenea** — geometrica,
   radiometrica, di densità — e non una posizione arbitraria imposta
   dall'operatore;
3. i segmenti sono **significativi** rispetto alla scena.

L'etichetta semantica non è condizione: è ciò che aggiunge la classificazione, o
la semantic segmentation.

## 4. (b) Filtering, outlier removal, cropping: pre-processing, non segmentazione

**Nessuna delle tassonomie lette contiene «filtering», «denoising», «outlier
removal» o «cropping» fra le famiglie di segmentazione.** Le cinque famiglie di
Nguyen & Le sono edge based, region based, attributes based, model based, graph
based; quelle di Xie et al. sono EDGE BASED, REGION GROWING, MODEL FITTING,
UNSUPERVISED CLUSTERING BASED, GRAPH BASED; quelle di Grilli et al. sono
edge-based, region growing, model fitting, hybrid, machine learning. Il filtro
non compare in nessuna delle tre. [V]

Formulazioni esplicite trovate:

- Nguyen & Le, §II.B, sui dataset pubblici: [V]

  > «they also may need a preprocessing step before using them as input for
  > segmenting algorithms.»

  Il pre-processing è ciò che si fa **prima** di dare in pasto i dati agli
  algoritmi di segmentazione. È la formulazione più diretta, benché breve.

- Xie et al. usano «preprocessing» per la voxelizzazione a monte delle reti e
  hanno una sezione finale «NOISE AND OUTLIERS» fra i **problemi aperti**, non
  fra i metodi di segmentazione. [V]

- Tang, P., Huber, D., Akinci, B., Lipman, R., Lytle, A. (2010), *Automatic
  reconstruction of as-built building information models from laser-scanned
  point clouds: A review of related techniques*, **Automation in Construction**
  19(7):829–843, DOI 10.1016/j.autcon.2010.06.007. §1.1, letto sulla copia
  aperta del NIST: [V]

  > «The process of creating an as-built BIM using laser scanners can be divided
  > into three main steps: 1) data collection [...]; 2) data preprocessing, in
  > which the sets of point measurements (known as point clouds) from the
  > collected scans are filtered to remove artifacts and combined into a single
  > point cloud or surface representation in a common coordinate system; and 3)
  > modeling the BIM [...]»

  §1.1.2, ancora più esplicito:

  > «Data preprocessing may also include manual or automated filtering to remove
  > unwanted data, such as points from moving objects, reflections, or sensor
  > artifacts.»

  E, altrove nello stesso lavoro, la segmentazione compare come cosa diversa e
  successiva: i metodi di riconoscimento di componenti BIM «typically perform an
  initial shape-based segmentation of the scene, into planar regions».

- Han, X.-F., Jin, J. S., Wang, M.-J., Jiang, W., Gao, L., Xiao, L. (2017),
  *A review of algorithms for filtering the 3D point cloud*, **Signal Processing:
  Image Communication** 57:103–112. [CIT: esistenza e estremi confermati in
  ricerca, testo integrale non letto — dietro paywall]. Il fatto rilevante è già
  nel titolo: il filtraggio ha una **letteratura di rassegna propria**, distinta
  da quella della segmentazione.

**Sul cropping non ho trovato nessuna formulazione esplicita in una survey.**
Il termine non compare nelle tassonomie lette. Compare invece nella letteratura
applicata, e sempre come passo manuale di preparazione: art. 12 (Zhang, Xia,
Taylor, *Comput.-Aided Civ. Infrastruct. Eng.*) scrive «cropping the background
is needed», «after cropping the unnecessary part», e nelle limitazioni elenca
«several manual steps, such as cropping the background, scaling the point cloud,
determining of point cloud simplification strength». [V-loc] Nessuno lo chiama
segmentazione. Il nome corretto nel vocabolario del dominio è **ROI extraction**
o **clipping**, ed è pre-processing.

### 4.1 Un caveat onesto: «filtering» in fotogrammetria non è sempre pre-processing

In fotogrammetria da laser scanning aereo, «filtering» ha un secondo significato,
tecnico e più antico: la separazione fra punti a terra e punti non a terra. Il
benchmark ISPRS WG III/3 citato da Grilli et al. §1 nasce «to compare the
performance of various automatic filters» e mira a «segment and classify points
in bare earth and object classes» — cioè il *filtro* fa il lavoro di una
*segmentazione* binaria. [V]

La conseguenza per la tesi: «filtro» da solo è ambiguo in questo campo, e va
qualificato. `remove_statistical_outlier` non è un filtro di quel tipo — non
separa due classi, elimina punti anomali rispetto al vicinato — ma la parola
nuda può far pensare all'altro.

## 5. (c) RANSAC e DBSCAN: sono segmentazione, e con quale qualificatore

### 5.1 RANSAC — model fitting / model based

Le tre tassonomie concordano, e usano lo stesso nome di famiglia.

- Nguyen & Le, §III.D «Model based methods»: [V]

  > «Model based methods use geometric primitive shapes (e.g. sphere, cone,
  > plane, and cylinder) for grouping points. The points which have the same
  > mathematical representation are grouped as one segment.»

  e su RANSAC: «Fischer [5] introduced a well known algorithm called RANSAC
  (RANdom SAmple Consensus). [...] This method is now the state of the art for
  model fitting. In 3D point cloud segmentation, many subsequent works have
  inherited this initial algorithm.»

- Grilli et al., §2.3 «Segmentation by model fitting»: [V]

  > «primitive shapes are fitted onto point cloud data and the points that
  > conform to the mathematical representation of the primitive shape are
  > labelled as one segment. As part of the model fitting-based category, two
  > widely employed algorithms are the Hough Transform (HT) [...] and the Random
  > Sample Consensus (RANSAC) approach (Fischer and Bolles, 1981).»

  Con l'osservazione che pesa sul nostro caso: «In case the primitives have some
  semantic meaning, then such approach is also performing a classification.»

- Xie et al., sezione «MODEL FITTING»: [V]

  > «For PCS, as with HT and region growing, the RANSAC method is widely used in
  > plane segmentation, such as building façades, building roofs, and indoor
  > scenes.»

  Con il limite che il nostro `segment.extract_planes` deve conoscere: «RANSAC is
  a nondeterministic algorithm, and thus its main shortcoming is its spurious
  surface: models detected by the RANSAC-based algorithm may not exist.»
  (Il seme fisso di `extract_planes` rende l'esito riproducibile; non lo rende
  esente da piani spuri.)

Fonte contemporanea che usa il termine senza esitazione, in sede ISPRS: Ling, Y.,
Wang, Y., Chan, T. O. (2024), *RANSAC-Based Planar Point Cloud Segmentation
Enhanced by Normal Vector and Maximum Principal Curvature Clustering*, **ISPRS
Annals of the Photogrammetry, Remote Sensing and Spatial Information Sciences**,
Vol. X-1/2024, pp. 145 ss., CC BY 4.0. Abstract: «Planar feature segmentation is
an essential task for 3D point cloud processing [...] The Random Sample Consensus
(RANSAC) is one of the most common algorithms for the segmentation». [V]
<https://isprs-annals.copernicus.org/articles/X-1-2024/145/2024/isprs-annals-X-1-2024-145-2024.pdf>

**Qualificatore corretto per `segment.extract_planes`**: segmentazione **per
adattamento di modello** (*model fitting*, *model based*), non supervisionata,
con estrazione iterativa di primitive planari.

### 5.2 DBSCAN — clustering non supervisionato

- Xie et al., sezione «UNSUPERVISED CLUSTERING BASED»: [V]

  > «Clustering-based methods are widely used for unsupervised PCS tasks.
  > Strictly speaking, clustering-based methods are not grounded in a specific
  > mathematical theory. This methodology family is made up of a mixture of
  > different methods that share a similar aim: grouping points with similar
  > geometric features, spectral features, or spatial distribution into the same
  > homogeneous pattern. Unlike region growing and model fitting, these patterns
  > usually are not defined in advance [...] and thus clustering-based algorithms
  > can be employed for irregular object segmentation [...] in contrast to
  > region-growing methods, seed points are not required by clustering-based
  > approaches.»

  **Onestà sulla fonte**: gli algoritmi che Xie et al. nominano dentro questa
  famiglia sono K-means, mean shift e fuzzy clustering. **DBSCAN non è nominato**
  in quel lavoro (verificato per grep sul testo estratto). La famiglia è quella
  giusta, ma la citazione non copre l'algoritmo specifico.

- Grilli et al. mettono K-means, hierarchical clustering e mean shift sotto
  «2.5 Machine learning segmentation», e non nominano DBSCAN. [V]

- L'algoritmo in sé: Ester, M., Kriegel, H.-P., Sander, J., Xu, X. (1996),
  *A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases
  with Noise*, KDD-96. È la citazione che Open3D stampa nella docstring di
  `cluster_dbscan`. [V, sulla docstring; il paper originale non è stato letto]

- Per DBSCAN nominato come segmentazione di nuvole va citata la letteratura
  applicata, dove abbonda. Nei 17: art. 3 (Zhang, Shu, Shao, Zhao, *J. Civ.
  Struct. Health Monit.*) intitola una figura «Two-step clustering algorithm for
  **segmentation** of point clouds» e la implementa con DBSCAN. [V-loc]

**Qualificatore corretto per `segment.cluster`**: segmentazione **per clustering
non supervisionato**, di tipo **density-based**, senza punti seme.

## 6. (e) Come si chiama questo passaggio nel dominio scan-to-BIM / scan-to-FEM

Le due fonti più pertinenti sono entrambe nella cartella `Articoli/`, e sono
entrambe lavori che fanno **esattamente le operazioni del nostro step 2**.

**Art. 7 — Yang, T., Zou, Y., Yang, X., del Rey Castillo, E. (2024), *Domain
knowledge-enhanced region growing framework for semantic segmentation of bridge
point clouds*, Automation in Construction 165:105572, open access CC BY.** [V-loc]

Struttura dichiarata in §4:

> «It consists of four phases: (1) data pre-processing, (2) substructure
> segmentation, (3) superstructure segmentation, and (4) original point cloud
> segmentation.»

Che cosa sta in Phase 1 (§4.1.1): down-sampling con Voxel Grid Filter e
allineamento con PCA. «Down-sampling is a crucial pre-processing step in point
cloud segmentation, providing benefits such as computational efficiency, noise
reduction, and simplification of complex scenes.»

Che cosa sta invece **dentro** le fasi di segmentazione: DBSCAN, per raggruppare
i pilastri — «Density-Based Spatial Clustering of Applications with Noise
(DBSCAN) is adopted to group the bridge piers [...] DBSCAN is primarily adopted
here for distance-based clustering» — e RANSAC, per adattare i piani di taglio —
«the Random Sample Consensus (RANSAC) algorithm is adopted for plane fitting due
to its better robustness for noise points».

**È la conferma diretta e nel nostro dominio**: preparazione da una parte,
RANSAC e DBSCAN dall'altra, e la seconda parte si chiama segmentazione.

**Art. 2 — Chen, Y., Gao, C., Chen, Q., Zhang, J., *Automated finite element
modeling method for steel bridges integrating 3D point clouds and intelligent
drawing recognition technology*, Automation in Construction.** [V-loc] §3.1 si
intitola «Point cloud data acquisition and pre-processing»:

> «The preprocessing steps include the registration of multi-station point cloud
> data, the manual removal of various environmental interferences (such as trees,
> pedestrians, vehicles, etc.), point cloud downsampling, point cloud denoising,
> and coordinate transformation.»

e, sulla rimozione degli outlier — che è **la stessa operazione** di
`segment.remove_outliers`, descritta con la stessa formula:

> «Point cloud denoising is conducted using a statistical filtering algorithm
> that calculates the distances from each point to its neighboring points within
> the point cloud model. Points with distances that exceed a specified threshold
> (typically defined as the mean distance plus three times the standard
> deviation) are identified as outliers.»

Il resto del lavoro chiama «segmentation» l'estrazione dei componenti (e
«secondary segmentation» il raffinamento successivo).

**Nel ramo HBIM su patrimonio il vocabolario è più lasco.** Art. 11 (Abbate,
Invernizzi, Spanò, *Applied Geomatics*) usa «Cloud segmentation and structural
elements recognition» come titolo di sezione, e altrove «Point cloud
segmentation accordingly to the hierarchic structural elements recognition»
[V-loc]: segmentazione **e** riconoscimento, nominati assieme, per un'operazione
per lo più manuale in software commerciale. Art. 13 (Pirchio et al., *Eng.
Struct.*, chiese medievali in muratura) **non usa mai la parola
«segmentation»**: zero occorrenze nel PDF. [V-loc] Il termine, in quella
sotto-letteratura, non è ancora obbligatorio.

## 7. (d) Come andrebbero nominate le operazioni dello step 2

Sintesi di quanto sopra, applicata al nostro codice.

| operazione | è segmentazione? | nome che un revisore accetta |
|---|---|---|
| `segment.remove_outliers` | **no** | filtraggio statistico degli outlier — *statistical outlier removal*; è **pre-processing** / *denoising* |
| `segment.crop_box` | **no** | ritaglio della regione d'interesse — *ROI extraction*, *clipping*; è **pre-processing** |
| `segment.extract_planes` | **sì** | segmentazione per adattamento di modello (RANSAC) — *model fitting based segmentation*, estrazione iterativa di primitive planari |
| `segment.cluster` | **sì** | segmentazione per clustering non supervisionato basato su densità (DBSCAN) — *unsupervised density-based clustering segmentation* |
| scelta di `groups[cluster_index]` | **no** | selezione del componente d'interesse — *object extraction*, *component selection* |

**Nome dell'insieme.** Lo step non è «segmentazione» e non è nemmeno solo
pre-processing: è una catena mista che finisce con una selezione. Due formule
difendibili:

- **«Isolamento del muro»** — è già il nome che la docstring di `core/segment.py`
  usa, ed è il più onesto: dice il risultato, non il metodo, e quindi non promette
  nulla di sbagliato. Il calco inglese nel dominio è *target component
  extraction*.
- **«Pre-processing e segmentazione geometrica non supervisionata»** — se si
  vuole nominare il metodo. Più lungo, ma è la formula che il revisore riconosce
  parola per parola dalle survey.

Ciò che **non** va scritto in tesi: «segmentazione semantica». Lo step non
assegna classi. E non va scritto «classificazione»: non etichetta nulla.

## 8. Verdetto

**Il tutore ha ragione in parte, e la parte in cui ha ragione è più importante di
quella in cui ha torto.**

1. **Ha ragione sul nome dello step.** Chiamare «Segmentazione» un blocco che
   inizia con un filtro statistico e un ritaglio a box è impreciso: nessuna
   tassonomia della letteratura contiene quelle due operazioni, e la letteratura
   del nostro dominio — Tang et al. 2010, art. 2, art. 7 — le mette
   esplicitamente sotto «data pre-processing».

2. **Ha ragione, se intendeva la segmentazione in senso moderno.** Nel senso oggi
   dominante — *semantic segmentation*, ogni punto una classe — lo step 2 non
   segmenta affatto: non produce etichette, produce un sottoinsieme.

3. **Ha torto se intendeva che nulla nello step è segmentazione.**
   `segment.extract_planes` e `segment.cluster` sono segmentazione senza
   ambiguità, e appartengono a due delle cinque famiglie canoniche: *model
   fitting* e *unsupervised clustering*. Lo dicono con lo stesso nome Nguyen &
   Le 2013, Grilli et al. 2017 e Xie et al. 2020, e lo fa con gli stessi due
   algoritmi un lavoro scan-to-FEM del 2024 che intitola sé stesso «semantic
   segmentation».

4. **Il difetto vero non sta nel codice, sta nella riga di interfaccia.**
   `PROPOSITI` in `ui/app.js` descrive `02_segment` così: «Tiene i soli punti
   dell'oggetto: toglie il rumore e ritaglia via il resto della stanza».
   Quella frase descrive **solo** `remove_outliers` e `crop_box`, e tace
   completamente RANSAC e DBSCAN, cioè le due sole operazioni dello step che sono
   segmentazione. Chi legge quella riga e legge l'etichetta «Segmentazione» vede
   una contraddizione, e ha ragione a segnalarla. Il codice fa più di quanto la
   sua descrizione ammetta.

### Che cosa andrebbe rinominato

Raccomandazioni, non decisioni prese.

1. **`PROPOSITI["02_segment"]`** — è la correzione che chiude la contestazione, e
   la più economica. La frase deve nominare tutte e tre le cose che lo step fa:
   toglie rumore e ritaglia, **poi stacca i piani con RANSAC e raggruppa il
   residuo**, poi tiene il gruppo scelto.
2. **`ETICHETTE["02_segment"]`** — se si vuole l'etichetta esatta, «Isolamento»
   è più difendibile di «Segmentazione», e coincide con la docstring che il
   modulo già porta. Se si preferisce non toccarla, «Segmentazione» resta
   sostenibile **a patto che** la riga di `PROPOSITI` dica quale segmentazione.
3. **Il testo di tesi** — non chiamare lo step «segmentazione» senza
   qualificatore. La forma sicura: «pre-processing (rimozione statistica degli
   outlier, ritaglio della regione d'interesse) seguito da segmentazione
   geometrica non supervisionata — adattamento di modello con RANSAC ed
   estrazione dei gruppi con DBSCAN — e selezione del componente».
4. **I nomi dei simboli in `core/segment.py`** — `segment_cloud` è il nome più
   discutibile del modulo, perché promette segmentazione e fa una catena mista.
   `remove_outliers`, `crop_box`, `extract_planes` e `cluster` sono invece già
   nominati esattamente come la letteratura li nomina, e non vanno toccati.
   Rinominare `segment_cloud` è una decisione da pesare contro il costo di
   toccare le chiamate: è un'imprecisione di nome, non un difetto di
   comportamento.

## 9. Che cosa questa ricerca non stabilisce

- **Nessuna norma definisce «segmentazione».** Ho cercato una definizione
  normativa (ISO, ASTM) e non l'ho trovata: la terminologia in questo campo è
  fissata dalle survey, non da uno standard. [NON TROVATO]
- **Nessuna survey letta parla di «cropping».** L'assenza dalle tassonomie è
  un'assenza, non una negazione esplicita; l'unica evidenza positiva che sia
  pre-processing viene dalla letteratura applicata (art. 12) e da come Open3D
  organizza la propria documentazione.
- **Nessuna fonte primaria letta nomina DBSCAN dentro una tassonomia di
  segmentazione.** La famiglia («unsupervised clustering based») è certa;
  l'algoritmo specifico è coperto solo da letteratura applicata.
- **Guo et al. e Kirillov et al. non sono stati letti nella versione di rivista**:
  il primo in preprint arXiv, il secondo nel solo abstract. Le pagine e i volumi
  riportati per questi due sono [CIT].
