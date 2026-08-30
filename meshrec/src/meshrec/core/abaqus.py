"""Scrittura del deck Abaqus (.inp), compatibile anche con CalculiX."""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import numpy as np

from meshrec.core import selezione
from meshrec.core.config import (
    GRAVITY_MM_S2,
    AnalysisConfig,
    CarichiConfig,
    Material,
    Momento,
    Selettore,
    TetConfig,
    _mappa_casefold,
)

_SET_ITEMS_PER_LINE = 8

# Rapporto massimo ammesso fra la componente del momento effettivo che cade
# fuori dall'asse dichiarato e il modulo dichiarato. Adimensionale: una
# coppia di forze realizza esattamente il momento voluto solo se i due
# gruppi stanno alla stessa quota lungo l'asse (vedi `coppia_equivalente`);
# su un selettore volumetrico con estensione lungo l'asse non e' cosi', e il
# deck scriverebbe in silenzio un momento anche perpendicolare a quello
# chiesto.
#
# La soglia e' la media geometrica fra il peggiore dei casi as-built
# legittimi misurati (un `TOP` reale non e' un piano, e' una banda di nodi
# entro la tolleranza dei set, e porta gia' da se' un rapporto fuori-asse
# non nullo) e il caso volumetrico degenere (un selettore che sconfina
# lungo l'asse). I due margini che ne risultano non sono equivalenti: sotto
# soglia il deck scrive un momento storto **in silenzio** -- il guasto che
# questo controllo esiste per chiudere -- sopra soglia si rifiuta un caso
# legittimo, ma con un messaggio che l'operatore vede subito. E' il margine
# sopra quello da difendere, non quello sotto: la media geometrica lo rende
# esplicito invece di sceglierlo a occhio. I numeri delle due misure e i
# margini risultanti sono in `docs/fase-6-carichi.md`, non qui -- un numero
# di laboratorio dentro `src/` legherebbe questa soglia a una geometria sola.
TOLLERANZA_MOMENTO_FUORI_ASSE: float = 5e-2

# Una componente di direzione che vale meno di questa frazione della piu'
# grande dello stesso vettore non scrive la sua riga *CLOAD. Il confronto
# con lo zero esatto bastava alla forza, che prende le componenti dalla
# configurazione, e non al momento: `np.cross(asse, separazione)` scrive
# 1e-16 dove la geometria vuole zero, e meta' delle righe di una coppia
# erano quel rumore. La soglia sta quattro ordini di grandezza sopra
# l'arrotondamento del prodotto vettoriale (~1e-16 relativo) e otto sotto
# qualunque componente che sposti un risultato: risultante e momento
# realizzati non cambiano in modo misurabile.
SOGLIA_COMPONENTE_RELATIVA: float = 1e-12

# Sopra questo rapporto fra i due valori singolari nel piano della coppia, il
# selettore e' troppo vicino all'isotropo perche' la geometria determini su
# quale diametro la coppia cade. Il momento attorno all'asse resta quello
# dichiarato per costruzione: arbitraria e' la direzione, che puo' cambiare
# in silenzio fra un rimaglio e l'altro. La curva non offre un ginocchio da
# leggere come soglia -- la sensibilita' cresce come r/(1 - r^2), liscia --
# quindi questo numero dichiara quanta rotazione si accetta: 2,30 gradi nel
# caso peggiore su una piastra sintetica cui si toglie un nodo, provate tutte
# le rimozioni. Tabella misurata e margini delle due geometrie reali in
# `docs/fase-6-carichi.md`, sezione 5.5.
SOGLIA_PAREGGIO_VALORI_SINGOLARI: float = 8e-1


class UnconstrainedModelWarning(UserWarning):
    """L'insieme vincolato raggiunge meno della meta' della superficie d'appoggio."""


class CaricoSulVincoloWarning(UserWarning):
    """Un carico posizionato include, in parte, nodi dell'insieme vincolato."""


class SelettoreIsotropoWarning(UserWarning):
    """Il selettore di un momento non determina la direzione della coppia."""


def _gradi_da_scrivere(direzione: np.ndarray) -> list[tuple[int, float]]:
    """I gradi di liberta con una componente che conta, e la componente stessa.

    Il filtro vive sulla **direzione**, non sul valore che finisce nel deck.
    La direzione e' un versore, la stessa per tutti i nodi del carico: qui si
    decide *quali gradi di liberta* ricevono una riga, non *quali nodi*. Una
    componente a 1e-16 e' rumore di `np.cross(asse, separazione)`, dove la
    geometria vuole zero, e meta' delle righe di una coppia erano quel
    rumore; il confronto e' relativo alla componente piu' grande dello stesso
    vettore (vedi `SOGLIA_COMPONENTE_RELATIVA`) perche' su uno dei due
    percorsi che la chiamano lo zero non arriva mai esatto.

    **Un nodo a quota nulla scrive comunque la sua riga, a zero.** Il valore
    scritto e' `quota * componente`, e la quota non passa di qui: un nodo ad
    area tributaria nulla porta nel deck una riga a `-0.000000000e+00`.
    Non e' una svista da correggere filtrando a valle. `docs/fase-6-carichi.md`
    § 4 pubblica per `CARICO_TOP` una tabella con 3.036 righe `*CLOAD`, di cui
    703 a zero, e spiega li' che cosa sono quei 703 nodi: togliere le righe
    mute porterebbe il conteggio a 2.333 e smentirebbe una tabella gia'
    pubblicata. Il comportamento e' fissato da un test apposta.

    Una direzione con tutte le componenti nulle rende una lista vuota: la
    soglia vale zero e nessun `abs(c) > 0.0` passa. Non solleva e non divide.
    """
    soglia = SOGLIA_COMPONENTE_RELATIVA * float(np.abs(direzione).max())
    return [(g, c) for g, c in enumerate(direzione, start=1) if abs(c) > soglia]


def _set_lines(indices: np.ndarray) -> list[str]:
    """Indici 0-based in righe di numeri 1-based, otto per riga."""
    one_based = np.asarray(indices, dtype=np.int64) + 1
    return [
        ", ".join(str(value) for value in one_based[start : start + _SET_ITEMS_PER_LINE])
        for start in range(0, len(one_based), _SET_ITEMS_PER_LINE)
    ]


def _passo_statico(
    nome: str, carichi: list[str], *, elset: str, fixed_nset: str | None,
    print_nsets: tuple[str, ...], pressure: tuple[str, float] | None,
    carichi_nodali: dict[int, tuple[float, float, float]] | None = None,
    pressioni_da_azzerare: tuple[str, ...] = (),
    pressioni_distribuite: tuple[tuple[str, float], ...] = (),
) -> list[str]:
    """Un passo statico completo: nome a commento, carichi, uscite.

    Il nome sta in un commento e non in `*STEP, NAME=` perche' CalculiX
    rifiuta quel parametro e ne emette un avviso; un avviso benigno
    tollerato nasconde quello vero. `*NODE FILE`/`*EL FILE` invece di
    `*OUTPUT, FIELD`: sono keyword Abaqus legacy valide, e sono quelle che
    CalculiX vuole per l'uscita ascii.

    `RF` su `fixed_nset` non e' un'uscita in piu': e' il controllo di
    conservazione, e sta nel deck perche' e' li' che il solutore lo puo'
    dare.

    `pressioni_distribuite` e' una **tupla** e non una pressione sola (#146):
    un passo di combinazione porta dentro di se' piu' azioni, e fra queste
    possono esserci due carichi distribuiti su due superfici diverse. Nei passi
    dei singoli distribuiti la tupla ha un elemento solo, come prima.
    """
    righe = [f"** NOME PASSO: {nome}", "*STEP", "*STATIC", "*DLOAD, OP=NEW"]
    righe += carichi
    # `pressure` e' la pressione **permanente** del modello, legata al parziale
    # in `write_inp` e percio' presente in ogni passo; `pressioni_distribuite`
    # sono quelle dei carichi distribuiti di questo passo (#10). Due parametri e
    # non uno perche' nei passi distribuiti devono comparire **entrambe**: il
    # `*DLOAD, OP=NEW` due righe piu' su cancella anche i `*DSLOAD` dei passi
    # precedenti, quindi una permanente non riscritta qui semplicemente non
    # agisce (#119).
    pressioni = [
        *(() if pressure is None else (pressure,)),
        *pressioni_distribuite,
    ]
    if pressioni:
        # `OP=NEW` su questa card non e' la via: `ccx` **non riconosce quel
        # parametro** su `*DSLOAD`, risponde con due «*WARNING reading *DLOAD:
        # parameter not recognized» e tira dritto ignorandolo -- due avvisi per
        # passo che degradano `controlla_avvisi`, uno dei sette verdetti, senza
        # fare nulla (misurato in CI il 27/08/2026, corsa 33088953374).
        #
        # Le superfici dei passi precedenti si ridichiarano allora a **zero**,
        # nella stessa card e prima delle proprie. **Oggi quelle righe non
        # spostano le reazioni**: `*DLOAD, OP=NEW`, che apre ogni passo, cura
        # gia' lo stesso difetto e arriva prima. Misurato su `ccx` 2.21 con due
        # distribuiti su facce perpendicolari, reazioni del secondo passo (#119):
        #
        #   | passo 2                          |      RF_x |      RF_y |
        #   |----------------------------------|-----------|-----------|
        #   | OP=NEW + azzeramento (com'e' qui) | -1666.667 |     0.000 |
        #   | OP=NEW, azzeramento tolto        | -1666.667 |     0.000 |
        #   | senza OP=NEW, azzeramento tenuto | -1666.667 |     0.000 |
        #   | senza OP=NEW, azzeramento tolto  | -1666.667 | -1666.667 |
        #
        # L'ultima riga e' il difetto di #84, che e' reale; la terza e' il suo
        # rimedio, che e' corretto. Restano perche' sono l'unica rete se un
        # giorno `OP=NEW` se ne va da `*DLOAD`: si toglie la rete dopo aver
        # visto il salto, non prima.
        righe += ["*DSLOAD"]
        righe += [f"{nome_superficie}, P, 0.0" for nome_superficie in pressioni_da_azzerare]
        righe += [f"{nome_superficie}, P, {valore}" for nome_superficie, valore in pressioni]
    if carichi_nodali:
        # Forze nodali esplicite, una componente per riga come vuole `*CLOAD`.
        # Servono al patch test nella variante a carichi (vedi #46): la
        # trazione di uno stato tensionale costante si integra sulle facce di
        # bordo e diventa un vettore per nodo, che nessuna delle vie esistenti
        # sa esprimere -- `ripartisci` distribuisce una risultante per area
        # tributaria, che e' un'altra cosa.
        righe += ["*CLOAD"]
        for nodo in sorted(carichi_nodali):
            for grado, valore in enumerate(carichi_nodali[nodo], start=1):
                if valore != 0.0:
                    righe += [f"{int(nodo) + 1}, {grado}, {valore:.9e}"]
    for name in print_nsets:
        righe += [f"*NODE PRINT, NSET={name}", "U"]
    # Senza set vincolato non c'e' RF da stampare, e non e' una mancanza: un
    # modello cinematicamente incompleto per costruzione -- il benchmark modale
    # FV52 lo e', e i suoi primi tre modi **devono** essere moti rigidi -- non ha
    # reazioni su cui chiudere il bilancio.
    if fixed_nset is not None:
        righe += [f"*NODE PRINT, NSET={fixed_nset}", "RF"]
    righe += ["*NODE FILE", "U", "*EL FILE", "S, E", "*END STEP"]
    return righe


class _Azione(NamedTuple):
    """Le righe di carico di un'azione dichiarata, senza il peso proprio accanto.

    E' quello che una combinazione somma. **Senza** il peso proprio, che nei
    passi dei casi singoli si ripete per una ragione diversa (un passo senza
    peso descriverebbe una struttura che non pesa) e che in una combinazione e'
    esso stesso un'azione, con il proprio coefficiente: ripeterlo di nuovo lo
    scriverebbe due volte, una col γ della combinazione e una senza.

    `cload` non porta l'intestazione `*CLOAD, OP=NEW`: quella va scritta **una
    volta per passo**, e due `OP=NEW` nello stesso passo cancellerebbero le
    forze della prima.
    """

    dload: tuple[str, ...] = ()
    cload: tuple[str, ...] = ()
    pressione: tuple[str, float] | None = None


def _riga_scalata(riga: str, coefficiente: float) -> str:
    """Una riga di carico moltiplicata per il coefficiente della combinazione.

    Si scala il **testo gia' scritto** invece di rifare il conto a monte, e la
    ragione e' che cosi' i passi dei casi singoli restano identici all'ultima
    riga: il coefficiente unitario non passa di qui, e nessuna corsa gia'
    registrata cambia deck. Il conto e' comunque lo stesso -- ogni carico di
    questo esportatore e' lineare nel proprio modulo -- e la riga da scalare la
    scrive questa stessa funzione, non un formato altrui.

    Le due sole forme che arrivano qui portano il numero nella **terza**
    colonna: `elset, GRAV, modulo, nx, ny, nz` e `nodo, grado, valore`. Una
    riga di forma diversa e' un errore di chi ha costruito l'azione, e si
    rifiuta invece di scalare la colonna sbagliata in silenzio.
    """
    campi = [campo.strip() for campo in riga.split(",")]
    if riga.startswith("*") or len(campi) not in (3, 6):
        raise ValueError(
            f"riga di carico non scalabile: {riga!r}. Le forme note sono la "
            "gravità («elset, GRAV, modulo, nx, ny, nz») e la forza nodale "
            "(«nodo, grado, valore»), e in entrambe il modulo sta nella terza "
            "colonna"
        )
    campi[2] = f"{float(campi[2]) * coefficiente:.9e}"
    return ", ".join(campi)


MAGLIO_VUOTO = (
    "il maglio non ha nessun elemento: un deck vuoto è valido per il "
    "solutore, che lo risolve senza protestare, e i controlli di "
    "conservazione uscirebbero verdi su un modello che non esiste"
)
"""Un solo testo per le due porte che rifiutano il maglio vuoto.

`write_inp` e' la guardia di fondo, ma `export_model` non ci arriva: con zero
elementi `boundary_faces` non da' bordo, e `align_to_axes` muore prima con
«nessun nodo da allineare» -- vero, ma e' il sintomo, e manda chi legge a
cercare un difetto nei nodi invece che negli elementi. Due `raise` sullo
stesso testo, e non due testi che scivolano l'uno dall'altro.
"""


