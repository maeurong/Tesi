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
    risultato falso in silenzio: una regione a Π non e' un prisma, e il
    riempimento di sezione del Task 3 la dichiara «vuoto» con la propria misura
    (vedi `test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata`),
    perche' chi costruisce possa rifiutarla. Il giorno in cui qualcuno implementasse la separazione per
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


def test_il_contorno_di_un_rettangolo_ha_quattro_vertici():
    """Il contorno misurato non deve portare nella mesh il rumore dello
    scanner: un rettangolo campionato fitto resta un rettangolo."""
    lato_u = np.linspace(0.0, 200.0, 60)
    lato_v = np.linspace(0.0, 140.0, 40)
    bordo = np.vstack([
        np.column_stack([lato_u, np.zeros_like(lato_u)]),
        np.column_stack([lato_u, np.full_like(lato_u, 140.0)]),
        np.column_stack([np.zeros_like(lato_v), lato_v]),
        np.column_stack([np.full_like(lato_v, 200.0), lato_v]),
    ])

    contorno = wall.semplifica_contorno(bordo, tolleranza=5.0)

    assert len(contorno) == 4, f"attesi 4 vertici, trovati {len(contorno)}"
    assert contorno.min(axis=0) == pytest.approx([0.0, 0.0], abs=1e-9)
    assert contorno.max(axis=0) == pytest.approx([200.0, 140.0], abs=1e-9)


def test_il_contorno_semplificato_non_perde_area_oltre_la_tolleranza():
    """Il controllo che smentisce il precedente: semplificare e' lecito finche'
    l'area della sezione non cambia piu' di quanto la tolleranza consenta."""
    angoli = np.linspace(0.0, 2.0 * np.pi, 400, endpoint=False)
    cerchio = np.column_stack([100.0 * np.cos(angoli), 100.0 * np.sin(angoli)])

    contorno = wall.semplifica_contorno(cerchio, tolleranza=2.0)

    def area(poligono):
        x, y = poligono[:, 0], poligono[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    assert len(contorno) < len(cerchio)
    assert area(contorno) == pytest.approx(area(cerchio), rel=0.05)


def test_la_misura_di_un_prisma_noto_ritrova_sezione_asse_e_lunghezza():
    """Verita' nota del banco: un prisma 200 x 140 lungo 1500 lungo z."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.lunghezza == pytest.approx(1500.0, abs=30.0)
    lunga, corta = sorted(membratura.sezione, reverse=True)
    assert lunga == pytest.approx(200.0, abs=15.0)
    assert corta == pytest.approx(140.0, abs=15.0)
    assert abs(abs(membratura.asse[2]) - 1.0) < 1e-3, "asse atteso verticale"
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.0)
    assert membratura.volume == pytest.approx(200.0 * 140.0 * 1500.0, rel=0.15)


def test_il_fuori_piombo_misura_l_inclinazione_e_il_rigonfiamento_no():
    """Le due grandezze restano distinte perche' sono difetti diversi: un
    elemento puo' essere perfettamente piano e tutto storto, oppure a piombo e
    panciuto. Un prisma inclinato di 4 gradi ha fuori piombo e non pancia."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    angolo = np.radians(4.0)
    rotazione = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(angolo), -np.sin(angolo)],
        [0.0, np.sin(angolo), np.cos(angolo)],
    ])
    inclinati = punti @ rotazione.T
    direzioni, _ = wall.terna(inclinati)

    membratura = wall.misura(inclinati, direzioni, _cfg())

    assert membratura.fuori_piombo_deg == pytest.approx(4.0, abs=1.0)
    assert np.abs(membratura.rigonfiamento).max() < 20.0, (
        "un prisma inclinato ma dritto non deve risultare panciuto: se lo "
        "risulta, il rigonfiamento sta misurando l'inclinazione"
    )


def test_il_rigonfiamento_e_una_mappa_e_trova_la_pancia_dove_c_e():
    """Il controllo che smentisce il precedente: una faccia gonfiata di 25 mm
    al centro deve comparire nella mappa, e nel fuori piombo no."""
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    sulla_faccia = np.isclose(punti[:, 1], 140.0)
    altezza_relativa = (punti[:, 2] - 750.0) / 750.0
    gonfiati = punti.copy()
    gonfiati[sulla_faccia, 1] += 25.0 * (1.0 - altezza_relativa[sulla_faccia] ** 2)
    direzioni, _ = wall.terna(gonfiati)

    membratura = wall.misura(gonfiati, direzioni, _cfg())

    assert membratura.rigonfiamento.ndim == 1
    assert len(membratura.rigonfiamento) > 10, "il rigonfiamento e' una mappa, non un numero"
    assert np.abs(membratura.rigonfiamento).max() > 10.0
    assert membratura.fuori_piombo_deg == pytest.approx(0.0, abs=1.5)


