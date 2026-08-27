# Come la letteratura scan-to-FEM valida il proprio lavoro

Ricerca su 17 PDF in `/Users/mario/GitHub/Tesi/Articoli/` + fonti esterne primarie.

**Provenienza.** cwd `/Users/mario/GitHub/Tesi`, repo `/Users/mario/GitHub/Tesi`, branch `main`, HEAD `a07071a`, data 2026-08-26.
Testo estratto con `pdftotext -layout` (poppler, `/opt/homebrew/bin/pdftotext`) da tutti i 17 PDF in `/tmp/artxt/`.
Ogni numero qui sotto è **letto** nel PDF, non ricordato. Dove il PDF non dichiara qualcosa, è scritto esplicitamente.
DOI: riportati solo se **stampati** nel PDF (verificati con grep). Nessun DOI inventato.

---

## 1. I 17 articoli — scheda sintetica

Legenda colonne: **Rif.** | **Cosa ricostruiscono** | **Come validano** | **Elemento finito** | **Limite dichiarato**

### 1.1 Tabella compatta

| # | Riferimento | Oggetto / rilievo | Contro cosa confronta | Elemento finito | Limite dichiarato |
|---|---|---|---|---|---|
| 1 | Yu, Zhang, Shooshtarian, Zhao, Shu (2021), *Structural Concrete* 22:3213–3227, DOI 10.1002/suco.202100194 | 2 travi RC 600×150×100 mm fessurate; scanner palmare DotProduct DPI-8S | **Prova sperimentale**: flessione 3 punti (UC Berkeley) — curve carico/freccia FE vs 2 curve sperimentali; pattern di fessura FE vs fessura estratta dalla nuvola | C3D8R (esaedro 8 nodi, integr. ridotta) + T3D2 (truss) per le barre | Fessura troppo piccola per misurarne l'ampiezza dalla nuvola: usata solo la **posizione**; errori relativi maggiori su oggetti piccoli — "metodo più adatto a oggetti grandi" |
| 2 | Zhang, Shu, Shao, Zhao (2022), *J. Civ. Struct. Health Monit.* 12:29–46, DOI 10.1007/s13349-021-00525-5 | 2 travi RC fessurate; nuvola + immagini, registrazione ICP-based DLT | **Riferimento interno alla nuvola**: posizione fessura back-proiettata vs fessura estratta dalla nuvola (err. max 3,271 mm, medio 2,351 mm); ampiezza fessura err. medio relativo 9,97 %, max 0,844 mm; larghezza trave 101,6 mm reale vs 102,1 mm da nuvola. FE: **solo dimostrazione di fattibilità** (curva carico/spostamento, snervamento a 15,0 kN, rottura 17,5 kN) — nessun confronto con la prova | Elementi continuum 3D in DIANA, total strain **rotating crack** | Posizione delle armature **predeterminata**, non ricavata dalla nuvola; distorsione dell'immagine trascurata |
| 3 | Zhang, Shu, Zhang, Ning, Yu (2024), *Eng. Struct.* 310:118126, DOI 10.1016/j.engstruct.2024.118126 | 4 travi RC 2,4 m (1 riferimento + 3 pre-fessurate); scanner KSCAN-Magic + DIC | **Doppio livello**: (a) geometria — distanza **cloud-to-cloud (C2C)** fra gDT ricampionato e nuvola originale, Hausdorff definito formalmente (eq. 1–3); errore < 3 mm su > 95 % della regione (§4.1); errore 3–4 mm in lunghezza, 1 mm in altezza/larghezza vs misure manuali. (b) meccanica — **prova di flessione**: carico ultimo sperimentale RB0 111 kN, PB1–PB3 106–108 kN (PB3 118 kN) vs FE; confronto anche con analisi "phased" | Brick 3D solidi, dim. media 15 mm; total strain **fixed crack**; crack bandwidth Govindjee, valore utente 21,2 mm (=√2·15) per elementi danneggiati | Gli spigoli governano l'accuratezza e sono mal definiti nel CA; **profondità della fessura non ottenibile** dalla visione (per ponti reali servirebbe GPR); UAV rileva fessure ≥0,2 mm, DIC 0,02 mm |
| 4 | Chen, Gao, Chen, Zhang (2025), *Autom. Constr.* 179:106466, DOI 10.1016/j.autcon.2025.106466 | Ponte ad arco in acciaio in scala (5,2 m) + passerella strallata reale 37,6 m; TLS RIEGL VZ-400i (spaziatura ~3 mm) + lettura automatica dei disegni (YOLOv5 + OCR + LLM GLM4) | **Il più completo dei 17**: (a) dimensioni calcolate vs misurate (dev. di forma ≤ ±3,05 mm, err. lunghezza ≤ 9,2 mm sul modello; ±20 mm posizione trave, ±7 mm altezza torre, ±2 mm raggio stralli sul ponte reale); (b) precisione di segmentazione vs 2 algoritmi noti (media 0,984 vs 0,946 e 0,978); (c) **prova di carico statico** 20/63 kN e 700/1200 N — spostamenti FE vs misurati; (d) **analisi modale sperimentale** (eccitazione a martello): f misurate 2,68 / 6,39 / 9,72 Hz vs FE 2,52 / 5,86 / 9,67 Hz | BEAM188 per tutto tranne i cavi; LINK180 per i cavi; SOLID per l'impalcato | Rimozione manuale delle interferenze ambientali dalla nuvola; workflow 2–3 h; benchmarking sistematico rimandato al lavoro futuro |
| 5 | Abbate, Invernizzi, Spano (2022), *Applied Geomatics* 14(Suppl 1):S79–S96, DOI 10.1007/s12518-020-00341-4 | "Paraboloide" di Casale, volta sottile in CA (spessore 8 cm, 23×53 m); TLS Faro Focus3D S120 + UAV + MMS Zeb Revo | **Nessuna prova sperimentale**. Validazione tutta **geometrica e interna**: RMS registrazione scansioni < 1 cm (83 % punti < 4 mm); RMSE medio blocco fotogrammetrico 0,0090 m; drift MMS 2 cm; *deviation analysis* NURBS vs mesh, deviazione max **0,5 mm** (pilastro) e **1 mm** (arco). Poi confronto **fra tre modelli propri** (3D brick / 2D shell / 1D beam): von Mises, spostamenti, prima forma modale | Brick 3D, shell 2D, beam 1D a sezione variabile (Autodesk Simulation Mechanical) | Il modello 1D non coglie le concentrazioni di tensione; per la dinamica servono diagonali equivalenti alla Hrennikoff (1949); problemi di interoperabilità BIM→FEM |
| 6 | Pirchio, Walsh, Kerr, Giongo, Giaretton, Weldon, Ciocci, Sorrentino (2021), *Eng. Struct.* 241:112439, DOI 10.1016/j.engstruct.2021.112439 | Chiesa in muratura non armata S. Maria Maggiore, Alatri; SfM da UAS + camere fisse | **Nessuna prova sperimentale, nessuna identificazione dinamica**. (a) geometria: alcune misure manuali confermano la scala automatica della nuvola con **errore ~1 %**; (b) meccanica: **auto-validazione interna** — l'analisi con spettro di risposta modale è "validata" da un pushover non-lineare *stiffness adaptation analysis* (SAA) proprio, e i risultati coincidono | **Shell** in CSi SAP2000 — scelti *perché solo gli shell erano esportabili* dall'HBIM (vincolo di interoperabilità, non meccanico); colonne come frame | Elencano 5 limiti della SAA: comportamento fuori piano ignorato, costo computazionale, sensibilità al passo Δ, rimozione manuale degli elementi, non adatta a cicli. Ammettono che FDEM/DEM sono più accurati per la muratura |
| 7 | Casimiro-Bernardez, Martinez-Carricondo, Aguera-Vega, Carvajal-Ramirez, *Conservation Science in Cultural Heritage*, pp. 111–139 (**annata e DOI non stampati nella copia**) | Acquedotto dei Venti Occhi, Carcauz (Almeria), 42 m; fotogrammetria UAV DJI Phantom 4 RTK, 315 foto, GSD 1,22 cm, 11,78 M punti | **Nessuna prova sperimentale**. Validazione geometrica esplicita e con **criterio di accettazione dichiarato a priori**: rilievo GNSS RTK, 7 GCP + 7 check point, errore totale sui CP **3,53 cm**; poi **Cloud-to-Mesh Distance in CloudCompare** fra nuvola e mesh HBIM: media **0,022 m**, dev. std **0,08 m**; criterio (da Martinez-Carricondo et al., rif. [48]): media ∈ [−0,10; +0,10] m e σ < 0,10 m. Verifica strutturale contro **norma** (CTE): CSV vento 2,41 (>2 OK), CSV sisma **0,88 (< 2, non verificato)** | **Shell 2D** in SAP2000, 4170 elementi, dim. media < 0,50 m | Nessuna caratterizzazione distruttiva dei materiali: proprietà **stimate** da letteratura e geologia; spessore muro assunto costante 0,90 m; analisi solo elastica lineare; passaggio Revit→SAP2000 forzato via AutoCAD 3D per problemi di interoperabilità |
| 8 | Shetty, Banerjee, Tallur, Desai (2022), *J. Nondestruct. Eval.* 41:67, DOI 10.1007/s10921-022-00897-8 | Interfaccia acciaio–calcestruzzo corrosa; **nuvola simulata**, non rilevata | **Prova sperimentale** su corrosione accelerata 12 giorni: (a) perdita di massa cumulata da modello vs legge di Faraday su corrente impressa misurata; (b) segnale guided wave di baseline FE vs sperimentale; (c) inviluppi di energia delle onde nelle 3 fasi di corrosione | Tetraedri liberi (COMSOL), min 3 mm / max 8 mm, growth rate 1,3; convergenza di mesh verificata | La nuvola è **generata dal modello multi-fisico**, non scansionata: scansionare l'armatura annegata è impossibile senza rompere il calcestruzzo |
| 9 | Akhlaghi, Bose, Mohammadi, Moaveni, Stavridis, Wood (2021), *Eng. Struct.* 227:111413, DOI 10.1016/j.engstruct.2020.111413 | Scuola RC 4 piani con tamponature, Sankhu (Nepal), danneggiata dal sisma di Gorkha 2015; lidar terrestre (13 scansioni) + accelerometri | **Il più forte metodologicamente**: (a) **OMA** — NExT-ERA su vibrazioni ambientali, 3 modi 1,19 / 2,16 / 3,14 Hz (COV 0,5–1,7 %), smorzamenti 1,5–3,0 %; (b) lidar — registrazione cloud-to-cloud, accuratezza media **2,7 mm** (< 2 mm su muri e pilastri a piano terra); difetti di superficie quantificati (pilastri 6–40 %, muri 5–23 %; AUC della CDF per i muri esterni); (c) **model updating** deterministico (LSQ) **e bayesiano**, con il danno da nuvola usato come **prior** e le vibrazioni come *likelihood*; (d) confronto incrociato: danno da nuvola vs danno da vibrazioni vs ispezione visiva | OpenSEES: beam-column inelastici displacement-based + truss (puntoni diagonali per le tamponature), 428 elementi; solo comportamento elastico usato nell'updating | Il legame rigidezza↔difetto di superficie è un'**esponenziale calibrata a giudizio** (κ = α e^{βAUC}), estremi scelti soggettivamente (0 % e 80 % di perdita), forma scelta per **trial and error**; serve altra ricerca su modelli alternativi |
| 10 | Kong, Gu, Xiong, Yuan (2023), *Comput.-Aided Civ. Infrastruct. Eng.* 38:2378–2390, DOI 10.1111/mice.12967 | Parete a taglio RC 1700×2900×200 mm dopo carico ciclico; iPhone 13 Pro (camera + LiDAR) | **Esperimento di verifica dedicato**: 3 blocchi di calcestruzzo di forma regolare, volume teorico vs volume da convex hull — errori **2,35 % / 5,34 % / 7,19 %**, media 4,96 %. Mask R-CNN: loss totale 10,83 %. Perdita di volume della parete 5,44 %. **Nessun confronto FE vs prova ciclica** | Esaedri a 8 nodi, 25×25×25 mm; l'aggiornamento consiste nel **cancellare elementi** | Solo superficie (danno interno non aggiornabile); solo **geometria** (materiali e armature restano manuali); danni < 10 mm persi per la risoluzione del LiDAR; solo spalling riconosciuto; solo mesh esaedrica; passi manuali elencati in Tab. 3 |
| 11 | Graves, Nahshon, Aminfar, Lattanzi (2023), *Data-Centric Engineering* 4:e16, DOI 10.1017/dce.2023.7 | Grigliato di ponte navale in acciaio, 7,5 × 2,5 m, imperfezioni iniziali; laser tracker Faro Vantage | **Il livello probatorio più alto dei 17**: prova a **collasso a scala reale** in fixture NSWC Carderock; il provino è parte di uno **studio round-robin** (Ringsberg et al., 2021). Capacità ultima: fisica **6,59 MN** vs FE aggiornato con kriging **6,56 MN** (**0,46 %**) vs benchmark spettrale 6,68 MN (1,37 %); UQ: 6,58 / 6,56 MN (0,15 % / 0,46 %). Deformazioni quantificate come **distanze di Hausdorff dirette**; interpolate ai nodi con **kriging ordinario** (con intervalli di confidenza al 95 %) | **S8R**: shell a 8 nodi, integrazione ridotta, 5 punti nello spessore; mesh 30 mm, ~100 000 nodi / 35 000 elementi (Abaqus 2019) | **Dichiarano l'insuccesso**: il meccanismo di collasso è riprodotto (instabilità flesso-torsionale del corrente, poi instabilità locale delle ali) ma la **posizione** è sbagliata (sezione 4 invece di 2); rigidezza FE più alta della prova (tensioni residue assunte al 75 % di f_y, mai misurate) |
| 12 | Zhang Y., Xia, Taylor (2024), *Comput.-Aided Civ. Infrastruct. Eng.* 39:3–19, DOI 10.1111/mice.13076 | 2 travi in calcestruzzo con perdita di volume su spigolo e vertice; fotogrammetria da fotocamera consumer | **Misura fisica del ground truth**: volume del danno misurato **riempiendo la cavità con aggregato fine pesato** (1 L = 1717,92 g). Caso 1: misurato 2380,9 mm³ vs simulato 1607,87 mm³ = **67,5 %**. Caso 2: 52 551,9 vs 49 442 mm³ = **94,1 %**. Studio di sensibilità alla semplificazione della nuvola (voxel 0,002→0,007): rapporto di volume 94,08 % → 93,15 % (stabile) | Tetraedri nella zona danneggiata, esaedri nella zona integra (remeshing locale) | La fotogrammetria sbaglia la **profondità** su danni poco profondi (7 mm → 67,5 %; 25 mm → 94,1 %); il mesh di taglio è traslato di 1 mm, il che sottrae volume; molti passaggi manuali (crop, scelta del raggio della palla) |
| 13 | Camo, Waldmann (2025), *Eng. Struct.* 336:120498, DOI 10.1016/j.engstruct.2025.120498 | Travi e ponti reali (Soleuvre, Ettelbruck); fotogrammetria per la linea di deformata sotto carico statico | **Prova di carico statico** (metodo DAD, Deformation Area Difference) + model updating per l'inversione. Precisione fotogrammetrica in situ **0,1186 mm** (da Erdenebat et al.); esperimento su HEB 220 S355 con freccia L/290. **Dichiarano il fallimento parziale**: "i casi studio **non hanno validato pienamente** la tecnica MU per la valutazione del livello di danno" | Sotto-modelli FE al posto di mesh ad alta fedeltà (per costo computazionale) | Su ponti reali la freccia è troppo piccola (L/2450) e il rumore troppo alto; danno rilevabile solo sopra ~50 % di riduzione di rigidezza flessionale; dati confidenziali (non riproducibile) |
| 14 | Yang, Zou, Yang, del Rey Castillo (2024), *Autom. Constr.* 165:105572, DOI 10.1016/j.autcon.2024.105572 | Segmentazione semantica di nuvole di ponti a travata in CA (non ricostruzione) | **Solo metrica di segmentazione**: mIoU ≥ 95,47 % sull'intero ponte, 93,44 % per tipo di componente. Nessuna validazione strutturale — la FEA è usata *a monte*, per generare feature di punto basate sulla conoscenza di dominio | n/a (la FEA genera feature, non risultati) | I dataset sintetici esistenti derivano da BIM as-design e ignorano incompletezza, rumore e danni reali |
| 15 | Zahs, Anders, Kohns, Stark, Hofle (2023), *Int. J. Appl. Earth Obs. Geoinf.* 122:103406, DOI 10.1016/j.jag.2023.103406 | Classificazione dei gradi di danno EMS-98 di edifici, L'Aquila; nuvole fotogrammetriche UAV multi-temporali | **Validazione statistica su dataset etichettato**: 125 edifici di valutazione, overall accuracy 92,0–95,1 %. Il classificatore RF è addestrato su **laser scanning virtuale** (HELIOS++, modello RIEGL VUX-1UAV) invece che su dati reali; errore di registrazione ICP finale **7,4 cm** (definito come SD delle distanze locali nelle zone stabili). **Dataset pubblico**: DOI 10.11588/data/D3WZID | n/a (nessun FEM) | Metodo a livello di edificio; il guadagno con training reale region-specific è < 2–3 % |
| 16 | Shishegaran A., Shishegaran A. (2025), *Int. J. Mech. Syst. Dyn.* 5:324–344, DOI 10.1002/msd2.70021 | Muro di sostegno in CA in ambiente marino; nuvola per misurare la deformata (CloudCompare) | **Validazione di modello su prova altrui**: il modello FE è calibrato su una prova sperimentale su RRCW (curva carico-spostamento, rif. [56]); poi 144 provini simulati e surrogati ML (GEP: 99 % sul danno, 97 % sulla capacità). **La prova non è sulla struttura scansionata** | C3D8R per il calcestruzzo + elementi beam per le barre (Abaqus); mesh 60 mm calcestruzzo | Il modello validato e la struttura rilevata sono oggetti diversi; nessuna prova sulla struttura reale |
| 17 | Rakhee (2025), tesi MSc, University of Wisconsin–Madison (nessun DOI) | Lamiere grecate in acciaio a parete sottile + faro storico Au Sable; Artec Ray/Leo, iPad Pro (Scaniverse), fotogrammetria | (a) geometria: misure da nuvola vs **calibro manuale** (Tab. 3.2–3.4) — Artec Leo vicino al manuale, iPad no (es. raggio 0,15625" manuale vs 0,187" Leo vs 0,574" iPad); (b) **buckling**: lunghezza d'onda da fotogrammetria vs **sensori a fibra ottica** — differenza **0,33 %–28,21 %**; spostamento globale da nuvola iPad vs **OptiTrack** — differenza **16,18–38,28 %**; (c) FE: §4.6 dichiara che il confronto FE vs sperimentale "**è in corso** da parte del gruppo di ricerca" — **non concluso nella tesi** | Abaqus, mesh da slice a intervalli regolari (30 mm; 2 mm sul profilo composito) | Lo spessore (~1 mm) **non è misurabile** dalla scansione: la nuvola descrive solo la superficie esterna; la fotogrammetria **sovrastima** la lunghezza d'onda; il tarpaulin del vacuum box degrada le scansioni a bassa pressione |

### 1.2 Note che non stanno in tabella

- **Incoerenza interna in Zhang et al. 2024** (art. 3): §4.1 scrive "modeling error ... less than 3 mm in more than **95 %** of the region"; le conclusioni scrivono "less than 3 mm" in "**99 %** of the region". Due numeri diversi per lo stesso risultato nello stesso articolo. Se lo si cita, citare la sezione dei risultati, non le conclusioni.
- **7 articoli su 17 non hanno alcun confronto meccanico con una prova**: nn. 5, 6, 7, 12, 14, 15, 17 (il 17 lo dichiara "in corso"). Di questi, 5, 6, 7 sono proprio i casi HBIM su patrimonio — cioè i più vicini per tipologia a una tesi su un telaio esistente.
- **Chi dichiara un criterio di accettazione numerico *prima* di misurare**: solo l'art. 7 (media ∈ ±0,10 m, σ < 0,10 m). Tutti gli altri riportano il numero e lo giudicano "acceptable"/"satisfactory" a posteriori.
- **Chi dichiara un risultato negativo**: art. 11 (posizione del collasso sbagliata), art. 13 ("non validato pienamente"), art. 12 (67,5 % di volume nel caso 1), art. 7 (CSV sismico 0,88 < 2). Sono i quattro lavori più credibili proprio per questo.

---

## 2. Fonti esterne

### 2.1 Scan-to-FEM civile con validazione sperimentale

| Fonte | Cosa aggiunge |
|---|---|
| Castellazzi, Lo Presti, D'Altri, de Miranda (2022), *Cloud2FEM: A finite element mesh generator based on point clouds of existing/historical structures*, **SoftwareX 18:101099**, DOI 10.1016/j.softx.2022.101099 | Riferimento obbligato per il ramo "voxel" dello scan-to-FEM. Pipeline: slicing verticale della nuvola → poligoni chiusi per fetta → impilamento a voxel → **mesh esaedrica a 8 nodi**, esportata in **notazione Abaqus `.inp`** (l'esempio ha 31 638 esaedri a 8 nodi). Codice GPL-3, Python (PyQt5, NumPy, pyntcloud, Shapely). Nota importante: l'articolo è una *original software publication* — **non contiene una validazione sperimentale**, cita l'aggiornamento del modello e le valutazioni sismiche come lavori a valle. Repo: github.com/gcastellazzi/Cloud2FEM |
| Bassoli, Vincenzi, D'Altri, de Miranda, Forghieri, Castellazzi (2018), *Ambient vibration-based finite element model updating of an earthquake-damaged masonry tower*, **Struct. Control Health Monit.** — onlinelibrary.wiley.com/doi/full/10.1002/stc.2150 | Il caso canonico di torre in muratura: nuvola → FEM → **OMA** → model updating con dati di vibrazione ambientale su struttura danneggiata dal sisma. È il modello di riferimento per "livello 5" della scala del §5 |
| Gentile, Saisi (2007), *Ambient vibration testing, dynamic identification and model updating of a historic tower*, **NDT & E International** — sciencedirect.com/science/article/abs/pii/S0963869511001745 (record ScienceDirect) | Lavoro fondativo su AVT + identificazione dinamica + updating su torre storica |
| *Model updating of a masonry tower based on operational modal analysis: the role of soil-structure interaction*, **Case Studies in Construction Materials** (2022) — sciencedirect.com/science/article/pii/S2214509522000894 | Mostra che l'updating su sole frequenze può essere **non identificabile** se non si modella l'interazione terreno-struttura: monito diretto per chi valida solo con frequenze |
| *Scan-to-BIM-to-Sim: Automated reconstruction of digital and simulation models from point clouds with applications on bridges* (2025), **Developments in the Built Environment** — sciencedirect.com/science/article/pii/S2590123025003743 | Il termine "scan-to-BIM-to-sim" con applicazione a ponti; utile per posizionare la nomenclatura |
| Jasinski et al. (2023), *The Concept of Creating Digital Twins of Bridges Using Load Tests*, **Sensors** 23:7349, DOI 10.3390/s23177349 | Gemello digitale di ponte **calibrato su prove di carico**; le frecce misurate risultano il 68–72 % di quelle calcolate — esempio di scostamento sistematico onesto |
| *Finite Element Model Updating of RC Bridge Structure with Static Load Testing: ThiThac Bridge*, **Materials** — ncbi.nlm.nih.gov/pmc/articles/PMC9695130/ | Caso di updating con sola prova statica |
| **ASME V&V 10-2019 (R2025)**, *Standard for Verification and Validation in Computational Solid Mechanics* — asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics; e **ASME V&V 10.1-2012 (R2022)**, *An Illustration of the Concepts of V&V in CSM* | **La norma da citare in tesi per definire cosa vuol dire "validare"**. Distinzione fondamentale: *verification* = fedeltà **numerica** della simulazione (mesh, solutore, convergenza); *validation* = fedeltà alla **fisica**, e si fa solo confrontando con un esperimento. Introduce la gerarchia di validazione (componente → sotto-sistema → sistema) e la quantificazione dell'incertezza. **Nessuno dei 17 PDF la cita** |