CONTINUO_CONFINATO = (
    "il continuo di ogni regione: il calcestruzzo confinato. Un tetraedro non "
    "ha fibre, e non distingue nucleo da copriferro"
)
"""Un solo testo per il commento nel deck e per la chiave nel resoconto.

Il testo non porta accenti perche' finisce in un deck scritto in ascii, ed e'
per questo che la frase non ha copula (vedi tests/test_accenti.py).

Il continuo del modello solido e' il calcestruzzo confinato, e la scelta e' una
**limitazione dichiarata** e non una ovvieta': la distinzione fra nucleo e
copriferro e' un concetto della sezione a fibre, dove sono fibre diverse dello
stesso elemento, e un tetraedro non ha fibre. Fra i due il nucleo e' quello che
domina il volume. L'acciaio non e' un materiale del continuo: senza barre
modellate non ha un elemento a cui appartenere.

Scritto nel deck e non solo qui: chi apre il `.inp` fra sei mesi vede un
calcestruzzo per regione, e senza quella riga crederebbe che il modello
distingua cio' che non distingue. Un testo solo, perche' il commento del deck e
la chiave del resoconto non possano dire due cose diverse.
"""


def _materiali_del_deck(citati: list[tuple[str, Material]]) -> list[Material]:
    """Un `*MATERIAL` per nome distinto, nell'ordine in cui le sezioni li citano.

    `citati` sono i materiali che il deck nomina davvero, ciascuno con chi lo
    dichiara -- serve solo a scrivere di chi parla il rifiuto.

    Lo stesso materiale in due regioni e' un materiale e non due: `ccx` legge
    due card omonime senza protestare e tiene l'ultima, quindi la seconda non
    aggiungerebbe nulla e lascerebbe un nome definito due volte.

    Due materiali **diversi** sotto lo stesso nome sono invece rifiutati, e il
    confronto ignora le maiuscole: `ccx` risolve i nomi senza distinguerle
    (misurato in docs/fase-6-cantiere/sonda-caso-nomi/), quindi le due card
    diventerebbero una sola e a una delle due regioni toccherebbero in silenzio
    le proprieta' dell'altra.
    """
    scritti: dict[str, tuple[str, Material]] = {}
    for chi, materiale in citati:
        gia_chi, gia = scritti.setdefault(materiale.name.casefold(), (chi, materiale))
        if gia != materiale:
            raise ValueError(
                f"{chi} dichiara il materiale '{materiale.name}', ma {gia_chi} ne "
                f"dichiara un altro sotto il nome '{gia.name}': `ccx` risolve i nomi "
                "senza distinguere le maiuscole, quindi le due card diventerebbero "
                "una sola e una delle due regioni prenderebbe in silenzio le "
                "proprietà dell'altra"
            )
    return [materiale for _, materiale in scritti.values()]


