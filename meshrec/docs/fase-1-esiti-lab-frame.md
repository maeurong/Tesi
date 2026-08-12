# Fase 1 — Segmentazione automatica su lab_frame.pcd

- **Data di esecuzione:** 12-13 agosto 2026
- **File:** `Nuvole di punti/lab_frame.pcd`, 152 MB, 6.329.096 punti letti (nessuno scartato per coordinate non finite)
- **Scopo:** provare `segment_cloud(method="auto")` (Task 11) sulla scansione reale, che contiene pavimento, oggetti e piu pareti, non solo il muro d'interesse.

## Scala

Lettura con `scale=1.0`: ingombro `[2.759, 0.785, 2.0]` (unita non note). Un ambiente di
laboratorio ha dimensioni dell'ordine dei metri; un ingombro dell'ordine delle unita indica
che la nuvola e' gia' in metri. Rilanciata con `scale=1000`:

| Grandezza | Valore |
|---|---|
| `extent` [mm] | `[2759.0, 785.0, 2000.0]` |
| `spacing` (distanza media al vicino) | 1.192 mm |
| punti letti | 6.329.096 |

Nessun `expected_size` disponibile (non ho una misura indipendente del muro per la verifica
di scala): la scala e' stata dedotta solo dall'ordine di grandezza dell'ingombro, non
confermata contro un valore atteso.

## Prova 1: configurazione di default (`plane_max_count=4`, `cluster_index=0`)

