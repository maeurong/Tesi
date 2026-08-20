"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from pathlib import Path

import numpy as np

from meshrec.core.config import GRAVITY_MM_S2, AnalysisConfig, Material, TetConfig

_SET_ITEMS_PER_LINE = 8


class UnconstrainedModelWarning(UserWarning):
    """L'insieme vincolato raggiunge meno della meta' della superficie d'appoggio."""


def _set_lines(indices: np.ndarray) -> list[str]:
    """Indici 0-based in righe di numeri 1-based, otto per riga."""
    one_based = np.asarray(indices, dtype=np.int64) + 1
    return [
        ", ".join(str(value) for value in one_based[start : start + _SET_ITEMS_PER_LINE])
        for start in range(0, len(one_based), _SET_ITEMS_PER_LINE)
    ]


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
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str] | tuple[str, str, str, float], ...] = (),
    pressure: tuple[str, float] | None = None,
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

    `element_surfaces`, `ties` e `pressure` sono le tre aggiunte della Fase 4 e
    sono tutte facoltative: senza di esse il deck e' identico a quello che
    questa funzione scriveva prima, ed e' cosi' che le corse tetraedriche
    restano confrontabili con quelle gia' fatte. Un carico assente non diventa
    una pressione dichiarata a zero: le due cose non sono la stessa.

    Ogni tupla di `ties` e' `(nome, dipendente, indipendente)` o, con la
    `POSITION TOLERANCE` di Ruling AH (giro di correzione 6),
    `(nome, dipendente, indipendente, tolleranza)`. Un *TIE a tre elementi non
    scrive affatto quel parametro: assente non e' la stessa cosa di zero,
    stessa regola gia' vera per `pressure` qui sopra.
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
    superfici = {} if element_surfaces is None else element_surfaces
    for tie in ties:
        nome, dipendente, indipendente = tie[0], tie[1], tie[2]
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

    for name, indices in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(indices)

    for nome, coppie in superfici.items():
        lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={nome}")
        lines += [f"{elemento + 1}, S{numero}" for elemento, numero in coppie]

    for tie in ties:
        nome, dipendente, indipendente = tie[0], tie[1], tie[2]
        # ADJUST=NO: spostare i nodi della superficie dipendente sulla
        # indipendente cambierebbe la geometria dopo che il volume e' stato
        # misurato, e il modello non sarebbe piu' quello di cui il report parla.
        # POSITION TOLERANCE (Ruling AH), solo se data: assente non e' zero.
        tolleranza_card = f", POSITION TOLERANCE={tie[3]}" if len(tie) > 3 else ""
        lines.append(f"*TIE, NAME={nome}{tolleranza_card}, ADJUST=NO")
        lines.append(f"{dipendente}, {indipendente}")

    lines += [
        f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC",
        f"{material.young}, {material.poisson}",
        "*DENSITY",
        f"{material.density:.9g}",
        "*BOUNDARY",
        f"{fixed_nset}, 1, 3",
        f"*STEP, NAME={step_name}",
        "*STATIC",
        "*DLOAD",
        f"{elset}, GRAV, {gravity}, 0.0, 0.0, -1.0",
    ]
    if pressure is not None:
        lines += ["*DSLOAD", f"{pressure[0]}, P, {pressure[1]}"]

    for name in print_nsets:
        lines += [f"*NODE PRINT, NSET={name}", "U"]

    lines += [
        "*OUTPUT, FIELD",
        "*NODE OUTPUT",
        "U",
        "*ELEMENT OUTPUT",
        "S, E",
        "*END STEP",
        "",
    ]

    Path(path).write_text("\n".join(lines), encoding="ascii")


