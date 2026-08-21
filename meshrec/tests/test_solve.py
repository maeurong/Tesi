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

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
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
        tmp_path, tmp_path / "assente.inp", ANALISI, nodi, elementi, "C3D4"
    )

    assert esito == {"eseguito": False, "solutore": "assente"}
    assert not (tmp_path / "13_solution.vtu").exists()


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
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico
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
    """
    from meshrec.core.config import TetConfig

    vertices, faces = synth.box_mesh((100.0, 100.0, 100.0))
    nodi, elementi = volume.tetrahedralize(
        vertices, faces, max_volume=20_000.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False
    )
    carichi = CarichiConfig(
        spinta=SpintaOrizzontale(coefficiente=0.1, asse="x"),
        carico_sommita=CaricoSommita(risultante=1000.0, nset="TOP"),
        modale=Modale(modi=2),
    )
    esito = abaqus.export_model(
        tmp_path / "prova.inp", tmp_path / "prova.vtu", nodi, elementi,
        ANALISI, TetConfig(), carichi=carichi,
    )

    testo = (tmp_path / "prova.inp").read_text(encoding="ascii")
    ordine_reale = [
        riga.split(": ", 1)[1]
        for riga in testo.splitlines()
        if riga.startswith("** NOME PASSO: ")
    ]

    assert esito["casi_di_carico"] == ordine_reale
