# Onda di correzione della revisione finale — Fase 4

Ventuno rilievi, **nessun bloccante**. Il ramo è approvato nella sostanza: il
confine `wall.py` misura / `hexa.py` costruisce regge, i controlli intrinseci
dichiarano invece di scartare, i `ponytail:` nominano soffitto e via
d'aggiornamento. Quello che segue è rifinitura.

**Ordine di lavoro: dall'alto.** Se resti senza tempo, i primi tre valgono più
di tutto il resto messo insieme.

---

## I tre che contano

### F1 — Una corsa figlia fallita rompe il confronto, e l'interfaccia la maschera come stato normale

`pipeline.py:171-172` · `report.py:661-667` · `ui/app.js:503-512`

`genera_modello` scrive `out/config.yaml` **prima** di `hexa.costruisci`. Se
`costruisci` solleva — e sulla nuvola vera solleva, perché il prior non accetta
membrature — resta una cartella con dentro **solo** `config.yaml`. Ne esiste una
adesso, verificata: `runs/lab_telaio-estruso/`.

Poi `confronta()` la include (è una directory) e la rifiuta con `ValueError`,
l'`exception_handler` rende 400, e `caricaConfronto` sul ramo `!risposta.ok`
mostra `confronto-vuoto`, cioè **«Nessun modello parametrico generato»** — il
messaggio dello stato normale alla prima apertura.

Esito: chi ha appena visto fallire una generazione legge che non ha ancora
generato nulla. Per sempre.

**Correzione:** sposta `save_config` **dopo** `hexa.costruisci`, così la cartella
nasce solo quando c'è un modello. È il diff più corto e chiude anche la cartella
orfana. In più `caricaConfronto` legga `corpo.messaggio` invece di ricadere sullo
stato vuoto: il gestore globale lo mette lì apposta.

**Poi togli `runs/lab_telaio-estruso/`**, che è il residuo di quel difetto.

### F2 — Il limite dichiarato della fase non arriva al browser

`ui/app.js:521`

`/api/compare` restituisce `note_non_geometriche` (dentro c'è `nota_giunzioni`,
la frase sulla mesh non conforme), `vincoli_giunzioni` (con
`nodi_dipendenti_legati` e `nodi_dipendenti_totali`) e `qualita`. Il pannello ne
rende **tre**: volume, massa, scostamento. Il rapporto HTML ha la sezione
«Vincoli alle giunzioni»; il browser no.

Chi apre i due modelli nel pannello legge che il primitive ha volume e
scostamento diversi, e **nulla gli dice che parte dei nodi dipendenti non è
vincolata** — cioè che una differenza di cedevolezza verrebbe dal `*TIE` e non
dalla forma. È esattamente l'errore che `nota_giunzioni` esiste per evitare, ed
è il quinto vincolo di prodotto della fase.

**Correzione:** due `<p>` in `caricaConfronto`, uno per `note_non_geometriche` e
uno per `vincoli_giunzioni`. Il dato è già nel payload. Aggiungi anche
`chiusura_volume`, che porta un `passato` booleano su «un errore che nessuna
metrica di qualità della mesh vedrebbe» e oggi non compare fuori dal JSON.

### F3 — La tabella che il sorgente chiama «la fonte d'errore silenzioso» non ha un test sull'ordine

`abaqus.py:225-232` · test a `tests/test_abaqus.py:672-692, 900-960`

Il sorgente dichiara: «Non è `FACCE_TOPOLOGICHE` con un altro nome: quella può
elencare le facce in qualunque ordine. **Questa non può: l'ordine È
l'informazione.**»

I due test che la coprono usano `sorted()` e il baricentro: **entrambi buttano
via l'ordine**. Verificato da me: mutando S2 dell'esaedro da `(4, 7, 6, 5)` a
`(4, 7, 5, 6)` — non più un perimetro, ma una farfalla — la suite resta
**555 passati**.

Su faccia piana non si vede. Su faccia svergolata, che è ciò che una mesh vera
ha, il revisore ha misurato: area di S2 4,8284 contro 4,8900, e
`hexa._distanza_punto_faccia` per un punto **sulla** faccia 0,3638 invece di 0.
Il secondo è quello che pesa: `costruisci` confronta quella distanza con
`soglia_legame`, quindi un nodo appoggiato sulla faccia risulterebbe non legato
e **`nodi_dipendenti_legati` scenderebbe** — cioè il numero che il confronto
pubblica come misura del limite dichiarato.

**Correzione:** un test che chieda a `FACCE_DEL_SOLUTORE[8]` di essere un ciclo
di perimetro — per ogni faccia, i quattro lati consecutivi devono essere spigoli
dell'esaedro, mai diagonali. Sette righe, e non richiede di conoscere il manuale
del solutore. **Applica la mutazione della farfalla e verifica che il test nuovo
la uccida.**

---

## Correttezza

