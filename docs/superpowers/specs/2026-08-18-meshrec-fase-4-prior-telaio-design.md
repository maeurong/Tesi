# MeshRec Fase 4 — Prior geometrico del telaio e modelli parametrici

- **Data:** 18 agosto 2026
- **Stato:** design approvato in sessione di brainstorming
- **Dipende da:** Fase 1 completa. Non dipende dalla Fase 2 né dalla Fase 3, ma
  le usa entrambe: il registro degli esperimenti resta dov'è, e l'interfaccia
  cresce di uno step.
- **Spec di riferimento:**
  [`2026-08-12-meshreconstructor-architettura-design.md`](2026-08-12-meshreconstructor-architettura-design.md)
  § 6, «Fase 4 — prior geometrico "muro"»
- **Documento di esito collegato:**
  [`fase-4-materiale.md`](../../../meshrec/docs/fase-4-materiale.md)

---

## 1. Perché questa fase cambia nome

La spec di architettura la chiamava «prior geometrico *muro*» e la descriveva
così: «un muro è una lastra piana, e questa informazione a priori consente
operazioni che una pipeline generica non può fare».

La premessa è falsa sul caso studio, e la falsità è stata misurata all'apertura
di questa fase, non ipotizzata. Il provino `lab_frame.pcd` non è una lastra: la
tavola esecutiva `muro_1.pdf` (`MURO 1`, obra 0021, novembre 2021, ing. José A.
Barros Cabezas) lo descrive come un **telaio in cemento armato** di sei
membrature prismatiche, e le misure sulla nuvola concordano con la tavola.

| membratura | sezione [mm] | lunghezza [mm] | n. | riscontro sulla nuvola |
|---|---|---|---|---|
| Zapata | 700 × 250 | 700 | 2 | estensione trasversale ~730 mm sotto z ≈ −470 |
| Viga inferior | 250 × 250 | 1300 | 1 | fascia ~278 mm al centro, sotto z ≈ −500 |
| Columna | 172 × 172 | 1695 | 2 | ~200 mm sui percentili grezzi, 176 mm misurati sul posto |
| Viga superior | 140 × 175 | 2090 | 1 | corpo continuo da z ≈ +900 |

Fuori tutto 2700 × 1945 mm; volume di calcestruzzo dichiarato in tavola
**0,4777 m³**. La `PARED` — il tamponamento in blocchi, spesso 90 mm — non entra
nel modello per decisione dell'autore, ed è comunque assente dal provino
scansionato: nella campata centrale la nuvola non ha punti fra z = −450 e
z = +850 mm.

Il prior giusto non è dunque «due piani paralleli e uno spessore», che
schiaccerebbe quattro sezioni diverse in una. È **telaio di membrature
prismatiche**: ogni membratura ha una propria sezione costante lungo un proprio
asse.

La sostanza della fase non cambia: adattamento di forme regolari alla geometria
rilevata, misura del fuori piombo e del rigonfiamento, un secondo e un terzo modo
d'uscita con mesh esaedrica, e il confronto fra modelli a parità di nuvola.
Cambia la forma del prior, e cambia in meglio una cosa: **la tavola è una verità
di riferimento**, e ogni misura ha ora qualcosa con cui essere contraddetta.

### 1.1 Il guadagno secondario, già incassato

L'apertura di questa fase ha trovato un difetto già presente: le configurazioni
di `lab_frame` dichiaravano il materiale `MURATURA` a 1500 MPa, ereditato in
silenzio dai valori predefiniti di `config.Material`, su un provino in cemento
armato. La correzione è stata fatta subito ed è documentata in
[`fase-4-materiale.md`](../../../meshrec/docs/fase-4-materiale.md): il materiale
non ha più predefiniti, `meshrec init` lo chiede sulla riga di comando, e le
corse di riferimento conservano il materiale con cui sono state davvero eseguite,
perché riscriverle falsificherebbe la provenienza.

