"""L'equilibrio delle reazioni sull'elemento che gira davvero (#40).

Il manuale di CalculiX (§6.11.5) dichiara che sotto `*DLOAD` la `RF` non e'
la reazione: «selecting RF gives you the sum of the reaction forces and the
loading forces». La quota di carico e' pero' **calcolabile esattamente** --
e' il vettore dei carichi consistenti -- quindi `somma(RF) + quota` resta
un'identita' algebrica. Cio' che dipende dall'elemento sono i coefficienti:

| elemento | vertici | nodi di lato |
|---|---|---|
| C3D4 | `+V/4` | -- |
| C3D10 | **`-V/20`** | `+V/5` |

Fino al 26/08/2026 il codice applicava `+V/4` ai vertici qualunque fosse
l'elemento. Su **C3D10, predefinito dalla PR #53**, questo sbagliava anche
di segno, e il verdetto `reazioni` era falso su **ogni** corsa. Nessun test
lo vedeva perche' nessun test esegue la pipeline vera con `ccx` vero: i test
di `risolvi` usano un `ccx` finto. Questo file esegue `ccx` vero.

Misurato su un cubo di 100 mm a quattro raffinamenti, scarto relativo sul
peso:

| elementi | formula lineare | formula consistente |
|---|---|---|
| 48 | 1,67e-01 | 1,8e-08 |
| 285 | 9,29e-02 | 4,0e-08 |
| 640 | 6,67e-02 | 5,3e-09 |
| 1287 | 5,79e-02 | 2,6e-09 |

Lo scarto sbagliato **cala raffinando**: e' la firma di un rapporto
bordo/volume, cioe' di un artefatto di maglio. E' la stessa firma che
l'indagine del 21/08/2026 aveva incontrato su C3D4 e che allora aveva
portato fuori strada -- stessa trappola, stesso controllo, un elemento piu'
tardi.

**`*SECTION PRINT, SOF` misurata e scartata.** Il manuale la indica come
alternativa, e funziona (`ccx` 2.22 la accetta e stampa «statistics for
surface set»), ma e' l'integrale della **tensione** sulla superficie: porta
l'errore di discretizzazione e converge col maglio, da 21,0% a 6,6% su C3D4
e da 2,3% a 1,1% su C3D10, contro l'1e-8 fermo dell'identita'. Un controllo
di conservazione col 6,6% di residuo non puo' avere tolleranza 1e-4, e
soprattutto confonderebbe «il modello e' sbagliato» con «il maglio e' rado»
-- che e' la distinzione per cui il controllo esiste.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import Material

pytestmark = pytest.mark.validazione

LATO = 100.0
MATERIALE = Material(name="ACCIAIO", young=210_000.0, poisson=0.3, density=7.85e-9)


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _corri(tmp_path, order: int, element_type: str):
    vertici, facce = synth.box_mesh((LATO, LATO, LATO))
    nodi, elementi = volume.tetrahedralize(
        vertici, facce, max_volume=(LATO / 2.0) ** 3 / 6.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False, order=order,
    )
    base = np.flatnonzero(nodi[:, 2] <= nodi[:, 2].min() + 1e-9)
    deck = tmp_path / "m.inp"
    abaqus.write_inp(
        deck, nodi, elementi, node_sets={"BASE": base}, material=MATERIALE,
        element_type=element_type, fixed_nset="BASE",
    )
    subprocess.run([_ccx_o_salta(), "-i", deck.stem], cwd=deck.parent,
                   capture_output=True, text=True)

    reazioni = solve.leggi_reazioni(deck.with_suffix(".dat"), passo=1)
    somma = np.sum(np.array(list(reazioni.values()), dtype=np.float64), axis=0)
    massa = float(MATERIALE.density) * solve._volume_totale(nodi, elementi)
    return nodi, elementi, reazioni, somma, massa


def _scarto(somma, massa, quota, gravita=abaqus.GRAVITY_MM_S2):
    peso = np.array([0.0, 0.0, (massa - quota) * gravita])
    return float(np.linalg.norm(somma - peso) / (massa * gravita))


@pytest.mark.parametrize("order,element_type", [(1, "C3D4"), (2, "C3D10")], ids=["C3D4", "C3D10"])
def test_la_somma_delle_reazioni_piu_la_quota_eguaglia_il_peso(tmp_path, order, element_type):
    """L'identita' vale su entrambi gli elementi, con `ccx` vero.

    Non e' un test di regressione su un numero registrato: il peso atteso e'
    `rho*V*g` calcolato qui, e la quota e' la formula dei carichi
    consistenti. Se il solutore, il deck o la formula andassero in disaccordo,
    l'identita' salterebbe.
    """
    nodi, elementi, reazioni, somma, massa = _corri(tmp_path, order, element_type)
    quota = solve._quota_tributaria_gravita(
        nodi, elementi, reazioni.keys(), MATERIALE.density, element_type
    )

    assert _scarto(somma, massa, quota) < solve._TOLLERANZA_REAZIONI


def test_su_c3d10_la_formula_del_lineare_fallirebbe_il_controllo(tmp_path):
    """La seconda meta' del reperto, e senza di essa la prima non dimostra
    nulla: che l'identita' regga con la formula giusta non dice che quella
    vecchia fosse sbagliata.

    Qui si applica la formula del tetraedro **lineare** a un maglio
    **quadratico** -- esattamente cio' che il codice faceva prima -- e si
    pretende che il controllo **non** passi. Il numero misurato e' 1,67e-01
    contro una tolleranza di 1e-4: tre ordini di grandezza, non un caso al
    limite.
    """
    nodi, elementi, reazioni, somma, massa = _corri(tmp_path, 2, "C3D10")

    giusta = solve._quota_tributaria_gravita(
        nodi, elementi, reazioni.keys(), MATERIALE.density, "C3D10"
    )
    sbagliata = solve._quota_tributaria_gravita(
        nodi, elementi, reazioni.keys(), MATERIALE.density, "C3D4"
    )

    assert _scarto(somma, massa, giusta) < solve._TOLLERANZA_REAZIONI
    assert _scarto(somma, massa, sbagliata) > 1e-2, (
        "con la formula del lineare su un maglio quadratico il controllo deve "
        "fallire di molto, non di poco: se questo scarto scendesse, il reperto "
        "andrebbe rimisurato invece di restare scritto"
    )
