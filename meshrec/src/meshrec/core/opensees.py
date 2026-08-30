"""Scrittura del `.tcl` di OpenSees e lettura delle sue uscite.

Il gemello di `core/abaqus.py`, e non lo e' fino in fondo: **OpenSees non ha un
formato di deck**. CalculiX legge un `.inp`, cioe' un file di dati; OpenSees si
comanda, e il modello vive nella memoria dell'interprete. L'artefatto
riproducibile non e' quindi il modello, e' **lo script che lo costruisce**
(`docs/validazione/ricerca-opensees-e-armature.md`, §4.1). Il file che questo
modulo scrive resta pero' lo stesso genere di cosa: testo che chiunque abbia la
distribuzione standard puo' rileggere ed eseguire, che era la ragione dichiarata
per scartare `openseespy` (#139 Q2).

Tre fatti su OpenSees 3.8.0 misurati eseguendolo su questa macchina il
30/08/2026, non letti dal manuale, e su cui questo modulo poggia:

- **`-GJ` e' obbligatorio nelle sezioni a fibre 3D.** Senza, OpenSees stampa
  «WARNING - no torsion specified for 3D fiber section, use -GJ or -torsion» e
  lo script **si ferma** alla card della sezione: non e' un avviso, e' una
  morte.
- **Il codice d'uscita non e' il segnale.** OpenSees esce con codice 0 anche
  quando lo script muore su un errore fatale (misurato su un `element truss` con
  nodo e materiale inesistenti). Chi legge le uscite guarda i file, e chi
  verifica il binario guarda l'uscita: mai il codice.
- **Il marcatore di avviso e' `WARNING`, senza asterisco**, dove `ccx` scrive
  `*WARNING`. Contare il marcatore di CalculiX sull'uscita di OpenSees darebbe
  zero avvisi qualunque cosa sia successa, cioe' un verdetto verde per
  costruzione. Vedi `solve.CONTROLLI_PER_MODELLO["avvisi"]`.

**Che cosa questo modulo non scrive, e a chi appartiene.** I carichi diversi dal
peso proprio non ci sono, e non e' una dimenticanza: il contratto `Telaio`
(§4.7 del sequenziamento) porta nodi, elementi, giunzioni e materiali, e
nient'altro. Le azioni e le combinazioni sono del ramo G (§4.9). Uno script che
aprisse un passo senza carichi produrrebbe spostamenti nulli e sette verdetti
verdi su un modello mai caricato, che e' il falso peggiore che questo progetto
possa rendere: `scrivi_tcl` si ferma e lo dice.
"""

from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from meshrec.core import solve
from meshrec.core.config import GRAVITY_MM_S2, AnalysisConfig, Modale

if TYPE_CHECKING:  # pragma: no cover
    from meshrec.core.config import SolutoreConfig
    # `core/telaio.py` lo scrive il ramo D dell'onda 3. Le annotazioni di
    # questo modulo sono stringhe (`from __future__ import annotations`), e
    # l'import vero non gira mai: lo scrittore legge solo i campi che §4.7
    # dichiara, e nessun altro.
    from meshrec.core.telaio import Telaio

# `WARNING`, e non `*WARNING` di CalculiX. Vedi la nota in testa al modulo.
MARCA_AVVISO = "WARNING"

# Il nome che il caso di peso proprio deve portare, letto dal predefinito che
# `AnalysisConfig` dichiara e non riscritto qui: un secondo "GRAVITA" scritto a
# mano divergerebbe dal primo in silenzio. Chi configura `step_name` passa il
# proprio nome a `scrivi_tcl`.
_NOME_PESO_PROPRIO = str(AnalysisConfig.model_fields["step_name"].default)

# Punti d'integrazione per elemento a forze. Cinque e' il numero d'uso per un
# `forceBeamColumn` a sezione costante: sotto i tre l'integrazione di
# Gauss-Lobatto non coglie l'andamento del momento sull'asta, sopra i sette non
# cambia nulla su una sezione che non varia lungo la stazione.
# ponytail: costante e non parametro. Diventa un parametro il giorno in cui la
# sezione varia dentro la stazione, che oggi non succede -- il prior misura una
# sezione per fetta e ogni stazione e' una fetta (#142 Q2).
_PUNTI_INTEGRAZIONE = 5

# Suddivisioni della `patch rect` del calcestruzzo, lungo i due assi della
# sezione. Dieci per dieci sono cento fibre per sezione: abbastanza da
# rappresentare un diagramma di tensione lineare senza che il conto delle fibre
# domini il costo dell'analisi.
# ponytail: e' un parametro di discretizzazione, e a rigore vorrebbe uno studio
# di convergenza come `TetConfig`. Non lo fa qui perche' oggi i materiali sono
# elastici (vedi `_materiali`), e su una sezione elastica il numero di fibre non
# sposta il risultato: la rigidezza integrata di un rettangolo elastico e'
# esatta a qualunque suddivisione. Il giorno in cui i materiali diventano non
# lineari, questo numero va misurato.
_SUDDIVISIONI_PATCH = 10

# Un versore della sezione quasi parallelo all'asse dell'asta non definisce un
# piano: `geomTransf` ne uscirebbe degenere. Il coseno e' quello di circa 2,5
# gradi.
_COSENO_MASSIMO_VECXZ = 0.999

# Quanto il verso di `e1` puo' discostarsi dall'asse locale y che OpenSees
# deriva da (asse, `e2`). Stesso coseno del limite qui sopra, circa 2,5 gradi:
# oltre, la terna che il prior ha stimato non e' quella che il `.tcl`
# costruisce, e la sezione a fibre esce ruotata o specchiata.
_COSENO_MINIMO_E1 = _COSENO_MASSIMO_VECXZ


def _nome_uscita(caso: str, cosa: str) -> str:
    """Il nome del file che un registratore scrive, e che il lettore ricerca.

    Un posto solo: due nomi che divergono darebbero uno scrittore che scrive e
    un lettore che non trova, senza che nulla sollevi -- il file mancante si
    legge come «caso non calcolato».

    Il nome del caso entra nel nome del file, ed e' il secondo motivo per cui
    `solve.valida_casi_di_carico` rifiuta due casi che differiscono solo per le
    maiuscole: su un filesystem che non distingue il caso il secondo
    sovrascriverebbe le uscite del primo.
    """
    return f"{caso}_{cosa}.out"


NOME_MASSA_MODALE = "massa_modale.out"

# Lo script e il registro della corsa, dentro la cartella della corsa. Il
# registro porta lo stesso nome di quello di CalculiX (`solve.risolvi`): una
# corsa risolve un solido oppure un telaio, mai tutti e due, e chi va a
# guardare che cosa ha detto il solutore cerca un nome solo.
NOME_TCL = "13_telaio.tcl"
NOME_REGISTRO = "13_solver.log"

