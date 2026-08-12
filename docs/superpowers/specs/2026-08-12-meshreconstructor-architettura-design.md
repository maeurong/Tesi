# MeshRec — Architettura e ambito

- **Data:** 2026-08-12
- **Stato:** design approvato in sessione di brainstorming
- **Sostituisce:** `MeshReconstructorPro` (eseguibile fornito dai tutor, senza sorgente)
- **Collocazione codice:** `meshrec/` dentro il repository `Tesi`

---

## 1. Contesto

Il materiale di partenza è quello condiviso dai tutor per la tesi:

- `MeshReconstructorPro/` — applicazione desktop Windows distribuita come eseguibile PyInstaller,
  senza codice sorgente. Il bundle contiene PySide6, Open3D, VTK/PyVista, TetGen 0.8.3,
  meshio 5.3.5, numpy/scipy, più dipendenze inutilizzate (dash, flask, plotly, matplotlib,
  IPython, nbformat).
- `Nuvole di punti/lab_frame.pcd` (152 MB) — scansione reale di un ambiente di laboratorio:
  contiene pavimento, oggetti e più pareti, quindi richiede segmentazione.
- `Nuvole di punti/muro_generato.ply` (31 MB) — muro sintetico generato al calcolatore:
  geometria nota, quindi utilizzabile come verità di riferimento per la validazione.
- `Cartella di lavoro Abaqus/prova_1.inp`, `prova_2.inp` — output del programma attuale:
  circa 70.000 righe contenenti solo `*NODE` e `*ELEMENT, TYPE=C3D4`, senza set, materiali,
  vincoli, carichi o step di analisi.
- `Articoli/` — 17 pubblicazioni su ricostruzione FEM da nuvole di punti, valutazione del danno,
  gemelli digitali e modellazione HBIM di murature.

### Limiti del programma attuale

1. Interfaccia grafica obbligatoria, nessuna esecuzione batch, parametri non salvati: un risultato
   non è riproducibile e quindi non è documentabile in tesi.
2. Nessuna metrica di qualità degli elementi (jacobiano, angolo diedro, elementi invertiti):
   lo stato `SOLIDO` è una condizione topologica, non una garanzia numerica.
3. Nessuna gestione esplicita di unità, scala e sistema di riferimento.
4. Nessun node set o element set: vincoli e carichi vanno applicati a mano su migliaia di nodi.
5. Nessuna misura dell'errore geometrico rispetto alla nuvola sorgente.
6. La ricostruzione di Poisson chiude le zone non rilevate creando superfici inventate, e nulla
   quantifica il fenomeno.
7. Le operazioni di riparazione ("locale", "estrema") sono opache, non deterministiche e non
   citabili in un lavoro scientifico.
8. Nessuna segmentazione: la scena reale non è trattabile senza pre-elaborazione esterna.

## 2. Obiettivo

Realizzare una pipeline riproducibile da nuvola di punti a modello FEM di muratura, con
applicazione grafica locale, e usarla come strumento del caso studio della tesi. Il contributo
è duplice: il metodo (pipeline documentata, parametrizzata e validata) e i risultati ottenuti
applicandolo.

## 3. Requisiti fissati

| Ambito | Decisione |
|---|---|
| Deliverable | Pipeline software più caso studio |
| Analisi FEM di riferimento | Elastica lineare statica |
| Interfaccia | Applicazione locale con interfaccia web, viewport 3D interattivo completo |
| Design dell'interfaccia | Affidato alla skill `impeccable`, a partire da `impeccable init` |
| Segmentazione | Inclusa nella pipeline (automatica assistita più ritaglio manuale) |
| Export Abaqus | Modello pronto all'analisi: set, materiale, vincoli, carichi, step, output |
| Distribuzione | Repository più `uv sync`; nessun eseguibile impacchettato |
| Unità | mm, N, MPa, tonnellata, secondo — dichiarate e imposte in un solo punto |

## 4. Architettura

Tre strati con dipendenze in una sola direzione: `ui → app → core`. Il core non conosce
l'interfaccia e resta utilizzabile da script.

