"""La mensola contro la teoria delle travi: il primo numero citabile in tesi.

Ticket https://github.com/maeurong/Tesi/issues/47. Due motivi indipendenti per
cui il provino e' una mensola, e non altro:

1. **ASME V&V 10.1 usa una mensola** -- trave a scatola rastremata, elastica,
   carico non uniforme. Verificare su mensola allinea il lavoro alla prassi
   normativa invece di inventarsi un caso.
2. **Benzley et al. (1995) usa una mensola**, e pubblica le tabelle di errore
   per tet lineare, tet quadratico, esaedro lineare e quadratico. Riusare la
   stessa famiglia di casi rende il nostro numero confrontabile con una tabella
   gia' pubblicata, invece di lasciarlo isolato.

**Due riferimenti analitici, dichiarati entrambi.** Eulero-Bernoulli
(`PL^3/3EI`) e Timoshenko col taglio (`+ PL/kGA`). La differenza fra i due
**non e'** un errore dell'elemento: e' l'errore della teoria di trave snella su
un solido tridimensionale. Riportarli entrambi dice al lettore quanto pesa la
scelta della teoria rispetto a quanto pesa l'elemento -- e il provino e'
scelto **snello apposta**, perche' quel peso sia piccolo e l'elemento resti la
grandezza sotto esame.

**Cosa questo file non misura, e perche'.** La **tensione** alla radice. Benzley
riporta che sul tet lineare l'errore in tensione **resta a circa il 21% anche
raffinando**, mentre lo spostamento migliora -- e' il suo reperto piu' duro.
Leggerla chiede pero' di ricostruire il tensore dal `.frd`, cioe' di fidarsi
dell'ordine delle colonne che #39 dichiara **non verificato**. La freccia e le
frequenze passano invece dal `.dat`, che quel problema non ce l'ha. La tensione
entra quando #39 chiude, non prima.

**Il confronto fra elementi vive qui e non sul telaio.** #45 non puo' misurarlo
sull'as-built, perche' le nuvole di punti non stanno nel repository. Qui c'e' in
piu' la soluzione **esatta**, quindi il confronto non e' fra due modelli ma fra
ciascuno e la teoria.
"""

from __future__ import annotations

import math
import shutil
import subprocess

import numpy as np
import pytest

from ccx_utils import read_dat_displacements
from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import CarichiConfig, Material, Modale

pytestmark = pytest.mark.validazione

# Unita' di lavoro del progetto: mm, N, MPa, tonnellata, secondo.
LUNGHEZZA = 400.0  # mm, lungo x
LARGHEZZA = 30.0  # mm, lungo y  -- l'asse debole
ALTEZZA = 40.0  # mm, lungo z   -- l'asse forte
CARICO = 1000.0  # N, all'estremo libero, lungo -z

MATERIALE = Material(name="PROVA", young=30000.0, poisson=0.2, density=2.4e-9)

# La sezione e' **rettangolare e non quadrata** apposta: su una sezione quadrata
# i due primi modi flessionali sono degeneri, hanno la stessa frequenza, e
# «la prima frequenza» smette di identificare un modo. Con 30 x 40 il primo e'
# la flessione attorno all'asse forte, cioe' lo spostamento nella direzione
# debole, e si riconosce senza ambiguita'.
INERZIA_FORTE = LARGHEZZA * ALTEZZA**3 / 12.0  # flessione in z, quella caricata
INERZIA_DEBOLE = ALTEZZA * LARGHEZZA**3 / 12.0  # flessione in y, il primo modo
AREA = LARGHEZZA * ALTEZZA

# Fattore di taglio della sezione rettangolare, Gere & Timoshenko.
K_TAGLIO = 5.0 / 6.0
# Primo autovalore della mensola incastrata-libera, Hurty & Rubinstein.
BETA_L_PRIMO = 1.8751040687119611


def _freccia_eulero_bernoulli() -> float:
    return CARICO * LUNGHEZZA**3 / (3.0 * MATERIALE.young * INERZIA_FORTE)


def _freccia_timoshenko() -> float:
    """Eulero-Bernoulli piu' la quota di taglio, che su una trave snella e' piccola."""
    taglio = MATERIALE.young / (2.0 * (1.0 + MATERIALE.poisson))
    return _freccia_eulero_bernoulli() + CARICO * LUNGHEZZA / (K_TAGLIO * taglio * AREA)


