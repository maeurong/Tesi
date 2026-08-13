# Debito Fase 1: tolleranza dei set, orientazione, verifica di min_ratio

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chiudere tre voci di debito della Fase 1 di meshrec: la tolleranza dei set che lascia il modello praticamente non vincolato, la superficie riparata che può uscire rovesciata senza che nulla lo dica, e `min_ratio` che nessuna metrica verifica sul risultato.

**Architecture:** Tre interventi indipendenti su file disgiunti. Il compito 1 è una misura che si conclude con una decisione di progetto, non con codice: la regola che sostituisce l'euristica attuale non è deducibile a tavolino e va scelta sui dati delle due corse archiviate. I compiti 2 e 3 sono implementazioni dirette. Il compito 2 sposta la garanzia di orientazione allo step 6, dove la riparazione già promette una superficie chiusa. Il compito 3 aggiunge al maglio di volume la misura che `min_ratio` vincola, chiudendo la famiglia dei parametri impostati e mai verificati.

**Tech Stack:** Python 3.12, numpy, pydantic v2, pytest, tetgen 0.8.4, pymeshfix, open3d, meshio. Gestione con `uv`.

## Global Constraints

- Directory di lavoro: `C:\Users\mario\github\tesi\meshrec`. Ogni comando `uv run` va lanciato da lì, altrimenti l'ambiente non risolve `open3d` e `tetgen`.
- **Mai `git add -A`**: la radice del repository ha 1,1 GB non tracciati. Aggiungere sempre i singoli percorsi.
- `meshrec/runs/muro/` e `meshrec/runs/lab_crop/` sono **archivi**: si leggono e si copiano, non si scrive mai al loro interno. Ogni esperimento va in una directory nuova sotto `runs/`, che è ignorata da git.
- L'unico luogo dove un parametro di elaborazione ha un valore predefinito è `src/meshrec/core/config.py`. Le firme delle funzioni del core non portano predefiniti per i parametri di elaborazione; il test `tests/test_volume.py::test_no_processing_default_lives_in_the_signature` lo verifica.
- Commenti, docstring e messaggi di commit in italiano, senza lettere accentate nelle docstring del core (il resto del codice segue questa convenzione).
- Suite di riferimento: `uv run pytest -q`. Prima dell'intervento vale **113 passati, 6 deselezionati, 1 avviso**. L'avviso superstite è legittimo e viene da `test_an_exhausted_steiner_budget_is_reported_not_hidden`.
- Le unità di lavoro sono mm, N, MPa, tonnellata, secondo.
- Nessun agente esegue commit. Le modifiche restano nell'albero di lavoro; il coordinatore committa a lavoro rivisto.
- Nessun agente modifica `docs/fase-1-debito.md`: i tre compiti se lo contenderebbero. Ogni agente scrive i propri esiti nel file di rapporto indicato nel suo incarico, e il coordinatore li riversa nel documento di debito.

---

### Task 1: Quale regola sostituisce la tolleranza dei set

**Files:**
- Nessuna modifica al codice sorgente in questo compito.
- Create: `docs/fase-1-tolleranza-set.md`
- Script usa e getta: nella directory scratchpad indicata nell'incarico, non nel repository.

**Interfaces:**
- Consumes: `meshrec.core.abaqus.align_to_axes(nodes, reference=...)`, `meshrec.core.abaqus._boundary_nodes(tets)`, `meshrec.core.abaqus.set_tolerance(nodes, tets, factor)`, `meshrec.core.abaqus.build_node_sets(nodes, tolerance)`, `meshrec.core.quality.tet_volumes(nodes, tets)`.
- Produces: una raccomandazione scritta, con i numeri che la sostengono, che diventerà l'incarico di un compito successivo. Nessuna interfaccia di codice.

**Perché questo compito è una misura e non un'implementazione**

L'euristica attuale lega la tolleranza al volume medio dell'elemento. Il documento di debito la dichiara sbagliata in partenza e suggerisce come sostituto la spaziatura dei nodi di bordo, mediana 13,73 mm sul muro. Quel suggerimento **non regge**: con il fattore 0,5 darebbe una tolleranza di 6,87 mm contro i 31,95 mm attuali, cioè un `BASE` più piccolo di quello che già oggi è troppo piccolo. La selezione per direzione della normale, che è la scelta standard nei preprocessori, ha un difetto opposto: su `lab_frame`, che ha aperture, l'intradosso di un architrave ha normale verso il basso e finirebbe in `BASE` pur non poggiando a terra.

