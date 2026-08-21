# Task 7 — `core/hexa.py` — review

Skill invocate: caveman:caveman, ponytail:ponytail, code-reviewer, adversarial-reviewer.

File esaminati: `src/meshrec/core/hexa.py`, `tests/test_hexa.py`, `src/meshrec/core/config.py` (ModelConfig), `src/meshrec/core/quality.py` (hex_volumes, scaled_jacobian), diff `032e79e..719ac23`, brief e report del Task 7. Suite verificata indipendentemente: `uv run pytest tests -q --ignore=tests/feasibility` → **476 passed, 0 failed** (1 warning preesistente non correlato). Corrisponde alla dichiarazione dell'implementatore. Albero pulito a fine review (`git status --short` vuoto, nessuna mutazione residua).

## Verdetto 1 — Conformità alla spec

| Requisito | Esito |
|---|---|
| Interfaccia `passo_di_mesh(contorno, cfg) -> float` | OK, firma e comportamento coincidono col brief |
| Interfaccia `ordine_canonico(nodi, esaedri) -> tuple[np.ndarray, np.ndarray]` | OK |
| Interfaccia `mesh_prisma(contorno, origine, asse, lunghezza, cfg) -> tuple[np.ndarray, np.ndarray, dict]` | OK |
| Vincolo 1 — tre strati nello spessore imposti dal codice (non suggeriti), riduzione e non avviso | OK. `passo_di_mesh` fa `min(target_size, minima/min_layers)`: il passo chiesto viene **ridotto**, mai alzato, mai lasciato passare con un warning. Verificato anche con `ModelConfig(min_layers=3)` (default, `ge=3` in pydantic — il pavimento è imposto due volte, in config e in hexa) e con passo grossolano (100000mm su sezione 30mm minima → passo effettivo 10mm, 22 piani di nodi nello spessore, ben oltre i 4 minimi). Docstring spiega il "perché" (Jacobiano scalato invariante di scala per direzione, non vede spigoli sottili) |
| Vincolo 2 — soli esaedri, su più contorni | OK. Verificato su contorno a L (6 vertici, non rettangolare, non convesso) con asse obliquo (non cardinale): `esaedri.shape[1] == 8`, nessun triangolo, `RuntimeError` esplicito se gmsh restituisse un tipo diverso da 5 |
| Vincolo 3 — niente numeri del banco in `src/` | OK. `grep` mirato su 200/140/1500/832/1221 in `hexa.py`: zero occorrenze. Nessuna assunzione di rettangolarità (verificato su L) né di asse cardinale (verificato con asse obliquo + origine fuori assi, volume analitico riprodotto esatto a 1e-16 relativo) |
| Vincolo 4 — `hexa.py` costruisce, non misura | OK. Il volume di riferimento nei test è calcolato nel test (shoelace/geometria nota), non richiesto a `hexa.py`; `mesh_prisma` restituisce `area_sezione`/`volume_analitico` calcolati dal proprio input (formula di Gauss sul contorno ricevuto), non da costanti. Nessuna erosione del confine con `wall.py` osservata: nessuna chiamata a wall.py, nessun dato "misurato" hardcoded |

Tutti i requisiti della spec sono soddisfatti.

## Verdetto 2 — Qualità (mutazione, adversarial review)

### Mutazioni — cosa morde, cosa no

Ripristinato ogni volta con `git checkout -- src/meshrec/core/hexa.py`, verificato `git status --short` pulito prima di procedere alla successiva.

1. **`passo_di_mesh` ignora il tetto** (`return float(cfg.target_size)` invece di `min(target_size, tetto)`): **1 fallito / 4 passati** — `test_lo_spessore_ha_almeno_tre_strati_di_elementi` cade correttamente. Il vincolo dei tre strati è testato e morde.
2. **Off-by-one negli strati assiali** (`strati = max(...) - 1`): **0 falliti, 5/5 verdi**. Non è un difetto di spec — `strati` governa la suddivisione lungo l'asse di estrusione, non il vincolo "tre strati nello spessore" (quello resta il passo in pianta, invariato dalla mutazione). Ma è un gap di copertura: nessun test verifica `metriche["strati"]`, quindi un errore lì passerebbe inosservato.
3. **Rimozione di `setRecombine(2, superficie)`** (lasciando `Mesh.RecombineAll=1`): **0 falliti, 5/5 verdi**. Rilievo reale — il docstring in `mesh_prisma` dice "senza il primo la faccia resta triangolata e l'estrusione dà prismi a base triangolare invece di esaedri": empiricamente falso in questo caso, perché `Mesh.RecombineAll` da solo è sufficiente a coprire l'assenza del `setRecombine` per-superficie. Confermato rimuovendo *anche* `RecombineAll`: lì sì, 4/5 test cadono con `RuntimeError` (la guardia funziona quando la vera causa manca). Il commento nel codice attribuisce la protezione al meccanismo sbagliato.
4. **Priorità di ordinamento invertita in `ordine_canonico`** (`lexsort((chiave[:,0], chiave[:,1], chiave[:,2]))` invece di `(chiave[:,2], chiave[:,1], chiave[:,0])`, cioè z primario invece di x primario): **0 falliti, 5/5 verdi**. Rilievo reale, confermato con probe esterna su nodi asimmetrici (box 1×5×9): l'ordine di uscita è realmente diverso fra codice originale e mutato (x-primario vs z-primario), ma la fixture del test (cubo unitario) è simmetrica per permutazione degli assi — `ordinati[0]==[0,0,0]` e `ordinati[-1]==[1,1,1]` restano identici in entrambi i casi, e i controlli su insieme-di-punti e volume sono invarianti all'ordine. Il test dichiara di verificare "i nodi escono ordinati per x, poi y, poi z" ma non lo verifica: qualunque permutazione della priorità degli assi passa.

