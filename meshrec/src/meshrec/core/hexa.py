"""I modelli parametrici: prismi di membratura in mesh esaedrica.

hexa.py **costruisce e non misura**: riceve da wall.py sezioni, assi e
lunghezze gia' misurati e ne fa una mesh. Il confine con wall.py non e'
estetico, e' cio' che rende ciascuno dei due verificabile da solo contro una
geometria a verita' nota.

La mesh esaedrica si fa con gmsh, che dalla Fase 4 e' una dipendenza vera e non
un extra: superficie piana dal contorno, ricombinazione in quadrilateri,
estrusione a strati. Il modulo non riscrive `gmsh_backend.py`, che genera mesh
tetraedriche da una STL ed e' un'altra macchina; ne riprende pero' due
abitudini, perche' sono state pagate: la rimappatura dei tag di nodo su indici
di array, e l'inizializzazione per tentativo con il `finalize` in un `finally`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meshrec.core.config import ModelConfig

_ARROTONDAMENTO = 6
"""Cifre decimali su cui i nodi sono confrontati per l'ordine canonico.

Non e' una tolleranza geometrica: e' la risoluzione oltre la quale due
coordinate prodotte dalla stessa costruzione differiscono solo per l'ultimo
bit. In millimetri, un nanometro.
"""


def passo_di_mesh(contorno: np.ndarray, cfg: ModelConfig) -> float:
    """Passo caratteristico che rispetta il vincolo degli strati nello spessore.

    Il vincolo e' imposto dal codice e non suggerito: con uno o due strati la
    flessione nello spessore non e' rappresentata, e il risultato e' sbagliato
    senza alcun segnale. Il passo chiesto in configurazione, se c'e', viene
    quindi ridotto fin dove serve, mai alzato.
    """
    punti = np.asarray(contorno, dtype=np.float64)
    minima = float(np.min(np.ptp(punti, axis=0)))
    if minima <= 0.0:
        raise ValueError(
            f"il contorno ha estensione nulla su un asse (minima={minima!r} mm): "
            "non e' una sezione valida per un prisma"
        )
    tetto = minima / cfg.min_layers
    if cfg.target_size is None:
        return tetto
    return min(float(cfg.target_size), tetto)


def ordine_canonico(nodi: np.ndarray, esaedri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Riordina nodi ed elementi in un ordine funzione delle sole coordinate.

    I tag di gmsh sono un ordine di generazione, non un dato della geometria, e
    un conteggio o un indice che ne dipendesse dipenderebbe dalla piattaforma:
    e' la stessa lezione gia' pagata sull'ordine dei voxel di Open3D fra
    Windows x86-64 e macOS arm64 (quinto vincolo di prodotto).

    L'ordine **interno** dei nodi di un esaedro non si tocca: e' la topologia
    dell'elemento, e riordinarlo cambierebbe il solido invece del suo nome.
    Si riordinano i nodi fra loro e gli elementi fra loro.
    """
    punti = np.asarray(nodi, dtype=np.float64)
    elementi = np.asarray(esaedri, dtype=np.int64)

    chiave = np.round(punti, _ARROTONDAMENTO)
    # lexsort ordina per l'ultima chiave data: (z, y, x) ordina per x, poi y, poi z
    permutazione = np.lexsort((chiave[:, 2], chiave[:, 1], chiave[:, 0]))
    posizione = np.empty(len(punti), dtype=np.int64)
    posizione[permutazione] = np.arange(len(punti))

    rimappati = posizione[elementi]
    # gli elementi si ordinano per la tupla dei propri nodi rimappati, che e'
    # un numero della geometria; lexsort vuole le chiavi dall'ultima alla prima
    ordine = np.lexsort(rimappati.T[::-1])
    return np.ascontiguousarray(punti[permutazione]), np.ascontiguousarray(rimappati[ordine])


