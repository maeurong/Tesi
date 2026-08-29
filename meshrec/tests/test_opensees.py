"""Test di `meshrec.core.opensees`: lo scrittore del `.tcl` e il lettore delle uscite.

**Il telaio di prova e' un sostituto, e va detto perche'.** `core/telaio.py` lo
scrive il ramo D dell'onda 3 e qui non c'e' ancora: le classi `_Telaio`,
`_Elemento`, `_Sezione`, `_Barra` sotto hanno **esattamente** i campi che il
documento di sequenziamento dichiara in §4.7 e §4.4, e nient'altro. Lo
scrittore legge solo quei campi, quindi il giorno in cui `core/telaio.py`
arriva i suoi oggetti veri passano di qui senza che nulla cambi -- e se D
dichiarasse un campo diverso, questi test resterebbero verdi mentre il
programma vero cadrebbe. E' il limite di un sostituto, ed e' scritto qui
perche' chi lo rilegge lo sappia.

I fatti su OpenSees che questi test danno per veri sono misurati il 30/08/2026
eseguendo `OpenSees` 3.8.0 su questa macchina, non letti dal manuale. Il test
che li rimisura contro il binario vero e' in fondo, marcato `feasibility`.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest

from meshrec.core import config, opensees

CALCESTRUZZO = config.Material(name="C25_30", young=31_476.0, poisson=0.2, density=2.5e-9)
ACCIAIO = config.Material(name="B450C", young=210_000.0, poisson=0.3, density=7.85e-9)


class _Barra(NamedTuple):
    y: float
    z: float
    diametro: float


class _Elemento(NamedTuple):
    membratura: int
    stazione: int
    nodo_i: int
    nodo_j: int
    sezione: tuple[float, float]
    e1: np.ndarray
    e2: np.ndarray
    barre: list[_Barra]
    riempimento_sezione: float = 1.0


class _Dichiarato(NamedTuple):
    material: config.Material


class _Sezione(NamedTuple):
    calcestruzzo_confinato: _Dichiarato
    calcestruzzo_copriferro: _Dichiarato
    acciaio: _Dichiarato


class _Telaio(NamedTuple):
    nodi: np.ndarray
    elementi: list[_Elemento]
    giunzioni: list[dict[str, object]]
    materiali: dict[int, _Sezione]


SEZIONE = _Sezione(
    calcestruzzo_confinato=_Dichiarato(CALCESTRUZZO),
    calcestruzzo_copriferro=_Dichiarato(CALCESTRUZZO),
    acciaio=_Dichiarato(ACCIAIO),
)

# Quattro barre da 16 mm agli angoli di una sezione 300 x 200, copriferro 40.
BARRE = [
    _Barra(y=-110.0, z=-60.0, diametro=16.0),
    _Barra(y=110.0, z=-60.0, diametro=16.0),
    _Barra(y=-110.0, z=60.0, diametro=16.0),
    _Barra(y=110.0, z=60.0, diametro=16.0),
]


def _mensola(stazioni: int = 4, altezza: float = 2000.0) -> _Telaio:
    """Una mensola verticale, `stazioni` elementi in fila, incastrata al piede."""
    quote = np.linspace(0.0, altezza, stazioni + 1)
    nodi = np.column_stack([np.zeros_like(quote), np.zeros_like(quote), quote])
    elementi = [
        _Elemento(
            membratura=0, stazione=i, nodo_i=i, nodo_j=i + 1,
            sezione=(300.0, 200.0),
            e1=np.array([1.0, 0.0, 0.0]), e2=np.array([0.0, 1.0, 0.0]),
            barre=list(BARRE),
        )
        for i in range(stazioni)
    ]
    return _Telaio(nodi=nodi, elementi=elementi, giunzioni=[], materiali={0: SEZIONE})


# --- Lo scrittore rifiuta invece di scrivere un file che OpenSees rifiuta -----
def test_un_telaio_senza_elementi_non_si_scrive(tmp_path):
    vuoto = _Telaio(nodi=np.zeros((2, 3)), elementi=[], giunzioni=[], materiali={})

    with pytest.raises(ValueError, match="nessun elemento"):
        opensees.scrivi_tcl(tmp_path / "m.tcl", vuoto, casi_di_carico=["GRAVITA"])
    assert not (tmp_path / "m.tcl").exists()


def test_un_telaio_con_un_solo_nodo_non_si_scrive(tmp_path):
    solo = _mensola()._replace(nodi=np.zeros((1, 3)))

    with pytest.raises(ValueError, match="un nodo solo"):
        opensees.scrivi_tcl(tmp_path / "m.tcl", solo, casi_di_carico=["GRAVITA"])


def test_un_telaio_tutto_su_una_quota_non_ha_nodi_liberi(tmp_path):
    """Se il piede prende tutto, non resta niente da calcolare: si dice, non si
    lancia il solutore su un modello interamente vincolato."""
    piatto = _mensola()
    piatto = piatto._replace(nodi=np.zeros_like(piatto.nodi))

    with pytest.raises(ValueError, match="nessun nodo libero"):
        opensees.scrivi_tcl(tmp_path / "m.tcl", piatto, casi_di_carico=["GRAVITA"])


def _due_colonne(quota_secondo_piede: float = 0.0) -> _Telaio:
    """Due colonne alte 2000 mm, i due piedi alle quote 0 e `quota_secondo_piede`."""
    nodi = np.array(
        [
            [0.0, 0.0, 0.0], [1000.0, 0.0, quota_secondo_piede],
            [0.0, 0.0, 2000.0], [1000.0, 0.0, 2000.0],
        ]
    )
    elementi = [
        _Elemento(
            membratura=0, stazione=i, nodo_i=i, nodo_j=i + 2,
            sezione=(300.0, 200.0),
            e1=np.array([1.0, 0.0, 0.0]), e2=np.array([0.0, 1.0, 0.0]),
            barre=list(BARRE),
        )
        for i in range(2)
    ]
    return _Telaio(nodi=nodi, elementi=elementi, giunzioni=[], materiali={0: SEZIONE})


@pytest.mark.parametrize("valore", [float("nan"), float("inf")])
def test_un_nodo_con_coordinata_non_finita_non_si_scrive(tmp_path, valore):
    """Misurato prima della guardia, con `z = NaN` sul secondo nodo: il minimo
    delle quote esce `NaN`, ogni confronto contro `NaN` e' falso, e l'insieme
    dei piedi resta **vuoto**. Il `.tcl` usciva con zero righe `fix`, un
    `node 2 0 0 nan`, e un resoconto che dichiarava `nodi_vincolati = 0` e
    `peso_proprio = nan` senza che nulla si fermasse.

    E' la stessa guardia che `abaqus.build_node_sets` porta gia', per la stessa
    ragione: la' i set di faccia uscivano vuoti, qui i vincoli.
    """
    telaio = _mensola()
    nodi = telaio.nodi.copy()
    nodi[1, 2] = valore

    with pytest.raises(ValueError, match="non finit"):
        opensees.scrivi_tcl(
            tmp_path / "m.tcl", telaio._replace(nodi=nodi), casi_di_carico=["GRAVITA"]
        )
    assert not (tmp_path / "m.tcl").exists()


def test_due_piedi_quasi_complanari_sono_incastrati_tutti_e_due(tmp_path):
    """I nodi del telaio vengono da una **stima del prior**, non da un disegno:
    due piedi che il disegno vuole complanari escono a quote vicine e non
    uguali. Con la tolleranza assoluta di 1e-6 mm che questo modulo portava,
    quote 0,0 e 1e-5 davano **un solo** piede incastrato e un telaio che
    penzola -- il difetto misurato il 21/08/2026 che `constraint_plan_extent`
    esiste per catturare, e che sul telaio nessuno dei sette verdetti vede,
    perche' li' quel controllo e' dichiarato non applicabile.
    """
    resoconto = opensees.scrivi_tcl(
        tmp_path / "m.tcl", _due_colonne(1e-5), casi_di_carico=["GRAVITA"]
    )

    assert resoconto["nodi_vincolati"] == 2
    fix = [r.split()[1] for r in (tmp_path / "m.tcl").read_text().splitlines()
           if r.startswith("fix ")]
    assert fix == ["1", "2"]


def test_un_piede_piu_alto_della_tolleranza_resta_libero(tmp_path):
    """La tolleranza e' relativa all'altezza, non larga: una colonna che parte
    un metro piu' su e' un'altra cosa da un piede, e non si incastra."""
    resoconto = opensees.scrivi_tcl(
        tmp_path / "m.tcl", _due_colonne(1000.0), casi_di_carico=["GRAVITA"]
    )

    assert resoconto["nodi_vincolati"] == 1


