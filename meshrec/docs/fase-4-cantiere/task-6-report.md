## Task 6 — Rapporto (rifacimento del 20/08/2026)

Riprende il lavoro dell'implementatore precedente, gia' in albero e non
committato: `scaled_jacobian` e `hexa_metrics` erano corretti e verbatim dal
brief. Il difetto era solo nel test `test_lo_jacobiano_scalato_scende_su_un_elemento_schiacciato`
e in una frase del docstring — entrambi corretti dal brief aggiornato
(sezione "Correzione del 20/08/2026").

### File toccati

- `meshrec/src/meshrec/core/quality.py` — sostituita la frase falsa del
  docstring di `scaled_jacobian` ("scende avvicinandosi a zero man mano che
  l'elemento si schiaccia") con il paragrafo corretto del brief: la metrica
  non misura lo schiacciamento perche' normalizza ogni spigolo per la propria
  lunghezza, quindi e' invariante di scala per direzione. Nessun'altra riga
  toccata: la formula, `_ANGOLI_ESAEDRO` e `hexa_metrics` restano quelli
  dell'implementatore precedente.
- `meshrec/tests/test_quality.py` — aggiunto `import math`; sostituito
  l'unico test sbagliato (`test_lo_jacobiano_scalato_scende_su_un_elemento_schiacciato`)
  con i tre test prescritti dalla correzione del brief: taglio, non-misura
  dello schiacciamento, angolo ripiegato. Gli altri tre test gia' presenti
  nell'albero (cubo, rovesciato, metriche senza min_ratio) erano gia'
  corretti verbatim dal brief e non sono stati toccati.

### Test nuovi: valore atteso prima di eseguire, provenienza, valore uscito

**1. `test_lo_jacobiano_scalato_di_un_elemento_tagliato_vale_il_valore_atteso`**
(taglio con `s = tagliato[4:, 0] += 1.0`)

- Atteso, calcolato su carta: la faccia superiore trasla di 1 lungo x. In ogni
  angolo gli spigoli uscenti diventano (1,0,0), (0,1,0), (s,0,1) con s=1 (per
  costruzione, verificato a mano anche sul nodo 0 e sul nodo 6 con la
  numerazione reale di `_ANGOLI_ESAEDRO`: entrambi danno determinante 1 e
  prodotto delle norme sqrt(2)). Valore atteso: `1/sqrt(1+1^2) = 1/sqrt(2) =
  0.707107`.
- Uscito: `0.707107` (pytest.approx, PASS).

**2. `test_lo_jacobiano_scalato_non_misura_lo_schiacciamento`**
(`sottile[4:, 2] = 0.1`, non un'offset ma un'altezza assoluta)

- Atteso, calcolato su carta: il solido resta un parallelepipedo rettangolo
  con spigoli assiali (1,0,0), (0,1,0), (0,0,0.1) in ogni angolo. Determinante
  = 0.1, prodotto delle norme = 1*1*0.1 = 0.1, rapporto = 1.0 esatto,
  indipendente dall'altezza perche' la formula normalizza ogni spigolo per la
  propria lunghezza (invarianza di scala per direzione).
- Uscito: `1.0` esatto su tutti e otto gli angoli (pytest.approx, PASS).

**3. `test_lo_jacobiano_scalato_e_negativo_su_un_angolo_ripiegato`**
(`ripiegato[6] = [0.35, 0.35, 1.0]`)

- Atteso: solo il segno, negativo. Spostare il nodo 6 oltre la diagonale
  della faccia superiore la rende concava in quel vertice; il minimo sugli
  otto angoli scende sotto zero (il brief riporta -0.4053 come valore di
  riferimento verificato dall'utente, non ripreso nel test — l'assert e' solo
  `< 0.0`, per non ancorare il test a una cifra che nessuna derivazione
  chiusa giustifica qui).
- Uscito: negativo (PASS).

Nessuno dei tre casi ha sorpreso: i valori calcolati a mano prima di eseguire
combaciano esattamente con quelli usciti dal codice.

### Test eseguiti

- `uv run pytest tests/test_quality.py -v` — 40 passati, 0 falliti.
- `uv run pytest tests -q --ignore=tests/feasibility` — **470 passati**, 1
  warning preesistente e non correlato (`UnmetQualityConstraintWarning` in
  `test_volume.py`), 0 falliti.

### Numero atteso vs numero uscito — discrepanza segnalata, non corretta

Il brief e le istruzioni del task indicano "469 passati (464 di base piu' i
cinque test nuovi)". Verificato: la baseline vera (con `git stash` delle
modifiche non committate) e' **464**, confermata. Ma il blocco di test del
brief corretto ne contiene **sei**, non cinque: cubo, tagliato,
non-misura-schiacciamento, angolo-ripiegato, rovesciato,
metriche-senza-min-ratio. 464 + 6 = **470**, il numero che esce davvero.
Nessuno dei sei e' superfluo o duplicato: coprono ciascuno una proprieta'
distinta della metrica, e nessuno era gia' presente nella baseline da 464 (il
lavoro precedente sullo Jacobiano scalato era interamente non committato).
Segnalo la discrepanza cosi' come richiesto, senza alterare test o soglie per
farla tornare.