### F4 — `_legge_json` non regge un file mal codificato
`report.py:608-614`. `except (OSError, json.JSONDecodeError)` non copre
`UnicodeDecodeError`, che è sottoclasse di `ValueError`. Su un `modello.json` con
un byte `0xff` l'eccezione esce non gestita e porta giù `/api/compare` e
`write_comparison_report` insieme. **Correzione:** `except (OSError, ValueError)`
— più corto e più corretto, perché `json.JSONDecodeError` è già un `ValueError`.

### F5 — `/api/membrature` unisce due artefatti senza verificare che vengano dalla stessa corsa
`server.py:700-720`. Gli indici vengono da `12_wall.json`, la nuvola da
`02_segmented.ply`, e nessuna delle due letture guarda `steps.json`. Rifatto lo
step 2 con un ritaglio diverso senza rifare il 12, gli indici o escono
dall'array (400 opaco) o — se la nuvola nuova è più grande — **restano dentro e
dipingono le etichette sui punti sbagliati in silenzio**.
`steps.step_fingerprints` esiste esattamente per questo. **Correzione:**
confronta l'impronta dello step 12 con quella della configurazione corrente e
di' «il prior è più vecchio dello step 2» invece di disegnare.

### F6 — `facce_i` sopravvive fra due giunzioni
`hexa.py:881-886`, letta a `:903`. È assegnata dentro il ramo `else` del ciclo
sui ruoli e letta dopo il ciclo, e il ciclo esterno sulle giunzioni non la
azzera. Oggi irraggiungibile, ma se un giorno il ruolo `"I"` saltasse,
`_distanza_punto_faccia` misurerebbe contro le facce **della giunzione
precedente** e `nodi_dipendenti_legati` uscirebbe plausibile e falso. **In un
conteggio che il confronto pubblica.** Dichiarala dentro il ciclo, accanto a
`nomi = []`. Togli anche `baricentri_faccia_i` (`hexa.py:839`), dichiarata,
annotata e mai usata.

---

## Affermazioni diventate false

### F7 — «nessuna libreria del progetto» fa operazioni booleane: falso da questo ramo
`hexa.py:538-539` dice che una vera operazione booleana fra solidi «oggi non ha
in casa nessuna libreria del progetto». Ma questo ramo ha promosso **gmsh** a
dipendenza vera (`pyproject.toml:22`), e sull'installato `occ.cut`, `occ.fuse` e
`occ.intersect` esistono tutti. Il documento della fase lo sa già e valuta e
scarta la frammentazione dei volumi; il sorgente no, e manda chi raccoglie la
via d'aggiornamento a cercare una dipendenza **già installata**. Stessa frase da
rivedere a `hexa.py:722-727` e `:825-827`.

### F8 — Citazioni con numero di riga, scadute
Il ramo ha spostato codice sotto a citazioni che non sono state aggiornate:

| Dove | Cita | È a |
|---|---|---|
| `server.py:137-138` | «il verso uscente delle facce (`core/quality.py:51`)» | `_TET_FACES` è a `quality.py:169`; la riga 51 ora parla della decomposizione **dell'esaedro** |
| `pipeline.py:110` | «verificato contro `wall.py:735-758`» | il dizionario è a `wall.py:747-774` |
| `hexa.py:744` | «`wall.py:501-506`» | l'assegnazione di `riempimento_stato` è a `wall.py:507-512` |
| `server.py:612-616` | «l'ingresso grezzo dello step 2 (vedi `pipeline.py:132-148`)» | lo step 2 è a `pipeline.py:306-310`. **Preesistente**: era falsa anche su `main` |

**Correzione, e vale per tutte:** cita il **nome** (`quality._TET_FACES`), non il
numero di riga. Un nome non scade quando qualcuno inserisce una funzione sopra.
Cerca le altre con `rg` — il revisore ne ha contate dieci in `src/`.

### F9 — `quality.py:136-141` parla al futuro di un lavoro chiuso
«Chi **metterà** queste metriche accanto a quelle tetraedriche — il confronto,
**al Task 12** — deve tenerle in due colonne separate». Il Task 12 è fatto, e
`report.py:706,711` lo fa. Chi legge non sa se la regola è stata rispettata o è
ancora da rispettare. Riscrivi al presente, nominando il chiamante.

### F10 — Una quota del provino in `src/` (vincolo 1)
`config.py:653`: «È il controllo che smentisce l'asse di fedeltà: **176 su
lab_frame**, 1245,7 su muro_generato». 176 mm è lo spessore misurato del
provino. **Preesistente** (Fase 2, commit `25b96a3`), ma è il solo esito del
vincolo 1 su tutto il sorgente, e il vincolo dice `src/` senza eccezioni per
anzianità. La descrizione dice già tutto senza i due numeri.

---

## Duplicazione