**Norma di progetto che ne discende:** la classe e i parametri meccanici del
materiale sono una decisione di chi analizza. Il programma non li deduce dalla
nuvola, non li ricava dalla tavola, non li supplisce con un predefinito.

---

## 2. Che cosa consegna la fase

1. Il **prior**: scomposizione della nuvola in membrature prismatiche, con
   sezione, asse, lunghezza, fuori piombo e mappa di rigonfiamento per ciascuna.
2. **Tre modelli** dello stesso pezzo, a parità di nuvola:
   - **as-built** — la superficie rilevata, mesh tetraedrica (esiste già);
   - **estruso** — sezione misurata e asse misurato, mesh esaedrica;
   - **primitive** — sezione rettangolare e asse ideale, mesh esaedrica.
3. Il **deck** `.inp` di ciascun modello, con `*SURFACE, TYPE=ELEMENT` — debito
   rinviato dalla Fase 1 — e carico laterale opzionale.
4. Il **confronto geometrico** fra i modelli generati, nel report e
   nell'interfaccia.

**Confine dichiarato:** nessun solutore. La risposta strutturale è la Fase 5, che
ha già CalculiX in batch in programma. Qui CalculiX compare in un solo ruolo, e
minore: verificare che un deck sia leggibile.

**Fuori ambito, per decisione dell'autore:** l'armatura. La tavola quota tutte le
barre e le staffe, quindi il dato esiste e resta disponibile; il modello di
questa fase è calcestruzzo omogeneo. Va scritto nel report, perché un telaio in
c.a. modellato senza armatura non è il telaio vero, ed è una scelta, non una
dimenticanza.

---

## 3. Architettura

### 3.1 I modelli parametrici sono corse figlie, non rami

`pipeline.run()` è oggi una sequenza lineare di undici blocchi in una sola
funzione. Biforcarla su tre modelli raddoppierebbe la complessità della funzione
più delicata del progetto e non risparmierebbe nulla: i tre modelli vanno
comunque eseguiti tre volte.

I due modelli parametrici sono **generatori di mesh di volume alternativi a
TetGen**. Producono nodi ed elementi e rientrano negli step esistenti di metriche
di volume ed esportazione. Ogni modello è la propria cartella
`runs/<nome>-estruso/` e `runs/<nome>-primitive/`, con configurazione completa,
artefatti, metriche e riga di registro proprie.

`pipeline.run()` cresce di **un solo blocco**, lo step 12, che calcola il prior.

Scartate: la biforcazione dentro `run()`, per la ragione detta; e l'uso del
motore di sweep come contenitore dei tre modelli, perché lo sweep esiste per
scegliere per dominanza di Pareto fra configurazioni della stessa pipeline,
mentre qui i tre modelli non competono, si confrontano — piegarlo renderebbe
bugiardo il registro degli esperimenti, che è la tabella sperimentale della tesi.

### 3.2 Moduli

| modulo | responsabilità | dipende da |
|---|---|---|
| `core/wall.py` (nuovo) | il prior: scomposizione, sezioni, assi, fuori piombo, rigonfiamento. Nessuna mesh, nessun file: solo misura | `segment`, `numpy` |
| `core/hexa.py` (nuovo) | i due modelli parametrici: sagoma, ricombinazione in quadrilateri, estrusione, esaedri | `gmsh` (già dipendenza), `wall` |
| `core/abaqus.py` (esteso) | esportazione per tipo di elemento, superfici di elemento, `*TIE`, carico laterale | — |
| `core/quality.py` (esteso) | metriche di volume per esaedri (Jacobiano scalato) accanto a quelle per tetraedri | — |
| `core/viewport.py` (esteso) | disegno della mesh esaedrica, colore per membratura, campo di rigonfiamento | — |
| `core/report.py` (esteso) | sezione del prior e tabella di confronto | — |
| `cli.py`, `app/server.py` | comando `wall` e step 12 nell'interfaccia | — |

Il criterio di ripartizione: `wall.py` misura e non costruisce; `hexa.py`
costruisce e non misura. Ognuno dei due è verificabile da solo contro una
geometria di verità nota.

