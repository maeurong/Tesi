# Task 1 — Report

Stato: **DONE_WITH_CONCERNS**

Commit: `c63670f` — `feat(fase-4): i due blocchi del prior, lo step 12 e gmsh come dipendenza`
Commit: `fad1b83` — `fix(fase-4): la completezza di uno sweep non include il prior` (ramo `worktree-fase-4-materiale`).

## Esito della suite

`uv run pytest tests -q --ignore=tests/feasibility` → **409 passed, 0 skipped, 0 failed** (partenza: 402 passed, 3 skipped).

Delta: +4 test nuovi (2 in `test_config.py`, 1 in `test_steps.py`, 1 in `test_sweep.py`) + 3 test di `test_gmsh_backend.py` che non saltano più = +7 passati, -3 saltati. Torna: 402 + 7 = 409.

## File toccati

### Sorgente (esattamente i quattro previsti dal brief)

- `meshrec/pyproject.toml` — `gmsh>=4.15.2` spostato da `[project.optional-dependencies].feasibility` a `dependencies`; il gruppo `feasibility` resta vuoto (`[]`).
- `meshrec/uv.lock` — rigenerato da `uv sync`.
- `meshrec/src/meshrec/core/config.py` — aggiunte `WallConfig` e `ModelConfig` (testo esatto del brief, nessuna modifica), agganciate a `PipelineConfig` fra `analysis` e `run`; `RunConfig.to_step` tetto alzato a 12 (default 12), descrizione di `from_step` estesa col paragrafo sullo step 12.
- `meshrec/src/meshrec/core/steps.py` — `STEP_KEYS` a dodici elementi (`"12_wall"` in coda), `STEP_BLOCKS[12] = ("wall",)`, commento aggiornato.
- `meshrec/src/meshrec/core/sweep.py` — `BLOCCHI_FUORI_IMPRONTA = ("run", "wall", "model")`; `fingerprint` esclude i tre blocchi invece del solo `run`; `expand` rifiuta un asse che punta a un blocco escluso, prima di costruire la griglia.

Nessun numero del provino di laboratorio è entrato in `src/` (verificato con grep su `172x172`, `250x250`, `140x175`, `700x250`, `0.4777`/`0,4777`: nessuna corrispondenza).

### Test — i tre previsti dal brief

- `meshrec/tests/test_config.py` — sostituito il corpo di `test_l_impronta_di_una_corsa_registrata_non_cambia` (ora rilegge i due registri veri invece di fissare un valore magico) e aggiunto `test_i_blocchi_nuovi_stanno_in_pipelineconfig_e_fuori_dall_impronta`. Aggiunto l'import diretto `from meshrec.core.config import PipelineConfig`, necessario perché il testo del test dato dal brief usa `PipelineConfig` senza il prefisso `config.` che il file usava fino a ora.
- `meshrec/tests/test_steps.py` — aggiunti `test_gli_step_sono_dodici_e_l_ultimo_e_il_prior` e `test_lo_step_dodici_non_cambia_le_impronte_degli_undici_precedenti` (testo esatto del brief).
- `meshrec/tests/test_sweep.py` — aggiunto `test_un_asse_su_un_blocco_fuori_impronta_viene_rifiutato` (testo esatto del brief).

### Test — tre file **non elencati dal brief**, toccati per tenere la suite verde (vedi concern sotto)

- `meshrec/tests/test_cli.py`
- `meshrec/tests/test_pipeline.py`
- `meshrec/tests/test_server.py`

## Ciclo TDD seguito

1. Sostituito il test in `test_config.py` (Step 1), eseguito `pytest tests/test_config.py -k impronta -v`: il primo test PASSA subito (fotografia dello stato attuale), il secondo FALLISCE con `ImportError: cannot import name 'BLOCCHI_FUORI_IMPRONTA'` — esattamente l'errore atteso dal brief (Step 2).
2. Scritto `WallConfig`, `ModelConfig`, l'aggancio a `PipelineConfig`, il nuovo tetto di `to_step` (Step 3-4).
3. Scritto lo step 12 nel registro (Step 5).
4. Scritto `BLOCCHI_FUORI_IMPRONTA`, la nuova `fingerprint`, il controllo in `expand` (Step 6).
5. Eseguiti i tre moduli (Step 7): **3 fallimenti**, nessuno nei due test nuovi appena scritti — vedi sezione concern sotto per il dettaglio e il fix applicato.
6. Aggiunti i due test di Step 8, rieseguiti (Step 9): PASS.
7. `gmsh` spostato a dipendenza vera (Step 10), `uv sync` (Step 11): installato, i tre test di `tests/test_gmsh_backend.py` eseguiti e passati (nessun fallimento nel merito — gmsh su questa macchina si comporta come misurato in Fase 0).
8. Suite intera (Step 12): 3 fallimenti fuori dai tre moduli espliciti — stessa causa, vedi sotto.
9. Commit (Step 13).