```
meshrec/
  core/                 # geometria pura, nessuna dipendenza dall'interfaccia
    config.py           # modelli pydantic: unico luogo dove vive un parametro
    io.py               # lettura e scrittura nuvole e mesh
    segment.py          # RANSAC planare, DBSCAN, ritaglio
    surface.py          # downsample, normali, ricostruzione superficie
    repair.py           # riparazione topologica
    volume.py           # tetraedrizzazione
    quality.py          # metriche superficie e volume, errore rispetto alla sorgente
    abaqus.py           # scrittura .inp completo
    pipeline.py         # esecuzione degli step da config, con cache
    sweep.py            # motore multi-candidato e fronte di Pareto (Fase 2)
    wall.py             # prior geometrico "muro" e modo parametrico (Fase 4)
    bench.py            # generatore sintetico e batch solver (Fase 5)
  app/
    server.py           # FastAPI: endpoint per step, eventi di progresso, servizio interfaccia
    worker.py           # esecuzione degli step lunghi in processo separato
  ui/                   # HTML, CSS, JavaScript, viewport three.js
tests/
  test_pipeline.py
```

**Contratto degli step.** Ogni step del core ha la stessa firma concettuale: riceve un artefatto
in ingresso e i propri parametri, restituisce un artefatto in uscita e un dizionario di metriche.
Nessuno step conosce gli altri; la sequenza vive soltanto in `pipeline.py`.

**Stato su disco, non in memoria.** Ogni elaborazione è una cartella:

```
runs/<nome>/
  config.yaml           # parametri completi: va in appendice alla tesi
  artifacts/            # 01_cloud.ply, 02_segmented.ply, 03_surface.ply, ...
  metrics.json          # metriche di ogni step
  report.html           # riepilogo stampabile
  wall_model.inp
```

La pipeline mette in cache i risultati sull'impronta del config di ogni step: modificando un
parametro si rieseguono soltanto lo step interessato e quelli a valle. Gli step a valle di una
modifica sono marcati non validi ed evidenziati; un risultato ottenuto con parametri diversi non
viene mai riutilizzato in silenzio.

## 5. Decisioni tecniche rilevanti

**Allineamento agli assi prima dell'export.** La nuvola vive nel sistema arbitrario dello
scanner. Una rototraslazione derivata dai piani principali porta lo spessore lungo x, la
lunghezza lungo y, l'altezza lungo z, con base a z = 0. La trasformazione è salvata nei metadati
per riportare i risultati al sistema originale.

**Parametri derivati dai dati.** La spaziatura media dei punti, calcolata al caricamento, guida i
valori predefiniti di dimensione del voxel e dei raggi di Ball Pivoting, al posto di costanti
arbitrarie. I valori restano modificabili.

**Trimming per densità nel Poisson.** La ricostruzione di Poisson restituisce una densità per
vertice; scartando i vertici sotto soglia si eliminano le superfici generate dove non esistevano
dati. È il rimedio diretto al principale artefatto della pipeline attuale.

**Verifica di scala esplicita.** L'ingombro della nuvola va confrontato con le dimensioni reali
misurate del muro prima di procedere. Il fattore di scala è un parametro visibile, non un
valore implicito: un modello in unità errate produce tensioni sbagliate di ordini di grandezza
senza alcun segnale.

**Riparazione citabile.** Le operazioni opache dell'attuale sono sostituite da algoritmi
pubblicati (MeshFix tramite PyMeshFix; in alternativa tetraedrizzazione robusta con fTetWild),
con riferimenti bibliografici e comportamento deterministico.

**Selezione multi-obiettivo.** Fedeltà geometrica, numero di elementi e qualità degli elementi
sono obiettivi in conflitto. La selezione fra candidati avviene per dominanza di Pareto; i
candidati dominati vengono scartati automaticamente e non viene calcolato alcun punteggio pesato
con pesi arbitrari.

**Solver libero per il batch.** CalculiX legge il formato `.inp` di Abaqus e risolve statica
lineare con gli stessi elementi: consente di risolvere molti modelli in automatico senza
occupare una licenza Abaqus, che resta per le verifiche finali.

## 6. Fasi

| Fase | Contenuto | Dipende da |
|---|---|---|
| 0 | Verifica di fattibilità delle dipendenze, scheletro del repository, test sul cubo sintetico | — |
| 1 | Core della pipeline senza interfaccia, dall'ingresso all'`.inp` pronto all'analisi | 0 |
| 2 | Motore di sweep: multi-fidelità, parallelismo, fronte di Pareto, registro esperimenti, report | 1 |
| 3 | Interfaccia web completa: sistema di design `impeccable`, viewport three.js, galleria di curazione | 2 |
| 4 | Prior "muro": doppio piano, spessore, fuori piombo, modo parametrico, mesh esaedrica | 1 |
| 5 | Banco sintetico con rumore e occlusioni, CalculiX in batch, analisi di sensibilità | 1, 2 |

