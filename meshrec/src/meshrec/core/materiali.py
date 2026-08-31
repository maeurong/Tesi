"""Il catalogo dei materiali di norma: ogni voce con la fonte, l'origine del valore e la data.

Unico luogo dove una classe di calcestruzzo o di acciaio ha i propri numeri,
come `core/soglie.py` lo e' per le soglie di verifica e `core/config.py` per i
parametri di elaborazione. **La forma e' quella di `soglie.py` e non una forma
nuova**: chi ha imparato a leggere quel registro sa gia' leggere questo.

I numeri e i loro articoli vengono da
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md`, che li ha letti
sul testo di norma convertito e ne ha verificato l'oracolo per tre vie
indipendenti.

**`fonte` e `origine` sono cose diverse**, ed e' la lezione che `soglie.py` ha
pagato una volta: la fonte e' l'autorita' contro cui il numero si giustifica,
l'origine dice se il numero **sta** in quell'autorita' (`letta`), se si
**calcola** da un suo fatto (`derivata`), o se e' **nostro** (`nostra`), scelto
dove la fonte non pubblica un valore o ne pubblica due che divergono. Una voce
`nostra` senza nota viene rifiutata dai test.

**Una voce porta piu' numeri e una sola `origine`, e la regola e' che vince il
piu' debole.** Per il calcestruzzo l'origine e' `derivata`: la Tab. 4.1.I porta i
**nomi** delle classi e nessun valore, e `f_cm` ed `E_cm` si calcolano dalle
espressioni del §11.2.10. **Ma non tutte le sue grandezze lo sono**: il
§11.2.10.4 pubblica due coefficienti di Poisson e la Tab. 3.1.I due densita', e
prendere l'estremo alto di entrambi e' una scelta per la regola scritta qui
sopra. L'etichetta resta `derivata` perche' la resistenza -- la grandezza
principale della riga -- lo e' davvero, e chiamare `nostra` l'intera voce direbbe
un'altra cosa falsa; le due scelte stanno percio' nella `nota` di ogni classe,
che e' cio' per cui la forma di `soglie.py` esiste. Per l'acciaio `f_yk` e la densita'
sono lette in Tab. 11.3.Ia e nel §11.3.2.4, ma `E_s` e il coefficiente di
Poisson non stanno nelle NTC: la voce e' percio' `nostra`, e la nota dice quali
numeri lo sono e perche'. Marcare `letta` una riga che contiene una scelta
direbbe una cosa falsa sulla propria provenienza.

**Il catalogo parte dal nome della classe, non da `R_ck`.** «C25/30» e' la
coppia normalizzata `f_ck`/`R_ck` di UNI EN 206: `f_ck` vale 25 per definizione.
L'espressione `[11.2.1]`, `f_ck = 0,83 · R_ck`, e' un'altra strada con un altro
scopo -- si parte da un `R_ck` prescritto in capitolato o misurato su cubetti --
e le due non coincidono: sulla C35/45 lo scarto e' del 6,7%. Un catalogo che
facesse le due cose in silenzio produrrebbe due `f_cd` diversi per lo stesso
calcestruzzo, quindi qui ne fa una sola e la dichiara. Chi ha un `R_ck` applica
la `[11.2.1]` prima di entrare, e lo scrive.

**`alpha_cc` non e' facoltativo.** La `[4.1.3]` e' `f_cd = alpha_cc · f_ck /
gamma_c` con `alpha_cc` = 0,85: il coefficiente di lunga durata sta dentro la
formula di norma, ha un nome e un valore fissato. Chi scrive `f_ck / 1,5`
ottiene un valore del 17,6% piu' alto del vero, dalla parte insicura.

**Le sei riduzioni ulteriori della norma non sono applicate qui**, e non e' una
dimenticanza: nessuna delle sei e' decidibile da una riga di catalogo, perche'
ognuna dipende da un fatto che la riga non porta -- lo spessore e il modo di
getto dell'elemento (§4.1.2.1.1.1, 0,80 sugli elementi piani sotto i 50 mm), il
regime di produzione (`gamma_c` da 1,5 a 1,4, §4.1.2.1.1.1), l'essere la sezione
armata o no (§4.1.11.1, 0,85 su `f_ctd`), il tipo di aggregato (§11.2.10.2-3,
-10% su `f_ctm` e -20% su `E_cm` con aggregati di riciclo), una misura in opera
(§11.2.6, la soglia dell'85%), il livello di conoscenza di una costruzione
esistente (Circolare Tab. C8.5.IV, i fattori di confidenza). Quando serviranno
entreranno come **argomenti espliciti** di `valori_di_progetto`, mai come
predefiniti silenziosi: un fattore applicato di nascosto e' indistinguibile da
un fattore dimenticato.

**Il catalogo copre i calcestruzzi ordinari, e nient'altro.** E' la definizione
della riga 2124 delle NTC: ordinari sono quelli «conformi al presente § 4.1 ed
al § 11.2, con esclusione dei calcestruzzi di aggregati leggeri (LC), di cui al
§4.1.12, e di quelli fibrorinforzati (FRC), di cui al §11.2.12». Il §4.1.12
ammette gli LC fino alla LC55/60 e l'§11.2.12 gli FRC: nessuno dei due sta qui,
e chi ne cerca uno riceve il rifiuto di `trova`. Il campo e' ristretto per
scelta, ma un campo ristretto e non dichiarato si scopre solo a valle.

**Il catalogo non e' un cancello.** `runs/muro` usa una muratura a 1500 MPa che
nessuna tabella NTC 2018 contiene, e un catalogo che rifiutasse cio' che non
elenca renderebbe irripetibile una corsa di riferimento. Qui non c'e' nulla che
obblighi un chiamante a passare da `trova`: il catalogo e' la tabella di norma
per chi la vuole, non il solo modo di dichiarare un materiale.

**Perche' `f_ctm` sta qui, e le altre della cascata no.** La regola per entrare
e' avere un chiamante: fissare la forma di una grandezza prima di sapere chi la
usa vuol dire indovinarla. `f_ctm` un chiamante ce l'ha -- l'armatura minima a
flessione, `A_s,min = 0,26 · (f_ctm / f_yk) · b_t · d`, NTC §4.1.6.1.1
espressione `[4.1.45]`, dove la norma stessa rimanda al §11.2.10.2 per la
definizione di `f_ctm` -- e finche' il catalogo non la portava quel calcolo se
la faceva passare dall'esterno, cioe' teneva un numero di norma fuori dal solo
luogo che li tiene. Le altre -- `f_cm`, i due frattili `f_ctk` 5% e 95%,
`f_cfm`, `epsilon_c2`, `epsilon_cu` -- restano fuori per la stessa regola, che
per loro dice ancora di no: stanno tutte, con i loro articoli, nella ricerca
citata sopra. Nemmeno `f_ctd` e' qui, e quando servira' non sara' un campo: e'
una resistenza di **progetto**, `f_ctk / gamma_c` per la `[4.1.4]`, quindi
appartiene all'uscita di `valori_di_progetto` accanto a `f_cd`, dove sta gia' la
regola che i valori di progetto non si tengono come dato. Il copriferro per
classe di esposizione non e' un dato di materiale: vive in
`config.ArmaturaConfig`.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Literal, NamedTuple

Famiglia = Literal["calcestruzzo", "acciaio"]
Origine = Literal["letta", "derivata", "nostra"]


class VoceMateriale(NamedTuple):
    """Un materiale di norma, con l'autorita' che lo giustifica e l'origine dei propri numeri.

    `f_k` e' **sempre caratteristico** -- `f_ck` per il calcestruzzo, `f_yk` per
    l'acciaio -- e i valori di progetto si ottengono da `valori_di_progetto`.
    Tenere qui un valore gia' ridotto renderebbe impossibile distinguerlo da un
    caratteristico, e i coefficienti parziali verrebbero applicati due volte.

    Il tipo resta permissivo su `fonte` e su `f_k` -- una stringa vuota e uno
    zero sono costruibili -- perche' vincolarli renderebbe impossibile
    fabbricare una voce nei test. I controlli vivono sul registro e
    sull'ingresso di `valori_di_progetto`, dove servono.

    `f_ctm` e' l'unico campo che non vale per tutte e due le famiglie: e' la
    resistenza media a trazione **del calcestruzzo**, e sull'acciaio vale
    `None`. Non zero: uno zero entrerebbe nella `[4.1.45]` come un numero e
    renderebbe un'armatura minima nulla in silenzio, mentre `None` fa fallire il
    conto nel punto in cui la grandezza e' stata chiesta al materiale sbagliato.

    `nota` e `avvertenze` non sono due nomi per la stessa cosa. La `nota` e' la
    provenienza per intero -- la difesa dei numeri scelti, uguale per ogni
    classe, piu' le condizioni d'uso di quella classe -- e la legge chi legge il
    catalogo. `avvertenze` porta le sole condizioni d'uso, una per voce
    dell'elenco, e serve a chi ne sceglie una sola: sotto un menu' la difesa dei
    numeri e' mille caratteri fra chi sceglie e cio' che deve sapere. Le
    avvertenze restano dentro la nota, quindi il campo nuovo non sottrae niente
    a nessuno.
    """

    classe: str
    famiglia: Famiglia
    young: float
    poisson: float
    density: float
    f_k: float
    fonte: str
    origine: Origine
    fissata: date
    nota: str = ""
    f_ctm: float | None = None
    avvertenze: tuple[str, ...] = ()


FISSATA = date(2026, 8, 30)

# NTC 2018 §4.1.2.1.1.1, espressione [4.1.3], e §4.1.2.1.1.3, espressione
# [4.1.5]. La Circolare avverte che gamma_c e' quello europeo e alpha_cc no:
# «il coefficiente alpha_cc resta fissato a 0,85, a differenza di quello
# proposto dalla UNI EN 1992». Chi volesse una modalita' Eurocodice cambierebbe
# ALFA_CC e non GAMMA_C.
ALFA_CC = 0.85
GAMMA_C = 1.5
GAMMA_S = 1.15

# La Tab. 4.1.I (riga 2126 delle NTC) elenca **quindici** classi. C28/35 e
# C32/40 le ammette la frase che la segue, riga 2128, e la loro fonte deve dirlo:
# la `nota` lo dichiarava gia', ma la `fonte` e' il campo che i test sorvegliano.
_FONTE_CLASSI_IN_TABELLA = "NTC 2018 §4.1, Tab. 4.1.I (elenco delle classi)"

_FONTE_CLASSI_IN_USO = (
    "NTC 2018 §4.1, la frase che segue la Tab. 4.1.I: le classi «già in uso» C28/35 e "
    "C32/40, che la tabella non elenca"
)

_FONTE_GRANDEZZE_CALCESTRUZZO = (
    "§11.2.10.1 e §11.2.10.3, espressioni [11.2.2] e [11.2.5]; §11.2.10.2, espressioni "
    "[11.2.3a] e [11.2.3b] (resistenza media a trazione); §11.2.10.4 (Poisson); "
    "§3.1.2, Tab. 3.1.I (peso dell'unità di volume)"
)

_FONTE_ACCIAIO = (
    "NTC 2018 §11.3.2.1 e §11.3.2.2, Tab. 11.3.Ia (f_y nom = 450 N/mm²); "
    "§11.3.2.4 (densità 7,85 kg/dm³)"
)

# Tab. 3.1.I da' 25,0 kN/m³ per il calcestruzzo armato e 24,0 per l'ordinario.
# Il catalogo porta il primo, perche' le sezioni che serve sono armate:
# 25,0e3 / 9,80665 = 2549,3 kg/m³, cioe' 2,5493e-9 t/mm³. Non e' il 2,5e-9 di
# prassi che le corse del progetto usano, che vale 24,52 kN/m³.
#
# **Due incoerenze note, entrambe dichiarate qui e nella nota di ogni classe.**
# La prima: le corse di riferimento girano con 2,5e-9, cioe' l'1,972% in meno
# sul peso proprio. La seconda: la conversione qui sopra usa g = 9,80665 m/s²,
# ma le corse girano con `gravity: 9810` mm/s² (`casi/lab.yaml`), e con quel
# valore 2,5493e-9 rende 25,009 kN/m³ invece di 25,000 -- lo 0,03%, trascurabile
# in se', ma e' una seconda incoerenza e va nominata invece che subita.
_DENSITA_CALCESTRUZZO = 2.5493e-9

# 7,85 kg/dm³, cioe' 7850 kg/m³, letto verbatim nel §11.3.2.4.
_DENSITA_ACCIAIO = 7.85e-9

_POISSON_CALCESTRUZZO = 0.2

# Le NTC non pubblicano il coefficiente di Poisson dell'acciaio da armatura, e
# la ricerca in `docs/validazione/` non lo porta: 0,3 e' il valore corrente,
# aggiunto qui e dichiarato nella nota delle due voci.
_POISSON_ACCIAIO = 0.3

# I **quindici** nomi della Tab. 4.1.I piu' le **due** che la frase seguente
# ammette in via residuale: diciassette in tutto. Il numero in tupla era gia'
# giusto, la provenienza scritta qui no. Il catalogo tiene i **nomi** e ricalcola il resto:
# ricopiare la tabella di valori della ricerca creerebbe la seconda copia che
# questo modulo esiste per evitare.
_CLASSI_CALCESTRUZZO = (
    "C8/10",
    "C12/15",
    "C16/20",
    "C20/25",
    "C25/30",
    "C28/35",
    "C30/37",
    "C32/40",
    "C35/45",
    "C40/50",
    "C45/55",
    "C50/60",
    "C55/67",
    "C60/75",
    "C70/85",
    "C80/95",
    "C90/105",
)

_IN_USO = ("C28/35", "C32/40")


def _fonte_di_classe(classe: str) -> str:
    """L'autorita' che elenca **questa** classe, piu' quelle delle sue grandezze."""
    elenco = _FONTE_CLASSI_IN_USO if classe in _IN_USO else _FONTE_CLASSI_IN_TABELLA
    return f"{elenco}; {_FONTE_GRANDEZZE_CALCESTRUZZO}"


