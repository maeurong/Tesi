# Inventario rulings — Fase 3 interfaccia

Totale decisioni trovate: **107** (R1–R107, nessun buco; R15 compare due volte nella numerazione).
Registro letto il: **2026-08-14**.

---

### R1 — `create_app` prende `config_path`, non `root`

- **Deciso:** `app.server.create_app` prende `config_path: Path`, non `root`.
- **Perche':** codice e test del Task 1 concordano su `config_path`; legare l'app a un file di config rende sensati `GET`/`PUT /api/config`.
- **Costo se sbagliato:** servirebbe un secondo parametro per la radice esperimenti, oggi ricavato da `config_path.parent`.
- **Stato:** in vigore.

### R2 — il contratto endpoint esclude lo streaming

- **Deciso:** insieme `STREAMING = {"/api/events"}` dichiarato nel modulo di test, commentato, esclude le rotte in streaming dal contratto sugli endpoint.
- **Perche':** `TestClient.get` su un generatore SSE senza fine bloccherebbe la suite dal Task 5 in poi; `/api/events` ha test dedicato con `max_eventi`.
- **Costo se sbagliato:** un endpoint in streaming futuro sfugge al contratto se l'insieme non resta corto e commentato.
- **Stato:** in vigore.

### R3 — gli helper `_config_cubo*` vanno creati

- **Deciso:** `_config_cubo(tmp_path)` e `_config_cubo_su_disco(tmp_path)` vanno creati come helper di modulo, riproducendo la costruzione gia' presente nei file.
- **Perche':** il piano li citava come esistenti; e' un difetto del piano, non del codice.
- **Costo se sbagliato:** i test nuovi girerebbero su geometria diversa da quella della Fase 1, numeri non confrontabili con quelli archiviati.
- **Stato:** in vigore.

### R4 — prefisso `config.` nei test nuovi

- **Deciso:** i test nuovi in `tests/test_config.py` usano il prefisso `config.` (`config.PipelineConfig`, ecc.).
- **Perche':** uniformita' col file esistente, che importa `from meshrec.core import config`.
- **Costo se sbagliato:** solo un `NameError` immediato in sviluppo.
- **Stato:** in vigore.

### R5 — ramo `.vtu` precede `read_triangle_mesh`

- **Deciso:** nel Task 9 il ramo `.vtu` precede `o3d.io.read_triangle_mesh`.
- **Perche':** `read_triangle_mesh` su un `.vtu` non restituisce la geometria attesa; leggere due volte lo stesso file da 34,7 MB e' spreco puro.
- **Costo se sbagliato:** il contorno del volume esce vuoto, il test sui conteggi lo rivela subito.
- **Stato:** in vigore.

### R6 — commento errato nel Task 15

- **Deciso:** il commento `# solo per numpy` va corretto: Open3D serve per `o3d.io.read_image`.
- **Perche':** un commento che dice il falso e' peggio di nessun commento.
- **Costo se sbagliato:** nulla, e' prosa.
- **Stato:** in vigore.

### R7 — three.js vendorizzato nel Task 1, in due file

- **Deciso:** three.js vendorizzato durante il Task 1 invece che nel Task 7, in due file (`three.module.js` 603.113 B + `three.core.js` 1.403.455 B = 2.006.568 B, non uno come stimava la spec); Task 7 Step 1 riscritto di conseguenza.
- **Perche':** il piano dichiarava la rete come unico rischio bloccante della notte; verificarlo per primo lo toglie di mezzo prima che costi sei task.
- **Costo se sbagliato:** i due file pesano 800 KB piu' del previsto, irrilevante contro i 400 MB di artefatti gia' presenti.
- **Stato:** in vigore.

### R8 — `httpx2` accettato nel gruppo dev

- **Deciso:** `httpx2>=2.10.0` nel gruppo dev e' accettato, benche' la spec dichiarasse solo `fastapi`/`uvicorn`.
- **Perche':** e' dipendenza di starlette/testclient, non dell'app; i 191 test passano con `httpx2` presente e `httpx` assente; nome verificato non typosquat.
- **Costo se sbagliato:** una dipendenza di test in piu' nel gruppo dev, non entra nella distribuzione ne' nel wheel.
- **Stato:** in vigore.

### R9 — rilevatore impeccable e' ora intero

- **Deciso:** il rilevatore impeccable e' intero, non piu' degradato; il quesito Q1 e' chiuso.
- **Perche':** i quattro moduli di parsing sono stati installati nella cache dei plugin; prova di controllo su pagina rotta apposta conferma le tre capacita' dichiarate perse.
- **Costo se sbagliato:** nulla nel repository.
- **Stato:** in vigore.

### R10 — residui npm non cancellati

- **Deciso:** `package.json`, `package-lock.json`, `node_modules/` (4,7 MB) restano non tracciati nella radice, non cancellati.
- **Perche':** cancellare e' irreversibile e non compra nulla; sono non tracciati, la regola «mai `git add -A`» impedisce che entrino in un commit; l'utente era tornato a dormire, senza dare consenso.
- **Costo se sbagliato:** 4,7 MB di ingombro su disco finche' l'utente non li rimuove.
- **Stato:** in vigore.

### R11 — minor del Task 1 anticipato al Task 3

- **Deciso:** il minor del Task 1 (`steps.py:119-120`, `(voce or {}).get(...)`) non apre un giro suo, entra come requisito esplicito nel dispaccio del Task 3.
- **Perche':** il Task 3 riapre `steps.py` per `write_state`, la correzione costa una riga in lavoro gia' previsto; contraddice il contratto dichiarato «uno stato illeggibile e' uno stato assente».
- **Costo se sbagliato:** la correzione slitta di un task; nel frattempo uno `steps.json` corrotto in modo specifico farebbe fallire `run_state` invece di riportare «mai eseguito».
- **Stato:** in vigore.

### R12 — `runs/sweep/` di sola lettura, verifiche su `prova-interfaccia`

- **Deciso:** `meshrec/runs/sweep/` trattata come sola lettura al pari delle altre quattro cartelle; verifiche manuali su `runs/prova-interfaccia/`, config `prova-interfaccia.yaml` derivata da `lab.yaml` cambiandone solo `run.out_dir`.
- **Perche':** `lab.yaml` (tracciato) punta alla cartella del candidato adottato dalla Fase 2; eseguire `meshrec run lab.yaml` la riscriverebbe e `sweep verify` dichiarerebbe stantia una riga della tabella sperimentale della tesi.
- **Costo se sbagliato:** 400 MB di disco in piu' per una corsa di prova separata, contro il rischio di invalidare la provenienza del candidato adottato.
- **Stato:** in vigore.

### R13 — scrittura atomica `nome.tmp.ply`

- **Deciso:** accettata la correzione dell'implementatore, `nome.tmp.ply` (non `nome.ply.tmp` come da piano); glob di `scarta_temporanei` portato a `*.tmp.*`.
- **Perche':** il piano sbagliava — Open3D non riconosce piu' `.ply` se l'estensione finale e' `.tmp`; verificato che nessun artefatto vero del progetto contiene la sottostringa `.tmp.`.
- **Costo se sbagliato:** un file dal nome sfortunato verrebbe cancellato all'avvio di una corsa, ma nessun nome del progetto ha quella forma.
- **Stato:** in vigore.

### R14 — commento stantio in `sweep.py:528` anticipato al Task 3

