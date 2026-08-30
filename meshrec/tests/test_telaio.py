"""Il telaio a fibre: comporre, non inventare.

Le parti vengono da altri moduli -- le sezioni per stazione da `wall.misura`, i
nodi dall'adiacenza di `wall.giunzioni`, le barre da `armatura.colloca`, i
materiali da `config.RegioneConfig` -- e qui si prova solo la composizione:
quante aste escono, dove stanno i loro nodi, quale sezione porta ciascuna, e
che le terne che ne escono siano quelle che `opensees.scrivi_tcl` accetta.

**Il banco vero e' il consumatore.** Il test che chiude il contratto non
guarda i campi di `Telaio` a uno a uno: dà il telaio a `opensees.scrivi_tcl` e
guarda che scriva. Un contratto verificato leggendo i campi resterebbe verde il
giorno in cui il consumatore cambia idea.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import config, opensees, synth, telaio, wall

SPAZIATURA = 20.0

# Lo stesso telaio sintetico del banco del prior (`test_wall.TELAIO`): due
# montanti e due traversi, quattro sezioni deliberatamente diverse. Sta qui una
# seconda volta e non importato, per la stessa ragione per cui sta la' e non in
# `src/`: e' un banco, e due banchi che si muovono insieme non provano piu'
# l'uno l'altro.
TELAIO_SINTETICO = [
    ((0.0, -90.0, 0.0), (200.0, 180.0, 1600.0)),
    ((1400.0, -130.0, 0.0), (200.0, 260.0, 1600.0)),
    ((0.0, -70.0, 1600.0), (1600.0, 140.0, 300.0)),
    ((0.0, -170.0, -300.0), (1600.0, 340.0, 300.0)),
]


def _materiale(nome: str, young: float, densita: float) -> config.MaterialeDichiarato:
    return config.MaterialeDichiarato(
        material=config.Material(name=nome, young=young, poisson=0.2, density=densita),
        f_k=25.0,
        provenienza="a_mano",
        norma="banco di prova",
    )


def _armatura(**campi) -> config.ArmaturaConfig:
    """Una gabbia magra, che ci sta anche nella sezione piu' stretta del banco."""
    predefiniti = dict(
        classe_calcestruzzo="C25/30",
        classe_acciaio="B450C",
        barre_tese=2,
        diametro_teso=12,
        barre_compresse=2,
        diametro_compresso=12,
        diametro_staffe=8,
        passo_staffe=150.0,
        copriferro_nominale=25.0,
    )
    return config.ArmaturaConfig(**{**predefiniti, **campi})


def _sezione(armatura: config.ArmaturaConfig | None = None) -> config.SezioneConfig:
    return config.SezioneConfig(
        calcestruzzo_confinato=_materiale("C25_30", 31_476.0, 2.5e-9),
        calcestruzzo_copriferro=_materiale("C25_30", 31_476.0, 2.5e-9),
        acciaio=_materiale("B450C", 200_000.0, 7.85e-9),
        armatura=armatura,
    )


def _regioni(quante: int, armatura=..., **eccezioni) -> dict[str, config.RegioneConfig]:
    """Una regione per membratura, tutte con la stessa sezione salvo eccezioni."""
    gabbia = _armatura() if armatura is ... else armatura
    return {
        f"M{indice}": config.RegioneConfig(
            membratura=indice, sezione=eccezioni.get(f"M{indice}", _sezione(gabbia))
        )
        for indice in range(quante)
    }