def _f_ck_dal_nome(classe: str) -> float:
    """Il primo numero della coppia normalizzata, che **e'** `f_ck`."""
    return float(classe[1:].split("/")[0])


def _modulo_elastico(f_ck: float) -> float:
    """`E_cm` dall'espressione [11.2.5], modulo secante fra 0 e 0,40 `f_cm`.

    `22000 · (f_cm/10)^0,3` con `f_cm = f_ck + 8` dalla `[11.2.2]`. La stessa
    formula di UNI EN 1992-1-1 Tab. 3.1, scritta li' in GPa e qui in MPa.
    """
    return 22000.0 * ((f_ck + 8.0) / 10.0) ** 0.3


# Il confine fra le due espressioni della [11.2.3]: la C50/60 sta **dentro** il
# campo della [11.2.3a], che vale «per classi <= C50/60».
_F_CK_LIMITE_TRAZIONE = 50.0


def _resistenza_a_trazione_media(f_ck: float) -> float:
    """`f_ctm` dal §11.2.10.2, che ha **due** espressioni e non una.

        f_ctm = 0,30 · f_ck^(2/3)         per classi <= C50/60   [11.2.3a]
        f_ctm = 2,12 · ln(1 + f_cm/10)    per classi >  C50/60   [11.2.3b]

    Estendere la `[11.2.3a]` sopra il suo campo sbaglierebbe dalla parte
    insicura per l'armatura minima, che le e' proporzionale: sulla C55/67
    darebbe 4,339 MPa contro i 4,214 della `[11.2.3b]`, il 2,9% in piu'. Il
    salto e' nella norma, non nel conto.
    """
    if f_ck <= _F_CK_LIMITE_TRAZIONE:
        return 0.30 * f_ck ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + (f_ck + 8.0) / 10.0)


