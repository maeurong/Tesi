import inspect
import json

import numpy as np
import pytest

from meshrec.core import quality, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_box_mesh_has_eight_vertices_and_twelve_triangles():
    vertices, faces = synth.box_mesh(SIZE)

    assert vertices.shape == (8, 3)
    assert faces.shape == (12, 3)
    assert vertices.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert vertices.max(axis=0) == pytest.approx(list(SIZE))


def test_box_mesh_is_watertight_and_has_no_boundary_edges():
    _, faces = synth.box_mesh(SIZE)

    assert len(quality.boundary_edges(faces)) == 0
    assert quality.is_watertight(faces)


def test_box_mesh_volume_is_exact_and_positive():
    vertices, faces = synth.box_mesh(SIZE)

    assert quality.mesh_volume(vertices, faces) == pytest.approx(EXACT_VOLUME)


def test_punch_holes_opens_the_mesh():
    _, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    assert len(damaged) == 10
    # triangoli 0 e 6 condividono spigolo (1,2): sono adiacenti, quindi 4 spigoli di bordo
    assert len(quality.boundary_edges(damaged)) == 4
    assert not quality.is_watertight(damaged)


def test_regular_tetrahedron_has_the_textbook_dihedral_angle():
    """Il tetraedro regolare ha tutti i diedri a arccos(1/3) = 70,5288 gradi."""
    nodes = np.array(
        [[1.0, 1.0, 1.0], [1.0, -1.0, -1.0], [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] == pytest.approx(70.5288, abs=1e-3)


def test_flattened_tetrahedron_has_a_small_dihedral_angle():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.001]])
    tets = np.array([[0, 1, 2, 3]])
    assert quality.min_dihedral_angles(nodes, tets)[0] < 1.0


def test_aspect_ratio_of_an_equilateral_triangle_is_one():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, np.sqrt(3.0) / 2.0, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] == pytest.approx(1.0, abs=1e-6)


def test_aspect_ratio_of_a_sliver_triangle_is_large():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.001, 0.0]])
    faces = np.array([[0, 1, 2]])
    assert quality.triangle_aspect_ratios(vertices, faces)[0] > 100.0


def test_surface_metrics_on_a_closed_box():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, faces)
    assert metrics["watertight"] is True
    assert metrics["boundary_edges"] == 0
    assert metrics["volume"] == pytest.approx(100.0 * 40.0 * 200.0)
    assert metrics["area"] == pytest.approx(2 * (100 * 40 + 100 * 200 + 40 * 200))
    assert metrics["triangles"] == 12


def test_surface_metrics_on_a_punched_box_reports_the_opening():
    vertices, faces = synth.box_mesh((100.0, 40.0, 200.0))
    metrics = quality.surface_metrics(vertices, synth.punch_holes(faces))
    assert metrics["watertight"] is False
    assert metrics["boundary_edges"] == 4


def test_volume_metrics_flag_inverted_elements():
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    good = np.array([[0, 1, 2, 3]])
    flipped = np.array([[0, 2, 1, 3]])
    assert quality.volume_metrics(nodes, good, reference_ratio=1.8)["inverted"] == 0
    assert quality.volume_metrics(nodes, flipped, reference_ratio=1.8)["inverted"] == 1


def test_geometric_error_of_a_cloud_sampled_on_its_own_mesh_is_small():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0)

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] < 1.0
    assert error["cloud_to_mesh"]["RMS"] < 1.0
    assert error["mesh_to_cloud"]["max"] < 6.0


def test_geometric_error_grows_with_a_displaced_cloud():
    pytest.importorskip("pymeshlab")
    size = (100.0, 40.0, 200.0)
    vertices, faces = synth.box_mesh(size)
    cloud = synth.sample_box_surface(size, 5.0) + np.array([0.0, 0.0, 10.0])

    error = quality.geometric_error(vertices, faces, cloud)

    assert error["cloud_to_mesh"]["max"] > 5.0


def test_a_summary_without_finite_values_stays_valid_json():
    """`NaN` non fa parte di JSON: un metrics.json che lo contiene non si rilegge.

    Il riassunto dichiara anche quanti valori ha scartato, perche' una statistica
    calcolata su una frazione dei valori senza dirlo e' un numero plausibile e
    non verificabile.
    """
    summary = quality._distribution(np.array([np.nan, np.inf, -np.inf]))

    assert summary == {"min": None, "median": None, "mean": None, "max": None, "non_finite": 3}
    assert json.loads(json.dumps(summary)) == summary

    partial = quality._distribution(np.array([1.0, np.nan, 3.0]))
    assert partial["non_finite"] == 1
    assert partial["median"] == pytest.approx(2.0)