def test_casi_di_carico_vuoto_non_produce_un_file_muto(tmp_path):
    with pytest.raises(ValueError, match="vuoto"):
        opensees.scrivi_tcl(tmp_path / "m.tcl", _mensola(), casi_di_carico=[])
    assert not (tmp_path / "m.tcl").exists()


def test_due_casi_che_differiscono_solo_per_maiuscole_sono_rifiutati(tmp_path):
    """Non e' solo la regola di `ccx`: qui i nomi diventano nomi di file, e su
    un filesystem che non distingue il caso il secondo caso sovrascriverebbe le
    uscite del primo."""
    with pytest.raises(ValueError, match="maiuscole"):
        opensees.scrivi_tcl(
            tmp_path / "m.tcl", _mensola(), casi_di_carico=["GRAVITA", "Gravita"]
        )


def test_il_primo_caso_col_nome_di_un_altra_azione_non_diventa_gravita(tmp_path):
    """Misurato prima della guardia: `casi_di_carico=["VENTO"]` scriveva un
    pattern di **gravità** e le uscite uscivano etichettate `U_VENTO`. È
    l'etichetta al posto del carico, cioè proprio il falso che il docstring di
    questo modulo dichiara di esistere per impedire.

    `AnalysisConfig.step_name` porta già il nome giusto, e non veniva letto.
    """
    with pytest.raises(ValueError, match="VENTO"):
        opensees.scrivi_tcl(
            tmp_path / "m.tcl", _mensola(), casi_di_carico=["VENTO"]
        )
    assert not (tmp_path / "m.tcl").exists()


