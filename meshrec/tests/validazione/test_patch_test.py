"""Il patch test: il gradino piu' basso e piu' solido della verifica del codice.

Ticket https://github.com/maeurong/Tesi/issues/46. Riferimento:
Taylor, Simo, Zienkiewicz & Chan (1986), «The patch test -- a condition for
assessing FEM convergence», IJNME 22:39-62, DOI 10.1002/nme.1620220105, che
formalizza il test di Irons come condizione **necessaria** di consistenza e,
insieme al test di stabilita', **sufficiente** per la convergenza.

Se un maglio non riproduce esattamente uno stato di deformazione costante,
nessun risultato piu' complesso e' credibile. E' anche il controllo che coglie
una permutazione sbagliata dei nodi di lato di un C3D10, che e' il motivo per
cui il ripristino del quadratico (#45) dipende da questo file.

**Due varianti, decise il 26/08/2026.**

- **A** -- si impone il campo lineare su **tutti** i nodi di bordo e si risolve
  l'interno. Condizione necessaria canonica, nessuna ginnastica sui vincoli.
- **B** -- si vincolano pochi nodi e si applicano le **forze nodali
  consistenti** con lo stato tensionale costante. Prova in piu' l'equilibrio,
  cioe' che il deck non perda o inventi carico.

**Perche' basta guardare gli spostamenti.** Se il campo lineare e' imposto su
tutto il bordo e i nodi interni escono esattamente su quel campo, l'intero
campo e' lineare, quindi la deformazione e' costante **per costruzione** e la
tensione con lei. Leggere anche le tensioni chiederebbe di fidarsi
dell'ordine delle colonne del `.frd`, che e' proprio il difetto non ancora
verificato di #39: il test poggerebbe su cio' che non e' stato verificato.

**Il maglio viene da TetGen come lo usiamo noi**, non da una suddivisione
scritta a mano: il test deve poter cadere se la nostra tetraedrizzazione o la
nostra esportazione hanno un difetto. E deve avere **nodi interni**: un maglio
i cui nodi stanno tutti sul bordo non proverebbe nulla, perche' non resterebbe
nulla da risolvere.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from ccx_utils import read_dat_displacements
from meshrec.core import abaqus, synth, volume
from meshrec.core.config import Material

pytestmark = pytest.mark.validazione

LATO = (100.0, 100.0, 100.0)  # mm
MATERIALE = Material(name="PROVA", young=30000.0, poisson=0.2, density=2.4e-9)

# Gradiente costante del campo di spostamento, u = A x. Nullo nell'origine, che
# e' l'unico modo per far convivere il campo imposto con il nodo vincolato a
# zero senza che le due condizioni si contraddicano.
#
# Non e' diagonale apposta: i termini fuori diagonale mettono in gioco anche il
# taglio, e un elemento che riproduce l'estensione ma non lo scorrimento
# passerebbe un test costruito sulla sola diagonale.
A = np.array(
    [
        [1.0e-4, 2.0e-5, 3.0e-5],
        [-1.0e-5, -3.0e-5, 1.0e-5],
        [2.0e-5, -1.0e-5, -3.0e-5],
    ]
)

# Il `.dat` di CalculiX stampa in `0.000000E+00`: **sette cifre significative**.
# Su un campo di ampiezza 1,5e-2 mm l'ultima cifra vale circa 1e-9 in assoluto,
# cioe' 1,345e-7 rapportata all'ampiezza. Una soglia piu' stretta di cosi' non
# misura l'elemento: misura il formato di stampa, e sarebbe precisione
# fabbricata (principio 3 di PRODUCT.md).
#
# La prima stesura della soglia valeva 1e-8, scelta in #35 **prima** di sapere
# quanto il canale sapesse esprimere, e il patch test falliva mostrando
# esattamente il pavimento, cifra per cifra: l'elemento era a posto, era la
# soglia a pretendere una precisione che il `.dat` non ha.
#
# La correzione, decisa il 26/08/2026: non un numero assoluto ma un **multiplo
# della risoluzione del canale**. Cosi' la soglia resta dichiarata prima -- cio'
# che varia e' la risoluzione della misura, non il risultato -- e segue da se'
# se un domani il formato di stampa cambia.
try:  # il registro arriva con la PR #49
    from meshrec.core.soglie import trova

    FATTORE = float(trova("patch_test_fattore_sul_pavimento").massimo)
except (ImportError, KeyError):  # pragma: no cover - sparisce quando #49 e' fuso
    FATTORE = 2.0


def _pavimento_del_formato(atteso: np.ndarray) -> float:
    """Lo scarto relativo che il solo formato del `.dat` introduce.

    Si fa passare il campo **esatto** attraverso la stessa formattazione che
    `ccx` usa per stamparlo, e si misura di quanto cambia. E' il rumore di
    fondo del canale: nessun test che legga il `.dat` puo' distinguere sotto
    questa soglia, quale che sia la qualita' dell'elemento.
    """
    rientrato = np.array([[float("%.6E" % c) for c in riga] for riga in atteso])
    scala = float(np.abs(atteso).max())
    return float(np.linalg.norm(rientrato - atteso, axis=1).max() / scala)


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


# I due elementi che il deck sa scrivere per un maglio tetraedrico, con
# l'ordine di TetGen che li produce. Il patch test vale per entrambi, e sul
# quadratico e' il secondo dei due oracoli sulla permutazione dei nodi di lato
# (#45): un nodo di lato al posto sbagliato **sposta un punto nello spazio**,
# l'elemento cambia forma e non riproduce piu' un campo lineare.
ELEMENTI = [pytest.param(1, "C3D4", id="C3D4"), pytest.param(2, "C3D10", id="C3D10")]


def _provino(order: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Un blocchetto di tetraedri dalla nostra pipeline, con nodi interni.

    `max_volume` e' scelto perche' TetGen debba aggiungere punti dentro il
    solido: senza nodi interni il sistema non ha incognite e il test passerebbe
    a vuoto. Che ce ne siano lo verifica il chiamante, non un commento.
    """
    vertici, facce = synth.box_mesh(LATO)
    return volume.tetrahedralize(
        vertici, facce,
        max_volume=8000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=order,
    )