def test_radius_edge_ratio_of_the_regular_tetrahedron():
    """Il tetraedro regolare vale sqrt(6)/4: e' il minimo possibile."""
    nodi = np.array(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ]
    )
    tetraedri = np.array([[0, 1, 2, 3]])

    rapporti = quality.radius_edge_ratios(nodi, tetraedri)

    assert rapporti == pytest.approx([np.sqrt(6.0) / 4.0], rel=1e-9)


def test_radius_edge_ratio_grows_on_a_flattened_tetrahedron():
    """Uno schiacciato ha rapporto alto: e' la grandezza che min_ratio limita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.001]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert quality.radius_edge_ratios(nodi, tetraedri)[0] > 10.0


def test_a_degenerate_tetrahedron_is_infinite_not_a_crash():
    """Quattro punti complanari: nessuna sfera circoscritta finita."""
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]])
    tetraedri = np.array([[0, 1, 2, 3]])

    assert not np.isfinite(quality.radius_edge_ratios(nodi, tetraedri)[0])


def test_thickness_measures_the_distance_between_the_two_faces():
    """Su una lastra campionata su entrambe le facce lo spessore e' la distanza fra i modi.

    L'ingombro non risponde alla stessa domanda: con rumore sulle facce e'
    sistematicamente piu grande della distanza fra i piani medi, ed e' il
    motivo per cui la misura e' un istogramma e non un bounding box.
    """
    rng = np.random.default_rng(0)
    n = 20_000
    y = rng.normal(0.0, 2.0, n) + np.where(rng.random(n) < 0.5, 0.0, 176.0)
    points = np.column_stack([rng.uniform(0.0, 2700.0, n), y, rng.uniform(0.0, 2000.0, n)])

    measured = quality.thickness(points, bin_width=1.0)

    assert measured["bimodal"] is True
    assert measured["thickness"] == pytest.approx(176.0, abs=3.0)
    assert measured["extent"] > measured["thickness"]


def test_thickness_declares_itself_invalid_on_a_solid_without_two_faces():
    """Una nuvola piena non ha due modi: la misura lo dichiara invece di restituire un numero."""
    rng = np.random.default_rng(1)
    # n grande per tenere il rumore di conteggio per bin sotto la soglia della
    # valle: con 5.000 punti (media ~56 per bin) capita per caso un avvallamento
    # che supera il 50% e fa dichiarare bimodale una nuvola piena.
    points = rng.uniform(0.0, 1.0, (50_000, 3)) * np.array([2700.0, 176.0, 2000.0])

    measured = quality.thickness(points, bin_width=2.0)

    assert measured["bimodal"] is False


def test_thickness_declares_itself_invalid_on_a_degenerate_cloud_instead_of_raising():
    """Tre punti piatti non danno due meta' popolate: np.argmax su una fetta
    vuota solleverebbe ValueError senza la guardia sul numero di bin.

    E' l'ingresso che ha fatto sollevare measure_thickness_error su una mesh
    degenere: la guardia sta qui perche' thickness e' chiamata sia dal
    cancello sulla nuvola sorgente sia dalla misura sulla superficie riparata.

    thickness deve restituire None, non uno zero: uno zero sembrerebbe una
    misura letta in una riga del registro, invece di un'assenza dichiarata.
    """
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

    measured = quality.thickness(points, bin_width=1.0)

    assert measured["bimodal"] is False
    assert measured["thickness"] is None


def test_thickness_declares_itself_invalid_on_a_cloud_with_a_nan_vertex():
    """Un vertice non finito puo' uscire da una ricostruzione di Poisson andata
    male, da una chiusura dei fori o da una stima delle normali degenere.

    eigh su una matrice corrotta da NaN non solleva: non converge in
    silenzio (LinAlgError). La guardia sui valori finiti deve intercettarlo
    prima che il calcolo delle direzioni principali lo raggiunga.
    """
    points = np.array([[np.nan, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    measured = quality.thickness(points, bin_width=1.0)

    assert measured["bimodal"] is False
    assert measured["thickness"] is None


def test_thickness_declares_itself_invalid_on_fewer_than_two_points():
    """Nuvola vuota compresa: np.ptp su una riduzione a zero elementi
    solleverebbe ValueError prima di arrivare all'istogramma."""
    assert quality.thickness(np.zeros((0, 3)), bin_width=1.0)["bimodal"] is False
    assert quality.thickness(np.zeros((0, 3)), bin_width=1.0)["thickness"] is None
    assert quality.thickness(np.array([[0.0, 0.0, 0.0]]), bin_width=1.0)["bimodal"] is False


