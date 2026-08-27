# Inventario delle grandezze calcolate, e di cosa le verifica

Misurato il 26/08/2026 su `main` a `a07071a`, **albero di lavoro sporco**
(`quality.py`, `volume.py`, `abaqus.py`, `config.py` modificati): le righe citate
sono quelle dell'albero di lavoro, non di HEAD.

Raccolta test: `uv run pytest --collect-only -q` → **1019 su 1035 raccolti, 16
deselezionati** (`tests/feasibility/`, escluso da `pyproject.toml:47` via
`addopts = "-m 'not feasibility'"`).

Legenda verdetto: **O** = oracolo indipendente (valore analitico noto, invariante,
o libreria terza) · **R** = solo regressione autoreferenziale · **N** = non
coperta.

---

## Superficie

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `mesh_volume` | `quality.py:27` | V = Σ_f (a·(b×c))/6 | mm³, + se normali uscenti | scatola esatta 100·40·200 — `test_quality.py:33`, `:78` | **O** |
| area superficie | `quality.py:322` | A = Σ_f ‖(b−a)×(c−a)‖/2 | mm², ≥0 | 2(100·40+100·200+40·200) analitico — `test_quality.py:79` | **O** |
| `is_watertight` | `quality.py:21` | ∀e: n(e)=2 | bool | scatola chiusa / bucata — `test_quality.py:23,36` | **O** |
| `boundary_edges` | `quality.py:15` | {e : n(e)=1} | conteggio | 4 spigoli dopo un buco — `test_quality.py:85` | **O** |
| `triangle_aspect_ratios` | `quality.py:175` | AR = L_max/(2√3·r), r = 2A/Σℓ | adim., ≥1 | equilatero = 1 — `test_quality.py:64`; sliver >100 — `:70` | **O** |

## Volume — tetraedri

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `tet_volumes` | `quality.py:38` | V = (b−a)·((c−a)×(d−a))/6 | mm³, **con segno**, <0 = invertito | Σ = volume esatto scatola su output TetGen — `test_volume.py:31` | **O** |
| `inverted_tets` | `quality.py:46` | {i : V_i ≤ 0} | indici | tet a orientazione scambiata — `test_quality.py:95` | **O**, ma **cieco su NaN** (§4) |
| `min_dihedral_angles` | `quality.py:208` | θ = min_{i<j} [180° − arccos(n̂_i·n̂_j)] | gradi, ∈[0,180] | tet regolare = arccos(1/3) = 70,5288° — `test_quality.py:52` | **O** |
| `tet_aspect_ratios` | `quality.py:222` | AR = L_max/(2√6·r), r = 3V/ΣA_f | adim., ≥1, ∞ se degenere | **nessuna chiamata in nessun test** | **N** |
| `radius_edge_ratios` | `quality.py:240` | ρ = R_circ/L_min | adim., ≥√6/4 | tet regolare = √6/4 (rel 1e-9) — `test_quality.py:153`; schiacciato >10 — `:162`; complanare → inf — `:170` | **O** |
| `fraction_over_ratio` | `quality.py:328` | #{ρ finito > limite}/#{ρ finito}; 1.0 se vuoto | ∈[0,1] | 0.0/1.0 costruiti — `test_quality.py:288-292` | **O** |
| `radius_edge_ratio_p99` | `volume.py:230` | q₀,₉₉ dei ρ finiti; `None` se vuoto | adim. | solo `< min_ratio` su mesh sana — `test_volume.py:197` | **R** |

## Volume — esaedri

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `hex_volumes` | `quality.py:60` | V = Σ_{k=1..6} V_tet (ventaglio da 0 attorno alla diagonale 0–6) | mm³, con segno | cubo unitario = 1 — `test_quality.py:499`; rovesciato <0 — `:503` | **O** |
| `scaled_jacobian` | `quality.py:83` | SJ = min_{c=0..7} det(e₁,e₂,e₃)/(‖e₁‖‖e₂‖‖e₃‖); 0 se il prodotto è nullo | adim., ≤1 | cubo = 1 — `test_quality.py:536`; angolo a 45° = 1/√2 — `:554` | **O**, ma **formula ≠ Verdict** (§2) |
| `element_volumes` | `quality.py:155` | dispatch sul numero di colonne: 8→hex, 4 o 10→tet dei primi 4 | mm³ | concorda con `tet_volumes`/`hex_volumes` — `test_quality.py:500,523` | **R** (tautologia) |

