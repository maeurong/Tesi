#!/usr/bin/env python
"""Rimisura i numeri della sezione «Il deficit di volume» di `docs/fase-5-analisi.md`.

Non fa parte del programma: sta sotto `docs/` apposta, perche' contiene numeri
del provino di laboratorio, che in `src/` non possono stare. Legge la corsa e
non scrive nulla.

    uv run python docs/fase-5-cantiere/misura-deficit.py

Ogni valore che il documento cita esce da qui, e ognuno porta il proprio
`assert` contro il valore pubblicato: se la corsa cambia, questo script cade
invece di stampare in silenzio numeri diversi da quelli scritti.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import meshio
import numpy as np
import open3d as o3d
from scipy.spatial import ConvexHull

CORSA = Path(__file__).resolve().parents[2] / "runs" / "lab_telaio_v2"
# Fase 6: la ripartizione di CARICO_TOP e' passata da uniforme per nodo ad area
# tributaria. Stessa configurazione, stessa geometria, corsa diversa: solo il
# passo CARICO_TOP di `13_solve` e il suo *CLOAD cambiano rispetto a CORSA.
#
# `_dload_fix`: seconda correzione. `_passo_statico` apriva ogni passo statico
# con `*DLOAD` senza `OP=NEW`, e la spinta orizzontale (dichiarata una volta
# sola nel passo SPINTA_ORIZZONTALE) restava attiva anche in CARICO_TOP -- la
# stessa configurazione dichiara `spinta` insieme a `carico_sommita`. La
# corsa senza suffisso resta la prova della contaminazione, non si sovrascrive
# (vedi docs/fase-6-cantiere/sonda-cload-persiste/README.md).
CORSA_PESATA = Path(__file__).resolve().parents[2] / "runs" / "lab_telaio_v3_pesata_dload_fix"
PIANO_DI_TAGLIO = -498.0  # crop_min[2] di config.yaml, nel sistema della scansione
DENSITA = 2.5e-9  # t/mm3, CALCESTRUZZO_C25_30
GRAVITA = 9810.0  # mm/s2

# Tavola MURO 1, docs/fase-4-materiale.md righe 12-17: (sezione_a, sezione_b, lunghezza, n)
TAVOLA = {
    "Zapata": (700, 250, 700, 2),
    "Viga inferior": (250, 250, 1300, 1),
    "Columna": (172, 172, 1695, 2),
    "Viga superior": (140, 175, 2090, 1),
}
# Altezza interrata delle due membrature che attraversano il piano di taglio, in mm.
# Banda, non valore singolo: la quota d'attacco ha due ancoraggi che non coincidono
# (§ 3 del documento). (area_in_pianta, altezza_min, altezza_max)
SOTTO_IL_TAGLIO = {"Zapata x2": (980_000, 219, 240), "Viga inferior": (325_000, 236, 242)}


def volumi_tetraedri(punti: np.ndarray, celle: np.ndarray) -> np.ndarray:
    v = punti[celle]
    return np.abs(np.einsum("ij,ij->i", v[:, 1] - v[:, 0], np.cross(v[:, 2] - v[:, 0], v[:, 3] - v[:, 0]))) / 6.0


def volume_sotto(punti: np.ndarray, celle: np.ndarray, quota: float) -> float:
    """Volume esatto sotto un piano orizzontale: i tetraedri interi piu' la parte
    tagliata di quelli attraversati, chiusa con l'inviluppo convesso."""
    v = punti[celle]
    vol = volumi_tetraedri(punti, celle)
    sotto = (v[:, :, 2] < quota).sum(1)
    totale = float(vol[sotto == 4].sum())
    for i in np.where((sotto > 0) & (sotto < 4))[0]:
        pezzi = [p for p in v[i] if p[2] < quota]
        for a, b in itertools.combinations(range(4), 2):
            pa, pb = v[i, a], v[i, b]
            if (pa[2] < quota) != (pb[2] < quota):
                pezzi.append(pa + (quota - pa[2]) / (pb[2] - pa[2]) * (pb - pa))
        totale += float(ConvexHull(np.array(pezzi)).volume)
    return totale


def vicino(atteso: float, ottenuto: float, tolleranza: float, etichetta: str) -> None:
    scarto = abs(ottenuto - atteso)
    stato = "ok" if scarto <= tolleranza else "SCOSTA"
    print(f"  [{stato}] {etichetta}: {ottenuto:,.4f} (pubblicato {atteso:,.4f}, scarto {scarto:.4g})")
    assert scarto <= tolleranza, f"{etichetta}: {ottenuto} contro {atteso} pubblicato"