### 2.2 Benchmark e dataset con ground truth geometrico

| Fonte | Cosa fornisce |
|---|---|
| Berger, Levine, Nonato, Taubin, Silva (2013), *A benchmark for surface reconstruction*, **ACM Trans. Graph.** 32(2), DOI 10.1145/2451236.2451246 — PDF: matthewberger.github.io/papers/bench.pdf | **Il benchmark storico**. Pipeline in 3 fasi: (1) modellazione della forma con **superfici implicite** (per avere dettagli di scala diversa e spigoli vivi), (2) **simulazione sintetica di range scan** con artefatti realistici (rumore, non uniformità, scansioni disallineate), (3) valutazione confrontando la superficie ricostruita con un **campionamento denso e uniforme della superficie implicita** — cioè il ground truth è analitico, non un altro rilievo |
| Berger, Tagliasacchi, Seversky, Alliez, Guennebaud, Levine, Sharf, Silva (2017), *A Survey of Surface Reconstruction from Point Clouds*, **Computer Graphics Forum** 36(1), DOI 10.1111/cgf.12802 | La rassegna di riferimento: tassonomia dei metodi e delle metriche |
| Sulzer, Marlet, Vallet, Landrieu (2023–2024), *A Survey and Benchmark of Automatic Surface Reconstruction from Point Clouds*, **arXiv:2301.13656**, DOI 10.48550/arXiv.2301.13656 (accettato TPAMI); codice e dati: github.com/raphaelsulzer/dsr-benchmark | Benchmark moderno. Metriche standardizzate: **Chamfer distance**, **F-score** (a soglia), **Normal Consistency Score**. Conclusione utile per la tesi: i metodi *tradizionali* (Poisson e simili) sono **più robusti** alle anomalie delle acquisizioni reali dei metodi learning-based, che vincono solo quando train e test hanno le stesse caratteristiche |
| Huang, Wen, Liu, Sheng, Wang, Yang (2022), *Surface Reconstruction from Point Clouds: A Survey and a Benchmark*, **arXiv:2205.02413** | Benchmark parallelo al precedente, con dataset sintetico e reale |
| Kazhdan, Hoppe (2013), *Screened Poisson Surface Reconstruction*, **ACM Trans. Graph.** 32(3), DOI 10.1145/2487228.2487237 | Il metodo che la pipeline della tesi usa. Va citato in versione **screened** (2013), non nella versione 2006. Gli autori si valutano sul framework di Berger et al. |
| Cignoni, Rocchini, Scopigno (1998), *Metro: Measuring Error on Simplified Surfaces*, **Computer Graphics Forum** 17(2), DOI 10.1111/1467-8659.00236 — vcg.isti.cnr.it/activities/OLD/surfacegrevis/simplification/metro.html | **La definizione operativa** di errore fra due mesh: campionamento della superficie + distanza punto-superficie, approssimazione della distanza di Hausdorff. Restituisce **errore massimo e medio** oltre a aree e volumi, e la colorazione della superficie. Implementato in MeshLab |
| Aspert, Santa-Cruz, Ebrahimi (2002), *MESH: Measuring Errors between Surfaces using the Hausdorff Distance*, **IEEE ICME** | La formulazione esplicita di Hausdorff diretta e simmetrica fra mesh, complementare a Metro |
| Lague, Brodu, Leroux (2013), *Accurate 3D comparison of complex topography with terrestrial laser scanner: application to the Rangitikei canyon (N-Z)*, **ISPRS J. Photogramm. Remote Sens.** 82:10–26 — PDF: nicolas.brodu.net/common/recherche/publications/M3C2.pdf; plugin: cloudcompare.org/doc/wiki/index.php?title=M3C2_(plugin) | **M3C2**. Definizione: per ogni punto core, la normale locale è stimata su un intorno di scala *D*; lungo quella normale si proietta un **cilindro** di diametro *d* e si prende la differenza fra le posizioni medie delle due nuvole dentro il cilindro. Restituisce una distanza **con segno lungo la normale** e — cosa che le altre metriche non fanno — un **livello di confidenza spazialmente variabile** che tiene conto di rugosità locale e errore di registrazione |
| Winiwarter, Esmoris Pena, Weiser, Anders, Sanchez, Searle, Hofle (2022), *Virtual laser scanning with HELIOS++*, **Remote Sensing of Environment** | Il simulatore usato dall'art. 15 per generare dati di addestramento con ground truth noto per costruzione |
| Dataset L'Aquila di Zahs et al., DOI **10.11588/data/D3WZID** | Uno dei pochi dataset pubblici del dominio civile con etichettatura di danno EMS-98 su nuvole multi-temporali |
| Knapitsch, Park, Zhou, Koltun (2017), *Tanks and Temples*, ACM TOG; Schops et al. (2017), *ETH3D*, CVPR | Benchmark di ricostruzione 3D generalisti che hanno reso standard la coppia **precision/recall + F-score a soglia** al posto della sola distanza media |
| Historic England, *3D Laser Scanning for Heritage* (3a ed.), Boardman & Bryan — historicengland.org.uk/images-books/publications/3d-laser-scanning-heritage/ | Linea guida operativa (non peer-reviewed ma normativa di settore) sulla dichiarazione delle tolleranze: la pratica raccomandata è **definire in anticipo la deviazione massima ammessa** del modello dalla nuvola (es. 5 mm o 10 mm) |