def _campo(punti: np.ndarray) -> np.ndarray:
    return punti @ A.T


def _indici_di_bordo(nodi: np.ndarray) -> np.ndarray:
    """I nodi sulla superficie del provino, riconosciuti per **geometria**.

    Non per topologia: `abaqus.boundary_faces` rende terne di **vertici**,
    quindi su un maglio quadratico i nodi di lato che stanno sul bordo non ne
    farebbero parte. Lasciarli liberi rompe il patch test nella variante A, e
    non per colpa dell'elemento: un nodo libero e **scarico** non puo' stare
    sul campo lineare, perche' su quel bordo la trazione non e' nulla. Misurato
    prima di questa correzione: 22% di scarto sul C3D10, contro il pavimento
    del formato sul C3D4.

    Il criterio geometrico e' esatto su questo provino perche' e' una scatola
    a facce piane e assi allineati. Non e' un criterio generale, e non pretende
    di esserlo: qui il provino lo scegliamo noi.
    """
    tolleranza = 1e-9
    fuori = np.zeros(len(nodi), dtype=bool)
    for asse, lunghezza in enumerate(LATO):
        fuori |= np.abs(nodi[:, asse]) < tolleranza
        fuori |= np.abs(nodi[:, asse] - lunghezza) < tolleranza
    return np.flatnonzero(fuori)


def _nodo_piu_vicino(nodi: np.ndarray, punto) -> int:
    return int(np.argmin(np.linalg.norm(nodi - np.asarray(punto, dtype=float), axis=1)))


