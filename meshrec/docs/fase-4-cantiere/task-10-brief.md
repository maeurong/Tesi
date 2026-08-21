> ## LEGGI QUESTO PRIMA DEL RESTO — correzioni vincolanti del 20/08/2026
>
> Il corpo del brief qui sotto e' la prima stesura e contiene **tre difetti
> bloccanti** e tre seri. Sono tutti corretti in questa sezione. Dove questa
> sezione e il corpo dicono cose diverse, **vale questa**.
>
> Ogni affermazione qui e' stata riletta nel codice, con file e riga, non
> ricordata. Se una ti risulta falsa, **fermati e dillo** invece di adattare il
> codice per farla tornare: in questa fase e' successo otto volte che avesse
> ragione chi eseguiva e non chi scriveva il piano.
>
> ### C1 (BLOCCANTE) — la `Membratura` ricostruita manca di tre campi
>
> `wall.Membratura` ha quindici campi obbligatori; il corpo del brief ne passa
> dodici, e seguito alla lettera solleva
> `TypeError: Membratura.__init__() missing 3 required positional arguments:
> 'riempimento_sezione', 'riempimento_stato', and 'densita_dispersione'`.
>
> Non e' un dettaglio meccanico: `riempimento_stato` e' il campo su cui poggia
> l'unica guardia del Ruling J, quella che rifiuta di costruire un modello
> parametrico da una sezione dichiarata vuota. Ricostruita senza, la guardia
> diventa muta.
>
> Nel JSON il dato c'e' ma **annidato**: `wall.prior` scrive
> `"riempimento": riempimento(m, cfg)` (`wall.py:756`), cioe' un dizionario con
> `stato`, `valore`, `soglia`, `affidabile`, `densita_dispersione` e altro
> (`wall.py:639-646`). Quindi, in coda agli altri campi:
>
> ```python
>             rigonfiamento=np.zeros(0),
>             volume=float(voce["volume"]),
>             # Il riempimento nel JSON e' il dizionario che `wall.riempimento`
>             # scrive, non tre campi piatti: e' da li' che viene lo stato su
>             # cui la guardia del Ruling J rifiuta una regione a Pi.
>             riempimento_sezione=float(voce["riempimento"]["valore"]),
>             riempimento_stato=str(voce["riempimento"]["stato"]),
>             densita_dispersione=float(voce["riempimento"]["densita_dispersione"]),
> ```
>
> Gli altri dodici campi che il corpo del brief usa esistono davvero: verificato
> uno per uno contro `wall.py:735-758`.
>
> ### C2 (BLOCCANTE) — `metriche["vincolo_giunzioni"]` non esiste piu'
>
> Il corpo scrive `"nota_giunzioni": modello["metriche"]["vincolo_giunzioni"]`.
> Quel campo **e' stato rimosso** dal Task 8 nei giri di correzione di oggi:
> erano cinque righe di prosa dentro un dizionario di numeri, e la loro sede
> giusta e' il generatore del rapporto. Seguito alla lettera, `KeyError`.
>
> L'avvertenza pero' **non e' opzionale**, perche' senza di essa il confronto
> fra i tre modelli attribuisce alla geometria una differenza che viene dal
> vincolo. Scrivila come letterale, esattamente come gia' fai per
> `nota_armatura` due righe sotto:
>
> ```python
>         "nota_giunzioni": (
>             "*TIE fra superfici a contatto: le mesh di membrature adiacenti "
>             "non combaciano nodo a nodo. E' una differenza fra i modelli che "
>             "non deriva dalla geometria -- as-built monolitico, parametrici "
>             "vincolati alle giunzioni -- e va letta accanto al confronto"
>         ),
> ```
>
> ### C3 (BLOCCANTE) — `scostamento_nuvola` non lo scrive nessuno, e il Task 12 lo legge
>
> Il Task 12 legge `voce["modello"].get("scostamento_nuvola")` e dichiara quella
> grandezza **il perno** del confronto. Nel dizionario `esito` del corpo non
> c'e'. Verificato eseguendo il codice dei due task: esce
> `{'as-built': 4.9, 'estruso': None, 'primitive': None}`, cioe' due colonne su
> tre vuote, e nessun test dei due brief se ne accorge perche' il banco finto
> del Task 12 riproduce fedelmente un `modello.json` **senza** quella chiave.
>
> Si calcola qui, dove i dati ci sono. `quality.vertex_deviation`
> (`quality.py:439`) esiste gia' ed e' persino dichiarata fra le dipendenze del
> Task 12:
>
> ```python
>     # Lo scostamento dalla nuvola sorgente e' il perno del confronto (Task 12):
>     # e' definito allo stesso modo per i tre modelli. Si misura qui, dove la
>     # nuvola segmentata della madre e i nodi del modello sono entrambi a
>     # portata; il confronto non ricalcola nulla.
>     sorgente_nuvola, _ = io.read_cloud(sorgente / ARTIFACTS[2])
>     scarti = quality.vertex_deviation(nodi, sorgente_nuvola)
>     esito["scostamento_nuvola"] = {
>         "rms": float(np.sqrt(np.mean(scarti ** 2))),
>         "max": float(scarti.max()),
>         "nota": "distanza punto-nuvola nei soli nodi: sottostima dove gli "
>                 "elementi sono grandi, come dichiara quality.vertex_deviation",
>     }
> ```
>
> ### C4 (SERIO) — un'asserzione che non puo' fallire, e un test che non guarda cio' che ha nel nome
>
> `assert "*C3D4" not in testo` non puo' fallire in nessun deck: `write_inp`
> scrive il tipo solo come `*ELEMENT, TYPE={element_type}` (`abaqus.py:103`), e
> la stringa `*C3D4` con l'asterisco attaccato non compare mai, nemmeno in un
> deck tetraedrico. Nessuna mutazione la fa apparire.
>
> E il test che si chiama «porta le superfici» non asserisce nulla su `*SURFACE`
> ne' su `*TIE`. Non potrebbe: il banco della corsa figlia e' il cubo sintetico,
> che da' **una sola** membratura, quindi zero giunzioni e zero superfici
> (verificato: `regioni_trovate: 1`).
>
> Sostituisci l'asserzione impossibile con una mutabile:
>
> ```python
>     assert "*ELEMENT, TYPE=C3D8I" in testo
>     assert "TYPE=C3D4" not in testo
> ```
>
> e aggiungi un **secondo test su una geometria che le superfici ce le ha**: il
> telaio a quattro membrature. Non passare per `pipeline.run`, che su un telaio
> costerebbe Poisson piu' TetGen: costruisci il `12_wall.json` chiamando
> `wall.prior` direttamente sulla nuvola di `synth.sample_frame_surface`, e
> scrivi accanto la nuvola come `02_segmented.ply`. Cosi' il dato d'ingresso lo
> produce il codice vero e non la tua mano. Il telaio e la sua costante
> `TELAIO` stanno in `tests/test_wall.py:33-38` e in
> `tests/feasibility/test_calculix.py` — i numeri del provino nei test sono
> ammessi, e' in `src/` che non devono comparire.
>
> Quel test asserisce `"*SURFACE, TYPE=ELEMENT"` e `"*TIE"` nel deck.
>
> ### C5 (SERIO) — una docstring che questo task rende falsa
>
> `quality.py:139-141` dice, al presente: «Oggi la funzione non ha ancora
> chiamanti: questa riga e' il vincolo che li aspetta, non il resoconto di cio'
> che fanno». Verificato vero **oggi** (nessun riferimento a `hexa_metrics` in
> `src/`), falso dal tuo task in poi, perche' `genera_modello` e' il primo
> chiamante. E' la stessa forma di difetto gia' pagata due volte in questa fase.
>
> Sostituiscila con: «Il suo unico chiamante e' `pipeline.genera_modello`; il
> confronto del Task 12 legge il risultato da `modello.json`.»
>
> ### C6 (MINORE) — nomi di aiuti e import che non esistono
>
> `_config_di_prova`, `Path`, `RunConfig`, `load_config`, `save_config` non sono
> definiti ne' importati dove il corpo li usa. I nomi veri:
>
> - in `tests/test_pipeline.py` l'aiuto e' **`_config_cubo(tmp_path)`** e
>   restituisce un `PipelineConfig` pronto;
> - in `tests/test_cli.py` e' **`_config_cubo_su_disco(tmp_path)`** e
>   restituisce il **percorso** del `config.yaml`: la configurazione si ricava
>   con `config.load_config(percorso)`;
> - `cfg.run.out_dir` e' gia' un `Path`: non serve avvolgerlo;
> - `PipelineConfig` e' mutabile, quindi `cfg.run.to_step = 11` basta;
> - entrambi i file importano **dentro la funzione** cio' che serve al singolo
>   test: segui quello stile.
>
> `from meshrec.core.sweep import fingerprint` invece e' corretto: verificato.
>
> ### C7 — le metriche che `hexa.costruisci` restituisce oggi
>
> Dopo sei giri di correzione il dizionario `metriche` e' questo, e il tuo
> `modello.json` lo pubblica intero passando `modello["metriche"]`:
>
> ```
> tipo, membrature, giunzioni, ties, membrature_non_legate,
> accorciamenti, element_type, nodi_dipendenti_legati, nodi_dipendenti_totali
> ```
>
> `giunzioni` e `ties` sono **due numeri diversi** e vanno lasciati tali: il
> primo conta le giunzioni geometriche tagliate, il secondo i vincoli
> effettivamente scritti nel deck. Cosi' `nodi_dipendenti_legati` contro
> `nodi_dipendenti_totali`: su una geometria reale il secondo e' maggiore del
> primo, ed e' un limite noto della mesh non conforme, dichiarato e misurato.
> **Non sommarli, non farne un rapporto, non nasconderli**: sono i numeri che
> rendono leggibile il confronto del Task 12, perche' dicono quanta della
> cedevolezza di un modello parametrico viene dal vincolo e non dalla geometria.
>
> ---

