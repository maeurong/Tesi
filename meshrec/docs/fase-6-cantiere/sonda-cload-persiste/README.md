# Un `*CLOAD` resta attivo nel passo statico successivo, se nessuno lo azzera

**Sì.** Misurato il 22 agosto 2026 con `ccx` 2.22 su questa macchina arm64,
durante la scrittura del documento di esito della Fase 6.

## Perché la domanda

`core/abaqus.py` scrive un passo statico per ogni carico dichiarato
(`carichi.carico_sommita`, e da questa fase anche ogni voce di
`carichi.posizionati`), ciascuno con il proprio `*CLOAD`. Il documento di fase
e la sua stessa configurazione dichiarano che «ogni carico dichiarato è un
passo statico a sé, col solo peso proprio accanto»: l'aspettativa implicita è
che il secondo passo veda solo il proprio carico, non anche quello del passo
precedente.

Fino a questa fase nessun deck aveva mai avuto **due passi statici
consecutivi che dichiarano entrambi un `*CLOAD`**: `SPINTA_ORIZZONTALE` usa
`*DLOAD`, `CARICO_TOP` è sempre l'ultimo passo statico prima di `MODALE` (che è
`*FREQUENCY`, non statico). La Fase 6 introduce la prima configurazione che
mette due `*CLOAD` in sequenza — due `carichi.posizionati`, o un
`carico_sommita` seguito da un posizionato — e questa è la prima corsa reale
che li combina davvero.

## La sonda

`sonda.inp` è un tetraedro C3D4 solo, incastrato su tre nodi (`BASSO`), con
tre passi statici identici a parte i carichi:

```
** PASSO 1: un *CLOAD di -100 N sul grado 3 di ALTO.
*STEP
*STATIC
*CLOAD
ALTO, 3, -100.0
...
** PASSO 2: nessun *CLOAD dichiarato qui dentro.
*STEP
*STATIC
...
** PASSO 3: *CLOAD, OP=NEW senza dati: azzera i concentrati dei passi precedenti.
*STEP
*STATIC
*CLOAD, OP=NEW
...
```

Il passo 2 non dichiara alcun `*CLOAD`: se i carichi concentrati fossero
un'proprietà del solo passo che li dichiara, la reazione sul passo 2 dovrebbe
tornare a zero come sotto il solo incastro. Il passo 3 dichiara `*CLOAD,
OP=NEW` senza righe: è la card che, per le stesse regole Abaqus/CalculiX,
azzera esplicitamente i concentrati ereditati.

## Come si rifà

```
cd docs/fase-6-cantiere/sonda-cload-persiste
ccx -i sonda
```

## Cosa esce

Uscita 0, `Job finished`, zero `*WARNING`/`*ERROR`. Le reazioni sul set
vincolato `BASSO`, sommate per passo:

| passo | `*CLOAD` dichiarato in quel passo | Σfz misurata |
|---|---|---:|
| 1 | `ALTO, 3, -100.0` | **100,0 N** |
| 2 | *(nessuno)* | **100,0 N** |
| 3 | `*CLOAD, OP=NEW` (vuoto) | **0,0 N** |

Il passo 2 **eredita** i -100 N del passo 1 pur non dichiarando alcun
`*CLOAD` proprio: un carico concentrato scritto in un passo statico **resta
attivo in ogni passo successivo** finché qualcosa non lo sostituisce o non lo
azzera esplicitamente con `*CLOAD, OP=NEW`. Il passo 3 lo conferma per
contrasto: la stessa card, senza dati, riporta la reazione a zero.

## Conseguenza

`write_inp` (`core/abaqus.py`) scrive un `*CLOAD` per ogni carico posizionato
che ha una `forza`, e le righe del `*CLOAD` del momento (`coppia_equivalente`)
nel passo del carico successivo, ma **non** scrive mai `*CLOAD, OP=NEW` prima
di aprire il passo successivo. Il risultato: il secondo (e ogni successivo)
carico posizionato o `carico_sommita` in un deck che ne dichiara più di uno
**non è isolato** — la sua soluzione include anche il `*CLOAD` di ogni passo
precedente che ne aveva scritto uno. È esattamente il difetto che questo
progetto esiste per stanare: un errore silenzioso di `ccx`, zero avvisi, zero
errori, spostamenti e reazioni tutti finiti e plausibili — solo sbagliati
rispetto a quello che il nome del passo promette.

La corsa dimostrativa di questo stesso documento lo mostra su scala reale: le
reazioni `fz` sommate sul passo `TORSIONE` (`runs/lab_telaio_v4_posizionati/`)
coincidono, a sette cifre, con quelle del passo `PRESSA` precedente — la
coppia (a risultante netta nulla) non le sposta di un newton, perché la
reazione che si legge è ancora quella della forza di `PRESSA`, mai rimossa.
