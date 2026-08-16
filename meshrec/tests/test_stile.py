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


def _luminanza(esadecimale: str) -> float:
    """Luminanza relativa sRGB, WCAG 2.x."""
    canali = [int(esadecimale[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def _rapporto(primo: str, secondo: str) -> float:
    a, b = _luminanza(primo), _luminanza(secondo)
    chiaro, scuro = max(a, b), min(a, b)
    return (chiaro + 0.05) / (scuro + 0.05)


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
