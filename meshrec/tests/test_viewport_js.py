"""Il modulo della vista dalla parte del browser: le decisioni pure, eseguite.

`ui/viewport.js` non e' importabile da qui, e le sue funzioni interne stanno
dentro la chiusura di creaViewport, che `node` non puo' aprire senza un
three.js finto. Percio' le decisioni che questa fase aggiunge sono funzioni
pure di primo livello: si estraggono dal sorgente e si eseguono davvero,
esattamente come tests/test_app_js.py fa con le funzioni di app.js.

Un controllo che cerca una sottostringa nel sorgente passa anche quando la
logica e' capovolta, e su questo ramo e' gia' successo (vedi il docstring di
tests/test_app_js.py). Qui la logica pura si esegue. Sul testo restano le sole
asserzioni su cio' che vive dentro la chiusura di creaViewport e che da fuori
non si puo' eseguire: chi chiama chi, e la bandiera della prima inquadratura.
Sono l'eccezione, e ognuna e' stata provata mutando il sorgente e rigirando il
banco — un'asserzione sul testo scritta senza quella prova sorveglia una riga
che potrebbe non esserci.

ponytail: il banco (_node, _esegui, _sorgente_di) e' ricopiato da
tests/test_app_js.py invece di essere condiviso in un conftest. Condividerlo
vorrebbe dire toccare le settantanove chiamate al banco di quel file, che e'
lungo 3719 righe e non ne guadagna niente. Se nasce un terzo file di questa
famiglia, allora conftest.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from meshrec.app.server import UI_DIR


def _node() -> str:
    percorso = shutil.which("node")
    if percorso is None:
        pytest.skip("node non installato: la logica resta verificata a mano")
    return percorso


def _esegui(tmp_path: Path, sorgente: str) -> str:
    """Il banco: scrive il modulo di prova e lo esegue. Rosso e' l'assert di
    `node` che salta, e il suo messaggio arriva qui dentro."""
    prova = tmp_path / "prova.mjs"
    prova.write_text(sorgente, encoding="utf-8")
    esito = subprocess.run([_node(), str(prova)], capture_output=True, text=True)
    assert esito.returncode == 0, esito.stderr
    return esito.stdout


def _modulo() -> str:
    return (UI_DIR / "viewport.js").read_text(encoding="utf-8")


def _senza_commenti(modulo: str) -> str:
    return "\n".join(r for r in modulo.splitlines() if not r.lstrip().startswith("//"))


def _sorgente_di(nome: str, testo: str) -> str:
    """Il corpo di una funzione di primo livello, dalla firma alla graffa che
    la chiude in prima colonna. `export` cade: serve a chi importa il modulo,
    non a chi ne esegue una funzione da sola."""
    assert f"function {nome}(" in testo, f"il modulo non ha una funzione {nome}"
    corpo = testo.split(f"function {nome}(", 1)[1]
    return f"function {nome}(" + corpo.split("\n}\n", 1)[0] + "\n}"


def _funzioni(*nomi: str) -> str:
    testo = _modulo()
    return "\n".join(_sorgente_di(nome, testo) for nome in nomi)


_INTESTAZIONE = "import assert from 'node:assert/strict';\n"


# La soglia non e' orbita.raggio: quello e' la distanza fra camera e centro, e
# cio' che si vede sul piano del centro e' la semialtezza raggio * tan(fov / 2),
# con fov 50 poco meno della meta'. Scritta qui una volta perche' i due controlli
# la usino dai due lati dello stesso confine.
_SEMIALTEZZA = "const soglia = 100 * Math.tan((25 * Math.PI) / 180);\n"


def test_un_ingombro_dentro_la_vista_non_fa_reinquadrare(tmp_path):
    """Criterio 1 della spec: passando dallo step 3 al 4 la camera resta dove
    l'utente l'aveva messa. Il centro nuovo cade dentro cio' che la camera sta
    gia' mostrando, quindi la geometria e' visibile e spostare la camera non
    aggiungerebbe niente se non la sensazione di ricominciare da capo."""
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("fuoriDallaVista") + _SEMIALTEZZA + """
assert.equal(fuoriDallaVista([10, 0, 0], [0, 0, 0], 100, 50), false);
assert.equal(fuoriDallaVista([0, 0, 0], [0, 0, 0], 100, 50), false);
// Il confine, dal lato di dentro: appena dentro la semialtezza visibile la
// geometria e' ancora inquadrata.
assert.equal(fuoriDallaVista([soglia * 0.999, 0, 0], [0, 0, 0], 100, 50), false);
""")


def test_un_ingombro_fuori_dalla_vista_fa_reinquadrare(tmp_path):
    """Criterio 2. Senza questo, il test qui sopra si soddisfa anche non
    reinquadrando mai: e' il difetto opposto e altrettanto reale, perche'
    cambiando corsa la camera resterebbe puntata sul vuoto senza che nulla lo
    spieghi."""
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("fuoriDallaVista") + _SEMIALTEZZA + """
assert.equal(fuoriDallaVista([soglia * 1.001, 0, 0], [0, 0, 0], 100, 50), true);
// Il centro a 0,7 volte il raggio dell'orbita: sta dentro la sfera e fuori
// dallo schermo. Misurando sul raggio la guardia lo lasciava passare, e a video
// restava il vuoto — cioe' il caso che questa guardia esiste per evitare.
assert.equal(fuoriDallaVista([70, 0, 0], [0, 0, 0], 100, 50), true);
assert.equal(fuoriDallaVista([1000, 0, 0], [0, 0, 0], 100, 50), true);
// Le tre componenti contano tutte: una distanza calcolata sul solo asse x
// direbbe «dentro» a una corsa spostata in profondita'.
assert.equal(fuoriDallaVista([0, 0, 1000], [0, 0, 0], 100, 50), true);
assert.equal(fuoriDallaVista([60, 60, 60], [0, 0, 0], 100, 50), true);
// Lo stesso punto con un obiettivo piu' largo e' dentro: senza questa, un
// corpo che ignora il fov e confronta col raggio passerebbe tutto il resto.
assert.equal(fuoriDallaVista([70, 0, 0], [0, 0, 0], 100, 100), false);
""")


def test_i_due_disegni_non_azzerano_piu_la_camera():
    """La funzione pura decide bene solo se qualcuno la interroga. Le due
    strade che disegnano devono passare dalla guardia: una chiamata diretta a
    inquadra() rimetterebbe l'azzeramento senza toccare fuoriDallaVista, e i
    due controlli qui sopra resterebbero verdi.

    Si conta invece di cercare: `inquadra();` compare tre volte — due dentro
    inquadraSeServe e una nel tasto `f`, che e' un comando esplicito
    dell'utente, cioe' l'uso che la § 4 della spec ammette. Una quarta e' una
    strada che disegna e che e' tornata ad azzerare, e va guardata prima di
    alzare ancora questa soglia: la soglia serve a costringere a quello
    sguardo, non a essere aggiornata per far tornare il verde.
    """
    testo = _senza_commenti(_modulo())
    assert testo.count("inquadraSeServe();") == 2, (
        "le due strade che disegnano devono passare dalla guardia"
    )
    assert testo.count("inquadra();") == 3, (
        "inquadra() e' chiamata da qualcuno oltre a inquadraSeServe e al tasto f: "
        "la camera torna ad azzerarsi a ogni step"
    )


def test_la_guardia_e_la_memoria_dell_inquadratura_sono_scritte_come_decidono():
    """La riga che risolve il difetto di Mario e' la memoria dell'ultima
    inquadratura, e vive dentro la chiusura di creaViewport: da fuori non si
    esegue senza costruire un three.js finto. Restava percio' scoperta, e i
    controlli qui sopra erano verdi anche togliendo la memoria, capovolgendo la
    guardia o capovolgendo la condizione della prima inquadratura — mutato il
    sorgente e rigirato il banco, non dedotto.

    Le cinque asserzioni qui sono sul testo, che e' il modo debole: si
    accettano solo perche' ognuna e' stata provata contro la mutazione che deve
    prendere. Una sesta scritta senza quella prova non varrebbe niente.
    """
    testo = _senza_commenti(_modulo())
    assert "centroInquadrato = orbita.centro.clone();" in testo, (
        "inquadra() non ricorda che cosa ha inquadrato: la prima inquadratura "
        "non finisce mai e ogni step torna a reinquadrare, che e' il difetto "
        "per intero"
    )
    assert "if (centroInquadrato === null) {" in testo, (
        "la condizione della prima inquadratura e' capovolta: il primo disegno "
        "non inquadra e tutti quelli dopo si'"
    )
    assert "if (fuoriDallaVista(" in testo, (
        "la guardia non interroga fuoriDallaVista: la funzione pura decide bene "
        "e nessuno la ascolta"
    )
    assert "if (!fuoriDallaVista(" not in testo, (
        "la guardia e' capovolta: reinquadra quando la geometria e' gia' a video "
        "e resta ferma quando non lo e'"
    )
    assert "PerspectiveCamera(FOV_GRADI," in testo, (
        "la camera nasce con un fov scritto a mano: la soglia della guardia si "
        "calcola sull'altro, e i due divergono senza che nulla lo dica"
    )


# --------------------------------------------------------------------------
# Il pan, e il difetto che il pan puo' riaprire.
# --------------------------------------------------------------------------


def test_lo_spostamento_segue_il_cursore(tmp_path):
    """Un trascinamento lungo quanto la tela sposta la vista di tutta l'altezza
    visibile a quella distanza: e' cio' che rende il gesto «il punto sotto il
    dito resta sotto il dito» invece di una velocita' scelta a caso.

    Con fov 50 gradi (FOV_GRADI) e raggio 1000, l'altezza visibile e'
    2 * 1000 * tan(25 gradi).
    """
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("scalaDelloSpostamento") + """
const altezzaTela = 600;
const scala = scalaDelloSpostamento(1000, altezzaTela, 50);
const attesa = 2 * 1000 * Math.tan((25 * Math.PI) / 180);
assert.ok(
  Math.abs(scala * altezzaTela - attesa) < 1e-9,
  `un trascinamento di tutta la tela sposta ${scala * altezzaTela}, atteso ${attesa}`,
);
// Piu' lontano si guarda, piu' un pixel vale: senza, sul telaio largo 2.759 mm
// il gesto sarebbe microscopico da lontano e violento da vicino.
assert.ok(scalaDelloSpostamento(2000, altezzaTela, 50) > scala);
// Una tela piu' alta mostra la stessa scena su piu' pixel, quindi ogni pixel
// vale meno.
assert.ok(scalaDelloSpostamento(1000, 1200, 50) < scala);
""")


def _comandi() -> str:
    trovato = re.search(r'const COMANDI = "([^"]*)"', _modulo())
    assert trovato is not None, "la costante COMANDI non e' piu' nel modulo"
    return trovato.group(1)


def test_l_etichetta_della_tela_dichiara_i_comandi_nuovi():
    """L'aria-label e' il contenuto testuale equivalente della tela: se dichiara
    meno di quanto la tela fa, chi non vede la scena non sa che il comando
    esiste. Le quattro parole sono i quattro verbi, non le quattro scorciatoie:
    l'etichetta si ascolta di seguito alla descrizione della geometria, quindi
    resta una frase e non diventa un elenco di tasti."""
    comandi = _comandi()
    for parola in ("ruotare", "spostare", "zoom", "inquadrare"):
        assert parola in comandi, f"l'etichetta della tela non nomina «{parola}»"


def test_la_traslazione_e_legata_a_maiusc_sia_col_mouse_sia_da_tastiera():
    """Le due strade sono due, e provarne una sola lascia l'altra scoperta: chi
    non usa il mouse resterebbe senza pan, che e' il difetto che questa fase
    chiude. Le cinque chiamate attese sono il trascinamento e le quattro
    frecce; la definizione non conta, altrimenti togliere una freccia
    resterebbe verde."""
    testo = _senza_commenti(_modulo())
    assert "evento.shiftKey" in testo, "nessun comando e' legato a maiusc"
    chiamate = testo.count("trasla(") - testo.count("function trasla(")
    assert chiamate == 5, (
        f"le cinque strade attese sono il trascinamento e le quattro frecce, "
        f"trovate {chiamate}"
    )


def _voce_da_tastiera(chiave: str) -> str:
    """Il corpo di una voce della tabella dei tasti. Dentro non ci sono graffe,
    quindi la prima chiude la voce."""
    trovato = re.search(
        rf"{re.escape(chiave)}: \(maiusc\) => \{{([^}}]*)\}}", _senza_commenti(_modulo()),
    )
    assert trovato is not None, f"la tabella dei tasti non ha piu' una voce {chiave}"
    return trovato.group(1)


def test_il_verso_dello_spostamento_e_quello_del_gesto_e_dello_scorrere():
    """I segni sono la meta' del pan, e sono l'unica meta' che nessun conteggio
    vede: invertirne uno lascia cinque chiamate a trasla() e una scala giusta.

    Due convenzioni, e sono due apposta. Col puntatore il contenuto segue il
    dito — trascinando a destra la geometria va a destra, quindi la camera va a
    sinistra, che e' il meno davanti a dx. Da tastiera le frecce spostano il
    punto di vista, come lo scorrere di una pagina: freccia sinistra porta la
    vista a sinistra e la geometria scorre a destra. La seconda non e' una
    scelta libera, e' quella che le frecce di questo modulo gia' seguivano
    (`ArrowLeft: orbita.theta -= 0.1` equivale a trascinare a destra): il verso
    opposto metterebbe due convenzioni dentro lo stesso tasto, la freccia sola
    che porta la geometria di la' e la freccia con maiusc che la porta di qua.

    Sul testo per la stessa ragione delle altre asserzioni di questo file — il
    pan vive nella chiusura — e ognuna e' stata provata invertendo il segno che
    sorveglia e rigirando il banco.
    """
    testo = _senza_commenti(_modulo())
    assert "orbita.centro.addScaledVector(destra, -dx * scala);" in testo, (
        "il trascinamento orizzontale e' al contrario: la geometria scappa dalla "
        "parte opposta al dito"
    )
    assert "orbita.centro.addScaledVector(alto, dy * scala);" in testo, (
        "il trascinamento verticale e' al contrario: la geometria scappa dalla "
        "parte opposta al dito"
    )
    versi = {
        "ArrowLeft": "trasla(PASSO_TASTIERA, 0)",
        "ArrowRight": "trasla(-PASSO_TASTIERA, 0)",
        "ArrowUp": "trasla(0, PASSO_TASTIERA)",
        "ArrowDown": "trasla(0, -PASSO_TASTIERA)",
    }
    for chiave, atteso in versi.items():
        assert atteso in _voce_da_tastiera(chiave), (
            f"{chiave} con maiusc sposta la vista dalla parte sbagliata: la stessa "
            f"freccia porterebbe la geometria di qua da sola e di la' con maiusc"
        )


def test_la_guardia_misura_dall_ultimo_ingombro_inquadrato_e_non_dal_centro_che_il_pan_sposta():
    """Il pan e' il secondo scrittore di orbita.centro, e da li' il difetto che
    la guardia aveva appena chiuso puo' rientrare per un'altra porta: chi
    trasla lungo il muro porta orbita.centro lontano dal centroide
    dell'ingombro, e al passaggio di step la distanza supera la soglia e la
    vista si riazzera — proprio il reclamo che questa fase chiude.

    A essere memorizzato e' il **centro**, non la distanza: la soglia si calcola
    sul raggio corrente, che la rotella e i tasti +/- scrivono, ed e' giusto
    cosi'. La domanda della guardia e' se la geometria nuova sia dentro cio' che
    si vede *adesso*, e cio' che si vede adesso dipende dallo zoom di adesso.
    Con un raggio memorizzato la soglia resterebbe larga a zoom stretto e la
    vista non si reinquadrerebbe nemmeno con la geometria fuori schermo, che e'
    il difetto opposto e peggiore.

    Il riferimento della guardia e' percio' il centro dell'ingombro inquadrato
    l'ultima volta, che solo inquadra() scrive, e ne e' una copia: tenuto come
    riferimento allo stesso Vector3 di orbita.centro, il pan lo sposterebbe
    insieme e la memoria direbbe sempre «siamo li'».

    Sul testo per la stessa ragione del controllo qui sopra — la guardia vive
    nella chiusura — e ognuna delle tre asserzioni e' stata provata contro la
    mutazione che deve prendere.
    """
    testo = _senza_commenti(_modulo())
    assert testo.count("orbita.centro.addScaledVector(") == 2, (
        "il pan non sposta piu' il centro dell'orbita lungo i due assi della "
        "camera: mezzo pan e' un pan che non raggiunge lo spigolo, e nessun pan "
        "toglie il caso che questa guardia sorveglia"
    )
    assert "fuoriDallaVista(centro.toArray(), centroInquadrato.toArray()" in testo, (
        "la guardia non misura dall'ultimo ingombro inquadrato"
    )
    assert "fuoriDallaVista(centro.toArray(), orbita.centro.toArray()" not in testo, (
        "la guardia misura da orbita.centro, che il pan sposta: zoomato su un "
        "dettaglio e traslato lungo il muro, il passaggio di step riazzera la vista"
    )