def _prima_frequenza(inerzia: float) -> float:
    """Hurty & Rubinstein: f = (beta L)^2 / (2 pi) sqrt(EI / (rho A L^4))."""
    rigidezza = MATERIALE.young * inerzia
    massa_lineica = MATERIALE.density * AREA
    return (BETA_L_PRIMO**2 / (2.0 * math.pi)) * math.sqrt(
        rigidezza / (massa_lineica * LUNGHEZZA**4)
    )


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


ELEMENTI = [pytest.param(1, "C3D4", id="C3D4"), pytest.param(2, "C3D10", id="C3D10")]


def _maglio(order: int, passo: float) -> tuple[np.ndarray, np.ndarray]:
    vertici, facce = synth.box_mesh((LUNGHEZZA, LARGHEZZA, ALTEZZA))
    return volume.tetrahedralize(
        vertici, facce,
        max_volume=passo**3 / 6.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=order,
    )


def _insiemi(nodi: np.ndarray) -> dict[str, np.ndarray]:
    tolleranza = 1e-6
    x = nodi[:, 0]
    return {
        "INCASTRO": np.flatnonzero(x <= x.min() + tolleranza),
        "ESTREMO": np.flatnonzero(x >= x.max() - tolleranza),
        "TUTTI": np.arange(len(nodi)),
    }


def _corri(tmp_path, nodi, tets, tipo, **kwargs) -> subprocess.CompletedProcess:
    eseguibile = _ccx_o_salta()
    abaqus.write_inp(
        tmp_path / "mensola.inp", nodi, tets,
        material=MATERIALE, element_type=tipo, fixed_nset="INCASTRO",
        node_sets=_insiemi(nodi), print_nsets=("ESTREMO",),
        gravity=0.0,  # il peso proprio non fa parte del caso di flessione
        **kwargs,
    )
    esito = subprocess.run(
        [eseguibile, "-i", "mensola"],
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]
    return esito


@pytest.mark.parametrize(("order", "tipo"), ELEMENTI)
def test_la_freccia_all_estremo_contro_le_due_teorie(tmp_path, order, tipo):
    """Il numero che la tesi cita, contro la teoria e non contro un altro modello.

    Il carico si ripartisce **in parti uguali** fra i nodi della faccia
    d'estremo. Non e' la ripartizione consistente, e non serve che lo sia: per
    Saint-Venant la freccia all'estremo non risente di come la risultante e'
    distribuita su quella faccia, e li' non si misura tensione. Dirlo e'
    obbligatorio, perche' su una faccia quadratica la ripartizione consistente
    darebbe zero ai vertici (Abaqus Theory Guide §3.2.6) e chi legge il deck
    potrebbe crederla un difetto.
    """
    nodi, tets = _maglio(order, passo=12.0)
    insiemi = _insiemi(nodi)
    estremo = insiemi["ESTREMO"]
    quota = -CARICO / len(estremo)
    carichi = {int(i): (0.0, 0.0, quota) for i in estremo}

    _corri(tmp_path, nodi, tets, tipo, carichi_nodali=carichi)
    spostamenti = read_dat_displacements(tmp_path / "mensola.dat")
    misurata = abs(float(np.mean([spostamenti[int(i) + 1][2] for i in estremo])))

    eb = _freccia_eulero_bernoulli()
    ti = _freccia_timoshenko()

    # La differenza fra le due teorie e' l'errore della teoria, non
    # dell'elemento. Sul provino snello scelto qui vale meno dell'1%: se
    # crescesse, l'elemento smetterebbe di essere la grandezza sotto esame.
    peso_della_teoria = (ti - eb) / ti
    assert peso_della_teoria < 0.02, (
        f"la quota di taglio pesa il {peso_della_teoria:.1%}: il provino e' "
        "troppo tozzo, e l'errore misurato sarebbe della teoria di trave"
    )

    # **Con segno**, non in modulo: un elemento troppo rigido da' una freccia
    # **minore** della teoria, e il segno e' meta' dell'informazione. Scriverlo
    # in modulo faceva leggere «+12,73%» come «freccia troppo grande», che e'
    # l'opposto di quello che succede -- e questo numero finisce in tesi.
    errore_eb = (misurata - eb) / eb
    errore_ti = (misurata - ti) / ti
    print(
        f"\n[{tipo}] freccia misurata {misurata:.5f} mm | "
        f"Eulero-Bernoulli {eb:.5f} ({errore_eb:+.2%}) | "
        f"Timoshenko {ti:.5f} ({errore_ti:+.2%}) | "
        f"nodi {len(nodi)} tet {len(tets)}"
    )

    # La mensola si abbassa: il segno prima del modulo.
    assert float(np.mean([spostamenti[int(i) + 1][2] for i in estremo])) < 0.0

    # Soglia larga e dichiarata: qui si **misura**, non si promuove. Il tet
    # lineare e' noto per sbagliare fra il 10% e il 70% (Benzley 1995), quindi
    # un limite stretto boccerebbe il comportamento atteso invece di un difetto.
    # Cio' che il test sorveglia e' che il risultato resti nello stesso mondo
    # della teoria, non che ci coincida.
    assert abs(errore_ti) < 0.80, f"freccia fuori scala: {errore_ti:+.1%} da Timoshenko"

    # La firma dell'elemento troppo rigido: freccia **minore** della teoria.
    # Sul quadratico lo scarto residuo puo' cadere dai due lati, perche' il
    # riferimento e' teoria di trave e non la soluzione esatta del solido.
    if tipo == "C3D4":
        assert errore_ti < 0.0, (
            "il tet lineare dovrebbe dare una freccia minore della teoria: se e' "
            "maggiore, e' il caso a essere costruito male, non l'elemento"
        )


