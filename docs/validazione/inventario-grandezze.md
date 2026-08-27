# Inventario delle grandezze calcolate, e di cosa le verifica

Rimisurato il 27/08/2026 su `main` a **`fed1872`**, **albero di lavoro pulito**:
le righe citate sono quelle di quel commit, non di un albero di lavoro, e la
prossima deriva e' quindi databile.

La stesura precedente era misurata su un albero **sporco** a `a07071a`, novanta
commit piu' indietro. Fra i due, le PR #49-#109 hanno chiuso buona parte dei
difetti che questo documento registrava: la sezione 6 elenca voce per voce che
cosa e' rimasto vero, che cosa e' stato chiuso e da quale commit.

I riferimenti `file:riga` si ricontrollano a macchina:

    python docs/validazione/controlla-riferimenti.py docs/validazione/inventario-grandezze.md

Che una riga esista non dice che porti ancora la cosa di cui il testo parla:
quello lo vede solo chi legge, ed e' il lavoro che questa stesura ha rifatto.

Raccolta test: `uv run pytest --collect-only -q` → **1320 casi**, di cui **44**
marcati `validazione` e **17** `feasibility`, entrambi esclusi dalla corsa
predefinita (`pyproject.toml:47`, `addopts = "-m 'not feasibility and not
validazione'"`).

**Perimetro.** Sono censite le grandezze che l'inventario copriva al 26/08/2026,
rimisurate una per una. Sono entrate dopo, e **restano da censire in un giro
proprio**: `quality.is_oriented`, `quality.scarto_con_segno`,
`solve.controlla_massa_modale`, l'estrapolazione di Richardson e la GCI di
`convergenza.py`, e il registro di `soglie.py`.

Legenda verdetto: **O** = oracolo indipendente (valore analitico noto,
invariante, o libreria terza) · **R** = solo regressione autoreferenziale · **N**
= non coperta.

---

## Superficie

| grandezza | dove | formula | unita'/segno | oracolo | v |
|---|---|---|---|---|---|
| `mesh_volume` | `quality.py:77` | V = Σ_f (a·(b×c))/6 | mm³, + se normali uscenti | scatola esatta 100·40·200 — `test_quality.py:33`, `test_quality.py:78` | **O** |
| area superficie | `quality.py:449` | A = Σ_f ‖(b−a)×(c−a)‖/2 | mm², ≥0 | 2(100·40+100·200+40·200) analitico — `test_quality.py:79` | **O** |
| `is_watertight` | `quality.py:42` | ∀e: n(e)=2, **e almeno uno spigolo** | bool | scatola chiusa — `test_quality.py:27`; bucata — `test_quality.py:43` | **O** |
| `boundary_edges` | `quality.py:36` | {e : n(e)=1} | conteggio | 4 spigoli dopo un buco — `test_quality.py:42` | **O** |
| `triangle_aspect_ratios` | `quality.py:278` | AR = L_max/(2√3·r), r = 2A/Σℓ | adim., ≥1 | equilatero = 1 — `test_quality.py:64`; sliver >100 — `test_quality.py:70` | **O** |

## Volume — tetraedri

| grandezza | dove | formula | unita'/segno | oracolo | v |
|---|---|---|---|---|---|
| `tet_volumes` | `quality.py:88` | V = (b−a)·((c−a)×(d−a))/6 | mm³, **con segno**, <0 = invertito | Σ = volume esatto scatola su output TetGen — `test_volume.py:31` | **O** |
| `inverted_tets` | `quality.py:96` | {i : ¬(finito(V_i) ∧ V_i > 0)} | indici | tet a orientazione scambiata — `test_quality.py:95`; NaN e inf marcati — `test_cancello_finitezza.py:73` | **O** |
| `min_dihedral_angles` | `quality.py:311` | θ = min_{i<j} [180° − arccos(n̂_i·n̂_j)] | gradi, ∈[0,180] | tet regolare = arccos(1/3) = 70,5288° — `test_quality.py:52`; schiacciato <1° — `test_quality.py:58` | **O** |
| `tet_aspect_ratios` | `quality.py:325` | AR = L_max/(2√6·r), r = 3V/ΣA_f | adim., ≥1, ∞ se degenere | regolare = 1 — `test_oracoli_mancanti.py:55`; rettangolo (1+√3)/2 in forma chiusa — `test_oracoli_mancanti.py:73`; degenere → ∞ — `test_oracoli_mancanti.py:85` | **O** |
| `radius_edge_ratios` | `quality.py:356` | ρ = R_circ/L_min | adim., ≥√6/4 | tet regolare = √6/4 (rel 1e-9) — `test_quality.py:151`; schiacciato >10 — `test_quality.py:161`; complanare → ∞ — `test_quality.py:169` | **O** |
| `fraction_over_ratio` | `quality.py:455` | #{ρ finito > limite}/#{ρ finito}; 1,0 se vuoto | ∈[0,1] | 0,0/1,0 costruiti — `test_quality.py:288`, `test_quality.py:289` | **O** |
| `radius_edge_ratio_p99` | `volume.py:279` | q₀,₉₉ dei ρ finiti; `None` se vuoto | adim. | e' davvero un percentile: dentro il campo, ≥98% sotto, ≥√6/4 — `test_oracoli_mancanti.py:254`, `test_oracoli_mancanti.py:261` | **O** |

