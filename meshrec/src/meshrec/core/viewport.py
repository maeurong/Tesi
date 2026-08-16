"""Decimazione per il disegno, con la mappa verso gli indici della nuvola piena.

Senza la mappa il clic sul cluster e il box di ritaglio agirebbero su una
nuvola scollegata dal dato: e' la forma esatta del risultato plausibile che
nessuna metrica smentisce. Open3D la fornisce gia' con
voxel_down_sample_and_trace, verificato su 100.000 punti: copertura completa,
nessuna ripetizione.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
import open3d as o3d

from meshrec.core.io import mean_spacing, read_cloud, scrivi_atomico

_ESPONENTE_DENSITA = 1.45
"""Esponente della stima del primo passo di voxel, non un vincolo del ciclo.

Per una superficie il numero di voxel occupati scala con una potenza del
rapporto fra estensione e passo; 2 sarebbe l'esponente di una griglia ideale,
ma qui vale circa 1,45, **misurato** su lab_crop (passo per 8 riduce i punti
per 21,8 e non per 64) e non dedotto da un modello. Se il valore vero fosse
diverso l'unico effetto e' un tentativo in piu' nel ciclo sottostante, che
raddoppia comunque il voxel finche' il conteggio non scende sotto il budget:
la stima puo' sbagliare il numero di giri, mai il risultato.
"""


def decimate(
    points: np.ndarray, max_points: int, spacing: float
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Punti da disegnare, gli indici pieni che ciascuno rappresenta, il voxel usato.

    Il passo non e' un numero scelto: il primo tentativo e' una stima dalla
    spaziatura media (vedi _ESPONENTE_DENSITA) e poi si raddoppia finche' il
    conteggio scende sotto il budget. La ricerca resta deterministica e non
    introduce alcun parametro da tarare: una stima sbagliata costa un giro in
    piu', mai un risultato fuori budget.

    Attenzione al caso opposto: se la stima cade cosi' alta da restituire
    molti meno punti del budget, la nuvola disegnata e' piu' rada del
    necessario. E' accettato e non corretto con altri giri: il budget e' un
    tetto, non un obiettivo.

    Voxel zero dichiara che nessuna decimazione e' stata applicata: la nuvola
    era gia' sotto il budget e i gruppi sono le identita'.

    L'ordine dei punti disegnati fa parte del contratto: i gruppi crescono per
    indice pieno minimo, e il punto i-esimo e' sempre quello del gruppo
    i-esimo. Non e' una comodita': voxel_down_sample_and_trace enumera i voxel
    nell'ordine di iterazione di una std::unordered_map interna a Open3D, che
    e' stabile dentro una build ma cambia fra libc++ (macOS) e la STL
    Microsoft (Windows). Propagarlo tale e quale farebbe indicare a 'punto
    disegnato numero 0' un pezzo di nuvola diverso a seconda della macchina,
    senza che nulla lo smentisca: il disegno resta identico, solo rinumerato.
    L'ordine preteso qui e' anche l'unico coerente con il ramo sotto budget,
    che restituisce gia' le identita' in ordine crescente.
    """
    punti = np.ascontiguousarray(np.asarray(points, dtype=np.float64))
    if len(punti) <= max_points:
        return punti, [np.array([indice]) for indice in range(len(punti))], 0.0

    nuvola = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(punti))
    basso, alto = nuvola.get_min_bound(), nuvola.get_max_bound()
    if spacing > 0.0:
        fattore = max(1.0, (len(punti) / max_points) ** (1.0 / _ESPONENTE_DENSITA))
        voxel = float(spacing) * fattore
    else:
        voxel = float(np.max(alto - basso)) / 1000.0
    for _ in range(64):
        ridotta, _indici, tracce = nuvola.voxel_down_sample_and_trace(voxel, basso, alto)
        if len(ridotta.points) <= max_points:
            gruppi = [np.asarray(traccia, dtype=np.int64) for traccia in tracce]
            # L'ordine dei voxel che Open3D restituisce e' quello di una sua
            # hash map interna: stabile dentro una build, diverso fra libc++ e
            # la STL Microsoft. Riordinare per indice pieno minimo lo rende
            # una funzione del dato. Punti e gruppi si permutano con lo stesso
            # ordine: sfasarli slaccerebbe in silenzio l'indice che il browser
            # rimanda dal gruppo che rappresenta.
            # Nessun criterio di pareggio, e non serve: le tracce partizionano
            # la nuvola, quindi ogni indice pieno cade in un voxel e uno solo e
            # i minimi sono unici. Un sort stabile qui sarebbe anzi fuorviante,
            # perche' fra eventuali pari conserverebbe proprio l'ordine di
            # Open3D che questa riga esiste per togliere di mezzo.
            ordine = np.argsort([int(gruppo.min()) for gruppo in gruppi])
            return (
                np.ascontiguousarray(np.asarray(ridotta.points)[ordine], dtype=np.float64),
                [gruppi[posizione] for posizione in ordine],
                voxel,
            )
        voxel *= 2.0
    # Sessantaquattro raddoppi portano il voxel oltre qualunque ingombro
    # fisico: se il budget non e' stato raggiunto il problema e' il budget,
    # non la nuvola, e dirlo e' meglio che restituire tutto in silenzio.
    raise ValueError(
        f"nessun passo di voxel porta {len(punti)} punti sotto il budget di {max_points}"
    )


