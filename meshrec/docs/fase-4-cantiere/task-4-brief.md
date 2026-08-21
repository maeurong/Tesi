## Task 4: `core/abaqus.py` generalizzato per tipo di elemento

Non una versione esaedrica parallela: **le stesse funzioni**, che smettono di dare per scontati quattro nodi per elemento e tre nodi per faccia.

**Files:**
- Modify: `src/meshrec/core/abaqus.py`
- Test: `tests/test_abaqus.py`

**Interfaces:**
- Consumes: `config.ModelConfig` (Task 1).
- Produces:
  - `abaqus.NODI_PER_ELEMENTO: dict[str, int]` — `{"C3D4": 4, "C3D10": 10, "C3D8": 8, "C3D8I": 8, "C3D8R": 8}`.
  - `abaqus.FACCE_TOPOLOGICHE: dict[int, tuple[tuple[int, ...], ...]]` — combinazioni di faccia per numero di nodi d'angolo.
  - `abaqus.boundary_faces(elements) -> np.ndarray` (pubblica, generalizzata).
  - `abaqus.write_inp(path, nodes, elements, *, element_type="C3D4", ...)`.
  - `abaqus.export_model(..., element_type=...)`.

- [ ] **Step 1: I test della generalizzazione**

In coda a `tests/test_abaqus.py`:

```python
def test_le_facce_di_bordo_di_un_esaedro_solo_sono_sei_quadrilateri():
    """_boundary_faces dava per scontati quattro nodi per elemento e tre per
    faccia. Un esaedro ha sei facce, tutte quadrilatere, e tutte di bordo."""
    esaedro = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    facce = abaqus.boundary_faces(esaedro)

    assert facce.shape == (6, 4)
    assert len(np.unique(facce, axis=0)) == 6


def test_due_esaedri_affiancati_non_hanno_la_faccia_condivisa_sul_bordo():
    """Il controllo che smentisce il precedente: se la faccia interna comparisse
    fra quelle di bordo, ogni set di faccia e ogni superficie esportata
    conterrebbero nodi interni al solido."""
    doppio = np.array(
        [[0, 1, 2, 3, 4, 5, 6, 7], [4, 5, 6, 7, 8, 9, 10, 11]], dtype=np.int64
    )

    facce = abaqus.boundary_faces(doppio)

    assert facce.shape == (10, 4), "sei piu' sei meno la faccia condivisa contata due volte"
    condivisa = np.sort(np.array([4, 5, 6, 7]))
    assert not (np.sort(facce, axis=1) == condivisa).all(axis=1).any()


def test_le_facce_di_bordo_dei_tetraedri_restano_quelle_di_prima():
    """La generalizzazione non deve cambiare il comportamento sui tetraedri: e'
    la macchina con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2."""
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )

    facce = abaqus.boundary_faces(tets)

    assert facce.shape[1] == 3
    assert len(np.unique(facce)) == len(np.unique(abaqus.boundary_faces(tets)))
    # una superficie chiusa: ogni spigolo compare in esattamente due facce
    spigoli = np.sort(
        np.vstack([facce[:, [0, 1]], facce[:, [1, 2]], facce[:, [0, 2]]]), axis=1
    )
    _, conteggi = np.unique(spigoli, axis=0, return_counts=True)
    assert (conteggi == 2).all()


def test_il_deck_dichiara_il_tipo_di_elemento_che_gli_si_chiede(tmp_path):
    """C3D8I non e' un dettaglio estetico: un telaio lavora a flessione, e C3D8
    a integrazione piena si irrigidirebbe a taglio restituendo spostamenti
    troppo piccoli senza alcun segnale sulla mesh."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)
    percorso = tmp_path / "esaedro.inp"

    abaqus.write_inp(
        percorso, nodi, esaedri,
        node_sets={"BASE": np.array([0, 1, 2, 3])},
        material=MATERIALE,
        element_type="C3D8I",
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D8I, ELSET=ALL_WALL" in testo
    assert "1, 1, 2, 3, 4, 5, 6, 7, 8" in testo
    assert "*ELEMENT, TYPE=C3D4" not in testo


def test_un_tipo_di_elemento_che_non_combacia_coi_nodi_viene_rifiutato(tmp_path):
    """L'errore arriva prima di scrivere il file, non dopo che un solutore ha
    letto un deck con otto nodi dichiarati C3D4."""
    nodi = np.zeros((8, 3))
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    with pytest.raises(ValueError, match="C3D4"):
        abaqus.write_inp(
            tmp_path / "storto.inp", nodi, esaedri,
            node_sets={"BASE": np.array([0])},
            material=MATERIALE,
            element_type="C3D4",
        )
```

