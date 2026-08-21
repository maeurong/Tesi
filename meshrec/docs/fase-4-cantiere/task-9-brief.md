## Task 9: lo step 12 nella pipeline, e `meshrec wall`

`pipeline.run()` cresce di **un solo blocco**. I modelli parametrici non sono rami di `run()`: biforcarla raddoppierebbe la complessita' della funzione piu' delicata del progetto senza risparmiare nulla, perche' i tre modelli vanno comunque eseguiti tre volte.

**Files:**
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/cli.py`
- Modify: `src/meshrec/core/steps.py` (tre affermazioni che questo task rende false — Step 9)
- Modify: `src/meshrec/core/config.py` (una riga di `description` — Step 9)
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `wall.prior(points, cfg_segment, cfg_wall, spacing) -> dict[str, object]` (Task 3, firma letta a `wall.py:683-685`); `steps.STEP_KEYS` con dodici voci (Task 1).
- Produces: `pipeline.WALL_FILENAME = "12_wall.json"`; `pipeline.calcola_prior(out, cfg, points, spacing) -> dict[str, object]`; comando `meshrec wall <config>`.

### Cose gia' verificate nel codice: usale, non ricontrollarle a naso

Ognuna e' stata letta nel file, non ricordata. Se una ti risulta falsa,
**fermati e dillo** invece di adattare il codice per farla tornare.

- `steps.write_state` (`steps.py:110-118`) scrive alla **radice** del documento: `salvato[STEP_KEYS[numero - 1]] = {"impronta", "esito", "artefatto", "secondi"}`. Non esiste nessuna chiave `"steps"` e nessun campo `"stato"`. L'esito di uno step riuscito e' la stringa `"riuscito"` (`pipeline.py:123`).
- `RunConfig.to_step` vale **gia' 12** di predefinito (`config.py:260-263`). Non va toccato.
- `cfg.run.out_dir` e' gia' un `Path` (`config.py:245`): non serve avvolgerlo in `Path(...)`.
- `PipelineConfig` e' mutabile: `cfg.run.to_step = 3` e' la forma gia' usata a `tests/test_pipeline.py:270`. Non serve `model_validate({**model_dump(), ...})`.
- In `tests/test_pipeline.py` l'aiuto e' **`_config_cubo(tmp_path)`** e restituisce un `PipelineConfig` pronto. In `tests/test_cli.py` l'aiuto e' **`_config_cubo_su_disco(tmp_path)`** e restituisce il **percorso** del `config.yaml` gia' scritto: per averne la configurazione serve `config.load_config(percorso)`, che e' un giro completo senza perdite (`config.py:573-576`).
- `json` e' gia' importato in testa a `tests/test_pipeline.py`. Entrambi i file importano **dentro la funzione** cio' che serve al singolo test (`tests/test_pipeline.py:243`, `tests/test_cli.py:125`): segui quello stile invece di aggiungere import in testa.
- `pipeline.ARTIFACTS[2] == "02_segmented.ply"` (`pipeline.py:33`).
- `cli.py` ha gia' `json`, `sys`, `Path`, `pipeline`, `load_config` a livello di modulo e **non** ha `io`.
- `source_cloud` e `spacing` sono in ambito nel punto dove va inserito il blocco 12.

---

- [ ] **Step 1: I test dello step 12**

In coda a `tests/test_pipeline.py`:

```python
def test_una_corsa_completa_arriva_allo_step_dodici(tmp_path):
    """Lo step 12 chiude la corsa madre: se non compare nelle metriche, il
    prior non e' stato calcolato e i modelli parametrici non hanno da cosa
    partire."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)

    metriche = pipeline.run(cfg)

    assert "12_wall" in metriche
    assert (cfg.run.out_dir / pipeline.WALL_FILENAME).exists()
    stato = steps.read_state(cfg.run.out_dir)
    assert stato["12_wall"]["esito"] == "riuscito"


def test_lo_step_dodici_si_puo_fermare_prima_con_to_step(tmp_path):
    """to_step=11 lascia la corsa dov'era prima della Fase 4: le corse gia'
    fatte restano riproducibili senza calcolare un prior che nessuno ha
    chiesto."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 11

    metriche = pipeline.run(cfg)

    assert "11_export" in metriche
    assert "12_wall" not in metriche
    assert not (cfg.run.out_dir / pipeline.WALL_FILENAME).exists()


