"""Test di `meshrec.core.solve`: lettura del `.frd` e del `.dat`.

Le fixture `.frd` sotto sono quelle del brief del Task 5 (Fase 5), scritte a
mano dall'architect per riprodurre le due trappole di formato. Le fixture
`.dat` invece sono misurate da questa sessione (21/08/2026), eseguendo `ccx`
2.22 su un deck di prova ad hoc in `/tmp/ccx_probe` -- non `lab_telaio_v2`,
che nessun task fino al 6 ha ancora prodotto: un cubo di otto nodi, un passo
statico con carico e un passo modale successivo, proprio per catturare la
contaminazione delle reazioni descritta nel modulo.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest

from meshrec.core import abaqus, quality, solve, synth, volume
from meshrec.core.config import CaricoSommita, CarichiConfig, Modale, SpintaOrizzontale
from materiale import ANALISI, MATERIALE

# Tre blocchi apposta, non due: il brief ne dava due monotoni (passo 1, poi
# passo 2), e un contatore incrementale per record `100CL` ci azzecca lo
# stesso per puro caso di ordine. Qui il passo 1 porta DUE blocchi (DISP e
# STRESS, come succede davvero quando un passo statico chiede sia
# spostamenti che tensioni): un contatore darebbe [1, 2, 3], la lettura dal
# file da [1, 1, 2]. Misurato oggi che ccx ripete il record 100CL una volta
# per blocco di uscita, anche entro lo stesso passo fisico (`ccx` 2.22,
# `/tmp/ccx_probe/probe2.frd`).
FRD_TRE_BLOCCHI = """\
    1PSTEP                         1           1           1
  100CL  101 1.000000000           2                     0    1           1
 -4  DISP        4    1
 -1         1 1.00000E+00 2.00000E+00 3.00000E+00
 -1         2 4.00000E+00 5.00000E+00 6.00000E+00
 -3
    1PSTEP                         1           1           1
  100CL  101 1.000000000           2                     0    1           1
 -4  STRESS      6    1
 -1         1 1.00000E+01 2.00000E+01 3.00000E+01 4.00000E+01 5.00000E+01 6.00000E+01
 -3
    1PSTEP                         2           1           2
  100CL  102 21.19324067           2                     2    2MODAL      1
 -4  DISP        4    1
 -1         1 7.00000E+00 8.00000E+00 9.00000E+00
 -1         2 1.00000E+01 1.10000E+01 1.20000E+01
 -3
"""


def test_il_passo_si_legge_dal_file_e_non_dalla_posizione(tmp_path):
    """Contare i blocchi in ordine cade appena due blocchi condividono un passo.

    Il record 100CL porta il numero di passo, e nei blocchi modali porta la
    frequenza al posto del tempo. Sul deck del telaio i blocchi DISP sono nove
    per quattro passi: tre statici piu' sei modi (misurato 21/08/2026).
    """
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_TRE_BLOCCHI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert [b.passo for b in blocchi] == [1, 1, 2]
    assert [b.modale for b in blocchi] == [False, False, True]
    assert blocchi[2].valore == pytest.approx(21.19324067)


def test_il_marchio_modale_sopravvive_all_incollamento(tmp_path):
    """Nel record modale il passo e il tipo escono incollati: `2MODAL`.

    Un `split()` legge un token solo e l'attribuzione salta in silenzio. La
    lettura e' a colonne fisse.
    """
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_TRE_BLOCCHI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert blocchi[2].passo == 2, "il passo e' stato letto insieme alla parola MODAL"


def test_i_blocchi_modali_portano_forme_e_non_spostamenti(tmp_path):
    """Un blocco modale non e' un caso di carico e non deve poter fingere di esserlo."""
    percorso = tmp_path / "prova.frd"
    percorso.write_text(FRD_TRE_BLOCCHI, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert not blocchi[0].modale
    assert not blocchi[1].modale
    assert blocchi[2].modale


def test_von_mises_di_uno_stato_di_taglio_puro():
    """Taglio puro tau: la von Mises vale tau*sqrt(3), forma chiusa."""
    tensioni = np.array([[0.0, 0.0, 0.0, 5.0, 0.0, 0.0]])

    assert solve.von_mises(tensioni)[0] == pytest.approx(5.0 * math.sqrt(3.0))


def test_von_mises_di_una_trazione_monoassiale():
    """Trazione sigma su un asse solo: la von Mises vale sigma."""
    tensioni = np.array([[7.0, 0.0, 0.0, 0.0, 0.0, 0.0]])

    assert solve.von_mises(tensioni)[0] == pytest.approx(7.0)


# Misurato oggi (vedi docstring del modulo): un passo statico con RF
# richiesta su BASE, seguito da un passo modale che non la richiede ne' la
# cancella. ccx la ristampa comunque per ciascun modo, con numeri all'ordine
# dei milioni di N.
DAT_REAZIONI_CONTAMINATO = """\

                        S T E P       1


                                INCREMENT     1


 forces (fx,fy,fz) for set BASE and time  0.1000000E+01

         1 -1.000000E+03 -1.108911E+02 -2.000000E+03
         2 -1.000000E+03  1.108911E+02  2.000000E+03
         3 -1.000000E+03 -1.108911E+02  2.000000E+03
         4 -1.000000E+03  1.108911E+02 -2.000000E+03

                        S T E P       2


     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00

                    E I G E N V A L U E    N U M B E R     1


 forces (fx,fy,fz) for set BASE and time  0.2000000E+01

         1  3.606172E+06  4.669528E+06  1.590494E+07
         2  2.524231E+06  3.895093E+06  2.634639E+06
         3  3.606172E+06  4.669528E+06 -1.590494E+07
         4  2.524231E+06  3.895093E+06 -2.634639E+06
"""


def test_le_reazioni_si_fermano_al_passo_statico_e_non_prendono_il_modo(tmp_path):
    """Il passo modale non cancella la richiesta RF del passo statico: ccx la
    ristampa per ciascun modo, con numeri all'ordine dei milioni di N che non
    sono reazioni. Un lettore che scorra tutto il file e tenga l'ultimo
    blocco a quattro campi (come fa `ccx_utils` per gli spostamenti) li
    prenderebbe per buoni.
    """
    percorso = tmp_path / "prova.dat"
    percorso.write_text(DAT_REAZIONI_CONTAMINATO, encoding="ascii")

    reazioni = solve.leggi_reazioni(percorso)

    assert reazioni[1] == pytest.approx((-1000.0, -110.8911, -2000.0))
    assert reazioni.keys() == {1, 2, 3, 4}


DAT_FREQUENZE = """\
     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00
      2   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00
      3   0.1500000E+10   0.3872983E+05   0.6164044E+04   0.0000000E+00
      4   0.3663609E+10   0.6052775E+05   0.9633291E+04   0.0000000E+00

     P A R T I C I P A T I O N   F A C T O R S
"""


def test_le_frequenze_sono_la_colonna_cycles_time_non_la_prima_dopo_il_modo(tmp_path):
    """La colonna CYCLES/TIME e' la terza dopo il numero di modo, non la
    prima: l'autovalore e la componente RAD/TIME la precedono.
    """
    percorso = tmp_path / "prova.dat"
    percorso.write_text(DAT_FREQUENZE, encoding="ascii")

    frequenze = solve.leggi_frequenze(percorso)

    assert frequenze == pytest.approx([4384.661, 4384.661, 6164.044, 9633.291])


def test_senza_ccx_lo_step_dichiara_l_assenza_e_non_fallisce(tmp_path, monkeypatch):
    """Un esito negativo documentato non e' un fallimento.

    PRODUCT.md dichiara utenti successivi confermati, che non avranno
    necessariamente CalculiX. Senza solutore non c'e' analisi, e il programma lo
    dice invece di rompersi o di inventare un ripiego.
    """
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))

    esito = solve.risolvi(
        tmp_path, tmp_path / "assente.inp", ANALISI, nodi, elementi, "C3D4",
        casi_di_carico=["GRAVITA"], vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0},
        trasformata=np.eye(4),
    )

    assert esito == {"eseguito": False, "solutore": "assente"}
    assert not (tmp_path / "13_solution.vtu").exists()


def test_risolvi_rifiuta_casi_di_carico_vuoto(tmp_path, monkeypatch):
    """Un deck senza casi non e' uno stato da rappresentare con `None`
    (giro di correzione della revisione): e' un errore del chiamante, e
    `risolvi` lo dice esplicitamente invece di eseguire a vuoto -- prima
    della correzione, `[nome for nome in (None or ()) if nome != "MODALE"]`
    dava `[]` in silenzio e scartava ogni blocco statico letto dal `.frd`.
    """
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    nodi, elementi = synth.box_mesh((100.0, 100.0, 100.0))

    with pytest.raises(ValueError, match="casi_di_carico"):
        solve.risolvi(
            tmp_path, tmp_path / "assente.inp", ANALISI, nodi, elementi, "C3D4",
            casi_di_carico=[], vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0},
            trasformata=np.eye(4),
        )


# Deck sintetico a quattro nodi, tre passi statici (GRAVITA, SPINTA_ORIZZONTALE,
# CARICO_TOP) e un passo modale a due modi: costruito a mano con lo stesso
# schema di FRD_TRE_BLOCCHI, non misurato su ccx vero. Le tensioni sono
# trazione monoassiale pura (sigma, 0,0,0,0,0): la von Mises esce esattamente
# sigma (stessa forma di test_von_mises_di_una_trazione_monoassiale), quindi
# ogni passo ha un vm_max esatto e distinto (1, 5, 90) da cui riconoscere se
# un'etichetta e' finita sul passo sbagliato.
FRD_QUATTRO_PASSI = """  100CL  101 1.000000000           2                     0    1           1
 -4  DISP        4    1
 -1         1 1.00000E-02 0.00000E+00-1.00000E-02
 -1         2 2.00000E-02 0.00000E+00-2.00000E-02
 -1         3 3.00000E-02 0.00000E+00-3.00000E-02
 -1         4 4.00000E-02 0.00000E+00-4.00000E-02
 -3
  100CL  101 1.000000000           2                     0    1           1
 -4  STRESS      6    1
 -1         1 1.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         3 1.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         4 1.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -3
  100CL  101 1.000000000           2                     0    2           1
 -4  DISP        4    1
 -1         1 5.00000E-02 0.00000E+00-5.00000E-02
 -1         2 1.00000E-01 0.00000E+00-1.00000E-01
 -1         3 1.50000E-01 0.00000E+00-1.50000E-01
 -1         4 2.00000E-01 0.00000E+00-2.00000E-01
 -3
  100CL  101 1.000000000           2                     0    2           1
 -4  STRESS      6    1
 -1         1 5.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 5.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         3 5.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         4 5.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -3
  100CL  101 1.000000000           2                     0    3           1
 -4  DISP        4    1
 -1         1 9.00000E-01 0.00000E+00-9.00000E-01
 -1         2 1.80000E+00 0.00000E+00-1.80000E+00
 -1         3 2.70000E+00 0.00000E+00-2.70000E+00
 -1         4 3.60000E+00 0.00000E+00-3.60000E+00
 -3
  100CL  101 1.000000000           2                     0    3           1
 -4  STRESS      6    1
 -1         1 9.00000E+01 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 9.00000E+01 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         3 9.00000E+01 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         4 9.00000E+01 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -3
  100CL  101 21.19324067           2                     0    4MODAL      1
 -4  DISP        4    1
 -1         1 1.00000E-02 0.00000E+00-1.00000E-02
 -1         2 2.00000E-02 0.00000E+00-2.00000E-02
 -1         3 3.00000E-02 0.00000E+00-3.00000E-02
 -1         4 4.00000E-02 0.00000E+00-4.00000E-02
 -3
  100CL  101 33.00000000           2                     0    4MODAL      1
 -4  DISP        4    1
 -1         1 2.00000E-02 0.00000E+00-2.00000E-02
 -1         2 4.00000E-02 0.00000E+00-4.00000E-02
 -1         3 6.00000E-02 0.00000E+00-6.00000E-02
 -1         4 8.00000E-02 0.00000E+00-8.00000E-02
 -3
"""

DAT_DUE_MODI = """     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00
      2   0.1500000E+10   0.3872983E+05   0.6164044E+04   0.0000000E+00

     P A R T I C I P A T I O N   F A C T O R S
"""


