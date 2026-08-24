# MeshRec Fase 6 — Carichi posizionati su una mesh senza topologia

- **Data:** 22 agosto 2026
- **Stato:** design approvato in sessione di brainstorming
- **Dipende da:** Fase 5 chiusa e fusa (risoluzione con CalculiX, `meshrec/docs/fase-5-analisi.md`).
- **Mappa di charting:** [Fase 6 — carichi posizionati su una mesh senza topologia](https://github.com/maeurong/Tesi/issues/4).
  Quattro ticket chiusi ne alimentano le decisioni: [#5](https://github.com/maeurong/Tesi/issues/5) (TRVEC),
  [#6](https://github.com/maeurong/Tesi/issues/6) (forma del selettore),
  [#7](https://github.com/maeurong/Tesi/issues/7) (ingressi degeneri),
  [#8](https://github.com/maeurong/Tesi/issues/8) (impronta di sweep, già in codice: `911f15f`).
  Questa spec chiude anche [#9](https://github.com/maeurong/Tesi/issues/9) (ripartizione)
  e [#11](https://github.com/maeurong/Tesi/issues/11) (taglio).
- **Documento di esito collegato:** `meshrec/docs/fase-6-carichi.md`, da scrivere alla chiusura.

Ogni numero di questa spec dichiara il file e il campo da cui viene, ed è stato
letto il 22 agosto 2026 nella sessione che l'ha scritta.

---

## 1. Il problema, in una riga

Un as-built da scansione non ha topologia: nessuna faccia nominata, nessuno
spigolo da referenziare. Non si può dire «sulla trave superiore», perché quella
trave il programma non ce l'ha — `runs/lab_telaio_v2/12_wall.json` dichiara
`regioni_trovate: 8` e `membrature: 0`.

Gli unici indirizzi che il deck contiene oggi sono i sei `*NSET` che
`core/abaqus.py:741` `build_node_sets` **ricalcola dalle coordinate a ogni
esportazione** (`BASE`, `TOP`, `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`,
`SIDE_RIGHT`, righe 765-771). Non li memorizza. Una lista di indici di nodo non è
quindi un indirizzo durevole: un remesh la fa puntare altrove in silenzio.

La Fase 6 introduce l'indirizzo durevole: una **regola geometrica dichiarata**,
che vive nella configurazione, si diffa, e sopravvive al remesh perché viene
risolta di nuovo ogni volta.

### 1.1 Vocabolario

«Regione» è già preso: `core/wall.py:185` `regioni()` sono le regioni a spessore
quasi costante del prior. Quindi:

- **selettore** — la *regola* dichiarata (box, sfera, nodo più vicino, nset esistente).
- **nset** — il *risultato*, i nodi che la regola ha preso. Termine già del dominio.
- **`carichi.posizionati`** — il nome del blocco. Non «manuali»: anche `spinta`,
  `carico_sommita` e `modale` sono dichiarati a mano dall'operatore
  (`core/config.py:648`). La differenza vera è che i posizionati **portano con sé
  il proprio selettore**.

---

## 2. Il perimetro

### 2.1 Dentro

1. Blocco `selettori:` alla radice della configurazione, quattro forme.
2. Validazione degli ingressi degeneri, divisa fra prima e dopo la mesh.
3. Risoluzione del selettore in nodi, con resoconto sempre scritto.
4. `carichi.posizionati`: forza concentrata e momento come coppia di forze.
5. Ripartizione **pesata per area tributaria**, sui posizionati e su
   `carico_sommita`, con rimisura e ripubblicazione dei numeri della Fase 5.
6. `selettori` dentro l'impronta di sweep e dentro i blocchi dello step 11.
7. Documento di fase `meshrec/docs/fase-6-carichi.md`, con lo script committato
   che porta gli `assert` contro i valori pubblicati.

### 2.2 Fuori, e in quest'ordine tornano

| # | cantiere | perché fuori |
|---|---|---|
| 1 | distribuito `P` sull'as-built ([#10](https://github.com/maeurong/Tesi/issues/10)) | richiede di aprire `element_surfaces` sul percorso as-built (`core/pipeline.py:439-448` non lo passa) e una decisione di prodotto in più, ereditata dalla caduta di `TRVEC` |
| 2 | guardie sul modello mal vincolato ([#12](https://github.com/maeurong/Tesi/issues/12)) | parte «verifica» della destinazione, ma indipendente dai posizionati |
| 3 | selezione col mouse | `ui/viewport.js:208` fa solo orbita, nessun raycast esiste; `app/server.py:817` butta gli `indici` che `_contorno_del_volume` gli restituisce (`app/server.py:128`) |
| 4 | vista deformata | endpoint vettoriale, più il rifiuto delle chiavi assenti da `point_data` che `app/server.py:894` già fa per gli scalari |
| 5 | round-trip dello YAML | `save_config` è chiamato **32 volte in 11 file** (misurato in sessione, `def` esclusa) e `ruamel` non compare in `pyproject.toml`, che per lo YAML dichiara `pyyaml>=6.0` alla riga 15 |

### 2.3 Cosa la Fase 6 dichiara di non fare

Il documento di esito lo scrive, invece di lasciarlo intendere:

- **non ricostruisce topologia.** Nessuna faccia nominata, nessuno spigolo, nessuna
  membratura. Il selettore prende nodi per criterio geometrico, e basta.
- **non applica alcun carico distribuito sull'as-built.** Né `P` né direzionale.
  `ccx` 2.22 rifiuta `TRVEC` con errore fatale (misurato, [#5](https://github.com/maeurong/Tesi/issues/5)),
  e `P` richiede il cantiere 1 della coda.
- **non identifica fisicamente le facce.** I nomi `FACE_FRONT`, `SIDE_LEFT` e
  compagni restano nomi di convenzione, come `build_node_sets` già dichiara nel
  proprio docstring (`core/abaqus.py:750-759`).
- **non scrive momenti concentrati.** Un `*CLOAD` sui gradi 4-6 su un C3D4 è
  scartato in silenzio: si veda § 5.
- **non combina due posizionati in un passo solo.** Ogni carico dichiarato è un
  passo statico a sé, col solo peso proprio accanto. Lo schema non ha modo di
  chiedere una combinazione, e la Fase 6 non gliene aggiunge uno.

---

## 3. Il selettore

### 3.1 Forma: elenco nominato alla radice

Deciso in [#6](https://github.com/maeurong/Tesi/issues/6) misurando due
frammenti risolti sui **14 103 nodi** di `runs/lab_telaio_v2` (`metrics.json`,
`09_tetrahedralize.nodes`; 51 913 tetraedri nello stesso campo `tets`). Due
carichi sullo stesso posto danno 212 nodi sia con il selettore annidato in ogni
carico sia con quello nominato alla radice. Dopo la mutazione «la piastra scende
di 50 mm», corretta in un punto solo, la forma annidata dà **69 e 212** — la
coppia si spezza in silenzio — mentre quella nominata dà **69 e 69**.

L'argomento che regge: anche la forma annidata un nome nel deck lo scrive
(`SEL_<carico>`, fabbricato). La scelta non aggiunge uno spazio di nomi, lo rende
dichiarato invece che derivato.

```yaml
selettori:
  piastra:
    tipo: box
    min: [1200.0, 300.0, 1700.0]
    max: [1500.0, 600.0, 1800.0]
  angolo:
    tipo: sfera
    centro: [0.0, 0.0, 1799.0]
    raggio: 120.0
  punta:
    tipo: nodo
    punto: [2698.0, 875.0, 1799.0]
  appoggio:
    tipo: nset
    nome: BASE

carichi:
  posizionati:
    - nome: PRESSA
      selettore: piastra
      forza: [0.0, 0.0, -12000.0]      # N, risultante ripartita sui nodi presi
    - nome: TORSIONE
      selettore: piastra
      momento:
        asse: [0.0, 0.0, 1.0]
        modulo: 4500000.0              # N·mm
        braccio: 400.0                 # mm, dichiarato e verificato: § 5
```

Un carico dichiara **o** `forza` **o** `momento`, mai entrambi e mai nessuno dei
due: due carichi sullo stesso selettore si dichiarano come due voci, che è già la
forma che il blocco ha.

Ogni posizionato è **un passo statico a sé**, e come i due casi esistenti porta
con sé il peso proprio: `core/abaqus.py:222` scrive
`passo_statico("CARICO_TOP", [peso] + righe_cload)`, e un carico senza peso
descriverebbe una struttura che non pesa. Due posizionati **non** si sommano in un
passo solo, e lo schema non ha modo di chiederlo: è un limite dichiarato della
Fase 6, che il documento di esito scrive al § 2.3. La combinazione di più
posizionati in un unico passo torna con la coda, se una misura la chiede.

Il nome del carico diventa il nome del passo nel deck, e non può collidere con
`NOMI_PASSO_RISERVATI` (`core/config.py:261`: `SPINTA_ORIZZONTALE`, `CARICO_TOP`,
`MODALE`) né con `analysis.step_name`. Il controllo esiste già per il passo di
peso proprio (`core/config.py:290`) e si estende.

Il nome del selettore diventa il nome dell'`*NSET` nel deck. Rifiutato il
prefisso `SEL_`, che rimetterebbe in piedi il nome fabbricato tolto di mezzo
dalla #6.

### 3.2 Validazione: due gruppi, e la spaccatura è la decisione

Cinque ingressi diversi danno oggi lo stesso identico sintomo: `min > max`, box
piatta, box fuori dai bounds, `raggio: 0` e `raggio: -5` risolvono **tutti zero
nodi** sui 14 103. Un oracolo unico a valle non potrebbe dire quale sia successo
([#7](https://github.com/maeurong/Tesi/issues/7)).

**A monte, a validazione della configurazione, senza mesh:**

| condizione | oracolo |
|---|---|
| `min > max` su una componente qualsiasi | solleva, e nomina la componente |
| `raggio <= 0` | solleva |
| nome di selettore uguale a uno dei sei di `core/abaqus.py:765-771` | solleva, e nomina il set che collide |
| carico che cita un selettore non dichiarato | solleva, e nomina il selettore |
| due chiavi YAML omonime sotto `selettori:` | solleva (oggi `safe_load` tiene l'ultima in silenzio: la prima sparisce) |
| nome di carico riservato o uguale a `analysis.step_name` | solleva |
| selettore dichiarato e mai citato | **non** è un errore |

Il controllo di `core/abaqus.py:213-218` — il carico in sommità che nomina un
insieme assente o vuoto — sale a monte per la parte che non ha bisogno della
mesh.

Il rifiuto delle chiavi omonime costa un `SafeLoader` sottoclassato, che
sovrascrive `construct_mapping` e solleva invece di tenere l'ultima. Va messo
**in un punto solo** e usato da entrambe le `yaml.safe_load` del modulo:
`core/config.py:686` (`load_config`, la configurazione della pipeline) e
`core/config.py:768` (`ExperimentConfig`). Passarlo solo alla prima lascerebbe la
seconda a perdere una chiave in silenzio — è la stessa falla, e patchare il solo
percorso che il ticket nomina la lascerebbe aperta sull'altro.

**A valle, con la mesh risolta:**

| condizione | oracolo |
|---|---|
| il selettore prende **0 nodi** | solleva, e riporta la bbox del selettore accanto a quella della mesh |
| il selettore prende **tutti** i nodi | solleva: 0,85 N a nodo non è un posizionato, è un peso proprio storto |
| `tipo: nodo` col nodo più vicino oltre **3 spigoli medi** | solleva. Su questa mesh lo spigolo medio è 32,82 mm, quindi la soglia è 98,5 mm; il caso degenere misurato cadeva a 9 979,9 mm, il punto legittimo a 32,17 mm |
| area tributaria totale nulla (§ 4) | solleva |

Fra 1 e 14 103 nodi nessuna soglia può giudicare: si può solo mostrare. Perciò il
conteggio nodi-per-selettore **si scrive sempre**, anche quando passa (§ 6).

---

## 4. La ripartizione pesata per area

### 4.1 La decisione

Oggi la ripartizione è uniforme per nodo: `core/abaqus.py:220` scrive
`per_nodo = sommita.risultante / len(nodi_carico)`. Il docstring di
`CaricoSommita` (`core/config.py:231-238`) lo dichiara già come limite noto — *«la
ripartizione è uniforme per nodo, quindi il carico si concentra dove i nodi sono
più fitti»*.

La Fase 6 passa alla **pesatura per area tributaria**, e ci passa **anche
`carico_sommita`**: una sola ripartizione nel programma, nessuna incoerenza da
motivare fra due carichi che fanno la stessa cosa.

### 4.2 Come si calcola

`core/abaqus.py:440` `surface_area` somma le aree faccia per faccia in **uno
scalare**. Serve la funzione gemella, accanto e non al posto: stesso ciclo, stesse
tabelle `FACCE_DEL_SOLUTORE` e `_ANGOLI_PER_COLONNE`, stesso ventaglio dal primo
nodo, ma l'accumulo va in un array indicizzato per nodo. Un terzo dell'area di
ogni triangolo a ciascuno dei suoi tre nodi.

Le facce su cui si somma sono quelle di **bordo** — `core/abaqus.py:468`
`boundary_faces` esiste già e generalizza sui nodi d'angolo — **interamente
contenute** nel nset del selettore. Non servono `element_surfaces` nel deck:
`runs/lab_telaio_v2/metrics.json` mostra `"element_surfaces": {}` e
`"surface_area": {}` sul percorso as-built, e la Fase 6 non li apre. Il calcolo è
interno.

Regole, e ognuna ha il proprio oracolo:

- Le forze sono **normalizzate** perché la loro somma sia esattamente la
  risultante dichiarata. La verifica è un `assert` sul deck scritto, non una fede.
- Un nodo con area tributaria nulla — dentro il nset ma non toccato da alcuna
  faccia di bordo interamente contenuta — prende **0** e il resoconto **lo conta**.
  La risultante resta esatta perché la normalizzazione è sul totale.
- Area tributaria totale nulla — nessuna faccia interamente contenuta, per
  esempio un selettore tutto interno al solido — **solleva**. È l'unico caso in cui
  la pesatura non ha nulla su cui pesare, e scrivere zero ovunque sarebbe un
  carico applicato a nulla.

### 4.3 Il costo, dichiarato

I numeri `CARICO_TOP` pubblicati dalla Fase 5 su `runs/lab_telaio_v2` **cambiano**.
Quelli da rimisurare e ripubblicare, con la riga in cui stanno oggi:

| valore pubblicato | dove | oggi |
|---|---|---|
| picco di von Mises | `docs/fase-5-analisi.md:305` | 0,98 MPa |
| riga della tabella dei casi | `docs/fase-5-analisi.md:438` | 0,064273 / 0,0827 / 0,3923 / 0,9811 / 2,501 |
| forma del `*CLOAD` | `docs/fase-5-analisi.md:578` | 3.036 righe, ciascuna −0,395257 N |

Il conteggio regge, e chiude su tre file letti in sessione:
`runs/lab_telaio_v2/config.yaml:77` dichiara `risultante: 1200.0` su `nset: TOP`;
`runs/lab_telaio_v2/metrics.json`, campo `11_export.node_sets.TOP`, vale **3036**;
1200 / 3036 = 0,395257 N, che è il valore pubblicato. Dopo la pesatura le righe
restano 3.036 ma i valori diventano diversi fra loro, e il picco si sposta.

Un task del piano di implementazione rimisura eseguendo, aggiorna le tre righe e
aggiunge la nota che spiega perché sono cambiate. `SPINTA_ORIZZONTALE`, `GRAVITA`
e `MODALE` non toccano questa ripartizione e non cambiano.

---

## 5. Il momento: coppia di forze, braccio dichiarato

### 5.1 Perché non un `*CLOAD` sui gradi 4-6

Misurato su un deck di sonda minimo dato a `ccx` 2.22 su questa macchina arm64: un
momento concentrato su un elemento solido C3D4 è **scartato in silenzio**. Zero
occorrenze di `warning` o `error`, `number of equations 3`, spostamento
`0.000000E+00` su tutte e tre le componenti. La guardia di `core/solve.py:438` —
«zero `*WARNING` da ccx o i numeri non sono citabili» — non lo intercetta, perché
non c'è nessun warning da intercettare.

Il momento si realizza quindi come **coppia di forze staticamente equivalente**,
scritta con le stesse card `*CLOAD` del carico concentrato.

### 5.2 Il braccio lo dichiara l'operatore, il programma lo contraddice

Due vie erano aperte: il programma misura il braccio sull'estensione reale dei
nodi presi, oppure l'operatore lo dichiara e il programma verifica. Vince la
seconda, per il principio 1 di `PRODUCT.md` — *un numero mostrato senza un
controllo che lo smentisca non vale più di un numero assente*. La prima non chiede
nulla ma decide da sé, e nessuno la può contraddire.

Il controllo: proiettati i nodi del selettore sul piano perpendicolare all'`asse`
dichiarato, la loro estensione lungo la direzione della coppia deve **sostenere**
il braccio. Se il braccio dichiarato supera l'estensione disponibile, si solleva e
si riportano entrambi i numeri — dichiarato e misurato — perché l'operatore possa
correggere il dato giusto.

La coppia si costruisce su due sottoinsiemi del nset, quello oltre `+braccio/2` e
quello oltre `−braccio/2` lungo la direzione scelta, e dentro ciascuno la forza
si ripartisce per area come al § 4. Se un lato resta senza nodi si solleva: una
coppia con una forza sola è una forza.

**Il momento realizzato è esattamente quello dichiarato.** I due sottoinsiemi
raccolgono nodi *oltre* `±braccio/2`, quindi i loro baricentri pesati distano fra
loro più del braccio dichiarato. È il **braccio effettivo**, e la forza si calibra
su di esso — `modulo / braccio_effettivo` — invece di restare `modulo / braccio`.
Così il `braccio` dichiarato conserva il solo ruolo che gli compete, scegliere i
due gruppi, e il `modulo` dichiarato non si scosta di nascosto da quello che il
deck applica. Il resoconto scrive entrambi i bracci accanto al momento, perché
la differenza fra i due è una cosa da guardare, non da nascondere.

---

## 6. Impronta, step e resoconto

### 6.1 `selettori` entra nell'impronta

`core/steps.py:65` dichiara `STEP_BLOCKS[11] = ("tet", "analysis", "carichi")`, e
`core/sweep.py:64` dichiara `BLOCCHI_VUOTI_FUORI_IMPRONTA = ("carichi",)`.

Il nuovo blocco `selettori` va aggiunto a **entrambi**, con la stessa regola
«omesso quando vuoto» già scelta in [#8](https://github.com/maeurong/Tesi/issues/8)
e implementata in `911f15f`. Senza l'aggiunta a `STEP_BLOCKS[11]`, cambiare un
selettore non invalida lo step 11 e il deck resta quello vecchio in silenzio;
senza l'aggiunta a `BLOCCHI_VUOTI_FUORI_IMPRONTA`, due candidati con selettori
diversi calcolano la stessa impronta e scrivono nella stessa cartella
(`core/sweep.py:677`, `root / fingerprint(item[1])[:12]`).

La regola «omesso quando vuoto» è la stessa e per la stessa ragione: le 22 righe
di `experiments/muro/` e `experiments/lab_crop/` non hanno un blocco `selettori`,
e la loro impronta non deve cambiare.

### 6.2 Il resoconto sta dove stanno già gli altri

Nessun file nuovo. `metrics["11_export"]` porta già `node_sets`,
`element_surfaces`, `surface_area`, `pressure` e `casi_di_carico` — letti in
`runs/lab_telaio_v2/metrics.json`. Si aggiungono due chiavi:

- **`selettori`**: per ciascuno, tipo, nodi risolti, bbox reale dei nodi presi.
  Sempre, anche quando passa.
- **`carichi_posizionati`**: per ciascuno, risultante dichiarata, somma effettiva
  delle forze scritte nel deck, numero di nodi ad area tributaria nulla, e — per i
  momenti — braccio dichiarato, braccio effettivo, momento effettivo.

Il precedente comportamentale è `app/server.py:617` `/api/cluster`: il server
calcola, scrive, e **risponde dicendo cosa ha scelto e con quali numeri**.

---

## 7. Test

Ogni test nuovo dichiara nel proprio docstring la mutazione che lo uccide, e il
piano di implementazione la **applica davvero** per verificare che il test
fallisca nel modo giusto.

Copertura minima, un test per riga della tabella degli ingressi degeneri del § 3.2,
più:

- la ripartizione pesata su una geometria a densità di nodi volutamente
  disomogenea, dove uniforme e pesata danno risultati distinguibili;
- la somma delle forze scritte nel deck uguale alla risultante dichiarata, entro
  la tolleranza di scrittura in ascii;
- il round-trip `model_validate` → `model_dump` del blocco `selettori`, con
  l'impronta immutata sulle 22 righe dei registri esistenti;
- il deck con un carico posizionato dato a `ccx` vero, che esce 0, non stampa
  warning e produce spostamenti non nulli — la sonda che la Fase 5 ha imparato a
  chiedere.

Baseline da non far scendere: **726 passed in 103,89 s**, misurata su questo
branch a `a4fefc7` con `uv run pytest tests -q --ignore=tests/feasibility`,
uscita 0. (Il 723 della mappa è il numero su `main`, prima dei tre test che
`911f15f` ha aggiunto.) Più 11 passed e 1 skipped con `-m feasibility`.

---

## 8. Vincoli di lavoro

- Sola lettura: `runs/muro/`, `runs/lab_crop/`, `experiments/muro/`,
  `experiments/lab_crop/`. Mai `git add -A`.
- Niente numeri del provino di laboratorio in `src/`.
- Il server **riscrive `config.yaml`** (`core/config.py:689-693`, `safe_dump` del
  modello alla riga 693): dopo averlo avviato, controllare `git diff` dello YAML
  prima di misurare qualunque cosa.
- Un brief che afferma qualcosa sul codice cita `file.ext:riga` letto nella
  sessione corrente.

---

## 9. Documento di esito

Alla chiusura, `meshrec/docs/fase-6-carichi.md`, sul modello della Fase 5: ogni
numero col file e il campo da cui viene, più uno script committato con gli
`assert` contro i valori pubblicati — il modello è
`docs/fase-5-cantiere/misura-deficit.py`.

Il documento riporta il § 2.3 per intero: questo repo è privato, e una issue non
si cita in una tesi.
