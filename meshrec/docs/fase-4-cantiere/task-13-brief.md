> ## LEGGI QUESTO PRIMA DEL RESTO — correzioni vincolanti del 20/08/2026
>
> Il corpo del brief qui sotto e' la prima stesura: contiene **due difetti
> bloccanti**, tre seri e un minore. Dove questa sezione e il corpo divergono,
> **vale questa**.
>
> Ogni affermazione qui e' stata riletta nel codice, con file e riga, e le due
> piu' importanti le ho **eseguite**. Se una ti risulta falsa, **fermati e dillo
> con la prova** invece di adattare il codice per farla tornare: in questa fase
> e' successo otto volte che avesse ragione chi eseguiva e non chi scriveva il
> piano.
>
> ### E1 (BLOCCANTE) — `triangoli_da_quadrilateri` non fa quello che il test afferma
>
> Il corpo usa `np.argsort(np.repeat(np.arange(len(quad)), 2), kind="stable")`
> come indice di riordino. **Quell'indice e' l'identita'**: `repeat([0,1],2)` da'
> `[0,0,1,1]`, che e' gia' ordinato, quindi `argsort` restituisce `[0,1,2,3]` e
> la permutazione non permuta niente. Eseguito:
>
> ```
> indice: [0 1 2 3]
> risultato:  [[0 1 2]
>              [4 5 6]
>              [0 2 3]
>              [4 6 7]]
> ```
>
> I due triangoli dello stesso quadrilatero finiscono agli indici 0 e **2**, non
> 0 e 1: il test `assert triangoli[1].tolist() == [0, 2, 3]` fallisce, e su una
> mesh vera l'ordine delle facce non sarebbe piu' quello dei quadrilateri
> d'origine.
>
> L'interlacciamento si scrive senza permutazioni, impilando sull'asse 1:
>
> ```python
>     quad = np.asarray(quadrilateri, dtype=np.int64)
>     # stack sull'asse 1: i due triangoli dello stesso quadrilatero restano
>     # adiacenti, e l'ordine delle facce resta quello dei quadrilateri d'origine.
>     return np.ascontiguousarray(
>         np.stack([quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]], axis=1).reshape(-1, 3)
>     )
> ```
>
> Verificato: `[[0 1 2] [0 2 3] [4 5 6] [4 6 7]]`.
>
> ### E2 (BLOCCANTE) — il corpo dell'errore non ha una chiave `detail`
>
> Il corpo asserisce `risposta.json()["detail"]`. `detail` e' la convenzione di
> `HTTPException`, che questo server **non usa**: il gestore globale di
> `create_app` (`server.py:274-277`) risponde
> `{"errore": type(errore).__name__, "messaggio": str(errore)}`, ed e' scritto
> per esteso nel commento sopra («L'errore torna strutturato, con il tipo,
> perche' l'interfaccia possa dirlo»). Lo stato 400 atteso e' invece giusto.
>
> ```python
>     corpo = risposta.json()
>     assert risposta.status_code == 400
>     assert corpo["errore"] == "ValueError"
>     assert "estruso" in corpo["messaggio"]
> ```
>
> ### E3 (SERIO) — `/api/membrature` etichetta con una chiave che nessuno scrive
>
> Il corpo scrive `quanti = int(membratura.get("punti_disegnati", 0))`.
> **`punti_disegnati` non esiste in nessun punto del progetto.** `wall.prior`
> scrive `"punti": int(len(m.punti))` (`wall.py:737`), cioe' il **conteggio**,
> non gli indici. Col `get(..., 0)` il ciclo lascia l'intero array a `-1.0` e
> l'endpoint risponde «nessuna membratura» per ogni punto: un difetto **muto**,
> che nessun test del corpo intercetta.
>
> C'e' un aggravante di forma: trenta righe piu' sotto il corpo ha una «Nota
> vincolante» che **ammette** che quel blocco e' sbagliato e prescrive di
> sostituirlo. Un implementatore che copia il blocco e prosegue non ci arriva.
> **Togli il codice sbagliato invece di lasciarlo accanto alla sua smentita**: il
> blocco diventa la versione che la Nota descrive, con `"indici": m.punti.tolist()`
> aggiunto in `wall.prior` e l'incrocio con la mappa `gruppi` che `decimate_file`
> restituisce, esattamente come fa gia' `/api/cluster` (`server.py:570`).
>
> ### E4 (SERIO) — `/api/rigonfiamento` promette una mappa e restituisce tre numeri
>
> Il corpo dice «la mappa di rigonfiamento di una membratura, **un valore per
> cella**», e poi risponde `campo_per_punto(np.array([min, max, p95]))` — tre
> numeri — con un'intestazione `X-Celle` che ne dichiara migliaia. Un viewport
> che chiedesse una mappa di colore riceverebbe tre valori.
>
> La causa: `12_wall.json` **non contiene** la mappa. `wall.prior` serializza il
> solo aggregato (`wall.py:747-753`); la mappa per cella vive in memoria dentro
> `Membratura.rigonfiamento` e non arriva su disco.
>
> **Ruling AM — l'endpoint dichiara l'aggregato, non si aggiunge un artefatto.**
> Nulla in questa fase consuma una mappa per cella, e scriverla vorrebbe dire un
> `.npy` accanto al JSON, cioe' un artefatto nuovo con la sua provenienza da
> gestire. Quindi:
>
> - l'endpoint restituisce i tre estremi **come JSON**, con le chiavi `min`,
>   `max`, `p95` e il numero di celle: tre numeri non hanno bisogno del percorso
>   binario, e passarci li' dentro e' cio' che rendeva credibile la promessa;
> - il nome e la docstring dicono che e' l'aggregato, e **dicono anche dove sta
>   la mappa vera** e cosa servirebbe per averla, cosi' chi la cerchera' un
>   giorno non ricomincia da zero;
> - niente intestazione `X-Celle` su una risposta che non e' un campo per punto.
>
> ### E5 (SERIO) — lo step 12 non parte da «esegui da qui in poi»
>
> `server.py:408-410` e' fermo a 11 in due punti scritti a mano:
>
> ```python
>         lavoratore.start(config_path, numero, 11)
>         return {"avviato": numero, "fino_a": 11}
> ```
>
> Dal Task 9 gli step sono **dodici**, e il Task 14 mettera' il dodicesimo nella
> colonna dell'interfaccia. Cosi' com'e', l'utente preme «esegui da qui in poi»
> e la riga dodici resta «mai eseguito» senza spiegazione. Nessuno dei due brief
> lo nominava.
>
> ```python
>     # 12 e non 11 dalla Fase 4: lo step 12 e' il prior geometrico e chiude la
>     # corsa madre. E' lo stesso numero del predefinito di RunConfig.to_step.
>     @app.post("/api/step/{numero}/from")
>     def esegui_da(numero: int) -> dict[str, object]:
>         lavoratore.start(config_path, numero, 12)
>         return {"avviato": numero, "fino_a": 12}
> ```
>
> con un test che lo sorveglia:
> `assert cliente.post("/api/step/9/from").json()["fino_a"] == 12`.
>
> ### E6 (MINORE) — `cfg_viewport` non esiste, e la cache e' un'altra cartella
>
> In `server.py` non esiste alcun `cfg_viewport`: l'idioma e'
> `ViewportConfig().max_points` (`server.py:498`), e l'ultimo argomento di
> `decimate_file` e' `CACHE_DIR` (`server.py:41`, `Path(".cache/viewport")`).
> Passando la cartella della corsa, `/api/membrature` decimerebbe in una cache
> diversa da quella di `/api/cloud/2` — rifacendo il lavoro **e** scrivendo cache
> dentro gli artefatti, che sono di sola lettura.
>
> ```python
>         punti, gruppi, _voxel = viewport.decimate_file(
>             Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2],
>             ViewportConfig().max_points, cfg.input.spacing_sample, cfg.input.seed,
>             CACHE_DIR,
>         )
> ```
>
> ---