# Il marcatore di fine corsa, e il file in cui il `.tcl` lo scrive.
#
# Serve perche' il codice d'uscita di OpenSees non e' il segnale (misurato: 0
# anche su uno script che muore su un errore fatale) e perche' i registratori
# scrivono a ogni passo: una corsa uccisa a meta' lascia sul disco file pieni e
# ben formati, che sono l'ultimo stato e non un risultato. Le due guardie di
# `_ultima_riga` vedono il singolo file troncato; questo marcatore e' l'unico
# modo di dire che la **corsa** e' finita.
NOME_FINE = "fine.out"
MARCA_FINE = "MESHREC_FINE"

# Il nome di un'uscita modale, e non la glob `modo_*.out`: quella cattura anche
# `modo_forze.out` e `modo_spostamenti.out`, cioe' le uscite di un caso di
# carico chiamato `modo`, e il numero del modo si leggeva da «forze».
_USCITA_MODALE = re.compile(r"modo_(\d+)\.out")


def conta_avvisi(uscita: str) -> int:
    """Gli avvisi nell'uscita di OpenSees, da dare a `solve.controlla_avvisi`.

    Funzione e non letterale sparso perche' il marcatore non e' lo stesso dei
    due solutori, e sbagliarlo non fa rumore: conta zero e il verdetto passa.
    """
    return uscita.upper().count(MARCA_AVVISO)


def _costante_torsionale(b: float, h: float) -> float:
    """Costante di torsione di Saint-Venant di una sezione rettangolare piena.

    Roark, *Formulas for Stress and Strain*, Tab. 10.1 caso 4:
    `K = a*t^3*(1/3 - 0.21*(t/a)*(1 - t^4/(12*a^4)))`, con `a` il lato lungo e
    `t` il corto. **Non** e' il momento polare `Ip = (b*h^3 + h*b^3)/12`, che
    per un rettangolo sovrastima la rigidezza torsionale -- fino a piu' del
    doppio su una sezione allungata -- perche' vale per la sola sezione
    circolare.

    Serve perche' `-GJ` e' obbligatorio (vedi la nota in testa al modulo) e
    perche' un valore inventato la' dentro e' un numero plausibile e sbagliato:
    OpenSees lo accetta senza dire nulla e la torsione del telaio esce di
    conseguenza.
    """
    lungo, corto = (b, h) if b >= h else (h, b)
    rapporto = corto / lungo
    return lungo * corto**3 * (1.0 / 3.0 - 0.21 * rapporto * (1.0 - rapporto**4 / 12.0))


def _versore(v: np.ndarray) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    norma = float(np.linalg.norm(a))
    if norma == 0.0:
        raise ValueError("versore nullo: non definisce una direzione")
    return a / norma


def _coricata(delta: np.ndarray) -> bool:
    """Un'asta e' coricata se il suo asse e' piu' orizzontale che verticale.

    Non e' una tolleranza sulla quota, e' il ruolo dell'asta: quarantacinque
    gradi e' la bisettrice, cioe' l'unica soglia che non si sceglie -- di qua
    l'asta si posa, di la' l'asta si alza. Sul telaio sintetico i due traversi
    stanno a 0,36 e 0,53 gradi dall'orizzontale e i due montanti a 89,60 e
    89,94, misurati il 30/08/2026: nessuno dei quattro e' vicino alla
    bisettrice, e nessuno cambia ruolo se la si sposta di dieci gradi.
    """
    return abs(float(delta[2])) < float(np.hypot(delta[0], delta[1]))


def _al_piede(nodi: np.ndarray, elementi) -> np.ndarray:
    """Gli indici dei nodi che poggiano a terra, dedotti dalla struttura.

    **Nessuna tolleranza sulla quota**, e la ragione e' il difetto che questa
    funzione sostituisce. Il criterio precedente era «entro 1e-4 dell'altezza
    dalla quota minima»: sul telaio sintetico il traverso di fondazione ha
    l'asse fuori piano di 0,53 gradi, i suoi ventuno nodi si spandono di 14,94
    mm in quota, la tolleranza ne valeva 0,191, e il telaio da ottanta nodi
    usciva incastrato in **uno** solo (misurato il 30/08/2026). Quello scarto
    non e' rumore di stima: e' il fuori piombo che il rilievo ha misurato,
    cioe' precisamente cio' che questo programma esiste per conservare. Una
    soglia che lo tratta come rumore va allargata finche' il caso torna, ed e'
    la soglia decisa dopo aver visto il risultato.

    Il piede si deduce invece da com'e' fatta la struttura, con due sole
    domande e nessun numero da tarare:

    1. **La membratura coricata che tocca il punto piu' basso ci poggia per
       tutta la propria lunghezza.** E' la trave di fondazione: si parte dal
       nodo di quota minima -- un `argmin`, non un confronto con una soglia --
       e si cammina lungo le sole aste coricate. Comunque il rilievo l'abbia
       trovata inclinata, la trave sta a terra da un capo all'altro.
    2. **Ogni nodo da cui la struttura sale soltanto, e sale in piedi.** E' il
       piede di un montante: sotto non prosegue niente, quindi o poggia o
       penzola. La seconda condizione -- che le aste che ne partono siano in
       piedi -- esclude la punta di uno sbalzo: l'estremo libero di un traverso
       e' il punto piu' basso *del traverso*, ma la struttura ci arriva da
       sopra e non ci poggia sopra.

    Il nodo di quota minima e' sempre nell'insieme (e' il punto di partenza
    del cammino), quindi il telaio non resta mai senza vincoli.
    """
    quote = nodi[:, 2]
    vicini: dict[int, list[tuple[int, bool]]] = {}
    for elemento in elementi:
        coricata = _coricata(nodi[elemento.nodo_j] - nodi[elemento.nodo_i])
        vicini.setdefault(elemento.nodo_i, []).append((elemento.nodo_j, coricata))
        vicini.setdefault(elemento.nodo_j, []).append((elemento.nodo_i, coricata))

    a_terra = {int(np.argmin(quote))}
    da_visitare = list(a_terra)
    while da_visitare:
        for altro, coricata in vicini.get(da_visitare.pop(), ()):
            if coricata and altro not in a_terra:
                a_terra.add(altro)
                da_visitare.append(altro)

    a_terra.update(
        nodo
        for nodo, intorno in vicini.items()
        if all(not coricata and quote[altro] > quote[nodo] for altro, coricata in intorno)
    )
    return np.array(sorted(a_terra), dtype=np.int64)


