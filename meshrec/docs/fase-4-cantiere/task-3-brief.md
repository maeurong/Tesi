## Task 3: `core/wall.py` — le misure per membratura, i controlli intrinseci, i riscontri dichiarati

**Files:**
- Modify: `src/meshrec/core/wall.py`
- Test: `tests/test_wall.py`

**Interfaces:**
- Consumes: `wall.scomponi`, `wall.terna` (Task 2).
- Produces:
  - `wall.Membratura` — dataclass con `punti, asse, origine, lunghezza, sezione, sezione_dispersione, contorno, fuori_piombo_deg, asse_ideale, scarto_asse_deg, rigonfiamento, volume, esiti`.
  - `wall.semplifica_contorno(contorno, tolleranza) -> np.ndarray`.
  - `wall.misura(punti_regione, direzioni, cfg) -> Membratura`.
  - `wall.controlla(membratura, cfg) -> dict[str, dict]`.
  - `wall.prior(points, cfg_segment, cfg, spacing) -> dict[str, object]` — il risultato completo dello step 12, serializzabile in JSON.

- [ ] **Step 1: I test del contorno di sezione**

In coda a `tests/test_wall.py`:

```python
def test_il_contorno_di_un_rettangolo_ha_quattro_vertici():
    """Il contorno misurato non deve portare nella mesh il rumore dello
    scanner: un rettangolo campionato fitto resta un rettangolo."""
    lato_u = np.linspace(0.0, 200.0, 60)
    lato_v = np.linspace(0.0, 140.0, 40)
    bordo = np.vstack([
        np.column_stack([lato_u, np.zeros_like(lato_u)]),
        np.column_stack([lato_u, np.full_like(lato_u, 140.0)]),
        np.column_stack([np.zeros_like(lato_v), lato_v]),
        np.column_stack([np.full_like(lato_v, 200.0), lato_v]),
    ])

    contorno = wall.semplifica_contorno(bordo, tolleranza=5.0)

    assert len(contorno) == 4, f"attesi 4 vertici, trovati {len(contorno)}"
    assert contorno.min(axis=0) == pytest.approx([0.0, 0.0], abs=1e-9)
    assert contorno.max(axis=0) == pytest.approx([200.0, 140.0], abs=1e-9)


def test_il_contorno_semplificato_non_perde_area_oltre_la_tolleranza():
    """Il controllo che smentisce il precedente: semplificare e' lecito finche'
    l'area della sezione non cambia piu' di quanto la tolleranza consenta."""
    angoli = np.linspace(0.0, 2.0 * np.pi, 400, endpoint=False)
    cerchio = np.column_stack([100.0 * np.cos(angoli), 100.0 * np.sin(angoli)])

    contorno = wall.semplifica_contorno(cerchio, tolleranza=2.0)

    def area(poligono):
        x, y = poligono[:, 0], poligono[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    assert len(contorno) < len(cerchio)
    assert area(contorno) == pytest.approx(area(cerchio), rel=0.05)
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k contorno -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'semplifica_contorno'`.

- [ ] **Step 3: Scrivere `semplifica_contorno`**

In coda a `wall.py`:

