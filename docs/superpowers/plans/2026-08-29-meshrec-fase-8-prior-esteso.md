# Il prior estende ciò che misura — Piano d'attuazione

> **Per chi esegue:** SOTTO-SKILL RICHIESTA: usa `superpowers:subagent-driven-development` (consigliata) oppure `superpowers:executing-plans` per attuare questo piano un compito alla volta. I passi usano caselle (`- [ ]`) per il tracciamento.

**Obiettivo:** far uscire da `wall.misura` le venti sezioni di fetta e la base del piano di sezione che già calcola, aggiungere l'adiacenza fra membrature come misura del prior, e scriverle tutte in `12_wall.json`.

**Architettura:** nessuna misura nuova tranne una. `wall.misura` calcola già le sezioni di fetta in una variabile locale e le butta: i compiti 1 e 2 le restituiscono. La scoperta delle coppie che si incontrano vive oggi dentro `hexa.taglia_giunzioni`: il compito 4 la estrae in `wall`, dove `hexa` continua a chiamarla. Il compito 5 aggiunge la sola misura nuova, il nodo di giunzione per proiezione e la sua distanza dall'asse misurato.

**Stack:** Python 3.12, numpy, pydantic, pytest. Nessuna dipendenza nuova.

**Spec:** `docs/superpowers/specs/2026-08-29-meshrec-fase-8-prior-esteso-design.md`

## Vincoli globali

- Unità: **mm, N, MPa, tonnellata, secondo**. Non introdurre conversioni.
- Lingua di codice, commenti e messaggi: **italiano**. Gli identificatori tecnici restano ASCII e invariati.
- **Non toccare `PipelineConfig`.** `Membratura` è un dataclass di lavoro, non un blocco di configurazione: questo piano non deve spostare l'impronta delle ventidue righe dei registri di sweep.
- **`_FETTE_LUNGO_ASSE` resta una costante privata**, non diventa un parametro. La sua docstring dice perché.
- I campi nuovi di `Membratura` devono avere un **predefinito**: `pipeline._ricostruisci_membrature` costruisce l'oggetto per parola chiave e non deve rompersi. In un dataclass i campi con predefinito vanno **dopo** quelli senza: `esiti` è già l'ultimo e ha già un predefinito, quindi i nuovi vanno dopo di lui.
- **Un prior vecchio non deve rompersi né essere completato d'ufficio.** Assente vuol dire assente: mai zero, mai una stima.
- Voce del progetto: registro asciutto. Si afferma ciò che è verificato, si dichiara ciò che non lo è.

### Come eseguire i test

Il comando canonico è `uv run pytest` da dentro `meshrec/`.

**Nota d'ambiente al 29/08/2026:** su questa macchina `meshrec/.venv` è incompleta — contiene `Scripts/`, `pyvenv.cfg` e `share/`, e **manca `Lib/site-packages`** — quindi `uv run` fallisce. Prima di cominciare, esegui `uv sync` dentro `meshrec/` e verifica che `uv run pytest --collect-only -q` raccolga. Se non si ripara, esiste una venv Linux funzionante costruita da un agente in `/home/mario/vtest`, usabile con:

```bash
cd meshrec && PYTHONPATH="$PWD/src" LD_LIBRARY_PATH=/home/mario/vtest/extralib \
  /home/mario/vtest/bin/python -m pytest tests/test_wall.py -q
```

Con quella venv la suite intera dà **26 rossi ambientali** (`libGLU.so.1` mancante per gmsh, più due di `pymeshlab`), tutti in `test_hexa`, `test_pipeline`, `test_gmsh_backend`, `test_cli`, `test_surface`. Nessuno tocca i file di questo piano: se il tuo conteggio ne mostra di più, li hai introdotti tu.

---

### Compito 1: `wall.misura` restituisce le sezioni di fetta e le loro quote

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — il dataclass `Membratura` (da riga 419) e la funzione `misura` (da riga 469)
- Test: `meshrec/tests/test_wall.py`

**Interfacce:**
- Consuma: niente da compiti precedenti.
- Produce: `Membratura.sezioni_fette: np.ndarray` di forma `(M, 2)`, con `M <= 20`, le due estensioni trasversali di ciascuna fetta che aveva almeno quattro punti; `Membratura.quote_fette: np.ndarray` di forma `(M,)`, la coordinata lungo l'asse del centro di ciascuna fetta misurata da `origine`. Le due hanno **sempre la stessa lunghezza** e sono nello stesso ordine. Predefiniti: array vuoti di forma `(0, 2)` e `(0,)`.

- [ ] **Passo 1: scrivi il test che fallisce**

In `meshrec/tests/test_wall.py`. Cerca prima nel file un aiutante che fabbrichi una regione prismatica di punti e riusalo invece di scriverne un secondo.

