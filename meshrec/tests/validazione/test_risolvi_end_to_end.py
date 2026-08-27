"""`solve.risolvi()` dall'inizio alla fine con `ccx` vero, su maglio tet10 (#95).

**Il buco che questo file chiude.** `tests/validazione/test_equilibrio_reazioni.py`
esegue `ccx` vero, ma chiama `solve._quota_tributaria_gravita` da se': verifica
la *formula*, non il *cablaggio*. I test di `risolvi()` in `tests/test_solve.py`
verificano il cablaggio, ma con un `ccx` finto e passando sempre `"C3D4"`
letterale, quindi non vedono la differenza fra i due elementi. Fra le due meta'
restava scoperta esattamente la riga che il difetto #40 aveva rotto:

    _quota_tributaria_gravita(..., cfg.material.density, element_type)

Rimettere li' un `"C3D4"` letterale -- cioe' reintrodurre #40 -- lasciava
l'intera suite verde. Qui il maglio e' **quadratico** e `element_type` e'
`"C3D10"`: la formula del lineare da' uno scarto di 2,22e-01 contro una
tolleranza di 1e-4, quindi quella mutazione tinge di rosso sia il test
sull'equilibrio sia quello sui verdetti (misurato oggi, 27/08/2026, `ccx`
2.21 su questo maglio).

Il maglio e' un cubo di 100 mm, il piu' rado che regga: `ccx` gira una volta
sola per l'intero modulo (fixture di modulo), perche' e' il costo dominante.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import AnalysisConfig, CarichiConfig, Material, Modale

pytestmark = pytest.mark.validazione

LATO = 100.0
MATERIALE = Material(name="ACCIAIO", young=210_000.0, poisson=0.3, density=7.85e-9)
ANALISI = AnalysisConfig(material=MATERIALE)
CASI_DI_CARICO = ["GRAVITA", "MODALE"]


def _ccx_o_salta() -> str:
    """`ccx` assente non e' un fallimento: PRODUCT.md dichiara utenti confermati
    senza CalculiX. Il motivo del salto nomina l'eseguibile, cosi' chi legge il
    verde della suite sa *cosa* non e' stato verificato."""
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH: validazione non eseguibile")
    return eseguibile


def _scrivi_deck(cartella: Path, nodi: np.ndarray, elementi: np.ndarray) -> tuple[Path, np.ndarray]:
    """Deck tet10 vincolato alla base, peso proprio piu' un passo modale.

    La guardia sul maglio vuoto sta **prima** di `write_inp`: quella accetta
    zero elementi e scrive un `.inp` sintatticamente valido e privo di
    `*ELEMENT` (misurato oggi: 605 byte, nessuna eccezione). `ccx` lo
    risolverebbe in silenzio, e il file di questo modulo confronterebbe
    reazioni nulle con un peso nullo -- un verde su nulla.
    """
    if len(elementi) == 0:
        raise ValueError(
            "il maglio non ha nessun elemento: un deck senza *ELEMENT e' un "
            "modello vuoto che il solutore accetta in silenzio, non un caso da "
            "risolvere"
        )
    base = np.flatnonzero(nodi[:, 2] <= nodi[:, 2].min() + 1e-9)
    deck = cartella / "m.inp"
    abaqus.write_inp(
        deck, nodi, elementi,
        node_sets={"BASE": base},
        material=MATERIALE,
        element_type="C3D10",
        fixed_nset="BASE",
        carichi=CarichiConfig(modale=Modale(modi=3)),
    )
    return deck, base


@pytest.fixture(scope="module")
def corsa(tmp_path_factory):
    """Una sola corsa di `ccx` per tutto il modulo: e' il costo dominante."""
    _ccx_o_salta()
    cartella = tmp_path_factory.mktemp("risolvi_c3d10")
    vertici, facce = synth.box_mesh((LATO, LATO, LATO))
    nodi, elementi = volume.tetrahedralize(
        vertici, facce, max_volume=(LATO / 2.0) ** 3 / 6.0, min_ratio=1.8,
        max_steiner_points=-1, nobisect=False, order=2,
    )
    deck, base = _scrivi_deck(cartella, nodi, elementi)
    vincolo = abaqus.constraint_plan_extent(nodi, base)
    esito = solve.risolvi(
        cartella, deck, ANALISI, nodi, elementi, "C3D10",
        casi_di_carico=CASI_DI_CARICO,
        vincolo_in_pianta=vincolo,
        # Identita': il deck e' scritto con `write_inp` sugli stessi nodi che
        # `risolvi` riceve, senza passare da `export_model`, quindi campi e
        # punti stanno gia' nello stesso telaio. La rotazione vera e' coperta
        # in tests/test_solve.py.
        trasformata=np.eye(4),
    )
    return nodi, elementi, vincolo, esito


def test_su_c3d10_il_verdetto_sulle_reazioni_chiude_l_equilibrio(corsa):
    """La mutazione che questo test uccide: `element_type` sostituito da un
    `"C3D4"` letterale nella chiamata a `_quota_tributaria_gravita` dentro
    `risolvi()` (core/solve.py:1173), cioe' il difetto #40.

    Misurato oggi su questo maglio: 1,98e-08 con la formula giusta, 2,22e-01
    con quella del lineare, contro una tolleranza di 1e-4. Non sono numeri
    registrati: il peso atteso e' `rho*V*g`, calcolato dentro `risolvi()` sui
    dati di questa corsa, e l'asserzione confronta con la tolleranza di
    produzione, non con un valore atteso scritto qui.
    """
    controllo = corsa[3]["controlli"]["reazioni"]

    assert controllo["scarto_relativo"] < solve._TOLLERANZA_REAZIONI


