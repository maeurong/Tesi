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
import math
import os
from pathlib import Path
from typing import Iterator

import yaml

from meshrec.core import steps
from meshrec.core.config import load_config
from meshrec.core.pipeline import METRICS_FILENAME, WALL_FILENAME
from meshrec.core.sweep import load_registry

CONFIG_FILENAME = "config.yaml"
RUN_REPORT_FILENAME = "report.html"

# Intestazione della dichiarazione degli step mai misurati. E' una costante
# perche' il test che la cerca deve puntare alla stessa stringa che il report
# scrive, non a una copia che puo' divergere in silenzio. L'unica eccezione e'
# scritta apposta: il test della proprieta' la ricopia a mano, perche' e' la
# sola prosa che questo elenco aggiunge ai dati e leggerla da qui renderebbe
# invisibile la mutazione che la riscrive.
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
FALLITO = "fallito"
NON_VALIDO = "non valido"
NON_ESEGUITI = "non ancora eseguiti restano fuori dal conteggio"
NESSUNO_ESEGUITO = "nessuno step di questa corsa è stato eseguito"

# Il quinto caso non e' uno stato di run_state: senza steps.json non c'e'
# niente da leggere. Scrivere qui uno dei quattro sarebbe affermare una lettura
# che il paragrafo della coerenza, poche righe sopra, dichiara impossibile.
STATO_IGNOTO = "stato ignoto"

# "senza metriche" e "non eseguito" sono due domande diverse: pipeline.run
# scrive lo stato "fallito" e salva solo metrics.partial.json, quindi uno step
# fallito e' partito davvero e non ha una riga in metrics.json. Dedurre da
# quell'assenza che lo step non e' stato eseguito smentisce il paragrafo di
# coerenza, che lo conta fra gli eseguiti.
#
# Ogni stato si spiega da solo, e solo dove compare. Una frase fissa che vale
# per l'intero elenco afferma degli step elencati quello che e' vero di altri:
# e' cosi' che il documento ha detto di uno step fallito che questa corsa non
# l'ha eseguito, e ha promesso "lo stato letto da steps.json" a una corsa che
# steps.json non ce l'ha. Nessuna glossa nomina uno stato, nemmeno il proprio:
# lo stato lo scrive chi la stampa, davanti, una volta sola, e viene da una
# lettura. Cosi' l'elenco degli step non ha altra prosa che questa.
GLOSSA = {
    VALIDO: "prodotto con i parametri mostrati, e di misure non ne ha lasciate",
    MAI_ESEGUITO: "lo step non è mai partito",
    FALLITO: "lo step è partito e non è arrivato in fondo",
    NON_VALIDO: "prodotto con parametri che questo report non mostra",
    STATO_IGNOTO: "steps.json non si è letto, e di questo step non si sa niente",
}

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
# Una stringa di soli spazi stampata cruda e' una cella bianca esattamente come
# una cella vuota, e una mappa vuota annidata non e' nemmeno una cella: e' una
# riga che sparisce. Un dato che c'e' e che il documento non mostra e' la stessa
# bugia della cella vuota, con un sintomo che nessuno nota.
SOLI_SPAZI = "(soli spazi)"
MAPPA_VUOTA = "nessuna voce (mappa vuota)"
# Uno step le cui metriche non sono una mappa non porta nomi di voce: senza
# questo l'intestazione esce vuota, che stampata e' la cella bianca di sempre.
SENZA_NOME = "(voce senza nome)"
# nan e inf arrivano davvero: pipeline scrive metrics.json con json.dump, che
# li salva come NaN e Infinity, e riletti tornano float non finiti.
NON_UN_NUMERO = "non un numero"
INFINITO = "infinito"

