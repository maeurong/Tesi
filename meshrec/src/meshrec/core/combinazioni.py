"""I coefficienti di norma delle combinazioni, la loro proposta, e la sismica statica equivalente.

Unico luogo dove un coefficiente ψ o γ delle NTC 2018 ha il proprio valore,
come `core/soglie.py` lo e' per le soglie di verifica e `core/materiali.py`
per le classi di materiale. **La forma e' quella di `soglie.py` e non una forma
nuova**: ogni voce porta la propria `fonte`, l'`origine` del numero, la data in
cui e' stata fissata e, dove serve, la nota che spiega la scelta.

I numeri e i loro articoli vengono da
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md`, sezioni 7 e 8,
che li ha letti sul testo di norma convertito. Qui non si ricerca nulla.

**Perche' non stanno in `core/soglie.py`.** Quel registro e' delle soglie di
qualita' del maglio, e i suoi campi (`minimo`, `massimo`, `unita`, `cancello` o
`etichetta`) non descrivono un coefficiente di combinazione, che non delimita
nulla. La forma si imita, il file no.

**La natura dell'azione comanda (#146 Q1).** Nessun coefficiente si sceglie da
solo: e' `natura` -- `permanente_strutturale`, `permanente_non_strutturale`,
`variabile` -- a dire quale riga della Tab. 2.6.I e quale colonna della Tab.
2.5.I spettino a un'azione. Un'azione che non la dichiara **ferma** la
proposta, con il proprio nome nel messaggio: presumere «variabile» sarebbe un
coefficiente scelto d'ufficio, ed e' esattamente cio' che il campo esiste per
impedire.

**Il programma propone, l'operatore corregge.** `proponi` genera le
combinazioni di norma; `Combinazione.proposta` distingue cio' che ha suggerito
il programma da cio' che ha scritto l'operatore, e `aggiorna` rifa' le sole
proposte lasciando intatto ciò che qualcuno ha gia' corretto a mano.

**Tutti i carichi si combinano come sfavorevoli.** La Tab. 2.6.I ha due
colonne, favorevole e sfavorevole, e la scelta fra le due dipende
dall'**effetto** del carico sulla verifica in esame -- cioe' da un risultato
che non esiste prima di risolvere. Le proposte prendono percio' sempre la
colonna sfavorevole, che e' quella conservativa, e chi sa che un carico aiuta
corregge il coefficiente a mano: le NTC §2.5.3 dicono infatti di **omettere** i
carichi favorevoli, non di ridurli. I valori favorevoli stanno comunque nel
registro, perche' chi corregge li legga da qui invece che da una dispensa.

**Che cosa questo modulo non fa.**

- **La modale con spettro non c'e'**, ed e' una decisione e non una
  dimenticanza: pretende la combinazione delle risposte modali (SRSS o CQC),
  che e' un'operazione **sui risultati** e produce una grandezza senza segno
  che non appartiene a nessun caso, mentre il contratto di #138 e' «un campo
  per caso». La decisione manca (#146, §8.1 del piano di Fase 8): qui c'e' la
  sola statica lineare equivalente.
- **Lo spettro di progetto `S_d(T_1)` non si calcola qui.** Dipende dal sito --
  `a_g`, `F_0`, `T_C*`, categoria di sottosuolo, fattore `q` (NTC §3.2.3.5) --
  e nessuno di quei dati sta nella configurazione. `forza_di_base` lo riceve
  come argomento: chi lo passa dichiara da dove viene.
- **La pressione permanente del percorso hexa** (`abaqus.write_inp`, parametro
  `pressure`) non e' un'azione dichiarata e non porta una `natura`: entra in
  ogni passo, combinazioni comprese, con coefficiente unitario. Un carico
  permanente che non sa di esserlo non puo' ricevere il proprio γ.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Literal, NamedTuple

import numpy as np

from .config import GRAVITY_MM_S2, Combinazione, Natura, PipelineConfig

Origine = Literal["letta", "derivata", "nostra"]

FISSATA = date(2026, 8, 30)

_FONTE_PSI = "NTC 2018 §2.5.2, Tab. 2.5.I"
_FONTE_GAMMA = "NTC 2018 §2.6.1, Tab. 2.6.I, colonna A1 (STR)"


class VocePsi(NamedTuple):
    """I tre coefficienti di combinazione di una categoria d'uso.

    Tre numeri in una voce sola e non tre voci, per la stessa ragione per cui
    `materiali.VoceMateriale` ne porta piu' d'uno: sono la riga di una tabella
    pubblicata, nascono insieme e si citano insieme. Spezzarli darebbe tre
    voci con la stessa fonte e la stessa nota, cioe' tre posti dove divergere.

    `ψ_0` e' il valore di combinazione, `ψ_1` il frequente, `ψ_2` il quasi
    permanente. La definizione di ciascuno sta nel §2.5.2 e spiega perche' e'
    `ψ_2` e non `ψ_0` a entrare nelle masse sismiche: e' «il valore istantaneo
    superato oltre il 50% del tempo nel periodo di riferimento».
    """

    categoria: str
    descrizione: str
    psi_0: float
    psi_1: float
    psi_2: float
    fonte: str
    origine: Origine
    fissata: date
    nota: str = ""


class VoceGamma(NamedTuple):
    """Il coefficiente parziale di una natura d'azione, nelle sue due colonne.

    `favorevole` e `sfavorevole` sono due numeri della stessa riga di tabella,
    e la scelta fra loro non e' un fatto del carico ma del suo **effetto**
    sulla verifica: sta a valle, non qui.
    """

    natura: Natura
    simbolo: str
    favorevole: float
    sfavorevole: float
    fonte: str
    origine: Origine
    fissata: date
    nota: str = ""


# Le categorie I («coperture praticabili») e K («coperture per usi speciali»)
# non stanno qui: la Tab. 2.5.I al loro posto scrive «da valutarsi caso per
# caso», e riempirle di numeri vorrebbe dire inventarli. `psi_di` le nomina nel
# rifiuto, cosi' chi le cerca sa che sono state viste e lasciate fuori apposta.
_CASO_PER_CASO = ("I", "K")

PSI: tuple[VocePsi, ...] = (
    VocePsi("A", "Ambienti ad uso residenziale", 0.7, 0.5, 0.3,
            _FONTE_PSI, "letta", FISSATA),
    VocePsi("B", "Uffici", 0.7, 0.5, 0.3, _FONTE_PSI, "letta", FISSATA),
    VocePsi("C", "Ambienti suscettibili di affollamento", 0.7, 0.7, 0.6,
            _FONTE_PSI, "letta", FISSATA),
    VocePsi("D", "Ambienti ad uso commerciale", 0.7, 0.7, 0.6,
            _FONTE_PSI, "letta", FISSATA),
    VocePsi("E", "Aree per immagazzinamento, uso commerciale e industriale; "
                 "biblioteche, archivi, magazzini",
            1.0, 0.9, 0.8, _FONTE_PSI, "letta", FISSATA),
    VocePsi("F", "Rimesse, parcheggi, aree per il traffico di veicoli "
                 "(autoveicoli di peso <= 30 kN)",
            0.7, 0.7, 0.6, _FONTE_PSI, "letta", FISSATA,
            nota=(
                "La conversione del PDF ha mandato la parentesi «(per autoveicoli "
                "di peso > 30 kN)» su una riga a sé: le due righe F e G si "
                "distinguono ricomponendola, ed è la ricerca a dichiararlo"
            )),
    VocePsi("G", "Rimesse, parcheggi, aree per il traffico di veicoli "
                 "(autoveicoli di peso > 30 kN)",
            0.7, 0.5, 0.3, _FONTE_PSI, "letta", FISSATA),
    VocePsi("H", "Coperture accessibili per sola manutenzione", 0.0, 0.0, 0.0,
            _FONTE_PSI, "letta", FISSATA,
            nota=(
                "Tre zeri **letti**, non un valore mancante: una copertura "
                "accessibile per sola manutenzione non accompagna nessuna altra "
                "azione, e la riga della tabella lo dice"
            )),
    VocePsi("VENTO", "Vento", 0.6, 0.2, 0.0, _FONTE_PSI, "letta", FISSATA),
    VocePsi("NEVE", "Neve, quota <= 1000 m s.l.m.", 0.5, 0.2, 0.0,
            _FONTE_PSI, "letta", FISSATA),
    VocePsi("NEVE_OLTRE_1000", "Neve, quota > 1000 m s.l.m.", 0.7, 0.5, 0.2,
            _FONTE_PSI, "letta", FISSATA),
    VocePsi("TERMICHE", "Variazioni termiche", 0.6, 0.5, 0.0,
            _FONTE_PSI, "letta", FISSATA),
)

_NOTA_COLONNA_A1 = (
    "La colonna è A1 e non EQU né A2, e la norma stessa dice quando: «Per la "
    "progettazione di componenti strutturali che non coinvolgano azioni di "
    "tipo geotecnico, le verifiche nei confronti degli stati limite ultimi "
    "strutturali (STR) si eseguono adottando i coefficienti γF riportati nella "
    "colonna A1». Un modello di membratura fuori terra è quel caso. Chi "
    "verifica l'equilibrio come corpo rigido (EQU) o la resistenza del terreno "
    "(GEO) ha altre due colonne, che questo registro non porta perché nessuno "
    "le chiede ancora"
)

GAMMA: tuple[VoceGamma, ...] = (
    VoceGamma("permanente_strutturale", "gamma_G1", 1.0, 1.3,
              _FONTE_GAMMA, "letta", FISSATA, nota=_NOTA_COLONNA_A1),
    VoceGamma("permanente_non_strutturale", "gamma_G2", 0.8, 1.5,
              _FONTE_GAMMA, "letta", FISSATA,
              nota=(
                  _NOTA_COLONNA_A1
                  + ". La nota (1) della tabella ammette di scendere da 1,5 a "
                  "1,3 «nel caso in cui l'intensità dei carichi permanenti non "
                  "strutturali sia ben definita in fase di progetto»: è un "
                  "giudizio di chi analizza, non un fatto della riga, e resta "
                  "una correzione a mano"
              )),
    VoceGamma("variabile", "gamma_Q", 0.0, 1.5,
              _FONTE_GAMMA, "letta", FISSATA,
              nota=(
                  _NOTA_COLONNA_A1
                  + ". Il valore favorevole è **zero e non uno**: un carico "
                  "variabile che aiuta si toglie, non si riduce"
              )),
)


def psi_di(categoria: str) -> VocePsi:
    """La riga della Tab. 2.5.I di quella categoria d'uso.

    Solleva invece di rendere `None` o di scegliere una riga plausibile: senza
    la categoria il programma non puo' sapere se un solaio e' residenziale o un
    magazzino, e fra le due i ψ_2 valgono 0,3 e 0,8.
    """
    chiave = categoria.strip().upper()
    for voce in PSI:
        if voce.categoria == chiave:
            return voce
    if chiave in _CASO_PER_CASO:
        raise KeyError(
            f"la categoria d'uso {categoria!r} è fra quelle che la Tab. 2.5.I "
            "lascia «da valutarsi caso per caso»: i tre ψ non sono pubblicati, "
            "e questo registro non li inventa. Dichiara i coefficienti a mano"
        )
    elenco = ", ".join(voce.categoria for voce in PSI)
    raise KeyError(
        f"categoria d'uso sconosciuta: {categoria!r}; la Tab. 2.5.I porta {elenco}"
    )


def gamma_di(natura: Natura) -> VoceGamma:
    """La riga della Tab. 2.6.I di quella natura d'azione."""
    for voce in GAMMA:
        if voce.natura == natura:
            return voce
    elenco = ", ".join(voce.natura for voce in GAMMA)
    raise KeyError(f"natura sconosciuta: {natura!r}; le nature sono {elenco}")


