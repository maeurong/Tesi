"""Server locale: pilota il core, non lo reimplementa.

Ogni numero che serve viene da metrics.json o dalle funzioni di core; ogni
parametro che scrive passa dai modelli di config.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Annotated, get_args

import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
)

from meshrec.app.worker import Worker
from meshrec.core import io, pipeline, quality, report, segment, steps, sweep, viewport
from meshrec.core.config import (
    InputConfig,
    PipelineConfig,
    RunConfig,
    SegmentConfig,
    ViewportConfig,
    load_config,
    save_config,
)
from meshrec.core.io import scrivi_atomico

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

# Mai dentro una cartella di corsa: runs/muro, runs/lab_crop, runs/sweep,
# experiments/muro ed experiments/lab_crop sono di sola lettura e contengono
# la tabella sperimentale della tesi. Percorso relativo come run.out_dir:
# risolto rispetto alla cartella da cui gira il server (meshrec/).
CACHE_DIR = Path(".cache/viewport")

# Incrementala quando cambia il modo in cui il contorno viene calcolato: il
# verso delle facce (quality._TET_FACES) o la regola di compattazione dei
# vertici (np.unique(..., return_inverse) in _contorno_del_volume). La chiave
# (sorgente, mtime) e' completa come parametri ma non registra il codice che ha
# prodotto la voce: senza incremento, ogni voce gia' su disco continuerebbe a
# rispondere col risultato vecchio per tutta la vita del file sorgente, che e'
# «restituisce in silenzio il risultato di qualcun altro». Entra nel nome, non
# nel contenuto, perche' _rimuovi_voci_vecchie sfratta per marchio e non guarda
# che cosa segue: cambiare la versione basta a far ripulire le voci precedenti.
VERSIONE_CONTORNO = 2


def _percorso_contorno(sorgente: Path) -> Path:
    """Voce di cache del contorno di un volume, con chiave (sorgente, versione, mtime).

    Duplica in piccolo viewport._cache_path, che non e' riusabile qui: la sua
    chiave porta budget, spacing_sample e seed, che l'estrazione del contorno
    non ha (dipende solo dal file), e il suo formato salva punti e gruppi di
    lunghezza variabile, non vertici e facce.

    Sottocartella propria, e non la stessa di viewport: _rimuovi_voci_vecchie
    cancella ogni altra voce che porta il marchio della sorgente, e il marchio
    e' l'hash del solo percorso. Nella stessa cartella la nuvola e il contorno
    di uno stesso file si sfratterebbero a vicenda ad ogni scrittura, e il
    ritorno del ricalcolo da dodici secondi non avrebbe alcun segnale. Oggi non
    accade perche' read_cloud rifiuta un .vtu, cioe' per una ragione che sta in
    un altro modulo: separare le cartelle non dipende da quella ragione.
    """
    sorgente = Path(sorgente)
    marchio = hashlib.sha256(str(sorgente.resolve()).encode("utf-8")).hexdigest()[:16]
    return (
        Path(CACHE_DIR)
        / "contorno"
        / f"{marchio}-{VERSIONE_CONTORNO}-{sorgente.stat().st_mtime_ns}.npz"
    )


def _leggi_contorno(voce: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Una voce assente o corrotta non e' un errore: si ricalcola, come _leggi_cache."""
    if not voce.exists():
        return None
    try:
        with np.load(voce, allow_pickle=False) as dati:
            vertici, facce, indici = dati["vertici"], dati["facce"], dati["indici"]
        if len(facce) and facce.max() >= len(vertici):
            # Come _leggi_cache col suo offsets: un indice fuori misura non
            # solleva mai in numpy, quindi va negato qui. Senza, la voce arriva
            # al browser con un 200 e three.js disegna fuori dall'attributo
            # position, senza un errore e senza un messaggio. Zero facce e' una
            # voce valida e max() su un array vuoto solleverebbe: il len() a
            # sinistra la lascia passare.
            raise ValueError("facce incoerenti con i vertici")
        if len(indici) != len(vertici):
            # L'argomento di sopra vale di piu' per indici, non di meno: e'
            # l'unico dei tre che indicizza un array diverso
            # (griglia.point_data, non vertici), e /api/campo lo usa per
            # ritagliare il campo sui nodi del contorno. Lungo o corto con
            # valori tutti in dominio, numpy non solleva: il campo esce di una
            # lunghezza che non e' quella dei vertici, e il colore si posa
            # sfalsato di un nodo senza che nessuno lo dica. Il client se ne
            # accorge solo quando le due lunghezze differiscono; se il ritaglio
            # sfalsato ne restituisse una giusta, non se ne accorgerebbe
            # nessuno.
            raise ValueError("indici incoerenti con i vertici")
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        return None
    return vertici, facce, indici


def _scrivi_contorno(voce: Path, vertici: np.ndarray, facce: np.ndarray, indici: np.ndarray) -> bool:
    """Vero se la voce e' finita su disco. Il chiamante ci lega la pulizia (MI-2)."""

    def scrittore(destinazione: Path) -> None:
        np.savez(str(destinazione), vertici=vertici, facce=facce, indici=indici)

    try:
        scrivi_atomico(voce, scrittore)
    except OSError:
        # Come in viewport._scrivi_cache: due richieste sovrapposte condividono
        # il nome del temporaneo. Una cache che non riesce a scriversi costa un
        # ricalcolo alla prossima chiamata, mai una richiesta fallita.
        return False
    return True


