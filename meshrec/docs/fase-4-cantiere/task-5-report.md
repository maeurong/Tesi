# Task 5 — Rapporto: `*SURFACE, TYPE=ELEMENT`, `*TIE` e carico laterale

## Stato
DONE.

## File toccati

- `meshrec/src/meshrec/core/abaqus.py`
  - Aggiunta `FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]]` subito dopo `FACCE_TOPOLOGICHE`, con il commento che ne distingue esplicitamente lo scopo (ordine del solutore, non insieme per il bordo).
  - Aggiunte `element_surface(elements, indici_nodo, element_type) -> list[tuple[int, int]]` e `surface_area(nodes, elements, superficie, element_type) -> float`.
  - `write_inp`: aggiunti i tre parametri opzionali `element_surfaces`, `ties`, `pressure`; validazione che ogni superficie nominata da un `*TIE` o da `pressure` sia fra quelle dichiarate (altrimenti `ValueError`); scrittura delle card `*SURFACE, TYPE=ELEMENT`, `*TIE, ADJUST=NO` (dopo gli `*NSET`, prima di `*SOLID SECTION`) e `*DSLOAD` (dopo la card `*DLOAD` della gravita', dentro lo step); docstring aggiornata.
- `meshrec/tests/test_abaqus.py`
  - Aggiunti i 7 test dello Step 1 del brief, in coda al file, verbatim.

Nessun altro file toccato. Nessuna nuova dipendenza.

## Ciclo TDD

1. Aggiunti i test (Step 1) — invariati rispetto al brief, gia' verificati a mano contro la geometria del cubo prima di scriverli (vedi sotto).
2. `uv run pytest tests/test_abaqus.py -k "faccia or superficie or tie or carico or pressione" -v`
   Esito: 6 falliti (i 6 nuovi che richiedono `FACCE_DEL_SOLUTORE`/`element_surface`), 2 passati (uno preesistente sul bordo dell'esaedro, e il test "senza pressione" che passa gia' perche' oggi `write_inp` non scrive ne' `*DSLOAD` ne' `*SURFACE` ne' `*TIE`). Fallimento con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'FACCE_DEL_SOLUTORE'` per i primi due, `AttributeError: ... 'element_surface'` per gli altri quattro — motivo atteso dal brief.
3. Implementazione (Step 3-4), come da brief.
4. `uv run pytest tests/test_abaqus.py -v` → **37 passed**.
5. `uv run pytest tests -q --ignore=tests/feasibility` → **461 passed, 1 warning** (warning preesistente e non correlato, in `test_volume.py`). 454 di base + 7 nuovi = 461, coerente.

## Verifica indipendente della tabella `FACCE_DEL_SOLUTORE`

Prima di implementare ho verificato a mano che le sei/quattro facce nominate da `FACCE_DEL_SOLUTORE[8]` e `FACCE_DEL_SOLUTORE[4]`, ridotte a insiemi di nodi ordinati, coincidano esattamente con quelle di `FACCE_TOPOLOGICHE[8]`/`FACCE_TOPOLOGICHE[4]` (stessi sei/quattro insiemi, nessuna ripetizione, nessuna diagonale). I test stessi fanno lo stesso confronto in automatico contro `boundary_faces`, che e' indipendente dalla tabella nuova.

Non ho usato CalculiX per una controprova risolta: il brief la definisce facoltativa qui e di competenza del Task 11. Il test `test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta` e il suo complementare "faccia solo sfiorata" gia' offrono una verifica indipendente dalla tabella (area calcolata sulle facce vs area attesa), quindi non ho ritenuto necessario aggiungere un deck feasibility per questo task.

## Vincolo del deck invariato — confronto byte per byte

Generato lo stesso deck (stesso muro sintetico `100.0, 40.0, 200.0`, stesso `TetConfig()` di default, nessuna superficie/`*TIE`/pressione) con il codice **prima** del commit e con quello **dopo**:

```
uv run python -c "... abaqus.write_inp(...) ..."   # prima: /tmp/deck_prima.inp
uv run python -c "... abaqus.write_inp(...) ..."   # dopo:  /tmp/deck_dopo.inp
cmp /tmp/deck_prima.inp /tmp/deck_dopo.inp
```

Esito: `cmp` non riporta differenze — **IDENTICI byte per byte**. Non ho toccato `meshrec/runs/*` (di sola lettura): il confronto usa il generatore sintetico gia' presente nella suite, che e' lo stesso metodo usato dal Task 4.

## Scelte prese

- Nessuna deviazione dal codice del brief: gia' verificato a mano che la tabella fosse corretta prima di scriverla, quindi implementazione diretta senza varianti.
- `element_surface`/`surface_area` messe subito dopo `FACCE_DEL_SOLUTORE`, prima di `boundary_faces`, seguendo l'ordine indicato dal brief (sotto `FACCE_TOPOLOGICHE`). `NODI_PER_ELEMENTO`, da cui dipendono, e' gia' definito sopra nel file: nessun problema di ordine di definizione.
- Le tre card nuove (`*SURFACE`, `*TIE`, `*DSLOAD`) sono scritte solo se i rispettivi argomenti sono forniti: verificato dal test "senza carico laterale" che nessuna delle tre compare quando gli argomenti sono assenti.

## Subagenti

Nessuno dispacciato (istruzione esplicita: "Non dispacciare subagenti").

## Aree segnalate a security-reviewer

Nessuna: nessun input esterno non fidato, nessuna auth, nessun dato sensibile toccato.

---

## Correzione post-review — RULING M e RULING N

La review ha bocciato la consegna sopra: il confronto per insiemi fra `FACCE_DEL_SOLUTORE` e `boundary_faces` non distingue uno scambio di etichette (due etichette scambiate nominano lo stesso insieme di nodi), e la verifica di area era circolare (rilegge la riga che `element_surface` ha gia' usato). Misurato per mutazione dal revisore: scambio S2/S4 dell'esaedro e permutazione completa del tetraedro, **entrambi 461 passati, 0 falliti**. Inoltre `element_surface` non filtrava le facce interne condivise fra elementi adiacenti (RULING N).

### RULING N — `element_surface` includeva facce interne

**File:** `meshrec/src/meshrec/core/abaqus.py`

**Test prima (rosso):** `test_la_superficie_di_elemento_non_include_una_faccia_interna_condivisa` in `tests/test_abaqus.py`, su due esaedri affiancati che condividono una faccia, con tutti i 12 nodi nell'insieme. Atteso 10 coppie (6+6 meno la condivisa contata due volte).

```
FAILED tests/test_abaqus.py::test_la_superficie_di_elemento_non_include_una_faccia_interna_condivisa
AssertionError: sei piu' sei meno la faccia condivisa contata due volte
assert 12 == 10
```

**Correzione:** `element_surface` ora calcola, per ogni faccia di ogni elemento, l'occorrenza globale (stesso principio di `boundary_faces`: indici ordinati, contati, tenute solo le occorrenze singole) e la incrocia con l'appartenenza all'insieme dato. Una faccia condivisa, comparendo due volte nella tabella, non e' mai di bordo e non entra piu' nella superficie qualunque sia l'insieme di nodi.

**Dopo:** `test_la_superficie_di_elemento_non_include_una_faccia_interna_condivisa` verde; tutti gli usi esistenti (nessun chiamante ancora in produzione) restano corretti perche' su un elemento isolato ogni faccia e' gia' di bordo.

### RULING M(a) — test per riga sui baricentri

**File:** `meshrec/tests/test_abaqus.py`

Aggiunti `test_ogni_etichetta_di_faccia_dell_esaedro_nomina_il_baricentro_giusto` e `test_ogni_etichetta_di_faccia_del_tetraedro_nomina_il_baricentro_giusto`. Per ciascuna delle sei/quattro righe della tabella, il baricentro atteso e' calcolato dalla geometria in modo indipendente dalla tabella:
- esaedro: parallelepipedo asimmetrico (`2.0 x 3.0 x 5.0`, non un cubo, per evitare baricentri troppo simili fra facce diverse); il baricentro atteso di ciascun S e' quello della faccia coordinata corrispondente (z minimo/massimo, y minimo/massimo, x minimo/massimo), dedotto dalla stessa convenzione del manuale gia' scritta nel commento della tabella;
- tetraedro: tetraedro asimmetrico a spigoli retti; il baricentro atteso di ciascun S esclude un vertice preciso (S1 il quarto, S2 il terzo, S3 il primo, S4 il secondo), dedotto direttamente dalla notazione del manuale (`S1=1-2-3, S2=1-4-2, S3=2-4-3, S4=3-4-1`), non dalla tabella `FACCE_DEL_SOLUTORE`.

Questi due test erano gia' verdi alla prima esecuzione: la tabella non e' stata toccata, era gia' corretta (verificato anche a mano prima di scriverla, vedi sopra). Non c'era un bug di implementazione da correggere qui — il valore aggiunto e' la protezione da regressione che il confronto per insiemi non dava.

**Mutazione 1 — scambio S2/S4 dell'esaedro**, per dimostrare che il test ora oppone resistenza dove il confronto per insiemi non lo faceva:

```
8: (
    (0, 1, 2, 3), (1, 5, 6, 2), (0, 4, 5, 1),
    (4, 7, 6, 5), (2, 6, 7, 3), (3, 7, 4, 0),
),
```

```
$ uv run pytest tests/test_abaqus.py -k baricentro -v
FAILED tests/test_abaqus.py::test_ogni_etichetta_di_faccia_dell_esaedro_nomina_il_baricentro_giusto
AssertionError: S2 non e' la faccia attesa
assert array([2. , 1.5, 2.5]) == approx([1.0 ± 1.0e-06, 1.5 ± 1.5e-06, 0.0 ± 5.0e-06])
```

**Mutazione 2 — permutazione completa delle quattro righe del tetraedro:**

```
4: ((1, 3, 2), (2, 3, 0), (0, 1, 2), (0, 3, 1)),
```

```
$ uv run pytest tests/test_abaqus.py -k "baricentro or etichette" -v
tests/test_abaqus.py::test_le_sei_etichette_di_faccia_di_un_esaedro_sono_le_sue_sei_facce PASSED
tests/test_abaqus.py::test_le_quattro_etichette_di_faccia_di_un_tetraedro_sono_le_sue_quattro_facce PASSED
tests/test_abaqus.py::test_ogni_etichetta_di_faccia_dell_esaedro_nomina_il_baricentro_giusto PASSED
tests/test_abaqus.py::test_ogni_etichetta_di_faccia_del_tetraedro_nomina_il_baricentro_giusto FAILED
AssertionError: S1 non e' la faccia attesa
```

In entrambi i casi i test "per insiemi" (`test_le_sei/quattro_etichette_...`, quelli scritti nel brief originale) **restano verdi**, confermando esattamente la misura del revisore: il confronto per insiemi non vede una permutazione. Dopo ogni mutazione ho ripristinato `abaqus.py` da una copia (`diff` vuoto verificato) e confermato `uv run pytest tests -q --ignore=tests/feasibility` di nuovo verde.

### RULING M(b) — controprova risolta con `ccx`

**File:** `meshrec/tests/feasibility/test_calculix.py` (nuovo test in coda al file esistente, marcato `pytestmark = pytest.mark.feasibility` come gli altri).

`test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra`: un solo esaedro C3D8I (`100 x 60 x 150` mm), `BASE` incastrata (z=0), densita' trascurabile (`1e-12`, `Material` non accetta zero) per isolare l'effetto della pressione dal peso proprio, pressione `2.0` MPa su `element_surface(..., [1,2,5,6], "C3D8I")` — verificato che quella chiamata restituisca `[(0, 4)]`, cioe' S4. Risolto con `ccx`, poi confrontato lo spostamento in x dei nodi in sommita' sul lato caricato (x=100) contro quello dei nodi sul lato opposto (x=0).

Eseguito con `uv run python` (fuori da pytest, stesso deck del test) per catturare i valori:

```
returncode: 0
superficie: [(0, 4)]
ux_caricato (x=100, S4): -1.410074
ux_non_caricato (x=0): -1.310074
```

Il lato caricato si sposta verso `-x` (compressione, coerente con la convenzione Abaqus/CalculiX per cui una pressione positiva spinge verso l'interno) e piu' del lato opposto: la faccia che si muove e' quella fisica a x massimo, non un'altra. **Nessuna anomalia trovata**: la tabella non e' stata toccata da questa verifica, non c'era nulla da correggere qui — la controprova ha confermato la mappatura, non l'ha smentita.

```
$ uv run pytest tests/feasibility -q -m feasibility
6 passed, 1 skipped
```

(il saltato e' `test_gmsh_meshes_and_optimizes_a_box`, preesistente, indipendente da questo task — dipende dalla disponibilita' del modulo `gmsh` nell'ambiente).

### Vincolo del deck — riverificato senza riusare l'esito precedente

**File temporaneo:** `/tmp/deck_prima.inp`, generato per la prima consegna, e' risultato **sovrascritto da un processo estraneo** fra una chiamata Bash e l'altra (nome generico su `/tmp`, condiviso sulla macchina): non era piu' il deck che credevo di confrontare (conteneva un tetraedro unitario di quattro nodi, non il muro sintetico `100x40x200`). Falso allarme individuato subito dal contenuto, non una regressione introdotta dalle correzioni.

Ripetuta la verifica con un metodo piu' robusto: un solo script Python, in un solo processo, che carica il codice di `abaqus.py` al commit `e2c1d7d` (l'ultimo prima del Task 5) tramite `git show` + `importlib`, genera il deck con quel codice e con quello attuale nella stessa esecuzione, in una directory temporanea dedicata (`tempfile.mkdtemp`), e confronta i byte in memoria — nessun file dal nome generico riusabile da altri processi.

```
$ uv run python /tmp/task5_verify_deck.py
bytes prima: 1860 bytes dopo: 1860
IDENTICI byte per byte
```

### Suite finale

```
$ uv run pytest tests -q --ignore=tests/feasibility
464 passed, 1 warning in 33.96s
```

(454 di base + 7 del Task 5 + 3 di questa correzione = 464; il warning e' lo stesso preesistente e non correlato di `test_volume.py`, gia' presente prima di questo task).

### File toccati in questa correzione

- `meshrec/src/meshrec/core/abaqus.py` — `element_surface` filtra le facce di bordo (RULING N).
- `meshrec/tests/test_abaqus.py` — test faccia interna (RULING N) e due test baricentro (RULING M(a)).
- `meshrec/tests/feasibility/test_calculix.py` — controprova ccx (RULING M(b)).

### Subagenti

Nessuno dispacciato in questa correzione (istruzione invariata: "Non dispacciare subagenti").