Assicurati che in testa a `tests/test_abaqus.py` ci siano gli import `synth`, `volume` e `MATERIALE` da `materiale`; se manca qualcuno, aggiungilo accanto a quelli gia' presenti.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_abaqus.py -k "esaedr or bordo or tipo_di_elemento" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.abaqus' has no attribute 'boundary_faces'`.

- [ ] **Step 3: Le tabelle e `boundary_faces`**

In `abaqus.py`, sostituisci `_TET_FACE_COMBOS` e `_boundary_faces` con:

```python
NODI_PER_ELEMENTO: dict[str, int] = {
    "C3D4": 4,
    "C3D10": 10,
    "C3D8": 8,
    "C3D8I": 8,
    "C3D8R": 8,
}
"""Nodi per elemento di ciascun tipo scrivibile nel deck.

C3D8, C3D8I e C3D8R hanno la stessa geometria e differiscono per la
formulazione: la mesh e' la stessa, cambia cosa il solutore ne fa. Sono
distinti qui perche' il nome finisce nel deck e il solutore lo legge.
"""

# Le facce di un elemento, come insiemi di nodi d'angolo, per il solo scopo di
# trovare il bordo: qui l'ordine dentro la faccia non conta, perche' le facce
# vengono ordinate prima di essere confrontate. La tabella che l'ordine ce
# l'ha, e con esso il numero S della faccia, e' FACCE_DEL_SOLUTORE (Task 5):
# le due non vanno confuse, ed e' per questo che portano nomi diversi.
FACCE_TOPOLOGICHE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)),
    8: (
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ),
}


def boundary_faces(elements: np.ndarray) -> np.ndarray:
    """Facce sul bordo della mesh di volume, per qualunque tipo di elemento.

    Stesso ragionamento di quality.boundary_edges, esteso alle facce: si
    costruiscono tutte le facce di ogni elemento, si ordinano gli indici al
    loro interno, si contano le occorrenze e si tengono quelle con occorrenza
    singola.

    La generalizzazione e' sui **nodi d'angolo**: un C3D10 ha dieci nodi ma la
    sua topologia e' quella del tetraedro, e i nodi di lato non definiscono
    facce proprie. Le prime quattro colonne di un C3D10 sono i suoi vertici,
    che e' la convenzione di TetGen e di Abaqus.
    """
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if elementi.shape[1] == 8 else 4
    combinazioni = FACCE_TOPOLOGICHE[angoli]
    facce = np.vstack([elementi[:, combo] for combo in combinazioni])
    facce = np.sort(facce, axis=1)
    uniche, conteggi = np.unique(facce, axis=0, return_counts=True)
    return uniche[conteggi == 1]


# Il nome privato resta come alias per non toccare i chiamanti interni gia'
# scritti e verificati: e' la stessa funzione, non una seconda.
_boundary_faces = boundary_faces
```

- [ ] **Step 4: `boundary_spacing` per facce di qualunque grado**

In `abaqus.py`, dentro `boundary_spacing`, sostituisci la costruzione degli spigoli con:

```python
    # Gli spigoli di una faccia sono le coppie di nodi consecutivi lungo il suo
    # perimetro: np.roll li da' per un triangolo come per un quadrilatero,
    # senza una tabella per grado.
    edges = np.sort(
        np.vstack([np.stack([f[:, i], f[:, (i + 1) % f.shape[1]]], axis=1) for i in range(f.shape[1])]),
        axis=1,
    )
    edges = np.unique(edges, axis=0)