- **Deciso:** il commento stantio di `sweep.py:528` entra nel Task 3 invece di aspettare la revisione finale.
- **Perche':** stesso motivo di R11 — una riga, il Task 3 tocca la funzione che il commento descrive; un commento che descrive un meccanismo superato e' un'affermazione falsa nel codice.
- **Costo se sbagliato:** resta una frase imprecisa in un commento per qualche ora.
- **Stato:** in vigore.

### R15 — il passo 4 del Task 4 riscritto prima del dispaccio

*(nota: il numero R15 compare due volte nel registro — una voce senza contenuto seguita dalla voce reale; vedi riga di ripetizioni in fondo.)*

- **Deciso:** il passo 4 del Task 4 non trasforma `if start <= N:` in `if start <= N <= stop:` come da piano; le guardie restano invariate, l'arresto avviene per interruzione del flusso con un'eccezione `_FermataRichiesta` catturata e assorbita.
- **Perche':** quelle guardie hanno rami `else` di ripresa che ricaricano da disco l'artefatto di step saltati; con `stop < N` il ramo `else` avrebbe letto artefatti da non toccare. Trovato leggendo il codice vero di `pipeline.run`, non fidandosi del testo scritto dal coordinatore.
- **Costo se sbagliato:** un'eccezione per controllo di flusso e' meno leggibile di una condizione, ma e' l'unica forma che non tocca le guardie di ripresa gia' collaudate.
- **Stato:** in vigore.

### R16 — corsa parziale fonde `metrics.json`

- **Deciso:** una corsa parziale (`from_step > 1` o `to_step < 11`) fonde le proprie metriche in `metrics.json` invece di sostituirlo; una corsa intera sostituisce come oggi; il valore restituito e' il dizionario fuso.
- **Perche':** l'interfaccia esegue uno step alla volta — se ogni step sostituisse il file, il pannello perderebbe tutto a monte; effetto collaterale voluto: anche `meshrec run --from-step 5` non butta piu' via le metriche a monte.
- **Costo se sbagliato:** `metrics.json` puo' contenere righe misurate con configurazioni diverse, ma `steps.json` e la catena di impronte lo dichiarano — l'informazione non e' persa.
- **Stato:** in vigore.

### R17 — test sul ramo `except BaseException` anticipato al Task 4

- **Deciso:** il secondo minor del Task 3 (nessun test end-to-end sulla scrittura dello stato «fallito») entra come requisito nel Task 4.
- **Perche':** e' il difetto peggiore emerso finora — un meccanismo che scrive un'affermazione su disco senza controllo che la smentisca; la prova costa poco perche' il Task 2 ha gia' lasciato un test che fa fallire una corsa vera.
- **Costo se sbagliato:** la registrazione dei fallimenti resta non provata per un altro task.
- **Stato:** in vigore.

### R18 — ordine delle assegnazioni nel test dell'accumulo

- **Deciso:** accettata la correzione dell'ordine delle due assegnazioni nel test (`to_step` prima di `from_step`), senza toccare il codice di produzione.
- **Perche':** `RunConfig` ha `validate_assignment=True` piu' un validatore incrociato; verificato di persona che `from_step=2` con `to_step` ancora a 1 e' correttamente rifiutato, e il caso reale dell'interfaccia non incontra la trappola.
- **Costo se sbagliato:** un chiamante futuro che riusa un oggetto config gia' ristretto incontra un `ValidationError` chiaro, non un comportamento silenzioso.
- **Stato:** in vigore.

### R19 — ordine `from_step`/`to_step` in `cli.py`