def test_risolvi_con_ccx_simulato_assembla_i_campi_e_conta_gli_avvisi(tmp_path, monkeypatch):
    """Important 1 della revisione: prima di questo test, tutto `risolvi()`
    oltre al ramo "solutore assente" -- la chiamata, la copia degli
    artefatti, l'assemblaggio di point_data, il conteggio di avvisi ed
    errori -- girava solo nel test di fattibilita' gated su `ccx` vero, quindi
    zero volte su una macchina senza CalculiX (esattamente il caso che
    PRODUCT.md dichiara).

    `ccx` e' sostituito da un `subprocess.run` finto: nessun processo parte
    davvero, e il `.frd`/`.dat` che il finto processo "avrebbe scritto" sono
    gia' su disco quando `risolvi()` li legge -- stesso principio del
    `_fake_run` di test_sweep.py.

    Dal giro di correzione seguente, `risolvi()` non deriva piu' l'ordine dei
    casi in proprio (era `solve._casi_statici`, una seconda copia della stessa
    logica di `abaqus.export_model`): lo riceve gia' fatto in
    `casi_di_carico`, cosi' come `pipeline.run` lo legge da
    `metrics["11_export"]["casi_di_carico"]`. Qui e' passato a mano, nello
    stesso ordine che quella lista avrebbe per questi carichi -- il confronto
    con l'ordine *vero* scritto da `write_inp` e' l'altro test qui sotto.
    """
    casi_di_carico = ["GRAVITA", "SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"]
    deck = tmp_path / "wall_model.inp"
    deck.write_text("*HEADING\n", encoding="ascii")
    deck.with_suffix(".frd").write_text(FRD_QUATTRO_PASSI, encoding="ascii")
    deck.with_suffix(".dat").write_text(DAT_DUE_MODI, encoding="ascii")

    import subprocess

    def ccx_finto(comando, **kwargs):
        return subprocess.CompletedProcess(
            comando, returncode=0,
            stdout=(
                "CalculiX finto per il test\n"
                "*WARNING in nmatrix: nodo isolato\n"
                "*WARNING in nmatrix: un altro nodo isolato\n"
                "Job finished\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(solve.subprocess, "run", ccx_finto)

    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    elementi = np.array([[0, 1, 2, 3]])

    esito = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0}, trasformata=np.eye(4),
    )

    assert esito["eseguito"] is True
    assert esito["returncode"] == 0
    assert esito["avvisi"] == 2
    assert esito["errori"] == 0
    assert esito["modi"] == 2
    assert esito["frequenze_hz"] == pytest.approx([4384.661, 6164.044])
    assert esito["casi"]["GRAVITA"]["vm_max"] == pytest.approx(1.0)
    assert esito["casi"]["SPINTA_ORIZZONTALE"]["vm_max"] == pytest.approx(5.0)
    assert esito["casi"]["CARICO_TOP"]["vm_max"] == pytest.approx(90.0)
    assert (tmp_path / "13_solver.log").exists()

    meshio = pytest.importorskip("meshio")
    mesh = meshio.read(tmp_path / "13_solution.vtu")
    assert set(mesh.point_data) == {
        "U_GRAVITA", "VM_GRAVITA",
        "U_SPINTA_ORIZZONTALE", "VM_SPINTA_ORIZZONTALE",
        "U_CARICO_TOP", "VM_CARICO_TOP",
        "MODO_1", "MODO_2",
    }


def test_il_controllo_sul_vincolo_in_pianta_usa_la_soglia_di_produzione(tmp_path, monkeypatch):
    """Aggancio del controllo `vincolo_in_pianta` a `risolvi()`: il caso
    sintetico a un piede (misurato 0,32 allo Step 7 del Task 2) deve fallire
    contro la soglia di produzione `_SOGLIA_VINCOLO_IN_PIANTA` (0,5); il caso
    lab_crop (0,987) deve passare. Nessun test esistente asserisce sul
    verdetto di questo controllo -- solo sulla sua presenza nel dizionario --
    quindi la mutazione dello Step 3 del giro di correzione non aveva nulla
    da uccidere prima di questo test.
    """
    casi_di_carico = ["GRAVITA", "SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"]
    deck = tmp_path / "wall_model.inp"
    deck.write_text("*HEADING\n", encoding="ascii")

    import subprocess

    def ccx_finto(comando, **kwargs):
        # Le uscite le scrive il processo finto e non il preambolo del test,
        # perche' `risolvi` le **rinomina** invece di copiarle (I4 della
        # revisione finale): la seconda corsa qui sotto le ritrova solo se
        # `ccx` le riscrive, che e' esattamente cio' che fa quello vero.
        deck.with_suffix(".frd").write_text(FRD_QUATTRO_PASSI, encoding="ascii")
        deck.with_suffix(".dat").write_text(DAT_DUE_MODI, encoding="ascii")
        return subprocess.CompletedProcess(comando, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(solve.subprocess, "run", ccx_finto)

    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    elementi = np.array([[0, 1, 2, 3]])

    un_piede = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 0.32, "minimo": 0.32}, trasformata=np.eye(4),
    )
    assert not un_piede["controlli"]["vincolo_in_pianta"]["passato"], "0,32 e' sotto 0,5: non citabile"

    lab_crop = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 0.987, "minimo": 0.987}, trasformata=np.eye(4),
    )
    assert lab_crop["controlli"]["vincolo_in_pianta"]["passato"]


def test_risolvi_porta_il_sesto_verdetto_col_rapporto_calcolabile_a_mano(tmp_path, monkeypatch):
    """Aggancio di `controlla_spostamenti` a `risolvi()` (#12).

    I test del reperto (tests/validazione/test_modello_mal_vincolato.py)
    chiamano la funzione **direttamente**: senza questo, il verdetto potrebbe
    non essere mai stato messo nel dizionario e quei test passerebbero lo
    stesso. L'oracolo e' aritmetica sul `.frd` finto, non un numero
    registrato: il piu' grande spostamento statico e' quello del nodo 4 al
    passo 3, `(3,6; 0; -3,6)`, che vale `3,6*sqrt(2)`; i quattro nodi sono il
    tetraedro unitario, quindi la diagonale del contenitore e' `sqrt(3)`.
    """
    casi_di_carico = ["GRAVITA", "SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE"]
    deck = tmp_path / "wall_model.inp"
    deck.write_text("*HEADING\n", encoding="ascii")

    import subprocess

    def ccx_finto(comando, **kwargs):
        deck.with_suffix(".frd").write_text(FRD_QUATTRO_PASSI, encoding="ascii")
        deck.with_suffix(".dat").write_text(DAT_DUE_MODI, encoding="ascii")
        return subprocess.CompletedProcess(comando, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(solve.subprocess, "run", ccx_finto)

    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    esito = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, np.array([[0, 1, 2, 3]]), "C3D4",
        casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0}, trasformata=np.eye(4),
    )

    spostamenti = esito["controlli"]["spostamenti"]
    assert spostamenti["u_max"] == pytest.approx(3.6 * math.sqrt(2.0))
    assert spostamenti["dimensione"] == pytest.approx(math.sqrt(3.0))
    assert spostamenti["rapporto"] == pytest.approx(3.6 * math.sqrt(2.0) / math.sqrt(3.0))
    # 2,94 supera 1: su questo provino il verdetto e' negativo, ed e' giusto
    # -- sono spostamenti quasi tre volte il modello.
    assert spostamenti["passato"] is False


def test_casi_di_carico_segue_l_ordine_vero_scritto_da_write_inp(tmp_path):
    """L'origine e' una sola: `casi_di_carico`, il campo che `export_model`
    restituisce e che `solve.risolvi` legge senza ri-derivarlo (giro di
    correzione della revisione, sostituisce `solve._casi_statici`). Ma
    `export_model` lo costruisce con una propria lista letterale, separata
    dai rami `if carichi.spinta is not None: ...` che `write_inp` esegue
    davvero -- due punti nello stesso file che devono restare d'accordo.

    Qui l'ordine vero non e' assunto: e' letto dal testo che `write_inp`
    scrive davvero (le righe `** NOME PASSO: ...`, comprese nello stesso
    deck che `export_model` produce), e quello e' l'oracolo contro cui si
    confronta `casi_di_carico`. Nessun `ccx` necessario: e' solo testo.

    `set_tolerance_factor` ridotto: col predefinito `TOP` e `BASE`
    collassano nello stesso insieme su questo cubo sintetico, e la
    guardia carico-sul-vincolo (punto 1, Task 15) rifiuterebbe il
    CARICO_TOP che qui non c'entra con l'ordine dei passi.
    """
    from meshrec.core.config import AnalysisConfig, TetConfig

    vertices, faces = synth.box_mesh((100.0, 100.0, 100.0))
    nodi, elementi = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    carichi = CarichiConfig(
        spinta=SpintaOrizzontale(coefficiente=0.1, asse="x"),
        carico_sommita=CaricoSommita(risultante=1000.0, nset="TOP"),
        modale=Modale(modi=2),
    )
    analisi = AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)
    esito = abaqus.export_model(
        tmp_path / "prova.inp", tmp_path / "prova.vtu", nodi, elementi,
        # Maglio lineare, quindi elemento lineare dichiarato: il predefinito e'
        # C3D10 dal ripristino del quadratico (#45), e qui l'elemento non e' la
        # variabile sotto esame -- lo e' l'ordine dei passi nel deck.
        analisi, TetConfig(element="C3D4"), carichi=carichi,
    )

    testo = (tmp_path / "prova.inp").read_text(encoding="ascii")
    ordine_reale = [
        riga.split(": ", 1)[1]
        for riga in testo.splitlines()
        if riga.startswith("** NOME PASSO: ")
    ]

    assert esito["casi_di_carico"] == ordine_reale


# ---------------------------------------------------------------------------
# Task 7: i controlli che smentiscono. I tre test sotto sono quelli del
# brief, Step 1, verbatim -- l'oracolo e' l'esempio dato, non una misura di
# questa sessione.
# ---------------------------------------------------------------------------


def test_la_somma_delle_reazioni_smentisce_una_densita_sbagliata():
    """Somma delle reazioni contro rho*V*g, come vettore e non come modulo.

    Un modulo giusto con una direzione sbagliata passerebbe: e' esattamente il
    caso di un vincolo che tiene la struttura di sbieco.
    """
    reazioni = {1: (0.0, 0.0, 500.0), 2: (0.0, 0.0, 500.0)}

    esito = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 0.0, 1000.0), tolleranza=0.02)
    assert esito["passato"]

    storta = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 600.0, 800.0), tolleranza=0.02)
    assert not storta["passato"], "il modulo coincide, la direzione no"


def test_un_autovalore_vicino_a_zero_e_un_meccanismo():
    """Una frequenza quasi nulla significa che la struttura si muove libera."""
    assert solve.controlla_autovalori([21.19, 34.34, 43.14])["passato"]
    assert not solve.controlla_autovalori([0.0004, 21.19])["passato"]
    assert not solve.controlla_autovalori([])["passato"]


def test_il_picco_di_tensione_dentro_la_banda_di_vincolo_e_un_artefatto():
    """Il numero piu' citabile e' il piu' facile da fraintendere.

    Misurato il 21/08/2026 sull'as-built col vincolo corretto: sotto peso
    proprio il rapporto max/p99 vale 2,16 e nessuno dei 142 nodi sopra il p99
    cade entro la banda di vincolo -- il picco sta all'89% dell'altezza, non
    sull'incastro, e resta sullo stesso nodo in tutti e tre i casi di carico.
    Il controllo non e' che il picco sia basso: e' che si sappia dove sta.
    """
    quote = np.array([0.0, 10.0, 2000.0, 2100.0])
    valori = np.array([9.0, 1.0, 1.0, 1.0])

    esito = solve.controlla_picco(valori, quote, banda=100.0)

    assert esito["frazione_in_banda"] == pytest.approx(1.0)
    assert not esito["passato"]


# ---------------------------------------------------------------------------
# Ingressi degeneri (brief Task 7): ognuno con il proprio oracolo. Le righe
# gia' coperte dai test sopra (autovalori vuoto) non si ripetono.
# ---------------------------------------------------------------------------


def test_controlla_reazioni_con_dizionario_vuoto_non_solleva():
    """Nessuna reazione letta (es. `.dat` senza il passo richiesto): fallisce
    senza dividere per zero e senza sollevare."""
    esito = solve.controlla_reazioni({}, peso_atteso=(0.0, 0.0, 1000.0), tolleranza=0.02)
    assert esito["passato"] is False


def test_controlla_reazioni_rifiuta_peso_atteso_nullo():
    """Un peso atteso nullo (tutte le componenti a zero) non e' un caso da
    dividere: il modulo attero varrebbe zero e la frazione di scarto sarebbe
    indefinita."""
    reazioni = {1: (0.0, 0.0, 500.0)}
    esito = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 0.0, 0.0), tolleranza=0.02)
    assert esito["passato"] is False


def test_controlla_picco_su_tensioni_tutte_zero_non_produce_nan():
    """p99 nullo: il rapporto max/p99 non si calcola (0/0), si dichiara
    indefinito -- mai un nan silenzioso nel dizionario."""
    valori = np.zeros(4)
    quote = np.array([0.0, 10.0, 20.0, 30.0])

    esito = solve.controlla_picco(valori, quote, banda=100.0)

    assert esito["rapporto_max_p99"] is None
    assert not math.isnan(esito["frazione_in_banda"])


def test_controlla_picco_su_un_solo_nodo_non_solleva():
    """Un solo nodo: il percentile 99 e' quel nodo stesso, non un IndexError."""
    esito = solve.controlla_picco(np.array([5.0]), np.array([100.0]), banda=50.0)

    assert esito["max"] == pytest.approx(5.0)
    assert esito["rapporto_max_p99"] == pytest.approx(1.0)


def test_controlla_picco_con_nan_a_monte_riporta_il_valore_invece_di_nasconderlo():
    """Il cancello di finitezza (sotto, enumerato) forza `passato: False` su
    un NaN a monte in `valori`, ma non nasconde il dato: `max`/`p99` restano
    NaN nel dizionario -- si marca, non si nasconde, come per il resto della
    fase. Questo test copre solo la trasparenza; il verdetto e' verificato
    dall'enumerazione sotto.
    """
    valori = np.array([1.0, np.nan, 3.0, 4.0])
    quote = np.array([0.0, 10.0, 20.0, 30.0])

    esito = solve.controlla_picco(valori, quote, banda=100.0)

    assert esito["rapporto_max_p99"] is None
    assert math.isnan(esito["max"])




# ---------------------------------------------------------------------------
# Indagine 21/08/2026 (giro di correzione del Task 7): da dove viene lo
# scarto reazioni/peso di `_TOLLERANZA_REAZIONI`. Non era rumore di mesh:
# vedi il commento sopra `_TOLLERANZA_REAZIONI` in solve.py e il docstring
# di `_quota_tributaria_gravita`. Le prime due fixture/test sono presi cosi'
# come sono dal worktree del debugger (non riscritti); il terzo e' adattato
# per essere l'oracolo giusto dopo il fix, non restare rosso.
# ---------------------------------------------------------------------------


