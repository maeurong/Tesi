# Lo storico annulla anche le esecuzioni, e il modello si legge sotto la pipeline

Data: 2026-09-03

## 1. Il problema, in una riga

Ctrl+Z oggi rimette la configurazione di prima e lascia a video la mesh di dopo:
chi ha sfoltito a voxel 2, poi 5, poi 10 e preme il tasto vede il campo tornare
a 5 e la geometria restare quella di 10, marcata «non valido». L'annullamento è
vero per il file e falso per lo schermo.

Attorno a questo difetto ce ne sono tre più piccoli, tutti nella stessa
interfaccia: la colonna di destra porta due sezioni che non servono più a chi
usa il programma (il registro dello stdout e la galleria degli sweep della
Fase 2), e la colonna di sinistra, sotto la pipeline, è vuota mentre i numeri
del modello — punti, triangoli, chiusa o aperta — stanno tutti in
`metrics.json` senza che nessun pannello li mostri insieme.

### 1.1 Vocabolario

- **Versione**: una voce dello storico. Ogni gesto dell'interfaccia che cambia
  qualcosa ne aggiunge una: un parametro scritto, un ritaglio, un cluster
  scelto, e — da questa spec — un'esecuzione.
- **Esecuzione**: un `POST /api/step/N` o `POST /api/step/N/from`. Produce
  artefatti su disco e riscrive `steps.json` e `metrics.json`.
- **Cartella di scambio**: la cartella `.storico/NNNN/` che accompagna una
  versione di esecuzione. Contiene ciò che l'esecuzione ha sostituito, oppure —
  dopo un annullamento — ciò che l'esecuzione aveva prodotto. Il nome dice il
  meccanismo: si scambia con la cartella della corsa, non si copia.
- **Fronte**: lo step valido di numero più alto. È lo step che il pannello del
  modello descrive.

## 2. Il perimetro

### 2.1 Dentro

1. Lo storico registra le esecuzioni oltre alle modifiche di configurazione, e
   annullarne una rimette gli artefatti, lo stato e le metriche di prima (§3).
2. Un pannello «Modello» sotto la pipeline, che descrive il fronte e si aggiorna
   da solo a ogni esecuzione e a ogni annullamento (§4).
3. Il registro dello stdout resta, chiuso in un `<details>`, e si apre da sé
   quando uno step fallisce (§5).
4. La galleria di curazione esce per intero: markup, script, stile, rotte,
   parametro del server, test (§6).
5. Un lotto di correzioni piccole che i tre audit hanno trovato e che toccano
   gli stessi file (§7). Ognuna sta in un commit suo e si può togliere dal lotto
   senza toccare le altre.

### 2.2 Fuori

Tutto ciò che sta in appendice (§10). Sono proposte misurate dagli audit, con
costo e valore, e restano lì finché una decisione non le porta dentro. Nessuna
di esse è un prerequisito di ciò che sta dentro.

## 3. Lo storico unificato con scambio

### 3.1 La decisione

Una lista sola. `app/storico.py` resta una sequenza di versioni numerate con un
cursore; ogni versione porta il testo della configurazione, come oggi, e le
versioni di esecuzione portano in più una cartella di scambio. Annullare è
sempre «torna alla versione prima», qualunque cosa fosse.

L'alternativa scartata è un secondo deposito per le sole esecuzioni, con Ctrl+Z
che sceglie il più recente fra i due per istante. Due cursori e due troncature
da tenere allineate, e un «configurazione annullata ma esecuzione no» che non è
più una lista ma un albero. Più codice, più modi di sbagliare.

L'altra alternativa scartata è il ricalcolo: annullare rimette il config e
rilancia lo step. Zero disco, ma su una scansione vera un Ctrl+Z costa da
secondi a minuti, e un annullamento che si aspetta non è un annullamento.

### 3.2 Su disco