def test_il_nome_del_peso_proprio_e_quello_che_AnalysisConfig_dichiara(tmp_path):
    """Non un secondo «GRAVITA» scritto qui: il predefinito si legge da dove è
    dichiarato, altrimenti i due divergono in silenzio."""
    nome = config.AnalysisConfig.model_fields["step_name"].default

    resoconto = opensees.scrivi_tcl(
        tmp_path / "m.tcl", _mensola(), casi_di_carico=[nome]
    )

    assert resoconto["casi_di_carico"] == [nome]


def test_un_nome_di_peso_proprio_diverso_si_dichiara_e_passa(tmp_path):
    """Chi configura `step_name` porta quel nome fin qui: il caso lo si
    pretende, non lo si indovina dal primo della lista."""
    resoconto = opensees.scrivi_tcl(
        tmp_path / "m.tcl", _mensola(),
        casi_di_carico=["PESO_PROPRIO"], nome_peso_proprio="PESO_PROPRIO",
    )

    assert resoconto["peso_proprio"] > 0.0
    assert "PESO_PROPRIO_spostamenti.out" in (tmp_path / "m.tcl").read_text()


def test_un_caso_senza_carico_dichiarato_si_ferma_e_dice_a_chi_appartiene(tmp_path):
    """Il contratto §4.7 non porta i carichi: `Telaio` ha nodi, elementi,
    giunzioni e materiali, e nient'altro. Scrivere un passo senza carichi
    darebbe spostamenti nulli e sette verdetti verdi su un modello mai
    caricato."""
    with pytest.raises(ValueError, match="SPINTA_ORIZZONTALE"):
        opensees.scrivi_tcl(
            tmp_path / "m.tcl", _mensola(),
            casi_di_carico=["GRAVITA", "SPINTA_ORIZZONTALE"],
        )


# --- Che cosa il .tcl contiene davvero ---------------------------------------
def _scrivi(tmp_path, telaio=None, casi=("GRAVITA",), **extra) -> str:
    percorso = tmp_path / "modello.tcl"
    opensees.scrivi_tcl(percorso, telaio or _mensola(), casi_di_carico=list(casi), **extra)
    return percorso.read_text(encoding="utf-8")


def test_ogni_sezione_a_fibre_porta_il_GJ(tmp_path):
    """Verificato per esecuzione, non per lettura: senza `-GJ` OpenSees 3.8.0
    stampa «WARNING - no torsion specified for 3D fiber section» e lo script
    si ferma alla card della sezione."""
    testo = _scrivi(tmp_path)

    sezioni = [r for r in testo.splitlines() if r.strip().startswith("section Fiber")]
    assert sezioni
    for riga in sezioni:
        assert "-GJ" in riga, riga


def test_ogni_barra_diventa_una_fibra_con_la_propria_area_e_posizione(tmp_path):
    testo = _scrivi(tmp_path)

    fibre = [r.split() for r in testo.splitlines() if r.strip().startswith("fiber ")]
    # quattro barre per ciascuna delle quattro stazioni
    assert len(fibre) == 4 * 4
    area = math.pi * 16.0**2 / 4.0
    for campi in fibre:
        assert float(campi[3]) == pytest.approx(area)
    posizioni = {(float(c[1]), float(c[2])) for c in fibre}
    assert posizioni == {(b.y, b.z) for b in BARRE}


def test_il_calcestruzzo_e_una_patch_sul_rettangolo_misurato(tmp_path):
    testo = _scrivi(tmp_path)

    patch = [r.split() for r in testo.splitlines() if r.strip().startswith("patch rect")]
    assert len(patch) == 4
    for campi in patch:
        assert [float(v) for v in campi[-4:]] == [-150.0, -100.0, 150.0, 100.0]


