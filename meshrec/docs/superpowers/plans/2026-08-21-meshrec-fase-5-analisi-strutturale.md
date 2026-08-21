# Fase 5 — Analisi strutturale: piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** far risolvere davvero i deck da CalculiX dentro la pipeline, dopo aver riparato il difetto di allineamento che oggi rende ogni risultato strutturale falso di due ordini di grandezza.

**Architecture:** un nuovo modulo `core/solve.py` esegue `ccx` e legge `.frd`/`.dat`; `pipeline.run` guadagna uno step 13 che scrive `13_solution.vtu` con i campi per nodo e solo scalari in `metrics.json`; `abaqus.py` raddrizza la terna sul verticale vero, scrive un deck a più casi di carico a zero avvisi, e misura una grandezza nuova che sorveglia il vincolo; il viewport riusa il percorso `.vtu` già esistente.

**Tech Stack:** Python 3, numpy, pydantic, meshio, CalculiX `ccx` 2.22, pytest, three.js (senza build).

**Spec:** [`../specs/2026-08-21-meshrec-fase-5-analisi-strutturale-design.md`](../specs/2026-08-21-meshrec-fase-5-analisi-strutturale-design.md)

## Global Constraints

- Unità: **mm, N, MPa, tonnellata, secondo**. Gravità 9810 mm/s².
- Un parametro di elaborazione ha il proprio predefinito in **un solo file**, `core/config.py`.
- **Nessun predefinito per grandezze che l'operatore deve dichiarare**: materiale, coefficiente di spinta, risultante del carico in sommità, numero di modi.
- Lingua di commenti, docstring, messaggi e documenti: **italiano**. Identificatori tecnici invariati: `C3D4`, `C3D10`, `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`, `ALL_WALL`, `min_ratio`, `nobisect`.
- **Sola lettura, mai riscrivere:** `runs/muro/`, `runs/lab_crop/`, `experiments/muro/`, `experiments/lab_crop/`.
- **Mai `git add -A`.** Ogni commit elenca i propri file.
- **Nessun numero del provino di laboratorio in `src/`.** I numeri dei banchi stanno nei test.
- **Ogni numero scritto in un brief, in un docstring o in un documento è misurato da chi lo scrive, adesso, sulla cosa di cui parla.** Verifica eseguendo, non leggendo.
- **Ogni test nuovo dichiara la mutazione che lo uccide e la applica davvero**, riportando l'esito nel rapporto di task.
- Suite: `uv run pytest tests -q --ignore=tests/feasibility` deve restare verde (555 passati al momento della stesura). I test che dipendono da `ccx` vanno in `tests/feasibility` con il marcatore `feasibility`.

## Il banco sintetico condiviso

Tasks 1, 2 e 4 usano lo stesso banco. Numeri del banco, non del pezzo vero. Misurato in fase di stesura di questo piano: `align_to_axes` di oggi lo allinea con l'asse z a **13,58°** dal verticale.

```python
# tests/test_abaqus.py
TELAIO_PIEDI_ASIMMETRICI = [
    ((0.0,    0.0,    0.0), (200.0,  800.0,  200.0)),   # piede largo
    ((0.0, 2200.0,    0.0), (200.0,  300.0,  200.0)),   # piede stretto
    ((0.0,  300.0,  200.0), (200.0,  200.0, 1600.0)),   # montante sinistro
    ((0.0, 2300.0,  200.0), (200.0,  200.0, 1600.0)),   # montante destro
    ((0.0,  300.0, 1800.0), (200.0, 2200.0,  200.0)),   # traverso
]
"""Portale con i due piedi di larghezza diversa.

L'asimmetria in basso inclina la direzione principale senza che la nuvola sia
inclinata: e' la forma esatta del difetto misurato su `lab_frame.pcd`, dove le
zapatas larghe e basse portano l'asse altezza a 22,43 gradi dal verticale.
La struttura poggia su tutta la luce, quindi un vincolo corretto deve coprirla
tutta: e' cio' che distingue "appoggio mancante" da "vuoto in mezzo".
"""
```

---

### Task 1: l'asse altezza è il verticale, non una direzione stimata

**Files:**
- Modify: `src/meshrec/core/abaqus.py:465-544` (`align_to_axes`)
- Modify: `src/meshrec/core/abaqus.py:622-626` (docstring di `build_node_sets`)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `synth.sample_frame_surface(prismi, spacing, noise=0.0, seed=0) -> np.ndarray`, `abaqus.fix_sign(direction) -> np.ndarray`
- Produces: `align_to_axes(nodes, reference=None) -> tuple[np.ndarray, np.ndarray, dict]` con firma invariata. La terza riga della rotazione (`transform[2, :3]`) vale ora esattamente `[0, 0, 1]`.

- [ ] **Step 1: scrivi il test che fallisce**

```python
def test_l_asse_altezza_e_il_verticale_anche_se_la_pca_pende():
    """La terna non lascia decidere l'altezza alla PCA.

    Sul banco a piedi asimmetrici la direzione principale piu' vicina al
    verticale sta 13,58 gradi fuori (misurato prima della correzione), e da li'
    discende il set BASE su un piede solo. Dopo la correzione l'asse altezza e'
    il verticale in ingresso per costruzione, e l'unica cosa ancora stimata e'
    l'imbardata, che e' quanto il docstring ha sempre dichiarato.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)

    _allineati, transform, _metriche = abaqus.align_to_axes(punti, reference=punti)

    assert transform[2, :3] == pytest.approx([0.0, 0.0, 1.0], abs=1e-12)
    # terna destrorsa e ortonormale: il determinante non e' un dettaglio, un -1
    # scambierebbe SIDE_LEFT con SIDE_RIGHT senza che nulla se ne accorga
    assert np.linalg.det(transform[:3, :3]) == pytest.approx(1.0, abs=1e-12)
    assert transform[:3, :3] @ transform[:3, :3].T == pytest.approx(np.eye(3), abs=1e-12)


def test_i_nodi_bassi_dopo_l_allineamento_coprono_tutta_la_luce():
    """Il vincolo prende entrambi i piedi, non uno.

    Misurato sul banco: prima della correzione i nodi entro 60 mm dal minimo di
    z-modello sono 131 e coprono lo 0,088 della lunghezza; dopo sono 654 e la
    coprono per intero.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)

    allineati, _transform, _metriche = abaqus.align_to_axes(punti, reference=punti)

    bassi = allineati[allineati[:, 2] <= allineati[:, 2].min() + 60.0]
    rapporto = float(np.ptp(bassi[:, 1]) / np.ptp(allineati[:, 1]))
    assert rapporto > 0.95, f"il vincolo copre solo {rapporto:.3f} della luce"
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_abaqus.py -k "asse_altezza or nodi_bassi" -v`
Expected: FAIL. Il primo su `transform[2, :3]` diverso da `[0,0,1]`; il secondo con `rapporto` circa 0,088.

- [ ] **Step 3: applica la correzione**

In `align_to_axes`, sostituisci il blocco che va dalla SVD alla costruzione di `rotation` (oggi righe 494-521, dalla `np.linalg.svd` a `rotation = np.stack(...)`) con:

```python
    # z e' il verticale del sistema in ingresso, non una direzione stimata. Il
    # docstring di questa funzione ha sempre dichiarato che lo scanner e'
    # livellato e che l'unica ambiguita' e' l'imbardata; fino alla Fase 5 il
    # codice lo dichiarava e poi lasciava scegliere l'altezza a una PCA a tre
    # dimensioni. Su `lab_frame.pcd` quella scelta cadeva a 22,43 gradi dal
    # verticale, perche' le zapatas larghe e basse tirano la direzione
    # principale, e da li' il set BASE prendeva un piede su due.
    z_dir = np.array([0.0, 0.0, 1.0])

    # Lo spessore si sceglie fra le sole direzioni orizzontali: PCA a due
    # dimensioni sulla proiezione. Cosi' l'imbardata resta l'unica grandezza
    # stimata, e l'assegnazione dell'altezza non dipende piu' da come la massa
    # e' distribuita in quota.
    piano = centred_reference[:, :2]
    _, _, principali = np.linalg.svd(piano, full_matrices=False)
    estensioni = np.ptp(piano @ principali.T, axis=0)
    stretta = principali[int(np.argmin(estensioni))]
    x_dir = fix_sign(np.array([stretta[0], stretta[1], 0.0]))

    # y come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori.
    y_dir = np.cross(z_dir, x_dir)

    rotation = np.stack([x_dir, y_dir, z_dir])
```

Aggiorna il docstring della funzione: l'assunzione «lo scanner e' livellato» resta, ma ora è ciò che il codice fa invece di ciò che presume, e va detto che su un pezzo fuori piombo `BASE` diventa un taglio orizzontale e non la base del pezzo.

- [ ] **Step 4: correggi il docstring che affermava il falso**

`build_node_sets`, righe 625-626, dice oggi «`BASE` e `TOP` sono verificati: l'asse z e' il verticale reale (vedi `align_to_axes`)». Era falso su `lab_frame.pcd` (22,43 gradi misurati). Riscrivilo dicendo che l'affermazione vale **per costruzione** dalla Fase 5, e da quando.