## Errore geometrico, deviazione, spessore

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `geometric_error` | `quality.py:366` | delega a PyMeshLab `get_hausdorff_distance` nei due versi; `hausdorff` = max(max_c2m, max_m2c) | mm, ≥0 | nuvola campionata sulla mesh → piccolo (`:98`); traslata → cresce (`:111`); coerenza con `vertex_deviation` rel 1e-5 (`:440`) | **O** |
| `vertex_deviation` | `quality.py:442` | d_v = min_{p∈nuvola} ‖v − p‖ (cKDTree, k=1) | mm, ≥0 | 0 esatto sui punti + 0,25 noto fuori — `:310,311`; scostamento 3.0 — `:320`; RMS = 0,5 analitico — `:366` | **O** |
| `thickness` | `quality.py:476` | PCA 3×3 → asse di `ptp` minimo; istogramma a passo `bin_width`; s = c_upper − c_lower; `bimodal` ⟺ mean(valle) < ½·min(picchi) | mm, >0 | lastra a spessore noto 176 mm ±3 — `:187`; solido pieno → non valido — `:191` | **O** |
| `extent` (in `thickness`) | `quality.py:527` | ptp lungo l'autovettore minimo | mm | nessuna asserzione sul valore | **R** |
| `_distribution` | `quality.py:286` | min/median/mean/max sui soli finiti + `non_finite` | come il campo | `None` invece di NaN, mediana 2.0 — `:134,136` | **O** |

## Ingresso e scala

| grandezza | dove | formula | unità | oracolo | v |
|---|---|---|---|---|---|
| `mean_spacing` | `io.py:64` | mean(d₂) su campione casuale, d₂ = 2° vicino kd-tree | mm | 8 test in `test_io.py` | — |
| `scale` | `io.py:85` | p ← p · cfg.scale | fattore adim. → mm | `size_check` contro `expected_size` (`io.py:91-102`) — controllo, non test | **O** se l'utente dichiara le misure |
| `extent`/`bbox` | `io.py:86-88` | max − min per asse | mm | `test_io.py` | **R** |

## Deck e set di nodi (`abaqus.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `align_to_axes` | `:956` | ẑ ≡ [0,0,1]; x̂ = fix_sign(autovettore di ptp minimo della PCA 2D orizzontale); ŷ = ẑ×x̂ | spessore su x / lunghezza su y / altezza su z su banco noto — `test_abaqus.py:204` | **O** |
| `build_node_sets` | `:1163` | BASE: z ≤ z_min+t; TOP: z ≥ z_max−t; FACE_*: x; SIDE_*: y | sei facce di una scatola — `:236`; chiavi = costante — `:250` | **O** per BASE/TOP; i nomi FACE_/SIDE_ restano convenzione (docstring `:1172-1181`) |
| `boundary_faces` | `:909` | facce con occorrenza singola dopo ordinamento indici | 10 riferimenti in `test_abaqus.py` | **O** |
| `boundary_spacing` | `:930` | mediana ‖p_i − p_j‖ sugli spigoli unici delle facce di bordo | **0 riferimenti diretti** | **N** diretta |
| `set_tolerance` | `:1045` | t = factor · boundary_spacing | segue la spaziatura, non il volume elemento — `:658` | **O** (relazione) |
| `footprint_coverage` | `:1073` | celle di lato 4·spacing; colonna «a contatto» se z_min,col ≤ z_min+0,02·H | base piana → 1.0 (`:684`); conta colonne, non nodi (`:694`) | **O** |
| `constraint_plan_extent` | `:1123` | r_a = ptp(scelti_a)/ptp(tutti_a), a∈{x,y}; `minimo` = min | =1 su due piedi (`:762`), crolla su un angolo (`:787`, `:808`) | **O** |
| `aree_tributarie` | `:639` | ventaglio dal 1° nodo; A_tri = ‖(p₁−p₀)×(p₂−p₀)‖/2; ⅓ a ciascuno | Σ = 100·40 calcolato a mano, **non** contro `surface_area` — `:1296` | **O** |
| `surface_area` | `:617` | = `aree_tributarie(...).sum()` | faccia di cubo unitario = 1 — `:1025` | **O** |
| `ripartisci` | `:675` | q_i = R · A_i / ΣA | somma = risultante — `:1390` | **O** |
| `coppia_equivalente` | `:716` | separazione = fix_sign(1° vettore singolare di P_⊥asse); F = M/b_eff | **Σ F = 0 e M_z = 3000 ricalcolato dalle righe `*CLOAD` del deck** — `:1699-1702` | **O** — il più forte del repo |
| `element_surface` | `:505` | facce di bordo con **tutti** i nodi nel set | S1 del C3D8 + area = 1 — `:1025`; 3 nodi su 4 → `[]` — `:1034` | **O** |
| `volume` / `mass` export | `:1442,1464` | V = Σ\|V_elem\|; m = V·ρ | nessuna asserzione sul valore | **R** |