```
runs/<corsa>/.storico/
  0001.yaml          config della versione 1 («avvio», depositata pigramente)
  0002.yaml          config dopo la modifica 2
  0003.yaml          config della versione 3 (identico a 0002: è un'esecuzione)
  0003/              cartella di scambio della versione 3
    scambio.json     gli step coperti e i nomi dei file che lo scambio governa
    02_segmented.ply
    steps.json
    metrics.json
  cursore.json
  registro.jsonl     una riga per versione; le esecuzioni portano "artefatti"
```

`scambio.json` è la lista chiusa dei nomi che lo scambio muove. Sta nella
cartella e non nel registro perché lo scambio deve funzionare anche se
`registro.jsonl` è stato toccato a mano: il registro è provenienza, l'elenco è
meccanismo.

I nomi in elenco per un'esecuzione da N a M sono: gli artefatti numerati degli
step N..M secondo `pipeline.ARTIFACTS`, i file che gli step senza artefatto
numerato scrivono (il deck e il suo `.vtu` per lo step 11, `12_wall.json` per
il 12; il piano li enumera da `pipeline.py`), più `steps.json`, `metrics.json`
e il parziale delle metriche. Il piano verifica i nomi contro il codice, non
contro questa lista.

### 3.3 Depositare un'esecuzione

`POST /api/step/N` e `POST /api/step/N/from`, sotto `_LUCCHETTO_STORICO` e
prima di `lavoratore.start`:

1. Le guardie di oggi: corsa legata, non in sola lettura, nessun worker in
   corso.
2. `_deposita_le_modifiche_fatte_a_mano`, come fanno già indietro e avanti.
3. `storico.deposita(out_dir, testo, endpoint, [], scambio=elenco)`: tronca il
   futuro, crea `NNNN/`, scrive `scambio.json`, e per ogni nome in elenco che
   esiste nella corsa lo **sposta** dentro la cartella. Spostare e non copiare:
   è un `rename` sullo stesso filesystem, cioè zero byte scritti anche per un
   `02_segmented.ply` da cento megabyte.
4. `steps.json` e `metrics.json` fanno eccezione: si **copiano** nella cartella
   e nella corsa restano, ma senza le voci degli step N..M. Il motivo è la
   ripresa: `write_state` rilegge lo stato esistente e vi aggiunge la voce
   nuova, quindi uno `steps.json` spostato via lascerebbe gli step 1..N-1 «mai
   eseguito» a esecuzione finita. Togliere le voci N..M è invece più vero di
   oggi: uno step che sta per essere rieseguito è davvero «mai eseguito» finché
   il worker non lo riscrive, e un'esecuzione da N a 12 che fallisce al passo k
   non lascia più «riuscito» sugli step k+1..12 con gli artefatti spostati
   altrove.
5. Solo dopo, `lavoratore.start`.

Se il deposito solleva (disco pieno, cartella non scrivibile), il worker non
parte e la rotta risponde con il motivo: un'esecuzione senza deposito sarebbe
un'esecuzione non annullabile, e questa spec esiste per togliere proprio
quel caso.

Un'esecuzione fallita o interrotta resta una versione. Annullarla rimette gli
artefatti di prima, che è ciò che serve: il fallimento ha lasciato «fallito»
nello stato e nessun artefatto, e il gesto che lo toglie è lo stesso di sempre.

### 3.4 Annullare e rifare: lo scambio

Con il cursore su c, «indietro» porta a c-1:

1. Scrive il testo di c-1 su `config.yaml`, come oggi (`_ripristina`, con le
   stesse guardie: testo rileggibile, stesso `out_dir`).
2. Se la versione c ha una cartella di scambio, per ogni nome in `scambio.json`
   scambia il file fra la corsa e la cartella: se esiste da entrambe le parti,
   tre `rename` per la permuta; se esiste da una parte sola, un `rename` verso
   l'altra. Dopo lo scambio la cartella contiene ciò che l'esecuzione aveva
   prodotto, e la corsa ciò che c'era prima.