- [ ] **Step 5: esegui i test e verifica che passino**

Run: `uv run pytest tests/test_abaqus.py -q`
Expected: PASS, compresi i test preesistenti su `muro` e `lab_crop`. Se un test preesistente cade, il suo valore atteso veniva dalla terna vecchia: rimisuralo e aggiornalo nel commit, dichiarando nel messaggio quale valore è cambiato e di quanto.

- [ ] **Step 6: applica la mutazione e verifica che uccida il test**

Rimetti `z_dir` alla scelta per PCA (`vertical = principal[height_axis]`) e riesegui: entrambi i test nuovi devono cadere. Poi ripristina. Riporta l'esito nel rapporto di task.

- [ ] **Step 7: misura l'effetto sulle tre geometrie**

Non è una stima: esegui.

```bash
uv run python -c "
import json, math, numpy as np
for nome in ('muro','lab_crop'):
    T=json.load(open(f'runs/{nome}/metrics.json'))['11_export']['transform']
    print(nome, 'angolo vecchio', round(math.degrees(math.acos(T[2][2])),2))
"
```

Attesi dai `metrics.json` già su disco: `muro` 0,45°, `lab_crop` 0,39°. Scrivi nel rapporto di task di quanto si sposta ciascuna e se qualche estensione orizzontale è abbastanza vicina all'altra da rendere instabile l'assegnazione x/y (su `lab_crop` sono 176 contro 2759 mm: dichiara i valori che misuri, non questi).

- [ ] **Step 8: commit**

```bash
git add src/meshrec/core/abaqus.py tests/test_abaqus.py
git commit -m "fix(abaqus): l'asse altezza e' il verticale, non la direzione principale piu' vicina"
```

---

### Task 2: la grandezza che sorveglia il vincolo

**Files:**
- Modify: `src/meshrec/core/abaqus.py` (nuova funzione accanto a `footprint_coverage:572`, e chiamata in `export_model:770-800`)
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `abaqus.align_to_axes` corretta dal Task 1.
- Produces: `constraint_plan_extent(nodes: np.ndarray, indices: np.ndarray) -> dict[str, float]`, che restituisce `{"x": float, "y": float, "minimo": float}` dove `minimo` è il minore dei due rapporti. `export_model` aggiunge al proprio dizionario la chiave `"constraint_plan_extent"` con quel dizionario, e la chiave `"fixed_nset_coverage"` **resta** dov'è.

- [ ] **Step 1: scrivi il test che fallisce**

```python
def test_l_estensione_in_pianta_del_vincolo_vale_uno_su_due_piedi():
    """Un telaio a due piedi e' ben vincolato anche se e' vuoto in mezzo.

    E' la proprieta' che distingue questa grandezza da footprint_coverage: i due
    piedi coprono l'intera luce, quindi il rapporto vale 1 pur essendoci un
    vuoto fra loro. Se valesse meno di 1, la grandezza confonderebbe "vuoto in
    mezzo" con "manca un appoggio" e sarebbe inutilizzabile su un portale.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)
    allineati, _t, _m = abaqus.align_to_axes(punti, reference=punti)
    bassi = np.flatnonzero(allineati[:, 2] <= allineati[:, 2].min() + 60.0)

    esteso = abaqus.constraint_plan_extent(allineati, bassi)

    assert esteso["y"] == pytest.approx(1.0, abs=0.05)
    assert esteso["minimo"] == pytest.approx(min(esteso["x"], esteso["y"]))


def test_l_estensione_in_pianta_crolla_se_il_vincolo_tiene_un_angolo():
    """Un insieme ammucchiato in un angolo si vede, e footprint_coverage no.

    Misurato sul deck as-built del 21/08/2026: BASE aveva 278 nodi in una toppa
    y 574-808 su un pezzo lungo 3144, cioe' un rapporto di 0,074, mentre
    fixed_nset_coverage dichiarava 1,0. E' il caso che questa grandezza esiste
    per cogliere.
    """
    punti = synth.sample_frame_surface(TELAIO_PIEDI_ASIMMETRICI, spacing=25.0)
    allineati, _t, _m = abaqus.align_to_axes(punti, reference=punti)
    # un solo piede: i nodi bassi con y sotto il primo quarto della luce
    limite = allineati[:, 1].min() + 0.25 * np.ptp(allineati[:, 1])
    un_piede = np.flatnonzero(
        (allineati[:, 2] <= allineati[:, 2].min() + 60.0) & (allineati[:, 1] <= limite)
    )

    esteso = abaqus.constraint_plan_extent(allineati, un_piede)

    assert esteso["minimo"] < 0.5
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_abaqus.py -k estensione_in_pianta -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'constraint_plan_extent'`.

- [ ] **Step 3: scrivi la funzione**

Accanto a `footprint_coverage`, che **non si cancella**:

```python
def constraint_plan_extent(nodes: np.ndarray, indices: np.ndarray) -> dict[str, float]:
    """Quanto dell'impronta del pezzo l'insieme vincolato attraversa, per asse.

    Nasce da un difetto misurato il 21/08/2026: su `lab_frame.pcd` il set BASE
    teneva 278 nodi ammucchiati in una toppa larga 233 mm su un pezzo lungo
    3144, il telaio penzolava da un piede solo, lo spostamento sotto peso
    proprio usciva a 15,25 mm invece di 0,0367 — e `footprint_coverage`
    dichiarava 1,0. Non per un bug: quella misura risponde a "quanta parte
    dell'appoggio che vedo e' vincolata", e vedeva un piede solo.

    Questa grandezza risponde all'altra domanda. Vale 1 per un muro, e vale 1
    **anche per un telaio a due piedi**, perche' i due piedi attraversano
    l'intera luce pur essendo vuoti in mezzo: non confonde "vuoto in mezzo" con
    "manca un appoggio". Crolla quando l'insieme tiene un angolo di una cosa
    larga.

    Non ha parametri impliciti — nessun lato di cella, nessuna banda di
    contatto, nessun asse da scegliere — ed e' per questo che puo' fare da
    regola dove `footprint_coverage` resta una diagnosi. La soglia e' larga
    perche' la grandezza e' quella giusta: sul caso misurato il divario e' fra
    0,074 e 1.

    `footprint_coverage` resta accanto: insieme dicono piu' di ciascuna da sola
    — "l'insieme copre tutto l'appoggio che vede, e vede il 7% del pezzo".
    """
    points = np.asarray(nodes, dtype=np.float64)
    scelti = points[np.asarray(indices, dtype=np.int64)]
    if len(scelti) == 0:
        return {"x": 0.0, "y": 0.0, "minimo": 0.0}
    rapporti: dict[str, float] = {}
    for asse, nome in ((0, "x"), (1, "y")):
        pezzo = float(np.ptp(points[:, asse]))
        # Un pezzo senza estensione su un asse non ha nulla da coprire su
        # quell'asse: 1.0, non una divisione per zero e non uno 0.0 che
        # sembrerebbe un vincolo mancante.
        rapporti[nome] = 1.0 if pezzo == 0.0 else float(np.ptp(scelti[:, asse]) / pezzo)
    rapporti["minimo"] = min(rapporti["x"], rapporti["y"])
    return rapporti
```

- [ ] **Step 4: agganciala a `export_model`**

Nel dizionario restituito da `export_model` (righe 770-800), subito dopo `"fixed_nset_coverage"`, aggiungi:

```python
        "constraint_plan_extent": constraint_plan_extent(aligned, node_sets[cfg.fixed_nset]),
```

- [ ] **Step 5: esegui i test**

Run: `uv run pytest tests/test_abaqus.py tests/test_pipeline.py -q`
Expected: PASS.

- [ ] **Step 6: applica la mutazione**

Cambia `min(...)` in `max(...)` nel calcolo di `minimo`: il secondo test deve cadere, perché con un piede solo il rapporto su x resta alto mentre quello su y crolla. Ripristina e riporta l'esito.

- [ ] **Step 7: misura la soglia invece di sceglierla**

Nessuna soglia entra nel codice in questo task. Produci la tabella che la giustificherà, misurando la grandezza su tutte e tre le geometrie disponibili:

```bash
uv run python -c "
import json, numpy as np
from pathlib import Path
for nome in ('muro','lab_crop'):
    m=json.load(open(f'runs/{nome}/metrics.json'))
    print(nome, m['11_export'].get('constraint_plan_extent'), m['11_export']['fixed_nset_coverage'])
"
```

`muro` e `lab_crop` vanno rigenerati in una cartella di lavoro **fuori** da `runs/muro/` e `runs/lab_crop/`, che sono di sola lettura: usa `--out-dir`. Riporta nel rapporto di task i valori misurati, quale sarebbe il primo valore di soglia che non regge e quale la fa crollare. La soglia si scrive nel Task 7, con questa tabella in mano.

- [ ] **Step 8: commit**