def azioni_dichiarate(cfg: PipelineConfig) -> dict[str, Natura | None]:
    """Le azioni del deck e la natura che ciascuna dichiara, nell'ordine dei passi.

    Il passo di peso proprio non ha un campo `natura` da compilare e non gli
    serve: e' `G1` **per definizione** di norma -- NTC §2.5.1, «peso proprio
    degli elementi strutturali» -- e non una deduzione del programma.

    Le altre azioni portano la natura che l'operatore ha dichiarato, `None`
    compreso: questa funzione **riporta**, non completa. Chi la passa a
    `proponi` riceve il rifiuto che nomina l'azione incompleta, ed e' li' che
    la mancanza deve emergere.

    L'ordine e' quello in cui `abaqus.write_inp` scrive i passi, cosi' che
    l'ordine dei termini di una combinazione proposta sia quello del deck.
    """
    azioni: dict[str, Natura | None] = {}
    if cfg.analysis is not None:
        azioni[cfg.analysis.step_name] = "permanente_strutturale"
    carichi = cfg.carichi
    if carichi.spinta is not None:
        azioni["SPINTA_ORIZZONTALE"] = carichi.spinta.natura
    if carichi.carico_sommita is not None:
        azioni["CARICO_TOP"] = carichi.carico_sommita.natura
    for carico in (*carichi.posizionati, *carichi.distribuiti):
        azioni[carico.nome] = carico.natura
    return azioni