«Avanti» da c a c+1 fa le stesse due cose con la versione c+1: scrive il suo
testo e, se ha una cartella, scambia. La cartella torna a contenere lo stato di
prima e la corsa quello di dopo. L'operazione è la propria inversa, e per
questo non esistono un «indietro» e un «avanti» diversi nel modulo: esiste
`scambia(out_dir, numero)`.

Il rifiuto arriva prima dello scambio, mai dopo: le guardie di `_ripristina`
girano sul testo, e lo scambio parte solo quando `config.yaml` è già stato
riscritto. Un'eccezione a metà scambio è il caso dichiarato al §3.7.

Un deposito nuovo tronca il futuro come oggi, e con i file `.yaml` cancella le
cartelle oltre il cursore: contengono gli artefatti del futuro scartato, e
cancellarle libera il disco che quegli artefatti occupavano.

### 3.5 Guardie nuove

- Indietro e avanti rispondono **409** mentre un worker gira: «uno step sta
  girando: aspetta la fine, oppure interrompi il calcolo». Scambiare file
  sotto un processo che li sta scrivendo non ha un esito buono.
- Il tetto resta a 200 versioni (`TETTO`), e pota le più vecchie insieme alle
  loro cartelle. Non è un tetto sugli snapshot recenti, che è ciò che è stato
  chiesto di non avere: è l'unica cosa che impedisce a `.storico/` di crescere
  per sempre in una corsa lunga mesi. Se anche questo va tolto, è una riga.
- La risposta di indietro e avanti porta due campi in più: `tipo`
  («configurazione» o «esecuzione») e, per le esecuzioni, `da` e `a` (gli
  step). Il browser li usa per la frase (§3.6).

### 3.6 Nell'interfaccia

- La riga in testata cambia: «Ctrl/Cmd+Z annulla l'ultima modifica o
  esecuzione, con Maiusc la rifà».
- `fraseDelRitorno` resta per il cambio di stato degli step; davanti le si
  antepone, quando `tipo` è esecuzione, «esecuzione dello step N annullata» (o
  «da N a M»). Per le configurazioni la frase è quella di oggi.
- Dopo il ritorno, `caricaStato`, `ricaricaVista` e `apriDettaglio` come oggi;
  il pannello del modello (§4) si aggiorna da `caricaStato` perché legge lo
  stato e non un evento proprio.

### 3.7 Limiti dichiarati

- **Lo scambio non è atomico fra file.** Ogni `rename` lo è, la sequenza no.
  Un processo ucciso a metà lascia una parte dei file scambiata e una no;
  l'impronta di `steps.json` non lo ripara. `_LUCCHETTO_STORICO` esclude il
  caso concorrente; resta la morte del processo, che oggi lascia già
  `config.yaml` e cursore disallineati nello stesso modo. Il piano mette
  `steps.json` **per ultimo** nell'ordine di scambio, così uno stato a metà
  porta ancora le impronte di prima e gli step risultano «non valido» invece
  di «valido» su artefatti misti.
- **Il disco.** Senza tetto sugli snapshot recenti, una sessione da cinquanta
  esecuzioni dello step 2 su `lab_crop` tiene cinquanta `02_segmented.ply`. È
  la scelta fatta e va detta nel `README` della corsa: `.storico/` si cancella
  a mano quando serve spazio, e cancellarla costa solo l'annullamento.
- Lo storico resta nella corsa, quindi non attraversa un cambio di corsa: come
  oggi.

## 4. Il pannello «Modello»

### 4.1 Dove e che cosa

Una sezione nuova nella colonna di sinistra, sotto l'elenco degli step, con
titolo «Modello» e una riga di sottotitolo che nomina il fronte: «dopo lo step
6, Riparazione». Sotto, una lista di definizioni come `.metriche` nella
colonna di destra: etichetta a sinistra, valore con unità a destra, numeri con
`toLocaleString("it")` e cifre tabulari.

Le righe dipendono da che cosa il fronte ha prodotto. Chiavi di `metrics.json`
già scritte oggi, verificate su `runs/lab_telaio_v2`:

| fronte | righe |
|---|---|
| 1 | punti (`points_kept`), spaziatura media (`spacing`, mm), ingombro (`extent`, mm × 3) |
| 2 | punti (`points_after`), rimossi (`outliers_removed` + `cropped_points`) |
| 3 | punti (`points_after`), voxel (`voxel_size`, mm), riduzione (`reduction`) |
| 4 | punti (dal 3), normali degeneri (`degenerate_normals`) |
| 5, 6, 8 | vertici, triangoli, chiusa/aperta, bordi liberi, area (mm²), volume (mm³) |
| 7 | come 6 più errore geometrico (`geometric_error`, la RMS e il massimo) |
| 9 | nodi, tetraedri, punti di Steiner, **saturato** (`steiner_saturated`, come avviso) |
| 10 | nodi, tetraedri, volume totale, diedro minimo, elementi invertiti |
| 11 | tipo di elemento, nodi e tetraedri (dal 10), massa, volume |

### 4.2 Le misure che mancano, e dove si aggiungono

Oggi solo lo step 7 misura chiusura, bordi liberi, area e volume
(`quality.surface_metrics`). Gli step 5, 6 e 8 scrivono vertici e triangoli e
basta, quindi un fronte fermo al 5 non saprebbe dire «aperta». La misura si
aggiunge dove si producono le superfici: in `pipeline.run`, dopo che gli step 5,
6 e 8 hanno la propria coppia `(vertices, faces)`, le loro `step_metrics`
ricevono le chiavi di `surface_metrics` che non hanno già (`watertight`,
`boundary_edges`, `area`, `volume`, `aspect_ratio`). È numpy su un milione di
triangoli, senza albero né campionamento: il costo è nullo rispetto allo step.
Lo step 6 ha già `watertight_after`, che resta: due nomi per la stessa cosa
sono un debito, ma rinominarlo tocca il report e le corse di riferimento, e non
è di questo cantiere.

Le corse eseguite prima di questa modifica non hanno le chiavi nuove: il
pannello scrive «non misurato» al posto del valore, e non lo inventa.

### 4.3 Quando si aggiorna

Il pannello legge `/api/metrics` — non ne calcola — e lo fa quando il fronte
cambia. Il fronte lo calcola `disegnaStep` dallo stato, che arriva dal flusso
SSE ogni mezzo secondo; una lettura a ogni fotogramma sarebbe due richieste al
secondo per niente, quindi il pannello ricorda `(numero, impronta, secondi)`
del fronte e rilegge solo quando la terna cambia. Un'esecuzione finita cambia
`secondi`; un annullamento cambia l'impronta o il numero; una modifica di
parametro cambia l'impronta. Sono i tre casi che contano, e nessun altro.

Stato vuoto, nel markup: «Nessuno step valido: esegui lo step 1». Con il
fronte fermo a uno step senza metriche leggibili (file assente o rotto), la
riga dice «metriche non leggibili» e il resto del pannello resta.

## 5. Il registro, chiuso

La sezione resta nella colonna di destra, dentro un
`<details id="registro-dettagli">` con `<summary>Registro dell'esecuzione</summary>`,
chiuso alla nascita. `tabindex`, `role="log"` e `aria-live="off"` restano sul
`div` interno, per le ragioni scritte accanto nel markup.

Si apre da solo sul fronte di discesa di un'esecuzione fallita, e solo allora:
un registro che si apre a ogni esecuzione riuscita è la sezione di oggi con un
clic in più. La frase in `#esito` cambia in «Il motivo è nel registro, in
fondo alla colonna Dettaglio: …» seguita dall'ultima riga non vuota che il
flusso ha portato. È la riga che chi legge cercherebbe comunque per prima, e
chi non vuole aprire il registro la ha già.

## 6. La galleria, via