```bash
git add src/meshrec/core/abaqus.py tests/test_abaqus.py
git commit -m "feat(abaqus): l'estensione in pianta del vincolo, accanto alla copertura che non la vede"
```

---

### Task 3: i casi di carico entrano nella configurazione, senza predefiniti

**Files:**
- Modify: `src/meshrec/core/config.py:210-234` (`AnalysisConfig`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.SpintaOrizzontale(coefficiente: float, asse: Literal["x","y"])`, `config.CaricoSommita(risultante: float, nset: str)`, `config.Modale(modi: int)`. `AnalysisConfig` guadagna `spinta: SpintaOrizzontale | None = None`, `carico_sommita: CaricoSommita | None = None`, `modale: Modale | None = None`. Nessun campo interno ha un predefinito numerico.

- [ ] **Step 1: scrivi il test che fallisce**

```python
def test_i_casi_di_carico_non_hanno_valori_predefiniti():
    """La spinta e il carico si dichiarano, come il materiale.

    Stessa ragione di config.Material: un predefinito di muratura a 1500 MPa
    era finito in silenzio nella configurazione di un telaio in calcestruzzo, e
    nessuno l'aveva scelto. Un coefficiente di spinta predefinito sarebbe lo
    stesso errore su una grandezza che nessun dato puo' suggerire.
    """
    with pytest.raises(ValidationError):
        config.SpintaOrizzontale()
    with pytest.raises(ValidationError):
        config.CaricoSommita()
    with pytest.raises(ValidationError):
        config.Modale()


def test_un_analisi_senza_casi_dichiarati_ha_il_solo_peso_proprio():
    """Chi non dichiara nulla ottiene l'unico caso derivabile dai dati.

    Densita' e gravita' sono gia' nella configurazione, quindi il peso proprio
    non e' un predefinito indovinato: e' l'unica cosa che il programma sa gia'.
    """
    analisi = config.AnalysisConfig(material=MATERIALE)

    assert analisi.spinta is None
    assert analisi.carico_sommita is None
    assert analisi.modale is None


def test_il_coefficiente_di_spinta_rifiuta_lo_zero_e_il_negativo():
    with pytest.raises(ValidationError):
        config.SpintaOrizzontale(coefficiente=0.0, asse="y")
    with pytest.raises(ValidationError):
        config.SpintaOrizzontale(coefficiente=-0.1, asse="y")
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_config.py -k "casi_di_carico or peso_proprio or coefficiente_di_spinta" -v`
Expected: FAIL con `AttributeError` sui tre nomi nuovi.

- [ ] **Step 3: scrivi le classi**

Sopra `AnalysisConfig` in `config.py`:

```python
class SpintaOrizzontale(_ModelloBase):
    """Forza di massa orizzontale, come frazione dell'accelerazione di gravita.

    E' la stessa card `*DLOAD, GRAV` del peso proprio, diretta di lato: non
    tocca nessun set di faccia, quindi non pretende di sapere quale faccia sia
    quale. `FACE_FRONT` e `FACE_BACK` sono misurati inutilizzabili su una
    scansione reale, e i nomi dei set di faccia sono convenzioni e non
    identificazioni fisiche (PRODUCT.md): un carico applicato a una faccia
    nominata sarebbe applicato dove crediamo, non dove sappiamo.

    Nessun predefinito: il coefficiente e' una decisione di chi analizza.
    """

    coefficiente: float = Field(
        gt=0.0, description="frazione dell'accelerazione di gravita, adimensionale"
    )
    asse: Literal["x", "y"] = Field(
        description="asse orizzontale del modello lungo cui la spinta agisce"
    )


class CaricoSommita(_ModelloBase):
    """Risultante verticale ripartita sui nodi di un insieme.

    La ripartizione e' uniforme per nodo, quindi il carico si concentra dove i
    nodi sono piu' fitti, e l'insieme e' costruito per tolleranza e non e' la
    faccia superiore certificata del pezzo. Sono due cose da dichiarare accanto
    ai risultati di questo caso, non da correggere qui.
    """

    risultante: float = Field(gt=0.0, description="risultante in N, ripartita sui nodi")
    nset: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="insieme di nodi su cui ripartire, di norma TOP",
    )


class Modale(_ModelloBase):
    """Analisi in frequenza.

    Costa poco e smentisce molto: un modello mal vincolato ha una prima
    frequenza fuori scala. Misurato il 21/08/2026 sull'as-built del telaio:
    21,19 Hz col vincolo corretto, 4,03 Hz col vincolo su un piede solo.
    """

    modi: int = Field(gt=0, description="numero di modi da estrarre")
```

E dentro `AnalysisConfig`, dopo `set_tolerance_factor`:

```python
    spinta: SpintaOrizzontale | None = None
    carico_sommita: CaricoSommita | None = None
    modale: Modale | None = None
```

Aggiungi `Literal` agli import di `typing` se non c'è già.

- [ ] **Step 4: esegui i test**

Run: `uv run pytest tests/test_config.py tests/test_server.py -q`
Expected: PASS. `test_server.py` è nell'elenco perché il server espone lo schema della configurazione all'interfaccia (`server.py:385-406`): tre blocchi nullabili nuovi devono attraversarlo senza rompere il pannello.

- [ ] **Step 5: applica la mutazione**

Dai a `coefficiente` un predefinito (`= 0.1`): il primo test deve cadere. Ripristina.

- [ ] **Step 6: commit**

```bash
git add src/meshrec/core/config.py tests/test_config.py
git commit -m "feat(config): spinta, carico in sommita e modale, dichiarati e senza predefiniti"
```

---

### Task 4: il deck a più casi di carico, a zero avvisi

**Files:**
- Modify: `src/meshrec/core/abaqus.py:29-166` (`write_inp`), `:676-800` (`export_model`)
- Test: `tests/test_abaqus.py`
- Test: `tests/feasibility/test_calculix.py`

**Interfaces:**
- Consumes: `config.SpintaOrizzontale`, `config.CaricoSommita`, `config.Modale` dal Task 3.
- Produces: `write_inp(..., analysis: AnalysisConfig | None = None)` — quando `analysis` porta i blocchi nuovi, il deck contiene i relativi `*STEP`. La firma esistente resta valida per ogni chiamante già scritto.

- [ ] **Step 1: scrivi i test che falliscono**

```python
def test_il_deck_non_contiene_piu_card_che_calculix_scavalca():
    """Zero avvisi non e' cosmesi: e' cio' che rende leggibile un avviso vero.

    Misurato il 21/08/2026 sul deck as-built: `ccx` 2.22 emette due avvisi,
    "parameter not recognized: NAME=GRAVITA" e "parameter not recognized:
    FIELD". Sono card Abaqus che CalculiX non conosce, e nessuno le leggeva.
    Un avviso benigno tollerato e' un avviso che nasconde quello vero.

    `*NODE FILE` e `*EL FILE` sono keyword Abaqus legacy, valide, e sono quelle
    che CalculiX vuole per l'uscita ascii: il cambio non perde la validita' del
    lato Abaqus. Il nome del passo scende a commento.
    """
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets={"BASE": np.array([0])}, material=MATERIALE, step_name="GRAVITA",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*OUTPUT" not in testo
    assert "*NODE OUTPUT" not in testo
    assert "*ELEMENT OUTPUT" not in testo
    assert "*STEP, NAME=" not in testo
    assert "** NOME PASSO: GRAVITA" in testo
    assert "*NODE FILE" in testo
    assert "*EL FILE" in testo


def test_i_tre_casi_statici_e_la_modale_diventano_quattro_passi():
    """Un deck, quattro passi, un'esecuzione.

    Misurato il 21/08/2026: `ccx` accetta i quattro in fila e chiude con
    "Job finished", zero avvisi e zero errori.
    """
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))
    analisi = config.AnalysisConfig(
        material=MATERIALE,
        spinta=config.SpintaOrizzontale(coefficiente=0.1, asse="y"),
        carico_sommita=config.CaricoSommita(risultante=1000.0, nset="TOP"),
        modale=config.Modale(modi=6),
    )
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets={"BASE": np.array([0]), "TOP": np.array([1, 2])},
        material=MATERIALE, analysis=analisi,
    )

    testo = percorso.read_text(encoding="ascii")
    assert testo.count("*STEP") == 4
    assert testo.count("*END STEP") == 4
    assert "*FREQUENCY" in testo and "\n6\n" in testo
    assert "*CLOAD" in testo
    # la spinta e' una seconda GRAV nello stesso passo, non un passo a se':
    # senza il peso proprio accanto, la spinta descriverebbe una struttura che
    # non pesa
    assert testo.count("GRAV") == 4  # gravita in 3 passi statici + spinta
    # ogni passo statico stampa le reazioni: e' il controllo di conservazione
    assert testo.count("*NODE PRINT, NSET=BASE") == 3
    assert testo.count("RF") >= 3


