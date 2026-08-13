# Fase 1 — Quale regola sostituisce la tolleranza dei set

- **Data di esecuzione:** 13 agosto 2026
- **Ambiente:** Windows 11, stessa macchina delle misure di `fase-1-esiti.md` e
  di `fase-1-min-ratio.md`
- **Parametro sotto misura:** la tolleranza con cui `abaqus.build_node_sets`
  estrae i sei set di faccia, oggi derivata dal volume medio dell'elemento in
  `abaqus.set_tolerance` e regolata da `analysis.set_tolerance_factor`
  (predefinito 0,5)
- **Esito:** una raccomandazione. Nessun file sorgente è stato modificato *durante la misura*.
- **Implementata il 13 agosto 2026.** `abaqus.set_tolerance` segue la regola raccomandata e
  `analysis.set_tolerance_factor` vale 6. La verifica sulle due corse reali riproduce tutti e sei
  gli insiemi di questo documento, non solo `BASE`: muro 18.020 / 13.932 / 241.021 / 137.151 /
  15.417 / 15.807 con copertura 100,00%, `lab_crop` 5915 / 34.866 / 105.878 / 96.459 / 25.668 /
  24.782 con copertura 98,93%. La copertura per colonne descritta più sotto è ora
  `abaqus.footprint_coverage` e compare in `11_export`, come il punto 3 di «che cosa la regola non
  risolve» chiedeva.

## Perché questo documento esiste

`fase-1-debito.md` dichiara sbagliata in partenza l'euristica in vigore — la
tolleranza legata al volume medio dell'elemento, cioè a un artefatto del
raffinamento e non alla geometria — e propone come sostituto la spaziatura dei
nodi di bordo, mediana 13,73 mm sul muro. Il piano di questo compito osserva
che quel suggerimento non regge: con il fattore 0,5 darebbe 6,87 mm contro i
31,95 mm attuali, cioè un `BASE` più piccolo di quello che già oggi è troppo
piccolo. La seconda regola candidata, la selezione per direzione della normale,
è lo standard dei preprocessori ma ha un difetto opposto e sospettato:
l'intradosso di un architrave ha normale verso il basso e finirebbe in `BASE`
pur non poggiando a terra.

Nessuna delle due era scartabile o adottabile a tavolino. Questo documento le
misura entrambe, misura l'euristica in vigore, e ne propone una terza con i
numeri che la sostengono — sullo stesso modello dell'argomento che ha fissato
`tet.min_ratio` a 1,8 in [`fase-1-min-ratio.md`](fase-1-min-ratio.md).

## Gli artefatti misurati, e quali di essi sono stati ricalcolati

**`muro`.** `runs/muro/wall_model.vtu`, l'uscita di `export_model` e quindi
già allineata agli assi: 420.547 nodi, 1.752.795 tetraedri, estensione
1224,06 × 5854,32 × 7823,59 mm. Il suo `metrics.json` contiene `11_export`,
con `set_tolerance` 31,945180563423072 mm e i sei conteggi di set. La
tolleranza ricalcolata qui da `abaqus.set_tolerance(nodi, tetraedri, 0.5)` sul
file `.vtu` vale **31,945 mm**, identica all'archiviata in tutte le cifre
stampate: il metodo di ricalcolo usato in questo documento è quindi verificato
contro l'archivio prima di essere usato dove l'archivio tace.

**`lab_crop`.** Qui l'archivio tace, e va detto per intero. Il suo
`metrics.json` si ferma a `08_simplify`: non contiene `09_volume` né
`11_export`, quindi **non esiste un `set_tolerance` né un conteggio dei set
registrati** per questa corsa. I file `09_volume.vtu`, `wall_model.inp` e
`wall_model.vtu` presenti nella stessa cartella appartengono a una corsa
precedente, i cui numeri `fase-1-esiti-lab-frame.md` dichiara superati: sono la
mesh troncata dal tetto ereditato di 100.000 punti di Steiner, e la firma è
esatta — 313.154 nodi meno i 213.154 vertici della superficie fanno 100.000.
Una misura indipendente lo conferma: in quella mesh **tutti** i 313.154 nodi
stanno sul bordo, cioè i 100.000 punti aggiunti sono finiti interamente nella
suddivisione delle facce di ingresso, che è precisamente il meccanismo di
fallimento diagnosticato in `fase-1-min-ratio.md`.

