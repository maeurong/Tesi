"""Il numero di passo oltre il nono, verificato contro `ccx` vero.

Ticket https://github.com/maeurong/Tesi/issues/94.

`solve.leggi_frd` legge il numero di passo dal record `100CL` del `.frd`, a
colonne fisse. Fino a nove passi quel numero e' una cifra sola alla colonna
62, ed e' l'unico caso che qualcuno abbia misurato su un file scritto dal
solutore. Dal decimo in poi il campo cresce -- `printf` in C non tronca mai --
ma **da quale lato** dipende dalla larghezza dichiarata nel formato di `ccx`,
che qui non si puo' leggere: il pacchetto CalculiX non e' installabile in
locale. `tests/test_solve.py` copre allora entrambe le forme possibili con due
generatori di record; questo file chiude la questione misurandola, e gira nel
lavoro `benchmark` della CI, che CalculiX ce l'ha.

**Perche' importa.** `risolvi()` attribuisce ogni blocco a un caso di carico
con `etichetta_passo.get(blocco.passo)`. Un passo 10 letto come 1 attribuisce
i risultati del decimo caso al primo, senza un errore e senza un avviso: il
`.vtu` e i verdetti escono pieni di numeri plausibili e sbagliati.

**Perche' dieci passi non sono un'ipotesi.** `abaqus.write_inp` scrive un
passo per la gravita', uno per la spinta, uno per `CARICO_TOP`, uno per ogni
carico posizionato e uno per ogni distribuito, e ne' `posizionati` ne'
`distribuiti` hanno un limite in `core.config`.

`deck_a_molti_passi` resta a disposizione di chi scrivera' il controllo end to
end di `risolvi()` con `ccx` vero (#95): un deck oltre i nove passi e' il suo
oracolo.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import CaricoPosizionato, CarichiConfig, Material, Modale

pytestmark = pytest.mark.validazione

LATO = (60.0, 60.0, 60.0)
MATERIALE = Material(name="PROVA", young=30000.0, poisson=0.2, density=2.4e-9)

# Dieci passi statici: la gravita' piu' nove carichi posizionati. Uno in piu'
# del limite che una cifra sola sa scrivere, cosi' i passi 10 e 11 (il modale)
# cadono entrambi oltre.
N_POSIZIONATI = 9


def deck_a_molti_passi(tmp_path, nome: str = "molti_passi"):
    """Un deck con dieci passi statici piu' uno modale, e la sua mesh.

    Rende `(percorso_inp, nodi, elementi, nomi_dei_casi)`, con `nomi_dei_casi`
    nello stesso ordine in cui `write_inp` scrive i passi -- cioe' la lista
    che `risolvi()` vuole come `casi_di_carico`.
    """
    vertici, facce = synth.box_mesh(LATO)
    nodi, tets = volume.tetrahedralize(
        vertici, facce,
        max_volume=6000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=1,
    )
    base = np.flatnonzero(nodi[:, 2] < 1e-9)
    cima = np.flatnonzero(nodi[:, 2] > LATO[2] - 1e-9)
    assert len(base) and len(cima), "il provino deve avere una base e una cima"

    posizionati = tuple(
        CaricoPosizionato(nome=f"CARICO_{i}", selettore="CIMA", forza=(0.0, 0.0, -1000.0))
        for i in range(1, N_POSIZIONATI + 1)
    )
    percorso = tmp_path / f"{nome}.inp"
    abaqus.write_inp(
        percorso, nodi, tets,
        material=MATERIALE, element_type="C3D4",
        node_sets={"BASE": base, "CIMA": cima},
        fixed_nset="BASE",
        carichi=CarichiConfig(posizionati=posizionati, modale=Modale(modi=2)),
        nset_selettori={"CIMA": cima},
    )
    casi = ["GRAVITA"] + [c.nome for c in posizionati] + ["MODALE"]
    return percorso, nodi, tets, casi


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def test_il_passo_dieci_e_oltre_si_legge_intero_dal_frd_vero(tmp_path):
    """I passi che `ccx` scrive nel `.frd` devono essere 1..11, non 1..9 e poi
    cifre singole.

    Mutazione che lo uccide: rileggere il passo da una colonna sola
    (`_COL_CODA` -> `slice(62, 63)`), che e' il difetto di #94.
    """
    eseguibile = _ccx_o_salta()
    percorso, _nodi, _tets, casi = deck_a_molti_passi(tmp_path)

    esito = subprocess.run(
        [eseguibile, "-i", percorso.stem],
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]

    blocchi = solve.leggi_frd(percorso.with_suffix(".frd"))
    statici = sorted({b.passo for b in blocchi if not b.modale})
    modali = {b.passo for b in blocchi if b.modale}

    assert statici == list(range(1, len(casi))), (
        f"passi statici letti {statici}: il deck ne scrive {len(casi) - 1}, "
        "numerati da 1. Un passo oltre il nono letto come una cifra sola "
        "finisce sul caso di carico sbagliato"
    )
    assert modali == {len(casi)}, f"passo modale letto {modali}, atteso {len(casi)}"


def test_ogni_caso_del_deck_porta_un_blocco_di_tensione(tmp_path):
    """L'altra meta' di #92: il verdetto sul picco si aggrega sui casi che il
    deck dichiara, e quella scelta vale solo se ogni passo statico produce
    davvero un blocco STRESS. `abaqus._passo_statico` scrive `*EL FILE S, E`
    per tutti; qui si verifica che il solutore lo onori per tutti e dieci.
    """
    eseguibile = _ccx_o_salta()
    percorso, _nodi, _tets, casi = deck_a_molti_passi(tmp_path)

    esito = subprocess.run(
        [eseguibile, "-i", percorso.stem],
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]

    blocchi = solve.leggi_frd(percorso.with_suffix(".frd"))
    con_tensione = sorted({b.passo for b in blocchi if b.grandezza == "STRESS"})

    assert con_tensione == list(range(1, len(casi))), (
        f"passi con STRESS {con_tensione}: senza un blocco per ogni passo statico "
        "il verdetto sul picco segnalerebbe casi mancanti su una corsa sana"
    )
