"""Il catalogo dei materiali e' una tabella di norma, non numeri sparsi nel codice.

Stessa disciplina di `tests/test_soglie.py`, e per la stessa ragione: una voce
senza fonte non deve essere rappresentabile, e una voce che si giustifica da se'
-- col catalogo stesso, con una dispensa, con «da progetto» -- non e' una voce di
norma. Il registro delle soglie ha gia' pagato quell'errore una volta (la fonte
«Benzley» accanto a un numero che in Benzley non c'e'), e qui si evita per
imitazione invece che per esperienza.

Cio' che questi test **non** fanno e' ricalcolare le formule del modulo per
confrontarle con il modulo: sarebbe la stessa espressione scritta due volte, e
non ucciderebbe una formula sbagliata. I numeri attesi sono trascritti da
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md`, che li ha
verificati contro le NTC e, per l'oracolo, per tre vie indipendenti.
"""

import math
import re
from datetime import date

import pytest

from meshrec.core import materiali
from meshrec.core.materiali import (
    ALFA_CC,
    CATALOGO,
    FISSATA,
    GAMMA_C,
    GAMMA_S,
    VoceMateriale,
    trova,
    valori_di_progetto,
)


def _voce(**campi) -> VoceMateriale:
    """Una `VoceMateriale` valida, da deformare campo per campo nei casi limite."""
    predefiniti = dict(
        classe="C25/30",
        famiglia="calcestruzzo",
        young=31475.8,
        poisson=0.2,
        density=2.5493e-9,
        f_k=25.0,
        fonte="NTC 2018 §4.1, Tab. 4.1.I",
        origine="derivata",
        fissata=FISSATA,
        nota="",
    )
    return VoceMateriale(**{**predefiniti, **campi})


# --- il registro ---------------------------------------------------------


def test_il_catalogo_non_e_vuoto_e_porta_tutte_e_due_le_famiglie():
    """Un catalogo senza voci e' un difetto, non uno stato.

    E' la classe di difetto piu' frequente di questo repository -- l'insieme
    vuoto che passa inosservato invece di dichiararsi -- e qui morde due volte:
    un catalogo vuoto, o un catalogo che perde per strada una delle due
    famiglie, lascerebbe `trova` a sollevare sempre senza che nulla lo dica.
    """
    assert CATALOGO, "catalogo vuoto: nessuna classe di materiale dichiarata"
    assert {v.famiglia for v in CATALOGO} == {"calcestruzzo", "acciaio"}


def test_ogni_voce_porta_una_fonte_e_una_data():
    """Mutazione che lo uccide: aggiungere una `VoceMateriale` con `fonte=""`."""
    senza_fonte = [v.classe for v in CATALOGO if not v.fonte.strip()]
    assert not senza_fonte, f"voci senza fonte: {senza_fonte}"

    senza_data = [v.classe for v in CATALOGO if not isinstance(v.fissata, date)]
    assert not senza_data, f"voci senza data di fissazione: {senza_data}"


def test_le_fonti_non_sono_autoreferenziali():
    """Una voce non si giustifica da se', ne' con una dispensa.

    Tre modi di scriverlo che sarebbero tutti sbagliati: il catalogo stesso
    (`core/materiali.py`), il materiale del corso (`Lezioni CLS/`,
    `Domini_NM_DM2018`, `Tabelle_flessione_SL_2018`), e «da progetto», che non e'
    una fonte ma l'assenza di una. Le dispense spiegano la norma e non la
    sostituiscono; e chi clona il repository non le ha.

    Mutazione che lo uccide: dare a una voce `fonte="Lezioni 35-36, tabella"`.
    """
    interna = re.compile(
        r"(core/|src/|meshrec|runs/|tests/|Lezioni|dispensa|Domini_NM|Tabelle_flessione"
        r"|da progetto|catalogo)",
        re.IGNORECASE,
    )
    autoreferenziali = [v.classe for v in CATALOGO if interna.search(v.fonte)]
    assert not autoreferenziali, (
        f"voci giustificate da noi stessi o da una dispensa invece che dalla norma: "
        f"{autoreferenziali}"
    )


