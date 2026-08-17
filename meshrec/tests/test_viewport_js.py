"""Il modulo della vista dalla parte del browser: le decisioni pure, eseguite.

`ui/viewport.js` non e' importabile da qui, e le sue funzioni interne stanno
dentro la chiusura di creaViewport, che `node` non puo' aprire senza un
three.js finto. Percio' le decisioni che questa fase aggiunge sono funzioni
pure di primo livello: si estraggono dal sorgente e si eseguono davvero,
esattamente come tests/test_app_js.py fa con le funzioni di app.js.

Un controllo che cerca una sottostringa nel sorgente passa anche quando la
logica e' capovolta, e su questo ramo e' gia' successo (vedi il docstring di
tests/test_app_js.py). Qui la logica pura si esegue.

E non solo quella: due pezzi che stanno dentro la chiusura — la tabella dei
tasti e `trasla` — toccano di three.js quattro cose sole, e si estraggono e si
eseguono con quattro finte (_ascoltatore, _corpo_di). Erano il caso peggiore
della fase: `passo(evento.shiftKey)` scritto `passo()` uccide il pan da tastiera
per intero e lascia intatti tutti i conteggi che se ne dichiaravano
responsabili.

Sul testo restano le sole asserzioni su cio' che nemmeno cosi' si esegue: chi
chiama chi, la bandiera della prima inquadratura, e le materie del velo. Sono
l'eccezione, e ognuna e' stata provata mutando il sorgente e rigirando il banco
— un'asserzione sul testo scritta senza quella prova sorveglia una riga che
potrebbe non esserci. Una negativa sussunta dalla positiva che la precede non
e' un'asserzione provata: e' una riga che non salta mai, e qui non ce ne sono
piu'.

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


def _costante(nome: str) -> str:
    """La riga vera di un `const`, presa dal modulo e non ricopiata qui: il
    valore ricopiato diverge in silenzio e lascia il banco verde su un numero
    che il codice non ha piu'."""
    trovato = re.search(rf"^\s*const {nome} = .*;$", _modulo(), flags=re.MULTILINE)
    assert trovato is not None, f"{nome} non e' un const del modulo"
    return trovato.group(0).strip()


def _ascoltatore(tipo: str) -> str:
    """Il gestore di un evento della tela, dalla chiamata ad addEventListener
    alla sua chiusura. Vive dentro creaViewport e da fuori non si esegue senza
    un three.js finto: quel che serve a eseguirlo e' una `tela` che raccolga il
    gestore, ed e' il banco a darla."""
    testo = _modulo()
    apertura = f'tela.addEventListener("{tipo}", (evento) => {{'
    assert apertura in testo, f"la tela non ascolta piu' {tipo}"
    return apertura + testo.split(apertura, 1)[1].split("\n  });", 1)[0] + "\n  });"


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

    Le quattro asserzioni qui sono sul testo, che e' il modo debole: si
    accettano solo perche' ognuna e' stata provata contro la mutazione che deve
    prendere. Una quinta scritta senza quella prova non varrebbe niente.

    La negativa che stava qui — `if (!fuoriDallaVista(` assente — era una di
    quelle: capovolta la guardia, la positiva qui sopra salta per prima, perche'
    il punto di chiamata e' uno solo e la sua forma cambia. Costo zero tenerla,
    valore zero, e faceva dire a questo docstring una cosa che non era vera.
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


def test_il_viewport_restituisce_ogni_comando_che_l_interfaccia_gli_chiede():
    """La cucitura fra le due meta', ed e' il punto che nessuno dei due banchi
    guardava: qui si prova che una funzione esiste e che svuota() la nomina, di
    la' `vista` e' una finta che quel metodo ce l'ha per costruzione. Tolto un
    nome dal letterale di ritorno — `togliFantasma,` o `inquadra,` — tutti e due
    i banchi restano verdi e spegnere la casella lancia TypeError al primo clic:
    provato.

    Derivato e non elencato a mano: un elenco scritto qui diventa la copia di un
    fatto che sta in un altro file, e il giorno che l'interfaccia chiede un
    comando nuovo la copia tace.
    """
    testo = _senza_commenti(_modulo())
    assert "\n  return {\n" in testo, (
        "creaViewport non restituisce piu' un oggetto letterale: la cucitura si "
        "guarda altrove"
    )
    letterale = testo.split("\n  return {\n", 1)[1].split("\n  };", 1)[0]
    offerti = set(re.findall(r"^    (\w+)[,(]", letterale, flags=re.MULTILINE))
    app = "\n".join(
        r for r in (UI_DIR / "app.js").read_text(encoding="utf-8").splitlines()
        if not r.lstrip().startswith("//")
    )
    chiesti = set(re.findall(r"\bvista\.(\w+)\(", app))
    assert chiesti, "nessuna chiamata a `vista` in app.js: il banco non guarda piu' niente"
    assert chiesti <= offerti, (
        f"l'interfaccia chiama comandi che il viewport non restituisce, e il "
        f"primo clic che ci arriva lancia TypeError: {sorted(chiesti - offerti)}"
    )


