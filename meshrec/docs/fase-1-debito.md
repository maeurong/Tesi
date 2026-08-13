# Fase 1 — Debito noto e questioni aperte

- **Data:** 13 agosto 2026
- **Stato del ramo:** dodici task completati, tutti revisionati; ogni rilievo Critical e
  Important chiuso e verificato in modo indipendente.
- **Aggiornato il 13 agosto 2026**, dopo tre interventi su questo documento stesso: l'orientazione
  della superficie riparata è garantita, `min_ratio` è verificato sul maglio prodotto, e la regola
  che sostituisce la tolleranza dei set è misurata e in attesa di implementazione. Le voci
  interessate lo dicono al loro posto invece di essere cancellate, perché come si è arrivati a
  chiuderle è parte di ciò che il documento serve a tramandare.

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
convergeva.

La terza causa è stata poi trovata, e chiude la questione. Un fallimento che non cambia quando il
vincolo di qualità diventa inerte non è causato dal vincolo di qualità: nel raffinamento di
Delaunay una faccia di bordo viene suddivisa anche per **invasione** della sua sfera diametrale, e
quella suddivisione ricorre fino alla distanza locale fra lembi opposti della superficie. Su
`lab_frame.pcd` quella distanza crolla: lo 0,15% della superficie ha dietro di sé meno di un
millimetro di materiale e lo 0,41% meno di cinque, contro una mediana di 181,5 mm, mentre il muro
sintetico non scende mai sotto i 1190 mm. Sono strozzature interne, non l'assottigliamento del
bordo. La verifica è a variabile unica: con `nobisect`, che vieta a TetGen di suddividere le facce
di ingresso, la stessa superficie allo stesso `min_ratio` 1,8 **converge** — 365.212 nodi,
1.607.146 tetraedri, 32,6 s, zero invertiti, mediana dell'angolo diedro minimo 38,83°. Senza,
fallisce in 72 s. I dettagli e il costo della leva sono in
[`fase-1-min-ratio.md`](fase-1-min-ratio.md).

`nobisect` è stato quindi esposto come `tet.nobisect`, con predefinito **falso** perché nessun
risultato documentato cambi. Con `tet.nobisect: true` e il `min_ratio` predefinito, **la pipeline
su `lab_frame.pcd` arriva al deck**: il criterio di accettazione della Fase 1 è raggiungibile, non
più solo mancato. Resta però un modello che non si può ancora usare, e per una ragione diversa da
quelle di questa voce: `BASE` raccoglie 850 nodi su 365.212, cioè il difetto della tolleranza dei
set descritto più sotto. Il criterio va quindi considerato soddisfatto nella lettera —
l'elaborazione arriva in fondo e scrive un deck valido — e non nella sostanza.

Quel numero è ora quantificato: gli 850 nodi coprono il **34,76%** della superficie che poggia
davvero a terra, e sotto la regola raccomandata in [`fase-1-tolleranza-set.md`](fase-1-tolleranza-set.md)
diventano 5915 nodi al 98,93% di copertura. Restano pochi in assoluto, ma per una ragione fisica e
non per un difetto: `lab_frame` è un telaio, e solo il 16,26% della sua impronta tocca il suolo.

Non è la fine della questione. Le strozzature sotto il millimetro nascono nella ricostruzione, e
`nobisect` chiede a TetGen di conviverci invece di rimuoverle: è la leva che funziona, non
necessariamente quella giusta. Affrontarle a monte resta l'alternativa da valutare in Fase 2.

**Esporre `nobisect` ha rivelato una trappola gemella di quella di `fixedvolume`.** Con
`nobisect` attivo TetGen non aggiunge punti sul bordo, e su una superficie di ingresso grossolana
restituisce pochi elementi enormi senza segnalare nulla: sul cubo di prova, con `max_volume` di
2000 mm³, dà **12 tetraedri invece di 7103**, lasciando il limite impostato e disatteso. È ora
dichiarata da `IneffectiveVolumeLimitWarning`, con soglia a un fattore due perché `maxvolume` per
TetGen è un obiettivo e non un tetto: lo scarto di routine è di circa il 10% anche a raffinamento
riuscito. Il conto dei parametri della libreria che risultano impostati e inerti sale così a tre —
`maxvolume` senza `fixedvolume`, `steinerleft` al predefinito, `max_volume` sotto `nobisect` — e
tutti e tre sono stati trovati per caso, nessuno da un controllo che li cercasse.