def to_float32(array: np.ndarray) -> bytes:
    """Serializzazione binaria: 300.000 punti sono 3,6 MB contro i circa 18 in JSON."""
    return np.ascontiguousarray(np.asarray(array), dtype="<f4").tobytes()


# Gettone del contratto di decimate, non della sorgente. Va alzato ogni volta
# che cambia CHE COSA decimate promette, non come lo calcola: una voce scritta
# sotto il contratto vecchio resterebbe altrimenti valida per chiave e servirebbe
# un risultato che non rispetta piu' la promessa, con la suite verde perche' i
# test esercitano decimate e non la cache. Il 2 e' l'ordine dei gruppi, diventato
# contratto quando si e' scoperto che quello di Open3D cambia con la piattaforma.
_VERSIONE_CONTRATTO = 2


def _cache_path(source: Path, max_points: int, spacing_sample: int, seed: int, cache_dir: Path) -> Path:
    """Nome del file di cache per (contratto, sorgente, budget, spacing_sample, seed), senza leggerne il contenuto.

    spacing_sample e seed sostituiscono lo spacing gia' calcolato: mean_spacing
    e' deterministica su (sorgente, spacing_sample, seed), quindi le due chiavi
    sono equivalenti, ma questa si ottiene con un solo Path.stat().

    Il gettone di contratto sta nel nome e non nel contenuto perche' cosi'
    invalida senza aprire il file: le voci vecchie non vengono lette, non
    vengono migrate, semplicemente non rispondono piu' alla chiave.
    """
    source = Path(source)
    marchio = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:16]
    mtime = source.stat().st_mtime_ns
    return (
        Path(cache_dir)
        / f"{marchio}-v{_VERSIONE_CONTRATTO}-{max_points}-{spacing_sample}-{seed}-{mtime}.npz"
    )


