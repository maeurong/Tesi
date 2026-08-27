# Errore geometrico con segno: materia inventata contro materia mancante

Misurato il 26/08/2026 per chiudere
[#73](https://github.com/maeurong/Tesi/issues/73). Giustificazione del segno
riscritta il 28/08/2026 per [#112](https://github.com/maeurong/Tesi/issues/112);
i riferimenti al codice sono per nome e verificati contro `main` a `a6e9f81`.

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
| **materia mancante** (*attribuibile alla ricostruzione: ≤*) | 48,135 % | 12,413 mm | **737,695 mm** |
| **materia inventata** | 51,864 % | 5,473 mm | 30,681 mm |

I tre valori sono **misurati**, e vanno citati nudi quando descrivono il reperto: il 48,135 % dei
punti *sta* fuori dalla superficie, e il massimo *vale* 737,695 mm. È l'**attribuzione** a essere
un limite superiore: occlusione e materia mancante qui si confondono, e la separazione **non è
fatta** — chiede una stima della copertura che questa misura non esegue. Citando la materia
mancante come errore della sola ricostruzione va quindi citato il «≤» — vedi
[Limiti dichiarati](#limiti-dichiarati).

| | |
|---|---|
| **`segno_definito`** | **`True`** |
| **bilancio medio con segno** | **+0,0718 mm** |
| modulo RMS | 9,4710 mm |
| recall (rilievo entro 5 mm) | 65,544 % |
| precision (modello entro 5 mm) | 75,018 % |

**`segno_definito` sta in cima apposta.** È la chiave che
`quality.scarto_con_segno` pubblica accanto a ogni misura, ed è la condizione
sotto cui tutte le altre righe di questa pagina si leggono come decomposizione
invece che come moduli. Quando è falsa, `modulo_rms` resta una misura e la
separazione fra «mancante» e «inventata» no. Misurata il 27/08/2026 —
`is_watertight True`, `is_oriented True`, quindi `segno_definito True` — con i
due limiti dichiarati sotto.

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
esattamente dove una ricostruzione di Poisson tende a sbagliare.

**Perché il dentro/fuori è definito, e non è la chiusura a garantirlo.** La
stesura precedente scriveva «la superficie è `watertight: true`, quindi il
dentro/fuori è definito». **L'inferenza è falsa**, e
[#48](https://github.com/maeurong/Tesi/issues/48) l'ha misurata falsa:
`is_watertight` conta gli spigoli, e una superficie capovolta ne ha due per
spigolo come una diritta. Chiusa e rovesciata supera quel controllo, e con essa
dentro e fuori si scambiano senza sintomo.
[#90](https://github.com/maeurong/Tesi/issues/90) ha tolto l'inferenza dal
codice: il controllo vero è `quality.is_watertight` **e** `quality.is_oriented`,
ed è quello che `quality.scarto_con_segno` pubblica nella chiave
`segno_definito`.

**Il meccanismo vero è un rovesciamento esplicito nella riparazione.** L'uscita
di Poisson arriva alla riparazione **orientata al contrario**, e le metriche
dello step 6 lo dicono: `volume_before` vale −63 147 900,67 mm³,
`orientation_flipped` vale `true`, `volume_after` vale +217 728 626,84 mm³.
`repair.repair_surface` calcola il volume racchiuso, e se è negativo scambia due
colonne di ogni faccia — un'inversione esatta, che non approssima nulla e non sposta un
vertice. **Il segno non viene dalla chiusura: viene da quella correzione.** Una
superficie chiusa e non raddrizzata avrebbe dato gli stessi moduli e i due modi
scambiati.

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
rilevata invece che persa dalla ricostruzione. **La separazione non è fatta**:
chiede una stima della copertura che questa misura non esegue, e senza quella
il massimo di 737,7 mm non è attribuito a nessuno dei due. I valori della
materia mancante restano misurati; è la loro **attribuzione alla sola
ricostruzione** a valere come limite superiore.

**`segno_definito` è stato misurato su una rifattura, non sulla corsa
congelata.** `runs/lab_telaio_v2` non è sulla macchina dove la verifica è stata
fatta: il 27/08/2026 la ricostruzione è stata rifatta da
`meshrec/casi/lab_telaio.yaml` sulla stessa nuvola (`lab_frame.pcd`,
151 898 491 byte) fino allo step 6 — oltre non serve, perché né i tetraedri né
il solutore entrano nel segno. Su quella superficie: `is_watertight True`,
`is_oriented True`, `segno_definito True`, con controprova indipendente di
Open3D (`is_orientable`, `is_vertex_manifold`, volume +2,177e8 mm³). **Le due
superfici non sono la stessa** (vedi il limite seguente), quindi in senso
stretto è stato misurato l'orientamento di quella di oggi. Chi ha accesso alla
corsa congelata chiude il residuo con
`quality.is_watertight(facce) and quality.is_oriented(facce)` su
`runs/lab_telaio_v2/06_repaired.ply`.

**La rifattura non riproduce la corsa pubblicata, e questo è un fatto sulla
riproducibilità.** Questa pagina pubblica **10 968** vertici e **21 932** facce;
la rifattura del 27/08/2026 ne dà **10 978** e **21 952** — dieci vertici e venti
facce di scarto. Configurazione identica e `seed: 0`, quindi **lo scostamento
viene da codice cambiato fra il 26/08 e il 27/08, non da rumore di esecuzione**.
La conseguenza non è sui numeri di questa pagina, che restano quelli della corsa
congelata: è che **la corsa non si rigenera identica a distanza di un giorno**, e
va saputo prima di citarla in un capitolo come se fosse riproducibile. Il
meccanismo del segno — il rovesciamento esplicito nella riparazione — non dipende
da quei dieci vertici.

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
