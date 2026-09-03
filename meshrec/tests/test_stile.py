"""Controlli testuali sul foglio di stile dell'interfaccia.

Il CSS non ha un `node --check`: una graffa sbagliata non fa rosso nessun test e
rompe la pagina in silenzio, perche' il browser chiude da solo a fine file e
salta cio' che non sa leggere. E' successo davvero durante il Task 16a, spostando
un blocco @media: la graffa di chiusura e' rimasta indietro e a video non si
vedeva nulla. Questi tre controlli sono l'unica sorveglianza che quel file ha.
"""

import re
from pathlib import Path

from meshrec.app.server import UI_DIR
from meshrec.core import steps

# I commenti del foglio contengono regole citate per iscritto, graffe comprese
# (per esempio «.viewport { flex: 1 } di un genitore alto quanto il suo
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


def test_ogni_stato_del_server_ha_il_suo_pallino_nella_colonna():
    """Il pallino in testa a ogni riga della colonna e' un ruolo di colore per
    stato, e il vocabolario degli stati non vive qui: lo decide `run_state`.

    Uno stato nuovo la' dentro che nessuna regola raccoglie non rompe niente e
    non fa rosso niente. Disegna l'anello vuoto del «mai eseguito» sopra uno
    step che magari e' fallito: la colonna direbbe con sicurezza il contrario
    di cio' che e' successo, che e' il modo peggiore di sbagliare per una
    figura fatta per essere letta in un colpo d'occhio.
    """
    foglio = _senza_commenti()
    sorgente = Path(steps.__file__).read_text(encoding="utf-8")
    stati = set(re.findall(r'corrente = "([^"]+)"', sorgente))
    # Senza questa riga il controllo diventa cieco invece di rosso: cambiato il
    # nome della variabile in run_state, l'insieme resta vuoto, il ciclo non
    # gira e il test passa senza aver guardato nulla. Un superinsieme e non un
    # conteggio: uno stato in piu' lo deve raccogliere il ciclo qui sotto, non
    # fermare questa riga.
    predefinito = "mai eseguito"
    noti = {predefinito, "fallito", "non valido", "valido"}
    assert stati >= noti, f"run_state non dichiara piu' gli stati noti: {sorted(stati)}"
    for stato in sorted(stati - {predefinito}):
        # `replace(..., 1)` come lo scrive app.js, che usa la String.replace di
        # JavaScript e sostituisce solo la prima occorrenza: se un giorno uno
        # stato avra' due spazi, il test chiedera' al foglio la stessa classe
        # che il modulo scrive davvero, non quella che sarebbe corretta.
        regola = f".stato-{stato.replace(' ', '-', 1)} .step-nome::before"
        assert regola in foglio, f"stato senza pallino nella colonna: «{stato}» ({regola})"


def test_il_valore_di_una_metrica_ha_una_colonna_sua_e_non_quella_che_avanza():
    """Due controlli su una tabella che a video era illeggibile.

    Con `grid-template-columns: auto 1fr` la colonna dell'etichetta prendeva la
    larghezza del suo contenuto piu' lungo -- 298 dei 319 pixel della zona,
    misurati nel browser sullo step 7 -- e al valore restava quel che avanzava,
    8,98 pixel. Non sbordava: `overflow-wrap: anywhere` autorizza il numero a
    spezzarsi fra due cifre qualunque, quindi «339.710» scendeva in sette righe
    invece di chiedere spazio. La colonna del valore va DICHIARATA, e la sua
    larghezza si dichiara in `ch`, che e' la larghezza di una cifra.

    E il valore che in quella colonna non ci sta comunque -- una lista chiusa da
    JSON.stringify -- viene marcato da app.js con una classe: qui si controlla
    che il foglio la vesta davvero, e che la porti fuori dalla colonna. Una
    classe scritta in un file e assente nell'altro non fa rosso niente da se':
    il valore resta stretto e nessuno se ne accorge finche' non lo guarda.
    """
    foglio = _senza_commenti()
    regola = foglio.split(".metriche {", 1)[1].split("}", 1)[0]
    colonne = re.search(r"grid-template-columns:([^;]+);", regola)
    assert colonne is not None, "la tabella delle metriche non dichiara piu' le proprie colonne"
    assert "ch" in colonne.group(1), (
        "la colonna del valore non ha piu' una larghezza dichiarata in ch: quel che avanza "
        f"puo' essere una cifra, e il numero scende in verticale ({colonne.group(1).strip()})"
    )

    modulo = (UI_DIR / "app.js").read_text(encoding="utf-8")
    trovata = re.search(r'^const CLASSE_VALORE_LARGO = "([^"]+)";$', modulo, flags=re.MULTILINE)
    assert trovata is not None, "app.js non dichiara piu' CLASSE_VALORE_LARGO"
    selettore = f".metriche dd.{trovata.group(1)}"
    assert selettore in foglio, (
        f"app.js marca i valori lunghi con «{trovata.group(1)}» e il foglio non la veste: {selettore}"
    )
    corpo = foglio.split(selettore, 1)[1].split("}", 1)[0]
    assert "grid-column" in corpo, (
        "la classe non porta piu' il valore fuori dalla colonna del numero"
    )