Ogni fase ha una propria spec di dettaglio e un proprio piano di implementazione. Dopo la Fase 1
il programma supera già quello attuale; dopo la Fase 2 esiste il metodo; dopo la Fase 3 esiste
l'applicazione da presentare.

### Fase 2 — motore di sweep

Genera N candidati da una griglia di parametri (dimensione voxel, metodo di ricostruzione,
profondità, soglia di trimming, target di triangoli, vincoli di qualità della tetraedrizzazione).
Lo sweep gira prima su nuvola fortemente decimata e riesegue a risoluzione piena solo i primi k
candidati. I candidati sono indipendenti e vengono eseguiti in parallelo su più processi. I
candidati dominati sono scartati automaticamente; resta il fronte di Pareto, presentato con
metriche e miniature. I candidati scartati conservano la propria riga di metriche nel registro
dell'esperimento, che costituisce la tabella sperimentale della tesi.

L'ottimizzazione bayesiana è esclusa: lo spazio dei parametri ha poche dimensioni con pochi
livelli sensati, la griglia lo copre ed è spiegabile. Resta come possibile evoluzione se lo
spazio dovesse crescere.

### Fase 4 — prior geometrico "muro"

Un muro è una lastra piana, e questa informazione a priori consente operazioni che una pipeline
generica non può fare: adattamento di due piani paralleli alle facce e quindi spessore misurato
con la sua dispersione; mappa di scostamento della faccia dal piano ideale, cioè fuori piombo e
rigonfiamento, che sono grandezze diagnostiche per la muratura; e un secondo modo di uscita come
solido parametrico regolare, che essendo estruso ammette una mesh esaedrica strutturata,
preferibile ai tetraedri lineari a parità di gradi di libertà. Con entrambi i modi disponibili
diventa possibile il confronto fra modello as-built e modello parametrico semplificato a parità
di nuvola e di analisi.

### Fase 5 — validazione e sensibilità

Il muro sintetico viene parametrizzato (dimensioni, fuori piombo, rigonfiamento) e campionato con
rumore gaussiano controllato e occlusioni artificiali, ottenendo un banco di prova con verità
nota su cui misurare la dipendenza dell'errore da rumore, densità e occlusione. Con il solver in
batch si misura infine quanto la risposta strutturale dipende dai parametri di ricostruzione:
è la domanda scientifica centrale del lavoro, perché stabilisce se la scelta dei parametri
geometrici sia ininfluente o determinante per il risultato strutturale.

## 7. Interfaccia (Fase 3)

Avvio con un comando; il server locale apre il browser. Utente singolo, nessuna autenticazione.

Layout a tre zone: a sinistra la pipeline come sequenza verticale di step con il rispettivo stato;
al centro il viewport 3D; a destra i parametri dello step corrente e le metriche del risultato.

Il viewport è realizzato in three.js e resta completo: nuvola decimata per il disegno con dati
integrali sul server, mesh triangolare, superficie di contorno del volume con piano di taglio,
mappe di colore della deviazione, box di ritaglio manipolabile e selezione dei cluster di
segmentazione con un clic.

Gli step lunghi girano in un processo separato con avanzamento e log in tempo reale e possibilità
di annullamento: l'interfaccia non si blocca mai.

Un comando genera `report.html` con parametri, metriche, istogrammi di qualità e viste catturate,
stampabile in PDF per l'appendice.

L'aspetto visivo — sistema di design, tipografia, colore, gerarchia, stati, micro-interazioni —
è definito dalla skill `impeccable` a partire da `impeccable init`. Questa spec fissa cosa deve
esserci e come si comporta, non che aspetto ha.

## 8. Export Abaqus

Set generati automaticamente con tolleranza derivata dalla dimensione media dell'elemento:
`BASE` (nodi alla quota minima), `TOP` (quota massima), `FACE_FRONT` e `FACE_BACK` (facce di
contorno con normale lungo ±x, definite come superfici di elemento e quindi caricabili a
pressione), `SIDE_LEFT` e `SIDE_RIGHT` (normale lungo ±y), `ALL_WALL` (element set completo).

Il file contiene nodi, elementi C3D4 (C3D10 opzionale), i set, la sezione solida, il materiale
elastico con densità, l'incastro alla base, uno step statico con carico gravitazionale e le
richieste di output di tensioni, deformazioni e spostamenti.

I valori di materiale predefiniti sono indicativi per muratura (E ≈ 1500 MPa, ν = 0,2,
ρ = 1800 kg/m³), modificabili e riportati in evidenza nel report perché vanno tarati sul
materiale reale del caso studio.