```python
def test_la_membratura_restituisce_una_sezione_per_fetta_con_la_propria_quota():
    """Le venti fette che `misura` già calcola per la dispersione escono dalla
    funzione: sono le stazioni su cui il modello a telaio poggia.

    Su un prisma a sezione costante le sezioni di fetta sono tutte uguali fra
    loro e uguali alla sezione complessiva; il test verifica la forma e
    l'accordo, non un valore fabbricato.
    """
    punti, direzioni, cfg = _regione_prismatica(lunghezza=2000.0, sezione=(300.0, 200.0))

    membratura = wall.misura(punti, direzioni, cfg)

    assert membratura.sezioni_fette.ndim == 2
    assert membratura.sezioni_fette.shape[1] == 2
    assert len(membratura.quote_fette) == len(membratura.sezioni_fette)
    assert len(membratura.sezioni_fette) > 1, "una sola fetta non è una stazione"
    # le quote crescono lungo l'asse e stanno dentro la lunghezza misurata
    assert np.all(np.diff(membratura.quote_fette) > 0.0)
    assert membratura.quote_fette.min() >= 0.0
    assert membratura.quote_fette.max() <= membratura.lunghezza
    # su un prisma costante ogni fetta vede la sezione del pezzo
    assert np.allclose(
        membratura.sezioni_fette, np.asarray(membratura.sezione), rtol=0.05
    )
```

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py::test_la_membratura_restituisce_una_sezione_per_fetta_con_la_propria_quota -v`
Atteso: FALLITO con `AttributeError: 'Membratura' object has no attribute 'sezioni_fette'`.

- [ ] **Passo 3: aggiungi i due campi al dataclass**

In `wall.py`, **dopo** il campo `esiti`, che è l'ultimo e ha già un predefinito:

```python
    sezioni_fette: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    """Le due estensioni trasversali, misurate fetta per fetta lungo l'asse.

    Sono le stazioni su cui il modello a telaio poggia: una fetta, un elemento.
    `misura` le calcolava gia' per la dispersione della sezione e le teneva in
    una variabile locale; qui escono, perche' `sezione` e `sezione_dispersione`
    sono sintesi e il telaio ha bisogno del dato che le produce.

    Le fette con meno di quattro punti non compaiono: una sezione misurata su
    tre punti misurerebbe il campionamento e non il pezzo. Il predefinito
    vuoto non e' «nessuna fetta»: e' «questa Membratura viene da un prior
    scritto prima che la misura esistesse».
    """
    quote_fette: np.ndarray = field(default_factory=lambda: np.zeros(0))
    """Coordinata lungo l'asse del centro di ciascuna fetta, misurata da `origine`.

    Stessa lunghezza e stesso ordine di `sezioni_fette`. Serve perche' una
    sezione senza la propria stazione non colloca nulla, e perche' una fetta
    saltata deve restare visibile come una quota assente invece di far
    scivolare di una posizione tutte le sezioni che la seguono.
    """
```

- [ ] **Passo 4: raccogli le quote nel ciclo delle fette e restituisci**

In `misura`, il ciclo che riempie `per_fetta` scarta le fette povere con `continue`. Raccogli la quota **nello stesso ramo** in cui la sezione viene accettata, così le due liste non possono divergere:

```python
    per_fetta = []
    quote_per_fetta = []
    riempimenti = []
    for indice in range(_FETTE_LUNGO_ASSE):
        dentro = fetta == indice
        if dentro.sum() < 4:
            continue
        per_fetta.append((np.ptp(sezione_2d[dentro, 0]), np.ptp(sezione_2d[dentro, 1])))
        # Il centro della fetta lungo l'asse, non la media dei punti che
        # contiene: la stazione e' una posizione geometrica, e su una fetta
        # con densita' sbilanciata la media dei punti la sposterebbe.
        quote_per_fetta.append(float((bordi[indice] + bordi[indice + 1]) / 2.0 - lungo.min()))
```

E nel `return Membratura(...)`, accanto agli altri campi:

```python
        sezioni_fette=np.asarray(per_fetta, dtype=np.float64).reshape(-1, 2),
        quote_fette=np.asarray(quote_per_fetta, dtype=np.float64),
```

`reshape(-1, 2)` e non `np.asarray` da solo: su una lista vuota `np.asarray([])` ha forma `(0,)` e non `(0, 2)`, e il test sulla forma cadrebbe su una regione che non ha prodotto nessuna fetta.

- [ ] **Passo 5: esegui il test e verifica che passi**

Esegui: `uv run pytest tests/test_wall.py -v -k fetta`
Atteso: PASSATO.

- [ ] **Passo 6: esegui i test del modulo per intero**

Esegui: `uv run pytest tests/test_wall.py -q`
Atteso: nessun rosso nuovo. `misura` è chiamata da molti banchi esistenti: se uno si rompe, hai cambiato una grandezza che doveva restare ferma.

- [ ] **Passo 7: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(wall): misura restituisce le sezioni di fetta e le loro quote"
```

---

### Compito 2: `wall.misura` restituisce la base del piano di sezione

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — `Membratura` e `misura`
- Test: `meshrec/tests/test_wall.py`

