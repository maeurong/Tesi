# NTC 2018 e Circolare 7/2019 — i numeri per il catalogo dei materiali e per i controlli di sezione

Data: 30/08/2026. Autore della raccolta: agente di ricerca (sola lettura).
Scopo: mettere sotto un solo tetto i valori normativi di cui hanno bisogno il
catalogo dei materiali e i controlli di sezione in cemento armato, **ciascuno
col proprio articolo**, e separare ciò che la norma pubblica da ciò che si
ottiene solo calcolando. Il documento non decide nulla: dove le fonti divergono
riporta entrambe, e la §11 propone una forma di dati marcandola come
raccomandazione.

Il modello è [`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md),
che copre le stesse classi da fonti diverse. Le due letture concordano quasi
ovunque; i tre punti in cui non concordano sono elencati nella §10.2, senza
sceglierne uno.

## Convenzioni di lettura

- **[V]** = letto in questa sessione sul testo convertito che sta in
  `Norme/markdown/`, con il numero di riga del file convertito accanto.
- **[R]** = **ricostruito** da un testo che la conversione da PDF ha rotto —
  frazione appiattita, esponente andato a capo, segno di disuguaglianza
  storpiato. Ogni ricostruzione dice da che cosa è ricostruita.
- **[I]** = calcolato da me a partire da una formula [V]. Non è un dato di
  norma, ed è marcato come derivato ovunque compaia.
- **[NON TROVATO]** = cercato nel testo convertito e non trovato. Non riportato
  a memoria.

**Notazione numerica.** Vale la regola di [`README.md`](README.md) di questa
cartella: virgola decimale, punto per le migliaia, salvo dentro le citazioni
verbatim, nei numeri che sono nomi — articoli, tabelle, classi, espressioni — e
dentro i blocchi di codice. Le espressioni di norma conservano la numerazione
originale fra parentesi quadre, `[4.1.3]`, `[11.2.5]`: sono nomi.

**Le fonti sono primarie e stanno in casa.** Il testo di norma e la Circolare
sono nel repository come Markdown convertito da PDF, in `Norme/markdown/`; la
cartella `Norme/` dei PDF è esclusa da git perché è materiale di terzi. Le
dispense del corso di Tecnica delle Costruzioni stanno in `Lezioni CLS/markdown/`.
**Le NTC e la Circolare sono la fonte, le dispense sono la spiegazione**: dove un
numero sta in entrambe si cita l'articolo di norma, e la dispensa serve solo a
capire come la formula si usa e a intercettare i passaggi che la norma dà per
scontati. Chi clona il repository non ha né le une né le altre: un riferimento
alla pagina della dispensa sarebbe irrecuperabile.

---

## 0. Che cosa la conversione da PDF ha rotto, e come l'ho letto lo stesso

Questa sezione va letta prima delle altre. Il PDF della Gazzetta Ufficiale usa
un font simbolico che il convertitore ha mappato su caratteri latini a caso: le
lettere greche escono come segni che non c'entrano nulla, e chi legge il file
convertito senza saperlo trascrive numeri giusti attaccati a simboli sbagliati.

### 0.1 Il dizionario dei simboli storpiati

Ricavato leggendo lo stesso simbolo in tre o più punti diversi e in contesti in
cui il significato è obbligato [R]:

| come appare nel convertito | che cos'è | dove si vede |
|---|---|---|
| `΅` | α | `΅cc` in §4.1.2.1.1.1 = alfa con pedice cc |
| `·` , `J` | γ | `·c` = gamma con pedice c; `·s` = gamma con pedice s; `Jc` nella [4.1.6] |
| `Ή` , `H` , `İ` , `2` | ε | `Ήc2`, `Ήcu` in §4.1.2.1.2.1 |
| `Η` , `V` | σ | «modelli Η-Ή per il calcestruzzo» |
| `ȥ` | ψ | `ȥ₀ⱼ`, `ȥ₁ⱼ`, `ȥ₂ⱼ` nella Tab. 2.5.I |
| `Ώ` | λ | il coefficiente della forza di base sismica |
| `Ε` | ρ | rapporto geometrico di armatura in §7.4.6.2 |
| `Α` | ν | `Αd` = sforzo normale normalizzato |
| `Κ` , `̘` , `)` , `Ø` | Ø | il diametro di una barra |
| `ǂ` | ≤ | ovunque |
| `ǃ` | ≥ | ovunque |
| `ȉ` | · (moltiplicazione) | dentro le combinazioni di carico |
| `>` … `@` | `[` … `]` | i numeri d'espressione, `>11.2.5@` = `[11.2.5]` |

Il caso pericoloso è `·`: nel convertito è **sia** gamma **sia**, altrove, il
punto di moltiplicazione. L'ho letto come gamma solo dove porta un pedice `c`,
`s`, `G1`, `G2`, `Q` e la frase intorno dice «coefficiente parziale».

### 0.2 Le formule di cui la conversione ha perso un pezzo

Quattro, tutte ricostruite e tutte dichiarate in loco:

1. **`A_s,min`, espressione `[4.1.45]`.** Il convertito scrive
   `As,min0,26 ffctmbt� d` e manda `yk` da solo sulla riga successiva
   (`NTC 2018 2024-03-05 08_37_19.md`, righe 2379-2380). La frazione
   `f_ctm / f_yk` è stata appiattita in orizzontale e il denominatore è finito
   sotto. Ricostruzione in §6.1.
2. **L'esponente di `E_cm`, espressione `[11.2.5]`.** Il convertito manda `0,3`
   a capo *prima* della formula: `0,3` da solo, poi
   `Ecm = 22.000 � [fcm/ 10] [N/mm²]` (riga 6389). Ricostruzione in §1.1.
3. **`ε_c2` e `ε_cu` per le classi oltre C50/60.** Il convertito manda `0,53` e
   `4` a capo prima della formula (riga 2183). Sono i due esponenti.
   Ricostruzione in §4.2.
4. **Il periodo `T_1`, espressione `[7.3.6]`.** Il convertito scrive `T₁ 2 d`
   (riga 4847): il segno di radice è sparito. Ricostruzione in §9.2.

### 0.3 Il buco vero: il capitolo C7 della Circolare non c'è

Nel file `Circolare 7 2024-03-05 08_37_21.md` l'indice elenca `C7.3.3.2 ANALISI
LINEARE STATICA` (riga 829), ma **il corpo del capitolo C7 è interamente
assente**: il testo salta da `CCAPITOLO C6.` (riga 4501) a `CCAPITOLO C8.`
(riga 4867), e in mezzo ci sono solo numeri di pagina vuoti — le pagine da
«— 243 —» a «— 248 —» non portano una riga di testo.

Conseguenza pratica: **il commento della Circolare all'analisi statica lineare
non l'ho potuto leggere.** La §9 riporta perciò solo quello che sta nelle NTC.
Se serve il commento, il PDF va riconvertito.

Non è l'unico buco: il capitolo C7 mancante porta via anche i commenti alle
regole sismiche di dettaglio (C7.4.6), che nella §6.5 cito quindi dal solo testo
di norma.

---

## 1. Le classi di calcestruzzo

### 1.1 Le formule, ciascuna col proprio articolo

Sono cinque, e vanno applicate **in cascata**: ogni grandezza deriva dalla
precedente. Le NTC le raccolgono tutte nel §11.2.10, non nel §4.1.

**Da cubica a cilindrica** — §11.2.10.1, espressione `[11.2.1]`, verbatim [V]
(riga 6387):

> «Dalla resistenza cubica si passerà a quella cilindrica da utilizzare nelle
> verifiche mediante l'espressione: fck = 0,83 · Rck»

```
f_ck = 0,83 · R_ck                                        [11.2.1]
```

**Da caratteristica a media** — §11.2.10.1, espressione `[11.2.2]`, verbatim [V]:

> «è possibile passare dal valore caratteristico al valor medio della resistenza
> cilindrica mediante l'espressione fcm = fck + 8 [N/mm²]»

```
f_cm = f_ck + 8            [MPa]                          [11.2.2]
```

**La resistenza media a trazione** — §11.2.10.2, espressioni `[11.2.3a]` e
`[11.2.3b]`, verbatim [V] (riga 6389):

> «In sede di progettazione si può assumere come resistenza media a trazione
> semplice (assiale) del calcestruzzo il valore (in N/mm²): fctm = 0,30 · fck2/3
> per classi ≤ C50/60 [11.2.3a] fctm = 2,12 · ln [1+fcm/10] per classi > C50/60
> [11.2.3b]»

Il `fck2/3` del convertito è `f_ck` elevato a 2/3: l'esponente ha perso la
formattazione ma non l'ordine dei caratteri [R].

```
f_ctm = 0,30 · f_ck^(2/3)          per classi <= C50/60   [11.2.3a]
f_ctm = 2,12 · ln(1 + f_cm/10)     per classi >  C50/60   [11.2.3b]
```

**I frattili della resistenza a trazione** — §11.2.10.2, subito dopo, verbatim
[V]:

> «I valori caratteristici corrispondenti ai frattili 5% e 95% sono assunti,
> rispettivamente, pari a 0,7 fctm, ed 1,3 fctm.»

```
f_ctk       = f_ctk,0.05 = 0,7 · f_ctm
f_ctk,0.95  = 1,3 · f_ctm
```

**Nota di nomenclatura che conta.** Il §4.1.2.1.1.2 chiama `f_ctk` senza pedice
la grandezza che entra in `f_ctd`, e il §11.2.10.2 definisce il frattile 5% e il
frattile 95%. Il `f_ctk` del §4.1.2.1.1.2 è **il frattile 5%**: è l'unico dei
due che ha senso in una resistenza di progetto. Le NTC non lo dicono a lettere;
è deduzione mia [I], concorde con l'uso corrente.

Nello stesso paragrafo, la resistenza media a trazione **per flessione**,
espressione `[11.2.4]` [V]: `f_cfm = 1,2 · f_ctm`. Non serve al catalogo ma
serve allo stato limite di formazione delle fessure — §4.1.2.2.4 [V], riga 2246,
dove la tensione di prima fessurazione è `f_ctm / 1,2`, espressione `[4.1.13]`.
**Attenzione**: la `[11.2.4]` moltiplica per 1,2 e la `[4.1.13]` divide per 1,2.
Sono due grandezze diverse e il convertito le mostra a poche righe di distanza.

**Il modulo elastico** — §11.2.10.3, espressione `[11.2.5]`, verbatim [V]
(riga 6389), con l'esponente rimesso al suo posto [R]:

> «Per modulo elastico istantaneo del calcestruzzo va assunto quello secante tra
> la tensione nulla e 0,40 fcm […] In sede di progettazione si può assumere il
> valore: Ecm = 22.000 · [fcm/10]^0,3 [N/mm²]»

```
E_cm = 22000 · (f_cm / 10)**0.3    [MPa]                  [11.2.5]
```

Lo stesso paragrafo pone tre limiti al numero, tutti verbatim [V]: il valore
«dovrà essere ridotto del 20% in caso di utilizzo di aggregati grossi di
riciclo»; «tale formula non è applicabile ai calcestruzzi maturati a vapore»; e
«essa non è da considerarsi vincolante nell'interpretazione dei controlli
sperimentali delle strutture».

**Il coefficiente di Poisson** — §11.2.10.4, verbatim [V]:

> «Per il coefficiente di Poisson può adottarsi, a seconda dello stato di
> sollecitazione, un valore compreso tra 0 (calcestruzzo fessurato) e 0,2
> (calcestruzzo non fessurato).»

Cioè le NTC danno un **intervallo con due estremi che sono due modelli
diversi**, non una banda di incertezza. Per un'analisi elastica lineare non
fessurata il valore è 0,2.

**La dilatazione termica** — §11.2.10.5 [V]: valor medio 10·10⁻⁶ °C⁻¹, con
l'avvertenza esplicita che «può assumere valori anche sensibilmente diversi da
quello indicato».

**Il peso dell'unità di volume** — Tab. 3.1.I [V]. Il convertito **ha separato
l'elenco dei materiali dalla colonna dei valori** (riga 1650: i nomi in una
colonna, l'intestazione «PESO UNITÀ DI VOLUME [kN/m³]» dopo, e i numeri
mescolati in mezzo alla lista). Non riporto qui i numeri della Tab. 3.1.I da
questo file: sono già trascritti, da altra copia, in
[`materiali-intervallo.md`](materiali-intervallo.md) §2.1 e in
[`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md)
§4.3 — 24,0 kN/m³ per il calcestruzzo ordinario e 25,0 kN/m³ per l'armato. **Il
convertito non permette di confermarli né di smentirli** [NON TROVATO in forma
leggibile].

