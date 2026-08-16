## Panoramica tecnica di MeshReconstructorPro

MeshReconstructorPro è un’applicazione desktop Windows per trasformare una nuvola di punti 3D o una mesh superficiale in un modello volumetrico tetraedrico, esportabile per analisi FEM in Abaqus. La distribuzione locale è un eseguibile nativo accompagnato da runtime CPython 3.12 e librerie scientifiche/GUI: PySide6/Qt6, Open3D, VTK/PyVista, TetGen e meshio.

La catena funzionale è:

```text
Nuvola di punti / mesh
        ↓
Importazione e riduzione dati
        ↓
Ricostruzione della superficie triangolare
        ↓
Ritopologia, pulizia e riparazione topologica
        ↓
Ottimizzazione per Abaqus
        ↓
Tetraedrizzazione volumetrica
        ↓
Esportazione .inp (C3D4) e formati di mesh
```

## 1. Input e rappresentazione dei dati

Il programma accetta file 3D costituiti da punti o mesh. Nell’ambiente di tesi sono presenti, fra gli altri:

- `lab_frame.pcd`: nuvola di punti PCD;
- `muro_generato.ply`: mesh/nuvola in formato PLY.

Una nuvola di punti è un insieme discreto:

\[
P = \{p_i\}_{i=1}^{N}, \qquad p_i=(x_i,y_i,z_i)
\]

Eventualmente, ciascun punto può avere attributi aggiuntivi, quali colore, intensità o normale. La nuvola non contiene connettività: non specifica quali punti siano collegati da facce o quale sia il volume interno dell’oggetto. Il compito principale del software è quindi inferire una superficie triangolare coerente e, successivamente, un volume discretizzato.

Internamente, la geometria passa attraverso almeno tre rappresentazioni:

1. point cloud: coordinate discrete senza topologia;
2. surface mesh: vertici, spigoli e facce triangolari;
3. volume mesh: nodi e tetraedri, adatti a un solutore FEM.

## 2. Interfaccia e componenti software

L’interfaccia grafica è basata su Qt6/PySide6. Il rendering e la manipolazione 3D sono supportati dalle librerie Open3D, VTK e PyVista/PyVistaQt; i formati di mesh e l’esportazione sono gestiti da meshio; TetGen è incluso per la generazione tetraedrica.

La struttura logica dell’applicazione è quindi riconducibile a quattro sottosistemi:

| Sottosistema | Responsabilità |
|---|---|
| GUI | Caricamento file, configurazione parametri, comandi di elaborazione, visualizzazione e statistiche |
| Geometria superficiale | Riduzione della nuvola, stima/uso delle normali, ricostruzione e pulizia della mesh |
| Topologia e riparazione | Eliminazione di difetti, chiusura dei bordi, controllo della condizione di solido |
| Mesh FEM e I/O | Tetraedrizzazione, creazione di elementi C3D4 e scrittura dei formati di output |

## 3. Caricamento e sfoltimento voxel

Dopo l’importazione, il comando `Sfoltisci` applica un downsampling voxel. Lo spazio viene suddiviso in celle cubiche di lato \(h\), dove \(h\) è il parametro voxel.

\[
V_{ijk} =
[ih,(i+1)h)
\times
[jh,(j+1)h)
\times
[kh,(k+1)h)
\]

I punti appartenenti alla stessa cella vengono rappresentati da un solo punto, tipicamente il baricentro o un campione della cella. L’effetto è:

- diminuzione del numero di punti;
- riduzione di rumore locale e densità non uniforme;
- minore consumo di memoria;
- ricostruzione più rapida;
- perdita controllata di dettaglio geometrico.

Il valore voxel è espresso nelle stesse unità geometriche della nuvola. Un voxel maggiore produce una superficie più regolare e meno dettagliata; un voxel minore conserva più dettaglio ma rende più onerose e potenzialmente instabili le fasi successive.

## 4. Ricostruzione della superficie

Il programma espone tre tecniche di ricostruzione:

- `Poisson Surface`;
- `Ball Pivoting`;
- `Alpha Shape`.

### 4.1 Poisson Surface

È il metodo principale per ricostruire superfici continue da nuvole di punti orientate. Richiede punti e normali coerenti. Le normali definiscono un campo vettoriale \(V\); il problema viene formulato come ricerca di una funzione indicatrice \(\chi\) del solido:

\[
\Delta \chi = \nabla \cdot V
\]

La superficie viene poi estratta come isosuperficie di \(\chi\). Il parametro `Depth` controlla la profondità della struttura gerarchica spaziale, assimilabile a un octree:

- depth maggiore → celle più piccole, maggiore dettaglio, più triangoli e maggior costo;
- depth minore → ricostruzione più levigata, più robusta e meno dettagliata.