def test_le_forme_modali_non_chiedono_tensioni():
    """Da un passo *FREQUENCY non escono MPa.

    Le forme sono normalizzate sulla massa, e una von Mises calcolata su una
    forma da' numeri plausibili e privi di significato: fino a 88,5 MPa,
    misurati il 21/08/2026. Il deck non le chiede nemmeno.
    """
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))
    analisi = config.AnalysisConfig(material=MATERIALE, modale=config.Modale(modi=4))
    percorso = tmp_path / "deck.inp"

    abaqus.write_inp(
        percorso, nodi, elementi,
        node_sets={"BASE": np.array([0])}, material=MATERIALE, analysis=analisi,
    )

    passo_modale = percorso.read_text(encoding="ascii").split("** NOME PASSO: MODALE")[1]
    assert "*EL FILE" not in passo_modale
    assert "*NODE FILE" in passo_modale
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_abaqus.py -k "card_che_calculix or quattro_passi or forme_modali" -v`
Expected: FAIL — il primo su `"*OUTPUT" not in testo`, gli altri su `TypeError: unexpected keyword argument 'analysis'`.

- [ ] **Step 3: riscrivi la coda di `write_inp`**

Sostituisci il blocco che va da `f"*STEP, NAME={step_name}"` (riga 144) fino a `""` (riga 162) con la costruzione dei passi. Il passo statico è una funzione locale, così i tre casi non sono tre copie:

```python
    def passo_statico(nome: str, carichi: list[str]) -> list[str]:
        """Un passo statico completo: nome a commento, carichi, uscite.

        Il nome sta in un commento e non in `*STEP, NAME=` perche' CalculiX
        rifiuta quel parametro e ne emette un avviso; un avviso benigno
        tollerato nasconde quello vero. `*NODE FILE`/`*EL FILE` invece di
        `*OUTPUT, FIELD`: sono keyword Abaqus legacy valide, e sono quelle che
        CalculiX vuole per l'uscita ascii.

        `RF` su `fixed_nset` non e' un'uscita in piu': e' il controllo di
        conservazione, e sta nel deck perche' e' li' che il solutore lo puo'
        dare.
        """
        righe = [f"** NOME PASSO: {nome}", "*STEP", "*STATIC", "*DLOAD"]
        righe += carichi
        if pressure is not None:
            righe += ["*DSLOAD", f"{pressure[0]}, P, {pressure[1]}"]
        for name in print_nsets:
            righe += [f"*NODE PRINT, NSET={name}", "U"]
        righe += [f"*NODE PRINT, NSET={fixed_nset}", "RF"]
        righe += ["*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP"]
        return righe

    peso = f"{elset}, GRAV, {gravity}, 0.0, 0.0, -1.0"
    lines += passo_statico(step_name, [peso])

    if analysis is not None and analysis.spinta is not None:
        # La spinta accompagna il peso proprio nello stesso passo: da sola
        # descriverebbe una struttura che non pesa. La direzione e' un asse
        # orizzontale del modello, che dopo la correzione della terna e'
        # davvero orizzontale.
        versore = {"x": "1.0, 0.0, 0.0", "y": "0.0, 1.0, 0.0"}[analysis.spinta.asse]
        spinta = f"{elset}, GRAV, {gravity * analysis.spinta.coefficiente}, {versore}"
        lines += passo_statico("SPINTA_ORIZZONTALE", [peso, spinta])

    if analysis is not None and analysis.carico_sommita is not None:
        sommita = analysis.carico_sommita
        if sommita.nset not in node_sets:
            raise ValueError(
                f"il carico in sommita nomina l'insieme '{sommita.nset}', che non e' "
                f"fra quelli scritti nel deck ({sorted(node_sets)}): il solutore "
                f"leggerebbe un carico applicato a nulla"
            )
        nodi_carico = node_sets[sommita.nset]
        per_nodo = sommita.risultante / len(nodi_carico)
        righe_cload = ["*CLOAD"] + [f"{int(n) + 1}, 3, {-per_nodo:.9e}" for n in nodi_carico]
        lines += passo_statico("CARICO_TOP", [peso] + righe_cload)

    if analysis is not None and analysis.modale is not None:
        # Nessun `*EL FILE`: le forme sono normalizzate sulla massa e una
        # tensione calcolata su di esse non significa nulla. Non si chiede.
        lines += [
            "** NOME PASSO: MODALE", "*STEP", "*FREQUENCY", str(analysis.modale.modi),
            "*NODE FILE", "U", "*END STEP",
        ]

    lines.append("")
```

Aggiungi `analysis: AnalysisConfig | None = None` alla firma di `write_inp`, come ultimo parametro keyword-only.

- [ ] **Step 4: passa `cfg` da `export_model` a `write_inp`**

In `export_model`, alla chiamata di `write_inp`, aggiungi `analysis=cfg`. Nel dizionario restituito aggiungi:

```python
        "casi_di_carico": [nome for nome in (
            cfg.step_name,
            None if cfg.spinta is None else "SPINTA_ORIZZONTALE",
            None if cfg.carico_sommita is None else "CARICO_TOP",
            None if cfg.modale is None else "MODALE",
        ) if nome is not None],
```

- [ ] **Step 5: esegui i test unitari**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. I test preesistenti che confrontano il testo del deck cadranno sul dialetto nuovo: aggiornali, e nel messaggio di commit dichiara quali card sono cambiate e perché.

- [ ] **Step 6: scrivi il test di fattibilità che esegue davvero il solutore**

In `tests/feasibility/test_calculix.py`:

```python
@pytest.mark.feasibility
def test_il_deck_a_quattro_passi_gira_a_zero_avvisi(tmp_path):
    """Che le card siano giuste lo dice il solutore, non una lettura del testo.

    Un controllo interno partirebbe dalla stessa trascrizione che vorrebbe
    verificare (stesso principio del Ruling M della Fase 4). Misurato il
    21/08/2026 sul deck as-built del telaio: quattro passi, "Job finished",
    zero avvisi e zero errori, sei autovalori con U^T*M*U = 1.
    """
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    ...
    uscita = processo.stdout
    assert "Job finished" in uscita
    assert uscita.upper().count("*WARNING") == 0, uscita
    assert uscita.upper().count("*ERROR") == 0, uscita
```

Il corpo del banco ricalca quello di `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero` (riga 139), che già costruisce mesh, scrive il deck ed esegue `ccx`.

- [ ] **Step 7: esegui la suite di fattibilità**

Run: `uv run pytest tests/feasibility -m feasibility -q`
Expected: i test di `ccx` passano; `wildmeshing` resta saltato. Riporta il conteggio esatto: al momento della stesura era `8 passati, 1 saltato`.

- [ ] **Step 8: applica la mutazione**

Rimetti `*STEP, NAME={step_name}` al posto del commento e riesegui il test di fattibilità: il conteggio degli avvisi deve salire da 0 a 1 e il test cadere. Ripristina.

- [ ] **Step 9: commit**

```bash
git add src/meshrec/core/abaqus.py tests/test_abaqus.py tests/feasibility/test_calculix.py
git commit -m "feat(abaqus): deck a quattro passi, dialetto che CalculiX legge per intero"
```

---

### Task 5: leggere il `.frd` e il `.dat`

**Files:**
- Create: `src/meshrec/core/solve.py`
- Test: `tests/test_solve.py`

**Interfaces:**
- Produces:
  - `solve.leggi_frd(percorso: Path) -> list[Blocco]` dove `Blocco` è una `NamedTuple` con `grandezza: str` (`"DISP"`, `"STRESS"`, `"TOSTRAIN"`), `passo: int`, `modale: bool`, `valore: float` (tempo del passo, oppure frequenza in Hz per i blocchi modali), `nodi: np.ndarray` (interi, 1-based come nel deck), `dati: np.ndarray` di forma `(n, componenti)`.
  - `solve.leggi_reazioni(percorso: Path) -> dict[int, tuple[float, float, float]]`
  - `solve.leggi_frequenze(percorso: Path) -> list[float]`
  - `solve.von_mises(tensioni: np.ndarray) -> np.ndarray`

- [ ] **Step 1: scrivi i test che falliscono**

```python
FRD_DUE_PASSI = """\
    1PSTEP                         1           1           1          
  100CL  101 1.000000000           2                     0    1           1
 -4  DISP        4    1
 -1         1 1.00000E+00 2.00000E+00 3.00000E+00
 -1         2 4.00000E+00 5.00000E+00 6.00000E+00
 -3
    1PSTEP                         2           1           2          
  100CL  102 21.19324067           2                     2    2MODAL      1
 -4  DISP        4    1
 -1         1 7.00000E+00 8.00000E+00 9.00000E+00
 -1         2 1.00000E+01 1.10000E+01 1.20000E+01
 -3
"""


def test_il_passo_si_legge_dal_file_e_non_dalla_posizione(tmp_path):
    """Contare i blocchi in ordine cade appena si aggiunge un passo.

    Il record 100CL porta il numero di passo, e nei blocchi modali porta la
    frequenza al posto del tempo. Sul deck del telaio i blocchi DISP sono nove
    per quattro passi: tre statici piu' sei modi (misurato 21/08/2026).
    """
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_DUE_PASSI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert [b.passo for b in blocchi] == [1, 2]
    assert [b.modale for b in blocchi] == [False, True]
    assert blocchi[1].valore == pytest.approx(21.19324067)


