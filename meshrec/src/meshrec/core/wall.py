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

from dataclasses import dataclass, field

import numpy as np

from meshrec.core import io, segment
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

    E' il «metodo delle colonne» di docs/fase-1-tolleranza-set.md, la stessa
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


def _chiave_di_cella(celle: np.ndarray) -> np.ndarray:
    """Chiave intera che appiattisce (riga, colonna) in un solo numero: stesso
    risultato di `np.unique(..., axis=0)`, un terzo del costo (vedi il
    commento dov'era duplicata, in `spessore_per_cella`)."""
    return celle[:, 0] * (celle[:, 1].max() + 1) + celle[:, 1]


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
    chiave = _chiave_di_cella(celle)
    _, prima, inverso = np.unique(chiave, return_index=True, return_inverse=True)
    uniche = celle[prima]

    valori = np.asarray(trasversale, dtype=np.float64)
    alto = np.full(len(uniche), -np.inf)
    basso = np.full(len(uniche), np.inf)
    np.maximum.at(alto, inverso, valori)
    np.minimum.at(basso, inverso, valori)
    return uniche, alto - basso, inverso


def scarta_pavimento(
    points: np.ndarray, cfg_segment: SegmentConfig, cfg: WallConfig, spacing: float
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
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

    Il secondo valore restituito e' la maschera booleana, lunga come `points`,
    dei punti tenuti: senza, un indice calcolato sulla nuvola ripulita non ha
    modo di tornare a un indice della nuvola d'origine, che e' esattamente cio'
    che serve a `prior` per dichiarare a quali punti della nuvola segmentata
    appartiene ciascuna membratura.
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
        return np.ascontiguousarray(punti[tenuti]), tenuti, {
            "pavimento_trovato": True,
            "pavimento_punti": int(len(piano)),
            "punti_dopo": int(tenuti.sum()),
            **metriche_piani,
        }

    return punti, np.ones(len(punti), dtype=bool), {
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
    # ponytail: il soffitto e' lo spessore costante. Due membrature adiacenti
    # con la stessa sezione (per esempio un piedritto e una trave uniti a Π
    # con lo stesso spessore) non hanno alcuna discontinuita' da cui tagliare
    # e restano una regione sola -- vedi
    # test_una_sezione_uniforme_e_un_canarino_per_la_separazione_per_orientamento
    # in tests/test_wall.py. Non e' un risultato falso in silenzio: quella
    # regione non e' un prisma, e il riempimento di sezione la dichiara
    # «vuoto» perche' chi costruisce possa rifiutarla -- vedi `riempimento`
    # piu' sotto. Aggiornamento se servisse: direzione locale di
    # allungamento per cella (PCA sull'intorno) invece del solo spessore.
    from scipy.sparse import coo_array
    from scipy.sparse.csgraph import connected_components

    griglia = np.asarray(celle, dtype=np.int64)
    valori = np.asarray(spessori, dtype=np.float64)
    passo = int(griglia[:, 1].max() + 1)
    chiave = _chiave_di_cella(griglia)
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
) -> tuple[list[np.ndarray], dict[str, object], np.ndarray, np.ndarray, np.ndarray]:
    """La scomposizione completa: dal pavimento scartato agli indici dei punti per regione.

    Il numero di membrature non e' un parametro e non e' un'attesa: e' cio' che
    la nuvola contiene. Su una scatola torna una regione sola.

    Restituisce anche `puliti` (la nuvola senza pavimento), `tenuti` (la
    maschera su `points`) e `direzioni` (la terna principale): `prior()` li
    deve alla stessa `scarta_pavimento`/`terna` che questa funzione ha gia'
    pagato, e ricalcolarli vuol dire un secondo `extract_planes` e una seconda
    SVD sull'intera nuvola ripulita.
    """
    puliti, tenuti, metriche_pavimento = scarta_pavimento(points, cfg_segment, cfg, spacing)
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
    return per_regione, metriche, puliti, tenuti, direzioni


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
        # va tolto per primo. np.cross rifiuta vettori 2D da numpy 2.0, quindi
        # la componente z del prodotto vettoriale si scrive per esteso
        scostamento = inviluppo - precedente
        scarto = np.abs(corda[:, 0] * scostamento[:, 1] - corda[:, 1] * scostamento[:, 0])
        altezza = np.divide(
            scarto, lunghezza, out=np.zeros_like(scarto), where=lunghezza > 0.0
        )
        peggiore = int(np.argmin(altezza))
        if altezza[peggiore] > tolleranza:
            break
        inviluppo = np.delete(inviluppo, peggiore, axis=0)

    return np.ascontiguousarray(inviluppo)


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
    riempimento_sezione: float
    """Mediana, sulle fette lungo l'asse, della frazione occupata (bordo piu' interno racchiuso)."""
    riempimento_stato: str
    """«pieno», «vuoto» o «non_verificabile»: esito misurato, mai un motivo di scarto."""
    densita_dispersione: float
    """Dispersione relativa delle distanze al vicino piu' prossimo: quanto la densita' non e' uniforme."""
    esiti: dict[str, dict] = field(default_factory=dict)
    """Gli esiti dei controlli intrinseci, riempiti da `controlla`."""


_FETTE_LUNGO_ASSE = 20
"""Fette in cui la regione e' divisa per misurare la dispersione della sezione.

Non e' un parametro di elaborazione: e' la risoluzione con cui si guarda una
grandezza gia' definita, come i bin di un istogramma. Venti fette danno almeno
una decina di punti per fetta su qualunque membratura che superi min_cells.
"""


def misura(punti_regione: np.ndarray, direzioni: np.ndarray, cfg: WallConfig) -> Membratura:
    """Asse, lunghezza, sezione, contorno, fuori piombo, rigonfiamento e riempimento di una regione.

    Il fuori piombo e il rigonfiamento sono tenuti distinti perche' sono
    difetti diversi: un elemento puo' essere perfettamente piano e tutto
    storto, oppure a piombo e panciuto. Il primo e' un numero, il secondo e'
    una mappa, e sommarli darebbe un indice che non corrisponde a nulla di
    fisico.

    `direzioni` e' la terna del pezzo intero, non della regione: le due
    grandezze «asse ideale» e «rigonfiamento» hanno senso solo rispetto a un
    riferimento comune a tutte le membrature.

    La spaziatura per la griglia del riempimento non e' quella del pezzo
    intero: e' stimata qui su `punti_regione`, dalle distanze al vicino piu'
    prossimo che restituisce `io.nn_distances` (la stessa base su cui lo step 1
    calcola la spaziatura del pezzo). Una regione piu' lontana dallo scanner (o
    parzialmente occlusa) puo' essere campionata molto piu' rada del resto
    del pezzo: ereditare la spaziatura globale sposterebbe la soglia sulla
    grandezza sbagliata, come una prima versione di questo controllo faceva.
    Dalle stesse distanze viene la dispersione della densita', che dice se
    quella media descrive davvero la regione.
    """
    from scipy.ndimage import binary_fill_holes

    punti = np.asarray(punti_regione, dtype=np.float64)
    distanze = io.nn_distances(punti, cfg.spacing_sample, cfg.seed)
    spacing_locale = float(distanze.mean())
    densita_dispersione = float(distanze.std() / spacing_locale) if spacing_locale > 0.0 else 0.0
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
    # deve restare vuota invece di essere riempita da punti di un'altra. Il
    # lato di fetta e' anche la risoluzione della griglia del rigonfiamento
    # piu' sotto: niente moltiplicato per cell_factor perche' li' non c'e' una
    # spaziatura di punti da scalare, solo una frazione di lunghezza.
    lato_fetta = max(1e-9, float(np.ptp(lungo)) / _FETTE_LUNGO_ASSE)
    bordi = np.linspace(lungo.min(), lungo.max(), _FETTE_LUNGO_ASSE + 1)
    fetta = np.clip(np.digitize(lungo, bordi[1:-1]), 0, _FETTE_LUNGO_ASSE - 1)
    # riempimento: la risoluzione qui e' cell_factor * spacing_locale, la
    # stessa griglia gia' usata da scomponi e spessore_per_cella -- una
    # spaziatura di punti da scalare, non una frazione di lunghezza. Su una
    # nuvola di sola superficie i punti stanno solo sul perimetro della
    # sezione: «cella occupata» misurerebbe il bordo, e una griglia piu' fine
    # farebbe sembrare vuoto anche un prisma pieno. La cella piena e' invece
    # «non raggiungibile dall'esterno»: si marcano le celle con punti (il
    # perimetro), poi binary_fill_holes riempie cio' che quel perimetro
    # racchiude. Un prisma pieno da' un perimetro chiuso -> quasi tutto
    # riempito qualunque sia la sua forma; una Π ha un vano che l'esterno
    # raggiunge -> quel vano resta vuoto.
    lato_celle = cfg.cell_factor * spacing_locale
    per_fetta = []
    riempimenti = []
    for indice in range(_FETTE_LUNGO_ASSE):
        dentro = fetta == indice
        if dentro.sum() < 4:
            continue
        per_fetta.append((np.ptp(sezione_2d[dentro, 0]), np.ptp(sezione_2d[dentro, 1])))
        celle_fetta = chiavi_di_cella(sezione_2d[dentro], lato_celle)
        nx, ny = int(celle_fetta[:, 0].max()) + 1, int(celle_fetta[:, 1].max()) + 1
        # sotto le due celle per lato la griglia e' degenere in una riga o
        # colonna sola: binary_fill_holes non puo' mai chiudere un vuoto al
        # suo interno (servono celle su entrambi i lati per «racchiudere»
        # qualcosa), quindi il numero che uscirebbe non misura piu' un
        # riempimento ma la sola occupazione grezza del perimetro. Non e' un
        # parametro di qualita' da tarare: e' il minimo perche' la
        # definizione stessa (bordo piu' interno racchiuso) abbia senso.
        if nx < 2 or ny < 2:
            continue
        griglia = np.zeros((nx, ny), dtype=bool)
        griglia[celle_fetta[:, 0], celle_fetta[:, 1]] = True
        riempimenti.append(float(binary_fill_holes(griglia).mean()))
    misure = np.asarray(per_fetta, dtype=np.float64) if per_fetta else np.zeros((1, 2))
    medie = misure.mean(axis=0)
    dispersione = tuple(
        float(scarto / media) if media > 0.0 else 0.0
        for scarto, media in zip(misure.std(axis=0), medie, strict=True)
    )
    # mediana e non media: una minoranza di fette piene (ai capi, dove nella
    # Π i traversi chiudono l'ingombro per davvero) non deve nascondere la
    # maggioranza di fette vuote in mezzo
    riempimento_sezione = float(np.median(riempimenti)) if riempimenti else 0.0
    # tre stati e nessuno scarto. «non verificabile» copre i due modi in cui il
    # numero che uscirebbe misurerebbe il campionamento invece della sezione:
    # nessuna fetta con punti a sufficienza, oppure una densita' cosi' poco
    # uniforme che la sua media non e' piu' una scala e la griglia costruita su
    # di essa non risolve la parte rada. Una grandezza non misurata non e' ne'
    # piena ne' vuota, e dirlo e' l'unica cosa onesta che si possa fare qui.
    #
    # Non c'e' una seconda misura di affidabilita' per fetta, ed e' una
    # decisione presa con i numeri in mano: una regione le cui fette vedono
    # sezioni diverse fra loro e' gia' fermata da costanza_sezione, che sulla
    # stessa grandezza e' molto piu' sensibile (vedi
    # test_una_pi_meta_fitta_e_meta_rada_non_arriva_fra_le_membrature).
    if not riempimenti or densita_dispersione > cfg.density_dispersion_limit:
        riempimento_stato = "non_verificabile"
    elif riempimento_sezione >= cfg.section_fill_ratio:
        riempimento_stato = "pieno"
    else:
        riempimento_stato = "vuoto"

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
    # di sezione, non un numero. La griglia corre lungo l'asse ed e2, cosi' la
    # quota che resta libera di variare e' e1 -- la direzione trasversale del
    # pezzo intero -- ed e' quella su cui una faccia gonfiata si vede. Stesso
    # lato_fetta gia' usato sopra per dispersione e riempimento.
    piano_faccia = np.column_stack([lungo, sezione_2d[:, 1]])
    celle_faccia = chiavi_di_cella(piano_faccia, lato_fetta)
    chiave = _chiave_di_cella(celle_faccia)
    _, inverso = np.unique(chiave, return_inverse=True)
    quota = sezione_2d[:, 0]
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
        riempimento_sezione=riempimento_sezione,
        riempimento_stato=riempimento_stato,
        densita_dispersione=densita_dispersione,
    )


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
                "faccia vista da pochi punti produce un piano finto, come già "
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
                "soglia la regione non è un prisma"
            ),
        },
    }


