# Task 6 — Review

Revisore: code-reviewer (sola lettura). Codice mai toccato in modo permanente:
ogni mutazione ripristinata con `git checkout --`, albero verificato pulito
prima e dopo (`git status --short` vuoto).

## Verdetto 1 — Conformita' alla spec

| Requisito (brief corretto, sezione "Correzione del 20/08/2026" inclusa) | Stato |
|---|---|
| `scaled_jacobian(nodes, hexes) -> np.ndarray`, minimo sugli otto angoli | Conforme, verbatim dal brief |
| `hexa_metrics(nodes, hexes) -> dict`, consuma `hex_volumes`/`_distribution` | Conforme, verbatim dal brief |
| Test cubo = 1 | Presente, passa |
| Test taglio = `1/sqrt(1+s^2)` = 0.707107 con s=1, calcolato su carta e non dal codice | Presente, valore verificato indipendentemente (vedi sotto) |
| Test schiacciamento: invariante di scala per direzione, resta 1 | Presente, verificato su piu' rapporti di forma (vedi sotto) |
| Test angolo ripiegato < 0 | Presente, passa |
| Test elemento rovesciato <= 0 | Presente, passa |
| `hexa_metrics` non contiene `min_ratio`/`radius_edge_ratio` | Presente, passa |
| Test sbagliato originale (`..._scende_su_un_elemento_schiacciato`) rimosso | Confermato: non compare piu' nel file |
| Due colonne mai sottratte/confrontate in tutta la codebase | Verificato con `rg` su tutto `src/` e `tests/`: nessun punto in cui `min_ratio` e `scaled_jacobian` compaiono nella stessa espressione o file di produzione, a parte `quality.py` dove `min_ratio` compare solo in prosa (docstring) e in un assert che ne verifica **l'assenza** |
| Suite intera verde | 470 passati, 0 falliti, 1 warning preesistente non correlato — confermato da me indipendentemente |

**Tutti i requisiti della spec corretta sono soddisfatti. Conforme.**

## Verdetto 2 — Qualita'

### Correttezza — verificata per mutazione, non per lettura

Sei mutazioni, una alla volta, ripristino ogni volta:

| # | Mutazione | Test caduti |
|---|---|---|
| 1 | Rimossa normalizzazione (divido determinante per 1 invece che per prodotto delle norme) | 2/7: taglio, schiacciamento |
| 2 | Permutata `_ANGOLI_ESAEDRO` (scambiati i primi due indici di ogni angolo) | 5/7: cubo, taglio, schiacciamento, rovesciato, metriche-senza-min-ratio |
| 3 | Segno del determinante invertito | 5/7: stesso schema della mutazione 2 |
| 4 | Minimo sugli otto angoli sostituito con la media | 1/7: solo ripiegato (`0.6599` invece di `<0`) |
| 5 | Minimo sostituito col secondo valore piu' piccolo (non l'estremo) | 1/7: solo ripiegato (`0.4741` invece di `<0`) |
| 6 | `hexa_metrics["inverted"]` forzato a `0`, ignora `jacobiani` | **0/7 — nessun test cade** |

Le mutazioni 1-3 sono catturate largamente: piu' test ancorati a valori
numerici esatti cadono insieme, confermando che quei test verificano davvero
la formula e non un placeholder. Le mutazioni 4-5 (min vs. aggregato diverso)
sono catturate da un solo test, `test_lo_jacobiano_scalato_e_negativo_su_un_angolo_ripiegato`
— ma lo catturano davvero, su due varianti di aggregazione diverse, quindi il
test fa il suo lavoro anche se e' l'unico ad ancorare quella proprieta'.

**Mutazione 6 e' l'unica sopravvissuta: rilievo reale.** `hexa_metrics()["inverted"]`
non e' mai testato su una mesh davvero invertita — l'unico caso testato a
livello di dizionario e' il cubo perfetto (`inverted == 0`), dove il valore
resterebbe 0 anche se il campo fosse hardcodato. Il segnale che l'array
`scaled_jacobian` sa vedere il ripiegamento (`ripiegato`, `rovesciato`) non e'
mai integrato: nessun test verifica `quality.hexa_metrics(rovesciato, hex)["inverted"] == 1`.
Severita': WARNING (copertura, non bug — il codice di produzione e' corretto,
verificato a mano: `"inverted": int((jacobiani <= 0.0).sum())` e' semplicemente
il conteggio giusto).

### Verifica indipendente dei tre valori attesi

- **Taglio**: derivato a mano prima di eseguire — in ogni angolo gli spigoli
  uscenti diventano (1,0,0), (0,1,0), (s,0,1) con s=1, determinante 1, prodotto
  delle norme `sqrt(2)`, rapporto `1/sqrt(2) = 0.707107`. Confermato per
  calcolo diretto sul nodo 0 e sul nodo 6 con la numerazione reale di
  `_ANGOLI_ESAEDRO` (non la formula del test): entrambi danno esattamente
  `(1.0, sqrt(2), 0.7071067811865475)`. Il valore atteso scritto nel test e'
  corretto e non viene dall'implementazione.