---

## 4. Il prior

### 4.1 La scomposizione, senza soglie tarate a mano

Separare le membrature con una soglia di quota (`z < −470`) sarebbe tarare una
costante sulla scansione di oggi. Il secondo principio del progetto dice il
contrario: la grandezza da sorvegliare si sceglie prima della soglia, e una
soglia difficile da tarare è il sintomo di una grandezza sbagliata.

La grandezza giusta qui è lo **spessore locale**, e la regola è la sua
**costanza**, non il suo valore:

1. Sul piano del telaio si accende la griglia di celle quadrate già usata in
   Fase 1 per la copertura per colonne — non è un metodo nuovo.
2. Per ogni cella si misura l'estensione della nuvola in direzione trasversale:
   è lo spessore locale.
3. L'istogramma degli spessori ha modi netti — le misure d'apertura li trovano a
   ~200, ~280 e ~730 mm, cioè colonna, viga inferior e zapata.
4. Le membrature sono le **regioni connesse a spessore quasi costante**.
5. Il pavimento non è una membratura: è un piano quasi orizzontale esteso oltre
   l'ingombro del pezzo, e viene scartato come tale.

Nessun numero tarato su `lab_frame` entra nel codice. La stessa procedura, su
`muro_generato.ply`, deve trovare **una** regione sola: è la prova che non
inventa membrature dove non ce ne sono.

### 4.2 Che cosa misura, per membratura

- **asse** — direzione principale della regione;
- **lunghezza** lungo l'asse;
- **sezione** — le due estensioni trasversali, con la loro dispersione;
- **fuori piombo** — angolo dell'asse rispetto alla verticale, un numero solo;
- **rigonfiamento** — scostamento locale dalla faccia ideale, che è una mappa e
  non un numero.

Le ultime due sono tenute distinte perché sono difetti diversi: un elemento può
essere perfettamente piano e tutto storto, oppure a piombo e panciuto.

### 4.3 I controlli che possono smentire il prior

Senza questi il prior è una macchina per fabbricare numeri.

| controllo | criterio | esito se fallisce |
|---|---|---|
| numero di membrature | 6 su `lab_frame`, 1 su `muro_generato` | la corsa si ferma e dice quante ne ha trovate |
| sezione | contro il nominale di tavola (172×172, 250×250, 140×175, 700×250) | scarto riportato, non nascosto |
| volume | contro i 0,4777 m³ di tavola | scarto riportato |
| parallelismo delle facce | angolo entro una soglia dichiarata | il prior si rifiuta invece di dare una sezione media priva di senso |
| copertura per faccia | frazione di area vista dallo scanner sopra una soglia dichiarata | il prior si rifiuta: una faccia vista da pochi punti produce un piano finto. È la lezione già pagata su `FACE_FRONT`/`FACE_BACK` |

### 4.4 Il piede del modello è un taglio, non una faccia

Le zapatas poggiano sul pavimento, e il pavimento viene scartato. La base del
modello è quindi una **quota di taglio scelta dall'operatore**, esattamente come
il ritaglio di oggi, e il set `BASE` nasce lì. Il report deve dirlo a lettere
chiare: quella superficie non esiste nel pezzo vero, è dove abbiamo tagliato.

**Ricaduta pratica:** serve un ritaglio nuovo, che scenda al pavimento e si
allarghi trasversalmente fino a comprendere le zapatas. Le corse `lab_crop`
attuali restano valide per ciò che sono — il solo telaio sopra le zapatas — e non
vengono toccate.

---

## 5. I tre modelli

| modello | sezione | asse | elemento |
|---|---|---|---|
| **as-built** | superficie reale dal Poisson | — | `C3D4` / `C3D10` |
| **estruso** | contorno di sezione **misurato** | misurato, fuori piombo conservato | `C3D8I` |
| **primitive** | rettangolo dai valori **misurati** | ideale, dritto e a piombo | `C3D8I` |

