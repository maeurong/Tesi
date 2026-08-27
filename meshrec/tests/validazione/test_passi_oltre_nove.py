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

**Cosa ha detto il solutore vero**, al primo giro di questo file in CI
(corsa 33088412242, 27/08/2026). Il deck ha dieci passi statici e **un**
`*STEP, *FREQUENCY` con due modi, ma nel `.frd` i passi letti sono **dodici**:

- i dieci statici escono numerati 1..10, il decimo compreso -- che e' il
  riscontro che #94 cercava, e in locale non era ottenibile;
- il passo modale non e' uno: `ccx` numera **un passo per modo**, quindi 11 e
  12. Il deck ne dichiara uno, il file ne porta due;
- i passi 11 e 12 portano **anche un blocco STRESS**, benche' il passo modale
  del deck non chieda `*EL FILE` (`abaqus.write_inp`, ramo modale, lo dice a
  chiare lettere). E' la stessa non-cancellazione che il docstring di
  `core/solve.py` documenta gia' per `*NODE PRINT, RF` nel `.dat`: una
  richiesta di stampa fatta in un passo statico resta attiva nei passi
  successivi, che non la cancellano. La tensione calcolata su una forma
  normalizzata sulla massa e' quella dei "fino a 88,5 MPa privi di
  significato" gia' misurati li'.

Nulla di tutto questo tocca `risolvi()`, che scarta ogni blocco modale che non
sia `DISP` prima di guardare il numero di passo: erano le attese di questo
file a essere ingenue, non il codice. Le asserzioni qui sotto sono riscritte
sul misurato, e quella sui blocchi STRESS modali esiste apposta per inchiodare
il fatto invece di lasciarlo a memoria.
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
# del limite che una cifra sola sa scrivere, cosi' il passo 10 e i due modali
# (11 e 12) cadono tutti oltre.
N_POSIZIONATI = 9
N_STATICI = 1 + N_POSIZIONATI

# `ccx` scrive un passo del `.frd` per **ogni modo**, non uno per la card
# `*FREQUENCY`: con due modi i passi modali sono due, misurato in CI.
MODI = 2
PASSI_MODALI = list(range(N_STATICI + 1, N_STATICI + 1 + MODI))