Escono: le due intestazioni e i tre elementi in `index.html`; le funzioni della
galleria in `app.js` (dall'elenco alla tabella e al suo ascoltatore, circa 110
righe) e i richiami che le chiamano all'apertura di una corsa; le regole
`.galleria-*` in `stile.css`; `GET /api/experiments` e
`GET /api/experiments/{nome}` in `server.py`; il parametro `radice_esperimenti`
di `create_app` e chi lo passa in `cli.py`; i banchi che li sorvegliano in
`test_server.py`, `test_app_js.py` e `test_stile.py`. Il commento in
`index.html` sullo stato vuoto della vista conta «gli altri tre vuoti di questa
pagina (le corse, il dettaglio, la galleria)»: diventano due.

Il core dello sweep (`core/sweep.py`, `meshrec sweep`, `sweep-report`) non si
tocca: la galleria era una finestra su quei registri, non il loro proprietario.

## 7. Il lotto delle correzioni piccole

Trovate dagli audit del 03/09/2026, tutte a costo S, tutte in file che questo
cantiere apre comunque. Ognuna è un commit e si toglie dal lotto senza toccare
le altre. Da confermare in revisione della spec, una per una.

1. **Il predefinito si vede, e si rimette.** `/api/schema` manda già
   `default` per ogni campo; il pannello lo usa solo per piegare i campi
   fermi. L'aiuto del campo aggiunge «predefinito: X», e un campo spostato dal
   predefinito porta un bottone «Riporta» che chiama `scriviValore` con il
   predefinito. Chi ha girato `min_ratio` tre volte deve sapere da dove è
   partito.
2. **La scheda dice quando ha finito.** `document.title` diventa «✓ MeshRec»
   o «✗ MeshRec» sul fronte di discesa e torna «MeshRec» al fuoco sulla
   pagina; se `Notification.permission` è già concessa, una notifica con lo
   stesso testo di `#esito`. Il permesso non si chiede mai da solo: si chiede
   con un bottone nella testata, una volta, e chi non lo vuole non lo vede più.
   L'attesa da minuti è dichiarata in `PRODUCT.md`, e chi cambia finestra oggi
   non lo sa.
3. **Riporta la vista, e salvala.** `inquadra()` e `cattura()` esistono in
   `viewport.js` e nessun comando le chiama; `preserveDrawingBuffer` è pagato
   per una cattura che non c'è. Due bottoni sopra la tela, accanto al comando
   del taglio: «Inquadra» e «Salva immagine». Il secondo scarica un PNG il cui
   nome porta corsa, step e didascalia (`lab_telaio_v2-06-riparazione.png`).
   Nessuna rotta: il file lo scrive il browser, dove l'utente lo trova.
4. **Invio crea la corsa.** L'ingresso non ha un `<form>`: Tab fino al bottone
   funziona, Invio nel campo no. Si avvolgono i due campi e il bottone in un
   `<form>` con `submit` che chiama ciò che il clic chiama oggi.
5. **«Esegui da qui in giù» si ferma all'11.** `POST /api/step/{n}/from`
   arriva al 12 mentre `PRODUCT.md` dichiara che il prior non gira per difetto
   e la colonna lo nasconde: l'utente paga uno step invisibile. Il tetto del
   server passa a 11; chi vuole il 12 ha `meshrec wall`. La spec del perimetro
   lo ammetteva già. Nello stesso commit, il bottone dice per esteso «Esegui
   da qui fino al deck».
6. **Le metriche degli altri step hanno un nome.** `ETICHETTE_METRICHE` in
   `app.js` copre solo gli step 7 e 10; gli altri dieci passano come chiave
   grezza. Si estende la tabella alle chiavi che il pannello del modello
   nomina (§4.1) più i controlli che contraddicono: `size_check`,
   `watertight_after`, `holes_over_threshold`, `steiner_saturated`,
   `fixed_nset_coverage`. `steiner_saturated` vero è la «mesh troncata in
   silenzio» del primo principio di prodotto, e nel dettaglio si mostra con la
   classe d'avviso, non fra tredici righe uguali.

## 8. Test