def _senza_natura(azioni: Mapping[str, Natura | None]) -> list[str]:
    return [nome for nome, natura in azioni.items() if natura is None]


def proponi(
    azioni: Mapping[str, Natura | None],
    categoria_uso: str,
    *,
    azione_sismica: str | None = None,
) -> list[Combinazione]:
    """Le combinazioni di norma dalle nature dichiarate (#146 Q1).

    Cinque tipi, ciascuno con la propria espressione del §2.5.3:

        [2.5.1] fondamentale       gamma_G1*G1 + gamma_G2*G2
                                   + gamma_Q*Q_k1 + gamma_Q*psi_0j*Q_kj
        [2.5.2] caratteristica     G1 + G2 + Q_k1 + psi_0j*Q_kj
        [2.5.3] frequente          G1 + G2 + psi_11*Q_k1 + psi_2j*Q_kj
        [2.5.4] quasi permanente   G1 + G2 + psi_2j*Q_kj
        [2.5.5] sismica            E + G1 + G2 + psi_2j*Q_kj

    **La precompressione `P` non compare**: nessuna azione di questo programma
    la dichiara, e un termine per un'azione che non esiste sarebbe un passo
    scritto a vuoto.

    **Le prime tre si ripetono, una per ciascuna variabile nel ruolo di base**:
    il §2.5.2 dice che «`Q_k1` rappresenta l'azione variabile di base e `Q_k2`,
    `Q_k3`, ... le azioni variabili d'accompagnamento», e quale delle variabili
    domini non si sa prima di risolvere. Con n variabili sono n combinazioni per
    tipo, non una. La quasi permanente e la sismica non hanno una base e restano
    una sola.

    `azione_sismica` e' il nome dell'azione che fa da `E` nella `[2.5.5]`.
    Senza, la sismica **non si propone**: `natura` ha tre valori e nessuno dice
    «sismica», quindi il programma non puo' sapere quale azione sia il sisma, e
    sceglierne una sarebbe indovinare. Quell'azione e' esclusa dalle altre
    quattro combinazioni, dove la norma non la mette.

    I coefficienti sono tutti quelli **sfavorevoli**: vedi il docstring del
    modulo per il motivo.
    """
    psi = psi_di(categoria_uso)
    if azione_sismica is not None and azione_sismica not in azioni:
        raise ValueError(
            f"l'azione sismica '{azione_sismica}' non è fra quelle dichiarate "
            f"({sorted(azioni)}): la [2.5.5] ha bisogno di un'azione E che il "
            "deck scriva davvero"
        )
    mute = _senza_natura(azioni)
    if mute:
        raise ValueError(
            f"le azioni {mute} non dichiarano la propria natura: senza, nessun "
            "coefficiente parziale può scegliersi da solo, e presumere "
            "«variabile» sarebbe un γ scelto d'ufficio. Dichiara `natura` "
            "(permanente_strutturale, permanente_non_strutturale, variabile) "
            "su ciascuna, oppure scrivi le combinazioni a mano"
        )
    if not azioni:
        return []

    permanenti = [nome for nome, n in azioni.items() if n != "variabile"]
    variabili = [
        nome for nome, n in azioni.items()
        if n == "variabile" and nome != azione_sismica
    ]
    gamma = {nome: gamma_di(azioni[nome]).sfavorevole for nome in permanenti}
    gamma_q = gamma_di("variabile").sfavorevole

    proposte: list[Combinazione] = []

    def aggiungi(nome, tipo, termini):
        proposte.append(
            Combinazione(nome=nome, tipo=tipo, termini=tuple(termini), proposta=True)
        )

    def con_base(prefisso, tipo, su_permanente, su_base, su_accompagnamento):
        """Un tipo che si ripete con ciascuna variabile a turno come base."""
        fissi = [(nome, su_permanente(nome)) for nome in permanenti]
        if not variabili:
            if fissi:
                aggiungi(prefisso, tipo, fissi)
            return
        for base in variabili:
            termini = [
                *fissi,
                (base, su_base),
                *((altra, su_accompagnamento) for altra in variabili if altra != base),
            ]
            aggiungi(f"{prefisso}_{base}", tipo, termini)

    con_base("SLU_FOND", "slu_fondamentale",
             lambda nome: gamma[nome], gamma_q, gamma_q * psi.psi_0)
    con_base("SLE_RARA", "sle_rara", lambda _nome: 1.0, 1.0, psi.psi_0)
    con_base("SLE_FREQ", "sle_frequente", lambda _nome: 1.0, psi.psi_1, psi.psi_2)

    quasi = [(nome, 1.0) for nome in permanenti]
    quasi += [(nome, psi.psi_2) for nome in variabili]
    if quasi:
        aggiungi("SLE_QP", "sle_quasi_permanente", quasi)

    if azione_sismica is not None:
        sismica = [(azione_sismica, 1.0)]
        sismica += [(nome, 1.0) for nome in permanenti]
        sismica += [(nome, psi.psi_2) for nome in variabili]
        aggiungi("SISMICA", "sismica", sismica)

    return proposte


