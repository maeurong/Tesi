# Task 7: `core/hexa.py` — rapporto

## File toccati

- `meshrec/src/meshrec/core/hexa.py` (nuovo)
- `meshrec/tests/test_hexa.py` (nuovo)

## Ciclo TDD seguito

1. Scritto `tests/test_hexa.py` (verbatim dal brief).
2. `uv run pytest tests/test_hexa.py -v` → fallito con `ImportError: cannot import name 'hexa' from 'meshrec.core'` (variante di `ModuleNotFoundError`, stessa ragione: il modulo non esisteva). Confermato che il fallimento era quello atteso, non un errore di sintassi nel test.
3. Scritto `src/meshrec/core/hexa.py` (verbatim dal brief).
4. `uv run pytest tests/test_hexa.py -v` → 5 passati.
5. Suite intera.

## Valori attesi calcolati a mano, prima di eseguire, e valori usciti

### Test 1 — `test_il_prisma_e_fatto_di_soli_esaedri_e_ne_ha_il_volume_analitico`

Verita' di riferimento: il prisma e' un parallelepipedo retto 200 x 140 x 1500 (rettangolo di sezione, estruso lungo l'asse Z senza rotazione: con `asse = ASSE_Z`, `_base_del_piano` restituisce `e1=[1,0,0]`, `e2=[0,1,0]`, quindi la trasformazione locale→globale e' l'identita' e le coordinate (u,v,w) del prisma locale diventano (x,y,z) invariate).

- Volume analitico calcolato a mano: `200.0 * 140.0 * 1500.0 = 42_000_000.0` mm³.
- Atteso: `esaedri.shape[1] == 8`; `hex_volumes(...).sum() ≈ 42_000_000.0`; `metriche["hexes"] == len(esaedri)`; `metriche["volume_analitico"] ≈ 42_000_000.0`.
- Uscito: `esaedri.shape == (832, 8)`; `hex_volumes(...).sum() == 42000000.0` (esatto, non solo entro tolleranza); `metriche["hexes"] == 832 == len(esaedri)`; `metriche["volume_analitico"] == 42000000.0`. Nodi totali: 1221.

Il volume esce esatto (non solo entro `rel=1e-6`) perche' il prisma e' un parallelepipedo e la decomposizione tetraedrica di `hex_volumes` e' esatta su facce piane — nessuna sorpresa.

### Test 2 — `test_nessun_esaedro_del_prisma_ha_jacobiano_non_positivo`

Atteso: nessuna assunzione numerica precisa possibile prima di eseguire (il valore dipende dalla mesh che gmsh produce), ma il segno si puo' predire: su un prisma retto con estrusione ortogonale alla sezione, ogni esaedro e' un parallelepipedo (non necessariamente cubo, ma ad angoli retti fra i tre spigoli locali), quindi lo Jacobiano scalato deve risultare positivo ovunque, con margine lontano da zero se gli elementi non sono troppo schiacciati.

Uscito: `scaled_jacobian` compreso fra `min = 0.7082` e `max = 0.9996`, tutti `> 0.0`. Coerente con l'attesa qualitativa (nessun elemento rovesciato, valori vicini a 1 perche' gli elementi sono quasi cubici: passo ≈ 46.67 mm sia in pianta sia — indirettamente, tramite `MeshSizeMax/Min` — nell'estrusione a strati regolari di lunghezza 1500/32 ≈ 46.875 mm).

### Test 3 — `test_lo_spessore_ha_almeno_tre_strati_di_elementi`

Calcolo a mano di `passo_di_mesh` con `cfg = ModelConfig(target_size=1000.0)`, default `min_layers=3`:
- `minima = min(ptp(x), ptp(y)) = min(200, 140) = 140`
- `tetto = 140 / 3 = 46.666666...`
- `passo = min(1000.0, 46.666...) = 46.666666...` (il passo assurdo da 1000 viene scartato in favore del tetto)

