#!/usr/bin/env python
"""Rimisura i numeri di `docs/fase-6-carichi.md`.

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-5-cantiere/misura-deficit.py`. Legge gli artefatti gia' scritti
(la corsa dimostrativa in `runs/lab_telaio_v4_posizionati_top/`, quella
"prima" in `runs/lab_telaio_v4_posizionati/` tenuta come prova del difetto
del § 5.4, e la corsa della Fase 5 in `runs/lab_telaio_v2/` e
`runs/lab_telaio_v3_pesata_dload_fix/`, tutte in sola lettura) e rifa' da capo le sonde
su `ccx` vero -- il posizionato, il momento, il rumore di fondo a sola
gravita', e i due banchi sintetici della prima taratura. Ogni valore che il
documento pubblica porta qui il
proprio `assert`: se qualcosa si muove, questo script cade invece di
stampare in silenzio un numero diverso da quello scritto.

    uv run python docs/fase-6-cantiere/misura-carichi.py
"""

from __future__ import annotations

import itertools
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import meshio
import numpy as np
from pydantic import ValidationError

from meshrec.core import abaqus, config, selezione, solve, synth, volume

RADICE = Path(__file__).resolve().parents[2]
CORSA_V2 = RADICE / "runs" / "lab_telaio_v2"
# `_dload_fix`: `runs/lab_telaio_v3_pesata` (senza suffisso) dichiara `spinta`
# insieme a `carico_sommita` ed era contaminata dal difetto gemello sul
# *DLOAD (vedi docs/fase-6-cantiere/sonda-cload-persiste/README.md); tenuta
# come prova, non riletta qui.
CORSA_PESATA = RADICE / "runs" / "lab_telaio_v3_pesata_dload_fix"
CORSA_DIMOSTRATIVA = RADICE / "runs" / "lab_telaio_v4_posizionati_top"
# La corsa "prima" del commit 2fc0ae5 (*CLOAD, OP=NEW): stessa configurazione,
# tenuta apposta come prova del difetto che il § 5.4 racconta.
CORSA_DIMOSTRATIVA_PRIMA = RADICE / "runs" / "lab_telaio_v4_posizionati"

sys.path.insert(0, str(RADICE / "tests" / "feasibility"))
from ccx_utils import read_dat_displacements  # noqa: E402

MATERIALE_SONDA = config.Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
SIZE_SONDA = (100.0, 100.0, 400.0)


def vicino(atteso: float, ottenuto: float, tolleranza: float, etichetta: str) -> None:
    scarto = abs(ottenuto - atteso)
    stato = "ok" if scarto <= tolleranza else "SCOSTA"
    print(f"  [{stato}] {etichetta}: {ottenuto:,.6f} (pubblicato {atteso:,.6f}, scarto {scarto:.4g})")
    assert scarto <= tolleranza, f"{etichetta}: {ottenuto} contro {atteso} pubblicato"


def uguale(atteso: object, ottenuto: object, etichetta: str) -> None:
    stato = "ok" if ottenuto == atteso else "SCOSTA"
    print(f"  [{stato}] {etichetta}: {ottenuto!r} (pubblicato {atteso!r})")
    assert ottenuto == atteso, f"{etichetta}: {ottenuto!r} contro {atteso!r} pubblicato"


def contiene(frammento: str, testo: str, etichetta: str) -> None:
    stato = "ok" if frammento in testo else "SCOSTA"
    print(f"  [{stato}] {etichetta}: {testo!r}")
    assert frammento in testo, f"{etichetta}: {frammento!r} non trovato in {testo!r}"


def cfg(**campi) -> config.PipelineConfig:
    analisi = config.AnalysisConfig(material=MATERIALE_SONDA)
    return config.PipelineConfig(input=config.InputConfig(path="nuvola.ply"), analysis=analisi, **campi)


def messaggio_di(funzione) -> str:
    try:
        funzione()
    except (ValidationError, ValueError) as errore:
        return str(errore)
    raise AssertionError("la condizione degenere non ha sollevato nulla")