def test_i_tre_parser_del_dat_restano_chiamabili_col_solo_percorso(tmp_path):
    """La lettura condivisa di `risolvi` non ha spostato il contratto dei tre.

    `risolvi` legge il `.dat` una volta e passa le righe ai tre parser
    (`leggi_frequenze`, `leggi_massa_modale`, `leggi_reazioni`), invece di
    leggerlo per intero tre volte. Il percorso resta la via normale e resta
    obbligatorio: e' quella che usano i test e chiunque apra un `.dat` a
    mano, ed e' quella che nomina il file quando il file non c'e'.

    Le due meta' del caso degenere non sono la stessa cosa e il test le
    tiene distinte: un `.dat` **assente** solleva nominando il file, un
    `.dat` **vuoto** non solleva affatto -- rende zero frequenze, nessuna
    massa modale, nessuna reazione. Un file vuoto e' un risultato mancante,
    non un errore di lettura.
    """
    assente = tmp_path / "non_c_e.dat"
    for lettura in (solve.leggi_frequenze, solve.leggi_massa_modale, solve.leggi_reazioni):
        with pytest.raises(FileNotFoundError) as errore:
            lettura(assente)
        assert "non_c_e.dat" in str(errore.value)

    vuoto = tmp_path / "vuoto.dat"
    vuoto.write_text("", encoding="ascii")
    assert solve.leggi_frequenze(vuoto) == []
    assert solve.leggi_massa_modale(vuoto) is None
    assert solve.leggi_reazioni(vuoto) == {}


def test_le_righe_gia_lette_sostituiscono_davvero_la_lettura_del_file(tmp_path):
    """L'oracolo del parametro `righe`, che senza di questo non ne ha.

    Sostituire l'intero corpo di `_righe_dat` con la sola lettura dal
    percorso -- cioe' ignorare il parametro -- lasciava la suite verde:
    rileggere lo stesso file da' lo stesso risultato, e nessun test
    distingueva le due cose. Qui il file **non c'e' piu'** quando i parser
    partono, quindi l'unico modo di rendere le frequenze e' usare le righe
    ricevute.

    Mutazione che lo uccide: ignorare `righe` in `_righe_dat`. I tre parser
    vanno a leggere un file cancellato e sollevano `FileNotFoundError`.
    """
    percorso = tmp_path / "sparito.dat"
    percorso.write_text(DAT_FREQUENZE, encoding="ascii")
    righe = percorso.read_text(encoding="ascii").splitlines()
    percorso.unlink()

    assert solve.leggi_frequenze(percorso, righe=righe) == pytest.approx(
        [4384.661, 4384.661, 6164.044, 9633.291]
    )
    assert solve.leggi_massa_modale(percorso, righe=righe) is None
    assert solve.leggi_reazioni(percorso, righe=righe) == {}


def test_un_byte_non_ascii_non_aggiunge_un_campo_alla_riga_di_dati(tmp_path):
    """Perche' la lettura condivisa decodifica con `errors="ignore"`.

    Il `.dat` si dichiara ASCII e `ccx` lo scrive ASCII, ma la scelta di che
    cosa fare di un byte fuori tabella cambia il **conteggio dei campi**, che
    e' il criterio con cui questi tre parser distinguono una riga di dati da
    una di intestazione. Misurato sulle due opzioni, con un byte isolato fra
    due spazi in mezzo a una riga a cinque campi:

    - `errors="ignore"` scarta il byte, restano cinque campi e la riga si
      legge;
    - `errors="replace"` mette `U+FFFD`, che non e' spazio ma nemmeno si
      attacca ai vicini: diventa un **sesto** campo, la riga non passa piu'
      il `len(campi) != 5` e `leggi_frequenze` si ferma li', perdendo i modi
      che seguono.

    Sull'altro caso -- byte incollato fra due cifre -- le due opzioni danno
    lo stesso conteggio (`1.02.0` e `1.0\ufffd2.0` sono entrambi un campo
    solo), quindi `replace` non protegge da nulla e in cambio inventa un
    campo dove `ignore` non ne inventa. Il byte non e' uno spazio in nessuna
    delle due letture: non puo' separare due campi che erano uniti.

    Mutazione che lo uccide: rimettere `errors="replace"` in `_righe_dat`.
    Escono due frequenze invece di quattro.
    """
    percorso = tmp_path / "sporco.dat"
    intera = DAT_FREQUENZE.encode("ascii").replace(
        b"      3   0.1500000E+10", b"      3 \xb0 0.1500000E+10"
    )
    assert b"\xb0" in intera
    percorso.write_bytes(intera)

    assert solve.leggi_frequenze(percorso) == pytest.approx(
        [4384.661, 4384.661, 6164.044, 9633.291]
    )


def test_leggi_reazioni_su_dat_senza_blocco_forze_non_solleva(tmp_path):
    """Ingresso degenere 1: `.dat` senza alcun blocco di reazioni -> dizionario
    vuoto, non un'eccezione. Codice gia' corretto (nessun ramo puo' sollevare
    qui), nessun test esistente lo copriva per `leggi_reazioni` in isolamento
    (solo `controlla_reazioni({})` era testato) -- verificato in questa
    sessione, aggiunto per chiudere la mappa ingressi degeneri del brief."""
    percorso = tmp_path / "senza_reazioni.dat"
    percorso.write_text("qualche riga di testo\nche non ha reazioni\n", encoding="ascii")

    assert solve.leggi_reazioni(percorso) == {}


DAT_SOLO_MODALE = """\
     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00

                    E I G E N V A L U E    N U M B E R     1


 forces (fx,fy,fz) for set BASE and time  0.2000000E+01

         1  3.606172E+06  4.669528E+06  1.590494E+07
"""


def test_leggi_reazioni_su_dat_con_solo_blocco_modale_non_prende_le_righe_modali(tmp_path):
    """Ingresso degenere 2: `.dat` con il solo blocco modale (nessun passo
    statico prima) -> nessuna reazione statica, e le righe modali (milioni di
    N) non vengono scambiate per reazioni vere. La guardia su
    `E I G E N V A L U E   O U T P U T` scatta subito, prima di incontrare
    qualunque `S T E P`: stesso meccanismo gia' testato per il caso
    contaminato sopra, qui verificato per il caso limite senza alcun passo
    statico davanti."""
    percorso = tmp_path / "solo_modale.dat"
    percorso.write_text(DAT_SOLO_MODALE, encoding="ascii")

    assert solve.leggi_reazioni(percorso) == {}


# ccx 2.22 reale, deck ad hoc: un tetraedro solo, base (nodi 1,2,3) a z=0
# fissata su tutti e tre gli assi, apice (nodo 4) libero, `*DLOAD, GRAV`
# verticale. Catturato eseguendo `ccx -i model` su questo identico deck nel
# worktree del debugger. Nessun errore, zero avvisi, returncode 0, "Job
# finished".
DAT_UN_TETRAEDRO = """\

                        S T E P       1


                                INCREMENT     1


 forces (fx,fy,fz) for set BASE and time  0.1000000E+01

         1  1.839375E-01  1.839375E-01  7.357500E-01
         2 -1.839375E-01  0.000000E+00  0.000000E+00
         3  0.000000E+00 -1.839375E-01  0.000000E+00
"""


def test_somma_reazioni_su_un_tetraedro_piu_la_quota_tributaria_eguaglia_il_peso():
    """Oracolo corretto dopo il fix (giro di correzione del Task 7).

    Stesso deck e stessa prova in forma chiusa dell'indagine: con l'apice
    libero e i tre nodi di base fissati, `ccx` stampa solo 0,73575 N di
    reazione totale (1/4 di 2,943 N attesi) perche' la `RF` di un nodo
    vincolato non include la quota di `*DLOAD, GRAV` applicata a quel nodo
    dagli elementi che lo toccano -- riporta solo la trasmissione elastica
    interna. L'invariante fisico vero non e' `somma(RF) == rho*V*g`, e'
    `somma(RF) + quota_tributaria(BASE) == rho*V*g`: e' esattamente cio' che
    `_quota_tributaria_gravita` calcola e che `risolvi()` somma prima del
    confronto in `controlla_reazioni`.
    """
    nodes = np.array(
        [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]]
    )
    tets = np.array([[0, 1, 2, 3]], dtype=np.int64)
    densita, gravita = 1.8e-9, 9810.0
    massa = densita * float(np.abs(quality.tet_volumes(nodes, tets)).sum())
    peso_atteso_z = massa * gravita  # 2.943 N

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        percorso = Path(d) / "model.dat"
        percorso.write_text(DAT_UN_TETRAEDRO, encoding="ascii")
        reazioni = solve.leggi_reazioni(percorso, passo=1)

    somma_z = sum(v[2] for v in reazioni.values())
    quota_tributaria_massa = solve._quota_tributaria_gravita(
        nodes, tets, reazioni.keys(), densita, "C3D4"
    )

    assert somma_z + quota_tributaria_massa * gravita == pytest.approx(peso_atteso_z, rel=1e-6)


def test_la_ripartizione_della_gravita_somma_al_peso_su_entrambi_gli_elementi():
    """L'oracolo in forma chiusa della ripartizione, senza eseguire `ccx` (#40).

    Il vettore dei carichi consistenti e' l'integrale delle funzioni di
    forma, quindi sommato su **tutti** i nodi di un elemento deve dare
    esattamente il volume -- e moltiplicato per la densita', la massa. Vale
    per costruzione qualunque siano i coefficienti giusti, quindi e' il test
    che smaschera una tabella sbagliata senza sapere quale sia quella giusta.

    Su C3D10 i coefficienti sono `-1/20` ai quattro vertici e `+1/5` ai sei
    nodi di lato: `4*(-1/20) + 6*(1/5) = 1`. Il segno negativo sui vertici
    non e' un refuso, ed e' la ragione per cui la formula del lineare
    sbagliava anche di **verso** e non solo di ampiezza.
    """
    nodes_lin = np.array(
        [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]]
    )
    tets = np.array([[0, 1, 2, 3]], dtype=np.int64)
    densita = 1.8e-9
    massa = densita * float(np.abs(quality.tet_volumes(nodes_lin, tets)).sum())

    tutti_lin = np.arange(1, len(nodes_lin) + 1)
    assert solve._quota_tributaria_gravita(
        nodes_lin, tets, tutti_lin, densita, "C3D4"
    ) == pytest.approx(massa, rel=1e-12)

    # lo stesso tetraedro a dieci nodi: i sei di lato a meta' spigolo, che e'
    # dove TetGen li mette con `order=2`
    v = nodes_lin
    lati = np.array([
        (v[0] + v[1]) / 2, (v[1] + v[2]) / 2, (v[0] + v[2]) / 2,
        (v[0] + v[3]) / 2, (v[1] + v[3]) / 2, (v[2] + v[3]) / 2,
    ])
    nodes_quad = np.vstack([v, lati])
    tets10 = np.arange(10, dtype=np.int64).reshape(1, 10)
    tutti_quad = np.arange(1, len(nodes_quad) + 1)

    assert solve._quota_tributaria_gravita(
        nodes_quad, tets10, tutti_quad, densita, "C3D10"
    ) == pytest.approx(massa, rel=1e-12)


def test_su_c3d10_i_vertici_pesano_negativo_e_i_lati_portano_il_carico():
    """La controprova del test sopra, e **serve davvero**: verificato per
    mutazione il 26/08/2026, rimettendo la formula del lineare sul ramo
    C3D10, il test della somma totale **non fallisce**. Con `+V/4` sui soli
    quattro vertici la somma su tutti e dieci i nodi vale comunque `V`, cioe'
    l'oracolo globale e' soddisfatto da una tabella sbagliata. Solo guardando
    le due meta' separate la differenza si vede.

    Quattro vertici a `-V/20` fanno `-massa/5`; sei nodi di lato a `+V/5`
    fanno `+6*massa/5`. Sono i due numeri che la formula del tetraedro
    lineare (`+massa/4` sui soli vertici, zero sui lati) non puo' produrre
    ne' per ampiezza ne' per segno.
    """
    v = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]])
    lati = np.array([
        (v[0] + v[1]) / 2, (v[1] + v[2]) / 2, (v[0] + v[2]) / 2,
        (v[0] + v[3]) / 2, (v[1] + v[3]) / 2, (v[2] + v[3]) / 2,
    ])
    nodes = np.vstack([v, lati])
    tets10 = np.arange(10, dtype=np.int64).reshape(1, 10)
    densita = 1.8e-9
    massa = densita * float(np.abs(quality.tet_volumes(nodes, tets10[:, :4])).sum())

    soli_vertici = solve._quota_tributaria_gravita(nodes, tets10, [1, 2, 3, 4], densita, "C3D10")
    soli_lati = solve._quota_tributaria_gravita(
        nodes, tets10, [5, 6, 7, 8, 9, 10], densita, "C3D10"
    )

    assert soli_vertici == pytest.approx(-massa / 5.0, rel=1e-12)
    assert soli_lati == pytest.approx(6.0 * massa / 5.0, rel=1e-12)
    # e la formula del lineare sugli stessi vertici da' tutt'altro: e' il
    # numero che il codice usava prima della correzione
    assert solve._quota_tributaria_gravita(
        nodes, tets10, [1, 2, 3, 4], densita, "C3D4"
    ) == pytest.approx(massa, rel=1e-12)


def test_un_elemento_sconosciuto_non_prende_la_formula_di_un_altro():
    """Senza predefinito e senza ripiego: la ripartizione dipende dalle
    funzioni di forma, e prendere quelle di un elemento diverso darebbe un
    numero plausibile e sbagliato -- che e' peggio di nessun numero.
    """
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    tets = np.array([[0, 1, 2, 3]], dtype=np.int64)

    with pytest.raises(ValueError, match="C3D8"):
        solve._quota_tributaria_gravita(nodes, tets, [1], 1.8e-9, "C3D8")