**Nota di staleness.** Cloud2FEM v1.0 è del 2022; il repo GitHub è stato aggiornato dopo. Il benchmark Sulzer et al. è stato revisionato l'ultima volta a dicembre 2024. Non ho verificato le versioni correnti di CloudCompare (la pagina wiki risponde 403 a fetch automatica) — le definizioni C2C/C2M qui riportate vengono dalla letteratura primaria e dall'uso che ne fanno gli articoli 3 e 7, non dalla documentazione ufficiale letta direttamente.

---

## 3. Metriche: definizioni formali

Sia **P** la nuvola sorgente (n punti), **M** la mesh ricostruita, **S** un campionamento denso di M.

### 3.1 Distanza di Hausdorff

Distanza **diretta** (one-sided) da A a B:

    h(A, B) = max_{a∈A} min_{b∈B} ||a − b||₂

Distanza **simmetrica** (Hausdorff propriamente detta):

    H(A, B) = max( h(A,B), h(B,A) )

Queste sono esattamente le eq. (1)–(2) dell'articolo 3 (Zhang et al. 2024, *Eng. Struct.* 310:118126, §4.1). Loro aggiungono un raffinamento (eq. 3): invece del punto più vicino nel set discreto, usano un **modello quadratico locale Q** fittato sui vicini nel set di riferimento, e cercano il punto più vicino su Q — cioè distanza punto-superficie, non punto-punto.

