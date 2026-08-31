# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Utente primario:** l'autore della tesi. Apre l'applicazione da riga di comando
con `uv run meshrec serve`, e la usa ogni giorno per tarare e rieseguire la
pipeline sulle proprie scansioni. Conosce a memoria i dodici step della pipeline,
il solutore che sta nella propria schermata, e i nomi dei parametri.

Ha lavorato su Windows 11 fino al 16/08/2026, poi su macOS con Apple Silicon, e
al 28/08/2026 dichiara di essere tornato su Windows, operando da WSL mentre il
programma resta su Windows; la data del rientro non è registrata. Il fatto è di
prodotto e non di ambiente: la stessa pipeline ha già girato su due piattaforme,
e gli utenti successivi confermati la eseguiranno sulle proprie macchine.

Ne discende una norma di progetto, non un requisito d'interfaccia: un esito
**discreto** che dipende dalla piattaforma — un ordine, un indice, un conteggio,
una scelta fra alternative — è un difetto e va reso funzione del dato. Ne è già
stato misurato e corretto uno: l'ordine dei voxel restituito da Open3D differisce
fra le due piattaforme. Le grandezze **continue** non ricadono sotto questa norma:
le riduzioni in virgola mobile e le librerie di algebra non sono bit-identiche fra
arm64 e x86-64, e inseguire le ultime cifre di una metrica fra due macchine
sarebbe fabbricare una precisione che non esiste.

**Utenti successivi (confermati):** altri tesisti e il laboratorio, dopo la
discussione, sui propri dati. Questo è un fatto vincolante e non un'ipotesi:
l'applicazione sopravvive alla tesi e verrà aperta da qualcuno che non ha mai
visto la pipeline. Ne discendono requisiti di prodotto — stati vuoti che
spiegano, messaggi d'errore che dicono cosa fare, un primo avvio che non
presuppone la conoscenza degli step — non requisiti visivi.

**Pubblico di sola osservazione:** tutori e commissione, che la vedono usata in
discussione.

## Product Purpose

MeshRec trasforma una nuvola di punti rilevata per fotogrammetria in un modello
a elementi finiti di una struttura in cemento armato pronto per l'analisi, in
modo **riproducibile e documentabile**.

Sostituisce `MeshReconstructorPro`, un eseguibile fornito senza sorgente, i cui
limiti sono l'origine del progetto: interfaccia obbligatoria senza esecuzione
batch, parametri non salvati, nessuna metrica di qualità degli elementi, nessuna
misura dell'errore geometrico rispetto alla nuvola sorgente, operazioni di
riparazione opache e non citabili in un lavoro scientifico.

Il successo ha due metà: il metodo — una pipeline parametrizzata, misurata e
validata — e i risultati ottenuti applicandolo al caso studio della tesi.

## Positioning

Il meccanismo che un programma vicino non potrebbe copiare sinceramente:
**ogni numero che l'applicazione mostra ha un controllo che lo contraddice se il
risultato peggiora.** Non è una promessa di marketing ma una regola di
costruzione, nata da sette affermazioni false prodotte e corrette durante la
Fase 1 — una mesh degenere con metriche buone, una mesh troncata in silenzio, un
volume racchiuso negativo presente nei dati da sempre e mai guardato.

Le due conseguenze concrete: la selezione fra configurazioni avviene per dominanza
di Pareto su tre assi dichiarati, senza punteggi pesati con pesi arbitrari; e ogni
esecuzione lascia dietro di sé una riga in un registro tracciato da git, con
configurazione completa, impronte degli artefatti, commit del codice e versioni
delle librerie, così che la provenienza di un risultato sia ricostruibile a
distanza di mesi.

## Operating Context

Applicazione **locale**, utente singolo, nessuna autenticazione, nessun server
remoto. Si avvia da riga di comando e apre il browser.

Lo stato non vive in memoria ma su disco: ogni elaborazione è una cartella
`runs/<nome>/` con la configurazione completa, gli artefatti numerati step per
step, le metriche e il report. Gli esperimenti di sweep vivono in
`experiments/<nome>/` con il proprio registro in sola aggiunta, che è la tabella
sperimentale della tesi.

I dati veri sono grandi e lenti: la scansione di riferimento ha 6.329.096 punti,
gli artefatti di una corsa pesano circa 400 MB, e il singolo step più lungo dura
34,39 secondi su quella scansione. L'attesa è parte dell'esperienza d'uso e non
un caso limite.

Le uscite del programma escono dal programma: il file `.inp` va in Abaqus o
CalculiX, il report e le viste vanno in appendice a un documento accademico
stampato.

## Capabilities and Constraints

**Capacità confermate.** Undici step dalla lettura della nuvola al deck pronto
all'analisi: lettura e controllo di scala, segmentazione con ritaglio a box o
automatica, riduzione a voxel, normali, ricostruzione della superficie,
riparazione, metriche di superficie, semplificazione opzionale,
tetraedrizzazione, metriche di volume, esportazione. Motore di sweep su griglia
con fronte di Pareto e registro degli esperimenti. Report HTML statico.

**Terminologia da preservare alla lettera.** Sono identificatori, non parole:
`C3D4`, `C3D10`, `BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`,
`SIDE_RIGHT`, `ALL_WALL`, `min_ratio`, `nobisect`, Poisson, TetGen, MeshFix,
fronte di Pareto. Un letterale senza spazi è un identificatore e resta ASCII;
una chiave non si stampa mai, si stampa la sua etichetta.