def test_c3d10_su_un_array_a_quattro_colonne_non_rende_un_peso_negativo():
    """`element_type` era validato, le colonne di `elements` no.

    Su C3D10 la funzione legge `elements[:, 4:10]` per i nodi di lato: con un
    array a quattro colonne quella fetta e' **vuota**, il termine `+V/5` dei
    lati vale zero, e resta il solo `-V/20` dei vertici. La funzione rendeva
    quindi una massa **negativa**, senza errore -- e una massa negativa in un
    controllo di equilibrio non e' un numero sbagliato di poco, e' un numero
    che non esiste.

    Non raggiungibile dalla pipeline (`export_model` valida `elements.shape[1]`
    a monte) ma sì da chiamata diretta: test e script di cantiere chiamano
    questa funzione senza passare da li'.

    Mutazione che lo uccide: togliere la guardia sulle colonne. Nessuna
    eccezione, e il valore reso e' `-massa/5`, cioe' negativo.
    """
    nodes = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]])
    tets = np.array([[0, 1, 2, 3]], dtype=np.int64)

    with pytest.raises(ValueError, match="10 nodi per elemento"):
        solve._quota_tributaria_gravita(nodes, tets, [1, 2, 3, 4], 1.8e-9, "C3D10")


def test_le_guardie_della_quota_parlano_anche_a_insieme_vuoto():
    """`if not nodi_1based: return 0.0` precedeva le due validazioni, quindi
    un `element_type` ignoto e un array di forma sbagliata passavano in
    silenzio a insieme vuoto. Lo `0.0` era il numero giusto, ma l'oracolo
    «C3D10 a quattro colonne solleva» valeva solo a insieme non vuoto e
    nessuno lo diceva.

    Ordine dichiarato: parla prima `element_type`, poi le colonne. Un tipo
    ignoto non ha un numero di colonne atteso da confrontare, quindi la
    seconda guardia non saprebbe nemmeno che cosa dire.

    Mutazione che lo uccide: rimettere il return anticipato sopra le due
    guardie. Nessuna delle due solleva e la funzione rende `0.0`.
    """
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    tets = np.array([[0, 1, 2, 3]], dtype=np.int64)

    with pytest.raises(ValueError, match="C3D8"):
        solve._quota_tributaria_gravita(nodes, tets, [], 1.8e-9, "C3D8")
    with pytest.raises(ValueError, match="10 nodi per elemento"):
        solve._quota_tributaria_gravita(nodes, tets, [], 1.8e-9, "C3D10")
    # e a tipo noto con array coerente l'insieme vuoto resta zero, non un errore
    assert solve._quota_tributaria_gravita(nodes, tets, [], 1.8e-9, "C3D4") == 0.0


def test_la_guardia_sulle_colonne_scatta_anche_a_una_colonna_dalla_meta():
    """Non solo il caso a quattro colonne, e il messaggio non promette una
    conseguenza che vale solo lì.

    Con **nove** colonne su C3D10 la fetta `elements[:, 4:10]` dà cinque nodi
    di lato su sei: `4*(-1/20) + 5*(1/5) = +0,8` invece di `1`. Il peso esce
    **positivo** e sbagliato, non negativo -- negativo è il solo caso a
    quattro colonne, dove i lati mancano tutti e resta `4*(-1/20) = -0,2`.
    Un messaggio che promette «negativo» descriverebbe quindi una
    conseguenza falsa su ogni forma intermedia.
    """
    nodes = np.zeros((10, 3))
    nodes[1:4] = np.eye(3) * 100.0
    noni = np.arange(9, dtype=np.int64).reshape(1, 9)

    with pytest.raises(ValueError, match="peso sbagliato") as errore:
        solve._quota_tributaria_gravita(nodes, noni, [1, 2, 3, 4], 1.8e-9, "C3D10")
    assert "9" in str(errore.value)


# ---------------------------------------------------------------------------
# Giro di correzione 5: enumerazione esplicita del cancello di finitezza,
# non un elenco tenuto a mente. Tre giri di seguito abbiamo chiuso un caso
# alla volta -- rapporto_max_p99, poi passato, poi banda -- perche' ogni
# volta l'elenco dei parametri che raggiungono un confronto lo compilava
# una persona ragionando. Ragionare su NaN aveva nascosto ±inf: due
# combinazioni passavano ancora (`controlla_reazioni(..., tolleranza=inf)`,
# `controlla_autovalori(..., soglia_relativa=-inf)`) perche' "NaN in un
# confronto e' sempre falso" e' vero solo per NaN, non per un infinito con
# segno dalla parte permissiva del confronto. Questa tabella e' l'elenco:
# chi aggiunge un sesto controllo lo aggiunge qui, non lo tiene a mente.
# ---------------------------------------------------------------------------

_PICCO_VALORI_SANI = np.array([1.0, 2.0, 3.0, 4.0])
_PICCO_QUOTE_SANE = np.array([0.0, 10.0, 20.0, 30.0])
_REAZIONI_SANE = {1: (0.0, 0.0, 500.0), 2: (0.0, 0.0, 500.0)}
_PESO_ATTESO_SANO = (0.0, 0.0, 1000.0)

# (nome, costruttore che inietta il valore anomalo in un ingresso, valore
# sano nello stesso slot -- deve restare `passato: True`).
_INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO = [
    ("picco/valori", lambda b: solve.controlla_picco(
        np.array([1.0, b, 3.0, 4.0]), _PICCO_QUOTE_SANE, banda=5.0), 2.0),
    ("picco/quote", lambda b: solve.controlla_picco(
        _PICCO_VALORI_SANI, np.array([0.0, b, 20.0, 30.0]), banda=5.0), 10.0),
    ("picco/banda", lambda b: solve.controlla_picco(
        _PICCO_VALORI_SANI, _PICCO_QUOTE_SANE, banda=b), 5.0),
    ("autovalori/prima_frequenza", lambda b: solve.controlla_autovalori(
        [b, 21.19]), 25.0),
    ("autovalori/frequenza_unica", lambda b: solve.controlla_autovalori(
        [b]), 25.0),
    ("autovalori/soglia_relativa", lambda b: solve.controlla_autovalori(
        [21.19, 34.3], soglia_relativa=b), 0.2),
    ("reazioni/reazione", lambda b: solve.controlla_reazioni(
        {1: (0.0, 0.0, b), 2: (0.0, 0.0, 500.0)}, _PESO_ATTESO_SANO, tolleranza=0.02), 500.0),
    ("reazioni/peso_atteso", lambda b: solve.controlla_reazioni(
        _REAZIONI_SANE, (0.0, 0.0, b), tolleranza=0.02), 1000.0),
    ("reazioni/tolleranza", lambda b: solve.controlla_reazioni(
        _REAZIONI_SANE, _PESO_ATTESO_SANO, tolleranza=b), 0.02),
    # Le due righe che mancavano (M11 della revisione finale): l'elenco
    # copriva tre verdetti su cinque, perche' gli altri due erano scritti
    # inline dentro `risolvi()` e non c'era una funzione da chiamare qui.
    ("vincolo_in_pianta/minimo", lambda b: solve.controlla_vincolo_in_pianta(b), 0.99),
    ("avvisi/conteggio", lambda b: solve.controlla_avvisi(b), 0),
    # Sesto verdetto (#12). `soglia` e' lo slot che ripete la trappola gia'
    # vista su `controlla_reazioni`: senza guardia, `soglia=+inf` sarebbe
    # soddisfatta da qualunque rapporto finito e il controllo passerebbe su
    # un modello esploso.
    ("spostamenti/u_max", lambda b: solve.controlla_spostamenti(b, 100.0), 1.0),
    ("spostamenti/dimensione", lambda b: solve.controlla_spostamenti(1.0, b), 100.0),
    ("spostamenti/soglia", lambda b: solve.controlla_spostamenti(1.0, 100.0, soglia=b), 1.0),
    # Settimo verdetto (#75): la soglia sulla frazione di massa raggiunge un
    # confronto come le altre, e `-inf` la renderebbe soddisfatta da
    # qualunque frazione.
    ("massa_modale/soglia", lambda b: solve.controlla_massa_modale(
        {"catturata": [0.95] * 6, "disponibile": [1.0] * 6}, soglia=b), 0.9),
]


@pytest.mark.parametrize(
    "nome,costruisci,_sano", _INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO,
    ids=[nome for nome, _, _sano in _INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO],
)
@pytest.mark.parametrize("anomalo", [float("nan"), float("inf"), float("-inf")], ids=["nan", "+inf", "-inf"])
def test_ogni_ingresso_che_raggiunge_un_confronto_fallisce_chiuso(nome, costruisci, _sano, anomalo):
    """27 combinazioni (9 ingressi x 3 valori anomali): tutte `passato: False`.

    Prima di questo giro ne passavano due: `tolleranza=inf` in
    `controlla_reazioni` (`scarto <= inf` e' vero per qualunque scarto
    finito) e `soglia_relativa=-inf` in `controlla_autovalori` (nessuna
    frequenza supera mai una soglia `-inf`). Entrambi erano stati
    "verificati" nel giro precedente ragionando solo sul caso NaN.
    """
    assert costruisci(anomalo)["passato"] is False


@pytest.mark.parametrize(
    "nome,costruisci,sano", _INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO,
    ids=[nome for nome, _, _sano in _INGRESSI_CHE_RAGGIUNGONO_UN_CONFRONTO],
)
def test_lo_stesso_ingresso_con_un_valore_sano_passa(nome, costruisci, sano):
    """Controprova della tabella sopra: un valore finito e coerente nello
    stesso slot deve restare `passato: True` -- altrimenti la guardia di
    finitezza sarebbe troppo larga, non solo troppo stretta."""
    assert costruisci(sano)["passato"] is True


def test_senza_passo_statico_gli_spostamenti_sono_non_verificati_non_zero():
    """Un deck solo modale non ha uno spostamento fisico da misurare: le
    `MODO_n` sono forme normalizzate sulla massa. `None` non e' zero, e zero
    passerebbe il confronto -- che e' come un deck modale otterrebbe un
    verdetto verde su una grandezza che non possiede.
    """
    esito = solve.controlla_spostamenti(None, 100.0)

    assert esito["passato"] is False
    assert esito["rapporto"] is None
    assert esito["u_max"] is None


def test_una_dimensione_nulla_non_divide_per_zero():
    """Nessun nodo, o tutti coincidenti: la diagonale del contenitore e' 0 e
    il rapporto non esiste. Dichiarato non verificato, non `inf`."""
    assert solve.controlla_spostamenti(1.0, 0.0)["passato"] is False
    assert solve.controlla_spostamenti(1.0, 0.0)["rapporto"] is None
    assert solve._dimensione(np.zeros((0, 3))) == 0.0


def test_lo_spostamento_pari_alla_dimensione_del_modello_non_passa():
    """Il confronto e' stretto (`<`), e il confine e' dove sta la ragione
    della soglia: uno spostamento **grande quanto il modello** falsifica gia'
    l'ipotesi di piccoli spostamenti con cui e' stato calcolato. Un `<=`
    lascerebbe passare esattamente il caso che definisce il limite.
    """
    assert solve.controlla_spostamenti(100.0, 100.0)["passato"] is False
    assert solve.controlla_spostamenti(99.9, 100.0)["passato"] is True


