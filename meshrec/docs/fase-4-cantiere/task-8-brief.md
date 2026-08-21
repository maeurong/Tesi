## Task 8: il telaio — i due modelli, le giunzioni tagliate, le superfici del `*TIE`

**Files:**
- Modify: `src/meshrec/core/hexa.py`
- Test: `tests/test_hexa.py`

**Interfaces:**
- Consumes: `hexa.mesh_prisma` (Task 7); `wall.Membratura` (Task 3); `abaqus.element_surface` (Task 5).
- Produces:
  - `hexa.Prisma` — dataclass `contorno, origine, asse, lunghezza`.
  - `hexa.prisma_di(membratura, tipo) -> Prisma` con `tipo` in `("estruso", "primitive")`.
  - `hexa.dentro(prisma, punti, tolleranza=0.0) -> np.ndarray`.
  - `hexa.taglia_giunzioni(prismi) -> tuple[list[Prisma], list[dict]]`.
  - `hexa.costruisci(membrature, tipo, cfg) -> dict[str, object]` con chiavi `nodi`, `elementi`, `blocchi`, `superfici`, `ties`, `metriche`.

**Requisito del Ruling J, con un proprio test e non come nota:** `wall.py` misura e non scarta, quindi il rifiuto di una regione non prismatica arriva qui. `costruisci` **non puo' costruire** su una membratura con `riempimento_stato == "vuoto"`: quella regione e' un ingombro, non una sezione — tipicamente due membrature unite a Π che la scomposizione non ha separato — e un modello costruito su di essa sarebbe inventato. Lo stato basta da solo e **non c'e' alcuna soglia da rileggere qui**: `wall.misura` mette «vuoto» soltanto quando la misura e' affidabile, e degrada a «non_verificabile» appena la dispersione della densita' supera `WallConfig.density_dispersion_limit` (`wall.py:501-506`). `costruisci` riceve un `ModelConfig`, che quella soglia non ce l'ha e non deve averla. Lo stato `non_verificabile` **non** e' motivo di rifiuto: dice che la misura non vale, non che il pezzo e' cavo, e su una nuvola rada e' l'esito normale. Se questa guardia mancasse, una Π diventerebbe un modello parametrico: e' il costo dichiarato del Ruling J.

- [ ] **Step 1: I test dei due prismi, del taglio e delle superfici**

In coda a `tests/test_hexa.py`. **Ogni test dichiara nel proprio corpo quale mutazione del codice deve ucciderlo**: se rileggendolo non riesci a nominarne una, quel test e' decorazione e va rifatto, non allentato.

