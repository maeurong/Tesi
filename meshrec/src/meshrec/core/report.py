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
from datetime import datetime
from pathlib import Path
from typing import Iterator, get_args

import yaml

from meshrec.core import steps
from meshrec.core.config import PipelineConfig, load_config
from meshrec.core.pipeline import METRICS_FILENAME, WALL_FILENAME
from meshrec.core.sweep import load_registry, objectives

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
# La stessa regola nella tabella dello sweep, che e' la piu' lunga delle tre.
# Un candidato che non arriva in fondo non ha 10_volume_quality: tetraedri,
# fuori vincolo e diedro non sono zero, non esistono. Sul registro di
# experiments/muro sono quattro righe su undici, tre celle bianche ciascuna,
# e chi guarda 132 righe su 23 pagine non ha modo di sapere se manca il dato o
# se il generatore ha saltato una colonna. Nessun trattino:
# write_comparison_report ha gia' deciso che un trattino in mezzo ai numeri
# somiglia a un valore.
NON_MISURATO = "non misurato"
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

# La resa italiana dei numeri, una sola per tutti e tre i documenti.
#
# I documenti sono un'appendice italiana e vengono stampati, dove la prosa del
# progetto scrive gia' «8,10%» e «1.752.795 tetraedri». Le tabelle scrivevano
# invece `1.1943`: in un documento italiano quel punto si legge come
# separatore delle migliaia, cioe' «milleduecento», e il segno dice l'opposto
# di quel che significa. Da qui due decisioni che stanno in piedi solo
# insieme -- la virgola sui decimali e il punto sulle migliaia -- perche' un
# solo segno per due mestieri, nella stessa colonna, e' proprio il difetto per
# cui il raggruppamento non era stato aggiunto prima.
#
# `format` sa raggruppare, ma solo alla maniera inglese: `f"{1752795:,}"` da'
# "1,752,795", che e' esattamente la convenzione opposta. I due segni si
# scambiano con una tabella di traduzione invece che con due `replace`: la
# traduzione e' simultanea, mentre due sostituzioni in fila si
# sovrascriverebbero a vicenda e obbligherebbero a inventare un segno
# intermedio.
#
# Il raggruppamento va sulle **grandezze**: quanto misura una cosa, quante ce
# ne sono. Non sugli identificatori -- l'impronta esadecimale, il commit della
# provenienza, `C3D10`, `C25_30`, un numero di versione -- che nei tre
# documenti arrivano tutti come stringhe e restano intatti, perche' i due rami
# qui sotto guardano il tipo e non le cifre. Un identificatore spezzato in tre
# non si rimette insieme.
_SEGNI_ITALIANI = str.maketrans(",.", ".,")


def _italiano(scritto: str) -> str:
    """Una resa di `format` con i due segni scambiati: inglese in, italiano out."""
    return scritto.translate(_SEGNI_ITALIANI)


_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "impronta"),
    ("axes", "assi"),
    ("outcome", "esito"),
    ("thickness_error", "errore di spessore [mm]"),
    ("tets", "tetraedri"),
    ("over", "fuori vincolo [frazione]"),
    # Peggiore **e** mediana, non la sola mediana. La mediana confronta due
    # candidati dello sweep; il peggiore e' l'unico dei due che vede uno
    # sliver, e lo sliver e' l'elemento che il vincolo raggio-spigolo di
    # TetGen non puo' fermare: misurato, un tetraedro di manuale con
    # raggio-spigolo 0,707 -- ben sotto il limite di 2,0 -- ha un diedro
    # minimo di 0,162 gradi. Con la sola mediana in tabella quel maglio si
    # legge sano. Il numero c'era gia' in metrics.json, non lo mostrava
    # nessuno.
    #
    # L'unita' sta dentro l'etichetta come in "errore di spessore [mm]", ed e'
    # la stessa ragione di _ETICHETTE_GRANDEZZE: su carta un numero senza
    # unita' non si ricostruisce. «frazione» e non «%» perche' il dato non si
    # tocca -- radius_edge_over_reference vale 0,08098 e non 8,098 -- e
    # un'etichetta in percento sopra una frazione e' la stessa bugia con un
    # sintomo peggiore.
    ("dihedral", "diedro min. [gradi: peggiore / mediana]"),
    ("duration_s", "durata [s]"),
)


