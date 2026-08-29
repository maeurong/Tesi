# Le sezioni a fibre di OpenSees: comandi, idioma, materiali, elementi, generatori

Ricerca del 28/08/2026, su repo `main` a `787fdeb`. Domanda posta: come chi usa
OpenSees davvero mette l'armatura in una sezione trasversale di cemento armato.
Si cercano soluzioni rodate, non idee.

Il documento gemello
[`ricerca-opensees-e-armature.md`](ricerca-opensees-e-armature.md) ha già chiuso
il fronte del continuo — elementi solidi, `TenNodeTetrahedron` e i suoi tre
difetti, `ASDEmbeddedNodeElement`, l'assenza di `*REBAR` in CalculiX — e nel suo
§2.1 dichiara la sezione a fibre «strada maestra, pienamente documentata» senza
scendere nei comandi. Questo documento scende nei comandi, e non ripete quel
lavoro.

Le fonti sono primarie: la documentazione ufficiale di OpenSeesPy, il wiki di
Berkeley, il nuovo sito di documentazione `opensees.github.io`, il sorgente di
OpenSees su GitHub al ramo `master`, e i metadati di PyPI e dell'API GitHub.
Dove una domanda si chiudeva contando, il conteggio è riportato con il comando
che lo produce.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte primaria in questa sessione (pagina
  ufficiale, file di sorgente, metadati).
- **[M]** = misurato o contato in questa sessione. Non è una citazione.
- **[INF]** = inferenza mia, non letta su fonte. Da non citare come fatto.
- **[NON TROVATO]** = non l'ho trovato pubblicato in chiaro. Non l'ho inventato.

I blocchi di codice sono **trascritti**, non parafrasati, e portano i numeri
come la fonte li scrive: dentro un blocco `così` il punto resta il separatore
decimale inglese.

## Artefatti consultati

| artefatto | provenienza | stato |
|---|---|---|
| documentazione OpenSeesPy 3.5.1.3, pagine dei comandi di sezione, materiale ed elemento | <https://openseespydoc.readthedocs.io/en/latest/> | letta pagina per pagina [V] |
| wiki OpenSees di Berkeley, pagine `Fiber_Section`, `Patch_Command`, `Layer_Command`, `Moment_Curvature_Example` | <https://opensees.berkeley.edu/wiki/> | lette [V] |
| documentazione nuova, pagina `forceBeamColumn` | <https://opensees.github.io/OpenSeesDocumentation/> | letta [V] |
| sorgente OpenSees, ramo `master` a `2890cb3` (14/08/2026) | <https://github.com/OpenSees/OpenSees> | letti `TclModelBuilderSectionCommand.cpp`, `ElasticBeam3d.cpp`, `FiberSection3d.cpp` [V] |
| `BuildRCrectSection.tcl` della galleria PEER | <https://github.com/peer-open-source/opensees-gallery>, licenza BSD-3-Clause | scaricato e trascritto per intero [V] |
| sorgente `opsvis`, file `fibsec.py` | <https://github.com/sewkokot/opsvis>, licenza GPL-3.0 | letto [V] |
| metadati PyPI di `openseespy`, `opsvis`, `concreteproperties`, `sectionproperties` | <https://pypi.org/> | interrogati [M] |

**Premesse del committente, ricontrollate prima di ragionarci sopra.** Tutte e
quattro risolvono per riga sul commit corrente: `wall.py:764` porta `def prior(`,
`hexa.py:758` porta `def costruisci(`, `config.py:244` porta
`element: Literal["C3D10", "C3D4"]`, `solve.py:231` porta `def leggi_frd(`. [V]

**Una correzione marginale, che non sposta il compito.** Il brief chiama la
sezione di `wall.prior` una «coppia (larghezza, altezza)». Il campo è
`wall.Membratura.sezione` e la sua docstring dice altro: «Le due estensioni
trasversali all'asse [mm]». Sono i due `ptp` della nuvola di regione proiettata
su una base ortonormale `e1`, `e2` costruita dentro `wall.misura`. Non sono
larghezza e altezza in nessun senso etichettato: sono l'ingombro della sezione
lungo due direzioni che il programma sceglie e **non restituisce**. La
distinzione conta, e il §6 la usa. [V]

---

## 1. I comandi (domanda a)

### 1.1 La sezione

Firma OpenSeesPy, due forme alternative, verbatim: [V]

    section('Fiber', secTag, '-GJ', GJ)
    section('Fiber', secTag, '-torsion', torsionMatTag)

Argomenti, verbatim dalla stessa pagina:

| argomento | tipo | descrizione della fonte |
|---|---|---|
| `secTag` | int | «unique section tag» |
| `GJ` | float | «linear-elastic torsional stiffness assigned to the section» |
| `torsionMatTag` | int | «uniaxialMaterial tag assigned to the section for torsional response (can be nonlinear)» |

E la frase che definisce l'oggetto, verbatim:

> «Each FiberSection object is composed of Fibers, with each fiber containing a
> UniaxialMaterial, an area and a location (y,z).»

La stessa pagina dichiara i gradi di libertà della sezione: `[P, Mz]` in due
dimensioni, `[P, Mz, My, T]` in tre. [V]

Forma Tcl, dal wiki di Berkeley: [V]

    section Fiber $secTag <-GJ $GJ> {
        fiber ...
        patch ...
        layer ...
    }

La differenza fra i due interpreti è di **sintassi, non di modello**: in Tcl le
fibre stanno dentro un blocco fra graffe, in Python i comandi `fiber`, `patch` e
`layer` si chiamano dopo `section` e valgono per la sezione «corrente». Il
sorgente lo conferma: `TclModelBuilderSectionCommand.cpp` tiene una variabile
statica `currentSectionTag`, e il messaggio d'errore del comando `fiber` dice
verbatim «WARNING subcommand 'fiber' is only valid inside a 'section' command».
[V]

### 1.2 `fiber` — la singola fibra

Firma OpenSeesPy, verbatim: [V]

    fiber(yloc, zloc, A, matTag)

| argomento | descrizione della fonte |
|---|---|
| `yloc` | «y coordinate of the fiber in the section (local coordinate system)» |
| `zloc` | «z coordinate of the fiber in the section (local coordinate system)» |
| `A` | «cross-sectional area of fiber» |
| `matTag` | tag di `UniaxialMaterial` in una `FiberSection`, di `NDMaterial` in una `NDFiberSection` |

**Ruolo nella sezione armata**: è la via di ultima istanza. Serve quando una
barra sta dove nessun `layer` la mette — un ferro d'angolo di diametro diverso,
una barra spostata — oppure quando la sezione di calcestruzzo non è
decomponibile in patch regolari e la si vuole discretizzare cella per cella.
Costa una chiamata per fibra.

### 1.3 `patch` — il calcestruzzo

Frase introduttiva, verbatim: [V]

> «The patch command is used to generate a number of fibers over a
> cross-sectional area. Currently there are three types of cross-section that
> fibers can be generated: quadrilateral, rectangular and circular.»