def _controlla_telaio(telaio: "Telaio") -> tuple[np.ndarray, np.ndarray]:
    """`(nodi, indici dei nodi al piede)`, o il motivo per cui non si scrive.

    Tre rifiuti, e nessuno dei tre e' teorico. Un `.tcl` senza elementi e' un
    file che OpenSees legge, esegue e su cui non calcola nulla: `analyze 1`
    torna 0 e ogni verdetto a valle guarda uscite vuote. Un nodo solo non e'
    un'asta. Un modello dove ogni nodo cade al piede e' interamente vincolato,
    e non ha nulla da risolvere.
    """
    nodi = np.asarray(telaio.nodi, dtype=np.float64)
    if not np.isfinite(nodi).all():
        raise ValueError(
            "il telaio ha coordinate non finite: la quota minima diventa NaN, "
            "ogni confronto contro NaN è falso, e l'insieme dei piedi uscirebbe "
            "vuoto. Il .tcl avrebbe zero righe `fix` e un resoconto che "
            "dichiara nodi_vincolati = 0 e peso_proprio = nan senza fermarsi"
        )
    if not telaio.elementi:
        raise ValueError(
            "il telaio non ha nessun elemento: un .tcl scritto così sarebbe un "
            "file che OpenSees esegue senza calcolare niente, e i verdetti a "
            "valle leggerebbero uscite vuote come se fossero risultati"
        )
    if len(nodi) < 2:
        raise ValueError(
            f"il telaio ha un nodo solo ({len(nodi)} nodi): non c'è un'asta da "
            "scrivere"
        )
    al_piede = _al_piede(nodi, telaio.elementi)
    if len(al_piede) == len(nodi):
        raise ValueError(
            "ogni nodo del telaio poggia a terra: il piede prende tutto e non "
            "resta nessun nodo libero da calcolare. Il modello è degenere, non "
            "è un telaio"
        )
    return nodi, al_piede


def _materiali(telaio: "Telaio") -> tuple[list[str], dict[int, tuple[int, int]]]:
    """Le card dei materiali e, per membratura, i tag `(calcestruzzo, acciaio)`.

    **Elastici, e va dichiarato perché.** `MaterialeDichiarato` porta `f_k` e la
    sua `veste`, cioè quanto vale la resistenza e se il numero è caratteristico
    o già ridotto; con quei due si scriverebbe un `Concrete01` o uno `Steel01`.
    Non si fa qui, e non per pigrizia: §8.2 del sequenziamento dichiara **non
    decisa** la casella che dice che cosa il programma fa con `f_cd`/`f_yd`
    quando il materiale è dichiarato `veste = "gia_ridotta"`, e sceglierla qui
    sarebbe deciderla di nascosto. I sette verdetti che questo modulo serve --
    equilibrio, autovalori, spostamenti, massa modale -- sono tutti definiti
    sull'analisi elastica lineare, e nessuno di loro legge una resistenza.

    Un `uniaxialMaterial Elastic` per membratura e per famiglia, non uno per
    elemento: le venti stazioni di una membratura condividono i materiali della
    propria sezione, e ventitré card identiche sarebbero solo rumore in un file
    che qualcuno deve poter rileggere.
    """
    righe: list[str] = []
    tag_per_membratura: dict[int, tuple[int, int]] = {}
    prossimo = 1
    for membratura in sorted({elemento.membratura for elemento in telaio.elementi}):
        sezione = telaio.materiali.get(membratura)
        if sezione is None:
            raise ValueError(
                f"la membratura {membratura} non ha una sezione dichiarata in "
                f"telaio.materiali: dichiarate {sorted(telaio.materiali)}. Il "
                "telaio non ha materiali per quell'asta e non si scrive un "
                "modello che ricada su un predefinito"
            )
        calcestruzzo = sezione.calcestruzzo_confinato.material
        acciaio = sezione.acciaio.material
        righe.append(
            f"uniaxialMaterial Elastic {prossimo} {calcestruzzo.young:.10g}"
            f"    ;# {calcestruzzo.name}, membratura {membratura}"
        )
        righe.append(
            f"uniaxialMaterial Elastic {prossimo + 1} {acciaio.young:.10g}"
            f"    ;# {acciaio.name}, membratura {membratura}"
        )
        tag_per_membratura[membratura] = (prossimo, prossimo + 1)
        prossimo += 2
    return righe, tag_per_membratura


def _massa_lineare(telaio: "Telaio", elemento) -> float:
    """Massa per unita' di lunghezza di un'asta, **acciaio compreso**.

    Le barre pesano, e il modulo le ignorava mentre la sezione a fibre le
    include nella rigidezza: su 4 barre da 16 mm in una sezione 300x200 sono il
    2,79% di peso mancante. Una massa che non e' quella del pezzo boccia un
    modello sano su `controlla_reazioni`, e sposta le frequenze di un'analisi
    modale che nessuno riguarda.

    L'acciaio **sostituisce** il calcestruzzo dove sta: e' il peso vero del
    pezzo. La sezione a fibre invece somma le barre alla `patch` che copre
    tutto il rettangolo, quindi la rigidezza sovrastima di poco -- e' la
    convenzione della sezione a fibre, e non e' questa funzione a doverla
    correggere.
    """
    base, altezza = float(elemento.sezione[0]), float(elemento.sezione[1])
    area_barre = sum(math.pi * float(b.diametro) ** 2 / 4.0 for b in elemento.barre)
    sezione = telaio.materiali[elemento.membratura]
    return (
        (base * altezza - area_barre) * float(sezione.calcestruzzo_confinato.material.density)
        + area_barre * float(sezione.acciaio.material.density)
    )


def _peso_nodale(telaio: "Telaio", nodi: np.ndarray) -> np.ndarray:
    """Il peso proprio ripartito sui nodi, meta' per estremo di ogni asta.

    **Nodale e non `eleLoad -type -beamUniform`**, che sarebbe la forma
    idiomatica. Due ragioni, e la seconda decide. La prima: `-beamUniform` vuole
    le componenti nel riferimento **locale** dell'asta, quindi la gravita'
    globale andrebbe proiettata elemento per elemento, e una proiezione
    sbagliata da' un carico plausibile in una direzione sbagliata. La seconda:
    `controlla_reazioni` confronta la somma delle reazioni con il peso che la
    geometria dichiara (`_massa_lineare` per la lunghezza, per `g`), e la
    ripartizione nodale rende quell'uguaglianza **esatta** -- il carico
    applicato a un nodo vincolato entra intero nella sua reazione. E' anche il
    motivo per cui la casella `reazioni` di `solve.CONTROLLI_PER_MODELLO` dice
    che sul telaio il termine correttivo di `_quota_tributaria_gravita` vale
    zero invece di essere un'altra formula.
    """
    peso = np.zeros(len(nodi), dtype=np.float64)
    for elemento in telaio.elementi:
        lunghezza = float(np.linalg.norm(nodi[elemento.nodo_j] - nodi[elemento.nodo_i]))
        meta = 0.5 * _massa_lineare(telaio, elemento) * lunghezza * GRAVITY_MM_S2
        peso[elemento.nodo_i] += meta
        peso[elemento.nodo_j] += meta
    return peso


