# Intervallo dei parametri meccanici del calcestruzzo — telaio di laboratorio, classe non dichiarata

Ricerca esterna svolta il **26/08/2026**. Serve a quantificare l'assunzione
dell'operatore sui materiali per un'analisi di sensibilità, da confrontare con
l'errore geometrico della ricostruzione.

Convenzione (la stessa di `mensola-benzley.md`): **[V]** = stampato nella fonte
citata, letto in questa sessione. **[I]** = inferito o calcolato, con il conto
che lo sostiene accanto. Nessun numero **[I]** va citato in tesi come dato di norma.

Unità di lavoro del progetto: **mm / N / MPa / t**. Con questa terna la gravità
vale `g = 9806,65 mm/s^2` e la densità di massa va in `t/mm^3`.

---

## 0. Sintesi operativa

| Parametro | Estremo inferiore | Valore centrale | Estremo superiore | Base |
|---|---|---|---|---|
| `E` [MPa] | 29 962 (C20/25) | 32 837 (C30/37) | 35 220 (C40/50) | classi plausibili, aggregato quarzitico |
| `E` [MPa] con incertezza sull'aggregato | 20 973 | — | 42 264 | come sopra x 0,70 e x 1,20 (EC2 3.1.3(2)) |
| `rho` [t/mm^3] | 2,40e-9 | 2,55e-9 | 2,60e-9 | EN 206 normal-weight / NTC Tab. 3.1.I |
| `nu` [-] | 0,14 | 0,20 | 0,26 | fib MC2010 5.1.7.3 |

Tutti i numeri sono giustificati sotto. La riga «con incertezza sull'aggregato»
è la più onesta se la tavola non dichiara nemmeno la litologia degli inerti.

---

## 1. Modulo elastico E

### 1.1 Eurocodice 2 — EN 1992-1-1:2004

Fonte letta: PDF di **BS EN 1992-1-1:2004 (E)** recuperato il 26/08/2026 da
<https://www.phd.eng.br/wp-content/uploads/2015/12/en.1992.1.1.2004.pdf>
(scansione OCR; le cifre della Tabella 3.1 sono leggibili, il testo ha refusi OCR
che non toccano i numeri).

**3.1.3(2)** [V], testuale:

«Approximate values for the modulus of elasticity Ecm, secant value between
sigma_c = 0 and 0,4 fcm, for concretes with quartzite aggregates, are given in
Table 3.1. For limestone and sandstone aggregates the value should be reduced
by 10% and 30% respectively. For basalt aggregates the value should be increased
by 20%.»

**3.1.3(1)** [V]:

«The elastic deformations of concrete largely depend on its composition
(especially the aggregates). The values given in this Standard should be
regarded as indicative for general applications. However, they should be
specifically assessed if the structure is likely to be sensitive to deviations
from these general values.»

Questa è la frase che *autorizza* l'analisi di sensibilità: la norma stessa
dichiara i propri valori indicativi.

Relazione analitica in Tabella 3.1 [V]: `Ecm = 22 [(fcm)/10]^0,3` con `Ecm` in
**GPa** e `fcm` in MPa; `fcm = fck + 8 MPa`. In MPa la stessa formula si scrive
`Ecm = 22000 (fcm/10)^0,3`.

Riga `Ecm` della Tabella 3.1, in **GPa** [V] (arrotondata dalla norma):

| classe | C12/15 | C16/20 | C20/25 | C25/30 | C30/37 | C35/45 | C40/50 | C45/55 | C50/60 | C55/67 | C60/75 | C70/85 | C80/95 | C90/105 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fck [MPa] | 12 | 16 | 20 | 25 | 30 | 35 | 40 | 45 | 50 | 55 | 60 | 70 | 80 | 90 |
| Ecm [GPa] | 27 | 29 | 30 | 31 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 41 | 42 | 44 |

Valori non arrotondati in **MPa**, ricalcolati dalla formula [I]
(`22000*((fck+8)/10)**0.3`, Python 3, 26/08/2026):

| classe | fck | fcm | Ecm [MPa] |
|---|---|---|---|
| C12/15 | 12 | 20 | 27 085 |
| C16/20 | 16 | 24 | 28 608 |
| C20/25 | 20 | 28 | 29 962 |
| C25/30 | 25 | 33 | 31 476 |
| C28/35 | 28 | 36 | 32 308 |
| C30/37 | 30 | 38 | 32 837 |
| C32/40 | 32 | 40 | 33 346 |
| C35/45 | 35 | 43 | 34 077 |
| C40/50 | 40 | 48 | 35 220 |
| C45/55 | 45 | 53 | 36 283 |
| C50/60 | 50 | 58 | 37 278 |
| C90/105 | 90 | 98 | 43 631 |

