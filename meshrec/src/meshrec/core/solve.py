"""Lettura delle uscite di CalculiX: il `.frd` e il `.dat`.

Il modulo esiste separato da `abaqus.py` perche' quello scrive il deck e
questo legge i risultati: sono due direzioni, e `abaqus.py` e' gia' lungo.

Le uscite di `ccx` hanno tre trappole sul `.frd`, tutte misurate il
21/08/2026 sul deck as-built del telaio (`ccx` 2.22, `runs/lab_telaio_v2/
wall_model.inp`):

- il numero di passo sta nel record `100CL` e **si legge**, non si deduce
  contando i blocchi: su quel deck i blocchi DISP sono nove per quattro
  passi, tre statici piu' sei modi, e contare cade appena le uscite
  cambiano;
- nel record modale il passo e il tipo escono incollati (`2MODAL`), quindi
  la lettura e' a colonne fisse e mai un `split()`;
- le forme modali sono normalizzate sulla massa. Una von Mises calcolata su
  una forma da' numeri plausibili per un calcestruzzo e privi di
  significato: fino a 88,5 MPa, misurati. Il flag `modale` esiste per
  impedire che escano da qui come se fossero millimetri o MPa.

Il `.dat` ha una trappola analoga, misurata oggi su un deck di prova ad hoc
(non `lab_telaio_v2`) a due passi -- uno statico con carico, uno modale --
costruito apposta per verificarla: la richiesta di stampa delle reazioni
(`*NODE PRINT, RF`) fatta nel passo statico resta attiva anche nel passo
modale successivo, che non la richiede e non la cancella. `ccx` ristampa
quindi un blocco "forces" anche per ciascun modo, sotto l'intestazione
`E I G E N V A L U E   O U T P U T`: numeri nell'ordine dei milioni di N,
che non sono reazioni ne' altro di fisico. `leggi_reazioni` si ferma a
quella intestazione per lo stesso motivo per cui `leggi_frd` marca `modale`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from meshrec.core import abaqus, quality
from meshrec.core.config import AnalysisConfig, _mappa_casefold

if TYPE_CHECKING:  # pragma: no cover
    # Il blocco `solutore` di `PipelineConfig` lo scrive l'onda 0 della Fase 8:
    # qui serve solo come annotazione, e le annotazioni di questo modulo sono
    # stringhe (`from __future__ import annotations`). L'import vero
    # arriverebbe a runtime prima che il blocco esista.
    from meshrec.core.config import SolutoreConfig

# Tempo massimo concesso a ccx: stesso valore usato in tutta la suite di
# fattibilita' (tests/feasibility/test_calculix.py), non un numero nuovo.
_TIMEOUT_S = 600.0

# Estensione in pianta minima dell'insieme vincolato
# (abaqus.constraint_plan_extent), come frazione dell'impronta del pezzo.
# Sotto questa soglia i risultati restano scritti ma sono marcati non
# citabili. Misurato il 21/08/2026 allo Step 7 del Task 2 su quattro
# geometrie: muro 0,999, lab_crop 0,987, sintetico a due piedi 1,000,
# sintetico a un piede solo 0,32 -- un dirupo netto fra 0,32 e 0,987, nessun
# punto di misura in mezzo. 0,5 sta in quel dirupo: sopra il solo caso
# patologico misurato, sotto ogni caso vincolato correttamente.
#
# Il caso difettoso **reale** e' arrivato col Task 11 e chiude il debito che
# questa nota dichiarava: sull'as-built del telaio, col BASE che teneva un
# piede solo, l'insieme vincolato attraversava 233 mm di un pezzo lungo 3144,
# cioe' 0,074 (il difetto e la sua misura stanno in
# `abaqus.constraint_plan_extent`); la stessa corsa col vincolo corretto vale
# 0,9943 (misurato su `runs/lab_telaio_v2/metrics.json`,
# `11_export.constraint_plan_extent.minimo`). La soglia regge quindi su un
# difetto reale piu' netto del sostituto sintetico -- 0,074 contro 0,32 --
# non piu' solo su un banco.
#
# Costante di modulo e non campo di `AnalysisConfig` (ruling della revisione
# del Task 7): non cambia cosa viene calcolato, solo l'etichetta di un
# verdetto, quindi non appartiene all'impronta di `sweep.fingerprint` (che
# include `analysis` per intero, sweep.py:43) -- un campo qui romperebbe
# `experiments/*/registro.jsonl`, sola lettura. E una soglia di controllo che
# l'utente puo' allentare da YAML e' un controllo che l'utente puo' zittire:
# questa fase esiste per avere controlli che smentiscono, non per renderli
# opzionali. Confine con `AnalysisConfig.set_tolerance_factor`, che resta in
# configurazione: quello cambia quali nodi finiscono nei set, cioe'
# l'elaborazione stessa, non solo il verdetto su un suo risultato.
_SOGLIA_VINCOLO_IN_PIANTA = 0.5

# Rapporto fra lo spostamento massimo e la dimensione caratteristica del
# modello, oltre il quale i numeri non sono citabili (#12).
#
# Il difetto che intercetta, misurato il 26/08/2026: un frammento **staccato**
# dal corpo principale ma dentro la sua impronta -- cioe' esattamente cio' che
# un maglio da scansione produce quando la segmentazione lascia un'isola. Il
# corpo e' vincolato bene, l'isola cade libera. Su un cubo di 100 mm con
# un'isola di 3 mm: `ccx` esce **0**, zero `*WARNING`, e **tutti e cinque** i
# verdetti precedenti passano, con uno spostamento massimo di 3,6e10 mm. Con
# l'isola a 1 mm, 8,0e21 mm. Nessuno dei cinque guarda l'ampiezza.
#
# Perche' `controlla_reazioni` non lo vede, ed e' il punto: la sua tolleranza
# e' **relativa** al peso. L'isola di 3 mm pesa 5,2e-06 del totale e quella da
# 1 mm 2,0e-07, cioe' sotto 1e-4 -- l'equilibrio globale resta soddisfatto
# entro tolleranza mentre una parte del modello vola via. Un'isola grande la
# prende (lato 30 mm: scarto 5,2e-03), una piccola no: la cecita' cresce al
# calare della massa staccata, non del disordine.
#
# Perche' 1,0, e perche' **non** e' una soglia difficile da tarare -- che era
# il dubbio esplicito del ticket. Ha una giustificazione teorica prima che
# empirica: l'elasticita' lineare a piccoli spostamenti assume u << L, quindi
# uno spostamento grande quanto il modello stesso **falsifica l'ipotesi con
# cui il solutore lo ha appena calcolato**. Non e' un limite fisico tarato su
# un provino, e' il confine di validita' del modello. La misura poi dice che
# la banda e' larghissima: i casi legittimi stanno a 1,0e-08 e i casi guasti
# partono da 1,7e+07, sedici ordini di grandezza di vuoto in mezzo. La media
# geometrica dei due estremi vale 0,41, quindi 1,0 ci cade dentro a meno di un
# fattore 2,5, con circa otto decadi di margine per lato. `origine`: **nostra**
# -- nessuna fonte pubblica questo rapporto, e la nota che il registro esige
# per una soglia nostra e' questo commento.
#
# ponytail: la dimensione caratteristica e' la diagonale del parallelepipedo
# contenitore dei nodi, che **non** e' invariante per rotazione. Irrilevante
# qui: cambia il rapporto di un fattore di pochi, contro otto decadi di
# margine. Una misura invariante costerebbe di piu' e non sposterebbe alcun
# verdetto.
_SOGLIA_SPOSTAMENTO_SU_DIMENSIONE = 1.0

# Frazione minima di massa partecipante che i modi estratti devono catturare
# perche' l'analisi modale sia citabile (#75).
#
# **Il valore e' letto, non nostro**: EN 1998-1 §4.3.3.3.1(3) chiede che «la
# somma delle masse modali efficaci per i modi considerati sia almeno il 90%
# della massa totale della struttura». Le NTC 2018 riportano lo stesso criterio
# al §7.3.3.1.
#
# **Il contesto pero' e' diverso e va dichiarato.** L'Eurocodice pone quel
# limite per l'analisi sismica con spettro di risposta, dove la massa non
# catturata e' forza sismica che il calcolo non vede. Qui non si fa analisi
# sismica: il criterio e' preso in prestito come misura di **sufficienza del
# numero di modi**, che e' la stessa grandezza sottostante. Preso in prestito e
# non derivato, quindi la nota deve dirlo -- ed e' questa.
#
# Il difetto che intercetta, misurato il 26/08/2026 su `runs/lab_telaio_v2`:
# coi venti modi chiesti la frazione catturata vale 92,78% in x, 92,71% in y e
# **87,46% in z**. La direzione verticale non arriva al 90%, e nessun controllo
# se ne accorgeva -- `controlla_autovalori` guarda che le frequenze siano
# reali, positive e non degeneri, e un'analisi con tre modi su una struttura
# che ne vorrebbe cento le supera tutte.
#
# Non e' un cancello sul modello ma sulla **configurazione**: sotto soglia il
# modello non e' sbagliato, e' `Modale.modi` a essere troppo basso.
#
# **Seguito, 26/08/2026.** Quei venti modi erano scritti a mano nel file di
# caso. Si e' misurato quanti ne servono davvero -- lo scavallamento cade a 32
# su entrambi i corpi di riferimento -- e `Modale.modi` ha ora un predefinito
# misurato di 40, che porta ogni direzione sopra il 90% con circa quattro punti
# di margine. Il predefinito **non sostituisce questo verdetto**: e' tarato su
# una scena sola, quindi su una struttura diversa puo' non bastare, ed e' il
# verdetto a dirlo. Misura in `docs/validazione/modi-per-la-normativa.md`.
_FRAZIONE_MASSA_MINIMA = 0.90

# Tolleranza di equilibrio per `controlla_reazioni`.
#
# Lo scarto misurato nel giro originale del Task 7 (8,5% con 35 nodi
# vincolati, 5,7% con 85, 19,5% su una mesh rada) non era rumore di mesh: era
# indagato come tale e la lettura era sbagliata. Causa radice trovata da
# un'indagine dedicata (21/08/2026, worktree separato): `ccx` non riporta,
# nella `RF` di un nodo vincolato che porta anche `*DLOAD, GRAV`, la quota di
# gravita' applicata a quel nodo dagli elementi che lo toccano -- stampa solo
# la forza trasmessa elasticamente attraverso la struttura. Prova in forma
# chiusa, zero errore di discretizzazione: un tetraedro solo, base fissa,
# apice libero -- rho*V*g = 2,943 N, ccx stampa 0,73575 N (esattamente 1/4,
# la sola quota del nodo libero). Lo scarto era quindi un rapporto
# bordo/volume della mesh (quanti nodi vincolati toccano il carico, che cala
# raffinando), non un errore fisico: coincideva a sei decimali con la quota
# tributaria di BASE su tutte le mesh misurate. Anche l'indizio dell'MPC
# spuria era falso: "multiple point constraints: 1" e' un conteggio di limite
# superiore che ccx stampa identico su ogni corsa, incluso il tetraedro
# singolo senza alcun *TIE.
#
# `risolvi()` ora toglie quella quota da `peso_atteso` prima del confronto
# (`_quota_tributaria_gravita`): con l'oracolo corretto lo scarto residuo,
# misurato oggi su tre mesh a cubo (13/35/85 nodi vincolati, carichi
# cumulativi peso+spinta+carico in sommita'), e' 1,3e-7 nel caso peggiore --
# precisione del solutore, non fisica mancante. 1e-4 sta sotto l'uno per
# mille chiesto dalla revisione e circa tre ordini di grandezza sopra quel
# residuo: margine per la mesh reale della pipeline, mai eseguita in questa
# indagine (non e' fine quanto il residuo misurato, ma resta un errore di
# solutore, non di modello).
#
# Cosa intercetta davvero, ora che il rumore di stampa e' tolto: NON un
# errore di densita' (entra sia nel carico che ccx integra sia in
# `peso_atteso`, si cancella con qualunque tolleranza) -- la *direzione*
# (un vincolo che tiene la struttura di sbieco, il confronto e' vettoriale
# apposta), una deriva fra cio' che il deck dichiara e cio' che la
# configurazione crede, o una lettura parziale delle reazioni.
_TOLLERANZA_REAZIONI = 1e-4

# ponytail: banda di vincolo come frazione dell'altezza totale del modello,
# non una quota assoluta in mm (sarebbe un numero del provino dentro src/).
# 0,05 non e' misurato -- e' una scelta conservativa non tarata su un caso
# difettoso reale, segnalata nel report del Task 7. Se il Task 11 porta un
# caso reale con un picco vicino al confine, tarare qui.
_FRAZIONE_BANDA_VINCOLO = 0.05

# Il marcatore con cui `ccx` apre una riga di avviso. Costante e non letterale
# sparso, perche' non e' lo stesso per ogni solutore: OpenSees 3.8.0 scrive
# `WARNING` senza asterisco (misurato il 30/08/2026), e cercare questa stringa
# nella sua uscita darebbe zero avvisi qualunque cosa sia successo. Vedi la
# casella `avvisi` di `CONTROLLI_PER_MODELLO`.
_MARCA_AVVISO_CCX = "*WARNING"


class Blocco(NamedTuple):
    """Un blocco di risultati del `.frd`, con il passo a cui appartiene."""

    grandezza: str
    passo: int
    modale: bool
    valore: float
    nodi: np.ndarray
    dati: np.ndarray


# Colonne del record 100CL, contate sul `.frd` scritto da ccx 2.22 (misurate
# oggi anche su un deck di prova ad hoc, non solo su quello del brief): il
# valore sta fra 12 e 23, il passo comincia o finisce alla colonna 62, e nel
# record modale "MODAL" gli sta incollata subito dopo, senza spazio. Un
# `split()` sulla riga intera legge quel token unico e perde entrambi i campi
# in silenzio.
#
# #94: fino a nove passi il numero occupa la sola colonna 62. Dal decimo in
# poi non si sa se il campo cresca verso destra (`%1d`, che spinge "MODAL"
# avanti di una colonna) o verso sinistra (`%5d`, che riempie le colonne
# 58-61 oggi vuote): `printf` in C non tronca mai, quindi le cifre restano
# contigue e in entrambe le forme cadono dentro la coda che comincia alla
# colonna 58. Si legge quindi il primo gruppo di cifre della coda invece di
# una colonna sola, e il tipo si cerca subito dopo quelle cifre: la lettura
# non dipende da quale delle due larghezze abbia il campo. Il benchmark di
# validazione `tests/validazione/test_passi_oltre_nove.py` la misura contro
# `ccx` vero, e ha misurato i passi 1..12 (corsa CI 33088412242).
_COL_VALORE = slice(12, 24)
_COL_CODA = slice(58, None)
_PASSO_NELLA_CODA = re.compile(r"\s*(\d+)")


def leggi_frd(percorso: Path) -> list[Blocco]:
    """I blocchi di un `.frd` ascii, ciascuno con il passo che il file dichiara."""
    blocchi: list[Blocco] = []
    passo, valore, modale = 0, 0.0, False
    grandezza: str | None = None
    nodi: list[int] = []
    righe: list[list[float]] = []
    aperti = chiusi = 0
    righe_del_file = Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines()
    for numero, linea in enumerate(righe_del_file, start=1):
        if linea.startswith("  100CL"):
            coda = linea[_COL_CODA]
            # Il numero di passo si legge prima del valore: un record tagliato
            # prima della colonna 62 -- `ccx` ucciso a meta' scrittura, lo
            # stesso incidente di #93 visto sul record invece che sul blocco --
            # lascia la coda senza cifre, e va nominato qui invece di uscire
            # come un `AttributeError` su `None` che non dice quale file.
            cifre = _PASSO_NELLA_CODA.match(coda)
            if cifre is None:
                raise ValueError(
                    f"{Path(percorso)}, riga {numero}: il record 100CL non porta il "
                    f"numero di passo alla colonna 62, il file è tagliato prima. "
                    f"Riga letta: {linea!r}"
                )
            valore = float(linea[_COL_VALORE])
            passo = int(cifre.group(1))
            modale = coda[cifre.end():].lstrip().startswith("MODAL")
            continue
        if linea.startswith(" -4"):
            aperti += 1
            grandezza = linea.split()[1]
            nodi, righe = [], []
            continue
        if linea.startswith(" -3"):
            if grandezza is not None:
                chiusi += 1
                if righe:
                    blocchi.append(Blocco(
                        grandezza=grandezza, passo=passo, modale=modale, valore=valore,
                        nodi=np.array(nodi, dtype=np.int64),
                        dati=np.array(righe, dtype=np.float64),
                    ))
            grandezza = None
            continue
        if grandezza is not None and linea.startswith(" -1"):
            nodi.append(int(linea[3:13]))
            componenti = (len(linea) - 13) // 12
            righe.append([float(linea[13 + 12 * i:25 + 12 * i]) for i in range(componenti)])
    # #93: un blocco aperto da ` -4` e mai chiuso da ` -3` e' un `.frd`
    # troncato, cioe' una corsa di `ccx` interrotta -- solutore ucciso, disco
    # pieno. Fino a qui veniva scartato senza una parola, e il chiamante
    # riceveva meno risultati di quanti il file ne dichiarasse: esattamente il
    # momento in cui serve saperlo. Il parser solleva, a differenza dei
    # verdetti di questo modulo che riportano (#36).
    #
    # Si contano le chiusure, non i blocchi con dati: un blocco regolarmente
    # chiuso ma senza righe ` -1` e' vuoto, non troncato, e la guardia non
    # deve accusare un file sano. Il conteggio delle chiusure prende anche il
    # taglio a meta' file (un ` -4` che ne segue un altro mai chiuso), che una
    # guardia sul solo stato di fine ciclo si lascerebbe scappare.
    if aperti != chiusi:
        raise ValueError(
            f"{Path(percorso)} dichiara {aperti} blocchi di risultati e ne chiude "
            f"{chiusi}: il file è troncato, la corsa del solutore non l'ha "
            "scritto tutto e i risultati letti sono parziali"
        )
    return blocchi


def _righe_dat(percorso: Path, righe: list[str] | None) -> list[str]:
    """Le righe del `.dat`, lette dal file se il chiamante non le porta gia'.

    `risolvi` chiama tre parser sullo stesso file: leggerlo tre volte per
    intero non serve a nessuno (14.103 nodi e 20 modi non fanno un file
    piccolo). Il parametro e' facoltativo e i tre parser restano chiamabili
    col solo percorso, che e' come li usano i test e chiunque legga un `.dat`
    a mano; il percorso resta comunque richiesto, cosi' l'errore di un file
    mancante continua a nominarlo.

    `errors="ignore"` e non `"replace"`, misurato e non scelto a orecchio: i
    tre parser distinguono una riga di dati da una di intestazione contando i
    campi, e delle due opzioni e' `replace` quella che il conteggio lo cambia.
    Un byte fuori tabella isolato fra due spazi diventa `U+FFFD`, che non e'
    spazio ma nemmeno si attacca ai vicini: e' un campo in piu', la riga non
    passa piu' il suo `len(campi)` e i modi che seguono si perdono. Con
    `ignore` il byte sparisce e i campi restano quelli. Sull'altro caso -- un
    byte incollato fra due cifre -- le due opzioni danno lo stesso conteggio
    (`1.02.0` e `1.0\ufffd2.0` sono entrambi un campo solo), quindi `replace`
    non protegge da niente: il byte non e' uno spazio in nessuna delle due
    letture, e non puo' separare due campi che erano uniti.
    """
    if righe is not None:
        return righe
    return Path(percorso).read_text(encoding="ascii", errors="ignore").splitlines()


def leggi_reazioni(
    percorso: Path, passo: int | None = None, *, righe: list[str] | None = None
) -> dict[int, tuple[float, float, float]]:
    """Reazioni nodali dall'ultimo blocco statico "forces" del `.dat`.

    Righe a quattro campi (nodo piu' tre componenti) dopo l'intestazione delle
    forze -- e solo quelle: un blocco `*NODE PRINT, U` ha righe identiche in
    forma, e `abaqus._passo_statico` scrive gli `U` di `print_nsets` **prima**
    dell'`RF` sul set vincolato. Senza il filtro sull'intestazione, millimetri
    e newton finivano nello stesso dizionario e `controlla_reazioni` li
    sommava. Ultimo blocco vince -- coerente coi passi statici cumulativi
    di `abaqus.write_inp`, dove ogni passo ripete i carichi permanenti dei
    precedenti. La lettura si ferma pero' a `E I G E N V A L U E   O U T P U T`:
    oltre quel punto i blocchi "forces" appartengono ai modi, non ai passi
    statici (vedi il docstring del modulo).

    `passo`, se dato, isola le reazioni di un singolo passo statico invece
    dell'ultimo: ccx scrive una riga `S T E P n` prima di ogni blocco, e
    questa e' la stessa numerazione ordinale del record `100CL` del `.frd`
    (verificato il 21/08/2026 eseguendo `ccx` 2.22 su un deck di prova a
    quattro passi: `S T E P 1..4` per GRAVITA, SPINTA_ORIZZONTALE,
    CARICO_TOP, MODALE, nello stesso ordine). Serve al controllo di
    equilibrio: il passo 1 e' sempre il solo peso proprio, per costruzione di
    `abaqus.write_inp` (la card `peso` e' scritta prima di ogni ramo
    condizionale su `carichi`), quindi confrontabile con `rho*V*g` senza
    conoscere gli altri carichi eventualmente cumulati nei passi successivi.
    """
    reazioni: dict[int, tuple[float, float, float]] = {}
    passo_corrente = 0
    dentro_le_forze = False
    for linea in _righe_dat(percorso, righe):
        if "E I G E N V A L U E   O U T P U T" in linea:
            break
        # Ogni blocco di `*NODE PRINT` si apre con "<grandezza> (...) for set
        # NOME and time ...": l'intestazione accende il filtro sulle forze e
        # qualunque altra lo spegne.
        if " for set " in linea:
            dentro_le_forze = linea.strip().startswith("forces")
            continue
        pulita = linea.strip()
        if pulita.startswith("S T E P"):
            cifre = pulita.replace("S T E P", "").split()
            if cifre:
                passo_corrente = int(cifre[0])
            dentro_le_forze = False
            continue
        if not dentro_le_forze:
            continue
        if passo is not None and passo_corrente != passo:
            continue
        campi = linea.split()
        if len(campi) != 4:
            continue
        try:
            nodo = int(campi[0])
            valori = tuple(float(valore) for valore in campi[1:])
        except ValueError:
            continue
        reazioni[nodo] = valori
    return reazioni


# Regola, dopo cinque giri di revisione sulla stessa classe di difetto
# (Task 7): ogni ingresso che raggiunge un confronto (<, <=, >, >=, o un
# valore derivato da uno di questi) entra nel "cancello di finitezza" della
# funzione -- non solo gli array, non solo il parametro "principale", anche
# gli scalari come una tolleranza o una soglia. La regola era gia' giusta
# cosi' formulata; l'errore nei giri precedenti e' stato applicarla a mente
# invece che enumerando: controlla_picco (p99 NaN -> sopra_p99 tutto False
# -> frazione 0.0 -> passa; poi lo stesso schema su banda) e' un verdetto a
# combinazione booleana (AND/OR), dove un NaN puo' nascondersi dietro un
# False che sembra "in regola". controlla_reazioni/controlla_autovalori
# sono un confronto di grandezza (scarto <= tolleranza, rapporto >=
# soglia_relativa): un NaN li' cade dalla parte giusta da solo, ma un
# infinito con segno dalla parte permissiva del confronto no
# (tolleranza=+inf, soglia_relativa=-inf) -- ragionare solo sul caso NaN lo
# aveva nascosto. L'elenco completo dei parametri e dei tre valori anomali
# (nan, +inf, -inf) vive in `tests/test_solve.py`, tabella
# `_INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO`: chi aggiunge un sesto controllo
# lo aggiunge li', non lo tiene a mente.
def controlla_reazioni(
    reazioni: dict[int, tuple[float, float, float]],
    peso_atteso: tuple[float, float, float],
    tolleranza: float,
) -> dict[str, object]:
    """Confronta la somma delle reazioni con `rho*V*g` come vettore, non come modulo.

    Un modulo giusto con una direzione sbagliata passerebbe un confronto
    scalare: e' esattamente il caso di un vincolo che tiene la struttura di
    sbieco (`*BOUNDARY` su assi sbagliati, o una spinta applicata dove non
    dovrebbe). Il confronto e' quindi sulla norma del vettore differenza,
    relativa alla norma del peso atteso.

    Dizionario vuoto o peso atteso nullo: `passato: False` senza dividere per
    zero, non un'eccezione -- un `.dat` senza il passo richiesto o una
    configurazione senza massa non sono casi da normalizzare, sono casi da
    dichiarare non verificati.

    Cancello di finitezza (Task 7): `passato` chiede `tolleranza` finita
    oltre a `scarto <= tolleranza`. `reazioni`/`peso_atteso` non hanno
    bisogno di guardia propria, perche' propagano in `scarto` (via `norm`):
    NaN o `inf` li' rendono gia' falso quel confronto. `tolleranza` invece
    si', ed e' il lato opposto dello stesso confronto: NaN cade dalla parte
    giusta da solo, ma `tolleranza = +inf` e' soddisfatta da qualunque
    scarto finito -- senza guardia farebbe passare qualunque squilibrio.
    """
    peso = np.asarray(peso_atteso, dtype=np.float64)
    norma_attesa = float(np.linalg.norm(peso))
    if not reazioni or norma_attesa == 0.0:
        return {
            "passato": False,
            "somma": (0.0, 0.0, 0.0),
            "peso_atteso": tuple(float(v) for v in peso_atteso),
            "scarto_relativo": None,
        }
    somma = np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)
    scarto = float(np.linalg.norm(somma - peso) / norma_attesa)
    return {
        "passato": bool(np.isfinite(tolleranza)) and scarto <= tolleranza,
        "somma": tuple(float(v) for v in somma),
        "peso_atteso": tuple(float(v) for v in peso_atteso),
        "scarto_relativo": scarto,
    }


def controlla_autovalori(frequenze_hz: list[float], soglia_relativa: float = 0.2) -> dict[str, object]:
    """Una frequenza (quasi) nulla e' un meccanismo: il vincolo non tiene la
    struttura, la lascia libera di muoversi.

    L'elenco vuoto rifiuta. Altrimenti la prima frequenza (la piu' bassa,
    ccx le estrae in ordine crescente) deve valere almeno `soglia_relativa`
    volte la seconda: un vero meccanismo esce ordini di grandezza sotto le
    altre, non una frazione confrontabile. La soglia e' relativa e non in Hz
    assoluti perche' l'Hz e' scala del pezzo (massa, rigidezza), non del
    prodotto -- un numero assoluto qui sarebbe un numero del provino dentro
    `src/`. Misurato il 21/08/2026 sull'as-built del telaio: 21,19 Hz col
    vincolo corretto, 4,03 Hz col vincolo su un piede solo (rapporto a
    seconda frequenza comunque sopra soglia in entrambi i casi con vincolo
    presente; il meccanismo vero, prima frequenza praticamente nulla, e' un
    altro ordine di grandezza).

    Cancello di finitezza (Task 7): senza la guardia su `frequenze_hz`, una
    prima frequenza infinita passerebbe (`inf > 0.0` e' vero, `inf /
    seconda >= soglia_relativa` pure) -- il valore resta riportato in
    `prima_frequenza_hz`, ma `passato` e' sempre `False` se una qualunque
    frequenza non e' finita. `soglia_relativa` ha una guardia propria, ma
    solo sul ramo a due o piu' frequenze: li' la consulta il confronto
    `rapporto >= soglia_relativa`, e `soglia_relativa = -inf` sarebbe
    superata da qualunque rapporto, cioe' non filtrerebbe piu' niente (NaN
    e `+inf` cadrebbero invece dalla parte giusta da soli). Sul ramo a una
    sola frequenza il verdetto e' `prima > 0.0` e nessun confronto legge la
    soglia: li' la guardia non si applica, altrimenti un parametro inerte
    boccerebbe dati buoni.
    """
    if not frequenze_hz:
        return {"passato": False, "prima_frequenza_hz": None}
    finito = bool(np.isfinite(frequenze_hz).all())
    prima = float(frequenze_hz[0])
    if len(frequenze_hz) == 1:
        return {"passato": finito and prima > 0.0, "prima_frequenza_hz": prima}
    seconda = float(frequenze_hz[1])
    rapporto = prima / seconda if seconda != 0.0 else 0.0
    return {
        "passato": (
            finito
            and bool(np.isfinite(soglia_relativa))
            and prima > 0.0
            and rapporto >= soglia_relativa
        ),
        "prima_frequenza_hz": prima,
        "rapporto_prima_seconda": rapporto,
    }


def controlla_picco(valori: np.ndarray, quote: np.ndarray, banda: float) -> dict[str, object]:
    """max/p99 e dove vive il picco: non basta che sia alto, conta se cade
    dentro la banda di vincolo.

    Misurato il 21/08/2026 sulla corsa dell'as-built, sui tre casi: max/p99
    vale 2,16 sotto peso proprio, 2,54 sotto spinta orizzontale e 2,50 sotto
    il carico in sommita'. In tutti e tre il massimo cade sullo **stesso**
    nodo -- indice 7132 nel `.vtu`, che e' il nodo 7133 del deck perche'
    `write_vtu` scrive gli indici a base zero -- all'89% dell'altezza del
    pezzo, nella membratura di sommita': fuori dalla banda di vincolo e
    fuori dal set TOP dove il carico e' applicato. E' una
    singolarita' della geometria del maglio, non un artefatto del carico --
    se lo fosse, il picco si sposterebbe coi carichi. Dei 142 nodi sopra il
    p99 nessuno cade entro la banda di vincolo, in nessuno dei tre casi.
    Il controllo non dice se il picco e' alto: dice se vive dentro la banda
    vicino alla base, dove un vincolo o un carico concentrato produce numeri
    grandi e non rappresentativi del pezzo.

    p99 nullo (tensioni tutte a zero): `rapporto_max_p99` e' `None`, mai un
    `nan` silenzioso da una divisione 0/0. Un solo nodo: il percentile e'
    quel nodo stesso, nessun `IndexError`.

    Cancello di finitezza (Task 7, tre giri sulla stessa classe): il
    verdetto e' una combinazione booleana (`finito and frazione_in_banda ==
    0.0`), non un unico confronto di grandezza -- ogni NaN che finisce in un
    confronto sotto puo' quindi mascherarsi da esito buono, ed e' successo
    due volte. Prima su `passato` stesso (`p99` NaN -> `sopra_p99 = v >=
    p99` tutto `False` -> `frazione_in_banda` 0.0 -> "va bene" sul dato
    corrotto). Poi su `banda`: derivato a monte da `np.ptp(nodes[:, 2])` su
    *tutti* i nodi del modello, non sul sottoinsieme del caso di carico
    corrente (`quote`) -- un nodo NaN altrove nel modello corrompe `banda`
    senza toccare `v`/`q`, e `q <= q.min() + banda` con `banda` NaN da'
    tutto `False` con lo stesso schema. La guardia quindi copre tutti e tre
    i parametri che raggiungono un confronto (`v`, `q`, `banda`), non solo
    gli array. `max`/`p99` restano riportati anche se NaN o infiniti (si
    marca, non si nasconde), ma `passato` e' sempre `False` in quel caso.
    """
    v = np.asarray(valori, dtype=np.float64)
    q = np.asarray(quote, dtype=np.float64)
    # `leggi_frd` non produce mai un blocco vuoto, quindi in produzione non ci
    # si arriva: e' latente. Ma senza guardia schianta con «zero-size array to
    # reduction operation maximum», che accusa numpy di un errore che sta a
    # monte. Stesso trattamento che `risolvi` da' a `casi_di_carico` vuoto: un
    # errore del chiamante, dichiarato come tale invece che mascherato da
    # verdetto.
    if v.size == 0 or q.size == 0:
        raise ValueError(
            "valori o quote vuoti: non c'è un picco da localizzare. È un errore "
            "del chiamante, non uno stato da valutare a vuoto"
        )
    finito = bool(np.isfinite(v).all() and np.isfinite(q).all() and np.isfinite(banda))
    massimo = float(v.max())
    p99 = float(np.percentile(v, 99))
    rapporto = None if p99 == 0.0 or np.isnan(p99) else massimo / p99
    sopra_p99 = v >= p99
    in_banda = q <= float(q.min()) + banda
    n_sopra = int(sopra_p99.sum())
    frazione_in_banda = float((sopra_p99 & in_banda).sum() / n_sopra) if n_sopra else 0.0
    return {
        "passato": finito and frazione_in_banda == 0.0,
        "max": massimo,
        "p99": p99,
        "rapporto_max_p99": rapporto,
        "frazione_in_banda": frazione_in_banda,
    }


def controlla_vincolo_in_pianta(minimo: float) -> dict[str, object]:
    """L'insieme vincolato attraversa abbastanza dell'impronta del pezzo?

    `minimo` e' `abaqus.constraint_plan_extent(...)["minimo"]`, gia' calcolato
    allo step 11 e passato a `risolvi` invece di essere ricalcolato qui, dove
    i `node_sets` non arrivano.

    Cancello di finitezza (Task 7, riga aggiunta nel giro della revisione
    finale): il verdetto e' un confronto di grandezza, dove NaN cade dalla
    parte giusta da solo ma `+inf >= soglia` no. Un `minimo` non finito non
    puo' arrivare da `constraint_plan_extent`, e non per il motivo scritto
    prima qui (un limite dichiarato fuori perimetro): per **contenimento**.
    Quella funzione divide l'estensione dei nodi *scelti* per quella di tutti
    i nodi, e i primi sono un sottoinsieme dei secondi -- il rapporto sta fra
    0 e 1 per costruzione, e l'unica via per un NaN e' che le coordinate in
    ingresso lo siano gia'. La guardia c'e' lo stesso perche' la regola del
    modulo e' enumerare gli ingressi che raggiungono un confronto, non
    ragionare caso per caso su quali possano davvero degenerare: e' lo stesso
    motivo per cui `_TOLLERANZA_REAZIONI`, che e' una costante di modulo,
    passa comunque per `np.isfinite`.
    """
    return {
        "passato": bool(np.isfinite(minimo)) and minimo >= _SOGLIA_VINCOLO_IN_PIANTA,
        "minimo": minimo,
        "soglia": _SOGLIA_VINCOLO_IN_PIANTA,
    }


def controlla_avvisi(conteggio: int) -> dict[str, object]:
    """Zero `*WARNING` da `ccx`, o i numeri non sono citabili.

    Il conteggio viene da `str.count` e resta un intero naturale qualunque
    cosa faccia la mesh: l'uguaglianza a zero e' gia' chiusa su NaN e sugli
    infiniti senza bisogno di guardia. Sta comunque nella tabella
    `_INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO` -- enumerare tutti e sette i
    verdetti costa meno che ricordarsi quale dei sette non serviva.
    """
    return {"passato": conteggio == 0, "conteggio": conteggio}


# I due modelli su cui i sette verdetti possono girare. Non sono i due
# solutori: la validita' dipende dal MODELLO, non da chi lo risolve. Un telaio
# ad aste ha spostamenti nodali come un solido, ma non ha una tensione
# equivalente per nodo, e nessun cambio di solutore gliela da'.
MODELLI = ("solido", "telaio")

# La tabella che #138 Q3 obbliga a scrivere PRIMA di portare un controllo al
# secondo modello, e non a dedurre dopo.
#
# Il motivo per cui va scritta prima non e' una formalita': un controllo
# eseguito su un modello dove la sua grandezza non significa niente produce un
# numero verde che non vale nulla, ed e' precisamente la classe di falso che
# tutti i verdetti di questo modulo esistono per non produrre. Un «vale» dato
# per scontato non lascia traccia; un «non vale» scritto qui la lascia.
#
# Ogni casella e' "vale" oppure "non vale: <ragione>". Chi la consuma passa da
# `esito_non_applicabile`, che su una casella «non vale» rende un esito mai
# verde invece di far girare il controllo.
#
# Le caselle del telaio sono misurate su questa macchina il 30/08/2026
# eseguendo `OpenSees` 3.8.0 su script di prova, non lette dal manuale:
# `eigen` rende gli autovalori, `recorder Node ... reaction` le reazioni,
# `recorder Node ... disp` gli spostamenti, `modalProperties -print -file` le
# percentuali cumulate di massa partecipante per MX, MY e MZ.
CONTROLLI_PER_MODELLO: dict[str, dict[str, str]] = {
    "reazioni": {
        "solido": "vale",
        # Il confronto e' fra la somma delle reazioni e `rho*V*g` come vettore:
        # e' equilibrio globale, e non dipende dal tipo di elemento. Cambia il
        # solo termine correttivo: `_quota_tributaria_gravita` esiste perche'
        # `ccx` non include nella `RF` la quota di gravita' che gli elementi
        # applicano ai nodi vincolati, e le sue due formule sono quelle delle
        # funzioni di forma di C3D4 e C3D10 -- solleva su ogni altro tipo. Sul
        # telaio il peso proprio e' ripartito sui nodi meta' per estremo
        # (`opensees._peso_nodale`, e li' e' scritto perche' non
        # `eleLoad -type -beamUniform`), quindi il carico applicato a un nodo
        # vincolato entra intero nella sua reazione: il termine correttivo vale
        # zero, non e' un'altra formula da scrivere.
        "telaio": "vale",
    },
    "vincolo_in_pianta": {
        "solido": "vale",
        "telaio": (
            "non vale: la misura è l'estensione in pianta dei nodi vincolati "
            "rapportata a quella di TUTTI i nodi del modello "
            "(abaqus.constraint_plan_extent), e nel telaio i nodi stanno "
            "sull'asse delle membrature. Su un telaio a una sola colonna quel "
            "denominatore è ZERO: la funzione ha un ramo di guardia che in quel "
            "caso rende 1,0 -- «un pezzo senza estensione su un asse non ha "
            "nulla da coprire» -- e controlla_vincolo_in_pianta(1,0) passa "
            "verde su un modello dove la grandezza non misura niente. Misurato "
            "il 30/08/2026 su una mensola verticale con un solo nodo "
            "vincolato: {'x': 1.0, 'y': 1.0, 'minimo': 1.0}, verdetto "
            "«passato: True»"
        ),
    },
    "autovalori": {"solido": "vale", "telaio": "vale"},
    "avvisi": {
        "solido": "vale",
        # `controlla_avvisi` prende un intero e chiede che sia zero: il
        # confronto e' neutro rispetto al solutore, cambia chi conta. `ccx`
        # marca `*WARNING` con l'asterisco; OpenSees 3.8.0 scrive `WARNING`
        # senza -- misurato: «WARNING - no torsion specified for 3D fiber
        # section, use -GJ or -torsion». Chi contasse `*WARNING` sull'uscita di
        # OpenSees conterebbe sempre zero, cioe' avrebbe un verdetto verde per
        # costruzione. Il marcatore di `ccx` sta in `_MARCA_AVVISO_CCX`.
        "telaio": "vale",
    },
    "spostamenti": {"solido": "vale", "telaio": "vale"},
    "massa_modale": {
        "solido": "vale",
        # `leggi_massa_modale` legge i blocchi del `.dat` di `ccx` e su OpenSees
        # non vale, ma il verdetto `controlla_massa_modale` consuma
        # `{"catturata", "disponibile"}` e non un formato: cambia la sorgente,
        # non la grandezza. Su OpenSees la sorgente e' il rapporto cumulato che
        # `modalProperties` stampa (`opensees.leggi_massa_modale`).
        "telaio": "vale",
    },
    "picco": {
        "solido": "vale",
        "telaio": (
            "non vale: il verdetto è su una tensione equivalente per NODO e "
            "sulla quota del suo picco. Il telaio non ha una tensione per nodo "
            "-- le sue grandezze sono N, V e M per elemento, e la tensione vive "
            "per fibra dentro la sezione. Un max/p99 sulle fibre è un'altra "
            "grandezza, e la banda di vincolo di `controlla_picco` non vi si "
            "applica"
        ),
    },
}


def esito_non_applicabile(controllo: str, modello: str) -> dict[str, object] | None:
    """`None` se il controllo vale su quel modello, altrimenti l'esito che lo dichiara.

    Si usa come `esito_non_applicabile(c, m) or controlla_...(...)`: dove la
    tabella dice «non vale» il controllo **non viene eseguito**, e l'esito che
    esce non e' mai verde -- `passato: False` con `applicabile: False` e il
    motivo. E' diverso da un `passato: False` per dati cattivi, e chi legge
    `metrics.json` deve poterli distinguere: il primo dice «questa domanda non
    ha senso qui», il secondo «la risposta e' no».

    Un controllo o un modello che la tabella non conosce **solleva** invece di
    valere «vale»: un refuso che rendesse `None` farebbe girare il controllo su
    un modello mai dichiarato, cioe' esattamente il verde su nulla per cui la
    tabella esiste.
    """
    if controllo not in CONTROLLI_PER_MODELLO:
        raise KeyError(
            f"controllo '{controllo}' non dichiarato in CONTROLLI_PER_MODELLO: "
            f"i sette sono {sorted(CONTROLLI_PER_MODELLO)}"
        )
    if modello not in MODELLI:
        raise KeyError(f"modello '{modello}' sconosciuto: i modelli sono {list(MODELLI)}")
    verdetto = CONTROLLI_PER_MODELLO[controllo][modello]
    if verdetto == "vale":
        return None
    return {
        "passato": False,
        "applicabile": False,
        "controllo": controllo,
        "modello": modello,
        "motivo": verdetto,
    }


def verdetti_per_modello(
    modello: str,
    calcolo: Mapping[str, Callable[[], dict[str, object]]],
) -> dict[str, dict[str, object]]:
    """I sette verdetti di un modello, tutti e sette passati per la tabella.

    Il consumatore porta i **calcoli**, uno per controllo, e non i verdetti:
    quali girino lo decide `CONTROLLI_PER_MODELLO`. Finché i verdetti si
    scrivono a mano -- come faceva `risolvi` -- la tabella è documentazione e
    non un vincolo, e la via al verde su un controllo non applicabile resta
    aperta. Misurata su una mensola: `abaqus.constraint_plan_extent` rende
    `minimo = 1,0` (il ramo di guardia del denominatore nullo, perché i nodi
    stanno tutti su una verticale) e `controlla_vincolo_in_pianta(1,0)` dice
    `passato: True`, mentre la tabella dice `applicabile: False`.

    Su un controllo che la tabella dichiara **non applicabile** il calcolo, se
    c'è, non viene chiamato: vince la tabella, e l'esito che esce è quello che
    dichiara la non applicabilità. È la proprietà per cui questa funzione
    esiste -- il verde non è raggiungibile per quella strada nemmeno da chi
    porta il calcolo.

    Due rifiuti:

    - un calcolo per un controllo che la tabella **non conosce**: sarebbe un
      ottavo verdetto mai dichiarato, e quasi sempre è un refuso;
    - un controllo applicabile **senza** il suo calcolo: sette meno uno non è
      sei verdetti, è un verdetto perso in silenzio.

    I calcoli sono funzioni senza argomenti e non valori già calcolati: dove la
    tabella dice «non vale» il controllo non viene **eseguito**, e non solo
    scartato dopo. Sul telaio la tensione equivalente per nodo non esiste, e
    calcolarla per buttarla via vorrebbe dire prima inventarla.
    """
    ignoti = sorted(set(calcolo) - set(CONTROLLI_PER_MODELLO))
    if ignoti:
        raise KeyError(
            f"calcolo per {ignoti}, che CONTROLLI_PER_MODELLO non dichiara: i "
            f"controlli sono {sorted(CONTROLLI_PER_MODELLO)}"
        )
    applicabili = {
        controllo
        for controllo in CONTROLLI_PER_MODELLO
        if esito_non_applicabile(controllo, modello) is None
    }
    mancanti = sorted(applicabili - set(calcolo))
    if mancanti:
        raise KeyError(
            f"il modello '{modello}' non porta il calcolo di {mancanti}, che la "
            "tabella dichiara applicabile: sette meno uno non è sei verdetti, è "
            "un verdetto perso in silenzio"
        )
    return {
        controllo: esito_non_applicabile(controllo, modello) or calcolo[controllo]()
        for controllo in CONTROLLI_PER_MODELLO
    }


def _spostamento_massimo(point_data: dict[str, np.ndarray]) -> float | None:
    """Il piu' grande spostamento nodale fra i soli passi **statici**.

    Filtra su `U_`: i campi `MODO_n` sono forme normalizzate sulla massa, non
    spostamenti fisici (vedi il docstring del modulo), e la loro ampiezza non
    significa nulla -- confonderli qui darebbe un verdetto su una grandezza
    priva di unita'. `VM_` e' una tensione e non entra.

    `None` se non c'e' alcun passo statico: un deck solo modale non ha uno
    spostamento da misurare, e `controlla_spostamenti` lo dichiara non
    verificato invece di inventare uno zero.
    """
    massimi = [
        float(np.max(np.linalg.norm(np.asarray(campo, dtype=np.float64), axis=1)))
        for nome, campo in point_data.items()
        if nome.startswith("U_") and np.asarray(campo).ndim == 2 and len(campo)
    ]
    return max(massimi) if massimi else None


def _dimensione(nodes: np.ndarray) -> float:
    """Diagonale del parallelepipedo contenitore: la scala con cui confrontare
    uno spostamento. Vedi la nota sopra `_SOGLIA_SPOSTAMENTO_SU_DIMENSIONE`
    sul perche' non serva una misura invariante per rotazione."""
    punti = np.asarray(nodes, dtype=np.float64)
    if len(punti) == 0:
        return 0.0
    return float(np.linalg.norm(np.ptp(punti, axis=0)))


def controlla_spostamenti(
    u_max: float | None, dimensione: float, soglia: float = _SOGLIA_SPOSTAMENTO_SU_DIMENSIONE
) -> dict[str, object]:
    """Lo spostamento massimo contro la dimensione del modello (#12).

    Sesto verdetto, e l'unico che guarda l'**ampiezza** del risultato invece
    della coerenza fra il deck e cio' che la configurazione crede. Serve
    perche' un modello mal vincolato -- o con un pezzo staccato -- produce
    numeri enormi senza che `ccx` protesti: codice d'uscita 0, zero
    `*WARNING`, e gli altri sei verdetti verdi. Il motivo per cui gli
    altri sei non bastano sta per esteso sopra
    `_SOGLIA_SPOSTAMENTO_SU_DIMENSIONE`, col numero misurato.

    Non solleva: marca. Stessa scelta di `wall.controlla` e degli altri
    cinque verdetti -- l'esito resta scritto col numero che lo ha deciso e la
    soglia con cui e' stato confrontato, perche' chi legge `metrics.json`
    possa vedere *quale* controllo ha detto no e *quanto*. `risolvi` scrive
    `13_solution.vtu` **prima** di valutare i verdetti (la chiamata a
    `abaqus.write_vtu` precede il dizionario `controlli`; i due nomi e non i
    due numeri di riga, che slittano a ogni fusione): sollevare qui
    lascerebbe quel file su disco senza che il chiamante
    ne riceva mai il percorso, cioe' toglierebbe l'unico modo di **guardare**
    dove il modello e' scappato proprio nel caso in cui serve.

    `u_max` assente (`None`) significa nessun passo statico da misurare -- un
    deck solo modale, dove `MODO_n` e' una forma normalizzata sulla massa e
    non uno spostamento fisico. Come per `controlla_reazioni` su un `.dat`
    senza reazioni, non e' un caso da normalizzare ma da dichiarare **non
    verificato**: `passato: False` con `rapporto: None`.

    Cancello di finitezza: entrambi gli ingressi raggiungono un confronto e
    hanno bisogno di guardia, per motivi opposti. `u_max` non finito e' il
    caso guasto per eccellenza (un solutore che diverge stampa `inf`) e deve
    fallire; `dimensione` non finita o nulla renderebbe il rapporto NaN o una
    divisione per zero. Nessuno dei due e' un ingresso della pipeline -- i
    nodi arrivano gia' finiti allo step 11 -- ma la regola del modulo e'
    enumerare gli ingressi che raggiungono un confronto, non ragionare caso
    per caso su quali possano davvero degenerare.
    """
    fuori = (
        u_max is None
        or not np.isfinite(u_max)
        or not np.isfinite(dimensione)
        or not np.isfinite(soglia)
        or dimensione <= 0.0
    )
    if fuori:
        return {
            "passato": False,
            "rapporto": None,
            "u_max": None if u_max is None else float(u_max),
            "dimensione": float(dimensione),
            "soglia": float(soglia),
        }
    rapporto = float(abs(u_max) / dimensione)
    return {
        "passato": rapporto < float(soglia),
        "rapporto": rapporto,
        "u_max": float(u_max),
        "dimensione": float(dimensione),
        "soglia": float(soglia),
    }


_INTESTAZIONE_MODALE = "E F F E C T I V E   M O D A L   M A S S"
_INTESTAZIONE_TOTALE = "T O T A L   E F F E C T I V E   M A S S"


def leggi_massa_modale(
    percorso: Path, *, righe: list[str] | None = None
) -> dict[str, list[float]] | None:
    """Massa modale efficace dal `.dat`: quella catturata e quella disponibile.

    `ccx` scrive tre blocchi dopo `E I G E N V A L U E   O U T P U T` e finora
    non li leggeva nessuno: fattori di partecipazione, **massa modale
    efficace** per modo (con una riga `TOTAL` che somma i modi estratti) e
    **massa efficace totale**, cioe' quella che i modi potrebbero catturare
    tutti insieme. Il rapporto fra i due totali e' la frazione di massa che
    l'analisi ha davvero preso.

    Sei componenti in entrambi: tre traslazioni e tre rotazioni.

    `None` se il blocco non c'e' -- un deck senza passo modale, oppure un passo
    modale che non ha estratto nulla. Non e' uno zero: zero significherebbe
    «i modi non catturano massa», che e' un'altra cosa e sarebbe un difetto.
    """
    righe = _righe_dat(percorso, righe)

    def sei_numeri(riga: str, salta: int = 0) -> list[float] | None:
        campi = riga.split()[salta:]
        if len(campi) != 6:
            return None
        try:
            return [float(c) for c in campi]
        except ValueError:
            return None

    catturata: list[float] | None = None
    disponibile: list[float] | None = None
    for indice, riga in enumerate(righe):
        if _INTESTAZIONE_MODALE in riga:
            # la riga `TOTAL` somma i soli modi estratti
            for seguente in righe[indice:]:
                if seguente.strip().startswith("TOTAL"):
                    catturata = sei_numeri(seguente, salta=1)
                    break
        elif _INTESTAZIONE_TOTALE in riga:
            # dopo l'intestazione e la riga dei nomi di colonna, la prima riga
            # con sei numeri e' il totale disponibile
            for seguente in righe[indice + 1 :]:
                valori = sei_numeri(seguente)
                if valori is not None:
                    disponibile = valori
                    break
    if catturata is None or disponibile is None:
        return None
    return {"catturata": catturata, "disponibile": disponibile}


def controlla_massa_modale(
    masse: dict[str, list[float]] | None, soglia: float = _FRAZIONE_MASSA_MINIMA
) -> dict[str, object]:
    """Quanta massa partecipante i modi estratti catturano (#75).

    Settimo verdetto. Gli altri sei guardano il passo statico o l'ampiezza del
    risultato; questo e' l'unico che guarda se l'**analisi modale** ha chiesto
    abbastanza modi. `controlla_autovalori` verifica che le frequenze siano
    reali, positive e non degeneri, e nulla di piu': un'analisi che estragga
    tre modi su una struttura che ne vorrebbe cento le supera tutte.

    Il verdetto e' sulle sole **traslazioni**. Le componenti rotazionali hanno
    unita' diverse (massa per lunghezza al quadrato) e il loro «totale
    disponibile» dipende dal polo scelto, quindi una frazione su quelle non e'
    confrontabile con la stessa soglia. Restano scritte, perche' chi legge
    possa guardarle.

    **Non e' un cancello sul modello.** Una frazione sotto soglia non dice che
    il modello sia sbagliato: dice che il **numero di modi chiesto** e'
    insufficiente, ed e' un parametro di configurazione (`Modale.modi`). Il
    verdetto lo riporta come gli altri sei, si marca e non si nasconde.

    `masse` a `None` -- nessun blocco modale nel `.dat` -- da' `passato: False`
    con `frazione_minima: None`: non verificato, non «zero massa catturata».
    Stessa convenzione di `controlla_reazioni` su un `.dat` senza reazioni.
    """
    if masse is None:
        return {
            "passato": False, "frazione_minima": None, "soglia": float(soglia),
            "per_direzione": None, "direzione_peggiore": None,
        }

    catturata = np.asarray(masse["catturata"], dtype=np.float64)[:3]
    disponibile = np.asarray(masse["disponibile"], dtype=np.float64)[:3]
    nomi = ("x", "y", "z")

    per_direzione: dict[str, float | None] = {}
    frazioni: list[float] = []
    for nome, presa, totale in zip(nomi, catturata, disponibile, strict=True):
        # Massa disponibile nulla in una direzione: la struttura e' vincolata
        # li' e non c'e' nulla da catturare. Non e' un fallimento, e dividere
        # darebbe un NaN che il confronto tratterebbe come «non passato».
        if not np.isfinite(totale) or totale <= 0.0 or not np.isfinite(presa):
            per_direzione[nome] = None
            continue
        frazione = float(presa / totale)
        per_direzione[nome] = frazione
        frazioni.append(frazione)

    if not frazioni:
        return {
            "passato": False, "frazione_minima": None, "soglia": float(soglia),
            "per_direzione": per_direzione, "direzione_peggiore": None,
        }

    minima = min(frazioni)
    peggiore = min(
        (n for n in nomi if per_direzione[n] is not None),
        key=lambda n: per_direzione[n],
    )
    return {
        "passato": bool(np.isfinite(soglia) and minima >= soglia),
        "frazione_minima": minima,
        "soglia": float(soglia),
        "per_direzione": per_direzione,
        "direzione_peggiore": peggiore,
        # Le rotazionali restano scritte ma fuori dal verdetto: unita' diverse,
        # e il totale disponibile dipende dal polo.
        "rotazionali_catturate": [float(v) for v in masse["catturata"][3:]],
        "rotazionali_disponibili": [float(v) for v in masse["disponibile"][3:]],
    }


def leggi_frequenze(percorso: Path, *, righe: list[str] | None = None) -> list[float]:
    """Le frequenze proprie [Hz]: colonna CYCLES/TIME del blocco MODE NO del `.dat`.

    Il blocco e' una tabella libera (nessuna colonna incollata, a differenza
    del `.frd`): la riga di intestazione fa da ancora, le righe dati hanno
    cinque campi con il primo intero, e il blocco finisce alla prima riga
    vuota dopo che almeno un modo e' stato letto.
    """
    frequenze: list[float] = []
    dentro = False
    for linea in _righe_dat(percorso, righe):
        if "MODE NO" in linea and "EIGENVALUE" in linea:
            dentro = True
            continue
        if not dentro:
            continue
        campi = linea.split()
        if len(campi) != 5 or not campi[0].isdigit():
            if frequenze:
                break
            continue
        frequenze.append(float(campi[3]))
    return frequenze


def von_mises(tensioni: np.ndarray) -> np.ndarray:
    """Tensione equivalente da sei componenti nell'ordine di CalculiX.

    L'ordine e' SXX, SYY, SZZ, SXY, SYZ, SZX: leggerlo sbagliato non solleva
    nulla e produce un numero plausibile, che e' il modo peggiore di sbagliare.

    **Verificato contro `ccx` vero il 26/08/2026**, non piu' assunto (#39). Fino
    ad allora la formula aveva due oracoli analitici solidi e la **mappatura non
    ne aveva nessuno**: gli `.frd` dei test li scriveva il test stesso, con
    trazione monoassiale `(sigma, 0, 0, 0, 0, 0)`, che e' invariante rispetto a
    qualunque permutazione dentro il gruppo dei normali e dentro quello dei
    taglianti. Nessun riordino la cambiava, quindi nessun riordino la faceva
    cadere.

    La prova sta in `tests/validazione/test_ordine_frd.py`: un campo di
    spostamento lineare imposto su tutto il bordo produce uno stato costante con
    tutte e sei le componenti distinte e ben separate, e le sei colonne lette dal
    file si confrontano una per una con la legge di Hooke. Un secondo test prova
    che **tutte e 719 le permutazioni** diverse dall'identita' verrebbero
    respinte, cioe' che il confronto discrimina invece di limitarsi a passare.
    """
    s = np.asarray(tensioni, dtype=np.float64)
    normali = 0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
    taglianti = 3.0 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2)
    return np.sqrt(normali + taglianti)


def _volume_totale(nodes: np.ndarray, elements: np.ndarray) -> float:
    """Volume della mesh di volume. Solo tetraedri (Minor M1 della revisione
    del Task 7): `risolvi()` gira su output di `TetConfig` o di `ModelConfig`
    C3D8*, ma nessun chiamante in produzione passa mai una mesh esaedrica
    qui -- zero copertura sul ramo, generalita' non richiesta. Il ramo
    esaedrico si riaggiunge (`quality.hex_volumes`) quando un chiamante hex
    esiste davvero.
    """
    volumi = quality.tet_volumes(nodes, elements[:, :4])
    return float(np.abs(volumi).sum())


def _quota_tributaria_gravita(
    nodes: np.ndarray,
    elements: np.ndarray,
    nodi_1based: Iterable[int],
    density: float,
    element_type: str,
) -> float:
    """Massa che il carico distribuito assegna direttamente ai nodi dati.

    **Dipende dall'elemento, e ignorarlo era un difetto vivo (#40).** La
    ripartizione della gravita' fra i nodi di un elemento e' il vettore dei
    carichi consistenti, cioe' l'integrale delle funzioni di forma, e le
    funzioni di forma del tetraedro quadratico non sono quelle del lineare:

    - **C3D4**: `+V/4` a ciascuno dei quattro vertici (le funzioni di forma
      sono lineari e il loro integrale e' `V/4`);
    - **C3D10**: `-V/20` a ciascun **vertice** -- negativo, non e' un errore
      di segno -- e `+V/5` a ciascuno dei sei **nodi di lato**. La somma
      torna: `4*(-1/20) + 6*(1/5) = 1`.

    Fino al 26/08/2026 questa funzione applicava `V/4` ai soli vertici
    qualunque fosse l'elemento. Su C3D4 era esatto; su **C3D10, predefinito
    dalla PR #53**, era sbagliato -- e non di poco, perche' sbagliava anche
    di **segno** sui vertici e ignorava del tutto i nodi di lato, che sono
    quelli che portano il carico. Misurato su un cubo con quattro
    raffinamenti: col termine sbagliato lo scarto valeva 1,67e-01, 9,29e-02,
    6,67e-02, 5,79e-02 -- sempre oltre la tolleranza di 1e-4, quindi il
    verdetto `reazioni` era **falso su ogni corsa C3D10**; col termine giusto
    vale 1,8e-08, 4,0e-08, 5,3e-09, 2,6e-09, cioe' precisione di solutore.
    Nessun test lo vedeva perche' nessun test esegue la pipeline vera con
    `ccx` vero (i test di `risolvi` usano un `ccx` finto).

    Lo scarto del termine sbagliato **calava raffinando** -- 1,67e-01 ->
    5,79e-02 -- che e' la firma di un rapporto bordo/volume, cioe' di un
    artefatto di maglio. E' la stessa firma che l'indagine del 21/08/2026
    aveva gia' incontrato su C3D4 e che allora aveva portato fuori strada:
    la stessa trappola, sullo stesso controllo, un elemento piu' tardi.

    Causa radice del termine, trovata dall'indagine del 21/08/2026: la `RF`
    che `ccx` stampa per un nodo vincolato che porta anche `*DLOAD, GRAV`
    non include la quota di gravita' applicata a quel nodo dagli elementi
    che lo toccano -- riporta solo la forza trasmessa elasticamente
    attraverso la struttura. Prova in forma chiusa su C3D4: un tetraedro
    solo, base fissa, apice libero -- `rho*V*g` = 2,943 N, `ccx` stampa
    0,73575 N (esattamente 1/4, la sola quota del nodo libero). Il manuale
    di CalculiX (§6.11.5) lo dichiara: «selecting RF gives you the sum of
    the reaction forces and the loading forces».

    Il manuale indica `*SECTION PRINT, SOF` come alternativa. **Misurata e
    scartata** (#40): `SOF` e' l'integrale della tensione sulla superficie,
    quindi porta l'errore di discretizzazione e **converge** col maglio --
    su C3D4 sbaglia dal 21,0% al 6,6% raffinando, su C3D10 dal 2,3% all'1,1%
    -- mentre `RF` piu' questo termine e' un'**identita' algebrica**, ferma
    a 1e-8 su ogni maglio. Un controllo di conservazione col 6,6% di residuo
    non puo' avere tolleranza 1e-4, e soprattutto confonderebbe «il modello
    e' sbagliato» con «il maglio e' rado»: e' proprio la distinzione per cui
    il controllo esiste.

    `element_type` e' **obbligatorio e senza predefinito**, di proposito: un
    predefinito `"C3D4"` renderebbe il difetto qui sopra invisibile una
    seconda volta, perche' il chiamante che se ne dimentica prende in
    silenzio la formula sbagliata proprio sull'elemento che il progetto usa
    per predefinito. Un tipo fuori dai due noti solleva invece di prendere
    la formula di un altro elemento: sarebbe un numero plausibile e
    sbagliato, che e' la cosa peggiore che questo modulo possa rendere.
    """
    # Le due guardie prima del return anticipato, non dopo: a insieme vuoto lo
    # zero e' il numero giusto, ma renderlo senza guardare gli argomenti fa
    # passare in silenzio un `element_type` ignoto e un array di forma
    # sbagliata, e l'oracolo «C3D10 a quattro colonne solleva» varrebbe solo a
    # insieme non vuoto senza che nulla lo dica. Parla prima il tipo: senza un
    # tipo noto non c'e' un numero di colonne atteso da confrontare.
    if element_type not in ("C3D4", "C3D10"):
        raise ValueError(
            f"la ripartizione della gravità non è definita per '{element_type}': "
            "il vettore dei carichi consistenti dipende dalle funzioni di forma, "
            "e un valore preso da un altro elemento sarebbe un numero plausibile "
            "e sbagliato"
        )
    # Le colonne, non solo il nome: su C3D10 la fetta `elements[:, 4:10]` prende
    # i nodi di lato che ci sono, non quelli che servono. Con quattro colonne ne
    # prende zero e resta il solo `-V/20` dei vertici, cioe' `-0,2*V`; con nove
    # ne prende cinque su sei e la somma vale `+0,8*V`. Il segno cambia col
    # numero di colonne, l'errore no -- e nessuno dei due casi solleva da se'.
    # `export_model` valida a monte, ma qui si arriva anche per chiamata diretta
    # (test e script di cantiere).
    attesi = abaqus.NODI_PER_ELEMENTO[element_type]
    if elements.shape[1] < attesi:
        raise ValueError(
            f"{element_type} vuole {attesi} nodi per elemento, ne sono arrivati "
            f"{elements.shape[1]}: la ripartizione perde i nodi di lato che "
            "mancano, e rende un peso sbagliato -- negativo se mancano tutti"
        )
    nodi_1based = list(nodi_1based)
    if not nodi_1based:
        return 0.0
    # Il volume e' quello del tetraedro a spigoli dritti: le quattro colonne
    # dei vertici bastano per entrambi i tipi, e su C3D10 i nodi di lato di
    # TetGen stanno a meta' spigolo (non c'e' curvatura da integrare).
    volumi = np.abs(quality.tet_volumes(nodes, elements[:, :4]))
    massa = volumi * density
    in_set = np.zeros(len(nodes), dtype=bool)
    in_set[np.array(nodi_1based, dtype=np.int64) - 1] = True

    # La somma corre per ogni coppia (elemento, nodo del set) che l'elemento
    # incide -- un tetraedro con due dei suoi nodi nel set contribuisce due
    # volte, una per coppia, perche' `in_set[elements[:, :4]]` da' una matrice
    # (n_tet, 4) e non un vettore per tetraedro. Nessun bisogno dei
    # `node_sets`: `nodi_1based` sono gia' esattamente i nodi che `ccx` ha
    # stampato in `leggi_reazioni`.
    vertici = in_set[elements[:, :4]]
    if element_type == "C3D4":
        return float((vertici * (massa / 4.0)[:, None]).sum())
    lati = in_set[elements[:, 4:10]]
    return float(
        (vertici * (-massa / 20.0)[:, None]).sum() + (lati * (massa / 5.0)[:, None]).sum()
    )


# Dove si prende ciascun solutore. Sta nel codice e non in un documento perche'
# lo legge chi ha appena scoperto che gli manca: un messaggio che dice «assente»
# senza dire da dove prenderlo costringe a indovinare (#144).
DOVE_PRENDERLO: dict[str, str] = {
    "calculix": (
        "CalculiX CrunchiX da http://www.dhondt.de/ (sorgenti e binari), "
        "oppure il pacchetto 'calculix-ccx' della propria distribuzione: "
        "l'eseguibile si chiama 'ccx' e va messo nel PATH, o dichiarato in "
        "solutore.percorso"
    ),
    "opensees": (
        "OpenSees da https://opensees.berkeley.edu/ (sezione Download): "
        "l'eseguibile si chiama 'OpenSees' ('OpenSees.exe' su Windows) e va "
        "messo nel PATH, o dichiarato in solutore.percorso. Non è installabile "
        "a sistema da un gestore di pacchetti sulla maggior parte delle "
        "distribuzioni"
    ),
}

# Come si prova che un eseguibile è davvero quel solutore, e non un omonimo.
#
# Due prove diverse perche' i due programmi si presentano in due modi diversi,
# e tutti e due misurati su questa macchina il 30/08/2026:
#
# - `ccx -v` stampa «This is Version 2.21» ed esce con **codice 201**. Il
#   codice d'uscita non e' il segnale, e' gia' costato un difetto (`9d2f751`):
#   la prova guarda l'uscita.
# - OpenSees non ha un flag di versione. Senza argomenti legge lo script da
#   stdin, quindi gli si fa **eseguire una riga** e si guarda che l'abbia
#   eseguita. Non basta il banner: OpenSees 3.8.0 lo stampa e poi esce con
#   **codice 0** anche quando lo script muore su un errore fatale (misurato su
#   `element truss 1 1 99 100.0 1` con nodo e materiale inesistenti), quindi
#   ne' il codice ne' il banner distinguono «c'e'» da «funziona». E non basta
#   l'eco: la sola eco la fa anche un omonimo qualsiasi, e misurato il
#   30/08/2026 `percorso=/bin/cat` passava la prova con
#   `{'funziona': True, 'codice': 0, 'motivo': None}`. I marcatori richiesti
#   sono quindi **due**, e vanno chiesti tutti: il banner chiude l'omonimo,
#   l'eco chiude il «parte e muore subito».
_SOLUTORI: dict[str, dict[str, object]] = {
    "calculix": {
        "eseguibile": "ccx",
        "argomenti": ("-v",),
        "ingresso": "",
        # `ccx -v` stampa la sola riga «This is Version 2.21» (misurato il
        # 30/08/2026): non c'e' un secondo marcatore da chiedere.
        "marcatori": ("Version",),
    },
    "opensees": {
        "eseguibile": "OpenSees",
        "argomenti": (),
        "ingresso": 'puts "MESHREC_VERIFICA"\n',
        "marcatori": ("OpenSees", "MESHREC_VERIFICA"),
    },
}

# Tempo massimo concesso alla prova di un solutore. Non `_TIMEOUT_S`: quello e'
# il tempo di una corsa vera, e una prova che stampa una riga o e' immediata o
# e' rotta.
_TIMEOUT_VERIFICA_S = 30.0


def _nome_noto(nome: str) -> str:
    if nome not in _SOLUTORI:
        raise KeyError(
            f"solutore '{nome}' sconosciuto: i solutori sono {sorted(_SOLUTORI)}"
        )
    return nome


def _trova(nome: str, percorso: Path | None) -> tuple[Path | None, str | None, str | None]:
    """`(percorso, origine, motivo dell'assenza)` per un solutore solo.

    Il punto unico in cui si decide *dove* sta un solutore, cosi' che
    `eseguibile`, `disponibilita` e `verifica` non abbiano tre risposte.

    Un `percorso` dichiarato e inesistente **non ripiega sul PATH**: sarebbe il
    caso peggiore da diagnosticare, perche' l'utente crede di star usando il
    proprio binario e ne sta usando un altro, e nulla glielo dice.
    """
    _nome_noto(nome)
    if percorso is not None:
        dichiarato = Path(percorso)
        if dichiarato.is_file():
            return dichiarato, "dichiarato", None
        return None, None, (
            f"solutore.percorso dichiara «{dichiarato}», che non è un file. Un "
            "percorso dichiarato non ripiega sul PATH: correggilo o toglilo per "
            "far cercare il solutore nel PATH"
        )
    binario = str(_SOLUTORI[nome]["eseguibile"])
    # Anche col suffisso: la distribuzione di OpenSees che gira qui porta
    # `OpenSees.exe` (misurato, con la sua cartella nel PATH
    # `shutil.which("OpenSees")` rende None e `shutil.which("OpenSees.exe")` lo
    # trova), e `DOVE_PRENDERLO` promette che basti metterlo nel PATH.
    nel_path = shutil.which(binario) or shutil.which(binario + ".exe")
    if nel_path is not None:
        return Path(nel_path), "PATH", None
    return None, None, (
        f"«{binario}» non è nel PATH e solutore.percorso non è dichiarato. "
        f"{DOVE_PRENDERLO[nome]}"
    )


def eseguibile(cfg: "SolutoreConfig") -> Path | None:
    """Il percorso dichiarato, altrimenti `shutil.which`. `None` se non c'è.

    Vale per `ccx` e per OpenSees: il percorso dichiarabile mancava a entrambi
    (#139), e `risolvi` cercava `ccx` nel solo PATH. OpenSees in particolare
    non si installa a sistema quasi da nessuna parte, quindi senza percorso
    dichiarabile non sarebbe raggiungibile affatto.
    """
    trovato, _, _ = _trova(cfg.nome, cfg.percorso)
    return trovato


def disponibilita(cfg: "SolutoreConfig | None" = None) -> dict[str, dict[str, object]]:
    """Lo sguardo rapido dell'avvio: c'è / non c'è, e da dove (#144 Q1).

    **Non esegue niente** e non solleva mai per un solutore assente: un
    solutore che non c'è non è un difetto finché nessuno lo sceglie. Chi usa
    solo CalculiX deve vedere OpenSees come «non installato, e va bene», non
    come un errore -- ed è il motivo per cui `scelto` sta accanto a
    `disponibile` invece di essere dedotto da chi legge.

    Il `percorso` dichiarato vale per il solo solutore scelto: è il campo di
    *quella* configurazione, e attribuirlo anche all'altro direbbe che
    l'utente ha dichiarato una cosa che non ha dichiarato.

    `cfg` a `None` significa «nessuna configurazione»: si guarda il PATH e
    nessuno dei due è scelto.
    """
    scelto = _nome_noto(cfg.nome) if cfg is not None else None
    stato: dict[str, dict[str, object]] = {}
    for nome in _SOLUTORI:
        percorso, origine, motivo = _trova(
            nome, cfg.percorso if cfg is not None and nome == scelto else None
        )
        stato[nome] = {
            "disponibile": percorso is not None,
            "percorso": None if percorso is None else str(percorso),
            "origine": origine,
            "scelto": nome == scelto,
            "motivo": motivo,
            "dove_prenderlo": DOVE_PRENDERLO[nome],
        }
    return stato


def verifica(cfg: "SolutoreConfig") -> dict[str, object]:
    """La prova vera, al momento di scegliere: esegue il binario e guarda che risponda.

    «C'è» non è «funziona» (#144 Q1). Un file col nome giusto e i permessi
    giusti può essere un omonimo, un collegamento rotto, un binario per
    un'altra architettura, o il solutore vero che non trova le proprie
    librerie: nessuna di queste si vede da `shutil.which`.

    **Il codice d'uscita non è il verdetto**, per tutti e due i solutori e per
    due ragioni diverse, misurate e non lette: `ccx -v` funziona ed esce 201
    (`9d2f751`); OpenSees 3.8.0 esce 0 anche quando lo script muore su un
    errore fatale. Il verdetto è il marcatore che `_SOLUTORI` dichiara. Il
    codice resta comunque riportato, e finisce nel messaggio quando la prova
    fallisce: è l'indizio che dice se il binario è nemmeno partito.

    L'uscita si decodifica con `errors="replace"`, e non con l'`ignore` di
    `_righe_dat`: quell'argomento qui non arriva. Là i parser contano i campi
    di una riga e `U+FFFD` ne aggiungerebbe uno; qui non si conta nulla, si
    cerca una sottostringa e si mostra il resto a una persona. Con `ignore` un
    byte illeggibile *dentro* «Version» sparirebbe e la parola si
    ricomporrebbe: la cancellazione fabbricherebbe il marcatore che non c'era,
    cioè un verdetto di «funziona» su un binario che non è un solutore. Resta
    la ragione originale, che vale per tutte e due le politiche: un byte fuori
    tabella non deve trasformare una diagnosi in un `UnicodeDecodeError`.
    """
    nome = _nome_noto(cfg.nome)
    percorso, _, assente = _trova(nome, cfg.percorso)
    if percorso is None:
        return {
            "solutore": nome, "percorso": None, "disponibile": False,
            "funziona": False, "codice": None, "uscita": "",
            # `assente` porta gia' `DOVE_PRENDERLO` quando il binario non e'
            # nel PATH; concatenarcelo di nuovo stampava la frase due volte.
            "motivo": assente,
        }

    scheda = _SOLUTORI[nome]
    try:
        processo = subprocess.run(
            [str(percorso), *scheda["argomenti"]],
            input=str(scheda["ingresso"]).encode(),
            capture_output=True,
            timeout=_TIMEOUT_VERIFICA_S,
        )
    except (OSError, subprocess.SubprocessError) as errore:
        return {
            "solutore": nome, "percorso": str(percorso), "disponibile": True,
            "funziona": False, "codice": None, "uscita": "",
            "motivo": f"«{percorso}» non è eseguibile: {type(errore).__name__}: {errore}",
        }

    uscita = (processo.stdout + processo.stderr).decode("utf-8", errors="replace")
    mancanti = [marca for marca in scheda["marcatori"] if marca not in uscita]
    funziona = not mancanti
    motivo = None
    if not funziona:
        motivo = (
            f"«{percorso}» è partito (codice {processo.returncode}) ma la sua "
            f"uscita non è riconosciuta come {nome}: mancano i marcatori "
            f"{mancanti}. Coda dell'uscita:\n{uscita[-2000:]}"
        )
    return {
        "solutore": nome, "percorso": str(percorso), "disponibile": True,
        "funziona": funziona, "codice": processo.returncode,
        "uscita": uscita[-2000:], "motivo": motivo,
    }


def valida_casi_di_carico(casi_di_carico: list[str]) -> list[str]:
    """I nomi dei casi, o il motivo per cui non sono nomi.

    Due guardie, e nessuna delle due è teorica in questo repo.

    **Vuoto**: un deck senza casi non è uno stato da eseguire a vuoto. Era già
    la guardia di `risolvi`, spostata qui perché ora ha un secondo chiamante --
    `opensees.scrivi_tcl`, che senza di essa scriverebbe un file muto che
    OpenSees esegue senza calcolare nulla.

    **Due nomi che differiscono solo per le maiuscole**: `ccx` risolve i nomi
    senza distinguere il caso (misurato in
    `docs/fase-6-cantiere/sonda-caso-nomi/`), quindi nel deck sono lo stesso
    nome e i risultati del secondo sovrascrivono quelli del primo. `config.
    PipelineConfig` lo verifica già sui nomi che l'operatore dichiara; questa
    è la stessa regola al confine di chi riceve la lista già costruita, dove
    arriva anche per chiamata diretta.

    L'ordine si conserva: è un contratto col lettore del `.frd`, dove il
    numero di passo è l'unico legame fra un blocco e il suo caso, e un ordine
    diverso da quello del deck scambierebbe i risultati.
    """
    if not casi_di_carico:
        raise ValueError(
            "casi_di_carico è vuoto: nessun caso da risolvere. Un deck senza "
            "casi è un errore del chiamante, non uno stato da eseguire a vuoto"
        )
    per_caso = _mappa_casefold(casi_di_carico)
    if len(per_caso) != len(casi_di_carico):
        visti: dict[str, str] = {}
        for nome in casi_di_carico:
            gemello = visti.get(nome.casefold())
            if gemello is not None:
                raise ValueError(
                    f"i casi di carico '{gemello}' e '{nome}' differiscono solo "
                    "per le maiuscole: per il solutore sono lo stesso nome (ccx "
                    "risolve i nomi senza distinguere il caso), e il secondo "
                    "sovrascriverebbe i risultati del primo"
                )
            visti[nome.casefold()] = nome
    return list(casi_di_carico)


def _rotazione_ai_punti(trasformata: np.ndarray | list[list[float]]) -> np.ndarray:
    """La parte rotatoria di `metrics["11_export"]["transform"]`, verificata.

    `abaqus.align_to_axes` scrive `aligned = (punti - centro) @ R.T - shift`:
    la stessa `R` porta un vettore dal telaio dei punti a quello del modello
    (`v_modello = R @ v_punti`), e la sua inversa -- che per una rotazione e'
    la trasposta -- lo riporta indietro (`v_punti = v_modello @ R`).

    Verifica il determinante e non solo la forma: se quello che arriva qui non
    e' una rotazione (una riflessione, una scala, una matrice corrotta),
    applicarlo specchierebbe o allungherebbe il campo senza dirlo, che e' la
    stessa classe di difetto silenzioso del C1. `align_to_axes` costruisce la
    terna col prodotto vettoriale, quindi +1 e' garantito alla sorgente: qui
    si controlla che sia ancora quella la sorgente.
    """
    matrice = np.asarray(trasformata, dtype=np.float64)
    if matrice.shape != (4, 4):
        raise ValueError(
            "trasformata deve essere la matrice 4x4 di "
            "metrics['11_export']['transform'], che riporta i vettori del "
            f"modello nel telaio dei punti del .vtu: arrivata {matrice.shape}"
        )
    rotazione = matrice[:3, :3]
    determinante = float(np.linalg.det(rotazione))
    if not np.isclose(determinante, 1.0, atol=1e-6):
        raise ValueError(
            f"la parte rotatoria della trasformata ha determinante {determinante}, "
            "non +1: non è una rotazione, e applicarla al campo lo specchierebbe "
            "o lo scalerebbe in silenzio"
        )
    return rotazione


def risolvi(
    out_dir: Path,
    deck: Path,
    cfg: AnalysisConfig,
    nodes: np.ndarray,
    elements: np.ndarray,
    element_type: str,
    *,
    casi_di_carico: list[str],
    vincolo_in_pianta: dict[str, float],
    trasformata: np.ndarray | list[list[float]],
    solutore: "SolutoreConfig | None" = None,
) -> dict[str, object]:
    """Step 13: esegue `ccx` sul deck e scrive i campi in `13_solution.vtu`.

    Un solutore assente non e' un fallimento (PRODUCT.md dichiara utenti
    successivi confermati senza CalculiX): la funzione lo dice e esce, senza
    scrivere alcun artefatto numerato.

    Contratto delle chiavi di `point_data`, letto da `pipeline.run` per
    decidere se registrare l'artefatto e dai Task 8/9 per portare il campo al
    viewport: `U_<CASO>` (vettore, spostamento nodale) e `VM_<CASO>` (scalare,
    tensione equivalente) per ciascun passo statico -- `<CASO>` e' il nome che
    `abaqus.write_inp` da' al passo ("GRAVITA" di norma, "SPINTA_ORIZZONTALE",
    "CARICO_TOP", il nome di ogni carico posizionato o distribuito e -- dalla
    Fase 8 -- il nome di ogni **combinazione** dichiarata, che e' un passo
    statico come gli altri e produce un campo come gli altri, in coda ai casi
    singoli e prima del modale);
    `MODO_<n>` (vettore, forma non dimensionale) per l'n-esimo
    modo. Un blocco modale non produce mai `U_`/`VM_`: la forma e' normalizzata
    sulla massa, non uno spostamento fisico (vedi il docstring del modulo).

    `casi_di_carico` traduce il numero di passo del `.frd` (che non porta un
    nome, solo un numero) nell'etichetta del caso: e' `metrics["11_export"]
    ["casi_di_carico"]`, cioe' l'ordine che `abaqus.export_model` ha scritto
    *davvero* nel deck, letto qui e non ri-derivato. Prima di questo modulo
    aveva una propria `_casi_statici` che rifaceva lo stesso calcolo in
    proprio, accoppiata a `export_model` solo da un commento («deve restare
    la stessa derivazione»): un riordino dei passi in `write_inp` senza
    toccare questo file avrebbe etichettato un caso col nome sbagliato in
    silenzio. Una sola origine chiude l'esposizione per costruzione, non per
    promessa. Il modale, se presente, e' l'ultima voce della lista e viene
    scartato qui: i suoi blocchi si riconoscono da `Blocco.modale`, non da
    un'etichetta di passo. Nessun predefinito (giro di correzione del Task 7):
    un deck senza casi non e' uno stato rappresentabile con `None` -- con
    quel predefinito, `ccx` presente eseguiva davvero e scartava in silenzio
    ogni blocco statico letto (`[nome for nome in (None or ()) if nome !=
    "MODALE"]` da' `[]`). E' un errore del chiamante, e si dichiara come tale.

    `trasformata` e' `metrics["11_export"]["transform"]`, la 4x4 con cui
    `abaqus.align_to_axes` ha portato i nodi nel telaio del deck. Serve perche'
    i due ingressi di `write_vtu` arrivano da telai diversi: `nodes` non e'
    allineato (`export_model` allinea internamente e non restituisce i nodi
    allineati), mentre il `point_data` viene dal `.frd`, cioe' dal deck
    allineato. I vettori (`U_*`, `MODO_*`) si riportano quindi nel telaio dei
    punti prima della scrittura -- stessa strada che `constraint_plan_extent`
    percorre gia'. La von Mises e' scalare e non si tocca.

    `vincolo_in_pianta` e' `metrics["11_export"]["constraint_plan_extent"]`,
    gia' calcolato allo step 11 su `abaqus.constraint_plan_extent`: non si
    ricalcola qui, dove non arrivano i `node_sets` per farlo.

    Aggiunge `metrics["13_solve"]["controlli"]` (Task 7): sette verdetti
    che dicono quando i numeri qui sopra non sono citabili -- `reazioni`
    (equilibrio del solo peso proprio, passo 1, sempre isolabile per
    costruzione di `abaqus.write_inp`), `vincolo_in_pianta` (soglia
    `_SOGLIA_VINCOLO_IN_PIANTA`, costante di modulo -- vedi il commento sopra la
    sua definizione), `autovalori`, `avvisi` (zero per essere
    citabili), `picco` (per caso di carico, dove vive il picco di tensione,
    non se e' alto), `spostamenti` (#12: l'ampiezza contro la dimensione del
    modello, il solo verdetto che guarda quanto grande e' il risultato invece
    che se il deck e la configurazione concordano) e `massa_modale` (#75: la
    frazione di massa partecipante che i modi estratti catturano, cioe' se il
    numero di modi chiesto bastava). Sotto soglia i risultati restano scritti:
    si marcano, non si nascondono.
    """
    valida_casi_di_carico(casi_di_carico)
    rotazione = _rotazione_ai_punti(trasformata)
    out_dir = Path(out_dir)
    nome_solutore = "calculix" if solutore is None else _nome_noto(solutore.nome)
    if nome_solutore != "calculix":
        # Misurato il 30/08/2026 su questa macchina: «OpenSees.exe -i m» stampa
        # il banner ed esce con codice 0. La guardia sul codice d'uscita qui
        # sotto passerebbe, e il fallimento arriverebbe piu' avanti come un
        # `FileNotFoundError` nudo sul `.frd` mai scritto, con un messaggio che
        # nomina «ccx».
        raise ValueError(
            f"solutore.nome = '{nome_solutore}': questo passo monta la riga di "
            "comando di CalculiX («-i <deck>») e legge il .frd e il .dat che "
            "solo lui scrive. Il telaio su OpenSees lo porta il ramo del "
            "telaio, con core/opensees.py (scrivi_tcl e leggi_uscite), non "
            "risolvi"
        )
    percorso_dichiarato = None if solutore is None else solutore.percorso
    binario, _, assente = _trova(nome_solutore, percorso_dichiarato)
    if binario is None:
        # `{"eseguito": False, "solutore": "assente"}` senza altro e' lo stato
        # che questo passo dichiara da sempre, ed e' quello giusto per un
        # solutore semplicemente non installato: PRODUCT.md dichiara utenti
        # confermati senza CalculiX, e non e' un difetto. Ma un `percorso`
        # **dichiarato** e sbagliato e' un'altra cosa -- l'utente crede di aver
        # detto dove sta il binario -- e uscire di qui con la stessa parola
        # muta lo lascerebbe a indovinare quale delle due sia. Il motivo
        # compare quindi solo quando c'e' qualcosa di dichiarato da correggere;
        # per tutto il resto `meshrec dottore` dice da dove prendere il
        # solutore. La chiave in piu' e' additiva: nessun consumatore di
        # `metrics["13_solve"]` legge questo dizionario per intero.
        esito: dict[str, object] = {"eseguito": False, "solutore": "assente"}
        if percorso_dichiarato is not None:
            esito["motivo"] = assente
        return esito

    deck = Path(deck)
    processo = subprocess.run(
        [str(binario), "-i", deck.stem],
        cwd=deck.parent,
        capture_output=True,
        text=True,
        # `ccx` e' di terze parti e su Windows scrive nella codepage locale.
        # Senza `encoding` la lettura userebbe quella preferita dalla macchina
        # -- utf-8 dentro il sottoprocesso del server -- e un byte accentato
        # farebbe morire lo step 13 prima di scrivere `13_solver.log`, cioe'
        # prima di lasciare la sola cosa che spiega perche' si e' fermato.
        # `replace` e non `ignore`: in un registro che si apre per capire un
        # guasto un carattere cancellato e' una bugia silenziosa.
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT_S,
    )
    uscita = processo.stdout + processo.stderr
    percorso_log = out_dir / "13_solver.log"
    percorso_log.write_text(uscita, encoding="utf-8")
    if processo.returncode != 0:
        raise RuntimeError(
            f"ccx è terminato con codice {processo.returncode} su {deck.name}:\n{uscita[-2000:]}"
        )

    percorso_frd = out_dir / "13_solution.frd"
    percorso_dat = out_dir / "13_solution.dat"
    # Rinomina e non copia: `deck.parent` **e'** `out_dir`, quindi copiare
    # significava materializzare l'intero `.frd` in un `bytes` Python (81 MiB
    # sulla corsa dell'as-built) e lasciarne due esemplari identici nella
    # stessa cartella. `ccx` riscrive `wall_model.frd` a ogni corsa, quindi
    # l'originale non serve a nessuno: nessun altro punto del progetto lo
    # nomina.
    deck.with_suffix(".frd").replace(percorso_frd)
    deck.with_suffix(".dat").replace(percorso_dat)

    casi_statici = [nome for nome in casi_di_carico if nome != "MODALE"]
    etichetta_passo = dict(enumerate(casi_statici, start=1))
    blocchi = leggi_frd(percorso_frd)

    n_nodi = len(nodes)
    point_data: dict[str, np.ndarray] = {}
    casi: dict[str, dict[str, float]] = {}
    picco_per_caso: dict[str, dict[str, object]] = {}
    altezza = float(np.ptp(nodes[:, 2])) if n_nodi else 0.0
    banda_vincolo = _FRAZIONE_BANDA_VINCOLO * altezza
    n_modi = 0
    for blocco in blocchi:
        if blocco.modale:
            if blocco.grandezza != "DISP":
                continue
            n_modi += 1
            campo = np.zeros((n_nodi, 3))
            campo[blocco.nodi - 1] = blocco.dati
            point_data[f"MODO_{n_modi}"] = campo
            continue
        caso = etichetta_passo.get(blocco.passo)
        if caso is None:
            continue
        if blocco.grandezza == "DISP":
            campo = np.zeros((n_nodi, 3))
            campo[blocco.nodi - 1] = blocco.dati
            point_data[f"U_{caso}"] = campo
            casi.setdefault(caso, {})["u_max"] = float(np.linalg.norm(blocco.dati, axis=1).max())
        elif blocco.grandezza == "STRESS":
            equivalente = von_mises(blocco.dati)
            campo = np.zeros(n_nodi)
            campo[blocco.nodi - 1] = equivalente
            point_data[f"VM_{caso}"] = campo
            casi.setdefault(caso, {})["vm_max"] = float(equivalente.max())
            picco_per_caso[caso] = controlla_picco(
                equivalente, nodes[blocco.nodi - 1, 2], banda=banda_vincolo
            )

    # I campi vengono dal `.frd`, cioe' dal deck allineato agli assi; i nodi
    # scritti nel `.vtu` sono quelli non allineati che il chiamante passa.
    # Senza questa riga il file mescolerebbe due telai: un *Warp By Vector*
    # deformerebbe il pezzo a 90 gradi dalla direzione vera, senza errore e
    # senza avviso, perche' ogni consumatore odierno e' invariante per
    # rotazione (il viewport prende la norma, i controlli usano scalari o la
    # sola z). Si riporta il campo nel telaio dei punti e non viceversa,
    # cosi' il `.vtu` dello step 13 resta nello stesso telaio di quello dello
    # step 9. Gli scalari (`VM_*`) non si toccano.
    for nome, campo in point_data.items():
        if campo.ndim == 2:
            point_data[nome] = campo @ rotazione

    percorso_vtu = out_dir / "13_solution.vtu"
    abaqus.write_vtu(percorso_vtu, nodes, elements, element_type=element_type, point_data=point_data)

    avvisi = uscita.upper().count(_MARCA_AVVISO_CCX)
    # Una lettura sola per i tre parser: il `.dat` e' lo stesso file.
    righe_dat = _righe_dat(percorso_dat, None)
    frequenze_hz = leggi_frequenze(percorso_dat, righe=righe_dat)
    masse_modali = leggi_massa_modale(percorso_dat, righe=righe_dat)
    reazioni_peso_proprio = leggi_reazioni(percorso_dat, passo=1, righe=righe_dat)
    massa = float(cfg.material.density) * _volume_totale(nodes, elements)
    quota_tributaria = _quota_tributaria_gravita(
        # `.keys()` esplicito: la funzione vuole i numeri di nodo a base uno,
        # e `list(dict)` darebbe le chiavi comunque -- ma dalla firma non si
        # vede, e chi legge passa indici a base zero e prende un off-by-one
        # silenzioso che boccia una corsa buona.
        # `element_type` non e' decorativo: la ripartizione della gravita' fra
        # i nodi e' diversa fra C3D4 e C3D10, e passare il predefinito su un
        # maglio quadratico dava un verdetto `reazioni` falso su ogni corsa
        # (#40). E' lo stesso `element_type` che ha scritto il deck.
        nodes, elements, reazioni_peso_proprio.keys(), cfg.material.density,
        element_type,
    )
    peso_atteso = (0.0, 0.0, (massa - quota_tributaria) * cfg.gravity)
    # Sette verdetti, sette funzioni: `vincolo_in_pianta` e `avvisi` erano
    # scritti inline qui, e per questo restavano fuori dalla tabella
    # `_INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO` di tests/test_solve.py, che il
    # commento sopra `controlla_reazioni` dichiara completa (M11 della
    # revisione finale: copriva tre verdetti su cinque). Non c'e' altro da
    # sapere qui sotto: il perche' di ciascuna guardia sta nel docstring della
    # funzione che la porta.
    casi_mancanti = [nome for nome in casi_statici if nome not in picco_per_caso]
    # Il deck di questo passo e' un solido, e i sette verdetti passano da
    # `verdetti_per_modello`: senza, la tabella `CONTROLLI_PER_MODELLO`
    # resterebbe un commento lungo che nessun chiamante di produzione
    # attraversa, e un controllo dichiarato non applicabile continuerebbe a
    # girare e a uscire verde.
    controlli = verdetti_per_modello("solido", {
        "reazioni": lambda: controlla_reazioni(
            reazioni_peso_proprio, peso_atteso, tolleranza=_TOLLERANZA_REAZIONI
        ),
        "vincolo_in_pianta": lambda: controlla_vincolo_in_pianta(vincolo_in_pianta["minimo"]),
        "autovalori": lambda: controlla_autovalori(frequenze_hz),
        "avvisi": lambda: controlla_avvisi(avvisi),
        "spostamenti": lambda: controlla_spostamenti(
            _spostamento_massimo(point_data), _dimensione(nodes)
        ),
        "massa_modale": lambda: controlla_massa_modale(masse_modali),
        # #92: il verdetto si aggrega sui casi che il **deck dichiara**, non
        # su quelli che il `.frd` ha portato. `picco_per_caso` si riempie dai
        # blocchi letti, e `all()` su un insieme parziale e' `True`: un `.frd`
        # con un caso su tre dava tre verdetti verdi su dati incompleti. Ogni
        # passo statico chiede `*EL FILE S` (`abaqus._passo_statico`), quindi
        # un caso senza blocco STRESS e' un risultato mancante, non un caso
        # che non ne produce.
        "picco": lambda: {
            "passato": bool(picco_per_caso) and not casi_mancanti
            and all(v["passato"] for v in picco_per_caso.values()),
            "per_caso": picco_per_caso,
            "casi_mancanti": casi_mancanti,
        },
    })

    return {
        "eseguito": True,
        "returncode": processo.returncode,
        "avvisi": avvisi,
        "errori": uscita.upper().count("*ERROR"),
        "casi": casi,
        "controlli": controlli,
        "modi": n_modi,
        "frequenze_hz": frequenze_hz,
        "vtu": str(percorso_vtu),
        "frd": str(percorso_frd),
        "dat": str(percorso_dat),
        "log": str(percorso_log),
    }
