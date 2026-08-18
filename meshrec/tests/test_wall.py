"""Il prior geometrico: terna del pezzo, celle, spessore locale, regioni.

Ogni verifica ha una geometria sintetica a verita' nota dietro: il numero di
membrature atteso viene dal banco di prova e mai dal codice, che deve poter
girare su una geometria che non ha mai visto.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import synth, wall
from meshrec.core.config import SegmentConfig, WallConfig

# Un telaio sintetico: due montanti, un traverso in alto, uno in basso. Sei
# numeri che stanno qui, nel banco, e in nessun file di src/.
#
# Le quattro sezioni (l'estensione in y di ciascun prisma, cioe' lo spessore
# che scomponi() sorveglia) sono deliberatamente tutte diverse fra loro. La
# scomposizione separa le membrature per costanza dello spessore locale: con
# quattro sezioni uguali il banco non proverebbe nulla, perche' un algoritmo
# che fonde tutto in una regione sola passerebbe la prova tanto quanto uno che
# separa correttamente (e' proprio il caso limite verificato piu' sotto da
# test_una_sezione_uniforme_smentisce_la_separazione_per_spessore). I valori
# sono del banco, scelti per essere ben distanti oltre la tolleranza relativa
# predefinita fra ogni coppia di membrature che si toccano a un nodo, non le
# sezioni del provino di laboratorio: quelle vivono nella configurazione del
# Task 15. Ogni sezione e' centrata sull'origine in y (invece che appoggiata a
# y=0): mantiene la simmetria per riflessione attorno a y che il telaio a
# sezione uniforme ha per costruzione, cosi' la terna stimata dalla SVD trova
# ancora y come trasversale in modo esatto e non solo approssimato.
TELAIO = [
    ((0.0, -90.0, 0.0), (200.0, 180.0, 1600.0)),        # montante sinistro
    ((1400.0, -130.0, 0.0), (200.0, 260.0, 1600.0)),    # montante destro
    ((0.0, -70.0, 1600.0), (1600.0, 140.0, 300.0)),     # traverso superiore
    ((0.0, -170.0, -300.0), (1600.0, 340.0, 300.0)),    # traverso inferiore
]
SPAZIATURA = 20.0


def _cfg() -> WallConfig:
    return WallConfig()


def test_la_terna_mette_la_direzione_trasversale_per_ultima():
    """Il telaio e' sottile in y: la terna deve riconoscerlo dal dato, non da
    un asse scelto a mano."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    direzioni, centro = wall.terna(punti)

    assert direzioni.shape == (3, 3)
    assert centro.shape == (3,)
    trasversale = direzioni[2]
    assert abs(abs(trasversale[1]) - 1.0) < 1e-6, f"trasversale attesa lungo y, e' {trasversale}"
    # terna ortonormale destrorsa: e' la condizione perche' u, v, n siano un
    # sistema di riferimento e non tre direzioni qualunque
    assert np.linalg.det(direzioni) == pytest.approx(1.0, abs=1e-9)


def test_la_terna_ha_lo_stesso_verso_su_due_esecuzioni_e_su_una_nuvola_rimescolata():
    """Il verso di una direzione principale e' arbitrario per la SVD: senza
    convenzione due esecuzioni sulla stessa nuvola darebbero assi opposti, e
    ogni indice derivato dalla terna dipenderebbe dall'ordine dei punti."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(0).permutation(len(punti))]

    prima, _ = wall.terna(punti)
    dopo, _ = wall.terna(rimescolati)
    assert prima == pytest.approx(dopo, abs=1e-9)


def test_le_celle_sono_indici_non_negativi_misurati_dal_minimo():
    piano = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 25.0], [-5.0, -5.0]])
    celle = wall.chiavi_di_cella(piano, lato=5.0)

    assert celle.dtype == np.int64
    assert (celle >= 0).all()
    assert celle.shape == (4, 2)
    # il minimo cade nella cella (0, 0); 10 mm a destra del minimo sono tre celle
    assert celle[3].tolist() == [0, 0]
    assert celle[0].tolist() == [1, 1]


def test_lo_spessore_locale_di_una_scatola_e_la_sua_dimensione_sottile():
    """La grandezza sorvegliata e' lo spessore, e su una scatola nota vale la
    dimensione sottile: se non lo fa, ogni regione trovata piu' avanti misura
    un'altra cosa."""
    punti = synth.sample_box_surface((400.0, 180.0, 900.0), SPAZIATURA)
    direzioni, centro = wall.terna(punti)
    centrati = punti - centro
    piano = centrati @ direzioni[:2].T
    trasversale = centrati @ direzioni[2]

    celle, spessori, _ = wall.spessore_per_cella(piano, trasversale, lato=4.0 * SPAZIATURA)

    assert len(celle) == len(spessori)
    # le celle interne alla faccia larga vedono le due facce a 180 mm di distanza
    assert np.median(spessori) == pytest.approx(180.0, abs=1.5 * SPAZIATURA)


