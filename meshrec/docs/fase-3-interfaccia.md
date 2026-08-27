# Fase 3 — Interfaccia web: esiti, rulings, prova d'uso degli strumenti

Documento di chiusura della Fase 3. Scritto il **2026-08-17**, sul ramo
`fix/critica-giro-3`, ultimo commit dell'interfaccia `e0b84e1`.

**Regola di questo documento.** Ogni numero viene da una lettura, e la lettura e'
citata. Dove una cosa non e' stata misurata, sta scritto che non lo e' stato:
un'affermazione senza fonte non entra qui, perche' e' esattamente il difetto che
questa fase e' esistita per estirpare.

---

## 1. Che cosa gira e che cosa no

### La suite

```
uv run pytest    →  494 passed, 3 skipped, 6 deselected, 1 warning in 39.74s
```

Eseguita da `meshrec/` il 17/08/2026 su macOS arm64, Python 3.12.13, al commit
`e0b84e1`. Il riferimento di partenza dichiarato dal piano era **181 test
raccolti, 6 deselezionati**; la tabella di stato del piano al 16/08 registrava
**399 passed, 3 skipped**.

L'unico avviso e' voluto e non e' un difetto: `test_volume.py:135` alza
`UnmetQualityConstraintWarning` perche' il test verifica proprio che `nobisect`
possa rendere inerte il limite di qualita' **e che il programma lo dica**.

### Che cosa gira

Undici step dalla lettura della nuvola al deck pronto all'analisi, pilotati
dall'interfaccia web locale. Gli step sono quelli di `core/steps.py:19-31`:
`01_load`, `02_segment`, `03_downsample`, `04_normals`, `05_reconstruct`,
`06_repair`, `07_surface_quality`, `08_simplify`, `09_tetrahedralize`,
`10_volume_quality`, `11_export`.

Diciassette tratte HTTP in `app/server.py`, contate sui decoratori:
`GET /`, `GET /ui/{nome}`, `GET /api/run`, `GET|PUT /api/config`,
`GET /api/metrics`, `GET /api/schema`, `GET /api/experiments`,
`GET /api/experiments/{nome}`, `POST /api/step/{numero}`,
`POST /api/step/{numero}/from`, `POST /api/cancel`, `POST /api/crop`,
`GET /api/cloud/{numero}`, `POST /api/cluster`, `GET /api/mesh/{numero}`,
`GET /api/events`.

L'avvio e' `uv run meshrec serve <configurazione>.yaml`. Il percorso della
configurazione **e' obbligatorio**: fino a `eccfe0c` il comando documentato in
PRODUCT.md non partiva affatto, perche' `cli.py` voleva un posizionale che la
documentazione non nominava. Corretto in PRODUCT.md e in `meshrec/README.md`
nello stesso commit. Le configurazioni pronte sono `lab.yaml` (il caso studio),
`muro.yaml` (il muro sintetico) e `prova-interfaccia.yaml` (una corsa vuota, per
guardare l'interfaccia senza calcolare niente).

### Che cosa non gira, o non e' verificabile oggi

- **`meshrec/runs/` non contiene le corse di riferimento su questa macchina.**
  Restano `runs/default/`, prodotta dalle prove. Le corse `runs/muro/` e
  `runs/lab_crop/` sono in trasferimento dal PC Windows dal 16/08. Nessun test ne
  dipende — usano tutti `tmp_path` — ma **non c'e' geometria vera da servire
  all'interfaccia senza rieseguire la pipeline**, e i tempi citati in questo
  documento (27-34 s per step a freddo, 96,27 s di prima lettura, ~26 s per il
  ritaglio) vengono dalle misure archiviate, non da una riesecuzione di oggi.
- **`/api/cluster` e' una tratta completa che nessun comando dell'interfaccia
  raggiunge.** Vedi R133.
- **`EventSource` non ha `onerror` e `caricaStato()` e' l'unica lettura senza
  `.catch(serverMuto)`.** A server morto durante una corsa l'interfaccia si
  congela sull'ultimo conteggio ricevuto e continua a mostrare un tempo trascorso
  che nessuno sta piu' misurando. E' il difetto piu' grosso lasciato aperto dalla
  fase; la ragione per cui non e' stato chiuso e' R132.
- **Il ciclo di disegno di `viewport.js` rende 60 fps anche a scena ferma.** R137.
- **`analysis.material` non e' modificabile dall'interfaccia**: modulo di Young e
  densita' stanno dentro un input in sola lettura che contiene il JSON del
  modello. R134.

### Che cosa questo documento non afferma

Per prescrizione di PRODUCT.md, sezione *Evidence on Hand*, e per verifica
diretta:

- **Nessuna validazione con Abaqus.** Non c'e' licenza sulla macchina di
  sviluppo. Il deck `.inp` e' prodotto ed e' esportabile; non e' stato aperto in
  un solutore.
- **Nessun caso studio oltre a `lab_frame.pcd` / `lab_crop` e al muro sintetico
  `muro_generato.ply`.**
- **Nessun utente oltre all'autore** ha usato il programma: nessuna
  testimonianza, nessun dato d'uso, nessuna prova di usabilita' con persone.
- **Nessun confronto di prestazioni con `MeshReconstructorPro`** oltre alle
  differenze di *capacita'* elencate in PRODUCT.md (esecuzione batch, parametri
  salvati, metriche di qualita' degli elementi, misura dell'errore geometrico,
  operazioni di riparazione citabili).

---

## 2. Il punteggio impeccable, criterio per criterio

### Da dove viene il numero, e che cosa non e'

Il punteggio e' **21/40, «Acceptable»**, da
`.impeccable/critique/2026-08-16T11-21-22Z__meshrec-src-meshrec-ui-index-html.md`
(campo `total_score: 21`, `p0_count: 2`, `p1_count: 3`). Metodo dichiarato dallo
strumento: doppio agente, A in revisione di disegno con ispezione dal vivo in
Chrome, B rilevatore deterministico con misure di contrasto.

**Due avvertenze che valgono piu' del numero.**

**(a) Il confronto 25 → 20 → 21 fra i tre giri non e' una misura.** Lo dichiara
la critique stessa: i tre giri sono stati assegnati da tre valutatori diversi con
criteri di severita' diversi, e il giro 1 era per sua stessa ammissione degradato
(la ragione tecnica sta in R99: fino al giro 2 un vincolo del coordinatore
impediva a `critique` di avviare i propri sottoagenti). Non c'e' un delta, non
c'e' una tendenza, e questo documento non ne fabbrica nessuno. La stessa
constatazione era gia' stata fatta da dentro il progetto in R102: *lo strumento
ha dato 25/40 e 20/40 sulla stessa interfaccia*, e *otto difetti chiusi non hanno
mosso il punteggio*.

**(b) Il 21/40 precede il lavoro che lo avrebbe cambiato.** La critique porta la
marca temporale `2026-08-16T11:21:22Z`, cioe' le 13:21 locali. **Trentotto commit
sono atterrati dopo, ventiquattro dei quali toccano `src/meshrec/ui/`**, dalle
13:42 del 16/08 alle 12:03 del 17/08. Il punteggio qui sotto e' quindi la
fotografia *prima* della chiusura
dei rilievi, non dopo. **Nessuna rimisurazione e' stata eseguita** — il passo
«Rimisurare» previsto dalla chiusura del piano della critica non e' stato fatto,
e la cartella `.impeccable/` contiene tre soli file, tutti in `critique/`, il
piu' recente dei quali e' quello del 16/08 alle 13:21.

**Provenienza delle colonne «chiuso da».** Il Task 16 e' stato chiuso su
decisione dell'utente senza una verifica del codice riga per riga. Le
attribuzioni sotto vengono quindi da **due fonti dichiarate e non da una
rilettura del sorgente**: la mappa rilievo → task scritta nella Self-Review del
piano `2026-08-16-meshrec-critica-giro-3.md`, e i messaggi dei commit che quei
task hanno prodotto. Dove il codice e' stato letto direttamente, e' detto.

### La tabella

| # | Euristica | G2 | G3 | Dove si e' arrivati | Che cosa manca |
|---|---|---|---|---|---|
| 1 | Visibilita' dello stato | 2 | 2 | Il rilievo centrale era che nessuna lettura asincrona aveva stato di caricamento: per 27-34 s la vista mostrava la mesh dello step precedente sotto i parametri del nuovo. Chiuso in `287a537` («la vista dichiara l'attesa invece di mostrare lo step di prima»). La fine di una corsa ora si annuncia con la durata misurata (`9d4bd2d`), una corsa senza codice d'uscita tace invece di dirsi riuscita (`1e34bf2`), e la testata dice quale corsa e' finita e come (`b1c67e6`). In `e0b84e1` la riga che cambia stato porta 700 ms di anello nella tinta del proprio stato. | `EventSource` resta senza `onerror` e `caricaStato()` senza `.catch` (R132). A server morto l'interfaccia afferma ancora un tempo che nessuno misura. |
| 2 | Sistema e mondo reale | 2 | 3 | `#in-corso` scriveva `step 9 in corso`, un numero nudo mentre `ETICHETTE` era li': chiuso con `nomeDelloStep` in `9d4bd2d`. I campi di `SegmentConfig` senza `description` — 6 su 11, quindi lo spazio dell'aiuto si stampava vuoto — sono stati riempiti in `02a13b9` («l'interfaccia si spiega a chi non conosce la pipeline»). E' l'unico criterio che la critique aveva gia' visto salire da 2 a 3. | Le metriche non portano unita' di misura. Nessun commit di questa serie lo affronta. |
| 3 | Controllo e liberta' | 2 | 2 | Nessun lavoro mirato. `Annulla` esisteva gia' e in questa serie e' stato reso piu' solido lato worker (`54ac943`, `50f6e4a`, `5aa5e11`, `e2af4de`). | Non c'e' annullamento di una **modifica di parametro**: ogni `change` scrive su disco e non si torna indietro. `inquadra` (`viewport.js`) resta esportata e legata a niente, quindi dopo un'orbita storta l'unico rimedio e' ricaricare. Entrambi sotto R133. |
| 4 | Coerenza e standard | 2 | 2 | I bottoni della Galleria non avevano stato scelto e `#galleria-tabella` non aveva `tabindex`, mentre `#registro` lo aveva con otto righe di commento a difenderlo. Chiusi nel Task 4 (`c22e9c2`, `d64153a`). **Letto nel codice:** `index.html:153-154` porta oggi `role="region" aria-label="Registro dell'esperimento" tabindex="0"`, con il commento che cita WCAG 2.1.1. | `annullaLaCorsa` resta l'unica fetch senza `.catch(serverMuto)` — stessa famiglia di R132. |
| 5 | Prevenzione dell'errore | 2 | 2 | I sei campi del ritaglio ingoiavano l'ingresso non valido in silenzio e «Applica» mandava poi l'ultimo array **valido**: cio' che finiva sul disco non era cio' che il campo mostrava. Chiuso in `af9faa9` («un estremo del ritaglio che non si legge lo dice, e Applica si spegne»), riusando `segnalaCampo`. I due «Esegui» restavano vivi durante una corsa: spenti nel Task 5 (`8c9d46f`, `2e6de87`). | Il rischio di R115 — due «Applica» in volo su una POST da ~26 s — e' stato corretto nel giro successivo alla revisione, ma la classe «due richieste lente in volo sullo stesso comando» non ha un test che la sorvegli in generale. |
| 6 | Riconoscere invece che ricordare | 2 | 2 | Era il buco piu' netto: `/api/schema` manda il `default` di ogni campo e l'interfaccia non lo rendeva, in un prodotto la cui tesi e' la riproducibilita'. Chiuso nel Task 6: il pannello apre su cio' che la corsa ha cambiato (`e741f08`), una sola resa per il confronto e per il segno del predefinito (`e383012`), e il predefinito di un modello annidato esce come JSON e non come `repr` (`1006c4b`). | Niente di dichiarato aperto su questo criterio. |
| 7 | Flessibilita' ed efficienza | 1 | 1 | **Il criterio piu' basso della tabella, e quello su cui si e' deliberatamente scelto di non lavorare.** L'unico guadagno e' il confronto fra due step di `e0b84e1`, che risparmia un ricaricamento ma non e' una scorciatoia. | Tutto il resto: zero scorciatoie da tastiera, nessun Invio-per-eseguire, nessuna selezione multipla, il cursore del taglio con 1000 passi inservibile a frecce, `/api/cluster` irraggiungibile. E' la persona Alex al completo, ed e' funzionalita' nuova, non un difetto: R133. |
| 8 | Estetica e minimalismo | 3 | 3 | Il rilievo era la gerarchia piatta e in parte rovesciata — `.zona h2` a 13px, il gradino piu' piccolo, mentre il corpo sta a 16 — e il ceto unico dei bottoni, che rendeva «Esegui da qui in giu'» identico al filtro «muro». Il secondo e' chiuso in `8c9d46f` («un'esecuzione non ha piu' l'aspetto di un filtro»), con la variante primaria misurata a 7,49:1. La spaziatura e' stata rifatta in `dc30504` («lo spazio dice dove finisce un gruppo e dove sta la vista»). Il sistema visivo di base era gia' in `aaa720e`. | La distribuzione della scala tipografica non e' stata rovesciata: i titoli strutturali restano il testo piu' piccolo dell'interfaccia. Il rilievo minore «Tipografia per il caso proiettato» non ha un commit suo. |
| 9 | Recupero dall'errore | 2 | 2 | La critique lo definiva «una macchina ottima» a cui mancava l'unica cosa: **una corsa fallita non alzava nessun allarme**, perche' `exit_code` e `annullato` arrivavano in ogni frame SSE e `app.js` non li leggeva. Chiuso nel Task 1: l'esito ha una regione sua e il fallimento ci resta (`f2de552`), l'errore di una corsa finita non sopravvive alla successiva (`ec28037`), e il worker garantisce che una corsa conclusa porti sempre il proprio codice d'uscita (`832824a`). **Letto nel codice:** `index.html:20` porta `<p class="esito" id="esito" aria-live="polite">`, separata da `#in-corso` con il commento che spiega perche' non e' la stessa riga riusata. | I due 500 lato server su clic ordinari (`FileNotFoundError` non gestita) sono chiusi in `eccfe0c`, ma il criterio nel complesso non e' stato rimisurato. |
| 10 | Aiuto e documentazione | 2 | 2 | «non valido» — il concetto su cui l'intero strumento e' costruito — non era spiegato in nessun punto. **Letto nel codice:** `index.html:46-55` porta oggi un `<details class="legenda">` con le quattro definizioni, ripiegato perche' disteso misurava 160 px in cima al contenitore che scorre e spingeva l'undicesimo step fuori vista. `meshrec/README.md` non nominava mai `serve`: corretto in `eccfe0c`. | La maggior parte dei parametri fuori da `SegmentConfig` resta senza descrizione. |
| | **Totale** | **20/40** | **21/40** | — | **Acceptable** |

