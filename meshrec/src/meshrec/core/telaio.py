"""Il telaio a fibre: le parti misurate, composte in un modello risolvibile.

Questo modulo **non misura niente**. Le sezioni per stazione le misura
`wall.misura` (`Membratura.sezioni_fette`, `quote_fette`, `base_sezione`), gli
incontri li misura `wall.giunzioni`, le barre le colloca `armatura.colloca`, i
materiali li dichiara l'operatore in `config.RegioneConfig`. Qui si decide solo
**dove stanno i nodi** e **quale asta porta quale sezione**, che e' l'unica cosa
che nessuna delle parti puo' decidere da sola.

Tre scelte di composizione, e nessuna e' un dettaglio.

**Una fetta, un'asta.** Le venti fette di `wall.misura` sono venti elementi in
serie, ciascuno con la sezione misurata alla propria quota (#134 Q2). La
sezione varia lungo l'asse ed e' giusto che vari: appiattirla a una media
butterebbe via `sezione_dispersione`, cioe' proprio cio' che distingue un
rilievo da un disegno. Una fetta che il prior non ha misurato non produce
un'asta: il numero di elementi e' quello vero, mai venti dichiarati a vuoto.

**La lunghezza di calcolo e' da nodo a nodo.** Gli estremi della nuvola non
sono gli estremi dell'asta: chi cede raggiunge il nodo di giunzione, che sta
sull'asse di chi resta (#143 Q2-Q3). Solo il nodo d'estremo si sposta, e le
stazioni interne restano alla quota a cui sono state misurate -- riscalare la
catena sposterebbe ogni sezione da dove il rilievo l'ha trovata.

**Il nodo condiviso e' una stazione di chi resta.** Il nodo che il prior misura
cade quasi sempre fra due stazioni; posarlo esattamente li' vorrebbe dire
spezzare un'asta in due, e il conteggio «una fetta, un'asta» smetterebbe di
valere. Si posa sulla stazione piu' vicina, e di quanto si e' spostato lo dice
`scostamento_nodo` accanto alla `distanza_proiezione` che il prior gia' misura.
E' la stessa regola del resto del progetto: la correzione si mostra, non si tace.

**Due traduzioni verso il consumatore, dichiarate qui perche' e' qui che i due
rami si ricongiungono** (`core/opensees.py` e' stato scritto contro questo
contratto prima che esistesse):

1. `armatura.colloca` misura `y` e `z` da uno spigolo della sezione, in `[0, b]`
   e `[0, h]`; `opensees` posa la `patch rect` **centrata** sul baricentro e
   scrive le barre come `fiber y z`. La traslazione la fa questo modulo, o le
   barre uscirebbero fuori dal calcestruzzo senza che nulla sollevi. Il bordo
   teso finisce dal lato `-e2`.
2. La terna di ogni elemento e' ricostruita **sull'asse dell'elemento**, non su
   quello della membratura: l'asta d'estremo che raggiunge il nodo e' inclinata
   rispetto all'asse misurato, e con la terna della membratura la guardia di
   `opensees._sezioni_ed_elementi` -- `e1 == e2 x asse`, col verso -- cadrebbe.
   La terna della membratura si **rifiuta** invece se non e' quella che
   `wall.misura` costruisce (`e2 == asse x e1`): `sezioni_fette` e' misurata in
   quel piano, e raddrizzarla scambierebbe base e altezza in silenzio.

**Tre cose che questo modulo non porta, e non e' una dimenticanza.** I vincoli,
il numero di modi e il nome del caso di peso proprio restano dedotti da
`core/opensees.py`. Nessuno dei tre e' una misura della geometria: dove poggia
il pezzo e' una lettura e non un rilievo (§6.3 di
`docs/validazione/ricerca-armature-opensees-fibre.md`), e gli altri due sono
parametri d'analisi che `config.Modale` e `config.AnalysisConfig` gia'
dichiarano. Portarli qui sarebbe una seconda verita' accanto alla prima.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from meshrec.core.armatura import BarraCollocata, colloca
from meshrec.core.config import RegioneConfig, SezioneConfig

# Quanto la terna del prior puo' discostarsi dall'invariante `e2 = asse x e1`
# prima di essere rifiutata. E' uno scarto di arrotondamento, non una
# tolleranza di modellazione: `wall.misura` costruisce `e2` proprio cosi', e
# `12_wall.json` la riscrive in decimale.
_TOLLERANZA_TERNA = 1e-6

# Sotto questa norma la proiezione di `e1` sul piano ortogonale all'asse
# dell'asta e' collassata: `e1` e' parallelo all'asse, e il piano di sezione
# non e' definito. Costante propria e non la tolleranza qui sopra: le due hanno
# significati diversi, e stringere l'una sposterebbe l'altra in silenzio.
_NORMA_MINIMA_E1 = 1e-6


def _versore(v: np.ndarray) -> np.ndarray:
    norma = float(np.linalg.norm(v))
    if norma == 0.0:
        raise ValueError("versore nullo: non definisce una direzione")
    return np.asarray(v, dtype=np.float64) / norma


class ElementoTelaio(NamedTuple):
    """Un'asta: una fetta della membratura, con la sezione misurata li'."""

    membratura: int
    """Indice nella lista `membrature` del prior."""
    stazione: int
    """Indice della fetta dentro la membratura, nell'ordine di `sezioni_fette`."""
    nodo_i: int
    """Indice in `Telaio.nodi` dell'estremo di quota minore lungo l'asse."""
    nodo_j: int
    """Indice in `Telaio.nodi` dell'estremo opposto."""
    sezione: tuple[float, float]
    """Le due estensioni della **propria** fetta [mm]: la prima lungo e1, la seconda lungo e2."""
    e1: np.ndarray
    """Versore (3,) del primo asse di sezione, ortogonale all'asse di **questa** asta."""
    e2: np.ndarray
    """Versore (3,) del secondo. Vale `e1 == e2 x asse`, che e' cio' che il solutore controlla."""
    barre: list[BarraCollocata]
    """Le barre a questa stazione, **centrate sul baricentro** della sezione. Vuota: solo calcestruzzo."""
    riempimento_sezione: float
    """Quanto il rettangolo sta semplificando (#142 Q3).

    E' il valore **della membratura** ripetuto su ogni sua asta, non quello
    della fetta: `wall.misura` calcola il riempimento fetta per fetta ma
    restituisce solo la mediana, e un numero per stazione qui sarebbe inventato.
    """