def write_inp(
    path: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    *,
    node_sets: dict[str, np.ndarray],
    material: Material,
    element_type: str = "C3D4",
    fixed_nset: str | None = "BASE",
    print_nsets: tuple[str, ...] = (),
    gravity: float = GRAVITY_MM_S2,
    elset: str = "ALL_WALL",
    regioni: dict[str, tuple[np.ndarray, Material]] | None = None,
    step_name: str = "GRAVITA",
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str] | tuple[str, str, str, float], ...] = (),
    pressure: tuple[str, float] | None = None,
    carichi: CarichiConfig | None = None,
    nset_selettori: dict[str, np.ndarray] | None = None,
    spostamenti_imposti: dict[int, dict[int, float]] | None = None,
    carichi_nodali: dict[int, tuple[float, float, float]] | None = None,
) -> dict[str, object]:
    """Scrive un modello pronto all'analisi statica sotto peso proprio.

    `element_type` e' il nome che il solutore legge, e il numero di nodi per
    elemento deve combaciare con esso: un array di otto colonne dichiarato
    C3D4 produrrebbe un deck che nessun solutore puo' leggere, e l'errore
    arriverebbe dopo l'intera pipeline invece che qui.

    Il predefinito C3D4 non e' un parametro di elaborazione con un valore
    scelto: e' il comportamento che questa funzione aveva prima della Fase 4,
    tenuto perche' i chiamanti gia' scritti continuino a valere. Chi sceglie
    davvero il tipo lo prende da `tet.element` o da `model.element`.

    `element_surfaces`, `ties` e `pressure` sono le tre aggiunte della Fase 4 e
    sono tutte facoltative: senza di esse il deck e' identico a quello che
    questa funzione scriveva prima, ed e' cosi' che le corse tetraedriche
    restano confrontabili con quelle gia' fatte. Un carico assente non diventa
    una pressione dichiarata a zero: le due cose non sono la stessa.

    Ogni tupla di `ties` e' `(nome, dipendente, indipendente)` o, con la
    `POSITION TOLERANCE` di Ruling AH (giro di correzione 6),
    `(nome, dipendente, indipendente, tolleranza)`. Un *TIE a tre elementi non
    scrive affatto quel parametro: assente non e' la stessa cosa di zero,
    stessa regola gia' vera per `pressure` qui sopra.

    `carichi` e' la quarta aggiunta, della Fase 5: senza di esso il deck ha un
    solo passo statico sotto peso proprio, come prima. Con esso si aggiungono
    fino a tre passi in piu' -- spinta orizzontale, carico in sommita',
    modale -- ciascuno scritto da `_passo_statico`, tranne il modale che non
    chiede tensioni. Ogni passo e' scritto in dialetto CalculiX: il nome sta
    in un commento e non in `*STEP, NAME=`, e l'uscita e' `*NODE FILE`/`*EL
    FILE` invece di `*OUTPUT, FIELD`. Misurato il 21/08/2026: la forma
    precedente faceva emettere a `ccx` 2.22 due avvisi ("parameter not
    recognized: NAME=..." e "...FIELD"), questa zero.

    `pressure`, quando dato insieme a `carichi`, si ripete identico in **ogni**
    passo statico: non e' un caso di carico fra gli altri, e' una condizione
    permanente del modello -- la stessa natura del peso proprio, che infatti e'
    ripetuto in ognuno di quei passi per la stessa ragione (senza di esso ogni
    passo diverso dal primo descriverebbe una struttura che non pesa). Una
    spinta del terreno dichiarata in Fase 4 non smette di agire perche' il
    passo successivo aggiunge un carico in sommita' o il vento.

    La ripetizione e' **esplicita**, card per card, e non lasciata al
    solutore. Nei passi peso proprio, spinta, sommita' e posizionati la porta
    il parziale `passo_statico` piu' sotto, a cui `pressure` e' legato; nei
    passi dei carichi distribuiti (#10) la scrive `pressione_distribuita`
    accanto alla pressione del distribuito corrente, che occupa la stessa card
    `*DSLOAD`.

    Perche' non basti scriverla una volta e fidarsi della persistenza di
    `*DSLOAD` e' misurato in #119: `*DLOAD, OP=NEW`, che `_passo_statico` mette
    in testa a ogni passo, cancella **anche** i carichi di superficie, non solo
    quelli di volume. Con la sola card del primo passo, le reazioni del passo
    distribuito perdevano per intero la componente della permanente -- `RF_y`
    da -1666.667 a 0.0 su `ccx` 2.21, con la permanente e il distribuito su
    facce perpendicolari. Un carico permanente che si spegne quando arriva il
    vento, senza che il deck diventi invalido o i numeri implausibili.

    `nset_selettori` e' la quinta aggiunta, di questa fase: ogni voce di
    `carichi.posizionati` cita un selettore per nome, ed e' la mappa da quel
    nome agli indici gia' risolti -- il deck scrive un `*NSET` per selettore
    (non per carico: due carichi sullo stesso selettore citano lo stesso
    nome) e un passo statico per carico, col peso proprio ripetuto per la
    stessa ragione degli altri passi.

    `regioni` e' la sesta, della Fase 8 (#135): la mappa da nome di regione ai
    suoi elementi e al suo materiale, `(indici, Material)`, di norma quella che
    `core/attribuzione.py` misura e che la pipeline completa col materiale
    della sezione. Senza di essa il deck ha la sola sezione su `elset`,
    identica a prima -- ed e' cosi' che le corse gia' registrate restano
    riproducibili. Con essa il deck scrive un `*ELSET` per regione, una
    `*SOLID SECTION` per ciascuno e un `*MATERIAL` per nome distinto; `elset`
    (`ALL_WALL`) non si rinomina e non si toglie, resta l'insieme di tutti gli
    elementi dichiarato dalla card `*ELEMENT` ed e' quello che le regioni
    partizionano.

    Gli indici e il materiale insieme e non due dizionari a chiavi uguali: due
    strutture da tenere allineate a mano sono il modo in cui la classe di
    difetto torna, e una regione senza il proprio materiale ricadrebbe in
    silenzio su quello unico della corsa -- cioe' proprio il deck monomaterico
    che dichiarare le regioni serve a non produrre.

    Il materiale delle regioni e' il **calcestruzzo confinato** della loro
    sezione, e il deck lo dichiara: vedi `CONTINUO_CONFINATO`. Gli orfani
    restano su `material`, il materiale unico della corsa (#145).

    Il resoconto (forza effettiva, nodi, e per CARICO_TOP anche
    `nodi_ad_area_nulla`) e' il valore di ritorno di questa funzione, chiave
    per nome di passo: un dizionario riempito e reso, non un parametro
    d'uscita silenzioso in cui un ramo puo' dimenticare di scrivere senza che
    nulla se ne accorga (era esattamente cosi' che CARICO_TOP restava fuori
    da `metrics.json`).
    """
    if fixed_nset is not None and fixed_nset not in node_sets:
        raise ValueError(f"il set vincolato '{fixed_nset}' non e fra i node_sets forniti")
    for name in print_nsets:
        if name not in node_sets:
            raise ValueError(f"il set richiesto in stampa '{name}' non e fra i node_sets forniti")
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(
            f"tipo di elemento '{element_type}' sconosciuto: "
            f"i tipi scrivibili sono {sorted(NODI_PER_ELEMENTO)}"
        )
    # Copia e non il dizionario del chiamante: i carichi distribuiti (#10) ne
    # aggiungono, e mutare l'argomento farebbe crescere la struttura di chi
    # chiama a ogni esportazione, in silenzio.
    superfici = {} if element_surfaces is None else dict(element_surfaces)
    # Un solo spazio di nomi, e ignora le maiuscole: `ccx` risolve i nomi senza
    # distinguerle (misurato in docs/fase-6-cantiere/sonda-caso-nomi/), quindi
    # ogni confronto su questo dizionario passa dallo stesso `_mappa_casefold`
    # che `core/config.py` usa a monte. Tre confronti e non uno: i `ties` e il
    # carico laterale chiedono se un nome c'e', i carichi distribuiti se c'e'
    # gia' -- domande opposte sullo stesso spazio di nomi, e una sola normalizza
    # il caso lasciava le altre due a rifiutare un deck che il solutore legge.
    # Ricostruita dove serve e non tenuta in parallelo a `superfici`, che i
    # distribuiti fanno crescere: due dizionari da sincronizzare a mano sono il
    # modo in cui questa classe di difetto torna.
    per_caso = _mappa_casefold(superfici)
    for tie in ties:
        nome, dipendente, indipendente = tie[0], tie[1], tie[2]
        mancanti = [s for s in (dipendente, indipendente) if s.casefold() not in per_caso]
        if mancanti:
            raise ValueError(
                f"il vincolo *TIE '{nome}' nomina {mancanti}, che non è fra le "
                "superfici dichiarate: un deck così viene rifiutato dal solutore "
                "solo alla lettura, e questo errore arriva prima"
            )
    for nome_regione, (indici_regione, _) in (regioni or {}).items():
        # Prima che si scriva una riga: un *ELSET vuoto non ferma `ccx`, che
        # risolve un modello in cui quella sezione semplicemente non c'e'.
        if len(np.asarray(indici_regione)) == 0:
            raise ValueError(
                f"la regione '{nome_regione}' non contiene alcun elemento: un "
                "*ELSET vuoto non ferma il solutore, che risolve un modello in "
                "cui quella sezione non esiste. Il deck non si scrive a metà"
            )
    if pressure is not None and pressure[0].casefold() not in per_caso:
        raise ValueError(
            f"il carico laterale agisce su '{pressure[0]}', che non è fra le "
            "superfici dichiarate: una pressione applicata a nulla non è un carico"
        )

    nodes = np.asarray(nodes, dtype=np.float64)
    elements = np.asarray(elements, dtype=np.int64)
    attesi = NODI_PER_ELEMENTO[element_type]
    if elements.shape[1] != attesi:
        raise ValueError(
            f"{element_type} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: un deck scritto così non è leggibile da alcun solutore"
        )
    # Le righe, non solo le colonne: un deck con zero elementi e' **valido**
    # per `ccx`, che lo risolve in silenzio. Reazioni nulle contro un peso
    # nullo, e i sette verdetti di `core/solve.py` escono verdi su nulla --
    # un controllo di conservazione che non ha niente da conservare non e'
    # un controllo passato. Qui perche' e' il fondo comune di ogni chiamante;
    # `export_model` ne tiene una propria e identica, perche' col maglio vuoto
    # muore prima di arrivare fin qui (misurato: «nessun nodo da allineare»).
    if len(elements) == 0:
        raise ValueError(MAGLIO_VUOTO)

    # Le superfici dei carichi distribuiti (#10) si derivano qui, prima che le
    # card *SURFACE si scrivano piu' sotto: entrano nello stesso dizionario del
    # percorso hexa, quindi la scrittura e la validazione che gia' esistono non
    # cambiano. Prima del deck e non durante: un selettore che non delimita
    # nulla, o che prende due lati opposti, deve fermare l'esportazione con
    # ancora zero righe scritte -- «il deck non si scrive a metà».
    resoconti_distribuiti: dict[str, dict[str, object]] = {}
    for carico in () if carichi is None else carichi.distribuiti:
        if carico.selettore not in (nset_selettori or {}):
            raise ValueError(
                f"il carico '{carico.nome}' cita il selettore '{carico.selettore}', "
                f"che non è stato risolto: arrivati {sorted(nset_selettori or {})}. "
                "Il deck non si scrive a metà"
            )
        omonima = _mappa_casefold(superfici).get(carico.nome.casefold())
        if omonima is not None:
            raise ValueError(
                f"il carico distribuito '{carico.nome}' darebbe il proprio nome a "
                f"una superficie che è già dichiarata ('{omonima}'): nel deck ci "
                "sarebbero due *SURFACE omonime -- il confronto ignora le "
                "maiuscole perché ccx le ignora -- e il solutore userebbe l'ultima"
            )
        superficie, resoconto_distribuito = superficie_di_pressione(
            nodes, elements, np.asarray(nset_selettori[carico.selettore], dtype=np.int64),
            element_type, nome=carico.nome,
        )
        superfici[carico.nome] = superficie
        resoconto_distribuito["pressione"] = carico.pressione
        # Il meno: l'area vettoriale **esce** dal solido, la pressione preme
        # **dentro**, quindi la forza applicata e' opposta all'area uscente.
        # `risultante` e' la forza che il passo applica, e la reazione al
        # vincolo -- quella che `ccx` stampa -- e' la sua opposta.
        resoconto_distribuito["risultante"] = [
            -carico.pressione * componente
            for componente in resoconto_distribuito["area_vettoriale_uscente"]
        ]
        resoconti_distribuiti[carico.nome] = resoconto_distribuito

    lines: list[str] = ["*HEADING", "modello generato da meshrec (mm, N, MPa, t, s)", "*NODE"]
    lines += [
        f"{index + 1}, {x:.9e}, {y:.9e}, {z:.9e}"
        for index, (x, y, z) in enumerate(nodes)
    ]

    lines.append(f"*ELEMENT, TYPE={element_type}, ELSET={elset}")
    lines += [
        ", ".join([str(index + 1)] + [str(nodo + 1) for nodo in elemento])
        for index, elemento in enumerate(elements)
    ]

    for name, indices in node_sets.items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(indices)

    # Un *NSET per selettore (non per carico): due carichi sullo stesso
    # selettore citano lo stesso nome, ed e' tutto il senso della forma
    # nominata. Ogni selettore compare qui una volta sola perche' e' una
    # chiave di dizionario, non una voce per carico che lo cita.
    for name, indices in (nset_selettori or {}).items():
        lines.append(f"*NSET, NSET={name}")
        lines += _set_lines(np.asarray(indices, dtype=np.int64))

    for nome, coppie in superfici.items():
        lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={nome}")
        lines += [f"{elemento + 1}, S{numero}" for elemento, numero in coppie]

    for tie in ties:
        nome, dipendente, indipendente = tie[0], tie[1], tie[2]
        # ADJUST=NO: spostare i nodi della superficie dipendente sulla
        # indipendente cambierebbe la geometria dopo che il volume e' stato
        # misurato, e il modello non sarebbe piu' quello di cui il report parla.
        # POSITION TOLERANCE (Ruling AH), solo se data: assente non e' zero.
        tolleranza_card = f", POSITION TOLERANCE={tie[3]}" if len(tie) > 3 else ""
        lines.append(f"*TIE, NAME={nome}{tolleranza_card}, ADJUST=NO")
        lines.append(f"{dipendente}, {indipendente}")

    # Le regioni (#135) partizionano `elset`, che resta l'insieme di tutti gli
    # elementi: gli *ELSET prima delle sezioni che li citano, e la sezione su
    # `elset` solo se qualche elemento e' rimasto fuori da ogni regione. Senza
    # sezione quell'elemento non ha materiale e il deck non e' leggibile;
    # scriverla comunque lascerebbe invece una sezione che non attribuisce
    # niente a nessuno. Sta **prima** delle regioni perche' e' il ripiego: chi
    # ha una regione la sovrascrive.
    attribuiti = np.zeros(len(elements), dtype=bool)
    if regioni:
        # Sopra gli *ELSET che spiega, e solo quando le regioni ci sono: senza
        # di esse il deck non ha nulla da dichiarare ed e' quello di prima.
        lines.append(f"** {CONTINUO_CONFINATO}")
    for nome_regione, (indici_regione, _) in (regioni or {}).items():
        indici_regione = np.asarray(indici_regione, dtype=np.int64)
        attribuiti[indici_regione] = True
        lines.append(f"*ELSET, ELSET={nome_regione}")
        lines += _set_lines(indici_regione)
    citati = [
        (f"la regione '{nome_regione}'", materiale)
        for nome_regione, (_, materiale) in (regioni or {}).items()
    ]
    if not attribuiti.all():
        lines.append(f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}")
        # In testa perche' la sua sezione e' la prima, e il ripiego deve poter
        # essere sovrascritto da chi ha una regione.
        citati.insert(0, ("il materiale della corsa", material))
    lines += [
        f"*SOLID SECTION, ELSET={nome_regione}, MATERIAL={materiale.name}"
        for nome_regione, (_, materiale) in (regioni or {}).items()
    ]
    # Solo i materiali che una sezione cita: senza orfani il materiale unico
    # della corsa non e' scritto, per la stessa ragione per cui non e' scritta
    # la sua sezione -- una card che non attribuisce niente a nessuno.
    for materiale in _materiali_del_deck(citati):
        lines += [
            f"*MATERIAL, NAME={materiale.name}",
            "*ELASTIC",
            f"{materiale.young}, {materiale.poisson}",
            "*DENSITY",
            f"{materiale.density:.9g}",
        ]
    lines.append("*BOUNDARY")
    if fixed_nset is not None:
        lines += [f"{fixed_nset}, 1, 3"]

    if spostamenti_imposti:
        # Spostamento imposto a valore non nullo, nodo per nodo e grado per
        # grado. Serve al patch test (vedi #46): la variante canonica impone
        # su tutto il bordo un campo di spostamento lineare noto e risolve
        # l'interno, e nessun set puo' esprimerlo perche' il valore cambia da
        # nodo a nodo.
        #
        # Sta nello stesso blocco `*BOUNDARY` del set vincolato, e non lo
        # sostituisce: chi impone spostamenti deve comunque togliere i moti
        # rigidi, e il modo piu' semplice e' un campo nullo nell'origine con
        # un nodo li'. Un nodo che compare in entrambi riceverebbe due
        # condizioni sullo stesso grado, quindi il chiamante lo esclude.
        for nodo in sorted(spostamenti_imposti):
            for grado in sorted(spostamenti_imposti[nodo]):
                valore = spostamenti_imposti[nodo][grado]
                lines += [f"{int(nodo) + 1}, {grado}, {grado}, {valore:.9e}"]

    passo_statico = functools.partial(
        _passo_statico, elset=elset, fixed_nset=fixed_nset,
        print_nsets=print_nsets, pressure=pressure,
        carichi_nodali=carichi_nodali,
    )

    # Le azioni del deck, ciascuna con le proprie righe di carico e senza il
    # peso proprio accanto: e' cio' che una combinazione somma (#146). Si
    # riempie mentre i passi dei casi singoli si scrivono, perche' le righe
    # sono le stesse -- costruirle due volte sarebbe due posti dove divergere.
    azioni_del_deck: dict[str, _Azione] = {}

    peso = f"{elset}, GRAV, {gravity}, 0.0, 0.0, -1.0"
    azioni_del_deck[step_name] = _Azione(dload=(peso,))
    lines += passo_statico(step_name, [peso])

    if carichi is not None and carichi.spinta is not None:
        # La spinta accompagna il peso proprio nello stesso passo: da sola
        # descriverebbe una struttura che non pesa. La direzione e' un asse
        # orizzontale del modello, che dopo la correzione della terna e'
        # davvero orizzontale.
        versore = {"x": "1.0, 0.0, 0.0", "y": "0.0, 1.0, 0.0"}[carichi.spinta.asse]
        spinta = f"{elset}, GRAV, {gravity * carichi.spinta.coefficiente}, {versore}"
        azioni_del_deck["SPINTA_ORIZZONTALE"] = _Azione(dload=(spinta,))
        lines += passo_statico("SPINTA_ORIZZONTALE", [peso, spinta])

    # Il resoconto di ogni carico che passa da `ripartisci`/`coppia_equivalente`,
    # CARICO_TOP compreso: costruito qui e reso al chiamante (vedi il `return`
    # in fondo), non riempito in loco in un parametro d'uscita. Il ramo che
    # dimenticava di aggiungere CARICO_TOP non faceva rumore proprio perche'
    # nulla obbligava a farlo confluire da qualche parte.
    resoconto: dict[str, object] = {}

    if carichi is not None and carichi.carico_sommita is not None:
        sommita = carichi.carico_sommita
        if sommita.nset not in node_sets or len(node_sets[sommita.nset]) == 0:
            raise ValueError(
                f"il carico in sommita nomina l'insieme '{sommita.nset}', che non è "
                f"fra quelli scritti nel deck ({sorted(node_sets)}) o è vuoto: il "
                f"solutore leggerebbe un carico applicato a nulla"
            )
        nodi_carico = np.asarray(node_sets[sommita.nset], dtype=np.int64)
        # Pesata per area tributaria dalla Fase 6, uniforme per nodo fino alla
        # Fase 5: e' lo stesso carico dei posizionati e non puo' ripartire in
        # un altro modo. I numeri di CARICO_TOP pubblicati in
        # docs/fase-5-analisi.md sono cambiati per questo, ed e' scritto li'.
        quote, resoconto_top = ripartisci(
            sommita.risultante, nodes, elements, nodi_carico, element_type, nome="CARICO_TOP",
        )
        # OP=NEW: senza, ccx tiene attivo il *CLOAD del passo statico
        # precedente (misurato in docs/fase-6-cantiere/sonda-cload-persiste/),
        # e un carico in sommita' seguito da un posizionato applicherebbe
        # entrambi nel secondo passo invece del solo suo.
        righe_cload = ["*CLOAD, OP=NEW"] + [
            f"{int(n) + 1}, 3, {-quota:.9e}"
            for n, quota in zip(nodi_carico, quote, strict=True)
        ]
        azioni_del_deck["CARICO_TOP"] = _Azione(cload=tuple(righe_cload[1:]))
        lines += passo_statico("CARICO_TOP", [peso] + righe_cload)
        resoconto["CARICO_TOP"] = resoconto_top

    # Un passo statico per carico posizionato, col peso proprio ripetuto per
    # la stessa ragione degli altri passi: senza di esso il passo
    # descriverebbe una struttura che non pesa.
    for carico in () if carichi is None else carichi.posizionati:
        if carico.selettore not in (nset_selettori or {}):
            raise ValueError(
                f"il carico '{carico.nome}' cita il selettore '{carico.selettore}', "
                f"che non è stato risolto: arrivati {sorted(nset_selettori or {})}. "
                "Il deck non si scrive a metà"
            )
        indici = np.asarray(nset_selettori[carico.selettore], dtype=np.int64)
        if carico.forza is None:
            righe_cload, resoconto_carico = coppia_equivalente(
                carico.momento, nodes, elements, indici, element_type, nome=carico.nome
            )
            azioni_del_deck[carico.nome] = _Azione(cload=tuple(righe_cload[1:]))
            lines += passo_statico(carico.nome, [peso] + righe_cload)
            resoconto[carico.nome] = resoconto_carico
            continue
        modulo = float(np.linalg.norm(carico.forza))
        quote, resoconto_carico = ripartisci(
            modulo, nodes, elements, indici, element_type, nome=carico.nome
        )
        versore = np.asarray(carico.forza, dtype=np.float64) / modulo
        gradi = _gradi_da_scrivere(versore)
        righe_cload = ["*CLOAD, OP=NEW"]
        for nodo, quota in zip(indici, quote, strict=True):
            righe_cload += [
                f"{int(nodo) + 1}, {grado}, {quota * componente:.9e}"
                for grado, componente in gradi
            ]
        azioni_del_deck[carico.nome] = _Azione(cload=tuple(righe_cload[1:]))
        lines += passo_statico(carico.nome, [peso] + righe_cload)
        resoconto_carico["forza_dichiarata"] = list(carico.forza)
        resoconto_carico["forza_effettiva"] = np.outer(quote, versore).sum(axis=0).tolist()
        resoconto[carico.nome] = resoconto_carico

    # Un passo statico per carico distribuito (#10). La superficie e' gia' nel
    # deck: qui resta solo la card `*DSLOAD`, che `_passo_statico` scrive dai
    # suoi due parametri di pressione. Sono due e non uno perche' in questi
    # passi le pressioni sono due: la permanente del percorso hexa, una sola
    # per tutto il deck e legata al parziale, e quella del distribuito
    # corrente, diversa a ogni giro. La seconda **non sostituisce** la prima --
    # si aggiunge accanto, nella stessa card -- perche' il `*DLOAD, OP=NEW` in
    # testa al passo cancella anche i `*DSLOAD` e una permanente non riscritta
    # qui smetterebbe di agire (#119).
    distribuiti = () if carichi is None else carichi.distribuiti
    for indice, carico in enumerate(distribuiti):
        # `*CLOAD, OP=NEW` come nei due cicli gemelli sopra: `*DLOAD, OP=NEW`
        # azzera il carico di volume e non le forze nodali, e i distribuiti
        # sono ultimi nell'ordine dei passi -- senza la card erediterebbero il
        # `*CLOAD` del posizionato che li precede.
        #
        # Le pressioni dei passi distribuiti precedenti si azzerano una per
        # una (#84): la ragione, e il perche' oggi quelle righe siano inerti,
        # stanno nel commento dentro `_passo_statico`.
        #
        # `pressione_distribuita` e non `pressure`: quest'ultimo e' legato al
        # parziale e porta la permanente, che deve comparire **anche qui**
        # (#119).
        azioni_del_deck[carico.nome] = _Azione(
            pressione=(carico.nome, carico.pressione)
        )
        lines += passo_statico(
            carico.nome, [peso, "*CLOAD, OP=NEW"],
            pressioni_distribuite=((carico.nome, carico.pressione),),
            pressioni_da_azzerare=tuple(c.nome for c in distribuiti[:indice]),
        )
        resoconto[carico.nome] = resoconti_distribuiti[carico.nome]

    # Un passo per combinazione (#146), **dopo** tutti i casi singoli e prima
    # del modale: `metrics["11_export"]["casi_di_carico"]` elenca i passi in
    # quest'ordine, e `solve.risolvi` traduce il numero di passo del `.frd`
    # nell'etichetta del caso leggendo quella lista in ordine. Un passo di
    # combinazione scritto altrove attribuirebbe i risultati al caso sbagliato
    # senza un errore e senza un avviso.
    #
    # Qui il peso proprio **non** si ripete: in una combinazione e' un'azione
    # come le altre, col proprio coefficiente, e chi non lo mette fra i termini
    # ha dichiarato una combinazione senza peso proprio.
    for combinazione in () if carichi is None else carichi.combinazioni:
        dload: list[str] = []
        cload: list[str] = []
        pressioni_combinate: list[tuple[str, float]] = []
        for nome_azione, coefficiente in combinazione.termini:
            azione = azioni_del_deck.get(nome_azione)
            if azione is None:
                raise ValueError(
                    f"la combinazione '{combinazione.nome}' cita l'azione "
                    f"'{nome_azione}', che questo deck non scrive. Le azioni "
                    f"dichiarate sono {sorted(azioni_del_deck)}"
                )
            # Un coefficiente nullo **non** salta il termine: la riga si scrive
            # con il valore a zero, cosi' chi legge il deck vede che l'azione e'
            # stata messa a zero invece di dedurlo dalla sua assenza -- che e'
            # indistinguibile da un termine dimenticato. Un coefficiente
            # negativo e' ammesso e rovescia il verso dell'azione: e' il modo
            # con cui si scrivono le due direzioni del sisma senza dichiarare
            # due carichi.
            dload += [_riga_scalata(riga, coefficiente) for riga in azione.dload]
            cload += [_riga_scalata(riga, coefficiente) for riga in azione.cload]
            if azione.pressione is not None:
                superficie, valore = azione.pressione
                pressioni_combinate.append((superficie, valore * coefficiente))
        lines += passo_statico(
            combinazione.nome,
            [*dload, "*CLOAD, OP=NEW", *cload],
            pressioni_distribuite=tuple(pressioni_combinate),
            # Tutte, e non le precedenti: i passi di combinazione vengono dopo
            # ogni distribuito, quindi ogni sua superficie e' gia' stata
            # dichiarata. Le proprie si riscrivono subito sotto, col valore
            # scalato.
            pressioni_da_azzerare=tuple(c.nome for c in distribuiti),
        )

    if carichi is not None and carichi.modale is not None:
        # Nessun `*EL FILE`: le forme sono normalizzate sulla massa e una
        # tensione calcolata su di esse non significa nulla. Non si chiede.
        lines += [
            "** NOME PASSO: MODALE", "*STEP", "*FREQUENCY", str(carichi.modale.modi),
            "*NODE FILE", "U", "*END STEP",
        ]

    lines.append("")

    Path(path).write_text("\n".join(lines), encoding="ascii")
    return resoconto