def test_il_massimo_ignora_i_modi_e_prende_il_peggiore_fra_gli_statici():
    """`MODO_n` e' normalizzato sulla massa: la sua ampiezza non e' un
    millimetro. Se entrasse qui, un modale con forma grande boccerebbe una
    corsa buona -- e un `VM_` (uno scalare) non e' uno spostamento affatto.
    """
    point_data = {
        "U_GRAVITA": np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
        "U_SPINTA": np.array([[0.0, 3.0, 0.0], [0.0, 0.0, 0.0]]),
        "MODO_1": np.array([[1e6, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        "VM_GRAVITA": np.array([10.0, 20.0]),
    }

    assert solve._spostamento_massimo(point_data) == pytest.approx(3.0)
    assert solve._spostamento_massimo({"MODO_1": np.array([[1e6, 0.0, 0.0]])}) is None


def test_il_ramo_a_una_frequenza_non_consulta_la_soglia_relativa():
    """Con una sola frequenza non esiste rapporto da confrontare: il verdetto e'
    `prima > 0.0` e nient'altro. Una `soglia_relativa` non finita non deve
    quindi bocciarlo -- il cancello di finitezza copre gli ingressi che
    raggiungono un confronto, e su questo ramo la soglia non ne raggiunge
    nessuno. Una prima frequenza nulla resta un meccanismo, soglia a parte.
    """
    for soglia in (float("nan"), float("inf"), float("-inf")):
        assert solve.controlla_autovalori([25.0], soglia_relativa=soglia)["passato"] is True
    assert solve.controlla_autovalori([0.0])["passato"] is False


# ---------------------------------------------------------------------------
# Revisione finale, C1: nel `.vtu` i vettori devono stare nello stesso telaio
# dei punti. `export_model` allinea il deck agli assi e non restituisce i nodi
# allineati; `pipeline.run` passa a `risolvi` i nodi NON allineati insieme al
# `point_data` che viene dal `.frd`, cioe' dal deck allineato. Fino a questo
# giro il `.vtu` mescolava i due telai, e ogni consumatore odierno era
# invariante per rotazione (norma, scalari, sola z) quindi nessuno se ne
# accorgeva -- ma un *Warp By Vector* in ParaView deforma a 90 gradi dalla
# direzione vera, senza un avviso.
#
# I blocchi `.frd` qui sotto sono costruiti a colonne fisse dallo stesso
# generatore, invece che a mano: le tre trappole di formato che
# `FRD_TRE_BLOCCHI` e `FRD_QUATTRO_PASSI` verificano sono gia' coperte da
# quelle fixture, e ricopiarle a mano per ogni nuovo caso e' solo occasione
# di sbagliare una colonna.
# ---------------------------------------------------------------------------

# Il tratto fisso del record 100CL fra il valore e la cifra del passo,
# misurato sui due record veri gia' in questo file (colonne 24-61).
_100CL_MEZZO = "           2                     0    "


def _record_100cl(passo: int, valore: float, modale: bool) -> str:
    """Numero di passo scritto **a partire** dalla colonna 62.

    E' cio' che `printf("%1d", passo)` produce: a una cifra il campo occupa
    la sola colonna 62, a due cifre trabocca a destra e sposta `MODAL`.
    """
    return f"  100CL  101{valore:12.9f}{_100CL_MEZZO}{passo}{'MODAL' if modale else '     '}      1"


def _record_100cl_allineato(passo: int, valore: float, modale: bool) -> str:
    """Numero di passo allineato **a destra** sulla colonna 62.

    E' cio' che `printf("%5d", passo)` produce: a una cifra e' identico a
    `_record_100cl`, ma a due cifre cresce verso sinistra e `MODAL` resta alla
    colonna 63.

    Le due forme esistono perche' il `.frd` non dichiara la larghezza del
    campo: quale delle due abbia resta indeciso qui, dove non si esegue il
    solutore. La lettura deve reggere entrambe, e il benchmark di validazione
    `tests/validazione/test_passi_oltre_nove.py` la misura contro `ccx` vero.
    """
    cifre = str(passo)
    mezzo = _100CL_MEZZO[: len(_100CL_MEZZO) - len(cifre) + 1]
    return f"  100CL  101{valore:12.9f}{mezzo}{cifre}{'MODAL' if modale else '     '}      1"


def _frd(blocchi, record=_record_100cl) -> str:
    """`.frd` ascii da una lista di `(passo, grandezza, modale, valore, righe)`.

    `righe` e' `{nodo: (componenti...)}`. Le colonne sono quelle che
    `solve.leggi_frd` legge: nodo a dieci caratteri dopo ` -1`, componenti a
    dodici.
    """
    testo: list[str] = []
    for passo, grandezza, modale, valore, righe in blocchi:
        testo.append(record(passo, valore, modale))
        testo.append(f" -4  {grandezza:<12}{len(next(iter(righe.values())))}    1")
        for nodo, componenti in righe.items():
            testo.append(f" -1{nodo:10d}" + "".join(f"{v:12.5E}" for v in componenti))
        testo.append(" -3")
    return "\n".join(testo) + "\n"


# Quattro nodi, un tetraedro: la geometria non conta per il telaio dei
# vettori, conta solo che i punti scritti nel `.vtu` siano questi.
_NODI_TET = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
_ELEMENTI_TET = np.array([[0, 1, 2, 3]])

# Rotazione di 90 gradi attorno a z nella forma che `align_to_axes` produce
# davvero: `rotation = [x_dir, y_dir, z_dir]` con `y_dir = z x x`, quindi
# determinante +1 per costruzione. Con lo spessore del pezzo su y del telaio
# dei punti si ottiene x_dir = (0,1,0) e y_dir = (-1,0,0). E' la stessa forma
# della trasformata misurata su `runs/lab_telaio_v2`
# (`metrics["11_export"]["transform"]`), dove l'imbardata stimata vale
# 0,0054 rad e la traslazione (730,6; 4328,9; 595,4) mm.
_ROTAZIONE_90_Z = [
    [0.0, 1.0, 0.0, 730.6],
    [-1.0, 0.0, 0.0, 4328.9],
    [0.0, 0.0, 1.0, 595.4],
    [0.0, 0.0, 0.0, 1.0],
]

# GRAVITA scende, SPINTA_ORIZZONTALE scende e spinge su +y **del modello** --
# la differenza vale esattamente (0, 1, 0), l'asse dichiarato in
# `lab_telaio.yaml`. Il modo e' anch'esso su +y del modello.
_FRD_SPINTA_SU_Y = _frd([
    (1, "DISP", False, 1.0, {n: (0.0, 0.0, -1.0) for n in (1, 2, 3, 4)}),
    (1, "STRESS", False, 1.0, {n: (1.0, 0.0, 0.0, 0.0, 0.0, 0.0) for n in (1, 2, 3, 4)}),
    (2, "DISP", False, 1.0, {n: (0.0, 1.0, -1.0) for n in (1, 2, 3, 4)}),
    (2, "STRESS", False, 1.0, {n: (5.0, 0.0, 0.0, 0.0, 0.0, 0.0) for n in (1, 2, 3, 4)}),
    (3, "DISP", True, 21.19, {n: (0.0, 1.0, 0.0) for n in (1, 2, 3, 4)}),
])


def _risolvi_finto(
    tmp_path, monkeypatch, frd, *, casi, trasformata, dat=DAT_DUE_MODI,
    nodi=_NODI_TET, elementi=_ELEMENTI_TET, uscita="Job finished\n",
):
    """`risolvi()` con `ccx` sostituito da un `subprocess.run` finto.

    Stesso principio di `test_risolvi_con_ccx_simulato_...`: il `.frd`/`.dat`
    che il processo finto "avrebbe scritto" sono gia' su disco quando
    `risolvi()` li legge.
    """
    import subprocess

    deck = tmp_path / "wall_model.inp"
    deck.write_text("*HEADING\n", encoding="ascii")
    deck.with_suffix(".frd").write_text(frd, encoding="ascii")
    deck.with_suffix(".dat").write_text(dat, encoding="ascii")

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(
        solve.subprocess, "run",
        lambda comando, **kwargs: subprocess.CompletedProcess(
            comando, returncode=0, stdout=uscita, stderr=""),
    )
    return solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4",
        casi_di_carico=casi, vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0},
        trasformata=trasformata,
    )


def test_i_vettori_del_vtu_stanno_nel_telaio_dei_punti_e_non_del_modello(tmp_path, monkeypatch):
    """C1: la direzione della spinta, riletta dal `.vtu`, deve stare nello
    stesso telaio dei punti che il `.vtu` contiene.

    Il campo esce dal `.frd`, cioe' dal deck allineato: `U_SPINTA_ORIZZONTALE
    - U_GRAVITA` vale (0, 1, 0), l'asse +y **del modello**. I punti del
    `.vtu` sono quelli non allineati. Con questa rotazione +y del modello e'
    -x nel telaio dei punti: e' quello che il file deve contenere, altrimenti
    un *Warp By Vector* deforma a 90 gradi dalla direzione vera.

    L'oracolo e' il campo riletto, non la matrice.
    """
    meshio = pytest.importorskip("meshio")

    _risolvi_finto(
        tmp_path, monkeypatch, _FRD_SPINTA_SU_Y,
        casi=["GRAVITA", "SPINTA_ORIZZONTALE", "MODALE"], trasformata=_ROTAZIONE_90_Z,
    )

    mesh = meshio.read(tmp_path / "13_solution.vtu")
    differenza = mesh.point_data["U_SPINTA_ORIZZONTALE"] - mesh.point_data["U_GRAVITA"]
    direzione = differenza.mean(axis=0)
    direzione = direzione / np.linalg.norm(direzione)

    assert direzione == pytest.approx([-1.0, 0.0, 0.0], abs=1e-9), (
        "+y del modello, riportato nel telaio dei punti da questa rotazione, "
        f"e' -x: il file contiene invece {direzione}"
    )
    # Controprova nell'altro verso: riportata nel telaio del modello (u @ R.T,
    # l'inversa di u @ R), la direzione deve tornare +y, l'asse dichiarato.
    rotazione = np.asarray(_ROTAZIONE_90_Z)[:3, :3]
    assert direzione @ rotazione.T == pytest.approx([0.0, 1.0, 0.0], abs=1e-9)


def test_anche_le_forme_modali_si_riportano_nel_telaio_dei_punti(tmp_path, monkeypatch):
    """Ingresso degenere: `MODO_*` presenti e `U_*` assenti -- i modi vanno
    ruotati lo stesso. Un modo e' un vettore come uno spostamento: quello che
    non e' un vettore, e non si tocca, e' la von Mises."""
    meshio = pytest.importorskip("meshio")

    solo_modale = _frd([(1, "DISP", True, 21.19, {n: (0.0, 1.0, 0.0) for n in (1, 2, 3, 4)})])
    esito = _risolvi_finto(
        tmp_path, monkeypatch, solo_modale, casi=["GRAVITA", "MODALE"],
        trasformata=_ROTAZIONE_90_Z,
    )

    assert esito["modi"] == 1
    mesh = meshio.read(tmp_path / "13_solution.vtu")
    assert set(mesh.point_data) == {"MODO_1"}
    assert mesh.point_data["MODO_1"][0] == pytest.approx([-1.0, 0.0, 0.0], abs=1e-9)


def test_un_vtu_di_sole_tensioni_non_ha_nulla_da_ruotare(tmp_path, monkeypatch):
    """Ingresso degenere: nessuna chiave `U_*` ne' `MODO_*` (solo von Mises,
    che e' uno scalare) -- nessun errore, e lo scalare resta quello che
    `von_mises` ha calcolato."""
    meshio = pytest.importorskip("meshio")

    solo_tensioni = _frd([
        (1, "STRESS", False, 1.0, {n: (3.0, 0.0, 0.0, 0.0, 0.0, 0.0) for n in (1, 2, 3, 4)}),
    ])
    esito = _risolvi_finto(
        tmp_path, monkeypatch, solo_tensioni, casi=["GRAVITA"], trasformata=_ROTAZIONE_90_Z,
    )

    assert esito["eseguito"] is True
    mesh = meshio.read(tmp_path / "13_solution.vtu")
    assert set(mesh.point_data) == {"VM_GRAVITA"}
    assert mesh.point_data["VM_GRAVITA"] == pytest.approx([3.0, 3.0, 3.0, 3.0])


@pytest.mark.parametrize(
    "trasformata,motivo",
    [
        (None, "assente"),
        ([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], "3x3"),
    ],
    ids=["assente", "3x3"],
)
def test_una_trasformata_che_non_e_4x4_e_un_errore_dichiarato(tmp_path, monkeypatch, trasformata, motivo):
    """Ingresso degenere: senza la trasformata il campo non e' riportabile nel
    telaio dei punti. Un `.vtu` scritto lo stesso, con il campo non ruotato,
    sarebbe di nuovo il difetto C1 -- in silenzio."""
    with pytest.raises(ValueError, match="4x4"):
        _risolvi_finto(
            tmp_path, monkeypatch, _FRD_SPINTA_SU_Y,
            casi=["GRAVITA", "SPINTA_ORIZZONTALE", "MODALE"], trasformata=trasformata,
        )
    assert not (tmp_path / "13_solution.vtu").exists(), f"trasformata {motivo}: nessun artefatto"


def test_una_rotazione_con_determinante_diverso_da_uno_non_si_applica(tmp_path, monkeypatch):
    """Ingresso degenere: `align_to_axes` costruisce la terna col prodotto
    vettoriale, quindi il determinante vale +1 per costruzione. Se quello che
    arriva qui non e' una rotazione (riflessione, scala, matrice corrotta),
    applicarlo comunque specchierebbe il campo senza dirlo."""
    specchiata = [
        [0.0, 1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    with pytest.raises(ValueError, match="determinante"):
        _risolvi_finto(
            tmp_path, monkeypatch, _FRD_SPINTA_SU_Y,
            casi=["GRAVITA", "SPINTA_ORIZZONTALE", "MODALE"], trasformata=specchiata,
        )


# ---------------------------------------------------------------------------
# Revisione finale, I2: `leggi_reazioni` prometteva nel docstring un filtro
# sull'intestazione delle forze che il corpo non aveva -- accettava qualunque
# riga a quattro campi col primo intero. Un blocco `*NODE PRINT, U` produce
# righe identiche in forma, e `_passo_statico` (abaqus.py) scrive gli `U`
# **prima** dell'`RF`. Oggi la produzione non passa mai `print_nsets`, ma
# `print_nsets=("TOP",)` e' gia' usato in tests/feasibility/test_calculix.py
# e tests/test_abaqus.py: bastava esporlo per sommare millimetri e newton
# dentro `controlla_reazioni` senza alcuna eccezione.
#
# Blocco misurato in forma su un `.dat` vero (runs/lab_telaio_v2/13_solution.dat,
# riga 8: ` forces (fx,fy,fz) for set BASE and time  0.1000000E+01`); il blocco
# `displacements` ha la stessa forma, ed e' quello di
# tests/feasibility/test_calculix.py::DAT_SPOSTAMENTI_CONTAMINATO.
# ---------------------------------------------------------------------------

DAT_SPOSTAMENTI_PRIMA_DELLE_REAZIONI = """\

                        S T E P       1


                                INCREMENT     1


 displacements (vx,vy,vz) for set TOP and time  0.1000000E+01

       101 -1.000000E-03  2.000000E-04  3.000000E-04
       102 -1.100000E-03  2.100000E-04  3.100000E-04

 forces (fx,fy,fz) for set BASE and time  0.1000000E+01

         1 -1.000000E+03 -1.108911E+02 -2.000000E+03
         2 -1.000000E+03  1.108911E+02  2.000000E+03
"""


def test_leggi_reazioni_scarta_gli_spostamenti_stampati_prima_delle_forze(tmp_path):
    """I2: con `print_nsets` non vuoto il `.dat` porta un blocco `U` prima
    dell'`RF`, nello stesso passo. Solo le forze devono finire in `reazioni`:
    i due nodi del set TOP sono millimetri, e sommati alle reazioni in newton
    darebbero un verdetto di equilibrio calcolato su unita' diverse -- senza
    eccezione, senza avviso.
    """
    percorso = tmp_path / "con_spostamenti.dat"
    percorso.write_text(DAT_SPOSTAMENTI_PRIMA_DELLE_REAZIONI, encoding="ascii")

    reazioni = solve.leggi_reazioni(percorso)

    assert reazioni.keys() == {1, 2}, "101 e 102 sono spostamenti del set TOP, non reazioni"
    assert reazioni[1] == pytest.approx((-1000.0, -110.8911, -2000.0))


def test_gli_artefatti_del_solutore_si_rinominano_invece_di_duplicarsi(tmp_path, monkeypatch):
    """I4: `deck.parent` **e'** `out_dir`, quindi la copia era
    `wall_model.frd` -> `13_solution.frd` nella stessa cartella. Misurato su
    `runs/lab_telaio_v2`: 84.997.257 byte di `.frd` e 4.542.878 di `.dat`,
    materializzati in un `bytes` Python e lasciati sul disco in doppia copia
    (169.994.514 byte dove ne bastavano 84.997.257). `ccx` riscrive
    `wall_model.frd` a ogni corsa: rinominare non perde nulla.
    """
    esito = _risolvi_finto(
        tmp_path, monkeypatch, _FRD_SPINTA_SU_Y,
        casi=["GRAVITA", "SPINTA_ORIZZONTALE", "MODALE"], trasformata=np.eye(4),
    )

    assert (tmp_path / "13_solution.frd").read_text(encoding="ascii") == _FRD_SPINTA_SU_Y
    assert (tmp_path / "13_solution.dat").read_text(encoding="ascii") == DAT_DUE_MODI
    assert not (tmp_path / "wall_model.frd").exists(), "il .frd resta in una copia sola"
    assert not (tmp_path / "wall_model.dat").exists(), "il .dat resta in una copia sola"
    assert esito["frd"] == str(tmp_path / "13_solution.frd")


# ---------------------------------------------------------------------------
# Revisione finale, Critical di copertura: `controlli["picco"]` non era
# toccato da nessun test. La funzione pura `controlla_picco` e' ben coperta
# (tabella di finitezza e tre casi diretti), la **fiatura dentro `risolvi()`**
# no: quali quote arrivano alla funzione, come si calcola la banda, come i
# verdetti per caso si aggregano in uno solo.
# ---------------------------------------------------------------------------

# Otto nodi in colonna, altezza 100 -> banda di vincolo 5 (5% di
# _FRAZIONE_BANDA_VINCOLO). Il `.frd` sotto stampa i soli nodi 3..8, cioe' le
# quote 40..100: e' il caso che distingue le quote del **sottoinsieme del
# caso** (`nodes[blocco.nodi - 1, 2]`, minimo 40, banda fino a 45) da quelle
# di tutti i nodi del modello (minimo 0, banda fino a 5).
_NODI_COLONNA = np.array([
    [0.0, 0.0, 0.0], [10.0, 0.0, 10.0], [0.0, 10.0, 40.0], [10.0, 10.0, 50.0],
    [0.0, 0.0, 60.0], [10.0, 0.0, 80.0], [0.0, 10.0, 90.0], [10.0, 10.0, 100.0],
])
_ELEMENTI_COLONNA = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
_NODI_STAMPATI = (3, 4, 5, 6, 7, 8)


def _blocco_stress(passo: int, sigma_per_nodo: dict[int, float]):
    """Trazione monoassiale pura: la von Mises esce esattamente sigma."""
    return (passo, "STRESS", False, 1.0,
            {n: (s, 0.0, 0.0, 0.0, 0.0, 0.0) for n, s in sigma_per_nodo.items()})


# GRAVITA: il picco (100) cade sul nodo 3, quota 40, cioe' dentro la banda di
# vincolo del proprio sottoinsieme -- artefatto, non citabile.
# SPINTA_ORIZZONTALE: il picco cade sul nodo 8, quota 100, fuori banda.
_FRD_PICCO_DENTRO_E_FUORI_BANDA = _frd([
    (1, "DISP", False, 1.0, {n: (0.0, 0.0, -1.0) for n in _NODI_STAMPATI}),
    _blocco_stress(1, {3: 100.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0}),
    (2, "DISP", False, 1.0, {n: (0.0, 1.0, -1.0) for n in _NODI_STAMPATI}),
    _blocco_stress(2, {3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 100.0}),
])


def test_il_controllo_sul_picco_usa_le_quote_del_caso_e_aggrega_i_verdetti(tmp_path, monkeypatch):
    """Il picco si giudica sulle quote dei nodi che il blocco stampa, non su
    quelle di tutto il modello, e un solo caso bocciato basta a bocciare il
    verdetto d'insieme.

    Mutazione che questo test uccide (applicata davvero, `risolvi()`:
    `nodes[blocco.nodi - 1, 2]` -> `nodes[:, 2]`): reintroduce il difetto che
    il docstring di `controlla_picco` documenta come gia' pagato una volta.
    Con le quote di tutti i nodi la banda parte da 0 invece che da 40 e il
    confronto non e' nemmeno piu' allineato al vettore delle tensioni.
    Seconda mutazione uccisa: `all(...)` -> `any(...)`, qui un caso passa e
    l'altro no.
    """
    esito = _risolvi_finto(
        tmp_path, monkeypatch, _FRD_PICCO_DENTRO_E_FUORI_BANDA,
        casi=["GRAVITA", "SPINTA_ORIZZONTALE"], trasformata=np.eye(4),
        nodi=_NODI_COLONNA, elementi=_ELEMENTI_COLONNA,
    )

    per_caso = esito["controlli"]["picco"]["per_caso"]
    assert per_caso.keys() == {"GRAVITA", "SPINTA_ORIZZONTALE"}
    assert per_caso["GRAVITA"]["frazione_in_banda"] == 1.0
    assert per_caso["GRAVITA"]["passato"] is False, "quota 40 e' il minimo del caso: dentro banda"
    assert per_caso["SPINTA_ORIZZONTALE"]["frazione_in_banda"] == 0.0
    assert per_caso["SPINTA_ORIZZONTALE"]["passato"] is True, "quota 100: fuori banda"
    assert esito["controlli"]["picco"]["passato"] is False


def test_senza_tensioni_il_verdetto_sul_picco_e_falso_e_non_vero_per_vuoto(tmp_path, monkeypatch):
    """Ingresso degenere: `picco_per_caso` vuoto -> verdetto `False`, mai
    `True` per vacuita'. `all(())` vale `True` in Python, ed e' esattamente
    il modo in cui un controllo assente si traveste da controllo superato.

    Mutazione uccisa: `if picco_per_caso else False` -> `else True`.
    """
    solo_spostamenti = _frd([
        (1, "DISP", False, 1.0, {n: (0.0, 0.0, -1.0) for n in _NODI_STAMPATI}),
    ])

    esito = _risolvi_finto(
        tmp_path, monkeypatch, solo_spostamenti, casi=["GRAVITA"], trasformata=np.eye(4),
        nodi=_NODI_COLONNA, elementi=_ELEMENTI_COLONNA,
    )

    assert esito["controlli"]["picco"]["per_caso"] == {}
    assert esito["controlli"]["picco"]["passato"] is False


# La massa modale (#75). Il `.dat` qui sotto e' costruito con la stessa forma
# che `ccx` 2.22 scrive davvero, con numeri scelti: catturata meta' del
# disponibile in z e nove decimi nelle altre due, cosi' il verdetto e i suoi
# campi si leggono a memoria.
DAT_MASSA_MODALE = """\
     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY

      1   0.7589826E+09   0.2754964E+05   0.4384661E+04   0.0000000E+00

     P A R T I C I P A T I O N   F A C T O R S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

      1  -0.5526834E+00  -0.1568618E-02  -0.8979709E-03   0.1002478E+01  -0.8666169E+03   0.6908348E+03

     E F F E C T I V E   M O D A L   M A S S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

      1   0.4000000E+00   0.4000000E+00   0.2000000E+00   0.1000000E+03   0.2000000E+03   0.3000000E+03
      2   0.5000000E+00   0.5000000E+00   0.3000000E+00   0.1000000E+03   0.2000000E+03   0.3000000E+03
TOTAL     0.9000000E+00   0.9000000E+00   0.5000000E+00   0.2000000E+03   0.4000000E+03   0.6000000E+03

     T O T A L   E F F E C T I V E   M A S S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

          0.1000000E+01   0.1000000E+01   0.1000000E+01   0.5000000E+03   0.5000000E+03   0.5000000E+03
"""


def test_la_massa_modale_si_legge_dai_due_totali_del_dat(tmp_path):
    """`ccx` scrive la riga `TOTAL` della massa modale efficace -- la somma sui
    modi **estratti** -- e, in un blocco separato, la massa efficace
    **totale**, cioe' quella che tutti i modi insieme potrebbero catturare.
    Il rapporto fra i due e' la grandezza che serve, e finora nessuno leggeva
    ne' l'una ne' l'altra.
    """
    percorso = tmp_path / "prova.dat"
    percorso.write_text(DAT_MASSA_MODALE, encoding="ascii")

    masse = solve.leggi_massa_modale(percorso)

    assert masse["catturata"][:3] == pytest.approx([0.9, 0.9, 0.5])
    assert masse["disponibile"][:3] == pytest.approx([1.0, 1.0, 1.0])
    assert masse["catturata"][3:] == pytest.approx([200.0, 400.0, 600.0])


def test_senza_blocco_modale_la_lettura_rende_none_e_non_zero(tmp_path):
    """Un deck senza passo modale non ha massa catturata **da misurare**.
    Zero significherebbe «i modi non ne catturano», che e' un'altra cosa e
    sarebbe un difetto: stessa distinzione di `controlla_reazioni` su un
    `.dat` senza reazioni.
    """
    percorso = tmp_path / "senza.dat"
    percorso.write_text(DAT_FREQUENZE, encoding="ascii")

    assert solve.leggi_massa_modale(percorso) is None
    esito = solve.controlla_massa_modale(None)
    assert esito["passato"] is False
    assert esito["frazione_minima"] is None


def test_il_verdetto_guarda_la_direzione_peggiore_e_la_nomina(tmp_path):
    """Nove decimi in x e y, meta' in z: il verdetto e' la **peggiore**, non la
    media. Una media coprirebbe una direzione scoperta con due buone, ed e'
    proprio la direzione scoperta a mancare all'analisi.
    """
    percorso = tmp_path / "prova.dat"
    percorso.write_text(DAT_MASSA_MODALE, encoding="ascii")

    esito = solve.controlla_massa_modale(solve.leggi_massa_modale(percorso))

    assert esito["frazione_minima"] == pytest.approx(0.5)
    assert esito["direzione_peggiore"] == "z"
    assert esito["passato"] is False
    assert esito["per_direzione"]["x"] == pytest.approx(0.9)


def test_sopra_soglia_il_verdetto_passa():
    """Controprova: senza, un verdetto che dice sempre «no» supererebbe il
    test qui sopra senza distinguere nulla."""
    masse = {"catturata": [0.95, 0.95, 0.95, 1.0, 1.0, 1.0],
             "disponibile": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]}

    esito = solve.controlla_massa_modale(masse)

    assert esito["passato"] is True
    assert esito["frazione_minima"] == pytest.approx(0.95)


def test_una_direzione_senza_massa_disponibile_non_divide_per_zero():
    """Struttura vincolata lungo un asse: li' non c'e' nulla da catturare, e
    la direzione si dichiara non applicabile invece di rendere un NaN che il
    confronto tratterebbe come «non passato»."""
    masse = {"catturata": [0.95, 0.95, 0.0, 1.0, 1.0, 1.0],
             "disponibile": [1.0, 1.0, 0.0, 1.0, 1.0, 1.0]}

    esito = solve.controlla_massa_modale(masse)

    assert esito["per_direzione"]["z"] is None
    assert esito["passato"] is True
    assert esito["direzione_peggiore"] in ("x", "y")


def test_le_rotazionali_restano_scritte_ma_fuori_dal_verdetto():
    """Hanno unita' diverse -- massa per lunghezza al quadrato -- e il loro
    totale disponibile dipende dal polo scelto, quindi una frazione su quelle
    non e' confrontabile con la stessa soglia. Restano pero' nel resoconto,
    perche' chi legge possa guardarle."""
    masse = {"catturata": [0.95, 0.95, 0.95, 10.0, 20.0, 30.0],
             "disponibile": [1.0, 1.0, 1.0, 1000.0, 1000.0, 1000.0]}

    esito = solve.controlla_massa_modale(masse)

    # le rotazionali catturano l'1-3%: se entrassero nel verdetto, boccerebbero
    assert esito["passato"] is True
    assert esito["rotazionali_catturate"] == pytest.approx([10.0, 20.0, 30.0])
    assert esito["rotazionali_disponibili"] == pytest.approx([1000.0] * 3)


# ---------------------------------------------------------------------------
# #94, #93, #92: il passo a due cifre, il blocco troncato, il caso mancante.
# ---------------------------------------------------------------------------

# Undici passi: dieci statici piu' uno modale. Il deck ci arriva senza sforzo
# -- `abaqus.write_inp` scrive un passo per la gravita', uno per la spinta,
# uno per `CARICO_TOP`, uno per ogni posizionato e uno per ogni distribuito, e
# `carichi.distribuiti` non ha limite in `core.config`.
def _frd_a_undici_passi(record=_record_100cl) -> str:
    """`.frd` a dieci passi statici piu' un modale, nel layout dato.

    Riusabile: l'oracolo di parsing per un deck oltre i nove passi (#95).
    """
    return _frd(
        [(passo, "DISP", False, 1.0, {1: (0.0, 0.0, float(passo))}) for passo in range(1, 11)]
        + [(11, "DISP", True, 21.19324067, {1: (1.0, 0.0, 0.0)})],
        record=record,
    )


@pytest.mark.parametrize("record", [_record_100cl, _record_100cl_allineato])
def test_dal_decimo_passo_in_poi_il_numero_si_legge_intero(tmp_path, record):
    """#94: una sola colonna rende `1` dal passo 10 in poi.

    `etichetta_passo.get` in `risolvi()` attribuirebbe allora i risultati del
    passo 10 al primo caso di carico, in silenzio. Mutazione uccisa: tornare
    a leggere una cifra sola.
    """
    percorso = tmp_path / "undici.frd"
    percorso.write_text(_frd_a_undici_passi(record), encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert [b.passo for b in blocchi] == list(range(1, 12))
    assert [b.modale for b in blocchi] == [False] * 10 + [True]


@pytest.mark.parametrize("record", [_record_100cl, _record_100cl_allineato])
def test_il_marchio_modale_sopravvive_anche_a_un_passo_a_due_cifre(tmp_path, record):
    """#94: con `MODAL` incollato a un numero a due cifre il tipo non deve
    scivolare fuori dalle colonne che lo cercano."""
    percorso = tmp_path / "undici.frd"
    percorso.write_text(_frd_a_undici_passi(record), encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert blocchi[-1].modale is True
    assert blocchi[-1].passo == 11


def test_un_frd_troncato_a_meta_blocco_solleva_invece_di_scartare(tmp_path):
    """#93: un `.frd` tagliato a meta' e' una corsa di `ccx` interrotta --
    solutore ucciso, disco pieno -- cioe' il momento in cui serve saperlo.

    Mutazione uccisa: togliere il confronto fra blocchi aperti e blocchi
    chiusi. Senza, la funzione rende un blocco su due e nessun errore.
    """
    intero = _frd([
        (1, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)}),
        (1, "STRESS", False, 1.0, {1: (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)}),
    ])
    percorso = tmp_path / "troncato.frd"
    percorso.write_text(intero[: intero.rindex(" -3")], encoding="ascii")

    with pytest.raises(ValueError) as errore:
        solve.leggi_frd(percorso)

    messaggio = str(errore.value)
    assert "troncato.frd" in messaggio, "l'errore non nomina il file"
    assert "2" in messaggio and "1" in messaggio, "l'errore non porta i due conteggi"


def test_un_record_100cl_tagliato_nomina_il_file_e_la_riga(tmp_path):
    """Un `100CL` tagliato prima della colonna 62 e' lo stesso incidente di
    #93 -- `ccx` ucciso a meta' scrittura -- visto sul record invece che sul
    blocco: il file va nominato con la stessa cura.

    Mutazione uccisa: `_PASSO_NELLA_CODA.match(coda).group(1)` senza guardia,
    che rende `AttributeError: 'NoneType' object has no attribute 'group'`
    senza dire ne' quale file ne' quale riga.
    """
    intero = _frd([
        (1, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)}),
        (2, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)}),
    ])
    righe = intero.splitlines()
    # Il secondo record 100CL, tagliato a meta': quinta riga del file.
    assert righe[4].startswith("  100CL")
    righe[4] = righe[4][:40]
    percorso = tmp_path / "record_tagliato.frd"
    percorso.write_text("\n".join(righe) + "\n", encoding="ascii")

    with pytest.raises(ValueError) as errore:
        solve.leggi_frd(percorso)

    messaggio = str(errore.value)
    assert "record_tagliato.frd" in messaggio, "l'errore non nomina il file"
    assert "5" in messaggio, "l'errore non nomina la riga"


