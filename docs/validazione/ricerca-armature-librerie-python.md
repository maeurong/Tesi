# Le librerie Python che modellano una sezione in cemento armato

Ricerca del 28/08/2026, su repo `main` a `787fdeb`. Domanda posta: il programma
deve permettere di **inserire le armature nelle sezioni trasversali** degli
elementi in cemento armato, e non si vuole inventare nulla. Questo documento
copre un solo fronte — **le librerie Python installabili** che descrivono una
sezione armata — e risponde a sei domande: che cosa esiste, se si installa
davvero, come descrive la sezione, che cosa restituisce, se sa parlare a
OpenSees, e quale converrebbe adottare.

Le fonti sono primarie: l'API JSON di PyPI, i file distribuiti dai pacchetti
stessi, i metadati dei repository ufficiali su GitHub. **Il sorgente di ogni
libreria candidata è stato scaricato ed estratto in questa sessione**, e le
firme riportate sono trascritte da quei file, non citate a memoria né riprese
dalla documentazione narrativa.

## Convenzioni di lettura

- **[V]** = verificato leggendo la fonte primaria in questa sessione (metadati
  PyPI, file di sorgente distribuito, API di GitHub).
- **[M]** = misurato in questa sessione. Non è una citazione: è un conteggio o
  un'ispezione, e il modo in cui l'ho ottenuta è riportato.
- **[INF]** = inferenza mia, non letta su fonte. Da non citare come fatto.
- **[NON TROVATO]** = non l'ho trovato pubblicato in chiaro. Non l'ho inventato.

Le firme di funzione sono riportate **verbatim dal file distribuito**, con i
soli tipi e valori predefiniti, senza il corpo. Quando taglio, lo dico.

## Artefatti consultati

| artefatto | provenienza | stato |
|---|---|---|
| `sectionproperties-3.10.2-py3-none-any.whl`, 113.723 B | PyPI | scaricato, estratto, letto file per file [V] |
| `concreteproperties-0.8.0-py3-none-any.whl`, 84.785 B | PyPI | scaricato, estratto, letto file per file [V] |
| `structuralcodes-0.7.1-py3-none-any.whl`, 192.554 B | PyPI | scaricato, estratto, letto file per file [V] |
| `strupy-0.6.3.tar.gz`, 965.063 B | PyPI | scaricato, estratto, letto sugli import e sulla sezione rettangolare [V] |
| metadati PyPI di 20 pacchetti | `https://pypi.org/pypi/<nome>/json` | interrogati a macchina [M] |
| metadati di 5 repository | API di GitHub, `https://api.github.com/repos/...` | interrogati a macchina [M] |

**Premesse del committente, ricontrollate prima di ragionarci sopra.** Tutte e
quattro risolvono. `config.TetConfig.element` ammette `C3D10` e `C3D4`;
`config.ModelConfig.element` ammette i tre esaedri `C3D8I`, `C3D8`, `C3D8R`;
`wall.prior` è lo step 12 per intero e scompone la nuvola in membrature
prismatiche misurandone fra l'altro la sezione; `hexa.costruisci` da quelle
membrature genera i prismi esaedrici. `PRODUCT.md` impone mm, N, MPa,
tonnellata, secondo, e dichiara la distribuzione come repository più `uv sync`
senza eseguibile impacchettato, con l'autore passato da Windows 11 a macOS
Apple Silicon il 16/08/2026. Nessuna correzione da riportare. [V]

**Un vincolo che il committente non ha citato e che decide metà delle risposte
di §2**: `meshrec/pyproject.toml` dichiara `requires-python = ">=3.12,<3.13"`.
La domanda «Python 3.12 è supportato?» non è quindi una domanda di comodo: 3.12
è **l'unica** versione che questo progetto usa, e una libreria che pubblica
ruote solo per 3.13 o solo per 3.11 è fuori. [V]

---

## 1. Censimento

### 1.1 Le sei nominate, più quelle trovate

Ordinate per pertinenza alla domanda posta — *descrivere una sezione armata* —
e non per notorietà.

| libreria | versione | ultimo rilascio | licenza | fa davvero questo lavoro? |
|---|---|---|---|---|
| `structuralcodes` | 0.7.1 | 10/06/2026 | Apache-2.0 | **sì**: geometria di sezione, barre come punti con diametro, materiali normativi Eurocodice/Model Code |
| `concreteproperties` | 0.8.0 | 06/07/2026 | MIT | **sì**: sezione armata completa, barre come aree, precompressione |
| `sectionproperties` | 3.10.2 | 24/01/2026 | MIT | **in parte**: proprietà geometriche di una sezione qualsiasi, con un catalogo di sezioni in c.a. già armate |
| `strupy` | 0.6.3 | 17/02/2021 | GPL | **sì ma**: sezione rettangolare in c.a. con armatura superiore e inferiore, e nient'altro |
| `rcdesign` | 0.4.18 | 17/05/2025 | MIT | **sì ma**: sezioni rettangolari e a T secondo IS 456 (norma indiana) |
| `PyCBA` | 1.0.1 | 27/06/2026 | AGPL-3.0-or-later | **no**: trave continua, analisi di linee d'influenza. Nessuna sezione armata |
| `anastruct` | 1.7.0 | 06/06/2026 | GPL-3.0-or-later dichiarata su PyPI, LGPL-3.0 sul repository | **no**: telaio piano a elementi finiti. Nessuna sezione armata |
| `eurocodepy` | 2027.0.0 | 13/08/2026 | [NON TROVATO] su PyPI | non ispezionato in questa sessione; **non raccomandabile** per il motivo di §2.4 |
| `steelpy`, `efficalc`, `handcalcs`, `forallpeople`, `structuralglass`, `PyNiteFEA` | — | — | — | **no**: acciaio, foglio di calcolo, unità di misura, vetro, telaio FEM. Fuori tema, elencati per chiudere la ricerca |

