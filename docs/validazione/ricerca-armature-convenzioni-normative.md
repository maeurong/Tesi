# Come si dichiara l'armatura di una sezione in c.a. — convenzioni e norme

Data: 2026-08-28. Autore della raccolta: agente di ricerca (sola lettura).
Scopo: fissare le **parole e le grandezze** con cui un ingegnere descrive già
oggi l'armatura di una sezione, perché il modello dei dati del programma le
riusi invece di inventarne di nuove. Il documento non decide nulla: la §7
propone una forma di dati e la marca come raccomandazione.

## Convenzioni di lettura

- **[V]** = verificato leggendo il testo della norma in questa sessione, sul PDF
  citato accanto.
- **[V-sec]** = verificato su fonte secondaria affidabile, perché il testo
  primario è a pagamento o irraggiungibile.
- **[I]** = calcolato o inferito da me, col conto accanto. Non è un dato di norma.
- **[NON TROVATO]** = non l'ho trovato pubblicato in chiaro, e non l'ho inventato.

**Caveat generale.** Tutte le norme citate sono a pagamento. Ho letto il testo
integrale di quattro documenti su copie in rete che riproducono l'originale:

| documento | copia letta | natura della copia |
|---|---|---|
| NTC 2018, cap. 4 e 11 (DM 17/01/2018) | `studiopetrillo.com/files/ntc2018/cap4.pdf`, `cap11.pdf` | ristampa integrale del testo di Gazzetta Ufficiale, con l'intestazione «20-2-2018 Supplemento ordinario n. 8 alla GAZZETTA UFFICIALE Serie generale - n. 42» su ogni pagina |
| Circolare 21/01/2019 n. 7, cap. 4 | `studiopetrillo.com/files/ntc2018/circolare-ntc2018-cap4.pdf` | stessa provenienza |
| BS EN 1992-1-1:2004 (EC2) | <https://www.phd.eng.br/wp-content/uploads/2015/12/en.1992.1.1.2004.pdf> | scansione OCR della versione BSI; i numeri delle tabelle sono leggibili, il testo ha refusi OCR |
| BS EN 10080:2005 | <https://regbar.com/wp-content/uploads/2019/09/BS-EN-10080-2005-Steel-for-the-reinforcement-of-concrete-Weldable-reinforcing-steel-General.pdf> | copia della versione BSI |
| EHE-08 (Spagna), testo integrale 704 pagine | <http://ponderosa.es/docs/Norma-EHE-08.pdf> | ristampa integrale con articolato e commenti affiancati |

Le trascrizioni marcate **[V]** vengono da questi file. Dove il testo riportato
contiene simboli storpiati dall'OCR — `Cmin,dur`, i segni di maggiore-uguale —
lo dichiaro in loco. **Se una cifra finisce in tesi, va ricontrollata sulla
copia UNI o CEN acquistata**: queste copie servono a sapere *che cosa* cercare,
non a sostituire l'originale.

**Notazione numerica.** Vale la regola di [`README.md`](README.md) di questa
cartella: virgola decimale, punto per le migliaia, salvo dentro citazioni
verbatim, nei numeri che sono nomi — articoli, tabelle, classi, sigle — e dentro
i blocchi di codice.

**Una premessa del brief corretta in corso d'opera.** Il brief dice «il provino è
spagnolo». `PRODUCT.md` dice soltanto che la tavola `MURO 1` è dell'ing. José A.
Barros Cabezas, obra 0021, novembre 2021; non dichiara il paese. La ricerca
precedente [`materiali-intervallo.md`](materiali-intervallo.md) §1.5 tiene
aperta l'ipotesi **Ecuador** (NEC-15 / NEC-SE-HM) accanto a quella spagnola, e
non l'ha risolta. Quello che è certo è che la tavola è **in lingua spagnola**:
per questo la §6 copre la notazione ispanofona, e la §3 riporta anche le classi
di acciaio della norma spagnola. Il paese resta **non accertato**, e la scelta
del corpo normativo di riferimento resta una decisione aperta.

---

## 1. Le grandezze canoniche, e la definizione esatta di ciascuna

### 1.1 Il diametro

Il **diametro nominale** non è una misura del pezzo: è un numero convenzionale.
EHE-08, art. 32.1, verbatim [V]:

> «Se entiende por diámetro nominal de un producto de acero el número
> convencional que define el círculo respecto al cual se establecen las
> tolerancias. El área del mencionado círculo es la sección nominal.»

NTC 2018 §11.3.2.4 dice la stessa cosa per un'altra via [V]:

> «Tutti i prodotti sono caratterizzati dal diametro della barra tonda liscia
> equipesante, calcolato nell'ipotesi che la densità dell'acciaio sia pari a
> 7,85 kg/dm3.»

Cioè: il diametro è definito **per peso**, non per calibro. Una barra ad
aderenza migliorata non ha un diametro geometrico unico — ha nervature alte da
`0,03 d` a `0,15 d` (EN 10080:2005, Tabella 7 [V]) — e il diametro nominale è
quello del tondo liscio di pari massa lineica.

Conseguenza per il programma: `diametro` è un **numero convenzionale scelto da
un elenco**, non una lunghezza libera. Vedi §2.

### 1.2 Il numero e l'area

L'area di armatura si calcola **sulla sezione nominale**. EC2 3.2.7(1), verbatim
[V]: «Design should be based on the nominal cross-section area of the
reinforcement». EHE-08 art. 32.2, nota (1) della Tabella 32.2.a [V]: «Para el
cálculo de los valores unitarios se utilizará la sección nominal».

EN 10080:2005 §3, definizione di `An` [V]: «nominal cross-sectional area, An —
cross-sectional area equivalent to the area of a circular plain bar of the same
nominal diameter, d». La stessa norma **tabula** le sezioni nominali (Tabella 6,
riprodotta in §2), e le tabula **arrotondate**: 113 mm² per il Ø12, mentre
π·12²/4 = 113,1 mm² [I].

**Punto che il programma deve decidere e dichiarare:** se `area` si prende dalla
tabella della norma o si ricalcola da π·d²/4. Lo scarto è sotto lo 0,1% e non
sposta nulla in un modello elastico, ma dichiararlo costa una riga e chiude una
domanda che altrimenti torna.

L'area totale della sezione di armatura è `As = n · An`, con `n` il numero di
barre. Il simbolo `As` è quello di EC2 e delle NTC; le NTC usano `Ast` per
l'armatura trasversale (§4.1.6.1.1 [V]) e `Asw` è il simbolo di EC2 per l'area
di armatura a taglio entro il passo `s` (9.2.2(5) [V]).

### 1.3 Il copriferro — e qui si sbaglia

**Le due norme danno la stessa definizione, ed è una sola: distanza netta dalla
superficie *esterna* dell'armatura più vicina alla superficie di calcestruzzo
più vicina, staffe comprese.**

EC2 4.4.1.1(1)P, verbatim [V]:

> «The concrete cover is the distance between the surface of the reinforcement
> closest to the nearest concrete surface (including links and stirrups and
> surface reinforcement where relevant) and the nearest concrete surface.»

EHE-08 art. 37.2.4.1, verbatim [V]:

> «El recubrimiento de hormigón es la distancia entre la superficie exterior de
> la armadura (incluyendo cercos y estribos) y la superficie del hormigón más
> cercana.»

Tre cose seguono, e nessuna è ovvia.

1. **Il copriferro è netto, non all'asse.** Si misura al *bordo* della barra, non
   al suo centro.
2. **Il copriferro si misura alla staffa**, non alla barra longitudinale, quando
   la staffa è più esterna — che è il caso normale. Chi inserisce il copriferro
   pensando alla barra longitudinale sposta tutte le barre verso l'interno di
   `Ø_staffa`.
3. Esistono **due** copriferri, e sono grandezze diverse:
   - `cmin` — il minimo da garantire in ogni punto;
   - `cnom = cmin + Δcdev` — il **nominale**, quello che va sul disegno.

   EC2 4.4.1.1(2)P, verbatim [V]: «The nominal cover shall be specified on the
   drawings. It is defined as a minimum cover, Cmin (see 4.4.1.2), plus an
   allowance in design for deviation, ΔCdev». EHE-08 art. 37.2.4.1, verbatim [V]:
   «El recubrimiento nominal es el valor que debe reflejarse en los planos, y que
   servirá para definir los separadores. El recubrimiento mínimo es el valor que
   se debe garantizar en cualquier punto del elemento».

   **Il numero che l'utente legge sulla tavola è quindi `cnom`, non `cmin`.** Un
   campo chiamato «copriferro» senza qualificatore è ambiguo, e l'ambiguità vale
   10 mm — cioè, su una staffa Ø8 in una colonna, più del diametro della staffa.

