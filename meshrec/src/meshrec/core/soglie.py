"""Le soglie di verifica: ognuna con la fonte, l'origine del valore, e la data in cui e' stata fissata.

Unico luogo dove una soglia di verifica ha il proprio valore, come
`core/config.py` lo e' per i parametri di elaborazione. La decisione sta in
https://github.com/maeurong/Tesi/issues/35, ratificata il 26/08/2026.

**Verifica, non validazione.** Nel vocabolario di ASME V&V 10 *verification* e'
«il codice risolve giuste le equazioni» e *validation* e' «le equazioni
descrivono la realta'». Tutte le soglie di questo registro sono di
verification: nessuna confronta il modello con una misura sperimentale, perche'
sul telaio non ne esiste nessuna. Il nome del modulo lo dice per non
contraddire `docs/validazione/README.md`, che vieta di chiamare «validato» cio'
che non lo e'.

**Perche' un dato e non una costante.** La lacuna n. 3 misurata sui 17 articoli
di `Articoli/`: le soglie si dichiarano quasi sempre *dopo* aver visto il
numero, e uno solo su diciassette la fissa prima citando la fonte. Una soglia
decisa dopo non e' un test, e' una descrizione. Tenere `fonte`, `origine` e
`fissata` accanto al valore rende quella pretesa verificabile invece che
dichiarata.

**`fonte` e `origine` sono cose diverse, e confonderle era il difetto.** Una
prima stesura scriveva «Benzley et al. 1995» accanto al fattore 2,0 come se il
2,0 stesse in Benzley: non ci sta. Benzley e' il **riferimento** contro cui il
nostro errore si misura; il 2,0 e' **nostro**. `origine` dice quale dei tre casi
e' -- `letta` (il numero e' pubblicato nella fonte), `derivata` (calcolato da un
fatto della fonte), `nostra` (scelto da noi, in assenza di un valore
pubblicato). Una soglia `nostra` senza una nota che dica perche' viene
rifiutata dal registro.

**Le tre classi, e perche' sono tre.**

- `cancello` -- boccia. Esiste solo dove il riferimento e' esterno e duro.
- `etichetta` -- conta e riporta, non boccia. E' la classe delle metriche di
  qualita' dell'elemento: TetGen con `-q` non garantisce **alcun** angolo
  diedro minimo (predefinito 0 gradi), quindi gli sliver esistono per
  costruzione. Un cancello sul diedro fallirebbe sempre, oppure sarebbe tarato
  per passare -- che e' di nuovo la soglia decisa dopo.
- `parametro` -- non e' un limite ma un valore di riferimento o un coefficiente
  di metodo, tenuto qui perche' anche lui deve portare la propria fonte.

**Cosa non sta qui.** Il vincolo raggio-spigolo di TetGen (`min_ratio`) e' un
parametro di **elaborazione**, non di verifica: il suo valore vive in
`core/config.py` e li' resta. Duplicarlo qui creerebbe la seconda copia che
questo modulo esiste per evitare.

**Stato.** Questo modulo e' il registro, cioe' la meta' che *dichiara*. La meta'
che *applica* -- i benchmark che confrontano un risultato contro queste soglie
-- non esiste ancora e arriva con i ticket #46, #47 e #48. Finche' non arriva,
`SOGLIE` non ha chiamanti fuori dai propri test, e nessun cancello boccia
davvero alcunche'.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Literal, NamedTuple

Tipo = Literal["cancello", "etichetta", "parametro"]
Origine = Literal["letta", "derivata", "nostra"]


class Soglia(NamedTuple):
    """Un limite, con l'autorita' che lo giustifica e l'origine del proprio valore.

    `minimo` e `massimo` sono entrambi opzionali ma non entrambi assenti: una
    soglia che non delimita nulla e' una guardia inerte, e il registro la
    rifiuta. Quando coincidono, la soglia e' un valore di riferimento e non un
    intervallo.

    Il tipo resta permissivo su `fonte` -- una stringa vuota e' costruibile --
    perche' vincolarlo renderebbe impossibile fabbricare una `Soglia` nei test.
    I controlli vivono sul registro, dove servono.
    """

    nome: str
    minimo: float | None
    massimo: float | None
    unita: str
    tipo: Tipo
    origine: Origine
    fonte: str
    fissata: date
    nota: str = ""


RATIFICA = date(2026, 8, 26)

# sqrt(2)/2: l'estremo superiore del range Verdict per lo scaled Jacobian
# tetraedrico. Scritto una volta e riusato perche' e' esattamente il numero che
# si sbaglia copiando il range dell'esaedro, che arriva a 1.
_RADICE_DI_DUE_MEZZI = 2**0.5 / 2

# I bound in forma chiusa si stampano come tali: sei cifre decimali
# asserirebbero una precisione che il bound non ha.
_SIMBOLI: dict[float, str] = {_RADICE_DI_DUE_MEZZI: "sqrt(2)/2 ~ 0,7071"}

_VERDICT = (
    "Stimpson, Ernst, Knupp, Pébay & Thompson (2007), "
    "The Verdict Geometric Quality Library, SAND2007-1751, §6"
)


SOGLIE: tuple[Soglia, ...] = (
    # --- cancelli: bocciano ---
    Soglia(
        nome="patch_test_relativo",
        minimo=None,
        massimo=1e-8,
        unita="adim.",
        tipo="cancello",
        origine="nostra",
        fonte="Taylor, Simo, Zienkiewicz & Chan (1986), IJNME 22:39-62, DOI 10.1002/nme.1620220105",
        fissata=RATIFICA,
        nota=(
            "La fonte dimostra che il patch test è esatto per costruzione, non fissa "
            "una tolleranza: il valore è nostro e copre l'errore di macchina più il "
            "condizionamento del solutore."
        ),
    ),
    Soglia(
        nome="mensola_fattore_su_benzley",
        minimo=None,
        massimo=2.0,
        unita="adim.",
        tipo="cancello",
        origine="nostra",
        fonte=(
            "Benzley, Perry, Merkley, Clark & Sjaardema (1995), "
            "4th International Meshing Roundtable, pp. 179-191, Tab. 2"
        ),
        fissata=RATIFICA,
        nota=(
            "Benzley pubblica gli errori dell'elemento (31,48% sullo spostamento, "
            "21,23% sulla tensione a 666 gradi di libertà), non un fattore di "
            "tolleranza: il 2,0 è nostro. Non misura l'elemento, che è già noto per "
            "essere troppo rigido, ma quanto errore aggiunge la nostra catena oltre "
            "quello pubblicato, a pari gradi di libertà."
        ),
    ),
    Soglia(
        nome="le10_c3d10_errore",
        minimo=None,
        massimo=7.24,
        unita="% su -5,38 MPa",
        tipo="cancello",
        origine="letta",
        fonte="Abaqus Benchmarks Guide, LE10, tabella di errore per tipo di elemento",
        fissata=RATIFICA,
        nota=(
            "Abaqus pubblica per C3D10 una banda da 1,15% a 7,24%: si sbarra solo "
            "l'estremo peggiore, perché essere più accurati di Abaqus non è un "
            "difetto. L'errore su questo benchmark peggiora raffinando -- nella mesh "
            "fine un solo elemento converge nel punto di lettura invece di quattro -- "
            "quindi un criterio della forma «l'errore cala raffinando» qui sarebbe falso."
        ),
    ),
    Soglia(
        nome="modi_rigidi_numero",
        minimo=6.0,
        massimo=6.0,
        unita="-",
        tipo="cancello",
        origine="letta",
        fonte="Dhondt, CalculiX 2.22 manual, §6.9; Benzley et al. (1995), Tab. 1",
        fissata=RATIFICA,
        nota=(
            "Tre traslazioni e tre rotazioni. Un settimo autovalore nullo, o uno "
            "mancante, è un difetto del deck e non del solutore."
        ),
    ),
    Soglia(
        nome="modi_rigidi_rapporto",
        minimo=None,
        massimo=1e-3,
        unita="adim.",
        tipo="cancello",
        origine="nostra",
        fonte="Bathe, Finite Element Procedures, §10.2 (proprietà di limite superiore degli autovalori)",
        fissata=RATIFICA,
        nota=(
            "La fonte sostiene che gli autovalori rigidi sono nulli, non quanto "
            "possano discostarsene in aritmetica finita: il valore è nostro, per "
            "analogia con la tolleranza di datcheck. Rapporto fra la frequenza del "
            "modo rigido e la prima frequenza propria."
        ),
    ),
    Soglia(
        nome="massa_efficace_relativo",
        minimo=None,
        massimo=1e-6,
        unita="adim.",
        tipo="cancello",
        origine="nostra",
        fonte="Dhondt, CalculiX 2.22 manual, §6.9 (massa efficace totale nel file .dat)",
        fissata=RATIFICA,
        nota=(
            "La fonte dice dove leggere la massa efficace, non quanto possa "
            "discostarsi: il valore è nostro. È un'identità aritmetica contro ρ·V, "
            "quindi stretta è giusto, e allentarla nasconderebbe un errore di unità "
            "invece di tollerarlo."
        ),
    ),
    Soglia(
        nome="incrociato_calculix_abaqus",
        minimo=None,
        massimo=1e-3,
        unita="adim.",
        tipo="cancello",
        origine="letta",
        fonte="Dhondt, suite di verifica ufficiale CalculiX 2.22, datcheck.pl",
        fissata=RATIFICA,
        nota=(
            "Soglia numerica letta in `datcheck.pl`, la suite con cui l'autore di "
            "CalculiX verifica il proprio codice. Relativa al massimo del blocco, "
            "non al valore puntuale."
        ),
    ),
    Soglia(
        nome="errore_geometrico_max",
        minimo=None,
        massimo=5.0,
        unita="mm",
        tipo="cancello",
        origine="derivata",
        fonte=(
            "Historic England, 3D Laser Scanning for Heritage (3a ed.), Boardman & Bryan "
            "-- pratica della soglia dichiarata prima, non il valore"
        ),
        fissata=RATIFICA,
        nota=(
            "Metà del voxel della corsa di riferimento, 10 mm: sotto, la ricostruzione "
            "non risolve e la soglia dichiarerebbe una precisione che il dato non ha. "
            "Fissata dopo che l'errore era già stato misurato nelle Fasi 1 e 5: per "
            "questa sola famiglia «dichiarata prima» non è vero, ed è più debole delle "
            "altre. Il capitolo lo deve dire."
        ),
    ),
    # --- etichette: contano e riportano. TetGen non garantisce il diedro ---
    Soglia(
        nome="diedro_minimo_tet",
        minimo=40.0,
        massimo=70.5288,
        unita="gradi",
        tipo="etichetta",
        origine="letta",
        fonte=f"{_VERDICT}, minimum dihedral angle",
        fissata=RATIFICA,
        nota=(
            "L'unica metrica del set che vede gli sliver: il radius-edge è cieco a "
            "quelli per costruzione. Il massimo è il valore del tetraedro regolare, "
            "arccos(1/3)."
        ),
    ),
    Soglia(
        nome="aspect_ratio_tet",
        minimo=1.0,
        massimo=3.0,
        unita="adim.",
        tipo="etichetta",
        origine="letta",
        fonte=f"{_VERDICT}, aspect ratio",
        fissata=RATIFICA,
        nota=(
            "Definizione Verdict, spigolo massimo diviso 2*sqrt(6)*raggio inscritto, "
            "ed è quella che `core/quality.py` implementa. Abaqus e CAE chiamano "
            "«aspect ratio» un'altra grandezza, il rapporto fra spigolo massimo e "
            "minimo: citare una soglia da manuale senza dire quale definizione è "
            "confronterebbe due cose diverse."
        ),
    ),
    Soglia(
        nome="scaled_jacobian_tet",
        minimo=0.5,
        massimo=_RADICE_DI_DUE_MEZZI,
        unita="adim.",
        tipo="etichetta",
        origine="letta",
        fonte=f"{_VERDICT}, scaled Jacobian",
        fissata=RATIFICA,
        nota=(
            "L'estremo superiore è sqrt(2)/2, non 1: quello a 1 è dell'esaedro, e "
            "copiarlo accetterebbe come buoni tetraedri che Verdict rifiuta. "
            "Oggi nessuna grandezza del programma la produce: `core/quality.py` "
            "calcola lo scaled Jacobian per i soli esaedri. La voce sta qui perché è "
            "il range da usare quando la si calcolerà, non perché sia già misurata."
        ),
    ),
    # --- parametri: riferimenti e coefficienti di metodo, non limiti ---
    Soglia(
        nome="gci_fattore_sicurezza",
        minimo=1.25,
        massimo=1.25,
        unita="adim.",
        tipo="parametro",
        origine="letta",
        fonte=(
            "Roache (1994), Journal of Fluids Engineering 116(3):405-413, "
            "DOI 10.1115/1.2910291; formulazione del fattore verbatim da NASA NPARC"
        ),
        fissata=RATIFICA,
        nota="Vale da tre griglie in su. Con due sole griglie il fattore sale a 3,0.",
    ),
    Soglia(
        nome="le10_riferimento",
        minimo=-5.38,
        massimo=-5.38,
        unita="MPa",
        tipo="parametro",
        origine="letta",
        fonte=(
            "NAFEMS LSB2, Test LE10 (1990), sigma_yy nel punto D (2; 0; 0,6) sulla "
            "superficie superiore caricata; Abaqus lo attribuisce a TNSB Rev. 3"
        ),
        fissata=RATIFICA,
        nota=(
            "Target numerico, qualificato «mesh refinement» dalla scheda NAFEMS: non "
            "è una soluzione in forma chiusa, quindi nessuna soglia costruita su di "
            "esso può essere più stretta della sua stessa incertezza. La superficie "
            "va detta: sulla faccia inferiore si legge un altro numero."
        ),
    ),
    Soglia(
        nome="fv52_prima_frequenza",
        minimo=44.092,
        massimo=44.092,
        unita="Hz",
        tipo="parametro",
        origine="letta",
        fonte=(
            "Abaqus Benchmarks Guide, FV52 -- set numerico; l'attribuzione dei due "
            "set a NAFEMS R0015 resta non verificata sul documento originale"
        ),
        fissata=RATIFICA,
        nota=(
            "NAFEMS pubblica anche il set in forma chiusa, 45,897 Hz, e i due non "
            "vanno mescolati: le tabelle di errore per tipo di elemento sono tarate "
            "su questo. Oltre il modo 7 l'ordine degli autovalori cambia fra tipi di "
            "elemento, quindi si appaia per forma modale e non per indice."
        ),
    ),
)


def trova(nome: str) -> Soglia:
    """La soglia che porta questo nome.

    Solleva invece di rendere `None`: un chiamante che confronta contro `None`
    otterrebbe un verdetto sempre falso, cioe' una guardia inerte al posto di
    un errore.
    """
    for soglia in SOGLIE:
        if soglia.nome == nome:
            return soglia
    raise KeyError(f"soglia sconosciuta: {nome}")


def sotto_la_risoluzione(soglia_mm: float | None, voxel_mm: float) -> bool:
    """La soglia pretende piu' precisione di quanta la ricostruzione ne abbia.

    Principio 3 di `PRODUCT.md`: non fabbricare precisione che non esiste. Il
    pavimento e' meta' del voxel, perche' sotto quella distanza la superficie
    ricostruita non porta informazione -- il campionamento che l'ha generata
    non ce l'ha.

    Non e' una costante ma una funzione della corsa: `config.py:133` lascia
    `voxel_size` a `None`, cioe' due volte la spaziatura media, quindi il
    pavimento cambia con la nuvola. Una soglia piu' larga del pavimento e'
    prudente e lecita; una piu' stretta e' una promessa che il dato non
    mantiene. Esattamente meta' del voxel passa: e' il pavimento, non un valore
    gia' sotto di esso.

    `soglia_mm` accetta `None` per rifiutarlo: il chiamante naturale e'
    `sotto_la_risoluzione(soglia.massimo, voxel)`, e `Soglia.massimo` e'
    opzionale. Lasciar propagare un `TypeError` da `math.isfinite` direbbe al
    chiamante che ha sbagliato tipo, non che ha passato una soglia senza
    estremo superiore.
    """
    if not math.isfinite(voxel_mm) or voxel_mm <= 0.0:
        raise ValueError(
            f"voxel non positivo o non finito ({voxel_mm}): nessun pavimento di "
            "risoluzione è calcolabile"
        )
    if soglia_mm is None:
        raise ValueError("soglia senza estremo superiore: non è confrontabile con un pavimento")
    if not math.isfinite(soglia_mm):
        raise ValueError(f"soglia non finita ({soglia_mm}): non è confrontabile")
    return soglia_mm < voxel_mm / 2.0


_APICI = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _numero(valore: float) -> str:
    """Un valore come lo vuole un'appendice italiana.

    Tre regole, tutte nate da un rilievo di review sulla prima stesura: i bound
    in forma chiusa restano simbolici (sei decimali di `sqrt(2)/2` asserirebbero
    una precisione che il bound non ha); le potenze di dieci si scrivono tutte
    allo stesso modo (`:g` da solo rendeva `1e-08`, `1e-06` e `0.001`, tre
    grafie per tre tolleranze sorelle); e il separatore decimale e' la virgola,
    perche' la prosa intorno alla tabella scrive gia' all'italiana.
    """
    if valore in _SIMBOLI:
        return _SIMBOLI[valore]
    if valore > 0:
        esponente = math.log10(valore)
        arrotondato = round(esponente)
        if abs(esponente - arrotondato) < 1e-12 and arrotondato <= -3:
            return "10" + str(int(arrotondato)).translate(_APICI)
    return f"{valore:g}".replace(".", ",")


def _intervallo(soglia: Soglia) -> str:
    if soglia.minimo is not None and soglia.massimo is not None:
        if soglia.minimo == soglia.massimo:
            return f"= {_numero(soglia.minimo)}"
        return f"da {_numero(soglia.minimo)} a {_numero(soglia.massimo)}"
    if soglia.massimo is not None:
        return f"<= {_numero(soglia.massimo)}"
    if soglia.minimo is not None:
        return f">= {_numero(soglia.minimo)}"
    # Raggiungibile: `tabella_markdown` e' pubblica e accetta una tupla
    # arbitraria, che il registro non ha filtrato. Il registro suo proprio non
    # puo' contenere una soglia senza estremi -- `test_soglie` la rifiuta.
    return "nessun limite"


def _senza_barre(testo: str) -> str:
    """Una barra verticale in un campo spaccherebbe la riga della tabella.

    Difetto trovato in review sulla prima stesura: una fonte che contiene `|`
    produceva sette colonne invece di sei, e il test che conta le righe restava
    verde perche' contava righe, non colonne.
    """
    return testo.replace("|", "\\|")


def tabella_markdown(soglie: tuple[Soglia, ...] = SOGLIE) -> str:
    """La tabella che finisce nel documento di fase e nel capitolo.

    Generata e non ricopiata: due copie dello stesso numero sono due posti dove
    divergere, e la copia nel testo e' quella che nessun test guarda.

    Porta con se' legenda e note. Senza legenda un lettore dell'appendice non
    puo' sapere che un'etichetta fuori range non ferma nulla; senza le note
    resta «<= 7,24 | cancello» senza il motivo, e il motivo e' l'unica cosa che
    rende la tabella difendibile in discussione.
    """
    righe = [
        "| soglia | intervallo | unità | classe | origine | riferimento |",
        "|---|---|---|---|---|---|",
    ]
    righe += [
        "| `{}` | {} | {} | {} | {} | {} |".format(
            _senza_barre(s.nome),
            _senza_barre(_intervallo(s)),
            _senza_barre(s.unita),
            s.tipo,
            s.origine,
            _senza_barre(s.fonte),
        )
        for s in soglie
    ]

    legenda = [
        "",
        "**Classe.** `cancello` boccia il risultato fuori intervallo; `etichetta` conta e "
        "riporta senza bocciare; `parametro` è un valore di riferimento o un coefficiente "
        "di metodo, non un limite.",
        "",
        "**Origine.** `letta` = il numero è pubblicato nel riferimento; `derivata` = "
        "calcolato da un fatto del riferimento; `nostra` = scelto da noi, perché il "
        "riferimento non pubblica un valore. Il riferimento resta la fonte del confronto, "
        "anche quando il numero non viene da lì.",
        "",
        f"I nomi sono le chiavi del registro `core/soglie.py`. Tutte ratificate il "
        f"{RATIFICA:%d/%m/%Y}.",
    ]

    note = [linea for s in soglie if s.nota for linea in ("", f"- `{s.nome}` — {s.nota}")]
    if note:
        note = ["", "**Note.**", *note]

    return "\n".join([*righe, *legenda, *note])