Per non misurare la regola su una mesh che la pipeline di oggi non produce, il
maglio di volume di `lab_crop` è stato **rigenerato**, in sola lettura
sull'archivio e senza scrivere nulla al suo interno: `06_repaired.ply`
(213.154 vertici, 426.600 triangoli, volume racchiuso −173.282.926,9485 mm³)
è stato letto, l'avvolgimento dei triangoli capovolto in memoria — il volume
diventa +173.282.926,9485 mm³ — e passato a
`volume.tetrahedralize(min_ratio=1.8, max_steiner_points=-1, nobisect=True)`.
Risultato: **365.212 nodi, 1.607.146 tetraedri in 30,7 s, zero elementi
invertiti**, identico ai numeri registrati in `fase-1-min-ratio.md` per la
stessa configurazione. `align_to_axes` con riferimento i vertici della
superficie dà un'estensione di 213,97 × 2468,83 × 1693,99 mm. Su questo maglio
la tolleranza in vigore vale **4,854 mm**.

Le tabelle che seguono usano `muro` dall'archivio e `lab_crop` rigenerato. La
mesh troncata archiviata compare solo dove serve al confronto, sempre
dichiarata.

Tolleranza e set in vigore, ricalcolati dove l'archivio tace:

| corsa | artefatto | tolleranza | BASE | TOP | FACE_FRONT | FACE_BACK | SIDE_LEFT | SIDE_RIGHT |
|---|---|---|---|---|---|---|---|---|
| `muro` | `wall_model.vtu` (archivio, valore confermato da `metrics.json`) | 31,945 mm | 4738 | 3468 | 224.875 | 122.728 | 4272 | 4085 |
| `lab_crop` | rigenerato con `nobisect` (ricalcolato) | 4,854 mm | 850 | 23 | 37 | 79 | 166 | 48 |
| `lab_crop` | `wall_model.vtu` archiviato, corsa superata (ricalcolato) | 5,678 mm | 1289 | 11 | 196 | 145 | 393 | 2717 |

## La forma dei due modelli, misurata prima di ogni altra cosa

Nessuna delle sei domande si risponde correttamente senza sapere che forma
hanno i due solidi, e le due forme non sono quelle che il nome suggerisce.

`muro` riempie il proprio parallelepipedo al **96,1%** (53,873 m³ di volume
contro 56,064 m³ di scatola): è un blocco pieno, senza aperture. La mappa di
occupazione dei baricentri dei tetraedri nel piano lunghezza-altezza ha tutte
e 3040 le celle occupate.

`lab_crop` riempie il proprio parallelepipedo al **19,4%** (0,173 m³ contro
0,895 m³). La stessa mappa, sul maglio rigenerato:

```
z=  1655 |################################################################|
z=  1578 |################################################################|
z=  1501 |################################################################|
z=  1424 |######                                                    ######|
z=  1347 |######                                                    ######|
   ...   |######                                                    ######|
z=   115 |######                                                    ######|
z=    38 |######                                                    ######|
         y=0                                                    y=2469
```

**`lab_frame` è un telaio**, non un muro pieno: due piedritti alle estremità
della lunghezza e un architrave in testa, e il vano vuoto in mezzo. Il nome del
file lo diceva. L'apertura scende fino al piede del ritaglio senza incontrare
un davanzale, quindi è un vano di porta oppure una finestra il cui davanzale
cade sotto la scatola di ritaglio: la mappa non distingue i due casi e la
distinzione non serve a nulla di ciò che segue. La conseguenza è diretta e domina tutte le misure
che seguono: solo una piccola parte dell'impronta poggia a terra, e
l'intradosso dell'architrave — la superficie che chiude il vano dall'alto — sta
a **1493,5 mm su 1693,99 mm di altezza**, cioè all'88,2% dell'altezza, con la
normale rivolta verso il basso.

## Il metodo delle colonne

Le domande 1, 3 e 5 chiedono se una faccia è piatta e quanto un set la copra.
Contare i nodi non basta: un set può avere molti nodi tutti ammucchiati in un
angolo. La misura usata qui è la **copertura per colonne**.

L'impronta ortogonale a un asse viene divisa in celle quadrate di lato
`L = 4·s`, con `s` la mediana della lunghezza degli spigoli di bordo. Una
colonna è **occupata** se contiene almeno un nodo di bordo, ed è **a contatto**
se il suo estremo lungo l'asse cade entro il 2% dell'estensione dall'estremo
globale — cioè se in quel punto il solido tocca davvero il piano di
riferimento. L'**ondulazione** è, sulle sole colonne a contatto, la distanza
fra l'estremo della colonna e l'estremo globale: è quanto la faccia si scosta
dal proprio piano di appoggio. La **copertura** di una tolleranza è la
frazione di colonne a contatto che contengono almeno un nodo del set, e la
**contaminazione** («% fuori») è la frazione di nodi del set che cadono in
colonne non a contatto, cioè presi da tutt'altra parte del modello.