Cercati su PyPI e **non esistenti**: `concreteplanner`, `sectionproperties-plus`,
`concreteBeam`, `sectionprops`, `IStructE` — tutti 404. [M]

### 1.2 Che cosa fa davvero ciascuna delle quattro che contano

**`structuralcodes`** — pubblicata da *fib — International Federation for
Structural Concrete* (campo `Author-email` del `METADATA` distribuito), sotto
**Apache License 2.0** (file di licenza dentro la ruota). È la sola del gruppo
che porta la firma di un ente normativo. Contiene: i modelli materiali di
Eurocodice 2 nelle edizioni 2004 e 2023 e di Model Code 2010 e 2020; nove leggi
costitutive (parabola-rettangolo, Sargin, Popovics, elastoplastica, bilineare,
definita dall'utente, e altre); una geometria di sezione basata su `shapely`;
le funzioni per posare le barre; e un calcolatore di sezione con due
integratori intercambiabili, Marin e a fibre. **Il campo `license` dei metadati
PyPI è vuoto**, e chi si fermasse lì concluderebbe «licenza ignota»: la
licenza sta nel file, non nel campo. [V]

**`concreteproperties`** — di Robbie van Leeuwen, MIT. Costruisce sopra
`sectionproperties`: la geometria della sezione **è** una `CompoundGeometry` di
`sectionproperties`, e `concreteproperties` la classifica in calcestruzzo,
armatura discretizzata, armatura concentrata e trefoli. Porta due codici di
progetto, AS 3600 (australiano) e NZS 3101 (neozelandese), e nessuno europeo.
È la più ricca sul versante del **calcolo**: fessurazione, momento-curvatura,
dominio di interazione, flessione deviata, tensioni allo stato limite di
esercizio e ultimo. [V]

**`sectionproperties`** — stesso autore, MIT, 552 stelle. Non è una libreria di
cemento armato: è un calcolatore di proprietà geometriche di sezione — area,
momenti d'inerzia, centro di taglio, costante torsionale, ingobbamento — su una
mesh a triangoli a sei nodi. Il cemento armato ci entra da due porte: la
libreria di sezioni già armate (`concrete_rectangular_section`,
`concrete_column_section`, `concrete_tee_section`, `concrete_circular_section`,
`rectangular_wall`, `cee_wall`) e il fatto di essere la base geometrica di
`concreteproperties`. [V]

**`strupy`** — di Łukasz Laba, GPL, **ultimo rilascio 17/02/2021**, homepage su
Bitbucket. La sezione in c.a. è la classe `RcRecSect`: rettangolo `b × h`,
copriferro superiore e inferiore `ap`/`an`, diametri `fip`/`fin`, aree `Ap`/`An`.
Solo rettangoli, solo due letti di barre. Sconsigliata per tre ragioni
indipendenti, ciascuna sufficiente: la licenza GPL è virale e questo repository
non lo è; il `setup.py` distribuito **non dichiara alcuna dipendenza** mentre il
sorgente importa `unum`, `numpy`, `PyQt5` e `pyautocad`; e `pyautocad` pilota
AutoCAD via COM, cioè non esiste su macOS. [V]

### 1.3 Stato di manutenzione, misurato

Interrogata l'API di GitHub il 28/08/2026. [M]

| repository | stelle | issue aperte | ultimo push | licenza dichiarata | archiviato |
|---|---|---|---|---|---|
| `fib-international/structuralcodes` | 294 | 94 | 28/08/2026 | Apache-2.0 | no |
| `robbievanleeuwen/section-properties` | 552 | 5 | 16/04/2026 | MIT | no |
| `robbievanleeuwen/concrete-properties` | 241 | 14 | 06/07/2026 | MIT | no |
| `ccaprani/pycba` | 126 | 3 | 30/07/2026 | AGPL-3.0 | no |
| `anastruct/anaStruct` | 463 | — | 28/08/2026 | LGPL-3.0 | no |

Due letture che il numero da solo non dà. Le 94 issue aperte di
`structuralcodes` non sono un segnale di abbandono ma di cantiere: il push è
dello stesso giorno di questa ricerca, e il progetto ha 16 rilasci su PyPI. Le
5 issue di `sectionproperties` accanto a 41 rilasci sono invece il profilo di
una libreria matura e finita.

`anastruct` porta una **discordanza di licenza** da dichiarare se mai la si
usasse: i metadati PyPI della 1.7.0 dicono `GPL-3.0-or-later`, il repository
dice `LGPL-3.0`. Non l'ho risolta e non la risolvo qui. [V]

---

## 2. Installabilità reale, verificata su PyPI

Tutto ciò che segue è letto dall'API JSON di PyPI il 28/08/2026, elencando i
file effettivamente pubblicati. Non è una lettura della documentazione. [M]

### 2.1 Le tre candidate serie sono ruote universali

| pacchetto | file pubblicati | Python richiesto | Windows | macOS arm64 |
|---|---|---|---|---|
| `sectionproperties` 3.10.2 | 1 ruota `py3-none-any` + sorgente | `>=3.11` | sì, per costruzione | sì, per costruzione |
| `concreteproperties` 0.8.0 | 1 ruota `py3-none-any` + sorgente | `>=3.12` | sì, per costruzione | sì, per costruzione |
| `structuralcodes` 0.7.1 | 1 ruota `py3-none-any` + sorgente | `>=3.10` | sì, per costruzione | sì, per costruzione |

Nessuna delle tre contiene codice compilato. La domanda «esistono ruote per
Windows e per macOS arm64» per loro **non si pone**: una ruota `py3-none-any` è
la stessa ovunque. Python 3.12 è supportato da tutte e tre, e i classificatori
lo dichiarano esplicitamente in tutte e tre. [V]

**Il problema, se c'è, sta una riga più sotto**: nelle dipendenze transitive
compilate.

### 2.2 Il vero collo di bottiglia: il triangolatore

Entrambe le famiglie triangolano la sezione, e per farlo si portano dietro un
avvolgimento del *Triangle* di Shewchuk, scritto in C. Sono due pacchetti
diversi.

**`cytriangle`** — dipendenza di `sectionproperties`, quindi anche di
`concreteproperties`. Versione corrente 3.0.2, del 22/01/2026, `>=3.11`,
licenza dichiarata `LGPL 3.0`. Ruote pubblicate per cp312: [V]

    cytriangle-3.0.2-cp312-cp312-win_amd64.whl
    cytriangle-3.0.2-cp312-cp312-macosx_15_0_arm64.whl
    cytriangle-3.0.2-cp312-cp312-macosx_15_0_x86_64.whl
    cytriangle-3.0.2-cp312-cp312-manylinux_2_39_x86_64.whl

Windows sì, macOS arm64 sì. **Ma il tag dice `macosx_15_0`**: quella ruota
richiede macOS 15 o superiore. E le versioni 3.0.1 e 3.0.2 **non pubblicano
alcun archivio di sorgente** — 12 e 16 file, tutte ruote [M] — quindi su un
macOS 13 o 14 non c'è nemmeno la via del ripiego «compila tu». Il ripiego vero è
un'altra: `cytriangle` 2.0.0, del 12/02/2025, pubblica per cp312 le ruote
`macosx_13_0_x86_64` e `macosx_14_0_arm64` **e** un archivio di sorgente, e
`sectionproperties` non fissa un minimo su `cytriangle`, quindi il risolutore
può scendere. Che scenda davvero non l'ho provato: sarebbe una prova di
installazione su un macOS che qui non c'è. [INF]

Da notare per Linux: `manylinux_2_39` significa glibc 2.39 o superiore, cioè
Ubuntu 24.04 in avanti. Questa macchina ha glibc 2.43 [M], quindi passa, ma è
una soglia alta e va detta.

**`triangle`** — dipendenza di `structuralcodes`, dichiarata
`triangle>=20230923`. Versione corrente `20250106`, licenza `LGPL-3.0`. Ruote
per cp312: `win_amd64`, `win32`, `macosx_11_0_arm64`,
`manylinux_2_17_x86_64`, `manylinux_2_5_i686`. [V]

Windows sì, macOS arm64 sì **da macOS 11**, quindi un requisito molto più
mite di quello di `cytriangle`. In compenso: **nessun archivio di sorgente
pubblicato** [M], nessuna ruota per macOS x86_64, e nessuna ruota oltre cp313 —
il che è irrilevante qui, dove Python è 3.12, ma sarebbe un muro il giorno in
cui il progetto salisse a 3.14.

**Il caveat di licenza che nessuno dei due metadati dichiara in chiaro.** I
classificatori di `cytriangle` elencano *sia* `GNU Lesser General Public
License v3` *sia* `License :: Other/Proprietary License` [V]. La seconda voce
non è un refuso: il *Triangle* di Shewchuk che entrambi avvolgono è
distribuito con una restrizione d'uso commerciale. **Non ho aperto la licenza
originale di Triangle in questa sessione** e non affermo quale sia il suo testo
esatto: dichiaro che il classificatore proprietario c'è e che va letto prima di
usare queste librerie fuori da una tesi. [NON TROVATO — il testo di licenza a
monte]

### 2.3 Il peso vero: quante dipendenze, e di che genere

Le dipendenze dichiarate, verbatim dai metadati PyPI. [V]

| pacchetto | dipendenze obbligatorie |
|---|---|
| `structuralcodes` | `numpy>=1.20.0`, `scipy>=1.6.0`, `shapely>=2.0.2`, `triangle>=20230923` |
| `sectionproperties` | `cytriangle`, `matplotlib`, `more-itertools`, `numpy`, `rich[jupyter]`, `scipy`, `shapely` |
| `concreteproperties` | le sette di `sectionproperties`, più `quantiphy`, più `sectionproperties` stessa |

Il conto che interessa a questo progetto, che ha già `numpy` e `scipy` in
albero:

- **`structuralcodes` aggiunge due pacchetti**: `shapely` (ruote per cp312 su
  `win_amd64` e `macosx_11_0_arm64`, presenti [V]) e `triangle`.
- **`concreteproperties` ne aggiunge sette**: `shapely`, `cytriangle`,
  `matplotlib`, `more-itertools`, `quantiphy`, `rich` con l'extra `jupyter`, e
  `sectionproperties`.

L'extra `jupyter` di `rich` merita una riga: è dichiarato **obbligatorio**, non
opzionale, e trascina l'apparato di visualizzazione dei notebook dentro una
pipeline che notebook non ne ha. È fastidio, non ostacolo. [V]

**Nessuna delle tre trascina un solutore FEM.** Il criterio posto dal
committente — «numpy va bene, un solutore FEM intero no» — è rispettato da
tutte. Il solo codice compilato che entra è il triangolatore, poche centinaia di
kilobyte, non un solutore.

### 2.4 Le scartate per installabilità

- **`strupy` 0.6.3**: un solo archivio di sorgente, nessuna ruota, nessun
  vincolo di Python dichiarato, nessuna dipendenza dichiarata mentre il codice
  ne importa quattro. `pyautocad` non esiste su macOS. Fuori. [V]
- **`eurocodepy` 2027.0.0**: dichiara fra le dipendenze **obbligatorie**
  `mkdocs`, `mkdocs-material`, `mkdocstrings`, `mkdocs-gen-files`,
  `mkdocs-literate-nav`, `mkdocs-section-index`, `marimo`, `pyzmq`, `seaborn`,
  `plotly`. Cioè: installare la libreria installa il suo generatore di
  documentazione e un ambiente di notebook. È un difetto di confezionamento che
  da solo la squalifica per un progetto che dichiara `uv sync` come unica via
  di installazione. [V]
- **`PyCBA` 1.0.1**: si installa benissimo — ruota universale, `>=3.9`, tre
  dipendenze leggere — ma **è AGPL-3.0-or-later**, e non modella sezioni
  armate. Fuori per pertinenza prima che per licenza. [V]
- **`anastruct` 1.7.0**: pubblica 30 ruote compilate, cp310–cp314, comprese
  `cp312-win_amd64` e `cp312-macosx_11_0_arm64`. Si installa. Non modella
  sezioni armate. Fuori per pertinenza. [V]

---

## 3. Il modello dei dati della sezione armata

È la parte che il committente ha chiesto di riportare nella forma concreta,
perché è quella che il progetto dovrebbe imitare o riusare. Le firme sono
trascritte dai file distribuiti.

### 3.1 `structuralcodes`: la barra è un punto con un diametro

La geometria vive in `structuralcodes.geometry`. Il contorno è una
`SurfaceGeometry` costruita su un poligono di `shapely`, con la scorciatoia
`RectangularGeometry(width, height, material, concrete=False, origin=None,
name=None, group_label=None)` che genera il rettangolo centrato sull'origine.
Sommare geometrie con `+` dà una `CompoundGeometry`.

La barra è una `PointGeometry` costruita con `Point(coords)`, un diametro, un
materiale. L'area **non si passa: si calcola**, e la riga che la calcola è

    self._area = np.pi * diameter**2 / 4.0

Le tre funzioni che posano l'armatura, con la firma intera:

    add_reinforcement(geo, coords, diameter, material, group_label=None) -> CompoundGeometry
    add_reinforcement_line(geo, coords_i, coords_j, diameter, material,
                           n=0, s=0.0, first=True, last=True, group_label=None) -> CompoundGeometry
    add_reinforcement_circle(geo, center, radius, diameter, material,
                             n=0, s=0.0, first=True, last=True,
                             start_angle=0.0, stop_angle=2*np.pi, group_label=None) -> CompoundGeometry

`add_reinforcement_line` merita attenzione perché è **esattamente** la forma di
cui questo progetto ha bisogno: si danno i due estremi del letto di barre e poi
*o* il numero di barre `n` *o* il passo `s` — e se si danno entrambi la
funzione controlla che ci stiano e centra il gruppo, altrimenti solleva
`ValueError`. `first` e `last` permettono di non ripetere le barre d'angolo
quando si posano quattro letti attorno a un contorno. `group_label` etichetta un
gruppo di barre perché lo si possa ritrovare dopo.

### 3.2 `concreteproperties`: la barra è un'area, e buca il calcestruzzo

Il modello sta in `concreteproperties.pre`. Le firme:

    add_bar(geometry, area, material, x, y, n=4) -> Geometry | CompoundGeometry
    add_bar_rectangular_array(geometry, area, material, n_x, x_s, n_y=1, y_s=0,
                              anchor=(0, 0), exterior_only=False, n=4) -> Geometry | CompoundGeometry
    add_bar_circular_array(geometry, area, material, n_bar, r_array,
                           theta_0=0, ctr=(0, 0), n=4) -> Geometry | CompoundGeometry

Due differenze sostanziali rispetto a `structuralcodes`, non di stile.

**Prima: si passa l'area, non il diametro.** Chi ha in mano un diametro deve
convertirlo lui.

**Seconda: la barra è un poligono vero, e viene sottratta al calcestruzzo.** Il
corpo di `add_bar` è, verbatim:

    bar = circular_section_by_area(area=area, n=n, material=material).shift_section(
        x_offset=x, y_offset=y
    )
    return (geometry - bar) + bar

Cioè il cerchio della barra viene tolto dal calcestruzzo e poi riaggiunto come
regione propria: il calcestruzzo **non** è contato due volte sotto la barra. È
la scelta corretta, ed è la ragione per cui questa libreria ha bisogno di
un'area esatta. Ma il predefinito `n=4` va guardato: «Bars are discretised by
four points by default» dice la docstring, e un cerchio con quattro punti è un
quadrato. L'area del poligono è quella richiesta — la costruzione è *by area* —
ma la forma del buco nel calcestruzzo non è un cerchio, e a `n=4` neanche ci
somiglia.

I materiali sono dataclass, e la distinzione fra armatura discretizzata e
armatura concentrata **passa da un campo booleano del materiale**, non dalla
geometria:

| classe | campi | `meshed` |
|---|---|---|
| `Material` | `name`, `density`, `stress_strain_profile`, `colour`, `meshed` | dichiarato dall'utente |
| `Concrete` | i precedenti più `ultimate_stress_strain_profile`, `flexural_tensile_strength` | `True`, non modificabile |
| `Steel` | come `Material` | `True`, non modificabile |
| `SteelBar` | come `Steel` | **`False`**, non modificabile |
| `SteelStrand` | come `Steel` più `prestress_stress` | `False`, non modificabile |

`ConcreteSection.__init__(geometry, moment_centroid=None,
geometric_centroid_override=False, default_units=None)` prende quella
`CompoundGeometry` e la **smista** in sei liste: `concrete_geometries`,
`meshed_geometries`, `reinf_geometries_meshed`, `reinf_geometries_lumped`,
`strand_geometries`, `all_geometries`. Lo smistamento è per `isinstance` del
materiale. Il costruttore fa anche una cosa che vale la pena copiare: chiama
`check_geometry_overlaps` e **avvisa** se due regioni si sovrappongono, con il
messaggio «The provided geometry contains overlapping regions, results may be
incorrect». È un avviso, non un errore.

### 3.3 `sectionproperties`: la sezione armata come costruttore parametrico

Qui il modello dei dati non c'è: c'è un **catalogo di sezioni già armate**, e
l'armatura è descritta dai parametri del costruttore. La firma di
`concrete_rectangular_section`, per intero:

    concrete_rectangular_section(
        d, b,
        dia_top, area_top, n_top, c_top,
        dia_bot, area_bot, n_bot, c_bot,
        dia_side=None, area_side=None, n_side=0, c_side=0.0,
        n_circle=4,
        conc_mat=pre.DEFAULT_MATERIAL, steel_mat=pre.DEFAULT_MATERIAL,
    )

e le sorelle `concrete_column_section(d, b, dia_bar, area_bar, n_x, n_y, cover,
n_circle=4, filled=False, ...)`, `concrete_tee_section(d, b, d_f, b_f, ...)`,
`concrete_circular_section(d, area_conc, n_conc, dia_bar, area_bar, n_bar,
cover, ...)`, `rectangular_wall(d, t, dia_bar, area_bar, spacing, cover,
double=True, ...)`, `cee_wall(...)`.

**Diametro e area si passano entrambi, e separatamente.** Non è una ridondanza
distratta: il diametro serve a posizionare l'asse della barra rispetto al
copriferro, l'area serve a pesarla. Lo si legge nella riga che calcola il
raggio del cerchio di barre della sezione circolare, `r = d / 2 - cover -
dia_bar / 2`, e in quella della sezione a colonna, `-cover - dia_bar / 2`.

### 3.4 Il copriferro e le staffe: come li tratta ciascuna

Questa è la risposta più utile della sezione, ed è per sottrazione.

**Il copriferro non è mai un attributo della sezione.** In `sectionproperties`
è un **argomento dei costruttori** — `c_top`, `c_bot`, `c_side`, `cover` — usato
per calcolare la posizione delle barre e poi dimenticato: la geometria che esce
porta le barre dove vanno, non il numero che le ci ha messe. In
`concreteproperties` e in `structuralcodes` non compare affatto nel modello
geometrico: le barre si posano a coordinate, e il copriferro è aritmetica del
chiamante. Ricompare solo dentro le formule normative — controllo di
fessurazione dell'Eurocodice 2, dove è la variabile `c`. [M, cercato con `grep`
ricorsivo su tutti i file `.py` distribuiti dai tre pacchetti]

