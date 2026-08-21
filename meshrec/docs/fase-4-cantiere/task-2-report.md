# Task 2 — report

Stato finale: **DONE**. Chiuso dal Ruling F di Mario (opzione C): il banco
`TELAIO` era sbagliato, non l'algoritmo. Corretto il fixture, aggiunto il test
del limite dichiarato, completato lo Step 15. Suite verde: 423 passati, 0
falliti. La cronologia sotto (fino a "Il problema") e' rimasta com'era scritta
prima del ruling, per non perdere la diagnosi; la sezione "Ruling F" in fondo
riporta la correzione finale.

## File toccati

- `src/meshrec/core/synth.py` — aggiunta `sample_frame_surface` in coda (Step 1),
  testuale al brief.
- `tests/test_synth.py` — aggiunto `test_il_telaio_sintetico_ha_i_prismi_che_gli_si_chiedono`
  (Step 2), testuale al brief.
- `src/meshrec/core/abaqus.py` — `_fix_sign` rinominata in `fix_sign` (Step 4):
  definizione, le due chiamate dentro `align_to_axes` (z_dir e x_dir), la
  citazione dentro la docstring di `build_node_sets`. Il paragrafo "Pubblica
  dalla Fase 4" e' finito nella docstring di `fix_sign` stessa (il brief non
  specifica quale delle due docstring, e questa e' la piu' vicina al contenuto:
  spiega perche' la funzione e' ora pubblica). Nessun alias privato lasciato
  dietro. `grep -rn "_fix_sign" src tests` prima e dopo: zero occorrenze anche
  prima della rinomina, nessun test la citava.
- `src/meshrec/core/wall.py` — nuovo modulo, creato in due tempi (Step 7 e Step
  12): `terna`, `chiavi_di_cella`, `spessore_per_cella`, `scarta_pavimento`,
  `regioni`, `scomponi`. Codice testuale al brief, nessuna modifica.
- `tests/test_wall.py` — nuovo file, creato in due tempi (Step 5 e Step 10),
  testuale al brief.
- `src/meshrec/core/config.py` — non toccato: `WallConfig` (Task 1) ha gia' ogni
  parametro che `wall.py` usa (`cell_factor`, `thickness_tolerance`,
  `min_cells`, `floor_angle_deg`, `floor_min_ratio`), niente da aggiungere.

## Ciclo TDD seguito, con gli esiti reali

- Step 3: `uv run pytest tests/test_synth.py -k telaio -v` con `synth.py` allo
  stato precedente (via `git stash`) — FAIL, `AttributeError: module
  'meshrec.core.synth' has no attribute 'sample_frame_surface'`. Poi
  `git stash pop` e riesecuzione — PASS.
- Step 6: `uv run pytest tests/test_wall.py -v` prima di scrivere `wall.py` —
  errore di collezione, `ImportError: cannot import name 'wall' from
  'meshrec.core'` (equivalente a `ModuleNotFoundError` per il motivo:
  il modulo non esiste).
- Step 8: dopo la prima meta' di `wall.py` — PASS su tutti e quattro
  (`test_la_terna_mette_la_direzione_trasversale_per_ultima`,
  `test_la_terna_ha_lo_stesso_verso_su_due_esecuzioni_e_su_una_nuvola_rimescolata`,
  `test_le_celle_sono_indici_non_negativi_misurati_dal_minimo`,
  `test_lo_spessore_locale_di_una_scatola_e_la_sua_dimensione_sottile`).
- Step 9: commit intermedio fatto, hash `dbe197f`
  (`feat(fase-4): terna del pezzo, celle e spessore locale del prior`).
- Step 11: dopo aver aggiunto i cinque test di `scarta_pavimento`/`scomponi` —
  FAIL sui cinque nuovi (`AttributeError: module 'meshrec.core.wall' has no
  attribute 'scarta_pavimento'` / `'scomponi'`), PASS sui quattro precedenti.
