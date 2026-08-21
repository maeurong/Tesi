# Fase 5 — analisi strutturale del telaio as-built

Data di apertura: 21/08/2026. Corsa di riferimento: `runs/lab_telaio_v2`,
rigenerata il 21/08/2026 alle 22:14 sul ramo `feat/fase-5-analisi-strutturale`.
Ogni numero di questo documento e' stato misurato su quella corsa, e porta
accanto **il file e il campo da cui viene**. I numeri della sezione sul deficit
di volume — che non stanno in nessun campo, perche' vanno calcolati — li
riproduce uno script committato,
[`docs/fase-5-cantiere/misura-deficit.py`](fase-5-cantiere/misura-deficit.py):
`uv run python docs/fase-5-cantiere/misura-deficit.py`. Ogni valore che quello
script stampa porta il proprio `assert` contro il valore pubblicato qui, quindi
se la corsa cambia lo script cade invece di stampare in silenzio numeri diversi
dal documento.

---

## Il deficit di volume: dove va il volume che manca

Il modello as-built vale meno della meta' del telaio di tavola. Questa sezione
dice **dove** va la differenza, con quanta incertezza, e dichiara la parte che
**non** si riesce ad attribuire.

L'esito in una riga: **il deficit e' quasi per intero materiale che sta sotto
il piano di taglio, mai entrato nella scansione. L'assottigliamento della
ricostruzione, la seconda causa candidata, non si misura: sopra il piano di
taglio il residuo sta fra -8,6 e +14,0 milioni di mm³, cioe' attraversa lo
zero.**

### 1. I due termini del confronto

**Il nominale, dalla tavola `MURO 1`** (`docs/fase-4-materiale.md`, righe 12-17),
ricalcolato membratura per membratura:

| membratura | sezione [mm] | lunghezza [mm] | n. | volume [mm³] |
|---|---|---|---|---|
| Zapata | 700 x 250 | 700 | 2 | 245.000.000 |
| Viga inferior | 250 x 250 | 1300 | 1 | 81.250.000 |
| Columna | 172 x 172 | 1695 | 2 | 100.289.760 |
| Viga superior | 140 x 175 | 2090 | 1 | 51.205.000 |
| **totale** | | | **6** | **477.744.760** |

La tavola dichiara 0,4777 m³, cioe' 477.700.000 mm³: scarto 44.760 mm³, lo
0,0094%. La tavola e' coerente con se' stessa e si usa come riferimento senza
riserve. Nel seguito il nominale e' il **ricalcolato**, 477.744.760 mm³.

**Il modello**, da `runs/lab_telaio_v2/metrics.json`, campo
`10_volume_quality.total_volume`: **217.728.361,2 mm³**, su 14.103 nodi e
51.913 tetraedri, zero invertiti. Il valore e' stato ricalcolato in questa
sessione dal prodotto misto dei 51.913 tetraedri di `09_volume.vtu` e coincide
a un decimo di mm³; ricalcolato una terza volta dalle coordinate del deck
`wall_model.inp` effettivamente risolto, coincide ancora.

**Deficit misurato: 260.016.399 mm³.** Il modello e' il **45,57%** del
nominale.

### 2. Il piano di taglio, e in quale sistema di riferimento sta

Il ritaglio della corsa e' `crop_min = [1690, -680, -498]`,
`crop_max = [4460, 70, 1230]` (`runs/lab_telaio_v2/config.yaml`). La quota che
conta e' `crop_min[2] = -498`.

Va detto subito perche' e' la trappola di questa sezione: **il modello risolto
e il ritaglio stanno nello stesso sistema di riferimento**, e i due numeri sono
confrontabili. La verifica, in questa sessione:

| oggetto | x | y | z |
|---|---|---|---|
| `02_segmented.ply` (nuvola ritagliata) | 1716,5 .. 4325,5 | -660,5 .. 54,5 | -497,5 .. 1218,5 |
| `09_volume.vtu` (solido tetraedrico) | 1630,8 .. 4327,6 | -741,6 .. 134,2 | -595,4 .. 1204,3 |
| `13_solution.vtu` (soluzione) | 1630,8 .. 4327,6 | -741,6 .. 134,2 | -595,4 .. 1204,3 |
| `wall_model.inp` (deck risolto) | 0 .. 875,2 | 0 .. 2698,2 | 0 .. 1799,7 |

Solo il **deck** e' traslato e ruotato sulla terna misurata; il solido e la
soluzione restano nelle coordinate della scansione. Il volume e' invariante per
rototraslazione, quindi i 217.728.361,2 mm³ sono gli stessi nei due sistemi.

Il pavimento, rimisurato qui con RANSAC (`segment_plane`, soglia 3x la
spaziatura di 1,1923 mm, sui punti con z < -350 nella fascia x 1690-4460):
normale (0,0043, -0,0039, 1,0000), circa 520-550 mila punti interni con il
bordo alto fra **-502,5 e -497,5** secondo l'estrazione. Il § 8 di
`docs/fase-4-prior-telaio.md` aveva misurato -498,5 sulla stessa nuvola, e cade
dentro quella banda. **RANSAC e' stocastico e qui la dispersione fra estrazioni
vale 5 mm**: e' quella, non il singolo valore, la misura utile. Lo script di
cantiere fissa il seme a 0 per riproducibilita' — 519.660 punti interni, bordo
alto -497,5 — e dichiara la banda accanto, perche' il seme rende ripetibile il
numero, non piu' preciso.