def test_il_pavimento_viene_scartato_come_piano_e_non_come_quota():
    """Il pavimento e' un piano quasi orizzontale esteso oltre l'ingombro del
    pezzo. Scartarlo con una soglia di quota sarebbe tarare una costante sulla
    scansione di oggi; qui viene scartato per cio' che e'."""
    telaio = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    pavimento = synth.sample_box_surface((4000.0, 3000.0, 10.0), SPAZIATURA * 2.0)
    pavimento = pavimento + np.array([-1200.0, -1400.0, -320.0])
    punti = np.vstack([telaio, pavimento])

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is True
    assert len(tenuti) < len(punti)
    # nessun punto sotto il piede del telaio sintetico resta in circolazione
    assert tenuti[:, 2].min() > -320.0
    assert tenuti[:, 2].min() == pytest.approx(-300.0, abs=3.0 * SPAZIATURA)


def test_senza_pavimento_non_ne_viene_inventato_uno():
    """Il controllo che smentisce il precedente: su una nuvola che pavimento
    non ha, la funzione non deve togliere una faccia del pezzo scambiandola per
    tale."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    tenuti, metriche = wall.scarta_pavimento(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["pavimento_trovato"] is False
    assert len(tenuti) == len(punti)


def test_una_scatola_da_una_sola_membratura():
    """La prova che la scomposizione non inventa membrature dove non ce ne
    sono. Il numero atteso viene dal banco, non dal codice."""
    punti = synth.sample_box_surface((400.0, 180.0, 1200.0), SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(regioni) == 1
    assert metriche["regioni_trovate"] == 1


def test_un_telaio_sintetico_da_le_membrature_che_ha():
    """Quattro prismi di tre sezioni diverse: la scomposizione deve separarli
    per costanza dello spessore, e i due montanti identici, che sono disgiunti
    nel piano, restano due regioni e non una."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert metriche["regioni_trovate"] == len(regioni)
    assert 2 <= len(regioni) <= 6, (
        f"attese fra 2 e 6 regioni sui quattro prismi del banco, trovate {len(regioni)}: "
        "sotto, la scomposizione fonde membrature diverse; sopra, le frammenta"
    )
    # ogni punto sta in al piu' una regione: una regione non ruba punti a un'altra
    tutti = np.concatenate(regioni)
    assert len(tutti) == len(np.unique(tutti))


