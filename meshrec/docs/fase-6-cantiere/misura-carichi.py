#!/usr/bin/env python
"""Rimisura i numeri di `docs/fase-6-carichi.md`.

Non fa parte del programma: sta sotto `docs/` apposta, sul modello di
`docs/fase-5-cantiere/misura-deficit.py`. Legge gli artefatti gia' scritti
(la corsa dimostrativa in `runs/lab_telaio_v4_posizionati/` e la corsa della
Fase 5 in `runs/lab_telaio_v2/` e `runs/lab_telaio_v3_pesata/`, entrambe in
sola lettura) e rifa' da capo le due sonde su `ccx` vero. Ogni valore che il
documento pubblica porta qui il proprio `assert`: se qualcosa si muove, questo
script cade invece di stampare in silenzio un numero diverso da quello scritto.

    uv run python docs/fase-6-cantiere/misura-carichi.py
"""

from __future__ import annotations

import itertools
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
CORSA_PESATA = RADICE / "runs" / "lab_telaio_v3_pesata"
CORSA_DIMOSTRATIVA = RADICE / "runs" / "lab_telaio_v4_posizionati"

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
            "`uv run meshrec run lab_telaio_v4_posizionati.yaml`"
        )
        return 1

    print("selettori della corsa dimostrativa (metrics.json, campo 11_export.selettori)")
    import json

    metriche = json.loads((CORSA_DIMOSTRATIVA / "metrics.json").read_text(encoding="utf-8"))
    esporta = metriche["11_export"]
    uguale(365, esporta["selettori"]["piastra"]["nodi"], "piastra (box): nodi presi")
    uguale(158, esporta["selettori"]["angolo"]["nodi"], "angolo (sfera): nodi presi")
    uguale(1, esporta["selettori"]["punta"]["nodi"], "punta (nodo): nodi presi")
    uguale(3719, esporta["selettori"]["appoggio"]["nodi"], "appoggio (nset=BASE): nodi presi")
    uguale(
        ["GRAVITA", "PRESSA", "TORSIONE"], esporta["casi_di_carico"], "casi di carico scritti nel deck"
    )

    print("\ncarichi posizionati risolti (metrics.json, campo 11_export.carichi_posizionati)")
    pressa = esporta["carichi_posizionati"]["PRESSA"]
    uguale(365, pressa["nodi"], "PRESSA: nodi")
    uguale(76, pressa["nodi_ad_area_nulla"], "PRESSA: nodi ad area tributaria nulla")
    vicino(-1000.0, pressa["forza_effettiva"][2], 1e-6, "PRESSA: forza effettiva lungo z [N]")

    torsione = esporta["carichi_posizionati"]["TORSIONE"]
    uguale(3719, torsione["nodi"], "TORSIONE: nodi (l'intero set BASE)")
    uguale(800.0, torsione["braccio_dichiarato"], "TORSIONE: braccio dichiarato [mm]")
    vicino(2116.398, torsione["braccio_effettivo"], 0.01, "TORSIONE: braccio effettivo [mm]")
    vicino(500000.0, torsione["momento_dichiarato"][2], 1e-6, "TORSIONE: momento dichiarato, asse z [N*mm]")
    vicino(500000.0, torsione["momento_effettivo"][2], 0.01, "TORSIONE: momento effettivo, asse z [N*mm]")
    uguale(559, torsione["nodi_positivi"], "TORSIONE: nodi del gruppo positivo")
    uguale(218, torsione["nodi_negativi"], "TORSIONE: nodi del gruppo negativo")

    print("\nla contaminazione fra passi statici consecutivi con *CLOAD")
    reazioni_v4 = solve.leggi_reazioni(CORSA_DIMOSTRATIVA / "13_solution.dat", passo=2)
    fz_pressa = sum(v[2] for v in reazioni_v4.values())
    reazioni_v4_t = solve.leggi_reazioni(CORSA_DIMOSTRATIVA / "13_solution.dat", passo=3)
    fz_torsione = sum(v[2] for v in reazioni_v4_t.values())
    print(f"  reazione fz sul passo PRESSA:   {fz_pressa:,.6f} N")
    print(f"  reazione fz sul passo TORSIONE: {fz_torsione:,.6f} N (dovrebbe essere ~4162.39, il solo peso)")
    assert abs(fz_pressa - fz_torsione) < 1.0, (
        "le reazioni di PRESSA e TORSIONE sono tornate diverse: la contaminazione "
        "fra passi non e' piu' riproducibile, il documento va rivisto"
    )
    vicino(4162.392140, fz_pressa - 1000.0, 0.01, "reazione fz di PRESSA meno i 1000 N dichiarati")

    print("\nsonda: un *CLOAD resta attivo nel passo statico successivo se non e' azzerato")
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        print("  ccx non e' nel PATH: sonda saltata (il documento la riporta come gia' eseguita)")
    else:
        sonda_dir = Path(__file__).parent / "sonda-cload-persiste"
        processo = subprocess.run([eseguibile, "-i", "sonda"], cwd=sonda_dir, capture_output=True, text=True, timeout=120)
        assert "Job finished" in processo.stdout
        reazioni = _reazioni_per_passo(sonda_dir / "sonda.dat")
        uguale(3, len(reazioni), "sonda: numero di passi con un blocco di reazioni")
        vicino(100.0, reazioni[1][2], 1e-6, "sonda passo 1 (*CLOAD dichiarato): fz")
        vicino(100.0, reazioni[2][2], 1e-6, "sonda passo 2 (nessun *CLOAD dichiarato): fz eredita il passo 1")
        vicino(0.0, reazioni[3][2], 1e-6, "sonda passo 3 (*CLOAD, OP=NEW): fz torna a zero")

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

    print("\nCARICO_TOP ripartito per area tributaria (gia' pubblicato in docs/fase-5-analisi.md)")
    deck = (CORSA_PESATA / "wall_model.inp").read_text().splitlines()
    inizio = deck.index("*CLOAD", deck.index("** NOME PASSO: CARICO_TOP")) + 1
    righe = list(itertools.takewhile(lambda r: r and not r.startswith("*"), deck[inizio:]))
    valori = np.array([float(r.split(",")[2]) for r in righe])
    uguale(3036, len(valori), "CARICO_TOP: righe *CLOAD")
    vicino(-1200.0, float(valori.sum()), 1e-3, "CARICO_TOP: somma [N]")
    vicino(-0.8678660701, float(valori.min()), 1e-6, "CARICO_TOP: valore piu' negativo [N]")
    uguale(703, int((valori == 0.0).sum()), "CARICO_TOP: nodi ad area tributaria nulla")

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

    print("\ntutti i valori pubblicati sono stati riprodotti.")
    return 0