**Conseguenza, e va letta al contrario di come suona:** il piano di taglio a
-498 cade **entro 4,5 mm dal bordo alto del pavimento**, cioe' dentro la
dispersione della misura stessa: taglio e pavimento **coincidono**. Il ritaglio non
taglia via le zapatas — le zapatas non ci sono perche' **lo scanner non le ha
mai viste**: sotto quella quota c'e' il pavimento, e sotto il pavimento non
c'e' informazione. Il piano di taglio e' il posto dove finisce il dato, non il
posto dove qualcuno ha deciso di tagliare il pezzo.

### 3. Quanta parte del nominale sta sotto il piano di taglio

La tavola da' sezione e lunghezza di tutte e sei le membrature, ma **non
l'orientamento**. L'orientamento e' stato ricavato dalla geometria, non scelto.

**L'altezza della zapata e' 250 mm, non 700.** La sezione 700 x 250 e la
lunghezza 700 lasciano due letture. Il punto di transizione fra la base e la
columna e' misurato: nella nuvola grezza, per **entrambe** le colonne,
l'ampiezza in y crolla da ~435 mm a ~211 mm fra z = -468 e z = -466 (fascia sx
x 1690-2600, dx x 3900-4460, percentili 1-99 su fette da 2 mm). La columna
comincia quindi a z ~ -467, appena 32 mm sopra il pavimento: una zapata alta
700 mm porterebbe l'attacco della columna a z ~ +200. Resta 250 mm, e la pianta
e' 700 x 700.

**La viga inferior sta esattamente nella luce fra le due zapatas.**
700 + 1300 + 700 = 2700 mm, che e' il fuori-tutto in x dichiarato in tavola.
L'aritmetica non lascia alternative.

**La quota della viga inferior e' misurata.** Nella campata centrale
(x 2500-3700) la nuvola grezza **non ha un solo punto sopra z = -484**; l'ultima
fascia popolata, z fra -500 e -490, conta 3.363 punti larghi 287 mm in y
(nominale 250). Il bordo alto della viga inferior sta quindi fra -490 e -484, e
con i suoi 250 mm di altezza il bordo basso sta fra -740 e -734.

**La quota della zapata ha due ancoraggi che non coincidono.**

- dalla transizione misurata: bordo alto -467 ± 1, bordo basso -717;
- dal fuori-tutto: 1945 = 250 (zapata) + 1695 (columna), quindi bordo basso
  della zapata = sommita' del telaio - 1945. La sommita' misurata sta fra 1207
  (dove i ritorni collassano: 1.821 punti nella fascia 1205-1207, 339 nella
  fascia 1208-1210) e 1218,5 (massimo assoluto, coda di rumore). Bordo basso
  fra -738 e -726,5.

I due ancoraggi danno **h(zapata) fra 219 e 240 mm** sotto il piano di taglio,
su 250 nominali: dall'87,6% al 96,0% dell'altezza della zapata. Lo scarto di
21 mm fra gli ancoraggi e' della stessa classe dell'errore di lettura gia'
misurato su questa nuvola (le colonne si leggono ~205 x 200 mm contro 172 x 172
nominali, `docs/fase-4-materiale.md`). **Non si sceglie fra i due: si porta la
banda.**

Volume nominale sotto z = -498:

| membratura | area in pianta [mm²] | altezza interrata [mm] | volume [mm³] |
|---|---|---|---|
| Zapata x2 | 980.000 | 219 .. 240 | 214.620.000 .. 235.200.000 |
| Viga inferior | 325.000 | 236 .. 242 | 76.700.000 .. 78.650.000 |
| Columna x2, Viga superior | — | 0 | 0 |
| **totale sotto il taglio** | | | **291.320.000 .. 313.850.000** |

### 4. La smentita da riportare, non da riscalare

Il volume nominale sotto il piano di taglio — da 291,3 a 313,9 milioni di mm³ —
**e' maggiore del deficit misurato**, che vale 260,0 milioni. Preso alla
lettera, e' una contraddizione, ed e' il caso che questa fase si era imposta di
fermare invece di aggirare.

Non e' una contraddizione, e la ragione va scritta perche' e' il secondo
risultato di questa sezione: **il modello mette 45,3 milioni di mm³ sotto il
piano di taglio, dove non ha un solo punto per farlo.**

Misurato per clipping esatto dei tetraedri contro il piano z = -498 (1.394
tetraedri attraversati, ciascuno ritagliato e chiuso con l'inviluppo convesso
dei suoi vertici sotto il piano):

- volume del modello **sotto** z = -498: **45.283.601 mm³**, il **20,80%** del
  totale;
- volume del modello **sopra** z = -498: **172.444.760 mm³**.

Quel volume e' la chiusura cieca di Poisson. La nuvola ritagliata non ha punti
sotto z = -497,5; Poisson chiude la superficie aperta lasciata dal taglio e
scende fino a -595,4, quasi 98 mm sotto il piano. E non ha la forma di due
zapatas: l'area orizzontale del modello a z = -520 vale **611.280 mm²** e si
estende da x 1660 a x 4301, y da -707 a +100 — **una soletta larga quanto tutto
il telaio**, non due plinti da 700 x 700. E' il pavimento che il ritaglio ha
sfiorato, richiuso in solido.