def main() -> int:
    if not CORSA.is_dir():
        print(f"manca {CORSA}: rigenera la corsa con `uv run meshrec run lab_telaio.yaml`")
        return 1
    if not CORSA_PESATA.is_dir():
        print(
            f"manca {CORSA_PESATA}: rigenera con `uv run meshrec run lab_telaio.yaml "
            "--out-dir runs/lab_telaio_v3_pesata_dload_fix`"
        )
        return 1

    print("nominale di tavola")
    nominale = sum(a * b * lung * n for a, b, lung, n in TAVOLA.values())
    for nome, (a, b, lung, n) in TAVOLA.items():
        print(f"  {nome:16s} {n} x {a}x{b}x{lung} = {a * b * lung * n:>15,d} mm3")
    vicino(477_744_760, nominale, 0.5, "nominale ricalcolato")
    vicino(0.0094, 100 * (nominale - 477_700_000) / nominale, 1e-4, "scarto dalla tavola [%]")

    print("\nmodello")
    maglia = meshio.read(CORSA / "09_volume.vtu")
    punti, celle = maglia.points, maglia.cells_dict["tetra"]
    volume = float(volumi_tetraedri(punti, celle).sum())
    vicino(217_728_361.2, volume, 0.5, "volume totale")
    vicino(260_016_399, nominale - volume, 1.0, "deficit")
    vicino(45.57, 100 * volume / nominale, 0.01, "modello / nominale [%]")

    print("\nil piano di taglio e il pavimento")
    grezza = np.asarray(o3d.io.read_point_cloud(str(CORSA / "01_cloud.ply")).points)
    fascia = grezza[(grezza[:, 0] >= 1690) & (grezza[:, 0] <= 4460) & (grezza[:, 2] < -350)]
    nuvola = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(fascia))
    # Il seme serve alla riproducibilita', non alla precisione: senza, il bordo alto
    # oscilla fra -502,5 e -497,5 da un'estrazione all'altra. E' quella dispersione
    # di 5 mm, non il singolo valore, la misura di quanto il taglio e il pavimento
    # coincidano -- ed e' il motivo per cui il documento porta una banda.
    o3d.utility.random.seed(0)
    _, interni = nuvola.segment_plane(distance_threshold=3 * 1.1922732319774867, ransac_n=3, num_iterations=2000)
    alto = float(fascia[interni][:, 2].max())
    print(f"  pavimento: {len(interni):,} punti interni, bordo alto z = {alto:.1f}")
    assert -503.0 <= alto <= -497.0, f"bordo alto del pavimento fuori banda: {alto}"
    print(f"  il piano di taglio ({PIANO_DI_TAGLIO}) dista {abs(PIANO_DI_TAGLIO - alto):.1f} mm da esso")

    print("\nripartizione del deficit")
    sotto_modello = volume_sotto(punti, celle, PIANO_DI_TAGLIO)
    vicino(45_283_601, sotto_modello, 200.0, "volume del modello sotto il taglio")
    sopra_modello = volume - sotto_modello
    vicino(172_444_760, sopra_modello, 200.0, "volume del modello sopra il taglio")
    basso = sum(area * lo for area, lo, _ in SOTTO_IL_TAGLIO.values())
    alto_ = sum(area * hi for area, _, hi in SOTTO_IL_TAGLIO.values())
    for nome, (area, lo, hi) in SOTTO_IL_TAGLIO.items():
        print(f"  {nome:16s} {area:,} mm2 x [{lo},{hi}] mm = [{area * lo:,}, {area * hi:,}] mm3")
    for nominale_sotto in (basso, alto_):
        deficit_sotto = nominale_sotto - sotto_modello
        deficit_sopra = (nominale - nominale_sotto) - sopra_modello
        print(
            f"  nominale sotto {nominale_sotto:>13,} -> deficit sotto {deficit_sotto:>13,.0f}"
            f" ({100 * deficit_sotto / (nominale - volume):5.1f}%), sopra {deficit_sopra:>12,.0f}"
            f" ({100 * deficit_sopra / (nominale - volume):5.1f}%)"
        )
        assert abs(deficit_sotto + deficit_sopra - (nominale - volume)) < 1.0, "la contabilita' non chiude"

    print("\nsezione orizzontale del modello (derivata esatta, passo 20 mm)")
    due_colonne = 2 * 172 * 172
    for quota, pubblicato in ((-460, 63_585), (-300, 62_740), (0, 62_959), (600, 61_901), (900, 60_592)):
        area = (volume_sotto(punti, celle, quota + 10) - volume_sotto(punti, celle, quota - 10)) / 20.0
        print(f"  z = {quota:>5}: {area:>10,.0f} mm2, {100 * (area / due_colonne - 1):+5.1f}% sul nominale")
        assert abs(area - pubblicato) < 50, f"area a z={quota}: {area} contro {pubblicato} pubblicato"

    print("\npeso proprio")
    vicino(5339.79, volume * DENSITA * GRAVITA, 0.01, "peso del modello [N]")
    vicino(11_716.69, nominale * DENSITA * GRAVITA, 0.01, "peso del telaio nominale [N]")
    vicino(4229.21, sopra_modello * DENSITA * GRAVITA, 0.02, "peso del modello sopra il taglio [N]")
    for nominale_sotto in (alto_, basso):
        print(f"  peso nominale sopra il taglio: {(nominale - nominale_sotto) * DENSITA * GRAVITA:,.2f} N")

    print("\ndove sta il picco")
    soluzione = meshio.read(CORSA / "13_solution.vtu")
    vm = soluzione.point_data["VM_GRAVITA"]
    indice = int(vm.argmax())
    quote = soluzione.points[:, 2]
    frazione = (soluzione.points[indice, 2] - quote.min()) / (quote.max() - quote.min())
    print(f"  indice {indice} nel .vtu = nodo {indice + 1} nel deck, al {100 * frazione:.1f}% dell'altezza")
    assert indice == 7132 and abs(frazione - 0.892) < 0.002
    incidenti = np.where((celle == indice).any(1))[0]
    vol_el = volumi_tetraedri(punti, celle)
    print(
        f"  {len(incidenti)} tetraedri incidenti, il piu' piccolo {vol_el[incidenti].min():.2f} mm3"
        f" contro una mediana di {np.median(vol_el):,.2f}"
    )
    assert abs(vol_el[incidenti].min() - 17.66) < 0.01

    print("\nCARICO_TOP ripartito per area tributaria (Fase 6) e senza la spinta ereditata (dload_fix)")
    top = meshio.read(CORSA_PESATA / "13_solution.vtu")
    u_top = np.linalg.norm(top.point_data["U_CARICO_TOP"], axis=1)
    vm_top = top.point_data["VM_CARICO_TOP"]
    p99_top = float(np.percentile(vm_top, 99))
    vicino(0.058280504767754024, float(u_top.max()), 1e-6, "CARICO_TOP u_max [mm]")
    vicino(0.8101475038401819, float(vm_top.max()), 1e-6, "CARICO_TOP vm max [MPa]")
    vicino(0.37356652064926726, p99_top, 1e-6, "CARICO_TOP vm p99 [MPa]")
    vicino(0.08144335915512604, float(np.median(vm_top)), 1e-6, "CARICO_TOP vm mediana [MPa]")
    vicino(2.168683377814818, float(vm_top.max()) / p99_top, 1e-4, "CARICO_TOP max/p99")

    # Le righe *CLOAD non cambiano fra le due corse (`v3_pesata` e
    # `v3_pesata_dload_fix`): la correzione tocca solo il *DLOAD (peso e
    # spinta), non il *CLOAD del carico in sommita'. La riga apre ora con
    # "*CLOAD, OP=NEW", non piu' "*CLOAD" da solo.
    deck = (CORSA_PESATA / "wall_model.inp").read_text().splitlines()
    passo = deck.index("** NOME PASSO: CARICO_TOP")
    inizio = next(i for i in range(passo, len(deck)) if deck[i].startswith("*CLOAD")) + 1
    righe_cload = list(itertools.takewhile(lambda r: r and not r.startswith("*"), deck[inizio:]))
    quote = np.array([float(r.split(",")[2]) for r in righe_cload])
    print(f"  {len(quote)} righe, somma {quote.sum():.6f} N, da {quote.min():.6f} a {quote.max():.6f} N")
    assert len(quote) == 3036, f"righe *CLOAD di CARICO_TOP: {len(quote)} contro 3036 pubblicato"
    vicino(-1200.0, float(quote.sum()), 1e-3, "CARICO_TOP *CLOAD somma [N]")
    vicino(-0.8678660701, float(quote.min()), 1e-6, "CARICO_TOP *CLOAD valore piu' negativo [N]")
    nodi_a_zero = int((quote == 0.0).sum())
    assert nodi_a_zero == 703, f"nodi *CLOAD a area tributaria nulla: {nodi_a_zero} contro 703 pubblicato"

    print("\ntutti i valori pubblicati sono stati riprodotti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