## Volume — esaedri

| grandezza | dove | formula | unita'/segno | oracolo | v |
|---|---|---|---|---|---|
| `hex_volumes` | `quality.py:122` | V = Σ_{k=1..6} V_tet (ventaglio da 0 attorno alla diagonale 0–6) | mm³, con segno | cubo unitario = 1 — `test_quality.py:499`; rovesciato <0 — `test_quality.py:513` | **O** |
| `scaled_jacobian` | `quality.py:145` | SJ = min su **nove** punti: gli 8 angoli, det(e₁,e₂,e₃)/(‖e₁‖‖e₂‖‖e₃‖), piu' il centro sugli assi principali medi; 0 se il prodotto e' nullo | adim., ≤1 | cubo = 1 — `test_quality.py:536`; angolo a 45° = 1/√2 in forma chiusa — `test_quality.py:554`; ripiegato <0 — `test_quality.py:583` | **O**, e **coincide con Verdict** (§2) |
| `element_volumes` | `quality.py:258` | dispatch sul numero di colonne: 8→hex, 4 o 10→tet dei primi 4 | mm³ | concorda con `tet_volumes`/`hex_volumes` — `test_quality.py:500`, `test_quality.py:523` | **R** (tautologia) |

## Errore geometrico, deviazione, spessore

| grandezza | dove | formula | unita'/segno | oracolo | v |
|---|---|---|---|---|---|
| `geometric_error` | `quality.py:493` | delega a PyMeshLab `get_hausdorff_distance` nei due versi; `hausdorff` = max(max_c2m, max_m2c) | mm, ≥0 | nuvola campionata sulla mesh → piccolo (`test_quality.py:106`); traslata → cresce (`test_quality.py:119`); coerenza con `vertex_deviation` rel 1e-5 (`test_quality.py:440`) | **O** |
| `vertex_deviation` | `quality.py:566` | d_v = min_{p∈nuvola} ‖v − p‖ (cKDTree, k=1) | mm, ≥0 | 0 esatto sui punti + 0,25 noto fuori — `test_quality.py:310`, `test_quality.py:311`; scostamento 3,0 — `test_quality.py:320`; RMS = 0,5 analitico — `test_quality.py:366` | **O** |
| `thickness` | `quality.py:609` | PCA 3×3 → asse di `ptp` minimo; istogramma a passo `bin_width`; s = c_upper − c_lower; `bimodal` ⟺ modi non contigui **e** mean(valle) < ½·min(picchi) | mm, >0 | lastra a spessore noto 176 mm ±3 — `test_quality.py:187`; solido pieno → non valido — `test_quality.py:201` | **O** |
| `extent` (in `thickness`) | `quality.py:660` | ptp lungo l'autovettore minimo | mm | lastra allineata: 37,0 esatto — `test_oracoli_mancanti.py:197` | **O** |
| `_distribution` | `quality.py:413` | min/median/mean/max sui soli finiti + `non_finite` | come il campo | `None` invece di NaN, mediana 2,0 — `test_quality.py:131`, `test_quality.py:136` | **O** |

## Ingresso e scala

| grandezza | dove | formula | unita' | oracolo | v |
|---|---|---|---|---|---|
| `mean_spacing` | `io.py:64` | mean(d₂) su campione casuale, d₂ = 2° vicino kd-tree | mm | 8 test in `test_io.py` | — |
| `scale` | `io.py:85` | p ← p · cfg.scale | fattore adim. → mm | `size_check` contro `expected_size` (`io.py:91-102`) — controllo, non test | **O** se l'utente dichiara le misure |
| `extent`/`bbox` | `io.py:86-88` | max − min per asse | mm | `test_io.py` | **R** |