Rifatta la contabilita' con i due termini separati sopra e sotto il piano, la
somma torna esatta:

| | nominale [mm³] | modello [mm³] | deficit [mm³] | quota del deficit |
|---|---|---|---|---|
| sotto z = -498 | 291.320.000 .. 313.850.000 | 45.283.601 | 246.036.399 .. 268.566.399 | 94,6% .. 103,3% |
| sopra z = -498 | 186.424.760 .. 163.894.760 | 172.444.760 | +13.980.000 .. -8.550.000 | +5,4% .. -3,3% |
| **totale** | **477.744.760** | **217.728.361** | **260.016.399** | **100%** |

(le due righe sono accoppiate: la banda alta sotto il taglio corrisponde alla
banda bassa sopra, e la somma resta 260.016.399 in ogni punto della banda.)

### 5. La ripartizione, e cosa resta non attribuito

**Attribuito — il taglio: dal 94,6% al 103,3% del deficit**, cioe' da 246,0 a
268,6 milioni di mm³. Sono le zapatas e la viga inferior sotto il pavimento,
al netto della soletta che Poisson ha inventato al loro posto.

**Non attribuito — il residuo sopra il taglio: fra -8,6 e +14,0 milioni di
mm³**, cioe' fra il -3,3% e il +5,4% del deficit. La banda **attraversa lo
zero**: con i dati di questa corsa **non si puo' dire se sopra il piano di
taglio il modello sia in difetto o in eccesso rispetto al nominale**, ne' di
quanto. Il brief di questo task assumeva che quel residuo fosse
l'assottigliamento di Poisson; la misura non lo sostiene. Non si stima un
numero per riempire il buco: la risposta e' la banda, con il suo segno
indeterminato.

Cosa allarga la banda, e non e' riducibile senza dati nuovi:

1. **la quota di attacco della zapata**, nota a ± 10 mm da due ancoraggi che
   non coincidono (§ 3). Vale 20,6 milioni di mm³ di banda, da sola;
2. **i 45,3 milioni di mm³ di soletta inventata** (§ 4): non sono materiale
   misurato e non appartengono a nessuna delle due cause. Entrano nella
   contabilita' solo come termine correttivo, e mascherano il taglio invece di
   spiegarlo. Se domani il ritaglio scendesse sotto il pavimento, quel termine
   cambierebbe di segno e di grandezza;
3. **il nominale potrebbe non essere il riferimento giusto.** La scansione
   legge le colonne ~205 x 200 mm contro 172 x 172 di tavola (+39% di area). Se
   l'as-built e' davvero piu' grosso del disegno, il deficit vero e' maggiore
   di 260,0 milioni e il residuo sopra il taglio si sposta verso il negativo.
   Serve un rilievo calibrato del pezzo, che non esiste.

**Non attribuito per membratura.** La corsa trova 8 regioni e accetta **zero
membrature** (`12_wall.json`: `membrature: []`, `regioni_trovate: 8`,
`pavimento_trovato: false`). Non esiste quindi un volume per membratura da
estrarre dal modello, e **nessuna riga della tabella di tavola puo' essere
confrontata singolarmente** con la sua controparte ricostruita: il confronto e'
solo aggregato. Restano inoltre due orientamenti non risolti, dichiarati con il
loro nome invece di essere scelti:

- **Zapata** — la pianta 700 x 700 e' dedotta dall'aritmetica del fuori-tutto
  (§ 3), non vista. Il moncone visibile fra z = -482 e z = -467 misura circa
  200 mm in x e 560 mm in y: non corrisponde ne' a 700 x 700 ne' a 700 x 250.
  L'altezza 250 mm e' invece stabilita, ed e' l'unica dimensione che entra nel
  conto del volume interrato, che quindi **non** ne risente.
- **Viga superior** — quale dei due lati, 140 o 175, sia il verticale non e'
  determinabile: il modello legge quella fascia ~24% piu' larga del nominale.
  Sta interamente sopra il piano di taglio, quindi **non** entra nel conto.

### 6. Verifica con lo spessore: sulle colonne libere non c'e' assottigliamento

Lo spessore mediano misurato da `wall.regioni` vale **192,0267 mm**
(`12_wall.json`, `spessore_mediano`). Le dimensioni di sezione nominali sono
140, 172, 175, 250 e 700 mm: 192 sta **dentro** l'intervallo, fra 175 e 250.
Un assottigliamento uniforme lo porterebbe sotto il minimo, e non ci va.

La misura diretta e' piu' netta dell'argomento sulla mediana. Area orizzontale
del modello in funzione della quota, derivata esatta del volume ritagliato con
passo 20 mm:

| z [mm] | area del modello [mm²] | due colonne nominali [mm²] | scarto |
|---|---|---|---|
| -460 | 63.585 | 59.168 | +7,5% |
| -300 | 62.740 | 59.168 | +6,0% |
| 0 | 62.959 | 59.168 | +6,4% |
| +600 | 61.901 | 59.168 | +4,6% |
| +900 | 60.592 | 59.168 | +2,4% |

Su tutta l'altezza libera delle colonne il modello e' **piu' grosso** del
nominale, dal 2,4% al 7,5%, mai piu' sottile: qui l'assottigliamento di Poisson
non c'e', e il segno e' misurato, positivo e monotono.