```

Aggiungi alla docstring, in coda:

```
    Dalla Fase 4 vale anche sulle facce quadrilatere della mesh esaedrica: gli
    spigoli sono le coppie consecutive lungo il perimetro, quale che sia il
    numero di lati.
```

- [ ] **Step 5: `write_inp` per tipo di elemento**

In `abaqus.py`, cambia la firma e le due parti che davano per scontato il tetraedro:

```python
def write_inp(
    path: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    element_type: str = "C3D4",
    fixed_nset: str = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    step_name: str = "GRAVITA",
) -> None:
    """Scrive un modello pronto all'analisi statica sotto peso proprio.

    `element_type` e' il nome che il solutore legge, e il numero di nodi per
    elemento deve combaciare con esso: un array di otto colonne dichiarato
    C3D4 produrrebbe un deck che nessun solutore puo' leggere, e l'errore
    arriverebbe dopo l'intera pipeline invece che qui.

    Il predefinito C3D4 non e' un parametro di elaborazione con un valore
    scelto: e' il comportamento che questa funzione aveva prima della Fase 4,
    tenuto perche' i chiamanti gia' scritti continuino a valere. Chi sceglie
    davvero il tipo lo prende da `tet.element` o da `model.element`.
    """
    if fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(
            f"tipo di elemento '{element_type}' sconosciuto: "
            f"i tipi scrivibili sono {sorted(NODI_PER_ELEMENTO)}"
        )

    nodes = np.asarray(nodes, dtype=np.float64)
    elements = np.asarray(elements, dtype=np.int64)
    attesi = NODI_PER_ELEMENTO[element_type]
    if elements.shape[1] != attesi:
        raise ValueError(
            f"{element_type} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: un deck scritto cosi' non e' leggibile da alcun solutore"
        )

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE={element_type}, ELSET={elset}")
    lines += [
        ", ".join([str(index + 1)] + [str(nodo + 1) for nodo in elemento])
        for index, elemento in enumerate(elements)
    ]
```

Il resto del corpo — i set di nodo, il materiale, il vincolo, lo step, le stampe e l'uscita — resta **identico**. Rinomina le occorrenze di `tets` in `elements` dove compaiono.

- [ ] **Step 6: `export_model` accetta gli esaedri**

In `export_model`, sostituisci la firma e la guardia sul tipo:

```python
def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
    reference: np.ndarray | None = None,
    element_type: str | None = None,
) -> dict[str, object]:
```

e al posto della `NotImplementedError` su `tet_cfg.element != "C3D4"`:

```python
    tipo = tet_cfg.element if element_type is None else element_type
    if tipo == "C3D10":
        raise NotImplementedError(
            "elemento C3D10 non supportato dal writer: TetGen produce i nodi di "
            "lato con order=2, ma il deck scrive i soli vertici. Usa C3D4 finche' "
            "il writer non gestisce i dieci nodi."
        )
    if tipo not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{tipo}' sconosciuto")
```

Dentro il corpo, sostituisci `tets` con `elements`, `_boundary_faces(tets)` con `boundary_faces(elements)`, e la riga del volume:

```python
    from meshrec.core.quality import element_volumes

    volume = float(np.abs(element_volumes(aligned, elements)).sum())
```

Aggiungi `"element_type": tipo,` al dizionario restituito, e passa `element_type=tipo` a `write_inp` e a `write_vtu`.

- [ ] **Step 7: `write_vtu` per tipo di elemento**

```python
def write_vtu(
    path: Path, nodes: np.ndarray, elements: np.ndarray, element_type: str = "C3D4"
) -> None:
    """Esportazione per la visualizzazione, delegata a meshio.

    meshio ha nomi propri per i tipi di cella, che non sono quelli del
    solutore: la tabella traduce, e un tipo non tradotto solleva invece di
    scrivere un file che nessun visualizzatore aprirebbe.
    """
    import meshio

    celle = {"C3D4": "tetra", "C3D10": "tetra10", "C3D8": "hexahedron",
             "C3D8I": "hexahedron", "C3D8R": "hexahedron"}
    if element_type not in celle:
        raise ValueError(f"tipo di elemento '{element_type}' senza corrispondente in meshio")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write_points_cells(
        str(path),
        np.asarray(nodes, dtype=np.float64),
        [(celle[element_type], np.asarray(elements, dtype=np.int64))],
    )