Nessuna delle due regole è scartabile o adottabile senza guardare i dati. Scegliere adesso ripeterebbe esattamente l'errore che ha prodotto l'euristica in vigore.

- [ ] **Step 1: Preparare i due modelli allineati**

Le corse archiviate contengono `wall_model.vtu`, che è **già allineato agli assi**: è l'uscita di `export_model`, dopo `align_to_axes`. Per la misura serve però anche la connettività dei tetraedri, che è nello stesso file.

Script (nella scratchpad, non nel repository):

```python
import json
from pathlib import Path

import meshio
import numpy as np

RADICE = Path(r"C:\Users\mario\github\tesi\meshrec")

for nome in ("muro", "lab_crop"):
    corsa = RADICE / "runs" / nome
    maglia = meshio.read(corsa / "wall_model.vtu")
    nodi = np.asarray(maglia.points, dtype=np.float64)
    tetraedri = np.asarray(maglia.cells_dict["tetra"], dtype=np.int64)
    metriche = json.loads((corsa / "metrics.json").read_text(encoding="utf-8"))
    print(nome, len(nodi), len(tetraedri))
    print("  tolleranza in vigore:", metriche["11_export"]["set_tolerance"])
    print("  set:", metriche["11_export"]["node_sets"])
    print("  estensione:", nodi.max(axis=0) - nodi.min(axis=0))
```

Atteso: `muro` riporta una tolleranza di circa 31,95 mm e un `BASE` di 4738 nodi; `lab_crop` riporta un `BASE` molto più piccolo del totale. Riporta i numeri esatti che leggi, non quelli citati qui.

- [ ] **Step 2: Misurare la forma della base, su entrambi i modelli**

Le domande a cui questo passo deve rispondere, con numeri:

1. **La base è piatta?** Prendi i nodi di bordo (`abaqus._boundary_nodes(tetraedri)`) la cui quota sta entro il 5% dell'altezza totale dal minimo. Riporta la distribuzione delle loro z: minimo, mediana, massimo, e i quantili 0,50/0,90/0,99. Se lo scarto fra il primo e il novantanovesimo percentile è di pochi millimetri la base è piatta e la tolleranza può essere piccola; se è di centimetri la base è ondulata e la tolleranza deve coprire l'ondulazione.
2. **Quanto vale la spaziatura dei nodi sul bordo?** Costruisci le facce di bordo dei tetraedri (le facce triangolari che appartengono a un solo tetraedro), prendine gli spigoli unici e riporta la mediana della loro lunghezza. Serve come unità di misura naturale per confrontare le altre grandezze.
3. **Quanto copre `BASE` al variare della tolleranza?** Per una decina di tolleranze coprenti almeno tre ordini di grandezza (per esempio da 1 mm a 200 mm, in scala logaritmica), riporta la cardinalità di `BASE` restituita da `abaqus.build_node_sets`. Cerchi un ginocchio: la tolleranza oltre la quale il conteggio smette di crescere in fretta è quella che ha appena finito di coprire la faccia, e oltre la quale comincia a risalire i fianchi.
4. **Quanti nodi ci si aspetta sulla faccia?** L'impronta della base vale `estensione_x * estensione_y`; con spaziatura `s` un singolo strato di nodi ne contiene circa `impronta / s^2`. Confronta questa stima con i conteggi del punto 3 e con il `BASE` in vigore.
5. **Su `lab_crop`, `BASE` è piccolo per la tolleranza o per la geometria?** Verifica se esiste una tolleranza che porta `BASE` a una frazione ragionevole della stima del punto 4 senza far esplodere `TOP`. Se non esiste, la scansione non ha una base piana e il problema non è la tolleranza: dillo esplicitamente, è un esito valido e importante.
6. **La selezione per normale funzionerebbe?** Per le facce di bordo, calcola la normale uscente e classificale secondo la componente dominante della normale (sei classi: ±x, ±y, ±z). Riporta, per la classe «verso il basso», la distribuzione delle quote dei suoi nodi. Se sta tutta a quota bassa la regola per normale è sana su questa geometria; se ha una coda a quote alte hai trovato gli intradossi ed è la controprova del difetto sospettato.