Il lato `L = 4·s` non è arbitrario: con `L = s` la griglia è più fine dei
triangoli della faccia inferiore di `muro`, che ha spigoli con p95 di 47,4 mm,
e una colonna su dieci risulta priva di nodi bassi per puro artefatto di
griglia — il novantesimo percentile del profilo inferiore sale a 7803,61 mm su
7823,59 mm di altezza, cioè al soffitto del modello. Misurato, e scartato per
questo.

## Le sei domande

### 1. La base è piatta?

No, in nessuno dei due modelli, e l'ordine di grandezza è il centimetro.

| grandezza | `muro` | `lab_crop` |
|---|---|---|
| lato della cella `L = 4·s` | 54,91 mm | 21,52 mm |
| colonne occupate | 2460 | 1150 |
| colonne a contatto | 2438 (99,11%) | **187 (16,26%)** |
| area a contatto | 7,3510 m² su 7,1660 m² d'impronta | 0,0866 m² su 0,5283 m² |
| ondulazione p50 | 29,50 mm | 13,84 mm |
| ondulazione p90 | 48,05 mm | 20,61 mm |
| ondulazione p95 | 49,97 mm | 24,97 mm |
| ondulazione p99 | 69,81 mm | 32,09 mm |
| ondulazione massima | 80,93 mm | 33,86 mm |
| ondulazione p95 / altezza | 0,64% | 1,47% |

La base di `muro` ondula di **50 mm al novantacinquesimo percentile** e di 81 mm
al massimo: la ricostruzione di Poisson non produce un piano, produce una
superficie ondulata. Quella di `lab_crop` ondula di 25 mm al p95. In entrambi i
casi una tolleranza di pochi millimetri non può coprire la faccia, e questo da
solo scarta ogni regola che dia una tolleranza dell'ordine dello spigolo.

L'area a contatto supera l'impronta su `muro` (7,3510 contro 7,1660 m²) perché
le celle di bordo sporgono oltre il perimetro: è un effetto di
discretizzazione della griglia, non un solido più largo della propria scatola.

### 2. Quanto vale la spaziatura dei nodi sul bordo?

| grandezza | `muro` | `lab_crop` |
|---|---|---|
| facce di bordo | 517.158 | 426.600 |
| spigoli di bordo unici | 775.737 | 639.900 |
| p05 | 0,008 mm | 1,107 mm |
| p25 | 0,287 mm | 4,946 mm |
| **p50 = `s`** | **13,728 mm** | **5,381 mm** |
| p75 | 33,532 mm | 6,239 mm |
| p95 | 47,415 mm | 7,613 mm |
| spigolo mediano di `06_repaired.ply` | 33,553 mm | 5,381 mm |

L'ultima riga è una trappola da segnalare a chi implementerà la regola. Su
`lab_crop`, tetraedrizzato con `tet.nobisect: true`, il bordo del maglio di
volume **è** la superficie di ingresso e le due mediane coincidono alla quarta
cifra. Su `muro`, con `nobisect` falso, TetGen suddivide le facce di ingresso e
il bordo del maglio è 2,4 volte più fitto della superficie da cui deriva
(13,728 contro 33,553 mm). La spaziatura da usare è quella del **maglio di
volume**, non quella della superficie riparata: è sul maglio che i set vengono
estratti.

### 3. Quanto copre `BASE` al variare della tolleranza? C'è un ginocchio?

Il ginocchio cercato dal piano **non esiste**. Su `muro`, spazzando dieci
tolleranze da 1 a 200 mm in scala logaritmica, `|BASE|` vale 1, 4, 30, 97,
635, 2162, 5318, 15.181, 25.726, 36.568: una crescita liscia, senza il gomito
che segnalerebbe «qui la faccia è appena stata coperta». La ragione è la
risposta alla domanda 1: la faccia non è un piano, è una superficie ondulata
su 81 mm, quindi non c'è una tolleranza oltre la quale il conteggio smette di
crescere in fretta. La regola non è deducibile dalla forma di questa curva, e
va derivata altrove.

Frazione delle colonne a contatto coperta dal set, al variare del fattore `k`
nella tolleranza `k·s` (la contaminazione è commentata subito sotto la tabella):