def _voce(
    asse=(0.0, 0.0, 1.0),
    origine=(0.0, 0.0, 0.0),
    lunghezza=2000.0,
    fette=20,
    sezione=(300.0, 200.0),
    riferimento=None,
    quote=None,
    base_sezione=...,
) -> dict[str, object]:
    """Una voce di `12_wall.json`, nella forma che `wall.prior` scrive.

    `e2 = asse x e1` e' l'invariante che `wall.misura` costruisce: qui si
    riproduce invece di essere battuta a mano, cosi' il banco non puo'
    dichiarare una terna che il prior non produrrebbe mai.
    """
    asse = np.asarray(asse, dtype=np.float64)
    asse = asse / np.linalg.norm(asse)
    if riferimento is None:
        # La stessa regola di `wall.misura`: il riferimento della terna del
        # pezzo, salvo che sia quasi allineato all'asse.
        candidati = [(0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)]
        riferimento = next(c for c in candidati if abs(asse @ np.asarray(c)) < 0.9)
    grezzo = np.asarray(riferimento, dtype=np.float64)
    e1 = grezzo - asse * float(grezzo @ asse)
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(asse, e1)
    if quote is None:
        bordi = np.linspace(0.0, lunghezza, 21)
        quote = [float((bordi[i] + bordi[i + 1]) / 2.0) for i in range(fette)]
    sezioni = [list(sezione) for _ in quote]
    return {
        "asse": asse.tolist(),
        "origine": list(map(float, origine)),
        "lunghezza": float(lunghezza),
        "sezioni_fette": sezioni,
        "quote_fette": [float(q) for q in quote],
        "base_sezione": (
            np.vstack([e1, e2]).tolist() if base_sezione is ... else base_sezione
        ),
        "riempimento": {"valore": 0.93, "stato": "pieno"},
    }


def _prior(membrature: list[dict], giunzioni: list[dict] | None = None) -> dict[str, object]:
    return {"membrature": membrature, "giunzioni": [] if giunzioni is None else giunzioni}


def _giunzione(cede: int, resta: int, nodo, **campi) -> dict[str, object]:
    predefiniti = {
        "cede": cede,
        "resta": resta,
        "nodo": list(map(float, nodo)),
        "distanza_proiezione": 0.0,
        "nodo_limitato": False,
        "tipo_incontro": "estremo",
    }
    return {**predefiniti, **campi}


# --- quante aste, e con quale sezione ----------------------------------------
def test_una_sola_membratura_senza_giunzioni_e_un_telaio_legittimo():
    """Una mensola e' una struttura: nessun legame non e' un errore."""
    costruito = telaio.costruisci(_prior([_voce()]), _regioni(1))

    assert len(costruito.elementi) == 20
    assert len(costruito.nodi) == 21
    assert costruito.giunzioni == []


def test_venti_elementi_per_sei_membrature_fanno_centoventi():
    """Il conteggio si misura, non si presume."""
    costruito = telaio.costruisci(
        _prior([_voce(origine=(i * 3000.0, 0.0, 0.0)) for i in range(6)]), _regioni(6)
    )

    assert len(costruito.elementi) == 120


def test_meno_di_venti_fette_danno_meno_elementi():
    """Sette fette misurate sono sette aste, non venti con tredici interpolate."""
    costruito = telaio.costruisci(_prior([_voce(fette=7)]), _regioni(1))

    assert len(costruito.elementi) == 7
    assert [e.stazione for e in costruito.elementi] == list(range(7))


def test_una_membratura_senza_fette_si_dichiara_e_non_si_fabbrica():
    voce = _voce(fette=0)

    with pytest.raises(ValueError, match="membratura 0"):
        telaio.costruisci(_prior([voce]), _regioni(1))


def test_ogni_elemento_porta_la_sezione_della_propria_fetta():
    """La sezione varia lungo l'asse ed e' giusto che vari: appiattirla alla
    media butterebbe via cio' che il programma misura."""
    voce = _voce(fette=3)
    voce["sezioni_fette"] = [[300.0, 200.0], [280.0, 200.0], [260.0, 200.0]]

    costruito = telaio.costruisci(_prior([voce]), _regioni(1))

    assert [e.sezione for e in costruito.elementi] == [
        (300.0, 200.0),
        (280.0, 200.0),
        (260.0, 200.0),
    ]


def test_zero_membrature_non_fabbricano_un_telaio():
    with pytest.raises(ValueError, match="nessuna membratura"):
        telaio.costruisci(_prior([]), {})


def test_un_prior_senza_giunzioni_non_costruisce_un_telaio():
    """Corsa vecchia: la chiave non c'e'. Sei aste che galleggiano non sono un
    telaio, e assente vuol dire assente."""
    vecchio = {"membrature": [_voce()]}

    with pytest.raises(ValueError, match="giunzioni"):
        telaio.costruisci(vecchio, _regioni(1))


