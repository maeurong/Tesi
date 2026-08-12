# MeshRec — Fasi 0 e 1: fondamenta e core della pipeline

- **Data:** 2026-08-12
- **Spec di riferimento:** `2026-08-12-meshreconstructor-architettura-design.md`
- **Ambito:** verifica di fattibilità, scheletro del repository, pipeline completa senza interfaccia

---

## Fase 0 — Verifica di fattibilità e scheletro

### Obiettivo

Chiudere le incognite che cambierebbero la forma della Fase 1, e lasciare un repository
funzionante con un test che gira.

### Verifiche, con criterio di esito

Ogni verifica è un piccolo script eseguibile su un cubo o su un modello ridotto, non una lettura
di documentazione.

| Verifica | Criterio di successo | Ripiego se fallisce |
|---|---|---|
| `pymeshfix` su Windows con Python 3.12 | Ripara una mesh con fori e restituisce una superficie chiusa manifold | Riparazione con Open3D più chiusura fori propria |
| `wildmeshing` (fTetWild) | Installa e tetraedrizza una mesh volutamente difettosa (fori, auto-intersezioni) | TetGen più PyMeshFix, con vincolo di superficie chiusa |
| `pymeshlab` | Esegue remeshing isotropo e calcolo della distanza di Hausdorff | Decimazione quadric di Open3D più distanza calcolata con KD-tree |
| `gmsh` | Ottimizza una mesh tetraedrica e ne migliora l'angolo diedro minimo | Nessuna ottimizzazione post-mesh, si agisce sui parametri di TetGen |
| CalculiX | Risolve un `.inp` generato da noi su un cubo incastrato sotto peso proprio, con spostamento confrontabile con la soluzione analitica | Solo Abaqus, con un numero ridotto di esecuzioni in batch |

L'esito di ogni verifica va annotato nel documento di fase, con versione del pacchetto: è la base
di scelte che verranno citate in tesi.

### Scheletro

Repository `meshrec/` dentro `Tesi`, ambiente gestito con `uv`, struttura dei moduli come da spec
di architettura, con i file del core presenti anche se in parte vuoti. `tests/test_pipeline.py`
esiste e gira, inizialmente sul solo percorso già implementato.

### Criteri di accettazione della Fase 0

`uv sync` completa su una macchina pulita; il test gira; ogni verifica ha esito e decisione
registrata; le dipendenze definitive della Fase 1 sono fissate.

---

## Fase 1 — Core della pipeline

### Obiettivo

Da nuvola di punti a file `.inp` pronto all'analisi, eseguibile da script, senza interfaccia
grafica. Al termine della fase il programma supera già quello dei tutor su tutti i punti deboli
elencati nella spec di architettura.

### Configurazione

`core/config.py` definisce con pydantic l'intera configurazione di un'elaborazione. È l'unico
luogo in cui un parametro ha un valore predefinito: nessun default vive altrove, né in interfaccia
né negli script. La configurazione è serializzata in `config.yaml` e ricaricabile senza perdita.

Gruppi di parametri: ingresso e scala; segmentazione; riduzione e normali; ricostruzione;
riparazione; semplificazione; tetraedrizzazione; materiale e analisi; esecuzione (percorsi, cache,
limiti).

### Step

Ogni step riceve un artefatto e i propri parametri, restituisce un artefatto e le proprie
metriche. La sequenza vive in `pipeline.py`; nessuno step conosce gli altri.

**1. Caricamento** — formati `.pcd`, `.ply`, `.xyz`. Filtra coordinate non finite conteggiandole.
Calcola spaziatura media dei punti (distanza media al vicino più prossimo su un campione),
ingombro e numero di punti. Applica il fattore di scala verso il sistema di unità di lavoro
(mm, N, MPa, tonnellata, secondo) e riporta l'ingombro convertito, da confrontare con le
dimensioni reali misurate del muro. Limite configurabile sul numero di punti, con avviso.

*Metriche:* punti letti, punti scartati, spaziatura media, ingombro, fattore di scala applicato.

**2. Segmentazione** — rimozione di outlier statistici; estrazione iterativa di piani con RANSAC
per separare pavimento e pareti; clustering DBSCAN sul residuo; selezione del cluster o del piano
corrispondente al muro, per indice o tramite ritaglio a box definito da coordinate. In Fase 1 la
selezione è da configurazione; in Fase 3 diventa un clic nel viewport.

*Metriche:* numero di piani estratti, numero di cluster, punti del cluster scelto, planarità
(scarto quadratico medio dal piano adattato), spessore stimato.

**3. Riduzione a voxel** — dimensione predefinita pari al doppio della spaziatura media,
sovrascrivibile.

*Metriche:* punti residui, riduzione percentuale, spaziatura media risultante.

**4. Normali** — stima con vicinato KNN e orientamento coerente tramite propagazione su albero di
supporto minimo; se disponibile il punto di vista del sensore, orientamento verso di esso;
in alternativa orientamento verso l'esterno rispetto al piano adattato del muro.