**Le staffe non sono modellate come geometria da nessuna delle tre.** Non
esiste una classe staffa, non esiste una funzione che ne posi una, non esiste
un attributo che le contenga. Dove compaiono, compaiono come **numeri dentro
una formula**:

- in `structuralcodes`, nelle funzioni di taglio, torsione e punzonamento di
  Model Code 2010, come `alpha` — «Inclination of the stirrups in degrees» — e
  nel modello di aderenza barra-calcestruzzo, dove il confinamento è un
  `Literal['unconfined', 'stirrups']`;
- in `concreteproperties`, dentro il profilo tensione-deformazione
  `ModifiedMander`, che accetta i parametri del confinamento (passo, area di un
  braccio, copriferro `cvr` alla staffa, tipo di sezione `rect` con «closed
  stirrup/tie transverse reinforcement») e ne ricava una legge di calcestruzzo
  confinato.

**Conseguenza diretta per questo progetto.** Se «inserire le armature» include
disegnare le staffe, nessuna di queste librerie lo fa e nessuna va aspettata:
la staffa entra nel calcolo come parametro di confinamento, non come geometria.
Se invece include solo le barre longitudinali, tutte e tre lo fanno, e in modo
quasi identico.

### 3.5 Il minimo comune denominatore

Messe una accanto all'altra, le tre concordano su un modello che sta in una
riga:

> una barra è **(x, y, dimensione, materiale)**, dove la dimensione è il
> diametro in `structuralcodes` e l'area in `concreteproperties` e in
> `sectionproperties`, e le due si convertono l'una nell'altra.

Tutto il resto — array rettangolari, array circolari, letti su una linea,
copriferro, esclusione degli angoli — è **zucchero costruito sopra quella
tupla**. È il fatto che decide §6.

---

## 4. Che cosa restituiscono

Il committente ha chiesto di separare ciò che serve a **descrivere**
l'armatura da ciò che serve a **calcolarci sopra**. La separazione è netta e
cade sempre nello stesso punto.

### 4.1 Descrivere

Ciò che si ottiene senza far girare nulla:

- la geometria composta, con le barre come regioni o punti distinti e
  ritrovabili;
- per ciascuna barra, coordinate, area e materiale;
- il raggruppamento per etichetta (`group_label` in `structuralcodes`);
- la classificazione automatica in calcestruzzo / armatura discretizzata /
  armatura concentrata / trefoli (`ConcreteSection` di `concreteproperties`);
- l'avviso di regioni sovrapposte.

Questo è **tutto** ciò che serve per «inserire le armature nelle sezioni
trasversali», ed è la parte che nessuna delle tre rende difficile.

### 4.2 Calcolare

