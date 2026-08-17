"""L'interfaccia dalla parte del browser: le funzioni vere di `app.js`, eseguite.

Due famiglie di controlli, e la seconda esiste per il limite della prima.

**Le mosse.** Lo stesso difetto — l'annuncio del rifiuto non garantito — e'
tornato tre volte per tre strade diverse: `hidden` sulla regione `role="alert"`,
una regola di stile che la nascondeva, e `replaceChildren()` su `#dettaglio` che
la distruggeva a ogni apertura di pannello. La quarta strada e' sempre la stessa
mossa: rimettere la regione sotto qualcosa che la puo' distruggere o generare.
Quei controlli guardano la mossa, non il sintomo.

**Il comportamento.** Un controllo che cerca una sottostringa nel sorgente passa
anche quando la logica e' capovolta, e su questo ramo e' successo: una guardia
resa inerte con `|| true` lasciava la sottostringa al suo posto e il controllo
restava verde mentre il difetto era riaperto. Percio' tutto cio' che e' logica —
il marchio dello step, il tetto del registro, il valore che dai tasti finisce
nella configurazione, la didascalia del ritaglio — si prova **eseguendo le
funzioni vere ritagliate da `app.js`** su un DOM finto, con `node`. Il DOM finto
non e' un browser: e' il minimo che quelle funzioni toccano, e sta qui sotto.

Non stanno in `tests/test_server.py` per la stessa ragione per cui non ci sta
`test_stile.py`: quel file e' in mano ad altri, e metterlo nell'indice
porterebbe nel commit righe che non sono mie.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meshrec.app.server import UI_DIR, create_app
from meshrec.core.config import InputConfig, PipelineConfig, save_config


def _markup() -> str:
    return (UI_DIR / "index.html").read_text(encoding="utf-8")


def _modulo() -> str:
    return (UI_DIR / "app.js").read_text(encoding="utf-8")


def _foglio() -> str:
    return (UI_DIR / "stile.css").read_text(encoding="utf-8")


def _senza_commenti_html(markup: str) -> str:
    """Il markup senza i commenti. Un commento che nomina un attributo non e'
    quell'attributo: schermato dietro `<!-- id="errore" role="alert" -->` scritto
    sopra la regione vera, il primo controllo di questo file restava verde
    mentre la regione perdeva il proprio ruolo. Provato, era verde davvero."""
    return re.sub(r"<!--.*?-->", "", markup, flags=re.DOTALL)


def _senza_commenti_js(modulo: str) -> str:
    """Il modulo senza le righe di commento. Serve al contrario: `role="alert"`
    compare per iscritto nei commenti che spiegano perche' la regione sta dove
    sta, e cercare la forma di codice dentro la spiegazione la vieterebbe."""
    return "\n".join(r for r in modulo.splitlines() if not r.lstrip().startswith("//"))


def _elemento(markup: str, identificativo: str) -> str:
    """Il tag di apertura dell'elemento con quell'id, non la prima riga che ne
    contiene il nome."""
    trovato = re.search(rf"<[a-z]+[^>]*\bid=\"{identificativo}\"[^>]*>", markup)
    assert trovato is not None, f"nessun elemento con id={identificativo} nel markup"
    return trovato.group(0)


def _sorgente_di(nome: str, testo: str) -> str:
    """Il corpo di una funzione di primo livello, dalla firma alla graffa che la
    chiude in prima colonna. I moduli dell'interfaccia non sono importabili da
    qui (importano percorsi serviti dal server), quindi si estrae il testo.

    `async` va tenuto: senza, il testo estratto resta leggibile ma non e' piu'
    eseguibile.
    """
    corpo = testo.split(f"function {nome}(", 1)[1]
    prefisso = "async " if f"async function {nome}(" in testo else ""
    return f"{prefisso}function {nome}(" + corpo.split("\n}\n", 1)[0] + "\n}"


def _funzioni(*nomi: str) -> str:
    testo = _modulo()
    return "\n".join(_sorgente_di(nome, testo) for nome in nomi)


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


# Il minimo di DOM che le funzioni vere toccano: nodi, figli, classi, attributi,
# dataset, e le due proprieta' di scorrimento del registro. Non e' un browser e
# non pretende di esserlo — quello che si sta provando e' la logica del modulo,
# non il motore che ci sta sotto.
_DOM = """import assert from 'node:assert/strict';

class Elemento {
  constructor(tag) {
    this.tag = tag;
    this.figli = [];
    this.className = "";
    this.dataset = {};
    this.attributi = {};
    this.testo = "";
    this.scrollTop = 0;
    // Non legata a figli.length: in un browser vero e' l'altezza visibile in
    // pixel del contenitore, indipendente da quanto contenuto ci sta dentro.
    // Se il banco la lega al conteggio dei figli, scrollHeight e clientHeight
    // coincidono sempre e "in fondo" e' vero per costruzione — niente prova
    // piu' nulla sul ramo che condiziona lo scorrimento.
    this.clientHeight = 0;
    this.padre = null;
    this.gestori = {};
    this.classList = {
      toggle: (nome, attivo) => {
        const classi = new Set(this.className.split(" ").filter(Boolean));
        if (attivo) classi.add(nome); else classi.delete(nome);
        this.className = [...classi].join(" ");
      },
      // Il confronto la legge per sapere se la didascalia che sta fotografando
      // era distesa al centro (nessuna geometria) o nell'angolo (didascalia di
      // una geometria): senza, il banco non potrebbe provare che il ritorno
      // rimette la riga dov'era.
      contains: (nome) => this.className.split(" ").includes(nome),
    };
  }
  addEventListener(tipo, gestore) { (this.gestori[tipo] ??= []).push(gestore); }
  // Il gestore vero, eseguito: e' cio' che mancava al banco. `await` perche' il
  // gestore del campo e' asincrono, e senza aspettarlo il controllo guarderebbe
  // lo stato di prima della risposta.
  async scatena(tipo) { for (const gestore of this.gestori[tipo] ?? []) await gestore(); }
  get children() { return this.figli; }
  get childElementCount() { return this.figli.length; }
  get firstElementChild() { return this.figli[0] ?? null; }
  get lastElementChild() { return this.figli[this.figli.length - 1] ?? null; }
  get scrollHeight() { return this.figli.length; }
  get textContent() { return this.testo; }
  set textContent(valore) { this.testo = String(valore); }
  append(...nodi) { for (const nodo of nodi) { nodo.padre = this; this.figli.push(nodo); } }
  replaceChildren(...nodi) { this.figli = []; this.append(...nodi); }
  remove() { this.padre.figli.splice(this.padre.figli.indexOf(this), 1); }
  setAttribute(nome, valore) { this.attributi[nome] = String(valore); }
  removeAttribute(nome) { delete this.attributi[nome]; }
  getAttribute(nome) { return this.attributi[nome] ?? null; }
  discendenti() { return this.figli.flatMap((f) => [f, ...f.discendenti()]); }
  querySelectorAll(selettore) {
    const classe = selettore.slice(1);
    return this.discendenti().filter((e) => e.className.split(" ").includes(classe));
  }
}

const radice = new Elemento("body");
const perId = new Map();
const document = {
  createElement: (tag) => new Elemento(tag),
  getElementById(id) {
    if (!perId.has(id)) {
      const nodo = new Elemento("div");
      radice.append(nodo);
      perId.set(id, nodo);
    }
    return perId.get(id);
  },
  querySelectorAll: (selettore) => radice.querySelectorAll(selettore),
};

const ETICHETTE = {};
const rigaErrore = document.getElementById("errore");
let stepAperto = null;
// Le due variabili di modulo che le funzioni estratte leggono e scrivono:
// senza, il banco proverebbe una copia che non e' quella del modulo.
let configurazione = null;
let generazione = 0;
const elenco = document.getElementById("elenco-step");
const STEPS = [
  { numero: 1, chiave: "01_load", stato: "valido" },
  { numero: 2, chiave: "02_segment", stato: "in corso" },
  { numero: 3, chiave: "03_downsample", stato: "mai eseguito" },
];
const marcati = () =>
  document.querySelectorAll(".step")
    .filter((c) => c.getAttribute("aria-current") === "true")
    .map((c) => Number(c.dataset.numero));
"""


# --------------------------------------------------------------------------
# La regione role="alert": la mossa, non il sintomo.
# --------------------------------------------------------------------------


def test_la_regione_d_errore_esiste_nel_markup_e_non_nasce_nascosta():
    """Strada 1. Nel markup e non creata da codice: deve preesistere a cio' che
    annuncia. E senza `hidden`, che la toglierebbe dall'albero."""
    elemento = _elemento(_senza_commenti_html(_markup()), "errore")
    assert 'role="alert"' in elemento, f"la regione ha perso il proprio ruolo: {elemento}"
    assert "hidden" not in elemento, f"hidden la toglie dall'albero: {elemento}"


def test_la_regione_d_errore_sta_fuori_da_cio_che_viene_riscritto():
    """Strada 3. `#dettaglio` viene svuotato con replaceChildren() a ogni
    apertura di pannello: la regione dentro di li' non sopravvive a un clic."""
    markup = _senza_commenti_html(_markup())
    assert markup.index('id="errore"') < markup.index('id="dettaglio"'), (
        "la regione e' finita dentro il pannello che viene riscritto"
    )
    dentro = markup.split('<div id="dettaglio"', 1)[1]
    assert 'id="errore"' not in dentro, "la regione e' finita dentro #dettaglio"


def test_il_modulo_scrive_nella_regione_invece_di_fabbricarne_una():
    """La quarta strada. Un ramo che si crea la propria regione `role="alert"`
    riapre il difetto con l'aria di risolverlo: il codice sembra piu' completo,
    e l'annuncio smette di essere garantito.

    Si guarda la **forma di codice** e non la stringa — `role="alert"` compare
    per iscritto nei commenti, e vietare la stringa vieterebbe la spiegazione —
    ma tutte le forme, non una sola grafia: `setAttribute` con gli apici in
    entrambi i versi e con qualunque spaziatura, la proprieta' riflessa
    `.role =` (Chrome 119+), e `Object.assign(p, { role: … })`. Le tre che
    mancavano erano verdi, ed erano equivalenti a quella sorvegliata.
    """
    modulo = _modulo()
    codice = _senza_commenti_js(modulo)
    assert 'getElementById("errore")' in modulo, "il modulo non e' piu' agganciato alla regione"
    forme = re.findall(
        r"""setAttribute\(\s*["']role["']|\.role\s*=|\brole\s*:""", codice
    )
    assert forme == [], f"un ramo fabbrica di nuovo la propria regione role=alert: {forme}"


# --------------------------------------------------------------------------
# L'elenco degli step: comando, aggiornamento sul posto, marchio.
# --------------------------------------------------------------------------


def test_ogni_step_e_un_comando_e_non_una_riga_cliccabile():
    """Undici `li` con un gestore di click erano l'intera interfaccia
    pilotabile col solo mouse (WCAG 2.1.1, livello A). Il rischio della
    ricaduta e' concreto: il `li` torna comodo appena qualcuno vuole
    aggiungerci sopra un'altra riga."""
    riga = _modulo().split("function nuovaRiga(", 1)[1].split("\n}\n", 1)[0]
    assert 'createElement("button")' in riga, "lo step e' tornato una riga senza ruolo"
    assert 'comando.type = "button"' in riga, "senza type, dentro un form il bottone invia"
    assert 'className = "step"' in riga, "il foglio si aggancia a .step: il nome non cambia"


def test_l_elenco_degli_step_si_aggiorna_e_non_si_ricostruisce(tmp_path):
    """Il difetto e' nato dalla correzione che lo precede.

    Finche' gli step erano `li` inerti, riscrivere l'elenco a ogni evento non
    costava niente. Reso ciascuno un `<button>`, la stessa riscrittura — due
    volte al secondo mentre la pipeline gira — distrugge l'elemento che ha il
    fuoco una sessantina di volte durante uno step da 34 secondi.

    Provato **eseguendo** `disegnaStep` due volte e guardando l'identita' dei
    nodi, non la guardia per iscritto: la guardia resa inerte con `|| true`
    lascia la sottostringa al suo posto, ricostruisce l'elenco a ogni evento, e
    un controllo testuale resta verde. Questo diventa rosso.
    """
    _esegui(tmp_path, _DOM + "let ultimiSteps = [];\n" + _funzioni("segnaStepAperto", "nuovaRiga", "disegnaStep") + """
disegnaStep(STEPS);
const prima = elenco.children.map((riga) => riga.firstElementChild);
assert.equal(prima.length, 3, "l'elenco non viene piu' costruito");
assert.deepEqual(prima.map((c) => c.className), ["step", "step", "step"]);
disegnaStep(STEPS.map((voce) => ({ ...voce, stato: "fallito" })));
const dopo = elenco.children.map((riga) => riga.firstElementChild);
assert.deepEqual(
  prima.map((c, i) => c === dopo[i]), [true, true, true],
  "l'elenco si ricostruisce a ogni evento: il fuoco da tastiera non sopravvive",
);
assert.deepEqual(
  elenco.children.map((riga) => riga.className),
  ["stato-fallito", "stato-fallito", "stato-fallito"],
  "lo stato non arriva piu' alla riga",
);
disegnaStep([...STEPS, { numero: 4, chiave: "04_normals", stato: "valido" }]);
assert.equal(elenco.childElementCount, 4, "cambiata la lunghezza, l'elenco non la segue");
""")


def test_solo_la_riga_che_ha_cambiato_stato_porta_il_segnale(tmp_path):
    """L'elenco dice quale stato ogni riga porta e non quale riga sia appena
    diventata quello: e' l'informazione che sta nella differenza fra due frame,
    e sono undici righe. Serve a chi guarda altrove — la vista, il registro, o
    la colonna dei parametri, dove una modifica manda «non valido» uno step
    nell'altra colonna.

    Le tre proprieta' si rompono tutte in silenzio, e ognuna trasforma il
    segnale nel suo contrario:

    1. la prima passata non segnala niente (a corsa aperta ultimiSteps e' vuoto,
       e undici righe che si accendono insieme non indicano nessuna riga);
    2. segnala **solo** la riga cambiata, non tutte quelle riscritte;
    3. un elenco che si allunga non segnala le righe che c'erano gia', ne' quella
       nuova, che non ha uno stato di prima da cui differire.
    """
    _esegui(tmp_path, _DOM + "let ultimiSteps = [];\n" + _funzioni("segnaStepAperto", "nuovaRiga", "disegnaStep") + """
const segnalate = () =>
  elenco.children
    .map((riga, indice) => [indice, riga.getAttribute("data-cambiato")])
    .filter(([, segno]) => segno !== null)
    .map(([indice]) => indice);
const fallito = (numero) =>
  STEPS.map((voce) => (voce.numero === numero ? { ...voce, stato: "fallito" } : voce));

disegnaStep(STEPS);
assert.deepEqual(segnalate(), [],
  "la prima passata segnala tutte le righe: undici segnali insieme non indicano nessuna riga");

disegnaStep(fallito(2));
assert.deepEqual(segnalate(), [1],
  "il segnale non e' sulla sola riga cambiata: le altre due si sono riscritte, non cambiate");
assert.equal(elenco.children[1].className, "stato-fallito",
  "lo stato non arriva piu' alla riga, e il segnale ne indossa la tinta");

disegnaStep([...fallito(2), { numero: 4, chiave: "04_normals", stato: "valido" }]);
assert.deepEqual(segnalate(), [],
  "un elenco che si allunga segnala righe che non sono cambiate");
""")


def test_solo_lo_step_aperto_porta_il_marchio(tmp_path):
    """Correzione 2. Quale step e' aperto lo sapeva solo una variabile di
    modulo: a video non lo diceva niente, e chi non vede il fondo evidenziato
    non aveva **nessun** canale. `aria-current` e non una classe, perche' e'
    l'attributo che porta il significato e il foglio ci si aggancia sopra.

    Due proprieta', ed entrambe si rompono in silenzio: mai due marchi insieme
    (due «stai guardando questo» sono peggio di nessuno), e il marchio sparisce
    quando nessun pannello e' aperto.
    """
    _esegui(tmp_path, _DOM + "let ultimiSteps = [];\n" + _funzioni("segnaStepAperto", "nuovaRiga", "disegnaStep") + """
disegnaStep(STEPS);
segnaStepAperto(2);
assert.deepEqual(marcati(), [2], "il marchio non e' sullo step aperto, o non e' solo suo");
segnaStepAperto(3);
assert.deepEqual(marcati(), [3], "il marchio precedente resta: due step aperti insieme");
segnaStepAperto(null);
assert.deepEqual(marcati(), [], "nessun pannello aperto e il marchio resta appeso");
""")
    assert '.step[aria-current="true"]' in _foglio(), (
        "il foglio non si aggancia piu' ad aria-current: il marchio resta senza fondo"
    )


def test_il_marchio_non_resta_su_uno_step_che_nessun_pannello_mostra(tmp_path):
    """`apriDettaglio` ha due uscite d'errore, e nessuna delle due toccava il
    marchio: aperto lo step 3, cliccato il 5, `/api/config` che risponde 500, il
    pannello si svuotava, la riga d'errore parlava del 5, il viewport mostrava
    il 5 — e `aria-current` restava sul 3. L'unico canale che dice «stai
    guardando questo» nominava lo step sbagliato.
    """
    testo = _modulo()
    assert testo.count("fallisciDettaglio(dettaglio, ragione);") == 2, (
        "una delle due uscite d'errore di apriDettaglio non passa piu' di qui"
    )
    _esegui(tmp_path, _DOM + "let ultimiSteps = [];\n" + _funzioni(
        "segnaStepAperto", "nuovaRiga", "disegnaStep", "dichiaraErrore", "fallisciDettaglio",
    ) + """
const dettaglio = document.getElementById("dettaglio");
disegnaStep(STEPS);
stepAperto = 3;
segnaStepAperto(3);
dettaglio.append(document.createElement("p"));
fallisciDettaglio(dettaglio, "il server ha risposto 500");
assert.deepEqual(marcati(), [], "il marchio resta su uno step che nessun pannello mostra");
assert.equal(stepAperto, null, "a fine corsa si ricaricherebbe un pannello che non c'e'");
assert.equal(dettaglio.childElementCount, 0, "il pannello non e' stato svuotato");
assert.equal(rigaErrore.textContent, "il server ha risposto 500", "la ragione non e' a video");
""")


# --------------------------------------------------------------------------
# Il registro: tappa di tabulazione, non regione viva, e con un tetto.
# --------------------------------------------------------------------------


def test_il_registro_e_una_tappa_di_tabulazione():
    """Il registro e' alto 14rem, scorre, e dentro non c'e' niente su cui il
    fuoco possa posarsi: senza `tabindex` Chrome non lo rende raggiungibile da
    tastiera e le righe uscite dall'alto non si rileggono senza il mouse
    (WCAG 2.1.1, livello A). Firefox mette il fuoco sui contenitori che
    scorrono da se', Chrome no."""
    elemento = _elemento(_senza_commenti_html(_markup()), "registro")
    assert 'tabindex="0"' in elemento, f"il registro non e' piu' raggiungibile: {elemento}"


def test_il_registro_non_e_una_regione_viva():
    """`role="log"` porta con se' una regione viva, e qui dentro finisce tutto
    lo stdout del sottoprocesso: un lettore di schermo leggeva ad alta voce ogni
    riga di TetGen per i 34 secondi di uno step, coprendo l'unica cosa che va
    davvero sentita, il `role="alert"` della riga d'errore."""
    elemento = _elemento(_senza_commenti_html(_markup()), "registro")
    assert 'aria-live="off"' in elemento, (
        f"il registro torna a parlare sopra la riga d'errore: {elemento}"
    )


def test_il_registro_scarta_la_riga_piu_vecchia_e_mai_la_piu_recente(tmp_path):
    """Il registro cresceva senza tetto. Il tetto va provato **al confine** e
    sul verso: un `>=` al posto del `>` tiene una riga di meno, e togliere
    `firstElementChild` invece di quello butta via l'ultima arrivata, che e'
    l'unica che si sta guardando. Nessuna delle due si vede leggendo.
    """
    testo = _modulo()
    tetto = int(re.search(r"const RIGHE_DEL_REGISTRO = (\d+);", testo).group(1))
    corpo = testo.split('flusso.addEventListener("riga", (evento) => {', 1)[1]
    corpo = corpo.split("\n});", 1)[0]
    _esegui(tmp_path, _DOM + f"const RIGHE_DEL_REGISTRO = {tetto};\n"
            "function aggiungiRiga(evento) {" + corpo + "}\n" + f"""
const registro = document.getElementById("registro");
const scrivi = (n) => aggiungiRiga({{ data: JSON.stringify(`riga ${{n}}`) }});
for (let n = 1; n <= {tetto}; n += 1) scrivi(n);
assert.equal(registro.childElementCount, {tetto}, "il tetto taglia prima di esserci arrivato");
assert.equal(registro.firstElementChild.textContent, "riga 1", "ha buttato via una riga di troppo");
assert.equal(registro.lastElementChild.textContent, "riga {tetto}");
scrivi({tetto} + 1);
assert.equal(registro.childElementCount, {tetto}, "il tetto non tiene: il registro cresce ancora");
assert.equal(
  registro.firstElementChild.textContent, "riga 2",
  "non esce la piu' vecchia",
);
assert.equal(
  registro.lastElementChild.textContent, "riga {tetto + 1}",
  "esce la piu' recente, cioe' l'unica che si sta guardando",
);
""")


# --------------------------------------------------------------------------
# Il fuoco da tastiera si deve vedere.
# --------------------------------------------------------------------------


def test_il_fuoco_da_tastiera_si_vede_su_ogni_comando():
    """Chi naviga da tastiera senza un contorno di fuoco non sa dove si trova
    (WCAG 2.4.7). `:focus-visible` e non `:focus`, cosi' il contorno non compare
    al clic del mouse; e nessun `outline: none`, che e' il modo in cui questo
    difetto rientra di solito."""
    foglio = _foglio()
    for comando in (".bottone", ".step", ".registro", ".campo input"):
        assert f"{comando}:focus-visible" in foglio, (
            f"{comando} non mostra piu' dove si trova il fuoco"
        )
    regole = re.findall(r":focus-visible[^{]*\{([^}]*)\}", foglio)
    assert regole, "nessuna regola di fuoco nel foglio"
    for regola in regole:
        assert "outline" in regola and "outline: none" not in regola, (
            f"la regola di fuoco non disegna nulla: {regola}"
        )


# --------------------------------------------------------------------------
# Lo scanner strutturale: ogni gestore che scrive dopo un'attesa fetch si
# difende con un contatore fresco o un disable, non solo con `ordine`.
#
# La proprieta' e' generica, non di dominio: un `addEventListener` agganciato
# una volta puo' rifirare piu' volte (due clic, non un solo evento), e un
# contatore catturato nella chiusura esterna (`ordine` = la generazione del
# pannello) non si aggiorna fra un clic e l'altro. Applicato al file prima di
# questo giro lo scanner sotto avrebbe segnalato **entrambi** i bottoni che
# questo giro corregge — riga del ritaglio e righe dei due «Esegui» — insieme
# a `scriviParametro`, gia' corretto in un giro precedente: la quarta istanza
# senza che nessuno la trovasse leggendo a mano.
# --------------------------------------------------------------------------


