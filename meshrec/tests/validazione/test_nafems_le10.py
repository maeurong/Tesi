"""NAFEMS LE10: piastra spessa a pianta ellittica anulare sotto pressione.

Ticket https://github.com/maeurong/Tesi/issues/48. La scheda completa, letta
dalle fonti, sta in `docs/validazione/benchmark-nafems.md` §3.

**Il benchmark statico per solidi tridimensionali.** LE1 e FV32 sono piani e
non esercitano un esportatore di solidi; LE2 vuole gusci; LE11 e' testato da
Abaqus solo su C3D20 e non offre termine di paragone per tetraedri. LE10 si',
e per entrambi i gradi.

**La geometria non c'era.** `synth` sapeva fare solo scatole: il quarto di
anello ellittico e' stato aggiunto per questo benchmark, con l'estrusione a
strati che serve a mettere nodi sul **piano di mezzeria** -- il vincolo di LE10
li richiede, e un'estrusione a due sole quote non li avrebbe.

**I vincoli sono per singolo grado**, e non erano esprimibili prima che il
patch test (#46) insegnasse a `write_inp` gli spostamenti imposti:

- faccia `y = 0` (DCD'C'): `u_y = 0`
- faccia `x = 0` (ABA'B'): `u_x = 0`
- faccia ellittica esterna (BCB'C'): `u_x = u_y = 0`
- **solo la linea di mezzeria** di quella faccia: anche `u_z = 0`

**La trappola, dichiarata dalla scheda stessa.** ESRD annota: *«Since constraints
along a line are incompatible with 3D-elasticity, the StressCheck results were
obtained by fixing the z-displacement of the face BCB'C'»*. Chi vincola tutta la
faccia invece della sola linea **non sta piu' risolvendo LE10**. Qui si vincola
la linea, ed e' l'unico insieme con tutti e tre i gradi bloccati -- quindi fa da
`fixed_nset`.

**Il target e' numerico.** sigma_yy = -5,38 MPa nel punto D, e la scheda lo
qualifica «(mesh refinement)»: non e' una soluzione in forma chiusa, quindi
nessuna soglia costruita su di esso puo' essere piu' stretta della sua stessa
incertezza.

**Non e' uno studio di convergenza, e Abaqus spiega perche'.** Il suo C3D10
sbaglia **meno** sulla maglia rada (+1,15%) che su quella fine (+7,24%), e la
ragione e' scritta nel manuale: nel punto d'angolo la maglia rada fa convergere
quattro elementi, quella fine uno solo, e l'estrapolazione ai nodi peggiora.
L'errore non e' dell'elemento ma della lettura in uno spigolo.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import Material

pytestmark = pytest.mark.validazione

# Unita' di progetto: la scheda e' in metri e GPa, qui mm e MPa.
A_INTERNO, B_INTERNO = 2000.0, 1000.0
A_ESTERNO, B_ESTERNO = 3250.0, 2750.0
SPESSORE = 600.0
PRESSIONE = 1.0  # MPa sulla superficie superiore
MATERIALE = Material(name="LE10", young=210_000.0, poisson=0.3, density=7.8e-9)

PUNTO_D = np.array([A_INTERNO, 0.0, SPESSORE])
TARGET = -5.38  # MPa, sigma_yy in D. Target **numerico**, non forma chiusa.

# Termini di paragone pubblicati, sigma_yy in D [MPa].
ABAQUS_C3D10 = {"rada": -5.44, "fine": -5.77}
SIMSCALE_TET_LINEARI = -5.08010  # Code_Aster, 63.381 nodi, errore -5,57%

TOLLERANZA = 1e-6


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _provino(order: int, passo: float, segmenti: int = 48):
    vertici, facce = synth.elliptical_annulus_mesh(
        (A_INTERNO, B_INTERNO), (A_ESTERNO, B_ESTERNO), SPESSORE,
        segments=segmenti, layers=2,
    )
    return volume.tetrahedralize(
        vertici, facce,
        max_volume=passo**3 / 6.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=order,
    )


def _sull_ellisse_esterna(nodi: np.ndarray) -> np.ndarray:
    """Vero per i nodi della faccia ellittica esterna.

    Il contorno e' poligonale, quindi quei nodi stanno su corde e cadono
    **appena dentro** l'ellisse: il criterio e' una soglia sotto 1, non
    l'uguaglianza. Le due ellissi sono lontane -- la piu' vicina vale 0,38 in
    questa misura -- quindi 0,95 separa senza ambiguita'.
    """
    return (nodi[:, 0] / A_ESTERNO) ** 2 + (nodi[:, 1] / B_ESTERNO) ** 2 > 0.95


def _vincoli(nodi: np.ndarray) -> tuple[np.ndarray, dict[int, dict[int, float]]]:
    """La linea di mezzeria (tutti e tre i gradi) e gli spostamenti per grado."""
    x, y, z = nodi[:, 0], nodi[:, 1], nodi[:, 2]
    esterna = _sull_ellisse_esterna(nodi)
    mezzeria = esterna & (np.abs(z - SPESSORE / 2.0) < TOLLERANZA)
    assert mezzeria.sum() >= 8, (
        f"solo {mezzeria.sum()} nodi sulla linea di mezzeria esterna: senza quelli il "
        "vincolo verticale di LE10 non e' esprimibile"
    )

    imposti: dict[int, dict[int, float]] = {}
    for indice in np.flatnonzero(y < TOLLERANZA):
        imposti.setdefault(int(indice), {})[2] = 0.0     # faccia y = 0
    for indice in np.flatnonzero(x < TOLLERANZA):
        imposti.setdefault(int(indice), {})[1] = 0.0     # faccia x = 0
    for indice in np.flatnonzero(esterna):
        imposti.setdefault(int(indice), {}).update({1: 0.0, 2: 0.0})
    # I nodi della linea di mezzeria escono dagli spostamenti imposti: li
    # blocca `fixed_nset` in tutti e tre i gradi, e dichiarare due volte lo
    # stesso grado sullo stesso nodo e' un deck che si contraddice.
    for indice in np.flatnonzero(mezzeria):
        imposti.pop(int(indice), None)
    return np.flatnonzero(mezzeria), imposti


def _sigma_yy_in_d(tmp_path, order: int, tipo: str, passo: float) -> tuple[float, int, int]:
    eseguibile = _ccx_o_salta()
    nodi, tets = _provino(order, passo)
    linea, imposti = _vincoli(nodi)

    superiore = np.flatnonzero(np.abs(nodi[:, 2] - SPESSORE) < TOLLERANZA)
    caricata = abaqus.element_surface(tets, superiore, tipo)
    assert caricata, "nessuna faccia di elemento sulla superficie superiore"

    abaqus.write_inp(
        tmp_path / "le10.inp", nodi, tets,
        material=MATERIALE, element_type=tipo,
        node_sets={"MEZZERIA": linea, "TUTTI": np.arange(len(nodi))},
        fixed_nset="MEZZERIA",
        spostamenti_imposti=imposti,
        element_surfaces={"CARICATA": caricata},
        pressure=("CARICATA", PRESSIONE),
        gravity=0.0,
    )
    esito = subprocess.run(
        [eseguibile, "-i", "le10"],
        cwd=tmp_path, capture_output=True, text=True, timeout=3600,
    )
    assert esito.returncode == 0, esito.stdout[-3000:] + esito.stderr[-3000:]

    blocchi = [b for b in solve.leggi_frd(tmp_path / "le10.frd") if b.grandezza == "STRESS"]
    assert blocchi, "nessun blocco STRESS nel .frd"
    blocco = blocchi[-1]

    distanze = np.linalg.norm(nodi[blocco.nodi - 1] - PUNTO_D, axis=1)
    piu_vicino = int(np.argmin(distanze))
    assert distanze[piu_vicino] < TOLLERANZA, (
        f"il nodo piu' vicino a D dista {distanze[piu_vicino]:.3f} mm: D e' un vertice "
        "della geometria e deve essere un nodo, non un'approssimazione"
    )
    # Colonna 1 = SYY. L'ordine delle colonne e' verificato contro ccx in
    # `test_ordine_frd.py` (#39), non assunto.
    return float(blocco.dati[piu_vicino, 1]), len(nodi), len(tets)


def test_la_geometria_e_chiusa_e_del_volume_giusto():
    """Prima del benchmark, il provino.

    Il volume del poligono inscritto sta **sotto** quello dell'ellisse, e lo
    scarto va come l'inverso del quadrato delle suddivisioni: e' geometria, non
    un errore, ma va dichiarato perche' il confronto di LE10 e' su una tensione
    e la tensione dipende dalla forma del bordo.
    """
    from meshrec.core import quality

    vertici, facce = synth.elliptical_annulus_mesh(
        (A_INTERNO, B_INTERNO), (A_ESTERNO, B_ESTERNO), SPESSORE, segments=48, layers=2
    )
    assert quality.is_watertight(facce)
    esatto = np.pi * (A_ESTERNO * B_ESTERNO - A_INTERNO * B_INTERNO) / 4.0 * SPESSORE
    scarto = (quality.mesh_volume(vertici, facce) - esatto) / esatto
    print(f"\nvolume del poligono inscritto: {scarto:+.4%} rispetto all'ellisse")
    assert -0.001 < scarto < 0.0, (
        f"scarto {scarto:+.4%}: un poligono inscritto sta sotto, e di poco"
    )


def test_il_generatore_rifiuta_le_geometrie_impossibili():
    """Ingressi degeneri, con il loro oracolo."""
    buono = dict(inner=(A_INTERNO, B_INTERNO), outer=(A_ESTERNO, B_ESTERNO), thickness=SPESSORE)
    with pytest.raises(ValueError, match="arco"):
        synth.elliptical_annulus_mesh(**buono, segments=2)
    with pytest.raises(ValueError, match="spessore"):
        synth.elliptical_annulus_mesh(
            inner=(A_INTERNO, B_INTERNO), outer=(A_ESTERNO, B_ESTERNO),
            thickness=0.0, segments=12,
        )
    with pytest.raises(ValueError, match="autointersec"):
        synth.elliptical_annulus_mesh(
            inner=(A_ESTERNO, B_ESTERNO), outer=(A_INTERNO, B_INTERNO),
            thickness=SPESSORE, segments=12,
        )
    with pytest.raises(ValueError, match="strati"):
        synth.elliptical_annulus_mesh(**buono, segments=12, layers=0)


@pytest.mark.parametrize(("order", "tipo"), [(1, "C3D4"), (2, "C3D10")])
def test_sigma_yy_nel_punto_d(tmp_path, order, tipo):
    """Il benchmark. sigma_yy in D contro il target numerico NAFEMS.

    Il confronto non e' «coincide» ma «sta nel mondo dei solutori che lo hanno
    pubblicato»: Abaqus con C3D10 sbaglia dall'1,15% al 7,24% a seconda della
    maglia, e SimScale con tetraedri lineari del -5,57%.
    """
    valore, n_nodi, n_tet = _sigma_yy_in_d(tmp_path, order, tipo, passo=400.0)
    scarto = (valore - TARGET) / abs(TARGET)
    print(
        f"\n[{tipo}] sigma_yy in D = {valore:.4f} MPa | target {TARGET} | "
        f"scarto {scarto:+.2%} | nodi {n_nodi} tet {n_tet}"
    )
    print(
        f"  paragoni pubblicati: Abaqus C3D10 {ABAQUS_C3D10['rada']} (rada) e "
        f"{ABAQUS_C3D10['fine']} (fine); SimScale tet lineari {SIMSCALE_TET_LINEARI}"
    )

    assert valore < 0.0, "sigma_yy in D e' di compressione: il segno e' meta' del risultato"
    assert abs(scarto) < 0.35, (
        f"scarto {scarto:+.1%} dal target: fuori dal mondo dei solutori pubblicati, "
        "che su questo benchmark stanno fra -5,6% e +9,5%"
    )


def test_raffinando_l_errore_in_d_non_e_detto_che_cali(tmp_path):
    """Abaqus documenta che su LE10 il suo C3D10 **peggiora** raffinando.

    Dal manuale, verbatim: *«The C3D10 and C3D10M elements are more accurate
    with the coarse mesh than with the fine mesh: in the coarse meshes four
    elements come together at the point of interest, giving a more accurate
    result after averaging to the nodes. In the more refined mesh, only one
    element contains the point of interest; therefore, the extrapolation to the
    nodes is less accurate.»*

    L'errore non e' dell'elemento: e' della **lettura in uno spigolo**. E'
    anche il motivo per cui questo benchmark **non** va usato come studio di
    convergenza, e per cui la soglia sui benchmark si esprime come scarto
    assoluto dal riferimento e mai come monotonia del raffinamento (#35).

    Il test non impone ne' che cali ne' che salga: misura e stampa. Imporre
    l'una o l'altra sarebbe assumere la conclusione, e su questa grandezza
    nemmeno il produttore la assume.
    """
    tabella: list[tuple[float, float, int]] = []
    for passo in (500.0, 350.0):
        cartella = tmp_path / f"p{passo:g}"
        cartella.mkdir()
        valore, n_nodi, _ = _sigma_yy_in_d(cartella, order=2, tipo="C3D10", passo=passo)
        tabella.append((passo, valore, n_nodi))

    print("\nsigma_yy in D, C3D10, al variare del passo")
    print("passo    nodi    sigma_yy   scarto")
    for passo, valore, n_nodi in tabella:
        print(f"{passo:>5.0f} {n_nodi:>7} {valore:>10.4f} {(valore - TARGET) / abs(TARGET):>+8.2%}")

    rado, fine = (abs(v - TARGET) / abs(TARGET) for _, v, _ in tabella)
    verso = "cala" if fine < rado else "peggiora"
    print(
        f"\nraffinando l'errore {verso}: da {rado:.2%} a {fine:.2%}."
        f"\nAbaqus sullo stesso benchmark passa da +1,15% a +7,24%, cioe' peggiora."
    )
    # L'unico vincolo e' che entrambe restino nel mondo dei solutori pubblicati.
    assert max(rado, fine) < 0.35, (
        f"scarto massimo {max(rado, fine):.1%}: fuori dalla forbice fra -5,6% e +9,5% "
        "in cui stanno i risultati pubblicati su LE10"
    )