## Soluzione (`solve.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `von_mises` | `:474` | σ_vm = √{½[(σx−σy)²+(σy−σz)²+(σz−σx)²] + 3(τ²_xy+τ²_yz+τ²_zx)} | taglio puro = 5√3 (`:100`); trazione monoassiale = 7 (`:107`) | **O** per la formula; **ordine colonne `.frd` non verificato** (§1) |
| `_volume_totale` | `:486` | Σ \|V_tet(elements[:, :4])\| | dentro l'invariante di equilibrio | **O** indiretto |
| `_quota_tributaria_gravita` | `:498` | Σ_{(t,n): n∈set} ρ·V_t/4 | **invariante fisico chiuso**: Σ RF_z + q·g = ρVg su un tetraedro, rel 1e-6 — `:686` | **O** |
| `controlla_reazioni` | `:259` | ε = ‖ΣRF − W‖/‖W‖; passa ⟺ isfinite(tol) ∧ ε ≤ tol | modulo giusto + direzione storta = bocciato — `:490` | **O** |
| `controlla_autovalori` | `:304` | passa ⟺ tutte finite ∧ f₁>0 ∧ f₁/f₂ ≥ 0,2 | 0,0004 Hz bocciato — `:496-499` | **O** |
| `controlla_picco` | `:353` | p99 = percentile(v,99); frazione = #{v≥p99 ∧ q ≤ q_min+banda}/#{v≥p99} | costruito frazione = 1 → bocciato — `:518` | **O** |
| `controlla_vincolo_in_pianta` | `:409` | passa ⟺ isfinite(m) ∧ m ≥ 0,5 | `:385` | **O**, soglia però inattivabile su NaN (§3) |
| `controlla_avvisi` | `:437` | passa ⟺ conteggio = 0 | tabella in `test_solve.py` | **O** |
| `u_max` | `:700` | max_i ‖u_i‖ | dati sintetici — `:312` | **R** |
| `frequenze_hz` | `:449` | colonna 4 (CYCLES/TIME) del blocco `MODE NO` | colonna giusta, non la prima — `:184` | **O** |

## Conversioni di unità

Sistema dichiarato **mm, N, MPa, t, s** (`config.py:3`). Una sola conversione
numerica:

- `GRAVITY_MM_S2 = 9810.0` (`config.py:22`), usata come `AnalysisConfig.gravity`
  (`config.py:305`). **Nessun test asserisce il valore.** → **R/N**
- ρ in t/mm³ (`config.py:97`), E in MPa (`config.py:95`). La coerenza ρ·V·g → N è
  verificata **solo indirettamente** da `test_solve.py:686` (ρ=1.8e-9, g=9810,
  V=1e6/6 → 2,943 N). Quello è un oracolo dimensionale chiuso.
- `io.py:85` `points * cfg.scale`: unico punto di conversione ingresso→mm, difeso
  da `ScaleError` (`io.py:96`), non da un test di valore.
- `viewport.py:74` `/1000.0` è un ripiego per la dimensione voxel, non un'unità.

---

## 1. Grandezze senza oracolo indipendente

**Non coperte del tutto:**

1. **`tet_aspect_ratios`** (`quality.py:222`) — zero riferimenti in tutta
   `tests/`. Esercitata solo di rimbalzo da `volume_metrics` (`quality.py:359`),
   e quel test (`test_quality.py:90`) asserisce **solo** `inverted`. Finisce in
   `metrics.json` sotto `10_volume_quality.aspect_ratio` e nel report. Il gemello
   triangolare l'oracolo ce l'ha (`test_quality.py:64`).
2. **`boundary_spacing`** (`abaqus.py:930`) — zero chiamate dirette. Solo come
   ingrediente di `set_tolerance` (`abaqus.py:1070`), dove il test verifica la
   *relazione*, non il valore della mediana. **Sotto ci stanno tutti e sei i set
   di nodi.**