### Carico cognitivo e anti-pattern, come stavano al 16/08

**Carico cognitivo: 6 falliti su 8 — critico.** Falliti: focus singolo, blocchi
≤ 4, gerarchia visiva, scelte minime, memoria di lavoro, divulgazione
progressiva. Passati: raggruppamento e una-cosa-alla-volta. La divulgazione
progressiva e' stata affrontata dopo, nel Task 6 del piano della critica e con la
legenda ripiegata di `02a13b9`; **gli altri cinque non sono stati rimisurati.**

**Verdetto anti-pattern: «non e' slop, e non e' nemmeno vicino».** La scansione
deterministica dava `[]` ed exit 0 su tutte e quattro le forme, e lo strumento e'
stato validato con un file di controllo contenente anti-pattern noti (exit 2, due
rilievi) — quindi il vuoto e' reale e non uno scanner rotto. Nessun
`.impeccable/config.json` e nessun `DESIGN.md`: la pulizia non e' il prodotto di
una deroga configurata.

Il modo di fallire dichiarato dalla critique merita di restare a verbale, perche'
e' il giudizio piu' utile che la fase abbia ricevuto: **l'interfaccia e'
sotto-disegnata dove il prodotto e' lento, e sovra-ingegnerizzata dove e' gia'
corretto.** `app.js` porta tre contatori di generazione perche' una risposta
tardiva non contraddica mai una didascalia, e poi non mostrava nulla per i 27-34
secondi in cui quella risposta arrivava. La correzione centrale della serie di
commit del 16-17/08 e' esattamente questa: leggere tre informazioni che il
prodotto **gia' possedeva e gia' mandava al browser** — `exit_code`, `secondi`,
`default` — invece di disegnare qualcosa di nuovo.

---

## 3. I rulings

**Centotrentotto decisioni, R1–R138.** L'elenco integrale con la forma estesa,
le fonti e lo stato di ciascuna sta in
[`fase-3-rulings-inventario.md`](fase-3-rulings-inventario.md), riallineato il
17/08. Qui sotto ciascuna nella forma richiesta,
`Ruling: <cosa ho deciso> — <perche'> — <cosa costa se sbagliato>`, generata
meccanicamente da quel documento e non riparafrasata.

**Le tre tratte hanno provenienza diversa:**

| Tratta | Fonte | Letta il |
|---|---|---|
| R1–R107 | `fase-3-registro-decisioni.md` | 2026-08-14 |
| R108–R127 | `fase-3-registro-decisioni.md`, dopo il riallineamento `8e85f43` | 2026-08-17 |
| R128–R138 | **non stanno nel registro**: piano `2026-08-16-meshrec-critica-giro-3.md` e messaggi di commit del 16–17/08 | 2026-08-17 |

Il registro delle decisioni si ferma a R127, alla consegna del Task 16. Il lavoro
del 16-17/08 e' stato condotto a mano e non lo ha alimentato: le sue decisioni
stavano nel piano e nei messaggi di commit, mai in forma di ruling numerato.
R128–R138 le portano in quella forma, **numerandole per la prima volta il
17/08**. Sono decisioni vere con la fonte citata voce per voce; non sono voci del
registro e non vengono spacciate per tali.

**Due difetti dei documenti sorgente, dichiarati e non corretti.**

1. `fase-3-registro-decisioni.md` contiene blocchi duplicati alla lettera: **19
   rulings compaiono piu' di una volta** — R80 e tutta la tratta continua
   R110–R127; R118 quattro volte. E' l'impronta di un riallineamento che ha
   riaccodato intervalli sovrapposti. Conseguenza per chi legge: un conteggio di
   occorrenze sul registro sovrastima quelle decisioni di un fattore due.
2. R108 registra che **30 decisioni su 107 non hanno il «costo se sbagliato»** e
   decide di non riempirle a posteriori. Ma nell'inventario la riga del costo c'e'
   su tutte e 138 le voci, verificato meccanicamente il 17/08. O il conteggio di
   R108 riguarda le sole voci grezze del registro e l'inventario le ha completate
   dal contesto, o e' invecchiato. **Questo documento non ha riderivato il numero
   e non sceglie fra le due letture.**

**R1** — Ruling: `app.server.create_app` prende `config_path: Path`, non `root`. — codice e test del Task 1 concordano su `config_path`; legare l'app a un file di config rende sensati `GET`/`PUT /api/config`. — servirebbe un secondo parametro per la radice esperimenti, oggi ricavato da `config_path.parent`.

**R2** — Ruling: insieme `STREAMING = {"/api/events"}` dichiarato nel modulo di test, commentato, esclude le rotte in streaming dal contratto sugli endpoint. — `TestClient.get` su un generatore SSE senza fine bloccherebbe la suite dal Task 5 in poi; `/api/events` ha test dedicato con `max_eventi`. — un endpoint in streaming futuro sfugge al contratto se l'insieme non resta corto e commentato.

**R3** — Ruling: `_config_cubo(tmp_path)` e `_config_cubo_su_disco(tmp_path)` vanno creati come helper di modulo, riproducendo la costruzione gia' presente nei file. — il piano li citava come esistenti; e' un difetto del piano, non del codice. — i test nuovi girerebbero su geometria diversa da quella della Fase 1, numeri non confrontabili con quelli archiviati.

**R4** — Ruling: i test nuovi in `tests/test_config.py` usano il prefisso `config.` (`config.PipelineConfig`, ecc.). — uniformita' col file esistente, che importa `from meshrec.core import config`. — solo un `NameError` immediato in sviluppo.

**R5** — Ruling: nel Task 9 il ramo `.vtu` precede `o3d.io.read_triangle_mesh`. — `read_triangle_mesh` su un `.vtu` non restituisce la geometria attesa; leggere due volte lo stesso file da 34,7 MB e' spreco puro. — il contorno del volume esce vuoto, il test sui conteggi lo rivela subito.

**R6** — Ruling: il commento `# solo per numpy` va corretto: Open3D serve per `o3d.io.read_image`. — un commento che dice il falso e' peggio di nessun commento. — nulla, e' prosa.

**R7** — Ruling: three.js vendorizzato durante il Task 1 invece che nel Task 7, in due file (`three.module.js` 603.113 B + `three.core.js` 1.403.455 B = 2.006.568 B, non uno come stimava la spec); Task 7 Step 1 riscritto di conseguenza. — il piano dichiarava la rete come unico rischio bloccante della notte; verificarlo per primo lo toglie di mezzo prima che costi sei task. — i due file pesano 800 KB piu' del previsto, irrilevante contro i 400 MB di artefatti gia' presenti.

**R8** — Ruling: `httpx2>=2.10.0` nel gruppo dev e' accettato, benche' la spec dichiarasse solo `fastapi`/`uvicorn`. — e' dipendenza di starlette/testclient, non dell'app; i 191 test passano con `httpx2` presente e `httpx` assente; nome verificato non typosquat. — una dipendenza di test in piu' nel gruppo dev, non entra nella distribuzione ne' nel wheel.

**R9** — Ruling: il rilevatore impeccable e' intero, non piu' degradato; il quesito Q1 e' chiuso. — i quattro moduli di parsing sono stati installati nella cache dei plugin; prova di controllo su pagina rotta apposta conferma le tre capacita' dichiarate perse. — nulla nel repository.

**R10** — Ruling: `package.json`, `package-lock.json`, `node_modules/` (4,7 MB) restano non tracciati nella radice, non cancellati. — cancellare e' irreversibile e non compra nulla; sono non tracciati, la regola «mai `git add -A`» impedisce che entrino in un commit; l'utente era tornato a dormire, senza dare consenso. — 4,7 MB di ingombro su disco finche' l'utente non li rimuove.

**R11** — Ruling: il minor del Task 1 (`steps.py:119-120`, `(voce or {}).get(...)`) non apre un giro suo, entra come requisito esplicito nel dispaccio del Task 3. — il Task 3 riapre `steps.py` per `write_state`, la correzione costa una riga in lavoro gia' previsto; contraddice il contratto dichiarato «uno stato illeggibile e' uno stato assente». — la correzione slitta di un task; nel frattempo uno `steps.json` corrotto in modo specifico farebbe fallire `run_state` invece di riportare «mai eseguito».

**R12** — Ruling: `meshrec/runs/sweep/` trattata come sola lettura al pari delle altre quattro cartelle; verifiche manuali su `runs/prova-interfaccia/`, config `prova-interfaccia.yaml` derivata da `lab.yaml` cambiandone solo `run.out_dir`. — `lab.yaml` (tracciato) punta alla cartella del candidato adottato dalla Fase 2; eseguire `meshrec run lab.yaml` la riscriverebbe e `sweep verify` dichiarerebbe stantia una riga della tabella sperimentale della tesi. — 400 MB di disco in piu' per una corsa di prova separata, contro il rischio di invalidare la provenienza del candidato adottato.

**R13** — Ruling: accettata la correzione dell'implementatore, `nome.tmp.ply` (non `nome.ply.tmp` come da piano); glob di `scarta_temporanei` portato a `*.tmp.*`. — il piano sbagliava — Open3D non riconosce piu' `.ply` se l'estensione finale e' `.tmp`; verificato che nessun artefatto vero del progetto contiene la sottostringa `.tmp.`. — un file dal nome sfortunato verrebbe cancellato all'avvio di una corsa, ma nessun nome del progetto ha quella forma.

**R14** — Ruling: il commento stantio di `sweep.py:528` entra nel Task 3 invece di aspettare la revisione finale. — stesso motivo di R11 — una riga, il Task 3 tocca la funzione che il commento descrive; un commento che descrive un meccanismo superato e' un'affermazione falsa nel codice. — resta una frase imprecisa in un commento per qualche ora.

