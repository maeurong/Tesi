# Sonda: CalculiX accetta TRVEC su C3D4?

**Esito: no. `ccx` 2.22 rifiuta `TRVEC` con errore fatale e si ferma — exit 201,
nessun `.dat` scritto. Non e' la trappola del silenzio: la card non passa.**

Misurato il 22/08/2026 su `ccx` 2.22, arm64 (macOS 25.5.0, Darwin), binario
`~/.local/bin/ccx` -> `~/.local/share/calculix-2.22/bin/ccx`, `ccx -v` risponde
`This is Version 2.22`. Repo `maeurong/Tesi`, ramo `research/trvec-su-c3d4`,
partito da HEAD `6d3275c`.

Tutti i deck stanno in `meshrec/docs/fase-6-cantiere/sonda-trvec/`. Sono
sintetici: cubo unitario, materiale 210000 / 0.3, nessun numero del provino di
laboratorio e nessuna geometria del telaio. Ognuno si ricorre da solo con
`ccx <nome>` dentro quella cartella.

## Il deck di sonda

`cubo.inc` — cubo unitario in 6 `C3D4` (nodi 1-8, elementi 1-6). Faccia `z=0`
(nodi 1-4, nset `FISSI`) vincolata, faccia `z=1` (nodi 5-8, nset `LIBERI`)
libera. Due superfici nominate:

- `SOPRA` = piano `z=1`, facce `4, S3` e `5, S3`
- `LATO` = piano `y=0`, facce `5, S1` e `6, S1`

Generato da `genera_cubo.py`, che verifica jacobiano positivo su ogni tet e
somma dei volumi pari a 1.

**Area, misurata fuori dal solutore.** `meshrec.core.abaqus.surface_area`
(`meshrec/src/meshrec/core/abaqus.py:440`) sui nodi e sugli elementi del cubo:

    SOPRA 1.0
    LATO  1.0

Geometria nota: due triangoli rettangoli di cateti unitari, area 0.5 ciascuno,
totale 1.0 esatto. Le due misure coincidono. Il solutore non e' mai stato
interrogato sull'area.

## Perche' non un tet solo

Primo tentativo, `a-p.inp`: un `C3D4`, faccia caricata e faccia vincolata che
condividono nodi. `P = 1.0` su area 0.5, risultante attesa 0.5. `RF` sommava
`-1.666667E-01`, un terzo del dovuto.

Non e' un difetto della pressione. `a2-cload.inp` lo tara: `*CLOAD 4, 2, 0.5`
sul solo nodo libero da `total force` `0.000000E+00 -5.000000E-01 0.000000E+00`,
esatta. **`RF` non conta il carico esterno applicato a un nodo gia' vincolato.**
Nel tet solo, due nodi su tre della faccia caricata erano fissi: due terzi del
carico sparivano dalla lettura.

Conseguenza pratica: una superficie di carico che tocca la superficie di
vincolo rende `RF` inutilizzabile come controllo di conservazione. Il cubo
separa i due insiemi di nodi e la lettura torna esatta.

## 1. `ccx` 2.22 accetta `*DSLOAD` con `TRVEC` su C3D4?

No. `c-trvec.inp`, riga di carico

    SOPRA, TRVEC, 1.0, 0.0, 0.0, 1.0

`ccx` esce con **201** e stampa:

    *ERROR reading *DLOAD. Card image:
           SOPRA,TRVEC,1.0,0.0,0.0,1.0

    *ERROR in calinput: at least one fatal
           error message while reading the
           input deck: CalculiX stops.

Nessuna forma della riga passa. Quattro varianti provate, tutte exit 201:

| deck | riga di carico | exit | `*ERROR` |
|---|---|---|---|
| `c-trvec.inp` | `SOPRA, TRVEC, 1.0, 0.0, 0.0, 1.0` | 201 | 2 |
| `d-trvec-solo-modulo.inp` | `SOPRA, TRVEC, 1.0` | 201 | 2 |
| `p-trvec-minuscolo.inp` | `SOPRA, trvec, 1.0, 0.0, 0.0, 1.0` | 201 | 2 |
| `o-trvec-su-dload.inp` | `*DLOAD` / `4, TRVEC, 1.0, 0.0, 0.0, 1.0` | 201 | 2 |

