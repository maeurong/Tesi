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
