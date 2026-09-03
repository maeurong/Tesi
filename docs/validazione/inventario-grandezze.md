# Inventario delle grandezze calcolate, e di cosa le verifica

> **Nota del 03/09/2026.** Questo documento resta come è stato scritto. Descrive un
> programma di validazione costruito sul solutore integrato — `core/solve.py`,
> `core/convergenza.py`, il registro delle soglie `core/soglie.py` e i test
> NAFEMS, della mensola e della GCI — che è uscito per intero dal repository
> il 2-3 settembre 2026 con la mappa
> [#161](https://github.com/maeurong/Tesi/issues/161). Ciò che qui è al
> presente va letto al passato; resta il patch test. Quale validazione debba
> tornare, e con quali oracoli, è una domanda aperta della mappa
> [#33](https://github.com/maeurong/Tesi/issues/33).

**Verificato contro `main` a `a6e9f81`**, albero di lavoro pulito.

**I riferimenti al codice sono per nome, non per numero di riga.** Un nome non
slitta quando si fonde un ramo; un numero sì. La stesura del 27/08/2026 citava
`fed1872` per riga, e la fusione dei sette rami ne ha spostati 43 su un testo
diverso — non rotti, peggio: atterravano su una riga che *esiste* e dice
un'altra cosa. Dove un simbolo esiste si cita il simbolo
(`quality.mesh_volume`, `solve.controlla_reazioni`,
`test_quality.test_box_mesh_volume_is_exact_and_positive`); il numero resta solo
dove non c'è un simbolo da nominare, e allora porta il proprio commit accanto.

La stesura precedente ancora era misurata su un albero **sporco** a `a07071a`.
Fra quello e oggi, le PR #49-#121 hanno chiuso buona parte dei difetti che
questo documento registrava: la sezione 6 elenca voce per voce che cosa è
rimasto vero, che cosa è stato chiuso e da quale commit.

I riferimenti si ricontrollano a macchina — entrambe le forme:

    python docs/validazione/controlla-riferimenti.py docs/validazione/inventario-grandezze.md

Che un simbolo esista non dice che faccia ancora la cosa di cui il testo parla:
quello lo vede solo chi legge, ed è il lavoro che questa stesura ha rifatto.

Raccolta test su `a6e9f81`: **1350 casi**, di cui **50** marcati `validazione` e
**18** `feasibility`, entrambi esclusi dalla corsa predefinita (`addopts` in
`[tool.pytest.ini_options]` di `pyproject.toml`).

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

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `mesh_volume` | `quality.mesh_volume` | V = Σ_f (a·(b×c))/6 | mm³, + se normali uscenti | scatola esatta 100·40·200 — `test_quality.test_box_mesh_volume_is_exact_and_positive`, `test_quality.test_surface_metrics_on_a_closed_box` | **O** |
| area superficie | `quality.surface_metrics` | A = Σ_f ‖(b−a)×(c−a)‖/2 | mm², ≥0 | 2(100·40+100·200+40·200) analitico — `test_quality.test_surface_metrics_on_a_closed_box` | **O** |
| `is_watertight` | `quality.is_watertight` | ∀e: n(e)=2, **e almeno uno spigolo** | bool | scatola chiusa — `test_quality.test_box_mesh_is_watertight_and_has_no_boundary_edges`; bucata — `test_quality.test_punch_holes_opens_the_mesh` | **O** |
| `boundary_edges` | `quality.boundary_edges` | {e : n(e)=1} | conteggio | 4 spigoli dopo un buco — `test_quality.test_punch_holes_opens_the_mesh` | **O** |
| `triangle_aspect_ratios` | `quality.triangle_aspect_ratios` | AR = L_max/(2√3·r), r = 2A/Σℓ | adim., ≥1 | equilatero = 1 — `test_quality.test_aspect_ratio_of_an_equilateral_triangle_is_one`; sliver >100 — `test_quality.test_aspect_ratio_of_a_sliver_triangle_is_large` | **O** |

## Volume — tetraedri

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `tet_volumes` | `quality.tet_volumes` | V = (b−a)·((c−a)×(d−a))/6 | mm³, **con segno**, <0 = invertito | Σ = volume esatto scatola su output TetGen — `test_volume.test_sum_of_tet_volumes_equals_the_exact_volume` | **O** |
| `inverted_tets` | `quality.inverted_tets` | {i : ¬(finito(V_i) ∧ V_i > 0)} | indici | tet a orientazione scambiata — `test_quality.test_volume_metrics_flag_inverted_elements`; NaN e inf marcati — `test_cancello_finitezza.test_una_coordinata_non_finita_e_marcata_degenere` | **O** |
| `min_dihedral_angles` | `quality.min_dihedral_angles` | θ = min_{i<j} [180° − arccos(n̂_i·n̂_j)] | gradi, ∈[0,180] | tet regolare = arccos(1/3) = 70,5288° — `test_quality.test_regular_tetrahedron_has_the_textbook_dihedral_angle`; schiacciato <1° — `test_quality.test_flattened_tetrahedron_has_a_small_dihedral_angle` | **O** |
| `tet_aspect_ratios` | `quality.tet_aspect_ratios` | AR = L_max/(2√6·r), r = 3V/ΣA_f | adim., ≥1, ∞ se degenere | regolare = 1 — `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_regolare_vale_uno`; rettangolo (1+√3)/2 in forma chiusa — `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_rettangolo_ha_forma_chiusa`; degenere → ∞ — `test_oracoli_mancanti.test_l_aspetto_di_un_tetraedro_degenere_e_infinito` | **O** |
| `radius_edge_ratios` | `quality.radius_edge_ratios` | ρ = R_circ/L_min | adim., ≥√6/4 | tet regolare = √6/4 (rel 1e-9) — `test_quality.test_radius_edge_ratio_of_the_regular_tetrahedron`; schiacciato >10 — `test_quality.test_radius_edge_ratio_grows_on_a_flattened_tetrahedron`; complanare → ∞ — `test_quality.test_a_degenerate_tetrahedron_is_infinite_not_a_crash` | **O** |
| `fraction_over_ratio` | `quality.fraction_over_ratio` | #{ρ finito > limite}/#{ρ finito}; 1,0 se vuoto | ∈[0,1] | 0,0/1,0 costruiti — `test_quality.test_the_reference_fraction_does_not_depend_on_the_requested_min_ratio` | **O** |
| `radius_edge_ratio_p99` | `volume.tetrahedralize_with_metrics` | q₀,₉₉ dei ρ finiti; `None` se vuoto | adim. | è davvero un percentile: dentro il campo, ≥98% sotto, ≥√6/4 — `test_oracoli_mancanti.test_il_percentile_del_raggio_spigolo_e_davvero_un_percentile` | **O** |

## Volume — esaedri

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `hex_volumes` | `quality.hex_volumes` | V = Σ_{k=1..6} V_tet (ventaglio da 0 attorno alla diagonale 0–6) | mm³, con segno | cubo unitario = 1 — `test_quality.test_il_volume_di_un_cubo_unitario_vale_uno`; rovesciato <0 — `test_quality.test_il_volume_esaedrico_e_negativo_se_l_elemento_e_rovesciato` | **O** |
| `scaled_jacobian` | `quality.scaled_jacobian` | SJ = min su **nove** punti: gli 8 angoli, det(e₁,e₂,e₃)/(‖e₁‖‖e₂‖‖e₃‖), più il centro sugli assi principali medi; 0 se il prodotto è nullo | adim., ≤1 | cubo = 1 — `test_quality.test_lo_jacobiano_scalato_di_un_cubo_vale_uno`; angolo a 45° = 1/√2 in forma chiusa — `test_quality.test_lo_jacobiano_scalato_di_un_elemento_tagliato_vale_il_valore_atteso`; ripiegato <0 — `test_quality.test_lo_jacobiano_scalato_e_negativo_su_un_angolo_ripiegato` | **O**, e **coincide con Verdict** (§2) |
| `element_volumes` | `quality.element_volumes` | dispatch sul numero di colonne: 8→hex, 4 o 10→tet dei primi 4 | mm³ | concorda con `tet_volumes`/`hex_volumes` — `test_quality.test_il_volume_di_un_cubo_unitario_vale_uno`, `test_quality.test_element_volumes_sui_tetraedri_da_quello_che_dava_tet_volumes` | **R** (tautologia) |

## Errore geometrico, deviazione, spessore

| grandezza | dove | formula | unità/segno | oracolo | v |
|---|---|---|---|---|---|
| `geometric_error` | `quality.geometric_error` | delega a PyMeshLab `get_hausdorff_distance` nei due versi; `hausdorff` = max(max_c2m, max_m2c) | mm, ≥0 | nuvola campionata sulla mesh → piccolo (`test_quality.test_geometric_error_of_a_cloud_sampled_on_its_own_mesh_is_small`); traslata → cresce (`test_quality.test_geometric_error_grows_with_a_displaced_cloud`); coerenza con `vertex_deviation` rel 1e-5 (`test_quality.test_su_una_calotta_il_campionamento_dei_soli_vertici_sottostima_l_errore`) | **O** |
| `vertex_deviation` | `quality.vertex_deviation` | d_v = min_{p∈nuvola} ‖v − p‖ (cKDTree, k=1) | mm, ≥0 | 0 esatto sui punti + 0,25 noto fuori — `test_quality.test_la_deviazione_per_vertice_e_zero_sui_vertici_della_nuvola_e_nota_fuori`; scostamento 3,0 — `test_quality.test_la_deviazione_per_vertice_misura_lo_scostamento_noto`; RMS = 0,5 analitico — `test_quality.test_il_campo_per_vertice_resta_nell_ordine_di_grandezza_dell_aggregato` | **O** |
| `thickness` | `quality.thickness` | PCA 3×3 → asse di `ptp` minimo; istogramma a passo `bin_width`; s = c_upper − c_lower; `bimodal` ⟺ modi non contigui **e** mean(valle) < ½·min(picchi) | mm, >0 | lastra a spessore noto 176 mm ±3 — `test_quality.test_thickness_measures_the_distance_between_the_two_faces`; solido pieno → non valido — `test_quality.test_thickness_declares_itself_invalid_on_a_solid_without_two_faces` | **O** |
| `extent` (in `thickness`) | `quality.thickness` | ptp lungo l'autovettore minimo | mm | lastra allineata: 37,0 esatto — `test_oracoli_mancanti.test_l_ingombro_di_una_lastra_allineata_e_il_suo_spessore` | **O** |
| `_distribution` | `quality._distribution` | min/median/mean/max sui soli finiti + `non_finite` | come il campo | `None` invece di NaN, mediana 2,0 — `test_quality.test_a_summary_without_finite_values_stays_valid_json` | **O** |

## Ingresso e scala

| grandezza | dove | formula | unità | oracolo | v |
|---|---|---|---|---|---|
| `mean_spacing` | `io.mean_spacing` | mean(d₂) su campione casuale, d₂ = 2° vicino kd-tree | mm | 8 test in `test_io.py` | — |
| `scale` | `io.load_cloud` | p ← p · cfg.scale | fattore adim. → mm | `size_check` contro `expected_size`, nella stessa funzione — controllo, non test | **O** se l'utente dichiara le misure |
| `extent`/`bbox` | `io.load_cloud` | max − min per asse | mm | `test_io.py` | **R** |

## Deck e set di nodi (`abaqus.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `align_to_axes` | `abaqus.align_to_axes` | ẑ ≡ [0,0,1]; x̂ = fix_sign(autovettore di ptp minimo della PCA 2D orizzontale); ŷ = ẑ×x̂ | spessore su x / lunghezza su y / altezza su z su banco noto — `test_abaqus.test_alignment_puts_thickness_on_x_length_on_y_height_on_z` | **O** |
| `build_node_sets` | `abaqus.build_node_sets` | BASE: z ≤ z_min+t; TOP: z ≥ z_max−t; FACE_*: x; SIDE_*: y | sei facce di una scatola — `test_abaqus.test_node_sets_cover_the_six_faces_of_a_box`; chiavi = costante — `test_abaqus.test_build_node_sets_ha_le_chiavi_della_costante` | **O** per BASE/TOP; i nomi FACE_/SIDE_ restano convenzione, e la docstring lo dichiara |
| `boundary_faces` | `abaqus.boundary_faces` | facce con occorrenza singola dopo ordinamento indici; su 10 colonne usa i primi 4 vertici | 10 riferimenti in `test_abaqus.py` | **O** |
| `boundary_spacing` | `abaqus.boundary_spacing` | mediana ‖p_i − p_j‖ sugli spigoli unici delle facce di bordo | tetraedro regolare di lato 1 → 1 — `test_oracoli_mancanti.test_la_spaziatura_di_bordo_del_tetraedro_regolare_e_il_suo_lato`; scala col fattore 2 — `test_oracoli_mancanti.test_la_spaziatura_di_bordo_scala_con_la_geometria` | **O** |
| `set_tolerance` | `abaqus.set_tolerance` | t = factor · `boundary_spacing` | segue la spaziatura, non il volume elemento — `test_abaqus.test_the_tolerance_follows_the_boundary_spacing_not_the_element_volume` | **O** (relazione) |
| `footprint_coverage` | `abaqus.footprint_coverage` | celle di lato 4·spacing; colonna «a contatto» se z_min,col ≤ z_min+0,02·H | base piana → 1,0 (`test_abaqus.test_the_footprint_is_fully_covered_on_a_flat_base`); conta colonne, non nodi (`test_abaqus.test_the_coverage_counts_columns_of_the_footprint_not_nodes`) | **O** |
| `constraint_plan_extent` | `abaqus.constraint_plan_extent` | r_a = ptp(scelti_a)/ptp(tutti_a), a∈{x,y}; `minimo` = min | =1 su due piedi (`test_abaqus.test_l_estensione_in_pianta_del_vincolo_vale_uno_su_due_piedi`), crolla su un angolo (`test_abaqus.test_l_estensione_in_pianta_crolla_se_il_vincolo_tiene_un_angolo`, `test_abaqus.test_l_estensione_in_pianta_crolla_anche_quando_e_x_l_asse_stretto`) | **O** |
| `aree_tributarie` | `abaqus.aree_tributarie` | ventaglio dal 1° nodo; A_tri = ‖(p₁−p₀)×(p₂−p₀)‖/2; ⅓ a ciascuno | Σ = 100·40 calcolato a mano, **non** contro `surface_area` — `test_abaqus.test_le_aree_tributarie_sommano_all_area_della_superficie` | **O** |
| `surface_area` | `abaqus.surface_area` | = `aree_tributarie(...).sum()` | faccia di cubo unitario = 1 — `test_abaqus.test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta` | **O** |
| `ripartisci` | `abaqus.ripartisci` | q_i = R · A_i / ΣA | somma = risultante — `test_abaqus.test_la_ripartizione_pesata_conserva_la_risultante` | **O** |
| `coppia_equivalente` | `abaqus.coppia_equivalente` | separazione = fix_sign(1° vettore singolare di P_⊥asse); F = M/b_eff | **Σ F = 0 e M_z = 3000 ricalcolato dalle righe `*CLOAD` del deck** — `test_abaqus.test_la_coppia_realizza_il_momento_dichiarato` | **O** — il più forte del repo |
| `element_surface` | `abaqus.element_surface` | facce di bordo con **tutti** i nodi nel set | S1 del C3D8 + area = 1 — `test_abaqus.test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta`; 3 nodi su 4 → `[]` — `test_abaqus.test_la_superficie_di_elemento_non_nomina_una_faccia_solo_sfiorata` | **O** |
| `volume` / `mass` export | `abaqus.export_model` | V = Σ\|V_elem\|; m = V·ρ | scatola nota, rel 1e-6 — `test_oracoli_mancanti.test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola` | **O** |

## Soluzione (`solve.py`)

| grandezza | dove | formula | oracolo | v |
|---|---|---|---|---|
| `von_mises` | `solve.von_mises` | σ_vm = √{½[(σx−σy)²+(σy−σz)²+(σz−σx)²] + 3(τ²_xy+τ²_yz+τ²_zx)} | taglio puro = 5√3 (`test_solve.test_von_mises_di_uno_stato_di_taglio_puro`); trazione monoassiale = 7 (`test_solve.test_von_mises_di_una_trazione_monoassiale`) | **O**; **anche l'ordine delle colonne `.frd`** è verificato contro `ccx` vero (§1) |
| `_volume_totale` | `solve._volume_totale` | Σ \|V_tet(elements[:, :4])\| | dentro l'invariante di equilibrio | **O** indiretto |
| `_quota_tributaria_gravita` | `solve._quota_tributaria_gravita` | carichi consistenti: C3D4 ρ·V/4 ai vertici; C3D10 −1/20 ai vertici e +1/5 ai lati | **invariante fisico chiuso**: Σ RF_z + q·g = ρVg su un tetraedro, rel 1e-6 — `test_solve.test_somma_reazioni_su_un_tetraedro_piu_la_quota_tributaria_eguaglia_il_peso`; somma = massa su entrambi gli elementi — `test_solve.test_la_ripartizione_della_gravita_somma_al_peso_su_entrambi_gli_elementi` | **O** |
| `controlla_reazioni` | `solve.controlla_reazioni` | ε = ‖ΣRF − W‖/‖W‖; passa ⟺ isfinite(tol) ∧ ε ≤ tol | modulo giusto + direzione storta = bocciato — `test_solve.test_la_somma_delle_reazioni_smentisce_una_densita_sbagliata` | **O** |
| `controlla_autovalori` | `solve.controlla_autovalori` | passa ⟺ tutte finite ∧ f₁>0 ∧ f₁/f₂ ≥ 0,2 | 0,0004 Hz bocciato — `test_solve.test_un_autovalore_vicino_a_zero_e_un_meccanismo` | **O** |
| `controlla_picco` | `solve.controlla_picco` | p99 = percentile(v,99); frazione = #{v≥p99 ∧ q ≤ q_min+banda}/#{v≥p99} | costruito frazione = 1 → bocciato — `test_solve.test_il_picco_di_tensione_dentro_la_banda_di_vincolo_e_un_artefatto` | **O** |
| `controlla_vincolo_in_pianta` | `solve.controlla_vincolo_in_pianta` | passa ⟺ isfinite(m) ∧ m ≥ 0,5 | soglia di produzione su due casi noti — `test_solve.test_il_controllo_sul_vincolo_in_pianta_usa_la_soglia_di_produzione` | **O** |
| `controlla_avvisi` | `solve.controlla_avvisi` | passa ⟺ conteggio = 0 | tabella in `test_solve.py` | **O** |
| `u_max` | `solve._spostamento_massimo` | max_i ‖u_i‖ | aritmetica in forma chiusa sul `.frd` di prova: 3,6·√2 — `test_solve.test_risolvi_porta_il_sesto_verdetto_col_rapporto_calcolabile_a_mano` | **O** |
| `frequenze_hz` | `solve.leggi_frequenze` | colonna 4 (CYCLES/TIME) del blocco `MODE NO` | colonna giusta, non la prima — `test_solve.test_le_frequenze_sono_la_colonna_cycles_time_non_la_prima_dopo_il_modo` | **O** |

## Conversioni di unità

Sistema dichiarato **mm, N, MPa, t, s** (docstring di `config.py`). Una sola conversione
numerica:

- `config.GRAVITY_MM_S2` = 9810.0, usata come predefinito di
  `config.AnalysisConfig.gravity`. Asserita contro 9,81·1000 — `test_oracoli_mancanti.test_la_gravita_e_novecentootto_metri_al_secondo_quadro_in_millimetri`.
  → **O**
- ρ in t/mm³ (`config.Material.density`), E in MPa (`config.Material.young`). La coerenza ρ·V·g → N
  ha due oracoli: quello dimensionale chiuso di `test_solve.test_somma_reazioni_su_un_tetraedro_piu_la_quota_tributaria_eguaglia_il_peso` (ρ=1,8e-9,
  g=9810, V=1e6/6 → 2,943 N) e l'acqua a `test_oracoli_mancanti.test_densita_per_volume_per_gravita_da_newton`
  (1 t/m³ · 1 m³ · g = 9810 N).
- `io.load_cloud`, `points * cfg.scale`: unico punto di conversione ingresso→mm,
  difeso da `io.ScaleError`, non da un test di valore.
- il `/1000.0` di `viewport.decimate` è un ripiego per la dimensione voxel, non
  un'unità.

---

## 1. Grandezze senza oracolo indipendente

**Nessuna delle voci elencate qui il 26/08/2026 lo è ancora.** Le cinque
lacune sono state chiuse da `tests/test_oracoli_mancanti.py` (commit `aa2716f`),
e l'ordine delle colonne `.frd` da `tests/validazione/test_ordine_frd.py`
(commit `87c7d7c`). Il registro sta in §6.

Ciò che resta senza valore ancorato, e non è un difetto ma un limite
dichiarato:

- **`element_volumes`** (`quality.element_volumes`) — il dispatch è verificato contro
  `tet_volumes` e `hex_volumes`, cioè contro se stesso. È una tautologia per
  costruzione: la funzione **è** quel dispatch, e non c'è un terzo termine di
  paragone.
- **`extent`/`bbox_min`/`bbox_max` di `load_cloud`** (`io.load_cloud`) — solo
  regressione. Sono `max − min` per asse: un oracolo indipendente sarebbe la
  stessa formula scritta due volte.
- **`mean_spacing`** (`io.mean_spacing`) — otto test in `test_io.py` la esercitano,
  nessuno la confronta con una spaziatura nota per costruzione.

**Il punto sensibile che era il più grave, e non lo è più.** L'assunzione
**SXX,SYY,SZZ,SXY,SYZ,SZX** in `von_mises` (`solve.von_mises`) non è più assunta:
`tests/validazione/test_ordine_frd.py` impone sul bordo un campo di spostamento
lineare, che produce uno stato costante con **tutte e sei le componenti distinte
e ben separate**, e confronta le sei colonne lette dal `.frd` una per una con la
legge di Hooke. Un secondo test prova che **tutte e 719 le permutazioni** diverse
dall'identità verrebbero respinte, cioè che il confronto discrimina invece di
limitarsi a passare. Era il difetto D2 del registro; è chiuso.

## 2. Metriche col nome standard e formula diversa

**`scaled_jacobian` (`quality.scaled_jacobian`) — oggi COINCIDE con Verdict/Sandia.**
Verdict `hex_scaled_jacobian` prende il minimo su **9** punti: gli 8 angoli più
il centro, dove usa gli assi principali medi (`calc_hex_efg`) e non tre spigoli.
Fino a `0a622a5` questa funzione prendeva il minimo su **8**, e dava quindi un
valore sistematicamente **più ottimistico**. Il nono punto ora c'è in
`quality.scaled_jacobian`, accanto agli otto angoli, e la docstring lo
dichiara. Il costo era nullo e misurato: **nessun numero già
pubblicato si è spostato**. La metà che gira in albero è
`test_guardie_e_nomi.test_su_magli_veri_il_nono_punto_non_sposta_nulla`, su duecento esaedri; le cifre più grandi — zero
scarto su 1644 esaedri di tre prismi gmsh e su 148.689 cubi perturbati a caso —
sono state **misurate una volta il 26/08/2026 fuori dall'albero, nel giro di
`0a622a5`, e non sono riproducibili qui**: nessuno script le genera. La tabella `_ANGOLI_ESAEDRO`
(`quality._ANGOLI_ESAEDRO`) coincide angolo per angolo con Verdict.
*Nota di staleness:* la doc Cubit 15.8 dice «8 corner nodes only», il sorgente
`sandialabs/verdict` dice 9 — **il sorgente vince**, e la docstring lo scrive.

**`tet_aspect_ratios` (`quality.tet_aspect_ratios`) — coincide** con Verdict/VTK
`L_max/(2√6·r_in)` (=1 sul tet regolare). **Ma non** con `Aspect Ratio Beta`
(= R_circ/(3·r_in)) né `Aspect Ratio Gamma` (= S_rms³/(8,479670·V)) di Cubit —
**e non con Abaqus/CAE, dove «aspect ratio» è spigolo massimo su spigolo minimo**,
che Verdict chiama `edge ratio`. Sul tetraedro rettangolo di lato 1 questa vale
(1+√3)/2 = 1,366 e quella di Abaqus √2 = 1,414. La divergenza ora è scritta
nella docstring della funzione e nel registro delle soglie, non solo qui: chi
cita «aspect ratio» accanto a una soglia presa da un manuale **deve dire quale
definizione è**.

**`triangle_aspect_ratios` (`quality.triangle_aspect_ratios`) — coincide** con Verdict,
`L_max/(2√3·r_in)`. *(Caveat invariato: verificato per analogia con la tet, non
aprendo il sorgente Verdict del triangolo.)*

**`radius_edge_ratios` (`quality.radius_edge_ratios`)** — non è una metrica Verdict, è la
grandezza di **TetGen** (`-q`, `minratio`), √6/4 = 0,6124 sul regolare. Coerente
col nome. **Ma: il default `-q` di TetGen impone radius-edge ≤ 2,0 e angolo
diedro minimo 0° — nessun vincolo sugli sliver. Il radius-edge ratio è cieco agli
sliver per costruzione**, e la docstring lo misura: quattro punti sfalsati di un
millesimo attorno a una circonferenza danno raggio-spigolo **0,707**, cioè sotto
il limite, e diedro minimo **0,162°**. Per quelli serve il **minimum dihedral
angle**, che il progetto calcola (`quality.min_dihedral_angles`) ma non usa come vincolo.
Fonte: manuale TetGen 1.5 e Si 2015, ACM TOMS 41(2):11.

**`min_dihedral_angles`** e **`von_mises`** — definizioni standard, nessuna
divergenza. Range accettabile Verdict per il diedro minimo del tet: **[40°,
70,53°]**.

**`hex_volumes` (`quality.hex_volumes`)** — la docstring lo dichiara (`quality.hex_volumes`):
**non** è la quadratura di Gauss dell'esaedro trilineare che Abaqus/CalculiX usano
per integrare l'elemento. È il volume del solido a facce triangolate. Su facce non
piane i due numeri differiscono. Scelta consapevole e documentata, da citare come
tale se il volume finisce in tesi accanto a una massa del solutore.

## 3. Guardie che non possono fallire

**Due delle tre voci non esistono più.**

1. **Ramo modi adiacenti in `thickness`** — era `valley = float(counts[lower])`
   con `valley < 0.5·min(counts[lower], counts[upper])`, **falsa per
   costruzione**. Chiusa da `0a622a5`: la condizione ora è scritta come esito e
   non come calcolo, `upper > lower + 1 and mean(valle) < ...`
   (`quality.thickness`), e il commento sopra dice perché la forma precedente
   non poteva dare `True`. Due modi in bin contigui restano `bimodal=False`, ma
   ora perché è **dichiarato**, non perché un confronto impossibile fallisce.
2. **`footprint_coverage`, nessuna colonna a contatto** — era `return 0.0`,
   irraggiungibile su qualunque mesh chiusa. Chiusa da `0a622a5`: ora
   **solleva** (`abaqus.footprint_coverage`), e il commento spiega che quello zero si
   sarebbe letto come «l'insieme non copre nulla», condizione vera e diversa.
   Il ramo resta irraggiungibile dalla pipeline; ciò che è cambiato è che
   adesso, se ci si arriva, si sa.
3. **`np.isfinite(minimo)` in `solve.controlla_vincolo_in_pianta`** e
   **`conteggio == 0` con NaN in `solve.controlla_avvisi`** — restano inerti **per progetto e dichiarate tali** nelle rispettive
   docstring: la seconda dice esplicitamente che l'uguaglianza a zero è già
   chiusa su NaN e sugli infiniti, e che sta nella tabella dei sette verdetti
   perché enumerarli tutti costa meno che ricordare quale non serviva. Non un
   difetto, ma nemmeno una difesa.

**Guardie che invece scattano davvero** (verificate), ciascuna col proprio
avviso o errore: `volume.TruncatedRefinementWarning`, saturazione Steiner
(`test_volume.test_an_exhausted_steiner_budget_is_reported_not_hidden`);
`volume.IneffectiveVolumeLimitWarning`, limite di volume disatteso
(`test_volume.test_nobisect_can_make_the_volume_limit_inert_and_says_so`);
`volume.UnmetQualityConstraintWarning`, vincolo raggio-spigolo
(`test_volume.test_a_mesh_the_constraint_does_not_govern_is_reported`);
`abaqus.UnconstrainedModelWarning`
(`test_abaqus.test_export_warns_when_the_constrained_set_misses_the_footprint`);
`abaqus.SelettoreIsotropoWarning`
(`test_abaqus.test_un_selettore_quadrato_avvisa_che_la_direzione_non_e_determinata`);
determinante ≠ +1 in `solve._rotazione_ai_punti`
(`test_solve.test_una_rotazione_con_determinante_diverso_da_uno_non_si_applica`).

## 4. Ingressi degeneri

**Il buco che era il più grave è chiuso.** Le coordinate NaN non passano più
la guardia di inversione: `inverted_tets` (`quality.inverted_tets`) è scritta in
positivo, `~(isfinite(V) & (V > 0))`, e il controllo di finitezza copre anche la
metà che `not (V > 0)` da solo non coprirebbe — un volume `+inf` è maggiore di
zero e passerebbe. `hexa_metrics` usa la stessa forma (`quality.hexa_metrics`), e gli
scalari che uscivano `NaN` in JSON passano ora per `finito_o_none`
(`quality.finito_o_none`), che rende `None`. La copertura sta in
`tests/test_cancello_finitezza.py`.

La tabella qui sotto **non è rimisurata eseguendo il codice**: questo giro non
aveva un ambiente con numpy separato da quello condiviso. Ogni riga porta quindi
la propria fonte — una guardia esplicita nel sorgente, o un test che la fissa —
e le righe che dipendevano da un comportamento di numpy senza una guardia che lo
scriva sono marcate **da rimisurare**.

| ingresso | esito | fonte | giudizio |
|---|---|---|---|
| mesh vuota → `is_watertight` | **`False`** | guardia `quality.is_watertight` | chiuso: era `True`, e `volume.tetrahedralize` la passava a TetGen. Ora la rifiuta per prima |
| mesh vuota → `mesh_volume`, `surface_metrics`, `volume_metrics`, `hexa_metrics` | `0,0`, `min/median/mean/max = None` | `quality._distribution` | gestito |
| tet complanare (V=0) → `inverted_tets` | marcato | `quality.inverted_tets` (`0.0 > 0.0` è falso) | gestito |
| tet complanare → aspetto / diedro / raggio-spigolo | ∞ / ~0° / ∞ | `test_oracoli_mancanti.test_l_aspetto_di_un_tetraedro_degenere_e_infinito`, `test_quality.test_flattened_tetrahedron_has_a_small_dihedral_angle`, `test_quality.test_a_degenerate_tetrahedron_is_infinite_not_a_crash` | gestito, mai eccezione |
| hex con nodi NaN → `scaled_jacobian` | `0,0` | guardia `where=prodotto > 0.0` in `quality.scaled_jacobian`, sugli angoli e sul centro | gestito |
| hex con nodi inf → `hexa_metrics["inverted"]` | contato | `quality.hexa_metrics` | chiuso: il vecchio `jacobiani <= 0.0` ne contava **zero** |
| nuvola a **1 punto** → `vertex_deviation` | array di zeri | — | **da rimisurare**: nessuna guardia lo scrive e nessun test lo fissa |
| nuvola **vuota** → `vertex_deviation` | **`ValueError`** | guardia `quality.vertex_deviation` | chiuso: erano `[inf, inf, inf]` nella mappa colore |
| nuvola < 2 punti → `thickness` | `{thickness: None, bimodal: False}` | guardia `quality.thickness` | gestito |
| array vuoto → `controlla_picco` | **`ValueError` col proprio messaggio** | guardia `solve.controlla_picco` | chiuso: era `zero-size array to reduction operation maximum` |
| nodi vuoti → `build_node_sets` | **`ValueError` col proprio messaggio** | guardia `abaqus.build_node_sets` | chiuso: era `zero-size array to reduction operation minimum` |
| nodi non finiti → `build_node_sets` | **`ValueError`** | guardia `abaqus.build_node_sets` | chiuso: i due set dell'asse uscivano **vuoti** senza che nulla protestasse |
| indici vuoti → `constraint_plan_extent` | `{x:0, y:0, minimo:0}` | `abaqus.constraint_plan_extent` | gestito, il verdetto boccia |
| elementi vuoti → `boundary_faces` | shape `(0,3)` | — | **da rimisurare** |
| elemento a **10 nodi** → `element_volumes` | calcola sui primi 4 | `quality.element_volumes` | **non è più un ramo morto**: `NODI_PER_ELEMENTO` (`abaqus.NODI_PER_ELEMENTO`) contiene di nuovo `C3D10` dopo `76bbc00`, e `boundary_faces` (`abaqus.boundary_faces`) tratta le dieci colonne come tetraedro |
| elemento a 6 nodi → `boundary_faces` | **`ValueError`** | `abaqus.boundary_faces`, `test_abaqus.test_boundary_faces_rifiuta_un_numero_di_nodi_sconosciuto` | gestito |
| tensioni vuote → `von_mises` | array vuoto | — | **da rimisurare** |

**Non verificato in questa sessione:** mesh non chiusa passata a
`geometric_error` / `thickness` (richiede PyMeshLab); elemento esaedrico passato a
`solve._volume_totale`, che userebbe `elements[:, :4]` senza dirlo — la docstring
(`solve._volume_totale`) ammette il limite e dichiara zero copertura sul ramo.

## 5. Conteggio test

- Raccolti su `a6e9f81`: **1350 casi**, di cui **50** marcati `validazione` e
  **18** `feasibility`. Entrambi i marcatori sono esclusi dalla corsa
  predefinita (`addopts` in `[tool.pytest.ini_options]` di `pyproject.toml`).
- Funzioni `test_*` di modulo, prima della parametrizzazione:
  **1168** — `grep -rh "^def test_" tests/ --include="*.py" | wc -l` da
  `meshrec/`.
- **Rimosso**, e vale la pena dire perché: la stesura precedente riportava
  «153 su 892 nominano almeno una delle 47 funzioni di calcolo, ≈17%», con un
  caveat che lo dichiarava insieme limite inferiore e limite superiore. Un
  numero che non regge una conclusione in nessuna delle due direzioni, e che
  nessun comando scritto da qualche parte permetteva di rifare, non è una
  misura: è un'impressione con tre cifre. I conteggi che restano hanno il
  comando accanto.

---

## 6. Che cosa è cambiato dal 26/08/2026

Ogni voce della stesura precedente, con il proprio esito su `fed1872`. Le sigle
D/O/G/N sono quelle del registro in [`README.md`](README.md) §3.

| voce | stato | dove |
|---|---|---|
| D1 — `inverted_tets` filtra con `V <= 0.0`, NaN passa | **chiusa** (`757429c`, `69465e1`) | `quality.inverted_tets`, `tests/test_cancello_finitezza.py` |
| D2 — ordine colonne `.frd` mai verificato contro `ccx` | **chiusa** (`87c7d7c`) | `solve.von_mises`, `tests/validazione/test_ordine_frd.py` |
| D3 — `controlla_reazioni` confronta `RF` col peso, ma sotto gravità `RF` non è la sola reazione | **ancora vera**, e gestita: `risolvi` somma la quota tributaria prima del confronto | `solve._quota_tributaria_gravita`, `test_solve.test_somma_reazioni_su_un_tetraedro_piu_la_quota_tributaria_eguaglia_il_peso` |
| D4 — nessuna guardia sull'ampiezza degli spostamenti | **chiusa** (`c8d9084`) | `solve.controlla_spostamenti` |
| D5 — `vertex_deviation` su nuvola vuota rende `[inf, inf, inf]` | **chiusa** | `quality.vertex_deviation` |
| D6 — `build_node_sets` su nodi vuoti solleva `ValueError` grezzo | **chiusa** | `abaqus.build_node_sets` |
| D7 — `controlla_picco` su array vuoto solleva `ValueError` grezzo | **chiusa** (`587d138`) | `solve.controlla_picco` |
| D8 — `element_volumes` accetta 10 colonne ma C3D10 non esiste più | **falsa oggi**: C3D10 è stato ripristinato (`76bbc00`, `479d671`) | `abaqus.NODI_PER_ELEMENTO`, `quality.element_volumes` |
| O1 — `tet_aspect_ratios` senza alcun test | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_regolare_vale_uno`, `test_oracoli_mancanti.test_l_aspetto_del_tetraedro_rettangolo_ha_forma_chiusa`, `test_oracoli_mancanti.test_l_aspetto_di_un_tetraedro_degenere_e_infinito` |
| O2 — `boundary_spacing` senza chiamate dirette | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.test_la_spaziatura_di_bordo_del_tetraedro_regolare_e_il_suo_lato`, `test_oracoli_mancanti.test_la_spaziatura_di_bordo_scala_con_la_geometria` |
| O3 — `export["volume"]`/`export["mass"]` senza asserzione di valore | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola` |
| O4 — `GRAVITY_MM_S2` che nessun test asserisce | **chiusa** (`aa2716f`) | `test_oracoli_mancanti.test_la_gravita_e_novecentootto_metri_al_secondo_quadro_in_millimetri`, `test_oracoli_mancanti.test_densita_per_volume_per_gravita_da_newton` |
| O5 — `radius_edge_ratio_p99`, `extent` di `thickness`, `u_max`, ingombro/bbox | **chiusa in parte**: p99 ed `extent` hanno ora un oracolo, `u_max` ce l'ha in forma chiusa; ingombro/bbox resta **R** | `test_oracoli_mancanti.test_l_ingombro_di_una_lastra_allineata_e_il_suo_spessore`, `test_oracoli_mancanti.test_il_percentile_del_raggio_spigolo_e_davvero_un_percentile`, `test_solve.test_risolvi_porta_il_sesto_verdetto_col_rapporto_calcolabile_a_mano` |
| G1 — `bimodal` coi modi in bin contigui, falsa per costruzione | **chiusa** (`0a622a5`) | `quality.thickness` |
| G2 — `if not in_contact.any(): return 0.0` irraggiungibile | **chiusa** (`0a622a5`): ora solleva | `abaqus.footprint_coverage` |
| G3 — `isfinite(minimo)` e `conteggio == 0` inerti per progetto | **ancora vera**, e dichiarata | `solve.controlla_vincolo_in_pianta`, `solve.controlla_avvisi` |
| N1 — `scaled_jacobian` su 8 punti, diverge da Verdict | **chiusa** (`0a622a5`): nove punti, centro compreso | `quality.scaled_jacobian` |
| N2 — «aspect ratio» del tet non è quello di Abaqus | **ancora vera**, e ora dichiarata nella docstring | `quality.tet_aspect_ratios` |
| N3 — raggio-spigolo cieco agli sliver | **ancora vera**, e ora misurata nella docstring | `quality.radius_edge_ratios` |
| N4 — `hex_volumes` non è la quadratura di Gauss | **ancora vera**, già dichiarata | `quality.hex_volumes` |
| §4 — mesh vuota «chiusa», passata a TetGen | **chiusa** | `quality.is_watertight`, `volume.tetrahedralize` |
| §5 — «1019 su 1035 raccolti» | **scaduta**: 1350 casi su `a6e9f81` | `addopts` in `[tool.pytest.ini_options]` di `pyproject.toml` |

**Nessuna voce è risultata falsa già al 26/08/2026.** Tutte erano vere quando
scritte; sedici PR le hanno superate in due giorni, e il documento non se n'era
accorto perché nulla lo obbligava a farlo. Ora
`docs/validazione/controlla-riferimenti.py` obbliga almeno i puntatori.

## Il materiale che conta

**Senza oracolo indipendente, in ordine di rischio per la tesi** — la lista si è
accorciata a tre voci, e nessuna delle tre è un difetto:

1. `element_volumes` (`quality.element_volumes`) — tautologia per costruzione.
2. `extent`/`bbox` di `load_cloud` (`io.load_cloud`) — `max − min`, nessun terzo
   termine di paragone.
3. `mean_spacing` (`io.mean_spacing`) — esercitata, mai confrontata con una spaziatura
   nota.

**Guardie inerti che restano:** `solve.controlla_vincolo_in_pianta` e
`solve.controlla_avvisi`, entrambe dichiarate tali nelle docstring.

**Il debito vero non è più un difetto del codice, è di censimento.** Cinque
grandezze entrate dopo il 26/08 non sono in questo inventario: `is_oriented`,
`scarto_con_segno`, `controlla_massa_modale`, Richardson/GCI di `convergenza.py`,
il registro di `soglie.py`. Finché non ci sono, questo documento è vero su ciò
che dice e muto su una parte di ciò che il programma calcola.

**Raccomandazione (non una decisione).** La divergenza `scaled_jacobian` contro
Verdict è stata chiusa aggiungendo il nono punto, e la misura ha mostrato che
non sposta alcun numero pubblicato: il timore che l'aveva sconsigliata era
infondato, ed è un precedente utile. Le due divergenze di nome che restano — N2
e N3 — **non si chiudono nel codice**: vanno dichiarate in tesi ogni volta che
una soglia presa da un manuale finisce accanto a uno di questi numeri.

## Fonti

- [Metrics for Hexahedral Elements — Cubit/Sandia](https://cubit.sandia.gov/files/cubit/15.8/help_manual/WebHelp/mesh_generation/mesh_quality_assessment/hexahedral_metrics.htm)
- [sandialabs/verdict — V_HexMetric.cpp](https://raw.githubusercontent.com/sandialabs/verdict/master/V_HexMetric.cpp)
- [Metrics for Tetrahedral Elements — Coreform Cubit](https://coreform.com/cubit_help/mesh_generation/mesh_quality_assessment/tetrahedral_metrics.htm)
- Stimpson, Knupp et al., *The Verdict Geometric Quality Library*, SAND2007-1751.
- Si, H. (2015), «TetGen, a Delaunay-Based Quality Tetrahedral Mesh Generator»,
  *ACM TOMS* 41(2):11.
