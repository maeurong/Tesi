# Convergenza di maglio: che cosa la GCI misura, e dove non si può fare

Misurato il 26/08/2026 per chiudere
[#71](https://github.com/maeurong/Tesi/issues/71). ASME V&V chiama la stima
dell'errore di discretizzazione «the largest omission in the verification
process»: senza, ogni numero pubblicato è un numero senza barra d'errore.

Due risultati, e il secondo è un **no**.

## 1. La GCI non è una barra d'errore verso la verità

Verificata sulla mensola, dove la freccia di Gere-Timoshenko si conosce in
forma chiusa, su tre maglie (passo 10 / 14 / 20 mm) e due elementi.

| | C3D4 | C3D10 |
|---|---|---|
| ordine osservato | 1,17 (formale 2) | 5,89 (formale 3) |
| GCI sulla griglia fine | 23,67 % | **0,0015 %** |
| distanza dall'estrapolato | 18,94 % | 0,00116 % |
| **errore vero contro Timoshenko** | 9,31 % | **0,279 %** |

Su **C3D4** la banda contiene l'errore vero (9,31 % dentro 23,67 %), e verrebbe
da concludere che la GCI sia una barra d'errore verso la verità.

**Su C3D10 no.** La GCI dice 0,0015 % e la distanza da Timoshenko è 0,279 %:
**186 volte più grande**, fuori banda.

Non è la stima a sbagliare. La GCI misura la distanza dalla soluzione **a
maglio convergente**, e quella vale davvero 0,00116 % — dentro la banda,
verificato. Il residuo dello 0,279 % **non è discretizzazione**: è **errore di
modello**, la teoria di trave contro l'elasticità tridimensionale.

[#47](https://github.com/maeurong/Tesi/issues/47) lo aveva già visto
dall'altro lato, trovando il C3D10 **fra** Eulero-Bernoulli e Timoshenko,
cioè dove la soluzione esatta del solido deve stare.

**Perché conta in tesi.** Confondere le due sarebbe la confusione fra
*verification* e *validation* che `docs/validazione/README.md` vieta. Su un
elemento che ha già convergiuto, una GCI vicina a zero **non** significa che
il numero sia vicino alla realtà: significa che raffinare ancora non lo
sposterà.

E si vede solo perché il confronto è stato fatto **su due elementi**. Con il
solo C3D4 la conclusione sbagliata — «la GCI copre l'errore vero» — sarebbe
passata.

### La GCI di una grandezza già convergente è rumore, e lo si è misurato

I numeri della tabella sono di macOS arm64. La CI su Linux x86-64 dà, sullo
stesso problema:

| | macOS arm64 | Linux x86-64 |
|---|---|---|
| errore vero contro Timoshenko | 0,279 % | 0,271 % |
| **GCI sulla griglia fine** | **0,0015 %** | **0,0346 %** |
| rapporto fra i due | 186 × | 7,8 × |

L'errore vero è praticamente lo stesso; la **GCI cambia di ventitré volte**.

Non è una contraddizione: su una grandezza già convergente le tre frecce
differiscono per quantità minime, e la GCI che ne discende misura il **rumore
del maglio** invece della discretizzazione. Il maglio dipende dalla
piattaforma ([#66](https://github.com/maeurong/Tesi/issues/66)), quindi quel
rumore anche.

Conseguenza pratica: **una GCI molto piccola non va citata come cifra**, va
letta come «sotto la soglia di rumore di questa serie di griglie». Il fatto
qualitativo — la banda non contiene l'errore vero — regge su entrambe le
piattaforme; il fattore no.

Questa distinzione è arrivata da un **difetto in questo stesso lavoro**: la
prima stesura del test pretendeva un fattore maggiore di dieci, misurato su
una piattaforma sola. Era una soglia decisa dopo aver visto il numero, ed è
caduta al primo giro di CI su Linux.

## 2. Sul telaio la GCI non è ottenibile raffinando il volume

Il secondo passo del ticket era applicarla dove la soluzione non si conosce.
**Non si può**, e le due vie sono entrambe chiuse, misurate.

**Con `nobisect=True`** (l'impostazione della corsa di riferimento) il limite
di volume **non viene applicato**: TetGen non aggiunge punti sul bordo, quindi
è la superficie a fissare la dimensione del maglio.

| h chiesto [mm] | h effettivo [mm] | tetraedri | \|u\|max [mm] |
|---|---|---|---|
| 30,0 | 23,478 | 100 951 | 0,04191172 |
| 42,0 | 27,541 | 62 536 | 0,04191633 |
| 58,8 | 29,178 | 52 588 | 0,04190768 |

Rapporti di raffinamento effettivi: **1,173** e **1,059**, contro il minimo di
**1,3** che Celik et al. (2008) raccomandano. Sotto quel valore la formula
divide per un denominatore che va a zero e misura il rumore del solutore
invece della discretizzazione — e infatti i tre spostamenti differiscono alla
quinta cifra.

Il programma **avvisava già**: `IneffectiveVolumeLimitWarning`, con dentro la
diagnosi esatta e la via d'uscita.

**Con `nobisect=False`** TetGen **fallisce**: `Internal TetGen error within
'recoversubfaces'`, intercettato da `RefinementFailedError`.

**Quindi la manopola vera è la superficie**, non il volume: la profondità
della ricostruzione di Poisson o la semplificazione. Ma girare quella cambia
la **geometria** che si sta magliando, e le tre griglie non sarebbero più lo
stesso solido: la stima confonderebbe errore di discretizzazione ed errore
geometrico, che sono due grandezze diverse e già misurate separatamente.

Questa è una **decisione**, non un'esecuzione, e resta aperta.

## Le risposte alle domande del ticket

**Quale grandezza d'interesse.** Lo **spostamento massimo**: convergenza
monotona su entrambi gli elementi, ordine osservato dentro la banda su
entrambi. Il controesempio che obbliga a sceglierla è NAFEMS **LE10**, dove la
tensione nel punto d'angolo **peggiora raffinando** (Abaqus dichiara 1,15 % →
7,24 % per il proprio C3D10, noi riproduciamo +5,31 % → +7,05 %): lì
Richardson non ha ipotesi, e il modulo lo **dichiara** invece di calcolare.

**Quanti raffinamenti.** Tre: è il minimo per stimare l'ordine osservato
invece di assumerlo. Il registro delle soglie già annota che sotto tre griglie
il fattore di sicurezza sale da 1,25 a 3,0.

**Il criterio d'arresto.** Quello che il metodo ha già: convergenza monotona,
ordine osservato dentro la banda, rapporto di raffinamento ≥ 1,3. **Nessuna
soglia nuova**, e quindi niente da aggiungere a `core/soglie.py` — la GCI è un
numero da **riportare**, non un cancello. Fissare «quanto errore di
discretizzazione è accettabile» sarebbe una decisione di modellazione, non di
verifica.

**Il rapporto `r` da `max_volume`.** Sul telaio **non si ottiene**, misurato
sopra. Sulla mensola sì, perché lì il maglio è generato da una geometria
analitica e non da una superficie ricostruita.

**Dove vive il codice.** `core/convergenza.py`, con 23 test unità a oracoli in
forma chiusa (`tests/test_convergenza.py`) e 4 test di validazione su `ccx`
vero (`tests/validazione/test_convergenza_mensola.py`).

## Note sul metodo

**Il fattore di sicurezza non sta nel modulo**: è
`gci_fattore_sicurezza` = 1,25 in `core/soglie.py` (Roache 1994), e il modulo
lo **riceve**. Una soglia dichiarata in un posto solo.

**L'indice di campo asintotico non vale 1 per il solo fatto che l'ordine sia
giusto**, e leggerlo così porta fuori strada. Misurato su serie di potenza
**esatte** con p = 2: vale 0,786 quando l'errore sulla griglia fine è il 10 %,
0,971 all'1 %, 0,997 allo 0,1 %. Il motivo è che i due errori sono relativi,
normalizzati su valori diversi, che coincidono solo quando l'errore è piccolo.

**Limite dichiarato.** Richardson classico assume griglie **nidificate**.
TetGen non le produce: raffinando si ottiene un maglio nuovo, non una
suddivisione del precedente. La procedura di Celik è formulata proprio per
griglie non strutturate, ma l'ipotesi resta più debole di quella del caso
strutturato.

## Fonti

- Celik, Ghia, Roache, Freitas, Coleman, Raad (2008), «Procedure for Estimation
  and Reporting of Uncertainty Due to Discretization in CFD Applications»,
  *Journal of Fluids Engineering* 130(7):078001 — procedura, equazione
  dell'ordine osservato, raccomandazione `r ≥ 1,3`.
- Roache (1994), *Journal of Fluids Engineering* 116(3):405-413,
  DOI 10.1115/1.2910291 — fattore di sicurezza 1,25 su tre griglie.
