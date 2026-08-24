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