def fix_sign(direction: np.ndarray) -> np.ndarray:
    """Convenzione deterministica di segno: componente di modulo massimo positiva.

    Le direzioni principali restituite dalla SVD hanno segno arbitrario: senza
    una convenzione, due esecuzioni sulla stessa nuvola possono produrre assi
    opposti e quindi set di faccia scambiati.

    Pubblica dalla Fase 4: `wall.terna` deve fissare il segno delle proprie
    direzioni con la stessa convenzione con cui `align_to_axes` fissa le sue,
    o due moduli dello stesso programma sceglierebbero versi opposti sulla
    stessa geometria.
    """
    direction = np.asarray(direction, dtype=np.float64)
    return direction if direction[int(np.argmax(np.abs(direction)))] >= 0.0 else -direction


NODI_PER_ELEMENTO: dict[str, int] = {
    "C3D4": 4,
    "C3D10": 10,
    "C3D8": 8,
    "C3D8I": 8,
    "C3D8R": 8,
}
"""Nodi per elemento di ciascun tipo scrivibile nel deck.

C3D8, C3D8I e C3D8R hanno la stessa geometria e differiscono per la
formulazione: la mesh e' la stessa, cambia cosa il solutore ne fa. Sono
distinti qui perche' il nome finisce nel deck e il solutore lo legge.
"""

ANGOLI_PER_ELEMENTO: dict[str, int] = {
    "C3D4": 4,
    "C3D10": 4,
    "C3D8": 8,
    "C3D8I": 8,
    "C3D8R": 8,
}
"""Nodi **d'angolo**, che non sono i nodi.

Un C3D10 ne ha dieci ma i suoi vertici restano quattro: i sei di lato stanno a
meta' degli spigoli e non definiscono ne' facce ne' topologia. Chi cerca il
bordo, costruisce una superficie o ripartisce un'area lavora sui vertici, e
usare `NODI_PER_ELEMENTO` al posto di questa mappa cercherebbe le facce di un
elemento a dieci angoli, che non esiste.

E' la mappa che il commit `66b526d` aveva tolto insieme a C3D10, sotto il nome
`_ANGOLI_PER_COLONNE` e chiavata sul numero di colonne. Chiavarla sul nome
dell'elemento dice la stessa cosa senza chiedere a chi legge di sapere quante
colonne ha un C3D10.
"""

# Le facce di un elemento, come insiemi di nodi d'angolo, per il solo scopo di
# trovare il bordo: qui l'ordine dentro la faccia non conta, perche' le facce
# vengono ordinate prima di essere confrontate. La tabella che l'ordine ce
# l'ha, e con esso il numero S della faccia, e' FACCE_DEL_SOLUTORE (Task 5):
# le due non vanno confuse, ed e' per questo che portano nomi diversi.
FACCE_TOPOLOGICHE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)),
    8: (
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ),
}

# Le facce di un elemento nell'ordine e con la numerazione del solutore: S1 e'
# la prima riga, S2 la seconda, e cosi' via. E' la tabella che il debito
# rinviato dalla Fase 1 chiedeva, ed e' la fonte d'errore silenzioso per cui
# era stato rinviato: sbagliarla produce un deck che il solutore legge senza
# protestare, applicando il carico a una faccia diversa da quella chiesta.
#
# C3D4, dal manuale: S1 = 1-2-3, S2 = 1-4-2, S3 = 2-4-3, S4 = 3-4-1.
# C3D8, dal manuale: S1 = 1-2-3-4, S2 = 5-8-7-6, S3 = 1-5-6-2,
#                    S4 = 2-6-7-3, S5 = 3-7-8-4, S6 = 4-8-5-1.
# Qui gli indici sono 0-based, quindi ciascuno vale uno in meno.
#
# Non e' FACCE_TOPOLOGICHE con un altro nome: quella serve a trovare il bordo e
# ordina gli indici prima di confrontarli, quindi puo' elencare le facce in
# qualunque ordine. Questa non puo': l'ordine E' l'informazione.
FACCE_DEL_SOLUTORE: dict[int, tuple[tuple[int, ...], ...]] = {
    4: ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)),
    8: (
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ),
}

# Le due tabelle sono indicizzate sul numero di nodi dell'elemento, che per il
# primo grado coincide col numero di angoli. Un elemento del secondo grado
# (dieci nodi, quattro angoli) romperebbe la coincidenza e chiederebbe una
# conversione: il writer non lo scrive, e la chiave assente lo ferma.


def _facce_di_bordo(
    elementi: np.ndarray, combinazioni: tuple[tuple[int, ...], ...]
) -> tuple[np.ndarray, np.ndarray]:
    """Le facce di ogni elemento (n_elementi, n_facce, nodi_per_faccia) e la
    maschera di quali sono di bordo.

    Una faccia interna, condivisa da due elementi adiacenti, e' contata due
    volte e viene esclusa per occorrenza: lo stesso criterio di
    `boundary_faces` (non toccata, resta la sua ragione), qui come maschera
    per elemento/faccia invece che come elenco di facce, perche' e' quello
    che serve a `element_surface` e `tie_surface`. Le due funzioni la
    calcolavano separatamente, una vettorizzata e una con un insieme di
    tuple ~1,9x piu' lenta su 27.000 esaedri.
    """
    nodi_per_faccia = len(combinazioni[0])
    facce = np.stack([elementi[:, list(combo)] for combo in combinazioni], axis=1)
    ordinate = np.sort(facce, axis=2).reshape(-1, nodi_per_faccia)
    _, inverso, conteggi = np.unique(ordinate, axis=0, return_inverse=True, return_counts=True)
    di_bordo = (conteggi[inverso.reshape(-1)] == 1).reshape(facce.shape[0], facce.shape[1])
    return facce, di_bordo


def element_surface(
    elements: np.ndarray, indici_nodo: np.ndarray, element_type: str
) -> list[tuple[int, int]]:
    """Le coppie (elemento, numero di faccia) di bordo le cui facce cadono nell'insieme dato.

    Una faccia entra nella superficie solo se **tutti** i suoi nodi stanno
    nell'insieme: tre nodi su quattro non sono quella faccia, e nominarla
    applicherebbe un carico dove l'utente non lo ha chiesto.

    Una faccia interna, condivisa da due elementi adiacenti, non entra mai:
    e' contata due volte nella tabella (una per elemento) e viene esclusa allo
    stesso modo di `boundary_faces`, per occorrenza. Senza questo filtro un
    *TIE o un carico laterale su una selezione di nodi larga finirebbero
    applicati dentro il solido, non sulla sua pelle.

    L'ordine delle coppie e' quello degli elementi e, dentro un elemento,
    quello dei numeri di faccia: e' funzione del dato e non dell'iterazione,
    quindi il deck scritto su due macchine e' lo stesso file.
    """
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{element_type}' sconosciuto")
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = ANGOLI_PER_ELEMENTO[element_type]
    dentro = np.zeros(int(elementi.max()) + 1, dtype=bool)
    dentro[np.asarray(indici_nodo, dtype=np.int64)] = True

    combinazioni = FACCE_DEL_SOLUTORE[angoli]
    facce, di_bordo = _facce_di_bordo(elementi, combinazioni)

    coppie: list[tuple[int, int]] = []
    for posizione in range(len(combinazioni)):
        tutte_dentro = dentro[facce[:, posizione, :]].all(axis=1) & di_bordo[:, posizione]
        coppie += [(int(indice), posizione + 1) for indice in np.flatnonzero(tutte_dentro)]
    coppie.sort()
    return coppie


# Quanto della superficie sopravvive alla somma vettoriale delle sue normali:
# ||somma(area_i * n_i)|| / somma(area_i), cioe' la risultante di una pressione
# unitaria divisa per l'area su cui agisce. Vale **1** su una faccia piana,
# **0,707** su uno spigolo retto a facce uguali, **0,5** su un emisfero, **0**
# su due facce opposte che si guardano.
#
# **La soglia e' 0,5, ed e' derivata e non tarata.** 0,5 e' esattamente
# l'emisfero: la superficie le cui normali coprono **esattamente un
# semispazio**, cioe' il caso limite di un solo «lato». Sotto quel valore la
# superficie gira **oltre** l'opposto, ovvero avvolge il solido -- ed e'
# precisamente il selettore a box che attraversa il pezzo e prende le facce di
# entrambi i lati. Dichiarata prima di misurare qualunque caso reale.
#
# **Cio' che l'indicatore non e'**: una condizione necessaria. Una superficie
# puo' avere efficienza alta e comunque non essere quella voluta. E' un
# indicatore sufficiente del solo difetto che coglie -- le due spinte che si
# annullano -- e la sua ragione di esistere e' che quel difetto **nessuna
# guardia di equilibrio lo vede**: la risultante esce quasi nulla mentre le
# tensioni locali ci sono per davvero.
_EFFICIENZA_MINIMA_DI_PRESSIONE = 0.5


def superficie_di_pressione(
    nodes: np.ndarray,
    elements: np.ndarray,
    indici: np.ndarray,
    element_type: str,
    *,
    nome: str,
) -> tuple[list[tuple[int, int]], dict[str, object]]:
    """La superficie su cui una pressione agisce, piu' il resoconto che la smentisce (#10).

    La superficie e' quella che `element_surface` gia' costruisce: le facce
    **di bordo** con **tutti** i nodi nell'insieme. Qui non si ripartisce
    nulla -- la pressione va nel deck come `*DSLOAD, P` ed e' il solutore a
    integrarla sulle facce -- quindi, a differenza di `ripartisci`, questa
    strada vale anche sui **tetraedri quadratici**: non c'e' alcuna quota
    nodale da sbagliare.

    Le normali sono orientate **verso l'esterno** confrontandole col vettore
    che va dal baricentro dell'elemento a quello della faccia, e non fidandosi
    dell'ordine di `FACCE_DEL_SOLUTORE`: quell'ordine e' giusto, ma farlo
    dipendere da una convenzione di tabella significa che una tabella
    sbagliata darebbe una guardia sbagliata **in silenzio**, che e' il difetto
    per cui la tabella stessa era stata rinviata.
    """
    superficie = element_surface(elements, indici, element_type)
    if not superficie:
        raise ValueError(
            f"il carico '{nome}' agisce su un insieme di nodi che non delimita "
            "alcuna faccia di bordo: nessuna faccia ha tutti i suoi nodi "
            "nell'insieme, oppure l'insieme è tutto interno al solido. Una "
            "pressione applicata a nulla non è un carico"
        )

    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = ANGOLI_PER_ELEMENTO[element_type]
    combinazioni = FACCE_DEL_SOLUTORE[angoli]

    vettori = np.zeros((len(superficie), 3), dtype=np.float64)
    for riga, (elemento, numero) in enumerate(superficie):
        nodi = elementi[elemento][list(combinazioni[numero - 1])]
        p = punti[nodi]
        # Ventaglio dal primo nodo, la stessa decomposizione di `aree_tributarie`:
        # su un triangolo e' il triangolo, su un quadrilatero sono i due
        # triangoli, e la somma vettoriale porta con se' area **e** giacitura.
        vettore = np.zeros(3, dtype=np.float64)
        for k in range(1, len(nodi) - 1):
            vettore = vettore + np.cross(p[k] - p[0], p[k + 1] - p[0]) / 2.0
        centro_elemento = punti[elementi[elemento][:angoli]].mean(axis=0)
        if float(np.dot(vettore, p.mean(axis=0) - centro_elemento)) < 0.0:
            vettore = -vettore
        vettori[riga] = vettore

    aree = np.linalg.norm(vettori, axis=1)
    area_totale = float(aree.sum())
    # Forma positiva, come in `ripartisci`: con `area_totale <= 0.0` un NaN
    # cadrebbe dalla parte permissiva e uscirebbe un'efficienza NaN, che il
    # confronto con la soglia tratterebbe come «passata».
    if not (np.isfinite(area_totale) and area_totale > 0.0):
        raise ValueError(
            f"il carico '{nome}' agisce su {len(superficie)} facce la cui area "
            f"vale {area_totale}: una coordinata non finita o facce degeneri "
            "producono questo, e una pressione su un'area così non è un carico"
        )

    risultante = vettori.sum(axis=0)
    efficienza = float(np.linalg.norm(risultante) / area_totale)
    if efficienza < _EFFICIENZA_MINIMA_DI_PRESSIONE:
        # La direzione di riferimento e' la normale della faccia piu' grande e
        # non il verso della risultante: quando le facce si annullano la
        # risultante e' quasi nulla, e il suo verso non e' piu' una direzione.
        riferimento = vettori[int(np.argmax(aree))]
        verso = float(np.linalg.norm(riferimento))
        concordi = (vettori @ riferimento) > 0.0
        area_con = float(aree[concordi].sum())
        area_contro = float(aree[~concordi].sum())
        raise ValueError(
            f"il carico '{nome}' agisce su una superficie che si richiude su sé "
            f"stessa: {area_con:.6g} mm² di facce spingono da una parte e "
            f"{area_contro:.6g} mm² dall'altra, e le due pressioni si annullano "
            f"(efficienza {efficienza:.4f}, soglia {_EFFICIENZA_MINIMA_DI_PRESSIONE}). "
            "Di norma è un selettore che attraversa il pezzo e ne prende "
            "entrambi i lati: la risultante esce quasi nulla mentre le tensioni "
            "locali ci sono davvero, e nessun controllo di equilibrio lo vede. "
            f"Restringi il selettore a un lato solo (normale di riferimento di "
            f"modulo {verso:.6g} mm²)"
        )

    resoconto: dict[str, object] = {
        "facce": len(superficie),
        "area_totale": area_totale,
        "efficienza": efficienza,
        # La somma vettoriale delle facce, **uscente** dal solido: area e
        # giacitura in un vettore solo. Non e' una forza e il nome non deve
        # prometterlo -- la forza applicata e' `-pressione * questo vettore`,
        # perche' una pressione positiva preme dentro la faccia, e la reazione
        # al vincolo e' a sua volta l'opposta di quella forza.
        "area_vettoriale_uscente": risultante.tolist(),
    }
    return superficie, resoconto


