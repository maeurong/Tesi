"""Quanto l'incertezza sui materiali muove i risultati, e perche' e' algebra.

Ticket https://github.com/maeurong/Tesi/issues/43.

**Il problema che questo ticket chiude.** La tavola `MURO 1` non dichiara la
classe del calcestruzzo: i parametri meccanici sono un'assunzione
dell'operatore. Per una tesi il cui contributo e' **geometrico** e' la lacuna
letale, e la letteratura non la colma mai -- nessuno dei 17 articoli letti
separa il contributo dei materiali da quello della geometria. Un 5% di scarto
sulla freccia non prova nulla se un 20% di incertezza su E puo' produrne uno
identico.

**Ma in elasticita' lineare la propagazione e' esatta, non campionata.**
Misurato prima di scrivere qualunque cosa:

| se l'incertezza su | vale +-X% | la freccia | la frequenza |
|---|---|---|---|
| `E` | +-X% | -+X%, **esatto** | -+X/2% |
| `rho` | +-X% | **nessun effetto** sotto carico imposto | -+X/2% |
| `nu` | tutto il suo intervallo | **0,29%** | trascurabile |

Un campionamento a forza di corse misurerebbe una moltiplicazione. Il capitolo
dichiara le leggi in forma chiusa; questi test le **verificano** come oracolo.

**Quanto vale davvero quel +-X%.** Gli intervalli normativi stanno in
`docs/validazione/materiali-intervallo.md`; qui la conseguenza numerica:

| incertezza | banda | -> freccia | -> frequenza |
|---|---|---|---|
| `E`, classe nota (C20/25-C40/50) | **+-8%** | +-8% | +-4% |
| `E`, aggregato ignoto (EC2 3.1.3(2)) | **+-34%** | +-34% | +16/-19% |
| `rho` (2,40-2,60e-9 t/mm^3) | +-4% | **0** | -+2% |
| `nu` (0,14-0,26) | tutto | **0,29%** | trascurabile |

La riga che conta e' la seconda: **la tavola non dichiara ne' la classe ne'
l'aggregato**, e finche' resta cosi' la banda sulla freccia e' +-34%, non +-8%.
Restringerla non e' lavoro di calcolo, e' un dato da procurarsi.

**E sono una verifica in piu' della catena.** Le leggi di scala vengono dalla
teoria, non dal codice: se il modulo finisse nel posto sbagliato del deck, se
le unita' si mescolassero, se il solutore leggesse la densita' come peso
specifico, il prodotto `u E` smetterebbe di essere costante. Un test di
regressione sullo stesso numero non se ne accorgerebbe.

**Cosa questo ticket NON chiude.** Il confronto con l'errore **geometrico**, che
richiede la misura sul telaio e quindi il checkout principale (#45). Qui c'e'
la meta' che si puo' calcolare esattamente; l'altra meta' va misurata.
"""

from __future__ import annotations

import math
import pathlib
import shutil
import subprocess

import numpy as np
import pytest

from ccx_utils import read_dat_displacements
from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import CarichiConfig, Material, Modale

pytestmark = pytest.mark.validazione

LUNGHEZZA, LARGHEZZA, ALTEZZA = 400.0, 30.0, 40.0
CARICO = 1000.0  # N all'estremo

# Il campo plausibile del calcestruzzo, da `docs/validazione/materiali-intervallo.md`.
# Per E e rho servono solo punti ben separati, perche' cio' che si verifica e' la
# **legge**, non il valore; l'intervallo scelto copre con margine quello normativo.
# Per `nu` invece il valore misurato E' il risultato, quindi gli estremi sono
# esattamente quelli della fonte (fib MC2010 §5.1.7.3: 0,14-0,26).
MODULI = (20_000.0, 30_000.0, 45_000.0)  # MPa -- copre 20 973-42 264 (EC2 §3.1.3(2))
DENSITA = (2.0e-9, 2.4e-9, 2.5e-9)  # t/mm^3 -- copre 2,40-2,60e-9 (EN 206:2013)
POISSON = (0.14, 0.20, 0.26)  # gli estremi della fonte, non un campione interno


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


