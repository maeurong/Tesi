"""Le stringhe che il server mostra portano gli accenti italiani veri.

Gemella di `test_app_js.py::test_le_stringhe_mostrate_portano_gli_accenti_italiani`,
che sorveglia i tre file dell'interfaccia. Quel controllo dichiarava per
iscritto il proprio confine -- «copre i tre file dell'interfaccia, non le
stringhe che arrivano dal server» -- e questo file e' l'altra meta'. Finche'
mancava, nella stessa colonna convivevano le due grafie.

La regola sta nel piano del giro 3: «Sorgenti in ASCII, con una sola eccezione
dichiarata: le stringhe **mostrate all'utente** portano gli accenti italiani
veri. I commenti, i nomi e il resto del codice restano ASCII». Il motivo non e'
ortografico ma di prodotto: PRODUCT.md dichiara che questa interfaccia viene
proiettata durante la discussione e che il report finisce in un'appendice
cartacea, e «qualita'» su un muro davanti alla commissione si legge come un
refuso di tesi.

**Due classi di difetto, non una.** Oltre a `e'` -> `è` esistono le parole
scritte **nude**, senza apostrofo e senza accento (`piu`, `densita`, `unita`).
Nessuna regex sull'apostrofo le vede: una passata che sistemasse solo la prima
classe lascerebbe le altre sbagliate **sembrando finita**.

**Due strati, non uno** (la decisione sta in
https://github.com/maeurong/Tesi/issues/18):

- **per provenienza** dove una porta esiste. Le descrizioni del pannello
  raggiungono il browser da un punto solo, `/api/schema`, che legge le
  `description` dei campi: li' il criterio e' esatto e un campo nuovo entra da
  se', senza aggiornare nessun elenco;
- **per modulo** dove una porta non esiste, con la regola dello spazio a
  separare una frase da un identificatore.
"""

import ast
import re
from pathlib import Path

from meshrec.core.config import PipelineConfig

SORGENTI = Path(__file__).resolve().parents[1] / "src" / "meshrec"

# `po'` e' un troncamento corretto, non un accento mancante. Nessun'altra
# parola tronca lo e'.
TRONCA = re.compile(r"\b[A-Za-z]*[aeiou]'(?![A-Za-zàèéìòù])")
# Le nude. `meta` non c'e': in `<meta charset="utf-8">` non e' una parola
# italiana, ed e' il generatore del report a scriverlo.
NUDA = re.compile(
    r"\b(piu|gia|percio|cosi|perche|poiche|finche|puo|sara|qualita|densita|unita|possibilita)"
    r"(?![A-Za-z'àèéìòù])"
)
# Un tag HTML intero, e cio' che vive dentro un paio di apici senza spazi.
# Sono le due famiglie di falso positivo misurate:
#   - `class='assente'` ha l'aspetto esatto di una parola tronca, e sono undici
#     casi nel solo `core/report.py`. Una passata meccanica ci avrebbe scritto
#     `class='assentè'` dentro il generatore del report;
#   - una parola fra apici dentro la prosa -- «i modelli parametrici sono
#     'estruso' e 'primitive'» -- chiude con lo stesso apice. Accentarla
#     romperebbe il nome che la frase sta citando.
# In tutti e due i casi cio' che sta fra gli apici non ha spazi: e' la stessa
# regola dello spazio, applicata dentro la frase invece che alla frase intera.
TAG = re.compile(r"<[^<>]*>")
CITATO = re.compile(r"'[^'\s]*'")


def _pulito(testo: str) -> str:
    return CITATO.sub("''", TAG.sub("<>", testo))


def _guaste(testo: str) -> set[str]:
    pulito = _pulito(testo)
    return {p for p in TRONCA.findall(pulito) if p != "po'"} | set(NUDA.findall(pulito))


def _letterali_di(percorso: Path):
    """Ogni letterale di stringa del file che non e' un docstring.

    `ast.get_docstring` non basta e non e' un dettaglio: non riconosce i
    docstring d'attributo (una stringa nuda dopo un'assegnazione), e contarli
    gonfiava la misura di questo perimetro del 24% -- 275 parole invece di 221.
    Si escludono tutte le stringhe che sono un'istruzione a se'.
    """
    albero = ast.parse(percorso.read_text(encoding="utf-8"))
    docs = {
        id(nodo.value)
        for nodo in ast.walk(albero)
        if isinstance(nodo, ast.Expr)
        and isinstance(nodo.value, ast.Constant)
        and isinstance(nodo.value.value, str)
    }
    for nodo in ast.walk(albero):
        if (
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and id(nodo) not in docs
        ):
            yield nodo