class Telaio(NamedTuple):
    """Il modello a telaio: nodi, aste, incontri e materiali. Nessun carico."""

    nodi: np.ndarray
    """(m, 3) float64 [mm], nelle coordinate della nuvola."""
    elementi: list[ElementoTelaio]
    """Nell'ordine delle membrature del prior, e dentro ciascuna nell'ordine delle fette."""
    giunzioni: list[dict[str, object]]
    """I record di `wall.giunzioni`, piu' `nodo_telaio` (indice in `nodi`) e `scostamento_nodo` [mm]."""
    materiali: dict[int, SezioneConfig]
    """Indice di membratura -> la sezione dichiarata per la sua regione."""


def _sezioni_dichiarate(
    regioni: dict[str, RegioneConfig], quante: int
) -> dict[int, SezioneConfig]:
    """Una sezione per membratura, e nessun predefinito sotto.

    `RegioneConfig` dichiara che il rifiuto dell'indice fuori intervallo spetta
    a chi legge il prior, perche' la configurazione nasce prima che lo step 12
    giri: chi legge e' questo modulo.
    """
    per_membratura: dict[int, SezioneConfig] = {}
    da: dict[int, str] = {}
    for nome, regione in regioni.items():
        indice = int(regione.membratura)
        if not 0 <= indice < quante:
            raise ValueError(
                f"la regione '{nome}' nomina la membratura {indice}, ma il prior "
                f"ne porta {quante}: la configurazione è stata scritta prima "
                "dello step 12, e l'indice non è più quello di questa corsa"
            )
        if indice in per_membratura:
            raise ValueError(
                f"le regioni '{da[indice]}' e '{nome}' nominano la stessa "
                f"membratura {indice}: due sezioni per la stessa asta, e "
                "sceglierne una sarebbe la sezione decisa dall'ordine di un "
                "dizionario"
            )
        per_membratura[indice] = regione.sezione
        da[indice] = nome
    mancanti = [indice for indice in range(quante) if indice not in per_membratura]
    if mancanti:
        elenco = ", ".join(f"membratura {indice}" for indice in mancanti)
        raise ValueError(
            f"il prior porta {quante} membrature e queste non hanno una sezione "
            f"dichiarata in `regioni`: {elenco}. Il telaio non ha materiali per "
            "quelle aste, e non si ricade su un predefinito"
        )
    return per_membratura