**Quadrilatero.** Firma OpenSeesPy e Tcl: [V]

    patch('quad', matTag, numSubdivIJ, numSubdivJK, *crdsI, *crdsJ, *crdsK, *crdsL)
    patch quad $matTag $numSubdivIJ $numSubdivJK $yI $zI $yJ $zJ $yK $zK $yL $zL

> «This is the command to generate a quadrilateral shaped patch (the geometry of
> the patch is defined by four vertices: I J K L. The coordinates of each of the
> four vertices is specified in COUNTER CLOCKWISE sequence)»

`numSubdivIJ` è «number of subdivisions (fibers) in the IJ direction»,
`numSubdivJK` la stessa cosa nella direzione JK; `crdsI`…`crdsL` sono «y &
z-coordinates of vertices ... in local coordinate system». Il verso antiorario
non è un consiglio di stile: decide il segno dell'area delle fibre.

**Rettangolo.** [V]

    patch('rect', matTag, numSubdivY, numSubdivZ, *crdsI, *crdsJ)
    patch rect $matTag $numSubdivY $numSubdivZ $yI $zI $yJ $zJ

> «This is the command to generate a rectangular patch. The geometry of the
> patch is defined by coordinates of vertices: I and J. To ensure positive fiber
> areas are created, (zJ-zI)/(yJ-yI) should be positive.»

Cioè: I è l'angolo «basso a sinistra» e J quello «alto a destra» nel piano
(y, z). È il `patch quad` con i due vertici opposti al posto di quattro, e la
condizione sul rapporto è la stessa condizione di verso scritta in un altro modo.

**Cerchio.** [V]

    patch('circ', matTag, numSubdivCirc, numSubdivRad, *center, *rad, *ang)
    patch circ $matTag $numSubdivCirc $numSubdivRad $yCenter $zCenter $intRad $extRad $startAng $endAng

`numSubdivCirc` è «number of subdivisions (fibers) in circumferential direction
(number of wedges)», `numSubdivRad` «number of subdivisions (fibers) in radial
direction (number of rings)»; `rad` è «internal & external radius», `ang`
«starting & ending-coordinates angles (degrees)». Il raggio interno esiste
perché il comando serve anche le sezioni cave.

**Ruolo nella sezione armata**: il `patch` è il calcestruzzo, e sempre **almeno
due** — uno per il nucleo confinato con il proprio materiale, uno o più per il
copriferro non confinato con un materiale diverso. È la ragione per cui esiste
il concetto di patch multipli: non la geometria, i due materiali.

### 1.4 `layer` — le barre

Firme OpenSeesPy e Tcl: [V]

    layer('straight', matTag, numFiber, areaFiber, *start, *end)
    layer straight $matTag $numFiber $areaFiber $yStart $zStart $yEnd $zEnd

    layer('circ', matTag, numFiber, areaFiber, *center, radius, *ang=[0.0, 360.0-360/numFiber])
    layer circ $matTag $numFiber $areaFiber $yCenter $zCenter $radius <$startAng $endAng>

| argomento | descrizione della fonte |
|---|---|
| `numFiber` | «number of fibers along line» |
| `areaFiber` | «area of each fiber» |
| `start` / `end` | «y & z-coordinates of first/last fiber in line (local coordinate system)» |
| `center`, `radius`, `ang` | centro, raggio dell'arco, angolo iniziale e finale (opzionali) |

Le due frasi di definizione, verbatim: `layer straight` «is used to construct a
straight line of fibers», `layer circ` «is used to construct a line of fibers
along a circular arc». Il predefinito dell'angolo finale della variante
circolare — `360.0-360/numFiber` — è quello che distribuisce `numFiber` barre
**equispaziate sull'intero cerchio senza raddoppiare l'ultima**: è il caso della
colonna circolare.

**Ruolo nella sezione armata**: `layer` è l'armatura longitudinale, e la posa
**una barra per volta**, con l'area vera di ciascuna e le coordinate vere.
Nessuno «strato spalmato»: `numFiber` fibre discrete, ognuna con `areaFiber`. È
la differenza che separa questo modello dal guscio composito che il manuale di
CalculiX propone al §2.11, dove l'acciaio è uno strato di spessore equivalente
(si veda [`ricerca-opensees-e-armature.md`](ricerca-opensees-e-armature.md) §3.3).

**Le staffe non entrano nella sezione a fibre.** Nessuno dei comandi le
rappresenta: l'armatura trasversale entra solo attraverso i *parametri del
materiale* del calcestruzzo di nucleo. Il §3.4 lo riprende.

### 1.5 Alias, e perché contano se si genera codice

Letti sul sorgente, `TclModelBuilderSectionCommand.cpp` al ramo `master`
`2890cb3`: [V]

| comando | alias accettati |
|---|---|
| `section` | `Fiber`, `fiberSec`, `NDFiber`, `NDFiberWarping` trattati nello stesso ramo (riga 359 e seguenti) |
| `patch` | `quad` e `quadr` (riga 800), `rect` e `rectangular` (riga 898), `circ` (riga 990) |
| `layer` | `straight` (riga 1382), `circ` (riga 1497) |

Serve saperlo perché il codice pubblicato non è uniforme: il file canonico
`BuildRCrectSection.tcl` trascritto al §2.3 scrive `section fiberSec` e `patch
quadr`, la documentazione scrive `section Fiber` e `patch quad`. Sono lo stesso
comando. Un generatore che ne emette uno e legge l'altro va tarato su entrambi.
Gli alias sono stati verificati **nel solo file dei comandi Tcl**: non ho
controllato che l'interprete usato da OpenSeesPy accetti `quadr`. [NON TROVATO]

### 1.6 In tre dimensioni la torsione non è opzionale

