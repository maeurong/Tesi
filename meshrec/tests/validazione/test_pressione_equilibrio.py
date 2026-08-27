"""La pressione arriva davvero al solutore, e vale quanto dichiarato (#10).

`tests/test_carichi_distribuiti.py` prova che il deck **scrive** la superficie
e la card `*DSLOAD`. Non prova che il solutore la **applichi**: un nome di
superficie sbagliato, una faccia numerata male o un segno capovolto passano
quel banco e si vedono solo qui. E' la stessa distinzione per cui
`test_equilibrio_reazioni.py` esiste accanto ai test di `write_inp`.

**Come la pressione si isola dalla gravita', senza stimarla.** Ogni passo
statico ripete il peso proprio, e sotto `*DLOAD` la `RF` non e' la sola
reazione ma «the sum of the reaction forces and the loading forces»
(manuale CalculiX §6.11.5). Il termine gravitazionale e' pero' **identico nei
due passi**, quindi la loro **differenza** lo cancella per sottrazione e
lascia la sola pressione. Non c'e' alcuna quota tributaria da calcolare, e
nessuna approssimazione entra nel confronto.

Il provino e' costruito a mano, per due ragioni misurate:

- TetGen da' magli diversi fra Linux x86-64 e macOS arm64 a parita' di
  versione e di ingresso (#66), e qui l'area della faccia caricata deve
  valere **esattamente** 400 mm² su entrambe;
- e' alto **otto** strati e non quattro perche' `set_tolerance_factor` vale 6
  e la tolleranza dei set di faccia e' sei volte la spaziatura: su un provino
  di quattro strati il `*NSET` di `BASE` finisce per contenere **ogni** nodo
  del modello, il solido resta bloccato per intero e le reazioni escono tutte
  nulle. Misurato provandolo.
"""

import itertools
import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve
from meshrec.core.config import (
    AnalysisConfig,
    CarichiConfig,
    CaricoDistribuito,
    Material,
    SelettoreBox,
    TetConfig,
)

pytestmark = pytest.mark.validazione

_CUBO_IN_SEI = (
    (0, 1, 3, 7), (0, 1, 7, 5), (0, 5, 7, 4),
    (0, 3, 2, 7), (0, 6, 4, 7), (0, 2, 6, 7),
)

PASSO = 10.0
PRESSIONE = 0.25
"""N/mm². Positiva preme dentro la faccia, come vuole la card `P`."""

AREA_ATTESA = 400.0
"""Il tetto del provino: 20 x 20 mm, e non dipende dalla piattaforma."""

MATERIALE = Material(name="ACCIAIO", young=210_000.0, poisson=0.3, density=7.85e-9)


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _lastra(nx: int, ny: int, nz: int):
    """Griglia di celle nei sei tetraedri di Kuhn, orientati positivi.

    L'ordine dei bit -- x sul bit 0, y sul bit 1, z sul bit 2 -- e' quello
    della fixture `griglia_mesh` di `test_abaqus.py`. Invertirlo da' tetraedri
    a jacobiano negativo, che `ccx` rifiuta con «nonpositive jacobian
    determinant»: misurato scrivendolo al contrario.
    """
    indice, punti = {}, []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                indice[(i, j, k)] = len(punti)
                punti.append([i * PASSO, j * PASSO, k * PASSO])
    tetraedri = []
    for i, j, k in itertools.product(range(nx), range(ny), range(nz)):
        angoli = [
            indice[(i + (n & 1), j + ((n >> 1) & 1), k + ((n >> 2) & 1))]
            for n in range(8)
        ]
        tetraedri += [[angoli[n] for n in quattro] for quattro in _CUBO_IN_SEI]
    return np.array(punti, dtype=np.float64), np.array(tetraedri, dtype=np.int64)


def _somma_reazioni(dat, passo: int) -> np.ndarray:
    reazioni = solve.leggi_reazioni(dat, passo=passo)
    return np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)


def test_la_reazione_al_vincolo_vale_la_pressione_dichiarata(tmp_path):
    """RF del passo con pressione, meno RF del passo di sola gravita', e' la risultante.

    La tolleranza non e' scelta qui: e' `solve._TOLLERANZA_REAZIONI`, gia'
    dichiarata nel programma per questa identita' di equilibrio, e usarne una
    propria vorrebbe dire fissare una soglia dopo aver visto il numero.

    Mutazione che lo uccide: capovolgere il segno nella card `*DSLOAD`, oppure
    scrivere la superficie con le facce di un'altra numerazione. Entrambe
    lasciano verdi i controlli che guardano il solo testo del deck.
    """
    nodi, tetraedri = _lastra(2, 2, 8)
    analisi = AnalysisConfig(
        material=MATERIALE, gravity=abaqus.GRAVITY_MM_S2, fixed_nset="BASE",
        step_name="GRAVITA",
    )
    tet = TetConfig(
        min_ratio=1.8, max_volume=None, max_steiner_points=-1, nobisect=True,
        reference_ratio=1.8, element="C3D4",
    )
    selettori = {
        "TETTO": SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 8 * PASSO - 1.0),
            max=(2 * PASSO + 1.0, 2 * PASSO + 1.0, 8 * PASSO + 1.0),
        )
    }
    carichi = CarichiConfig(
        distribuiti=(
            CaricoDistribuito(nome="VENTO", selettore="TETTO", pressione=PRESSIONE),
        )
    )

    deck = tmp_path / "m.inp"
    esito = abaqus.export_model(
        deck, tmp_path / "m.vtu", nodi, tetraedri, analisi, tet,
        reference=nodi, carichi=carichi, selettori=selettori,
    )
    resoconto = esito["carichi_distribuiti"]["VENTO"]
    assert resoconto["area_totale"] == pytest.approx(AREA_ATTESA), (
        "il provino non carica piu' il tetto che questo test crede"
    )
    atteso = np.asarray(resoconto["risultante"], dtype=np.float64)
    assert atteso == pytest.approx([0.0, 0.0, PRESSIONE * AREA_ATTESA])

    subprocess.run(
        [_ccx_o_salta(), "-i", deck.stem], cwd=deck.parent, capture_output=True, text=True
    )
    dat = deck.with_suffix(".dat")
    assert dat.exists() and dat.stat().st_size > 0, "ccx non ha prodotto reazioni"

    solo_gravita = _somma_reazioni(dat, passo=1)
    con_pressione = _somma_reazioni(dat, passo=2)
    misurata = con_pressione - solo_gravita

    # Il verso: la pressione preme **dentro** la faccia superiore, quindi verso
    # il basso, e la base deve spingere in su. Un segno capovolto nella card
    # darebbe lo stesso modulo con la reazione dall'altra parte.
    assert misurata[2] > 0.0, (
        f"la reazione alla base non spinge in su: {misurata}. La pressione "
        "starebbe tirando invece di premere"
    )
    scarto = float(np.linalg.norm(misurata - atteso) / np.linalg.norm(atteso))
    assert scarto < solve._TOLLERANZA_REAZIONI, (
        f"la pressione applicata dal solutore non è quella dichiarata: "
        f"attesa {atteso}, misurata {misurata}, scarto relativo {scarto:.3e}"
    )