**Solo regressione o relazione, senza valore ancorato:**
`radius_edge_ratio_p99` (`volume.py:230`) · `extent` dentro `thickness`
(`quality.py:527`) · `export["volume"]` e `export["mass"]`
(`abaqus.py:1463-1464`, e sono i numeri che il report di confronto mette in
colonna, `report.py:1126`) · `u_max` (`solve.py:700`) · dispatch di
`element_volumes` (tautologia) · `GRAVITY_MM_S2` (`config.py:22`) ·
`extent`/`bbox_min`/`bbox_max` di `load_cloud` (`io.py:110-112`).

**Punto sensibile a parte — l'ordine delle colonne `.frd` in `von_mises`.**
La formula ha due oracoli analitici solidi, ma l'assunzione
**SXX,SYY,SZZ,SXY,SYZ,SZX** (`solve.py:477`) non è verificata contro nessun
`.frd` prodotto da `ccx` vero. Gli `.frd` dei test li scrive il test stesso
(`test_solve.py:242+`) e portano trazione monoassiale (σ,0,0,0,0,0) — stato
**invariante rispetto a qualunque permutazione** dentro il gruppo dei normali e
dentro quello dei taglianti. Nemmeno `tests/feasibility/test_calculix.py` la
tocca. La docstring dice «leggerlo sbagliato non solleva nulla e produce un
numero plausibile, che è il modo peggiore di sbagliare» — e oggi nulla lo
smentirebbe.

## 2. Metriche col nome standard e formula diversa

**`scaled_jacobian` (`quality.py:83`) — DIVERGE da Verdict/Sandia.**
Verdict `hex_scaled_jacobian` prende il minimo su **9** punti: gli 8 angoli **più
il centro**, dove usa gli assi principali (`calc_hex_efg`) e non tre spigoli.
`quality.py:107-127` prende il minimo su **8**. Conseguenza: un esaedro con facce
ragionevoli ma interno svergolato riceve qui un valore **più ottimistico** di
quello che Verdict, Cubit o VTK darebbero — e il valore finisce in
`hexa_metrics["scaled_jacobian"]` (`quality.py:151`) e nel report di confronto
(`report.py:1141`). La tabella `_ANGOLI_ESAEDRO` (`quality.py:77-80`) invece
**coincide** angolo per angolo con Verdict. La docstring non menziona
l'omissione del centro.
*Nota di staleness:* la doc Cubit 15.8 dice «8 corner nodes only», il sorgente
`sandialabs/verdict` dice 9 — **il sorgente vince**.

**`tet_aspect_ratios` (`quality.py:222`) — coincide** con Verdict/VTK
`L_max/(2√6·r_in)` (=1 sul tet regolare). **Ma non** con `Aspect Ratio Beta`
(= R_circ/(3·r_in)) né `Aspect Ratio Gamma` (= S_rms³/(8,479670·V)) di Cubit —
**e non con Abaqus/CAE, dove «aspect ratio» è spigolo massimo su spigolo minimo**,
che Verdict chiama `edge ratio`. Chi in tesi cita «aspect ratio» accanto a una
soglia presa da un manuale sta confrontando due grandezze diverse: **va detto
quale definizione è.**

**`triangle_aspect_ratios` (`quality.py:175`) — coincide** con Verdict,
`L_max/(2√3·r_in)`. *(Caveat: verificato per analogia con la tet, non aprendo il
sorgente Verdict del triangolo.)*

**`radius_edge_ratios` (`quality.py:240`)** — non è una metrica Verdict, è la
grandezza di **TetGen** (`-q`, `minratio`), √6/4 = 0,6124 sul regolare. Coerente
col nome. **Ma: il default `-q` di TetGen impone radius-edge ≤ 2,0 e angolo
diedro minimo 0° — nessun vincolo sugli sliver. Il radius-edge ratio è cieco agli
sliver per costruzione.** Per quelli serve il **minimum dihedral angle**, che il
progetto calcola (`quality.py:208`) ma non usa come vincolo. Fonte: manuale
TetGen 1.5 e Si 2015, ACM TOMS 41(2):11.

**`min_dihedral_angles`** e **`von_mises`** — definizioni standard, nessuna
divergenza. Range accettabile Verdict per il diedro minimo del tet: **[40°,
70,53°]**.

**`hex_volumes` (`quality.py:60`)** — la docstring lo dichiara già (`:64-67`):
**non** è la quadratura di Gauss dell'esaedro trilineare che Abaqus/CalculiX usano
per integrare l'elemento. È il volume del solido a facce triangolate. Su facce non
piane i due numeri differiscono. Scelta consapevole e documentata, da citare come
tale se il volume finisce in tesi accanto a una massa del solutore.

