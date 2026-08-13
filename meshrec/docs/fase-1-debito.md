# Fase 1 — Debito noto e questioni aperte

- **Data:** 13 agosto 2026
- **Stato del ramo:** dodici task completati, tutti revisionati; ogni rilievo Critical e
  Important chiuso e verificato in modo indipendente.

Questo documento raccoglie ciò che è stato deliberatamente lasciato aperto, perché un debito
noto e scritto è governabile e un debito dimenticato no. È il seguito naturale della sezione
omonima degli esiti di Fase 0.

## 1. Questioni che toccano la validità dei risultati

**La pipeline non arriva in fondo su `lab_frame.pcd`.** Con i parametri onesti la
tetraedrizzazione non converge: `RefinementFailedError` con ogni valore di `min_ratio` provato,
da 1,8 a 4,0. Il risultato che in precedenza sembrava un successo era la mesh troncata dal tetto
ai punti di Steiner, e rimettendo quel tetto si riproducono esattamente i numeri archiviati. Il
criterio di accettazione «su `lab_frame.pcd` la pipeline arriva in fondo» **non è soddisfatto**.

La causa è stata poi misurata, e la diagnosi che questa voce riportava — «la qualità della
superficie riparata» — era giusta a metà. Lo sweep documentato in
[`fase-1-min-ratio.md`](fase-1-min-ratio.md) porta `min_ratio` fino a 12,0, quasi sette volte il
predefinito e un vincolo di fatto inerte: fallisce identico a 1,8, sempre dentro `split_subface`.
La taratura del parametro è quindi esclusa. Ma i numeri non descrivono nemmeno una superficie
genericamente degradata: il 99,75% dei triangoli ha rapporto d'aspetto sotto 100, le
autointersezioni misurate sono zero, e la mesh è un manifold pulito di spigoli e vertici. Il
difetto è uno solo e preciso: **la superficie è rovesciata**. Le sue 426.600 facce puntano tutte
verso l'interno, con avvolgimento globalmente coerente (zero spigoli incoerenti su 639.900), e il
volume racchiuso è negativo, −0,173 m³, che capovolge esattamente di segno invertendo ogni
triangolo.

La correzione è stata poi provata, e il risultato è più informativo di un sì o di un no.
Capovolgendo l'avvolgimento di tutti i triangoli, senza toccare vertici né connettività, lo step 9
**converge a `min_ratio` 12,0** — 692.617 nodi, 2.230.860 tetraedri, nessun elemento invertito —
mentre la stessa superficie non raddrizzata, allo stesso valore e nella stessa cartella, continua a
fallire. L'orientazione è quindi una causa reale, verificata da un controllo in cui l'unica
variabile è il verso delle facce. Ma non è l'unica: sulla superficie raddrizzata i valori da 1,8 a
10,0 falliscono ancora, e il confine di convergenza cade fra 10,0 e 12,0, cioè a un vincolo di
qualità di fatto inerte. Il modello che ne esce non è utilizzabile — mediana dell'angolo diedro
minimo 25,33° contro 38,26° del muro sintetico, `BASE` con 420 nodi su 692.617 — ed è un esito
diagnostico, non un successo. Resta quindi una seconda causa da trovare, e il sospetto misurato
sono le 108 facce con rapporto d'aspetto oltre 1000, che è esattamente ciò che rende mal
condizionata la `split_subface` dove TetGen si arrende.

Anche il remeshing isotropo dello step 8 è stato provato, e non risolve: peggiora. Porta la
superficie da 426.600 a 89.772 triangoli ma vi **introduce 16 autointersezioni** dove non ce
n'erano, e lo step 9 fallisce allora prima ancora del raffinamento, nel recupero del bordo
(`recoversubfaces`), a qualunque `min_ratio`. Riparando con MeshFix dopo la semplificazione le
autointersezioni spariscono e il recupero del bordo torna a passare, ma il raffinamento fallisce
comunque da 1,8 fino a 12,0 — cioè anche al valore che sulla superficie non semplificata
convergeva. Resta quindi una terza causa, sotto l'orientazione e sotto le autointersezioni, che si
manifesta sempre come `split_subface`.