I due parametrici sono entrambi sei prismi. Cambia se la sezione conserva la
forma rilevata o diventa un rettangolo, e se l'asse conserva il fuori piombo
misurato o è dritto. Il confronto separa così due effetti diversi — irregolarità
della sezione, e fuori piombo — invece di sommarli in un unico salto.

Le sezioni dei modelli parametrici sono **misurate sulla nuvola**, non prese
dalla tavola. Prenderle dalla tavola farebbe misurare al confronto anche lo
scarto fra progetto e costruito, che è un'altra domanda. La tavola resta il
riferimento con cui contraddire, non la fonte del modello.

### 5.1 Il tipo di elemento

Predefinito `C3D8I`, con `C3D8` e `C3D8R` disponibili come oggi lo sono `C3D4` e
`C3D10`. La ragione è meccanica e va scritta: un telaio lavora a flessione,
`C3D8` a integrazione piena si irrigidisce a taglio e restituirebbe spostamenti
troppo piccoli — un errore invisibile guardando la mesh. `C3D8R` ha il problema
opposto, i modi a clessidra. `C3D8I` è supportato sia da Abaqus sia da CalculiX.

**Vincolo imposto dal codice:** almeno tre strati di elementi nello spessore. Con
uno o due la flessione nello spessore non è rappresentata, e il risultato è
sbagliato senza alcun segnale.

### 5.2 Le giunzioni del telaio

Le sei membrature si compenetrano dove si incontrano. Vanno **tagliate ai piani
di giunzione**, o il volume viene contato due volte — errore che nessuna metrica
di qualità vedrebbe, e per questo il controllo di § 8 lo cerca esplicitamente.

Le mesh di membrature adiacenti non combaciano nodo a nodo (una sezione da 172
contro una da 700): il legame è un `*TIE` fra le superfici a contatto. La mesh
conforme multiblocco resta la via d'aggiornamento, segnata nel codice con un
commento che ne dichiara il soffitto.

**Questa è una differenza fra i modelli che non deriva dalla geometria**, e il
report la dichiara accanto al confronto: *as-built monolitico, parametrici
vincolati alle giunzioni*. Senza quella riga, una differenza di rigidezza nata
dal `*TIE` verrebbe letta come effetto della forma.

---

## 6. Il deck

Stessa macchina della Fase 1 — nodi, elementi, `ALL_WALL`, set di nodo,
materiale, gravità — con tre aggiunte:

1. **`*SURFACE, TYPE=ELEMENT`**, il debito rinviato dalla Fase 1, che serve sia
   al `*TIE` sia ai carichi laterali. La mappatura delle facce dell'elemento
   sulle etichette del solutore è per tipo di elemento, e ha il proprio test:
   è la fonte d'errore silenzioso per cui il debito era stato rinviato.
2. **Carico laterale opzionale**: una pressione su una faccia nominata,
   dichiarata in configurazione, assente se non richiesta.
3. **Materiale unico** `CALCESTRUZZO`, dichiarato dall'operatore.

### 6.1 Come si verifica un deck senza licenza Abaqus

Non leggendolo: dandolo da leggere a CalculiX, che è installato e verificato
dalla Fase 0. Il controllo è che il solutore **accetti** il deck su un modello
piccolo, non che la risposta sia giusta — quello è Fase 5. Un deck che nessun
solutore ha mai aperto è un deck di cui non sappiamo se esiste.

---

## 7. Il confronto

Quasi nessuna metrica è confrontabile fra i tre modelli senza mentire, e la
tabella dice quale lo è.

| grandezza | confrontabile | nota |
|---|---|---|
| volume, massa | **sì** | e contro i 0,4777 m³ di tavola |
| scostamento della superficie dalla nuvola sorgente | **sì** | è la misura centrale |
| numero di nodi e gradi di libertà | sì | solo accanto al tipo di elemento |
| qualità degli elementi | **no** | `min_ratio` per i tetraedri, Jacobiano scalato per gli esaedri: due colonne separate, mai una differenza fra le due |
| rigidezza, spostamenti | **no** | nessun solutore in questa fase |