## Deck e set di nodi (`abaqus.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `align_to_axes` | `abaqus.py:1246` | ẑ ≡ [0,0,1]; x̂ = fix_sign(autovettore di ptp minimo della PCA 2D orizzontale); ŷ = ẑ×x̂ | spessore su x / lunghezza su y / altezza su z su banco noto — `test_abaqus.py:285` | **O** |
| `build_node_sets` | `abaqus.py:1482` | BASE: z ≤ z_min+t; TOP: z ≥ z_max−t; FACE_*: x; SIDE_*: y | sei facce di una scatola — `test_abaqus.py:310`; chiavi = costante — `test_abaqus.py:332` | **O** per BASE/TOP; i nomi FACE_/SIDE_ restano convenzione (docstring `abaqus.py:1491-1501`) |
| `boundary_faces` | `abaqus.py:1190` | facce con occorrenza singola dopo ordinamento indici; su 10 colonne usa i primi 4 vertici | 10 riferimenti in `test_abaqus.py` | **O** |
| `boundary_spacing` | `abaqus.py:1220` | mediana ‖p_i − p_j‖ sugli spigoli unici delle facce di bordo | tetraedro regolare di lato 1 → 1 — `test_oracoli_mancanti.py:107`; scala col fattore 2 — `test_oracoli_mancanti.py:120` | **O** |
| `set_tolerance` | `abaqus.py:1348` | t = factor · boundary_spacing (`abaqus.py:1373`) | segue la spaziatura, non il volume elemento — `test_abaqus.py:750` | **O** (relazione) |
| `footprint_coverage` | `abaqus.py:1376` | celle di lato 4·spacing; colonna «a contatto» se z_min,col ≤ z_min+0,02·H | base piana → 1,0 (`test_abaqus.py:761`); conta colonne, non nodi (`test_abaqus.py:788`) | **O** |
| `constraint_plan_extent` | `abaqus.py:1442` | r_a = ptp(scelti_a)/ptp(tutti_a), a∈{x,y}; `minimo` = min | =1 su due piedi (`test_abaqus.py:852`), crolla su un angolo (`test_abaqus.py:875`, `test_abaqus.py:898`) | **O** |
| `aree_tributarie` | `abaqus.py:889` | ventaglio dal 1° nodo; A_tri = ‖(p₁−p₀)×(p₂−p₀)‖/2; ⅓ a ciascuno | Σ = 100·40 calcolato a mano, **non** contro `surface_area` — `test_abaqus.py:1366` | **O** |
| `surface_area` | `abaqus.py:867` | = `aree_tributarie(...).sum()` | faccia di cubo unitario = 1 — `test_abaqus.py:1095` | **O** |
| `ripartisci` | `abaqus.py:925` | q_i = R · A_i / ΣA | somma = risultante — `test_abaqus.py:1440` | **O** |
| `coppia_equivalente` | `abaqus.py:997` | separazione = fix_sign(1° vettore singolare di P_⊥asse); F = M/b_eff | **Σ F = 0 e M_z = 3000 ricalcolato dalle righe `*CLOAD` del deck** — `test_abaqus.py:1769-1772` | **O** — il piu' forte del repo |
| `element_surface` | `abaqus.py:637` | facce di bordo con **tutti** i nodi nel set | S1 del C3D8 + area = 1 — `test_abaqus.py:1094`, `test_abaqus.py:1095`; 3 nodi su 4 → `[]` — `test_abaqus.py:1104` | **O** |
| `volume` / `mass` export | `abaqus.py:1813-1814` | V = Σ\|V_elem\|; m = V·ρ | scatola nota, rel 1e-6 — `test_oracoli_mancanti.py:149`, `test_oracoli_mancanti.py:150` | **O** |