def test_un_blocco_chiuso_senza_righe_non_e_un_file_troncato(tmp_path):
    """Un blocco aperto da ` -4` e **chiuso** da ` -3` senza righe ` -1` e' un
    blocco vuoto, non un file tagliato: la guardia di #93 non deve accusarlo.

    Mutazione uccisa: contare i blocchi con dati invece delle chiusure
    (`len(blocchi) != aperti`), che dichiara «troncato» un file sano. Una
    guardia che accusa un file integro viene spenta dal primo che ci sbatte
    contro, e con lei se ne va il caso vero che sorvegliava.
    """
    pieno = _frd([(1, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)})])
    vuoto = "\n".join(r for r in pieno.splitlines() if not r.startswith(" -1"))
    percorso = tmp_path / "blocco_vuoto.frd"
    percorso.write_text(vuoto + "\n" + pieno, encoding="ascii")

    blocchi = solve.leggi_frd(percorso)

    assert [b.grandezza for b in blocchi] == ["DISP"]


def test_un_blocco_aperto_e_mai_chiuso_a_meta_file_solleva(tmp_path):
    """Il taglio non e' sempre in coda: un ` -4` seguito da un altro ` -4`
    perde il primo blocco in silenzio, ed e' il caso che il conteggio delle
    aperture prendeva e una guardia sul solo stato finale non prenderebbe."""
    pieno = _frd([
        (1, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)}),
        (2, "DISP", False, 1.0, {1: (1.0, 2.0, 3.0)}),
    ])
    righe = [r for r in pieno.splitlines() if r != " -3"]
    percorso = tmp_path / "meta_file.frd"
    percorso.write_text("\n".join(righe) + "\n -3\n", encoding="ascii")

    with pytest.raises(ValueError) as errore:
        solve.leggi_frd(percorso)

    assert "meta_file.frd" in str(errore.value)