_GESTORE_NOMINATO = re.compile(r"^\w+$")
_DELEGA_A_UNA_FUNZIONE = re.compile(r"^\([^)]*\)\s*=>\s*(\w+)\(")
_CONTATORE_FRESCO = re.compile(r"\bapri\w*\(")
# Due forme riconosciute, non una sola: `.disabled = true` e
# `.setAttribute("disabled", ...)` disabilitano l'elemento allo stesso modo
# (un attributo booleano HTML, il valore del secondo argomento non conta).
# Prima di questa riga solo la prima forma era riconosciuta, e la seconda —
# una difesa legittima quanto la prima — veniva segnalata come vulnerabile:
# un falso positivo che disattiva chi lo incontra invece di proteggerlo.
_DISABLE_ELEMENTO = re.compile(r"""\.disabled\s*=\s*true\b|\.setAttribute\(\s*["']disabled["']""")
_SCRITTURA = re.compile(r"(?<![=!<>])=(?!=|>)")


def _corpo_del_gestore(gestore: str, modulo: str) -> str:
    """Risolve il testo del gestore per un solo livello di delega: un
    riferimento nominato (`annullaLaCorsa`) o una singola espressione di
    chiamata (`() => scriviParametro(...)`) vengono seguiti fino al corpo
    della funzione richiamata. Non piu' in la': un gestore che delega a una
    funzione che a sua volta delega a quella che apre il contatore non viene
    risolto — e' il primo confine dichiarato piu' sotto, nel corpo del test.
    """
    gestore = gestore.strip()
    if _GESTORE_NOMINATO.match(gestore):
        try:
            return _sorgente_di(gestore, modulo)
        except (IndexError, ValueError):
            return gestore
    apertura = gestore.find("{")
    if apertura != -1:
        profondita = 0
        for indice in range(apertura, len(gestore)):
            if gestore[indice] == "{":
                profondita += 1
            elif gestore[indice] == "}":
                profondita -= 1
                if profondita == 0:
                    return gestore[apertura + 1 : indice]
        return gestore[apertura + 1 :]
    delega = _DELEGA_A_UNA_FUNZIONE.match(gestore)
    if delega:
        try:
            return _sorgente_di(delega.group(1), modulo)
        except (IndexError, ValueError):
            return gestore
    return gestore


def _fine_chiamata(testo: str, apertura: int) -> int:
    """Indice appena dopo la ')' che chiude la chiamata la cui '(' sta a
    `apertura`, contando la profondita' delle parentesi."""
    profondita = 1
    indice = apertura + 1
    while indice < len(testo) and profondita > 0:
        if testo[indice] == "(":
            profondita += 1
        elif testo[indice] == ")":
            profondita -= 1
        indice += 1
    return indice


def _file_js_dell_interfaccia(base: Path = UI_DIR) -> list[Path]:
    """Ogni `.js` sotto `base`, in qualunque sottocartella, derivato con un
    glob e non elencato a mano: uno scanner che leggesse un percorso
    letterale (`base / "app.js"`) lascerebbe un secondo file con un gestore
    vulnerabile invisibile in silenzio — e un elenco a mano dei nomi avrebbe
    lo stesso difetto un livello piu' in la', perche' un file nuovo non
    finirebbe nell'elenco. Un glob non ricorsivo ha lo stesso difetto ancora
    un livello piu' in la': cattura un file nuovo a fianco di `app.js` ma non
    uno nato domani in una sottocartella (`ui/pannelli/qualcosa.js`), e tace
    esattamente come i due difetti precedenti — percio' `rglob`, non `glob`.

    `vendor/` resta fuori per nome, non perche' un glob ricorsivo non ci
    arrivi: ci arriverebbe, ed e' filtrato apposta, perche' non e' nostro
    codice. Fuori raggio anche cio' che non finisce in `.js` — `index.html`,
    `stile.css` — dichiarato qui e non lasciato implicito: quei file hanno le
    proprie prove altrove in questo modulo, non questo scanner."""
    return sorted(
        p for p in base.rglob("*.js") if "vendor" not in p.relative_to(base).parts
    )


def _addEventListener_del_modulo(modulo: str) -> list[dict]:
    """Ogni `.addEventListener(evento, gestore)` a livello di modulo, con la
    riga sorgente e il testo grezzo (non ancora risolto) del gestore."""
    risultati = []
    for trovato in re.finditer(r'\.addEventListener\(\s*["\'](\w+)["\']\s*,\s*', modulo):
        evento = trovato.group(1)
        apertura = modulo.index("(", trovato.start())
        fine = _fine_chiamata(modulo, apertura)
        gestore = modulo[trovato.end() : fine - 1]
        riga = modulo.count("\n", 0, trovato.start()) + 1
        risultati.append({"riga": riga, "evento": evento, "gestore": gestore})
    return risultati


def _vulnerabile(corpo: str) -> tuple[bool, str]:
    """La proprieta': un corpo che attende `fetch` e scrive dopo, senza aprire
    un contatore fresco (`apri\\w*(`, la famiglia di apriGenerazione /
    apriGeometria / apriBattuta / apriRichiesta / apriAzione) ne'
    disabilitare l'elemento (`.disabled = true`) **prima** dell'attesa, e'
    vulnerabile all'ordine invertito di due chiamate sovrapposte."""
    indice = corpo.find("await fetch(")
    if indice == -1:
        return False, "nessuna await fetch nel corpo risolto"
    apertura = corpo.index("(", indice)
    dopo = corpo[_fine_chiamata(corpo, apertura) :]
    if not _SCRITTURA.search(dopo):
        return False, "nessuna scrittura dopo l'attesa"
    prima = corpo[:indice]
    if _CONTATORE_FRESCO.search(prima) or _DISABLE_ELEMENTO.search(prima):
        return False, "contatore fresco o disable aperti prima dell'attesa"
    return True, "nessun contatore fresco ne' disable prima dell'attesa fetch, e scrive dopo"


def _segnalazioni(base: Path = UI_DIR) -> list[str]:
    """Applica la proprieta' `_vulnerabile` a ogni gestore di ogni file
    trovato da `_file_js_dell_interfaccia(base)`. Estratta a parte cosi' la
    portata (quali file entrano nella scansione) e la proprieta' (cosa rende
    un gestore vulnerabile) si provano insieme, con la stessa funzione, sia
    sull'interfaccia vera sia su una directory finta."""
    segnalati = []
    for percorso in _file_js_dell_interfaccia(base):
        modulo = percorso.read_text(encoding="utf-8")
        for voce in _addEventListener_del_modulo(modulo):
            corpo = _corpo_del_gestore(voce["gestore"], modulo)
            vulnerabile, ragione = _vulnerabile(corpo)
            if vulnerabile:
                segnalati.append(f"{percorso.name}, riga {voce['riga']} (evento {voce['evento']}): {ragione}")
    return segnalati


def test_ogni_gestore_che_scrive_dopo_un_attesa_si_difende():
    """Lo scanner strutturale che chiude la serie — il cuore di questo giro.
    Vedi il commento di sezione qui sopra per la proprieta'; qui sotto, per
    iscritto e non taciuto, il confine di quello che questo scanner NON vede
    — tacerlo ripeterebbe esattamente il difetto del test sui `.json()`, che
    scandiva la sola sottostringa letterale ed e' stato aggirato in tre modi:

    - **un solo livello di delega.** Un gestore che delega a una funzione la
      quale a sua volta delega a un'altra che apre il contatore non viene
      risolto: passerebbe per «nessuna await fetch nel corpo risolto» anche
      se in realta' ne contiene una, due chiamate piu' in la'.
    - **solo la stringa letterale `await fetch(`.** Un gestore che attende
      una funzione intermedia (`await ricaricaVistaAsync()`) che al suo
      interno fa la fetch non viene riconosciuto come «attende» da questo
      scanner, anche se il gestore risolto la contiene per intero.
    - **controllo posizionale sul testo, non sul flusso di controllo.** Il
      contatore o il disable devono comparire testualmente prima della prima
      `await fetch(`: una chiamata `apriX()` scritta dentro un `if` che a
      runtime puo' non eseguirsi affatto prima della fetch supera comunque
      questo controllo, perche' lo scanner non sa se quel ramo si esegue
      davvero.
    - **il contatore va solo aperto, non controllato.** Lo scanner guarda se
      `apri\\w*(` compare nel testo prima della fetch — non se il valore che
      restituisce viene davvero letto da una `superata(...)`. Una
      `apriRichiesta()` lasciata li' per decorazione, con la guardia vera
      tolta subito dopo, resta invisibile: verificato mutando cosi' il
      bottone del ritaglio nel worktree di lavoro — lo scanner e' rimasto
      verde, e solo il test comportamentale sui due clic sovrapposti (sotto)
      e' diventato rosso. E' il motivo per cui questo giro non si ferma allo
      scanner: la coppia struttura+comportamento e' quella che chiude,
      nessuna delle due da sola.
    - **due forme di disable riconosciute, non tutte.** `.disabled = true` e
      `.setAttribute("disabled", ...)` (qualunque secondo argomento: e' un
      attributo booleano HTML) contano come difesa. Un `readOnly = true`, o
      togliere l'elemento dal DOM per la durata dell'attesa, restano non
      riconosciuti: un gestore disabilitato in una di queste due forme
      risulterebbe un falso vulnerabile (innocuo qui: nessuno dei due casi e'
      nel file oggi, verificato leggendolo). Fino alla correzione di questo
      giro solo `.disabled = true` era riconosciuta, e `setAttribute` — una
      difesa legittima quanto l'altra — veniva segnalata a torto: un falso
      positivo che disattiva chi lo incontra, verificato in
      `test_lo_scanner_riconosce_anche_setAttribute_disabled_come_disable_legittimo`.
    - **«scrive dopo l'attesa» e' un `=` di assegnazione nel testo dopo la
      fetch** (che non sia `==`, `===` ne' `=>`). Conta anche una `const x =
      ...` puramente locale che non scrive mai fuori dal gestore — puo'
      quindi sovrastimare (falso vulnerabile) — ma non vede una scrittura per
      side-effect senza `=` dopo la fetch, come una `Array.push(...)` o una
      chiamata a un setter senza segno `=` visibile — puo' quindi
      sottostimare (falso sicuro) in quel caso specifico, non presente oggi
      in questo file, verificato leggendolo.

    - **la portata era un percorso letterale, non dichiarata.** Fino alla
      correzione di questo giro lo scanner leggeva solo `UI_DIR / "app.js"`:
      un secondo file dell'interfaccia con un gestore vulnerabile restava
      invisibile in silenzio, il difetto peggiore per un test strutturale
      perche' non fallisce e non avverte. Ora scandisce ogni `.js` derivato
      da `_file_js_dell_interfaccia()` (oggi: `app.js` e `viewport.js`;
      `vendor/` resta fuori) — verificato che il glob deriva l'insieme giusto
      in `test_l_insieme_dei_file_scanditi_e_derivato_non_elencato_a_mano`.
      `viewport.js` oggi non contiene nessuna `fetch(`: scandirlo non
      aggiunge segnalazioni, ma lo mette nel raggio se un giorno ne
      aggiungesse una.

    La parte che resta vera della dichiarazione di limite del giro precedente:
    questa proprieta' cattura la guardia **assente o troppo grossolana in una
    forma riconoscibile** — non stabilisce quale sia la grana giusta (per
    campo? per clic? per pannello?), quella resta una decisione di dominio.
    """
    assert _segnalazioni() == [], (
        "gestori senza contatore fresco (apri\\w*()) ne' disable riconosciuto "
        '(.disabled = true, oppure .setAttribute("disabled", ...)) prima dell\'attesa:\n'
        + "\n".join(_segnalazioni())
    )


def test_l_insieme_dei_file_scanditi_e_derivato_non_elencato_a_mano(tmp_path):
    """Il limite trovato dal revisore: lo scanner leggeva `UI_DIR / "app.js"`,
    un percorso letterale. Un secondo file dell'interfaccia con un gestore
    vulnerabile restava invisibile in silenzio — provato dal revisore
    creandone uno vero in un worktree isolato e vedendo lo scanner non
    accorgersene.

    Qui si prova la derivazione da sola, su una directory finta: un elenco a
    mano dei nomi (`["app.js", "viewport.js"]`) avrebbe risolto il caso di
    oggi ma avrebbe lo stesso identico difetto un livello piu' in la' — un
    terzo file futuro resterebbe fuori dall'elenco esattamente come restava
    fuori dal percorso letterale. Il glob non ha questo problema: qualunque
    `.js`, a qualunque profondita' sotto la directory, ci entra da solo —
    `pannelli/qualcosa.js` qui sotto non esiste oggi in `UI_DIR`: e' il caso
    futuro che un glob non ricorsivo lasciava fuori in silenzio.
    """
    finto = tmp_path / "ui"
    finto.mkdir()
    (finto / "app.js").write_text("", encoding="utf-8")
    (finto / "altro.js").write_text("", encoding="utf-8")
    (finto / "vendor").mkdir()
    (finto / "vendor" / "three.module.js").write_text("", encoding="utf-8")
    (finto / "pannelli").mkdir()
    (finto / "pannelli" / "qualcosa.js").write_text("", encoding="utf-8")
    trovati = {p.relative_to(finto) for p in _file_js_dell_interfaccia(finto)}
    assert trovati == {Path("app.js"), Path("altro.js"), Path("pannelli/qualcosa.js")}, (
        f"il glob non scende nelle sottocartelle, o non esclude vendor/: {trovati}"
    )


def test_un_gestore_vulnerabile_in_una_sottocartella_futura_viene_visto(tmp_path):
    """Dai alla portata un test proprio, non solo all'insieme dei nomi qui
    sopra: qui il file in sottocartella non e' vuoto, contiene un gestore
    vulnerabile per davvero — la stessa proprieta' di
    `test_ogni_gestore_che_scrive_dopo_un_attesa_si_difende`, applicata a un
    file che oggi non esiste in `UI_DIR` (`pannelli/qualcosa.js`) ma
    domani potrebbe. Morde: con `base.glob("*.js")` al posto di
    `base.rglob("*.js")` questo file resta fuori e `_segnalazioni` torna
    vuota nonostante il gestore sotto sia vulnerabile — verificato a mano
    ripristinando temporaneamente il glob non ricorsivo nel worktree di
    lavoro, vedi il rapporto.
    """
    finto = tmp_path / "ui"
    (finto / "pannelli").mkdir(parents=True)
    (finto / "pannelli" / "qualcosa.js").write_text(
        'bottone.addEventListener("click", async () => {\n'
        '  const risposta = await fetch("/api/qualcosa");\n'
        '  esito.textContent = risposta.status;\n'
        "});\n",
        encoding="utf-8",
    )
    segnalati = _segnalazioni(finto)
    assert segnalati != [], (
        "un gestore vulnerabile in sottocartella resta invisibile allo scanner"
    )
    assert segnalati[0].startswith("qualcosa.js"), segnalati


def test_lo_scanner_riconosce_anche_setAttribute_disabled_come_disable_legittimo():
    """Il falso positivo trovato dal revisore: `setAttribute("disabled", "")`
    disabilita l'elemento tanto quanto `.disabled = true` — e' lo stesso
    attributo booleano HTML, letto da entrambe le forme — ma prima di questa
    correzione lo scanner riconosceva solo la seconda e segnalava la prima
    come vulnerabile. Un test strutturale che grida al lupo per una difesa
    legittima si disattiva al primo che ha fretta, e allora non protegge piu'
    niente."""
    corpo = """
      bottone.setAttribute("disabled", "");
      const risposta = await fetch("/api/qualcosa");
      esito.textContent = risposta.status;
    """
    vulnerabile, ragione = _vulnerabile(corpo)
    assert not vulnerabile, f"setAttribute('disabled', ...) e' una difesa legittima, segnalata comunque: {ragione}"


# --------------------------------------------------------------------------
# Rilievo 1, quarta istanza: `ultimaGeometria`. Il buco principale trovato
# dalla revisione di questo giro. Le quattro guardie (righe 218, 232, 257,
# 269) esistono gia' e sono corrette — il difetto non e' nel codice, e' nella
# copertura: nessun test le provava, e rese decorative (`apriGeometria()`
# lasciata a chiamare, la lettura tolta) la suite intera restava 36 passed su
# 36, in un worktree isolato. Questi due test chiudono quel buco.
# --------------------------------------------------------------------------


def _banco_di_geometria() -> str:
    """`mostraNuvolaDelloStep` e `mostraStep`, con `vista` finta: e' dove sta
    il quarto contatore del censimento, `ultimaGeometria`, condiviso fra la
    tratta della nuvola e quella della mesh — il fronte di discesa ricarica
    la vista senza aprire una nuova generazione, quindi puo' gareggiare con
    una risposta partita prima portando lo stesso `ordine`; solo
    `ultimaGeometria` li distingue.
    """
    return _DOM + _funzioni(
        "apriGeometria", "superata", "nomeDelloStep", "scriviConteggi",
        "dichiaraCaricamento", "chiudiCaricamento",
        "serverMuto", "ragioneDelRifiuto", "corpoBinarioLetto", "messaggioArtefattoMancante",
        "messaggioDownloadInterrotto", "segnalaArtefattoMancante",
        "mostraNuvolaDelloStep", "mostraStep",
        # Il confronto sta su ogni strada che svuota o disegna: spostaNelPrecedente
        # ha preso il posto delle quattro chiamate a vista.svuota(), e registraVista
        # quello delle due didascalie di una geometria riuscita.
        "spostaNelPrecedente", "registraVista", "aggiornaConfronto", "spegniConfronto",
        "alternaConfronto",
    ) + """
let ultimaGeometria = 0;
let ultimiSteps = [];
const STEP_CON_MESH = new Set([5, 6, 8, 9]);
let vistaMostrata = null;
let vistaPrecedente = null;
let conteggiDiPrima = null;
let stepMostrato = null;
const bottoneConfronta = document.getElementById("confronta");
const vista = {
  svuotate: 0,
  disegnato: null,
  precedente: null,
  confronto: false,
  // Sposta e dichiara se ha spostato, come quella vera: e' il valore su cui
  // spostaNelPrecedente decide se far scorrere anche il nome. Uno stub che
  // torna sempre undefined renderebbe la guardia inerte e verde — la seconda
  // svuota() di ogni strada butterebbe il precedente appena messo da parte, e
  // nessun assert lo vedrebbe.
  svuota() {
    this.svuotate += 1;
    if (this.disegnato === null) return false;
    this.precedente = this.disegnato;
    this.disegnato = null;
    return true;
  },
  mostraNuvola(dati) { this.disegnato = { tipo: "nuvola", lunghezza: dati.length }; },
  mostraMesh(vertici) { this.disegnato = { tipo: "mesh", lunghezza: vertici.length }; },
  mostraPrecedente(attivo) { this.confronto = attivo; },
};
let risponde = [];
let chiamata = 0;
globalThis.fetch = async () => risponde[chiamata++]();
"""


def test_due_richieste_di_nuvola_sovrapposte_con_lo_stesso_ordine_non_fanno_vincere_la_vecchia(tmp_path):
    """La tratta della nuvola. Due richieste con lo stesso `ordine` — il caso
    del fronte di discesa in gara con una risposta partita prima, righe
    195-206 del modulo — invertite: quella piu' recente arriva per prima e
    disegna, quella piu' vecchia rientra dopo e non deve scrivere sopra."""
    _esegui(tmp_path, _banco_di_geometria() + """
let risolvi1, risolvi2;
risponde = [
  () => new Promise((r) => { risolvi1 = r; }),
  () => new Promise((r) => { risolvi2 = r; }),
];

const vecchia = mostraNuvolaDelloStep(9, generazione);
const nuova = mostraNuvolaDelloStep(9, generazione);

// La piu' recente arriva per prima.
risolvi2({
  ok: true,
  headers: { get: (nome) => ({ "X-Points-Drawn": "20", "X-Points-Total": "20" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(80),
});
assert.equal(await nuova, true, "la richiesta piu' recente non risulta disegnata");
assert.equal(vista.disegnato.lunghezza, 20, "il disegno a video non e' quello della richiesta recente");
assert.equal(vista.svuotate, 1, "la vista si e' svuotata piu' volte del dovuto finora");

// La piu' vecchia, rimasta in volo, rientra per ultima.
risolvi1({
  ok: true,
  headers: { get: (nome) => ({ "X-Points-Drawn": "5", "X-Points-Total": "5" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(20),
});
assert.equal(await vecchia, false, "la richiesta vecchia risulta disegnata: doveva essere scartata");
assert.equal(vista.disegnato.lunghezza, 20,
  "la risposta vecchia, arrivata per ultima, ha scritto sopra la nuvola piu' recente");
assert.equal(vista.svuotate, 1,
  "la vista vecchia e' stata svuotata di nuovo dopo essere gia' aggiornata dalla richiesta recente");
""")


def test_due_richieste_di_mesh_sovrapposte_con_lo_stesso_ordine_non_fanno_vincere_la_vecchia(tmp_path):
    """Stessa istanza sul ramo della mesh (righe 254-269 del modulo): stesso
    contatore `ultimaGeometria`, stessa guardia ripetuta due volte. Provata a
    parte perche' la mutazione decorativa del giro precedente ha svuotato
    tutte e quattro le guardie insieme, e un solo test sulla nuvola non
    proverebbe che anche questo ramo si difende per davvero."""
    _esegui(tmp_path, _banco_di_geometria() + """
let risolvi1, risolvi2;
risponde = [
  () => new Promise((r) => { risolvi1 = r; }),
  () => new Promise((r) => { risolvi2 = r; }),
];

const vecchia = mostraStep(9, generazione);
const nuova = mostraStep(9, generazione);

// La piu' recente arriva per prima: 7 vertici, 0 triangoli.
risolvi2({
  ok: true,
  headers: { get: (nome) => ({ "X-Vertices": "7", "X-Triangles": "0" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(84),
});
assert.equal(await nuova, true, "la richiesta piu' recente non risulta disegnata");
assert.equal(vista.disegnato.lunghezza, 21, "il disegno a video non e' quello della mesh recente");

// La piu' vecchia, rimasta in volo, rientra per ultima: 2 vertici.
risolvi1({
  ok: true,
  headers: { get: (nome) => ({ "X-Vertices": "2", "X-Triangles": "0" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(24),
});
assert.equal(await vecchia, false, "la mesh vecchia risulta disegnata: doveva essere scartata");
assert.equal(vista.disegnato.lunghezza, 21,
  "la mesh vecchia, arrivata per ultima, ha scritto sopra quella piu' recente");
""")


# --------------------------------------------------------------------------
# aria-busy: chi lo chiude, e chi non deve toccarlo.
# --------------------------------------------------------------------------


def test_una_risposta_arrivata_chiude_il_caricamento(tmp_path):
    """Il caso comune: la risposta passa la guardia dell'ordine e scrive.
    chiudiCaricamento() deve girare, non restare marcato all'infinito."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
risponde = [() => ({
  ok: true,
  headers: { get: (nome) => ({ "X-Points-Drawn": "3", "X-Points-Total": "3" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(12),
})];
await mostraNuvolaDelloStep(9, generazione);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), null,
  "una risposta disegnata lascia la tela marcata come occupata",
);
""")


def test_nessun_artefatto_chiude_il_caricamento_e_non_lo_confonde_con_un_server_muto(tmp_path):
    """Un 404 vero (lo step non ha ancora un artefatto) e' un dato negativo
    documentato, non un guasto: il testo resta quello di sempre e la tela
    smette comunque di dirsi occupata."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
risponde = [() => ({ ok: false, status: 404, text: async () => "" })];
await mostraNuvolaDelloStep(9, generazione);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), null,
  "\\"nessun artefatto\\" lascia la tela marcata come occupata",
);
assert.equal(
  document.getElementById("conteggi").textContent,
  "nessun artefatto per questo step: eseguilo per vederne il risultato.",
  "il testo del rifiuto documentato e' cambiato",
);
""")