def test_lo_spostamento_si_misura_sull_altezza_della_tela_e_sugli_assi_di_adesso(tmp_path):
    """`trasla` vive nella chiusura, ma di three.js tocca quattro cose sole —
    la matrice della camera, i tre assi e il centro dell'orbita — e con quattro
    finte si esegue. Fuori dall'esecuzione restavano scoperte due righe che
    nessun conteggio vede.

    L'altezza della tela e non la larghezza: la scala e' millimetri per pixel
    verticale, ed e' cio' che fa restare sotto il dito il punto che ci stava. Su
    una tela larga il doppio, misurata sulla larghezza, il gesto varrebbe la
    meta'.

    E la matrice del mondo aggiornata prima di leggerla: `lookAt` scrive il
    quaternione, ma la matrice three.js la ricalcola al disegno. Senza quella
    riga si leggerebbero gli assi del fotogramma precedente — qui, al primo
    gesto, tre vettori nulli, cioe' un pan che non sposta niente.
    """
    _esegui(tmp_path, _INTESTAZIONE + _funzioni("scalaDelloSpostamento") + """
const tela = { clientHeight: 600, clientWidth: 1200 };
class Vettore {
  constructor() { this.x = 0; this.y = 0; this.z = 0; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  addScaledVector(v, s) {
    this.x += v.x * s; this.y += v.y * s; this.z += v.z * s; return this;
  }
}
const destra = new Vettore();
const alto = new Vettore();
const avanti = new Vettore();
let matrici = 0;
const camera = {
  fov: 50,
  updateMatrixWorld() { matrici += 1; },
  matrixWorld: {
    // Prima dell'aggiornamento la matrice e' quella del fotogramma precedente:
    // qui, al primo gesto, non ha ancora nessun asse.
    extractBasis(d, a, av) {
      if (matrici === 0) { d.set(0, 0, 0); a.set(0, 0, 0); av.set(0, 0, 0); return; }
      d.set(1, 0, 0); a.set(0, 1, 0); av.set(0, 0, 1);
    },
  },
};
const orbita = { raggio: 1000, centro: new Vettore() };
""" + "function trasla(dx, dy) {" + _corpo_di(r"function trasla\(dx, dy\) \{") + "\n}\n" + """
// Un trascinamento lungo tutta la tela sposta la vista di tutta l'altezza
// visibile a quella distanza.
const altezzaVisibile = 2 * 1000 * Math.tan((25 * Math.PI) / 180);

trasla(tela.clientHeight, 0);
assert.equal(matrici, 1,
  "trasla legge gli assi senza aggiornare la matrice del mondo: sono quelli del fotogramma prima");
assert.ok(Math.abs(orbita.centro.x + altezzaVisibile) < 1e-9,
  `il trascinamento di tutta la tela non sposta di tutta l'altezza visibile, `
  + `o la misura e' presa sulla larghezza: ${orbita.centro.x}, attesa ${-altezzaVisibile}`);
assert.equal(orbita.centro.y, 0, "il trascinamento orizzontale ha spostato anche in verticale");

orbita.centro.x = 0;
trasla(0, tela.clientHeight);
assert.ok(Math.abs(orbita.centro.y - altezzaVisibile) < 1e-9,
  `il trascinamento verticale non segue il dito: ${orbita.centro.y}, attesa ${altezzaVisibile}`);
assert.equal(orbita.centro.x, 0, "il trascinamento verticale ha spostato anche in orizzontale");
""")