La quantificazione di `Δcdev`: EC2 4.4.1.3(1)P, valore raccomandato **10 mm**
[V]; EHE-08 art. 37.2.4.1 [V] lo chiama `Δr` e lo gradua sul controllo di
esecuzione — «0 mm en elementos prefabricados con control intenso de ejecución,
5 mm en el caso de elementos ejecutados in situ con nivel intenso de control de
ejecución, y 10 mm en el resto de los casos». La Circolare NTC 2018 §C4.1.6.1.3
[V] dice: «A tali valori di tabella vanno aggiunte le tolleranze di posa, pari a
10 mm o minore, secondo indicazioni di norme di comprovata validità».

**Il «copriferro all'asse» non è un termine di norma.** Quello che le norme
definiscono è l'**altezza utile** `d` — la distanza dal bordo compresso al
baricentro dell'armatura tesa — e quella sì si misura all'asse. Se il programma
ha bisogno della posizione del centro della barra, la ricava:

    distanza asse barra dal bordo = cnom + Ø_staffa + Ø_barra/2

Questa espressione è **[I]**, una composizione delle definizioni sopra, non una
formula stampata in norma. Va scritta nel codice con questa avvertenza.

### 1.4 L'interferro

**Interferro** è il termine delle NTC per la distanza *libera* fra barre
adiacenti. NTC 2018 §4.1.6.1.3 [V]:

> «Per consentire un omogeneo getto del calcestruzzo, il copriferro e
> l'interferro delle armature devono essere rapportati alla dimensione massima
> degli inerti impiegati.»

Il valore lo dà EC2 8.2(2) [V]:

> «The clear distance (horizontal and vertical) between individual parallel bars
> or horizontal layers of parallel bars should be not less than the maximum of
> k1·bar diameter, (dg + k2 mm) or 20 mm where dg is the maximum size of
> aggregate.»
>
> «Note: The value of k1 and k2 for use in a Country may be found in its National
> Annex. The recommended values are 1 and 5 mm respectively.»

Cioè, coi valori raccomandati: **interferro ≥ max(Ø, dg + 5 mm, 20 mm)**.

Un secondo limite, di segno opposto, nelle sovrapposizioni — NTC 2018
§4.1.6.1.4 [V]: «La distanza mutua (interferro) nella sovrapposizione non deve
superare 4 volte il diametro».

### 1.5 Il passo delle staffe, e l'interasse

Le NTC usano **due** parole per la stessa idea, e le usano in due posti diversi:

- **passo**, per le staffe delle travi — §4.1.6.1.1 [V]: «con un minimo di tre
  staffe al metro e comunque passo non superiore a 0,8 volte l'altezza utile
  della sezione»;
- **interasse**, per le armature trasversali dei pilastri — §4.1.6.1.2 [V]: «Le
  armature trasversali devono essere poste ad interasse non maggiore di 12 volte
  il diametro minimo delle barre impiegate per l'armatura longitudinale, con un
  massimo di 250 mm».

Sono la stessa grandezza: **distanza fra due staffe consecutive, misurata da
asse a asse lungo l'asse dell'elemento**. EC2 9.2.2(5) [V] la chiama `s`, «the
spacing of the shear reinforcement measured along the longitudinal axis of the
member». **Non** è una distanza netta, a differenza dell'interferro.

Il limite superiore di EC2 9.2.2(6), valore raccomandato [V]:
`sl,max = 0,75·d·(1 + cot α)`, che per staffe verticali (α = 90°) dà `0,75·d`.

### 1.6 I bracci

Le NTC nel §4.1.6 **non usano la parola «bracci»**: prescrivono `Ast`, la
«sezione complessiva» delle staffe (§4.1.6.1.1 [V]), lasciando implicito che una
staffa chiusa attraversi due volte il piano di taglio.

Il termine di norma per la stessa cosa è quello di EC2 9.2.2(8) [V]: **`legs`**,
con un limite sul loro passo trasversale — «The transverse spacing of the legs
in a series of shear links should not exceed St,max», valore raccomandato
`0,75·d ≤ 600 mm`.

Quindi: «bracci» è la traduzione italiana corrente di `legs`, e il numero di
bracci `nb` entra nell'area a taglio come `Asw = nb · An(Ø_staffa)` **[I]** — la
composizione è mia, le due grandezze `Asw` e `legs` sono di norma.

**Terminologia spagnola, e la distinzione che l'italiano non fa.** EHE-08 usa
**due** parole dove l'italiano usa «staffa»: `cerco` e `estribo`. Compaiono
sempre appaiate — art. 37.2.4.1 [V] «incluyendo cercos y estribos», art. 42.3.1
[V] «cercos o estribos». **[NON TROVATO]** una definizione esplicita nel testo
di EHE-08 che separi i due termini; l'uso corrente li distingue per l'elemento
(cerco nel pilastro, estribo nella trave), ma non ho una fonte normativa che lo
dica. Se la tavola `MURO 1` scrive una delle due parole, va letta come «staffa»
e basta, senza dedurne altro.

### 1.7 Gli ancoraggi

L'ancoraggio non è un numero che l'utente dichiara: è una **lunghezza calcolata**.
EC2 8.4.4(1) [V] dà `lbd` come `α1·α2·α3·α4·α5·lb,rqd`, con cinque coefficienti
tabulati (Tabella 8.2) che dipendono dalla forma della barra, dal copriferro,
dal confinamento trasversale, dalle barre trasversali saldate e dalla pressione
trasversale; e un minimo [V]:

> «for anchorages in tension: lb,min ≥ max{0,3·lb,rqd; 10·Ø; 100 mm}»
> «for anchorages in compression: lb,min ≥ max{0,6·lb,rqd; 10·Ø; 100 mm}»

(trascrizione dal PDF OCR, dove i pedici sono in parte storpiati; i tre termini
del massimo sono leggibili senza ambiguità.)

NTC 2018 §4.1.2.1.1.4 [V] dà la tensione di aderenza da cui `lb,rqd` discende,
`fbd = fbk/γc` con `fbk = 2,25·η1·η2·fctk`, e:

> «η1 = 1,0 in condizioni di buona aderenza; η1 = 0,7 in condizioni di non buona
> aderenza [...] η2 = 1,0 per barre di diametro Ø ≤ 32 mm; η2 = (132 - Ø)/100 per
> barre di diametro superiore»

Ciò che **è** un dato geometrico dichiarabile è il **diametro del mandrino** di
piegatura, cioè il raggio della piega. EC2 Tabella 8.1N, valori raccomandati [V]:
`4Ø` per `Ø ≤ 16 mm`, `7Ø` per `Ø > 16 mm`. NTC 2018 Tab. 11.3.Ib [V] usa una
scala più fine, ma **per la prova di piegamento e raddrizzamento**, non come
regola di progetto: `4Ø` sotto 12 mm, `5Ø` fra 12 e 16, `8Ø` fra 16 e 25, `10Ø`
fra 25 e 40 — e la Tab. 32.2.b di EHE-08 [V] dà `5d`, `8d`, `10d` sugli stessi
tre scaglioni, per la stessa prova. **Non confondere le due tabelle**: quella di
EC2 è una regola di progetto, quelle di NTC ed EHE-08 sono specifiche di prova
sul materiale.

**Raccomandazione, non decisione.** Per un modello elastico di verifica
geometrica l'ancoraggio non serve. Se il programma lo chiede, chieda il
**diametro del mandrino** o il raggio di piega, che è geometria; non chieda `lbd`,
che è un risultato di calcolo e sarebbe un dato inventato dall'operatore.

---

## 2. Le serie di diametri commerciali

### 2.1 EN 10080:2005 — la regola, e la serie preferenziale

**La regola**, §7.3.1, verbatim [V]:

> «The nominal diameters up to and including 10,0 mm shall be in half
> millimetres, and above 10,0 mm, shall be in whole millimetres.»

Cioè: fino a 10 mm i mezzi millimetri sono ammessi, sopra i 10 mm solo i
millimetri interi. **Qualunque intero sopra i 10 mm è conforme**, non solo quelli
tabulati.

**La serie preferenziale**, Tabella 6 «Preferred nominal diameters,
cross-sectional areas and masses per metre», trascritta integralmente [V]. Le
colonne `X` dicono per quale prodotto quel diametro è preferenziale.

