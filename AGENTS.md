# AGENTS.md

Istruzioni per chi lavora su questo repository con un agente di codice.

## Cos'è e dov'è

MeshRec porta un rilievo fotogrammetrico di una struttura in cemento armato fino
a un modello a elementi finiti, in undici passaggi. Ogni passaggio salva i parametri con cui è
stato eseguito e le misure di qualità del proprio risultato.

```
meshrec/
├── src/meshrec/
│   ├── cli.py          comandi da riga di comando
│   ├── app/            server e coda di esecuzione dell'interfaccia
│   ├── core/           la pipeline: un modulo per famiglia di passaggi
│   └── ui/             l'interfaccia: JavaScript e CSS scritti a mano,
│                       con three.js vendorizzato in ui/vendor/ per la vista 3D
├── tests/              i test, accanto al codice che verificano
├── casi/               le configurazioni del caso studio della tesi
└── docs/               esiti delle fasi di sviluppo
docs/                   ricerche di validazione, alla radice del repository
PRODUCT.md              a chi serve il programma e con quali vincoli
```

## Ambiente

Python **≥3.12 e <3.13** — il vincolo è stretto in entrambe le direzioni — e
[uv](https://docs.astral.sh/uv/). Dalla cartella `meshrec/`:

```bash
uv sync --frozen
uv run meshrec serve
```

## Il verde che mente

**Leggi questa sezione prima di lanciare i test.**

`uv run pytest -q` può passare mentre centinaia di test non vengono eseguiti.
Non falliscono: spariscono. Due dipendenze esterne li fanno saltare in silenzio,
e la suite resta verde.

- Senza **`node`** (versione 22) saltano i test che eseguono davvero il
  JavaScript dell'interfaccia. `tests/test_app_js.py` cerca `node` sul PATH e
  senza di lui salta: sono circa 130 test.
- Senza **`ccx`** (CalculiX) sul PATH saltano i benchmark di verifica.
  Misurati il 28/08/2026 sul commit `20cb464`: **54 test saltati** contro l'unico
  che salta sempre, `wildmeshing`, per cui non esiste una wheel Windows.

In più, la configurazione predefinita **esclude due famiglie di test**:

```toml
addopts = "-m 'not feasibility and not validazione'"
```

`feasibility` sono le verifiche sulle dipendenze esterne, `validazione` i
confronti contro riferimenti esterni (NAFEMS LE10 e FV52, patch test, mensola
contro Gere-Timoshenko).

Quindi il comando onesto, con `node` e `ccx` presenti, è:

```bash
uv run pytest -m "" -q      # tutto, marcatori compresi
uv run pytest -q            # solo la suite predefinita
```

Se lanci la forma breve e vedi verde, hai verificato meno di quanto credi. La CI
in `.github/workflows/suite.yml` dichiara `ccx` obbligatorio proprio per questo:
senza, il lavoro fallisce invece di lasciar sparire i test in un verde.

## Come si legge la pipeline

Il punto di ingresso è **`src/meshrec/core/steps.py`**. Contiene due tabelle che
valgono più di qualsiasi diagramma:

- `STEP_KEYS` — i tredici passaggi in ordine, dal caricamento della nuvola di
  punti fino alla soluzione. **Il prodotto ne dichiara undici**: si chiude sul
  deck `.inp` dello step 11, e per questo `to_step` ha 11 come predefinito. Gli
  ultimi due — il prior geometrico e il solutore — restano funzionanti e
  raggiungibili chiedendoli, ma appartengono a una linea di sviluppo che sta
  fuori dal perimetro (`docs/linea-analisi-integrata.md`). Prima di aggiungere
  capacità là dentro, leggi quel documento.
- `STEP_BLOCKS` — quale blocco di configurazione ogni passaggio legge davvero.
  È da qui che discende quali passaggi diventano non validi quando si cambia un
  parametro.

Da lì si entra in `core/pipeline.py`, dove la funzione `run` esegue i passaggi
in sequenza. I parametri e i loro significati stanno in `core/config.py`: ogni
campo porta un titolo e spesso una descrizione in italiano, scritti per essere
letti.

## Regole che governano questo codice

Non sono preferenze di stile. Vengono da `PRODUCT.md` e hanno già trovato
difetti veri.

**Ogni numero che il programma mostra ha un controllo che lo contraddice se il
risultato peggiora.** Una misura senza il suo controllo non è finita.

**Un esito discreto che dipende dalla piattaforma è un difetto** — un ordine, un
indice, un conteggio, una scelta fra alternative. La matrice Linux/macOS della
CI è il rilevatore, e ne ha già trovato uno: l'ordine dei voxel restituito da
Open3D differiva fra le due piattaforme.

**Le grandezze continue non ricadono sotto quella regola.** Le riduzioni in
virgola mobile non sono bit-identiche fra arm64 e x86-64: i test confrontano con
tolleranze relative, e la risposta a uno scarto sull'ultima cifra è la
tolleranza dichiarata, non l'uguaglianza esatta.

## Se rimandi un cambio

- Rami da `main`, con prefisso `feat/`, `fix/`, `docs/` o `chore/` e uno slug
  che dica la cosa.
- Messaggi di commit **in italiano**, formato Conventional Commits: il soggetto
  dice cosa cambia e il corpo, quando serve, dice perché.
- Pull request verso `main`. La CI deve essere verde su **entrambe** le
  piattaforme, non su una.
- I test stanno accanto al codice che verificano, in `meshrec/tests/`.
