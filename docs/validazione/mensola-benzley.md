# Mensola di Benzley et al. (1995) — geometria quotata e valori di riferimento

Fonte primaria: S. E. Benzley, E. Perry, K. Merkley, B. Clark, G. Sjaardema,
«A Comparison of All Hexagonal and All Tetrahedral Finite Element Meshes for
Elastic and Elasto-plastic Analysis», Proc. 4th International Meshing Roundtable,
1995, pp. 179-191.
PDF letto: <https://coreform.com/papers/hex_tet_comparison.pdf> (8 pagine, PDF 1.3,
scaricato il 26/08/2026). I numeri di pagina qui sotto sono pagine del PDF, non del volume.

Convenzione: **[V]** = stampato nel paper. **[I]** = inferito, con la verifica numerica
che lo sostiene. Nessun numero **[I]** va citato in tesi come dato del paper.

---

## 1. Geometria della barra

| Grandezza | Valore | Fonte |
|---|---|---|
| Lunghezza | 10,0 | [V] Figura 3, p. 5 (quota 10,0 sull'asse lungo) |
| Larghezza sezione | 1,0 | [V] Figura 3, p. 5 |
| Altezza sezione | 1,0 | [V] Figura 3, p. 5 |
| Ascissa del *Reference Point* | 5,0 dall'estremo incastrato | [V] Figura 3, p. 5 (quota 5,0 con freccia al Reference Point) |

Sezione quindi **quadrata 1x1**, non genericamente rettangolare: il testo dice
«rectangular cross-section» (p. 5) ma la figura quota 1,0 e 1,0.

### Unità — non dichiarate

Il paper **non dichiara mai** le unità: né in Figura 3, né nel testo, né nelle
tabelle. Compaiono solo numeri nudi, e qui sotto stanno **come il paper li
stampa**: «Young's Modulus = 10,000,000», «Density = 0.1», «10.0», «1.0» — virgola
americana per le migliaia, punto per i decimali. Non c'è nemmeno una frase che le
dichiari adimensionali.

**[I]** La terna che rende consistenti tutti e quattro i valori di riferimento è
**pollice / libbra-forza / secondo**, con la densità letta come **peso specifico**
(lb/in^3) e g = 386,4 in/s^2. Vedi §4 e §7: con rho_massa = 0,1/386,4 la prima frequenza
flessionale viene 317,54 Hz contro i 317,5 stampati; leggendo 0,1 come densità di
massa verrebbe 16,2 Hz. E = 10^7 psi + 0,1 lb/in^3 = alluminio. Resta inferenza:
il paper non lo scrive.

## 2. Vincolo e carico

- **Vincolo**: barra «fixed at one end» (p. 5, testo e tratteggio in Figura 3 su
  tutta la faccia d'estremità). Il paper **non specifica** quali gradi di libertà
  siano bloccati né su quali nodi della faccia; il conteggio dei DOF (§5) dice che
  i DOF vincolati sono comunque **contati** nei totali di Figura 3.
- **Flessione**: quattro forze **F = .25** ai quattro spigoli della faccia libera,
  tutte trasversali e concordi (verso il basso) → risultante **P = 1,0** all'estremo
  libero. [V] Figura 3, p. 5 (vista sinistra: quattro etichette F = .25, frecce parallele).
- **Torsione**: le stesse quattro forze **F = .25** agli spigoli della faccia libera,
  ma **tangenziali**, disposte a coppia attorno all'asse. [V] Figura 3, p. 5 (vista destra).
  Il **valore della coppia risultante non è stampato**: vedi §6 per le due letture
  possibili (T = 0,7071 oppure T = 1,4142) e per l'incoerenza che ne segue.
- Nessun momento concentrato, nessun carico distribuito: solo forze nodali agli spigoli.

## 3. Materiale

| Caso | Parametri | Fonte |
|---|---|---|
| Barra, elastico | «E = 10,000,000; nu = .3 e .49; Density = 0.1» | [V] Figura 3, p. 5 |
| Barra, elasto-plastico | «E = 10,000,000; nu = .3 (e .49 in figura); Yield Stress = 10,000» | [V] Figura 7 e testo, p. 7 |
| Cubo unitario (studio autovalori, **caso diverso**) | «E = 30,000,000; nu = .3» | [V] p. 3 |

Non mescolare i due E: **30,000,000** è del cubo unitario dello studio sugli autovalori
della matrice di rigidezza (Tabella 1, p. 3), **non** della mensola. La densità 0,1
compare solo in Figura 3 e serve al caso modale.

## 4. Valori di riferimento analitici

### Flessione (statica)

> «the analytical magnitudes of the normal displacement and the bending stress at
> the reference point, using classical beam theory [10] are 0.000125 and 30.0
> respectively. Both the displacement and bending stress are independent of
> Poisson's ratio.» — [V] p. 5

- Fonte analitica: **[10] = Gere & Timoshenko, Mechanics of Materials, PWS, 1990**
  (teoria classica della trave). **Non** Timoshenko & Goodier: quello è [11], torsione.
- Il paper **non stampa la formula** né dice esplicitamente che il Reference Point sia
  a metà luce sulla fibra estrema. **[I]** verificato esattamente:
  - I = 1*1^3/12 = 0,08333, EI = 833333,3
  - delta(x) = P x^2 (3L - x)/(6EI) con P = 1,0, L = 10, **x = 5** → **1,25e-4** (esatto)
  - sigma = M c/I con M = P(L-x) = 5, c = 0,5 → **30,0** (esatto)
  Quindi **freccia trasversale a metà luce** (non all'estremo: là sarebbe 4,0e-4) e
  **tensione flessionale a metà luce sulla fibra estrema**, coerenti con la quota 5,0
  del Reference Point in Figura 3.

### Torsione (statica)

> «The shear stress from this solution is 6.8 and is independent of Poisson's ratio.
> The rotational displacement (i.e. the translation of the reference point in the
> direction of twisting) is 0.000003269 for a Poisson's ratio of .3, and 0.000003747
> for a Poisson's ratio of .49.» — [V] p. 5

Fonte: **[11] Timoshenko & Goodier, Theory of Elasticity, 3rd ed.** Il paper **non
riporta né la formula né il fattore di forma**. Vedi §6.

### Modale

> «The analytical solution for the bending mode is given by Hurty and Rubenstien
> [13] as 317.5 cycles/sec. An approximate solution for the torsional vibration
> mode, assuming the stiffness value as determined from the elasticity solution
> [11], and no warping, is 2614 cycles/sec.» — [V] p. 7

Nota: quei due numeri stanno nel **testo sopra la Tabella 4**, non dentro la Tabella 4
(che contiene solo errori percentuali).
Fonte: **[13] Hurty & Rubinstein, Dynamics of Structures, Prentice-Hall, 1964**.
Nessuna formula stampata. Vedi §7.

## 5. Densità di maglio e gradi di libertà

Tutti i livelli stanno in **Figura 3, p. 5** (tabellina Designation / DOF) e ricompaiono
come righe di Tabella 2 (p. 6), Tabella 3 (p. 6), Tabella 4 (p. 7). I livelli sono
**otto**, non sei: oltre a 567, 666, 1863, 3075, 3615, 3894 ci sono **10995** (4x4 QH)
e **23613** (4x4 QT).

| Designazione | DOF [V] | Sezione | Elementi | Nodi |
|---|---|---|---|---|
| 2x2 LH | 567 | 2x2 | **80 esaedri** (2*2*20) [I] | 189 = 3*3*21 [I] |
| 2x2 QH | 1863 | 2x2 | 80 esaedri a 20 nodi [I] | 621 [I] |
| 4x4 LH | 3075 | 4x4 | **640 esaedri** (4*4*40) [I] | 1025 = 5*5*41 [I] |
| 4x4 QH | 10995 | 4x4 | 640 esaedri a 20 nodi [I] | 3665 [I] |
| 2x2 LT | 666 | 2x2 | **non stampato** | 222 [I] |
| 2x2 QT | 3894 | 2x2 | **non stampato** | 1298 [I] |
| 4x4 LT | 3615 | 4x4 | **non stampato** | 1205 [I] |
| 4x4 QT | 23613 | 4x4 | **non stampato** | 7871 [I] |

Regola di costruzione stampata [V] p. 5:

> «The finite element models are generated with either a regular 2x2 or 4x4 mesh
> across the cross-section of the bar as shown in Figure 3. Element length in the
> longitudinal direction is the same as shown in the cross-section view of Figure 3.
> The quadratic finite element model is generated by simply adding midside nodes to
> the linear model.»

Quindi lato elemento **0,5** per il 2x2 (20 elementi in lunghezza) e **0,25** per il
4x4 (40 elementi). Verifica [I] che chiude i conti sugli esaedri:

- 3*3*21 nodi * 3 = **567** e 5*5*41 * 3 = **3075** → i **DOF sono contati su tutti i
  nodi, vincolati compresi** (nessuna sottrazione dei gradi bloccati). Per confrontare
  una nostra maglia serve la stessa convenzione: 3 * numero_nodi.
- Quadratici: 621 = 189 nodi d'angolo + 432 nodi di mezzeria spigolo → 1863; e
  1025 + 2640 = 3665 → 10995. Confermano esaedri **serendipity a 20 nodi** (nessun nodo
  di faccia né centrale).

**Tetraedri: numero di elementi non ricostruibile.** I nodi impliciti (222, 1205) non
fattorizzano in una griglia strutturata (222 = 2*3*37; 1205 = 5*241) e non coincidono con
quelli esaedrici a pari sezione. La figura etichetta le sezioni tetraedriche come
«**Nominal** Cross-Section Mesh» (2x2: ogni sottoquadrato tagliato da una diagonale verso
il centro, 8 triangoli; 4x4: schema analogo). Il paper **non dice** con quale mesher o
schema di suddivisione siano nate le maglie tet, né quanti elementi contengano.
Per la comparabilità si pareggiano i **DOF**, non gli elementi.

## 6. Caso torsione — geometria, carico, fonte analitica

- Geometria e vincolo identici alla flessione (barra 1x1x10 incastrata a un estremo,
  Reference Point a 5,0). [V] Figura 3, p. 5.
- Carico: quattro forze tangenziali F = .25 agli spigoli della faccia libera. [V] Figura 3.
  **La coppia risultante non è stampata.**
- Fonte: [11] Timoshenko & Goodier, Theory of Elasticity, 3rd ed. **Nessuna formula e
  nessun fattore di forma stampati nel paper.**

**[I]** Ricostruzione con i valori classici di Saint-Venant per sezione quadrata di lato
a = 1: K = 0,140577 a^4, tau_max = T/(0,208 a^3), G = E/(2(1+nu)).

- Con **T = 0,7071** (= 4 * 0,25 * sqrt(2)/2, forze tangenziali agli spigoli, braccio
  sqrt(2)/2) e spostamento letto a **r = 0,5**, x = 5:
  theta*r = 3,2695e-6 per nu=.3 e 3,7473e-6 per nu=.49 → **coincidono esattamente** con i
  valori stampati 0,000003269 e 0,000003747. Torna anche il rapporto
  G(.3)/G(.49) = 1,1462 = 3,747/3,269.
- Con lo stesso T = 0,7071, tau_max = **3,40**, cioè **metà** del 6,8 stampato.
- La coppia che rende vero il 6,8 è **T = 1,4142**, ma allora lo spostamento torna solo
  leggendolo a **r = 0,25**, cioè dentro la sezione, non sulla superficie.

Conclusione onesta: **il paper non dà elementi per sciogliere il fattore 2 fra tensione e
spostamento torsionali.** Raccomandazione (non dato del paper): riprodurre con T = 0,7071
e lettura a r = 0,5, unica combinazione fisicamente coerente con «translation of the
reference point», e trattare il 6,8 come sospetto.

Anomalia collegata: in **Tabella 3, p. 6** il blocco torsione con nu = .49 riporta numeri
**identici** per Displacement e Stress (26,41/26,41, 68,80/68,80, 2,60/2,60, 5,44/5,44,
52,72/52,72, 4,70/4,70, 0,75/0,75, 1,41/1,41): sembra un copia-incolla, non due misure
indipendenti. In più le intestazioni interne di Tabella 3 dicono «Bending» mentre il
titolo della tabella dice «Torsion Model».

## 7. Caso modale

- **317,5 cycles/sec** = **primo modo flessionale** della mensola. [V] p. 7 («the bending
  mode»). Il paper **non dice in quale piano**: la sezione è quadrata 1x1, i due piani
  principali sono **degeneri** (stessa I = 0,08333) e i due primi modi flessionali hanno
  la stessa frequenza. Nessuna scelta di piano è necessaria.
- **[I]** La formula di Hurty & Rubinstein non è stampata. È la Bernoulli-Euler classica
  per mensola: f1 = (beta1 L)^2/(2 pi) * sqrt( EI / (rho A L^4) ), con **beta1 L = 1,875104**.
  Con E = 1e7, I = 0,08333, A = 1, L = 10, **rho = 0,1/386,4**: **f1 = 317,54 Hz** contro i
  317,5 stampati. È questa coincidenza a fissare le unità (§1) e a dire che Density = 0,1
  va inteso come **peso** specifico.
- **2614 cycles/sec** = primo modo **torsionale**, «assuming the stiffness value as
  determined from the elasticity solution [11], and no warping» [V] p. 7.
  **[I]** f = sqrt(G K/(rho I_p)) / (4L) con K = 0,140577, I_p = 1/6, rho = 0,1/386,4 dà:
  - nu = .49 → **2614,5 Hz** (il valore stampato)
  - nu = .3 → 2799,0 Hz
  Cioè il 2614 stampato corrisponde a **nu = 0,49**, non a nu = 0,3, benché la Tabella 4 usi
  un unico riferimento per entrambe le colonne. Per la torsione l'errore relativo è quasi
  insensibile a nu (frequenza e risposta scalano entrambe con sqrt(G)), il che spiega perché
  le due colonne di Tabella 4 siano quasi uguali (8,86% contro 8,88% su LH). Inferenza,
  non dichiarazione del paper.

## 8. Cosa il paper NON stampa

1. Le **unità** — mai, da nessuna parte.
2. La **coppia torcente** risultante e il braccio delle forze tangenziali.
3. Le **formule** analitiche: né trave (rimando a [10]), né torsione (rimando a [11], senza
   fattore di forma), né modale (rimando a [13]).
4. Il **numero di elementi** di qualunque maglia — solo i DOF e le designazioni 2x2/4x4.
5. Come sono generate le **maglie tetraedriche** (mesher, schema di suddivisione).
6. Il dettaglio del **vincolo** (quali DOF, su quali nodi della faccia incastrata).
7. Il valore di **g** implicito nella densità.
8. Dove esattamente cade il **Reference Point** nella sezione (superficie? spigolo? mezzeria
   del lato?) — dedotto dai numeri, non scritto.

## 9. Tabelle di errore, per riferimento

- **Tabella 2, p. 6**: errore su spostamento e tensione, flessione, nu=.3 e nu=.49.
  Da 0,00% (LH, tensione) a 71,68% (2x2 LT, spostamento, nu=.49).
- **Tabella 3, p. 6**: idem, torsione. 2x2 LT al 50,81% (nu=.3) e 68,80% (nu=.49).
- **Tabella 4, p. 7**: errore sulle frequenze, flessione e torsione.
- **Tabella 5, p. 8**: spostamento del tip, elasto-plastico, passi di carico
  Load 4xF = 0, 160, 185,2, 196,08, 208,3, 238.
- **Tabella 6, p. 8**: spostamento del punto medio, torsione elasto-plastica, coppie applicate
  0, 1201, 1717, 1844, 1880, con riga di riferimento «Ref 14»
  (**[14] Mendelson, Plasticity: Theory and Application, Macmillan, 1968**, soluzione alle
  differenze finite).