# Le due grandezze del calcestruzzo di cui la norma pubblica **due** valori
# possibili. Per il criterio che il docstring di questo modulo enuncia sono
# scelte, non derivazioni, e vanno dette accanto alla riga: l'`origine` resta
# `derivata` perche' la resistenza -- la grandezza principale della voce -- lo e'
# davvero, e cambiare l'etichetta dell'intera voce direbbe un'altra cosa falsa.
_NOTA_SCELTE_CALCESTRUZZO = (
    "Due numeri di questa riga sono **scelti** fra due che la norma pubblica entrambi. "
    "**Poisson**: il §11.2.10.4 ammette «un valore compreso tra 0 (calcestruzzo "
    "fessurato) e 0,2 (calcestruzzo non fessurato)», che sono due modelli e non un "
    "intervallo di incertezza; qui vale 0,2, perché l'analisi è elastica lineare su "
    "sezione non fessurata. **Densità**: la Tab. 3.1.I pubblica 24,0 kN/m³ per il "
    "calcestruzzo ordinario e 25,0 per l'armato; qui vale 25,0, cioè 2,5493e-9 t/mm³, "
    "perché le sezioni che questo catalogo serve sono armate. Le corse di riferimento "
    "del progetto girano invece con 2,5e-9 t/mm³: l'1,972% in meno sul peso proprio, ed "
    "è la ragione per cui un risultato nuovo non torna cifra per cifra con uno vecchio. "
    "Le corse usano anche «gravity: 9810» mm/s² invece di 9,80665 m/s², con cui il "
    "2,5493e-9 rende 25,009 kN/m³ e non 25,000: lo 0,03%."
)