def test_il_server_muto_chiude_il_caricamento_e_segnala_il_server_non_il_dato(tmp_path):
    """Il guasto vero: fetch rigetta (rete caduta, non un HTTP di rifiuto).
    Prima della correzione questo rigetto usciva non gestito e la tela restava
    marcata occupata per sempre. Ora .catch(serverMuto) lo prende, e il testo
    deve dire che il server non ha risposto — non che il dato non esiste,
    che e' il fatto opposto."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
risponde = [() => { throw new TypeError("fetch failed"); }];
await mostraNuvolaDelloStep(9, generazione);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), null,
  "il server muto lascia la tela marcata come occupata",
);
const didascalia = document.getElementById("conteggi").textContent;
assert.match(didascalia, /il server non ha risposto/,
  `il server muto non viene raccontato come tale: ${didascalia}`);
assert.doesNotMatch(didascalia, /nessun artefatto/,
  `il server muto si confonde con un rifiuto documentato: ${didascalia}`);
""")


def test_una_risposta_scartata_non_chiude_il_caricamento(tmp_path):
    """La guardia contro un chiudiCaricamento() spostato in un finally: una
    risposta che la regola dell'ordine scarta non deve toccare aria-busy,
    perche' e' la risposta che vince la propria corsa a doverlo chiudere. Un
    finally cieco lo toglierebbe anche qui, e questo diventerebbe rosso."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
risponde = [() => ({
  ok: true,
  headers: { get: (nome) => ({ "X-Points-Drawn": "3", "X-Points-Total": "3" }[nome]) },
  arrayBuffer: async () => new ArrayBuffer(12),
})];
const ordine = generazione;
const scartata = mostraNuvolaDelloStep(9, ordine);
generazione += 1; // un nuovo clic supera questa richiesta prima che risponda
assert.equal(await scartata, false, "la risposta scartata risulta disegnata");
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), "true",
  "la risposta scartata ha tolto aria-busy: doveva lasciarlo a chi vince la corsa",
);
""")


def test_messaggioArtefattoMancante_distingue_server_muto_da_rifiuto_documentato(tmp_path):
    """La funzione estratta, chiamata da sola: e' l'unica superficie che
    decide il testo, e questo la sorveglia senza passare da mostraStep o
    mostraNuvolaDelloStep."""
    _esegui(tmp_path, _banco_di_geometria() + """
const documentato = await messaggioArtefattoMancante({ status: 404 });
assert.equal(documentato,
  "nessun artefatto per questo step: eseguilo per vederne il risultato.",
  "il rifiuto documentato non deve cambiare testo");

const muto = await messaggioArtefattoMancante({
  status: 0,
  text: async () => JSON.stringify({ messaggio: "il server non ha risposto: boom" }),
});
assert.match(muto, /il server non ha risposto: boom/,
  `lo status 0 non produce il messaggio del server muto: ${muto}`);
""")


def test_segnalaArtefattoMancante_chiude_svuota_e_scrive_il_messaggio(tmp_path):
    """L'altra meta' estratta, chiamata da sola: chiude aria-busy, svuota la
    vista e scrive il messaggio che riceve — niente di piu', niente di meno."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
segnalaArtefattoMancante("un messaggio qualsiasi");
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), null,
  "segnalaArtefattoMancante non chiude aria-busy",
);
assert.equal(vista.svuotate, 1, "segnalaArtefattoMancante non svuota la vista");
assert.equal(
  document.getElementById("conteggi").textContent, "un messaggio qualsiasi",
  "segnalaArtefattoMancante non scrive il messaggio ricevuto",
);
""")


# --------------------------------------------------------------------------
# Il confronto fra due step. La domanda per cui lo strumento esiste — «che cosa
# ha fatto questo step alla geometria» — non aveva risposta a video: gli undici
# artefatti si guardavano di fila e mai due insieme.
# --------------------------------------------------------------------------


_DISEGNA = """
ETICHETTE["03_downsample"] = "Riduzione";
ETICHETTE["04_normals"] = "Normali";
ultimiSteps = [
  { numero: 3, chiave: "03_downsample", stato: "valido" },
  { numero: 4, chiave: "04_normals", stato: "valido" },
];
const conteggi = document.getElementById("conteggi");
// Una nuvola disegnata per davvero, passando dalle strade vere: stepMostrato e'
// cio' che registraVista legge per sapere di quale step e' la geometria.
const disegna = async (numero, punti) => {
  stepMostrato = numero;
  chiamata = 0;
  risponde = [() => ({
    ok: true,
    headers: { get: (n) => ({ "X-Points-Drawn": String(punti), "X-Points-Total": String(punti) }[n]) },
    arrayBuffer: async () => new ArrayBuffer(punti * 12),
  })];
  return mostraStep(numero, generazione);
};
const fallisci = async (numero) => {
  stepMostrato = numero;
  chiamata = 0;
  risponde = [() => ({ ok: false, status: 404 })];
  return mostraStep(numero, generazione);
};
"""


def test_il_confronto_si_annuncia_solo_quando_c_e_qualcosa_da_confrontare(tmp_path):
    """Il requisito che rende la funzione una funzione: deve dirsi. Un gesto che
    nessuna etichetta annuncia esiste solo per chi lo sa gia', e l'utente
    successivo confermato non conosce nemmeno gli undici step.

    Tre proprieta', e ognuna rotta trasforma il comando in una promessa falsa:

    1. con un solo step guardato non c'e' nessun confronto possibile, e il
       comando non deve esserci (un bottone che non puo' fare niente e' un
       invito che mente);
    2. quando c'e', **nomina** lo step che mostrerebbe, col nome che la colonna
       di sinistra usa e non col numero;
    3. rieseguendo lo stesso step nomina «di prima» — e' il confronto che conta
       di piu', cioe' che cosa ha fatto alla geometria il parametro appena
       cambiato, e senza quelle due parole il comando direbbe «Confronta con
       Normali» stando sulle Normali, cioe' sembrerebbe non fare nulla.
    """
    elemento = _elemento(_senza_commenti_html(_markup()), "confronta")
    assert "hidden" in elemento, f"il comando nasce visibile e non ha nulla da mostrare: {elemento}"
    assert 'aria-pressed="false"' in elemento, (
        f"il comando non nasce dichiarato come interruttore: {elemento}"
    )

    _esegui(tmp_path, _banco_di_geometria() + _DISEGNA + """
aggiornaConfronto();
assert.equal(bottoneConfronta.hidden, true,
  "alla prima apertura il comando c'e' gia', e non ha nessuna geometria di prima da mostrare");

await disegna(3, 10);
assert.equal(bottoneConfronta.hidden, true,
  "un solo step guardato e il comando promette un confronto che non esiste");

await disegna(4, 20);
assert.equal(bottoneConfronta.hidden, false, "due step guardati e il confronto non si annuncia");
assert.equal(bottoneConfronta.textContent, "Confronta con Riduzione",
  `il comando non nomina lo step che mostrerebbe: ${bottoneConfronta.textContent}`);

await disegna(4, 30);
assert.equal(bottoneConfronta.textContent, "Confronta con Normali di prima",
  `lo stesso step rieseguito non e' distinto da un altro step: ${bottoneConfronta.textContent}`);
""")


def test_il_confronto_dice_sempre_quale_geometria_e_a_video(tmp_path):
    """L'interruttore, nei due versi. Il difetto che questo chiude e' quello che
    il modulo ha gia' pagato una volta sul ramo dell'artefatto mancante: una
    vista che contraddice la propria didascalia. Acceso il confronto, a video c'e'
    la geometria di prima e sotto si leggerebbero i conteggi di quella di adesso.

    Quattro proprieta':

    1. accendendo, la scena riceve il confronto e la didascalia nomina l'altro
       step **con i suoi conteggi**, non con quelli della geometria coperta;
    2. spegnendo, la didascalia torna identica a com'era, non ricostruita;
    3. `aria-pressed` segue nei due versi, perche' e' l'unico canale per chi non
       vede quale delle due geometrie sia a video;
    4. una geometria nuova spegne il confronto: acceso, resterebbe a video il
       gruppo che sta proprio diventando il precedente di se stesso.
    """
    _esegui(tmp_path, _banco_di_geometria() + _DISEGNA + """
await disegna(3, 10);
await disegna(4, 20);
const didascalia = conteggi.textContent;
assert.equal(didascalia, "20 punti disegnati su 20", `precondizione: ${didascalia}`);

alternaConfronto();
assert.equal(bottoneConfronta.getAttribute("aria-pressed"), "true",
  "chi non vede non ha modo di sapere che a video c'e' l'altra geometria");
assert.equal(vista.confronto, true, "il confronto non arriva alla scena");
assert.match(conteggi.textContent, /Riduzione/,
  `la didascalia non dice di quale step sia la geometria a video: ${conteggi.textContent}`);
assert.match(conteggi.textContent, /10 punti/,
  `la didascalia porta i conteggi della geometria coperta: ${conteggi.textContent}`);

alternaConfronto();
assert.equal(vista.confronto, false, "il confronto non si spegne");
assert.equal(bottoneConfronta.getAttribute("aria-pressed"), "false", "l'interruttore resta premuto");
assert.equal(conteggi.textContent, didascalia,
  `la didascalia non torna quella di prima: ${conteggi.textContent}`);

alternaConfronto();
await disegna(3, 30);
assert.equal(vista.confronto, false,
  "una geometria nuova lascia il confronto acceso: a video resta il gruppo che sta diventando il precedente");
assert.equal(bottoneConfronta.getAttribute("aria-pressed"), "false",
  "il comando resta premuto su una geometria che non e' quella confrontata");
""")


def test_un_artefatto_mancante_lascia_a_tiro_l_ultima_geometria_riuscita(tmp_path):
    """Il ramo dell'artefatto mancante svuota la vista apposta — una vista che
    contraddice la sua didascalia e' peggio di una vista vuota — e per il
    confronto e' esattamente il caso in cui serve: l'artefatto non c'e', e
    l'ultima cosa che si e' vista con successo sta a un clic.

    La proprieta' che si rompe in silenzio e' il **nome**: il fallimento non
    registra nessuna geometria mostrata, quindi il comando deve continuare a
    nominare l'ultimo step riuscito. Se il nome scorresse insieme alla scheda
    grafica su questo ramo, nominerebbe lo step di due prima mostrando quello di
    prima."""
    _esegui(tmp_path, _banco_di_geometria() + _DISEGNA + """
await disegna(3, 10);
await disegna(4, 20);
await fallisci(3);
assert.equal(vista.disegnato, null, "precondizione: l'artefatto mancante lascia la vista vuota");
assert.equal(bottoneConfronta.hidden, false,
  "l'artefatto manca e l'ultima geometria riuscita non e' piu' raggiungibile");
assert.equal(bottoneConfronta.textContent, "Confronta con Normali",
  `il comando nomina uno step e ne mostrerebbe un altro: ${bottoneConfronta.textContent}`);
""")


def test_corpoBinarioLetto_torna_undefined_se_il_download_si_interrompe(tmp_path):
    """La funzione che tiene fuori il rigetto di arrayBuffer(): un download
    riuscito torna il buffer, uno interrotto torna undefined invece di
    sollevare. Il controllo positivo evita che basti sempre restituire
    undefined per passare."""
    _esegui(tmp_path, _banco_di_geometria() + """
const buono = await corpoBinarioLetto({ arrayBuffer: async () => new ArrayBuffer(4) });
assert.equal(buono.byteLength, 4, "un download riuscito non deve tornare undefined");

const interrotto = await corpoBinarioLetto({
  arrayBuffer: async () => { throw new Error("connessione caduta"); },
});
assert.equal(interrotto, undefined,
  "un download interrotto deve tornare undefined, non far sollevare la funzione");
""")


def test_messaggioDownloadInterrotto_racconta_un_server_muto(tmp_path):
    """Il messaggio del download interrotto e' lo stesso di un server muto,
    non un testo proprio: se divergesse, questo lo direbbe."""
    _esegui(tmp_path, _banco_di_geometria() + """
const messaggio = await messaggioDownloadInterrotto();
assert.match(messaggio, /il server non ha risposto/,
  `il download interrotto non si racconta come un server muto: ${messaggio}`);
""")


def test_il_download_interrotto_a_meta_chiude_il_caricamento_e_segnala_il_server(tmp_path):
    """Finding 3: gli header arrivano (risposta.ok e' vero, i conteggi sono
    leggibili), poi arrayBuffer() rigetta a meta' del trasferimento. Prima
    della correzione questo rigetto usciva non gestito da mostraNuvolaDelloStep
    e da mostraStep(...).then() senza .catch: la tela restava marcata occupata
    per sempre. Deve leggersi come un server muto, non come uno step senza
    artefatto — i byte erano in arrivo."""
    _esegui(tmp_path, _banco_di_geometria() + """
document.getElementById("viewport").setAttribute("aria-busy", "true");
risponde = [() => ({
  ok: true,
  headers: { get: (nome) => ({ "X-Points-Drawn": "20", "X-Points-Total": "20" }[nome]) },
  arrayBuffer: async () => { throw new Error("connessione caduta a meta' del download"); },
})];
await mostraNuvolaDelloStep(9, generazione);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), null,
  "il download interrotto lascia la tela marcata come occupata",
);
const didascalia = document.getElementById("conteggi").textContent;
assert.match(didascalia, /il server non ha risposto/,
  `il download interrotto non viene raccontato come un server muto: ${didascalia}`);
assert.doesNotMatch(didascalia, /nessun artefatto/,
  `il download interrotto si confonde con un rifiuto documentato: ${didascalia}`);
""")


def test_mostraStep_instrada_il_ramo_mesh_attraverso_le_funzioni_condivise():
    """Finding 4: nuvola e mesh condividevano lo stesso ramo di rifiuto
    copiato verbatim. Estratto in funzioni comuni, questo guarda che il ramo
    mesh ci passi davvero — una divergenza copia-incolla che tornasse a
    duplicare la logica invece di chiamare le funzioni condivise diventerebbe
    rossa qui, non solo sulla tratta della nuvola che i test sopra
    esercitano."""
    corpo = _sorgente_di("mostraStep", _modulo())
    for nome in (
        "messaggioArtefattoMancante(", "segnalaArtefattoMancante(",
        "corpoBinarioLetto(", "messaggioDownloadInterrotto(",
    ):
        assert nome in corpo, (
            f"mostraStep non instrada piu' per {nome}: torna a duplicare la logica della nuvola"
        )


# --------------------------------------------------------------------------
# BL-1: dai tasti al disco.
# --------------------------------------------------------------------------


def test_il_campo_parametro_non_indovina_il_tipo_dal_valore():
    """La radice del difetto. Il tipo veniva da `typeof` del valore corrente,
    cioe' indovinato: i quattro campi numerici nullabili scalari erano una
    casella di testo finche' valevano `None` e una numerica appena valevano
    qualcosa, e con `type="number"` Chrome sanifica cio' che non sa leggere —
    `.value` torna `""` mentre a video resta scritto `1e`. Il tipo lo conosce
    solo il modello, e `/api/schema` oggi non lo manda.

    I sei campi del ritaglio restano `type="number"`, e non e' un'incoerenza:
    li' il tipo non e' indovinato, sono le coordinate dell'ingombro e sono
    numeri per costruzione, con la loro guardia sul campo vuoto.

    I conteggi sono contati, non copiati: sui blocchi che l'interfaccia mostra i
    campi nullabili sono 7, di cui 4 numerici scalari (gli altri 3 sono tuple,
    che il pannello rende readOnly), gli interi 14, i decimali 19, i booleani 4,
    i `Literal` 4.
    """
    campo = _sorgente_di("campoParametro", _modulo())
    assert "typeof valore ===" not in campo, "il tipo del campo torna a dipendere dal valore"
    assert 'input.type = "number"' not in campo, (
        'type="number" sanifica in silenzio: cio\' che il browser non legge diventa ""'
    )
    assert 'input.step = "any"' not in campo, "step=any toglie il passo unitario ai 14 interi"


def test_una_battuta_illeggibile_resta_quella_battuta(tmp_path):
    """La funzione che trasforma dei tasti in un dato persistito, eseguita.

    `1e`, `-`, `1.2.3` non si leggono come numeri e restano la stringa battuta:
    il modello le rifiuta con un 422 leggibile, che e' l'unico posto dove il
    tipo vero si conosce. Diventassero `null` sarebbero accettate in silenzio
    sui quattro campi numerici nullabili. E lo spazio non vale zero:
    `Number(" ")` e' `0`, e un campo che a video sembra vuoto scriveva `0`.
    """
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n" + _funzioni("valoreScritto") + """
for (const battuto of ["1e", "-", "1.2.3", "abc", "1,5"]) {
  assert.equal(valoreScritto(battuto), battuto,
    `${battuto} non arriva al modello: viene inghiottito qui`);
}
assert.equal(valoreScritto(" "), null, "uno spazio scrive zero in un campo che sembra vuoto");
assert.equal(valoreScritto(""), null);
assert.equal(valoreScritto("2.5"), 2.5, "un valore buono non arriva piu' a destinazione");
assert.equal(valoreScritto(" 2.5 "), 2.5);
assert.equal(valoreScritto("true"), true);
assert.equal(valoreScritto("false"), false);
""")


def test_il_fuori_scala_non_diventa_un_numero(tmp_path):
    """Il confine della guardia. `Number("1e999")` e `Number("Infinity")` non
    sono `NaN`: passavano come numeri, e `JSON.stringify` li scrive **`null`**.
    Il corpo della PUT partiva gia' azzerato, il server accettava, e su
    `simplify.target_faces` e `tet.max_volume` — dove `null` significa «nessun
    limite» — chi batteva `1e999` credendo di alzare il tetto se lo vedeva
    tolto, con un 200 e lo schermo muto.

    Col controllo che lo smentisce: `1e3` e' notazione esponenziale legittima e
    deve continuare a valere `1000`, altrimenti la guardia rifiuta tutto e
    l'assenza di difetti e' solo l'assenza dell'interfaccia.
    """
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n" + _funzioni("valoreScritto")
            + """
for (const battuto of ["Infinity", "-Infinity", "1e999", "2e400"]) {
  assert.equal(valoreScritto(battuto), battuto,
    `${battuto} diventa un numero, e JSON.stringify lo scrive null`);
}
assert.equal(valoreScritto("  Infinity  "), "Infinity", "il trim non basta: resta un non finito");
assert.equal(valoreScritto("1e3"), 1000, "la notazione esponenziale legittima non passa piu'");
assert.equal(valoreScritto("2.5"), 2.5);
assert.equal(valoreScritto("-3"), -3);
""")


def test_il_fuori_scala_non_scrive_null_sul_disco(tmp_path):
    """La stessa cosa letta dal disco, che e' dove il danno si misura.

    `null` non e' piu' cio' che parte dal browser: la battuta arriva al modello,
    che su un intero la rifiuta con un 422 e lascia il file com'era. Su un
    decimale nullabile il modello oggi la **accetta** come infinito e scrive
    `.inf`: e' un residuo che sta nel modello e non qui — `allow_inf_nan=False`
    in `core/config.py`, misurato nel rapporto — e questo controllo afferma cio'
    che vale in tutti e due i casi, cosi' che quella correzione non lo rompa: il
    fronte non fabbrica piu' un `null` che nessuno ha battuto.
    """
    percorso = tmp_path / "config.yaml"
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    cfg.downsample.voxel_size = 25.0
    cfg.simplify.target_faces = 200000
    save_config(cfg, percorso)
    cliente = TestClient(create_app(percorso), raise_server_exceptions=False)

    uscita = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
                     + _funzioni("valoreScritto")
                     + 'process.stdout.write(JSON.stringify(valoreScritto("1e999")));')
    assert json.loads(uscita) == "1e999", (
        "il browser manda un valore che nessuno ha battuto: JSON.stringify scrive null"
    )

    configurazione = cliente.get("/api/config").json()
    prima = percorso.read_bytes()

    configurazione["simplify"]["target_faces"] = json.loads(uscita)
    rifiuto = cliente.put("/api/config", json=configurazione)
    assert rifiuto.status_code == 422, "il fuori scala e' stato accettato su un intero"
    assert percorso.read_bytes() == prima, "il tetto della semplificazione e' cambiato su disco"

    configurazione = cliente.get("/api/config").json()
    configurazione["downsample"]["voxel_size"] = json.loads(uscita)
    cliente.put("/api/config", json=configurazione)
    assert "voxel_size: null" not in percorso.read_text(encoding="utf-8"), (
        "il campo e' stato azzerato dal browser, non dal modello"
    )


def test_una_battuta_illeggibile_non_cambia_la_configurazione_su_disco(tmp_path):
    """La catena intera, dai tasti al file: il valore lo produce la funzione
    vera di `app.js` in `node`, la PUT e' quella vera del server, e il file e'
    quello della corsa. La regressione era esattamente qui — `voxel_size` che
    tornava a `None`, la configurazione scritta su disco, e a video niente.

    Il caso simmetrico e' nello stesso controllo apposta: un rifiuto che
    rifiuta tutto passerebbe la prima meta' e lascerebbe l'interfaccia inutile.
    """
    percorso = tmp_path / "config.yaml"
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    save_config(cfg, percorso)
    cliente = TestClient(create_app(percorso), raise_server_exceptions=False)

    def scritto(battuto: str) -> object:
        uscita = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
                         + _funzioni("valoreScritto")
                         + "process.stdout.write(JSON.stringify(valoreScritto("
                         + json.dumps(battuto) + ")));")
        return json.loads(uscita)

    configurazione = cliente.get("/api/config").json()
    prima = percorso.read_bytes()

    configurazione["downsample"]["voxel_size"] = scritto("1e")
    rifiuto = cliente.put("/api/config", json=configurazione)
    assert rifiuto.status_code == 422, "il valore illeggibile e' stato accettato"
    assert percorso.read_bytes() == prima, "la configurazione della corsa e' cambiata su disco"

    # La ragione che finisce a video la ricava la funzione vera del modulo dal
    # corpo vero del rifiuto: senza questo pezzo il rifiuto ci sarebbe e non si
    # vedrebbe, che e' meta' del difetto.
    ragione = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
                      + _funzioni("ragioneDelRifiuto")
                      + "const risposta = { status: 422, text: async () => "
                      + json.dumps(rifiuto.text) + " };\n"
                      "process.stdout.write(await ragioneDelRifiuto(risposta));")
    assert "voxel_size" in ragione and "number" in ragione, (
        f"la ragione non nomina il campo o non dice perche': {ragione}"
    )

    configurazione["downsample"]["voxel_size"] = scritto("2.5")
    buono = cliente.put("/api/config", json=configurazione)
    assert buono.status_code == 200, buono.text
    assert cliente.get("/api/config").json()["downsample"]["voxel_size"] == 2.5, (
        "un valore legittimo non arriva piu' a destinazione"
    )
    assert percorso.read_bytes() != prima, "il valore buono non e' stato scritto su disco"


# --------------------------------------------------------------------------
# BL-2: il gestore del campo, eseguito.
# --------------------------------------------------------------------------


def _banco_del_campo() -> str:
    """Il gestore vero del campo, con le sue dipendenze, su un DOM finto e con
    una `fetch` che decide il banco.

    Fino a ieri qui non arrivava niente: il gestore era una funzione anonima
    dentro un ciclo dentro `apriDettaglio`, e nessun banco la raggiungeva.
    Quello che si vedeva provato era la catena ricucita a mano — `valoreScritto`
    piu' `TestClient` — che e' la catena giusta ma **non e' il gestore**: il
    ripristino del valore di prima e il ramo del campo nullabile si potevano
    togliere e la suite restava verde. Adesso `campoParametro` costruisce la
    riga vera e `scriviParametro` la scrive, entrambe di primo livello apposta.
    """
    return _DOM + _funzioni(
        "valoreScritto", "ragioneDelRifiuto", "serverMuto", "superata", "corpoLetto",
        "reso", "segnalaCampo", "apriBattuta", "scriviParametro", "cambiatoDalPredefinito",
        "campoParametro",
    ) + """