@pytest.mark.parametrize(("order", "tipo"), ELEMENTI)
def test_la_prima_frequenza_contro_hurty_rubinstein(tmp_path, order, tipo):
    """Il primo modo e' la flessione attorno all'asse **forte**, cioe' lo
    spostamento nella direzione debole: e' li' che la trave e' piu' cedevole.

    Le frequenze si leggono dal `.dat`, non dal `.frd`: nessuna dipendenza
    dall'ordine delle colonne del tensore, che #39 dichiara non verificato.
    """
    nodi, tets = _maglio(order, passo=12.0)
    _corri(
        tmp_path, nodi, tets, tipo,
        carichi=CarichiConfig(modale=Modale(modi=3)),
    )
    frequenze = solve.leggi_frequenze(tmp_path / "mensola.dat")
    assert frequenze, "nessuna frequenza letta dal .dat"

    attesa = _prima_frequenza(INERZIA_DEBOLE)
    misurata = frequenze[0]
    errore = (misurata - attesa) / attesa
    print(
        f"\n[{tipo}] prima frequenza {misurata:.3f} Hz | "
        f"Hurty-Rubinstein {attesa:.3f} Hz ({errore:+.2%}) | modi letti {len(frequenze)}"
    )

    assert misurata > 0.0
    # **Sovrastima attesa, non pretesa.** Il metodo agli spostamenti da' un
    # limite superiore agli autovalori (Ritz-Galerkin, quoziente di Rayleigh:
    # Strang & Fix, Bathe §10.2), e un elemento piu' rigido sovrastima di piu'.
    # La direzione e' teoria, non una misura di Benzley, che riporta moduli.
    assert errore > -0.05, (
        f"frequenza sotto la teoria del {errore:.1%}: il metodo agli spostamenti "
        "da' un limite superiore, quindi una sottostima marcata indica un difetto "
        "del modello e non dell'elemento"
    )
    assert errore < 1.0, f"prima frequenza fuori scala: {errore:.1%}"


def test_il_quadratico_e_piu_vicino_alla_teoria_del_lineare(tmp_path):
    """Il confronto che #45 non puo' fare sul telaio, qui contro la **teoria**.

    E' il numero che giustifica il cambio di predefinito con una misura invece
    che con una citazione. L'attesa dalla letteratura -- il tet lineare e' piu'
    rigido, quindi da' frecce **minori** -- viene messa alla prova, non
    assunta: se uscisse il contrario sarebbe il confronto a essere sbagliato.

    Girano due corse complete, quindi il test e' lento apposta. Sta nel
    marcatore `validazione`, che non entra nella suite normale.
    """
    frecce: dict[str, float] = {}
    for order, tipo in ((1, "C3D4"), (2, "C3D10")):
        cartella = tmp_path / tipo
        cartella.mkdir()
        nodi, tets = _maglio(order, passo=12.0)
        estremo = _insiemi(nodi)["ESTREMO"]
        quota = -CARICO / len(estremo)
        _corri(
            cartella, nodi, tets, tipo,
            carichi_nodali={int(i): (0.0, 0.0, quota) for i in estremo},
        )
        spostamenti = read_dat_displacements(cartella / "mensola.dat")
        frecce[tipo] = abs(float(np.mean([spostamenti[int(i) + 1][2] for i in estremo])))

    riferimento = _freccia_timoshenko()
    # Con segno per la stampa, in modulo per il confronto: sono due domande
    # diverse -- «da che parte sbaglia» e «di quanto sbaglia».
    scarti = {tipo: (v - riferimento) / riferimento for tipo, v in frecce.items()}
    errori = {tipo: abs(v) for tipo, v in scarti.items()}
    print(
        f"\nfreccia di riferimento (Timoshenko) {riferimento:.5f} mm"
        f"\n  C3D4  {frecce['C3D4']:.5f} mm  scarto {scarti['C3D4']:+.2%}"
        f"\n  C3D10 {frecce['C3D10']:.5f} mm  scarto {scarti['C3D10']:+.2%}"
    )

    assert errori["C3D10"] < errori["C3D4"], (
        "il quadratico non e' piu' vicino alla teoria del lineare: il cambio di "
        "predefinito deciso in #41 non regge sulla misura"
    )
    assert frecce["C3D4"] < frecce["C3D10"], (
        "il tet lineare dovrebbe essere piu' rigido e dare una freccia minore. "
        "Se non lo e', e' il confronto a essere sbagliato, non la letteratura"
    )