# --- la terna, che il solutore controlla col verso ----------------------------
def test_ogni_elemento_esce_con_e1_uguale_a_e2_per_asse():
    """La guardia di `opensees._sezioni_ed_elementi`: l'asse locale y che
    OpenSees deriva da (asse, e2) deve coincidere **col verso** con e1, o
    l'armatura asimmetrica esce specchiata in silenzio."""
    prior = _prior(
        [_voce(asse=(0.0, 0.0, 1.0)), _voce(asse=(0.3, 0.4, 0.866), origine=(5000.0, 0.0, 0.0))]
    )

    costruito = telaio.costruisci(prior, _regioni(2))

    for elemento in costruito.elementi:
        asse = costruito.nodi[elemento.nodo_j] - costruito.nodi[elemento.nodo_i]
        asse = asse / np.linalg.norm(asse)
        assert np.allclose(np.cross(elemento.e2, asse), elemento.e1, atol=1e-9)


def test_anche_l_asta_inclinata_dal_nodo_di_giunzione_passa_la_guardia():
    """L'estremo che raggiunge il nodo inclina la propria asta: se la terna
    restasse quella della membratura, la guardia del solutore cadrebbe."""
    montante = _voce(asse=(0.0, 0.0, 1.0), origine=(0.0, 0.0, 0.0), lunghezza=1000.0)
    traverso = _voce(
        asse=(1.0, 0.0, 0.0), origine=(-500.0, 40.0, 1000.0), lunghezza=2000.0, fette=20
    )
    # Il montante cede al traverso, e il nodo sta 40 mm fuori dal suo asse.
    prior = _prior(
        [montante, traverso],
        [_giunzione(0, 1, (0.0, 40.0, 1000.0), distanza_proiezione=40.0)],
    )

    costruito = telaio.costruisci(prior, _regioni(2))

    inclinati = 0
    for elemento in costruito.elementi:
        asse = costruito.nodi[elemento.nodo_j] - costruito.nodi[elemento.nodo_i]
        asse = asse / np.linalg.norm(asse)
        assert np.allclose(np.cross(elemento.e2, asse), elemento.e1, atol=1e-9)
        if elemento.membratura == 0 and abs(float(asse[1])) > 1e-9:
            inclinati += 1
    assert inclinati == 1, "il nodo spostato deve inclinare esattamente l'asta d'estremo"


def test_una_base_sezione_vuota_non_fabbrica_un_telaio():
    """Un prior scritto prima delle misure nuove non porta il piano di sezione:
    senza, non si sa dove stiano le due estensioni ne' come sia orientata la
    sezione a fibre."""
    with pytest.raises(ValueError, match="base_sezione"):
        telaio.costruisci(_prior([_voce(base_sezione=[])]), _regioni(1))


def test_una_terna_che_non_e_e2_uguale_asse_per_e1_e_rifiutata():
    """Rifiutata qui e non corretta: `sezioni_fette` e' misurata **in quel
    piano**, e raddrizzarlo scambierebbe base e altezza senza dirlo."""
    storta = _voce()
    e1, e2 = np.asarray(storta["base_sezione"], dtype=np.float64)
    storta["base_sezione"] = [e1.tolist(), (-e2).tolist()]

    with pytest.raises(ValueError, match="base_sezione"):
        telaio.costruisci(_prior([storta]), _regioni(1))


# --- i nodi vengono dall'adiacenza -------------------------------------------
def _telaio_a_elle():
    """Un montante che cede a un traverso, con gli assi che si incontrano."""
    montante = _voce(asse=(0.0, 0.0, 1.0), origine=(0.0, 0.0, 0.0), lunghezza=1000.0)
    traverso = _voce(asse=(1.0, 0.0, 0.0), origine=(0.0, 0.0, 1000.0), lunghezza=2000.0)
    return _prior([montante, traverso], [_giunzione(0, 1, (0.0, 0.0, 1000.0))])


def test_due_membrature_che_si_incontrano_condividono_un_nodo():
    """In un telaio due aste che si incontrano condividono un nodo: senza, il
    solutore calcola due pezzi che si toccano senza parlarsi."""
    costruito = telaio.costruisci(_telaio_a_elle(), _regioni(2))

    # 21 nodi per membratura, uno in comune.
    assert len(costruito.nodi) == 41
    del_montante = [e for e in costruito.elementi if e.membratura == 0]
    del_traverso = [e for e in costruito.elementi if e.membratura == 1]
    assert del_montante[-1].nodo_j == del_traverso[0].nodo_i