def test_il_marchio_modale_sopravvive_all_incollamento(tmp_path):
    """Nel record modale il passo e il tipo escono incollati: `2MODAL`.

    Un `split()` legge un token solo e l'attribuzione salta in silenzio. La
    lettura e' a colonne fisse.
    """
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_DUE_PASSI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert blocchi[1].passo == 2, "il passo e' stato letto insieme alla parola MODAL"


def test_i_blocchi_modali_portano_forme_e_non_spostamenti(tmp_path):
    """Un blocco modale non e' un caso di carico e non deve poter fingere di esserlo."""
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_DUE_PASSI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert not blocchi[0].modale
    assert blocchi[1].modale


def test_von_mises_di_uno_stato_di_taglio_puro():
    """Taglio puro tau: la von Mises vale tau*sqrt(3), forma chiusa."""
    tensioni = np.array([[0.0, 0.0, 0.0, 5.0, 0.0, 0.0]])

    assert solve.von_mises(tensioni)[0] == pytest.approx(5.0 * math.sqrt(3.0))


def test_von_mises_di_una_trazione_monoassiale():
    """Trazione sigma su un asse solo: la von Mises vale sigma."""
    tensioni = np.array([[7.0, 0.0, 0.0, 0.0, 0.0, 0.0]])

    assert solve.von_mises(tensioni)[0] == pytest.approx(7.0)
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_solve.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.solve'`.

- [ ] **Step 3: scrivi il modulo**

```python
"""Esecuzione di CalculiX e lettura delle sue uscite.

Il modulo esiste separato da `abaqus.py` perche' quello scrive deck e questo
legge risultati: sono due direzioni, e `abaqus.py` e' gia' lungo.

Le uscite di `ccx` hanno tre trappole, tutte misurate il 21/08/2026 sul deck
as-built del telaio:

- il numero di passo sta nel record `100CL` e **si legge**, non si deduce
  contando i blocchi: su quel deck i blocchi DISP sono nove per quattro passi,
  tre statici piu' sei modi, e contare cade appena le uscite cambiano;
- nel record modale il passo e il tipo escono incollati (`4MODAL`), quindi la
  lettura e' a colonne fisse e mai un `split()`;
- le forme modali sono normalizzate sulla massa. Una von Mises calcolata su una
  forma da' numeri plausibili per un calcestruzzo e privi di significato: fino
  a 88,5 MPa, misurati. Il flag `modale` esiste per impedire che escano da qui
  come se fossero millimetri o MPa.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

import numpy as np


class Blocco(NamedTuple):
    """Un blocco di risultati del `.frd`, con il passo a cui appartiene."""

    grandezza: str
    passo: int
    modale: bool
    valore: float
    nodi: np.ndarray
    dati: np.ndarray


# Colonne del record 100CL, contate sul file scritto da ccx 2.22. Sono fisse
# perche' il formato e' a colonne: nel record modale il numero di passo e la
# parola MODAL non hanno spazio in mezzo.
_COL_VALORE = slice(12, 24)
_COL_PASSO = slice(57, 62)
_COL_TIPO = slice(62, 67)


def leggi_frd(percorso: Path) -> list[Blocco]:
    """I blocchi di un `.frd` ascii, ciascuno con il passo che il file dichiara."""
    blocchi: list[Blocco] = []
    passo, valore, modale = 0, 0.0, False
    grandezza: str | None = None
    nodi: list[int] = []
    righe: list[list[float]] = []
    for linea in Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines():
        if linea.startswith("  100CL"):
            valore = float(linea[_COL_VALORE])
            passo = int(linea[_COL_PASSO])
            modale = linea[_COL_TIPO].strip().startswith("MODAL")
            continue
        if linea.startswith(" -4"):
            grandezza = linea.split()[1]
            nodi, righe = [], []
            continue
        if linea.startswith(" -3"):
            if grandezza is not None and righe:
                blocchi.append(Blocco(
                    grandezza=grandezza, passo=passo, modale=modale, valore=valore,
                    nodi=np.array(nodi, dtype=np.int64),
                    dati=np.array(righe, dtype=np.float64),
                ))
            grandezza = None
            continue
        if grandezza is not None and linea.startswith(" -1"):
            nodi.append(int(linea[3:13]))
            componenti = (len(linea) - 13) // 12
            righe.append([float(linea[13 + 12 * i:25 + 12 * i]) for i in range(componenti)])
    return blocchi


def von_mises(tensioni: np.ndarray) -> np.ndarray:
    """Tensione equivalente da sei componenti nell'ordine di CalculiX.

    L'ordine e' SXX, SYY, SZZ, SXY, SYZ, SZX: leggerlo sbagliato non solleva
    nulla e produce un numero plausibile, che e' il modo peggiore di sbagliare.
    """
    s = np.asarray(tensioni, dtype=np.float64)
    normali = 0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
    taglianti = 3.0 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2)
    return np.sqrt(normali + taglianti)
```