## Concern: sei test preesistenti aggiornati, tre in file fuori dallo scope dichiarato dal brief

Estendere `STEP_KEYS` a dodici elementi rende `sweep.is_complete()` (che itera su `REQUIRED_STEPS = STEP_KEYS`) più stringente: richiede anche la chiave `"12_wall"`. `pipeline.run()` — file esplicitamente **non** nell'elenco "Files: Modify" del brief — si ferma ancora allo step 11 (nessuna logica per lo step 12: è lavoro di un task successivo della Fase 4). Di conseguenza, dopo questa modifica, **nessuna corsa reale della pipeline risulta più "completa"** finché lo step 12 non viene implementato in `pipeline.py`.

Questo si è propagato oltre i tre moduli esplicitamente elencati dal brief (`test_config.py`, `test_steps.py`, `test_sweep.py`):

- `tests/test_steps.py::test_gli_undici_step_sono_quelli_che_la_pipeline_scrive` e `test_una_corsa_mai_eseguita_ha_tutti_gli_step_mai_eseguiti` — asserzioni numeriche stantie (`11` invece di `12`, `"11_export"` invece di `"12_wall"`, `range(1, 12)` invece di `range(1, 13)`). Rinominato il primo in `test_i_dodici_step_sono_quelli_che_la_pipeline_scrive` perché il nome vecchio era diventato falso.
- `tests/test_sweep.py::test_a_candidate_that_succeeds_records_its_artifacts` — asseriva `row["complete"] is True` su una corsa reale del cubo sintetico; ora è `False` perché manca `"12_wall"`. Corretto con un commento che spiega il perché.
- `tests/test_pipeline.py::test_una_corsa_completa_lascia_gli_undici_step_validi` — asseriva che tutti gli step fossero `"valido"` dopo una corsa completa; lo step 12 resta `"mai eseguito"` perché `pipeline.run` non lo tocca. Riscritto per asserire esplicitamente `{"valido", "mai eseguito"}` con lo step 12 isolato.
- `tests/test_server.py::test_lo_stato_della_corsa_elenca_gli_undici_step` — `len(corpo["steps"]) == 11` stantio, portato a `12`.
- `tests/test_cli.py::test_the_sweep_command_runs_a_two_candidate_grid_on_the_synthetic_cube` — con `complete` sempre `False` oggi, `check_sweep` non solleva più il warning "non discrimina" (nessuna riga è confrontabile) ma "nessuno dei 2 candidati e' confrontabile"; il test cercava il primo testo. Aggiornato il match atteso e l'asserzione `on_front` (ora nessuna riga entra nel fronte, essendo il fronte vuoto).

Tutti e sei sono correzioni meccaniche di un'asserzione stantia — nessuna ha richiesto inventare un comportamento nuovo o toccare `src/`: descrivono lo stato vero del sistema dopo il cambiamento esplicitamente richiesto dal brief. Nessuno introduce un numero del provino.

Segnalo comunque la cosa perché:

1. Il brief elenca solo `pyproject.toml`, `config.py`, `steps.py`, `sweep.py` in "Files: Modify" e solo `test_config.py`, `test_steps.py`, `test_sweep.py` in "Test:" — tre file di test toccati non erano previsti.
2. La conseguenza è strutturale, non locale: **per tutta la durata della Fase 4, fino a quando un task successivo non implementa davvero lo step 12 in `pipeline.py`**, ogni corsa reale della pipeline (via CLI, sweep, o server) risulterà "incompleta" secondo `sweep.is_complete()`, e ogni sweep reale avrà il fronte vuoto per mancanza di candidati confrontabili. Se un task successivo si aspettava di ereditare candidati "completi" prima che lo step 12 sia implementato, questo è il punto da cui ripartire.

Nessun blocco: la suite è verde, il cancello è aperto, ma la review dovrebbe confermare che questa sequenza (STEP_KEYS esteso subito, pipeline.py aggiornato solo dopo) è quella voluta dalla SDD, e non un'inversione d'ordine da correggere.