```python
def semplifica_contorno(contorno: np.ndarray, tolleranza: float) -> np.ndarray:
    """Inviluppo convesso della sezione, ridotto ai vertici che contano.

    Il contorno di sezione va misurato sulla nuvola e non preso dal disegno,
    ma un contorno con un vertice per punto rilevato porterebbe nella mesh il
    rumore dello scanner invece della forma della sezione. La riduzione toglie
    a ripetizione il vertice la cui distanza dal segmento fra i due vicini e'
    la piu' piccola, finche' tutte le distanze superano la tolleranza: e' la
    stessa idea di Douglas-Peucker su un poligono chiuso, senza ricorsione.

    L'inviluppo convesso e' di scipy, gia' installata. La convessita' non e'
    una perdita: la sezione di una membratura prismatica e' convessa, e una
    concavita' misurata sarebbe piu' probabilmente un'occlusione dello scanner
    che una rientranza del calcestruzzo. E' anche cio' che rende immediato il
    test di appartenenza usato dal taglio alle giunzioni.

    I pari merito sono sciolti dall'indice, che e' un numero della geometria e
    non dell'esecuzione: l'esito e' funzione del dato.
    """
    from scipy.spatial import ConvexHull

    punti = np.asarray(contorno, dtype=np.float64)
    inviluppo = punti[ConvexHull(punti).vertices]

    while len(inviluppo) > 3:
        precedente = np.roll(inviluppo, 1, axis=0)
        successivo = np.roll(inviluppo, -1, axis=0)
        corda = successivo - precedente
        lunghezza = np.linalg.norm(corda, axis=1)
        # distanza punto-retta come modulo del prodotto vettoriale in 2D,
        # normalizzato sulla corda; corda nulla vuol dire vertice doppio, che
        # va tolto per primo
        scarto = np.abs(np.cross(corda, inviluppo - precedente))
        altezza = np.divide(
            scarto, lunghezza, out=np.zeros_like(scarto), where=lunghezza > 0.0
        )
        peggiore = int(np.argmin(altezza))
        if altezza[peggiore] > tolleranza:
            break
        inviluppo = np.delete(inviluppo, peggiore, axis=0)

    return np.ascontiguousarray(inviluppo)
```

- [ ] **Step 4: Eseguirli**

Run: `uv run pytest tests/test_wall.py -k contorno -v`
Expected: PASS.

- [ ] **Step 5: I test delle misure per membratura**

In coda a `tests/test_wall.py`:

```python
def test_la_misura_di_un_prisma_noto_ritrova_sezione_asse_e_lunghezza():
    """Verita' nota del banco: un prisma 200 x 140 lungo 1500 lungo z."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.lunghezza == pytest.approx(1500.0, abs=30.0)
    lunga, corta = sorted(membratura.sezione, reverse=True)
    assert lunga == pytest.approx(200.0, abs=15.0)
    assert corta == pytest.approx(140.0, abs=15.0)
    assert abs(abs(membratura.asse[2]) - 1.0) < 1e-3, "asse atteso verticale"
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.0)
    assert membratura.volume == pytest.approx(200.0 * 140.0 * 1500.0, rel=0.15)


def test_il_fuori_piombo_misura_l_inclinazione_e_il_rigonfiamento_no():
    """Le due grandezze restano distinte perche' sono difetti diversi: un
    elemento puo' essere perfettamente piano e tutto storto, oppure a piombo e
    panciuto. Un prisma inclinato di 4 gradi ha fuori piombo e non pancia."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    angolo = np.radians(4.0)
    rotazione = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(angolo), -np.sin(angolo)],
        [0.0, np.sin(angolo), np.cos(angolo)],
    ])
    inclinati = punti @ rotazione.T
    direzioni, _ = wall.terna(inclinati)

    membratura = wall.misura(inclinati, direzioni, _cfg())

    assert membratura.fuori_piombo_deg == pytest.approx(4.0, abs=1.0)
    assert np.abs(membratura.rigonfiamento).max() < 20.0, (
        "un prisma inclinato ma dritto non deve risultare panciuto: se lo "
        "risulta, il rigonfiamento sta misurando l'inclinazione"
    )


def test_il_rigonfiamento_e_una_mappa_e_trova_la_pancia_dove_c_e():
    """Il controllo che smentisce il precedente: una faccia gonfiata di 25 mm
    al centro deve comparire nella mappa, e nel fuori piombo no."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    sulla_faccia = np.isclose(punti[:, 1], 140.0)
    altezza_relativa = (punti[:, 2] - 750.0) / 750.0
    gonfiati = punti.copy()
    gonfiati[sulla_faccia, 1] += 25.0 * (1.0 - altezza_relativa[sulla_faccia] ** 2)
    direzioni, _ = wall.terna(gonfiati)

    membratura = wall.misura(gonfiati, direzioni, _cfg())

    assert membratura.rigonfiamento.ndim == 1
    assert len(membratura.rigonfiamento) > 10, "il rigonfiamento e' una mappa, non un numero"
    assert np.abs(membratura.rigonfiamento).max() > 10.0
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.5)
```