def aggiorna(
    esistenti: Sequence[Combinazione],
    azioni: Mapping[str, Natura | None],
    categoria_uso: str,
    *,
    azione_sismica: str | None = None,
) -> tuple[Combinazione, ...]:
    """Le combinazioni rigenerate, senza toccare quelle corrette a mano.

    `proposta=False` dice che il numero l'ha scelto l'operatore, e ricalcolare
    non puo' cancellarlo: sarebbe il programma che smentisce chi analizza, in
    silenzio, ed e' la ragione per cui quel campo esiste.

    Una proposta omonima di una correzione a mano **non entra**: il deck
    scriverebbe due passi con lo stesso nome, e la configurazione li rifiuta.
    Fra i due vince quello dell'operatore.
    """
    a_mano = [c for c in esistenti if not c.proposta]
    presi = {c.nome.casefold() for c in a_mano}
    nuove = [
        c
        for c in proponi(azioni, categoria_uso, azione_sismica=azione_sismica)
        if c.nome.casefold() not in presi
    ]
    return (*a_mano, *nuove)


# ------------------------------------------------------------------------------
# La sismica statica lineare equivalente, NTC 2018 §7.3.3.2.
#
# Solo questa: la modale con spettro pretende una decisione che non c'e' (vedi
# il docstring del modulo).
#
# Il §7.3.3.2 ammette la statica «a condizione che il periodo del modo di
# vibrare principale nella direzione in esame (T1) non superi 2,5 TC o TD e che
# la costruzione sia regolare in altezza». Le due condizioni non si verificano
# qui: `T_C` e `T_D` dipendono dal sito e non stanno nella configurazione, e la
# regolarita' in altezza (§7.2.2) e' un giudizio sull'edificio. Chi usa queste
# funzioni le ha verificate altrove.
# ------------------------------------------------------------------------------