Tre cose che questi quattro deck stabiliscono:

- **E' l'etichetta, non il conteggio dei campi.** `d-trvec-solo-modulo.inp`
  porta `TRVEC` con un solo valore e nessuna componente: muore lo stesso. Il
  controllo e' `e-p-campi-extra.inp`, che scrive `SOPRA, P, 1.0, 0.0, 0.0, 1.0`
  — etichetta valida piu' tre campi in eccesso: exit **0**, zero warning,
  risultante `1.000000E+00`. I tre numeri in piu' vengono ingoiati in silenzio.
- **Non e' un caso di maiuscole.** `ccx` normalizza: `p-trvec-minuscolo.inp`
  scrive `trvec` minuscolo e il messaggio d'errore lo rimanda maiuscolo,
  `SOPRA,TRVEC,...`. Stesso rifiuto.
- **`*DSLOAD` e `*DLOAD` condividono il lettore.** L'errore nomina sempre
  `*DLOAD` anche quando la card scritta e' `*DSLOAD`, e `TRVEC` su `*DLOAD`
  per elemento fallisce identico.

Il rifiuto non e' specifico di `TRVEC`: `f-etichetta-finta.inp` con
`SOPRA, XYZZY, 1.0` da' lo stesso exit 201 e lo stesso messaggio. `ccx` respinge
qualunque etichetta di carico distribuito che non conosce.

**Sintassi esatta, ordine argomenti, forma della riga: non esistono.** Non c'e'
forma valida di `TRVEC` in `ccx` 2.22.

## 2. Warning o errori? E' la trappola del momento?

**No, non e' la trappola.** L'errore e' fatale e rumoroso, il deck non gira,
nessun risultato viene prodotto. Il precedente del `*CLOAD` sul grado 4 di un
nodo C3D4 — accettato, ignorato, zero warning, zeri in uscita — **non si ripete
qui**. `TRVEC` non viene accettata affatto.

Tre dettagli operativi che pero' contano per la pipeline:

- **Zero `*WARNING` in tutte e 18 le corse**, comprese quelle fallite. `ccx`
  emette `*ERROR`, mai `*WARNING`, per questa classe di guasti. Il controllo di
  `meshrec/src/meshrec/core/solve.py:438` (`controlla_avvisi`: «Zero `*WARNING`
  da `ccx`, o i numeri non sono citabili») **non intercetta nulla di tutto
  questo**. Serve il codice d'uscita, o il conteggio di `*ERROR`.
- **`ccx` crea comunque il `.dat`, a zero byte.** `c-trvec.dat`,
  `i-p-e-trvec.dat`, `j-superficie-finta.dat`, `l-trvec-vettore-nullo.dat`:
  tutti presenti, tutti `0`. Un controllo del tipo «il `.dat` esiste» passa su
  un deck morto.
- **Exit code 201** e' il segnale affidabile. Zero sulle corse riuscite.

## 3. Risultante di reazione contro `trazione x area`

Per `TRVEC` la domanda **non si pone**: nessun deck gira, nessuna risultante
esiste. Misurata quindi sull'unica etichetta che `ccx` accetta su una
superficie, `P`, per fissare la precisione dello strumento.

`b-p.inp` — `SOPRA, P, 1.0`, area misurata a parte 1.0, risultante attesa 1.0:

    total force (fx,fy,fz) for set FISSI and time  0.1000000E+01
           1.387779E-17  0.000000E+00  1.000000E+00

Scarto sulla componente normale: `1.000000E+00` contro `1.0` atteso, cioe'
**sotto la risoluzione di stampa del `.dat`**, che da' sette cifre — quindi
scarto relativo ≤ 5e-7, e non e' misurabile piu' fine da qui. Le due componenti
trasverse danno `1.387779E-17` e `0.000000E+00`: il rumore aritmetico vero sta a
1e-17, quindi il limite e' la stampa, non il solutore.

