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

## Il fratello non sondato: `*DLOAD`

**Sì, persiste anche lui.** Misurato il 23 agosto 2026 con `ccx` 2.22 su
questa macchina arm64, in `sonda-dload.inp`, stesso tetraedro e stesso
incastro di `sonda.inp`.

`core/abaqus.py` apre **ogni** passo statico con `*DLOAD` e ripete al suo
interno la riga `ELSET, GRAV, ...` del peso proprio (vedi `_passo_statico`,
`write_inp`): questa non è una card che un passo dichiara una volta sola,
come il `*CLOAD` di un carico posizionato — è ripetuta apposta in ognuno.
`carichi.spinta` (`SPINTA_ORIZZONTALE`), però, aggiunge una **seconda** riga
`GRAV` nel **solo** passo in cui è dichiarata: nessun passo successivo la
ripete, e nessuna riga scrive mai `*DLOAD, OP=NEW`.

`sonda-dload.inp` ha tre passi statici sullo stesso tetraedro:

```
** PASSO 1: *DLOAD con GRAV verticale (100) e GRAV orizzontale (20).
*STEP
*STATIC
*DLOAD
TUTTO, GRAV, 100.0, 0.0, 0.0, -1.0
TUTTO, GRAV, 20.0, 1.0, 0.0, 0.0
...
** PASSO 2: *DLOAD con la sola GRAV verticale (100), nessun OP=NEW.
*STEP
*STATIC
*DLOAD
TUTTO, GRAV, 100.0, 0.0, 0.0, -1.0
...
** PASSO 3: *DLOAD, OP=NEW con la sola GRAV verticale (100): isola per contrasto.
*STEP
*STATIC
*DLOAD, OP=NEW
TUTTO, GRAV, 100.0, 0.0, 0.0, -1.0
...
```

Le reazioni sul set vincolato `BASSO`, per passo (`sonda.dat`, righe
`forces (fx,fy,fz) for set BASSO`, valori sui nodi 1, 2, 3):

| passo | `*DLOAD` dichiarato in quel passo | reazioni |
|---|---|---|
| 1 | verticale (100) + orizzontale (20) | `(7.476190E-06, 1.401786E-05, 2.616667E-05)` / `(-1.401786E-05, 0, 6.541667E-06)` / `(0, -1.401786E-05, 0)` |
| 2 | verticale (100) soltanto | **identiche, bit per bit**, a quelle del passo 1 |
| 3 | `*DLOAD, OP=NEW`, verticale (100) soltanto | diverse: `(1.401786E-05, 1.401786E-05, 3.270833E-05)` / `(-1.401786E-05, 0, 0)` / `(0, -1.401786E-05, 0)` |

Il passo 2 ridichiara la **stessa** riga verticale del passo 1 (stesso
`ELSET`, stessa direzione, stesso modulo) e non la raddoppia: la reazione
resta quella del passo 1, non il doppio. Ma la riga orizzontale, **mai
ripetuta** nel passo 2, resta comunque attiva: le reazioni del passo 2 sono
identiche a quelle del passo 1, non a quelle "sola verticale" che il passo 3
mostra per contrasto (dove `OP=NEW` azzera tutto e lascia solo ciò che quel
passo dichiara).

## Conseguenza

Una configurazione che dichiara `carichi.spinta` **insieme a** un
`carico_sommita` o a uno o più `carichi.posizionati` — la combinazione che
questa stessa fase rende possibile per la prima volta — scrive un deck dove
la spinta orizzontale, dichiarata una volta sola nel passo
`SPINTA_ORIZZONTALE`, resta attiva in **ogni** passo statico successivo:
`CARICO_TOP` e ciascun posizionato includerebbero silenziosamente anche la
spinta, sommata al proprio carico, senza che il nome del passo lo prometta e
senza che `ccx` emetta alcun avviso. È lo stesso guasto di `*CLOAD` misurato
sopra, sullo stesso meccanismo (`OP=NEW` assente), su una card diversa.

La corsa dimostrativa citata in questo documento (`lab_telaio_v4_posizionati_top`)
non dichiara `carichi.spinta` (`casi_di_carico` è `["GRAVITA", "PRESSA",
"TORSIONE"]`): i numeri già pubblicati in `docs/fase-5-analisi.md` e
`docs/fase-6-carichi.md` non sono toccati da questa misura. Il guasto è
nella combinazione `spinta` + (`carico_sommita` o `posizionati`), non ancora
corretto: **la scelta di come e dove chiuderlo resta aperta**, non è presa
in questo documento.