**La famiglia è ora chiusa, e il quarto membro era `min_ratio` stesso.** `max_steiner_points` era
verificato sul risultato dal conteggio dei punti aggiunti e `max_volume` da
`largest_element_volume`; il rapporto raggio-spigolo, che è la grandezza che `minratio` vincola,
da nulla. `quality.radius_edge_ratios` lo misura ora sul maglio prodotto e la distribuzione entra
nelle metriche dello step 10.

La misura dice una cosa che va scritta: **`minratio` è un obiettivo e non un tetto, esattamente
come `maxvolume`.** Con `min_ratio` 1,8 il vincolo resta violato dall'8,10% degli elementi sul
muro di riferimento (1.752.795 tetraedri), dal 9,55% su `lab_frame` tetraedrizzato con `nobisect`
(1.607.146) e dallo 0,00% sul cubo sintetico. Una corsa sana a scala reale lascia quindi fuori
vincolo circa un elemento su dieci: sono gli sliver di bordo che il raffinamento non può
legalmente correggere.

La grandezza sorvegliata è la frazione di elementi fuori vincolo e non un percentile alto della
distribuzione. Un percentile avrebbe richiesto una soglia tarata, e tarare su due sole corse è il
debito che già portiamo per `min_ratio` stesso; la frazione si legge da sola. L'avviso scatta
oltre la metà, che non è una soglia scelta ma un'affermazione qualitativa: quando gli elementi che
violano il vincolo sono più di quelli che lo rispettano, il parametro non sta governando quel
maglio.

Una nota utile a chi userà `nobisect`: sul cubo di prova, con la superficie di ingresso a otto
vertici, `nobisect` porta la frazione fuori vincolo al 66,67%. È un effetto della superficie
grossolana e **non** di `nobisect` in sé — su `lab_frame`, dove la superficie ha 213.154 vertici,
la frazione è il 9,55%, in linea con l'8,10% del muro senza `nobisect`. Il sospetto opposto era
naturale ed è stato misurato prima di essere scritto.

**La prova che questo avviso serviva è retrospettiva, ed è la più forte disponibile.** La mesh che
la Fase 1 aveva scambiato per un successo su `lab_frame` era quella troncata dal tetto ereditato di
100.000 punti di Steiner — 313.154 nodi meno i 213.154 vertici della superficie fanno esattamente
100.000, verificato — e nessuna metrica dell'epoca la smentiva: zero elementi invertiti, deck
scritto, tutto in ordine. Su quella mesh la frazione fuori vincolo vale l'**86,36%**. L'avviso
l'avrebbe segnalata. È il caso da manuale del requisito enunciato in fondo a questo documento: una
metrica senza un controllo che la smentisca misura soltanto che il codice ha girato.

**La semplificazione può rompere le garanzie della riparazione, e nulla se ne accorge.** Lo step 6
produce una superficie chiusa e senza autointersezioni, lo step 7 lo verifica, e lo step 8 la
modifica senza che nessun controllo venga rieseguito. Le 16 autointersezioni introdotte dal
remeshing sono la dimostrazione che non è un rischio teorico: la superficie risultante resta chiusa
e manifold, quindi supera ogni criterio che la pipeline sappia applicare, ed è comunque inservibile
per TetGen. La garanzia di orientazione ora aggiunta allo step 6 eredita lo stesso buco: nulla
rivalida il verso delle facce dopo la semplificazione.

**~~Lo step 7 dichiara chiusa una superficie rovesciata.~~ Corretto allo step 6.** `watertight:
true`, `boundary_edges: 0` e un volume racchiuso **negativo** convivevano senza che nulla
protestasse: `is_watertight` conta gli spigoli, e una superficie capovolta ne ha due per spigolo
esattamente come una diritta. Il numero negativo era già in `metrics["volume_after"]` e nessuno lo
guardava.