def test_il_nodo_del_telaio_e_quello_che_il_prior_ha_misurato():
    costruito = telaio.costruisci(_telaio_a_elle(), _regioni(2))

    incontro = costruito.giunzioni[0]
    assert "nodo_telaio" in incontro
    assert np.allclose(costruito.nodi[incontro["nodo_telaio"]], [0.0, 0.0, 1000.0], atol=1e-9)


def test_la_lunghezza_di_calcolo_e_da_nodo_a_nodo_e_non_l_estensione_della_nuvola():
    """Il montante finisce a 900 mm nella nuvola e arriva a 1000 sul nodo: la
    differenza e' mezza altezza del traverso, e non e' trascurabile."""
    montante = _voce(asse=(0.0, 0.0, 1.0), origine=(0.0, 0.0, 0.0), lunghezza=900.0)
    traverso = _voce(asse=(1.0, 0.0, 0.0), origine=(0.0, 0.0, 1000.0), lunghezza=2000.0)
    prior = _prior([montante, traverso], [_giunzione(0, 1, (0.0, 0.0, 1000.0))])

    costruito = telaio.costruisci(prior, _regioni(2))

    del_montante = [e for e in costruito.elementi if e.membratura == 0]
    piede = costruito.nodi[del_montante[0].nodo_i]
    testa = costruito.nodi[del_montante[-1].nodo_j]
    assert float(np.linalg.norm(testa - piede)) == pytest.approx(1000.0, abs=1e-9)


def test_una_lunghezza_di_calcolo_nulla_solleva_nominando_la_coppia():
    """Il nodo cade sotto la penultima stazione: l'asta d'estremo si rovescia,
    e un'asta di lunghezza negativa non e' un'asta."""
    montante = _voce(asse=(0.0, 0.0, 1.0), origine=(0.0, 0.0, 0.0), lunghezza=1000.0)
    traverso = _voce(asse=(1.0, 0.0, 0.0), origine=(0.0, 0.0, 80.0), lunghezza=2000.0)
    prior = _prior([montante, traverso], [_giunzione(0, 1, (0.0, 0.0, 80.0))])

    with pytest.raises(ValueError, match="membrature 0 e 1"):
        telaio.costruisci(prior, _regioni(2))


def test_quanto_il_nodo_si_e_spostato_dalla_misura_si_mostra():
    """Il nodo misurato cade fra due stazioni di chi resta: il telaio lo posa
    sulla stazione piu' vicina, e quel millimetro non si tace."""
    montante = _voce(asse=(0.0, 0.0, 1.0), origine=(0.0, 0.0, 0.0), lunghezza=1000.0)
    traverso = _voce(asse=(1.0, 0.0, 0.0), origine=(0.0, 0.0, 1000.0), lunghezza=2000.0)
    # 137 mm lungo il traverso: le stazioni stanno a 0, 100, 200, ...
    prior = _prior([montante, traverso], [_giunzione(0, 1, (137.0, 0.0, 1000.0))])

    costruito = telaio.costruisci(prior, _regioni(2))

    incontro = costruito.giunzioni[0]
    assert incontro["scostamento_nodo"] == pytest.approx(37.0, abs=1e-9)
    assert incontro["distanza_proiezione"] == 0.0, "la misura del prior resta intatta"


def test_un_incontro_che_si_scavalca_arriva_dichiarato_nel_telaio():
    """`nodo_limitato` dice che i due pezzi si scavalcano invece di
    incontrarsi: il telaio si costruisce e lo mostra, non lo nasconde."""
    prior = _telaio_a_elle()
    prior["giunzioni"][0]["nodo_limitato"] = True

    costruito = telaio.costruisci(prior, _regioni(2))

    assert costruito.giunzioni[0]["nodo_limitato"] is True


@pytest.mark.parametrize("tipo", ["attraversamento", "contenimento"])
def test_un_attraversamento_o_un_contenimento_arriva_dichiarato(tipo):
    """La lunghezza di calcolo non e' quella di un incontro a un estremo, e chi
    guarda il telaio deve poterlo vedere."""
    prior = _telaio_a_elle()
    prior["giunzioni"][0]["tipo_incontro"] = tipo

    costruito = telaio.costruisci(prior, _regioni(2))

    assert costruito.giunzioni[0]["tipo_incontro"] == tipo


