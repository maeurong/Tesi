"""L'attribuzione dei tetraedri alle membrature, per baricentro.

I prismi si costruiscono qui a mano, con `hexa.Prisma`, e non da una
`Membratura` misurata: cio' che questo modulo decide e' una questione di
appartenenza geometrica, e una membratura vera porterebbe dentro il test venti
campi che non c'entrano. Con `asse = z` la base del piano di sezione e' `x, y`
(vedi `hexa._base_del_piano`), quindi il contorno si legge come una scatola
allineata agli assi.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from meshrec.core import attribuzione, config, hexa
from materiale import MATERIALE


def _prisma(centro, lati, altezza):
    """Una scatola: centro in pianta [mm], lati [mm], asse z lungo `altezza`."""
    mezzo = np.array(lati, dtype=np.float64) / 2.0
    rettangolo = np.array(centro, dtype=np.float64) + mezzo * np.array(
        [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]]
    )
    return hexa.Prisma(
        contorno=rettangolo,
        origine=np.zeros(3),
        asse=np.array([0.0, 0.0, 1.0]),
        lunghezza=float(altezza),
    )


_SPIGOLI = np.array(
    [[-0.25, -0.25, -0.25], [0.75, -0.25, -0.25], [-0.25, 0.75, -0.25], [-0.25, -0.25, 0.75]]
)
"""Quattro vertici la cui media e' esattamente l'origine: baricentro esatto.

Serve al caso di confine, dove il baricentro deve cadere **sul** piano e non a
un epsilon da una parte: la media di questi quattro somma a zero in binario.
"""


def _maglio(baricentri):
    """Un tetraedro per baricentro chiesto, ciascuno di volume 1/6 mm^3."""
    centri = np.asarray(baricentri, dtype=np.float64)
    nodi = np.vstack([centro + _SPIGOLI for centro in centri])
    return nodi, np.arange(4 * len(centri)).reshape(-1, 4)


def _regione(membratura):
    """Una `RegioneConfig` col minimo che la configurazione pretende."""
    voce = config.MaterialeDichiarato(
        material=MATERIALE, provenienza="a_mano", norma="NTC 2018 Tab. 4.1.I"
    )
    return config.RegioneConfig(
        membratura=membratura,
        sezione=config.SezioneConfig(
            calcestruzzo_confinato=voce, calcestruzzo_copriferro=voce, acciaio=voce
        ),
    )


def _membratura(contorno_lati=(100.0, 100.0)):
    """I quattro campi che `hexa.prisma_di(..., 'estruso')` legge, e nient'altro."""
    mezzo = np.array(contorno_lati, dtype=np.float64) / 2.0
    return SimpleNamespace(
        contorno=mezzo * np.array([[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]]),
        origine=np.zeros(3),
        asse=np.array([0.0, 0.0, 1.0]),
        lunghezza=200.0,
    )


def test_il_maglio_senza_elementi_e_rifiutato_invece_di_attribuire():
    """Zero elementi: si dichiara, non si restituisce una mappa vuota.

    Stesso testo delle due porte che gia' rifiutano il maglio vuoto in
    `abaqus.py`: un resoconto con `frazione_orfana` su zero elementi sarebbe
    un numero calcolato sul nulla.

    Mutazione che lo uccide: togliere la guardia e lasciare che
    `frazione_orfana` esca `nan` da una divisione per zero.
    """
    with pytest.raises(ValueError, match="non ha nessun elemento"):
        attribuzione.attribuisci(np.zeros((0, 3)), np.zeros((0, 4), dtype=np.int64), {})


def test_senza_prismi_ogni_tetraedro_e_orfano_e_non_e_un_errore():
    """Nessuna membratura accettata dal prior: frazione orfana 1, non uno schianto."""
    nodi, elementi = _maglio([(0.0, 0.0, 10.0), (50.0, 0.0, 10.0)])

    etichette, resoconto = attribuzione.attribuisci(nodi, elementi, {})

    assert np.array_equal(etichette, [-1, -1])
    assert resoconto["frazione_orfana"] == 1.0
    assert resoconto["elementi_per_regione"] == {}