def test_thickness_declares_itself_invalid_on_a_bad_bin_width():
    """bin_width zero esce davvero da io.mean_spacing su punti duplicati
    esatti: np.arange con passo zero o NaN solleva invece di produrre un
    istogramma vuoto, e measure_thickness_error lo passa qui senza guardia
    propria perche' e' un float valido, non una chiave mancante."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    for bin_width in (0.0, -1.0, float("nan"), float("inf")):
        measured = quality.thickness(points, bin_width=bin_width)
        assert measured["bimodal"] is False
        assert measured["thickness"] is None


def test_thickness_declares_itself_invalid_instead_of_exhausting_memory_on_a_tiny_bin_width():
    """Un bin_width minuscolo rispetto all'estensione fa provare a np.arange
    l'allocazione di un array enorme (MemoryError), pur essendo finito e
    positivo, quindi passa tutte le guardie precedenti. La grandezza giusta
    e' il numero di bin contro il numero di punti: un istogramma con piu bin
    che campioni non misura nulla comunque."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1000.0, 0.0, 1.0]])

    measured = quality.thickness(points, bin_width=1e-6)

    assert measured == {"thickness": None, "axis": None, "extent": None, "bimodal": False}


def test_the_reference_fraction_does_not_depend_on_the_requested_min_ratio():
    """L'asse di qualita' del fronte usa un metro unico per tutti i candidati.

    Se contasse gli elementi che violano il min_ratio richiesto da ciascun
    candidato, un candidato lasco supererebbe facilmente un vincolo lasco e
    il confronto sarebbe privo di senso.
    """
    nodes = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
    )
    tets = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])

    lasco = quality.fraction_over_ratio(nodes, tets, limit=100.0)
    severo = quality.fraction_over_ratio(nodes, tets, limit=0.1)

    assert lasco == pytest.approx(0.0)
    assert severo == pytest.approx(1.0)
    assert quality.volume_metrics(nodes, tets, reference_ratio=100.0)[
        "radius_edge_over_reference"
    ] == pytest.approx(0.0)


def test_la_deviazione_per_vertice_e_zero_sui_vertici_della_nuvola_e_nota_fuori():
    """Meta' dei vertici sono punti della nuvola, meta' sono sollevati di 0,25 mm.

    Il solo controllo sullo zero non distingueva questa funzione da una che
    restituisce sempre zero. Lo scostamento di 0,25 mm sta ben sotto la
    distanza tipica fra due punti della nuvola (5.000 punti in un cubo di
    100 mm di lato: circa 3,2 mm), quindi il punto piu vicino a un vertice
    sollevato resta quello da cui e' stato preso e la distanza attesa e'
    esattamente 0,25 mm.
    """
    nuvola = np.random.default_rng(0).random((5_000, 3)) * 100.0
    vertici = nuvola[:100].copy()
    vertici[50:, 2] += 0.25
    campo = quality.vertex_deviation(vertici, nuvola)
    assert campo.shape == (100,)
    assert campo[:50].max() == pytest.approx(0.0, abs=1e-12)
    assert campo[50:] == pytest.approx(np.full(50, 0.25), abs=1e-9)


def test_la_deviazione_per_vertice_misura_lo_scostamento_noto():
    nuvola = np.zeros((500, 3))
    nuvola[:, 0] = np.linspace(0.0, 100.0, 500)
    vertici = nuvola[:10].copy()
    vertici[:, 2] += 3.0     # sollevati di 3 mm esatti
    campo = quality.vertex_deviation(vertici, nuvola)
    assert campo == pytest.approx(np.full(10, 3.0), abs=1e-9)


def _griglia_piana(lato: float, passo: float) -> tuple[np.ndarray, np.ndarray]:
    """Piano z = 0 triangolato con passo regolare: triangoli piccoli e uguali.

    Serve al confronto con geometric_error: su triangoli grandi le due misure
    divergono per costruzione, e il confronto non direbbe nulla.
    """
    n = int(round(lato / passo)) + 1
    x, y = np.meshgrid(np.linspace(0.0, lato, n), np.linspace(0.0, lato, n), indexing="ij")
    vertici = np.column_stack([x.ravel(), y.ravel(), np.zeros(n * n)])
    i, j = np.meshgrid(np.arange(n - 1), np.arange(n - 1), indexing="ij")
    angolo = (i * n + j).ravel()
    triangoli = np.column_stack(
        [angolo, angolo + n, angolo + n + 1, angolo, angolo + n + 1, angolo + 1]
    ).reshape(-1, 3)
    return vertici, triangoli