Per orientare la normale verso l'esterno: ogni faccia di bordo appartiene a un solo tetraedro, e il quarto nodo di quel tetraedro sta all'interno. La normale `cross(b - a, c - a)` va invertita se punta verso quel quarto nodo, cioè se il prodotto scalare con `quarto - a` è positivo.

- [ ] **Step 3: Scrivere il documento con la raccomandazione**

Crea `docs/fase-1-tolleranza-set.md` in italiano, con:

- Le tabelle dei numeri misurati, per entrambe le corse, con le unità.
- La risposta esplicita a ciascuna delle sei domande dello Step 2.
- **Una** regola raccomandata, dichiarata in forma di formula o algoritmo eseguibile, con il valore che assumerebbero `BASE` e gli altri cinque set sulle due corse sotto quella regola.
- Se dovesse restare un parametro configurabile, il suo valore predefinito proposto e la misura che lo giustifica, sullo stesso modello dell'argomento che ha fissato `tet.min_ratio` a 1,8 in `docs/fase-1-min-ratio.md`.
- Le regole considerate e scartate, con il numero che le ha scartate.
- Che cosa la regola raccomandata **non** risolve.

Non modificare alcun file sorgente. Non modificare `docs/fase-1-debito.md`.

- [ ] **Step 4: Rileggere il documento contro i numeri**

Rileggi ogni affermazione del documento e verifica che il numero che la sostiene sia nelle tabelle. Un'affermazione senza il proprio numero va tolta o misurata. In particolare, se la raccomandazione migliora `muro` e peggiora `lab_crop`, o viceversa, il documento deve dirlo in chiaro invece di riportare la media dei due.

---

### Task 2: La riparazione garantisce anche l'orientazione

**Files:**
- Modify: `src/meshrec/core/repair.py:162-172`
- Test: `tests/test_repair.py`

**Interfaces:**
- Consumes: `meshrec.core.quality.mesh_volume(vertices, faces) -> float`, già importata in `repair.py`; restituisce il volume racchiuso con segno positivo se le normali sono uscenti.
- Produces: `repair_surface` restituisce d'ora in poi una superficie con volume racchiuso positivo, e le sue metriche contengono la chiave `orientation_flipped: bool`.

**Il difetto**

La riparazione promette una superficie chiusa e la verifica con `is_watertight`, che conta gli spigoli: una mesh rovesciata è chiusa quanto una diritta, e supera il controllo. Su `lab_frame.pcd` la superficie riparata aveva volume racchiuso di −0,173 m³, cioè era rovesciata, con zero spigoli di avvolgimento incoerente su 639.900: globalmente invertita, localmente perfetta. `metrics["volume_after"]` conteneva già il numero negativo e nessuno lo guardava. È costato un giro completo di indagine, ed è la prima delle tre cause del fallimento di TetGen su quella scansione.

La correzione va alla radice: chi promette una superficie chiusa promette anche che sia orientata verso l'esterno, perché è ciò che lo step 9 richiede. Il rimedio è l'inversione dell'avvolgimento dei triangoli, che è esatta e non approssima nulla.

- [ ] **Step 1: Scrivere il test che fallisce**

In `tests/test_repair.py`, in coda al file:

```python
def test_repair_returns_an_outward_oriented_surface():
    """Una superficie chiusa ma rovesciata supera il controllo di chiusura.

    `is_watertight` conta gli spigoli: una mesh capovolta ne ha due per
    spigolo esattamente come una diritta. Su lab_frame.pcd la superficie
    riparata usciva con volume racchiuso di -0,173 m^3, e lo step 9 falliva
    tre cause piu' in la'. Chi promette una superficie chiusa deve promettere
    anche il verso, perche' e' quello che TetGen richiede.
    """
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    rovesciata = np.ascontiguousarray(faces[:, [0, 2, 1]])
    assert quality.mesh_volume(vertices, rovesciata) < 0.0

    v, f, metrics = repair.repair_surface(vertices, rovesciata, config.RepairConfig())

    assert quality.mesh_volume(v, f) > 0.0
    assert metrics["volume_after"] > 0.0
    assert metrics["orientation_flipped"] is True


def test_an_already_outward_surface_is_left_alone():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))

    _, _, metrics = repair.repair_surface(vertices, faces, config.RepairConfig())

    assert metrics["orientation_flipped"] is False
```

