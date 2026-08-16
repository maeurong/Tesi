"""Server locale: pilota il core, non lo reimplementa.

Ogni numero che serve viene da metrics.json o dalle funzioni di core; ogni
parametro che scrive passa dai modelli di config.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, BeforeValidator, ConfigDict

from meshrec.app.worker import Worker
from meshrec.core import io, pipeline, quality, report, segment, steps, sweep, viewport
from meshrec.core.config import (
    PipelineConfig,
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
VERSIONE_CONTORNO = 1


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


def _leggi_contorno(voce: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Una voce assente o corrotta non e' un errore: si ricalcola, come _leggi_cache."""
    if not voce.exists():
        return None
    try:
        with np.load(voce, allow_pickle=False) as dati:
            vertici, facce = dati["vertici"], dati["facce"]
        if len(facce) and facce.max() >= len(vertici):
            # Come _leggi_cache col suo offsets: un indice fuori misura non
            # solleva mai in numpy, quindi va negato qui. Senza, la voce arriva
            # al browser con un 200 e three.js disegna fuori dall'attributo
            # position, senza un errore e senza un messaggio. Zero facce e' una
            # voce valida e max() su un array vuoto solleverebbe: il len() a
            # sinistra la lascia passare.
            raise ValueError("facce incoerenti con i vertici")
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        return None
    return vertici, facce


def _scrivi_contorno(voce: Path, vertici: np.ndarray, facce: np.ndarray) -> bool:
    """Vero se la voce e' finita su disco. Il chiamante ci lega la pulizia (MI-2)."""

    def scrittore(destinazione: Path) -> None:
        np.savez(str(destinazione), vertici=vertici, facce=facce)

    try:
        scrivi_atomico(voce, scrittore)
    except OSError:
        # Come in viewport._scrivi_cache: due richieste sovrapposte condividono
        # il nome del temporaneo. Una cache che non riesce a scriversi costa un
        # ricalcolo alla prossima chiamata, mai una richiesta fallita.
        return False
    return True


def _contorno_del_volume(percorso: Path) -> tuple[np.ndarray, np.ndarray]:
    """Vertici e triangoli del contorno di una mesh di volume, con cache su disco.

    Su lab_crop l'estrazione costa circa 15 s e oltre un gigabyte di picco, e
    senza cache ogni clic sullo step 9 la rifa' identica. La chiave e' la sola
    coppia (sorgente, mtime) perche' l'estrazione non ha altri ingressi: non
    legge la configurazione e non ha parametri.
    """
    import meshio

    voce = _percorso_contorno(percorso)
    trovato = _leggi_contorno(voce)
    if trovato is not None:
        return trovato

    griglia = meshio.read(percorso)
    if "tetra" not in griglia.cells_dict:
        raise ValueError(
            f"{percorso.name} non contiene tetraedri: le celle sono {sorted(griglia.cells_dict)}"
        )
    tetraedri = griglia.cells_dict["tetra"]
    # quality._TET_FACES: la stessa convenzione, non una copia. E' privata, ma
    # da lei dipende il verso uscente delle facce (core/quality.py:51) e due
    # copie di una convenzione che decide un segno prima o poi divergono.
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
    # MI-2: la pulizia solo se la scrittura e' riuscita. Sfrattare la voce
    # vecchia quando la nuova non esiste lascia la cache vuota e costa un
    # ricalcolo da quindici secondi, mai un dato sbagliato. viewport ha lo
    # stesso schema e non e' modificabile da qui: i due divergono apposta.
    if _scrivi_contorno(voce, vertici, facce):
        viewport._rimuovi_voci_vecchie(voce.parent, voce)
    return vertici, facce


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
        raise ValueError("un booleano non e' una coordinata: attesa una misura in mm")
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
                    "il box va dato in coordinate della nuvola, nelle unita di lavoro (mm)"
                )


