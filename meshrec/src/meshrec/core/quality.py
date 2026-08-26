"""Metriche topologiche e geometriche su mesh triangolari e tetraedriche."""

from __future__ import annotations

import numpy as np


def finito_o_none(valore: float) -> float | None:
    """Un aggregato non finito esce come `None`, mai come `NaN`.

    JSON non ammette `NaN`: `json.dumps` lo scrive lo stesso, ma
    `JSONResponse` solleva e `/api/metrics` risponde 500, e `JSON.parse` nel
    browser si ferma su `SyntaxError`. Un campo che vale `null` dice «non
    calcolabile» e attraversa entrambi.

    E' la convenzione che `_distribution` applica gia' alle distribuzioni;
    questa funzione la estende agli scalari, che ne erano rimasti fuori --
    area, volume racchiuso, volume totale tetraedrico ed esaedrico uscivano
    `NaN` da una mesh con una coordinata non finita.
    """
    return valore if np.isfinite(valore) else None


def _edge_counts(faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spigoli unici (ordinati per indice) e numero di triangoli che li usano."""
    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.sort(edges, axis=1)
    return np.unique(edges, axis=0, return_counts=True)


def boundary_edges(faces: np.ndarray) -> np.ndarray:
    """Spigoli appartenenti a un solo triangolo: bordi aperti della mesh."""
    unique, counts = _edge_counts(np.asarray(faces))
    return unique[counts == 1]


def is_watertight(faces: np.ndarray) -> bool:
    """Vero se ogni spigolo e condiviso da esattamente due triangoli.

    Una mesh **vuota** rende `False`, non `True`. `(counts == 2).all()` su un
    array vuoto e' vacuamente vero, e quel vero attraversava il cancello di
    `volume.tetrahedralize` che esiste per fermare le superfici aperte: una
    mesh senza facce finiva a TetGen invece di essere rifiutata. Non c'e' una
    lettura utile in cui il nulla sia un solido chiuso.
    """
    _, counts = _edge_counts(np.asarray(faces))
    return bool(counts.size > 0 and (counts == 2).all())


def mesh_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Volume racchiuso, con segno positivo se le normali sono uscenti.

    Teorema della divergenza applicato ai tetraedri origine-triangolo.
    """
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def tet_volumes(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Volume con segno di ogni tetraedro; negativo se l'elemento e invertito."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a, b, c, d = n[t[:, 0]], n[t[:, 1]], n[t[:, 2]], n[t[:, 3]]
    return np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a)) / 6.0