def fix_sign(direction: np.ndarray) -> np.ndarray:
    """Convenzione deterministica di segno: componente di modulo massimo positiva.

    Le direzioni principali restituite dalla SVD hanno segno arbitrario: senza
    una convenzione, due esecuzioni sulla stessa nuvola possono produrre assi
    opposti e quindi set di faccia scambiati.

    Pubblica dalla Fase 4: `wall.terna` deve fissare il segno delle proprie
    direzioni con la stessa convenzione con cui `align_to_axes` fissa le sue,
    o due moduli dello stesso programma sceglierebbero versi opposti sulla
    stessa geometria.
    """
    direction = np.asarray(direction, dtype=np.float64)
    return direction if direction[int(np.argmax(np.abs(direction)))] >= 0.0 else -direction


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
    """Le coppie (elemento, numero di faccia) di bordo le cui facce cadono nell'insieme dato.

    Una faccia entra nella superficie solo se **tutti** i suoi nodi stanno
    nell'insieme: tre nodi su quattro non sono quella faccia, e nominarla
    applicherebbe un carico dove l'utente non lo ha chiesto.

    Una faccia interna, condivisa da due elementi adiacenti, non entra mai:
    e' contata due volte nella tabella (una per elemento) e viene esclusa allo
    stesso modo di `boundary_faces`, per occorrenza. Senza questo filtro un
    *TIE o un carico laterale su una selezione di nodi larga finirebbero
    applicati dentro il solido, non sulla sua pelle.

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

    combinazioni = FACCE_DEL_SOLUTORE[angoli]
    nodi_per_faccia = len(combinazioni[0])
    # (n_elementi, n_facce, nodi_per_faccia): ogni faccia di ogni elemento, coi suoi nodi.
    facce = np.stack([elementi[:, list(combo)] for combo in combinazioni], axis=1)
    ordinate = np.sort(facce, axis=2).reshape(-1, nodi_per_faccia)
    _, inverso, conteggi = np.unique(ordinate, axis=0, return_inverse=True, return_counts=True)
    di_bordo = (conteggi[inverso.reshape(-1)] == 1).reshape(facce.shape[0], facce.shape[1])

    coppie: list[tuple[int, int]] = []
    for posizione in range(len(combinazioni)):
        tutte_dentro = dentro[facce[:, posizione, :]].all(axis=1) & di_bordo[:, posizione]
        coppie += [(int(indice), posizione + 1) for indice in np.flatnonzero(tutte_dentro)]
    coppie.sort()
    return coppie


def tie_surface(
    nodes: np.ndarray,
    elements: np.ndarray,
    dentro_altro: Callable[[np.ndarray], np.ndarray],
    element_type: str,
    *,
    tocca: bool = False,
) -> list[tuple[int, int]]:
    """Le coppie (elemento, numero di faccia) di bordo il cui baricentro cade dentro l'altro solido.

    Criterio diverso da `element_surface` apposta, per una ragione fisica e
    non stilistica: un `*TIE` lega due superfici che si toccano, e il
    contatto e' una questione di **area sovrapposta**, non di nodi
    coincidenti -- le due mesh ai lati di una giunzione (Ruling AE) sono
    generate indipendentemente e non condividono nodi, quindi pretendere che
    tutti e quattro i nodi di una faccia cadano dentro l'altro solido
    escluderebbe facce che si toccano davvero solo perche' un angolo e' appena
    fuori. Un carico invece si applica dove l'utente lo ha nominato, e li'
    l'ambiguita' non e' ammessa: e' per questo che `element_surface` resta
    quella che e', non si tocca, e questa e' una funzione a parte.

    `tocca=True` (Ruling AH, giro di correzione 6): una faccia entra anche se
    il baricentro e' fuori ma **almeno uno dei suoi nodi** e' dentro. Misurato
    sul telaio a quattro membrature: il lato indipendente ha facce piu'
    grandi (la sua mesh e' piu' rada), e una faccia cosi' puo' coprire solo in
    parte la zona di contatto -- il baricentro cade fuori pur toccando
    davvero, e i nodi dipendenti sopra quella zona restano senza una faccia su
    cui proiettarsi. Il lato dipendente resta a `tocca=False` (il predefinito):
    sulla faccia di taglio, gia' piana per costruzione, il solo baricentro e'
    gia' quello giusto -- misurato che allargarlo anche li' peggiora, non
    migliora, il risultato (esperimento B3 del giro 6: scambiare i ruoli fa
    salire gli avvisi del solutore da 20 a 58).

    `dentro_altro` e' la geometria iniettata come funzione (punti -> booleani)
    e non un import di `hexa.Prisma`/`hexa.dentro`: `abaqus.py` non dipende da
    `hexa.py`, che gia' importa `abaqus.py`, e importare nell'altro verso
    creerebbe un ciclo.

    Solo facce di bordo (`boundary_faces`, non toccata): una faccia interna,
    condivisa da due elementi, non e' pelle e non puo' stare in una
    superficie, qui come in `element_surface`.
    """
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{element_type}' sconosciuto")
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = 8 if NODI_PER_ELEMENTO[element_type] == 8 else 4

    combinazioni = FACCE_DEL_SOLUTORE[angoli]
    nodi_per_faccia = len(combinazioni[0])
    facce = np.stack([elementi[:, list(combo)] for combo in combinazioni], axis=1)
    ordinate = np.sort(facce, axis=2).reshape(-1, nodi_per_faccia)
    bordo_uniche = {tuple(riga) for riga in np.sort(boundary_faces(elementi), axis=1).tolist()}
    di_bordo = np.array(
        [tuple(riga) in bordo_uniche for riga in ordinate.tolist()], dtype=bool
    ).reshape(facce.shape[0], facce.shape[1])

    baricentri = punti[facce].mean(axis=2)  # (n_elementi, n_facce, 3)
    forma = baricentri.shape[:2]
    dentro = dentro_altro(baricentri.reshape(-1, 3)).reshape(forma)
    if tocca:
        dentro_nodi = dentro_altro(punti[facce].reshape(-1, 3)).reshape(
            facce.shape[0], facce.shape[1], nodi_per_faccia
        )
        dentro = dentro | dentro_nodi.any(axis=2)

    coppie: list[tuple[int, int]] = []
    for posizione in range(len(combinazioni)):
        selezionate = dentro[:, posizione] & di_bordo[:, posizione]
        coppie += [(int(indice), posizione + 1) for indice in np.flatnonzero(selezionate)]
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

# Nodi d'angolo per numero di colonne dell'array: un C3D10 ha dieci colonne
# ma la topologia di faccia e' quella del tetraedro (le prime quattro sono i
# vertici). Mappa esplicita e non un ternario: un conteggio non previsto deve
# fermarsi con un errore, non essere trattato come tetraedro per default.
_ANGOLI_PER_COLONNE: dict[int, int] = {4: 4, 8: 8, 10: 4}


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
    colonne = elementi.shape[1]
    if colonne not in _ANGOLI_PER_COLONNE:
        raise ValueError(
            f"elemento con {colonne} nodi: nessuna topologia di faccia definita per questa forma"
        )
    combinazioni = FACCE_TOPOLOGICHE[_ANGOLI_PER_COLONNE[colonne]]
    facce = np.vstack([elementi[:, combo] for combo in combinazioni])
    facce = np.sort(facce, axis=1)
    uniche, conteggi = np.unique(facce, axis=0, return_counts=True)
    return uniche[conteggi == 1]


# Il nome privato resta come alias per non toccare i chiamanti interni gia'
# scritti e verificati: e' la stessa funzione, non una seconda.
_boundary_faces = boundary_faces


def _boundary_nodes(tets: np.ndarray) -> np.ndarray:
    """Indici dei nodi sul bordo della mesh tetraedrica.

    I punti di Steiner interni aggiunti da TetGen compaiono solo in facce
    condivise da due tetraedri e restano quindi esclusi.
    """
    return np.unique(_boundary_faces(tets))


def boundary_spacing(nodes: np.ndarray, faces: np.ndarray) -> float:
    """Mediana della lunghezza degli spigoli delle facce di bordo date.

    E' la scala geometrica del maglio dove i set vengono estratti, e non va
    confusa con quella della superficie riparata da cui il maglio deriva: con
    `tet.nobisect` falso TetGen suddivide le facce di ingresso, e sul muro di
    riferimento il bordo del maglio di volume risulta 2,4 volte piu fitto
    della superficie (13,73 mm contro 33,55 mm).

    Dalla Fase 4 vale anche sulle facce quadrilatere della mesh esaedrica: gli
    spigoli sono le coppie consecutive lungo il perimetro, quale che sia il
    numero di lati.
    """
    points = np.asarray(nodes, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    # Gli spigoli di una faccia sono le coppie di nodi consecutivi lungo il suo
    # perimetro: np.roll li da' per un triangolo come per un quadrilatero,
    # senza una tabella per grado.
    edges = np.sort(
        np.vstack([np.stack([f[:, i], f[:, (i + 1) % f.shape[1]]], axis=1) for i in range(f.shape[1])]),
        axis=1,
    )
    edges = np.unique(edges, axis=0)
    return float(np.median(np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)))


def align_to_axes(
    nodes: np.ndarray, reference: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Rototraslazione ai piani principali: spessore su x, lunghezza su y, altezza su z.

    La trasformazione e' restituita come matrice 4x4 e va salvata nei metadati:
    e' l'unico modo per riportare i risultati nel sistema originale dello scanner.

    Assunzione: lo scanner e' livellato, cioe' la z della nuvola in ingresso
    e' gia' il verticale reale e l'unica ambiguita' e' l'imbardata. Se la
    nuvola e' inclinata fuori dal piano orizzontale (beccheggio o rollio),
    l'assegnazione dell'asse altezza non e' garantita.

    `reference`, se fornito, e' l'insieme di punti su cui stimare centro e
    direzioni principali; in sua assenza si usano i nodi stessi. Il
    riferimento e' una proprieta della geometria e non del maglio, e la
    distinzione non e' teorica: la stima e' una PCA che pesa ogni punto allo
    stesso modo, mentre la densita dei nodi dipende da dove il raffinamento
    ha infittito, cioe' da un artefatto. Misurato sul muro reale: stimando
    sui nodi del volume la prima direzione principale si scosta di 21,44
    gradi dal verticale, e di 15,33 anche restringendosi ai soli nodi di
    bordo, mentre sui vertici della superficie ricostruita lo scarto e' di
    0,45 gradi.

    La trasformazione si applica comunque a tutti i nodi passati, e lo
    scostamento al primo ottante si calcola sui nodi trasformati, non sul
    riferimento: BASE deve corrispondere alla base del solido, quindi la
    quota minima a valere zero e' quella dei nodi.
    """
    points = np.asarray(nodes, dtype=np.float64)
    reference = points if reference is None else np.asarray(reference, dtype=np.float64)
    centre = reference.mean(axis=0)
    centred = points - centre
    centred_reference = reference - centre

    _, _, principal = np.linalg.svd(centred_reference, full_matrices=False)
    extents = np.ptp(centred_reference @ principal.T, axis=0)

    thickness_axis = int(np.argmin(extents))
    remaining = [index for index in range(3) if index != thickness_axis]
    # fra le due direzioni restanti, l'altezza e' quella piu vicina al verticale
    # originale: la gravita agisce lungo il verticale reale, non lungo l'asse
    # con l'estensione maggiore.
    verticality = [abs(principal[index][2]) for index in remaining]
    height_axis = remaining[int(np.argmax(verticality))]

    vertical = principal[height_axis]
    # L'altezza punta verso l'alto del sistema originale: la gravita agisce
    # lungo il verticale reale, e BASE deve restare l'estremita fisicamente
    # piu bassa. Se la nuvola e' quasi coricata il prodotto scalare non decide,
    # e si ricade sulla convenzione di segno deterministica.
    if abs(vertical[2]) > 1e-6:
        z_dir = vertical if vertical[2] > 0.0 else -vertical
    else:
        z_dir = fix_sign(vertical)

    x_dir = fix_sign(principal[thickness_axis])
    # y come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori, che
    # cambierebbe il verso di un asse gia deciso.
    y_dir = np.cross(z_dir, x_dir)

    rotation = np.stack([x_dir, y_dir, z_dir])

    aligned = centred @ rotation.T
    shift = aligned.min(axis=0)
    aligned = aligned - shift

    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ centre - shift

    metrics = {
        "extent": (aligned.max(axis=0) - aligned.min(axis=0)).tolist(),
        "transform": transform.tolist(),
    }
    return np.ascontiguousarray(aligned), transform, metrics


