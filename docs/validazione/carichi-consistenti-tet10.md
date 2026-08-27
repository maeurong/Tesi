# Carichi nodali consistenti: pressione uniforme su faccia tet10 (C3D10)

Ricerca su fonti primarie. Redatta il 2026-08-26.

**Verdetto in una riga.** L'affermazione è **esatta**: per pressione uniforme `p` su una
faccia triangolare a 6 nodi *a lati diritti con nodi di lato a metà spigolo*, il vettore
dei carichi nodali consistenti è `0` ai tre vertici e `pA/3` a ciascuno dei tre nodi di
lato (`A` = area della faccia). Verificato per derivazione esatta e confermato alla
lettera dalla documentazione ufficiale Abaqus.

---

## 0. Stato di ogni affermazione

| # | Affermazione | Stato |
|---|---|---|
| 1 | `[0,0,0,A/3,A/3,A/3]*p` per T6 a lati diritti, nodi a metà spigolo | **verificato** (derivazione esatta + quadratura, sez. 1-2) |
| 2 | Abaqus dichiara «zero equivalent loads at the corner nodes» | **verificato** (citazione verbatim, sez. 4) |
| 3 | Abaqus dichiara segno invertito ai vertici per facce *senza* nodo di centro faccia (Q8) | **verificato** (citazione verbatim, sez. 4) |
| 4 | C3D10M distribuisce diversamente, per costruzione uniforme sui 6 nodi | **verificato** su brevetto originale (sez. 5) |
| 5 | Coefficiente `A_tri = -1/16` del brevetto | **verificato come testo**, ma **incoerente**: vedi sez. 5.1.1 |
| 6 | Pagina/capitolo esatti in Cook / Zienkiewicz / Bathe / Hughes | **NON verificato** - vedi sez. 3 |
| 7 | Letteratura che quantifica l'errore del lumping ingenuo su T6 | **non trovata**; la quantificazione in sez. 6 è mia, esatta ma non pubblicata |

---

## 1. Derivazione (esatta)

### Funzioni di forma

Coordinate d'area `L1 + L2 + L3 = 1`. Numerazione: 1-2-3 vertici, 4-5-6 nodi di lato
(4 su 1-2, 5 su 2-3, 6 su 3-1). Le funzioni di forma del triangolo quadratico sono

```
N_i = L_i (2 L_i - 1)      i = 1,2,3   (vertici)
N_4 = 4 L_1 L_2 ,  N_5 = 4 L_2 L_3 ,  N_6 = 4 L_3 L_1   (nodi di lato)
```

Sono le stesse funzioni elencate come «Second-order triangle (6 nodes)» in
Abaqus Theory Guide sez. 3.2.6 (fonte in sez. 4).

### Carico consistente

Il carico consistente discende dal principio dei lavori virtuali:

```
f_i = int_A  N_i  p  dA        (p costante, faccia piana -> direzione costante)
```

### Formula d'integrazione in coordinate d'area

```
int_A  L1^a L2^b L3^c  dA  =  a! b! c! / (a+b+c+2)!  *  2A
```

Fonte primaria della formula: **Eisenberg, M. A.; Malvern, L. E., "On finite element
integration in natural co-ordinates", International Journal for Numerical Methods in
Engineering, vol. 7, n. 4 (1973), pp. 574-575, DOI 10.1002/nme.1620070421**. Metadati
verificati su Wiley Online Library e NASA ADS; testo dell'articolo dietro paywall, non
letto - la formula però è verificata numericamente qui sotto.

### Conti

Vertice:

```
int L1^2 dA = 2!*0!*0!/4! * 2A = (2/24)*2A = A/6
int L1   dA = 1!*0!*0!/3! * 2A = (1/6)*2A  = A/3
int N_1  dA = 2*(A/6) - (A/3) = A/3 - A/3 = 0
```

Nodo di lato:

```
int 4 L1 L2 dA = 4 * 1!*1!*0!/4! * 2A = 4*(1/24)*2A = A/3
```

Risultato:

```
f = p * [ 0, 0, 0, A/3, A/3, A/3 ]        somma f_i = pA   OK
```

Il vertice riceve **zero, non un valore negativo**. Il valore negativo è la faccia
quadrangolare a 8 nodi (serendipity), non il triangolo - vedi sez. 7.

### Perché vale solo per la faccia "regolare"

L'integrale sopra è in coordinate d'area; il passaggio all'elemento reale introduce lo
jacobiano. Se la faccia è **piana e i nodi di lato stanno esattamente a metà spigolo**,
lo jacobiano è costante e si semplifica: il risultato `[0,0,0,1/3,1/3,1/3]` è esatto. Se
i nodi di lato sono spostati (lato curvo, oppure nodo a metà geometrica ma non a metà
parametrica), lo jacobiano varia sul dominio e i coefficienti cambiano: i vertici non
ricevono più zero, e possono ricevere carico di segno opposto alla pressione. Vedi
sez. 2 per numeri concreti.

---

## 2. Verifica numerica indipendente

Quadratura simmetrica a 7 punti esatta al grado 5 (l'integrando ha grado 4 al massimo),
`/usr/bin/python3` 3.9.6, eseguita il 2026-08-26. Triangolo di riferimento con vertici
`(0,0), (1,0), (0,1)`.

| Caso | `f/(pA)` - v1, v2, v3, l4, l5, l6 | somma |
|---|---|---|
| lati diritti, nodi a metà spigolo | `0, 0, 0, +0.3333, +0.3333, +0.3333` | 1 |
| nodo 4 spostato a `s = 0.65` sul lato diritto | `+0.0300, -0.0300, 0, +0.3333, +0.2933, +0.3733` | 1 |
| lato 2-3 curvato verso l'esterno (nodo 5 in `(0.6,0.6)`) | `-0.0105, +0.0053, +0.0053, +0.3263, +0.3474, +0.3263` | 1 |
| lato 2-3 curvato verso l'interno (nodo 5 in `(0.42,0.42)`) | `+0.0136, -0.0068, -0.0068, +0.3424, +0.3153, +0.3424` | 1 |

Conclusioni operative:

- caso regolare: `0` e `1/3` esatti a macchina;
- nodo di lato fuori mezzeria: i vertici prendono carico **non nullo e di segno
  discorde tra loro**, con modulo di ordine 3% di `pA` già per uno spostamento del 15%
  del lato;
- lato curvo: contributi ai vertici di ordine 1% di `pA`, di segno opposto alla
  pressione se la faccia bomba verso l'esterno;
- la somma resta sempre `pA`: l'equilibrio globale non è mai violato, la somma delle
  funzioni di forma vale identicamente 1.

Verifica riproducibile - copia e incolla:

```python
def shp(L1, L2, L3):
    N = [L1*(2*L1-1), L2*(2*L2-1), L3*(2*L3-1), 4*L1*L2, 4*L2*L3, 4*L3*L1]
    dNx = [1-4*L1, 4*L2-1, 0, 4*(L1-L2), 4*L3, -4*L3]
    dNy = [1-4*L1, 0, 4*L3-1, -4*L2, 4*L2, 4*(L1-L3)]
    return N, dNx, dNy

a1, b1, w1 = 0.0597158717, 0.4701420641, 0.1323941527
a2, b2, w2 = 0.7974269853, 0.1012865073, 0.1259391805
pts = [(1/3, 1/3, 1/3, 9/40),
       (a1, b1, b1, w1), (b1, a1, b1, w1), (b1, b1, a1, w1),
       (a2, b2, b2, w2), (b2, a2, b2, w2), (b2, b2, a2, w2)]

def loads(c):
    F, A = [0.0]*6, 0.0
    for L1, L2, L3, w in pts:
        N, dNx, dNy = shp(L1, L2, L3)
        gx0 = sum(dNx[i]*c[i][0] for i in range(6))
        gx1 = sum(dNx[i]*c[i][1] for i in range(6))
        gy0 = sum(dNy[i]*c[i][0] for i in range(6))
        gy1 = sum(dNy[i]*c[i][1] for i in range(6))
        ww = w * (gx0*gy1 - gx1*gy0) * 0.5
        A += ww
        for i in range(6):
            F[i] += N[i]*ww
    return A, F

A, F = loads([(0,0), (1,0), (0,1), (.5,0), (.5,.5), (0,.5)])
assert all(abs(f/A - t) < 1e-12 for f, t in zip(F, [0, 0, 0, 1/3, 1/3, 1/3]))
```

---

## 3. Fonte primaria da citare in tesi

### Cosa NON sono riuscito a verificare

Cook-Malkus-Plesha-Witt, Zienkiewicz-Taylor, Bathe e Hughes sono tutti **fuori accesso**
dagli strumenti a disposizione: le copie su Internet Archive
(`conceptsapplicat0000unse_f2e3`, 4a ed. 2001) sono in prestito controllato e
restituiscono HTTP 403 sia sul testo OCR sia sull'endpoint di ricerca interna; l'API
Google Books ha risposto HTTP 429, quota esaurita. **Non riporto capitolo o pagina per
nessuno dei quattro**: sarebbe un numero inventato. Va verificato su copia cartacea o di
biblioteca prima che finisca in bibliografia.

### Cosa E' verificato e citabile subito

Catena di citazione difendibile in tesi, tutta verificata:

1. **Funzioni di forma del T6** - Abaqus Theory Guide, sez. 3.2.6 «Triangular,
   tetrahedral, and wedge elements», voce «Second-order triangle (6 nodes)».
2. **Formula d'integrazione in coordinate naturali** - Eisenberg e Malvern (1973),
   IJNME 7(4):574-575, DOI 10.1002/nme.1620070421.
3. **Il risultato dichiarato dal produttore del solutore** - Abaqus Theory Guide
   sez. 3.2.6, verbatim: «a constant pressure on an element face produces zero
   equivalent loads at the corner nodes».
4. **Il risultato dichiarato indipendentemente da un secondo produttore** - Ansys
   Mechanical APDL Modeling and Meshing Guide sez. 2.2.2 «Quadratic Elements (Midside
   Nodes)» e Figura 2.3 «Equivalent Nodal Allocations», che ha un caso dedicato
   «(c) triangular 3D elements».
5. **Il brevetto originario del C3D10M** - US 6,044,210 e US 6,697,770 B1, Nagtegaal
   (Hibbitt, Karlsson and Sorensen), che enuncia il fatto come scoperta dell'inventore.

Se serve *un solo* riferimento bibliografico "di libro", il candidato più probabile
resta Cook et al. (4a ed., Wiley 2002) nel capitolo sugli elementi isoparametrici
triangolari - ma **la pagina va confermata leggendola**, qui non è confermata.

---

## 4. Cosa dice la documentazione Abaqus (citazioni verbatim)

### 4.1 Il risultato, dichiarato senza ambiguità

Abaqus Theory Guide sez. 3.2.6, «Triangular, tetrahedral, and wedge elements»:

> «Second-order tetrahedra are not suitable for the analysis of contact problems: a
> constant pressure on an element face produces zero equivalent loads at the corner
> nodes. In contact problems this makes the contact condition at the corners
> indeterminate, with failure of the solution likely because of excessive gap chatter.
> The same argument holds true for contact on triangular faces of a wedge element.»

Fonte: https://ceae-server.colorado.edu/v2016/books/stm/ch03s02ath64.html - mirror
universitario del manuale ufficiale, versione 2016.

Nota: la frase parla di *pressione costante*, non solo di contatto. Il contatto è la
conseguenza citata, non l'ipotesi.

### 4.2 Come Abaqus integra i carichi distribuiti

Stessa sezione 3.2.6, sotto «Integration»:

> «The three-point scheme is also used for the stiffness of the second-order triangle
> when it is used in stress/displacement applications. [...] Distributed loads are
> integrated using three points.»

> «For stress/displacement applications the second-order tetrahedron uses 4 integration
> points for its stiffness matrix and 15 integration points for its consistent mass
> matrix.»

Cioè: il carico da `*DSLOAD` o `*DLOAD` è **integrato sulla faccia** con quadratura a 3
punti, esatta per l'integrando quadratico del caso regolare; non è ripartito con regole
euristiche. È esattamente il vettore `f_i = int N_i p dA` della sez. 1.

### 4.3 L'avvertenza sul segno (facce quadrangolari, non triangolari)

Abaqus Analysis User's Guide, «Common difficulties associated with contact modeling in
Abaqus/Standard», sezione «Poorly defined surfaces», sottosezione «Three-dimensional
surfaces with second-order faces and a node-to-surface formulation»:

> «Some second-order element types are not well-suited for underlying the slave surface
> with the combination of a node-to-surface contact formulation and strict enforcement
> of "hard" contact conditions, because of the distribution of equivalent nodal forces
> when a pressure acts on the face of the element.»

> «a constant pressure applied to the face of a second-order element without a midface
> node produces forces at the corner nodes acting in the opposite sense of the pressure»

> «Second-order tetrahedral elements (C3D10 and C3D10HS) have zero contact force at
> their corner nodes»

Fonte: https://abaqus-docs.mit.edu/2017/English/SIMACAEITNRefMap/simaitn-c-contacttrouble.htm
- mirror MIT della documentazione ufficiale 2017.

**Distinzione da tenere ferma in tesi**: il carico *negativo* ai vertici riguarda le
facce quadrangolari a 8 nodi senza nodo centrale (C3D20, C3D20R). La faccia
**triangolare** a 6 nodi dà **zero**, non negativo. Chi cita "carichi negativi ai
vertici" per un tet10 sta trasportando il risultato dell'esaedro.

### 4.4 Scelta dell'elemento

Abaqus, «Element selection»:

> «These elements are designed to be used in complex contact simulations; regular
> second-order tetrahedral elements (C3D10) have zero contact force at their corner
> nodes, leading to poor predictions of the contact pressures.»

Fonte: https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-cntelmselect.htm

---

## 5. C3D10M: sì, cambia, e cambia per progetto

### 5.1 Il brevetto

Il tetraedro modificato è coperto da **US 6,044,210 A** (Joop C. Nagtegaal, assegnataria
Hibbitt, Karlsson and Sorensen Inc., depositato 5 giugno 1997, concesso 28 marzo 2000) e
dalla continuazione **US 6,697,770 B1**, «Computer process for prescribing second-order
tetrahedral elements during deformation simulation in the design analysis of
structures». Testo verbatim:

> «I have determined that these elements are not appropriate for contact problems
> because in uniform pressure situations, the contact forces are non-uniform at the
> corner and midside nodes. I have further determined that equisized tetrahedra have
> zero contact forces at the corner nodes, so that the midside nodes carry all the
> contact load.»

Ed ecco il punto di progetto del C3D10M:

> «In Step S20, coefficients (e.g., A_tri, B_tri, A_tet, B_tet) to result in uniform
> distribution of nodal forces are determined. The coefficients A_tri, B_tri have been
> determined analytically and numerically so that the equivalent nodal forces on the six
> external nodes of a face due to constant applied pressure on the face with a
> constrained mid-face node are uniform.»

Meccanismo: l'elemento è **composito**, non isoparametrico quadratico. Dal brevetto:

> «the tetrahedral element is composed of four uniform-strain hexahedra and fifteen
> nodes [...] the first ten nodes (corner and mid-edge nodes) are defined by the user»

più un nodo interno (11) e quattro nodi di centro faccia (12-15) vincolati da

```
x12 = A_tri (x1 + x2 + x3) + B_tri (x5 + x6 + x7)     (e analoghe per 13, 14, 15)
```

> «where A_tri = -1/16 and B_tri = 2/5»   (US 6,697,770 B1)

**Risposta secca alla domanda 4: sì, la distribuzione cambia.** Sul C3D10M una pressione
uniforme su faccia piana si ripartisce **uniforme sui sei nodi della faccia**, cioè
`pA/6` a ciascuno: è esattamente ciò che il progettista dell'elemento ha imposto
scegliendo `A_tri` e `B_tri`. Il valore `pA/6` per nodo è mio, segue da "uniform" più
somma pari a `pA`; nel brevetto non è stampato.

### 5.1.1 Caveat sul coefficiente A_tri (rilievo mio, da segnalare)

`US 6,697,770 B1` stampa `A_tri = -1/16`, `B_tri = 2/5`. Ma per un tetraedro regolare con
nodi di lato a metà spigolo la relazione deve restituire il baricentro della faccia, il
che impone `3*(A_tri + B_tri) = 1`, cioè `A_tri + B_tri = 1/3`. Con i valori stampati:

```
-1/16 + 2/5 = 0.3375    contro    1/3 = 0.3333...
```

La condizione è soddisfatta *esattamente* da `A_tri = -1/15`, perché `-1/15 + 2/5 = 1/3`.
Molto probabilmente il brevetto ha un refuso 15 diventato 16, propagato dal brevetto
padre alla continuazione; nel rendering Google Patents di US 6,044,210 A si perde per
giunta il segno meno e resta `1/16`. **Inferenza mia, non verificata su altra fonte**: se
il numero serve in tesi, va confermato sul PDF originale USPTO o sul manuale Abaqus, non
citato dal solo brevetto.

### 5.2 La documentazione utente

Abaqus Analysis User's Guide sez. 28.1.1 «Solid (continuum) elements», sottosezione
«Modified triangular and tetrahedral elements»:

> «Modified triangular and tetrahedral elements work well in contact, exhibit minimal
> shear and volumetric locking, and are robust during finite deformation [...] These
> elements use a lumped matrix formulation for dynamic analysis.»

> «regular second-order tetrahedral elements cannot underly a slave surface for the
> node-to-surface contact formulation with strict enforcement of a "hard" contact
> relationship.»

Fonte: https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01alm01.html

### 5.3 Conferma indipendente (atti di conferenza)

Diehl, T.; Carroll, D., «Utilizing ABAQUS' 10-Node Modified Tet for Analyzing Impact
Problems Involving Thin-Walled Structures», Proceedings, ABAQUS Users' Conference,
31 maggio - 2 giugno 2000, Newport (RI), p. 6:

> «The appropriate nodal weighting was computed in a separate analysis where a normal
> unit pressure was applied to the elements while their nodes were completely
> constrained. The resulting reaction forces yielded the nodal weighting factors. It is
> important to note that the nodal weighting for a C3D10 is significantly different than
> a C3D10M.»

Utile due volte: conferma la differenza, e descrive la **procedura sperimentale** per
misurarla su qualunque solutore: pressione unitaria più tutti i nodi vincolati, e le
reazioni *sono* i pesi nodali. Riproducibile in CalculiX in dieci righe di deck.

Fonte: https://bodietech.com/themes/user/site/default/asset/publications/Abaqus10NodeTet_Diehl_2000.pdf

---

## 6. Rischio pratico: ripartire "a occhio"

Due errori comuni, entrambi sbagliati e sbagliati in modo diverso.

### 6.1 pA/3 su *tutti e sei* i nodi

Somma pari a `2pA`. **Raddoppia il carico applicato.** Errore del 100% sul risultante.
Non è una sottigliezza di distribuzione, è un errore di equilibrio globale: va escluso
da una guardia, non discusso.

### 6.2 pA/6 a ciascuno dei sei nodi (lumping "uniforme")

Somma pari a `pA`, corretta. È l'errore interessante.

Differenza rispetto al consistente:

```
delta_f = f_lump - f_cons = pA * [ +1/6, +1/6, +1/6, -1/6, -1/6, -1/6 ]
```

Quantificazione (conti miei, esatti):

- **risultante**: identico. La somma di `delta_f` è nulla.
- **momento risultante**: identico. Per faccia piana e lati diritti il baricentro dei
  sei carichi `pA/6` è `(x1+x2+x3)/3`, perché la somma delle posizioni dei tre nodi di
  lato vale `x1+x2+x3`; il baricentro dei tre carichi `pA/3` sui nodi di lato è lo
  stesso punto. Forze parallele, stesso risultante, stesso punto d'applicazione:
  **stesso momento rispetto a qualunque polo**. Quindi `delta_f` è un **sistema
  autoequilibrato**.
- **conseguenza**: per Saint-Venant l'errore è **locale**, decade allontanandosi dalla
  faccia caricata; reazioni vincolari lontane e spostamenti globali restano
  essenzialmente corretti. È esattamente ciò che rende l'errore insidioso: non si vede
  nei controlli d'equilibrio.
- **entità locale**: `1/6` di `pA` per nodo, cioè **50% del valore consistente sui nodi
  di lato** e un carico spurio **da zero a `+pA/6`** sui vertici. Sulla faccia caricata
  la tensione superficiale ricostruita sbaglia dello stesso ordine, proprio dove di
  solito si legge il picco.
- **energia**: `f_lump` non è il carico work-equivalent, quindi la soluzione non è più
  quella di Galerkin del problema di partenza; le stime d'errore ottimali in norma
  energetica non si applicano al risultato ottenuto.

### 6.3 Letteratura che quantifica

**Non ho trovato** un articolo peer-reviewed che quantifichi l'errore del lumping
ingenuo su facce T6 in funzione della finezza di mesh. Quello che esiste, ed è citabile,
è l'avvertenza dei produttori:

- Ansys, Modeling and Meshing Guide sez. 2.2.2: «Distributed loads and edge pressures
  are not allocated to the element nodes according to "common sense," as they are in the
  linear elements. (See Figure 2.3: Equivalent Nodal Allocations.) Reaction forces from
  midside-node elements exhibit the same nonintuitive interpretation.» - e ancora: «Mass
  at the midside nodes is greater than at the corner nodes.»
  https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_mod/Hlp_G_MOD2_4.html
- Abaqus Theory Guide sez. 3.2.6 e la sezione sul contatto citata in sez. 4.

Se in tesi serve un numero, il posto onesto è dichiararlo **derivato**, con la
derivazione della sez. 6.2 in nota.

---

## 7. Tabella di riferimento (tutti i valori verificati qui)

Pressione uniforme `p`, faccia o volume regolare, `A` area di faccia, `V` volume.

| Ente | Vertici | Nodi di lato | somma |
|---|---|---|---|
| Faccia T6 (tet10, wedge15), pressione | `0` | `pA/3` ciascuno | `pA` |
| Faccia Q8 senza nodo centrale (C3D20, C3D20R), pressione | `-pA/12` ciascuno | `+pA/3` ciascuno | `pA` |
| Volume tet10, forza di volume `b` per unità di volume | `-bV/20` ciascuno | `+bV/5` ciascuno | `bV` |
| Faccia T6 su C3D10M, pressione | `pA/6` | `pA/6` | `pA` |
| Lato quadratico a 3 nodi (linea), carico `q` per unità di lunghezza | `qL/6` | `2qL/3` | `qL` |

I valori Q8 e tet10-volume sono calcolati qui: `-0.08333` e `+0.33333` per Q8 da
quadratura di Gauss 3x3; `-1/20` e `+1/5` per il volume da formula esatta in coordinate
di volume, con verifica `4*(-1/20) + 6*(1/5) = 1`. La riga C3D10M è dichiarata uniforme
dal brevetto; il valore `pA/6` è conseguenza della somma pari a `pA`.

Il tetraedro quadratico è quindi **l'unico** dei tre casi in cui il vertice prende
esattamente zero: sulla faccia esaedrica prende negativo, sotto forza di volume prende
negativo.

---

## 8. Caveat

- **Versione dei manuali.** Le citazioni Abaqus vengono da mirror universitari
  pubblicamente accessibili delle versioni 2016 (Colorado) e 2017 (MIT). Il testo delle
  release recenti (Abaqus 2023 e successive, su help.3ds.com) non è stato controllato:
  richiede autenticazione. Il risultato fisico non può cambiare, la numerazione delle
  sezioni sì.
- **Numerazione delle sezioni.** «Solid (continuum) elements» è sez. 28.1.1 nel manuale
  2016 ma sez. 22.1.4 nella 6.6, e ancora diversa nelle release recenti. Citare la
  versione insieme al numero.
- **Facce non piane.** Le sez. 1 e 2 assumono faccia **piana**, cioè pressione con
  direzione costante. Su faccia genuinamente curva anche la *direzione* della trazione
  varia punto per punto, e ai coefficienti della sez. 2 si somma quell'effetto. Il caso
  curvo della sez. 2 è una curvatura *nel piano*: dimostra la variazione dello
  jacobiano, non l'effetto della normale variabile.
- **Convenzioni di numerazione dei nodi.** Abaqus numera prima i vertici poi i nodi di
  lato (Theory Guide sez. 3.2.6: «Corner nodes are numbered first, and then the midside
  nodes»), e CalculiX segue la stessa convenzione. Verificare comunque l'associazione
  lato-nodo prima di riusare la tabella su un altro solutore.
- **A_tri del brevetto**: vedi sez. 5.1.1, il valore stampato è internamente incoerente.
- **Cook, Zienkiewicz, Bathe, Hughes**: nessuna pagina verificata, vedi sez. 3.

---

## Fonti

Primarie, tutte consultate il 2026-08-26:

- Abaqus Theory Guide sez. 3.2.6 «Triangular, tetrahedral, and wedge elements» -
  https://ceae-server.colorado.edu/v2016/books/stm/ch03s02ath64.html
- Abaqus Analysis User's Guide sez. 28.1.1 «Solid (continuum) elements» -
  https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01alm01.html
- Abaqus, «Common difficulties associated with contact modeling in Abaqus/Standard» -
  https://abaqus-docs.mit.edu/2017/English/SIMACAEITNRefMap/simaitn-c-contacttrouble.htm
- Abaqus, «Element selection» -
  https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-cntelmselect.htm
- Ansys Mechanical APDL, Modeling and Meshing Guide sez. 2.2 «Choosing Between Linear
  and Higher Order Elements» -
  https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_mod/Hlp_G_MOD2_4.html
- US 6,044,210 A - Nagtegaal, Hibbitt Karlsson and Sorensen -
  https://patents.google.com/patent/US6044210A/en
- US 6,697,770 B1 - continuazione -
  https://patents.google.com/patent/US6697770B1/en
- Eisenberg e Malvern, IJNME 7(4):574-575 (1973), DOI 10.1002/nme.1620070421 -
  https://onlinelibrary.wiley.com/doi/abs/10.1002/nme.1620070421 (soli metadati)
- Diehl e Carroll, ABAQUS Users' Conference 2000, p. 6 -
  https://bodietech.com/themes/user/site/default/asset/publications/Abaqus10NodeTet_Diehl_2000.pdf