```python
def _membratura_finta(contorno, origine, asse, lunghezza, asse_ideale, riempimento="pieno"):
    from meshrec.core.wall import Membratura

    return Membratura(
        punti=np.arange(0),
        asse=np.asarray(asse, dtype=np.float64),
        origine=np.asarray(origine, dtype=np.float64),
        lunghezza=float(lunghezza),
        sezione=(float(np.ptp(contorno[:, 0])), float(np.ptp(contorno[:, 1]))),
        sezione_dispersione=(0.0, 0.0),
        contorno=np.asarray(contorno, dtype=np.float64),
        fuori_piombo_deg=0.0,
        asse_ideale=np.asarray(asse_ideale, dtype=np.float64),
        scarto_asse_deg=0.0,
        rigonfiamento=np.zeros(4),
        volume=0.0,
        riempimento_sezione=1.0 if riempimento == "pieno" else 0.3,
        riempimento_stato=riempimento,
        densita_dispersione=0.0,
    )


# Il telaio del banco: una colonna 200 x 200 alta 1400 e una trave 300 x 200
# lunga 1400, la cui faccia inferiore sta a z = 1300. Sono numeri scelti perche'
# ogni valore atteso qui sotto sia un prodotto di dimensioni o una differenza
# fra due quote, mai una misura letta dal codice sotto prova.
COLONNA = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0]])
TRAVE = np.array([[0.0, 0.0], [300.0, 0.0], [300.0, 200.0], [0.0, 200.0]])
QUOTA_TRAVE = 1300.0
ALTEZZA_COLONNA = 1400.0
LUNGHEZZA_TRAVE = 1400.0
# 1400 - 1300: la colonna arriva 100 mm dentro la trave e li' va tagliata.
ACCORCIAMENTO_ATTESO = ALTEZZA_COLONNA - QUOTA_TRAVE


def _telaio_di_prova():
    """Le due membrature del banco, nell'ordine colonna, trave."""
    return [
        _membratura_finta(COLONNA, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0],
                          ALTEZZA_COLONNA, [0.0, 0.0, 1.0]),
        _membratura_finta(TRAVE, [0.0, 0.0, QUOTA_TRAVE], [1.0, 0.0, 0.0],
                          LUNGHEZZA_TRAVE, [1.0, 0.0, 0.0]),
    ]


def test_una_membratura_a_sezione_vuota_non_diventa_un_modello():
    """La guardia del Ruling J, che e' l'unica che ferma una Π: wall.py misura
    e non scarta, quindi una regione il cui ingombro non e' la sezione arriva
    fin qui. Costruirci sopra vorrebbe dire dare per pieno un vano vuoto.

    Muore se: si toglie la guardia, o se la si allarga a «non_verificabile»
    (il test qui sotto e' la meta' che smentisce questa)."""
    vuota = _membratura_finta(
        RETTANGOLO, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], LUNGHEZZA, ASSE_Z, riempimento="vuoto"
    )

    with pytest.raises(ValueError, match="vuoto"):
        hexa.costruisci([vuota], "estruso", ModelConfig())


def test_una_membratura_non_verificabile_si_costruisce_lo_stesso():
    """Il controllo che smentisce la guardia: «non verificabile» dice che la
    misura non vale, non che il pezzo e' cavo. Su una nuvola rada e' l'esito
    normale, e rifiutarlo fermerebbe il modello su meta' dei casi reali.

    Muore se: la guardia rifiuta ogni stato diverso da «pieno»."""
    incerta = _membratura_finta(
        RETTANGOLO, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], LUNGHEZZA, ASSE_Z,
        riempimento="non_verificabile",
    )

    esito = hexa.costruisci([incerta], "estruso", ModelConfig())

    assert len(esito["blocchi"]) == 1


def test_il_modello_primitive_raddrizza_l_asse_e_squadra_la_sezione():
    """I due modelli separano due effetti diversi: l'irregolarita' della sezione
    e il fuori piombo. Se primitive non raddrizzasse, il confronto li
    sommerebbe in un unico salto invece di distinguerli.

    Muore se: primitive restituisce `membratura.asse` invece di `asse_ideale`,
    o il contorno rilevato invece del rettangolo."""
    storto = np.array([0.0, np.sin(np.radians(6.0)), np.cos(np.radians(6.0))])
    sezione_irregolare = np.array([[0.0, 0.0], [200.0, 4.0], [197.0, 140.0], [3.0, 136.0]])
    membratura = _membratura_finta(
        sezione_irregolare, [0.0, 0.0, 0.0], storto, LUNGHEZZA, [0.0, 0.0, 1.0]
    )

    estruso = hexa.prisma_di(membratura, "estruso")
    primitive = hexa.prisma_di(membratura, "primitive")

    assert estruso.asse == pytest.approx(storto)
    assert primitive.asse == pytest.approx([0.0, 0.0, 1.0])
    assert len(estruso.contorno) == 4
    assert len(primitive.contorno) == 4
    # primitive e' il rettangolo dei valori misurati: quattro angoli retti
    lati = np.diff(np.vstack([primitive.contorno, primitive.contorno[:1]]), axis=0)
    for primo, secondo in zip(lati, np.roll(lati, -1, axis=0), strict=True):
        assert float(np.dot(primo, secondo)) == pytest.approx(0.0, abs=1e-9)


def test_il_modello_primitive_conserva_le_dimensioni_misurate():
    """Il controllo che smentisce il precedente: raddrizzare non vuol dire
    inventare. Le due dimensioni del rettangolo sono quelle misurate.

    La sezione del banco e' **irregolare** apposta: con un rettangolo gia'
    squadrato, un primitive che restituisse il contorno tal quale supererebbe
    il test senza fare nulla — verificato per mutazione.

    Muore se: primitive copia il contorno rilevato; muore anche se lo squadra
    su dimensioni che non sono le due estensioni misurate."""
    # 250 x 175 sono le estensioni della sezione irregolare qui sotto:
    # np.ptp sui vertici da' esattamente quei due numeri.
    sezione = np.array([[0.0, 0.0], [250.0, 6.0], [246.0, 175.0], [4.0, 169.0]])
    membratura = _membratura_finta(
        sezione, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 900.0, [0.0, 0.0, 1.0]
    )

    primitive = hexa.prisma_di(membratura, "primitive")

    assert np.ptp(primitive.contorno, axis=0) == pytest.approx([250.0, 175.0])
    assert primitive.lunghezza == pytest.approx(900.0)
    assert not np.allclose(primitive.contorno, sezione), "primitive squadra, non copia"


def test_l_appartenenza_a_un_prisma_e_esatta_sul_contorno_convesso():
    """Muore se: la tolleranza viene applicata sempre invece che su richiesta
    (il punto «appena fuori» entrerebbe), o se non viene applicata affatto
    (non entrerebbe nemmeno quando la si chiede)."""
    prisma = hexa.Prisma(
        contorno=RETTANGOLO, origine=np.zeros(3), asse=ASSE_Z, lunghezza=1000.0
    )
    dentro = np.array([[100.0, 70.0, 500.0], [1.0, 1.0, 1.0]])
    fuori = np.array([[300.0, 70.0, 500.0], [100.0, 70.0, 1500.0], [100.0, -5.0, 500.0]])

    assert hexa.dentro(prisma, dentro).all()
    assert not hexa.dentro(prisma, fuori).any()

    # la tolleranza e' un margine chiesto, non un predefinito: mezzo millimetro
    # fuori dalla faccia y = 0 sta fuori, ed entra solo se la si concede.
    appena_fuori = np.array([[100.0, -0.5, 500.0]])
    assert not hexa.dentro(prisma, appena_fuori).any()
    assert hexa.dentro(prisma, appena_fuori, tolleranza=1.0).all()


def test_due_prismi_che_si_compenetrano_vengono_tagliati_sul_bordo_del_solido():
    """Le membrature si compenetrano dove si incontrano, e senza taglio il
    volume viene contato due volte: un errore che nessuna metrica di qualita'
    vedrebbe, e per questo il controllo lo cerca esplicitamente.

    Il taglio si ferma sul **bordo del solido**, trovato per bisezione, non
    sull'ultimo campione libero: la differenza e' 5,5 mm su questo banco, ed e'
    cio' che rende possibile il `*TIE` del test in fondo — due superfici
    distanti mezzo centimetro non si legano.

    Ogni numero atteso qui e' geometria dichiarata, non una lettura:
    l'accorciamento e' 1400 - 1300 = 100 mm, cioe' quanto la colonna entrava
    nella trave; il volume e' la somma di due prodotti di dimensioni, senza
    sottrazioni, perche' dopo il taglio i due solidi non si sovrappongono piu'.

    Muore se: si toglie il taglio (accorciamento 0, volume in eccesso dell'8,8%);
    muore anche se si toglie la sola bisezione e ci si ferma sul campione
    (accorciamento 94,5 invece di 100, volume in eccesso dello 0,16%) — entrambe
    le mutazioni verificate."""
    colonna = hexa.Prisma(
        contorno=COLONNA, origine=np.array([0.0, 0.0, 0.0]),
        asse=np.array([0.0, 0.0, 1.0]), lunghezza=ALTEZZA_COLONNA,
    )
    trave = hexa.Prisma(
        contorno=TRAVE, origine=np.array([0.0, 0.0, QUOTA_TRAVE]),
        asse=np.array([1.0, 0.0, 0.0]), lunghezza=LUNGHEZZA_TRAVE,
    )

    tagliati, giunzioni = hexa.taglia_giunzioni([colonna, trave])

    assert len(tagliati) == 2
    assert len(giunzioni) == 1
    # per indice e mai con min(): la trave e' piu' corta della colonna intera,
    # e un min() farebbe passare il test scegliendo il prisma mai tagliato.
    assert (giunzioni[0]["minore"], giunzioni[0]["maggiore"]) == (0, 1)
    assert giunzioni[0]["accorciamento"] == pytest.approx(ACCORCIAMENTO_ATTESO, abs=1e-6)
    assert tagliati[0].lunghezza == pytest.approx(QUOTA_TRAVE, abs=1e-6)
    assert tagliati[1].lunghezza == pytest.approx(LUNGHEZZA_TRAVE)

    somma = sum(
        abs(hexa._area_poligono(p.contorno)) * p.lunghezza for p in tagliati
    )
    # rel=1e-9 e non una tolleranza larga: dopo la bisezione l'errore misurato
    # e' 1,3e-15, cioe' il solo residuo in virgola mobile. Una tolleranza che
    # copre l'errore che dovrebbe scoprire e' un permesso, non una tolleranza.
    assert somma == pytest.approx(
        200.0 * 200.0 * QUOTA_TRAVE + 300.0 * 200.0 * LUNGHEZZA_TRAVE, rel=1e-9
    )


def test_un_prisma_che_attraversa_un_altro_da_parte_a_parte_e_rifiutato():
    """Il soffitto dichiarato del taglio, con il proprio controllo invece che
    come nota: l'accorciamento lungo l'asse non sa dividere un prisma in due.

    Una colonna alta 1600 passa oltre la trave, che sta fra 1300 e 1500: le due
    estremita' restano libere e l'invasione e' una banda centrale. Prima della
    correzione del 20/08/2026 questo caso non sollevava — la guardia guardava
    `invaso[0] and invaso[-1]`, che e' il contenimento, non l'attraversamento —
    e produceva un accorciamento di zero in silenzio.

    Muore se: la guardia torna a controllare il contenimento invece
    dell'attraversamento, o sparisce."""
    passante = hexa.Prisma(
        contorno=COLONNA, origine=np.array([0.0, 0.0, 0.0]),
        asse=np.array([0.0, 0.0, 1.0]), lunghezza=1600.0,
    )
    trave = hexa.Prisma(
        contorno=TRAVE, origine=np.array([0.0, 0.0, QUOTA_TRAVE]),
        asse=np.array([1.0, 0.0, 0.0]), lunghezza=LUNGHEZZA_TRAVE,
    )

    with pytest.raises(ValueError, match="parte a parte"):
        hexa.taglia_giunzioni([passante, trave])


def test_il_telaio_costruito_dichiara_le_superfici_del_tie():
    """La mesh di due membrature adiacenti non combacia nodo a nodo: il legame
    e' un *TIE fra superfici a contatto, e le superfici devono avere facce.

    Non basta che i due nomi esistano nel dizionario: un *TIE su una superficie
    senza facce e' accettato dal solutore e non vincola nulla — verificato con
    CalculiX, che sulla geometria compenetrata esce con codice 0, senza alcun
    `*ERROR`, e stampa `*WARNING in gentiedmpc: no tied MPC`. Le facce sono la
    cosa da asserire.

    Muore se: si toglie il taglio (le due mesh si compenetrano e le superfici
    nominano facce sepolte dentro l'altro solido, che il solutore non lega);
    muore se si toglie la bisezione (le superfici restano vuote, distanti 5,5 mm,
    e `ties` esce vuota); muore se la tolleranza di contatto va a zero (le
    superfici restano vuote per il solo residuo della bisezione)."""
    modello = hexa.costruisci(_telaio_di_prova(), "estruso", ModelConfig())

    assert modello["elementi"].shape[1] == 8
    assert len(modello["blocchi"]) == 2
    assert modello["ties"], "due membrature che si toccano devono avere un *TIE"
    for _nome, dipendente, indipendente in modello["ties"]:
        assert modello["superfici"][dipendente], "superficie dipendente senza facce"
        assert modello["superfici"][indipendente], "superficie indipendente senza facce"
    # una sola giunzione: le due membrature si incontrano in un punto solo
    assert modello["metriche"]["giunzioni"] == 1
    assert modello["metriche"]["accorciamenti"] == pytest.approx(
        [ACCORCIAMENTO_ATTESO], abs=1e-6
    )
```

