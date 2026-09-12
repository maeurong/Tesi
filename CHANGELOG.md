# Changelog

Le versioni di MeshRec, nella forma di [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
con [versionamento semantico](https://semver.org/lang/it/).

## [Unreleased]

## [1.0.0] — 2026-09-19

Prima versione: quella discussa in sede di tesi.

### Aggiunto

**Dalla nuvola al deck.** Le fondamenta, costruite prima che il lavoro passasse per le pull
request.

- Pipeline in undici passaggi da nuvola di punti (`.pcd`, `.ply`, `.xyz`) a deck Abaqus `.inp`,
  con i parametri e le misure di qualità di ogni passaggio salvati nella corsa.
- Motore di sweep con registro delle corse, fronte di Pareto e impronta della configurazione.
- Prior geometrico del telaio (step 12) e modelli parametrici della struttura.

**Ingresso, vista e interfaccia degli step.**

- Una corsa nasce da una nuvola, non da uno yaml (#14).
- L'artefatto si guarda dall'inizio alla fine (#16).
- I cinque gruppi dell'interfaccia: esito, attesa, pannello dei parametri, storico (#23).
- I fine riga che `cmd.exe` e la shell pretendono negli avviatori (#24).
- I due capi del tubo verso il worker dichiarano la propria codifica (#26).
- Le guardie sulle letture dicevano «troncato» e non coprivano «storto» (#27).
- Applicato l'audit ponytail, sette tagli su otto, con un giro di review (#28).

**Carichi e analisi integrata.** Lo strato tolto prima della 1.0.0 — vedi «Rimosso».

- L'analisi strutturale dell'as-built: solutore, verdetti e verifiche di norma (#3).
- Carichi posizionati su selettori geometrici dichiarati (#13).
- Un ramo solo, con i carichi e la vista continua (#22).
- La pressione sull'as-built, e la guardia che la smentisce (#81).
- Carichi distribuiti: `OP=NEW`, segno della risultante, guardia sul vincolo (#109).
- La pressione permanente agisce anche nei passi dei carichi distribuiti (#121).
- La sonda su `TRVEC` entra nel tronco invece di morire su un ramo (#149).

**Validazione e qualità del maglio.**

- Registro delle soglie di verifica (#49).
- Ciò che non è un numero non passa per buono (#51).
- Il patch test, nelle due varianti A e B (#52).
- Il tetraedro quadratico, per la prima volta (#53).
- La mensola confrontata con la teoria delle travi (#54).
- L'ordine delle colonne del `.frd`, verificato contro CalculiX (#56).
- La tensione sulla mensola, e una divergenza da Benzley (#57).
- NAFEMS FV52 e LE10, i due benchmark per solidi (#58).
- Gli oracoli per le cinque grandezze rimaste senza controllo (#59).
- L'incertezza sui materiali propagata, misurando le leggi (#60).
- Il nono punto dello scaled Jacobian, e due guardie rese oneste (#61).
- Il sesto verdetto: l'ampiezza dello spostamento (#62).
- Cinque guardie scritte in negativo, e due premesse smentite (#63).
- La gravità si ripartisce diversamente sul tetraedro quadratico (#64).
- La suite gira da sola, e i benchmark non possono sparire in silenzio (#65).
- I conteggi discreti non si asseriscono su un maglio generato (#67).
- Una sezione senza spessore si dichiara, non schianta (#69).
- Lo scarto fra C3D4 e C3D10 sul telaio reale (#70).
- La GCI, e le due cose che misurando si scoprono (#72).
- L'errore geometrico guadagna il segno (#74).
- Il settimo verdetto: quanta massa i modi catturano (#76).
- Il numero di modi lo fissa la norma, non l'operatore (#77).
- I sette documenti di ricerca entrano nel repository (#78).
- I tre documenti dell'interfaccia rimasti sui rami (#79).
- I quattro controlli della vista che il tronco non aveva (#80).
- Il tronco torna pulito, e resta pulito (#82).
- Numeri incoerenti nei documenti di validazione (#104).
- Il cancello di finitezza, e il segno dichiarato nello scarto (#105).
- Accenti italiani veri nei tre documenti rimasti in ASCII (#106).
- La convergenza dichiara le uscite degeneri invece di crollare (#107).
- Passo a due cifre, `.frd` troncato, picco sui casi parziali (#108).
- I conteggi della scala, e il controllo dei riferimenti (#113).
- Provenienza: `git` con codice d'uscita diverso da zero non è un albero pulito (#114).
- Risoluzione end-to-end con CalculiX vero su C3D10 (#115).
- I rilievi di codice raccolti nella revisione (#116).
- L'etichetta italiana al posto della chiave nelle grandezze confrontate (#117).
- Due reperti che dicevano più di quanto reggono (#118).
- Un maglio vuoto è rifiutato anche dall'esportazione del modello (#122).
- Riferimenti al codice per nome invece che per riga (#123).
- I tre conteggi della suite, rimisurati (#126).

**Il repository dice cos'è a chi lo apre.**

- Il repository dice cos'è a chi lo apre dal link (#148).
- Le istruzioni per gli agenti dicono dove il verde mente (#150).
- La licenza MIT rende riusabile quello che `PRODUCT.md` promette (#151).
- Terminologia del progetto uniformata (#152).
- Revisione dei testi di progetto (#153).
- L'ago si cerca nella sezione delle metriche, non nel documento (#154).
- La specifica elenca requisiti da coprire, non difetti altrui (#155).
- Il perimetro del prodotto si chiude sul deck `.inp` (#156).
- Il perimetro dichiarato, e il predefinito che lo rispetta (#157).
- Via la skill di terzi, e con lei tutte e 144 le vulnerabilità (#158).

**Rifinitura dell'interfaccia.**

- La linea dell'analisi si nasconde dietro un interruttore (#160).
- Lo storico annulla anche le esecuzioni, e il modello si legge sotto la pipeline (#168).
- Le rifiniture rinviate: etichette e modello separati, misura della superficie, verifiche a mano
  (#169).
- Gli stati spiegati, i blocchi etichettati, rimedio ai rifiuti (#170).
- Titolo dello step a 16 px, registro a 14, scorciatoia bilanciata (#172).
- Passata di rifinitura sull'intero percorso (#176).
- I gesti della tela adattati al trackpad e a macOS (#177).
- La pagina adattata a portatili e monitor da PC (#178).
- Il numero di prima accanto a quello cambiato (#180).
- Le nuvole si decimano a fine corsa, non al primo clic (#181).
- Le normali le calcola il server, non il browser (#182).
- Il vuoto dove il senso si spezza, il peso dove sta la priorità (#183).
- La tela si tiene i gesti del dito (#184).
- La pinza non può esplodere, e il terzo dito non la congela (#185).

**Il deck nudo e la geometria STEP.**

- La decisione scritta: il deck va nudo e il prior scrive STEP (#186).
- Geometria `.step` dal prior geometrico, accanto al deck (#191).

**Immagini della corsa e programma da scrivania.**

- La striscia del PNG salvato porta i parametri dello step in figura (#193).
- La camera è un riferimento della corsa; un'immagine per step in un gesto (#194).
- Cartiglio a destra nel PNG salvato (#195).
- Grafo del repository committato in `graphify-out/` (#196).
- Specifica e piano per MeshRec come programma (#197).
- L'immagine salvata va nella cartella delle immagini della corsa (#198).
- MeshRec come programma da scrivania: finestra propria, icona, schermata «Informazioni su»,
  `MeshRec.app` per macOS e collegamento per Windows (#199).
- `CITATION.cff`, endpoint `/api/info`, piè di pagina con versione, licenza e come citare.

### Rimosso

- Il solutore integrato e le verifiche di norma (2 settembre 2026): l'analisi si fa in Abaqus.
  Escono i sei moduli del solutore, le rotte che li servivano e la schermata dell'analisi.
- Carichi e selettori: il deck torna al solo passo di gravità (#190).
- Il deck `.inp` è nudo, via la sezione di analisi e il pannello del materiale (#192): materiali,
  carichi e selettori si assegnano in Abaqus/CAE (8 settembre 2026).

[Unreleased]: https://github.com/maeurong/meshrec/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/maeurong/meshrec/releases/tag/v1.0.0
