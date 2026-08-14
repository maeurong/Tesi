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
    this.padre = null;
  }
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
    _esegui(tmp_path, _DOM + _funzioni("segnaStepAperto", "nuovaRiga", "disegnaStep") + """
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


def test_solo_lo_step_aperto_porta_il_marchio(tmp_path):
    """Correzione 2. Quale step e' aperto lo sapeva solo una variabile di
    modulo: a video non lo diceva niente, e chi non vede il fondo evidenziato
    non aveva **nessun** canale. `aria-current` e non una classe, perche' e'
    l'attributo che porta il significato e il foglio ci si aggancia sopra.

    Due proprieta', ed entrambe si rompono in silenzio: mai due marchi insieme
    (due «stai guardando questo» sono peggio di nessuno), e il marchio sparisce
    quando nessun pannello e' aperto.
    """
    _esegui(tmp_path, _DOM + _funzioni("segnaStepAperto", "nuovaRiga", "disegnaStep") + """
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
    _esegui(tmp_path, _DOM + _funzioni(
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
# BL-1: dai tasti al disco.
# --------------------------------------------------------------------------


def test_il_campo_parametro_non_indovina_il_tipo_dal_valore():
    """La radice del difetto. Il tipo veniva da `typeof` del valore corrente,
    cioe' indovinato: i nove campi numerici nullabili erano una casella di testo
    finche' valevano `None` e una numerica appena valevano qualcosa, e con
    `type="number"` Chrome sanifica cio' che non sa leggere — `.value` torna
    `""` mentre a video resta scritto `1e`. Il tipo lo conosce solo il modello,
    e `/api/schema` oggi non lo manda.

    I sei campi del ritaglio restano `type="number"`, e non e' un'incoerenza:
    li' il tipo non e' indovinato, sono le coordinate dell'ingombro e sono
    numeri per costruzione, con la loro guardia sul campo vuoto.
    """
    campo = _modulo().split("const valore = configurazione[blocco][nome];", 1)[1]
    campo = campo.split("gruppo.append(riga);", 1)[0]
    assert "typeof valore ===" not in campo, "il tipo del campo torna a dipendere dal valore"
    assert 'input.type = "number"' not in campo, (
        'type="number" sanifica in silenzio: cio\' che il browser non legge diventa ""'
    )
    assert 'input.step = "any"' not in campo, "step=any toglie il passo unitario ai 18 interi"


def test_una_battuta_illeggibile_resta_quella_battuta(tmp_path):
    """La funzione che trasforma dei tasti in un dato persistito, eseguita.

    `1e`, `-`, `1.2.3` non si leggono come numeri e restano la stringa battuta:
    il modello le rifiuta con un 422 leggibile, che e' l'unico posto dove il
    tipo vero si conosce. Diventassero `null` sarebbero accettate in silenzio su
    nove campi. E lo spazio non vale zero: `Number(" ")` e' `0`, e un campo che
    a video sembra vuoto scriveva `0`.
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
const COINCIDENZA = /e' quanti ne terrebbe lo step 2/;
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