### 1.2 L'elenco delle classi

**Tab. 4.1.I, verbatim [V]** (riga 2126). La tabella **non porta valori**: è un
elenco di nomi.

> «Tab. 4.1.I – Classi di resistenza. Classe di resistenza C8/10 C12/15 C16/20
> C20/25 C25/30 C30/37 C35/45 C40/50 C45/55 C50/60 C55/67 C60/75 C70/85 C80/95
> C90/105»

E subito dopo [V]: «Oltre alle classi di resistenza riportate in Tab. 4.1.I si
possono prendere in considerazione le classi di resistenza già in uso C28/35 e
C32/40.»

Tre limiti d'uso, tutti nello stesso punto [V]:

- **Tab. 4.1.II**: classe minima C8/10 per strutture non armate o a bassa
  percentuale di armatura, **C16/20 per strutture semplicemente armate**,
  C28/35 per le precompresse.
- oltre C45/55 serve «un'apposita sperimentazione preventiva»;
- oltre C70/85 «si rinvia al caso C) del § 11.1», cioè all'autorizzazione
  ministeriale. La Circolare (riga 2465) lo dice per esteso [V]: «Per le Classi
  di resistenza superiori a C70/85 deve essere richiesta l'autorizzazione
  ministeriale mediante le procedure già stabilite per altri materiali
  "innovativi"».

### 1.3 Il punto in cui il nome della classe e la `[11.2.1]` non tornano

**Il nome della classe è una coppia convenzionale, non il risultato della
`[11.2.1]`.** Applicando `f_ck = 0,83 · R_ck` al secondo numero del nome si
ottiene un `f_ck` che **non** coincide col primo [I]:

| classe | `R_ck` dal nome | `0,83 · R_ck` | `f_ck` dal nome | scarto |
|---|---|---|---|---|
| C20/25 | 25 | 20,75 | 20 | +3,8% |
| C25/30 | 30 | 24,90 | 25 | −0,4% |
| C30/37 | 37 | 30,71 | 30 | +2,4% |
| C35/45 | 45 | 37,35 | 35 | +6,7% |
| C40/50 | 50 | 41,50 | 40 | +3,8% |

Non è un difetto della norma: la coppia cilindrica/cubica del nome è
normalizzata da UNI EN 206, e la `[11.2.1]` serve quando si **parte da un
`R_ck`** — un valore prescritto in capitolato, o misurato su cubetti — e non da
una classe.

**Conseguenza per il catalogo, ed è la ragione per cui questa sezione esiste.**
Se il catalogo si indicizza per classe, `f_ck` si legge dal nome. Se accetta un
`R_ck` libero, `f_ck` si calcola con la `[11.2.1]`. Le due strade danno numeri
diversi fino al 7%, e **l'oracolo della §7 usa la seconda**: parte da
`R_ck = 30` e ottiene `f_ck = 24,9`, non 25. Un catalogo che facesse le due cose
in silenzio produrrebbe due `f_cd` diversi per lo stesso calcestruzzo.

### 1.4 La tabella dei valori — tutta derivata, nessuna riga letta

**Nessuno di questi numeri è pubblicato nelle NTC**: la Tab. 4.1.I porta solo i
nomi, e il §11.2.10 porta solo le formule. La tabella è quindi **interamente
[I]**, calcolata dalle `[11.2.2]`, `[11.2.3a/b]`, `[11.2.5]` in Python 3 il
30/08/2026, con `f_ck` letto dal nome della classe.

| classe | `R_ck` [MPa] | `f_ck` [MPa] | `f_cm` [MPa] | `f_ctm` [MPa] | `f_ctk` 5% [MPa] | `f_ctk` 95% [MPa] | `E_cm` [MPa] | `f_cd` [MPa] |
|---|---|---|---|---|---|---|---|---|
| C8/10 | 10 | 8 | 16 | 1,20 | 0,84 | 1,56 | 25.331 | 4,53 |
| C12/15 | 15 | 12 | 20 | 1,57 | 1,10 | 2,04 | 27.085 | 6,80 |
| C16/20 | 20 | 16 | 24 | 1,90 | 1,33 | 2,48 | 28.608 | 9,07 |
| C20/25 | 25 | 20 | 28 | 2,21 | 1,55 | 2,87 | 29.962 | 11,33 |
| C25/30 | 30 | 25 | 33 | 2,56 | 1,80 | 3,33 | 31.476 | 14,17 |
| C28/35 | 35 | 28 | 36 | 2,77 | 1,94 | 3,60 | 32.308 | 15,87 |
| C30/37 | 37 | 30 | 38 | 2,90 | 2,03 | 3,77 | 32.837 | 17,00 |
| C32/40 | 40 | 32 | 40 | 3,02 | 2,12 | 3,93 | 33.346 | 18,13 |
| C35/45 | 45 | 35 | 43 | 3,21 | 2,25 | 4,17 | 34.077 | 19,83 |
| C40/50 | 50 | 40 | 48 | 3,51 | 2,46 | 4,56 | 35.220 | 22,67 |
| C45/55 | 55 | 45 | 53 | 3,80 | 2,66 | 4,93 | 36.283 | 25,50 |
| C50/60 | 60 | 50 | 58 | 4,07 | 2,85 | 5,29 | 37.278 | 28,33 |
| C55/67 | 67 | 55 | 63 | 4,21 | 2,95 | 5,48 | 38.214 | 31,17 |
| C60/75 | 75 | 60 | 68 | 4,35 | 3,05 | 5,66 | 39.100 | 34,00 |
| C70/85 | 85 | 70 | 78 | 4,61 | 3,23 | 5,99 | 40.743 | 39,67 |
| C80/95 | 95 | 80 | 88 | 4,84 | 3,39 | 6,29 | 42.244 | 45,33 |
| C90/105 | 105 | 90 | 98 | 5,04 | 3,53 | 6,56 | 43.631 | 51,00 |

Sei cose da sapere prima di usarla.

1. **La colonna `f_cd` anticipa la §5**: è `0,85 · f_ck / 1,5`, e vale solo per
   il caso ordinario. Le riduzioni della §5.4 non sono applicate.
2. **La riga C8/10 è fuori dal dominio della formula del modulo.** La classe sta
   nelle NTC ma non nella Tabella 3.1 di UNI EN 1992-1-1, da cui la `[11.2.5]`
   proviene. Il valore è un'estrapolazione [I] e va marcato come tale.
3. **La discontinuità a C50/60 è nella norma, non nel conto.** Passando dalla
   `[11.2.3a]` alla `[11.2.3b]` la `f_ctm` cresce molto più lentamente: da
   C50/60 a C90/105 il `f_ck` quasi raddoppia e la `f_ctm` sale solo del 24%.
4. **C28/35 e C32/40 sono nella tabella perché le NTC le ammettono in via
   residuale**, non perché stiano in Tab. 4.1.I. La Circolare (riga 2465)
   aggiunge una restrizione che le NTC non hanno [V]: «Ai soli fini della
   valutazione della durabilità, dette classi di resistenza C28/35 e C32/40,
   possono essere adottate per le classi di esposizione ambientale in cui sono
   prescritti i valori minimi delle classi di resistenza immediatamente
   inferiori.»
5. **`E_cm` è un modulo secante fra 0 e `0,40 · f_cm`**, non tangente
   all'origine, ed è il numero da mettere in un'analisi elastica lineare — §11.2.10.3 [V].
6. **Una divergenza aperta con la ricerca precedente**: per la C8/10,
   [`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md)
   §4.2 pubblica `E_cm` = 25.393 MPa; io ottengo **25.331 MPa**. Tutte le altre
   sedici righe coincidono cifra per cifra. Vedi §10.2.

---

## 2. Gli acciai da armatura

### 2.1 Due classi, e una sola resistenza

NTC 2018 §11.3.2.1, verbatim [V] (riga 6470):

> «L'acciaio per calcestruzzo armato B450C è caratterizzato dai seguenti valori
> nominali della tensione di snervamento e della tensione a carico massimo da
> utilizzare nei calcoli: Tab. 11.3.Ia — f y nom 450 N/mm², f t nom 540 N/mm²»

§11.3.2.2, verbatim [V] (riga 6478):

> «L'acciaio per calcestruzzo armato B450A, caratterizzato dai medesimi valori
> nominali della tensione di snervamento e della tensione a carico massimo
> dell'acciaio B450C, deve rispettare i requisiti indicati nella seguente
> Tab. 11.3.Ic.»

**Le due classi hanno lo stesso snervamento e lo stesso carico massimo
nominali.** Differiscono per duttilità e per diametri ammessi, non per
resistenza. È l'equivoco più facile da commettere in un menù a tendina.

### 2.2 I requisiti, dalle Tab. 11.3.Ib e Ic

Trascritte [V] con i segni di disuguaglianza ricostruiti dal dizionario della
§0.1 (`ǃ` = ≥, `ǂ` = ≤) [R]:

| caratteristica | B450C (Tab. 11.3.Ib) | B450A (Tab. 11.3.Ic) | frattile |
|---|---|---|---|
| `f_yk` | ≥ `f_y nom` = 450 N/mm² | ≥ `f_y nom` = 450 N/mm² | 5,0% |
| `f_tk` | ≥ `f_t nom` = 540 N/mm² | ≥ `f_t nom` = 540 N/mm² | 5,0% |
| `(f_t/f_y)_k` | ≥ 1,15 e < 1,35 | ≥ 1,05 | 10,0% |
| `(f_y/f_y nom)_k` | ≤ 1,25 | ≤ 1,25 | 10,0% |
| allungamento `(A_gt)_k` | ≥ 7,5% | ≥ 2,5% | 10,0% |

**Le due righe che contano per la duttilità sono le ultime due**, ed è dove sta
tutta la differenza fra le classi:

- il **rapporto di sovraresistenza** `k = (f_t/f_y)_k`: il B450C è chiuso in un
  intervallo (fra 1,15 e 1,35), il B450A ha solo un minimo (1,05). Il tetto
  superiore del B450C non è un dettaglio: serve alla gerarchia delle resistenze,
  perché un acciaio troppo sovraresistente sposta la crisi dove non deve;
- l'**allungamento uniforme al carico massimo** `(A_gt)_k`: 7,5% contro 2,5%,
  cioè un fattore tre.

**`ε_uk` è `(A_gt)_k`**, e lo dice la norma per esteso: §4.1.2.1.2.2, verbatim
[V] (riga 2232):

> «modelli definiti in base al valore di progetto εud = 0,9 εuk (εuk = (Agt)k)
> della deformazione uniforme ultima, al valore di progetto della tensione di
> snervamento fyd ed al rapporto di sovraresistenza k = (ft / fy)k
> (Tab. 11.3.Ia-b)»

Da cui, direttamente [I]:

| | B450C | B450A |
|---|---|---|
| `ε_uk` = `(A_gt)_k` | 0,075 | 0,025 |
| `ε_ud` = 0,9 · `ε_uk` | **0,0675** | **0,0225** |

Il valore 0,0675 per il B450C **si ritrova in due materiali del corso**, ed è
una conferma incrociata: il file `Domini_NM_DM2018 2024-03-05 08_37_22.md` pone
«εsu = 0.0675» fra le ipotesi dei domini M-N [V], e il file
`Tabelle_flessione_SL_2018 2024-03-05 08_37_32.md` fa partire ogni tabella dalla
riga `ε(acc.) = 67,500 · 10⁻³` [V]. Nessuno dei due dice da dove viene: viene
dalla `0,9 · 7,5%` del §4.1.2.1.2.2.

### 2.3 Il modulo elastico: le NTC non lo danno, e le due fonti che lo danno divergono

**Nelle NTC 2018 il modulo elastico dell'acciaio da armatura non c'è.** Il
§11.3.2 non lo pubblica; il §4.1.2.1.2.2 definisce i diagrammi senza citarlo; il
§4.1.4 lo nomina come parametro dell'analisi non lineare («E s modulo elastico
dell'armatura», riga 2368) senza assegnargli un valore. [NON TROVATO nelle NTC].

**La Circolare lo dà, e dà 210.000.** Circolare 7/2019, §C4.1.2.2.5 (riga
2664), verbatim [V]:

> «Nei calcoli per azioni di breve durata può assumersi il valore del modulo di
> elasticità del calcestruzzo Ec dato dalla [11.2.5] delle NTC, ed un modulo di
> elasticità dell'acciaio Es pari a 210.000 N/mm². Tale valore può essere
> opportunamente ridotto nel caso di fili, trecce e trefoli da calcestruzzo
> armato precompresso.»

Nello stesso capoverso [V]: «si può assumere un coefficiente di omogeneizzazione
n fra i moduli di elasticità di acciaio e calcestruzzo, pari a n = 15».

**Le altre due fonti danno 200.000.**
[`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md)
§3.3 riporta UNI EN 1992-1-1 §3.2.7(4) verbatim, 200 GPa; e il file
`Domini_NM_DM2018 2024-03-05 08_37_22.md` del corso pone «Es = 200000 N/mm²» [V].