`leggi_reazioni` riusa il formato di `tests/feasibility/ccx_utils.py` (righe a quattro campi dopo l'intestazione delle forze); `leggi_frequenze` legge la colonna `CYCLES/TIME` del blocco `MODE NO` del `.dat`. Scrivili con lo stesso stile e con i loro test, sullo stesso schema dei test sopra.

- [ ] **Step 4: esegui i test**

Run: `uv run pytest tests/test_solve.py -q`
Expected: PASS.

- [ ] **Step 5: applica le mutazioni**

Tre, una per trappola:

1. Sostituisci `int(linea[_COL_PASSO])` con un contatore incrementale dei blocchi: `test_il_passo_si_legge_dal_file_e_non_dalla_posizione` deve cadere.
2. Sostituisci la lettura a colonne con `linea.split()[5]`: `test_il_marchio_modale_sopravvive_all_incollamento` deve cadere.
3. Fissa `modale=False`: `test_i_blocchi_modali_portano_forme_e_non_spostamenti` deve cadere.

Ripristina dopo ciascuna e riporta i tre esiti.

- [ ] **Step 6: commit**

```bash
git add src/meshrec/core/solve.py tests/test_solve.py
git commit -m "feat(solve): lettura di frd e dat, col passo letto dal file e le forme marcate"
```

---

### Task 6: lo step 13 nella pipeline

**Files:**
- Modify: `src/meshrec/core/steps.py:23-36` (`STEP_KEYS`), `:41-53` (`STEP_BLOCKS`)
- Modify: `src/meshrec/core/pipeline.py:32-41` (`ARTIFACTS`), `:432-442` (coda di `run`)
- Modify: `src/meshrec/core/solve.py` (esecuzione di `ccx` e scrittura del `.vtu`)
- Modify: `src/meshrec/core/abaqus.py:652-673` (`write_vtu` accetta `point_data`)
- Test: `tests/test_solve.py`, `tests/test_pipeline.py`, `tests/test_steps.py`

**Interfaces:**
- Consumes: `solve.leggi_frd`, `solve.leggi_reazioni`, `solve.leggi_frequenze`, `solve.von_mises` dal Task 5; `config.AnalysisConfig` dal Task 3.
- Produces: `solve.risolvi(out_dir: Path, deck: Path, cfg: AnalysisConfig, nodes: np.ndarray, elements: np.ndarray, element_type: str) -> dict[str, object]`, il valore che finisce in `metrics["13_solve"]`. Scrive `13_solution.vtu`, `13_solution.frd`, `13_solution.dat`, `13_solver.log`.

- [ ] **Step 1: scrivi il test che fallisce**

```python
def test_senza_ccx_lo_step_dichiara_l_assenza_e_non_fallisce(tmp_path, monkeypatch):
    """Un esito negativo documentato non e' un fallimento.

    PRODUCT.md dichiara utenti successivi confermati, che non avranno
    necessariamente CalculiX. Senza solutore non c'e' analisi, e il programma lo
    dice invece di rompersi o di inventare un ripiego.
    """
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))

    esito = solve.risolvi(
        tmp_path, tmp_path / "assente.inp", ANALISI, nodi, elementi, "C3D4"
    )

    assert esito == {"eseguito": False, "solutore": "assente"}
    assert not (tmp_path / "13_solution.vtu").exists()


def test_lo_step_13_e_l_ultimo_e_non_entra_nella_completezza_di_uno_sweep():
    """Stesso principio del Ruling D della Fase 4 su 12_wall.

    Uno sweep varia parametri di elaborazione e confronta geometrie: farlo
    risolvere dodici volte pagherebbe un solutore per ogni candidato senza che
    la selezione di Pareto ne guardi il risultato.
    """
    assert steps.STEP_KEYS[-1] == "13_solve"
    assert "13_solve" not in sweep.REQUIRED_STEPS
    assert "12_wall" not in sweep.REQUIRED_STEPS
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_solve.py::test_senza_ccx_lo_step_dichiara_l_assenza_e_non_fallisce tests/test_steps.py -k step_13 -v`
Expected: FAIL su `AttributeError: module ... has no attribute 'risolvi'` e su `STEP_KEYS[-1] == "12_wall"`.

- [ ] **Step 3: registra lo step**

`steps.py`: aggiungi `"13_solve"` in coda a `STEP_KEYS` e `13: ("tet", "analysis")` a `STEP_BLOCKS`.

`sweep.py:130` non si tocca: `REQUIRED_STEPS` esclude per chiave, e va esteso a escludere anche `"13_solve"`:

```python
REQUIRED_STEPS: tuple[str, ...] = tuple(
    chiave for chiave in STEP_KEYS if chiave not in ("12_wall", "13_solve")
)
```

`pipeline.py`: aggiungi `13: "13_solution.vtu"` ad `ARTIFACTS`, così il viewport può chiedere lo step 13 come ogni altro.

- [ ] **Step 4: `write_vtu` accetta i campi**

```python
def write_vtu(
    path: Path, nodes: np.ndarray, elements: np.ndarray, element_type: str = "C3D4",
    point_data: dict[str, np.ndarray] | None = None,
) -> None:
```

e nel corpo, al posto di `meshio.write_points_cells(...)`:

```python
    meshio.write(
        str(path),
        meshio.Mesh(
            np.asarray(nodes, dtype=np.float64),
            [(celle[element_type], np.asarray(elements, dtype=np.int64))],
            point_data=point_data or {},
        ),
    )
```

`point_data` assente lascia il file identico a prima: i chiamanti già scritti non cambiano comportamento.

- [ ] **Step 5: scrivi `solve.risolvi`**

Esegue `ccx` con `subprocess.run` nella cartella della corsa, con `timeout`, cattura stdout in `13_solver.log`, conta le righe `*WARNING` e `*ERROR`, legge i blocchi, calcola gli scalari per caso di carico, e scrive `13_solution.vtu` con `point_data` per caso (`U_<CASO>`, `VM_<CASO>`) più le forme (`MODO_<n>`). I blocchi con `modale=True` non producono né chiavi `U_` né `VM_`.

- [ ] **Step 6: aggancia lo step a `run`**

In `pipeline.run`, dopo il blocco dello step 12 (riga 442) e prima di `pipeline_completa = True`:

```python
        in_corso = 13
        avvio = time.monotonic()
        # Il solutore legge il deck dello step 11, non una sua copia: se il
        # deck e' quello che l'analisi risolve, allora e' quello che il report
        # descrive e quello di cui il registro porta l'impronta.
        metrics["13_solve"] = solve.risolvi(
            out, out / "wall_model.inp", cfg.analysis, nodes, tets,
            metrics["11_export"]["element_type"],
        )
        registra(13, avvio, ARTIFACTS[13] if metrics["13_solve"]["eseguito"] else None)
```

Aggiorna il commento a `pipeline.py:284-286`, che dichiara quale sia l'ultimo step implementato.

Il report della corsa **non** richiede lavoro: `report._sezione_metriche` scorre `steps.STEP_KEYS` (`report.py:411`), quindi `13_solve` compare da solo appena la chiave esiste. Verificalo aprendo il report invece di darlo per fatto, e se le voci escono illeggibili sistema la resa, non la struttura.

- [ ] **Step 7: esegui la suite**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. `tests/test_sweep.py` esercita `REQUIRED_STEPS` e `tests/test_report.py` esercita `STEP_KEYS`: se cadono, il valore atteso è cambiato per ragione nota e va aggiornato.

- [ ] **Step 8: applica la mutazione**

Togli `"13_solve"` dall'esclusione in `REQUIRED_STEPS`: il secondo test deve cadere. Ripristina.

- [ ] **Step 9: commit**

```bash
git add src/meshrec/core/steps.py src/meshrec/core/sweep.py src/meshrec/core/pipeline.py src/meshrec/core/solve.py src/meshrec/core/abaqus.py tests/
git commit -m "feat(pipeline): step 13, il solutore gira nella corsa e lascia i campi in un vtu proprio"
```

---

### Task 7: i controlli che smentiscono

**Files:**
- Modify: `src/meshrec/core/solve.py`
- Modify: `src/meshrec/core/config.py` (la soglia sul vincolo, con il suo docstring di taratura)
- Test: `tests/test_solve.py`

**Interfaces:**
- Consumes: `solve.risolvi` dal Task 6; `abaqus.constraint_plan_extent` dal Task 2; la tabella dei margini misurata allo Step 7 del Task 2.
- Produces: nel dizionario di `risolvi`, la chiave `"controlli"` con cinque voci — `"reazioni"`, `"vincolo_in_pianta"`, `"autovalori"`, `"avvisi"`, `"picco"` — ciascuna `"passato"` o `"fallito"`, e le grandezze che le motivano nelle voci per caso.

- [ ] **Step 1: scrivi i test che falliscono**

```python
def test_la_somma_delle_reazioni_smentisce_una_densita_sbagliata():
    """Somma delle reazioni contro rho*V*g, come vettore e non come modulo.

    Un modulo giusto con una direzione sbagliata passerebbe: e' esattamente il
    caso di un vincolo che tiene la struttura di sbieco.
    """
    reazioni = {1: (0.0, 0.0, 500.0), 2: (0.0, 0.0, 500.0)}

    esito = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 0.0, 1000.0), tolleranza=0.02)
    assert esito["passato"]

    storta = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 600.0, 800.0), tolleranza=0.02)
    assert not storta["passato"], "il modulo coincide, la direzione no"


def test_un_autovalore_vicino_a_zero_e_un_meccanismo():
    """Una frequenza quasi nulla significa che la struttura si muove libera."""
    assert solve.controlla_autovalori([21.19, 34.34, 43.14])["passato"]
    assert not solve.controlla_autovalori([0.0004, 21.19])["passato"]
    assert not solve.controlla_autovalori([])["passato"]


def test_il_picco_di_tensione_dentro_la_banda_di_vincolo_e_un_artefatto():
    """Il numero piu' citabile e' il piu' facile da fraintendere.

    Misurato il 21/08/2026 sull'as-built col vincolo corretto: sotto peso
    proprio il rapporto max/p99 vale 2,16 e nessuno dei 142 nodi sopra il p99
    cade entro la banda di vincolo — il picco sta a z 2286 mm, non
    sull'incastro. Il controllo non e' che il picco sia basso: e' che si sappia
    dove sta.
    """
    quote = np.array([0.0, 10.0, 2000.0, 2100.0])
    valori = np.array([9.0, 1.0, 1.0, 1.0])

    esito = solve.controlla_picco(valori, quote, banda=100.0)

    assert esito["frazione_in_banda"] == pytest.approx(1.0)
    assert not esito["passato"]
```

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_solve.py -k "reazioni or autovalori or picco" -v`
Expected: FAIL con `AttributeError` sui tre nomi.

- [ ] **Step 3: scrivi i controlli**

Tre funzioni pure in `solve.py`, ciascuna con il proprio docstring che dice cosa coglie e con quale numero misurato. `controlla_reazioni` confronta il **vettore** e non il modulo. `controlla_autovalori` rifiuta l'elenco vuoto e ogni frequenza sotto una soglia relativa alla prima. `controlla_picco` restituisce `max/p99` e la frazione dei nodi sopra il p99 che cade entro la banda.

- [ ] **Step 4: scrivi la soglia sul vincolo, con la sua taratura**

In `config.AnalysisConfig`:

```python
    constraint_extent_min: float = Field(
        # Scrivi qui il numero che HAI misurato allo Step 7 del Task 2, non un
        # valore preso da questo piano: la spec propone 0,5 come punto di
        # partenza, ma la soglia la decide la tabella dei margini.
        default=<il valore misurato allo Step 7 del Task 2>,
        gt=0.0, le=1.0,
        description=(
            "estensione in pianta minima dell'insieme vincolato, come frazione "
            "dell'impronta del pezzo. Sotto questa soglia i risultati restano "
            "scritti ma sono marcati non citabili. Il valore e' misurato: "
            # la tabella dei margini, con i numeri del Task 2 e per ciascuna
            # delle tre geometrie: dove regge, il primo valore che non regge,
            # dove crolla. Nessuna soglia senza la tabella che la giustifica.
        ),
    )
```

- [ ] **Step 5: aggancia i cinque controlli a `risolvi`**

Il verdetto entra in `metrics["13_solve"]["controlli"]`, e ogni caso di carico porta accanto le grandezze che lo motivano. Sotto soglia i risultati **restano scritti**: si marcano, non si nascondono.

- [ ] **Step 6: esegui i test**

Run: `uv run pytest tests/test_solve.py tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 7: applica la mutazione**

In `controlla_reazioni`, confronta i moduli invece dei vettori: il primo test deve cadere sul caso "storta". Ripristina.

- [ ] **Step 8: commit**

```bash
git add src/meshrec/core/solve.py src/meshrec/core/config.py tests/test_solve.py tests/test_config.py
git commit -m "feat(solve): i cinque controlli che smentiscono i risultati, con le soglie misurate"
```

---

### Task 8: il campo arriva al server con la corrispondenza intatta

**Files:**
- Modify: `src/meshrec/app/server.py:52` (`VERSIONE_CONTORNO`), `:116-123` (`_contorno_del_volume`), `:786-817` (endpoint dell'artefatto)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `13_solution.vtu` prodotto dal Task 6.
- Produces: `_contorno_del_volume(percorso) -> tuple[np.ndarray, np.ndarray, np.ndarray]`, dove il terzo elemento sono gli indici dei nodi originali che i vertici del contorno rappresentano. Nuovo endpoint `GET /api/campo/{caso}/{grandezza}` che risponde `Float32` per vertice del contorno, con intestazioni `X-Min`, `X-Max`, `X-P99`, `X-Sopra-P99`.

- [ ] **Step 1: scrivi il test che fallisce**

```python
def test_il_contorno_restituisce_gli_indici_dei_nodi_originali(tmp_path):
    """Senza la corrispondenza, un campo per nodo non sa dove va.

    `np.unique(..., return_inverse)` la calcola gia' dentro `_contorno_del_volume`
    e fino alla Fase 5 la buttava via. Riallinearla a valle, in ogni consumatore,
    sarebbe la forma d'errore che la Fase 5 esiste per non commettere: un indice
    che scivola e nessuna metrica che lo smentisce.
    """
    nodi, tetraedri = synth.box_mesh((100.0, 100.0, 100.0))
    percorso = tmp_path / "volume.vtu"
    abaqus.write_vtu(percorso, nodi, tetraedri)

    vertici, _facce, indici = server._contorno_del_volume(percorso)

    assert len(indici) == len(vertici)
    assert vertici == pytest.approx(nodi[indici])
```

- [ ] **Step 2: eseguilo e verifica che fallisca**

Run: `uv run pytest tests/test_server.py -k contorno_restituisce_gli_indici -v`
Expected: FAIL con `ValueError: not enough values to unpack (expected 3, got 2)`.

- [ ] **Step 3: restituisci ciò che si calcola già**

In `_contorno_del_volume`, l'array che `np.unique(..., return_inverse=True)` produce come primo valore è già la corrispondenza: restituiscilo come terzo elemento, salvalo nella cache, e porta `VERSIONE_CONTORNO` da 1 a 2 così le voci vecchie si sfrattano da sole (il commento a `server.py:45-51` spiega perché la versione entra nel nome).

Aggiorna il chiamante all'endpoint dell'artefatto (riga 797), che oggi spacchetta due valori.

- [ ] **Step 4: scrivi l'endpoint del campo**

Legge `13_solution.vtu` con `meshio`, prende `point_data[f"{grandezza}_{caso}"]`, lo restringe agli `indici`, e risponde con `viewport.campo_per_punto`. Le intestazioni portano minimo, massimo, p99 e quanti nodi lo superano: sono i numeri con cui il browser costruisce la legenda senza ricalcolare nulla.

Un caso modale chiesto come `U` o `VM` risponde **400** con un messaggio che dice perché: una forma normalizzata sulla massa non ha millimetri né MPa.

- [ ] **Step 5: esegui i test**

Run: `uv run pytest tests/test_server.py -q`
Expected: PASS.

- [ ] **Step 6: applica la mutazione**

Restituisci `np.arange(len(vertici))` al posto degli indici veri: il test deve cadere sull'asserzione `vertici == nodi[indici]`. Ripristina.

- [ ] **Step 7: commit**

```bash
git add src/meshrec/app/server.py tests/test_server.py
git commit -m "feat(server): il contorno porta con se' la corrispondenza ai nodi, e serve i campi"
```

---

### Task 9: il campo si vede

**Files:**
- Modify: `src/meshrec/ui/viewport.js` (nuova `mostraMeshPerCampo`, accanto a `mostraMesh:193` e `mostraNuvolaPerMembratura:208`)
- Modify: `src/meshrec/ui/app.js` (scelta del caso e della grandezza, legenda, didascalia)
- Modify: `src/meshrec/ui/stile.css`
- Test: `tests/test_viewport.py`, `tests/test_app_js.py`, `tests/test_stile.py`

**Interfaces:**
- Consumes: l'endpoint del Task 8 e le sue intestazioni.
- Produces: `mostraMeshPerCampo(vertici, facce, valori, { taglio, sopraTaglio })` in `viewport.js`.

- [ ] **Step 1: scrivi i test che falliscono**

`tests/test_app_js.py` non cerca sottostringhe nel sorgente: ritaglia le funzioni vere e le **esegue** in `node` (il docstring del file spiega perché — una guardia resa inerte con `|| true` lasciava la sottostringa al suo posto e il controllo restava verde). Segui quel banco, che porta già `_funzioni(*nomi)` e `_esegui(tmp_path, sorgente)`.

Perché siano eseguibili, le due decisioni numeriche vanno in due funzioni pure di `viewport.js`, fuori da `mostraMeshPerCampo`: `scalaDelCampo(valori)` che torna `{ taglio, sopraTaglio }`, e `fattoreAmplificazione(massimo, diagonale)`. Sono pure apposta: una decisione numerica sepolta dentro una funzione che tocca three.js non si può eseguire in `node`, e finirebbe verificata cercando una sottostringa — che è il modo di sbagliare contro cui il docstring di quel file mette in guardia.

Il banco di oggi legge solo `app.js`: `_modulo()` (riga 46) e `_funzioni(*nomi)` (riga 90) partono da lì. Aggiungi accanto la coppia gemella per l'altro file, che è la stessa lettura su un percorso diverso:

```python
def _modulo_viewport() -> str:
    """Il sorgente di `viewport.js`. Gemella di `_modulo()`, che legge `app.js`.

    Serve da quando le decisioni numeriche del campo di colore vivono li': la
    scala e l'amplificazione sono logica, e la logica di questo progetto si
    prova eseguendola.
    """
    return (Path(meshrec.__file__).parent / "ui" / "viewport.js").read_text(encoding="utf-8")


def _funzioni_viewport(*nomi: str) -> str:
    testo = _modulo_viewport()
    return "\n".join(_sorgente_di(nome, testo) for nome in nomi)
```

Nei due test eseguiti usa `_funzioni_viewport` al posto di `_funzioni`; il terzo legge `_modulo_viewport()` direttamente.

```python
def test_la_scala_del_campo_si_taglia_al_p99_e_non_al_massimo(tmp_path):
    """Un nodo non decide la scala di tutti gli altri.

    Misurato il 21/08/2026 sull'as-built sotto peso proprio: il rapporto fra il
    massimo della von Mises e il suo p99 vale 2,16. Una scala lineare fino al
    massimo schiaccia quattordicimila nodi in fondo perche' uno solo sta in
    cima. Chi supera il taglio prende un colore dichiarato e la legenda lo dice:
    e' un'informazione, non un buco.
    """
    uscita = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
        + _funzioni_viewport("scalaDelCampo") + """
const valori = new Float32Array(1000);
for (let i = 0; i < 1000; i += 1) valori[i] = 1.0;
valori[999] = 50.0;                       // il nodo isolato in cima
const { taglio, sopraTaglio } = scalaDelCampo(valori);
assert.ok(taglio < 2.0, `il taglio ha seguito il massimo: ${taglio}`);
assert.equal(sopraTaglio, 10);            // l'1% di mille
console.log("ok");
""")
    assert uscita.strip() == "ok"


def test_il_fattore_di_amplificazione_viene_dal_dato_e_non_da_un_gusto(tmp_path):
    """0,0367 mm su un telaio di 2,5 m non si vede a 1:1.

    Qualunque amplificazione fa sembrare vera una deformazione inventata, quindi
    il fattore non si sceglie perche' "viene bene": e' quello per cui lo
    spostamento massimo vale il 2% della diagonale, e si scrive sempre accanto
    alla vista insieme allo spostamento vero in millimetri.
    """
    uscita = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
        + _funzioni_viewport("fattoreAmplificazione") + """
const fattore = fattoreAmplificazione(0.0367, 4000.0);
assert.ok(Math.abs(fattore * 0.0367 - 0.02 * 4000.0) < 1e-6, `${fattore}`);
console.log("ok");
""")
    assert uscita.strip() == "ok"


def test_la_didascalia_di_una_forma_modale_non_porta_millimetri():
    """Da un passo *FREQUENCY non escono ne' mm ne' MPa.

    Nel viewport e' piu' facile cadere che altrove, perche' la vista di una
    forma modale e' identica a quella di un caso di carico vero.
    """
    sorgente = _modulo_viewport()
    didascalia = _sorgente_di("didascaliaDelCampo", sorgente)
    assert "ampiezza arbitraria" in didascalia
    assert "modale" in didascalia, "la didascalia non distingue una forma da un caso"
```

I tre comportamenti che questi test fissano:

1. la scala si taglia al p99 e chi lo supera prende un colore dichiarato;
2. il fattore di amplificazione si **deriva dal dato** e compare **sempre** nella didascalia, insieme allo spostamento vero in millimetri;
3. una forma modale porta l'etichetta «forma, ampiezza arbitraria» e la frequenza, e **mai** un numero in mm o in MPa.

- [ ] **Step 2: eseguili e verifica che falliscano**

Run: `uv run pytest tests/test_app_js.py tests/test_viewport.py -q`
Expected: FAIL.

- [ ] **Step 3: scrivi `mostraMeshPerCampo`**

È `mostraMesh` più il blocco di colori per vertice che `mostraNuvolaPerMembratura` ha già, con la scala tagliata al p99:

```javascript
    // Il campo per nodo sopra la superficie di contorno. La scala si taglia al
    // p99 e non al massimo: su un campo di tensione il rapporto fra i due vale
    // 2,16 (misurato sull'as-built sotto peso proprio), e una scala fino al
    // massimo schiaccerebbe quattordicimila nodi in fondo perche' uno solo sta
    // in cima. Chi supera il taglio prende un colore dichiarato, e la legenda
    // dice dov'e' il taglio e quanti nodi sono sopra: e' un'informazione, non
    // un buco.
    mostraMeshPerCampo(vertici, facce, valori, { taglio, sopraTaglio }) {
      ...
    },
```

- [ ] **Step 4: esegui i test**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 5: verifica nel browser vero**

Avvia `uv run meshrec serve <config>` su una corsa che ha lo step 13, apri il viewport, e guarda: il campo si colora, la legenda porta il taglio, la didascalia porta il fattore di amplificazione e lo spostamento in millimetri, la forma modale porta la frequenza e nessun millimetro. Un test non vede una legenda illeggibile a distanza, e l'interfaccia viene proiettata in sede di discussione.

- [ ] **Step 6: applica la mutazione**

Metti la scala fino al massimo invece che al p99: il test corrispondente deve cadere. Ripristina.

- [ ] **Step 7: commit**

```bash
git add src/meshrec/ui/ tests/test_app_js.py tests/test_viewport.py tests/test_stile.py
git commit -m "feat(ui): spostamenti e tensioni sul modello, con la scala e l'amplificazione dichiarate"
```

---

### Task 10: dove va il volume mancante

**Files:**
- Create: `meshrec/docs/fase-5-analisi.md` se il Task 11 non l'ha ancora creato; altrimenti Modify, aggiungendo la sezione sul deficit
- Nessun file di `src/` cambia, a meno che la misura non serva anche al report: in quel caso va in `solve.py` e porta il suo test in `tests/test_solve.py`. Se resta una misura una tantum, è uno script del task e non entra nel repository.

**Interfaces:**
- Consumes: `runs/lab_telaio_v2/metrics.json` rigenerato al Task 11, e la tavola `MURO 1` riportata in `docs/fase-4-materiale.md`.

- [ ] **Step 1: misura il deficit**

Volume del modello 217.728.361 mm³ contro 477.700.000 mm³ nominali: **45,6%**, misurato. Il deficit è 259.971.639 mm³. Due cause candidate, nessuna delle due misurata:

1. il ritaglio parte sopra il pavimento (`crop_min[2] = -498`, pavimento misurato a −498,5) e la parte interrata delle zapatas non c'è. Il § 8 di `docs/fase-4-prior-telaio.md` lo dichiara;
2. assottigliamento della ricostruzione di Poisson.

- [ ] **Step 2: calcola la parte attribuibile al ritaglio**

Dalla tavola, ciascuna membratura è un prisma di sezione e lunghezza note. Calcola il volume nominale della porzione **sopra** il piano di taglio e confrontalo con il nominale totale: la differenza è la parte attribuibile al ritaglio, e si calcola senza toccare il solido ricostruito.

- [ ] **Step 3: attribuisci il resto, o dichiaralo non attribuito**

Il residuo fra il deficit misurato e la parte del ritaglio è l'assottigliamento. Se la lunghezza di una membratura non è nella tavola, **quella parte resta non attribuita**: si scrive quanto si sa. Non si stima.

- [ ] **Step 4: verifica con lo spessore**

Lo spessore mediano misurato da `wall.regioni` sul pezzo vero è 192,03 mm (`runs/lab_telaio_v2/12_wall.json`), contro sezioni nominali da 172 a 250 mm. È dentro l'intervallo, quindi l'assottigliamento **non** è uniforme sullo spessore: dillo, perché restringe le ipotesi per chi riprende.

- [ ] **Step 5: scrivi la sezione**

Con i numeri misurati, la ripartizione fra le due cause dove è calcolabile, e la dichiarazione esplicita di ciò che resta non attribuito. La conseguenza da scrivere: sotto peso proprio le tensioni scalano con la massa, quindi quelle di questo modello stanno a quelle del telaio vero come il rapporto misurato.

- [ ] **Step 6: commit**

```bash
git add docs/fase-5-analisi.md
git commit -m "docs(fase-5): dove va il volume che manca, e quanto ne resta non attribuito"
```

---

### Task 11: la corsa vera e il documento di esiti

**Files:**
- Create: `meshrec/docs/fase-5-analisi.md`
- Modify: `meshrec/lab_telaio.yaml` (i casi di carico dichiarati dall'operatore)

**Interfaces:**
- Consumes: tutti i task precedenti.

- [ ] **Step 1: chiedi all'operatore i tre valori che deve dichiarare**

Coefficiente della spinta orizzontale e suo asse, risultante del carico in sommità, numero di modi. Non hanno predefiniti e nessun dato li suggerisce. **Non inventarli.** I 10 kN usati durante la stesura della spec erano un valore di sonda per far girare il deck e non devono comparire da nessuna parte.

- [ ] **Step 2: rigenera la corsa madre in questo albero**

`runs/lab_telaio_v2/` esiste solo in `.claude/worktrees/fase-4-materiale/` e `runs/` è in `.gitignore`. Misurare da lì sarebbe la variante «cartella sbagliata» del difetto che questa fase esiste per non ripetere.

Run: `uv run meshrec run lab_telaio.yaml`
Attesa dichiarata alla chiusura della Fase 4: circa 85 s per dodici step, più lo step 13.

- [ ] **Step 3: confronta con la Fase 4 e spiega ogni scostamento**

Dopo la correzione del Task 1 la terna cambia, quindi cambiano `extent`, i sei set di nodi, `set_tolerance` e il deck. Le grandezze che **non** devono cambiare: numero di nodi e tetraedri, volume, errore geometrico. Se una di queste si muove, fermati: la correzione ha toccato qualcosa che non doveva.

Valori della Fase 4, da `runs/lab_telaio_v2/metrics.json`: 14.103 nodi, 51.913 tetraedri, 0 invertiti, volume 217.728.361 mm³, errore mesh→nuvola 27,54 mm RMS e 135,69 di massimo su 10.968 campioni.

- [ ] **Step 4: leggi i cinque controlli**

Se uno fallisce, il documento lo scrive e i risultati restano marcati non citabili. Un controllo fallito è un esito, non un ostacolo da aggirare.

- [ ] **Step 5: esegui le due suite**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Run: `uv run pytest tests/feasibility -m feasibility -q`
Riporta i conteggi esatti che ottieni. Alla stesura di questo piano erano 555 passati e 8 passati / 1 saltato.

- [ ] **Step 6: scrivi `docs/fase-5-analisi.md`**

Struttura: che cosa gira e che cosa no; il difetto trovato e la sua correzione, con il prima e il dopo misurati; i risultati per caso di carico; i cinque controlli e i loro esiti; gli otto punti del § 7 della spec, che sono ciò che i risultati **non** hanno il diritto di affermare; i limiti misurati; le ipotesi non verificate elencate come tali.

Ogni numero misurato da chi scrive, adesso, su questa corsa. Nessun numero copiato da questo piano o dalla spec senza rimisurarlo: i numeri qui dentro sono del 21/08/2026 e di un codice che i task precedenti hanno cambiato.

- [ ] **Step 7: commit e PR**

```bash
git add meshrec/docs/fase-5-analisi.md meshrec/lab_telaio.yaml
git commit -m "docs(fase-5): l'analisi strutturale dell'as-built, coi controlli e i limiti"
gh pr create --base main --title "Fase 5 — l'analisi strutturale" --body "..."
```

---

## Note per chi esegue

- **Ordine.** I Task 1 e 2 vengono per primi: senza di essi ogni risultato strutturale è falso di due ordini di grandezza, e misurarlo sarebbe fabbricare un esito. Il Task 3 precede il 4 perché il deck legge le classi di configurazione. Il 5 precede il 6. Gli 8 e 9 possono girare in parallelo ai 6 e 7 solo dopo che il Task 6 ha fissato i nomi delle chiavi in `point_data`.
- **Revisione fra un task e l'altro**, con `security-reviewer`, `code-reviewer` e `test-writer` dispacciati **in parallelo** e non in sequenza.
- **La regola sopra tutte:** ogni numero o l'hai misurato tu, adesso, sulla cosa di cui stai parlando, oppure non lo scrivi. Verifica eseguendo, non leggendo. La Fase 4 l'ha pagata undici volte; l'apertura di questa fase ne ha trovata una dodicesima in un docstring e una tredicesima in una memoria di progetto.