def histogram_svg(values: list[float], title: str, bins: int) -> str:
    """Istogramma come SVG scritto a mano, senza dipendenze.

    Le misure restano quelle di sempre, 320 x 140, ma passano anche da
    `viewBox`: con le sole `width`/`height` in pixel il riquadro non si
    rimpicciolisce sotto la larghezza di una finestra stretta e sfonda la
    pagina in orizzontale. Con il `viewBox` il foglio di stile puo' dargli una
    larghezza relativa, e il disegno la segue.

    Le barre non hanno piu' un colore proprio: `currentColor` le lega alla
    tinta che il foglio da' al riquadro, cosi' l'istogramma cambia con il tema
    del documento invece di restare l'unico grigio-azzurro scritto a mano nel
    codice. Fuori dal documento, senza foglio, `currentColor` e' il nero
    ereditato, che e' esattamente cio' che serve a un SVG che deve reggere da
    solo.

    Il `role='img'` con dentro un `<title>` vale per entrambi i rami, anche
    per quello vuoto: un riquadro senza nome accessibile e' un buco per chi
    legge con un lettore di schermo, e il ramo vuoto e' proprio quello che ha
    qualcosa da dichiarare. Il nome sta in un `<title>` e non in un
    `aria-label` perche' e' il modo canonico di nominare un SVG, e perche' il
    testo dentro un elemento non e' un attributo che qualcuno debba ricordarsi
    di leggere.
    """
    etichetta = html.escape(title)
    if not values:
        return (
            f"<svg class='istogramma' viewBox='0 0 320 140' width='320' height='140' role='img'>"
            f"<title>{etichetta}: vuoto</title>"
            f"<text x='8' y='20' font-size='11'>{etichetta}: vuoto</text></svg>"
        )

    low, high = min(values), max(values)
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    tallest = max(counts) or 1

    bars = "".join(
        f"<rect x='{8 + index * (300 / bins):.1f}' y='{120 - 100 * count / tallest:.1f}' "
        f"width='{300 / bins - 2:.1f}' height='{100 * count / tallest:.1f}' fill='currentColor'/>"
        for index, count in enumerate(counts)
    )
    return (
        f"<svg class='istogramma' viewBox='0 0 320 140' width='320' height='140' role='img'>"
        f"<title>{etichetta}</title>"
        f"<text x='8' y='14' font-size='11'>{etichetta}</text>{bars}"
        # La linea di base: senza, le barre galleggiano e le due estremita'
        # dell'intervallo qui sotto non si capisce a che cosa si riferiscano.
        f"<line x1='8' y1='120.5' x2='308' y2='120.5' stroke='currentColor' stroke-opacity='0.35'/>"
        f"<text x='8' y='134' font-size='10'>{_italiano(f'{low:,.3g}')}</text>"
        f"<text x='260' y='134' font-size='10'>{_italiano(f'{high:,.3g}')}</text></svg>"
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
            return _italiano(f"{peggiore:,.4g} / {mediana:,.4g}")
        value = peggiore if isinstance(peggiore, float) else mediana
    else:
        value = row.get(key)

    if isinstance(value, float):
        return _italiano(f"{value:,.4g}")
    # I tetraedri sono un intero e non passerebbero da nessuna formattazione:
    # senza questo ramo la colonna piu' larga della tabella e' anche l'unica
    # che si conta col dito. Il booleano e' un intero per Python e non per chi
    # legge: raggruppato uscirebbe "1".
    if isinstance(value, int) and not isinstance(value, bool):
        return _italiano(f"{value:,}")
    if isinstance(value, dict):
        return ", ".join(
            f"{html.escape(str(name))}={html.escape(str(item))}" for name, item in value.items()
        ) or "base"
    return html.escape(str(value)) if value is not None else NON_MISURATO


# Il rivestimento dei tre documenti, uno solo per tutti e tre.
#
# Erano due fogli: uno scritto dentro write_report e uno qui, e divergevano su
# una regola che decide come si legge una tabella -- `text-align: right` la',
# `text-align: left` qui. Due documenti dello stesso programma, stampati nella
# stessa appendice, allineavano i numeri in due modi. Un foglio solo non e'
# risparmio di righe: e' l'unico modo perche' quella divergenza non torni.
#
# I documenti si aprono da disco, viaggiano allegati e vengono stampati. Da
# qui tre vincoli che non sono estetici:
#
# - **nessuna risorsa esterna.** Niente <link>, niente @import, nessun
#   carattere scaricato: le pile sono quelle che la macchina ha gia'. E' lo
#   stesso ragionamento -- e le stesse due pile -- di ui/stile.css, che le
#   nomina invece di fidarsi del solo `system-ui` perche' il ripiego di
#   `system-ui` su un Windows senza Segoe UI e' Times New Roman.
# - **la stampa e' in bianco e nero.** Ogni cosa che il documento dice con il
#   colore la deve dire anche senza. Il fronte di Pareto -- il risultato
#   principale della tabella dello sweep -- portava il solo fondo verde e il
#   grassetto: i browser non stampano i fondi se non glielo si chiede, e sulla
#   carta restava il peso di un corpo di 0,8rem. Adesso porta anche un
#   filetto, che si stampa sempre.
# - **l'inchiostro si paga.** Niente griglia di riquadri intorno a ogni cella
#   e niente fondo pieno sulle intestazioni: filetti orizzontali, che e' anche
#   il modo in cui una tabella di riferimento si e' sempre composta.
#
# La tavolozza e la scala dei passi vengono da ui/stile.css e valgono li' le
# stesse ragioni, misurate: il rapporto di --testo su carta, il verde
# dell'azione, l'ocra dell'avviso, il rosso del guasto, il passo di 4px. Il
# report non e' l'interfaccia e non deve somigliarle -- uno e' proiettato in
# discussione, l'altro e' stampato e rilegato -- ma quando i due dicono la
# stessa cosa la dicono con la stessa tinta, e dove divergono divergono per
# una ragione: qui il corpo del testo e' un graziato, perche' il documento si
# legge su carta e non a tre metri da un proiettore, e i dati stanno tutti in
# una pila a passo fisso, perche' una colonna di numeri da confrontare a
# colpo d'occhio vuole cifre della stessa larghezza.
_STILE = """
/* Hallmark · genre: editorial · theme: Almanac · macrostructure: Long Document
 * nav: none · footer: none · enrichment: none · motion: none
 * (documento stampabile, non pagina web: nessuna di queste cose esiste qui)
 * paper #fbfaf8 · ink #1c1b19 · accent #2f5d50 · rule #ddd9d2 / #948e85
 * display + body: local serif stack · data: local mono stack
 * print is the primary medium · pre-emit critique: P5 H5 E4 S5 R5 V4 */
:root {
  --carta: #fbfaf8;
  --inchiostro: #1c1b19;
  --tenue: #6b6862;
  --filetto: #ddd9d2;
  --filetto-marcato: #948e85;
  --accento: #2f5d50;
  --avviso: #9a5b12;
  --guasto: #a02020;
  --fronte: #eaf3ea;
  --passo-1: 0.25rem;
  --passo-2: 0.5rem;
  --passo-3: 0.75rem;
  --passo-4: 1rem;
  --passo-6: 1.5rem;
  --passo-8: 2rem;
  --stack-prosa: ui-serif, Georgia, "Times New Roman", "Liberation Serif", serif;
  --stack-dati: ui-monospace, "Cascadia Mono", Consolas, "SF Mono", "DejaVu Sans Mono", monospace;
  --tipo-dato: 0.8125rem;
  --tipo-nota: 0.75rem;
}
html, body { overflow-x: clip; }
body {
  font-family: var(--stack-prosa);
  font-size: 1rem;
  line-height: 1.5;
  color: var(--inchiostro);
  background: var(--carta);
  margin: var(--passo-8) auto;
  padding: 0 var(--passo-6);
  /* Larga per le tabelle, non per la prosa: la misura del testo la fissa la
     regola su `p`, in caratteri, e resta quella qualunque sia la finestra. */
  max-width: 72rem;
}
h1, h2, h3 { line-height: 1.25; overflow-wrap: anywhere; }
h1 {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 0 0 var(--passo-6);
  padding-bottom: var(--passo-3);
  border-bottom: 2px solid var(--inchiostro);
}
h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: var(--passo-8) 0 var(--passo-3);
  padding: var(--passo-2) 0;
  border-top: 1px solid var(--filetto-marcato);
  background: var(--carta);
  position: sticky;
  top: 0;
  z-index: 1;
}
h3 {
  font-family: var(--stack-dati);
  font-size: var(--tipo-dato);
  font-weight: 600;
  letter-spacing: 0.02em;
  margin: var(--passo-6) 0 var(--passo-2);
}
p { max-width: 68ch; margin: var(--passo-3) 0; }
ul { max-width: 68ch; padding-left: var(--passo-4); }
li { margin: var(--passo-2) 0; }
.tabellone { overflow-x: auto; }
table {
  border-collapse: collapse;
  font-size: var(--tipo-dato);
  margin: var(--passo-3) 0 var(--passo-6);
  border-top: 1.5px solid var(--inchiostro);
  border-bottom: 1.5px solid var(--inchiostro);
}
th, td {
  padding: var(--passo-1) var(--passo-3);
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--filetto);
}
th { font-family: var(--stack-dati); font-weight: 600; }
td {
  font-family: var(--stack-dati);
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
thead th {
  font-size: var(--tipo-nota);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--tenue);
  border-bottom: 1.5px solid var(--inchiostro);
}
.prosa th { font-family: var(--stack-prosa); }
/* Le celle dello sweep non vanno a capo: un esito diviso in «riusci / to» e
   soprattutto un intero diviso in «160714 / 6» sono, in una colonna di
   numeri da confrontare a occhio, un dato illeggibile. Le intestazioni
   invece vanno a capo, sugli spazi, perché «errore di spessore [mm]» su una
   riga sola allarga la colonna quanto tutta la sua misura.
   L'impronta è l'unica eccezione: sono 64 cifre esadecimali, una parola
   sola, e su una riga sarebbe larga quanto mezza pagina. Va a capo in poche
   righe e non in sette: la larghezza minima e il corpo ridotto stanno qui
   per questo, altrimenti l'identificativo detta l'altezza di ogni riga della
   tabella e la colonna più opaca diventa la più alta. */
.sweep tbody td { white-space: nowrap; }
.sweep tbody td:first-child {
  white-space: normal;
  word-break: break-all;
  min-width: 22ch;
  max-width: 34ch;
  font-size: var(--tipo-nota);
  line-height: 1.25;
  color: var(--tenue);
}
.sweep th:nth-child(n+4), .sweep td:nth-child(n+4) { text-align: right; }
tr.fronte td {
  background: var(--fronte);
  font-weight: 600;
  border-top: 1px solid var(--inchiostro);
  border-bottom: 1px solid var(--inchiostro);
}
tr.fronte td:first-child { border-left: 3px solid var(--inchiostro); color: var(--inchiostro); }
tr.fronte td:last-child { border-right: 1px solid var(--inchiostro); }
p.assente {
  border-left: 3px solid var(--guasto);
  background: color-mix(in srgb, var(--guasto) 6%, var(--carta));
  padding: var(--passo-2) var(--passo-3);
}
p.avviso {
  border-left: 3px solid var(--avviso);
  background: color-mix(in srgb, var(--avviso) 8%, var(--carta));
  padding: var(--passo-2) var(--passo-3);
}
/* Sta sotto il titolone e non fa parte del testo: corpo di nota, pila dei
   dati perché è fatta di percorsi e di impronte, e si spezza dove capita
   perché un percorso assoluto è più largo di mezza pagina. */
p.provenienza {
  font-family: var(--stack-dati);
  font-size: var(--tipo-nota);
  color: var(--tenue);
  margin: calc(-1 * var(--passo-4)) 0 var(--passo-6);
  overflow-wrap: anywhere;
}
.istogramma {
  display: inline-block;
  width: 100%;
  max-width: 20rem;
  height: auto;
  margin: 0 var(--passo-4) var(--passo-4) 0;
  color: var(--accento);
}
.istogramma text { font-family: var(--stack-dati); fill: var(--inchiostro); }
figure { display: inline-block; max-width: 30rem; margin: 0 var(--passo-4) var(--passo-4) 0; }
figcaption {
  font-family: var(--stack-dati);
  font-size: var(--tipo-nota);
  color: var(--tenue);
  margin-top: var(--passo-1);
}
/* Mai ingrandita oltre la sua taglia vera: una vista scalata in su è una
   figura sfocata in appendice, e a schermo quel difetto non si vede. */
img { display: block; max-width: 100%; height: auto; border: 1px solid var(--filetto-marcato); }
@media (max-width: 40rem) {
  body { margin: var(--passo-4) auto; padding: 0 var(--passo-4); }
}
@page { margin: 18mm 15mm; }
@media print {
  body { margin: 0; padding: 0; max-width: none; background: none; font-size: 10pt; }
  /* Il fondo del titolo serve solo a coprire quello che gli scorre sotto
     quando resta appiccicato in cima: sulla carta niente scorre, e resterebbe
     un rettangolo di inchiostro che non dice niente. */
  h2 { position: static; background: none; }
  thead { display: table-header-group; }
  tr, figure, .istogramma { break-inside: avoid; }
  h1, h2, h3 { break-after: avoid; }
  .tabellone { overflow: visible; }
  /* Sulla carta la larghezza non è negoziabile: l'impronta rinuncia al suo
     minimo e va a capo quante volte serve, perché una tabella tagliata dal
     bordo del foglio perde le colonne di destra, che sono le misure. */
  .sweep tbody td:first-child { min-width: 0; }
  p.assente, p.avviso { background: none; }
}
"""

# L'intestazione comune ai tre documenti: la codifica, e la larghezza reale
# della finestra invece di quella finta a 980px che i telefoni assumono per i
# documenti che non la dichiarano.
_TESTA = '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'

# «La provenienza e' parte del risultato. Un artefatto, una metrica o una
# vista dicono sempre da quale configurazione e da quale esecuzione vengono»
# (PRODUCT.md, quarto principio). I tre documenti finiscono stampati in
# appendice e si discutono mesi dopo essere stati generati: senza queste due
# cose diventano tre fogli che nessuno puo' ricondurre a una corsa, e il
# titolone da solo -- «Sweep -- muro» -- non e' un riferimento.
SORGENTE = "sorgente:"
GENERATO = "generato il"


def _provenienza(sorgente: str, coda: str = "") -> str:
    """Da dove viene il documento e quando e' stato scritto, sotto il titolone.

    La data la mette l'orologio della macchina che genera, perche' e' l'unica
    che risponde alla domanda vera: quanto e' vecchio il foglio che ho in
    mano. Tutto il resto viene da una lettura, `coda` compresa -- per lo sweep
    e' il commit gia' scritto nelle righe del registro, non quello del
    processo che compone il documento, che sarebbe un'altra corsa.
    """
    quando = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"<p class='provenienza'>{SORGENTE} {html.escape(sorgente)} — "
        f"{GENERATO} {quando}{coda}</p>"
    )