def test_una_terna_col_verso_di_e1_ribaltato_e_rifiutata(tmp_path):
    """`e1` non compariva nel modulo: l'orientamento veniva tutto da `e2` come
    `vecxz`, e le `y` delle barre assumevano che l'asse locale y che OpenSees
    deriva da (asse, `e2`) -- cioè `e2 x asse` -- coincidesse **in verso** con
    `e1`. Se non coincide la sezione esce specchiata, e con armatura simmetrica
    (il telaio di prova) un ribaltamento non si vede."""
    telaio = _mensola()
    ribaltato = telaio._replace(
        elementi=[e._replace(e1=-np.asarray(e.e1)) for e in telaio.elementi]
    )

    with pytest.raises(ValueError, match="e1"):
        opensees.scrivi_tcl(tmp_path / "m.tcl", ribaltato, casi_di_carico=["GRAVITA"])


def test_con_armatura_asimmetrica_ogni_barra_resta_dalla_propria_parte(tmp_path):
    """L'oracolo che l'armatura simmetrica non può dare: due barre di diametro
    diverso, una per parte. Se la sezione uscisse specchiata, la grossa
    finirebbe dove sta la piccola."""
    barre = [
        _Barra(y=-110.0, z=-60.0, diametro=20.0),
        _Barra(y=110.0, z=-60.0, diametro=12.0),
    ]
    telaio = _mensola()
    telaio = telaio._replace(
        elementi=[e._replace(barre=list(barre)) for e in telaio.elementi]
    )

    testo = _scrivi(tmp_path, telaio)

    fibre = [r.split() for r in testo.splitlines() if r.strip().startswith("fiber ")]
    per_area = {round(float(c[3])): float(c[1]) for c in fibre}
    assert per_area[round(math.pi * 20.0**2 / 4.0)] == -110.0
    assert per_area[round(math.pi * 12.0**2 / 4.0)] == 110.0


def test_il_piede_e_incastrato_e_il_resto_e_libero(tmp_path):
    testo = _scrivi(tmp_path)

    fix = [r.split() for r in testo.splitlines() if r.strip().startswith("fix ")]
    assert [c[0:2] for c in fix] == [["fix", "1"]]
    assert [c[2:] for c in fix] == [["1"] * 6]


def test_il_peso_proprio_e_lo_stesso_di_rho_per_V_per_g(tmp_path):
    """L'oracolo di `controlla_reazioni` e' `rho*V*g`: se la somma dei carichi
    nodali non lo vale, il verdetto boccia un modello sano."""
    testo = _scrivi(tmp_path)

    carichi = [r.split() for r in testo.splitlines() if r.strip().startswith("load ")]
    somma = sum(float(c[4]) for c in carichi)
    volume = 300.0 * 200.0 * 2000.0
    atteso = -volume * CALCESTRUZZO.density * config.GRAVITY_MM_S2
    assert somma == pytest.approx(atteso)


def test_il_blocco_modale_chiede_i_modi_e_la_massa_partecipante(tmp_path):
    testo = _scrivi(tmp_path, casi=("GRAVITA", "MODALE"), modi=6)

    assert "eigen" in testo
    assert "modalProperties" in testo
    assert " 6\n" in testo or " 6 " in testo


def test_senza_caso_modale_non_si_chiedono_autovalori(tmp_path):
    assert "eigen" not in _scrivi(tmp_path)


def test_il_resoconto_conta_quello_che_ha_scritto(tmp_path):
    resoconto = opensees.scrivi_tcl(
        tmp_path / "m.tcl", _mensola(), casi_di_carico=["GRAVITA", "MODALE"]
    )

    assert resoconto["nodi"] == 5
    assert resoconto["elementi"] == 4
    assert resoconto["barre"] == 16
    assert resoconto["nodi_vincolati"] == 1
    assert resoconto["casi_di_carico"] == ["GRAVITA", "MODALE"]
    assert resoconto["tcl"] == str(tmp_path / "m.tcl")


# --- Il lettore delle uscite --------------------------------------------------
def _fine(cartella: Path) -> None:
    """Il marcatore che il `.tcl` scrive in coda, e che il lettore pretende."""
    (cartella / opensees.NOME_FINE).write_text(
        opensees.MARCA_FINE + "\n", encoding="utf-8"
    )


def _scrivi_uscite(cartella: Path, righe_spostamenti: str, righe_forze: str) -> None:
    (cartella / "GRAVITA_spostamenti.out").write_text(righe_spostamenti, encoding="utf-8")
    (cartella / "GRAVITA_forze.out").write_text(righe_forze, encoding="utf-8")
    _fine(cartella)


