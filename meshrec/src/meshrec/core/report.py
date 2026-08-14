"""Report statici in HTML: quello dello sweep e quello di una singola corsa.

`write_report` nasce dal registro degli esperimenti: tabella, fronte di
Pareto, istogrammi. `write_run_report` nasce invece dai file di una corsa
sola: config.yaml, metrics.json, steps.json e le viste catturate.

Nessuna libreria di grafici: per pochi istogrammi non si giustifica, ed e'
gia' escluso dalla spec di architettura. Nessuna miniatura e nessun
rendering 3D: il confronto visivo arriva con il viewport della Fase 3, che
rivestira' questo report invece di riscriverlo.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Iterator

import yaml

from meshrec.core import steps
from meshrec.core.config import load_config
from meshrec.core.pipeline import METRICS_FILENAME
from meshrec.core.sweep import load_registry

CONFIG_FILENAME = "config.yaml"
RUN_REPORT_FILENAME = "report.html"

# Intestazione della dichiarazione degli step mai misurati. E' una costante
# perche' il test che la cerca deve puntare alla stessa stringa che il report
# scrive, non a una copia che puo' divergere in silenzio.
SENZA_METRICHE = "step senza metriche:"

# metrics.json e' cumulativo: una corsa parziale fonde le proprie metriche con
# quelle precedenti (pipeline.run). Affiancare la tabella dei parametri a righe
# prodotte da parametri diversi afferma un legame che non esiste, e su carta
# nessuno puo' accorgersene. Queste due stringhe sono la dichiarazione, ed e'
# la stessa che i test cercano: non ne esiste una seconda copia.
COERENTI = "coerenti con i parametri mostrati"
NON_VERIFICABILE = "corrispondenza fra parametri e metriche non verificabile"

# I quattro stati di steps.run_state, ripetuti qui perche' quel modulo non li
# esporta. Non sono due categorie: uno step mai eseguito non ha metriche
# prodotte da altri parametri, non ne ha affatto, e uno fallito non e' uno
# prodotto con parametri diversi. Il conteggio di coerenza riguarda i soli
# step eseguiti; i mai eseguiti li dichiara la sezione delle metriche.
VALIDO = "valido"
MAI_ESEGUITO = "mai eseguito"
NON_ESEGUITI = "non ancora eseguiti restano fuori dal conteggio"
NESSUNO_ESEGUITO = "nessuno step di questa corsa e' stato eseguito"
SPIEGAZIONE_GUASTI = (
    "Fra parentesi lo stato: 'non valido' vuol dire prodotto con parametri che "
    "questo report non mostra, 'fallito' che lo step non e' arrivato in fondo."
)

# Un file che manca e un file che c'e' ma non si legge sono due fatti diversi
# sul disco, e mandano a cercare due cose diverse. steps.read_state documenta
# proprio il caso del processo ucciso a meta' scrittura.
ILLEGGIBILE = "presente ma illeggibile"
FORMA_INATTESA = "presente ma non contiene una mappa di voci"

# Una lista vuota e' un dato, e spesso il migliore possibile (nessun buco oltre
# la soglia). Scritta come cella bianca non si distingue da un dato mancante.
LISTA_VUOTA = "nessuno (lista vuota)"
NON_IMPOSTATO = "non impostato"
VUOTO = "(vuoto)"

ESCLUSE_CORTE = "liste troppo corte per un istogramma"
PNG_NON_LEGGIBILE = "il file c'e' ma non e' un PNG leggibile, non incorporata."

# Sotto questa lunghezza una lista di numeri non e' una distribuzione ma un
# vettore di coordinate (extent, bbox_min, bbox_max hanno tre componenti): un
# istogramma di tre barre in appendice a una tesi e' rumore, non una misura.
_MINIMO_PER_ISTOGRAMMA = 4

# Firma PNG e taglia del PNG piu' piccolo che esista: 8 di firma, 25 di IHDR,
# almeno 22 di IDAT e 12 di IEND. Sotto questa soglia il file e' troncato o
# vuoto, e nel documento diventerebbe un riquadro rotto senza spiegazione.
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
_MINIMO_PNG = 67

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "impronta"),
    ("axes", "assi"),
    ("outcome", "esito"),
    ("thickness_error", "errore di spessore [mm]"),
    ("tets", "tetraedri"),
    ("over", "fuori vincolo"),
    ("dihedral", "diedro min., mediana"),
    ("duration_s", "durata [s]"),
)


def histogram_svg(values: list[float], title: str, bins: int) -> str:
    """Istogramma come SVG scritto a mano, senza dipendenze."""
    if not values:
        return f"<svg width='320' height='140'><text x='8' y='20'>{html.escape(title)}: vuoto</text></svg>"

    low, high = min(values), max(values)
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    tallest = max(counts) or 1

    bars = "".join(
        f"<rect x='{8 + index * (300 / bins):.1f}' y='{120 - 100 * count / tallest:.1f}' "
        f"width='{300 / bins - 2:.1f}' height='{100 * count / tallest:.1f}' fill='#456'/>"
        for index, count in enumerate(counts)
    )
    return (
        f"<svg width='320' height='140' role='img'>"
        f"<text x='8' y='14' font-size='11'>{html.escape(title)}</text>{bars}"
        f"<text x='8' y='134' font-size='10'>{low:.3g}</text>"
        f"<text x='260' y='134' font-size='10'>{high:.3g}</text></svg>"
    )


def _cell(row: dict[str, object], key: str) -> str:
    volume = row.get("metrics", {}).get("10_volume_quality", {})
    if key == "tets":
        value = volume.get("tets")
    elif key == "over":
        value = volume.get("radius_edge_over_reference")
    elif key == "dihedral":
        value = volume.get("min_dihedral_deg", {}).get("median")
    else:
        value = row.get(key)

    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, dict):
        return ", ".join(
            f"{html.escape(str(name))}={html.escape(str(item))}" for name, item in value.items()
        ) or "base"
    return html.escape(str(value)) if value is not None else ""


def write_report(registry_path: Path, out_path: Path) -> Path:
    """Scrive il report HTML a partire dal solo registro.

    Il registro e' l'unica rappresentazione autoritativa: la tabella piatta
    per l'appendice si genera da qui e non si mantiene a mano, che e' il modo
    in cui in Fase 1 numeri di corse diverse sono finiti fianco a fianco.
    """
    rows = load_registry(registry_path)
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in _COLUMNS)
    body = "".join(
        "<tr class='{}'>{}</tr>".format(
            "fronte" if row.get("on_front") else "",
            "".join(f"<td>{_cell(row, key)}</td>" for key, _ in _COLUMNS),
        )
        for row in rows
    )

    errors = [row["thickness_error"] for row in rows if isinstance(row.get("thickness_error"), float)]
    tets = [
        float(row["metrics"]["10_volume_quality"]["tets"])
        for row in rows
        if row.get("metrics", {}).get("10_volume_quality")
    ]

    document = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Sweep — {html.escape(registry_path.parent.name)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
table {{ border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: right; }}
th {{ background: #eee; }}
tr.fronte td {{ background: #eaf3ea; font-weight: 600; }}
</style></head><body>
<h1>Sweep — {html.escape(registry_path.parent.name)}</h1>
<p>{len(rows)} candidati. Le righe evidenziate sono il <strong>fronte</strong> di Pareto:
errore di spessore, numero di tetraedri e frazione fuori vincolo, tutti da minimizzare.</p>
<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<h2>Distribuzioni</h2>
{histogram_svg(errors, "errore di spessore [mm]", bins=12)}
{histogram_svg(tets, "tetraedri", bins=12)}
</body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path


_STILE = """
body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; }
table { border-collapse: collapse; font-size: 0.85rem; margin-bottom: 1rem; }
th, td { border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: left; }
th { background: #eee; }
p.assente { background: #fbeaea; padding: 0.25rem 0.5rem; }
figure { display: inline-block; margin: 0 1rem 1rem 0; }
img { max-width: 30rem; border: 1px solid #ccc; }
"""


def _mappa(percorso: Path, caricatore, assente: str) -> tuple[dict | None, str]:
    """La mappa contenuta nel file, oppure la frase che dice perche' non c'e'.

    Un file illeggibile non deve impedire il report: il documento dichiara il
    buco, che e' un'informazione, invece di sollevare e non produrre nulla. Ma
    dichiararlo 'assente' quando il file c'e' e' un'affermazione falsa sul
    disco, e manda a cercare una corsa mai fatta invece che un file rotto.
    """
    if not percorso.exists():
        return None, f"{percorso.name} assente: {assente}"
    try:
        with percorso.open(encoding="utf-8") as maniglia:
            contenuto = caricatore(maniglia)
    except (OSError, ValueError, yaml.YAMLError):
        return None, f"{percorso.name} {ILLEGGIBILE}: il file c'e' sul disco e non si rilegge."
    if not isinstance(contenuto, dict):
        return None, f"{percorso.name} {FORMA_INATTESA}: il file c'e' sul disco ma non ha la forma attesa."
    return contenuto, ""


def _numero(valore: float) -> str:
    """Sei cifre significative senza passare alla notazione esponenziale.

    %.6g da solo scrive 168845511.1 come 1.68846e+08: e' lo stesso valore, ma
    in una tabella stampata in appendice si legge peggio dell'intero. Fuori
    dall'intervallo qui sotto l'esponenziale resta l'unica resa leggibile.
    """
    arrotondato = float(f"{valore:.6g}")
    if arrotondato and not 1e-4 <= abs(arrotondato) < 1e12:
        return f"{arrotondato:.6g}"
    return f"{arrotondato:.10f}".rstrip("0").rstrip(".")


def _testo(valore: object) -> str:
    """Rappresentazione stampabile di un valore letto, senza arrotondarlo a zero."""
    if isinstance(valore, list):
        return ", ".join(_testo(item) for item in valore) or LISTA_VUOTA
    if isinstance(valore, bool):
        return "si" if valore else "no"
    if valore is None:
        return NON_IMPOSTATO
    if isinstance(valore, float):
        return _numero(valore)
    return str(valore) or VUOTO


def _piatto(prefisso: str, valore: object) -> Iterator[tuple[str, object]]:
    """Coppie (nome puntato, foglia) da una struttura annidata."""
    if isinstance(valore, dict):
        for chiave, dentro in valore.items():
            yield from _piatto(f"{prefisso}.{chiave}" if prefisso else str(chiave), dentro)
    else:
        yield prefisso, valore


def _tabella(coppie: Iterator[tuple[str, object]]) -> str:
    righe = "".join(
        f"<tr><th>{html.escape(nome)}</th><td>{html.escape(_testo(valore))}</td></tr>"
        for nome, valore in coppie
    )
    return f"<table>{righe}</table>" if righe else "<p>nessuna voce.</p>"


def _stato_degli_step(out_dir: Path) -> tuple[dict[str, str] | None, str]:
    """Stato di ogni step rispetto ai parametri sul disco, o il motivo per cui non si sa.

    Non riusa la configurazione gia' letta con yaml.safe_load, perche'
    `run_state` vuole un PipelineConfig vero: se la validazione non passa, il
    report esce lo stesso e lo dichiara, invece di sparire.
    """
    if not (out_dir / steps.STATE_FILENAME).exists():
        return None, f"{steps.STATE_FILENAME} assente: nessuna traccia delle impronte"
    try:
        stato = steps.run_state(out_dir, load_config(out_dir / CONFIG_FILENAME))
    except (OSError, ValueError, yaml.YAMLError):
        return None, f"{CONFIG_FILENAME} non e' una configurazione valida"
    return {str(voce["chiave"]): str(voce["stato"]) for voce in stato}, ""


def _riga_coerenza(stato: dict[str, str] | None, motivo: str) -> str:
    """Quanti step *eseguiti* vengono davvero dai parametri mostrati sopra, e quali no.

    Il denominatore sono gli step eseguiti: contare fra gli incoerenti anche
    quelli mai eseguiti fa leggere una corsa non ancora fatta come una corsa
    sbagliata, e contraddice la dichiarazione che il documento fa piu' sotto.
    """
    if stato is None:
        return f"<p class='assente'>{NON_VERIFICABILE}: {html.escape(motivo)}.</p>"
    mai = [chiave for chiave, valore in stato.items() if valore == MAI_ESEGUITO]
    guasti = [
        f"{chiave} ({valore})"
        for chiave, valore in stato.items()
        if valore not in (VALIDO, MAI_ESEGUITO)
    ]
    eseguiti = len(stato) - len(mai)
    coda = f" {len(mai)} step {NON_ESEGUITI}." if mai else ""
    if not eseguiti:
        return f"<p class='assente'>{NESSUNO_ESEGUITO}.{coda}</p>"
    if not guasti:
        return f"<p>{eseguiti} step su {eseguiti} {COERENTI}.{coda}</p>"
    return (
        f"<p class='assente'>{eseguiti - len(guasti)} step su {eseguiti} {COERENTI}, "
        f"{len(guasti)} no: {html.escape(', '.join(guasti))}. "
        f"{SPIEGAZIONE_GUASTI}{coda}</p>"
    )


def _sezione_metriche(
    metriche: dict[str, object] | None, motivo: str, stato: dict[str, str] | None
) -> str:
    """Le metriche presenti, con il proprio stato, e quelle mancanti dichiarate."""
    if metriche is None:
        return f"<p class='assente'>{html.escape(motivo)}</p>"

    presenti = "".join(
        "<h3>{} [{}]</h3>{}".format(
            html.escape(nome),
            html.escape((stato or {}).get(nome, "stato ignoto")),
            _tabella(_piatto("", valore)),
        )
        for nome, valore in sorted(metriche.items())
    )
    mancanti = [chiave for chiave in steps.STEP_KEYS if chiave not in metriche]
    coda = (
        f"<p class='assente'>{SENZA_METRICHE} {html.escape(', '.join(mancanti))}. "
        "Non sono righe a zero: sono step che questa corsa non ha eseguito.</p>"
        if mancanti
        else "<p>tutti gli step di una corsa completa hanno metriche.</p>"
    )
    return presenti + coda


def _istogrammi(metriche: dict[str, object] | None) -> str:
    """Un istogramma per ogni lista di numeri trovata: nessun nome di metrica scritto qui.

    Le liste sotto la soglia non spariscono in silenzio: una di tre valori puo'
    essere una distribuzione vera (hole_areas di una corsa dello sweep) tanto
    quanto una terna di coordinate, e il lettore deve poterlo sapere.
    """
    numeriche = [
        (nome, valore)
        for nome, valore in _piatto("", metriche if isinstance(metriche, dict) else {})
        if isinstance(valore, list)
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in valore)
    ]
    grafici = [
        histogram_svg([float(item) for item in valore], nome, bins=12)
        for nome, valore in numeriche
        if len(valore) >= _MINIMO_PER_ISTOGRAMMA
    ]
    corte = [nome for nome, valore in numeriche if len(valore) < _MINIMO_PER_ISTOGRAMMA]
    coda = (
        f"<p>{ESCLUSE_CORTE} (meno di {_MINIMO_PER_ISTOGRAMMA} valori): "
        f"{html.escape(', '.join(corte))}. I valori restano nella tabella qui sopra.</p>"
        if corte
        else ""
    )
    return ("".join(grafici) or "<p>nessuna distribuzione fra le metriche di questa corsa.</p>") + coda


def _e_png(vista: Path) -> bool:
    """Il file e' plausibilmente un PNG: firma giusta e non troncato.

    exists() da solo lascia passare una cattura interrotta o un file di zero
    byte, che nel documento diventa un riquadro vuoto senza spiegazione.
    """
    try:
        with vista.open("rb") as maniglia:
            firma = maniglia.read(len(_FIRMA_PNG))
        return firma == _FIRMA_PNG and vista.stat().st_size >= _MINIMO_PNG
    except OSError:
        return False


def _sezione_viste(viste: list[Path], cartella: Path) -> str:
    """Le viste presenti come immagini relative, le altre dichiarate assenti."""
    pezzi = []
    for vista in viste:
        vista = Path(vista)
        nome = html.escape(vista.name)
        if not vista.exists():
            pezzi.append(f"<p class='assente'>vista {nome}: file assente, non incorporata.</p>")
            continue
        if not _e_png(vista):
            pezzi.append(f"<p class='assente'>vista {nome}: {PNG_NON_LEGGIBILE}</p>")
            continue
        try:
            riferimento = Path(os.path.relpath(vista, cartella)).as_posix()
        except ValueError:
            # Su Windows fra unita' diverse nessun percorso relativo esiste:
            # meglio un percorso assoluto dichiarato che un report non scritto.
            riferimento = vista.as_posix()
        pezzi.append(
            f'<figure><img src="{html.escape(riferimento)}" alt="{nome}">'
            f"<figcaption>{nome}</figcaption></figure>"
        )
    return "".join(pezzi)


def _conteggio_viste(viste: list[Path]) -> str:
    if not viste:
        return "<p class='assente'>nessuna vista catturata: 0 attese, 0 presenti.</p>"
    presenti = sum(1 for vista in viste if Path(vista).exists())
    classe = "" if presenti == len(viste) else " class='assente'"
    return f"<p{classe}>{len(viste)} attese, {presenti} presenti, {len(viste) - presenti} assenti.</p>"


def write_run_report(out_dir: Path, viste: list[Path]) -> Path:
    """Report di una corsa: configurazione, metriche, istogrammi, viste catturate.

    Le viste assenti vengono dichiarate e non lasciate come riquadri muti: un
    report con buchi silenziosi non e' distinguibile da uno completo se
    nessuno conta. Vale per ogni buco: metriche mai misurate, parametri mai
    salvati, immagini sparite dal disco. Ogni cifra qui dentro arriva da una
    lettura di metrics.json o di config.yaml, mai da un valore scritto nel
    codice.
    """
    out_dir = Path(out_dir)
    metriche, motivo_metriche = _mappa(
        out_dir / METRICS_FILENAME, json.load, "questa corsa non ha metriche sul disco."
    )
    configurazione, motivo_config = _mappa(
        out_dir / CONFIG_FILENAME,
        yaml.safe_load,
        "i parametri di questa corsa non sono sul disco.",
    )
    stato, motivo = _stato_degli_step(out_dir)
    parametri = (
        _tabella(_piatto("", configurazione))
        if configurazione is not None
        else f"<p class='assente'>{html.escape(motivo_config)}</p>"
    )

    documento = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Corsa: {html.escape(out_dir.name)}</title>
<style>{_STILE}</style></head><body>
<h1>Corsa: {html.escape(out_dir.name)}</h1>
<h2>Parametri</h2>
{parametri}
<h2>Metriche per step</h2>
{_riga_coerenza(stato, motivo)}
{_sezione_metriche(metriche, motivo_metriche, stato)}
<h2>Distribuzioni</h2>
{_istogrammi(metriche)}
<h2>Viste</h2>
{_conteggio_viste(viste)}
{_sezione_viste(viste, out_dir)}
</body></html>"""

    percorso = out_dir / RUN_REPORT_FILENAME
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(documento, encoding="utf-8")
    return percorso