ESCLUSE_CORTE = "liste troppo corte per un istogramma"
PNG_NON_LEGGIBILE = "il file c'è ma non è un PNG leggibile, non incorporata."
# Contare le viste con exists() e incorporarle con _e_png sono due criteri
# diversi sullo stesso insieme: due file rotti danno "2 presenti" e zero
# immagini, e chi conta le figure in appendice non ritrova il conteggio.
NON_INCORPORABILI = "presenti ma non incorporabili"
IMMAGINI_NEL_DOCUMENTO = "le immagini nel documento sono"

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
    # Peggiore **e** mediana, non la sola mediana. La mediana confronta due
    # candidati dello sweep; il peggiore e' l'unico dei due che vede uno
    # sliver, e lo sliver e' l'elemento che il vincolo raggio-spigolo di
    # TetGen non puo' fermare: misurato, un tetraedro di manuale con
    # raggio-spigolo 0,707 -- ben sotto il limite di 2,0 -- ha un diedro
    # minimo di 0,162 gradi. Con la sola mediana in tabella quel maglio si
    # legge sano. Il numero c'era gia' in metrics.json, non lo mostrava
    # nessuno.
    ("dihedral", "diedro min. [peggiore / mediana]"),
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
        diedro = volume.get("min_dihedral_deg", {})
        peggiore, mediana = diedro.get("min"), diedro.get("median")
        # Una riga vecchia del registro puo' non avere `min`: si scrive quello
        # che c'e' invece di fabbricare un trattino che si leggerebbe come un
        # valore misurato.
        if isinstance(peggiore, float) and isinstance(mediana, float):
            return f"{peggiore:.4g} / {mediana:.4g}"
        value = peggiore if isinstance(peggiore, float) else mediana
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
        return None, f"{percorso.name} {ILLEGGIBILE}: il file c'è sul disco e non si rilegge."
    if not isinstance(contenuto, dict):
        return None, f"{percorso.name} {FORMA_INATTESA}: il file c'è sul disco ma non ha la forma attesa."
    return contenuto, ""


def _numero(valore: float) -> str:
    """Sei cifre significative senza passare alla notazione esponenziale.

    %.6g da solo scrive 168845511.1 come 1.68846e+08: e' lo stesso valore, ma
    in una tabella stampata in appendice si legge peggio dell'intero. Fuori
    dall'intervallo qui sotto l'esponenziale resta l'unica resa leggibile.

    nan e inf non sono numeri da formattare ma esiti da dichiarare, e scritti
    cosi' come sono restano due parole inglesi in un documento italiano.
    """
    if math.isnan(valore):
        return NON_UN_NUMERO
    if math.isinf(valore):
        return f"-{INFINITO}" if valore < 0 else INFINITO
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
    if isinstance(valore, dict):
        if not valore:
            return MAPPA_VUOTA
        return ", ".join(f"{k} {_testo(v)}" for k, v in valore.items())
    scritto = str(valore)
    if scritto.strip():
        return scritto
    return VUOTO if not scritto else SOLI_SPAZI


def _piatto(prefisso: str, valore: object) -> Iterator[tuple[str, object]]:
    """Coppie (nome puntato, foglia) da una struttura annidata.

    Una mappa vuota annidata e' una foglia, non un ramo: ricorrendoci sopra non
    si produce nulla e la chiave sparisce dal documento senza lasciare traccia,
    che e' peggio di una cella vuota perche' non lascia nemmeno il buco. In cima
    invece la mappa vuota resta un ramo senza rami, altrimenti la riga uscirebbe
    con il nome vuoto, e a dire "nessuna voce" ci pensa gia' _tabella.
    """
    if isinstance(valore, dict) and (valore or not prefisso):
        for chiave, dentro in valore.items():
            yield from _piatto(f"{prefisso}.{chiave}" if prefisso else str(chiave), dentro)
    else:
        yield prefisso or SENZA_NOME, valore


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
    if not (out_dir / CONFIG_FILENAME).exists():
        # Un file che manca e uno che non si valida sono due fatti diversi, e
        # la sezione Parametri qui sopra dice gia' quale dei due e'.
        return None, f"{CONFIG_FILENAME} assente: niente con cui ricalcolare le impronte"
    try:
        stato = steps.run_state(out_dir, load_config(out_dir / CONFIG_FILENAME))
    except (OSError, ValueError, yaml.YAMLError):
        return None, f"{CONFIG_FILENAME} non è una configurazione valida"
    return {str(voce["chiave"]): str(voce["stato"]) for voce in stato}, ""


