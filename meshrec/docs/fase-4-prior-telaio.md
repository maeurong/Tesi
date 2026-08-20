# Il prior geometrico del telaio, i modelli parametrici e il confronto

Data: 21/08/2026. Chiude la Fase 4, aperta da [`fase-4-materiale.md`](fase-4-materiale.md)
il 18/08/2026.

## 1. Che cosa gira e che cosa no

Quello che questa sessione ha eseguito e verificato davvero:

- la suite principale, `uv run pytest tests -q --ignore=tests/feasibility`:
  **555 passati**, 2 avvisi (nessun test rosso, nessun test saltato);
- la suite di fattibilita', `uv run pytest tests/feasibility -m feasibility`:
  **8 passati, 1 saltato** — il saltato e' `test_ftetwild_meshes_a_punched_box`
  (`wildmeshing`), non un test di CalculiX;
- i quattro controlli col solutore vero (`ccx`, versione 2.22, installato in
  `/Users/mario/.local/bin/ccx` — Ruling C), compreso quello sul telaio a
  quattro membrature (§ 7);
- `lab_telaio.yaml` e' stato scritto e si carica senza errori con
  `meshrec.core.config.load_config`, col ritaglio misurato al § 8 e i
  riscontri della tavola MURO 1.

Quello che questa sessione **non** ha eseguito: la corsa madre
`uv run meshrec run lab_telaio.yaml` su `lab_frame.pcd` con il ritaglio
corretto, i due modelli parametrici che ne dipendono e il confronto a tre. Il
motivo e il dettaglio sono nella sezione seguente.

## Cosa manca a questo documento

La corsa end-to-end sulla scansione di riferimento, con `lab_telaio.yaml` cosi'
come questo documento lo definisce, **non e' stata completata** in questa
sessione. Due cose distinte sono successe, ed e' importante non confonderle:

**Un tentativo e' stato avviato**, in background, durante la stesura di questo
documento, su `/Users/mario/GitHub/Tesi/Nuvole di punti/lab_frame.pcd`, con la
configurazione materiale dell'utente (C25/30, `young=31500`, `poisson=0.2`,
`density=2.5e-9`), uscita in `runs/lab_telaio/`. Verificato leggendo
`runs/lab_telaio/config.yaml`: il ritaglio usato e' pero' quello di `lab.yaml`
(`crop_min=[1690,-470,-480]`, `crop_max=[4460,-180,1230]`, largo 290 mm in y),
**non** quello misurato al § 8 di questo documento (largo 750 mm, esteso fino
al pavimento). Il tentativo ha completato gli step 1-12 in circa 80 secondi di
calcolo totale (somma dei tempi in `runs/lab_telaio/steps.json`, non ore come
inizialmente previsto) e il suo `12_wall.json` riporta **0 membrature
accettate su 3 regioni trovate** — un esito coerente con un ritaglio che non
comprende le zapatas, non con il prior descritto in questo documento. Un
secondo tentativo, `meshrec model lab_telaio.yaml --tipo estruso`, ha scritto
solo `runs/lab_telaio-estruso/config.yaml` e nient'altro, compatibile con un
arresto immediato per assenza di membrature accettate a monte.

**Questi due tentativi non sono il risultato che questo documento descrive** e
i loro numeri non compaiono da nessun'altra parte in questo testo, per la
stessa regola che vale per il solutore: un controllo saltato non e' un
controllo passato, e una corsa con la configurazione sbagliata non e' la corsa
giusta arrivata tardi. Restano su disco in `runs/lab_telaio/` e
`runs/lab_telaio-estruso/` finche' qualcuno non decide se sovrascriverli.

Il comando esatto per la corsa vera, da eseguire da `meshrec/` con il
collegamento simbolico creato al passo 1 del piano (`ln -s
"/Users/mario/GitHub/Tesi/Nuvole di punti" "../Nuvole di punti"`, dalla radice
del worktree) gia' presente:

```bash
uv run meshrec run lab_telaio.yaml
uv run meshrec model lab_telaio.yaml --tipo estruso
uv run meshrec model lab_telaio.yaml --tipo primitive
uv run meshrec compare runs/lab_telaio runs/lab_telaio-estruso runs/lab_telaio-primitive --out runs/lab_telaio/confronto.html
```

