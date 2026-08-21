## Task 6: la qualita' degli esaedri e' lo Jacobiano scalato, ed e' una colonna separata

`min_ratio` non vale per gli esaedri e la differenza fra le due metriche non e' una grandezza: sono due colonne, mai una sottrazione.

**Files:**
- Modify: `src/meshrec/core/quality.py`
- Test: `tests/test_quality.py`

**Interfaces:**
- Consumes: `quality.hex_volumes`, `quality._distribution` (Task 4 e preesistente).
- Produces: `quality.scaled_jacobian(nodes, hexes) -> np.ndarray`; `quality.hexa_metrics(nodes, hexes) -> dict[str, object]`.

- [ ] **Step 1: I test dello Jacobiano scalato**

In coda a `tests/test_quality.py`:

```python
_CUBO_NODI = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
_CUBO_HEX = np.array([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=np.int64)


def test_lo_jacobiano_scalato_di_un_cubo_vale_uno():
    """Il cubo e' l'elemento perfetto: se non vale 1, la metrica non e' quella
    che dice di essere e ogni numero che ne discende e' senza scala."""
    assert quality.scaled_jacobian(_CUBO_NODI, _CUBO_HEX) == pytest.approx([1.0])


def test_lo_jacobiano_scalato_di_un_elemento_tagliato_vale_il_valore_atteso():
    """Il caso degradato ancorato a un valore noto in forma chiusa.

    Portare la faccia superiore avanti di `s` trasforma il cubo in un
    parallelepipedo di spigoli (1,0,0), (0,1,0), (s,0,1). Il determinante vale
    1 e il prodotto delle norme sqrt(1+s^2), a ogni angolo e per costruzione:
    il valore atteso e' quindi 1/sqrt(1+s^2), calcolabile su carta prima di
    eseguire il codice. Il numero non viene da questa implementazione, ed e'
    per questo che il test puo' smentirla.
    """
    tagliato = _CUBO_NODI.copy()
    tagliato[4:, 0] += 1.0

    valore = quality.scaled_jacobian(tagliato, _CUBO_HEX)[0]

    assert valore == pytest.approx(1.0 / math.sqrt(2.0))


def test_lo_jacobiano_scalato_non_misura_lo_schiacciamento():
    """Il limite della metrica, scritto come controllo e non come commento.

    Un esaedro sottile quanto si vuole, finche' resta rettangolo, ha Jacobiano
    scalato 1: la formula divide ogni spigolo per la propria lunghezza, quindi
    non vede il rapporto di forma. Chi cerca gli elementi troppo sottili deve
    guardare altrove — il vincolo sul numero di strati nello spessore e la
    distribuzione dei volumi di elemento. Questo test esiste perche' qualcuno,
    un giorno, credera' il contrario.
    """
    sottile = _CUBO_NODI.copy()
    sottile[4:, 2] = 0.1

    assert quality.scaled_jacobian(sottile, _CUBO_HEX) == pytest.approx([1.0])


def test_lo_jacobiano_scalato_e_negativo_su_un_angolo_ripiegato():
    """Un angolo ripiegato non e' un elemento rovesciato, ed e' peggio da
    trovare: l'elemento e' orientato bene ovunque tranne che in un vertice,
    quindi un controllo globale sull'orientamento non lo vedrebbe. Portando il
    nodo 6 verso il centro oltre la diagonale, la faccia superiore diventa
    concava e il minimo sugli otto angoli scende sotto zero.
    """
    ripiegato = _CUBO_NODI.copy()
    ripiegato[6] = [0.35, 0.35, 1.0]

    assert quality.scaled_jacobian(ripiegato, _CUBO_HEX)[0] < 0.0


def test_lo_jacobiano_scalato_e_non_positivo_su_un_elemento_rovesciato():
    rovesciato = np.array([[4, 5, 6, 7, 0, 1, 2, 3]], dtype=np.int64)

    assert quality.scaled_jacobian(_CUBO_NODI, rovesciato)[0] <= 0.0


def test_le_metriche_esaedriche_non_contengono_min_ratio():
    """min_ratio e' il rapporto raggio-spigolo di un tetraedro e su un esaedro
    non e' definito. Metterlo nella stessa colonna dello Jacobiano scalato
    inviterebbe a sottrarre due grandezze diverse."""
    metriche = quality.hexa_metrics(_CUBO_NODI, _CUBO_HEX)

    assert "scaled_jacobian" in metriche
    assert "min_ratio" not in metriche
    assert "radius_edge_ratio" not in metriche
    assert metriche["inverted"] == 0
    assert metriche["hexes"] == 1
    assert metriche["total_volume"] == pytest.approx(1.0)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_quality.py -k "jacobiano or esaedric" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.quality' has no attribute 'scaled_jacobian'`.

- [ ] **Step 3: Implementare**

In `quality.py`, sotto `hex_volumes`:

```python
# Per ciascuno degli otto nodi di un esaedro, i tre nodi adiacenti nell'ordine
# che da' determinante positivo su un cubo con la numerazione standard
# (0-3 faccia inferiore in verso antiorario, 4-7 la superiore sopra di essi).
# Verificata a mano, nodo per nodo, sul cubo unitario: tutti e otto danno +1.
_ANGOLI_ESAEDRO = (
    (1, 3, 4), (2, 0, 5), (3, 1, 6), (0, 2, 7),
    (7, 5, 0), (4, 6, 1), (5, 7, 2), (6, 4, 3),
)


def scaled_jacobian(nodes: np.ndarray, hexes: np.ndarray) -> np.ndarray:
    """Jacobiano scalato di ogni esaedro: il minimo sugli otto angoli.

    E' la grandezza di qualita' degli esaedri, e non ha nulla a che vedere con
    `min_ratio`, che e' il rapporto raggio-spigolo di un tetraedro. Su un
    esaedro min_ratio non e' definito, quindi le due vivono in due colonne
    separate e la loro differenza non e' una grandezza: sottrarle darebbe un
    numero senza unita' e senza significato.

    In ogni angolo si prendono i tre spigoli uscenti, se ne calcola il
    determinante e lo si divide per il prodotto delle tre lunghezze. Vale 1 sul
    cubo, scende man mano che gli angoli si allontanano da quelli retti, ed e'
    non positivo dove l'elemento e' rovesciato o ripiegato. E' quindi anche il
    controllo che cerca gli Jacobiani negativi chiesto dalla spec, senza una
    seconda misura.

    Non misura lo schiacciamento: normalizzando ogni spigolo per la propria
    lunghezza e' invariante di scala per direzione, quindi un esaedro sottile
    ma rettangolo vale 1 come il cubo. Gli elementi troppo sottili si trovano
    con il numero di strati nello spessore e con la distribuzione dei volumi,
    non di qui.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    h = np.asarray(hexes, dtype=np.int64)
    minimi = np.full(len(h), np.inf)

    for angolo, (a, b, c) in enumerate(_ANGOLI_ESAEDRO):
        origine = punti[h[:, angolo]]
        e1 = punti[h[:, a]] - origine
        e2 = punti[h[:, b]] - origine
        e3 = punti[h[:, c]] - origine
        determinante = np.einsum("ij,ij->i", e1, np.cross(e2, e3))
        prodotto = (
            np.linalg.norm(e1, axis=1)
            * np.linalg.norm(e2, axis=1)
            * np.linalg.norm(e3, axis=1)
        )
        # prodotto nullo vuol dire spigolo degenere: l'elemento e' rotto, e il
        # valore che lo dice e' zero, non un NaN che si propaga in silenzio
        valore = np.divide(
            determinante, prodotto, out=np.zeros_like(determinante), where=prodotto > 0.0
        )
        minimi = np.minimum(minimi, valore)

    return np.ascontiguousarray(minimi)


def hexa_metrics(nodes: np.ndarray, hexes: np.ndarray) -> dict[str, object]:
    """Metriche di volume di una mesh esaedrica.

    Deliberatamente **senza** min_ratio, rapporto raggio-spigolo e angolo
    diedro: sono grandezze del tetraedro, e riportarle qui accanto a quelle
    dell'esaedro inviterebbe a confrontare due colonne che non si confrontano.
    Il confronto fra i modelli, in report.py, le tiene infatti separate e
    dichiara che la qualita' degli elementi non e' una grandezza confrontabile
    fra un modello tetraedrico e uno esaedrico.
    """
    volumi = hex_volumes(nodes, hexes)
    jacobiani = scaled_jacobian(nodes, hexes)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "hexes": int(len(np.asarray(hexes))),
        "inverted": int((jacobiani <= 0.0).sum()),
        "total_volume": float(volumi.sum()),
        "element_volume": _distribution(volumi),
        "scaled_jacobian": _distribution(jacobiani),
    }
```

- [ ] **Step 4: Eseguire**

Run: `uv run pytest tests/test_quality.py -v`
Expected: PASS.

- [ ] **Step 5: La suite intera e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/quality.py meshrec/tests/test_quality.py
git commit -m "feat(fase-4): Jacobiano scalato degli esaedri, colonna separata da min_ratio"
```

---


---

## Correzione del 20/08/2026 (Ruling O e P)

La prima stesura di questo brief conteneva un test sbagliato,
`test_lo_jacobiano_scalato_scende_su_un_elemento_schiacciato`, ora sostituito
qui sopra dai tre test su taglio, schiacciamento e angolo ripiegato. Il
difetto non erano le coordinate: era falsa la proprieta' che il test diceva di
verificare. Lo Jacobiano scalato **non misura lo schiacciamento** — un cubo
portato a spessore 0.1 vale ancora 1.0 esatto su tutti e otto gli angoli,
perche' la formula normalizza ogni spigolo per la propria lunghezza ed e'
quindi invariante di scala per direzione.

Attenzione alla trappola, perche' e' aperta: spostare il nodo 6 a
(0.75, 0.75, 1.0) da' 0.7542, cioe' cade nel vecchio range atteso e fa tornare
verde la suite — documentando pero' una bugia su cosa la metrica sa vedere.
Il caso degradato va ancorato a `1/sqrt(1+s^2)`, che si calcola su carta prima
di eseguire il codice.