**R15** — Ruling: il passo 4 del Task 4 non trasforma `if start <= N:` in `if start <= N <= stop:` come da piano; le guardie restano invariate, l'arresto avviene per interruzione del flusso con un'eccezione `_FermataRichiesta` catturata e assorbita. — quelle guardie hanno rami `else` di ripresa che ricaricano da disco l'artefatto di step saltati; con `stop < N` il ramo `else` avrebbe letto artefatti da non toccare. Trovato leggendo il codice vero di `pipeline.run`, non fidandosi del testo scritto dal coordinatore. — un'eccezione per controllo di flusso e' meno leggibile di una condizione, ma e' l'unica forma che non tocca le guardie di ripresa gia' collaudate.

**R16** — Ruling: una corsa parziale (`from_step > 1` o `to_step < 11`) fonde le proprie metriche in `metrics.json` invece di sostituirlo; una corsa intera sostituisce come oggi; il valore restituito e' il dizionario fuso. — l'interfaccia esegue uno step alla volta — se ogni step sostituisse il file, il pannello perderebbe tutto a monte; effetto collaterale voluto: anche `meshrec run --from-step 5` non butta piu' via le metriche a monte. — `metrics.json` puo' contenere righe misurate con configurazioni diverse, ma `steps.json` e la catena di impronte lo dichiarano — l'informazione non e' persa.

**R17** — Ruling: il secondo minor del Task 3 (nessun test end-to-end sulla scrittura dello stato «fallito») entra come requisito nel Task 4. — e' il difetto peggiore emerso finora — un meccanismo che scrive un'affermazione su disco senza controllo che la smentisca; la prova costa poco perche' il Task 2 ha gia' lasciato un test che fa fallire una corsa vera. — la registrazione dei fallimenti resta non provata per un altro task.

**R18** — Ruling: accettata la correzione dell'ordine delle due assegnazioni nel test (`to_step` prima di `from_step`), senza toccare il codice di produzione. — `RunConfig` ha `validate_assignment=True` piu' un validatore incrociato; verificato di persona che `from_step=2` con `to_step` ancora a 1 e' correttamente rifiutato, e il caso reale dell'interfaccia non incontra la trappola. — un chiamante futuro che riusa un oggetto config gia' ristretto incontra un `ValidationError` chiaro, non un comportamento silenzioso.

**R19** — Ruling: rilievo Important accettato — `cli.py` assegna `from_step` prima di `to_step`; corretto invertendo l'ordine delle due righe. — con `to_step` gia' ristretto sul disco lo step richiesto non gira affatto, e l'errore viene inghiottito dall'`except Exception` di `main`; la verifica precedente del coordinatore era incompleta (dedotta, non letta sui chiamanti). — nulla — la correzione e' l'inversione di due righe piu' il test che la copre.