Per confronto, `q-cload-equivalente.inp` (trazione tangenziale 1.0 in `+x` sulla
stessa faccia, portata a mano come `*CLOAD`):

    total force (fx,fy,fz) for set FISSI and time  0.1000000E+01
          -1.000000E+00 -6.938894E-18 -1.110223E-16

Stessa esattezza, direzione arbitraria, zero warning.

## 4. `P` e `TRVEC` possono coesistere nello stesso passo?

**Domanda vuota: `TRVEC` non esiste.** `i-p-e-trvec.inp` mette `SOPRA, P, 1.0` e
`LATO, TRVEC, 2.0, 0.0, 1.0, 0.0` nello stesso `*DSLOAD` — exit **201**, il
deck intero muore sulla seconda riga. Un `TRVEC` in mezzo a card valide non
degrada: abbatte tutto.

Due `P` su superfici diverse invece convivono. `h-p-due-superfici.inp`,
`SOPRA, P, 1.0` piu' `LATO, P, 2.0`: exit 0, zero warning,

    total force (fx,fy,fz) for set FISSI and time  0.1000000E+01
          -5.551115E-17 -1.000000E+00  1.000000E+00

La componente `z` resta `1.000000E+00`, identica a `b-p.inp`: le due card non
interferiscono. La componente `y` legge `-1.000000E+00` e non `-2.000000E+00`
perche' `LATO` tocca i nodi 1 e 2, che sono vincolati, e `RF` scarta il carico
applicato a un nodo gia' fisso — la stessa trappola misurata sopra sul tet solo,
non un difetto della sovrapposizione.

## 5. Il verso, e il sistema di riferimento

**`P` positiva comprime.** `b-p.inp` con `P = +1.0` sulla faccia `z=1`: il nodo
7 scende, `uz = -3.383272E-06`, e la reazione ai vincoli e' `+1.000000E+00` in
`z`. `g-p-negativa.inp` con `P = -1.0`: il nodo 7 sale, `uz = +3.383272E-06`,
reazione `-1.000000E+00`. La pressione positiva spinge lungo la normale
**entrante**.

Concorda con il manuale, §7.43 `*DLOAD` (fonte, non misura): «for pressure
loading the magnitude of the load is positive, for tension loading it is
negative».

**Sistema di riferimento di `TRVEC`: non applicabile.** La card non viene letta,
quindi non c'e' un sistema in cui interpretarla. In Abaqus, dove `TRVEC` esiste,
il vettore e' globale — ma non l'ho misurato e non c'e' niente da misurare in
`ccx`.

## Ingressi degeneri

| ingresso | deck | oracolo | misurato |
|---|---|---|---|
| superficie nominata inesistente | `j-superficie-finta.inp` | `ccx` protesta | exit 201, 3 `*ERROR`, `.dat` a 0 byte. Protesta, e nomina il colpevole |
| `TRVEC` vettore nullo `(0,0,0)` | `l-trvec-vettore-nullo.inp` | zero non distinguibile da card ignorata | exit 201. Non arriva mai a produrre uno zero: muore prima, sull'etichetta |
| `TRVEC` modulo zero, vettore non nullo | `m-trvec-modulo-zero.inp` | come sopra | exit 201, identico |
| corpo libero sotto `TRVEC` | `n-trvec-senza-vincolo.inp` | fallire per singolarita' | exit 201, ma per l'etichetta, non per la singolarita': il lettore muore prima del solutore |

Il primo caso stampa il messaggio utile:

    *ERROR reading *DLOAD: element set
           or facial surface NONESISTE
           has not yet been defined.

I tre casi `TRVEC` sono tutti indistinguibili tra loro, e questo **e' l'esito
buono**: nessuno dei tre puo' produrre uno zero silenzioso, perche' nessuno dei
tre supera il lettore del deck.

### Il corpo libero e' la trappola vera, e non riguarda `TRVEC`