**Interfacce:**
- Consuma: `Membratura` con i campi del compito 1.
- Produce: `Membratura.base_sezione: np.ndarray` di forma `(2, 3)`, la riga 0 è `e1` e la riga 1 è `e2`. Entrambe sono versori, ortogonali fra loro e ortogonali ad `asse`. Predefinito: array vuoto di forma `(0, 3)`.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_la_base_del_piano_di_sezione_esce_dalla_misura_ed_e_ortonormale():
    """`misura` costruisce gia' e1 ed e2 e le tiene per se'. Senza di loro
    nessuno puo' collocare una barra nel piano della sezione: sono il dato che
    trasforma due estensioni in una geometria.
    """
    punti, direzioni, cfg = _regione_prismatica(lunghezza=2000.0, sezione=(300.0, 200.0))

    membratura = wall.misura(punti, direzioni, cfg)
    base = membratura.base_sezione

    assert base.shape == (2, 3)
    assert np.allclose(np.linalg.norm(base, axis=1), 1.0), "e1 ed e2 devono essere versori"
    assert abs(float(base[0] @ base[1])) < 1e-9, "e1 ed e2 devono essere ortogonali"
    assert np.allclose(base @ membratura.asse, 0.0, atol=1e-9), (
        "il piano di sezione e' ortogonale all'asse"
    )
```

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py::test_la_base_del_piano_di_sezione_esce_dalla_misura_ed_e_ortonormale -v`
Atteso: FALLITO con `AttributeError: 'Membratura' object has no attribute 'base_sezione'`.

- [ ] **Passo 3: aggiungi il campo**

Dopo `quote_fette`:

```python
    base_sezione: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    """Le due direzioni del piano di sezione, e1 sulla riga 0 ed e2 sulla riga 1.

    `misura` le costruisce gia', ancorate alla terna del pezzo e non alla SVD
    della regione, «o le loro sezioni non sono confrontabili»: due membrature
    parallele devono avere lo stesso piano. Escono di qui perche' `sezione` e
    `contorno` sono numeri in quel piano, e senza il piano non collocano nulla.
    """
```

- [ ] **Passo 4: restituiscila**

Nel `return Membratura(...)`, accanto agli altri:

```python
        base_sezione=np.vstack([e1, e2]),
```

`e1` ed `e2` esistono già nella funzione, costruite poco sopra `sezione_2d`. Non ricalcolarle: sarebbe una seconda verità sullo stesso piano.

- [ ] **Passo 5: esegui i test**

Esegui: `uv run pytest tests/test_wall.py -q`
Atteso: PASSATO, nessun rosso nuovo.

- [ ] **Passo 6: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(wall): misura restituisce la base del piano di sezione"
```

---

### Compito 3: il prior scrive le nuove misure in `12_wall.json`

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — la funzione `prior` (da riga 764), dove costruisce il dizionario di ciascuna membratura (da riga 855 circa)
- Test: `meshrec/tests/test_wall.py`

**Interfacce:**
- Consuma: i campi dei compiti 1 e 2.
- Produce: nella voce di ogni membratura di `12_wall.json`, tre chiavi nuove — `sezioni_fette` (lista di coppie), `quote_fette` (lista di numeri), `base_sezione` (lista di due terne). Sono **solo tipi JSON**: il dizionario del prior finisce su disco e nel browser, e un array numpy dentro romperebbe entrambi.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_il_prior_scrive_le_sezioni_di_fetta_e_la_base_in_json():
    """Il prior finisce su disco e nel browser: le misure nuove devono uscire
    come tipi JSON, non come array numpy.
    """
    punti, cfg_segment, cfg, spacing = _scena_a_due_membrature()

    esito = wall.prior(punti, cfg_segment, cfg, spacing)
    voce = esito["membrature"][0]

    assert isinstance(voce["sezioni_fette"], list)
    assert all(isinstance(coppia, list) and len(coppia) == 2 for coppia in voce["sezioni_fette"])
    assert isinstance(voce["quote_fette"], list)
    assert len(voce["quote_fette"]) == len(voce["sezioni_fette"])
    assert isinstance(voce["base_sezione"], list)
    assert len(voce["base_sezione"]) == 2
    assert all(len(riga) == 3 for riga in voce["base_sezione"])
    # la prova che conta: l'intero esito e' serializzabile
    json.dumps(esito)
```

Se `_scena_a_due_membrature` non esiste in `test_wall.py`, cerca l'aiutante che i banchi di `prior` già usano e riusalo; scrivine uno nuovo solo se non c'è.

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py::test_il_prior_scrive_le_sezioni_di_fetta_e_la_base_in_json -v`
Atteso: FALLITO con `KeyError: 'sezioni_fette'`.

- [ ] **Passo 3: aggiungi le tre chiavi**

Nel dizionario per membratura dentro `prior`, accanto a `"sezione"` e `"contorno"`:

```python
                "sezioni_fette": m.sezioni_fette.tolist(),
                "quote_fette": m.quote_fette.tolist(),
                "base_sezione": m.base_sezione.tolist(),