**Questo non chiude il residuo del § 5, e i due non si contraddicono.** Questa
tabella confronta le **sole colonne libere**, la fascia di quota dove la
sezione nominale e' fatta di due soli prismi. Il residuo del § 5 sta invece
sull'**intero nominale sopra il piano di taglio**, che comprende anche i
tronconi emersi di zapata e viga inferior (da 10 a 31 mm di zapata e da 8 a 14
di viga, § 3) e la fascia della viga superior, dove il modello legge il 24% in
piu' del nominale ma la profondita' della trave non e' determinabile (§ 5). Su
quelle fasce nessuna misura di sezione e' stata fatta. Quindi: **sulle colonne
il segno e' noto e positivo; sul totale sopra il taglio resta indeterminato**,
e resta tale.

Cio' che manca al modello, comunque, non e' spalmato sulle pareti: e' un pezzo
intero che sta sotto il taglio.

### 7. Conseguenza strutturale

**Il peso proprio del modello e' 5.339,79 N**, da 217.728.361,2 mm³ x
2,5e-9 t/mm³ x 9810 mm/s². Il telaio nominale pesa **11.716,69 N**. Il rapporto
delle masse e' **0,4557** — lo stesso denominatore ricalcolato del § 1, non
i 477.700.000 mm³ dichiarati in tavola, che darebbero 0,4558.

Prima una precisazione che serve a non sbagliare il numero: i **4.162,39 N** che
la corsa riporta in `13_solve.controlli.reazioni` **non sono il peso**. Sono la
reazione trasmessa attraverso la struttura al set `BASE`, al netto della quota
tributaria caricata direttamente sui nodi vincolati, che `solve.py:610`
sottrae apposta da `peso_atteso`. Quella quota vale 5.339,79 - 4.162,39 =
**1.177,40 N**, il 22,05% del peso — alta proprio perche' la soletta inventata
del § 4 appoggia molti nodi su `BASE`.

**La scalatura ingenua «le tensioni stanno come le masse, 0,456» non regge, e
va scartata.** Sotto peso proprio la tensione a una quota vale, in media, il
peso sovrastante diviso l'area della sezione; il volume che manca sta tutto
**sotto** il piano di taglio, cioe' **sotto** il percorso del carico, e non
pesa su nulla.

| | peso sopra z = -498 [N] |
|---|---|
| modello | 4.229,21 |
| telaio nominale | 4.019,52 .. 4.572,07 |

Il modello porta quindi dal **92,5% al 105,2%** del carico che il telaio vero
manda nelle colonne, non il 45,6%: **±8% sul carico**, non su un fattore 2,2.
Il ±8% e' l'errore del **solo numeratore** di σ = F/A. Il denominatore ha
un'incertezza propria e piu' grande — l'errore geometrico vale il 14,3% dello
spessore in RMS (§ 6) e le colonne del modello escono dal 2,4% al 7,5% piu'
grosse del nominale — e **qui le due non sono composte**.

Lo conferma la posizione del picco. Il massimo di von Mises sotto gravita' vale
**0,51 MPa** e cade a z = **+1010 mm**, cioe' nella viga superior, 1.606 mm
sopra il punto piu' basso del modello — **non alla base**. Il volume mancante
sta 1,5 m piu' in basso e non lo tocca. Le tensioni delle altre due condizioni:
SPINTA_ORIZZONTALE **0,68 MPa**, CARICO_TOP **0,98 MPa**
(`13_solve.casi`).

Quel che il volume mancante toglia davvero e' un'altra cosa, e va detta come
limite, non come numero: **il set `BASE` di questo modello non e' la faccia
inferiore di una zapata, e' la sezione di taglio a filo pavimento.** Il modello
e' incastrato dove finisce il dato. Manca quindi ogni effetto della fondazione
— diffusione della tensione nel plinto, cedevolezza rotazionale dell'appoggio —
e il modello e' alla base piu' rigido del telaio vero. Sulla prima frequenza
(21,2 Hz, `13_solve.frequenze_hz`) l'effetto e' presumibilmente piccolo,
perche' la massa che manca sta al vincolo e non partecipa al primo modo, ma
**questa e' un'attesa, non una misura**: non e' stata verificata.

### 8. Come rimisurare tutto questo

Le misure di questa sezione non stanno nel programma: `src/` non contiene, e non
deve contenere, alcun numero del provino. Stanno in
[`docs/fase-5-cantiere/misura-deficit.py`](fase-5-cantiere/misura-deficit.py),
committato apposta perche' «riscriviti lo script» non e' riproducibilita':

```
uv run python docs/fase-5-cantiere/misura-deficit.py
```

Rilegge `runs/lab_telaio_v2/01_cloud.ply`, `09_volume.vtu` e `13_solution.vtu`
con `open3d`, `meshio` e `scipy.spatial`, e rifa' da capo il nominale di tavola,
il volume del solido, il pavimento, la ripartizione del deficit, il profilo
delle aree, i pesi e l'elemento del picco. **Ogni valore stampato porta il
proprio `assert` contro il numero pubblicato qui**: se la corsa cambia lo script
cade e nomina la grandezza che si e' mossa, invece di stampare in silenzio
numeri diversi dal documento. Serve la corsa in `runs/lab_telaio_v2/` — se manca,
lo script lo dice e si ferma invece di misurare la cartella sbagliata.