**La divergenza è del 5% e non la sciolgo.** Va notato però *dove* i due valori
compaiono: il 210.000 della Circolare sta in un paragrafo sulle **tensioni in
esercizio** (SLE), il 200.000 di UNI EN 1992-1-1 è il valore generale. E
**l'oracolo della §7 usa 200.000**: usare 210.000 sposterebbe `k_bil` da 0,641 a
0,653 e `μ_bil` da 1,872% a 1,905% [I]. La scelta è di Mario; vedi §10.2.

### 2.4 I diametri ammessi

NTC 2018 §11.3.2.4, verbatim [V] (righe 6484 e 6487):

> «Tutti i prodotti sono caratterizzati dal diametro Ø della barra tonda liscia
> equipesante, calcolato nell'ipotesi che la densità dell'acciaio sia pari a
> 7,85 kg/dm³. Gli acciai B450C, di cui al § 11.3.2.1, possono essere impiegati
> in barre di diametro Ø compreso tra 6 e 40 mm.»
> «Per gli acciai B450A, di cui al § 11.3.2.2 il diametro Ø delle barre deve
> essere compreso tra 5 e 10 mm. L'uso di acciai forniti in rotolo è ammesso,
> esclusivamente per impieghi strutturali, per diametri Ø non superiori a 16 mm
> per gli acciai B450C e diametri Ø non superiori a 10 mm per gli acciai B450A.»

| prodotto | B450C | B450A | articolo |
|---|---|---|---|
| barre | 6 ≤ Ø ≤ 40 mm | 5 ≤ Ø ≤ 10 mm | §11.3.2.4 |
| rotoli | Ø ≤ 16 mm | Ø ≤ 10 mm | §11.3.2.4 |
| reti e tralicci, elementi base | 6 ≤ Ø ≤ 16 mm | 5 ≤ Ø ≤ 10 mm | §11.3.2.5 |

Più tre regole che stanno lì accanto e che un catalogo farebbe bene a portare:

- **il rapporto fra i diametri di una rete**, espressione `[11.3.1]` [V]:
  `Ø_min / Ø_max ≥ 0,6`;
- **l'interasse delle barre di rete o traliccio** non deve superare 330 mm nelle
  due direzioni — §11.3.2.5 [V];
- **oltre Ø 32 mm servono cautele** negli ancoraggi e nelle sovrapposizioni —
  §4.1.6.1.4 [V].