**Vincoli tecnici.** Unità dichiarate e imposte in un solo punto: mm, N, MPa,
tonnellata, secondo. Un parametro di elaborazione ha il proprio valore
predefinito in un solo file, `core/config.py`. Distribuzione come repository più
`uv sync`, senza eseguibile impacchettato e senza toolchain di build per
l'interfaccia. Riproducibilità a parità di configurazione: il parallelismo delle
librerie è fissato a un thread perché altrimenti la stessa configurazione
produce risultati diversi.

**Fatti di prodotto esplicitamente non decisi.** Il controllo dei dati con Abaqus
non è mai stato eseguito, perché non c'è licenza sulla macchina di sviluppo: nulla
deve affermare che il deck sia stato validato da Abaqus. I set di faccia
`FACE_FRONT` e `FACE_BACK` sono misurati inutilizzabili su una scansione reale, e
i nomi dei set di faccia sono convenzioni, non identificazioni delle facce
fisiche.

## Brand Commitments

**Lingua dell'interfaccia: italiano**, coerente con commenti, documenti e messaggi
di commit del progetto. Gli identificatori tecnici elencati sopra restano invariati.

**Nessuna identità visiva d'ateneo da rispettare.** Vincolo unico e vincolante
dichiarato dall'utente: le viste e il report catturati finiscono in appendice a un
documento accademico stampato e non devono stonare accanto a un testo composto.

**Voce.** Il progetto scrive in un registro asciutto e misurato: afferma ciò che è
stato verificato, dichiara ciò che non lo è, e distingue sempre un esito negativo
documentato da un fallimento. È la voce dei suoi documenti e va estesa alle
etichette e ai messaggi dell'interfaccia.

## Evidence on Hand

Materiale reale, presente nel repository:

- `Nuvole di punti/lab_frame.pcd` — scansione reale di laboratorio, 152 MB,
  6.329.096 punti. È un **telaio in cemento armato**, non una muratura: due
  zapatas, la viga inferior che le collega, due columnas e la viga superior,
  sei membrature prismatiche in tutto. Il tamponamento in blocchi previsto dalla
  tavola non è presente nel provino scansionato, e non fa parte del modello.
- `muro_1.pdf` — tavola esecutiva `MURO 1` del provino (obra 0021, novembre
  2021, ing. José A. Barros Cabezas): sezioni, armature e volume di calcestruzzo
  dichiarato, 0,4777 m³. È la verità di riferimento con cui le misure sulla
  nuvola possono essere contraddette. **Non è versionato** — `.gitignore` lo
  esclude esplicitamente — quindi vive solo nella copia di lavoro dell'autore:
  chi clona il repository non ha la tavola su cui poggia la Fase 4. Non dichiara la classe del calcestruzzo:
  i parametri meccanici restano un'assunzione dell'operatore. Vedi
  `meshrec/docs/fase-4-materiale.md`.
- `Nuvole di punti/muro_generato.ply` — muro sintetico con geometria nota, usato
  come verità di riferimento.
- `meshrec/runs/muro/` e `meshrec/runs/lab_crop/` — corse di riferimento
  complete, **di sola lettura**.
- `meshrec/experiments/muro/` e `meshrec/experiments/lab_crop/` — registri di
  sweep con il fronte di Pareto adottato, **di sola lettura**.
- `meshrec/docs/` — i documenti di esiti e debito, con i numeri misurati.
- `Articoli/` — 17 pubblicazioni sul dominio.

**Assenze che il lavoro futuro non deve fabbricare.** Nessuna validazione con
Abaqus. Nessun caso studio reale oltre a queste due geometrie. Nessun utente
oltre all'autore ha ancora usato il programma, quindi nessuna testimonianza,
nessun dato d'uso, nessun confronto di prestazioni con il programma sostituito
oltre alle differenze di capacità elencate sopra.

## Product Principles

1. **Un numero mostrato senza un controllo che lo smentisca non vale più di un
   numero assente.** Vale per l'interfaccia quanto per il core: mostrare una
   grandezza è già sembrare di averla verificata.
2. **La grandezza da sorvegliare si sceglie prima della soglia.** Una soglia
   difficile da tarare è quasi sempre il sintomo di una grandezza sbagliata.
3. **Non fabbricare precisione che non esiste.** Nessuna percentuale di
   avanzamento inventata dove le librerie non la forniscono, nessuna nuvola
   decimata presentata come piena, nessuno zero che significa «sotto la
   risoluzione della misura» presentato come «esatto».
4. **La provenienza è parte del risultato.** Un artefatto, una metrica o una vista
   dicono sempre da quale configurazione e da quale esecuzione vengono.
5. **Chi arriva dopo deve poter capire.** L'utente successivo confermato non
   conosce i dodici step della pipeline: stati vuoti, errori e prima apertura devono
   insegnare, senza rallentare chi la pipeline la conosce a memoria.

## Accessibility & Inclusion

Nessun requisito specifico d'utenza è stato stabilito oltre allo standard: il
lavoro punta a WCAG AA pieno, con la postilla d'uso reale che l'interfaccia viene
proiettata in sede di discussione, quindi la leggibilità a distanza e il contrasto
non sono soltanto un obbligo di conformità.