Verifica in testa a `tests/test_repair.py` che `numpy`, `synth`, `quality`, `config` e `repair` siano già importati; se manca `quality`, aggiungilo alla riga di importazione esistente da `meshrec.core`.

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_repair.py::test_repair_returns_an_outward_oriented_surface -v`
Atteso: FAIL con `KeyError: 'orientation_flipped'`.

Se invece fallisce prima, sull'asserzione `mesh_volume(v, f) > 0.0`, va bene lo stesso: significa che pymeshfix non raddrizza da sé, che è precisamente il punto. Se invece **passa** l'asserzione sul volume e fallisce solo sulla chiave, annotalo: vorrebbe dire che pymeshfix raddrizza già, e il compito si riduce a registrare il fatto. In quel caso misura su `runs/lab_crop/06_repaired.ply` quale sia il segno del volume prima di concludere, perché su quella superficie reale l'inversione era sopravvissuta alla riparazione.

- [ ] **Step 3: Implementare**

In `src/meshrec/core/repair.py`, sostituisci il blocco finale (attualmente dalla riga 168 alla 172):

```python
    metrics["watertight_after"] = is_watertight(f)
    metrics["volume_after"] = mesh_volume(v, f)
    metrics["vertices"] = int(len(v))
    metrics["triangles"] = int(len(f))
    return v, f, metrics
```

con:

```python
    # Una superficie chiusa puo' essere chiusa e rovesciata: `is_watertight`
    # conta gli spigoli e una mesh capovolta ne ha due per spigolo come una
    # diritta. Su lab_frame.pcd la superficie riparata usciva con volume
    # racchiuso di -0,173 m^3, avvolgimento coerente ovunque e globalmente
    # invertito, e lo step 9 falliva senza che nulla indicasse il verso. Chi
    # promette una superficie chiusa promette anche il verso, perche' e' cio'
    # che TetGen richiede in ingresso. L'inversione dell'avvolgimento e'
    # esatta: non approssima nulla e non sposta un solo vertice.
    flipped = mesh_volume(v, f) < 0.0
    if flipped:
        f = np.ascontiguousarray(f[:, [0, 2, 1]])

    metrics["watertight_after"] = is_watertight(f)
    metrics["orientation_flipped"] = flipped
    metrics["volume_after"] = mesh_volume(v, f)
    metrics["vertices"] = int(len(v))
    metrics["triangles"] = int(len(f))
    return v, f, metrics
```

- [ ] **Step 4: Eseguire i test del file**

Run: `uv run pytest tests/test_repair.py -v`
Atteso: tutti passati, compresi i due nuovi.

- [ ] **Step 5: Verificare sulla superficie reale che ha originato il difetto**

Questo passo è il vero collaudo: il caso sintetico dice che il codice fa quel che dice, la scansione dice che serviva.

```python
from pathlib import Path

import numpy as np
import open3d as o3d

from meshrec.core import config, quality, repair

percorso = Path(r"C:\Users\mario\github\tesi\meshrec\runs\lab_crop\05_surface.ply")
maglia = o3d.io.read_triangle_mesh(str(percorso))
vertici = np.asarray(maglia.vertices)
facce = np.asarray(maglia.triangles)