Sono ore di calcolo su 152 MB di nuvola: la spesa la decide l'utente. Prima di
lanciarlo, chi lo fa deve decidere cosa fare di `runs/lab_telaio/` e
`runs/lab_telaio-estruso/`, che oggi contengono l'esito del ritaglio
sbagliato.

Quando la corsa vera esistera', le sezioni 1, 3 e 4 di questo documento vanno
riscritte con i numeri veri al posto di questa nota, e la sezione 9 va
riletta: i limiti li' descritti sono strutturali (dal codice e dai banchi
sintetici), ma la loro entita' su questa geometria specifica resta da
verificare.

## 2. Perche' la fase ha cambiato nome

Il piano di questa fase si apriva assumendo un muro: «due piani paralleli e
uno spessore». La tavola `MURO 1` (obra 0021, novembre 2021, ing. Jose A.
Barros Cabezas), letta all'apertura della Fase 4 e riportata per intero in
[`fase-4-materiale.md`](fase-4-materiale.md), dice il contrario:
`lab_frame.pcd` e' un **telaio in cemento armato** di sei membrature
prismatiche — due zapatas, una viga inferior, due columnas, una viga
superior — non una parete. La premessa vecchia non era un'ipotesi rimasta
inverificata: e' stata **misurata falsa**, dalla tavola stessa, prima che
qualunque riga di codice della fase venisse scritta. Da qui il prior cambia
oggetto: non piu' "muro", ma "insieme di membrature prismatiche", ciascuna
misurata e controllata per conto proprio (Task 2-3), assemblata in un telaio
di blocchi esaedrici legati da `*TIE` alle giunzioni (Task 7-8).

## 3. Le membrature trovate contro la tavola

Questa sezione non puo' essere scritta con numeri misurati: la corsa vera non
e' stata eseguita (§ "Cosa manca a questo documento"). I dati della tavola,
dati del caso e non del programma, sono quelli gia' riportati in
[`fase-4-materiale.md`](fase-4-materiale.md) e ripetuti in `lab_telaio.yaml`
come riscontri dichiarati:

| membratura | sezione nominale [mm] | n. |
|---|---|---|
| Zapata | 700 x 250 | 2 |
| Viga inferior | 250 x 250 | 1 |
| Columna | 172 x 172 | 2 |
| Viga superior | 140 x 175 | 1 |

Volume nominale totale: 0,4777 m³ (477.700.000 mm³).

Quando la corsa vera produce `runs/lab_telaio/12_wall.json`, questa sezione va
riscritta con: `esito['membrature_accettate']` contro le sei attese
(`esito['riscontri']['scarto_membrature']`), le sezioni misurate di ciascuna
contro la tabella sopra, il volume misurato contro 0,4777 m³
(`esito['riscontri']['scarto_volume']`) e — se le membrature accettate non
sono sei — quale controllo ha respinto ciascuna regione scartata, con il
proprio numero (`esito['scartate']`).

## 4. I tre controlli intrinseci e il riempimento di sezione

Ogni regione candidata attraversa tre controlli intrinseci prima di diventare
una membratura accettata (`wall.controlla`, soglie in `lab_telaio.yaml` sotto
`wall:`):

- **parallelismo** (`parallelism_deg: 5.0`): angolo fra le due facce opposte
  della regione. Oltre soglia la regione non ha una sezione definita, e una
  sezione media sarebbe priva di senso.
- **copertura_faccia** (`face_coverage: 0.5`): frazione delle celle della
  faccia viste dallo scanner. Una faccia vista da pochi punti produce un piano
  finto — lo stesso difetto gia' misurato su `FACE_FRONT`/`FACE_BACK` in Fase 1
  (`docs/fase-1-debito.md`).
- **costanza_sezione** (`section_dispersion: 0.10`): dispersione relativa
  della sezione lungo l'asse. Oltre soglia la regione non e' un prisma — e' il
  controllo che, nel banco sintetico, scarta la regione a "Π" quando due
  membrature adiacenti condividono la stessa sezione (Ruling F/G).