Gli stessi valori non arrotondati sono tabulati anche in
<https://eurocodeapplied.com/design/en1992/concrete-design-properties> (fonte
secondaria, usata solo come controprova: coincide cifra per cifra).

### 1.2 NTC 2018 — italiane

Fonte letta: testo del **DM 17/01/2018**, Supplemento ordinario n. 8 alla
Gazzetta Ufficiale, Serie generale n. 42 del 20-02-2018, capitoli 3, 4, 7, 11,
PDF recuperati il 26/08/2026 da `studiopetrillo.com/files/ntc2018/` (ristampa
integrale del testo GU: ogni pagina porta l'intestazione «20-2-2018 Supplemento
ordinario n. 8 alla GAZZETTA UFFICIALE Serie generale - n. 42» e la numerazione
di pagina della GU).

**11.2.10.3 MODULO ELASTICO** [V], testuale:

«Per modulo elastico istantaneo del calcestruzzo va assunto quello secante tra
la tensione nulla e 0,40 fcm, determinato sulla base di apposite prove, da
eseguirsi secondo la norma UNI EN 12390-13:2013. In sede di progettazione si
può assumere il valore: Ecm = 22.000 [fcm/10]^0,3 [N/mm2] (11.2.5) che dovrà
essere ridotto del 20% in caso di utilizzo di aggregati grossi di riciclo nei
limiti previsti dalla Tab. 11.2.III. Tale formula non è applicabile ai
calcestruzzi maturati a vapore. Essa non è da considerarsi vincolante
nell'interpretazione dei controlli sperimentali delle strutture.»

**11.2.10.1** [V]: `fck = 0,83 · Rck` (11.2.1) e `fcm = fck + 8 [N/mm2]` (11.2.2).

**Differenza con l'Eurocodice: nessuna sulla formula.** La (11.2.5) delle NTC e
la relazione di Tabella 3.1 di EN 1992-1-1 sono la stessa espressione, scritta
una in N/mm^2 e l'altra in GPa. Le differenze sono ai margini:

- NTC prescrive la riduzione del **20%** per aggregati grossi di riciclo e
  l'inapplicabilità ai calcestruzzi maturati a vapore [V, 11.2.10.3]; EC2 non ha
  queste due clausole.
- EC2 prescrive le correzioni per **litologia** dell'aggregato (-10% calcare,
  -30% arenaria, +20% basalto) [V, 3.1.3(2)]; NTC non le riporta, ma il 11.2.10
  rinvia esplicitamente alla Sezione 3 di UNI EN 1992-1-1:2005 «per quanto non
  previsto» [V].

**Classi previste, Tab. 4.1.I «Classi di resistenza»** [V]:
C8/10, C12/15, C16/20, C20/25, C25/30, C30/37, C35/45, C40/50, C45/55, C50/60,
C55/67, C60/75, C70/85, C80/95, C90/105. Subito dopo [V]: «Oltre alle classi di
resistenza riportate in Tab. 4.1.I si possono prendere in considerazione le
classi di resistenza già in uso **C28/35 e C32/40**».

Nota: **C8/10 esiste nelle NTC e non in EN 1992-1-1**, dove Tabella 3.1 parte da
C12/15.

### 1.3 Quali classi sono realistiche per questo provino, e quali si escludono

Vincoli **normativi** [V], tutti dalle NTC 2018:

- **Tab. 4.1.II, Impiego delle diverse classi di resistenza**: «Per strutture
  semplicemente armate: **C16/20**» classe di resistenza minima. Sotto C16/20 si
  esce dall'ambito del calcestruzzo armato ordinario.
- **7.4.2.1 CONGLOMERATO**: «Non è ammesso l'uso di conglomerati di classe
  inferiore a **C20/25** (v. 4.1) o LC20/22.» Vale per le costruzioni di
  calcestruzzo in zona sismica. Un telaio di prova sismica ricade qui.
- **4.1** [V]: «Per le classi di resistenza superiori a **C45/55**, la resistenza
  caratteristica e tutte le grandezze meccaniche e fisiche che hanno influenza
  sulla resistenza e durabilità del conglomerato devono essere accertate prima
  dell'inizio dei lavori tramite un'apposita sperimentazione preventiva e la
  produzione deve seguire specifiche procedure per il controllo di qualità.»
  Sopra C45/55 il progetto non può più tacere la classe: servono prove preventive
  documentate. Un elaborato che non dichiara nulla è quindi incompatibile con un
  calcestruzzo ad alta resistenza.
- **4.1** [V]: «Per classi di resistenza superiore a C70/85 si rinvia al caso C)
  del 11.1» (materiali non normati, autorizzazione del Servizio Tecnico Centrale).