## Task 13: il server — lo step 12, i modelli come azione, i campi per il viewport

**Files:**
- Modify: `src/meshrec/app/server.py`
- Modify: `src/meshrec/app/worker.py`
- Modify: `src/meshrec/core/viewport.py`
- Test: `tests/test_server.py`, `tests/test_viewport.py`, `tests/test_worker.py`

**Interfaces:**
- Consumes: `pipeline.calcola_prior`, `pipeline.genera_modello` (Task 9 e 10); `report.confronta` (Task 12).
- Produces:
  - `viewport.campo_per_punto(valori) -> bytes`; `viewport.triangoli_da_quadrilateri(quadrilateri) -> np.ndarray`.
  - `worker.Worker.start_comando(argomenti, etichetta)`.
  - `GET /api/wall`, `POST /api/wall`, `POST /api/model/{tipo}`, `GET /api/compare`, `GET /api/membrature`, `GET /api/rigonfiamento`.

- [ ] **Step 1: I test del viewport**

In coda a `tests/test_viewport.py`:

```python
def test_i_quadrilateri_diventano_due_triangoli_ciascuno():
    """La superficie di contorno di un esaedro e' fatta di quadrilateri, e
    three.js disegna triangoli: la divisione va fatta qui e non nel browser,
    dove nessun test la sorveglierebbe."""
    quadrilateri = np.array([[0, 1, 2, 3], [4, 5, 6, 7]], dtype=np.int64)

    triangoli = viewport.triangoli_da_quadrilateri(quadrilateri)

    assert triangoli.shape == (4, 3)
    assert triangoli[0].tolist() == [0, 1, 2]
    assert triangoli[1].tolist() == [0, 2, 3]


def test_il_campo_per_punto_esce_in_float32_come_le_coordinate():
    """Stessa macchina delle mappe di deviazione della Fase 3: cambia il campo
    scalare, non il trasporto."""
    valori = np.array([0.0, 1.5, -2.25])

    corpo = viewport.campo_per_punto(valori)

    assert len(corpo) == 3 * 4
    assert np.frombuffer(corpo, dtype="<f4") == pytest.approx(valori)
```

