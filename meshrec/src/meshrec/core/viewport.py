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

from meshrec.core.io import read_cloud, scrivi_atomico

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
            return (
                np.ascontiguousarray(np.asarray(ridotta.points), dtype=np.float64),
                gruppi,
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


def cache_path(source: Path, max_points: int, cache_dir: Path) -> Path:
    """Nome del file di cache per una terna (sorgente, budget), senza leggerne il contenuto.

    Un solo Path.stat() basta a saperlo: e' cio' che permette al chiamante di
    scoprire se la cache e' calda prima di calcolare la spaziatura media, che
    su lab_crop costa da sola 2 s.
    """
    source = Path(source)
    marchio = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(cache_dir) / f"{marchio}-{max_points}-{source.stat().st_mtime_ns}.npz"


def decimate_file(
    source: Path, max_points: int, spacing: float, cache_dir: Path
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Come decimate, ma il risultato e' salvato su disco per la terna (sorgente, budget, mtime).

    La chiave e' il percorso assoluto della sorgente, il budget e la data di
    modifica in nanosecondi (Path.stat().st_mtime_ns): una sorgente riscritta
    cambia mtime e quindi chiave, non viene mai letta una voce stantia. La
    voce vecchia della stessa sorgente e dello stesso budget viene rimossa
    quando la nuova viene scritta, cosi' la cache non cresce senza fine a ogni
    riesecuzione di uno step.

    Una cache illeggibile o corrotta non e' un errore verso il chiamante: si
    ricalcola, la stessa regola gia' applicata a read_state e leggi_metriche.
    """
    source = Path(source)
    cache_dir = Path(cache_dir)
    percorso = cache_path(source, max_points, cache_dir)

    trovato = _leggi_cache(percorso)
    if trovato is not None:
        return trovato

    punti, _normali = read_cloud(source)
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
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        # Un file troncato o sostituito da byte a caso non e' un errore: e'
        # una voce assente, e si ricalcola (vedi read_state, leggi_metriche).
        return None
    gruppi = [indici[offsets[i] : offsets[i + 1]] for i in range(len(offsets) - 1)]
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

    scrivi_atomico(percorso, scrittore)


def _rimuovi_voci_vecchie(cache_dir: Path, corrente: Path) -> None:
    """Elimina le altre voci della stessa sorgente e dello stesso budget.

    Il nome corrente e' "{marchio}-{max_points}-{mtime}.npz": marchio e
    max_points non contengono mai un trattino, quindi l'ultimo trattino nel
    nome separa in modo affidabile il prefisso condiviso dal mtime.
    """
    prefisso = corrente.stem.rsplit("-", 1)[0]
    for vecchia in cache_dir.glob(f"{prefisso}-*.npz"):
        if vecchia != corrente:
            vecchia.unlink()