def _piano_di_sezione(voce: dict, indice: int) -> tuple[np.ndarray, np.ndarray]:
    """`(asse, e1)` della membratura, o il motivo per cui non si costruisce.

    `e2` si verifica qui e non esce: chi costruisce un'asta lo ricava dal
    proprio asse, e restituirlo inviterebbe a usare quello della membratura.
    """
    base = np.asarray(voce.get("base_sezione", []), dtype=np.float64).reshape(-1, 3)
    if base.shape != (2, 3):
        raise ValueError(
            f"la membratura {indice} non porta `base_sezione`: è un prior "
            "scritto prima che quella misura esistesse. Senza il piano non si "
            "sa dove stiano le due estensioni della sezione né come orientare "
            "la sezione a fibre, e un telaio dedotto a caso sarebbe peggio di "
            "un telaio assente"
        )
    asse = _versore(np.asarray(voce["asse"], dtype=np.float64))
    e1, e2 = base
    if not np.allclose(np.cross(asse, e1), e2, atol=_TOLLERANZA_TERNA):
        raise ValueError(
            f"la membratura {indice} ha una `base_sezione` che non è quella di "
            "`wall.misura`: là vale `e2 = asse x e1`, e qui non vale. Le due "
            "colonne di `sezioni_fette` sono misurate in quel piano, quindi "
            "raddrizzarlo scambierebbe base e altezza della sezione a fibre "
            "senza che nulla lo dica"
        )
    return asse, e1


def _stazioni(voce: dict, indice: int) -> tuple[np.ndarray, np.ndarray]:
    """`(coordinate dei nodi lungo l'asse, sezioni per fetta)`.

    Gli `n + 1` nodi di una membratura con `n` fette: i due estremi della nuvola
    e, in mezzo, il punto medio fra due stazioni consecutive. Con tutte e venti
    le fette sono esattamente i bordi che `wall.misura` ha usato per tagliarle;
    con una fetta saltata il vuoto resta visibile come un'asta piu' lunga,
    invece di far scivolare tutte le sezioni di una posizione.
    """
    quote = np.asarray(voce["quote_fette"], dtype=np.float64).reshape(-1)
    sezioni = np.asarray(voce["sezioni_fette"], dtype=np.float64).reshape(-1, 2)
    if len(quote) != len(sezioni):
        raise ValueError(
            f"la membratura {indice} porta {len(sezioni)} sezioni di fetta e "
            f"{len(quote)} quote: senza la propria quota una sezione non "
            "colloca nulla, e la coppia sbagliata sposterebbe ogni asta sulla "
            "stazione successiva"
        )
    if len(quote) == 0:
        raise ValueError(
            f"la membratura {indice} non porta nessuna fetta misurabile: non c'è "
            "un'asta da scrivere, e fabbricarne una sulla sezione media "
            "significherebbe dare al solutore una misura che il rilievo non ha "
            "fatto"
        )
    lunghezza = float(voce["lunghezza"])
    if not (np.all(np.diff(quote) > 0.0) and quote[0] > 0.0 and quote[-1] < lunghezza):
        raise ValueError(
            f"la membratura {indice} ha `quote_fette` che non cresce dentro "
            f"[0, {lunghezza:g}] mm: {quote.tolist()}. Le fette di `wall.misura` "
            "sono i centri di bin equispaziati, quindi crescono per costruzione; "
            "fuori ordine o fuori dal pezzo appenderebbero ogni sezione alla "
            "stazione sbagliata senza che nulla lo dica"
        )
    interni = (quote[:-1] + quote[1:]) / 2.0
    return np.concatenate([[0.0], interni, [lunghezza]]), sezioni


def _fondi_le_giunzioni(
    prior: dict, catene: list[np.ndarray], offset: list[int]
) -> tuple[dict[int, int], dict[int, tuple[int, int]], list[dict[str, object]]]:
    """Gli alias fra nodi che un incontro rende lo stesso nodo.

    Chi cede porta il proprio estremo **piu' vicino** al nodo -- lo stesso
    estremo che `wall.nodo_di_giunzione` ha gia' scelto per misurare la
    distanza -- sulla stazione di chi resta piu' vicina al nodo misurato.
    """
    alias: dict[int, int] = {}
    coppia_di: dict[int, tuple[int, int]] = {}
    incontri: list[dict[str, object]] = []
    quante = len(catene)
    for record in prior["giunzioni"]:
        cede, resta = int(record["cede"]), int(record["resta"])
        if not (0 <= cede < quante and 0 <= resta < quante):
            raise ValueError(
                f"la giunzione {record} nomina le membrature {cede} e {resta}, ma "
                f"il prior ne porta {quante}: gli indici sono dentro la lista "
                "delle membrature accettate, e questo prior non è quello con cui "
                "l'adiacenza è stata misurata"
            )
        nodo = np.asarray(record["nodo"], dtype=np.float64)
        stazione = int(np.argmin(np.linalg.norm(catene[resta] - nodo, axis=1)))
        bersaglio = offset[resta] + stazione
        estremi = [0, len(catene[cede]) - 1]
        distanze = [float(np.linalg.norm(catene[cede][e] - nodo)) for e in estremi]
        sorgente = offset[cede] + estremi[int(np.argmin(distanze))]
        # Unione e non assegnazione: la testa di un pilastro interno riceve
        # due traversi **dallo stesso estremo**, ed e' la topologia normale di
        # un telaio a piu' campate. Rifiutarla -- come questo modulo faceva --
        # lasciava passare solo i telai a campata unica. I nodi diventano uno;
        # di quanto ciascuno si e' mosso lo dice `scostamento_nodo`.
        radice_cede, radice_resta = _risolvi(sorgente, alias), _risolvi(bersaglio, alias)
        if radice_cede != radice_resta:
            alias[radice_cede] = radice_resta
        coppia_di.setdefault(sorgente, (cede, resta))
        incontri.append({**record, "nodo_telaio": bersaglio})
    return alias, coppia_di, incontri