def test_una_corsa_fermata_all_undici_non_si_dichiara_completa(tmp_path):
    """Il gemello di `test_una_corsa_piena_sostituisce_una_chiave_estranea...`,
    dall'altro lato del confine: una corsa intera SOSTITUISCE metrics.json, una
    corsa parziale ci si FONDE, ed e' la distinzione da cui dipende lo sweep
    della Fase 2.

    Serve perche' senza di lui spostare o non spostare `pipeline_completa =
    True` lascia la suite verde in entrambi i casi. La chiave estranea
    sopravvive solo se la corsa si e' considerata parziale: e' un controllo
    indiretto ma non circolare, perche' non rilegge il valore che vuole
    provare.
    """
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    cfg.run.to_step = 11
    out = cfg.run.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / pipeline.METRICS_FILENAME).write_text(
        json.dumps({"99_estranea": {"ok": True}}), encoding="utf-8"
    )

    pipeline.run(cfg)

    metriche = json.loads((out / pipeline.METRICS_FILENAME).read_text(encoding="utf-8"))
    assert "99_estranea" in metriche


def test_il_prior_scritto_su_disco_e_quello_che_le_metriche_dichiarano(tmp_path):
    """La provenienza e' parte del risultato: il file e le metriche non possono
    raccontare due storie diverse dello stesso calcolo."""
    from meshrec.core import pipeline

    cfg = _config_cubo(tmp_path)
    metriche = pipeline.run(cfg)

    scritto = json.loads(
        (cfg.run.out_dir / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert scritto["regioni_trovate"] == metriche["12_wall"]["regioni_trovate"]
    assert len(scritto["membrature"]) == len(metriche["12_wall"]["membrature"])
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k "dodici or dichiara_completa" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.pipeline' has no attribute 'WALL_FILENAME'`.

- [ ] **Step 3: Il blocco 12 in `pipeline.py`**

Aggiungi `wall` all'import da `meshrec.core` e, sotto `METRICS_PARTIAL`:

```python
WALL_FILENAME = "12_wall.json"
```

**Il punto d'inserimento, esattamente.** Oggi il blocco dello step 11 finisce
cosi' (`pipeline.py:262-264`):

```python
        registra(11, avvio, "wall_model.inp")
        pipeline_completa = True
    except _FermataRichiesta:
```

Il codice nuovo va **fra `registra(11, ...)` e `pipeline_completa = True`**, e
`pipeline_completa = True` **si sposta in fondo al blocco nuovo**. Le due cose
insieme, mai una sola: spostarne una lascia una corsa fermata a 11 che si
dichiara completa, oppure una corsa piena che non lo e'. Risultato:

```python
        registra(11, avvio, "wall_model.inp")

        if stop <= 11:
            raise _FermataRichiesta

        in_corso = 12
        avvio = time.monotonic()
        # Il prior misura la nuvola segmentata e non la superficie ricostruita:
        # il rilievo e' il dato, e la ricostruzione di Poisson e' gia' una
        # interpretazione del rilievo. `source_cloud` e' esattamente l'uscita
        # dello step 2, che la ripresa ricarica quando riparte da piu' in la'.
        metrics["12_wall"] = calcola_prior(out, cfg, source_cloud, spacing)
        registra(12, avvio, WALL_FILENAME)
        pipeline_completa = True
    except _FermataRichiesta:
```

**NON toccare la riga 287**, `completa = start == 1 and pipeline_completa`. Il
commento che l'accompagna (`pipeline.py:114-119`) anticipa per nome proprio
questo task e spiega perche' il numero 12 non va rimesso a mano li'. Aggiorna
invece quel commento: «(oggi 11_export, domani 12_wall)» diventa «(oggi
12_wall)».

E la funzione, sopra `run()`:

```python
def calcola_prior(
    out: Path, cfg: PipelineConfig, points: np.ndarray, spacing: float
) -> dict[str, object]:
    """Step 12: il prior geometrico, calcolato e scritto accanto agli altri artefatti.

    Sta in una funzione propria e non dentro `run()` perche' ha due chiamanti:
    la corsa intera e il comando `meshrec wall`, che ricalcola il solo prior
    sugli artefatti gia' presenti. Una seconda copia del calcolo sarebbe una
    seconda cosa da tenere allineata.
    """
    esito = wall.prior(points, cfg.segment, cfg.wall, spacing)
    io.scrivi_atomico(
        out / WALL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito
```

Aggiorna la docstring di `run()`: la prima riga resta, e sotto aggiungi:

```
    Dalla Fase 4 gli step sono dodici. Il dodicesimo e' il prior geometrico e
    chiude la corsa madre; non e' un punto di ripresa e non e' un ramo: i due
    modelli parametrici sono corse figlie con la propria cartella, non
    biforcazioni di questa funzione.
```

- [ ] **Step 4: Riscrivere il test che questo task rende falso**

`tests/test_pipeline.py:238` si chiama
`test_una_corsa_completa_lascia_gli_undici_step_validi` e afferma, con tanto di
docstring che spiega perche', che lo step 12 resta «mai eseguito». Dopo questo
task e' falso. Riscrivilo:

```python
def test_una_corsa_completa_lascia_i_dodici_step_validi(tmp_path):
    """Dal Task 9 lo step 12 (prior geometrico) e' parte della corsa madre:
    una corsa intera non lascia piu' nulla di "mai eseguito"."""
    from meshrec.core import pipeline, steps

    cfg = _config_cubo(tmp_path)
    pipeline.run(cfg)
    stato = steps.run_state(cfg.run.out_dir, cfg)
    per_numero = {voce["numero"]: voce["stato"] for voce in stato}
    assert set(per_numero.values()) == {"valido"}
    assert all(per_numero[n] == "valido" for n in range(1, 13))
```

Il predefinito di `to_step` e' gia' 12 dal Task 1: nessun test si aspetta 11, e
non c'e' niente da riportare a 12.

- [ ] **Step 5: Eseguire, e provare per mutazione che il test di completezza serve**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS.

Poi la prova che quel test non e' decorazione. **Sposta temporaneamente**
`pipeline_completa = True` da dove l'hai messo a subito dopo `registra(11, ...)`
— cioe' la versione sbagliata — e riesegui:

Run: `uv run pytest tests/test_pipeline.py -k "dichiara_completa" -v`
Expected: **FAIL**. Se passa, il test non protegge nulla: dillo nel rapporto
invece di proseguire.

Rimetti la riga a posto e riesegui: PASS.

Riporta nel rapporto **i secondi misurati dello step 12**, letti dal campo
`"secondi"` sotto `"12_wall"` in `steps.json` della corsa di prova. Non e' un
numero decorativo: serve allo Step 9.

- [ ] **Step 6: Il test del comando `wall`**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_wall_ricalcola_il_solo_prior(tmp_path, capsys):
    """Il prior e' un'azione e non una ripresa: legge l'artefatto dello step 2
    gia' sul disco e non rifa' nulla di cio' che sta a monte."""
    import json

    from meshrec.core import pipeline

    percorso = _config_cubo_su_disco(tmp_path)
    cfg = config.load_config(percorso)
    cfg.run.to_step = 2
    config.save_config(cfg, percorso)
    pipeline.run(cfg)

    assert cli.main(["wall", str(percorso)]) == 0

    scritto = json.loads(
        (cfg.run.out_dir / pipeline.WALL_FILENAME).read_text(encoding="utf-8")
    )
    assert "membrature" in scritto
    assert json.loads(capsys.readouterr().out)["regioni_trovate"] == scritto["regioni_trovate"]


def test_il_comando_wall_senza_lo_step_due_dice_che_cosa_manca(tmp_path, capsys):
    """Chi arriva dopo non conosce gli step: l'errore dice quale artefatto
    manca e come ottenerlo, non solo che un file non c'e'."""
    percorso = _config_cubo_su_disco(tmp_path)

    assert cli.main(["wall", str(percorso)]) == 1
    assert "02_segmented.ply" in capsys.readouterr().err
```

- [ ] **Step 7: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_cli.py -k wall -v`
Expected: FAIL con `SystemExit: 2` da argparse — `invalid choice: 'wall'`.

- [ ] **Step 8: Il comando `wall` in `cli.py`**

In `_build_parser`, dopo `report_command`:

```python
    wall_command = commands.add_parser(
        "wall", help="ricalcola il solo prior geometrico sugli artefatti gia' presenti"
    )
    wall_command.add_argument("config", type=Path)
```

E in `main`, prima del ramo `serve`:

```python
    if args.command == "wall":
        from meshrec.core import io

        try:
            cfg = load_config(args.config)
            out = Path(cfg.run.out_dir)
            sorgente = out / pipeline.ARTIFACTS[2]
            if not sorgente.exists():
                raise FileNotFoundError(
                    f"manca {sorgente}: il prior misura la nuvola segmentata, che e' "
                    "l'artefatto dello step 2. Esegui almeno fino a quello "
                    f"(`meshrec run {args.config} --to-step 2`) e riprova"
                )
            punti, _ = io.read_cloud(sorgente)
            spaziatura = io.mean_spacing(punti, cfg.input.spacing_sample, cfg.input.seed)
            esito = pipeline.calcola_prior(out, cfg, punti, spaziatura)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0
```

- [ ] **Step 9: Le affermazioni che questo task rende false**

Tre commenti nel codice smettono di essere veri nel momento in cui lo step 12
entra in `run()`. Aggiornali: restano bugie firmate, altrimenti.

1. `steps.py:17-21`, il commento sopra `STEP_KEYS`. Togli «Fino al Task 9,
   pipeline.run scrive solo le prime undici». Al suo posto va la **ragione**,
   che non e' piu' un'attesa ma una decisione presa: `is_complete` in `sweep.py`
   continua a non richiedere `"12_wall"` a un candidato perche' un candidato di
   sweep si confronta sulle sole undici misure di elaborazione — e' completo
   quando ha il proprio deck, non quando ha il prior.
2. `steps.py:106`, docstring di `write_state`: «sono undici voci» → dodici.
   (Era gia' falso dal Task 1.)
3. `steps.py:128`, docstring di `run_state`: «Stato dei undici step» → «Stato
   dei dodici step». (Idem — e «dei undici» era pure sgrammaticato.)

E una riga in `config.py`, riportata dal Task 8: la `description` di
`WallConfig.section_dispersion` non dichiara di essere l'**unica** difesa contro
la coppia (pieno, affidabile) su una sezione a Π. Un operatore che la allenta in
YAML non puo' saperlo da solo. Aggiungi una frase che nomini l'accoppiamento.

**Conseguenza da dichiarare, non da correggere.** `sweep.py` lancia i candidati
con `meshrec run <config>` senza `--to-step` (`sweep.py:299-301`), quindi da
questo task in poi **ogni candidato di sweep calcola anche il prior**, perche'
`to_step` vale 12 di predefinito. Non introdurre un `--to-step 11` nello sweep:
la decisione e' lasciarlo com'e'. Il costo si misura, non si stima — nel
rapporto scrivi i secondi dello step 12 letti allo Step 5, che sono il costo per
candidato sulla geometria di prova.

- [ ] **Step 10: Eseguire e commit**

Run: `uv run pytest tests/test_cli.py tests/test_pipeline.py -v`
Expected: PASS.
Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/pipeline.py meshrec/src/meshrec/cli.py meshrec/src/meshrec/core/steps.py meshrec/src/meshrec/core/config.py meshrec/tests/test_pipeline.py meshrec/tests/test_cli.py
git commit -m "feat(fase-4): lo step 12 nella pipeline e il comando wall"
```

---

## Correzione del 20/08/2026 (setaccio Task 8-15)

La prima stesura di questo brief conteneva sei difetti, uno bloccante. Sono
corretti qui sopra; li elenco perche' chi legge sappia che i valori del brief
sono stati riletti nel codice e non ricordati.

- **9.1 (BLOCCANTE)** — `stato["steps"]["12"]["stato"] == "riuscito"` non e' la
  forma di `steps.json`: il documento e' piatto e il campo si chiama `esito`.
  Era un `KeyError` garantito. Forma giusta: `stato["12_wall"]["esito"]`.
- **9.2 e 9.3** — il brief chiedeva `completa = start == 1 and stop == 12`,
  rimettendo a mano il numero che il Task 1 aveva tolto, e indicava un punto
  d'inserimento che lasciava `pipeline_completa = True` prima dello step 12.
  Insieme cambiavano, senza dichiararlo, quali corse sostituiscono
  `metrics.json` e quali ci si fondono — il comportamento da cui dipende lo
  sweep della Fase 2. Ora la riga 287 non si tocca, le due cose si spostano
  insieme, e un test lo prova per mutazione.
- **9.4** — il brief diceva di aggiornare un test che si aspettava `to_step`
  predefinito 11. Nessun test lo fa: il predefinito e' 12 dal Task 1. Quello che
  si rompe davvero e' `test_una_corsa_completa_lascia_gli_undici_step_validi`,
  ora nominato allo Step 4.
- **9.5** — `_config_di_prova` non esiste in nessuno dei due file di test, e i
  due aiuti veri hanno nomi diversi e restituiscono cose diverse (un oggetto
  contro un percorso). Ora sono nominati entrambi, con cosa restituiscono.
- **9.6** — tre affermazioni in `steps.py` diventano false con questo task e
  nessuno le aggiornava; e la conseguenza sullo sweep (ogni candidato paga il
  prior) non era dichiarata da nessun brief. Sono lo Step 9.