@pytest.fixture(scope="module")
def maglio():
    vertici, facce = synth.box_mesh((LUNGHEZZA, LARGHEZZA, ALTEZZA))
    nodi, tets = volume.tetrahedralize(
        vertici, facce, max_volume=12.0**3 / 6.0,
        min_ratio=1.8, max_steiner_points=-1, nobisect=False, order=2,
    )
    x = nodi[:, 0]
    insiemi = {
        "INCASTRO": np.flatnonzero(x <= x.min() + 1e-6),
        "ESTREMO": np.flatnonzero(x >= x.max() - 1e-6),
        "TUTTI": np.arange(len(nodi)),
    }
    return nodi, tets, insiemi


def _corri(tmp_path, maglio, young, densita, poisson=0.2, modale=False) -> float:
    eseguibile = _ccx_o_salta()
    nodi, tets, insiemi = maglio
    estremo = insiemi["ESTREMO"]
    materiale = Material(name="P", young=young, poisson=poisson, density=densita)
    extra: dict[str, object] = {}
    if modale:
        extra["carichi"] = CarichiConfig(modale=Modale(modi=3))
    else:
        extra["carichi_nodali"] = {
            int(i): (0.0, 0.0, -CARICO / len(estremo)) for i in estremo
        }
    cartella = pathlib.Path(tmp_path)
    abaqus.write_inp(
        cartella / "m.inp", nodi, tets, material=materiale, element_type="C3D10",
        fixed_nset="INCASTRO", node_sets=insiemi, print_nsets=("ESTREMO",),
        gravity=0.0, **extra,
    )
    esito = subprocess.run(
        [eseguibile, "-i", "m"], cwd=cartella, capture_output=True, text=True, timeout=900
    )
    assert esito.returncode == 0, esito.stdout[-2000:]
    if modale:
        return solve.leggi_frequenze(cartella / "m.dat")[0]
    spostamenti = read_dat_displacements(cartella / "m.dat")
    return abs(float(np.mean([spostamenti[int(i) + 1][2] for i in estremo])))


def test_la_freccia_va_come_l_inverso_del_modulo(tmp_path, maglio):
    """`u E` costante: la propagazione dell'incertezza su E e' **esatta**.

    Sotto carico imposto la rigidezza scala linearmente con E, quindi lo
    spostamento va come `1/E`. Misurato su un intervallo che copre un fattore
    2,25: il prodotto resta costante a una parte su 10^8.

    Conseguenza per la tesi: **un'incertezza del X% su E da' esattamente il X%
    sulla freccia**, e non serve nessun campionamento per saperlo.

    Mutazione che lo uccide: scrivere il modulo elastico al posto sbagliato
    nella card `*ELASTIC`, o mescolare le unita' -- il prodotto smetterebbe di
    essere costante. Un test di regressione sullo stesso numero non se ne
    accorgerebbe.
    """
    prodotti = []
    for indice, young in enumerate(MODULI):
        cartella = tmp_path / f"E{indice}"
        cartella.mkdir()
        prodotti.append(_corri(cartella, maglio, young, 2.4e-9) * young)
    print("\nfreccia per modulo, prodotto u*E:")
    for young, prodotto in zip(MODULI, prodotti, strict=True):
        print(f"  E = {young:>7.0f} MPa   u*E = {prodotto:.5f}")
    scarto = (max(prodotti) - min(prodotti)) / np.mean(prodotti)
    print(f"  scarto relativo sul prodotto: {scarto:.2e}")
    assert scarto < 1e-6, f"u*E non e' costante: scarto {scarto:.2e}"


def test_la_densita_non_muove_la_freccia_sotto_carico_imposto(tmp_path, maglio):
    """Sotto carico imposto e senza gravita', `rho` non entra nell'equilibrio.

    E' l'altra meta' della propagazione, e la piu' facile da dare per scontata
    senza verificarla: se la densita' finisse per sbaglio in una card che
    contribuisce al carico, la freccia si muoverebbe.
    """
    frecce = []
    for indice, densita in enumerate(DENSITA):
        cartella = tmp_path / f"rho{indice}"
        cartella.mkdir()
        frecce.append(_corri(cartella, maglio, 30_000.0, densita))
    scarto = (max(frecce) - min(frecce)) / np.mean(frecce)
    print(f"\ndensita' su tre valori: freccia costante entro {scarto:.2e}")
    assert scarto < 1e-9, f"la densita' muove la freccia di {scarto:.2e}: entra dove non deve"


