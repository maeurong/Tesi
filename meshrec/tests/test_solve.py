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
        vincolo_in_pianta={"x": 1.0, "y": 1.0, "minimo": 1.0},
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
    deck.with_suffix(".frd").write_text(FRD_QUATTRO_PASSI, encoding="ascii")
    deck.with_suffix(".dat").write_text(DAT_DUE_MODI, encoding="ascii")

    import subprocess

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(
        solve.subprocess, "run",
        lambda comando, **kwargs: subprocess.CompletedProcess(comando, returncode=0, stdout="", stderr=""),
    )

    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    elementi = np.array([[0, 1, 2, 3]])

    un_piede = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 0.32, "minimo": 0.32},
    )
    assert not un_piede["controlli"]["vincolo_in_pianta"]["passato"], "0,32 e' sotto 0,5: non citabile"

    lab_crop = solve.risolvi(
        tmp_path, deck, ANALISI, nodi, elementi, "C3D4", casi_di_carico=casi_di_carico,
        vincolo_in_pianta={"x": 1.0, "y": 0.987, "minimo": 0.987},
    )
    assert lab_crop["controlli"]["vincolo_in_pianta"]["passato"]


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


def test_controlla_autovalori_con_una_frequenza_infinita_non_passa():
    """Bug reale trovato nella revisione (Task 7, terzo giro), applicando la
    stessa domanda posta a `controlla_picco` agli altri controlli: prima del
    fix, `inf` come prima frequenza passava (`inf > 0.0` e' vero, e
    `inf / seconda >= soglia_relativa` pure, essendo `inf` maggiore di
    qualunque soglia finita). La regola generale (ingressi non finiti ->
    `passato` sempre `False`) chiude anche questo caso, non solo quello di
    `controlla_picco` dove il revisore l'ha trovato.
    """
    assert not solve.controlla_autovalori([float("inf"), 21.19])["passato"]
    assert not solve.controlla_autovalori([float("inf")])["passato"]


def test_il_picco_di_tensione_dentro_la_banda_di_vincolo_e_un_artefatto():
    """Il numero piu' citabile e' il piu' facile da fraintendere.

    Misurato il 21/08/2026 sull'as-built col vincolo corretto: sotto peso
    proprio il rapporto max/p99 vale 2,16 e nessuno dei 142 nodi sopra il p99
    cade entro la banda di vincolo -- il picco sta a z 2286 mm, non
    sull'incastro. Il controllo non e' che il picco sia basso: e' che si sappia
    dove sta.
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


def test_controlla_reazioni_con_reazione_nan_non_passa():
    """Verifica (Task 7, terzo giro, stessa domanda posta a tutti i
    controlli): qui non serve una guardia in piu'. Un NaN in `reazioni`
    propaga in `scarto` (via `norm`), e `scarto <= tolleranza` e' gia' falso
    per costruzione con `scarto` NaN -- a differenza di `controlla_picco`,
    il verdetto finale e' un confronto di grandezza, non una combinazione
    booleana che un confronto-con-NaN puo' mascherare da esito buono.
    """
    reazioni = {1: (0.0, 0.0, float("nan")), 2: (0.0, 0.0, 500.0)}
    esito = solve.controlla_reazioni(reazioni, peso_atteso=(0.0, 0.0, 1000.0), tolleranza=0.02)
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


def test_controlla_picco_con_nan_a_monte_non_passa():
    """Rilievo Important della revisione (Task 7, terzo giro): il Minor M3
    del giro precedente guardava solo `np.isnan(p99)` per proteggere
    `rapporto_max_p99`, e sembrava chiudere il buco -- ma non toccava
    `passato`. Con `p99` NaN, `sopra_p99 = v >= p99` da' tutto `False` (ogni
    confronto con NaN e' falso), `frazione_in_banda` esce 0.0, e il verdetto
    diceva "va bene" esattamente sul dato corrotto (dimostrato dal
    revisore: `{'passato': True, 'max': nan, ...}`). La regola giusta e'
    generale: ingressi non finiti -> `passato` sempre `False`. Il valore
    resta comunque riportato (si marca, non si nasconde).
    """
    valori = np.array([1.0, np.nan, 3.0, 4.0])
    quote = np.array([0.0, 10.0, 20.0, 30.0])

    esito = solve.controlla_picco(valori, quote, banda=100.0)

    assert esito["passato"] is False
    assert esito["rapporto_max_p99"] is None
    assert math.isnan(esito["max"])


def test_controlla_picco_con_banda_nan_su_valori_sani_non_passa():
    """Giro di correzione 4: `banda` raggiunge un confronto (`q <= q.min() +
    banda`) tanto quanto `valori`/`quote`, e non era nel cancello di
    finitezza -- il revisore l'ha trovato con valori e quote perfettamente
    sani: `banda` NaN da' `in_banda` tutto `False` (stesso schema del giro
    3), `frazione_in_banda` esce 0.0, il verdetto passa. E' un percorso
    reale: `banda_vincolo` in `risolvi()` e' una frazione dell'altezza di
    *tutti* i nodi del modello, non del sottoinsieme (`quote`) del caso di
    carico corrente -- un nodo NaN altrove nel modello corrompe `banda`
    senza toccare `valori`/`quote` di questo caso.
    """
    valori = np.array([1.0, 2.0, 3.0, 4.0])
    quote = np.array([0.0, 10.0, 20.0, 30.0])

    esito = solve.controlla_picco(valori, quote, banda=float("nan"))

    assert esito["passato"] is False



# ---------------------------------------------------------------------------
# Indagine 21/08/2026 (giro di correzione del Task 7): da dove viene lo
# scarto reazioni/peso di `_TOLLERANZA_REAZIONI`. Non era rumore di mesh:
# vedi il commento sopra `_TOLLERANZA_REAZIONI` in solve.py e il docstring
# di `_quota_tributaria_gravita`. Le prime due fixture/test sono presi cosi'
# come sono dal worktree del debugger (non riscritti); il terzo e' adattato
# per essere l'oracolo giusto dopo il fix, non restare rosso.
# ---------------------------------------------------------------------------


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
    quota_tributaria_massa = solve._quota_tributaria_gravita(nodes, tets, reazioni, densita)

    assert somma_z + quota_tributaria_massa * gravita == pytest.approx(peso_atteso_z, rel=1e-6)
