## Task 15 — report

Stato: **DONE**

### Aggiornamento finale (dopo il messaggio del coordinatore)

Il coordinatore ha confermato entrambi i concern sotto: il numero di
equazioni sbagliato era suo (misura pre-Task 8, non rimisurata), e il primo
tentativo di corsa usava per errore il ritaglio di `lab.yaml`. Ha rifatto la
corsa con `lab_telaio.yaml` in `runs/lab_telaio_v2/` e riportato i risultati.
Prima di scriverli nel documento li ho verificati uno per uno contro
`runs/lab_telaio_v2/metrics.json` e `12_wall.json`:

- **I numeri del prior (otto regioni, zero accettate, la tabella per
  regione con parallelismo/copertura/costanza, spessore mediano 192,03 mm, i
  riscontri `scarto_membrature: -6`/`scarto_volume: -1.0`) sono risultati
  esatti**, cifra per cifra, confrontati con `12_wall.json`. Riportati come
  misurati.
- **I numeri dell'as-built riportati dal coordinatore erano sbagliati**:
  dichiarava 13.237 nodi / 50.728 tetraedri / volume 168.845.534 mm³ / RMS
  mesh-nuvola 4,356 mm su 9.659 campioni / step piu' lenti a 17,88 s e
  48,95 s. Il file su disco (`runs/lab_telaio_v2/metrics.json`, nessun
  processo attivo, timestamp coerenti con un'unica corsa completata alle
  00:19) dice altro: **14.103 nodi, 51.913 tetraedri, volume 217.728.361 mm³,
  RMS mesh-nuvola 27,54 mm su 10.968 campioni, step piu' lenti 53,25 s e
  16,62 s**. Ho scritto nel documento i numeri del file, non quelli del
  messaggio, senza segnalarlo nel testo del documento (non e' materia per il
  lettore del documento, lo e' per questo report).
- La citazione dell'errore di `hexa.costruisci` sul prior vuoto l'ho
  riprodotta io stesso (`uv run meshrec model lab_telaio.yaml --tipo estruso`
  contro un prior a zero membrature): il testo combacia esattamente col
  codice (`hexa.py:730-734`).
- I numeri del prototipo PCA (anisotropia 0,000/0,270/0,087, sezioni
  224x48 ecc.) restano attribuiti al coordinatore nel documento, con nota
  esplicita che non li ho riprodotti io: nessun file su disco li porta, e
  rifarli avrebbe significato implementare un prototipo di segmentazione, fuori
  scope per un task di documentazione.

`lab_telaio.yaml` ora punta a `runs/lab_telaio_v2/` (`run.out_dir`), con un
commento che spiega perche' non punta piu' a `runs/lab_telaio/` (occupata dal
primo tentativo, ritaglio sbagliato). Il documento e' stato riscritto nei
punti 1, 3, 4, 5 (nuovo Ruling AN), 7 (equazioni) e 9 con i numeri veri,
senza piu' bisogno della sezione "Cosa manca a questo documento", rimossa.
Secondo commit: `42ba116`.

Skill invocate: nessuna. `coder.md` (il mio file in `~/.claude/agents/`) non
elenca il tool `Skill` fra i tool assegnati e non ha una sezione `## Skill`:
non potevo invocare `caveman`, `ponytail` né una skill di dominio anche
volendo. Ponytail era già attivo via hook di sessione (SubagentStart) e ne ho
seguito lo spirito manualmente nella prosa di questa risposta; caveman non è
applicabile al documento per esplicita istruzione del task ("caveman non vale
per il documento che scrivi").

### File toccati

- `meshrec/lab_telaio.yaml` (nuovo) — ritaglio misurato in questa sessione
  (RANSAC sul pavimento + transizione di ampiezza per il bordo delle
  zapatas), riscontri della tavola MURO 1, blocchi `wall`/`model` della Fase 4.
  Validato con `meshrec.core.config.load_config`.
- `meshrec/docs/fase-4-prior-telaio.md` (nuovo, poi riscritto in punti dopo
  la corsa vera) — documento di esito, tutti i numeri con fonte citata
  (file:riga o comando eseguito in sessione, mai un numero riportato senza
  verifica contro il file che lo produce).
- `meshrec/docs/fase-4-materiale.md` (modificato) — una riga di rimando in
  coda.

### Verificato

- Suite principale: `uv run pytest tests -q --ignore=tests/feasibility` →
  **555 passati**, 2 avvisi, 0 falliti, 0 saltati.
- Suite di fattibilità: `uv run pytest tests/feasibility -m feasibility` →
  **8 passati, 1 saltato** (il saltato è `wildmeshing`, non `ccx`).
- `ccx` presente (`/Users/mario/.local/bin/ccx`, versione 2.22); i quattro
  test di `tests/feasibility/test_calculix.py` girano e passano, compreso
  quello sul telaio a quattro membrature.
- `lab_telaio.yaml` si carica senza errori con `load_config`.

### Concern 1 (risolto) — un numero della correzione G4 non ha retto alla verifica

G4 dava come "misurato in questa sessione" **31.674 equazioni** nel sistema
risolto da `ccx` sul telaio sintetico a quattro membrature. Ho riprodotto lo
stesso scenario del test `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero`
in `/tmp/ccx_repro` (stesso banco, stesso `ModelConfig()`, stesso materiale) e
`ccx` riporta **32.637 equazioni** (riga "number of equations" del suo
stdout), non 31.674. Gli altri numeri della stessa tabella G4 hanno invece
retto alla riproduzione indipendente: `tie constraints: 4`, 79 nodi
dipendenti totali sulle quattro superfici `*_D` (contati sommando i nodi
unici per faccia), 24 non legati (righe di `model_WarnNodeMissTiedContact.nam`
e conteggio di `no tied MPC` nello stdout, entrambi 24), quindi 55 legati.
Nel documento ho scritto 32.637 con la fonte e ho detto esplicitamente che
31.674 non corrisponde a quanto ho misurato, invece di scrivere il numero
dato per buono. Il coordinatore ha confermato: 31.674 era una misura del
revisore del Task 12, presa prima che i giri 3-6 del Task 8 cambiassero il
criterio di taglio alle giunzioni. Il documento riporta ora anche questa
spiegazione (§ 7).

### Concern 2 (risolto) — un run in background con la configurazione sbagliata occupava `runs/lab_telaio/`

Durante la stesura, un aggiornamento mi ha informato che era stata avviata
una corsa end-to-end in background su `lab_frame.pcd`, uscita in
`runs/lab_telaio/`. Verificando `runs/lab_telaio/config.yaml` ho trovato che
il ritaglio usato è quello di `lab.yaml` (largo 290 mm, non arriva alle
zapatas), **non** quello che questo Task 15 misura e mette in
`lab_telaio.yaml` (largo 750 mm). Il tentativo ha finito in ~80 secondi (non
ore) con **0 membrature accettate su 3 regioni trovate** — coerente con un
ritaglio che non comprende le zapatas. Un secondo tentativo,
`meshrec model ... --tipo estruso`, ha lasciato solo un `config.yaml` in
`runs/lab_telaio-estruso/`, compatibile con un arresto immediato per assenza
di membrature a monte.

Non ho toccato né cancellato nulla in `runs/lab_telaio/` o
`runs/lab_telaio-estruso/` (restano sul disco, storia del primo tentativo, non
citati come risultato in nessun punto del documento). Non ho lanciato io
stesso la corsa vera: l'ha rifatta il coordinatore in `runs/lab_telaio_v2/`
con la configurazione corretta (§ "Aggiornamento finale" sopra), verificata
da me numero per numero prima di scriverla nel documento. `lab_telaio.yaml`
ora punta lì.

I due modelli parametrici e il confronto restano non generati, ma non per
mancata esecuzione: `meshrec model lab_telaio.yaml --tipo estruso`, eseguito
da me in questa sessione contro il prior vero (zero membrature accettate),
solleva `ValueError` — il codice si rifiuta di costruire un modello vuoto
(`hexa.py:730-734`). È un esito misurato, non un passo saltato.