Lo **scostamento dalla nuvola** è il perno del confronto: è definito allo stesso
modo per tutti e tre i modelli e risponde alla domanda vera — quanto costa, in
fedeltà al rilievo, la regolarizzazione della forma.

### 7.1 Insiemi parziali

L'utente sceglie quali modelli generare. Il confronto deve quindi reggere gli
insiemi parziali: con due modelli su tre confronta due modelli e **dice quale
manca**; con uno solo diventa una scheda singola e lo dichiara. Nessuna colonna
con un trattino che somiglia a un valore, nessuna differenza calcolata contro un
modello assente.

La selezione è un'**azione, non un parametro di elaborazione**: non entra in
`config.yaml` della corsa madre, o rigenerare un modello in più cambierebbe
l'impronta di una corsa che non è cambiata.

---

## 8. I controlli della fase

| grandezza | ciò che la contraddice |
|---|---|
| scomposizione in membrature | 6 su `lab_frame`, 1 su `muro_generato`; un numero diverso ferma la corsa |
| sezioni misurate | i nominali di tavola |
| volume del prior | i 0,4777 m³ di tavola |
| mesh esaedrica | volume della mesh contro volume analitico dei prismi; nessun Jacobiano negativo |
| giunzioni | somma dei volumi delle membrature contro volume dell'unione: se differiscono, c'è doppio conteggio |
| superfici di elemento | area della superficie esportata contro area calcolata sulle facce |
| deck | `ccx` lo legge senza errori |
| indipendenza dalla piattaforma | ordini, indici e conteggi funzione del dato e non della macchina, come già imposto per l'ordine dei voxel di Open3D |

---

## 9. L'interfaccia

**Colonna della pipeline.** Step 12, «Prior geometrico», con i propri parametri a
destra: passo della griglia, tolleranza di semplificazione del contorno, soglie
dei controlli. Sotto, le tre caselle dei modelli: as-built spuntata e
disabilitata (esiste già, è la corsa madre), estruso e primitive libere.

**Viewport.** Tre aggiunte, due delle quali riusano quanto esiste:

- membrature colorate per regione — è la prova visiva che la scomposizione ha
  capito il pezzo, e si legge in un secondo dove nessuna metrica sarebbe così
  rapida;
- rigonfiamento come mappa di colore — il viewport ha già le mappe di deviazione
  dalla Fase 3: cambia il campo scalare, non la macchina;
- disegno della mesh esaedrica — la superficie di contorno di un esaedro è fatta
  di quadrilateri, che vanno divisi in triangoli per il disegno.

**Il confronto è un pannello, non una modalità 3D nuova.** Tabella e mappe
accanto, con il selettore del modello mostrato nel viewport. La vista di
sovrapposizione as-built/parametrico si aggiunge dopo, se guardando la tabella
serve.

**Stati vuoti che insegnano**, come impone il quinto principio del prodotto: «il
prior non è ancora stato calcolato», «questo modello non è stato generato», e in
caso di rifiuto il motivo per esteso — quale controllo ha detto no, e quale
numero glielo ha fatto dire.

---

## 10. Ciò che questa fase non fa

- **Nessun solutore, nessuna risposta strutturale.** È la Fase 5.
- **Nessuna armatura.** Scelta dell'autore; la tavola conserva il dato.
- **Nessun tamponamento.** Non è nel modello e non è nel provino scansionato.
- **Nessuna riscrittura delle corse di riferimento.** Conservano il materiale con
  cui sono state eseguite; le loro grandezze geometriche restano valide, la massa
  no, e il documento di esito lo dice.
- **Nessuna mesh conforme alle giunzioni.** `*TIE` ora, multiblocco come via
  d'aggiornamento dichiarata.
- **Nessun confronto fra tavola e costruito come obiettivo.** I modelli si
  misurano sulla nuvola; la tavola serve a contraddire, non a modellare.