Accanto ai tre, dal Task 3 (Ruling J, dopo tre giri di correzione descritti al
§ 5), ogni membratura porta un **quarto stato misurato e non scartante**: il
**riempimento di sezione**, a tre valori — `pieno`, `vuoto`,
`non_verificabile` — con la propria affidabilita' (dispersione delle distanze
al vicino piu' prossimo *fra le fette*, non sull'intera regione — Ruling K
respinto, Ruling L confermato). Una membratura con riempimento basso e misura
affidabile non diventa un modello parametrico (guardia nel Task 8); una con
misura non affidabile puo', ma porta l'avviso fino al report e all'interfaccia.
Non e' un quarto controllo che scarta in `wall.py`: `wall.py` per specifica di
prodotto "misura e non costruisce", e lo scarto — quando avviene — e' deciso da
chi costruisce il modello, non da chi misura.

Infine, **chiusura del volume** (`union_tolerance: 0.02`): somma dei volumi
delle membrature accettate contro il volume della loro unione geometrica. Se
differiscono, alle giunzioni un volume viene contato due volte — un errore che
nessuna metrica di qualita' della mesh vedrebbe da sola.

I quattro esiti concreti su questa geometria (`esito['membrature'][i]`,
`esito['scartate']`, `esito['chiusura_volume']`) non sono disponibili: la
corsa vera non e' stata eseguita (§ "Cosa manca a questo documento").

## 5. I rulings

Trentanove rulings numerati, da A a AM, sono stati presi durante l'esecuzione
di questa fase e registrati per intero in `progress.md` del workspace SDD, che
sparisce alla chiusura della fase. Quelli che seguono sono quelli che cambiano
cosa il programma fa o come va letto il suo risultato; i rulings di processo e
di forma restano fuori. Dove un ruling e' stato poi corretto da uno successivo,
e' riportato l'esito finale con la nota che e' stato corretto.

**Ruling C** — CalculiX 2.22 installato via conda-forge su richiesta esplicita
dell'utente durante il Task 1 (`~/.local/bin/ccx`) — perche' il piano dava
`ccx` per assente e marcava il Task 11 come saltabile, e col solutore presente
quel controllo gira davvero — costo se sbagliato: nessuno sul codice, se
l'ambiente sparisse il Task 11 tornerebbe a saltare com'era gia' previsto.
Commit `7a42c2f`.

**Ruling D** — la completezza di uno sweep non include il prior:
`sweep.REQUIRED_STEPS` e' i soli step fino a `11_export`, non un alias di tutti
gli step — perche' il Task 1 ha esteso `STEP_KEYS` a dodici voci ma `pipeline.run`
scrive fino all'11 fino al Task 9, e ogni candidato sarebbe risultato
incompleto nel mezzo — costo se sbagliato: se uno sweep dovesse un giorno
variare parametri del prior, la sua completezza andrebbe riestesa insieme
all'impronta.

**Ruling J** (sostituisce i Ruling F/G/H/I sullo stesso punto, dopo tre giri
di correzione: la misura del riempimento si spostava dalla lunghezza assiale
alla spaziatura globale alla spaziatura di regione, sempre la stessa forma di
errore un livello piu' in profondita') — il riempimento di sezione smette di
scartare e diventa un esito misurato a tre stati (pieno/vuoto/non
verificabile), con affidabilita' propria; il rifiuto, quando serve, si sposta
da `wall.controlla` (Task 3) a `hexa.costruisci` (Task 8) — perche' `wall.py`
misura e non costruisce, e uno scarto e' una decisione di costruzione — costo
se sbagliato: una regione a "Π" arriva al Task 8 e va rifiutata li'; se quella
guardia mancasse, si costruirebbe un modello su una membratura inventata.

**Ruling K, respinto dal Ruling L** — proponeva un limite sul numero di
campioni per fetta per irrobustire l'affidabilita' del riempimento; il revisore
ha riprodotto i quattro punti della tesi contraria in modo indipendente
(l'asse della regione trasversale al taglio, non assiale; le fette che
leggono 1.0 sono corte non rade; il limite romperebbe il caso obbligatorio
della "Π" uniforme; il caso e' gia' fermato da `costanza_sezione`) — esito
finale: Ruling K respinto con evidenza, Task 3 chiuso con il limite dichiarato
invece che corretto ulteriormente (§ 9).