def main() -> int:
    if not CORSA_V2.is_dir():
        print(f"manca {CORSA_V2}: rigenera con `uv run meshrec run lab_telaio.yaml`")
        return 1
    if not CORSA_PESATA.is_dir():
        print(f"manca {CORSA_PESATA}")
        return 1
    if not CORSA_DIMOSTRATIVA.is_dir():
        print(
            f"manca {CORSA_DIMOSTRATIVA}: rigenera con "
            "`uv run meshrec run lab_telaio_v4_posizionati_top.yaml`"
        )
        return 1
    if not CORSA_DIMOSTRATIVA_PRIMA.is_dir():
        print(f"manca {CORSA_DIMOSTRATIVA_PRIMA}: era la corsa 'prima' del fix, non si rigenera piu'")
        return 1

    print("selettori della corsa dimostrativa (metrics.json, campo 11_export.selettori)")
    metriche = json.loads((CORSA_DIMOSTRATIVA / "metrics.json").read_text(encoding="utf-8"))
    esporta = metriche["11_export"]
    uguale(365, esporta["selettori"]["piastra"]["nodi"], "piastra (box): nodi presi")
    uguale(158, esporta["selettori"]["angolo"]["nodi"], "angolo (sfera): nodi presi")
    uguale(1, esporta["selettori"]["punta"]["nodi"], "punta (nodo): nodi presi")
    uguale(3719, esporta["selettori"]["appoggio"]["nodi"], "appoggio (nset=BASE): nodi presi")
    uguale(3036, esporta["selettori"]["sommita"]["nodi"], "sommita (nset=TOP): nodi presi")
    uguale(
        ["GRAVITA", "PRESSA", "TORSIONE"], esporta["casi_di_carico"], "casi di carico scritti nel deck"
    )

    print("\nil rapporto dei due valori singolari della SVD su 'sommita' (§ 5.2)")
    deck_dimostrativa = meshio.read(CORSA_DIMOSTRATIVA / "wall_model.inp")
    presi_sommita = deck_dimostrativa.points[deck_dimostrativa.point_sets["sommita"]]
    relativi_sommita = presi_sommita - presi_sommita.mean(axis=0)
    asse_z = np.array([0.0, 0.0, 1.0])
    piano_sommita = relativi_sommita - np.outer(relativi_sommita @ asse_z, asse_z)
    valori_singolari = np.linalg.svd(piano_sommita, full_matrices=False)[1]
    rapporto_svd = float(valori_singolari[1] / valori_singolari[0])
    vicino(0.0961010, rapporto_svd, 1e-6, "SVD instabile: rapporto valore singolare 2/1 su TOP reale (§ 5.2)")

    print("\ncarichi posizionati risolti (metrics.json, campo 11_export.carichi_posizionati)")
    pressa = esporta["carichi_posizionati"]["PRESSA"]
    uguale(365, pressa["nodi"], "PRESSA: nodi")
    uguale(76, pressa["nodi_ad_area_nulla"], "PRESSA: nodi ad area tributaria nulla")
    vicino(-1000.0, pressa["forza_effettiva"][2], 1e-6, "PRESSA: forza effettiva lungo z [N]")

    torsione = esporta["carichi_posizionati"]["TORSIONE"]
    uguale(3036, torsione["nodi"], "TORSIONE: nodi (l'intero set TOP)")
    uguale(490.7, torsione["braccio_dichiarato"], "TORSIONE: braccio dichiarato [mm]")
    vicino(1491.161, torsione["braccio_effettivo"], 0.01, "TORSIONE: braccio effettivo [mm]")
    vicino(500000.0, torsione["momento_dichiarato"][2], 1e-6, "TORSIONE: momento dichiarato, asse z [N*mm]")
    vicino(500000.0, torsione["momento_effettivo"][2], 0.01, "TORSIONE: momento effettivo, asse z [N*mm]")
    uguale(1197, torsione["nodi_positivi"], "TORSIONE: nodi del gruppo positivo")
    uguale(1285, torsione["nodi_negativi"], "TORSIONE: nodi del gruppo negativo")
    uguale(2453.2664114565505, torsione["estensione_disponibile"], "TORSIONE: estensione disponibile [mm]")

    rapporto_torsione = float(
        (torsione["momento_effettivo"][0] ** 2 + torsione["momento_effettivo"][1] ** 2) ** 0.5
    ) / 500000.0
    vicino(0.003552, rapporto_torsione, 5e-6, "TORSIONE: rapporto fuori asse nel deck vero (§ 6.2)")

    print("\nprima del fix: PRESSA e TORSIONE condividevano la stessa reazione (§ 5.4, tabella 'prima')")
    fz_pressa_prima = sum(
        v[2] for v in solve.leggi_reazioni(CORSA_DIMOSTRATIVA_PRIMA / "13_solution.dat", passo=2).values()
    )
    fz_torsione_prima = sum(
        v[2] for v in solve.leggi_reazioni(CORSA_DIMOSTRATIVA_PRIMA / "13_solution.dat", passo=3).values()
    )
    print(f"  reazione fz sul passo PRESSA:   {fz_pressa_prima:,.6f} N")
    print(f"  reazione fz sul passo TORSIONE: {fz_torsione_prima:,.6f} N")
    vicino(0.0, fz_pressa_prima - fz_torsione_prima, 1e-3, "prima: PRESSA e TORSIONE coincidevano")
    vicino(4162.392140, fz_pressa_prima - 1000.0, 0.01, "prima: reazione fz di PRESSA meno i 1000 N dichiarati")

    print("\ndopo il fix (2fc0ae5): PRESSA e TORSIONE hanno reazioni diverse, TORSIONE torna al solo peso")
    fz_pressa = sum(v[2] for v in solve.leggi_reazioni(CORSA_DIMOSTRATIVA / "13_solution.dat", passo=2).values())
    fz_gravita = sum(v[2] for v in solve.leggi_reazioni(CORSA_DIMOSTRATIVA / "13_solution.dat", passo=1).values())
    fz_torsione = sum(v[2] for v in solve.leggi_reazioni(CORSA_DIMOSTRATIVA / "13_solution.dat", passo=3).values())
    print(f"  reazione fz sul passo GRAVITA:  {fz_gravita:,.6f} N")
    print(f"  reazione fz sul passo PRESSA:   {fz_pressa:,.6f} N")
    print(f"  reazione fz sul passo TORSIONE: {fz_torsione:,.6f} N")
    assert abs(fz_pressa - fz_torsione) > 1.0, (
        "le reazioni di PRESSA e TORSIONE sono tornate uguali: la correzione "
        "non e' piu' in vigore, il documento e' sbagliato"
    )
    vicino(4162.392140, fz_pressa - 1000.0, 0.01, "dopo: reazione fz di PRESSA meno i 1000 N dichiarati")
    vicino(fz_gravita, fz_torsione, 1e-3, "dopo: TORSIONE torna esattamente alla reazione di GRAVITA")

    print("\ndopo il fix: TORSIONE sposta davvero qualcosa di proprio (sommita non e' vincolata)")
    casi = metriche["13_solve"]["casi"]
    vicino(0.036730, casi["GRAVITA"]["u_max"], 1e-6, "GRAVITA: u_max [mm]")
    vicino(0.5055793774495465, casi["GRAVITA"]["vm_max"], 1e-6, "GRAVITA: vm_max [MPa]")
    vicino(0.070417, casi["PRESSA"]["u_max"], 1e-6, "PRESSA: u_max [mm]")
    vicino(0.9332259648842575, casi["PRESSA"]["vm_max"], 1e-6, "PRESSA: vm_max [MPa]")
    vicino(0.057308, casi["TORSIONE"]["u_max"], 1e-6, "TORSIONE: u_max [mm]")
    vicino(0.5695047580291122, casi["TORSIONE"]["vm_max"], 1e-6, "TORSIONE: vm_max [MPa]")
    assert casi["TORSIONE"]["u_max"] not in (casi["GRAVITA"]["u_max"], casi["PRESSA"]["u_max"]), (
        "TORSIONE ha lo stesso u_max di GRAVITA o PRESSA: il selettore sommita "
        "e' tornato degenere, il documento va rivisto"
    )

    print("\nsonda: un *CLOAD resta attivo nel passo statico successivo se non e' azzerato")
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        print("  ccx non e' nel PATH: sonda saltata (il documento la riporta come gia' eseguita)")
    else:
        sonda_inp = Path(__file__).parent / "sonda-cload-persiste" / "sonda.inp"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "sonda.inp").write_text(sonda_inp.read_text(encoding="utf-8"), encoding="utf-8")
            processo = subprocess.run(
                [eseguibile, "-i", "sonda"], cwd=tmp_path, capture_output=True, text=True, timeout=120
            )
            assert "Job finished" in processo.stdout
            for passo, atteso, etichetta in (
                (1, 100.0, "sonda passo 1 (*CLOAD dichiarato): fz"),
                (2, 100.0, "sonda passo 2 (nessun *CLOAD dichiarato): fz eredita il passo 1"),
                (3, 0.0, "sonda passo 3 (*CLOAD, OP=NEW): fz torna a zero"),
            ):
                reazioni = solve.leggi_reazioni(tmp_path / "sonda.dat", passo=passo)
                fz = sum(v[2] for v in reazioni.values())
                vicino(atteso, fz, 1e-6, etichetta)

    print("\nil momento fuori asse: TOP as-built, il caso peggiore misurato")
    mesh_v2 = meshio.read(CORSA_V2 / "wall_model.vtu")
    nodi_v2, tets_v2 = mesh_v2.points, mesh_v2.cells_dict["tetra"]
    tolleranza_set = 134.9659268950455
    top = np.flatnonzero(nodi_v2[:, 2] >= nodi_v2[:, 2].max() - tolleranza_set)
    uguale(3036, top.size, "TOP as-built: nodi")

    peggiore = 0.0
    for braccio, attesi in ((490.7, (1197, 1285)), (1226.6, (768, 741)), (1962.6, (368, 316))):
        momento = config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=braccio)
        _, resoconto = abaqus.coppia_equivalente(momento, nodi_v2, tets_v2, top, "C3D4", nome="SONDA")
        uguale(attesi, (resoconto["nodi_positivi"], resoconto["nodi_negativi"]), f"TOP braccio={braccio}: nodi +/-")
        eff = np.array(resoconto["momento_effettivo"])
        rapporto = float(np.linalg.norm(eff - eff[2] * np.array([0.0, 0.0, 1.0]))) / 3000.0
        print(f"  braccio={braccio} mm -> rapporto fuori asse {rapporto:.6f}")
        peggiore = max(peggiore, rapporto)
        # Le due chiavi che il resoconto del momento non portava (§ 7): non
        # dipendono dal braccio, perche' la ripartizione e il piano si
        # calcolano una volta sola sull'intero selettore.
        vicino(
            0.0961010, resoconto["rapporto_valori_singolari"], 1e-6,
            f"TOP braccio={braccio}: rapporto SVD reso dal resoconto",
        )
        uguale(703, resoconto["nodi_ad_area_nulla"], f"TOP braccio={braccio}: nodi ad area nulla")
    vicino(0.003552, peggiore, 5e-6, "TOP as-built: rapporto fuori asse peggiore dei tre bracci")

    print("\nil momento fuori asse: selettore volumetrico con estensione piena lungo l'asse")
    box_montante = config.SelettoreBox(
        tipo="box", min=(0.0, 1700.0, 0.0), max=(875.2360569173816, 2698.1591353725844, 1799.7276611328125)
    )
    presi = selezione.risolvi(box_montante, nodi_v2, {}, nome="montante", spigolo=1.0)
    uguale(7571, presi.size, "montante: nodi presi dal box")
    try:
        abaqus.coppia_equivalente(
            config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=1799.0),
            nodi_v2, tets_v2, presi, "C3D4", nome="SONDA",
        )
        raise AssertionError("il braccio di prova avrebbe dovuto essere rifiutato per estensione")
    except ValueError as errore:
        contiene("si estendono", str(errore), "messaggio dell'estensione disponibile")
    braccio_montante = 0.5 * 1010.1204675091565
    vicino(505.06, braccio_montante, 0.01, "montante: braccio scelto (50% dell'estensione)")
    try:
        abaqus.coppia_equivalente(
            config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=braccio_montante),
            nodi_v2, tets_v2, presi, "C3D4", nome="SONDA",
        )
        raise AssertionError("il selettore volumetrico avrebbe dovuto essere rifiutato")
    except ValueError as errore:
        contiene("8.180e-01", str(errore), "messaggio del rapporto fuori asse del selettore volumetrico")

    media_geometrica = (0.003552 * 0.8180) ** 0.5
    vicino(0.0539, media_geometrica, 1e-4, "media geometrica dei due estremi misurati")
    uguale(5e-2, abaqus.TOLLERANZA_MOMENTO_FUORI_ASSE, "soglia in codice, arrotondata dalla media geometrica")
    vicino(14.08, 5e-2 / 0.003552, 0.01, "margine sopra il peggiore dei casi as-built")
    vicino(16.36, 0.8180 / 5e-2, 0.01, "margine sotto il selettore volumetrico")

    print("\nil momento fuori asse: i due banchi sintetici della prima taratura (§ 6.4)")
    vertici_cubo, facce_cubo = synth.box_mesh((100.0, 40.0, 200.0))
    nodi_cubo, tets_cubo = volume.tetrahedralize(
        vertici_cubo, facce_cubo, max_volume=100_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )

    top_cubo = np.flatnonzero(nodi_cubo[:, 2] >= nodi_cubo[:, 2].max() - 1e-6)
    _, res_planare = abaqus.coppia_equivalente(
        config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        nodi_cubo, tets_cubo, top_cubo, "C3D4", nome="TEST",
    )
    eff_planare = np.array(res_planare["momento_effettivo"])
    rapporto_planare = float(np.linalg.norm(eff_planare - eff_planare[2] * np.array([0.0, 0.0, 1.0]))) / 3000.0
    print(f"  banco planare (TOP del cubo sintetico): rapporto fuori asse {rapporto_planare:.6f}")
    vicino(0.0, rapporto_planare, 1e-9, "banco planare sintetico: rapporto fuori asse esatto")

    spigolo_cubo = np.flatnonzero((nodi_cubo[:, 0] <= 20.0) & (nodi_cubo[:, 2] <= 100.0))
    try:
        abaqus.coppia_equivalente(
            config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=30.0),
            nodi_cubo, tets_cubo, spigolo_cubo, "C3D4", nome="TEST",
        )
        raise AssertionError("lo spigolo del banco sintetico avrebbe dovuto essere rifiutato")
    except ValueError as errore:
        print(f"  banco volumetrico sintetico (spigolo): {errore}")
        contiene("8.333e-01", str(errore), "banco volumetrico sintetico: rapporto fuori asse")

    print("\nCARICO_TOP ripartito per area tributaria (gia' pubblicato in docs/fase-5-analisi.md)")
    # Le righe *CLOAD non cambiano fra `v3_pesata` e `v3_pesata_dload_fix`: la
    # correzione sul *DLOAD (spinta ereditata) non tocca il *CLOAD del carico
    # in sommita'. La riga apre ora con "*CLOAD, OP=NEW", non piu' "*CLOAD".
    deck = (CORSA_PESATA / "wall_model.inp").read_text().splitlines()
    passo = deck.index("** NOME PASSO: CARICO_TOP")
    inizio = next(i for i in range(passo, len(deck)) if deck[i].startswith("*CLOAD")) + 1
    righe = list(itertools.takewhile(lambda r: r and not r.startswith("*"), deck[inizio:]))
    valori = np.array([float(r.split(",")[2]) for r in righe])
    uguale(3036, len(valori), "CARICO_TOP: righe *CLOAD")
    vicino(-1200.0, float(valori.sum()), 1e-3, "CARICO_TOP: somma [N]")
    vicino(-0.8678660701, float(valori.min()), 1e-6, "CARICO_TOP: valore piu' negativo [N]")
    uguale(703, int((valori == 0.0).sum()), "CARICO_TOP: nodi ad area tributaria nulla")
    uguale(2334, len(np.unique(valori)), "CARICO_TOP: valori distinti nel *CLOAD pesato")

    vm_top_v2 = meshio.read(CORSA_V2 / "13_solution.vtu").point_data["VM_CARICO_TOP"]
    vicino(0.9811407754536536, float(vm_top_v2.max()), 1e-6, "CARICO_TOP: picco vm prima della pesatura [MPa]")
    # Corso il fix sul *DLOAD (v3_pesata_dload_fix): il picco scende da
    # 0,9808637 a 0,8101475 MPa perche' la spinta orizzontale, dichiarata in
    # SPINTA_ORIZZONTALE, non e' piu' ereditata da CARICO_TOP (§ 4 nota,
    # docs/fase-6-carichi.md).
    vm_top_pesata = meshio.read(CORSA_PESATA / "13_solution.vtu").point_data["VM_CARICO_TOP"]
    vicino(0.8101475038401819, float(vm_top_pesata.max()), 1e-6, "CARICO_TOP: picco vm dopo la pesatura e senza la spinta ereditata [MPa]")

    print("\nle due sonde su ccx vero (tests/feasibility/test_calculix.py, rigiocate qui)")
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        print("  ccx non e' nel PATH: le due sonde sono saltate")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nodes, tets, node_sets = _banco_sonda()
            abaqus.write_inp(
                tmp_path / "model.inp", nodes, tets,
                node_sets=node_sets, material=MATERIALE_SONDA, print_nsets=("TOP",),
                nset_selettori={"piastra": node_sets["TOP"]},
                carichi=config.CarichiConfig(posizionati=[
                    config.CaricoPosizionato(nome="PRESSA", selettore="piastra", forza=(0.0, 0.0, -1000.0)),
                ]),
            )
            processo = subprocess.run(
                [eseguibile, "-i", "model"], cwd=tmp_path, capture_output=True, text=True, timeout=600
            )
            assert "Job finished" in processo.stdout
            assert processo.stdout.upper().count("*WARNING") == 0
            reazioni = solve.leggi_reazioni(tmp_path / "model.dat", passo=2)
            fx, fy, fz = np.array(list(reazioni.values())).sum(axis=0)
            print(f"  forza posizionata: reazioni ({fx:.3g}, {fy:.3g}, {fz:.6f}) N")
            vicino(1067.53, fz, 0.01, "forza posizionata: reazione fz [N]")
            vicino(0.0, fx, 1e-5, "forza posizionata: reazione fx [N]")
            vicino(2.2e-6, fy, 1e-5, "forza posizionata: reazione fy [N]")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nodes, tets, node_sets = _banco_sonda()
            abaqus.write_inp(
                tmp_path / "model.inp", nodes, tets,
                node_sets=node_sets, material=MATERIALE_SONDA, print_nsets=("TOP",),
                nset_selettori={"piastra": node_sets["TOP"]},
                carichi=config.CarichiConfig(posizionati=[
                    config.CaricoPosizionato(
                        nome="TORSIONE", selettore="piastra",
                        momento=config.Momento(asse=(0.0, 0.0, 1.0), modulo=50_000.0, braccio=60.0),
                    ),
                ]),
            )
            processo = subprocess.run(
                [eseguibile, "-i", "model"], cwd=tmp_path, capture_output=True, text=True, timeout=600
            )
            assert "Job finished" in processo.stdout
            assert processo.stdout.upper().count("*WARNING") == 0
            spostamenti = read_dat_displacements(tmp_path / "model.dat")
            orizzontali = max(max(abs(u[0]), abs(u[1])) for u in spostamenti.values())
            print(f"  momento come coppia: spostamento orizzontale massimo {orizzontali:.6f} mm")
            vicino(0.056761, orizzontali, 1e-4, "momento come coppia: spostamento orizzontale massimo [mm]")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nodes, tets, node_sets = _banco_sonda()
            abaqus.write_inp(
                tmp_path / "model.inp", nodes, tets,
                node_sets=node_sets, material=MATERIALE_SONDA, print_nsets=("TOP",),
            )
            processo = subprocess.run(
                [eseguibile, "-i", "model"], cwd=tmp_path, capture_output=True, text=True, timeout=600
            )
            assert "Job finished" in processo.stdout
            spostamenti = read_dat_displacements(tmp_path / "model.dat")
            rumore = max(max(abs(u[0]), abs(u[1])) for u in spostamenti.values())
            print(f"  sola gravita', stesso banco: rumore orizzontale massimo {rumore:.6e} mm")
            vicino(1.765108e-05, rumore, 1e-9, "sola gravita': rumore orizzontale massimo [mm]")
            vicino(3215.0, orizzontali / rumore, 5.0, "momento come coppia: volte il rumore di fondo")

    print("\nlo spigolo medio e la soglia dei tre spigoli (§ 3)")
    spigolo_v2 = json.loads((CORSA_V2 / "metrics.json").read_text(encoding="utf-8"))["11_export"]["boundary_spacing"]
    vicino(22.49432114917425, spigolo_v2, 1e-9, "spigolo medio (boundary_spacing) [mm]")
    vicino(67.48296344752275, selezione.SPIGOLI_DI_TOLLERANZA * spigolo_v2, 1e-6, "soglia dei tre spigoli [mm]")

    print("\ngli errori veri sugli ingressi degeneri (§ 3, tabelle)")
    contiene(
        "min > max sulla componente y",
        messaggio_di(lambda: cfg(selettori={"rotta": {"tipo": "box", "min": [0.0, 9.0, 0.0], "max": [10.0, 1.0, 10.0]}})),
        "box rovesciata",
    )
    contiene(
        "greater than",
        messaggio_di(lambda: cfg(selettori={"vuota": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 0.0}})),
        "raggio non positivo",
    )
    contiene(
        "collide, ignorando le maiuscole",
        messaggio_di(lambda: cfg(selettori={"BASE": {"tipo": "nset", "nome": "TOP"}})),
        "nome di selettore uguale a uno dei sei",
    )
    contiene(
        "cita il selettore 'fantasma', che non e' dichiarato",
        messaggio_di(lambda: cfg(
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(
                posizionati=[{"nome": "PRESSA", "selettore": "fantasma", "forza": [0.0, 0.0, -1.0]}]
            ),
        )),
        "carico su selettore non dichiarato",
    )
    percorso_omonime = Path(tempfile.mkstemp(suffix=".yaml")[1])
    percorso_omonime.write_text(
        "input:\n  path: nuvola.ply\n"
        "analysis:\n  material:\n    name: MURATURA\n    young: 1500.0\n"
        "    poisson: 0.2\n    density: 1.8e-9\n"
        "selettori:\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 5.0\n"
        "  angolo:\n    tipo: sfera\n    centro: [0.0, 0.0, 0.0]\n    raggio: 9.0\n",
        encoding="utf-8",
    )
    contiene(
        "compare due volte nello stesso blocco",
        messaggio_di(lambda: config.carica_yaml(percorso_omonime)),
        "due chiavi YAML omonime",
    )
    percorso_omonime.unlink()
    contiene(
        "gia' preso",
        messaggio_di(lambda: cfg(
            selettori={"piastra": {"tipo": "nset", "nome": "TOP"}},
            carichi=config.CarichiConfig(
                posizionati=[{"nome": "CARICO_TOP", "selettore": "piastra", "forza": [0.0, 0.0, -1.0]}]
            ),
        )),
        "nome di carico riservato",
    )
    # Selettore dichiarato e mai citato: NON e' un errore.
    configurazione = cfg(selettori={"mai_usato": {"tipo": "sfera", "centro": [0.0, 0.0, 0.0], "raggio": 1.0}})
    assert "mai_usato" in configurazione.selettori

    nodi_banco = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [10.0, 10.0, 0.0],
         [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [0.0, 10.0, 10.0], [10.0, 10.0, 10.0]]
    )
    node_sets_banco = {"BASE": np.array([0, 1, 2, 3]), "TOP": np.array([4, 5, 6, 7])}
    contiene(
        "risolve zero nodi",
        messaggio_di(lambda: selezione.risolvi(
            config.SelettoreBox(tipo="box", min=(100.0, 100.0, 100.0), max=(200.0, 200.0, 200.0)),
            nodi_banco, node_sets_banco, nome="lontana", spigolo=10.0,
        )),
        "selettore a zero nodi",
    )
    contiene(
        "prende tutti i 8 nodi",
        messaggio_di(lambda: selezione.risolvi(
            config.SelettoreBox(tipo="box", min=(-1.0, -1.0, -1.0), max=(11.0, 11.0, 11.0)),
            nodi_banco, node_sets_banco, nome="tutto", spigolo=10.0,
        )),
        "selettore su tutti i nodi",
    )
    contiene(
        "oltre i 30.0 mm di 3 spigoli medi",
        messaggio_di(lambda: selezione.risolvi(
            config.SelettoreNodo(tipo="nodo", punto=(1000.0, 0.0, 0.0)),
            nodi_banco, node_sets_banco, nome="persa", spigolo=10.0,
        )),
        "nodo oltre 3 spigoli medi",
    )
    elementi_banco = np.array([[0, 1, 2, 4], [3, 5, 6, 7]], dtype=np.int64)
    contiene(
        "non formano alcuna faccia di bordo",
        messaggio_di(lambda: abaqus.ripartisci(1.0, nodi_banco, elementi_banco, np.array([0]), "C3D4", nome="interno")),
        "area tributaria totale nulla",
    )

    print("\nil pareggio dei valori singolari: la tabella del § 9.1")
    _, res_banco = abaqus.coppia_equivalente(
        config.Momento(asse=(0.0, 0.0, 1.0), modulo=3000.0, braccio=60.0),
        nodi_cubo, tets_cubo, top_cubo, "C3D4", nome="TEST",
    )
    vicino(0.4, res_banco["rapporto_valori_singolari"], 1e-9, "banco dei test (TOP 100 x 40): rapporto")
    tabella = ((100.0, None), (99.0, 35.12), (90.0, 1.44), (80.0, 0.65),
               (40.0, 0.13), (9.61, 0.027))
    for larghezza, atteso in tabella:
        rapporto, rotazione = _piastra_perturbata(larghezza)
        print(f"  100 x {larghezza} -> rapporto {rapporto:.4f}, rotazione {rotazione:.4f} gradi")
        vicino(larghezza / 100.0, rapporto, 1e-9, f"piastra 100 x {larghezza}: rapporto")
        if atteso is None:
            # Su un pareggio esatto la SVD non ha un vettore da scegliere: il
            # valore preciso non e' riproducibile fra versioni di LAPACK, il
            # salto si'.
            assert rotazione > 45.0, f"piastra isotropa: rotazione {rotazione}, attesa oltre 45 gradi"
            print("  [ok] piastra isotropa: rotazione oltre 45 gradi")
        else:
            vicino(atteso, rotazione, 0.01, f"piastra 100 x {larghezza}: rotazione [gradi]")
    vicino(0.3100, (0.0961010 * 1.0) ** 0.5, 1e-4, "media geometrica dei due estremi del § 9.1")
    # La soglia scelta, e i due margini che il § 9.1 dichiara. Non e' una
    # misura: e' 0,65 gradi di rotazione tollerata, letti sulla tabella qui
    # sopra. Spostarla senza rimisurare fa cadere queste tre righe.
    vicino(0.80, abaqus.SOGLIA_PAREGGIO_VALORI_SINGOLARI, 1e-9, "soglia del pareggio")
    assert res_banco["rapporto_valori_singolari"] < abaqus.SOGLIA_PAREGGIO_VALORI_SINGOLARI, (
        "il banco dei test finisce sopra la soglia: l'avviso partirebbe su una piastra 2,5 : 1"
    )
    assert 0.0961010 < abaqus.SOGLIA_PAREGGIO_VALORI_SINGOLARI, (
        "il caso studio finisce sopra la soglia"
    )

    print("\ntutti i valori pubblicati sono stati riprodotti.")
    return 0