`RETTANGOLO` (200 x 140), `LUNGHEZZA` (1500) e `ASSE_Z` sono le costanti gia' in testa a `tests/test_hexa.py`: si riusano, non si ridichiarano.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_hexa.py -k "membratura or primitive or appartenenza or compenetrano or attraversa or telaio" -v`
Expected: FAIL su tutti e otto con `AttributeError: module 'meshrec.core.hexa' has no attribute 'Prisma'` (o `'costruisci'`). Controlla che il filtro ne selezioni **otto**: un `-k` che ne prende meno non sta provando quello che credi.

- [ ] **Step 3: `Prisma`, `prisma_di`, `dentro`**

In `hexa.py`, aggiungi `from dataclasses import dataclass` agli import e in coda al file:

```python
@dataclass(eq=False)
class Prisma:
    """Un prisma retto: contorno di sezione nel proprio piano, origine, asse, lunghezza.

    E' l'unica forma che i modelli parametrici conoscono. Il contorno e'
    convesso perche' viene da `wall.semplifica_contorno`, che ne prende
    l'inviluppo convesso con scipy e poi toglie vertici — e togliere vertici a
    un poligono convesso lo lascia convesso. La convessita' e' cio' che rende
    immediato il test di appartenenza usato dal taglio alle giunzioni.
    """

    contorno: np.ndarray
    origine: np.ndarray
    asse: np.ndarray
    lunghezza: float


def prisma_di(membratura, tipo: str) -> Prisma:
    """Il prisma di una membratura, secondo il modello richiesto.

    Non sono due generatori ma due argomenti: cambia se la sezione conserva la
    forma rilevata o diventa il rettangolo dei valori misurati, e se l'asse
    conserva il fuori piombo misurato o e' l'asse ideale, dritto. Il confronto
    separa cosi' due effetti diversi -- irregolarita' della sezione e fuori
    piombo -- invece di sommarli in un unico salto.

    In nessuno dei due casi la sezione viene dal disegno: prenderla dal disegno
    farebbe misurare al confronto anche lo scarto fra progetto e costruito, che
    e' un'altra domanda.
    """
    if tipo == "estruso":
        return Prisma(
            contorno=np.asarray(membratura.contorno, dtype=np.float64),
            origine=np.asarray(membratura.origine, dtype=np.float64),
            asse=np.asarray(membratura.asse, dtype=np.float64),
            lunghezza=float(membratura.lunghezza),
        )
    if tipo == "primitive":
        larghezza, altezza = (float(valore) for valore in np.ptp(membratura.contorno, axis=0))
        minimo = np.min(np.asarray(membratura.contorno, dtype=np.float64), axis=0)
        rettangolo = minimo + np.array(
            [[0.0, 0.0], [larghezza, 0.0], [larghezza, altezza], [0.0, altezza]]
        )
        return Prisma(
            contorno=rettangolo,
            origine=np.asarray(membratura.origine, dtype=np.float64),
            asse=np.asarray(membratura.asse_ideale, dtype=np.float64),
            lunghezza=float(membratura.lunghezza),
        )
    raise ValueError(f"modello '{tipo}' sconosciuto: i modelli sono 'estruso' e 'primitive'")


def dentro(prisma: Prisma, punti: np.ndarray, tolleranza: float = 0.0) -> np.ndarray:
    """Quali dei punti dati cadono dentro il prisma, entro la tolleranza data.

    Due condizioni: la coordinata lungo l'asse sta fra zero e la lunghezza, e
    la proiezione sul piano di sezione sta dentro il contorno. Il contorno e'
    convesso, quindi «dentro» significa che tutti i prodotti vettoriali con i
    lati hanno lo stesso segno: nessun algoritmo di ray casting.

    `tolleranza` [mm] allarga la condizione **in tutte le direzioni**: lungo
    l'asse e nel piano di sezione. E' un parametro e non un valore fisso perche'
    ha due usi opposti. Il taglio alle giunzioni la lascia a zero, che e' la
    condizione esatta su cui la bisezione converge; le superfici del `*TIE` la
    chiedono piccola, come margine per il residuo in virgola mobile della
    bisezione stessa. Allargare invece la geometria del prisma -- gonfiarne
    origine e lunghezza -- non sarebbe la stessa cosa e sarebbe sbagliato: lo
    allargherebbe solo lungo il proprio asse e mai nella sezione, che e'
    proprio la direzione in cui due membrature che si incontrano si toccano.
    """
    coordinate = np.atleast_2d(np.asarray(punti, dtype=np.float64))
    versore = prisma.asse / np.linalg.norm(prisma.asse)
    e1, e2 = _base_del_piano(versore)
    relativi = coordinate - prisma.origine

    lungo = relativi @ versore
    nel_tratto = (lungo >= -tolleranza) & (lungo <= prisma.lunghezza + tolleranza)

    sezione = np.column_stack([relativi @ e1, relativi @ e2])
    contorno = prisma.contorno
    if _area_poligono(contorno) < 0.0:
        contorno = contorno[::-1]
    dentro_sezione = np.ones(len(coordinate), dtype=bool)
    for primo, secondo in zip(contorno, np.roll(contorno, -1, axis=0), strict=True):
        lato = secondo - primo
        scostamento = sezione - primo
        # Componente z del prodotto vettoriale, scritta per esteso: np.cross
        # rifiuta i vettori 2D da numpy 2.0 e solleva ValueError. E' la stessa
        # lezione gia' pagata e annotata in wall.semplifica_contorno, che con
        # numpy 2.5 e' l'unica versione che il progetto usa.
        # Il prodotto vale |lato| per la distanza dal lato, quindi la soglia si
        # normalizza sulla lunghezza del lato per essere una distanza in mm.
        verso = lato[0] * scostamento[:, 1] - lato[1] * scostamento[:, 0]
        dentro_sezione &= verso >= -tolleranza * float(np.linalg.norm(lato))
    return nel_tratto & dentro_sezione
```

