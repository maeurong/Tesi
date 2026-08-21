## Task 2: `core/wall.py` — la scomposizione in membrature, senza soglie tarate a mano

**Files:**
- Create: `src/meshrec/core/wall.py`
- Modify: `src/meshrec/core/synth.py` (geometria sintetica di telaio, a verita' nota)
- Modify: `src/meshrec/core/abaqus.py` (`_fix_sign` diventa pubblica `fix_sign`)
- Test: `tests/test_wall.py`, `tests/test_synth.py`

**Interfaces:**
- Consumes: `config.WallConfig` (Task 1); `segment.extract_planes`, `segment.remove_outliers`.
- Produces:
  - `synth.sample_frame_surface(prismi, spacing, noise=0.0, seed=0) -> np.ndarray`, con `prismi: list[tuple[tuple[float, float, float], tuple[float, float, float]]]` cioe' coppie `(origine, dimensioni)`.
  - `wall.fix_sign` riesportata da `abaqus.fix_sign`.
  - `wall.terna(points) -> tuple[np.ndarray, np.ndarray]` — matrice 3x3 delle direzioni `(u, v, n)` e centro.
  - `wall.chiavi_di_cella(coordinate, lato) -> np.ndarray` (N x 2, interi non negativi).
  - `wall.spessore_per_cella(piano, trasversale, lato) -> tuple[np.ndarray, np.ndarray, np.ndarray]` — celle uniche, spessore di ciascuna, indice di cella di ogni punto.
  - `wall.scarta_pavimento(points, cfg_segment, cfg_wall, spacing) -> tuple[np.ndarray, dict]`.
  - `wall.regioni(celle, spessori, cfg) -> list[np.ndarray]` — per ciascuna regione gli indici delle proprie celle, in ordine canonico.
  - `wall.scomponi(points, cfg_segment, cfg_wall, spacing) -> tuple[list[np.ndarray], dict]` — per ciascuna regione gli indici dei propri punti, piu' le metriche della scomposizione.

- [ ] **Step 1: Il telaio sintetico a verita' nota**

In `src/meshrec/core/synth.py`, in coda:

```python
def sample_frame_surface(
    prismi: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    spacing: float,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Campiona le superfici di piu' parallelepipedi, ciascuno con la propria origine.

    Serve alle verifiche del prior: un telaio di membrature prismatiche di cui
    si conoscono sezione, asse, lunghezza e volume analitico, cosi' che la
    scomposizione abbia qualcosa che la smentisca. I numeri dei prismi sono del
    banco di prova, mai del codice: `wall` non sa quante membrature aspettarsi.

    I punti che cadono dentro un altro prisma restano: sono le superfici che
    nella realta' si compenetrano alle giunzioni, e toglierli farebbe misurare
    alla scomposizione una geometria piu' pulita di quella che vedra' mai.
    """
    nuvole = []
    for origine, dimensioni in prismi:
        superficie = sample_box_surface(dimensioni, spacing, noise=noise, seed=seed)
        nuvole.append(superficie + np.asarray(origine, dtype=np.float64))
    return np.ascontiguousarray(np.vstack(nuvole), dtype=np.float64)
```

- [ ] **Step 2: Il test del telaio sintetico**

In coda a `tests/test_synth.py`:

```python
def test_il_telaio_sintetico_ha_i_prismi_che_gli_si_chiedono():
    """Verita' nota del banco: due prismi disgiunti danno una nuvola il cui
    ingombro e' l'unione dei due, e nessun punto fuori."""
    prismi = [
        ((0.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
        ((800.0, 0.0, 0.0), (200.0, 200.0, 1000.0)),
    ]
    punti = synth.sample_frame_surface(prismi, spacing=25.0)

    assert punti.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert punti.max(axis=0) == pytest.approx([1000.0, 200.0, 1000.0])
    # nessun punto nella campata vuota fra i due prismi
    assert not ((punti[:, 0] > 250.0) & (punti[:, 0] < 750.0)).any()
```

- [ ] **Step 3: Eseguirlo e vederlo fallire**

Run: `uv run pytest tests/test_synth.py -k telaio -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.synth' has no attribute 'sample_frame_surface'` — poi, dopo lo Step 1, PASS. Se hai gia' scritto lo Step 1, riesegui e attendi PASS.

- [ ] **Step 4: `_fix_sign` diventa pubblica**

In `src/meshrec/core/abaqus.py`, rinomina `_fix_sign` in `fix_sign` (definizione alla riga della `def`, piu' le due chiamate dentro `align_to_axes` e la citazione dentro la docstring di `build_node_sets`). Aggiungi alla docstring, in coda:

```
    Pubblica dalla Fase 4: `wall.terna` deve fissare il segno delle proprie
    direzioni con la stessa convenzione con cui `align_to_axes` fissa le sue,
    o due moduli dello stesso programma sceglierebbero versi opposti sulla
    stessa geometria.
```

Run: `uv run pytest tests/test_abaqus.py -q`
Expected: PASS (nessun test citava il nome privato: verificato con `grep -rn "_fix_sign" src tests` prima di rinominare — rifallo, e se compare in un test aggiornalo).

- [ ] **Step 5: I test della terna e delle celle**

Crea `tests/test_wall.py`:

```python
"""Il prior geometrico: terna del pezzo, celle, spessore locale, regioni.

Ogni verifica ha una geometria sintetica a verita' nota dietro: il numero di
membrature atteso viene dal banco di prova e mai dal codice, che deve poter
girare su una geometria che non ha mai visto.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import synth, wall
from meshrec.core.config import SegmentConfig, WallConfig

# Un telaio sintetico: due montanti, un traverso in alto, uno in basso. Sei
# numeri che stanno qui, nel banco, e in nessun file di src/.
TELAIO = [
    ((0.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),      # montante sinistro
    ((1400.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),   # montante destro
    ((0.0, 0.0, 1600.0), (1600.0, 200.0, 300.0)),   # traverso superiore
    ((0.0, 0.0, -300.0), (1600.0, 200.0, 300.0)),   # traverso inferiore
]
SPAZIATURA = 20.0


def _cfg() -> WallConfig:
    return WallConfig()


def test_la_terna_mette_la_direzione_trasversale_per_ultima():
    """Il telaio e' sottile in y: la terna deve riconoscerlo dal dato, non da
    un asse scelto a mano."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    direzioni, centro = wall.terna(punti)

    assert direzioni.shape == (3, 3)
    assert centro.shape == (3,)
    trasversale = direzioni[2]
    assert abs(abs(trasversale[1]) - 1.0) < 1e-6, f"trasversale attesa lungo y, e' {trasversale}"
    # terna ortonormale destrorsa: e' la condizione perche' u, v, n siano un
    # sistema di riferimento e non tre direzioni qualunque
    assert np.linalg.det(direzioni) == pytest.approx(1.0, abs=1e-9)


def test_la_terna_ha_lo_stesso_verso_su_due_esecuzioni_e_su_una_nuvola_rimescolata():
    """Il verso di una direzione principale e' arbitrario per la SVD: senza
    convenzione due esecuzioni sulla stessa nuvola darebbero assi opposti, e
    ogni indice derivato dalla terna dipenderebbe dall'ordine dei punti."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(0).permutation(len(punti))]

    prima, _ = wall.terna(punti)
    dopo, _ = wall.terna(rimescolati)
    assert prima == pytest.approx(dopo, abs=1e-9)


def test_le_celle_sono_indici_non_negativi_misurati_dal_minimo():
    piano = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 25.0], [-5.0, -5.0]])
    celle = wall.chiavi_di_cella(piano, lato=5.0)

    assert celle.dtype == np.int64
    assert (celle >= 0).all()
    assert celle.shape == (4, 2)
    # il minimo cade nella cella (0, 0); 10 mm a destra del minimo sono tre celle
    assert celle[3].tolist() == [0, 0]
    assert celle[0].tolist() == [1, 1]


def test_lo_spessore_locale_di_una_scatola_e_la_sua_dimensione_sottile():
    """La grandezza sorvegliata e' lo spessore, e su una scatola nota vale la
    dimensione sottile: se non lo fa, ogni regione trovata piu' avanti misura
    un'altra cosa."""
    punti = synth.sample_box_surface((400.0, 180.0, 900.0), SPAZIATURA)
    direzioni, centro = wall.terna(punti)
    centrati = punti - centro
    piano = centrati @ direzioni[:2].T
    trasversale = centrati @ direzioni[2]

    celle, spessori, _ = wall.spessore_per_cella(piano, trasversale, lato=4.0 * SPAZIATURA)

    assert len(celle) == len(spessori)
    # le celle interne alla faccia larga vedono le due facce a 180 mm di distanza
    assert np.median(spessori) == pytest.approx(180.0, abs=1.5 * SPAZIATURA)
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.core.wall'`.

- [ ] **Step 7: Scrivere la prima meta' di `core/wall.py`**

```python
"""Il prior geometrico: il pezzo e' un telaio di membrature prismatiche.

La spec di architettura chiamava questa fase «prior geometrico muro» e dava per
buono che il pezzo fosse una lastra piana. La premessa e' falsa sul caso studio,
e la falsita' e' stata misurata: il provino e' un telaio di membrature
prismatiche, ciascuna con la propria sezione costante lungo il proprio asse. Un
prior a due piani paralleli schiaccerebbe sezioni diverse in una.

Questo modulo **misura e non costruisce**: nessuna mesh, nessun file. Chi
costruisce e' `hexa.py`. Il confine non e' estetico: e' cio' che rende ciascuno
dei due verificabile da solo contro una geometria sintetica a verita' nota.

Nessun numero del provino di laboratorio vive qui dentro. Non il numero di
membrature, non le sezioni, non il volume, non una soglia di quota: la
scomposizione trova le membrature che ci sono, e su una scatola ne trova una.
"""

from __future__ import annotations

import numpy as np

from meshrec.core import segment
from meshrec.core.abaqus import fix_sign
from meshrec.core.config import SegmentConfig, WallConfig


def terna(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Terna del pezzo: due direzioni nel piano del telaio, la terza trasversale.

    La direzione trasversale e' quella di minore estensione, com'e' gia' in
    `segment._plane_metrics` e in `abaqus.align_to_axes`: un telaio e' sottile
    in una direzione sola, e quella e' la direzione lungo cui si misura lo
    spessore locale.

    Il verso di ciascuna direzione e' fissato da `abaqus.fix_sign`, e non e' un
    dettaglio: la SVD restituisce segni arbitrari, quindi senza convenzione due
    esecuzioni sulla stessa nuvola potrebbero dare assi opposti e ogni indice
    di cella derivato dalla terna dipenderebbe dall'ordine dei punti invece che
    dal dato.

    Restituisce la matrice 3x3 delle direzioni per riga -- u, v, n -- e il
    centro su cui e' stata stimata.
    """
    punti = np.asarray(points, dtype=np.float64)
    centro = punti.mean(axis=0)
    centrati = punti - centro
    _, _, principali = np.linalg.svd(centrati, full_matrices=False)
    estensioni = np.ptp(centrati @ principali.T, axis=0)

    trasversale = int(np.argmin(estensioni))
    restanti = [indice for indice in range(3) if indice != trasversale]
    # u e' la direzione di estensione maggiore fra le due restanti: e' l'asse
    # lungo del pezzo, e fissarlo dal dato invece che dall'ordine della SVD
    # rende la terna la stessa su due esecuzioni.
    restanti.sort(key=lambda indice: -estensioni[indice])

    n = fix_sign(principali[trasversale])
    u = fix_sign(principali[restanti[0]])
    # v come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori.
    v = np.cross(n, u)
    return np.stack([u, v, n]), centro


def chiavi_di_cella(coordinate: np.ndarray, lato: float) -> np.ndarray:
    """Indice intero di cella di ogni punto, su una griglia quadrata di lato dato.

    E' il «metodo delle colonne» di docs/fase-1-tolleranza-set.md: la stessa
    griglia con cui `abaqus.footprint_coverage` misura la copertura della
    superficie d'appoggio, e lo stesso lato `4 x spaziatura`, che li' e' stato
    scelto misurando il fallimento di `1 x spaziatura` e non a occhio.

    Quella funzione non viene toccata e questa non la sostituisce: rispondono a
    domande diverse -- copertura di un insieme di nodi sull'impronta
    orizzontale contro spessore locale sul piano del telaio -- e condividono
    quattro righe di aritmetica. `footprint_coverage` produce numeri citati
    nella tesi (100,00% su muro, 98,93% su lab_crop) e riscriverla per
    condividere quattro righe li metterebbe a rischio in cambio di nulla.

    Gli indici sono misurati dal minimo, quindi non negativi e funzione dei
    soli dati: nessun conteggio che ne discenda dipende dalla piattaforma.
    """
    piano = np.asarray(coordinate, dtype=np.float64)
    return np.floor((piano - piano.min(axis=0)) / float(lato)).astype(np.int64)


def spessore_per_cella(
    piano: np.ndarray, trasversale: np.ndarray, lato: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Spessore locale di ogni cella occupata: estensione della nuvola lungo n.

    E' la grandezza da sorvegliare, e la regola che ne discende e' la sua
    costanza, non il suo valore. Separare le membrature con una soglia di quota
    sarebbe tarare una costante sulla scansione di oggi, e una soglia difficile
    da tarare e' quasi sempre il sintomo di una grandezza sbagliata (secondo
    principio di prodotto).

    Restituisce le celle occupate (M x 2, ordinate per indice crescente), lo
    spessore di ciascuna, e per ogni punto la posizione della propria cella
    dentro quell'elenco.
    """
    celle = chiavi_di_cella(piano, lato)
    # Chiave intera invece di np.unique(..., axis=0): stesso risultato, e su un
    # maglio a scala reale costa un terzo. Stessa scelta gia' fatta in
    # abaqus.footprint_coverage, e per la stessa ragione.
    chiave = celle[:, 0] * (celle[:, 1].max() + 1) + celle[:, 1]
    _, prima, inverso = np.unique(chiave, return_index=True, return_inverse=True)
    uniche = celle[prima]

    valori = np.asarray(trasversale, dtype=np.float64)
    alto = np.full(len(uniche), -np.inf)
    basso = np.full(len(uniche), np.inf)
    np.maximum.at(alto, inverso, valori)
    np.minimum.at(basso, inverso, valori)
    return uniche, alto - basso, inverso
```

- [ ] **Step 8: Eseguire i test della prima meta'**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti e quattro.

- [ ] **Step 9: Commit intermedio**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/src/meshrec/core/synth.py meshrec/src/meshrec/core/abaqus.py meshrec/tests/test_wall.py meshrec/tests/test_synth.py
git commit -m "feat(fase-4): terna del pezzo, celle e spessore locale del prior"
```

- [ ] **Step 10: I test del pavimento e delle regioni**

In coda a `tests/test_wall.py`:

```python
def test_il_pavimento_viene_scartato_come_piano_e_non_come_quota():
    """Il pavimento e' un piano quasi orizzontale esteso oltre l'ingombro del
    pezzo. Scartarlo con una soglia di quota sarebbe tarare una costante sulla
    scansione di oggi; qui viene scartato per cio' che e'."""
    telaio = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    pavimento = synth.sample_box_surface((4000.0, 3000.0, 10.0), SPAZIATURA * 2.0)
    pavimento = pavimento + np.array([-1200.0, -1400.0, -320.0])
    punti = np.vstack([telaio, pavimento])

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is True
    assert len(tenuti) < len(punti)
    # nessun punto sotto il piede del telaio sintetico resta in circolazione
    assert tenuti[:, 2].min() > -320.0
    assert tenuti[:, 2].min() == pytest.approx(-300.0, abs=3.0 * SPAZIATURA)


def test_senza_pavimento_non_ne_viene_inventato_uno():
    """Il controllo che smentisce il precedente: su una nuvola che pavimento
    non ha, la funzione non deve togliere una faccia del pezzo scambiandola per
    tale."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is False
    assert len(tenuti) == len(punti)


def test_una_scatola_da_una_sola_membratura():
    """La prova che la scomposizione non inventa membrature dove non ce ne
    sono. Il numero atteso viene dal banco, non dal codice."""
    punti = synth.sample_box_surface((400.0, 180.0, 1200.0), SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(regioni) == 1
    assert metriche["regioni_trovate"] == 1


def test_un_telaio_sintetico_da_le_membrature_che_ha():
    """Quattro prismi di tre sezioni diverse: la scomposizione deve separarli
    per costanza dello spessore, e i due montanti identici, che sono disgiunti
    nel piano, restano due regioni e non una."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["regioni_trovate"] == len(regioni)
    assert 2 <= len(regioni) <= 6, (
        f"attese fra 2 e 6 regioni sui quattro prismi del banco, trovate {len(regioni)}: "
        "sotto, la scomposizione fonde membrature diverse; sopra, le frammenta"
    )
    # ogni punto sta in al piu' una regione: una regione non ruba punti a un'altra
    tutti = np.concatenate(regioni)
    assert len(tutti) == len(np.unique(tutti))


def test_l_ordine_delle_regioni_non_dipende_dall_ordine_dei_punti():
    """Quinto vincolo di prodotto: un ordine e' un esito discreto e deve essere
    funzione del dato. E' la stessa lezione gia' pagata sull'ordine dei voxel di
    Open3D fra Windows x86-64 e macOS arm64."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(1).permutation(len(punti))]

    prima, _ = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)
    dopo, _ = wall.scomponi(rimescolati, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(prima) == len(dopo)
    # confronto per insieme di coordinate, non per indice: gli indici puntano a
    # due ordinamenti diversi della stessa nuvola
    for regione_prima, regione_dopo in zip(prima, dopo, strict=True):
        a = np.unique(np.round(punti[regione_prima], 6), axis=0)
        b = np.unique(np.round(rimescolati[regione_dopo], 6), axis=0)
        assert a.shape == b.shape
        assert a == pytest.approx(b)
```

- [ ] **Step 11: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'scarta_pavimento'` sui cinque nuovi, PASS sui quattro precedenti.

- [ ] **Step 12: Scrivere la seconda meta' di `core/wall.py`**

In coda a `wall.py`:

```python
def scarta_pavimento(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> tuple[np.ndarray, dict[str, object]]:
    """Toglie il pavimento, se c'e'. Non e' una membratura ed e' scartato come piano.

    Il pavimento e' riconosciuto da due condizioni che valgono insieme e non da
    una soglia di quota: la normale del piano sta entro `floor_angle_deg`
    dalla verticale, e il piano contiene almeno `floor_min_ratio` dei punti.
    Una faccia superiore di membratura soddisfa la prima e non la seconda.

    L'estrazione dei piani non viene riscritta: e' `segment.extract_planes`,
    con la stessa configurazione con cui lo step 2 la usa gia'.

    Se nessun piano soddisfa entrambe le condizioni la nuvola torna intatta e
    le metriche lo dichiarano: non viene inventato un pavimento, per lo stesso
    motivo per cui non viene inventata un'aspettativa quando non e' dichiarata.
    """
    punti = np.asarray(points, dtype=np.float64)
    piani, _residuo, metriche_piani = segment.extract_planes(punti, cfg_segment, spacing)
    coseno = np.cos(np.radians(cfg.floor_angle_deg))
    minimo = cfg.floor_min_ratio * len(punti)

    for piano in piani:
        if len(piano) < minimo:
            continue
        centrati = piano - piano.mean(axis=0)
        _, _, principali = np.linalg.svd(centrati, full_matrices=False)
        if abs(principali[2][2]) < coseno:
            continue
        # Il pavimento e' questo: si toglie per appartenenza, confrontando le
        # coordinate arrotondate. Un confronto per indice non e' disponibile,
        # perche' extract_planes restituisce i punti e non le loro posizioni.
        chiave_piano = {tuple(riga) for riga in np.round(piano, 6).tolist()}
        tenuti = np.array(
            [tuple(riga) not in chiave_piano for riga in np.round(punti, 6).tolist()],
            dtype=bool,
        )
        return np.ascontiguousarray(punti[tenuti]), {
            "pavimento_trovato": True,
            "pavimento_punti": int(len(piano)),
            "punti_dopo": int(tenuti.sum()),
            **metriche_piani,
        }

    return punti, {
        "pavimento_trovato": False,
        "pavimento_punti": 0,
        "punti_dopo": int(len(punti)),
        **metriche_piani,
    }


def regioni(celle: np.ndarray, spessori: np.ndarray, cfg: WallConfig) -> list[np.ndarray]:
    """Regioni connesse a spessore quasi costante, sulla griglia delle celle.

    Due celle adiacenti sui quattro lati appartengono alla stessa membratura se
    i loro spessori differiscono di meno di `thickness_tolerance` in relativo.
    E' la forma numerica di «quasi costante», ed e' l'unica soglia della
    scomposizione: non c'e' un istogramma da leggere ne' un numero di modi da
    dichiarare, quindi non c'e' un numero di membrature da aspettarsi.

    Le componenti connesse vengono da scipy.sparse.csgraph, gia' installata:
    non c'e' motivo di scrivere una union-find a mano.

    L'ordine delle regioni e' canonico -- per numero di celle decrescente, a
    pari numero per la cella di indice minimo -- quindi funzione del dato e non
    dell'ordine di visita: e' il quinto vincolo di prodotto.
    """
    from scipy.sparse import coo_array
    from scipy.sparse.csgraph import connected_components

    griglia = np.asarray(celle, dtype=np.int64)
    valori = np.asarray(spessori, dtype=np.float64)
    passo = int(griglia[:, 1].max() + 1)
    chiave = griglia[:, 0] * passo + griglia[:, 1]
    ordine = np.argsort(chiave, kind="stable")
    ordinate = chiave[ordine]

    archi_a: list[np.ndarray] = []
    archi_b: list[np.ndarray] = []
    for salto in (passo, 1):  # vicino lungo il primo asse, vicino lungo il secondo
        posizione = np.searchsorted(ordinate, chiave + salto)
        posizione = np.clip(posizione, 0, len(ordinate) - 1)
        vicino = ordine[posizione]
        esiste = ordinate[posizione] == chiave + salto
        if salto == 1:
            # il vicino lungo il secondo asse esiste solo se non ha scavalcato
            # la riga: due celle contigue nella chiave possono stare su righe
            # diverse della griglia
            esiste &= griglia[vicino, 0] == griglia[:, 0]
        vicini_validi = np.flatnonzero(esiste)
        if len(vicini_validi) == 0:
            continue
        altro = vicino[vicini_validi]
        massimo = np.maximum(valori[vicini_validi], valori[altro])
        simili = np.abs(valori[vicini_validi] - valori[altro]) <= cfg.thickness_tolerance * massimo
        archi_a.append(vicini_validi[simili])
        archi_b.append(altro[simili])

    da = np.concatenate(archi_a) if archi_a else np.empty(0, dtype=np.int64)
    a = np.concatenate(archi_b) if archi_b else np.empty(0, dtype=np.int64)
    grafo = coo_array(
        (np.ones(len(da), dtype=np.int8), (da, a)), shape=(len(griglia), len(griglia))
    )
    _quante, etichette = connected_components(grafo, directed=False)

    gruppi = []
    for etichetta in np.unique(etichette):
        indici = np.flatnonzero(etichette == etichetta)
        if len(indici) < cfg.min_cells:
            continue
        gruppi.append(indici)
    # ordine canonico: le regioni grandi per prime, i pari merito per la cella
    # di indice minimo, che e' un numero della griglia e non dell'esecuzione
    gruppi.sort(key=lambda indici: (-len(indici), int(chiave[indici].min())))
    return gruppi


def scomponi(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> tuple[list[np.ndarray], dict[str, object]]:
    """La scomposizione completa: dal pavimento scartato agli indici dei punti per regione.

    Il numero di membrature non e' un parametro e non e' un'attesa: e' cio' che
    la nuvola contiene. Su una scatola torna una regione sola.
    """
    puliti, metriche_pavimento = scarta_pavimento(points, cfg_segment, cfg, spacing)
    if len(puliti) == 0:
        raise ValueError(
            "la rimozione del pavimento ha svuotato la nuvola: il piano scartato "
            "conteneva tutti i punti, quindi non era un pavimento ma il pezzo. "
            "Alza wall.floor_min_ratio o restringi wall.floor_angle_deg"
        )

    direzioni, centro = terna(puliti)
    centrati = puliti - centro
    piano = centrati @ direzioni[:2].T
    trasversale = centrati @ direzioni[2]
    lato = cfg.cell_factor * spacing

    celle, spessori, inverso = spessore_per_cella(piano, trasversale, lato)
    gruppi = regioni(celle, spessori, cfg)

    per_regione = []
    for indici_cella in gruppi:
        appartiene = np.isin(inverso, indici_cella)
        per_regione.append(np.flatnonzero(appartiene))

    metriche: dict[str, object] = {
        **metriche_pavimento,
        "cell_side": float(lato),
        "celle_occupate": int(len(celle)),
        "regioni_trovate": len(per_regione),
        "punti_per_regione": [int(len(indici)) for indici in per_regione],
        "spessore_mediano": float(np.median(spessori)) if len(spessori) else None,
        "terna": direzioni.tolist(),
        "centro": centro.tolist(),
    }
    return per_regione, metriche
```

**Attenzione all'appartenenza dei punti:** `scomponi` restituisce gli indici dentro `puliti`, non dentro `points`. Se il pavimento e' stato tolto i due non coincidono. Il chiamante che serve (`pipeline`, Task 9) usa la nuvola ripulita e non l'originale; restituiscila quindi anche tu, aggiungendo `puliti` come terzo elemento del ritorno **solo se** un test lo richiede — per ora la nuvola ripulita e' ricostruibile da `scarta_pavimento`, che e' pubblica.

- [ ] **Step 13: Eseguire i test delle regioni**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti e nove. Se `test_un_telaio_sintetico_da_le_membrature_che_ha` cade fuori dall'intervallo 2-6, **non allargare l'intervallo**: stampa `metriche["punti_per_regione"]` e guarda se la scomposizione fonde o frammenta, poi correggi `regioni` o dichiara la limitazione nel documento del Task 13.

- [ ] **Step 14: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 15: Commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): la scomposizione in membrature per costanza dello spessore"
```

---