def _banco_sonda() -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    vertices, faces = synth.box_mesh(SIZE_SONDA)
    nodes, tets = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    z = nodes[:, 2]
    node_sets = {"BASE": np.flatnonzero(z <= z.min() + 1e-6), "TOP": np.flatnonzero(z >= z.max() - 1e-6)}
    return nodes, tets, node_sets


def _reazioni_per_passo(percorso_dat: Path) -> dict[int, tuple[float, float, float]]:
    """Somma delle reazioni di ciascun blocco 'forces' del `.dat`, per passo (1, 2, 3, ...)."""
    testo = Path(percorso_dat).read_text(encoding="ascii", errors="ignore").splitlines()
    inizi = [i for i, riga in enumerate(testo) if riga.strip().startswith("forces")]
    inizi.append(len(testo))
    risultato: dict[int, tuple[float, float, float]] = {}
    for indice, (inizio, fine) in enumerate(zip(inizi[:-1], inizi[1:]), start=1):
        somma = [0.0, 0.0, 0.0]
        for riga in testo[inizio + 1 : fine]:
            campi = riga.split()
            if len(campi) != 4:
                continue
            try:
                valori = [float(v) for v in campi[1:]]
            except ValueError:
                continue
            for componente in range(3):
                somma[componente] += valori[componente]
        risultato[indice] = (somma[0], somma[1], somma[2])
    return risultato


if __name__ == "__main__":
    sys.exit(main())