- [ ] **Step 4: `taglia_giunzioni` e `costruisci`**

In coda a `hexa.py`:

```python
_CAMPIONI_ASSE = 200
"""Campioni lungo l'asse con cui si cerca **se** un prisma entra in un altro.

Non e' un parametro di elaborazione: e' la risoluzione con cui si trova
l'intervallo che contiene il bordo, non la precisione del taglio, che e' quella
della bisezione qui sotto. Duecento campioni su una membratura di due metri
sono un centimetro, cioe' sotto la scala di qualunque giunzione.
"""

_PASSI_BISEZIONE = 40
"""Dimezzamenti con cui si trova il bordo del solido dentro l'intervallo trovato.

Quaranta dimezzamenti portano un intervallo di sette millimetri sotto 1e-11 mm,
cioe' sotto la risoluzione di `_ARROTONDAMENTO` con cui due coordinate sono lo
stesso punto. Sul banco del telaio il residuo misurato e' 3,4e-12 mm.
"""

_TOLLERANZA_CONTATTO = 1e-6
"""Margine [mm] con cui due superfici tagliate a filo sono considerate a contatto.

Un micrometro e' la stessa risoluzione di `_ARROTONDAMENTO`, dove due
coordinate prodotte dalla stessa costruzione sono gia' lo stesso punto. Non e'
un raggio di ricerca e non deve diventarlo: dopo la bisezione le due superfici
distano il solo residuo in virgola mobile, e questo margine copre quello.
Verificato che serve: a tolleranza zero le superfici escono vuote per il solo
residuo, e con esso portano 20 e 12 facce.
"""


def _bordo_del_solido(
    maggiore: Prisma, base: np.ndarray, versore: np.ndarray, fuori: float, dentro_s: float
) -> float:
    """Ascissa dell'ultimo punto fuori dal prisma maggiore, per bisezione.

    Bisezione sulla stessa funzione di appartenenza che il taglio usa gia',
    quindi il bordo trovato e' il bordo secondo `dentro` e non secondo una
    seconda descrizione della stessa superficie, che potrebbe non coincidere.
    `fuori` e' un'ascissa fuori dal maggiore, `dentro_s` una dentro; l'ordine
    numerico fra le due non conta.
    """
    for _ in range(_PASSI_BISEZIONE):
        mezzo = 0.5 * (fuori + dentro_s)
        if dentro(maggiore, base + mezzo * versore)[0]:
            dentro_s = mezzo
        else:
            fuori = mezzo
    return fuori


def taglia_giunzioni(prismi: list[Prisma]) -> tuple[list[Prisma], list[dict[str, object]]]:
    """Accorcia i prismi minori dove entrano in un prisma maggiore.

    Le membrature si compenetrano dove si incontrano, e senza taglio il volume
    alle giunzioni viene contato due volte: un errore che nessuna metrica di
    qualita' della mesh vedrebbe, e per questo il controllo di chiusura del
    volume lo cerca esplicitamente.

    Il taglio si ferma sul **bordo del solido**, non sull'ultimo campione
    libero: i campioni servono solo a trovare l'intervallo che contiene il
    bordo, e la bisezione lo stringe fin sotto il rumore in virgola mobile.
    **E' la precisione del taglio a rendere possibile il `*TIE`**: fermarsi sul
    campione lascia fra le due membrature un vuoto grande quanto il passo di
    campionamento -- 5,5 mm sul banco del telaio -- e due superfici distanti
    mezzo centimetro non si legano. Legarle allargando il raggio di ricerca
    farebbe passare il controllo senza rendere giusto il modello.

    Chi cede e' il prisma di sezione minore, che e' un criterio del dato e non
    dell'ordine in cui i prismi arrivano: a pari sezione decide la lunghezza, e
    a pari lunghezza l'indice, che e' l'ultima carta e serve solo a non
    lasciare la scelta all'ordinamento.

    **Soffitto dichiarato:** il taglio e' un accorciamento lungo l'asse, quindi
    vale quando l'intersezione tocca un'estremita' del prisma minore -- il caso
    di un telaio, dove le membrature si incontrano alle estremita'. Gli altri
    due casi sollevano invece di produrre un risultato in silenzio: un prisma
    che attraversa l'altro da parte a parte (estremita' entrambe libere,
    invasione al centro) e un prisma interamente contenuto in un altro
    (estremita' entrambe invase). La via d'aggiornamento e' una vera operazione
    booleana fra solidi, che oggi non ha in casa nessuna libreria del progetto.
    """
    ordine = sorted(
        range(len(prismi)),
        key=lambda indice: (
            -abs(_area_poligono(prismi[indice].contorno)),
            -prismi[indice].lunghezza,
            indice,
        ),
    )
    tagliati = list(prismi)
    giunzioni: list[dict[str, object]] = []

    for posizione, maggiore in enumerate(ordine):
        for minore in ordine[posizione + 1 :]:
            piccolo = tagliati[minore]
            versore = piccolo.asse / np.linalg.norm(piccolo.asse)
            passo = np.linspace(0.0, piccolo.lunghezza, _CAMPIONI_ASSE)
            centro_sezione = piccolo.contorno.mean(axis=0)
            e1, e2 = _base_del_piano(versore)
            base = piccolo.origine + centro_sezione[0] * e1 + centro_sezione[1] * e2
            invaso = dentro(tagliati[maggiore], base + np.outer(passo, versore))
            if not invaso.any():
                continue

            # I due casi che l'accorciamento lungo l'asse non sa fare, ciascuno
            # con la propria diagnosi. Sono guardie e non note: senza,
            # l'attraversamento produceva un accorciamento di zero in silenzio.
            if invaso[0] and invaso[-1]:
                raise ValueError(
                    "un prisma e' interamente dentro un altro: non c'e' un "
                    "estremo da accorciare. Verifica la scomposizione: due "
                    "regioni sovrapposte non sono due membrature"
                )
            if not invaso[0] and not invaso[-1]:
                raise ValueError(
                    "un prisma attraversa un altro da parte a parte: il taglio "
                    "alle giunzioni accorcia lungo l'asse e non sa dividere un "
                    "prisma in due. Verifica la scomposizione: due membrature "
                    "che si attraversano sono quasi sempre una regione fusa"
                )

            libero = np.flatnonzero(~invaso)
            if invaso[0]:
                # invasa l'estremita' iniziale: il bordo sta fra il primo
                # campione libero e quello invaso che lo precede
                fine = _bordo_del_solido(
                    tagliati[maggiore], base, versore,
                    passo[libero[0]], passo[libero[0] - 1],
                )
                nuova_origine = piccolo.origine + versore * fine
                nuova_lunghezza = piccolo.lunghezza - fine
            else:
                fine = _bordo_del_solido(
                    tagliati[maggiore], base, versore,
                    passo[libero[-1]], passo[libero[-1] + 1],
                )
                nuova_origine = piccolo.origine
                nuova_lunghezza = fine

            giunzioni.append({
                "maggiore": int(maggiore),
                "minore": int(minore),
                "accorciamento": float(piccolo.lunghezza - nuova_lunghezza),
            })
            tagliati[minore] = Prisma(
                contorno=piccolo.contorno,
                origine=nuova_origine,
                asse=piccolo.asse,
                lunghezza=float(nuova_lunghezza),
            )

    return tagliati, giunzioni


def costruisci(membrature: list, tipo: str, cfg: ModelConfig) -> dict[str, object]:
    """Il telaio intero: prismi tagliati, mesh di ciascuno, superfici e vincoli.

    Le mesh di membrature adiacenti non combaciano nodo a nodo -- una sezione
    da 172 contro una da 700 -- quindi il legame e' un `*TIE` fra le superfici
    a contatto e non una fusione di nodi. **La mesh conforme multiblocco resta
    la via d'aggiornamento**, e non e' un dettaglio d'attuazione: e' una
    differenza fra i modelli che non deriva dalla geometria, ed e' per questo
    che il report la dichiara accanto al confronto. Senza quella riga, una
    differenza di rigidezza nata dal `*TIE` verrebbe letta come effetto della
    forma.
    """
    if not membrature:
        raise ValueError(
            "nessuna membratura da costruire: il prior non ne ha accettata alcuna. "
            "Guarda le regioni scartate e il controllo che le ha respinte, invece "
            "di generare un modello vuoto"
        )

    # la guardia del Ruling J: wall.py misura e non scarta, quindi il rifiuto
    # di una regione non prismatica arriva qui. Riempimento «vuoto» vuol dire
    # che l'ingombro non e' la sezione ma il suo contenitore -- tipicamente due
    # membrature unite a Π che la scomposizione non ha separato -- e un modello
    # costruito su quella sezione sarebbe inventato. Lo stato «non_verificabile»
    # non e' motivo di rifiuto: dice che la misura non vale, non che il pezzo e'
    # cavo. Lo stato basta da solo: `wall.misura` mette «vuoto» solo su una
    # misura affidabile e degrada a «non_verificabile» appena non lo e'
    # (wall.py:501-506). Nessuna soglia da rileggere qui, e ModelConfig non ne
    # ha una.
    vuote = [
        numero
        for numero, membratura in enumerate(membrature)
        if membratura.riempimento_stato == "vuoto"
    ]
    if vuote:
        raise ValueError(
            f"le membrature {vuote} hanno riempimento di sezione «vuoto» con "
            "misura affidabile: la loro sezione e' un ingombro e non una "
            "sezione, e su di essa non si costruisce. Guarda la scomposizione: "
            "sono quasi sempre due membrature adiacenti fuse in una regione a Π"
        )

    prismi = [prisma_di(membratura, tipo) for membratura in membrature]
    tagliati, giunzioni = taglia_giunzioni(prismi)

    nodi_totali: list[np.ndarray] = []
    elementi_totali: list[np.ndarray] = []
    blocchi: list[dict[str, object]] = []
    scorrimento = 0
    for numero, prisma in enumerate(tagliati):
        nodi, esaedri, metriche = mesh_prisma(
            prisma.contorno, prisma.origine, prisma.asse, prisma.lunghezza, cfg
        )
        nodi_totali.append(nodi)
        elementi_totali.append(esaedri + scorrimento)
        blocchi.append({
            "membratura": numero,
            "primo_nodo": scorrimento,
            "nodi": int(len(nodi)),
            "primo_elemento": int(sum(len(e) for e in elementi_totali[:-1])),
            "elementi": int(len(esaedri)),
            **metriche,
        })
        scorrimento += len(nodi)

    nodi = np.ascontiguousarray(np.vstack(nodi_totali))
    elementi = np.ascontiguousarray(np.vstack(elementi_totali))

    # Le superfici a contatto: per ogni giunzione, le facce del prisma minore
    # che toccano il maggiore, e viceversa. Il margine e' `_TOLLERANZA_CONTATTO`
    # e non il passo di mesh: dopo la bisezione le due superfici sono a filo, e
    # quel che resta e' il residuo in virgola mobile. Un margine grande quanto
    # il passo di mesh legherebbe anche superfici che non si toccano, e il
    # controllo passerebbe senza che il modello sia giusto.
    #
    # Il dipendente e' il prisma di sezione minore. Non e' la regola «la
    # superficie piu' fitta fa da dipendente»: l'ordine per area e quello per
    # passo di mesh non coincidono -- una sezione 1000 x 10 ha area maggiore di
    # una 90 x 90 e passo sei volte piu' fine -- quindi questa e' una scelta di
    # determinismo, non di convergenza numerica. Verificato che su questa
    # assegnazione CalculiX genera i vincoli senza un solo nodo fallito; la via
    # d'aggiornamento, se una geometria reale mostrasse il contrario, e'
    # ordinare i due ruoli per `blocco["passo"]`.
    from meshrec.core import abaqus

    superfici: dict[str, list[tuple[int, int]]] = {}
    ties: list[tuple[str, str, str]] = []
    for numero, giunzione in enumerate(giunzioni, start=1):
        minore, maggiore = int(giunzione["minore"]), int(giunzione["maggiore"])
        nomi = []
        for ruolo, indice, altro in (
            ("D", minore, maggiore),
            ("I", maggiore, minore),
        ):
            blocco = blocchi[indice]
            inizio = blocco["primo_nodo"]
            fine = inizio + blocco["nodi"]
            vicini = np.flatnonzero(
                dentro(tagliati[altro], nodi[inizio:fine], _TOLLERANZA_CONTATTO)
            ) + inizio
            nome = f"{cfg.tie_name_prefix}_{numero}_{ruolo}"
            superfici[nome] = abaqus.element_surface(elementi, vicini, cfg.element)
            nomi.append(nome)
        if superfici[nomi[0]] and superfici[nomi[1]]:
            ties.append((f"{cfg.tie_name_prefix}_{numero}", nomi[0], nomi[1]))
        else:
            # superficie vuota: le due mesh non si toccano davvero. Meglio
            # nessun vincolo che un *TIE su una superficie senza facce, che il
            # solutore accetterebbe e non vincolerebbe nulla.
            for nome in nomi:
                superfici.pop(nome, None)

    return {
        "nodi": nodi,
        "elementi": elementi,
        "blocchi": blocchi,
        "superfici": superfici,
        "ties": tuple(ties),
        "metriche": {
            "tipo": tipo,
            "membrature": len(tagliati),
            "giunzioni": len(ties),
            "accorciamenti": [giunzione["accorciamento"] for giunzione in giunzioni],
            "element_type": cfg.element,
            "vincolo_giunzioni": (
                "*TIE fra superfici a contatto: le mesh di membrature adiacenti "
                "non combaciano nodo a nodo. E' una differenza fra i modelli che "
                "non deriva dalla geometria -- as-built monolitico, parametrici "
                "vincolati alle giunzioni -- e va letta accanto al confronto. La "
                "mesh conforme multiblocco e' la via d'aggiornamento"
            ),
        },
    }
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_hexa.py -v`
Expected: PASS su tutti e **sedici** — gli otto gia' presenti nel file piu' gli otto di questo task.