def set_tolerance(nodes: np.ndarray, tets: np.ndarray, factor: float) -> float:
    """Tolleranza dei set: un multiplo della spaziatura dei nodi sul bordo.

    L'euristica precedente derivava dal volume medio dell'elemento, cioe' da un
    artefatto del raffinamento e non dalla geometria: su una distribuzione a
    coda pesante la media e' dominata da pochi tetraedri enormi dell'interno
    (sul muro di riferimento mediana 14,6 mm^3 contro media 30.735 mm^3). Il
    costo e' misurato: `BASE` raggiungeva il 55,78% della superficie che poggia
    davvero a terra sul muro e il 34,76% su lab_crop.

    Le due candidate note sono state misurate e respinte, ciascuna da un
    numero. Il volume mediano dell'elemento da' 2,50 mm di tolleranza e un
    `BASE` di 9 nodi su 420.547. La selezione per direzione della normale, che
    e' lo standard dei preprocessori, e' catastrofica su una scansione con
    aperture: l'87,8% dell'area di lab_crop rivolta verso il basso e'
    l'intradosso dell'architrave, a 1493,5 mm su 1693,99 di altezza, e
    finirebbe in `BASE`.

    La scala giusta e' quella su cui la faccia ricostruita ondula, che e' la
    scala del campionamento e non quella del solido: misurata in spaziature,
    l'ondulazione trasferisce fra i due modelli entro un fattore 1,79, mentre
    misurata in frazioni dell'estensione entro un fattore 3,2. Misura completa,
    criterio di accettazione e sweep del fattore in
    docs/fase-1-tolleranza-set.md.
    """
    return factor * boundary_spacing(nodes, _boundary_faces(tets))