def _avvertenze_di_classe(classe: str, f_ck: float) -> tuple[str, ...]:
    """I vincoli d'uso che la classe si porta dietro, uno per frase.

    Ogni classe del catalogo e' ammessa dalle NTC, ma alcune di esse lo sono
    **a condizioni**, e la condizione va accanto alla riga: altrove nessuno la
    leggerebbe. Qui stanno le sole condizioni, senza le due scelte che la norma
    lascia aperte: quelle valgono per ogni classe, quindi chi ne ha scelta una
    non le sta leggendo per la propria: le legge per il catalogo, ed e'
    `_nota_di_classe` a comporre le due cose per chi legge il catalogo.

    Una classe senza condizioni rende la tupla vuota, non una stringa vuota:
    a video la seconda diventa un separatore appeso sopra il nulla.
    """
    frasi: list[str] = []
    if classe == "C8/10":
        frasi.append(
            "Il modulo elastico è un'estrapolazione: la classe sta nelle NTC ma non nella "
            "Tabella 3.1 di UNI EN 1992-1-1, da cui la [11.2.5] proviene."
        )
    if f_ck < 16.0:
        frasi.append(
            "Sotto la classe minima per le strutture semplicemente armate, che la "
            "Tab. 4.1.II fissa a C16/20."
        )
    if classe in _IN_USO:
        frasi.append(
            "Classe ammessa in via residuale, «già in uso»: non compare in Tab. 4.1.I ma "
            "nella frase che la segue. La Circolare 7/2019, nel commento al §4.1 delle NTC, "
            "la ammette ai soli fini della durabilità dove sono prescritte le classi "
            "immediatamente inferiori."
        )
    if f_ck > _F_CK_LIMITE_TRAZIONE:
        frasi.append(
            "La resistenza media a trazione di questa riga viene dalla [11.2.3b], "
            "«2,12 · ln [1+fcm/10] per classi > C50/60», e non dalla [11.2.3a] delle altre "
            "dodici: oltre la C50/60 la norma cambia forma, e la f_ctm smette di crescere "
            "come f_ck^(2/3). Dalla C50/60 alla C90/105 la resistenza a compressione quasi "
            "raddoppia e quella a trazione sale del 24%."
        )
    if f_ck > 45.0:
        frasi.append("Oltre la C45/55 le NTC chiedono «un'apposita sperimentazione preventiva».")
    if f_ck > 70.0:
        frasi.append(
            "Oltre la C70/85 le NTC «rinviano al caso C) del §11.1», che chiede un "
            "«Certificato di Valutazione Tecnica» del Presidente del Consiglio Superiore "
            "dei Lavori Pubblici, previa istruttoria del Servizio Tecnico Centrale. La "
            "Circolare 7/2019, §CC4.1, chiama la stessa procedura «autorizzazione "
            "ministeriale»: le parole sono sue, non delle NTC."
        )
    return tuple(frasi)