**Quello che si può escludere, e su che base** [I, con la clausola normativa
citata sopra a sostegno di ciascuna riga]:

- C8/10 e C12/15: escluse, sotto il minimo di Tab. 4.1.II per struttura armata.
- C16/20: esclusa se il telaio è progettato per prova sismica (7.4.2.1);
  ammissibile se la prova è statica.
- oltre C45/55 (C50/60 fino a C90/105): escluse in pratica, la loro adozione
  presuppone una qualificazione preventiva documentata che una tavola muta
  contraddice.
- **restano C20/25 fino a C45/55**, cioè Ecm da **29 962** a **36 283 MPa**.

Restringere ulteriormente non è possibile con fonti pubblicate: **non ho trovato
nessuna statistica pubblicata sulla classe di calcestruzzo dei provini di telaio
in c.a. di laboratorio**. Le campagne sperimentali dichiarano la propria classe
caso per caso (esempi trovati: target 20 / 25 / 30 MPa su cilindri 100x200; C20,
C25, C40; C30/37 su cilindri 150x300) ma non esiste una distribuzione di
riferimento citabile. Chi volesse un intervallo più stretto lo sta supponendo,
non lo sta leggendo.

**Raccomandazione (non decisione):** usare **C20/25 fino a C40/50**, cioè
**29 962 fino a 35 220 MPa**, centrata su C30/37 = **32 837 MPa**. Il taglio a
C40/50 invece che a C45/55 è una scelta di comodo (C45/55 è già il gradino su cui
scatta la sperimentazione preventiva); se si preferisce l'estremo normativo puro,
l'estremo superiore è 36 283 MPa. **Va dichiarato quale dei due si è preso.**

### 1.4 L'incertezza che non dipende dalla classe

L'aggregato pesa quanto e più della classe. EC2 3.1.3(2) [V]: da arenaria (-30%)
a basalto (+20%), a parità di classe, il fattore va da **0,70 a 1,20**, cioè un
rapporto **1,71** tra i due estremi. Confronto: da C20/25 a C45/55 il rapporto su
Ecm è solo **1,21**.

Stessa struttura nel fib Model Code 2010, 5.1.7.2:
`Eci = Eco · alpha_E · (fcm/fcmo)^(1/3)` con `Eco = 2,15e4 MPa`, `fcmo = 10 MPa`,
`alpha_E = 1,0` per aggregato quarzitico (fonte: manuale DIANA FEA 12.1.2,
<https://manuals.dianafea.com/d101/MatLib/node194.html>, che riproduce MC2010:
**fonte secondaria**, MC2010 non è liberamente consultabile).

Se la tavola non dichiara nemmeno la litologia dell'inerte, l'intervallo onesto è
il prodotto dei due: **0,70 x 29 962 = 20 973 MPa** fino a
**1,20 x 35 220 = 42 264 MPa** [I, moltiplicazione diretta].

### 1.5 Se il provino non è europeo

La tavola è in spagnolo («obra 0021», novembre 2021, ing. José A. Barros
Cabezas). Se il laboratorio non è italiano, il codice di riferimento potrebbe non
essere l'Eurocodice. **Caveat esplicito, non risolto in questa ricerca.** Due
riferimenti alternativi, verificati solo per esistenza della formula:

- **ACI 318**, 19.2.2.1: `Ec = 4700 sqrt(f'c)` MPa per calcestruzzo di peso
  normale. Con `f'c = 28 MPa` dà 24 870 MPa, cioè circa **17% sotto** l'Ecm
  eurocodice della stessa classe. La differenza non è trascurabile e va
  dichiarata se si adotta ACI. **[non verificato su testo ACI primario: ACI 318
  non è liberamente consultabile; formula confermata solo su fonti secondarie]**
- **NEC-15 / NEC-SE-HM** (Ecuador) usa una formula con la radice cubica del
  modulo dell'aggregato Ea, dichiaratamente calibrata sugli inerti locali perché
  la formula ACI sovrastimava. **[non verificato su testo NEC primario]**

Se la provenienza del provino conta per la tesi, va accertata prima di fissare
l'intervallo.

### 1.6 Il quadro NTC per «materiale non dichiarato»

C'è una risposta normativa italiana diretta alla domanda «quanto costa non sapere
il materiale»: i **fattori di confidenza** della Circolare 21/01/2019 n. 7
(Istruzioni NTC 2018), C8.5.4 [V, letto da
`studiopetrillo.com/files/ntc2018/circolare-ntc2018-cap8.pdf`, 26/08/2026]:

«I fattori di confidenza sono utilizzati per la riduzione dei valori dei
parametri meccanici dei materiali e devono essere intesi come indicatori del
livello di approfondimento raggiunto.»

