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
    # Le tre schermate ci stanno da quando sono tre: nascono `hidden` nel markup
    # come i sovrapposti della vista, e un `display` aggiunto a una di loro la
    # stamperebbe sopra le altre due. `analisi` e' quella nuova; `ingresso` e
    # `tre-zone` erano gia' nella stessa condizione e non li guardava nessuno --
    # `tre-zone` la propria riga [hidden] ce l'ha, e questo controllo la difende.
    for classe in ["taglio", "vista-vuota", "fantasma-comando",
                   "analisi", "ingresso", "tre-zone"]:
        dichiarazione = re.search(rf"^\.{re.escape(classe)} \{{([^}}]*)\}}", foglio, flags=re.MULTILINE)
        assert dichiarazione is not None, f".{classe} non e' piu' dichiarata"
        if "display:" not in dichiarazione.group(1):
            continue
        assert f".{classe}[hidden]" in foglio, (
            f".{classe} dichiara un display ma non si sa piu' nascondere: "
            "l'attributo hidden non morde, e resta a video"
        )


def test_i_quattro_stadi_restano_leggibili_stretti_e_proiettati():
    """La seconda schermata si guarda a due larghezze molto diverse.

    Su una finestra stretta i quattro stadi devono impilarsi in una colonna
    sola; proiettata in sede di discussione (PRODUCT.md:187) la finestra e'
    larga e la prosa non deve stendersi su tutto lo schermo, dove la riga si
    perde fra una fine e l'inizio della successiva.

    Le due cose in un token e una traccia fluida: `auto-fit` con un `minmax` in
    `rem` -- che segue l'ingrandimento del testo, a differenza dei px -- e il
    tetto di `--misura` che `.vuoto` gia' porta. Una larghezza di colonna scritta
    in pixel farebbe traboccare la griglia sotto quel numero.
    """
    foglio = _senza_commenti()
    regola = re.search(r"^\.stadi \{([^}]*)\}", foglio, flags=re.MULTILINE)
    assert regola is not None, "gli stadi della seconda schermata non sono piu' vestiti"
    colonne = re.search(r"grid-template-columns:([^;]+);", regola.group(1))
    assert colonne is not None, "gli stadi non dichiarano piu' le proprie colonne"
    traccia = colonne.group(1).strip()
    assert "display: grid" in regola.group(1), (
        "gli stadi non sono piu' una griglia: `grid-template-columns` resta scritta e inerte"
    )
    assert "auto-fit" in traccia, (
        f"le colonne sono fissate: stretta la finestra, gli stadi non si impilano ({traccia})"
    )
    minimo = re.search(r"minmax\(\s*([\d.]+)(rem|px)", traccia)
    assert minimo is not None, f"nessun minimo dichiarato per la colonna di uno stadio: {traccia}"
    assert minimo.group(2) == "rem", (
        f"il minimo della colonna e' in px ({minimo.group(0)}): non segue l'ingrandimento del testo"
    )
    # L'unita' da sola non basta: `minmax(1rem, 1fr)` la soddisfa e rimette quattro
    # colonne strettissime sulla finestra piu' stretta. Il numero e' il vincolo.
    assert float(minimo.group(1)) >= 12, (
        f"la colonna di uno stadio puo' scendere a {minimo.group(0)}: quattro colonne "
        "sottili invece di una impilata"
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