def _nota_di_classe(classe: str, f_ck: float) -> str:
    """La provenienza per intero: la difesa dei numeri, poi le avvertenze.

    E' cio' che il catalogo pubblica per la riga, e va letto per intero da chi
    legge il catalogo. Chi sceglie una sola classe legge invece `avvertenze`.
    """
    return " ".join((_NOTA_SCELTE_CALCESTRUZZO, *_avvertenze_di_classe(classe, f_ck)))


_NOTA_ACCIAIO = (
    "Due numeri di questa riga non stanno nelle NTC, ed è la ragione per cui l'origine è "
    "«nostra». **Il modulo elastico**: la Circolare 7/2019 §C4.1.2.2.5 dà 210.000 N/mm², "
    "ma in un paragrafo sulle tensioni in esercizio, «Stato Limite di limitazione delle "
    "tensioni»; UNI EN 1992-1-1 §3.2.7(4) dà 200.000, "
    "ed è il valore con cui l'oracolo di collaudo del progetto torna — con 210.000 il "
    "rapporto della sezione bilanciata passa da 0,6414 a 0,6526. Qui si scrive 200.000 e la "
    "divergenza resta dichiarata invece che sciolta. **Il coefficiente di Poisson**: le NTC "
    "non lo pubblicano per l'acciaio da armatura, e 0,3 è il valore corrente, aggiunto da noi."
)