def _risolvi(indice: int, alias: dict[int, int]) -> int:
    """Il nodo vero dietro un alias. Il giro e' limitato: un anello solleva."""
    for _ in range(len(alias) + 1):
        if indice not in alias:
            return indice
        indice = alias[indice]
    raise ValueError(
        "le giunzioni formano un anello di nodi che si rimandano l'un l'altro: "
        "ogni membratura dell'anello cede all'altra, e non resta un nodo su cui "
        "posarsi"
    )


def costruisci(prior: dict[str, object], regioni: dict[str, RegioneConfig]) -> Telaio:
    """Il telaio a fibre dal prior geometrico e dalle regioni dichiarate.

    Una fetta, un'asta; i nodi dall'adiacenza che il prior ha gia' scritto; le
    barre ricollocate a ogni stazione, perche' `colloca` dipende dalla sezione e
    la sezione cambia.

    Solleva -- e non restituisce un telaio a meta' -- quando manca una parte:
    nessuna membratura, l'adiacenza di una corsa vecchia, il piano di sezione,
    una sezione dichiarata, o una geometria su cui l'aritmetica non parte.
    """
    membrature = list(prior.get("membrature") or [])
    if not membrature:
        raise ValueError(
            "il prior non porta nessuna membratura: non c'è un telaio da "
            "costruire. Non è un telaio vuoto, è l'assenza di un modello, e "
            "scriverlo darebbe un `.tcl` che OpenSees esegue senza calcolare "
            "niente"
        )
    if "giunzioni" not in prior:
        raise ValueError(
            "il prior non porta la chiave `giunzioni`: è una corsa scritta prima "
            "che l'adiacenza fosse misurata. Un telaio senza connettività non è "
            "un telaio, sono aste che galleggiano, e dedurre gli incontri qui "
            "sarebbe fabbricare una misura che nessuno ha fatto"
        )
    sezioni_dichiarate = _sezioni_dichiarate(regioni, len(membrature))

    posizioni: list[np.ndarray] = []
    catene: list[np.ndarray] = []
    offset: list[int] = []
    piani: list[tuple[np.ndarray, np.ndarray]] = []
    sezioni_di: list[np.ndarray] = []
    for indice, voce in enumerate(membrature):
        asse, e1 = _piano_di_sezione(voce, indice)
        lungo, sezioni = _stazioni(voce, indice)
        catena = np.asarray(voce["origine"], dtype=np.float64) + np.outer(lungo, asse)
        if not np.isfinite(catena).all():
            raise ValueError(
                f"la membratura {indice} produce nodi con coordinate non finite: "
                "`origine`, `asse` o `lunghezza` portano un NaN. Ogni confronto "
                "contro NaN è falso, quindi nessuna guardia a valle lo vedrebbe "
                "e il telaio arriverebbe intero al solutore"
            )
        offset.append(len(posizioni))
        posizioni.extend(catena)
        catene.append(catena)
        piani.append((asse, e1))
        sezioni_di.append(sezioni)

    alias, coppia_di, incontri = _fondi_le_giunzioni(prior, catene, offset)

    nodi: list[np.ndarray] = []
    numerati: dict[int, int] = {}

    def registra(grezzo: int) -> int:
        vero = _risolvi(grezzo, alias)
        if vero not in numerati:
            numerati[vero] = len(nodi)
            nodi.append(posizioni[vero])
        return numerati[vero]

    elementi: list[ElementoTelaio] = []
    for indice, voce in enumerate(membrature):
        asse, e1 = piani[indice]
        sezioni = sezioni_di[indice]
        armatura = sezioni_dichiarate[indice].armatura
        riempimento = float(voce["riempimento"]["valore"])
        for stazione in range(len(sezioni)):
            base, altezza = float(sezioni[stazione, 0]), float(sezioni[stazione, 1])
            if not (base > 0.0 and altezza > 0.0):
                raise ValueError(
                    f"la stazione {stazione} della membratura {indice} ha "
                    f"sezione {base:g} x {altezza:g} mm: una `patch rect` di "
                    "estensione nulla e un `-GJ 0` OpenSees li accetta senza "
                    "dire niente, e l'asta esce senza rigidezza"
                )
            grezzo_i, grezzo_j = offset[indice] + stazione, offset[indice] + stazione + 1
            nodo_i, nodo_j = registra(grezzo_i), registra(grezzo_j)
            delta = nodi[nodo_j] - nodi[nodo_i]
            if float(delta @ asse) <= 0.0:
                raise ValueError(
                    f"la stazione {stazione} della membratura {indice} ha "
                    f"lunghezza di calcolo {float(delta @ asse):g} mm: l'asta si "
                    "rovescia su se stessa invece di accorciarsi"
                    f"{_nomina_coppia(grezzo_i, grezzo_j, coppia_di)}"
                )
            asse_elemento = _versore(delta)
            e1_elemento = e1 - asse_elemento * float(e1 @ asse_elemento)
            if float(np.linalg.norm(e1_elemento)) < _NORMA_MINIMA_E1:
                raise ValueError(
                    f"la stazione {stazione} della membratura {indice} ha l'asse "
                    "dell'asta parallelo a e1: il piano di sezione non è "
                    "definito, e la sezione a fibre uscirebbe orientata a caso"
                )
            e1_elemento = _versore(e1_elemento)
            elementi.append(
                ElementoTelaio(
                    membratura=indice,
                    stazione=stazione,
                    nodo_i=nodo_i,
                    nodo_j=nodo_j,
                    sezione=(base, altezza),
                    e1=e1_elemento,
                    e2=np.cross(asse_elemento, e1_elemento),
                    barre=_barre(armatura, base, altezza, indice, stazione),
                    riempimento_sezione=riempimento,
                )
            )

    # Lo scostamento si misura contro il nodo **finale**, non contro la
    # stazione scelta: dopo l'unione di due incontri sullo stesso estremo il
    # nodo puo' essersi mosso una seconda volta, e il numero deve dire dove il
    # telaio l'ha davvero messo rispetto a dove il prior l'aveva misurato.
    for incontro in incontri:
        incontro["nodo_telaio"] = registra(int(incontro["nodo_telaio"]))
        incontro["scostamento_nodo"] = float(
            np.linalg.norm(
                nodi[incontro["nodo_telaio"]]
                - np.asarray(incontro["nodo"], dtype=np.float64)
            )
        )

    return Telaio(
        nodi=np.asarray(nodi, dtype=np.float64).reshape(-1, 3),
        elementi=elementi,
        giunzioni=incontri,
        materiali=sezioni_dichiarate,
    )