Atteso: `metriche["passo"] ≈ 46.6667 ≤ 140/3 + 1e-9`; almeno 4 piani distinti di quota lungo la direzione di spessore (asse y, essendo 140 la dimensione minima).

Uscito: `metriche["passo"] == 46.666666666666664`, `metriche["strati"] == 32`. `np.unique(np.round(nodi[:,1], 6))` restituisce 22 quote distinte (elenco da 0 a 140), ben oltre le 4 minime richieste. Coerente: il vincolo dei tre strati non e' stato allentato nonostante `target_size=1000` lo chiedesse.

### Test 4 — `test_il_prisma_parte_dall_origine_e_va_lungo_l_asse_che_gli_si_da`

Verita' di riferimento geometrica: qualunque sia l'asse (qui inclinato di 5° dalla verticale) e l'origine, la proiezione `(nodi - origine) @ asse` deve spaziare esattamente da 0 (base) a `LUNGHEZZA = 1500.0` (sommita'), perche' il prisma e' costruito in locale con w che va da 0 a `lunghezza` e poi trasformato rigidamente.

Atteso: `lungo.min() ≈ 0.0`, `lungo.max() ≈ 1500.0`, entro `abs=1e-6`.

Uscito: `lungo.min() = -3.55e-15` (zero a meno di errore di arrotondamento in doppia precisione), `lungo.max() = 1500.0000000000002`. Entrambi entro la tolleranza `1e-6` richiesta dal test.

### Test 5 — `test_l_ordine_di_nodi_ed_elementi_e_canonico_e_non_quello_dei_tag`

Calcolo a mano di `ordine_canonico` sul cubo unitario con nodi in ordine non ordinato per coordinate: la matrice `chiave` va lessicograficamente ordinata per (x, y, poi z tramite `lexsort` con chiavi `(z, y, x)` → ordina per x primario). I nodi con x=0 sono le righe `[0,0,0],[0,0,1],[0,1,0],[0,1,1]` (indici originali 1,5,2,6) e quelli con x=1 `[1,0,0],[1,0,1],[1,1,0],[1,1,1]` (indici originali 0,4,3,7), ciascun gruppo ordinato poi per y e z.