# Le due voci d'acciaio non passano da `_avvertenze_di_classe` -- il loro
# vincolo d'uso non si deduce da una resistenza, sta scritto in un articolo per
# ciascuna -- ma la nota ha la stessa forma delle altre: il preambolo comune,
# poi cio' che vale per quella sola classe. Le frasi proprie stanno qui perche'
# la voce le usa due volte, nella `nota` e in `avvertenze`, e riscriverle
# significherebbe farle divergere.
_AVVERTENZE_B450C = (
    "È l'acciaio che il §7.4.2.2 obbliga a usare in zona sismica, salvo le eccezioni che vi "
    "sono elencate. Barre da 6 a 40 mm (§11.3.2.4).",
)
_AVVERTENZE_B450A = (
    "Stessa resistenza del B450C — il §11.3.2.2 dice «i medesimi valori nominali» — e "
    "duttilità minore: allungamento uniforme al carico massimo 2,5% contro 7,5%, e nessun "
    "tetto sul rapporto di sovraresistenza. Barre da 5 a 10 mm (§11.3.2.4).",
)


CATALOGO: tuple[VoceMateriale, ...] = tuple(
    VoceMateriale(
        classe=classe,
        famiglia="calcestruzzo",
        young=_modulo_elastico(_f_ck_dal_nome(classe)),
        poisson=_POISSON_CALCESTRUZZO,
        density=_DENSITA_CALCESTRUZZO,
        f_k=_f_ck_dal_nome(classe),
        fonte=_fonte_di_classe(classe),
        origine="derivata",
        fissata=FISSATA,
        nota=_nota_di_classe(classe, _f_ck_dal_nome(classe)),
        f_ctm=_resistenza_a_trazione_media(_f_ck_dal_nome(classe)),
        avvertenze=_avvertenze_di_classe(classe, _f_ck_dal_nome(classe)),
    )
    for classe in _CLASSI_CALCESTRUZZO
) + (
    VoceMateriale(
        classe="B450C",
        famiglia="acciaio",
        young=200000.0,
        poisson=_POISSON_ACCIAIO,
        density=_DENSITA_ACCIAIO,
        f_k=450.0,
        fonte=_FONTE_ACCIAIO,
        origine="nostra",
        fissata=FISSATA,
        nota=" ".join((_NOTA_ACCIAIO, *_AVVERTENZE_B450C)),
        avvertenze=_AVVERTENZE_B450C,
    ),
    VoceMateriale(
        classe="B450A",
        famiglia="acciaio",
        young=200000.0,
        poisson=_POISSON_ACCIAIO,
        density=_DENSITA_ACCIAIO,
        f_k=450.0,
        fonte=_FONTE_ACCIAIO,
        origine="nostra",
        fissata=FISSATA,
        nota=" ".join((_NOTA_ACCIAIO, *_AVVERTENZE_B450A)),
        avvertenze=_AVVERTENZE_B450A,
    ),
)


