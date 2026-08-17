"""Controlli testuali sul foglio di stile dell'interfaccia.

Il CSS non ha un `node --check`: una graffa sbagliata non fa rosso nessun test e
rompe la pagina in silenzio, perche' il browser chiude da solo a fine file e
salta cio' che non sa leggere. E' successo davvero durante il Task 16a, spostando
un blocco @media: la graffa di chiusura e' rimasta indietro e a video non si
vedeva nulla. Questi tre controlli sono l'unica sorveglianza che quel file ha.
"""

import re

from meshrec.app.server import UI_DIR

# I commenti del foglio contengono regole citate per iscritto, graffe comprese
# (per esempio «.viewport { height: 100% } di un genitore alto quanto il suo
# contenuto vale zero»): contarle sarebbe contare due volte.
COMMENTO = re.compile(r"/\*.*?\*/", re.S)


def _senza_commenti() -> str:
    return COMMENTO.sub("", (UI_DIR / "stile.css").read_text(encoding="utf-8"))


def test_le_graffe_del_foglio_di_stile_sono_bilanciate():
    saldo = 0
    for numero, riga in enumerate(_senza_commenti().splitlines(), start=1):
        for carattere in riga:
            saldo += {"{": 1, "}": -1}.get(carattere, 0)
            assert saldo >= 0, f"graffa chiusa di troppo alla riga {numero}: {riga}"
    assert saldo == 0, f"restano {saldo} blocchi aperti a fine file"


def test_ogni_variabile_usata_e_dichiarata():
    """Un var(--nome) scritto male non e' un errore: la proprieta' cade e la
    regola resta muta, che e' esattamente il modo di rompere una pagina senza
    che niente lo dica."""
    testo = _senza_commenti()
    dichiarate = set(re.findall(r"^\s*(--[\w-]+)\s*:", testo, re.MULTILINE))
    usate = set(re.findall(r"var\(\s*(--[\w-]+)", testo))
    assert usate <= dichiarate, f"variabili mai dichiarate: {sorted(usate - dichiarate)}"


def test_nessun_colore_scritto_a_mano_fuori_dai_token():
    """Il sistema di colore sta in :root e da nessun'altra parte: un esadecimale
    dentro una regola e' un colore che nessun tema e nessun controllo di
    contrasto raggiunge."""
    testo = _senza_commenti()
    fine_root = testo.index("\n}", testo.index(":root"))
    fuori = re.findall(r"#[0-9a-fA-F]{3,8}\b", testo[fine_root:])
    assert not fuori, f"colori scritti a mano fuori da :root: {fuori}"


