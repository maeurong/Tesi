"""Il modello mal vincolato che passava tutte le guardie (#12).

Il ticket dichiarava due guardie sul deck risolto -- codice d'uscita e
conteggio dei `*WARNING` -- e chiedeva che cosa aggiungere. La premessa era
**incompleta**: al momento di risolverlo i verdetti erano gia' cinque, e i
tre aggiunti dal Task 7 (`reazioni`, `vincolo_in_pianta`, `picco`) prendono
da soli i casi grossolani. Misurato il 26/08/2026 su cubo di 100 mm, `ccx`
2.22, con **tutti** i controlli valutati:

| deck | |u|max [mm] | preso da |
|---|---|---|
| ben vincolato | 1,7e-06 | -- (passa, ed e' giusto) |
| nessun `*BOUNDARY` | 8,1e+09 | `reazioni` (nessuna RF) e `vincolo_in_pianta` |
| un solo nodo | 3,3e+09 | `vincolo_in_pianta` (minimo 0) |
| uno spigolo | 2,0e+09 | `vincolo_in_pianta` (minimo 0) |
| appeso in alto | 1,7e-06 | -- (passa: e' un modello ben posto, non spazzatura) |
| diagonale di base | 8,2e-06 | -- (singolare ma non eccitato: la gravita' e' simmetrica) |

Nessuno di questi sei e' il buco. Fermarsi qui avrebbe portato a
«dichiara, non correggere», che e' l'errore di #38 rifatto: il caso non esce
al campionamento perche' va **cercato**.

Il caso cercato e' un frammento **staccato dentro l'impronta**, cioe' cio'
che la segmentazione di una scansione produce quando lascia un'isola. Il
corpo principale e' vincolato bene -- pianta piena, equilibrio soddisfatto --
e l'isola cade libera. `controlla_reazioni` ha tolleranza **relativa**, quindi
un'isola abbastanza leggera resta sotto di essa mentre i suoi nodi volano:

| lato isola [mm] | scarto su RF | |u|max [mm] | tutti e cinque passano |
|---|---|---|---|
| 30 | 5,2e-03 | 5,0e+25 | no (`reazioni`) |
| 10 | 1,9e-04 | 2,9e+09 | no (`reazioni`, di un pelo) |
| **3** | **5,2e-06** | **3,6e+10** | **si'** |
| **1** | **2,0e-07** | **8,0e+21** | **si'** |

La cecita' cresce al **calare** della massa staccata, non del disordine: e'
la firma di una tolleranza relativa, e per questo nessuna sua taratura la
chiude. Serve una grandezza diversa, ed e' `controlla_spostamenti`.
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

# Lato dell'isola. 3 mm sul cubo da 100 e' il caso misurato in cui **tutti** i
# cinque verdetti precedenti passano: piu' grande e la prende `reazioni`, piu'
# piccolo e il reperto resta lo stesso ma con meno margine da mostrare.
LATO_ISOLA = 3.0


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _cubo():
    vertici, facce = synth.box_mesh((LATO, LATO, LATO))
    return volume.tetrahedralize(
        vertici, facce, max_volume=(LATO / 3.0) ** 3 / 6.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False, order=1,
    )


def _con_isola(nodi, elementi):
    """Un tetraedro staccato, sospeso **dentro** l'impronta del cubo.

    Dentro e non di lato: un'isola fuori allargherebbe il parallelepipedo
    contenitore e farebbe cadere `vincolo_in_pianta` da sola (misurato: 0,43
    con l'isola a due lati di distanza), nascondendo il reperto dietro un
    controllo che scatta per il motivo sbagliato.
    """
    origine = np.array([LATO * 0.4, LATO * 0.4, LATO * 0.5])
    unita = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    isola = origine + unita * LATO_ISOLA
    return (
        np.vstack([nodi, isola]),
        np.vstack([elementi, np.arange(4) + len(nodi)]),
    )


def _esegui(tmp_path, nodi, elementi, vincolati):
    deck = tmp_path / "m.inp"
    abaqus.write_inp(
        deck, nodi, elementi, node_sets={"BASE": vincolati}, material=MATERIALE,
        element_type="C3D4", fixed_nset="BASE",
    )
    processo = subprocess.run(
        [_ccx_o_salta(), "-i", deck.stem], cwd=deck.parent, capture_output=True, text=True,
    )
    uscita = (processo.stdout or "") + (processo.stderr or "")

    u_max = None
    for blocco in solve.leggi_frd(deck.with_suffix(".frd")):
        if not blocco.modale and blocco.grandezza == "DISP":
            spostamenti = np.asarray(blocco.dati, dtype=np.float64)[:, :3]
            u_max = float(np.max(np.linalg.norm(spostamenti, axis=1)))

    reazioni = solve.leggi_reazioni(deck.with_suffix(".dat"), passo=1)
    massa = float(MATERIALE.density) * solve._volume_totale(nodi, elementi)
    quota = solve._quota_tributaria_gravita(nodi, elementi, reazioni.keys(), MATERIALE.density)
    peso_atteso = (0.0, 0.0, (massa - quota) * abaqus.GRAVITY_MM_S2)

    return {
        "returncode": processo.returncode,
        "avvisi": solve.controlla_avvisi(uscita.upper().count("*WARNING")),
        "reazioni": solve.controlla_reazioni(
            reazioni, peso_atteso, tolleranza=solve._TOLLERANZA_REAZIONI
        ),
        "vincolo_in_pianta": solve.controlla_vincolo_in_pianta(
            float(abaqus.constraint_plan_extent(nodi, vincolati)["minimo"])
        ),
        "spostamenti": solve.controlla_spostamenti(u_max, solve._dimensione(nodi)),
        "u_max": u_max,
    }


def _base(nodi, quota_minima):
    return np.flatnonzero(nodi[:, 2] <= quota_minima + 1e-9)


def test_il_cubo_ben_vincolato_passa_anche_il_sesto_verdetto(tmp_path):
    """Controprova: senza di essa il verdetto nuovo potrebbe bocciare tutto.

    Un controllo che dice sempre «no» supererebbe il test del reperto qui
    sotto senza vedere nulla -- e' la stessa mutazione che `bimodal` non
    aveva nessuno a ucciderla prima di #38.
    """
    nodi, elementi = _cubo()
    esito = _esegui(tmp_path, nodi, elementi, _base(nodi, nodi[:, 2].min()))

    assert esito["returncode"] == 0
    assert esito["spostamenti"]["passato"], esito["spostamenti"]
    # sei ordini di grandezza sotto la soglia: il verdetto non e' al limite
    assert esito["spostamenti"]["rapporto"] < 1e-6


def test_un_frammento_staccato_passa_i_cinque_verdetti_e_lo_prende_il_sesto(tmp_path):
    """Il reperto di #12, nella forma che dimostra che il buco esisteva.

    Le due meta' vanno insieme e nessuna basta da sola: se i cinque
    precedenti non passassero, il sesto sarebbe ridondante; se il sesto non
    bocciasse, il buco sarebbe ancora aperto. Sono asserite qui sullo
    **stesso** deck e nella stessa corsa di `ccx`.
    """
    cubo_n, cubo_e = _cubo()
    nodi, elementi = _con_isola(cubo_n, cubo_e)
    # solo i nodi di base del cubo: l'isola sta a meta' altezza e non entra
    vincolati = _base(nodi, cubo_n[:, 2].min())
    esito = _esegui(tmp_path, nodi, elementi, vincolati)

    # I cinque che c'erano prima: tutti verdi su un modello con un pezzo che vola.
    assert esito["returncode"] == 0, "ccx non protesta: e' il punto del ticket"
    assert esito["avvisi"]["passato"], "zero *WARNING: e' il punto del ticket"
    assert esito["reazioni"]["passato"], (
        "l'equilibrio globale resta soddisfatto: la tolleranza e' relativa e "
        f"l'isola pesa {esito['reazioni']['scarto_relativo']:.1e} del totale"
    )
    assert esito["vincolo_in_pianta"]["passato"], "il corpo principale e' vincolato bene"

    # Il sesto lo prende, e non di misura.
    assert not esito["spostamenti"]["passato"]
    assert esito["spostamenti"]["rapporto"] > 1e6, esito["spostamenti"]
    assert esito["u_max"] > 1e9


def test_lo_scarto_sulle_reazioni_resta_sotto_la_propria_tolleranza(tmp_path):
    """Il *perche'* i cinque non bastano, misurato invece che argomentato.

    Se un giorno `_TOLLERANZA_REAZIONI` scendesse abbastanza da prendere
    l'isola, questo test fallirebbe e direbbe che il reperto va rimisurato --
    invece di lasciare in piedi una motivazione diventata falsa.
    """
    cubo_n, cubo_e = _cubo()
    nodi, elementi = _con_isola(cubo_n, cubo_e)
    esito = _esegui(tmp_path, nodi, elementi, _base(nodi, cubo_n[:, 2].min()))

    assert esito["reazioni"]["scarto_relativo"] < solve._TOLLERANZA_REAZIONI
