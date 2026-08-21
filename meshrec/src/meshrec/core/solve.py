"""Lettura delle uscite di CalculiX: il `.frd` e il `.dat`.

Il modulo esiste separato da `abaqus.py` perche' quello scrive il deck e
questo legge i risultati: sono due direzioni, e `abaqus.py` e' gia' lungo.

Le uscite di `ccx` hanno tre trappole sul `.frd`, tutte misurate il
21/08/2026 sul deck as-built del telaio (`ccx` 2.22, `runs/lab_telaio_v2/
wall_model.inp`):

- il numero di passo sta nel record `100CL` e **si legge**, non si deduce
  contando i blocchi: su quel deck i blocchi DISP sono nove per quattro
  passi, tre statici piu' sei modi, e contare cade appena le uscite
  cambiano;
- nel record modale il passo e il tipo escono incollati (`2MODAL`), quindi
  la lettura e' a colonne fisse e mai un `split()`;
- le forme modali sono normalizzate sulla massa. Una von Mises calcolata su
  una forma da' numeri plausibili per un calcestruzzo e privi di
  significato: fino a 88,5 MPa, misurati. Il flag `modale` esiste per
  impedire che escano da qui come se fossero millimetri o MPa.

Il `.dat` ha una trappola analoga, misurata oggi su un deck di prova ad hoc
(non `lab_telaio_v2`) a due passi -- uno statico con carico, uno modale --
costruito apposta per verificarla: la richiesta di stampa delle reazioni
(`*NODE PRINT, RF`) fatta nel passo statico resta attiva anche nel passo
modale successivo, che non la richiede e non la cancella. `ccx` ristampa
quindi un blocco "forces" anche per ciascun modo, sotto l'intestazione
`E I G E N V A L U E   O U T P U T`: numeri nell'ordine dei milioni di N,
che non sono reazioni ne' altro di fisico. `leggi_reazioni` si ferma a
quella intestazione per lo stesso motivo per cui `leggi_frd` marca `modale`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import numpy as np

from meshrec.core import abaqus, quality
from meshrec.core.config import AnalysisConfig

# Tempo massimo concesso a ccx: stesso valore usato in tutta la suite di
# fattibilita' (tests/feasibility/test_calculix.py), non un numero nuovo.
_TIMEOUT_S = 600.0

# Estensione in pianta minima dell'insieme vincolato
# (abaqus.constraint_plan_extent), come frazione dell'impronta del pezzo.
# Sotto questa soglia i risultati restano scritti ma sono marcati non
# citabili. Misurato il 21/08/2026 allo Step 7 del Task 2 su quattro
# geometrie: muro 0,999, lab_crop 0,987, sintetico a due piedi 1,000,
# sintetico a un piede solo 0,32 -- un dirupo netto fra 0,32 e 0,987, nessun
# punto di misura in mezzo. 0,5 sta in quel dirupo: sopra il solo caso
# patologico misurato, sotto ogni caso vincolato correttamente. Debito: la
# tabella non contiene il caso difettoso reale, solo il banco sintetico a un
# piede come sostituto; il Task 11 porta il punto vero, e questa soglia va
# riverificata allora.
#
# Costante di modulo e non campo di `AnalysisConfig` (ruling della revisione
# del Task 7): non cambia cosa viene calcolato, solo l'etichetta di un
# verdetto, quindi non appartiene all'impronta di `sweep.fingerprint` (che
# include `analysis` per intero, sweep.py:43) -- un campo qui romperebbe
# `experiments/*/registro.jsonl`, sola lettura. E una soglia di controllo che
# l'utente puo' allentare da YAML e' un controllo che l'utente puo' zittire:
# questa fase esiste per avere controlli che smentiscono, non per renderli
# opzionali. Confine con `AnalysisConfig.set_tolerance_factor`, che resta in
# configurazione: quello cambia quali nodi finiscono nei set, cioe'
# l'elaborazione stessa, non solo il verdetto su un suo risultato.
_SOGLIA_VINCOLO_IN_PIANTA = 0.5

# Tolleranza di equilibrio per `controlla_reazioni`, misurata in questa
# sessione (21/08/2026, ccx 2.22) su un cubo omogeneo sotto peso proprio:
# scarto fra reazioni e rho*V*g dell'8,5% con 35 nodi vincolati alla base,
# sceso al 5,7% raffinando a 85; su una mesh piu' rada (13 nodi vincolati,
# 43 nodi totali) lo scarto e' salito al 19,5%, accompagnato da una MPC
# spuria che ccx riporta da solo ("multiple point constraints: 1") -- indizio
# di un artefatto di TetGen su quella mesh specifica, non della fisica.
# Nessuna di queste corse e' la mesh reale della pipeline (min_ratio
# vincolato, molto piu' fitta): 0,25 sta sopra il rumore misurato oggi e
# sotto qualunque errore di un ordine di grandezza (densita' sbagliata,
# direzione di vincolo sbagliata). Da rivedere se una corsa reale la
# attraversa: vedi il rapporto del Task 7.
_TOLLERANZA_REAZIONI = 0.25

# ponytail: banda di vincolo come frazione dell'altezza totale del modello,
# non una quota assoluta in mm (sarebbe un numero del provino dentro src/).
# 0,05 non e' misurato -- e' una scelta conservativa non tarata su un caso
# difettoso reale, segnalata nel report del Task 7. Se il Task 11 porta un
# caso reale con un picco vicino al confine, tarare qui.
_FRAZIONE_BANDA_VINCOLO = 0.05


class Blocco(NamedTuple):
    """Un blocco di risultati del `.frd`, con il passo a cui appartiene."""

    grandezza: str
    passo: int
    modale: bool
    valore: float
    nodi: np.ndarray
    dati: np.ndarray


# Colonne del record 100CL, contate sul `.frd` scritto da ccx 2.22 (misurate
# oggi anche su un deck di prova ad hoc, non solo su quello del brief): il
# passo e' un'unica cifra alla colonna 62, e nel record modale "MODAL" le sta
# incollata subito dopo, senza spazio. Un `split()` legge quel token unico e
# perde entrambi i campi in silenzio.
_COL_VALORE = slice(12, 24)
_COL_PASSO = slice(62, 63)
_COL_TIPO = slice(63, 68)


def leggi_frd(percorso: Path) -> list[Blocco]:
    """I blocchi di un `.frd` ascii, ciascuno con il passo che il file dichiara."""
    blocchi: list[Blocco] = []
    passo, valore, modale = 0, 0.0, False
    grandezza: str | None = None
    nodi: list[int] = []
    righe: list[list[float]] = []
    for linea in Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines():
        if linea.startswith("  100CL"):
            valore = float(linea[_COL_VALORE])
            passo = int(linea[_COL_PASSO])
            modale = linea[_COL_TIPO].strip().startswith("MODAL")
            continue
        if linea.startswith(" -4"):
            grandezza = linea.split()[1]
            nodi, righe = [], []
            continue
        if linea.startswith(" -3"):
            if grandezza is not None and righe:
                blocchi.append(Blocco(
                    grandezza=grandezza, passo=passo, modale=modale, valore=valore,
                    nodi=np.array(nodi, dtype=np.int64),
                    dati=np.array(righe, dtype=np.float64),
                ))
            grandezza = None
            continue
        if grandezza is not None and linea.startswith(" -1"):
            nodi.append(int(linea[3:13]))
            componenti = (len(linea) - 13) // 12
            righe.append([float(linea[13 + 12 * i:25 + 12 * i]) for i in range(componenti)])
    return blocchi


def leggi_reazioni(
    percorso: Path, passo: int | None = None
) -> dict[int, tuple[float, float, float]]:
    """Reazioni nodali dall'ultimo blocco statico "forces" del `.dat`.

    Stessa logica di `tests/feasibility/ccx_utils.read_dat_displacements`:
    righe a quattro campi (nodo piu' tre componenti) dopo l'intestazione
    delle forze, ultimo blocco vince -- coerente coi passi statici cumulativi
    di `abaqus.write_inp`, dove ogni passo ripete i carichi permanenti dei
    precedenti. La lettura si ferma pero' a `E I G E N V A L U E   O U T P U T`:
    oltre quel punto i blocchi "forces" appartengono ai modi, non ai passi
    statici (vedi il docstring del modulo).

    `passo`, se dato, isola le reazioni di un singolo passo statico invece
    dell'ultimo: ccx scrive una riga `S T E P n` prima di ogni blocco, e
    questa e' la stessa numerazione ordinale del record `100CL` del `.frd`
    (verificato il 21/08/2026 eseguendo `ccx` 2.22 su un deck di prova a
    quattro passi: `S T E P 1..4` per GRAVITA, SPINTA_ORIZZONTALE,
    CARICO_TOP, MODALE, nello stesso ordine). Serve al controllo di
    equilibrio: il passo 1 e' sempre il solo peso proprio, per costruzione di
    `abaqus.write_inp` (la card `peso` e' scritta prima di ogni ramo
    condizionale su `carichi`), quindi confrontabile con `rho*V*g` senza
    conoscere gli altri carichi eventualmente cumulati nei passi successivi.
    """
    reazioni: dict[int, tuple[float, float, float]] = {}
    passo_corrente = 0
    for linea in Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines():
        if "E I G E N V A L U E   O U T P U T" in linea:
            break
        pulita = linea.strip()
        if pulita.startswith("S T E P"):
            cifre = pulita.replace("S T E P", "").split()
            if cifre:
                passo_corrente = int(cifre[0])
            continue
        if passo is not None and passo_corrente != passo:
            continue
        campi = linea.split()
        if len(campi) != 4:
            continue
        try:
            nodo = int(campi[0])
            valori = tuple(float(valore) for valore in campi[1:])
        except ValueError:
            continue
        reazioni[nodo] = valori
    return reazioni


def controlla_reazioni(
    reazioni: dict[int, tuple[float, float, float]],
    peso_atteso: tuple[float, float, float],
    tolleranza: float,
) -> dict[str, object]:
    """Confronta la somma delle reazioni con `rho*V*g` come vettore, non come modulo.

    Un modulo giusto con una direzione sbagliata passerebbe un confronto
    scalare: e' esattamente il caso di un vincolo che tiene la struttura di
    sbieco (`*BOUNDARY` su assi sbagliati, o una spinta applicata dove non
    dovrebbe). Il confronto e' quindi sulla norma del vettore differenza,
    relativa alla norma del peso atteso.

    Dizionario vuoto o peso atteso nullo: `passato: False` senza dividere per
    zero, non un'eccezione -- un `.dat` senza il passo richiesto o una
    configurazione senza massa non sono casi da normalizzare, sono casi da
    dichiarare non verificati.
    """
    peso = np.asarray(peso_atteso, dtype=np.float64)
    norma_attesa = float(np.linalg.norm(peso))
    if not reazioni or norma_attesa == 0.0:
        return {
            "passato": False,
            "somma": (0.0, 0.0, 0.0),
            "peso_atteso": tuple(float(v) for v in peso_atteso),
            "scarto_relativo": None,
        }
    somma = np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)
    scarto = float(np.linalg.norm(somma - peso) / norma_attesa)
    return {
        "passato": scarto <= tolleranza,
        "somma": tuple(float(v) for v in somma),
        "peso_atteso": tuple(float(v) for v in peso_atteso),
        "scarto_relativo": scarto,
    }


def controlla_autovalori(frequenze_hz: list[float], soglia_relativa: float = 0.2) -> dict[str, object]:
    """Una frequenza (quasi) nulla e' un meccanismo: il vincolo non tiene la
    struttura, la lascia libera di muoversi.

    L'elenco vuoto rifiuta. Altrimenti la prima frequenza (la piu' bassa,
    ccx le estrae in ordine crescente) deve valere almeno `soglia_relativa`
    volte la seconda: un vero meccanismo esce ordini di grandezza sotto le
    altre, non una frazione confrontabile. La soglia e' relativa e non in Hz
    assoluti perche' l'Hz e' scala del pezzo (massa, rigidezza), non del
    prodotto -- un numero assoluto qui sarebbe un numero del provino dentro
    `src/`. Misurato il 21/08/2026 sull'as-built del telaio: 21,19 Hz col
    vincolo corretto, 4,03 Hz col vincolo su un piede solo (rapporto a
    seconda frequenza comunque sopra soglia in entrambi i casi con vincolo
    presente; il meccanismo vero, prima frequenza praticamente nulla, e' un
    altro ordine di grandezza).
    """
    if not frequenze_hz:
        return {"passato": False, "prima_frequenza_hz": None}
    prima = float(frequenze_hz[0])
    if len(frequenze_hz) == 1:
        return {"passato": prima > 0.0, "prima_frequenza_hz": prima}
    seconda = float(frequenze_hz[1])
    rapporto = prima / seconda if seconda != 0.0 else 0.0
    return {
        "passato": prima > 0.0 and rapporto >= soglia_relativa,
        "prima_frequenza_hz": prima,
        "rapporto_prima_seconda": rapporto,
    }


def controlla_picco(valori: np.ndarray, quote: np.ndarray, banda: float) -> dict[str, object]:
    """max/p99 e dove vive il picco: non basta che sia alto, conta se cade
    dentro la banda di vincolo.

    Misurato il 21/08/2026 sull'as-built, caso CARICO_TOP: `vm_max` 31.977,6
    MPa a quota 239,62 su 240,90 mm, dentro il set TOP dove il carico e'
    applicato -- max/p99 = 5,09, un picco stretto e non un plateau. Sotto
    peso proprio invece max/p99 = 2,16 e nessuno dei 142 nodi sopra il p99
    cade entro la banda di vincolo (il picco sta a z 2286 mm, non
    sull'incastro). Il controllo non dice se il picco e' alto: dice se vive
    dentro la banda vicino alla base, dove un vincolo o un carico
    concentrato produce numeri grandi e non rappresentativi del pezzo.

    p99 nullo (tensioni tutte a zero): `rapporto_max_p99` e' `None`, mai un
    `nan` silenzioso da una divisione 0/0. Un solo nodo: il percentile e'
    quel nodo stesso, nessun `IndexError`.
    """
    v = np.asarray(valori, dtype=np.float64)
    q = np.asarray(quote, dtype=np.float64)
    massimo = float(v.max())
    p99 = float(np.percentile(v, 99))
    rapporto = None if p99 == 0.0 else massimo / p99
    sopra_p99 = v >= p99
    in_banda = q <= float(q.min()) + banda
    n_sopra = int(sopra_p99.sum())
    frazione_in_banda = float((sopra_p99 & in_banda).sum() / n_sopra) if n_sopra else 0.0
    return {
        "passato": frazione_in_banda == 0.0,
        "max": massimo,
        "p99": p99,
        "rapporto_max_p99": rapporto,
        "frazione_in_banda": frazione_in_banda,
    }


def leggi_frequenze(percorso: Path) -> list[float]:
    """Le frequenze proprie [Hz]: colonna CYCLES/TIME del blocco MODE NO del `.dat`.

    Il blocco e' una tabella libera (nessuna colonna incollata, a differenza
    del `.frd`): la riga di intestazione fa da ancora, le righe dati hanno
    cinque campi con il primo intero, e il blocco finisce alla prima riga
    vuota dopo che almeno un modo e' stato letto.
    """
    frequenze: list[float] = []
    dentro = False
    for linea in Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines():
        if "MODE NO" in linea and "EIGENVALUE" in linea:
            dentro = True
            continue
        if not dentro:
            continue
        campi = linea.split()
        if len(campi) != 5 or not campi[0].isdigit():
            if frequenze:
                break
            continue
        frequenze.append(float(campi[3]))
    return frequenze


def von_mises(tensioni: np.ndarray) -> np.ndarray:
    """Tensione equivalente da sei componenti nell'ordine di CalculiX.

    L'ordine e' SXX, SYY, SZZ, SXY, SYZ, SZX: leggerlo sbagliato non solleva
    nulla e produce un numero plausibile, che e' il modo peggiore di sbagliare.
    """
    s = np.asarray(tensioni, dtype=np.float64)
    normali = 0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
    taglianti = 3.0 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2)
    return np.sqrt(normali + taglianti)


def _volume_totale(nodes: np.ndarray, elements: np.ndarray) -> float:
    """Volume della mesh di volume, tetraedri o esaedri secondo i nodi per elemento.

    Riusa `quality.tet_volumes`/`quality.hex_volumes`, gia' misurate e testate
    allo step 10: nessuna seconda formula di volume nel programma.
    """
    if elements.shape[1] == 8:
        volumi = quality.hex_volumes(nodes, elements)
    else:
        volumi = quality.tet_volumes(nodes, elements[:, :4])
    return float(np.abs(volumi).sum())


def risolvi(
    out_dir: Path,
    deck: Path,
    cfg: AnalysisConfig,
    nodes: np.ndarray,
    elements: np.ndarray,
    element_type: str,
    *,
    casi_di_carico: list[str],
    vincolo_in_pianta: dict[str, float],
) -> dict[str, object]:
    """Step 13: esegue `ccx` sul deck e scrive i campi in `13_solution.vtu`.

    Un solutore assente non e' un fallimento (PRODUCT.md dichiara utenti
    successivi confermati senza CalculiX): la funzione lo dice e esce, senza
    scrivere alcun artefatto numerato.

    Contratto delle chiavi di `point_data`, letto da `pipeline.run` per
    decidere se registrare l'artefatto e dai Task 8/9 per portare il campo al
    viewport: `U_<CASO>` (vettore, spostamento nodale) e `VM_<CASO>` (scalare,
    tensione equivalente) per ciascun passo statico -- `<CASO>` e' il nome che
    `abaqus.write_inp` da' al passo ("GRAVITA" di norma, "SPINTA_ORIZZONTALE",
    "CARICO_TOP"); `MODO_<n>` (vettore, forma non dimensionale) per l'n-esimo
    modo. Un blocco modale non produce mai `U_`/`VM_`: la forma e' normalizzata
    sulla massa, non uno spostamento fisico (vedi il docstring del modulo).

    `casi_di_carico` traduce il numero di passo del `.frd` (che non porta un
    nome, solo un numero) nell'etichetta del caso: e' `metrics["11_export"]
    ["casi_di_carico"]`, cioe' l'ordine che `abaqus.export_model` ha scritto
    *davvero* nel deck, letto qui e non ri-derivato. Prima di questo modulo
    aveva una propria `_casi_statici` che rifaceva lo stesso calcolo in
    proprio, accoppiata a `export_model` solo da un commento («deve restare
    la stessa derivazione»): un riordino dei passi in `write_inp` senza
    toccare questo file avrebbe etichettato un caso col nome sbagliato in
    silenzio. Una sola origine chiude l'esposizione per costruzione, non per
    promessa. Il modale, se presente, e' l'ultima voce della lista e viene
    scartato qui: i suoi blocchi si riconoscono da `Blocco.modale`, non da
    un'etichetta di passo. Nessun predefinito (giro di correzione del Task 7):
    un deck senza casi non e' uno stato rappresentabile con `None` -- con
    quel predefinito, `ccx` presente eseguiva davvero e scartava in silenzio
    ogni blocco statico letto (`[nome for nome in (None or ()) if nome !=
    "MODALE"]` da' `[]`). E' un errore del chiamante, e si dichiara come tale.

    `vincolo_in_pianta` e' `metrics["11_export"]["constraint_plan_extent"]`,
    gia' calcolato allo step 11 su `abaqus.constraint_plan_extent`: non si
    ricalcola qui, dove non arrivano i `node_sets` per farlo.

    Aggiunge `metrics["13_solve"]["controlli"]` (Task 7): cinque verdetti
    che dicono quando i numeri qui sopra non sono citabili -- `reazioni`
    (equilibrio del solo peso proprio, passo 1, sempre isolabile per
    costruzione di `abaqus.write_inp`), `vincolo_in_pianta` (soglia
    `_SOGLIA_VINCOLO_IN_PIANTA`, costante di modulo -- vedi il commento sopra la
    sua definizione), `autovalori`, `avvisi` (zero per essere
    citabili), `picco` (per caso di carico, dove vive il picco di tensione,
    non se e' alto). Sotto soglia i risultati restano scritti: si marcano,
    non si nascondono.
    """
    if not casi_di_carico:
        raise ValueError(
            "casi_di_carico e' vuoto: nessun caso da risolvere. Un deck senza "
            "casi e' un errore del chiamante, non uno stato da eseguire a vuoto"
        )
    out_dir = Path(out_dir)
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        return {"eseguito": False, "solutore": "assente"}

    deck = Path(deck)
    processo = subprocess.run(
        [eseguibile, "-i", deck.stem],
        cwd=deck.parent,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )
    uscita = processo.stdout + processo.stderr
    percorso_log = out_dir / "13_solver.log"
    percorso_log.write_text(uscita, encoding="utf-8")
    if processo.returncode != 0:
        raise RuntimeError(
            f"ccx e' terminato con codice {processo.returncode} su {deck.name}:\n{uscita[-2000:]}"
        )

    percorso_frd = out_dir / "13_solution.frd"
    percorso_dat = out_dir / "13_solution.dat"
    percorso_frd.write_bytes(deck.with_suffix(".frd").read_bytes())
    percorso_dat.write_bytes(deck.with_suffix(".dat").read_bytes())

    casi_statici = [nome for nome in casi_di_carico if nome != "MODALE"]
    etichetta_passo = dict(enumerate(casi_statici, start=1))
    blocchi = leggi_frd(percorso_frd)

    n_nodi = len(nodes)
    point_data: dict[str, np.ndarray] = {}
    casi: dict[str, dict[str, float]] = {}
    picco_per_caso: dict[str, dict[str, object]] = {}
    altezza = float(np.ptp(nodes[:, 2])) if n_nodi else 0.0
    banda_vincolo = _FRAZIONE_BANDA_VINCOLO * altezza
    n_modi = 0
    for blocco in blocchi:
        if blocco.modale:
            if blocco.grandezza != "DISP":
                continue
            n_modi += 1
            campo = np.zeros((n_nodi, 3))
            campo[blocco.nodi - 1] = blocco.dati
            point_data[f"MODO_{n_modi}"] = campo
            continue
        caso = etichetta_passo.get(blocco.passo)
        if caso is None:
            continue
        if blocco.grandezza == "DISP":
            campo = np.zeros((n_nodi, 3))
            campo[blocco.nodi - 1] = blocco.dati
            point_data[f"U_{caso}"] = campo
            casi.setdefault(caso, {})["u_max"] = float(np.linalg.norm(blocco.dati, axis=1).max())
        elif blocco.grandezza == "STRESS":
            equivalente = von_mises(blocco.dati)
            campo = np.zeros(n_nodi)
            campo[blocco.nodi - 1] = equivalente
            point_data[f"VM_{caso}"] = campo
            casi.setdefault(caso, {})["vm_max"] = float(equivalente.max())
            picco_per_caso[caso] = controlla_picco(
                equivalente, nodes[blocco.nodi - 1, 2], banda=banda_vincolo
            )

    percorso_vtu = out_dir / "13_solution.vtu"
    abaqus.write_vtu(percorso_vtu, nodes, elements, element_type=element_type, point_data=point_data)

    avvisi = uscita.upper().count("*WARNING")
    frequenze_hz = leggi_frequenze(percorso_dat)
    massa = float(cfg.material.density) * _volume_totale(nodes, elements)
    peso_atteso = (0.0, 0.0, massa * cfg.gravity)
    reazioni_peso_proprio = leggi_reazioni(percorso_dat, passo=1)
    controlli = {
        "reazioni": controlla_reazioni(reazioni_peso_proprio, peso_atteso, tolleranza=_TOLLERANZA_REAZIONI),
        "vincolo_in_pianta": {
            "passato": vincolo_in_pianta["minimo"] >= _SOGLIA_VINCOLO_IN_PIANTA,
            "minimo": vincolo_in_pianta["minimo"],
            "soglia": _SOGLIA_VINCOLO_IN_PIANTA,
        },
        "autovalori": controlla_autovalori(frequenze_hz),
        "avvisi": {"passato": avvisi == 0, "conteggio": avvisi},
        "picco": {
            "passato": all(v["passato"] for v in picco_per_caso.values()) if picco_per_caso else False,
            **picco_per_caso,
        },
    }

    return {
        "eseguito": True,
        "returncode": processo.returncode,
        "avvisi": avvisi,
        "errori": uscita.upper().count("*ERROR"),
        "casi": casi,
        "controlli": controlli,
        "modi": n_modi,
        "frequenze_hz": frequenze_hz,
        "vtu": str(percorso_vtu),
        "frd": str(percorso_frd),
        "dat": str(percorso_dat),
        "log": str(percorso_log),
    }