// Il terzo contatore di Rilievo 1, per campo: scriviParametro lo legge dal
// modulo per nome, non da un parametro, quindi il banco deve ricrearlo tale e
// quale a `generazione` e `configurazione` qui sopra.
let ultimaBattutaDelCampo = new Map();
const CAMPO = { description: "la spaziatura del voxel" };
const richieste = [];
let risponde = null;
globalThis.fetch = async (percorso, opzioni) => {
  richieste.push({ percorso, corpo: JSON.parse(opzioni.body) });
  return risponde(percorso, opzioni);
};
const accetta = (canonica) => async () => ({ ok: true, status: 200, json: async () => canonica });
const rifiuta = (corpo) => async () => ({
  ok: false, status: 422, text: async () => JSON.stringify(corpo),
});
// Il server che non risponde: `fetch` non torna un 500, solleva.
const cade = () => { throw new TypeError("fetch failed"); };
function apriCampo(blocco, nome) {
  const riga = campoParametro(blocco, nome, CAMPO, generazione);
  const [, input, , messaggio] = riga.children;
  assert.equal(input.tag, "input", "la riga non e' piu' fatta come il banco crede");
  assert.equal(messaggio.className, "errore-campo", "il messaggio non e' piu' il quarto figlio");
  return { input, messaggio };
}
"""


def test_un_campo_nullabile_vuoto_non_mostra_la_stringa_null(tmp_path):
    """`String(null)` e' `"null"`: quattro parole in una casella dove `null`
    significa «lascia decidere alla misura», e chi la riscrive senza toccarla
    manda al modello la stringa `null`, che non e' un numero.
    """
    _esegui(tmp_path, _banco_del_campo() + """
configurazione = { downsample: { voxel_size: null }, segment: { crop_min: [1, 2, 3] } };
const { input } = apriCampo("downsample", "voxel_size");
assert.equal(input.value, "", "un campo nullabile vuoto mostra la stringa null");
// Una tupla non e' scritta in una casella di testo: String() la renderebbe
// "1,2,3", cioe' un testo che nessuna lettura produce. readOnly e non disabled,
// che la toglierebbe anche dal lettore di schermo.
const tupla = apriCampo("segment", "crop_min");
assert.equal(tupla.input.value, "[1,2,3]", "la lista finisce nel campo come testo di nessuno");
assert.equal(tupla.input.readOnly, true, "una lista diventa modificabile e ogni modifica e' rifiutata");
assert.equal((tupla.input.gestori.change ?? []).length, 0, "la lista manda una PUT a ogni battuta");
""")


def test_il_campo_mostra_il_valore_che_il_server_ha_accettato(tmp_path):
    """Il campo continuava a mostrare la battuta anche quando sul disco era
    finito un altro numero: `1_0` diventa `10.0`, `1e1_0` diventa dieci
    miliardi, `0x10` diventa `16.0`, `9.0` su un intero diventa `9`, `no`
    diventa `false`. Tutte con 200 e schermo muto.

    Riscrivere la casella con cio' che il server ha risposto le rende visibili
    in blocco, invece che una difesa per ogni grafia: a video finisce cio' che
    e' stato salvato.
    """
    _esegui(tmp_path, _banco_del_campo() + """
configurazione = { downsample: { voxel_size: 25 }, normals: { knn: 30 } };
const { input, messaggio } = apriCampo("downsample", "voxel_size");
assert.equal(input.value, "25", "il campo non parte dal valore della configurazione");
input.value = "1_0";
risponde = accetta({ downsample: { voxel_size: 10.0 }, normals: { knn: 30 } });
await input.scatena("change");
assert.deepEqual(
  richieste.map((r) => [r.percorso, r.corpo.downsample.voxel_size]), [["/api/config", "1_0"]],
  "cio' che il browser non legge non arriva piu' al modello, che e' l'unico che lo sa leggere",
);
assert.equal(input.value, "10", "il campo mostra la battuta e sul disco c'e' un altro numero");
assert.equal(configurazione.downsample.voxel_size, 10, "in memoria resta la battuta");
assert.equal(messaggio.hidden, true, "un campo accettato porta un messaggio d'errore");
assert.equal(input.getAttribute("aria-invalid"), null);
assert.ok(!input.className.includes("campo-rifiutato"));
""")


def test_il_valore_rifiutato_non_resta_nella_configurazione(tmp_path):
    """La PUT manda l'**intera** configurazione: un valore rifiutato lasciato
    dentro farebbe rifiutare ogni modifica successiva accusando il campo
    sbagliato. E il rifiuto va detto su tre canali, perche' due su tre lasciano
    fuori qualcuno.
    """
    _esegui(tmp_path, _banco_del_campo() + """
configurazione = { downsample: { voxel_size: 25 } };
const { input, messaggio } = apriCampo("downsample", "voxel_size");
input.value = "1e";
risponde = rifiuta({ detail: [
  { loc: ["body", "downsample", "voxel_size"], msg: "Input should be a valid number" },
] });
await input.scatena("change");
assert.equal(configurazione.downsample.voxel_size, 25,
  "il valore rifiutato resta in memoria: la prossima modifica sara' accusata al posto suo");
assert.equal(input.value, "1e", "la battuta rifiutata sparisce: non si vede piu' che correggere");
assert.match(messaggio.textContent, /downsample\\.voxel_size: Input should be a valid number/);
assert.equal(messaggio.hidden, false, "la ragione c'e' ma resta nascosta");
assert.equal(input.getAttribute("aria-invalid"), "true");
assert.equal(input.getAttribute("aria-errormessage"), messaggio.id,
  "aria-invalid da solo dice che c'e' un errore, mai quale");
assert.ok(input.className.includes("campo-rifiutato"));
""")


def test_il_server_caduto_non_manda_il_valore_con_la_modifica_di_un_altro_campo(tmp_path):
    """Il bloccante peggiore, perche' il valore trasportato e' arbitrario.

    `fetch` **solleva** quando il server non risponde — fermo, riavviato, la
    rete caduta — e l'eccezione usciva dal gestore: niente messaggio a video, e
    niente ripristino, che stava solo nel ramo del rifiuto. Il valore restava in
    `configurazione`, che e' di modulo, e partiva con la PUT successiva, quella
    di un altro campo. L'utente toccava `knn` e sul disco cambiava anche
    `voxel_size`, senza che nulla lo avesse mai detto.
    """
    _esegui(tmp_path, _banco_del_campo() + """
configurazione = { downsample: { voxel_size: 25 }, normals: { knn: 30 } };
const voxel = apriCampo("downsample", "voxel_size");
const knn = apriCampo("normals", "knn");

voxel.input.value = "3.5";
risponde = cade;
await voxel.input.scatena("change");
assert.equal(configurazione.downsample.voxel_size, 25,
  "il valore resta in memoria e lo portera' su disco la prima modifica riuscita");
assert.equal(voxel.messaggio.hidden, false, "il server non ha risposto e lo schermo tace");
assert.match(voxel.messaggio.textContent, /il server non ha risposto/);
assert.equal(voxel.input.getAttribute("aria-invalid"), "true");

knn.input.value = "31";
risponde = accetta({ downsample: { voxel_size: 25 }, normals: { knn: 31 } });
await knn.input.scatena("change");
assert.equal(richieste.length, 2, "il banco non ha mandato le due PUT che sta guardando");
const ultima = richieste[1].corpo;
assert.equal(ultima.normals.knn, 31, "la modifica dell'utente non arriva piu' a destinazione");
assert.equal(ultima.downsample.voxel_size, 25,
  "l'utente ha toccato knn e sul disco cambia anche voxel_size, che non ha mai visto");
""")


# --------------------------------------------------------------------------
# La didascalia del ritaglio.
# --------------------------------------------------------------------------


def test_la_didascalia_del_ritaglio_dice_di_quale_numero_si_tratta(tmp_path):
    """`/api/crop` dice fin dove arriva l'anteprima con `completo`. Quando lo
    step 2 prosegue oltre il ritaglio con i piani e i cluster ne tiene molti
    meno — 5 602 di anteprima contro 84 su una nuvola di prova — quindi
    affermare li' che quello e' il conteggio dello step 2 e' un numero falso con
    una didascalia che lo garantisce.

    Il controllo guarda le due affermazioni, non le parole con cui sono fatte:
    incompleta deve dire che lo step prosegue **e non** affermare la
    coincidenza; completa deve affermarla e non parlare di seguito. La
    didascalia unica di prima — quella che afferma sempre — fallisce il primo
    caso, che e' esattamente il difetto che questa riga chiude.
    """
    pezzi = [p.split(";", 1)[0] for p in _modulo().split("esito.textContent =")[1:]]
    espressione = next(p for p in pezzi if "points_after" in p)
    uscita = _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
                     # Le parentesi non sono ornamento: l'espressione comincia
                     # con un a capo, e `return` seguito da un a capo torna
                     # undefined invece di quello che c'e' scritto sotto.
                     "function didascalia(corpo) { return (" + espressione + "); }\n" + """
const parziale = didascalia({ points_after: 5602, completo: false });
const intero = didascalia({ points_after: 84, completo: true });
const COINCIDENZA = /è quanti ne terrebbe lo step 2/;
const SEGUITO = /prosegue/;
assert.match(parziale, SEGUITO,
  "l'anteprima non e' tutto lo step 2 e la didascalia non dice che lo step prosegue");
assert.doesNotMatch(parziale, COINCIDENZA,
  "l'anteprima non e' tutto lo step 2 e la didascalia la spaccia per tale");
assert.match(intero, COINCIDENZA,
  "l'anteprima e' tutto lo step 2 e la didascalia non lo dice piu'");
assert.doesNotMatch(intero, SEGUITO,
  "l'anteprima e' tutto lo step 2 e la didascalia se ne scusa");
assert.ok(parziale.includes((5602).toLocaleString("it")), "il numero non compare");
assert.ok(intero.includes((84).toLocaleString("it")), "il numero non compare");
for (const testo of [parziale, intero]) {
  assert.match(testo, /crop_min e crop_max sono stati scritti/,
    "il bottone dice Applica: chi lo preme deve sapere che ha scritto");
}
""")
    assert uscita == ""


# --------------------------------------------------------------------------
# Rilievo 1 (giro 2): l'ordine fra risposte, alla granularita' del campo.
#
# `superata(ordine)` lega la guardia alla generazione del clic che ha aperto
# il pannello: due battute sullo stesso campo, nello stesso pannello, portano
# lo stesso `ordine`, e la guardia non le distingue. E' il terzo requisito
# dello stesso difetto gia' corretto due volte su questo file (`generazione`
# per i clic, `ultimaGeometria` per le richieste di geometria) — qui la
# granularita' giusta e' il campo, non il pannello.
# --------------------------------------------------------------------------


def test_apriBattuta_apre_in_ordine_e_non_confonde_due_campi(tmp_path):
    """La meta' pura della guardia, eseguita da sola: sale di uno per campo,
    comincia da 1, e due campi diversi non condividono il contatore. L'altra
    meta' — l'uso vero dentro `scriviParametro` — e' nel banco piu' sotto."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
            "let ultimaBattutaDelCampo = new Map();\n"
            + _funzioni("apriBattuta") + """
assert.equal(apriBattuta("downsample.voxel_size"), 1, "la prima battuta di un campo non parte da 1");
assert.equal(apriBattuta("downsample.voxel_size"), 2, "la battuta sullo stesso campo non sale");
assert.equal(apriBattuta("normals.knn"), 1, "due campi diversi condividono il contatore");
assert.equal(ultimaBattutaDelCampo.get("downsample.voxel_size"), 2,
  "la mappa non tiene l'ultima battuta registrata per quel campo");
assert.equal(ultimaBattutaDelCampo.get("normals.knn"), 1);
""")


def test_scriviparametro_guarda_anche_la_battuta_del_campo_per_iscritto():
    """Il contratto per iscritto, cosi' una modifica futura che tolga la
    guardia lo dice senza dover eseguire `node`. Non basta da solo — una
    guardia scritta e resa inerte passerebbe questo controllo — percio' il
    controllo che conta e' quello che esegue, subito sotto."""
    corpo = _sorgente_di("scriviParametro", _modulo())
    assert "apriBattuta(chiave)" in corpo, "la battuta non si apre piu' per campo"
    assert "superata(battuta, ultimaBattutaDelCampo.get(chiave))" in corpo, (
        "la guardia sulla battuta del campo e' sparita: due scritture sullo stesso "
        "campo tornano a condividere solo l'ordine del pannello, ed e' esattamente "
        "il difetto tornato una quarta volta"
    )


def test_la_risposta_della_battuta_piu_vecchia_sullo_stesso_campo_non_vince(tmp_path):
    """L'ingresso concreto di Rilievo 1. Due battute sullo stesso campo, nello
    stesso pannello aperto (stesso `ordine`): la prima e' lenta, la seconda
    parte dopo e arriva prima. Senza la guardia per campo, la risposta della
    prima — che descrive un valore piu' vecchio di quello che l'utente ha gia'
    scritto — vince perche' arriva per ultima, e la prossima PUT su un altro
    campo la riporterebbe sul disco sopra il valore vero.

    Il controllo che smentisce e' nello stesso banco: due scritture in ordine
    normale (nessun accavallamento) devono continuare a funzionare, altrimenti
    la guardia rifiuta tutto e non e' una correzione.
    """
    _esegui(tmp_path, _banco_del_campo() + """
// --- il caso che rompeva: risposte invertite -------------------------------
configurazione = { downsample: { voxel_size: 1 } };
const campo = apriCampo("downsample", "voxel_size");

let risolvi1, risolvi2;
const risposte = [
  new Promise((r) => { risolvi1 = r; }),
  new Promise((r) => { risolvi2 = r; }),
];
let chiamata = 0;
globalThis.fetch = async (percorso, opzioni) => {
  richieste.push({ percorso, corpo: JSON.parse(opzioni.body) });
  return risposte[chiamata++];
};

campo.input.value = "1";
const primaBattuta = scriviParametro("downsample", "voxel_size", campo.input, campo.messaggio, generazione);
campo.input.value = "2";
const secondaBattuta = scriviParametro("downsample", "voxel_size", campo.input, campo.messaggio, generazione);

// La risposta della seconda battuta (l'ultima che l'utente ha davvero
// scritto) arriva per prima; quella della prima, piu' vecchia, rientra dopo.
risolvi2({ ok: true, status: 200, json: async () => ({ downsample: { voxel_size: 2 } }) });
await secondaBattuta;
risolvi1({ ok: true, status: 200, json: async () => ({ downsample: { voxel_size: 1 } }) });
await primaBattuta;

assert.equal(configurazione.downsample.voxel_size, 2,
  "la risposta della battuta vecchia ha scritto sopra quella nuova in memoria");
assert.equal(campo.input.value, "2",
  "il campo torna a mostrare la battuta vecchia dopo che l'utente ha gia' scritto la nuova");

// --- il controllo che smentisce: ordine normale, nessun accavallamento -----
globalThis.fetch = async (percorso, opzioni) => {
  richieste.push({ percorso, corpo: JSON.parse(opzioni.body) });
  return { ok: true, status: 200, json: async () => ({ downsample: { voxel_size: 3 } }) };
};
campo.input.value = "3";
await scriviParametro("downsample", "voxel_size", campo.input, campo.messaggio, generazione);
assert.equal(configurazione.downsample.voxel_size, 3,
  "una scrittura normale, senza accavallamento, smette di funzionare");
assert.equal(campo.input.value, "3");
""")


def test_scriviparametro_200_illeggibile_non_va_in_crash_ne_ripristina_ne_cachea(tmp_path):
    """Rilievo 2 sul terzo `.json()`: la conferma di una PUT accettata. Tre
    corpi spazzatura — JSON invalido, JSON valido ma senza il blocco appena
    scritto, e il `null` letterale — non devono far sollevare il gestore, non
    devono ripristinare `precedente` (la PUT e' stata accettata: il valore
    vecchio in memoria scriverebbe sopra quello vero alla prossima modifica di
    un altro campo, lo stesso guasto di BL-2), e non devono entrare in
    `configurazione`.

    Il `null` letterale e' il caso che la correzione di questo giro chiude:
    prima, `salvata === undefined` lasciava passare `null`, e
    `salvata[blocco]` (senza `?.` sul primo livello — solo il secondo,
    `?.[nome]`, era protetto) sollevava fuori da ogni catch.
    """
    _esegui(tmp_path, _banco_del_campo() + """
for (const corpoRotto of [
  async () => { throw new SyntaxError("non e' JSON"); },
  async () => ({ normals: { knn: 30 } }),  // valido, ma senza il blocco downsample
  async () => null,                        // null letterale: mai legittimo qui
]) {
  configurazione = { downsample: { voxel_size: 9 } };
  const campo = apriCampo("downsample", "voxel_size");
  campo.input.value = "12";
  risponde = async () => ({ ok: true, status: 200, json: corpoRotto });
  await campo.input.scatena("change");
  assert.equal(configurazione.downsample.voxel_size, 12,
    "un 200 accettato ma illeggibile ripristina un valore che il server ha gia' scritto");
  assert.equal(campo.messaggio.hidden, false, "un 200 illeggibile non deve restare muto");
  assert.match(campo.messaggio.textContent, /non ne ha confermato/);
}
""")


# --------------------------------------------------------------------------
# Rilievo 2, il resto del censimento: caricaStato e apriDettaglio.
# --------------------------------------------------------------------------


def test_corpoLetto_distingue_illeggibile_da_null(tmp_path):
    """La difesa unica che protegge i sei punti di `app.js` che leggevano
    `risposta.json()` senza guardia (il censimento e' nel rapporto). `undefined`
    marca "non si legge"; `null` resta `null`, perche' e' cio' che il server ha
    davvero risposto — la stessa distinzione che `valoreScritto` fa sui campi
    nullabili."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n" + _funzioni("corpoLetto") + """
const buono = { json: async () => ({ a: 1 }) };
assert.deepEqual(await corpoLetto(buono), { a: 1 }, "un corpo buono non arriva piu' intatto");
const nullo = { json: async () => null };
assert.equal(await corpoLetto(nullo), null, "un null vero diventa qualcos'altro");
const rotto = { json: async () => { throw new SyntaxError("non e' JSON"); } };
assert.equal(await corpoLetto(rotto), undefined, "il corpo illeggibile continua a sollevare fuori da qui");
""")


def test_ogni_lettura_di_un_corpo_passa_da_corpoLetto():
    """Il censimento per iscritto: `corpoLetto()` e' la difesa unica, e ogni
    punto che legge un corpo deve passare da li'. Un settimo punto aggiunto
    domani con `.json()` diretto invece di `corpoLetto()` torna a rompere il
    gestore su un 200 spazzatura senza che nessuno se ne accorga leggendo — e
    questo controllo lo dice senza dover eseguire `node`.

    La sottostringa letterale `.json()` si aggira scrivendo `r.json\\n()` (la
    chiamata avviene lo stesso, verificato eseguendo in node): il controllo
    tollera spazi e a capo fra `.json` e le parentesi, cosi' quella grafia
    specifica non passa piu' inosservata. Restano fuori — dichiarato, non
    taciuto — l'accesso indicizzato (`r["json"]()`, `r[j]()`) e la chiamata
    indiretta (`r.json.call(r)`), che nessuna forma testuale di questo
    controllo puo' distinguere da codice legittimo che non tocca affatto
    `.json`. Il bypass piu' realistico non e' nessuno di questi tre — e' il
    modello `.text()` + `JSON.parse()` gia' presente in `ragioneDelRifiuto`,
    copiato su un settimo punto: lo controlla il test qui sotto.
    """
    modulo = _modulo()
    corpo_funzione = _sorgente_di("corpoLetto", modulo)
    resto = modulo.replace(corpo_funzione, "", 1)
    assert resto != modulo, "corpoLetto() e' sparita dal modulo: non si estrae piu' il suo corpo"
    codice = _senza_commenti_js(resto)
    assert not re.search(r"\.json\s*\(\s*\)", codice), (
        "un punto legge risposta.json() direttamente invece di passare da corpoLetto()"
    )


def test_nessun_punto_oltre_ragioneDelRifiuto_legge_un_corpo_con_text():
    """Il bypass realistico del controllo sopra: non una grafia equivalente
    di `.json()` scritta apposta per aggirarlo, ma il modello gia' presente
    nello stesso file — `ragioneDelRifiuto` legge con `.text()` piu'
    `JSON.parse()`, non con `.json()` — copiato domani su un settimo punto,
    naturalmente, perche' e' li' e nello stesso stile. Se quel settimo punto
    dimenticasse il `try/catch` che `ragioneDelRifiuto` ha, romperebbe il
    gestore esattamente come il difetto che questo giro chiude, senza che
    lo scanner sui `.json()` se ne accorga: quello scanner non contiene
    `.json()` in nessuna forma.

    Il controllo e' grosso apposta: vieta `.text()` fuori da `corpoLetto` e
    `ragioneDelRifiuto` senza distinguere se prosegue con `JSON.parse()` o
    no, perche' la distinzione fine e' esattamente il punto cieco che ha
    aggirato la versione precedente — un settimo punto scritto con `.text()`
    e basta, senza `JSON.parse()`, sarebbe comunque un modo nuovo di leggere
    un corpo fuori dalla difesa unica.
    """
    modulo = _modulo()
    corpo_corpoLetto = _sorgente_di("corpoLetto", modulo)
    corpo_ragione = _sorgente_di("ragioneDelRifiuto", modulo)
    resto = modulo.replace(corpo_corpoLetto, "", 1).replace(corpo_ragione, "", 1)
    assert resto != modulo, "una delle due funzioni ammesse e' sparita: non si estrae piu' il suo corpo"
    codice = _senza_commenti_js(resto)
    assert ".text(" not in codice, (
        "un punto fuori da corpoLetto e ragioneDelRifiuto legge un corpo con .text(): "
        "se prosegue con JSON.parse() senza il try/catch di ragioneDelRifiuto, e' lo stesso "
        "difetto che questo giro doveva chiudere, per una grafia diversa da .json()"
    )


def _banco_di_caricaStato() -> str:
    """`caricaStato` e' l'unica tratta senza `ordine` (parte una volta sola
    all'avvio, non da un clic — vedi `test_ogni_tratta_che_interroga_il_server`
    in `test_server.py`, che la esclude per lo stesso motivo): qui si guarda
    solo che il suo `.json()`, il primo del censimento, non faccia cadere la
    pagina su un 200 spazzatura. `corpoLetto` e' estratta **dopo** `caricaStato`
    nello stesso ordine del file vero: se lo hoisting non reggesse, questo
    banco lo direbbe eseguendo, non ragionandoci sopra.
    """
    return _DOM + "let ultimiSteps = [];\n" + _funzioni(
        "caricaStato", "segnaStepAperto", "nuovaRiga", "disegnaStep", "dichiaraErrore", "corpoLetto",
    ) + """
