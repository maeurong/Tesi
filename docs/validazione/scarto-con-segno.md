# Errore geometrico con segno: materia inventata contro materia mancante

Misurato il 26/08/2026 per chiudere
[#73](https://github.com/maeurong/Tesi/issues/73).

## Perché il segno non è un dettaglio

L'errore geometrico che il programma pubblicava era **senza segno**:
`geometric_error` dà max e RMS nei due versi, `vertex_deviation` una distanza
per vertice. Nessuno dei tre distingue i due modi di sbagliare, che sul
modello a elementi finiti hanno conseguenze **opposte**:

- **materia inventata** — la superficie sta oltre il rilievo → volume, massa e
  rigidezza in più che nella realtà non ci sono;
- **materia mancante** — il rilievo sta fuori dalla superficie → il contrario.

I due spingono la frequenza propria in direzioni contrarie. Con un numero
senza segno, **un errore che si compensa in media sembra un errore piccolo** —
e sul modello non si compensa affatto, perché massa e rigidezza aggiunte da
una parte non tornano indietro dall'altra.

## Il reperto, sul telaio reale

Corsa `runs/lab_telaio_v2`: nuvola segmentata di **4 269 608** punti contro la
superficie riparata di 10 968 vertici e 21 932 facce. Tolleranza **5 mm**,
cioè `errore_geometrico_max` ratificata in
[#35](https://github.com/maeurong/Tesi/issues/35).

| | frazione dei punti | RMS | massimo |
|---|---|---|---|
| **materia mancante** (*limite superiore*) | ≤ 48,135 % | ≤ 12,413 mm | ≤ **737,695 mm** |
| **materia inventata** | 51,864 % | 5,473 mm | 30,681 mm |

I tre valori della materia mancante sono **limiti superiori**, non misure della sola
ricostruzione: qui occlusione e materia mancante si confondono, e il massimo di 737,7 mm è
quasi certamente occlusione. Il «≤» va citato insieme al numero — vedi
[Limiti dichiarati](#limiti-dichiarati).

| | |
|---|---|
| **bilancio medio con segno** | **+0,0718 mm** |
| modulo RMS | 9,4710 mm |
| recall (rilievo entro 5 mm) | 65,544 % |
| precision (modello entro 5 mm) | 75,018 % |

**Il bilancio con segno vale +0,07 mm mentre il modulo RMS vale 9,47 mm**: due
ordini di grandezza. Una metrica senza segno racconta «errore di 9,5 mm»; il
bilancio dice che i due modi quasi si annullano nella media. È esattamente il
caso che questa misura esiste per rendere visibile.

**E le due code sono di natura diversa.** Il lato mancante ha RMS 12,4 mm e un
massimo di **737,7 mm**; quello inventato ha RMS 5,5 mm e massimo 30,7 mm — un
fattore ventiquattro sul massimo. Non è lo stesso errore letto da due lati: è
un errore quasi simmetrico nella parte centrale e **fortemente asimmetrico
nelle code**.

### La controprova che rende i numeri citabili

Il modulo dello scarto con segno riproduce **cifra per cifra** il
`cloud_to_mesh` che quella stessa corsa aveva già pubblicato in
`metrics.json`:

| | pubblicato in `metrics.json` | qui |
|---|---|---|
| RMS | 9,471039772 | 9,471039772 |
| massimo | 737,694580078 | 737,694580078 |
| campioni | 4 269 608 | 4 269 608 |

Non è una misura nuova che contraddice la vecchia: è **la stessa misura,
decomposta**. E la decomposizione dice una cosa che l'aggregato non poteva:
quel massimo di 737,7 mm sta sul lato **mancante**.

## Le risposte alle domande del ticket

**Come si ottiene il segno.** Dal raycasting di Open3D
(`RaycastingScene.compute_signed_distance`), che dà la distanza dal solido
chiuso, **non** dalla proiezione sulla normale della faccia più vicina. La
differenza non è di comodo: la proiezione sbaglia il segno vicino agli
spigoli, dove la faccia più vicina è ambigua e la normale salta — ed è
esattamente dove una ricostruzione di Poisson tende a sbagliare. La superficie
di questa corsa è `watertight: true`, quindi il dentro/fuori è definito.

**Quale convenzione.** **Positivo = materia mancante**, cioè il punto rilevato
sta *fuori* dalla superficie. È inchiodata da un test con oracolo costruito
(nuvola spostata di 3 mm sopra e sotto una faccia), perché invertirla non
farebbe cadere nient'altro.

**Precision e recall a 5 mm.** *Recall* = frazione del rilievo riprodotta dalla
superficie entro tolleranza («quanto del rilievo è finito nel modello»).
*Precision* = frazione dei vertici della superficie sostenuta da un punto
rilevato («quanto del modello è sostenuto dal dato»). Non sono simmetriche e
nessuna delle due basta: una superficie che copre metà del pezzo ma bene ha
precision alta e recall basso; una che gonfia il pezzo ha il contrario.

## Limiti dichiarati

**L'occlusione e la materia mancante qui si confondono, e non è risolto.** Lo
scanner non vede dappertutto: una zona senza punti può essere superficie mai
rilevata invece che persa dalla ricostruzione. Il massimo di 737,7 mm è quasi
certamente di questa natura. **La materia mancante va quindi letta come limite
superiore**, non come misura della sola ricostruzione. Separare le due chiede
una stima della copertura che questa misura non fa.

**`precision` campiona i soli vertici**, quindi sottostima l'errore dove i
triangoli sono grandi — lo stesso limite che `vertex_deviation` già dichiara.
Campionare l'area richiederebbe un generatore pseudocasuale, e
[#66](https://github.com/maeurong/Tesi/issues/66) ha misurato che ciò che
dipende dal maglio dipende dalla piattaforma: un numero pubblicato non deve
cambiare fra due macchine.

## La lacuna di letteratura

Zero occorrenze su 17 articoli di `Articoli/` letti uno per uno (vedi
`docs/validazione/ricerca-letteratura-scan-to-fem.md`). M3C2 (Lague et al.
2013) è lo standard di fatto in geomorfologia per la distanza **con segno**
nuvola-nuvola, con intervallo di confidenza da rugosità locale ed errore di
registrazione; nella letteratura scan-to-FEM non compare.

Questa misura **non è M3C2**: M3C2 stima anche la significatività locale della
differenza, che qui non serve perché il bersaglio non è una seconda nuvola
rumorosa ma una superficie. Il debito che raccoglie da M3C2 è il principio —
la distanza fra due geometrie ha un verso, e buttarlo via perde metà
dell'informazione.

## Riproduzione

`meshrec/docs/fase-7-cantiere/scarto-con-segno.py`, con un `assert` per ogni
numero pubblicato e per la controprova contro `metrics.json`. Eseguito: tutti
gli assert passati.