def _glossa(stati: list[str]) -> str:
    """La spiegazione dei soli stati che compaiono davvero nell'elenco.

    Elencare gli stati possibili invece di quelli presenti dice, degli step
    elencati, quello che vale per altri. Uno stato che il modulo non conosce
    resta senza glossa: il documento esce lo stesso, con una parola in meno e
    nessuna frase inventata.
    """
    return " ".join(
        f"{stato}: {GLOSSA[stato]}." for stato in sorted(set(stati)) if stato in GLOSSA
    )


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
        (chiave, valore)
        for chiave, valore in stato.items()
        if valore not in (VALIDO, MAI_ESEGUITO)
    ]
    eseguiti = len(stato) - len(mai)
    if not eseguiti:
        # Senza un conteggio, "restano fuori dal conteggio" non dice niente.
        return f"<p class='assente'>{NESSUNO_ESEGUITO}.</p>"
    coda = f" {len(mai)} step {NON_ESEGUITI}." if mai else ""
    if not guasti:
        return f"<p>{eseguiti} step su {eseguiti} {COERENTI}.{coda}</p>"
    nomi = ", ".join(f"{chiave} ({valore})" for chiave, valore in guasti)
    return (
        f"<p class='assente'>{eseguiti - len(guasti)} step su {eseguiti} {COERENTI}, "
        f"{len(guasti)} no: {html.escape(nomi)}. "
        f"{_glossa([valore for _, valore in guasti])}{coda}</p>"
    )


def _sezione_metriche(
    metriche: dict[str, object] | None, motivo: str, stato: dict[str, str] | None
) -> str:
    """Le metriche presenti e quelle mancanti, ognuna con il proprio stato."""
    if metriche is None:
        return f"<p class='assente'>{html.escape(motivo)}</p>"

    presenti = "".join(
        "<h3>{} [{}]</h3>{}".format(
            html.escape(nome),
            html.escape((stato or {}).get(nome, STATO_IGNOTO)),
            _tabella(_piatto("", valore)),
        )
        for nome, valore in sorted(metriche.items())
    )
    mancanti = [
        (chiave, (stato or {}).get(chiave, STATO_IGNOTO))
        for chiave in steps.STEP_KEYS
        if chiave not in metriche
    ]
    if not mancanti:
        return presenti + "<p>tutti gli step di una corsa completa hanno metriche.</p>"
    nomi = ", ".join(f"{chiave} ({valore})" for chiave, valore in mancanti)
    return presenti + (
        f"<p class='assente'>{SENZA_METRICHE} {html.escape(nomi)}. "
        f"{_glossa([valore for _, valore in mancanti])}</p>"
    )


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
    """Quante viste sono attese, quante sul disco, e quante finiscono in figura.

    Contarle con exists() e incorporarle con _e_png dichiara presenti immagini
    che il documento non mostra: chi conta le figure in appendice non ritrova
    il numero. Il file c'e' davvero, quindi "assente" sarebbe falso; e' il
    numero delle immagini che va detto, ed e' quello che manca.
    """
    if not viste:
        return "<p class='assente'>nessuna vista catturata: 0 attese, 0 presenti.</p>"
    presenti = [Path(vista) for vista in viste if Path(vista).exists()]
    rotte = [vista for vista in presenti if not _e_png(vista)]
    coda = (
        f" Di queste, {len(rotte)} {NON_INCORPORABILI}: "
        f"{IMMAGINI_NEL_DOCUMENTO} {len(presenti) - len(rotte)}."
        if rotte
        else ""
    )
    classe = "" if len(presenti) == len(viste) and not rotte else " class='assente'"
    return (
        f"<p{classe}>{len(viste)} attese, {len(presenti)} presenti, "
        f"{len(viste) - len(presenti)} assenti.{coda}</p>"
    )


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


MODELLI = ("as-built", "estruso", "primitive")
"""I tre modelli dello stesso pezzo, nell'ordine in cui il confronto li mostra.

as-built e' la corsa madre e c'e' sempre: e' la superficie rilevata in mesh
tetraedrica, che esiste dalla Fase 1. Gli altri due sono corse figlie e possono
mancare.
"""