**`sectionproperties`** offre `calculate_geometric_properties`,
`calculate_warping_properties`, `calculate_frame_properties`,
`calculate_plastic_properties`, `calculate_stress`, e una cinquantina di
accessori `get_*`: area, perimetro, massa, rigidezza assiale, momenti statici,
momenti d'inerzia geometrici e trasformati, moduli di resistenza elastici e
plastici, raggi d'inerzia, angolo degli assi principali, costante torsionale
`get_j`, centro di taglio `get_sc`, costante d'ingobbamento `get_gamma`, aree
di taglio `get_as`, moduli efficaci `get_e_eff`, `get_g_eff`, `get_nu_eff`.
È l'unica delle tre che dia **torsione e ingobbamento**, ed è il motivo per cui
esiste. [V]

**`concreteproperties`**, sulla classe `ConcreteSection`:
`calculate_gross_area_properties`, `calculate_cracked_properties`,
`calculate_cracking_moment`, `moment_curvature_analysis`,
`ultimate_bending_capacity`, `moment_interaction_diagram`,
`biaxial_bending_diagram`, e quattro calcoli di tensione — non fessurato,
fessurato, di esercizio, ultimo. I risultati sono classi proprie:
`GrossProperties`, `TransformedGrossProperties`, `CrackedResults`,
`MomentCurvatureResults`, `UltimateBendingResults`, `MomentInteractionResults`,
`BiaxialBendingResults`, `StressResult`, ciascuna con i propri
`print_results` e `plot_*`. [V]