def test_le_due_classi_gia_in_uso_non_dichiarano_la_tab_4_1_i_come_proprio_elenco():
    """La Tab. 4.1.I elenca quindici classi, e il catalogo ne porta diciassette.

    Riga 2126 delle NTC, verbatim: C8/10, C12/15, C16/20, C20/25, C25/30,
    C30/37, C35/45, C40/50, C45/55, C50/60, C55/67, C60/75, C70/85, C80/95,
    C90/105. **Quindici.** C28/35 e C32/40 vengono dalla frase che segue, riga
    2128: «Oltre alle classi di resistenza riportate in Tab. 4.1.I si possono
    prendere in considerazione le classi di resistenza gia' in uso C28/35 e
    C32/40».

    La `nota` di quelle due righe lo diceva gia', ma la `fonte` -- il campo che
    questi test sorvegliano -- attribuiva a entrambe l'elenco della tabella, e
    per due righe su diciassette era falso.

    Mutazione che lo uccide: rendere la fonte del calcestruzzo di nuovo unica.
    """
    for classe in ("C28/35", "C32/40"):
        fonte = trova(classe).fonte
        assert "elenco delle classi" not in fonte, (
            f"{classe} non sta nell'elenco della Tab. 4.1.I: la tabella ne porta quindici"
        )
        assert "gia' in uso" in fonte or "già in uso" in fonte

    assert "Tab. 4.1.I (elenco delle classi)" in trova("C25/30").fonte
    assert "Tab. 4.1.I (elenco delle classi)" in trova("C90/105").fonte


def test_ogni_voce_nostra_dichiara_perche_e_nostra():
    """Come `test_soglie.py` gia' fa per le soglie.

    Vale in particolare per l'acciaio, la cui `origine` e' `nostra` per un solo
    motivo: `E_s` e' una scelta fra due fonti che divergono. Senza nota, quella
    scelta sparirebbe.
    """
    mute = [v.classe for v in CATALOGO if v.origine == "nostra" and not v.nota.strip()]
    assert not mute, f"voci nostre senza una nota che dica perche': {mute}"


def test_ogni_origine_e_una_delle_tre_dichiarate():
    ammesse = {"letta", "derivata", "nostra"}
    fuori = {v.origine for v in CATALOGO} - ammesse
    assert not fuori, f"origini non dichiarate: {fuori}"


def test_le_classi_non_collidono_nemmeno_ignorando_il_caso():
    """Due voci con la stessa classe: l'ultima vincerebbe in silenzio.

    `trova` normalizza il caso, quindi la collisione va cercata sulla stessa
    chiave normalizzata: «C25/30» e «c25/30» sarebbero due righe distinte nella
    tupla e una sola raggiungibile.
    """
    chiavi = [v.classe.strip().upper() for v in CATALOGO]
    doppie = sorted({c for c in chiavi if chiavi.count(c) > 1})
    assert not doppie, f"due voci con la stessa classe: {doppie}"


def test_ogni_f_k_e_positivo():
    """`f_k` nullo o negativo non e' impossibile per costruzione: e' rifiutato qui.

    `VoceMateriale` e' una `NamedTuple`, quindi un `f_k=0.0` e' costruibile --
    vincolare il tipo renderebbe impossibile fabbricare una voce nei test, come
    `soglie.Soglia` dichiara per la propria `fonte`. Il controllo sta sul
    registro, dove serve, e `valori_di_progetto` lo ripete sul proprio ingresso
    perche' accetta anche voci che il registro non ha filtrato.
    """
    non_positivi = [v.classe for v in CATALOGO if not math.isfinite(v.f_k) or v.f_k <= 0.0]
    assert not non_positivi, f"voci con resistenza caratteristica non positiva: {non_positivi}"


def test_il_catalogo_e_immutabile():
    """La mutazione che uccide: trasformare `VoceMateriale` in una dataclass mutabile.

    Un catalogo riscrivibile a runtime permetterebbe di alzare un `f_ck` dopo
    aver visto il verdetto della sezione, che e' il difetto che tenere la
    tabella come dato esiste per impedire.
    """
    with pytest.raises(AttributeError):
        CATALOGO[0].f_k = 999.0  # type: ignore[misc]
    assert isinstance(CATALOGO, tuple)
    assert all(isinstance(v, tuple) for v in CATALOGO)


# --- i numeri, trascritti dalla ricerca e non ricalcolati ----------------