def test_un_frd_senza_blocchi_rende_una_lista_vuota(tmp_path):
    """Zero blocchi non e' un file troncato: nessuna apertura, nessuna
    chiusura mancante. Chi dichiara dei casi di carico e non li ritrova lo
    scopre dal verdetto sui casi mancanti (#92), a valle, dove la lista dei
    casi attesi c'e' -- qui non c'e'."""
    percorso = tmp_path / "vuoto.frd"
    percorso.write_text("    1C\n 9999\n", encoding="ascii")

    assert solve.leggi_frd(percorso) == []


# Un solo caso su due nel `.frd`, e quello presente **passa**: cosi' il
# verdetto d'insieme puo' essere falso solo per il caso mancante, non per il
# caso letto.
_FRD_UN_CASO_SU_DUE = _frd([
    (1, "DISP", False, 1.0, {n: (0.0, 0.0, -1.0) for n in _NODI_STAMPATI}),
    _blocco_stress(1, {3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 100.0}),
])


def test_un_caso_dichiarato_e_assente_dal_frd_boccia_il_picco(tmp_path, monkeypatch):
    """#92: `all()` su un insieme parziale e' `True`, e approva quel che resta.

    Il deck dichiara due casi statici, il `.frd` ne porta uno. Mutazione
    uccisa: aggregare sui soli casi presenti in `picco_per_caso`.
    """
    esito = _risolvi_finto(
        tmp_path, monkeypatch, _FRD_UN_CASO_SU_DUE,
        casi=["GRAVITA", "SPINTA_ORIZZONTALE"], trasformata=np.eye(4),
        nodi=_NODI_COLONNA, elementi=_ELEMENTI_COLONNA,
    )

    picco = esito["controlli"]["picco"]
    assert picco["per_caso"]["GRAVITA"]["passato"] is True
    assert picco["casi_mancanti"] == ["SPINTA_ORIZZONTALE"]
    assert picco["passato"] is False, "un caso non letto non e' un caso superato"


def test_risolvi_non_scrive_i_verdetti_a_mano_ma_li_prende_dalla_tabella(
    tmp_path, monkeypatch
):
    """Finché `risolvi` scrive i sette a mano, la tabella è un commento lungo:
    nessun chiamante di produzione la attraversa. Dichiarare `picco` non
    applicabile sul solido deve quindi bastare a spegnerlo, senza toccare
    `risolvi`."""
    monkeypatch.setitem(
        solve.CONTROLLI_PER_MODELLO["picco"], "solido", "non vale: prova della tabella"
    )

    esito = _risolvi_finto(
        tmp_path, monkeypatch, _FRD_UN_CASO_SU_DUE,
        casi=["GRAVITA", "SPINTA_ORIZZONTALE"], trasformata=np.eye(4),
        nodi=_NODI_COLONNA, elementi=_ELEMENTI_COLONNA,
    )

    assert set(esito["controlli"]) == set(solve.CONTROLLI_PER_MODELLO)
    assert esito["controlli"]["picco"]["applicabile"] is False
    assert esito["controlli"]["picco"]["passato"] is False
    assert "applicabile" not in esito["controlli"]["reazioni"]


# --- La tabella controllo x modello (#138 Q3) ---------------------------------
#
# L'elenco dei sette non e' scritto a mano qui: si ricava dalle funzioni
# `controlla_*` del modulo. Chi ne aggiunge un ottavo senza dichiararlo nella
# tabella fa cadere questo test, che e' il punto: la tabella va scritta prima
# del controllo, non dedotta dopo.
def _i_sette_controlli() -> set[str]:
    return {
        nome[len("controlla_"):]
        for nome in dir(solve)
        if nome.startswith("controlla_") and callable(getattr(solve, nome))
    }


def test_la_tabella_copre_i_sette_controlli_su_ogni_modello():
    assert len(_i_sette_controlli()) == 7, _i_sette_controlli()
    assert set(solve.CONTROLLI_PER_MODELLO) == _i_sette_controlli()
    for controllo, per_modello in solve.CONTROLLI_PER_MODELLO.items():
        assert set(per_modello) == set(solve.MODELLI), controllo


def test_ogni_casella_o_vale_o_porta_il_motivo_per_cui_non_vale():
    """«non vale» senza una ragione e' un'omissione, non una dichiarazione."""
    for controllo, per_modello in solve.CONTROLLI_PER_MODELLO.items():
        for modello, verdetto in per_modello.items():
            if verdetto == "vale":
                continue
            assert verdetto.startswith("non vale: "), (controllo, modello, verdetto)
            assert len(verdetto) > len("non vale: ") + 20, (controllo, modello)


def test_un_controllo_che_vale_non_ha_esito_di_non_applicabilita():
    assert solve.esito_non_applicabile("reazioni", "solido") is None


def test_un_controllo_che_non_vale_e_dichiarato_e_mai_verde():
    esito = solve.esito_non_applicabile("picco", "telaio")
    assert esito is not None
    assert esito["passato"] is False
    assert esito["applicabile"] is False
    assert esito["motivo"].startswith("non vale: ")


def test_i_sette_verdetti_di_un_modello_escono_tutti_dalla_tabella():
    """Il consumatore porta i **calcoli**, non i verdetti: quali girino lo
    decide la tabella, e i due che sul telaio non valgono non vengono nemmeno
    chiamati."""
    chiamati: list[str] = []

    def calcolo(nome):
        def esegui():
            chiamati.append(nome)
            return {"passato": True, "chi": nome}
        return esegui

    verdetti = solve.verdetti_per_modello(
        "telaio",
        {n: calcolo(n) for n in ("reazioni", "autovalori", "avvisi",
                                 "spostamenti", "massa_modale")},
    )

    assert set(verdetti) == set(solve.CONTROLLI_PER_MODELLO)
    assert sorted(chiamati) == ["autovalori", "avvisi", "massa_modale",
                                "reazioni", "spostamenti"]
    assert verdetti["reazioni"] == {"passato": True, "chi": "reazioni"}
    assert verdetti["picco"]["applicabile"] is False
    assert verdetti["vincolo_in_pianta"]["applicabile"] is False


def test_un_verdetto_scritto_a_mano_su_un_controllo_che_non_vale_e_rifiutato():
    """Il difetto misurato: su una mensola `abaqus.constraint_plan_extent` rende
    `minimo = 1,0` -- il ramo di guardia del denominatore nullo, perche' i nodi
    stanno tutti su una verticale -- e `controlla_vincolo_in_pianta(1,0)` dice
    `passato: True`, mentre la tabella dice `applicabile: False`. Chi scrivesse
    i sette verdetti a mano otterrebbe quel verde."""
    nodi = np.column_stack([np.zeros(5), np.zeros(5), np.linspace(0.0, 2000.0, 5)])
    estensione = abaqus.constraint_plan_extent(nodi, np.array([0]))
    assert estensione["minimo"] == 1.0
    assert solve.controlla_vincolo_in_pianta(estensione["minimo"])["passato"] is True

    verdetti = solve.verdetti_per_modello(
        "telaio",
        {
            "vincolo_in_pianta": lambda: solve.controlla_vincolo_in_pianta(
                estensione["minimo"]
            ),
            "reazioni": lambda: {"passato": True},
            "autovalori": lambda: {"passato": True},
            "avvisi": lambda: {"passato": True},
            "spostamenti": lambda: {"passato": True},
            "massa_modale": lambda: {"passato": True},
        },
    )

    assert verdetti["vincolo_in_pianta"]["passato"] is False
    assert verdetti["vincolo_in_pianta"]["applicabile"] is False
    assert "minimo" not in verdetti["vincolo_in_pianta"], "il calcolo non va eseguito"


def test_un_controllo_applicabile_senza_il_suo_calcolo_e_rifiutato():
    """Sette meno uno non e' sei verdetti: e' un verdetto perso in silenzio."""
    with pytest.raises(KeyError, match="massa_modale"):
        solve.verdetti_per_modello(
            "telaio",
            {n: (lambda: {"passato": True})
             for n in ("reazioni", "autovalori", "avvisi", "spostamenti")},
        )


def test_un_calcolo_per_un_controllo_inesistente_e_rifiutato():
    with pytest.raises(KeyError, match="ottavo_controllo"):
        solve.verdetti_per_modello("solido", {"ottavo_controllo": lambda: {}})


def test_un_modello_sconosciuto_non_produce_verdetti():
    with pytest.raises(KeyError, match="guscio"):
        solve.verdetti_per_modello("guscio", {})


def test_un_controllo_o_un_modello_sconosciuto_solleva_invece_di_tacere():
    """Un refuso non deve valere «vale»: sarebbe un verde su nulla."""
    with pytest.raises(KeyError, match="ottavo_controllo"):
        solve.esito_non_applicabile("ottavo_controllo", "solido")
    with pytest.raises(KeyError, match="guscio"):
        solve.esito_non_applicabile("picco", "guscio")


# --- Percorso dichiarabile, disponibilita' e verifica (#139, #144) ------------
#
# `config.SolutoreConfig` lo scrive l'onda 0 e qui non c'e' ancora: il blocco
# ha forma `nome: Literal["calculix", "opensees"]` piu' `percorso: Path | None`,
# e il codice sotto prova e' scritto contro quella forma. Il sostituto ha gli
# stessi due campi e nient'altro -- se l'onda 0 ne aggiunge un terzo, il codice
# non lo legge e questi test restano validi.
class _SolutoreFinto(NamedTuple):
    nome: str = "calculix"
    percorso: Path | None = None


