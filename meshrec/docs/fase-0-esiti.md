# Fase 0 — Esiti delle verifiche di fattibilità

- **Data di esecuzione:** 12 agosto 2026
- **Ambiente:** Windows 11, Python 3.12.10, uv 0.12.3

## Dipendenze obbligatorie

| Pacchetto | Versione | Esito | Note |
|---|---|---|---|
| numpy | 2.5.2 | OK | nessuna deviazione |
| scipy | 1.18.0 | OK | nessuna deviazione |
| open3d | 0.19.0 | OK | wheel disponibile per Python 3.12 Windows, nessun ripiego necessario |
| tetgen | 0.8.4 | OK, con due scostamenti di API | vedi "Nomi di API osservati" |
| meshio | 5.3.5 | OK | legge senza errori l'`.inp` scritto da `abaqus.write_inp`, incluse le parole chiave `*SOLID SECTION`/`*STEP` non riconosciute (ignorate, non fatali) |
| pydantic | 2.13.4 | OK | usato per il modello `Material` |

## Dipendenze in valutazione

| Pacchetto | Versione | Esito | Decisione |
|---|---|---|---|
| pymeshfix | 0.18.1 | PASS | adottato per la riparazione garantita della superficie, nessun ripiego su Open3D |
| wildmeshing (fTetWild) | non installabile su win_amd64 | SKIP | ripiego TetGen + PyMeshFix con guardia di superficie chiusa mantenuta in Fase 1 |
| pymeshlab | 2025.7.post1 | PASS | adottato per remeshing isotropo ed errore geometrico (distanza di Hausdorff), nessun ripiego su decimazione Open3D + KD-tree SciPy |
| gmsh | 4.15.2 | PASS | **generatore alternativo opzionale** a TetGen, con ottimizzatore proprio (`optimize("Netgen")`) che agisce sulla mesh generata da Gmsh stesso. Non è un ottimizzatore post-mesh di TetGen: non riceve né migliora una mesh di TetGen. Validato in Fase 1 sulla geometria sintetica, a parità di elementi (vedi [`fase-1-esiti.md`](fase-1-esiti.md)); resta fuori dal percorso principale della pipeline |
| CalculiX | 2.22 | PASS | adottato per il batch libero di Fase 5. Il PASS originale e' di Windows x86-64. **Riverificato su macOS arm64 il 18/08/2026**, stessa versione 2.22 installata da conda-forge: la colonna incastrata sotto peso proprio rientra entro il 20% della soluzione in forma chiusa, quindi l'esito vale ora su entrambe le piattaforme |

## Nomi di API osservati

Scostamenti fra le API previste dal piano e quelle effettivamente esposte dalle
versioni installate, riscontrati durante l'esecuzione delle verifiche e
vincolanti per l'implementazione della Fase 1:

- **tetgen 0.8.4**
  - `tetrahedralize()` restituisce **quattro** valori (`node, elem, attributes, triface_markers`), non due come atteso. Va destrutturato con `nodes, tets, *_ = generator.tetrahedralize(**options)`.
  - `maxvolume` passato per nome è **inerte**: con `max_volume=200_000.0` o `max_volume=20_000.0` il numero di tetraedri prodotti resta identico (verificato con più valori: `None, 200000, 20000, 2000, 500`), e non viene sollevato alcun errore o warning. Il parametro funziona solo se accompagnato da `fixedvolume=True` nella stessa chiamata nominale. L'alternativa letterale del piano (switches testuali, es. `pq1.1a{max_volume}`) funziona ma disabilita gli altri parametri nominali e produce output verboso su stdout dalla libreria nativa TetGen; `fixedvolume=True` risolve lo stesso problema con un diff minimo e senza rumore su stdout.

- **pymeshfix 0.18.1**
  - Gli attributi del risultato riparato sono `.points` e `.faces`, non `.v` e `.f` come indicato nel piano originale.

- **pymeshlab 2025.7.post1**
  - `filter_list()` è una **funzione di modulo** (`pymeshlab.filter_list()`), non un metodo di `MeshSet` (`mesh_set.filter_list()` solleva `AttributeError`). `MeshSet.apply_filter(filter_name, **kwargs)` resta invariato.
  - Filtro di remeshing isotropo: `meshing_isotropic_explicit_remeshing`.
  - Filtro di distanza di Hausdorff: `get_hausdorff_distance`.
  - Tipo percentuale: `pymeshlab.PercentageValue` (non `pymeshlab.Percentage`).

## Conseguenze sulla Fase 1