| Ø nominale [mm] | barre | rotoli e sbobinati | reti | tralicci | sezione nominale [mm²] | massa nominale [kg/m] |
|---|---|---|---|---|---|---|
| 4,0 | | X | | X | 12,6 | 0,099 |
| 4,5 | | X | | X | 15,9 | 0,125 |
| 5,0 | | X | X | X | 19,6 | 0,154 |
| 5,5 | | X | X | X | 23,8 | 0,187 |
| 6,0 | X | X | X | X | 28,3 | 0,222 |
| 6,5 | | X | X | X | 33,2 | 0,260 |
| 7,0 | | X | X | X | 38,5 | 0,302 |
| 7,5 | | X | X | X | 44,2 | 0,347 |
| 8,0 | X | X | X | X | 50,3 | 0,395 |
| 8,5 | | X | X | X | 56,7 | 0,445 |
| 9,0 | | X | X | X | 63,6 | 0,499 |
| 9,5 | | X | X | X | 70,9 | 0,556 |
| 10,0 | X | X | X | X | 78,5 | 0,617 |
| 11,0 | | X | X | X | 95,0 | 0,746 |
| 12,0 | X | X | X | X | 113 | 0,888 |
| 14,0 | X | X | X | X | 154 | 1,21 |
| 16,0 | X | X | X | X | 201 | 1,58 |
| 20,0 | X | | | | 314 | 2,47 |
| 25,0 | X | | | | 491 | 3,85 |
| 28,0 | X | | | | 616 | 4,83 |
| 32,0 | X | | | | 804 | 6,31 |
| 40,0 | X | | | | 1257 | 9,86 |
| 50,0 | X | | | | 1963 | 15,4 |

La massa nominale è calcolata con densità 7,85 kg/dm³ (§7.3.2 [V]).

**I diametri preferenziali per le barre** sono quindi soltanto dieci:
**6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40, 50 mm** — dodici, contando il 50.

Controllo aritmetico delle sezioni, `π·d²/4` [I]: 28,3 / 50,3 / 78,5 / 113,1 /
153,9 / 201,1 / 314,2 / 490,9 / 615,8 / 804,2 / 1256,6 / 1963,5 mm². La norma
tabula gli stessi numeri arrotondati a tre cifre significative; lo scarto massimo
è sotto lo 0,1%.

### 2.2 Il limite italiano — NTC 2018

Le NTC **non pubblicano una serie di diametri**. Pubblicano un intervallo, e
diverso per le due classi di acciaio, §11.3.2.4 [V]:

> «Gli acciai B450C, di cui al § 11.3.2.1, possono essere impiegati in barre di
> diametro compreso tra 6 e 40 mm.»
> «Per gli acciai B450A, di cui al § 11.3.2.2 il diametro delle barre deve essere
> compreso tra 5 e 10 mm.»

E per i rotoli, sempre §11.3.2.4 [V]: «per diametri non superiori a 16 mm per gli
acciai B450C e diametri non superiori a 10 mm per gli acciai B450A». Per le reti
e i tralicci, §11.3.2.5 [V]: `6 mm ≤ Ø ≤ 16 mm` con B450C, `5 mm ≤ Ø ≤ 10 mm` con
B450A.

Sulle dimensioni le NTC rinviano [V]: «Per quanto riguarda le tolleranze
dimensionali si fa riferimento a quanto previsto nella UNI EN 10080:2005».

**Conseguenza per un menù a tendina italiano:** l'intersezione fra la serie
preferenziale EN 10080 e l'intervallo NTC per il B450C è
**6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40 mm** — undici voci, il Ø50 escluso
perché sopra i 40 mm.

**[NON TROVATO]** Una fonte normativa o di produttore, letta in questa sessione,
che stabilisca quali diametri **non preferenziali ma conformi** (Ø18, Ø22, Ø24,
Ø26, Ø30, Ø36) siano effettivamente in commercio in Italia. La regola di
EN 10080 §7.3.1 li **ammette** tutti — sono interi sopra i 10 mm — e la prassi
italiana ne usa alcuni, ma non ho una fonte citabile. Chi progetta il menù
sappia che offrire i soli undici preferenziali è una scelta difendibile e
**restrittiva**, non una scelta neutra, e che una tavola può legittimamente
portare un Ø18.

### 2.3 La serie spagnola — EHE-08

EHE-08 art. 32.2, verbatim [V]:

> «Los posibles diámetros nominales de las barras corrugadas serán los definidos
> en la serie siguiente, de acuerdo con la tabla 6 de la UNE-EN 10080:
> 6 – 8 – 10 – 12 – 14 – 16 – 20 – 25 – 32 y 40 mm»

**Dieci voci, e non coincide con la serie preferenziale di EN 10080: mancano il
Ø28 e il Ø50.** La norma spagnola dichiara di rifarsi alla Tabella 6 della
UNE-EN 10080 e poi ne prende un sottoinsieme.

Lo stesso articolo aggiunge una raccomandazione operativa [V]: «se recomienda
utilizar en obra el menor número posible de suministradores y de diámetros
distintos, así como que estos diámetros se diferencien al máximo entre sí»; e una
cautela sul Ø6 [V]: «se procurará evitar el empleo del diámetro de 6 mm cuando se
aplique cualquier proceso de soldadura».

**Conseguenza pratica:** se la tavola `MURO 1` è spagnola, i suoi diametri
stanno in quella serie di dieci. Se il menù offre l'undici di §2.2, offre un Ø28
che quella tavola non può portare — innocuo — ma se offrisse solo i dieci
spagnoli escluderebbe il Ø28 italiano, che è legittimo. **Le due serie vanno
tenute distinte se il programma deve servire entrambi i contesti.**

---

## 3. L'acciaio d'armatura

### 3.1 Le classi italiane — NTC 2018 §11.3.2

**Sono due, e due sole.** NTC 2018 §11.3.2, incipit [V]: «È ammesso
esclusivamente l'impiego di acciai saldabili qualificati secondo le procedure di
cui al precedente § 11.3.1.2».

**B450C** — §11.3.2.1, Tab. 11.3.Ia [V]:

| | |
|---|---|
| `fy nom` | 450 N/mm² |
| `ft nom` | 540 N/mm² |

e i requisiti di Tab. 11.3.Ib [V], trascritti col verso dei segni ricostruito
dall'OCR (`≥` e `≤` escono storpiati nel PDF):

| caratteristica | requisito | frattile [%] |
|---|---|---|
| tensione caratteristica di snervamento `fyk` | ≥ `fy nom` | 5,0 |
| tensione caratteristica a carico massimo `ftk` | ≥ `ft nom` | 5,0 |
| `(ft/fy)k` | ≥ 1,15 e < 1,35 | 10,0 |
| `(fy/fy nom)k` | ≤ 1,25 | 10,0 |
| allungamento `(Agt)k` | ≥ 7,5% | 10,0 |

**B450A** — §11.3.2.2, Tab. 11.3.Ic [V]. Verbatim: «L'acciaio per calcestruzzo
armato B450A, caratterizzato dai medesimi valori nominali della tensione di
snervamento e della tensione a carico massimo dell'acciaio B450C, deve rispettare
i requisiti indicati nella seguente Tab.11.3.Ic». Le differenze:

| caratteristica | requisito | frattile [%] |
|---|---|---|
| `(ft/fy)k` | ≥ 1,05 | 10,0 |
| allungamento `(Agt)k` | ≥ 2,5% | 10,0 |

**Quindi `fyk` = 450 MPa per entrambe**: le due classi differiscono per
**duttilità**, non per resistenza. La `C` e la `A` sono le classi di duttilità di
EC2 Annex C, non gradi di resistenza. È il fraintendimento più facile, e un menù
che presentasse «B450A» e «B450C» come se avessero snervamenti diversi mentirebbe.

**Il modulo elastico non è nelle NTC.** Il §11.3.2 non lo dà, e il §4.1.2.1.2.2
[V] definisce i diagrammi di progetto senza citarlo. Il valore va preso da EC2
(§3.3 sotto) — coerentemente col fatto che le NTC rinviano alla Sezione 3 di
UNI EN 1992-1-1 «per quanto non previsto».

### 3.2 Le classi di EC2 — A, B, C

EC2 3.2.2(3)P [V]: «The application rules for design and detailing in this
Eurocode are valid for a specified yield strength range, fyk = 400 to 600 MPa».
Cioè EC2 **non tabula classi di resistenza**: dà un intervallo, e lascia al
prodotto nazionale il numero.

Quello che EC2 tabula sono le tre classi di **duttilità**, Annex C (normativo),
Tabella C.1 [V]:

| grandezza | A | B | C | frattile [%] |
|---|---|---|---|---|
| `fyk` o `f0,2k` [MPa] | 400 to 600 | 400 to 600 | 400 to 600 | 5,0 |
| `k = (ft/fy)k` | ≥ 1,05 | ≥ 1,08 | ≥ 1,15 e < 1,35 | 10,0 |
| `εuk` [%] | ≥ 2,5 | ≥ 5,0 | ≥ 7,5 | 10,0 |

(La riga `fyk` nel PDF OCR è stampata una sola volta a cavallo delle colonne;
l'intervallo 400-600 vale per tutte e tre. I valori per `Wire Fabrics` coincidono
con quelli per `Bars and de-coiled rods`.)