CONFRONTABILI: dict[str, bool] = {
    "volume": True,
    "massa": True,
    "scostamento_nuvola": True,
    "gradi_di_liberta": True,
    "qualita_elementi": False,
    "rigidezza": False,
}
"""Quali grandezze si confrontano fra i tre modelli senza mentire.

- volume e massa: si', ed e' anche il confronto con il volume dichiarato dal
  disegno, quando il disegno c'e';
- scostamento dalla nuvola sorgente: si', ed e' il perno -- e' definito allo
  stesso modo per tutti e tre e risponde alla domanda vera, quanto costa in
  fedelta' al rilievo la regolarizzazione della forma;
- numero di nodi: si', ma solo accanto al tipo di elemento, perche' un C3D8I e
  un C3D4 non spendono lo stesso per nodo. La riga si intitola «nodi e tipo di
  elemento» e non «gradi di liberta'»: quel numero, 3 x nodi per un solido a
  spostamenti, non lo calcola nessuno in questa fase;
- qualita' degli elementi: NO. Rapporto raggio-spigolo per i tetraedri
  (radius_edge_ratio, la misura; tet.min_ratio e' invece il vincolo chiesto a
  TetGen), Jacobiano scalato per gli esaedri: due colonne separate, mai una
  differenza;
- rigidezza e spostamenti: NO. Nessun solutore in questa fase.
"""

NOTE_STATICHE = (
    "Nessuna armatura in alcun modello: calcestruzzo omogeneo. E' una scelta "
    "dell'autore e non una dimenticanza, e il dato delle barre resta nel disegno. "
    "Un telaio in cemento armato modellato senza armatura non è il telaio vero.",
    "Il set BASE non è una faccia del pezzo: è la quota di taglio scelta "
    "dall'operatore. Quella superficie non esiste nel pezzo vero, è dove abbiamo "
    "tagliato.",
)
"""Le due dichiarazioni che non dipendono da quale modello e' presente.

La terza -- il *TIE alle giunzioni -- non sta qui: modello.json la porta gia'
come nota_giunzioni (Task 10), e riscriverla in questo modulo duplicherebbe una
fonte che puo' divergere in silenzio. confronta() la legge e la mette in testa.
"""


def _legge_json(percorso: Path) -> dict | None:
    try:
        with percorso.open(encoding="utf-8") as handle:
            letto = json.load(handle)
    except (OSError, ValueError):
        # ValueError copre json.JSONDecodeError (ne e' sottoclasse) e
        # UnicodeDecodeError, che la lettura del file solleva prima ancora
        # del parse su un byte non UTF-8 (F4).
        return None
    return letto if isinstance(letto, dict) else None


def _testo_vincoli(voce: object) -> str:
    """giunzioni e ties non si sommano mai; i nodi dipendenti restano legati/totali."""
    if not isinstance(voce, dict):
        return _testo(voce)
    return (
        f"giunzioni {_testo(voce.get('giunzioni'))}, ties {_testo(voce.get('ties'))}, "
        f"nodi vincolati {_testo(voce.get('nodi_dipendenti_legati'))}/"
        f"{_testo(voce.get('nodi_dipendenti_totali'))}"
    )