def test_senza_percorso_dichiarato_il_solutore_si_cerca_nel_path(monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda nome: f"/usr/bin/{nome}")

    assert solve.eseguibile(_SolutoreFinto(nome="calculix")) == Path("/usr/bin/ccx")


def test_un_percorso_dichiarato_e_inesistente_non_ripiega_sul_path(tmp_path, monkeypatch):
    """Il ripiego silenzioso è il difetto: l'utente crede di usare il proprio
    binario e ne usa un altro."""
    monkeypatch.setattr(solve.shutil, "which", lambda nome: f"/usr/bin/{nome}")
    inesistente = tmp_path / "non_c_e" / "ccx"

    assert solve.eseguibile(_SolutoreFinto(percorso=inesistente)) is None

    stato = solve.disponibilita(_SolutoreFinto(percorso=inesistente))
    assert stato["calculix"]["disponibile"] is False
    assert str(inesistente) in stato["calculix"]["motivo"]


def test_un_percorso_con_spazi_e_accenti_si_cita_per_intero(tmp_path, monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)
    cartella = tmp_path / "Program Files" / "città"
    cartella.mkdir(parents=True)
    binario = cartella / "OpenSees.exe"
    binario.write_text("finto", encoding="utf-8")

    cfg = _SolutoreFinto(nome="opensees", percorso=binario)
    assert solve.eseguibile(cfg) == binario
    stato = solve.disponibilita(cfg)
    assert stato["opensees"]["percorso"] == str(binario)
    assert stato["opensees"]["origine"] == "dichiarato"


def test_il_solutore_assente_e_non_scelto_non_e_un_difetto(monkeypatch):
    """Chi usa solo CalculiX non deve vedere OpenSees come un errore."""
    monkeypatch.setattr(
        solve.shutil, "which", lambda nome: "/usr/bin/ccx" if nome == "ccx" else None
    )

    stato = solve.disponibilita(_SolutoreFinto(nome="calculix"))

    assert stato["calculix"] == {
        "disponibile": True, "percorso": "/usr/bin/ccx", "origine": "PATH",
        "scelto": True, "motivo": None,
        "dove_prenderlo": solve.DOVE_PRENDERLO["calculix"],
    }
    assert stato["opensees"]["disponibile"] is False
    assert stato["opensees"]["scelto"] is False
    assert stato["opensees"]["dove_prenderlo"] == solve.DOVE_PRENDERLO["opensees"]


def test_nessuno_dei_due_installato_si_elenca_e_non_solleva(monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)

    stato = solve.disponibilita(None)

    assert set(stato) == {"calculix", "opensees"}
    assert not any(voce["disponibile"] for voce in stato.values())
    assert not any(voce["scelto"] for voce in stato.values())
    for nome, voce in stato.items():
        assert solve.DOVE_PRENDERLO[nome] in voce["dove_prenderlo"]


def test_un_solutore_sconosciuto_solleva_invece_di_dirsi_assente():
    with pytest.raises(KeyError, match="ansys"):
        solve.disponibilita(_SolutoreFinto(nome="ansys"))


def test_la_verifica_di_un_solutore_assente_lo_dichiara_senza_eseguire(monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)

    def mai(*_a, **_k):
        raise AssertionError("nessun processo va avviato se il binario non c'è")

    monkeypatch.setattr(solve.subprocess, "run", mai)

    esito = solve.verifica(_SolutoreFinto(nome="opensees"))
    assert esito["disponibile"] is False
    assert esito["funziona"] is False
    assert solve.DOVE_PRENDERLO["opensees"] in esito["motivo"]


class _Processo(NamedTuple):
    returncode: int
    stdout: bytes
    stderr: bytes


def _finge(monkeypatch, processo, *, esiste="/usr/bin/ccx"):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: esiste)
    visti: dict[str, object] = {}

    def finto(comando, **kwargs):
        visti["comando"] = comando
        visti["kwargs"] = kwargs
        return processo

    monkeypatch.setattr(solve.subprocess, "run", finto)
    return visti


def test_il_codice_201_di_ccx_non_boccia_la_verifica(monkeypatch):
    """9d2f751: `ccx -v` esce 201 e funziona. Il codice non è il segnale."""
    _finge(monkeypatch, _Processo(201, b"\nThis is Version 2.21\n", b""))

    esito = solve.verifica(_SolutoreFinto(nome="calculix"))

    assert esito["funziona"] is True
    assert esito["codice"] == 201
    assert esito["motivo"] is None


def test_un_binario_che_non_e_il_solutore_dichiara_l_uscita_non_riconosciuta(monkeypatch):
    _finge(monkeypatch, _Processo(0, b"GNU bash, version 5.2\n", b""))

    esito = solve.verifica(_SolutoreFinto(nome="calculix"))

    assert esito["funziona"] is False
    assert "non è riconosciuta" in esito["motivo"]
    assert "GNU bash" in esito["motivo"]


def test_un_codice_diverso_da_zero_entra_nel_messaggio_con_la_coda(monkeypatch):
    _finge(monkeypatch, _Processo(127, b"", b"error while loading shared libraries\n"))

    esito = solve.verifica(_SolutoreFinto(nome="calculix"))

    assert esito["funziona"] is False
    assert "127" in esito["motivo"]
    assert "shared libraries" in esito["motivo"]


def test_l_uscita_con_byte_non_decodificabili_si_legge_senza_sollevare(monkeypatch):
    """Stessa scelta di `_righe_dat`: `ignore`, non `replace`."""
    _finge(monkeypatch, _Processo(0, b"This is \xff\xfeVersion 2.21\n", b""))

    esito = solve.verifica(_SolutoreFinto(nome="calculix"))

    assert esito["funziona"] is True
    assert "�" not in esito["uscita"]


def test_opensees_si_verifica_facendogli_eseguire_una_riga(monkeypatch):
    """«C'è» non è «funziona»: un banner stampato non prova che l'interprete giri."""
    visti = _finge(
        monkeypatch,
        _Processo(0, b"Version 3.8.0 64-Bit\nMESHREC_VERIFICA\n", b""),
        esiste="/opt/OpenSees",
    )

    esito = solve.verifica(_SolutoreFinto(nome="opensees"))

    assert esito["funziona"] is True
    assert visti["kwargs"]["input"] == solve._SOLUTORI["opensees"]["ingresso"].encode()


def test_opensees_che_stampa_il_banner_e_non_esegue_e_bocciato(monkeypatch):
    """Misurato il 30/08/2026: OpenSees 3.8.0 esce con codice 0 anche su uno
    script che muore su un errore fatale. Il codice non basta, serve la prova
    che l'interprete abbia eseguito."""
    _finge(
        monkeypatch,
        _Processo(0, b"Version 3.8.0 64-Bit\nTclElementCommand -- unable\n", b""),
        esiste="/opt/OpenSees",
    )

    esito = solve.verifica(_SolutoreFinto(nome="opensees"))

    assert esito["funziona"] is False
    assert "non è riconosciuta" in esito["motivo"]


def test_un_binario_che_non_parte_dichiara_il_perche(monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")

    def esplode(*_a, **_k):
        raise OSError(8, "Exec format error")

    monkeypatch.setattr(solve.subprocess, "run", esplode)

    esito = solve.verifica(_SolutoreFinto(nome="calculix"))
    assert esito["funziona"] is False
    assert "Exec format error" in esito["motivo"]


# --- I nomi dei casi di carico -----------------------------------------------
def test_casi_di_carico_vuoto_si_dichiara():
    with pytest.raises(ValueError, match="vuoto"):
        solve.valida_casi_di_carico([])


def test_due_casi_che_differiscono_solo_per_maiuscole_sono_rifiutati():
    """`ccx` risolve i nomi senza distinguere il caso
    (docs/fase-6-cantiere/sonda-caso-nomi/)."""
    with pytest.raises(ValueError, match="GRAVITA"):
        solve.valida_casi_di_carico(["GRAVITA", "Gravita"])


def test_casi_distinti_passano_e_tornano_indietro():
    casi = ["GRAVITA", "SPINTA_ORIZZONTALE", "MODALE"]
    assert solve.valida_casi_di_carico(casi) == casi


def test_risolvi_rifiuta_i_casi_omonimi_prima_di_avviare_il_solutore(tmp_path, monkeypatch):
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")

    def mai(*_a, **_k):
        raise AssertionError("il solutore non va avviato su casi già rifiutati")

    monkeypatch.setattr(solve.subprocess, "run", mai)

    with pytest.raises(ValueError, match="maiuscole"):
        solve.risolvi(
            tmp_path, tmp_path / "m.inp", ANALISI,
            np.zeros((1, 3)), np.zeros((1, 4), dtype=np.int64), "C3D4",
            casi_di_carico=["GRAVITA", "gravita"],
            vincolo_in_pianta={"minimo": 1.0}, trasformata=np.eye(4),
        )


def test_risolvi_usa_il_percorso_dichiarato_invece_del_path(tmp_path, monkeypatch):
    """Il percorso dichiarato mancava a `risolvi`, che cercava solo nel PATH (#139)."""
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx_del_path")
    dichiarato = tmp_path / "mio_ccx"
    dichiarato.write_text("finto", encoding="utf-8")
    visti: list[str] = []

    def finto(comando, **_kwargs):
        visti.append(comando[0])
        raise RuntimeError("basta il comando")

    monkeypatch.setattr(solve.subprocess, "run", finto)

    with pytest.raises(RuntimeError, match="basta il comando"):
        solve.risolvi(
            tmp_path, tmp_path / "m.inp", ANALISI,
            np.zeros((1, 3)), np.zeros((1, 4), dtype=np.int64), "C3D4",
            casi_di_carico=["GRAVITA"], vincolo_in_pianta={"minimo": 1.0},
            trasformata=np.eye(4),
            solutore=_SolutoreFinto(nome="calculix", percorso=dichiarato),
        )

    assert visti == [str(dichiarato)]


def test_risolvi_rifiuta_opensees_invece_di_eseguirlo_come_fosse_ccx(
    tmp_path, monkeypatch
):
    """`risolvi` monta la riga di comando di CalculiX e legge il `.frd`.

    Misurato il 30/08/2026 su questa macchina: `OpenSees.exe -i m` stampa il
    banner ed esce con codice **0**, quindi la guardia sul codice d'uscita
    passa e il fallimento arriva dopo, come un `FileNotFoundError` nudo su un
    `.frd` mai scritto, con un messaggio che parla di «ccx». Si rifiuta prima,
    dicendo chi porta l'altro solutore.
    """
    binario = tmp_path / "OpenSees"
    binario.write_text("finto", encoding="utf-8")

    def mai(*_a, **_k):
        raise AssertionError("nessun processo va avviato per un solutore che risolvi non esegue")

    monkeypatch.setattr(solve.subprocess, "run", mai)

    with pytest.raises(ValueError, match="core/opensees.py"):
        solve.risolvi(
            tmp_path, tmp_path / "m.inp", ANALISI,
            np.zeros((1, 3)), np.zeros((1, 4), dtype=np.int64), "C3D4",
            casi_di_carico=["GRAVITA"], vincolo_in_pianta={"minimo": 1.0},
            trasformata=np.eye(4),
            solutore=_SolutoreFinto(nome="opensees", percorso=binario),
        )

    assert not (tmp_path / "13_solution.vtu").exists()


def test_risolvi_col_solutore_assente_non_scrive_niente(tmp_path, monkeypatch):
    """CalculiX scelto e non installato: si esce senza artefatti. Il rimedio lo
    dice `meshrec dottore`, che nomina da dove prenderlo."""
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: None)

    esito = solve.risolvi(
        tmp_path, tmp_path / "m.inp", ANALISI,
        np.zeros((1, 3)), np.zeros((1, 4), dtype=np.int64), "C3D4",
        casi_di_carico=["GRAVITA"], vincolo_in_pianta={"minimo": 1.0},
        trasformata=np.eye(4), solutore=_SolutoreFinto(nome="calculix"),
    )

    assert esito == {"eseguito": False, "solutore": "assente"}
    assert not (tmp_path / "13_solution.vtu").exists()


def test_un_percorso_dichiarato_e_sbagliato_non_esce_muto(tmp_path, monkeypatch):
    """«assente» da solo non distingue un solutore non installato da un
    percorso dichiarato male, e i due rimedi sono opposti."""
    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    sbagliato = tmp_path / "questo" / "non" / "esiste"

    esito = solve.risolvi(
        tmp_path, tmp_path / "m.inp", ANALISI,
        np.zeros((1, 3)), np.zeros((1, 4), dtype=np.int64), "C3D4",
        casi_di_carico=["GRAVITA"], vincolo_in_pianta={"minimo": 1.0},
        trasformata=np.eye(4),
        solutore=_SolutoreFinto(percorso=sbagliato),
    )

    assert esito["solutore"] == "assente"
    assert str(sbagliato) in esito["motivo"]
    assert "non ripiega sul PATH" in esito["motivo"]


def test_un_percorso_con_spazi_arriva_al_processo_come_un_argomento_solo(
    tmp_path, monkeypatch
):
    """Nessuna shell di mezzo: il comando è una lista, e un percorso con spazi
    resta un argomento. Con una riga di comando montata a stringa,
    `Program Files` diventerebbe due argomenti e il messaggio d'errore
    accuserebbe un file che nessuno ha nominato."""
    cartella = tmp_path / "Program Files" / "città"
    cartella.mkdir(parents=True)
    binario = cartella / "ccx"
    binario.write_text("finto", encoding="utf-8")
    visti = _finge(monkeypatch, _Processo(0, b"This is Version 2.21\n", b""))

    solve.verifica(_SolutoreFinto(percorso=binario))

    assert visti["comando"] == [str(binario), "-v"]