def _sezioni_ed_elementi(telaio: "Telaio", nodi: np.ndarray, tag_materiale) -> list[str]:
    righe: list[str] = []
    for indice, elemento in enumerate(telaio.elementi, start=1):
        base, altezza = float(elemento.sezione[0]), float(elemento.sezione[1])
        calcestruzzo, acciaio = tag_materiale[elemento.membratura]
        dichiarato = telaio.materiali[elemento.membratura].calcestruzzo_confinato.material
        taglio = dichiarato.young / (2.0 * (1.0 + dichiarato.poisson))
        gj = taglio * _costante_torsionale(base, altezza)
        righe.append(
            f"# --- stazione {elemento.stazione} della membratura "
            f"{elemento.membratura}, sezione {base:.10g} x {altezza:.10g} mm"
        )
        # `-GJ` non e' facoltativo: senza, OpenSees 3.8.0 muore sulla card.
        righe.append(f"section Fiber {indice} -GJ {gj:.10g} {{")
        righe.append(
            f"    patch rect {calcestruzzo} {_SUDDIVISIONI_PATCH} "
            f"{_SUDDIVISIONI_PATCH} {-base / 2.0:.10g} {-altezza / 2.0:.10g} "
            f"{base / 2.0:.10g} {altezza / 2.0:.10g}"
        )
        # Una barra, una fibra: `layer straight` posa una fila equidistante,
        # ma `armatura.colloca` rende le posizioni gia' calcolate una per una
        # (#136 Q2), e reinterpolarle in file perderebbe proprio cio' che quella
        # funzione ha misurato.
        for barra in elemento.barre:
            area = math.pi * float(barra.diametro) ** 2 / 4.0
            righe.append(
                f"    fiber {float(barra.y):.10g} {float(barra.z):.10g} "
                f"{area:.10g} {acciaio}"
            )
        righe.append("}")
        asse = _versore(nodi[elemento.nodo_j] - nodi[elemento.nodo_i])
        vecxz = _versore(elemento.e2)
        if abs(float(np.dot(asse, vecxz))) > _COSENO_MASSIMO_VECXZ:
            raise ValueError(
                f"la stazione {elemento.stazione} della membratura "
                f"{elemento.membratura} ha l'asse della sezione quasi parallelo "
                "all'asse dell'asta: geomTransf non può costruire il "
                "riferimento locale, e OpenSees uscirebbe con un modello "
                "orientato a caso"
            )
        # `geomTransf Linear` prende `vecxz` come vettore del piano locale x-z
        # e ne ricava l'asse locale **y** come `vecxz x asse`. Misurato il
        # 30/08/2026 eseguendo OpenSees 3.8.0, non letto: su una mensola lungo
        # z con `vecxz = (0,1,0)` e un carico di 1000 N lungo il **global x**,
        # `recorder Element ... localForce` rende `Py = -1000` e `Pz = 2e-14`,
        # cioe' il global x e' l'asse locale y, col verso di `vecxz x asse`.
        # Le `y` delle
        # barre sono scritte cosi' come `armatura.colloca` le ha calcolate,
        # cioe' lungo `e1`: se i due versi non coincidono la sezione esce
        # specchiata. Con armatura simmetrica -- il caso di prova -- un
        # ribaltamento non si vede, ed e' il motivo per cui si controlla invece
        # di assumere.
        y_locale = _versore(np.cross(vecxz, asse))
        if float(np.dot(y_locale, _versore(elemento.e1))) < _COSENO_MINIMO_E1:
            raise ValueError(
                f"la stazione {elemento.stazione} della membratura "
                f"{elemento.membratura} ha e1 che non coincide con e2 x asse, "
                "cioè con l'asse locale y che OpenSees deriva da (asse, e2): le "
                "posizioni y delle barre sono misurate lungo e1, e la sezione a "
                "fibre uscirebbe ruotata o specchiata. Con armatura simmetrica "
                "non si vedrebbe"
            )
        righe.append(
            f"geomTransf Linear {indice} {vecxz[0]:.10g} {vecxz[1]:.10g} {vecxz[2]:.10g}"
        )
        # La stessa massa dei carichi nodali, acciaio compreso: due formule
        # diverse per la stessa asta darebbero una statica e una modale che
        # pesano cose diverse.
        massa = _massa_lineare(telaio, elemento)
        righe.append(
            f"element forceBeamColumn {indice} {elemento.nodo_i + 1} "
            f"{elemento.nodo_j + 1} {_PUNTI_INTEGRAZIONE} {indice} {indice} "
            f"-mass {massa:.10g}"
        )
    return righe


def _passo_statico(caso: str, n_nodi: int, n_elementi: int, pesi: np.ndarray) -> list[str]:
    righe = [
        f"# ===== caso di carico {caso}: peso proprio =====",
        "timeSeries Linear 1",
        "pattern Plain 1 1 {",
    ]
    for indice, peso in enumerate(pesi, start=1):
        if peso != 0.0:
            righe.append(f"    load {indice} 0 0 {-peso:.10g} 0 0 0")
    righe.append("}")
    righe += [
        f"recorder Node -file {_nome_uscita(caso, 'spostamenti')} -precision 12 "
        f"-nodeRange 1 {n_nodi} -dof 1 2 3 disp",
        f"recorder Node -file {_nome_uscita(caso, 'reazioni')} -precision 12 "
        f"-nodeRange 1 {n_nodi} -dof 1 2 3 4 5 6 reaction",
        f"recorder Element -file {_nome_uscita(caso, 'forze')} -precision 12 "
        f"-eleRange 1 {n_elementi} force",
        "constraints Transformation",
        "numberer RCM",
        "system BandGeneral",
        "test NormDispIncr 1.0e-8 10",
        "algorithm Linear",
        "integrator LoadControl 1.0",
        "analysis Static",
        # Il codice di `analyze` si guarda: un'analisi che non converge non
        # fermerebbe lo script, OpenSees uscirebbe 0 lo stesso, i registratori
        # scriverebbero l'ultimo stato e il lettore non lo distinguerebbe da un
        # risultato. `exit 1` lascia anche il marcatore di fine non scritto.
        "if {[analyze 1] != 0} {",
        f'    puts "{MARCA_FINE}_MANCA: il caso {caso} non è arrivato a '
        'convergenza"',
        "    exit 1",
        "}",
        "remove recorders",
        "wipeAnalysis",
        "remove loadPattern 1",
    ]
    return righe


