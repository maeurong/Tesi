"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

import warnings
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
    tets: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    fixed_nset: str = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    step_name: str = "GRAVITA",
) -> None:
    """Scrive un modello pronto all'analisi statica sotto peso proprio."""
    if fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")

    nodes = np.asarray(nodes, dtype=np.float64)
    tets = np.asarray(tets, dtype=np.int64)

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE=C3D4, ELSET={elset}")
    lines += [
        f"{index + 1}, {a + 1}, {b + 1}, {c + 1}, {d + 1}"
        for index, (a, b, c, d) in enumerate(tets)
    ]

    for name, indices in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(indices)

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


_TET_FACE_COMBOS = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))


def _boundary_faces(tets: np.ndarray) -> np.ndarray:
    """Facce triangolari sul bordo della mesh tetraedrica.

    Stesso ragionamento di quality.boundary_edges, esteso alle facce
    triangolari dei tetraedri: si costruiscono le quattro facce di ogni
    tetraedro, si ordinano gli indici al loro interno, si contano le
    occorrenze e si tengono quelle con occorrenza singola.
    """
    t = np.asarray(tets, dtype=np.int64)
    faces = np.vstack([t[:, combo] for combo in _TET_FACE_COMBOS])
    faces = np.sort(faces, axis=1)
    unique, counts = np.unique(faces, axis=0, return_counts=True)
    return unique[counts == 1]


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
    """
    points = np.asarray(nodes, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    edges = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [0, 2]]]), axis=1)
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


def write_vtu(path: Path, nodes: np.ndarray, tets: np.ndarray) -> None:
    """Esportazione per la visualizzazione, delegata a meshio."""
    import meshio

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write_points_cells(
        str(path),
        np.asarray(nodes, dtype=np.float64),
        [("tetra", np.asarray(tets, dtype=np.int64))],
    )


def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    tets: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
    reference: np.ndarray | None = None,
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
    from meshrec.core.quality import tet_volumes

    if tet_cfg.element != "C3D4":
        raise NotImplementedError(
            f"elemento {tet_cfg.element} non supportato dal writer: TetGen produce i nodi "
            "di lato con order=2, ma il deck scrive quattro nodi per elemento. "
            "Usa C3D4 finche il writer non gestisce i dieci nodi."
        )

    boundary_faces = _boundary_faces(tets)
    boundary = np.unique(boundary_faces)
    if reference is None:
        reference = np.asarray(nodes, dtype=np.float64)[boundary]
    aligned, transform, align_metrics = align_to_axes(nodes, reference=reference)
    spacing = boundary_spacing(aligned, boundary_faces)
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
        tets,
        node_sets=node_sets,
        material=cfg.material,
        fixed_nset=cfg.fixed_nset,
        gravity=cfg.gravity,
        step_name=cfg.step_name,
    )
    write_vtu(path_vtu, aligned, tets)

    volume = float(np.abs(tet_volumes(aligned, tets)).sum())
    return {
        "transform": transform.tolist(),
        "extent": align_metrics["extent"],
        "boundary_spacing": float(spacing),
        "set_tolerance": float(tolerance),
        "fixed_nset_coverage": float(coverage),
        "node_sets": {name: int(len(indices)) for name, indices in node_sets.items()},
        "volume": volume,
        "mass": volume * cfg.material.density,
        "inp": str(path_inp),
        "vtu": str(path_vtu),
    }