let risponde = null;
globalThis.fetch = async () => risponde();
"""


def test_caricaStato_non_crolla_su_un_corpo_che_non_si_legge(tmp_path):
    """Tre grafie di spazzatura su un 200: JSON invalido, JSON valido ma
    senza `steps`, e il `null` letterale. Nessuna delle tre deve far
    sollevare `caricaStato` (la pagina cadrebbe bianca all'avvio, prima
    ancora che l'elenco degli step compaia) e le prime due devono dirlo a
    video, con lo stesso canale degli altri rifiuti. Il controllo che
    smentisce e' nello stesso banco: un corpo buono deve continuare a
    disegnare gli step.

    Il `null` letterale e' un caso a parte: `corpoLetto` lo lascia passare
    intatto per contratto (e' cio' che il server ha davvero risposto), ma un
    corpo `null` per intero non e' mai una risposta legittima di `/api/run` —
    solo un campo nullabile innestato lo sarebbe. Prima della correzione,
    `corpo === undefined` lasciava passare `null`, e `!Array.isArray(null.steps)`
    sollevava fuori da ogni catch.
    """
    _esegui(tmp_path, _banco_di_caricaStato() + """
risponde = async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("boom"); } });
await caricaStato();
assert.match(rigaErrore.textContent, /non si legge/, "il corpo illeggibile non dice niente a video");
assert.equal(document.getElementById("corsa").textContent, "",
  "un corpo illeggibile non deve scrivere corsa");

rigaErrore.textContent = "";
risponde = async () => ({ ok: true, status: 200, json: async () => null });
await caricaStato();
assert.match(rigaErrore.textContent, /non si legge/, "un null letterale fa sollevare caricaStato fuori da ogni catch");
assert.equal(document.getElementById("corsa").textContent, "",
  "un null letterale non deve scrivere corsa");

rigaErrore.textContent = "";
risponde = async () => ({ ok: true, status: 200, json: async () => ({ out_dir: "/tmp/corsa" }) });
await caricaStato();
assert.match(rigaErrore.textContent, /non si legge/,
  "un corpo senza l'elenco degli step non dice niente a video");

// --- il controllo che smentisce: un corpo buono deve continuare a funzionare
rigaErrore.textContent = "";
risponde = async () => ({ ok: true, status: 200, json: async () => ({ out_dir: "/tmp/corsa", steps: STEPS }) });
await caricaStato();
assert.equal(rigaErrore.textContent, "", "un corpo buono non deve mostrare errore");
assert.equal(document.getElementById("corsa").textContent, "corsa: /tmp/corsa",
  "la riga della testata non dice piu' che quel percorso e' la corsa aperta");
assert.equal(elenco.childElementCount, 3, "un corpo buono deve continuare a disegnare gli step");
""")


def _banco_di_apriDettaglio() -> str:
    """`apriDettaglio` intero, con le sue dipendenze vere: e' il punto in cui
    stanno quattro dei sei `.json()` del censimento (schema, config, metriche
    — le ultime due nella stessa guardia). `campoParametro`/`scriviParametro`
    servono solo perche' il ramo buono del pannello li chiama costruendo le
    righe; nessun banco qui li scatena.
    """
    return _DOM + _funzioni(
        "segnaStepAperto", "nuovaRiga", "disegnaStep", "dichiaraErrore", "fallisciDettaglio",
        "ragioneDelRifiuto", "serverMuto", "superata", "corpoLetto", "valoreScritto",
        "reso", "segnalaCampo", "apriBattuta", "scriviParametro", "cambiatoDalPredefinito",
        "campoParametro",
        "gruppoDelBlocco", "azioniDelloStep", "intestazioneDelloStep", "apriDettaglio",
    ) + """
// L'intestazione del pannello legge i nomi degli step da qui: in questi banchi
// resta vuota, e la funzione deve reggere lo stesso (titolo senza nome).
let ultimiSteps = [];
// ETICHETTE arriva dal DOM finto; PROPOSITI no, e l'intestazione lo legge.
const PROPOSITI = {};
let ultimaBattutaDelCampo = new Map();
let schemaParametri = null;
// apriDettaglio ora costruisce le sue azioni con azioniDelloStep, che legge
// questa variabile di modulo: nessun banco qui fa girare una corsa, resta ferma.
let corsaInCorso = false;
const ULTIMO_STEP = 11;
const richieste = [];
let risponde = {};
globalThis.fetch = async (percorso) => {
  richieste.push(percorso);
  return risponde[percorso]();
};
// Letto e non chiamato in questi banchi (numero e' sempre 1): apriDettaglio
// lo confronta comunque a ogni apertura, quindi deve esistere.
const STEP_CON_RITAGLIO = 2;
const SCHEMA_BUONO = { "1": { blocchi: ["input"], campi: { input: { path: { description: "percorso" } } } } };
const CONFIG_BUONA = { input: { path: "nuvola.ply" } };
const METRICHE_BUONE = {};
"""


def test_apriDettaglio_schema_illeggibile_non_avvelena_la_cache(tmp_path):
    """Il caso che l'addendum nomina esplicitamente: uno schema mezzo letto
    resterebbe in memoria per tutta la vita della pagina, perche'
    `schemaParametri` non e' piu' `null` e nessun clic successivo ritenterebbe
    la richiesta. Il controllo che smentisce e' nello stesso banco: dopo un
    fallimento, un secondo clic con uno schema buono deve ancora funzionare —
    provato solo perche' la cache e' rimasta vuota.

    Ripetuto anche sul `null` letterale: prima della correzione,
    `corpo === undefined` lasciava passare `null`, `schemaParametri = null`
    veniva assegnato comunque (la guardia non se ne accorgeva), e il primo
    clic successivo andava in crash differito su `schemaParametri[...]`
    invece di ritentare la richiesta.
    """
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("boom"); } }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /schema/, "il corpo illeggibile non nomina lo schema a video");
assert.equal(schemaParametri, null,
  "un corpo illeggibile e' finito comunque in cache: nessun clic successivo ritentera'");
assert.equal(document.getElementById("dettaglio").childElementCount, 0,
  "il pannello non e' stato svuotato dopo il fallimento");

risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => null }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /schema/, "un null letterale non nomina lo schema a video");
assert.equal(schemaParametri, null, "un null letterale e' finito in cache: nessun clic successivo ritentera'");

risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};
await apriDettaglio(1);
assert.equal(schemaParametri, SCHEMA_BUONO, "lo schema buono non e' stato memorizzato");
assert.ok(document.getElementById("dettaglio").childElementCount > 0,
  "il pannello non si e' ripreso con uno schema buono, dopo che il primo era fallito");
""")


def test_apriDettaglio_config_illeggibile_non_scrive_la_configurazione_di_modulo(tmp_path):
    """Un rischio in piu' rispetto a quanto l'addendum nomina: `configurazione`
    e' anch'essa una variabile di modulo che sopravvive fra un'apertura e
    l'altra, ed e' quella da cui riparte la prossima PUT di `scriviParametro`.
    Un corpo illeggibile non deve entrarci, altrimenti la prossima modifica di
    un campo qualsiasi partirebbe da un valore rotto invece che da quello
    dell'apertura precedente.

    Ripetuto sul `null` letterale: prima della correzione,
    `corpoConfig === undefined` lasciava passare `null`,
    `configurazione = null` veniva assegnato comunque, e la prossima
    `scriviParametro` sarebbe andata in crash differito su
    `configurazione[blocco]` invece di ripartire da un valore buono.
    """
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
configurazione = { input: { path: "valore-precedente.ply" } };
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("boom"); } }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /non si legge/, "il corpo illeggibile non dice niente a video");
assert.equal(configurazione.input.path, "valore-precedente.ply",
  "la configurazione di modulo e' stata sovrascritta da un corpo che non si legge: " +
  "la prossima PUT partirebbe da un valore rotto");
assert.equal(schemaParametri, SCHEMA_BUONO, "lo schema, gia' buono, non doveva essere ritoccato");

rigaErrore.textContent = "";
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => null }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /non si legge/, "un null letterale non dice niente a video");
assert.equal(configurazione.input.path, "valore-precedente.ply",
  "un null letterale ha sovrascritto la configurazione di modulo");
""")


def test_apriDettaglio_metriche_illeggibili_non_scrivono_la_configurazione_di_modulo(tmp_path):
    """Il verso simmetrico del controllo sopra. La guardia e' una condizione
    sola con un `||` fra `corpoConfig` e `corpoMetriche`: un mutante che
    rompesse solo il lato destro non si vedrebbe da un controllo dove a
    fallire e' la config. Qui la config e' buona e sono le metriche a essere
    spazzatura, comprese le metriche `null` per intero.
    """
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
configurazione = { input: { path: "valore-precedente.ply" } };
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError("boom"); } }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /non si legge/, "il corpo illeggibile non dice niente a video");
assert.equal(configurazione.input.path, "valore-precedente.ply",
  "la configurazione di modulo e' stata sovrascritta anche se solo le metriche erano illeggibili");

rigaErrore.textContent = "";
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => null }),
};
await apriDettaglio(1);
assert.match(rigaErrore.textContent, /non si legge/, "metriche null letterale non dicono niente a video");
assert.equal(configurazione.input.path, "valore-precedente.ply",
  "la configurazione di modulo e' stata sovrascritta anche se solo le metriche erano null");
""")


# --------------------------------------------------------------------------
# La quinta e la sesta tratta nella stessa condizione di `ultimaGeometria`:
# i rami di `apriDettaglio` che leggono schema e config+metriche hanno solo
# `ordine`/`generazione` come guardia — nessun contatore locale, quindi
# niente da rendere decorativo — ma quella guardia stessa non era mai stata
# provata da un test che aprisse davvero due pannelli sovrapposti.
# Verificato rimuovendola (worktree isolato): la suite intera restava 36
# passed su 36.
# --------------------------------------------------------------------------


def test_apriDettaglio_due_pannelli_sovrapposti_lo_schema_vecchio_non_scrive_sopra_il_nuovo(tmp_path):
    """`schemaParametri` e' una cache di modulo che parte `null`: il primo
    pannello aperto la va sempre a prendere. Se un secondo step si apre prima
    che la risposta arrivi, e la prima e' un rifiuto arrivato tardi, senza la
    guardia `fallisciDettaglio` svuoterebbe il pannello del secondo step gia'
    disegnato e gli toglierebbe il marchio — la stessa famiglia "risposta
    vecchia vince", per una strada diversa da `ultimaGeometria`.
    """
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
// Serve una voce anche per lo step 3: SCHEMA_BUONO del banco ne ha una sola,
// per lo step 1. Non lo step 2: e' STEP_CON_RITAGLIO nel banco, e farebbe
// costruire anche il pannello del ritaglio, non extratto qui.
const SCHEMA_DUE_STEP = { "1": SCHEMA_BUONO["1"], "3": SCHEMA_BUONO["1"] };
let filaSchema = [];
globalThis.fetch = async (percorso) => {
  if (percorso === "/api/schema") return new Promise((r) => filaSchema.push(r));
  return risponde[percorso]();
};
risponde = {
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};

// Primo pannello (step 1): schema non ancora in cache, resta in attesa.
const primoPannello = apriDettaglio(1);
// Secondo pannello (step 2), un clic dopo: schema ancora null quando parte,
// resta in attesa anche lui, con la propria richiesta.
generazione += 1;
const secondoPannello = apriDettaglio(3, generazione);
assert.equal(filaSchema.length, 2, "il secondo pannello non ha aperto una propria richiesta di schema");

// Lo schema del secondo pannello, il piu' recente, arriva per primo.
filaSchema[1]({ ok: true, status: 200, json: async () => SCHEMA_DUE_STEP });
await secondoPannello;
assert.equal(stepAperto, 3, "il secondo pannello non risulta aperto");
assert.ok(document.getElementById("dettaglio").childElementCount > 0,
  "il secondo pannello non si e' disegnato");

// Lo schema del primo, il piu' vecchio, rientra per ultimo: un rifiuto.
filaSchema[0]({ ok: false, status: 500, text: async () => JSON.stringify({ messaggio: "schema vecchio" }) });
await primoPannello;
assert.equal(stepAperto, 3,
  "il rifiuto dello schema del pannello vecchio ha tolto il marchio dal pannello nuovo");
assert.ok(document.getElementById("dettaglio").childElementCount > 0,
  "il rifiuto dello schema del pannello vecchio ha svuotato il pannello nuovo gia' disegnato");
""")


def test_apriDettaglio_due_pannelli_sovrapposti_la_config_vecchia_non_scrive_sopra_la_nuova(tmp_path):
    """Lo stesso caso sul ramo di config+metriche di `apriDettaglio`: schema
    gia' in cache per isolare la guardia sotto esame, e la config a
    gareggiare."""
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
// Serve una voce anche per lo step 3: SCHEMA_BUONO del banco ne ha una sola,
// per lo step 1. Non lo step 2: e' STEP_CON_RITAGLIO nel banco, e farebbe
// costruire anche il pannello del ritaglio, non extratto qui.
schemaParametri = { "1": SCHEMA_BUONO["1"], "3": SCHEMA_BUONO["1"] };
let filaConfig = [];
globalThis.fetch = async (percorso) => {
  if (percorso === "/api/config") return new Promise((r) => filaConfig.push(r));
  return risponde[percorso]();
};
risponde = {
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};

const primoPannello = apriDettaglio(1);
generazione += 1;
const secondoPannello = apriDettaglio(3, generazione);
assert.equal(filaConfig.length, 2, "il secondo pannello non ha aperto una propria richiesta di config");

filaConfig[1]({ ok: true, status: 200, json: async () => CONFIG_BUONA });
await secondoPannello;
assert.equal(stepAperto, 3, "il secondo pannello non risulta aperto");
assert.ok(document.getElementById("dettaglio").childElementCount > 0,
  "il secondo pannello non si e' disegnato");

filaConfig[0]({ ok: false, status: 500, text: async () => JSON.stringify({ messaggio: "config vecchia" }) });
await primoPannello;
assert.equal(stepAperto, 3,
  "il rifiuto della config del pannello vecchio ha tolto il marchio dal pannello nuovo");
assert.ok(document.getElementById("dettaglio").childElementCount > 0,
  "il rifiuto della config del pannello vecchio ha svuotato il pannello nuovo gia' disegnato");
""")


def test_i_bottoni_esegui_due_clic_sovrapposti_non_lasciano_vincere_il_rifiuto_vecchio(tmp_path):
    """Riga 836 di `app.js`: la seconda istanza che lo scanner strutturale
    segnala, mai nominata come buco distinto prima di questo giro. I due
    bottoni («Esegui questo step», «Esegui da qui in giu'») condividono
    `ordine` (la generazione del pannello, non del clic) e la stessa
    `rigaErrore`: cliccato uno, poi — mentre e' ancora in volo — l'altro, con
    le risposte invertite, il rifiuto del clic piu' vecchio arriverebbe per
    ultimo e scriverebbe sopra il messaggio del clic piu' recente, accusando
    l'azione sbagliata. Un contatore condiviso dai due bottoni, aperto a ogni
    clic su uno qualunque dei due, li distingue.
    """
    _esegui(tmp_path, _banco_di_apriDettaglio() + """
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};
await apriDettaglio(1);
// Per classe e non per posizione: il pannello si apre sull'intestazione dello
// step, e un indice fisso legherebbe questo controllo all'ordine dei blocchi.
const azioni = document.getElementById("dettaglio").figli.find((n) => n.className === "azioni");
const [questo, daQui] = azioni.figli;

// "da qui in giu'" chiede conferma al primo clic e non spara nessuna fetch:
// lo si arma qui, fuori dalla corsa cronometrata sotto, cosi' il clic che
// partecipa alla gara e' quello che davvero manda la richiesta.
await daQui.scatena("click");

let risolvi1, risolvi2;
const risposte = [
  new Promise((r) => { risolvi1 = r; }),
  new Promise((r) => { risolvi2 = r; }),
];
let chiamata = 0;
globalThis.fetch = async () => risposte[chiamata++];

// Clic 1 (piu' vecchio) su "da qui in giu'" (gia' armato, quindi spara subito
// senza chiedere una seconda conferma), poi clic 2 (piu' recente) su "questo
// step", mentre il primo e' ancora in volo. Nell'ordine opposto il clic su
// "questo step" disarmerebbe "da qui in giu'" prima che quest'ultimo possa
// leggere la propria conferma, un'interazione fra fratelli che il test sulla
// disarma copre per conto suo: qui la gara resta sui due clic che davvero
// partono in fretta.
const primoClic = daQui.scatena("click");
const secondoClic = questo.scatena("click");

// Il secondo clic e' rifiutato e arriva per primo.
risolvi2({ ok: false, status: 500, text: async () => JSON.stringify({ messaggio: "errore nuovo" }) });
await secondoClic;
assert.match(rigaErrore.textContent, /errore nuovo/, "il rifiuto del clic piu' recente non arriva a video");

// Il primo clic, piu' vecchio, e' rifiutato anche lui ma rientra per ultimo.
risolvi1({ ok: false, status: 500, text: async () => JSON.stringify({ messaggio: "errore vecchio" }) });
await primoClic;
assert.match(rigaErrore.textContent, /errore nuovo/,
  "il rifiuto del clic vecchio, arrivato per ultimo, ha scritto sopra quello nuovo");
assert.doesNotMatch(rigaErrore.textContent, /errore vecchio/,
  "il messaggio a video accusa un clic che l'utente ha gia' superato");

// --- il controllo che smentisce: un clic normale, senza accavallamento -----
chiamata = 0;
rigaErrore.textContent = "";
globalThis.fetch = async () => (
  { ok: false, status: 500, text: async () => JSON.stringify({ messaggio: "guasto" }) }
);
await questo.scatena("click");
assert.match(rigaErrore.textContent, /guasto/, "un clic normale, senza accavallamento, smette di funzionare");
""")


# --------------------------------------------------------------------------
# Il sesto punto del censimento: la conferma di /api/crop.
# --------------------------------------------------------------------------


def _banco_del_ritaglio() -> str:
    return _DOM + _funzioni(
        "superata", "ragioneDelRifiuto", "serverMuto", "corpoLetto", "dichiaraErrore", "pannelloRitaglio",
    ) + """
const vista = {
  ingombro: () => ({ min: [0, 0, 0], max: [1, 1, 1] }),
  ultimoBox: null,
  mostraBox(min, max) { this.ultimoBox = { min: [...min], max: [...max] }; },
};
// Come nel modulo vero: configurazione e' gia' popolata quando il pannello si
// costruisce, con crop_min/crop_max al loro default (null, core/config.py)
// finche' nessun ritaglio e' stato applicato.
configurazione = { segment: { crop_min: null, crop_max: null } };
let risponde = null;
globalThis.fetch = async () => risponde();
function apriPannello(ordine) {
  const contenitore = pannelloRitaglio(ordine);
  const applica = contenitore.figli.find((f) => f.tag === "button");
  const esito = contenitore.figli[contenitore.figli.length - 1];
  return { applica, esito };
}
"""


def test_il_pannello_del_ritaglio_mostra_il_box_persistito_quando_c_e(tmp_path):
    """Rimasto aperto da due revisioni: il pannello leggeva solo
    `vista.ingombro()`, il box **disegnato**, e mai
    `configurazione.segment.crop_min/max`, quello **scritto su disco**. Anche
    dopo che i due clic sovrapposti non si scavalcano piu' (il test sopra),
    l'utente non aveva modo di vedere che cosa fosse davvero persistito.

    I due valori possono divergere legittimamente, e il pannello li distingue
    cosi': `crop_min`/`crop_max` sono `null` (il default del modello,
    core/config.py) finche' nessun ritaglio e' mai stato applicato — solo
    allora l'ingombro disegnato e' l'unico punto di partenza sensato, ed e'
    quello che il primo blocco sotto prova. Una volta valorizzati, sono la
    fonte anche se la nuvola nel frattempo e' la stessa: e' cio' che il
    server ha davvero scritto, non una nuova lettura dell'ingombro — il
    secondo blocco lo dimostra con numeri apposta diversi dall'ingombro finto,
    cosi' un pannello che leggesse ancora `vista.ingombro()` per errore li
    tradirebbe.
    """
    _esegui(tmp_path, _banco_del_ritaglio() + """
// Prima di ogni applicazione: crop_min/crop_max sono null, il pannello
// riparte dall'ingombro disegnato.
apriPannello(generazione);
assert.deepEqual(vista.ultimoBox, { min: [0, 0, 0], max: [1, 1, 1] },
  "senza un ritaglio persistito il pannello non riparte piu' dall'ingombro disegnato");

// Dopo un'applicazione riuscita (o alla riapertura con una configurazione
// gia' scritta): il pannello mostra il persistito, non l'ingombro — apposta
// diverso qui sotto, per non poter combaciare per caso.
configurazione = { segment: { crop_min: [5, 6, 7], crop_max: [8, 9, 10] } };
apriPannello(generazione);
assert.deepEqual(vista.ultimoBox, { min: [5, 6, 7], max: [8, 9, 10] },
  "il pannello riaperto non mostra il box persistito nella configurazione, mostra ancora l'ingombro disegnato");
""")


def test_applica_il_ritaglio_200_illeggibile_non_va_in_crash(tmp_path):
    """Il sesto `.json()` del censimento: la conferma di `/api/crop`. Un 200
    illeggibile, o senza `points_after`, non deve far sollevare il gestore del
    bottone — il testo "ritaglio in corso" scritto poco prima (`esito`)
    resterebbe a video per sempre, il silenzio peggiore perche' promette una
    fine che non arriva mai. Lo stesso canale delle altre due uscite d'errore
    di questo bottone: `dichiaraErrore`, non `esito`.

    Il terzo caso e' il `null` letterale: `corpoLetto` lo lascia passare
    intatto per contratto (e' cio' che il server ha davvero risposto), ma un
    corpo `null` per intero non e' mai una risposta legittima di /api/crop —
    solo un campo nullabile innestato lo sarebbe. Prima della correzione,
    `corpo === undefined` lasciava passare `null` e la riga sotto
    (`corpo.points_after`) sollevava fuori da ogni catch.
    """
    _esegui(tmp_path, _banco_del_ritaglio() + """
for (const corpoRotto of [
  async () => { throw new SyntaxError("non e' JSON"); },
  async () => ({ completo: true }),  // valido, ma senza points_after
  async () => null,                  // null letterale: mai legittimo qui
]) {
  rigaErrore.textContent = "";
  const { applica } = apriPannello(generazione);
  risponde = async () => ({ ok: true, status: 200, json: corpoRotto });
  await applica.scatena("click");
  assert.match(rigaErrore.textContent, /non descrive il ritaglio/,
    "un 200 illeggibile non dice niente a video, e il bottone resta muto per sempre");
}
""")


