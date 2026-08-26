# Quanti modi servono per il 90% di massa partecipante

Misurato il 26/08/2026. Rimisurabile con
`meshrec/docs/fase-7-cantiere/modi-per-la-normativa.py`.

[#75](https://github.com/maeurong/Tesi/issues/75) aveva trovato il difetto e
si era fermato lì: coi venti modi che il caso del telaio chiedeva, la
direzione **verticale** cattura l'**87,46%** della massa partecipante, sotto
il 90% che EN 1998-1 §4.3.3.3.1(3) chiede (NTC 2018 §7.3.3.1 riporta lo stesso
criterio). Le altre due direzioni passavano.

Questo documento risponde alla domanda successiva — **quanti modi servono** —
e giustifica il predefinito che ne è uscito.

## Perché la verticale restava indietro

Non è un caso che mancasse proprio lei. Su un telaio il moto **verticale**
richiede deformazione **assiale** delle colonne, molto più rigida della
flessione: i modi che portano massa in z stanno quindi a frequenza alta. Con
venti modi lo spettro si ferma a **681,9 Hz** e quei modi non ci sono ancora
dentro. Le direzioni orizzontali sono invece governate dai primi modi
flessionali, che arrivano subito — per questo x e y erano già oltre il 90%.

Ipotesi dichiarata **prima** di misurare, e la misura la conferma: a 40 modi
lo spettro arriva a **1752,8 Hz** e la verticale sale a 93,98%.

## La misura

Due corpi, entrambi rimagliati dalla superficie riparata della propria corsa,
C3D4, stessa configurazione di maglio (`min_ratio` 1,8, `nobisect`):

- **telaio** — `runs/lab_telaio_v2`, calcestruzzo C25/30, 14.103 nodi e 51.913
  tetraedri;
- **ritaglio** — `runs/lab_crop`, muratura, 13.264 nodi e 50.800 tetraedri.
  La sua corsa non ha un passo modale: gliene è stato aggiunto uno **solo per
  misurare**, senza riscrivere alcun artefatto.

La colonna è la **direzione traslazionale peggiore**, che è sempre la
verticale. Le rotazionali restano fuori: unità diverse, e un totale
disponibile che dipende dal polo.

| modi | telaio | ritaglio |
|---:|---:|---:|
| 20 | 87,46 % | 87,96 % |
| 24 | 88,25 % | 88,57 % |
| 28 | 88,28 % | 88,82 % |
| 31 | 88,31 % | 88,93 % |
| **32** | **90,83 %** | **90,87 %** |
| 36 | 90,87 % | 90,89 % |
| **37** | **93,96 %** | 90,89 % |
| **38** | 93,97 % | **94,42 %** |
| 40 | 93,98 % | 94,43 % |
| 44 | 94,17 % | 94,44 % |
| 48 | 94,48 % | 94,78 % |

## Il fatto che decide: la frazione sale a gradini, non liscia

I modi entrano in **coppie**, e ogni coppia porta la sua quota di massa in un
colpo solo. La curva è quindi fatta di pianerottoli separati da salti, e
questo cambia completamente come va scelto un valore.

- Sotto **32** nessuno dei due corpi arriva al 90%.
- A **32** entrambi scavallano, ma su un pianerottolo **sottile**: 90,83% e
  90,87%, cioè 0,83 e 0,87 punti di margine, che tengono fino a 36-37.
- Il pianerottolo **largo** — circa 94% — comincia a **37 sul telaio** e a
  **38 sul ritaglio**.

Quel disallineamento è il risultato più importante del documento. **Il bordo
del gradino si sposta col maglio**, e i magli cambiano: TetGen e gmsh
producono maglie diverse su Linux x86-64 e macOS arm64 a parità di versione e
di ingresso ([#66](https://github.com/maeurong/Tesi/issues/66)). Un predefinito
appoggiato sul bordo di un gradino mobile passa sulla macchina dove è stato
tarato e fallisce altrove — che è esattamente l'errore già commesso e bocciato
dalla CI in [#72](https://github.com/maeurong/Tesi/issues/72), dove una soglia
tarata su macOS non reggeva su Linux.

## La scelta: 40, non 32

Il **32** è il più piccolo che regge, ed è la scelta che lo stile della casa
farebbe di norma (è così che è stato fissato `set_tolerance_factor`). Qui non
si può: sta sul bordo, con meno di un punto di margine, e il bordo si muove.

Il **40** sta dentro il pianerottolo largo su **entrambi** i corpi, con circa
quattro punti di margine e **otto modi sopra lo scavallamento**. Perché scenda
sotto il 90% servirebbe che l'intera curva slittasse di otto modi, contro i
zero-e-uno di scarto misurati fra i due magli disponibili.

Il costo è trascurabile: sul telaio **9,9 s** contro i 4,9 s dei venti modi.

## Che cosa questa misura non dimostra

**I due corpi non sono indipendenti.** `lab_crop` è il ritaglio della stessa
scena che contiene il telaio, e scalare il modulo elastico non cambia le forme
modali — il calcestruzzo a 31.500 MPa e la muratura a 1.500 MPa danno
frequenze diverse ma **la stessa** ripartizione di massa. Che le due colonne
concordino a mezzo punto era **atteso**, e non va contato come una seconda
conferma.

Il 40 è quindi un punto di partenza tarato su **una scena sola**, non una
costante universale: su una struttura con un altro rapporto fra rigidezza
assiale e flessionale può non bastare.

È precisamente per questo che il predefinito **non sostituisce** il verdetto.
`massa_modale` (`meshrec/src/meshrec/core/solve.py`) continua a leggere la
frazione dal `.dat` e a nominare la direzione peggiore: il predefinito fa
partire bene, il verdetto dice se è bastato.

## Che cosa è cambiato nel programma

- `Modale.modi` ha un predefinito, **40**, prima non ne aveva alcuno. Non
  contraddice la regola che vieta i predefiniti indovinati: quella riguarda i
  parametri **meccanici** (modulo, Poisson, densità, carichi), che nessun dato
  del rilievo suggerisce. Il numero di modi è un parametro di
  **discretizzazione**, come `set_tolerance_factor`, e come quello porta un
  predefinito misurato.
- `casi/lab_telaio.yaml` non scrive più `modi: 20`: dichiara `modale: {}` ed
  eredita il predefinito.

**Conseguenza da dichiarare.** L'impronta di `casi/lab_telaio.yaml` passa da
`037cf06…` a `6731eab…`, e `037cf06…` era anche l'impronta delle corse
congelate `lab_telaio_v2` e `lab_telaio_v3_pesata`: il file di caso **non le
riproduce più**. Le corse restano intatte e citabili con la propria
configurazione. I risultati statici pubblicati non ne risentono — chiedere più
modi non cambia né i passi statici né le frequenze già estratte, aggiunge solo
le successive — ma l'identità di impronta fra il caso e la corsa è rotta, e
una corsa nuova da quel caso sarà un esperimento diverso.

Nessuna delle otto corse in `runs/` cambia impronta: verificato ricalcolandole
tutte prima e dopo la modifica.