def inverted_tets(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Indici dei tetraedri non utilizzabili: volume non finito, nullo o negativo.

    Il criterio e' scritto in positivo -- **buono se e solo se finito e
    positivo** -- e non come negazione di «non positivo». La differenza non e'
    stilistica: `nan <= 0.0` e' `False`, quindi la forma negata lasciava
    passare per sano un elemento con una coordinata `NaN`. La conseguenza,
    misurata il 26/08/2026, era che `volume.tetrahedralize` non sollevava e
    `metrics.json` scriveva `inverted: 0` su una mesh corrotta.

    Il controllo di finitezza copre anche la meta' che `not (v > 0)` da solo
    non coprirebbe: un volume `+inf` e' maggiore di zero e passerebbe.
    """
    volumes = tet_volumes(nodes, tets)
    return np.flatnonzero(~(np.isfinite(volumes) & (volumes > 0.0)))


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


# Per ciascuno degli otto nodi di un esaedro, i tre nodi adiacenti nell'ordine
# che da' determinante positivo su un cubo con la numerazione standard
# (0-3 faccia inferiore in verso antiorario, 4-7 la superiore sopra di essi).
# Verificata a mano, nodo per nodo, sul cubo unitario: tutti e otto danno +1.
_ANGOLI_ESAEDRO = (
    (1, 3, 4), (2, 0, 5), (3, 1, 6), (0, 2, 7),
    (7, 5, 0), (4, 6, 1), (5, 7, 2), (6, 4, 3),
)


def scaled_jacobian(nodes: np.ndarray, hexes: np.ndarray) -> np.ndarray:
    """Jacobiano scalato di ogni esaedro: il minimo su nove punti.

    **Nove e non otto**, come in Sandia Verdict: gli otto angoli piu' il
    **centro**, dove si usano gli assi principali medi invece di tre spigoli
    uscenti. Il nono punto e' l'unico che vede un esaedro con tutti gli spigoli
    a posto e l'interno ripiegato -- misurato, esiste un esaedro con gli otto
    angoli a 0,9155 e il centro a -0,9979. Nota: la documentazione Cubit 15.8
    dice «8 corner nodes only», il sorgente `sandialabs/verdict` ne usa nove;
    fra i due vince il sorgente.


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

    # Il nono punto: il centro dell'elemento, dove Verdict non usa tre spigoli
    # uscenti ma gli **assi principali medi** -- la somma dei quattro spigoli
    # paralleli, uno per direzione. E' l'unico punto in cui si vede se
    # l'interno e' rovesciato mentre tutti gli spigoli sono a posto.
    #
    # Non e' una raffinatezza. Misurato cercando il caso peggiore: esiste un
    # esaedro con tutti e otto gli angoli a **0,9155** -- che si legge
    # «elemento ottimo» -- e il centro a **-0,9979**, cioe' completamente
    # ripiegato dentro. Senza questo termine la funzione lo promuoveva.
    #
    # Sui magli veri il termine non vincola mai: zero scarto su 1644 esaedri di
    # tre prismi gmsh e su 148 689 cubi perturbati a caso. Aggiungerlo quindi
    # **non sposta alcun numero gia' pubblicato**, e copre il caso che la
    # ricerca mirata trova e il campionamento no.
    q = punti[h]
    assi = (
        q[:, 1] - q[:, 0] + q[:, 2] - q[:, 3] + q[:, 5] - q[:, 4] + q[:, 6] - q[:, 7],
        q[:, 3] - q[:, 0] + q[:, 2] - q[:, 1] + q[:, 7] - q[:, 4] + q[:, 6] - q[:, 5],
        q[:, 4] - q[:, 0] + q[:, 5] - q[:, 1] + q[:, 6] - q[:, 2] + q[:, 7] - q[:, 3],
    )
    determinante = np.einsum("ij,ij->i", assi[0], np.cross(assi[1], assi[2]))
    prodotto = np.prod([np.linalg.norm(asse, axis=1) for asse in assi], axis=0)
    centro = np.divide(
        determinante, prodotto, out=np.zeros_like(determinante), where=prodotto > 0.0
    )

    return np.ascontiguousarray(np.minimum(minimi, centro))


def hexa_metrics(nodes: np.ndarray, hexes: np.ndarray) -> dict[str, object]:
    """Metriche di volume di una mesh esaedrica.

    Deliberatamente **senza** min_ratio, rapporto raggio-spigolo e angolo
    diedro: sono grandezze del tetraedro, e riportarle qui accanto a quelle
    dell'esaedro inviterebbe a confrontare due colonne che non si confrontano.
    `report.confronta` mette queste metriche accanto a quelle tetraedriche in
    due colonne separate (`qualita[nome]` prende `scaled_jacobian` qui,
    `radius_edge_ratio` per l'as-built) e dichiara che la qualita' degli
    elementi non e' confrontabile fra un modello tetraedrico e uno esaedrico.
    Il suo unico chiamante e' `pipeline.genera_modello`; il confronto legge il
    risultato da `modello.json`.
    """
    volumi = hex_volumes(nodes, hexes)
    jacobiani = scaled_jacobian(nodes, hexes)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "hexes": int(len(np.asarray(hexes))),
        # Stesso criterio di `inverted_tets`, scritto nella stessa forma: buono
        # se e solo se finito e positivo. Su un nodo `NaN` il vecchio
        # `jacobiani <= 0.0` era gia' corretto per una proprieta' di
        # `scaled_jacobian`, che li' riporta 0,0; su un nodo `inf` no --
        # il jacobiano esce `NaN` e il vecchio confronto contava **zero**
        # invertiti su un esaedro corrotto.
        "inverted": int((~(np.isfinite(jacobiani) & (jacobiani > 0.0))).sum()),
        "total_volume": finito_o_none(float(volumi.sum())),
        "element_volume": _distribution(volumi),
        "scaled_jacobian": _distribution(jacobiani),
    }


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