def test_la_freccia_converge_alla_teoria_raffinando(tmp_path):
    """La curva di convergenza, tre maglie per elemento.

    Serve a due cose. Primo, produce la tabella che il capitolo cita. Secondo,
    e' l'unico modo di distinguere «l'elemento sbaglia» da «la maglia e'
    grossolana»: un errore che **non cala** raffinando non e' discretizzazione,
    e' l'elemento.

    **La comparabilita' fra i due elementi qui non passa dai gradi di liberta'
    ma dal maglio.** Benzley appaia le maglie per DOF, perche' confronta
    famiglie diverse (tetraedri contro esaedri) che non possono condividere la
    stessa suddivisione. Noi confrontiamo lo **stesso identico maglio** letto
    come lineare o come quadratico: stessa geometria, stessi 3027 elementi,
    cambia solo dove stanno i nodi. E' un confronto piu' pulito, e va detto
    che e' diverso dal suo.
    """
    riferimento = _freccia_timoshenko()
    tabella: list[tuple[str, float, int, int, float]] = []

    for passo in (20.0, 14.0, 10.0):
        for order, tipo in ((1, "C3D4"), (2, "C3D10")):
            cartella = tmp_path / f"{tipo}_{passo:g}"
            cartella.mkdir()
            nodi, tets = _maglio(order, passo=passo)
            estremo = _insiemi(nodi)["ESTREMO"]
            quota = -CARICO / len(estremo)
            _corri(
                cartella, nodi, tets, tipo,
                carichi_nodali={int(i): (0.0, 0.0, quota) for i in estremo},
            )
            spostamenti = read_dat_displacements(cartella / "mensola.dat")
            freccia = abs(float(np.mean([spostamenti[int(i) + 1][2] for i in estremo])))
            errore = (freccia - riferimento) / riferimento
            tabella.append((tipo, passo, len(nodi), len(tets), errore))

    print(f"\nfreccia di riferimento (Timoshenko) {riferimento:.5f} mm")
    print("elemento  passo   nodi    tet    errore")
    for tipo, passo, n_nodi, n_tet, errore in tabella:
        print(f"{tipo:<9} {passo:>5.0f} {n_nodi:>6} {n_tet:>6}  {errore:+8.2%}")

    for tipo in ("C3D4", "C3D10"):
        errori = [abs(e) for t, _, _, _, e in tabella if t == tipo]
        assert errori[-1] < errori[0], (
            f"{tipo}: l'errore non cala raffinando ({errori[0]:.2%} -> {errori[-1]:.2%}). "
            "Su questa grandezza -- la freccia, che e' integrale -- la monotonia e' "
            "attesa; non lo sarebbe su una tensione puntuale, dove #48 documenta il "
            "caso contrario su LE10"
        )

    # Il quadratico e' piu' vicino alla teoria a **ogni** livello di raffinamento,
    # non solo al piu' fine: e' cio' che rende la scelta del predefinito una
    # misura invece che una preferenza.
    for passo in (20.0, 14.0, 10.0):
        lineare = next(abs(e) for t, p, _, _, e in tabella if t == "C3D4" and p == passo)
        quadratico = next(abs(e) for t, p, _, _, e in tabella if t == "C3D10" and p == passo)
        assert quadratico < lineare, f"a passo {passo:g} il quadratico non vince"
