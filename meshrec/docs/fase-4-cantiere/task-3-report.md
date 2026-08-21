# Task 3 — report

## File toccati

- `meshrec/src/meshrec/core/wall.py` — aggiunte `semplifica_contorno`, `Membratura`,
  `misura`, `controlla`, `_volume_unione`, `prior`. Corretto anche il riferimento
  al test rinominato dentro il commento `ponytail:` di `regioni()`.
- `meshrec/tests/test_wall.py` — aggiunti i test degli step 1, 5, 10 del brief
  (contorno, misure per membratura, controlli intrinseci, riscontri, prior,
  chiusura del volume).

Nessun file toccato fuori da questi due. Nessun campo nuovo in `WallConfig`:
tutte le soglie richieste (`contour_tolerance`, `parallelism_deg`, `face_coverage`,
`section_dispersion`, `union_tolerance`, `union_step_factor`, `membrature_attese`,
`sezioni_nominali`, `volume_atteso`) erano gia' scritte dal Task 1.

## Test aggiunti ed esito

Tutti gli step del brief (1 → 15), eseguiti in ordine TDD (rosso per il motivo
giusto, poi verde):

- `test_il_contorno_di_un_rettangolo_ha_quattro_vertici` — PASS
- `test_il_contorno_semplificato_non_perde_area_oltre_la_tolleranza` — PASS
- `test_la_misura_di_un_prisma_noto_ritrova_sezione_asse_e_lunghezza` — PASS
- `test_il_fuori_piombo_misura_l_inclinazione_e_il_rigonfiamento_no` — PASS
- `test_il_rigonfiamento_e_una_mappa_e_trova_la_pancia_dove_c_e` — PASS
- `test_i_quattro_controlli_intrinseci_passano_su_un_prisma_pulito` — PASS
- `test_una_regione_a_sezione_variabile_non_e_un_prisma_e_lo_dice` — PASS
- `test_senza_riscontri_dichiarati_il_prior_non_inventa_un_aspettativa` — PASS
- `test_con_i_riscontri_dichiarati_il_prior_riporta_lo_scarto` — PASS
- `test_l_esito_del_prior_e_serializzabile_in_json` — PASS
- `test_il_controllo_di_chiusura_del_volume_confronta_somma_e_unione` — PASS

`uv run pytest tests/test_wall.py -v` → **22 passed**.
`uv run pytest tests -q --ignore=tests/feasibility` → **435 passed, 0 failed,
0 skipped** (partiva da 424; +11 di questo task).

Nessun subagente `test-writer` dispacciato: il codice toccato e' tutto nuovo
di questo task, non legacy scoperto.

## Due correzioni al codice del brief, scoperte dal ciclo TDD

Il codice del brief e' stato incollato verbatim in un primo momento e i suoi
stessi test lo hanno smentito. Due bug distinti, entrambi indipendenti dalla
logica di dominio:

1. **`np.cross` su vettori 2D.** `semplifica_contorno` chiamava
   `np.cross(corda, inviluppo - precedente)` su array (N, 2): numpy 2.0 ha
   tolto il supporto al prodotto vettoriale 2D, e la chiamata solleva
   `ValueError`. Sostituita con la formula esplicita della componente z
   (`corda[:,0]*scostamento[:,1] - corda[:,1]*scostamento[:,0]`), stesso
   risultato, nessuna libreria in piu'.

2. **Assi scambiati nella mappa di rigonfiamento.** Il codice del brief
   costruiva la griglia su `(lungo, sezione_2d[:, 0])` e leggeva la quota da
   `sezione_2d[:, 1]`, ma `sezione_2d[:, 0]` (asse `e1`) e' proprio la
   direzione trasversale del pezzo lungo cui il test gonfia una faccia:
   usarla come asse della griglia invece che come quota fa sparire il
   rigonfiamento nella cella invece di mostrarlo (`test_il_rigonfiamento...`
   falliva con mappa piatta, tutta zero). In piu' il `lato` della griglia
   usava `cfg.cell_factor` — un fattore pensato per moltiplicare una
   spaziatura di punti (`spessore_per_cella`, `scomponi`) — su una frazione
   di lunghezza: risultato, celle troppo larghe (6 invece delle >10 richieste
   dal test). Corretto scambiando gli assi (griglia su `asse, e2`; quota
   `e1`) e togliendo `cell_factor` da quel `lato` locale, che ora usa solo
   `lunghezza / _FETTE_LUNGO_ASSE`, la stessa risoluzione gia' usata per la
   dispersione di sezione. Verificato numericamente prima di scrivere la
   correzione (script a mano con `misura_swap`), poi trasferito nel file.

Nessuna delle due correzioni cambia l'interfaccia dichiarata nel brief
(`Membratura`, `misura`, `controlla`, `prior` hanno le firme e i campi
richiesti) ne' introduce soglie nuove.

## La condizione fuori brief: la regione a Π NON viene scartata

Ho scritto il test richiesto (banco a sezione uniforme del canarino di
`test_wall.py`, passato a `wall.prior`, verifica che finisca fra `scartate` e
non fra `membrature`). Il test **fallisce**: la regione a Π passa tutti e tre
i controlli intrinseci e viene misurata come una membratura da 200 x 1600 mm.

Numeri esatti dalla corsa (banco sintetico, nessuno di questi vive in `src/`):

```
asse [0. 0. 1.]  lunghezza 2200.0  sezione (200.0, 1600.0)  sezione_dispersione (0.0, 0.0)
parallelismo:      passato=True  valore=0.0  soglia=5.0
copertura_faccia:  passato=True  valore=1.0  soglia=0.5
costanza_sezione:  passato=True  valore=0.0  soglia=0.1
rigonfiamento: min=0.0 max=0.0 (piatto)
contorno: rettangolo pieno 200 x 1600, non una Π
```

