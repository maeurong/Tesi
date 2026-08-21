# Task 10 — le corse figlie: `meshrec model`, il deck dei modelli parametrici

Stato: **DONE**

Commit: `28cf16a` — feat(fase-4): i modelli parametrici come corse figlie con deck proprio
Commit: `5c95248` — test(fase-4): protegge scostamento_nuvola, la guardia del Ruling J e le note di modello.json (giro di correzione 1)
Commit: `700a963` — test(fase-4): giro di correzione 2 -- cinque test rinominati o resi sensibili

## File toccati

- `src/meshrec/core/pipeline.py` — `MODEL_FILENAME`, `genera_modello(cfg, tipo, out_dir)`
- `src/meshrec/core/abaqus.py` — `export_model` accetta `element_surfaces`/`ties`/`pressure` e li pubblica nel dizionario restituito
- `src/meshrec/cli.py` — comando `model <config> --tipo estruso|primitive [--out-dir]`
- `src/meshrec/core/quality.py` — docstring di `hexa_metrics` aggiornata (C5): non più "nessun chiamante", ora dichiara `pipeline.genera_modello`
- `tests/test_pipeline.py` — 5 test nuovi
- `tests/test_cli.py` — 1 test nuovo

## Correzioni vincolanti del brief (C1–C7)

Tutte verificate contro il codice prima di scrivere, e tutte confermate vere (nessuna delle otto volte precedenti si è ripetuta qui):