print("volume prima:", quality.mesh_volume(vertici, facce))
v, f, metriche = repair.repair_surface(vertici, facce, config.RepairConfig())
print("capovolta:", metriche["orientation_flipped"])
print("volume dopo:", metriche["volume_after"])
```

Atteso: `volume dopo` positivo. Riporta i tre numeri nel rapporto. Se `05_surface.ply` non esiste nell'archivio, usa `06_repaired.ply` e dichiara nel rapporto che hai misurato il volume della superficie già riparata invece di rieseguire la riparazione.

- [ ] **Step 6: Eseguire la suite intera**

Run: `uv run pytest -q`
Atteso: tutti passati. Il conteggio sale di due rispetto ai 113 di partenza.

Se un test di `tests/test_pipeline.py` o `tests/test_abaqus.py` fallisce, fermati e riportalo senza aggiustarlo: significa che qualcosa a valle dipendeva dall'orientazione precedente, ed è un esito da discutere, non da mettere a posto di slancio.

- [ ] **Step 7: Scrivere il rapporto**

Nel file di rapporto indicato nell'incarico: le modifiche, i tre numeri dello Step 5, l'esito della suite, e una riga sul debito che questo **non** chiude — lo step 8 (semplificazione) gira dopo la riparazione e nessuno rivalida ciò che potrebbe rompere.

---

### Task 3: `min_ratio` verificato sul risultato

**Files:**
- Modify: `src/meshrec/core/quality.py` (nuova funzione dopo `tet_aspect_ratios`, riga 119; nuova voce in `volume_metrics`, righe 164-175)
- Modify: `src/meshrec/core/volume.py` (nuova classe di avviso vicino a `IneffectiveVolumeLimitWarning`, riga 23; nuovo controllo e nuova metrica in `tetrahedralize_with_metrics`, righe 112-191)
- Test: `tests/test_quality.py`, `tests/test_volume.py`

**Interfaces:**
- Consumes: `meshrec.core.quality.tet_volumes(nodes, tets) -> np.ndarray`, `meshrec.core.quality._FACE_PAIRS` (le sei coppie di indici su quattro, che valgono anche come spigoli del tetraedro), `meshrec.core.quality._distribution(values) -> dict`.
- Produces: `meshrec.core.quality.radius_edge_ratios(nodes, tets) -> np.ndarray`; la chiave `radius_edge_ratio` nel dizionario di `volume_metrics`; `meshrec.core.volume.UnmetQualityConstraintWarning`; le chiavi `radius_edge_ratio_max` e `radius_edge_ratio_p99` nelle metriche di `tetrahedralize_with_metrics`.

**Il difetto**

Dei parametri di `TetConfig` che vincolano il risultato, due sono verificati sul maglio prodotto — `max_steiner_points` tramite il conteggio dei punti aggiunti, `max_volume` tramite `largest_element_volume` — e uno no. `min_ratio` è il rapporto raggio-spigolo massimo ammesso, ed è esattamente la grandezza che nessuna metrica misura. Finora tre parametri di libreria sono stati trovati impostati e inerti, tutti e tre per caso e nessuno da un controllo che li cercasse: `maxvolume` senza `fixedvolume`, `steinerleft` al predefinito, `max_volume` sotto `nobisect`. Questo compito chiude la famiglia.

Il rapporto raggio-spigolo di un tetraedro è il raggio della sfera circoscritta diviso la lunghezza dello spigolo più corto. Vale `sqrt(6)/4 = 0,6124` per il tetraedro regolare e cresce sugli elementi mal condizionati. È la grandezza che TetGen limita con `minratio`.

- [ ] **Step 1: Scrivere il test della nuova misura**

In `tests/test_quality.py`, in coda al file:

```python
def test_radius_edge_ratio_of_the_regular_tetrahedron():
    """Il tetraedro regolare vale sqrt(6)/4: e' il minimo possibile."""
    nodi = np.array(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ]
    )
    tetraedri = np.array([[0, 1, 2, 3]])

    rapporti = quality.radius_edge_ratios(nodi, tetraedri)

    assert rapporti == pytest.approx([np.sqrt(6.0) / 4.0], rel=1e-9)


def test_radius_edge_ratio_grows_on_a_flattened_tetrahedron():
    """Uno schiacciato ha rapporto alto: e' la grandezza che min_ratio limita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.001]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert quality.radius_edge_ratios(nodi, tetraedri)[0] > 10.0


def test_a_degenerate_tetrahedron_is_infinite_not_a_crash():
    """Quattro punti complanari: nessuna sfera circoscritta finita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert not np.isfinite(quality.radius_edge_ratios(nodi, tetraedri)[0])