def _banco_della_tastiera() -> str:
    """La tabella dei tasti, eseguita. Il gestore tocca solo `orbita`, `trasla`,
    `inquadra` e `aggiornaCamera`: nessuno dei quattro ha bisogno di three.js, e
    con quattro finti la tabella si interroga davvero invece di leggerla."""
    return _INTESTAZIONE + """
const gestori = {};
const tela = { addEventListener(tipo, gestore) { gestori[tipo] = gestore; } };
const orbita = { theta: 0, phi: 1, raggio: 100 };
const traslate = [];
function trasla(dx, dy) { traslate.push([dx, dy]); }
let inquadrature = 0;
function inquadra() { inquadrature += 1; }
let camere = 0;
function aggiornaCamera() { camere += 1; }
let impediti = 0;
const premi = (key, shiftKey = false) =>
  gestori.keydown({ key, shiftKey, preventDefault() { impediti += 1; } });
""" + _costante("PASSO_TASTIERA") + "\n" + _ascoltatore("keydown")


def test_le_frecce_con_maiusc_spostano_la_vista_e_senza_maiusc_la_ruotano(tmp_path):
    """Il pan da tastiera, eseguito: e' la meta' del comando per chi non usa il
    mouse, cioe' il difetto che questa fase dichiara di chiudere.

    Contarlo non basta. Il gestore passa `evento.shiftKey` alla voce della
    tabella, e togliendo quell'argomento le quattro voci restano scritte, le
    cinque chiamate a `trasla(` restano cinque e `evento.shiftKey` resta nel
    modulo per via del trascinamento: il pan da tastiera sparisce per intero e
    ogni controllo testuale resta verde — provato. Qui la tabella si interroga.
    """
    _esegui(tmp_path, _banco_della_tastiera() + """
premi("ArrowLeft", true);
assert.deepEqual(traslate, [[PASSO_TASTIERA, 0]],
  `maiusc con la freccia sinistra non sposta la vista: ${JSON.stringify(traslate)}`);
assert.equal(orbita.theta, 0, "maiusc con la freccia sinistra ruota invece di spostare");

premi("ArrowRight", true);
premi("ArrowUp", true);
premi("ArrowDown", true);
assert.deepEqual(traslate, [
  [PASSO_TASTIERA, 0], [-PASSO_TASTIERA, 0], [0, PASSO_TASTIERA], [0, -PASSO_TASTIERA],
], `le quattro frecce con maiusc non spostano la vista: ${JSON.stringify(traslate)}`);
assert.equal(orbita.theta, 0, "una freccia con maiusc ha ruotato");
assert.equal(orbita.phi, 1, "una freccia con maiusc ha ruotato");

// E senza maiusc le stesse frecce ruotano e non spostano: il verso opposto del
// medesimo argomento, che una voce sempre in traslazione lascerebbe passare.
traslate.length = 0;
premi("ArrowLeft");
assert.deepEqual(traslate, [], "la freccia sola sposta la vista invece di ruotare");
assert.ok(orbita.theta < 0, "la freccia sinistra sola non ruota");
premi("ArrowUp");
assert.ok(orbita.phi < 1, "la freccia in su' sola non ruota");

// Lo zoom e l'inquadratura non guardano maiusc, e con una tabella sola
// continuano a funzionare quando lo si tiene premuto: su una tastiera americana
// «+» E' maiusc piu' «=».
const raggio = orbita.raggio;
premi("+", true);
assert.ok(orbita.raggio < raggio, "lo zoom smette di funzionare con maiusc premuto");
premi("-");
premi("f");
assert.equal(inquadrature, 1, "il tasto f non riporta la vista sulla geometria");

// Ogni tasto della tabella ha impedito lo scorrimento della pagina, e i tasti
// che la tabella non conosce escono prima senza toccare la camera.
assert.equal(impediti, 9, `un tasto della tabella non impedisce lo scorrimento: ${impediti}`);
assert.equal(camere, 9, `un tasto della tabella non aggiorna la camera: ${camere}`);
premi("q");
assert.equal(camere, 9, "un tasto che la tabella non conosce muove la camera lo stesso");
""")