- [ ] **Step 6: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k misura -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'misura'`.

- [ ] **Step 7: `Membratura` e `misura`**

In `wall.py`, subito sotto gli import aggiungi `from dataclasses import dataclass, field`, e in coda al file:

```python
@dataclass(eq=False)
class Membratura:
    """Una membratura prismatica misurata. Nessun campo viene da un disegno.

    `eq=False` perche' i campi sono array: il confronto per uguaglianza di un
    dataclass con dentro numpy solleverebbe invece di rispondere, e non serve
    a nessuno qui.
    """

    punti: np.ndarray
    """Indici, dentro la nuvola passata a `misura`, dei punti della regione."""
    asse: np.ndarray
    """Direzione principale della regione, versore, con verso fissato da fix_sign."""
    origine: np.ndarray
    """Punto sull'asse da cui la lunghezza e' misurata."""
    lunghezza: float
    sezione: tuple[float, float]
    """Le due estensioni trasversali all'asse [mm]."""
    sezione_dispersione: tuple[float, float]
    """Dispersione delle due estensioni lungo l'asse, in relativo."""
    contorno: np.ndarray
    """Contorno di sezione misurato e semplificato, K x 2, nel piano dell'asse."""
    fuori_piombo_deg: float
    """Angolo dell'asse rispetto alla verticale. Un numero solo."""
    asse_ideale: np.ndarray
    """Il versore della terna piu' vicino all'asse: e' l'asse del modello primitive."""
    scarto_asse_deg: float
    """Angolo fra l'asse misurato e l'asse ideale."""
    rigonfiamento: np.ndarray
    """Scostamento locale dalla faccia ideale, una mappa per cella e non un numero."""
    volume: float
    """Sezione media per lunghezza [mm^3]."""
    esiti: dict[str, dict] = field(default_factory=dict)
    """Gli esiti dei controlli intrinseci, riempiti da `controlla`."""


_FETTE_LUNGO_ASSE = 20
"""Fette in cui la regione e' divisa per misurare la dispersione della sezione.

Non e' un parametro di elaborazione: e' la risoluzione con cui si guarda una
grandezza gia' definita, come i bin di un istogramma. Venti fette danno almeno
una decina di punti per fetta su qualunque membratura che superi min_cells.
"""


