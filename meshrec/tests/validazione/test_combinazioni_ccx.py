"""Un deck con combinazioni di carico, dato a `ccx` vero.

Ticket https://github.com/maeurong/Tesi/issues/146.

`abaqus.write_inp` scrive un passo per combinazione, e dentro quel passo
**piu' azioni insieme** -- una `*DLOAD, GRAV` per la gravita' e una `*CLOAD`
per le forze nodali, ciascuna moltiplicata per il proprio coefficiente. E' la
prima volta che due azioni dichiarate condividono uno `*STEP`, e nessun test
di solo testo puo' dire se il solutore le sommi davvero: un deck che non gira
non e' un deck.

**Che cosa questo file misura, che il testo non puo'.**

1. Il deck con combinazioni **gira**, con zero errori e zero avvisi. Gli avvisi
   contano: `controlla_avvisi` e' uno dei sette verdetti, e due avvisi per
   passo lo degraderebbero su ogni corsa con combinazioni.
2. Ogni passo -- singoli e combinazioni -- produce il **proprio** blocco nel
   `.frd`, cioe' il proprio campo. Un passo che non producesse blocchi
   sposterebbe la numerazione e `risolvi` attribuirebbe i risultati al caso
   sbagliato, in silenzio.
3. **La combinazione somma davvero.** La combinazione qui sotto porta la sola
   gravita' con coefficiente 2,0, e il solutore deve renderne spostamenti
   doppi di quelli del passo di peso proprio: e' un oracolo in forma chiusa
   (il problema e' lineare) che nessuna lettura del deck fornisce. Un
   coefficiente applicato alla colonna sbagliata darebbe un numero plausibile
   e diverso da due.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import (
    CarichiConfig,
    CaricoSommita,
    Combinazione,
    Material,
    SpintaOrizzontale,
)

pytestmark = pytest.mark.validazione

LATO = (60.0, 60.0, 120.0)
MATERIALE = Material(name="PROVA", young=30000.0, poisson=0.2, density=2.4e-9)

# Il fattore della combinazione di controllo: la sola gravita' moltiplicata per
# due. Scelto cosi' perche' l'oracolo e' esatto -- il problema e' lineare -- e
# non richiede di conoscere alcun risultato in anticipo.
FATTORE = 2.0

# Il confronto non pretende piu' precisione di quanta il canale di misura ne
# abbia. Il `.frd` scrive ogni componente in un campo di **12 caratteri** in
# notazione scientifica (`solve.leggi_frd`, `linea[13 + 12*i : 25 + 12*i]`),
# cioe' sei cifre significative: un'unita' sull'ultima vale 1e-5 in relativo.
# Il doppio di un numero arrotondato e il numero doppio arrotondato non
# coincidono per costruzione. Misurato su questo provino con `ccx` 2.21 il
# 30/08/2026: scarto relativo massimo 3,9e-6, sotto la risoluzione del campo.
# Stessa forma della soglia `patch_test_fattore_sul_pavimento` di
# `core/soglie.py`, e per la stessa ragione: chiedere 1e-12 qui misurerebbe la
# quantizzazione del file, non la somma delle azioni.
TOLLERANZA_FRD = 1e-5

CASI = [
    "GRAVITA",
    "SPINTA_ORIZZONTALE",
    "CARICO_TOP",
    "PESO_DOPPIO",
    "SLU_FOND",
]


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


@pytest.fixture(scope="module")
def corsa(tmp_path_factory):
    """Una sola corsa di `ccx` su un deck con due combinazioni.

    Rende `(uscita_del_solutore, blocchi_del_frd, nodi)`. A corsa per test
    sarebbero tre tetraedrizzazioni e tre corse dello stesso deck.
    """
    eseguibile = _ccx_o_salta()
    tmp_path = tmp_path_factory.mktemp("combinazioni_ccx")

    vertici, facce = synth.box_mesh(LATO)
    nodi, tets = volume.tetrahedralize(
        vertici, facce,
        max_volume=6000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=1,
    )
    base = np.flatnonzero(nodi[:, 2] < 1e-9)
    cima = np.flatnonzero(nodi[:, 2] > LATO[2] - 1e-9)
    assert len(base) and len(cima), "il provino deve avere una base e una cima"

    carichi = CarichiConfig(
        spinta=SpintaOrizzontale(coefficiente=0.1, asse="y", natura="variabile"),
        carico_sommita=CaricoSommita(
            risultante=1000.0, nset="TOP", natura="variabile"
        ),
        combinazioni=(
            # Il solo peso proprio raddoppiato: l'oracolo in forma chiusa.
            Combinazione(
                nome="PESO_DOPPIO", tipo="slu_fondamentale",
                termini=(("GRAVITA", FATTORE),), proposta=False,
            ),
            # Tre azioni in un passo solo, coi coefficienti della Tab. 2.6.I:
            # e' la forma che #146 chiede, e serve a far girare il caso vero.
            Combinazione(
                nome="SLU_FOND", tipo="slu_fondamentale",
                termini=(
                    ("GRAVITA", 1.3),
                    ("SPINTA_ORIZZONTALE", 1.5),
                    ("CARICO_TOP", 1.5 * 0.7),
                ),
                proposta=True,
            ),
        ),
    )

    percorso = tmp_path / "combinazioni.inp"
    abaqus.write_inp(
        percorso, nodi, tets,
        material=MATERIALE, element_type="C3D4",
        node_sets={"BASE": base, "TOP": cima},
        fixed_nset="BASE",
        carichi=carichi,
    )

    esito = subprocess.run(
        [eseguibile, "-i", percorso.stem],
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
    )
    uscita = esito.stdout + esito.stderr
    assert esito.returncode == 0, uscita[-2000:]
    return uscita, solve.leggi_frd(percorso.with_suffix(".frd")), nodi


def test_il_deck_con_combinazioni_gira_senza_errori_e_senza_avvisi(corsa):
    """Zero avvisi non e' pedanteria: `controlla_avvisi` e' uno dei sette
    verdetti, e un avviso per passo lo degraderebbe su ogni corsa con
    combinazioni.

    Mutazione che lo uccide: scrivere `*DSLOAD, OP=NEW` nel passo di
    combinazione, che `ccx` non riconosce su quella card (#84).
    """
    uscita, _blocchi, _nodi = corsa
    assert "Job finished" in uscita, uscita[-2000:]
    assert uscita.upper().count("*ERROR") == 0, uscita[-2000:]
    assert uscita.upper().count("*WARNING") == 0, uscita[-2000:]


def test_ogni_passo_produce_il_proprio_campo(corsa):
    """Cinque passi nel deck, cinque passi nel `.frd`, ciascuno con
    spostamenti e tensioni.

    Un passo che non producesse blocchi sposterebbe la numerazione, e
    `risolvi` attribuirebbe i risultati al caso sbagliato senza un errore.
    """
    _uscita, blocchi, _nodi = corsa
    statici = sorted({b.passo for b in blocchi if not b.modale})
    assert statici == list(range(1, len(CASI) + 1)), statici
    for passo in statici:
        grandezze = {b.grandezza for b in blocchi if b.passo == passo}
        assert {"DISP", "STRESS"} <= grandezze, (passo, grandezze)


def test_la_combinazione_somma_le_azioni_col_proprio_coefficiente(corsa):
    """Il peso proprio moltiplicato per due da' spostamenti doppi.

    Oracolo in forma chiusa e non un numero copiato da una corsa: il problema
    e' lineare, quindi il rapporto vale esattamente `FATTORE` qualunque sia il
    maglio. Un coefficiente applicato alla colonna sbagliata della riga `GRAV`
    -- alla componente `nz` invece che al modulo -- darebbe un rapporto
    diverso da due, e nessuna lettura del deck lo direbbe.
    """
    _uscita, blocchi, _nodi = corsa
    etichetta = dict(enumerate(CASI, start=1))
    spostamenti = {
        etichetta[b.passo]: b.dati
        for b in blocchi
        if not b.modale and b.grandezza == "DISP" and b.passo in etichetta
    }

    peso = np.linalg.norm(spostamenti["GRAVITA"], axis=1)
    doppio = np.linalg.norm(spostamenti["PESO_DOPPIO"], axis=1)
    assert peso.max() > 0.0, "il passo di peso proprio non ha spostato nulla"
    np.testing.assert_allclose(doppio, FATTORE * peso, rtol=TOLLERANZA_FRD, atol=0.0)