**Le NTC danno un intervallo, non una serie.** Quali diametri esistano davvero
dentro `6 ≤ Ø ≤ 40` è cosa di UNI EN 10080, non delle NTC: la serie
commerciale è già trascritta in
[`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md)
§2.1, e questa ricerca non l'ha ricontrollata. [NON TROVATO nelle NTC].

### 2.5 Dove le NTC obbligano al B450C

Non è una prescrizione di catalogo ma di impiego, e cambia quale classe il
programma deve offrire come predefinita in zona sismica. §7.4.2.2, verbatim
[V] (riga 4960):

> «Per le strutture si deve utilizzare acciaio B450C (v. § 11.3.2.1). E' consentito
> l'utilizzo di acciai di tipo B450A, con diametri compresi tra 5 e 10 mm, per le
> reti e i tralicci; se ne consente inoltre l'uso per l'armatura trasversale
> unicamente se è rispettata almeno una delle seguenti condizioni: elementi in
> cui è impedita la plasticizzazione mediante il rispetto del criterio di
> gerarchia delle resistenze, elementi secondari di cui al §7.2.3, strutture con
> comportamento non dissipativo di cui al §7.2.2.»

Il §7.6.1.2 ripete la stessa cosa per le strutture prefabbricate [V].

---

## 3. Le resistenze di progetto — e il passaggio che si dimentica

### 3.1 La formula del calcestruzzo, per esteso

NTC 2018 §4.1.2.1.1.1, espressione `[4.1.3]`, verbatim [V] (riga 2161), coi
simboli greci ricostruiti dal dizionario della §0.1 [R]:

> «Per il calcestruzzo la resistenza di progetto a compressione, fcd, é:
> fcd = αcc · fck / γc [4.1.3] dove: αcc è il coefficiente riduttivo per le
> resistenze di lunga durata; γc è il coefficiente parziale di sicurezza
> relativo al calcestruzzo; fck è la resistenza caratteristica cilindrica a
> compressione del calcestruzzo a 28 giorni. Il coefficiente γc è pari ad 1,5.
> Il coefficiente αcc è pari a 0,85.»

```
f_cd = alpha_cc * f_ck / gamma_c            [4.1.3]
     con alpha_cc = 0,85  e  gamma_c = 1,5
```

**L'utente ha ragione, e la norma gli dà ragione a lettere.** Il coefficiente di
lunga durata non è un'aggiunta di prassi: sta dentro la `[4.1.3]`, ha un nome
(«coefficiente riduttivo per le resistenze di lunga durata») e un valore fissato
(0,85). Chi scrive `f_cd = f_ck / 1,5` ottiene un valore **del 17,6% più alto**
del vero [I], e sbaglia dalla parte insicura.

La Circolare conferma entrambi i numeri e aggiunge da dove viene la differenza
con l'Eurocodice, verbatim [V] (riga 2465):

> «Per le verifiche allo Stato Limite Ultimo (SLU), il coefficiente parziale di
> sicurezza per il calcestruzzo γc resta fissato a 1,5, in accordo con la UNI EN
> 1992; il coefficiente αcc resta fissato a 0,85, a differenza di quello proposto
> dalla UNI EN 1992.»

Cioè: `γ_c` è quello europeo, `α_cc` **no**. Un programma che offrisse «modalità
Eurocodice» dovrebbe cambiare `α_cc` e non `γ_c`.

### 3.2 C'è anche un secondo passaggio, e sta più a monte

**Sì, c'è dell'altro, e non è un coefficiente: è la scala di partenza.** La
`[4.1.3]` prende `f_ck`, cioè la **resistenza cilindrica**. Se il dato di
partenza è un `R_ck` — che è quello che si legge in capitolato, sulle prove di
accettazione e nella designazione della classe — allora prima della `[4.1.3]`
va applicata la `[11.2.1]`, e la catena completa è a **tre** fattori:

```
f_cd = alpha_cc * (0,83 * R_ck) / gamma_c = 0,85 * 0,83 * R_ck / 1,5
     = 0,4703 * R_ck                                      [I]
```

La dispensa `Lezioni 35-36 - Analisi allo SLU della sezione inflessa - NTC 2018.md`
scrive esattamente questa catena, verbatim [V]:

> «f cd = 0.85 × (R ck × 0.83) / 1.5 […] In cui il coefficiente αcc = 0.85 tiene
> conto della lunga durata di applicazione dei carichi, f ck è la resistenza
> caratteristica cilindrica, che si ottiene da quella cubica tramite il
> coefficiente di passaggio 0.83 ed il coefficiente 1.5 è il coefficiente
> parziale di sicurezza per il calcestruzzo.»

**È il passaggio che la norma dà per scontato**, perché il §4.1.2.1.1.1 e il
§11.2.10.1 stanno in due capitoli diversi e nessuno dei due rimanda all'altro
per questo. Un catalogo indicizzato per classe non lo incontra mai — legge
`f_ck` dal nome; un catalogo che accetta un `R_ck` libero lo incontra sempre.
Vedi §1.3 per lo scarto fra le due strade.

### 3.3 Le altre due formule

**Trazione** — §4.1.2.1.1.2, espressione `[4.1.4]`, verbatim [V] (riga 2162):

> «La resistenza di progetto a trazione, fctd, vale: fctd = fctk / γc [4.1.4]
> […] Il coefficiente γc assume il valore 1,5.»

```
f_ctd = f_ctk / gamma_c            [4.1.4]     con f_ctk = 0,7 * f_ctm
```

**Nella `[4.1.4]` non c'è nessun `α_cc`.** La riduzione di lunga durata vale per
la compressione e non per la trazione: applicarla anche qui sarebbe un errore
simmetrico a quello di dimenticarla nella `[4.1.3]`.

**Acciaio** — §4.1.2.1.1.3, espressione `[4.1.5]`, verbatim [V] (riga 2163):

> «La resistenza di progetto dell'acciaio fyd è riferita alla tensione di
> snervamento ed il suo valore è dato da: fyd = fyk / γs [4.1.5] […] Il
> coefficiente γs assume sempre, per tutti i tipi di acciaio, il valore 1,15.»

```
f_yd = f_yk / gamma_s              [4.1.5]     con gamma_s = 1,15
```

**Neanche qui c'è un `α`**, e la parola «sempre» è nel testo di norma: 1,15 vale
per il B450A come per il B450C, e per gli acciai da precompressione.

Per il B450 [I]: `f_yd` = 450 / 1,15 = **391,30 MPa**; e la deformazione di
snervamento di progetto `ε_yd` = `f_yd` / `E_s` = 391,30 / 200000 =
**1,9565 · 10⁻³**.

### 3.4 I casi in cui la resistenza va ridotta ancora

Cercati uno per uno nel testo convertito. Sono cinque, e uno è quello dei getti
in opera che il brief chiede.

**a) Elementi piani sottili gettati in opera** — §4.1.2.1.1.1 e §4.1.2.1.1.2,
verbatim [V]:

> «Nel caso di elementi piani (solette, pareti, …) gettati in opera con
> calcestruzzi ordinari e con spessori minori di 50 mm, la resistenza di
> progetto a compressione va ridotta a 0,80 fcd.»

e, parola per parola uguale, «la resistenza di progetto a trazione va ridotta a
0,80 fctd». Il fattore è **0,80**, la soglia è **50 mm di spessore**, e la
condizione è **gettati in opera**: un elemento prefabbricato dello stesso
spessore non ci ricade.

**b) `γ_c` ridotto per produzione controllata** — §4.1.2.1.1.1, verbatim [V]:

> «Il coefficiente γc può essere ridotto da 1,5 a 1,4 per produzioni
> continuative di elementi o strutture, soggette a controllo continuativo del
> calcestruzzo dal quale risulti un coefficiente di variazione (rapporto tra
> scarto quadratico medio e valor medio) della resistenza non superiore al 10%.
> Le suddette produzioni devono essere inserite in un sistema di qualità di cui
> al § 11.8.3.»

È l'unica riduzione **favorevole**: +7,1% su `f_cd` [I]. Non si applica a un
getto in opera qualunque.

**c) Calcestruzzo non armato o debolmente armato** — §4.1.11.1, verbatim [V]
(riga 2454): «fct1d = 0,85 fctd è la resistenza a trazione di progetto per
calcestruzzo non armato o debolmente armato». Il §4.1.11 definisce «a bassa
percentuale di armatura» come meno dell'armatura minima, oppure meno di 0,3 kN
di acciaio per metro cubo [V].

**d) Aggregati grossi di riciclo** — §11.2.10.2 e §11.2.10.3, verbatim [V]:
`f_ctm` «ridotto del 10%», `E_cm` «ridotto del 20%», entro i limiti della
Tab. 11.2.III.

**e) Bassa qualità accertata in opera** — §11.2.6, verbatim [V] (riga 6342):

> «Il valore caratteristico della resistenza del calcestruzzo in opera (definita
> come resistenza caratteristica in situ, Rckis o fckis) è in genere minore del
> valore della resistenza caratteristica assunta in fase di progetto Rck o fck.
> Per i soli aspetti relativi alla sicurezza strutturale e senza pregiudizio
> circa eventuali carenze di durabilità, è accettabile un valore caratteristico
> della resistenza in situ non inferiore all'85% della resistenza caratteristica
> assunta in fase di progetto.»

Cioè: **la soglia di accettabilità del calcestruzzo in opera è 0,85 · R_ck**, e
sotto quella soglia il §11.8.3.1 [V] impone «un controllo teorico e/o
sperimentale della sicurezza della struttura interessata […] sulla base della
resistenza ridotta del calcestruzzo». La norma non dà una formula: dice di
rifare il conto col numero misurato.

**f) Costruzioni esistenti — i fattori di confidenza.** Sono un'altra cosa
ancora, e non stanno nel §4: si applicano ai **valori medi** delle resistenze,
non ai caratteristici, e valgono per il Capitolo 8. Circolare Tab. C8.5.IV [V]
(riga 5034 e segg.): FC = 1,35 per LC1, 1,2 per LC2, 1 per LC3. Li segnalo
perché una tesi che modella un edificio esistente li incontra, ma non fanno
parte del catalogo dei materiali nuovi.

---

## 4. I legami costitutivi

### 4.1 Che cosa la norma dà, e che cosa non dà

NTC 2018 §4.1.2.1.2.1, verbatim [V] (righe 2180-2183):

> «Per il diagramma tensione-deformazione del calcestruzzo è possibile adottare
> opportuni modelli rappresentativi del reale comportamento del materiale,
> definiti in base alla resistenza di progetto fcd e alla deformazione ultima di
> progetto εcu. […] In Fig. 4.1.1 sono rappresentati i modelli σ-ε per il
> calcestruzzo: (a) parabola-rettangolo; (b) triangolo-rettangolo; (c)
> rettangolo (stress block). In particolare, per le classi di resistenza pari o
> inferiore a C50/60 si può porre: εc2 = 0,20% εcu = 0,35% εc3 = 0,175%
> εc4 = 0,07%»

**Quello che la norma dà**: i nomi dei tre modelli e i valori limite delle
deformazioni. **Quello che la norma non dà**: la forma analitica di nessuno dei
tre, e in particolare l'esponente della parabola. [NON TROVATO nelle NTC né,
per la parte ordinaria, nella Circolare — il §C4.1.12.1.3.1 della Circolare
(riga 2806) mostra la stessa figura ma per i **calcestruzzi di aggregati
leggeri**, che sono un altro §.]

**Una trappola di nomenclatura.** Le NTC scrivono `ε_cu` senza il 2; UNI EN
1992-1-1 scrive `ε_cu2` per la deformazione ultima del **parabola-rettangolo** e
`ε_cu3` per quella del **triangolo-rettangolo** e dello stress block. Nelle NTC
il pedice distingue il modello solo per la deformazione di picco (`ε_c2` per la
parabola, `ε_c3` per il triangolo, `ε_c4` per lo stress block) e non per quella
ultima, che è unica. Sono la stessa cosa per le classi fino a C50/60, dove tutti
e tre valgono 0,35%; un codice che si aspetta due valori diversi legge male le
NTC.

Per le classi fino a C50/60, quindi:

```
eps_c2  = 0,0020        # 0,20 %   -- picco del parabola-rettangolo
eps_cu  = 0,0035        # 0,35 %   -- deformazione ultima
eps_c3  = 0,00175       # 0,175 %  -- picco del triangolo-rettangolo
eps_c4  = 0,0007        # 0,07 %   -- inizio dello stress block
```

E una regola che vale per tutti [V]: «Per sezioni o parti di sezioni soggette a
distribuzioni di tensione di compressione approssimativamente uniformi, si
assume per la deformazione ultima di progetto il valore εc2 anziché εcu.» È il
caso della compressione centrata, e senza di essa il dominio M-N ha il vertice
sbagliato.

### 4.2 Le classi oltre C50/60

Stesso §4.1.2.1.2.1, verbatim [V] con i due esponenti rimessi a posto [R] — il
convertito li ha mandati a capo prima della formula, `0,53` e `4`:

```
eps_c2  = 0,20%  + 0,0085% * (f_ck - 50)**0.53
eps_cu  = 0,26%  + 3,5%    * ((90 - f_ck)/100)**4
eps_c3  = 0,175% + 0,055%  * (f_ck - 50)/40
eps_c4  = 0,2 * eps_cu
```

Valori [I], calcolati dalle formule sopra:

| `f_ck` | `ε_c2` | `ε_cu` | `ε_c3` | `ε_c4` |
|---|---|---|---|---|
| 55 | 0,220% | 0,313% | 0,182% | 0,063% |
| 60 | 0,229% | 0,288% | 0,189% | 0,058% |
| 70 | 0,242% | 0,266% | 0,202% | 0,053% |
| 80 | 0,252% | 0,260% | 0,216% | 0,052% |
| 90 | 0,260% | 0,260% | 0,230% | 0,052% |

A `f_ck` = 90 i due valori coincidono: il tratto rettangolare del diagramma
sparisce e resta la sola parabola. La ricostruzione degli esponenti si regge
anche su questo — con esponenti diversi la coincidenza a 90 non uscirebbe.

**L'esponente della parabola per le classi oltre C50/60 resta [NON TROVATO].**
Le NTC danno le deformazioni e non l'esponente; per le classi fino a C50/60
l'esponente si ricava (§4.3), per quelle oltre no.

### 4.3 L'esponente della parabola, ricavato e verificato in casa

La forma che tutti i testi usano è

```
sigma_c = f_cd * (1 - (1 - eps/eps_c2)**n)      per 0 <= eps <= eps_c2
sigma_c = f_cd                                   per eps_c2 < eps <= eps_cu
```

con `n` = 2 per le classi fino a C50/60. **Le NTC non lo scrivono**, e neanche
le dispense: la `Lezioni 35-36` dice soltanto [V] «Il tratto parabolico del
diagramma σ-ε si estende nell'intervallo di deformazioni compreso fra lo 0 ed il
2 ‰, in corrispondenza del quale si raggiunge il valore di picco. Il tratto
orizzontale si estende tra il 2 ‰ ed il 3.5 ‰».

**L'esponente si può però ricavare da una fonte che sta nel repository**, ed è
la verifica più solida di tutto questo documento. Il file
`Diagramma_Parabola_rettangolo 2024-03-05 08_37_13.md` tabula, per ogni
deformazione massima da 0 a 3,5 ‰, il **coefficiente di riempimento** α del
diagramma e la **posizione del baricentro** δ = `y_G`/`y_c`, attribuendoli al
Bollettino CEB n. 123 [V].

Ho ricalcolato quei due coefficienti per integrazione numerica del legame sopra
con `n = 2` e `ε_c2` = 2 ‰ (Python 3, regola dei trapezi con 400.000 intervalli,
30/08/2026) [I]:

| `ε_max` [‰] | α tavola CEB [V] | α ricalcolato [I] | β tavola CEB [V] | β ricalcolato [I] |
|---|---|---|---|---|
| 3,5 | 0,8095 | 0,8095 | 0,4160 | 0,4160 |
| 3,0 | 0,7778 | 0,7778 | 0,4048 | 0,4048 |
| 2,6 | 0,7436 | 0,7436 | 0,3939 | 0,3939 |
| 2,0 | 0,6667 | 0,6667 | 0,3750 | 0,3750 |
| 1,5 | 0,5625 | 0,5625 | 0,3611 | 0,3611 |
| 1,2 | 0,4800 | 0,4800 | 0,3542 | 0,3542 |
| 1,0 | 0,4167 | 0,4167 | 0,3500 | 0,3500 |
| 0,5 | 0,2292 | 0,2292 | 0,3409 | 0,3409 |
| 0,1 | 0,0492 | 0,0492 | 0,3347 | 0,3347 |

**Nove punti su nove, quattro cifre decimali, sia sul diagramma completo sia sui
tronchi incompleti.** L'esponente è 2 [I]. Con `n` = 1,5 o `n` = 3 nessuna
colonna tornerebbe.

Per il diagramma **completo** (`ε_max` = `ε_cu` ≥ `ε_c2`) i due coefficienti
hanno forma chiusa [I]:

```
alpha = 1 - eps_c2 / (3 * eps_cu)      = 1 - 2/(3*3,5) = 0,809524
```

e il valore 0,4160 di β è quello che la dispensa `Lezioni 35-36` usa
arrotondato a 0,416 [V]. Il valore 0,81 che la stessa dispensa usa per α è
l'arrotondamento di 0,809524 [I].

### 4.4 Il legame dell'acciaio

NTC 2018 §4.1.2.1.2.2, verbatim [V] (riga 2233): «In Fig. 4.1.3 sono
rappresentati i modelli σ-ε per l'acciaio: (a) bilineare finito con
incrudimento; (b) elastico-perfettamente plastico indefinito.»

Anche qui la norma dà i **nomi** e i **parametri** — `ε_ud` = 0,9 `ε_uk`, `f_yd`,
`k = (f_t/f_y)_k` — e non le equazioni. La forma è però obbligata dai parametri
[I]:

```
eps_yd = f_yd / E_s

# (b) elastico-perfettamente plastico, ramo plastico indefinito
sigma_s(eps) = E_s * eps                  se |eps| <= eps_yd
sigma_s(eps) = f_yd * sign(eps)           se |eps| >  eps_yd

# (a) bilineare finito con incrudimento, troncato a eps_ud
sigma_s(eps) = E_s * eps                  se |eps| <= eps_yd
sigma_s(eps) = f_yd + (k*f_yd - f_yd) * (|eps| - eps_yd)/(eps_ud - eps_yd)
                                          se eps_yd < |eps| <= eps_ud
# non definito oltre eps_ud: il modello (a) e' *finito*
```

Il valore di picco del ramo incrudente è `k · f_yd` con `k = (f_t/f_y)_k`. Le
NTC non scrivono l'equazione della retta [NON TROVATO]; che il ramo vada da
(`ε_yd`, `f_yd`) a (`ε_ud`, `k·f_yd`) è deduzione mia [I] dalla frase del
§4.1.2.1.2.2 che elenca esattamente quei tre parametri e nessun altro.

Valori numerici, con `E_s` = 200.000 MPa (vedi la divergenza della §2.3) [I]:

| | B450C | B450A |
|---|---|---|
| `f_yd` | 391,30 MPa | 391,30 MPa |
| `ε_yd` | 1,9565·10⁻³ | 1,9565·10⁻³ |
| `ε_ud` | 0,0675 | 0,0225 |
| `k` di progetto | 1,15 ≤ k < 1,35 | k ≥ 1,05 |

**Il modello (b) è quello che la dispensa usa**, e lo dice con parole che vale la
pena ripetere perché spiegano il perché [V], `Lezioni 35-36`: «Il diagramma di
calcolo dell'acciaio è di tipo elasto-plastico e si ricava da quello
caratteristico effettuando un'affinità parallelamente alla tangente all'origine
nel rapporto 1/γs […] Il diagramma si estende convenzionalmente in modo
indefinito secondo l'asse ε.»

Con il modello (b), `ε_ud` **non entra nel conto della resistenza**: entra solo
se si usa il modello (a) o se si vuole un limite di duttilità. Questo spiega
perché nella §7 la sezione bilanciata si calcola senza mai nominare `ε_ud`.

---

## 5. La sezione bilanciata

### 5.1 «Bilanciata» non è una parola della norma

La cerco nei due file convertiti: **zero occorrenze** di «bilanciat*» sia nelle
NTC sia nella Circolare. Non è un termine normativo [NON TROVATO].

Quello che le NTC danno sono le **ipotesi di base**, §4.1.2.3.4.1, verbatim [V]
(riga 2286):

> «si adottano le seguenti ipotesi: – conservazione delle sezioni piane; –
> perfetta aderenza tra acciaio e calcestruzzo; – deformazione iniziale
> dell'armatura di precompressione considerata nelle relazioni di congruenza
> della sezione. – resistenza a trazione del calcestruzzo nulla.»

La definizione di rottura bilanciata è della **dispensa**, `Lezioni 35-36`,
verbatim [V]: una sezione «di cui sia nota la modalità di crisi per rottura
bilanciata, nella quale si verificano simultaneamente la deformazione massima
del calcestruzzo compresso e l'incipiente snervamento dell'acciaio teso».

Cioè, in formule: `ε_c` = `ε_cu` **e** `ε_s` = `ε_yd` nella stessa sezione.

### 5.2 Come si ricava `k_bil`

Dalla sola similitudine dei triangoli del diagramma lineare delle deformazioni —
è l'ipotesi 1 del §4.1.2.3.4.1 e non serve altro [I], seguendo la dispensa:

```
x_bil / d = eps_cu / (eps_cu + eps_yd)
k_bil     = eps_cu / (eps_cu + f_yd/E_s)
```

`k_bil` **non dipende dalla classe del calcestruzzo**: dipende solo da `ε_cu`
(che per le classi fino a C50/60 è 0,35% per tutte), da `f_yk`, da `γ_s` e da
`E_s`. Per il B450 vale lo stesso numero per B450A e B450C, perché `f_yk` è lo
stesso.

Da lì l'equilibrio alla traslazione, `C = T`, col coefficiente di riempimento
della §4.3:

```
C = alpha * f_cd * b * x_bil = alpha * f_cd * k_bil * b * d
T = A_s * f_yd
mu_bil = A_s / (b*d) = alpha * f_cd * k_bil / f_yd
```

`μ_bil` è quindi una **percentuale geometrica** — area di armatura su `b·d` — e
non meccanica. La percentuale meccanica corrispondente è
`omega_bil = mu_bil * f_yd / f_cd = alpha * k_bil` [I], che per i valori
dell'oracolo vale 0,809524 · 0,64143 = **0,5192** e non dipende dalla classe del
calcestruzzo. È lo stesso fatto detto in un'altra unità.

E il braccio delle forze interne, dalla dispensa [V]: «la risultante di
compressione dista dal lembo superiore della sezione di 0.416 y_bil», cioè
`z = d · (1 - 0,416 · k_bil)`, dove 0,416 è il β della tavola CEB verificato
nella §4.3.

### 5.3 L'oracolo del progetto: torna

Dati: `R_ck` = 30, acciaio B450C. Attesi: `f_cd` = 14,11 MPa, `k_bil` = 0,641,
`μ_bil` ≈ 1,87%.

Rifatto il conto passo per passo [I], Python 3, 30/08/2026:

| passo | formula | conto | risultato |
|---|---|---|---|
| 1 | `[11.2.1]` | `f_ck` = 0,83 · 30 | 24,90 MPa |
| 2 | `[4.1.3]` | `f_cd` = 0,85 · 24,90 / 1,5 | **14,110 MPa** |
| 3 | `[4.1.5]` | `f_yd` = 450 / 1,15 | 391,3043 MPa |
| 4 | — | `ε_yd` = 391,3043 / 200000 | 1,95652·10⁻³ |
| 5 | §5.2 | `k_bil` = 0,0035 / (0,0035 + 0,00195652) | **0,641434** |
| 6 | §4.3 | α = 1 − 2/(3·3,5) | 0,809524 |
| 7 | §5.2 | `μ_bil` = 0,809524 · 14,110 · 0,641434 / 391,3043 | **0,018724 = 1,872%** |

**Torna, e torna in tutti e sette i passi.**

- `f_cd` = 14,110 MPa: coincide **esattamente** col valore atteso, non
  approssimativamente — 0,85·0,83·30/1,5 dà 14,11 senza arrotondamenti.
- `k_bil` = 0,641434, che a tre decimali è 0,641: coincide.
- `μ_bil` = 1,872% con α esatto, **1,873%** con α = 0,81 come lo arrotonda la
  dispensa. L'atteso 1,87% è coerente con entrambi. Lo scarto fra le due
  varianti di α è dello 0,06%: sotto la terza cifra, quindi irrilevante — ma un
  test che confrontasse `μ_bil` a cinque decimali dovrebbe dichiarare **quale**
  α usa.

Il conto della dispensa, verbatim [V], è identico riga per riga:

> «f cd = 30 × 0.83 × 0.85 / 1.5 = 14.11 N/mm² ; k bil = 0.0035 / (0.0035 + 450
> / (1.15 × 200000)) = 0.641 ; μ bil = α f cd k bil / f yd = 0.81 × 14.11 ×
> 0.641 / (450/1.15) ≈ 0.0187 = 1.87 %»

**E c'è una terza conferma, indipendente dalla dispensa e dal mio conto.** Il
file `Tabelle_flessione_SL_2018 2024-03-05 08_37_32.md`, blocco `f_yk` = 450,
`R_ck` = 30, tabula k e μ in funzione delle due deformazioni marginali. Alle due
righe che stringono `ε_yd` = 1,9565 ‰ [V]:

| `ε(cls.)` ‰ | `ε(acc.)` ‰ | k | μ |
|---|---|---|---|
| 3,500 | 2,000 | 0,636 | 0,018576 |
| 3,500 | 1,900 | 0,648 | 0,018921 |

Interpolando linearmente a `ε_s` = 1,9565 ‰ [I]: k = **0,6412**, μ = **0,018726**,
cioè 1,873%. Le tre vie — dispensa, mio ricalcolo, tavole di progetto — danno lo
stesso numero a quattro cifre.

**Due cautele sull'oracolo, che non lo smentiscono ma ne delimitano la
validità.**

1. **L'oracolo parte da `R_ck` = 30 e non dalla classe C25/30.** Sono cose
   diverse: la classe C25/30 ha `f_ck` = 25 per definizione, e darebbe
   `f_cd` = 14,17 MPa e `μ_bil` = 1,88% [I]. Lo scarto è dello 0,4% su `f_cd` e
   dello 0,6% su `μ_bil`. Un test che passasse «C25/30» dove l'oracolo vuole
   «R_ck = 30» fallirebbe di poco — che è il modo peggiore di fallire. Vedi §1.3.
2. **L'oracolo usa `E_s` = 200.000**, cioè il valore di UNI EN 1992-1-1 e non i
   210.000 della Circolare (§2.3). Con 210.000 verrebbe `k_bil` = 0,6526 e
   `μ_bil` = 1,905% [I]: l'oracolo fallirebbe alla terza cifra. **Il valore di
   `E_s` va dichiarato accanto all'oracolo**, altrimenti l'oracolo non è
   riproducibile.

### 5.4 Qualche `μ_bil` in più

Sempre B450, `E_s` = 200.000, classi fino a C50/60. `k_bil` = 0,6414 per tutte
[I]:

| classe | `f_cd` [MPa] | `μ_bil` [%] |
|---|---|---|
| C20/25 | 11,33 | 1,50 |
| C25/30 | 14,17 | 1,88 |
| C30/37 | 17,00 | 2,26 |
| C35/45 | 19,83 | 2,63 |
| C40/50 | 22,67 | 3,01 |

`μ_bil` cresce **linearmente con `f_cd`**, perché tutto il resto è costante. Da
confrontare col massimo di norma della §6.2: già dalla C35/45 la percentuale
bilanciata supera i massimi sismici del §7.4.6.2.1.

---

## 6. Armatura minima, massima, staffe e copriferro

### 6.1 L'armatura minima a flessione

NTC 2018 §4.1.6.1.1, espressione `[4.1.45]`. Il convertito la spezza — è il caso
1 della §0.2 — e la ricostruzione [R] è:

```
A_s,min = 0,26 * (f_ctm / f_yk) * b_t * d
          e comunque  A_s,min >= 0,0013 * b_t * d          [4.1.45]
```

Il testo del convertito, verbatim [V] (righe 2379-2380), col denominatore che
finisce sulla riga dopo:

> «L'area dell'armatura longitudinale in zona tesa non deve essere inferiore a
> As,min 0,26 f fctm bt · d e comunque non minore di 0,0013 · bt · d [4.1.45]»
> / «yk»

E le definizioni, verbatim [V] (riga 2384):

> «bt rappresenta la larghezza media della zona tesa; per una trave a T con
> piattabanda compressa, nel calcolare il valore di bt si considera solo la
> larghezza dell'anima; d è l'altezza utile della sezione; fctm è il valore
> medio della resistenza a trazione assiale definita nel § 11.2.10.2; fyk è il
> valore caratteristico della resistenza a trazione dell'armatura ordinaria.»

Tre cose che la formula da sola non dice:

- **`b_t` non è `b`.** È la larghezza media della **zona tesa**, e per una T con
  piattabanda compressa è la larghezza dell'anima. Un programma che passasse la
  base lorda di una T sovrastimerebbe il minimo.
- **`f_yk` e non `f_yd`.** Il minimo è tarato sulla resistenza caratteristica.
- **Il minimo assoluto 0,0013·`b_t`·`d`** — cioè 0,13% — governa quando
  `0,26·f_ctm/f_yk < 0,0013`, cioè quando `f_ctm < 0,005·f_yk`: con `f_yk` = 450
  significa `f_ctm` < 2,25 MPa, cioè **fino alla C25/30 compresa** [I]. Dalla
  C30/37 in su comanda il primo termine.

**La Circolare non corregge la formula, ne allarga il campo.** §C4.1.6.1.1,
verbatim e per intero [V] (riga 2702) — sono due righe:

> «Con riferimento al secondo capoverso del § 4.1.6.1.1 delle NTC, si precisa
> che detta prescrizione si riferisce anche alle travi senza armatura al taglio.»

Il «secondo capoverso» è quello sulle staffe minime (§6.3): la Circolare dice
che **anche le travi non armate a taglio devono portare le staffe minime**. Non
tocca `A_s,min`.

Valori [I] per B450 (`f_yk` = 450) e classi correnti:

| classe | `f_ctm` [MPa] | `0,26·f_ctm/f_yk` | governa |
|---|---|---|---|
| C20/25 | 2,21 | 0,00128 | il minimo assoluto 0,0013 |
| C25/30 | 2,56 | 0,00148 | la formula |
| C30/37 | 2,90 | 0,00167 | la formula |
| C35/45 | 3,21 | 0,00185 | la formula |

(La C20/25 è al confine: 0,00128 contro 0,0013.)

### 6.2 L'armatura massima

§4.1.6.1.1 per le travi, verbatim [V] (riga 2384):

> «Al di fuori delle zone di sovrapposizione, l'area di armatura tesa o compressa
> non deve superare individualmente As,max = 0,04 Ac, essendo Ac l'area della
> sezione trasversale di calcestruzzo.»

§4.1.6.1.2 per i pilastri, verbatim [V] (riga 2388): stessa formula,
`A_s,max = 0,04 A_c`, ma **senza** la parola «individualmente».

Due differenze da non appiattire:

- nelle travi il 4% vale **per ciascuna** delle due armature, tesa e compressa,
  separatamente; nei pilastri vale sull'armatura totale;
- `A_c` è l'area **lorda** della sezione di calcestruzzo, non l'area di `b·d`.

**In zona sismica i limiti sono altri e più stretti.** §7.4.6.2.1, espressione
`[7.4.26]`. Il convertito la riduce a `1,4 3,5 ȡ ȡcomp [7.4.26] fykfyk` (riga
5159): due frazioni appiattite e i segni persi. Ricostruzione [R], nella forma
che rende coerente il testo che la accompagna:

```
1,4 / f_yk  <=  rho  <=  rho_comp + 3,5 / f_yk        [7.4.26]
        con f_yk in MPa, rho = A_s/(b*h) oppure A_i/(b*h)
```

Per `f_yk` = 450 [I]: `ρ_min` = 0,311%, `ρ_max` = `ρ_comp` + 0,778%.

**Questa ricostruzione è la meno sicura del documento** e va ricontrollata sul
PDF prima di finire in un test: il convertito non conserva né il segno «+» né i
due «≤», e la forma sopra è quella corrente ma non l'ho potuta leggere.

Il resto dello stesso § è invece leggibile e integro, verbatim [V]:

> «Almeno due barre di diametro non inferiore a 14 mm devono essere presenti
> superiormente e inferiormente, per tutta la lunghezza della trave.»
> «Inoltre deve essere ρcomp ≥ 0,25 ρ ovunque e nelle zone dissipative
> ρcomp ≥ 1/2 ρ.»

E per i pilastri in zona sismica, espressione `[7.4.28]`, verbatim [V] (riga
5177): «1% ≤ ρ ≤ 4%», con «per tutta la lunghezza del pilastro, l'interasse tra
le barre non deve essere superiore a 25 cm».

### 6.3 Le staffe

**Attenzione: le NTC danno i minimi delle staffe in due § diversi, e non dicono
le stesse cose.**

**Travi**, §4.1.6.1.1, verbatim [V] (riga 2384):

> «Le travi devono prevedere armatura trasversale costituita da staffe con
> sezione complessiva non inferiore ad Ast = 1,5 b mm²/m essendo b lo spessore
> minimo dell'anima in millimetri, con un minimo di tre staffe al metro e
> comunque passo non superiore a 0,8 volte l'altezza utile della sezione. In
> ogni caso almeno il 50% dell'armatura necessaria per il taglio deve essere
> costituita da staffe.»

e, subito dopo [V]: «Eventuali armature longitudinali compresse di diametro Ø
prese in conto nei calcoli di resistenza devono essere trattenute da armature
trasversali con spaziatura non maggiore di 15 Ø.»

**Il §4.1.6.1.1 non dà alcun diametro minimo di staffa.** [NON TROVATO nel § delle
travi.]

**Pilastri**, §4.1.6.1.2, verbatim [V] (riga 2388):

> «Le armature trasversali devono essere poste ad interasse non maggiore di 12
> volte il diametro minimo delle barre impiegate per l'armatura longitudinale,
> con un massimo di 250 mm. Il diametro delle staffe non deve essere minore di
> 6 mm e di ¼ del diametro massimo delle barre longitudinali.»

Riassunto, con l'articolo di ciascuna riga:

| grandezza | travi | pilastri |
|---|---|---|
| sezione minima | `A_st` ≥ 1,5·b mm²/m — §4.1.6.1.1 | — |
| numero minimo | 3 staffe/m — §4.1.6.1.1 | — |
| passo massimo | 0,8·d — §4.1.6.1.1 | min(12·Ø_long,min ; 250 mm) — §4.1.6.1.2 |
| diametro minimo | [NON TROVATO] | max(6 mm ; Ø_long,max/4) — §4.1.6.1.2 |
| quota a taglio | ≥ 50% in staffe — §4.1.6.1.1 | — |
| ritegno delle compresse | passo ≤ 15·Ø — §4.1.6.1.1 | — |

**Il campo `diametro_staffe` di `config.ArmaturaConfig`** (`config.py:1148`)
cita già il §4.1.6.1.2 e impone `ge=6`, con una nota che dice esplicitamente che
il minimo relativo `Ø_long,max/4` «questa configurazione non può controllare da
sola». La lettura di questa sessione conferma la citazione ed è d'accordo con la
nota: il minimo di norma è il **massimo fra due numeri**, e uno dei due dipende
da un altro campo.

**In zona sismica, di nuovo, i numeri sono altri.** §7.4.6.2.1, zone dissipative
delle travi, verbatim [V] (riga 5172): staffe di contenimento, prima staffa a non
più di 5 cm dal filo pilastro, passo non superiore al minimo fra un quarto
dell'altezza utile, 175 mm (CD"A") o 225 mm (CD"B"), 6 o 8 volte il diametro
minimo delle barre longitudinali, e 24 volte il diametro delle trasversali; e
«per staffa di contenimento si intende una staffa rettangolare, circolare o a
spirale, di diametro minimo 6 mm, con ganci a 135° prolungati, alle due
estremità, per almeno 10 diametri».

§7.4.6.2.2, pilastri [V] (riga 5177): diametro «non inferiore a: max[6 mm; (0,4 ·
dbl,max · fyd,l/fyd,st)] per CD"A" e 6 mm per CD"B"»; passo non superiore al
minimo fra 1/3 (CD"A") o 1/2 (CD"B") del lato minore, 12,5 cm o 17,5 cm, e 6 o 8
volte il diametro delle barre collegate.

**Il §4.1.6.1 lo dice da sé** che questi prevalgono, verbatim [V] (riga 2378):
«Dette indicazioni si applicano se non sono in contrasto con più restrittive
regole relative a costruzioni in zona sismica.»

### 6.4 Il copriferro

**Le NTC non danno nessun numero.** §4.1.6.1.3, verbatim e quasi per intero [V]
(riga 2389):

> «Al fine della protezione delle armature dalla corrosione, lo strato di
> ricoprimento di calcestruzzo (copriferro) deve essere dimensionato in funzione
> dell'aggressività dell'ambiente e della sensibilità delle armature alla
> corrosione, tenendo anche conto delle tolleranze di posa delle armature; a
> tale scopo si può fare utile riferimento alla UNI EN 1992-1-1. Per consentire
> un omogeneo getto del calcestruzzo, il copriferro e l'interferro delle
> armature devono essere rapportati alla dimensione massima degli inerti
> impiegati.»

**I numeri li dà la Circolare**, §C4.1.6.1.3, Tabella C4.1.IV [V] (riga 2706).
La tabella è una griglia 3×8 e la conversione ne ha storpiato l'intestazione:
`¢¢o Cmin C<Co` sta per le due colonne «C ≥ C₀» e «C_min ≤ C < C₀» [R]. I valori
numerici sono invece leggibili e in ordine.

**Tabella C4.1.IV — copriferri minimi in mm** [V per i numeri, [R] per
l'intestazione]:

| ambiente | `C_min` | `C₀` | barre c.a., piastre: C≥C₀ / C<C₀ | barre c.a., altri elementi: C≥C₀ / C<C₀ | cavi c.a.p., piastre | cavi c.a.p., altri |
|---|---|---|---|---|---|---|
| ordinario | C25/30 | C35/45 | 15 / 20 | 20 / 25 | 25 / 30 | 30 / 35 |
| aggressivo | C30/37 | C40/50 | 25 / 30 | 30 / 35 | 35 / 40 | 40 / 45 |
| molto aggressivo | C35/45 | C45/55 | 35 / 40 | 40 / 45 | 45 / 50 | 50 / 50 |

L'ultima cella vale 50 in entrambe le colonne: il convertito riporta «50|50» e
non è un errore di lettura mio, ma **è l'unica coppia della tabella in cui i due
valori coincidono** e merita un controllo sul PDF.

**Le tre condizioni ambientali sono definite dalle NTC**, Tab. 4.1.III, verbatim
[V] (riga 2233):

| condizione | classi di esposizione |
|---|---|
| Ordinarie | X0, XC1, XC2, XC3, XF1 |
| Aggressive | XC4, XD1, XS1, XA1, XA2, XF2, XF3 |
| Molto aggressive | XD2, XD3, XS2, XS3, XA3, XF4 |

**Le quattro correzioni al valore di tabella**, §C4.1.6.1.3, verbatim [V]:

> «A tali valori di tabella vanno aggiunte le tolleranze di posa, pari a 10 mm o
> minore, secondo indicazioni di norme di comprovata validità. I valori della
> Tabella C4.1.IV si riferiscono a costruzioni con vita nominale di 50 anni […]
> Per costruzioni con vita nominale di 100 anni […] i valori della Tabella
> C4.1.IV vanno aumentati di 10 mm. Per classi di resistenza inferiori a Cmin i
> valori della tabella sono da aumentare di 5 mm. Per produzioni di elementi
> sottoposte a controllo di qualità che preveda anche la verifica dei
> copriferri, i valori della tabella possono essere ridotti di 5 mm.»

Da cui il copriferro **nominale** [I]:

```
c_nom = c_min(ambiente, tipo elemento, classe)   # Tabella C4.1.IV
        + 10 mm            se vita nominale 100 anni
        + 5  mm            se classe di resistenza < C_min
        - 5  mm            se controllo di qualita' sui copriferri
        + tolleranza di posa (10 mm o meno)
```

Il campo `config.ArmaturaConfig.copriferro_nominale` (`config.py:1160`) chiede
già il **nominale** e impone `ge=10.0`. Coerente: il minimo assoluto della
Tabella C4.1.IV è 15 mm, e con la tolleranza di posa il nominale non scende sotto
25 mm nel caso più favorevole.

**Divergenza da segnalare, non da sciogliere.** Il file
`classi esposizione UNI EN 206 2024-03-05 08_37_28.md` — che è **materiale del
corso**, non norma: la sua intestazione dice «Classi di esposizione ambientale
secondo UNI EN 206-1» e la tabella cita la UNI 9858, ritirata — porta una colonna
«Copriferro minimo mm» con valori diversi da quelli della Circolare [V]:

| classe | copriferro dal file del corso | condizione NTC | c_min Circolare, barre c.a., «altri elementi», C≥C₀ |
|---|---|---|---|
| X0 | 15 | ordinaria | 20 |
| XC1 | 20 | ordinaria | 20 |
| XC2 | 20 | ordinaria | 20 |
| XC3 | 30 | ordinaria | 20 |
| XC4 | 30 | aggressiva | 30 |
| XD3 | 40 | molto aggressiva | 40 |

Concordano su XC1, XC2, XC4, XD3; divergono su X0 e XC3. **La fonte da citare è
la Circolare**, che è norma; il file del corso è utile per le altre colonne
(rapporto a/c massimo, contenuto minimo di cemento, classe di resistenza minima
per classe di esposizione) che né le NTC né la Circolare tabulano. Non scelgo:
vedi §10.2.

---

## 7. Le combinazioni di carico

### 7.1 I coefficienti ψ — Tab. 2.5.I

NTC 2018 §2.5.2, Tab. 2.5.I [V] (righe 1571-1583). La conversione ha spezzato la
tabella in due tronconi e ha mandato la parentesi «(per autoveicoli di peso > 30
kN)» della categoria G su una riga a sé; l'ho ricomposta [R] usando il fatto che
la categoria F porta «≤ 30 kN» e la G «> 30 kN».

| Categoria / azione variabile | `ψ_0j` | `ψ_1j` | `ψ_2j` |
|---|---|---|---|
| A — Ambienti ad uso residenziale | 0,7 | 0,5 | 0,3 |
| B — Uffici | 0,7 | 0,5 | 0,3 |
| C — Ambienti suscettibili di affollamento | 0,7 | 0,7 | 0,6 |
| D — Ambienti ad uso commerciale | 0,7 | 0,7 | 0,6 |
| E — Aree per immagazzinamento, uso commerciale e industriale; biblioteche, archivi, magazzini | 1,0 | 0,9 | 0,8 |
| F — Rimesse, parcheggi, aree per il traffico di veicoli (autoveicoli ≤ 30 kN) | 0,7 | 0,7 | 0,6 |
| G — Rimesse, parcheggi, aree per il traffico di veicoli (autoveicoli > 30 kN) | 0,7 | 0,5 | 0,3 |
| H — Coperture accessibili per sola manutenzione | 0,0 | 0,0 | 0,0 |
| I — Coperture praticabili | da valutarsi caso per caso | | |
| K — Coperture per usi speciali (impianti, eliporti, …) | da valutarsi caso per caso | | |
| Vento | 0,6 | 0,2 | 0,0 |
| Neve (quota ≤ 1000 m s.l.m.) | 0,5 | 0,2 | 0,0 |
| Neve (quota > 1000 m s.l.m.) | 0,7 | 0,5 | 0,2 |
| Variazioni termiche | 0,6 | 0,5 | 0,0 |

Il testo di norma [V] dice a che cosa i tre coefficienti servono, e la
definizione è utile perché spiega perché `ψ_2` e non `ψ_0` entra nelle masse
sismiche: «valore quasi permanente ψ2j·Qkj: il valore istantaneo superato oltre
il 50% del tempo nel periodo di riferimento»; «valore frequente ψ1j·Qkj: il
valore superato per un periodo totale di tempo che rappresenti una piccola
frazione del periodo di riferimento»; «valore di combinazione ψ0j·Qkj: il valore
tale che la probabilità di superamento degli effetti causati dalla concomitanza
con altre azioni sia circa la stessa di quella associata al valore
caratteristico di una singola azione».

**Una premessa del brief da correggere.** Il brief chiede «Tab. 2.5.I e 2.5.II».
**La Tab. 2.5.II non esiste nelle NTC 2018**: zero occorrenze della stringa
«2.5.II» nel testo convertito. I ψ stanno tutti nella Tab. 2.5.I, e i
coefficienti parziali γ non stanno nel §2.5 affatto: stanno nella **Tab. 2.6.I**
del §2.6.1. Le NTC lo dicono in fondo al §2.5.3 [V]: «I valori dei coefficienti
parziali di sicurezza γGi e γQj sono dati nel § 2.6.1».

Il §2.5.3 rimanda inoltre a due tabelle diverse per i ponti [V]: Tab. 5.1.VI per
i ponti stradali, Tab. 5.2.VII per i ferroviari. Non le ho lette.

### 7.2 I coefficienti γ — Tab. 2.6.I

NTC 2018 §2.6.1, Tab. 2.6.I, verbatim [V] (riga 1628):

| coefficiente | | EQU | A1 (STR) | A2 (GEO) |
|---|---|---|---|---|
| `γ_G1` — carichi permanenti | favorevoli | 0,9 | 1,0 | 1,0 |
| | sfavorevoli | 1,1 | **1,3** | 1,0 |
| `γ_G2` — permanenti non strutturali | favorevoli | 0,8 | 0,8 | 0,8 |
| | sfavorevoli | 1,5 | **1,5** | 1,3 |
| `γ_Qi` — azioni variabili | favorevoli | 0,0 | 0,0 | 0,0 |
| | sfavorevoli | 1,5 | **1,5** | 1,3 |

E, nel testo [V]: «Il coefficiente parziale della precompressione si assume pari
a γP = 1,0».

Quattro cose che la tabella da sola non dice, tutte verbatim [V]:

- **quale colonna usare**: «Per la progettazione di componenti strutturali che
  non coinvolgano azioni di tipo geotecnico, le verifiche nei confronti degli
  stati limite ultimi strutturali (STR) si eseguono adottando i coefficienti γF
  riportati nella colonna A1». Per un telaio fuori terra la colonna è **A1**;
- **il γ delle variabili favorevoli è zero, non uno**: un carico variabile che
  aiuta si toglie, non si riduce;
- **la nota (1) sulla colonna dei permanenti non strutturali**: «Nel caso in cui
  l'intensità dei carichi permanenti non strutturali […] sia ben definita in
  fase di progetto, per detti carichi o per la parte di essi nota si potranno
  adottare gli stessi coefficienti parziali validi per le azioni permanenti».
  Cioè `γ_G2` può scendere da 1,5 a 1,3 se il carico è noto;
- **i tre stati limite ultimi** sono EQU (equilibrio come corpo rigido), STR
  (resistenza della struttura, fondazioni comprese) e GEO (resistenza del
  terreno).

### 7.3 Le sei combinazioni, per esteso

NTC 2018 §2.5.3 [V] (righe 1584-1596). **Il convertito ha ridotto le sei
combinazioni a una tabella Markdown spezzata**, con i pedici dei `Q_k` dispersi
su righe separate in fondo (`1 k1 k2 k3`, `1 k1 22 k2 k3`, e così via). Ho
ricostruito le sei formule [R] incrociando: i pedici superstiti nel testo, la
numerazione delle espressioni `[2.5.1]`–`[2.5.7]` che è intatta, e le
intestazioni in prosa di ciascuna combinazione, che sono leggibili per intero.
Le intestazioni sono verbatim [V]; le formule sono [R].

```
# Fondamentale (SLU)                                        [2.5.1]
gamma_G1*G1 + gamma_G2*G2 + gamma_P*P
    + gamma_Q1*Q_k1 + gamma_Q2*psi_02*Q_k2 + gamma_Q3*psi_03*Q_k3 + ...

# Caratteristica, cosiddetta rara (SLE irreversibili)        [2.5.2]
G1 + G2 + P + Q_k1 + psi_02*Q_k2 + psi_03*Q_k3 + ...

# Frequente (SLE reversibili)                                [2.5.3]
G1 + G2 + P + psi_11*Q_k1 + psi_22*Q_k2 + psi_23*Q_k3 + ...

# Quasi permanente (SLE, effetti a lungo termine)            [2.5.4]
G1 + G2 + P + psi_21*Q_k1 + psi_22*Q_k2 + psi_23*Q_k3 + ...

# Sismica (SLU e SLE connessi all'azione sismica E)          [2.5.5]
E + G1 + G2 + P + psi_21*Q_k1 + psi_22*Q_k2 + ...

# Eccezionale (SLU connessi alle azioni eccezionali A)       [2.5.6]
G1 + G2 + P + A_d + psi_21*Q_k1 + psi_22*Q_k2 + ...

# Carichi gravitazionali per le masse sismiche               [2.5.7]
G1 + G2 + sum_j( psi_2j * Q_kj )
```

Le intestazioni in prosa, verbatim [V], che dicono a che cosa serve ciascuna:

> «Combinazione fondamentale, generalmente impiegata per gli stati limite ultimi
> (SLU)»; «Combinazione caratteristica, cosiddetta rara, generalmente impiegata
> per gli stati limite di esercizio (SLE) irreversibili»; «Combinazione
> frequente, generalmente impiegata per gli stati limite di esercizio (SLE)
> reversibili»; «Combinazione quasi permanente (SLE), generalmente impiegata per
> gli effetti a lungo termine»; «Combinazione sismica, impiegata per gli stati
> limite ultimi e di esercizio connessi all'azione sismica E»; «Combinazione
> eccezionale, impiegata per gli stati limite ultimi connessi alle azioni
> eccezionali A»; «Gli effetti dell'azione sismica saranno valutati tenendo
> conto delle masse associate ai seguenti carichi gravitazionali».

Quattro note del testo, verbatim [V]:

- «Nelle combinazioni si intende che vengano omessi i carichi Q che danno un
  contributo favorevole ai fini delle verifiche e, se del caso, i carichi G₂.»
- «Nelle formule sopra riportate il simbolo "+" vuol dire "combinato con".»
- «`Q_k1` rappresenta l'azione variabile di base e `Q_k2`, `Q_k3`, … le azioni
  variabili d'accompagnamento» (§2.5.2). Ne segue che **la combinazione
  fondamentale va ripetuta con ciascuna variabile a turno nel ruolo di base**:
  con n variabili sono n combinazioni, non una.
- «Altre combinazioni sono da considerare in funzione di specifici aspetti (p.
  es. fatica, ecc.).»

**Le due combinazioni che si scambiano più facilmente sono la `[2.5.3]` e la
`[2.5.4]`**, perché differiscono in un solo pedice: la frequente porta `ψ_11`
sulla variabile di base e `ψ_2j` sulle altre; la quasi permanente porta `ψ_2j`
su tutte. Il primo `ψ` è l'unico carattere che le distingue.

**La `[2.5.7]` non è una combinazione di verifica**: è la regola con cui si
costruiscono le **masse** per l'analisi sismica, e non porta né `γ` né `P`. È
anche la combinazione che il §7.3.3.2 usa per stimare lo spostamento `d` da cui
si ricava `T_1` (§9.2).

---

## 8. La sismica statica lineare equivalente

Tutto ciò che segue viene dal solo §7.3.3.2 delle NTC (riga 4845): il commento
della Circolare non è leggibile, per il buco della §0.3.

### 8.1 Quando è ammessa

Verbatim [V]:

> «L'analisi lineare statica consiste nell'applicazione di forze statiche
> equivalenti alle forze d'inerzia indotte dall'azione sismica e può essere
> effettuata per costruzioni che rispettino i requisiti specifici riportati nei
> paragrafi successivi, a condizione che il periodo del modo di vibrare
> principale nella direzione in esame (T₁) non superi 2,5 TC o TD e che la
> costruzione sia regolare in altezza.»

Due condizioni cumulative:

```
T_1 <= 2,5 * T_C   oppure   T_1 <= T_D
e la costruzione e' regolare in altezza (§7.2.2)
```

`T_C` e `T_D` sono i periodi che delimitano lo spettro di progetto (§3.2.3.5) e
dipendono dal sito. Non li ho letti in questa sessione.

### 8.2 Il periodo `T_1`

Verbatim [V], espressione `[7.3.6]`, col segno di radice ricostruito [R] — è il
caso 4 della §0.2:

> «Per costruzioni civili o industriali che non superino i 40 m di altezza e la
> cui massa sia distribuita in modo approssimativamente uniforme lungo l'altezza,
> T₁ (in secondi) può essere stimato, in assenza di calcoli più dettagliati,
> utilizzando la formula seguente: T₁ = 2 √d [7.3.6] dove d è lo spostamento
> laterale elastico del punto più alto dell'edificio, espresso in metri, dovuto
> alla combinazione di carichi [2.5.7] applicata nella direzione orizzontale.»

```
T_1 = 2 * sqrt(d)          [7.3.6]      d in metri, T_1 in secondi
```

Tre cose che si sbagliano:

- **`d` è in metri.** Il progetto lavora in millimetri
  (`config.GRAVITY_MM_S2` = 9810,0): passare millimetri alla `[7.3.6]` dà un
  periodo 31,6 volte più grande [I].
- **`d` è lo spostamento sotto i carichi della `[2.5.7]` applicati
  orizzontalmente**, non sotto una forza sismica: si prende il peso sismico e lo
  si gira di 90°.
- **La `[7.3.6]` è condizionata**: vale per costruzioni fino a 40 m e con massa
  approssimativamente uniforme in altezza, e solo «in assenza di calcoli più
  dettagliati». È una stima, non una definizione di `T_1`.

**La formula delle NTC 2008, `T_1 = C_1·H^(3/4)`, non c'è più**: nel testo
convertito delle NTC 2018 non compare [NON TROVATO]. Un programma che la usasse
citerebbe una norma abrogata.

### 8.3 La forza di base

Verbatim [V]:

> «L'entità delle forze si ottiene dall'ordinata dello spettro di progetto
> corrispondente al periodo T₁ e la loro distribuzione sulla struttura segue la
> forma del modo di vibrare principale nella direzione in esame, valutata in
> modo approssimato. […] Fh = Sd(T₁) · W · λ / g»

```
F_h = S_d(T_1) * W * lambda / g
```

dove, verbatim [V]:

> «Sd(T₁) è l'ordinata dello spettro di risposta di progetto definito al §
> 3.2.3.5; W è il peso complessivo della costruzione; λ è un coefficiente pari a
> 0,85 se T₁ < 2TC e la costruzione ha almeno tre orizzontamenti, uguale a 1,0
> in tutti gli altri casi; g è l'accelerazione di gravità.»

```
lambda = 0,85   se T_1 < 2*T_C  E  orizzontamenti >= 3
lambda = 1,0    in tutti gli altri casi
```

**`λ` è congiuntivo**: bastano due orizzontamenti, o `T_1` ≥ 2`T_C`, e vale 1,0.
Un edificio a due piani non prende lo sconto.

**La divisione per `g` c'è perché `S_d` è un'accelerazione e `W` un peso.** Se il
programma tiene le masse invece dei pesi, `F_h = S_d(T_1) · M · λ` senza `g` — ed
è esattamente il posto dove nasce l'errore di un fattore 9,81. Nelle unità del
progetto `g` = 9810 mm/s².

### 8.4 La distribuzione lungo l'altezza

Verbatim [V], espressione `[7.3.7]`:

> «La forza da applicare a ciascuna massa della costruzione è data dalla formula
> seguente: Fi = Fh · zi · Wi / Σj zj Wj [7.3.7] dove: Fi è la forza da applicare
> alla massa i-esima; Wi e Wj sono i pesi, rispettivamente, della massa i e
> della massa j; zi e zj sono le quote, rispetto al piano di fondazione (v. §
> 3.2.3.1), delle masse i e j»

```
F_i = F_h * (z_i * W_i) / sum_j( z_j * W_j )              [7.3.7]
```

È una distribuzione **triangolare pesata sulle masse**, cioè il primo modo
approssimato con una retta. Due dettagli:

- **`z` si misura dal piano di fondazione**, non dal suolo né dal piano terra
  (rimando esplicito al §3.2.3.1);
- **la somma delle `F_i` è `F_h` per costruzione**, ed è la verifica di
  autoconsistenza più economica che un'implementazione possa portarsi dietro.

### 8.5 L'eccentricità accidentale

Non sta nel §7.3.3.2 ma nel §7.3.3, e vale anche per la statica, verbatim [V]
(riga 4828):

> «Sia per analisi lineare dinamica, sia per analisi lineare statica, si deve
> tenere conto dell'eccentricità accidentale del centro di massa. Per gli
> edifici, gli effetti di tale eccentricità possono essere determinati mediante
> l'applicazione di carichi statici costituiti da momenti torcenti di valore pari
> alla risultante orizzontale della forza agente al piano, determinata come in §
> 7.3.3.2, moltiplicata per l'eccentricità accidentale del baricentro delle
> masse rispetto alla sua posizione di calcolo, determinata come in § 7.2.6.»

Il valore dell'eccentricità sta nel §7.2.6, che non ho letto in questa sessione
[NON TROVATO qui].

### 8.6 Gli spostamenti

§7.3.3.3, verbatim [V] (riga 4872), espressioni `[7.3.8]` e `[7.3.9]`: gli
spostamenti sotto l'azione sismica di progetto allo SLV si ottengono
moltiplicando quelli dell'analisi lineare per un fattore di duttilità in
spostamento `μ_d`, con «in ogni caso μd ≤ 5q – 4». Le due espressioni che
definiscono `μ_d` sono illeggibili nel convertito [NON TROVATO in forma
leggibile]; il tetto `5q − 4` è leggibile e integro.

---

## 9. Che cosa non ho verificato

1. **Il capitolo C7 della Circolare** — assente dalla conversione (§0.3). Tutta
   la §8 poggia sulle sole NTC.
2. **La serie commerciale dei diametri** — le NTC danno un intervallo, non un
   elenco (§2.4). La serie sta in UNI EN 10080, già trascritta altrove in questa
   cartella e non ricontrollata qui.
3. **La Tab. 3.1.I dei pesi dell'unità di volume** — illeggibile nel convertito
   (§1.1).
4. **`T_C`, `T_D` e lo spettro di progetto** (§3.2.3.5), e **l'eccentricità
   accidentale** (§7.2.6). Servono alla §8 e non li ho letti.
5. **Le espressioni `[7.3.8]` e `[7.3.9]`** sul fattore di duttilità in
   spostamento — illeggibili.
6. **Le tabelle dei ponti** — Tab. 5.1.VI e 5.2.VII, richiamate dal §2.5.3.
7. **UNI EN 1992-1-1 e UNI EN 10080** — non li ho aperti in questa sessione: dove
   li cito, cito la trascrizione già fatta in
   [`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md),
   che è una fonte di seconda mano rispetto a loro.
