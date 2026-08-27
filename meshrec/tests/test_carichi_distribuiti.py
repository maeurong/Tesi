"""Il carico distribuito sull'as-built (#10): una pressione normale alla faccia.

Perche' un file suo e non una coda a `test_abaqus.py`: quel file prova la
logica **geometrica** dell'esportatore -- terna, set di nodi, impronta a terra,
ripartizione -- ed e' gia' lungo. Qui si prova una cosa sola, la superficie su
cui una pressione agisce e la guardia che la smentisce.

La lastra e' costruita **a mano** e non da TetGen, per la ragione scritta nel
docstring di `griglia_mesh`: il generatore da' magli diversi fra Linux x86-64 e
macOS arm64 a parita' di versione e di ingresso (#66), e ogni numero qui sotto
e' un'area esatta che deve valere su entrambe le piattaforme. E' la lezione di
#72, dove una soglia tarata su una macchina sola e' stata bocciata dalla CI.
"""

import itertools

import numpy as np
import pytest

from meshrec.core import abaqus, config
from materiale import ANALISI


# Un cubo in sei tetraedri (decomposizione di Kuhn), coi vertici numerati sui
# bit di (i, j, k). Copia deliberata di quello di `test_abaqus.py`: e' un fatto
# di geometria di tre righe, e condividerlo vorrebbe dire che un file di test
# ne importa un altro.
_CUBO_IN_SEI = (
    (0, 1, 3, 7), (0, 1, 7, 5), (0, 5, 7, 4),
    (0, 3, 2, 7), (0, 6, 4, 7), (0, 2, 6, 7),
)

TET_LINEARE = config.TetConfig(element="C3D4")


def _lastra(nx: int, ny: int, nz: int, passo: float):
    """Griglia di celle, ognuna nei sei tetraedri di Kuhn."""
    indice, punti = {}, []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                indice[(i, j, k)] = len(punti)
                punti.append([i * passo, j * passo, k * passo])
    tetraedri = []
    for i, j, k in itertools.product(range(nx), range(ny), range(nz)):
        # Ordine dei bit come nella fixture `griglia_mesh` di `test_abaqus.py`:
        # x sul bit 0, y sul bit 1, z sul bit 2. Invertirlo produce tetraedri a
        # **jacobiano negativo**, che questi controlli non vedrebbero -- non
        # risolvono nulla -- e che `ccx` rifiuta con «nonpositive jacobian
        # determinant». Misurato provando il deck col solutore.
        angoli = [
            indice[(i + (n & 1), j + ((n >> 1) & 1), k + ((n >> 2) & 1))]
            for n in range(8)
        ]
        tetraedri += [[angoli[n] for n in quattro] for quattro in _CUBO_IN_SEI]
    return np.array(punti, dtype=np.float64), np.array(tetraedri, dtype=np.int64)


def _distribuito(nome: str, selettore: str, pressione: float) -> config.CarichiConfig:
    return config.CarichiConfig(
        distribuiti=(
            config.CaricoDistribuito(nome=nome, selettore=selettore, pressione=pressione),
        )
    )