_TET_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
# Le sei combinazioni di due indici su quattro: valgono sia come coppie di facce
# (angoli diedri) sia come spigoli del tetraedro (rapporto d'aspetto).
_FACE_PAIRS = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def triangle_aspect_ratios(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei triangoli: 1 per l'equilatero, cresce coi degeneri."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    sides = np.stack(
        [
            np.linalg.norm(b - a, axis=1),
            np.linalg.norm(c - b, axis=1),
            np.linalg.norm(a - c, axis=1),
        ],
        axis=1,
    )
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    inradius = np.where(sides.sum(axis=1) > 0.0, 2.0 * area / sides.sum(axis=1), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sides.max(axis=1) / (2.0 * np.sqrt(3.0) * inradius)
    return np.where(np.isfinite(ratio), ratio, np.inf)


def _tet_face_normals(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Normali uscenti delle quattro facce di ogni tetraedro, forma (n, 4, 3)."""
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    normals = np.empty((len(t), 4, 3), dtype=np.float64)
    for index, (i, j, k) in enumerate(_TET_FACES):
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        face = np.cross(q - p, r - p)
        length = np.linalg.norm(face, axis=1, keepdims=True)
        normals[:, index] = np.divide(face, length, out=np.zeros_like(face), where=length > 0.0)
    return normals


def min_dihedral_angles(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Angolo diedro minimo di ogni tetraedro, in gradi.

    Un tetraedro regolare vale arccos(1/3) = 70,5288 gradi; valori vicini a
    zero indicano elementi schiacciati, numericamente inaffidabili.
    """
    normals = _tet_face_normals(nodes, tets)
    angles = np.empty((len(normals), len(_FACE_PAIRS)), dtype=np.float64)
    for index, (i, j) in enumerate(_FACE_PAIRS):
        cosine = np.clip(np.einsum("ij,ij->i", normals[:, i], normals[:, j]), -1.0, 1.0)
        angles[:, index] = 180.0 - np.degrees(np.arccos(cosine))
    return angles.min(axis=1)


def tet_aspect_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Rapporto d'aspetto dei tetraedri: 1 per il regolare, cresce coi degeneri.

    **Il nome vale due grandezze diverse, e questa e' quella di Verdict**:
    spigolo massimo diviso `2*sqrt(6)` volte il raggio della sfera inscritta.
    Abaqus e CAE chiamano «aspect ratio» il rapporto fra spigolo massimo e
    minimo -- cio' che Verdict chiama invece `edge ratio`. Le due non sono
    riscalabili l'una nell'altra: sul tetraedro rettangolo di lato 1 questa
    vale `(1+sqrt(3))/2 = 1,366` e quella di Abaqus `sqrt(2) = 1,414`.

    La conseguenza pratica e' che una soglia presa da un manuale Abaqus e
    applicata a questo numero confronta due cose diverse. Il registro delle
    soglie lo dichiara sulla voce `aspect_ratio_tet`; sta anche qui perche'
    chi legge la funzione non passa necessariamente di la'.
    """
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    volume = np.abs(tet_volumes(n, t))
    area = np.zeros(len(t), dtype=np.float64)
    for i, j, k in _TET_FACES:
        p, q, r = n[t[:, i]], n[t[:, j]], n[t[:, k]]
        area += np.linalg.norm(np.cross(q - p, r - p), axis=1) / 2.0
    longest = np.max(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in _FACE_PAIRS], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        inradius = 3.0 * volume / area
        ratio = longest / (inradius * 2.0 * np.sqrt(6.0))
    return np.where(np.isfinite(ratio) & (inradius > 0.0), ratio, np.inf)


def radius_edge_ratios(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Raggio della sfera circoscritta diviso lo spigolo piu corto.

    E' la grandezza che TetGen limita con `minratio`: vale sqrt(6)/4 = 0,6124
    per il tetraedro regolare e cresce sugli elementi mal condizionati. Serve a
    verificare sul maglio prodotto un vincolo che finora era solo richiesto: dei
    parametri di TetConfig, `max_steiner_points` e `max_volume` sono controllati
    sul risultato, `min_ratio` no.

    Il centro della sfera circoscritta si ottiene risolvendo il sistema lineare
    che impone uguale distanza dai quattro vertici. Su un tetraedro degenere la
    matrice e singolare: il risultato e' infinito e non un'eccezione, cosi la
    metrica resta calcolabile su un maglio che contiene qualche elemento piatto.

    **E' cieca agli sliver, e non per approssimazione.** Uno sliver ha i
    quattro vertici vicini a una circonferenza: la sfera circoscritta resta
    piccola e gli spigoli restano lunghi, quindi il rapporto resta buono
    mentre il volume tende a zero. Misurato su quattro punti sfalsati di un
    millesimo attorno a una circonferenza di raggio 1: raggio-spigolo
    **0,707**, cioe' sotto il limite di 2,0 che TetGen impone, e angolo diedro
    minimo **0,162 gradi**. Il default `-q` di TetGen limita questo rapporto e
    pretende un diedro minimo di **zero** gradi: gli sliver sopravvivono per
    costruzione, non per caso. Chi vuole vederli guardi `min_dihedral_angles`,
    che e' l'unica grandezza del set che li coglie.
    """
    n = np.asarray(nodes, dtype=np.float64)
    t = np.asarray(tets)
    a = n[t[:, 0]]
    spigoli = np.stack([n[t[:, i]] - a for i in (1, 2, 3)], axis=1)

    # 2 (p - a) . d = |p - a|^2 per ciascuno dei tre vertici restanti, con d il
    # centro riferito ad a.
    matrice = 2.0 * spigoli
    termine = np.einsum("ijk,ijk->ij", spigoli, spigoli)

    determinante = np.linalg.det(matrice)
    regolare = np.abs(determinante) > 0.0
    centri = np.zeros((len(t), 3), dtype=np.float64)
    if regolare.any():
        # Il termine noto porta un asse finale esplicito (colonna singola):
        # senza, quando il numero di tetraedri regolari coincide con 1 o con 3
        # (la dimensione della matrice), np.linalg.solve confonde il lotto con
        # un'unica matrice 3x3 condivisa invece di risolvere un sistema per
        # tetraedro, e sbaglia in silenzio anziche' sollevare un errore.
        centri[regolare] = np.linalg.solve(
            matrice[regolare], termine[regolare, :, None]
        )[..., 0]
    raggio = np.linalg.norm(centri, axis=1)

    piu_corto = np.min(
        [np.linalg.norm(n[t[:, i]] - n[t[:, j]], axis=1) for i, j in _FACE_PAIRS], axis=0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        rapporto = raggio / piu_corto
    return np.where(regolare & (piu_corto > 0.0), rapporto, np.inf)


def _distribution(values: np.ndarray) -> dict[str, float | int | None]:
    """Riassunto di una distribuzione, per il report e per metrics.json.

    I valori non finiti sono esclusi dalle statistiche e contati in
    `non_finite`, perche' quanti se ne sono scartati e' parte del risultato: un
    riassunto calcolato su meta dei valori senza dirlo e' un numero plausibile e
    non verificabile.

    Quando non resta alcun valore finito le voci valgono `null` e non `NaN`:
    `NaN` non fa parte di JSON, e un `metrics.json` che lo contiene smette di
    essere leggibile da qualunque lettore che non sia quello di Python.
    """
    all_values = np.asarray(values, dtype=np.float64)
    finite = all_values[np.isfinite(all_values)]
    summary: dict[str, float | int | None] = {"non_finite": int(len(all_values) - len(finite))}
    if len(finite) == 0:
        return {"min": None, "median": None, "mean": None, "max": None, **summary}
    return {
        "min": float(finite.min()),
        "median": float(np.median(finite)),
        "mean": float(finite.mean()),
        "max": float(finite.max()),
        **summary,
    }


def surface_metrics(vertices: np.ndarray, faces: np.ndarray) -> dict[str, object]:
    """Step 7: chiusura, bordi, area, volume racchiuso, aspetto dei triangoli."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return {
        "vertices": int(len(v)),
        "triangles": int(len(f)),
        "watertight": is_watertight(f),
        "boundary_edges": int(len(boundary_edges(f))),
        "area": finito_o_none(float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2.0)),
        "volume": finito_o_none(mesh_volume(v, f)),
        "aspect_ratio": _distribution(triangle_aspect_ratios(v, f)),
    }


def fraction_over_ratio(nodes: np.ndarray, tets: np.ndarray, limit: float) -> float:
    """Frazione di elementi con rapporto raggio-spigolo oltre `limit`.

    `limit` e' un metro esterno e non il vincolo chiesto a TetGen: nel motore
    di sweep min_ratio e' una variabile, e contare le violazioni del proprio
    vincolo confronterebbe candidati contro vincoli diversi.

    La grandezza distingue una mesh sana da una troncata scambiata per
    riuscita: 8,10% sul muro e 9,55% su lab_frame contro l'86,36% della mesh
    tagliata dal tetto ereditato ai punti di Steiner.
    """
    ratios = radius_edge_ratios(nodes, tets)
    finite = ratios[np.isfinite(ratios)]
    return float((finite > limit).mean()) if len(finite) else 1.0


def volume_metrics(nodes: np.ndarray, tets: np.ndarray, reference_ratio: float) -> dict[str, object]:
    """Step 10: elementi invertiti, angolo diedro minimo, aspetto, volumi, raggio-spigolo.

    `reference_ratio` e' il metro fisso con cui si conta la frazione fuori
    vincolo: non ha predefinito in firma perche' il suo unico predefinito
    vive in TetConfig.
    """
    volumes = tet_volumes(nodes, tets)
    return {
        "nodes": int(len(np.asarray(nodes))),
        "tets": int(len(np.asarray(tets))),
        "inverted": int(len(inverted_tets(nodes, tets))),
        "total_volume": finito_o_none(float(volumes.sum())),
        "element_volume": _distribution(volumes),
        "min_dihedral_deg": _distribution(min_dihedral_angles(nodes, tets)),
        "aspect_ratio": _distribution(tet_aspect_ratios(nodes, tets)),
        "radius_edge_ratio": _distribution(radius_edge_ratios(nodes, tets)),
        "radius_edge_over_reference": fraction_over_ratio(nodes, tets, reference_ratio),
        "reference_ratio": float(reference_ratio),
    }


def geometric_error(
    vertices: np.ndarray, faces: np.ndarray, cloud: np.ndarray
) -> dict[str, object]:
    """Errore geometrico bidirezionale fra superficie ricostruita e nuvola sorgente.

    I due versi non misurano la stessa cosa, e la differenza conta.

    In cloud_to_mesh i campioni sono i punti della nuvola e il bersaglio e' la
    superficie con le sue facce: e' una distanza punto-superficie. Su lab_crop
    n_samples vale 4.229.538, cioe' tutti i punti.

    In mesh_to_cloud PyMeshLab campiona i **soli vertici**, e il bersaglio e'
    una nuvola, che facce non ne ha. Su lab_crop n_samples vale 213.154, cioe'
    esattamente il numero di vertici della superficie. Quel verso e' dunque una
    misura per vertice, e vertex_deviation lo riproduce esattamente.

    Il limite da tenere presente quando si legge il numero: campionare i soli
    vertici **sottostima** l'errore dove i triangoli sono grandi, non lo
    sovrastima. Se i vertici cadono sulla nuvola, cio' che la superficie
    sbaglia fra un vertice e l'altro non entra in nessun campione. La calotta
    che lo mostra non sta scritta qui in una frase ma in un test che la
    ricostruisce, coi suoi parametri dichiarati nel codice del test:
    test_su_una_calotta_il_campionamento_dei_soli_vertici_sottostima_l_errore,
    in tests/test_quality.py. La misura che quel test verifica e' la
    relazione fra le tre grandezze, non tre valori assoluti, che dipendono
    dalla geometria scelta e dalla macchina.

    Il verso della disuguaglianza fra i due numeri vale in un regime, e il
    regime va detto. cloud_to_mesh misura l'errore di corda, cioe' quanto la
    superficie si discosta dalla forma vera fra un vertice e l'altro;
    mesh_to_cloud e' una distanza punto-punto e porta con se' il pavimento
    della spaziatura della nuvola, perche' un vertice non puo' avvicinarsi a
    una nuvola discreta piu di quanto la nuvola sia fitta. Finche' l'errore di
    corda resta sopra quel pavimento, cloud_to_mesh e' il piu grande; sotto,
    il pavimento domina e il verso si rovescia
    (test_su_triangoli_piu_fini_il_verso_della_disuguaglianza_si_rovescia).

    Il metro del regime non e' il lato del triangolo contro la spaziatura:
    l'errore di corda cresce col quadrato del lato e cala col raggio di
    curvatura, e sulla stessa calotta il verso e' gia' rovesciato con
    triangoli da 6 mm contro una nuvola a passo 1 mm.

    Su lab_crop, il caso reale della tesi, il pavimento non morde: la
    spaziatura vale 1,1923 mm (chiave 01_load.spacing di metrics.json) contro
    un mesh_to_cloud RMS di 3,8984 mm (chiave
    07_surface_quality.geometric_error, verso mesh_to_cloud, campo RMS), cioe'
    3,27 volte la spaziatura.

    Il calcolo non e' cambiato e i numeri gia' pubblicati restano quelli: qui e'
    cambiata solo la loro descrizione, che diceva il contrario del vero.
    """
    import pymeshlab

    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(
        pymeshlab.Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces)), "mesh"
    )
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(cloud, dtype=np.float64)), "cloud")

    cloud_to_mesh = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=1, targetmesh=0))
    mesh_to_cloud = dict(mesh_set.apply_filter("get_hausdorff_distance", sampledmesh=0, targetmesh=1))
    for name, result in (("cloud_to_mesh", cloud_to_mesh), ("mesh_to_cloud", mesh_to_cloud)):
        missing = {"max", "RMS"} - set(result)
        if missing:
            raise RuntimeError(f"get_hausdorff_distance non ha restituito {missing} per {name}")

    return {
        "cloud_to_mesh": cloud_to_mesh,
        "mesh_to_cloud": mesh_to_cloud,
        "hausdorff": max(float(cloud_to_mesh["max"]), float(mesh_to_cloud["max"])),
    }


def vertex_deviation(vertices: np.ndarray, cloud: np.ndarray) -> np.ndarray:
    """Distanza di ogni vertice della superficie dal punto piu prossimo della nuvola.

    geometric_error restituisce soltanto aggregati, max e RMS: una mappa di
    colore ha bisogno di uno scalare per vertice. Il KD-tree e' gia' in uso in
    io.mean_spacing, quindi non entra alcuna dipendenza nuova.

    E' una distanza punto-nuvola misurata nei soli vertici, quindi
    **sottostima** l'errore dove i triangoli sono grandi: cio' che la
    superficie sbaglia fra un vertice e l'altro non entra in nessun campione.
    Serve come mappa diagnostica, non come misura di fedelta'. La calotta su
    cui la sottostima si misura sta in
    test_su_una_calotta_il_campionamento_dei_soli_vertici_sottostima_l_errore,
    che la ricostruisce dai parametri invece di citarne i valori.

    Vale anche qui il pavimento della spaziatura descritto in
    geometric_error: sotto quel pavimento questa mappa non scende, quindi su
    triangoli piu fini dell'errore di corda misura la nuvola e non la mesh.

    Non e' una seconda misura indipendente: riproduce esattamente il verso
    mesh_to_cloud di geometric_error, perche' anche PyMeshLab in quel verso
    campiona i soli vertici contro una nuvola senza facce. Su lab_crop l'RMS
    vale 3,8984 mm qui e 3,898384 mm li', e la differenza e' la precisione a
    32 bit di PyMeshLab. La misura che questa funzione non replica e'
    cloud_to_mesh, dove i campioni sono i 4.229.538 punti della nuvola, il
    bersaglio sono le facce e l'RMS vale 4,897 mm.
    """
    from scipy.spatial import cKDTree

    punti = np.asarray(cloud, dtype=np.float64)
    # Su una nuvola vuota `cKDTree.query` rende `inf` per ogni vertice, senza
    # sollevare. Quegli `inf` sono lo scalare per vertice che
    # `pipeline.genera_modello` porta alla mappa di colore: non una misura, una
    # scala rotta. Un punto solo invece e' poco ma e' una misura, e passa.
    if len(punti) == 0:
        raise ValueError(
            "nuvola vuota: nessun punto da cui misurare la distanza dei vertici"
        )
    albero = cKDTree(punti)
    distanze, _indici = albero.query(np.asarray(vertices, dtype=np.float64), k=1)
    return np.ascontiguousarray(distanze, dtype=np.float64)


def thickness(points: np.ndarray, bin_width: float) -> dict[str, object]:
    """Spessore come distanza fra i due modi lungo la direzione di minore estensione.

    Si applica indifferentemente a una nuvola e ai vertici di una superficie:
    e' il requisito che rende la misura verificabile, perche' il valore letto
    sulla ricostruzione si confronta con quello letto sulla sorgente.

    L'ingombro non risponde alla stessa domanda: e' sistematicamente piu
    grande dello spessore, perche' il rumore e gli sguinci allargano la
    scatola, non il muro. Attenzione ai sistemi di riferimento: l'ingombro
    assiale nel sistema del mondo (231 mm sul ritaglio di lab_frame, da
    fase-1-esiti-lab-frame.md) non e' la stessa grandezza di `extent`, che
    questa funzione misura lungo l'autovettore di minore estensione (237,1 mm
    sullo stesso ritaglio): due sistemi di riferimento diversi, due numeri
    diversi, nessuno dei due e' lo spessore.

    La divisione fra i due modi cade al punto medio dell'estensione, che per
    una lastra sta fra le due facce: nessuna finestra da tarare. Se fra i due
    modi non c'e' una valle la distribuzione non e' bimodale, la misura non
    e' valida e `bimodal` lo dichiara invece di restituire un numero comunque:
    su una nuvola piena i due massimi cadrebbero comunque da qualche parte, e
    la loro distanza non sarebbe uno spessore.
    """
    values = np.asarray(points, dtype=np.float64)
    if (
        len(values) < 2
        or not np.isfinite(values).all()
        or not np.isfinite(bin_width)
        or bin_width <= 0.0
    ):
        # Tre ingressi su cui l'autodecomposizione o l'istogramma non
        # girano affatto, non un errore del programma da propagare:
        # - meno di due punti, nuvola vuota compresa (np.ptp su una
        #   riduzione a zero elementi solleva ValueError);
        # - coordinate non finite (NaN, inf), che possono uscire da una
        #   ricostruzione di Poisson andata male, da una chiusura dei fori
        #   o da una stima delle normali degenere (eigh su una matrice
        #   corrotta da NaN non solleva: non converge in silenzio);
        # - bin_width non finito o non positivo: zero esce davvero da
        #   io.mean_spacing su punti duplicati esatti, e np.arange con
        #   passo zero o NaN solleva (dimensione impossibile o lunghezza
        #   incalcolabile) invece di produrre un istogramma vuoto.
        # Stesso dizionario in tutti e tre i casi: la misura non si
        # applica, mai un errore grezzo di numpy propagato al chiamante.
        return {"thickness": None, "axis": None, "extent": None, "bimodal": False}
    centred = values - values.mean(axis=0)
    # eigh su una 3x3: costo indipendente dal numero di punti, al contrario
    # di una SVD sulla matrice intera, che su 6,3 milioni di punti materializza
    # una U da oltre 150 MB per restituire le stesse tre direzioni.
    _, directions = np.linalg.eigh(centred.T @ centred)
    projected = centred @ directions
    extents = np.ptp(projected, axis=0)
    axis = int(np.argmin(extents))

    if extents[axis] / bin_width > len(values):
        # Il numero di bin che np.arange proverebbe ad allocare supera il
        # numero di punti: un istogramma con piu bin che campioni non misura
        # nulla comunque, quindi l'ingresso e' degenere quanto una nuvola
        # troppo piccola. La grandezza giusta e' questo rapporto, non una
        # soglia sul bin_width: un bin_width valido per la densita' reale dei
        # punti resta ben sotto, e senza la guardia np.arange solleverebbe
        # MemoryError provando ad allocare l'array dei bordi dei bin.
        return {"thickness": None, "axis": None, "extent": None, "bimodal": False}

    along = projected[:, axis]
    edges = np.arange(along.min(), along.max() + bin_width, bin_width)
    if len(edges) < 3:
        # Meno di due bin: la nuvola e' piatta, collineare o piu piccola del
        # passo di campionamento lungo l'asse di minore estensione. Non c'e'
        # una valle da cercare fra due meta' che non esistono entrambe:
        # np.argmax su una fetta vuota solleverebbe ValueError piu sotto.
        # bimodal lo dichiara invece di sollevare, come sul resto della nuvola
        # piena: e' un ingresso su cui la misura non si applica, non un
        # errore del programma. thickness resta None, non uno zero che fra
        # mesi si leggerebbe in una riga del registro come un numero
        # misurato invece che come un'assenza dichiarata.
        return {
            "thickness": None,
            "axis": axis,
            "extent": float(extents[axis]),
            "bimodal": False,
        }
    counts, _ = np.histogram(along, bins=edges)
    centres = (edges[:-1] + edges[1:]) / 2.0
    split = len(counts) // 2

    lower = int(np.argmax(counts[:split]))
    upper = split + int(np.argmax(counts[split:]))
    # La valle fra i due modi deve essere almeno mezza vuota rispetto al modo
    # piu basso. Non e' una soglia tarata ma un'affermazione qualitativa: se
    # fra i due massimi il conteggio non cala, non ci sono due facce.
    #
    # La media sui bin della valle, non il minimo di un solo bin: il minimo e'
    # una statistica d'ordine estremo, e su una densita' di punti bassa scende
    # per rumore di conteggio anche quando la nuvola e piena, dichiarando
    # bimodale cio' che non lo e'. La media converge alla densita' vera al
    # crescere del numero di bin nella valle, che e' la stessa leva (bin_width,
    # densita' della nuvola) su cui lo sweep della Fase 2 non da' garanzie.
    # Modi in bin **contigui**: fra i due massimi non esiste alcun bin, quindi
    # non c'e' una valle da misurare e lungo questo asse le due facce non si
    # distinguono. Sta scritto come esito e non come calcolo perche' la forma
    # precedente -- `valley = counts[lower]` e poi lo stesso confronto -- era
    # falsa per costruzione: `counts[lower] < 0.5 * min(counts[lower], ...)`
    # richiede un conteggio negativo, e un istogramma non ne ha. Il ramo
    # sembrava poter dare True e non poteva, il che e' peggio di non averlo.
    bimodal = upper > lower + 1 and bool(
        counts[lower + 1 : upper].mean() < 0.5 * min(counts[lower], counts[upper])
    )

    return {
        "thickness": float(centres[upper] - centres[lower]),
        "axis": axis,
        "extent": float(extents[axis]),
        "bimodal": bimodal,
    }


def scarto_con_segno(
    vertices: np.ndarray, faces: np.ndarray, cloud: np.ndarray, *, tolleranza: float
) -> dict[str, object]:
    """Errore geometrico **con segno**: materia inventata contro materia mancante (#73).

    `geometric_error` e `vertex_deviation` danno moduli, e un modulo non
    distingue i due modi di sbagliare, che sul modello a elementi finiti hanno
    conseguenze **opposte**: la materia inventata aggiunge massa e rigidezza
    che non ci sono, quella mancante le toglie. Un RMS di 4 mm non dice quale
    dei due, e i due spingono la frequenza propria in direzioni contrarie --
    quindi **un errore che si compensa in media sembra un errore piccolo**.

    **Convenzione, fissata qui una volta**: il segno e' quello della distanza
    dal solido chiuso, cioe' `positivo = il punto rilevato sta FUORI dalla
    superficie ricostruita`. Fuori significa che la materia c'e' nella realta'
    e non nel modello: **materia mancante**. Negativo significa il contrario:
    il modello racchiude spazio dove il rilievo trova la superficie piu'
    dentro, cioe' **materia inventata**.

    Il segno viene dal raycasting di Open3D (`RaycastingScene.
    compute_signed_distance`), non dalla proiezione sulla normale della faccia
    piu' vicina. La differenza non e' di comodo: la proiezione sbaglia il segno
    vicino agli spigoli, dove la faccia piu' vicina e' ambigua e la normale
    salta, ed e' esattamente dove una ricostruzione di Poisson tende a
    sbagliare. La convenzione di Open3D e' **misurata** e non assunta: su un
    cubo unitario il centro rende -0,5 e un punto a un mezzo sopra la faccia
    rende +0,5.

    `precision` e `recall` a `tolleranza`, che e' `errore_geometrico_max` (5 mm,
    ratificata in #35):

    - **recall** -- frazione dei punti rilevati che la superficie riproduce
      entro tolleranza. Risponde a «quanto del rilievo e' finito nel modello»;
    - **precision** -- frazione dei vertici della superficie sostenuta da un
      punto rilevato entro tolleranza. Risponde a «quanto del modello e'
      sostenuto dal dato».

    I due non sono simmetrici e nessuno dei due basta: una superficie che
    copre solo meta' del pezzo ma la copre bene ha precision alta e recall
    basso; una che gonfia il pezzo ha il contrario.

    **Limite dichiarato, lo stesso di `vertex_deviation`**: `precision` campiona
    i **soli vertici**, quindi sottostima l'errore dove i triangoli sono
    grandi. Campionare l'area richiederebbe un generatore pseudocasuale, e
    #66 ha misurato che cio' che dipende dal maglio dipende dalla piattaforma:
    un numero pubblicato non deve cambiare fra due macchine.

    **Limite dichiarato, e non risolto**: la materia «mancante» e l'**occlusione**
    qui si confondono. Lo scanner non vede dappertutto, e una zona senza punti
    puo' essere superficie mai rilevata invece che persa dalla ricostruzione.
    Separarle chiede una stima della copertura che questa funzione non fa: il
    numero va quindi letto come limite superiore della materia mancante.
    """
    punti = np.asarray(cloud, dtype=np.float64)
    vert = np.asarray(vertices, dtype=np.float64)
    facce = np.asarray(faces, dtype=np.int64)
    if not np.isfinite(tolleranza) or tolleranza <= 0.0:
        raise ValueError(
            f"la tolleranza vale {tolleranza!r}: senza una distanza positiva e finita "
            "non esiste un «entro quanto», e precision e recall non sono definite"
        )
    if len(punti) == 0 or len(facce) == 0:
        raise ValueError(
            f"nuvola di {len(punti)} punti e superficie di {len(facce)} facce: "
            "senza entrambe non c'e' uno scarto da misurare"
        )

    import open3d as o3d

    maglia = o3d.t.geometry.TriangleMesh(
        o3d.core.Tensor(vert.astype(np.float32)),
        o3d.core.Tensor(facce.astype(np.int32)),
    )
    scena = o3d.t.geometry.RaycastingScene()
    scena.add_triangles(maglia)
    con_segno = scena.compute_signed_distance(
        o3d.core.Tensor(punti.astype(np.float32))
    ).numpy().astype(np.float64)

    fuori = con_segno > 0.0
    dentro = con_segno < 0.0
    # I vertici della superficie contro la nuvola: e' il verso `mesh_to_cloud`
    # gia' usato da `vertex_deviation`, e non si riscrive.
    da_vertici = vertex_deviation(vert, punti)

    def rms(valori: np.ndarray) -> float:
        return float(np.sqrt(np.mean(valori**2))) if len(valori) else 0.0

    return {
        "tolleranza": float(tolleranza),
        "punti": int(len(punti)),
        "vertici": int(len(vert)),
        # materia mancante: il rilievo sta fuori dal modello
        "mancante_rms": rms(con_segno[fuori]),
        "mancante_max": float(con_segno[fuori].max()) if fuori.any() else 0.0,
        "mancante_frazione": float(fuori.mean()),
        # materia inventata: il modello racchiude cio' che il rilievo non vede
        "inventata_rms": rms(con_segno[dentro]),
        "inventata_max": float(-con_segno[dentro].min()) if dentro.any() else 0.0,
        "inventata_frazione": float(dentro.mean()),
        # Il bilancio con segno e' la grandezza che un RMS non puo' portare: se
        # i due modi si compensano vale circa zero mentre l'RMS resta grande, ed
        # e' precisamente il caso che questa funzione esiste per rendere
        # visibile.
        "bilancio_medio": float(np.mean(con_segno)),
        "modulo_rms": rms(con_segno),
        "recall": float(np.mean(np.abs(con_segno) <= tolleranza)),
        "precision": float(np.mean(da_vertici <= tolleranza)),
    }