- **LC1** (rilievo geometrico completo, indagini limitate sui dettagli, prove
  limitate sui materiali): **FC = 1,35** [V]
- **LC2** (indagini e prove estese): **FC = 1,2** [V]
- **LC3** (indagini e prove esaustive): **FC = 1** [V]

Caveat: il Capitolo 8 riguarda le **costruzioni esistenti**, non un provino di
laboratorio; e FC riduce le resistenze, non il modulo. Ma il numero **1,35** è il
metro con cui la norma italiana misura la stessa ignoranza che qui si vuole
quantificare, ed è citabile come ordine di grandezza atteso.

---

## 2. Densità rho

### 2.1 Valore nominale

**NTC 2018, Tab. 3.1.I, Pesi dell'unità di volume dei principali materiali** [V]:

| materiale | peso unità di volume [kN/m^3] |
|---|---|
| Calcestruzzo ordinario | 24,0 |
| **Calcestruzzo armato (e/o precompresso)** | **25,0** |
| Calcestruzzi «leggeri»: da determinarsi caso per caso | 14,0 ÷ 20,0 |
| Calcestruzzi «pesanti»: da determinarsi caso per caso | 28,0 ÷ 50,0 |

Identico in **EN 1991-1-1:2002, Tabella A.1**: calcestruzzo di peso normale
24,0 kN/m^3, con le note «Increase by 1 kN/m3 for normal percentage of
reinforcing and pre-stressing steel» e «Increase by 1 kN/m3 for unhardened
concrete», cioè 25,0 kN/m^3 per il c.a. **[non verificato su testo EN 1991-1-1
primario: i PDF trovati non erano estraibili; concordanza su più fonti secondarie
e coincidenza esatta con la Tab. 3.1.I NTC]**

Attenzione: **25,0 kN/m^3 è un peso specifico, non una densità.** La conversione
richiede g.

### 2.2 In unità di lavoro (t/mm^3)

`25,0 kN/m^3 = 2,5e-5 N/mm^3`. Con `g = 9806,65 mm/s^2`:

`rho = 2,5e-5 / 9806,65 = 2,5493e-9 t/mm^3` [I, divisione diretta]

cioè **2 549 kg/m^3**. Il valore da manuale 2500 kg/m^3 = 2,50e-9 t/mm^3
restituisce 24,5 kN/m^3, non 25,0: **scegliere quale delle due grandezze si vuole
riprodurre esattamente, e dichiararlo.**

### 2.3 Intervallo