**La semplificazione può rompere le garanzie della riparazione, e nulla se ne accorge.** Lo step 6
produce una superficie chiusa e senza autointersezioni, lo step 7 lo verifica, e lo step 8 la
modifica senza che nessun controllo venga rieseguito. Le 16 autointersezioni introdotte dal
remeshing sono la dimostrazione che non è un rischio teorico: la superficie risultante resta chiusa
e manifold, quindi supera ogni criterio che la pipeline sappia applicare, ed è comunque inservibile
per TetGen.

**Lo step 7 dichiara chiusa una superficie rovesciata.** `watertight: true`, `boundary_edges: 0` e
un volume racchiuso **negativo** convivono senza che nulla protesti: il controllo di qualità della
superficie verifica la topologia e non l'orientazione, quindi lascia passare verso la
tetraedrizzazione una mesh il cui interno e il cui esterno sono scambiati. Un volume con segno
negativo su una superficie chiusa non è un caso limite da interpretare, è un difetto: andrebbe
segnalato dallo step 7, o corretto dallo step 6.

**Il margine di `tet.min_ratio` è ora misurato, ma su una sola superficie.** Il predefinito 1,8
era stato scelto per aneddoto — 1,6 falliva, 1,8 no — senza sapere quanto distasse dal punto di
rottura. La misura su sei valori da 1,4 a 2,5, riportata in
[`fase-1-min-ratio.md`](fase-1-min-ratio.md), colloca il confine fra 1,6 e 1,7: 1,8 non è quindi
il valore più severo che converge, ma quello che tiene un decimo di margine sopra di esso. Il
debito che resta è la generalità del numero. La misura vale per la superficie riparata di
`muro_generato.ply` con quel passo di voxel e quella profondità di Poisson; il confine dipende
dalla superficie, non dal parametro da solo, e su una geometria diversa può cadere altrove. Ha
però un corollario utile per la voce precedente: se su `muro_generato.ply` il parametro ha un
intervallo di lavoro largo e ben ordinato, e su `lab_frame.pcd` nessun valore fra 1,8 e 4,0
converge, allora il guasto su quella scansione non è una taratura da correggere ma la qualità
della superficie che entra nello step 9. È l'argomento più solido a favore della diagnosi scritta
sopra.

**Il controllo dei dati con Abaqus non è stato eseguito**, perché Abaqus non è disponibile sulla
macchina di sviluppo. Il deck è verificato in lettura con `meshio` e in soluzione con CalculiX
2.22. Resta dovuto alla prima occasione di accesso a una licenza.

**La tolleranza dei set non ha una base solida.** `set_tolerance` deriva dal volume medio
dell'elemento, su una distribuzione con coda pesantissima: sul muro la mediana vale 14,6 mm³ e la
media 30.735 mm³, un fattore duemila. Il passaggio alla mediana è stato implementato, misurato e
scartato perché peggiora il modello — `BASE` scenderebbe da 4738 a 9 nodi. La diagnosi è che né
media né mediana descrivono l'elemento tipico: gli elementi enormi sono interni, i minuscoli
stanno nello strato di bordo, e la scala che conta è la spaziatura dei nodi sul bordo, mediana
13,73 mm. Legare la tolleranza al volume dell'elemento è l'euristica sbagliata in partenza.
Sostituirla è un cambiamento di progetto.

**La guardia sull'insieme vincolato è cieca su tutto ciò che non è vuoto.** `export_model` rifiuta
un `BASE` vuoto ma accetta un `BASE` da 9 nodi, che produce un deck formalmente valido per un
modello di fatto non vincolato. Nessuna metrica confronta la taglia di un insieme con la faccia
che dovrebbe coprire.