Il Poisson tende a produrre superfici chiuse anche quando i dati sono incompleti; questo può però introdurre superfici artificiali nelle zone non rilevate.

### 4.2 Ball Pivoting

Il Ball Pivoting Algorithm fa rotolare una sfera di raggio noto sui punti. Quando la sfera tocca tre punti compatibili, genera una faccia triangolare. È sensibile alla scelta del raggio, alla densità locale e alla qualità delle normali. Può conservare dettagli locali meglio del Poisson, ma genera più facilmente buchi in aree scarsamente campionate.

### 4.3 Alpha Shape

L’Alpha Shape parte da una triangolazione/tetraedrizzazione di Delaunay e conserva gli elementi compatibili con una soglia \(\alpha\). È utile per estrarre involucri geometrici controllati dalla scala del parametro alpha. Un valore piccolo segue maggiormente i dettagli; uno grande tende verso un inviluppo più convesso e semplice.

## 5. Ritopologia

Dopo la ricostruzione, il comando `Ritopologia` riceve un numero target di triangoli. La funzione riduce o ridistribuisce la discretizzazione superficiale per ottenere una mesh con complessità controllata.

L’obiettivo non è solo diminuire il numero di facce, ma migliorare la qualità della mesh:

- eliminare triangoli eccessivamente piccoli;
- ridurre l’irregolarità della densità triangolare;
- limitare elementi sottili o degeneri;
- rendere il modello più gestibile per riparazione, visualizzazione e tetraedrizzazione.

Dal punto di vista geometrico, una buona ritopologia cerca di conservare la forma globale minimizzando un errore di approssimazione, mentre impone un limite alla complessità della mesh.

## 6. Pulizia e riparazione topologica

Il programma mette a disposizione una sequenza di operazioni specifiche.

### Elimina Triangoli Degeneri

Rimuove facce con area nulla o quasi nulla. Per un triangolo con vertici \(a,b,c\), l’area è:

\[
A = \frac{1}{2}\left\|(b-a)\times(c-a)\right\|
\]

Se \(A \approx 0\), il triangolo è degenere. Questi elementi provocano instabilità nei calcoli di normali, intersezioni, smoothing e generazione volumetrica.

### Elimina Triangoli Sovrapposti

Rimuove facce duplicate, coincidenti o geometricamente sovrapposte. Le sovrapposizioni possono introdurre non-manifoldness, errori nel calcolo del volume e ambiguità tra interno ed esterno.

### Chiudi Fori (Rapido)

Individua i bordi aperti: spigoli appartenenti a una sola faccia. Un bordo interno di una mesh manifold chiusa deve essere condiviso da esattamente due triangoli. Gli spigoli con una sola incidenza formano loop di frontiera; il comando crea facce per chiuderli.

È una riparazione rapida, adatta a piccoli fori. Può risultare inadeguata per aperture grandi, topologie complesse o zone con auto-intersezioni.

### Riparazione Locale

Agisce sulle aree problematiche senza modificare inutilmente l’intera mesh. Tipicamente comporta identificazione delle componenti difettose, rimozione di facce non valide, ricostruzione di patch locali, saldatura di vertici e ricostruzione delle adiacenze.

### Riparazione Estrema

È un intervento più invasivo, da usare quando la riparazione locale non basta. Può comportare semplificazione, ricostruzione di porzioni più ampie o eliminazione di geometrie topologicamente ambigue. Migliora le probabilità di ottenere un volume valido, ma può alterare maggiormente la geometria originale.

### Pulisci Mesh

È una normalizzazione finale della mesh superficiale: rimozione di elementi inutilizzati, ricostruzione delle connettività, consolidamento dei vertici e aggiornamento delle strutture interne.

## 7. Stato `SOLIDO` e `APERTO`

L’area statistiche dell’applicazione riporta lo stato topologico della mesh. Lo stato `SOLIDO` indica che il programma considera la superficie idonea al trattamento volumetrico; `APERTO` segnala che esistono ancora discontinuità topologiche.

In termini tecnici, una mesh considerata solida dovrebbe soddisfare, almeno in larga parte, queste condizioni:

- assenza di bordi aperti;
- assenza di facce degeneri;
- assenza di componenti topologicamente ambigue;
- orientamento coerente delle normali;
- connettività utilizzabile per distinguere interno ed esterno;
- assenza o controllo delle auto-intersezioni.

`SOLIDO` non implica automaticamente che la mesh sia perfetta dal punto di vista meccanico o numerico: elementi troppo sottili, dettagli spurii, facce molto allungate o piccoli artefatti geometrici possono ancora influenzare negativamente la successiva discretizzazione FEM.

## 8. Ottimizzazione per Abaqus

