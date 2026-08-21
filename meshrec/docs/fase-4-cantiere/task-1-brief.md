## Task 1: Fondamenta — gmsh dipendenza vera, i due blocchi di configurazione, lo step 12 nel registro, l'impronta storica protetta

**Files:**
- Modify: `meshrec/pyproject.toml`
- Modify: `src/meshrec/core/config.py`
- Modify: `src/meshrec/core/steps.py`
- Modify: `src/meshrec/core/sweep.py`
- Test: `tests/test_config.py`, `tests/test_steps.py`, `tests/test_sweep.py`

**Interfaces:**
- Consumes: niente.
- Produces: `config.WallConfig`; `config.ModelConfig`; `PipelineConfig.wall: WallConfig`; `PipelineConfig.model: ModelConfig`; `steps.STEP_KEYS` di dodici elementi con `"12_wall"` in coda; `steps.STEP_BLOCKS[12] == ("wall",)`; `sweep.BLOCCHI_FUORI_IMPRONTA: tuple[str, ...]`.

- [ ] **Step 1: Il test di regressione che protegge le 22 righe storiche**

Sostituisci in `tests/test_config.py` il corpo di `test_l_impronta_di_una_corsa_registrata_non_cambia` con questo, e aggiungi il secondo test subito sotto:

```python
def test_l_impronta_di_una_corsa_registrata_non_cambia():
    """Le impronte della Fase 2 vivono nei registri: allargare PipelineConfig
    senza escludere il blocco nuovo cambierebbe la provenienza di ogni riga
    della tabella sperimentale della tesi.

    Il test non fissa un valore magico: rilegge i due registri veri, rivalida
    la configurazione incorporata in ciascuna riga e ricalcola l'impronta. Se
    coincide con quella registrata, la riga e' ancora derivabile dalla
    configurazione che dichiara.
    """
    import json

    from meshrec.core.sweep import fingerprint

    radice = Path(__file__).resolve().parents[1] / "experiments"
    righe = 0
    for registro in sorted(radice.glob("*/registro.jsonl")):
        for riga in registro.read_text(encoding="utf-8").splitlines():
            if not riga.strip():
                continue
            voce = json.loads(riga)
            cfg = PipelineConfig.model_validate(voce["config"])
            assert fingerprint(cfg) == voce["fingerprint"], (
                f"{registro}: la riga {righe + 1} non e' piu' derivabile dalla "
                "propria configurazione"
            )
            righe += 1
    assert righe == 22, f"attese 22 righe nei due registri, trovate {righe}"


def test_i_blocchi_nuovi_stanno_in_pipelineconfig_e_fuori_dall_impronta():
    """I due blocchi della Fase 4 viaggiano con la configurazione, perche' lo
    step 12 li legge, e restano fuori dall'impronta di sweep, perche' nessun
    asse della Fase 2 li tocca."""
    from meshrec.core.sweep import BLOCCHI_FUORI_IMPRONTA

    campi = set(PipelineConfig.model_fields)
    assert {"wall", "model"} <= campi
    assert set(BLOCCHI_FUORI_IMPRONTA) == {"run", "wall", "model"}
    assert set(BLOCCHI_FUORI_IMPRONTA) <= campi
```

- [ ] **Step 2: Eseguirli e vedere fallire il secondo**

Run: `uv run pytest tests/test_config.py -k impronta -v`
Expected: il primo PASSA gia' oggi — e' la fotografia dello stato attuale, 22 righe su 22 — il secondo FALLISCE con `ImportError: cannot import name 'BLOCCHI_FUORI_IMPRONTA'`.

- [ ] **Step 3: `WallConfig` e `ModelConfig` in `config.py`**

In `config.py`, subito dopo `PipelineConfig` e prima di `load_config`, aggiungi i due modelli. Nessun numero del provino: le soglie sono angoli, frazioni e multipli della spaziatura, e i riscontri dichiarati nascono tutti a `None`.

