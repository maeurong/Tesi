"""L'armatura si colloca, e la sezione si giudica -- una stazione alla volta.

I numeri attesi sono trascritti da
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md` e da
`docs/validazione/ricerca-armature-convenzioni-normative.md`, che li hanno
verificati contro le NTC 2018 e la Circolare. Non si ricalcolano qui le formule
del modulo per confrontarle col modulo: sarebbe la stessa espressione scritta
due volte, e non ucciderebbe una formula sbagliata.

Un solo genere di ingresso ferma il calcolo, ed e' la geometria impossibile: una
sezione sotto il minimo di norma e' un **risultato** che si mostra, non un
errore che rifiuta il modello (#136).
"""

import math

import numpy as np
import pytest

from meshrec.core.armatura import (
    BarraCollocata,
    VerdettoStazione,
    bilanciata,
    colloca,
    verdetti,
)
from meshrec.core.config import ArmaturaConfig

# `f_ctm` non sta nel catalogo dei materiali -- `core/materiali.py` lo dichiara
# fuori nel proprio docstring -- e per questo `verdetti` lo riceve. 2,56 MPa e'
# il valore della C25/30 nella tabella della ricerca, §6.1.
F_CTM_C25_30 = 2.56


def _armatura(**campi) -> ArmaturaConfig:
    """Una gabbia che ci sta in 300 x 500, da deformare campo per campo."""
    predefiniti = dict(
        classe_calcestruzzo="C25/30",
        classe_acciaio="B450C",
        barre_tese=4,
        diametro_teso=16,
        barre_compresse=2,
        diametro_compresso=16,
        diametro_staffe=8,
        passo_staffe=150.0,
        copriferro_nominale=30.0,
    )
    return ArmaturaConfig(**{**predefiniti, **campi})


def _una_stazione(sezione, **campi) -> VerdettoStazione:
    esiti = verdetti(
        _armatura(**campi),
        np.asarray([sezione], dtype=np.float64),
        np.asarray([0.0]),
        F_CTM_C25_30,
    )
    assert len(esiti) == 1
    return esiti[0]


def test_l_oracolo_di_collaudo_parte_da_rck_30_con_es_200000_e_alfa_esatto():
    """`R_ck` = 30, B450C, `E_s` = 200.000: `k_bil` = 0,641434 e `mu_bil` = 1,872%.

    **I due ingressi vanno dichiarati o l'oracolo non e' riproducibile.** Parte
    da `R_ck` = 30 e **non** dalla classe C25/30, che avrebbe `f_ck` = 25 per
    definizione e darebbe `f_cd` = 14,1667 -- uno scarto dello 0,4%, cioe' il
    modo peggiore di fallire. E usa `E_s` = 200.000, il valore che il catalogo
    porta: con i 210.000 della Circolare §C4.1.2.2.5 `k_bil` passerebbe a
    0,652577 e l'oracolo fallirebbe alla terza cifra.

    Il terzo ingresso implicito e' alpha = 0,809524 esatto e non lo 0,81 con cui
    la dispensa lo arrotonda: fra le due varianti corrono 0,06%, sotto la terza
    cifra ma sopra i cinque decimali che questo test confronta.

    Verificato per tre vie indipendenti nella ricerca, §5.3: ricalcolo diretto,
    il conto della dispensa, e l'interpolazione sulle tavole di flessione.
    """
    f_ck_da_rck = 0.83 * 30.0  # [11.2.1], e vale sul capitolato, non sul nome della classe
    f_cd = 0.85 * f_ck_da_rck / 1.5  # [4.1.3]
    f_yd = 450.0 / 1.15  # [4.1.5]
    assert f_cd == pytest.approx(14.110, abs=5e-4)

    k_bil, mu_bil = bilanciata(f_cd, f_yd, 200000.0)

    assert k_bil == pytest.approx(0.641434, abs=5e-7)
    assert mu_bil == pytest.approx(0.018724, abs=5e-7)


def test_con_es_210000_l_oracolo_non_torna_e_il_numero_e_quello_dichiarato():
    """La divergenza fra le due fonti su `E_s` vale 1,7% su `k_bil`, ricerca §2.3.

    Non e' un doppione dell'oracolo: sorveglia che `E_s` sia davvero un ingresso
    e non una costante murata nel modulo. Mutazione che lo uccide: sostituire
    l'argomento con 200.000 dentro `bilanciata`.
    """
    k_bil, _ = bilanciata(0.85 * 0.83 * 30.0 / 1.5, 450.0 / 1.15, 210000.0)

    assert k_bil == pytest.approx(0.652577, abs=5e-7)