```

- [ ] **Passo 4: esegui il test e verifica che passi**

Esegui: `uv run pytest tests/test_wall.py -q`
Atteso: PASSATO.

- [ ] **Passo 5: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(wall): il prior scrive sezioni di fetta, quote e base di sezione"
```

---

### Compito 4: la scoperta delle coppie esce da `hexa` e va in `wall`

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — nuova funzione
- Modifica: `meshrec/src/meshrec/core/hexa.py` — `taglia_giunzioni` (da riga 538) chiama la funzione estratta invece di decidere i ruoli in proprio
- Test: `meshrec/tests/test_wall.py`, `meshrec/tests/test_hexa.py`

**Interfacce:**
- Consuma: niente dai compiti precedenti.
- Produce: `wall.ruoli_dell_incontro(invaso_candidato: np.ndarray, invaso_maggiore: np.ndarray, indice_candidato: int, indice_maggiore: int) -> tuple[int, int, np.ndarray]`, che rende `(indice_che_cede, indice_che_resta, campionamento_invaso_di_chi_cede)`. Il campionamento restituito è quello di chi cede, così il chiamante non lo ricalcola.

**Perché questa firma e non una che prende i prismi:** `Prisma` è definito in `hexa`, e `wall` non deve importarlo — oggi `hexa` non importa `wall` a livello di modulo e `wall` non importa `hexa` affatto. Estrarre la **decisione del ruolo** invece della geometria tiene le due direzioni pulite e sposta esattamente il pezzo che il prior deve riusare: chi cede e chi resta.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_cede_chi_ha_l_asse_invaso_e_non_chi_ha_l_indice_piu_basso():
    """Ruling AD: cede la membratura che finisce dentro l'altra, come una trave
    appoggiata su un pilastro accorcia il pilastro e non la trave. Il criterio
    e' del dato, non dell'ordine in cui le membrature arrivano.
    """
    invaso = np.array([True, True, False, False])
    libero = np.zeros(4, dtype=bool)

    # il candidato 7 ha l'asse invaso dentro il 3: cede il 7
    cede, resta, campionamento = wall.ruoli_dell_incontro(invaso, libero, 7, 3)
    assert (cede, resta) == (7, 3)
    assert campionamento is invaso

    # rovesciato: e' il 3 ad avere l'asse invaso dentro il 7, quindi cede il 3
    cede, resta, campionamento = wall.ruoli_dell_incontro(libero, invaso, 7, 3)
    assert (cede, resta) == (3, 7)
    assert campionamento is invaso


def test_a_pari_invasione_lo_spareggio_non_dipende_dall_ordine():
    """Entrambi invasi o nessuno invaso: decide l'ordine che il chiamante ha
    gia' stabilito per area, e la funzione non lo ribalta.
    """
    entrambi = np.array([True, False])
    cede, resta, _ = wall.ruoli_dell_incontro(entrambi, entrambi, 7, 3)
    assert (cede, resta) == (7, 3), "a pari invasione cede il candidato, non il maggiore"

    nessuno = np.zeros(2, dtype=bool)
    cede, resta, _ = wall.ruoli_dell_incontro(nessuno, nessuno, 7, 3)
    assert (cede, resta) == (7, 3)
```

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py -v -k ruoli`
Atteso: FALLITO con `AttributeError: module 'meshrec.core.wall' has no attribute 'ruoli_dell_incontro'`.

- [ ] **Passo 3: scrivi la funzione in `wall.py`**

```python
def ruoli_dell_incontro(
    invaso_candidato: np.ndarray,
    invaso_maggiore: np.ndarray,
    indice_candidato: int,
    indice_maggiore: int,
) -> tuple[int, int, np.ndarray]:
    """Chi cede e chi resta, quando due membrature si incontrano (Ruling AD).

    Cede quella il cui asse baricentrico entra nell'altra: ha il significato
    fisico giusto -- cede la membratura che finisce dentro l'altra, come una
    trave appoggiata su un pilastro accorcia il pilastro e non la trave. Il
    criterio precedente, «cede il prisma di sezione minore», sceglieva il ruolo
    sbagliato proprio quando un montante entra nel traverso da sotto.

    Un solo verso invaso decide da solo. Se **entrambi** o **nessuno** dei due
    lo e', la funzione non ribalta l'ordine che il chiamante ha gia' stabilito:
    cede il candidato. Il chiamante ordina per area decrescente, quindi lo
    spareggio resta deterministico e funzione del dato.

    Restituisce anche il campionamento di chi cede, gia' calcolato dal
    chiamante per decidere il ruolo: ricalcolarlo sarebbe pagare due volte la
    stessa misura.
    """
    if invaso_maggiore.any() and not invaso_candidato.any():
        return indice_maggiore, indice_candidato, invaso_maggiore
    return indice_candidato, indice_maggiore, invaso_candidato
```

- [ ] **Passo 4: esegui i test e verifica che passino**

Esegui: `uv run pytest tests/test_wall.py -v -k ruoli`
Atteso: PASSATO, entrambi.

- [ ] **Passo 5: fai chiamare la funzione a `hexa.taglia_giunzioni`**