def tie_surface(
    nodes: np.ndarray,
    elements: np.ndarray,
    dentro_altro: Callable[[np.ndarray], np.ndarray],
    element_type: str,
    *,
    tocca: bool = False,
) -> list[tuple[int, int]]:
    """Le coppie (elemento, numero di faccia) di bordo il cui baricentro cade dentro l'altro solido.

    Criterio diverso da `element_surface` apposta, per una ragione fisica e
    non stilistica: un `*TIE` lega due superfici che si toccano, e il
    contatto e' una questione di **area sovrapposta**, non di nodi
    coincidenti -- le due mesh ai lati di una giunzione (Ruling AE) sono
    generate indipendentemente e non condividono nodi, quindi pretendere che
    tutti e quattro i nodi di una faccia cadano dentro l'altro solido
    escluderebbe facce che si toccano davvero solo perche' un angolo e' appena
    fuori. Un carico invece si applica dove l'utente lo ha nominato, e li'
    l'ambiguita' non e' ammessa: e' per questo che `element_surface` resta
    quella che e', non si tocca, e questa e' una funzione a parte.

    `tocca=True` (Ruling AH, giro di correzione 6): una faccia entra anche se
    il baricentro e' fuori ma **almeno uno dei suoi nodi** e' dentro. Misurato
    sul telaio a quattro membrature: il lato indipendente ha facce piu'
    grandi (la sua mesh e' piu' rada), e una faccia cosi' puo' coprire solo in
    parte la zona di contatto -- il baricentro cade fuori pur toccando
    davvero, e i nodi dipendenti sopra quella zona restano senza una faccia su
    cui proiettarsi. Il lato dipendente resta a `tocca=False` (il predefinito):
    sulla faccia di taglio, gia' piana per costruzione, il solo baricentro e'
    gia' quello giusto -- misurato che allargarlo anche li' peggiora, non
    migliora, il risultato (esperimento B3 del giro 6: scambiare i ruoli fa
    salire gli avvisi del solutore da 20 a 58).

    `dentro_altro` e' la geometria iniettata come funzione (punti -> booleani)
    e non un import di `hexa.Prisma`/`hexa.dentro`: `abaqus.py` non dipende da
    `hexa.py`, che gia' importa `abaqus.py`, e importare nell'altro verso
    creerebbe un ciclo.

    Solo facce di bordo (`boundary_faces`, non toccata): una faccia interna,
    condivisa da due elementi, non e' pelle e non puo' stare in una
    superficie, qui come in `element_surface`.
    """
    if element_type not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{element_type}' sconosciuto")
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = ANGOLI_PER_ELEMENTO[element_type]

    combinazioni = FACCE_DEL_SOLUTORE[angoli]
    nodi_per_faccia = len(combinazioni[0])
    facce, di_bordo = _facce_di_bordo(elementi, combinazioni)

    baricentri = punti[facce].mean(axis=2)  # (n_elementi, n_facce, 3)
    forma = baricentri.shape[:2]
    dentro = dentro_altro(baricentri.reshape(-1, 3)).reshape(forma)
    if tocca:
        dentro_nodi = dentro_altro(punti[facce].reshape(-1, 3)).reshape(
            facce.shape[0], facce.shape[1], nodi_per_faccia
        )
        dentro = dentro | dentro_nodi.any(axis=2)

    coppie: list[tuple[int, int]] = []
    for posizione in range(len(combinazioni)):
        selezionate = dentro[:, posizione] & di_bordo[:, posizione]
        coppie += [(int(indice), posizione + 1) for indice in np.flatnonzero(selezionate)]
    coppie.sort()
    return coppie


def surface_area(
    nodes: np.ndarray,
    elements: np.ndarray,
    superficie: list[tuple[int, int]],
    element_type: str,
) -> float:
    """Area della superficie di elemento, somma delle aree tributarie dei suoi nodi.

    E' il controllo che smentisce la superficie esportata: se l'area calcolata
    qui non coincide con quella delle facce che il deck dichiara, la tabella
    delle etichette nomina facce diverse da quelle volute.

    Delega ad `aree_tributarie` invece di ripetere lo stesso ciclo sulle
    facce: le due erano gemelle a mano, stesso ciclo e stesse tabelle
    duplicati, e la somma di un array per nodo e' per costruzione lo stesso
    numero della somma diretta per faccia -- a meno dell'ordine in cui i
    numeri in virgola mobile si sommano, che qui e' per nodo invece che per
    faccia.
    """
    return float(aree_tributarie(nodes, elements, superficie, element_type).sum())