# Gli istogrammi dello sweep descrivono la stessa popolazione del fronte di
# Pareto -- sweep.objectives, cioe' i candidati riusciti, completi e con le
# misure sul disco -- e non tutte le righe del registro. Un candidato fallito
# porta comunque un thickness_error che non misura nessuna mesh: sul registro
# di experiments/muro quattro falliti portano 0 oppure 9,125 e spostavano la
# distribuzione dei sette riusciti. «confrontabili» e' la parola che sweep.py
# usa gia' per questo insieme (check_sweep).
SOLO_CONFRONTABILI = "solo i confrontabili"
NESSUN_CONFRONTABILE = "nessun candidato confrontabile: nessuna distribuzione da mostrare"

# Un registro senza righe non e' un guasto: e' uno sweep che non ha ancora
# prodotto niente, o un esperimento cancellato. Stampata, una tabella con le
# sole intestazioni e nessuna riga si legge invece come un generatore rotto, e
# nessuno puo' chiedere al foglio quale delle due cose sia. Il documento esce
# lo stesso e dichiara il vuoto, che e' un dato.
NESSUN_CANDIDATO = "registro vuoto: nessun candidato da mostrare"


def write_report(registry_path: Path, out_path: Path) -> Path:
    """Scrive il report HTML a partire dal solo registro.

    Il registro e' l'unica rappresentazione autoritativa: la tabella piatta
    per l'appendice si genera da qui e non si mantiene a mano, che e' il modo
    in cui in Fase 1 numeri di corse diverse sono finiti fianco a fianco.
    """
    rows = load_registry(registry_path)
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in _COLUMNS)
    body = "".join(
        "<tr{}>{}</tr>".format(
            " class='fronte'" if row.get("on_front") else "",
            "".join(f"<td>{_cell(row, key)}</td>" for key, _ in _COLUMNS),
        )
        for row in rows
    )

    # La stessa lettura che decide il fronte, riusata: cosi' la tabella e le
    # distribuzioni parlano dello stesso insieme di candidati invece di due.
    misurati = [assi for assi in (objectives(row) for row in rows) if assi is not None]
    errors = [assi[0] for assi in misurati]
    tets = [assi[1] for assi in misurati]

    tabella = (
        f"""<p>{len(rows)} candidati. Le righe evidenziate sono il <strong>fronte</strong> di Pareto:
errore di spessore, numero di tetraedri e frazione fuori vincolo, tutti da minimizzare.</p>
<div class="tabellone"><table class="sweep"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"""
        if rows
        else f"<p class='assente'>{NESSUN_CANDIDATO}.</p>"
    )

    if not rows:
        # Il paragrafo del registro vuoto ha gia' detto tutto. Due riquadri con
        # dentro la parola «vuoto» sono, stampati, due rettangoli bianchi da
        # cinque centimetri che lo ripetono peggio.
        distribuzioni = ""
    elif not misurati:
        distribuzioni = f"<h2>Distribuzioni</h2>\n<p class='assente'>{NESSUN_CONFRONTABILE}.</p>"
    else:
        distribuzioni = f"""<h2>Distribuzioni</h2>
<p>Solo i candidati confrontabili entrano in queste distribuzioni — riusciti, completi e con le
misure sul disco: {len(misurati)} su {len(rows)}. Gli altri restano nella tabella qui sopra, dove
la colonna «esito» dice perché.</p>
{histogram_svg(errors, f"errore di spessore [mm] — {SOLO_CONFRONTABILI}", bins=12)}
{histogram_svg(tets, f"tetraedri — {SOLO_CONFRONTABILI}", bins=12)}"""

    # Il commit e' gia' in ogni riga, sotto provenance: quello del processo che
    # compone il documento sarebbe l'impronta di un'altra esecuzione.
    commit = sorted(
        {
            str(riga["provenance"]["commit"])
            for riga in rows
            if isinstance(riga.get("provenance"), dict) and riga["provenance"].get("commit")
        }
    )
    coda = f" — commit {html.escape(', '.join(commit))}" if commit else ""

    document = f"""<!doctype html>
<html lang="it"><head>{_TESTA}<title>Sweep — {html.escape(registry_path.parent.name)}</title>
<style>{_STILE}</style></head><body>
<h1>Sweep — {html.escape(registry_path.parent.name)}</h1>
{_provenienza(str(registry_path), coda)}
{tabella}
{distribuzioni}
</body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path


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
    cosi' come sono restano due parole inglesi in un documento italiano. Le due
    guardie stanno prima di ogni formattazione perche' nessuno dei due ha
    migliaia o decimali da rendere.

    Dentro l'intervallo si raggruppa dalle migliaia in su, quattro cifre
    comprese: `1.234` e non `1234`. Le due regole sono entrambe in uso, ma
    tenerne una sola evita che nella stessa colonna `1234` e `12.345` sembrino
    due formati diversi dello stesso dato.

    Fuori dall'intervallo il numero passa all'esponenziale, e li' la resa e'
    dichiarata invece che casuale: la mantissa e' una grandezza e prende la
    virgola, l'esponente e' la potenza di dieci che la scala e resta come si
    scrive. Un punto ogni tre cifre dentro `e-09` non separerebbe niente, e
    `%g` non ne produce comunque: la traduzione tocca il solo punto decimale.
    """
    if math.isnan(valore):
        return NON_UN_NUMERO
    if math.isinf(valore):
        return f"-{INFINITO}" if valore < 0 else INFINITO
    arrotondato = float(f"{valore:.6g}")
    if arrotondato and not 1e-4 <= abs(arrotondato) < 1e12:
        return _italiano(f"{arrotondato:.6g}")
    return _italiano(f"{arrotondato:,.10f}".rstrip("0").rstrip("."))


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
    # Un intero non passa da _numero: `%.6g` lo arrotonderebbe a sei cifre
    # significative, e i 6.329.096 punti letti da una nuvola diventerebbero
    # 6.329.100. Un conteggio non si arrotonda, si raggruppa e basta.
    if isinstance(valore, int):
        return _italiano(f"{valore:,}")
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