- **C1**: `Membratura` ricostruita coi 15 campi; `riempimento_sezione`, `riempimento_stato`, `densita_dispersione` presi da `voce["riempimento"]["valore"/"stato"/"densita_dispersione"]`, non da campi piatti inesistenti nel JSON.
- **C2**: `nota_giunzioni` scritta come stringa letterale (il campo `vincolo_giunzioni` non esiste più in `hexa.costruisci`, confermato leggendo `hexa.py:963-973`).
- **C3**: `scostamento_nuvola` calcolato in `genera_modello` con `quality.vertex_deviation(nodi, sorgente_nuvola)`, leggendo `02_segmented.ply` dalla cartella madre.
- **C4**: `test_il_deck_della_corsa_figlia_e_esaedrico` usa `assert "TYPE=C3D4" not in testo` (non l'impossibile `"*C3D4"`); aggiunto `test_il_deck_della_corsa_figlia_porta_le_superfici_e_i_tie`, che costruisce `12_wall.json` chiamando `wall.prior` sul telaio a quattro membrature di `synth.sample_frame_surface` (stessa geometria di `tests/test_wall.py:33-38`), senza passare per `pipeline.run`.
- **C5**: docstring di `quality.hexa_metrics` aggiornata.
- **C6**: usati i nomi veri (`_config_cubo`, `_config_cubo_su_disco`, `cfg.run.out_dir` senza avvolgerlo in `Path`, `config.RunConfig`/`config.load_config` dal modulo già importato, `fingerprint` importato dentro la funzione).
- **C7**: `modello["metriche"]` pubblicato intero, senza sommare `giunzioni`/`ties` né `nodi_dipendenti_legati`/`nodi_dipendenti_totali`.

## TDD

Ogni funzione nuova (`genera_modello`, il ramo `model` della CLI) è stata scritta dopo aver visto fallire il test nel modo giusto:

- `tests/test_pipeline.py -k figlia|corsa_madre|senza_prior`: RED confermato con `AttributeError: module 'meshrec.core.pipeline' has no attribute 'genera_modello'`, poi GREEN dopo l'implementazione.
- `tests/test_cli.py::test_il_comando_model_scrive_la_cartella_col_suffisso_del_tipo`: implementato prima il comando CLI (contestualmente a `genera_modello`, stesso commit); RED verificato **a posteriori** ripristinando `cli.py` alla versione precedente via `git checkout` + patch salvata (non `git stash`, condiviso con altre sessioni) — `SystemExit: 2`, `invalid choice: 'model'` — poi riapplicata la patch e riverificato GREEN.

## Mutation testing (dichiarato nel docstring di ogni test nuovo, applicato davvero)

Tutte e sei le mutazioni dichiarate sono state applicate al codice sorgente (via `git diff`/`git checkout` per andata e ritorno, mai `git stash`), il test bersaglio è stato rieseguito, e in tutti e sei i casi il test è morto come dichiarato:

1. `test_la_corsa_figlia_ha_cartella_configurazione_deck_e_metriche_proprie` — rimosso `save_config(...)`: `AssertionError` su `config.yaml` mancante.
2. `test_il_deck_della_corsa_figlia_e_esaedrico` — scambiato `cfg.model.element` con `cfg.tet.element`: uccisa non dall'asserzione ma da `ValueError: C3D4 vuole 4 nodi per elemento, ne sono arrivati 8` sollevata da `write_inp` — comunque un fallimento del test, quindi la mutazione è morta.
3. `test_il_deck_della_corsa_figlia_porta_le_superfici_e_i_tie` — rimosso `element_surfaces=modello["superfici"]`: uccisa da `ValueError` sul `*TIE` che nomina superfici non dichiarate (guardia di `write_inp`).
4. `test_la_corsa_madre_non_cambia_quando_si_genera_un_modello` — mutazione composta (mutare `cfg.model.tie_name_prefix` **e** scrivere su `sorgente / "config.yaml"` invece che su `out / "config.yaml"`): `AssertionError` sul testo di `config.yaml` della madre. Nota onesta: una mutazione che *solo* sposta la destinazione di scrittura senza mutare `cfg` **non** ucciderebbe questo test, perché la serializzazione YAML è deterministica e il contenuto riscritto sarebbe bit-identico — verificata questa debolezza durante la progettazione della mutazione, non lasciata implicita.
5. `test_generare_un_modello_senza_prior_dice_che_cosa_manca` — tolto il nome del file dal messaggio dell'eccezione: `AssertionError: Regex pattern did not match`.
6. `test_il_comando_model_scrive_la_cartella_col_suffisso_del_tipo` — verificata via RED reale (punto sopra), equivalente a una mutazione totale (comando assente).

Nessuna mutazione dichiarata è sopravvissuta.

## Verifica reale (non solo pytest)

Eseguito il comando vero, non `cli.main()` in-process: `init` → `run` (pipeline intera fino allo step 12) → `model config.yaml --tipo estruso`, tutto tramite `uv run python -m meshrec.cli` su un cubo sintetico scritto su disco in `/tmp`. Uscita: `EXIT=0`, JSON ben formato con `scostamento_nuvola`, `nota_giunzioni`, `nota_armatura`, `export.element_surfaces/surface_area/ties/pressure`. Verificato su disco: `runs/default-estruso/` ha `config.yaml`, `modello.json`, `wall_model.inp`, `wall_model.vtu` propri; `runs/default/` (la madre) non ha guadagnato alcun `modello.json`.

## Suite

- `uv run pytest tests -q --ignore=tests/feasibility`: **513 passed** (507 di partenza + 6 nuovi: 5 in `test_pipeline.py`, 1 in `test_cli.py`).
- `uv run pytest tests/feasibility -m feasibility`: 7 passed, 1 skipped (eseguibile `ccx` assente in questo ambiente per un test già esistente, non toccato da questo task).

## Giro di correzione 1 — due mutazioni della coordinatrice sopravvivevano

La coordinatrice ha applicato due mutazioni contro il commit `28cf16a` e sono sopravvissute entrambe a 513 test verdi: rinominare `"scostamento_nuvola"` in `pipeline.py` (`_assente`), e forzare `riempimento_stato="pieno"` nella ricostruzione della `Membratura`. In entrambi i casi il codice di produzione era corretto (le due correzioni C1/C3 erano applicate davvero), ma nessun test nominava quelle chiavi né esercitava la guardia di `hexa.costruisci` dal percorso reale di `genera_modello` — un rename o una regressione futura sarebbero passati inosservati esattamente come oggi.

Tre test nuovi in `tests/test_pipeline.py` (nessun codice di produzione toccato):

1. **`test_lo_scostamento_dalla_nuvola_e_coerente_con_una_misura_indipendente`** — non rilegge `esito["scostamento_nuvola"]` e basta: ricostruisce indipendentemente le `Membratura` dallo stesso `12_wall.json` su disco, richiama `hexa.costruisci` e `quality.vertex_deviation` per conto proprio (stessa trasformazione di `genera_modello`, ma un secondo calcolo, non una rilettura), e confronta con `pytest.approx`. Mutazione verificata: rinominare `"scostamento_nuvola"` → `"scostamento_nuvola_assente"` in `pipeline.py:199` → **muore** con `KeyError: 'scostamento_nuvola'` (stesso identico effetto osservato dalla coordinatrice).
2. **`test_la_guardia_del_ruling_j_rifiuta_una_membratura_vuota_dal_percorso_reale`** — usa il telaio a sezioni uguali (`_TELAIO_A_SEZIONE_UNIFORME`, stessa geometria di `test_wall.py::TELAIO_A_SEZIONE_UNIFORME`) che `wall.prior` fonde davvero in un'unica regione a Π con `riempimento.stato == "vuoto"` e `affidabile == True` — verificato con due asserzioni sul prior stesso prima di chiamare `genera_modello`, per non dipendere da uno stato costruito a mano. Poi si aspetta `ValueError` da `pipeline.genera_modello`. Mutazione verificata: forzare `riempimento_stato="pieno"` in `pipeline.py:153` (identica alla mutazione della coordinatrice) → **muore** con `Failed: DID NOT RAISE ValueError`.
3. **`test_il_modello_json_porta_nota_giunzioni_e_conteggio_nodi_dipendenti`** — sul telaio a quattro membrature (giunzioni vere, non il cubo a una sola membratura dove il controllo sarebbe vuoto per costruzione): `nota_giunzioni != ""`, `nodi_dipendenti_totali > 0`, `0 <= nodi_dipendenti_legati <= nodi_dipendenti_totali`. Mutazione verificata: svuotare `"nota_giunzioni": ""` in `pipeline.py:205` → **muore** con `AssertionError: assert '' != ''`.

Tutte e tre le mutazioni sono state applicate al sorgente, verificate (uccidono), e ripristinate con `git checkout -- src/meshrec/core/pipeline.py` (mai `git stash`) prima di continuare. `git diff --stat` dopo ogni ripristino conferma zero residuo.

Helper aggiunto per evitare di duplicare tre volte la costruzione del telaio sintetico e del prior: `_scrivi_prior_telaio(cfg, telaio, spaziatura)`, usato anche dal test C4 già esistente (`test_il_deck_della_corsa_figlia_porta_le_superfici_e_i_tie`), che è stato refattorizzato per usarlo — nessun cambiamento di comportamento in quel test, solo la stessa logica estratta.

Suite dopo il giro di correzione: **516 passed** (513 + 3 nuovi test).

## Delega test-writer

Non dispacciato: il codice toccato (`pipeline.py`, `abaqus.py`, `cli.py`) non era codice legacy scoperto — era già coperto dalla suite esistente, e questo task ne estende la copertura direttamente in TDD sul codice nuovo.

## Segnalazioni a security-reviewer

Nessuna: nessun input esterno non fidato, nessuna auth, nessun dato sensibile nuovo. Il comando `model` legge solo file locali dichiarati dall'operatore in riga di comando, stessa superficie degli altri comandi CLI già esistenti.

## Giro di correzione 2 — cinque test rinominati o resi sensibili

Il revisore ha eseguito il deck vero su `ccx`: `Job finished`, 31.674 equazioni fattorizzate, nessun errore — codice di produzione confermato corretto. Ha poi applicato cinque mutazioni nuove (non quelle del giro 1) e tutte e cinque sono sopravvissute a 516 test verdi. Zero righe di codice di produzione cambiate in risposta a questo giro, salvo un refactor after-green (`_ricostruisci_membrature` estratta da `genera_modello`, comportamento invariato: 49/49 verde in `test_pipeline.py`+`test_cli.py` prima e dopo l'estrazione).

**1 — il test dello scostamento era circolare sull'aritmetica, non sul cablaggio.** Il revisore ha mutato `quality.py:469` (`distanze * 2.0`) e il test del giro 1 passava lo stesso, ma ha anche misurato che la stessa mutazione uccide quattro test in `test_quality.py` — la correttezza di `vertex_deviation` è già protetta altrove. Rinominato in `test_lo_scostamento_dalla_nuvola_prende_i_nodi_e_la_nuvola_giusti`, con docstring che dichiara esplicitamente cosa verifica (il cablaggio: nodi del modello + nuvola segmentata della madre, non l'aritmetica). Aggiunto **`test_lo_scostamento_dalla_nuvola_e_esatto_su_una_nuvola_spostata_di_una_distanza_nota`**: la nuvola sorgente è costruita come i nodi del modello (ricostruiti indipendentemente) spostati di un offset costante (0,001 mm, molto sotto il passo di mesh ~20 mm) lungo x — RMS e max attesi si calcolano su carta come `offset`, prima di eseguire qualunque cosa. Mutazione applicata (`distanze * 2.0`): il test rinominato **sopravvive** (conferma la diagnosi del revisore: è circolare sull'aritmetica per costruzione, e lo dichiara), il test nuovo **muore** con `0.002 == 0.001 ± 1e-9`.

**2 — `nota_giunzioni`.** L'asserzione `!= ""` è diventata `"*TIE" in esito["nota_giunzioni"]`. Mutazione applicata (testo vero → `"placeholder"`): muore con `AssertionError: assert '*TIE' in 'placeholder'`.

**3 — due campi di `Membratura` senza consumatore a valle.** Estratta `pipeline._ricostruisci_membrature(prior) -> list[Membratura]` (prima inline dentro `genera_modello`), e aggiunto `test_la_ricostruzione_legge_riempimento_sezione_e_densita_dispersione_dalle_chiavi_giuste`, che chiama la funzione estratta direttamente e verifica `riempimento_sezione`/`densita_dispersione` contro le chiavi annidate giuste (`valore`/`densita_dispersione`, non `soglia`). Mutazione applicata (`voce["riempimento"]["valore"]` → `["soglia"]`): muore con `0.5 == 1.0 ± 1e-6` (sul cubo di prova `valore` e `soglia` sono numericamente diversi, verificato con un'asserzione esplicita nel test prima del confronto, per non dipendere da una coincidenza del banco).

**4 — "la madre non cambia" protetto per coincidenza.** Aggiunta un'asserzione su `st_mtime_ns` di `config.yaml` della madre (una riscrittura, anche bit-identica, aggiorna sempre il tempo di modifica — `save_config` apre sempre in scrittura, non c'è un'ottimizzazione "salta se invariato" da verificare) **e** l'asserzione che la cartella figlia abbia il proprio `config.yaml`, nello stesso test. Mutazione applicata (`save_config(cfg, out / "config.yaml")` → `save_config(cfg, sorgente / "config.yaml")`, senza mutare `cfg`): muore — non sulla mtime ma sulla prima asserzione nuova (`figlia/config.yaml` non esiste più, perché con la mutazione nessuna scrittura finisce più nella cartella figlia). È un esito migliore di quello preventivato: il test cattura la mutazione più direttamente, senza bisogno del "fratello" che se ne accorgeva per caso nel giro 1.

**5 — ramo d'errore del comando `model` scoperto.** Aggiunto `test_il_comando_model_senza_il_prior_dice_che_cosa_manca` in `test_cli.py`, gemello di `test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca`. Mutazione applicata (rimosso il `try/except` dal ramo `model` di `cli.main`): muore con `FileNotFoundError` propagata invece di catturata (pytest la riporta come errore del test, non come mancata `AssertionError`, ma il test comunque non passa — la mutazione è morta).

Tutte e cinque le mutazioni sono state applicate al sorgente committato (`git checkout` per il ripristino, mai `git stash`), verificate una alla volta, e ripristinate; `git diff --stat` a zero dopo ogni ripristino, confermato con `git status --short` pulito alla fine del giro.

Suite dopo il giro di correzione 2: **519 passed** (516 + 3 nuovi: due test sullo scostamento sostituiscono un test esistente per un netto di +1, +1 sui campi di riempimento, +1 sul ramo d'errore CLI).