def riempimento(membratura: Membratura, cfg: WallConfig) -> dict[str, object]:
    """L'esito del riempimento di sezione: misurato e dichiarato, mai uno scarto.

    Non e' un controllo intrinseco e non sta con gli altri tre: quelli dicono
    se una regione ha una sezione da misurare, questo dice che cosa la sezione
    misurata e' risultata essere. Tre stati, nessuno dei quali toglie la
    regione dalle membrature:

    - `pieno`: l'ingombro locale e' occupato davvero, la regione e' un prisma;
    - `vuoto`: l'ingombro non e' la sezione ma il suo contenitore -- il caso di
      due membrature uguali unite a Π, che l'estensione e la dispersione non
      vedono perche' sono entrambe misure di bounding box;
    - `non_verificabile`: la misura non ha le condizioni per valere.

    Il rifiuto spetta a chi costruisce: una membratura `vuoto` con misura
    affidabile non puo' diventare un modello parametrico, e chi lo costruisce
    trova qui tutto cio' che gli serve per dirlo senza ricalcolare nulla.
    Scartarla qui sarebbe una decisione di costruzione presa dentro uno
    strumento di misura, e per scartare senza sbagliare servirebbe una
    certezza che una nuvola reale non da'.
    """
    return {
        "stato": membratura.riempimento_stato,
        "valore": float(membratura.riempimento_sezione),
        "soglia": float(cfg.section_fill_ratio),
        "affidabile": membratura.densita_dispersione <= cfg.density_dispersion_limit,
        "densita_dispersione": float(membratura.densita_dispersione),
        "limite_densita_dispersione": float(cfg.density_dispersion_limit),
        "unita": "frazione",
        "spiegazione": (
            "frazione mediana, sulle fette lungo l'asse, delle celle del "
            "proprio ingombro locale non raggiungibili dall'esterno (bordo "
            "più interno racchiuso). Sotto la soglia lo stato è «vuoto» e la "
            "regione non è un prisma; sopra è «pieno». Lo stato "
            "«non_verificabile» dice che la misura non vale, non che il pezzo "
            "è cavo: nessuna fetta con punti a sufficienza, oppure una "
            "densità troppo poco uniforme (dispersione delle distanze al "
            "vicino più prossimo oltre il limite) perché una griglia "
            "costruita sulla loro media risolva la parte rada -- il caso di un "
            "pezzo scansionato da un lato solo. Nessuno dei tre stati scarta "
            "la regione: il riempimento misura e dichiara, e il rifiuto spetta "
            "a chi costruisce i modelli. Confine dichiarato: una membratura "
            "legittimamente cava (un tubo) risulta «vuoto», ed è corretto in "
            "questo prior, che costruisce prismi pieni"
        ),
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
    celle = chiavi_di_cella(tutti, passo)
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
    regioni_punti, metriche, puliti, tenuti, direzioni = scomponi(
        points, cfg_segment, cfg, spacing
    )
    # puliti/tenuti/direzioni vengono da scomponi, che ha gia' pagato
    # scarta_pavimento e terna: ricalcolarli qui sarebbe la stessa
    # scarta_pavimento (quindi extract_planes) e la stessa SVD una seconda
    # volta sulla nuvola intera.
    indici_pieni = np.flatnonzero(tenuti)

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
        # metriche (da scomponi) porta gia' tutte le chiavi di
        # metriche_pavimento -- scomponi le ha spalmate dentro (vedi la sua
        # `return`) -- quindi non c'e' un secondo spread da fare qui.
        **{chiave: valore for chiave, valore in metriche.items() if chiave != "terna"},
        "terna": direzioni.tolist(),
        "membrature": [
            {
                "punti": int(len(m.punti)),
                # Indici dentro la nuvola segmentata (ARTIFACTS[2]) intera, non
                # dentro `puliti`: e' quella che /api/membrature decima, e un
                # indice relativo al solo `puliti` cadrebbe su un punto diverso
                # ogni volta che il pavimento viene tolto.
                "indici": indici_pieni[m.punti].tolist(),
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
                "riempimento": riempimento(m, cfg),
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
                "unione: se differiscono, alle giunzioni il volume è contato "
                "due volte, ed è un errore che nessuna metrica di qualità "
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
                "definizione su un pezzo mai visto: dove c'è null, non c'è "
                "un'aspettativa, non c'è un valore mancante"
            ),
        },
    }