## Verifica gmsh

`uv sync` ha installato `gmsh==4.15.2`. `uv run pytest tests/test_gmsh_backend.py -v` → 3 test eseguiti (non più saltati) e tutti passati:
- `test_gmsh_produces_a_valid_tetrahedral_mesh`
- `test_gmsh_beats_tetgen_at_comparable_element_counts`
- `test_calibration_reports_the_best_ratio_when_the_target_is_unreachable`

Nessun fallimento nel merito: gmsh su questa macchina si comporta come misurato in Fase 0, nulla da segnalare su quel fronte.

## Correzione: la completezza di uno sweep non include il prior (ruling del coordinatore)

Commit: `fad1b83`.

Il concern segnalato sopra è stato risolto con un ruling esplicito: la completezza di un candidato di sweep non include il prior (step 12). Un candidato è completo quando ha il proprio deck (fino a `11_export`), non quando ha il prior — coerente col Ruling 1, che tiene `wall` e `model` fuori dall'impronta perché nessun asse della griglia li tocca.

### Ciclo TDD

1. Scritti due test in `meshrec/tests/test_sweep.py`, prima del fix:
   - `test_uno_sweep_e_completo_senza_il_prior` — un `metrics` con tutte le chiavi da `01_load` a `11_export` e senza `12_wall` deve risultare completo.
   - `test_uno_sweep_senza_un_vero_step_di_elaborazione_resta_incompleto` — il controllo che smentisce: un `metrics` a cui manca `09_tetrahedralize` (oltre a `12_wall`) resta incompleto.

   Eseguiti con `uv run pytest tests/test_sweep.py -k "senza_il_prior or senza_un_vero_step" -v`: il primo **FALLISCE** con `assert False is True` (esattamente l'errore atteso, `is_complete` pretendeva ancora `12_wall`), il secondo passa già (nessun regresso).

2. In `meshrec/src/meshrec/core/sweep.py`, `REQUIRED_STEPS` non è più un alias di `STEP_KEYS`: è filtrato per chiave (`tuple(chiave for chiave in STEP_KEYS if chiave != "12_wall")`), non per slice posizionale, con un commento che spiega il perché (nessun asse di sweep tocca il prior; un candidato è completo con il proprio deck).

3. Il controllo che smentisce era già coperto dal secondo test dello Step 1 (nessun modulo aggiuntivo necessario: verifica che togliere anche uno step di elaborazione vero, non solo il prior, faccia ancora fallire `is_complete`).

### Esito

- `uv run pytest tests/test_sweep.py -q` → **41 passed, 0 failed** (i due nuovi test compresi).
- `uv run pytest tests -q --ignore=tests/feasibility` → **409 passed, 2 failed**.

I due falliti sono, per costruzione dello stesso ruling, due delle sei asserzioni corrette nel task precedente che tornano vere nella direzione opposta:

- `meshrec/tests/test_sweep.py::test_a_candidate_that_succeeds_records_its_artifacts` — asseriva `row["complete"] is False`; ora una corsa reale del cubo sintetico torna `complete: True`, perché non serve più `12_wall`.
- `meshrec/tests/test_cli.py::test_the_sweep_command_runs_a_two_candidate_grid_on_the_synthetic_cube` — asseriva il warning "nessuno dei 2 candidati e' confrontabile"; ora i due candidati sono di nuovo confrontabili e il warning reale è "non discrimina" (fronte largo quanto la griglia), il testo opposto a quello atteso dal test.

Su indicazione esplicita del coordinatore questi due non sono stati ritoccati in questo giro: restano rossi, in attesa di review.

## Correzione 2: le due asserzioni ribaltate dal ruling tornano alla forma di f395ce8

Commit: `ee9a3dd`.

Le due asserzioni segnalate nella correzione precedente come rosse per costruzione del ruling sono state recuperate testualmente da `git show f395ce8:meshrec/tests/test_sweep.py` e `git show f395ce8:meshrec/tests/test_cli.py`, invece di riscritte a memoria:

- `meshrec/tests/test_sweep.py::test_a_candidate_that_succeeds_records_its_artifacts` — `assert row["complete"] is False` (con il commento che lo giustificava) sostituito con `assert row["complete"] is True`, identico a f395ce8.
- `meshrec/tests/test_cli.py::test_the_sweep_command_runs_a_two_candidate_grid_on_the_synthetic_cube` — il match del warning torna a `"non discrimina"`, l'asserzione sul fronte torna a `assert any(row["on_front"] for row in rows)`. `diff` contro l'originale di f395ce8 è vuoto: il file è tornato bit per bit identico.

`meshrec/tests/test_sweep.py` conserva invece, oltre al ripristino, tutte le aggiunte legittime del Task 1 e della correzione 1 (`test_uno_sweep_e_completo_senza_il_prior`, `test_uno_sweep_senza_un_vero_step_di_elaborazione_resta_incompleto`, `test_un_asse_su_un_blocco_fuori_impronta_viene_rifiutato`, l'import di `steps`): confermato con `diff` contro la versione di f395ce8, che mostra solo quei blocchi in aggiunta e nessun residuo della riga `complete`.

Colta anche l'occasione segnalata dal coordinatore: in `meshrec/src/meshrec/core/sweep.py` la docstring di `fingerprint` ripeteva parola per parola il commento sopra `BLOCCHI_FUORI_IMPRONTA` (nove righe duplicate). Il commento resta sulla costante, la docstring ora rimanda a quello con una riga sola.

### Esito

`uv run pytest tests -q --ignore=tests/feasibility` → **411 passed, 0 failed, 0 skipped**, 1 warning invariato (non correlato).

## Correzione 3: `completa` non confronta piu' `stop` con un numero scritto a mano

Commit: `7de9754`.

Rilievo di review: `pipeline.py:281` aveva `completa = start == 1 and stop == 11`. Il Task 1 ha alzato il tetto e il predefinito di `RunConfig.to_step` a 12: una corsa piena con la configurazione predefinita ha ora `stop == 12`, quindi non risultava piu' `completa`, cadeva nel ramo che fonde le metriche con quelle gia' sul disco invece di sostituirle — il contrario di quanto dice il commento due righe sotto ("Una corsa intera e' autoritativa: sostituisce, non fonde"). Non si vedeva in pratica solo perche' ogni corsa con `from_step=1` scrive comunque le stesse undici chiavi e le cartelle di sweep sono sempre nuove.

### Ciclo TDD

1. Scritto `tests/test_pipeline.py::test_una_corsa_piena_sostituisce_una_chiave_estranea_gia_sul_disco`: cartella d'uscita con un `metrics.json` che porta gia' una chiave estranea (`"99_estranea"`), poi una corsa piena con `_config_cubo` (configurazione predefinita, quindi `to_step=12`). Eseguito con `uv run pytest tests/test_pipeline.py -k test_una_corsa_piena_sostituisce_una_chiave_estranea -v`: **FALLISCE**, `AssertionError: assert '99_estranea' not in {...}` — la chiave estranea sopravvive nel merge, esattamente il difetto segnalato.

2. Corretto `src/meshrec/core/pipeline.py`: `completa` non confronta piu' `stop` con `11`. Al suo posto un flag `pipeline_completa`, inizializzato a `False` insieme a `in_corso`, alzato a `True` come ultima istruzione del blocco `try` (subito dopo `registra(11, avvio, "wall_model.inp")`, l'ultimo step che questa versione di `run()` implementa). `completa = start == 1 and pipeline_completa`. La condizione e' vera solo se il flusso ha attraversato per intero l'ultimo step implementato: quando il Task 9 aggiungera' il blocco dello step 12, la riga che alza il flag si sposta li' e la condizione resta corretta senza toccare il confronto stesso — nessun numero da tenere sincronizzato con `cfg.run.to_step`.

3. Aggiornato il commento sopra `STEP_KEYS` in `src/meshrec/core/steps.py` (rilievo minore della stessa review): diceva "le dodici chiavi che una corsa completa scrive in metrics.json", falso oggi (`pipeline.run` ne scrive undici fino al Task 9). Riformulato per restare vero prima e dopo il Task 9.

4. Rieseguito il test nuovo (PASS), poi la suite intera.

### Esito

`uv run pytest tests -q --ignore=tests/feasibility` → **412 passed, 0 failed, 0 skipped** (411 → 412: il nuovo test).

### Debito lasciato non toccato, su indicazione esplicita

- Il nome `test_una_corsa_completa_lascia_gli_undici_step_validi` (`tests/test_pipeline.py`) resta con "undici" nel nome pur riferendosi ora a dodici step nel registro.
- La stringa `"12_wall"` ripetuta letteralmente in tre punti della suite resta cosi'.

Nessuna delle due e' stata toccata in questo giro.