```python
class WallConfig(_ModelloBase):
    """Step 12: il prior geometrico. Il pezzo e' un telaio di membrature prismatiche.

    Nessun valore qui dentro viene dal provino di laboratorio. Le soglie sono
    angoli, frazioni e multipli della spaziatura media della nuvola: la
    grandezza sorvegliata e' la costanza dello spessore, non il suo valore, e
    una soglia di quota sarebbe una costante tarata sulla scansione di oggi
    (secondo principio di prodotto).
    """

    cell_factor: float = Field(
        default=4.0,
        gt=0.0,
        description=(
            "lato della cella quadrata, in multipli della spaziatura media. E' il "
            "«metodo delle colonne» di docs/fase-1-tolleranza-set.md, dove il "
            "fattore 4 e' misurato e non scelto: con una cella larga quanto la "
            "spaziatura la griglia diventa piu fine dei triangoli della faccia e "
            "una colonna su dieci risulta vuota per puro artefatto di griglia"
        ),
    )
    thickness_tolerance: float = Field(
        default=0.15,
        gt=0.0,
        lt=1.0,
        description=(
            "scarto relativo entro cui due celle adiacenti contano come «stesso "
            "spessore», e quindi come stessa membratura. E' la forma numerica di "
            "«quasi costante»: le membrature sono le regioni connesse a spessore "
            "quasi costante, e questa e' l'unica soglia della scomposizione"
        ),
    )
    min_cells: int = Field(
        default=12,
        gt=0,
        description=(
            "celle minime perche' una regione connessa sia una membratura. Sotto "
            "questo numero la regione e' rumore di griglia e non ha abbastanza "
            "celle perche' una direzione principale sia stimabile"
        ),
    )
    floor_angle_deg: float = Field(
        default=15.0,
        gt=0.0,
        lt=90.0,
        description=(
            "un piano estratto con la normale entro questo angolo dalla verticale "
            "e' candidato pavimento. Il pavimento non e' una membratura e va "
            "scartato come piano, mai come quota"
        ),
    )
    floor_min_ratio: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description=(
            "frazione minima dei punti perche' un piano quasi orizzontale sia il "
            "pavimento e non la faccia superiore di una membratura. Le due "
            "condizioni valgono insieme: orizzontale e esteso"
        ),
    )
    contour_tolerance: float = Field(
        default=5.0,
        gt=0.0,
        description=(
            "tolleranza [mm] con cui il contorno di sezione misurato viene "
            "semplificato. Un contorno con un vertice per punto rilevato porta "
            "nella mesh il rumore dello scanner invece della forma della sezione"
        ),
    )
    parallelism_deg: float = Field(
        default=5.0,
        gt=0.0,
        lt=90.0,
        description=(
            "controllo intrinseco: angolo massimo fra le due facce opposte di una "
            "regione. Oltre, la regione non ha una sezione e il prior si rifiuta "
            "invece di darne una media priva di senso"
        ),
    )
    face_coverage: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "controllo intrinseco: frazione minima delle celle della regione che "
            "vedono entrambe le facce. E' la lezione gia' pagata su FACE_FRONT e "
            "FACE_BACK: una faccia vista da pochi punti produce un piano finto"
        ),
    )
    section_dispersion: float = Field(
        default=0.10,
        gt=0.0,
        description=(
            "controllo intrinseco: dispersione relativa massima della sezione "
            "lungo l'asse. Oltre, la regione non e' un prisma e viene riportata "
            "come tale invece di essere spacciata per una membratura"
        ),
    )
    union_tolerance: float = Field(
        default=0.02,
        gt=0.0,
        description=(
            "controllo intrinseco: scarto relativo ammesso fra la somma dei "
            "volumi delle membrature e il volume della loro unione. Oltre c'e' "
            "doppio conteggio alle giunzioni, che nessuna metrica di qualita' "
            "vedrebbe"
        ),
    )
    union_step_factor: float = Field(
        default=2.0,
        gt=0.0,
        description=(
            "passo del conteggio di celle con cui si misura il volume "
            "dell'unione, in multipli della spaziatura media. Piu' fine, piu' "
            "lento e piu' preciso: l'errore di discretizzazione viene riportato "
            "accanto al risultato, non nascosto"
        ),
    )
    membrature_attese: int | None = Field(
        default=None,
        gt=0,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: quante membrature l'operatore si "
            "aspetta. Assente per definizione su un pezzo nuovo. Se dichiarato il "
            "prior riporta lo scarto; se assente riporta cio' che ha trovato e "
            "non inventa un'aspettativa"
        ),
    )
    sezioni_nominali: list[tuple[float, float]] | None = Field(
        default=None,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: le sezioni nominali attese [mm], "
            "dal disegno se esiste. Non sono la fonte del modello: i modelli "
            "parametrici misurano la sezione sulla nuvola, e il nominale serve "
            "solo a contraddire la misura"
        ),
    )
    volume_atteso: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: il volume complessivo atteso "
            "[mm^3], dal disegno se esiste"
        ),
    )


class ModelConfig(_ModelloBase):
    """I due modelli parametrici e il loro deck. Non e' letto da alcuno step di run().

    La scelta di quali modelli generare non sta qui, ed e' deliberato: e'
    un'azione, non un parametro di elaborazione. Se ci stesse, rigenerare un
    modello in piu' cambierebbe l'impronta di una corsa che non e' cambiata.
    """

    element: Literal["C3D8I", "C3D8", "C3D8R"] = Field(
        default="C3D8I",
        description=(
            "un telaio lavora a flessione. C3D8 a integrazione piena si "
            "irrigidisce a taglio e restituisce spostamenti troppo piccoli, un "
            "errore invisibile guardando la mesh; C3D8R ha il problema opposto, i "
            "modi a clessidra. C3D8I e' supportato sia da Abaqus sia da CalculiX"
        ),
    )
    min_layers: int = Field(
        default=3,
        ge=3,
        description=(
            "strati di elementi minimi nello spessore, imposti dal codice e non "
            "suggeriti. Con uno o due la flessione nello spessore non e' "
            "rappresentata e il risultato e' sbagliato senza alcun segnale. Il "
            "vincolo ge=3 e' il vincolo stesso: non si scende sotto"
        ),
    )
    target_size: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "passo caratteristico della mesh [mm]. None = la sezione minima "
            "divisa per min_layers, cioe' il passo piu' grosso che rispetta il "
            "vincolo degli strati"
        ),
    )
    tie_name_prefix: str = Field(
        default="GIUNZIONE",
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "prefisso dei nomi dei vincoli *TIE fra membrature adiacenti. Stesso "
            "vincolo di caratteri del nome del materiale, e per la stessa "
            "ragione: finisce interpolato in un deck scritto in ascii"
        ),
    )
    lateral_nset: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "CARICO LATERALE, facoltativo: nome della superficie di elemento su "
            "cui agisce la pressione. Assente se non richiesto"
        ),
    )
    lateral_pressure: float | None = Field(
        default=None,
        description="CARICO LATERALE, facoltativo: pressione [MPa] sulla superficie nominata",
    )

    @model_validator(mode="after")
    def _carico_completo_o_assente(self) -> "ModelConfig":
        if (self.lateral_nset is None) != (self.lateral_pressure is None):
            raise ValueError(
                "il carico laterale si dichiara per intero o non si dichiara: "
                f"lateral_nset={self.lateral_nset!r} e "
                f"lateral_pressure={self.lateral_pressure!r}. Meta' dichiarazione "
                "produrrebbe un deck con una card muta o con una pressione "
                "applicata a nulla"
            )
        return self
```