def _nomina_coppia(
    grezzo_i: int, grezzo_j: int, coppia_di: dict[int, tuple[int, int]]
) -> str:
    for grezzo in (grezzo_i, grezzo_j):
        if grezzo in coppia_di:
            cede, resta = coppia_di[grezzo]
            return (
                f": il nodo di giunzione fra le membrature {cede} e {resta} cade "
                "oltre la stazione successiva"
            )
    return ""


def _barre(
    armatura, base: float, altezza: float, membratura: int, stazione: int
) -> list[BarraCollocata]:
    """Le barre della stazione, traslate sul baricentro della sezione.

    `colloca` le misura da uno spigolo; `opensees` scrive la `patch rect` da
    `-b/2` a `+b/2` e le barre come `fiber y z` nello stesso riferimento. Senza
    questa traslazione le fibre d'acciaio cadrebbero in un quadrante fuori dal
    calcestruzzo, e OpenSees le accetterebbe senza dire niente.
    """
    if armatura is None:
        return []
    try:
        grezze = colloca(armatura, (base, altezza))
    except ValueError as errore:
        raise ValueError(
            f"la stazione {stazione} della membratura {membratura}: {errore}"
        ) from errore
    return [
        BarraCollocata(barra.y - base / 2.0, barra.z - altezza / 2.0, barra.diametro)
        for barra in grezze
    ]