def test_il_nome_della_classe_porta_f_ck_e_non_r_ck():
    """La divergenza della §1.3 della ricerca, fissata in un test.

    «C25/30» e' la coppia normalizzata `f_ck`/`R_ck` di UNI EN 206: `f_ck` = 25
    per definizione. Chi applicasse `f_ck = 0,83 · R_ck` al secondo numero del
    nome otterrebbe 24,9 sulla C25/30 e sbaglierebbe fino al 6,7% sulla C35/45.

    Mutazione che lo uccide: costruire il catalogo da `R_ck` con la `[11.2.1]`.
    """
    assert trova("C25/30").f_k == pytest.approx(25.0)
    assert trova("C35/45").f_k == pytest.approx(35.0)
    assert trova("C8/10").f_k == pytest.approx(8.0)


def test_il_modulo_elastico_e_quello_della_formula_non_quello_pubblicato_altrove():
    """La C8/10 vale 25.331 MPa, non 25.393.

    `docs/validazione/ricerca-armature-convenzioni-normative.md` §4.2 pubblicava
    25.393 per questa sola riga; le altre sedici coincidono cifra per cifra fra
    le due ricerche, quindi era un refuso isolato. `22000·(16/10)^0,3` =
    25.331,37, e quel documento e' stato corretto insieme a questo test.
    """
    assert trova("C8/10").young == pytest.approx(25331.37, abs=0.01)
    assert trova("C25/30").young == pytest.approx(31475.81, abs=0.01)
    assert trova("C90/105").young == pytest.approx(43630.53, abs=0.01)


def test_il_calcestruzzo_porta_poisson_non_fessurato_e_la_densita_dell_armato():
    """I due numeri che non vengono dalla cascata delle resistenze.

    Poisson: le NTC §11.2.10.4 danno un intervallo i cui due estremi sono due
    modelli diversi, 0 (fessurato) e 0,2 (non fessurato). Un'analisi elastica
    lineare e' il secondo.

    Densita': Tab. 3.1.I da' 25,0 kN/m³ per il calcestruzzo armato, cioe'
    2,5493·10⁻⁹ t/mm³ con g = 9,80665 m/s². Non e' il 2,5·10⁻⁹ di prassi che le
    corse del progetto usano, che vale 24,52 kN/m³.
    """
    voce = trova("C25/30")
    assert voce.poisson == pytest.approx(0.2)
    assert voce.density == pytest.approx(2.5493e-9, rel=1e-4)


def test_le_due_classi_di_acciaio_hanno_la_stessa_resistenza():
    """L'equivoco piu' facile da commettere in un menu' a tendina.

    NTC §11.3.2.2: il B450A e' «caratterizzato dai medesimi valori nominali
    della tensione di snervamento e della tensione a carico massimo
    dell'acciaio B450C». Differiscono per duttilita' e per diametri ammessi, non
    per resistenza.
    """
    assert trova("B450A").f_k == pytest.approx(450.0)
    assert trova("B450C").f_k == pytest.approx(450.0)
    assert trova("B450A").young == trova("B450C").young


def test_l_acciaio_dichiara_la_divergenza_sul_modulo_elastico():
    """200.000 MPa, e la nota dice che l'altra fonte ne da' 210.000.

    Le NTC non pubblicano `E_s`. La Circolare §C4.1.2.2.5 da' 210.000 in un
    paragrafo sulle tensioni in esercizio; UNI EN 1992-1-1 §3.2.7(4) da'
    200.000, ed e' il valore con cui l'oracolo di collaudo torna. Nascondere la
    divergenza renderebbe il numero indistinguibile da un dato di norma.

    **Il paragrafo e' il §C4.1.2.2.5 e non il §C4.1.2.2.5.1**, che nella
    Circolare non esiste: `grep -c "C4.1.2.2.5.1"` sul convertito ne da' zero. Il
    210.000 sta alla riga 2664, dentro il §C4.1.2.2.5 «Stato Limite di
    limitazione delle tensioni». Fino al 2026-08-30 questo test asseriva
    l'articolo inesistente, cioe' inchiodava la citazione falsa e la faceva
    sembrare verificata.

    Mutazione che lo uccide: scrivere 210.000 senza toccare la nota, o rimettere
    nella nota il paragrafo che non esiste.
    """
    voce = trova("B450C")
    assert voce.young == pytest.approx(200000.0)
    assert voce.origine == "nostra"
    assert "210.000" in voce.nota
    assert "C4.1.2.2.5" in voce.nota
    assert "C4.1.2.2.5.1" not in voce.nota, (
        "il §C4.1.2.2.5.1 non esiste nella Circolare: il 210.000 sta nel §C4.1.2.2.5"
    )
    assert "3.2.7" in voce.nota