def test_una_pressione_su_una_faccia_scrive_la_superficie_e_la_card(tmp_path):
    """Il caso diritto: la faccia superiore di una lastra 40x40x10.

    I numeri sono esatti e non di piattaforma: 1600 mm² di area (40 per 40),
    efficienza 1 perche' la faccia e' piana, e risultante 0,25 * 1600 = 400 N
    tutta lungo z.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    percorso = tmp_path / "m.inp"
    esito = abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
        reference=nodi, carichi=_distribuito("VENTO", "TETTO", 0.25), selettori=selettori,
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*SURFACE, TYPE=ELEMENT, NAME=VENTO" in testo
    assert "\nVENTO, P, 0.25\n" in testo
    # Il nome deve arrivare nella promessa che `solve.risolvi` usa per dare un
    # nome ai blocchi del `.frd`, e dopo i passi che il deck scrive prima.
    assert esito["casi_di_carico"] == ["GRAVITA", "VENTO"]

    resoconto = esito["carichi_distribuiti"]["VENTO"]
    assert resoconto["area_totale"] == pytest.approx(1600.0)
    assert resoconto["efficienza"] == pytest.approx(1.0)
    assert resoconto["risultante"] == pytest.approx([0.0, 0.0, 400.0])
    # Il resoconto dei posizionati non deve averlo raccolto: due chiavi, due
    # forme diverse, e un nome che dice «posizionati» non deve contenere altro.
    assert "VENTO" not in esito["carichi_posizionati"]


def test_una_scatola_che_attraversa_il_pezzo_e_rifiutata_con_le_due_aree(tmp_path):
    """Il difetto che nessun controllo di equilibrio vede.

    La scatola prende in pianta il quadrato centrale della lastra e attraversa
    lo spessore: qualificano le facce **sopra** e quelle **sotto**, che si
    guardano. La risultante esce nulla mentre le tensioni locali ci sono
    davvero, quindi `controlla_reazioni` la lascerebbe passare indenne -- e' lo
    stesso meccanismo dell'errore autoequilibrato di `ripartisci`.

    I due numeri nel messaggio sono esatti: 400 mm² per parte, il quadrato
    20x20 al centro, sopra e sotto.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "PASSANTE": config.SelettoreBox(
            tipo="box", min=(9.0, 9.0, -1.0), max=(31.0, 31.0, 11.0)
        )
    }
    percorso = tmp_path / "m.inp"
    with pytest.raises(ValueError, match="si richiude su sé stessa") as errore:
        abaqus.export_model(
            percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI, TET_LINEARE,
            reference=nodi, carichi=_distribuito("SBAGLIATO", "PASSANTE", 0.5),
            selettori=selettori,
        )
    messaggio = str(errore.value)
    assert "400 mm² di facce spingono da una parte" in messaggio
    assert "400 mm² dall'altra" in messaggio
    # Il deck non si scrive a meta': la guardia sta prima di ogni riga.
    assert not percorso.exists()


def test_uno_spigolo_retto_non_e_una_superficie_che_si_richiude():
    """La guardia non deve bocciare una superficie che gira ma resta un lato.

    E' l'altra meta' della soglia, e senza questo controllo `0,5` sarebbe
    indistinguibile da `0,99`: qualunque superficie non piana verrebbe
    rifiutata e nessun test se ne accorgerebbe.

    La selezione e' il tetto (40x40 = 1600 mm², normale +z) piu' la testata a
    x = 40 (40x10 = 400 mm², normale +x), perpendicolari fra loro. La
    risultante di una pressione unitaria vale (400, 0, 1600), il suo modulo
    sqrt(400² + 1600²) = 1649,242, e l'efficienza 1649,242 / 2000 = 0,824621:
    sopra soglia, quindi passa.

    Gli indici si passano diretti e non per scatola: una scatola allineata agli
    assi che contenga entrambe le facce contiene anche tutto il resto del
    solido, e la selezione non sarebbe piu' quella voluta.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    presi = np.flatnonzero((nodi[:, 2] == 10.0) | (nodi[:, 0] == 40.0))

    superficie, resoconto = abaqus.superficie_di_pressione(
        nodi, tetraedri, presi, "C3D4", nome="SPIGOLO",
    )

    assert resoconto["area_totale"] == pytest.approx(2000.0)
    assert resoconto["risultante_per_pressione_unitaria"] == pytest.approx(
        [400.0, 0.0, 1600.0]
    )
    assert resoconto["efficienza"] == pytest.approx(0.824621, abs=1e-6)
    assert resoconto["facce"] == len(superficie)


def test_la_normale_esce_dal_solido_anche_su_elementi_invertiti():
    """L'orientamento non si fida dell'ordine di `FACCE_DEL_SOLUTORE`, e serve.

    Su un maglio ben orientato quella tabella da' gia' normali uscenti, quindi
    il confronto col baricentro dell'elemento non cambia nulla e **resterebbe
    non provato**: misurato, togliendolo i cinque controlli di questo file
    restavano verdi. Un ramo che nessuna mutazione uccide e' un ramo che si
    puo' cancellare senza accorgersene, ed e' il difetto che questo progetto
    insegue.

    Qui gli elementi hanno due nodi scambiati, cioe' volume negativo -- che e'
    una condizione che il programma **conta** (`quality`, «0 invertiti») ma non
    vieta a questo percorso. Con l'ordine capovolto la tabella darebbe la
    normale rivolta **dentro** il solido, e la risultante uscirebbe a
    `-1600` invece che `+1600`: la pressione risulterebbe applicata al
    contrario, con l'area giusta e il segno sbagliato. L'area non se ne
    accorge, perche' e' un modulo.

    Mutazione che lo uccide: togliere le due righe che confrontano la normale
    col vettore dal baricentro dell'elemento a quello della faccia.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    invertiti = tetraedri[:, [1, 0, 2, 3]]
    tetto = np.flatnonzero(nodi[:, 2] == 10.0)

    _superficie, resoconto = abaqus.superficie_di_pressione(
        nodi, invertiti, tetto, "C3D4", nome="VENTO",
    )

    assert resoconto["area_totale"] == pytest.approx(1600.0)
    assert resoconto["risultante_per_pressione_unitaria"] == pytest.approx(
        [0.0, 0.0, 1600.0]
    ), "la normale punta dentro il solido: la pressione agirebbe al contrario"