- [ ] **Step 6: La suite intera e commit**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/hexa.py meshrec/tests/test_hexa.py
git commit -m "feat(fase-4): il telaio in esaedri, giunzioni tagliate e superfici del *TIE"
```

---

## Correzione del 20/08/2026 (setaccio)

Questo brief e' stato riscritto dopo un setaccio che ha trovato dodici difetti
nella versione precedente, tutti della stessa forma: un'affermazione scritta
senza eseguire nulla per verificarla. Ogni numero e ogni esito citati qui sotto
vengono da una prova eseguita, non da una lettura. Chi rilegge fra sei mesi
trova cosi' il difetto raccontato invece della versione sbagliata.

**Ruling W — `np.cross` sui vettori 2D non esiste piu'.** `dentro` calcolava
`np.cross(lato, sezione - primo)` su vettori a due componenti: da numpy 2.0
solleva `ValueError: Both input arrays must be (arrays of) 3-dimensional
vectors`, e il progetto gira su numpy 2.5.2. Nessuno dei sette test poteva
partire. La componente z si scrive per esteso, ed e' la stessa lezione gia'
annotata in `wall.semplifica_contorno` (`wall.py:322`), venti righe dentro la
funzione che questo brief cita per nome: il commento nuovo ci rimanda, cosi' la
prossima volta si trova.

**Ruling X — il taglio si ferma sul bordo del solido, non sull'ultimo campione.**
Il taglio prendeva `passo[libero[-1]]`, cioe' l'ultimo campione libero: sul
banco del telaio finiva a 1294,472 invece che a 1300, lasciando un vuoto di
5,528 mm che e' un artefatto del campionamento (1400/199 = 7,035 mm) e non
geometria. Ora `_bordo_del_solido` fa bisezione sulla stessa `dentro`, e il
vuoto scende a 3,4e-12 mm — l'errore relativo sul volume passa da 1,63e-03 a
8,8e-16. Ancoraggio non circolare: la trave comincia a z = 1300 per
costruzione, e `dentro(trave, fine - 1e-6)` e' falso mentre
`dentro(trave, fine + 1e-6)` e' vero.

La prima correzione proposta era un'altra — allargare a 66,7 mm la tolleranza
di appartenenza finche' le superfici del `*TIE` tornavano non vuote — ed e'
stata **scartata**: curava il sintomo. Legare due superfici distanti 5,5 mm con
un raggio di ricerca dodici volte piu' grande del vuoto avrebbe fatto passare
il controllo senza rendere giusto il modello, che e' esattamente la forma di
difetto che il setaccio serve a togliere.

**Le superfici del `*TIE` erano vuote, e nessun test lo vedeva.** Con il taglio
corretto la tolleranza gonfiava la geometria del prisma lungo il **proprio
asse**, mai nella sezione — cioe' nell'unica direzione in cui due membrature
che si incontrano si toccano — e la superficie dipendente usciva con zero
facce. Ora la tolleranza e' un parametro di `dentro` e vale in tutte le
direzioni, e `_TOLLERANZA_CONTATTO` e' un micrometro, la stessa risoluzione di
`_ARROTONDAMENTO`. Misurato: a tolleranza zero le superfici restano vuote per
il solo residuo della bisezione; con il micrometro portano 20 e 12 facce.

**Portato fino al solutore.** Sulla geometria compenetrata della versione
precedente, CalculiX usciva con codice 0, senza alcun `*ERROR`, e stampava
ventotto volte `*WARNING in gentiedmpc: no tied MPC`: il deck era accettato e i
due blocchi restavano slegati. Con il taglio per bisezione, sullo stesso deck:
`tie constraints: 1`, `Decascading the MPC's`, e **zero** nodi falliti. La
differenza fra «il solutore legge il deck» e «il modello e' legato» e' tutta
qui, e il Task 11 va esteso a un caso `*TIE` con criterio
`"no tied MPC" not in stdout` — senza, quel controllo resta l'unico punto in cui
un solutore vero tocca un deck del progetto e non prova la card piu' rischiosa.