_SPOSTAMENTI_MENSOLA = " ".join(["0 0 0"] + [f"{i} 0 {-i}" for i in range(1, 5)]) + "\n"
_FORZE_MENSOLA = "\n".join(" ".join(["1"] * 12) for _ in range(1)) + "\n"


def test_le_uscite_assenti_si_dichiarano_invece_di_schiantare(tmp_path):
    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi == {}


def test_gli_spostamenti_diventano_U_del_caso(tmp_path):
    _scrivi_uscite(tmp_path, _SPOSTAMENTI_MENSOLA, " ".join(["1.0"] * 12 * 4) + "\n")

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi["U_GRAVITA"].shape == (5, 3)
    assert campi["U_GRAVITA"][0].tolist() == [0.0, 0.0, 0.0]
    assert campi["U_GRAVITA"][4].tolist() == [4.0, 0.0, -4.0]


def test_le_forze_diventano_N_V_M_per_cella_e_non_per_nodo(tmp_path):
    """#138 Q2: sul telaio le grandezze sono per CELLA. Un campo per nodo dentro
    un `.vtu` di celle sarebbe letto come nodale e mostrato sbagliato.

    Il registratore scrive in coordinate **globali**: l'asse della mensola e'
    z, quindi la terza componente e' l'assiale e le prime due il taglio. Della
    coppia, la componente lungo z e' torsione e resta fuori dal flettente --
    sommarla darebbe un momento gonfiato e plausibile.
    """
    fine_j = ["2.0", "3.0", "-7.0", "5.0", "12.0", "4.0"]
    forze = " ".join((["0"] * 6 + fine_j) * 4) + "\n"
    _scrivi_uscite(tmp_path, _SPOSTAMENTI_MENSOLA, forze)

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi["N_GRAVITA"].shape == (4,)
    assert campi["V_GRAVITA"].shape == (4,)
    assert campi["M_GRAVITA"].shape == (4,)
    assert campi["N_GRAVITA"][0] == pytest.approx(-7.0)
    assert campi["V_GRAVITA"][0] == pytest.approx(math.hypot(2.0, 3.0))
    assert campi["M_GRAVITA"][0] == pytest.approx(13.0)


def test_il_telaio_non_produce_mai_una_von_mises_per_nodo(tmp_path):
    """Lo dichiara `solve.CONTROLLI_PER_MODELLO["picco"]["telaio"]`: la
    tensione del telaio vive per fibra, non per nodo."""
    _scrivi_uscite(tmp_path, _SPOSTAMENTI_MENSOLA, " ".join(["1.0"] * 12 * 4) + "\n")

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert not [nome for nome in campi if nome.startswith("VM_")]


def test_un_blocco_modale_non_produce_mai_U_ne_VM(tmp_path):
    (tmp_path / "modo_1.out").write_text(_SPOSTAMENTI_MENSOLA, encoding="utf-8")
    _fine(tmp_path)

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi["MODO_1"].shape == (5, 3)
    assert not [nome for nome in campi if nome.startswith(("U_", "VM_"))]


def test_un_caso_di_carico_chiamato_modo_non_confonde_le_uscite_modali(tmp_path):
    """La glob `modo_*.out` catturava anche `modo_forze.out` e `modo_
    spostamenti.out`, cioè le uscite di un caso chiamato `modo`. Misurato:
    `leggi_uscite` alzava
    `ValueError: invalid literal for int() with base 10: 'forze'`."""
    _scrivi_uscite(
        tmp_path, _SPOSTAMENTI_MENSOLA, " ".join(["1.0"] * 12 * 4) + "\n"
    )
    for vecchio in ("spostamenti", "forze"):
        (tmp_path / f"GRAVITA_{vecchio}.out").rename(tmp_path / f"modo_{vecchio}.out")

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi["U_modo"].shape == (5, 3)
    assert not [nome for nome in campi if nome.startswith("MODO_")]


def test_un_uscita_troncata_a_meta_riga_si_dichiara_incompleta(tmp_path):
    """Classe di difetto gia' occorsa quattro volte in questo repo: il
    processo ucciso a meta' scrittura. Il file resta, e le sue righe sono
    corte."""
    (tmp_path / "GRAVITA_spostamenti.out").write_text("0 0 0 1 0 -1 2 0", encoding="utf-8")
    _fine(tmp_path)

    with pytest.raises(ValueError, match="troncat"):
        opensees.leggi_uscite(tmp_path, _mensola())