## Task 10: le corse figlie — `meshrec model`, il deck dei modelli parametrici

Ogni modello e' la propria cartella, con configurazione completa, artefatti, metriche e riga di registro proprie. La selezione e' un'**azione**: non entra in `config.yaml` della corsa madre, o rigenerare un modello in piu' cambierebbe l'impronta di una corsa che non e' cambiata.

**Files:**
- Modify: `src/meshrec/core/pipeline.py`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `hexa.costruisci` (Task 8); `abaqus.export_model`, `abaqus.element_surface` (Task 4 e 5); `quality.hexa_metrics` (Task 6); `pipeline.WALL_FILENAME` (Task 9).
- Produces: `pipeline.MODEL_FILENAME = "modello.json"`; `pipeline.genera_modello(cfg, tipo, out_dir) -> dict[str, object]`; comando `meshrec model <config> --tipo estruso|primitive --out-dir <cartella>`.

- [ ] **Step 1: I test della corsa figlia**

In coda a `tests/test_pipeline.py`:

```python
def test_la_corsa_figlia_ha_cartella_configurazione_deck_e_metriche_proprie(tmp_path):
    """Ogni modello e' la propria cartella: la provenienza e' parte del
    risultato, e un modello senza la configurazione che lo ha prodotto non e'
    ricostruibile a distanza di mesi."""
    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-estruso"

    esito = pipeline.genera_modello(cfg, "estruso", figlia)

    assert (figlia / "config.yaml").exists()
    assert (figlia / "wall_model.inp").exists()
    assert (figlia / pipeline.MODEL_FILENAME).exists()
    assert esito["tipo"] == "estruso"
    assert esito["sorgente"] == str(cfg.run.out_dir)
    assert esito["hexa"]["hexes"] > 0
    assert esito["hexa"]["inverted"] == 0


def test_il_deck_della_corsa_figlia_e_esaedrico_e_porta_le_superfici(tmp_path):
    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    figlia = tmp_path / "figlia-primitive"

    pipeline.genera_modello(cfg, "primitive", figlia)

    testo = (figlia / "wall_model.inp").read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I" in testo
    assert "*C3D4" not in testo


def test_la_corsa_madre_non_cambia_quando_si_genera_un_modello(tmp_path):
    """La selezione e' un'azione e non un parametro: se toccasse la
    configurazione della madre, rigenerare un modello in piu' cambierebbe
    l'impronta di una corsa che non e' cambiata."""
    from meshrec.core.sweep import fingerprint

    cfg = _config_di_prova(tmp_path)
    pipeline.run(cfg)
    prima = (Path(cfg.run.out_dir) / "config.yaml").read_text(encoding="utf-8")
    impronta = fingerprint(cfg)

    pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")

    assert (Path(cfg.run.out_dir) / "config.yaml").read_text(encoding="utf-8") == prima
    assert fingerprint(load_config(Path(cfg.run.out_dir) / "config.yaml")) == impronta


def test_generare_un_modello_senza_prior_dice_che_cosa_manca(tmp_path, capsys):
    cfg = _config_di_prova(tmp_path)
    cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), "to_step": 11})
    pipeline.run(cfg)

    with pytest.raises(FileNotFoundError, match="12_wall.json"):
        pipeline.genera_modello(cfg, "estruso", tmp_path / "figlia")
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_pipeline.py -k figlia -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.pipeline' has no attribute 'genera_modello'`.