def _etichette(percorso: tuple[str, ...]) -> list[str]:
    """L'etichetta di ogni passo di una chiave puntata di configurazione.

    «Una chiave non si stampa mai, si stampa la sua etichetta» (PRODUCT.md).
    Le etichette esistono gia' e non vanno scritte qui: sono i `title` dei
    campi di PipelineConfig, messi li' per il pannello, e `input.max_points`
    stampato crudo in appendice non dice ne' che cosa misura ne' in che unita'.

    E' la stessa logica di `server._etichetta_del_percorso`, riscritta qui
    perche' quel modulo e' l'interfaccia e questo il generatore dei documenti:
    li' serve il nome del campo che il validatore ha rifiutato, uno solo, qui
    servono tutti i passi perche' la riga li porta annidati.

    Dove il `title` manca resta la chiave, che e' l'unica cosa che si sa, e non
    si inventa una frase. Vale anche per una chiave che il modello non conosce
    affatto: un config.yaml scritto da una versione precedente ne porta, e
    fermarsi li' lascerebbe la riga senza nome.
    """
    modello: object = PipelineConfig
    nomi: list[str] = []
    for passo in percorso:
        campi = getattr(modello, "model_fields", None)
        if not campi or passo not in campi:
            return nomi + list(percorso[len(nomi) :])
        campo = campi[passo]
        nomi.append(campo.title or passo)
        # `analysis` e' `AnalysisConfig | None`: i campi stanno sul modello e
        # non sull'unione, e leggerli dall'annotazione grezza li perderebbe.
        modello = next(
            (
                tipo
                for tipo in get_args(campo.annotation) or (campo.annotation,)
                if tipo is not type(None)
            ),
            None,
        )
    return nomi