Tutto ciò che è nuovo ha un banco prima del codice. I banchi esistenti che la
galleria sorveglia escono con lei.

`tests/test_storico.py`:
- `deposita` con `artefatti` crea la cartella, scrive `scambio.json`, sposta i
  file presenti e non solleva per quelli assenti.
- `scambia` due volte è l'identità, su un elenco con un file presente da
  entrambe le parti, uno solo nella corsa, uno solo nella cartella.
- Il deposito nuovo tronca il futuro **con** le cartelle; il tetto pota le più
  vecchie **con** le cartelle.
- `steps.json` e `metrics.json` si copiano e non si spostano, e nella corsa
  restano senza le voci N..M.
- Una versione di configurazione (senza cartella) annullata non tocca nessun
  file della corsa.

`tests/test_server.py`:
- `POST /api/step/N` deposita prima di avviare il worker; a deposito che
  solleva, il worker non parte e la risposta porta il motivo.
- Indietro e avanti rispondono 409 con il worker in corso.
- Indietro di un'esecuzione rimette l'artefatto di prima, lo `steps.json` di
  prima e risponde `tipo: "esecuzione"` con `da` e `a`; avanti lo rifà.
- Indietro di un'esecuzione fallita rimette lo stato precedente.
- `/from` si ferma all'11.
- `GET /api/experiments` non esiste più.

`tests/test_pipeline.py`:
- Le metriche degli step 5, 6 e 8 portano `watertight`, `boundary_edges`,
  `area`, `volume`; lo step 6 conserva `watertight_after`.

`tests/test_app_js.py` (sorveglianza sul sorgente, come oggi):
- Il fronte è lo step valido di numero più alto (funzione pura, provata sui
  quattro stati).
- Le righe del pannello per un fronte dato (funzione pura su un `metrics`
  finto): le chiavi assenti danno «non misurato».
- Nessun riferimento a `galleria` nel sorgente; il registro sta in un
  `<details>` chiuso alla nascita; la riga della testata nomina le esecuzioni.
- Per il lotto §7: il predefinito compare nell'aiuto; `document.title` cambia
  sul fronte di discesa; l'ingresso è un `<form>`.

`tests/test_stile.py`: nessuna regola `.galleria-*`; il pannello del modello ha
cifre tabulari come `.metriche`.

## 9. Vincoli di lavoro

- Il checkout condiviso `/mnt/c/Users/mario/GitHub/Tesi` è in uso da un'altra
  sessione per la pulizia: il lavoro va in un worktree sotto `/home/mario/
  worktrees/`, da `main`, su un ramo `feat/storico-esecuzioni`. Percorsi
  assoluti, un comando per chiamata, `git -C`.
- La suite gira con `LD_LIBRARY_PATH` sulle librerie estratte e
  `PYTHONPATH` sul `src` del worktree, senza `uv run` finché un altro worktree
  è in volo (memoria `ambiente-tesi-wsl`).
- Ordine dei lotti: §6 (togliere) prima di §3 e §4 (aggiungere), così i banchi
  della galleria non restano rossi a metà. §5 e §7 alla fine, un commit per
  voce.
- Review pre-commit in parallelo: `security-reviewer` (le rotte scrivono e
  spostano file dentro `out_dir`: l'elenco deve restare dentro la corsa, come
  il deck), `code-reviewer`, `test-writer`, `craft-reviewer`.

## 10. Appendice: ciò che gli audit hanno trovato e resta fuori

Tre ricerche del 03/09/2026: l'interfaccia dal punto di vista di chi la usa,
ciò che CLI e core sanno fare senza che l'interfaccia lo esponga, e ciò che
MeshLab, CloudCompare, Open3D, Gmsh e TetGen offrono e MeshRec no. Le voci
già dentro (§7) non si ripetono. Costo S/M/L, valore per il tesista.

**Interfaccia e parametri**
- Legenda dei comandi della vista (frecce, +/-, trascinamento con
  Alt/Ctrl/Maiusc) visibile e non solo nell'`aria-label`. S, alto.
