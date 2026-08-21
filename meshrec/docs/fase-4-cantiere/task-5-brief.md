## Task 5: `*SURFACE, TYPE=ELEMENT`, `*TIE` e carico laterale — il debito rinviato dalla Fase 1

La mappatura delle facce dell'elemento sulle etichette del solutore e' **la fonte d'errore silenzioso per cui il debito era stato rinviato**: una tabella sbagliata produce un deck che il solutore legge senza protestare, applicando il carico alla faccia sbagliata. Ha quindi un test proprio, e il test non guarda la tabella: guarda la geometria che la tabella nomina.

**Files:**
- Modify: `src/meshrec/core/abaqus.py`
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `abaqus.NODI_PER_ELEMENTO`, `abaqus.boundary_faces` (Task 4).
- Produces:
  - `abaqus.FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]]` — per numero di nodi d'angolo, i nodi di S1, S2, ... nell'ordine del solutore.
  - `abaqus.element_surface(elements, indici_nodo, element_type) -> list[tuple[int, int]]` — coppie `(elemento, numero di faccia)`.
  - `abaqus.surface_area(nodes, elements, superficie, element_type) -> float`.
  - `write_inp(..., element_surfaces: dict[str, list[tuple[int, int]]] | None = None, ties: tuple[tuple[str, str, str], ...] = (), pressure: tuple[str, float] | None = None)`.

- [ ] **Step 1: I test della mappatura, che guardano la geometria e non la tabella**

In coda a `tests/test_abaqus.py`:

```python
_CUBO = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
_ESAEDRO = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_le_sei_etichette_di_faccia_di_un_esaedro_sono_le_sue_sei_facce():
    """Il test non legge la tabella: costruisce l'insieme dei nodi che ogni
    etichetta nomina e verifica che siano le sei facce distinte del cubo. Una
    tabella sbagliata nominerebbe due volte la stessa faccia, o una diagonale."""
    nominate = {
        tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[8][numero]))
        for numero in range(6)
    }
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(_ESAEDRO).tolist()}

    assert len(nominate) == 6
    assert nominate == vere


def test_le_quattro_etichette_di_faccia_di_un_tetraedro_sono_le_sue_quattro_facce():
    tetraedro = np.array([[0, 1, 2, 3]], dtype=np.int64)
    nominate = {tuple(sorted(abaqus.FACCE_DEL_SOLUTORE[4][numero])) for numero in range(4)}
    vere = {tuple(sorted(faccia)) for faccia in abaqus.boundary_faces(tetraedro).tolist()}

    assert len(nominate) == 4
    assert nominate == vere


def test_la_superficie_di_elemento_di_una_faccia_nominata_ha_l_area_giusta():
    """Il controllo della spec: area della superficie esportata contro area
    calcolata sulle facce. Su un cubo unitario ogni faccia vale 1."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    assert superficie == [(0, 1)], "la faccia z=0 di un C3D8 e' S1"
    assert abaqus.surface_area(_CUBO, _ESAEDRO, superficie, "C3D8I") == pytest.approx(1.0)


def test_la_superficie_di_elemento_non_nomina_una_faccia_solo_sfiorata():
    """Il controllo che smentisce il precedente: tre nodi su quattro di una
    faccia non sono quella faccia, e nominarla applicherebbe un carico dove
    l'utente non lo ha chiesto."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2]), "C3D8I")

    assert superficie == []


def test_la_superficie_esportata_ha_l_area_delle_facce_che_dichiara(tmp_path):
    """Il deck e' la fonte: si rilegge il file e si contano le coppie scritte,
    invece di fidarsi di cio' che la funzione ha restituito."""
    nodi_base = np.flatnonzero(_CUBO[:, 2] <= 1e-9)
    superficie = abaqus.element_surface(_ESAEDRO, nodi_base, "C3D8I")
    percorso = tmp_path / "carico.inp"

    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": nodi_base},
        material=MATERIALE,
        element_type="C3D8I",
        element_surfaces={"FACCIA_BASSA": superficie},
        pressure=("FACCIA_BASSA", 0.25),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT, NAME=FACCIA_BASSA" in testo
    assert "1, S1" in testo
    assert "*DSLOAD" in testo
    assert "FACCIA_BASSA, P, 0.25" in testo


def test_senza_carico_laterale_il_deck_non_ha_alcuna_card_di_pressione(tmp_path):
    """Il carico laterale e' opzionale e assente se non richiesto: un deck che
    lo portasse comunque a zero applicherebbe una pressione nulla dichiarata,
    che e' un'altra cosa da nessuna pressione."""
    percorso = tmp_path / "senza.inp"
    abaqus.write_inp(
        percorso, _CUBO, _ESAEDRO,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*DSLOAD" not in testo
    assert "*SURFACE" not in testo
    assert "*TIE" not in testo


def test_il_tie_nomina_due_superfici_gia_dichiarate(tmp_path):
    """Un *TIE che punta a una superficie mai dichiarata e' un deck rotto che
    il solutore rifiuta solo alla lettura: l'errore arriva prima."""
    superficie = abaqus.element_surface(_ESAEDRO, np.array([0, 1, 2, 3]), "C3D8I")

    with pytest.raises(ValueError, match="MAI_DICHIARATA"):
        abaqus.write_inp(
            tmp_path / "rotto.inp", _CUBO, _ESAEDRO,
            node_sets={"BASE": np.array([0, 1, 2, 3])},
            material=MATERIALE,
            element_type="C3D8I",
            element_surfaces={"UNA": superficie},
            ties=(("GIUNZIONE_1", "UNA", "MAI_DICHIARATA"),),
        )
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_abaqus.py -k "faccia or superficie or tie or carico or pressione" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'FACCE_DEL_SOLUTORE'`.