8. **La ricostruzione della `[7.4.26]`** (§6.2) è la meno solida del documento e
   va ricontrollata sul PDF prima di finire in un test.

## 10. Le divergenze lasciate aperte

### 10.1 Fra la norma e sé stessa

**a) `R_ck` dal nome della classe contro `f_ck` dal nome della classe** (§1.3).
La `[11.2.1]` e la designazione UNI EN 206 non sono la stessa funzione: lo
scarto arriva al 6,7% sulla C35/45. Il catalogo deve dichiarare da quale dei due
parte.

**b) Il fattore 1,2 sulla `f_ctm`** (§1.1): la `[11.2.4]` moltiplica, la
`[4.1.13]` divide. Non è una contraddizione — sono due grandezze diverse — ma le
due espressioni compaiono a poche righe l'una dall'altra e si scambiano.

### 10.2 Fra fonti diverse

**a) `E_s` = 210.000 o 200.000?** Circolare §C4.1.2.2.5 contro UNI EN 1992-1-1
§3.2.7(4) (§2.3). Il 5% di differenza sposta `k_bil` da 0,6414 a 0,6526 e `μ_bil` da
1,872% a 1,905%, cioè l'1,8% in relativo. **L'oracolo del progetto usa 200.000.** Non scelgo.

**b) `E_cm` della C8/10: 25.331 o 25.393 MPa?**
[`ricerca-armature-convenzioni-normative.md`](ricerca-armature-convenzioni-normative.md)
§4.2 pubblica 25.393; il mio ricalcolo dalla `[11.2.5]` dà 25.331 (§1.4). Le
altre sedici righe della tabella coincidono cifra per cifra fra le due sessioni,
quindi non è una divergenza di formula né di arrotondamento sistematico: è una
riga sola. `22000·(16/10)^0,3` = 25.331,37 [I]. **Segnalo, non correggo il
documento altrui.**