def _piastra_perturbata(larghezza: float) -> tuple[float, float]:
    """Rapporto dei valori singolari e rotazione della direzione tolto un nodo.

    Una griglia 12 x 12 su una piastra lunga 100 mm: e' il banco del § 9.1,
    scelto perche' il rapporto lo fissa la sola larghezza. Si toglie un nodo
    (la perturbazione che un rimaglio produce davvero) e si misura di quanto
    ruota la direzione di separazione che `coppia_equivalente` sceglierebbe.
    """
    asse = np.array([0.0, 0.0, 1.0])

    def direzione(punti: np.ndarray) -> tuple[np.ndarray, float]:
        relativi = punti - punti.mean(axis=0)
        piano = relativi - np.outer(relativi @ asse, asse)
        _, valori, versori = np.linalg.svd(piano, full_matrices=False)
        return abaqus.fix_sign(versori[0]), float(valori[1] / valori[0])

    x, y = np.meshgrid(np.linspace(0.0, 100.0, 12), np.linspace(0.0, larghezza, 12))
    punti = np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)])
    intera, rapporto = direzione(punti)
    ridotta, _ = direzione(np.delete(punti, len(punti) // 3, axis=0))
    coseno = float(np.clip(abs(intera @ ridotta), -1.0, 1.0))
    return rapporto, float(np.degrees(np.arccos(coseno)))


def _banco_sonda() -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    vertices, faces = synth.box_mesh(SIZE_SONDA)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    z = nodes[:, 2]
    node_sets = {"BASE": np.flatnonzero(z <= z.min() + 1e-6), "TOP": np.flatnonzero(z >= z.max() - 1e-6)}
    return nodes, tets, node_sets


if __name__ == "__main__":
    sys.exit(main())