In `hexa.py`, aggiungi l'importazione in testa al modulo:

```python
from meshrec.core.wall import ruoli_dell_incontro
```

e sostituisci le cinque righe che decidono i ruoli con la chiamata:

```python
            invaso_candidato = _asse_baricentrico_invaso(tagliati[candidato], tagliati[maggiore])
            invaso_maggiore = _asse_baricentrico_invaso(tagliati[maggiore], tagliati[candidato])
            minore, maggiore_effettivo, invaso = ruoli_dell_incontro(
                invaso_candidato, invaso_maggiore, candidato, maggiore
            )
```

Lascia il commento del Ruling AD dov'è: rimanda alla docstring, che ora vive in `wall`.

- [ ] **Passo 6: verifica che `hexa` non sia cambiato di comportamento**

Esegui: `uv run pytest tests/test_hexa.py -q`
Atteso: lo **stesso** conteggio di prima della modifica. Misuralo prima con `git stash`, se non lo hai già.

Su questa macchina `test_hexa.py` porta 12 rossi ambientali per `libGLU.so.1` mancante: se il numero resta 12, l'estrazione non ha cambiato niente. Se sale, l'ha cambiato.

- [ ] **Passo 7: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/src/meshrec/core/hexa.py meshrec/tests/test_wall.py
git commit -m "refactor(wall): la decisione del ruolo all'incontro esce da hexa"
```

---

### Compito 5: il nodo di giunzione e la sua distanza dall'asse misurato

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — nuova funzione
- Test: `meshrec/tests/test_wall.py`

**Interfacce:**
- Consuma: niente dai compiti precedenti.
- Produce: `wall.nodo_di_giunzione(origine_cede, asse_cede, lunghezza_cede, origine_resta, asse_resta) -> tuple[np.ndarray, float]`, che rende il punto del nodo (tre coordinate) e la **distanza di proiezione** in mm — quanto l'estremo di chi cede deve spostarsi per raggiungere l'asse di chi resta.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_il_nodo_e_la_proiezione_sull_asse_di_chi_resta():
    """Su una geometria rilevata gli assi non si intersecano quasi mai: passano
    vicini e si scansano. Il nodo e' la proiezione di chi cede sull'asse di chi
    resta -- il traverso continuo col montante che vi si innesta.
    """
    # traverso lungo x a quota z=3000; montante verticale che gli passa
    # accanto, scansato di 40 mm lungo y
    origine_resta = np.array([0.0, 0.0, 3000.0])
    asse_resta = np.array([1.0, 0.0, 0.0])
    origine_cede = np.array([1000.0, 40.0, 0.0])
    asse_cede = np.array([0.0, 0.0, 1.0])

    nodo, distanza = wall.nodo_di_giunzione(
        origine_cede, asse_cede, 3000.0, origine_resta, asse_resta
    )

    # il nodo sta sull'asse del traverso, quindi a y = 0 e z = 3000
    assert np.allclose(nodo, np.array([1000.0, 0.0, 3000.0]), atol=1e-9)
    # e il montante ha dovuto spostarsi dei 40 mm di cui era scansato
    assert distanza == pytest.approx(40.0, abs=1e-9)


def test_assi_che_si_incontrano_davvero_danno_distanza_nulla():
    """Il caso ideale non e' un caso speciale: la stessa formula lo copre, e la
    distanza dice da sola che non c'e' stato nessuno spostamento.
    """
    nodo, distanza = wall.nodo_di_giunzione(
        np.array([1000.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), 3000.0,
        np.array([0.0, 0.0, 3000.0]), np.array([1.0, 0.0, 0.0]),
    )
    assert np.allclose(nodo, np.array([1000.0, 0.0, 3000.0]), atol=1e-9)
    assert distanza == pytest.approx(0.0, abs=1e-9)
```

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py -v -k nodo`
Atteso: FALLITO con `AttributeError: module 'meshrec.core.wall' has no attribute 'nodo_di_giunzione'`.

- [ ] **Passo 3: scrivi la funzione**

```python
def nodo_di_giunzione(
    origine_cede: np.ndarray,
    asse_cede: np.ndarray,
    lunghezza_cede: float,
    origine_resta: np.ndarray,
    asse_resta: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Il punto in cui due membrature si legano, e quanto e' costato metterlo li'.

    Su una geometria rilevata gli assi di due membrature che si incontrano non
    si intersecano quasi mai: passano vicini e si scansano di qualche
    millimetro. Il nodo e' la **proiezione di chi cede sull'asse di chi resta**
    -- il traverso continuo col montante che vi si innesta, che e' la
    convenzione del calcolo strutturale e coincide col ruolo che
    `ruoli_dell_incontro` ha gia' assegnato.

    La distanza restituita e' **una misura, non un residuo di calcolo**: e' di
    quanto l'estremo di chi cede si e' dovuto spostare, e va mostrata. Uno
    spostamento silenzioso sarebbe una correzione della geometria rilevata
    spacciata per la geometria rilevata, cioe' l'opposto dello scopo del
    programma.

    L'estremo di chi cede e' quello **piu' vicino** all'asse di chi resta: una
    colonna incontra il traverso da un capo solo, e prendere l'altro
    proietterebbe il piede sul tetto.
    """
    versore_cede = np.asarray(asse_cede, dtype=np.float64)
    versore_cede = versore_cede / np.linalg.norm(versore_cede)
    versore_resta = np.asarray(asse_resta, dtype=np.float64)
    versore_resta = versore_resta / np.linalg.norm(versore_resta)
    origine_resta = np.asarray(origine_resta, dtype=np.float64)

    def proietta(punto: np.ndarray) -> np.ndarray:
        scarto = punto - origine_resta
        return origine_resta + versore_resta * float(scarto @ versore_resta)

    estremi = [
        np.asarray(origine_cede, dtype=np.float64),
        np.asarray(origine_cede, dtype=np.float64) + versore_cede * float(lunghezza_cede),
    ]
    distanze = [float(np.linalg.norm(estremo - proietta(estremo))) for estremo in estremi]
    scelto = int(np.argmin(distanze))
    return proietta(estremi[scelto]), distanze[scelto]
```

- [ ] **Passo 4: esegui i test e verifica che passino**

Esegui: `uv run pytest tests/test_wall.py -v -k nodo`
Atteso: PASSATO, entrambi.

- [ ] **Passo 5: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(wall): il nodo di giunzione per proiezione, con la distanza misurata"
```

---

### Compito 6: il prior calcola e scrive l'adiacenza

**File:**
- Modifica: `meshrec/src/meshrec/core/wall.py` — la funzione `prior`
- Test: `meshrec/tests/test_wall.py`

**Interfacce:**
- Consuma: `ruoli_dell_incontro` e `nodo_di_giunzione` dei compiti 4 e 5.
- Produce: in `12_wall.json`, la chiave di primo livello `giunzioni`: una lista di dizionari con `cede` (indice), `resta` (indice), `nodo` (tre coordinate) e `distanza_proiezione` (mm). Gli indici sono posizioni dentro la lista `membrature` dello stesso file.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_il_prior_scrive_le_giunzioni_col_nodo_e_la_distanza():
    """L'adiacenza e' una misura del prior come l'asse e la sezione: chi
    costruisce un telaio la legge da `12_wall.json` invece di ricalcolarla.
    """
    punti, cfg_segment, cfg, spacing = _scena_a_due_membrature()

    esito = wall.prior(punti, cfg_segment, cfg, spacing)

    assert "giunzioni" in esito
    assert len(esito["giunzioni"]) >= 1, "due membrature che si toccano fanno una giunzione"
    incontro = esito["giunzioni"][0]
    assert set(incontro) >= {"cede", "resta", "nodo", "distanza_proiezione"}
    assert incontro["cede"] != incontro["resta"]
    assert 0 <= incontro["cede"] < len(esito["membrature"])
    assert 0 <= incontro["resta"] < len(esito["membrature"])
    assert len(incontro["nodo"]) == 3
    assert incontro["distanza_proiezione"] >= 0.0
    json.dumps(esito)


def test_membrature_che_non_si_toccano_non_fanno_giunzioni():
    """Una giunzione inventata fra due pezzi lontani sarebbe un telaio che sta
    in piedi su un legame che non esiste.
    """
    punti, cfg_segment, cfg, spacing = _scena_a_due_membrature_lontane()

    esito = wall.prior(punti, cfg_segment, cfg, spacing)

    assert esito["giunzioni"] == []
```

- [ ] **Passo 2: eseguilo e verifica che fallisca**

Esegui: `uv run pytest tests/test_wall.py -v -k giunzion`
Atteso: FALLITO con `KeyError: 'giunzioni'` sul primo test.

- [ ] **Passo 3: scrivi la funzione che compone l'adiacenza**

In `wall.py`, accanto a `prior`. Il rilevamento dell'invasione vive in `hexa` e opera su `Prisma`: qui si usa il criterio geometrico direttamente sulle membrature, campionando la baricentrica di una dentro il prisma dell'altra.

```python
_CAMPIONI_GIUNZIONE = 200
"""Campioni sulla baricentrica di una membratura, per vedere se entra nell'altra.

Stesso ordine di grandezza dei campioni che `hexa.taglia_giunzioni` usa per la
stessa domanda: qui non serve la precisione del taglio -- non si taglia niente
-- ma la risoluzione deve bastare a non mancare un'invasione corta.
"""


def _baricentrica_invasa(interna, esterna) -> np.ndarray:
    """Campionamento booleano della baricentrica di `interna` dentro `esterna`.

    Il prisma di `esterna` e' definito dalla propria sezione misurata attorno
    al proprio asse: un punto e' dentro se la sua proiezione cade nella
    lunghezza e le due componenti trasversali stanno dentro le semiestensioni.
    E' il prisma circoscritto, non il contorno: la stessa approssimazione che
    `sezione` gia' e', e sulla quale `riempimento_sezione` dichiara lo scarto.
    """
    asse = esterna.asse / np.linalg.norm(esterna.asse)
    passo = np.linspace(0.0, interna.lunghezza, _CAMPIONI_GIUNZIONE)
    versore = interna.asse / np.linalg.norm(interna.asse)
    punti = interna.origine + np.outer(passo, versore)
    scarto = punti - esterna.origine
    lungo = scarto @ asse
    base = esterna.base_sezione
    if base.shape != (2, 3):
        # Un prior vecchio non porta la base: senza il piano non si sa dove
        # stiano le due estensioni, e una giunzione dedotta a caso sarebbe
        # peggio di una giunzione assente.
        return np.zeros(len(punti), dtype=bool)
    trasversale = np.abs(scarto @ base.T)
    semi = np.asarray(esterna.sezione, dtype=np.float64) / 2.0
    return (
        (lungo >= 0.0)
        & (lungo <= esterna.lunghezza)
        & (trasversale[:, 0] <= semi[0])
        & (trasversale[:, 1] <= semi[1])
    )


def giunzioni(membrature: list[Membratura]) -> list[dict[str, object]]:
    """Gli incontri fra membrature, con il nodo e quanto e' costato collocarlo.

    L'adiacenza e' una **misura della geometria**, allo stesso titolo dell'asse
    e della sezione: `wall.prior` la calcola e la scrive, e chi costruisce un
    telaio la legge invece di dedurla. `hexa.taglia_giunzioni` continua a fare
    il proprio mestiere, che e' il taglio, e condivide con questa funzione la
    sola decisione del ruolo (`ruoli_dell_incontro`).

    L'ordine di esame e' per area di sezione decrescente, poi per lunghezza,
    poi per indice: e' lo stesso spareggio deterministico gia' in uso, e serve
    a non lasciare la scelta all'ordine in cui le membrature arrivano.
    """
    ordine = sorted(
        range(len(membrature)),
        key=lambda i: (
            -(membrature[i].sezione[0] * membrature[i].sezione[1]),
            -membrature[i].lunghezza,
            i,
        ),
    )
    incontri: list[dict[str, object]] = []
    for posizione, maggiore in enumerate(ordine):
        for candidato in ordine[posizione + 1 :]:
            invaso_candidato = _baricentrica_invasa(membrature[candidato], membrature[maggiore])
            invaso_maggiore = _baricentrica_invasa(membrature[maggiore], membrature[candidato])
            if not invaso_candidato.any() and not invaso_maggiore.any():
                continue
            cede, resta, _ = ruoli_dell_incontro(
                invaso_candidato, invaso_maggiore, candidato, maggiore
            )
            nodo, distanza = nodo_di_giunzione(
                membrature[cede].origine,
                membrature[cede].asse,
                membrature[cede].lunghezza,
                membrature[resta].origine,
                membrature[resta].asse,
            )
            incontri.append(
                {
                    "cede": int(cede),
                    "resta": int(resta),
                    "nodo": nodo.tolist(),
                    "distanza_proiezione": float(distanza),
                }
            )
    return incontri
```

- [ ] **Passo 4: chiamala da `prior` e scrivi la chiave**

In `prior`, dopo che `accettate` è completa e prima del `return`, aggiungi la chiave al dizionario restituito:

```python
        "giunzioni": giunzioni(accettate),
```

- [ ] **Passo 5: esegui i test e verifica che passino**

Esegui: `uv run pytest tests/test_wall.py -v -k giunzion`
Atteso: PASSATO, entrambi.

- [ ] **Passo 6: esegui i moduli che leggono il prior**

Esegui: `uv run pytest tests/test_wall.py tests/test_server.py tests/test_pipeline.py -q`
Atteso: nessun rosso nuovo. `test_pipeline.py` porta 9 rossi ambientali su questa macchina: se restano 9, va bene.

- [ ] **Passo 7: commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(wall): il prior misura e scrive l'adiacenza fra membrature"
```

---

### Compito 7: un prior vecchio si rilegge senza rompersi e senza essere completato

**File:**
- Modifica: `meshrec/src/meshrec/core/pipeline.py` — `_ricostruisci_membrature` (da riga 152)
- Test: `meshrec/tests/test_pipeline.py`

**Interfacce:**
- Consuma: le chiavi dei compiti 3 e 6.
- Produce: niente di nuovo. Garantisce che `_ricostruisci_membrature` accetti un dizionario privo delle chiavi nuove.

- [ ] **Passo 1: scrivi il test che fallisce**

```python
def test_un_prior_scritto_prima_delle_nuove_misure_si_rilegge_ancora():
    """`runs/muro/` e `runs/lab_crop/` sono corse di riferimento in sola
    lettura, e i loro 12_wall.json non portano le chiavi nuove. Rileggerle non
    deve rompersi -- e non deve nemmeno riempirle: assente vuol dire assente,
    non zero e non una stima.
    """
    voce_vecchia = {
        "asse": [0.0, 0.0, 1.0],
        "origine": [0.0, 0.0, 0.0],
        "lunghezza": 3000.0,
        "sezione": [300.0, 300.0],
        "sezione_dispersione": [0.01, 0.01],
        "contorno": [[-150.0, -150.0], [150.0, -150.0], [150.0, 150.0], [-150.0, 150.0]],
        "fuori_piombo_deg": 0.0,
        "asse_ideale": [0.0, 0.0, 1.0],
        "scarto_asse_deg": 0.0,
        "volume": 270_000_000.0,
        "riempimento": {"valore": 0.98, "stato": "pieno", "densita_dispersione": 0.1},
    }

    membrature = pipeline._ricostruisci_membrature({"membrature": [voce_vecchia]})

    assert len(membrature) == 1
    assert len(membrature[0].sezioni_fette) == 0, "non inventare fette che nessuno ha misurato"
    assert len(membrature[0].quote_fette) == 0
    assert membrature[0].base_sezione.shape == (0, 3)
```

- [ ] **Passo 2: eseguilo e verifica che fallisca o passi**

Esegui: `uv run pytest tests/test_pipeline.py::test_un_prior_scritto_prima_delle_nuove_misure_si_rilegge_ancora -v`

**Può darsi che passi già**, perché i tre campi hanno un predefinito e `_ricostruisci_membrature` non li nomina. In quel caso **il test resta**: è la guardia che impedisce a un compito futuro di renderli obbligatori senza accorgersene. Annotalo nel messaggio di commit e salta al passo 4.

- [ ] **Passo 3: se fallisce, non nominare le chiavi nuove nel costruttore**

`_ricostruisci_membrature` costruisce `Membratura` per parola chiave. Lascia i tre campi fuori: il predefinito è già la risposta giusta, e leggerli con `voce.get(...)` produrrebbe un array vuoto identico al predefinito, cioè lo stesso esito per più codice.

- [ ] **Passo 4: esegui i test del modulo**

Esegui: `uv run pytest tests/test_pipeline.py -q`
Atteso: nessun rosso nuovo oltre ai 9 ambientali.

- [ ] **Passo 5: commit**

```bash
git add meshrec/tests/test_pipeline.py
git commit -m "test(pipeline): un prior senza le misure nuove si rilegge e non viene completato"
```

---

### Compito 8: l'invariante delle ventidue righe

**File:**
- Test: `meshrec/tests/test_sweep.py`

**Interfacce:**
- Consuma: niente.
- Produce: la prova eseguibile che questo sottosistema non ha spostato l'impronta dei registri.

- [ ] **Passo 1: scrivi il test**

Il test usa `json`, `pytest`, `pathlib.Path`, `PipelineConfig` e `sweep`: controlla che siano già importati in testa a `tests/test_sweep.py` e aggiungi solo quelli che mancano. Il percorso `experiments/` è relativo alla cartella `meshrec/`, che è da dove la suite gira.

```python
def test_le_impronte_dei_registri_non_si_muovono():
    """Le ventidue righe di experiments/ sono la tabella sperimentale della
    tesi. Ogni riga porta la propria configurazione e la propria impronta:
    ricalcolare la seconda dalla prima deve dare lo stesso valore, oggi come
    quando fu scritta.

    E' l'invariante che governa tutta la Fase 8 -- ogni blocco nuovo di
    PipelineConfig la mette a rischio -- e va verificata dopo ogni onda, non
    solo dopo quella che tocca la configurazione.
    """
    registri = sorted(Path("experiments").glob("*/registro.jsonl"))
    if not registri:
        pytest.skip("nessun registro di sweep in questa copia di lavoro")

    righe = 0
    for registro in registri:
        for linea in registro.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            record = json.loads(linea)
            cfg = PipelineConfig.model_validate(record["config"])
            assert sweep.fingerprint(cfg) == record["fingerprint"], (
                f"{registro}: l'impronta di una riga gia' registrata e' cambiata"
            )
            righe += 1
    assert righe == 22, f"attese 22 righe registrate, trovate {righe}"
```

- [ ] **Passo 2: eseguilo**

Esegui: `uv run pytest tests/test_sweep.py::test_le_impronte_dei_registri_non_si_muovono -v`
Atteso: PASSATO, con 22 righe verificate.

Se fallisce **adesso**, non è colpa di questo piano: significa che l'impronta era già disallineata prima, ed è un difetto da riportare e non da aggirare. Fermati e dillo.

- [ ] **Passo 3: commit**

```bash
git add meshrec/tests/test_sweep.py
git commit -m "test(sweep): le impronte delle ventidue righe registrate non si muovono"
```

---

## Verifica finale del sottosistema

- [ ] `uv run pytest -q` dentro `meshrec/`, e il conteggio dei rossi è **lo stesso** di prima di cominciare (26 ambientali su questa macchina).
- [ ] `python3 docs/validazione/controlla-riferimenti.py docs/superpowers/specs/2026-08-29-meshrec-fase-8-prior-esteso-design.md` esce 0.
- [ ] Il round di review prima del merge, come prescrive `dev-workflow`: `code-reviewer`, `security-reviewer`, `craft-reviewer`, `test-writer` in parallelo.
