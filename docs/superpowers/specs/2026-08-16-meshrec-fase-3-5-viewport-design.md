# MeshRec Fase 3.5 — Continuità del viewport e ritorno indietro

**Data:** 16/08/2026
**Stato:** design approvato in brainstorming, piano da scrivere
**Colloca:** dopo la chiusura della Fase 3 (critica del giro 3 inclusa), prima
della Fase 4.
**Dipende da:** Fase 3 completa. In particolare dal motore per step con catena
di impronte (`2026-08-13-meshrec-fase-3-interfaccia-design.md` § 6), su cui
poggia il § 6 di questo documento.

---

## 1. Perché questa fase esiste

Tre osservazioni d'uso, riportate dall'autore dopo aver usato l'interfaccia
sulla propria scansione. Nessuna delle tre è coperta dalle fasi successive: la
Fase 4 è il prior geometrico «muro» e la mesh esaedrica, la Fase 5 è il banco
sintetico e CalculiX in batch
(`2026-08-12-meshreconstructor-architettura-design.md` § 6). Nessuna delle due
tocca il viewport.

> **Un falso amico da disinnescare subito.** In tutti i documenti della Fase 3
> «annullamento» significa la terminazione del processo che sta eseguendo uno
> step lungo (§ 7 della spec di Fase 3, bottone `#annulla` in
> `ui/index.html:19`). Non ha mai significato «ritorno indietro» su una
> modifica. L'undo non compare in nessun piano precedente, e questa è la prima
> volta che entra in un documento.

### 1.1 Le tre osservazioni, e cosa si è misurato sotto

**«Dal secondo passaggio in poi mancano dei pezzi.»** La scansione
`lab_frame.pcd` è un telaio con due piedistalli in calcestruzzo, due pilastri
sopra di essi e una trave che li collega alla sommità. Dallo step 2 in poi si
vedono soltanto i pilastri e la trave.

Non è un difetto di disegno: è il ritaglio adottato che fa il proprio lavoro.
Il config di lavoro ha `segment.method: crop` con `crop_min[2] = -480`, mentre
la nuvola piena parte da `bbox_min[2] = -781,5`
(`runs/lab_crop/metrics.json`, `01_load`). Il box toglie **301,5 mm alla base**,
cioè i piedistalli, ed è corretto che lo faccia: i piedistalli sono in
calcestruzzo e la tesi modella il telaio in muratura. Lo stesso box restringe la
profondità da 785 mm (`bbox` da −703,5 a 81,5) ai 290 mm fra −470 e −180,
togliendo lo sfondo del laboratorio.