- [ ] **Step 3: `genera_modello`**

In `pipeline.py`, sotto `calcola_prior`:

```python
MODEL_FILENAME = "modello.json"


def genera_modello(cfg: PipelineConfig, tipo: str, out_dir: Path) -> dict[str, object]:
    """Genera un modello parametrico come corsa figlia, nella propria cartella.

    I due modelli parametrici sono **generatori di mesh di volume alternativi a
    TetGen**: producono nodi ed elementi e rientrano negli step esistenti di
    metriche di volume ed esportazione. Non sono rami di `run()`, e la ragione
    e' che biforcarla raddoppierebbe la complessita' della funzione piu'
    delicata del progetto senza risparmiare nulla.

    La cartella figlia porta la stessa `config.yaml` della madre -- e' lo
    stesso esperimento, e la stessa impronta -- piu' un `modello.json` che dice
    di quale tipo e' e da quale corsa viene. La provenienza sta li' e non nella
    configurazione, perche' la scelta del modello e' un'azione e non un
    parametro di elaborazione.
    """
    from meshrec.core import hexa
    from meshrec.core.wall import Membratura

    sorgente = Path(cfg.run.out_dir)
    percorso_prior = sorgente / WALL_FILENAME
    if not percorso_prior.exists():
        raise FileNotFoundError(
            f"manca {percorso_prior}: un modello parametrico si costruisce sul "
            "prior, e il prior e' lo step 12. Esegui `meshrec wall` sulla stessa "
            "configurazione e riprova"
        )
    with percorso_prior.open(encoding="utf-8") as handle:
        prior = json.load(handle)

    membrature = [
        Membratura(
            punti=np.arange(0),
            asse=np.asarray(voce["asse"], dtype=np.float64),
            origine=np.asarray(voce["origine"], dtype=np.float64),
            lunghezza=float(voce["lunghezza"]),
            sezione=tuple(voce["sezione"]),
            sezione_dispersione=tuple(voce["sezione_dispersione"]),
            contorno=np.asarray(voce["contorno"], dtype=np.float64),
            fuori_piombo_deg=float(voce["fuori_piombo_deg"]),
            asse_ideale=np.asarray(voce["asse_ideale"], dtype=np.float64),
            scarto_asse_deg=float(voce["scarto_asse_deg"]),
            rigonfiamento=np.zeros(0),
            volume=float(voce["volume"]),
        )
        for voce in prior["membrature"]
    ]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")

    modello = hexa.costruisci(membrature, tipo, cfg.model)
    nodi = modello["nodi"]
    elementi = modello["elementi"]

    carico = None
    if cfg.model.lateral_nset is not None and cfg.model.lateral_pressure is not None:
        carico = (cfg.model.lateral_nset, float(cfg.model.lateral_pressure))

    export = abaqus.export_model(
        out / "wall_model.inp",
        out / "wall_model.vtu",
        nodi,
        elementi,
        cfg.analysis,
        cfg.tet,
        reference=nodi,
        element_type=cfg.model.element,
        element_surfaces=modello["superfici"],
        ties=modello["ties"],
        pressure=carico,
    )

    esito: dict[str, object] = {
        "tipo": tipo,
        "sorgente": str(sorgente),
        "modello": modello["metriche"],
        "blocchi": modello["blocchi"],
        "hexa": quality.hexa_metrics(nodi, elementi),
        "export": export,
        "nota_giunzioni": modello["metriche"]["vincolo_giunzioni"],
        "nota_armatura": (
            "modello a calcestruzzo omogeneo: l'armatura e' fuori ambito per "
            "decisione dell'autore, non per dimenticanza, e il dato resta nel "
            "disegno. Un telaio in cemento armato modellato senza armatura non "
            "e' il telaio vero"
        ),
    }
    io.scrivi_atomico(
        out / MODEL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito
```