# §7.3.3.2: «λ è un coefficiente pari a 0,85 se T1 < 2TC e la costruzione ha
# almeno tre orizzontamenti, uguale a 1,0 in tutti gli altri casi». La
# condizione e' **congiuntiva**: un edificio a due piani non prende lo sconto.
LAMBDA_RIDOTTO = 0.85
LAMBDA_PIENO = 1.0
ORIZZONTAMENTI_PER_LO_SCONTO = 3

_MM_PER_METRO = 1000.0


def periodo_fondamentale(spostamento_mm: float) -> float:
    """`T_1 = 2·√d` [7.3.6], con `d` in **metri** e `T_1` in secondi.

    `d` e' «lo spostamento laterale elastico del punto piu' alto dell'edificio,
    espresso in metri, dovuto alla combinazione di carichi [2.5.7] applicata
    nella direzione orizzontale»: si prende il peso sismico e lo si gira di 90
    gradi, non si applica una forza sismica.

    L'argomento e' in **millimetri**, che sono le unita' del progetto, e la
    conversione avviene qui: passare millimetri alla `[7.3.6]` da' un periodo
    31,6 volte piu' grande, ed e' un numero plausibile e sbagliato.

    La `[7.3.6]` e' condizionata: vale per costruzioni fino a 40 m con massa
    approssimativamente uniforme in altezza, e «in assenza di calcoli piu'
    dettagliati». E' una stima, non una definizione di `T_1`. La formula delle
    NTC 2008 `T_1 = C_1·H^(3/4)` **non esiste piu'** nelle NTC 2018, e un
    programma che la usasse citerebbe una norma abrogata.
    """
    if not math.isfinite(spostamento_mm) or spostamento_mm <= 0.0:
        raise ValueError(
            f"spostamento in sommità non positivo o non finito ({spostamento_mm}): "
            "la [7.3.6] renderebbe un periodo nullo, che è un numero e non un "
            "risultato. Una struttura che non si sposta sotto il proprio peso "
            "girato di lato non ha un periodo stimabile per questa via"
        )
    return 2.0 * math.sqrt(spostamento_mm / _MM_PER_METRO)


