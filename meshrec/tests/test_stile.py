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
    for classe in ["taglio", "vista-vuota"]:
        dichiarazione = re.search(rf"^\.{re.escape(classe)} \{{([^}}]*)\}}", foglio, flags=re.MULTILINE)
        assert dichiarazione is not None, f".{classe} non e' piu' dichiarata"
        if "display:" not in dichiarazione.group(1):
            continue
        assert f".{classe}[hidden]" in foglio, (
            f".{classe} dichiara un display ma non si sa piu' nascondere: "
            "l'attributo hidden non morde, e resta a video"
        )