- Riparazione della superficie: **PyMeshFix**, usando `fixer.points`/`fixer.faces` (non `.v`/`.f`).
- Tetraedrizzazione: **TetGen**, guardia di chiusura (superficie manifold prima della tetraedrizzazione) **mantenuta**; `tetrahedralize()` va destrutturato a 4 valori e `maxvolume` richiede `fixedvolume=True` per avere effetto.
- Errore geometrico: **PyMeshLab** (`get_hausdorff_distance`), enumerazione filtri via `pymeshlab.filter_list()` a livello di modulo.
- Ottimizzazione della qualità: **Gmsh** (`optimize("Netgen")`), opzionale — non richiesto per far girare la pipeline principale. Sulla geometria sintetica di prova la qualità minima è passata da 0,037787 a 0,423365, con il numero di elementi da 540 a 775 (+43,5%). Su point cloud reali (rumorose, non watertight in origine) la riclassificazione delle superfici da STL resta il passaggio più a rischio — da validare in Fase 1 su dati reali, non solo sintetici.

  > **Correzione apportata in Fase 1.** Questa misura è stata riletta alla fonte (`tests/feasibility/test_gmsh.py`) e va intesa per quello che è, perché così com'era formulata si prestava a due letture sbagliate. Primo: **non è un confronto fra Gmsh e TetGen**. I due valori sono la qualità minima della mesh di Gmsh *prima* e *dopo* la sua stessa chiamata a `optimize("Netgen")`; TetGen non compare nella prova, e anche il passaggio da 540 a 775 elementi è interno a Gmsh, prodotto dagli split e collapse dell'ottimizzatore. Secondo: **la grandezza non è l'angolo diedro minimo** ma il valore restituito da `gmsh.model.mesh.getElementQualities`, un indice adimensionale in [0, 1] proprio di Gmsh, non confrontabile con le metriche di `core/quality.py` e da non leggere come gradi. Il confronto vero fra i due generatori, a parità di elementi, è in [`fase-1-esiti.md`](fase-1-esiti.md): a rapporto di elementi 0,947 l'angolo diedro minimo passa da 2,302° (TetGen) a 25,504° (Gmsh), quindi il guadagno esiste, ma sta nella coda e non nella mediana.
- Solutore per il batch: **CalculiX**, verificato installabile e funzionante (dettagli sotto). OpenSees valutato e scartato come secondo solutore di verifica (vedi sezione dedicata).

## Verifica CalculiX

**Installazione.** CalculiX non era disponibile come pacchetto Python installabile via `uv`; è un eseguibile esterno. Installato estraendo PrePoMax v2.5.0 da `prepomax.fs.um.si` (Università di Maribor) in `C:\Users\mario\tools\PrePoMax v2.5.0`. Il binario risolutore è `Solver\ccx_dynamic.exe`; è stato creato un collegamento fisico `ccx.exe` nella stessa cartella (il test cerca l'eseguibile con nome `ccx`), e la cartella è stata aggiunta al PATH utente.

**Prova.** Colonna 100 × 100 × 400 mm incastrata alla base, sotto peso proprio, 133 nodi, 394 tetraedri. `ccx` è terminato con codice di uscita 0.

**Confronto con la soluzione analitica.** Spostamento verticale medio in sommità:

- Numerico (CalculiX): **−9,291402 · 10⁻⁴ mm**
- Analitico (ρ g L² / 2E): **−9,417600 · 10⁻⁴ mm**
- Scarto: **1,34%**, con il modello numerico più rigido dell'analitico — atteso, per l'uso di tetraedri lineari grossolani con base incastrata (la condizione di incastro impedisce la contrazione trasversale per effetto Poisson vicino alla base, effetto che il modello 1D analitico non cattura).

**Come rieseguire la verifica.** Richiede `ccx` raggiungibile nel `PATH`:

```bash
cd meshrec
uv run pytest tests/feasibility/test_calculix.py -v -m feasibility
```

## Decisione: `punch_holes` e adiacenza dei triangoli rimossi

`synth.punch_holes(faces, remove=(0, 6))` rimuove i triangoli di indice 0 e 6
di `_BOX_FACES`, che condividono lo spigolo (1, 2): sono adiacenti, quindi il
default apre **un foro unico** a cavallo delle due facce, con **4** spigoli di
bordo — non due fori separati da tre spigoli ciascuno. Decisione presa perche'
riflette il caso di danno piu comune sulla muratura reale (lacuna continua),
non due lesioni isolate; `tests/test_quality.py` verifica il valore 4.

## Alternativa valutata e scartata: OpenSees

OpenSees (`openseespy`) è stato valutato come secondo solutore di verifica
indipendente da CalculiX, e scartato. Motivi:

1. Con un'analisi elastica lineare, due solutori diversi convergono banalmente
   sullo stesso risultato (entrambi risolvono lo stesso sistema lineare):
   un confronto fra i due verificherebbe la correttezza dei *solutori*, non
   quella del *modello* — mentre il rischio principale del progetto è di
   natura geometrica (qualità della mesh, chiusura della superficie),
   non numerica.
2. OpenSees non legge il formato `.inp`: richiederebbe un secondo writer del
   deck, dedicato, mentre CalculiX riusa lo stesso deck già prodotto per
   Abaqus (Task 4), a costo di implementazione nullo.

La decisione si riapre se l'ambito della tesi passa ad analisi non lineari o
dinamiche (danno della muratura, azione sismica, model updating), dove un
confronto fra solutori con formulazioni diverse avrebbe contenuto informativo
reale.