**Nota d'ordine:** `WallConfig` e `ModelConfig` vanno definiti **prima** di `PipelineConfig` nel file, perche' `PipelineConfig` li annota. Se lo Step 3 li ha messi dopo, spostali sopra `class PipelineConfig` — l'ordine di definizione e' l'unico vincolo.

- [ ] **Step 4: Agganciarli a `PipelineConfig` e alzare il tetto di `to_step`**

Dentro `PipelineConfig`, fra `analysis` e `run`:

```python
    wall: WallConfig = Field(default_factory=WallConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
```

In `RunConfig`, il campo `to_step` diventa:

```python
    to_step: int = Field(
        default=12,
        ge=1,
        le=12,
        description=(
            "ultimo step eseguito. Serve all'interfaccia, che esegue uno step "
            "alla volta: from_step e to_step uguali eseguono soltanto quello. "
            "Il tetto e' 12 dalla Fase 4: lo step 12 e' il prior geometrico, e "
            "chiude la corsa madre. from_step resta fermo a 9 e non lo segue, "
            "per la ragione scritta la'. "
            "Con validate_assignment attivo il validatore incrociato rifiuta "
            "ogni stato intermedio incoerente, e nessun ordine di assegnazione "
            "e' sicuro: restringendo un intervallo verso l'alto rompe to_step "
            "per primo, verso il basso rompe from_step. I due campi si "
            "assegnano quindi insieme, con una sola validazione dell'oggetto "
            "intero (RunConfig.model_validate su model_dump aggiornato), mai "
            "uno alla volta"
        ),
    )
```