- [ ] **Step 2: Eseguirli, vederli fallire, implementare**

Run: `uv run pytest tests/test_viewport.py -k "quadrilater or campo" -v`
Expected: FAIL con `AttributeError`.

In `viewport.py`, in coda:

```python
def triangoli_da_quadrilateri(quadrilateri: np.ndarray) -> np.ndarray:
    """Ogni quadrilatero in due triangoli, tagliato sulla diagonale 0-2.

    La superficie di contorno di una mesh esaedrica e' fatta di quadrilateri, e
    three.js disegna triangoli. La divisione sta qui e non nel browser perche'
    nel browser nessun test la sorveglierebbe, ed e' la stessa ragione per cui
    la decimazione della nuvola sta nel core.
    """
    quad = np.asarray(quadrilateri, dtype=np.int64)
    return np.ascontiguousarray(
        np.vstack([quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]]).reshape(-1, 3)[
            np.argsort(np.repeat(np.arange(len(quad)), 2), kind="stable")
        ]
    )


def campo_per_punto(valori: np.ndarray) -> bytes:
    """Uno scalare per punto in Float32, per le mappe di colore.

    E' `to_float32` applicata a un campo invece che a coordinate: il viewport
    ha gia' le mappe di deviazione dalla Fase 3, e qui cambia il campo scalare
    e non la macchina.
    """
    return to_float32(np.asarray(valori, dtype=np.float64).ravel())
```

Run: `uv run pytest tests/test_viewport.py -v`
Expected: PASS.

- [ ] **Step 3: Il test del worker per un comando che non e' uno step**

In coda a `tests/test_worker.py`:

```python
def test_il_worker_esegue_anche_un_comando_che_non_e_uno_step(tmp_path):
    """Il prior e i modelli sono azioni, non step: passano dallo stesso
    sottoprocesso -- perche' e' il percorso con cui sono stati prodotti tutti i
    numeri delle Fasi 1 e 2 -- ma non hanno un numero di step."""
    lavoratore = worker.Worker()

    lavoratore.start_comando(["--version"], etichetta="prova")
    for _ in range(200):
        if not lavoratore.is_running():
            break
        time.sleep(0.05)

    assert lavoratore.step is None
    assert lavoratore.etichetta == "prova"
    assert lavoratore.exit_code is not None
```

- [ ] **Step 4: `start_comando` in `worker.py`**

Aggiungi `self.etichetta: str | None = None` a `__init__`, e:

```python
    def start_comando(self, argomenti: list[str], etichetta: str) -> None:
        """Avvia un comando di `meshrec` che non e' uno step della pipeline.

        Il prior e i modelli parametrici sono azioni e non step: non hanno un
        numero, non entrano nella colonna della pipeline e non invalidano nulla
        a valle. Passano pero' dallo stesso sottoprocesso degli step, per le
        stesse tre ragioni gia' misurate: un processo ucciso lascia un codice di
        uscita, il percorso eseguito e' esattamente quello della riga di
        comando, e l'avvio di un interprete costa pochi secondi.
        """
        if self.is_running():
            raise RuntimeError("uno step sta gia' girando: annullalo prima di avviarne un altro")
        with self._lucchetto:
            self._righe.clear()
        self.exit_code = None
        self.annullato = False
        self.step = None
        self.etichetta = etichetta
        self.avviato = time.monotonic()
        self._processo = subprocess.Popen(
            [sys.executable, "-m", "meshrec.cli", *argomenti],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        threading.Thread(target=self._leggi, daemon=True).start()
```