**Ruling M** — la corrispondenza fra i numeri di faccia del solutore e le
facce fisiche non puo' essere verificata da un controllo interno, perche' un
controllo interno partirebbe dalla stessa trascrizione che vorrebbe
verificare; serve un controllo risolto da `ccx`, marcato `feasibility` —
perche' per mutazione (scambio S2/S4 sull'esaedro, permutazione completa sul
tetraedro) la suite restava verde prima di questo test — costo se sbagliato:
dipende da `ccx` e salta dove manca, ma resta il test per riga (a) che
protegge dalle regressioni. Vale il § 7.

**Ruling N** — `element_surface` filtra alle sole facce di bordo (stesso
criterio di `boundary_faces`, occorrenza singola) — perche' su una mesh a piu'
elementi una faccia interna condivisa entrerebbe due volte in un `*TIE` o in
un carico laterale — costo se sbagliato: nessuno oggi, nessun chiamante
esisteva ancora.

**Ruling O** — lo Jacobiano scalato non misura lo schiacciamento
dell'elemento: e' invariante di scala per direzione, misura distorsione
angolare. Un esaedro sottile quanto si vuole, se resta rettangolo, vale 1 —
dimostrato schiacciando un cubo da altezza 1.0 a 0.1 e misurando 1.0 esatto su
tutti gli otto angoli — correggeva un'affermazione falsa nel test, nel
docstring e nel nome del test stesso.

**Ruling P** (conseguenza del Ruling O) — la difesa contro gli esaedri troppo
sottili non e' lo Jacobiano scalato, e' il vincolo di almeno tre strati nello
spessore (Task 7) piu' la distribuzione di `element_volume` — costo se
sbagliato: nessuno oggi; se un domani servisse distinguere due mesh con lo
stesso Jacobiano ma spessori diversi, si aggiunge una colonna con il caso
concreto in mano.

**Ruling AD** — nella giunzione fra due membrature, cede (viene tagliato) il
prisma che ha l'asse invaso dall'altro, non quello di sezione minore — trovato
misurando sul telaio sintetico a quattro membrature, dove il criterio
precedente sollevava un errore su una geometria non patologica (un portale
normale) — costo se sbagliato: `hexa.costruisci` solleva su geometrie
legittime invece di costruirle.

**Ruling AE** — la tolleranza di contatto alla giunzione non e' piu' una
costante di modulo, e' una grandezza per giunzione calcolata dal cuneo fra la
faccia di taglio e la faccia di contatto — perche' su qualunque geometria
misurata (non il banco squadrato) il fuori-squadra e' il dato, non il rumore —
costo se sbagliato: la tolleranza vale solo per la coppia gia' accertata dal
taglio, mai come raggio globale.