def footprint_coverage(
    nodes: np.ndarray, boundary: np.ndarray, indices: np.ndarray, spacing: float
) -> float:
    """Frazione della superficie d'appoggio che l'insieme dato raggiunge davvero.

    Contare i nodi di un insieme non dice se copra la faccia che deve coprire:
    possono stare tutti ammucchiati in un angolo. 4738 nodi su una faccia
    coperta al 55,78% e 4738 su una coperta al 100% sono lo stesso numero.

    L'impronta viene divisa in celle quadrate di lato `4 * spacing`. Una
    colonna e' *a contatto* se il suo nodo di bordo piu basso cade entro il 2%
    dell'altezza dal minimo globale, cioe' se in quel punto il solido tocca
    davvero il piano d'appoggio; il risultato e' la frazione di colonne a
    contatto che contengono almeno un nodo dell'insieme.

    Il lato `4 * spacing` non e' arbitrario: con una cella larga quanto la
    spaziatura la griglia diventa piu fine dei triangoli della faccia inferiore
    (su quella del muro il p95 degli spigoli vale 47,4 mm contro una mediana di
    13,7) e una colonna su dieci risulta priva di nodi bassi per puro artefatto
    di griglia. Misurato, e scartato per questo.

    La misura ha tre parametri impliciti — il lato della cella, la banda di
    contatto e l'asse — ed e' per questo che serve come diagnosi e non come
    regola: la tolleranza dei set ne ha uno solo.
    """
    points = np.asarray(nodes, dtype=np.float64)
    edge = np.asarray(boundary, dtype=np.int64)
    low = points.min(axis=0)
    height = float(points[:, 2].max() - low[2])

    cell = np.floor((points[edge, :2] - low[:2]) / (4.0 * spacing)).astype(np.int64)
    # Chiave intera invece di np.unique(..., axis=0): stesso risultato, e su un
    # maglio a scala reale costa un terzo. Le celle sono non negative perche'
    # misurate dal minimo.
    key = cell[:, 0] * (cell[:, 1].max() + 1) + cell[:, 1]
    _, inverse = np.unique(key, return_inverse=True)
    columns = int(inverse.max()) + 1

    floor_height = np.full(columns, np.inf)
    np.minimum.at(floor_height, inverse, points[edge, 2])
    in_contact = floor_height <= low[2] + 0.02 * height
    if not in_contact.any():
        return 0.0

    in_set = np.zeros(len(points), dtype=bool)
    in_set[np.asarray(indices, dtype=np.int64)] = True
    reached = np.bincount(inverse, weights=in_set[edge], minlength=columns) > 0
    return float(reached[in_contact].mean())