**Poisson ingrassa il muro e l'errore geometrico non lo rivela.** Sulla scansione reale lo
spessore ricostruito vale 212,9 mm contro i 176 mm misurati, ma l'errore bidirezionale resta
piccolo perché è una distanza punto-superficie e un ispessimento simmetrico la lascia bassa. La
metrica di fedeltà adottata è cieca proprio all'errore sistematico che più conta per la rigidezza
di una muratura. Serve un controllo dedicato sullo spessore.

**I nomi dei set di faccia sono convenzioni.** `FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT` e
`SIDE_RIGHT` non hanno una corrispondenza verificata con le facce fisiche della scansione. Finché
i carichi sono il solo peso proprio la cosa è innocua; diventa rilevante in Fase 4, con i carichi
di pressione.

## 2. Verifiche che non verificano abbastanza

Tre lacune che, prese insieme, significano che né i test né le metriche noterebbero un modello
degradato. Sono state differite una alla volta e il loro effetto combinato è emerso solo nella
revisione finale.

- Il test di riproducibilità confronta conteggi di nodi ed elementi e volume totale, non le
  coordinate: sono precisamente gli invarianti sopravvissuti al disordine non deterministico di
  Poisson scoperto durante la fase.
- Il test sull'insieme `BASE` verifica che i nodi che vi stanno siano alla quota minima, ma non
  che vi siano tutti quelli alla quota minima, e prende il conteggio atteso dalla pipeline stessa.
  È esattamente il guasto trovato a mano, con `BASE` sceso a 387 nodi, che né il test né il codice
  hanno notato.
- Il test sul confronto Gmsh contro TetGen si chiama «a parità di elementi» ma la sola asserzione
  di qualità è che l'angolo diedro minimo sia positivo: Gmsh potrebbe peggiorare fino sotto TetGen
  senza far fallire nulla.

## 3. Debito minore, registrato e non urgente

- `synth.punch_holes` ha un valore predefinito fuori da `config.py`; è codice di supporto ai test.
- Una faccia esattamente degenere produce normale nulla e quindi un angolo diedro fabbricato di
  90°, inerte in pipeline perché un tetraedro degenere viene bloccato prima dallo step 9.
- I raggi di Ball Pivoting sono calcolati due volte in `surface.reconstruct`.
- `04_normals.ply` viene letto due volte nella ripresa da `from_step` fra 5 e 9.
- La conversione fra numpy e Open3D è ripetuta in cinque punti; la convenzione non diverge.
- `RefinementFailedError` deriva da `RuntimeError` mentre gli altri errori di dominio del core
  sono `ValueError`: un chiamante che filtra su `ValueError` se lo perde.
- Lo step 8 espone la chiave `vertices` solo quando è abilitato.
- In modalità `auto` il conteggio dei punti dopo il ritaglio viene sovrascritto e si perde.
- `TruncatedRefinementWarning` va su stderr mentre la riga di comando scrive il JSON su stdout;
  l'informazione è comunque ridondata in `metrics.json`.
- La componente connessa maggiore è scelta per numero di vertici e le dimensioni delle componenti
  scartate non compaiono nelle metriche.

## 4. Che cosa insegna questa fase

Sette affermazioni false sono state prodotte e corrette durante la Fase 1: quattro nel codice —
una mesh degenere con metriche buone, una mesh troncata in silenzio, fori inesistenti nel registro
della riparazione, un parametro di configurazione disattivato di nascosto — e tre nei documenti
degli esiti. Tutte avevano la stessa forma: un risultato plausibile che nessuna metrica smentiva.

Nessuna è emersa dai test sulle geometrie sintetiche, e tutte sono emerse nel passaggio ai dati
reali. Il parallelepipedo a soluzione nota serve a verificare che la catena non si spezzi, non che
produca qualcosa di sensato. Ne segue un requisito per le fasi successive: ogni metrica riportata
deve avere un controllo che la smentisca se il risultato si degrada, altrimenti misura soltanto
che il codice ha girato.