Comando (solo step 1+2, non l'intera pipeline: la ricostruzione di superficie su 6M+ punti
non segmentati non e' lo scopo di questo task):

```python
points, load_metrics = io.load_cloud(InputConfig(path=..., scale=1000.0))
wall, metrics = segment.segment_cloud(points, SegmentConfig(method="auto"), load_metrics["spacing"])
```

Tempo: caricamento 9.5 s, segmentazione 82.8 s (single-thread, vedi sezione riproducibilita').

| Metrica | Valore |
|---|---|
| `outliers_removed` | 244.304 |
| `planes_found` | 4 |
| `plane_points` | `[612748, 450159, 440424, 359631]` |
| `plane_distance` (soglia RANSAC) | 3.577 mm |
| `residual_points` | 4.221.830 |
| `clusters_found` | 3.309 |
| `cluster_eps` | 4.769 mm |
| `noise_points` | 2.452.663 |
| `cluster_points` (cluster scelto, index 0) | 639.655 |
| `planarity_rms` | 3.84 mm |
| `thickness` | 41.85 mm |
| `normal` | `[0.004, -0.008, 1.0]` |

**Esito: fallito.** Il cluster piu numeroso del residuo (index 0, il default) e' piatto e
pulito (planarita' 3.84 mm) ma la sua normale e' quasi puramente lungo Z (`[0.004,-0.008,1.0]`):
e' una superficie **orizzontale**, non il muro. E' probabile che sia una porzione di pavimento
o di un piano di lavoro non catturata dalle prime 4 estrazioni RANSAC (che hanno gia' rimosso
pavimento e alcune pareti dominanti). Con i parametri di default, `segment_cloud(method="auto")`
non isola il muro.

## Prova 2: stessa segmentazione, cluster_index diversi

Senza rilanciare RANSAC da capo (il seme e' fisso: la lista `cluster_sizes` e' la stessa),
provati `cluster_index=1` e `cluster_index=2` sullo stesso residuo:

| `cluster_index` | punti | planarity_rms | thickness | normal | bbox (mm) |
|---|---|---|---|---|---|
| 0 (default) | 639.655 | 3.84 mm | 41.85 mm | `[0.004,-0.008,1.0]` (orizzontale) | — |
| **1** | **281.084** | **3.49 mm** | **24.21 mm** | **`[1.0,0.013,-0.002]` (verticale, normale ~X)** | x:[1862.5,1888.5] y:[-394.5,-232.5] z:[-206.5,1193.5] |
| 2 | 103.297 | 19.15 mm | 117.57 mm | `[0.968,0.249,0.006]` (verticale, ~X) | x:[4114.5,4237.5] y:[-403.5,-232.5] z:[5.5,644.5] |

**Esito: `cluster_index=1` isola un muro.** Normale quasi perfettamente lungo X (superficie
verticale), molto piatto (planarita' 3.49 mm), sottile (spessore 24.21 mm, coerente con
l'intonaco/la faccia di una parete in muratura), esteso 1400 mm in verticale (z, coerente con
un'altezza di parete) su una fetta stretta di 162 mm in y (probabilmente la porzione di muro
visibile dal punto di scansione, non l'intera parete). `cluster_index=2` e' un'altra superficie
verticale (probabilmente un'altra parete o un'altra porzione della stessa), ma meno pulita
(planarita' 19.15 mm, spessore 117.57 mm: piu' rumore o piu' superfici quasi complanari
fuse insieme dal DBSCAN).

**Conclusione:** sulla scansione reale, `method="auto"` con i soli default **non** isola il
muro; va accompagnato da una scelta esplicita di `cluster_index` (qui `1`), dedotta
ispezionando `cluster_sizes` e la normale dei candidati. Questo e' coerente con il
disegno del modulo: `SegmentConfig` non ha default "giusti" universali, il chiamante (script
di configurazione in Fase 1, clic nel viewport in Fase 3) sceglie il cluster.

## Riproducibilita'

Verificata, non dedotta, in tre condizioni separate:

1. **Sintetica, isolata:** `tests/test_segment.py::test_auto_mode_is_reproducible_across_runs`,
   12/12 lanci su `pytest tests/test_segment.py -v` in isolamento, tutti identici.
2. **Sintetica, con OpenMP gia' scaldato da un'altra libreria nello stesso processo:** con la
   sola `os.environ.setdefault("OMP_NUM_THREADS", "1")` (prima versione del fix), due lanci
   della stessa configurazione su `tests/test_pipeline.py` seguito da `tests/test_segment.py`
   nello stesso processo `pytest` davano risultati **diversi** (2 su 3 volte, un
   AssertionError su `np.array_equal`). Causa: `os.environ` letto da OpenMP solo alla prima
   region parallela del processo; se un'altra libreria l'ha gia' avviata con piu' thread,
   l'impostazione tardiva non ha effetto. Risolto forzando anche a runtime, subito prima di
   ogni chiamata a `segment_plane`, con `ctypes.CDLL("vcomp140.dll").omp_set_num_threads(1)`
   (vedi `core/segment.py`, funzione `_pin_openmp_to_one_thread`). Dopo il fix: `uv run pytest`
   sull'intera suite, 3 lanci consecutivi, `test_auto_mode_is_reproducible_across_runs` sempre
   passato (l'unico fallimento residuo e' `test_gmsh_backend.py`, non correlato: file di un
   altro agente, fallisce anche da solo, prima di qualunque modifica di questo task).
3. **Sulla scansione reale:** `segment_cloud` con `method="auto", cluster_index=1` lanciato
   due volte sugli stessi 6.329.096 punti caricati con `scale=1000`. Risultato identico bit
   per bit su tutte le metriche osservate: `cluster_points=281084` in entrambi i lanci,
   `planarity_rms=3.488325`, `thickness=24.207539`, `normal=(0.999919, 0.012621, -0.001717)`,
   stessi valori a 6 cifre decimali in entrambi i lanci.

## Nota sui tempi

Segmentazione a thread singolo (necessario per la riproducibilita', vedi sopra) su 6.3M
punti: ~83-93 s per chiamata a `segment_cloud`. Non e' stato un problema di tempi non
praticabili per lo scopo di questo task (verifica dei soli step 1-2), ma va tenuto presente
per la pipeline completa (Fase 1, altri task): con `method="auto"` su nuvole di questa
dimensione, la sola segmentazione costa piu' di un minuto.