def deck_a_molti_passi(tmp_path, nome: str = "molti_passi"):
    """Un deck con dieci passi statici piu' una card modale a due modi.

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
        carichi=CarichiConfig(posizionati=posizionati, modale=Modale(modi=MODI)),
        nset_selettori={"CIMA": cima},
    )
    casi = ["GRAVITA"] + [c.nome for c in posizionati] + ["MODALE"]
    return percorso, nodi, tets, casi


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _blocchi_della_corsa(tmp_path):
    eseguibile = _ccx_o_salta()
    percorso, _nodi, _tets, _casi = deck_a_molti_passi(tmp_path)

    esito = subprocess.run(
        [eseguibile, "-i", percorso.stem],
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
    )
    assert esito.returncode == 0, esito.stdout[-2000:] + esito.stderr[-2000:]

    return solve.leggi_frd(percorso.with_suffix(".frd"))


def test_il_passo_dieci_e_oltre_si_legge_intero_dal_frd_vero(tmp_path):
    """I dieci passi statici escono numerati 1..10, il decimo compreso.

    E' il riscontro che #94 cercava: senza `ccx` non era ottenibile in locale,
    perche' il solo record misurato aveva il passo a una cifra e restava
    indeciso da quale lato il campo cresca oltre il nono.

    Mutazione che lo uccide: rileggere il passo da una colonna sola
    (`_COL_CODA` -> `slice(62, 63)`), che e' il difetto di #94. Il decimo
    passo tornerebbe `1` e i suoi risultati finirebbero sul primo caso di
    carico, in silenzio.
    """
    blocchi = _blocchi_della_corsa(tmp_path)
    statici = sorted({b.passo for b in blocchi if not b.modale})

    assert statici == list(range(1, N_STATICI + 1)), (
        f"passi statici letti {statici}: il deck ne scrive {N_STATICI}, numerati "
        "da 1. Un passo oltre il nono letto come una cifra sola finisce sul caso "
        "di carico sbagliato"
    )


def test_ccx_numera_un_passo_per_modo_e_non_uno_per_la_card_frequency(tmp_path):
    """Il deck dichiara **una** card `*FREQUENCY` a due modi; il `.frd` porta
    **due** passi modali, 11 e 12.

    Misurato in CI al primo giro, non previsto: e' la ragione per cui l'attesa
    precedente (`{11}`) era sbagliata. Il conteggio si lega a `MODI` e non a
    una coppia scritta a mano, cosi' cambiare il numero di modi non richiede
    di riscrivere l'attesa a occhio.

    Nessuna conseguenza su `risolvi()`, che conta i modi dai blocchi `DISP`
    modali e non dal numero di passo -- ma il fatto va inchiodato, perche' chi
    legge il deck si aspetta un passo modale solo.
    """
    blocchi = _blocchi_della_corsa(tmp_path)
    forme = [b for b in blocchi if b.modale and b.grandezza == "DISP"]
    modali = sorted({b.passo for b in blocchi if b.modale})

    assert len(forme) == MODI, f"{len(forme)} forme modali lette, attese {MODI}"
    assert modali == PASSI_MODALI, (
        f"passi modali letti {modali}, attesi {PASSI_MODALI}: uno per modo, "
        f"numerati di seguito ai {N_STATICI} statici"
    )


def test_ogni_passo_statico_porta_un_blocco_di_tensione(tmp_path):
    """L'altra meta' di #92: il verdetto sul picco si aggrega sui casi che il
    deck dichiara, e quella scelta vale solo se ogni passo statico produce
    davvero un blocco STRESS. `abaqus._passo_statico` scrive `*EL FILE S, E`
    per tutti; qui si verifica che il solutore lo onori per tutti e dieci.

    Mutazione che lo uccide: togliere `*EL FILE` da `_passo_statico`. Il
    verdetto sul picco segnalerebbe allora casi mancanti su una corsa sana.
    """
    blocchi = _blocchi_della_corsa(tmp_path)
    statici_con_tensione = sorted(
        {b.passo for b in blocchi if b.grandezza == "STRESS" and not b.modale}
    )

    assert statici_con_tensione == list(range(1, N_STATICI + 1)), (
        f"passi statici con STRESS {statici_con_tensione}: ne servono {N_STATICI}, "
        "uno per caso dichiarato, o `casi_mancanti` accusa una corsa sana"
    )


def test_anche_i_passi_modali_portano_tensioni_che_nessuno_ha_chiesto(tmp_path):
    """Il passo modale del deck **non** chiede `*EL FILE` -- e `ccx` scrive le
    tensioni lo stesso, per tutti e due i modi.

    Non e' una stranezza isolata: e' la non-cancellazione che il docstring di
    `core/solve.py` documenta gia' per `*NODE PRINT, RF` nel `.dat`, dove una
    richiesta di stampa fatta in un passo statico resta attiva nei passi
    successivi. Qui la stessa cosa sul `.frd`, e la tensione calcolata su una
    forma normalizzata sulla massa e' quella dei «fino a 88,5 MPa privi di
    significato» gia' misurati.

    Il test esiste per due ragioni. Inchioda il fatto che ha fatto cadere la
    prima stesura di questo file, e sorveglia la sola difesa che c'e': il
    flag `modale`. Mutazione che lo uccide: `risolvi()` che smette di scartare
    i blocchi modali diversi da `DISP` -- quelle tensioni entrerebbero nel
    `.vtu` e nel verdetto sul picco come se fossero MPa.
    """
    blocchi = _blocchi_della_corsa(tmp_path)
    modali_con_tensione = sorted(
        {b.passo for b in blocchi if b.grandezza == "STRESS" and b.modale}
    )

    assert modali_con_tensione == PASSI_MODALI, (
        f"passi modali con STRESS {modali_con_tensione}, attesi {PASSI_MODALI}. "
        "Se `ccx` smettesse di scriverli, il flag `modale` avrebbe un motivo in "
        "meno di esistere e questo file lo direbbe invece di tacerlo"
    )
    assert all(
        b.modale for b in blocchi if b.grandezza == "STRESS" and b.passo in PASSI_MODALI
    ), "una tensione modale non marcata `modale` esce da `leggi_frd` come se fossero MPa"