def _contorno_del_volume(
    percorso: Path, griglia=None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vertici, triangoli e indici dei nodi originali del contorno di una mesh
    di volume, con cache su disco.

    `griglia`: la stessa mesh gia' letta dal chiamante, quando ce l'ha. A cache
    fredda il .vtu si leggeva due volte per richiesta — una in `campo()` per i
    campi di soluzione, una qui per il contorno — su un file da 8,58 MB
    (13_solution.vtu di runs/lab_telaio_v2, misurato il 22/08/2026) e con un
    picco che su lab_crop il commento a VERSIONE_CONTORNO dichiara oltre il
    gigabyte. Due letture intere sul primo clic del pannello Campo, che e'
    quello della dimostrazione. Il ramo a cache calda non tocca la griglia e
    non la legge affatto: passarla non costa niente a chi ce l'ha gia' e non
    obbliga chi non ce l'ha.

    Su lab_crop l'estrazione costa circa 15 s e oltre un gigabyte di picco, e
    senza cache ogni clic sullo step 9 la rifa' identica. La chiave e' la sola
    coppia (sorgente, mtime) perche' l'estrazione non ha altri ingressi: non
    legge la configurazione e non ha parametri.

    Il terzo elemento (indici) e' cio' che serve alla Fase 5 per portare un
    campo per nodo (spostamenti, tensioni) fino ai vertici del contorno senza
    ricalcolarlo altrove: `vertici[i]` e' sempre `griglia.points[indici[i]]`,
    quindi un campo scritto su `griglia.points` si legge con `campo[indici]`.
    """
    import meshio

    voce = _percorso_contorno(percorso)
    trovato = _leggi_contorno(voce)
    if trovato is not None:
        return trovato

    if griglia is None:
        griglia = meshio.read(percorso)
    if "tetra" not in griglia.cells_dict:
        raise ValueError(
            f"{percorso.name} non contiene tetraedri: le celle sono {sorted(griglia.cells_dict)}"
        )
    tetraedri = griglia.cells_dict["tetra"]
    # quality._TET_FACES: la stessa convenzione, non una copia. E' privata, ma
    # da lei dipende il verso uscente delle facce e due copie di una
    # convenzione che decide un segno prima o poi divergono.
    facce_tutte = np.vstack([tetraedri[:, list(schema)] for schema in quality._TET_FACES])
    # L'ordinamento serve solo a confrontare le facce e perde il verso.
    # return_index riporta la faccia originale, quindi l'orientamento
    # uscente degli schemi qui sopra sopravvive al conteggio.
    _ordinate, primo, conteggi = np.unique(
        np.sort(facce_tutte, axis=1), axis=0, return_index=True, return_counts=True
    )
    # Una faccia che appartiene a un solo tetraedro sta sul contorno: e' la
    # stessa definizione che quality.boundary_edges applica agli spigoli di
    # una superficie.
    contorno = facce_tutte[primo[conteggi == 1]]
    # Solo i nodi che il contorno tocca: griglia.points porta anche quelli
    # interni, che nessun triangolo disegna, e X-Vertices direbbe un numero
    # che nessuna lettura sostiene.
    usati, rimappate = np.unique(contorno, return_inverse=True)
    # I tipi del trasporto gia' qui, non solo nella risposta: cosi' la cache
    # calda e quella fredda restituiscono gli stessi byte invece di far
    # dipendere la precisione da quale delle due strade ha risposto.
    vertici = np.ascontiguousarray(griglia.points[usati], dtype="<f4")
    facce = np.ascontiguousarray(rimappate.reshape(contorno.shape), dtype="<u4")
    indici = np.ascontiguousarray(usati, dtype="<u4")
    # MI-2: la pulizia solo se la scrittura e' riuscita. Sfrattare la voce
    # vecchia quando la nuova non esiste lascia la cache vuota e costa un
    # ricalcolo da quindici secondi, mai un dato sbagliato. viewport ha lo
    # stesso schema e non e' modificabile da qui: i due divergono apposta.
    if _scrivi_contorno(voce, vertici, facce, indici):
        viewport._rimuovi_voci_vecchie(voce.parent, voce)
    return vertici, facce, indici


def _non_booleano(valore: object) -> object:
    """True e False non sono coordinate, ma pydantic li accetta come float.

    `bool` e' sottotipo di `int` per Python, quindi `{"min": [true, false, true]}`
    passava il confine e finiva in configurazione come `(1.0, 0.0, 1.0)`: un tipo
    sbagliato scritto sul disco, che e' esattamente cio' che B-1 vietava. Il
    controllo sta prima della conversione, perche' dopo il booleano non esiste
    piu'. I numeri scritti come stringhe restano accettati apposta: `"1.0"` e' un
    numero espresso male, `true` non e' un numero.
    """
    if isinstance(valore, bool):
        raise ValueError("un booleano non è una coordinata: attesa una misura in mm")
    return valore


Coordinata = Annotated[float, BeforeValidator(_non_booleano)]


class BoxRitaglio(BaseModel):
    """Il corpo di POST /api/crop, verificato prima di toccare la configurazione.

    Tipizzato invece di dict[str, list[float]] apposta: cosi' e' FastAPI a
    rifiutare arita' sbagliata, chiave mancante e valore non numerico, con un
    messaggio che dice quale campo e perche', e la tratta non arriva mai ad
    assegnare. Senza, l'assegnazione finiva su SegmentConfig, che non ha
    validate_assignment e quindi non verifica nulla; numpy trasmetteva
    (N,3) >= (1,) senza lamentarsi; save_config usa model_dump, che non valida,
    e scriveva su disco una tupla di uno in un campo dichiarato di tre. Da li'
    in poi load_config rifiutava la corsa e l'interfaccia restava morta.

    NaN e Infinity restano fuori di qui e li guarda `_estremi_finiti`: json
    non li ammette in uscita, e il corpo del 422 di FastAPI riporta il valore
    ricevuto. Rifiutarli con `allow_inf_nan=False` farebbe quindi fallire la
    codifica della risposta, e a video arriverebbe «Out of range float values
    are not JSON compliant» invece del nome del campo — misurato, non dedotto.
    """

    model_config = ConfigDict(extra="forbid")

    min: tuple[Coordinata, Coordinata, Coordinata]
    max: tuple[Coordinata, Coordinata, Coordinata]


def _estremi_finiti(box: BoxRitaglio) -> None:
    """NaN e Infinity fuori dal box: sono float per pydantic e non coordinate.

    json.loads li legge, quindi arrivano davvero. Il messaggio dice quale
    estremo e quale asse, come le altre tratte del modulo: «KeyError: 'max'»
    era la forma da cui non si capiva dove guardare.
    """
    for nome, estremo in (("min", box.min), ("max", box.max)):
        for asse, coordinata in zip("xyz", estremo):
            if not math.isfinite(coordinata):
                raise ValueError(
                    f"la coordinata {asse} di '{nome}' vale {coordinata} e non un numero finito: "
                    "il box va dato in coordinate della nuvola, nelle unità di lavoro (mm)"
                )


@lru_cache(maxsize=1)
def _ingresso_del_ritaglio(sorgente: Path, _mtime_ns: int, vicini: int, scarto: float) -> np.ndarray:
    """La nuvola come lo step 2 la vede un istante prima di ritagliarla.

    Riproduce la tratta, non la funzione: `segment.segment_cloud` legge
    l'artefatto dello step 1 e fa remove_outliers e poi crop_box, in
    quest'ordine. Un'anteprima che ritagliasse 02_segmented.ply
    lavorerebbe su un file gia' ripulito e gia' ritagliato, e allargando il box
    non potrebbe far tornare indietro nessun punto; una che ritagliasse
    01_cloud.ply e basta sovrastimerebbe, perche' terrebbe gli outlier che lo
    step toglie prima. Il ritaglio resta di segment.crop_box: qui non ce n'e'
    una seconda copia da tenere allineata.

    Misurato su runs/lab_crop, 6 329 096 punti: 0,70 s di lettura piu' 25,86 s
    di remove_outliers. Senza memoria ogni ritocco del box li ripagherebbe
    interi, e il pannello del ritaglio si usa proprio ritoccando.

    _mtime_ns sta nella chiave e non nel corpo: e' quello che fa scadere la
    voce quando lo step 1 riscrive l'artefatto.

    Il tetto: una voce sola, in memoria, viva quanto il processo — circa 146 MB
    per la nuvola di lab_crop. Due corse usate a turno se la scambiano e
    ripagano i 26 s ogni volta; alzare maxsize costa un'altra nuvola intera.
    L'array torna condiviso fra i chiamanti: crop_box lo legge e copia i punti
    scelti, non lo modifica.
    """
    punti, _normali = io.read_cloud(sorgente)
    puliti, _metriche = segment.remove_outliers(
        punti, SegmentConfig(outlier_neighbors=vicini, outlier_std_ratio=scarto)
    )
    return puliti


# Il nome di una corsa diventa il nome di una cartella dentro `runs/`. Il
# vincolo non e' cosmetico: senza, un nome come `../fuori` scriverebbe fuori
# dalla radice, e uno con una barra creerebbe un annidamento che l'elenco non
# ritroverebbe piu'. Stessa forma del vincolo su `Material.name`, piu' il
# divieto esplicito su `.` e `..`: il punto e' un carattere ammesso dalla
# tabella (`lab.v2` e' un nome legittimo), quindi il solo pattern lascia
# passare proprio le due voci che risalgono l'albero.
NOME_CORSA = r"^[A-Za-z0-9_.-]+$"

# Il file che marca una corsa come di riferimento. Vive nella cartella della
# corsa e non in un elenco dentro il codice: cosi' la protezione viaggia con la
# cartella, e chi la copia altrove se la porta dietro.
SENTINELLA_SOLA_LETTURA = "SOLA_LETTURA"

# I nomi con cui il server accetta di essere chiamato. `ServerConfig.host` e'
# 127.0.0.1: qualunque altro nome nell'Host significa che la richiesta e'
# passata per una risoluzione che non e' quella dell'utente.
NOMI_LOCALI = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})

# Il selettore file di sistema, per il campo del percorso nella schermata
# d'ingresso. Sfogliare e' una comodita' e non l'unica strada: il campo resta
# scrivibile, e chi lavora da remoto o incolla un percorso non passa di qui.
#
# Gira in un SOTTOPROCESSO e non nel server, per due ragioni che non sono
# stilistiche:
#   1. su macOS Tk pretende il thread principale del processo, e FastAPI
#      esegue gli endpoint sincroni in un threadpool. Chiamare tkinter li'
#      dentro non fa cadere la richiesta: fa cadere il processo.
#   2. un dialogo lasciato aperto terrebbe occupato quel thread per sempre.
#      Un sottoprocesso ha il proprio timeout e si uccide.
#
# Il percorso torna su stdout e nient'altro finisce li': gli avvisi di Tk vanno
# su stderr, e mescolarli al risultato darebbe un percorso che non esiste.
_SELETTORE = """
import sys
import tkinter
from tkinter import filedialog

radice = tkinter.Tk()
radice.withdraw()
# Senza questo la finestra nasce dietro al browser e sembra che il clic non
# abbia fatto niente.
radice.attributes("-topmost", True)
scelto = filedialog.askopenfilename(
    parent=radice,
    title="MeshRec - scegli la nuvola di punti",
    initialdir=sys.argv[1],
    filetypes=[("Nuvole di punti", "*.pcd *.ply *.xyz"), ("Tutti i file", "*")],
)
radice.destroy()
sys.stdout.write(scelto or "")
"""

# Due minuti: il dialogo e' un'azione umana e non una richiesta di rete, ma
# senza un tetto un sottoprocesso dimenticato resterebbe fino allo spegnimento.
SECONDI_SELETTORE = 120


class CartellaIniziale(BaseModel):
    """Da dove aprire il selettore. Vuoto: la cartella da cui gira il server."""

    model_config = ConfigDict(extra="forbid")

    iniziale: str = ""


def _riga_decisiva(stderr: str) -> str:
    """L'ultima riga non vuota di una traccia: quella che dice che cosa e'
    successo, senza le venti che dicono da dove."""
    righe = [riga.strip() for riga in stderr.splitlines() if riga.strip()]
    return righe[-1] if righe else "nessun dettaglio"


def _non_e_un_passo_dell_albero(nome: str) -> str:
    """Rifiuta i nomi fatti di soli punti.

    Il punto e' un carattere ammesso dalla tabella -- `lab.v2` e' un nome
    legittimo -- quindi il solo pattern lascia passare `.`, `..` e `...`.
    I primi due risalgono l'albero; il terzo su POSIX e' una cartella
    letterale, ma su Win32 i punti finali vengono normalizzati via. La regola
    che li copre tutti e' una: un nome non e' un passo dell'albero.
    """
    if not nome.strip("."):
        raise ValueError(
            f"'{nome}' non è un nome di corsa: è un passo dell'albero delle cartelle"
        )
    return nome


def _modello_del_blocco(annotazione: object) -> type:
    """Il modello annidato di un blocco di `PipelineConfig`.

    `analysis` puo' essere assente, quindi la sua annotazione e'
    `AnalysisConfig | None`: i campi stanno sul modello, non sull'unione, e
    leggerli dall'annotazione grezza faceva cadere `/api/schema` -- cioe' il
    pannello degli step 11 e 13 -- con un `AttributeError` fuori vista.
    """
    return next(t for t in get_args(annotazione) or (annotazione,) if t is not type(None))


def _rifiuto_leggibile(errore: Exception) -> str:
    """Una riga che dice che cosa non va, non il verbale del validatore.

    `str(ValidationError)` sono cinque righe con il tipo interno, il valore
    ricevuto e un collegamento alla documentazione di pydantic; rese dentro un
    `<small>` collassano in una riga sola e illeggibile. Chi apre il programma
    deve leggere quale campo e perche', non imparare pydantic.
    """
    if isinstance(errore, ValidationError) and errore.errors():
        voce = errore.errors()[0]
        campo = ".".join(str(pezzo) for pezzo in voce["loc"]) or "la configurazione"
        return f"{campo}: {voce['msg']}"
    return f"{type(errore).__name__}: {errore}"


NomeCorsa = Annotated[
    str,
    Field(pattern=NOME_CORSA, min_length=1, max_length=64),
    AfterValidator(_non_e_un_passo_dell_albero),
]


class NuovaCorsa(BaseModel):
    """Tutto cio' che serve per far nascere una corsa: un nome e una nuvola."""

    model_config = ConfigDict(extra="forbid")

    nome: NomeCorsa
    nuvola: Path


class CorsaScelta(BaseModel):
    """La corsa gia' su disco da legare all'applicazione."""

    model_config = ConfigDict(extra="forbid")

    nome: NomeCorsa


def create_app(
    config_path: Path | None = None,
    radice_corse: Path = Path("runs"),
    radice_esperimenti: Path = Path("experiments"),
) -> FastAPI:
    """Applicazione legata a un file di configurazione, che e' la corsa corrente.

    Il legame e' mutabile e puo' nascere vuoto. `serve` senza argomenti apre
    l'interfaccia su nessuna corsa: si sceglie una cartella di `runs/` o si
    crea una corsa nuova da un file di punti, e da li' in poi tutto il resto
    del server lavora come prima su `config_path`. Chi passa gia' un percorso
    (la forma vecchia, `serve config.yaml`) trova l'applicazione legata
    all'avvio, come e' sempre stato.

    `radice_corse` e' la cartella dove le corse nascono e dove vengono cercate;
    `radice_esperimenti` quella dei registri di sweep della galleria. Relative
    come `run.out_dir` e `CACHE_DIR`: risolte rispetto alla cartella da cui gira
    il server, non rispetto al file di configurazione. La galleria le cercava
    accanto al config, e bastava aprire una configurazione che non stesse alla
    radice del progetto -- oggi ogni corsa nuova, che vive in
    `runs/<nome>/config.yaml` -- perche' sparisse senza dire perche'.
    """
    config_path = Path(config_path) if config_path is not None else None
    radice_corse = Path(radice_corse)
    radice_esperimenti = Path(radice_esperimenti)
    app = FastAPI(title="MeshRec", docs_url=None, redoc_url=None)

    def corrente() -> PipelineConfig:
        if config_path is None:
            raise ValueError(
                "nessuna corsa aperta: scegline una fra quelle di "
                f"'{radice_corse}' oppure creane una da un file di punti"
            )
        return load_config(config_path)

    def lega(percorso: Path) -> None:
        nonlocal config_path
        # Letta prima di legare: una configurazione illeggibile non deve
        # lasciare l'applicazione appesa a un percorso che nessun endpoint
        # riuscira' piu' a caricare.
        load_config(percorso)
        config_path = percorso
        # `mappe` e' indicizzata sul solo numero di step: senza questa riga, dopo
        # un cambio di corsa `/api/cluster` troverebbe la mappa di decimazione
        # della corsa precedente, la guardia `if not gruppi` resterebbe
        # soddisfatta, e la risposta sarebbe un cluster plausibile e sbagliato.
        mappe.clear()

    def sola_lettura() -> bool:
        """Vero se la corsa aperta porta il file sentinella `SOLA_LETTURA`.

        `runs/muro` e `runs/lab_crop` sono le corse di riferimento della tesi.
        Prima bastava un clic nell'elenco per legarle e da li' ogni bottone ci
        scriveva dentro; la sentinella le apre in lettura e ferma le tratte che
        scrivono.
        """
        return config_path is not None and (config_path.parent / SENTINELLA_SOLA_LETTURA).exists()

    def non_in_sola_lettura(azione: str) -> None:
        if sola_lettura():
            raise ValueError(
                f"'{nome_corrente() or config_path.parent}' è una corsa di riferimento, "
                f"aperta in sola lettura: {azione} la modificherebbe. Toglile il file "
                f"{SENTINELLA_SOLA_LETTURA} se vuoi davvero riscriverla, oppure creane una nuova"
            )

    def nome_corrente() -> str | None:
        """Il nome della corsa aperta, se e' una delle corse di `radice_corse`.

        `serve casi/lab_telaio.yaml` apre una configurazione che non sta in
        `runs/`: non e' una voce dell'elenco, e restituire «casi» segnerebbe
        come corrente una riga che non esiste.
        """
        if config_path is None:
            return None
        cartella = config_path.parent
        if cartella.resolve().parent != radice_corse.resolve():
            return None
        return cartella.name

    @app.middleware("http")
    async def solo_dal_calcolatore_locale(richiesta, prosegui):
        """Rifiuta le richieste che non arrivano da un nome locale.

        Il CSRF classico e' gia' chiuso: i corpi sono `application/json`,
        quindi il browser fa il preflight, e nessuna intestazione CORS torna.
        Resta il DNS rebinding, che fa risolvere un dominio ostile su
        127.0.0.1 e rende le richieste same-origin, saltando il preflight: da
        li' una pagina qualunque enumererebbe i percorsi assoluti del disco
        (`/api/corse`), creerebbe corse e lancerebbe sottoprocessi.

        Il nome, non l'indirizzo del chiamante: e' l'`Host` che il rebinding
        controlla e che l'origine legittima non puo' falsificare dal browser.
        """
        nome = (richiesta.headers.get("host") or "").split(":")[0].strip("[]").lower()
        if nome and nome not in NOMI_LOCALI:
            return JSONResponse(
                status_code=403,
                content={
                    "errore": "HostNonLocale",
                    "messaggio": (
                        f"richiesta arrivata con Host '{nome}': questo server risponde "
                        "solo a localhost. Aprilo da http://127.0.0.1"
                    ),
                },
            )
        return await prosegui(richiesta)

    @app.exception_handler(Exception)
    async def nessuna_eccezione_verso_il_browser(_richiesta, errore: Exception):
        # Il contratto vale sulla tratta: nessun endpoint solleva verso il
        # browser. L'errore torna strutturato, con il tipo, perche'
        # l'interfaccia possa dirlo invece di mostrare una pagina bianca.
        return JSONResponse(
            status_code=400,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )

    @app.get("/")
    def interfaccia() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    @app.get("/ui/{nome:path}")
    def statico(nome: str) -> FileResponse:
        percorso = (UI_DIR / nome).resolve()
        if not percorso.is_relative_to(UI_DIR) or not percorso.is_file():
            raise FileNotFoundError(f"nessun file dell'interfaccia chiamato {nome}")
        return FileResponse(percorso)

    @app.get("/api/run")
    def stato_corsa() -> dict[str, object]:
        # Nessuna corsa non e' un errore: e' lo stato in cui il programma si
        # apre la prima volta. Rispondere 400 qui farebbe nascere l'interfaccia
        # da una pagina rossa invece che dalla schermata d'ingresso.
        if config_path is None:
            return {"legata": False, "corsa": None, "out_dir": None,
                    "config_path": None, "steps": None}
        cfg = corrente()
        return {
            "legata": True,
            "corsa": nome_corrente(),
            "out_dir": str(cfg.run.out_dir),
            "config_path": str(config_path),
            "steps": steps.run_state(cfg.run.out_dir, cfg),
        }

    @app.get("/api/corse")
    def elenco_corse() -> dict[str, object]:
        """Le corse trovate su disco: una cartella con un config.yaml dentro.

        Una configurazione illeggibile non fa sparire le altre: quella riga
        porta il proprio errore e resta nell'elenco, perche' una corsa rotta
        che non compare e' indistinguibile da una corsa che non e' mai esistita.
        """
        corse: list[dict[str, object]] = []
        if radice_corse.is_dir():
            for cartella in sorted(radice_corse.iterdir()):
                percorso = cartella / "config.yaml"
                if not percorso.is_file():
                    continue
                voce: dict[str, object] = {
                    "nome": cartella.name,
                    "nuvola": None,
                    "modificata": None,
                    "materiale": None,
                    "riferimento": (cartella / SENTINELLA_SOLA_LETTURA).exists(),
                    "errore": None,
                }
                # `stat()` dentro il try quanto `load_config`: un config
                # cancellato fra `is_file()` e qui faceva 400 sull'intero
                # elenco invece di perdere la sola riga che lo riguarda.
                try:
                    voce["modificata"] = percorso.stat().st_mtime
                    cfg = load_config(percorso)
                except Exception as errore:
                    voce["errore"] = _rifiuto_leggibile(errore)
                else:
                    voce["nuvola"] = str(cfg.input.path)
                    voce["materiale"] = cfg.analysis.material.name if cfg.analysis else None
                corse.append(voce)
        return {"radice": str(radice_corse), "corse": corse, "corrente": nome_corrente()}

    @app.post("/api/corse")
    def crea_corsa(richiesta: NuovaCorsa) -> dict[str, object]:
        """Fa nascere una corsa dalla sola nuvola, e ci lega l'applicazione.

        Scrive `input.path` e `run.out_dir` e nient'altro: ogni altro parametro
        resta al proprio predefinito, dichiarato in `config.py`, e il materiale
        resta assente finche' non lo dichiara chi analizza.
        """
        # Prima di ogni altra cosa: `Path("")` e' `PosixPath('.')`, e senza
        # questo ramo un campo lasciato vuoto tornava indietro come
        # «'.' non e' un file», cioe' un punto comparso dal nulla.
        if not str(richiesta.nuvola).strip():
            raise ValueError("indica il percorso del file di punti da cui far nascere la corsa")
        nuvola = Path(richiesta.nuvola).expanduser()
        if not nuvola.exists():
            raise ValueError(f"nessun file di punti in '{nuvola}'")
        if not nuvola.is_file():
            raise ValueError(f"'{nuvola}' non è un file: serve una nuvola di punti")
        if not nuvola.suffix:
            raise ValueError(
                f"'{nuvola.name}' non ha estensione: servono "
                f"{', '.join(io.ESTENSIONI_NUVOLA)}"
            )
        if nuvola.suffix.lower() not in io.ESTENSIONI_NUVOLA:
            raise ValueError(
                f"'{nuvola.suffix}' non è un formato che il programma legge: "
                f"servono {', '.join(io.ESTENSIONI_NUVOLA)}"
            )
        cartella = radice_corse / richiesta.nome
        if cartella.exists():
            raise ValueError(
                f"'{richiesta.nome}' esiste già in '{radice_corse}': scegli un altro "
                "nome. Una corsa non viene mai sovrascritta"
            )
        cfg = PipelineConfig(
            input=InputConfig(path=nuvola),
            run=RunConfig(out_dir=cartella),
        )
        percorso = cartella / "config.yaml"
        save_config(cfg, percorso)
        lega(percorso)
        return stato_corsa()

    @app.put("/api/corrente")
    def apri_corsa(richiesta: CorsaScelta) -> dict[str, object]:
        percorso = radice_corse / richiesta.nome / "config.yaml"
        if not percorso.is_file():
            raise ValueError(
                f"nessuna corsa chiamata '{richiesta.nome}' in '{radice_corse}'"
            )
        lega(percorso)
        return stato_corsa()

    @app.post("/api/sfoglia")
    def sfoglia(richiesta: CartellaIniziale) -> dict[str, object]:
        """Il selettore file di sistema, per non dover scrivere il percorso.

        Apre la finestra sulla macchina dove gira il server -- che e' la stessa
        dove sta il file, e la stessa dove sta il browser: il programma e'
        locale per progetto. Un `<input type="file">` non servirebbe: il
        browser restituisce un oggetto File e nasconde la via reale
        (`C:\\fakepath\\...`), per difesa propria, quindi il percorso da
        scrivere in `input.path` non arriverebbe mai.

        Annullare non e' un errore: torna `percorso: null` e chi ha chiamato
        lascia il campo com'era.
        """
        iniziale = Path(richiesta.iniziale).expanduser() if richiesta.iniziale.strip() else None
        # Dalla cartella del percorso gia' battuto, se ne porta uno: riaprire
        # il selettore deve tornare dove si era, non alla radice ogni volta.
        if iniziale is not None and not iniziale.is_dir():
            iniziale = iniziale.parent
        if iniziale is None or not iniziale.is_dir():
            iniziale = Path.cwd()
        try:
            esito = subprocess.run(
                [sys.executable, "-c", _SELETTORE, str(iniziale)],
                capture_output=True,
                text=True,
                timeout=SECONDI_SELETTORE,
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                f"il selettore file è rimasto aperto più di {SECONDI_SELETTORE} secondi "
                "ed è stato chiuso: riprova, oppure scrivi il percorso nel campo"
            ) from None
        if esito.returncode != 0:
            # Succede senza tkinter (alcune build di Python ridotte) e senza
            # schermo a cui attaccarsi (sessione remota, servizio). Nessuno dei
            # due e' un motivo per non lavorare: il campo resta scrivibile, e
            # il messaggio lo dice invece di lasciare il bottone muto.
            raise ValueError(
                "il selettore file non si è aperto su questa macchina "
                f"({_riga_decisiva(esito.stderr)}): scrivi il percorso nel campo"
            )
        scelto = esito.stdout.strip()
        return {"percorso": scelto or None}

    @app.get("/api/config")
    def configurazione() -> dict[str, object]:
        return corrente().model_dump(mode="json")

    @app.put("/api/config")
    def scrivi_configurazione(nuova: PipelineConfig) -> dict[str, object]:
        # La validazione e' quella dei modelli: l'interfaccia non ne ha una
        # propria, e un valore fuori dominio non arriva mai alla pipeline.
        # `corrente()` prima della scrittura per la sola guardia sul legame:
        # senza, `save_config(nuova, None)` cadrebbe con un TypeError che non
        # dice quale sia il problema.
        corrente()
        non_in_sola_lettura("riscrivere la configurazione")
        save_config(nuova, config_path)
        return nuova.model_dump(mode="json")

    @app.get("/api/metrics")
    def metriche() -> dict[str, object]:
        """Le metriche cosi' come stanno sul disco. L'interfaccia non ne calcola."""
        return sweep.leggi_metriche(corrente().run.out_dir)

    @app.get("/api/wall")
    def prior_geometrico() -> dict[str, object]:
        """Il prior come sta sul disco. Un prior non calcolato lo dichiara.

        Uno stato vuoto che insegna e non un 404 nudo: l'utente successivo non
        conosce gli step, e «non ancora calcolato, ecco come» e' l'unica
        risposta che gli serve.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            return {
                "calcolato": False,
                "motivo": (
                    "il prior geometrico non è ancora stato calcolato: è lo "
                    "step 12, e si ottiene eseguendo la corsa fino in fondo "
                    "oppure con il comando 'Calcola il prior' qui accanto"
                ),
                "prior": None,
            }
        with percorso.open(encoding="utf-8") as handle:
            return {"calcolato": True, "motivo": "", "prior": json.load(handle)}

    @app.post("/api/wall")
    def calcola_prior() -> dict[str, object]:
        corrente()
        non_in_sola_lettura("ricalcolare il prior")
        lavoratore.start_comando(["wall", str(config_path)], etichetta="prior geometrico")
        return {"avviato": "wall"}

    @app.post("/api/model/{tipo}")
    def genera_modello(tipo: str) -> dict[str, object]:
        """Genera un modello parametrico. E' un'azione, non un parametro.

        Non scrive nulla in config.yaml: se lo facesse, rigenerare un modello in
        piu' cambierebbe l'impronta di una corsa che non e' cambiata.
        """
        if tipo not in ("estruso", "primitive"):
            raise ValueError(
                f"modello '{tipo}' sconosciuto: i modelli parametrici sono "
                "'estruso' e 'primitive'. as-built è la corsa madre e non si genera"
            )
        madre = Path(corrente().run.out_dir)
        non_in_sola_lettura(f"generare il modello {tipo}")
        lavoratore.start_comando(
            ["model", str(config_path), "--tipo", tipo,
             "--out-dir", str(madre.with_name(f"{madre.name}-{tipo}"))],
            etichetta=f"modello {tipo}",
        )
        return {"avviato": tipo}

    @app.get("/api/compare")
    def confronto() -> dict[str, object]:
        """Il confronto sulle cartelle che esistono davvero.

        Le cartelle mancanti non vengono create ne' finte: il confronto dice
        quale modello manca invece di mettere un trattino in una colonna di
        numeri.
        """
        madre = Path(corrente().run.out_dir)
        cartelle = [madre] + [
            madre.with_name(f"{madre.name}-{tipo}")
            for tipo in ("estruso", "primitive")
            if madre.with_name(f"{madre.name}-{tipo}").is_dir()
        ]
        return report.confronta(cartelle)

    @app.get("/api/schema")
    def schema() -> dict[str, object]:
        """Quali parametri appartengono a quale step, con descrizione e dominio.

        Le descrizioni vengono dai modelli: sono le stesse che documentano il
        perche' di ogni predefinito misurato, e vanno mostrate accanto al
        campo invece di essere riscritte nell'interfaccia.
        """
        modelli = PipelineConfig.model_fields
        fuori: dict[str, object] = {}
        for numero, blocchi in steps.STEP_BLOCKS.items():
            campi: dict[str, object] = {}
            for blocco in blocchi:
                # `selettori` e' un `dict[NomeSet, Selettore]`, non un
                # `BaseModel`: le sue voci sono nominate dall'operatore, non
                # campi fissi da descrivere uno per uno. Niente `model_fields`
                # da leggere, quindi nessun campo da elencare per questo blocco.
                #
                # Le due meta' di questo blocco vengono da due rami e servono a
                # due casi diversi: nessuna copre l'altro, e tenerne una sola
                # reintroduce il difetto che l'altra aveva chiuso.
                # _modello_del_blocco scarta il None da `X | None` -- senza,
                # `analysis` faceva cadere /api/schema con un AttributeError,
                # cioe' spegneva il pannello degli step 11 e 13. La guardia
                # regge le annotazioni che non sono modelli affatto, come
                # questo dict, su cui _modello_del_blocco da solo prenderebbe
                # NomeSet e chiederebbe model_fields a una stringa. Il difetto
                # muto e' il peggiore dei due: esce 200 con i campi mancanti,
                # invece di sollevare dove qualcuno se ne accorge.
                annidato = _modello_del_blocco(modelli[blocco].annotation)
                if not hasattr(annidato, "model_fields"):
                    campi[blocco] = {}
                    continue
                campi[blocco] = {
                    nome: {
                        "description": campo.description or "",
                        # Un campo obbligatorio non ha predefinito: null, e non
                        # il sentinella di pydantic, che finirebbe a video come
                        # la stringa "PydanticUndefined" e somiglierebbe a un
                        # valore.
                        "default": (
                            None
                            if campo.is_required()
                            else campo.get_default(call_default_factory=True)
                        ),
                    }
                    for nome, campo in annidato.model_fields.items()
                }
            fuori[str(numero)] = {"blocchi": list(blocchi), "campi": campi}
        # Un predefinito puo' essere un Path, una tupla o un modello annidato:
        # non tutti sono serializzabili in JSON, e il pannello li mostra come
        # testo. default=str li rende senza inventarne il valore.
        return json.loads(json.dumps(fuori, default=str))

    @app.get("/api/experiments")
    def esperimenti() -> dict[str, object]:
        """Nomi degli esperimenti della Fase 2. Sola lettura: mai una scrittura.

        Una sottocartella di experiments/ senza registro.jsonl non e' un
        esperimento concluso, e resta fuori dall'elenco.
        """
        radice = radice_esperimenti
        if not radice.is_dir():
            return {"esperimenti": []}
        return {
            "esperimenti": sorted(
                voce.name for voce in radice.iterdir()
                if (voce / "registro.jsonl").exists()
            )
        }

    @app.get("/api/experiments/{nome}")
    def esperimento(nome: str) -> dict[str, object]:
        """Le righe del registro di un esperimento, per la galleria di curazione.

        Le colonne e la formattazione di ogni cella sono quelle di
        report._COLUMNS e report._cell: riusate, non riscelte. Sono le stesse
        che finiscono nell'appendice della tesi (report.write_report), e due
        elenchi di colonne che divergono sono precisamente il difetto che
        questo ramo ha gia' inseguito per giorni.
        """
        radice = radice_esperimenti.resolve()
        percorso = (radice / nome / "registro.jsonl").resolve()
        if not percorso.is_relative_to(radice) or not percorso.exists():
            raise FileNotFoundError(f"nessun registro per l'esperimento {nome}")
        righe = sweep.load_registry(percorso)
        return {
            "nome": nome,
            "righe": righe,
            "fronte": sum(1 for riga in righe if riga.get("on_front")),
            "colonne": [
                {"chiave": chiave, "etichetta": etichetta}
                for chiave, etichetta in report._COLUMNS
            ],
            "celle": [
                [report._cell(riga, chiave) for chiave, _ in report._COLUMNS]
                for riga in righe
            ],
        }

    lavoratore = Worker()

    # Le mappe dell'ultima decimazione servita, per step. Il ritaglio e la
    # selezione le rileggono: senza, agirebbero su indici che non esistono.
    mappe: dict[int, list] = {}

    @app.post("/api/step/{numero}")
    def esegui_step(numero: int) -> dict[str, object]:
        # Senza queste due righe, a legame vuoto il Worker lanciava
        # `python -m meshrec.cli run None` e restava occupato: un 200 che non
        # eseguiva niente e bloccava anche la richiesta successiva.
        corrente()
        non_in_sola_lettura(f"eseguire lo step {numero}")
        lavoratore.start(config_path, numero, numero)
        return {"avviato": numero, "fino_a": numero}

    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        # 12 e non 11 dalla Fase 4: lo step 12 e' il prior geometrico e chiude
        # la corsa madre. Il tetto qui e' una scelta dell'interfaccia, non
        # un'eredita' dal predefinito di RunConfig.to_step (13 dalla Fase 5,
        # il solutore fa parte di ogni corsa): "riprendi da qui" nel pannello
        # non deve far partire un processo esterno da solo, per lo stesso
        # motivo per cui sweep.run_candidate chiede --to-step 12 esplicito.
        corrente()
        non_in_sola_lettura(f"eseguire dallo step {numero} in giù")
        lavoratore.start(config_path, numero, 12)
        return {"avviato": numero, "fino_a": 12}

    @app.post("/api/cancel")
    def annulla() -> dict[str, object]:
        return {"annullato": lavoratore.cancel()}

    @app.post("/api/crop")
    def ritaglia(box: BoxRitaglio) -> dict[str, object]:
        """Il box disegnato nel viewport diventa segment.crop_min e crop_max.

        L'interfaccia disegna il box; la pulizia la esegue
        segment.remove_outliers e il ritaglio segment.crop_box, che sono le
        stesse funzioni che la pipeline usa allo step 2 e nello stesso ordine.
        Non c'e' una seconda implementazione da tenere allineata.

        `completo` dice fin dove l'anteprima arriva, e non e' un ornamento: con
        `method: auto` lo step 2 non finisce col ritaglio, prosegue con
        extract_planes e cluster e riscrive points_after col numero del cluster
        scelto (`segment.segment_cloud`, ramo `method == "auto"`). Su una
        nuvola di 5 050 punti sono 5 000
        contro 82. L'anteprima si ferma comunque al ritaglio, e lo dichiara
        invece di affermare il falso: il resto della tratta, misurato su
        runs/lab_crop, costa 57,76 s di extract_planes piu' 26,35 s di cluster,
        e quel costo non e' memorizzabile perche' dipende dal box, cioe' proprio
        dalla cosa che si sta ritoccando. Un pannello in cui ogni ritocco costa
        un minuto e mezzo non e' un'anteprima. La didascalia legge questo campo.

        La configurazione si scrive solo se il ritaglio e' andato a buon fine:
        un box degenere o vuoto solleva prima, e non lascia sul disco estremi
        che nessuno step potrebbe applicare.
        """
        _estremi_finiti(box)
        cfg = corrente()
        cfg.segment.crop_min = box.min
        cfg.segment.crop_max = box.max
        # I due estremi sono accoppiati e SegmentConfig non ha
        # validate_assignment: l'unico punto in cui lo stato risultante viene
        # verificato per intero e' qui, prima che finisca su disco.
        # model_validate e' la stessa che load_config applica in lettura,
        # quindi cio' che si scrive e' per costruzione rileggibile.
        cfg = PipelineConfig.model_validate(cfg.model_dump())
        # L'ingresso dello step 2, non la sua uscita: vedi _ingresso_del_ritaglio.
        sorgente = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[1]
        if not sorgente.exists():
            raise FileNotFoundError(
                f"lo step 1 non ha ancora prodotto {pipeline.ARTIFACTS[1]}: "
                "il ritaglio si misura sulla nuvola letta, che è l'ingresso dello step 2"
            )
        puliti = _ingresso_del_ritaglio(
            sorgente,
            sorgente.stat().st_mtime_ns,
            cfg.segment.outlier_neighbors,
            cfg.segment.outlier_std_ratio,
        )
        _dentro, metriche = segment.crop_box(puliti, cfg.segment)
        non_in_sola_lettura("scrivere il ritaglio")
        save_config(cfg, config_path)
        # Le metriche del core sono l'unica fonte: points_after c'e' gia'
        # dentro (`segment.crop_box`), e riscriverlo qui sarebbe una riga che
        # sembra calcolare qualcosa e non lo fa.
        #
        # `== "crop"` e non `!= "auto"`: il giorno che segment.method prendesse
        # un terzo valore, questo direbbe «incompleta» per prudenza invece di
        # promettere una coincidenza che nessuno ha verificato.
        return {**metriche, "completo": cfg.segment.method == "crop"}

    @app.get("/api/cloud/{numero}")
    def nuvola(numero: int, max_points: int | None = None) -> Response:
        """Punti decimati dello step richiesto, in binario Float32.

        Decima l'artefatto dello step chiesto e non un altro: servire al posto
        della nuvola dello step 2 quella dello step 3, che e' gia' piccola e
        pronta, mostrerebbe una nuvola diversa da quella su cui il ritaglio
        agisce.
        """
        if numero not in pipeline.ARTIFACTS:
            raise ValueError(
                f"lo step {numero} non esiste: gli step con una nuvola sono {sorted(pipeline.ARTIFACTS)}"
            )
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step {numero} non ha ancora prodotto {pipeline.ARTIFACTS[numero]}"
            )
        if max_points is not None and max_points <= 0:
            raise ValueError(f"max_points={max_points} non valido: atteso un intero positivo")
        budget = max_points if max_points is not None else ViewportConfig().max_points
        # decimate_file calcola la spaziatura al proprio interno, solo a
        # cache fredda: qui non si legge piu' la nuvola ne' si controlla la
        # cache in anticipo, perche' spacing_sample e seed sono gia' nella
        # sua chiave (vedi viewport.decimate_file).
        ridotti, gruppi, voxel = viewport.decimate_file(
            percorso, budget, cfg.input.spacing_sample, cfg.input.seed, CACHE_DIR
        )
        mappe[numero] = gruppi
        return Response(
            content=viewport.to_float32(ridotti),
            media_type="application/octet-stream",
            headers={
                "X-Points-Drawn": str(len(ridotti)),
                "X-Points-Total": str(sum(len(gruppo) for gruppo in gruppi)),
                "X-Voxel": f"{voxel:.6g}",
            },
        )

    @app.post("/api/cluster")
    def scegli_cluster(richiesta: dict[str, int]) -> dict[str, object]:
        """Dal punto disegnato al cluster_index che segment_cloud consuma.

        Il punto cliccato e' un indice della nuvola DISEGNATA (decimata),
        cioe' quella che /api/cloud/2 ha servito al browser: interpretarlo
        come indice della nuvola piena risponderebbe un cluster plausibile
        ma sbagliato, senza sollevare. La mappa che /api/cloud/2 ha salvato
        in `mappe` lo riporta a TUTTI i punti pieni del gruppo di
        decimazione (un voxel puo' contenere punti di piu' cluster): il
        rappresentante e' il cluster in maggioranza fra loro, non il primo
        punto del gruppo (task-11a-review.md misura il difetto del primo
        punto sopra qualche milione di punti).

        Il raggruppamento resta in core.segment.cluster: qui non ce n'e' una
        seconda implementazione da tenere allineata.
        """
        gruppi = mappe.get(2)
        if not gruppi:
            raise ValueError("nessuna nuvola caricata: apri prima lo step 2 nel viewport")
        disegnato = int(richiesta["punto"])
        if not 0 <= disegnato < len(gruppi):
            raise ValueError(f"il punto {disegnato} non appartiene alla nuvola disegnata")
        gruppo = gruppi[disegnato]

        cfg = corrente()
        # I punti pieni per la ricerca delle coordinate (sotto) restano quelli
        # DISEGNATI, cioe' 02_segmented.ply: e' la nuvola che /api/cloud/2 ha
        # servito e su cui gli indici di `gruppo` sono definiti.
        punti, _normali = io.read_cloud(Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2])

        # Ma la CLUSTERIZZAZIONE deve essere quella che la corsa 'auto' esegue
        # davvero (`segment.segment_cloud`), non quella di 02_segmented.ply
        # preso a se': quel file e' l'uscita del metodo 'crop' (nessun piano
        # tolto), mentre la corsa parte sempre dall'ingresso grezzo dello
        # step 2 (ARTIFACTS[1], vedi lo step 2 di `pipeline.run`) per la
        # spaziatura e per
        # remove_outliers -> crop_box -> extract_planes -> cluster, in
        # quest'ordine. Saltare extract_planes clusterizzava un insieme
        # diverso: sul dato vero, 4293 gruppi (il clic, sbagliato) contro
        # 2447 (la corsa, task-11b-allineamento.md). Nessuna cache qui,
        # apposta (vedi il mandato di questo giro): ogni clic ripaga
        # l'intera tratta, come la pagherebbe la corsa.
        sorgente_grezza = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[1]
        if not sorgente_grezza.exists():
            raise FileNotFoundError(
                f"lo step 1 non ha ancora prodotto {pipeline.ARTIFACTS[1]}: "
                "il clic clusterizza a partire dall'ingresso grezzo dello step 2"
            )
        grezzi, _normali_grezze = io.read_cloud(sorgente_grezza)
        spaziatura = io.mean_spacing(grezzi, cfg.input.spacing_sample, cfg.input.seed)
        puliti, _metriche_outlier = segment.remove_outliers(grezzi, cfg.segment)
        ritagliati, _metriche_crop = segment.crop_box(puliti, cfg.segment)
        _piani, residuo, _metriche_piani = segment.extract_planes(ritagliati, cfg.segment, spaziatura)
        insiemi, metriche = segment.cluster(residuo, cfg.segment, spaziatura)

        def cluster_del_punto_pieno(indice_pieno: int) -> int | None:
            coordinata = punti[indice_pieno]
            return next(
                (
                    indice
                    for indice, insieme in enumerate(insiemi)
                    if np.isclose(insieme, coordinata).all(axis=1).any()
                ),
                None,
            )

        # Un gruppo disegnato e' un voxel di decimazione: quando il voxel e'
        # piu' grande del raggio che separa due cluster (nuvole sopra
        # qualche milione di punti, vedi task-11a-review.md), il gruppo puo'
        # contenere punti pieni di piu' cluster. Il primo punto del gruppo e'
        # un rappresentante arbitrario; il rappresentante corretto e' la
        # MAGGIORANZA del gruppo: si vota il cluster (o il rumore, None) di
        # ogni punto pieno e vince chi ha piu' voti.
        #
        # Due casi che la maggioranza da sola non decide, dichiarati qui:
        # - pareggio fra cluster (o fra un cluster e il rumore): vince il
        #   cluster piu' popoloso IN ASSOLUTO. insiemi e' gia' ordinato per
        #   numerosita' decrescente (core.segment.cluster), quindi a parita'
        #   di voti nel gruppo l'indice piu' basso e' la scelta piu'
        #   prudente e deterministica.
        # - il rumore e' in MAGGIORANZA STRETTA (piu' voti di ogni singolo
        #   cluster): il clic e' trattato come rumore e solleva, senza
        #   scrivere. A parita' con il cluster piu' votato vince il cluster:
        #   un pareggio non e' un'evidenza sufficiente per scartare un
        #   match reale.
        voti = Counter(
            v for v in (cluster_del_punto_pieno(int(p)) for p in gruppo) if v is not None
        )
        voti_rumore = len(gruppo) - sum(voti.values())
        scelto, voti_vincitore = max(
            voti.items(), key=lambda kv: (kv[1], -kv[0]), default=(None, 0)
        )
        if scelto is None or voti_rumore > voti_vincitore:
            raise ValueError(
                "il punto cliccato ricade per lo più nel rumore: "
                "DBSCAN non assegna il gruppo a nessun cluster"
            )

        metodo_precedente = cfg.segment.method
        cfg.segment.method = "auto"
        cfg.segment.cluster_index = scelto
        non_in_sola_lettura("scegliere il cluster")
        save_config(cfg, config_path)
        return {
            "cluster_index": scelto,
            "cluster_points": int(len(insiemi[scelto])),
            "method_before": metodo_precedente,
            "method_after": cfg.segment.method,
            **metriche,
        }

    @app.get("/api/membrature")
    def membrature() -> Response:
        """Un'etichetta di membratura per punto della nuvola disegnata.

        E' la prova visiva che la scomposizione ha capito il pezzo, e si legge
        in un secondo dove nessuna metrica sarebbe cosi' rapida. -1 significa
        «nessuna membratura», che e' un'informazione e non un buco.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non è ancora stato calcolato: è lo step 12"
            )
        # Gli indici di 12_wall.json valgono per la nuvola di ARTIFACTS[2] con
        # cui il prior e' stato calcolato: se lo step 2 e' stato rifatto (un
        # ritaglio diverso) senza rifare il 12, l'impronta salvata per lo
        # step 12 non combacia piu' con quella che la configurazione corrente
        # produce, e disegnare dipingerebbe le etichette sui punti sbagliati
        # in silenzio invece di fermarsi (F5).
        stato_prior = next(v for v in steps.run_state(cfg.run.out_dir, cfg) if v["chiave"] == "12_wall")
        if stato_prior["stato"] == "non valido":
            raise ValueError(
                "il prior geometrico (step 12) è più vecchio della "
                "configurazione corrente: rilancia `meshrec wall` prima di "
                "vedere la mappa delle membrature"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        punti, gruppi, _voxel = viewport.decimate_file(
            Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2],
            ViewportConfig().max_points, cfg.input.spacing_sample, cfg.input.seed,
            CACHE_DIR,
        )
        # Etichetta per punto PIENO, letta da "indici" (wall.prior, posizioni
        # dentro ARTIFACTS[2] intera). Un gruppo di decimazione puo' contenere
        # punti pieni di piu' membrature: vince la maggioranza del gruppo, non
        # il primo punto -- lo stesso principio di /api/cluster (server.py),
        # non la stessa implementazione (li' il voto e' geometrico, qui e' gia'
        # un'etichetta per indice).
        per_punto_pieno = np.full(sum(len(gruppo) for gruppo in gruppi), -1, dtype=np.int64)
        for numero, voce in enumerate(prior["membrature"]):
            per_punto_pieno[voce["indici"]] = numero
        etichette = np.full(len(punti), -1.0)
        for disegnato, gruppo in enumerate(gruppi):
            # ponytail: fino a max_points (400.000) iterazioni con un Counter su
            # gruppi piccoli -- rapido nella pratica su lab_crop/muro. Se un
            # giorno diventasse un collo di bottiglia misurato, la stessa
            # etichettatura si vettorizza con un bincount su (indice
            # disegnato, etichetta+1).
            migliore, _voti = Counter(per_punto_pieno[gruppo].tolist()).most_common(1)[0]
            if migliore != -1:
                etichette[disegnato] = float(migliore)
        return Response(
            content=viewport.campo_per_punto(etichette),
            media_type="application/octet-stream",
            headers={"X-Punti": str(len(punti)),
                      "X-Membrature": str(len(prior["membrature"]))},
        )

    @app.get("/api/rigonfiamento")
    def rigonfiamento(membratura: int) -> dict[str, object]:
        """L'aggregato di rigonfiamento di una membratura: min, max, p95 [mm].

        Non la mappa per cella: quella vive solo in memoria dentro
        Membratura.rigonfiamento (wall.py) e non arriva su 12_wall.json, che
        serializza il solo aggregato (wall.py, voce "rigonfiamento" di
        wall.prior). Scriverla vorrebbe dire un artefatto nuovo (un .npy per
        membratura accanto al JSON, con la propria provenienza da gestire) e
        niente in questa fase la consuma: dichiarare qui dove sta e cosa
        servirebbe evita a chi la cerchera' di ripartire da zero.
        """
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.WALL_FILENAME
        if not percorso.exists():
            raise FileNotFoundError(
                "il prior geometrico non è ancora stato calcolato: è lo step 12"
            )
        with percorso.open(encoding="utf-8") as handle:
            prior = json.load(handle)
        if not 0 <= membratura < len(prior["membrature"]):
            raise ValueError(
                f"membratura {membratura} inesistente: il prior ne ha trovate "
                f"{len(prior['membrature'])}"
            )
        mappa = prior["membrature"][membratura]["rigonfiamento"]
        return {"min": mappa["min"], "max": mappa["max"], "p95": mappa["p95"], "celle": mappa["celle"]}

    @app.get("/api/mesh/{numero}")
    def mesh(numero: int) -> Response:
        """Vertici e facce in un solo corpo binario: prima i Float32 delle
        coordinate, poi gli Uint32 degli indici. I conteggi stanno nelle
        intestazioni, cosi' il browser sa dove tagliare.
        """
        if numero not in pipeline.ARTIFACTS:
            raise ValueError(
                f"lo step {numero} non esiste: gli step con un artefatto sono {sorted(pipeline.ARTIFACTS)}"
            )
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step {numero} non ha ancora prodotto {pipeline.ARTIFACTS[numero]}"
            )
        if percorso.suffix == ".vtu":
            vertici, facce, _indici = _contorno_del_volume(percorso)
        else:
            import open3d as o3d

            triangolare = o3d.io.read_triangle_mesh(str(percorso))
            vertici = np.asarray(triangolare.vertices)
            facce = np.asarray(triangolare.triangles)
        # Senza triangoli non c'e' nulla da disegnare: 01_cloud.ply letto come
        # mesh da' vertici e zero facce, e risponderebbe 200 con un solido
        # vuoto invece di dire che quell'artefatto e' una nuvola.
        if len(vertici) == 0 or len(facce) == 0:
            raise ValueError(
                f"{percorso.name} non è una mesh disegnabile: "
                f"{len(vertici)} vertici e {len(facce)} triangoli"
            )
        corpo = viewport.to_float32(vertici) + np.ascontiguousarray(facce, dtype="<u4").tobytes()
        return Response(
            content=corpo,
            media_type="application/octet-stream",
            headers={"X-Vertices": str(len(vertici)), "X-Triangles": str(len(facce))},
        )

    @app.get("/api/campo/{caso}/{grandezza}")
    def campo(caso: str, grandezza: str) -> Response:
        """Un campo dello step 13 (`solve.risolvi`), ristretto ai vertici del
        contorno con la stessa corrispondenza di /api/mesh.

        La chiave e' `f"{grandezza}_{caso}"` (contratto di `solve.risolvi`,
        es. "VM_GRAVITA"): non c'e' un elenco di casi/grandezze validi da
        tenere allineato altrove, la validita' e' la presenza della chiave in
        `point_data`. Ne' `caso` ne' `grandezza` toccano mai il filesystem
        (il percorso e' fisso, 13_solution.vtu della corsa corrente): un
        valore come '..' fallisce lo stesso controllo di appartenenza di uno
        inventato, non serve una guardia sui caratteri.

        U_<caso> e' un vettore (spostamento nodale): la magnitudine e' lo
        scalare che risponde, uno per vertice, come VM_<caso> gia' e' scalare.

        L'unica intestazione e' `X-Max`, il massimo del campo, che finisce
        nella didascalia della vista. Il p99 su cui si taglia la scala colore
        (il picco isolato di una singolarita' del maglio - misurato il
        22/08/2026 su runs/lab_telaio_v2, CARICO_TOP: 0,9811 MPa contro un p99
        di 0,3962, al rango piu' vicino sui nodi del contorno come fa il browser -
        stirerebbe la scala su un solo vertice) lo calcola il browser in `viewport.scalaDelCampo`:
        e' una
        decisione numerica, e questo progetto le prova eseguendole in node.
        Le intestazioni `X-Min`, `X-P99` e `X-Sopra-P99` c'erano e nessuno le
        leggeva: un dato che il client ignora invecchia in silenzio.
        """
        import meshio

        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[13]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step 13 non ha ancora prodotto {pipeline.ARTIFACTS[13]}"
            )
        griglia = meshio.read(percorso)
        if not griglia.point_data:
            raise ValueError(f"{percorso.name} non contiene campi di soluzione")
        chiave = f"{grandezza}_{caso}"
        if chiave not in griglia.point_data:
            if caso in griglia.point_data:
                raise ValueError(
                    f"'{caso}' è un modo, non un caso di carico: la sua forma è "
                    "normalizzata sulla massa e non ha né millimetri né MPa"
                )
            raise ValueError(
                f"nessun campo '{chiave}' in {percorso.name}: i campi disponibili "
                f"sono {sorted(griglia.point_data)}"
            )
        _vertici, _facce, indici = _contorno_del_volume(percorso, griglia)
        valori = np.asarray(griglia.point_data[chiave], dtype=np.float64)[indici]
        if valori.ndim > 1:
            valori = np.linalg.norm(valori, axis=1)
        if len(valori) == 0:
            return Response(
                content=b"",
                media_type="application/octet-stream",
                headers={"X-Max": "0.0"},
            )
        return Response(
            content=viewport.campo_per_punto(valori),
            media_type="application/octet-stream",
            headers={"X-Max": str(float(valori.max()))},
        )

    @app.get("/api/events")
    def eventi(max_eventi: int | None = None) -> StreamingResponse:
        """Avanzamento e log verso il browser. Una direzione sola, quindi SSE:
        WebSocket aggiungerebbe un secondo protocollo per traffico che va da
        una parte sola, e EventSource riconnette da solo."""

        def flusso():
            inviate = 0
            emesse = 0
            while True:
                # Nessuna corsa aperta non e' un errore qui, ed e' lo stato in
                # cui la schermata d'ingresso vive: il browser apre
                # l'EventSource al caricamento del modulo, sempre. Sollevare
                # dentro il generatore non produce nemmeno un 400 -- le
                # intestazioni sono gia' partite, e il gestore generico non le
                # puo' piu' toccare: il browser riceveva 200 con corpo vuoto e
                # riconnetteva ogni tre secondi, con una traccia per giro.
                cfg = corrente() if config_path is not None else None
                stato = {
                    "legata": cfg is not None,
                    "in_corso": lavoratore.is_running(),
                    "step": lavoratore.step,
                    "exit_code": lavoratore.exit_code,
                    "annullato": lavoratore.annullato,
                    "da_secondi": lavoratore.da_secondi(),
                    "steps": steps.run_state(cfg.run.out_dir, cfg) if cfg else [],
                }
                yield f"event: stato\ndata: {json.dumps(stato, default=str)}\n\n"
                emesse += 1
                righe = lavoratore.righe()
                for riga in righe[inviate:]:
                    yield f"event: riga\ndata: {json.dumps(riga)}\n\n"
                inviate = len(righe)
                if max_eventi is not None and emesse >= max_eventi:
                    return
                time.sleep(0.5)

        return StreamingResponse(flusso(), media_type="text/event-stream")

    return app