def _sezione_parametri(configurazione: dict[str, object]) -> str:
    """I parametri della corsa, un'intestazione per blocco e le etichette al posto delle chiavi.

    Novanta righe di chiavi puntate di seguito sono, stampate, una colonna che
    nessuno legge: la gerarchia che il config.yaml ha gia' si vede se i blocchi
    restano blocchi. La forma e' quella che «Metriche per step» usa da sempre
    -- un <h3> e la sua tabella -- riusata invece di inventarne una seconda.

    Un blocco che non e' una mappa (`analysis: null` sta in ogni corsa senza
    analisi) resta una riga sola col nome del blocco: passarlo a `_piatto` gli
    darebbe il nome vuoto, cioe' la cella bianca di sempre.
    """
    pezzi = []
    for blocco, dentro in configurazione.items():
        titolo = _etichette((str(blocco),))[0]
        if isinstance(dentro, dict) and dentro:
            coppie = [
                (" · ".join(_etichette((str(blocco), *nome.split(".")))[1:]), valore)
                for nome, valore in _piatto("", dentro)
            ]
        else:
            coppie = [(titolo, dentro)]
        pezzi.append(f"<h3>{html.escape(titolo)}</h3>{_tabella(iter(coppie))}")
    return "".join(pezzi) or "<p>nessuna voce.</p>"


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
        _sezione_parametri(configurazione)
        if configurazione is not None
        else f"<p class='assente'>{html.escape(motivo_config)}</p>"
    )

    documento = f"""<!doctype html>
<html lang="it"><head>{_TESTA}<title>Corsa: {html.escape(out_dir.name)}</title>
<style>{_STILE}</style></head><body>
<h1>Corsa: {html.escape(out_dir.name)}</h1>
{_provenienza(str(out_dir))}
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
    "Nessuna armatura in alcun modello: calcestruzzo omogeneo. È una scelta "
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

    La cartella di ogni modello esce insieme alle sue misure: il confronto si
    stampa in appendice con le colonne intitolate «as-built», «estruso» e
    «primitive», e senza il percorso quei tre nomi non riconducono a nessuna
    corsa sul disco.

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
        "cartelle": {nome: str(voce["cartella"]) for nome, voce in presenti.items()},
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
    sorgenti = ", ".join(
        f"{nome} {confronto['cartelle'][nome]}"
        for nome in MODELLI
        if nome in confronto["cartelle"]
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
<html lang="it"><head>{_TESTA}<title>MeshRec — confronto fra modelli</title>
<style>{_STILE}</style></head><body>
<h1>Confronto fra modelli</h1>
{_provenienza(sorgenti)}
{avviso}
<h2>Grandezze confrontabili</h2>
<div class="tabellone"><table class="prosa"><thead><tr><th></th>{intestazione}</tr></thead><tbody>{''.join(righe)}</tbody></table></div>
<h2>Qualità degli elementi: una misura per modello, mai una differenza</h2>
<p>radius_edge_ratio vale per i tetraedri, il Jacobiano scalato per gli esaedri. Non sono
la stessa grandezza e la loro differenza non è un numero: ogni modello porta la propria,
col nome davanti, e nessuna colonna le affianca.</p>
<div class="tabellone"><table class="prosa"><thead><tr><th>modello</th><th>misura e valore</th></tr></thead><tbody>{qualita_righe}</tbody></table></div>
<h2>Vincoli alle giunzioni: il limite che il vincolo aggiunge, non la geometria</h2>
<p>Giunzioni tagliate e *TIE effettivamente scritti restano due numeri distinti;
i nodi della superficie dipendente vincolati sul totale dicono quanto il
solutore chiude davvero. as-built è monolitico: non applicabile.</p>
<div class="tabellone"><table class="prosa"><tbody>{vincoli_righe}</tbody></table></div>
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
