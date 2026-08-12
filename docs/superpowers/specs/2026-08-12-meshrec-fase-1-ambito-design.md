# MeshRec — Fase 1: ambito di esecuzione e decisioni

- **Data:** 2026-08-12
- **Spec di riferimento:** `2026-08-12-meshreconstructor-architettura-design.md`,
  `2026-08-12-meshreconstructor-fase-0-1-design.md`
- **Esiti su cui si appoggia:** `meshrec/docs/fase-0-esiti.md`
- **Natura del documento:** non riscrive le due spec precedenti. Registra soltanto le decisioni
  che quelle spec lasciavano aperte e le deviazioni deliberate rispetto a quanto vi è prescritto.

---

## 1. Decisioni prese

### 1.1 Struttura dei moduli: `src/meshrec/core/`

La spec di architettura prescrive `meshrec/core/*.py`; l'albero uscito dalla Fase 0 ha
`src/meshrec/*.py` piatto. Vince la spec: i moduli esistenti vengono spostati in
`src/meshrec/core/`.

```
meshrec/
  src/meshrec/
    __init__.py
    core/
      config.py io.py segment.py surface.py repair.py
      volume.py quality.py abaqus.py pipeline.py synth.py
    cli.py
  tests/
```

Motivo: è il momento più economico in cui la migrazione possa avvenire, perché nessun modulo del
core ne importa un altro. Dopo la Fase 1 i moduli sono dieci, e in Fase 3 arrivano `app/server.py`
e `app/worker.py`: un albero piatto li mescolerebbe alla geometria pura, cancellando il confine
`ui → app → core` che la spec di architettura pone come vincolo di dipendenza.

`synth.py` appartiene al core: il test di integrazione della Fase 1 lo usa per generare il
parallelepipedo a soluzione nota. La riga di comando vive in `src/meshrec/cli.py`, fuori dal core,
perché il core deve restare utilizzabile da script senza passare da essa.

### 1.2 Ripresa dell'esecuzione al posto della cache a impronta

La spec della Fase 1 prescrive una cache indicizzata sull'impronta della configurazione cumulativa.
In Fase 1 non viene realizzata. Al suo posto la riga di comando espone `--from-step N`, che riparte
dagli artefatti numerati già presenti sul disco della cartella di elaborazione.

Motivo: gli artefatti sono già scritti numerati, quindi riprendere da uno step costa poche righe e
nessuna struttura dati. La cache a impronta ha valore quando molte configurazioni vengono eseguite
in successione automatica, cioè in Fase 2 con il motore di sweep, che è anche il punto in cui la
sua correttezza viene messa alla prova. Anticiparla in Fase 1 significherebbe introdurre subito la
categoria di errore più insidiosa che possa avere — riusare in silenzio un artefatto ottenuto con
parametri diversi — senza alcun carico di lavoro che la giustifichi.

Conseguenza esplicita: `--from-step N` si fida dell'operatore. Non verifica che gli artefatti a
monte siano stati prodotti con la configurazione corrente. Il comportamento va documentato nella
guida della riga di comando.

### 1.3 `report.html` rinviato alla Fase 2

La riproducibilità richiesta dai criteri di accettazione della Fase 1 è coperta da `config.yaml`
serializzato e da `metrics.json`. Il report stampabile serve quando esiste una tabella
sperimentale da presentare, cioè con il registro degli esperimenti della Fase 2, che ne
riscriverebbe comunque la struttura.

### 1.4 Segmentazione in due tempi

Lo step 2 viene diviso. Entra subito la parte che serve a far girare la catena completa: rimozione
di outlier statistici e ritaglio a box definito da coordinate in configurazione. La parte
automatica — estrazione iterativa di piani con RANSAC, clustering DBSCAN, selezione del cluster —
è l'ultimo lavoro della fase.

Motivo: `muro_generato.ply` non richiede segmentazione, quindi un `.inp` completo end-to-end è
raggiungibile senza di essa. Scrivendo per ultima la parte automatica, la si scrive avendo davanti
il comportamento reale di `lab_frame.pcd` invece che ipotesi sulla sua struttura. È lo step con
l'incertezza più alta della fase e non deve stare sul percorso critico.

### 1.5 Richieste di output del deck in forma moderna

Il writer della Fase 0 emette `*NODE FILE` e `*EL FILE`, che in Abaqus producono un file `.fil` e
non un `.odb`. La Fase 1 le sostituisce con `*OUTPUT, FIELD` più `*NODE OUTPUT` / `*ELEMENT
OUTPUT`. CalculiX 2.22 accetta entrambe le forme, quindi la verifica esistente non regredisce.