**`structuralcodes`**, sulla classe `BeamSection` — che dalla 0.7.0 ha
sostituito `GenericSection`, il quale resta come guscio deprecato che emette un
`DeprecationWarning` [V] — attraverso il suo `BeamSectionCalculator`:
`calculate_bending_strength`, `calculate_moment_curvature`,
`calculate_nm_interaction_domain`, `calculate_nmm_interaction_domain`,
`calculate_mm_interaction_domain`, `calculate_strain_profile`,
`get_balanced_failure_strain`, `n_min`, `n_max`. Più
`calculate_elastic_cracked_properties`. [V]

### 4.3 La discretizzazione a fibre

Tutte e tre la producono, ma solo una la restituisce in una forma che si possa
prendere e portare via.

- **`sectionproperties`** mesha in triangoli a sei nodi (`Tri6`) e li espone
  come `section.elements`. Ogni elemento porta coordinate, identificativo e
  materiale.
- **`concreteproperties`** mesha in triangoli a tre nodi (`Tri3`), dentro
  `AnalysisSection`. Non c'è una funzione pubblica che li esporti.
- **`structuralcodes`** ha `FiberIntegrator.triangulate(geo, mesh_size)`, il cui
  tipo di ritorno è dichiarato nella firma:

      def triangulate(self, geo: CompoundGeometry, mesh_size: float
          ) -> t.List[t.Tuple[np.ndarray, np.ndarray, np.ndarray, ConstitutiveLaw]]

  cioè, per ogni regione, **(y, z, area, legge costitutiva) per ciascuna
  fibra**, con `mesh_size` espresso come frazione dell'area della regione
  (predefinito 0,01, cioè un centesimo). Il codice calcola il baricentro di
  ogni triangolo e la sua area con la formula di Gauss, e chiama `triangle`
  con la stringa di opzioni `pq30.0Aa<max_area>o1`. È una discretizzazione a
  fibre **riusabile così com'è**, e §5 ne fa il perno.

---

## 5. Il ponte verso OpenSees

### 5.1 Nessuna produce comandi OpenSees. Una produce comandi di un altro codice

Cercato in tutti i file `.py` distribuiti dai tre pacchetti: **nessuna
occorrenza di `section Fiber`, `patch`, `layer` nel senso di OpenSees**. [M]