- **Deciso:** rilievo Important accettato — `cli.py` assegna `from_step` prima di `to_step`; corretto invertendo l'ordine delle due righe.
- **Perche':** con `to_step` gia' ristretto sul disco lo step richiesto non gira affatto, e l'errore viene inghiottito dall'`except Exception` di `main`; la verifica precedente del coordinatore era incompleta (dedotta, non letta sui chiamanti).
- **Costo se sbagliato:** nulla — la correzione e' l'inversione di due righe piu' il test che la copre.
- **Stato:** sostituita da R41 (l'ordine scelto salva solo il primo dei due casi di rottura e lascia aperto il secondo; R41 sostituisce l'inversione con l'assegnazione congiunta dei due campi in un `RunConfig` nuovo).

### R20 — minor del Task 5 anticipato al Task 8

- **Deciso:** il minor del Task 5 (secondi trascorsi sbagliati per un client che si connette a lavoro gia' in corso) entra come requisito nel Task 8 invece di finire alla revisione finale.
- **Perche':** e' un numero mostrato che puo' essere falso, non cosmesi — stessa famiglia dei difetti che questa fase esiste per evitare.
- **Costo se sbagliato:** il tempo trascorso resta impreciso solo per un client che si collega a lavoro gia' avviato, caso raro con utente singolo.
- **Stato:** in vigore.

### R21 — i 27,5 s di `decimate` si dichiarano, non si correggono

- **Deciso:** i 27,5 s di `decimate` sulla nuvola vera si dichiarano, non si correggono.
- **Perche':** l'ipotesi che la ricerca del passo sprecasse il tempo e' smentita dalla misura — l'esponente reale del legame passo/punti e' ~1,45 non 2, una stima taglierebbe le passate solo da ~4 a ~2 (~50%, non millisecondi); la lettura del file pesa solo l'1,5% del tempo.
- **Costo se sbagliato:** l'utente aspetta 27 s al primo caricamento di ogni step sulla scansione reale — l'effetto peggiore fra quelli parcheggiati finora.
- **Stato:** annullata da R23 (revocata su richiesta esplicita dell'utente, che ha chiesto la correzione con entrambe le leve).

### R22 — messaggio d'errore step fuori intervallo

- **Deciso:** il messaggio `{"errore":"KeyError","messaggio":"99"}` per uno step fuori intervallo entra come requisito nel Task 8.
- **Perche':** difetto trovato con `curl` contro un server vero — struttura dell'errore giusta ma testo inutile a chi legge; il Task 9 introdurra' lo stesso schema di accesso ad `ARTIFACTS`, va corretto prima che si duplichi.
- **Costo se sbagliato:** un messaggio d'errore poco chiaro in un caso che l'interfaccia da sola non produce.
- **Stato:** in vigore.

### R23 — Task 6-bis: stima del voxel piu' cache su disco

- **Deciso:** R21 revocato su richiesta esplicita dell'utente; nasce il Task 6-bis (stima iniziale del passo, quattro giri diventano due; cache del risultato in `meshrec/.cache/viewport/`, non nella cartella della corsa; `_ESPONENTE_DENSITA = 1.45` come costante di modulo in `viewport.py`).
- **Perche':** la misura diretta da' numeri piu' netti della stima del revisore (25,7 s su 33,6 s sprecati nei primi due raddoppi); la cache non sta nella cartella corsa perche' un server puntato su `runs/lab_crop` non deve poterci scrivere.
- **Costo se sbagliato:** la stima puo' solo costare un giro in piu', mai un risultato errato, perche' il ciclo di raddoppio resta e garantisce il budget.
- **Stato:** in vigore.

### R24 — Task 6-bis dispacciato dopo il Task 7, non in parallelo

- **Deciso:** il Task 6-bis si dispaccia dopo il rientro del Task 7, non in parallelo.
- **Perche':** i file non si sovrappongono, ma due agenti che committano insieme sullo stesso ramo si contendono `.git/index.lock`.
- **Costo se sbagliato:** si perdono i minuti di attesa del Task 7.
- **Stato:** in vigore.

### R25 — minor del Task 7 corretto direttamente dal coordinatore

- **Deciso:** il minor del Task 7 (`!risposta.ok` di `mostraNuvolaDelloStep` non svuotava la scena) corretto direttamente dal coordinatore, senza aprire un giro di dispaccio.
- **Perche':** quattro righe in due file che nessun altro agente tocca; il ciclo dispaccio-revisione costerebbe piu' della correzione; il rilievo era gia' stato trovato e formulato da un revisore terzo.
- **Costo se sbagliato:** due modifiche entrano nel ramo senza revisione indipendente, ma la revisione finale del ramo le vedra' nel diff complessivo.
- **Stato:** in vigore.

### R26 — `role="application"` sulla tela, non `role="img"`

- **Deciso:** il rilievo Important del Task 7 (`role="img"` su una tela azionabile da tastiera) corretto con `role="application"`, con i comandi entrati nell'etichetta costruita da un'unica funzione `descrivi`.
- **Perche':** `role="img"` fa si' che lo screen reader trattenga le frecce nella propria navigazione invece di consegnarle alla pagina; `application` passa i tasti.
- **Costo se sbagliato:** `role="application"` sopprime la navigazione per elemento dentro la tela, ma non ha contenuto navigabile essendo un canvas unico.
- **Stato:** in vigore.

### R27 — la prova a video la esegue il coordinatore

- **Deciso:** la prova a video del viewport la esegue il coordinatore, non l'implementatore; rimandata a dopo il Task 6-bis.
- **Perche':** un'affermazione su cio' che appare a schermo, fatta da chi non ha un browser, non e' una misura; a cache fredda ogni caricamento costa 27-34 s, impraticabile prima del 6-bis.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R28 — rilevatore impeccable su copia con href relativi

- **Deciso:** il rilevatore impeccable va eseguito su una copia con gli href relativi, mai sul file sorgente; il Task 16 deve farlo cosi'.
- **Perche':** misurato — su `index.html` sorgente il rilevatore da' `[]` perche' `href="/ui/stile.css"` (assoluto) non esiste dal disco e non legge nessuna regola CSS; su copia con href relativi compare subito `flat-type-hierarchy`.
- **Costo se sbagliato:** nulla, la copia si butta.
- **Stato:** in vigore.

### R29 — `flat-type-hierarchy` e' l'ingresso di `typeset`

- **Deciso:** `flat-type-hierarchy` sulla scala tipografica di `stile.css` e' rilievo gia' misurato, diventa primo compito di `typeset` nel Task 16, non scoperta da rifare.
- **Perche':** cinque corpi fra 12px e 16px con rapporto 1,3:1 fra gli estremi non sono una gerarchia.
- **Costo se sbagliato:** `typeset` lo troverebbe comunque, si perde solo tempo.
- **Stato:** in vigore.

### R30 — tempi del Task 6-bis rimisurati dal coordinatore

- **Deciso:** i tempi del rapporto Task 6-bis rimisurati dal coordinatore invece di riportare quelli dell'implementatore.
- **Perche':** 4,08/0,09 s dichiarati contro 4,47/0,10 s letti (differenza da rumore), ma il numero che finisce nella tesi e' quello verificato di persona — quinto principio del progetto.
- **Costo se sbagliato:** costa due minuti di macchina; senza, sarebbe un numero ricordato e non derivato da una lettura.
- **Stato:** in vigore.

### R31 — la prova browser di R27 non eseguibile, verificato il resto

- **Deciso:** la prova nel browser riservata al coordinatore (R27) non e' eseguibile — estensione Chrome non connessa; verificato invece tutto cio' che sta «sotto il vetro» col server vivo.
- **Perche':** invece di dichiarare la prova fatta o saltarla, si verifica tutto il verificabile senza browser.
- **Costo se sbagliato:** resta non verificato che WebGL disegni, che le frecce ruotino la scena, che l'`aria-label` cambi, che `cattura()` dia un PNG — se il canvas non disegnasse, i task 9-15 si costruirebbero su una vista morta.
- **Stato:** in vigore.

### R32 — file `$F` rimosso dalla radice

- **Deciso:** rimosso dalla radice il file `$F`, zero byte, creato durante il Task 6-bis da un reindirizzamento di shell malriuscito.
- **Perche':** non dichiarato nel registro oltre l'origine.
- **Costo se sbagliato:** nulla — non tracciato, vuoto, nessun contenuto perso.
- **Stato:** in vigore.

### R33 — spaziatura dentro `decimate_file`, chiave a cinque campi

- **Deciso:** I-2, I-4 e la finestra TOCTOU si correggono spostando il calcolo della spaziatura dentro `decimate_file`, chiave `(sorgente, max_points, mtime_ns, spacing_sample, seed)`; il pre-controllo `cache_path(...).exists()` sparisce.
- **Perche':** aggiungere solo `spacing` alla chiave costringerebbe a calcolarlo anche a cache calda (1,78 s), buttando il guadagno; la nuova chiave e' equivalente perche' la spaziatura e' deterministica da sorgente + due interi.
- **Costo se sbagliato:** una firma pubblica cambiata a un giorno dalla nascita, un test in piu' da riscrivere; `decimate_file` conosce due parametri in piu' — accettabile, gia' conosceva `max_points`.
- **Stato:** in vigore.

### R34 — pulizia cache per solo marchio

- **Deciso:** la pulizia della cache passa da `marchio-max_points` a solo `marchio` (una voce per file sorgente).
- **Perche':** una voce pesa 35,9-52,3 MB (non «circa 1,5 MB» come diceva il rapporto, che aveva dimenticato gli indici); con la chiave allargata ogni orfano peserebbe ~40 MB.
- **Costo se sbagliato:** chi chiedesse due budget diversi in alternanza pagherebbe un ricalcolo ogni volta — con utente solo e un budget solo non accade.
- **Stato:** in vigore.

### R35 — I-1 corretto per primo

- **Deciso:** ordinato di correggere per primo il rilievo I-1 (nessun test attraversa il ramo caldo dell'endpoint), benche' Importante e non Bloccante.
- **Perche':** quarto principio del progetto in forma pura — sei test coprono la funzione, zero coprono la tratta; il revisore l'ha contato, non dedotto.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R36 — M-9, M-12, M-13 parcheggiati

- **Deciso:** M-9 (endpoint «nuvola» serve anche lo step 9, `.vtu` di volume), M-12 (`CACHE_DIR` relativa al cwd) e M-13 (test forza `mtime` con `os.utime`) parcheggiati come minori.
- **Perche':** M-9 sara' toccato comunque dal Task 9; M-12 e' convenzione condivisa gia' esistente; M-13 e' modo legittimo di rendere deterministico un test.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R37 — riferimento tipografico misurato per il Task 16

- **Deciso:** il numero `flat-type-hierarchy` (cinque corpi in 4 px, scala larga 1,33 volte) e' l'ingresso del Task 16, non una scoperta da rifare; chi esegue `typeset` rimisura solo alla fine, sulla stessa copia.
- **Perche':** non dichiarato oltre «misurato e non supposto».
- **Costo se sbagliato:** nessuno — la misura si ripete in due secondi.
- **Stato:** in vigore.

### R38 — `renderer.setSize` col terzo argomento sbagliato

- **Deciso:** correzione del bug nel piano — `renderer.setSize(larghezza, altezza, false)` non scrive la misura in CSS; aggiunto anche `display: block` sulla tela, nello stesso commit.
- **Perche':** misurato nel browser — la scena era tagliata su due lati con entrambe le barre di scorrimento visibili; la riga sbagliata era del piano scritto dal coordinatore, non dell'implementatore.
- **Costo se sbagliato:** sei task avevano superato revisione e suite verde con la scena tagliata — nessun test puo' vedere una barra di scorrimento, motivo per cui la prova a video non era rimandabile.
- **Stato:** in vigore.

### R39 — voce di cache in formato vecchio rimossa

- **Deciso:** rimossa dal coordinatore una voce di cache in formato vecchio (tre campi invece di cinque), trovata dal revisore e non dal rapporto dell'implementatore.
- **Perche':** e' la seconda volta nel task che una dichiarazione di pulizia dell'implementatore non regge alla verifica.
- **Costo se sbagliato:** per il resto della notte le affermazioni di pulizia dell'implementatore si controllano, non si riportano.
- **Stato:** in vigore.

### R40 — due residui accettati senza correzione

- **Deciso:** accettati due residui del Task 6-bis: (1) configurazioni alternate sulla stessa nuvola si scaccino a vicenda dalla cache; (2) `_rimuovi_voci_vecchie` gira anche dopo un `OSError` inghiottito, lasciando la cache vuota invece di conservare la voce vecchia.
- **Perche':** (1) e' il prezzo scelto consapevolmente per tenere la cache a otto voci; (2) accade solo su un disco che rifiuta la scrittura.
- **Costo se sbagliato:** (1) con utente solo e una config alla volta non si paga mai; (2) costa un ricalcolo, mai un risultato sbagliato.
- **Stato:** in vigore.

### R41 — `from_step`/`to_step` assegnati insieme

- **Deciso:** corretto assegnando `from_step` e `to_step` insieme, in un `RunConfig` nuovo, dopo che il browser ha mostrato un `ValidationError` vero durante l'uso reale.
- **Perche':** nessun ordine di assegnazione singola e' sicuro — la config su disco puo' rompere in un verso o nell'altro a seconda di quale campo e' piu' vecchio; la correzione precedente (R19) salvava solo un caso.
- **Costo se sbagliato:** nessuno visto dal coordinatore — il nuovo stato e' validato per intero da pydantic come prima.
- **Stato:** in vigore (sostituisce l'approccio di R19).

### R42 — quattro Importanti del Task 8 in un giro solo

- **Deciso:** i quattro rilievi Importanti del Task 8 (server manda la ragione del rifiuto, browser la butta via) trattati in un giro solo.
- **Perche':** separarli darebbe quattro correzioni che si toccano nello stesso gestore; nessuno e' colpa dell'implementatore, sono nel brief incompleto.
- **Costo se sbagliato:** un giro piu' grande da rivedere.
- **Stato:** in vigore.

### R43 — I-2 corretto per primo

- **Deciso:** ordinato I-2 per primo — la PUT rimanda l'intera configurazione, valore rifiutato compreso, quindi dopo un errore ogni campo toccato diventa rosso a torto.
- **Perche':** misurato dal revisore che un campo valido successivo prende comunque `campo-rifiutato`; un indicatore che accusa il campo sbagliato e' peggio di nessun indicatore.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R44 — M-3 trattato come Importante

- **Deciso:** M-3 (cronometro) trattato come se fosse Importante — il revisore ha sostituito `time.monotonic()` con `time.time()` e la suite e' rimasta verde.
- **Perche':** requisito piu' delicato del cronometro (aggiunto dal coordinatore nell'addendum) non aveva un controllo che lo smentisse.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R45 — deselezione: comportamento lasciato com'e'

- **Deciso:** l'unico punto dell'addendum non fatto come chiesto (stato vuoto rimesso quando lo step non ha ne' blocchi ne' metriche, non quando non c'e' nessuno step scelto) resta com'e'.
- **Perche':** la deselezione non esiste in questa interfaccia, l'esito pratico e' quello voluto — non conformita' formale, non difetto.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R46 — M-4 (metriche ferme) va corretto

- **Deciso:** M-4 (pannello mostra metriche vecchie mentre la colonna step gia' dice «valido») va corretto.
- **Perche':** le due meta' della schermata si contraddicono e niente lo dichiara — stessa famiglia della vista che contraddiceva la didascalia, gia' corretta nel Task 7.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R47 — due implementatori insieme, file disgiunti

- **Deciso:** dispacciati due implementatori insieme (Task 12a e Task 9), contro la regola generale di uno alla volta.
- **Perche':** insiemi di file disgiunti verificati tali; ogni dispaccio nomina esplicitamente i file dell'altro come vietati in scrittura.
- **Costo se sbagliato:** un conflitto di merge su un file non previsto, che si vede subito e si risolve rileggendo.
- **Stato:** in vigore.

### R48 — Task 12 spezzato in 12a/12b

- **Deciso:** il Task 12 si spezza in 12a (core: funzione e test) e 12b (endpoint, mappa colore, legenda); 12b torna in coda.
- **Perche':** la meta' core non tocca nulla in mano al Task 8 ed era l'unico lavoro geometrico che potesse partire subito.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R49 — terzo test del Task 12 riscritto (era tautologico)

- **Deciso:** il terzo test del brief del Task 12 (tautologico: `atteso` calcolato da `campo` e confrontato con se stesso) riscritto contro `quality.geometric_error`, con margine dichiarato e giustificato.
- **Perche':** l'unica riga con contenuto era un range arbitrario — «il controllo che smentisce» non smentiva nulla; il brief era del coordinatore stesso.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R50 — compattazione con `np.unique` nel Task 9

- **Deciso:** imposta compattazione con `np.unique(contorno, return_inverse=True)` per il ramo `.vtu`.
- **Perche':** `griglia.points` contiene tutti i nodi della tetraedralizzazione (365.212 su `lab_crop`), mentre le facce di contorno ne toccano una frazione — l'endpoint avrebbe mandato al browser vertici in maggioranza non disegnati.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R51 — `np.sort` sulle facce, solo un commento richiesto

- **Deciso:** `np.sort(facce_tutte, axis=1)` butta via l'orientamento delle facce — non lo fa correggere, chiede solo una riga di commento accanto.
- **Perche':** il materiale usa gia' `DoubleSide` e le normali sono ricalcolate dal browser, la superficie si vede comunque; il commento serve al prossimo che vede una superficie a chiazze.
- **Costo se sbagliato:** una resa peggiore di quella possibile, visibile ma non fuorviante.
- **Stato:** in vigore.

### R52 — guardia sullo step fuori intervallo aggiunta al brief del Task 9

- **Deciso:** aggiunta al brief del Task 9 la guardia sullo step fuori intervallo, gia' imposta su `/api/cloud` nel Task 6-bis.
- **Perche':** il brief mancava questo requisito; stesso difetto, stessa forma di correzione gia' vista.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R53 — numeri di verifica del Task 9 corretti

- **Deciso:** corretti nel brief i numeri di verifica del Task 9 — erano quelli dello step 5 (199.891/398.044), per lo step 6 l'attesa e' 213.154/426.600.
- **Perche':** un numero di verifica sbagliato e' peggio di nessuna verifica — chi lo trova diverso sospetta il codice invece del brief.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R54 — Task 15 spezzato in 15a/15b

- **Deciso:** il Task 15 si spezza come il 12 — 15a (`write_run_report` in `core/report.py` + test) e 15b (cattura viste, endpoint, bottoni, CLI); tre implementatori insieme (12a, 9, 15a).
- **Perche':** la meta' core (15a) e' disgiunta da tutto cio' che gira ed e' la parte sostanziosa.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R55 — Task 13 non si spezza

- **Deciso:** il Task 13 non si spezza, benche' `ui/viewport.js` sia libero; parte intero quando `app.js` si libera.
- **Perche':** i due metodi di taglio senza il loro comando in `app.js` non sarebbero verificabili in alcun modo (nessun motore di test del DOM, permesso negato di aggiungerne uno).
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R56 — docstring di `geometric_error` corretta

- **Deciso:** corretta la docstring che affermava, senza distinguere, che il campionamento delegato a PyMeshLab evita la sovrastima — vero per `cloud_to_mesh`, falso per `mesh_to_cloud`; `vertex_deviation` dichiarata come riproduzione di quel verso.
- **Perche':** trovato leggendo `metrics.json` — `mesh_to_cloud.n_samples` coincide esattamente col numero di vertici.
- **Costo se sbagliato:** senza correzione, chi vede due funzioni dare lo stesso numero a cinque cifre sospetta un errore e perde tempo; il documento di Fase 1 pubblicava gia' `n_samples` per entrambi i versi, quindi la tesi non dice il falso.
- **Stato:** in vigore.

### R57 — il controllo sorveglia l'accordo, non la divergenza

- **Deciso:** accettata la preoccupazione dell'implementatore — il controllo del Task 12a sorveglia l'accordo fra due implementazioni della stessa misura, non la divergenza punto-nuvola/punto-superficie; quella resta non sorvegliata.
- **Perche':** ora che si sa perche' coincidono, il controllo e' onesto per cio' che e'; una soglia sulla divergenza attesa sarebbe il secondo principio del progetto rovesciato.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R58 — revisione del Task 12a saltata, corretta la disciplina

- **Deciso:** il Task 12a era segnato «complete» senza revisore dispacciato — dispacciati subito i revisori mancanti (Task 12a e Task 9).
- **Perche':** dimenticanza mentre si dispacciavano tre implementatori in parallelo, non una decisione.
- **Costo se sbagliato:** non dichiarato nel registro — il rischio del parallelismo non e' il conflitto sui file ma la fase del metodo che salta perche' l'attenzione e' altrove.
- **Stato:** in vigore.

### R59 — mismatch parametri/metriche in `prova-interfaccia` corretto

- **Deciso:** corretta la preoccupazione principale dell'implementatore del Task 15a — `config.yaml` di `prova-interfaccia` dichiara `from_step`/`to_step`=2 mentre `metrics.json` porta undici step fusi; correzione via `steps.run_state(out_dir, cfg)`, senza codice nuovo.
- **Perche':** su uno schermo e' un fastidio, stampato in appendice a una tesi e' una tabella che afferma un legame inesistente senza che il lettore possa accorgersene.
- **Costo se sbagliato:** un report piu' verboso.
- **Stato:** in vigore.

### R60 — `yaml.safe_load` resta al posto di `load_config`

- **Deciso:** la scelta dell'implementatore di `yaml.safe_load` invece di `load_config` resta, combinata col controllo di R59.
- **Perche':** stessa regola gia' applicata alle viste assenti — mai un riquadro muto.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R61 — intervallo del cursore dall'ingombro della geometria

- **Deciso:** aggiunto requisito non nel brief — l'intervallo del cursore del taglio deve venire dall'ingombro della geometria mostrata (`Box3().setFromObject(gruppo)`), non da un valore fisso nel codice.
- **Perche':** su un muro di 2470,99×231,00×1697,00 mm un intervallo fisso renderebbe il cursore inutile per due assi su tre.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R62 — `attivaTaglio` e i materiali nuovi

- **Deciso:** `attivaTaglio` assegna i piani ai materiali che esistono in quel momento; lasciata all'implementatore la scelta fra ricordare lo stato o spegnere il taglio ad ogni cambio di step dichiarandolo — non lasciata aperta.
- **Perche':** cambiando step la geometria nuova nascerebbe senza taglio mentre il comando dice attivo — vista che contraddice il comando.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R63 — il cursore, quando ha il fuoco, riceve le frecce

- **Deciso:** imposto di verificare che il cursore, quando ha il fuoco, riceva lui le frecce e non la tela.
- **Perche':** il Task 7 ha dato alla tela `role="application"` che intercetta le frecce — due controlli che si contendono gli stessi tasti sono un difetto di accessibilita'.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R64 — non si cambia il calcolo di `mesh_to_cloud`

- **Deciso:** non si cambia il calcolo (che sottostima l'errore superficiale); corretta solo la descrizione (commit `3bfd285`), fatto salire il fatto in cima al documento del mattino.
- **Perche':** cambiare il calcolo muoverebbe ogni numero di `07_surface_quality` in tutte le tabelle delle Fasi 1 e 2 — decisione di Mario, non da prendere di notte in un commit di docstring.
- **Costo se sbagliato:** la tesi continua a riportare un RMS che misura meno di quanto il lettore crede; mitigato perche' `n_samples` per entrambi i versi e' gia' pubblico.
- **Stato:** in vigore.

### R65 — rietichettatura del controllo del Task 12a

- **Deciso:** accolto l'Importante 1 del revisore come rietichettatura, non difetto da correggere stanotte; il controllo va rinominato e ridocumentato, il controllo mancante entra nel Task 12b.
- **Perche':** il controllo da' rapporto 1,0000 per qualunque geometria perche' le due misure sono la stessa misura, non perche' sia inutile — la prova per mutazione lo fa diventare rosso.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R66 — Minore 3 fondato, correzione nel 12b

- **Deciso:** il Minore 3 del revisore (`test_quality.py:293-299` passa anche con `return np.zeros(...)`) e' fondato, va corretto nel 12b.
- **Perche':** un test di deviazione nulla su vertici presi dalla nuvola non distingue la funzione giusta da una che restituisce sempre zero.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R67 — giro di correzione del Task 9 limitato a `server.py`

- **Deciso:** il giro di correzione si ferma a `server.py` e `tests/test_server.py`; I-4 e I-5 (in `ui/app.js`/`ui/viewport.js`) vanno in un giro successivo.
- **Perche':** quei file sono in mano al Task 13 in quel momento.
- **Costo se sbagliato:** due difetti restano aperti qualche ora in piu'; il conflitto su due file contesi costerebbe di piu'.
- **Stato:** in vigore.

### R68 — tre rilievi corretti spostando la geometria di prova

- **Deciso:** i tre rilievi del giro Task 9 (stessa forma: codice giusto senza un controllo che lo smentisca) corretti spostando la geometria di prova, non il codice.
- **Perche':** con la geometria di prova originale, sostituire la riga del verso con quella sbagliata del brief lasciava la suite verde.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R69 — cache riusata per `/api/mesh/9`

- **Deciso:** la cura per I-3 (`/api/mesh/9` costa 14,89 s e 1.088 MB di picco ad ogni clic) e' riusare la cache su disco gia' scritta in `core/viewport.py`.
- **Perche':** accolto anche il «cosa non fare» del revisore — i 7,6 MB di corpo non sono il problema, una decimazione qui sarebbe fuori posto.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R70 — M-4 (step 8 «nessun artefatto») non corretto

- **Deciso:** il Minore M-4 (didascalia «nessun artefatto» per lo step 8 con `simplify.enabled=false`) non viene corretto.
- **Perche':** la giustificazione del rapporto era sbagliata, ma la conclusione regge — `apriDettaglio` mostra `enabled=false` nel pannello accanto, nello stesso istante.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R71 — falso allarme del coordinatore sul comando nascosto

- **Deciso:** un controllo del coordinatore era sbagliato, non il codice — il comando di taglio sullo step 2 era gia' nascosto (`querySelector` trova un elemento anche dentro un contenitore con `hidden`).
- **Perche':** stessa forma dell'errore del rilevatore impeccable (R28) — uno strumento che risponde senza guardare cio' che si crede stia guardando.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R72 — tre revisioni mancanti trovate da Mario

- **Deciso:** verificate contro `git log` tre revisioni mancanti (Task 15a, Task 8 giro 1, Task 13), trovate da Mario e non dal coordinatore; dispacciate subito.
- **Perche':** seconda volta stanotte, peggiore della prima — il Task 15a produce il documento che finisce in appendice alla tesi.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R73 — revisione del Task 13 tenuta indietro di proposito

- **Deciso:** la revisione del Task 13 tenuta indietro di proposito, parte solo quando il giro 2 del Task 9 (stessi file) committa.
- **Perche':** un revisore che leggesse ora giudicherebbe codice meta' del quale non e' nel diff dato; il problema di fondo — con cinque agenti in volo il coordinatore teneva il conto degli agenti, non dei task.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R74 — cache del contorno spostata in sottocartella propria

- **Deciso:** le voci di `/api/cloud` e del contorno condividevano il marchio della sorgente (rischio di sfratto reciproco); corretto spostando il contorno in `.cache/viewport/contorno/`, con test che verifica che entrambe le voci sopravvivano.
- **Perche':** verificato eseguendo, non dedotto, che oggi non accade solo perche' l'unico artefatto a rischio risponde 400; l'invariante reggeva per una ragione che sta in un altro modulo.
- **Costo se sbagliato:** non dichiarato nel registro.
- **Stato:** in vigore.

### R75 — riga d'errore, correzione rimandata al giro che tocca `app.js`

- **Deciso:** correggere (ma non subito, non da solo) — la riga d'errore riceve testo mentre e' ancora `hidden`; la forma giusta e' tenere la regione sempre nell'albero e vuota.
- **Perche':** correzione minima ma non verificabile senza un lettore di schermo vero; va nello stesso giro che tocca `app.js` per altro.
- **Costo se sbagliato:** chi usa un lettore di schermo puo' non sentire il motivo di un rifiuto; nessun dato perso, nessun numero della tesi toccato.
- **Stato:** in vigore.

### R76 — `/api/config`/`/api/metrics` senza guardia, gravita' minore

- **Deciso:** rilievo reale ma di gravita' minore di M-1 — `/api/config`/`/api/metrics` letti senza guardare `risposta.ok`; entra nello stesso giro di R75, non prima.
- **Perche':** a differenza di M-1, qui i dati si rileggono ad ogni apertura del pannello, quindi non c'e' nulla da avvelenare.
- **Costo se sbagliato:** in un difetto futuro del server il pannello resta bianco senza dire perche'.
- **Stato:** in vigore.

### R77 — pannello senza copertura automatica, accettato

- **Deciso:** il pannello resta senza copertura automatica — accettato e dichiarato, non coperto.
- **Perche':** coprirlo vuol dire un motore di DOM fra le dipendenze, vietate dalla spec.
- **Costo se sbagliato:** ogni difetto che vive solo nel comportamento del browser lo trova chi apre la pagina — va scritto nel documento della mattina.
- **Stato:** in vigore.

### R78 — commit `f716729` rosso da solo, lasciato com'e'

- **Deciso:** il commit `f716729` e', da solo, rosso — colpa del coordinatore; si lascia il commit dov'e' e si dichiara, non si riscrive.
- **Perche':** riscriverlo vuol dire un rebase (vietato dai vincoli); la storia che nasconde un errore vale meno del record.
- **Costo se sbagliato:** chi fa `git bisect` su questo ramo trova un commit rosso e deve saltarlo.
- **Stato:** in vigore.

### R79 — I4 non e' difetto del Task 15a

- **Deciso:** I4 (report15a: «attese» calcolata dalla lista ricevuta) non e' un difetto del Task 15a — portato nel brief del 15b come requisito suo.
- **Perche':** il chiamante vero (che fara' il `glob`) e' il passo 15b, non ancora scritto.
- **Costo se sbagliato:** se il 15b non lo raccoglie, resta un controllo che non puo' mai fallire — il difetto peggiore perche' ha l'aria di un controllo.
- **Stato:** in vigore.

### R80 — dipendenza dall'ordine dei test non riprodotta

- **Deciso:** nessuna correzione per la dipendenza dall'ordine vista una volta dal revisore; riprovato dal coordinatore con corse ripetute a ordine casuale, nessuna dipendenza visibile.
- **Perche':** corse verdi ripetute non provano l'assenza di una dipendenza dall'ordine, provano solo che non si ripresenta facilmente — si continua a osservarla.
- **Costo se sbagliato:** un test che fallisce a intermittenza; il modo giusto di trovarlo e' il seme che `pytest-randomly` stampa ad ogni corsa.
- **Stato:** in vigore.

### R81 — buco nella guardia sull'ordine: funzioni freccia

- **Deciso:** la guardia sull'ordine ha un buco — le funzioni freccia asincrone inline gli sfuggono; l'estensione entra nel Task 10, non un giro a se'.
- **Perche':** un commit a se' su un file conteso costa piu' del difetto; il Task 10 e' il primo lavoro che il buco lascerebbe passare.
- **Costo se sbagliato:** se il Task 10 non ce la fa e nessuno lo raccoglie, resta una regola sorvegliata a meta'.
- **Stato:** in vigore.

### R82 — brief del Task 10 corretto, non dispacciato com'era

- **Deciso:** brief del Task 10 (vecchio di quattro task) corretto in un addendum che vince sul brief; quattro conflitti veri sanati (`ingombro()` gia' esistente, `this._box`, test che passerebbe per la ragione sbagliata, `points_after` scritto due volte), piu' un punto non nominato (`/api/crop` scrive su disco).
- **Perche':** riscrivere il brief cancellerebbe la traccia di che cosa il piano diceva davvero — quarta volta che il piano si rivela vecchio.
- **Costo se sbagliato:** l'implementatore legge due documenti e puo' seguire quello sbagliato dove si contraddicono; l'aggiunta dice in testa quale vince.
- **Stato:** in vigore.

### R83 — R75/R76 entrano nel Task 10

- **Deciso:** le due correzioni di accessibilita' rimaste dal Task 8 (R75, R76) entrano nel Task 10 invece di aprire un giro proprio.
- **Perche':** stesso ragionamento di R25 — un ciclo dispaccio-revisione per quattro righe costa piu' della correzione.
- **Costo se sbagliato:** due correzioni piccole entrano in un commit che parla d'altro — il messaggio di commit deve nominarle.
- **Stato:** in vigore.

### R84 — di impeccable usato solo `init`, ordine corretto

- **Deciso:** di impeccable e' stato usato solo `init`, non i sette comandi chiesti da Mario; ordine cambiato — passaggio impeccable sul sistema visivo (`typeset`/`colorize`/`layout`/`animate`) PRIMA dei Task 11/12b/14, poi Task 16.
- **Perche':** i Task 11/12b/14 aggiungono pannelli nuovi — farli prima significa scriverli contro un sistema visivo che poi cambia.
- **Costo se sbagliato:** i tre task slittano dietro il passaggio di design e possono finire tagliati — va scritto nel documento della mattina con la ragione.
- **Stato:** in vigore.

### R85 — BL-1 gia' chiuso, verificato per mutazione

- **Deciso:** BL-1 (test dell'ordine cieco alle funzioni freccia) e' gia' chiuso dal Task 10 — verificato per mutazione dal coordinatore stesso, nessun giro aperto.
- **Perche':** il controllo che mancava adesso c'e' e morde sulla riga esatta che il revisore aveva usato per dimostrare che non mordeva.
- **Costo se sbagliato:** nessuno visto; il tetto dichiarato (graffe dentro stringhe/commenti) resta e va nel documento della mattina.
- **Stato:** in vigore.

### R86 — BL-2, entrambe le difese richieste

- **Deciso:** BL-2 (cache del contorno con chiave incompleta come versione) apre un giro; chieste entrambe le difese — costante di versione nel nome della voce E controllo `facce.max() < len(vertici)` in lettura.
- **Perche':** proteggono da guasti diversi — la versione copre il cambio di codice, il controllo in lettura copre il file gia' sul disco; prenderne una sola lascia scoperto l'altro.
- **Costo se sbagliato:** una riga di codice in piu' e un ricalcolo in piu' quando la versione cambia.
- **Stato:** in vigore.

### R87 — IM-2/IM-3/IM-4 in un giro loro

- **Deciso:** IM-2 (`disattivaTaglio` non raggiungibile), IM-3 (piano complanare alla faccia estrema), IM-4 (vista non si aggiorna alla rieseсuzione dello step) vanno in un giro loro, sui file dell'interfaccia.
- **Perche':** stessi file, stesso ragionamento; IM-3 dipende da come si risolve IM-2.
- **Costo se sbagliato:** un giro piu' grande e' piu' difficile da revisionare, ma spezzarlo costringerebbe due implementatori a contendersi `app.js`.
- **Stato:** in vigore.

### R88 — revisione del Task 10 saltata, meccanismo cambiato

- **Deciso:** la revisione del Task 10 era stata saltata (terza volta); dispacciata subito. Da adesso ogni commit del ramo deve comparire nella tabella delle revisioni con il file che la copre, controllo eseguito via `git log` prima di dire che qualcosa e' finito.
- **Perche':** «ricordarmi» ha fallito tre volte su tre — il controllo dev'essere eseguibile, non ricordabile.
- **Costo se sbagliato:** la tabella si aggiorna a mano, quindi puo' mentire se non aggiornata — comunque meglio di prima perche' la discrepanza salta fuori dal confronto.
- **Stato:** in vigore.

### R89 — sette commit del coordinatore senza revisione

- **Deciso:** trovati nove commit senza revisione, sette del coordinatore stesso; dispacciata una revisione dedicata su tutti e sette insieme.
- **Perche':** la regola del metodo tiene il coordinatore fuori dal codice perche' e' la persona meno adatta a giudicare il proprio lavoro — la giustificazione di R25 valeva per una correzione, ripetuta sette volte ha costruito l'insieme di codice che nessuno ha guardato.
- **Costo se sbagliato:** un revisore su sette diff sparsi ha meno contesto di uno dedicato — compensato scrivendo per ogni commit che cosa verificare.
- **Stato:** in vigore.

### R90 — B-1: validazione al confine, non in `core/config.py`

- **Deciso:** B-1 del Task 10 (`POST /api/crop` con liste di un elemento rompe l'interfaccia) si corregge nell'endpoint, non aggiungendo `validate_assignment` a `SegmentConfig`.
- **Perche':** `core/config.py` e' dove vive la verita' dei parametri di tutta la pipeline — cambiarne la validazione sposterebbe il rischio su undici step e due fasi gia' pubblicate.
- **Costo se sbagliato:** un'altra tratta futura dovra' rifare la stessa validazione — il duplicato va scritto nel documento finale.
- **Stato:** in vigore.

### R91 — B-2: l'anteprima deve riprodurre la tratta

- **Deciso:** B-2 (confronto tautologico su `02_segmented.ply`) e' anche difetto del coordinatore — `server.py` legge l'uscita gia' ritagliata dello step 2 invece di riprodurre `remove_outliers`+`crop_box`; entra come secondo bloccante.
- **Perche':** l'anteprima fedele deve riprodurre la tratta e non la funzione — quarto principio del progetto.
- **Costo se sbagliato:** un numero non riproducibile eseguendo lo step e' peggio di un numero assente; se il costo fosse proibitivo, la risposta accettabile e' dichiarare cosa il numero e' e non e', non fingere.
- **Stato:** in vigore.

### R92 — tecnica `git hash-object`/`update-index` adottata

- **Deciso:** adottata come tecnica standard per file di test condivisi la tecnica con cui un implementatore ha messo in indice solo il proprio contenuto senza toccare il file su disco (`git hash-object -w` + `git update-index --cacheinfo`), insieme alla verifica in worktree staccato.
- **Perche':** «guarda `git diff --cached`» dice di accorgersi del problema, questa tecnica lo risolve senza aspettare l'altro implementatore.
- **Costo se sbagliato:** sono due comandi git poco comuni, sbagliarli e' possibile — il controllo che lo smentisce e' la corsa in worktree staccato.
- **Stato:** in vigore.

### R93 — B1 del report tornato su «fallito», test deve coprire i quattro stati

- **Deciso:** B1 del report15a (contraddizione «eseguito»/«ha metriche») e' tornato su «fallito»; terzo giro dispacciato, con requisito che il test nuovo valga per tutti e quattro gli stati.
- **Perche':** e' la seconda volta che il difetto torna cambiando stato — un test che ne guarda uno solo lo lascera' tornare una terza volta.
- **Costo se sbagliato:** un test piu' largo e' piu' difficile da scrivere e puo' diventare generico al punto di non dire niente.
- **Stato:** in vigore.

### R94 — smesso di pre-generare i pacchetti di revisione

- **Deciso:** smesso di pre-generare i pacchetti di revisione (due su tre azzerati a 0 byte fra scrittura e lettura); il revisore genera il proprio diff.
- **Perche':** un file che si azzera fra scrittura e lettura non ha verifica che possa salvarlo — leggere la dimensione dopo la scrittura non protegge da niente perche' il troncamento avviene dopo.
- **Costo se sbagliato:** ogni revisore spende due comandi in piu', ma non esiste piu' un bersaglio da controllare.
- **Stato:** in vigore.

### R95 — direttiva di Mario: ciclo positivo chiude il task

- **Deciso:** una revisione positiva (conformita' e qualita' approvate, nessun bloccante) chiude il task, non se ne apre un altro sullo stesso; unica eccezione il ciclo ralph di impeccable.
- **Perche':** i tre giri del Task 15a hanno prodotto correzioni vere ma il terzo ha dovuto correggere due difetti introdotti dal secondo — oltre un certo punto un giro in piu' sposta i difetti invece di ridurli.
- **Costo se sbagliato:** qualche minore resta nel ramo — tutti vanno nel documento della mattina.
- **Stato:** in vigore.

### R96 — misura sulla calotta non riproducibile, geometria va scritta

- **Deciso:** la misura del coordinatore sulla calotta non era riproducibile dal revisore (struttura confermata, valori diversi); la geometria di prova va scritta esplicitamente in un test, entra nel Task 12b.
- **Perche':** il commit non registrava la geometria — quinto principio applicato al coordinatore stesso: un numero in una docstring del core dev'essere riderivabile.
- **Costo se sbagliato:** resta un numero non riderivabile in una docstring del core.
- **Stato:** in vigore.

### R97 — due Importanti mandati all'agente col file gia' in mano

- **Deciso:** due Importanti della revisione taglio-e-vista non aprono un ciclo nuovo — mandati come aggiunta al mandato dell'implementatore del Task 10 che ha gia' in mano `app.js`/`test_server.py`.
- **Perche':** zero cicli in piu', nessuna contesa di file; il secondo punto e' un test vacuo, categoria di difetto che il progetto esiste per eliminare.
- **Costo se sbagliato:** il giro del Task 10 diventa piu' grande e la sua revisione piu' difficile.
- **Stato:** in vigore.

### R98 — `app.js` entra nel perimetro del ciclo ralph

- **Deciso:** `app.js` entra nel perimetro del ciclo ralph (Task 16) dal giro 2; il criterio di chiusura (punteggio massimo) non si tocca.
- **Perche':** il tetto raggiungibile senza `app.js` e' stimato sotto il massimo — Mario ha dichiarato il punteggio massimo non negoziabile, quindi si allarga il perimetro invece di abbassare il criterio.
- **Costo se sbagliato:** il ciclo tocca il file piu' grande e piu' conteso — contromisura gia' presente (giro che rompe un test si annulla).
- **Stato:** in vigore.

### R99 — divieto sottoagenti tolto per `critique`

- **Deciso:** dal giro 2 il divieto di sottoagenti non si applica ai sottoagenti che `impeccable critique` avvia per conto proprio.
- **Perche':** `critique` girava degradato per colpa di un vincolo del coordinatore pensato per altro scopo, non per mutilare lo strumento di misura.
- **Costo se sbagliato:** un giro costa piu' agenti e piu' tempo; i punteggi del giro 1 non sono confrontabili col giro 2 in poi.
- **Stato:** in vigore.

### R100 — giro 4 del Task 15a: chiudere la serie, non l'istanza

- **Deciso:** il giro 4 parte, ma il mandato principale non e' correggere l'istanza — e' scrivere il test della proprieta' generale (nessuno step riceve due descrizioni incompatibili nello stesso documento).
- **Perche':** la diagnosi di quattro giri e' che ognuno ha corretto l'istanza scrivendo un test che guarda la forma della correzione invece della proprieta'.
- **Costo se sbagliato:** e' piu' lavoro di una sottostringa e puo' allungare il giro; lasciata la facolta' di dire che non si puo', con la ragione.
- **Stato:** in vigore.

### R101 — BL-1 del Task 11: omissione del coordinatore

- **Deciso:** BL-1 del Task 11 (con `method:auto` l'anteprima si ferma prima del vero ramo che lo step 2 percorre) e' un'omissione del coordinatore; giro 2 con obbligo di misurare, vietata la terza strada (ammorbidire le parole).
- **Perche':** il brief nominava solo i primi due passi mentre l'addendum del Task 13, scritto lo stesso giorno, gia' elencava la catena intera.
- **Costo se sbagliato:** se la tratta intera costa troppo, l'anteprima diventa meno utile — comunque meglio di un numero falso.
- **Stato:** in vigore.

### R102 — criterio di chiusura del Task 16 cambiato

- **Deciso:** il criterio di chiusura del Task 16 passa dal punteggio massimo a «ogni rilievo o e' chiuso o porta la ragione con la misura»; il ciclo si sospende finche' i punti 11/14/15b non sono costruiti.
- **Perche':** lo strumento non e' riproducibile (`critique` 25/40 vs 20/40 sulla stessa interfaccia); il punteggio non si muove col lavoro vero (otto difetti chiusi, punteggio invariato); il massimo e' irraggiungibile per costruzione col prodotto incompleto.
- **Costo se sbagliato:** il documento della mattina deve portare la tabella dei rilievi invece di una cifra sola, piu' lungo da leggere.
- **Stato:** annullata da R103, in entrambe le parti (criterio e sospensione).

### R103 — Mario annulla R102

- **Deciso:** R102 annullato in tutte e due le parti su decisione esplicita di Mario; il criterio torna quello della skill (punteggio massimo); il ciclo esce dal perimetro del coordinatore, eseguito da Mario dopo che tutte le altre task sono chiuse.
- **Perche':** «Non e' una mia decisione: e' la sua» — il coordinatore non dispaccia altri giri sul Task 16.
- **Costo se sbagliato:** nessuno per il coordinatore; resta al progetto il costo di inseguire un punteggio massimo su uno strumento che si muove di cinque punti fra due letture.
- **Stato:** in vigore (annulla R102).

### R104 — didascalia del ritaglio entra nel Task 11

- **Deciso:** la didascalia del ritaglio (dopo che il giro 2 del Task 10 ha reso `completo` nell'endpoint) non apre un giro suo per sei righe — entra nel Task 11, testo consegnato da usare verbatim.
- **Perche':** quattro agenti vivi, uno sta mutando gli stessi due file per verificare i controlli del ciclo impeccable — un quinto agente che scrive li' produce il guasto gia' pagato tre volte.
- **Costo se sbagliato:** finche' la riga non entra, l'endpoint dice il vero e la didascalia no — un utente legge un numero che lo step non produrra'.
- **Stato:** in vigore.

### R105 — il regime `mesh_to_cloud`/`cloud_to_mesh` era sbagliato nel brief

- **Deciso:** il regime scritto dal coordinatore nel brief `task-12b-nucleo.md` («vale finche' il lato del triangolo resta sopra la spaziatura») e' falso; sostituito dall'implementatore con l'errore di corda contro la spaziatura.
- **Perche':** misura sulla calotta a 6 mm mostra lato sei volte la spaziatura col verso gia' rovesciato — il lato da solo non determina il regime.
- **Costo se sbagliato:** non dichiarato esplicitamente nel registro.
- **Stato:** in vigore (sostituisce il regime implicito nelle docstring corrette da R56/R64/R96).

### R106 — quattro rilievi informativi del 12b, nessun giro

- **Deciso:** i quattro rilievi informativi del Task 12b (imprecisioni in docstring del core) non aprono un giro — vanno nel documento della mattina, i primi due in evidenza.
- **Perche':** direttiva di Mario esplicita (task con esito positivo non ne apre un'altra), nessuno dei quattro cambia una conclusione.
- **Costo se sbagliato:** la tesi cita una docstring imprecisa su una conclusione vera — si corregge in mezz'ora scrivendo il capitolo, ma solo se qualcuno se la ricorda.
- **Stato:** in vigore.

### R107 — didascalia del ritaglio, testo corretto in due punti

- **Deciso:** la didascalia del ritaglio (R104) entra con due correzioni al testo — «con method: auto» diventa «con questo metodo»; «e ne terra' di meno» diventa «e non ne terra' di piu'».
- **Perche':** entrambe le imprecisioni sono la stessa specie del difetto che la riga esiste per chiudere — un'affermazione piu' forte di quanto il codice garantisca.
- **Costo se sbagliato:** «con questo metodo» e' meno esplicito per chi legge oggi con due soli metodi, ma la prudenza del server esiste per quando saranno tre.
- **Stato:** in vigore (finche' non entra, il Task 10 non e' chiuso).

---

## Numeri mancanti

Nessuno. La numerazione va da R1 a R107 senza buchi.

## Numeri ripetuti

**R15** — compare due volte nel registro (righe 108 e 110 del file sorgente): una voce senza alcun contenuto (`- **R15.**` seguito da riga vuota), immediatamente seguita da una seconda voce numerata R15 con il contenuto reale (la riscrittura del passo 4 del Task 4). Trattata sopra come una sola decisione.