**Il B450C italiano è quindi un prodotto di classe C con `fyk` = 450 MPa**, e il
B450A un prodotto di classe A con lo stesso `fyk`: i requisiti di Tab. 11.3.Ib e
Ic combaciano con le colonne C e A di Tabella C.1.

### 3.3 I valori che una tesi può dichiarare

EC2 3.2.7, verbatim [V]:

> «(3) The mean value of density may be assumed to be 7850 kg/m3.»
> «(4) The design value of the modulus of elasticity, Es may be assumed to be
> 200 GPa.»

EHE-08 art. 38.4 [V] dà lo stesso numero con altre unità: «tomando como módulo de
deformación longitudinal del acero Es = 200.000 N/mm2».

**Nelle unità del progetto** — mm, N, MPa, t, s:

| grandezza | valore | unità del progetto | fonte |
|---|---|---|---|
| `Es` | 200 000 | MPa | EC2 3.2.7(4) [V]; EHE-08 38.4 [V] |
| `ρs` | 7,85·10⁻⁹ | t/mm³ | EC2 3.2.7(3), 7850 kg/m³ [V]; conversione [I] |
| `fyk` B450A e B450C | 450 | MPa | NTC 2018 Tab. 11.3.Ia [V] |
| `ftk` B450A e B450C | 540 | MPa | NTC 2018 Tab. 11.3.Ia [V] |
| `νs` | — | — | **[NON TROVATO]** in EC2, NTC ed EHE-08 |

La conversione della densità: 7850 kg/m³ = 7850·10⁻¹² t/mm³ = 7,85·10⁻⁹ t/mm³ [I].
Coerente con il 7,85 kg/dm³ che NTC §11.3.2.4 ed EN 10080 §7.3.2 usano per
definire il diametro equipesante.

**Il coefficiente di Poisson dell'acciaio d'armatura non è dato da nessuna delle
tre norme lette.** Il valore 0,3 è di manuale, non di norma. Se serve in un
modello continuo, va dichiarato come assunzione dell'operatore, esattamente come
si fa per la classe del calcestruzzo. Non citare EC2 per quel numero.

### 3.4 Le classi spagnole — EHE-08 art. 32.2, Tabella 32.2.a

Quattro designazioni, non due [V]:

| | B 400 S | B 500 S | B 400 SD | B 500 SD |
|---|---|---|---|---|
| tipo | soldable | soldable | soldable con características especiales de ductilidad | idem |
| límite elástico `fy` [N/mm²] | ≥ 400 | ≥ 500 | ≥ 400 | ≥ 500 |
| carga unitaria de rotura `fs` [N/mm²] | ≥ 440 | ≥ 550 | ≥ 480 | ≥ 575 |
| alargamiento de rotura `εu,5` [%] | ≥ 14 | ≥ 12 | ≥ 20 | ≥ 16 |
| `εmáx` in barra [%] | ≥ 5,0 | ≥ 5,0 | ≥ 7,5 | ≥ 7,5 |
| `εmáx` in rotolo [%] | ≥ 7,5 | ≥ 7,5 | ≥ 10,0 | ≥ 10,0 |
| `fs/fy` | ≥ 1,05 | ≥ 1,05 | 1,20 ≤ `fs/fy` ≤ 1,35 | 1,15 ≤ `fs/fy` ≤ 1,35 |
| `fy real / fy nominal` | — | — | ≤ 1,20 | ≤ 1,25 |