## 3. Guardie che non possono fallire

1. **`quality.py:574-575`, ramo modi adiacenti.** Con `upper == lower + 1`,
   `valley = float(counts[lower])` e la condizione
   `valley < 0.5·min(counts[lower], counts[upper])` è **falsa per costruzione**
   (verificato numericamente su 5 coppie, incluso 0/0). Due modi in bin contigui
   danno `bimodal=False` sempre. **L'ingresso che la farebbe scattare non
   esiste.**
2. **`abaqus.py:1114`, `if not in_contact.any(): return 0.0`.** `floor_height` è
   il minimo di z sui nodi **di bordo** per colonna; `low[2]` è il minimo su
   **tutti** i punti. Su una mesh di volume chiusa il nodo globalmente più basso è
   di bordo, quindi la sua colonna soddisfa sempre la condizione. Costruibile a
   mano (5 punti, il più basso non di bordo), **ma non producibile dalla
   pipeline**.
3. **`solve.py:431`, `np.isfinite(minimo)`** e **`solve.py:446`,
   `conteggio == 0` con NaN** — inerti **per progetto e dichiarate tali** nelle
   rispettive docstring. Non un difetto, ma nemmeno una difesa.

**Guardie che invece scattano davvero** (verificate): `volume.py:152` saturazione
Steiner (`test_volume.py:163`), `volume.py:175` limite di volume disatteso
(`:138`), `volume.py:231` vincolo raggio-spigolo (`:229`), `abaqus.py:1413`
`UnconstrainedModelWarning` (`test_abaqus.py:722`), `abaqus.py:877`
`SelettoreIsotropoWarning` (`:2140`), `solve.py:559` determinante ≠ +1
(`test_solve.py:970`).

## 4. Ingressi degeneri — misurati, non dedotti

**Il buco vero: le coordinate NaN passano ogni guardia di inversione.**

```
tet_volumes(NaN)                -> array([nan])
inverted_tets(NaN)              -> array([], dtype=int64)   # NON marcato
volume_metrics(NaN)["inverted"] -> 0
```

`quality.py:48` è `np.flatnonzero(V <= 0.0)`, e `nan <= 0.0` è `False`. Quindi:

- `volume.py:139` `if len(inverted) > 0: raise InvertedElementsError` **non
  solleva** su una mesh con nodi NaN;
- `metrics.json` scrive `inverted: 0` — **verde su una mesh corrotta**;
- `total_volume` (`quality.py:356`) diventa NaN e finisce in JSON, che NaN non
  ammette (`_distribution` protegge le distribuzioni, **non** `total_volume`).

Nessun test passa NaN a `inverted_tets` o a `volume_metrics`. È la stessa classe
di difetto che il «cancello di finitezza» ha chiuso in `solve.py`: `quality.py`
non l'ha mai attraversata.

Il resto, misurato:

| ingresso | esito | giudizio |
|---|---|---|
| mesh vuota → `is_watertight` | **`True`** | una mesh vuota è «chiusa». `volume.py:73` la passa a TetGen invece di rifiutarla |
| mesh vuota → `mesh_volume`, `surface_metrics`, `volume_metrics`, `hexa_metrics` | `0.0`, `min/median/mean/max = None` | gestito bene |
| tet complanare (V=0) → `inverted_tets` | `array([0])` | gestito |
| tet complanare → aspect / diedro / raggio-spigolo | `inf` / `0.0` / `inf` | gestito, mai eccezione |
| hex con nodi NaN → `scaled_jacobian` | `0.0` | gestito (`quality.py:122-124`) |
| nuvola a **1 punto** → `vertex_deviation` | array di zeri | gestito |
| nuvola **vuota** → `vertex_deviation` | **`array([inf, inf, inf])`** | **non gestito**: quegli inf finiscono nella mappa colore |
| nuvola < 2 punti → `thickness` | `{thickness: None, bimodal: False}` | gestito (`quality.py:500-520`) |
| array vuoto → `controlla_picco` | **`ValueError: zero-size array to reduction operation maximum`** | non guardato (`solve.py:393`); latente, non attivo |
| nodi vuoti → `build_node_sets` | **`ValueError: zero-size array to reduction operation minimum`** | non guardato (`abaqus.py:1184`) |
| indici vuoti → `constraint_plan_extent` | `{x:0, y:0, minimo:0}` | gestito (`abaqus.py:1150`), il verdetto boccia |
| elementi vuoti → `boundary_faces` | shape `(0,3)` | gestito |
| elemento a **10 nodi** → `element_volumes` | calcola sui primi 4 | **ramo morto**: `NODI_PER_ELEMENTO` (`abaqus.py:429`) non contiene più C3D10 dopo `66b526d`; `quality.py:164` accetta ancora `colonne == 10` |
| tensioni vuote → `von_mises` | array vuoto | gestito |