# --- l'armatura, riposizionata a ogni stazione -------------------------------
def test_le_barre_si_ricollocano_a_ogni_stazione():
    """`colloca` dipende dalla sezione e la sezione cambia: due stazioni con
    basi diverse hanno barre in posti diversi."""
    voce = _voce(fette=2)
    voce["sezioni_fette"] = [[300.0, 200.0], [200.0, 200.0]]

    costruito = telaio.costruisci(_prior([voce]), _regioni(1))

    prima, seconda = costruito.elementi
    assert [b.y for b in prima.barre] != [b.y for b in seconda.barre]


def test_le_barre_arrivano_centrate_sul_baricentro_della_sezione():
    """`armatura.colloca` misura da uno spigolo, `opensees` scrive le fibre nel
    riferimento locale **centrato** in cui posa la `patch rect`: la traslazione
    la fa il telaio, o le barre uscirebbero fuori dal calcestruzzo."""
    costruito = telaio.costruisci(
        _prior([_voce(fette=1, sezione=(300.0, 200.0))]), _regioni(1)
    )

    barre = costruito.elementi[0].barre
    assert barre, "la gabbia dichiarata deve produrre barre"
    for barra in barre:
        assert -150.0 <= barra.y <= 150.0
        assert -100.0 <= barra.z <= 100.0
    assert min(b.z for b in barre) < 0.0, "il bordo teso sta dal lato -e2"


def test_una_membratura_senza_armatura_da_un_elemento_di_solo_calcestruzzo():
    """Nessuna armatura si inventa, e nessuna assenza schianta."""
    costruito = telaio.costruisci(_prior([_voce()]), _regioni(1, armatura=None))

    assert all(elemento.barre == [] for elemento in costruito.elementi)


def test_le_barre_che_non_ci_stanno_fermano_nominando_la_stazione():
    """L'unica guardia di `armatura.colloca` che ferma e' la geometria
    impossibile, e il rifiuto deve dire **dove**."""
    voce = _voce(fette=3)
    voce["sezioni_fette"] = [[300.0, 200.0], [300.0, 200.0], [300.0, 40.0]]

    with pytest.raises(ValueError, match="stazione 2 della membratura 0"):
        telaio.costruisci(_prior([voce]), _regioni(1))


# --- i materiali per membratura ----------------------------------------------
def test_una_membratura_senza_sezione_dichiarata_si_dichiara():
    """Non si ricade su un predefinito: un modulo elastico scelto da nessuno e'
    il difetto che questo progetto esiste per non produrre."""
    prior = _prior([_voce(), _voce(origine=(3000.0, 0.0, 0.0))])

    with pytest.raises(ValueError, match="membratura 1"):
        telaio.costruisci(prior, _regioni(1))


def test_una_regione_che_nomina_una_membratura_inesistente_e_rifiutata():
    """`RegioneConfig` dichiara che il rifiuto dell'indice fuori intervallo
    spetta a chi legge il prior."""
    regioni = {
        "M0": config.RegioneConfig(membratura=0, sezione=_sezione(_armatura())),
        "FANTASMA": config.RegioneConfig(membratura=7, sezione=_sezione(_armatura())),
    }

    with pytest.raises(ValueError, match="FANTASMA"):
        telaio.costruisci(_prior([_voce()]), regioni)


def test_due_regioni_sulla_stessa_membratura_sono_rifiutate():
    """Due sezioni per la stessa asta: sceglierne una in silenzio sarebbe la
    sezione decisa dall'ordine di un dizionario."""
    regioni = {
        "A": config.RegioneConfig(membratura=0, sezione=_sezione(_armatura())),
        "B": config.RegioneConfig(membratura=0, sezione=_sezione(None)),
    }

    with pytest.raises(ValueError, match="membratura 0"):
        telaio.costruisci(_prior([_voce()]), regioni)


def test_i_materiali_escono_indicizzati_per_membratura():
    costruito = telaio.costruisci(_prior([_voce(), _voce(origine=(3000.0, 0.0, 0.0))]), _regioni(2))

    assert set(costruito.materiali) == {0, 1}


# --- un esito discreto che cambia e' un difetto di prodotto -------------------
def test_lo_stesso_prior_costruito_due_volte_da_lo_stesso_telaio():
    prior = _telaio_a_elle()

    primo = telaio.costruisci(prior, _regioni(2))
    secondo = telaio.costruisci(prior, _regioni(2))

    assert np.array_equal(primo.nodi, secondo.nodi)
    assert [(e.membratura, e.stazione, e.nodo_i, e.nodo_j) for e in primo.elementi] == [
        (e.membratura, e.stazione, e.nodo_i, e.nodo_j) for e in secondo.elementi
    ]