- [ ] **Step 3: La tabella delle etichette del solutore**

In `abaqus.py`, subito sotto `FACCE_TOPOLOGICHE`:

```python
# Le facce di un elemento nell'ordine e con la numerazione del solutore: S1 e'
# la prima riga, S2 la seconda, e cosi' via. E' la tabella che il debito
# rinviato dalla Fase 1 chiedeva, ed e' la fonte d'errore silenzioso per cui
# era stato rinviato: sbagliarla produce un deck che il solutore legge senza
# protestare, applicando il carico a una faccia diversa da quella chiesta.
#
# C3D4, dal manuale: S1 = 1-2-3, S2 = 1-4-2, S3 = 2-4-3, S4 = 3-4-1.
# C3D8, dal manuale: S1 = 1-2-3-4, S2 = 5-8-7-6, S3 = 1-5-6-2,
#                    S4 = 2-6-7-3, S5 = 3-7-8-4, S6 = 4-8-5-1.
# Qui gli indici sono 0-based, quindi ciascuno vale uno in meno.
#
# Non e' FACCE_TOPOLOGICHE con un altro nome: quella serve a trovare il bordo e
# ordina gli indici prima di confrontarli, quindi puo' elencare le facce in
# qualunque ordine. Questa non puo': l'ordine E' l'informazione.
FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)),
    8: (
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ),
}


def element_surface(
    elements: np.ndarray, indici_nodo: np.ndarray, element_type: str
) -> list[tuple[int, int]]:
    """Le coppie (elemento, numero di faccia) le cui facce cadono nell'insieme dato.

    Una faccia entra nella superficie solo se **tutti** i suoi nodi stanno
    nell'insieme: tre nodi su quattro non sono quella faccia, e nominarla
    applicherebbe un carico dove l'utente non lo ha chiesto.

    L'ordine delle coppie e' quello degli elementi e, dentro un elemento,
    quello dei numeri di faccia: e' funzione del dato e non dell'iterazione,
    quindi il deck scritto su due macchine e' lo stesso file.
    """
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{element_type}' sconosciuto")
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if NODI_PER_ELEMENTO[element_type] == 8 else 4
    dentro = np.zeros(int(elementi.max()) + 1, dtype=bool)
    dentro[np.asarray(indici_nodo, dtype=np.int64)] = True

    coppie: list[tuple[int, int]] = []
    for numero, combo in enumerate(FACCE_DEL_SOLUTORE[angoli], start=1):
        tutte_dentro = dentro[elementi[:, list(combo)]].all(axis=1)
        coppie += [(int(indice), numero) for indice in np.flatnonzero(tutte_dentro)]
    coppie.sort()
    return coppie


def surface_area(
    nodes: np.ndarray,
    elements: np.ndarray,
    superficie: list[tuple[int, int]],
    element_type: str,
) -> float:
    """Area della superficie di elemento, sommata faccia per faccia.

    E' il controllo che smentisce la superficie esportata: se l'area calcolata
    qui non coincide con quella delle facce che il deck dichiara, la tabella
    delle etichette nomina facce diverse da quelle volute. Una faccia di piu'
    di tre nodi e' divisa a ventaglio dal primo, che e' esatto per una faccia
    piana e sottostima di poco una faccia svergolata.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if NODI_PER_ELEMENTO[element_type] == 8 else 4

    totale = 0.0
    for elemento, numero in superficie:
        nodi = [elementi[elemento][indice] for indice in FACCE_DEL_SOLUTORE[angoli][numero - 1]]
        for primo, secondo in zip(nodi[1:-1], nodi[2:], strict=True):
            lato_a = punti[primo] - punti[nodi[0]]
            lato_b = punti[secondo] - punti[nodi[0]]
            totale += float(np.linalg.norm(np.cross(lato_a, lato_b)) / 2.0)
    return totale
```