def test_il_campo_per_vertice_resta_nell_ordine_di_grandezza_dell_aggregato():
    """Il controllo che smentisce: il campo per vertice deve restare vicino
    all'aggregato gia' pubblicato, `geometric_error`.

    Le due misure non coincidono per costruzione: `vertex_deviation` e' una
    distanza punto-nuvola calcolata sui soli vertici, `geometric_error` una
    distanza punto-superficie con la superficie campionata da PyMeshLab. Il
    verso confrontabile e' `mesh_to_cloud`, che parte anch'esso dalla
    superficie e cerca il punto piu vicino della nuvola.

    Margine dichiarato: un fattore due sul rapporto fra i due RMS. La
    geometria e' scelta perche' il margine sia onesto (triangoli da 5 mm
    contro una nuvola a passo 1 mm), e il residuo atteso e' solo lo
    scostamento nel piano fra un campione qualunque della superficie e il
    punto di griglia piu vicino. Se un giorno le due misure divergono di un
    fattore dieci, qualcosa e' cambiato e il fattore due se ne accorge.
    """
    pytest.importorskip("pymeshlab")
    vertici, triangoli = _griglia_piana(100.0, 5.0)
    piano, _ = _griglia_piana(100.0, 1.0)
    nuvola = piano + np.array([0.0, 0.0, 0.5])   # sollevata di 0,5 mm esatti

    campo = quality.vertex_deviation(vertici, nuvola)
    rms_campo = float(np.sqrt(np.mean(campo**2)))
    aggregato = float(quality.geometric_error(vertici, triangoli, nuvola)["mesh_to_cloud"]["RMS"])

    assert rms_campo == pytest.approx(0.5, abs=1e-9)
    assert 0.5 < rms_campo / aggregato < 2.0