E in coda alla descrizione di `from_step`, dentro la stringa gia' presente, aggiungi:

```
            " Lo step 12 (prior geometrico) e' l'ultimo e non e' un punto di "
            "ripresa: legge 02_segmented.ply, che e' gia' cio' che una ripresa "
            "da 3 in poi ricarica. Chi vuole il solo prior usa `meshrec wall`, "
            "che e' un'azione e non una ripresa."
```

- [ ] **Step 5: Lo step 12 nel registro degli step**

In `steps.py`, sostituisci il commento sopra `STEP_KEYS` e aggiungi la chiave e il blocco:

```python
# Le dodici chiavi che una corsa completa scrive in metrics.json. Lo step 7 non
# ha artefatto proprio ma ha metriche, quindi c'e' anche lui. Lo step 12 e' il
# prior geometrico della Fase 4: chiude la corsa madre e non e' un punto di
# ripresa.
```

In coda a `STEP_KEYS`, dopo `"11_export",`, la riga `"12_wall",`.
In coda a `STEP_BLOCKS`, dopo `11: ("tet", "analysis"),`, la riga `12: ("wall",),`.

- [ ] **Step 6: `fingerprint` esclude i blocchi nuovi, `expand` rifiuta un asse che ci punta**

In `sweep.py`, sopra `def fingerprint`:

```python
# I blocchi di PipelineConfig che non entrano nell'impronta di sweep.
# `run` non ci entra perche' out_dir e from_step non cambiano il risultato
# dell'elaborazione. `wall` e `model` non ci entrano perche' sono nati con la
# Fase 4, dopo che i registri della Fase 2 erano gia' scritti: includerli
# cambierebbe l'impronta di ogni riga gia' registrata, cioe' la provenienza
# della tabella sperimentale della tesi, e nessun asse di sweep li tocca --
# tutti gli assi della griglia stanno a monte dello step 11. La falla che
# l'esclusione apre e' chiusa da `expand`, che rifiuta un asse su un blocco
# escluso invece di produrre candidati indistinguibili.
BLOCCHI_FUORI_IMPRONTA: tuple[str, ...] = ("run", "wall", "model")
```

Dentro `fingerprint`, al posto di `payload.pop("run", None)`:

```python
    for blocco in BLOCCHI_FUORI_IMPRONTA:
        payload.pop(blocco, None)
```

La prima riga della docstring di `fingerprint` diventa:

```python
    """Sha256 della configurazione canonica, esclusi i blocchi di BLOCCHI_FUORI_IMPRONTA.
```

e sotto la spiegazione gia' presente aggiungi, senza lettere accentate, il paragrafo del commento qui sopra.

In `expand`, come primo controllo del corpo:

```python
    for asse in experiment.axes:
        blocco = asse.path.split(".")[0]
        if blocco in BLOCCHI_FUORI_IMPRONTA:
            raise ValueError(
                f"l'asse '{asse.path}' punta al blocco '{blocco}', che non entra "
                "nell'impronta: due candidati che differissero solo per quel "
                "valore avrebbero la stessa impronta e il registro non potrebbe "
                "distinguerli"
            )
```

- [ ] **Step 7: Eseguire i test dei tre moduli**

Run: `uv run pytest tests/test_config.py tests/test_steps.py tests/test_sweep.py -v`
Expected: PASS. In particolare `test_l_impronta_di_una_corsa_registrata_non_cambia` conta ancora 22 righe su 22 con i due blocchi nuovi in `PipelineConfig`.