**c) Il copriferro per classe di esposizione** (§6.4): il file del corso su
UNI EN 206-1 e la Tabella C4.1.IV della Circolare divergono su X0 e XC3. La
Circolare è norma; il file del corso porta però colonne che la Circolare non ha.

### 10.3 Fra la norma e le fonti del corso

I due file `Domini_NM_DM2018` e `Tabelle_flessione_SL_2018` portano nel testo
l'intestazione **«DM 14-01-2008»**, non NTC 2018 [V], anche se il nome del file
dice 2018. Per le grandezze che questo documento usa — `γ_c` = 1,5, `γ_s` = 1,15,
`α_cc` = 0,85, `ε_c2` = 2‰, `ε_cu` = 3,5‰, `f_ck` = 0,83·`R_ck`, `ε_su` = 0,0675
— **NTC 2008 e NTC 2018 coincidono**, e infatti i numeri tornano (§5.3). Ma
l'intestazione va detta: quei due file **non sono fonti NTC 2018**, e per
qualunque grandezza fuori da questo elenco vanno ricontrollati.

---

## 11. Che cosa il catalogo dovrebbe portare — raccomandazione, non decisione

Questa sezione **propone**. La scelta è di Mario.

### 11.1 La forma, per analogia col registro delle soglie

`meshrec/src/meshrec/core/soglie.py` risolve già lo stesso problema per le
soglie di verifica, e la lezione che porta è nella sua docstring: **`fonte` e
`origine` sono cose diverse, e confonderle era il difetto** (`soglie.py:22`).
Una `soglie.Soglia` distingue `letta` (il numero è pubblicato nella fonte),
`derivata` (calcolato da un fatto della fonte) e `nostra` (scelto da noi), e i
test rifiutano una voce senza fonte.