La correzione è alla radice e non allo step 7: chi promette una superficie chiusa promette anche
il verso, perché è ciò che TetGen richiede in ingresso. `repair_surface` inverte ora
l'avvolgimento quando il volume racchiuso è negativo e lo dichiara in
`metrics["orientation_flipped"]`; l'inversione è esatta, non approssima nulla e non sposta un
vertice. Verificato sulla scansione che ha originato il difetto: `05_surface.ply` di `lab_crop`
entra a −0,0284 m³ ed esce a +0,1733 m³. **MeshFix da solo non raddrizza**: restituisce la
superficie chiusa e rovesciata, ed è per questo che il difetto è sopravvissuto a uno step di
riparazione.

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

**La tolleranza dei set non ha una base solida. La regola che la sostituisce è ora misurata; resta
da implementare.** `set_tolerance` deriva dal volume medio dell'elemento, su una distribuzione con
coda pesantissima: sul muro la mediana vale 14,6 mm³ e la media 30.735 mm³, un fattore duemila.
Legare la tolleranza al volume dell'elemento è l'euristica sbagliata in partenza.

Quanto costi si sa ora con precisione, ed è più di quanto la voce lasciasse intendere. La misura è
in [`fase-1-tolleranza-set.md`](fase-1-tolleranza-set.md), che introduce la **copertura per
colonne**: contare i nodi di un insieme non dice nulla, perché possono stare tutti ammucchiati in
un angolo, mentre la frazione di impronta d'appoggio che l'insieme raggiunge sì. `BASE` sul muro
copre il **55,78%** delle colonne che poggiano a terra, e vale il 12,1% di uno strato singolo di
nodi. Su `lab_crop`, il 34,76%.

**Le due regole candidate sono state entrambe respinte da un numero.** La spaziatura dei nodi di
bordo, che questa voce suggeriva, ha la grandezza giusta e il fattore sbagliato di più di un
ordine: a 0,5 spaziature la tolleranza sul muro scende a 6,86 mm e `BASE` a **138 nodi**, cioè
trentaquattro volte peggio dell'euristica che doveva sostituire. La selezione per direzione della
normale, che è lo standard dei preprocessori, è catastrofica su una scansione con aperture:
l'**87,8%** dell'area di `lab_crop` rivolta verso il basso è l'intradosso dell'architrave, a
1493,5 mm su 1693,99 mm di altezza, e finirebbe in `BASE` — un modello appeso al soffitto del
proprio vano di porta. Su un muro pieno la stessa regola sarebbe sana, e questo è il punto: una
regola che dipende dalla presenza di aperture non è una regola.

La regola raccomandata mantiene la forma `fattore × scala` e cambia entrambi: la scala diventa la
mediana della lunghezza degli spigoli di bordo del **maglio di volume** — non della superficie
riparata, che con `nobisect` falso è 2,4 volte più rada — e il fattore predefinito passa da 0,5 a
**6**. `BASE` sul muro passa da 4738 a 18.020 nodi e dal 55,78% al 100,00% di copertura, su
`lab_crop` da 850 a 5915 e dal 34,76% al 98,93%, con contaminazione nulla; nessun insieme peggiora
su nessuno dei due modelli. Il margine del 6 ha la stessa struttura di quello di `tet.min_ratio`:
5 è il primo valore che non regge, 4 il primo che crolla.

**La regola è ora implementata**, e i sei insiemi che produce coincidono con la misura su entrambe
le corse reali, non solo `BASE`. Il predefinito di `analysis.set_tolerance_factor` è 6 e le due
configurazioni tracciate sono allineate.