def _passo_modale(modi: int, n_nodi: int) -> list[str]:
    righe = ["# ===== caso di carico MODALE ====="]
    for modo in range(1, modi + 1):
        righe.append(
            f"recorder Node -file modo_{modo}.out -precision 12 "
            f"-nodeRange 1 {n_nodi} -dof 1 2 3 \"eigen {modo}\""
        )
    righe += [
        f"eigen {modi}",
        # Le frequenze e la massa partecipante nello stesso file: e' l'unico
        # scarico strutturato che OpenSees offre su queste due grandezze.
        f"modalProperties -print -file {NOME_MASSA_MODALE} -unorm",
        # I registratori di `eigen` non scrivono da soli: `record` li forza.
        "record",
        "remove recorders",
    ]
    return righe


def scrivi_tcl(
    path: Path,
    telaio: "Telaio",
    *,
    casi_di_carico: list[str],
    modi: int | None = None,
    nome_peso_proprio: str = _NOME_PESO_PROPRIO,
) -> dict[str, object]:
    """Il gemello del `.inp`: un file che chiunque abbia la distribuzione standard esegue.

    Restituisce il resoconto per `metrics`, come `abaqus.write_inp`.

    **Il file si esegue con la cartella di lavoro sulla cartella di uscita**:
    i registratori portano nomi relativi, e OpenSees li scrive dove sta il
    processo, non dove sta lo script. `leggi_uscite` cerca in quella stessa
    cartella.

    `casi_di_carico` e' l'ordine del deck e resta tale: e' un contratto col
    lettore delle uscite esattamente come lo e' per il `.frd`. Il **primo** caso
    e' il peso proprio, per la stessa costruzione che vale per `ccx` -- la card
    del peso e' scritta prima di ogni ramo condizionale, quindi il passo 1 e'
    sempre e solo il peso proprio (vedi `solve.leggi_reazioni`). `MODALE`, se
    c'e', e' l'ultima voce. **Ogni altro nome si rifiuta**: i suoi carichi non
    stanno nel contratto `Telaio` e appartengono al ramo G.

    `nome_peso_proprio` e' il nome che il primo caso **deve** portare, e il suo
    predefinito e' quello che `AnalysisConfig.step_name` dichiara. Il nome non
    si prende dal primo della lista: prima si faceva, e `casi_di_carico=
    ["VENTO"]` scriveva un pattern di gravita' con le uscite etichettate
    `U_VENTO` -- l'etichetta al posto del carico, cioe' il falso contro cui
    questo modulo e' costruito.

    `modi` predefinito da `config.Modale`, che ha il proprio numero misurato:
    non un secondo 40 scritto qui.
    """
    casi = solve.valida_casi_di_carico(casi_di_carico)
    nodi, al_piede = _controlla_telaio(telaio)
    modi = Modale().modi if modi is None else modi

    peso_proprio, *restanti = casi
    if peso_proprio == "MODALE":
        peso_proprio, restanti = None, casi
    elif peso_proprio != nome_peso_proprio:
        # Prendere «il primo della lista» qualunque nome portasse scriveva un
        # pattern di gravita' sotto l'etichetta di un'altra azione: misurato,
        # `casi_di_carico=["VENTO"]` dava le uscite `U_VENTO` di un carico che
        # nessuno ha chiesto. E' l'etichetta al posto del carico.
        raise ValueError(
            f"il primo caso di carico è '{peso_proprio}', ma l'unico carico "
            f"che questo modulo scrive è il peso proprio, che si chiama "
            f"'{nome_peso_proprio}' (AnalysisConfig.step_name, o "
            "nome_peso_proprio). Scriverlo sotto un'altra etichetta darebbe un "
            "pattern di gravità con il nome di un'azione che nessuno ha "
            "calcolato"
        )
    fuori_contratto = [nome for nome in restanti if nome != "MODALE"]
    if fuori_contratto:
        raise ValueError(
            f"i casi di carico {fuori_contratto} non hanno un carico dichiarato: "
            "il contratto Telaio porta nodi, elementi, giunzioni e materiali, e "
            "non le azioni. Il primo caso è il peso proprio e MODALE è il "
            "blocco in frequenza; ogni altra azione appartiene alle "
            "combinazioni, che questo modulo non scrive. Uno *STEP senza "
            "carichi darebbe spostamenti nulli e verdetti verdi su un modello "
            "mai caricato"
        )

    card_materiali, tag_materiale = _materiali(telaio)
    pesi = _peso_nodale(telaio, nodi)

    righe = [
        "# Modello a telaio generato da MeshRec (core/opensees.py).",
        "# Unità: mm, N, MPa, t, s. OpenSees non processa unità: la coerenza è",
        "# di chi scrive, e questo file la dichiara qui una volta sola.",
        "# Si esegue con la cartella di lavoro sulla cartella di uscita:",
        "#     cd <cartella di uscita> && OpenSees <questo file>",
        "wipe",
        "model BasicBuilder -ndm 3 -ndf 6",
        "",
        "# --- nodi ---",
    ]
    for indice, (x, y, z) in enumerate(nodi, start=1):
        righe.append(f"node {indice} {x:.10g} {y:.10g} {z:.10g}")
    righe += [
        "",
        f"# --- vincoli: i {len(al_piede)} nodi che poggiano a terra, incastrati ---",
    ]
    for indice in al_piede:
        righe.append(f"fix {int(indice) + 1} 1 1 1 1 1 1")
    righe += ["", "# --- materiali ---", *card_materiali]
    righe += ["", "# --- sezioni a fibre, trasformazioni ed elementi ---"]
    righe += _sezioni_ed_elementi(telaio, nodi, tag_materiale)
    righe.append("")
    if peso_proprio is not None:
        righe += _passo_statico(peso_proprio, len(nodi), len(telaio.elementi), pesi)
        righe.append("")
    if "MODALE" in casi:
        if modi < 1:
            raise ValueError(
                f"modi={modi}: il caso MODALE chiede almeno un modo. «eigen "
                f"{modi}» non estrae niente, e il verdetto sulla massa modale "
                "leggerebbe una cartella senza forme come se il passo non ci "
                "fosse stato"
            )
        righe += _passo_modale(modi, len(nodi))
        righe.append("")
    righe += [
        "wipe",
        "",
        "# --- il marcatore di fine corsa: se manca, la corsa è stata troncata",
        f'set _fine [open "{NOME_FINE}" w]',
        f'puts $_fine "{MARCA_FINE}"',
        "close $_fine",
        "",
    ]

    percorso = Path(path)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text("\n".join(righe), encoding="utf-8")
    return {
        "tcl": str(percorso),
        "nodi": int(len(nodi)),
        "elementi": int(len(telaio.elementi)),
        "barre": int(sum(len(e.barre) for e in telaio.elementi)),
        "nodi_vincolati": int(len(al_piede)),
        "casi_di_carico": list(casi),
        "modi": int(modi) if "MODALE" in casi else 0,
        "peso_proprio": float(pesi.sum()),
    }