Le sole grandezze che **non** rifa' sono quelle gia' scritte in un campo di
`metrics.json` o di `12_wall.json`, che il documento cita nominando il campo.

---

## Che cosa gira, e che cosa no

**Gira.** `uv run meshrec run lab_telaio.yaml` porta a termine tredici step,
uscita 0. Lo step 13 esegue CalculiX 2.22 (`/Users/mario/.local/bin/ccx`) sul
deck della corsa e lascia `13_solution.frd/.vtu/.dat`, `13_solver.log` e la
provenienza in `metrics.json`. Il deck ha quattro passi —
`GRAVITA`, `SPINTA_ORIZZONTALE`, `CARICO_TOP`, `MODALE`
(`11_export.casi_di_carico`) — e il solutore li legge a **zero avvisi e zero
errori** (`13_solve.avvisi`, `13_solve.errori`).

**Non gira, ed e' un esito dichiarato, non un ostacolo.** Il modello
parametrico non esiste su questa geometria: `12_wall.json` porta
`regioni_trovate: 8` e `membrature: []`, zero accettate su sei attese. Il
confronto strutturale ha quindi **una colonna sola**, l'as-built. Il pavimento
non e' stato trovato (`pavimento_trovato: false`), coerente con un ritaglio che
comincia sopra di esso.

**Le due suite**, eseguite in questa sessione da
`/Users/mario/GitHub/Tesi/meshrec` sul ramo `feat/fase-5-analisi-strutturale`:

- `uv run pytest tests -q --ignore=tests/feasibility` → **694 passati**, 5
  avvisi, 101,42 s;
- `uv run pytest tests -q -m feasibility` → **11 passati, 1 saltato**, 694
  deselezionati, 4,49 s.

## Il difetto, e la sua correzione

La Fase 4 si era fermata al deck: i controlli verificavano che fosse leggibile e
risolvibile, non che fosse **giusto**. Solo un solutore poteva rendere visibile
quello che segue.

### Il prima

Questi numeri vengono dalla spec di progetto
(`docs/superpowers/specs/2026-08-21-meshrec-fase-5-analisi-strutturale-design.md`,
§§ 3.1-3.4, misurati il 21/08/2026) e **non sono rimisurabili oggi**: il codice
che li produceva non esiste piu'. Sono citati come stato di partenza, non come
misura di questa corsa.

| grandezza | prima |
|---|---|
| scostamento dell'asse altezza dal verticale vero | 22,43° |
| nodi nel set `BASE` | 278 su 14.103, un piede solo, toppa x 337,6-527,1 |
| max \|U\| sotto peso proprio | 15,2544 mm (mediana 9,8556) |
| somma delle reazioni | (34,476; −2004,943; 4858,062) N contro 5.339,8 N di peso |
| `fixed_nset_coverage` | 1,0 — mentre meta' degli appoggi non era vincolata |

La catena: `align_to_axes` sceglieva l'asse altezza con la PCA, e sul ritaglio
completo le zapatas — larghe 700 mm e tutte in basso — la spostavano di 22°.
`build_node_sets` costruiva poi `BASE` come i nodi entro tolleranza dal minimo
di z-**modello**: con il piano inclinato e i due piedi distanti 2,4 m, il
secondo piede finiva un metro piu' in alto e la tolleranza non lo raggiungeva.
Il telaio era incastrato in un angolo. Il docstring di `build_node_sets`
affermava il contrario, e non era mai stato eseguito.

### Il dopo, misurato su questa corsa

| grandezza | dopo | fonte |
|---|---|---|
| asse altezza del modello nel sistema originale | (0, 0, 1) esatto, **0,0000°** | `11_export.transform`, riga 3 della rotazione |
| nodi nel set `BASE` | **3.719**, mondo x da 1630,8 a 4312,3 — **entrambi i piedi** | `11_export.node_sets`, coordinate da `13_solution.vtu` |
| max \|U\| sotto peso proprio | **0,036730 mm** | `13_solve.casi.GRAVITA.u_max` |
| somma delle reazioni | (−1,836e-5; −2,454e-5; **4162,392140**) N | `13_solve.controlli.reazioni.somma` |
| estensione in pianta del vincolo | **0,9943** (x 1,0, y 0,9943) | `11_export.constraint_plan_extent` |

**Fattore 415,3 sullo spostamento massimo** (15,2544 / 0,036730), esattamente
quello che la prova della diagnosi aveva previsto. I 3.719 nodi coincidono con
i 3.719 che la spec aveva ottenuto ricostruendo `BASE` dal verticale vero: la
correzione ha prodotto il set che la diagnosi si aspettava, non uno simile.

**Controprova sulle altre due geometrie**, rimisurata qui dai rispettivi
`metrics.json`: `lab_crop` **0,3912°**, `muro` **0,4513°**. Il calcolo
funzionava li' e cedeva sul ritaglio completo, come la diagnosi affermava.

**Quel che la correzione non ha toccato**, e va detto: `fixed_nset_coverage`
vale ancora **1,0**. Non e' un residuo del difetto — e' la grandezza sbagliata,
come il suo stesso docstring dichiara, e per questo la fase ne ha aggiunta una
nuova (`constraint_plan_extent`) invece di ripararla.