### Subagenti dispacciati

Nessuno: task scoped a due file gia' letti per intero, nessun gap di
copertura su codice legacy toccato.

### Aree segnalate a security-reviewer

Nessuna: nessuna superficie auth/input esterno/dati sensibili toccata.

## Giro di correzione 1 (RULING Q, R) — 20/08/2026

Review del coordinatore tornata con 2 avvisi, entrambi accolti nello stesso
turno.

### RULING R — `inverted` non era provato

Il revisore ha mutato `hexa_metrics` fissando `"inverted": 0` e i sette test
allora esistenti sono restati tutti verdi: nessuno controllava che il
conteggio dei rovesciati fosse reale. Aggiunto
`test_le_metriche_esaedriche_contano_gli_elementi_rovesciati` in
`tests/test_quality.py`, con **due** esaedri (non uno, per lo stesso motivo
per cui un solo elemento non basterebbe: con `hexes == 1` un difetto che
restituisse il numero di elementi al posto del numero di rovesciati
darebbe comunque `inverted == 1`) — un cubo diritto e uno traslato di
`[2.0, 0.0, 0.0]` con la faccia inferiore e superiore scambiate
(`[12,13,14,15,8,9,10,11]`, lo stesso pattern di rovesciamento gia' usato
negli altri test del file).

Valori attesi, calcolati su carta prima di eseguire:
- `hexes == 2`: due elementi nell'array, diretto.
- `inverted == 1`: `hex_volumes` da' volume **con segno** (lo dichiara il
  proprio docstring), quindi il cubo diritto e' positivo e quello con le
  facce scambiate e' negativo — un solo elemento su due ha volume non
  positivo, e lo stesso vale per il segno di `scaled_jacobian` su cui
  `inverted` e' effettivamente calcolato (verificato nel test precedente
  `..._e_non_positivo_su_un_elemento_rovesciato` con la stessa identica
  permutazione di nodi).
- `total_volume == pytest.approx(0.0, abs=1e-9)`: +1 e -1 si annullano.

Uscito: i tre assert passano esattamente come previsto, nessuna sorpresa —
la convenzione di segno letta nei docstring esistenti era quella giusta.

### RULING Q — docstring che anticipava un fatto non ancora vero

`hexa_metrics` dichiarava «Il confronto fra i modelli, in report.py, le
tiene infatti separate...» come se il confronto esistesse gia'. Verificato
dal coordinatore (`rg -n "hexa|jacobian" src/meshrec/core/report.py` senza
occorrenze, nessun chiamante di `hexa_metrics` in `src/`): il confronto
arriva al Task 12, oggi non c'e'. Stessa famiglia di difetto del brief
originale (Ruling O/P): un'affermazione scritta e quindi creduta, invece di
verificata. Riscritta come vincolo su chi consumera' la funzione in futuro,
non come resoconto del presente — testo esatto fornito dal coordinatore,
applicato verbatim.

### Esito

- `uv run pytest tests/test_quality.py -k "rovesciati or contengono" -v` —
  2 passati (il test nuovo e quello adiacente, isolati per verifica rapida).
- `uv run pytest tests -q --ignore=tests/feasibility` — **471 passati**
  (470 + 1), 0 falliti, stesso warning preesistente e non correlato di
  prima. Numero verificato di persona, non assunto dal messaggio del
  coordinatore.
- Commit: `032e79e3e3d527ea527766d7d48d06a322d2d42f`, due file espliciti
  (`src/meshrec/core/quality.py`, `tests/test_quality.py`), nessun
  `git add -A`.