def test_la_misura_leggibile_e_una_lunghezza_e_raggiunge_la_prosa():
    """Due difetti che si tenevano per mano, misurati nel browser.

    `--misura` valeva `66ch`. `ch` e' l'avanzamento della cifra `0`, che in
    questo stack di sistema e' 1,44 volte il carattere medio della prosa
    italiana -- rapporto misurato su 496 caratteri presi dalla pagina, identico
    sui tre corpi. `66ch` non sono 66 caratteri ma 95: venti oltre il tetto che
    il commento accanto dichiarava di rispettare. E `ch` si risolve sul corpo E
    sul peso di chi lo usa, quindi lo stesso token dava otto larghezze diverse
    ai figli della schermata d'ingresso (misurate: 459, 556, 588, 598, 632, 681,
    849, 964). Una lunghezza assoluta chiude entrambi, e in `rem` segue ancora
    l'ingrandimento del testo.

    L'altra meta': `.aiuto` veste anche i `<small>` dell'ingresso, che sono
    figli diretti di `<section>` e restano inline. `max-width` non si applica a
    una scatola inline non rimpiazzata, quindi la' la misura non agiva affatto
    -- 145 caratteri su una riga, misurati. Senza `display: block` il tetto
    torna inerte e non se ne accorge nessuno, perche' la regola resta scritta.
    """
    foglio = _senza_commenti()
    misura = re.search(r"--misura:\s*([^;]+);", foglio)
    assert misura is not None, "il foglio non dichiara piu' --misura"
    valore = misura.group(1).strip()
    assert not valore.endswith("ch"), (
        f"--misura e' tornata in `ch` ({valore}): non sono caratteri, e cambia con il "
        "corpo e il peso di ogni ruolo che la usa"
    )
    assert re.fullmatch(r"[\d.]+(rem|px)", valore), (
        f"--misura non e' piu' una lunghezza assoluta: {valore}"
    )

    regola = foglio.split(".aiuto {", 1)[1].split("}", 1)[0]
    assert "display: block" in regola, (
        "`.aiuto` senza `display: block`: sui <small> dell'ingresso resta inline, "
        "e su una scatola inline il max-width qui accanto non fa nulla"
    )


def test_ogni_sovrapposto_della_vista_sa_ancora_nascondersi():
    """`hidden` non basta su un elemento che dichiara un `display`.

    L'attributo vale `display: none` da foglio dell'utente, che la piu' debole
    delle regole d'autore batte. Il comando del taglio l'ha gia' pagato -- il
    commento accanto alla sua regola lo dice per iscritto -- e lo stato vuoto
    della vista e' finito nella stessa forma: `display: grid`, un `hidden`
    scritto nel markup, e senza la propria riga resterebbe stampato al centro
    della tela sopra il pezzo, per sempre.

    Sui sovrapposti della vista e non su tutto il foglio: sono loro a nascere
    nascosti nel markup, ed e' li' che l'errore non si vede provando la pagina
    a corsa finita.
    """
    foglio = _senza_commenti()
    # Le due schermate ci stanno: nascono `hidden` nel markup come i
    # sovrapposti della vista, e un `display` aggiunto a una delle due la
    # stamperebbe sopra l'altra. `tre-zone` la propria riga [hidden] ce l'ha, e
    # questo controllo la difende.
    for classe in ["taglio", "vista-vuota", "fantasma-comando",
                   "ingresso", "tre-zone"]:
        dichiarazione = re.search(rf"^\.{re.escape(classe)} \{{([^}}]*)\}}", foglio, flags=re.MULTILINE)
        assert dichiarazione is not None, f".{classe} non e' piu' dichiarata"
        if "display:" not in dichiarazione.group(1):
            continue
        assert f".{classe}[hidden]" in foglio, (
            f".{classe} dichiara un display ma non si sa piu' nascondere: "
            "l'attributo hidden non morde, e resta a video"
        )