def _ultima_riga(percorso: Path, attesi: int) -> np.ndarray:
    """L'ultimo passo scritto da un registratore, con `attesi` numeri.

    Un registratore scrive una riga per passo d'analisi e nessuna intestazione:
    l'ultima riga e' lo stato finale, che e' quello che serve.

    Due guardie, e sono la stessa classe di difetto che questo repo ha gia'
    chiuso quattro volte sul `.frd` e sul `.dat`. Un file **senza righe** e' una
    corsa che non ha scritto, ed e' diverso da spostamenti nulli. Una riga con
    **meno numeri del dovuto** e' una scrittura interrotta -- processo ucciso,
    disco pieno -- e leggerla come completa darebbe un campo parziale che nessun
    verdetto distingue da uno intero.

    `errors="ignore"` e non `"replace"`, la stessa scelta misurata di
    `solve._righe_dat`: qui le righe si separano contando i campi, e `replace`
    e' l'opzione che il conteggio lo cambia -- un byte fuori tabella fra due
    numeri diventerebbe un campo in piu' e accuserebbe di troncamento un file
    sano.
    """
    testo = percorso.read_text(encoding="ascii", errors="ignore")
    righe = [riga for riga in testo.splitlines() if riga.split()]
    if not righe:
        raise ValueError(
            f"{percorso} non porta nessuna riga: il registratore non ha scritto "
            "niente. Non è uno stato nullo, è una corsa che non c'è stata"
        )
    campi = righe[-1].split()
    if len(campi) != attesi:
        raise ValueError(
            f"{percorso}, ultima riga: {len(campi)} numeri invece di {attesi}. "
            "L'uscita è troncata -- il solutore è stato interrotto a metà "
            "scrittura -- e i valori letti sarebbero parziali"
        )
    return np.array([float(c) for c in campi], dtype=np.float64)


def leggi_uscite(out_dir: Path, telaio: "Telaio") -> dict[str, np.ndarray]:
    """I risultati nelle convenzioni del contratto già in casa (#138 Q2).

    `U_<CASO>` per nodo (vettore), `MODO_<n>` per nodo (vettore, forma non
    dimensionale), e **per cella** `N_<CASO>`, `V_<CASO>`, `M_<CASO>`, che sono
    le grandezze del telaio.

    **Nessun `VM_`**, e non è un buco: il telaio non ha una tensione equivalente
    per nodo -- la tensione vive per fibra dentro la sezione. Lo dichiara
    `solve.CONTROLLI_PER_MODELLO["picco"]["telaio"]`, che per lo stesso motivo
    marca quel verdetto non applicabile invece di farlo girare su una grandezza
    che non esiste.

    Un blocco modale non produce mai `U_` né `VM_`: la forma è normalizzata
    sulla massa e non è uno spostamento fisico, esattamente come per il `.frd`.

    Un file assente significa «quel caso non è stato calcolato» e non è un
    errore: la cartella di una corsa interrotta prima del passo modale non ha i
    `modo_n.out`, e leggerla deve dire che non ci sono, non schiantare. Un file
    che invece **c'è** ed è vuoto o corto solleva: quella è una scrittura
    interrotta, non un'assenza.
    """
    cartella = Path(out_dir)
    if list(cartella.glob("*.out")):
        fine = cartella / NOME_FINE
        completa = fine.is_file() and MARCA_FINE in fine.read_text(
            encoding="ascii", errors="ignore"
        )
        if not completa:
            raise ValueError(
                f"{cartella} porta uscite ma non il marcatore di fine "
                f"({NOME_FINE}): la corsa è stata troncata -- processo ucciso, "
                "oppure l'analisi non è arrivata a convergenza e lo script è "
                "uscito. I file che ci sono portano l'ultimo stato scritto, che "
                "non è un risultato"
            )
    nodi = np.asarray(telaio.nodi, dtype=np.float64)
    n_nodi, n_elementi = len(nodi), len(telaio.elementi)
    campi: dict[str, np.ndarray] = {}

    for percorso in sorted(cartella.glob("*_spostamenti.out")):
        caso = percorso.name[: -len("_spostamenti.out")]
        campi[f"U_{caso}"] = _ultima_riga(percorso, 3 * n_nodi).reshape(n_nodi, 3)

    for percorso in sorted(cartella.glob("*_forze.out")):
        caso = percorso.name[: -len("_forze.out")]
        # Dodici numeri per elemento: forza e momento all'estremo i, poi
        # all'estremo j. Sono in coordinate **globali** (misurato su una mensola
        # caricata in testa: il primo numero coincide a sedici cifre con la
        # reazione globale), quindi N, V e M si ricavano proiettando sull'asse
        # dell'asta e non leggendo una colonna.
        crude = _ultima_riga(percorso, 12 * n_elementi).reshape(n_elementi, 12)
        assiale = np.zeros(n_elementi)
        taglio = np.zeros(n_elementi)
        flessione = np.zeros(n_elementi)
        for indice, elemento in enumerate(telaio.elementi):
            asse = _versore(nodi[elemento.nodo_j] - nodi[elemento.nodo_i])
            forza, momento = crude[indice, 6:9], crude[indice, 9:12]
            lungo = float(np.dot(forza, asse))
            assiale[indice] = lungo
            taglio[indice] = float(np.linalg.norm(forza - lungo * asse))
            # La componente del momento lungo l'asse e' torsione, non
            # flessione: sommarla nel modulo darebbe un momento flettente
            # gonfiato e plausibile.
            torsione = float(np.dot(momento, asse))
            flessione[indice] = float(np.linalg.norm(momento - torsione * asse))
        campi[f"N_{caso}"] = assiale
        campi[f"V_{caso}"] = taglio
        campi[f"M_{caso}"] = flessione

    modali = [
        (int(trovato.group(1)), percorso)
        for percorso in cartella.glob("modo_*.out")
        if (trovato := _USCITA_MODALE.fullmatch(percorso.name)) is not None
    ]
    for modo, percorso in sorted(modali):
        campi[f"MODO_{modo}"] = _ultima_riga(percorso, 3 * n_nodi).reshape(n_nodi, 3)

    return campi