Aggiungi `quality` all'import da `meshrec.core` se non c'e' gia'.

- [ ] **Step 4: `export_model` accetta le tre card nuove**

In `abaqus.export_model`, aggiungi alla firma, dopo `element_type`:

```python
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str], ...] = (),
    pressure: tuple[str, float] | None = None,
```

e passali a `write_inp` insieme agli altri argomenti. Nel dizionario restituito aggiungi:

```python
        "element_surfaces": {
            nome: len(coppie) for nome, coppie in (element_surfaces or {}).items()
        },
        "surface_area": {
            nome: surface_area(aligned, elements, coppie, tipo)
            for nome, coppie in (element_surfaces or {}).items()
        },
        "ties": [nome for nome, _dipendente, _indipendente in ties],
        "pressure": None if pressure is None else {"surface": pressure[0], "value": pressure[1]},
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_pipeline.py tests/test_abaqus.py -v`
Expected: PASS.

- [ ] **Step 6: Il comando `model`**

In `_build_parser`:

```python
    model_command = commands.add_parser(
        "model", help="genera un modello parametrico come corsa figlia"
    )
    model_command.add_argument("config", type=Path)
    model_command.add_argument(
        "--tipo", choices=("estruso", "primitive"), required=True,
        help="estruso conserva sezione e fuori piombo misurati; primitive li raddrizza",
    )
    model_command.add_argument(
        "--out-dir", type=Path, default=None,
        help="cartella della corsa figlia; se omessa, quella della madre col suffisso del tipo",
    )
```