def _calotta(
    raggio: float, semilato: float, passo: float, scarto: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Calotta sferica: griglia in pianta di lato 2*semilato sollevata sulla sfera.

    La griglia ha passo `passo` ed e' traslata di `scarto` prima del
    sollevamento z = sqrt(raggio^2 - x^2 - y^2). Lo scarto serve a sfasare la
    nuvola rispetto ai vertici della mesh: con un passo della mesh multiplo di
    quello della nuvola i vertici cadrebbero esattamente sui punti e
    mesh_to_cloud misurerebbe zero per costruzione, non per merito della mesh.
    """
    vertici, triangoli = _griglia_piana(2.0 * semilato, passo)
    vertici[:, :2] += scarto - semilato
    vertici[:, 2] = np.sqrt(raggio**2 - vertici[:, 0] ** 2 - vertici[:, 1] ** 2)
    return vertici, triangoli


def _errore_di_corda(vertici: np.ndarray, triangoli: np.ndarray, raggio: float) -> float:
    """Scostamento massimo della sfera dal piano dei triangoli, in forma chiusa.

    Con i tre vertici sulla sfera il piano del triangolo taglia un cerchio di
    raggio pari al circoraggio rho = abc/(4A) e dista sqrt(R^2 - rho^2) dal
    centro: la sfera se ne discosta al massimo di R - sqrt(R^2 - rho^2), sopra
    il circocentro. Nessun campionamento e nessuna tolleranza da tarare: e'
    l'errore geometrico vero della calotta fra un vertice e l'altro.
    """
    a, b, c = vertici[triangoli[:, 0]], vertici[triangoli[:, 1]], vertici[triangoli[:, 2]]
    lati = np.stack(
        [
            np.linalg.norm(b - c, axis=1),
            np.linalg.norm(a - c, axis=1),
            np.linalg.norm(a - b, axis=1),
        ],
        axis=1,
    )
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    circoraggio = lati.prod(axis=1) / (4.0 * area)
    return float((raggio - np.sqrt(raggio**2 - circoraggio**2)).max())


def test_su_una_calotta_il_campionamento_dei_soli_vertici_sottostima_l_errore():
    """La geometria che la docstring di geometric_error affermava a parole.

    Calotta di raggio 200 mm su un quadrato in pianta di 160x160 mm, mesh a
    passo 40 mm (25 vertici, 32 triangoli), nuvola a passo 1 mm sfasata di
    0,5 mm in x e in y (25.921 punti, tutti sulla stessa sfera). Valori letti
    su questa macchina: vertex_deviation RMS 0,7227 mm, mesh_to_cloud RMS
    0,7227 mm con n_samples 25, cloud_to_mesh RMS 1,4866 mm, errore di corda
    2,4936 mm contro un cloud_to_mesh max misurato di 2,4671 mm.

    Fissate sono le relazioni, non i valori: fissare i valori fisserebbe
    questa macchina invece della proprieta'. La terza relazione e' quella che
    prova la sottostima; le prime due la sostengono, e se un giorno
    mesh_to_cloud smettesse di campionare i soli vertici diventa rossa la
    prima e la conclusione della docstring va riscritta.
    """
    pytest.importorskip("pymeshlab")
    raggio, semilato = 200.0, 80.0
    vertici, triangoli = _calotta(raggio, semilato, 40.0)
    nuvola, _ = _calotta(raggio, semilato, 1.0, scarto=0.5)

    campo = quality.vertex_deviation(vertici, nuvola)
    errore = quality.geometric_error(vertici, triangoli, nuvola)
    mesh_verso_nuvola = errore["mesh_to_cloud"]
    nuvola_verso_mesh = errore["cloud_to_mesh"]
    corda = _errore_di_corda(vertici, triangoli, raggio)

    # 1. mesh_to_cloud campiona i soli vertici: e' vertex_deviation.
    rms_campo = float(np.sqrt(np.mean(campo**2)))
    assert mesh_verso_nuvola["n_samples"] == len(vertici)
    assert rms_campo == pytest.approx(float(mesh_verso_nuvola["RMS"]), rel=1e-5)
    assert campo.max() == pytest.approx(float(mesh_verso_nuvola["max"]), rel=1e-5)

    # 2. il verso che campiona le facce e' il piu grande.
    assert float(nuvola_verso_mesh["RMS"]) > float(mesh_verso_nuvola["RMS"])

    # 3. l'errore vero, calcolato in forma chiusa, sta sopra entrambi: e' la
    #    sottostima. Il confronto col massimo misurato da cloud_to_mesh vale
    #    da controprova che la forma chiusa descriva questa calotta e non
    #    un'altra.
    assert corda > float(mesh_verso_nuvola["RMS"])
    assert corda == pytest.approx(float(nuvola_verso_mesh["max"]), rel=0.05)


def test_su_triangoli_piu_fini_il_verso_della_disuguaglianza_si_rovescia():
    """Il regime in cui la relazione vale, esibito dal caso in cui non vale.

    Stessa calotta e stessa nuvola del test precedente, mesh a passo 6 mm
    (784 vertici, 1.458 triangoli). Valori letti su questa macchina:
    mesh_to_cloud RMS 0,4410 mm, cloud_to_mesh RMS 0,0684 mm, errore di corda
    0,0644 mm contro una nuvola a passo 1 mm.

    cloud_to_mesh e' una distanza punto-superficie e misura l'errore di corda;
    mesh_to_cloud e' una distanza punto-punto e porta con se' il pavimento
    della spaziatura della nuvola. Quando l'errore di corda scende sotto quel
    pavimento il pavimento domina e il verso si capovolge. Il metro non e' il
    lato del triangolo contro la spaziatura: qui il lato vale sei volte la
    spaziatura e il verso e' gia' rovesciato, perche' l'errore di corda cresce
    col quadrato del lato e cala col raggio di curvatura.
    """
    pytest.importorskip("pymeshlab")
    raggio, semilato = 200.0, 80.0
    vertici, triangoli = _calotta(raggio, semilato, 6.0)
    nuvola, _ = _calotta(raggio, semilato, 1.0, scarto=0.5)

    errore = quality.geometric_error(vertici, triangoli, nuvola)
    corda = _errore_di_corda(vertici, triangoli, raggio)

    assert corda < 1.0   # sotto il passo della nuvola: il pavimento domina
    assert float(errore["cloud_to_mesh"]["RMS"]) < float(errore["mesh_to_cloud"]["RMS"])


def test_the_reference_ratio_default_lives_in_config():
    from meshrec.core import config

    assert config.TetConfig().reference_ratio == pytest.approx(1.8)
    parameters = inspect.signature(quality.volume_metrics).parameters
    assert parameters["reference_ratio"].default is inspect.Parameter.empty