La scrittura del file è propria, non delegata a `meshio`: `meshio` scrive soltanto nodi ed
elementi, ed è il motivo per cui l'output attuale è privo di tutto il resto. `meshio` resta in
uso per i formati `.vtu` e `.vtk`.

Se Abaqus è disponibile nel percorso di sistema, un comando esegue il controllo dei dati sul file
generato e ne riporta l'esito.

## 9. Robustezza

Gli ingressi sono un confine di fiducia: file illeggibili, nuvole vuote, coordinate non finite
(frequenti nei file `.pcd` reali) vengono filtrati e conteggiati, mai ignorati in silenzio. Un
limite configurabile sul numero di punti evita la saturazione della memoria, con avviso esplicito.

Il fallimento di un processo di calcolo viene catturato e riportato con il log, lasciando intatti
gli artefatti degli step precedenti.

Quando la tetraedrizzazione richiede un ingresso chiuso, la condizione viene verificata prima e
l'operazione non parte se non è soddisfatta, indicando quale metrica è fuori tolleranza. Con una
tetraedrizzazione robusta su ingressi difettosi questa verifica diventa superflua e viene rimossa
insieme al vincolo.

## 10. Dipendenze

In ingresso: `numpy`, `scipy`, `open3d`, `tetgen`, `meshio`, `pydantic`, `fastapi`, `uvicorn`;
in valutazione nella Fase 0: `pymeshfix`, `wildmeshing` (fTetWild), `pymeshlab`, `gmsh`,
CalculiX.

Escluse rispetto al bundle attuale: PySide6, VTK, PyVista, dash, flask, plotly, matplotlib,
IPython, nbformat. Gli istogrammi del report sono SVG generati direttamente: una libreria di
grafici per pochi istogrammi non si giustifica.

Ogni dipendenza in valutazione ha un ripiego dichiarato: TetGen più PyMeshFix al posto di
fTetWild, Open3D puro al posto di pymeshlab, Abaqus al posto di CalculiX.

## 11. Verifica

Un test di integrazione, `tests/test_pipeline.py`, genera un parallelepipedo campionato
analiticamente con volume noto in forma chiusa, lo fa attraversare l'intera catena e verifica
superficie chiusa, volume entro tolleranza, assenza di tetraedri invertiti, rileggibilità
dell'`.inp`, set `BASE` non vuoto e coerenza dei conteggi di nodi ed elementi. È il controllo
minimo che fallisce se un qualsiasi step si rompe. Le fasi successive aggiungono un test per il
proprio nucleo logico, non una suite per funzione.

## 12. Fuori scope

Materiali non lineari, analisi dinamiche o modali, edifici o assemblaggi di più muri,
rilevamento automatico di fessure, impacchettamento in eseguibile, esecuzione remota e
multiutente. Si valutano solo se emerge una necessità concreta.

### Alternative valutate e scartate

**OpenSees come secondo solutore di verifica.** Con un'analisi elastica lineare due solutori
indipendenti concordano a meno della precisione macchina, perché implementano lo stesso
tetraedro standard: l'accordo verificherebbe i solutori, non il modello, mentre il rischio
di questo lavoro è geometrico. In più OpenSees non legge il formato `.inp` e richiederebbe
un secondo writer da scrivere e mantenere, mentre CalculiX riusa lo stesso identico deck
destinato ad Abaqus, che è la verifica incrociata a costo quasi nullo.

La decisione si riapre se l'ambito si sposta ad analisi non lineari o dinamiche — danno nella
muratura, azione sismica, aggiornamento del modello da vibrazioni ambientali: lì i due solutori
non concordano banalmente e il confronto acquista contenuto.

## 13. Rischi

| Rischio | Effetto | Mitigazione |
|---|---|---|
| fTetWild non installabile su Windows con Python 3.12 | Resta il vincolo di superficie chiusa prima della tetraedrizzazione | Ripiego su TetGen più PyMeshFix, deciso in Fase 0 |
| CalculiX non compatibile con l'`.inp` generato | Niente batch senza licenza Abaqus | Prova su modello ridotto in Fase 0; ripiego su Abaqus con meno esecuzioni |
| Il viewport three.js assorbe più lavoro della pipeline | Fasi successive in ritardo | Fase 3 isolata: le fasi 4 e 5 non ne dipendono e possono procedere |
| La nuvola reale è troppo rumorosa per la segmentazione automatica | Segmentazione manuale obbligata | Il ritaglio interattivo è comunque previsto come alternativa |
