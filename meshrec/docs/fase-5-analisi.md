# Fase 5 — analisi strutturale del telaio as-built

Data di apertura: 21/08/2026. Corsa di riferimento: `runs/lab_telaio_v2`,
rigenerata il 21/08/2026 alle 22:14 sul ramo `feat/fase-5-analisi-strutturale`.
Ogni numero di questo documento e' stato misurato su quella corsa, con il
comando riportato accanto.

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
normale (0,0043, -0,0039, 1,0000), **549.792 punti interni, z fra -520,5 e
-499,5**. Il § 8 di `docs/fase-4-prior-telaio.md` aveva misurato -522,5 / -498,5
sulla stessa nuvola: le due letture concordano entro 1 mm, la differenza e'
l'estrazione casuale di RANSAC.

**Conseguenza, e va letta al contrario di come suona:** il piano di taglio a
-498 sta **0,5-1,5 mm sopra il punto piu' alto del pavimento**. Il ritaglio non
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

### 6. Verifica con lo spessore: l'assottigliamento non e' uniforme

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
nominale, dal 2,4% al 7,5%, mai piu' sottile. **Sopra il piano di taglio
l'assottigliamento di Poisson non e' misurabile su questa geometria.** Cio'
che manca al modello non e' spalmato sulle pareti: e' un pezzo intero che sta
sotto il taglio.

### 7. Conseguenza strutturale

**Il peso proprio del modello e' 5.339,79 N**, da 217.728.361,2 mm³ x
2,5e-9 t/mm³ x 9810 mm/s². Il telaio nominale pesa **11.716,69 N**. Il rapporto
delle masse e' 0,4558.

Prima una precisazione che serve a non sbagliare il numero: i **4.162,39 N** che
la corsa riporta in `13_solve.controlli.reazioni` **non sono il peso**. Sono la
reazione trasmessa attraverso la struttura al set `BASE`, al netto della quota
tributaria caricata direttamente sui nodi vincolati, che `solve.py:608`
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
manda nelle colonne, non il 45,6%. Sulla tensione assiale media nelle colonne
l'errore e' dell'ordine del ±8%, non di un fattore 2,2.

Lo conferma la posizione del picco. Il massimo di von Mises sotto gravita' vale
**0,5056 MPa** e cade a z = **+1010,3 mm**, cioe' nella viga superior, 1.606 mm
sopra il punto piu' basso del modello — **non alla base**. Il volume mancante
sta 1,5 m piu' in basso e non lo tocca. Le tensioni delle altre due condizioni:
SPINTA_ORIZZONTALE **0,6763 MPa**, CARICO_TOP **0,9811 MPa**
(`13_solve.casi`).

Quel che il volume mancante toglia davvero e' un'altra cosa, e va detta come
limite, non come numero: **il set `BASE` di questo modello non e' la faccia
inferiore di una zapata, e' la sezione di taglio a filo pavimento.** Il modello
e' incastrato dove finisce il dato. Manca quindi ogni effetto della fondazione
— diffusione della tensione nel plinto, cedevolezza rotazionale dell'appoggio —
e il modello e' alla base piu' rigido del telaio vero. Sulla prima frequenza
(21,193 Hz, `13_solve.frequenze_hz`) l'effetto e' presumibilmente piccolo,
perche' la massa che manca sta al vincolo e non partecipa al primo modo, ma
**questa e' un'attesa, non una misura**: non e' stata verificata.

### 8. Come rimisurare tutto questo

Le misure di questa sezione non stanno nel programma: `src/` non contiene, e non
deve contenere, alcun numero del provino. Sono state prodotte da uno script una
tantum, fuori dal repository, che rilegge `runs/lab_telaio_v2/01_cloud.ply`,
`02_segmented.ply`, `09_volume.vtu`, `13_solution.vtu`, `wall_model.inp`,
`metrics.json` e `12_wall.json` con `open3d`, `meshio` e `scipy.spatial`.
Chi rifa' il conto rifa' lo script: tre righe di prodotto misto per il volume,
un clipping contro il piano per la ripartizione, un istogramma in z per le
quote.
