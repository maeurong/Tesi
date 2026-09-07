# Il deck va nudo e il prior scrive STEP

**Data:** 7 settembre 2026
**Stato:** approvata dall'autore, pronta per `superpowers:writing-plans`
**Mappa:** [#187](https://github.com/maeurong/Tesi/issues/187) — i ticket
[#188](https://github.com/maeurong/Tesi/issues/188) (fusione fuori piombo) e
[#189](https://github.com/maeurong/Tesi/issues/189) (baseline del collaudo)
sono chiusi.
**ADR:** [Deck nudo](../../adr/2026-09-07-deck-nudo-via-analisi-carichi-selettori.md),
[STEP dal prior geometrico](../../adr/2026-09-07-step-dal-prior-geometrico.md).
**Glossario:** [CONTEXT.md](../../../CONTEXT.md). I termini in grassetto alla
prima occorrenza sono quelli del glossario.

## Problem Statement

Il tutor importa in Abaqus/CAE il **deck** che MeshRec scrive e trova
l'istanza già impostata: materiale, sezione, incastro alla base, un passo di
gravità e, nel caso di tesi, altri tre passi di carico. Vuole invece tenere i
tetraedri di MeshRec e impostare lui — in CAE, a mano, come la tesi prevede
— materiale, sezioni, passi, peso proprio, carichi e vincoli, poi lanciare
l'analisi. Oggi deve prima disfare ciò che il programma ha già deciso per lui.

La richiesta iniziale era «esporta STEP o SAT, perché il `.inp` entra come
mesh orfana». Lo spike del 7 settembre 2026 ha mostrato che una mesh orfana
permette già tutto ciò che il tutor vuole (sezioni, set, carichi, vincoli,
job); che STEP e SAT portano geometria, non mesh, quindi Abaqus butterebbe i
tetraedri e rimesherebbe da sé; e che SAT non è producibile con strumenti
aperti. Il problema vero è il deck che arriva già carico.

In più, il programma porta da tre fasi di sviluppo (5, 6 e 8) un'intera
infrastruttura di carichi, selettori, cataloghi di materiali e combinazioni
che alimenta quelle righe: configurazione, interfaccia, rotte, tre moduli,
ventun file di test. Nessuno di quei numeri ha più un consumatore da quando il
solutore integrato è uscito da `main` (mappa #161, 2 settembre 2026).

## Solution

1. **Il deck va nudo.** Il deck del muro porta soltanto l'intestazione, i
   nodi, gli elementi in un solo insieme, i sei insiemi di nodi delle facce
   (BASE, TOP, FACE_FRONT, FACE_BACK, SIDE_LEFT, SIDE_RIGHT) e un insieme di
   elementi per ogni **regione** attribuita a una **membratura**. Sezioni,
   materiali, vincoli, passi, carichi e superfici non ci sono: si assegnano
   in Abaqus. Il deck del **modello parametrico** va nudo allo stesso modo,
   ma conserva i legami `*TIE` con le loro `*SURFACE`, perché senza di essi
   le membrature sono blocchi sciolti.
2. **La configurazione si stringe.** Escono i blocchi dell'analisi, dei
   carichi e dei selettori, il materiale dichiarato per regione e il catalogo
   dei materiali. Le regioni restano con la sola membratura. L'unico
   parametro dell'analisi che il deck nudo usa ancora — il fattore di
   tolleranza con cui si costruiscono gli insiemi di facce — migra in un
   blocco nuovo, `export`, letto soltanto dallo step 11.
3. **Un file di configurazione vecchio viene rifiutato con un messaggio che
   nomina il blocco tolto**, la data in cui è uscito e dove sta ora il
   parametro superstite. Nessuna migrazione silenziosa.
4. **Il modello parametrico scrive anche una geometria STEP**: il solido
   unico fuso dalle sue membrature, accanto al proprio deck, per entrambi i
   tipi (`estruso` e `primitive`). Abaqus lo importa come geometria e lo
   mesha da sé; è una seconda uscita, non un sostituto del deck.
5. **L'interfaccia segue la configurazione.** L'editor dei blocchi è guidato
   dallo schema, quindi i blocchi tolti spariscono da soli; a mano escono il
   pannello del materiale con la sua rotta e le etichette dei blocchi, e il
   testo d'aiuto dell'ingresso dice in una riga che materiali, vincoli e
   carichi si assegnano in Abaqus.

## User Stories

1. Come tutor, voglio importare il deck in Abaqus/CAE e trovare una mesh
   senza materiale, sezione, vincolo né passo, così da impostare io l'analisi
   senza prima disfare quella del programma.
2. Come tutor, voglio che il deck porti gli insiemi di nodi delle sei facce,
   così da applicare incastri e carichi ai set senza selezionare nodi a mano.
3. Come tutor, voglio che, quando il prior ha attribuito le regioni, il deck
   porti un insieme di elementi per membratura, così da assegnare una sezione
   diversa a ogni pilastro e trave.
4. Come tutor, voglio che i tetraedri di MeshRec restino i miei elementi, così
   che l'analisi in Abaqus sia sulla mesh che la tesi ha misurato.
5. Come autore della tesi, voglio che il deck sia riproducibile e confrontabile
   byte per byte con quello di prima nelle parti che restano, così da
   dimostrare che la rimozione non ha toccato la mesh.
6. Come autore, voglio che la configurazione non chieda più materiale,
   carichi né selettori, così da non compilare numeri che nessuno legge.
7. Come autore, voglio che un mio yaml vecchio con `analysis` o `carichi`
   fallisca con un messaggio che nomina il blocco e dove sta ora la
   tolleranza, così da correggerlo in un minuto invece di scoprire un deck
   diverso in silenzio.
8. Come autore, voglio regolare la tolleranza con cui si costruiscono gli
   insiemi di facce senza invalidare la tetraedrizzazione, così da non rifare
   lo step 9 per un ritocco allo step 11.
9. Come autore, voglio che una regione dichiarata a cui il prior non
   attribuisce elementi produca un avviso e non un errore, così che il deck
   esca comunque e io veda quale membratura manca.
10. Come autore, voglio che una corsa senza regioni produca lo stesso deck di
    oggi meno le righe di analisi, così da confrontarlo col baseline.
11. Come autore, voglio che `meshrec model` scriva accanto al deck un file
    STEP con il solido fuso delle membrature, così da confrontare in Abaqus la
    mesh dal rilievo con quella che Abaqus genera dal modello idealizzato.
12. Come autore, voglio lo STEP sia per il tipo `estruso` sia per il tipo
    `primitive`, così da portare in Abaqus il fuori piombo misurato oppure il
    telaio raddrizzato.
13. Come autore, voglio una metrica che dica quanti solidi contiene lo STEP e
    quanto il loro volume scarta dall'analitico, così da sapere se la fusione
    ha lasciato pezzi staccati.
14. Come autore, voglio che membrature disgiunte o a contatto di solo spigolo
    restino solidi distinti nello stesso file, dichiarati nella metrica, senza
    eccezione, così che il file esca e il conteggio mi avvisi.
15. Come autore, voglio che un prior senza membrature accettate non produca
    uno STEP vuoto ma un errore che dice di guardare le regioni scartate.
16. Come autore, voglio che il deck del modello parametrico conservi i legami
    tra membrature, così che in Abaqus il telaio sia un corpo solo.
17. Come utente successivo, voglio che l'interfaccia non mostri il pannello
    del materiale né i blocchi di carichi e selettori, così da non
    configurare ciò che il programma non usa.
18. Come utente successivo, voglio che l'ingresso mi dica in una riga che
    materiali, vincoli e carichi si assegnano in Abaqus, così da sapere dove
    finisce il programma.
19. Come utente successivo, voglio che il pannello dello step 11 mostri solo la
    tolleranza degli insiemi e le regioni, così da capire cosa governa il
    deck.
20. Come autore, voglio che le corse già su disco si aprano ancora e che lo
    step 11 risulti «non valido» finché non lo rieseguo, così da sapere che il
    deck sul disco non è quello che il programma scriverebbe ora.
21. Come autore, voglio che i registri di sweep non si muovano, così che le
    ventidue righe già scritte restino leggibili.
22. Come autore, voglio che il patch test continui a girare con `ccx`, così
    che la permutazione dei nodi C3D10 resti controllata anche se il deck non
    porta più materiale.
23. Come autore, voglio che `PRODUCT.md` dichiari il perimetro nuovo — dalla
    nuvola al deck nudo, dal prior alla geometria STEP — così che la tesi e il
    codice dicano la stessa cosa.
24. Come lettore del repository, voglio che i documenti delle fasi 5, 6 e 8
    restino intatti con una riga in testa che dice che sono superati, così da
    leggere come si è arrivati qui senza crederli attuali.
25. Come autore, voglio che il collaudo confronti il deck nuovo col baseline
    di `runs/geoandgeo-lab` e importi in CAE deck e STEP, così da chiudere con
    una prova e non con una suite verde soltanto.

## Implementation Decisions

### Il deck nudo

- Il deck del muro contiene, nell'ordine: intestazione, nodi, elementi in un
  solo insieme, un insieme di nodi per ciascuna delle sei facce, un insieme di
  elementi per ogni regione attribuita. Niente altro. Senza regioni il deck è
  quello di oggi meno le venti righe di sezione, materiale, vincolo e passo
  (misurato sul pilastro sintetico dello spike).
- Una regione dichiarata senza elementi attribuiti non scrive il proprio
  insieme vuoto: registra un avviso dedicato (`RegioneVuotaWarning`) e il deck
  si scrive. Oggi solleva perché la sezione mancherebbe; senza sezioni il
  motivo dell'errore non c'è più. Cambio dichiarato.
- Il deck del modello parametrico conserva `*TIE` e `*SURFACE` fra le
  membrature, perde sezioni e materiali. È l'unico deck che le porta: il deck
  del muro non ne ha mai avute.
- La metrica `mass` cade con la densità; la riga «massa» del confronto fra
  modelli cade con lei. Il volume resta. La copertura della base resta
  misurata su BASE fisso e il suo avviso punta al parametro nel blocco
  `export`.
- Il patch test di validazione si appende da sé le card di materiale,
  vincolo e passo (una ventina di righe nel test) e continua a lanciare
  `ccx`: è l'unico controllo rimasto sulla permutazione dei nodi C3D10.

### La configurazione

- Escono i blocchi `analysis` (materiale, gravità, set vincolato, nome del
  passo), `carichi` (spinta orizzontale, carico in sommità, modale,
  posizionati, distribuiti, combinazioni) e `selettori` (box, sfera, nodo,
  nset), con le loro classi e i loro validatori. Esce il tipo del materiale e
  il materiale dichiarato per regione, con provenienza, classe e norma. Esce
  il catalogo dei materiali con la sua rotta. Escono `lateral_nset` e
  `lateral_pressure` del modello parametrico. Esce il comando `meshrec init`,
  che serviva a compilare il materiale da riga di comando.
- Le regioni restano con la sola `membratura`; il modulo di attribuzione
  elemento→membratura resta com'è.
- Nasce il blocco `export` con il solo `set_tolerance_factor`, positivo,
  letto soltanto dallo step 11: la tabella dei blocchi per step diventa
  `("tet", "export", "regioni")` per l'undicesimo. Non in `tet`, perché
  avrebbe invalidato gli step 9 e 10 e sarebbe apparso nei loro pannelli.
- La radice della configurazione non vieta i campi ignoti, quindi un yaml
  vecchio passerebbe in silenzio. Un validatore «prima» sulla radice e uno sulle
  regioni rifiutano i nomi in un elenco di blocchi rimossi con un messaggio che
  dice: il blocco, la data e la PR che l'hanno tolto, dove sta ora
  `set_tolerance_factor`. Nessuna migrazione automatica: riscriverebbe il file
  dell'utente cambiando il significato della corsa in silenzio. `extra="forbid"`
  da solo non basta, perché il messaggio di pydantic non nomina niente.
- Le impronte degli step si muovono una volta: le corse già su disco mostrano
  lo step 11 e il 12 come «non valido» e si rieseguono in secondi. I registri
  di sweep non si toccano: la verifica dei registri confronta i digest degli
  artefatti, non l'impronta della configurazione.
- I quattro file di caso nel repository perdono i blocchi `analysis` e
  `carichi`.

### La geometria STEP

- Il modello parametrico, per entrambi i tipi, scrive `modello.step` accanto
  al proprio deck nella corsa figlia. Le membrature si costruiscono nel kernel
  OpenCASCADE di gmsh, direttamente in coordinate globali (origine più
  contorno nel piano locale, estrusione lungo l'asse per la lunghezza), a
  partire dai prismi **non tagliati**: il taglio alle giunzioni serve alla
  mesh esaedrica, non alla geometria. Poi una fusione booleana in un solido.
  La mesh esaedrica e il suo deck restano come sono: lo STEP è una seconda
  uscita.
- Fusione con le opzioni predefinite, **nessun parametro di tolleranza in
  configurazione**. Misurato il 7 settembre 2026 (#188): fino a 3° di fuori
  piombo e 3 mm di compenetrazione la fusione dà un solido a volume esatto,
  senza schegge. Restano due solidi le membrature disgiunte, quelle a contatto
  di solo spigolo, e quelle con un gioco sotto il decimo di millimetro. L'unica
  leva che agisce sulla fusione è la tolleranza booleana di gmsh; se un caso
  reale mostrerà giochi sub-millimetrici, si porterà a 1 mm, sempre sotto lo
  spessore minimo (a 400 mm su un pilastro da 300 il volume cala del 29%).
  Non usare la riparazione delle forme prima della fusione: distrugge i
  prismi coincidenti. Non chiamare `fragment` prima di `fuse`: nessun effetto.
- La metrica dello STEP porta il numero di solidi, il volume totale, il
  volume analitico (somma area per lunghezza delle membrature) e lo scarto
  relativo. Solidi maggiori di uno è un fatto dichiarato, non un errore.
  Nessuna rilettura del file in produzione: la rilettura sta nel test.
- Zero membrature accettate dal prior: nessun file scritto, errore che rimanda
  alle regioni scartate. È lo stesso errore che oggi rifiuta di generare un
  modello vuoto.
- Il formato è STEP AP214, l'unico che gmsh scrive. Verificato in CAE
  dall'autore sul telaio sintetico dello spike: entra come part unica.
- SAT non si produce: formato ACIS proprietario, nessun kernel aperto lo
  scrive.

### L'interfaccia

- L'editor dei blocchi è guidato dallo schema servito dal server: i blocchi
  tolti dalla configurazione spariscono da soli e il blocco `export` compare
  nel pannello dello step 11.
- A mano escono: la rotta del catalogo dei materiali e il pannello che la
  consuma, le etichette dei blocchi rimossi, il testo d'aiuto dell'ingresso
  che rimandava il materiale allo step 11 (diventa una riga sola: materiali,
  vincoli e carichi si assegnano in Abaqus), l'elenco dei campi fuori dal
  pannello che citava l'analisi.
- Nessuna vista nuova. Il pannello dello step 11 non elenca gli insiemi che il
  deck scrive: lo dice già il deck.

### La prosa

- `PRODUCT.md`: il paragrafo del perimetro diventa «dalla nuvola al deck nudo,
  che Abaqus completa; dal prior alla geometria STEP dei modelli parametrici»,
  con rimando alla spec del 31 agosto 2026 e ai due ADR.
- `AGENTS.md`: una frase nella sezione su `ccx`, che ora resta per il solo
  patch test.
- La spec del 31 agosto 2026 riceve un paragrafo di rimando; i documenti e le
  spec delle fasi 5, 6 e 8 restano intatti con una riga in testa «superato il
  7 settembre 2026, vedi ADR …».
- `CONTEXT.md` è il glossario; non porta implementazione.

### Sequenza

Quattro PR separate su `main`, ciascuna verde su Linux e macOS e con un `main`
coerente dietro di sé. Non un ramo unico come in #161: qui gli stati
intermedi sono coerenti per costruzione.

1. `feat/deck-nudo-carichi` — escono carichi, selettori, `lateral_*`, i passi
   e i materiali multipli del deck. Il deck torna alla forma precedente alla
   Fase 5 (materiale unico, vincolo, un passo). Una sessione.
2. `feat/deck-nudo-analisi` — escono analisi, materiale dichiarato, catalogo,
   `meshrec init`; entrano `export` e il rifiuto nominato; cade `mass`; il
   patch test si porta le card; file di caso e prosa. Dipende dalla 1. Una
   sessione.
3. `feat/step-dal-prior` — scrittura dello STEP e metrica. Indipendente dalle
   prime due nel codice: può correre in parallelo alla 1 su un altro
   worktree. Mezza sessione.
4. `feat/ui-senza-materiale` — rotta e pannello del materiale, etichette,
   testo d'aiuto, test dell'interfaccia. Dipende dalla 2. Mezza sessione.

Stima dell'architect: circa 6.000 righe tolte e 450 aggiunte, 35 file.

## Testing Decisions

Un buon test qui legge ciò che esce — il testo del deck, il file STEP riletto,
il messaggio d'errore, lo schema servito — e non gli interni. I seam sono
tutti esistenti; nessuno nuovo.

- **Il deck come testo**, sul maglio sintetico: il deck nudo senza regioni è
  il deck di prima meno le venti righe; con regioni porta un insieme di
  elementi per membratura; una regione vuota avvisa e non scrive l'insieme;
  nessuna card di sezione, materiale, vincolo, passo, carico o superficie
  compare. Prior art: le prove del deck sul cubo e sul pilastro sintetico che
  già asseriscono sulle righe `*`. Le prove dei carichi, dei selettori, delle
  combinazioni e del catalogo escono con il codice che provavano.
- **La corsa fino allo step 11** sul cubo sintetico: il deck esce, lo stato
  degli step lo registra, l'impronta dell'undicesimo cambia se cambia
  `export`, non se cambia solo `tet`. Prior art: le prove di ripresa e di
  invalidazione a valle.
- **La configurazione** da yaml: rifiuto nominato per ciascuno dei tre blocchi
  tolti e per il materiale di una regione, con il testo che nomina blocco e
  destinazione del parametro; tolleranza non positiva rifiutata alla
  validazione; un yaml con `export` valido passa. Prior art: le prove dei
  validatori e delle chiavi duplicate.
- **Lo STEP**, dal file scritto da `genera_modello` e riletto con gmsh: due
  prismi a T danno un solido a volume pari all'analitico; prismi disgiunti
  danno due solidi e la metrica lo dichiara; zero membrature danno l'errore e
  nessun file; entrambi i tipi di modello lo scrivono. Il volume si confronta
  con tolleranza relativa, non per uguaglianza: le grandezze continue non sono
  bit-identiche fra piattaforme. Prior art: le prove del modello parametrico
  che leggono il deck figlio, e l'esperimento del ticket #188 sul ramo
  `research/fusione-fuori-piombo`.
- **L'interfaccia**: lo schema servito non contiene i blocchi tolti e contiene
  `export`; la rotta del catalogo non esiste più; il pannello dello step 11
  mostra i due blocchi e il testo d'aiuto è la riga nuova. Prior art: le
  prove del server sulle rotte e quelle dell'interfaccia eseguite con `node`.
  Ricordare che senza `node` 158 prove saltano in silenzio: lanciare la forma
  onesta della suite.
- **Il collaudo, manuale**: `runs/geoandgeo-lab` rieseguita dallo step 9 con
  la configurazione aggiornata; nel deck nuovo `*NODE`, `*ELEMENT` e i sei
  `*NSET` sono identici al baseline (md5 `ba97f83be2f0d7b45f46e2f42f3bbfac`,
  14.103 nodi, 51.913 C3D4) e nessun'altra card compare. Lo STEP si collauda
  sul telaio sintetico, perché il prior oggi non accetta membrature su
  `lab_frame` (0 su 6). Deck e STEP li importa l'autore in CAE.

## Out of Scope

- **STEP dalla superficie del rilievo**: 1,6 milioni di facce diventerebbero
  un B-rep sfaccettato che in CAE non si mesha senza pulizia a mano, e
  servirebbe una dipendenza nuova. Scartato dall'autore.
- **SAT**: non producibile.
- **Selettori come set nominati senza carico**: scartati dall'autore; in CAE
  i set si creano selezionando la mesh.
- **Un parametro di tolleranza della fusione** in configurazione: misurato
  non necessario; resta una costante.
- **Il prior sul dato reale**: oggi non accetta membrature su `lab_frame`
  (tutto il telaio in una regione, le altre cadono per costanza di sezione e
  parallelismo). Misurarlo e tararlo è lavoro suo, con la propria mappa.
- **Rifare la corsa `geoandgeo`**, che è in metri con `scale: 1.0`: nota
  all'autore, non lavoro di questa spec.
- **Rifare l'analisi strutturale** dentro il programma (già fuori da #161) e
  **la validazione fisica del deck** (mappa #33).

## Further Notes

- Le unità restano quelle del prodotto: mm, N, MPa, t, s. Lo STEP eredita i mm
  dal modello.
- I quattro passi di carico che il deck di `lab_telaio.yaml` porta oggi
  (GRAVITA, SPINTA_ORIZZONTALE, CARICO_TOP, MODALE) sono ciò che il tutor si
  trovava davanti in CAE: il baseline li documenta, il deck nuovo non ne
  porta nessuno.
- Gli spike che hanno deciso la strada stanno in `runs/spike-abaqus/`
  (cartella non tracciata): il pilastro nudo e pieno, e il telaio STEP.
- Dopo la spec: `superpowers:writing-plans`, poi l'annotazione del piano da
  parte dell'`architect` (assegnazione, sequenziamento, skill-gate per passo),
  poi l'esecuzione per PR con il round di review in parallelo prima di ogni
  commit.