(I segni di disuguaglianza escono dal PDF come entità storpiate; li ho
ricostruiti dal verso che rende la tabella coerente. **Da ricontrollare
sull'originale UNE prima di citarli in tesi.**)

EHE-08 definisce inoltre il limite elastico in modo esplicito, art. 32.1 [V]: «se
considerará como límite elástico del acero para armaduras pasivas, fy, el valor
de la tensión que produce una deformación remanente del 0,2 por 100» — cioè `f0,2`,
la stessa convenzione di NTC §11.3.2.3 [V] («qualora lo snervamento non sia
chiaramente individuabile, si sostituisce fy con f(0,2)»).

**Se la tavola `MURO 1` è spagnola, l'acciaio più probabile è un B 500 S o
B 500 SD, con `fyk` = 500 MPa e non 450.** È una differenza dell'11% sullo
snervamento, e va accertata sulla tavola invece che assunta.

### 3.5 Il fraintendimento su EN 10080 da non ripetere

**EN 10080:2005 non definisce le classi di acciaio.** Introduzione, verbatim [V]:

> «This document does not define technical classes. Technical classes should be
> defined in accordance with this document by specified values for Re, Agt,
> Rm/Re, Re,act./Re,nom. (if applicable), fatigue strength (if required),
> bendability, weldability, bond strength, strength of welded or clamped joints
> (for welded fabric or lattice girders) and tolerances on dimensions.»

E la definizione 3.50 [V]: «reinforcing steel grade — steel grade defined by its
characteristic yield strength and ductility requirements».

Quindi: «B450C secondo EN 10080» **è una citazione sbagliata**. B450C è delle
NTC 2018 §11.3.2.1; B500S e B500SD sono di EHE-08 art. 32.2; EN 10080 dà i
diametri, le tolleranze, la geometria delle nervature e i metodi di prova, e
rimanda ai documenti nazionali per i gradi. La stessa EN 10080 è però ciò a cui
entrambe le norme nazionali rinviano per le dimensioni.

---

## 4. Il calcestruzzo — la tabella candidata a diventare il database dei materiali

### 4.1 La formula, e da dove viene

EC2, Tabella 3.1, riga `Ecm`, relazione analitica, letta sulla tabella [V]:

    Ecm = 22 · [(fcm)/10]^0,3        con Ecm in GPa e fcm in MPa

e nella stessa tabella `fcm = fck + 8 (MPa)` [V].

NTC 2018 §11.2.10.3, espressione (11.2.5), verbatim [V] (già trascritta in
[`materiali-intervallo.md`](materiali-intervallo.md) §1.2):

> «In sede di progettazione si può assumere il valore: Ecm = 22.000 [fcm/10]^0,3
> [N/mm2] (11.2.5)»

**È la stessa formula**, scritta una in GPa e l'altra in N/mm². Nelle unità del
progetto — MPa — la forma da implementare è:

    Ecm [MPa] = 22000 · (fcm / 10)^0,3        fcm = fck + 8

`Ecm` è il modulo **secante** fra tensione nulla e `0,4·fcm`. EC2 3.1.3(2),
verbatim [V]: «Approximate values for the modulus of elasticity Ecm, secant value
between σc = 0 and 0,4 fcm, for concretes with quartzite aggregates, are given in
Table 3.1». NTC §11.2.10.3 [V]: «va assunto quello secante tra la tensione nulla
e 0,40 fcm».

**Le correzioni per l'aggregato**, EC2 3.1.3(2), verbatim [V]: «For limestone and
sandstone aggregates the value should be reduced by 10% and 30% respectively. For
basalt aggregates the value should be increased by 20%». Non sono nelle NTC.

**La clausola che autorizza a dubitare del numero**, EC2 3.1.3(1), verbatim [V]:
«The values given in this Standard should be regarded as indicative for general
applications. However, they should be specifically assessed if the structure is
likely to be sensitive to deviations from these general values».

### 4.2 La tabella

Righe `fck`, `fcm` ed `Ecm` di EC2 Tabella 3.1, lette sul PDF [V]; le classi
C28/35 e C32/40 sono aggiunte perché le NTC le ammettono — Tab. 4.1.I e la frase
che la segue [V]: «Oltre alle classi di resistenza riportate in Tab. 4.1.I si
possono prendere in considerazione le classi di resistenza già in uso C28/35 e
C32/40». Anche la C8/10 è delle sole NTC: EC2 Tabella 3.1 parte da C12/15 [V].

La colonna `Ecm` non arrotondata è **[I]**, ricalcolata dalla formula sopra
(`22000*((fck+8)/10)**0.3`, Python 3, 28/08/2026), e coincide cifra per cifra
con quella già pubblicata in [`materiali-intervallo.md`](materiali-intervallo.md)
§1.1, calcolata in un'altra sessione.

| classe | `fck` [MPa] | `fcm` [MPa] | `Ecm` EC2 tabulato [GPa] | `Ecm` da formula [MPa] | in NTC? | in EC2? |
|---|---|---|---|---|---|---|
| C8/10 | 8 | 16 | — | 25.331 | sì | **no** |
| C12/15 | 12 | 20 | 27 | 27.085 | sì | sì |
| C16/20 | 16 | 24 | 29 | 28.608 | sì | sì |
| C20/25 | 20 | 28 | 30 | 29.962 | sì | sì |
| C25/30 | 25 | 33 | 31 | 31.476 | sì | sì |
| C28/35 | 28 | 36 | — | 32.308 | sì (in uso) | no |
| C30/37 | 30 | 38 | 33 | 32.837 | sì | sì |
| C32/40 | 32 | 40 | — | 33.346 | sì (in uso) | no |
| C35/45 | 35 | 43 | 34 | 34.077 | sì | sì |
| C40/50 | 40 | 48 | 35 | 35.220 | sì | sì |
| C45/55 | 45 | 53 | 36 | 36.283 | sì | sì |
| C50/60 | 50 | 58 | 37 | 37.278 | sì | sì |
| C55/67 | 55 | 63 | 38 | 38.214 | sì | sì |
| C60/75 | 60 | 68 | 39 | 39.100 | sì | sì |
| C70/85 | 70 | 78 | 41 | 40.743 | sì | sì |
| C80/95 | 80 | 88 | 42 | 42.244 | sì | sì |
| C90/105 | 90 | 98 | 44 | 43.631 | sì | sì |

**Correzione del 30/08/2026 sulla riga C8/10.** Questa tabella pubblicava
`Ecm` = 25.393 MPa. È un refuso isolato: `22000·(16/10)^0,3` = **25.331,37**, e
la ricerca successiva
[`ricerca-ntc-2018-numeri-per-il-catalogo.md`](ricerca-ntc-2018-numeri-per-il-catalogo.md)
§1.4 ottiene lo stesso 25.331 ricalcolando la colonna da capo, con le altre
sedici righe che coincidono cifra per cifra fra le due sessioni — quindi non era
né una formula diversa né un arrotondamento sistematico, ma questa sola riga. Il
valore in tabella è stato portato a quello della formula, che è anche quello che
il catalogo dei materiali di `core/materiali.py` produce.

La riga C8/10 porta un `Ecm` calcolato **fuori dal dominio in cui EC2 tabula la
formula**: la classe esiste nelle NTC ma non in EC2 Tabella 3.1. Il numero è
un'estrapolazione mia [I] e non va citato come dato di norma. Vale la pena
tenerlo nel database solo se il programma deve poter rappresentare una classe che
le NTC ammettono; e in quel caso la riga va marcata come tale.

### 4.3 Poisson e densità

**Poisson.** EC2 3.1.3(4), verbatim [V]:

> «Poisson's ratio may be taken equal to 0,2 for uncracked concrete and 0 for
> cracked concrete.»

Il valore per il programma è quindi **0,2**, ed è quello **non fessurato** — la
condizione di un'analisi elastica lineare. Il secondo numero della frase, lo zero
per il calcestruzzo fessurato, non è un'alternativa da offrire in un menù: è la
scelta che si fa quando si modella la fessurazione, cosa che questo programma non
fa.

Il dato che manca a EC2: **l'intervallo**. Le NTC non danno alcun valore di
Poisson per il calcestruzzo nel §11.2.10. L'intervallo 0,14-0,26 usato nella
ricerca precedente viene da fib Model Code 2010 §5.1.7.3 tramite fonte secondaria
— vedi [`materiali-intervallo.md`](materiali-intervallo.md) §3, che lo dichiara
come tale.

**Densità.** NTC 2018 Tab. 3.1.I [V, già trascritta in
[`materiali-intervallo.md`](materiali-intervallo.md) §2.1] dà **pesi dell'unità
di volume**, non densità: 24,0 kN/m³ per il calcestruzzo ordinario e 25,0 kN/m³
per il calcestruzzo armato.

La conversione, con `g` = 9,80665 m/s² [I]:

| voce | peso [kN/m³] | densità [kg/m³] | densità [t/mm³] |
|---|---|---|---|
| calcestruzzo ordinario | 24,0 | 2447,3 | 2,4473·10⁻⁹ |
| calcestruzzo armato | 25,0 | 2549,3 | 2,5493·10⁻⁹ |

**Il valore 2,5·10⁻⁹ t/mm³ che le corse del progetto usano non è nessuno dei due**:
corrisponde a 2500 kg/m³, cioè 24,52 kN/m³ [I]. È a metà fra le due righe della
tabella, ed è un arrotondamento di prassi. Non è un errore — è una scelta, e come
tale va dichiarata invece che presentata come dato di norma. Lo stesso punto è
già sollevato in [`materiali-intervallo.md`](materiali-intervallo.md) §2.1.

**Attenzione all'incoerenza interna che ne segue.** Se il programma usa `g` =
9810 mm/s² (come `config.GRAVITY_MM_S2`) e `ρ` = 2,5·10⁻⁹ t/mm³, il peso che ne
esce è 24,525 kN/m³, non i 25,0 della Tab. 3.1.I. Se si vuole che il modello pesi
quanto la norma dice, la densità da mettere è **2,5493·10⁻⁹**, non 2,5·10⁻⁹. Lo
scarto è del 2%, sotto la banda di incertezza sul modulo (±8% a classe nota, ±34%
ad aggregato ignoto, [`materiali-intervallo.md`](materiali-intervallo.md) §0) —
ma è sistematico e ha un verso.

### 4.4 La formula spagnola è un'altra, e differisce del 13%

EHE-08 art. 39.6, verbatim [V]:

> «Como módulo de deformación longitudinal secante Ecm a 28 días (pendiente de la
> secante de la curva real σ-ε), se adoptará: Ecm = 8500 · ∛fcm»
> «Dicha expresión es válida siempre que las tensiones, en condiciones de
> servicio, no sobrepasen el valor de 0,40 fcm»

Stessa definizione di modulo (secante a `0,4 fcm`, 28 giorni), **formula diversa**.
Confronto [I], stessa sessione:

| classe | `Ecm` EC2 [MPa] | `Ecm` EHE-08 [MPa] | rapporto |
|---|---|---|---|
| C20/25 | 29.962 | 25.811 | 0,861 |
| C25/30 | 31.476 | 27.264 | 0,866 |
| C30/37 | 32.837 | 28.577 | 0,870 |
| C40/50 | 35.220 | 30.891 | 0,877 |

**La formula spagnola dà sistematicamente il 12-14% in meno di quella
eurocodice.** Se il provino è spagnolo e si usa la formula EC2, si sta assumendo
un calcestruzzo più rigido di quanto la norma del paese del provino prescriva —
e il verso dell'errore è noto: la freccia calcolata esce **più piccola** del vero
di circa il 13%, perché in elasticità lineare la freccia va come `1/E`
([`materiali-intervallo.md`](materiali-intervallo.md) §5). È dello stesso ordine
della banda ±8% a classe nota. **Va dichiarato quale formula si è usata.**

EHE-08 usa anche `fcm = fck + 8 N/mm²`, con una condizione esplicita [V]:
«que es válida si las condiciones de fabricación son buenas».

### 4.5 Che cosa la tabella dei materiali deve portare

Per un modello **elastico lineare** servono tre numeri per materiale: `E`, `ν`,
`ρ`. La tabella della §4.2 li dà tutti e tre per il calcestruzzo, la §3.3 per
l'acciaio. Quello che la tabella **non** deve portare, perché non serve a un
modello elastico e inviterebbe a citarlo a sproposito: `fcd`, `fyd`, i
coefficienti parziali `γc` = 1,5 e `γs` = 1,15 (NTC §4.1.2.1.1.1 e §4.1.2.1.1.3
[V]), i diagrammi parabola-rettangolo. Sono grandezze di **verifica**, non di
analisi.

Una riga del database dovrebbe quindi portare: nome della classe, `fck`, `fcm`,
`Ecm`, `ν`, `ρ`, **la norma e l'articolo da cui ciascun numero viene**, e un
marcatore per le righe che sono estrapolazioni (la C8/10) o scelte di prassi (la
densità 2,5·10⁻⁹).

---

## 5. Il copriferro per norma — come si propone un valore predefinito

### 5.1 La struttura del calcolo secondo EC2

EC2 4.4.1.2(2)P, verbatim [V] (trascrizione dal PDF OCR, che storpia alcuni
pedici):

> «The greater value for Cmin satisfying the requirements for both bond and
> environmental conditions shall be used.
> Cmin = max {Cmin,b; Cmin,dur + ΔCdur,γ − ΔCdur,st − ΔCdur,add; 10 mm}»

Tre requisiti, EC2 4.4.1.2(1)P [V]: «the safe transmission of bond forces», «the
protection of the steel against corrosion (durability)», «an adequate fire
resistance (see EN 1992-1-2)».

**Il termine di aderenza**, Tabella 4.2 [V]: `cmin,b` = **diametro della barra**
per barre separate, diametro equivalente `Øn` per barre raggruppate; con la nota
[V]: «If the nominal maximum aggregate size is greater than 32 mm, Cmin,b should
be increased by 5 mm».

**Il termine di durabilità**, `cmin,dur`, dipende da **classe di esposizione** e
**classe strutturale**. Tabella 4.4N, valori raccomandati per l'armatura ordinaria
[V]:

| classe strutturale | X0 | XC1 | XC2/XC3 | XC4 | XD1/XS1 | XD2/XS2 | XD3/XS3 |
|---|---|---|---|---|---|---|---|
| S1 | 10 | 10 | 10 | 15 | 20 | 25 | 30 |
| S2 | 10 | 10 | 15 | 20 | 25 | 30 | 35 |
| S3 | 10 | 10 | 20 | 25 | 30 | 35 | 40 |
| S4 | 10 | 15 | 25 | 30 | 35 | 40 | 45 |
| S5 | 15 | 20 | 30 | 35 | 40 | 45 | 50 |
| S6 | 20 | 25 | 35 | 40 | 45 | 50 | 55 |

(Valori in mm. La riga S1 del PDF OCR ha una cella spostata: sono sette colonne e
sei valori leggibili, `10 10 10 15 20 30`, con il valore di XD2/XS2 ricostruito
come 25 per coerenza con la progressione delle righe successive. **La riga S1 va
ricontrollata sull'originale.** Le righe da S2 a S6 sono complete e leggibili.)

**La classe strutturale di partenza**, nota a 4.4.1.2(5) [V]: «The recommended
Structural Class (design working life of 50 years) is S4 for the indicative
concrete strengths given in Annex E and the recommended modifications to the
structural class is given in Table 4.3N. The recommended minimum Structural Class
is S1». Tabella 4.3N [V] modifica la classe: +2 per vita nominale di 100 anni;
−1 se la resistenza supera una soglia che dipende dalla classe di esposizione
(≥ C30/37 per X0, XC1, XC2/XC3; ≥ C35/45 per XC4; ≥ C40/50 per XD1, XD2/XS1;
≥ C45/55 per XD3/XS2/XS3); −1 per elemento a geometria di piastra; −1 se il
controllo di qualità della produzione del calcestruzzo è garantito.

**Il nominale**, 4.4.1.3(1)P [V]: `cnom = cmin + Δcdev`, con `Δcdev`
raccomandato 10 mm.

### 5.2 La via italiana — più corta, e con una tabella pronta

Le NTC 2018 **non tabulano il copriferro**. §4.1.6.1.3, verbatim [V]:

> «Al fine della protezione delle armature dalla corrosione, lo strato di
> ricoprimento di calcestruzzo (copriferro) deve essere dimensionato in funzione
> dell'aggressività dell'ambiente e della sensibilità delle armature alla
> corrosione, tenendo anche conto delle tolleranze di posa delle armature; a tale
> scopo si può fare utile riferimento alla UNI EN 1992-1-1.»

Il numero lo dà la **Circolare 21/01/2019 n. 7**, §C4.1.6.1.3, Tabella C4.1.IV
«Copriferri minimi in mm» [V]. Non usa le classi di esposizione di EC2 ma le tre
**condizioni ambientali** di NTC Tab. 4.1.III [V]:

| condizioni ambientali | classi di esposizione |
|---|---|
| ordinarie | X0, XC1, XC2, XC3, XF1 |
| aggressive | XC4, XD1, XS1, XA1, XA2, XF2, XF3 |
| molto aggressive | XD2, XD3, XS2, XS3, XA3, XF4 |

Tabella C4.1.IV, per **barre da c.a.** (le colonne per i cavi da c.a.p. sono
riportate per completezza) [V]:

| ambiente | `Cmin` | `C0` | piastre, `C ≥ C0` | piastre, `Cmin ≤ C < C0` | altri elementi, `C ≥ C0` | altri elementi, `Cmin ≤ C < C0` |
|---|---|---|---|---|---|---|
| ordinario | C25/30 | C35/45 | 15 | 20 | 20 | 25 |
| aggressivo | C30/37 | C40/50 | 25 | 30 | 30 | 35 |
| molto aggressivo | C35/45 | C45/55 | 35 | 40 | 40 | 45 |

(Per i cavi da c.a.p.: piastre 25/30/35 e 30/40/45; altri elementi 30/40/50 e
35/45/50. La tabella è stata estratta due volte con metodi diversi dallo stesso
PDF, e le due estrazioni concordano su tutte le celle tranne l'ultima colonna,
letta solo dall'estrazione testuale piatta.)

E le regole di correzione, §C4.1.6.1.3, verbatim [V]:

> «A tali valori di tabella vanno aggiunte le tolleranze di posa, pari a 10 mm o
> minore, secondo indicazioni di norme di comprovata validità.»
> «I valori della Tabella C4.1.IV si riferiscono a costruzioni con vita nominale
> di 50 anni (Tipo 2 secondo la Tabella 2.4.I delle NTC). Per costruzioni con vita
> nominale di 100 anni (Tipo 3 secondo la citata Tabella 2.4.I) i valori della
> Tabella C4.1.IV vanno aumentati di 10 mm. Per classi di resistenza inferiori a
> Cmin i valori della tabella sono da aumentare di 5 mm. Per produzioni di
> elementi sottoposte a controllo di qualità che preveda anche la verifica dei
> copriferri, i valori della tabella possono essere ridotti di 5 mm.»

### 5.3 Il valore predefinito che ne discende

Per un **telaio in c.a. in ambiente ordinario, elemento monodimensionale
(«altri elementi»), calcestruzzo da C25/30 a C35/45, vita nominale 50 anni**:

- copriferro minimo da Tabella C4.1.IV: **25 mm** (colonna `Cmin ≤ C < C0`, cioè
  classe fra C25/30 e C35/45 esclusa);
- più tolleranza di posa 10 mm;
- **`cnom` = 35 mm** [I, somma delle due righe di norma].

Se il calcestruzzo è C35/45 o superiore si scende alla colonna `C ≥ C0`, cioè
20 + 10 = **30 mm** [I].

Il controllo di aderenza di EC2 Tabella 4.2 non morde in questo intervallo: per
un Ø16 `cmin,b` = 16 mm, sotto i 25 mm della durabilità [I].

**Raccomandazione, non decisione: 35 mm come valore predefinito**, con la classe
di calcestruzzo e le condizioni ambientali come i due parametri che lo muovono, e
il numero mostrato all'utente come **modificabile** con la sua provenienza
accanto. Un campo vuoto e un campo con un 35 muto sono ugualmente sbagliati; un
campo con «35 mm — ambiente ordinario, elemento monodimensionale, C25/30-C35/45,
Circolare 2019 Tab. C4.1.IV + 10 mm di posa» è il terzo caso.

**Caveat che vale per tutta la §5.** Il provino non è un edificio: è un telaio di
laboratorio. Le tabelle di durabilità presuppongono una vita nominale di 50 anni
in un ambiente. Un provino di prova non ha né l'una né l'altro, e il copriferro
che porta è quello che il progettista ha disegnato — che la tavola `MURO 1`
dichiara o non dichiara. **Il valore predefinito serve a non lasciare il campo
vuoto, non a sostituire la lettura della tavola.**

### 5.4 La via spagnola

EHE-08 art. 37.2.4.1 [V] pone tre condizioni **minime, indipendenti dalla
tabella**, che nessuna delle due norme precedenti scrive così esplicitamente:

> «a) Cuando se trata de armaduras principales, el recubrimiento deberá ser igual
> o superior al diámetro de dicha barra (o diámetro equivalente si se trata de un
> grupo de barras) y a 0,80 veces el tamaño máximo del árido»
> «d) El recubrimiento de las barras dobladas no será inferior a dos diámetros,
> medido en dirección perpendicular al plano de la curva.»

e, per il getto contro terra [V]: «En piezas hormigonadas contra el terreno, el
recubrimiento mínimo será 70 mm, salvo que se haya preparado el terreno y
dispuesto un hormigón de limpieza». Rilevante: il provino ha **due zapatas**.

Le tabelle 37.2.4.1.a/b/c graduano il minimo su classe di esposizione, tipo di
cemento, `fck` e vita utile (50 o 100 anni). Per la classe I con `fck ≥ 25`:
**15 mm a 50 anni, 25 mm a 100 anni** [V].

---

## 6. La notazione da disegno

### 6.1 Che cosa la norma prescrive davvero

La norma internazionale che governa il disegno esecutivo delle armature è
**ISO 3766:2003, *Construction drawings — Simplified representation of concrete
reinforcement***, terza edizione, 2003-12-15, preparata da ISO/TC 10/SC 8;
recepita in Italia come **UNI EN ISO 3766:2005**. Ho letto l'**anteprima
ufficiale** (11 pagine, `standards.iteh.ai`), che copre il frontespizio, l'indice,
la §1 Scope, la §3 e la §4.1 con la Tabella 1. **Le §5 (Marking), §6 (Bending
information) e §7 (Bar schedule) non sono nell'anteprima e non le ho lette.** [V]
per ciò che segue, **[NON LETTO]** per la sintassi del contrassegno.

§3, verbatim [V] — l'elenco di ciò che la tavola **deve** portare:

> «The following characterizations (general information and placement
> information) of the reinforcement bars shall be given on the drawing:
> — required concrete strength class, the exposure class and further requirements
> to the concrete given in reference standards;
> — type of reinforcing steel and prestressed steel given in reference standards;
> — bar mark, number, diameter, shape and position of the reinforcement bars;
> distance between the bars and overlap length at joints; [...]
> — the layer dimension cV which derives from the nominal dimension cnom of the
> concrete cover, as well as the allowance in design for tolerance Δc of the
> concrete cover;»

**Questa è la lista dei campi, scritta da una norma.** Riordinata:

| campo ISO 3766 §3 | corrispettivo italiano |
|---|---|
| required concrete strength class | classe di calcestruzzo |
| exposure class | classe di esposizione |
| type of reinforcing steel | classe di acciaio |
| bar mark | contrassegno / posizione |
| number | numero di barre |
| diameter | diametro |
| shape | sagoma |
| position | posizione nella sezione |
| distance between the bars | interferro |
| overlap length | lunghezza di sovrapposizione |
| `cnom` e `Δc` | copriferro nominale e tolleranza di posa |

La §1 Scope [V] dichiara che la norma stabilisce anche «a coding system for bar
shapes, a schedule of preferred shapes, and a shape schedule and bending
schedule»: le **sagome** sono codificate per numero, e la §6.3 (non letta) porta
il sistema di codifica.

### 6.2 Le stringhe compatte — convenzione, non norma

`4Ø16`, `Ø8/20`, `e Ø8 c/20` sono **abbreviazioni di disegno**, e in nessuna
delle norme che ho letto in questa sessione compare una di queste stringhe.

**[NON TROVATO]** Una fonte normativa che prescriva la sintassi compatta. La §5
di ISO 3766 si chiama «Marking» e potrebbe contenerla; non l'ho potuta leggere.
**Da accertare sulla copia UNI EN ISO 3766:2005 prima di affermare che una
sintassi è «a norma».**

Quello che si può dire con le fonti in mano è la **scomposizione**, campo per
campo, e quella sì poggia sulla lista di ISO 3766 §3 e sul vocabolario delle due
norme nazionali:

| pezzo | che cosa è | fonte del termine |
|---|---|---|
| `4` | numero di barre | ISO 3766 §3 «number» [V] |
| `Ø` | il simbolo del diametro nominale | EN 10080 §4 usa `d`; le NTC scrivono il simbolo Ø nel §4.1.6.1.4 («Per barre di diametro Ø >32 mm») [V] |
| `16` | il diametro nominale in mm, dalla serie di §2 | EN 10080 Tab. 6 [V] |
| `/20` o `c/20` | il passo, cioè la distanza fra staffe consecutive | NTC §4.1.6.1.1 «passo», §4.1.6.1.2 «interasse» [V]; EC2 9.2.2(5) `s` [V] |
| `e` (spagnolo) | estribo, cioè staffa | EHE-08 art. 37.2.4.1 «cercos y estribos» [V] |

**Il tranello dell'unità sul passo.** `Ø8/20` in una tavola italiana è quasi
sempre `20 cm`, non `20 mm`, perché una staffa Ø8 ogni 20 mm non esiste; e la
notazione spagnola `c/20` — `c/` sta per `cada` — porta la stessa ambiguità.
**[V-sec]** per lo scioglimento di `c/` come `cada`: l'ho trovato solo su fonti
di forum e blog di settore, non su norma. Un programma che legge un passo da una
tavola **deve chiedere l'unità o dedurla da un intervallo di plausibilità**, e
deve dichiarare quale delle due ha fatto. Le NTC lavorano in millimetri
(§4.1.6.1.2, «con un massimo di 250 mm» [V]); le tavole no.

**Il contrassegno.** ISO 3766 §3 [V] richiede il `bar mark`, un identificatore
che lega la barra disegnata alla riga della distinta. La Tabella 1 dell'anteprima
[V] mostra come si disegna — voce 4, «Straight bars lying in a row or a plane to
indicate the ends of the bars, showing corresponding bar marks using narrow
line»; voce 8b, «with marking bar ends by a slash and bar marks» — ma non come si
scrive. Se il programma vuole poter ribattere una tavola riga per riga, il
contrassegno è il campo che glielo permette, ed è l'unico campo puramente
**testuale** dell'elenco.

### 6.3 Il vocabolario da usare nell'interfaccia italiana

Le parole sono già scritte in norma, e sono queste — non se ne inventano altre:

| concetto | parola italiana di norma | fonte |
|---|---|---|
| ricoprimento di calcestruzzo | **copriferro** | NTC §4.1.6.1.3 [V] |
| distanza libera fra barre | **interferro** | NTC §4.1.6.1.3 [V] |
| armatura trasversale chiusa | **staffa** | NTC §4.1.6.1.1 [V] |
| distanza fra staffe | **passo** (travi) / **interasse** (pilastri) | NTC §4.1.6.1.1 e §4.1.6.1.2 [V] |
| armatura in zona tesa | **armatura longitudinale** | NTC §4.1.6.1.1 [V] |
| distanza dal bordo compresso al baricentro dell'armatura tesa | **altezza utile** `d` | NTC §4.1.6.1.1 [V] |
| resistenza caratteristica a compressione | `fck` | NTC §11.2.10.1 [V] |
| tensione caratteristica di snervamento | `fyk` | NTC §4.1.2.1.1.3 [V] |

---

## 7. Verdetto — la forma dei dati che ne discende

**Questa sezione è una raccomandazione, non una decisione.** Le motivazioni
stanno tutte sopra, ciascuna col suo riferimento.

### 7.1 I campi

Otto campi dichiarati dall'utente, tre derivati e mostrati in sola lettura.

| campo | nome italiano | unità | dominio ammesso | perché |
|---|---|---|---|---|
| classe di calcestruzzo | `classe calcestruzzo` | — | enumerazione: C8/10, C12/15, C16/20, C20/25, C25/30, C28/35, C30/37, C32/40, C35/45, C40/50, C45/55, C50/60, C55/67, C60/75, C70/85, C80/95, C90/105 | NTC Tab. 4.1.I più le due «in uso» [V]; è l'elenco della §4.2. Da essa discendono `Ecm`, `ν`, `ρ`: non si chiedono all'utente |
| classe di acciaio | `classe acciaio` | — | enumerazione: B450A, B450C (NTC); B400S, B500S, B400SD, B500SD (EHE-08) | §3.1 e §3.4. Le due famiglie **non** vanno mescolate in un unico elenco senza dire di quale norma sono |
| diametro delle barre longitudinali | `diametro barre` | mm | enumerazione: 6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40 con B450C; 5, 6, 8, 10 con B450A; 6, 8, 10, 12, 14, 16, 20, 25, 32, 40 se la norma di riferimento è EHE-08 | §2.1, §2.2, §2.3. **Menù, non campo libero**: il diametro è un numero convenzionale scelto da una serie, §1.1 |
| numero di barre | `numero barre` | — | intero ≥ 2 | ISO 3766 §3 «number» [V] |
| diametro delle staffe | `diametro staffe` | mm | stessa enumerazione del diametro barre, con il vincolo `Ø_st ≥ 6 mm` e `Ø_st ≥ Ø_l,max / 4` | NTC §4.1.6.1.2, verbatim: «Il diametro delle staffe non deve essere minore di 6 mm e di ¼ del diametro massimo delle barre longitudinali» [V] |
| passo delle staffe | `passo staffe` | mm | reale > 0; avviso se `> min(12·Ø_l,min, 250)` per un pilastro, se `> 0,8·d` per una trave | NTC §4.1.6.1.2 e §4.1.6.1.1 [V]. **Unità dichiarata in etichetta**, per il tranello di §6.2 |
| numero di bracci | `bracci` | — | intero ≥ 2 | EC2 9.2.2(8) «legs» [V]; §1.6 |
| copriferro nominale | `copriferro nominale` | mm | reale ≥ 10; predefinito 35 | §5.3. **Il nome porta «nominale»**: è `cnom`, quello che sta sul disegno, non `cmin`. §1.3 |

I tre campi derivati, calcolati e non chiesti:

| campo derivato | formula | unità | fonte |
|---|---|---|---|
| area di una barra | valore tabulato di EN 10080 Tab. 6, oppure `π·Ø²/4` — e **si dichiara quale** | mm² | §1.2 |
| area totale di armatura `As` | `numero barre · area di una barra` | mm² | EC2 3.2.7(1) [V] |
| distanza dell'asse della barra dal bordo | `copriferro nominale + diametro staffe + diametro barre / 2` | mm | §1.3, composizione [I] |

### 7.2 Le tre regole di validazione che valgono la pena

Non un validatore per campo — tre controlli, ciascuno con la sua fonte:

1. **Interferro**: `(larghezza − 2·copriferro − 2·Ø_st − n·Ø_l) / (n − 1) ≥ max(Ø_l, dg + 5, 20)`.
   EC2 8.2(2) coi valori raccomandati `k1` = 1 e `k2` = 5 [V]. È il controllo che
   dice se le barre dichiarate ci **stanno** nella sezione. Richiede `dg`, la
   dimensione massima dell'inerte, che è un dato in più: se non si vuole chiederlo,
   il termine `dg + 5` si omette **dichiarandolo**, e il vincolo diventa
   `max(Ø_l, 20)`.
2. **Diametro delle staffe**: `Ø_st ≥ 6` e `Ø_st ≥ Ø_l,max / 4`. NTC §4.1.6.1.2 [V].
3. **Passo**: `s ≤ min(12·Ø_l,min, 250)` per un pilastro. NTC §4.1.6.1.2 [V].

Il primo è un **errore** — la geometria è impossibile. Gli altri due sono
**avvisi**: una tavola reale può violarli, e il programma deve poter ribattere
quello che c'è scritto, non rifiutarlo. È la stessa distinzione che il registro
delle soglie del progetto già fa fra vincolo e verdetto.

### 7.3 Che cosa non chiedere

- **La lunghezza di ancoraggio.** È un risultato di calcolo, non un dato
  geometrico: §1.7. Se serve la piega, si chiede il diametro del mandrino.
- **`E`, `ν`, `ρ` del calcestruzzo come numeri liberi.** Discendono dalla classe,
  §4.2 e §4.3. Se si vuole permettere l'override — e ha senso, perché la tavola
  non dichiara la classe — l'override va marcato come tale nel modello e nel
  report, non confuso con un valore di norma.
- **Il coefficiente di Poisson dell'acciaio.** Nessuna delle tre norme lo dà,
  §3.3. Se il modello lo richiede, è un'assunzione dell'operatore e va detto.
- **`fcd` e `fyd`.** Servono alla verifica, non all'analisi elastica: §4.5.

### 7.4 La riga che il modello dei dati deve poter scrivere nel report

Se i campi sono quelli di §7.1, il programma può stampare esattamente quello che
un ingegnere legge su una tavola, con la provenienza accanto:

    4 Ø16 B450C, staffe Ø8 passo 200 mm, 2 bracci, copriferro nominale 35 mm,
    calcestruzzo C25/30 (E = 31.476 MPa, nu = 0,20, rho = 2,5493e-9 t/mm^3)

dove `4 Ø16` viene dall'utente, `31.476` dalla formula di EC2 Tabella 3.1 e NTC
(11.2.5), `0,20` da EC2 3.1.3(4), `2,5493e-9` dalla Tab. 3.1.I delle NTC
convertita. **Nessuno di questi numeri è inventato dal programma, e ognuno sa
dire da dove viene.** È la condizione perché il modello dei dati non aggiunga
un'assunzione tacita a quella — già dichiarata — sulla classe del calcestruzzo.

---

## 8. Che cosa non ho verificato

Elenco esplicito, perché una ricerca senza questa sezione si legge come se avesse
letto tutto.

1. **ISO 3766:2003 §5 «Marking», §6 «Bending information», §7 «Bar schedule».**
   Fuori dall'anteprima pubblica. È esattamente dove starebbe la sintassi del
   contrassegno, se una sintassi normata esiste. **Da comprare o consultare in
   biblioteca prima di affermare che `4Ø16` è o non è «a norma».**
2. **Il significato normativo di `c/` nella notazione spagnola.** Sciolto come
   `cada` solo su fonti di settore non firmate. **[V-sec]** debole.
3. **La distinzione fra `cerco` e `estribo` in EHE-08.** I due termini compaiono
   sempre appaiati; non ho trovato una definizione che li separi.
4. **La riga S1 di EC2 Tabella 4.4N.** Una cella è illeggibile nel PDF OCR e l'ho
   ricostruita per coerenza. Le righe S2-S6 sono complete.
5. **I versi delle disuguaglianze in NTC Tab. 11.3.Ib/Ic e in EHE-08
   Tab. 32.2.a.** Il PDF li rende come entità storpiate; li ho ricostruiti dal
   senso. I **numeri** sono leggibili senza ambiguità, i **segni** no.
6. **L'ultima colonna della Tabella C4.1.IV della Circolare** (cavi da c.a.p.,
   altri elementi, `Cmin ≤ C < C0`): letta da una sola delle due estrazioni.