In `main`, accanto al ramo `wall`:

```python
    if args.command == "model":
        try:
            cfg = load_config(args.config)
            destinazione = args.out_dir
            if destinazione is None:
                madre = Path(cfg.run.out_dir)
                destinazione = madre.with_name(f"{madre.name}-{args.tipo}")
            esito = pipeline.genera_modello(cfg, args.tipo, destinazione)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0
```

- [ ] **Step 7: Il test del comando**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_model_scrive_la_cartella_col_suffisso_del_tipo(tmp_path):
    """La cartella predefinita e' quella della madre col suffisso: nessuna
    corsa figlia scrive dentro la cartella della madre, che e' il risultato di
    un'altra elaborazione."""
    cfg = _config_di_prova(tmp_path)
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)
    pipeline.run(cfg)

    assert cli.main(["model", str(percorso), "--tipo", "primitive"]) == 0

    madre = Path(cfg.run.out_dir)
    figlia = madre.with_name(f"{madre.name}-primitive")
    assert (figlia / "wall_model.inp").exists()
    assert not (madre / pipeline.MODEL_FILENAME).exists()
```

- [ ] **Step 8: Eseguire e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/pipeline.py meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/cli.py meshrec/tests/test_pipeline.py meshrec/tests/test_cli.py
git commit -m "feat(fase-4): i modelli parametrici come corse figlie con deck proprio"
```

---