- Step 12: seconda meta' di `wall.py` scritta.
- Step 13: `uv run pytest tests/test_wall.py -v` — **8 passati, 1 fallito**:
  `test_un_telaio_sintetico_da_le_membrature_che_ha` cade fuori
  dall'intervallo dichiarato (trovata 1 regione, atteso 2-6).
- Step 14 (suite intera, con lo stato attuale): `uv run pytest tests -q
  --ignore=tests/feasibility` — **421 passati, 1 fallito** (stesso test).
  Nessun'altra regressione: la baseline dichiarata di 412 piu i 10 test nuovi
  (1 in `test_synth.py`, 9 in `test_wall.py`) fa 422, e 421+1=422 torna.

Non ho allargato l'intervallo 2-6, come lo Step 13 vieta esplicitamente. Ho
seguito l'istruzione: stampato `metriche["punti_per_regione"]` e la mappa delle
celle occupate, guardato se fonde o frammenta.

## Il problema

Il fixture `TELAIO` (quattro prismi: due montanti 200x200x1600 lungo z, due
traversi 1600x200x300 lungo x) e l'algoritmo dello Step 12, presi insieme,
producono **matematicamente sempre 1 regione**, non un numero fra 2 e 6. Non
e' un bug di trascrizione: ho verificato con uno script diagnostico.

`terna()` trova correttamente `n = y` come direzione trasversale globale
(coerente con `test_la_terna_mette_la_direzione_trasversale_per_ultima`, che
verifica esattamente questo). Il problema e' che **tutti e quattro i prismi
del fixture condividono la stessa estensione in y (200 mm)** — e' cosi' per
costruzione del fixture, non per errore di misura:

```
montante sinistro: (200.0, 200.0, 1600.0)   # ly = 200
montante destro:   (200.0, 200.0, 1600.0)   # ly = 200
traverso superiore:(1600.0, 200.0, 300.0)   # ly = 200
traverso inferiore:(1600.0, 200.0, 300.0)   # ly = 200
```

Quindi lo spessore per cella (l'estensione lungo y dentro ogni cella (u,v))
risulta **esattamente 200 mm su tutte le 294 celle occupate**, senza eccezioni:

```
spessori range 199.99999999999994 199.99999999999994
(array([200.]), array([294]))
```

`regioni()` collega celle adiacenti con spessore simile: con spessore
identico ovunque, ogni soglia di `thickness_tolerance` (compreso lo 0,15
predefinito) le collega tutte. La separazione potrebbe allora venire solo
dalla connettivita' spaziale — ma il telaio e' una struttura fisicamente
continua (i montanti toccano i traversi ai nodi, come in un vero telaio in
cemento armato gettato in un pezzo unico), quindi anche la griglia delle celle
occupate e' un unico anello connesso, senza vuoti:

```
####################
####################
####################
####################
###..............###
###..............###
   ... (23 righe uguali) ...
###..............###
####################
####################
####################
####################
####################
```

Questa e' la mappa vera delle 294 celle occupate sul piano (u,v)=(z,x): un
telaio, letteralmente. Nessun taglio di soglia sullo spessore e nessuna
componente connessa puo' separare un anello uniforme e continuo in piu' pezzi:
matematicamente, con questo algoritmo e questo fixture, il risultato e' sempre
1.

Il segnale reale che distingue montanti da traversi non e' "quanto e' spesso"
(la profondita' in y e' identica per costruzione) ma **l'orientamento locale**
del prisma: i montanti sono sottili in x e y (sezione 200x200, asse z), i
traversi sono sottili in y e z (sezione 200x300, asse x). Per coglierlo
servirebbe stimare l'orientamento localmente (una PCA per cella o per piccolo
intorno, non la singola terna globale usata oggi), invece di un singolo asse
di spessore per l'intera nuvola.

## Perche' non ho indovinato una correzione

Due strade possibili, nessuna delle due presa senza il tuo assenso:

1. **Tarare `regioni()` con un criterio ad hoc** che nel test attuale
   separerebbe i quattro prismi — ma sarebbe esattamente la "soglia tarata a
   mano" che il titolo del task vieta, e rischierebbe di funzionare solo per
   questo fixture specifico (overfitting), il contrario dell'obiettivo
   dichiarato ("stessa procedura su una geometria mai vista").
2. **Aggiungere un criterio di orientamento locale** (PCA per cella/intorno)
   e' la correzione geometricamente onesta, ma e' un pezzo di lavoro reale, non
   una riga: introduce parametri nuovi (dimensione dell'intorno, soglia di
   somiglianza fra normali locali), costo computazionale aggiuntivo su una
   nuvola a scala reale, e ridefinisce cosa vuol dire "stessa membratura"
   rispetto a quanto scritto nella docstring gia' presente di `regioni()`
   ("Due celle adiacenti... appartengono alla stessa membratura se i loro
   spessori differiscono di meno di `thickness_tolerance`"). E' una decisione
   di design, non un dettaglio di implementazione.

Il brief stesso, allo Step 13, prevede questo esito e offre due strade:
"correggi `regioni`" oppure "dichiara la limitazione nel documento del Task
13" — cioe' un documento fuori dallo scope di questo task. Non ho l'autorita'
per scegliere fra le due da solo, e il vincolo globale del task ("Se qualcosa
nel brief e' ambiguo o sbagliato, chiedimelo prima di indovinare") mi impone
di fermarmi qui.

## Cosa serve da te

Una di queste tre:

- **A.** Vuoi che implementi il criterio di orientamento locale in `regioni()`
  (o altrove in `wall.py`) adesso, dentro questo task? Se si', dimmi se hai
  vincoli su come stimarlo (dimensione dell'intorno, per esempio in multipli
  di `cell_factor`, o un nuovo campo in `WallConfig`).
- **B.** Vuoi che lasci il test rosso, documentando la limitazione nel
  documento del Task 13, e chiudo il Task 2 cosi' com'e' (8/9 test di
  `test_wall.py`, 421/422 della suite)?
- **C.** Il fixture `TELAIO` va corretto (per esempio dando a ciascun prisma
  una `ly` diversa, cosi' come nel provino reale le sezioni sono davvero
  diverse fra loro su tutti e tre gli assi) invece dell'algoritmo? Se si', il
  numero da cambiare e' nel banco di prova (`tests/test_wall.py`), non in
  `src/`, quindi resta dentro i vincoli del task.

Non ho toccato altro nel frattempo: l'albero di lavoro ha `wall.py` e
`test_wall.py` con la seconda meta' scritta ma non committata (lo Step 15 resta
in sospeso), esattamente allo stato appena descritto.

## Riepilogo esecuzione test

- `uv run pytest tests/test_synth.py -k telaio -v` — 1 passato.
- `uv run pytest tests/test_abaqus.py -q` — 23 passati.
- `uv run pytest tests/test_wall.py -v` — 8 passati, 1 fallito
  (`test_un_telaio_sintetico_da_le_membrature_che_ha`).
- `uv run pytest tests --ignore=tests/feasibility -q` — 421 passati, 1
  fallito, 0 saltati.

## Ruling F — la correzione finale

Mario ha scelto l'opzione C con una precisazione: il banco `TELAIO` era
sbagliato perche' dava a tutte e quattro le membrature la stessa sezione,
lasciando passare un'implementazione che fonde tutto in una regione sola
tanto quanto una che separa correttamente. L'algoritmo non si tocca.

**File toccato:** `tests/test_wall.py`. `src/meshrec/core/wall.py` toccato
solo per il commento `ponytail:` (nessuna riga di logica).

### Il fixture `TELAIO`, corretto