def _voce_da_tastiera(chiave: str) -> str:
    """Il corpo di una voce della tabella dei tasti. Dentro non ci sono graffe,
    quindi la prima chiude la voce.

    Il nome del parametro non fa parte di cio' che si sorveglia: fissato a
    `maiusc`, questo controllo saltava rinominandolo, cioe' su una
    rifattorizzazione che non cambia niente di cio' che decide.
    """
    trovato = re.search(
        rf"{re.escape(chiave)}:\s*\(\s*\w*\s*\)\s*=>\s*\{{([^}}]*)\}}",
        _senza_commenti(_modulo()),
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
    nella chiusura — e ognuna delle due asserzioni e' stata provata contro la
    mutazione che deve prendere. La terza che stava qui — la guardia che misura
    da orbita.centro, dichiarata assente — non provava niente: quella mutazione
    toglie la forma che la positiva qui sotto cerca, e la positiva salta prima.
    """
    testo = _senza_commenti(_modulo())
    assert testo.count("orbita.centro.addScaledVector(") == 2, (
        "il pan non sposta piu' il centro dell'orbita lungo i due assi della "
        "camera: mezzo pan e' un pan che non raggiunge lo spigolo, e nessun pan "
        "toglie il caso che questa guardia sorveglia"
    )
    assert "fuoriDallaVista(centro.toArray(), centroInquadrato.toArray()" in testo, (
        "la guardia non misura dall'ultimo ingombro inquadrato: misurata da "
        "orbita.centro, che il pan sposta, zoomato su un dettaglio e traslato "
        "lungo il muro il passaggio di step riazzera la vista"
    )


# --------------------------------------------------------------------------
# Il fantasma: il passaggio precedente disegnato insieme a quello corrente.
# Vive tutto dentro la chiusura di creaViewport e tocca THREE a ogni riga,
# quindi da qui non si esegue: le asserzioni sono sul testo, che e' il modo
# debole, e ognuna e' stata provata contro la mutazione che deve prendere —
# fantasma figlio di `gruppo`, togliFantasma che non toglie, la visibilita'
# capovolta sotto il confronto, l'opacita' e il token cambiati.
# --------------------------------------------------------------------------


def _corpo_di(intestazione: str, chiusura: str = "\n  }") -> str:
    """Il corpo di una funzione o di un metodo della chiusura, che non chiude
    in prima colonna e quindi `_sorgente_di` non vede.

    L'intestazione e' un'espressione regolare e non un letterale: scritta a
    lettere, fissava anche gli spazi intorno all'`=` di un valore predefinito, e
    riscrivere `facce = null` come `facce=null` — che non cambia niente di cio'
    che questi controlli sorvegliano — li faceva saltare tutti insieme.
    """
    testo = _senza_commenti(_modulo())
    trovato = re.search(intestazione, testo)
    assert trovato is not None, f"{intestazione} non e' piu' nel modulo"
    return testo[trovato.end():].split(chiusura, 1)[0]


def _corpo_del_fantasma() -> str:
    """Il corpo di mostraFantasma, dove stanno i due materiali del velo."""
    return _corpo_di(r"mostraFantasma\(vertici, facce\s*=\s*null\) \{", "\n    }")


def test_il_fantasma_nasce_fratello_del_gruppo_e_non_figlio():
    """Da figlio di `gruppo` il fantasma finirebbe nel precedente, perche'
    svuota() sposta i figli di `gruppo` invece di distruggerli: ricomparirebbe
    premendo «Confronta», sovrapposto alla geometria di prima, cioe' tre
    geometrie a video mentre la didascalia ne nomina una. E finirebbe anche
    dentro scatolaDelGruppo(), che percorre i figli di `gruppo`: il cursore del
    taglio si tarerebbe sull'unione di due step.
    """
    testo = _senza_commenti(_modulo())
    assert "scena.add(fantasma);" in testo, (
        "il fantasma non entra nella scena accanto a `gruppo`: da figlio di "
        "`gruppo` svuota() lo sposta nel precedente e «Confronta» lo rimette a "
        "video sopra la geometria di prima"
    )


def test_il_fantasma_se_ne_va_col_passaggio_che_lo_ha_prodotto():
    """togliFantasma libera davvero, per la ragione scritta sopra
    liberaIlPrecedente(): togliere un oggetto dalla scena non cancella i suoi
    buffer, sono gli eventi di dispose a farlo. E si chiama in testa a svuota():
    ogni strada che disegna chiama svuota() due volte, e in coda la seconda
    lascerebbe il fantasma sotto la geometria nuova.
    """
    corpo = _corpo_di(r"function togliFantasma\(\) \{")
    for pezzo in ("geometry.dispose()", "material.dispose()", "scena.remove(fantasma)"):
        assert pezzo in corpo, f"togliFantasma non fa {pezzo}: {corpo}"
    assert "fantasma = null" in corpo, (
        f"togliFantasma non azzera il riferimento: il prossimo disegno lo perde "
        f"sulla scheda invece di sostituirlo: {corpo}"
    )
    svuota = _corpo_di(r"svuota\(\) \{", "\n    }")
    assert "togliFantasma();" in svuota, (
        "svuota() lascia in scena il fantasma del passaggio che si sta lasciando"
    )
    mostra = _corpo_del_fantasma()
    assert "togliFantasma();" in mostra, (
        "mostraFantasma non toglie quello di prima: il vecchio resta in scena e "
        "nessun riferimento lo raggiunge piu'"
    )


def test_il_fantasma_sparisce_sotto_il_confronto_e_torna_quando_si_spegne():
    """Le due risposte alla stessa domanda occupano lo stesso pixel. Il
    confronto scambia i due gruppi; il fantasma e' il precedente di cio' che sta
    in `gruppo`, non di cio' che sta in `precedente`, quindi lasciato acceso
    sopra il confronto metterebbe a video tre geometrie mentre l'etichetta ne
    nomina una. Nascosto e non distrutto: spegnendo il confronto la vista torna
    esattamente quella di prima, senza riscaricare niente."""
    testo = _senza_commenti(_modulo())
    assert "fantasma.visible = !attivo;" in testo, (
        "il fantasma non segue il confronto: acceso sopra il precedente sono tre "
        "geometrie a video e una sola nominata, e capovolto sparisce proprio "
        "quando serve"
    )


def test_il_fantasma_si_lascia_attraversare_e_prende_la_tinta_dal_foglio():
    """Deve stare dietro senza occludere: `transparent` con `depthWrite: false`,
    altrimenti il buffer di profondita' lo tratta come un solido e la geometria
    corrente sparisce dietro un velo. L'opacita' e' quella della spec (§ 6) e non
    un valore qualunque: piu' alta compete con cio' che sta davanti, piu' bassa
    non si vede sulla carta del report.

    Il colore dal foglio come tutti gli altri della scena: un esadecimale qui
    sarebbe un colore che nessun controllo raggiunge (tests/test_stile.py).
    """
    corpo = _corpo_del_fantasma()
    assert 'tinta("--fantasma")' in corpo, "il fantasma non prende il colore dal foglio"
    # Il valore intero e non il suo prefisso: `0.150` conteneva `0.15` e passava
    # questo conteggio, cioe' il numero della spec si poteva cambiare restando
    # verdi. Il confine dopo il 5 chiude quella strada.
    assert len(re.findall(r"opacity: 0\.15\b", corpo)) == 2, (
        f"le due materie del fantasma — nuvola e superficie — non hanno "
        f"entrambe l'opacita' della spec: {corpo}"
    )
    assert corpo.count("depthWrite: false") == 2, (
        f"il fantasma occlude cio' che sta davanti invece di lasciarsi "
        f"attraversare: {corpo}"
    )
    # `opacity` senza `transparent` three.js la ignora: il velo tornerebbe
    # opaco al 100% e coprirebbe la geometria che sta dietro, che e' cio' che
    # queste due righe esistono per evitare. Il conteggio di `opacity` da solo
    # non lo vede.
    assert corpo.count("transparent: true") == 2, (
        f"una delle due materie del fantasma non e' trasparente, e li' l'opacita' "
        f"e' un numero che three.js non guarda: {corpo}"
    )


def test_il_velo_e_materia_della_stessa_scena_della_geometria():
    """Due righe che nessun conteggio del velo guardava, e sono cio' che lo tiene
    dentro la scena invece che sopra.

    Il piano di taglio: l'elenco e' uno solo e condiviso, e una materia che non
    lo riceve nasce senza taglio. Il velo mostrerebbe la geometria che il taglio
    ha appena tolto, cioe' la vista che contraddice il proprio comando — sullo
    step 9 il taglio serve proprio a guardare dentro.

    E le normali: senza, `MeshStandardMaterial` non ha da che parte sta la
    superficie e il velo esce piatto e nero, che dietro la geometria corrente
    non e' un velo, e' una macchia.
    """
    corpo = _corpo_del_fantasma()
    assert corpo.count("clippingPlanes: pianiTaglio,") == 2, (
        f"una delle due materie del fantasma ignora il piano di taglio, e mostra "
        f"la geometria che il taglio ha tolto: {corpo}"
    )
    assert "computeVertexNormals();" in corpo, (
        f"il velo di una superficie non ha normali: esce piatto e nero invece che "
        f"illuminato come la geometria che sta dietro: {corpo}"
    )