- [ ] **Step 4: Le tre card nuove in `write_inp`**

Aggiungi alla firma di `write_inp`, dopo `element_type`:

```python
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str], ...] = (),
    pressure: tuple[str, float] | None = None,
```

Dopo i controlli sui `node_sets`, aggiungi:

```python
    superfici = {} if element_surfaces is None else element_surfaces
    for nome, dipendente, indipendente in ties:
        mancanti = [s for s in (dipendente, indipendente) if s not in superfici]
        if mancanti:
            raise ValueError(
                f"il vincolo *TIE '{nome}' nomina {mancanti}, che non e' fra le "
                "superfici dichiarate: un deck cosi' viene rifiutato dal solutore "
                "solo alla lettura, e questo errore arriva prima"
            )
    if pressure is not None and pressure[0] not in superfici:
        raise ValueError(
            f"il carico laterale agisce su '{pressure[0]}', che non e' fra le "
            "superfici dichiarate: una pressione applicata a nulla non e' un carico"
        )
```

Dopo il blocco che scrive i `*NSET` e **prima** di `*SOLID SECTION`:

```python
    for nome, coppie in superfici.items():
        lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={nome}")
        lines += [f"{elemento + 1}, S{numero}" for elemento, numero in coppie]

    for nome, dipendente, indipendente in ties:
        # ADJUST=NO: spostare i nodi della superficie dipendente sulla
        # indipendente cambierebbe la geometria dopo che il volume e' stato
        # misurato, e il modello non sarebbe piu' quello di cui il report parla.
        lines.append(f"*TIE, NAME={nome}, ADJUST=NO")
        lines.append(f"{dipendente}, {indipendente}")
```

E dopo la card `*DLOAD` della gravita', dentro lo step:

```python
    if pressure is not None:
        lines += ["*DSLOAD", f"{pressure[0]}, P, {pressure[1]}"]
```

Aggiungi alla docstring di `write_inp`, in coda:

```
    `element_surfaces`, `ties` e `pressure` sono le tre aggiunte della Fase 4 e
    sono tutte facoltative: senza di esse il deck e' identico a quello che
    questa funzione scriveva prima, ed e' cosi' che le corse tetraedriche
    restano confrontabili con quelle gia' fatte. Un carico assente non diventa
    una pressione dichiarata a zero: le due cose non sono la stessa.
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_abaqus.py -v`
Expected: PASS su tutti.

- [ ] **Step 6: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_abaqus.py
git commit -m "feat(fase-4): superfici di elemento, *TIE e carico laterale nel deck

Chiude il debito rinviato dalla Fase 1. La tabella delle etichette di faccia
e' verificata contro la geometria che nomina, non contro se stessa."
```

---