- **Schiacciamento non misurato**: verificato non solo con `s=0.1` del test ma
  con altezze 0.001, 0.01, 0.1, 10, 1000 e con tre casse anisotrope compresse
  su due assi contemporaneamente — sempre esattamente 1.0. L'affermazione
  contro-intuitiva del brief ("lo Jacobiano scalato non misura lo
  schiacciamento") e' vera, non un artefatto del singolo caso di test.
- **Trappola del 20/08**: `ripiegato[6] = (0.75, 0.75, 1.0)` da' `0.75425`
  (verificato), positivo. Nessuno dei sei test attuali lo accetterebbe: il
  test dell'angolo ripiegato richiede `< 0.0` in modo stretto, non un range.
  La trappola documentata dal brief e' effettivamente chiusa.

### Il vincolo delle due colonne separate

Verificato sull'intera codebase, non solo sul diff: `rg` su `min_ratio` e
`scaled_jacobian` in tutto `src/` e `tests/`. Nessun file mescola le due
grandezze in un'espressione. `min_ratio` vive in `config.py`, `volume.py`,
`sweep.py`, `wall.py` (parametro TetGen, tutto tetraedrico) e in `quality.py`
solo in prosa/assert-di-assenza. `scaled_jacobian` vive solo in `quality.py` e
nei test. Nessuna sottrazione, nessun rapporto, nessun punto dove le due
convivono numericamente. Vincolo rispettato.

Prova indiretta ulteriore (non richiesta ma rilevante): ho confrontato per
2000 esaedri distorti casuali il segno di `hex_volumes` con quello di
`scaled_jacobian`. In 1484/2000 casi i segni divergono, sempre nello stesso
verso — `hex_volumes` positivo (elemento globalmente non invertito) e
`scaled_jacobian` negativo (un angolo ripiegato). Mai il contrario: uno
`hex_volumes` negativo con `scaled_jacobian` positivo (un elemento davvero
invertito che il criterio dello Jacobiano lascerebbe passare) non si e' mai
presentato. Conferma empirica che `hexa_metrics` ha ragione a contare gli
invertiti da `jacobiani <= 0` invece che da `hex_volumes <= 0`: e' un criterio
almeno tanto sensibile, e cattura in piu' i ripiegamenti locali che un
controllo di volume non vedrebbe — esattamente quanto dichiarato nel
docstring.

### Rilievo di documentazione — stessa famiglia del difetto gia' corretto una volta

Il docstring di `hexa_metrics` (quality.py:136-138) dichiara:

> "Il confronto fra i modelli, in report.py, le tiene infatti separate e
> dichiara che la qualita' degli elementi non e' una grandezza confrontabile
> fra un modello tetraedrico e uno esaedrico."

Verificato: `report.py` (558 righe) non contiene alcun riferimento a
`hexa_metrics`, `scaled_jacobian`, `min_ratio` ne' a una distinzione
tet/esaedro. E' un renderer generico che legge chiavi da un dizionario di
metriche e le stampa in tabelle/istogrammi senza sapere cosa significano
(`_sezione_metriche`, `_istogrammi`) — non "dichiara" nulla sulla non
comparabilita' delle due grandezze, perche' non sa che esistono. Inoltre
`hexa_metrics` non e' chiamata da nessun punto della pipeline: e' codice
raggiungibile solo dai test.

La frase e' presumibilmente uno sguardo in avanti a un task successivo (dove
`report.py` verra' esteso per gli esaedri) scritto come se fosse gia' vero.
E' esattamente la classe di difetto che la "Correzione del 20/08/2026" ha
dovuto correggere altrove nello stesso file: un'affermazione nel docstring non
verificata contro il codice reale. Qui non falsa una proprieta' numerica (il
vincolo delle due colonne separate resta rispettato, verificato sopra), ma e'
un'affermazione sul comportamento di un altro modulo che oggi e' falsa.
Severita': WARNING — non blocca, ma nella stessa PR che ha appena pagato per
un problema di questo tipo merita la correzione, non il rinvio.

### Efficienza e semplificazione

Nessun rilievo. Il loop sugli otto angoli e' fisso e vettorizzato per esaedro
(nessun loop annidato sui singoli elementi); riusa `hex_volumes` e
`_distribution` gia' esistenti invece di reimplementarli; nessuna dipendenza
nuova; nessuna astrazione non richiesta (niente classe, niente config per un
valore che non cambia). `pr_analyzer.py` e `code_quality_checker.py` (skill
`code-reviewer`) non segnalano nulla sulle due funzioni nuove: complessita' 1
e 2, nessuna violazione SOLID, nessun code smell nuovo.

### Riepilogo rilievi

- **CRITICAL**: 0
- **WARNING**: 2 — copertura mancante su `hexa_metrics()["inverted"]` su mesh
  davvero invertita (mutazione 6, sopravvissuta); affermazione falsa nel
  docstring di `hexa_metrics` sul comportamento di `report.py`.
- **NOTE**: 0

## Stato della suite

470 passati, 0 falliti, 1 warning preesistente non correlato
(`UnmetQualityConstraintWarning` in `test_volume.py`) — confermato in modo
indipendente, eseguendo `uv run pytest tests -q --ignore=tests/feasibility`
dopo aver ripristinato l'albero da ogni mutazione.