def test_un_insieme_tutto_interno_non_delimita_alcuna_faccia():
    """Nessuna faccia di bordo ha tutti i nodi dentro: non c'è pelle su cui premere.

    Non e' lo stesso errore della superficie che si richiude, ed e' bene che i
    due messaggi restino diversi: qui il selettore non ha preso **niente** di
    utile, la' ne ha preso troppo.
    """
    nodi, tetraedri = _lastra(2, 2, 2, 10.0)
    interni = np.flatnonzero(
        (nodi[:, 0] == 10.0) & (nodi[:, 1] == 10.0) & (nodi[:, 2] == 10.0)
    )
    assert interni.size == 1, "il provino non ha piu' un nodo interno solo"

    with pytest.raises(ValueError, match="non delimita alcuna faccia di bordo"):
        abaqus.superficie_di_pressione(nodi, tetraedri, interni, "C3D4", nome="NULLA")


def test_la_pressione_vale_sui_quadratici_dove_la_ripartizione_deve_fermarsi():
    """La ragione per cui questa strada esiste accanto a `ripartisci`.

    Su una faccia a sei nodi i carichi consistenti di una pressione uniforme
    danno **zero ai vertici** (Abaqus Theory Guide §3.2.6, vedi
    `docs/validazione/carichi-consistenti-tet10.md`), quindi `ripartisci` --
    che pesa per area tributaria sui soli vertici -- solleva invece di mentire.
    Una pressione non ha quel problema: nel deck e' una card `*DSLOAD` e
    l'integrazione la fa il solutore.

    Il provino e' il maglio lineare con sei colonne finte in coda: la posizione
    dei nodi di lato non entra ne' in `element_surface` ne' in
    `superficie_di_pressione`, che lavorano sui soli angoli. Qui non si risolve
    nulla, si guarda quale delle due strade accetta l'elemento.
    """
    nodi, tetraedri = _lastra(1, 1, 1, 10.0)
    quadratici = np.hstack([tetraedri, tetraedri[:, [0, 1, 2, 0, 1, 2]]])
    tetto = np.flatnonzero(nodi[:, 2] == 10.0)

    _superficie, resoconto = abaqus.superficie_di_pressione(
        nodi, quadratici, tetto, "C3D10", nome="VENTO",
    )
    assert resoconto["area_totale"] == pytest.approx(100.0)

    with pytest.raises(NotImplementedError, match="zero ai vertici"):
        abaqus.ripartisci(1.0, nodi, quadratici, tetto, "C3D10", nome="VENTO")