**Punto critico**: H è un **massimo**, quindi è governato dall'outlier peggiore. Dichiarare "Hausdorff = 135 mm" senza percentili non dice nulla sulla qualità del modello.

### 3.2 Cloud-to-Cloud (C2C) e Cloud-to-Mesh (C2M)

- **C2C**: per ogni punto di A, distanza al punto più vicino di B (nearest neighbour su kd-tree). Nella pratica CloudCompare si può raffinare con un modello locale (piano ai minimi quadrati, quadrica, triangolazione di Delaunay 2.5D) per ridurre l'errore da campionamento discreto. **Sempre non negativa, senza segno.**
- **C2M**: per ogni punto della nuvola, distanza al **triangolo** più vicino della mesh. Può essere **con segno** (positivo/negativo secondo il lato della faccia). È quella usata dall'art. 7 sull'acquedotto (comando "Cloud to Mesh Distance").

La differenza pratica: C2C confronta due campionamenti e quindi **misura anche la differenza di campionamento**; C2M confronta un campionamento con una superficie continua e quindi isola meglio l'errore geometrico.

### 3.3 Chamfer distance

    CD(A, B) = (1/|A|) Σ_{a∈A} min_{b∈B} ||a−b||²  +  (1/|B|) Σ_{b∈B} min_{a∈A} ||a−b||²