def coefficiente_lambda(periodo_s: float, t_c_s: float, orizzontamenti: int) -> float:
    """`λ` del §7.3.3.2: 0,85 se `T_1 < 2·T_C` **e** almeno tre orizzontamenti.

    `T_C` dipende dal sito (§3.2.3.5) e arriva da fuori: nessun dato della
    configurazione lo porta.
    """
    sconto = periodo_s < 2.0 * t_c_s and orizzontamenti >= ORIZZONTAMENTI_PER_LO_SCONTO
    return LAMBDA_RIDOTTO if sconto else LAMBDA_PIENO


def forza_di_base(
    ordinata_spettro: float,
    peso: float,
    coefficiente: float,
    *,
    gravita: float = GRAVITY_MM_S2,
) -> float:
    """`F_h = S_d(T_1)·W·λ/g`, §7.3.3.2.

    `ordinata_spettro` e' `S_d(T_1)` come **accelerazione**, nelle stesse unita'
    di `gravita` (mm/s^2 nel progetto); `peso` e' `W`, il peso complessivo della
    costruzione, in newton. La divisione per `g` c'e' perche' `S_d` e'
    un'accelerazione e `W` un peso: e' esattamente il posto dove nasce l'errore
    di un fattore 9,81.

    `S_d` non si calcola qui: dipende dal sito (§3.2.3.5) e nessun dato della
    configurazione lo porta.
    """
    if not math.isfinite(peso) or peso <= 0.0:
        raise ValueError(
            f"peso complessivo non positivo o non finito ({peso}): la forza di "
            "base uscirebbe nulla, e una forza nulla spacciata per risultato è "
            "indistinguibile da un sisma che non c'è"
        )
    if not math.isfinite(ordinata_spettro) or ordinata_spettro <= 0.0:
        raise ValueError(
            f"ordinata dello spettro di progetto non positiva o non finita "
            f"({ordinata_spettro}): S_d(T_1) è un'accelerazione e viene dal §3.2.3.5, "
            "che dipende dal sito. Questo programma non la calcola: va passata"
        )
    return ordinata_spettro * peso * coefficiente / gravita


def forze_di_piano(
    forza_di_base: float,
    quote: np.ndarray,
    pesi: np.ndarray,
) -> np.ndarray:
    """`F_i = F_h·z_i·W_i / Σ_j z_j·W_j` [7.3.7].

    Distribuzione triangolare pesata sulle masse, cioe' il primo modo
    approssimato con una retta. Le `z` si misurano **dal piano di fondazione**
    (rimando esplicito del §7.3.3.2 al §3.2.3.1), non dal suolo ne' dal piano
    terra.

    La somma delle `F_i` vale `F_h` per costruzione, ed e' la verifica di
    autoconsistenza piu' economica che questa formula porti con se'.
    """
    quote = np.asarray(quote, dtype=np.float64)
    pesi = np.asarray(pesi, dtype=np.float64)
    if quote.shape != pesi.shape:
        raise ValueError(
            f"quote e pesi hanno forme diverse ({quote.shape} e {pesi.shape}): "
            "la [7.3.7] li accoppia uno a uno"
        )
    momenti = quote * pesi
    denominatore = float(momenti.sum())
    if not math.isfinite(denominatore) or denominatore <= 0.0:
        raise ValueError(
            f"la somma dei prodotti quota per peso vale {denominatore}: la [7.3.7] "
            "non è definita. Una struttura con tutte le masse al piano di "
            "fondazione, o senza massa, non distribuisce nessuna forza sismica "
            "lungo l'altezza, e zero forze non sono una distribuzione"
        )
    return forza_di_base * momenti / denominatore
