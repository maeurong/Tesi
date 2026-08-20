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
