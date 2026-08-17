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

    Si conta invece di cercare: dopo la modifica `inquadra();` compare due
    volte, ed entrambe dentro inquadraSeServe. Una terza e' una delle due
    strade che e' tornata ad azzerare.
    """
    testo = _senza_commenti(_modulo())
    assert testo.count("inquadraSeServe();") == 2, (
        "le due strade che disegnano devono passare dalla guardia"
    )
    assert testo.count("inquadra();") == 2, (
        "inquadra() e' chiamata da qualcuno oltre a inquadraSeServe: "
        "la camera torna ad azzerarsi a ogni step"
    )


def test_la_guardia_e_la_bandiera_sono_scritte_come_decidono():
    """La riga che risolve il difetto di Mario e' la bandiera, e vive dentro la
    chiusura di creaViewport: da fuori non si esegue senza costruire un
    three.js finto. Restava percio' scoperta, e i controlli qui sopra erano
    verdi anche togliendo la bandiera, capovolgendo la guardia o capovolgendo
    la condizione della prima inquadratura — mutato il sorgente e rigirato il
    banco, non dedotto.

    Le quattro asserzioni qui sono sul testo, che e' il modo debole: si
    accettano solo perche' ognuna e' stata provata contro la mutazione che deve
    prendere. Una quinta scritta senza quella prova non varrebbe niente.
    """
    testo = _senza_commenti(_modulo())
    assert "inquadrataAlmenoUnaVolta = true;" in testo, (
        "inquadra() non alza la bandiera: la prima inquadratura non finisce mai "
        "e ogni step torna a reinquadrare, che e' il difetto per intero"
    )
    assert "if (!inquadrataAlmenoUnaVolta) {" in testo, (
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