def test_l_autorizzazione_ministeriale_e_attribuita_alla_fonte_che_la_porta():
    """La frase e' della Circolare, non del §11.1 caso C) delle NTC.

    Le NTC alla riga 2128 dicono soltanto «Per classi di resistenza superiore a
    C70/85 si rinvia al caso C) del § 11.1», e il §11.1 caso C) (riga 6278) usa
    parole diverse: «dovra' ottenere un "Certificato di Valutazione Tecnica"
    rilasciato dal Presidente del Consiglio Superiore dei Lavori Pubblici,
    previa istruttoria del Servizio Tecnico Centrale». La parola
    «autorizzazione ministeriale» la porta la Circolare 7/2019 §CC4.1, riga
    2465: «Per le Classi di resistenza superiori a C70/85 deve essere richiesta
    l'autorizzazione ministeriale mediante le procedure gia' stabilite per altri
    materiali "innovativi"». Il meccanismo e' lo stesso, la parola no.

    Mutazione che lo uccide: rimettere la frase accanto al solo §11.1.
    """
    nota = trova("C80/95").nota
    assert "autorizzazione ministeriale" in nota
    assert "Circolare" in nota, (
        "la frase e' attribuita a un articolo che non la porta: la parola e' della Circolare"
    )
    assert "§11.1" in nota, "il rinvio delle NTC al caso C) del §11.1 resta il meccanismo"


def test_ogni_voce_di_calcestruzzo_dichiara_le_due_scelte_che_la_norma_lascia_aperte():
    """Il modulo detta la regola e deve applicarla a se stesso.

    La regola scritta nel docstring del modulo e' che una scelta va dichiarata
    anche «dove la fonte ne pubblica due che divergono». Ne pubblica due, due
    volte: il §11.2.10.4 da' Poisson «compreso tra 0 (calcestruzzo fessurato) e
    0,2 (calcestruzzo non fessurato)», che sono due modelli e non un intervallo
    di incertezza; la Tab. 3.1.I da' 24,0 kN/m³ per il calcestruzzo ordinario e
    25,0 per l'armato. Le diciassette righe prendono l'estremo alto tutte e due
    le volte.

    L'`origine` resta `derivata` -- la resistenza, che e' la grandezza
    principale della riga, lo e' davvero -- quindi la scelta o sta nella nota o
    non sta da nessuna parte.

    Mutazione che lo uccide: togliere il preambolo comune dalle note di classe.
    """
    for voce in CATALOGO:
        if voce.famiglia != "calcestruzzo":
            continue
        assert "11.2.10.4" in voce.nota, voce.classe
        assert "0,2" in voce.nota, voce.classe
        assert "3.1.I" in voce.nota, voce.classe
        assert "25,0" in voce.nota, voce.classe
        assert "24,0" in voce.nota, voce.classe


def test_ogni_voce_di_calcestruzzo_dichiara_lo_scarto_con_le_corse_di_riferimento():
    """1,972%: il 2,5493e-9 di norma contro il 2,5e-9 che le corse usano.

    `casi/lab.yaml`, `casi/lab_telaio.yaml`, `casi/prova-interfaccia.yaml` e i due
    `lab_telaio_v4_posizionati*.yaml` girano con 2,5e-9 t/mm³. Il catalogo tiene
    il valore di norma, perche' 25,0 kN/m³ e' quello che la Tab. 3.1.I pubblica
    per il calcestruzzo **armato** e le sezioni servite sono armate, e perche' le
    corse di riferimento sono dati di tesi in sola lettura.

    Non c'e' rischio di sovrascrittura silenziosa: la densita' sta in
    `analysis.material` e quindi dentro l'impronta, quindi una corsa col valore
    di catalogo finisce in un'altra cartella. Il rischio e' di lettura -- chi
    confronta un risultato nuovo con uno vecchio non saprebbe perche' non
    tornano -- ed e' quello che questa nota chiude.

    Mutazione che lo uccide: togliere lo scarto dalla nota lasciando la densita'.
    """
    for voce in CATALOGO:
        if voce.famiglia != "calcestruzzo":
            continue
        assert "2,5e-9" in voce.nota, voce.classe
        assert "1,972" in voce.nota, voce.classe