def _lineari(esadecimale: str) -> list[float]:
    """I tre canali sRGB portati in luce lineare, che e' dove si moltiplica."""
    canali = [int(esadecimale[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]


def _luminanza_lineare(lineari: list[float]) -> float:
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def _luminanza(esadecimale: str) -> float:
    """Luminanza relativa sRGB, WCAG 2.x."""
    return _luminanza_lineare(_lineari(esadecimale))


def _rapporto_fra(prima: float, seconda: float) -> float:
    chiaro, scuro = max(prima, seconda), min(prima, seconda)
    return (chiaro + 0.05) / (scuro + 0.05)


def _rapporto(primo: str, secondo: str) -> float:
    return _rapporto_fra(_luminanza(primo), _luminanza(secondo))


def _token(nome: str) -> str:
    testo = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    trovato = re.search(rf"{nome}:\s*(#[0-9a-fA-F]{{6}})", testo)
    assert trovato is not None, f"il token {nome} non e' piu' un esadecimale in :root"
    return trovato.group(1)


def test_il_contorno_dei_comandi_regge_anche_sulla_superficie_del_passaggio():
    """Il commento difende --bordo-comando sopra 3:1 su due superfici (WCAG
    1.4.11) e ne dimentica una terza: al passaggio del puntatore il fondo di un
    bottone diventa --evidenza, e li' lo stesso contorno misurava 2,88. E' il
    contorno che quel commento chiama «l'unico indizio del comando»: sotto
    soglia proprio nel momento in cui si sta per premere."""
    bordo = _token("--bordo-comando")
    # --evidenza e' --accento all'8% sopra la superficie, composto qui.
    superficie, accento = _token("--superficie"), _token("--accento")
    composto = "#" + "".join(
        f"{round(int(superficie[i:i + 2], 16) * 0.92 + int(accento[i:i + 2], 16) * 0.08):02x}"
        for i in (1, 3, 5)
    )
    misura = _rapporto(bordo, composto)
    assert misura >= 3.0, f"il contorno misura {misura:.2f} sul fondo del passaggio, sotto 3:1"


def test_le_colonne_laterali_non_superano_la_vista():
    """18rem + 22rem sono 640 px di cornice fissa: fra ~961 e ~1250 px la
    colonna centrale — la vista 3D, la ragione per cui l'applicazione esiste —
    era piu' stretta di entrambe le laterali. A 200% su uno schermo grande si
    atterra esattamente in quella fascia."""
    testo = _senza_commenti()
    trovato = re.search(r"\.tre-zone\s*{[^}]*grid-template-columns:\s*([^;]+);", testo)
    assert trovato is not None, "la griglia delle tre zone non si trova piu'"
    assert "minmax(" in trovato.group(1), (
        f"le laterali sono ancora a larghezza fissa: {trovato.group(1).strip()}"
    )


def test_il_registro_vuoto_non_e_una_striscia_bordata():
    """Vuoto rendeva un rettangolo alto 1 px con un contorno intorno, che si
    legge come un campo di testo rotto. .conteggi:empty ha gia' lo stesso
    rimedio da un giro."""
    assert ".registro:empty" in _senza_commenti(), "il registro vuoto resta una striscia"


def test_la_prosa_dichiara_il_proprio_margine():
    """Un <p> senza margine proprio prende quello del browser, 1em, che su
    --tipo-nota fa 13 px: un valore che non sta nella scala e che il foglio
    dice di aver tolto. Misurato a video prima della correzione, e' il salto
    fra un titolo e il suo aiuto in cinque punti del pannello: 13 px contro i
    24 px che separano due gruppi, cioe' due intervalli quasi uguali dove il
    disegno ne vuole due diversi. Il controllo guarda che il margine ci sia,
    non quanto vale: e' l'assenza a lasciar rientrare il valore del browser."""
    testo = _senza_commenti()
    for regola in ("p.aiuto", ".vuoto"):
        trovata = re.search(rf"{re.escape(regola)}\s*{{([^}}]*)}}", testo)
        assert trovata is not None, f"la regola {regola} non si trova piu'"
        assert "margin" in trovata.group(1), (
            f"{regola} non dichiara un margine: torna quello del browser, fuori scala"
        )


def test_lelenco_vuoto_degli_esperimenti_non_lascia_il_salto_di_un_gruppo():
    """.azioni porta 24 px sotto di se', che e' il salto fra due gruppi. Senza
    una cartella experiments/ accanto alla corsa — il caso comune mentre si
    lavora a uno step — l'elenco e' alto zero e quei 24 px separavano due cose
    che non c'erano. Terzo caso della famiglia di .registro:empty."""
    assert ".azioni:empty" in _senza_commenti(), "l'elenco vuoto lascia ancora il suo salto"


def test_il_velo_sopra_la_scena_regge_il_testo_che_ci_sta_sopra():
    """Gli altri controlli di contrasto misurano su --superficie e --sfondo, che
    sono carta. Il velo no: sta sopra la scena tridimensionale, e sotto c'e' la
    geometria disegnata. Al 85% il fondo peggiore vale 217 e --tenue sopra
    misurava 3,93 — sotto 4,5:1 per un testo da 14 px (WCAG 1.4.3) — proprio sui
    conteggi, che sono l'unica cosa che dichiara se la nuvola e' decimata."""
    testo = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    trovata = re.search(r"--velo:\s*color-mix\(in srgb, var\(--superficie\) (\d+)%", testo)
    assert trovata is not None, "il velo non e' piu' una miscela leggibile da qui"
    quota = int(trovata.group(1)) / 100
    superficie = _token("--superficie")
    # Il fondo peggiore possibile: nero sotto il velo.
    peggiore = "#" + "".join(f"{round(int(superficie[i:i + 2], 16) * quota):02x}" for i in (1, 3, 5))
    misura = _rapporto(_token("--tenue"), peggiore)
    assert misura >= 4.5, f"il testo sul velo misura {misura:.2f} sul fondo peggiore, sotto 4,5:1"


def test_la_pagina_non_scorre_di_lato_per_la_tabella_della_galleria():
    """La tabella dei candidati e' larga 1013 px dentro un riquadro da 467, e
    il riquadro scorre gia' per conto suo. La sua larghezza contava pero'
    ancora nel traboccamento della pagina: a 500 px di finestra si scorreva
    l'intera pagina di 521 px verso destra, fino a un rettangolo vuoto, con
    l'applicazione fuori dallo schermo. Misurato, e nessun antenato dichiarava
    di traboccare: senza contenere la pittura, overflow-x da solo non basta."""
    testo = _senza_commenti()
    trovata = re.search(r"\.galleria-tabella\s*{([^}]*)}", testo)
    assert trovata is not None, "la regola del riquadro della galleria non si trova piu'"
    assert "contain" in trovata.group(1), (
        "il riquadro non e' contenuto: la sua larghezza torna a far scorrere la pagina"
    )


def test_le_zone_possono_stringersi_sotto_il_loro_contenuto():
    """Una casella di griglia parte da min-width: auto e non scende sotto il
    contenuto piu' largo. La tela della vista e' larga quanto il contenitore e
    il contenitore quanto la tela: stringendo la finestra dal vivo la colonna
    restava alla misura di prima — misurata una tela da 800 px dentro una
    finestra da 500 — e il ResizeObserver di viewport.js non vedeva mai il
    restringimento, perche' a impedirlo era la tela stessa."""
    trovata = re.search(r"\.zona\s*{([^}]*)}", _senza_commenti())
    assert trovata is not None, "la regola delle zone non si trova piu'"
    assert re.search(r"min-width:\s*0", trovata.group(1)), (
        "le zone non si stringono sotto il contenuto: la vista resta larga come prima"
    )


def test_linvito_della_vista_non_viene_riancorato_a_una_colonna_sola():
    """Senza geometria la riga dei conteggi non e' una didascalia: e' l'unico
    contenuto della zona piu' grande dello schermo, distesa e centrata. La
    regola a una colonna sposta i conteggi in cima per non farli scontrare col
    comando del taglio, e scritta senza esclusione rimetterebbe in un angolo
    proprio la frase che l'utente successivo legge per prima."""
    testo = _senza_commenti()
    assert ".conteggi-al-centro" in testo, "l'invito non ha piu' una posizione sua"
    trovata = re.search(r"\.conteggi(:not\(\.conteggi-al-centro\))?\s*{[^}]*bottom:\s*auto", testo)
    assert trovata is not None and trovata.group(1) is not None, (
        "la regola a una colonna riancora anche l'invito, non solo la didascalia"
    )


# --- I colori della scena ----------------------------------------------------
# La zona piu' grande dello schermo e' la vista tridimensionale, e i suoi colori
# stavano in viewport.js come esadecimali nudi: fuori da :root, quindi fuori da
# test_nessun_colore_scritto_a_mano_fuori_dai_token, che vieta esattamente
# questo perche' «nessun controllo di contrasto lo raggiunge». Quel divieto
# sorvegliava un file solo. Questi controlli chiudono l'altro.


def _scena() -> str:
    return (UI_DIR / "viewport.js").read_text(encoding="utf-8")


def _intensita(luce: str) -> float:
    trovata = re.search(rf"{luce}\(0x[0-9a-fA-F]+,\s*([\d.]+)\)", _scena())
    assert trovata is not None, f"l'intensita' di {luce} non si legge piu' da viewport.js"
    return float(trovata.group(1))


def test_la_scena_non_scrive_piu_i_propri_colori_a_mano():
    """Restano solo i bianchi delle due luci, che non sono una scelta di
    tavolozza: 0xffffff e' l'assenza di tinta, cioe' una luce che non colora
    cio' che illumina. Ogni altro esadecimale qui dentro e' un colore che
    nessuna misura di contrasto raggiunge."""
    letterali = set(re.findall(r"0x[0-9a-fA-F]{6}", _scena()))
    assert letterali <= {"0xffffff"}, (
        f"colori della scena scritti fuori da stile.css: {sorted(letterali - {'0xffffff'})}"
    )


def test_ogni_colore_letto_dalla_scena_e_dichiarato():
    """tinta() si alza su un token vuoto invece di disegnare nero, ma si alza a
    video e a corsa avviata. Qui il nome sbagliato si trova prima."""
    testo = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    dichiarati = set(re.findall(r"^\s*(--[\w-]+)\s*:", testo, re.MULTILINE))
    letti = set(re.findall(r'tinta\("(--[\w-]+)"\)', _scena()))
    assert letti, "la scena non legge piu' nessun colore dal foglio"
    assert letti <= dichiarati, f"colori letti e mai dichiarati: {sorted(letti - dichiarati)}"


def test_la_nuvola_non_indossa_piu_il_colore_dell_azione():
    """--accento vale «azione, fuoco, selezione» e la sua forza sta nell'essere
    raro. Indossato da sei milioni di punti sul 55% della finestra non
    distingueva piu' nulla: la stessa tinta del bottone primario e dello step
    aperto era anche il fondale su cui quei due comandi si guardano. E' anche
    l'unico colore saturo che finiva in appendice accanto a un testo composto."""
    assert _token("--nuvola") != _token("--accento"), (
        "la nuvola e' tornata a indossare il colore dell'azione"
    )
    misura = _rapporto(_token("--nuvola"), _token("--sfondo"))
    assert misura >= 3.0, f"la nuvola misura {misura:.2f} sulla carta, sotto 3:1"


def test_la_faccia_illuminata_della_superficie_non_sparisce_sulla_carta():
    """La mesh non e' piatta: le due luci di viewport.js si sommano e una faccia
    rivolta alla luce rende l'albedo per (ambiente + direzionale). A 0xb8b2a7 —
    il valore di prima — quella faccia misurava 1,39:1 sulla carta, cioe' il
    bordo della superficie spariva dove tocca lo sfondo, che e' proprio dove si
    legge la forma. Le due intensita' si rileggono da viewport.js: alzare una
    luce senza scurire l'albedo fa rosso qui invece che a video."""
    fattore = _intensita("AmbientLight") + _intensita("DirectionalLight")
    illuminata = [min(1.0, canale * fattore) for canale in _lineari(_token("--ricostruzione"))]
    misura = _rapporto_fra(_luminanza_lineare(illuminata), _luminanza(_token("--sfondo")))
    assert misura >= 3.0, f"la faccia piena misura {misura:.2f} sulla carta, sotto 3:1"


def test_il_box_di_ritaglio_si_legge_sui_due_fondi_su_cui_e_disegnato():
    """Il box compare al solo step 2, che disegna punti e non mesh: i fondi sono
    la carta dove la nuvola e' rada e la nuvola dove e' fitta, e sono due perche'
    un contorno leggibile su uno solo non e' leggibile (WCAG 1.4.11). E' anche
    la ragione per cui --attrezzo e' piu' chiaro di --avviso invece di essere lo
    stesso arancione: --avviso e' tarato per leggersi sulla carta, e sulla
    nuvola misura 2,33:1."""
    for fondo in ("--sfondo", "--nuvola"):
        misura = _rapporto(_token("--attrezzo"), _token(fondo))
        assert misura >= 3.0, f"il box misura {misura:.2f} su {fondo}, sotto 3:1"