def test_i_controlli_intrinseci_passano_su_un_prisma_pulito():
    punti = synth.sample_box_surface((200.0, 140.0, 1500.0), 15.0)
    direzioni, _ = wall.terna(punti)
    membratura = wall.misura(punti, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert set(esiti) == {"parallelismo", "copertura_faccia", "costanza_sezione"}
    for nome, esito in esiti.items():
        assert esito["passato"] is True, f"{nome} non doveva fallire: {esito}"
        assert "valore" in esito and "soglia" in esito, (
            f"{nome} deve dire quale numero lo ha deciso, non solo se e' passato"
        )


def test_una_regione_a_sezione_variabile_non_e_un_prisma_e_lo_dice():
    """Il controllo che smentisce il prior: un tronco di piramide non e' una
    membratura, e viene riportato come tale invece di essere spacciato per una
    con la sezione media."""
    z = np.linspace(0.0, 1500.0, 120)
    punti = []
    for quota in z:
        mezzo_lato = 100.0 * (1.0 - 0.6 * quota / 1500.0)
        angoli = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        punti.append(np.column_stack([
            mezzo_lato * np.cos(angoli),
            mezzo_lato * np.sin(angoli),
            np.full_like(angoli, quota),
        ]))
    cono = np.vstack(punti)
    direzioni, _ = wall.terna(cono)
    membratura = wall.misura(cono, direzioni, _cfg())

    esiti = wall.controlla(membratura, _cfg())

    assert esiti["costanza_sezione"]["passato"] is False
    assert esiti["costanza_sezione"]["valore"] > esiti["costanza_sezione"]["soglia"]


def test_senza_riscontri_dichiarati_il_prior_non_inventa_un_aspettativa():
    """Su un pezzo nuovo i riscontri non esistono per definizione. Il prior
    riporta cio' che ha trovato, e nel posto dell'atteso non mette un numero."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] is None
    assert riscontri["volume_atteso"] is None
    assert riscontri["scarto_membrature"] is None
    assert riscontri["scarto_volume"] is None
    assert esito["membrature"], "il prior deve comunque riportare cio' che ha trovato"


def test_con_i_riscontri_dichiarati_il_prior_riporta_lo_scarto():
    """I numeri dell'atteso stanno qui, nel test, dove e' legittimo che
    compaiano: sono dati del caso, non del programma."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    volume_vero = sum(dx * dy * dz for _origine, (dx, dy, dz) in TELAIO)
    cfg = WallConfig(membrature_attese=4, volume_atteso=volume_vero)

    esito = wall.prior(punti, SegmentConfig(), cfg, SPAZIATURA)

    riscontri = esito["riscontri"]
    assert riscontri["membrature_attese"] == 4
    assert riscontri["scarto_membrature"] == len(esito["membrature"]) - 4
    assert riscontri["volume_atteso"] == pytest.approx(volume_vero)
    assert riscontri["scarto_volume"] is not None


def test_l_esito_del_prior_e_serializzabile_in_json():
    """Lo step 12 lo scrive su disco e il server lo manda al browser: un array
    di numpy dentro il dizionario romperebbe entrambi dopo l'intera corsa."""
    import json

    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)
    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    testo = json.dumps(esito)
    assert json.loads(testo)["regioni_trovate"] == esito["regioni_trovate"]