# --- trova ---------------------------------------------------------------


def test_trova_dice_quali_classi_esistono():
    """Solleva invece di rendere `None`, e nomina cio' che c'e'.

    Un chiamante che confrontasse contro `None` otterrebbe un attributo mancante
    a valle, lontano dal punto in cui la classe e' stata scritta male.
    """
    with pytest.raises(KeyError) as errore:
        trova("C99/99")
    assert "C99/99" in str(errore.value)
    assert "C25/30" in str(errore.value), "il rifiuto non elenca le classi che esistono"

    with pytest.raises(KeyError, match="B999"):
        trova("B999")


def test_trova_normalizza_il_caso_e_gli_spazi():
    """La scelta e' **normalizzare**, e vale su entrambi i lati del confronto.

    Il caso e' la seconda classe di difetto piu' frequente del repository. Qui
    normalizzare non costa nulla: le classi di norma sono maiuscole per
    convenzione tipografica, non per identita', e nessuna coppia di voci
    differisce per il solo caso -- lo sorveglia
    `test_le_classi_non_collidono_nemmeno_ignorando_il_caso`.
    """
    atteso = trova("C25/30")
    assert trova("c25/30") is atteso
    assert trova("  C25/30  ") is atteso
    assert trova("b450c") is trova("B450C")


def test_trova_su_stringa_vuota_dichiara_invece_di_sbagliare_tipo_di_errore():
    """Ingresso degenere: la stringa vuota non e' un `IndexError`.

    Arriva da un campo di configurazione lasciato in bianco, ed e' esattamente
    il caso in cui il messaggio deve dire che cosa manca.
    """
    with pytest.raises(KeyError) as errore:
        trova("")
    assert "C25/30" in str(errore.value)


def test_gli_aggregati_leggeri_sono_fuori_campo_e_il_modulo_lo_dichiara():
    """Il campo del catalogo e' ristretto, e un campo ristretto va detto.

    Le NTC §4.1.12 (riga 2458) ammettono i calcestruzzi di aggregati leggeri
    «fino alla classe LC55/60», e qui non ce n'e' nessuno. Non e' una
    dimenticanza: la riga 2124 definisce «calcestruzzi ordinari» proprio «con
    esclusione dei calcestruzzi di aggregati leggeri (LC), di cui al §4.1.12, e
    di quelli fibrorinforzati (FRC), di cui al §11.2.12», e il catalogo copre
    quelli. Ma un campo ristretto e non dichiarato si scopre a valle, quando
    `trova` solleva su una classe che la norma ammette.

    Mutazione che lo uccide: togliere la dichiarazione dal docstring del modulo.
    """
    with pytest.raises(KeyError):
        trova("LC25/28")
    fuori_campo = [v.classe for v in CATALOGO if v.classe.upper().startswith(("LC", "FRC"))]
    assert not fuori_campo, f"voci fuori dal campo dichiarato: {fuori_campo}"
    assert "LC" in materiali.__doc__
    assert "FRC" in materiali.__doc__


# --- i valori di progetto ------------------------------------------------


def test_il_calcestruzzo_da_f_cd_e_non_f_yd():
    """`f_cd = α_cc · f_ck / γ_c`, e `α_cc` non e' facoltativo.

    NTC §4.1.2.1.1.1, espressione `[4.1.3]`: il coefficiente di lunga durata sta
    dentro la formula, ha un nome e vale 0,85. Chi scrive `f_ck / 1,5` ottiene un
    valore del 17,6% piu' alto del vero, e sbaglia dalla parte insicura.

    Mutazione che lo uccide: togliere `ALFA_CC` dalla formula.
    """
    valori = valori_di_progetto(trova("C25/30"))
    assert set(valori) == {"f_cd"}
    assert valori["f_cd"] == pytest.approx(0.85 * 25.0 / 1.5)
    assert valori["f_cd"] == pytest.approx(14.1667, abs=1e-4)