def _chiave(classe: str) -> str:
    """La grafia su cui due nomi di classe si confrontano.

    Si normalizza il caso e si tolgono gli spazi ai bordi, **su entrambi i lati
    del confronto**. Non e' la regola di `ccx`, che ignora il caso perche' il
    formato del deck lo impone: qui e' una scelta di comodita' d'ingresso, e
    regge solo perche' nessuna coppia di voci del catalogo differisce per il
    solo caso -- lo sorveglia un test.
    """
    return classe.strip().upper()


def trova(classe: str) -> VoceMateriale:
    """La voce di catalogo che porta questa classe.

    Solleva invece di rendere `None`: un chiamante che confrontasse contro
    `None` se ne accorgerebbe a valle, lontano dal punto in cui la classe e'
    stata scritta male. Il rifiuto elenca le classi che esistono, perche' quasi
    sempre la classe giusta e' una di quelle e differisce di poco.
    """
    chiave = _chiave(classe)
    for voce in CATALOGO:
        if _chiave(voce.classe) == chiave:
            return voce
    elenco = ", ".join(voce.classe for voce in CATALOGO)
    raise KeyError(f"classe di materiale sconosciuta: {classe!r}; il catalogo porta {elenco}")


def valori_di_progetto(voce: VoceMateriale) -> dict[str, float]:
    """Le resistenze di progetto della voce, dalle [4.1.3] e [4.1.5].

        calcestruzzo:  f_cd = alpha_cc * f_ck / gamma_c     con alpha_cc = 0,85
        acciaio:       f_yd = f_yk / gamma_s                con gamma_s = 1,15

    Nessuna delle sei riduzioni ulteriori della norma e' applicata: vedi il
    docstring del modulo per l'elenco e per il motivo.

    Accetta anche una voce che il registro non ha filtrato -- un materiale
    dichiarato a mano ha la stessa forma di una riga di catalogo -- e per questo
    ripete qui il controllo sulla resistenza: senza, un `f_k` a zero darebbe una
    resistenza di progetto nulla in silenzio, e una sezione senza resistenza si
    leggerebbe come un risultato invece che come una dichiarazione incompleta.
    """
    if not math.isfinite(voce.f_k) or voce.f_k <= 0.0:
        raise ValueError(
            f"{voce.classe}: resistenza caratteristica non positiva o non finita "
            f"({voce.f_k}), nessun valore di progetto è calcolabile"
        )
    if voce.famiglia == "calcestruzzo":
        return {"f_cd": ALFA_CC * voce.f_k / GAMMA_C}
    if voce.famiglia == "acciaio":
        return {"f_yd": voce.f_k / GAMMA_S}
    raise ValueError(
        f"{voce.classe}: famiglia sconosciuta ({voce.famiglia!r}), i coefficienti parziali "
        "da applicare non sono decidibili"
    )