def aree_tributarie(
    nodes: np.ndarray,
    elements: np.ndarray,
    superficie: list[tuple[int, int]],
    element_type: str,
) -> np.ndarray:
    """L'area della superficie ripartita sui suoi nodi, un terzo per triangolo.

    `surface_area` e' `.sum()` di questo array: stesso ciclo, stesse tabelle,
    stesso ventaglio dal primo nodo per una faccia di piu' di tre nodi, una
    sola volta invece che duplicati in due funzioni gemelle a mano.

    Serve alla ripartizione di una risultante: uniforme per nodo il carico
    si concentra dove i nodi sono piu' fitti, che e' una proprieta' del
    maglio e non della struttura.

    Un nodo che non appartiene ad alcuna faccia della superficie resta a
    zero. Non e' un errore qui: e' un fatto che il chiamante deve poter
    riportare.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    elementi = np.asarray(elements, dtype=np.int64)
    angoli = ANGOLI_PER_ELEMENTO[element_type]

    aree = np.zeros(punti.shape[0], dtype=np.float64)
    for elemento, numero in superficie:
        nodi = [elementi[elemento][indice] for indice in FACCE_DEL_SOLUTORE[angoli][numero - 1]]
        for primo, secondo in zip(nodi[1:-1], nodi[2:], strict=True):
            lato_a = punti[primo] - punti[nodi[0]]
            lato_b = punti[secondo] - punti[nodi[0]]
            area = float(np.linalg.norm(np.cross(lato_a, lato_b)) / 2.0)
            for nodo in (nodi[0], primo, secondo):
                aree[nodo] += area / 3.0
    return aree


def ripartisci(
    risultante: float,
    nodes: np.ndarray,
    elements: np.ndarray,
    indici: np.ndarray,
    element_type: str,
    *,
    nome: str,
) -> tuple[np.ndarray, dict[str, object]]:
    """La risultante divisa fra i nodi dell'insieme, in proporzione all'area tributaria.

    La superficie su cui si pesa e' quella che `element_surface` gia'
    costruisce: le facce **di bordo** con **tutti** i nodi nell'insieme. Una
    faccia interna non entra -- il carico finirebbe applicato dentro il
    solido -- e nemmeno una con tre nodi su quattro nell'insieme, perche'
    non e' quella faccia.

    Le quote sono normalizzate sul totale, quindi la loro somma e'
    esattamente `risultante` anche quando qualche nodo dell'insieme non
    tocca alcuna faccia e resta a zero.
    """
    # Su una faccia quadratica questa ripartizione e' **sbagliata**, e sbagliata
    # in un modo che nessuna guardia di conservazione vedrebbe. La formula
    # consistente per pressione uniforme su un triangolo a 6 nodi da' **zero ai
    # tre vertici** e un terzo dell'area a ciascun nodo di lato -- Abaqus Theory
    # Guide §3.2.6, verbatim: «a constant pressure on an element face produces
    # zero equivalent loads at the corner nodes». Qui la ripartizione va per
    # area tributaria sui soli vertici, cioe' l'esatto contrario.
    #
    # La risultante resterebbe giusta, perche' `quote` normalizza sul totale:
    # l'errore e' **autoequilibrato**, risultante e momento nulli, e attraversa
    # `controlla_reazioni` indenne mettendo carico spurio proprio sui vertici,
    # dove si legge il picco di tensione. Meglio fermarsi che mentire in modo
    # invisibile. Vedi docs/validazione/carichi-consistenti-tet10.md.
    attesi = NODI_PER_ELEMENTO.get(element_type)
    if attesi is not None and attesi != ANGOLI_PER_ELEMENTO[element_type]:
        raise NotImplementedError(
            f"carico '{nome}' su elementi {element_type}: la ripartizione per area "
            "tributaria vale per le facce a vertici soli. Su una faccia quadratica i "
            "carichi consistenti danno zero ai vertici, e questa funzione darebbe "
            "loro tutto il carico conservando la risultante -- un errore che nessun "
            "controllo di equilibrio vede. Usa un elemento lineare per i carichi "
            "distribuiti finché la formula consistente non è implementata."
        )
    indici = np.asarray(indici, dtype=np.int64)
    superficie = element_surface(elements, indici, element_type)
    aree = aree_tributarie(nodes, elements, superficie, element_type)[indici]
    totale = float(aree.sum())
    # Forma positiva -- buono se e solo se finito e positivo -- e non
    # `totale <= 0.0`: con quel confronto un'area `NaN` cadeva dalla parte
    # permissiva, le quote uscivano tutte `NaN` e finivano interpolate nelle
    # righe `*CLOAD` del deck. Un `.inp` con `nan` al posto di una forza e'
    # peggio di un deck mancante: il solutore lo legge.
    if not (np.isfinite(totale) and totale > 0.0):
        raise ValueError(
            f"il carico '{nome}' agisce su {indici.size} nodi la cui area di bordo "
            f"vale {totale}: nessuna area utilizzabile su cui ripartire la "
            "risultante. Un insieme di nodi tutto interno al solido, o una "
            "coordinata non finita, producono questo, e un carico applicato a "
            "nulla non è un carico"
        )
    quote = risultante * aree / totale
    resoconto: dict[str, object] = {
        "nodi": int(indici.size),
        "area_totale": totale,
        # Stessa forma positiva: `aree == 0.0` con un `NaN` e' `False`, quindi
        # il conteggio dichiarava sano un insieme che non lo era.
        "nodi_ad_area_nulla": int((~(np.isfinite(aree) & (aree > 0.0))).sum()),
    }
    return quote, resoconto


def coppia_equivalente(
    momento: Momento,
    nodes: np.ndarray,
    elements: np.ndarray,
    indici: np.ndarray,
    element_type: str,
    *,
    nome: str,
) -> tuple[list[str], dict[str, object]]:
    """Le righe *CLOAD di una coppia di forze staticamente equivalente al momento.

    Non un `*CLOAD` sui gradi 4-6: su un C3D4 `ccx` 2.22 lo scarta senza un
    warning e con spostamento esattamente zero, e `controlla_avvisi`
    (`core/solve.py`) non ha nulla da intercettare.

    Il braccio lo dichiara l'operatore e questa funzione lo contraddice se i
    nodi presi non lo sostengono. La via opposta -- misurarlo sull'estensione
    reale -- non chiede nulla ma decide da se', e nessuno la puo' smentire.

    Il momento realizzato e' **esattamente** quello dichiarato solo nella
    componente in asse: la forza si calibra sul braccio effettivo fra i due
    baricentri pesati, che i nodi offrono davvero. Una componente fuori asse
    e' possibile quando i due gruppi non stanno alla stessa quota lungo
    `asse`, ed e' tollerata solo entro `TOLLERANZA_MOMENTO_FUORI_ASSE`, oltre
    la quale la funzione rifiuta. Il `braccio` dichiarato resta il criterio
    con cui i due gruppi sono stati scelti, e il resoconto mostra il momento
    in asse dichiarato e quello effettivo, fuori asse compreso.

    Una coppia ha risultante netta nulla: le sue reazioni vincolari sono
    indistinguibili da quelle della sola gravita', e un oracolo di equilibrio
    che le confronti non puo' passare da li'. E' la ragione per cui i test di
    fattibilita' su una coppia verificano lo spostamento orizzontale e non le
    reazioni, mentre quelli su una forza fanno l'opposto (vedi
    tests/feasibility/test_calculix.py): l'asimmetria e' voluta, non da
    "uniformare" aggiungendo l'oracolo delle reazioni anche qui.
    """
    punti = np.asarray(nodes, dtype=np.float64)
    indici = np.asarray(indici, dtype=np.int64)
    # L'asse nullo non arriva fin qui: `Momento` lo rifiuta a validazione
    # della configurazione, che e' dove vanno i rifiuti che non hanno
    # bisogno di una mesh. Un secondo controllo qui sarebbe codice morto, e
    # il codice morto e' peggio dell'assenza: promette una guardia che
    # nessuno esercita.
    asse = np.asarray(momento.asse, dtype=np.float64)
    asse = asse / float(np.linalg.norm(asse))

    presi = punti[indici]
    baricentro = presi.mean(axis=0)
    relativi = presi - baricentro
    piano = relativi - np.outer(relativi @ asse, asse)

    # Direzione di separazione: quella di massima estensione nel piano
    # perpendicolare all'asse, cioe' dove i nodi offrono il braccio piu'
    # lungo. `fix_sign` ne fissa il **segno**, non l'asse: quale dei due
    # vettori esca dalla SVD lo decide il rapporto fra i due valori
    # singolari, e quando quei due pareggiano lo decide il rumore
    # numerico. Il rapporto finisce nel resoconto
    # (`rapporto_valori_singolari`) perche' si veda anche quando passa; la
    # condizione d'uso e' in docs/fase-6-carichi.md, sezione 5.2.
    _, valori_singolari, versori = np.linalg.svd(piano, full_matrices=False)
    separazione = fix_sign(versori[0])
    proiezione = piano @ separazione
    estensione = float(proiezione.max() - proiezione.min())
    if momento.braccio > estensione:
        raise ValueError(
            f"il momento '{nome}' dichiara un braccio di {momento.braccio:g} mm, e i "
            f"{indici.size} nodi presi si estendono {estensione:.3f} mm nella "
            "direzione della coppia: i nodi non lo sostengono. Accorcia il braccio "
            "o allarga il selettore"
        )

    meta = momento.braccio / 2.0
    positivi = indici[proiezione >= meta]
    negativi = indici[proiezione <= -meta]
    if positivi.size == 0 or negativi.size == 0:
        raise ValueError(
            f"il momento '{nome}' con braccio {momento.braccio:g} mm lascia un lato "
            f"senza nodi ({positivi.size} da una parte, {negativi.size} dall'altra): "
            "una coppia con una sola forza è una forza"
        )

    # L'area tributaria si ripartisce una volta sola sull'intero selettore
    # (Task 6): e' la superficie che ha davvero facce di bordo intere. Un
    # lato preso da solo puo' non averne -- due nodi soli di una faccia
    # tagliata a meta' non formano una faccia -- e ripartire su di lui
    # solleverebbe l'errore di "nessuna faccia di bordo" per un lato che una
    # faccia ce l'ha, solo condivisa con l'altro lato.
    quote_totale, resoconto_aree = ripartisci(
        1.0, nodes, elements, indici, element_type, nome=nome
    )
    maschera_positivi = proiezione >= meta
    maschera_negativi = proiezione <= -meta

    quote_per_gruppo = []
    bracci = []
    for gruppo, maschera in ((positivi, maschera_positivi), (negativi, maschera_negativi)):
        pesi = quote_totale[maschera]
        peso_totale = float(pesi.sum())
        if peso_totale <= 0.0:
            raise ValueError(
                f"il momento '{nome}' con braccio {momento.braccio:g} mm lascia un lato "
                f"({gruppo.size} nodi) senza alcuna area tributaria: nessuna quota da "
                "ripartire su quel lato"
            )
        # Quote normalizzate sul lato: la loro somma e' 1, quindi la forza
        # del lato (Step 7) si distribuisce per intero fra i suoi nodi.
        quote = pesi / peso_totale
        quote_per_gruppo.append(quote)
        # Baricentro del gruppo pesato dalle quote, proiettato sulla direzione
        # di separazione.
        bracci.append(float(((punti[gruppo] - baricentro) @ separazione) @ quote))

    braccio_effettivo = bracci[0] - bracci[1]
    forza = float(momento.modulo) / braccio_effettivo
    direzione = np.cross(asse, separazione)

    # Il momento che il deck scrive davvero, calcolato dalle stesse forze per
    # nodo che finiscono nelle righe *CLOAD e non dal `modulo` dichiarato.
    # Non e' una smentita del programma, e non puo' esserlo: la componente
    # in asse vale il modulo **per costruzione**, perche' la forza si
    # calibra sul braccio effettivo, e `forza_effettiva` esce dalle stesse
    # quote gia' normalizzate sulla risultante. Questi campi documentano
    # cio' che il deck scrive; la sola componente informativa e' quella
    # fuori asse, che nasce quando i due gruppi non stanno alla stessa
    # quota lungo `asse` ed e' silenziosa finche' nessuno la misura.
    momento_effettivo = np.zeros(3)
    for gruppo, quote, segno in (
        (positivi, quote_per_gruppo[0], 1.0), (negativi, quote_per_gruppo[1], -1.0)
    ):
        forze_nodo = (segno * forza) * np.outer(quote, direzione)
        momento_effettivo += np.cross(punti[gruppo] - baricentro, forze_nodo).sum(axis=0)

    fuori_asse = momento_effettivo - (momento_effettivo @ asse) * asse
    rapporto_fuori_asse = float(np.linalg.norm(fuori_asse)) / float(momento.modulo)
    if rapporto_fuori_asse > TOLLERANZA_MOMENTO_FUORI_ASSE:
        raise ValueError(
            f"il momento '{nome}' scriverebbe nel deck un momento effettivo di "
            f"{momento_effettivo.tolist()} N*mm: la componente fuori dall'asse "
            f"dichiarato vale {rapporto_fuori_asse:.3e} volte il modulo, oltre "
            f"la tolleranza di {TOLLERANZA_MOMENTO_FUORI_ASSE:.0e}. I due gruppi "
            "presi non stanno alla stessa quota lungo l'asse del momento: usa "
            "un selettore che giaccia in un piano perpendicolare all'asse"
        )

    gradi = _gradi_da_scrivere(direzione)
    righe = ["*CLOAD, OP=NEW"]
    for gruppo, quote, segno in (
        (positivi, quote_per_gruppo[0], 1.0), (negativi, quote_per_gruppo[1], -1.0)
    ):
        for nodo, quota in zip(gruppo, quote, strict=True):
            righe += [
                f"{int(nodo) + 1}, {grado}, {segno * forza * quota * componente:.9e}"
                for grado, componente in gradi
            ]

    # Il rapporto sta gia' nel resoconto: qui diventa anche un avviso, perche'
    # un numero in un file lo legge chi lo cerca, e chi sceglie un selettore
    # quadrato non sa di doverlo cercare. Avviso e non rifiuto: il deck che
    # esce e' valido, e applicare un momento a una piastra quadrata resta
    # legittimo -- e' la direzione a non essere piu' un dato della geometria.
    rapporto_singolari = float(valori_singolari[1] / valori_singolari[0])
    if rapporto_singolari > SOGLIA_PAREGGIO_VALORI_SINGOLARI:
        warnings.warn(
            f"il momento '{nome}' ha un selettore quasi isotropo nel piano della "
            f"coppia: il rapporto dei valori singolari vale {rapporto_singolari:.3f}, "
            f"oltre {SOGLIA_PAREGGIO_VALORI_SINGOLARI:g}. Il momento attorno "
            "all'asse resta quello dichiarato, ma su quale diametro cade la coppia "
            "lo decide il rumore numerico, e un rimaglio può spostarlo. Allunga il "
            "selettore per fissare la direzione, oppure accetta: il deck è valido e "
            "il momento attorno all'asse è quello dichiarato. Su una piastra "
            "davvero quadrata allungare il selettore cambierebbe la fisica "
            "dichiarata, e accettare è la scelta giusta",
            SelettoreIsotropoWarning,
            stacklevel=2,
        )

    resoconto: dict[str, object] = {
        "nodi": int(indici.size),
        "braccio_dichiarato": float(momento.braccio),
        "braccio_effettivo": braccio_effettivo,
        "momento_dichiarato": (float(momento.modulo) * asse).tolist(),
        "momento_effettivo": momento_effettivo.tolist(),
        "rapporto_valori_singolari": rapporto_singolari,
        "area_totale": resoconto_aree["area_totale"],
        "nodi_ad_area_nulla": resoconto_aree["nodi_ad_area_nulla"],
        "forza_di_ciascun_lato": forza,
        "nodi_positivi": int(positivi.size),
        "nodi_negativi": int(negativi.size),
        "estensione_disponibile": estensione,
    }
    return righe, resoconto


def boundary_faces(elements: np.ndarray) -> np.ndarray:
    """Facce sul bordo della mesh di volume, per qualunque tipo di elemento.

    Stesso ragionamento di quality.boundary_edges, esteso alle facce: si
    costruiscono tutte le facce di ogni elemento, si ordinano gli indici al
    loro interno, si contano le occorrenze e si tengono quelle con occorrenza
    singola.
    """
    elementi = np.asarray(elements, dtype=np.int64)
    # La topologia sta nei **vertici**: i sei nodi di lato di un C3D10 stanno a
    # meta' degli spigoli e non definiscono ne' facce ne' adiacenze. Due
    # tetraedri quadratici che condividono una faccia condividono i tre vertici
    # di quella faccia, e il conteggio delle occorrenze funziona su quelli.
    # Prima di #45 dieci colonne erano un errore, perche' nessun elemento a
    # dieci nodi esisteva; ora sono un tetraedro, e i suoi vertici sono i primi
    # quattro.
    if elementi.shape[1] == 10:
        elementi = elementi[:, :4]
    colonne = elementi.shape[1]
    if colonne not in FACCE_TOPOLOGICHE:
        raise ValueError(
            f"elemento con {colonne} nodi: nessuna topologia di faccia definita per questa forma"
        )
    combinazioni = FACCE_TOPOLOGICHE[colonne]
    facce = np.vstack([elementi[:, combo] for combo in combinazioni])
    facce = np.sort(facce, axis=1)
    uniche, conteggi = np.unique(facce, axis=0, return_counts=True)
    return uniche[conteggi == 1]


def boundary_spacing(nodes: np.ndarray, faces: np.ndarray) -> float:
    """Mediana della lunghezza degli spigoli delle facce di bordo date.

    E' la scala geometrica del maglio dove i set vengono estratti, e non va
    confusa con quella della superficie riparata da cui il maglio deriva: con
    `tet.nobisect` falso TetGen suddivide le facce di ingresso, e sul muro di
    riferimento il bordo del maglio di volume risulta 2,4 volte piu fitto
    della superficie (13,73 mm contro 33,55 mm).

    Dalla Fase 4 vale anche sulle facce quadrilatere della mesh esaedrica: gli
    spigoli sono le coppie consecutive lungo il perimetro, quale che sia il
    numero di lati.
    """
    points = np.asarray(nodes, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    # Gli spigoli di una faccia sono le coppie di nodi consecutivi lungo il suo
    # perimetro: np.roll li da' per un triangolo come per un quadrilatero,
    # senza una tabella per grado.
    edges = np.sort(
        np.vstack([np.stack([f[:, i], f[:, (i + 1) % f.shape[1]]], axis=1) for i in range(f.shape[1])]),
        axis=1,
    )
    edges = np.unique(edges, axis=0)
    return float(np.median(np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)))


def align_to_axes(
    nodes: np.ndarray, reference: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Rototraslazione ai piani principali: spessore su x, lunghezza su y, altezza su z.

    La trasformazione e' restituita come matrice 4x4 e va salvata nei metadati:
    e' l'unico modo per riportare i risultati nel sistema originale dello scanner.

    Assunzione: lo scanner e' livellato, cioe' la z della nuvola in ingresso
    e' gia' il verticale reale e l'unica ambiguita' e' l'imbardata. Dalla
    Fase 5 questa non e' piu' una premessa che il codice dichiara e poi
    disattende: z e' imposto uguale a [0, 0, 1] per costruzione, e la sola
    direzione stimata (via PCA sulla proiezione orizzontale) e' lo spessore.
    Se la nuvola in ingresso e' fuori piombo (beccheggio o rollio), `BASE`
    diventa un taglio orizzontale a quota minima e non la base fisica del
    pezzo: la correzione sposta il difetto da "asse sbagliato" a "assunzione
    dichiarata e verificabile da chi fornisce la nuvola".

    `reference`, se fornito, e' l'insieme di punti su cui stimare centro e
    direzione dello spessore; in sua assenza si usano i nodi stessi. Il
    riferimento resta una proprieta della geometria e non del maglio: la PCA
    a due dimensioni pesa ogni punto della proiezione orizzontale allo stesso
    modo, mentre la densita dei nodi di volume dipende da dove TetGen ha
    infittito, cioe' da un artefatto del raffinamento e non dalla forma.

    Con z fisso l'effetto e' molto piu piccolo di quanto fosse con la PCA a
    tre dimensioni (quella dava, sugli stessi dati, 21,44 gradi sui nodi di
    volume e 15,33 sui soli nodi di bordo contro 0,45 sulla superficie).
    Misurato ora, con l'algoritmo attuale, su `muro` e `lab_crop`: la
    direzione dello spessore stimata sui nodi di bordo del volume coincide
    con quella sui vertici della superficie ricostruita (scarto nullo entro
    la precisione macchina su entrambi), e anche includendo i nodi interni lo
    scarto resta sotto 0,12 gradi (0,02 su `muro`, 0,11 su `lab_crop`). La
    misura vale sulle due geometrie disponibili e non e' una garanzia
    generale — resta un parametro esposto, non un dettaglio interno, perche'
    una nuvola con uno sbilanciamento di densita' piu marcato di questi due
    banchi potrebbe spostare la stima oltre quanto misurato qui.

    La trasformazione si applica comunque a tutti i nodi passati, e lo
    scostamento al primo ottante si calcola sui nodi trasformati, non sul
    riferimento: BASE deve corrispondere alla base del solido, quindi la
    quota minima a valere zero e' quella dei nodi.
    """
    points = np.asarray(nodes, dtype=np.float64)
    reference = points if reference is None else np.asarray(reference, dtype=np.float64)
    # Qui, e non solo in `build_node_sets`: questa e' la prima funzione che
    # `export_model` chiama, quindi e' il punto per cui passano davvero tutti i
    # chiamanti. Su zero nodi `np.ptp` piu' avanti solleva «zero-size array to
    # reduction operation maximum», che accusa una riduzione invece di dire
    # cosa manca -- e la guardia a valle non si raggiungeva mai perche' il
    # programma moriva prima. Le tre sorelle che leggono minimi e massimi
    # (`footprint_coverage`, `constraint_plan_extent`, `build_node_sets`)
    # ricevono i nodi da qui.
    if len(points) == 0 or len(reference) == 0:
        raise ValueError(
            "nessun nodo da allineare: la terna si ricava dall'ingombro della "
            "nuvola di riferimento, e su un insieme vuoto non esiste"
        )
    centre = reference.mean(axis=0)
    centred = points - centre
    centred_reference = reference - centre

    # z e' il verticale del sistema in ingresso, non una direzione stimata. Il
    # docstring di questa funzione ha sempre dichiarato che lo scanner e'
    # livellato e che l'unica ambiguita' e' l'imbardata; fino alla Fase 5 il
    # codice lo dichiarava e poi lasciava scegliere l'altezza a una PCA a tre
    # dimensioni. Su `lab_frame.pcd` quella scelta cadeva a 22,43 gradi dal
    # verticale, perche' le zapatas larghe e basse tirano la direzione
    # principale, e da li' il set BASE prendeva un piede su due.
    z_dir = np.array([0.0, 0.0, 1.0])

    # Lo spessore si sceglie fra le sole direzioni orizzontali: PCA a due
    # dimensioni sulla proiezione. Cosi' l'imbardata resta l'unica grandezza
    # stimata, e l'assegnazione dell'altezza non dipende piu' da come la massa
    # e' distribuita in quota.
    plane = centred_reference[:, :2]
    _, _, principal = np.linalg.svd(plane, full_matrices=False)
    extents = np.ptp(plane @ principal.T, axis=0)
    narrow = principal[int(np.argmin(extents))]
    x_dir = fix_sign(np.array([narrow[0], narrow[1], 0.0]))

    # y come prodotto vettoriale: la terna e' destrorsa per costruzione, quindi
    # il determinante vale +1 e non serve alcuna correzione a posteriori.
    y_dir = np.cross(z_dir, x_dir)

    rotation = np.stack([x_dir, y_dir, z_dir])

    aligned = centred @ rotation.T
    shift = aligned.min(axis=0)
    aligned = aligned - shift

    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ centre - shift

    metrics = {
        "extent": (aligned.max(axis=0) - aligned.min(axis=0)).tolist(),
        "transform": transform.tolist(),
    }
    return np.ascontiguousarray(aligned), transform, metrics