def _area_poligono(contorno: np.ndarray) -> float:
    """Area con segno di un poligono chiuso, formula di Gauss."""
    x, y = np.asarray(contorno, dtype=np.float64).T
    return float(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _base_del_piano(asse: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Due versori ortogonali all'asse, scelti in modo deterministico.

    Il riferimento e' l'asse coordinato meno allineato all'asse del prisma:
    sceglierlo dal dato invece che a caso rende la base la stessa su due
    esecuzioni, e quindi la mesh la stessa.
    """
    versore = np.asarray(asse, dtype=np.float64)
    versore = versore / np.linalg.norm(versore)
    candidati = np.eye(3)
    riferimento = candidati[int(np.argmin(np.abs(candidati @ versore)))]
    e1 = riferimento - versore * np.dot(riferimento, versore)
    e1 = e1 / np.linalg.norm(e1)
    return e1, np.cross(versore, e1)


def mesh_prisma(
    contorno: np.ndarray,
    origine: np.ndarray,
    asse: np.ndarray,
    lunghezza: float,
    cfg: ModelConfig,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Un prisma retto in esaedri: contorno di sezione estruso lungo l'asse.

    La sagoma viene costruita nel piano locale, ricombinata in quadrilateri ed
    estrusa a strati; solo alla fine il prisma viene ruotato e traslato al
    proprio posto. Costruire in locale e trasformare con numpy tiene fuori da
    gmsh ogni scelta di riferimento, che e' l'unica parte di questa funzione da
    cui potrebbe entrare una dipendenza dalla piattaforma.

    Il contorno e' orientato in senso antiorario prima di essere passato a
    gmsh: con l'orientazione opposta l'estrusione produce esaedri rovesciati,
    con Jacobiano negativo, e nessuna metrica della mesh lo direbbe guardandola.

    Restituisce nodi, esaedri e metriche, con nodi ed elementi gia' in ordine
    canonico.
    """
    if float(lunghezza) <= 0.0:
        raise ValueError(
            f"lunghezza={lunghezza!r} non e' positiva: un prisma richiede "
            "un'estrusione di lunghezza maggiore di zero"
        )

    import gmsh

    sagoma = np.asarray(contorno, dtype=np.float64)
    if _area_poligono(sagoma) < 0.0:
        sagoma = sagoma[::-1]
    area = abs(_area_poligono(sagoma))
    passo = passo_di_mesh(sagoma, cfg)
    strati = max(cfg.min_layers, int(round(float(lunghezza) / passo)))

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        punti = [gmsh.model.geo.addPoint(u, v, 0.0, passo) for u, v in sagoma]
        linee = [
            gmsh.model.geo.addLine(punti[indice], punti[(indice + 1) % len(punti)])
            for indice in range(len(punti))
        ]
        anello = gmsh.model.geo.addCurveLoop(linee)
        superficie = gmsh.model.geo.addPlaneSurface([anello])
        gmsh.model.geo.mesh.setRecombine(2, superficie)
        gmsh.model.geo.extrude(
            [(2, superficie)], 0.0, 0.0, float(lunghezza),
            numElements=[strati], recombine=True,
        )
        gmsh.model.geo.synchronize()
        # A impedire i prismi a base triangolare e' Mesh.RecombineAll=1 sotto,
        # non setRecombine sulla superficie sopra: verificato per mutazione,
        # togliendo setRecombine il risultato non cambia (832 esaedri, stesso
        # numero), mentre senza RecombineAll=1 o senza recombine=True
        # nell'estrusione gmsh non genera piu' esaedri puri, cioe' un elemento
        # che il deck non sa scrivere. setRecombine resta comunque a fissare
        # l'intento sulla faccia sorgente, che RecombineAll applica solo a
        # valle sull'intero maglio.
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMax", passo)
        gmsh.option.setNumber("Mesh.MeshSizeMin", passo)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.model.mesh.generate(3)

        tag_nodi, coordinate, _ = gmsh.model.mesh.getNodes()
        tipi, _, per_elemento = gmsh.model.mesh.getElements(3)
        if 5 not in list(tipi):
            raise RuntimeError(
                "gmsh non ha prodotto esaedri (tipo 5): la ricombinazione della "
                "sagoma non e' riuscita, e un modello a prismi triangolari non e' "
                "quello che il deck dichiara"
            )
        tag_esaedri = np.asarray(
            per_elemento[list(tipi).index(5)], dtype=np.int64
        ).reshape(-1, 8)
        versione = gmsh.option.getString("General.Version")
    finally:
        gmsh.finalize()

    tag_nodi = np.asarray(tag_nodi, dtype=np.int64)
    locali = np.ascontiguousarray(np.asarray(coordinate, dtype=np.float64).reshape(-1, 3))
    # I tag dei nodi sono 1-based e non contigui: senza rimappatura gli elementi
    # punterebbero a posizioni sbagliate dell'array, e la mesh sarebbe sbagliata
    # senza alcun segnale. Stessa cautela di gmsh_backend._extract_mesh.
    tavola = np.zeros(tag_nodi.max() + 1, dtype=np.int64)
    tavola[tag_nodi] = np.arange(len(tag_nodi))
    esaedri = np.ascontiguousarray(tavola[tag_esaedri])

    e1, e2 = _base_del_piano(asse)
    versore = np.asarray(asse, dtype=np.float64)
    versore = versore / np.linalg.norm(versore)
    rotazione = np.stack([e1, e2, versore])
    nodi = np.asarray(origine, dtype=np.float64) + locali @ rotazione

    nodi, esaedri = ordine_canonico(nodi, esaedri)
    metriche = {
        "hexes": int(len(esaedri)),
        "nodes": int(len(nodi)),
        "passo": float(passo),
        "strati": int(strati),
        "area_sezione": float(area),
        "volume_analitico": float(area * lunghezza),
        "gmsh_version": versione,
    }
    return nodi, esaedri, metriche


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