| `k` | `muro` BASE | `muro` TOP | `muro` SIDE_L | `muro` SIDE_R | `lab` BASE | `lab` TOP | `lab` SIDE_L | `lab` SIDE_R |
|---|---|---|---|---|---|---|---|---|
| 1 | 16,53% | 13,05% | 12,39% | 12,95% | 45,99% | 0,70% | 1,92% | 1,52% |
| 2 | 45,45% | 40,27% | 33,80% | 34,38% | 47,59% | 2,81% | 6,15% | 22,43% |
| 3 | 75,72% | 71,96% | 55,76% | 55,91% | 63,10% | 23,29% | 8,32% | 81,12% |
| 4 | 97,58% | 96,35% | 77,89% | 77,95% | 90,91% | 88,75% | 57,62% | 96,58% |
| 5 | 98,89% | 98,48% | 96,83% | 97,52% | 96,26% | 99,21% | **94,37%** | 98,73% |
| **6** | **100,00%** | **99,55%** | **98,42%** | **98,99%** | **98,93%** | **99,91%** | **98,72%** | **99,75%** |
| 7 | 100,00% | 99,96% | 99,48% | 99,66% | 100,00% | 100,00% | 99,49% | 99,87% |
| 8 | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% | 99,74% | 99,87% |
| 12 | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% | 100,00% |

La contaminazione di questi otto set non supera lo **0,01%** fino a `k = 6` su
entrambi i modelli — è 0,00% ovunque tranne `SIDE_LEFT` di `muro`, che vale
0,01% da `k` = 3 in poi — e non supera lo 0,03% fino a `k = 8`: nessun nodo di
`BASE` viene da una colonna che non poggia. Le due colonne di `FACE_FRONT` e
`FACE_BACK` sono omesse da questa tabella e trattate a parte, per un motivo che
è esso stesso un esito (vedi «Che cosa la regola non risolve»).

### 4. Quanti nodi ci si aspetta sulla faccia?

Con spaziatura `s`, uno strato singolo su un'area `A` contiene circa `A/s²`
nodi.

| stima | `muro` | `lab_crop` |
|---|---|---|
| impronta `x·y` | 7,1660 m² | 0,5283 m² |
| `impronta / s²` | 38.026 | 18.245 |
| area delle sole colonne a contatto | 7,3510 m² | **0,0866 m²** |
| strato singolo sulla faccia a contatto | **39.008** | **2992** |
| `BASE` in vigore | 4738 (**12,1%** di uno strato) | 850 (**28,4%**) |

Su `muro` le due stime coincidono, perché l'intera impronta poggia. Su
`lab_crop` differiscono di sei volte, e la differenza è la misura del telaio: la
stima sull'impronta intera (18.245) descrive un muro pieno che lì non c'è.

`BASE` in vigore vale un ottavo di uno strato su `muro`. Non è «piccolo»: è
un vincolo che lascia scoperta la maggior parte della faccia d'appoggio — il
55,78% delle colonne a contatto ha almeno un nodo vincolato, il restante 44,22%
no.

### 5. Su `lab_crop`, `BASE` è piccolo per la tolleranza o per la geometria?

**Per entrambe, e la parte di geometria è quella dominante e irriducibile.**

Per la geometria: solo **187 colonne su 1150 (16,26%)** poggiano a terra, cioè
0,0866 m² di un'impronta di 0,5283 m². Sono i piedi dei due piedritti del
telaio. Uno strato singolo su quell'area vale 2992 nodi, non 18.245: nessuna
tolleranza potrà mai fare di `BASE` una frazione grande del modello, e non
deve, perché quella è la superficie d'appoggio fisica.

Per la tolleranza: entro quel limite, una tolleranza che funziona esiste. Con
`k = 6`, cioè 32,28 mm, `BASE` passa da 850 a **5915 nodi** coprendo il
**98,93%** delle colonne a contatto, con **0,00%** di nodi presi fuori da esse.
E `TOP` non esplode: passa da 23 a 34.866 nodi coprendo il 99,91% delle sue
colonne — un numero grande in assoluto (9,5% del modello) ma corretto, perché
l'estradosso dell'architrave copre davvero tutta l'impronta.

La risposta è quindi affermativa nei termini in cui la domanda la ammette: la
scansione **ha** una base d'appoggio, sono i due piedritti, ed è raggiungibile
con la regola raccomandata. Ciò che non ha è una base larga quanto l'impronta,
e nessuna regola può inventarla.

### 6. La selezione per normale funzionerebbe?

**No.** È la controprova esatta del difetto sospettato dal piano.