Le quattro sezioni (l'estensione in y di ciascun prisma) sono ora tutte
diverse, valori del banco e non del provino:

```
montante sinistro:   ly = 180
montante destro:      ly = 260
traverso superiore:   ly = 140
traverso inferiore:   ly = 340
```

Scelti per due ragioni:

1. **Ben distanti fra ogni coppia che si tocca a un nodo**, oltre la
   tolleranza relativa predefinita (`thickness_tolerance = 0.15`): la
   differenza minima fra due membrature adiacenti a un giunto e' 180 vs 140
   (22,2%), la massima 340 vs 140 (58,3%) — tutte comodamente sopra il 15%,
   nessun valore borderline che renderebbe il test fragile a piccole
   variazioni numeriche.
2. **Ogni sezione centrata sull'origine in y** (`origine_y = -ly/2` invece di
   `origine_y = 0`): mantiene la simmetria per riflessione attorno a y che il
   telaio a sezione uniforme aveva per costruzione. Senza questo accorgimento
   la SVD globale di `terna()` trova un asse trasversale leggermente inclinato
   (l'ho misurato: componente y a 0,9989 invece di 1,0, cioe' fuori dalla
   tolleranza `1e-6` di `test_la_terna_mette_la_direzione_trasversale_per_ultima`,
   un test invariato da prima del ruling), perche' membrature di dimensione
   diversa appoggiate tutte a y=0 spostano il baricentro della nuvola in modo
   asimmetrico. Centrando ciascuna sezione la simmetria torna esatta:
   trasversale misurata a `[0, 1, 1.8e-15]`, `det(direzioni) = 1.0000000000000002`.