### Verifica geometrica indipendente

- Contorno a L (100×60 + 40×80, area 9200 mm² per shoelace), asse obliquo `[0.3,-0.2,0.9]` normalizzato, origine `[13,-7,41]`, lunghezza 733: volume mesh = 6743599.999999997 vs atteso 6743600.0 (errore relativo 4e-16), Jacobiano scalato ∈ [0.630, 0.997] tutto positivo, `esaedri.shape[1]==8`.
- Rettangolo 50×30, `target_size=100000` (passo assurdo): passo effettivo ridotto a 10.0, 50 strati, 22 piani di nodi nello spessore (min 4 richiesti), volume esatto.

### Rilievi (severità per gravità)

**WARNING (2):**
- Il test `test_l_ordine_di_nodi_ed_elementi_e_canonico_e_non_quello_dei_tag` non verifica realmente la priorità x→y→z dichiarata: la fixture è un cubo unitario, simmetrico per permutazione degli assi. Una qualunque permutazione della priorità di `lexsort` passa il test. Fix suggerito: fixture con tre estensioni diverse (es. box 1×2×3, come nella probe di questa review) invece del cubo unitario.
- Il commento su `setRecombine(2, superficie)` in `mesh_prisma` attribuisce a quella chiamata la prevenzione dei prismi triangolari, ma la mutazione mostra che `Mesh.RecombineAll=1` (impostato poche righe sotto) è da solo sufficiente. Il commento induce in errore un futuro manutentore che, fidandosi del commento, potesse rimuovere `RecombineAll` pensando che `setRecombine` basti da solo. Fix suggerito: correggere il commento per dire che `RecombineAll` è la rete di sicurezza effettiva, e chiarire se `setRecombine` per-superficie ha comunque un ruolo (es. su geometrie con più superfici) o è ridondante qui.

**NOTE (2):**
- `metriche["strati"]` non è coperto da alcun test: un errore nella suddivisione assiale (off-by-one o peggio) non altera il volume totale né lo Jacobiano in modo rilevabile dai test esistenti, quindi passerebbe inosservato. Non è un requisito esplicito del brief, ma è un valore restituito nell'interfaccia pubblica e non verificato.
- `mesh_prisma` non valida input degeneri (`lunghezza<=0`, contorno con estensione nulla su un asse → `passo_di_mesh` restituirebbe 0 e la mesh-size passata a gmsh sarebbe 0). Non testato, nessuna guardia. Accettabile se il contratto è "wall.py misura e garantisce input sani prima di chiamare hexa.py" (coerente col confine costruisce/misura dichiarato), ma non è scritto esplicitamente da nessuna parte come precondizione.

**Rilievo di design, non di questo diff (adversarial — Saboteur + Security Auditor, stesso punto da due prospettive):** `gmsh.initialize()`/`gmsh.finalize()` operano su stato di modulo globale, non per-istanza. `mesh_prisma` è corretto in isolamento (try/finally, niente leak), ma se il Task 8 (assemblaggio del telaio, fuori da questo diff) costruisse più prismi in parallelo (thread o processi con stato condiviso), le chiamate concorrenti a `mesh_prisma` si pesterebbero i piedi sullo stesso stato gmsh. Non è un difetto del Task 7 — la funzione fa esattamente un prisma per chiamata, come da brief — ma è un vincolo implicito da portare al Task 8 quando si deciderà se l'assemblaggio è seriale o parallelo.

## Sintesi

Codice pulito, aderente al brief in ogni punto, confine costruisce/non-misura rispettato, nessun numero di banco, nessuna assunzione di rettangolarità o asse cardinale (verificato su geometria diversa da quella del test). Le mutazioni sulla logica di business che il brief chiede di proteggere (vincolo tre strati, soli esaedri) mordono correttamente. Due mutazioni "strutturali" (ordine di sort, ridondanza setRecombine/RecombineAll) sopravvivono senza che nessun test se ne accorga: non sono bug funzionali oggi, ma sono punti dove un refactoring futuro potrebbe silenziosamente cambiare comportamento senza che la suite lo segnali.
