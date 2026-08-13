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
La causa più probabile è la qualità della superficie riparata su quella geometria, che ha 41
cammini di bordo aperti e schegge residue; va affrontata in Fase 2, non aggirata alzando il
vincolo di qualità.

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