def build_node_sets(nodes: np.ndarray, tolerance: float) -> dict[str, np.ndarray]:
    """I sei set di faccia, sul modello gia allineato agli assi.

    `BASE` e `TOP` sono verificati: l'asse z e' il verticale reale (vedi
    `align_to_axes`), quindi il minimo e' davvero la base del solido.

    `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT` e `SIDE_RIGHT` sono invece **nomi di
    convenzione**, non identificazioni fisiche. Sono assegnati al minimo e al
    massimo di x e di y dopo l'allineamento, e nulla nella pipeline sa quale
    delle due grandi facce sia quella «anteriore» del muro reale, ne' quale sia
    il lato «sinistro»: il segno degli assi viene da una convenzione
    deterministica (`fix_sign`), scelta per la ripetibilita, non da un
    riferimento sul campo. La coppia e' quindi affidabile come coppia (le due
    facce opposte sono quelle giuste), l'attribuzione del singolo nome no.
    Chiunque usi questi set per confrontare il modello con misure fatte sul muro
    deve prima verificare l'orientamento sul file allineato.
    """
    points = np.asarray(nodes, dtype=np.float64)
    low = points.min(axis=0)
    high = points.max(axis=0)
    return {
        "BASE": np.flatnonzero(points[:, 2] <= low[2] + tolerance),
        "TOP": np.flatnonzero(points[:, 2] >= high[2] - tolerance),
        "FACE_FRONT": np.flatnonzero(points[:, 0] <= low[0] + tolerance),
        "FACE_BACK": np.flatnonzero(points[:, 0] >= high[0] - tolerance),
        "SIDE_LEFT": np.flatnonzero(points[:, 1] <= low[1] + tolerance),
        "SIDE_RIGHT": np.flatnonzero(points[:, 1] >= high[1] - tolerance),
    }


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
    """Step 11: allinea, costruisce i set, scrive il deck e il file di visualizzazione.

    `reference` sono i punti su cui stimare la terna: la pipeline passa i
    vertici della superficie da cui la mesh e' stata generata, perche' il
    sistema di riferimento e' una proprieta della geometria e non del maglio.
    Senza riferimento si ripiega sui nodi di bordo della mesh di volume, che
    e' il comportamento precedente e resta valido sulle geometrie di prova,
    dove i nodi coincidono con la superficie.

    Su dati reali quel ripiego non e' valido, ed e' ora misurato: sul muro di
    riferimento la terna stimata sui nodi di bordo si scosta di 15,33 gradi dal
    verticale, `BASE` scende da 18.020 nodi a 874 e la copertura della
    superficie d'appoggio dal 100,00% al 44,23% — abbastanza da far scattare
    UnconstrainedModelWarning. Chi chiama questa funzione su una scansione deve
    passare `reference`.
    """
    from meshrec.core.quality import element_volumes

    tipo = tet_cfg.element if element_type is None else element_type
    if tipo == "C3D10":
        raise NotImplementedError(
            "elemento C3D10 non supportato dal writer: TetGen produce i nodi di "
            "lato con order=2, ma il deck scrive i soli vertici. Usa C3D4 finche' "
            "il writer non gestisce i dieci nodi."
        )
    if tipo not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{tipo}' sconosciuto")
    attesi = NODI_PER_ELEMENTO[tipo]
    elements = np.asarray(elements, dtype=np.int64)
    if elements.shape[1] != attesi:
        raise ValueError(
            f"{tipo} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: un deck scritto cosi' non e' leggibile da alcun solutore"
        )

    # Nome distinto dalla funzione pubblica boundary_faces: qui e' una
    # variabile locale, non va confusa col contratto che questo task ha
    # promosso (vedi Task 5, 7, 8).
    bordo_facce = _boundary_faces(elements)
    boundary = np.unique(bordo_facce)
    if reference is None:
        reference = np.asarray(nodes, dtype=np.float64)[boundary]
    aligned, transform, align_metrics = align_to_axes(nodes, reference=reference)
    spacing = boundary_spacing(aligned, bordo_facce)
    tolerance = cfg.set_tolerance_factor * spacing
    node_sets = build_node_sets(aligned, tolerance)
    if len(node_sets[cfg.fixed_nset]) == 0:
        raise ValueError(f"il set vincolato '{cfg.fixed_nset}' e vuoto: tolleranza {tolerance:.3f} mm troppo stretta")

    # La guardia sul set vuoto era cieca su tutto il resto: un `BASE` da 9 nodi
    # produce un deck formalmente valido per un modello di fatto non vincolato,
    # e nessuna metrica confrontava la taglia dell'insieme con la faccia che
    # deve coprire. La soglia e' la meta', che non e' un numero tarato ma
    # un'affermazione qualitativa: quando la superficie d'appoggio vincolata e'
    # meno di quella libera, il modello non e' vincolato in alcun senso utile.
    # Avrebbe segnalato entrambe le corse sotto l'euristica precedente
    # (55,78% sul muro e 34,76% su lab_crop), e tace sotto quella attuale
    # (100,00% e 98,93%).
    coverage = footprint_coverage(aligned, boundary, node_sets[cfg.fixed_nset], spacing)
    if coverage <= 0.5:
        warnings.warn(
            f"l'insieme vincolato '{cfg.fixed_nset}' raggiunge il {coverage:.2%} della "
            f"superficie d'appoggio con una tolleranza di {tolerance:.3f} mm: il modello "
            "e' vincolato su una chiazza, non sulla base. Alza "
            "analysis.set_tolerance_factor o verifica la geometria.",
            UnconstrainedModelWarning,
            stacklevel=2,
        )

    write_inp(
        path_inp,
        aligned,
        elements,
        node_sets=node_sets,
        material=cfg.material,
        element_type=tipo,
        fixed_nset=cfg.fixed_nset,
        gravity=cfg.gravity,
        step_name=cfg.step_name,
    )
    write_vtu(path_vtu, aligned, elements, element_type=tipo)

    volume = float(np.abs(element_volumes(aligned, elements)).sum())
    return {
        "transform": transform.tolist(),
        "extent": align_metrics["extent"],
        "boundary_spacing": float(spacing),
        "set_tolerance": float(tolerance),
        "fixed_nset_coverage": float(coverage),
        "node_sets": {name: int(len(indices)) for name, indices in node_sets.items()},
        "volume": volume,
        "mass": volume * cfg.material.density,
        "element_type": tipo,
        "inp": str(path_inp),
        "vtu": str(path_vtu),
    }