```

- [ ] **Step 2: Eseguire e verificare che fallisca**

Run: `uv run pytest tests/test_quality.py -k radius_edge -v`
Atteso: FAIL con `AttributeError: module 'meshrec.core.quality' has no attribute 'radius_edge_ratios'`.

- [ ] **Step 3: Implementare la misura**

In `src/meshrec/core/quality.py`, subito dopo `tet_aspect_ratios` (che termina alla riga 119):

```python
def radius_edge_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Raggio della sfera circoscritta diviso lo spigolo piu corto.

    E' la grandezza che TetGen limita con `minratio`: vale sqrt(6)/4 = 0,6124
    per il tetraedro regolare e cresce sugli elementi mal condizionati. Serve a
    verificare sul maglio prodotto un vincolo che finora era solo richiesto: dei
    parametri di TetConfig, `max_steiner_points` e `max_volume` sono controllati
    sul risultato, `min_ratio` no.

    Il centro della sfera circoscritta si ottiene risolvendo il sistema lineare
    che impone uguale distanza dai quattro vertici. Su un tetraedro degenere la
    matrice e singolare: il risultato e' infinito e non un'eccezione, cosi la
    metrica resta calcolabile su un maglio che contiene qualche elemento piatto.
    """
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a = n[t[:, 0]]
    spigoli = np.stack([n[t[:, i]] - a for i in (1, 2, 3)], axis=1)

    # 2 (p - a) . d = |p - a|^2 per ciascuno dei tre vertici restanti, con d il
    # centro riferito ad a.
    matrice = 2.0 * spigoli
    termine = np.einsum("ijk,ijk->ij", spigoli, spigoli)

    determinante = np.linalg.det(matrice)
    regolare = np.abs(determinante) > 0.0
    centri = np.zeros((len(t), 3), dtype=np.float64)
    if regolare.any():
        centri[regolare] = np.linalg.solve(matrice[regolare], termine[regolare])
    raggio = np.linalg.norm(centri, axis=1)

    piu_corto = np.min(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in _FACE_PAIRS], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        rapporto = raggio / piu_corto
    return np.where(regolare & (piu_corto > 0.0), rapporto, np.inf)
```

- [ ] **Step 4: Eseguire i test della misura**

Run: `uv run pytest tests/test_quality.py -k radius_edge -v`
Atteso: PASS, tutti e tre.

- [ ] **Step 5: Esporre la misura nelle metriche dello step 10**

In `src/meshrec/core/quality.py`, in `volume_metrics`, aggiungi la voce dopo `aspect_ratio`:

```python
        "aspect_ratio": _distribution(tet_aspect_ratios(nodes, tets)),
        "radius_edge_ratio": _distribution(radius_edge_ratios(nodes, tets)),
    }
```

Aggiorna la docstring di `volume_metrics` di conseguenza: da
`"""Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi."""` a
`"""Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi, raggio-spigolo."""`.

Run: `uv run pytest tests/test_quality.py -q`
Atteso: tutti passati.

- [ ] **Step 6: Misurare sul reale prima di scegliere la soglia dell'avviso**

Questo passo decide un numero e va eseguito prima di scriverlo. La domanda: di quanto il maglio prodotto supera il `min_ratio` richiesto, in una corsa perfettamente sana?

Il precedente da imitare è la soglia di `IneffectiveVolumeLimitWarning`: la prima versione scattava sull'uguaglianza e suonava a ogni corsa regolare, perché per TetGen `maxvolume` è un obiettivo con uno scarto di routine del 10%. È stata ritarata a un fattore 2 con un commento che spiega perché un avviso che suona sempre non viene letto quando conta. La stessa disciplina vale qui.

```python
from pathlib import Path

import meshio
import numpy as np

from meshrec.core import quality

for nome in ("muro", "lab_crop"):
    maglia = meshio.read(Path(r"C:\Users\mario\github\tesi\meshrec\runs") / nome / "09_volume.vtu")
    nodi = np.asarray(maglia.points, dtype=np.float64)
    tetraedri = np.asarray(maglia.cells_dict["tetra"], dtype=np.int64)
    rapporti = quality.radius_edge_ratios(nodi, tetraedri)
    finiti = rapporti[np.isfinite(rapporti)]
    print(nome, "non finiti:", int(len(rapporti) - len(finiti)))
    print("  mediana", np.median(finiti), "p99", np.quantile(finiti, 0.99), "max", finiti.max())
```

Il `min_ratio` di quelle corse è 1,8: leggilo da `config.yaml` della corsa invece di darlo per scontato. Aggiungi al maglio del cubo di prova (`synth.box_mesh` tetraedrizzato con `min_ratio=1.8`) la stessa misura, perché la soglia deve stare quieta anche lì.

Scegli il fattore moltiplicativo minimo che lascia silenziose tutte e tre le misure con un margine ragionevole, e annota nel rapporto i numeri che lo giustificano. Usa il **novantanovesimo percentile** e non il massimo come grandezza sorvegliata: un singolo elemento degenere ai bordi non è la stessa cosa di un vincolo disatteso ovunque, e il massimo è infinito appena c'è un elemento piatto.

- [ ] **Step 7: Scrivere il test dell'avviso**

In `tests/test_volume.py`, in coda al file. Sostituisci `FATTORE` con il numero scelto allo Step 6 e cita nella docstring i valori misurati.

```python
def test_the_quality_constraint_is_checked_on_the_result_not_only_requested():
    """`min_ratio` chiede un tetto al rapporto raggio-spigolo: qui si verifica.

    Dei parametri di TetConfig, `max_steiner_points` e `max_volume` erano
    controllati sul maglio prodotto e `min_ratio` no. Tre parametri di libreria
    sono gia' stati trovati impostati e inerti, tutti per caso: questo chiude la
    famiglia. La soglia e' calibrata sulle corse reali (vedi il commento nel
    codice), non sull'uguaglianza, perche' un avviso che suona a ogni corsa
    regolare non viene letto quando conta.
    """
    vertices, faces = synth.box_mesh(SIZE)

    _, _, metrics = volume.tetrahedralize_with_metrics(
        vertices, faces, config.TetConfig(max_volume=20_000.0)
    )

    assert metrics["radius_edge_ratio_p99"] < FATTORE * config.TetConfig().min_ratio
    assert metrics["radius_edge_ratio_max"] >= metrics["radius_edge_ratio_p99"]


def test_a_result_that_misses_the_quality_constraint_is_reported(monkeypatch):
    """Un maglio che disattende il vincolo non deve passare in silenzio."""
    vertices, faces = synth.box_mesh(SIZE)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=50_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    monkeypatch.setattr(
        quality, "radius_edge_ratios", lambda *args: np.full(len(tets), 100.0)
    )
    monkeypatch.setattr(volume, "tetrahedralize", lambda *args, **kwargs: (nodes, tets))

    with pytest.warns(volume.UnmetQualityConstraintWarning):
        volume.tetrahedralize_with_metrics(vertices, faces, config.TetConfig())
```

Perché la sostituzione con `monkeypatch` e non un maglio davvero cattivo: fabbricare un maglio che superi il vincolo richiederebbe di sconfiggere TetGen, che è precisamente ciò che il vincolo impedisce. Si sostituisce la misura per esercitare il ramo dell'avviso, come già fa `test_inverted_elements_are_a_blocking_error` con la tetraedrizzazione. La sostituzione deve avvenire sul nome che `volume.py` risolve a tempo di chiamata: se `volume.py` importa `radius_edge_ratios` con `from meshrec.core.quality import ...`, sostituisci `volume.radius_edge_ratios` invece di `quality.radius_edge_ratios`, e adegua il test a come hai scritto l'importazione.

Verifica che `quality` e `numpy` siano importati in `tests/test_volume.py`: `quality` lo è già, `numpy` come `np` pure.

- [ ] **Step 8: Eseguire e verificare che falliscano**

Run: `uv run pytest tests/test_volume.py -k quality_constraint -v`
Atteso: FAIL con `AttributeError: module 'meshrec.core.volume' has no attribute 'UnmetQualityConstraintWarning'`.

- [ ] **Step 9: Implementare l'avviso**

In `src/meshrec/core/volume.py`, dopo `IneffectiveVolumeLimitWarning` (riga 23-24):

```python
class UnmetQualityConstraintWarning(UserWarning):
    """Il maglio prodotto non rispetta il `min_ratio` richiesto: il vincolo e' rimasto lettera morta."""