L'unica che esporta comandi verso un solutore è `sectionproperties`, con il
modulo `sectionproperties.post.fibre`, e il solutore **non è OpenSees**. La
docstring del modulo lo dice in apertura, verbatim:

> «Provides functionalities to export a section to a fibre section. It can be
> used in `suanPan <https://github.com/TLCFEM/suanPan>`_ to perform further
> FEA.»

La firma della funzione:

    to_fibre_section(obj, *, main_section_tag=1, analysis_type="3DOS",
                     material_mapping=None, max_width=160, save_to=None) -> str

Produce righe della forma `section Cell3DOS <tag> <area> <omega> <py> <pz>
<materiale> <y> <z>`, oppure `Cell3D` senza le grandezze d'ingobbamento, oppure
`Cell2D` con la sola `y`. È la sintassi di suanPan. Il testo generato porta in
testa un commento che avverte, fra l'altro, «Beware of the potential different
orientations of beam section» e «It may be necessary to manually adjust the
material tags».

### 5.2 Quanto è corta la distanza, e da dove

La distanza è corta perché **il dato è lo stesso**. Una fibra di OpenSees è,
come riporta l'altra ricerca di questa cartella, «a UniaxialMaterial, an area
and a location (y,z)». Una `Cell3D` di `sectionproperties` è area, materiale,
`y`, `z`. Una tupla di `FiberIntegrator.triangulate` è `y`, `z`, area, legge
costitutiva. Sono la stessa cosa scritta tre volte.

Due vie praticabili, in ordine di preferenza. **Sono vie, non attuazioni: non
ho scritto né provato codice in questa sessione.** [INF]

1. **Da `structuralcodes`**: chiamare `FiberIntegrator.triangulate` e mappare
   ogni tupla su un comando `fiber(y, z, A, matTag)`. La corrispondenza è
   diretta, non c'è nulla da riformattare; l'unico lavoro è tradurre la legge
   costitutiva in un `uniaxialMaterial`, che è una tabella di scelte, non una
   conversione.
2. **Da `sectionproperties`**: chiamare `to_fibre_section` e riscrivere le
   righe `Cell3D` in righe `fiber`. Funziona ma passa da un formato di testo di
   un terzo solutore, che è un passaggio in più e un formato in più da tenere
   allineato.

**Ciò che nessuna delle due dà, e che va detto**: OpenSees distingue `patch`
(il calcestruzzo, generato a griglia dal solutore) da `layer` (le barre, posate
una per una) da `fiber` (la singola fibra esplicita). Queste librerie
producono **solo fibre esplicite**. Un ponte costruito così genera un
`section Fiber` fatto di sole `fiber`, mai di `patch` e `layer`. È più verboso
e perfettamente legittimo; ma se si vuole un deck che un lettore riconosca come
scritto a mano, `patch` e `layer` vanno generati dal modello parametrico
— larghezza, altezza, copriferro, numero di barre — che è un dato che
`wall.prior` già misura, non dalla mesh triangolare che questi pacchetti
producono.

Il resto del ponte — sintassi esatta dei comandi OpenSees, materiali
monoassiali disponibili, installabilità di `openseespy` su Windows e macOS
arm64 — sta in [`ricerca-opensees-e-armature.md`](ricerca-opensees-e-armature.md)
§2.1 e §4.4, e non lo ripeto qui.

---

## 6. Verdetto d'uso

### 6.1 La risposta è doppia, perché le domande sono due

**Per descrivere l'armatura: nessuna libreria, e il modello dei dati va scritto
in casa.** Il modello su cui tutte e tre convergono è, come misurato in §3.5,
la tupla `(x, y, diametro, materiale)` più il raggruppamento per letto. Sono
poche righe di `pydantic`, che questo repository già usa in `config.py` per ogni
altro parametro. Adottare `concreteproperties` per ottenerle significa
aggiungere sette pacchetti — fra cui `matplotlib`, `rich[jupyter]` e un
triangolatore in C con una nota di licenza proprietaria non risolta — per
un'astrazione che il progetto sa scrivere da sé in un pomeriggio. È il caso in
cui una dipendenza costa più di quello che risparmia.

Ciò che **va copiato invece che reinventato** sono tre decisioni di progetto,
tutte già prese bene da chi ci è passato prima:

1. **La firma di `add_reinforcement_line`** — due estremi, e *o* il numero di
   barre *o* il passo, con errore esplicito se non ci stanno e con `first` e
   `last` per non ripetere gli angoli. È la forma esatta che serve a un letto di
   barre lungo il contorno di una membratura misurata da `wall.prior`.
2. **La regola di `add_bar`** — la barra si sottrae al calcestruzzo prima di
   riaggiungersi, così il calcestruzzo non è contato due volte. Vale a
   prescindere dalla libreria.
3. **Il controllo di sovrapposizione** del costruttore di `ConcreteSection`,
   che avvisa invece di calcolare in silenzio su una geometria incoerente. In
   questo repository, dove `abaqus.footprint_coverage` è stata riscritta per
   sollevare invece di rendere un numero ambiguo, la scelta coerente è
   sollevare, non avvisare.

**Per calcolare sulla sezione armata: `structuralcodes`, se e quando serve.**
Le ragioni, in ordine:

- **Licenza Apache-2.0**, permissiva, contro la MIT delle altre due: pari
  merito. Ma `structuralcodes` la pubblica *fib International*, cioè l'ente che
  scrive il Model Code, e in una tesi la provenienza normativa di un modello
  vale quanto il modello.