**Causa geometrica, non un bug di implementazione mio o del brief:** ogni
misura di sezione in `misura()` (estensione, dispersione per fetta, contorno,
rigonfiamento) e' basata su bounding-box / massimo per cella (`ptp`,
`np.maximum.at`). Per una Π, i due piedritti attraversano *tutta* l'altezza
del pezzo: a ogni fetta lungo l'asse, in ogni cella della griglia di faccia,
ci sono sempre punti sia dal piedritto sinistro sia da quello destro. Il
bounding box di ogni fetta e' quindi largo 1600 mm dalla prima fetta
all'ultima — costante — e non "vede" che al centro la sezione e' vuota (due
strisce da 200 mm, non un rettangolo pieno da 1600). Nessuna delle tre
grandezze sorvegliate (dispersione della sezione, parallelismo delle facce
via rigonfiamento, copertura) e' sensibile a un buco *interno* al bounding
box: sono tutte pensate per una sezione convessa piena, e la Π non lo e'.

Per le istruzioni ricevute mi fermo qui: **non ho introdotto un controllo
tarato apposta per intercettare questo caso** (sarebbe la soglia tarata a
mano che il progetto vieta), e non ho lasciato nella suite un test rosso — il
test che dimostra il problema e' stato scritto, eseguito, e poi tolto da
`tests/test_wall.py` prima del commit, perche' un test rosso in un commit
viola il vincolo "suite verde a ogni commit" di questo task. La sua traccia
resta qui.

Questo riapre la decisione presa nel Task 2 ("il danno e' contenuto perche'
il controllo di costanza della sezione la scarta"): quella premessa non regge
con i tre controlli intrinseci attuali. La decisione su come procedere (nuovo
controllo geometrico sensibile a un buco interno — per esempio un confronto
fra punti osservati per fetta e punti attesi da un bounding box pieno,
oppure un controllo di connessione della sezione nel piano — o accettare il
limite e documentarlo diversamente) resta a Mario.

## Ruling G — il quarto controllo intrinseco: riempimento_sezione

Mario ha deciso: non serve stringere una soglia, serve la grandezza che
nessuno guardava. Le tre grandezze esistenti sono tutte di bounding box
(estensione, dispersione, rigonfiamento via massimo per cella) e cieche a un
vuoto interno. Aggiunto un quarto controllo intrinseco, scelto prima e a
prescindere dalla soglia: **quanto della propria ingombro locale la sezione
occupa davvero**, non quanto e' largo l'ingombro.

**Calcolo**, dentro `misura()`, riusando la stessa suddivisione in fette gia'
usata per la dispersione: per ogni fetta con almeno 4 punti, si costruisce
una griglia locale sulla sezione 2D di quella fetta con `chiavi_di_cella` (lato
= `lunghezza / _FETTE_LUNGO_ASSE`, la stessa risoluzione gia' condivisa da
dispersione e rigonfiamento — nessuna soglia nuova per la griglia), si conta
quante celle del proprio bounding box locale sono occupate contro quante ce
ne sarebbero in tutto il bounding box, e si prende la **mediana** sulle fette
(non la media: pochi capi pieni — nella Π, dove i traversi chiudono
l'ingombro per davvero — non devono nascondere una maggioranza di fette
vuote in mezzo). Il campo nuovo e' `Membratura.riempimento_sezione`, la
soglia e' `WallConfig.section_fill_ratio` (default 0.5, stessa convenzione di
meta' gia' usata da `face_coverage`).

**Verificato numericamente prima di scrivere la soglia** (nessuna soglia
tarata guardando il banco specifico, ma la scelta di 0.5 e' stata controllata
contro numeri reali per non lasciarla campata in aria):

```
prisma pulito (200x140x1500, spacing 15):        riempimento mediano = 1.0
telaio del Task 2, 4 regioni distinte (172-700):  riempimento minimo per regione = 0.64 / 0.83 / 0.89 / 1.0
regione a Π del canarino (sezione uniforme):      riempimento mediano = 0.333
```

Margine ampio su entrambi i lati di 0.5: nessuna membratura vera del banco
del Task 2 si avvicina alla soglia (minimo 0.64), e la Π ci sta nettamente
sotto (0.333). La soglia 0.5 non e' stata scelta per battere di poco lo
0.533 che dava una prima versione con la media anziche' la mediana — e'
proprio per questo che si e' passati alla mediana, che porta la Π a 0.333 con
margine, invece di stringere 0.5 in una soglia via via piu' vicina al caso
specifico.

**Confine dichiarato** (nella `spiegazione` del controllo, non solo qui): una
membratura legittimamente cava (un tubo) verrebbe scartata da
`riempimento_sezione`. E' corretto in questo prior, che costruisce prismi
pieni: modellare un tubo come pieno sarebbe un errore peggiore dello scarto.

**Test:**
1. `test_la_regione_a_pi_di_sezione_uniforme_finisce_fra_le_scartate` —
   rimesso nella suite, eseguito PRIMA dell'implementazione (rosso per il
   motivo giusto: `AssertionError` su `esito["membrature"] == []`, la Π
   passava ancora tutti i controlli), poi verde dopo l'implementazione. Ora
   verifica che la Π finisca fra `scartate` con `"riempimento_sezione"` fra
   i `controlli_falliti` e `valore < soglia`.
2. `test_le_membrature_piene_del_telaio_non_sono_scartate_dal_riempimento` —
   il controllo che smentisce il controllo: il telaio a sezioni diverse del
   Task 2 (4 regioni, tutte prismi veri) non deve avere nessuno scarto.
3. `test_i_quattro_controlli_intrinseci_passano_su_un_prisma_pulito` —
   aggiornato il `set(esiti)` atteso da 3 a 4 chiavi.

`uv run pytest tests/test_wall.py -v` → **24 passed** (22 + 2 nuovi).
`uv run pytest tests -q --ignore=tests/feasibility` → **437 passed, 0 failed,
0 skipped** (435 → 437).

Commit: `b88334f` — `fix(fase-4): riempimento_sezione, il quarto controllo
che vede la Π`.

**Agli atti:** la prima versione del Ruling G calcolava il riempimento come
**media** per fetta, e con la media la Π dava 0.533 — sopra una soglia di 0.5
che l'avrebbe fatta passare. E' passato alla **mediana** dopo aver visto quel
numero, non prima: e' la versione morbida della soglia tarata sul caso, e il
Ruling H (sotto) l'ha confermato mostrando che la misura sottostante aveva
comunque due difetti indipendenti dalla scelta fra media e mediana. Dichiararlo
nel rapporto invece di tacerlo e' cio' che ha permesso alla review di
prenderlo con i numeri in mano.