@lru_cache(maxsize=1)
def _ingresso_del_ritaglio(sorgente: Path, _mtime_ns: int, vicini: int, scarto: float) -> np.ndarray:
    """La nuvola come lo step 2 la vede un istante prima di ritagliarla.

    Riproduce la tratta, non la funzione: segment_cloud legge l'artefatto dello
    step 1 e fa remove_outliers e poi crop_box, in quest'ordine
    (core/segment.py:142-143). Un'anteprima che ritagliasse 02_segmented.ply
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


def create_app(config_path: Path) -> FastAPI:
    """Applicazione legata a un file di configurazione, che e' la corsa corrente."""
    config_path = Path(config_path)
    app = FastAPI(title="MeshRec", docs_url=None, redoc_url=None)

    def corrente() -> PipelineConfig:
        return load_config(config_path)

    @app.exception_handler(FileNotFoundError)
    async def artefatto_mancante(_richiesta, errore: FileNotFoundError):
        # Un artefatto che non c'e' non e' un guasto del server: e' lo stato
        # normale di uno step mai eseguito, ed e' cio' che l'interfaccia
        # gia' sa leggere («nessun artefatto per questo step»).
        #
        # Senza questo gestore la FileNotFoundError arrivava a quello generico,
        # registrato su Exception: Starlette lo esegue dentro
        # ServerErrorMiddleware, che manda la risposta e poi **rilancia**
        # l'eccezione perche' il server la registri. Il browser riceveva la
        # risposta giusta e il terminale un traceback completo per ogni clic su
        # uno step non ancora eseguito. Registrato sul tipo, il rifiuto passa
        # invece da ExceptionMiddleware, che non rilancia.
        #
        # La forma del corpo resta la stessa del gestore generico, cosi'
        # ragioneDelRifiuto la legge senza sapere che e' successo.
        return JSONResponse(
            status_code=404,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )

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
        cfg = corrente()
        return {
            "out_dir": str(cfg.run.out_dir),
            "config_path": str(config_path),
            "steps": steps.run_state(cfg.run.out_dir, cfg),
        }

    @app.get("/api/config")
    def configurazione() -> dict[str, object]:
        return corrente().model_dump(mode="json")

    @app.put("/api/config")
    def scrivi_configurazione(nuova: PipelineConfig) -> dict[str, object]:
        # La validazione e' quella dei modelli: l'interfaccia non ne ha una
        # propria, e un valore fuori dominio non arriva mai alla pipeline.
        save_config(nuova, config_path)
        return nuova.model_dump(mode="json")

    @app.get("/api/metrics")
    def metriche() -> dict[str, object]:
        """Le metriche cosi' come stanno sul disco. L'interfaccia non ne calcola."""
        return sweep.leggi_metriche(corrente().run.out_dir)

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
                annidato = modelli[blocco].annotation
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
        # non tutti sono serializzabili in JSON. Un modello annidato (Material,
        # per esempio) si serializza da solo in JSON quando gli si chiede
        # model_dump(mode="json"): usare str() al suo posto produrrebbe il repr
        # Python del modello, e il confronto col valore vivo (anch'esso JSON,
        # da /api/config) non potrebbe mai risultare uguale — il campo
        # risulterebbe cambiato a ogni corsa, sempre, e il repr finirebbe
        # scritto a video in un'interfaccia italiana. str() resta la via per
        # cio' che non e' un modello e che json non sa scrivere da se', come
        # Path. Una tupla non passa di qui: json.dumps la scrive come lista, e
        # `default` viene chiamato solo su cio' che non sa serializzare.
        def per_json(valore: object) -> object:
            return valore.model_dump(mode="json") if isinstance(valore, BaseModel) else str(valore)

        return json.loads(json.dumps(fuori, default=per_json))

    @app.get("/api/experiments")
    def esperimenti() -> dict[str, object]:
        """Nomi degli esperimenti della Fase 2. Sola lettura: mai una scrittura.

        Una sottocartella di experiments/ senza registro.jsonl non e' un
        esperimento concluso, e resta fuori dall'elenco.
        """
        radice = config_path.parent / "experiments"
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
        radice = (config_path.parent / "experiments").resolve()
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
        lavoratore.start(config_path, numero, numero)
        return {"avviato": numero, "fino_a": numero}

    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, 11)
        return {"avviato": numero, "fino_a": 11}

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
        scelto (core/segment.py:146-159). Su una nuvola di 5 050 punti sono 5 000
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
                "il ritaglio si misura sulla nuvola letta, che e' l'ingresso dello step 2"
            )
        puliti = _ingresso_del_ritaglio(
            sorgente,
            sorgente.stat().st_mtime_ns,
            cfg.segment.outlier_neighbors,
            cfg.segment.outlier_std_ratio,
        )
        _dentro, metriche = segment.crop_box(puliti, cfg.segment)
        save_config(cfg, config_path)
        # Le metriche del core sono l'unica fonte: points_after c'e' gia'
        # dentro (core/segment.py:59), e riscriverlo qui sarebbe una riga che
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
        # davvero (core/segment.py:146-150, segment_cloud), non quella di
        # 02_segmented.ply preso a se': quel file e' l'uscita del metodo
        # 'crop' (nessun piano tolto), mentre la corsa parte sempre
        # dall'ingresso grezzo dello step 2 (ARTIFACTS[1], vedi
        # pipeline.py:132-148) per la spaziatura e per
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
                "il punto cliccato ricade per lo piu' nel rumore: "
                "DBSCAN non assegna il gruppo a nessun cluster"
            )

        metodo_precedente = cfg.segment.method
        cfg.segment.method = "auto"
        cfg.segment.cluster_index = scelto
        save_config(cfg, config_path)
        return {
            "cluster_index": scelto,
            "cluster_points": int(len(insiemi[scelto])),
            "method_before": metodo_precedente,
            "method_after": cfg.segment.method,
            **metriche,
        }

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
            vertici, facce = _contorno_del_volume(percorso)
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
                f"{percorso.name} non e' una mesh disegnabile: "
                f"{len(vertici)} vertici e {len(facce)} triangoli"
            )
        corpo = viewport.to_float32(vertici) + np.ascontiguousarray(facce, dtype="<u4").tobytes()
        return Response(
            content=corpo,
            media_type="application/octet-stream",
            headers={"X-Vertices": str(len(vertici)), "X-Triangles": str(len(facce))},
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
                cfg = corrente()
                stato = {
                    "in_corso": lavoratore.is_running(),
                    "step": lavoratore.step,
                    "exit_code": lavoratore.exit_code,
                    "annullato": lavoratore.annullato,
                    "da_secondi": lavoratore.da_secondi(),
                    "steps": steps.run_state(cfg.run.out_dir, cfg),
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