def test_i_verdetti_composti_da_risolvi_coincidono_con_quelli_calcolati_a_mano(corsa):
    """Sei dei sette verdetti, ricalcolati qui dagli artefatti su disco.

    Non e' una tautologia: ogni verdetto viene ricomposto dalle uscite di `ccx`
    (`13_solution.dat`, `13_solver.log`, `13_solution.vtu`) invece che dai
    campi che `risolvi()` restituisce, quindi il confronto misura proprio il
    cablaggio -- quali argomenti `risolvi()` passa a quale `controlla_*`. E'
    la classe di difetto di #40, che era un argomento sbagliato e non una
    formula sbagliata.

    `picco` resta fuori: ricalcolarlo vuol dire riscorrere i blocchi del `.frd`
    e rifare la banda di vincolo, cioe' ricopiare il ciclo di `risolvi()` --
    impalcatura, e un oracolo che ripete il codice che dovrebbe controllare.
    Lo copre gia' `tests/test_solve.py` sull'aggregazione (#92).
    """
    meshio = pytest.importorskip("meshio")
    nodi, elementi, vincolo, esito = corsa
    dat = Path(esito["dat"])

    reazioni = solve.leggi_reazioni(dat, passo=1)
    massa = float(MATERIALE.density) * solve._volume_totale(nodi, elementi)
    quota = solve._quota_tributaria_gravita(
        nodi, elementi, reazioni.keys(), MATERIALE.density, "C3D10"
    )
    campi = meshio.read(esito["vtu"]).point_data
    avvisi = Path(esito["log"]).read_text(encoding="utf-8").upper().count("*WARNING")

    attesi = {
        "reazioni": solve.controlla_reazioni(
            reazioni,
            (0.0, 0.0, (massa - quota) * ANALISI.gravity),
            tolleranza=solve._TOLLERANZA_REAZIONI,
        ),
        "vincolo_in_pianta": solve.controlla_vincolo_in_pianta(vincolo["minimo"]),
        "autovalori": solve.controlla_autovalori(solve.leggi_frequenze(dat)),
        "avvisi": solve.controlla_avvisi(avvisi),
        "spostamenti": solve.controlla_spostamenti(
            solve._spostamento_massimo(campi), solve._dimensione(nodi)
        ),
        "massa_modale": solve.controlla_massa_modale(solve.leggi_massa_modale(dat)),
    }

    assert {nome: esito["controlli"][nome] for nome in attesi} == attesi


def test_senza_ccx_la_validazione_si_salta_nominando_il_solutore(monkeypatch):
    """Ingresso degenere: macchina senza CalculiX. Il modulo si salta con un
    motivo che nomina `ccx`, non fallisce e non passa a vuoto."""
    monkeypatch.setattr(shutil, "which", lambda _nome: None)

    with pytest.raises(pytest.skip.Exception) as saltato:
        _ccx_o_salta()

    assert "ccx" in str(saltato.value)


def test_un_frd_troncato_solleva_col_nome_del_file_invece_di_rendere_un_esito(
    tmp_path, monkeypatch, corsa
):
    """Ingresso degenere: il solutore esce senza scrivere tutti i blocchi
    (ucciso, disco pieno, mancata convergenza). `risolvi()` deve sollevare un
    `ValueError` che nomina il file, non rendere un dizionario con meno
    risultati di quanti il `.frd` ne dichiari -- che il chiamante leggerebbe
    come successo.

    Il `.frd` troncato e' quello **vero** di questa corsa privato della sua
    ultima riga di chiusura ` -3`: un reperto di `ccx`, non uno scritto a
    mano. `ccx` e' sostituito da un finto solo per rimettere quel file dove
    `risolvi()` lo cerca.
    """
    nodi, elementi, vincolo, esito = corsa
    righe = Path(esito["frd"]).read_text(encoding="ascii", errors="ignore").splitlines()
    ultima_chiusura = max(i for i, riga in enumerate(righe) if riga.startswith(" -3"))
    troncato = "\n".join(righe[:ultima_chiusura]) + "\n"
    dat = Path(esito["dat"]).read_bytes()

    deck = tmp_path / "m.inp"
    deck.write_text("", encoding="ascii")

    def ccx_finto(comando, **kwargs):
        deck.with_suffix(".frd").write_text(troncato, encoding="ascii")
        deck.with_suffix(".dat").write_bytes(dat)
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(solve.shutil, "which", lambda _nome: "/usr/bin/ccx")
    monkeypatch.setattr(solve.subprocess, "run", ccx_finto)

    with pytest.raises(ValueError) as errore:
        solve.risolvi(
            tmp_path, deck, ANALISI, nodi, elementi, "C3D10",
            casi_di_carico=CASI_DI_CARICO,
            vincolo_in_pianta=vincolo,
            trasformata=np.eye(4),
        )

    assert "13_solution.frd" in str(errore.value)


def test_un_maglio_senza_elementi_non_arriva_a_scrivere_il_deck(tmp_path):
    """Ingresso degenere: maglio con zero elementi. La guardia sta prima di
    `write_inp`, che invece accetta l'array vuoto e lascia sul disco un `.inp`
    senza `*ELEMENT` -- un modello vuoto che `ccx` risolve senza protestare."""
    with pytest.raises(ValueError, match="nessun elemento"):
        _scrivi_deck(tmp_path, np.zeros((4, 3)), np.zeros((0, 10), dtype=np.int64))

    assert list(tmp_path.iterdir()) == [], "il deck non deve esistere"