def test_applica_il_ritaglio_fallito_non_lascia_il_messaggio_in_corso_a_video(tmp_path):
    """Rilievo 2 di questo giro. Nel ramo di fallimento `esito` conservava
    «ritaglio in corso: la prima volta rilegge la nuvola piena, circa mezzo
    minuto.» scritto poco prima del `fetch`, mentre `rigaErrore` mostrava gia'
    il rifiuto: l'utente leggeva insieme "sto lavorando" e "e' fallito".
    Provato sulle due uscite d'errore del bottone (il rifiuto del server e il
    200 il cui corpo non descrive il ritaglio applicato), non solo su una:
    la stessa dimenticanza poteva ripetersi identica sulla seconda.
    """
    _esegui(tmp_path, _banco_del_ritaglio() + """
{
  const { applica, esito } = apriPannello(generazione);
  risponde = async () => (
    { ok: false, status: 422, text: async () => JSON.stringify({ messaggio: "box non valido" }) }
  );
  await applica.scatena("click");
  assert.equal(esito.textContent, "",
    "'ritaglio in corso' resta a video accanto all'errore del server");
  assert.match(rigaErrore.textContent, /box non valido/, "il rifiuto del server non arriva a video");
}
{
  const { applica, esito } = apriPannello(generazione);
  risponde = async () => ({ ok: true, status: 200, json: async () => ({ completo: true }) });
  await applica.scatena("click");
  assert.equal(esito.textContent, "",
    "'ritaglio in corso' resta a video accanto all'errore sul corpo illeggibile");
  assert.match(rigaErrore.textContent, /non descrive il ritaglio/, "il corpo illeggibile non arriva a video");
}
""")


def test_applica_il_ritaglio_due_clic_sovrapposti_lascia_vincere_l_ultimo(tmp_path):
    """Rilievo 1, terza istanza sullo stesso file. `ordine` e' la generazione
    del pannello, condivisa da tutti i clic fatti mentre il pannello resta
    aperto: regolare il box e ricliccare «Applica» per affinarlo e' il flusso
    normale, non un incidente — e senza un contatore per clic la risposta del
    clic vecchio, arrivata per ultima, scrive sopra l'esito del clic nuovo.
    Stessa meccanica di `apriBattuta`: un contatore locale al pannello,
    aperto a ogni clic.
    """
    _esegui(tmp_path, _banco_del_ritaglio() + """
const { applica, esito } = apriPannello(generazione);

let risolvi1, risolvi2;
const risposte = [
  new Promise((r) => { risolvi1 = r; }),
  new Promise((r) => { risolvi2 = r; }),
];
let chiamata = 0;
globalThis.fetch = async () => risposte[chiamata++];

const primoClic = applica.scatena("click");
const secondoClic = applica.scatena("click");

// La risposta del secondo clic (l'ultimo box che l'utente ha davvero
// battuto) arriva per prima; quella del primo, piu' vecchio, rientra dopo.
risolvi2({ ok: true, status: 200, json: async () => ({ points_after: 99, completo: true }) });
await secondoClic;
risolvi1({ ok: true, status: 200, json: async () => ({ points_after: 1, completo: true }) });
await primoClic;

assert.match(esito.textContent, /^99\\s+punti/,
  "la risposta del clic vecchio ha scritto sopra l'esito del clic nuovo");
assert.doesNotMatch(esito.textContent, /^1\\s+punti/,
  "l'esito mostra ancora il numero del clic superato");

// --- il controllo che smentisce: un clic normale, senza accavallamento -----
chiamata = 0;
globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ points_after: 7, completo: true }) });
await applica.scatena("click");
assert.match(esito.textContent, /^7\\s+punti/, "un clic normale, senza accavallamento, smette di funzionare");
""")


# --------------------------------------------------------------------------
# Task 14: galleria di curazione. mostraEsperimento e' la stessa famiglia di
# guardia di mostraNuvolaDelloStep/mostraStep (Rilievo 1): un contatore
# fresco per clic, aperto prima della fetch e controllato dopo, prima di
# ogni scrittura. Lo scanner strutturale sopra non vede questa tratta —
# il click su #galleria-elenco chiama mostraEsperimento senza attenderla, e
# "nessuna await fetch nel corpo risolto" del gestore la lascia fuori dal suo
# raggio dichiarato — quindi la prova che il contatore e' controllato e non
# solo aperto sta qui, non nello scanner.
# --------------------------------------------------------------------------


def _banco_di_galleria() -> str:
    return _DOM + "const ORDINE_GALLERIA = [\"esito\"];\n" + _funzioni(
        "corpoLetto", "ragioneDelRifiuto", "serverMuto", "superata",
        "apriGalleria", "dichiaraErrore", "colonneOrdinate", "disegnaTabellaGalleria", "mostraEsperimento",
    ) + """
let ultimaGalleria = 0;
let risponde = [];
let chiamata = 0;
globalThis.fetch = async () => risponde[chiamata++]();
"""


def test_due_richieste_di_esperimento_sovrapposte_non_fanno_vincere_la_vecchia(tmp_path):
    """Due clic su due esperimenti — o due riaperture dello stesso — possono
    accavallarsi, e la risposta piu' vecchia non deve scrivere sopra la
    tabella piu' recente.

    Il contatore va aperto E controllato: `apriGalleria()` lasciato per
    decorazione con la guardia (`superata(richiesta, ultimaGalleria)`) tolta
    subito dopo resta invisibile allo scanner strutturale del file (vedi la
    sua stessa dichiarazione di limite, sopra) — verificato mutando cosi'
    questa coppia nel worktree di lavoro: lo scanner resta verde, solo
    questo test diventa rosso.
    """
    _esegui(tmp_path, _banco_di_galleria() + """
let risolvi1, risolvi2;
risponde = [
  () => new Promise((r) => { risolvi1 = r; }),
  () => new Promise((r) => { risolvi2 = r; }),
];

const vecchia = mostraEsperimento("muro");
const nuova = mostraEsperimento("lab_crop");

// La piu' recente arriva per prima.
risolvi2({
  ok: true,
  json: async () => ({
    nome: "lab_crop", fronte: 1,
    colonne: [{ chiave: "esito", etichetta: "esito" }],
    righe: [{ on_front: true }],
    celle: [["riuscito"]],
  }),
});
assert.equal(await nuova, true, "la richiesta piu' recente non risulta scritta");
assert.equal(
  document.getElementById("galleria-didascalia").testo,
  "lab_crop: 1 candidati, 1 sul fronte.",
  "la tabella non mostra l'esperimento appena arrivato",
);

// La piu' vecchia, rimasta in volo, rientra per ultima.
risolvi1({
  ok: true,
  json: async () => ({
    nome: "muro", fronte: 0,
    colonne: [{ chiave: "esito", etichetta: "esito" }],
    righe: [],
    celle: [],
  }),
});
assert.equal(await vecchia, false, "la richiesta vecchia risulta scritta: doveva essere scartata");
assert.equal(
  document.getElementById("galleria-didascalia").testo,
  "lab_crop: 1 candidati, 1 sul fronte.",
  "la risposta vecchia, arrivata per ultima, ha scritto sopra la tabella piu' recente",
);
""")


def test_mostraEsperimento_dichiara_il_rifiuto_del_server(tmp_path):
    """Un 4xx del server (server.py solleva FileNotFoundError su un nome che
    non esiste, il gestore generico lo traduce in {"errore", "messaggio"})
    e' un rifiuto come gli altri: finisce nel canale d'errore condiviso, non
    in un silenzio."""
    _esegui(tmp_path, _banco_di_galleria() + """
risponde = [() => ({
  ok: false, status: 400,
  text: async () => JSON.stringify({ messaggio: "nessun registro per l'esperimento fantasma" }),
})];
const scritto = await mostraEsperimento("fantasma");
assert.equal(scritto, true, "un rifiuto e' comunque una scrittura: la ragione va dichiarata");
assert.match(
  rigaErrore.textContent,
  /nessun registro per l'esperimento fantasma/,
  "il rifiuto del server non arriva nella regione d'errore",
);
""")


# --------------------------------------------------------------------------
# La fine di una corsa: exit_code e secondi arrivano e vanno detti.
# --------------------------------------------------------------------------


def test_la_riga_dell_esito_esiste_nel_markup_ed_e_una_regione_viva():
    """Come la regione role="alert": deve preesistere a cio' che annuncia.
    Creata nell'istante in cui ci si scrive dentro, l'annuncio non e'
    garantito."""
    markup = _senza_commenti_html(_markup())
    elemento = _elemento(markup, "esito")
    assert 'aria-live="polite"' in elemento, f"la riga dell'esito non e' viva: {elemento}"
    assert "hidden" not in elemento, f"hidden la toglie dall'albero: {elemento}"
    # E nella testata, prima delle tre colonne. «Non dentro #dettaglio» non si
    # prova tagliando il file a quel tag: la collocazione pericolosa — accanto
    # alla riga d'errore, dentro la colonna del dettaglio — sta *prima* del
    # punto di taglio e passerebbe (provato: la suite resta verde). Che l'esito
    # stia fuori dalla colonna che apriDettaglio riscrive e' l'unica ragione
    # per cui ha una regione tutta sua, e qui si guarda dov'e' davvero.
    assert markup.index('id="esito"') < markup.index("<main"), (
        "la riga dell'esito e' scesa nelle tre colonne, dove il pannello la puo' raggiungere"
    )


def test_la_fine_della_corsa_distingue_fallito_annullato_e_concluso(tmp_path):
    """Il rilievo peggiore del giro 3. `exit_code` e `annullato` sono nel carico
    SSE da quando esiste il worker, e il modulo leggeva solo `in_corso`: a uscita
    non nulla la riga che pulsa spariva e basta, e chi guardava non poteva
    distinguere «fallito» da «finito».

    Tre esiti, tre frasi diverse, e nessuna delle tre inventa un numero.
    """
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
const steps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido", secondi: 34.39 }];
""" + _funzioni("nomeDelloStep", "descrizioneDellaCorsa", "esitoDellaCorsa") + """
const rotto = esitoDellaCorsa({ step: 9, exit_code: 1, annullato: false, steps });
assert.equal(rotto.esito, null, "un fallimento non e' un esito neutro");
assert.match(rotto.errore, /Tetraedri/, "il nome dello step, non il suo numero");
assert.match(rotto.errore, /codice 1/, "il codice d'uscita e' l'unico indizio che il server manda");
assert.match(rotto.errore, /registro/, "senza un rimando, il motivo resta introvabile");

const fermo = esitoDellaCorsa({ step: 9, exit_code: -15, annullato: true, steps });
assert.equal(fermo.errore, null, "annullare e' una scelta dell'utente, non un guasto");
assert.match(fermo.esito, /annullat/, "e va detto");

const bene = esitoDellaCorsa({ step: 9, exit_code: 0, annullato: false, steps });
assert.equal(bene.errore, null);
assert.match(bene.esito, /34[.,]39/, "la durata misurata, che run_state gia' porta");

// L'accordo: nove degli undici nomi sono femminili, e il participio andava con
// il nome. «Lettura concluso» era la frase piu' in vista dell'applicazione.
// Il soggetto e' «esecuzione», fisso, quindi l'accordo non dipende dal nome.
for (const [caso, frase] of [["rotto", rotto.errore], ["fermo", fermo.esito], ["bene", bene.esito]]) {
  assert.doesNotMatch(frase, /\\b(concluso|annullato|fallito)\\b/, `accordo sbagliato in ${caso}: ${frase}`);
}

console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_una_corsa_su_piu_step_non_si_annuncia_col_nome_del_primo(tmp_path):
    """Misurato nel browser: «Esegui dallo step 1 all'11» annunciava «Lettura
    in corso» per l'intera pipeline — a quattro secondi dall'avvio diceva
    ancora Lettura, che ne era durata 0,03 — e alla fine «Lettura concluso in
    0,03 s» per una corsa che ne aveva impiegati dieci. Il numero piu' in vista
    dell'applicazione era il tempo di un altro lavoro.

    La durata dell'intervallo nessuno la misura: `secondi` e' quella del solo
    step di partenza. Tacere e' l'unica alternativa che non inventa (principio
    3), e vale finche' il worker non misura la corsa intera.
    """
    sorgente = _DOM + """
ETICHETTE["01_load"] = "Lettura";
ETICHETTE["11_export"] = "Esportazione";
const steps = [
  { numero: 1, chiave: "01_load", stato: "valido", secondi: 0.03 },
  { numero: 11, chiave: "11_export", stato: "valido", secondi: 2.5 },
];
""" + _funzioni("nomeDelloStep", "descrizioneDellaCorsa", "esitoDellaCorsa") + """
const intervallo = { step: 1, a_step: 11, exit_code: 0, annullato: false, steps };
assert.match(
  descrizioneDellaCorsa(intervallo).testo, /Lettura.*Esportazione/,
  "l'intervallo si annuncia ancora col nome del solo primo step",
);
const esito = esitoDellaCorsa(intervallo).esito;
assert.match(esito, /Esportazione/, `l'esito non nomina la coda della corsa: ${esito}`);
assert.doesNotMatch(esito, /0[.,]03/, `il tempo del primo step spacciato per quello della corsa: ${esito}`);

// Un solo step resta com'era: li' `secondi` misura davvero quella corsa.
const singolo = { step: 1, a_step: 1, exit_code: 0, annullato: false, steps };
assert.match(esitoDellaCorsa(singolo).esito, /0[.,]03/, "la durata di una corsa di un solo step e' sparita");

// Un frame senza a_step — un server vecchio, o un carico incompleto — torna al
// nome del capo invece di inventare un intervallo.
assert.equal(descrizioneDellaCorsa({ step: 1, steps }).testo, "Lettura");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_una_corsa_conclusa_senza_durata_non_ne_inventa_una(tmp_path):
    """Principio 3. `secondi` viene dal file di stato e puo' mancare: una corsa
    conclusa senza misura si dichiara conclusa e nient'altro. Uno zero, o un
    trattino formattato come un numero, sarebbe una precisione fabbricata."""
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
const steps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido" }];
""" + _funzioni("nomeDelloStep", "descrizioneDellaCorsa", "esitoDellaCorsa") + """
const senza = esitoDellaCorsa({ step: 9, exit_code: 0, annullato: false, steps });
assert.equal(
  senza.esito, "Tetraedri: esecuzione conclusa", `ha inventato una durata: ${senza.esito}`,
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_exit_code_null_o_assente_non_si_annuncia_affatto(tmp_path):
    """Un codice d'uscita mancante non e' un fallimento, ma non e' nemmeno una
    riuscita: si tace.

    La prova diceva prima l'opposto — «va detto concluso, non taciuto» — e la
    sua motivazione era un file di stato letto prima che il worker fissasse il
    codice. Quello stato non esiste piu': il worker scrive exit_code prima di
    dichiararsi fermo, quindi `in_corso: false` implica un codice gia' scritto,
    e questo ramo si percorre solo quando qualcosa e' andato storto nell'avvio.
    Li' «concluso» e' un falso successo su una corsa mai partita, che e' la
    famiglia di difetti per cui il ramo esiste. Il silenzio non afferma niente.
    """
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
const steps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido" }];
""" + _funzioni("nomeDelloStep", "descrizioneDellaCorsa", "esitoDellaCorsa") + """
const conNull = esitoDellaCorsa({ step: 9, exit_code: null, annullato: false, steps });
assert.equal(conNull.errore, null, "exit_code null non e' un fallimento");
assert.equal(conNull.esito, null, `una corsa mai partita si annuncia riuscita: ${conNull.esito}`);

const senzaCampo = esitoDellaCorsa({ step: 9, annullato: false, steps });
assert.equal(senzaCampo.errore, null, "exit_code assente non e' un fallimento");
assert.equal(
  senzaCampo.esito, null, `una corsa mai partita si annuncia riuscita: ${senzaCampo.esito}`,
);

// Un annullamento arriva con exit_code non nullo, ma la marcatura viene
// guardata per prima: il silenzio non deve avergliela portata via.
const annullata = esitoDellaCorsa({ step: 9, exit_code: null, annullato: true, steps });
assert.match(
  annullata.esito, /Tetraedri.*annullata/, "il silenzio ha inghiottito l'annullamento",
);

console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def _banco_del_fronte_di_discesa() -> str:
    """Il fronte di discesa con `apriDettaglio` VERO, non un finto.

    Un finto `apriDettaglio` che si limita a chiamare `dichiaraErrore(null)`
    sorveglia una cosa sola: che l'annuncio non torni nella riga d'errore.
    Non sorveglia che nessuno svuoti `#esito` — e il difetto vive proprio
    dentro `apriDettaglio`, quindi il finto lo escluderebbe per costruzione.
    Qui la funzione vera viene eseguita per intero, con le sue fetch e le sue
    attese, sopra il banco che gia' esiste per lei.
    """
    return _banco_di_apriDettaglio() + _funzioni(
        "nomeDelloStep", "descrizioneDellaCorsa", "esitoDellaCorsa", "mostraEsito",
        "spegniLeEsecuzioni", "aggiornaDaStato",
    ) + """
// disegnaStep vero e' gia' nel banco e scrive qui dentro; ultimiSteps e'
// dichiarata la' dentro, perche' anche l'intestazione del pannello la legge.
// Una corsa stava girando: e' il fronte di discesa che si vuole esercitare.
let eraInCorso = true;
// null: il viewport non mostra niente, quindi non c'e' nessuna vista da
// ricaricare e ricaricaVista non deve essere chiamata.
let stepMostrato = null;
function ricaricaVista() { throw new Error("stepMostrato e' null: non c'era niente da ricaricare"); }
ETICHETTE["01_load"] = "Lettura";
const steps = [{ numero: 1, chiave: "01_load", stato: "fallito" }];
// Il pannello e' aperto, che e' lo stato normale: il bottone Esegui vive
// dentro quel pannello, quindi chi ha appena fatto partire una corsa lo ha
// aperto per forza. Lo step 1 e' quello che SCHEMA_BUONO descrive.
stepAperto = 1;
risponde = {
  "/api/schema": async () => ({ ok: true, status: 200, json: async () => SCHEMA_BUONO }),
  "/api/config": async () => ({ ok: true, status: 200, json: async () => CONFIG_BUONA }),
  "/api/metrics": async () => ({ ok: true, status: 200, json: async () => METRICHE_BUONE }),
};
// Il ciclo degli eventi fino in fondo: apriDettaglio non viene atteso dal
// gestore, e le sue tre risposte si risolvono in altrettanti giri.
const finoInFondo = async () => { for (let i = 0; i < 10; i += 1) await new Promise((r) => setTimeout(r, 0)); };
"""


def test_l_annuncio_del_fallimento_sopravvive_alla_riapertura_del_pannello(tmp_path):
    """Il reperto Critico della revisione di branch, e il caso che nessun banco
    eseguiva.

    `esitoDellaCorsa` era stata estratta apposta perche' fosse eseguibile, ed e'
    provata tre volte qui sopra. Ma il *cablaggio* — quale regione riceve il
    testo e chi la svuota subito dopo — stava dentro la freccia inline del
    gestore SSE, che `_sorgente_di` non sa estrarre. Scritto il fallimento nella
    riga d'errore del pannello, la riga successiva riapriva il pannello, e
    `apriDettaglio` svuotava quella regione dopo le proprie attese: l'allarme
    durava due fetch su localhost e spariva, lasciando a video qualcosa di
    indistinguibile da una corsa riuscita. E' il P0 della critica alla lettera,
    e il fronte di discesa scatta una volta sola: l'annuncio non torna piu'.

    Il controllo esegue il gestore vero **e apriDettaglio vero**, con un
    pannello aperto, e guarda che cosa resta scritto dopo che quest'ultimo ha
    ripreso dalle proprie attese. Con un finto apriDettaglio il controllo
    sorveglierebbe solo che l'annuncio non torni nella riga d'errore: il
    difetto vive dentro apriDettaglio, e un finto lo escluderebbe per
    costruzione.
    """
    _esegui(tmp_path, _banco_del_fronte_di_discesa() + """
aggiornaDaStato({ in_corso: false, step: 1, da_secondi: null, exit_code: 1, annullato: false, steps });

const riga = document.getElementById("esito");
assert.match(riga.textContent, /codice 1/, "il fallimento non e' stato annunciato affatto");

await finoInFondo();
// Il pannello si e' davvero riaperto: senza questo, un apriDettaglio che
// fallisse presto renderebbe il resto del controllo una formalita'.
assert.ok(
  document.getElementById("dettaglio").childElementCount > 0,
  "il pannello non e' stato riaperto: il caso non e' stato esercitato",
);
assert.equal(rigaErrore.textContent, "", "apriDettaglio non ha svuotato la riga d'errore");
assert.match(riga.textContent, /Lettura/, "l'annuncio non nomina piu' lo step");
assert.match(
  riga.textContent,
  /codice 1/,
  `l'annuncio del fallimento e' stato cancellato dalla riapertura del pannello: "${riga.textContent}"`,
);
assert.ok(
  riga.className.split(" ").includes("esito-fallito"),
  `un fallimento senza il proprio segno: "${riga.className}"`,
);

// Una corsa nuova pulisce, e quella che finisce bene non eredita il segno del
// fallimento precedente: senza il ramo negativo del toggle, ogni esito buono
// resterebbe colorato come un guasto per tutta la sessione.
aggiornaDaStato({ in_corso: true, step: 1, da_secondi: 2, exit_code: null, annullato: false, steps });
assert.equal(riga.textContent, "", "l'esito della corsa di prima descrive un lavoro diverso");
aggiornaDaStato({ in_corso: false, step: 1, da_secondi: null, exit_code: 0, annullato: false, steps });
await finoInFondo();
assert.match(riga.textContent, /Lettura.*conclusa/, "una corsa riuscita non e' annunciata");
assert.ok(
  !riga.className.split(" ").includes("esito-fallito"),
  `una corsa riuscita porta il segno del fallimento: "${riga.className}"`,
);

// E anche quando il pannello che si riapre fallisce. fallisciDettaglio e' il
// fratello di apriDettaglio e svuota la stessa riga d'errore: e' la seconda
// strada per lo stesso difetto, e il ramo buono da solo non la percorre. Il
// 500 su /api/config e' il caso che questo stesso ramo ha aggiunto — la
// configurazione sparita mentre il server gira.
risponde["/api/config"] = async () => ({
  ok: false,
  status: 500,
  text: async () => JSON.stringify({ messaggio: "la configurazione non c'e' piu'" }),
});
aggiornaDaStato({ in_corso: true, step: 1, da_secondi: 1, exit_code: null, annullato: false, steps });
stepAperto = 1;
aggiornaDaStato({ in_corso: false, step: 1, da_secondi: null, exit_code: 1, annullato: false, steps });
await finoInFondo();
assert.match(rigaErrore.textContent, /configurazione/, "il pannello non e' fallito: il ramo non e' stato percorso");
assert.match(
  riga.textContent,
  /codice 1/,
  `l'annuncio e' stato cancellato dal fallimento del pannello: "${riga.textContent}"`,
);
""")


def test_la_riga_di_stato_nomina_lo_step_invece_di_numerarlo(tmp_path):
    """Il reperto della critica che il piano aveva accolto e non consegnato: la
    colonna di sinistra mostra i nomi e questa riga diceva ancora «step 1».
    `nomeDelloStep` esiste per togliere le due lingue; qui era rimasta la
    seconda."""
    _esegui(tmp_path, _banco_del_fronte_di_discesa() + """
aggiornaDaStato({ in_corso: true, step: 1, da_secondi: 34.4, exit_code: null, annullato: false, steps });
const barra = document.getElementById("in-corso");
assert.match(barra.textContent, /^Lettura in corso/, `numera invece di nominare: "${barra.textContent}"`);
assert.ok(!/step 1/.test(barra.textContent), `dice ancora il numero nudo: "${barra.textContent}"`);
assert.match(barra.textContent, /34 s/, "il tempo misurato dal server non c'e' piu'");
""")


# --------------------------------------------------------------------------
# L'attesa della geometria: mezzo minuto in cui la vista mentiva.
# --------------------------------------------------------------------------


def test_la_vista_si_svuota_e_si_dichiara_prima_di_aspettare(tmp_path):
    """La finestra dei 27-34 secondi era l'unico punto in cui la vista e la sua
    didascalia potevano descrivere due step diversi: tela e conteggi restavano
    sullo step precedente mentre il pannello mostrava gia' il nuovo.

    Non e' una percentuale fabbricata: e' il nome di cio' che si sta leggendo.
    """
    sorgente = _DOM + """