7. **La disponibilità commerciale in Italia dei diametri non preferenziali**
   (Ø18, Ø22, Ø24, Ø26, Ø30, Ø36), che EN 10080 §7.3.1 ammette ma non tabula.
   **[NON TROVATO]** una fonte citabile.
8. **Il testo del Código Estructural spagnolo (RD 470/2021)**, in vigore dal
   10/11/2021 — cioè nello stesso mese della tavola. Ho letto EHE-08, che quel
   regio decreto sostituisce. **Se la provenienza spagnola si conferma, va
   accertato quale dei due si applichi** e se le serie di diametri e le classi di
   acciaio cambiano.
9. **La norma ecuadoriana NEC-SE-HM**, che
   [`materiali-intervallo.md`](materiali-intervallo.md) §1.5 tiene aperta come
   ipotesi alternativa. Il PDF ufficiale non era scaricabile in questa sessione
   (errori TLS ripetuti dal server). Se la provenienza del provino conta, va
   accertata: cambia la formula del modulo, la serie dei diametri e il grado
   dell'acciaio.
10. **fib Model Code 2010** per l'intervallo di Poisson: non consultabile
    liberamente, già dichiarato come **[V-sec]** in
    [`materiali-intervallo.md`](materiali-intervallo.md) §3.

---