`k-p-senza-vincolo.inp` — controllo del quarto caso degenere: stesso cubo,
nessun `*BOUNDARY`, carico `P` valido.

    exit=0
    warning=0
    error=0
    Job finished

    displacements (vx,vy,vz) for set LIBERI and time  0.1000000E+01
             5  3.424735E+09 -4.454392E+09 -1.478369E+10
             6  3.424735E+09 -1.017767E+09 -1.984465E+10
             7 -1.189023E+07 -1.017767E+09 -1.197734E+10
             8 -1.189023E+07 -4.454392E+09 -6.916379E+09

**`ccx` 2.22 non fallisce per singolarita'.** Esce a zero, scrive «Job
finished», non emette un solo warning, e stampa spostamenti dell'ordine di 1e10
su una geometria di lato 1. L'oracolo del brief («deve fallire per
singolarita', non stampare zeri») e' smentito da entrambi i lati: non fallisce,
e non stampa zeri — stampa spazzatura credibile come numero.

Questa e' la trappola del momento cercata, spostata: non sta in `TRVEC`, sta nel
deck senza vincoli. E `controlla_avvisi` (`solve.py:438`) la lascia passare
tutta, perche' non c'e' nessun `*WARNING` da contare.

## Fonti

Misure: mie, oggi, sui deck citati. Il resto e' documentazione, tenuta separata.

- Manuale CalculiX 2.22, §7.44 `*DSLOAD`, p. 475-477 —
  <https://www.dhondt.de/ccx_2.22.pdf>. Alla voce «Following line for pressure
  application on a surface» elenca: «Load label (**the only available right now
  is P for pressure**)».
- Stesso manuale, §7.43 `*DLOAD`, p. 470-473. Etichette di carico distribuito
  documentate: `Px`, `PxNUy` (con subroutine `dload.f`), `PxNP`, `EDNORx` (solo
  gusci), `CENTRIF`, `GRAV`, piu' le forze di volume. Nessuna trazione
  vettoriale.
- `TRVEC` **non compare da nessuna parte** nel manuale 2.22: `pdftotext -layout`
  sul PDF completo e `grep -c TRVEC` danno **0** occorrenze. `TRVEC` e' una
  etichetta Abaqus che CalculiX non ha mai implementato.
- Numerazione delle facce tetraedriche, stesso manuale: Face 1: 1-2-3,
  Face 2: 1-4-2, Face 3: 2-4-3, Face 4: 3-4-1. E' quella usata da `cubo.inc`.

## Raccomandazione (raccomandazione, non decisione)

Per una trazione di direzione arbitraria su una regione di superficie in
`ccx` 2.22 restano due strade, e la seconda e' quella pigra:

1. `PxNUy` con subroutine utente `dload.f` — richiede di ricompilare `ccx`, e
   comunque `dload.f` restituisce **la sola intensita' di una pressione**, che
   resta diretta lungo la normale. Non risolve la direzione arbitraria.
2. **`*CLOAD` nodale consistente.** `q-cload-equivalente.inp` lo mostra
   funzionante: trazione 1.0 in `+x` su una faccia di area 1.0, ripartita
   `area/3` per nodo di ogni triangolo, risultante `-1.000000E+00` esatta e zero
   warning. Il codice ha gia' i due pezzi che servono: `abaqus.element_surface`
   (`meshrec/src/meshrec/core/abaqus.py:334`) da' le coppie (elemento, faccia)
   della regione, e `abaqus.surface_area` (`:440`) le aree.

Il costo della seconda strada non e' il calcolo, e' l'indirizzamento della
regione — che e' lo stesso nodo aperto gia' registrato per la Fase 6.

Nota su `_passo_statico` (`meshrec/src/meshrec/core/abaqus.py:30`): oggi emette
`*DLOAD` alla riga 46 e, quando `pressure` e' dato, `*DSLOAD` con
`f"{pressure[0]}, P, {pressure[1]}"` alla riga 49. **Quella e' gia' l'unica
etichetta di superficie che `ccx` accetta.** Aggiungere `TRVEC` li' avrebbe
rotto ogni deck prodotto, in modo fatale e visibile.