- **Due dipendenze aggiunte contro sette.** `numpy` e `scipy` ci sono già;
  restano `shapely` e `triangle`.
- **È l'unica con l'Eurocodice.** `concreteproperties` porta AS 3600 e
  NZS 3101 e nessun codice europeo. Per una tesi italiana la differenza non è
  di gusto.
- **Il diametro è il dato d'ingresso**, e l'area la ricava lei. È il verso
  giusto: chi rileva un'armatura misura un diametro.
- **`FiberIntegrator.triangulate` restituisce le fibre in chiaro**, ed è il
  ponte verso OpenSees più corto che questa ricerca abbia trovato.

Contro, e da dichiarare: 94 issue aperte; l'API si muove ancora — il
rinominamento di `GenericSection` in `BeamSection` alla 0.7.0 è di questo
mese; e la sua dipendenza `triangle` non pubblica archivi di sorgente né ruote
oltre cp313, il che è indifferente a Python 3.12 e diventerebbe un muro dopo.

### 6.2 Le scartate, con la ragione in una riga

- **`concreteproperties`**: la più completa sul calcolo, ma sette dipendenze,
  nessun codice europeo, e il triangolatore con il requisito macOS 15.
  **Riapribile** se servisse il dominio di interazione biassiale o la
  precompressione, che `structuralcodes` copre meno.
- **`sectionproperties`**: entra comunque come dipendenza se si sceglie
  `concreteproperties`, e da sola serve solo se servono torsione e
  ingobbamento — che qui non servono.
- **`strupy`**: GPL virale, ferma al 2021, dipendenze non dichiarate,
  `pyautocad` su macOS non esiste. Chiusa dai fatti.
- **`PyCBA`, `anastruct`**: non modellano sezioni armate. Fuori tema.
- **`rcdesign`**: norma indiana IS 456. Fuori contesto normativo.
- **`eurocodepy`**: installa il proprio generatore di documentazione come
  dipendenza obbligatoria. Fuori per confezionamento.

### 6.3 Che cosa questa ricerca **non** decide

Resta aperto, e non lo decido io:

- se «inserire le armature» comprenda le **staffe**. Se sì, §3.4 dice che
  nessuna libreria le modella come geometria e che il modello va scritto
  comunque in casa; se no, la scelta si riduce a §6.1.
- se il programma debba **calcolare** sulla sezione armata o solo
  **descriverla**. Se la risposta è «solo descriverla», allora anche
  `structuralcodes` è di troppo, e la risposta secca alla domanda del
  committente diventa: **nessuna libreria**.
- il ponte verso OpenSees vero e proprio, che dipende dalle scelte dell'altra
  ricerca sui modelli a fibre e non da questa.

---

## 7. Riproducibilità

### 7.1 Come sono stati ottenuti i numeri

Tutto il §1.3, il §2 e il §3.4 sono misurati il 28/08/2026 su questa macchina,
non citati. Le tre vie:

- i metadati dei pacchetti, interrogando `https://pypi.org/pypi/<nome>/json` e
  `https://pypi.org/pypi/<nome>/<versione>/json` con `urllib.request`, e
  leggendo i campi `info.version`, `info.requires_python`, `info.requires_dist`,
  `info.classifiers`, e la lista `urls` per i file pubblicati;
- lo stato dei repository, interrogando `https://api.github.com/repos/<owner>/<nome>`
  e leggendo `stargazers_count`, `open_issues_count`, `pushed_at`, `license`,
  `archived`;
- il contenuto dei pacchetti, scaricando le ruote e l'archivio di `strupy`,
  estraendoli, e leggendo i file `.py` distribuiti.

La versione di glibc di questa macchina, 2.43, viene da `ldd --version`.

### 7.2 Che cosa non ho verificato

- **Non ho installato nulla.** Non c'è `pip` in questo ambiente e la `.venv`
  del repository è una virtualenv Windows. Tutte le affermazioni di
  installabilità sono lette dai **file pubblicati**, non da un'installazione
  riuscita. È una differenza reale: una ruota può esistere e non risolversi per
  un conflitto fra vincoli.
- **Non ho eseguito una sola riga di queste librerie.** Le firme sono lette,
  non chiamate. Un valore predefinito riportato è quello scritto nel file.
- **Non ho aperto la licenza originale del *Triangle* di Shewchuk**, e §2.2 lo
  dichiara: riporto che il classificatore proprietario esiste, non che cosa
  dica il testo a monte.
- **Non ho ispezionato il sorgente di `eurocodepy`, `rcdesign`, `PyCBA`,
  `anastruct`**: per queste ho letto solo i metadati PyPI e, dove c'era, la
  scheda del repository. Le righe che le riguardano in §1.1 sono di quel grado
  di verifica e non di più.
- **Non ho risolto la discordanza di licenza di `anastruct`** fra PyPI e
  GitHub.
- Le versioni si muovono. Ogni numero di versione di questo documento è quello
  corrente al 28/08/2026: `sectionproperties` 3.10.2, `concreteproperties`
  0.8.0, `structuralcodes` 0.7.1, `cytriangle` 3.0.2, `triangle` 20250106.
  Prima di consegnare, riverificare almeno i requisiti di piattaforma di
  `cytriangle`, che sono cambiati due volte in diciotto mesi.