**Ruling AF → AG → decisione dell'utente → AH** (il limite piu' importante
della fase, § 9): su un telaio reale, meta' delle giunzioni non produceva un
`*TIE` per mancanza di nodi sufficienti sulla zona di contatto stretta, non
per il cuneo (gia' risolto dal Ruling AE). Tre vie possibili: (A) accettare il
vincolo parziale e dichiararlo con un numero; (B) `POSITION TOLERANCE` per
giunzione piu' la regola "tocca" sul lato indipendente; (C) mesh conforme
multiblocco, che farebbe sparire i `*TIE` del tutto ma richiede o un
infittimento locale alle giunzioni o la frammentazione dei volumi in gmsh, con
rischio di perdere gli esaedri. L'utente ha scelto **(B)**, perche' (C) fatta
bene contraddice la mesh omogenea gia' scelta (infittire alle giunzioni
introdurrebbe densita' variabile proprio dove le sollecitazioni sono massime),
e la frammentazione in gmsh rischia il tetraedrico come ripiego — perdere gli
esaedri costerebbe piu' dei nodi non legati, perche' l'intera fase esiste per
avere un modello esaedrico da confrontare con l'as-built tetraedrico. La
tolleranza finale (Ruling AH) e' il solo scostamento da squadra sulla zona di
contatto, **non di piu'**: a 30 mm gli avvisi scenderebbero da 24 a 8, ma quel
guadagno non si prende, perche' a quella scala la tolleranza e' dello stesso
ordine del passo di mesh e legherebbe nodi alla faccia piu' vicina che puo' non
essere quella di contatto vera — un vincolo sbagliato e' peggio di un vincolo
mancante, perche' il mancante lo conta il numero e lo stampa il solutore,
mentre lo sbagliato non lo vede nessuno.

**Ruling AK** — lo scostamento dalla nuvola sorgente (`scostamento_nuvola`) si
calcola nel Task 10 (`pipeline.genera_modello`), dove nodi del modello e
nuvola segmentata sono entrambi a portata, e il Task 12 lo rilegge senza
ricalcolarlo — perche' ricalcolarlo nel confronto avrebbe significato riaprire
gli artefatti della madre per ogni modello, e due punti di calcolo della
stessa grandezza sono due cose da tenere allineate — costo se sbagliato:
nessuno; se un `modello.json` vecchio non porta la chiave, la guardia la
tratta come "non impostato" invece di sollevare.

**Ruling AL** — il rapporto di confronto porta `giunzioni` e `ties`, e
`nodi_dipendenti_legati` e `nodi_dipendenti_totali`, come numeri **distinti e
mai sommati o rapportati**; per l'as-built, che e' monolitico, quelle righe
valgono "non applicabile" — perche' senza quei numeri accanto, il confronto fra
i tre modelli attribuirebbe alla geometria una differenza che viene invece dal
vincolo del `*TIE` (§ 9), esattamente l'errore che l'intero task esiste per
evitare.

**Ruling AM** — l'endpoint `/api/rigonfiamento` restituisce l'aggregato (min,
max, p95) e non promette una mappa per cella, perche' quella mappa vive solo in
memoria dentro `Membratura.rigonfiamento` e non arriva su disco — costo se
sbagliato: se servisse una mappa di colore del rigonfiamento nel viewport,
serve un task che la faccia scrivere da `wall.prior`, oggi non c'e'.

## 6. Cosa la fase non fa

- **Nessun solutore strutturale** su un modello completo: i controlli col
  solutore in questa fase verificano che il deck sia leggibile e risolvibile
  (§ 7), non producono un'analisi strutturale del telaio reale. Quello e' la
  Fase 5.
- **Nessuna armatura**: ogni modello, incluso l'as-built, e' calcestruzzo
  omogeneo. E' una scelta dell'autore, non una dimenticanza — il dato delle
  barre resta nella tavola. Un telaio in cemento armato modellato senza
  armatura non e' il telaio vero, ed e' dichiarato in ogni corsa
  (`nota_armatura` in `modello.json`).
- **Nessun tamponamento**: solo la struttura portante in cemento armato.
- **Nessuna riscrittura delle corse di riferimento**: `runs/muro/` e
  `runs/lab_crop/` (dove esistono) e `experiments/muro/` ed
  `experiments/lab_crop/` restano quelli che sono, per cio' che sono — il
  telaio sopra le zapatas, non il telaio intero.
- **Nessuna mesh conforme alle giunzioni**: i due modelli parametrici legano
  le membrature con `*TIE`, non con nodi condivisi (§ 5, Ruling AF/AG/AH). La
  mesh conforme multiblocco resta la via d'aggiornamento dichiarata nel
  codice, non imboccata per la ragione gia' scritta al § 5.

## 7. Lo stato del deck

`ccx` (CalculiX, versione 2.22) e' installato su questa macchina, in
`/Users/mario/.local/bin/ccx` (Ruling C). I quattro controlli di
`tests/feasibility/test_calculix.py` **girano e passano**:

- `test_calculix_solves_a_column_under_self_weight` — una colonna incastrata
  sotto peso proprio, accorciamento confrontato con la forma chiusa;
- `test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra`
  (riga 80) — chiude la meta' "chiusa" del debito di Fase 1 (§ successivo);
- `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero` (riga 139) —
  il telaio sintetico a quattro membrature, unico controllo di questo elenco
  che non dipende dalla stessa geometria che genera cio' che verifica;
- `test_un_prisma_solo_di_mesh_prisma_e_letto_dal_solutore` — l'uscita piu'
  semplice di `hexa.mesh_prisma`, un prisma singolo, risolta da sola.

`8 passati, 1 saltato` in `tests/feasibility` con `-m feasibility`: il saltato
e' `wildmeshing`, non `ccx`. **La formula «il deck esaedrico non e' stato
verificato da alcun solutore su questa macchina» non e' vera su questa
macchina** e non va scritta qui: resta valida solo dove `ccx` non e'
installato, cioe' dove i quattro test sopra vengono saltati invece che
eseguiti. Un controllo saltato non e' un controllo passato, ma un controllo
passato non va raccontato come saltato.

Riproducendo lo scenario del terzo test — quattro membrature, quattro `*TIE`
— in questa sessione (`/tmp/ccx_repro`, stesso banco sintetico di
`tests/test_hexa.py`/`tests/test_wall.py`), `ccx` riporta `tie constraints: 4`
(tutti e quattro registrati), **32.637 equazioni** nel sistema fattorizzato
(riga "number of equations" dello stdout di `ccx`, non 31.674: quel numero,
proposto in una correzione precedente di questo stesso task come "misurato",
non corrisponde a quanto questa riproduzione produce e non viene riportato),
**79 nodi dipendenti totali sulle quattro superfici `*_D`** (contati sommando
i nodi unici per faccia delle quattro superfici, dai `superfici`/`elementi`
di `hexa.costruisci`) di cui **24 non legati** (`model_WarnNodeMissTiedContact.nam`,
24 righe; conteggio delle righe `*WARNING in gentiedmpc: no tied MPC`
nell'output di `ccx`, anch'esso 24), quindi **55 legati davvero** — gli stessi
numeri della storia misurata nel Ruling AH (61 avvisi prima della correzione,
24 dopo). `ccx` termina con `Job finished`, `returncode 0`.

Per **Abaqus**, il progetto non ha licenza sulla macchina di sviluppo:
`PRODUCT.md` e' esplicito — «il controllo dei dati con Abaqus non e' mai stato
eseguito... nulla deve affermare che il deck sia stato validato da Abaqus».
Nessuna riga di questo documento lo afferma.

## 8. Il ritaglio nuovo

Il ritaglio di `lab.yaml` (`crop_min z=-480`, y da -470 a -180, largo 290 mm)
taglia sopra le zapatas: cattura il telaio ma non la base. Le zapatas
misurano 700 mm in `MURO 1`. Per un ritaglio che scenda al pavimento e
comprenda le zapatas per intero, in questa sessione ho misurato, dalla nuvola
grezza `lab_frame.pcd` (152 MB, letta con `io.load_cloud`), ristretta alla
fascia x gia' valida di `lab.yaml` (1690-4460, che non taglia il telaio):

- **il pavimento**, con un piano RANSAC (`o3d.geometry.PointCloud.segment_plane`,
  soglia 3×spaziatura, sugli stessi punti con z < -350): normale quasi
  verticale (0.0046, -0.0063, 1.0000), 543.427 punti interni, z fra -522,5 e
  -498,5. Il bordo alto del pavimento e' quindi z ≈ -498,5;
- **il bordo visibile delle zapatas**: nella fascia z fra il pavimento e -467
  l'ampiezza in y dei punti (percentili 1-99%) vale 679-687 mm, coerente con
  700 mm nominali; da z=-467 a z=-464 crolla a 217 mm, la transizione alla
  sezione della columna (172 mm nominali). Sotto z=-498 domina il pavimento
  (ampiezza fino a 764 mm, la stessa larghezza vista alla quota del
  pavimento), quindi il pavimento e la base delle zapatas non sono
  distinguibili in quota in questa scansione: la zapata e' visibile solo per
  il tratto sopra il pavimento, non per l'intera altezza nominale di 250 mm,
  presumibilmente perche' il resto e' interrato o coperto dalla soletta di
  laboratorio;
- **estensione y** nella fascia zapata (z fra -498 e -467): da -675,5 a 63,5
  mm (min/max, non percentili). `crop_min[1]`/`crop_max[1]` allargano
  quell'intervallo di 5-7 mm di margine.

Valori scelti per `lab_telaio.yaml`:

```
crop_min: [1690.0, -680.0, -498.0]
crop_max: [4460.0,   70.0, 1230.0]
```

x e `crop_max[2]` restano quelli di `lab.yaml`: la fascia x non taglia il
telaio (verificato: x delle zapatas nella fascia individuata resta fra 1700,5
e 4391,5, dentro i limiti) e z=1230 comprende gia' la sommita'.

Va detto a lettere chiare, come chiede la specifica: **la base del modello non
esiste nel pezzo vero, e' dove abbiamo tagliato.** Lo stesso principio che
`report.py` applica al set `BASE` dell'as-built — «Il set BASE non e' una
faccia del pezzo: e' la quota di taglio scelta dall'operatore. Quella
superficie non esiste nel pezzo vero, e' dove abbiamo tagliato»
(`report.py`, costante `NOTE_NON_GEOMETRICHE`) — vale allo stesso modo per
`crop_min[2]` di questo ritaglio: e' una quota scelta sopra il pavimento
misurato, non una faccia fisica delle zapatas.

## 9. I limiti misurati

**Il soffitto del taglio alle giunzioni.** L'assemblaggio del telaio taglia
(accorcia lungo l'asse) il prisma il cui asse e' invaso dall'altro alla
giunzione (Ruling AD); non e' un'operazione booleana sui solidi. Le mesh delle
due membrature ai lati di una giunzione hanno passo diverso (quello della
propria sezione) e non condividono nodi sull'interfaccia: il `*TIE` lega
quello che riesce, e sul telaio sintetico a quattro membrature 24 nodi
dipendenti su 79 restano non legati anche dopo la correzione geometrica della
tolleranza di contatto (Ruling AE) e la regola "tocca" (Ruling AH — § 5, § 7).
**Conseguenza da leggere insieme al confronto fra i tre modelli**: un modello
parametrico con giunti parzialmente liberi e' piu' cedevole del vero, e quella
differenza non viene dalla geometria — viene dal vincolo. Per questo il
rapporto di confronto porta `giunzioni`/`ties` e
`nodi_dipendenti_legati`/`nodi_dipendenti_totali` come numeri separati, mai
sommati (Ruling AL), e per questo la mesh conforme multiblocco, valutata e
scartata (§ 5, decisione dell'utente sul Ruling AG), resta la via
d'aggiornamento dichiarata: farla richiederebbe o un infittimento locale alle
giunzioni, che contraddice la mesh omogenea scelta dall'utente, o la
frammentazione dei volumi in gmsh, che rischia di perdere gli esaedri — e
senza esaedri la fase non ha piu' oggetto.

Si e' anche verificato, e scartato, di allargare la `POSITION TOLERANCE` del
`*TIE` a 30 mm: sul telaio sintetico gli avvisi scenderebbero da 24 a 8, ma a
quella scala la tolleranza e' dello stesso ordine del passo di mesh (46-113 mm
sul banco) e della sezione, e il solutore legherebbe un nodo alla faccia
indipendente piu' vicina, che puo' non essere quella di contatto vera. Un
vincolo sbagliato e' peggio di un vincolo mancante: quello mancante lo conta un
numero e lo stampa il solutore, quello sbagliato non lo vede nessuno.

**Il soffitto della ricombinazione di gmsh.** L'ordine canonico dei nodi e
degli elementi prodotti da `hexa.mesh_prisma` e' garantito e verificato per
mutazione (Ruling S: permutando le chiavi del criterio d'ordinamento, il test
cade). Non e' garantito che qualunque combinatoria di contorno sia
ricombinabile in esaedri puri: `Mesh.RecombineAll=1` (non `setRecombine` sulla
sola superficie sorgente, Ruling T) produce esaedri per le sezioni
rettangolari di questo progetto, ma se gmsh non produce elementi di tipo 5
`mesh_prisma` solleva un `RuntimeError` esplicito (`hexa.py:180-184`, testo a
`hexa.py:182`) invece di restituire un prisma a base triangolare in silenzio. Il limite e' dichiarato
dalla guardia, non eliminato da essa.

**La sottostima del rigonfiamento dove le celle sono grandi.** La griglia con
cui `wall.misura` calcola sia la dispersione di sezione sia il rigonfiamento
usa lo stesso `lato_fetta = ptp(asse) / 20` (venti fette lungo l'asse,
`wall.py:441-449`): su una membratura lunga, ogni cella e' ampia, e il
rigonfiamento — il massimo scostamento dalla faccia ideale dentro ciascuna
cella — puo' nascondere un rigonfiamento locale piu' piccolo della cella
stessa. E' un limite strutturale della griglia scelta, dichiarato nel codice
che la calcola; la sua entita' su `lab_frame.pcd` non e' stata misurata in
questa sessione (§ "Cosa manca a questo documento").