def decimate_file(
    source: Path,
    max_points: int,
    spacing_sample: int,
    seed: int,
    cache_dir: Path,
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Come decimate, ma il risultato e' salvato su disco per (sorgente, budget, spacing_sample, seed, mtime).

    La spaziatura non e' un parametro di questa funzione: viene calcolata qui
    dentro, una sola volta e solo a cache fredda, dalla stessa lettura della
    sorgente che serve a decimate. Passarla gia' calcolata (come faceva la
    prima versione) la escluderebbe dalla chiave: due chiamate con la stessa
    sorgente e budget ma spaziatura diversa condividerebbero la voce e la
    seconda vedrebbe il risultato della prima. spacing_sample e seed nella
    chiave chiudono il buco perche' mean_spacing e' deterministica su di essi
    (vedi _cache_path): stessa garanzia di prima, senza che il chiamante
    debba leggere la nuvola solo per scoprire se puo' evitarlo.

    La voce vecchia della stessa sorgente viene rimossa quando la nuova viene
    scritta, qualunque fossero budget, spacing_sample o seed: una voce per
    file sorgente, mai una cache che cresce senza fine.

    Una cache illeggibile o corrotta non e' un errore verso il chiamante: si
    ricalcola, la stessa regola gia' applicata a read_state e leggi_metriche.
    """
    source = Path(source)
    cache_dir = Path(cache_dir)
    percorso = _cache_path(source, max_points, spacing_sample, seed, cache_dir)

    trovato = _leggi_cache(percorso)
    if trovato is not None:
        return trovato

    punti, _normali = read_cloud(source)
    spacing = mean_spacing(punti, spacing_sample, seed)
    ridotti, gruppi, voxel = decimate(punti, max_points, spacing)
    # Il float32 e' gia' il formato di trasporto (to_float32): scendere qui,
    # non solo nella cache, tiene identico il risultato a cache fredda e a
    # cache calda invece di far dipendere la precisione da quale delle due
    # strade ha risposto.
    ridotti = np.ascontiguousarray(ridotti, dtype=np.float32)
    _scrivi_cache(percorso, ridotti, gruppi, voxel)
    _rimuovi_voci_vecchie(cache_dir, percorso)
    return ridotti, gruppi, voxel


def _leggi_cache(percorso: Path) -> tuple[np.ndarray, list[np.ndarray], float] | None:
    if not percorso.exists():
        return None
    try:
        with np.load(percorso, allow_pickle=False) as dati:
            punti = np.ascontiguousarray(dati["punti"])
            indici = dati["indici"]
            offsets = dati["offsets"]
            voxel = float(dati["voxel"])
        if len(offsets) != len(punti) + 1 or int(offsets[-1]) != len(indici):
            # offsets[i]:offsets[i+1] non solleva mai su un array numpy anche
            # quando gli indici sono fuori misura: uno scarto di lunghezza
            # trunca in silenzio invece di alzare un'eccezione, quindi va
            # negato qui, non lasciato al try sottostante che non lo vedrebbe.
            raise ValueError("offsets incoerente con punti/indici")
        gruppi = [indici[offsets[i] : offsets[i + 1]] for i in range(len(offsets) - 1)]
    except (OSError, ValueError, KeyError, EOFError, IndexError, zipfile.BadZipFile):
        # Un file troncato, sostituito da byte a caso, o formalmente valido
        # ma con offsets/indici incoerenti non e' un errore: e' una voce
        # assente, e si ricalcola (vedi read_state, leggi_metriche). La
        # ricostruzione dei gruppi sta dentro il try apposta: un'incoerenza
        # che la farebbe fallire deve scartare la voce, non propagarsi.
        return None
    return punti, gruppi, voxel


def _scrivi_cache(percorso: Path, punti: np.ndarray, gruppi: list[np.ndarray], voxel: float) -> None:
    lunghezze = [len(gruppo) for gruppo in gruppi]
    offsets = np.zeros(len(gruppi) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lunghezze)
    indici = (
        np.concatenate([np.asarray(gruppo, dtype=np.int64) for gruppo in gruppi])
        if gruppi
        else np.zeros(0, dtype=np.int64)
    )

    def scrittore(destinazione: Path) -> None:
        np.savez(
            str(destinazione),
            punti=np.ascontiguousarray(punti, dtype=np.float32),
            indici=indici,
            offsets=offsets,
            voxel=np.float64(voxel),
        )

    try:
        scrivi_atomico(percorso, scrittore)
    except OSError:
        # Due richieste sovrapposte sullo stesso step (doppio clic durante i
        # secondi di decimazione fredda) condividono lo stesso nome di
        # temporaneo (stessa terna, stesso mtime): la replace() della seconda
        # puo' non trovare piu' il file che la prima ha gia' spostato. Una
        # cache che non riesce a scriversi deve costare un ricalcolo alla
        # prossima chiamata, mai una richiesta fallita verso il browser.
        return


def _rimuovi_voci_vecchie(cache_dir: Path, corrente: Path) -> None:
    """Elimina ogni altra voce della stessa sorgente, qualunque budget o parametro di spaziatura.

    Il marchio e' sempre il primo campo del nome ed e' esadecimale, quindi non
    contiene mai un trattino: split("-", 1) lo isola in modo affidabile
    indipendentemente da che cosa segua. Una voce per sorgente: la pipeline ha
    otto artefatti con nuvola, quindi al piu' otto voci in cache in totale.
    """
    marchio = corrente.name.split("-", 1)[0]
    for vecchia in cache_dir.glob(f"{marchio}-*.npz"):
        if vecchia != corrente:
            vecchia.unlink()