Facce di bordo classificate per componente dominante della normale uscente
(orientata verso l'esterno con il quarto nodo del tetraedro):

`muro`:

| classe | facce | area | nodi | quota p50 | quota p90 | quota p99 |
|---|---|---|---|---|---|---|
| −x | 261.520 | 44,7173 m² | 137.224 | 3621,8 | 7079,9 | 7745,7 |
| +x | 164.364 | 44,6842 m² | 84.017 | 3152,6 | 7353,8 | 7761,6 |
| −y | 21.093 | 9,1302 m² | 11.620 | 3566,7 | 6985,1 | 7789,1 |
| +y | 32.510 | 9,1554 m² | 20.163 | 3033,3 | 6638,2 | 7710,2 |
| **−z** | 23.093 | **6,9117 m²** | 14.499 | **41,6** | 6661,1 | 7731,8 |
| +z | 14.578 | 6,9730 m² | 8290 | 7785,8 | 7809,7 | 7818,2 |

`lab_crop`:

| classe | facce | area | nodi | quota p50 | quota p90 | quota p99 |
|---|---|---|---|---|---|---|
| −x | 102.742 | 1,0663 m² | 65.494 | 1277,8 | 1633,1 | 1672,8 |
| +x | 101.767 | 1,0870 m² | 61.150 | 1279,0 | 1634,6 | 1673,3 |
| −y | 62.131 | 0,6249 m² | 43.490 | 965,1 | 1572,1 | 1672,8 |
| +y | 58.548 | 0,6346 m² | 39.937 | 975,7 | 1573,2 | 1672,3 |
| **−z** | 50.263 | **0,5388 m²** | 35.484 | **1493,5** | 1566,9 | 1654,2 |
| +z | 51.149 | 0,5378 m² | 36.225 | 1671,9 | 1677,3 | 1682,9 |

Le quote sono in mm dal minimo. Il verdetto sta nella riga −z e nelle due
misure che la scompongono:

| grandezza | `muro` | `lab_crop` |
|---|---|---|
| nodi della classe −z entro l'1% dell'altezza | 9847/14.499 (**67,92%**) | 2106/35.484 (**5,94%**) |
| nodi della classe −z entro il 5% dell'altezza | 9893/14.499 (68,23%) | 3225/35.484 (9,09%) |
| area della classe −z sopra il 10% dell'altezza | 0,0041 m² su 6,9117 (**0,1%**) | 0,4732 m² su 0,5388 (**87,8%**) |
| quota mediana dei nodi della classe −z | 41,6 mm su 7823,59 (0,5%) | 1493,5 mm su 1693,99 (**88,2%**) |

Su `muro` la regola per normale sarebbe sana: lo 0,1% dell'area rivolta verso
il basso sta fuori posto. Su `lab_crop` è **catastrofica**: l'87,8% dell'area
rivolta verso il basso è l'intradosso dell'architrave, a 1493,5 mm su 1693,99
di altezza, e finirebbe in `BASE` — un modello appeso per il soffitto del
proprio vano di porta. Il sospetto del piano era corretto nel meccanismo e
sottostimato nell'entità: non una coda di intradossi, la quasi totalità della
classe.

Vale la pena notare, perché è il motivo per cui l'errore sarebbe passato
inosservato, che la classe −z di `lab_crop` ha un'area (0,5388 m²) quasi
identica a quella della classe +z (0,5378 m²) e all'impronta (0,5283 m²):
guardando solo le aree la classificazione sembra impeccabile.

## La regola raccomandata

> **La tolleranza dei set è un multiplo della spaziatura dei nodi sul bordo del
> maglio di volume.**
>
> ```
> facce_di_bordo = facce triangolari dei tetraedri con occorrenza singola
> s              = mediana della lunghezza degli spigoli unici di quelle facce
> tolleranza     = analysis.set_tolerance_factor * s
> ```
>
> con **`set_tolerance_factor = 6`** come nuovo predefinito.
> `build_node_sets` resta invariata: cambia solo il numero che riceve.

La forma dell'intervento è la più piccola possibile: `abaqus.set_tolerance` ha
già la firma giusta — `(nodes, tets, factor)` — e già oggi ricava una lunghezza
dai tetraedri; cambia il modo in cui la ricava. `analysis.set_tolerance_factor`
resta l'unico parametro configurabile, nell'unico luogo dove un predefinito di
elaborazione può stare, e cambia solo il suo valore e la sua descrizione. La
macchina per estrarre le facce a occorrenza singola esiste già in
`abaqus._boundary_nodes`: la via lazy è esporre `_boundary_faces(tets)` e
riscrivere `_boundary_nodes` come `np.unique(_boundary_faces(tets))`, senza
introdurre un secondo algoritmo che fa la stessa cosa.

I sei set sotto la regola, confrontati con quelli in vigore e con lo strato
singolo atteso:

`muro` — `s` = 13,7277 mm, tolleranza **82,37 mm** (in vigore 31,945 mm):

| set | in vigore | sotto la regola | strato singolo | copertura | contaminazione |
|---|---|---|---|---|---|
| BASE | 4738 | **18.020** | 39.008 | 100,00% | 0,00% |
| TOP | 3468 | **13.932** | 38.976 | 99,55% | 0,00% |
| FACE_FRONT | 224.875 | 241.021 | 239.504 | 100,00% | 0,42% |
| FACE_BACK | 122.728 | 137.151 | 239.328 | 100,00% | 0,82% |
| SIDE_LEFT | 4272 | **15.417** | 52.544 | 98,42% | 0,01% |
| SIDE_RIGHT | 4085 | **15.807** | 52.256 | 98,99% | 0,00% |

`lab_crop` — `s` = 5,3808 mm, tolleranza **32,28 mm** (in vigore 4,854 mm):

| set | in vigore | sotto la regola | strato singolo | copertura | contaminazione |
|---|---|---|---|---|---|
| BASE | 850 | **5915** | 2992 | 98,93% | 0,00% |
| TOP | 23 | **34.866** | 18.208 | 99,91% | 0,00% |
| FACE_FRONT | 37 | 105.878 | — | non utilizzabile | 99,21% |
| FACE_BACK | 79 | 96.459 | — | non utilizzabile | 99,10% |
| SIDE_LEFT | 166 | **25.668** | 12.496 | 98,72% | 0,00% |
| SIDE_RIGHT | 48 | **24.782** | 12.624 | 99,75% | 0,00% |

**La regola migliora entrambe le corse, e non a spese l'una dell'altra.** Il
`BASE` di `muro` passa dal 55,78% al 100,00% delle colonne a contatto, quello
di `lab_crop` dal 34,76% al 98,93%; nessun set su nessuno dei due modelli
peggiora in copertura. La contaminazione resta a 0,00% su tutti i set di
`lab_crop` tranne le due grandi facce, e su `muro` vale 0,01% su `SIDE_LEFT`,
0,00% su `BASE`, `TOP` e `SIDE_RIGHT`, e 0,42% e 0,82% sulle due grandi facce
— che sono un problema a sé e non un effetto della regola.

### Perché la spaziatura e non una frazione dell'estensione

La regola per frazione dell'estensione (`tolleranza = k · estensione`) funziona
numericamente: il 2% dell'estensione dà il 100% di copertura su entrambi i
modelli. È stata scartata da una misura, non da un'opinione. Il rapporto fra
l'ondulazione misurata di una faccia e la grandezza a cui la si vorrebbe
legare, confrontato fra i due modelli:

| set | ondulaz. p95 / `s`, `muro` | / `s`, `lab` | rapporto | ondulaz. p95 / estensione, `muro` | / estensione, `lab` | rapporto |
|---|---|---|---|---|---|---|
| BASE | 3,64 | 4,64 | 1,27 | 0,64% | 1,47% | 2,31 |
| TOP | 3,79 | 4,30 | 1,13 | 0,66% | 1,37% | 2,06 |
| FACE_FRONT | 0,95 | 0,75 | 0,79 | 1,06% | 1,88% | 1,77 |
| FACE_BACK | 1,10 | 0,78 | 0,71 | 1,23% | 1,97% | 1,60 |
| SIDE_LEFT | 4,72 | 5,05 | 1,07 | 1,11% | 1,10% | 0,99 |
| SIDE_RIGHT | 4,73 | 3,66 | 0,77 | 1,11% | 0,80% | 0,72 |

Misurata in spaziature, l'ondulazione trasferisce da un modello all'altro
entro un fattore **1,79** fra gli estremi (0,71 e 1,27). Misurata in frazioni
dell'estensione, entro un fattore **3,2** (0,72 e 2,31), e sui due set che
contano — `BASE` e `TOP` — sbaglia di più del doppio. La spaziatura è la scala
migliore perché l'ondulazione nasce nella ricostruzione, che ha la scala del
campionamento, non in quanto è alto il muro.

### Il predefinito 6 e il suo margine

Il criterio di accettazione usato per scegliere: **almeno il 95% delle colonne
a contatto coperto, su entrambi i modelli, per i quattro set utilizzabili**
(`BASE`, `TOP`, `SIDE_LEFT`, `SIDE_RIGHT`). Il 95% e non il 100% perché
l'ultimo 5% di colonne è dell'ordine del rumore della griglia di lato `4·s`: su
`muro` 22 colonne su 2460 non risultano a contatto per pura discretizzazione,
cioè lo 0,9%, e pretendere il 100% significherebbe tarare sul rumore. Il
criterio è dichiarato qui perché sia contestabile: cambiarlo cambia il valore
raccomandato, e la tabella dello sweep permette di rifare la scelta con un'altra
soglia senza rifare le misure.

Leggendo la tabella della domanda 3 riga per riga:

- **`k` = 4** fallisce nettamente: `SIDE_LEFT` e `SIDE_RIGHT` di `muro` si
  fermano al 77,89% e 77,95%, `SIDE_LEFT` di `lab_crop` al 57,62%.
- **`k` = 5** fallisce per un soffio, in un punto solo: `SIDE_LEFT` di
  `lab_crop` copre il **94,37%**, sotto la soglia. Tutti gli altri undici
  passano, il peggiore al 96,26%.
- **`k` = 6** passa ovunque, con il peggiore al **98,42%** (`SIDE_LEFT` di
  `muro`) e contaminazione non superiore allo 0,01% su tutti e otto.
- **`k` = 8** porta tutto sopra il 99,74%, ma costa: `BASE` di `muro` passa da
  18.020 a 25.450 nodi (**+41%**) per guadagnare l'1,58% di colonne che a 6
  già mancava soltanto a `SIDE_LEFT`.

**Il margine di 6 è quindi di un solo gradino sotto e di due sopra il
fallimento netto**, la stessa struttura del margine di `tet.min_ratio`: 5 è il
primo valore che non regge, 4 è il primo che crolla, e sopra 6 si compra
copertura marginale a prezzo pieno.

Il controllo incrociato conferma la scelta. Il fattore che servirebbe per
coprire l'ondulazione misurata, su tutte e dodici le combinazioni set × modello:

| percentile dell'ondulazione da coprire | fattore minimo | fattore massimo |
|---|---|---|
| p95 | 0,75 | 5,05 |
| p99 | 0,76 | 6,46 |
| massimo | 0,76 | 8,81 |

`k` = 6 copre il p95 su tutte e dodici — è il più piccolo intero di cui questo
si possa dire, perché il massimo richiesto è 5,05 — e il p99 su dieci su
dodici. Le due eccezioni sono i `SIDE_LEFT` dei due modelli, che
richiederebbero 6,46 e 6,42, e sono infatti i due set con la copertura più
bassa a `k` = 6 (98,42% e 98,72%): le tre misure indipendenti indicano lo
stesso punto debole, il che è una conferma e non una contraddizione.

### Il costo

Il calcolo di `s` sul maglio di volume — estrazione delle facce a occorrenza
singola, spigoli unici, mediana, con chiavi intere a una dimensione — costa
**2,28 s su `muro`** (1.752.795 tetraedri) e **2,15 s su `lab_crop`**
(1.607.146), contro **0,55 s e 0,47 s** dell'euristica in vigore. Sono circa
1,7 s in più su uno step 11 che segue uno step 9 da 31 a 45 s. Un'attuazione
ingenua, con `np.unique(..., axis=0)` invece delle chiavi intere, costa 6,5 s:
la differenza è nell'implementazione, non nella regola, e chi la scriverà
farebbe bene a usare le chiavi.

## Le regole considerate e scartate, con il numero che le ha scartate

| regola | numero che la scarta |
|---|---|
| **Volume medio dell'elemento** (in vigore) | `BASE` di `muro` = 4738 nodi, il **12,1%** di uno strato singolo, su appena il **55,78%** delle colonne a contatto. Su `lab_crop`, 850 nodi sul 34,76%. In più la grandezza è un artefatto del raffinamento: il volume medio è dominato da una manciata di elementi enormi (mediana 14,6 mm³ contro media 30.735 mm³, come già registrato nella docstring di `set_tolerance`). |
| **Volume mediano dell'elemento** | Già misurato e scartato prima di questo lavoro, citato senza rimisurarlo: tolleranza 2,50 mm su `muro` e `BASE` di **9 nodi** su 420.547. |
| **Spaziatura × 0,5** (il suggerimento di `fase-1-debito.md`) | 6,864 mm su `muro` → `BASE` = **138 nodi**, il 2,17% delle colonne a contatto, cioè 34 volte peggio dell'euristica che doveva sostituire. 2,690 mm su `lab_crop` → `BASE` = **7 nodi**, il 3,21%. Il suggerimento aveva la grandezza giusta e il fattore sbagliato di più di un ordine di grandezza. |
| **Selezione per direzione della normale** | Su `lab_crop` l'**87,8%** dell'area rivolta verso il basso (0,4732 m² su 0,5388) sta sopra il 10% dell'altezza: è l'intradosso dell'architrave, a 1493,5 mm su 1693,99. Solo il **5,94%** dei nodi di quella classe sta entro l'1% dell'altezza. Su `muro` la stessa regola sarebbe sana (0,1% dell'area fuori posto): una regola che dipende dalla presenza di aperture non è una regola. |
| **Frazione dell'estensione** (`k · estensione`) | Funziona, ma trasferisce peggio: il rapporto ondulazione/estensione varia di un fattore **3,2** fra i due modelli contro **1,79** del rapporto ondulazione/spaziatura, e su `BASE` e `TOP` sbaglia di 2,31 e 2,06 volte. Scartata come scala più debole, non come regola inutilizzabile. |
| **Ginocchio della curva `\|BASE\|`(tolleranza)** | Cercato su `muro` fra 1 e 200 mm e **non trovato**: 1, 4, 30, 97, 635, 2162, 5318, 15.181, 25.726, 36.568, senza gomito. Non c'è, perché la faccia non è un piano ma una superficie ondulata su 81 mm. |
| **Profilo per colonne come regola** (tolleranza = quantile dell'ondulazione misurata) | Non scartata dai numeri — è la misura su cui poggia tutto questo documento — ma dalla forma: richiede una griglia, un lato di cella e una soglia di contatto, cioè **tre** parametri nascosti al posto di uno, e `4·s` è già stato scelto misurando il fallimento di `1·s`. `k·s` ottiene lo stesso risultato con un parametro solo. |

## Che cosa la regola raccomandata **non** risolve

**1. `FACE_FRONT` e `FACE_BACK` su una scansione reale restano inutilizzabili,
per qualunque tolleranza.** È l'esito più netto fra quelli negativi. Su
`lab_crop`, solo **11 colonne su 2503** occupate (lo 0,44%) hanno il proprio
punto più avanzato entro il 2% dello spessore dal piano di riferimento. Sulla
stessa griglia `L = 4·s`, e su tutte le colonne e non solo quelle a contatto,
la faccia si scosta dal proprio piano di **15,46 mm alla mediana**, 27,91 mm al
p95 e **158,09 mm al p99**, con un massimo di 190,43 mm su uno spessore totale
di 213,97 mm — cioè in qualche colonna il punto più avanzato della faccia
«anteriore» dista appena 23,5 mm dal piano posteriore. `FACE_BACK` dà
14,84 / 25,29 / 127,50 / 189,25 mm. Non esiste una
tolleranza sensata: a `1·s` il set ha 51 nodi, a `6·s` ne ha 105.878, cioè il
29% del modello, e il 99,21% di essi viene da colonne che non toccano il piano.
La superficie ricostruita di un muro reale non è planare rispetto al proprio
spessore, e nessuna regola per scostamento da un piano può estrarne le due
facce. Su `muro` sintetico gli stessi due set funzionano (100% di copertura,
0,42% e 0,82% di contaminazione), il che rende il difetto invisibile a chi
provi solo lì. Questi due set non entrano nelle condizioni al contorno —
`fixed_nset` è `BASE` — quindi il difetto non invalida il modello, ma va
dichiarato: **su una scansione reale sono decorativi.**

**2. Un davanzale o una mensola bassa entrerebbero in `BASE` in silenzio.** La
contaminazione misurata è 0,00% su entrambi i modelli solo perché nessuno dei
due ha materiale fra il suolo e `6·s`. Su una geometria che ne avesse — un
davanzale a 100 mm con un maglio di spaziatura 20 mm — la regola lo
vincolerebbe a terra senza che nulla lo segnali. **Non è misurato: nessuna
delle due corse disponibili ha una geometria simile.**

**3. ~~La regola non si verifica da sé.~~ Risolto in fase di implementazione.**
Nessuna metrica della pipeline diceva se `BASE` coprisse l'impronta d'appoggio
o solo una sua chiazza: il `metrics.json` riportava la cardinalità dei set, e
4738 nodi su una faccia coperta al 55,78% e 4738 su una coperta al 100% sono lo
stesso numero. La copertura per colonne è ora `abaqus.footprint_coverage`, entra
in `11_export` e ha una guardia che scatta sotto la metà.

Ha dimostrato la propria utilità il giorno in cui è nata, trovando un difetto
che nessuno cercava: il ripiego di `export_model` quando manca il riferimento —
la terna stimata sui nodi di bordo invece che sui vertici della superficie —
porta `BASE` da 18.020 nodi a **874** e la copertura al **44,23%**, e ora lo
dichiara.

**4. I nomi dei set restano convenzioni.** La regola cambia la tolleranza, non
l'identificazione: quale delle due grandi facce sia l'«anteriore» e quale il
lato «sinistro» resta indeciso, come già dichiara la docstring di
`build_node_sets`. Nulla di ciò che è misurato qui migliora quel punto.

**5. `BASE` resta piccolo dove la geometria lo impone.** Su `lab_crop` i 5915
nodi su 365.212 non sono un difetto della regola: l'appoggio fisico sono i due
piedritti del telaio, 0,0866 m² di un'impronta di 0,5283 m². Chi leggerà quel
numero senza aver visto la forma del modello lo scambierà per un fallimento
della regola, ed è il motivo per cui la mappa di occupazione sta in questo
documento.

**6. Il valore 6 è tarato su due geometrie.** Un muro pieno sintetico e un
telaio scansionato. Il criterio di accettazione, la tabella dello
sweep e i fattori richiesti dall'ondulazione sono qui perché la taratura si
possa rifare su una terza geometria senza ricominciare da capo — non perché 6
sia stato dimostrato universale.