**R20** — Ruling: il minor del Task 5 (secondi trascorsi sbagliati per un client che si connette a lavoro gia' in corso) entra come requisito nel Task 8 invece di finire alla revisione finale. — e' un numero mostrato che puo' essere falso, non cosmesi — stessa famiglia dei difetti che questa fase esiste per evitare. — il tempo trascorso resta impreciso solo per un client che si collega a lavoro gia' avviato, caso raro con utente singolo.

**R21** — Ruling: i 27,5 s di `decimate` sulla nuvola vera si dichiarano, non si correggono. — l'ipotesi che la ricerca del passo sprecasse il tempo e' smentita dalla misura — l'esponente reale del legame passo/punti e' ~1,45 non 2, una stima taglierebbe le passate solo da ~4 a ~2 (~50%, non millisecondi); la lettura del file pesa solo l'1,5% del tempo. — l'utente aspetta 27 s al primo caricamento di ogni step sulla scansione reale — l'effetto peggiore fra quelli parcheggiati finora.

**R22** — Ruling: il messaggio `{"errore":"KeyError","messaggio":"99"}` per uno step fuori intervallo entra come requisito nel Task 8. — difetto trovato con `curl` contro un server vero — struttura dell'errore giusta ma testo inutile a chi legge; il Task 9 introdurra' lo stesso schema di accesso ad `ARTIFACTS`, va corretto prima che si duplichi. — un messaggio d'errore poco chiaro in un caso che l'interfaccia da sola non produce.

**R23** — Ruling: R21 revocato su richiesta esplicita dell'utente; nasce il Task 6-bis (stima iniziale del passo, quattro giri diventano due; cache del risultato in `meshrec/.cache/viewport/`, non nella cartella della corsa; `_ESPONENTE_DENSITA = 1.45` come costante di modulo in `viewport.py`). — la misura diretta da' numeri piu' netti della stima del revisore (25,7 s su 33,6 s sprecati nei primi due raddoppi); la cache non sta nella cartella corsa perche' un server puntato su `runs/lab_crop` non deve poterci scrivere. — la stima puo' solo costare un giro in piu', mai un risultato errato, perche' il ciclo di raddoppio resta e garantisce il budget.

**R24** — Ruling: il Task 6-bis si dispaccia dopo il rientro del Task 7, non in parallelo. — i file non si sovrappongono, ma due agenti che committano insieme sullo stesso ramo si contendono `.git/index.lock`. — si perdono i minuti di attesa del Task 7.

**R25** — Ruling: il minor del Task 7 (`!risposta.ok` di `mostraNuvolaDelloStep` non svuotava la scena) corretto direttamente dal coordinatore, senza aprire un giro di dispaccio. — quattro righe in due file che nessun altro agente tocca; il ciclo dispaccio-revisione costerebbe piu' della correzione; il rilievo era gia' stato trovato e formulato da un revisore terzo. — due modifiche entrano nel ramo senza revisione indipendente, ma la revisione finale del ramo le vedra' nel diff complessivo.

**R26** — Ruling: il rilievo Important del Task 7 (`role="img"` su una tela azionabile da tastiera) corretto con `role="application"`, con i comandi entrati nell'etichetta costruita da un'unica funzione `descrivi`. — `role="img"` fa si' che lo screen reader trattenga le frecce nella propria navigazione invece di consegnarle alla pagina; `application` passa i tasti. — `role="application"` sopprime la navigazione per elemento dentro la tela, ma non ha contenuto navigabile essendo un canvas unico.

**R27** — Ruling: la prova a video del viewport la esegue il coordinatore, non l'implementatore; rimandata a dopo il Task 6-bis. — un'affermazione su cio' che appare a schermo, fatta da chi non ha un browser, non e' una misura; a cache fredda ogni caricamento costa 27-34 s, impraticabile prima del 6-bis. — non dichiarato nel registro.

**R28** — Ruling: il rilevatore impeccable va eseguito su una copia con gli href relativi, mai sul file sorgente; il Task 16 deve farlo cosi'. — misurato — su `index.html` sorgente il rilevatore da' `[]` perche' `href="/ui/stile.css"` (assoluto) non esiste dal disco e non legge nessuna regola CSS; su copia con href relativi compare subito `flat-type-hierarchy`. — nulla, la copia si butta.

**R29** — Ruling: `flat-type-hierarchy` sulla scala tipografica di `stile.css` e' rilievo gia' misurato, diventa primo compito di `typeset` nel Task 16, non scoperta da rifare. — cinque corpi fra 12px e 16px con rapporto 1,3:1 fra gli estremi non sono una gerarchia. — `typeset` lo troverebbe comunque, si perde solo tempo.

**R30** — Ruling: i tempi del rapporto Task 6-bis rimisurati dal coordinatore invece di riportare quelli dell'implementatore. — 4,08/0,09 s dichiarati contro 4,47/0,10 s letti (differenza da rumore), ma il numero che finisce nella tesi e' quello verificato di persona — quinto principio del progetto. — costa due minuti di macchina; senza, sarebbe un numero ricordato e non derivato da una lettura.

**R31** — Ruling: la prova nel browser riservata al coordinatore (R27) non e' eseguibile — estensione Chrome non connessa; verificato invece tutto cio' che sta «sotto il vetro» col server vivo. — invece di dichiarare la prova fatta o saltarla, si verifica tutto il verificabile senza browser. — resta non verificato che WebGL disegni, che le frecce ruotino la scena, che l'`aria-label` cambi, che `cattura()` dia un PNG — se il canvas non disegnasse, i task 9-15 si costruirebbero su una vista morta.

**R32** — Ruling: rimosso dalla radice il file `$F`, zero byte, creato durante il Task 6-bis da un reindirizzamento di shell malriuscito. — non dichiarato nel registro oltre l'origine. — nulla — non tracciato, vuoto, nessun contenuto perso.

**R33** — Ruling: I-2, I-4 e la finestra TOCTOU si correggono spostando il calcolo della spaziatura dentro `decimate_file`, chiave `(sorgente, max_points, mtime_ns, spacing_sample, seed)`; il pre-controllo `cache_path(...).exists()` sparisce. — aggiungere solo `spacing` alla chiave costringerebbe a calcolarlo anche a cache calda (1,78 s), buttando il guadagno; la nuova chiave e' equivalente perche' la spaziatura e' deterministica da sorgente + due interi. — una firma pubblica cambiata a un giorno dalla nascita, un test in piu' da riscrivere; `decimate_file` conosce due parametri in piu' — accettabile, gia' conosceva `max_points`.

**R34** — Ruling: la pulizia della cache passa da `marchio-max_points` a solo `marchio` (una voce per file sorgente). — una voce pesa 35,9-52,3 MB (non «circa 1,5 MB» come diceva il rapporto, che aveva dimenticato gli indici); con la chiave allargata ogni orfano peserebbe ~40 MB. — chi chiedesse due budget diversi in alternanza pagherebbe un ricalcolo ogni volta — con utente solo e un budget solo non accade.

**R35** — Ruling: ordinato di correggere per primo il rilievo I-1 (nessun test attraversa il ramo caldo dell'endpoint), benche' Importante e non Bloccante. — quarto principio del progetto in forma pura — sei test coprono la funzione, zero coprono la tratta; il revisore l'ha contato, non dedotto. — non dichiarato nel registro.

**R36** — Ruling: M-9 (endpoint «nuvola» serve anche lo step 9, `.vtu` di volume), M-12 (`CACHE_DIR` relativa al cwd) e M-13 (test forza `mtime` con `os.utime`) parcheggiati come minori. — M-9 sara' toccato comunque dal Task 9; M-12 e' convenzione condivisa gia' esistente; M-13 e' modo legittimo di rendere deterministico un test. — non dichiarato nel registro.

**R37** — Ruling: il numero `flat-type-hierarchy` (cinque corpi in 4 px, scala larga 1,33 volte) e' l'ingresso del Task 16, non una scoperta da rifare; chi esegue `typeset` rimisura solo alla fine, sulla stessa copia. — non dichiarato oltre «misurato e non supposto». — nessuno — la misura si ripete in due secondi.

**R38** — Ruling: correzione del bug nel piano — `renderer.setSize(larghezza, altezza, false)` non scrive la misura in CSS; aggiunto anche `display: block` sulla tela, nello stesso commit. — misurato nel browser — la scena era tagliata su due lati con entrambe le barre di scorrimento visibili; la riga sbagliata era del piano scritto dal coordinatore, non dell'implementatore. — sei task avevano superato revisione e suite verde con la scena tagliata — nessun test puo' vedere una barra di scorrimento, motivo per cui la prova a video non era rimandabile.

**R39** — Ruling: rimossa dal coordinatore una voce di cache in formato vecchio (tre campi invece di cinque), trovata dal revisore e non dal rapporto dell'implementatore. — e' la seconda volta nel task che una dichiarazione di pulizia dell'implementatore non regge alla verifica. — per il resto della notte le affermazioni di pulizia dell'implementatore si controllano, non si riportano.

**R40** — Ruling: accettati due residui del Task 6-bis: (1) configurazioni alternate sulla stessa nuvola si scaccino a vicenda dalla cache; (2) `_rimuovi_voci_vecchie` gira anche dopo un `OSError` inghiottito, lasciando la cache vuota invece di conservare la voce vecchia. — (1) e' il prezzo scelto consapevolmente per tenere la cache a otto voci; (2) accade solo su un disco che rifiuta la scrittura. — (1) con utente solo e una config alla volta non si paga mai; (2) costa un ricalcolo, mai un risultato sbagliato.

**R41** — Ruling: corretto assegnando `from_step` e `to_step` insieme, in un `RunConfig` nuovo, dopo che il browser ha mostrato un `ValidationError` vero durante l'uso reale. — nessun ordine di assegnazione singola e' sicuro — la config su disco puo' rompere in un verso o nell'altro a seconda di quale campo e' piu' vecchio; la correzione precedente (R19) salvava solo un caso. — nessuno visto dal coordinatore — il nuovo stato e' validato per intero da pydantic come prima.

**R42** — Ruling: i quattro rilievi Importanti del Task 8 (server manda la ragione del rifiuto, browser la butta via) trattati in un giro solo. — separarli darebbe quattro correzioni che si toccano nello stesso gestore; nessuno e' colpa dell'implementatore, sono nel brief incompleto. — un giro piu' grande da rivedere.

**R43** — Ruling: ordinato I-2 per primo — la PUT rimanda l'intera configurazione, valore rifiutato compreso, quindi dopo un errore ogni campo toccato diventa rosso a torto. — misurato dal revisore che un campo valido successivo prende comunque `campo-rifiutato`; un indicatore che accusa il campo sbagliato e' peggio di nessun indicatore. — non dichiarato nel registro.

**R44** — Ruling: M-3 (cronometro) trattato come se fosse Importante — il revisore ha sostituito `time.monotonic()` con `time.time()` e la suite e' rimasta verde. — requisito piu' delicato del cronometro (aggiunto dal coordinatore nell'addendum) non aveva un controllo che lo smentisse. — non dichiarato nel registro.

**R45** — Ruling: l'unico punto dell'addendum non fatto come chiesto (stato vuoto rimesso quando lo step non ha ne' blocchi ne' metriche, non quando non c'e' nessuno step scelto) resta com'e'. — la deselezione non esiste in questa interfaccia, l'esito pratico e' quello voluto — non conformita' formale, non difetto. — non dichiarato nel registro.

**R46** — Ruling: M-4 (pannello mostra metriche vecchie mentre la colonna step gia' dice «valido») va corretto. — le due meta' della schermata si contraddicono e niente lo dichiara — stessa famiglia della vista che contraddiceva la didascalia, gia' corretta nel Task 7. — non dichiarato nel registro.

**R47** — Ruling: dispacciati due implementatori insieme (Task 12a e Task 9), contro la regola generale di uno alla volta. — insiemi di file disgiunti verificati tali; ogni dispaccio nomina esplicitamente i file dell'altro come vietati in scrittura. — un conflitto di merge su un file non previsto, che si vede subito e si risolve rileggendo.

**R48** — Ruling: il Task 12 si spezza in 12a (core: funzione e test) e 12b (endpoint, mappa colore, legenda); 12b torna in coda. — la meta' core non tocca nulla in mano al Task 8 ed era l'unico lavoro geometrico che potesse partire subito. — non dichiarato nel registro.

**R49** — Ruling: il terzo test del brief del Task 12 (tautologico: `atteso` calcolato da `campo` e confrontato con se stesso) riscritto contro `quality.geometric_error`, con margine dichiarato e giustificato. — l'unica riga con contenuto era un range arbitrario — «il controllo che smentisce» non smentiva nulla; il brief era del coordinatore stesso. — non dichiarato nel registro.

**R50** — Ruling: imposta compattazione con `np.unique(contorno, return_inverse=True)` per il ramo `.vtu`. — `griglia.points` contiene tutti i nodi della tetraedralizzazione (365.212 su `lab_crop`), mentre le facce di contorno ne toccano una frazione — l'endpoint avrebbe mandato al browser vertici in maggioranza non disegnati. — non dichiarato nel registro.

**R51** — Ruling: `np.sort(facce_tutte, axis=1)` butta via l'orientamento delle facce — non lo fa correggere, chiede solo una riga di commento accanto. — il materiale usa gia' `DoubleSide` e le normali sono ricalcolate dal browser, la superficie si vede comunque; il commento serve al prossimo che vede una superficie a chiazze. — una resa peggiore di quella possibile, visibile ma non fuorviante.

**R52** — Ruling: aggiunta al brief del Task 9 la guardia sullo step fuori intervallo, gia' imposta su `/api/cloud` nel Task 6-bis. — il brief mancava questo requisito; stesso difetto, stessa forma di correzione gia' vista. — non dichiarato nel registro.

**R53** — Ruling: corretti nel brief i numeri di verifica del Task 9 — erano quelli dello step 5 (199.891/398.044), per lo step 6 l'attesa e' 213.154/426.600. — un numero di verifica sbagliato e' peggio di nessuna verifica — chi lo trova diverso sospetta il codice invece del brief. — non dichiarato nel registro.

**R54** — Ruling: il Task 15 si spezza come il 12 — 15a (`write_run_report` in `core/report.py` + test) e 15b (cattura viste, endpoint, bottoni, CLI); tre implementatori insieme (12a, 9, 15a). — la meta' core (15a) e' disgiunta da tutto cio' che gira ed e' la parte sostanziosa. — non dichiarato nel registro.

**R55** — Ruling: il Task 13 non si spezza, benche' `ui/viewport.js` sia libero; parte intero quando `app.js` si libera. — i due metodi di taglio senza il loro comando in `app.js` non sarebbero verificabili in alcun modo (nessun motore di test del DOM, permesso negato di aggiungerne uno). — non dichiarato nel registro.

**R56** — Ruling: corretta la docstring che affermava, senza distinguere, che il campionamento delegato a PyMeshLab evita la sovrastima — vero per `cloud_to_mesh`, falso per `mesh_to_cloud`; `vertex_deviation` dichiarata come riproduzione di quel verso. — trovato leggendo `metrics.json` — `mesh_to_cloud.n_samples` coincide esattamente col numero di vertici. — senza correzione, chi vede due funzioni dare lo stesso numero a cinque cifre sospetta un errore e perde tempo; il documento di Fase 1 pubblicava gia' `n_samples` per entrambi i versi, quindi la tesi non dice il falso.

**R57** — Ruling: accettata la preoccupazione dell'implementatore — il controllo del Task 12a sorveglia l'accordo fra due implementazioni della stessa misura, non la divergenza punto-nuvola/punto-superficie; quella resta non sorvegliata. — ora che si sa perche' coincidono, il controllo e' onesto per cio' che e'; una soglia sulla divergenza attesa sarebbe il secondo principio del progetto rovesciato. — non dichiarato nel registro.

**R58** — Ruling: il Task 12a era segnato «complete» senza revisore dispacciato — dispacciati subito i revisori mancanti (Task 12a e Task 9). — dimenticanza mentre si dispacciavano tre implementatori in parallelo, non una decisione. — non dichiarato nel registro — il rischio del parallelismo non e' il conflitto sui file ma la fase del metodo che salta perche' l'attenzione e' altrove.

**R59** — Ruling: corretta la preoccupazione principale dell'implementatore del Task 15a — `config.yaml` di `prova-interfaccia` dichiara `from_step`/`to_step`=2 mentre `metrics.json` porta undici step fusi; correzione via `steps.run_state(out_dir, cfg)`, senza codice nuovo. — su uno schermo e' un fastidio, stampato in appendice a una tesi e' una tabella che afferma un legame inesistente senza che il lettore possa accorgersene. — un report piu' verboso.

**R60** — Ruling: la scelta dell'implementatore di `yaml.safe_load` invece di `load_config` resta, combinata col controllo di R59. — stessa regola gia' applicata alle viste assenti — mai un riquadro muto. — non dichiarato nel registro.

**R61** — Ruling: aggiunto requisito non nel brief — l'intervallo del cursore del taglio deve venire dall'ingombro della geometria mostrata (`Box3().setFromObject(gruppo)`), non da un valore fisso nel codice. — su un muro di 2470,99×231,00×1697,00 mm un intervallo fisso renderebbe il cursore inutile per due assi su tre. — non dichiarato nel registro.

**R62** — Ruling: `attivaTaglio` assegna i piani ai materiali che esistono in quel momento; lasciata all'implementatore la scelta fra ricordare lo stato o spegnere il taglio ad ogni cambio di step dichiarandolo — non lasciata aperta. — cambiando step la geometria nuova nascerebbe senza taglio mentre il comando dice attivo — vista che contraddice il comando. — non dichiarato nel registro.

**R63** — Ruling: imposto di verificare che il cursore, quando ha il fuoco, riceva lui le frecce e non la tela. — il Task 7 ha dato alla tela `role="application"` che intercetta le frecce — due controlli che si contendono gli stessi tasti sono un difetto di accessibilita'. — non dichiarato nel registro.

**R64** — Ruling: non si cambia il calcolo (che sottostima l'errore superficiale); corretta solo la descrizione (commit `3bfd285`), fatto salire il fatto in cima al documento del mattino. — cambiare il calcolo muoverebbe ogni numero di `07_surface_quality` in tutte le tabelle delle Fasi 1 e 2 — decisione di Mario, non da prendere di notte in un commit di docstring. — la tesi continua a riportare un RMS che misura meno di quanto il lettore crede; mitigato perche' `n_samples` per entrambi i versi e' gia' pubblico.

**R65** — Ruling: accolto l'Importante 1 del revisore come rietichettatura, non difetto da correggere stanotte; il controllo va rinominato e ridocumentato, il controllo mancante entra nel Task 12b. — il controllo da' rapporto 1,0000 per qualunque geometria perche' le due misure sono la stessa misura, non perche' sia inutile — la prova per mutazione lo fa diventare rosso. — non dichiarato nel registro.

**R66** — Ruling: il Minore 3 del revisore (`test_quality.py:293-299` passa anche con `return np.zeros(...)`) e' fondato, va corretto nel 12b. — un test di deviazione nulla su vertici presi dalla nuvola non distingue la funzione giusta da una che restituisce sempre zero. — non dichiarato nel registro.

**R67** — Ruling: il giro di correzione si ferma a `server.py` e `tests/test_server.py`; I-4 e I-5 (in `ui/app.js`/`ui/viewport.js`) vanno in un giro successivo. — quei file sono in mano al Task 13 in quel momento. — due difetti restano aperti qualche ora in piu'; il conflitto su due file contesi costerebbe di piu'.

**R68** — Ruling: i tre rilievi del giro Task 9 (stessa forma: codice giusto senza un controllo che lo smentisca) corretti spostando la geometria di prova, non il codice. — con la geometria di prova originale, sostituire la riga del verso con quella sbagliata del brief lasciava la suite verde. — non dichiarato nel registro.

**R69** — Ruling: la cura per I-3 (`/api/mesh/9` costa 14,89 s e 1.088 MB di picco ad ogni clic) e' riusare la cache su disco gia' scritta in `core/viewport.py`. — accolto anche il «cosa non fare» del revisore — i 7,6 MB di corpo non sono il problema, una decimazione qui sarebbe fuori posto. — non dichiarato nel registro.

**R70** — Ruling: il Minore M-4 (didascalia «nessun artefatto» per lo step 8 con `simplify.enabled=false`) non viene corretto. — la giustificazione del rapporto era sbagliata, ma la conclusione regge — `apriDettaglio` mostra `enabled=false` nel pannello accanto, nello stesso istante. — non dichiarato nel registro.

**R71** — Ruling: un controllo del coordinatore era sbagliato, non il codice — il comando di taglio sullo step 2 era gia' nascosto (`querySelector` trova un elemento anche dentro un contenitore con `hidden`). — stessa forma dell'errore del rilevatore impeccable (R28) — uno strumento che risponde senza guardare cio' che si crede stia guardando. — non dichiarato nel registro.

**R72** — Ruling: verificate contro `git log` tre revisioni mancanti (Task 15a, Task 8 giro 1, Task 13), trovate da Mario e non dal coordinatore; dispacciate subito. — seconda volta stanotte, peggiore della prima — il Task 15a produce il documento che finisce in appendice alla tesi. — non dichiarato nel registro.

**R73** — Ruling: la revisione del Task 13 tenuta indietro di proposito, parte solo quando il giro 2 del Task 9 (stessi file) committa. — un revisore che leggesse ora giudicherebbe codice meta' del quale non e' nel diff dato; il problema di fondo — con cinque agenti in volo il coordinatore teneva il conto degli agenti, non dei task. — non dichiarato nel registro.

**R74** — Ruling: le voci di `/api/cloud` e del contorno condividevano il marchio della sorgente (rischio di sfratto reciproco); corretto spostando il contorno in `.cache/viewport/contorno/`, con test che verifica che entrambe le voci sopravvivano. — verificato eseguendo, non dedotto, che oggi non accade solo perche' l'unico artefatto a rischio risponde 400; l'invariante reggeva per una ragione che sta in un altro modulo. — non dichiarato nel registro.

**R75** — Ruling: correggere (ma non subito, non da solo) — la riga d'errore riceve testo mentre e' ancora `hidden`; la forma giusta e' tenere la regione sempre nell'albero e vuota. — correzione minima ma non verificabile senza un lettore di schermo vero; va nello stesso giro che tocca `app.js` per altro. — chi usa un lettore di schermo puo' non sentire il motivo di un rifiuto; nessun dato perso, nessun numero della tesi toccato.

**R76** — Ruling: rilievo reale ma di gravita' minore di M-1 — `/api/config`/`/api/metrics` letti senza guardare `risposta.ok`; entra nello stesso giro di R75, non prima. — a differenza di M-1, qui i dati si rileggono ad ogni apertura del pannello, quindi non c'e' nulla da avvelenare. — in un difetto futuro del server il pannello resta bianco senza dire perche'.

**R77** — Ruling: il pannello resta senza copertura automatica — accettato e dichiarato, non coperto. — coprirlo vuol dire un motore di DOM fra le dipendenze, vietate dalla spec. — ogni difetto che vive solo nel comportamento del browser lo trova chi apre la pagina — va scritto nel documento della mattina.

**R78** — Ruling: il commit `f716729` e', da solo, rosso — colpa del coordinatore; si lascia il commit dov'e' e si dichiara, non si riscrive. — riscriverlo vuol dire un rebase (vietato dai vincoli); la storia che nasconde un errore vale meno del record. — chi fa `git bisect` su questo ramo trova un commit rosso e deve saltarlo.

**R79** — Ruling: I4 (report15a: «attese» calcolata dalla lista ricevuta) non e' un difetto del Task 15a — portato nel brief del 15b come requisito suo. — il chiamante vero (che fara' il `glob`) e' il passo 15b, non ancora scritto. — se il 15b non lo raccoglie, resta un controllo che non puo' mai fallire — il difetto peggiore perche' ha l'aria di un controllo.

**R80** — Ruling: nessuna correzione per la dipendenza dall'ordine vista una volta dal revisore; riprovato dal coordinatore con corse ripetute a ordine casuale, nessuna dipendenza visibile. — corse verdi ripetute non provano l'assenza di una dipendenza dall'ordine, provano solo che non si ripresenta facilmente — si continua a osservarla. — un test che fallisce a intermittenza; il modo giusto di trovarlo e' il seme che `pytest-randomly` stampa ad ogni corsa.

**R81** — Ruling: la guardia sull'ordine ha un buco — le funzioni freccia asincrone inline gli sfuggono; l'estensione entra nel Task 10, non un giro a se'. — un commit a se' su un file conteso costa piu' del difetto; il Task 10 e' il primo lavoro che il buco lascerebbe passare. — se il Task 10 non ce la fa e nessuno lo raccoglie, resta una regola sorvegliata a meta'.

**R82** — Ruling: brief del Task 10 (vecchio di quattro task) corretto in un addendum che vince sul brief; quattro conflitti veri sanati (`ingombro()` gia' esistente, `this._box`, test che passerebbe per la ragione sbagliata, `points_after` scritto due volte), piu' un punto non nominato (`/api/crop` scrive su disco). — riscrivere il brief cancellerebbe la traccia di che cosa il piano diceva davvero — quarta volta che il piano si rivela vecchio. — l'implementatore legge due documenti e puo' seguire quello sbagliato dove si contraddicono; l'aggiunta dice in testa quale vince.

**R83** — Ruling: le due correzioni di accessibilita' rimaste dal Task 8 (R75, R76) entrano nel Task 10 invece di aprire un giro proprio. — stesso ragionamento di R25 — un ciclo dispaccio-revisione per quattro righe costa piu' della correzione. — due correzioni piccole entrano in un commit che parla d'altro — il messaggio di commit deve nominarle.

**R84** — Ruling: di impeccable e' stato usato solo `init`, non i sette comandi chiesti da Mario; ordine cambiato — passaggio impeccable sul sistema visivo (`typeset`/`colorize`/`layout`/`animate`) PRIMA dei Task 11/12b/14, poi Task 16. — i Task 11/12b/14 aggiungono pannelli nuovi — farli prima significa scriverli contro un sistema visivo che poi cambia. — i tre task slittano dietro il passaggio di design e possono finire tagliati — va scritto nel documento della mattina con la ragione.

**R85** — Ruling: BL-1 (test dell'ordine cieco alle funzioni freccia) e' gia' chiuso dal Task 10 — verificato per mutazione dal coordinatore stesso, nessun giro aperto. — il controllo che mancava adesso c'e' e morde sulla riga esatta che il revisore aveva usato per dimostrare che non mordeva. — nessuno visto; il tetto dichiarato (graffe dentro stringhe/commenti) resta e va nel documento della mattina.

**R86** — Ruling: BL-2 (cache del contorno con chiave incompleta come versione) apre un giro; chieste entrambe le difese — costante di versione nel nome della voce E controllo `facce.max() < len(vertici)` in lettura. — proteggono da guasti diversi — la versione copre il cambio di codice, il controllo in lettura copre il file gia' sul disco; prenderne una sola lascia scoperto l'altro. — una riga di codice in piu' e un ricalcolo in piu' quando la versione cambia.

**R87** — Ruling: IM-2 (`disattivaTaglio` non raggiungibile), IM-3 (piano complanare alla faccia estrema), IM-4 (vista non si aggiorna alla rieseсuzione dello step) vanno in un giro loro, sui file dell'interfaccia. — stessi file, stesso ragionamento; IM-3 dipende da come si risolve IM-2. — un giro piu' grande e' piu' difficile da revisionare, ma spezzarlo costringerebbe due implementatori a contendersi `app.js`.

**R88** — Ruling: la revisione del Task 10 era stata saltata (terza volta); dispacciata subito. Da adesso ogni commit del ramo deve comparire nella tabella delle revisioni con il file che la copre, controllo eseguito via `git log` prima di dire che qualcosa e' finito. — «ricordarmi» ha fallito tre volte su tre — il controllo dev'essere eseguibile, non ricordabile. — la tabella si aggiorna a mano, quindi puo' mentire se non aggiornata — comunque meglio di prima perche' la discrepanza salta fuori dal confronto.

**R89** — Ruling: trovati nove commit senza revisione, sette del coordinatore stesso; dispacciata una revisione dedicata su tutti e sette insieme. — la regola del metodo tiene il coordinatore fuori dal codice perche' e' la persona meno adatta a giudicare il proprio lavoro — la giustificazione di R25 valeva per una correzione, ripetuta sette volte ha costruito l'insieme di codice che nessuno ha guardato. — un revisore su sette diff sparsi ha meno contesto di uno dedicato — compensato scrivendo per ogni commit che cosa verificare.

**R90** — Ruling: B-1 del Task 10 (`POST /api/crop` con liste di un elemento rompe l'interfaccia) si corregge nell'endpoint, non aggiungendo `validate_assignment` a `SegmentConfig`. — `core/config.py` e' dove vive la verita' dei parametri di tutta la pipeline — cambiarne la validazione sposterebbe il rischio su undici step e due fasi gia' pubblicate. — un'altra tratta futura dovra' rifare la stessa validazione — il duplicato va scritto nel documento finale.

**R91** — Ruling: B-2 (confronto tautologico su `02_segmented.ply`) e' anche difetto del coordinatore — `server.py` legge l'uscita gia' ritagliata dello step 2 invece di riprodurre `remove_outliers`+`crop_box`; entra come secondo bloccante. — l'anteprima fedele deve riprodurre la tratta e non la funzione — quarto principio del progetto. — un numero non riproducibile eseguendo lo step e' peggio di un numero assente; se il costo fosse proibitivo, la risposta accettabile e' dichiarare cosa il numero e' e non e', non fingere.

**R92** — Ruling: adottata come tecnica standard per file di test condivisi la tecnica con cui un implementatore ha messo in indice solo il proprio contenuto senza toccare il file su disco (`git hash-object -w` + `git update-index --cacheinfo`), insieme alla verifica in worktree staccato. — «guarda `git diff --cached`» dice di accorgersi del problema, questa tecnica lo risolve senza aspettare l'altro implementatore. — sono due comandi git poco comuni, sbagliarli e' possibile — il controllo che lo smentisce e' la corsa in worktree staccato.

**R93** — Ruling: B1 del report15a (contraddizione «eseguito»/«ha metriche») e' tornato su «fallito»; terzo giro dispacciato, con requisito che il test nuovo valga per tutti e quattro gli stati. — e' la seconda volta che il difetto torna cambiando stato — un test che ne guarda uno solo lo lascera' tornare una terza volta. — un test piu' largo e' piu' difficile da scrivere e puo' diventare generico al punto di non dire niente.

**R94** — Ruling: smesso di pre-generare i pacchetti di revisione (due su tre azzerati a 0 byte fra scrittura e lettura); il revisore genera il proprio diff. — un file che si azzera fra scrittura e lettura non ha verifica che possa salvarlo — leggere la dimensione dopo la scrittura non protegge da niente perche' il troncamento avviene dopo. — ogni revisore spende due comandi in piu', ma non esiste piu' un bersaglio da controllare.

**R95** — Ruling: una revisione positiva (conformita' e qualita' approvate, nessun bloccante) chiude il task, non se ne apre un altro sullo stesso; unica eccezione il ciclo ralph di impeccable. — i tre giri del Task 15a hanno prodotto correzioni vere ma il terzo ha dovuto correggere due difetti introdotti dal secondo — oltre un certo punto un giro in piu' sposta i difetti invece di ridurli. — qualche minore resta nel ramo — tutti vanno nel documento della mattina.

**R96** — Ruling: la misura del coordinatore sulla calotta non era riproducibile dal revisore (struttura confermata, valori diversi); la geometria di prova va scritta esplicitamente in un test, entra nel Task 12b. — il commit non registrava la geometria — quinto principio applicato al coordinatore stesso: un numero in una docstring del core dev'essere riderivabile. — resta un numero non riderivabile in una docstring del core.

**R97** — Ruling: due Importanti della revisione taglio-e-vista non aprono un ciclo nuovo — mandati come aggiunta al mandato dell'implementatore del Task 10 che ha gia' in mano `app.js`/`test_server.py`. — zero cicli in piu', nessuna contesa di file; il secondo punto e' un test vacuo, categoria di difetto che il progetto esiste per eliminare. — il giro del Task 10 diventa piu' grande e la sua revisione piu' difficile.

**R98** — Ruling: `app.js` entra nel perimetro del ciclo ralph (Task 16) dal giro 2; il criterio di chiusura (punteggio massimo) non si tocca. — il tetto raggiungibile senza `app.js` e' stimato sotto il massimo — Mario ha dichiarato il punteggio massimo non negoziabile, quindi si allarga il perimetro invece di abbassare il criterio. — il ciclo tocca il file piu' grande e piu' conteso — contromisura gia' presente (giro che rompe un test si annulla).

**R99** — Ruling: dal giro 2 il divieto di sottoagenti non si applica ai sottoagenti che `impeccable critique` avvia per conto proprio. — `critique` girava degradato per colpa di un vincolo del coordinatore pensato per altro scopo, non per mutilare lo strumento di misura. — un giro costa piu' agenti e piu' tempo; i punteggi del giro 1 non sono confrontabili col giro 2 in poi.

**R100** — Ruling: il giro 4 parte, ma il mandato principale non e' correggere l'istanza — e' scrivere il test della proprieta' generale (nessuno step riceve due descrizioni incompatibili nello stesso documento). — la diagnosi di quattro giri e' che ognuno ha corretto l'istanza scrivendo un test che guarda la forma della correzione invece della proprieta'. — e' piu' lavoro di una sottostringa e puo' allungare il giro; lasciata la facolta' di dire che non si puo', con la ragione.

**R101** — Ruling: BL-1 del Task 11 (con `method:auto` l'anteprima si ferma prima del vero ramo che lo step 2 percorre) e' un'omissione del coordinatore; giro 2 con obbligo di misurare, vietata la terza strada (ammorbidire le parole). — il brief nominava solo i primi due passi mentre l'addendum del Task 13, scritto lo stesso giorno, gia' elencava la catena intera. — se la tratta intera costa troppo, l'anteprima diventa meno utile — comunque meglio di un numero falso.

**R102** — Ruling: il criterio di chiusura del Task 16 passa dal punteggio massimo a «ogni rilievo o e' chiuso o porta la ragione con la misura»; il ciclo si sospende finche' i punti 11/14/15b non sono costruiti. — lo strumento non e' riproducibile (`critique` 25/40 vs 20/40 sulla stessa interfaccia); il punteggio non si muove col lavoro vero (otto difetti chiusi, punteggio invariato); il massimo e' irraggiungibile per costruzione col prodotto incompleto. — il documento della mattina deve portare la tabella dei rilievi invece di una cifra sola, piu' lungo da leggere.

**R103** — Ruling: R102 annullato in tutte e due le parti su decisione esplicita di Mario; il criterio torna quello della skill (punteggio massimo); il ciclo esce dal perimetro del coordinatore, eseguito da Mario dopo che tutte le altre task sono chiuse. — «Non e' una mia decisione: e' la sua» — il coordinatore non dispaccia altri giri sul Task 16. — nessuno per il coordinatore; resta al progetto il costo di inseguire un punteggio massimo su uno strumento che si muove di cinque punti fra due letture.

**R104** — Ruling: la didascalia del ritaglio (dopo che il giro 2 del Task 10 ha reso `completo` nell'endpoint) non apre un giro suo per sei righe — entra nel Task 11, testo consegnato da usare verbatim. — quattro agenti vivi, uno sta mutando gli stessi due file per verificare i controlli del ciclo impeccable — un quinto agente che scrive li' produce il guasto gia' pagato tre volte. — finche' la riga non entra, l'endpoint dice il vero e la didascalia no — un utente legge un numero che lo step non produrra'.

**R105** — Ruling: il regime scritto dal coordinatore nel brief `task-12b-nucleo.md` («vale finche' il lato del triangolo resta sopra la spaziatura») e' falso; sostituito dall'implementatore con l'errore di corda contro la spaziatura. — misura sulla calotta a 6 mm mostra lato sei volte la spaziatura col verso gia' rovesciato — il lato da solo non determina il regime. — non dichiarato esplicitamente nel registro.

**R106** — Ruling: i quattro rilievi informativi del Task 12b (imprecisioni in docstring del core) non aprono un giro — vanno nel documento della mattina, i primi due in evidenza. — direttiva di Mario esplicita (task con esito positivo non ne apre un'altra), nessuno dei quattro cambia una conclusione. — la tesi cita una docstring imprecisa su una conclusione vera — si corregge in mezz'ora scrivendo il capitolo, ma solo se qualcuno se la ricorda.

**R107** — Ruling: la didascalia del ritaglio (R104) entra con due correzioni al testo — «con method: auto» diventa «con questo metodo»; «e ne terra' di meno» diventa «e non ne terra' di piu'». — entrambe le imprecisioni sono la stessa specie del difetto che la riga esiste per chiudere — un'affermazione piu' forte di quanto il codice garantisca. — «con questo metodo» e' meno esplicito per chi legge oggi con due soli metodi, ma la prudenza del server esiste per quando saranno tre.

**R108** — Ruling: le 30 decisioni su 107 senza il «costo se sbagliato» non si riempiono a posteriori; il documento del mattino dichiara il numero e lascia le voci come sono. — ricostruire adesso il costo che si sarebbe dichiarato allora e' scriverne uno nuovo con la data sbagliata, e un elenco di decisioni serve a essere verificato riga per riga contro il registro. — trenta decisioni si leggono senza il rischio dichiarato e va ricostruito dal contesto per ribaltarne una. E' un costo di lettura, non di correttezza.

**R109** — Ruling: nessun sesto giro; il buco del residuo va scritto per intero nel documento del mattino, col confronto `R-3`/`R-4` che lo misura. — fuori dalla sezione il residuo non vede niente — la stessa frase e' verde fuori e rossa dentro — ma il buco e' piu' piccolo di quello chiuso, e tutti e quattro i ritorni storici del difetto sono nati dentro la sezione. — una contraddizione fra una frase fissa fuori sezione e il corpo del documento passa la rete. Nessuno dei quattro ritorni storici aveva quella forma, ma la ragione e' storica, non strutturale.

**R110** — Ruling: la correzione dell'infinito accettato dai campi decimali e' `allow_inf_nan=False` in `core/config.py`, dispacciata a un implementatore separato invece che a chi l'ha trovata. — `config.py` non era nel perimetro di chi ha misurato il difetto, e sconfinare in un file core mentre altri ci lavorano e' il modo di perdere la suite verde. Misurato che pydantic scrive `.inf` sul disco e `/api/config` risponde poi `null`: dal browser quel residuo non e' rimediabile. — un giro in piu' e una finestra di poche ore in cui il decimale accetta ancora l'infinito.

**R111** — Ruling: `campoParametro` lega `ordine` alla generazione del clic che ha aperto il pannello, quindi due battute sullo stesso campo portano lo stesso numero; apre un giro che deve correggere l'istanza, **censire tutte le tratte** che attendono e poi scrivono, e dire che cosa impedisce la quinta. — e' la quarta volta che il difetto torna sul ramo, e il file lo racconta da solo — `generazione` per i clic, `ultimaGeometria` aggiunto dopo perche' non bastava. Le scritture di parametro sono il terzo requisito e non hanno alcun contatore. — un giro su un file che nessun altro sta toccando. Il rischio opposto e' che la quarta istanza diventi la quinta.

**R112** — Ruling: chiesto al revisore il tempo di adesso e quello a `41edc6e` sullo stesso punto, piu' l'eventuale forma equivalente piu' economica — da dire, non da implementare. — la ricerca del cluster si faceva una volta sul primo punto del gruppo e adesso si fa per ogni punto — 136 chiamate su 4293 cluster — e la decisione fra accettare, accelerare e cambiare strada dipende da un numero che non c'era. — un giro di revisione che spende qualche minuto su una misura che poteva aspettare.

**R113** — Ruling: ogni brief dispacciato termina con la chiamata che alimenta il ciclo di apprendimento di ruflo, scritta insieme alla dichiarazione che potrebbe non esserci e all'ordine di riportarlo invece di insistere. — verificato con tre prove concordi che oggi non e' eseguibile — nessun `mcp__ruflo__*` fra gli strumenti, ricerca per nome a vuoto, e `~/.claude/mcp-needs-auth-cache.json` che elenca `plugin:ruflo-core:ruflo` in attesa di autenticazione dal `2026-08-15T14:17:17Z`. Plugin abilitato e server connesso sono due cose diverse. — una riga in piu' nei brief che gli agenti riportano come non disponibile. Il rischio opposto e' un agente che perde tempo o si inventa una strada, ed e' il motivo per cui il divieto di `npx @claude-flow/cli` resta.

**R114** — Ruling: giro su due test soli, codice intatto; vietata l'ottimizzazione trovata dal revisore (`core.segment.cluster` calcola `labels` e lo butta via). — la revisione ha verificato il codice sul dato vero; e 7-8 secondi su 54-82 non sono il problema. L'ottimizzazione diventera' interessante solo quando la clusterizzazione avra' una cache e il DBSCAN sparira' dal conto. — un giro corto su due test. Il rischio opposto e' chiudere il Task 11 con due regole scritte solo nei commenti.

**R115** — Ruling: il difetto di «Applica il ritaglio» (`valori` e' una chiusura mutata dal vivo, la POST costa ~26 s, due clic in volo fanno divergere schermo e disco) non si dispaccia subito; entra nel giro successivo alla revisione. — il meccanismo che lo correggerebbe e' appena atterrato in `5cd5c3a` e non e' ancora stato rivisto; costruirci sopra e' il modo di far crescere un errore invece di correggerlo. — il difetto resta aperto per il tempo di una revisione, in un'interfaccia che nessuno sta usando in produzione.

**R116** — Ruling: nessuna cache insieme alla correzione; chiesta invece la misura del costo dopo, che decide da sola se il giro successivo serve. — una cache messa insieme alla correzione rende impossibile capire quale delle due ha rotto qualcosa. E la chiave di quella cache dovra' portare i parametri di `segment`, a differenza della cache del contorno che ha per chiave la sola coppia (sorgente, mtime). — un giro in piu' se la misura dira' che il costo non e' sostenibile.

**R117** — Ruling: dispacciato `fix-ordine-e-json-2.md`; la parte che conta e' portare lo scanner del revisore dentro `test_app_js.py` come test vero e renderlo piu' difficile da aggirare, con l'obbligo di scrivere nel rapporto che cosa lo scanner **non** vede. — un test strutturale che si presenta piu' forte di quello che e' da' una sicurezza falsa, ed e' peggio di non averlo. — un giro su un file che nessun altro sta toccando. Il rischio opposto e' chiudere la fase credendo chiusa una serie a sei istanze perche' qualcuno l'ha dichiarato.

**R118** — Ruling: il passaggio dei cinque punti da `=== undefined` a `== null` non e' stato corretto ne' deciso: e' stato dato alla revisione come domanda. — `== null` e' vero sia per `null` sia per `undefined`, quindi fonde i due casi che `corpoLetto` distingueva. Puo' essere la scelta giusta, ma allora i commenti che celebrano quella distinzione sono falsi; distinguere «scelta consapevole con la prosa rimasta indietro» da «distinzione persa per sbaglio» richiede di leggere i commenti attorno. — un rilievo in piu' da valutare per il revisore.

**R119** — Ruling: la prova del clic deve far girare la pipeline vera con l'indice scelto e verificare che il gruppo segmentato sia quello indicato, controllando anche l'ordine delle chiamate contro `pipeline.run`. — un oracolo che riscrive a parte `remove_outliers -> crop_box -> extract_planes -> cluster` e' tautologico: dimostra che il codice fa quello che fa, non che coincida con la corsa. Un ordine diverso da' un residuo diverso e quindi cluster diversi. — una verifica costosa per confermare un risultato probabilmente giusto. Il rischio opposto e' chiudere il Task 11 con una prova circolare dopo tre giri sullo stesso indice.

**R120** — Ruling: la prossima decisione sulla cache si prende contro **96,27 s**, la prima lettura fredda, non contro gli 81,09 s della seconda. — e' cio' che l'utente aspetta davvero quando apre l'interfaccia la prima volta; la cache del filesystem e' fredda sui file da 150 e 101 MB. La conclusione «il costo non e' peggiorato» resta vera a caldo e non blocca niente. — si decide una cache guardando un numero ottimista, cioe' esattamente l'errore che questa misura esisteva per evitare.

**R121** — Ruling: se qualcuno ritocca la risoluzione del cluster o la segmentazione dello step 2, il test end-to-end va promosso a permanente fra i deselezionati **prima** di toccare il codice. — costa una `pipeline.run()` vera e non entra nella suite di ogni commit, ma e' l'unica prova non circolare che il Task 11 possieda, e oggi vive solo dentro `task-11b-review.md`. — «se serve lo riscriviamo» e' il modo in cui una prova costosa scompare.

**R122** — Ruling: da qui in avanti nei brief — una tratta non e' coperta perche' ha una guardia; e' coperta se rendere quella guardia decorativa fa diventare rosso qualcosa. Chiesto di passare tutte e nove le tratte del censimento con quella prova. — e' la stessa distinzione fra dichiarare e misurare che questa fase applica al codice, applicata ai test. — qualche minuto per tratta. Il rischio opposto e' una copertura dichiarata e non misurata.

**R123** — Ruling: chiesto al revisore di derivare l'elenco delle tratte dal codice con un criterio meccanico invece di rileggere la tabella del rapporto, e di rifare la prova su tutte e nove comprese le due dichiarate esenti. — l'elenco e' fatto a mano ed ereditato da due giri prima; un elenco incompleto nasconde difetti quanto uno stretto ne trova. «Non ne ha bisogno» e' un giudizio, non una misura. — una verifica in piu' su un elenco probabilmente completo. Il rischio opposto e' dichiarare chiusa una serie a sei istanze contando le tratte a mano.

**R124** — Ruling: il glob dello scanner diventa `base.rglob("*.js")` filtrato su `vendor/`; messo in coda e non dispacciato subito. — la docstring giustifica l'esclusione di `vendor/` e non dice niente su una sottocartella futura, quindi `ui/pannelli/qualcosa.js` resterebbe fuori **in silenzio**. E' la terza forma della stessa serie — guardia con la grana sbagliata, scanner su un file solo, insieme derivato con un glob che non scende — e ogni volta la difesa non fallisce: tace. In coda perche' il Task 14 e' vivo su `app.js` e due agenti sugli stessi file e' la situazione gia' pagata. — il difetto resta aperto per il tempo del Task 14.

**R125** — Ruling: l'ordine resta 14 → 16 → 17; la proposta di anticipare il Task 17 era sbagliata ed e' ritirata. — il Task 17 deve contenere «che cosa gira e che cosa no» e il punteggio per criterio, che li produce il Task 16. Scriverlo prima significa scrivere gli esiti prima che esistano. Il Task 14 sta prima perche' e' l'ultima funzione: finche' non c'e', il 16 non ha l'interfaccia completa da vestire. — due file di troppo nel repository, cancellabili con un commit.

**R126** — Ruling: nei brief, prima del commit, `git status --short` sulle cartelle di sola lettura, e attenzione ai filtri `-k` troppo larghi quando c'e' una mutazione applicata. — un filtro per sottostringa non sa quali test toccano il dato vero; il brief vieta di **scrivere**, non di **selezionare male**, e una mutazione innocua e' diventata una scrittura reale dentro la cartella che non si tocca. — una riga in piu' nei brief. Il rischio opposto e' una scrittura dentro la tabella della tesi che nessuno nota, ed e' mancato poco.

**R127** — Ruling: il giorno in cui la galleria — o qualunque tratta sotto quella difesa — acquista un endpoint di scrittura reale, la sonda va rinforzata per interrogare anche con un corpo JSON minimo, **prima** che l'endpoint esista. — la sonda chiama senza corpo, FastAPI risponde 422 prima di eseguire il gestore, e la scrittura non parte mai — quindi il test non puo' vederla. Oggi nessun endpoint reale ci casca, ma la difesa e' piu' stretta di come si presenta, ed e' la quarta volta che questa forma compare nella fase. — una riga di sonda in piu' il giorno in cui serve.

**R128** — Ruling: il ciclo automatico con ralph loop non prosegue oltre i due giri gia' fatti; da qui in avanti il lavoro sull'interfaccia lo conduce l'utente a mano, senza tetto di dieci cicli e senza un commit per giro. Restano vincolanti la suite verde e il punteggio per criterio. — decisione esplicita dell'utente del 16/08. Gli Step 1-5 del task restano come riferimento di merito, non come procedura. — gli Step 1-5 non hanno piu' un esecutore automatico che li spunti, quindi il merito va verificato a mano e dichiarato nel documento del mattino invece di essere dedotto dal registro dei giri.

**R129** — Ruling: i cinque Priority Issues della critica del giro 3 non si correggono alla spicciolata: entrano in un piano scritto di otto task, con la critique stessa come spec. — il filo conduttore e' uno solo — `exit_code`, `secondi` e `default` sono tre informazioni che il prodotto gia' possiede e gia' manda al browser, e non legge. La maggior parte delle task le legge invece di disegnare qualcosa di nuovo, e un piano rende visibile che sono la stessa correzione ripetuta. — un piano di 1936 righe per cinque rilievi. Il rischio opposto e' cinque correzioni scollegate che non chiudono la forma comune.

**R130** — Ruling: `app.js` resta un file solo, a 1056 righe piu' ~150 aggiunte dal piano. Le funzioni nuove sono di primo livello. — spezzarlo significherebbe moduli ES aggiuntivi serviti da `/ui/`, altre tratte statiche e un ordine di caricamento nuovo, per un file che una persona sola legge per intero; il progetto non ha una convenzione di moduli multipli per l'interfaccia. Il vincolo che conta davvero e' un altro: la funzione di primo livello e' l'unica forma che `_sorgente_di()` sa estrarre e che il banco sa eseguire. — un file che continua a crescere. Il giorno in cui si spezza, la convenzione va inventata insieme al banco che la sa leggere.

**R131** — Ruling: i sorgenti restano ASCII con una sola eccezione dichiarata — le stringhe **mostrate all'utente** portano gli accenti italiani veri. Commenti, nomi e resto del codice invariati. — che i sorgenti siano ASCII e' una convenzione di repository difendibile; le stringhe proiettate davanti a una commissione non ereditano quel vincolo. — una convenzione a due regimi dentro lo stesso file, che va spiegata a chi arriva dopo.

**R132** — Ruling: `EventSource` senza `onerror` e `caricaStato()` senza `.catch(serverMuto)` non entrano nel piano di chiusura. — sono rilievi reali della persona Riley, ma appartengono a una famiglia sola — il comportamento della pagina quando il server muore — che merita un giro suo con una spec propria invece di una coda in fondo a un piano di chiusura. — l'interfaccia continua ad affermare un tempo trascorso che nessuno sta piu' misurando quando il server cade a corsa viva, e una pagina aperta a server spento resta vuota per sempre senza un messaggio. E' il difetto piu' grosso lasciato aperto da questa fase.

**R133** — Ruling: `/api/cluster` senza comando che lo raggiunga, le scorciatoie da tastiera, `inquadra` esportata e non legata, i 1000 scatti del cursore del taglio: fuori dal piano. — non sono difetti, sono funzionalita' che non c'e'. Vanno da `superpowers:brainstorming`, non da un piano di chiusura dei rilievi. — l'utente esperto resta senza scorciatoie e senza reinquadramento, e dopo un'orbita storta l'unico rimedio e' ricaricare la pagina — che ributta via la geometria appena caricata.

**R134** — Ruling: `analysis.material` non modificabile dall'interfaccia e i campi di `SegmentConfig` senza `description` non sono difetti dell'interfaccia e non entrano nel piano come tali. — toccano il modello di configurazione, non la resa. L'interfaccia rende cio' che `/api/schema` le manda; se il campo non ha descrizione, il rimedio sta in `config.py`. — modulo di Young e densita' — le due cose che una tesista strutturale vorra' cambiare per prime — restano dietro un input in sola lettura che contiene il JSON del modello.

**R135** — Ruling: i due rilievi minori si escludono di proposito, e la ragione e' scritta in testa al Task 7 perche' non tornino a ogni giro. — `.step-stato` da' gia' `color: var(--tenue)` a tutti gli stati e «mai eseguito» ha per ruolo di colore proprio quello neutro — una regola in piu' direbbe la stessa cosa due volte. `preserveDrawingBuffer: true` costa una copia per fotogramma ma sostiene `cattura()`, che serve alle viste in appendice: va misurata prima, non tolta adesso. — una copia per fotogramma pagata per una funzione che oggi nessuno chiama.

**R136** — Ruling: il confronto fra due step e' un interruttore, non una dissolvenza incrociata. — l'attesa a cache fredda la fa la decimazione sul server, non il trasporto, e una geometria vecchia tenuta a video per quei secondi con la didascalia che dice «caricamento» e' la vista che contraddice la propria didascalia — il difetto che questo modulo ha gia' pagato. Il confronto esplicito da' lo stesso valore senza quel rischio. — il passaggio fra le due geometrie e' netto invece che graduale, che e' meno elegante e non meno vero.

**R137** — Ruling: il ciclo di `viewport.js` continua a rendere 60 fps anche a scena ferma; non corretto in questo giro. — il rimedio e' un flag di quattro righe, ma il modo di fallire — un mutatore che dimentica di chiedere il fotogramma lascia a video un'immagine vecchia — non ha qui una guardia economica: `test_viewport.py` sorveglia la decimazione Python, non il JS. Una correzione senza il suo controllo e' esattamente cio' che questa fase non accetta. — sei milioni di punti ridisegnati a vuoto sulla stessa macchina che gira la pipeline con le librerie fissate a un thread.

**R138** — Ruling: l'ultimo giro sull'interfaccia usa `impeccable overdrive`, comando che il piano di Fase 3 non prevedeva fra i sette, per costruire il confronto fra due step. — la domanda per cui lo strumento esiste — che cosa ha fatto questo step alla geometria — non aveva risposta a video: gli undici artefatti si guardavano di fila e mai due insieme. Non richiede nulla da scaricare, sono entrambe le geometrie gia' sulla scheda. — la prova d'uso degli strumenti del Task 17 deve dichiarare un comando in piu' di quelli pianificati, che e' una riga di documento; e il confronto e' superficie nuova, quindi porta con se' tre proprieta' che si rompono in silenzio — coperte da altrettanti banchi nello stesso commit.

---

## 4. I punti della lista di priorita' tagliati, e la ragione

La lista di priorita' e' quella della critique del giro 3: due P0, tre P1, piu' i
rilievi minori e le bandiere rosse delle quattro persone. Il piano
`2026-08-16-meshrec-critica-giro-3.md` ha pianificato i cinque Priority Issues e
ha **tagliato esplicitamente** il resto, con la ragione scritta nella propria
Self-Review perche' non tornasse a ogni giro.

**Pianificato ed eseguito:** i due P0 → Task 1 e 2. I tre P1 → Task 3 (campi del
ritaglio), 4 (Galleria), 5 (scritture irreversibili). La divulgazione progressiva
→ Task 6. I minori con un rimedio misurabile → Task 5 e 7. I due rilievi fuori
perimetro → Task 8.

**Tagliato, con la ragione:**

| Punto tagliato | Ragione | Ruling |
|---|---|---|
| `EventSource` senza `onerror`; `caricaStato()` senza `.catch` | Rilievi reali della persona Riley, ma appartengono a una famiglia sola — il comportamento della pagina quando il server muore — che merita un giro suo con una spec propria, non una coda in fondo a un piano di chiusura. **Costo accettato:** a server morto l'interfaccia afferma un tempo trascorso che nessuno misura, e a server spento resta vuota per sempre senza un messaggio. E' il difetto piu' grosso lasciato aperto. | R132 |
| `/api/cluster` senza comando; scorciatoie da tastiera; `inquadra` non legata; i 1000 scatti del cursore | Non sono difetti: sono funzionalita' che non c'e'. Vanno da `superpowers:brainstorming`, non da un piano di chiusura dei rilievi. **Costo accettato:** il criterio 7 resta a 1/4, e dopo un'orbita storta l'unico rimedio e' ricaricare. | R133 |
| `analysis.material` non modificabile; descrizioni mancanti nei campi | Toccano il modello di configurazione, non la resa: l'interfaccia rende cio' che `/api/schema` le manda. **Chiuso a meta' comunque:** le descrizioni di `SegmentConfig` sono state aggiunte in `02a13b9`; modulo di Young e densita' restano dietro un input in sola lettura. | R134 |
| `.stato-mai-eseguito` senza regola CSS | `.step-stato` da' gia' `color: var(--tenue)` a tutti gli stati, e «mai eseguito» ha per ruolo di colore proprio quello neutro: una regola in piu' direbbe la stessa cosa due volte. | R135 |
| `preserveDrawingBuffer: true` con `cattura()` mai chiamata | Il costo e' una copia per fotogramma, ma la funzione sostiene le viste che finiscono in appendice: va misurata prima, non tolta adesso. | R135 |
| La dissolvenza incrociata fra le due geometrie del confronto | L'attesa a cache fredda la fa la decimazione sul server, non il trasporto: una geometria vecchia tenuta a video con la didascalia che dice «caricamento» e' la vista che contraddice la propria didascalia, difetto che questo modulo ha gia' pagato. L'interruttore da' lo stesso valore senza quel rischio. | R136 |
| Il flag che ferma il ciclo di disegno a scena ferma | Il rimedio e' di quattro righe, ma il modo di fallire — un mutatore che dimentica di chiedere il fotogramma lascia a video un'immagine vecchia — non ha qui una guardia economica: `test_viewport.py` sorveglia la decimazione Python, non il JS. Una correzione senza il suo controllo non viene accettata da questo progetto. **Costo accettato:** sei milioni di punti ridisegnati a vuoto sulla stessa macchina che gira la pipeline a un thread. | R137 |
| L'ottimizzazione di `core.segment.cluster` (restituire `labels`) | Buona e registrata, ma 7-8 secondi su 54-82 non sono il problema, e `core.segment` non si tocca in un giro sui test. Diventera' interessante quando la clusterizzazione avra' una cache e il DBSCAN sparira' dal conto. | R114 |
| La cache della clusterizzazione allineata | Una cache messa insieme alla correzione rende impossibile capire quale delle due ha rotto qualcosa. Chiesta invece la misura, che decide da sola. La chiave dovra' portare i parametri di `segment`, a differenza della cache del contorno. | R116, R120 |
| I 30 «costo se sbagliato» mancanti nel registro | Ricostruire adesso il costo che si sarebbe dichiarato allora e' scriverne uno nuovo con la data sbagliata, e un elenco di decisioni serve a essere verificato riga per riga contro la sua fonte. | R108 |
| Il sesto giro sul residuo del report | Il buco e' piu' piccolo di quello chiuso, e tutti e quattro i ritorni storici del difetto sono nati dentro la sezione. Scritto per intero invece che corretto. | R109 |

**Un taglio di natura diversa, che riguarda il metodo e non un rilievo.** Il ciclo
automatico del Task 16 — `audit` + `critique` con ralph loop, tetto di dieci giri
— e' stato interrotto al secondo giro per decisione dell'utente, e la conduzione
e' passata a mano (R128). Gli Step 1-5 del Task 16 restano come riferimento di
merito e non come procedura. La conseguenza pratica e' che **`impeccable audit`
non e' mai stato eseguito** e che il tetto dei dieci giri non e' mai stato
raggiunto: si veda la sezione 5.

---

## 5. La prova d'uso degli strumenti

Uno strumento non usato e' dichiarato tale, con il motivo. Le righe sono in
ordine di piano.

| Strumento | Usato | Prova |
|---|---|---|
| `superpowers:brainstorming` | **Sì** | Ha prodotto la spec `docs/superpowers/specs/2026-08-13-meshrec-fase-3-interfaccia-design.md` (35 141 byte), citata come `**Spec:**` nell'intestazione del piano di Fase 3. Il piano ne riporta anche una misura presa durante la sessione (riga 3227: «l'asserzione ha misurato il renderer di Open3D durante il brainstorming»). |
| `superpowers:writing-plans` | **Sì** | Due piani: `docs/superpowers/plans/2026-08-13-meshrec-fase-3-interfaccia.md` (**17 task**, 3425 righe dopo le spunte di chiusura del 17/08; erano 3402 prima) e `docs/superpowers/plans/2026-08-16-meshrec-critica-giro-3.md` (**8 task**, 1936 righe), quest'ultimo con la critique come spec. |
| `superpowers:subagent-driven-development` | **Sì** | Dichiarato come sotto-skill obbligatoria alla riga 3 di entrambi i piani. Il roster dei dispacci e' registrato in `fase-3-registro-decisioni.md` (righe 1480-1487 e la tabella 1720-1723). Residuo materiale: `.superpowers/sdd/` nel repository, e il commit `e334a15` che rimuove il report di lavoro della Task 8. |
| `superpowers:test-driven-development` | **Sì** | Ogni task che tocca codice nel piano della critica apre con «Step 1: Scrivere il controllo che fallisce» (per esempio Task 7, riga 1531). La suite e' passata da **181 test raccolti** di riferimento iniziale a **494 passati**. R122 ne e' l'inasprimento: una tratta non e' coperta perche' ha una guardia, e' coperta se rendere quella guardia decorativa fa diventare rosso qualcosa. |
| `superpowers:verification-before-completion` | **Sì** | Vincolo dichiarato del Task 16 («la suite resta verde», `uv run pytest` fra una modifica e l'altra). Applicato fino all'ultimo commit: `e0b84e1` chiude il proprio messaggio con «`uv run pytest`: 494 passati, 3 saltati» e con due mutazioni provate sul segnale nuovo — `if (true)` sul rilevamento e fondo al posto dell'anello — che lo fanno rosso. |
| `impeccable init` | **Sì** | Ha prodotto `PRODUCT.md`, che porta il marcatore `<!-- impeccable:product-schema 1 -->` alla riga 3. Commit `dbc466f`. |
| `typeset` | **Sì** | Commit `aaa720e`: «Quattro passaggi con impeccable — typeset, colorize, layout, animate — sul solo foglio di stile». Esito tipografico: una scala dichiarata di quattro ruoli al posto di nove misure decise una alla volta, con il fondo scala a 13 px perche' l'interfaccia viene proiettata in discussione. |
| `colorize` | **Sì** | Stesso commit `aaa720e`. Le tre tinte di stato erano scritte a mano dentro le regole e diventano ruoli: fuori da `:root` non resta un esadecimale. Introdotto `--bordo-comando`, perche' `--bordo` misurava 1,41:1 sul bianco ed era l'unico indizio che un campo si potesse toccare (WCAG 1.4.11 chiede 3:1). |
| `layout` | **Sì** | Stesso commit `aaa720e`: spazio di 4 px e multipli, e la sparizione di `height: calc(100vh - 3rem)`, dove quel `3rem` era l'altezza della testata misurata una volta e mai piu' riverificata. Ripreso in `dc30504`. |
| `animate` | **Sì**, due volte | `aaa720e` per i tre movimenti iniziali; `e0b84e1` per il segnale di cambio stato. In entrambi `prefers-reduced-motion` toglie cio' che si muove e lascia cio' che informa — un'alternativa intenzionale e non un azzeramento globale, come il Task 16 Step 2 richiedeva. La misura che ha deciso la forma del segnale: un velo del proprio colore al 24% dava 3,85:1 su «non valido», sotto il 4,5:1 di WCAG 1.4.3; l'anello sta fra 5,41:1 e 7,71:1. |
| `impeccable audit` | **No** | Mai eseguito. Il piano lo prevedeva al Task 16 Step 3, dentro il ciclo ralph con `critique`; il ciclo e' stato interrotto al secondo giro e la conduzione e' passata a mano (R128). Prova materiale: `.impeccable/` contiene la sola sottocartella `critique/`, nessuna `audit/`. |
| `impeccable critique` | **Sì**, tre volte | I tre file in `.impeccable/critique/`: `2026-08-14T17-47-36Z`, `2026-08-14T18-50-32Z` e `2026-08-16T11-21-22Z`, tutti su `index.html`. I primi due sono i giri 1 e 2 del ciclo ralph; il terzo e' il giro 3, condotto a mano. |
| `impeccable overdrive` | **Sì**, e **non previsto dal piano** | Commit `e0b84e1`, che dichiara «Due giri di `impeccable` sull'interfaccia: `animate` e `overdrive`». Ha prodotto il confronto fra due step: `svuota()` non distrugge piu' la geometria uscente ma la sposta in un secondo gruppo, e un interruttore la rimette a video nella stessa inquadratura. R138. |
| ralph loop | **Sì, parzialmente** | Due giri su un tetto di dieci. Giro 1 dispacciato con `task-16-ralph.md` (registro, riga 2613: «il ciclo ralph e' partito, giro 1 di dieci»); giro 2 alla riga 2847. `app.js` e' entrato nel perimetro del ciclo dal giro 2 (R98). Il ciclo **non e' arrivato al terzo giro**: interrotto per decisione esplicita dell'utente, con la conduzione passata a mano (R128, che chiude la sequenza R102 → R103). |
| `ruflo` | **Sì come roster, no come gancio** | Il roster degli agenti e' stato usato per tutta la fase: `ruflo-core:coder` e `ruflo-core:reviewer` compaiono nella tabella dei dispacci del registro (righe 1720-1723) e nell'elenco alle righe 1480-1487. Il **gancio MCP `hooks_task-completed`**, che R113 prescrive in coda a ogni brief, **non e' mai stato eseguibile**: verificato con tre prove concordi — nessun `mcp__ruflo__*` fra gli strumenti, ricerca per nome a vuoto, e `~/.claude/mcp-needs-auth-cache.json` che elenca `plugin:ruflo-core:ruflo` in attesa di autenticazione dal `2026-08-15T14:17:17Z`. Il divieto di `npx @claude-flow/cli` resta, ed e' il motivo per cui tre agenti hanno rifiutato i ganci. |
| `caveman` | **Sì** | Vincolo esplicito nei dispacci: ogni agente doveva invocare `caveman:caveman` prima di lavorare (registro, righe 425 e 1491-1493), con l'avvertenza scritta che `caveman:caveman` non e' `caveman-init` e non richiede di scaricare nulla dalla rete. |
| `ponytail` | **Sì** | Stesso vincolo e stessi punti del registro (righe 425 e 1491): `ponytail:ponytail` invocato prima di lavorare, insieme a `caveman:caveman`, in tutti e tre i dispacci di quel blocco. |

**Tre comandi suggeriti dalla critique e mai eseguiti come comandi.** La critique
chiudeva ciascun Priority Issue con un comando — `/impeccable harden` per i due
P0 e per i campi del ritaglio, `/impeccable layout` per la Galleria,
`/impeccable clarify` per le scritture irreversibili. Nessuno dei tre e' stato
lanciato: il lavoro e' stato fatto dal piano scritto
`2026-08-16-meshrec-critica-giro-3.md`, che tratta i cinque rilievi come una
correzione sola (R129). I rimedi che quei comandi avrebbero prodotto sono nei
Task 1-5 di quel piano.

**Una nota sull'ordine, perche' e' stata una decisione e non un caso.** R84
registra che a meta' fase di `impeccable` era stato usato **solo `init`**, mentre
ne erano stati chiesti sette, e che l'ordine e' stato corretto di conseguenza: il
passaggio sul sistema visivo (`typeset`/`colorize`/`layout`/`animate`) e' stato
messo **prima** dei Task 11/12b/14, perche' costruire pannelli nuovi contro un
sistema visivo che poi cambia significa riscriverli. Il costo dichiarato in quel
ruling — «i tre task slittano dietro il passaggio di design e possono finire
tagliati» — non si e' verificato: 11, 12b e 14 sono stati consegnati.

---

## Provenienza di questo documento

| Affermazione | Fonte |
|---|---|
| 494 passed, 3 skipped, 6 deselected, 39.74s | `uv run pytest` da `meshrec/`, 17/08/2026, commit `e0b84e1` |
| 181 test di riferimento iniziale; 399 passed al 16/08 | piano di Fase 3, Global Constraints e tabella di stato |
| 21/40, 2 P0, 3 P1, tabella G2/G3, carico cognitivo 6/8 | `.impeccable/critique/2026-08-16T11-21-22Z__…md`, frontmatter e corpo |
| «25 → 20 → 21 non e' una misura» | stessa critique, sezione *Sul confronto fra i tre numeri*; e R102 |
| 38 commit dopo la critique, 24 sull'interfaccia | `git log --since='2026-08-16 13:21'`, con e senza `-- meshrec/src/meshrec/ui` |
| 17 tratte HTTP | decoratori `@app.get/post/put` in `src/meshrec/app/server.py` |
| gli undici step | `src/meshrec/core/steps.py:19-31` |
| legenda dei quattro stati; regione dell'esito; `tabindex` della Galleria | letti in `src/meshrec/ui/index.html`, righe 46-55, 20, 153-154 |
| assenze da non fabbricare (Abaqus, casi studio, utenti, confronti) | `PRODUCT.md`, sezione *Evidence on Hand* |
| R1–R127 | `meshrec/docs/fase-3-registro-decisioni.md` |
| R128–R138 | piano `2026-08-16-meshrec-critica-giro-3.md` e messaggi di commit del 16–17/08 |
| duplicazione di 19 rulings nel registro | conteggio sulle intestazioni di sezione, 17/08 |
| `impeccable audit` mai eseguito | contenuto di `.impeccable/`: la sola sottocartella `critique/` |
| gancio MCP di ruflo non disponibile | R113, con le tre prove che vi sono registrate |

**Che cosa questo documento non ha verificato.** Il Task 16 e' stato chiuso su
decisione dell'utente senza una rilettura del codice riga per riga: le
attribuzioni «chiuso da <commit>» della sezione 2 vengono dalla Self-Review del
piano e dai messaggi di commit, salvo i quattro punti dove e' scritto **letto nel
codice**. Il punteggio 21/40 non e' stato rimisurato dopo i 38 commit che lo
seguono, e non esiste quindi un numero che descriva l'interfaccia di oggi.