- 33 campi di `PipelineConfig` con `title` e senza `description`: l'aiuto del
  pannello resta vuoto. Solo testo in `config.py`. M, alto per l'utente
  successivo.
- «Prima: X» accanto a una metrica cambiata: `marcaLeMetricheCambiate` accende
  la classe e butta via il numero di prima. S, alto.
- Stima del tempo per «da qui fino al deck»: somma delle ultime durate. S,
  medio.
- Salvataggio di un parametro senza esito visibile: «scritto alle hh:mm». S,
  medio.
- Viste ortogonali (fronte, lato, alto) e proiezione ortografica per le
  figure. S+M, alto.
- Lato del taglio invertibile; wireframe; dimensione dei punti; terna degli
  assi; pan; rotazione del modello da tastiera. S ciascuno, medio.
- Riepilogo in sola lettura di carichi, selettori e regioni nel pannello 11. S,
  medio.
- Difetti di testo: commenti che promettono tasti `f`/maiusc sulla tela che
  non esistono, riferimenti di riga scaduti, `aria-invalid` su un `<button>`,
  un commento che cita ancora lo step 13. S, basso.

**Capacità del core senza interfaccia**
- `report.write_run_report` non ha chiamanti: né CLI né server. Un «Genera il
  resoconto» con rotta e file scaricabile. M, alto.
- Scarica artefatto (`.ply`, `.vtu`, `metrics.json`, `config.yaml`) con la
  stessa allowlist e lo stesso `is_relative_to` del deck. S, medio.
- `sweep-verify` come colonna «coerente/stantia» — decade con la galleria; da
  riconsiderare se il registro degli sweep torna in interfaccia. S, medio.
- `meshrec model` e `compare` hanno il Worker pronto (`start_comando`) e
  nessuna rotta; commenti in `app.js` e `pipeline.py` parlano di
  `/api/compare` che non esiste. M, basso finché il prior non regge sulla
  nuvola vera.
- `seconds` in `09_tetrahedralize` duplica `steps.json.secondi`. S, basso.

**Misure che gli strumenti vicini fanno e MeshRec no**
- Auto-intersezioni e spigoli non-manifold prima di TetGen
  (`is_self_intersecting`, `get_non_manifold_edges` di Open3D), con i
  triangoli colpevoli evidenziati nella vista. S/M, alto: anticipa e localizza
  il guasto che `_diagnosi_del_guasto` oggi legge a posteriori.
- Sezione piana misurata (polilinea e area) ai piani del taglio; profilo di
  sezione a passo fisso lungo un asse. S con pymeshlab, M in numpy. Alto: è il
  confronto diretto con la tavola.
- Diedro massimo e istogramma completo degli angoli: gli sliver hanno diedro
  minimo accettabile e massimo vicino a 180°. S, alto.
- `mindihedral` e `optlevel` di TetGen come parametri di `TetConfig` (da
  verificare i nomi nella versione installata). S, alto.
- Metriche alla Abaqus per tetraedro (shape factor, angoli di faccia, aspect
  ratio degli spigoli) con le soglie di CAE, da verificare sulla
  documentazione. S, alto.
- Colore per elemento nel volume (diedro minimo, aspect ratio) con taglio a
  elementi interi e filtro per intervallo. M, alto.
- Genus e numero di fori (`euler_poincare_characteristic`): un genus maggiore
  di zero su un telaio pieno è un tunnel del Poisson invisibile ai conteggi.
  S, medio.
- Distanza fra nuvola decimata e piena; coerenza delle normali rispetto alla
  superficie ricostruita; densità locale come campo colorato; componenti
  connesse con area. S ciascuno, medio.
- Ball pivoting e alpha shape come `SurfaceConfig.method`; decimazione a
  numero target di triangoli. M e S, medio.
- Bounding box orientato; fit gaussiano dello scarto; statistiche `-V` di
  TetGen nel log. S, basso.