## 9. Bibliografia

**Norme**

1. **NTC 2018** — DM 17/01/2018, *Aggiornamento delle «Norme tecniche per le
   costruzioni»*, Supplemento ordinario n. 8 alla Gazzetta Ufficiale, Serie
   generale n. 42 del 20-02-2018. Capitoli 4 e 11.
2. **Circolare 21/01/2019 n. 7 C.S.LL.PP.** — *Istruzioni per l'applicazione
   dell'«Aggiornamento delle Norme tecniche per le costruzioni»*. Capitolo 4.
3. **EN 1992-1-1:2004** — *Eurocode 2: Design of concrete structures — Part 1-1:
   General rules and rules for buildings*, CEN, Bruxelles. Recepita come
   UNI EN 1992-1-1:2005.
4. **EN 10080:2005** — *Steel for the reinforcement of concrete — Weldable
   reinforcing steel — General*, CEN, Bruxelles. Recepita come UNI EN 10080:2005.
5. **ISO 3766:2003** — *Construction drawings — Simplified representation of
   concrete reinforcement*, terza edizione, ISO/TC 10/SC 8, 2003-12-15. Recepita
   come UNI EN ISO 3766:2005. Pagina editore: <https://www.iso.org/standard/34171.html>
6. **EHE-08** — *Instrucción de Hormigón Estructural*, Real Decreto 1247/2008,
   Ministerio de Fomento, Spagna.
