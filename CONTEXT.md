# MeshRec

Porta un rilievo fotogrammetrico di una struttura in cemento armato fino a un
modello a elementi finiti che Abaqus completa e risolve. Questo file è il
glossario del progetto e nient'altro: cosa vuol dire ogni termine, non come è
implementato.

## Language

**Deck**:
Il file `.inp` che il programma scrive per Abaqus: la mesh e i suoi insiemi
nominati.
_Avoid_: input file, modello Abaqus, file di analisi

**Deck nudo**:
Un deck che porta solo nodi, elementi, insiemi di nodi delle facce e insiemi di
elementi per membratura. Materiali, sezioni, vincoli, passi e carichi non ci
sono: si assegnano in Abaqus.
_Avoid_: deck spoglio, deck senza analisi, mesh orfana (è come Abaqus chiama
qualsiasi mesh importata da `.inp`, non una proprietà del deck)

**Prior geometrico**:
La misura del rilievo che scompone la scansione in membrature prismatiche
(sezione, asse, lunghezza). È misura, non analisi: sta a monte del deck.
_Avoid_: prior, wall model, telaio misurato

**Membratura**:
Un elemento strutturale prismatico — pilastro o trave — che il prior riconosce
nella scansione.
_Avoid_: elemento (è l'elemento finito), prisma (è la sua forma geometrica),
asta

**Regione**:
L'insieme degli elementi finiti del deck attribuiti a una membratura.
_Avoid_: partizione, zona, sezione (è il termine di Abaqus per l'assegnazione
del materiale)

**Modello parametrico**:
Il modello a esaedri costruito dalle membrature del prior invece che dalla
superficie del rilievo. Ne esistono due tipi: `estruso`, che conserva sezione e
fuori piombo misurati, e `primitive`, che li raddrizza.
_Avoid_: modello idealizzato, modello hexa

**Geometria STEP**:
Il solido unico, fuso dalle membrature del prior, scritto in formato STEP
perché Abaqus lo importi come geometria e lo meshi da sé. È una seconda uscita
accanto al deck del modello parametrico, non lo sostituisce.
_Avoid_: CAD, esportazione STEP, file SAT (formato che il programma non scrive)