Base normativa: **EN 206:2013** definisce il calcestruzzo di peso normale come
quello con densità in condizione essiccata in stufa **maggiore di 2000 kg/m^3 e
non superiore a 2600 kg/m^3** (leggero: 800-2000; pesante: oltre 2600).
**[non verificato su testo EN 206 primario, non liberamente consultabile;
riportato concordemente da The Concrete Society,
<https://www.concrete.org.uk/fingertips/normal-weight-concrete/>]**

- intervallo normativo pieno «peso normale»: **2,0e-9 fino a 2,6e-9 t/mm^3**
- intervallo utile per **c.a. ordinario** [I]: **2,40e-9 fino a 2,60e-9 t/mm^3**
  (2400-2600 kg/m^3), centrato su 2,55e-9. L'estremo inferiore 2,0e-9 è
  formalmente ammesso da EN 206 ma appartiene a calcestruzzi al limite del
  leggero, non a un telaio armato di prova.

La densità è il parametro **meno incerto dei tre**: ampiezza relativa circa
piu/meno 4% attorno al centro, contro circa 8% di E sulle sole classi e 30% di nu.

---

## 3. Coefficiente di Poisson nu

### 3.1 Cosa prescrivono le norme: un valore, non un intervallo

**EN 1992-1-1, 3.1.3(4)** [V], testuale:

«Poisson's ratio may be taken equal to 0,2 for uncracked concrete and 0 for
cracked concrete.»

**NTC 2018, 11.2.10.4 COEFFICIENTE DI POISSON** [V], testuale:

«Per il coefficiente di Poisson può adottarsi, a seconda dello stato di
sollecitazione, un valore compreso tra 0 (calcestruzzo fessurato) e 0,2
(calcestruzzo non fessurato).»

Le NTC formulano come «intervallo 0 ÷ 0,2» quello che EC2 formula come due valori
discreti, ma è la **stessa** prescrizione: 0,2 e 0 sono i due stati (integro /
fessurato), **non** la dispersione di una misura. Usare 0 ÷ 0,2 come intervallo di
sensibilità su un modello elastico lineare non fessurato sarebbe una lettura
sbagliata della norma: nu = 0 è un artificio di modellazione del fessurato, non un
calcestruzzo che esiste.

### 3.2 Esiste una fonte che lo dia come intervallo vero: sì, due

1. **fib Model Code 2010, 5.1.7.3**: per l'intervallo di tensioni
   `-0,6 fck < sigma_c < 0,8 fctk`, il coefficiente di Poisson del calcestruzzo
   **varia tra 0,14 e 0,26**; per il progetto, `nu_c = 0,20` soddisfa
   l'accuratezza richiesta. **[non verificato su testo MC2010 primario, non
   liberamente consultabile]** Riscontro indiretto sul manuale DIANA FEA 12.1.2,
   che implementa MC2010 e annota: «Poisson's ratio is preset just halfway the
   lower and upper limit: nu = 0.20 for each concrete class»
   (<https://manuals.dianafea.com/d101/MatLib/node194.html>). La formulazione
   «halfway the lower and upper limit» conferma che MC2010 dà limiti, non un
   valore unico.

2. **Letteratura peer-reviewed**: L. Ahmed, «Dynamic Measurements for Determining
   Poisson's Ratio of Young Concrete», Nordic Concrete Research, Publ. No. NCR 58,
   Issue 1/2018, Art. 6, pp. 95-106, DOI 10.2478/ncr-2018-0006 (open access, PDF
   letto il 26/08/2026) [V]:

   «The static Poisson's ratio normally for hardened concrete varies between
   0.15-0.25 [2].»

   dove [2] è M. Anson, K. Newman, «The Effect of Mix Proportions and Method of
   Testing on Poisson's Ratio for Mortars and Concretes», Magazine of Concrete
   Research, Vol. 18, No. 56, September 1966, pp. 115-130. **Questa è la fonte
   sperimentale primaria dell'intervallo**, non l'ho letta direttamente.

   Lo stesso articolo osserva [V] che «to date, there is no information given in
   the Eurocode 2 about how to specify Poisson's ratio at early age»: l'assenza di
   un intervallo negli Eurocodici è nota in letteratura, non è una svista di
   questa ricerca.

**Raccomandazione (non decisione):** per la sensibilità usare **0,14 fino a 0,26**
(MC2010), centrata su 0,20. Il 0,15 fino a 0,25 (Anson e Newman via Ahmed 2018) è
quasi coincidente e ha dietro una misura sperimentale; scegliere in base a quale
fonte si preferisce citare in tesi. **Non** usare 0 fino a 0,2.

Terzo ordine di importanza atteso: in elasticità lineare isotropa nu entra nella
rigidezza flessionale di un telaio a barre in modo quasi nullo; su un solido 3D
pesa sul taglio e sul confinamento. Se il modello è un solido tetraedrico vale la
pena includerlo; se è a travi, quasi certamente no. **[I, ragionamento meccanico,
non una fonte]**

---

## 4. Il modulo è il valore giusto da far variare?

### 4.1 Quale modulo prescrivono le norme per l'analisi elastica lineare

**EN 1992-1-1, 5.4 Linear elastic analysis** [V], testuale:

«(1) Linear analysis of elements based on the theory of elasticity may be used
for both the serviceability and ultimate limit states. (2) For the determination
of the action effects, linear analysis may be carried out assuming: i) uncracked
cross sections, ii) linear stress-strain relationships and iii) mean value of the
modulus of elasticity.»

**NTC 2018, 4.1.1.1 ANALISI ELASTICA LINEARE** [V], testuale:

«Per la determinazione degli effetti delle azioni, le analisi saranno effettuate
assumendo: sezioni interamente reagenti con rigidezze valutate riferendosi al solo
calcestruzzo; relazioni tensione deformazione lineari; valori medi del modulo
d'elasticità.»

**Risposta netta: Ecm.** Entrambe le norme, con la stessa formula, indicano il
modulo **secante medio a 28 giorni tra 0 e 0,4 fcm** per l'analisi elastica
lineare su sezioni non fessurate. Non Ec tangente, non Ecd di progetto.

### 4.2 Gli altri moduli, e perché non sono quello giusto qui

| simbolo | definizione | dove si usa | fonte |
|---|---|---|---|
| Ecm | secante medio tra 0 e 0,4 fcm, 28 gg | **analisi elastica lineare** | EC2 3.1.3(2), 5.4(2); NTC 11.2.10.3, 4.1.1.1 [V] |
| Ec | tangente all'origine, Ec = 1,05 Ecm | coefficiente di viscosità | EC2 3.1.4(2) [V] |
| Ec,eff | efficace, Ecm / (1 + phi(inf,t0)) | deformazioni a lungo termine sotto carico permanente | EC2 7.4.3(5), espr. (7.20) [V] |
| Ecd | di progetto, Ecm / gamma_cE, gamma_cE raccomandato **1,2** | effetti del secondo ordine, metodo generale | EC2 5.8.6(3), espr. (5.20) [V] |
| Ecd,eff | Ecd / (1 + phi_ef) | secondo ordine con viscosità | EC2 5.8.7.2, espr. (5.27) [V] |
| Ecm(t) | (fcm(t)/fcm)^0,3 · Ecm | modulo a età t diversa da 28 gg | EC2 3.1.3(3), espr. (3.5) [V] |

