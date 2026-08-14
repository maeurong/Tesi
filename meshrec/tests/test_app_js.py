"""La regione `role="alert"` dell'interfaccia, e le strade per cui e' sparita.

Lo stesso difetto — l'annuncio del rifiuto non garantito — e' tornato tre volte
per tre strade diverse:

1. l'attributo `hidden` su quella regione, che la toglie dall'albero di
   accessibilita' (sorvegliato da `test_server.py`, che vieta `rigaErrore.hidden`);
2. una regola di stile che la nascondeva con `display: none`, in un file che
   nessun test guardava (sorvegliato da `test_server.py` su `.errore:empty`);
3. `replaceChildren()` su `#dettaglio`, che a ogni apertura di pannello
   distruggeva la regione e ne creava una nuova: una regione viva creata
   nell'istante in cui ci si scrive dentro non garantisce l'annuncio, perche'
   il lettore di schermo non stava sorvegliando niente.

La quarta strada e' sempre la stessa mossa: rimettere la regione sotto qualcosa
che la puo' distruggere o generare. Questi controlli chiudono quella mossa
invece del suo sintomo — la regione sta nel markup, fuori dal sottoalbero che
viene riscritto, e il modulo non ne fabbrica un'altra.

Non stanno in `tests/test_server.py` per la stessa ragione per cui non ci sta
`test_stile.py`: quel file e' in mano ad altri, e metterlo nell'indice
porterebbe nel commit righe che non sono mie.
"""

from meshrec.app.server import UI_DIR


def _markup() -> str:
    return (UI_DIR / "index.html").read_text(encoding="utf-8")


def _modulo() -> str:
    return (UI_DIR / "app.js").read_text(encoding="utf-8")


def test_la_regione_d_errore_esiste_nel_markup_e_non_nasce_nascosta():
    """Strada 1. Nel markup e non creata da codice: deve preesistere a cio' che
    annuncia. E senza `hidden`, che la toglierebbe dall'albero."""
    markup = _markup()
    riga = next((r for r in markup.splitlines() if 'id="errore"' in r), None)
    assert riga is not None, "la regione role=alert non e' piu' nel markup"
    assert 'role="alert"' in riga, f"la regione ha perso il proprio ruolo: {riga}"
    assert "hidden" not in riga, f"hidden la toglie dall'albero di accessibilita': {riga}"


def test_la_regione_d_errore_sta_fuori_da_cio_che_viene_riscritto():
    """Strada 3. `#dettaglio` viene svuotato con replaceChildren() a ogni
    apertura di pannello: la regione dentro di li' non sopravvive a un clic."""
    markup = _markup()
    assert markup.index('id="errore"') < markup.index('id="dettaglio"'), (
        "la regione e' finita dentro il pannello che viene riscritto"
    )
    dentro = markup.split('<div id="dettaglio"', 1)[1]
    assert 'id="errore"' not in dentro, "la regione e' finita dentro #dettaglio"


def test_il_modulo_scrive_nella_regione_invece_di_fabbricarne_una():
    """La quarta strada. Un ramo che si crea la propria regione `role="alert"`
    riapre il difetto con l'aria di risolverlo: il codice sembra piu' completo,
    e l'annuncio smette di essere garantito.

    Si guarda la **forma di codice** e non la stringa: `role="alert"` compare
    per iscritto nei commenti che spiegano perche' la regione sta dove sta, e
    vietare la stringa vieterebbe la spiegazione. Provato: il primo tentativo
    di questo controllo era rosso proprio su quei commenti.
    """
    modulo = _modulo()
    assert 'getElementById("errore")' in modulo, "il modulo non e' piu' agganciato alla regione"
    assert 'role", "alert"' not in modulo, "un ramo fabbrica di nuovo la propria regione role=alert"


def test_ogni_step_e_un_comando_e_non_una_riga_cliccabile():
    """Undici `li` con un gestore di click erano l'intera interfaccia
    pilotabile col solo mouse (WCAG 2.1.1, livello A). Il rischio della
    ricaduta e' concreto: il `li` torna comodo appena qualcuno vuole
    aggiungerci sopra un'altra riga."""
    riga = _modulo().split("function nuovaRiga(", 1)[1].split("\n}\n", 1)[0]
    assert 'createElement("button")' in riga, "lo step e' tornato una riga senza ruolo"
    assert 'comando.type = "button"' in riga, "senza type, dentro un form il bottone invia"
    assert 'className = "step"' in riga, "il foglio si aggancia a .step: il nome non cambia"


def test_l_elenco_degli_step_si_aggiorna_e_non_si_ricostruisce():
    """Il difetto e' nato dalla correzione che lo precede, ed e' la ragione per
    cui i due controlli stanno vicini.

    Finche' gli step erano `li` inerti, riscrivere l'elenco a ogni evento non
    costava niente: non c'era nessun fuoco da perdere. Reso ciascuno un
    `<button>`, la stessa riscrittura — due volte al secondo mentre la pipeline
    gira — distrugge l'elemento che ha il fuoco una sessantina di volte durante
    uno step da 34 secondi, e sbalza chi naviga da tastiera su `<body>`. La
    correzione della tastiera, da sola, avrebbe riaperto da un'altra parte
    esattamente cio' che chiudeva.

    Il controllo guarda la guardia e non il numero di nodi: `replaceChildren`
    puo' restare, purche' non giri quando le righe ci sono gia'.
    """
    disegna = _modulo().split("function disegnaStep(", 1)[1].split("\n}\n", 1)[0]
    assert "replaceChildren" in disegna, "l'elenco non viene piu' costruito"
    prima_della_riscrittura = disegna.split("replaceChildren", 1)[0]
    assert "childElementCount !== steps.length" in prima_della_riscrittura, (
        "l'elenco si ricostruisce a ogni evento: il fuoco da tastiera non sopravvive"
    )
