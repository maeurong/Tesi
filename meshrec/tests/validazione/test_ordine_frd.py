"""L'ordine delle colonne del tensore nel `.frd`, verificato contro `ccx` vero.

Ticket https://github.com/maeurong/Tesi/issues/39.

`solve.von_mises` assume che le sei componenti arrivino nell'ordine
**SXX, SYY, SZZ, SXY, SYZ, SZX**. Il suo docstring dice gia' perche' importa:
«leggerlo sbagliato non solleva nulla e produce un numero plausibile, che e' il
modo peggiore di sbagliare».

**Perche' i test esistenti non lo coprivano.** Gli `.frd` di `test_solve.py` li
scrive il test stesso, e portano trazione monoassiale -- `(sigma, 0, 0, 0, 0, 0)`.
Quello stato e' **invariante rispetto a qualunque permutazione** dentro il
gruppo dei tre normali e dentro quello dei tre taglianti: nessun riordino lo
cambia, quindi nessun riordino lo fa cadere. La formula aveva due oracoli
analitici solidi; la mappatura non ne aveva nessuno.

**Come si costruisce lo stato che discrimina.** Serve un tensore con tutte e
sei le componenti **distinte e non nulle**, prodotto da `ccx` e non scritto a
mano. Il patch test lo regala: un campo di spostamento lineare `u = eps x`
imposto su tutto il bordo produce uno stato di deformazione **costante** e
quindi una tensione costante nota in forma chiusa,

    sigma = lambda tr(eps) I + 2 mu eps

Basta scegliere `eps` con sei componenti distinte. Il confronto e' allora fra
sei numeri calcolati a mano e sei numeri letti dal file, uno per uno: una
permutazione qualunque li scambia, e il test cade.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import Material

pytestmark = pytest.mark.validazione

LATO = (60.0, 60.0, 60.0)
MATERIALE = Material(name="PROVA", young=30000.0, poisson=0.2, density=2.4e-9)

# Tolleranza del confronto, in frazione dell'ampiezza del tensore. Una sola,
# usata **sia** per accettare le colonne lette **sia** per pretendere che le sei
# componenti attese siano separate: se le due divergessero, il provino potrebbe
# avere due componenti piu' vicine di quanto il confronto sappia distinguere, e
# la loro permutazione passerebbe inosservata.
TOLLERANZA = 0.02

# Deformazione costante con **tutte e sei le componenti di tensione distinte e
# non nulle**. E' l'unica forma che discrimina: due componenti troppo vicine, o
# una nulla, e la permutazione che le scambia resta invisibile.
#
# Scelta al contrario, e non a occhio. Un primo tentativo con deformazioni
# "belle" produsse sigma_yy = 0,58333 e sigma_zx = 0,575, distanti lo 0,23%
# dell'ampiezza: sotto la tolleranza, quindi il loro scambio **sopravviveva** al
# confronto. Il verdetto «ordine giusto» sarebbe stato vero ma non dimostrato.
# Qui si sono scelte prima le sei tensioni, ben separate, e si sono ricavate le
# deformazioni invertendo la legge di Hooke.
#
# Tensioni volute: SXX 4,0 | SYY 1,0 | SZZ 2,5 | SXY 0,5 | SYZ 1,5 | SZX 3,0.
# La matrice e' simmetrica, cioe' priva di rotazione rigida: la rotazione non
# produce tensione e renderebbe il legame fra campo imposto e tensione attesa
# meno diretto.
EPS = np.array(
    [
        [1.1e-4, 2.0e-5, 1.2e-4],
        [2.0e-5, -1.0e-5, 6.0e-5],
        [1.2e-4, 6.0e-5, 5.0e-5],
    ]
)

# L'ordine che `solve.von_mises` dichiara, in coordinate della matrice.
ORDINE_DICHIARATO = (
    ("SXX", (0, 0)),
    ("SYY", (1, 1)),
    ("SZZ", (2, 2)),
    ("SXY", (0, 1)),
    ("SYZ", (1, 2)),
    ("SZX", (2, 0)),
)


def _tensione_attesa() -> np.ndarray:
    """`sigma = lambda tr(eps) I + 2 mu eps`, la legge di Hooke isotropa."""
    lam = (
        MATERIALE.young * MATERIALE.poisson
        / ((1.0 + MATERIALE.poisson) * (1.0 - 2.0 * MATERIALE.poisson))
    )
    mu = MATERIALE.young / (2.0 * (1.0 + MATERIALE.poisson))
    return lam * np.trace(EPS) * np.eye(3) + 2.0 * mu * EPS


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _indici_di_bordo(nodi: np.ndarray) -> np.ndarray:
    tolleranza = 1e-9
    fuori = np.zeros(len(nodi), dtype=bool)
    for asse, lunghezza in enumerate(LATO):
        fuori |= np.abs(nodi[:, asse]) < tolleranza
        fuori |= np.abs(nodi[:, asse] - lunghezza) < tolleranza
    return np.flatnonzero(fuori)


def _blocco_di_tensione(tmp_path) -> np.ndarray:
    """Le sei componenti nodali che `ccx` scrive, su uno stato costante noto."""
    eseguibile = _ccx_o_salta()
    vertici, facce = synth.box_mesh(LATO)
    nodi, tets = volume.tetrahedralize(
        vertici, facce,
        max_volume=6000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=1,
    )
    atteso = nodi @ EPS.T
    bordo = _indici_di_bordo(nodi)
    origine = int(np.argmin(np.linalg.norm(nodi, axis=1)))
    assert np.allclose(nodi[origine], 0.0), "serve un nodo nell'origine, dove il campo e' nullo"

    imposti = {
        int(i): {g + 1: float(atteso[int(i), g]) for g in range(3)}
        for i in bordo
        if int(i) != origine
    }
    abaqus.write_inp(
        tmp_path / "tensore.inp", nodi, tets,
        material=MATERIALE, element_type="C3D4",
        node_sets={"ANCORA": np.array([origine]), "TUTTI": np.arange(len(nodi))},
        fixed_nset="ANCORA", print_nsets=("TUTTI",), gravity=0.0,
        spostamenti_imposti=imposti,
    )
    esito = subprocess.run(
        [eseguibile, "-i", "tensore"],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]

    blocchi = [b for b in solve.leggi_frd(tmp_path / "tensore.frd") if b.grandezza == "STRESS"]
    assert blocchi, "nessun blocco STRESS nel .frd: il deck non ne chiede l'uscita"
    dati = blocchi[-1].dati
    assert dati.shape[1] == 6, f"{dati.shape[1]} componenti invece di sei"
    return dati


def test_lo_stato_di_prova_discrimina_ogni_permutazione():
    """Senza questo, tutto il resto del file potrebbe essere verde a vuoto.

    Se due componenti attese coincidessero, o una fosse nulla, la permutazione
    che le scambia resterebbe invisibile -- ed e' esattamente il difetto per cui
    i test esistenti non coprivano la mappatura.
    """
    sigma = _tensione_attesa()
    valori = [sigma[i, j] for _, (i, j) in ORDINE_DICHIARATO]
    scala = float(np.abs(sigma).max())
    # La separazione si misura **con la stessa tolleranza del confronto**, non
    # con una soglia scelta a parte: due componenti piu' vicine di quanto il
    # confronto distingua sono, per quel confronto, la stessa componente.
    minima = TOLLERANZA * scala
    assert all(abs(v) > minima for v in valori), f"una componente e' troppo piccola: {valori}"
    for a in range(6):
        for b in range(a + 1, 6):
            assert abs(valori[a] - valori[b]) > minima, (
                f"{ORDINE_DICHIARATO[a][0]} = {valori[a]:.4f} e "
                f"{ORDINE_DICHIARATO[b][0]} = {valori[b]:.4f} distano meno di "
                f"{minima:.4f}: la loro permutazione sarebbe invisibile al confronto"
            )


def test_le_sei_colonne_del_frd_stanno_nell_ordine_dichiarato(tmp_path):
    """Il confronto che mancava: sei numeri letti contro sei calcolati.

    Mutazione che lo uccide: una permutazione qualunque delle colonne lette,
    per esempio scambiare SXY e SYZ in `solve.von_mises`.
    """
    dati = _blocco_di_tensione(tmp_path)
    sigma = _tensione_attesa()

    # Stato costante: ogni nodo porta lo stesso tensore. La mediana invece
    # della media perche' `ccx` estrapola ai nodi dai punti d'integrazione, e
    # sui nodi di bordo l'estrapolazione e' meno accurata di quella interna.
    letto = np.median(dati, axis=0)

    scala = float(np.abs(sigma).max())
    for colonna, (nome, (i, j)) in enumerate(ORDINE_DICHIARATO):
        atteso = float(sigma[i, j])
        scarto = abs(letto[colonna] - atteso) / scala
        assert scarto < TOLLERANZA, (
            f"colonna {colonna} ({nome}): letto {letto[colonna]:.5f}, atteso {atteso:.5f}, "
            f"scarto {scarto:.2%} dell'ampiezza. L'ordine dichiarato in "
            "`solve.von_mises` non e' quello che ccx scrive"
        )


def test_ogni_permutazione_del_tensore_verrebbe_colta(tmp_path):
    """La prova che il confronto morde davvero.

    Non basta che i sei numeri combacino: bisogna mostrare che **non**
    combacerebbero con un ordine sbagliato. Si prendono le sei colonne lette,
    le si permuta in tutti i modi diversi dall'identita', e si verifica che
    nessuna passi il confronto.
    """
    import itertools

    dati = _blocco_di_tensione(tmp_path)
    sigma = _tensione_attesa()
    letto = np.median(dati, axis=0)
    attesi = np.array([sigma[i, j] for _, (i, j) in ORDINE_DICHIARATO])
    scala = float(np.abs(sigma).max())

    sopravvissute = [
        perm
        for perm in itertools.permutations(range(6))
        if perm != tuple(range(6))
        and np.all(np.abs(letto[list(perm)] - attesi) / scala < TOLLERANZA)
    ]
    assert not sopravvissute, (
        f"{len(sopravvissute)} permutazioni passano il confronto: lo stato di prova "
        "non discrimina, e il test sarebbe verde anche con l'ordine sbagliato"
    )


def test_la_von_mises_dalla_lettura_coincide_con_quella_analitica(tmp_path):
    """Il controllo end to end: dal file alla grandezza che finisce in tesi.

    Verifica formula **e** mappatura insieme. Se l'ordine fosse sbagliato in un
    modo che scambia un normale con un tagliante, la von Mises cambierebbe --
    ed e' l'unico numero tensionale che il programma mostra.
    """
    dati = _blocco_di_tensione(tmp_path)
    sigma = _tensione_attesa()

    normali = 0.5 * (
        (sigma[0, 0] - sigma[1, 1]) ** 2
        + (sigma[1, 1] - sigma[2, 2]) ** 2
        + (sigma[2, 2] - sigma[0, 0]) ** 2
    )
    taglianti = 3.0 * (sigma[0, 1] ** 2 + sigma[1, 2] ** 2 + sigma[2, 0] ** 2)
    attesa = float(np.sqrt(normali + taglianti))

    calcolata = float(np.median(solve.von_mises(dati)))
    scarto = abs(calcolata - attesa) / attesa
    assert scarto < TOLLERANZA, (
        f"von Mises {calcolata:.5f} contro {attesa:.5f} analitica, scarto {scarto:.2%}"
    )