def test_zero_stazioni_nessun_verdetto_invece_di_uno_su_una_sezione_media():
    """Una membratura senza fette misurabili non ha sezioni da giudicare.

    E' il predefinito di `wall.Membratura.sezioni_fette` (`core/wall.py:458`):
    un prior scritto prima che la misura esistesse non porta ne' le sezioni ne'
    le quote ne' `base_sezione` -- `pipeline._membrature_dal_prior` le legge
    tutte e tre con `.get`, quindi mancano insieme. Nessun verdetto fabbricato
    sulla `sezione` media, che e' una sintesi e non una stazione.
    """
    esiti = verdetti(_armatura(), np.zeros((0, 2)), np.zeros(0), F_CTM_C25_30)

    assert esiti == []


def test_lunghezze_diverse_rifiutate_dicendo_quali_invece_di_un_indexerror():
    """`sezioni_fette` e `quote_fette` hanno la stessa lunghezza per contratto.

    Se non l'hanno, lo scorrimento silenzioso di una posizione sposterebbe ogni
    verdetto sulla quota sbagliata. Il rifiuto porta i due numeri.
    """
    with pytest.raises(ValueError, match=r"3.*2|2.*3"):
        verdetti(
            _armatura(),
            np.asarray([[300.0, 500.0], [300.0, 500.0], [300.0, 500.0]]),
            np.asarray([0.0, 100.0]),
            F_CTM_C25_30,
        )


def test_le_barre_che_non_ci_stanno_fermano_nominando_la_stazione():
    """L'unica guardia che ferma: geometria impossibile, non norma disattesa.

    Larghezza 130 mm, luce fra le staffe 130 - 2*(30 + 8) = 54 mm, e quattro
    barre da 16 ne ingombrano 64. Non c'e' una sezione da descrivere.
    """
    with pytest.raises(ValueError, match="quota"):
        _una_stazione((130.0, 500.0))


def test_la_sezione_di_area_nulla_ferma_come_ogni_altra_geometria_impossibile():
    """Una fetta 0 x 0 non ospita nessuna barra: e' il caso limite della guardia.

    Il messaggio nomina la stazione, come per ogni altra sezione troppo stretta.
    """
    with pytest.raises(ValueError, match="quota"):
        _una_stazione((0.0, 0.0))


def test_il_copriferro_oltre_meta_altezza_ferma_perche_la_sezione_non_esiste():
    """`d = H - c - Ø_staffa - Ø_long/2` a 40 - 30 - 8 - 8 = -6 mm.

    Non e' una sezione sotto-armata: e' una sezione in cui l'armatura tesa
    cadrebbe fuori dal calcestruzzo. Stessa guardia delle barre che non ci
    stanno in larghezza, letta lungo l'altra direzione.
    """
    with pytest.raises(ValueError, match="quota"):
        _una_stazione((300.0, 40.0))


def test_l_interferro_netto_zero_e_accettato_e_il_numero_si_mostra():
    """Larghezza 140: la luce fra le staffe e' 64 mm e le quattro barre da 16 la riempiono.

    Ci stanno **appena**. Le NTC non danno un interferro minimo -- §4.1.6.1.3 lo
    rapporta alla dimensione degli inerti, che nessun campo dichiara -- quindi
    qui si misura e si mostra, non si giudica.
    """
    stazione = _una_stazione((140.0, 500.0))

    assert stazione.interferro_netto == pytest.approx(0.0, abs=1e-9)


def test_l_interferro_netto_e_la_distanza_libera_fra_le_barre_tese():
    """300 - 2*(30 + 8) - 4*16 = 160 mm su tre intervalli.

    E' la distanza **libera**, non l'interasse: NTC 2018 §4.1.6.1.3, e la
    ricerca sulle convenzioni §1.4.
    """
    stazione = _una_stazione((300.0, 500.0))

    assert stazione.interferro_netto == pytest.approx(160.0 / 3.0)


def test_il_copriferro_netto_e_quello_alla_barra_longitudinale_non_il_dichiarato():
    """L'operatore dichiara 30 alla staffa; la barra longitudinale ne ha 38.

    Ricerca sulle convenzioni §1.3: «il copriferro si misura alla staffa, non
    alla barra longitudinale, quando la staffa e' piu' esterna -- che e' il caso
    normale». Il numero vero e' quello che copre la barra, ed e' calcolato.
    """
    stazione = _una_stazione((300.0, 500.0))

    assert stazione.copriferro_netto == pytest.approx(38.0)