_INTESTAZIONE_CUMULATA = "MASS RATIOS (%) (cumulative)"


def leggi_massa_modale(percorso: Path) -> dict[str, list[float]] | None:
    """Massa partecipante dalle percentuali cumulate di `modalProperties`.

    Rende la stessa forma che `solve.controlla_massa_modale` consuma per
    CalculiX -- `{"catturata": [6], "disponibile": [6]}` -- e non un formato
    nuovo: il verdetto guarda una grandezza, non un file. OpenSees stampa
    direttamente il **rapporto** cumulato in percento per MX, MY, MZ, RMX, RMY,
    RMZ (misurato il 30/08/2026), quindi il disponibile vale 100 per
    costruzione e il rapporto esce identico a quello del `.dat`.

    L'ultima riga del blocco e' quella di tutti i modi estratti: il cumulato
    cresce col numero del modo, e la frazione che il verdetto vuole e' quella
    dopo l'ultimo.

    `None` se il blocco non c'e' -- nessun passo modale, o un passo modale che
    non ha estratto niente. Non e' uno zero: zero significherebbe «i modi non
    catturano massa», che e' un'altra cosa e sarebbe un difetto.
    """
    percorso = Path(percorso)
    if not percorso.is_file():
        return None
    dentro = False
    ultima: list[float] | None = None
    for riga in percorso.read_text(encoding="ascii", errors="ignore").splitlines():
        if _INTESTAZIONE_CUMULATA in riga:
            dentro = True
            continue
        if not dentro:
            continue
        campi = riga.split()
        # Sette campi, il primo il numero del modo: le righe di intestazione del
        # blocco cominciano tutte con `#` e non passano di qui.
        if len(campi) != 7 or not campi[0].isdigit():
            if ultima is not None:
                break
            continue
        try:
            ultima = [float(c) for c in campi[1:]]
        except ValueError:
            continue
    if ultima is None:
        return None
    return {"catturata": ultima, "disponibile": [100.0] * 6}


_INTESTAZIONE_AUTOVALORI = "EIGENVALUE ANALYSIS"


def leggi_frequenze(percorso: Path) -> list[float]:
    """Le frequenze proprie [Hz] dal blocco «EIGENVALUE ANALYSIS» di `modalProperties`.

    Stessa forma che `solve.controlla_autovalori` consuma per CalculiX -- una
    lista in Hz, in ordine crescente di modo -- e stessa sorgente della massa
    partecipante, cioe' il file che `modalProperties -print -file` scrive: la
    tabella porta `MODE LAMBDA OMEGA FREQUENCY PERIOD` (misurato il 30/08/2026
    su OpenSees 3.8.0), e la frequenza in Hz e' la terza colonna dopo il numero
    del modo. Si legge di li' e non si ricava da `eigen`, che rende gli
    autovalori allo script e non lascia nulla sul disco.

    Lista vuota se il blocco non c'e': nessun passo modale. Non e' uno zero --
    una frequenza nulla e' un meccanismo -- e `controlla_autovalori` sulla
    lista vuota dichiara «non verificato».
    """
    percorso = Path(percorso)
    if not percorso.is_file():
        return []
    dentro = False
    frequenze: list[float] = []
    for riga in percorso.read_text(encoding="ascii", errors="ignore").splitlines():
        if _INTESTAZIONE_AUTOVALORI in riga:
            dentro = True
            continue
        if not dentro:
            continue
        campi = riga.split()
        # Cinque campi, il primo il numero del modo: le intestazioni del blocco
        # cominciano con `#` e non passano di qui. La prima riga che non e' una
        # riga di modo, dopo che almeno una c'e' stata, chiude il blocco.
        if len(campi) != 5 or not campi[0].isdigit():
            if frequenze:
                break
            continue
        try:
            frequenze.append(float(campi[3]))
        except ValueError:
            continue
    return frequenze


def _reazioni_al_piede(
    cartella: Path, caso: str, n_nodi: int, al_piede: np.ndarray
) -> dict[int, tuple[float, float, float]]:
    """Le reazioni **dei soli nodi incastrati**, a numero di nodo a base uno.

    Il registratore le scrive per tutti i nodi e sei gradi per nodo; qui
    servono le tre forze dei nodi al piede, che sono quelle che
    `solve.controlla_reazioni` somma per confrontarle col peso.

    I nodi liberi restano fuori di proposito. La somma su **tutti** i nodi
    torna sempre uguale al carico applicato -- e' come sono definite le
    reazioni nodali, e infatti misurata il 30/08/2026 sul telaio sintetico
    valeva il peso a sedici cifre anche col telaio incastrato in un nodo solo:
    un verdetto che la guardasse sarebbe verde per costruzione. La somma sui
    soli appoggi e' invece l'equilibrio vero, e il residuo dei nodi liberi
    (misurato: 6e-9 N su 10 kN) resta fuori dove si vede.
    """
    percorso = cartella / _nome_uscita(caso, "reazioni")
    if not percorso.is_file():
        return {}
    campi = _ultima_riga(percorso, 6 * n_nodi).reshape(n_nodi, 6)
    return {
        int(indice) + 1: (
            float(campi[indice, 0]), float(campi[indice, 1]), float(campi[indice, 2])
        )
        for indice in al_piede
    }