**Non verificato in questa sessione:** mesh non chiusa passata a
`geometric_error` / `thickness` (richiede PyMeshLab); elemento esaedrico passato a
`solve._volume_totale`, che userebbe `elements[:, :4]` senza dirlo — la docstring
(`solve.py:486-493`) ammette il limite e dichiara zero copertura sul ramo.

## 5. Conteggio test

- Raccolti: **1019 su 1035, 16 deselezionati** (2,58 s).
- Funzioni `test_*` definite, prima della parametrizzazione (conteggio AST):
  **892**.
- Di queste, **153 nominano almeno una delle 47 funzioni di calcolo**:
  `test_abaqus.py` 60, `test_quality.py` 40, `test_volume.py` 14, `test_solve.py`
  13, `test_io.py` 8, `test_server.py` 5, `test_repair.py` 4, `test_hexa.py` 3,
  `test_gmsh_backend.py` 2, `test_surface.py` 2, `test_config.py` 1,
  `test_pipeline.py` 1.
- **Caveat:** è un limite inferiore (molti test di `solve` passano per `risolvi`
  senza nominare le funzioni) e simmetricamente un limite superiore sulla
  *qualità* (nominare una funzione non vuol dire avere un oracolo per essa:
  `test_quality.py:90` nomina `volume_metrics` e verifica solo `inverted`).
- Rapporto grezzo: **153/892 ≈ 17%**. Il resto — `test_app_js.py` 158,
  `test_server.py` 114, `test_config.py` 100 — è interfaccia, HTTP e validazione.

---

## Il materiale che conta

**Senza oracolo indipendente, in ordine di rischio per la tesi:**

1. `tet_aspect_ratios` (`quality.py:222`) — **zero test**, e il numero finisce in
   `metrics.json` e nel report.
2. **Ordine colonne `.frd` in `von_mises`** (`solve.py:477`) — formula verificata,
   mappatura no, e nessuno stato di prova la potrebbe smentire.
3. `export["volume"]` / `export["mass"]` (`abaqus.py:1463-1464`) — vanno in colonna
   nel report di confronto, nessuna asserzione di valore.
4. `boundary_spacing` (`abaqus.py:930`) — zero chiamate dirette; sotto ci stanno
   tutti e sei i set di nodi.
5. `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, `GRAVITY_MM_S2`,
   ingombro/bbox.

**Guardie inerti:** `quality.py:574` · `abaqus.py:1114` · `solve.py:431` e `:446`
(queste due dichiarate).

**Il difetto singolo più grave — una guardia cieca, non inerte:**
`inverted_tets` (`quality.py:48`) usa `V <= 0.0`, e NaN cade dalla parte
permissiva. Una mesh con coordinate non finite passa `InvertedElementsError`
(`volume.py:139`) e viene registrata con `inverted: 0`.

**Raccomandazione (non una decisione).** I tre buchi sono cose diverse: il NaN è
un fix da un carattere più il suo test; `tet_aspect_ratios` è un test mancante;
l'ordine `.frd` chiede un `.frd` prodotto da `ccx` vero in `tests/feasibility/`.
La divergenza `scaled_jacobian` contro Verdict **non la toccherei nel codice**:
va dichiarata in tesi e nella docstring, perché aggiungere il nono punto
sposterebbe tutti i numeri già pubblicati.

## Fonti

- [Metrics for Hexahedral Elements — Cubit/Sandia](https://cubit.sandia.gov/files/cubit/15.8/help_manual/WebHelp/mesh_generation/mesh_quality_assessment/hexahedral_metrics.htm)
- [sandialabs/verdict — V_HexMetric.cpp](https://raw.githubusercontent.com/sandialabs/verdict/master/V_HexMetric.cpp)
- [Metrics for Tetrahedral Elements — Coreform Cubit](https://coreform.com/cubit_help/mesh_generation/mesh_quality_assessment/tetrahedral_metrics.htm)
- Stimpson, Knupp et al., *The Verdict Geometric Quality Library*, SAND2007-1751.
- Si, H. (2015), «TetGen, a Delaunay-Based Quality Tetrahedral Mesh Generator»,
  *ACM TOMS* 41(2):11.