def test_l_altezza_utile_scende_dal_copriferro_dalla_staffa_e_da_mezza_barra():
    """`d` = 500 - 30 - 8 - 16/2 = 454 mm."""
    stazione = _una_stazione((300.0, 500.0))

    assert stazione.d == pytest.approx(454.0)


def test_base_e_altezza_non_si_scambiano_quando_la_sezione_e_stretta_lungo_e1():
    """La colonna 0 di `sezioni_fette` e' sempre `e1` e la colonna 1 sempre `e2`.

    `core/wall.py:458` lo fissa. Un `min`/`max` che raddrizzasse la sezione
    renderebbe indistinguibili una trave 300x500 e una 500x300, che hanno
    altezza utile e rapporto geometrico diversi.
    """
    alta = _una_stazione((300.0, 500.0))
    larga = _una_stazione((500.0, 300.0))

    assert alta.b == pytest.approx(300.0)
    assert alta.h == pytest.approx(500.0)
    assert larga.b == pytest.approx(500.0)
    assert larga.h == pytest.approx(300.0)
    assert larga.d == pytest.approx(254.0)
    assert alta.mu != pytest.approx(larga.mu)


def test_la_sezione_sotto_il_minimo_di_norma_e_fragile_e_il_verdetto_esce_lo_stesso():
    """Due barre da 6 in una 300x500: `mu` = 0,041% contro `mu_min` = 0,148%.

    #136: il programma rileva, non progetta. Una sezione sotto il minimo e' cio'
    che l'operatore ha misurato su un edificio esistente, e il modello si
    costruisce comunque.
    """
    stazione = _una_stazione((300.0, 500.0), barre_tese=2, diametro_teso=6)

    assert stazione.verdetto == "fragile"
    assert stazione.mu < stazione.mu_min


def test_il_minimo_di_norma_e_il_maggiore_fra_la_formula_e_lo_0_13_percento():
    """`A_s,min = 0,26 (f_ctm/f_yk) b_t d` e comunque `>= 0,0013 b_t d` -- NTC 2018 [4.1.45].

    Sulla C25/30 comanda la formula: 0,26 * 2,56 / 450 = 0,00148 > 0,0013.
    """
    stazione = _una_stazione((300.0, 500.0))

    assert stazione.mu_min == pytest.approx(0.26 * F_CTM_C25_30 / 450.0)


def test_il_minimo_assoluto_governa_quando_la_formula_scende_sotto_lo_0_13_percento():
    """`f_ctm` = 2,21 della C20/25 da' 0,00128, e il minimo assoluto lo supera.

    Ricerca §6.1: «il minimo assoluto governa quando 0,26 f_ctm/f_yk < 0,0013,
    cioe' fino alla C25/30 compresa». La C20/25 e' il caso al confine.
    """
    esiti = verdetti(
        _armatura(classe_calcestruzzo="C20/25"),
        np.asarray([[300.0, 500.0]]),
        np.asarray([0.0]),
        2.21,
    )

    assert esiti[0].mu_min == pytest.approx(0.0013)


def test_oltre_la_bilanciata_e_un_verdetto_dichiarato_non_un_rifiuto():
    """Sei barre da 25 in una 300x500: `mu` = 2,18% contro `mu_bil` = 1,88%.

    Il valore atteso di `mu_bil` per la C25/30 e' quello della ricerca §5.4.
    """
    stazione = _una_stazione((300.0, 500.0), barre_tese=6, diametro_teso=25)

    assert stazione.verdetto == "oltre_la_bilanciata"
    assert stazione.mu > stazione.mu_bil
    assert stazione.mu_bil == pytest.approx(0.0188, abs=5e-5)


def test_la_sezione_fra_i_due_estremi_e_duttile():
    stazione = _una_stazione((300.0, 500.0))

    assert stazione.verdetto == "duttile"
    assert stazione.mu_min < stazione.mu < stazione.mu_bil


def test_l_armatura_semplice_non_fa_saltare_nessun_ramo():
    """`barre_compresse = 0` e' l'armatura semplice, non un errore.

    I tre rapporti si calcolano lo stesso: nessuno dei tre dipende
    dall'armatura compressa.
    """
    semplice = _una_stazione((300.0, 500.0), barre_compresse=0)
    doppia = _una_stazione((300.0, 500.0))

    assert semplice.verdetto == "duttile"
    assert semplice.mu == pytest.approx(doppia.mu)
    assert semplice.mu_min == pytest.approx(doppia.mu_min)
    assert semplice.mu_bil == pytest.approx(doppia.mu_bil)