Osservazioni utili all'analisi di sensibilità [I]:

- Il salto da Ecm a Ecd è un fattore **1,2**, dello stesso ordine dell'intera
  escursione delle classi plausibili (1,21 da C20/25 a C45/55). Sbagliare quale
  modulo si è preso costa quanto sbagliare la classe.
- Il salto da Ecm a Ec,eff con phi(inf,t0) tipico 2,0 è un fattore **3**: un
  ordine di grandezza sopra ogni altra incertezza qui discussa. Se il caso di
  carico include permanenti a lungo termine, la scelta viscosità sì / viscosità no
  domina tutto il resto. Per un provino di laboratorio caricato in prova non si
  applica, ma va **dichiarato** che non si applica.
- Ecm(t): se la prova è avvenuta a un'età diversa da 28 giorni, l'espressione
  (3.5) è una correzione di prima approssimazione già disponibile.

### 4.3 La scelta è discussa in letteratura?

Sì, ma il dibattito non è su quale modulo per l'analisi lineare (su quello le
norme concordano) bensì sulla **dispersione** di Ecm attorno alla formula.

- La norma stessa mette le mani avanti: EC2 3.1.3(1) «should be regarded as
  indicative ... should be specifically assessed if the structure is likely to be
  sensitive to deviations» [V]; NTC 11.2.10.3 «non è da considerarsi vincolante
  nell'interpretazione dei controlli sperimentali» [V].
- **JCSS Probabilistic Model Code, Part 3.01 «Concrete properties»**
  (<https://jcss-pmc.github.io/PMC/part-03/concrete-properties.html>, letto il
  26/08/2026) modella Ec così [V]:
  `Ec = 10,5 · fc^(1/3) · Y_3 · (1 + beta_d · phi(t,tau))^-1` [GPa]
  dove Y_3 è la **variabile di incertezza di modello**, lognormale, media 1,0,
  **coefficiente di variazione 0,15**. Per confronto, Y_1 (resistenza a
  compressione) ha CoV **0,06**.

  Questo è il numero più direttamente utilizzabile di tutta la ricerca: **CoV del
  15% sul modulo, a resistenza nota**. Un intervallo Ecm x (1 piu/meno 2 x 0,15),
  cioè Ecm x [0,70 ; 1,30], è quasi esattamente il range che si ottiene dalle
  correzioni per aggregato di EC2 (0,70 fino a 1,20). Due strade indipendenti che
  convergono: buon segno per citarne una in tesi.
- **ACI 318** riconosce esplicitamente una dispersione dell'ordine del 20% in più
  o in meno tra Ec misurato e Ec calcolato dalla formula. **[non verificato sul
  commentario ACI 318R primario; concordanza su fonti secondarie e sul rapporto
  NRC ML16279A052]**

**Raccomandazione (non decisione):** far variare **Ecm**, ed esprimere
l'intervallo come **fattore moltiplicativo** su Ecm della classe centrale (0,70
fino a 1,30, da JCSS Y_3 con CoV 0,15 a due sigma) invece che come lista di
classi. Motivo: la classe e l'aggregato sono due incertezze distinte che si
compongono, e un fattore le porta entrambe senza fingere che il problema sia solo
«quale classe». Se il relatore vuole vedere le classi, tabellarle comunque: è la
forma che un ingegnere strutturista legge.

---

## 5. Prassi dell'analisi di sensibilità sui materiali

### 5.1 ASME V&V 20: sì, dice qualcosa, ed è preciso

**ASME V&V 20-2009, «Standard for Verification and Validation in Computational
Fluid Dynamics and Heat Transfer»**. **Caveat di dominio: il titolo dice CFD e
scambio termico, non meccanica dei solidi.** L'apparato di propagazione
dell'incertezza è però formulato in modo indipendente dalla fisica e viene citato
come tale anche fuori dalla CFD.