def misura(punti_regione: np.ndarray, direzioni: np.ndarray, cfg: WallConfig) -> Membratura:
    """Asse, lunghezza, sezione, contorno, fuori piombo e rigonfiamento di una regione.

    Il fuori piombo e il rigonfiamento sono tenuti distinti perche' sono
    difetti diversi: un elemento puo' essere perfettamente piano e tutto
    storto, oppure a piombo e panciuto. Il primo e' un numero, il secondo e'
    una mappa, e sommarli darebbe un indice che non corrisponde a nulla di
    fisico.

    `direzioni` e' la terna del pezzo intero, non della regione: le due
    grandezze «asse ideale» e «rigonfiamento» hanno senso solo rispetto a un
    riferimento comune a tutte le membrature.
    """
    punti = np.asarray(punti_regione, dtype=np.float64)
    centro = punti.mean(axis=0)
    centrati = punti - centro
    _, _, principali = np.linalg.svd(centrati, full_matrices=False)
    asse = fix_sign(principali[0])

    lungo = centrati @ asse
    lunghezza = float(np.ptp(lungo))
    origine = centro + asse * lungo.min()

    # base ortonormale del piano di sezione, ancorata alla terna del pezzo e non
    # alla SVD della regione: due membrature parallele devono avere lo stesso
    # piano di sezione, o le loro sezioni non sono confrontabili
    riferimento = direzioni[2] if abs(np.dot(direzioni[2], asse)) < 0.9 else direzioni[0]
    e1 = riferimento - asse * np.dot(riferimento, asse)
    e1 = fix_sign(e1 / np.linalg.norm(e1))
    e2 = np.cross(asse, e1)
    sezione_2d = np.column_stack([centrati @ e1, centrati @ e2])

    estensioni = (float(np.ptp(sezione_2d[:, 0])), float(np.ptp(sezione_2d[:, 1])))

    # dispersione della sezione lungo l'asse: la grandezza del controllo di
    # costanza. Fette a passo uguale, e non quantili, perche' una fetta vuota
    # deve restare vuota invece di essere riempita da punti di un'altra.
    bordi = np.linspace(lungo.min(), lungo.max(), _FETTE_LUNGO_ASSE + 1)
    fetta = np.clip(np.digitize(lungo, bordi[1:-1]), 0, _FETTE_LUNGO_ASSE - 1)
    per_fetta = []
    for indice in range(_FETTE_LUNGO_ASSE):
        dentro = fetta == indice
        if dentro.sum() < 4:
            continue
        per_fetta.append((np.ptp(sezione_2d[dentro, 0]), np.ptp(sezione_2d[dentro, 1])))
    misure = np.asarray(per_fetta, dtype=np.float64) if per_fetta else np.zeros((1, 2))
    medie = misure.mean(axis=0)
    dispersione = tuple(
        float(scarto / media) if media > 0.0 else 0.0
        for scarto, media in zip(misure.std(axis=0), medie, strict=True)
    )

    contorno = semplifica_contorno(sezione_2d, cfg.contour_tolerance)

    # fuori piombo: angolo dell'asse rispetto alla verticale del mondo. Per una
    # colonna e' il fuori piombo nel senso del cantiere; per una trave e' 90
    # gradi e non e' un difetto, ed e' per questo che accanto c'e' lo scarto
    # dall'asse ideale, che e' la grandezza che il modello primitive raddrizza.
    verticale = np.array([0.0, 0.0, 1.0])
    fuori_piombo = float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(asse, verticale)))))))

    proiezioni = np.abs(direzioni @ asse)
    asse_ideale = fix_sign(direzioni[int(np.argmax(proiezioni))])
    scarto_asse = float(np.degrees(np.arccos(min(1.0, float(np.max(proiezioni))))))

    # rigonfiamento: scostamento della faccia dalla propria faccia ideale, che
    # e' il piano medio della faccia stessa. Una mappa per cella della griglia
    # di sezione, non un numero.
    lato = cfg.cell_factor * max(1e-9, float(np.ptp(lungo)) / _FETTE_LUNGO_ASSE)
    piano_faccia = np.column_stack([lungo, sezione_2d[:, 0]])
    celle_faccia = chiavi_di_cella(piano_faccia, lato)
    chiave = celle_faccia[:, 0] * (celle_faccia[:, 1].max() + 1) + celle_faccia[:, 1]
    _, inverso = np.unique(chiave, return_inverse=True)
    quota = sezione_2d[:, 1]
    estremo = np.full(int(inverso.max()) + 1, -np.inf)
    np.maximum.at(estremo, inverso, quota)
    rigonfiamento = estremo - np.median(estremo)

    volume = float(medie[0] * medie[1] * lunghezza)

    return Membratura(
        punti=np.arange(len(punti)),
        asse=asse,
        origine=origine,
        lunghezza=lunghezza,
        sezione=estensioni,
        sezione_dispersione=dispersione,
        contorno=contorno,
        fuori_piombo_deg=fuori_piombo,
        asse_ideale=asse_ideale,
        scarto_asse_deg=scarto_asse,
        rigonfiamento=rigonfiamento,
        volume=volume,
    )
```

- [ ] **Step 8: Eseguire i test delle misure**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti.

- [ ] **Step 9: Commit intermedio**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): sezione, asse, fuori piombo e rigonfiamento per membratura"
```

- [ ] **Step 10: I test dei controlli intrinseci**

In coda a `tests/test_wall.py`:

```python
def test_i_quattro_controlli_intrinseci_passano_su_un_prisma_pulito():
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)
    membratura = wall.misura(punti, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert set(esiti) == {"parallelismo", "copertura_faccia", "costanza_sezione"}
    for nome, esito in esiti.items():
        assert esito["passato"] is True, f"{nome} non doveva fallire: {esito}"
        assert "valore" in esito and "soglia" in esito, (
            f"{nome} deve dire quale numero lo ha deciso, non solo se e' passato"
        )


def test_una_regione_a_sezione_variabile_non_e_un_prisma_e_lo_dice():
    """Il controllo che smentisce il prior: un tronco di piramide non e' una
    membratura, e viene riportato come tale invece di essere spacciato per una
    con la sezione media."""
    z = np.linspace(0.0, 1500.0, 120)
    punti = []
    for quota in z:
        mezzo_lato = 100.0 * (1.0 - 0.6 * quota / 1500.0)
        angoli = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        punti.append(np.column_stack([
            mezzo_lato * np.cos(angoli),
            mezzo_lato * np.sin(angoli),
            np.full_like(angoli, quota),
        ]))
    cono = np.vstack(punti)
    direzioni, _ = wall.terna(cono)
    membratura = wall.misura(cono, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert esiti["costanza_sezione"]["passato"] is False
    assert esiti["costanza_sezione"]["valore"] > esiti["costanza_sezione"]["soglia"]


def test_senza_riscontri_dichiarati_il_prior_non_inventa_un_aspettativa():
    """Su un pezzo nuovo i riscontri non esistono per definizione. Il prior
    riporta cio' che ha trovato, e nel posto dell'atteso non mette un numero."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] is None
    assert riscontri["volume_atteso"] is None
    assert riscontri["scarto_membrature"] is None
    assert riscontri["scarto_volume"] is None
    assert esito["membrature"], "il prior deve comunque riportare cio' che ha trovato"


def test_con_i_riscontri_dichiarati_il_prior_riporta_lo_scarto():
    """I numeri dell'atteso stanno qui, nel test, dove e' legittimo che
    compaiano: sono dati del caso, non del programma."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    volume_vero = sum(dx * dy * dz for _origine, (dx, dy, dz) in TELAIO)
    cfg = WallConfig(membrature_attese=4, volume_atteso=volume_vero)

    esito = wall.prior(punti, SegmentConfig(), cfg, SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] == 4
    assert riscontri["scarto_membrature"] == len(esito["membrature"]) - 4
    assert riscontri["volume_atteso"] == pytest.approx(volume_vero)
    assert riscontri["scarto_volume"] is not None


def test_l_esito_del_prior_e_serializzabile_in_json():
    """Lo step 12 lo scrive su disco e il server lo manda al browser: un array
    di numpy dentro il dizionario romperebbe entrambi dopo l'intera corsa."""
    import json

    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    testo = json.dumps(esito)
    assert json.loads(testo)["regioni_trovate"] == esito["regioni_trovate"]


def test_il_controllo_di_chiusura_del_volume_confronta_somma_e_unione():
    """Le membrature si compenetrano alle giunzioni: se la somma dei volumi
    supera quello dell'unione oltre la tolleranza, c'e' doppio conteggio, ed e'
    un errore che nessuna metrica di qualita' della mesh vedrebbe."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    chiusura = esito["chiusura_volume"]
    assert chiusura["somma"] > 0.0
    assert chiusura["unione"] > 0.0
    assert isinstance(chiusura["passato"], bool)
    assert chiusura["scarto_relativo"] == pytest.approx(
        (chiusura["somma"] - chiusura["unione"]) / chiusura["unione"]
    )
```

- [ ] **Step 11: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_wall.py -k "controll or riscontr or prior or chiusura" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.wall' has no attribute 'controlla'`.

- [ ] **Step 12: `controlla` e `prior`**

In coda a `wall.py`:

```python
def controlla(membratura: Membratura, cfg: WallConfig) -> dict[str, dict]:
    """I controlli intrinseci di una membratura: sempre attivi, nulla sanno del pezzo.

    Senza questi il prior e' una macchina per fabbricare numeri. Ogni esito
    porta con se' il numero che lo ha deciso e la soglia con cui e' stato
    confrontato: un «non passato» senza il proprio numero non dice a chi legge
    che cosa cambiare.

    Un controllo fallito **non solleva**. La regione non diventa una membratura
    e il motivo resta scritto, perche' l'interfaccia deve poter mostrare quale
    controllo ha detto no e quale numero glielo ha fatto dire: un'eccezione
    ucciderebbe la corsa sulla prima regione difettosa e non lascerebbe nulla
    da mostrare sulle altre.
    """
    # parallelismo delle facce: la mappa del rigonfiamento e' lo scostamento
    # della faccia dal proprio piano medio, quindi l'angolo fra le due facce si
    # legge dal gradiente di quella mappa lungo l'asse. Un valore grande
    # significa facce che divergono, cioe' nessuna sezione da misurare.
    pancia = np.asarray(membratura.rigonfiamento, dtype=np.float64)
    divergenza = float(np.ptp(pancia)) if len(pancia) else 0.0
    riferimento = max(membratura.lunghezza, 1e-9)
    angolo_facce = float(np.degrees(np.arctan2(divergenza, riferimento)))

    coperte = float(np.isfinite(pancia).mean()) if len(pancia) else 0.0
    dispersione = float(max(membratura.sezione_dispersione))

    return {
        "parallelismo": {
            "passato": angolo_facce <= cfg.parallelism_deg,
            "valore": angolo_facce,
            "soglia": float(cfg.parallelism_deg),
            "unita": "gradi",
            "spiegazione": (
                "angolo fra le due facce opposte: oltre la soglia la regione non "
                "ha una sezione, e una sezione media sarebbe priva di senso"
            ),
        },
        "copertura_faccia": {
            "passato": coperte >= cfg.face_coverage,
            "valore": coperte,
            "soglia": float(cfg.face_coverage),
            "unita": "frazione",
            "spiegazione": (
                "frazione delle celle della faccia viste dallo scanner: una "
                "faccia vista da pochi punti produce un piano finto, come gia' "
                "misurato su FACE_FRONT e FACE_BACK"
            ),
        },
        "costanza_sezione": {
            "passato": dispersione <= cfg.section_dispersion,
            "valore": dispersione,
            "soglia": float(cfg.section_dispersion),
            "unita": "frazione",
            "spiegazione": (
                "dispersione relativa della sezione lungo l'asse: oltre la "
                "soglia la regione non e' un prisma"
            ),
        },
    }


def _volume_unione(membrature: list[Membratura], punti: np.ndarray, passo: float) -> float:
    """Volume dell'unione delle membrature, per conteggio di celle occupate.

    Nessuna libreria di solidi entra nel progetto per una misura di controllo:
    una griglia regolare sull'ingombro, una cella contata una volta sola se
    contiene punti di una qualunque membratura. L'errore e' quello della
    discretizzazione, viene dal passo dichiarato e viene riportato accanto al
    risultato invece di essere nascosto.
    """
    if not membrature:
        return 0.0
    tutti = np.vstack([punti[m.punti] for m in membrature])
    celle = np.floor((tutti - tutti.min(axis=0)) / passo).astype(np.int64)
    occupate = len(np.unique(celle, axis=0))
    return float(occupate * passo**3)


def prior(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> dict[str, object]:
    """Lo step 12 per intero: scomposizione, misure, controlli, riscontri.

    Il risultato e' un dizionario di soli tipi JSON, perche' viene scritto su
    disco e mandato al browser: un array di numpy dentro romperebbe entrambi
    dopo che l'intera corsa e' gia' costata il suo tempo.

    I riscontri dichiarati sono facoltativi e assenti per definizione su un
    pezzo nuovo. Quando mancano, al posto dell'atteso c'e' `null` e non un
    numero: il prior non inventa un'aspettativa.
    """
    puliti, metriche_pavimento = scarta_pavimento(points, cfg_segment, cfg, spacing)
    regioni_punti, metriche = scomponi(points, cfg_segment, cfg, spacing)
    direzioni, _centro = terna(puliti)

    accettate: list[Membratura] = []
    scartate: list[dict[str, object]] = []
    for numero, indici in enumerate(regioni_punti):
        membratura = misura(puliti[indici], direzioni, cfg)
        membratura.punti = indici
        membratura.esiti = controlla(membratura, cfg)
        falliti = [nome for nome, esito in membratura.esiti.items() if not esito["passato"]]
        if falliti:
            scartate.append({
                "regione": numero,
                "punti": int(len(indici)),
                "controlli_falliti": falliti,
                "esiti": membratura.esiti,
            })
            continue
        accettate.append(membratura)

    passo_unione = cfg.union_step_factor * spacing
    somma = float(sum(m.volume for m in accettate))
    unione = _volume_unione(accettate, puliti, passo_unione)
    scarto_relativo = (somma - unione) / unione if unione > 0.0 else 0.0

    scarto_membrature = (
        len(accettate) - cfg.membrature_attese if cfg.membrature_attese is not None else None
    )
    scarto_volume = (
        (somma - cfg.volume_atteso) / cfg.volume_atteso
        if cfg.volume_atteso is not None
        else None
    )

    return {
        **{chiave: valore for chiave, valore in metriche.items() if chiave != "terna"},
        **metriche_pavimento,
        "terna": direzioni.tolist(),
        "membrature": [
            {
                "punti": int(len(m.punti)),
                "asse": m.asse.tolist(),
                "origine": m.origine.tolist(),
                "lunghezza": m.lunghezza,
                "sezione": list(m.sezione),
                "sezione_dispersione": list(m.sezione_dispersione),
                "contorno": m.contorno.tolist(),
                "fuori_piombo_deg": m.fuori_piombo_deg,
                "asse_ideale": m.asse_ideale.tolist(),
                "scarto_asse_deg": m.scarto_asse_deg,
                "rigonfiamento": {
                    "celle": int(len(m.rigonfiamento)),
                    "min": float(np.min(m.rigonfiamento)) if len(m.rigonfiamento) else None,
                    "max": float(np.max(m.rigonfiamento)) if len(m.rigonfiamento) else None,
                    "p95": float(np.percentile(np.abs(m.rigonfiamento), 95))
                    if len(m.rigonfiamento)
                    else None,
                },
                "volume": m.volume,
                "esiti": m.esiti,
            }
            for m in accettate
        ],
        "scartate": scartate,
        "chiusura_volume": {
            "somma": somma,
            "unione": unione,
            "scarto_relativo": scarto_relativo,
            "passo": float(passo_unione),
            "passato": abs(scarto_relativo) <= cfg.union_tolerance,
            "soglia": float(cfg.union_tolerance),
            "spiegazione": (
                "somma dei volumi delle membrature contro volume della loro "
                "unione: se differiscono, alle giunzioni il volume e' contato "
                "due volte, ed e' un errore che nessuna metrica di qualita' "
                "della mesh vedrebbe"
            ),
        },
        "riscontri": {
            "membrature_attese": cfg.membrature_attese,
            "scarto_membrature": scarto_membrature,
            "sezioni_nominali": (
                [list(sezione) for sezione in cfg.sezioni_nominali]
                if cfg.sezioni_nominali is not None
                else None
            ),
            "volume_atteso": cfg.volume_atteso,
            "scarto_volume": scarto_volume,
            "nota": (
                "i riscontri sono dichiarati dall'operatore e assenti per "
                "definizione su un pezzo mai visto: dove c'e' null, non c'e' "
                "un'aspettativa, non c'e' un valore mancante"
            ),
        },
    }
```

Le membrature di `prior` conservano gli indici della **nuvola ripulita** dal pavimento, non di quella in ingresso: e' scritto qui perche' i chiamanti dei Task 8 e 12 disegnano su quella nuvola.

- [ ] **Step 13: Eseguire**

Run: `uv run pytest tests/test_wall.py -v`
Expected: PASS su tutti.

- [ ] **Step 14: La suite intera**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

- [ ] **Step 15: Commit**

```bash
git add meshrec/src/meshrec/core/wall.py meshrec/tests/test_wall.py
git commit -m "feat(fase-4): i controlli intrinseci del prior e i riscontri dichiarati"
```

---