def test_due_stazioni_della_stessa_membratura_portano_due_verdetti_e_due_quote():
    """La sezione cambia lungo l'asse, e con essa il verdetto.

    Un verdetto solo per membratura appiattirebbe una gabbia che e' duttile a
    una stazione e fragile a un'altra.
    """
    esiti = verdetti(
        _armatura(barre_tese=2, diametro_teso=6),
        np.asarray([[300.0, 500.0], [300.0, 120.0]]),
        np.asarray([250.0, 2750.0]),
        F_CTM_C25_30,
    )

    assert [e.quota for e in esiti] == [250.0, 2750.0]
    assert esiti[0].d > esiti[1].d


def test_la_classe_fuori_catalogo_arriva_col_rifiuto_leggibile_di_materiali_trova():
    """`materiali.trova` elenca le classi che esistono, e quel messaggio non va coperto."""
    with pytest.raises(KeyError, match="C25/31"):
        _una_stazione((300.0, 500.0), classe_calcestruzzo="C25/31")


def test_le_classi_oltre_c50_60_dichiarano_il_dato_che_manca_invece_di_indovinarlo():
    """L'esponente della parabola oltre la C50/60 e' [NON TROVATO], ricerca §4.2.

    Senza l'esponente, alpha non si ricava e `mu_bil` non e' calcolabile. Il
    rifiuto nomina il dato che manca invece di riusare 0,809524, che vale solo
    per le classi fino alla C50/60 (§4.1.2.1.2.1).
    """
    with pytest.raises(ValueError, match="esponente"):
        _una_stazione((300.0, 500.0), classe_calcestruzzo="C55/67")


def test_la_stessa_membratura_calcolata_due_volte_da_gli_stessi_verdetti():
    """Un esito discreto che cambia fra due corse e' un difetto di prodotto."""
    sezioni = np.asarray([[300.0, 500.0], [280.0, 460.0], [300.0, 120.0]])
    quote = np.asarray([250.0, 1500.0, 2750.0])
    armatura = _armatura(barre_tese=2, diametro_teso=6)

    prima = verdetti(armatura, sezioni, quote, F_CTM_C25_30)
    seconda = verdetti(armatura, sezioni, quote, F_CTM_C25_30)

    assert prima == seconda


def test_le_barre_si_collocano_dentro_la_sezione_e_simmetriche_sulla_larghezza():
    """Quattro tese in basso e due compresse in alto, in una 300x500.

    Le posizioni non sono un dato: sono un derivato della sezione della
    stazione, e cambiano stazione per stazione.
    """
    barre = colloca(_armatura(), (300.0, 500.0))

    assert len(barre) == 6
    assert all(isinstance(b, BarraCollocata) for b in barre)
    tese = [b for b in barre if b.z < 250.0]
    compresse = [b for b in barre if b.z > 250.0]
    assert len(tese) == 4
    assert len(compresse) == 2
    assert all(b.z == pytest.approx(30.0 + 8.0 + 8.0) for b in tese)
    assert all(b.z == pytest.approx(500.0 - 30.0 - 8.0 - 8.0) for b in compresse)
    ye = [b.y for b in tese]
    assert ye[0] == pytest.approx(30.0 + 8.0 + 8.0)
    assert ye[-1] == pytest.approx(300.0 - 30.0 - 8.0 - 8.0)
    assert sum(ye) / len(ye) == pytest.approx(150.0)
    assert all(b.diametro == 16.0 for b in barre)


def test_le_barre_si_spostano_quando_la_sezione_della_stazione_cambia():
    """Stessa gabbia dichiarata, due stazioni, due collocamenti diversi."""
    larga = colloca(_armatura(), (300.0, 500.0))
    stretta = colloca(_armatura(), (200.0, 500.0))

    assert [b.y for b in larga] != [b.y for b in stretta]


def test_una_sola_barra_compressa_si_colloca_in_mezzo_alla_larghezza():
    """Con una barra sola non c'e' un interferro da spartire: sta al centro."""
    barre = colloca(_armatura(barre_compresse=1), (300.0, 500.0))

    compresse = [b for b in barre if b.z > 250.0]
    assert len(compresse) == 1
    assert compresse[0].y == pytest.approx(150.0)


def test_l_area_tesa_e_quella_delle_barre_dichiarate():
    """`mu = A_s / (b d)`, e `A_s` sono le sole barre tese."""
    stazione = _una_stazione((300.0, 500.0))
    area = 4 * math.pi * 16.0**2 / 4.0

    assert stazione.mu == pytest.approx(area / (300.0 * 454.0))