## Soluzione (`solve.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `von_mises` | `solve.py:824` | σ_vm = √{½[(σx−σy)²+(σy−σz)²+(σz−σx)²] + 3(τ²_xy+τ²_yz+τ²_zx)} | taglio puro = 5√3 (`test_solve.py:100`); trazione monoassiale = 7 (`test_solve.py:107`) | **O**; **anche l'ordine delle colonne `.frd`** e' verificato contro `ccx` vero (§1) |
| `_volume_totale` | `solve.py:851` | Σ \|V_tet(elements[:, :4])\| | dentro l'invariante di equilibrio | **O** indiretto |
| `_quota_tributaria_gravita` | `solve.py:863` | carichi consistenti: C3D4 ρ·V/4 ai vertici; C3D10 −1/20 ai vertici e +1/5 ai lati | **invariante fisico chiuso**: Σ RF_z + q·g = ρVg su un tetraedro, rel 1e-6 — `test_solve.py:731`; somma = massa su entrambi gli elementi — `test_solve.py:756-758` | **O** |
| `controlla_reazioni` | `solve.py:380` | ε = ‖ΣRF − W‖/‖W‖; passa ⟺ isfinite(tol) ∧ ε ≤ tol | modulo giusto + direzione storta = bocciato — `test_solve.py:536` | **O** |
| `controlla_autovalori` | `solve.py:425` | passa ⟺ tutte finite ∧ f₁>0 ∧ f₁/f₂ ≥ 0,2 | 0,0004 Hz bocciato — `test_solve.py:542` | **O** |
| `controlla_picco` | `solve.py:474` | p99 = percentile(v,99); frazione = #{v≥p99 ∧ q ≤ q_min+banda}/#{v≥p99} | costruito frazione = 1 → bocciato — `test_solve.py:560` | **O** |
| `controlla_vincolo_in_pianta` | `solve.py:541` | passa ⟺ isfinite(m) ∧ m ≥ 0,5 | soglia di produzione su due casi noti — `test_solve.py:385` | **O** |
| `controlla_avvisi` | `solve.py:569` | passa ⟺ conteggio = 0 | tabella in `test_solve.py` | **O** |
| `u_max` | `solve.py:581` | max_i ‖u_i‖ | aritmetica in forma chiusa sul `.frd` di prova: 3,6·√2 — `test_solve.py:461` | **O** |
| `frequenze_hz` | `solve.py:799` | colonna 4 (CYCLES/TIME) del blocco `MODE NO` | colonna giusta, non la prima — `test_solve.py:193` | **O** |

## Conversioni di unita'

Sistema dichiarato **mm, N, MPa, t, s** (`config.py:3`). Una sola conversione
numerica:

- `GRAVITY_MM_S2 = 9810,0` (`config.py:22`), usata come `AnalysisConfig.gravity`
  (`config.py:374`). Asserita contro 9,81·1000 — `test_oracoli_mancanti.py:163`.
  → **O**
- ρ in t/mm³ (`config.py:97`), E in MPa (`config.py:95`). La coerenza ρ·V·g → N
  ha due oracoli: quello dimensionale chiuso di `test_solve.py:731` (ρ=1,8e-9,
  g=9810, V=1e6/6 → 2,943 N) e l'acqua a `test_oracoli_mancanti.py:176`
  (1 t/m³ · 1 m³ · g = 9810 N).
- `io.py:85` `points * cfg.scale`: unico punto di conversione ingresso→mm, difeso
  da `ScaleError` (`io.py:96`), non da un test di valore.
- `viewport.py:74` `/1000.0` e' un ripiego per la dimensione voxel, non un'unita'.

---

## 1. Grandezze senza oracolo indipendente

**Nessuna delle voci elencate qui il 26/08/2026 lo e' ancora.** Le cinque
lacune sono state chiuse da `tests/test_oracoli_mancanti.py` (commit `aa2716f`),
e l'ordine delle colonne `.frd` da `tests/validazione/test_ordine_frd.py`
(commit `87c7d7c`). Il registro sta in §6.

Cio' che resta senza valore ancorato, e non e' un difetto ma un limite
dichiarato:

- **`element_volumes`** (`quality.py:258`) — il dispatch e' verificato contro
  `tet_volumes` e `hex_volumes`, cioe' contro se stesso. E' una tautologia per
  costruzione: la funzione **e'** quel dispatch, e non c'e' un terzo termine di
  paragone.
- **`extent`/`bbox_min`/`bbox_max` di `load_cloud`** (`io.py:110-112`) — solo
  regressione. Sono `max − min` per asse: un oracolo indipendente sarebbe la
  stessa formula scritta due volte.
- **`mean_spacing`** (`io.py:64`) — otto test in `test_io.py` la esercitano,
  nessuno la confronta con una spaziatura nota per costruzione.

**Il punto sensibile che era il piu' grave, e non lo e' piu'.** L'assunzione
**SXX,SYY,SZZ,SXY,SYZ,SZX** in `von_mises` (`solve.py:827`) non e' piu' assunta:
`tests/validazione/test_ordine_frd.py` impone sul bordo un campo di spostamento
lineare, che produce uno stato costante con **tutte e sei le componenti distinte
e ben separate**, e confronta le sei colonne lette dal `.frd` una per una con la
legge di Hooke. Un secondo test prova che **tutte e 719 le permutazioni** diverse
dall'identita' verrebbero respinte, cioe' che il confronto discrimina invece di
limitarsi a passare. Era il difetto D2 del registro; e' chiuso.