def test_un_uscita_con_byte_non_decodificabili_si_legge_senza_sollevare(tmp_path):
    (tmp_path / "GRAVITA_spostamenti.out").write_bytes(
        b"0 0 0 1 0 \xff-1 2 0 -2 3 0 -3 4 0 -4\n"
    )
    _fine(tmp_path)

    campi = opensees.leggi_uscite(tmp_path, _mensola())

    assert campi["U_GRAVITA"].shape == (5, 3)


def test_un_uscita_vuota_non_e_un_campo_di_zeri(tmp_path):
    """Un file che c'e' ma non porta righe e' una corsa che non ha scritto: e'
    diverso da spostamenti nulli, e va detto."""
    (tmp_path / "GRAVITA_spostamenti.out").write_text("\n\n", encoding="utf-8")
    _fine(tmp_path)

    with pytest.raises(ValueError, match="nessuna riga"):
        opensees.leggi_uscite(tmp_path, _mensola())


def test_un_analisi_che_non_converge_ferma_lo_script(tmp_path):
    """`analyze 1` rende un codice, e ignorarlo è il difetto: un'analisi che
    non converge non fermava lo script, OpenSees usciva 0 (misurato: il codice
    d'uscita non è mai il segnale), i registratori scrivevano l'ultimo stato e
    il lettore non lo distingueva da un risultato vero."""
    righe = _scrivi(tmp_path).splitlines()

    assert "analyze 1" not in righe, "il valore di ritorno va guardato"
    guardia = [r for r in righe if "analyze 1" in r]
    assert guardia and guardia[0].startswith("if {[analyze 1] != 0}"), guardia
    assert any("exit 1" in r for r in righe)


def test_il_tcl_scrive_il_marcatore_di_fine_in_coda(tmp_path):
    """Il solo modo di distinguere una corsa troncata da una completa a livello
    di **corsa** e non di singolo file."""
    testo = _scrivi(tmp_path)

    assert opensees.NOME_FINE in testo
    assert opensees.MARCA_FINE in testo


def test_una_corsa_senza_marcatore_di_fine_si_dichiara_incompleta(tmp_path):
    """Uscite sul disco e nessun marcatore: il processo è morto a metà, o
    l'analisi non ha converso ed è uscita 1. In tutti e due i casi l'ultimo
    stato scritto non è un risultato."""
    (tmp_path / "GRAVITA_spostamenti.out").write_text(
        _SPOSTAMENTI_MENSOLA, encoding="utf-8"
    )

    with pytest.raises(ValueError, match="marcatore di fine"):
        opensees.leggi_uscite(tmp_path, _mensola())


# --- La massa modale ----------------------------------------------------------
_MODALE = """\
* 10. MODAL PARTICIPATION MASS RATIOS (%) (cumulative):
# The cumulative modal participation mass ratios (%) for each mode.
#          MODE            MX            MY            MZ           RMX           RMY           RMZ
# ------------- ------------- ------------- ------------- ------------- ------------- -------------
              1            50            60             0             1             2             3
              2            92            95            91             4             5             6
"""


def test_la_massa_modale_e_l_ultima_riga_cumulata(tmp_path):
    (tmp_path / "massa_modale.out").write_text(_MODALE, encoding="utf-8")

    masse = opensees.leggi_massa_modale(tmp_path / "massa_modale.out")

    assert masse["catturata"][:3] == [92.0, 95.0, 91.0]
    assert masse["disponibile"][:3] == [100.0, 100.0, 100.0]


def test_senza_blocco_modale_la_massa_e_None_e_non_zero(tmp_path):
    """`None` significa «non verificato»; zero significherebbe «i modi non
    catturano massa», che e' un difetto e un'altra cosa."""
    (tmp_path / "massa_modale.out").write_text("nessun blocco qui\n", encoding="utf-8")

    assert opensees.leggi_massa_modale(tmp_path / "massa_modale.out") is None
    assert opensees.leggi_massa_modale(tmp_path / "manca.out") is None


def test_il_marcatore_di_avviso_non_e_quello_di_calculix():
    """Misurato: OpenSees scrive `WARNING` senza asterisco. Contare `*WARNING`
    sulla sua uscita darebbe zero avvisi qualunque cosa sia successa."""
    from meshrec.core import solve

    assert opensees.MARCA_AVVISO == "WARNING"
    assert solve._MARCA_AVVISO_CCX == "*WARNING"
    assert opensees.conta_avvisi(
        "WARNING - no torsion specified for 3D fiber section\nok\nWARNING: altro\n"
    ) == 2


# --- La prova contro il binario vero ------------------------------------------
_OPENSEES = os.environ.get("MESHREC_OPENSEES") or shutil.which("OpenSees")