def confronta(cartelle: list[Path]) -> dict[str, object]:
    """Il confronto fra i modelli **generati**, e la dichiarazione di quelli assenti.

    Regge gli insiemi parziali perche' l'utente sceglie quali modelli generare:
    con due su tre confronta due modelli e dice quale manca, con uno solo
    diventa una scheda singola e lo dichiara. Nessuna colonna con un trattino
    che somigli a un valore, nessuna differenza calcolata contro un modello
    assente.

    Non ricalcola nulla: legge cio' che ogni corsa ha scritto. Ricalcolare
    darebbe numeri che nessun artefatto sostiene.

    Lo scostamento dalla nuvola legge il verso mesh_to_cloud, non cloud_to_mesh:
    quality.vertex_deviation, che pipeline.genera_modello usa per lo
    scostamento_nuvola dei modelli parametrici, riproduce esattamente quel
    verso e non l'altro (`quality.vertex_deviation`, "la misura che questa
    funzione non replica e' cloud_to_mesh"). Leggere cloud_to_mesh per
    l'as-built metterebbe in colonna, sotto lo stesso nome, una misura
    diversa da quella dei parametrici -- l'errore esatto che questo task
    esiste per evitare. La chiave del valore e' anche maiuscola, RMS, perche'
    e' quella che PyMeshLab restituisce davvero (`quality.geometric_error`).
    """
    presenti: dict[str, dict] = {}
    for cartella in cartelle:
        percorso = Path(cartella)
        modello = _legge_json(percorso / "modello.json")
        metriche = _legge_json(percorso / METRICS_FILENAME) or {}
        wall = None
        if modello is None:
            # Assenza di modello.json non basta: e' un segnale negativo, e una
            # cartella vuota (percorso sbagliato, o corsa parametrica fallita a
            # meta') lo soddisfa allo stesso modo della vera corsa madre. Il
            # segno positivo della corsa madre e' 12_wall.json leggibile.
            wall = _legge_json(percorso / WALL_FILENAME)
            if wall is None:
                raise ValueError(
                    f"{percorso} non è una corsa valida: né modello.json né "
                    f"{WALL_FILENAME} si leggono, e senza uno dei due non è né "
                    "un modello parametrico né la corsa madre"
                )
            chiave = "as-built"
        else:
            chiave = str(modello.get("tipo"))
        if chiave in presenti:
            raise ValueError(
                f"due cartelle dichiarano lo stesso modello '{chiave}': "
                f"{presenti[chiave]['cartella']} e {percorso}"
            )
        presenti[chiave] = {"cartella": percorso, "metriche": metriche, "modello": modello, "wall": wall}

    mancanti = [nome for nome in MODELLI if nome not in presenti]

    volume: dict[str, float] = {}
    massa: dict[str, float] = {}
    scostamento: dict[str, object] = {}
    gradi: dict[str, object] = {}
    qualita: dict[str, dict] = {}
    vincoli: dict[str, object] = {}
    nota_giunzioni: str | None = None
    chiusura_volume: dict | None = None
    for nome, voce in presenti.items():
        if voce["modello"] is None:
            if voce["wall"] is not None:
                chiusura_volume = voce["wall"].get("chiusura_volume")
            export = voce["metriche"].get("11_export", {})
            volumi = voce["metriche"].get("10_volume_quality", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = (
                voce["metriche"]
                .get("07_surface_quality", {})
                .get("geometric_error", {})
                .get("mesh_to_cloud", {})
                .get("RMS")
            )
            gradi[nome] = {"nodi": volumi.get("nodes"), "elemento": export.get("element_type", "C3D4")}
            qualita[nome] = {"radius_edge_ratio": volumi.get("radius_edge_ratio")}
            vincoli[nome] = "non applicabile"
        else:
            export = voce["modello"].get("export", {})
            esaedri = voce["modello"].get("hexa", {})
            metriche_modello = voce["modello"].get("modello", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = (voce["modello"].get("scostamento_nuvola") or {}).get("rms")
            gradi[nome] = {"nodi": esaedri.get("nodes"), "elemento": export.get("element_type")}
            qualita[nome] = {"scaled_jacobian": esaedri.get("scaled_jacobian")}
            vincoli[nome] = {
                "giunzioni": metriche_modello.get("giunzioni"),
                "ties": metriche_modello.get("ties"),
                "nodi_dipendenti_legati": metriche_modello.get("nodi_dipendenti_legati"),
                "nodi_dipendenti_totali": metriche_modello.get("nodi_dipendenti_totali"),
            }
            if nota_giunzioni is None:
                nota_giunzioni = voce["modello"].get("nota_giunzioni")

    note = ([nota_giunzioni] if nota_giunzioni else []) + list(NOTE_STATICHE)

    return {
        "modelli": sorted(presenti),
        "mancanti": mancanti,
        "scheda_singola": len(presenti) == 1,
        "confrontabili": dict(CONFRONTABILI),
        "volume": volume,
        "massa": massa,
        "scostamento_nuvola": scostamento,
        "gradi_di_liberta": gradi,
        "qualita": qualita,
        "vincoli_giunzioni": vincoli,
        "chiusura_volume": chiusura_volume,
        "note_non_geometriche": note,
    }


_ETICHETTE_GRANDEZZE: tuple[tuple[str, str], ...] = (
    ("volume", "volume [mm^3]"),
    ("massa", "massa [t]"),
    ("scostamento_nuvola", "scostamento dalla nuvola [mm]"),
    ("gradi_di_liberta", "nodi e tipo di elemento"),
)
"""Che cosa si intitola ogni riga della tabella delle grandezze confrontabili.

Sorella di _COLUMNS, e per la stessa ragione: una chiave non si stampa mai, si
stampa la sua etichetta. Le chiavi restano quelle di CONFRONTABILI e dei
modello.json gia' sul disco, l'etichetta e' l'italiano che legge chi ha in mano
l'appendice.

L'unita' sta dentro l'etichetta, come in
("thickness_error", "errore di spessore [mm]"): in un'appendice cartacea una
colonna «massa» con dentro 0,25 non dice se sono tonnellate o chilogrammi.
mm^3 e non mm3 e' la grafia gia' in casa -- config.py scrive «densita [t/mm^3]»
e app.js la mostra cosi'.

`gradi_di_liberta` **non** si intitola «gradi di liberta'»: la chiave e' quella,
ma confronta() ci mette {"nodi", "elemento"} e i gradi di liberta' sarebbero
3 x nodi per un solido a spostamenti -- un numero che nessuno calcola qui.
Un'etichetta piu' credibile del suo contenuto e' peggio della chiave nuda: con
`gradi_di_liberta` in testa il lettore scartava la riga, con l'italiano di
appendice ci crede.
"""


def write_comparison_report(cartelle: list[Path], out_path: Path) -> Path:
    """Il confronto in una pagina, con lo stesso rivestimento del report di corsa.

    I modelli assenti compaiono per nome e con la dicitura «non generato», mai
    con un trattino in una colonna di numeri: un trattino in mezzo ai numeri
    somiglia a un valore. Una chiave presente ma valorizzata None passa comunque
    da _testo, che la scrive «non impostato»: un modello.json piu' vecchio o
    generato da una versione precedente puo' non portare ancora una chiave, e
    non e' lo stesso di «non generato».
    """
    confronto = confronta(cartelle)
    righe = []
    for grandezza, etichetta in _ETICHETTE_GRANDEZZE:
        celle = "".join(
            f"<td>{'non generato' if nome not in confronto[grandezza] else html.escape(_testo(confronto[grandezza][nome]))}</td>"
            for nome in MODELLI
        )
        righe.append(f"<tr><th>{html.escape(etichetta)}</th>{celle}</tr>")

    qualita_righe = "".join(
        f"<tr><th>{nome}</th><td>{html.escape(_testo(confronto['qualita'].get(nome, 'non generato')))}</td></tr>"
        for nome in MODELLI
    )
    vincoli_righe = "".join(
        f"<tr><th>{nome}</th><td>{html.escape(_testo_vincoli(confronto['vincoli_giunzioni'].get(nome, 'non generato')))}</td></tr>"
        for nome in MODELLI
    )
    note = "".join(f"<li>{html.escape(nota)}</li>" for nota in confronto["note_non_geometriche"])
    intestazione = "".join(f"<th>{nome}</th>" for nome in MODELLI)
    avviso = (
        "<p class='avviso'>Un solo modello generato: questa non è una tabella di "
        "confronto ma una <strong>scheda singola</strong>.</p>"
        if confronto["scheda_singola"]
        else ""
    )

    pagina = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>MeshRec -- confronto fra modelli</title>
<style>{_STILE}</style></head><body>
<h1>Confronto fra modelli</h1>
{avviso}
<h2>Grandezze confrontabili</h2>
<table><thead><tr><th></th>{intestazione}</tr></thead><tbody>{''.join(righe)}</tbody></table>
<h2>Qualità degli elementi: due colonne, mai una differenza</h2>
<p>radius_edge_ratio vale per i tetraedri, il Jacobiano scalato per gli esaedri. Non sono
la stessa grandezza e la loro differenza non è un numero.</p>
<table><tbody>{qualita_righe}</tbody></table>
<h2>Vincoli alle giunzioni: il limite che il vincolo aggiunge, non la geometria</h2>
<p>Giunzioni tagliate e *TIE effettivamente scritti restano due numeri distinti;
i nodi della superficie dipendente vincolati sul totale dicono quanto il
solutore chiude davvero. as-built è monolitico: non applicabile.</p>
<table><tbody>{vincoli_righe}</tbody></table>
<h2>Che cosa non deriva dalla geometria</h2>
<ul>{note}</ul>
<h2>Che cosa questa fase non dice</h2>
<p>Nessun solutore è stato eseguito: rigidezza e spostamenti non sono in questa
pagina perché non sono stati calcolati, non perché siano stati omessi.</p>
</body></html>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(pagina, encoding="utf-8")
    return Path(out_path)