## 2. Metriche col nome standard e formula diversa

**`scaled_jacobian` (`quality.py:145`) — oggi COINCIDE con Verdict/Sandia.**
Verdict `hex_scaled_jacobian` prende il minimo su **9** punti: gli 8 angoli piu'
il centro, dove usa gli assi principali medi (`calc_hex_efg`) e non tre spigoli.
Fino a `0a622a5` questa funzione prendeva il minimo su **8**, e dava quindi un
valore sistematicamente **piu' ottimistico**. Il nono punto ora c'e'
(`quality.py:198-224`), accanto agli otto angoli (`quality.py:180-196`), e la
docstring lo dichiara. Il costo era nullo e misurato: zero scarto su 1644
esaedri di tre prismi gmsh e su 148.689 cubi perturbati a caso, quindi
**nessun numero gia' pubblicato si e' spostato**. La tabella `_ANGOLI_ESAEDRO`
(`quality.py:139-142`) coincide angolo per angolo con Verdict.
*Nota di staleness:* la doc Cubit 15.8 dice «8 corner nodes only», il sorgente
`sandialabs/verdict` dice 9 — **il sorgente vince**, e la docstring lo scrive.

**`tet_aspect_ratios` (`quality.py:325`) — coincide** con Verdict/VTK
`L_max/(2√6·r_in)` (=1 sul tet regolare). **Ma non** con `Aspect Ratio Beta`
(= R_circ/(3·r_in)) ne' `Aspect Ratio Gamma` (= S_rms³/(8,479670·V)) di Cubit —
**e non con Abaqus/CAE, dove «aspect ratio» e' spigolo massimo su spigolo minimo**,
che Verdict chiama `edge ratio`. Sul tetraedro rettangolo di lato 1 questa vale
(1+√3)/2 = 1,366 e quella di Abaqus √2 = 1,414. La divergenza ora e' scritta
nella docstring della funzione e nel registro delle soglie, non solo qui: chi
cita «aspect ratio» accanto a una soglia presa da un manuale **deve dire quale
definizione e'**.

**`triangle_aspect_ratios` (`quality.py:278`) — coincide** con Verdict,
`L_max/(2√3·r_in)`. *(Caveat invariato: verificato per analogia con la tet, non
aprendo il sorgente Verdict del triangolo.)*

**`radius_edge_ratios` (`quality.py:356`)** — non e' una metrica Verdict, e' la
grandezza di **TetGen** (`-q`, `minratio`), √6/4 = 0,6124 sul regolare. Coerente
col nome. **Ma: il default `-q` di TetGen impone radius-edge ≤ 2,0 e angolo
diedro minimo 0° — nessun vincolo sugli sliver. Il radius-edge ratio e' cieco agli
sliver per costruzione**, e la docstring lo misura: quattro punti sfalsati di un
millesimo attorno a una circonferenza danno raggio-spigolo **0,707**, cioe' sotto
il limite, e diedro minimo **0,162°**. Per quelli serve il **minimum dihedral
angle**, che il progetto calcola (`quality.py:311`) ma non usa come vincolo.
Fonte: manuale TetGen 1.5 e Si 2015, ACM TOMS 41(2):11.

**`min_dihedral_angles`** e **`von_mises`** — definizioni standard, nessuna
divergenza. Range accettabile Verdict per il diedro minimo del tet: **[40°,
70,53°]**.

**`hex_volumes` (`quality.py:122`)** — la docstring lo dichiara (`quality.py:123-129`):
**non** e' la quadratura di Gauss dell'esaedro trilineare che Abaqus/CalculiX usano
per integrare l'elemento. E' il volume del solido a facce triangolate. Su facce non
piane i due numeri differiscono. Scelta consapevole e documentata, da citare come
tale se il volume finisce in tesi accanto a una massa del solutore.

## 3. Guardie che non possono fallire

**Due delle tre voci non esistono piu'.**

1. **Ramo modi adiacenti in `thickness`** — era `valley = float(counts[lower])`
   con `valley < 0.5·min(counts[lower], counts[upper])`, **falsa per
   costruzione**. Chiusa da `0a622a5`: la condizione ora e' scritta come esito e
   non come calcolo, `upper > lower + 1 and mean(valle) < ...`
   (`quality.py:714-716`), e il commento sopra dice perche' la forma precedente
   non poteva dare `True`. Due modi in bin contigui restano `bimodal=False`, ma
   ora perche' e' **dichiarato**, non perche' un confronto impossibile fallisce.
