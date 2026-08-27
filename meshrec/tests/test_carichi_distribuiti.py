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
from materiale import MATERIALE


# Un cubo in sei tetraedri (decomposizione di Kuhn), coi vertici numerati sui
# bit di (i, j, k). Copia deliberata di quello di `test_abaqus.py`: e' un fatto
# di geometria di tre righe, e condividerlo vorrebbe dire che un file di test
# ne importa un altro.
_CUBO_IN_SEI = (
    (0, 1, 3, 7), (0, 1, 7, 5), (0, 5, 7, 4),
    (0, 3, 2, 7), (0, 6, 4, 7), (0, 2, 6, 7),
)

TET_LINEARE = config.TetConfig(element="C3D4")

# La lastra e' alta un solo strato: con la tolleranza predefinita (sei volte la
# spaziatura) il `*NSET` di `BASE` arriva a contenere **ogni** nodo del
# provino, e allora qualunque selettore cade per intero dentro l'insieme
# vincolato. E' lo stesso inciampo che
# `tests/validazione/test_pressione_equilibrio.py` evita alzando il provino a
# otto strati; qui ogni area e' un numero esatto che non deve cambiare, quindi
# si stringe la tolleranza invece della geometria.
ANALISI_LASTRA = config.AnalysisConfig(material=MATERIALE, set_tolerance_factor=0.5)


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
    tutta lungo z. Il segno e' **negativo**: `risultante` e' la forza che il
    passo applica, e una pressione positiva preme dentro la faccia, quindi
    verso il basso su un tetto orizzontale. La reazione al vincolo e' l'opposta
    (`tests/validazione/test_pressione_equilibrio.py` la misura con `ccx`).
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    percorso = tmp_path / "m.inp"
    esito = abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
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
    assert resoconto["risultante"] == pytest.approx([0.0, 0.0, -400.0])
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
            percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
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
    x = 40 (40x10 = 400 mm², normale +x), perpendicolari fra loro. L'area
    vettoriale uscente vale (400, 0, 1600) mm², il suo modulo
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
    assert resoconto["area_vettoriale_uscente"] == pytest.approx(
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
    assert resoconto["area_vettoriale_uscente"] == pytest.approx(
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


def _passo(testo: str, nome: str) -> str:
    """Il blocco di deck del passo statico che porta quel nome."""
    for blocco in testo.split("** NOME PASSO: ")[1:]:
        if blocco.splitlines()[0] == nome:
            return blocco
    raise AssertionError(f"il deck non contiene un passo '{nome}'")


def test_il_passo_di_pressione_azzera_le_forze_nodali_del_passo_precedente(tmp_path):
    """`*CLOAD, OP=NEW` nel passo distribuito, che i due cicli gemelli già scrivono.

    `_passo_statico` apre con `*DLOAD, OP=NEW`, che azzera il carico di volume
    e non le forze nodali: `ccx` tiene attivo il `*CLOAD` del passo precedente
    (misurato in `docs/fase-6-cantiere/sonda-cload-persiste/`). I distribuiti
    sono ultimi nell'ordine dei passi, quindi senza la card erediterebbero le
    quote nodali del posizionato che li precede e il passo applicherebbe due
    carichi invece del suo.

    I due tipi di carico non comparivano mai insieme in questo file: è la
    ragione per cui nessun banco vedeva la mancanza.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    carichi = config.CarichiConfig(
        posizionati=(
            config.CaricoPosizionato(nome="TIRO", selettore="TETTO", forza=(100.0, 0.0, 0.0)),
        ),
        distribuiti=(
            config.CaricoDistribuito(nome="VENTO", selettore="TETTO", pressione=0.25),
        ),
    )
    percorso = tmp_path / "m.inp"
    abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
        reference=nodi, carichi=carichi, selettori=selettori,
    )

    testo = percorso.read_text(encoding="ascii")
    assert "*CLOAD, OP=NEW" in _passo(testo, "TIRO")
    assert "*CLOAD, OP=NEW" in _passo(testo, "VENTO"), (
        "il passo distribuito eredita le forze nodali del posizionato che lo precede"
    )


def test_ogni_passo_distribuito_azzera_le_pressioni_dei_passi_precedenti(tmp_path):
    """Il rimedio di #84, nella forma che `ccx` accetta.

    **Questo test prova la forma del deck, non la fisica**, e la distinzione
    conta qui piu' che altrove: misurato in #119, quelle righe `P, 0.0` **non
    spostano le reazioni**, perche' il `*DLOAD, OP=NEW` che apre ogni passo
    cancella gia' i `*DSLOAD` precedenti e arriva prima. Restano come unica
    rete se un giorno `OP=NEW` se ne va, e questo test le tiene ferme nella
    forma giusta -- ma un verde qui non dice nulla su che cosa il solutore
    calcoli. Quello lo dicono le sonde di `tests/feasibility/test_calculix.py`.

    La ragione per cui la forma e' questa: una pressione dichiarata in un
    passo statico resta attiva in quelli dopo, come un `*CLOAD`
    (`test_una_pressione_persiste_finche_non_la_si_ridichiara_a_zero`, `ccx`
    2.21), e `OP=NEW` sulla card `*DSLOAD` non e' percorribile -- `ccx` non
    riconosce quel parametro e ne fa due avvisi. Quindi ogni passo ridichiara
    a **zero** le superfici dei passi distribuiti precedenti, nella stessa
    card e prima della propria. Che la ridichiarazione sostituisca invece di
    sommarsi lo misura il passo 4 della stessa sonda.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    carichi = config.CarichiConfig(
        distribuiti=(
            config.CaricoDistribuito(nome="VENTO", selettore="TETTO", pressione=0.25),
            config.CaricoDistribuito(nome="NEVE", selettore="TETTO", pressione=0.1),
            config.CaricoDistribuito(nome="SPINTA_NEVE", selettore="TETTO", pressione=0.4),
        )
    )
    percorso = tmp_path / "m.inp"
    abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
        reference=nodi, carichi=carichi, selettori=selettori,
    )

    testo = percorso.read_text(encoding="ascii")
    assert "\n*DSLOAD\nVENTO, P, 0.25\n" in _passo(testo, "VENTO")
    assert "\n*DSLOAD\nVENTO, P, 0.0\nNEVE, P, 0.1\n" in _passo(testo, "NEVE")
    assert (
        "\n*DSLOAD\nVENTO, P, 0.0\nNEVE, P, 0.0\nSPINTA_NEVE, P, 0.4\n"
        in _passo(testo, "SPINTA_NEVE")
    )
    # Nessun `OP=NEW`: `ccx` 2.21 non lo riconosce su questa card (#84).
    assert "*DSLOAD, OP=NEW" not in testo


def test_una_pressione_tutta_sul_vincolo_e_un_errore_dichiarato(tmp_path):
    """La stessa guardia dei posizionati, che i distribuiti non attraversavano.

    Una pressione il cui selettore cade tutta dentro l'insieme vincolato non
    sposta nulla: la sua quota finisce in reazione. Il modello passerebbe i
    controlli e non risponderebbe al carico.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "FONDO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, -1.0), max=(41.0, 41.0, 1.0)
        )
    }
    percorso = tmp_path / "m.inp"
    with pytest.raises(ValueError, match="coincide per intero"):
        abaqus.export_model(
            percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
            reference=nodi, carichi=_distribuito("SPINTA_SUOLO", "FONDO", 0.25),
            selettori=selettori,
        )
    assert not percorso.exists()


def test_il_resoconto_di_una_pressione_dichiara_i_nodi_sul_vincolo(tmp_path):
    """`nodi_sul_vincolo` anche per i distribuiti: zero è un valore.

    Una chiave assente non si distingue da una versione che non contava.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    esito = abaqus.export_model(
        tmp_path / "m.inp", tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA,
        TET_LINEARE, reference=nodi, carichi=_distribuito("VENTO", "TETTO", 0.25),
        selettori=selettori,
    )

    assert esito["carichi_distribuiti"]["VENTO"]["nodi_sul_vincolo"] == 0


def _due_distribuiti(nomi: tuple[str, str], selettore: str) -> config.CarichiConfig:
    return config.CarichiConfig(
        distribuiti=tuple(
            config.CaricoDistribuito(nome=nome, selettore=selettore, pressione=0.25)
            for nome in nomi
        )
    )


def test_due_distribuiti_omonimi_non_scrivono_due_surface_con_lo_stesso_nome(tmp_path):
    """Due `*SURFACE` omonime nel deck: il solutore userebbe l'ultima, in silenzio.

    Nessuna validazione a monte lo impedisce -- `CarichiConfig.distribuiti` è
    una tupla senza vincolo di unicità sui nomi -- e con più carichi
    distribuiti per deck la collisione è a portata di un copia-incolla nel
    YAML.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    percorso = tmp_path / "m.inp"
    with pytest.raises(ValueError, match="già dichiarata"):
        abaqus.export_model(
            percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
            reference=nodi, carichi=_due_distribuiti(("VENTO", "VENTO"), "TETTO"),
            selettori=selettori,
        )
    assert not percorso.exists()


def test_un_distribuito_non_ruba_il_nome_a_una_superficie_gia_dichiarata(tmp_path):
    """Stessa collisione, altra provenienza: una `element_surfaces` del chiamante.

    Le due sorgenti finiscono nello stesso dizionario `superfici`, quindi la
    guardia è una sola.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    percorso = tmp_path / "m.inp"
    with pytest.raises(ValueError, match="già dichiarata"):
        abaqus.export_model(
            percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
            reference=nodi, carichi=_distribuito("VENTO", "TETTO", 0.25),
            selettori=selettori, element_surfaces={"VENTO": [(0, 1)]},
        )
    assert not percorso.exists()


# Il `pressure` di `write_inp` -- la pressione **permanente**, quella della
# Fase 4 -- e i distribuiti di #10 sono due cose diverse che finiscono nella
# stessa card `*DSLOAD`. Che la permanente si ripeta nei passi che il parziale
# `passo_statico` raggiunge lo prova gia'
# `test_abaqus.py::test_la_pressione_si_ripete_in_ogni_passo_statico_con_carichi`;
# scoperta restava l'altra meta', i passi distribuiti, dove il parziale viene
# sovrascritto e la permanente vive della sola persistenza del solutore (#111).
_SUPERFICIE_FINTA = [(0, 1)]


def test_la_pressione_permanente_non_e_fra_quelle_azzerate_dai_distribuiti(tmp_path):
    """La forma del deck che tiene viva la permanente nei passi distribuiti.

    **Forma, non fisica.** Che la permanente agisca davvero nel passo di un
    distribuito lo prova una sola cosa, le reazioni che `ccx` restituisce:
    `tests/feasibility/test_calculix.py::test_la_pressione_permanente_agisce_anche_nel_passo_di_un_distribuito`.
    Questo test guarda il testo del deck, ed e' utile per l'altra meta' della
    domanda -- che la permanente non finisca mai fra le superfici azzerate.

    Due modi di romperlo, entrambi silenziosi. Aggiungere la permanente a
    `pressioni_da_azzerare` la spegnerebbe dal primo passo distribuito in poi;
    togliere la sua card dai passi distribuiti farebbe lo stesso, perche' il
    `*DLOAD, OP=NEW` che apre ogni passo cancella i `*DSLOAD` precedenti
    (#119). In entrambi i casi il deck resta valido e i numeri plausibili.
    """
    nodi, tetraedri = _lastra(4, 4, 1, 10.0)
    selettori = {
        "TETTO": config.SelettoreBox(
            tipo="box", min=(-1.0, -1.0, 9.0), max=(41.0, 41.0, 11.0)
        )
    }
    carichi = config.CarichiConfig(
        distribuiti=(
            config.CaricoDistribuito(nome="VENTO", selettore="TETTO", pressione=0.25),
            config.CaricoDistribuito(nome="NEVE", selettore="TETTO", pressione=0.1),
        )
    )
    percorso = tmp_path / "m.inp"
    abaqus.export_model(
        percorso, tmp_path / "m.vtu", nodi, tetraedri, ANALISI_LASTRA, TET_LINEARE,
        reference=nodi, carichi=carichi, selettori=selettori,
        element_surfaces={"PERMANENTE": _SUPERFICIE_FINTA},
        pressure=("PERMANENTE", 0.5),
    )

    testo = percorso.read_text(encoding="ascii")
    assert "\n*DSLOAD\nPERMANENTE, P, 0.5\n" in _passo(testo, "GRAVITA")
    for nome in ("VENTO", "NEVE"):
        assert "PERMANENTE, P, 0.5" in _passo(testo, nome), nome
    azzerate = [riga for riga in testo.splitlines() if riga.endswith(", P, 0.0")]
    assert azzerate == ["VENTO, P, 0.0"], azzerate