- [ ] **Step 8: Il test dell'asse rifiutato e quello della catena di impronte**

In coda a `tests/test_sweep.py`:

```python
def test_un_asse_su_un_blocco_fuori_impronta_viene_rifiutato(tmp_path):
    """Due candidati indistinguibili nel registro sarebbero peggio di nessuno
    sweep: l'errore arriva prima di eseguire, non dopo aver scritto le righe."""
    from meshrec.core.config import AxisSpec, ExperimentConfig, InputConfig

    from materiale import crea_config

    esperimento = ExperimentConfig(
        name="prova",
        base=tmp_path / "base.yaml",
        axes=[AxisSpec(path="wall.min_cells", values=[8, 12])],
    )
    base = crea_config(input=InputConfig(path=tmp_path / "n.ply"))
    with pytest.raises(ValueError, match="non entra nell'impronta"):
        sweep.expand(esperimento, base)
```

In coda a `tests/test_steps.py`:

```python
def test_gli_step_sono_dodici_e_l_ultimo_e_il_prior():
    assert len(steps.STEP_KEYS) == 12
    assert steps.STEP_KEYS[-1] == "12_wall"
    assert steps.STEP_BLOCKS[12] == ("wall",)


def test_lo_step_dodici_non_cambia_le_impronte_degli_undici_precedenti(tmp_path):
    """La catena di impronte si allunga in coda: aggiungere lo step 12 non puo'
    invalidare un artefatto gia' scritto dagli step precedenti."""
    cfg = _config(tmp_path)
    impronte = steps.step_fingerprints(cfg)
    assert set(impronte) == set(range(1, 13))

    cfg_diverso = _config(tmp_path)
    cfg_diverso.wall.min_cells = cfg.wall.min_cells + 1
    diverse = steps.step_fingerprints(cfg_diverso)

    for numero in range(1, 12):
        assert diverse[numero] == impronte[numero], f"lo step {numero} non doveva cambiare"
    assert diverse[12] != impronte[12]
```

- [ ] **Step 9: Eseguirli**

Run: `uv run pytest tests/test_steps.py tests/test_sweep.py -v`
Expected: PASS.

- [ ] **Step 10: gmsh da extra a dipendenza**

In `meshrec/pyproject.toml`, togli `gmsh>=4.15.2` da `[project.optional-dependencies].feasibility` e mettilo in `dependencies`:

```toml
    "fastapi>=0.141.1",
    "uvicorn>=0.52.3",
    # Generatore della mesh esaedrica dei modelli parametrici (core/hexa.py):
    # serve a ogni corsa di un modello, non a una prova di fattibilita', quindi
    # non e' piu' un extra. Era gia' dichiarato fra le dipendenze facoltative e
    # gia' usato da core/gmsh_backend.py.
    "gmsh>=4.15.2",
]
```

e lascia il gruppo vuoto:

```toml
[project.optional-dependencies]
feasibility = []
```

- [ ] **Step 11: Installare e verificare che i tre test saltati non saltino piu'**

Run: `uv sync`
Poi: `uv run pytest tests/test_gmsh_backend.py -v`
Expected: PASS, tre test **eseguiti** e non saltati. Se uno fallisce nel merito invece che per l'import, fermati e segnala: significa che gmsh su questa macchina si comporta diversamente da quanto la Fase 0 aveva misurato, ed e' un fatto da scrivere prima di costruirci sopra.

- [ ] **Step 12: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. I passati salgono rispetto ai 402 di partenza e i saltati scendono dai 3: i tre `importorskip` su gmsh non saltano piu'. Se resta qualche altro salto, e' di altra origine e va lasciato dov'e'.

- [ ] **Step 13: Commit**

```bash
git add meshrec/pyproject.toml meshrec/uv.lock meshrec/src/meshrec/core/config.py meshrec/src/meshrec/core/steps.py meshrec/src/meshrec/core/sweep.py meshrec/tests/test_config.py meshrec/tests/test_steps.py meshrec/tests/test_sweep.py
git commit -m "feat(fase-4): i due blocchi del prior, lo step 12 e gmsh come dipendenza"
```

---