Le quattro invarianti che la correzione **non** doveva muovere, e non ha mosso:
14.103 nodi, 51.913 tetraedri, 0 invertiti, volume 217.728.361,2 mm³, errore
mesh→nuvola 27,5379 mm RMS e 135,6937 di massimo su 10.968 campioni.

## I risultati, per caso di carico

I tre carichi non hanno predefiniti e nessun dato li suggerisce: **li ha
dichiarati l'operatore** e stanno in `lab_telaio.yaml`, blocco `carichi`.
Coefficiente di spinta orizzontale **0,10** sull'asse y; risultante in sommita'
**1200 N** sul set `TOP`; **20 modi**. Non sono valori di norma e non sono
predefiniti del programma.

| caso | u_max [mm] | vm mediana [MPa] | vm p99 [MPa] | vm max [MPa] | max/p99 |
|---|---:|---:|---:|---:|---:|
| GRAVITA | 0,036730 | 0,0544 | 0,2336 | 0,5056 | 2,164 |
| SPINTA_ORIZZONTALE | 0,044611 | 0,0537 | 0,2661 | 0,6763 | 2,542 |
| CARICO_TOP | 0,064273 | 0,0827 | 0,3923 | 0,9811 | 2,501 |

`u_max` e `vm_max` da `13_solve.casi`; mediana e p99 ricalcolati in questa
sessione sui 14.103 valori nodali di `13_solution.vtu` (`VM_GRAVITA`,
`VM_SPINTA_ORIZZONTALE`, `VM_CARICO_TOP`).

**Le cifre di questa tabella, e di quella dei controlli e dei modi, sono i
valori come li scrive il solutore — non la precisione che il dato sostiene.**
Quella e' di **due cifre significative**, e il motivo sta nel punto 4 di
«Cosa questi risultati NON hanno il diritto di affermare»: l'errore geometrico
vale il 14,3% dello spessore in RMS, e σ = F/A. Nel resto del documento, dove
questi numeri sono citati come esiti e non come letture, sono arrotondati a due
cifre.

**Modale**: 20 modi estratti, prima frequenza **21,19324 Hz**, poi 34,34059 /
43,13673 / 91,06687 / 108,4334, fino a 681,9477 Hz
(`13_solve.frequenze_hz`, 20 valori).

## I cinque controlli, e i loro esiti

Tutti e cinque presenti nel dizionario, **tutti e cinque passati**
(`13_solve.controlli`).

| controllo | esito | numero | soglia |
|---|---|---|---|
| **reazioni** — somma = ρVg come vettore | passato | scarto relativo **7,730e-9** | 1e-4 |
| **vincolo_in_pianta** — estensione dell'impronta vincolata | passato | minimo **0,9943** | 0,5 |
| **autovalori** — reali, positivi, nessuno vicino a zero | passato | 1ª **21,19324 Hz**, rapporto 1ª/2ª **0,6171** | — |
| **avvisi** — zero avvisi, zero errori | passato | **0** | 0 |
| **picco** — dove vive il massimo e quanto e' appuntito | passato sui tre casi | **0,0** dei nodi sopra il p99 in banda | 0 |

**Una precisazione sul primo, perche' e' il numero piu' facile da sbagliare
leggendo.** I **4162,39 N** delle reazioni **non sono il peso del modello**. Il
peso e' 217.728.361,2 mm³ × 2,5e-9 t/mm³ × 9810 mm/s² = **5.339,79 N**; ccx
stampa sul set `BASE` solo la parte **trasmessa attraverso la struttura**, al
netto della quota tributaria caricata direttamente sui nodi gia' vincolati.
`solve.py:610` sottrae apposta quella quota da `peso_atteso`, ed e' per questo
che i due valori — 4162,392140 letto e 4162,392149 atteso — coincidono a nove
cifre. La quota tributaria vale **1.177,40 N**, il **22,05%** del peso, alta
perche' molti nodi della soletta ricostruita (§ «Il deficit di volume», punto 4)
appoggiano su `BASE`.

**Sul quinto, dove sta il picco.** In tutti e tre i casi statici il massimo di
von Mises cade sullo **stesso nodo**, a coordinate mondo
(2055,0; −348,3; +1010,3), cioe' al **89,2% dell'altezza** del modello, nella
viga superior — **fuori** dalla banda di vincolo (89,99 mm, il 5% dei 1799,73 mm
di altezza) e **fuori** dal set `TOP` dove il carico e' applicato. Sopra il p99
stanno 142 nodi per caso, e **zero** di essi cade in banda, in nessuno dei tre.
Il picco non si sposta coi carichi: se fosse un artefatto del carico, si
sposterebbe.

Qualificato in questa sessione con la grandezza che la pipeline gia' calcola: degli **8** tetraedri incidenti a quel nodo, il piu' piccolo vale **17,66 mm³** contro
una mediana di **2151,06 mm³** — sotto l'**1%** della distribuzione dei volumi
elementari. E' una scheggia del maglio.

Il § 6e della spec prevedeva di qualificare quell'elemento con `aspect_ratio` e
`min_dihedral_deg`. **La corsa le calcola** — stanno in `metrics.json`,
`10_volume_quality` — ma solo come statistiche d'insieme: il valore **per
elemento** al nodo del picco non c'e'. Usare il volume elementare al loro posto
e' quindi una **scelta**, non un ripiego per indisponibilita': e' l'unica delle
tre grandezze che si ricalcola dal `.vtu` con la stessa definizione della
pipeline, verificata (mediana 2151,06 mm³ qui e in `metrics.json`).