def set_tolerance(nodes: np.ndarray, tets: np.ndarray, factor: float) -> float:
    """Tolleranza dei set: un multiplo della spaziatura dei nodi sul bordo.

    L'euristica precedente derivava dal volume medio dell'elemento, cioe' da un
    artefatto del raffinamento e non dalla geometria: su una distribuzione a
    coda pesante la media e' dominata da pochi tetraedri enormi dell'interno
    (sul muro di riferimento mediana 14,6 mm^3 contro media 30.735 mm^3). Il
    costo e' misurato: `BASE` raggiungeva il 55,78% della superficie che poggia
    davvero a terra sul muro e il 34,76% su lab_crop.

    Le due candidate note sono state misurate e respinte, ciascuna da un
    numero. Il volume mediano dell'elemento da' 2,50 mm di tolleranza e un
    `BASE` di 9 nodi su 420.547. La selezione per direzione della normale, che
    e' lo standard dei preprocessori, e' catastrofica su una scansione con
    aperture: l'87,8% dell'area di lab_crop rivolta verso il basso e'
    l'intradosso dell'architrave, a 1493,5 mm su 1693,99 di altezza, e
    finirebbe in `BASE`.

    La scala giusta e' quella su cui la faccia ricostruita ondula, che e' la
    scala del campionamento e non quella del solido: misurata in spaziature,
    l'ondulazione trasferisce fra i due modelli entro un fattore 1,79, mentre
    misurata in frazioni dell'estensione entro un fattore 3,2. Misura completa,
    criterio di accettazione e sweep del fattore in
    docs/fase-1-tolleranza-set.md.
    """
    return factor * boundary_spacing(nodes, boundary_faces(tets))


def footprint_coverage(
    nodes: np.ndarray, boundary: np.ndarray, indices: np.ndarray, spacing: float
) -> float:
    """Frazione della superficie d'appoggio che l'insieme dato raggiunge davvero.

    Contare i nodi di un insieme non dice se copra la faccia che deve coprire:
    possono stare tutti ammucchiati in un angolo. 4738 nodi su una faccia
    coperta al 55,78% e 4738 su una coperta al 100% sono lo stesso numero.

    L'impronta viene divisa in celle quadrate di lato `4 * spacing`. Una
    colonna e' *a contatto* se il suo nodo di bordo piu basso cade entro il 2%
    dell'altezza dal minimo globale, cioe' se in quel punto il solido tocca
    davvero il piano d'appoggio; il risultato e' la frazione di colonne a
    contatto che contengono almeno un nodo dell'insieme.

    Il lato `4 * spacing` non e' arbitrario: con una cella larga quanto la
    spaziatura la griglia diventa piu fine dei triangoli della faccia inferiore
    (su quella del muro il p95 degli spigoli vale 47,4 mm contro una mediana di
    13,7) e una colonna su dieci risulta priva di nodi bassi per puro artefatto
    di griglia. Misurato, e scartato per questo.

    La misura ha tre parametri impliciti — il lato della cella, la banda di
    contatto e l'asse — ed e' per questo che serve come diagnosi e non come
    regola: la tolleranza dei set ne ha uno solo.
    """
    points = np.asarray(nodes, dtype=np.float64)
    edge = np.asarray(boundary, dtype=np.int64)
    low = points.min(axis=0)
    height = float(points[:, 2].max() - low[2])

    cell = np.floor((points[edge, :2] - low[:2]) / (4.0 * spacing)).astype(np.int64)
    # Chiave intera invece di np.unique(..., axis=0): stesso risultato, e su un
    # maglio a scala reale costa un terzo. Le celle sono non negative perche'
    # misurate dal minimo.
    key = cell[:, 0] * (cell[:, 1].max() + 1) + cell[:, 1]
    _, inverse = np.unique(key, return_inverse=True)
    columns = int(inverse.max()) + 1

    floor_height = np.full(columns, np.inf)
    np.minimum.at(floor_height, inverse, points[edge, 2])
    in_contact = floor_height <= low[2] + 0.02 * height
    if not in_contact.any():
        # Non raggiungibile dalla pipeline, e il motivo va scritto qui perche'
        # non e' ovvio: `low[2]` e' il minimo su **tutti** i nodi, mentre
        # `floor_height` e' il minimo sui soli nodi **di bordo**, per colonna.
        # Su un solido chiuso il nodo piu' basso e' di bordo, quindi la sua
        # colonna soddisfa sempre la condizione e almeno una colonna tocca.
        # L'unico modo di arrivare qui e' un `boundary` che non contiene il
        # nodo piu' basso, cioe' un errore del chiamante.
        #
        # Solleva invece di rendere 0.0: quello zero si legge come «l'insieme
        # non copre nulla dell'impronta», che e' una condizione vera, diversa
        # e gia' rappresentabile: confonderla con «non esiste un'impronta»
        # renderebbe indistinguibili un vincolo sbagliato e un ingresso rotto.
        raise ValueError(
            "nessuna colonna tocca il piano d'appoggio: i nodi di bordo non "
            "contengono il più basso del maglio, quindi l'impronta su cui "
            "misurare la copertura non esiste"
        )

    in_set = np.zeros(len(points), dtype=bool)
    in_set[np.asarray(indices, dtype=np.int64)] = True
    reached = np.bincount(inverse, weights=in_set[edge], minlength=columns) > 0
    return float(reached[in_contact].mean())


def constraint_plan_extent(nodes: np.ndarray, indices: np.ndarray) -> dict[str, float]:
    """Quanto dell'impronta del pezzo l'insieme vincolato attraversa, per asse.

    Nasce da un difetto misurato il 21/08/2026: su `lab_frame.pcd` il set BASE
    teneva 278 nodi ammucchiati in una toppa larga 233 mm su un pezzo lungo
    3144, il telaio penzolava da un piede solo, lo spostamento sotto peso
    proprio usciva a 15,25 mm invece di 0,0367 — e `footprint_coverage`
    dichiarava 1,0. Non per un bug: quella misura risponde a "quanta parte
    dell'appoggio che vedo e' vincolata", e vedeva un piede solo.

    Questa grandezza risponde all'altra domanda. Vale 1 per un muro, e vale 1
    **anche per un telaio a due piedi**, perche' i due piedi attraversano
    l'intera luce pur essendo vuoti in mezzo: non confonde "vuoto in mezzo" con
    "manca un appoggio". Crolla quando l'insieme tiene un angolo di una cosa
    larga.

    Non ha parametri impliciti — nessun lato di cella, nessuna banda di
    contatto, nessun asse da scegliere — ed e' per questo che puo' fare da
    regola dove `footprint_coverage` resta una diagnosi. La soglia e' larga
    perche' la grandezza e' quella giusta: sul caso misurato il divario e' fra
    0,074 e 1.

    `footprint_coverage` resta accanto: insieme dicono piu' di ciascuna da sola
    — "l'insieme copre tutto l'appoggio che vede, e vede il 7% del pezzo".
    """
    points = np.asarray(nodes, dtype=np.float64)
    scelti = points[np.asarray(indices, dtype=np.int64)]
    if len(scelti) == 0:
        return {"x": 0.0, "y": 0.0, "minimo": 0.0}
    rapporti: dict[str, float] = {}
    for asse, nome in ((0, "x"), (1, "y")):
        pezzo = float(np.ptp(points[:, asse]))
        # Un pezzo senza estensione su un asse non ha nulla da coprire su
        # quell'asse: 1.0, non una divisione per zero e non uno 0.0 che
        # sembrerebbe un vincolo mancante.
        rapporti[nome] = 1.0 if pezzo == 0.0 else float(np.ptp(scelti[:, asse]) / pezzo)
    rapporti["minimo"] = min(rapporti["x"], rapporti["y"])
    return rapporti


def build_node_sets(nodes: np.ndarray, tolerance: float) -> dict[str, np.ndarray]:
    """I sei set di faccia, sul modello gia allineato agli assi.

    `BASE` e `TOP` sono verificati **per costruzione dalla Fase 5**: `align_to_axes`
    impone l'asse z uguale al verticale della nuvola in ingresso invece di
    stimarlo con una PCA, quindi il minimo e' davvero la base del solido (fino
    alla Fase 5 l'affermazione era falsa su una geometria con appoggi larghi e
    bassi, dove la PCA sceglieva un asse a 22,43 gradi dal verticale).

    `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT` e `SIDE_RIGHT` sono invece **nomi di
    convenzione**, non identificazioni fisiche. Sono assegnati al minimo e al
    massimo di x e di y dopo l'allineamento, e nulla nella pipeline sa quale
    delle due grandi facce sia quella «anteriore» del muro reale, ne' quale sia
    il lato «sinistro»: il segno degli assi viene da una convenzione
    deterministica (`fix_sign`), scelta per la ripetibilita, non da un
    riferimento sul campo. La coppia e' quindi affidabile come coppia (le due
    facce opposte sono quelle giuste), l'attribuzione del singolo nome no.
    Chiunque usi questi set per confrontare il modello con misure fatte sul muro
    deve prima verificare l'orientamento sul file allineato.
    """
    points = np.asarray(nodes, dtype=np.float64)
    # Senza questa guardia numpy solleva «zero-size array to reduction
    # operation minimum», che accusa una riduzione invece di dire che non ci
    # sono nodi da cui ricavare i sei set. Chi legge quel messaggio non sa
    # cosa fare.
    if len(points) == 0:
        raise ValueError(
            "nessun nodo: i sei set di faccia si ricavano dal minimo e dal massimo "
            "delle coordinate, e su un insieme vuoto non esistono"
        )
    # Una coordinata non finita rende `NaN` il minimo e il massimo del proprio
    # asse, e ogni confronto contro `NaN` e' falso: i due set di quell'asse
    # escono **vuoti**, e il deck riceve un `*NSET` senza nodi senza che nulla
    # protesti. Misurato su tre nodi con una x a `NaN`: `FACE_FRONT` e
    # `FACE_BACK` entrambi vuoti, nessun errore.
    if not np.isfinite(points).all():
        raise ValueError(
            "coordinate non finite: il minimo e il massimo dell'asse diventano NaN "
            "e i suoi due set di faccia uscirebbero vuoti senza un errore"
        )
    low = points.min(axis=0)
    high = points.max(axis=0)
    # Dizionario letterale, non un accoppiamento per posizione con
    # NOMI_SET_DI_FACCIA: uno zip fra costante e tupla di criteri lega ogni
    # nome al criterio nella stessa posizione, e riordinare la costante
    # rilegherebbe silenziosamente un nome al criterio sbagliato -- qui il
    # nome sta nella stessa riga del suo criterio, non puo' scollegarsene.
    # Il prezzo e' che i sei nomi sono scritti due volte, qui e in
    # `config.NOMI_SET_DI_FACCIA`: l'accordo fra le due liste lo tengono due
    # test (`test_build_node_sets_ha_le_chiavi_della_costante` in
    # tests/test_abaqus.py e
    # `test_i_sei_nomi_dichiarati_sono_quelli_che_il_deck_fabbrica` in
    # tests/test_config.py), non il tipo.
    return {
        "BASE": np.flatnonzero(points[:, 2] <= low[2] + tolerance),
        "TOP": np.flatnonzero(points[:, 2] >= high[2] - tolerance),
        "FACE_FRONT": np.flatnonzero(points[:, 0] <= low[0] + tolerance),
        "FACE_BACK": np.flatnonzero(points[:, 0] >= high[0] - tolerance),
        "SIDE_LEFT": np.flatnonzero(points[:, 1] <= low[1] + tolerance),
        "SIDE_RIGHT": np.flatnonzero(points[:, 1] >= high[1] - tolerance),
    }


def write_vtu(
    path: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    element_type: str = "C3D4",
    point_data: dict[str, np.ndarray] | None = None,
    cell_data: dict[str, np.ndarray] | None = None,
) -> None:
    """Esportazione per la visualizzazione, delegata a meshio.

    meshio ha nomi propri per i tipi di cella, che non sono quelli del
    solutore: la tabella traduce, e un tipo non tradotto solleva invece di
    scrivere un file che nessun visualizzatore aprirebbe.

    `point_data`, dalla Fase 5, sono i campi per nodo che lo step 13 scrive
    (spostamenti e tensione equivalente per caso di carico, forme modali):
    assente lascia il file identico a prima, e i chiamanti gia' scritti (lo
    step 9 e `export_model`) non cambiano comportamento.

    `cell_data`, dalla Fase 8, sono i campi per **cella**: il telaio ha `N`,
    `V` e `M` per elemento e non per nodo (#138 Q2), e non c'era modo di
    scriverli. Un array per campo, lungo quanto le celle; meshio vuole una
    lista per blocco di celle e qui il blocco e' uno solo, quindi la lista la
    costruisce questa funzione invece di chiederla al chiamante.

    Assente lascia il file **valido e senza quei dati**: un `.vtu` senza
    `CellData` e' un file regolare che ogni visualizzatore apre, e dichiara con
    la propria struttura che quei campi non ci sono. Non si scrive un blocco
    di zeri, che si leggerebbe come «tutte le celle valgono zero».

    Una lunghezza sbagliata **solleva**: meshio scriverebbe il file lo stesso,
    e ParaView colorerebbe le celle con i valori sfalsati. E' un errore che si
    vede solo guardando, cioe' la classe che questo progetto esiste per non
    produrre.
    """
    import meshio

    # `tetra10` senza riordinare: la convenzione di VTK per i nodi di lato del
    # tetraedro quadratico coincide con quella di Abaqus, e `volume.tetrahedralize`
    # ha gia' portato la connettivita' in quella convenzione uscendo da TetGen.
    celle = {"C3D4": "tetra", "C3D10": "tetra10", "C3D8": "hexahedron",
             "C3D8I": "hexahedron", "C3D8R": "hexahedron"}
    if element_type not in celle:
        raise ValueError(f"tipo di elemento '{element_type}' senza corrispondente in meshio")

    connettivita = np.asarray(elements, dtype=np.int64)
    per_cella: dict[str, list[np.ndarray]] = {}
    for nome, valori in (cell_data or {}).items():
        campo = np.asarray(valori)
        # `campo.ndim == 0` prima di `len`: su un array a zero dimensioni `len`
        # alza «TypeError: len() of unsized object», che accusa una lunghezza
        # invece di dire che quel campo non e' un valore per cella, e il
        # messaggio parlante qui sotto non veniva mai raggiunto.
        if campo.ndim == 0 or len(campo) != len(connettivita):
            raise ValueError(
                f"il campo per cella '{nome}' ha forma {campo.shape} per "
                f"{len(connettivita)} celle: un .vtu scritto così assegnerebbe "
                "a ogni cella il valore di un'altra, e nessun visualizzatore "
                "protesterebbe"
            )
        per_cella[nome] = [campo]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    meshio.write(
        str(path),
        meshio.Mesh(
            np.asarray(nodes, dtype=np.float64),
            [(celle[element_type], connettivita)],
            point_data=point_data or {},
            cell_data=per_cella,
        ),
    )