```

- [ ] **Step 8: `element_volumes` in `quality.py`, il minimo che serve qui**

In `quality.py`, subito sotto `tet_volumes`:

```python
# Decomposizione di un esaedro in sei tetraedri, a ventaglio dal nodo 0 attorno
# alla diagonale 0-6. Verificata a mano sul cubo unitario: i sei volumi valgono
# 1/6 ciascuno, e la somma vale esattamente 1.
_HEX_IN_TET = (
    (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6),
    (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6),
)


def hex_volumes(nodes: np.ndarray, hexes: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni esaedro, per decomposizione in sei tetraedri.

    Non e' la quadratura di Gauss dell'elemento trilineare, e su un esaedro con
    facce non piane le due differiscono: la decomposizione misura il volume del
    solido a facce triangolate, che e' anche quello che la superficie di bordo
    racchiude. E' la definizione coerente con `mesh_volume`, quindi le due
    misure si possono confrontare invece di divergere in silenzio.
    """
    h = np.asarray(hexes, dtype=np.int64)
    return sum(tet_volumes(nodes, h[:, list(combo)]) for combo in _HEX_IN_TET)


def element_volumes(nodes: np.ndarray, elements: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni elemento, quale che sia il tipo.

    E' l'unico punto in cui il resto del programma deve chiedersi quanti nodi
    ha un elemento: chi la chiama non lo sa e non deve saperlo.
    """
    colonne = np.asarray(elements).shape[1]
    if colonne == 8:
        return hex_volumes(nodes, elements)
    if colonne in (4, 10):
        return tet_volumes(nodes, np.asarray(elements)[:, :4])
    raise ValueError(f"elemento con {colonne} nodi: nessun volume definito per questa forma")
```

- [ ] **Step 9: Il test del volume esaedrico**

In coda a `tests/test_quality.py`:

```python
def test_il_volume_di_un_cubo_unitario_vale_uno():
    """La decomposizione in sei tetraedri e' verificata a mano nel commento:
    questo test la verifica di nuovo, e cade se qualcuno la riordina."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    esaedri = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)

    assert quality.hex_volumes(nodi, esaedri) == pytest.approx([1.0])
    assert quality.element_volumes(nodi, esaedri) == pytest.approx([1.0])


def test_il_volume_esaedrico_e_negativo_se_l_elemento_e_rovesciato():
    """Il controllo che smentisce: scambiando la faccia inferiore con la
    superiore il volume cambia segno, ed e' cosi' che un elemento invertito si
    fa vedere invece di passare per buono."""
    nodi = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ])
    rovesciato = np.array([[4, 5, 6, 7, 0, 1, 2, 3]], dtype=np.int64)

    assert quality.hex_volumes(nodi, rovesciato)[0] < 0.0


def test_element_volumes_sui_tetraedri_da_quello_che_dava_tet_volumes():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False,
    )

    assert quality.element_volumes(nodes, tets) == pytest.approx(quality.tet_volumes(nodes, tets))
```

- [ ] **Step 10: Eseguire i test di `abaqus` e `quality`**

Run: `uv run pytest tests/test_abaqus.py tests/test_quality.py -v`
Expected: PASS. I test gia' esistenti su `write_inp` e `export_model` passavano `tets` come terzo argomento posizionale e continuano a valere: se qualcuno lo passava per nome (`tets=`), aggiornalo a `elements=`.

- [ ] **Step 11: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. `test_pipeline.py` e `test_cli.py` esercitano `export_model` sul percorso tetraedrico: se cadono, la generalizzazione ha cambiato il comportamento sui tetraedri, che e' il solo esito inaccettabile di questo task.

- [ ] **Step 12: Commit**

```bash
git add meshrec/src/meshrec/core/abaqus.py meshrec/src/meshrec/core/quality.py meshrec/tests/test_abaqus.py meshrec/tests/test_quality.py
git commit -m "feat(fase-4): abaqus e quality generalizzati per tipo di elemento"
```

---