Sul numero del nodo si fa presto a inciampare, ed e' gia' successo: **7132** e'
l'indice base zero nel `.vtu`, **7133** e' il nodo nel deck, e `write_vtu`
scrive i primi. Il docstring di `controlla_picco` chiamava quel nodo 7132 e lo
collocava «circa a meta' altezza del pezzo»; il commit **`eac6366`** l'ha
corretto e oggi il file dice l'89%. La quota misurata qui e' l'**89,2%**, su
`13_solution.vtu` e riscontrata sul deck (`wall_model.inp`, nodo 7133, z locale
1605,70 su 1799,73).

## Cosa questi risultati NON hanno il diritto di affermare

Otto punti, dal § 7 della spec. **Due erano falsi e sono corretti qui col numero
misurato.**

**1. Il confronto ha una colonna sola.** Zero membrature accettate significa
nessun modello parametrico su questa geometria: esiste solo l'as-built. Il
telaio sintetico a quattro membrature e' un banco di prova, non il pezzo, e
metterlo accanto non sarebbe una validazione.

**2. Nessuna armatura.** Calcestruzzo omogeneo, scelta dichiarata. Nessuna
verifica normativa, nessun confronto con `f_ck`. Le tensioni sotto peso proprio
(mediana **0,054** MPa, massimo **0,51** MPa, rimisurate qui) sono piccole
rispetto a qualunque resistenza: dire «verifica soddisfatta» sarebbe promuovere
a esito un carico che non sollecita.

**3. La base e' dove abbiamo tagliato.** `crop_min[2] = -498` sta appena sopra
il pavimento. Dopo la correzione l'incastro prende entrambi i piedi, il che e'
meglio, ma resta un **incastro perfetto su una superficie di taglio** — e ora si
sa in piu' che sotto quel taglio il modello si inventa 45,3 milioni di mm³ di
soletta. `BASE` per giunta non e' una faccia: sono 3.719 nodi distribuiti in z
da −595,4 a −463,4, una **fascia spessa 132 mm**, coerente con la tolleranza di
set di 134,97 mm. Vale la formula di `report.NOTE_NON_GEOMETRICHE`, identica.

**4. L'errore geometrico impedisce i decimali.** 27,5379 mm RMS e 135,6937 mm di
massimo contro uno spessore mediano di 192,0267 mm: **14,3%** e **70,7%**. La
sezione locale e' incerta a quella scala, e σ = F/A. **Nessuna tensione con tre
decimali va letta come tale.**

Il numero e' `mesh_to_cloud`, e la direzione va detta perche' in `metrics.json`
ce n'e' una seconda piu' grande: `cloud_to_mesh` ha RMS **9,4710** e massimo
**737,6946** mm, e `hausdorff` vale lo stesso 737,6946. Non e' il tetto
rilevante qui, per come sono definite le due. `cloud_to_mesh` misura, per
ciascuno dei 4.269.608 punti della nuvola, quanto dista dalla superficie:
penalizza cioe' i punti che la ricostruzione **non copre**, e questa
ricostruzione scarta per costruzione il 5% a densita' piu' bassa
(`density_quantile: 0.05`, 549 vertici tolti) e tiene solo la componente
maggiore (`largest_component_only: true`). `mesh_to_cloud` misura il contrario:
quanto la superficie che il modello **afferma** si scosta dal dato. E' quella
superficie che viene tetraedrizzata e risolta, quindi e' quella il tetto sulle
tensioni. I 737,69 mm restano un numero vero su una domanda diversa —
«quanto della nuvola e' rimasto fuori» — e vanno letti li'.