def test_alpha_cc_e_applicato_a_ogni_voce_del_catalogo_e_non_solo_alla_c25_30():
    """Da «impossibile per costruzione» a «misurato».

    `valori_di_progetto` ha un solo ramo per famiglia, quindi oggi la divergenza
    per classe non e' rappresentabile -- ma cio' che regge per costruzione regge
    finche' la costruzione non cambia, e un caso speciale per le classi alte
    (dove la norma **ha** riduzioni ulteriori, §11.2.10.2-3) e' esattamente la
    modifica plausibile. Il test che lo provava su una sola classe non l'avrebbe
    vista.

    I due coefficienti sono scritti come letterali e non ripresi dal modulo: la
    stessa espressione confrontata con se stessa non ucciderebbe una formula
    sbagliata.

    Mutazione che lo uccide: togliere `ALFA_CC` dalla formula, o applicarlo solo
    sotto una certa classe.
    """
    calcestruzzi = [v for v in CATALOGO if v.famiglia == "calcestruzzo"]
    assert len(calcestruzzi) == 17
    for voce in calcestruzzi:
        assert valori_di_progetto(voce)["f_cd"] == pytest.approx(0.85 * voce.f_k / 1.5), (
            f"{voce.classe}: alpha_cc non applicato"
        )

    acciai = [v for v in CATALOGO if v.famiglia == "acciaio"]
    assert len(acciai) == 2
    for voce in acciai:
        assert valori_di_progetto(voce)["f_yd"] == pytest.approx(voce.f_k / 1.15), voce.classe


def test_l_acciaio_da_f_yd_e_non_f_cd():
    """`f_yd = f_yk / γ_s`, senza alcun α: la `[4.1.5]` non ne ha.

    E il 1,15 vale «sempre, per tutti i tipi di acciaio» -- la parola e' nel
    testo di norma, §4.1.2.1.1.3.
    """
    valori = valori_di_progetto(trova("B450C"))
    assert set(valori) == {"f_yd"}
    assert valori["f_yd"] == pytest.approx(391.3043, abs=1e-4)


def test_i_coefficienti_parziali_sono_quelli_delle_ntc():
    """I tre numeri che la `[4.1.3]` e la `[4.1.5]` fissano, esposti e non sepolti.

    `γ_c` e' quello europeo, `α_cc` no: la Circolare lo dice, «il coefficiente
    αcc resta fissato a 0,85, a differenza di quello proposto dalla UNI EN
    1992». Chi un giorno volesse una modalita' Eurocodice cambierebbe `ALFA_CC`
    e non `GAMMA_C`.
    """
    assert ALFA_CC == 0.85
    assert GAMMA_C == 1.5
    assert GAMMA_S == 1.15


def test_l_oracolo_di_collaudo_del_progetto_parte_da_rck_30_e_non_dalla_c25_30():
    """`R_ck` = 30, B450C: `f_cd` = 14,110 MPa. Verificato per tre vie nella ricerca.

    **L'ingresso e' `R_ck` = 30, non la classe C25/30**, e le due cose non
    coincidono: la C25/30 ha `f_ck` = 25 per definizione e darebbe 14,17 MPa. Uno
    scarto dello 0,4%, cioe' il modo peggiore di fallire. La `[11.2.1]`
    `f_ck = 0,83 · R_ck` si applica qui, nel test, perche' l'ingresso e' un
    `R_ck` di capitolato; il catalogo parte dal nome della classe e non la
    incontra mai.

    `k_bil` e `μ_bil` non si calcolano qui: sono del controllo di sezione, che
    questo modulo non fa.
    """
    f_ck_da_rck = 0.83 * 30.0
    voce = _voce(classe="da R_ck = 30", f_k=f_ck_da_rck)
    assert valori_di_progetto(voce)["f_cd"] == pytest.approx(14.110, abs=5e-4)


def test_valori_di_progetto_rifiuta_una_resistenza_non_positiva():
    """Non e' impossibile per costruzione: un materiale dichiarato a mano puo' portarla.

    Senza guardia, `f_k = 0` darebbe `f_cd = 0` in silenzio, e una sezione con
    resistenza nulla non verrebbe letta come un difetto di dichiarazione ma come
    un risultato.
    """
    for f_k in (0.0, -25.0, float("nan")):
        with pytest.raises(ValueError, match="caratteristica"):
            valori_di_progetto(_voce(f_k=f_k))


def test_valori_di_progetto_rifiuta_una_famiglia_che_non_conosce():
    """`Literal` non vincola a runtime, e cadere sul ramo dell'acciaio per una
    famiglia sconosciuta restituirebbe un `f_yd` per un materiale che non e'
    acciaio."""
    with pytest.raises(ValueError, match="famiglia"):
        valori_di_progetto(_voce(famiglia="muratura"))