def test_la_frequenza_va_come_la_radice_del_rapporto(tmp_path, maglio):
    """`f / sqrt(E/rho)` costante: la propagazione modale e' esatta anch'essa.

    La frequenza propria di un sistema elastico va come la radice del rapporto
    fra rigidezza e massa, e qui entrambe scalano con un parametro solo.
    Misurato su quattro combinazioni che coprono un fattore 2,25 su E e 1,25
    su rho.

    Conseguenza: **un'incertezza del X% su E da' X/2% sulla frequenza**, e
    altrettanto per rho ma di segno opposto. La frequenza e' quindi **meno**
    sensibile ai materiali dello spostamento -- fatto che conta, perche' la
    frequenza e' la grandezza con cui si smentisce un modello mal vincolato.
    """
    casi = ((20_000.0, 2.4e-9), (30_000.0, 2.4e-9), (30_000.0, 2.0e-9), (45_000.0, 2.5e-9))
    rapporti = []
    print("\nfrequenza per combinazione, rapporto f/sqrt(E/rho):")
    for indice, (young, densita) in enumerate(casi):
        cartella = tmp_path / f"f{indice}"
        cartella.mkdir()
        frequenza = _corri(cartella, maglio, young, densita, modale=True)
        rapporto = frequenza / math.sqrt(young / densita)
        rapporti.append(rapporto)
        print(f"  E={young:>7.0f} rho={densita:.2e}  f={frequenza:>9.4f} Hz  -> {rapporto:.7e}")
    scarto = (max(rapporti) - min(rapporti)) / float(np.mean(rapporti))
    print(f"  scarto relativo sul rapporto: {scarto:.2e}")
    assert scarto < 1e-5, f"f/sqrt(E/rho) non e' costante: scarto {scarto:.2e}"


def test_il_coefficiente_di_poisson_e_trascurabile_e_di_quanto(tmp_path, maglio):
    """Trascurabile **misurato**, non trascurato.

    Su tutto l'intervallo documentato per il calcestruzzo -- da 0,14 a 0,26,
    fib Model Code 2010 5.1.7.3 -- la freccia si muove dello **0,29%**.
    Dichiarare un contributo trascurabile misurandolo e' un'altra cosa dal darlo
    per tale: il numero sta in tesi accanto all'affermazione.

    Gli estremi sono quelli della fonte, non un campione preso al suo interno:
    su un intervallo piu' stretto il numero uscirebbe piu' piccolo, e sarebbe
    piu' piccolo per costruzione invece che per misura. Nota che le norme
    (EC2 3.1.3(4), NTC 11.2.10.4) danno 0,2 per il calcestruzzo integro e 0
    per quello fessurato: e' una scelta di modello, non una banda di misura, e
    non e' quella che si propaga qui.

    Il valore vale **per questa grandezza su questo provino**: una mensola
    snella sotto flessione. Su una geometria tozza, o su una tensione, `nu`
    puo' pesare di piu', e questo test non lo dice.
    """
    frecce = []
    for indice, poisson in enumerate(POISSON):
        cartella = tmp_path / f"nu{indice}"
        cartella.mkdir()
        frecce.append(_corri(cartella, maglio, 30_000.0, 2.4e-9, poisson=poisson))
    escursione = (max(frecce) - min(frecce)) / float(np.mean(frecce))
    print("\nfreccia per coefficiente di Poisson:")
    for poisson, freccia in zip(POISSON, frecce, strict=True):
        print(f"  nu = {poisson:.2f}   u = {freccia:.6f} mm")
    print(f"  escursione su tutto l'intervallo: {escursione:.2%}")
    assert escursione < 0.005, (
        f"nu muove la freccia del {escursione:.2%}: non e' piu' trascurabile, "
        "e l'analisi deve includerlo"
    )