(esistono varianti con norma L1 e con media al posto di somma — **dichiarare sempre quale variante**). È la media bidirezionale, quindi robusta agli outlier al contrario di Hausdorff, ma **cieca** ai difetti locali: una mesh con un buco grande e un'ottima aderenza altrove può avere una CD bassa. È la metrica standard nel benchmark Sulzer et al. e nella letteratura di ricostruzione neurale.

### 3.4 F-score a soglia (precision / recall)

Data una soglia τ:
- **precision** = frazione dei punti di S (mesh ricostruita) che hanno un punto di ground truth entro τ → penalizza la **materia inventata** (ipotesi di ricostruzione false, gonfiature di Poisson);
- **recall** = frazione dei punti di ground truth che hanno un punto di S entro τ → penalizza la **materia mancante** (buchi, zone non scansionate);
- **F-score** = media armonica.

Introdotta come standard da Tanks and Temples (Knapitsch et al. 2017). **È la metrica che separa i due errori che RMS e Chamfer confondono**, ed è quella che manca completamente ai 17 articoli letti.

### 3.5 M3C2

Lague, Brodu, Leroux (2013). Per ogni punto core *i*:
1. normale **n** stimata su una sfera di raggio *D/2* (scala della normale);
2. si proietta un **cilindro** di diametro *d* lungo **n**, in entrambi i versi;
3. distanza = differenza fra le **posizioni medie** delle due nuvole dentro il cilindro, **lungo n** → distanza **con segno**;
4. **livello di confidenza** LoD₉₅% che combina la rugosità locale σ delle due nuvole (dentro il cilindro), i conteggi n₁, n₂ e l'errore di registrazione: una variazione è dichiarata significativa solo se |distanza| > LoD.

È l'unica delle metriche qui elencate che (a) dà un segno, (b) fornisce un test di significatività punto per punto, (c) è progettata per superfici rugose e nuvole con densità disomogenea. **Nessuno dei 17 PDF la usa.**

### 3.6 Normal Consistency

Media del valore assoluto del prodotto scalare fra normali corrispondenti fra le due superfici. Coglie differenze di ordine superiore (orientamento locale) che le distanze puntuali non vedono; usata nel benchmark Sulzer et al.

---

## 4. Prassi accettata per dichiarare l'accuratezza geometrica di una mesh vs la nuvola sorgente

### 4.1 Cosa si riporta

Dalla lettura incrociata dei 17 PDF e delle fonti esterne, la prassi difendibile è:

1. **Non un solo numero.** Il minimo accettabile è **media (o mediana) + deviazione standard + massimo**, e la **distribuzione** (istogramma) o almeno i percentili. L'art. 3 riporta media, istogramma e la quota di regione sotto soglia; l'art. 7 riporta media + σ + criterio; l'art. 5 riporta solo il massimo (e infatti dice poco).
2. **RMS vs media.** L'RMS penalizza gli outlier più della media assoluta. Se si riporta RMS, si deve riportare anche il massimo, altrimenti non è distinguibile un errore diffuso piccolo da un errore concentrato grande.
3. **Percentili, non solo max.** Formulazione consolidata: "errore < X mm sul P % della superficie" (art. 3: "< 3 mm su > 95 % della regione"). È più informativa del massimo perché immune agli outlier di registrazione.
4. **Il massimo va sempre dato**, e va **spiegato dove si trova**: se il massimo è su uno spigolo o su una zona non scansionata, va detto e va escluso esplicitamente dal calcolo (l'art. 3 lo fa: esclude dall'analisi d'errore i punti rossi ricostruiti ma non scansionati).
5. **Soglia dichiarata prima.** Historic England raccomanda di fissare la deviazione massima ammessa *prima* della misura. In letteratura civile lo fa solo l'art. 7 (media ∈ ±0,10 m, σ < 0,10 m). Nel resto la soglia è implicita e a posteriori — cattiva pratica facile da attaccare in commissione.
6. **Contro cosa.** La distanza mesh↔nuvola sorgente è **autoconsistenza**, non accuratezza. Se il ground truth è la nuvola stessa, l'errore misurato non contiene l'errore del rilievo. Va dichiarato separatamente: (a) errore di registrazione delle scansioni, (b) errore del rilievo topografico su check point indipendenti, (c) errore mesh↔nuvola. L'art. 7 è l'unico dei 17 che li separa tutti e tre (RTK ±7/14 mm → CP 3,53 cm → C2M 2,2 cm).

### 4.2 Come si evita il doppio conteggio

Tre trappole, tutte presenti nella letteratura letta:

- **Trappola 1 — misurare l'errore contro il dato che ha generato il modello.** Se la mesh è ricostruita dalla nuvola e poi l'errore è misurato contro *quella stessa* nuvola, si sta misurando la fedeltà del fitting, non l'accuratezza. Il rimedio accettato: **check point indipendenti** (art. 7: 7 GCP per georeferenziare, 7 CP **diversi** per validare) o una **misura fisica indipendente** (art. 12: riempimento con aggregato pesato; art. 17: calibro; art. 10: blocchi di volume noto).
- **Trappola 2 — sommare due volte la stessa incertezza.** Se l'errore di registrazione è già incluso nella nuvola consolidata, non va risommato all'errore mesh↔nuvola: sono lo stesso errore visto due volte. M3C2 lo gestisce esplicitamente inserendo l'errore di registrazione **dentro** il LoD, una volta sola.
- **Trappola 3 — Hausdorff simmetrico calcolato come somma delle due direzioni.** H è un **max**, non una somma: h(A,B) e h(B,A) misurano cose diverse (materia inventata vs materia mancante) e vanno riportate **separatamente**, poi combinate con max. Sommarle o mediarle è doppio conteggio mascherato. La coppia precision/recall (§3.4) è la forma pulita di questa distinzione.

### 4.3 Come si tratta il campionamento

- **Ricampionare la mesh, non confrontare vertici.** Confrontare i vertici della mesh con la nuvola misura la densità del meshing, non la geometria. La prassi (Metro, Cignoni et al. 1998) è campionare la superficie **densamente e uniformemente** e calcolare distanze punto-superficie. L'art. 3 lo fa esplicitamente: "a point cloud, denoted by Pm, was **resampled** from the created gDT".
- **Dichiarare la densità di campionamento** e verificare che sia almeno confrontabile con quella della nuvola sorgente. Berger et al. 2013 confrontano contro "a dense uniformly distributed sampling of the implicit surface".
- **Downsampling a voxel: dichiarare la dimensione e mostrare la sensibilità.** L'art. 12 fa lo studio giusto: sei livelli di voxel (0,002→0,007), rapporto di volume 94,08 %→93,15 %, cioè **il risultato è stabile e lo dimostra**. Chi non fa questo studio non può escludere che il proprio numero dipenda da una scelta arbitraria di voxel.
- **Densità non uniforme e occlusioni.** Le zone non scansionate producono superficie **inventata** dalla ricostruzione (Poisson chiude i buchi). Se non si esclude esplicitamente quella superficie dal calcolo dell'errore, il numero è falso in *entrambe* le direzioni: la mesh è vicina alla nuvola dove la nuvola c'è, e non è vincolata dove non c'è. L'art. 3 esclude quei punti; l'art. 12 attribuisce a questo il 67,5 % del caso 1.

---

## 5. Sintesi critica — la scala della forza probatoria

Sette livelli, da 0 a 6, dal più debole al più forte. Per ognuno: che cosa dimostra, chi lo fa in letteratura, cosa serve concretamente per farlo.

### Livello 0 — Il programma gira (autoconsistenza procedurale)
**Cosa dimostra**: che la pipeline termina e produce un `.inp` leggibile dal solutore. **Nulla sulla correttezza.**
**Chi lo fa**: Cloud2FEM (Castellazzi et al. 2022, SoftwareX) è esplicitamente una *software publication* e si ferma qui; art. 14 (segmentazione).
**Cosa serve**: nulla oltre l'esecuzione. In tesi vale come premessa, non come risultato.

### Livello 1 — Autoconsistenza geometrica interna
**Cosa dimostra**: che la mesh aderisce alla nuvola da cui è nata. **Non è accuratezza**: è fedeltà del fitting.
**Chi lo fa**: art. 5 (deviazione NURBS↔mesh max 0,5 e 1 mm); art. 3 (C2C, < 3 mm su > 95 %); art. 7 (C2M media 0,022 m, σ 0,08 m).
**Cosa serve**: ricampionamento denso della mesh (§4.3), metrica dichiarata (C2M o M3C2), esclusione documentata delle zone non scansionate, media + σ + max + percentili + istogramma, e uno **studio di sensibilità al voxel** come quello dell'art. 12.
**Vulnerabilità in commissione**: "state confrontando il modello con il dato che lo ha generato".

### Livello 2 — Confronto con misura diretta indipendente della geometria
**Cosa dimostra**: che la geometria ricostruita corrisponde alla realtà fisica, entro un'incertezza dichiarata di uno **strumento diverso**.
**Chi lo fa**: art. 17 (calibro manuale vs nuvola, tabelle 3.2–3.4); art. 4 (dimensioni calcolate vs misurate: ±3,05 mm forma, ±9,2 mm lunghezza); art. 3 (3–4 mm in lunghezza, 1 mm in altezza/larghezza vs misure manuali); art. 12 (volume da riempimento con aggregato pesato: 67,5 % e 94,1 %); art. 10 (volume di 3 blocchi regolari: errore medio 4,96 %); art. 7 (check point GNSS indipendenti dai GCP, 3,53 cm).
**Cosa serve**: (a) uno strumento indipendente dal rilievo (calibro, distanziometro, stazione totale, GNSS RTK, misura di volume per spostamento/riempimento); (b) **punti di controllo non usati nel processo** (la distinzione GCP/CP); (c) l'incertezza dichiarata dello strumento di riferimento; (d) abbastanza punti da avere una statistica, non due o tre misure.
**Nota**: questo è il livello **minimo credibile** per una tesi metrologica. Sette dei 17 articoli non ci arrivano.

### Livello 3 — Verifica numerica del modello FE (convergenza, non validazione)
**Cosa dimostra**: che il risultato non dipende dalla discretizzazione. Nella terminologia **ASME V&V 10** questa è *verification*, **non** *validation*: riguarda la fedeltà numerica, non la fisica.
**Chi lo fa**: art. 1 (sensibilità di mesh 20/10/5 mm; la mesh da 20 mm sovrastima la capacità del 14 %); art. 8 (studio di convergenza in COMSOL); art. 5 (confronto 3D/2D/1D — è verification incrociata fra idealizzazioni); art. 12 (sensibilità al voxel).
**Cosa serve**: almeno tre livelli di raffinamento con la stessa quantità di interesse; il criterio di arresto dichiarato; il costo computazionale riportato (l'art. 1 lo fa: 83,6 s / 1006,3 s / 3459,5 s).
**Vulnerabilità**: presentare la convergenza come "validazione". È l'errore più frequente: se la mesh convergesse su un modello sbagliato, converge lo stesso.

### Livello 4 — Auto-validazione incrociata (due metodi propri che concordano)
**Cosa dimostra**: consistenza interna fra due idealizzazioni. **Non è un confronto con la realtà.**
**Chi lo fa**: art. 6 (lo spettro di risposta modale "validato" da un pushover SAA proprio); art. 5 (3D vs 2D vs 1D); art. 3 (elementi indeboliti vs analisi *phased*).
**Cosa serve**: due formulazioni davvero indipendenti, non due varianti dello stesso modello.
**Vulnerabilità seria**: due modelli che condividono la stessa geometria e gli stessi materiali assunti concorderanno anche se entrambi sono sbagliati. Va presentato come **coerenza**, mai come validazione — l'art. 6 usa la parola "validation" nel titolo di sezione e questo è attaccabile.

### Livello 5 — Confronto con misura sperimentale sulla **stessa** struttura, in servizio
**Cosa dimostra**: che il modello riproduce il comportamento reale dell'oggetto rilevato, in campo elastico.
**Sotto-livelli, in ordine crescente**:
- **5a — prova di carico statico**: frecce/spostamenti FE vs misurati. Art. 4 (20/63 kN sul modello di laboratorio, 700/1200 N sulla passerella); art. 13 (metodo DAD su ponti reali, fotogrammetria a 0,1186 mm); Jasinski et al. 2023 (Sensors 23:7349).
- **5b — analisi modale sperimentale / OMA**: frequenze e forme modali FE vs identificate. Art. 4 (martello: 2,68/6,39/9,72 Hz vs FE 2,52/5,86/9,67 Hz); art. 9 (**vibrazioni ambientali**, NExT-ERA, 1,19/2,16/3,14 Hz con COV 0,5–1,7 %); Bassoli et al. 2018.
- **5c — OMA + model updating bayesiano con incertezza quantificata**: art. 9 (prior dalla nuvola, likelihood dalle vibrazioni, posterior con varianza); Graves et al. 2023 per la parte UQ.
**Cosa serve concretamente**:
- per 5a: un carico noto e applicabile (per un telaio in laboratorio: martinetto o pesi calibrati), strumenti di spostamento (LVDT, fotogrammetria, laser), e almeno **due configurazioni di carico** per evitare di calibrare su un solo punto;
- per 5b: **accelerometri** (l'art. 9 ne usa 4 per piano su due setup, 45–54 min di registrazione, campionamento 2048 Hz poi decimato a 256 Hz), un canale di riferimento condiviso fra i setup per assemblare le forme modali, e un algoritmo output-only (NExT-ERA, SSI-Cov, FDD) con **diagramma di stabilizzazione**;
- per 5c: prior definite e giustificate, funzione di verosimiglianza esplicita, e un campionatore (TMCMC o simili). Serve dichiarare che il prior **è soggettivo** (l'art. 9 lo fa onestamente).
**Vulnerabilità**: l'OMA da sola non identifica univocamente le rigidezze — se non si modella l'interazione terreno-struttura o le condizioni al contorno, l'updating compensa un errore con un altro (vedi *Case Studies in Construction Materials* 2022 sul ruolo della SSI).

### Livello 6 — Prova distruttiva a scala reale, con benchmark indipendente
**Cosa dimostra**: che il modello predice la **capacità ultima** e il **meccanismo di collasso**. È il livello massimo raggiungibile.
**Chi lo fa**: **Graves et al. 2023** (art. 11) — prova a collasso su grigliato 7,5×2,5 m, provino parte di uno studio **round-robin** internazionale (Ringsberg et al. 2021), capacità 6,59 MN misurata vs 6,56 MN predetta (0,46 %), con intervalli di incertezza propagati dal kriging. Nei 17 è l'unico. Parzialmente: art. 1 e art. 3 (prove a rottura su travi RC di laboratorio, ma non su una struttura rilevata in situ).
**Cosa serve**: una struttura sacrificabile (in tesi: un provino, non il telaio del caso studio), una macchina di prova, e — decisivo — **un riferimento esterno** (round-robin, benchmark pubblicato, o almeno un metodo alternativo consolidato come termine di paragone: Graves usa lo schema spettrale di Ringsberg come benchmark, non se stesso).
**Cosa rende Graves credibile più del numero**: dichiara che il modello **sbaglia la posizione** dell'instabilità (sezione 4 invece di 2) e che la rigidezza è sovrastimata per via delle tensioni residue mai misurate. Un lavoro che riporta solo il 0,46 % di errore e tace il resto è meno difendibile di uno che riporta entrambi.

### Riepilogo operativo della scala

| Liv. | Nome | Dimostra | Nei 17 PDF | Difendibile da sola? |
|---|---|---|---|---|
| 0 | Il programma gira | nulla | Cloud2FEM, art. 14 | no |
| 1 | Autoconsistenza geometrica | fedeltà del fitting | artt. 3, 5, 7 | no |
| 2 | Misura diretta indipendente | accuratezza geometrica | artt. 3, 4, 7, 10, 12, 17 | **soglia minima** |
| 3 | Convergenza numerica (V&V: *verification*) | indipendenza dalla mesh | artt. 1, 5, 8, 12 | no (necessaria, non sufficiente) |
| 4 | Auto-validazione incrociata | coerenza interna | artt. 3, 5, 6 | no |
| 5 | Prova su struttura in servizio (statica / OMA / bayesiana) | fedeltà fisica in campo elastico | artt. 4, 9, 13 | **sì** |
| 6 | Prova distruttiva + benchmark indipendente | capacità ultima e meccanismo | art. 11 | **sì, massimo** |

**Regola di composizione**: i livelli non si sostituiscono, si **impilano**. Un lavoro rigoroso porta 1 **e** 2 **e** 3, e almeno uno fra 5 e 6. Il livello 4 è un complemento, mai un sostituto. Un lavoro che porta solo 1 + 4 (come gli artt. 5, 6, 7 in questa raccolta) è pubblicabile in ambito HBIM ma **non regge una domanda diretta** del tipo "come sapete che il vostro modello è giusto?".

---

## 6. Le 5 lacune più gravi della prassi corrente

Ordinate per gravità probatoria, con l'evidenza che le sostiene.

**1. La metrica geometrica dominante misura la cosa sbagliata, e nessuno usa quella giusta.**
Su 17 articoli: 2 usano Hausdorff (artt. 3, 11), 2 usano C2C (artt. 3, 9), 1 usa C2M (art. 7). **Zero usano M3C2. Zero usano Chamfer. Zero usano F-score/precision-recall.** M3C2 esiste dal 2013 (Lague et al., ISPRS J. 82:10–26) ed è l'unica metrica che dia un **segno** e un **test di significatività punto per punto** che tiene conto di rugosità e errore di registrazione. Precision/recall a soglia è standard nella computer graphics dal 2017 (Tanks and Temples) ed è l'unica cosa che separa "materia inventata" da "materia mancante" — la distinzione che conta di più quando si chiude una superficie con Poisson.

**2. Sette articoli su diciassette non confrontano mai il modello con un esperimento, e tre di questi sono proprio i lavori HBIM su patrimonio costruito.**
Artt. 5, 6, 7, 12, 14, 15, 17. L'art. 6 chiama "validation" un pushover proprio che conferma un'analisi spettrale propria; l'art. 5 confronta tre proprie idealizzazioni fra loro; l'art. 7 valuta la stabilità contro una norma, non contro una misura. Nella tassonomia ASME V&V 10 questo è *verification*, mai *validation*. Il risultato è un intero filone (scan→HBIM→FEM su patrimonio) la cui credibilità poggia su coerenza interna. Nessuno dei 17 PDF cita ASME V&V 10, che è la norma che definisce la differenza.

**3. Le soglie di accettazione sono quasi sempre dichiarate dopo aver visto il numero.**
Un solo articolo su 17 (l'art. 7 sull'acquedotto) fissa il criterio prima: media ∈ [−0,10; +0,10] m, σ < 0,10 m, citando una fonte esterna. Tutti gli altri riportano il valore e lo giudicano "acceptable", "satisfactory", "of high precision" a posteriori. Historic England raccomanda esplicitamente la pratica opposta (definire la deviazione massima ammessa in anticipo). Una soglia decisa dopo non è un test: è una descrizione.

**4. Le proprietà dei materiali sono assunte, e l'errore che introducono non è mai separato dall'errore geometrico.**
L'art. 7 stima E dalla geologia locale (E = 0,50·E_b = 8500 N/mm²) senza una prova; l'art. 6 usa NDT aggregati; l'art. 11 assume le tensioni residue al 75 % di f_y "**implicitly**", non le misura, e poi attribuisce a questo lo scarto di rigidezza. Quando il modello sbaglia, non è distinguibile se ha sbagliato la geometria (che è il contributo dello scan-to-FEM) o il materiale (che non lo è). Nessuno dei 17 esegue un'analisi di sensibilità che separi i due contributi. Per una tesi il cui contributo è **geometrico**, questa è la lacuna che rende inutile il proprio risultato: un errore del 5 % sulla freccia non prova nulla se un errore del 20 % su E può produrne uno uguale.

**5. La pipeline specifica di questa tesi — Poisson → riparazione → tetraedrizzazione — è quasi assente dalla letteratura letta, e i suoi errori caratteristici non sono documentati.**
Ricerca testuale sui 17: "Poisson" come metodo di ricostruzione compare **3 volte, tutte in citazioni di introduzione** (art. 4, che cita Kasotakis; art. 11, che lo cita come alternativa non usata). "MeshFix" 0 volte. "TetGen" 0 volte. "watertight"/"manifold" 0 volte. Elementi tetraedrici: solo artt. 8 (COMSOL, tet liberi) e 12 (tet nella zona danneggiata). **Tutta la letteratura civile letta usa esaedri** (C3D8R negli artt. 1, 16; esaedri a 8 nodi negli artt. 10 e in Cloud2FEM; brick nell'art. 3), **shell** (S8R nell'art. 11, shell generici negli artt. 6, 7), o **beam/truss** (BEAM188/LINK180 nell'art. 4). Conseguenza pratica: (a) non esiste un termine di paragone pubblicato per l'accuratezza di una pipeline Poisson→tet su struttura civile — va costruito; (b) le patologie specifiche di quella pipeline (chiusura spuria dei buchi da parte di Poisson, degradazione della qualità dei tetraedri dopo MeshFix, sensibilità alla profondità dell'octree) **non sono trattate** dalla letteratura di dominio e vanno cercate nella letteratura di computer graphics (Kazhdan & Hoppe 2013; benchmark di Berger et al. 2013 e Sulzer et al. 2024); (c) la scelta di TetGen/tetraedri va **giustificata esplicitamente** in tesi contro l'alternativa voxel/esaedrica di Cloud2FEM, perché una commissione che conosce il dominio si aspetta esaedri.

---

## 7. Caveat

- Il testo dei PDF è estratto automaticamente (`pdftotext -layout`): tabelle a più colonne e formule risultano a tratti disallineate. I numeri citati sono stati letti nel loro contesto in prosa, non presi da celle isolate, salvo dove indicato il numero di tabella.
- L'articolo sull'acquedotto di Carcauz non ha **anno né DOI stampati** nella copia PDF (pp. 111–139 di *Conservation Science in Cultural Heritage*). Non li ho inventati: vanno verificati sulla rivista prima di citarlo.
- L'art. 3 contiene due valori discordanti per lo stesso risultato (95 % vs 99 %): vedi §1.2.
- Le fonti esterne di §2.1 (Bassoli, Gentile & Saisi, Scan-to-BIM-to-Sim, ThiThac) sono state **individuate via ricerca web**, non lette integralmente. Le uso come indicazioni di dove guardare, non come base per affermazioni numeriche.
- La documentazione ufficiale di CloudCompare risponde **403** alle richieste automatiche: le definizioni C2C/C2M in §3.2 provengono dalla letteratura primaria (Cignoni et al. 1998; Lague et al. 2013) e dall'uso documentato negli artt. 3 e 7, non dal wiki letto direttamente.
- ASME V&V 10-2019 è a pagamento: ho letto la descrizione ufficiale ASME/ANSI, non il testo della norma. La distinzione verification/validation riportata è quella dichiarata nella scheda ufficiale.
- Non ho verificato le versioni correnti di Cloud2FEM (v1.0 del 2022; il repo è stato aggiornato dopo) né la pubblicazione definitiva su TPAMI del benchmark Sulzer et al. (arXiv rev. dicembre 2024).