**Ruling Y — geometria in cui il taglio avviene, e asserzione per indice.** La
colonna del banco era alta 1600 con la trave fra 1300 e 1500: la attraversava,
il taglio non scattava, e l'asserzione `min(tagliati, key=...).lunghezza < 1600`
passava scegliendo la **trave**, mai tagliata. Ora la colonna e' alta 1400,
finisce dentro la trave, e le asserzioni sono per indice. Criterio di
accettazione verificato: la mutazione che disattiva il taglio uccide il test, e
lo uccide anche quella che toglie la sola bisezione.

**Ruling Z — la tolleranza del volume non copre piu' l'errore che deve
scoprire.** Il valore atteso era `200*200*1600 + 300*200*1400 - 200*200*300`,
con `rel=0.15`. Il volume sovrapposto vero e' 200x200x200 = 8e6 mm³, non 12e6:
la trave sporge in y, la colonna no. E `rel=0.15` copriva sia il caso tagliato
sia quello non tagliato, cioe' non poteva distinguerli. Ora il valore atteso e'
una somma di due prodotti di dimensioni senza sottrazioni — dopo il taglio i
solidi non si sovrappongono — e la tolleranza e' `rel=1e-9`, sei ordini sopra il
residuo misurato (1,3e-15) e sette sotto l'errore dell'8,8% che la mutazione
produce.