# --- il banco vero: il consumatore ------------------------------------------
def test_il_telaio_e_scrivibile_da_opensees(tmp_path):
    """Il contratto si prova eseguendo lo scrittore, non rileggendo i campi."""
    costruito = telaio.costruisci(_telaio_a_elle(), _regioni(2))

    resoconto = opensees.scrivi_tcl(
        tmp_path / "telaio.tcl", costruito, casi_di_carico=["GRAVITA", "MODALE"], modi=3
    )

    assert resoconto["elementi"] == 40
    assert resoconto["nodi"] == 41
    assert resoconto["peso_proprio"] > 0.0
    testo = (tmp_path / "telaio.tcl").read_text(encoding="utf-8")
    assert testo.count("section Fiber") == 40
    assert "-GJ" in testo


def test_il_prior_vero_arriva_fino_al_tcl(tmp_path):
    """Capo a capo sul telaio sintetico: nuvola -> prior -> telaio -> `.tcl`.
    E' il solo test che prova che i nomi del prior e quelli del telaio sono gli
    stessi nomi."""
    punti = synth.sample_frame_surface(TELAIO_SINTETICO, SPAZIATURA)
    prior = wall.prior(punti, config.SegmentConfig(), config.WallConfig(), SPAZIATURA)
    assert len(prior["membrature"]) == 4
    assert prior["giunzioni"], "il banco deve avere incontri, o non prova il telaio"

    costruito = telaio.costruisci(prior, _regioni(4))

    resoconto = opensees.scrivi_tcl(
        tmp_path / "telaio.tcl", costruito, casi_di_carico=["GRAVITA"]
    )
    assert resoconto["elementi"] == len(costruito.elementi)
    assert resoconto["barre"] > 0
    assert len(costruito.nodi) < sum(
        len(m["quote_fette"]) + 1 for m in prior["membrature"]
    ), "gli incontri devono avere fuso dei nodi"


_OPENSEES = os.environ.get("MESHREC_OPENSEES") or shutil.which("OpenSees")


@pytest.mark.feasibility
def test_opensees_esegue_davvero_il_telaio_del_prior(tmp_path):
    """La prova che il contratto regge: OpenSees 3.8.0 sul `.tcl` di un telaio
    costruito da un prior vero, non da un sostituto.

    **Il codice d'uscita non e' il segnale** (OpenSees esce 0 anche dopo un
    errore fatale): si guardano il marcatore di fine e i campi riletti.
    """
    if _OPENSEES is None:
        pytest.skip("OpenSees non trovato: né MESHREC_OPENSEES né 'OpenSees' nel PATH")

    punti = synth.sample_frame_surface(TELAIO_SINTETICO, SPAZIATURA)
    prior = wall.prior(punti, config.SegmentConfig(), config.WallConfig(), SPAZIATURA)
    costruito = telaio.costruisci(prior, _regioni(4))
    opensees.scrivi_tcl(
        tmp_path / "telaio.tcl", costruito, casi_di_carico=["GRAVITA", "MODALE"], modi=3
    )

    # Mai dalla cartella `bin/` dell'installazione: i registratori scrivono con
    # nomi relativi alla cartella corrente.
    subprocess.run([_OPENSEES, "telaio.tcl"], cwd=tmp_path, capture_output=True, timeout=600)

    campi = opensees.leggi_uscite(tmp_path, costruito)
    assert set(campi) >= {"U_GRAVITA", "N_GRAVITA", "V_GRAVITA", "M_GRAVITA", "MODO_1"}
    assert campi["U_GRAVITA"].shape == (len(costruito.nodi), 3)
    assert np.isfinite(campi["U_GRAVITA"]).all()
    assert float(np.max(np.abs(campi["U_GRAVITA"]))) > 0.0, (
        "un telaio sotto il proprio peso che non si sposta è un modello non caricato"
    )
    massa = opensees.leggi_massa_modale(tmp_path / opensees.NOME_MASSA_MODALE)
    assert massa is not None and len(massa["catturata"]) == 6