ETICHETTE["09_tetrahedralize"] = "Tetraedri";
let svuotate = 0;
// Torna false: qui non c'era niente a video, ed e' il valore su cui
// spostaNelPrecedente decide se far scorrere anche il nome dello step.
const vista = { svuota() { svuotate += 1; return false; }, mostraPrecedente() {} };
let ultimiSteps = [{ numero: 9, chiave: "09_tetrahedralize", stato: "valido" }];
let vistaMostrata = null;
let vistaPrecedente = null;
let conteggiDiPrima = null;
const bottoneConfronta = document.getElementById("confronta");
""" + _funzioni(
        "nomeDelloStep", "scriviConteggi", "dichiaraCaricamento",
        "spostaNelPrecedente", "aggiornaConfronto", "spegniConfronto",
    ) + """
dichiaraCaricamento(9);
assert.equal(svuotate, 1, "la geometria di prima e' rimasta a video");
const didascalia = document.getElementById("conteggi").textContent;
assert.match(didascalia, /Tetraedri/, `la didascalia non nomina lo step: ${didascalia}`);
assert.equal(
  document.getElementById("viewport").getAttribute("aria-busy"), "true",
  "chi non vede la tela non sa che sta arrivando qualcosa",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_la_dichiarazione_precede_l_attesa_e_non_la_segue():
    """Il controllo di comportamento qui sopra passerebbe anche con la
    dichiarazione scritta dopo il `fetch`, che e' esattamente il difetto: una
    didascalia d'attesa che compare quando l'attesa e' finita non ha aspettato
    niente. Questo guarda l'ordine nel sorgente, come i controlli della regola
    delle generazioni.
    """
    corpo = _sorgente_di("mostraStep", _modulo())
    assert "dichiaraCaricamento(" in corpo, "mostraStep non dichiara piu' l'attesa"
    assert corpo.index("dichiaraCaricamento(") < corpo.index("await fetch"), (
        "la dichiarazione e' finita dopo l'attesa: comparirebbe quando non serve piu'"
    )


def test_la_configurazione_e_le_metriche_si_chiedono_insieme():
    """Erano due andate e ritorni in fila per due letture indipendenti: il
    pannello aspettava la somma di due latenze invece della maggiore."""
    corpo = _sorgente_di("apriDettaglio", _modulo())
    assert "Promise.all" in corpo, "le due letture sono tornate in fila"
    assert corpo.count("await fetch(\"/api/config\")") == 0, (
        "e' rimasta un'attesa separata su /api/config"
    )


# --------------------------------------------------------------------------
# Il ritaglio: cio' che il campo mostra e cio' che finisce sul disco.
# --------------------------------------------------------------------------


def _stub_ritaglio() -> str:
    """Il minimo che pannelloRitaglio tocca: la vista con un ingombro noto e una
    configurazione senza ritaglio gia' applicato."""
    return """
const vista = {
  ingombro: () => ({ min: [0, 0, 0], max: [10, 20, 30] }),
  mostraBox() {},
};
configurazione = { segment: { crop_min: null, crop_max: null } };
function dichiaraErrore() {}
function superata() { return false; }
const campiDi = (pannello) =>
  pannello.figli.flatMap((f) => f.figli).filter((n) => n.tag === "input");
const bottoneDi = (pannello) =>
  pannello.figli.find((n) => n.tag === "button");
"""


def test_un_campo_del_ritaglio_illeggibile_si_dichiara_e_spegne_applica(tmp_path):
    """Il silenzio era doppio. Il box smetteva di muoversi senza dire perche',
    e «Applica» restava acceso e mandava l'ultimo array valido: sul disco
    finiva un estremo che i sei campi non mostravano piu'. E' il principio 1
    rovesciato — si mostra un numero, se ne usa un altro, e nessun controllo lo
    smentisce."""
    sorgente = _DOM + _stub_ritaglio() + _funzioni("segnalaCampo", "pannelloRitaglio") + """
const pannello = pannelloRitaglio(0);
const campi = campiDi(pannello);
assert.equal(campi.length, 6, `sei estremi, non ${campi.length}`);
const applica = bottoneDi(pannello);
assert.notEqual(applica, undefined, "il bottone Applica non c'e' piu'");
assert.notEqual(applica.disabled, true, "nasce spento senza che nulla sia rifiutato");

campi[0].value = "abc";
await campi[0].scatena("input");
assert.equal(applica.disabled, true, "Applica manderebbe un valore che il campo non mostra");
assert.ok(
  campi[0].className.split(" ").includes("campo-rifiutato"),
  `il rifiuto non ha un canale visivo: ${campi[0].className}`,
);
assert.equal(campi[0].getAttribute("aria-invalid"), "true", "e nessun canale per chi non vede");

campi[0].value = "1.5";
await campi[0].scatena("input");
assert.equal(applica.disabled, false, "corretto il campo, Applica resta spento per sempre");
assert.equal(campi[0].getAttribute("aria-invalid"), null, "il rifiuto risolto resta a video");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_solo_campo_rotto_su_sei_basta_a_spegnere_applica(tmp_path):
    """Il contatore e' per campo, non un booleano: risolto uno dei due rifiuti,
    un booleano avrebbe riacceso il bottone con l'altro campo ancora rotto."""
    sorgente = _DOM + _stub_ritaglio() + _funzioni("segnalaCampo", "pannelloRitaglio") + """
const pannello = pannelloRitaglio(0);
const campi = campiDi(pannello);
const applica = bottoneDi(pannello);
campi[0].value = "abc";
await campi[0].scatena("input");
campi[3].value = "";
await campi[3].scatena("input");
campi[0].value = "1";
await campi[0].scatena("input");
assert.equal(applica.disabled, true, "un campo e' ancora vuoto e Applica si e' riacceso");
console.log("ok");
"""


# --------------------------------------------------------------------------
# La galleria: otto colonne in 22rem, e l'impronta che le sfondava tutte.
# --------------------------------------------------------------------------


def test_la_didascalia_della_galleria_sta_fuori_dal_riquadro_che_scorre():
    """Stava dentro .galleria-tabella, che ha overflow-x: auto. Scorrendo a
    destra per leggere i numeri, «11 candidati, 1 sul fronte» usciva dallo
    schermo insieme all'impronta: si perdeva insieme il conto e l'identita'
    delle righe."""
    markup = _senza_commenti_html(_markup())
    assert 'id="galleria-didascalia"' in markup, "la didascalia non ha un posto proprio"
    assert markup.index('id="galleria-didascalia"') < markup.index('id="galleria-tabella"'), (
        "la didascalia e' finita dopo il riquadro che scorre"
    )


def test_il_riquadro_che_scorre_e_raggiungibile_da_tastiera():
    """Lo stesso difetto per cui #registro ha un tabindex e otto righe di
    commento: un contenitore che scorre e non contiene nulla di focalizzabile
    e' irraggiungibile senza mouse su Chrome (WCAG 2.1.1, livello A)."""
    elemento = _elemento(_senza_commenti_html(_markup()), "galleria-tabella")
    assert 'tabindex="0"' in elemento, f"irraggiungibile senza mouse: {elemento}"
    assert "aria-label" in elemento, f"raggiungibile e senza nome: {elemento}"


def test_l_ordine_delle_colonne_mette_l_impronta_in_coda(tmp_path):
    """L'insieme resta quello di report._COLUMNS — si sceglie per chiave, e una
    colonna che l'ordine non nomina compare comunque — cambia il verso di
    lettura. L'indice originale torna insieme alla colonna, perche' e' quello
    con cui si indicizzano le celle della riga."""
    sorgente = _DOM + _funzioni("colonneOrdinate") + """
const ORDINE_GALLERIA = [
  "outcome", "thickness_error", "tets", "over", "dihedral", "duration_s", "axes", "fingerprint",
];
const colonne = [
  { chiave: "fingerprint", etichetta: "impronta" },
  { chiave: "axes", etichetta: "assi" },
  { chiave: "outcome", etichetta: "esito" },
  { chiave: "tets", etichetta: "tetraedri" },
  { chiave: "novita", etichetta: "colonna futura" },
];
const ordinate = colonneOrdinate(colonne, ORDINE_GALLERIA);
const chiavi = ordinate.map((v) => v.colonna.chiave);
assert.equal(chiavi[0], "outcome", `apre con ${chiavi[0]} invece che con l'esito`);
assert.equal(chiavi[chiavi.length - 1], "novita", "una chiave sconosciuta e' sparita invece di finire in coda");
assert.ok(chiavi.indexOf("fingerprint") > chiavi.indexOf("tets"), "l'impronta apre ancora la tabella");
assert.equal(chiavi.length, colonne.length, "il riordino ha perso o duplicato una colonna");
assert.equal(
  ordinate.find((v) => v.colonna.chiave === "fingerprint").indice, 0,
  "l'indice originale non torna: le celle finirebbero sotto la colonna sbagliata",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_la_riga_di_fronte_ha_un_canale_che_non_e_il_colore(tmp_path):
    """L'appartenenza al fronte di Pareto e' la risposta all'intera domanda
    della Fase 2, e a video era una tinta e un filetto: due canali visivi e
    nessun canale testuale (WCAG 1.4.1). Peggio, il filetto e' ancorato al
    bordo sinistro della riga ed esce dalla vista appena si scorre a destra,
    cioe' proprio quando i numeri diventano leggibili."""
    sorgente = _DOM + """
const ORDINE_GALLERIA = ["outcome", "fingerprint"];
""" + _funzioni("colonneOrdinate", "disegnaTabellaGalleria") + """
disegnaTabellaGalleria({
  nome: "lab_crop",
  fronte: 1,
  righe: [{ on_front: true }, { on_front: false }],
  colonne: [
    { chiave: "fingerprint", etichetta: "impronta" },
    { chiave: "outcome", etichetta: "esito" },
  ],
  celle: [["a".repeat(64), "ok"], ["b".repeat(64), "ok"]],
});
const tabella = document.getElementById("galleria-tabella").figli[0];
// figli[0] e' <caption>, figli[1] <thead>, figli[2] <tbody>.
// La <caption> resta — e' il nome accessibile della tabella — ma fuori vista:
// e' centrata sulla larghezza della TABELLA e non del riquadro, misurati 1013
// px dentro 319, cioe' un titolo che a riposo non e' a video affatto. E' lo
// stesso difetto gia' corretto spostando #galleria-didascalia fuori dal
// riquadro che scorre, rientrato da un'altra porta.
assert.equal(
  tabella.figli[0].className, "fuori-vista",
  "la didascalia della tabella e' tornata a scorrere fuori dal riquadro",
);
const righe = tabella.figli[2].figli;
const testi = righe.map((r) => r.figli.map((c) => c.textContent));
assert.notEqual(testi[0][0], testi[1][0], "le due righe non si distinguono per testo");
assert.ok(testi[0].join(" ").includes("fronte"), `nessun canale testuale: ${testi[0]}`);
const cellaImpronta = righe[0].figli[righe[0].figli.length - 1];
const breve = cellaImpronta.figli.find((f) => f.className === "impronta-breve");
assert.ok(breve, "il testo visibile dell'impronta non ha un nodo proprio");
assert.ok(
  breve.textContent.length <= 12,
  `l'impronta piena sfonda ancora la colonna: ${breve.textContent}`,
);
assert.equal(
  cellaImpronta.getAttribute("title"), "a".repeat(64),
  "l'impronta troncata ha perso il valore pieno",
);
// Il titolo raggiunge solo il mouse: senza un nodo .fuori-vista dentro la
// stessa cella, chi usa un lettore di schermo non raggiunge mai il valore
// intero.
const nascosta = cellaImpronta.figli.find((f) => f.className === "fuori-vista");
assert.ok(nascosta, "l'impronta intera non e' raggiungibile da un lettore di schermo");
assert.equal(nascosta.textContent, "a".repeat(64), "il nodo fuori-vista non porta il valore pieno");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


# --------------------------------------------------------------------------
# I due «Esegui»: un ceto, una portata dichiarata, e la corsa che li spegne.
# --------------------------------------------------------------------------


def test_un_solo_ceto_primario_e_la_portata_e_scritta_nell_etichetta(tmp_path):
    """«Esegui da qui in giu'» riscrive gli artefatti dallo step aperto
    all'undicesimo — minuti di calcolo e centinaia di MB — e aveva lo stesso
    aspetto e la stessa etichetta generica del bottone che carica una tabella
    di sola lettura. La portata non era scritta da nessuna parte."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep") + """
const azioni = azioniDelloStep(9, 0);
const bottoni = azioni.figli;
assert.equal(bottoni.length, 2, `due azioni, non ${bottoni.length}`);
const primari = bottoni.filter((b) => b.className.split(" ").includes("bottone-primario"));
assert.equal(primari.length, 1, "il ceto primario si e' moltiplicato o e' sparito");
assert.match(bottoni[1].textContent, /9/, "la portata non nomina lo step di partenza");
assert.match(bottoni[1].textContent, /11/, "ne' quello d'arrivo");
assert.ok(
  bottoni.every((b) => b.className.split(" ").includes("esecuzione")),
  "un'esecuzione senza la classe che la fa spegnere durante la corsa",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_le_esecuzioni_si_spengono_mentre_la_corsa_gira(tmp_path):
    """Restavano vive e si affidavano al 400 del worker: un rifiuto che si
    poteva evitare, e un bottone che risponde «no» non si distingue da uno che
    non ha fatto niente. Annulla lo faceva gia', dallo stesso carico."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep", "spegniLeEsecuzioni") + """
const azioni = azioniDelloStep(9, 0);
radice.append(azioni);
spegniLeEsecuzioni(true);
assert.ok(azioni.figli.every((b) => b.disabled === true), "un Esegui e' rimasto vivo a corsa viva");
spegniLeEsecuzioni(false);
assert.ok(azioni.figli.every((b) => b.disabled === false), "restano spenti a corsa finita");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_le_etichette_mostrate_portano_gli_accenti_italiani():
    """I sorgenti in ASCII sono una convenzione del repository; le stringhe
    proiettate davanti a una commissione non la ereditano. Il registro che
    PRODUCT.md dichiara — asciutto e accademico — non regge «Qualita»."""
    modulo = _modulo()
    assert '"Qualità superficie"' in modulo, "l'etichetta dello step 7 e' senza accento"
    assert '"Qualità volume"' in modulo, "l'etichetta dello step 10 e' senza accento"
    # Le due frasi piu' in vista del ramo: sono l'annuncio di un fallimento, e
    # arrivavano davanti alla commissione scritte «e' fallito». Senza i
    # commenti per la stessa ragione di «in giu'» qui sotto: un commento che
    # discute la frase non e' la frase.
    assert "esecuzione fallita (codice" in modulo, "l'annuncio del fallimento e' cambiato di forma"
    assert "e' fallit" not in _senza_commenti_js(modulo), (
        "l'annuncio del fallimento e' senza accento"
    )
    assert "Il motivo è nelle ultime righe" in modulo, "il rimando al registro e' senza accento"
    # Senza i commenti: «riscrive gli artefatti dall'N in giu'» e' una
    # spiegazione, non un'etichetta, e vietare la stringa nei commenti
    # vieterebbe la spiegazione. E' la stessa ragione per cui
    # _senza_commenti_js esiste.
    assert "in giu'" not in _senza_commenti_js(modulo), (
        "un'etichetta mostrata dice ancora «da qui in giu'» invece della portata"
    )


def test_il_bottone_non_primario_chiede_conferma_e_poi_si_resetta(tmp_path):
    """La conferma in linea ha almeno due stati e un ripristino: il primo clic
    non deve mandare niente, solo cambiare l'etichetta in una domanda; il
    secondo la manda e riporta l'etichetta a quella di partenza. Un bottone che
    non chiede mai conferma, o che la chiede sempre, supererebbe un controllo
    che guardasse solo l'esito finale."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep", "serverMuto", "superata") + """
let chiamate = 0;
globalThis.fetch = async () => { chiamate += 1; return { ok: true, status: 200 }; };
const azioni = azioniDelloStep(9, 0);
const [questo, daQui] = azioni.figli;
const etichettaIniziale = daQui.textContent;

await daQui.scatena("click");
assert.equal(chiamate, 0, "il primo clic sul bottone non primario ha gia' mandato la richiesta");
assert.notEqual(daQui.textContent, etichettaIniziale, "il primo clic non cambia l'etichetta in una domanda");

await daQui.scatena("click");
assert.equal(chiamate, 1, "il secondo clic non ha mandato la richiesta");
assert.equal(daQui.textContent, etichettaIniziale, "l'etichetta non torna quella di partenza dopo la conferma");

// Il ceto primario non chiede mai conferma: un solo clic basta.
await questo.scatena("click");
assert.equal(chiamate, 2, "il bottone primario chiede conferma, e non dovrebbe");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_bottone_armato_si_disarma_se_si_clicca_il_fratello(tmp_path):
    """Un armato che non si disarma mai e' peggio di nessuna conferma: se dopo
    aver armato "Esegui dallo step" l'utente cambia idea e clicca l'altro
    bottone, il primo deve tornare al riposo — non restare in attesa di un
    secondo clic che magari arriva molto piu' tardi, su un'intenzione diversa
    da quella che lo aveva armato."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep", "serverMuto", "superata") + """
let chiamate = 0;
globalThis.fetch = async () => { chiamate += 1; return { ok: true, status: 200 }; };
const azioni = azioniDelloStep(9, 0);
const [questo, daQui] = azioni.figli;
const etichettaIniziale = daQui.textContent;

await daQui.scatena("click");
assert.notEqual(daQui.textContent, etichettaIniziale, "il primo clic non arma la conferma");

// Cambio idea: si clicca l'altro bottone. E' primario, quindi spara subito.
await questo.scatena("click");
assert.equal(chiamate, 1, "il bottone primario non ha sparato al primo clic");
assert.equal(daQui.textContent, etichettaIniziale,
  "il clic sul fratello non ha disarmato la conferma rimasta accesa");

// Il controllo che smentisce: disarmato, un clic su daQui deve tornare a
// chiedere conferma, non sparare come se il "Confermi?" di prima valesse ancora.
await daQui.scatena("click");
assert.equal(chiamate, 1, "un clic su daQui subito dopo il disarmo ha sparato senza chiedere conferma");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_spegniLeEsecuzioni_disarma_la_conferma_rimasta_accesa(tmp_path):
    """Una corsa partita altrove disabilita i bottoni ma prima non toccava la
    spunta di conferma: riaccesi a fine corsa, un "Confermi?" dimenticato
    sparava al primo clic invece di chiederlo di nuovo — la corsa nel
    frattempo poteva anche essere finita male, e il primo clic dopo non era
    piu' la stessa decisione che aveva armato il bottone."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = false;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep", "spegniLeEsecuzioni", "serverMuto", "superata") + """
let chiamate = 0;
globalThis.fetch = async () => { chiamate += 1; return { ok: true, status: 200 }; };
const azioni = azioniDelloStep(9, 0);
radice.append(azioni);
const [questo, daQui] = azioni.figli;
const etichettaIniziale = daQui.textContent;

await daQui.scatena("click");
assert.notEqual(daQui.textContent, etichettaIniziale, "il primo clic non arma la conferma");

// Una corsa parte altrove: i bottoni si spengono, e la conferma deve sparire.
spegniLeEsecuzioni(true);
assert.equal(daQui.textContent, etichettaIniziale,
  "spegniLeEsecuzioni non ha disarmato la conferma rimasta accesa");

// A corsa finita si riaccendono: il primo clic deve chiedere di nuovo, non sparare.
spegniLeEsecuzioni(false);
await daQui.scatena("click");
assert.equal(chiamate, 0, "il primo clic dopo la corsa altrui ha gia' sparato invece di chiedere conferma");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_i_bottoni_nascono_spenti_se_una_corsa_gira_gia(tmp_path):
    """Un pannello aperto in mezzo a una corsa nasceva con i bottoni vivi: la
    riga che li disabilita alla costruzione non la esercita nessun banco che
    parte da corsaInCorso = false, che e' quello che fa ogni banco di questo
    file. La stessa forma di buco gia' vista nei Task 1 e 2 di questo piano:
    la riga che chiude il caso raro e' quella che nessun controllo esegue."""
    sorgente = _DOM + """
function dichiaraErrore() {}
let corsaInCorso = true;
const ULTIMO_STEP = 11;
""" + _funzioni("azioniDelloStep") + """
const azioni = azioniDelloStep(9, 0);
assert.ok(
  azioni.figli.every((b) => b.disabled === true),
  "un bottone nasce vivo mentre una corsa gia' gira altrove",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_l_ultimo_step_ha_un_nome_solo_e_lo_leggono_entrambe_le_etichette():
    """Il numero dell'ultimo step, ripetuto alla lettera in due etichette, e'
    un terzo posto da tenere allineato il giorno che la catena cambia
    lunghezza. Un nome solo, e le due etichette lo leggono invece di scrivere
    ciascuna il proprio 11."""
    modulo = _modulo()
    assert modulo.count("const ULTIMO_STEP = ") == 1, (
        "il numero dell'ultimo step non e' definito in un punto solo"
    )
    corpo = _sorgente_di("azioniDelloStep", modulo)
    assert corpo.count("${ULTIMO_STEP}") == 2, (
        "le due etichette non leggono entrambe lo stesso nome per l'ultimo step"
    )
    assert re.search(r"all'11\b", corpo) is None, (
        "un'etichetta scrive ancora il numero dell'ultimo step alla lettera"
    )


# --------------------------------------------------------------------------
# I predefiniti: erano sul filo e finivano nel cestino.
# --------------------------------------------------------------------------


def test_il_confronto_col_predefinito_e_sul_testo_reso(tmp_path):
    """Il campo mostra una stringa, e /api/schema serializza i predefiniti con
    default=str: un Path arriva come testo. Confrontare i valori grezzi
    segnerebbe come «cambiato» un parametro che nessuno ha toccato, solo perche'
    le due grafie dello stesso valore non sono lo stesso oggetto."""
    sorgente = _DOM + _funzioni("reso", "cambiatoDalPredefinito") + """