2. **`footprint_coverage`, nessuna colonna a contatto** — era `return 0.0`,
   irraggiungibile su qualunque mesh chiusa. Chiusa da `0a622a5`: ora
   **solleva** (`abaqus.py:1417-1433`), e il commento spiega che quello zero si
   sarebbe letto come «l'insieme non copre nulla», condizione vera e diversa.
   Il ramo resta irraggiungibile dalla pipeline; cio' che e' cambiato e' che
   adesso, se ci si arriva, si sa.
3. **`solve.py:563` `np.isfinite(minimo)`** e **`solve.py:578` `conteggio == 0`
   con NaN** — restano inerti **per progetto e dichiarate tali** nelle rispettive
   docstring: la seconda dice esplicitamente che l'uguaglianza a zero e' gia'
   chiusa su NaN e sugli infiniti, e che sta nella tabella dei sette verdetti
   perche' enumerarli tutti costa meno che ricordare quale non serviva. Non un
   difetto, ma nemmeno una difesa.

**Guardie che invece scattano davvero** (verificate): `volume.py:207`
saturazione Steiner (`test_volume.py:162`), `volume.py:234` limite di volume
disatteso (`test_volume.py:136`), `volume.py:287` vincolo raggio-spigolo
(`test_volume.py:234`), `abaqus.py:1753` `UnconstrainedModelWarning`
(`test_abaqus.py:802`), `abaqus.py:1169` `SelettoreIsotropoWarning`
(`test_abaqus.py:2275`), `solve.py:986` determinante ≠ +1 (`test_solve.py:1199`).

## 4. Ingressi degeneri

**Il buco che era il piu' grave e' chiuso.** Le coordinate NaN non passano piu'
la guardia di inversione: `inverted_tets` (`quality.py:110`) e' scritta in
positivo, `~(isfinite(V) & (V > 0))`, e il controllo di finitezza copre anche la
meta' che `not (V > 0)` da solo non coprirebbe — un volume `+inf` e' maggiore di
zero e passerebbe. `hexa_metrics` usa la stessa forma (`quality.py:251`), e gli
scalari che uscivano `NaN` in JSON passano ora per `finito_o_none`
(`quality.py:8`), che rende `None`. La copertura sta in
`tests/test_cancello_finitezza.py`.

La tabella qui sotto **non e' rimisurata eseguendo il codice**: questo giro non
aveva un ambiente con numpy separato da quello condiviso. Ogni riga porta quindi
la propria fonte — una guardia esplicita nel sorgente, o un test che la fissa —
e le righe che dipendevano da un comportamento di numpy senza una guardia che lo
scriva sono marcate **da rimisurare**.