def _rapporto(primo: str, secondo: str) -> float:
    """Il rapporto di contrasto WCAG fra due esadecimali, calcolato e non creduto.

    Formula di WCAG 2.1 (1.4.3): canale in [0,1], linearizzazione, luminanza
    relativa, (L+0,05)/(l+0,05). Quindici righe di stdlib: la dipendenza in più
    costerebbe più della formula.
    """
    def luminanza(esadecimale: str) -> float:
        grezzo = esadecimale.lstrip("#")
        canali = [int(grezzo[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        lineari = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
        return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]

    alto, basso = sorted((luminanza(primo), luminanza(secondo)), reverse=True)
    return (alto + 0.05) / (basso + 0.05)


def test_il_grigio_degli_stati_vuoti_regge_su_tutte_e_due_le_carte():
    """Gli stati vuoti sono l'intera schermata dell'analisi, e vengono proiettati.

    `--tenue` è il colore di `.vuoto` e di `.aiuto`, cioè di ogni frase che dice
    perché qualcosa non c'è. Compare su due fondi diversi: `--superficie` dentro
    le schede degli stadi e dentro le zone, `--sfondo` sulla schermata
    dell'analisi, che un fondo proprio non lo dichiara.

    Finora il rapporto era affermato da un commento in `:root` e da nessun
    controllo. Un commento non cade quando qualcuno schiarisce il grigio: era a
    posto per fortuna, non per un cancello. 4,5:1 è la soglia AA per il testo
    normale, e `PRODUCT.md` (sezione Accessibility & Inclusion) dichiara di
    puntare a WCAG AA pieno con la postilla della proiezione in discussione.
    """
    testo = _senza_commenti()
    token = dict(re.findall(r"^\s*(--[\w-]+):\s*(#[0-9a-fA-F]{6});", testo, re.MULTILINE))
    for nome in ("--tenue", "--testo", "--superficie", "--sfondo"):
        assert nome in token, f"{nome} non e' piu' un esadecimale in :root: {sorted(token)}"
    for fondo in ("--superficie", "--sfondo"):
        for davanti in ("--tenue", "--testo"):
            rapporto = _rapporto(token[davanti], token[fondo])
            assert rapporto >= 4.5, (
                f"{davanti} su {fondo} vale {rapporto:.2f}:1, sotto il 4,5:1 di WCAG AA"
            )


def test_sotto_la_soglia_stretta_le_tre_zone_diventano_una_colonna():
    """La colonna a dodici step va letta anche su una finestra stretta.

    A tre tracce fisse — 18rem + 22rem + 22rem — sotto quella somma la vista, cioè
    l'unica cosa che quella schermata esiste per mostrare, resta più stretta del
    pannello che la commenta. La regola che rimedia sta in fondo al foglio e non
    la guardava nessun controllo: cancellata, la pagina non fa rosso niente e si
    rompe soltanto su uno schermo che chi la prova non ha davanti.
    """
    foglio = _senza_commenti()
    blocco = re.search(r"@media \(max-width: (\d+)rem\) \{(.*?)\n\}", foglio, flags=re.S)
    assert blocco is not None, "il foglio non porta piu' la soglia della colonna unica"
    assert ".tre-zone { grid-template-columns: 1fr; }" in blocco.group(2), (
        "sotto la soglia le tre zone non si impilano piu': la vista resta piu' stretta "
        "del pannello che la commenta"
    )


def test_ogni_cosa_che_prende_il_fuoco_lo_mostra():
    """WCAG 2.4.7: da sola tastiera il contorno del fuoco è l'unico canale che
    dice dove ci si trova.

    La regola per le caselle c'era e quella per i menù no, e la schermata
    dell'analisi ne porta tre — il solutore, la categoria d'uso e l'azione
    sismica: senza, il fuoco ci passava sopra invisibile. L'elenco è di
    famiglie, non di selettori esatti: ogni voce è una forma di comando che una
    delle tre schermate mette davvero sotto il tabulatore.
    """
    testo = _senza_commenti()
    for famiglia in (
        ".bottone", ".campo input", ".campo select", ".step",
        ".registro",
        ".gruppo details > summary", ".viewport canvas", "h2",
    ):
        assert f"{famiglia}:focus-visible" in testo, (
            f"«{famiglia}» prende il fuoco e non lo mostra: da sola tastiera il "
            "cursore ci passa sopra invisibile (WCAG 2.4.7)"
        )


def test_un_campo_bloccato_si_vede_bloccato():
    """Un valore solo non e' una scelta, e il pannello lo mette in un campo che
    non si scrive (`method` allo step 5, `mode` allo step 8). Bloccato senza
    dirlo e' peggio che modificabile: chi ci batte dentro non capisce perche'
    non succede niente. Il fondo spento e il testo tenue lo dicono senza una
    riga di prosa in piu'.

    Mutazione che lo uccide: togliere la regola su `input[readonly]`.
    """
    testo = _senza_commenti()
    regola = re.search(r"\.campo input\[readonly\]\s*\{([^}]*)\}", testo)
    assert regola is not None, (
        "un campo bloccato si vede come una casella vuota qualunque"
    )
    assert "background" in regola.group(1), (
        "il campo bloccato non cambia fondo: bloccato senza dirlo"
    )


def _composito(sopra: str, quota: float, sotto: str) -> str:
    """Il colore che si vede dove una tinta trasparente sta su un fondo opaco.

    `color-mix(in srgb, X n%, transparent)` vale X con alpha n/100: il mix è
    premoltiplicato, quindi i canali tornano X esatti una volta divisi per
    l'alpha. Sopra un fondo opaco resta la media pesata canale per canale, ed è
    quella che l'occhio misura -- non X, che sul fondo non ci arriva mai puro.
    """
    su = [int(sopra.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    giu = [int(sotto.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(quota * a + (1 - quota) * b):02x}" for a, b in zip(su, giu))


def _colori_del_foglio() -> dict[str, str]:
    """I token esadecimali di `:root`, più i tre fondi che il foglio compone.

    `--evidenza`, `--selezione` e `--spento` non sono un colore finché non si sa
    su cosa stanno. In questo foglio stanno sulla carta bianca: `.zona-step`,
    `.zona-dettaglio` e `.ingresso` dichiarano tutte `--superficie`, e la riga
    aperta, la riga sotto il puntatore, il candidato di fronte e il campo
    bloccato vivono lì dentro.
    """
    testo = _senza_commenti()
    token = dict(re.findall(r"^\s*(--[\w-]+):\s*(#[0-9a-fA-F]{6});", testo, re.MULTILINE))
    for nome in ("--evidenza", "--selezione", "--spento"):
        composto = re.search(
            rf"{nome}:\s*color-mix\(in srgb, var\((--[\w-]+)\) (\d+)%, transparent\)", testo
        )
        assert composto is not None, f"{nome} non e' piu' una tinta trasparente composta in :root"
        token[f"{nome}-su-superficie"] = _composito(
            token[composto.group(1)], int(composto.group(2)) / 100, token["--superficie"]
        )
    return token


def test_la_colonna_degli_stati_si_legge_anche_sul_fondo_della_riga_aperta():
    """Le parole di stato sono testo normale, non decorazione: la soglia è 4,5:1.

    La colonna degli step dice a che punto sta la corsa con due canali, il
    pallino e la parola in fondo alla riga. Il foglio giudicava tutti e due
    contro il 3:1 di WCAG 1.4.11, che è la soglia di ciò che porta uno stato
    *graficamente*: giusta per il pallino, sbagliata per la parola. `--tipo-nota`
    è 13px, e «large text» comincia a 18,66px in grassetto, quindi la parola
    risponde a 1.4.3 e vuole 4,5:1. Sul fondo della riga aperta -- il più scuro
    del foglio -- «mai eseguito» valeva 4,21:1 e «non valido» 4,11:1: sotto
    soglia proprio dove il pubblico di una discussione sta guardando.

    Il pallino porta le stesse quattro tinte sugli stessi quattro fondi: 4,5:1
    gli sta sopra il suo 3:1 per costruzione, e non serve un secondo controllo.

    Mutazione che lo uccide: schiarire `--tenue` o `--avviso`, o alzare la quota
    di `--selezione`.
    """
    token = _colori_del_foglio()
    fondi = {
        "riga ferma": token["--superficie"],
        "riga sotto il puntatore": token["--evidenza-su-superficie"],
        "riga aperta": token["--selezione-su-superficie"],
        "campo bloccato": token["--spento-su-superficie"],
    }
    for dove, fondo in fondi.items():
        for davanti in ("--tenue", "--accento", "--avviso", "--guasto"):
            rapporto = _rapporto(token[davanti], fondo)
            assert rapporto >= 4.5, (
                f"{davanti} sulla {dove} ({fondo}) vale {rapporto:.2f}:1, sotto il 4,5:1 "
                "che WCAG 1.4.3 chiede a un testo di 13px"
            )


# Il foglio porta i rapporti misurati accanto alle regole: è la sua forma di
# prova, e senza un cancello è una prova che nessuno rifà. Qui stanno le coppie
# che la riga aperta mette in gioco, quelle che questo cambio ha toccato.
RAPPORTI_SCRITTI = (
    ("--testo", "--superficie", "17,21"),
    ("--tenue", "--superficie", "6,55"),
    ("--accento", "--superficie", "7,49"),
    ("--avviso", "--superficie", "6,59"),
    ("--guasto", "--superficie", "7,71"),
    ("--testo", "--selezione-su-superficie", "13,06"),
    ("--tenue", "--selezione-su-superficie", "4,97"),
    ("--accento", "--selezione-su-superficie", "5,69"),
    ("--avviso", "--selezione-su-superficie", "5,00"),
    ("--guasto", "--selezione-su-superficie", "5,85"),
    ("--bordo-comando", "--selezione-su-superficie", "2,46"),
    ("--tenue", "--spento-su-superficie", "5,85"),
    ("--tenue", "--accento", "1,14"),
)


def test_i_rapporti_scritti_intorno_alla_riga_aperta_sono_quelli_dei_colori_dichiarati():
    """Un commento che porta un numero è vero finché nessuno tocca il token.

    I rapporti stanno scritti accanto alle regole perché il foglio si legge come
    un documento e non come una tabella di valori; ma un numero scritto non cade
    quando il colore sotto cambia, e un foglio che afferma 4,21:1 dove ne misura
    4,97:1 è peggio di un foglio che tace. Questo controllo li rifà tutti.

    Mutazione che lo uccide: cambiare un token senza riscrivere il numero, o
    riscrivere il numero senza cambiare il token.
    """
    token = _colori_del_foglio()
    grezzo = (UI_DIR / "stile.css").read_text(encoding="utf-8")
    for davanti, fondo, scritto in RAPPORTI_SCRITTI:
        calcolato = f"{_rapporto(token[davanti], token[fondo]):.2f}".replace(".", ",")
        assert calcolato == scritto, (
            f"{davanti} su {fondo} misura {calcolato}:1, e il foglio scrive {scritto}:1"
        )
        assert f"{scritto}:1" in grezzo, (
            f"il rapporto di {davanti} su {fondo} ({scritto}:1) non e' piu' scritto "
            "da nessuna parte nel foglio: la misura resta e la prova sparisce"
        )


def test_l_etichetta_di_una_metrica_va_a_capo_come_prosa_e_non_come_una_chiave():
    """Quella colonna ha cambiato natura, e le regole di prima erano giuste per
    la natura di prima.

    Portava chiavi -- `geometric_error · cloud_to_mesh · mean`, parole sole e
    inspezzabili -- e `overflow-wrap: anywhere` era l'unico modo di non
    sfondare un pannello largo 22rem. Da quando porta l'etichetta italiana con
    la sua unita', in circa 200 px di colonna va a capo due o tre volte, e
    `anywhere` spezza le parole a meta' in un punto qualunque.

    Il valore invece resta `anywhere`: e' li' che finisce una lista chiusa da
    JSON.stringify, che nessuna sillabazione sa dividere.

    Mutazione che lo uccide: riportare `overflow-wrap: anywhere` sul `dt`.
    """
    foglio = _senza_commenti()
    etichetta = foglio.split(".metriche dt {", 1)[1].split("}", 1)[0]
    assert "anywhere" not in etichetta, (
        "l'etichetta torna a spezzarsi come una chiave: su una frase italiana "
        f"`anywhere` taglia le parole in un punto qualunque ({etichetta.strip()})"
    )
    assert "hyphens" in etichetta, (
        "senza sillabazione una parola lunga apre un buco nella colonna invece "
        "di andare a capo dove l'italiano vuole"
    )
    assert "--interlinea)" in etichetta, (
        "l'etichetta tiene l'interlinea delle righe che NON vanno a capo, e "
        "adesso va a capo: il foglio i due valori li distingue gia'"
    )

    valore = foglio.split(".metriche dd {", 1)[1].split("}", 1)[0]
    assert "anywhere" in valore, (
        "il valore ha perso `anywhere`: una lista chiusa da JSON.stringify non "
        "ha punti in cui una sillabazione la possa dividere"
    )

    tabella = foglio.split(".metriche {", 1)[1].split("}", 1)[0]
    assert "align-items: baseline" in tabella, (
        "le due colonne hanno due interlinee diverse: senza linea di base "
        "condivisa l'etichetta e il suo numero partono da due altezze diverse"
    )