def export_model(
    path_inp: Path,
    path_vtu: Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    cfg: AnalysisConfig,
    tet_cfg: TetConfig,
    reference: np.ndarray | None = None,
    element_type: str | None = None,
    element_surfaces: dict[str, list[tuple[int, int]]] | None = None,
    ties: tuple[tuple[str, str, str] | tuple[str, str, str, float], ...] = (),
    pressure: tuple[str, float] | None = None,
    carichi: CarichiConfig | None = None,
    selettori: dict[str, Selettore] | None = None,
    regioni: dict[str, tuple[np.ndarray, Material]] | None = None,
) -> dict[str, object]:
    """Step 11: allinea, costruisce i set, scrive il deck e il file di visualizzazione.

    `regioni` sono gli elementi di ciascuna regione col materiale della sua
    sezione, misurati da `core/attribuzione.py` e passati di qui a `write_inp`.
    Gli indici e non le coordinate: `align_to_axes` sposta i nodi e non l'ordine degli elementi,
    quindi l'attribuzione si misura fuori di qui, sui nodi non allineati che
    la pipeline ha in mano e nello stesso riferimento in cui il prior misura.

    `carichi` e' un parametro a se', non un campo di `cfg`: dalla Fase 5 i tre
    casi di carico oltre al peso proprio (spinta orizzontale, carico in
    sommita', modale) stanno nel blocco di primo livello `PipelineConfig.
    carichi`, separato da `analysis` perche' altrimenti cambiavano l'impronta
    di sweep e i 22 record dei registri smettevano di derivare dalla propria
    configurazione. E' lo stesso ruolo che `tet_cfg` gia' ha accanto a `cfg`.

    `reference` sono i punti su cui stimare la terna: la pipeline passa i
    vertici della superficie da cui la mesh e' stata generata, perche' il
    sistema di riferimento e' una proprieta della geometria e non del maglio.
    Senza riferimento si ripiega sui nodi di bordo della mesh di volume, che
    e' il comportamento precedente e resta valido sulle geometrie di prova,
    dove i nodi coincidono con la superficie.

    Su dati reali il ripiego resta un compromesso, ma non piu' per il motivo
    di prima: con z fisso (vedi `align_to_axes`) un riferimento povero non
    puo' piu' scambiare l'asse altezza, quindi la caduta di `BASE` da 18.020
    nodi a 874 misurata prima della Fase 5 non e' piu' possibile per
    costruzione. Il motivo per passare `reference` ora e' piu' piccolo ma
    resta reale: la PCA a due dimensioni che sceglie lo spessore pesa ogni
    punto della proiezione orizzontale allo stesso modo, e i nodi di bordo
    della mesh di volume sono piu' fitti dei vertici della superficie dove
    TetGen ha suddiviso le facce di ingresso. Misurato su `muro` e
    `lab_crop` (dettaglio in `align_to_axes`), l'effetto oggi e' sotto 0,12
    gradi, insufficiente a spostare l'assegnazione degli assi su queste due
    geometrie, dove le due estensioni orizzontali differiscono di un fattore
    4,8 e 12,6. Su un'impronta piu' vicina al quadrato il margine e' minore e
    lo stesso scarto potrebbe pesare di piu': passare `reference` non costa
    nulla, perche' la pipeline ha gia' i vertici della superficie pronti, ed
    elimina questa fonte di deriva invece di scommettere che resti sempre
    piccola.
    """
    from meshrec.core.quality import element_volumes

    tipo = tet_cfg.element if element_type is None else element_type
    if tipo not in NODI_PER_ELEMENTO:
        raise ValueError(f"tipo di elemento '{tipo}' sconosciuto")
    attesi = NODI_PER_ELEMENTO[tipo]
    elements = np.asarray(elements, dtype=np.int64)
    if elements.shape[1] != attesi:
        raise ValueError(
            f"{tipo} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: un deck scritto così non è leggibile da alcun solutore"
        )
    # Qui e non solo in `write_inp`, che sta in fondo a questa funzione e non
    # viene mai raggiunto col maglio vuoto: `boundary_faces` non trova bordo e
    # `align_to_axes` solleva per primo su una nuvola di riferimento vuota.
    if len(elements) == 0:
        raise ValueError(MAGLIO_VUOTO)

    # Nome distinto dalla funzione pubblica boundary_faces: qui e' una
    # variabile locale, non va confusa col contratto che questo task ha
    # promosso (vedi Task 5, 7, 8).
    bordo_facce = boundary_faces(elements)
    boundary = np.unique(bordo_facce)
    if reference is None:
        reference = np.asarray(nodes, dtype=np.float64)[boundary]
    aligned, transform, align_metrics = align_to_axes(nodes, reference=reference)
    spacing = boundary_spacing(aligned, bordo_facce)
    tolerance = cfg.set_tolerance_factor * spacing
    node_sets = build_node_sets(aligned, tolerance)
    # Prima dell'indicizzazione, non dopo: il controllo con messaggio civile
    # di `write_inp` non veniva mai raggiunto, perche' qui sotto `KeyError`
    # arrivava per primo -- e arrivava dopo che tutta la mesh era stata
    # costruita.
    if cfg.fixed_nset not in node_sets:
        raise ValueError(
            f"il set vincolato '{cfg.fixed_nset}' non e fra gli insiemi che il modello "
            f"offre ({sorted(node_sets)}). Il caso non c'entra: `AnalysisConfig.fixed_nset` "
            "è un NomeSetDiFaccia e riscrive da sé i sei nomi nel proprio caso "
            "canonico, quindi ciò che arriva qui è un nome diverso, non un 'base' "
            "scritto minuscolo"
        )
    if len(node_sets[cfg.fixed_nset]) == 0:
        raise ValueError(f"il set vincolato '{cfg.fixed_nset}' e vuoto: tolleranza {tolerance:.3f} mm troppo stretta")

    # Risolti sui nodi **allineati**: e' il sistema di riferimento del deck e
    # di wall_model.vtu. L'estensione in quel sistema esce qui sotto in
    # "extent", e la bbox dei nodi presi in "selettori", perche' l'operatore
    # possa collocare un selettore senza indovinare. Un selettore degenere
    # (zero nodi, tutti i nodi, nodo troppo lontano) solleva da dentro
    # `selezione.risolvi_tutti`: non si intercetta qui, un `try` lo
    # trasformerebbe in un deck silenziosamente sbagliato.
    nset_selettori = selezione.risolvi_tutti(selettori or {}, aligned, elements, node_sets)

    # Un carico sul selettore che coincide, in tutto o in parte, col set
    # vincolato non sposta nulla: la sua quota finisce in reazione, non in
    # spostamento, e ne' `ccx` ne' la guardia sul set vuoto se ne accorgono
    # (misurato sulla corsa dimostrativa: il momento era su BASE ed e' stato
    # spostato senza che nulla lo segnalasse). Tutto dentro e' un errore di
    # modellazione dichiarato come tale; in parte e' un avviso col conteggio,
    # perche' potrebbe essere voluto (un selettore che tocca il bordo).
    vincolati = set(np.asarray(node_sets[cfg.fixed_nset], dtype=np.int64).tolist())
    # Coppie (nome_del_carico, origine, indici) da controllare: CARICO_TOP in
    # piu' rispetto a prima, perche' cita un *NSET esistente per nome invece
    # di un selettore risolto e non passava da questo stesso ciclo (misurato:
    # un carico_sommita su BASE anziche' TOP finiva in reazione senza un solo
    # avviso).
    carichi_da_controllare: list[tuple[str, str, np.ndarray]] = []
    if carichi is not None:
        if carichi.carico_sommita is not None and carichi.carico_sommita.nset in node_sets:
            carichi_da_controllare.append((
                "CARICO_TOP", carichi.carico_sommita.nset, node_sets[carichi.carico_sommita.nset],
            ))
        # Anche i distribuiti (#91): una pressione il cui selettore cade tutta
        # sul set vincolato non solleva, non avvisa, e il modello passa i sette
        # verdetti senza rispondere al carico. I tre campi hanno la stessa
        # forma, quindi e' lo stesso ciclo.
        for carico in (*carichi.posizionati, *carichi.distribuiti):
            if carico.selettore in nset_selettori:  # altrimenti write_inp rifiuta con messaggio piu' completo
                carichi_da_controllare.append((carico.nome, carico.selettore, nset_selettori[carico.selettore]))
    # Il conteggio nasce qui, dove compone la stringa dell'avviso, e va reso
    # anche in `metrics.json`: un avviso su stderr si perde con la finestra
    # del terminale, mentre `forza_effettiva` e `momento_effettivo` restano
    # nel file a dichiarare per intero una risultante di cui il modello
    # applica solo una frazione.
    bloccati_per_carico: dict[str, int] = {}
    for nome, origine, indici in carichi_da_controllare:
        indici_carico = set(np.asarray(indici, dtype=np.int64).tolist())
        bloccati = indici_carico & vincolati
        # Prima del ritorno anticipato: zero e' un valore, e una chiave
        # assente non si distingue da una versione che non contava.
        bloccati_per_carico[nome] = len(bloccati)
        if not bloccati:
            continue
        if indici_carico <= vincolati:
            raise ValueError(
                f"il carico '{nome}' agisce sull'insieme '{origine}', che coincide "
                f"per intero con l'insieme vincolato '{cfg.fixed_nset}': tutti i "
                f"{len(indici_carico)} nodi presi sono bloccati dal vincolo, il carico "
                "finirebbe tutto in reazione senza spostare nulla"
            )
        warnings.warn(
            f"il carico '{nome}' sull'insieme '{origine}' include "
            f"{len(bloccati)} dei suoi {len(indici_carico)} nodi anche nell'insieme "
            f"vincolato '{cfg.fixed_nset}': quella quota finisce in reazione, non in "
            "spostamento",
            CaricoSulVincoloWarning,
            stacklevel=2,
        )

    # La guardia sul set vuoto era cieca su tutto il resto: un `BASE` da 9 nodi
    # produce un deck formalmente valido per un modello di fatto non vincolato,
    # e nessuna metrica confrontava la taglia dell'insieme con la faccia che
    # deve coprire. La soglia e' la meta', che non e' un numero tarato ma
    # un'affermazione qualitativa: quando la superficie d'appoggio vincolata e'
    # meno di quella libera, il modello non e' vincolato in alcun senso utile.
    # Avrebbe segnalato entrambe le corse sotto l'euristica precedente
    # (55,78% sul muro e 34,76% su lab_crop), e tace sotto quella attuale
    # (100,00% e 98,93%).
    coverage = footprint_coverage(aligned, boundary, node_sets[cfg.fixed_nset], spacing)
    if coverage <= 0.5:
        warnings.warn(
            f"l'insieme vincolato '{cfg.fixed_nset}' raggiunge il {coverage:.2%} della "
            f"superficie d'appoggio con una tolleranza di {tolerance:.3f} mm: il modello "
            "è vincolato su una chiazza, non sulla base. Alza "
            "analysis.set_tolerance_factor o verifica la geometria.",
            UnconstrainedModelWarning,
            stacklevel=2,
        )

    resoconto_carichi = write_inp(
        path_inp,
        aligned,
        elements,
        node_sets=node_sets,
        material=cfg.material,
        element_type=tipo,
        fixed_nset=cfg.fixed_nset,
        gravity=cfg.gravity,
        step_name=cfg.step_name,
        element_surfaces=element_surfaces,
        ties=ties,
        pressure=pressure,
        carichi=carichi,
        nset_selettori=nset_selettori,
        regioni=regioni,
    )
    nomi_distribuiti = (
        frozenset() if carichi is None
        else frozenset(carico.nome for carico in carichi.distribuiti)
    )
    for nome, quanti in bloccati_per_carico.items():
        resoconto_carichi[nome]["nodi_sul_vincolo"] = quanti
    write_vtu(path_vtu, aligned, elements, element_type=tipo)

    volume = float(np.abs(element_volumes(aligned, elements)).sum())
    return {
        "transform": transform.tolist(),
        "extent": align_metrics["extent"],
        "boundary_spacing": float(spacing),
        "set_tolerance": float(tolerance),
        "fixed_nset_coverage": float(coverage),
        "constraint_plan_extent": constraint_plan_extent(aligned, node_sets[cfg.fixed_nset]),
        "node_sets": {name: int(len(indices)) for name, indices in node_sets.items()},
        "selettori": {
            nome: {
                "tipo": (selettori or {})[nome].tipo,
                "nodi": int(indici.size),
                "bbox": [
                    aligned[indici].min(axis=0).tolist(),
                    aligned[indici].max(axis=0).tolist(),
                ],
            }
            for nome, indici in nset_selettori.items()
        },
        # Due chiavi e non una: i distribuiti (#10) hanno un resoconto di forma
        # diversa -- area e efficienza della superficie, non nodi e quote -- e
        # infilarli sotto un nome che dice «posizionati» renderebbe falso un
        # nome che qualcuno legge. La vecchia chiave resta quella di prima.
        "carichi_posizionati": {
            nome: valore for nome, valore in resoconto_carichi.items()
            if nome not in nomi_distribuiti
        },
        "carichi_distribuiti": {
            nome: valore for nome, valore in resoconto_carichi.items()
            if nome in nomi_distribuiti
        },
        "volume": volume,
        "mass": volume * cfg.material.density,
        "element_type": tipo,
        "inp": str(path_inp),
        "vtu": str(path_vtu),
        "element_surfaces": {
            nome: len(coppie) for nome, coppie in (element_surfaces or {}).items()
        },
        "surface_area": {
            nome: surface_area(aligned, elements, coppie, tipo)
            for nome, coppie in (element_surfaces or {}).items()
        },
        "ties": [nome for nome, _dipendente, _indipendente, *_tolleranza in ties],
        "pressure": None if pressure is None else {"surface": pressure[0], "value": pressure[1]},
        "casi_di_carico": [nome for nome in (
            cfg.step_name,
            None if carichi is None or carichi.spinta is None else "SPINTA_ORIZZONTALE",
            None if carichi is None or carichi.carico_sommita is None else "CARICO_TOP",
            *(() if carichi is None else tuple(c.nome for c in carichi.posizionati)),
            # Dopo i posizionati e prima del modale, nello stesso ordine in cui
            # `write_inp` scrive i passi: questa lista e' la promessa che
            # `solve.risolvi` usa per dare un nome ai blocchi del `.frd`, e un
            # ordine diverso da quello del deck scambierebbe i risultati.
            *(() if carichi is None else tuple(c.nome for c in carichi.distribuiti)),
            # Le combinazioni entrano DOPO tutti i casi singoli (#146), nello
            # stesso punto in cui `write_inp` scrive i loro passi, e prima del
            # modale: `risolvi` scarta il modale come **ultima** voce della
            # lista, e una combinazione dietro di lui non troverebbe piu' il
            # proprio blocco.
            *(() if carichi is None else tuple(c.nome for c in carichi.combinazioni)),
            None if carichi is None or carichi.modale is None else "MODALE",
        ) if nome is not None],
    }