**Applicata al catalogo dei materiali, quella distinzione dice una cosa netta:
delle grandezze della tabella della §1.4, non ce n'è nessuna `letta`.** `f_ck` si
legge dal *nome* della classe (Tab. 4.1.I non porta numeri); `f_cm`, `f_ctm`,
`f_ctk`, `E_cm`, `f_cd` si calcolano tutte. Sono tutte **`derivata`**, con la
fonte che è l'espressione di norma. Se il catalogo copiasse la tabella della
§1.4 marcandola `letta`, direbbe una cosa falsa sulla propria provenienza.

Per l'acciaio è il contrario: `f_y nom`, `f_t nom`, `(A_gt)_k`, gli intervalli di
diametro sono **`letta`**, e stanno tutti in Tab. 11.3.Ia/Ib/Ic e §11.3.2.4.
`ε_ud` e `f_yd` sono `derivata`. `E_s` **non è né l'una né l'altra**: è una
scelta fra due fonti che divergono (§10.2a), quindi `nostra` con una nota che
dica quale si è presa e perché.

### 11.2 I campi

Per il calcestruzzo, per riga: nome della classe, `R_ck` e `f_ck` **entrambi**
(perché la §1.3 mostra che non si deducono l'uno dall'altro senza dichiarare
come), `f_cm`, `f_ctm`, `f_ctk`, `E_cm`, `ν`, `ρ`, `ε_c2`, `ε_cu`, e per ciascuno
l'espressione di norma da cui viene.