Fonte letta, perché V&V 20 non è liberamente consultabile: **NIST Interagency
Report NISTIR 8298**, «A Summary of Industrial Verification, Validation, and
Uncertainty Quantification ...», DOI 10.6028/NIST.IR.8298, PDF letto il
26/08/2026 (<https://nvlpubs.nist.gov/nistpubs/ir/2020/NIST.IR.8298.pdf>).
Riporta l'apparato di V&V 20 e cita «ASME V&V 20-2009» in bibliografia. **Fonte
secondaria di alta affidabilità (report NIST), non il testo ASME.**

Struttura, sezione 4 di NISTIR 8298 [V]:

«The validation standard uncertainty due to combination of the errors, uval, is
defined as uval = sqrt(unum^2 + uinput^2 + uexp^2) (10). This relationship is
valid when the three errors are independent of each other and their uncertainty
sources are aleatory (i.e., random).»

**Sezione 4.2, Estimation of input parameter uncertainty (uinput)** [V]:

«The contribution of each input parameter Xi to uinput is estimated by using a
local or a global approach. As a local method, the sensitivity coefficient method
describes the input uncertainty propagation equation for a simulation result S
caused by n uncorrelated random input parameters ... uinput^2 = somma su i di
(dS/dXi)^2 x uXi^2 (19) ... where the partial derivative dS/dXi is the sensitivity
coefficient of the validation variable S with respect to input Xi, Xi is the
nominal (e.g., mean) value of Xi, and the uXi/Xi is the relative standard
uncertainty (i.e., coefficient of variation). The input parameter uncertainty uXi
can be determined from measurements of parameters in experiments, database, or
expert's opinion.»

E il limite dichiarato del metodo locale [V]:

«This local method evaluates the input uncertainty propagation equation (Eq. (19))
within a small (local) neighborhood around the nominal values of the input
parameters. When the result S has a high non-linear behavior in the parameter
space, the local method cannot estimate properly the uncertainty inherent in
input parameters. A more reliable approach to estimating uinput is to employ
global samples in the parameter space by e.g., Monte Carlo methods. ... Since the
full Monte Carlo method is known to be computationally expensive, a less
computer-intensive method (e.g., Latin hypercube sampling method (McKay et al.
1979)) is preferred for practical applications.»

**Traduzione operativa per questa tesi:**

- V&V 20 **non** dice «varia agli estremi». Dice: prendi il **coefficiente di
  variazione** del parametro e il **coefficiente di sensibilità** dS/dX, e
  combinali in quadratura.
- La forma del risultato che V&V 20 si aspetta è una **incertezza standard
  uinput** in unità della grandezza validata, sommabile in quadratura con unum
  (discretizzazione) e uexp (misura sperimentale). Non un intervallo min/max.
- Per un modello **lineare** in E, come un'analisi elastica, il metodo locale a
  coefficienti di sensibilità è **esatto**, non approssimato: il caveat sulla non
  linearità non morde. Monte Carlo e LHS servono quando servono.

**Questo incastra bene col resto della tesi**: uinput (materiali) e la componente
geometrica della ricostruzione entrano nella **stessa** somma in quadratura, così
il confronto «quanto pesa il materiale contro quanto pesa la geometria» diventa un
rapporto tra due termini omogenei invece che tra due percentuali di cose diverse.

### 5.2 ASME V&V 10: è la norma del dominio giusto, ma dice meno

**ASME V&V 10-2019 (R2025), «Standard for Verification and Validation in
Computational Solid Mechanics»**, dominio corretto per la tesi. Dal sito ASME
<https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics>
[V]: «provide the CSM community with a common language, a conceptual framework,
and general guidance for implementing the processes of computational model VVUQ».

È un **quadro concettuale**, non un ricettario numerico: non contiene le equazioni
di propagazione che stanno in V&V 20. Gli strumenti che nomina sono la **PIRT**
(Phenomena Identification and Ranking Table) per identificare e ordinare i
fenomeni rilevanti, e la **sensitivity analysis** per stabilire l'importanza di un
processo fisico sulla risposta del sistema. **[non verificato sul testo ASME V&V
10 primario, a pagamento; ricostruito da pagina ASME piu fonti secondarie.
Confermare prima di citarlo puntualmente in tesi.]**

Documenti collegati: **ASME V&V 10.1-2012 (R2022)**, esempio svolto; **ASME
V&V 10.2**, dedicato alla UQ, che dalla pagina ASME risulta descritto come
«intended to», cioè **non ho conferma che sia pubblicato**. Verificare.

**Sintesi delle due:** V&V 10 dà il **processo** (cosa fare, in che ordine, come si
chiamano le cose); V&V 20 dà la **matematica** della propagazione. Per la tesi la
coppia funziona: citare V&V 10 per il quadro, V&V 20 per uinput, e dichiarare
esplicitamente che V&V 20 nasce in ambito CFD.

### 5.3 Come riportare la sensibilità: la letteratura ha una posizione netta

**A. Saltelli, K. Aleksankina, W. Becker, P. Fennell, F. Ferretti, N. Holst,
S. Li, Q. Wu, «Why so many published sensitivity analyses are false: A systematic
review of sensitivity analysis practices», Environmental Modelling and Software,
Vol. 114, 2019, pp. 29-39, DOI 10.1016/j.envsoft.2019.01.012** (preprint aperto:
<https://arxiv.org/abs/1711.11359>).

Tesi centrale [V, dall'abstract]: molte analisi di sensibilità pubblicate
esplorano lo spazio degli input «moving along one-dimensional corridors leaving
space of the input factors mostly unexplored»; la revisione bibliometrica mostra
che «many published sensitivity analyses fail the elementary requirement to
properly explore the space of the input factors», e conclude su «a worrying lack
of standards and of recognized good practices».

Il paper distingue nettamente **sensitivity analysis** («quale input pesa di
più?») da **uncertainty analysis** («quanto è incerta la previsione?») e
raccomanda approcci **globali** (varianza, indici di Sobol) sui modelli non
lineari o con interazioni. Raccomandazioni operative estese in A. Saltelli,
P. Annoni, «Recommended practices in global sensitivity analysis», Springer,
DOI 10.1007/978-90-481-2636-1_8.

**Come si applica qui, e dove non si applica** [I]:

- La critica di Saltelli colpisce l'OAT (one-at-a-time) **su modelli non lineari
  con interazioni**. Un'analisi **elastica lineare** con E, rho, nu non è quel
  caso: gli spostamenti sono esattamente proporzionali a 1/E, il peso proprio
  esattamente proporzionale a rho, e l'unica interazione seria è tra nu e la
  risposta 3D. **Su questo modello l'OAT è difendibile**, ma va difeso
  esplicitamente in tesi con l'argomento della linearità, non lasciato implicito.
- Se invece l'analisi diventa non lineare (fessurazione, contatto, secondo
  ordine), la difesa cade e serve un campionamento globale (LHS piu indici di
  Sobol).

**Forma del risultato, raccomandazione (non decisione):**

1. **Coefficienti di sensibilità adimensionali** `S_X = (dY/dX) · (X/Y)` per
   ciascun parametro. Su un modello lineare S_E circa -1, S_rho circa +1, S_nu
   circa 0: tre numeri che dicono tutto e si confrontano direttamente col
   coefficiente di sensibilità dell'errore geometrico.
2. **uinput in quadratura**, come V&V 20: `uinput = sqrt(somma (dY/dX · uX)^2)`,
   con uX/X = CoV (0,15 per E da JCSS; circa 0,02 per rho; circa 0,15 per nu).
   Questa è la grandezza da confrontare con il contributo geometrico.
3. **Tabella agli estremi** come contorno leggibile: min / nominale / max per
   ciascun parametro. Non è la forma raccomandata dalle norme, ma è quella che un
   lettore strutturista si aspetta, e con tre parametri costa tre run.

Le tre forme non si escludono: (1) e (2) sono il contenuto, (3) è la
presentazione.

---

## 6. Cosa non ho trovato pubblicato in chiaro

Elenco esplicito, per non dover ricostruire il perimetro dopo:

- Testo primario di **EN 1992-1-1**: letto solo un PDF OCR di terza parte. I
  numeri di Tabella 3.1 e le clausole 3.1.3 / 5.4 / 5.8.6 sono leggibili e
  coerenti tra loro, ma non è la copia CEN.
- Testo primario di **EN 1991-1-1 Tabella A.1**: nessun PDF estraibile. Il valore
  25 kN/m^3 è confermato indipendentemente dalla Tab. 3.1.I NTC, che ho letto.
- Testo primario di **EN 206:2013** (limiti 2000 / 2600 kg/m^3).
- Testo primario di **fib Model Code 2010**, 5.1.7.2 e 5.1.7.3 (formula Eci,
  intervallo 0,14-0,26).
- Testo primario di **ACI 318-19** 19.2.2.1 e del commentario ACI 318R-19 sul 20%
  in più o in meno.
- Testo primario di **ASME V&V 10-2019** e **ASME V&V 20-2009**, entrambe a
  pagamento. V&V 20 è ricostruito da NISTIR 8298, che è un report NIST e cita la
  norma in bibliografia.
- Stato di pubblicazione di **ASME V&V 10.2**.
- **Anson e Newman 1966**, Magazine of Concrete Research: fonte sperimentale
  primaria dell'intervallo 0,15-0,25, citata attraverso Ahmed 2018.
- **Nessuna statistica pubblicata** sulla classe di calcestruzzo usata nei provini
  di telaio in c.a. di laboratorio. Non esiste, o non l'ho trovata.
- **Provenienza del provino** («obra 0021», ing. José A. Barros Cabezas): non
  accertata. Se non è europea, la sezione 1.5 cambia l'intervallo.