Il comando `Ottimizza Mesh per Abaqus (Topologia Virt.)` prepara la mesh superficiale per il passaggio al dominio FEM. Il termine “topologia virtuale” indica un’operazione volta a ridurre o neutralizzare dettagli geometrici che causerebbero elementi volumetrici di scarsa qualità: micro-spigoli, facce piccole, discontinuità locali e caratteristiche geometriche superflue.

Questa fase può modificare la connettività della superficie. Per questo è tecnicamente possibile che una mesh inizialmente classificata `SOLIDO` venga poi indicata come `APERTO`: una semplificazione topologica può scoprire o generare difetti che richiedono nuova pulizia e riparazione.

L’ottimizzazione Abaqus va intesa come pre-processing della geometria e non come esecuzione di un’analisi strutturale: il programma genera il modello discretizzato, ma non definisce autonomamente materiali, vincoli, carichi, step di analisi o richieste di output del solver.

## 9. Generazione del volume tetraedrico

Il comando `Genera Volume Tetraedrico (C3D4)` trasforma la superficie chiusa in una mesh volumetrica tetraedrica. La presenza della libreria TetGen nel pacchetto conferma l’uso di una tecnologia dedicata alla tetraedrizzazione.

Un tetraedro lineare è definito da quattro nodi:

\[
T = (n_1,n_2,n_3,n_4)
\]

e occupa un volume:

\[
V_T = \frac{1}{6}
\left|
\det
\begin{bmatrix}
x_2-x_1 & x_3-x_1 & x_4-x_1 \\
y_2-y_1 & y_3-y_1 & y_4-y_1 \\
z_2-z_1 & z_3-z_1 & z_4-z_1
\end{bmatrix}
\right|
\]

La tetraedrizzazione richiede una superficie chiusa e coerente perché deve stabilire con certezza quali regioni dello spazio sono interne al solido.

L’elemento Abaqus `C3D4` è un elemento continuo tridimensionale tetraedrico lineare a quattro nodi. Ha interpolazione lineare e, in generale, è più robusto da generare rispetto a elementi esaedrici, ma può richiedere una densità di mesh elevata per rappresentare correttamente flessione, gradienti di tensione o geometrie sottili.

## 10. Output verificati

Il programma produce almeno:

- `.inp`: input deck Abaqus;
- `.vtk`: mesh volumetrica in formato VTK;
- file di mesh superficiale esportabili, inclusi STL secondo i comandi disponibili nell’interfaccia.

Il file prodotto localmente `mesh_volumetrica.inp` contiene:

```text
*HEADING
Abaqus DataFile Version 6.14
*NODE
...
*ELEMENT, TYPE=C3D4
...
```

Quindi l’output è un modello FEM volumetrico esplicito: coordinate nodali seguite dalla connettività dei tetraedri.

Il corrispondente `mesh_volumetrica.vtk` è un `UNSTRUCTURED_GRID` binario. Nell’artefatto presente sono dichiarati:

- 11.100 punti;
- 47.048 celle tetraedriche.

L’esportazione VTK e INP è scritta tramite meshio 5.3.5, versione inclusa nel pacchetto.

## 11. Sequenza operativa interna consigliata

1. Caricare la nuvola o la mesh sorgente.
2. Applicare lo sfoltimento voxel.
3. Ricostruire una superficie, preferibilmente con Poisson quando i dati sono densi e le normali sono affidabili.
4. Impostare il target di triangoli e ritopologizzare.
5. Rimuovere triangoli degeneri e sovrapposti.
6. Chiudere i fori.
7. Controllare lo stato topologico.
8. Applicare riparazione locale o estrema se necessario.
9. Pulire la mesh.
10. Ottimizzare la topologia per Abaqus.
11. Ripetere il controllo di solidità.
12. Generare il volume tetraedrico C3D4.
13. Esportare il modello FEM.

## 12. Limiti tecnici da comunicare a un’altra IA

- Il software non può recuperare informazione geometrica non presente nella nuvola: buchi, occlusioni e rumore possono essere solo interpolati o regolarizzati.
- La qualità della ricostruzione dipende da scala voxel, densità dei punti, qualità delle normali, parametro `Depth`, strategia di ritopologia e riparazioni applicate.
- La condizione `SOLIDO` è un requisito topologico per tetraedrizzare, non una garanzia di accuratezza geometrica o qualità meccanica del modello.
- I C3D4 sono elementi lineari: la qualità degli elementi e la convergenza FEM devono essere verificate in Abaqus tramite metriche, sensibilità alla densità di mesh e confronto dei risultati.
- I dettagli esatti degli algoritmi proprietari di ritopologia, riparazione locale/estrema e ottimizzazione Abaqus non sono esposti dal binario distribuito; ciò che è verificabile è l’interfaccia funzionale, gli output generati e le librerie geometriche incluse.