assert.equal(cambiatoDalPredefinito(9, 9), false, "lo stesso numero risulta cambiato");
assert.equal(cambiatoDalPredefinito(null, null), false, "due assenze risultano diverse");
assert.equal(cambiatoDalPredefinito(0.005, null), true, "un valore su un predefinito assente");
assert.equal(cambiatoDalPredefinito(9, 10), true, "due numeri diversi risultano uguali");
assert.equal(cambiatoDalPredefinito(false, false), false, "due booleani uguali");
assert.equal(cambiatoDalPredefinito([1, 2], [1, 2]), false, "due liste uguali");
assert.equal(cambiatoDalPredefinito([1, 2], [1, 3]), true, "due liste diverse");
// Scelta deliberata e non un caso sfuggito: il confronto e' sul testo reso, e
// un numero e la stessa cifra come stringa rendono lo stesso testo. Senza
// questa riga la decisione resta scritta solo in un commento.
assert.equal(cambiatoDalPredefinito(5, "5"), false, "un numero e la sua stringa risultano cambiati");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_il_blocco_apre_sui_cambiati_e_richiude_i_predefiniti(tmp_path):
    """Il fieldset `segment` rendeva undici campi di fila, `surface` nove: molto
    oltre i quattro elementi che si tengono in mente insieme. Il taglio non e'
    inventato — e' cio' che questa corsa ha spostato dal predefinito, che e'
    anche la sola domanda che un prodotto sulla riproducibilita' deve saper
    rispondere a colpo d'occhio."""
    sorgente = _DOM + """
configurazione = { segment: { method: "auto", knn: 20, soglia: 0.01 } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro", "gruppoDelBlocco") + """
const campi = {
  method: { description: "come segmentare", default: "auto" },
  knn: { description: "vicini", default: 30 },
  soglia: { description: "soglia", default: 0.01 },
};
const gruppo = gruppoDelBlocco("segment", campi, 0);
const pieghe = gruppo.figli.filter((f) => f.tag === "details");
assert.equal(pieghe.length, 1, "i predefiniti non si richiudono");
const aperti = gruppo.figli.filter((f) => f.tag === "label");
assert.equal(aperti.length, 1, `aperto ${aperti.length} campi invece del solo cambiato`);
assert.equal(pieghe[0].figli.filter((f) => f.tag === "label").length, 2, "due predefiniti nella piega");
assert.notEqual(pieghe[0].open, true, "la piega e' aperta pur avendo un cambiato fuori");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_blocco_tutto_al_predefinito_nasce_aperto(tmp_path):
    """Alla prima corsa nessun parametro e' stato spostato, e un pannello che
    mostra solo una riga da cliccare non insegna niente a chi apre lo step per
    la prima volta. E' l'utente successivo confermato da PRODUCT.md."""
    sorgente = _DOM + """
configurazione = { segment: { knn: 30, soglia: 0.01 } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro", "gruppoDelBlocco") + """
const gruppo = gruppoDelBlocco("segment", {
  knn: { description: "vicini", default: 30 },
  soglia: { description: "soglia", default: 0.01 },
}, 0);
const piega = gruppo.figli.find((f) => f.tag === "details");
assert.equal(piega.open, true, "il primo avvio si apre su una riga da cliccare");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_campo_cambiato_dichiara_il_predefinito_per_iscritto(tmp_path):
    """Non il solo colore: «che cosa ho spostato dallo stock» e' la storia che la
    tesi racconta, e chi non distingue le tinte deve poterla leggere."""
    sorgente = _DOM + """
configurazione = { segment: { knn: 20 } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro") + """
const riga = campoParametro("segment", "knn", { description: "vicini", default: 30 }, 0);
const testo = riga.figli.map((f) => f.textContent).join(" ");
assert.match(testo, /30/, `il predefinito non e' scritto da nessuna parte: ${testo}`);
assert.ok(riga.className.split(" ").includes("campo-cambiato"), "manca il canale visivo");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_campo_al_predefinito_non_porta_ne_classe_ne_segno(tmp_path):
    """Il rovescio del controllo sopra: un campo mai toccato non deve portare
    ne' la classe ne' la nota, altrimenti «cambiato» smette di significare
    qualcosa — un canale che si accende sempre non distingue piu' niente."""
    sorgente = _DOM + """
configurazione = { segment: { knn: 30 } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro") + """
const riga = campoParametro("segment", "knn", { description: "vicini", default: 30 }, 0);
assert.ok(!riga.className.split(" ").includes("campo-cambiato"), "un campo fermo porta il canale visivo");
const testo = riga.figli.map((f) => f.textContent).join(" ");
assert.doesNotMatch(testo, /cambiato/, `un campo fermo dichiara comunque un cambiamento: ${testo}`);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_il_segno_del_predefinito_rende_un_modello_come_lo_rende_il_confronto(tmp_path):
    """`analysis.material` e' un modello Pydantic e una lista e' una lista: il
    segno accanto al campo li passava per String(), che scrive «[object Object]»
    e «1,2,4». Sono i due testi che il commento di campoParametro vieta per
    nome trentaquattro righe sopra, e che nessuna lettura produce.

    Il confronto usava gia' la resa JSON: le due domande — «e' cambiato?» e «da
    che cosa?» — rispondevano in due lingue diverse, e la seconda si vede al
    primo parametro che un lavoro strutturale sposta.
    """
    sorgente = _DOM + """
configurazione = { analysis: { material: { name: "MATTONE", young: 900 }, assi: [1, 2, 4] } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro") + """
const modello = campoParametro("analysis", "material",
  { description: "materiale", default: { name: "MURATURA", young: 1500 } }, 0);
const testoModello = modello.figli.map((f) => f.textContent).join(" ");
assert.doesNotMatch(
  testoModello,
  /\\[object Object\\]/,
  `il segno rende un modello annidato con String(): ${testoModello}`,
);
assert.match(testoModello, /"name":\\s*"MURATURA"/, `il predefinito non si legge: ${testoModello}`);

const lista = campoParametro("analysis", "assi", { description: "assi", default: [0, 1, 2] }, 0);
const testoLista = lista.figli.map((f) => f.textContent).join(" ");
assert.match(testoLista, /\\[0,1,2\\]/, `la lista e' resa come una sequenza di virgole: ${testoLista}`);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_un_campo_obbligatorio_non_si_dichiara_cambiato(tmp_path):
    """`input.path` non ha un predefinito da cui scostarsi: il confronto lo
    trovava diverso da null e ogni corsa lo dichiarava «cambiato — predefinito:
    nessuno», su un campo che nessuno ha spostato da niente. E' il primo campo
    del primo step, quindi la frase falsa era anche la prima che si legge.

    «Dove il dato manca, si dichiara che manca»: qui manca il predefinito, non
    e' cambiato il valore.
    """
    sorgente = _DOM + """
configurazione = { input: { path: "lab_frame.pcd" }, segment: { knn: 20 } };
""" + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro", "gruppoDelBlocco") + """
const riga = campoParametro("input", "path",
  { description: "la nuvola", default: null, obbligatorio: true }, 0);
const testo = riga.figli.map((f) => f.textContent).join(" ");
assert.doesNotMatch(testo, /cambiato/, `un obbligatorio si dichiara cambiato: ${testo}`);
assert.match(testo, /obbligatorio/, `non dice che il predefinito manca: ${testo}`);
assert.ok(
  !riga.className.split(" ").includes("campo-cambiato"),
  "un obbligatorio porta il canale visivo del cambiamento",
);

// E non finisce nella piega: quel titolo dice «al valore predefinito», e un
// predefinito questo campo non ce l'ha.
const gruppo = gruppoDelBlocco("input", {
  path: { description: "la nuvola", default: null, obbligatorio: true },
}, 0);
assert.equal(
  gruppo.figli.filter((f) => f.tag === "details").length, 0,
  "l'obbligatorio e' stato richiuso fra i parametri al valore predefinito",
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_il_riquadro_della_galleria_prende_il_nome_dell_esperimento(tmp_path):
    """Il riquadro che scorre e' una region, e il suo nome era scritto fermo nel
    markup: cambiando esperimento, chi naviga da tastiera ci entrava e sentiva
    annunciare sempre lo stesso nome, cioe' nessuno dei due."""
    sorgente = _DOM + """
const ORDINE_GALLERIA = ["outcome"];
""" + _funzioni("colonneOrdinate", "disegnaTabellaGalleria") + """
const contenitore = document.getElementById("galleria-tabella");
contenitore.setAttribute("aria-label", "Registro dell'esperimento");
disegnaTabellaGalleria({
  nome: "lab_crop",
  fronte: 1,
  righe: [{ on_front: true }],
  colonne: [{ chiave: "outcome", etichetta: "esito" }],
  celle: [["ok"]],
});
assert.match(
  contenitore.getAttribute("aria-label"), /lab_crop/,
  `il nome annunciato non segue l'esperimento: ${contenitore.getAttribute("aria-label")}`,
);

// E anche verso un esperimento senza righe. Scritto dopo il ritorno anticipato
// del registro vuoto, il nome restava quello di prima: un nome fermo e
// generico e' meglio di uno attivamente sbagliato.
disegnaTabellaGalleria({
  nome: "muro",
  fronte: 0,
  righe: [],
  colonne: [{ chiave: "outcome", etichetta: "esito" }],
  celle: [],
});
assert.doesNotMatch(
  contenitore.getAttribute("aria-label"), /lab_crop/,
  `il nome dell'esperimento precedente e' rimasto: ${contenitore.getAttribute("aria-label")}`,
);
assert.match(
  contenitore.getAttribute("aria-label"), /muro/,
  `un registro vuoto perde il nome: ${contenitore.getAttribute("aria-label")}`,
);
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_l_ordine_della_galleria_nomina_le_stesse_colonne_del_registro():
    """`ORDINE_GALLERIA` e' un rispecchiamento scritto a mano delle chiavi di
    `report._COLUMNS`, e i tre banchi dell'interfaccia iniettano ciascuno la
    propria copia dell'elenco: scrivere «fingerprint» dentro un test non lega
    l'interfaccia al server, lega il test a se stesso.

    Rinominare una chiave in `report._COLUMNS` faceva scivolare quella colonna
    in coda in silenzio — cioe' riapriva il P1 che il branch esiste per
    chiudere — e disattivava insieme il troncamento dell'impronta, che si
    aggancia allo stesso letterale. La suite restava verde.
    """
    from meshrec.core import report

    trovato = re.search(r"const ORDINE_GALLERIA = \[(.*?)\];", _modulo(), flags=re.DOTALL)
    assert trovato is not None, "ORDINE_GALLERIA non e' piu' un elenco letterale"
    ordine = re.findall(r'"([^"]+)"', trovato.group(1))
    colonne = [chiave for chiave, _ in report._COLUMNS]
    assert set(ordine) == set(colonne), (
        "l'interfaccia e il registro non nominano le stesse colonne: "
        f"solo nell'interfaccia {sorted(set(ordine) - set(colonne))}, "
        f"solo nel registro {sorted(set(colonne) - set(ordine))}"
    )
    # set() da solo non vedrebbe una chiave scritta due volte.
    assert len(ordine) == len(colonne), f"una chiave compare piu' di una volta: {ordine}"
    # L'impronta e' 64 caratteri che non vanno a capo: in testa sfondava il
    # riquadro da 22rem e lasciava fuori schermo tutte le grandezze per cui il
    # pannello esiste. E il ramo che la tronca cerca lo stesso letterale.
    assert ordine[-1] == "fingerprint", f"l'impronta non e' piu' l'ultima colonna: {ordine}"
    assert '"fingerprint"' in _senza_commenti_js(_modulo()).split("colonneOrdinate", 1)[1], (
        "il troncamento dell'impronta non si aggancia piu' alla chiave"
    )


def test_il_registro_ha_un_nome_accessibile():
    """role="log" con tabindex="0" e nessun nome: il lettore di schermo
    annunciava «log» e basta. L'h2 accanto e' adiacente, non associato."""
    markup = _senza_commenti_html(_markup())
    elemento = _elemento(markup, "registro")
    assert "aria-labelledby=" in elemento, f"raggiungibile e senza nome: {elemento}"
    assert 'id="titolo-registro"' in markup, "il titolo a cui puntare non esiste"


def test_il_registro_non_strappa_in_fondo_chi_sta_leggendo():
    """Lo scorrimento era incondizionato, due volte al secondo per i 34 secondi
    di uno step: chi leggeva a meta' veniva riportato in fondo a ogni riga."""
    corpo = _modulo().split('flusso.addEventListener("riga"', 1)[1].split("\n});", 1)[0]
    assert "scrollTop = registro.scrollHeight" in corpo, "il registro non segue piu' la coda"
    assert "clientHeight" in corpo, "lo scorrimento e' tornato incondizionato"


def _corpo_riga_come_funzione() -> str:
    """Il corpo del gestore "riga", incapsulato in una funzione chiamabile dal
    banco: la controprova testuale sopra non basta, perche' una mutazione che
    scorre sempre lascia intatte entrambe le stringhe che quel test cerca."""
    corpo = _modulo().split('flusso.addEventListener("riga", (evento) => {', 1)[1]
    corpo = corpo.split("\n});", 1)[0]
    return "function aggiungiRiga(evento) {" + corpo + "}\n"


# Geometria vera, non un valore che nessun browser produce: 20 righe gia' nel
# registro (scrollHeight = 20, il banco lo lega al numero di figli), un
# clientHeight fisso e indipendente da quel conteggio (5, come una finestra che
# mostra 5 righe su 20), quindi uno scrollTop massimo reale di 15. 13 e 12
# stanno da parti opposte della soglia di 2 unita' (13+5=18 >= 20-2; 12+5=17 <
# 20-2): non estremi artificiali, il confine vero della disequazione.
_SETUP_REGISTRO_CON_SCORRIMENTO_VERO = """
const registro = document.getElementById("registro");
for (let n = 0; n < 20; n += 1) registro.append(document.createElement("div"));
registro.clientHeight = 5;
"""


def test_il_registro_segue_la_coda_per_chi_era_gia_in_fondo(tmp_path):
    """Il lato affermativo del ramo: scrollTop al bordo che soddisfa
    `scrollTop + clientHeight >= scrollHeight - 2` (13 su un massimo reale di
    15), cioe' il lettore era gia' in fondo, e la riga nuova deve restare
    visibile senza scorrere a mano."""
    sorgente = _DOM + "const RIGHE_DEL_REGISTRO = 500;\n" + _corpo_riga_come_funzione() + \
        _SETUP_REGISTRO_CON_SCORRIMENTO_VERO + """
registro.scrollTop = 13;
aggiungiRiga({ data: JSON.stringify("riga nuova") });
assert.equal(registro.scrollTop, registro.scrollHeight, "in fondo, ma il registro non segue la coda");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


def test_il_registro_resta_fermo_per_chi_non_era_in_fondo(tmp_path):
    """Il lato opposto dello stesso ramo: scrollTop appena sotto la stessa
    soglia (12, non 13), cioe' chi sta leggendo a meta'. Quella riga non deve
    muovere scrollTop di una virgola."""
    sorgente = _DOM + "const RIGHE_DEL_REGISTRO = 500;\n" + _corpo_riga_come_funzione() + \
        _SETUP_REGISTRO_CON_SCORRIMENTO_VERO + """
registro.scrollTop = 12;
aggiungiRiga({ data: JSON.stringify("riga nuova") });
assert.equal(registro.scrollTop, 12, "chi leggeva a meta' e' stato riportato in fondo");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"


# Passata di chiarezza: le metriche smettono di essere chiavi inglesi nude e
# JSON grezzo, il pannello dice quale step si sta guardando, e la colonna degli
# step spiega le quattro parole di stato. Le funzioni sono pure e di primo
# livello apposta, come reso() e superata(): si eseguono senza un pannello.


def test_resaMetrica_scrive_una_distribuzione_a_parole_e_non_in_JSON(tmp_path):
    """Le distribuzioni di quality.py sono quattro numeri, e `dd` mostrava
    `{"min":0.32,"median":0.71,...}`: graffe e virgolette sono la forma del
    trasporto, non il dato. Il caso dichiarato in cui nessun valore finito
    esiste (min a null) non deve stampare «null»."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
            + _funzioni("numeroReso", "riassuntoDistribuzione", "resaMetrica") + """
const reso = resaMetrica({ min: 0.32, median: 0.71, mean: 0.7, max: 1, non_finite: 0 });
assert.doesNotMatch(reso, /[{}"]/, `la distribuzione esce ancora come JSON: ${reso}`);
assert.match(reso, /min .*mediana .*media .*max /, `la distribuzione non si legge: ${reso}`);

const vuota = resaMetrica({ min: null, median: null, mean: null, max: null, non_finite: 3 });
assert.match(vuota, /nessun valore finito/, `il caso senza valori finiti dice: ${vuota}`);
assert.doesNotMatch(vuota, /null/, "«null» arriva a video come se fosse una misura");

const sporca = resaMetrica({ min: 1, median: 2, mean: 2, max: 3, non_finite: 5 });
assert.match(sporca, /non finiti: 5/, `i valori non finiti spariscono: ${sporca}`);
""")


def test_resaMetrica_dice_i_valori_semplici_nella_lingua_dell_interfaccia(tmp_path):
    """`true`, `false` e `null` sono la lingua di JSON, non quella di chi
    guarda: `watertight: true` e `max_volume: null` erano la meta' delle voci
    di due pannelli."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
            + _funzioni("numeroReso", "riassuntoDistribuzione", "resaMetrica") + """
assert.equal(resaMetrica(true), "sì");
assert.equal(resaMetrica(false), "no");
assert.equal(resaMetrica(null), "non impostato");
assert.equal(resaMetrica([]), "nessuno");
assert.equal(resaMetrica("crop"), "crop", "una stringa del server resta quella che e'");
// Un oggetto di oggetti (geometric_error) si apre di un livello: piu' giu' non
// c'e' nome che l'interfaccia sappia dire, e torna il JSON invece di inventarne uno.
const annidato = resaMetrica({ hausdorff: 12.5, cloud_to_mesh: { min: 0, median: 1, mean: 1, max: 2, non_finite: 0 } });
assert.match(annidato, /hausdorff: /, `il primo livello non si apre: ${annidato}`);
assert.match(annidato, /mediana/, `la distribuzione dentro resta JSON: ${annidato}`);
""")


def test_resaMetrica_non_arrotonda_un_numero_fino_a_cambiarlo(tmp_path):
    """maximumSignificantDigits scriverebbe 168.846.000 dove la misura vale
    168.845.511: un numero plausibile che nessuna lettura ha prodotto, cioe' il
    principio 3 del prodotto rovesciato."""
    _esegui(tmp_path, "import assert from 'node:assert/strict';\n"
            + _funzioni("numeroReso", "riassuntoDistribuzione", "resaMetrica") + """
const grande = resaMetrica(168845511.10290658);
assert.ok(grande.startsWith((168845511).toLocaleString("it")),
  `il volume misurato e' stato arrotondato a ${grande}`);

// L'altro capo della stessa regola. Il volume dell'elemento piu' piccolo di
// lab_crop vale 1,76e-06 mm^3 e con tre cifre decimali usciva «0», accanto a
// un massimo di 85.788: uno zero che vuol dire «sotto la risoluzione di questa
// resa» presentato come uno zero esatto.
const minuscolo = resaMetrica(1.7615617942227708e-06);
assert.notEqual(minuscolo, "0", "una misura sotto il millesimo diventa uno zero esatto");
assert.ok(/[1-9]/.test(minuscolo), `la misura piccola non porta nessuna cifra: ${minuscolo}`);
assert.equal(resaMetrica(0), "0", "uno zero vero non deve diventare altro");
""")


def test_l_intestazione_del_pannello_nomina_lo_step_e_dice_che_cosa_fa(tmp_path):
    """Il pannello si apriva sui due bottoni d'esecuzione: quale step si stesse
    guardando lo diceva soltanto il marchio nella colonna a sinistra, a 1100 px
    di distanza. E «Normali» da solo non dice a chi non conosce la pipeline che
    cosa stia per succedere al proprio dato."""
    _esegui(tmp_path, _DOM + _funzioni("intestazioneDelloStep") + """
const PROPOSITI = { "04_normals": "Stima in ogni punto da che parte guarda la superficie." };
ETICHETTE["04_normals"] = "Normali";
const [titolo, aiuto] = intestazioneDelloStep(4, [{ numero: 4, chiave: "04_normals" }]);
assert.equal(titolo.tag, "h3");
assert.match(titolo.textContent, /4/, "l'intestazione non dice quale step e'");
assert.match(titolo.textContent, /Normali/, "l'intestazione non porta il nome dello step");
assert.match(aiuto.textContent, /da che parte guarda/, "il proposito dello step non arriva a video");
assert.equal(aiuto.className, "aiuto");
""")


def test_l_intestazione_non_inventa_un_nome_per_uno_step_che_non_conosce(tmp_path):
    """Dove il dato manca si dichiara che manca: uno step la cui chiave non
    sta negli elenchi resta il proprio numero, senza una frase inventata."""
    _esegui(tmp_path, _DOM + _funzioni("intestazioneDelloStep") + """
const PROPOSITI = {};
const pezzi = intestazioneDelloStep(12, []);
assert.equal(pezzi.length, 1, "uno step sconosciuto si porta dietro una frase che nessuno ha scritto");
assert.equal(pezzi[0].textContent, "Step 12");
""")


def test_ogni_step_dell_elenco_ha_il_proprio_proposito():
    """ETICHETTE e PROPOSITI descrivono gli stessi undici step: una chiave in
    uno e non nell'altro e' un pannello che si apre senza dire che cosa fa,
    proprio per lo step aggiunto per ultimo."""
    testo = _senza_commenti_js(_modulo())
    etichette = set(re.findall(r'"(\d\d_[a-z_]+)":', testo.split("const PROPOSITI", 1)[0]))
    propositi = set(re.findall(r'"(\d\d_[a-z_]+)":', testo.split("const PROPOSITI", 1)[1].split("\n};", 1)[0]))
    assert etichette, "l'elenco dei nomi degli step non si trova piu'"
    assert etichette == propositi, f"step senza proposito: {sorted(etichette - propositi)}"


def test_la_colonna_degli_step_spiega_che_cosa_vuol_dire_non_valido():
    """«non valido» e' il concetto su cui l'intero strumento e' costruito — e
    l'unica cosa che distingue questo prodotto dall'eseguibile che sostituisce —
    e non era spiegato in nessun punto dell'interfaccia. Chi arriva dopo lo
    legge come «rotto» e riesegue tutto invece di riprendere da dove serve."""
    markup = _senza_commenti_html(_markup())
    assert "non valido" in markup, "la legenda degli stati non nomina «non valido»"
    assert "mai eseguito" in markup, "la legenda degli stati non e' completa"


def test_il_registro_dell_esecuzione_non_si_chiama_come_quello_dell_esperimento():
    """Nella stessa colonna, «Registro» erano due cose diverse: le righe che il
    sottoprocesso sta scrivendo adesso, e il registro dell'esperimento della
    Fase 2, che e' una tabella di candidati misurati."""
    markup = _senza_commenti_html(_markup())
    assert "Registro dell'esecuzione" in markup, "il registro delle righe non si distingue dall'altro"


def test_una_casella_di_sola_lettura_non_manda_in_due_posti_diversi(tmp_path):
    """La nota sotto una casella non modificabile diceva «si modifica dal file
    di configurazione», e su `crop_min` finiva tre righe sopra il riquadro
    «Ritaglio», che quello stesso valore lo scrive dall'interfaccia: due
    istruzioni opposte sullo stesso campo, misurate a video. La nota adesso
    dichiara solo che la casella non si scrive; dove si cambia il valore lo
    dice la descrizione del campo, che e' l'unica a saperlo."""
    sorgente = _DOM + _funzioni("reso", "cambiatoDalPredefinito", "campoParametro") + """
configurazione = { segment: { crop_min: [1690, -470, -480] } };
const riga = campoParametro("segment", "crop_min",
  { description: "si imposta dal riquadro «Ritaglio»", default: null }, 0);
const testo = riga.figli.map((f) => f.textContent).join(" ");
assert.match(testo, /riquadro/, "la descrizione del campo non arriva a video");
assert.doesNotMatch(testo, /file di configurazione/,
  `la nota manda al file mentre la descrizione manda al riquadro: ${testo}`);
assert.match(testo, /sola lettura/, "niente dice che la casella non si scrive");
console.log("ok");
"""
    assert _esegui(tmp_path, sorgente).strip() == "ok"