### F11 — `wall.prior` toglie il pavimento due volte
`wall.py:702` chiama `scarta_pavimento`, poi `:262` (dentro `scomponi`) lo
richiama con gli stessi argomenti. Misurato dal revisore con una spia:
`extract_planes` chiamate **2**. E `server.py:497` misura `extract_planes` a
**57,76 s** su `lab_crop`: lo step 12 lo paga due volte. Stessa storia per
`terna(puliti)`, calcolata da `scomponi`, scartata da `prior` e rifatta —
**due SVD sull'intera nuvola ripulita**.

**Correzione, ed è più corta di adesso:** `scomponi` restituisce anche `puliti`,
`tenuti` e `direzioni`, che ha già in mano; `prior` smette di ricalcolarli.
Sparisce anche il commento che oggi deve giustificare la doppia chiamata.

### F12 — La chiave di cella è scritta tre volte
`wall.py:108`, `:210`, `:535` identiche o quasi; e `_volume_unione` a `:684`
riscrive a mano ciò che `chiavi_di_cella` fa già — quella funzione è indipendente
dal numero di colonne e regge il 3-D così com'è. Una `_chiave_di_cella()` di due
righe, e `_volume_unione` che chiama `chiavi_di_cella`.

### F13 — Le facce di bordo trovate con due algoritmi diversi
`abaqus.py:264-266` (`element_surface`, vettorizzato) contro `:326-330`
(`tie_surface`, `set` di tuple e comprehension). Stessa definizione, due
implementazioni; misurato ~1,9× più lento su 27.000 esaedri. Estrai
`_facce_di_bordo(elementi, combinazioni)` e chiamala da entrambe.
**`boundary_faces` resta intatta**, la sua ragione è scritta e vale.

### F14 — `angoli = 8 if ... else 4`, tre volte
`abaqus.py:259`, `:322`, `:363` — mentre `_ANGOLI_PER_COLONNE` a `:379` esiste
per lo stesso scopo, col commento «mappa esplicita e non un ternario: un
conteggio non previsto deve fermarsi con un errore». Le tre righe sopra **sono**
il ternario che quel commento condanna.

---

## Rifinitura

### F15 — La cella «qualità» del rapporto stampa il `repr` Python
`report.py:756-759`. `_testo` non ha un ramo per un dizionario **non** vuoto e
cade su `str(valore)`. Coi dati veri esce
`{'radius_edge_ratio': {'min': 0.6243550092909288, ...}}` — apici singoli e
diciassette cifre, in una pagina dove ogni altra riga passa da `_numero()`. Ed è
la sezione che il vincolo 3 mette in evidenza. Due righe in `_testo`:
`", ".join(f"{k} {_testo(v)}" for k, v in valore.items())`.

### F16 — `.gitignore` non copre il collegamento alla cartella delle nuvole
Nel worktree c'è `Nuvole di punti` → `/Users/mario/GitHub/Tesi/Nuvole di punti`,
un **symlink** (40 byte, nessun dato copiato). `.gitignore:13` ha
`Nuvole di punti/` **con lo slash finale**, che per git combacia con una
directory e non con un link: risulta non tracciato. Aggiungi la riga senza
slash. Non togliere il link: fa funzionare `lab.yaml` dal worktree e non costa
disco.

---

## Parcheggiati con motivazione — non toccare

- **`sezioni_nominali` senza consumatori** (`config.py:470`, `wall.py:795-799`):
  è letta, ricopiata nel JSON e mai confrontata con le sezioni misurate. Il
  revisore propone di confrontarle o di togliere il campo. **Resta com'è**: è
  superficie di configurazione dell'utente, e toglierla o darle un significato
  nuovo è una decisione sua, non una correzione.
- **POST di azione senza controllo d'origine** (`server.py:338-361`): il server
  è dichiarato «utente singolo, nessuna autenticazione» su `127.0.0.1`, ed è lo
  schema già in uso da `POST /api/run`. Nessuna esfiltrazione, nessuna
  iniezione. **Resta com'è**, ed è annotato: il giorno che il server uscisse da
  localhost, il controllo di `Origin` è la prima riga da aggiungere.
- **Ciclo Python di `/api/membrature`** mai misurato sulla nuvola vera: già
  marcato `ponytail:` con la via d'aggiornamento. Se lo si riapre, va fatto
  insieme a **F5**, che tocca le stesse dieci righe.

---

## Regole del giro

- Ogni numero che scrivi in un docstring o in un commento: **o l'hai misurato tu,
  adesso, sulla cosa di cui stai parlando, o non lo scrivi.** Questa fase ha
  pagato **dieci volte** la violazione di quella frase, in tre varianti diverse:
  affermazione mai eseguita, misura scaduta dopo un cambio di codice, misura
  letta dalla cartella sbagliata.
- Ogni test nuovo dichiara quale mutazione lo uccide, e tu quella mutazione
  **l'applichi davvero** e verifichi che uccida. Se sopravvive, dillo.
- Percorsi espliciti nel `git add`, mai `-A`. Niente push, niente merge, niente
  `git stash`.
- Le suite partono da **555 passati** e **8 passati / 1 saltato** in
  `tests/feasibility`. Riporta i numeri che leggi tu.