def _risolvi(tmp_path, nodi, tets, **kwargs) -> dict[int, tuple[float, float, float]]:
    """Scrive il deck con `write_inp`, lancia `ccx`, rende gli spostamenti.

    Passa per l'esportatore vero e non per un deck scritto qui: un secondo
    scrittore dentro i test potrebbe divergere da quello di produzione senza
    che nulla lo dica, ed e' proprio l'esportatore che questo test deve
    sorvegliare.
    """
    eseguibile = _ccx_o_salta()
    abaqus.write_inp(
        tmp_path / "patch.inp", nodi, tets,
        material=MATERIALE,
        gravity=0.0,  # nessuna forza di volume: la tensione dev'essere costante
        print_nsets=("TUTTI",),
        **kwargs,
    )
    esito = subprocess.run(
        [eseguibile, "-i", "patch"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]
    avvisi = [r for r in esito.stdout.splitlines() if "*WARNING" in r]
    assert not avvisi, "\n".join(avvisi)
    spostamenti = read_dat_displacements(tmp_path / "patch.dat")
    assert spostamenti, "nessuno spostamento letto dal .dat"
    return spostamenti


def _scarto_relativo(spostamenti, nodi, indici) -> float:
    """Massimo scarto fra calcolato e campo lineare, normalizzato sull'ampiezza.

    Relativo e non assoluto: un patch piu' grande produce spostamenti piu'
    grandi, e una soglia assoluta diventerebbe piu' o meno severa al variare
    della geometria senza che nessuno lo abbia deciso.
    """
    atteso = _campo(nodi)
    scala = float(np.abs(atteso).max())
    assert scala > 0.0, "campo identicamente nullo: il test non proverebbe nulla"
    scarti = [
        np.linalg.norm(np.asarray(spostamenti[int(i) + 1]) - atteso[int(i)])
        for i in indici
    ]
    return float(max(scarti) / scala)


def test_il_provino_ha_nodi_interni_altrimenti_non_prova_nulla():
    """Senza incognite da risolvere il patch test passa a vuoto.

    Sta separato e gira sempre: se un domani `max_volume` cambia e il maglio
    perde i nodi interni, il patch test resterebbe verde senza risolvere
    niente, ed e' esattamente la guardia che non guarda.
    """
    nodi, tets = _provino()
    bordo = set(_indici_di_bordo(nodi).tolist())
    interni = [i for i in range(len(nodi)) if i not in bordo]
    assert len(interni) >= 10, f"solo {len(interni)} nodi interni: provino inadeguato"


def test_il_pavimento_del_canale_e_misurabile_e_non_nullo():
    """La grandezza su cui la soglia poggia dev'essere misurata, non supposta.

    Se il pavimento uscisse zero, il fattore moltiplicherebbe nulla e la
    soglia diventerebbe «errore esattamente zero», che nessuna aritmetica
    finita puo' soddisfare: il test non fallirebbe per un difetto ma per il
    proprio metro. Misurato il 26/08/2026: 1,345e-07 su questo provino.

    Il fattore dev'essere maggiore di uno: a uno la soglia coinciderebbe col
    pavimento, e il confronto diventerebbe un testa o croce sull'ultima cifra.

    Mutazione che lo uccide: portare `FATTORE` a 1,0.
    """
    nodi, _ = _provino()
    pavimento = _pavimento_del_formato(_campo(nodi))
    assert pavimento > 0.0, "pavimento nullo: la soglia non avrebbe nulla da moltiplicare"
    assert pavimento < 1e-5, (
        f"pavimento {pavimento:.3e} inatteso: il formato del .dat non e' piu' quello misurato"
    )
    assert FATTORE > 1.0, "un fattore a uno rende il confronto un testa o croce"


@pytest.mark.parametrize(("order", "tipo"), ELEMENTI)
def test_patch_test_a_il_campo_lineare_e_riprodotto_esattamente(tmp_path, order, tipo):
    """Variante A: campo imposto su tutto il bordo, interno risolto.

    **Cosa questo test coglie davvero su un C3D4**, misurato permutando le
    colonne di `tets` prima della scrittura:

    | permutazione | esito |
    |---|---|
    | intatta | scarto al pavimento del formato: passa |
    | scambio di due colonne (dispari) | `ccx` **rifiuta il deck** |
    | rotazione di tre colonne (pari) | scarto al pavimento: **non colta** |

    Le permutazioni **pari** non vengono colte, e non e' un limite: su un
    tetraedro lineare sono lo **stesso elemento**, solo rietichettato. Le
    dispari rovesciano l'orientamento e le respinge il solutore, prima ancora
    di questo confronto.

    Su un **C3D10** la faccenda cambia, ed e' il motivo per cui #45 dipende da
    qui: scambiare due nodi di lato sposta punti nello spazio invece di
    rinominarli, quindi l'elemento **cambia forma** e non riproduce piu' un
    campo lineare. Che questo test lo colga va misurato quando il quadratico
    esiste, non dato per scontato adesso.
    """
    nodi, tets = _provino(order)
    bordo = _indici_di_bordo(nodi)
    atteso = _campo(nodi)

    # Il nodo all'origine porta gia' spostamento nullo nel campo, quindi puo'
    # restare il set vincolato senza contraddirlo: e' il motivo per cui A e'
    # scelto nullo nell'origine.
    origine = _nodo_piu_vicino(nodi, (0.0, 0.0, 0.0))
    assert np.allclose(nodi[origine], 0.0), "il provino non ha un nodo nell'origine"

    imposti = {
        int(i): {g + 1: float(atteso[int(i), g]) for g in range(3)}
        for i in bordo
        if int(i) != origine
    }
    insiemi = {
        "ANCORA": np.array([origine]),
        "TUTTI": np.arange(len(nodi)),
    }

    spostamenti = _risolvi(
        tmp_path, nodi, tets,
        node_sets=insiemi, fixed_nset="ANCORA", element_type=tipo,
        spostamenti_imposti=imposti,
    )

    # Tutto cio' che non e' stato imposto: i nodi interni, e sul quadratico
    # anche i **nodi di lato che stanno sul bordo** -- `boundary_faces` rende
    # terne di vertici, quindi quelli restano incogniti. Meglio cosi': piu'
    # gradi di liberta' risolti, test piu' discriminante.
    interni = [i for i in range(len(nodi)) if i not in set(bordo.tolist())]
    scarto = _scarto_relativo(spostamenti, nodi, interni)
    limite = FATTORE * _pavimento_del_formato(atteso)
    assert scarto <= limite, (
        f"i nodi interni non riproducono il campo lineare: scarto relativo {scarto:.3e} "
        f"contro un limite di {limite:.3e}, cioe' {FATTORE:g} volte la risoluzione del .dat"
    )


def test_patch_test_b_con_forze_consistenti(tmp_path):
    """Variante B: pochi vincoli, e le forze nodali che equilibrano lo stato costante.

    Prova qualcosa che A non prova: che il deck non perda ne' inventi carico.
    In A le reazioni possono assorbire qualunque errore di carico, perche' il
    bordo e' tutto vincolato.

    Le forze vengono dalla trazione `t = sigma n` integrata su ogni faccia di
    bordo. Su un triangolo a **3 nodi** la ripartizione a un terzo per nodo
    **e' gia'** la formula consistente -- il caso a 6 nodi del C3D10, dove i
    vertici prendono zero, e' un'altra cosa e arriva con #45.
    """
    nodi, tets = _provino()
    atteso = _campo(nodi)

    # Tensione costante dal campo: sigma = lambda tr(eps) I + 2 mu eps.
    eps = 0.5 * (A + A.T)
    lam = (
        MATERIALE.young * MATERIALE.poisson
        / ((1.0 + MATERIALE.poisson) * (1.0 - 2.0 * MATERIALE.poisson))
    )
    mu = MATERIALE.young / (2.0 * (1.0 + MATERIALE.poisson))
    sigma = lam * np.trace(eps) * np.eye(3) + 2.0 * mu * eps

    facce = abaqus.boundary_faces(tets)
    centro = nodi.mean(axis=0)
    forze: dict[int, np.ndarray] = {}
    for faccia in facce:
        p = nodi[faccia]
        normale = np.cross(p[1] - p[0], p[2] - p[0])
        area = float(np.linalg.norm(normale)) / 2.0
        if area == 0.0:
            continue
        versore = normale / np.linalg.norm(normale)
        # Il verso delle facce di bordo non e' garantito uscente: sul provino
        # convesso lo si stabilisce confrontando con il centro del solido.
        if float(np.dot(versore, p.mean(axis=0) - centro)) < 0.0:
            versore = -versore
        quota = (area / 3.0) * (sigma @ versore)
        for indice in faccia:
            forze[int(indice)] = forze.get(int(indice), np.zeros(3)) + quota

    # Tre nodi lontani fra loro, vincolati al valore vero del campo: tolgono i
    # sei moti rigidi. Sono nove condizioni invece di sei, quindi ridondanti --
    # ma la soluzione esatta le soddisfa tutte, quindi resta la soluzione, e in
    # cambio non c'e' alcun rischio di scegliere una terna degenere che
    # lascerebbe la matrice singolare. `ccx` su matrice singolare esce **zero**
    # senza avvisi (vedi docs/validazione/ricerca-calculix-e-c3d4.md), quindi
    # quel rischio non si vedrebbe come errore ma come numeri enormi.
    ancore = [
        _nodo_piu_vicino(nodi, (0.0, 0.0, 0.0)),
        _nodo_piu_vicino(nodi, (LATO[0], 0.0, 0.0)),
        _nodo_piu_vicino(nodi, (0.0, LATO[1], LATO[2])),
    ]
    assert len(set(ancore)) == 3, "le tre ancore devono essere nodi distinti"

    imposti = {
        int(i): {g + 1: float(atteso[int(i), g]) for g in range(3)} for i in ancore
    }
    carichi = {i: tuple(v) for i, v in forze.items() if int(i) not in set(ancore)}

    insiemi = {"ANCORA": np.array([ancore[0]]), "TUTTI": np.arange(len(nodi))}
    spostamenti = _risolvi(
        tmp_path, nodi, tets,
        node_sets=insiemi, fixed_nset="ANCORA",
        spostamenti_imposti={k: v for k, v in imposti.items() if k != ancore[0]},
        carichi_nodali=carichi,
    )

    scarto = _scarto_relativo(spostamenti, nodi, range(len(nodi)))
    limite = FATTORE * _pavimento_del_formato(atteso)
    assert scarto <= limite, (
        f"il campo lineare non e' riprodotto sotto carichi consistenti: scarto "
        f"relativo {scarto:.3e} contro un limite di {limite:.3e}, cioe' {FATTORE:g} "
        "volte la risoluzione del .dat"
    )