def test_l_ordine_delle_regioni_non_dipende_dall_ordine_dei_punti():
    """Quinto vincolo di prodotto: un ordine e' un esito discreto e deve essere
    funzione del dato. E' la stessa lezione gia' pagata sull'ordine dei voxel di
    Open3D fra Windows x86-64 e macOS arm64."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    rimescolati = punti[np.random.default_rng(1).permutation(len(punti))]

    prima, _ = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)
    dopo, _ = wall.scomponi(rimescolati, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(prima) == len(dopo)
    # confronto per insieme di coordinate, non per indice: gli indici puntano a
    # due ordinamenti diversi della stessa nuvola
    for regione_prima, regione_dopo in zip(prima, dopo, strict=True):
        a = np.unique(np.round(punti[regione_prima], 6), axis=0)
        b = np.unique(np.round(rimescolati[regione_dopo], 6), axis=0)
        assert a.shape == b.shape
        assert a == pytest.approx(b)


def test_la_tolleranza_di_spessore_decide_fra_una_regione_e_due():
    """Il test che morde davvero la soglia, e non solo la connettivita'.

    Due prismi identici a parte lo spessore, affiancati e a contatto (nessun
    vuoto fra le celle): se la differenza di spessore sta sotto
    `thickness_tolerance` in relativo, `regioni` li deve fondere in una
    regione sola; se sta sopra, li deve separare in due. Le due differenze
    sono derivate da `WallConfig.thickness_tolerance` invece che scritte come
    numeri che «funzionano», cosi' il test segue il predefinito se cambia
    invece di rompersi in silenzio. E' il confronto -- stesso confine
    geometrico, tolleranza sotto contro sopra -- a dimostrare che e' la
    tolleranza a decidere: un `regioni` che ignorasse `thickness_tolerance` e
    facesse solo componenti connesse fonderebbe entrambi i casi in una regione
    sola, e solo il secondo assert lo smentirebbe."""
    tolleranza = _cfg().thickness_tolerance
    base = 200.0

    def scomponi_con_spessore(spessore_secondo_prisma: float) -> tuple[list[np.ndarray], dict]:
        prismi = [
            ((0.0, 0.0, 0.0), (600.0, base, 500.0)),
            ((600.0, 0.0, 0.0), (600.0, spessore_secondo_prisma, 500.0)),
        ]
        punti = synth.sample_frame_surface(prismi, SPAZIATURA)
        return wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    sotto_soglia = base * (1.0 + tolleranza / 2.0)  # scarto relativo meta' della tolleranza
    sopra_soglia = base * (1.0 + tolleranza * 3.0)  # scarto relativo tre volte la tolleranza

    regioni_fuse, metriche_fuse = scomponi_con_spessore(sotto_soglia)
    assert len(regioni_fuse) == 1
    assert metriche_fuse["regioni_trovate"] == 1

    regioni_separate, metriche_separate = scomponi_con_spessore(sopra_soglia)
    assert len(regioni_separate) == 2
    assert metriche_separate["regioni_trovate"] == 2


def test_una_sezione_uniforme_e_un_canarino_per_la_separazione_per_orientamento():
    """Non e' una prova di correttezza dell'algoritmo attuale: e' un canarino.

    La scomposizione separa le membrature per costanza dello spessore locale.
    Un telaio a sezione uniforme e' un anello fisicamente continuo con
    spessore identico ovunque, quindi restituisce una regione sola per pura
    geometria -- lo farebbe anche un `regioni` che ignorasse del tutto
    `thickness_tolerance` e facesse solo componenti connesse. Questo test da
    solo non dimostra che la tolleranza lavora (per quello vedi
    `test_la_tolleranza_di_spessore_decide_fra_una_regione_e_due`): dichiara
    invece il confine del metodo attuale, che non separa membrature adiacenti
    a sezione uguale (qui un piedritto e una trave, uniti a Π). Non e' un
    risultato falso in silenzio: una regione a Π non e' un prisma, quindi il
    controllo di costanza della sezione del Task 3 la scartera' con il
    proprio motivo. Il giorno in cui qualcuno implementasse la separazione per
    orientamento locale (vedi il commento `ponytail:` su `regioni` in
    `wall.py`), e' questo test che smettera' di passare, ed e' il segnale
    giusto per riscriverlo."""
    telaio_a_sezione_uniforme = [
        ((0.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),      # montante sinistro
        ((1400.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),   # montante destro
        ((0.0, 0.0, 1600.0), (1600.0, 200.0, 300.0)),   # traverso superiore
        ((0.0, 0.0, -300.0), (1600.0, 200.0, 300.0)),   # traverso inferiore
    ]
    punti = synth.sample_frame_surface(telaio_a_sezione_uniforme, SPAZIATURA)

    regioni, metriche = wall.scomponi(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert len(regioni) == 1
    assert metriche["regioni_trovate"] == 1