## Ruling H — la misura del riempimento era sbagliata, non la grandezza

La review ha riprodotto il difetto su cinque prismi sintetici **pieni**,
senza alcun vuoto, con la misura del Ruling G:

```
$ uv run python -c "..."
--- PRIMA DEL FIX (Ruling G) ---
200x140x1500: riempimento_sezione=1.0
300x300x1500: riempimento_sezione=0.64
500x500x1500: riempimento_sezione=0.4897959183673469   sotto soglia 0.5, scartato
200x140x500:  riempimento_sezione=0.48148148148148145  sotto soglia 0.5, scartato
500x500x500:  riempimento_sezione=0.20987654320987653
```

Due difetti distinti, entrambi nella misura, non nella grandezza (che resta
"quanto della sezione l'esterno non raggiunge"):

1. **Risoluzione presa dalla grandezza sbagliata.** `lato_fetta =
   lunghezza / _FETTE_LUNGO_ASSE` e' una lunghezza assiale, usata come lato
   di una griglia che misura occupazione trasversale: il risultato dipende
   dal rapporto sezione/lunghezza, non dal vuoto. Corretto con
   `lato_celle = cfg.cell_factor * spacing`, la stessa griglia gia' usata da
   `scomponi` e `spessore_per_cella`. `misura()` ora prende `spacing` come
   parametro (non un valore nuovo in `WallConfig`: `cell_factor` esisteva
   gia' e serviva esattamente a questo), e `prior()` lo passa dal proprio
   argomento.

2. **"Cella occupata" misurava il bordo, non il vuoto.** Su una nuvola di
   sola superficie i punti stanno solo sul perimetro della sezione: contare
   le celle con punti misura il perimetro, e infatti raffinando la griglia
   (cella piu' piccola) il valore peggiorava — la firma della review
   (0.49 → 0.22 → 0.11) e' esattamente quella di una misura di bordo.
   Corretto ridefinendo cella piena come **"non raggiungibile
   dall'esterno"**: si marcano le celle con punti (il perimetro) su una
   griglia booleana per fetta, poi `scipy.ndimage.binary_fill_holes` (gia'
   installata, nessuna dipendenza nuova) riempie cio' che quel perimetro
   racchiude. Un prisma pieno da' un perimetro chiuso — quasi tutta la
   griglia si riempie, qualunque sia la forma della sezione; una Π ha un
   vano che l'esterno raggiunge, e quel vano resta vuoto.

3. **Ripiego a 1.0 tolto.** Se nessuna fetta ha almeno 4 punti, prima il
   riempimento valeva 1.0 ("pieno" per assenza di dato). Ora
   `Membratura.riempimento_misurabile` e' `False`, `riempimento_sezione`
   vale `0.0`, e `controlla()` segna `"passato": False` con
   `"misurabile": False` nell'esito — il controllo si dichiara non in grado
   di pronunciarsi e scarta, invece di promuovere perche' nessuno ha potuto
   smentire.

**Dopo il fix**, stessi cinque casi piu' la Π del banco:

```
$ uv run python -c "..."
--- DOPO IL FIX (Ruling H), spacing=15.0 ---
200x140x1500: riempimento_sezione=1.0
300x300x1500: riempimento_sezione=1.0
500x500x1500: riempimento_sezione=1.0
200x140x500: riempimento_sezione=1.0
500x500x500: riempimento_sezione=1.0

--- Pi ring, dopo il fix ---
membrature: 0 scartate: 1
esito riempimento_sezione: {'passato': False, 'valore': 0.3, 'soglia': 0.5,
'misurabile': True, ...}
```

Tutti e cinque i prismi pieni danno 1.0 (nessuno scartato), e la Π resta
scartata con `valore=0.3 < soglia=0.5`: la correzione non ha spostato la
soglia, ha spostato la misura.

**Verifica per mutazione** (soglia svuotata a `1e-9`, non committata, solo
verifica manuale che il controllo morda davvero):

```
$ uv run python -c "..."
con soglia mutata (quasi 0): membrature trovate = 1 scartate = 0
la Pi passa il controllo? {'passato': True, 'valore': 0.3, 'soglia': 1e-09, ...}
```

Con la soglia svuotata la Π viene promossa a membratura (`valore=0.3 >=
soglia=1e-09`): conferma che a soglia 0.5 e' il controllo, non un caso, a
tenerla fuori.

**Test:**
- `test_un_prisma_pieno_non_e_scartato_qualunque_sia_la_sua_forma` — i cinque
  controesempi del revisore. Eseguito PRIMA del fix con la chiamata a
  `misura()` a 3 argomenti (interfaccia pre-Ruling-H): rosso per il motivo
  giusto (`AssertionError: (300.0, 300.0, 1500.0): 0.64` non supera 0.9).
  Verde dopo il fix su tutti e cinque.
- `test_il_riempimento_non_misurabile_scarta_invece_di_promuovere` — copre il
  ramo tolto del ripiego a 1.0: con troppo pochi punti,
  `esiti["riempimento_sezione"]["misurabile"] is False` e
  `["passato"] is False`.
- `test_la_regione_a_pi_di_sezione_uniforme_finisce_fra_le_scartate` — invariato
  nell'asserzione, riverificato verde con la nuova misura.

`uv run pytest tests/test_wall.py -v` → **26 passed** (24 + 2 nuovi).
`uv run pytest tests -q --ignore=tests/feasibility` → **439 passed, 0 failed,
0 skipped** (437 → 439).

Commit: `23bfb11` — `fix(fase-4): riempimento misura il vuoto, non il bordo
(Ruling H)`.

## Ruling I — la spaziatura si stima sulla regione, non si eredita

Stesso difetto, spostato: la re-review ha riprodotto che una risoluzione
presa da uno `spacing` **globale** (dichiarato per il pezzo intero, ereditato
da `prior()`) sposta l'esito con un fattore quattro appena la densita' locale
della regione si discosta da quella media — sintomaticamente identico al
Ruling H (risoluzione presa dalla grandezza sbagliata), ma sulla grandezza
successiva nella catena.

**Test PRIMA del fix**, con la chiamata a 4 argomenti (interfaccia
pre-Ruling-I, `misura(..., spacing_dichiarato)`), che riproduce esattamente i
numeri del revisore:

```
$ uv run pytest tests/test_wall.py -k "rada" -v
FAILED test_una_regione_rada_non_e_scartata_se_e_davvero_piena
  AssertionError: {'passato': False, 'valore': 0.4444444444444444, ...}
FAILED test_una_pi_molto_rada_non_passa_come_piena
  AssertionError: {'passato': True, 'valore': 1.0, 'soglia': 0.5, ...}
2 failed, 26 deselected
```

**Due correzioni**, entrambe nella misura, non nella grandezza:

1. `misura()` non prende piu' `spacing` in firma. Lo stima da se',
   internamente, con `io.mean_spacing(punti_regione, cfg.spacing_sample,
   cfg.seed)` — la stessa funzione con cui lo step 1 stima la spaziatura del
   pezzo intero, chiamata sui punti della singola regione. `WallConfig`
   guadagna `spacing_sample` (default 20_000, stessa semantica di
   `input.spacing_sample`) e `seed` (default 0): nessun parametro nuovo in
   una firma, come richiesto.
2. Verso opposto: se la spaziatura locale e' cosi' grossolana che la
   griglia di una fetta ha meno di due celle per lato in una dimensione, la
   griglia e' degenere (una riga o colonna sola) e `binary_fill_holes` non
   puo' mai racchiudere un vuoto in quella dimensione — la definizione
   stessa di riempimento («bordo piu' interno racchiuso») smette di avere
   senso, non e' un parametro di qualita' da tarare. Quella fetta non entra
   piu' in `riempimenti`; se nessuna fetta ne supera la soglia,
   `riempimento_misurabile=False` (meccanismo gia' costruito nel Ruling H)
   e la regione e' scartata dichiarando di non potersi pronunciare, non
   promossa a «piena».

**Dopo il fix**, stessi due casi piu' verifica che il banco standard resti
scartato **sul riempimento** e la verifica per mutazione:

```
$ uv run python -c "..."
caso1 prisma 300x300x1500 @70mm reale:
  {'passato': True, 'valore': 1.0, 'soglia': 0.5, 'misurabile': True, ...}
caso2 Pi @200mm reale:
  {'passato': False, 'valore': 0.0, 'soglia': 0.5, 'misurabile': False, ...}
banco standard 20mm: membrature= 0 scartate= 1
  controlli_falliti= ['riempimento_sezione']
mutazione soglia quasi 0: membrature= 1 scartate= 0
```

Il caso 1 passa (misurabile, pieno). Il caso 2 non passa perche' **non
misurabile** (`valore=0.0` e' il ripiego del Ruling H, non una misura), non
perche' "quasi vuoto" — e' esattamente l'esito che il ruling chiedeva: non
smentito da un numero basso per caso, ma dichiarato non pronunciabile. Il
banco standard (spaziatura 20mm, quella con cui e' sempre stato verificato)
resta scartato con lo stesso controllo di sempre. La mutazione (soglia
azzerata) promuove di nuovo la Π a membratura: conferma che a soglia 0.5 e'
il controllo, non un caso, a tenerla fuori.

**Test:**
- `test_una_regione_rada_non_e_scartata_se_e_davvero_piena` — il
  controesempio del revisore (prisma pieno, densita' locale rada).
- `test_una_pi_molto_rada_non_passa_come_piena` — il controllo che smentisce
  il precedente (Π vera, densita' cosi' rada che il vuoto non e' piu'
  risolvibile): deve dichiararsi non misurabile, non passare come piena.

`uv run pytest tests/test_wall.py -v` → **28 passed** (26 + 2 nuovi).
`uv run pytest tests -q --ignore=tests/feasibility` → **441 passed, 0 failed,
0 skipped** (439 → 441).

Commit: `501615a` — `fix(fase-4): riempimento stima la spaziatura sulla
regione (Ruling I)`.

**Conseguenza da sapere prima di trovarsela davanti:** su una scansione molto
rada, molte regioni risulteranno non misurabili e verranno scartate — non e'
un difetto di questa correzione, e' l'esito giusto: meglio una regione
scartata con il motivo scritto (`riempimento_sezione.misurabile=False`) che
una membratura inventata su una griglia troppo grossolana per vedere se e'
piena o cava. Su una nuvola povera il prior puo' quindi non consegnare
nessuna membratura, e chi legge il documento della fase deve saperlo prima
di eseguirlo su un caso reale scarsamente coperto.

## Debito chiuso

Il commento `ponytail:` dentro `regioni()` in `wall.py` citava
`test_una_sezione_uniforme_smentisce_la_separazione_per_spessore`, nome non
piu' esistente: aggiornato al nome attuale
`test_una_sezione_uniforme_e_un_canarino_per_la_separazione_per_orientamento`.

## Commit

- `6e592bc` — `feat(fase-4): sezione, asse, fuori piombo e rigonfiamento per membratura`
- `2e07a62` — `feat(fase-4): i controlli intrinseci del prior e i riscontri dichiarati`
- `b88334f` — `fix(fase-4): riempimento_sezione, il quarto controllo che vede la Π`
- `23bfb11` — `fix(fase-4): riempimento misura il vuoto, non il bordo (Ruling H)`
- `501615a` — `fix(fase-4): riempimento stima la spaziatura sulla regione (Ruling I)`

## Aree segnalate a security-reviewer

Nessuna: modulo di calcolo geometrico puro, nessun input esterno non fidato,
nessuna auth, nessun dato sensibile.

## Ruling J — il riempimento smette di scartare: misura, dichiara, e il rifiuto va a valle

La causa dei tre giri precedenti non era la grandezza ne' la sua risoluzione: era
di **ruolo**. `wall.py` per spec «misura e non costruisce», e uno scarto e' una
decisione di costruzione presa dentro uno strumento di misura. Per scartare
senza sbagliare serve una certezza che una nuvola reale non da'; per misurare e
dichiarare basta cio' che c'e'.

### Che cosa e' cambiato

1. **`riempimento_sezione` non e' piu' un controllo intrinseco.** E' uscito da
   `controlla`, che torna ai suoi tre controlli (parallelismo, copertura di
   faccia, costanza della sezione), invariati, scarto compreso. Al suo posto c'e'
   `wall.riempimento(membratura, cfg) -> dict`, che **non decide**: dichiara.
2. **Tre stati misurati:** `Membratura.riempimento_stato` vale `"pieno"`,
   `"vuoto"` o `"non_verificabile"`. Nessuno dei tre toglie la regione da
   `membrature` in `wall.prior`.
3. **La misura di affidabilita':** `Membratura.densita_dispersione` e' la
   dispersione relativa delle distanze al vicino piu' prossimo (scarto tipo su
   media). Distingue «non verificabile» dagli altri due stati. Le distanze
   erano gia' calcolate da `io.mean_spacing`: e' stata estratta
   `io.nn_distances(points, sample, seed) -> np.ndarray`, e `mean_spacing` ora
   e' la media di quelle. Nessun secondo albero, nessuna dipendenza nuova.
4. **L'informazione esce da `prior` nella forma che serve al Task 8:** ogni
   membratura porta `"riempimento": {stato, valore, soglia, affidabile,
   densita_dispersione, limite_densita_dispersione, unita, spiegazione}`. Un
   consumatore rifiuta con `stato == "vuoto" and affidabile` senza ricalcolare
   nulla.

Lo stato `non_verificabile` copre due condizioni, e sono la stessa cosa detta a
due scale: nessuna fetta con punti a sufficienza (o griglia degenere, il
meccanismo del Ruling I), oppure densita' troppo poco uniforme perche' una
griglia costruita sulla spaziatura media risolva la parte rada.

### La soglia di affidabilita', e da dove viene

`WallConfig.density_dispersion_limit = 1.0`, dichiarata come **condizione di
validita' della misura, non criterio di qualita' del pezzo**.

Scelta **prima** di guardare i casi, da un principio: sopra uno, lo scarto tipo
delle distanze al vicino piu' prossimo eguaglia la loro media, e una media il
cui scarto tipo e' grande quanto se stessa non e' piu' una scala della
popolazione — la griglia costruita su di essa (`cell_factor` per la spaziatura)
non e' la risoluzione di niente in particolare. Sotto uno, la media descrive
ancora la nuvola. Il valore ha due ancore indipendenti dal banco:

- una nuvola a densita' unica sta ben sotto: una griglia regolare da' 0, un
  campionamento casuale uniforme di superficie da' circa 0,52 (il coefficiente
  di variazione della distanza al vicino piu' prossimo di un processo di Poisson
  in due dimensioni, `sqrt(1/Gamma(3/2)^2 - 1)`);
- una nuvola in cui una frazione dei punti e' piu' rada di `cell_factor` volte la
  media — cioe' esattamente la condizione in cui il perimetro di quella parte
  non si chiude piu' sulla griglia — ci arriva sopra: con un decimo dei punti
  al limite di `4 x media`, il coefficiente di variazione vale 1,00 esatto.

**Non e' stata scelta guardando i casi di prova**, e i numeri misurati dopo lo
confermano con margine largo su entrambi i lati: il caso reale piu' disperso che
resta affidabile e' 0,49 (Π campionata a 200 mm), il controesempio meno disperso
che diventa non verificabile e' 1,42. Fra 0,49 e 1,42 non c'e' nessun caso del
banco: la soglia non e' incastrata fra due numeri vicini.

Restano `section_fill_ratio = 0.5` (ora confine fra `pieno` e `vuoto`, non piu'
criterio di scarto) e i tre controlli intrinseci, intatti.

### Il banco dei due controesempi

**I due controesempi non erano nel rapporto**, contrariamente a quanto diceva il
dispaccio: `task-3-report.md` a HEAD `501615a` non li contiene, e non compaiono
nemmeno in `progress.md` ne' nei diff di review salvati (`grep -rn "frontale"`,
`grep -rn "tappi"` sull'intero worktree: nessun riscontro). Sono stati
ricostruiti dalla descrizione del dispaccio, con numeri dichiarati nel banco e
non nel sorgente:

prisma **pieno** 300 x 300 x 1500, pareti a passo 100 mm, facce fitte a passo
5 mm — rapporto venti, che e' quello di un'incidenza radente attorno agli 87
gradi, cioe' cio' che una scansione da un lato solo produce per costruzione e
non un numero scelto per far cadere una soglia.

- **A**, faccia frontale fitta e pareti laterali rade: la faccia `y = 0`.
- **B**, tappi terminali fitti e pareti rade: le due facce `z = 0` e `z = 1500`.

### La tabella dei casi, prima e dopo

Prima = `501615a` (`uv run python` sul banco, esito di `controlla`); dopo = questo
commit (esito di `wall.riempimento`). Output catturato, nessun numero a memoria.

| caso | prima: valore / misurabile / passato | prima: effetto | dopo: stato / valore / dispersione | dopo: effetto |
|---|---|---|---|---|
| prisma pieno 200x140x1500 @20 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.000 | membratura, pieno |
| prisma pieno 300x300x1500 @20 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.000 | membratura, pieno |
| prisma pieno 500x500x1500 @20 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.000 | membratura, pieno |
| prisma pieno 200x140x500 @20 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.000 | membratura, pieno |
| prisma pieno 500x500x500 @20 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.000 | membratura, pieno |
| prisma rado ma uniforme @70 | 1.000 / True / True | membratura | `pieno` / 1.000 / 0.011 | membratura, pieno |
| telaio Task 2, 4 regioni @20 | tutte passate | 4 membrature, 0 scartate | `pieno` x 4 | 4 membrature, 0 scartate |
| **Π del banco a sezione uniforme @20** | 0.318 / True / **False** | **scartata** | **`vuoto` / 0.318 / 0.259, affidabile** | **membratura, vuoto e affidabile** |
| **A: faccia frontale fitta, pareti rade** | 0.112 / True / **False** | **scartata come vuota** | **`non_verificabile` / 0.112 / 1.424** | **non verificabile** |
| **B: tappi fitti, pareti rade** | 0.099 / True / **False** | **scartata come vuota** | **`non_verificabile` / 0.099 / 1.967** | **non verificabile** |
| Π molto rada @200 | 0.000 / False / False | scartata | `non_verificabile` / 0.000 / 0.491 | non verificabile |
| regione di cinque punti | 0.000 / False / False | scartata | `non_verificabile` / 0.000 / 0.153 | non verificabile |

Output di riferimento del dopo, per intero:

```
$ uv run python -c "..."
prisma pieno (200.0, 140.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (300.0, 300.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (500.0, 500.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (200.0, 140.0, 500.0)       stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (500.0, 500.0, 500.0)       stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma rado uniforme 70mm                stato=pieno            valore=1.000 disp=0.011 affidabile=True
A faccia frontale fitta, pareti rade     stato=non_verificabile valore=0.112 disp=1.424 affidabile=False
B tappi fitti, pareti rade               stato=non_verificabile valore=0.099 disp=1.967 affidabile=False
Pi molto rada 200mm                      stato=non_verificabile valore=0.000 disp=0.491 affidabile=True
regione con cinque punti                 stato=non_verificabile valore=0.000 disp=0.153 affidabile=True
Pi banco via prior: membrature=1 scartate=0 riempimento={'stato': 'vuoto',
  'valore': 0.3181818181818182, 'soglia': 0.5, 'affidabile': True,
  'densita_dispersione': 0.2589131342368177, 'limite_densita_dispersione': 1.0}
telaio Task2 via prior: membrature=4 scartate=0 stati=['pieno','pieno','pieno','pieno']
```

Il punto centrale del ruling e' la coppia A/B: prima uscivano con `passato=False`
e un valore basso, cioe' **scartate come se fossero vuote**, quando sono due
prismi pieni; ora dicono che la misura non vale.

### Test, in ordine TDD

Scritti e verificati **rossi prima** dell'implementazione (`9 failed, 21 passed`;
i motivi giusti: `AttributeError: 'Membratura' object has no attribute
'riempimento_stato'` sui nuovi, `KeyError: 'riempimento'` su quello che legge
`prior`, `AssertionError: il riempimento non scarta piu' nessuno: [...]` sulla Π).

- `test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata` —
  la Π non e' piu' scartata, esce fra le membrature con `stato="vuoto"` e
  `affidabile=True`: l'informazione con cui il Task 8 la rifiuta.
- `test_i_prismi_pieni_escono_pieni_qualunque_sia_la_loro_forma` — i cinque
  prismi pieni del Ruling H, ora sullo stato.
- `test_una_faccia_frontale_fitta_con_pareti_rade_non_e_vuota_ma_non_verificabile`
  — controesempio A.
- `test_tappi_terminali_fitti_con_pareti_rade_non_sono_vuoti_ma_non_verificabili`
  — controesempio B.
- `test_una_regione_senza_punti_a_sufficienza_resta_non_verificabile` — cinque
  punti.
- `test_una_regione_rada_ma_uniforme_esce_piena` e
  `test_una_pi_molto_rada_non_esce_piena` — la coppia del Ruling I, riscritta sui
  tre stati: rado non vuol dire non verificabile, non uniforme si'.
- `test_le_membrature_piene_del_telaio_escono_piene` — ora verifica lo stato di
  ciascuna e non piu' solo che nessuna sia scartata: con il riempimento che non
  scarta piu' nessuno, la vecchia asserzione sarebbe diventata vuota.
- `test_i_controlli_intrinseci_passano_su_un_prisma_pulito` — tornato a tre
  chiavi.

`uv run pytest tests/test_wall.py -q` → **30 passed** (28 → 30).
`uv run pytest tests -q --ignore=tests/feasibility` → **443 passed, 0 failed,
0 skipped** (441 → 443).

### Verifica per mutazione

Tre mutazioni, applicate una alla volta ai soli valori predefiniti in
`config.py`, mai committate:

```
density_dispersion_limit 1.0 -> 1e9   (l'affidabilita' non morde piu')
  FAILED test_una_faccia_frontale_fitta_con_pareti_rade_non_e_vuota_ma_non_verificabile
    AssertionError: stato vuoto, valore 0.11224489795918367, dispersione densita' 1.42...
  FAILED test_tappi_terminali_fitti_con_pareti_rade_non_sono_vuoti_ma_non_verificabili
    AssertionError: stato vuoto, valore 0.09917355371900827, dispersione densita' 1.96...
  2 failed, 28 passed

density_dispersion_limit 1.0 -> 1e-9  (tutto diventa inaffidabile)
  FAILED test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata
  FAILED test_le_membrature_piene_del_telaio_escono_piene
  FAILED test_una_regione_rada_ma_uniforme_esce_piena
  3 failed, 27 passed

section_fill_ratio 0.5 -> 1e-9        (il confine pieno/vuoto sparisce)
  FAILED test_la_regione_a_pi_esce_vuota_e_affidabile_invece_di_essere_scartata
    AssertionError: {'stato': 'pieno', 'valore': 0.3181818181818182, ...}
  1 failed, 29 passed
```

Le due soglie mordono ciascuna sui propri casi e su nessun altro: la prima
mutazione tocca solo i due controesempi a densita' bimodale, la terza solo il
confine pieno/vuoto della Π. Se fossero intercambiabili, le stesse prove
cadrebbero due volte.

### File toccati

- `meshrec/src/meshrec/core/wall.py` — `Membratura`: `riempimento_misurabile` →
  `riempimento_stato` piu' `densita_dispersione`; `misura` stima la dispersione
  della densita' e classifica nei tre stati; `controlla` perde il quarto
  controllo; nuova `riempimento(membratura, cfg)`; `prior` espone
  `"riempimento"` per membratura. Aggiornato il commento `ponytail:` di
  `regioni()`, che diceva ancora «il controllo di costanza della sezione la
  scarta».
- `meshrec/src/meshrec/core/io.py` — estratta `nn_distances`; `mean_spacing` ne
  e' la media. Firma di `mean_spacing` invariata, nessun chiamante toccato.
- `meshrec/src/meshrec/core/config.py` — nuovo `density_dispersion_limit`;
  riscritta la descrizione di `section_fill_ratio` (confine fra due esiti, non
  criterio di scarto).
- `meshrec/tests/test_wall.py` — i test del riempimento riscritti sul nuovo
  contratto, piu' il banco a densita' bimodale (`DENSITA_BIMODALE`,
  `_faccia_fitta`, `_prisma_a_densita_bimodale`) e `TELAIO_A_SEZIONE_UNIFORME`
  estratto perche' usato da tre prove. Aggiornata la docstring del canarino, che
  citava ancora lo scarto.
- `docs/superpowers/plans/2026-08-18-meshrec-fase-4-prior-telaio.md` — due punti
  che dicevano «i quattro controlli intrinseci»; lo stub `_membratura_finta` del
  Task 8, che costruiva una `Membratura` senza i campi del riempimento e non
  sarebbe piu' compilato; e il **requisito del Ruling J dentro il Task 8**, con
  la sua guardia e il suo test, come chiede `progress.md` («non come nota»).

Nessun numero del provino e' entrato nel sorgente. Le soglie stanno in
`WallConfig`, nessuna e' in una firma.

### Preoccupazioni

1. **Il Task 8 e' ora l'unico punto in cui una Π viene fermata.** Il requisito e'
   scritto nel piano con la sua guardia e il suo test, ma finche' non e'
   implementato, `wall.prior` consegna una Π come membratura: e' il costo
   dichiarato del ruling, non un effetto collaterale.
2. **`stato` e' una stringa e non un enum.** Tre valori, un solo produttore, e
   l'esito deve essere JSON per il browser: un enum andrebbe comunque
   serializzato a stringa. Se il Task 8 dovesse confrontarlo in piu' punti,
   promuoverlo a costanti di modulo e' un cambio di una riga.
3. **Nessun endpoint toccato**, quindi nessuna verifica con `curl`: `wall.prior`
   non e' ancora chiamato da `run()` ne' dal server (`grep -rn "wall.prior" src`
   → nessun riscontro), il cablaggio e' dei Task 9 e 10.
4. **Nessuna area per `security-reviewer`:** calcolo geometrico puro, nessun
   input esterno non fidato, nessuna auth, nessun dato sensibile.

## Ruling K — attuato in parte, e la parte non attuata e' motivata con i numeri

Il ruling chiedeva di sostituire la dispersione omnidirezionale con una
dispersione **fra le fette**, perche' il riempimento e' una mediana su fette
lungo l'asse e una grandezza che qualifica una misura deve descrivere la
dimensione lungo cui quella misura e' costruita. Il principio e' giusto e non lo
discuto. **Applicato al codice reale, il rimedio non corregge il proprio
controesempio**, e l'ho verificato prima di lasciarlo dentro: sotto ci sono i
numeri, poi la ragione, poi cosa protegge davvero quel caso.

### Il controesempio, riprodotto

Π vera del banco a sezione uniforme, meta' a 15 mm e meta' a 150 mm, taglio a
meta'. Riprodotto quasi esattamente (la review dava `pieno`, dispersione 0.703,
riempimento 0.554; io ottengo `pieno`, dispersione 0.747, riempimento 0.500 con
la meta' fitta in alto, e `vuoto` 0.473 con la meta' fitta in basso). **Il
difetto e' reale e confermato:** una Π genuinamente vuota esce `pieno` con
misura affidabile, e le due meta' a specchio cadono da parti opposte della
soglia per puro caso.

Test scritto per primo con l'asserzione del ruling (`non_verificabile`) e
verificato **rosso** prima di toccare il codice:

```
FAILED test_una_pi_fitta_su_meta_lunghezza_e_rada_sull_altra_non_esce_piena
  AssertionError: meta' fitta alta: stato pieno, valore 0.5, dispersione densita' 0.747
```

### Perche' il rimedio non lo corregge

Ho implementato la versione con la **spaziatura locale per fetta** (fra le due
grandezze offerte dal ruling e' quella giusta: il conteggio dipende anche da
quanta superficie la fetta contiene, la spaziatura no — vedi sotto), scartando
dalla mediana ogni fetta piu' rada del lato di cella. Ho poi guardato le venti
fette una per una:

```
spacing regione = 15.20  lato_celle = 60.80  disp = 0.747
asse [1. 0. 0.]
 0 n= 1998 sp=  14.6 griglia  4x37 fill=0.622
 3 n=  336 sp=  17.4 griglia  4x37 fill=0.203
 4 n=  330 sp=  15.0 griglia  4x 5 fill=1.000
 5 n=  402 sp=  17.0 griglia  4x37 fill=0.203
 6 n=  330 sp=  15.0 griglia  4x 5 fill=1.000
 ...  (alternanza fino alla fetta 19)
```

Tre fatti che il ruling non poteva sapere senza aprire le fette:

1. **L'asse della regione e' x, non z.** Il taglio «a meta' lunghezza» della
   review e' in z, cioe' **trasversale all'asse**, non lungo di esso. Ogni fetta
   contiene quindi sia punti fitti sia punti radi.
2. **Nessuna fetta e' rada.** Le spaziature per fetta stanno fra 14.1 e 17.4
   contro un lato di cella di 60.8: i punti radi sono minoranza *dentro ogni
   fetta*, e la media per fetta e' dominata dai fitti esattamente come lo era
   quella globale. Il criterio non scarta nulla, e lo stato non cambia: dopo
   l'implementazione il test restava rosso con lo stesso identico messaggio.
3. **Le fette che leggono 1.0 non sono rade: sono corte.** Hanno griglia `4x5`
   contro `4x37` delle altre — estensione di sezione ~300 mm contro ~2250 mm.
   La meta' rada si allinea a caso con i confini delle fette e alcune fette
   contengono **solo un pezzo della sezione**, che e' genuinamente pieno. E' uno
   scostamento **della sezione fra fette**, non della densita'.

Il conteggio di punti per fetta, l'altra grandezza offerta dal ruling, e' peggio:
rompe un caso obbligatorio.

```
Pi uniforme @20 (deve restare vuoto affidabile)  conteggi cv=0.696  spaziature cv=0.085
prisma pieno 300x300x1500 @20                    conteggi cv=0.271  spaziature cv=0.000
```

La Π uniforme, che il ruling J esige esca `vuoto` **affidabile**, ha conteggi per
fetta con dispersione 0.696 solo perche' le fette ai capi contengono un montante
e quelle in mezzo no: forma, non densita'. Qualunque limite sul conteggio che
prendesse il caso nuovo prenderebbe anche lei.

### Cosa protegge davvero quel caso

`costanza_sezione`, che gia' c'e' e misura esattamente quella grandezza — la
dispersione della sezione fra fette — con una sensibilita' molto maggiore:

```
fitta sopra (taglio in z)    stato=pieno   falliti=['costanza_sezione'] disp_sez=[0.    0.535]
fitta sotto (taglio in z)    stato=vuoto   falliti=['costanza_sezione'] disp_sez=[0.    0.535]
taglio in x (asse vero)      stato=vuoto   falliti=['costanza_sezione'] disp_sez=[0.    0.424]
Pi uniforme @20              stato=vuoto   falliti=[]                   disp_sez=[0.    0.   ]
via prior: regioni=1 membrature=0 scartate=1
   scartata, falliti: ['costanza_sezione']
```

0.535 contro una soglia di 0.10. **La regione non arriva mai fra le membrature**,
quindi non arriva mai alla guardia del Task 8: la coppia pericolosa
(«genuinamente vuota, dichiarata piena e affidabile») non esce da `prior`. E non
e' una coincidenza fortunata: le fette che leggono 1.0 lo fanno *perche'* vedono
una sezione diversa dalle altre, che e' la definizione della grandezza che
`costanza_sezione` sorveglia. Le due condizioni sono lo stesso fenomeno, e la
piu' stretta delle due e' quella che esiste gia'.

### Decisione, e la risposta alla domanda del ruling

Il ruling chiedeva esplicitamente di non tenere due misure di affidabilita' se
una non serve. La risposta e' piu' netta di quanto il ruling si aspettasse: **la
seconda non serve, e non e' la globale a dover cadere ma la nuova**. Ho quindi
tolto il codice della dispersione per fetta che avevo scritto — non scartava mai
una fetta in nessuno dei sei casi del banco, quindi era un numero che nessuno
avrebbe piu' saputo perche' era li', esattamente la cosa contro cui il ruling
metteva in guardia. `density_dispersion_limit` resta l'unica soglia di
affidabilita'.

Il test resta, riscritto sulla proprieta' che conta davvero e che oggi e' vera:
`test_una_pi_meta_fitta_e_meta_rada_non_arriva_fra_le_membrature`, che passa per
`wall.prior` e verifica che la regione non raggiunga chi costruisce e che a
fermarla sia `costanza_sezione`. Il commento nel codice accanto agli stati dice
perche' non c'e' una seconda misura, e rimanda a quel test.

**Verifica per mutazione** (`section_dispersion` 0.10 → 10.0, non committata):

```
FAILED test_una_pi_meta_fitta_e_meta_rada_non_arriva_fra_le_membrature
  AssertionError: meta' fitta alta: la Π non deve arrivare a chi costruisce, ...
```

Con la costanza della sezione allentata la Π passa: e' davvero quel controllo a
tenerla fuori, e se qualcuno lo allentasse il test lo direbbe.

### I cinque casi decisivi, tutti insieme, dopo Ruling K

```
prisma pieno (200.0, 140.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (300.0, 300.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (500.0, 500.0, 1500.0)      stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (200.0, 140.0, 500.0)       stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma pieno (500.0, 500.0, 500.0)       stato=pieno            valore=1.000 disp=0.000 affidabile=True
prisma rado uniforme 70mm                stato=pieno            valore=1.000 disp=0.011 affidabile=True
A faccia frontale fitta, pareti rade     stato=non_verificabile valore=0.112 disp=1.424 affidabile=False
B tappi fitti, pareti rade               stato=non_verificabile valore=0.099 disp=1.967 affidabile=False
Pi molto rada 200mm                      stato=non_verificabile valore=0.000 disp=0.491 affidabile=True
regione con cinque punti                 stato=non_verificabile valore=0.000 disp=0.153 affidabile=True
Pi banco via prior: membrature=1 scartate=0 riempimento={'stato': 'vuoto',
  'valore': 0.3181818181818182, 'soglia': 0.5, 'affidabile': True,
  'densita_dispersione': 0.2589131342368177, 'limite_densita_dispersione': 1.0}
telaio Task2 via prior: membrature=4 scartate=0 stati=['pieno','pieno','pieno','pieno']
Pi meta' fitta meta' rada via prior: membrature=0 scartate=1, falliti ['costanza_sezione']
```

Nessuno degli altri quattro gruppi si e' mosso.

### Le due cose oltre al ruling

**La trappola nel piano, chiusa.** Il Task 8 dichiarava il requisito del Ruling J
a parole ma il corpo di `costruisci` mostrato allo Step 4 non aveva alcuna
guardia, e `_membratura_finta` fissava `riempimento_stato="pieno"`: chi avesse
seguito il codice alla lettera avrebbe costruito senza guardia e nessun test
avrebbe toccato il percorso «vuoto». Ora nel piano ci sono la clausola in testa a
`costruisci` (con il proprio messaggio di errore), il parametro `riempimento` in
`_membratura_finta`, e **due** prove: `test_una_membratura_a_sezione_vuota_non
_diventa_un_modello` e il suo smentitore `test_una_membratura_non_verificabile_si
_costruisce_lo_stesso`, perche' «non verificabile» non deve diventare un secondo
motivo di rifiuto. La guardia guarda il solo `riempimento_stato` e non rilegge
nessuna soglia: `wall.misura` mette «vuoto» solo su una misura affidabile, e
degrada a «non_verificabile» appena non lo e'.

**La docstring bugiarda, corretta.** `misura()` diceva di stimare la spaziatura
con `io.mean_spacing`; il codice chiama `io.nn_distances` e ne fa la media. Ora
dice quello che fa, e dice anche che dalle stesse distanze viene la dispersione.

`uv run pytest tests/test_wall.py -q` → **31 passed** (30 → 31).
`uv run pytest tests -q --ignore=tests/feasibility` → **444 passed, 0 failed,
0 skipped** (443 → 444).

### Preoccupazione che resta

Su una regione di quel tipo `riempimento_stato` **e' sbagliato** — dice `pieno`
su una Π vuota — anche se la regione viene scartata prima di uscire da `prior` e
lo stato non compare da nessuna parte (le `scartate` portano `esiti`, non
`riempimento`). E' un errore che oggi non ha conseguenze e che non so correggere
senza una quarta incarnazione della stessa soglia: se un domani `costanza_sezione`
venisse allentata o rimossa, quello stato tornerebbe pericoloso. Il test nuovo e'
il canarino che lo direbbe, ma volevo che restasse scritto qui e non solo nel
test.