def test_il_controllo_di_chiusura_del_volume_confronta_somma_e_unione():
    """Le membrature si compenetrano alle giunzioni: se la somma dei volumi
    supera quello dell'unione oltre la tolleranza, c'e' doppio conteggio, ed e'
    un errore che nessuna metrica di qualita' della mesh vedrebbe."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    chiusura = esito["chiusura_volume"]
    assert chiusura["somma"] > 0.0
    assert chiusura["unione"] > 0.0
    assert isinstance(chiusura["passato"], bool)
    assert chiusura["scarto_relativo"] == pytest.approx(
        (chiusura["somma"] - chiusura["unione"]) / chiusura["unione"]
    )


TELAIO_A_SEZIONE_UNIFORME = [
    ((0.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),      # montante sinistro
    ((1400.0, 0.0, 0.0), (200.0, 200.0, 1600.0)),   # montante destro
    ((0.0, 0.0, 1600.0), (1600.0, 200.0, 300.0)),   # traverso superiore
    ((0.0, 0.0, -300.0), (1600.0, 200.0, 300.0)),   # traverso inferiore
]

# Il banco a densita' bimodale dei due controesempi della terza review: un
# pezzo scansionato da un lato solo. La faccia che guarda lo scanner e' presa
# alla risoluzione piena dello strumento, le pareti che scappano di taglio sono
# sfiorate di striscio e vengono via venti volte piu' rade. Venti e' il
# rapporto di un'incidenza radente attorno agli 87 gradi: non un numero scelto
# per far cadere una soglia, ma il caso che una scansione da un lato solo
# produce per forza.
DENSITA_BIMODALE = (300.0, 300.0, 1500.0)
PASSO_RADO = 100.0
PASSO_FITTO = 5.0


def _faccia_fitta(
    dimensioni: tuple[float, float, float], asse_fisso: int, quota: float, passo: float
) -> np.ndarray:
    """Una faccia rettangolare del parallelepipedo, campionata al passo dato."""
    resto = [indice for indice in range(3) if indice != asse_fisso]
    lati = [dimensioni[indice] for indice in resto]
    numeri = [max(2, int(round(lato / passo)) + 1) for lato in lati]
    u, v = np.meshgrid(
        np.linspace(0.0, lati[0], numeri[0]),
        np.linspace(0.0, lati[1], numeri[1]),
        indexing="ij",
    )
    punti = np.zeros((u.size, 3))
    punti[:, resto[0]] = u.ravel()
    punti[:, resto[1]] = v.ravel()
    punti[:, asse_fisso] = quota
    return punti


def _prisma_a_densita_bimodale(facce_fitte: list[tuple[int, float]]) -> np.ndarray:
    """Prisma pieno con alcune facce fitte e tutte le altre rade."""
    rado = synth.sample_box_surface(DENSITA_BIMODALE, PASSO_RADO)
    fitte = [
        _faccia_fitta(DENSITA_BIMODALE, asse, quota, PASSO_FITTO) for asse, quota in facce_fitte
    ]
    return np.unique(np.round(np.vstack([rado, *fitte]), 9), axis=0)


def test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata():
    """Ruling J: il riempimento misura e dichiara, non scarta.

    La scomposizione fonde due membrature adiacenti a sezione uguale in una
    regione sola a forma di Π (vedi
    `test_una_sezione_uniforme_e_un_canarino_per_la_separazione_per_orientamento`).
    Quella regione non e' un prisma, e il riempimento e' la sola grandezza che
    lo vede: la dispersione e l'estensione, entrambe di bounding box, non
    vedono il vuoto al centro perche' i due piedritti attraversano tutta
    l'altezza e tengono l'ingombro pieno da un capo all'altro.

    Ma vederlo non e' scartarlo. La regione resta fra le membrature con lo
    stato «vuoto» e la misura dichiarata affidabile: e' esattamente
    l'informazione con cui chi costruisce i modelli parametrici (Task 8) puo'
    rifiutarla, senza ricalcolare nulla."""
    punti = synth.sample_frame_surface(TELAIO_A_SEZIONE_UNIFORME, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert esito["regioni_trovate"] == 1, "il banco deve restare il caso limite: una regione a Π sola"
    assert esito["scartate"] == [], (
        f"il riempimento non scarta piu' nessuno: {esito['scartate']}"
    )
    assert len(esito["membrature"]) == 1
    riempimento = esito["membrature"][0]["riempimento"]
    assert riempimento["stato"] == "vuoto", riempimento
    assert riempimento["affidabile"] is True, riempimento
    assert riempimento["valore"] < riempimento["soglia"]


def test_le_membrature_piene_del_telaio_escono_piene():
    """Il controllo che smentisce il controllo: il telaio a sezioni diverse del
    Task 2 e' fatto di prismi veri, nessuno cavo, e ogni regione deve uscire
    «pieno» -- non basta che nessuna sia scartata, perche' ora il riempimento
    non scarta piu' nessuno e un esito sbagliato passerebbe inosservato."""
    punti = synth.sample_frame_surface(TELAIO, SPAZIATURA)

    esito = wall.prior(punti, SegmentConfig(), _cfg(), SPAZIATURA)

    assert esito["scartate"] == [], f"nessuna membratura del telaio doveva essere scartata: {esito['scartate']}"
    assert len(esito["membrature"]) == esito["regioni_trovate"]
    for membratura in esito["membrature"]:
        assert membratura["riempimento"]["stato"] == "pieno", membratura["riempimento"]