7. **UNI EN 206:2016** — classi di esposizione, richiamata da NTC Tab. 4.1.III.
   Non letta.
8. **Código Estructural** — Real Decreto 470/2021, BOE-A-2021-13681. Non letto.
   <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2021-13681>

**Copie consultate** (elencate anche in testa al documento)

9. `studiopetrillo.com/files/ntc2018/cap4.pdf`, `cap11.pdf`,
   `circolare-ntc2018-cap4.pdf` — ristampa integrale del testo di Gazzetta
   Ufficiale.
10. <https://www.phd.eng.br/wp-content/uploads/2015/12/en.1992.1.1.2004.pdf> —
    BS EN 1992-1-1:2004, scansione OCR.
11. <https://regbar.com/wp-content/uploads/2019/09/BS-EN-10080-2005-Steel-for-the-reinforcement-of-concrete-Weldable-reinforcing-steel-General.pdf> —
    BS EN 10080:2005.
12. <http://ponderosa.es/docs/Norma-EHE-08.pdf> — EHE-08, testo integrale,
    704 pagine.
13. <https://cdn.standards.iteh.ai/samples/34171/3a43c9a895634c6081447d5a36b0b5e5/ISO-3766-2003.pdf> —
    ISO 3766:2003, anteprima ufficiale di 11 pagine.

**Documenti di questa cartella a cui questa ricerca si appoggia**

14. [`materiali-intervallo.md`](materiali-intervallo.md) — l'intervallo dei
    parametri meccanici del calcestruzzo a classe non dichiarata, con le stesse
    citazioni di EC2 3.1.3 e NTC 11.2.10.3 verificate in una sessione precedente.
15. [`README.md`](README.md) — la convenzione numerica e il quadro di validazione
    in cui questa ricerca si inserisce.