| ingresso | esito | fonte | giudizio |
|---|---|---|---|
| mesh vuota → `is_watertight` | **`False`** | guardia `quality.py:52` | chiuso: era `True`, e `volume.tetrahedralize` la passava a TetGen. Ora `volume.py:96-105` la rifiuta per prima |
| mesh vuota → `mesh_volume`, `surface_metrics`, `volume_metrics`, `hexa_metrics` | `0,0`, `min/median/mean/max = None` | `quality.py:427-431` | gestito |
| tet complanare (V=0) → `inverted_tets` | marcato | `quality.py:110` (`0.0 > 0.0` e' falso) | gestito |
| tet complanare → aspetto / diedro / raggio-spigolo | ∞ / ~0° / ∞ | `test_oracoli_mancanti.py:85`, `test_quality.py:58`, `test_quality.py:169` | gestito, mai eccezione |
| hex con nodi NaN → `scaled_jacobian` | `0,0` | guardia `where=prodotto > 0.0`, `quality.py:193-195` e `quality.py:220-222` | gestito |
| hex con nodi inf → `hexa_metrics["inverted"]` | contato | `quality.py:251` | chiuso: il vecchio `jacobiani <= 0.0` ne contava **zero** |
| nuvola a **1 punto** → `vertex_deviation` | array di zeri | — | **da rimisurare**: nessuna guardia lo scrive e nessun test lo fissa |
| nuvola **vuota** → `vertex_deviation` | **`ValueError`** | guardia `quality.py:600-603` | chiuso: erano `[inf, inf, inf]` nella mappa colore |
| nuvola < 2 punti → `thickness` | `{thickness: None, bimodal: False}` | guardia `quality.py:633-653` | gestito |
| array vuoto → `controlla_picco` | **`ValueError` col proprio messaggio** | guardia `solve.py:519-523` | chiuso: era `zero-size array to reduction operation maximum` |
| nodi vuoti → `build_node_sets` | **`ValueError` col proprio messaggio** | guardia `abaqus.py:1507-1510` | chiuso: era `zero-size array to reduction operation minimum` |
| nodi non finiti → `build_node_sets` | **`ValueError`** | guardia `abaqus.py:1517-1521` | chiuso: i due set dell'asse uscivano **vuoti** senza che nulla protestasse |
| indici vuoti → `constraint_plan_extent` | `{x:0, y:0, minimo:0}` | `abaqus.py:1469-1470` | gestito, il verdetto boccia |
| elementi vuoti → `boundary_faces` | shape `(0,3)` | — | **da rimisurare** |
| elemento a **10 nodi** → `element_volumes` | calcola sui primi 4 | `quality.py:267` | **non e' piu' un ramo morto**: `NODI_PER_ELEMENTO` (`abaqus.py:539`) contiene di nuovo `C3D10` dopo `76bbc00`, e `boundary_faces` (`abaqus.py:1206-1207`) tratta le dieci colonne come tetraedro |
| elemento a 6 nodi → `boundary_faces` | **`ValueError`** | `abaqus.py:1209-1212`, `test_abaqus.py:987` | gestito |
| tensioni vuote → `von_mises` | array vuoto | — | **da rimisurare** |

**Non verificato in questa sessione:** mesh non chiusa passata a
`geometric_error` / `thickness` (richiede PyMeshLab); elemento esaedrico passato a
`solve._volume_totale`, che userebbe `elements[:, :4]` senza dirlo — la docstring
(`solve.py:851-858`) ammette il limite e dichiara zero copertura sul ramo.

## 5. Conteggio test

- Raccolti su `fed1872`: **1320 casi**, di cui **44** marcati `validazione` e
  **17** `feasibility`. Entrambi i marcatori sono esclusi dalla corsa
  predefinita (`pyproject.toml:47`).
- Funzioni `test_*` di modulo, prima della parametrizzazione:
  **1138** — `grep -rh "^def test_" tests/ --include="*.py" | wc -l` da
  `meshrec/`.
- **Rimosso**, e vale la pena dire perche': la stesura precedente riportava
  «153 su 892 nominano almeno una delle 47 funzioni di calcolo, ≈17%», con un
  caveat che lo dichiarava insieme limite inferiore e limite superiore. Un
  numero che non regge una conclusione in nessuna delle due direzioni, e che
  nessun comando scritto da qualche parte permetteva di rifare, non e' una
  misura: e' un'impressione con tre cifre. I conteggi che restano hanno il
  comando accanto.

---

## 6. Che cosa e' cambiato dal 26/08/2026

Ogni voce della stesura precedente, con il proprio esito su `fed1872`. Le sigle
D/O/G/N sono quelle del registro in [`README.md`](README.md) §3.

| voce | stato | dove |
|---|---|---|
| D1 — `inverted_tets` filtra con `V <= 0.0`, NaN passa | **chiusa** (`757429c`, `69465e1`) | `quality.py:110`, `tests/test_cancello_finitezza.py` |
| D2 — ordine colonne `.frd` mai verificato contro `ccx` | **chiusa** (`87c7d7c`) | `solve.py:827`, `tests/validazione/test_ordine_frd.py` |
| D3 — `controlla_reazioni` confronta `RF` col peso, ma sotto gravita' `RF` non e' la sola reazione | **ancora vera**, e gestita: `risolvi` somma la quota tributaria prima del confronto | `solve.py:863`, `test_solve.py:731` |
| D4 — nessuna guardia sull'ampiezza degli spostamenti | **chiusa** (`c8d9084`) | `solve.controlla_spostamenti`, `solve.py:611` |
| D5 — `vertex_deviation` su nuvola vuota rende `[inf, inf, inf]` | **chiusa** | `quality.py:600-603` |
| D6 — `build_node_sets` su nodi vuoti solleva `ValueError` grezzo | **chiusa** | `abaqus.py:1507-1510` |
| D7 — `controlla_picco` su array vuoto solleva `ValueError` grezzo | **chiusa** (`587d138`) | `solve.py:519-523` |
| D8 — `element_volumes` accetta 10 colonne ma C3D10 non esiste piu' | **falsa oggi**: C3D10 e' stato ripristinato (`76bbc00`, `479d671`) | `abaqus.py:539`, `quality.py:267` |
| O1 — `tet_aspect_ratios` senza alcun test | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.py:47-89` |
| O2 — `boundary_spacing` senza chiamate dirette | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.py:95-120` |
| O3 — `export["volume"]`/`export["mass"]` senza asserzione di valore | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.py:149-150` |
| O4 — `GRAVITY_MM_S2` che nessun test asserisce | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.py:163`, `test_oracoli_mancanti.py:176` |
| O5 — `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, ingombro/bbox | **chiusa in parte**: p99 ed `extent` hanno ora un oracolo, `u_max` ce l'ha in forma chiusa; ingombro/bbox resta **R** | `test_oracoli_mancanti.py:197`, `test_oracoli_mancanti.py:254`, `test_solve.py:461` |
| G1 — `bimodal` coi modi in bin contigui, falsa per costruzione | **chiusa** (`0a622a5`) | `quality.py:714-716` |
| G2 — `if not in_contact.any(): return 0.0` irraggiungibile | **chiusa** (`0a622a5`): ora solleva | `abaqus.py:1417-1433` |
| G3 — `isfinite(minimo)` e `conteggio == 0` inerti per progetto | **ancora vera**, e dichiarata | `solve.py:563`, `solve.py:578` |
| N1 — `scaled_jacobian` su 8 punti, diverge da Verdict | **chiusa** (`0a622a5`): nove punti, centro compreso | `quality.py:198-224` |
| N2 — «aspect ratio» del tet non e' quello di Abaqus | **ancora vera**, e ora dichiarata nella docstring | `quality.py:328-338` |
| N3 — raggio-spigolo cieco agli sliver | **ancora vera**, e ora misurata nella docstring | `quality.py:370-379` |
| N4 — `hex_volumes` non e' la quadratura di Gauss | **ancora vera**, gia' dichiarata | `quality.py:123-129` |
| §4 — mesh vuota «chiusa», passata a TetGen | **chiusa** | `quality.py:52`, `volume.py:96-105` |
| §5 — «1019 su 1035 raccolti» | **scaduta**: 1320 casi | `pyproject.toml:47` |

**Nessuna voce e' risultata falsa gia' al 26/08/2026.** Tutte erano vere quando
scritte; sedici PR le hanno superate in due giorni, e il documento non se n'era
accorto perche' nulla lo obbligava a farlo. Ora
`docs/validazione/controlla-riferimenti.py` obbliga almeno i puntatori.

## Il materiale che conta

**Senza oracolo indipendente, in ordine di rischio per la tesi** — la lista si e'
accorciata a tre voci, e nessuna delle tre e' un difetto:

1. `element_volumes` (`quality.py:258`) — tautologia per costruzione.
2. `extent`/`bbox` di `load_cloud` (`io.py:110-112`) — `max − min`, nessun terzo
   termine di paragone.
3. `mean_spacing` (`io.py:64`) — esercitata, mai confrontata con una spaziatura
   nota.

**Guardie inerti che restano:** `solve.py:563` e `solve.py:578`, entrambe
dichiarate tali nelle docstring.

**Il debito vero non e' piu' un difetto del codice, e' di censimento.** Cinque
grandezze entrate dopo il 26/08 non sono in questo inventario: `is_oriented`,
`scarto_con_segno`, `controlla_massa_modale`, Richardson/GCI di `convergenza.py`,
il registro di `soglie.py`. Finche' non ci sono, questo documento e' vero su cio'
che dice e muto su una parte di cio' che il programma calcola.

**Raccomandazione (non una decisione).** La divergenza `scaled_jacobian` contro
Verdict e' stata chiusa aggiungendo il nono punto, e la misura ha mostrato che
non sposta alcun numero pubblicato: il timore che l'aveva sconsigliata era
infondato, ed e' un precedente utile. Le due divergenze di nome che restano — N2
e N3 — **non si chiudono nel codice**: vanno dichiarate in tesi ogni volta che
una soglia presa da un manuale finisce accanto a uno di questi numeri.

## Fonti

- [Metrics for Hexahedral Elements — Cubit/Sandia](https://cubit.sandia.gov/files/cubit/15.8/help_manual/WebHelp/mesh_generation/mesh_quality_assessment/hexahedral_metrics.htm)
- [sandialabs/verdict — V_HexMetric.cpp](https://raw.githubusercontent.com/sandialabs/verdict/master/V_HexMetric.cpp)
- [Metrics for Tetrahedral Elements — Coreform Cubit](https://coreform.com/cubit_help/mesh_generation/mesh_quality_assessment/tetrahedral_metrics.htm)
- Stimpson, Knupp et al., *The Verdict Geometric Quality Library*, SAND2007-1751.
- Si, H. (2015), «TetGen, a Delaunay-Based Quality Tetrahedral Mesh Generator»,
  *ACM TOMS* 41(2):11.