In numeri: 6.329.096 punti letti, 244.304 tolti come outlier, poi 1.855.254
tolti dal box, per i 4.229.538 che lo step 2 dichiara
(`core/segment.py:142-143` fissa l'ordine: prima gli outlier, poi il ritaglio).

**Il difetto quindi non è dove sembra.** È che l'interfaccia non dice mai di
aver tolto qualcosa. Mostra il conteggio dell'artefatto corrente e nulla che lo
metta accanto a quello di prima. Chi guarda vede sparire un terzo della
scansione senza un numero che glielo spieghi, ed è il principio 1 di
`PRODUCT.md` letto al contrario: qui non c'è un numero da smentire, c'è un
numero che manca del tutto.

**«Di passaggio in passaggio si riparte da zero.»** Il dato non riparte: la
catena degli artefatti è già cumulativa e ogni step riceve il precedente
lavorato (`core/pipeline.py:31-40`). Chiedere lo step 4 serve
`04_normals.ply`, che è la nuvola sfoltita dallo step 3 con le normali sopra, e
`POST /api/step/{n}` esegue soltanto n riusando ciò che sta a monte
(`app/server.py:402`).

A ripartire da zero è la vista. Tre fatti dell'interfaccia, tutti verificati nel
codice:

1. **La camera si azzera a ogni step.** `mostraNuvola` e `mostraMesh` chiamano
   `inquadra()` senza condizione (`ui/viewport.js:187` e `:199`), che riscrive
   centro e raggio dell'orbita. La stessa nuvola inquadrata da un altro punto
   sembra un'altra nuvola.
2. **Gli step 7, 10 e 11 svuotano la scena.** Non hanno un artefatto proprio —
   `ARTIFACTS` (`core/pipeline.py:31`) salta il 7 e si ferma al 9 — quindi il
   server risponde con un errore e il browser esegue `vista.svuota()`
   (`ui/app.js:222` e `:260`), lasciando «nessun artefatto per questo step».
   Avanzando lungo la pipeline la geometria sparisce del tutto: è il «riparte da
   zero» nella sua forma più letterale.
3. **La densità disegnata salta.** Il budget di disegno è di 400.000 punti
   (§ 8.1 della spec di Fase 3). Lo step 2 ne ha 4.229.538 e viene decimato di
   circa dieci volte; lo step 3 ne ha 116.059 e viene disegnato intero. Il salto
   che si vede non è il salto vero, e il passo del voxel che lo spiega **il
   server lo calcola già e lo manda** nell'intestazione `X-Voxel`
   (`app/server.py:510`), dove `ui/app.js` lo butta senza leggerlo.

**«Manca un modo di tornare indietro.»** Vero e senza attenuanti. `PUT
/api/config`, `POST /api/crop` e `POST /api/cluster` riscrivono `config.yaml`
sul posto (`app/server.py:307`, `:464`, `:616`). Non esiste storico né
ripristino. L'unico rollback presente rimette nel campo il valore di prima
quando la PUT fallisce (`ui/app.js:705`): copre un errore di rete, non un
ripensamento.

### 1.2 Cosa consegna questa fase

Un viewport che mantiene lo stato attraverso il cambio di step, dichiara ciò che
un passaggio ha tolto, e un ritorno indietro sulle modifiche di configurazione
che sopravvive al riavvio del server.

---

## 2. Decisioni prese in brainstorming

| Decisione | Alternativa scartata | Perché |
|---|---|---|
| Continuità automatica della vista | Livelli accendibili a mano, una casella per step | Un comando in più da imparare, e l'utente successivo confermato non conosce gli undici step (`PRODUCT.md` § Users). Resta scritto come evoluzione, § 10 |
| Fantasma acceso di default solo dove il conteggio cala | Fantasma sempre acceso | Due superfici quasi coincidenti fanno z-fighting e non informano nessuno |
| Storico su disco | Pila in memoria del server | Costa una quindicina di righe in più, sopravvive al riavvio, e la provenienza viene gratis — principio 4 di `PRODUCT.md`. Una pila in memoria muore proprio quando serve sapere cosa si era cambiato |
| Innesto dello storico nel server | Innesto in `core.config.save_config` | `save_config` la chiamano anche `pipeline` e `sweep`: uno sweep depositerebbe una versione per candidato |
| Tabella esplicita step → artefatto | Calcolo su `ARTIFACTS` | `core/pipeline.py:42-48` documenta che un calcolo equivalente era già sbagliato in due punti. Stesso errore, stessa cura |

---

## 3. Architettura: che cosa si tocca

Quattro file, di cui uno nuovo.

| File | Che cosa cambia |
|---|---|
| `ui/viewport.js` | Camera che non si azzera, pan, secondo gruppo per il fantasma |
| `ui/app.js` | Tabella step → artefatto con ricaduta a monte, comando «Inquadra», Ctrl+Z, lettura di `X-Voxel` |
| `app/server.py` | `scrivi_config()` al posto delle tre chiamate dirette a `save_config`, due endpoint dello storico |
| `app/storico.py` | Nuovo. Deposito delle versioni, cursore, tetto |

Nessun file del `core/` cambia. È deliberato: il core ha prodotto tutti i numeri
delle Fasi 1 e 2 e non ha ragione di muoversi per un problema di vista.

---

## 4. La camera non si azzera

`inquadra()` smette di essere incondizionata. La chiamano soltanto due strade:
la prima geometria disegnata dopo l'avvio, e il comando esplicito — un bottone
«Inquadra» accanto ai conteggi, più il tasto `f` sulla tela, che è già
raggiungibile da tastiera (`ui/viewport.js:34`).

**Una guardia serve, e va detta.** Cambiando corsa — da `muro` a `lab_crop` —
l'ingombro nuovo può cadere fuori dalla vista corrente, e la camera resterebbe
puntata sul vuoto senza che nulla lo spieghi. La condizione è una sola e si
verifica: si reinquadra quando il centro del nuovo ingombro cade **fuori dalla
sfera** di raggio `orbita.raggio` centrata in `orbita.centro`. Dentro quella
sfera la geometria nuova è già visibile e non c'è ragione di spostare la camera;
fuori, non lo è, e lasciarla ferma mostrerebbe uno schermo vuoto.

`ingombro()` (`ui/viewport.js:206`) restituisce già ciò che serve per il
confronto e non va toccata.

**Il controllo che lo smentisce.** Un test sul modulo verifica che dal secondo
disegno in poi `inquadra()` non venga chiamata, e un secondo test verifica che
venga chiamata quando l'ingombro nuovo è disgiunto da quello vecchio. Senza il
secondo, il primo si soddisfa anche non chiamandola mai, che è il difetto
opposto e altrettanto reale.

---

## 5. Gli step senza geometria propria

Una tabella esplicita, nella forma di `_RESUME_POINTS` (`core/pipeline.py:52`),
che copre tutti e undici gli step:

| Step | Geometria mostrata | Da chi viene |
|---|---|---|
| 1 | `01_cloud.ply` | propria |
| 2 | `02_segmented.ply` | propria |
| 3 | `03_downsampled.ply` | propria |
| 4 | `04_normals.ply` | propria |
| 5 | `05_surface.ply` | propria |
| 6 | `06_repaired.ply` | propria |
| 7 | `06_repaired.ply` | **step 6** |
| 8 | `08_simplified.ply` se `simplify.enabled`, altrimenti `06_repaired.ply` | propria o **step 6** |
| 9 | `09_volume.vtu` | propria |
| 10 | `09_volume.vtu` | **step 9** |
| 11 | `09_volume.vtu` | **step 9** |

La riga dello step 8 non è un capriccio: `08_simplified.ply` esiste soltanto se
la semplificazione è abilitata, e `core/pipeline.py:57-58` documenta la stessa
dipendenza per `from_step=9`. Con `simplify.enabled: false`, che è il valore del
config di lavoro, oggi lo step 8 mostra un viewport vuoto pur essendo uno step
riuscito.

**La geometria altrui si dichiara sempre.** La didascalia sotto il viewport
scrive, per gli step 7, 10, 11 e per l'8 non abilitato:

> lo step 7 misura e non produce geometria: mostrata la superficie dello step 6

Mostrare l'artefatto di un altro step senza dirlo sarebbe esattamente il
risultato plausibile che nessuna metrica smentisce — principio 3 di
`PRODUCT.md`. È il motivo per cui la ricaduta a monte e la sua didascalia sono
un punto solo e non due.

**Resta distinto da «non c'è».** Uno step il cui artefatto a monte non esiste
ancora continua a dire che non c'è nulla da mostrare, e lo dice nominando lo
step che deve girare per primo.

---

## 6. Il fantasma del passaggio precedente

Un secondo gruppo nella scena, accanto a quello della geometria corrente:
materiale grigio, opacità 0,15, `depthWrite: false` perché non deve occludere
ciò che sta davanti.

La sorgente è l'artefatto dello step precedente **che ne ha uno proprio**, cioè
la stessa tabella del § 5 letta all'indietro. Sui tre step dove il fantasma
nasce acceso la coppia è fissa e vale la pena scriverla: step 2 → `01_cloud.ply`,
step 3 → `02_segmented.ply`, step 8 → `06_repaired.ply`.

**Acceso di default soltanto dove il conteggio cala**: step 2 (ritaglio), 3
(voxel) e 8 con semplificazione abilitata. Altrove nasce spento, e un
interruttore accanto ai conteggi lo accende. Su due superfici quasi coincidenti
— step 5 contro 6, per dire — il fantasma produce z-fighting e nessuna
informazione.

**Il controllo che lo smentisce.** Il fantasma dichiara due conteggi come la
geometria corrente, disegnato e pieno, e **il pieno** deve coincidere con il
conteggio che `metrics.json` porta per lo step che l'ha prodotto: `points_after`
per una nuvola, `vertices` per una superficie. Il disegnato no, ed è giusto:
anche il fantasma passa dal budget dei 400.000 punti. Confrontare il disegnato
sarebbe confrontare due decimazioni fra loro invece che il dato con la sua
misura.

Un fantasma che disegna una nuvola diversa da quella che dichiara è la forma
esatta del risultato plausibile contro cui è costruito tutto il progetto. Il
test si scrive su `lab_crop`, dove i valori sono già misurati e fermi: sullo
step 2 il fantasma dichiara i 6.329.096 punti dello step 1 (`points_kept`),
sullo step 3 i 4.229.538 dello step 2 (`points_after`).

**Costo.** Il commento a `svuota()` (`ui/viewport.js:158`) misura 7,6 MB di
attributi per geometria sul ciclo fra gli step 5, 6 e 9. Il fantasma raddoppia
quella cifra. Su un budget di disegno di 400.000 punti resta trascurabile, e
`svuota()` libera già entrambi i gruppi con la stessa traversata purché il
gruppo nuovo stia dentro `gruppo` — come già fa il box di ritaglio, per la
ragione scritta a `ui/viewport.js:44-48`.

**Una riga che il server ha già pagato.** Accanto ai due conteggi va il passo
del voxel di disegno, che `app/server.py:510` calcola e manda in `X-Voxel` e che
`ui/app.js:226-227` non legge. È ciò che spiega perché la densità disegnata
salta fra lo step 2 e lo step 3, ed è un fatto già misurato che oggi si butta.

---

## 7. Pan della camera

Oggi `orbita.centro` cambia soltanto dentro `inquadra()`
(`ui/viewport.js:145-151`): si ruota e si zooma, non si trasla. Su un telaio
largo 2.759 mm non si raggiunge uno spigolo.

Shift più trascinamento sposta il centro nel piano della camera; Shift più le
frecce fa lo stesso da tastiera, con lo stesso passo discretizzato che i comandi
esistenti già usano (`ui/viewport.js:105-119`). L'`aria-label` della tela
elenca i comandi e va esteso ai nuovi, altrimenti dichiara meno di quanto la
tela faccia.

Il bottone «Inquadra» del § 4 è l'uscita di sicurezza: qualunque smarrimento si
chiude con un clic.

---

## 8. Ritorno indietro sulle modifiche

### 8.1 Il punto d'innesto, e quello sbagliato

Tre siti scrivono il config dal server: `PUT /api/config`
(`app/server.py:307`), `POST /api/crop` (`:464`), `POST /api/cluster` (`:616`).
Tutti e tre chiamano `save_config`. Una funzione `scrivi_config(cfg)` locale al
server prende il loro posto: deposita la versione di partenza, poi chiama
`save_config`. Tre chiamate cambiate, un punto solo da sorvegliare.

**`core.config.save_config` (`core/config.py:284`) non si tocca.** La chiamano
anche `pipeline` e `sweep`, e agganciare lo storico lì significherebbe
depositare una versione per ogni candidato di uno sweep. Il punto condiviso
giusto è il server, non il core: è il server a servire i gesti di una persona,
ed è dei gesti di una persona che si tiene lo storico.

Un test di regressione sorveglia proprio questo: uno sweep non deve lasciare
nulla in `.storico/`.

### 8.2 Il deposito

Dentro la cartella della corsa, accanto a `config.yaml`:

```
runs/<nome>/.storico/
  0001.yaml           versione di partenza prima della prima modifica
  0002.yaml
  registro.jsonl      una riga per versione
  cursore.json        dove siamo adesso
```

Ogni riga di `registro.jsonl` porta l'istante, l'endpoint che ha scritto e
l'elenco dei campi cambiati. È la stessa forma in sola aggiunta del registro
degli esperimenti della Fase 2, per la stessa ragione: un file che si allunga
non perde ciò che aveva.

**Tetto a 200 versioni**, poi le più vecchie si scartano. Misurato e non scelto:
il config di lavoro pesa 1.328 byte, quindi il tetto costa 265,6 kB, contro i
circa 400 MB di artefatti che una corsa lascia (`PRODUCT.md` § Operating
Context).

### 8.3 I comandi

`POST /api/storico/indietro` rimette la versione precedente e arretra il
cursore. `POST /api/storico/avanti` lo riporta in avanti. Una scrittura nuova
tronca la coda oltre il cursore, come ogni undo che non voglia far convivere due
futuri.

Nel browser Ctrl+Z e Ctrl+Shift+Z li chiamano. Sono gli unici tasti globali che
questa fase aggiunge, e non entrano in conflitto con i comandi della tela
(frecce, `+`, `-`, `f`), che restano legati al canvas col fuoco sopra.

**Lo storico vuoto risponde, non tace.** `{"annullato": false, "perche":
"niente da annullare"}`, con un messaggio nell'interfaccia. Il difetto opposto —
un silenzio identico fra riuscita e nulla-da-fare — è già stato prodotto e
corretto una volta su questo stesso progetto, sul bottone Annulla
(`ui/app.js:118-119`), e non va rifatto per una seconda strada.

### 8.4 Che cosa l'undo non disfa

**Gli artefatti già scritti sul disco.** Ripristinare il config non cancella
`02_segmented.ply`.

Non serve che lo faccia: la catena di impronte della § 6 della spec di Fase 3
ricalcola l'impronta dello step dal config corrente, e un config ripristinato
riporta a «non valido» gli step che quella modifica aveva toccato. È il
comportamento giusto — l'artefatto resta sul disco, dichiarato non valido,
pronto a essere rifatto o a tornare valido se si preme «avanti» — e non costa
una riga di codice nuovo. Questa fase eredita quel meccanismo e non lo duplica.

Va detto nell'interfaccia, però: dopo un ritorno indietro il messaggio dice
quali step sono passati a «non valido». Un undo che cambia in silenzio lo stato
di sette step sarebbe una modifica invisibile.

---

## 9. Errori, e i controlli che smentiscono

Il contratto della § 8.4 della spec di Fase 3 vale sulla tratta e non sulla
funzione: **nessun endpoint solleva verso il browser**. I due endpoint nuovi
entrano nell'elenco del test parametrizzato esistente, che è scritto apposta per
fallire quando un endpoint nuovo non ci entra.

I controlli che questa fase deve avere, elencati con la grandezza che
sorvegliano:

| Cosa si afferma | Che cosa lo smentisce |
|---|---|
| La camera non si azzera | Dal secondo disegno in poi `inquadra()` non è chiamata |
| La camera non lascia lo schermo vuoto | Con ingombro disgiunto `inquadra()` **è** chiamata |
| Il fantasma disegna ciò che dichiara | Conteggio dichiarato contro `metrics.json` su `lab_crop` |
| Ogni step ha una geometria | La tabella del § 5 risolve 1..11 senza `KeyError`, con `simplify.enabled` a entrambi i valori |
| L'undo ripristina davvero | Scrivi, indietro, il `config.yaml` è byte per byte quello di prima |
| L'undo non tace a vuoto | Storico vuoto risponde con il proprio `perche` |
| Il tetto tiene | Alla 201-esima versione la prima non c'è più e il cursore è coerente |
| Lo storico è del server, non del core | Uno sweep non lascia nulla in `.storico/` |
| Ctrl+Z è legato | Il modulo registra il gestore |

I test attuali restano verdi: **402 selezionati su 408 raccolti**, con i 6
deselezionati che restano tali. Il conteggio è misurato al commit `59ab9c9` e
va riletto quando questa fase parte, perché la critica del giro 3 ne aggiunge.

---

## 10. Fuori scope

**Livelli accendibili a mano.** Una casella per step nella colonna sinistra, per
scegliere quali sovrapporre. È l'evoluzione naturale del fantasma del § 6 e
resta scritta qui come tale: si costruisce quando il fantasma automatico si
dimostrerà insufficiente, non prima.

**Modifica della geometria dal viewport.** La § 15 della spec di Fase 3 la
esclude e questa fase non la riapre: il viewport ispeziona e seleziona, non
scolpisce. Di conseguenza l'undo agisce sulla configurazione, mai sui vertici.

**Il ritaglio adottato.** I 301,5 mm di piedistalli che il box toglie restano
tolti. Il ritaglio è la scelta di modellazione della tesi, la corsa `lab_crop` è
di sola lettura (`PRODUCT.md` § Evidence on Hand), e nulla qui la tocca. Questa
fase rende visibile che cosa è stato tolto; non cambia che cosa si toglie.

### 10.1 Debito che questa fase lascia aperto

Trovati durante il riesame dell'interfaccia, veri, e deliberatamente non chiusi
qui perché nessuno dei tre problemi riportati passa da loro:

- **I punti sono tutti dello stesso colore** (`0x2f5d50`,
  `ui/viewport.js:183`). I cluster non si distinguono a occhio prima di
  cliccarli, quindi la selezione del cluster si fa alla cieca.
- **Il box di ritaglio non si vede sugli step a valle.** `svuota()` lo libera e
  nulla lo ridisegna, quindi non si vede mai il box accanto al risultato che ha
  prodotto.
- **Il piano di taglio esiste solo sullo step 9** (`ui/app.js:285`). La
  superficie degli step 5 e 6 non si ispeziona dall'interno.
- **«Nessun artefatto per questo step»** dice la stessa cosa per «mai eseguito»
  e per «artefatto cancellato». Il § 5 riduce i casi in cui compare, non
  l'ambiguità di quando compare.
- **La dimensione dei punti è fissa a 1,5** senza attenuazione con la distanza
  (`ui/viewport.js:183`): da lontano 400.000 punti diventano una macchia piena.

---

## 11. Criteri di accettazione

1. Passando dallo step 3 al 4 su `lab_crop` la camera resta dove l'utente
   l'aveva messa.
2. Cambiando corsa la camera si reinquadra da sola e la geometria è visibile.
3. Gli step 7, 10 e 11 mostrano una geometria e dichiarano di quale step è.
4. Lo step 8 con `simplify.enabled: false` mostra la superficie dello step 6 e
   lo dichiara.
5. Sullo step 2 il fantasma mostra la nuvola dello step 1: dichiara 6.329.096
   punti pieni, mentre la geometria corrente ne dichiara 4.229.538.
6. Accanto ai conteggi compare il passo del voxel di disegno.
7. Shift più trascinamento trasla la vista; «Inquadra» la riporta sull'ingombro.
8. Una modifica di parametro seguita da Ctrl+Z rimette il `config.yaml`
   precedente, e l'interfaccia elenca gli step tornati «non validi».
9. Ctrl+Z a storico vuoto dice che non c'è nulla da annullare.
10. Uno sweep di Fase 2 non lascia nulla in `.storico/`.
11. La suite passa: i test attuali più quelli nuovi, con i 6 deselezionati che
    restano tali.