Il sorgente è netto. `TclModelBuilderSectionCommand.cpp` costruisce il materiale
di torsione da `-GJ` (riga 591, come `ElasticMaterial`) oppure da `-torsion`
(riga 602, come materiale esistente), e poi, alla riga 623: [V]

    if (torsion == 0 && NDM == 3) {
      opserr << "WARNING - no torsion specified for 3D fiber section, use -GJ or -torsion\n";

Cioè: **una sezione a fibre in un modello `-ndm 3` senza `-GJ` né `-torsion` non
si costruisce.** La documentazione presenta i due argomenti come alternative
sintattiche; il sorgente dice che in tre dimensioni uno dei due è obbligatorio.
È un dato che il §6 conta fra quelli mancanti, perché `GJ` non è misurabile sulla
nuvola.

---

## 2. L'idioma completo (domanda b)

L'idioma è uno solo e ha vent'anni. Lo si trova identico, con gli stessi
commenti, in tre fonti indipendenti: l'esempio ufficiale OpenSeesPy, l'esempio
ufficiale Tcl del wiki, e la procedura di libreria della galleria PEER. Sotto
sono trascritti tutti e tre, perché le differenze fra loro sono la parte
interessante.

### 2.1 L'esempio ufficiale OpenSeesPy, trascritto

Da `MomentCurvature.py` della documentazione ufficiale, sezione «Moment
Curvature Analysis». Trascritto verbatim, dalla definizione dei materiali alla
fine della sezione: [V]

    # Material definitions
    uniaxialMaterial('Concrete01',1, -6.0,  -0.004,  -5.0,  -0.014)
    uniaxialMaterial('Concrete01',2, -5.0,  -0.002,  0.0,  -0.006)

    fy = 60.0
    E = 30000.0
    uniaxialMaterial('Steel01', 3, fy, E, 0.01)

    # Cross-section parameters
    colWidth = 15
    colDepth = 24
    cover = 1.5
    As = 0.60

    y1 = colDepth/2.0
    z1 = colWidth/2.0

    # Fiber section definition
    section('Fiber', 1)

    patch('rect',1,10,1 ,cover-y1, cover-z1, y1-cover, z1-cover)
    patch('rect',2,10,1 ,-y1, z1-cover, y1, z1)
    patch('rect',2,10,1 ,-y1, -z1, y1, cover-z1)
    patch('rect',2,2,1 ,-y1, cover-z1, cover-y1, z1-cover)
    patch('rect',2,2,1 ,y1-cover, cover-z1, y1, z1-cover)

    layer('straight', 3, 3, As, y1-cover, z1-cover, y1-cover, cover-z1)
    layer('straight', 3, 2, As, 0.0     , z1-cover, 0.0      , cover-z1)
    layer('straight', 3, 3, As, cover-y1, z1-cover, cover-y1, cover-z1)

Va letto così, ed è la ricetta:

- **materiale 1** = calcestruzzo di **nucleo**, confinato: `fpc` −6,0,
  deformazione al picco −0,004, resistenza residua −5,0 a −0,014. Resiste dopo
  il picco.
- **materiale 2** = calcestruzzo di **copriferro**, non confinato: `fpc` −5,0,
  picco a −0,002, e resistenza residua **0,0** a −0,006. Il copriferro si
  espelle, ed è il crollo a zero che lo dice.
- **materiale 3** = acciaio, `Steel01` con `fy` 60,0, `E0` 30000,0 e
  incrudimento `b` 0,01.
- **un patch di nucleo** che va da (`cover-y1`, `cover-z1`) a (`y1-cover`,
  `z1-cover`): il rettangolo interno al copriferro, per tutti e quattro i lati.
- **quattro patch di copriferro**: due fasce lunghe sui lati z estremi, due
  fasce corte sui lati y estremi fra le prime due. Quattro, non uno, perché il
  copriferro è una cornice e una cornice non è un rettangolo.
- **tre layer di barre**: 3 in alto a `y1-cover`, 2 intermedie a `y = 0.0`, 3 in
  basso a `cover-y1`. Le intermedie sono l'armatura di parete che le norme
  chiedono quando la sezione è alta.

La stessa fonte dichiara il proprio valore di controllo: lo spostamento del nodo
2 nel terzo grado di libertà deve valere `0.00190476190476190541` entro `1e-12`,
e se non lo fa l'esempio si dichiara `FAILED`. È un oracolo pubblicato, ed è
riusabile. [V]

### 2.2 Lo stesso in Tcl, dal wiki di Berkeley

Dalla pagina `Moment_Curvature_Example`, verbatim: [V]

    uniaxialMaterial Concrete01  1  -6.0  -0.004   -5.0     -0.014
    uniaxialMaterial Concrete01  2  -5.0   -0.002   0.0     -0.006
    uniaxialMaterial Steel01  3  $fy $E 0.01

    section Fiber 1 {
        patch rect 1 10 1 [expr $cover-$y1] [expr $cover-$z1] \
            [expr $y1-$cover] [expr $z1-$cover]

        patch rect 2 10 1  [expr -$y1] [expr $z1-$cover] $y1 $z1
        patch rect 2 10 1  [expr -$y1] [expr -$z1] $y1 [expr $cover-$z1]
        patch rect 2  2 1  [expr -$y1] [expr $cover-$z1] \
            [expr $cover-$y1] [expr $z1-$cover]
        patch rect 2  2 1  [expr $y1-$cover] [expr $cover-$z1] \
            $y1 [expr $z1-$cover]

        layer straight 3 3 $As [expr $y1-$cover] [expr $z1-$cover] \
            [expr $y1-$cover] [expr $cover-$z1]
        layer straight 3 2 $As 0.0 [expr $z1-$cover] 0.0 [expr $cover-$z1]
        layer straight 3 3 $As [expr $cover-$y1] [expr $z1-$cover] \
            [expr $cover-$y1] [expr $cover-$z1]
    }

Gli argomenti sono gli stessi, nello stesso ordine, con gli stessi numeri. La
traduzione fra i due interpreti è meccanica.

### 2.3 La procedura canonica, trascritta per intero

`BuildRCrectSection.tcl`, dalla galleria PEER
(<https://github.com/peer-open-source/opensees-gallery>, BSD-3-Clause, ultimo
push 10/03/2026), presente identica in almeno dieci repository pubblici — 26
risultati per `"BuildRCrectSection" language:tcl` sulla ricerca di codice
GitHub. [M] Intestazione e corpo, verbatim: [V]

    proc BuildRCrectSection {id HSec BSec coverH coverB coreID coverID steelID numBarsTop barAreaTop numBarsBot barAreaBot numBarsIntTot barAreaInt nfCoreY nfCoreZ nfCoverY nfCoverZ} {
    	# Build fiber rectangular RC section, 1 steel layer top, 1 bot, 1 skin, confined core
    	# Define a procedure which generates a rectangular reinforced concrete section
    	# with one layer of steel at the top & bottom, skin reinforcement and a
    	# confined core.
    	#		by: Silvia Mazzoni, 2006
    	#			adapted from Michael H. Scott, 2003

    	set coverY [expr $HSec/2.0];
    	set coverZ [expr $BSec/2.0];
    	set coreY [expr $coverY-$coverH];
    	set coreZ [expr $coverZ-$coverB];
    	set numBarsInt [expr $numBarsIntTot/2];

    	# Define the fiber section
    	section fiberSec $id -GJ 1e8 {
    		# Define the core patch
    		patch quadr $coreID $nfCoreZ $nfCoreY -$coreY $coreZ -$coreY -$coreZ $coreY -$coreZ $coreY $coreZ

    		# Define the four cover patches
    		patch quadr $coverID 2 $nfCoverY -$coverY $coverZ -$coreY $coreZ $coreY $coreZ $coverY $coverZ
    		patch quadr $coverID 2 $nfCoverY -$coreY -$coreZ -$coverY -$coverZ $coverY -$coverZ $coreY -$coreZ
    		patch quadr $coverID $nfCoverZ 2 -$coverY $coverZ -$coverY -$coverZ -$coreY -$coreZ -$coreY $coreZ
    		patch quadr $coverID $nfCoverZ 2 $coreY $coreZ $coreY -$coreZ $coverY -$coverZ $coverY $coverZ

    		# define reinforcing layers
    		layer straight $steelID $numBarsInt $barAreaInt  -$coreY $coreZ $coreY $coreZ;	# intermediate skin reinf. +z
    		layer straight $steelID $numBarsInt $barAreaInt  -$coreY -$coreZ $coreY -$coreZ;	# intermediate skin reinf. -z
    		layer straight $steelID $numBarsTop $barAreaTop $coreY $coreZ $coreY -$coreZ;	# top layer reinfocement
    		layer straight $steelID $numBarsBot $barAreaBot  -$coreY $coreZ  -$coreY -$coreZ;	# bottom layer reinforcement

    	};	# end of fibersection definition
    };		# end of procedure

E la nota che il file mette sotto lo schema, verbatim, perché è una convenzione
e non un dettaglio:

> «The core concrete ends at the NA of the reinforcement
> The center of the section is at (0,0) in the local axis system»

Cioè il nucleo **finisce sull'asse delle barre**, non sul filo interno delle
staffe: `coverH` è dichiarato «distance from section boundary to neutral axis of
reinforcement». È una scelta di modellazione, e va dichiarata quando si scrive
un copriferro.

### 2.4 Che cosa dell'idioma è invariante

Confrontando le tre fonti:

1. **Due materiali di calcestruzzo, non uno.** Nucleo e copriferro hanno leggi
   diverse, e la differenza sta tutta nella resistenza residua: il copriferro
   crolla a zero, il nucleo no.
2. **Un patch per il nucleo, quattro per il copriferro.** Sempre quattro: la
   cornice non è decomponibile in meno.
3. **Un `layer straight` per fila di barre**, con `numFiber` pari al numero di
   barre e `areaFiber` pari all'area della singola barra.
4. **L'origine è il baricentro geometrico** della sezione, (0, 0).
5. **La suddivisione è fitta in una direzione e rada nell'altra**: `10 1` nel
   patch di nucleo dell'esempio ufficiale, `$nfCoreZ $nfCoreY` nella procedura.
   Le fibre servono a integrare la flessione, e la flessione varia lungo `y`.
6. **La torsione si dichiara sulla sezione** (`-GJ 1e8` nella procedura), e in
   tre dimensioni è obbligatoria (§1.6).

Punto 5, dichiarato: **il numero di fibre è una scelta di discretizzazione, e
nelle tre fonti non porta alcuna giustificazione.** Non ho trovato nella
documentazione ufficiale uno studio di convergenza sul numero di fibre.
[NON TROVATO] È esattamente la classe di omissione che il
[`README.md`](README.md) §2 registra per il maglio, e vale qui identica.

---

## 3. I materiali (domanda c)

### 3.1 Calcestruzzo

**`Concrete01`** — Kent-Scott-Park con scarico degradante secondo Karsan-Jirsa,
**resistenza a trazione nulla**. Firma e argomenti verbatim: [V]

    uniaxialMaterial('Concrete01', matTag, fpc, epsc0, fpcu, epsU)

| argomento | descrizione della fonte |
|---|---|
| `fpc` | «concrete compressive strength at 28 days (compression is negative)» |
| `epsc0` | «concrete strain at maximum strength» |
| `fpcu` | «concrete crushing strength» |
| `epsU` | «concrete strain at crushing strength» |

Due note della fonte, verbatim: «Compressive concrete parameters should be input
as negative values (if input as positive, they will be converted to negative
internally)» e «The initial slope for this model is (2*fpc/epsc0)». La seconda
decide: **il modulo elastico non è un parametro indipendente**, è il rapporto fra
i primi due. Chi vuole un dato `E` deve scegliere `epsc0` di conseguenza.

**`Concrete02`** — `Concrete01` più la trazione, con ramo di softening lineare.
[V]

    uniaxialMaterial('Concrete02', matTag, fpc, epsc0, fpcu, epsU, lambda, ft, Ets)

I quattro primi argomenti sono quelli di `Concrete01`; in più: `lambda` «ratio
between unloading slope at epscu and initial slope», `ft` «tensile strength»,
`Ets` «tension softening stiffness (absolute value) (slope of the linear tension
softening branch)».

**`Concrete04`** — Popovics in compressione, Karsan-Jirsa allo scarico,
esponenziale in trazione. [V]

    uniaxialMaterial('Concrete04', matTag, fc, epsc, epscu, Ec, fct, et, beta)

Qui `Ec` **è** un argomento: «floating point values defining initial stiffness».
`fct` ed `et` sono dichiarati opzionali. La nota che conta, verbatim:

> «If Ec = 57000*sqrt(|fcc|) (in psi), the envelope curve matches the model by
> Mander et al. (1988).»

È l'aggancio esplicito al modello di confinamento di Mander, Priestley e Park,
*Theoretical Stress-Strain Model for Confined Concrete*, J. Struct. Eng. 114(8):
1804-1826, 1988, DOI 10.1061/(ASCE)0733-9445(1988)114:8(1804).

### 3.2 Acciaio

**`Steel01`** — bilineare con incrudimento cinematico. [V]

    uniaxialMaterial('Steel01', matTag, Fy, E0, b, a1, a2, a3, a4)

`Fy` «yield strength», `E0` «initial elastic tangent», `b` «strain-hardening
ratio (ratio between post-yield tangent and initial elastic tangent)». Da `a1` a
`a4` sono i parametri di incrudimento isotropo, opzionali.

**`Steel02`** — Giuffré-Menegotto-Pinto con incrudimento isotropo. [V]

    uniaxialMaterial('Steel02', matTag, Fy, E0, b, *params, a1=a2*Fy/E0, a2=1.0, a3=a4*Fy/E0, a4=1.0, sigInit=0.0)

I primi tre argomenti sono quelli di `Steel01`. `params` è, verbatim,
«parameters to control the transition from elastic to plastic branches.
params=[R0,cR1,cR2]. Recommended values: R0=between 10 and 20, cR1=0.925,
cR2=0.15». **I valori raccomandati sono nella documentazione**: è ciò che rende
`Steel02` usabile senza taratura.

**`ReinforcingSteel`** — il modello specifico per barre d'armatura, e il più
esigente. [V]

    uniaxialMaterial('ReinforcingSteel', matTag, fy, fu, Es, Esh, eps_sh, eps_ult,
                     '-GABuck', lsr, beta, r, gamma,
                     '-DMBuck', lsr, alpha=1.0,
                     '-CMFatigue', Cf, alpha, Cd,
                     '-IsoHard', a1=4.3, limit=1.0,
                     '-MPCurveParams', R1=0.333, R2=18.0, R3=4.0)

Argomenti obbligatori: `fy` «yield stress in tension», `fu` «ultimate stress in
tension», `Es` «initial elastic tangent», `Esh` «tangent at initial strain
hardening», `eps_sh` «strain corresponding to initial strain hardening»,
`eps_ult` «strain at peak stress». Gli opzionali coprono l'instabilità della
barra (Gomes-Appleton con `-GABuck`, Dhakal-Maekawa con `-DMBuck`) e la fatica
oligociclica (Coffin-Manson con `-CMFatigue`).

### 3.3 Quali una tesi può dichiarare, e quali no

La separazione richiesta dal committente, fatta sui parametri e non
sull'impressione:

| materiale | parametri | dichiarabili da normativa o da manuale? |
|---|---|---|
| `Concrete01` | `fpc`, `epsc0`, `fpcu`, `epsU` | **sì.** `fpc` è la resistenza di classe; `epsc0` e `epsU` sono le deformazioni caratteristiche che le norme tabulano. Quattro numeri, tutti con una fonte scrivibile |
| `Concrete02` | i quattro sopra più `lambda`, `ft`, `Ets` | **in parte.** `ft` si deduce dalla classe; `lambda` ed `Ets` no — sono parametri di scarico e di softening, e le norme non li danno. [INF] |
| `Concrete04` | `fc`, `epsc`, `epscu`, `Ec`, `fct`, `et`, `beta` | **sì per i primi quattro**, e con un vantaggio: `Ec` è indipendente, quindi il modulo elastico si dichiara invece di derivarlo. `beta` no |
| `Steel01` | `Fy`, `E0`, `b` | **sì.** Tre numeri, tutti di normativa. È il minimo dichiarabile |
| `Steel02` | `Fy`, `E0`, `b`, `R0`, `cR1`, `cR2` | **sì**, e i tre parametri di transizione hanno valori raccomandati **nella documentazione ufficiale** — non è una taratura, è una citazione |
| `ReinforcingSteel` | `fy`, `fu`, `Es`, `Esh`, `eps_sh`, `eps_ult` | **no.** `Esh`, `eps_sh` ed `eps_ult` vengono da una prova di trazione su barra. Senza quella prova sono numeri inventati con una faccia seria |

Ne discende, e resta una **raccomandazione**, non una decisione: per una tesi
senza campagna sperimentale la coppia difendibile è **`Concrete01` (o
`Concrete04`) più `Steel02`**, perché ogni parametro ha una fonte citabile.
`ReinforcingSteel` va lasciato dov'è finché non c'è un provino.

### 3.4 Il confinamento non è un comando: è un calcolo a monte

Nessun comando di OpenSees prende in ingresso le staffe. La differenza fra il
materiale di nucleo e quello di copriferro nell'idioma del §2 è **tutta nei
numeri** dei due `uniaxialMaterial`, e quei numeri li produce un modello di
confinamento — Mander, Priestley e Park 1988 — che va applicato **prima** di
scrivere il comando, a partire da diametro, passo e disposizione delle staffe.

Conseguenza per questo progetto, e va detta subito: **il passo delle staffe non
è misurabile su una nuvola di punti esterna.** Il confinamento è un dato che
entra da fuori, sempre.

---

## 4. Gli elementi che accettano una sezione a fibre (domanda d)

### 4.1 Il catalogo, con le firme

**`forceBeamColumn`** — formulazione a forze, iterativa. Firme, verbatim dalle
due documentazioni ufficiali: [V]

    element('forceBeamColumn', eleTag, *eleNodes, transfTag, integrationTag, '-iter', maxIter=10, tol=1e-12, '-mass', mass=0.0)
    element forceBeamColumn $eleTag $iNode $jNode $transfTag $integrationTag <-iter $maxIter $tol> <-mass $mass>

La teoria, verbatim dalla documentazione nuova: usa «known equilibrium along the
element length to determine section forces», e questo «necessitates iterative
computations at each trial step to resolve section deformations at integration
points given nodal displacements». `maxIter` e `tol` sono di quel ciclo interno.

**`dispBeamColumn`** — formulazione a spostamenti. [V]

    element('dispBeamColumn', eleTag, *eleNodes, transfTag, integrationTag, '-cMass', '-mass', mass=0.0)

Stessi argomenti meno il ciclo iterativo, più `-cMass` «to form consistent mass
matrix (optional, default = lumped mass matrix)».

**`nonlinearBeamColumn`** — è il nome **precedente** dell'elemento a forze, con
la sezione passata direttamente invece che attraverso un oggetto di
integrazione. La pagina del wiki di Berkeley che ne portava la sintassi
risponde **404** oggi: `https://opensees.berkeley.edu/wiki/index.php/Nonlinear_Beam_Column_Element`
non esiste più. [M] Che il comando resti accettato per compatibilità e che
l'astrazione `BeamIntegration` abbia reso obsoleta l'opzione `-sections` l'ho
letto solo in fonti secondarie: **non l'ho verificato sul sorgente né sulla
documentazione ufficiale**. [NON TROVATO] Per un programma che genera codice
nuovo la questione è comunque chiusa a monte: si scrive `forceBeamColumn`.

**`elasticBeamColumn`** — accetta un `secTag`, e questo va capito bene prima di
usarlo. Firme documentate: [V]

    element('elasticBeamColumn', eleTag, *eleNodes, Area, E_mod, G_mod, Jxx, Iy, Iz, transfTag, <'-mass', mass>, <'-cMass'>)
    element('elasticBeamColumn', eleTag, *eleNodes, secTag, transfTag, <'-mass', mass>, <'-cMass'>, <'-releasez', releaseCode>, <'-releasey', releaseCode>)

`secTag` è «identifier for previously-defined section object». Che cosa succeda
se quella sezione è una sezione a fibre lo dice il sorgente, non la
documentazione: `ElasticBeam3d.cpp`, costruttore che prende una
`SectionForceDeformation`, verbatim: [V]

    const Matrix &sectTangent = section.getInitialTangent();
    const ID &sectCode = section.getType();
    for (int i=0; i<sectCode.Size(); i++) {
      int code = sectCode(i);
      switch(code) {
      case SECTION_RESPONSE_P:
        A = sectTangent(i,i)/E;
        break;
      case SECTION_RESPONSE_MZ:
        Iz = sectTangent(i,i)/E;
        break;

e più sotto, quando la sezione non porta torsione:

    if (Jx == 0.0) {
      opserr << "ElasticBeam3d::ElasticBeam3d -- no torsion in section -- continuing with GJ = 0\n";

> Passare una sezione a fibre a un `elasticBeamColumn` **non fa un elemento a
> fibre**: l'elemento legge la **tangente iniziale** della sezione una volta
> sola, ne estrae A, Iy, Iz, Jx e poi dimentica le fibre. Nessuna non linearità,
> nessuna tensione di fibra da registrare. È un modo per ottenere le proprietà
> elastiche equivalenti di una sezione composita, non un modello armato.

**`zeroLengthSection`** — non è un elemento di telaio ma va nominato, perché è
quello che l'esempio ufficiale usa per il momento-curvatura di una sezione:
`element('zeroLengthSection', 1, 1, 2, secTag)` nel codice trascritto al §2.1. È
la via per **provare una sezione da sola**, senza costruire il telaio. [V]

### 4.2 Plasticità diffusa contro plasticità concentrata

La sezione non va sull'elemento: va su un oggetto `beamIntegration`, e il tipo
di integrazione è ciò che decide dove il materiale può snervare. Firma generale:
`beamIntegration(type, tag, *args)`; per `Lobatto` la documentazione dichiara due
forme, una prismatica con un `secTag` e il numero di punti `N`, una non
prismatica con `N` tag di sezione. [V]

Le due famiglie, con l'elenco della documentazione ufficiale: [V]

| famiglia | tipi | che cosa fa |
|---|---|---|
| **plasticità diffusa** | `Lobatto`, `Legendre`, `NewtonCotes`, `Radau`, `Trapezoidal`, `CompositeSimpson`, `UserDefined`, `FixedLocation`, `LowOrder`, `MidDistance` | «permit yielding at any integration point along the element length» |
| **cerniera plastica** | `UserHinge`, `HingeMidpoint`, `HingeRadau`, `HingeRadauTwo`, `HingeEndpoint`, `ConcentratedPlasticity`, `ConcentratedCurvature` | «confine material yielding to regions of the element of specified length while the remainder of the element is linear elastic» |

Le due frasi sono verbatim. La differenza pratica: con la plasticità diffusa
serve **una sezione a fibre per punto di integrazione** e il costo cresce con
`N`; con la cerniera plastica servono le fibre solo alle estremità, ma bisogna
dichiarare la **lunghezza della cerniera**, che è un dato empirico in più.

L'esempio ufficiale `RCFrameGravity` sceglie la prima, con cinque punti:
`beamIntegration('Lobatto', 1, 1, 5)` e poi `element('forceBeamColumn', 1, 1, 3,
1, 1)`. Nello stesso esempio la trave è invece un `elasticBeamColumn` con A, E e
I numerici — colonne a fibre, trave elastica. [V]

Sulla scelta fra elemento a forze ed elemento a spostamenti a parità di
accuratezza — quanti elementi per membratura, quanti punti — il wiki di Berkeley
ha una pagina dedicata, `Discovering OpenSees -- Force-based Element vs.
Displacement-based Element`, ma **il contenuto sta in un PDF e in un video
linkati, non nel testo della pagina**: non l'ho letto, e non riporto numeri.
[NON TROVATO]

### 4.3 Il minimo per una statica lineare sotto peso proprio

Elencato dai comandi la cui firma ho letto, nell'ordine in cui vanno chiamati.
Non è una ricetta trovata pubblicata: è la composizione delle firme, e come tale
va trattata. [INF, salvo le firme dei singoli comandi, che sono [V]]

1. `model('basic', '-ndm', 3, '-ndf', 6)` — sei gradi di libertà per nodo.
2. `node(...)` per ogni estremo di membratura, e `fix(...)` sui nodi vincolati.
3. `uniaxialMaterial(...)` — almeno il calcestruzzo; con l'armatura, anche
   l'acciaio.
4. `section('Fiber', secTag, '-GJ', GJ)` più `patch` e `layer`. **`-GJ` è
   obbligatorio in tre dimensioni** (§1.6).
5. `geomTransf('Linear', transfTag, *vecxz)`. La documentazione descrive `vecxz`
   verbatim come «X, Y, and Z components of vecxz, the vector used to define the
   local x-z plane of the local-coordinate system», ed è **richiesto in tre
   dimensioni**. [V]
6. `beamIntegration('Lobatto', tag, secTag, N)`.
7. `element('forceBeamColumn', eleTag, *eleNodes, transfTag, integrationTag)`.
8. `timeSeries('Constant', ...)` o `'Linear'`, poi `pattern('Plain', ...)`.
9. Il peso proprio. **Non c'è una scheda di gravità**, come già registrato in
   [`ricerca-opensees-e-armature.md`](ricerca-opensees-e-armature.md) §6: su un
   elemento di telaio si passa come carico distribuito con `eleLoad`, la cui
   firma è, verbatim: [V]

        eleLoad('-ele', *eleTags, '-range', eleTag1, eleTag2, '-type', '-beamUniform', Wy, <Wz>, Wx=0.0, '-beamPoint', Py, <Pz>, xL, Px=0.0, '-beamThermal', *tempPts)

   con `Wy` documentato come «mag of uniformily distributed ref load acting in
   local y direction of element». Il carico è **in coordinate locali
   dell'elemento**: per una gravità verticale globale, il generatore deve
   proiettare ρ·g·A sulla terna locale di ciascuna membratura, e la terna locale
   è quella che `geomTransf` ha fissato al punto 5.
10. `constraints`, `numberer`, `system`, `algorithm('Linear')`,
    `integrator('LoadControl', 1.0)`, `analysis('Static')`, `analyze(1)`.

**Il punto 9 è dove questo differisce da CalculiX in modo che conta.** In un
deck `.inp` la gravità è `*DLOAD, GRAV` e il solutore fa il resto, compreso
l'equilibrio che `solve.controlla_reazioni` verifica. Qui il peso proprio è un
numero che il generatore calcola e proietta, quindi **entra nel modello un
errore che il generatore può commettere da solo** — e serve un controllo di
equilibrio scritto qui, non uno ereditato.

---

## 5. Generatori pronti (domanda e)

Cercati quelli nominati dal committente, più quelli elencati dalla lista
`awesome-opensees`. Per ciascuno: cosa produce, licenza, stato al 28/08/2026.

### 5.1 `opsvis` — l'unico che genera i comandi da una struttura dati

`opsvis` 1.3.7, PyPI del 30/03/2026, licenza **GPL-3.0**, repository
`sewkokot/opsvis` con ultimo push il 30/03/2026 e 57 stelle. [M]

Non è solo un disegnatore. Il file `fibsec.py` definisce due funzioni:
`plot_fiber_section` alla riga 12 e `fib_sec_list_to_cmds` alla riga 189. La
seconda **emette i comandi OpenSees** a partire da una lista Python. Docstring
verbatim: [V]

> «Reuses fib_sec_list to define fiber section in OpenSees.
>
> At present it is not possible to extract fiber section data from the OpenSees
> domain, this function is a workaround. The idea is to prepare data similar to
> the one the regular OpenSees commands (``section('Fiber', ...)``, ``fiber()``,
> ``patch()`` and/or ``layer()``) require.»

e l'avvertimento che la accompagna, verbatim:

> «If you use this function, do not issue the regular OpenSees: section, Fiber,
> Patch or Layer commands.»

Il corpo è una traduzione uno a uno:

    for dat in fib_sec_list:
        if dat[0] == 'section':
            secTag, GJ = dat[2], dat[4]
            ops.section('Fiber', secTag, '-GJ', GJ)

        if dat[0] == 'layer':
            matTag = dat[2]
            n_bars = dat[3]
            As = dat[4]
            if dat[1] == 'straight':
                Iy, Iz, Jy, Jz = dat[5], dat[6], dat[7], dat[8]
                ops.layer('straight', matTag, n_bars, As, Iy, Iz, Jy, Jz)

E la struttura dati che consuma, dall'esempio nella docstring:

    fib_sec_1 = [['section', 'Fiber', 1, '-GJ', 1.0e6],
                 ['patch', 'quad', 1, 4, 1,  0.032, 0.317, -0.311, 0.067, -0.266, 0.005, 0.077, 0.254],
                 ...
                 ]

Lettura secca, ed è il fatto che conta per questo progetto: **`opsvis` non è un
generatore di sezioni, è un serializzatore.** La lista che consuma ha esattamente
la forma dei comandi: chi la costruisce ha già deciso tutto — patch, vertici,
barre, aree. Non toglie una sola decisione. Quello che dà in cambio è che la
**stessa** lista disegna la sezione e la costruisce, quindi il disegno non può
divergere dal modello. Non è poco: è il controllo visivo gratuito.

La citazione dice anche perché la funzione esiste: «At present it is not
possible to extract fiber section data from the OpenSees domain». Il dominio di
OpenSees **non si interroga** su come è fatta una sezione a fibre. Chi genera
deve conservare da sé la descrizione.

### 5.2 Gli esempi ufficiali di OpenSeesPy

Sono codice, non strumenti: `MomentCurvature.py` e `RCFrameGravity.py`
(trascritti in parte ai §2.1 e §4.2) sono da copiare e adattare. Licenza:
quella del progetto OpenSees. Stato: nella documentazione corrente. Non
generano nulla, ma il primo porta un **oracolo numerico pubblicato** (§2.1) ed è
questo che li rende preziosi per una tesi: sono un termine di paragone per
verificare un generatore scritto qui.

### 5.3 `sectionproperties` e `concreteproperties`

`sectionproperties` 3.10.2 (PyPI 24/01/2026, **MIT**, 552 stelle) e
`concreteproperties` 0.8.0 (PyPI 06/07/2026, **MIT**, 241 stelle), entrambi di
Robbie van Leeuwen, entrambi mantenuti. `concreteproperties` si descrive
«Calculate section properties for reinforced concrete sections». [M]

**Non generano comandi OpenSees.** Ricerca di codice sull'API GitHub per la
stringa `opensees` limitata a ciascun repository: **zero risultati in entrambi**.
[M] Fanno la cosa adiacente — costruiscono una geometria di sezione armata,
posano le barre, e ne calcolano proprietà, momento-curvatura e domini di
interazione con un proprio solutore. Utili come **oracolo indipendente** per un
momento-curvatura calcolato in OpenSees; inutili come generatori di `patch` e
`layer`.

### 5.4 STKO (ASDEA)

Pre e post processore per OpenSees, di ASDEA Software — la stessa casa di
`ASDEmbeddedNodeElement` registrato in
[`ricerca-opensees-e-armature.md`](ricerca-opensees-e-armature.md) §2.2. È
**commerciale**, con una licenza accademica gratuita introdotta con la versione
2.0; le licenze di prova diventano una «Free Learning License» dopo trenta
giorni, che il fornitore dichiara non utilizzabile «for developing or publishing
research or for profit-generating applications».

**Caveat sulla fonte.** Il sito ufficiale `asdeasoft.net` risponde **403** alla
lettura automatica: quanto sopra viene da un motore di ricerca che cita le
pagine di ASDEA, **non da una lettura diretta della pagina**. Le condizioni di
licenza vanno riverificate a mano prima di citarle in tesi. [NON TROVATO in
lettura diretta]

Va comunque escluso per un'altra ragione, che non dipende dalla licenza: è una
GUI. Questo programma deve **generare** un modello da una nuvola, non farlo
disegnare a un operatore.

### 5.5 OpenSeesNavigator e gli altri

Dalla lista `awesome-opensees` (<https://github.com/Hanlin-Dong/awesome-opensees>),
che raccoglie sette strumenti di pre-processing: [V]

| strumento | che cos'è, secondo la lista |
|---|---|
| GiD+OpenSees | «An OpenSees add-on for GiD, A general graphical pre/post processor» |
| Build-X | «An Expert Tool for Seismic Analysis and Assessment of 3D Buildings with OpenSees» |
| NextFEM | preprocessore per OpenSees e altri codici |
| OpenSees Navigator | «A stand-alone Matlab interface allowing users to quickly create models, perform analysis, and look at results» |
| ETO (Etabs To OpenSees) | pre e post processore che importa un `.s2k` di ETABS |
| STKO | «A cutting-edge pre- and post-processor for both serial and parallel versions of OpenSees» |
| eSEES | «A scripting and graphical user interface for OpenSees» |

Sono **tutte GUI o traduttori da un altro programma commerciale**. Nessuna prende
in ingresso una descrizione di sezione e restituisce testo. Per OpenSees
Navigator, in particolare, non ho trovato una versione né una data di rilascio
verificabili: la pagina di download richiede registrazione. [NON TROVATO]

### 5.6 La risposta secca alla domanda (e)

> **Non esiste uno strumento rodato che generi `patch` e `layer` da una
> descrizione di sezione.** Esiste un serializzatore (`opsvis`) che traduce una
> lista già completa, esistono librerie che modellano sezioni armate senza
> parlare OpenSees (`concreteproperties`), ed esistono GUI. La decomposizione
> «rettangolo armato → un patch di nucleo, quattro di copriferro, N layer di
> barre» è, in tutte le fonti lette, **scritta a mano ogni volta** — o incapsulata
> in una `proc` Tcl di vent'anni fa che ciascuno si ricopia (§2.3).

Il che, va detto, rende il compito piccolo: quella decomposizione è dieci righe,
ed è la stessa in tre fonti indipendenti.

---

## 6. Il ponte con questo progetto (domanda f)

`wall.prior` restituisce, per ciascuna membratura accettata, un dizionario di
soli tipi JSON con queste chiavi — lette sul codice, non supposte: `punti`,
`indici`, `asse`, `origine`, `lunghezza`, `sezione`, `sezione_dispersione`,
`contorno`, `fuori_piombo_deg`, `asse_ideale`, `scarto_asse_deg`,
`rigonfiamento`, `volume`, `riempimento`, `esiti`. Fuori dall'elenco delle
membrature il dizionario porta anche `terna`, la terna di direzioni del pezzo
intero. [V]

Che cosa manca per scrivere un `forceBeamColumn` con sezione a fibre. Uno per
uno, in tre gruppi per **provenienza**, perché è la provenienza a decidere se un
dato si calcola, si assume o si va a cercare.

### 6.1 Ciò che manca ma è ricavabile da quello che c'è

1. **La base del piano di sezione, `e1` ed `e2`.** `wall.Membratura.sezione` è
   una coppia di estensioni lungo due direzioni che `wall.misura` costruisce
   così: `riferimento = direzioni[2]` se non è quasi parallela all'asse,
   altrimenti `direzioni[0]`; poi `e1` è la sua parte ortogonale all'asse,
   normalizzata, e `e2 = asse × e1`. **Quelle due direzioni non escono da
   `wall.prior`**: escono `asse` e `terna`, che bastano a ricalcolarle con la
   stessa formula, ma la formula vive dentro `wall.misura` e non è esposta.
   Senza `e1` ed `e2` la coppia `sezione` e il `contorno` non sono
   posizionabili nello spazio, e `patch` e `layer` prendono coordinate nel piano
   locale (y, z). **Ricavabile; oggi non ricavato.**
2. **Il `vecxz` di `geomTransf`.** L'orientamento della sezione attorno al
   proprio asse è un dato del modello, non della mesh, e in tre dimensioni
   `geomTransf` lo pretende (§4.3, punto 5). È `e1` o `e2` del punto 1, scelto
   in modo coerente con quale delle due estensioni di `sezione` si mappa su y.
   **Ricavabile una volta risolto il punto 1.**
3. **L'area della sezione**, che serve al carico distribuito `eleLoad` del
   peso proprio. Il prodotto delle due estensioni è l'area del **rettangolo
   circoscritto**, non della sezione: `wall.Membratura.riempimento_sezione`
   misura proprio quanto le due cose differiscono, ed è pubblicato come esito.
   L'area vera è quella del poligono `contorno`. **Ricavabile dal `contorno`.**
4. **I due nodi dell'elemento.** `origine` è il punto sull'asse da cui la
   lunghezza è misurata, quindi il nodo I è `origine` e il nodo J è
   `origine + asse · lunghezza`. **Ricavabile, ed è l'unico di tutta la lista
   che è già una sottrazione.**

### 6.2 Ciò che manca e non è nella nuvola — va deciso o cercato altrove

5. **Il numero di barre.** Non è nella nuvola. Una scansione laser vede la
   superficie del calcestruzzo; le barre stanno sotto.
6. **Il diametro, quindi `areaFiber`.** Idem.
7. **La posizione delle barre nella sezione**, cioè le coordinate (y, z) degli
   estremi di ogni `layer straight`. Idem.
8. **Il copriferro.** Idem — e con l'ambiguità del §2.3 da risolvere per
   dichiarazione: copriferro fino all'**asse** delle barre, come vuole
   `BuildRCrectSection`, o fino al filo delle staffe.
9. **Le staffe: diametro, passo, disposizione.** Non entrano in alcun comando
   (§3.4), ma senza di esse non si calcolano i parametri del calcestruzzo
   confinato, e senza quelli il nucleo e il copriferro sono lo stesso materiale
   — cioè l'idioma del §2 si riduce a un solo patch e perde il suo senso.
10. **La classe del calcestruzzo**, quindi `fpc`, `epsc0`, `fpcu`, `epsU`. Il
    [`README.md`](README.md) §5 registra che la tavola `MURO 1` **non dichiara
    la classe**: è già un limite noto del progetto, e qui pesa di più che
    nell'elastico, perché l'analisi a fibre chiede quattro numeri invece di uno.
11. **L'acciaio: `Fy`, `E0`, `b`.** Da normativa, e vanno dichiarati.
12. **`GJ` della sezione**, obbligatorio in tre dimensioni (§1.6). Non è
    misurato da nulla nel programma: serve G e la rigidezza torsionale della
    sezione, che per un rettangolo ha forma chiusa ma per il poligono
    `contorno` no. La procedura canonica del §2.3 mette `-GJ 1e8` senza
    spiegarlo, ed è una scelta da non copiare senza dichiararla.

### 6.3 Ciò che manca perché `wall.prior` lavora su una membratura per volta

13. **La connettività del telaio.** `wall.prior` rende sei membrature
    indipendenti, ciascuna con il proprio asse e la propria origine. Un telaio
    ha **nodi condivisi**: la testa della colonna e l'estremo della trave devono
    essere lo stesso nodo, o l'analisi calcola sei pezzi che si toccano senza
    parlarsi. Fra le uscite di `wall.prior` non c'è nulla che dica quali
    membrature si incontrano. Che il problema sia reale lo dice il programma
    stesso da un'altra parte: la docstring di `hexa.costruisci` registra che «Le
    mesh di membrature adiacenti non combaciano nodo a nodo». [V]
14. **La lunghezza di calcolo contro la lunghezza misurata.** Gli assi di due
    membrature che si incontrano si intersecano dentro il nodo, e la lunghezza
    dell'elemento di telaio va dal punto d'intersezione, non dalla faccia
    esterna misurata. `lunghezza` è la seconda. La differenza è metà altezza
    della sezione dell'altra membratura per estremo, e sul caso studio — sei
    membrature prismatiche di un telaio in cemento armato — non è trascurabile.
15. **I vincoli.** Quali nodi sono incastrati non è un'uscita di `wall.prior`.
    Le due zapatas del caso studio sono membrature come le altre; che poggino a
    terra è una lettura, non una misura.

### 6.4 Ciò che è una scelta di modellazione, non un dato mancante

16. **Il numero di fibre** per patch (`numSubdivY`, `numSubdivZ`), il tipo e il
    numero di punti di `beamIntegration`, il numero di elementi per membratura.
    Nessuno di questi è nella nuvola e nessuno va cercato altrove: si decidono,
    e — come registrato al §2.4 — la documentazione ufficiale **non pubblica una
    convergenza** che li giustifichi.

### 6.5 L'assunzione che l'intera operazione porta con sé

Va scritta, perché nessuno dei quindici punti sopra la contiene e senza di essa
non valgono nulla.

Una sezione a fibre è **costante lungo l'elemento**: è la definizione del
`beamIntegration` prismatico del §4.2. `wall.prior` misura invece, di ogni
membratura, quanto la sezione **non** è costante — `sezione_dispersione` è la
dispersione delle due estensioni lungo l'asse, e c'è un controllo intrinseco,
`costanza_sezione`, che scarta le regioni che la superano. E misura
`rigonfiamento`, «scostamento locale dalla faccia ideale, una mappa per cella e
non un numero». [V]

Cioè: il programma misura con cura due grandezze che descrivono lo scostamento
dal prisma perfetto, e il modello a fibre le **butta entrambe**. Non è un difetto
del modello a fibre — è il suo prezzo, ed è lo stesso prezzo che
`hexa.costruisci` già paga generando prismi. Ma va dichiarato: **su questa
strada il contributo geometrico della tesi si riduce a due numeri per membratura
più un poligono di contorno**, e tutto il resto della misura non entra nel
modello.

---

## 7. Che cosa questo decide

### Fatti che chiudono qualcosa

1. **L'idioma della sezione armata è stabile e trascrivibile.** Tre fonti
   indipendenti, vent'anni di distanza fra la prima e l'ultima, stessa
   decomposizione: un patch di nucleo, quattro di copriferro, un `layer
   straight` per fila di barre. Non c'è una scelta di progetto da fare qui, c'è
   da copiare.
2. **Non esiste un generatore da riusare.** §5.6. Il che significa che le dieci
   righe vanno scritte qui, e che nessuno le ha già verificate al posto nostro.
3. **`elasticBeamColumn` con una sezione a fibre non è un elemento a fibre.**
   Letto sul sorgente, §4.1. È la scorciatoia che sembra funzionare e non fa
   quello che promette.
4. **In tre dimensioni `-GJ` o `-torsion` è obbligatorio.** Letto sul sorgente,
   §1.6. Un dato in più da inventare, e la fonte canonica lo inventa senza dirlo.
5. **Le staffe non sono un comando.** §3.4. Il confinamento è un calcolo a monte,
   e i suoi ingressi non sono sulla superficie di un pezzo.

### La forma della lacuna

Dei sedici punti del §6, **quattro** si ricavano da ciò che il programma già
misura, **otto** vengono da fuori la nuvola per ragioni fisiche, **tre** sono
conseguenze del fatto che `wall.prior` guarda una membratura per volta, e **uno**
è una scelta di discretizzazione.

Il gruppo che decide è il terzo, e non è quello che ci si aspetta. I dati di
armatura (gruppo 6.2) mancano per una ragione onesta e dichiarabile: un laser non
vede sotto il calcestruzzo, e in tesi si scrive che vengono dal progetto o da
un'ipotesi. La **connettività** (gruppo 6.3) è invece un dato che dovrebbe venire
dalla nuvola, che la nuvola contiene, e che il programma oggi non estrae: sei
membrature che si toccano e non lo sanno. Senza quella, non c'è telaio da
analizzare — con o senza armatura.

Nessuna di queste è una decisione: sono i fatti trovati, con la loro fonte.
