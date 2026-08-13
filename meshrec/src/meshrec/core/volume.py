"""Tetraedrizzazione della superficie chiusa."""

from __future__ import annotations

import time
import warnings

import numpy as np
import tetgen

from meshrec.core.config import TetConfig
from meshrec.core.quality import (
    boundary_edges,
    fraction_over_ratio,
    inverted_tets,
    is_watertight,
    radius_edge_ratios,
    tet_volumes,
)


class NotWatertightError(ValueError):
    """La superficie non e chiusa: TetGen non puo tetraedrizzarla."""


class TruncatedRefinementWarning(UserWarning):
    """TetGen ha esaurito i punti di Steiner: la mesh e' troncata, non completa."""


class IneffectiveVolumeLimitWarning(UserWarning):
    """`max_volume` era impostato ma la mesh non lo rispetta: il limite e' rimasto inerte."""


class UnmetQualityConstraintWarning(UserWarning):
    """Il maglio prodotto non rispetta il `min_ratio` richiesto: il vincolo e' rimasto lettera morta."""


class RefinementFailedError(RuntimeError):
    """Il raffinamento non converge: il vincolo di qualita e' troppo severo."""


class InvertedElementsError(ValueError):
    """La mesh di volume contiene elementi invertiti o degeneri."""


def tetrahedralize(
    vertices: np.ndarray,
    faces: np.ndarray,
    max_volume: float | None = None,
    *,
    min_ratio: float,
    max_steiner_points: int,
    nobisect: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Riempie di tetraedri lineari la superficie chiusa data.

    `min_ratio` e il rapporto raggio-spigolo massimo ammesso (piu basso =
    elementi piu regolari e piu numerosi); `max_volume` limita il volume del
    singolo elemento nelle unita di lavoro; `max_steiner_points` limita i punti
    che TetGen puo' aggiungere per raffinare, e -1 toglie il limite. `nobisect`
    vieta la suddivisione delle facce di ingresso: la superficie esce identica a
    come e' entrata, e il raffinamento resta confinato all'interno.

    Ne' `min_ratio`, ne' `max_steiner_points`, ne' `nobisect` hanno un valore predefinito qui,
    apposta: l'unico luogo dove un parametro di elaborazione ha un predefinito
    e' `core.config`. Il predefinito ereditato dalla libreria tetgen per
    `max_steiner_points` (100000) ha prodotto mesh troncate senza che nulla lo
    segnalasse; il predefinito 1.1 che questa firma portava per `min_ratio`
    contraddiceva il predefinito 1.8 di `TetConfig` ed era il valore che sul
    muro reale non porta a termine il raffinamento.
    """
    faces = np.asarray(faces)
    if not is_watertight(faces):
        open_edges = len(boundary_edges(faces))
        raise NotWatertightError(
            f"superficie non chiusa: {open_edges} spigoli di bordo. "
            "TetGen richiede un ingresso manifold chiuso; ripara la superficie "
            "con core.repair.repair_surface prima di tetraedrizzare."
        )

    generator = tetgen.TetGen(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces, dtype=np.int32),
    )
    options: dict[str, object] = {
        "order": 1,
        "minratio": float(min_ratio),
        "steinerleft": int(max_steiner_points),
        "nobisect": bool(nobisect),
    }
    if max_volume is not None:
        # Non e' un bug: e' una trappola dell'API di tetgen 0.8.4, per scelta
        # di progetto della libreria. maxvolume da solo e' inerte; il flag
        # booleano fixedvolume=True e' l'interruttore separato che attiva
        # l'opzione -a di TetGen e la rende effettiva.
        options["maxvolume"] = float(max_volume)
        options["fixedvolume"] = True

    # tetgen 0.8.4 restituisce (node, elem, attributes, triface_markers): teniamo solo i primi due.
    try:
        nodes, tets, *_ = generator.tetrahedralize(**options)
    except RuntimeError as errore:
        # L'errore grezzo della libreria ("Internal TetGen error within
        # `split_subface`") non dice nulla a chi lo riceve. Nella pratica arriva
        # quando il vincolo raggio-spigolo e' troppo severo per la geometria: il
        # raffinamento non converge e TetGen si arrende su una configurazione
        # degenere. Sul muro di riferimento accade con min_ratio fino a 1.6, non
        # con 1.8, quindi il margine e' sottile e su un'altra geometria puo' non
        # bastare.
        raise RefinementFailedError(
            f"TetGen si e' interrotto con min_ratio={min_ratio}: "
            "il vincolo raggio-spigolo puo' essere troppo severo per questa "
            "geometria, il raffinamento non converge. Alza min_ratio (valori piu "
            "alti = elementi meno regolari ma raffinamento che termina) e riprova. "
            f"Errore originale di TetGen: {errore}"
        ) from errore
    return (
        np.ascontiguousarray(nodes, dtype=np.float64),
        np.ascontiguousarray(tets, dtype=np.int64),
    )


def tetrahedralize_with_metrics(
    vertices: np.ndarray, faces: np.ndarray, cfg: TetConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Step 9 completo: tetraedrizza, cronometra e rifiuta gli elementi invertiti."""
    start = time.perf_counter()
    nodes, tets = tetrahedralize(
        vertices,
        faces,
        cfg.max_volume,
        min_ratio=cfg.min_ratio,
        max_steiner_points=cfg.max_steiner_points,
        nobisect=cfg.nobisect,
    )
    seconds = time.perf_counter() - start

    inverted = inverted_tets(nodes, tets)
    if len(inverted) > 0:
        raise InvertedElementsError(
            f"{len(inverted)} tetraedri invertiti o degeneri su {len(tets)}: "
            "risultato inutilizzabile per l'analisi, non un avviso"
        )

    # TetGen non dichiara di aver esaurito il budget di punti di Steiner. L'indizio
    # utilizzabile e' il conteggio: i nodi che escono in piu rispetto ai vertici
    # della superficie sono i punti aggiunti, e quando il budget si esaurisce
    # eguagliano il tetto esattamente, mai per difetto. Verificato sul muro reale a
    # sei tetti diversi (25000, 50000, 100000, 120000, 150000, 175000): i punti
    # aggiunti sono risultati ogni volta pari al tetto in modo esatto.
    steiner_points = int(len(nodes) - len(np.asarray(vertices)))
    saturated = cfg.max_steiner_points > 0 and steiner_points >= cfg.max_steiner_points
    if saturated:
        warnings.warn(
            f"TetGen ha esaurito i {cfg.max_steiner_points} punti di Steiner concessi: "
            "il raffinamento e' stato troncato e la mesh non rispetta i vincoli di "
            "qualita richiesti. Alza max_steiner_points o portalo a -1.",
            TruncatedRefinementWarning,
            stacklevel=2,
        )

    # Con nobisect TetGen non ha punti di bordo da cui partire, e su una
    # superficie di ingresso grossolana restituisce pochi elementi enormi senza
    # dire nulla: max_volume risulta impostato e disatteso. E' la stessa trappola
    # di fixedvolume, scoperta sul cubo (12 tetraedri invece di 7103), e come
    # quella non deve arrivare a valle in silenzio.
    #
    # La soglia e' un fattore 2 e non l'uguaglianza perche' per TetGen maxvolume
    # e' un obiettivo, non un tetto rigido: sul cubo il piu grande supera di
    # routine il limite di circa il 10% anche quando il raffinamento fa tutto il
    # suo lavoro. Un avviso che scatta a ogni corsa regolare e' un avviso che
    # nessuno legge piu quando conta; il caso da segnalare, sul cubo con
    # nobisect, e' trenta volte oltre.
    largest = float(np.abs(tet_volumes(nodes, tets)).max()) if len(tets) else 0.0
    if cfg.max_volume is not None and largest > 2.0 * cfg.max_volume:
        warnings.warn(
            f"il tetraedro piu grande misura {largest:.6g} contro il max_volume "
            f"di {cfg.max_volume:.6g} richiesto: il limite non e' stato applicato. "
            + (
                "Con nobisect attivo TetGen non aggiunge punti sul bordo: "
                "infittisci la superficie di ingresso o disattiva nobisect."
                if cfg.nobisect
                else "Verifica i vincoli di qualita richiesti."
            ),
            IneffectiveVolumeLimitWarning,
            stacklevel=2,
        )

    # `min_ratio` era il solo parametro di TetConfig che nessuna metrica
    # verificava sul risultato: `max_steiner_points` e' controllato dal
    # conteggio dei punti aggiunti, `max_volume` da largest_element_volume, e
    # il rapporto raggio-spigolo da nulla. Tre parametri di libreria sono gia'
    # stati trovati impostati e inerti, tutti per caso: questa chiude la
    # famiglia.
    #
    # La grandezza sorvegliata e' la frazione di elementi che superano il
    # vincolo, non un percentile alto della distribuzione. Un percentile
    # avrebbe richiesto una soglia tarata, e tarare su due sole corse e'
    # esattamente il debito che gia' portiamo per min_ratio stesso; la frazione
    # invece si legge da sola.
    #
    # TetGen tratta minratio come un obiettivo e non come un tetto rigido,
    # come gia' documentato per maxvolume. Con min_ratio=1.8 il vincolo resta
    # violato dall'8,10% degli elementi sul muro di riferimento (1.752.795
    # tetraedri), dal 9,55% su lab_frame tetraedrizzato con nobisect
    # (1.607.146 tetraedri) e dallo 0,00% sul cubo sintetico. Una corsa sana a
    # scala reale lascia quindi fuori vincolo una minoranza di elementi, gli
    # sliver di bordo che il raffinamento non puo' legalmente correggere.
    #
    # L'avviso scatta oltre la meta', che non e' una soglia scelta ma
    # un'affermazione qualitativa: quando gli elementi che violano il vincolo
    # sono piu' di quelli che lo rispettano, il parametro non sta governando
    # quel maglio. Sui magli grossolani scatta davvero, ed e' corretto che lo
    # faccia: sul cubo con nobisect, dodici tetraedri in tutto, il 66,67% e'
    # fuori vincolo.
    #
    # La prova migliore che serve e' pero' retrospettiva. La mesh che la Fase 1
    # aveva scambiato per un successo su lab_frame era troncata dal tetto
    # ereditato di 100.000 punti di Steiner — 313.154 nodi meno i 213.154
    # vertici della superficie fanno esattamente 100.000 — e nessuna metrica
    # dell'epoca la smentiva: zero elementi invertiti, deck scritto, tutto
    # regolare. Su quella mesh la frazione fuori vincolo vale l'86,36%. Questo
    # avviso l'avrebbe segnalata.
    ratios = radius_edge_ratios(nodes, tets)
    finite = ratios[np.isfinite(ratios)]
    over_limit = fraction_over_ratio(nodes, tets, cfg.min_ratio)
    # Lotto vuoto: nessun rapporto finito su cui misurare un percentile. None,
    # non float("inf"), che in metrics.json diventerebbe Infinity e non e'
    # JSON valido; quality.py usa gia' questa stessa convenzione altrove.
    p99 = float(np.quantile(finite, 0.99)) if len(finite) else None
    if over_limit > 0.5:
        p99_testo = f"{p99:.4g}" if p99 is not None else "non calcolabile (nessun rapporto finito)"
        warnings.warn(
            f"il {over_limit:.2%} degli elementi supera il min_ratio di "
            f"{cfg.min_ratio:.4g} richiesto: il vincolo di qualita non governa "
            "questo maglio. Il novantanovesimo percentile del rapporto "
            f"raggio-spigolo vale {p99_testo}.",
            UnmetQualityConstraintWarning,
            stacklevel=2,
        )

    metrics = {
        "nodes": int(len(nodes)),
        "tets": int(len(tets)),
        "seconds": float(seconds),
        "element": cfg.element,
        "min_ratio": cfg.min_ratio,
        "max_volume": cfg.max_volume,
        "max_steiner_points": cfg.max_steiner_points,
        "nobisect": bool(cfg.nobisect),
        "largest_element_volume": largest,
        "steiner_points": steiner_points,
        "steiner_saturated": bool(saturated),
        "radius_edge_ratio_over_limit": over_limit,
        "radius_edge_ratio_p99": p99,
    }
    return nodes, tets, metrics