Con questo fixture, `scomponi` sul telaio trova **4 regioni** (non piu' 1):
`punti_per_regione = [3472, 5984, 3866, 3206]`, tutti i punti distinti fra
regioni (`len(tutti) == len(np.unique(tutti))`), dentro l'intervallo 2-6 gia'
dichiarato dal test (nessuna modifica all'intervallo, come richiesto).

### Il test del caso degenere

Aggiunto `test_una_sezione_uniforme_smentisce_la_separazione_per_spessore` in
coda a `tests/test_wall.py`: costruisce un telaio con le vecchie quattro
sezioni tutte uguali (200x200x1600 e 1600x200x300, lo stesso fixture di prima
del ruling, ora locale al test e non piu' il banco condiviso) e asserisce
`len(regioni) == 1`. La docstring dichiara esplicitamente che e' un limite
noto e voluto — non un comportamento desiderabile da correggere qui — e
spiega perche' e' onesto: una regione a Π non e' un prisma e il controllo di
costanza della sezione del Task 3 la scartera' con il proprio motivo, quindi
il caso degenere non produce un risultato falso in silenzio.

### Commento `ponytail:` in `wall.py`

Aggiunto dentro `regioni()`, dopo la docstring, prima del corpo: nomina il
soffitto (spessore costante non separa membrature con la stessa sezione) e la
via d'aggiornamento (direzione locale di allungamento per cella, una PCA
sull'intorno, "lavoro in piu' che questo progetto non ha ancora avuto bisogno
di fare"), con riferimento incrociato al test che smetterebbe di passare il
giorno in cui qualcuno implementasse quella via.

### Step 15 e stato finale

Commit `ab62caf`
(`feat(fase-4): la scomposizione in membrature per costanza dello spessore`),
con il corpo del messaggio che spiega la correzione del banco. Nessun altro
file toccato oltre `src/meshrec/core/wall.py` e `tests/test_wall.py`.

`uv run pytest tests/test_wall.py -v` — **10 passati**, 0 falliti (il nono
test del brief piu' il decimo aggiunto dal ruling).

`uv run pytest tests -q --ignore=tests/feasibility` — **423 passati**, 0
falliti, 0 saltati.

## Fix round 1 — il test che non mordeva, e il seed correlato

Mario ha rilevato che `test_una_sezione_uniforme_smentisce_la_separazione_per_spessore`
non provava nulla sulla tolleranza: un telaio a sezione uniforme e' un anello
fisicamente continuo, spessore identico su ogni cella, quindi restituisce una
regione sola per pura geometria — lo farebbe anche un `regioni()` che
ignorasse del tutto `thickness_tolerance` e facesse solo componenti connesse.
Rilievo corretto e verificato di persona (vedi sotto).

**File toccati:** `tests/test_wall.py`, `src/meshrec/core/synth.py`. Nessuna
riga di `wall.py` toccata: l'algoritmo non si tocca, come da istruzione.

### Il test che morde la soglia

Aggiunto `test_la_tolleranza_di_spessore_decide_fra_una_regione_e_due`: due
prismi affiancati e a contatto (600x200x500 e 600xSPESSOREx500, toccanti sul
piano x=600), identici a parte lo spessore del secondo. Le due differenze di
spessore sono derivate da `WallConfig().thickness_tolerance` (letta da
`_cfg()`, non un numero fisso):

```
base = 200.0
sotto_soglia = base * (1.0 + tolleranza / 2.0)   # 215.0 con tolleranza=0.15
sopra_soglia = base * (1.0 + tolleranza * 3.0)   # 290.0 con tolleranza=0.15
```

`sotto_soglia` produce uno scarto relativo (rispetto al piu' grande dei due,
la stessa formula usata da `regioni()`) pari a meta' della tolleranza;
`sopra_soglia` pari a tre volte. Il test asserisce 1 regione nel primo caso, 2
nel secondo — stesso confine geometrico, solo la tolleranza cambia esito.

**Verificato che morde prima di dichiararlo verde:** ho sostituito
temporaneamente in `wall.py` la riga della similitudine
(`simili = np.abs(...) <= cfg.thickness_tolerance * massimo`) con
`simili = np.ones(...)` (solo connettivita', tolleranza ignorata), rieseguito
il test — FAIL, `assert 1 == 2` sul caso sopra-soglia, cioe' esattamente il
sintomo previsto: senza la tolleranza tutto resta fuso. Ripristinato
`wall.py` dal backup (nessun residuo), rieseguito — PASS. Nessuna riga di
`wall.py` e' rimasta diversa da prima di questa verifica.

### Il test del caso uniforme, cambiato di veste

`test_una_sezione_uniforme_smentisce_la_separazione_per_spessore` rinominato
`test_una_sezione_uniforme_e_un_canarino_per_la_separazione_per_orientamento`.
Corpo del test invariato (stesso fixture, stesse asserzioni); la docstring
ora dichiara esplicitamente che non e' una prova di correttezza dell'algoritmo
attuale ma un canarino di regressione per il giorno in cui qualcuno
implementasse la separazione per orientamento locale — con rimando incrociato
al test nuovo per la prova che manda davvero.

### `synth.sample_frame_surface`, il seed condiviso

`src/meshrec/core/synth.py:113`: ogni prisma ora riceve `seed=seed + indice`
invece del seed fisso passato dal chiamante. Con `noise=0.0` (unico valore
usato da tutti i test esistenti) il cambio e' inerte; con `noise > 0` ogni
membratura riceve ora una sequenza di rumore indipendente invece della stessa
sequenza ripetuta identica su ogni prisma.

### Suite e commit

Commit `e290a5f`
(`fix(fase-4): il test di regioni morde la tolleranza, seed indipendente per prisma`).

`uv run pytest tests/test_wall.py -v` — **11 passati**, 0 falliti.

`uv run pytest tests -q --ignore=tests/feasibility` — **424 passati**, 0
falliti, 0 saltati.

### Debito registrato, non toccato

Rilievo minore di Mario, esplicitamente lasciato com'e': `scarta_pavimento`
toglie il pavimento per appartenenza via coordinate arrotondate a 6 decimali
invece che per indice, perche' `segment.extract_planes` non restituisce gli
indici. Fragile solo se un pavimento reale coincidesse a sei decimali con un
punto del pezzo — non e' nello scope di questo task.

## Subagenti

Nessuno dispacciato: istruzione esplicita del compito.

## Aree per security-reviewer

Nessuna: modulo di calcolo geometrico puro, nessun input esterno non fidato,
nessun dato sensibile, nessuna superficie di autenticazione.