@pytest.mark.feasibility
def test_opensees_esegue_il_tcl_che_scriviamo_e_accorcia_la_mensola_come_la_formula(
    tmp_path,
):
    """Fase 0 per il secondo solutore: OpenSees accetta il nostro `.tcl` e dà
    un risultato corretto?

    L'oracolo è in forma chiusa e **non** approssimato dalla discretizzazione.
    Il peso proprio è ripartito a metà per estremo, quindi la forza nel tratto
    `j` di una mensola a `n` tratti vale `w*(n-j) + w/2`, e la somma degli
    accorciamenti dà esattamente `rho*A*g*L^2 / (2*EA)` -- la stessa formula del
    continuo, senza errore di discretizzazione. Un numero di tratti diverso non
    sposta il risultato, ed è la controprova che la ripartizione nodale è
    quella giusta.

    `EA` porta anche le barre: le fibre d'acciaio si sommano alla `patch` di
    calcestruzzo, che è la convenzione della sezione a fibre. Ignorarle darebbe
    uno scarto dell'8% e lo si leggerebbe come un difetto del modello.
    """
    if _OPENSEES is None:
        pytest.skip(
            "OpenSees non trovato: né MESHREC_OPENSEES né 'OpenSees' nel PATH"
        )
    telaio = _mensola(stazioni=4, altezza=2000.0)
    resoconto = opensees.scrivi_tcl(
        tmp_path / "telaio.tcl", telaio, casi_di_carico=["GRAVITA", "MODALE"], modi=4
    )

    processo = subprocess.run(
        [_OPENSEES, "telaio.tcl"],
        cwd=tmp_path, capture_output=True, timeout=300,
    )
    uscita = (processo.stdout + processo.stderr).decode("utf-8", errors="ignore")
    # Il codice d'uscita non è il segnale (misurato): lo sono gli avvisi e le
    # uscite scritte.
    assert opensees.conta_avvisi(uscita) == 0, uscita[-3000:]
    assert "while executing" not in uscita, uscita[-3000:]
    # Il marcatore di fine: la corsa è arrivata in fondo, non è stata troncata.
    assert (tmp_path / opensees.NOME_FINE).is_file(), uscita[-3000:]

    campi = opensees.leggi_uscite(tmp_path, telaio)

    area = 300.0 * 200.0
    area_barre = 4 * math.pi * 16.0**2 / 4.0
    rigidezza = CALCESTRUZZO.young * area + ACCIAIO.young * area_barre
    peso = area * CALCESTRUZZO.density * config.GRAVITY_MM_S2
    atteso = -peso * 2000.0**2 / (2.0 * rigidezza)

    assert campi["U_GRAVITA"][-1, 2] == pytest.approx(atteso, rel=1e-6)
    assert campi["U_GRAVITA"][0].tolist() == [0.0, 0.0, 0.0]
    assert resoconto["peso_proprio"] == pytest.approx(area * 2000.0 * CALCESTRUZZO.density * config.GRAVITY_MM_S2)

    # Le reazioni pareggiano il peso: è l'oracolo di `solve.controlla_reazioni`,
    # e sul telaio il termine di gravità tributaria vale zero.
    reazioni = opensees._ultima_riga(tmp_path / "GRAVITA_reazioni.out", 6 * 5)
    assert reazioni.reshape(5, 6)[0, 2] == pytest.approx(resoconto["peso_proprio"], rel=1e-9)

    # Quattro modi chiesti, quattro forme scritte, e nessun U_ né VM_ da loro.
    assert [n for n in campi if n.startswith("MODO_")] == [f"MODO_{i}" for i in range(1, 5)]
    masse = opensees.leggi_massa_modale(tmp_path / opensees.NOME_MASSA_MODALE)
    assert masse is not None
    assert masse["disponibile"] == [100.0] * 6


