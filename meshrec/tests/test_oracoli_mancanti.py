"""Le grandezze che il programma stampava senza nulla che le contraddicesse.

Ticket https://github.com/maeurong/Tesi/issues/37. Violavano il principio n. 1
di `PRODUCT.md`: *«un numero mostrato senza un controllo che lo smentisca non
vale piu' di un numero assente»*.

L'inventario che le ha trovate sta in `docs/validazione/inventario-grandezze.md`.
Ognuna finiva in `metrics.json` o nel report di tesi, e nessuna aveva un
valore di riferimento indipendente: alcune non erano nominate da alcun test,
altre solo da test di **regressione**, che cristallizzano il numero che il
codice produce oggi e cadono solo se qualcuno lo cambia -- mai se e' sbagliato
dall'inizio.

**Un oracolo e' indipendente quando il valore atteso si ricava senza eseguire
il codice.** Qui vengono tutti da geometria elementare, e ognuno porta la
propria derivazione.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from meshrec.core import abaqus, config, quality, synth
from meshrec.core.config import GRAVITY_MM_S2, Material

# Tetraedro regolare di lato 1: base equilatera nel piano z = 0 e apice sopra
# il baricentro, ad altezza sqrt(6)/3.
REGOLARE = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.5, math.sqrt(3) / 2.0, 0.0],
        [0.5, math.sqrt(3) / 6.0, math.sqrt(6) / 3.0],
    ]
)
# Tetraedro rettangolo con i tre cateti unitari sugli assi.
RETTANGOLO = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
TET = np.array([[0, 1, 2, 3]])


# --- O1: tet_aspect_ratios, che non era nominata da alcun test -----------


def test_l_aspetto_del_tetraedro_regolare_vale_uno():
    """Definizione Verdict: `L_max / (2 sqrt(6) r_in)`, e vale 1 sul regolare.

    E' lo stesso oracolo che il gemello triangolare ha da sempre
    (`test_quality.py`), e che a questa mancava del tutto: il numero finiva in
    `metrics.json` sotto `10_volume_quality.aspect_ratio` e nel report senza
    che nulla lo smentisse.
    """
    assert quality.tet_aspect_ratios(REGOLARE, TET)[0] == pytest.approx(1.0, rel=1e-12)


def test_l_aspetto_del_tetraedro_rettangolo_ha_forma_chiusa():
    """Secondo punto, e con derivazione a mano.

    Cateti unitari: `V = 1/6`; tre facce rette di area `1/2` e una equilatera
    di lato `sqrt(2)`, area `sqrt(3)/2`, quindi `somma_A = (3 + sqrt(3))/2`.
    Il raggio inscritto e' `3V/somma_A = 1/(3 + sqrt(3))`, e lo spigolo massimo
    e' `sqrt(2)`. Sostituendo:

        AR = sqrt(2) (3 + sqrt(3)) / (2 sqrt(6)) = (1 + sqrt(3)) / 2

    Un solo valore analitico non basta: 1 sul regolare e' anche il valore che
    una formula sbagliata di normalizzazione produrrebbe. Due punti distinti
    la inchiodano.
    """
    atteso = (1.0 + math.sqrt(3.0)) / 2.0
    assert quality.tet_aspect_ratios(RETTANGOLO, TET)[0] == pytest.approx(atteso, rel=1e-12)


def test_l_aspetto_di_un_tetraedro_degenere_e_infinito():
    """Ingresso degenere: volume nullo, raggio inscritto nullo, rapporto infinito.

    Non solleva -- e' il comportamento di oggi, e va tenuto: il chiamante
    conta gli elementi fuori range, e un'eccezione lo obbligherebbe a
    filtrare prima di misurare.
    """
    complanare = RETTANGOLO.copy()
    complanare[3, 2] = 0.0
    assert not np.isfinite(quality.tet_aspect_ratios(complanare, TET)[0])


def test_l_aspetto_su_un_insieme_vuoto_e_un_array_vuoto():
    assert quality.tet_aspect_ratios(REGOLARE, np.empty((0, 4), dtype=int)).size == 0


# --- O2: boundary_spacing, sotto cui stanno tutti i set di nodi ----------


def test_la_spaziatura_di_bordo_del_tetraedro_regolare_e_il_suo_lato():
    """Mediana delle lunghezze degli spigoli unici delle facce di bordo.

    Su un tetraedro regolare di lato 1 le facce di bordo sono le sue quattro,
    gli spigoli unici sono sei e misurano tutti 1: la mediana e' 1, senza
    bisogno di eseguire il codice per saperlo.

    Non e' un dettaglio: `set_tolerance` la moltiplica per un fattore, e da
    quella tolleranza escono **tutti e sei i set di nodi** del deck. Fino a
    questo test nessuna chiamata diretta la esercitava.
    """
    facce = abaqus.boundary_faces(TET)
    assert abaqus.boundary_spacing(REGOLARE, facce) == pytest.approx(1.0, rel=1e-12)


def test_la_spaziatura_di_bordo_scala_con_la_geometria():
    """Se il tetraedro raddoppia, la spaziatura raddoppia.

    E' un invariante di omogeneita': una formula che mescolasse lunghezze e
    aree non lo rispetterebbe, e il valore singolo sul lato unitario non
    l'avrebbe colto -- 1 elevato a qualunque potenza fa 1.
    """
    facce = abaqus.boundary_faces(TET)
    singola = abaqus.boundary_spacing(REGOLARE, facce)
    doppia = abaqus.boundary_spacing(REGOLARE * 2.0, facce)
    assert doppia == pytest.approx(2.0 * singola, rel=1e-12)


# --- O3: volume e massa del deck, che vanno in colonna nel report --------


def test_il_volume_e_la_massa_del_deck_sono_quelli_della_scatola(tmp_path):
    """I due numeri che il report di confronto mette in colonna.

    Su una scatola il volume e' il prodotto delle tre dimensioni e la massa e'
    quel volume per la densita': due valori che si scrivono senza eseguire
    nulla. Nessuna asserzione li copriva.
    """
    lati = (100.0, 40.0, 200.0)
    vertici, facce = synth.box_mesh(lati)
    from meshrec.core import volume as modulo_volume

    nodi, tets = modulo_volume.tetrahedralize(
        vertici, facce, max_volume=20_000.0,
        min_ratio=1.8, max_steiner_points=-1, nobisect=False, order=1,
    )
    materiale = Material(name="PROVA", young=30_000.0, poisson=0.2, density=2.4e-9)
    esito = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tets,
        config.AnalysisConfig(material=materiale),
        config.TetConfig(element="C3D4"),
    )

    atteso = lati[0] * lati[1] * lati[2]
    assert esito["volume"] == pytest.approx(atteso, rel=1e-6)
    assert esito["mass"] == pytest.approx(atteso * materiale.density, rel=1e-6)


# --- O4: la costante di gravita', che nessun test asseriva ---------------


def test_la_gravita_e_novecentootto_metri_al_secondo_quadro_in_millimetri():
    """9,81 m/s^2 nel sistema mm, N, MPa, tonnellata, secondo.

    Un fattore 1000 sbagliato qui darebbe un peso proprio mille volte fuori, e
    il deck girerebbe lo stesso producendo numeri plausibili: e' la classe di
    errore piu' cara e nessun test la copriva.
    """
    assert GRAVITY_MM_S2 == pytest.approx(9.81 * 1000.0, rel=1e-12)


def test_densita_per_volume_per_gravita_da_newton():
    """La coerenza dimensionale del sistema, in un solo confronto.

    Un metro cubo d'acqua pesa 9810 N. In unita' di lavoro: `V = 1e9 mm^3`,
    `rho = 1e-9 t/mm^3`, e `rho V g` deve dare 9810. Se una delle tre unita'
    fosse dichiarata male, questo numero non tornerebbe -- ed era verificato
    solo **di rimbalzo**, dentro un test sulle reazioni.
    """
    volume_mm3 = 1.0e9
    densita_acqua = 1.0e-9  # t/mm^3
    assert densita_acqua * volume_mm3 * GRAVITY_MM_S2 == pytest.approx(9810.0, rel=1e-12)


# --- O5: le grandezze che avevano solo test di regressione ---------------


def test_l_ingombro_di_una_lastra_allineata_e_il_suo_spessore():
    """`extent` e' l'ingombro lungo l'asse di **minima varianza**, non lungo z.

    Su un campionamento simmetrico di una lastra quei due assi coincidono e
    l'ingombro vale esattamente lo spessore. Con punti **casuali** invece no:
    misurato, 38,05 mm su una lastra di 37. Non e' un difetto ma la definizione
    della grandezza -- il rumore di campionamento inclina l'asse di un decimo
    di grado, e su una lastra larga 500 mm quell'inclinazione aggiunge un
    millimetro. Chi legge `extent` come «spessore» sbaglia di quel tanto, ed e'
    il motivo per cui la docstring della funzione avverte che e' il numero piu'
    facile da confondere.
    """
    passi = (np.linspace(0.0, 500.0, 21), np.linspace(0.0, 500.0, 21), np.linspace(0.0, 37.0, 13))
    griglia = np.meshgrid(*passi, indexing="ij")
    punti = np.column_stack([asse.ravel() for asse in griglia])
    assert quality.thickness(punti, bin_width=1.0)["extent"] == pytest.approx(37.0, rel=1e-12)


def test_una_lastra_piena_non_ha_uno_spessore_da_separare():
    """`thickness` cerca **due modi**: su un solido pieno non ce ne sono.

    E' l'altra meta' della distinzione con `extent`, che invece un numero lo
    da' sempre. Due grandezze con nomi simili, e fino a questo ticket una era
    coperta e l'altra no.

    **La bandiera e' `bimodal`, non il valore.** La funzione restituisce un
    numero comunque -- misurato, fra 11 e 19 mm al variare della densita' su
    una lastra di 37 -- e quel numero non significa nulla quando `bimodal` e'
    falso. Non e' un difetto: il consumatore lo controlla, e `core/sweep.py` lo
    dichiara per iscritto («source_thickness e' None quando la nuvola sorgente
    stessa e' risultata non bimodale»). Ma chi leggesse `thickness` senza la
    bandiera otterrebbe una misura fabbricata, ed e' scritto qui perche'
    qualcuno ci provera'.

    Il campionamento e' **casuale** apposta: su una griglia regolare i livelli
    discreti fanno un istogramma a punte. Non e' raggiungibile da una scansione,
    ma lo e' dopo la riduzione a voxel, che porta i punti su un reticolo.
    """
    rng = np.random.default_rng(0)
    punti = np.column_stack([
        rng.uniform(0.0, 500.0, 20_000),
        rng.uniform(0.0, 500.0, 20_000),
        rng.uniform(0.0, 37.0, 20_000),
    ])
    esito = quality.thickness(punti, bin_width=1.0)
    assert esito["bimodal"] is False, "una lastra piena non ha due facce da separare"
    assert esito["thickness"] is not None, (
        "il valore esce comunque: e' `bimodal` a dire se significa qualcosa"
    )


def test_il_percentile_del_raggio_spigolo_e_davvero_un_percentile():
    """Oracolo di **proprieta'**, non di valore.

    `radius_edge_ratio_p99` non ha un valore analitico su un maglio vero: TetGen
    non produce tetraedri regolari. Ma un percentile ha una definizione, e la
    definizione e' verificabile: sta fra il minimo e il massimo, e almeno il 99%
    dei valori finiti gli sta sotto.

    E' l'alternativa onesta a un test di regressione, che avrebbe cristallizzato
    il numero di oggi senza dire nulla su cosa significhi.
    """
    from meshrec.core import volume as modulo_volume

    vertici, facce = synth.box_mesh((100.0, 40.0, 200.0))
    cfg = config.TetConfig(max_volume=20_000.0, element="C3D4")
    nodi, tets, metriche = modulo_volume.tetrahedralize_with_metrics(vertici, facce, cfg)

    rapporti = quality.radius_edge_ratios(nodi, tets)
    finiti = rapporti[np.isfinite(rapporti)]
    p99 = metriche["radius_edge_ratio_p99"]

    assert finiti.min() <= p99 <= finiti.max()
    assert (finiti <= p99).mean() >= 0.98, (
        f"solo il {(finiti <= p99).mean():.1%} dei valori sta sotto il novantanovesimo "
        "percentile: non e' un percentile"
    )
    # Il tetraedro regolare e' il migliore possibile: nessun rapporto puo'
    # scendere sotto sqrt(6)/4, e il percentile nemmeno.
    assert p99 >= math.sqrt(6.0) / 4.0