**5. Il modello pesa meno della meta' del pezzo — ma non e' quel rapporto a
contare.** Volume 217.728.361,2 mm³ contro 477.744.760 mm³ nominali:
**45,57%** (denominatore ricalcolato dalla tavola, 477.744.760 mm³, come
dichiarato in copertina della sezione sul deficit; sui 477.700.000 mm³
dichiarati in tavola verrebbe 45,58%, e la spec cita quest'ultimo). Massa
**0,5443 t** contro **1,1944 t**.

Qui la spec deduceva: «sotto peso proprio le tensioni scalano con la massa»,
e quindi anche le tensioni starebbero al 45,6%. **La deduzione e' falsa su
questa geometria, ed e' la correzione piu' importante della fase.** Il volume
mancante sta **tutto sotto il piano di taglio** — zapatas e viga inferior
interrate — cioe' **fuori dal percorso del carico**: non pesa su nulla. Sopra il
piano di taglio il modello porta **4.229,21 N** contro i **4.019,52-4.572,07 N**
del telaio nominale, cioe' dal **92,5% al 105,2%**, non il 45,6%: **±8% sul
carico**, non un fattore 2,2. Il ±8% riguarda il solo numeratore di σ = F/A;
l'incertezza della sezione (punto 4) e' separata e non e' composta con questa. Lo conferma la posizione del picco: all'89,2% dell'altezza, nella viga
superior, 1,6 m sopra il volume che manca. La scomposizione del deficit sta
nella prima sezione di questo documento.

**6. `TOP` e' un set per tolleranza, e i nodi sono 3.036, non 397.** Il numero
della spec e' falso sulla corsa vera: dopo la correzione della terna i sei set
sono stati rifatti, e `11_export.node_sets` da' `TOP` **3036**, `BASE` 3719,
`FACE_FRONT` 403, `FACE_BACK` 444, `SIDE_LEFT` 1912, `SIDE_RIGHT` 454. Il numero
vero **rafforza** l'avvertenza invece di indebolirla: 3.036 nodi sono il
**21,5%** dei 14.103 del modello, con una tolleranza di set di **134,97 mm**.
`TOP` non e' una faccia, e' una **fascia spessa**. Verificato nel deck: il
`*CLOAD` del passo `CARICO_TOP` ha **3.036 righe**, ciascuna −0,395257 N, somma
esatta −1200,0 N. Il carico si ripartisce **uniformemente per nodo**, quindi si
concentra dove i nodi sono piu' fitti, e su una fascia di 135 mm non e' un
carico in sommita': e' un carico su una calotta.

**7. Abaqus non entra.** Nessuna licenza, nessuna prova. Nulla si afferma su
Abaqus. In piu': i nomi dei passi sono scesi a **commento** (`** NOME PASSO:
GRAVITA`) proprio per tenere CalculiX a zero avvisi — il parametro `NAME=` e le
card `*NODE OUTPUT`/`*ELEMENT OUTPUT` sono dialetto Abaqus che ccx scavalcava in
silenzio.

**8. La scomposizione resta al suo soffitto.** Otto regioni, zero membrature: la
regione da 4,2 milioni di punti e' stata respinta con una dispersione di sezione
di **1,187** contro una soglia di **0,10**. Il sistema non ha consegnato sei
membrature plausibili e sbagliate — ha dichiarato di non averne trovata nessuna,
col numero che l'ha respinta. L'asse mediale e' la via d'aggiornamento
dichiarata; spessore e PCA locale sono gia' stati provati e misurati, chi
riprende non li rifaccia.

## I limiti misurati

Non ipotesi: cose che questa corsa ha trovato.

1. **Zero membrature su sei** (§ «Cosa questi risultati NON hanno il diritto di
   affermare», punto 8). Nessun modello parametrico, nessun
   `*TIE` reale da misurare su questa geometria.
2. **Il pavimento non e' stato trovato** (`pavimento_trovato: false`,
   `pavimento_punti: 0`): il ritaglio comincia sopra di esso, e la ricerca del
   piano non ha piu' punti su cui lavorare.
3. **Il vincolo e' una fascia, non una faccia** — 132 mm di spessore — e sotto
   di essa il solido e' ricostruzione cieca (§ «Cosa questi risultati NON hanno
   il diritto di affermare», punto 3).
4. **Il picco vive su una scheggia del maglio**: il piu' piccolo degli 8 tetraedri
   incidenti vale 17,66 mm³ contro 2151,06 di mediana. Il numero e' del maglio,
   non del pezzo.
5. **Lo stimatore d'errore di CalculiX esce a zero, e non e' utilizzabile
   qui.** Misurato in questa sessione su `13_solution.frd`: **23 blocchi
   `ERROR`**, **324.369 valori**, minimo e massimo entrambi **0,0**. Il deck
   non chiede `ERR` in `*EL FILE` (chiede `S, E`): il blocco esce comunque, e
   comunque a zero. Misurato lo zero; la causa e' un'ipotesi, sotto.
6. **L'errore geometrico vale il 14,3% dello spessore in RMS e il 70,7% al
   massimo** (§ «Cosa questi risultati NON hanno il diritto di affermare»,
   punto 4). E' il tetto sulla precisione di ogni tensione.

## Le ipotesi non verificate, elencate come tali

1. **Che i 324.369 zeri del blocco `ERROR` vengano dai tetraedri lineari.**
   Misurato lo zero, non la causa. Se il modello passasse un giorno a C3D10, e'
   la prima cosa da riprovare.
2. **Che il deficit di volume incida poco sulla prima frequenza** (21,2 Hz).
   L'attesa e' che incida poco, perche' la massa che manca sta al vincolo e non
   partecipa al primo modo. **Non e' stata misurata**: servirebbe una modale su
   un modello col volume interrato, che non esiste.
3. **Che l'assegnazione x/y resti stabile su tutte e tre le geometrie.** Su
   `lab_telaio_v2` e' misurata (0,0000°). Su `lab_crop` (0,3912°) e `muro`
   (0,4513°) i valori vengono da corse **non rigenerate dopo la correzione**: la
   verifica sulle tre geometrie non e' chiusa.
4. **Che il picco sia una singolarita' del maglio e non del carico.** L'indizio
   e' forte — stesso nodo sui tre casi, fuori banda e fuori `TOP`, su una
   scheggia da 17,66 mm³ — ma la qualificazione con `aspect_ratio` e
   `min_dihedral_deg` prevista dal § 6e della spec non e' stata fatta: la corsa
   calcola quelle due solo come statistiche d'insieme, non per l'elemento del
   picco (§ «I cinque controlli, e i loro esiti»).
5. **Che il nominale di tavola sia il riferimento giusto per il deficit.** La
   scansione legge le colonne ~205 x 200 mm contro 172 x 172 di tavola. Se
   l'as-built e' davvero piu' grosso del disegno, la ripartizione del deficit si
   sposta. Serve un rilievo calibrato, che non esiste.