Atteso: `ordinati[0] ≈ [0,0,0]`, `ordinati[-1] ≈ [1,1,1]`; l'insieme di punti fisici puntati dall'elemento rimappato coincide (a meno di ordine) con quello originale; il volume con segno resta invariato (topologia interna dell'elemento non toccata).

Uscito: `ordinati[0] == [0,0,0]`, `ordinati[-1] == [1,1,1]` — confermato. `rimappati == [[0, 4, 6, 2, 1, 5, 7, 3]]`. `hex_volumes` prima e dopo: `[1.0]` in entrambi i casi — invariato, come atteso per un cubo unitario a volume 1.

## Nessuna sorpresa

Tutti e cinque i valori calcolati a mano prima dell'esecuzione hanno coinciso (a meno delle cifre attese per errore di arrotondamento in doppia precisione) con quelli usciti dal codice. Il brief non ha richiesto correzioni: la geometria descritta (prisma retto, estrusione ortogonale, base ortonormale scelta deterministicamente) e' quella effettivamente prodotta.

## Suite intera

`uv run pytest tests -q --ignore=tests/feasibility`

Base dichiarata: 471 passati. Aggiunti: 5 (`tests/test_hexa.py`). Atteso: 476.
Uscito: **476 passati**, 1 warning pre-esistente (non correlato, `test_volume.py::test_nobisect_can_make_the_volume_limit_inert_and_says_so`), 0 falliti. Conto verificato per differenza (476 − 471 = 5, pari ai test aggiunti).

## Commit

```
git add meshrec/src/meshrec/core/hexa.py meshrec/tests/test_hexa.py
git commit -m "feat(fase-4): il prisma in esaedri, con tre strati nello spessore imposti"
```

## Giro di correzione 1 di 5

### Ruling S — il test dell'ordine canonico non provava nulla

Il cubo unitario e' simmetrico per permutazione degli assi: la priorita' x→y→z che il test dichiara non e' distinguibile da nessun'altra priorita' fra gli stessi tre assi, perche' le estensioni sono uguali (1,1,1) su tutti e tre. Le sole due asserzioni sensibili all'ordine (`ordinati[0]`, `ordinati[-1]`) restano invariate sotto qualunque permutazione, dato che il punto minimo e quello massimo restano minimo e massimo componente per componente qualunque sia la priorita' di confronto.

Sostituito con un parallelepipedo di lati 1, 2, 3 (tre estensioni diverse fra loro) e asserzione sull'intera sequenza ordinata attesa, calcolata a mano prima di eseguire scorrendo prima tutti gli x=0 poi gli x=1, dentro ciascuno gli y crescenti, dentro ciascuno gli z crescenti:

```
[[0,0,0],[0,0,3],[0,2,0],[0,2,3],[1,0,0],[1,0,3],[1,2,0],[1,2,3]]
```

**Verifica richiesta esplicitamente**: ho permutato le chiavi del `lexsort` in `ordine_canonico` (da `np.lexsort((chiave[:,2], chiave[:,1], chiave[:,0]))`, priorita' x→y→z, a `np.lexsort((chiave[:,0], chiave[:,1], chiave[:,2]))`, priorita' z→y→x), rilanciato **solo** il test riscritto contro il codice mutato, e ripristinato subito dopo:

- Con la priorita' originale (x→y→z): il test passa.
- Con la priorita' permutata (z→y→x): il test **cade**, con `AssertionError` su 8/24 elementi (`Max absolute difference: 3.0`), sequenza uscita `[[0,0,0],[1,0,0],[0,2,0],[1,2,0],[0,0,3],[1,0,3],[0,2,3],[1,2,3]]` — z ora ha priorita' su x, la sequenza e' un'altra.
- Ripristinato il file originale da backup (`cp`), rieseguito il test da solo: passa di nuovo.

Il criterio del ruling e' soddisfatto: la geometria scelta non e' piu' troppo simmetrica, e la permutazione fa cadere il test.

### Ruling T — commento sbagliato su `setRecombine`

Verificato per mutazione diretta di uno script isolato (stessa sequenza di chiamate di `mesh_prisma`, non il codice di produzione) con la sagoma e i parametri del test 1 (rettangolo 200×140, passo 46.667, 32 strati):

- Con `setRecombine(2, superficie)` e `Mesh.RecombineAll=1` entrambi attivi: 832 esaedri, nessun altro tipo di elemento in dimensione 3.
- Rimuovendo **solo** `setRecombine(2, superficie)` (`RecombineAll=1` e `recombine=True` dell'estrusione restano): ancora 832 esaedri, stesso risultato.
- Rimuovendo **anche** `Mesh.RecombineAll` (con `setRecombine(2, superficie)` da solo, `recombine=True` dell'estrusione mantenuto): ancora 832 esaedri — quindi in questa configurazione specifica anche il solo `setRecombine` basterebbe.
- Disattivando `recombine=True` nell'estrusione (con `Mesh.RecombineAll=1` attivo): `gmsh` solleva `Exception: Cannot extrude quadrangles without Recombine` — l'estrusione con `recombine=True` e' la condizione davvero necessaria, e senza di essa nessuna delle due opzioni sulla superficie basta.

Conclusione: il commento originale attribuiva l'effetto a `setRecombine(2, superficie)` da solo ("senza il primo la faccia resta triangolata..."), ma nella configurazione del codice e' `Mesh.RecombineAll=1` (insieme a `recombine=True` nell'estrusione, che resta comunque necessario) a garantirlo — la rimozione di `setRecombine` non cambia il risultato. Il revisore aveva ragione. Commento riscritto per attribuire l'effetto al meccanismo verificato, spostato dopo `synchronize()` accanto a `Mesh.RecombineAll`, e la riga che citava l'effetto sbagliato sopra `setRecombine` e' stata rimossa per non lasciare due spiegazioni in contraddizione nella stessa funzione.

### Ruling U — `metriche["strati"]` non provato

Aggiunto `test_metriche_strati_conta_i_piani_di_nodi_lungo_l_asse`: conta i piani di nodi distinti lungo l'asse di estrusione (`nodi[:,2]` arrotondato, con `ASSE_Z`) e verifica `len(piani) == metriche["strati"] + 1` (N strati vogliono N+1 piani). Calcolato a mano prima di eseguire: con `strati=32` (stesso valore del test 1) ci si aspettano 33 piani; uscito: 33 piani, da 0.0 a 1500.0 in passi di 46.875 mm — coincide.

### Ruling V — guardie sugli ingressi degeneri

Prima della modifica, verificato empiricamente il comportamento silenzioso descritto dal coordinatore, chiamando `hexa.mesh_prisma` col codice non ancora modificato:

- `lunghezza=0.0`: nessun errore, mesh di 78 esaedri con `volume_analitico=0.0` e volume misurato `0.0` — un modello vuoto che non segnala nulla.
- `lunghezza=-1500.0`: nessun errore, `volume_analitico=-42000000.0` — un volume negativo che si propagherebbe silenzioso in ogni massa a valle.
- contorno con un'estensione nulla su un asse (rettangolo appiattito a altezza 0): `ZeroDivisionError: float division by zero` — non silenzioso, ma un errore che non dice ne' il valore ricevuto ne' perche' e' un problema, contro la convenzione del progetto (vedi gli altri `raise ValueError` in `abaqus.py`, `config.py`, `io.py`, `quality.py`).

Aggiunte due guardie, ciascuna nel punto dove il valore invalido si origina (radice, non nei chiamanti):

- `mesh_prisma`: `if float(lunghezza) <= 0.0: raise ValueError(...)`, primo controllo della funzione, prima di importare `gmsh`.
- `passo_di_mesh`: `if minima <= 0.0: raise ValueError(...)`, subito dopo aver calcolato `minima = np.min(np.ptp(...))`, che e' esattamente il punto dove l'estensione nulla diventa un problema (si', copre anche i chiamanti futuri di `passo_di_mesh`, oggi solo `mesh_prisma`).

Due test aggiunti: `test_mesh_prisma_rifiuta_una_lunghezza_non_positiva` (con `pytest.raises(ValueError, match="lunghezza")`, sia 0.0 sia negativa) e `test_passo_di_mesh_rifiuta_un_contorno_con_estensione_nulla_su_un_asse` (con `pytest.raises(ValueError, match="estensione")`, chiamato direttamente su `passo_di_mesh` per non pagare il costo di un giro completo in `gmsh` su un caso che fallisce comunque prima di toccarlo).

Nessuna validazione aggiunta oltre queste due, come richiesto.

## Suite dopo il giro di correzione

`uv run pytest tests -q --ignore=tests/feasibility`

Base dichiarata dal coordinatore: 476. Test aggiunti in questo giro: 3 nuovi (`test_metriche_strati_conta_i_piani_di_nodi_lungo_l_asse`, `test_mesh_prisma_rifiuta_una_lunghezza_non_positiva`, `test_passo_di_mesh_rifiuta_un_contorno_con_estensione_nulla_su_un_asse`) — il test dell'ordine canonico (Ruling S) e' stato riscritto, non aggiunto, quindi il conteggio dei test in `test_hexa.py` passa da 5 a 8 (+3). Atteso: 479.

Uscito: **479 passati**, 1 warning pre-esistente non correlato, 0 falliti. Conto verificato per differenza (479 − 476 = 3).