### 1.6 Verifica del deck senza Abaqus

Abaqus non è disponibile sulla macchina di sviluppo. La Fase 1 si chiude validando il deck con
`meshio` in lettura e con CalculiX in soluzione. Abaqus Learning Edition non è un ripiego
utilizzabile: il suo limite di 1000 nodi è inferiore di ordini di grandezza alle mesh in gioco.

Il controllo dei dati con Abaqus resta quindi un rischio dichiarato e non chiuso della Fase 1, da
eseguire alla prima occasione di accesso a una licenza. È l'unico criterio di accettazione della
Fase 1 che non viene soddisfatto in fase.

### 1.7 `quality.py` resta un modulo solo

Metriche degli elementi ed errore geometrico rispetto alla nuvola sorgente convivono in
`core/quality.py`, come prescritto dalla spec di architettura, benché abbiano dipendenze diverse
(numpy puro le prime, PyMeshLab il secondo). Non viene introdotto un modulo separato solo per
consentire a due agenti di lavorare in parallelo: l'organizzazione del lavoro non è un motivo
valido per deviare dall'architettura.

## 2. Debito della Fase 0 assorbito

| Debito | Dove viene chiuso |
|---|---|
| Guardia di superficie chiusa mai invocata | `core/volume.py`, all'ingresso di `tetrahedralize` |
| Angolo diedro minimo e rapporto d'aspetto mancanti | `core/quality.py` |
| Unità dichiarate ma non imposte | `core/io.py`, fattore di scala allo step 1 |
| Richieste di output legacy | `core/abaqus.py`, vedi 1.5 |
| Gmsh adottato ma non validato su dati reali | Ultimo lavoro della fase, a parità di numero di elementi |
| `maxvolume` inerte senza `fixedvolume=True` | `core/volume.py` |
| `pymeshfix` e `pymeshlab` dipendenze non importate da alcun modulo | `core/repair.py` e `core/quality.py` |

## 3. Ordine di esecuzione

Un solo proprietario per file all'interno di ciascuna onda, quindi nessun conflitto fra lavori
paralleli.

| Onda | Contenuto | File | Parallelismo |
|---|---|---|---|
| 0 | Spostamento in `core/` e configurazione pydantic completa di tutti i gruppi di parametri | `core/config.py` | seriale |
| 1 | Caricamento e fattore di scala · metriche di qualità ed errore geometrico · riparazione con PyMeshFix · tetraedrizzazione con guardia | `core/io.py` · `core/quality.py` · `core/repair.py` · `core/volume.py` | quattro lavori |
| 2 | Ricostruzione della superficie · outlier e ritaglio a box · allineamento, set, deck, esportazione `.vtu` | `core/surface.py` · `core/segment.py` · `core/abaqus.py` | tre lavori |
| 3 | Sequenza degli step, ripresa da step, riga di comando, test di integrazione | `core/pipeline.py`, `src/meshrec/cli.py`, `tests/test_pipeline.py` | seriale |
| 4 | Segmentazione automatica su `lab_frame.pcd` · validazione di Gmsh e esecuzione su `muro_generato.ply` | `core/segment.py` · documentazione | due lavori |

L'onda 0 è seriale perché `core/config.py` è il modulo che ogni altro importa. L'onda 3 è seriale
perché `core/pipeline.py` cuce insieme tutto ciò che le onde precedenti hanno prodotto.

## 4. Fuori dalla Fase 1

Cache a impronta della configurazione, `report.html`, motore di sweep e fronte di Pareto,
interfaccia web, prior geometrico "muro", banco sintetico con rumore e occlusioni. Restano alle
fasi che la spec di architettura assegna loro.

## 5. Criteri di accettazione, come modificati

Rispetto ai criteri della spec della Fase 0-1:

- Il test di integrazione passa. **Invariato.**
- Le metriche di errore geometrico rispetto alla nuvola sorgente sono calcolate e riportate.
  **Invariato.**
- Su `lab_frame.pcd` la segmentazione isola il muro e la pipeline arriva in fondo. **Invariato.**
- La stessa configurazione, rieseguita, produce lo stesso risultato. **Invariato.**
- Su `muro_generato.ply` la pipeline produce un `.inp` che Abaqus accetta al controllo dei dati.
  **Sostituito** per la durata della fase: il deck viene riletto da `meshio` e risolto da CalculiX
  senza errori. Il controllo dei dati con Abaqus resta dovuto, vedi 1.6.