**Due esiti negativi che la misura ha prodotto e che la regola non risolve.** Il primo:
`FACE_FRONT` e `FACE_BACK` su una scansione reale sono inutilizzabili **per qualunque tolleranza**,
perché la faccia ricostruita si scosta dal proprio piano di 158 mm al p99 su 214 mm di spessore
totale — in qualche punto il punto più avanzato della faccia «anteriore» dista 23,5 mm dal piano
posteriore. Sul muro sintetico gli stessi due insiemi funzionano al 100%, il che rende il difetto
invisibile a chi provi solo lì. Non entrano nelle condizioni al contorno, quindi non invalidano il
modello, ma **su una scansione reale sono decorativi**. Il secondo: `lab_frame` è un **telaio**,
due piedritti e un architrave, non un muro pieno; riempie il 19,4% della propria scatola e solo il
**16,26%** della sua impronta poggia a terra. I 5915 nodi di `BASE` non sono un fallimento della
regola: quella è la superficie d'appoggio fisica, e nessuna regola può inventarne una più larga.

**~~La guardia sull'insieme vincolato è cieca su tutto ciò che non è vuoto.~~ Chiusa.**
`export_model` rifiutava un `BASE` vuoto ma accettava un `BASE` da 9 nodi, che produce un deck
formalmente valido per un modello di fatto non vincolato, e nessuna metrica confrontava la taglia
dell'insieme con la faccia che deve coprire: 4738 nodi su una faccia coperta al 55,78% e 4738 su
una coperta al 100% erano lo stesso numero in `metrics.json`.

`abaqus.footprint_coverage` divide l'impronta in colonne di lato quattro spaziature, distingue
quelle che toccano davvero terra e riporta quante ne raggiunge l'insieme vincolato; il valore
entra in `11_export` accanto alla spaziatura. La soglia dell'avviso è la metà, e come per
`min_ratio` non è un numero tarato ma un'affermazione qualitativa: quando la superficie d'appoggio
vincolata è meno di quella libera, il modello non è vincolato in alcun senso utile. Avrebbe
segnalato entrambe le corse sotto l'euristica precedente e tace sotto quella attuale.

La misura ha tre parametri impliciti — il lato della cella, la banda di contatto e l'asse — ed è
per questo che serve come diagnosi e non come regola: la tolleranza dei set ne ha uno solo.

**Il ripiego di `export_model` quando manca il riferimento non è utilizzabile su dati reali.** Era
già dichiarato inferiore — la terna stimata sui nodi di bordo del maglio si scosta di 15,33 gradi
dal verticale contro 0,45 stimandola sui vertici della superficie — con la postilla che restasse
«valido sulle geometrie di prova». La postilla regge, il ripiego no: sul muro reale porta `BASE`
da 18.020 nodi a **874** e la copertura della superficie d'appoggio dal 100,00% al **44,23%**. La
pipeline passa sempre il riferimento e non è quindi esposta, ma chiunque chiami `export_model` a
mano lo è. Il difetto è stato trovato dalla metrica di copertura il giorno in cui è nata, il che
è la miglior prova che serviva.

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
  hanno notato. La misura che mancava esiste ora — la copertura dell'impronta d'appoggio, in
  [`fase-1-tolleranza-set.md`](fase-1-tolleranza-set.md) — ma vive in un documento e non nel
  codice, quindi il test non è ancora in grado di usarla.
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

Gli interventi del 13 agosto sono la prima applicazione deliberata di quel requisito, e ne
confermano due corollari. Il primo: **una metrica scritta e non guardata non vale più di una
metrica assente.** Il volume racchiuso negativo era in `metrics.json` da sempre; è costato un giro
completo di indagine perché nulla lo confrontava con lo zero. Il secondo, meno ovvio: **la
grandezza da sorvegliare va scelta prima della soglia, non dopo.** Sorvegliare il novantanovesimo
percentile del rapporto raggio-spigolo avrebbe richiesto una soglia tarata così larga da non
scattare mai; sorvegliare la frazione di elementi fuori vincolo non richiede alcuna taratura.
Lo stesso vale per gli insiemi di nodi: contarli non dice niente, misurare quanta faccia coprano
dice tutto. Una soglia difficile da scegliere è spesso il sintomo di una grandezza sbagliata.