**Il soffitto del taglio ha ora il proprio controllo.** La guardia
dell'attraversamento leggeva `invaso[0] and invaso[-1]`, che e' il
**contenimento**: un prisma che attraversa un altro ha le estremita' fuori e la
banda invasa al centro, quindi non sollevava e produceva un accorciamento di
zero in silenzio. Ora i due casi sono distinti, sollevano con diagnosi diverse,
e l'attraversamento ha un test.

**«La superficie piu' fitta fa da dipendente» non era vero.** Il commento
attribuiva all'ordine per area una proprieta' che appartiene al passo di mesh, e
i due ordini non coincidono: una sezione 1000 x 10 ha area maggiore di una
90 x 90 (10000 contro 8100) e passo sei volte piu' fine (3,33 contro 30). Il
commento ora dice quello che il codice fa davvero — una scelta di determinismo —
e nomina la via d'aggiornamento. L'assegnazione non e' stata cambiata perche'
nessuna misura mostra che l'altra sia migliore, e CalculiX lega senza un solo
nodo fallito su questa.

**Il resto, piu' minuto.** Il Requisito citava
`cfg.density_dispersion_limit` su un `ModelConfig` che non ha quel campo (sta in
`WallConfig`), mentre il codice faceva gia' la cosa giusta: ora la prosa dice
quello che il codice fa, con il rimando a `wall.py:501-506` che lo giustifica.
Lo Step 5 diceva «tutti e dieci» quando i test sono sedici (otto gia' nel file
piu' otto nuovi). Il filtro `-k` dello Step 2 conteneva «giunzion», che non
seleziona nessuno dei test nuovi, e lasciava fuori proprio quello del taglio.
`test_il_modello_primitive_conserva_le_dimensioni_misurate` usava una sezione
gia' rettangolare, quindi un `primitive` che copiasse il contorno tal quale lo
superava — verificato per mutazione; ora la sezione e' irregolare.
`assert metriche["giunzioni"] == len(ties)` rileggeva il valore che il codice
aveva appena scritto, e ora e' ancorato al banco: una giunzione, perche' le due
membrature si incontrano una volta sola.