```

Aggiungi `radius_edge_ratios` all'importazione da `meshrec.core.quality` in testa al file.

In `tetrahedralize_with_metrics`, dopo il blocco di `IneffectiveVolumeLimitWarning` (che finisce alla riga 176) e prima della costruzione di `metrics`:

```python
    # `min_ratio` era il solo parametro di TetConfig che nessuna metrica
    # verificava sul risultato: `max_steiner_points` e' controllato dal
    # conteggio dei punti aggiunti, `max_volume` da largest_element_volume, e
    # il rapporto raggio-spigolo da nulla. Tre parametri di libreria sono gia'
    # stati trovati impostati e inerti, tutti per caso: questa chiude la
    # famiglia.
    #
    # Si sorveglia il novantanovesimo percentile e non il massimo: un elemento
    # degenere isolato al bordo non e' un vincolo disatteso, e il massimo
    # diventa infinito appena ne compare uno. La soglia e' un fattore
    # <FATTORE> e non l'uguaglianza perche' <numeri misurati allo Step 6>.
    rapporti = radius_edge_ratios(nodes, tets)
    finiti = rapporti[np.isfinite(rapporti)]
    p99 = float(np.quantile(finiti, 0.99)) if len(finiti) else float("inf")
    massimo = float(rapporti.max()) if len(rapporti) else 0.0
    if p99 > <FATTORE> * cfg.min_ratio:
        warnings.warn(
            f"il rapporto raggio-spigolo al novantanovesimo percentile vale {p99:.4g} "
            f"contro il min_ratio di {cfg.min_ratio:.4g} richiesto: il vincolo di "
            "qualita non e' stato applicato al maglio prodotto.",
            UnmetQualityConstraintWarning,
            stacklevel=2,
        )