@pytest.mark.feasibility
def test_l_asse_locale_y_di_opensees_e_e2_per_asse_col_verso(tmp_path):
    """L'oracolo della guardia su `e1`, misurato sul binario e non letto.

    Le `y` delle barre valgono solo se l'asse locale y che OpenSees costruisce
    da (asse, `vecxz`) e' `vecxz x asse` **col verso**. Se la convenzione fosse
    l'opposta, la guardia rifiuterebbe ogni terna sana e accetterebbe quelle
    specchiate, e nessun test sul telaio simmetrico di prova lo vedrebbe.

    Mensola lungo z, `vecxz = (0,1,0)`, quindi `vecxz x asse = (1,0,0)`: un
    carico lungo il **global x** deve comparire nella componente locale **y**.
    """
    if _OPENSEES is None:
        pytest.skip("OpenSees non trovato")
    (tmp_path / "p.tcl").write_text(
        "wipe\n"
        "model BasicBuilder -ndm 3 -ndf 6\n"
        "node 1 0 0 0\nnode 2 0 0 1000\nfix 1 1 1 1 1 1\n"
        "uniaxialMaterial Elastic 1 30000.0\n"
        "section Fiber 1 -GJ 1.0e12 {\n"
        "    patch rect 1 10 10 -150 -100 150 100\n}\n"
        "geomTransf Linear 1 0 1 0\n"
        "element forceBeamColumn 1 1 2 5 1 1\n"
        "timeSeries Linear 1\n"
        "pattern Plain 1 1 {\n    load 2 1000.0 0 0 0 0 0\n}\n"
        "recorder Element -file loc.out -precision 12 -ele 1 localForce\n"
        "constraints Transformation\nnumberer RCM\nsystem BandGeneral\n"
        "test NormDispIncr 1.0e-8 10\nalgorithm Linear\n"
        "integrator LoadControl 1.0\nanalysis Static\n"
        "if {[analyze 1] != 0} { exit 1 }\nremove recorders\nwipe\n",
        encoding="utf-8",
    )

    subprocess.run([_OPENSEES, "p.tcl"], cwd=tmp_path, capture_output=True, timeout=300)

    locali = opensees._ultima_riga(tmp_path / "loc.out", 12)
    assert locali[1] == pytest.approx(-1000.0, rel=1e-6), "il carico non è sull'asse y"
    assert abs(locali[2]) < 1e-6, "l'asse z locale non deve portare nulla"


@pytest.mark.feasibility
def test_la_verifica_promuove_opensees_vero_e_boccia_un_omonimo(tmp_path):
    """La prova di `solve.verifica` contro il binario vero, non contro un finto.

    `/bin/cat` esiste su ogni macchina, esegue, e fa l'eco di quello che gli
    arriva: è l'omonimo perfetto, e passava la prova quando il verdetto era la
    sola eco.
    """
    from typing import NamedTuple

    from meshrec.core import solve

    class _Cfg(NamedTuple):
        nome: str
        percorso: Path | None

    if _OPENSEES is None:
        pytest.skip(
            "OpenSees non trovato: né MESHREC_OPENSEES né 'OpenSees' nel PATH"
        )

    vero = solve.verifica(_Cfg("opensees", Path(_OPENSEES)))
    assert vero["funziona"] is True, vero["motivo"]
    assert vero["motivo"] is None

    omonimo = solve.verifica(_Cfg("opensees", Path("/bin/cat")))
    assert omonimo["disponibile"] is True
    assert omonimo["funziona"] is False


# --- I dati per cella nel .vtu -------------------------------------------------
#
# Stanno qui e non in tests/test_abaqus.py perche' esistono per il telaio: N, V
# e M sono per CELLA (#138 Q2), e prima di questo ramo `write_vtu` sapeva
# scrivere solo campi per nodo.
_NODI_TETRAEDRO = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
)
_CELLE_TETRAEDRO = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64)


def _rileggi(percorso: Path):
    import meshio

    return meshio.read(str(percorso))


def test_senza_dati_per_cella_il_vtu_resta_valido_e_dichiara_che_non_ce_ne_sono(tmp_path):
    from meshrec.core import abaqus

    percorso = tmp_path / "senza.vtu"
    abaqus.write_vtu(percorso, _NODI_TETRAEDRO, _CELLE_TETRAEDRO, element_type="C3D4")

    letto = _rileggi(percorso)
    assert len(letto.cells[0].data) == 2
    assert letto.cell_data == {}


def test_i_dati_per_cella_arrivano_nel_vtu_uno_per_cella(tmp_path):
    from meshrec.core import abaqus

    percorso = tmp_path / "con.vtu"
    abaqus.write_vtu(
        percorso, _NODI_TETRAEDRO, _CELLE_TETRAEDRO, element_type="C3D4",
        cell_data={"N_GRAVITA": np.array([-7.0, 3.0])},
    )

    letto = _rileggi(percorso)
    assert letto.cell_data["N_GRAVITA"][0].tolist() == [-7.0, 3.0]


def test_un_dato_per_cella_di_lunghezza_sbagliata_e_rifiutato(tmp_path):
    """meshio scriverebbe il file lo stesso, e ParaView colorerebbe le celle
    con i valori scalati di uno: un errore che si vede solo guardando."""
    from meshrec.core import abaqus

    with pytest.raises(ValueError, match="N_GRAVITA"):
        abaqus.write_vtu(
            tmp_path / "storto.vtu", _NODI_TETRAEDRO, _CELLE_TETRAEDRO,
            element_type="C3D4", cell_data={"N_GRAVITA": np.array([1.0, 2.0, 3.0])},
        )