def test_le_descrizioni_che_il_pannello_mostra_portano_gli_accenti():
    """Strato 1: per provenienza, dove la porta esiste.

    `/api/schema` serve le `description` dei campi di `PipelineConfig`, e il
    pannello degli step le mostra: e' l'unica strada per cui quel testo arriva
    a video. Chiedere lo schema a pydantic invece di camminare a mano sulle
    annotazioni non e' comodita': il camminatore ingenuo
    (`issubclass(t, BaseModel)`) e' **cieco su undici modelli su ventiquattro**,
    quelli dietro `Optional`, liste e unioni, e fra le dieci descrizioni che
    perde c'e' quella del **nome del materiale** -- il campo che finisce
    interpolato in `*MATERIAL, NAME=...`.

    Le sole `properties`, mai gli oggetti: una `description` su un oggetto e' il
    **docstring della classe**, che la regola vuole in ASCII. Pretenderla
    accentata chiederebbe il contrario della regola su diciotto testi.

    Mutazione che lo uccide: scrivere `piu'` in una `description` di
    `core/config.py`.
    """
    schema = PipelineConfig.model_json_schema()
    corpi = [*schema.get("$defs", {}).values(), schema]
    descrizioni = {
        campo["description"]
        for corpo in corpi
        for campo in corpo.get("properties", {}).values()
        if "description" in campo
    }

    # Se lo schema smette di risolvere qualcosa il controllo diventa cieco
    # invece che rosso: zero descrizioni significa che e' cambiata la forma,
    # non che il difetto e' sparito.
    assert len(descrizioni) > 40, (
        f"solo {len(descrizioni)} descrizioni raggiunte: lo schema non morde piu'"
    )

    guaste = {p for testo in descrizioni for p in _guaste(testo)}
    assert not guaste, (
        "descrizioni mostrate dal pannello con la grafia vecchia: " + ", ".join(sorted(guaste))
    )


def test_la_prosa_dei_moduli_che_parlano_all_utente_porta_gli_accenti():
    """Strato 2: per modulo, dove una porta non esiste.

    Non tutto cio' che si mostra passa da una porta sola. I messaggi d'errore
    nascono sparsi -- `core/report.py` scrive la prosa che va in appendice,
    `app/server.py` i rifiuti che il pannello legge, i validatori di
    `core/config.py` quelli che compaiono sotto il campo -- e per loro il
    criterio e' il modulo, con la regola dello spazio a separare una frase da
    un identificatore.

    **La regola dello spazio**: e' prosa cio' che contiene uno spazio. Tutto il
    resto e' un identificatore e non si tocca. Non e' una soglia scelta a
    occhio: provata sui casi veri, risparmia tutte e undici le chiavi -- il
    flag `--densita` che si batte a mano, `densita_dispersione` gia' scritta
    nei `metrics.json` sul disco, `unita`, `qualita`, `qualita_elementi` --
    senza perdere nessuna frase.

    Mutazione che lo uccide: scrivere `"il piu' grande"` in un messaggio di
    `core/volume.py`.
    """
    guasti: dict[str, set[str]] = {}
    quanti = 0
    for percorso in sorted(SORGENTI.rglob("*.py")):
        for nodo in _letterali_di(percorso):
            if " " not in nodo.value.strip():
                continue
            quanti += 1
            parole = _guaste(nodo.value)
            if parole:
                chiave = f"{percorso.relative_to(SORGENTI)}:{nodo.lineno}"
                guasti[chiave] = parole

    assert quanti > 300, f"solo {quanti} letterali di prosa esaminati: l'estrazione non morde piu'"
    assert not guasti, "prosa con la grafia vecchia:\n" + "\n".join(
        f"  {dove}: {', '.join(sorted(parole))}" for dove, parole in sorted(guasti.items())
    )


def test_gli_identificatori_italiani_restano_in_ascii():
    """La controprova: la guardia vieta la grafia vecchia, non le parole.

    Undici stringhe corte portano una parola che in italiano vorrebbe
    l'accento, e **non devono cambiare**: sono un flag della CLI che Mario
    batte a mano, e chiavi gia' scritte nei `metrics.json` delle corse sul
    disco. PRODUCT.md dichiara `runs/muro` e `runs/lab_crop` di sola lettura:
    accentare la chiave la scollerebbe dai file che la portano, e nessun
    controllo se ne accorgerebbe finche' qualcuno non riapre una corsa vecchia.

    Senza questo controllo, la guardia qui sopra resterebbe verde anche se
    qualcuno «finisse il lavoro» accentandoli.

    Mutazione che lo uccide: rinominare `--densita` in `--densità` in `cli.py`.
    """
    identificatori = ["--densita", "densita_dispersione", "unita", "qualita", "qualita_elementi"]
    trovati = {nome: 0 for nome in identificatori}
    for percorso in sorted(SORGENTI.rglob("*.py")):
        for nodo in _letterali_di(percorso):
            grezzo = nodo.value.strip()
            if grezzo in trovati:
                trovati[grezzo] += 1

    mancanti = sorted(nome for nome, quante in trovati.items() if quante == 0)
    assert not mancanti, (
        f"identificatori spariti dal sorgente: {mancanti}. Se sono stati accentati, "
        "le corse gia' sul disco non si rileggono piu' con quelle chiavi"
    )
