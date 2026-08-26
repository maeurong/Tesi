# Lo scarto C3D4 contro C3D10 sul telaio reale

Misurato il 26/08/2026 per chiudere
[#45](https://github.com/maeurong/Tesi/issues/45). È il numero che dice quanto
il tetraedro lineare stava sbagliando **sul nostro caso**, invece che sulla
mensola di Benzley.

## Come è stato misurato

Punto di partenza: la superficie **già riparata** della corsa di riferimento,
`runs/lab_telaio_v2/06_repaired.ply` — 10 968 vertici, 21 932 facce. Da lì si
tetraedrizza **due volte cambiando solo l'ordine**. Non è una
semplificazione: TetGen con `order=2` tiene gli **stessi tetraedri** e
aggiunge i sei nodi di lato, quindi «stesso maglio» è letterale e non
approssimato. Lo conferma il conteggio: **51 913 elementi in entrambi i
casi**, e **3 135 punti di Steiner** identici.

Ripetere segmentazione e ricostruzione di Poisson sui 6,3 milioni di punti
della nuvola non avrebbe aggiunto nulla al confronto, e avrebbe introdotto
una seconda differenza fra i due modelli.

Configurazione identica a `runs/lab_telaio_v2/config.yaml`: calcestruzzo
C25/30 (E = 31 500 MPa, ν = 0,2, ρ = 2,5·10⁻⁹ t/mm³), gravità 9 810 mm/s²,
vincolo `BASE` con `set_tolerance_factor` 6,0, spinta orizzontale 0,1 g in y,
20 modi. Solutore CalculiX 2.22 su macOS arm64.

**Le corse in `runs/` non sono state rigenerate**, come deciso in
[#41](https://github.com/maeurong/Tesi/issues/41): le due corse di questo
confronto sono state scritte fuori dall'albero del repository.

### La controprova che rende il confronto citabile

La corsa C3D4 di questo confronto **riproduce cifra per cifra** i numeri già
pubblicati in `docs/fase-5-analisi.md`:

| grandezza | fase 5, riga | qui |
|---|---|---|
| max \|U\| sotto peso proprio | 0,036730 mm (riga 406) | 0,036730 mm |
| prima frequenza | 21,19324 Hz (riga 521) | 21,19324 Hz |
| von Mises max, gravità | 0,5056 MPa (riga 438) | 0,505579 MPa |

Senza questa coincidenza il confronto misurerebbe anche la distanza fra
questa ricostruzione e la corsa vera, e non si saprebbe quanta parte dello
scarto venga dall'elemento.

## I due numeri, per ciascuna grandezza

Lo scarto è di **C3D4 rispetto a C3D10**, che è il riferimento migliore.

| grandezza | C3D4 | C3D10 | scarto |
|---|---|---|---|
| nodi | 14 103 | 91 084 | ×6,46 |
| elementi | 51 913 | 51 913 | **uguali** |
| gradi di libertà | 42 309 | 273 252 | ×6,46 |
| **massa [t]** | **0,5443209031** | **0,5443209031** | **0,00e+00** |
| secondi di solutore | 4,99 | 58,81 | ×11,77 |
| \|u\|max gravità [mm] | 0,036730 | 0,041911 | **−12,36 %** |
| \|u\|max spinta [mm] | 0,044611 | 0,050736 | **−12,07 %** |
| von Mises max gravità [MPa] | 0,505579 | 1,468121 | **−65,56 %** |
| von Mises max spinta [MPa] | 0,676343 | 1,523934 | **−55,62 %** |
| quota del picco, gravità [mm] | 1010,30 | 1008,75 | 1,55 mm |
| quota del picco, spinta [mm] | 1010,30 | 1009,70 | 0,59 mm |

Frequenze proprie, prime otto:

| modo | C3D4 [Hz] | C3D10 [Hz] | scarto |
|---|---|---|---|
| 1 | 21,19324 | 19,79322 | +7,07 % |
| 2 | 34,34059 | 32,16103 | +6,78 % |
| 3 | 43,13673 | 39,45246 | +9,34 % |
| 4 | 91,06687 | 85,10083 | +7,01 % |
| 5 | 108,43340 | 99,94075 | +8,50 % |
| 6 | 208,90730 | 194,93230 | +7,17 % |
| 7 | 210,90870 | 197,90650 | +6,57 % |
| 8 | 215,62920 | 200,28410 | +7,66 % |

## Che cosa dicono

**L'attesa della letteratura è confermata, non smentita.** C3D4 è più rigido,
quindi dà spostamenti **minori** (−12,4 %) e frequenze **maggiori** (da +6,6 %
a +9,3 %). Sono le due firme dello stesso difetto, e il ticket dichiarava che
uscire il contrario avrebbe significato un confronto sbagliato: non è
successo.

**La massa coincide fino all'ultima cifra**, scarto `0,00e+00`. Era il
controllo che il ticket stesso proponeva — la massa è geometria e non
formulazione — e passa esattamente.

**Il benchmark sintetico aveva predetto il caso reale.** Sulla mensola di
Gere-Timoshenko ([#47](https://github.com/maeurong/Tesi/issues/47)) C3D4
dava **−12,73 %** sulla freccia; qui, sul telaio rilevato, dà **−12,36 %**.
Quattro decimi di punto percentuale di distanza, su due geometrie che non
hanno niente in comune. È il risultato più forte di questa misura: il
provino di laboratorio non era un esercizio, prediceva il caso studio.

Sulla frequenza l'accordo è più largo — +11,71 % sulla mensola contro +7,07 %
qui — e non c'è ragione di aspettarselo stretto: la frequenza dipende dalla
distribuzione di massa e rigidezza dell'intera struttura, e un telaio a sei
membrature non è una mensola.

**La tensione è dove il lineare è peggio, e di molto.** −65,6 % sul picco di
von Mises sotto peso proprio. Concorda con la direzione già misurata in
[#55](https://github.com/maeurong/Tesi/issues/55), dove la colonna della
tensione si comportava diversamente da quella dello spostamento.

**Il picco però sta nello stesso posto**: 1,55 mm di differenza in quota su
una struttura alta oltre un metro. Il lineare sbaglia *quanto*, non *dove* —
distinzione che conta, perché è il *dove* che dice se il picco vive contro il
vincolo (`controlla_picco`).

**Il costo.** ×6,46 gradi di libertà per ×11,77 di tempo di solutore. Su
questo maglio si parla di 5 s contro 59 s: irrilevante. La non linearità del
costo va però dichiarata, perché su un maglio dieci volte più fine non lo
sarebbe.

## Quali numeri già pubblicati vanno annotati

Lo scarto **è grande**, quindi la domanda ha una risposta e non è «nessuno».

Le corse in `runs/` **non si rigenerano** (#41), e i documenti delle fasi 5 e
6 ne citano i numeri campo per campo. I numeri restano quindi quelli, con
l'annotazione di quanto valga lo scarto:

| documento | numero pubblicato | annotazione |
|---|---|---|
| `docs/fase-5-analisi.md:406` | max \|U\| 0,036730 mm | C3D4; **−12,36 %** rispetto a C3D10 sullo stesso maglio |
| `docs/fase-5-analisi.md:438` | von Mises 0,5056 MPa | C3D4; **−65,56 %** rispetto a C3D10 |
| `docs/fase-5-analisi.md:521,534` | 1ª frequenza 21,19324 Hz | C3D4; **+7,07 %** rispetto a C3D10 |
| `docs/fase-6-carichi.md:493` | 0,036730 mm e 0,5056 MPa | stessi scarti |

Non è una correzione dei documenti: è la banda entro cui quei numeri vanno
letti, e questa tabella è la fonte da citare accanto.

## Che cosa resta fuori, e perché

**Il carico posizionato in sommità non è confrontabile su C3D10.**
`abaqus.ripartisci` **solleva di proposito** (guardia introdotta con
[#45 parte prima](https://github.com/maeurong/Tesi/pull/53)): la ripartizione
per area tributaria vale per le facce a soli vertici, e su una faccia a sei
nodi darebbe tutto il carico ai vertici, dove il vettore dei carichi
consistenti dà **zero**. L'errore conserverebbe la risultante, quindi
`controlla_reazioni` non lo vedrebbe.

La formula giusta è `p·[0, 0, 0, A/3, A/3, A/3]` ed è verificata su fonte
primaria in `docs/validazione/carichi-consistenti-tet10.md` (Abaqus Theory
Guide §3.2.6, verbatim: «a constant pressure on an element face produces zero
equivalent loads at the corner nodes»). **È implementabile, ma non è stata
implementata qui**: nessuna delle cinque grandezze che #45 chiede ne ha
bisogno, perché gravità e spinta sono entrambe `*DLOAD, GRAV`, cioè forze di
massa che non passano da `ripartisci`.

Chi volesse il confronto anche sul caso `CARICO_TOP` deve prima implementare
quella formula.