def test_il_tetraedro_dentro_un_prisma_va_a_quella_regione():
    """Il caso semplice, e le due misure per regione che ne discendono.

    Mutazione che lo uccide: contare gli elementi di una regione includendo
    gli orfani, o sommare i volumi di tutti gli elementi invece dei suoi.
    """
    nodi, elementi = _maglio([(0.0, 0.0, 10.0), (500.0, 0.0, 10.0)])
    prismi = {"PILASTRO": _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0)}

    etichette, resoconto = attribuzione.attribuisci(nodi, elementi, prismi)

    assert np.array_equal(etichette, [0, -1])
    assert resoconto["elementi_per_regione"] == {"PILASTRO": 1}
    assert resoconto["volume_per_regione"]["PILASTRO"] == pytest.approx(1.0 / 6.0)
    assert resoconto["frazione_orfana"] == 0.5
    assert resoconto["contesi_risolti"] == 0


def test_il_conteso_va_alla_membratura_maggiore_e_il_conteggio_lo_dichiara():
    """Due prismi sovrapposti: vince quello di sezione maggiore (Ruling AD).

    Mutazione che lo uccide: assegnare al primo prisma che contiene il
    baricentro, o alla sezione minore.
    """
    nodi, elementi = _maglio([(0.0, 0.0, 10.0)])
    prismi = {
        "PICCOLA": _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0),
        "GRANDE": _prisma(centro=(0.0, 0.0), lati=(300.0, 300.0), altezza=200.0),
    }

    etichette, resoconto = attribuzione.attribuisci(nodi, elementi, prismi)

    assert np.array_equal(etichette, [1])
    assert resoconto["elementi_per_regione"] == {"PICCOLA": 0, "GRANDE": 1}
    assert resoconto["contesi_risolti"] == 1


def test_il_baricentro_sul_confine_non_dipende_dall_ordine_dei_prismi():
    """Confine esatto fra due prismi: decide il dato, non l'iterazione.

    Il baricentro sta sul piano x = 50, che e' la faccia comune. Entrambi i
    prismi lo contengono (`hexa.dentro` chiude entrambe le disuguaglianze), ed
    e' un conteso come un altro: alla sezione maggiore, quale che sia l'ordine
    in cui i due arrivano.

    Mutazione che lo uccide: risolvere il conteso col primo o con l'ultimo che
    contiene il baricentro invece che con l'area.
    """
    nodi, elementi = _maglio([(50.0, 0.0, 10.0)])
    sinistro = _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0)
    destro = _prisma(centro=(200.0, 0.0), lati=(300.0, 300.0), altezza=200.0)

    diritto, _ = attribuzione.attribuisci(nodi, elementi, {"A": sinistro, "B": destro})
    rovescio, _ = attribuzione.attribuisci(nodi, elementi, {"B": destro, "A": sinistro})

    assert diritto[0] == 1
    assert rovescio[0] == 0


def test_a_pari_area_lo_spareggio_e_la_prima_regione():
    """«Alla maggiore» non basta quando le due aree sono identiche.

    Lo spareggio dichiarato e' la posizione nella mappa dei prismi, che e'
    l'ordine in cui le regioni sono dichiarate: un dato d'ingresso, non
    l'ordine in cui il ciclo interno le visita.

    Mutazione che lo uccide: uno spareggio all'ultima regione, o nessuno --
    che lascerebbe decidere all'ordine interno di iterazione.
    """
    nodi, elementi = _maglio([(0.0, 0.0, 10.0)])
    prismi = {
        "PRIMA": _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0),
        "SECONDA": _prisma(centro=(10.0, 0.0), lati=(100.0, 100.0), altezza=200.0),
    }

    etichette, resoconto = attribuzione.attribuisci(nodi, elementi, prismi)

    assert etichette[0] == 0
    assert resoconto["contesi_risolti"] == 1