In `start`, aggiungi `self.etichetta = None` accanto a `self.step = from_step`, cosi' i due stati non si sovrappongono.

- [ ] **Step 5: I test degli endpoint**

In coda a `tests/test_server.py`:

```python
def test_il_prior_non_ancora_calcolato_lo_dice_invece_di_rispondere_vuoto(cliente, tmp_path):
    """Quinto principio di prodotto: chi arriva dopo non conosce gli step. Uno
    stato vuoto che insegna, non un 404 nudo."""
    risposta = cliente.get("/api/wall")

    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["calcolato"] is False
    assert "step 12" in corpo["motivo"]


def test_il_prior_calcolato_torna_membrature_e_regioni_scartate(cliente, tmp_path):
    import json

    from meshrec.core import pipeline

    corsa = _cartella_di_corsa(cliente)
    (corsa / pipeline.WALL_FILENAME).write_text(
        json.dumps({
            "regioni_trovate": 2,
            "membrature": [{"lunghezza": 1500.0, "sezione": [200.0, 140.0]}],
            "scartate": [{"regione": 1, "controlli_falliti": ["costanza_sezione"],
                           "esiti": {"costanza_sezione": {"passato": False, "valore": 0.4,
                                                            "soglia": 0.1}}}],
        }),
        encoding="utf-8",
    )

    corpo = cliente.get("/api/wall").json()

    assert corpo["calcolato"] is True
    assert len(corpo["prior"]["membrature"]) == 1
    assert corpo["prior"]["scartate"][0]["controlli_falliti"] == ["costanza_sezione"]


def test_generare_un_modello_e_una_azione_e_non_tocca_la_configurazione(cliente, tmp_path):
    """La selezione dei modelli non entra in config.yaml: rigenerare un modello
    in piu' cambierebbe l'impronta di una corsa che non e' cambiata."""
    prima = cliente.get("/api/config").json()

    risposta = cliente.post("/api/model/estruso")

    assert risposta.status_code == 200
    assert risposta.json()["avviato"] == "estruso"
    assert cliente.get("/api/config").json() == prima


def test_un_tipo_di_modello_inventato_viene_rifiutato(cliente):
    risposta = cliente.post("/api/model/asbuilt")

    assert risposta.status_code == 400
    assert "estruso" in risposta.json()["detail"]


def test_il_confronto_dal_server_dice_quali_modelli_mancano(cliente, tmp_path):
    corpo = cliente.get("/api/compare").json()

    assert set(corpo["mancanti"]) <= {"estruso", "primitive"}
    assert corpo["confrontabili"]["qualita_elementi"] is False
```