def test_i_prismi_pieni_escono_pieni_qualunque_sia_la_loro_forma():
    """Ruling H, ripreso dal Ruling J: cinque prismi pieni, senza alcun vuoto
    -- tozzo, corto, allungato, grande -- devono uscire «pieno». Se il
    riempimento misurasse il bordo invece del vuoto, una colonna tozza o un
    elemento corto uscirebbero «vuoto» come una Π."""
    casi = [
        (200.0, 140.0, 1500.0),
        (300.0, 300.0, 1500.0),
        (500.0, 500.0, 1500.0),
        (200.0, 140.0, 500.0),
        (500.0, 500.0, 500.0),
    ]
    for dimensioni in casi:
        punti = synth.sample_box_surface(dimensioni, SPAZIATURA)
        direzioni, _ = wall.terna(punti)

        membratura = wall.misura(punti, direzioni, _cfg())

        assert membratura.riempimento_stato == "pieno", (
            f"{dimensioni}: stato {membratura.riempimento_stato}, "
            f"valore {membratura.riempimento_sezione}, ma e' un prisma pieno"
        )
        assert membratura.riempimento_sezione > 0.9, f"{dimensioni}: {membratura.riempimento_sezione}"


def test_una_faccia_frontale_fitta_con_pareti_rade_non_e_vuota_ma_non_verificabile():
    """Primo controesempio della terza review, il punto centrale del Ruling J.

    Un prisma **pieno** scansionato da un lato solo: la faccia frontale e' presa
    fitta, le pareti laterali rade. La griglia del riempimento e' costruita su
    una spaziatura media, e una media non descrive una densita' bimodale a
    nessuna scala: il perimetro rado non si chiude, il riempimento crolla, e il
    prisma pieno sembra vuoto. L'esito giusto non e' «vuoto» -- e' «non
    verificabile», perche' e' la misura a non valere, non il pezzo a essere
    cavo."""
    punti = _prisma_a_densita_bimodale([(1, 0.0)])
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.riempimento_stato == "non_verificabile", (
        f"stato {membratura.riempimento_stato}, valore {membratura.riempimento_sezione}, "
        f"dispersione densita' {membratura.densita_dispersione}"
    )


def test_tappi_terminali_fitti_con_pareti_rade_non_sono_vuoti_ma_non_verificabili():
    """Secondo controesempio della terza review: stessa densita' bimodale, ma
    concentrata sui due tappi terminali invece che su una parete laterale. La
    conclusione deve essere la stessa -- non verificabile, non vuoto -- perche'
    il difetto sta nella densita' del campionamento e non in dove capita."""
    punti = _prisma_a_densita_bimodale([(2, 0.0), (2, DENSITA_BIMODALE[2])])
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.riempimento_stato == "non_verificabile", (
        f"stato {membratura.riempimento_stato}, valore {membratura.riempimento_sezione}, "
        f"dispersione densita' {membratura.densita_dispersione}"
    )


def test_una_regione_senza_punti_a_sufficienza_resta_non_verificabile():
    """Una grandezza non misurata non e' una grandezza piena, e non e' nemmeno
    una grandezza vuota. Con troppo pochi punti perche' una sola fetta ne veda
    almeno quattro, lo stato e' «non verificabile» e lo dice."""
    punti_pochi = np.array([
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
        [10.0, 10.0, 10.0],
    ])
    direzioni, _ = wall.terna(punti_pochi)

    membratura = wall.misura(punti_pochi, direzioni, _cfg())

    assert membratura.riempimento_stato == "non_verificabile"


def test_una_regione_rada_ma_uniforme_esce_piena():
    """Ruling I: una porzione di pezzo piu' lontana dallo scanner ha densita'
    locale piu' rada del resto del pezzo. Finche' e' rada in modo uniforme, la
    misura vale e un prisma pieno campionato rado esce «pieno»: e' la
    controprova dei due controesempi qui sopra, dove a mancare non e' la
    densita' ma la sua uniformita'."""
    punti = synth.sample_box_surface((300.0, 300.0, 1500.0), 70.0)
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.riempimento_stato == "pieno", (
        f"stato {membratura.riempimento_stato}, dispersione densita' "
        f"{membratura.densita_dispersione}"
    )


def test_una_pi_molto_rada_non_esce_piena():
    """Il controllo che smentisce il precedente: una Π vera, campionata cosi'
    rada che la griglia locale copre la sezione con troppo poche celle per
    vedere il vuoto, non deve uscire «pieno» -- deve dichiararsi non
    verificabile."""
    punti = synth.sample_frame_surface(TELAIO_A_SEZIONE_UNIFORME, 200.0)
    direzioni, _ = wall.terna(punti)

    membratura = wall.misura(punti, direzioni, _cfg())

    assert membratura.riempimento_stato == "non_verificabile", (
        f"stato {membratura.riempimento_stato}, valore {membratura.riempimento_sezione}"
    )