```

e nelle metriche, accanto a `largest_element_volume`:

```python
        "radius_edge_ratio_p99": p99,
        "radius_edge_ratio_max": massimo,
```

Sostituisci `<FATTORE>` con il numero scelto allo Step 6 e il testo fra parentesi angolari nel commento con i numeri che lo giustificano. Un commento che lasci le parentesi angolari è un difetto.

- [ ] **Step 10: Eseguire i test del file**

Run: `uv run pytest tests/test_volume.py -v`
Atteso: tutti passati.

- [ ] **Step 11: Eseguire la suite intera**

Run: `uv run pytest -q`
Atteso: tutti passati, con il solo avviso legittimo di `test_an_exhausted_steiner_budget_is_reported_not_hidden`. Se compare un `UnmetQualityConstraintWarning` in una corsa regolare, la soglia dello Step 6 è troppo stretta: ritarala e annota il perché, non silenziare il test.

- [ ] **Step 12: Scrivere il rapporto**

Nel file di rapporto indicato nell'incarico: le modifiche, la tabella delle misure dello Step 6 con i valori per `muro`, `lab_crop` e il cubo, la soglia scelta e il margine che le resta, l'esito della suite.

---

## Ordine e parallelismo

I compiti 2 e 3 toccano file disgiunti (`repair.py` contro `quality.py` e `volume.py`; `test_repair.py` contro `test_quality.py` e `test_volume.py`) e possono procedere insieme. Il compito 1 non tocca alcun sorgente e non confligge con nessuno.

Il compito 1 si conclude con una raccomandazione, non con codice: l'implementazione della nuova regola per la tolleranza dei set è un compito successivo, che verrà scritto sul suo esito e toccherà `src/meshrec/core/abaqus.py`, `src/meshrec/core/config.py` e `tests/test_abaqus.py`.

Nota per chi eseguirà il compito 3 e il compito 2 insieme: entrambi eseguono `uv run pytest -q` sull'intero albero. Se la suite intera fallisce su un file che non è il tuo, verifica con `git status` se un altro intervento è in corso prima di concludere che l'hai rotta tu.