`_cartella_di_corsa(cliente)` e' l'aiuto gia' presente nel file che restituisce `Path` della cartella della corsa corrente; se non c'e', ricavala da `cliente.get("/api/run").json()["out_dir"]`.

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_server.py -k "prior or modello or confronto" -v`
Expected: FAIL con 404 sugli endpoint mancanti.

- [ ] **Step 7: Gli endpoint**

In `server.py`, dentro `create_app`, dopo `/api/metrics`:

```python
    @app.get("/api/wall")
    def prior_geometrico() -> dict[str, object]:
        """Il prior come sta sul disco. Un prior non calcolato lo dichiara.

        Uno stato vuoto che insegna e non un 404 nudo: l'utente successivo
        confermato non conosce gli step, e «non ancora calcolato, ecco come» e'
        l'unica risposta che gli serve.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            return {
                "calcolato": False,
                "motivo": (
                    "il prior geometrico non e' ancora stato calcolato: e' lo "
                    "step 12, e si ottiene eseguendo la corsa fino in fondo "
                    "oppure con il comando 'Calcola il prior' qui accanto"
                ),
                "prior": None,
            }
        with percorso.open(encoding="utf-8") as handle:
            return {"calcolato": True, "motivo": "", "prior": json.load(handle)}

    @app.post("/api/wall")
    def calcola_prior() -> dict[str, object]:
        lavoratore.start_comando(["wall", str(config_path)], etichetta="prior geometrico")
        return {"avviato": "wall"}

    @app.post("/api/model/{tipo}")
    def genera_modello(tipo: str) -> dict[str, object]:
        """Genera un modello parametrico. E' un'azione, non un parametro.

        Non scrive nulla in config.yaml: se lo facesse, rigenerare un modello in
        piu' cambierebbe l'impronta di una corsa che non e' cambiata.
        """
        if tipo not in ("estruso", "primitive"):
            raise ValueError(
                f"modello '{tipo}' sconosciuto: i modelli parametrici sono "
                "'estruso' e 'primitive'. as-built e' la corsa madre e non si genera"
            )
        madre = Path(corrente().run.out_dir)
        lavoratore.start_comando(
            ["model", str(config_path), "--tipo", tipo,
             "--out-dir", str(madre.with_name(f"{madre.name}-{tipo}"))],
            etichetta=f"modello {tipo}",
        )
        return {"avviato": tipo}

    @app.get("/api/compare")
    def confronto() -> dict[str, object]:
        """Il confronto sulle cartelle che esistono davvero.

        Le cartelle mancanti non vengono create ne' finte: il confronto dice
        quale modello manca invece di mettere un trattino in una colonna di
        numeri.
        """
        from meshrec.core import report

        madre = Path(corrente().run.out_dir)
        cartelle = [madre] + [
            madre.with_name(f"{madre.name}-{tipo}")
            for tipo in ("estruso", "primitive")
            if madre.with_name(f"{madre.name}-{tipo}").is_dir()
        ]
        return report.confronta(cartelle)
```

E i due endpoint binari per il viewport, accanto a `/api/mesh/{numero}`:

```python
    @app.get("/api/membrature")
    def membrature() -> Response:
        """Un'etichetta di membratura per punto della nuvola disegnata.

        E' la prova visiva che la scomposizione ha capito il pezzo, e si legge
        in un secondo dove nessuna metrica sarebbe cosi' rapida. -1 significa
        «nessuna membratura», che e' un'informazione e non un buco.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non e' ancora stato calcolato: e' lo step 12"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        punti, gruppi, _voxel = viewport.decimate_file(
            Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2],
            cfg_viewport.max_points, cfg.input.spacing_sample, cfg.input.seed,
            Path(cfg.run.out_dir),
        )
        etichette = np.full(len(punti), -1.0)
        scorrimento = 0
        for numero, membratura in enumerate(prior["membrature"]):
            quanti = int(membratura.get("punti_disegnati", 0))
            etichette[scorrimento : scorrimento + quanti] = float(numero)
            scorrimento += quanti
        return Response(
            content=viewport.campo_per_punto(etichette),
            media_type="application/octet-stream",
            headers={"X-Punti": str(len(punti)),
                      "X-Membrature": str(len(prior["membrature"]))},
        )

    @app.get("/api/rigonfiamento")
    def rigonfiamento(membratura: int) -> Response:
        """La mappa di rigonfiamento di una membratura, un valore per cella.

        Il viewport ha gia' le mappe di deviazione dalla Fase 3: cambia il
        campo scalare, non la macchina.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non e' ancora stato calcolato: e' lo step 12"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        if not 0 <= membratura < len(prior["membrature"]):
            raise ValueError(
                f"membratura {membratura} inesistente: il prior ne ha trovate "
                f"{len(prior['membrature'])}"
            )
        mappa = prior["membrature"][membratura]["rigonfiamento"]
        return Response(
            content=viewport.campo_per_punto(np.array([mappa["min"], mappa["max"], mappa["p95"]])),
            media_type="application/octet-stream",
            headers={"X-Celle": str(mappa["celle"]),
                      "X-Min": str(mappa["min"]), "X-Max": str(mappa["max"])},
        )
```

**Nota vincolante sull'endpoint `/api/membrature`:** perche' possa assegnare un'etichetta a ogni punto disegnato, `wall.prior` deve scrivere per ogni membratura anche gli indici dei propri punti dentro la nuvola segmentata. Aggiungi in `wall.prior`, nella voce di ciascuna membratura, la chiave `"indici": m.punti.tolist()`, e usa quella qui al posto di `punti_disegnati`, incrociandola con la mappa `gruppi` che `decimate_file` gia' restituisce — e' esattamente il meccanismo con cui il clic sul cluster della Fase 3 risale dai punti disegnati a quelli pieni. Se il file cresce troppo, scrivi gli indici in un `.npy` accanto invece che nel JSON, e dichiaralo nel documento del Task 15.

- [ ] **Step 8: Eseguire, suite, commit**

Run: `uv run pytest tests/test_server.py tests/test_worker.py tests/test_viewport.py -v`
Expected: PASS.
Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/app/server.py meshrec/src/meshrec/app/worker.py meshrec/src/meshrec/core/viewport.py meshrec/src/meshrec/core/wall.py meshrec/tests/test_server.py meshrec/tests/test_worker.py meshrec/tests/test_viewport.py
git commit -m "feat(fase-4): endpoint del prior, dei modelli e del confronto"
```

---