def esegui(
    out_dir: Path,
    telaio: "Telaio",
    solutore: "SolutoreConfig",
    *,
    casi_di_carico: list[str],
    modi: int | None = None,
) -> dict[str, object]:
    """Scrive il `.tcl`, lancia OpenSees su di esso, e rende i sette verdetti.

    E' il pezzo che mancava fra `scrivi_tcl` e `leggi_uscite`: senza, il
    modulo scriveva uno script che nessuno eseguiva. Sta qui e non in
    `solve.risolvi` perche' quella funzione monta la riga di comando di
    CalculiX e legge il `.frd` e il `.dat` che solo lui scrive: rifiuta ogni
    altro solutore, e questa e' l'altra strada che il suo rifiuto nomina.

    Tre cose misurate il 30/08/2026 su OpenSees 3.8.0, non dedotte:

    - **Il codice d'uscita non e' il segnale.** OpenSees esce 0 anche quando lo
      script muore su un errore fatale. Il segnale e' il marcatore di fine che
      `scrivi_tcl` scrive in coda: se manca, la corsa non e' arrivata in fondo
      -- errore fatale, processo ucciso, o `analyze` che non converge, che fa
      uscire lo script con codice 1 prima del marcatore. Il codice resta nel
      messaggio, perche' dice se il binario e' nemmeno partito.
    - **La cartella corrente e' quella d'uscita, mai la `bin/`
      dell'installazione.** I registratori portano nomi relativi e scrivono
      dove sta il processo: lanciato dalla propria cartella, OpenSees
      scriverebbe i risultati dentro l'installazione.
    - **Le uscite della corsa precedente si tolgono prima.** I registratori
      riscrivono i propri file, ma non quelli che questa corsa non apre: un
      `modo_3.out` di una corsa a tre modi resterebbe accanto ai due di una
      corsa a due, e `leggi_uscite` lo leggerebbe come un modo di questa.

    Un solutore assente **non e' un fallimento** -- e' lo stato che
    `solve.risolvi` dichiara da sempre per CalculiX -- e si dichiara *prima* di
    scrivere il `.tcl`: uno script sul disco che nessuno ha risolto e' un
    artefatto che mente sulla propria corsa.

    I sette verdetti passano tutti da `solve.verdetti_per_modello("telaio",
    ...)`, che e' l'unico modo perche' `vincolo_in_pianta` e `picco` -- le due
    caselle che la tabella dichiara non applicabili al telaio -- non escano
    verdi: la loro via al verde e' misurata e aperta (una mensola verticale da'
    `constraint_plan_extent` con `minimo = 1,0`, e `controlla_vincolo_in_pianta`
    la promuove), e non passa di qui perche' il calcolo non viene nemmeno
    chiamato.
    """
    if solutore.nome != "opensees":
        raise ValueError(
            f"solutore.nome = '{solutore.nome}': questo passo risolve un telaio "
            "a fibre, che è uno script di OpenSees e non un deck Abaqus -- non "
            "c'è un .inp da dare a CalculiX, e le grandezze del telaio (N, V, "
            "M per elemento) non stanno in un .frd. La strada di CalculiX è "
            "core/solve.py (risolvi), sul deck dello step 11"
        )
    # Prima di scrivere il .tcl: uno script sul disco che nessuno ha risolto
    # direbbe che la corsa e' arrivata al modello quando manca il solutore. Il
    # motivo e il dove prenderlo vengono da `solve.disponibilita`, che e' il
    # punto unico in cui si decide dove sta un solutore: riscriverli qui
    # darebbe due diagnosi diverse per la stessa assenza.
    stato = solve.disponibilita(solutore)["opensees"]
    if not stato["disponibile"]:
        return {
            "eseguito": False,
            "solutore": "assente",
            "motivo": stato["motivo"],
            "dove_prenderlo": stato["dove_prenderlo"],
        }
    binario = stato["percorso"]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for vecchia in out_dir.glob("*.out"):
        vecchia.unlink()

    percorso_tcl = out_dir / NOME_TCL
    resoconto = scrivi_tcl(
        percorso_tcl, telaio, casi_di_carico=casi_di_carico, modi=modi
    )

    processo = subprocess.run(
        [binario, NOME_TCL],
        cwd=out_dir,
        capture_output=True,
        timeout=solve._TIMEOUT_S,
    )
    # `replace` e non `ignore`: questo è un registro in prosa che l'utente apre
    # per capire un guasto, non un file di dati letto a campi come quelli di
    # `_righe_dat`. Un carattere cancellato consegna una riga che nessuno ha
    # scritto; `U+FFFD` dice che lì c'era qualcosa che non si è letto.
    uscita = (processo.stdout + processo.stderr).decode("utf-8", errors="replace")
    percorso_registro = out_dir / NOME_REGISTRO
    percorso_registro.write_text(uscita, encoding="utf-8")

    fine = out_dir / NOME_FINE
    arrivata = fine.is_file() and MARCA_FINE in fine.read_text(
        encoding="ascii", errors="ignore"
    )
    if not arrivata:
        raise RuntimeError(
            f"OpenSees non ha scritto il marcatore di fine ({NOME_FINE}) su "
            f"{percorso_tcl.name}: la corsa non è arrivata in fondo. Il codice "
            f"d'uscita ({processo.returncode}) non è il segnale -- OpenSees "
            "esce 0 anche dopo un errore fatale -- e i file che ci sono portano "
            f"l'ultimo stato scritto, che non è un risultato. Coda "
            f"dell'uscita:\n{uscita[-2000:]}"
        )

    nodi = np.asarray(telaio.nodi, dtype=np.float64)
    campi = leggi_uscite(out_dir, telaio)
    casi = list(resoconto["casi_di_carico"])
    statico = next((nome for nome in casi if nome != "MODALE"), None)
    reazioni = (
        {}
        if statico is None
        else _reazioni_al_piede(
            out_dir, statico, len(nodi), _al_piede(nodi, telaio.elementi)
        )
    )
    frequenze_hz = leggi_frequenze(out_dir / NOME_MASSA_MODALE)
    masse = leggi_massa_modale(out_dir / NOME_MASSA_MODALE)
    avvisi = conta_avvisi(uscita)
    # Le reazioni tengono su il peso proprio, e il peso proprio e' quello che
    # `_peso_nodale` ha applicato: la ripartizione nodale rende l'uguaglianza
    # esatta (vedi il suo docstring, e la casella `reazioni` della tabella).
    peso_atteso = (0.0, 0.0, float(resoconto["peso_proprio"]))

    # Le quattro grandezze che seguono vengono da `core/solve.py` e sono
    # private la': la tolleranza sulle reazioni, il tempo massimo di una corsa,
    # lo spostamento massimo fra i passi statici e la dimensione del modello
    # sono le stesse cose del solido, e riscriverle qui vorrebbe dire tenere
    # allineate due copie di ciascuna -- la seconda verita' accanto alla prima.
    controlli = solve.verdetti_per_modello("telaio", {
        "reazioni": lambda: solve.controlla_reazioni(
            reazioni, peso_atteso, tolleranza=solve._TOLLERANZA_REAZIONI
        ),
        "autovalori": lambda: solve.controlla_autovalori(frequenze_hz),
        "avvisi": lambda: solve.controlla_avvisi(avvisi),
        "spostamenti": lambda: solve.controlla_spostamenti(
            solve._spostamento_massimo(campi), solve._dimensione(nodi)
        ),
        "massa_modale": lambda: solve.controlla_massa_modale(masse),
    })

    return {
        "eseguito": True,
        "solutore": "opensees",
        "returncode": processo.returncode,
        "avvisi": avvisi,
        "controlli": controlli,
        "modi": sum(1 for nome in campi if nome.startswith("MODO_")),
        "frequenze_hz": frequenze_hz,
        "telaio": resoconto,
        "tcl": str(percorso_tcl),
        "log": str(percorso_registro),
    }