def test_senza_orfani_la_frazione_e_zero():
    """Mutazione che lo uccide: una frazione orfana che non scende mai a zero."""
    nodi, elementi = _maglio([(0.0, 0.0, 10.0), (10.0, 10.0, 20.0)])
    prismi = {"TUTTO": _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0)}

    _, resoconto = attribuzione.attribuisci(nodi, elementi, prismi)

    assert resoconto["frazione_orfana"] == 0.0


def test_la_mappa_e_la_stessa_fra_due_esecuzioni():
    """Un esito discreto che cambia fra due corse e' un difetto di prodotto."""
    nodi, elementi = _maglio([(0.0, 0.0, 10.0), (50.0, 0.0, 10.0), (500.0, 0.0, 10.0)])
    prismi = {
        "A": _prisma(centro=(0.0, 0.0), lati=(100.0, 100.0), altezza=200.0),
        "B": _prisma(centro=(60.0, 0.0), lati=(100.0, 100.0), altezza=200.0),
    }

    prima, resoconto_prima = attribuzione.attribuisci(nodi, elementi, prismi)
    seconda, resoconto_seconda = attribuzione.attribuisci(nodi, elementi, prismi)

    assert np.array_equal(prima, seconda)
    assert resoconto_prima == resoconto_seconda


def test_un_elemento_non_tetraedrico_e_rifiutato_dicendo_la_forma():
    """Otto colonne sono un esaedro: i suoi primi quattro nodi sono una faccia.

    Prenderli per vertici darebbe un baricentro sulla faccia inferiore, cioe'
    un'attribuzione sbagliata in silenzio invece di un rifiuto.

    Mutazione che lo uccide: troncare a `elementi[:, :4]` senza controllare
    quante colonne ci sono davvero.
    """
    nodi = np.zeros((8, 3))
    elementi = np.arange(8).reshape(1, 8)

    with pytest.raises(ValueError, match="8 nodi"):
        attribuzione.attribuisci(nodi, elementi, {})


def test_una_regione_oltre_le_membrature_del_prior_e_rifiutata_dicendo_quante():
    """La configurazione non puo' controllarlo: nasce prima che il prior giri.

    Mutazione che lo uccide: indicizzare `membrature` senza controllare, che
    darebbe un `IndexError` senza dire quante membrature ci sono davvero.
    """
    membrature = [_membratura(), _membratura()]

    with pytest.raises(ValueError, match="il prior ne ha 2"):
        attribuzione.prismi_delle_regioni(membrature, {"TROPPO_IN_LA": _regione(2)})


def test_due_regioni_sulla_stessa_membratura_sono_rifiutate():
    """Due *ELSET sugli stessi elementi: nel deck vincerebbe l'ultima sezione.

    Misurato su `ccx` 2.22: due `*SOLID SECTION` sovrapposte con materiali
    diversi non producono un avviso, e gli spostamenti sono quelli del
    materiale scritto per ultimo.

    Mutazione che lo uccide: costruire i prismi senza guardare se due regioni
    citano lo stesso indice.
    """
    membrature = [_membratura(), _membratura()]

    with pytest.raises(ValueError, match="la stessa membratura"):
        attribuzione.prismi_delle_regioni(
            membrature, {"PILASTRO": _regione(1), "GEMELLA": _regione(1)}
        )


def test_i_prismi_escono_nell_ordine_delle_regioni():
    """Il nome e' la chiave, e l'ordine e' quello della configurazione.

    E' l'ordine su cui poggia lo spareggio a pari area, quindi non e' un
    dettaglio di presentazione.
    """
    membrature = [_membratura((100.0, 100.0)), _membratura((300.0, 300.0))]

    prismi = attribuzione.prismi_delle_regioni(
        membrature, {"TRAVE": _regione(1), "PILASTRO": _regione(0)}
    )

    assert list(prismi) == ["TRAVE", "PILASTRO"]
    assert np.ptp(prismi["TRAVE"].contorno[:, 0]) == pytest.approx(300.0)