*Metriche:* raggio o numero di vicini usato, percentuale di normali a orientamento incerto.

**5. Ricostruzione della superficie** — metodi disponibili: Poisson (predefinito), Ball Pivoting,
Alpha Shape. Per Poisson sono esposti profondità, peso dei punti, scala e **soglia di trimming per
densità**, che elimina i vertici generati dove i dati erano assenti. Per Ball Pivoting i raggi
derivano dalla spaziatura media.

*Metriche:* vertici e triangoli, vertici rimossi dal trimming, superficie chiusa sì o no,
componenti connesse.

**6. Riparazione** — sequenza deterministica e registrata: conservazione della sola componente
connessa maggiore; rimozione di triangoli degeneri e duplicati; saldatura dei vertici coincidenti;
chiusura dei fori la cui area è sotto una soglia, con segnalazione esplicita di quelli oltre
soglia, che non vengono chiusi in silenzio; orientamento coerente delle normali; verifica delle
auto-intersezioni. La chiusura garantita si appoggia a MeshFix, oppure viene resa non necessaria
da una tetraedrizzazione robusta, secondo l'esito della Fase 0.

*Metriche:* entità rimosse per categoria, fori chiusi e fori lasciati aperti con relativa area,
esito manifold, auto-intersezioni residue.

**7. Qualità della superficie** — chiusura, componenti, bordi aperti, auto-intersezioni, area,
volume racchiuso, distribuzione dell'aspect ratio dei triangoli, ed errore geometrico
bidirezionale rispetto alla nuvola sorgente segmentata, riportato come scarto quadratico medio,
mediana e valore di Hausdorff.

**8. Semplificazione (opzionale)** — decimazione a un numero obiettivo di triangoli oppure
remeshing isotropo, seguita da smoothing di Taubin. Lo smoothing laplaciano è escluso perché
contrae il volume e assottiglia il muro.

*Metriche:* triangoli prima e dopo, variazione del volume, errore rispetto alla superficie
precedente.

**9. Tetraedrizzazione** — con vincoli di qualità espliciti (rapporto raggio-spigolo, volume
massimo dell'elemento). Elemento predefinito C3D4, C3D10 selezionabile. Se disponibile,
ottimizzazione post-mesh.

*Metriche:* nodi, tetraedri, tempo di calcolo.

**10. Qualità del volume** — elementi con jacobiano negativo o volume nullo, angolo diedro minimo,
aspect ratio, distribuzione dei volumi, con istogrammi. La presenza di elementi invertiti è un
errore bloccante, non un avviso.

**11. Allineamento ed export** — rototraslazione ai piani principali con spessore lungo x,
lunghezza lungo y, altezza lungo z e base a z = 0, con la trasformazione salvata nei metadati;
generazione dei set `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`,
`ALL_WALL` con tolleranza derivata dalla dimensione media dell'elemento; scrittura dell'`.inp`
con sezione solida, materiale elastico con densità, incastro alla base, step statico con carico
gravitazionale e richieste di output. Esportazione anche in `.vtu` tramite `meshio`.

*Metriche:* nodi per ciascun set, volume totale, massa totale, dimensioni finali del modello.

### Esecuzione e cache

`pipeline.py` esegue la sequenza, scrive gli artefatti numerati e aggiorna `metrics.json`.
La cache è indicizzata sull'impronta della configurazione cumulativa fino allo step: uno step
viene saltato solo se la sua impronta e quelle a monte coincidono. Al variare di un parametro
gli step a valle risultano non validi e vengono rieseguiti.

### Report

`report.html` con configurazione usata, metriche di ogni step, istogrammi in SVG generati
direttamente, e le viste renderizzate degli artefatti principali. Il documento è autosufficiente
e stampabile.

### Interfaccia da riga di comando

Minima e non definitiva: esecuzione della pipeline su un file di configurazione, e comando di
generazione del report. Serve a lavorare durante le Fasi 1 e 2; l'interfaccia vera arriva in
Fase 3.

### Verifica

`tests/test_pipeline.py` costruisce un parallelepipedo campionando analiticamente le sue facce
con densità nota, esegue l'intera pipeline e verifica: superficie chiusa; volume entro tolleranza
rispetto al valore esatto; nessun tetraedro invertito; `.inp` rileggibile con conteggi di nodi ed
elementi coerenti; set `BASE` non vuoto e contenente i soli nodi alla quota minima; massa totale
coerente con densità e volume.

Verifica manuale a corredo, da eseguire una volta e annotare: pipeline completa su
`muro_generato.ply` e su `lab_frame.pcd`, con esito della segmentazione e metriche di errore
registrate.

### Criteri di accettazione della Fase 1

Il test di integrazione passa. Su `muro_generato.ply` la pipeline produce un `.inp` che Abaqus
accetta al controllo dei dati. Le metriche di errore geometrico rispetto alla nuvola sorgente
sono calcolate e riportate. Su `lab_frame.pcd` la segmentazione isola il muro e la pipeline
arriva in fondo. La stessa configurazione, rieseguita, produce lo stesso risultato.