Per l'acciaio: nome, `f_yk`, `f_tk`, `(A_gt)_k`, `ε_uk`, `ε_ud`, `E_s`, `k_min`,
`k_max`, intervallo di diametri per barre / rotoli / reti.

Una riga del catalogo **non** dovrebbe portare `f_cd` e `f_yd` come dati: sono
funzioni dei coefficienti parziali, e i coefficienti parziali cambiano col caso
di verifica (§3.4). Meglio una funzione che li calcola, che prende
esplicitamente i casi della §3.4 e che non ha un valore predefinito silenzioso
per `α_cc`.

### 11.3 Tre controlli che valgono la pena

Non sono verifiche strutturali: sono controlli di coerenza del catalogo con sé
stesso, del genere che `soglie.trova` rende possibile per le soglie.

1. **La cascata è ricalcolabile.** Per ogni classe, ricalcolare `f_cm`, `f_ctm`,
   `E_cm` dalle espressioni e confrontarle con la riga: se il catalogo tiene i
   numeri, tenerli **generati** e non copiati, come `soglie.tabella_markdown`
   genera la propria tabella invece di ricopiarla.
2. **L'oracolo della §5.3 come collaudo**, con i suoi tre ingressi dichiarati
   accanto: `R_ck` = 30 (non C25/30), `E_s` = 200.000, α = 0,809524 oppure 0,81.
   Senza quei tre, l'oracolo non è riproducibile.
3. **Le classi ammesse.** C28/35 e C32/40 esistono ma «già in uso» e con la
   restrizione sulla durabilità della Circolare; sopra C45/55 serve la
   sperimentazione preventiva; sopra C70/85 l'autorizzazione ministeriale. Il
   catalogo può portarle tutte purché ciascuna porti il proprio vincolo.

`config.ArmaturaConfig` (`config.py:1100`) tiene già `classe_calcestruzzo` come
**testo libero** e ne spiega il perché nella propria docstring: «Resta testo e
non enumerazione finché il catalogo dei materiali non esiste: un'enumerazione
scritta a mano qui sarebbe una seconda verità da tenere allineata a quel
catalogo». Quando il catalogo esisterà, quel campo è il primo che può diventare
un'enumerazione — e l'elenco è quello della §1.2, diciassette voci, non quindici.

---

## 12. Riepilogo dei riferimenti normativi usati

| grandezza | articolo | espressione |
|---|---|---|
| elenco delle classi di calcestruzzo | NTC §4.1 | Tab. 4.1.I |
| classe minima per tipo di struttura | NTC §4.1 | Tab. 4.1.II |
| `f_ck` da `R_ck` | NTC §11.2.10.1 | `[11.2.1]` |
| `f_cm` | NTC §11.2.10.1 | `[11.2.2]` |
| `f_ctm` | NTC §11.2.10.2 | `[11.2.3a]`, `[11.2.3b]` |
| frattili 5% e 95% di `f_ctm` | NTC §11.2.10.2 | — |
| `f_cfm` | NTC §11.2.10.2 | `[11.2.4]` |
| `E_cm` | NTC §11.2.10.3 | `[11.2.5]` |
| Poisson | NTC §11.2.10.4 | — |
| dilatazione termica | NTC §11.2.10.5 | — |
| `f_cd`, `α_cc`, `γ_c` | NTC §4.1.2.1.1.1 | `[4.1.3]` |
| `f_ctd` | NTC §4.1.2.1.1.2 | `[4.1.4]` |
| `f_yd`, `γ_s` | NTC §4.1.2.1.1.3 | `[4.1.5]` |
| `f_bd` (aderenza) | NTC §4.1.2.1.1.4 | `[4.1.6]`, `[4.1.7]` |
| diagrammi del calcestruzzo, `ε_c2`, `ε_cu` | NTC §4.1.2.1.2.1 | Fig. 4.1.1 |
| diagrammi dell'acciaio, `ε_ud` | NTC §4.1.2.1.2.2 | Fig. 4.1.3 |
| condizioni ambientali | NTC §4.1.2.2.4.2 | Tab. 4.1.III |
| ipotesi di base a pressoflessione | NTC §4.1.2.3.4.1 | — |
| `A_s,min`, `A_s,max`, staffe delle travi | NTC §4.1.6.1.1 | `[4.1.45]` |
| armatura dei pilastri e staffe | NTC §4.1.6.1.2 | `[4.1.46]` |
| copriferro — rimando | NTC §4.1.6.1.3 | — |
| copriferro — valori | Circolare §C4.1.6.1.3 | Tab. C4.1.IV |
| calcestruzzo non armato | NTC §4.1.11.1 | `[4.1.50]` |
| classi B450C e B450A | NTC §11.3.2.1, §11.3.2.2 | Tab. 11.3.Ia, Ib, Ic |
| `f(0,2)` in luogo di `f_y` | NTC §11.3.2.3 | — |
| diametri ammessi | NTC §11.3.2.4 | — |
| reti e tralicci | NTC §11.3.2.5 | `[11.3.1]` |
| resistenza in opera, soglia 85% | NTC §11.2.6 | — |
| calcestruzzo non conforme | NTC §11.8.3.1 | — |
| `E_s` per le tensioni in esercizio | Circolare §C4.1.2.2.5 | — |
| coefficienti ψ | NTC §2.5.2 | Tab. 2.5.I |
| combinazioni delle azioni | NTC §2.5.3 | `[2.5.1]`–`[2.5.7]` |
| coefficienti γ | NTC §2.6.1 | Tab. 2.6.I |
| analisi lineare statica | NTC §7.3.3.2 | `[7.3.6]`, `[7.3.7]` |
| eccentricità accidentale | NTC §7.3.3 | — |
| acciaio obbligato in zona sismica | NTC §7.4.2.2 | — |
| armature delle travi in zona sismica | NTC §7.4.6.2.1 | `[7.4.26]` |
| armature dei pilastri in zona sismica | NTC §7.4.6.2.2 | `[7.4.28]` |
| fattori di confidenza | Circolare §C8.5.4.2 | Tab. C8.5.IV |
