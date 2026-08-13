# Fase 1 — Il margine di `tet.min_ratio`

- **Data di esecuzione:** 13 agosto 2026
- **Ambiente:** Windows 11, stessa macchina delle misure di `fase-1-esiti.md`
- **Superficie di partenza:** `06_repaired.ply`, la superficie riparata prodotta
  dalla corsa archiviata su `muro_generato.ply` (`meshrec/runs/muro/`)
- **Parametro sotto misura:** `tet.min_ratio`, il rapporto raggio-spigolo
  massimo imposto a TetGen nello step 9

## Che cosa è stato misurato e come

Il valore predefinito di `tet.min_ratio` è **1,8**. È un debito noto: fu scelto
perché durante lo sviluppo 1,6 falliva e 1,8 no, ma quei tentativi non sono mai
stati registrati — né i numeri, né a quale distanza dal fallimento si trovasse
il valore scelto. «Il margine è sottile» era un'impressione, non una misura.
Questo documento la sostituisce con una tabella.

Il metodo sfrutta la ripresa della pipeline da uno step intermedio
(`--from-step 9`), che evita di rifare gli step 1–8 per ogni prova. Gli
artefatti della corsa documentata in `fase-1-esiti.md` sono stati copiati da
`runs/muro/` (archivio, mai scritto) in una cartella di lavoro dedicata,
`runs/minratio/`: `04_normals.ply` (la nuvola con normali, da cui la ripresa
ricava la spaziatura) e `06_repaired.ply` (la superficie chiusa, l'ingresso
vero e proprio dello step 9). Nella pratica è stato necessario copiare anche
`02_segmented.ply`: la ripresa da `from_step=9` ricarica comunque la nuvola
segmentata come riferimento fisso per il calcolo dell'errore geometrico, anche
se lo step 7 che lo userebbe non viene rieseguito — se il file manca, la
ripresa fallisce subito con un `ValueError` prima ancora di arrivare a TetGen.
Non è un dettaglio da tesi, ma va detto per chi ripeterà la misura: i due file
citati nel testo della pipeline non bastano da soli.

Con questa preparazione, **tutte e sei le corse condividono esattamente la
stessa superficie di partenza** — stessi 116.967 vertici e 233.930 triangoli
di `06_repaired.ply`, nessuna rigenerazione di mesh fra una prova e l'altra.
È il punto che rende il confronto pulito: le differenze nei risultati vengono
solo da `tet.min_ratio`, non da rumore introdotto a monte.

Per ciascuno dei sei valori (1,4 · 1,6 · 1,7 · 1,8 · 2,0 · 2,5) la sequenza è
stata: scrivere il valore in `runs/minratio/config.yaml`, eseguire
`uv run meshrec run runs/minratio/config.yaml --from-step 9` dalla cartella
`meshrec/`, e leggere `runs/minratio/metrics.json` prima della prova
successiva. Una corsa a **1,8** è stata ripetuta come controllo, per verificare
che la preparazione riproducesse esattamente il riferimento archiviato prima
di fidarsi delle altre cinque: ha dato 420.547 nodi, 1.752.795 tetraedri, 0
elementi invertiti, mediana del diedro minimo 38,26°, 303.580 punti di
Steiner, nessuna saturazione — identico al riferimento in ogni cifra
significativa (il tempo, 44,57 s contro 43,77 s, rientra nella variabilità già
documentata fra 40,2 e 44,3 s). La preparazione è quindi verificata corretta.

## Risultati

| `min_ratio` | Esito | Nodi | Tetraedri | Tempo (s) | Punti di Steiner | Saturato | Invertiti | Volume totale (m³) | Diedro min. — minimo | Diedro min. — mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| 1,4 | **fallito** | — | — | — | — | — | — | — | — | — |
| 1,6 | **fallito** | — | — | — | — | — | — | — | — | — |
| 1,7 | riuscito | 452.967 | 1.923.892 | 50,98 | 336.000 | falso | 0 | 53,873 | 0,0029° | **39,11°** |
| 1,8 (predefinito) | riuscito | 420.547 | 1.752.795 | 44,57 | 303.580 | falso | 0 | 53,873 | 0,0025° | 38,26° |
| 2,0 | riuscito | 372.068 | 1.498.226 | 36,60 | 255.101 | falso | 0 | 53,873 | 0,0022° | 36,84° |
| 2,5 | riuscito | 301.362 | 1.134.074 | 27,66 | 184.395 | falso | 0 | 53,873 | 0,0015° | 34,20° |

Per le quattro corse riuscite lo step 11 ha scritto il deck (`wall_model.inp`
e `wall_model.vtu`), con volume e massa coerenti fra loro entro l'ultima cifra
(massa 96,97 t in tutti e quattro i casi, come atteso da mesh di volume diverse
ma derivate dalla stessa superficie chiusa).

Per 1,4 e 1,6 TetGen si è interrotto con lo stesso identico messaggio a parte
il valore del parametro, riportato qui verbatim (caso 1,4):

```
RefinementFailedError: TetGen si e' interrotto con min_ratio=1.4: il vincolo raggio-spigolo puo' essere troppo severo per questa geometria, il raffinamento non converge. Alza min_ratio (valori piu alti = elementi meno regolari ma raffinamento che termina) e riprova. Errore originale di TetGen: Internal TetGen error within `split_segment`.
```

Il caso 1,6 differisce solo per `min_ratio=1.6` nel testo. In entrambi i casi
`metrics.json` resta un dizionario vuoto: lo step 9 non scrive nulla quando
fallisce, coerentemente con quanto documentato per la corsa originale.

## Lettura

**Il confine non è dove l'aneddoto lo collocava.** L'unica cosa nota finora era
che 1,6 falliva e 1,8 no, senza sapere se il limite vero fosse vicino a 1,6, a
metà strada, o vicino a 1,8. La misura lo restringe: **1,7 converge**, quindi
il confine fra fallimento e convergenza cade nell'intervallo aperto-chiuso
(1,6; 1,7] su questa superficie — non è stato misurato un punto intermedio fra
1,6 e 1,7, quindi non si può dire di più senza un'altra prova mirata lì dentro.

**Il margine di 1,8 esiste, ma è quasi tutto raccolto in quel primo scalino.**
Dal predefinito al valore riuscito più basso misurato (1,7) c'è un solo passo
di 0,1; dal predefinito al fallimento più vicino noto (1,6) ce ne sono due,
0,2 in tutto — ma la metà di quello spazio, fra 1,6 e 1,7, è già oltre il
confine di convergenza. In altre parole 1,8 non è "il minimo che regge": lo è
già 1,7. Il margine reale che 1,8 porta sopra il punto di rottura più vicino
misurato è di 0,2, non di "poco", ma nemmeno ampio: un solo decimo lo separa
dal valore più basso già verificato funzionante, e un altro decimo sotto
quello si finisce nel fallimento.

**Che cosa si guadagna alzando il valore.** Il pattern è netto e monotono su
tutte e quattro le corse riuscite: alzare `min_ratio` riduce nodi, tetraedri,
punti di Steiner e tempo di calcolo — da 1,7 a 2,5 i tetraedri scendono da
1.923.892 a 1.134.074 (-41%) e il tempo da 51 a 28 secondi (-46%). Il prezzo è
una mesh via via meno regolare: la mediana del diedro minimo scende da 39,11°
a 34,20°, quasi cinque gradi persi. Il volume totale resta invariato in tutte
le corse (53,873 m³, la geometria della superficie chiusa non cambia), e non
compaiono mai elementi invertiti nell'intervallo misurato: la degradazione è
di qualità, non di validità topologica.

**Che cosa si guadagna abbassando fino a dove regge.** Scendere da 1,8 a 1,7 —
l'unico passo verso il basso che regge, fra quelli misurati — migliora la
mediana del diedro minimo da 38,26° a 39,11° e produce più nodi (452.967
contro 420.547, +7,7%) e più tempo di calcolo (51,0 s contro 44,6 s, +14%). È
un guadagno di qualità modesto per un costo di macchina non trascurabile, e va
pagato sapendo che un ulteriore passo di 0,1 verso il basso (1,6) fa fallire
il raffinamento su questa stessa superficie. Non c'è margine per spingersi
oltre senza nuova misura.

**In sintesi:** 1,8 non è il valore minimo possibile — 1,7 già converge e dà
una mesh leggermente più regolare — ma è vicino al limite: un solo decimo di
distanza dal valore più basso verificato, due dal fallimento più vicino noto.
Chi ha bisogno di mesh più leggere e più veloci può salire fino a 2,5 (e oltre,
non misurato qui) pagando in regolarità degli elementi; chi ha bisogno di
qualità migliore ha un solo gradino di manovra verso il basso, 1,7, prima del
muro.

## La scansione di laboratorio: lo stesso sweep su `lab_frame.pcd`

- **Data di esecuzione:** 13 agosto 2026
- **Ambiente:** stessa macchina delle misure precedenti in questo documento
- **Superficie di partenza:** `06_repaired.ply` della corsa archiviata
  `runs/lab_crop/` (ritaglio a box di `lab_frame.pcd`, scansione reale di un
  singolo muro di laboratorio) — 213 154 vertici, 426 600 triangoli
- **Parametro sotto misura:** `tet.min_ratio`, lo stesso dell'esperimento
  gemello sopra

Questa sezione è il gemello di quella precedente, con lo scopo di metterne
alla prova la conclusione su una geometria diversa. `fase-1-debito.md` ipotizza
che il fallimento di TetGen su questa scansione non dipenda dalla taratura del
parametro ma dalla qualità della superficie riparata che entra nello step 9.
È un'ipotesi ragionevole, sostenuta da un solo confronto — sei valori da 1,8 a
4,0, tutti falliti — e da due indizi mai spiegati nei dettagli: un volume
racchiuso negativo e un rapporto d'aspetto massimo di 34 972,8. Qui la si
verifica fino in fondo: allargando lo sweep a valori molto più laschi
(fino a 12,0, quasi sette volte il predefinito), e scomponendo i due indizi in
numeri verificabili invece di lasciarli come sintomi.

### Metodo

Identico al gemello: ripresa della pipeline da `--from-step 9`, stessa
superficie di partenza per tutte le corse. Da `runs/lab_crop/` (archivio, mai
scritto) sono stati copiati in `runs/minratio_lab/`: `02_segmented.ply`,
`04_normals.ply`, `06_repaired.ply` e `config.yaml`, con `run.out_dir` corretto
a `runs\minratio_lab`. Il primo file, `02_segmented.ply`, non serve alla
tetraedrizzazione in sé ma è comunque necessario: la ripresa da `from_step=9`
ricarica sempre la nuvola segmentata come riferimento fisso dell'errore
geometrico, esattamente come documentato per il gemello — qui pesa 101 MB,
molto più che nel caso sintetico, perché la nuvola segmentata reale è più
grande.

Per ciascuno dei sei valori di `tet.min_ratio` (**1,8 · 2,5 · 3,0 · 4,0 · 6,0 ·
12,0**) la sequenza è stata: scrivere il valore in
`runs/minratio_lab/config.yaml`, eseguire
`uv run meshrec run runs/minratio_lab/config.yaml --from-step 9` dalla
cartella `meshrec/`, leggere `runs/minratio_lab/metrics.json`. La prima corsa,
a 1,8, riproduce esattamente il fallimento già registrato in
`fase-1-debito.md` e in `fase-1-esiti-lab-frame.md` per lo stesso valore sulla
stessa superficie — stesso messaggio, stesso punto interno di TetGen — e
funge da controllo che la preparazione sia corretta, come la ripetizione a 1,8
nel gemello.

### Risultati dello sweep

| `min_ratio` | Esito |
|---|---|
| 1,8 (predefinito) | **fallito** |
| 2,5 | **fallito** |
| 3,0 | **fallito** |
| 4,0 | **fallito** |
| 6,0 | **fallito** |
| 12,0 | **fallito** |

Le sei corse falliscono con lo stesso messaggio, identico a parte il valore
del parametro riportato nel testo (caso 12,0, il più lasco provato):

```
RefinementFailedError: TetGen si e' interrotto con min_ratio=12.0: il vincolo raggio-spigolo puo' essere troppo severo per questa geometria, il raffinamento non converge. Alza min_ratio (valori piu alti = elementi meno regolari ma raffinamento che termina) e riprova. Errore originale di TetGen: Internal TetGen error within `split_subface`.
```

In ogni caso `metrics.json` resta un dizionario vuoto, come nel gemello quando
la tetraedrizzazione fallisce. Nessuna delle sei corse ha prodotto
`09_volume.vtu` né un deck Abaqus: lo step 9 non arriva mai a restituire una
mesh.

Vale la pena notare, senza forzarne il peso, che il punto interno di rottura
di TetGen qui è sempre `split_subface`, mentre nel caso del muro sintetico a
1,4 e 1,6 era `split_segment`: sono subroutine diverse di TetGen, il che è
coerente con — ma non prova da solo — una causa di fondo diversa dal semplice
vincolo raggio-spigolo troppo severo.

**12,0 è un vincolo praticamente inerte** — quasi sette volte il predefinito,
ben oltre il valore di TetGen stesso (2,0) e ben oltre qualunque valore che un
progetto userebbe per una mesh accettabile — e fallisce in modo identico a
1,8. Se il raffinamento non converge nemmeno lasciando che gli elementi siano
quasi arbitrariamente irregolari, il vincolo raggio-spigolo non è la causa:
può al più essere un fattore che accelera un fallimento che accadrebbe comunque.

### Diagnosi della superficie (sola lettura, nessuna correzione)

Misure dirette su `runs/minratio_lab/06_repaired.ply`, la stessa superficie di
tutte le sei corse sopra, con uno script Python usa-e-getta (open3d + numpy per
i controlli geometrici, pymeshlab per le autointersezioni; niente modifiche al
file, niente tentativi di riparazione). Confronto di riferimento:
`runs/muro/metrics.json`, la stessa superficie usata nel gemello di questo
documento.

**Il volume è negativo, e non per rumore: l'intera superficie ha
un'orientazione unica ma rovesciata.**

| grandezza | `lab_frame` (`06_repaired.ply`) | `muro_generato` (riferimento) |
|---|---|---|
| volume con segno | **−173 282 926,9 mm³ (−0,173 m³)** | +53 872 970 753,7 mm³ (+53,873 m³) |
| volume dopo aver invertito tutti i triangoli | +173 282 926,9 mm³ | — (non misurato, non serve) |
| spigoli interni condivisi controllati | 639 900 | — |
| spigoli con verso incoerente fra le due facce adiacenti | **0** | — |
| `is_edge_manifold` | vero | — |
| `is_vertex_manifold` | vero | — |

Il volume con segno calcolato direttamente dai vertici e dalla connettività
(somma di v₀·(v₁×v₂)/6 su tutti i triangoli) riproduce esattamente il
−173 282 926,9485 mm³ già presente in `runs/lab_crop/metrics.json`: non è un
artefatto del calcolo dello step 7, è la geometria reale della mesh. Capovolgendo
il verso di tutti e 426 600 i triangoli il volume diventa positivo e di segno
opposto esatto (+173 282 926,9 mm³): il segno dipende per intero dal verso di
avvolgimento, non da un errore di scala o da vertici scambiati.

Il controllo decisivo è quello combinatorio: su 639 900 spigoli interni
condivisi da due triangoli, **zero** sono percorsi nello stesso verso dalle due
facce che li toccano — cioè l'avvolgimento è **globalmente coerente** su tutta
la superficie, non un mosaico di patch invertite a caso. Insieme a
`is_edge_manifold` e `is_vertex_manifold` entrambi veri, il quadro è netto:
`06_repaired.ply` è una superficie chiusa, topologicamente pulita, a
orientazione singola e coerente — ma quella singola orientazione è quella
sbagliata. Le normali puntano verso l'interno del solido, non verso l'esterno.
È esattamente il caso descritto nel mandato: **la superficie è rovesciata**, e
lo è nella sua interezza, non a chiazze.

**Le schegge estreme sono poche, non il grosso della mesh.**

| soglia | triangoli | frazione del totale (426 600) |
|---|---|---|
| aspect ratio > 100 | 1 077 | 0,25% |
| aspect ratio > 1 000 | 108 | 0,03% |
| area quasi nulla (< 1 · 10⁻⁶ mm²) | 13 | 0,003% |
| area < 1 · 10⁻⁹ mm² | 0 | 0% |

Il rapporto d'aspetto massimo, 34 972,8, e la mediana, 1,399, coincidono con
quelli già riportati in `runs/lab_crop/metrics.json` — confermano che questa è
la stessa misura, non una ricalcolata diversamente. Ma il massimo è un valore
isolato: solo 1 077 triangoli su 426 600 (0,25%) superano un rapporto
d'aspetto di 100, e appena 108 (0,03%) superano 1000. Il 99,75% dei triangoli
ha quindi un rapporto d'aspetto ragionevole. Confrontato con il muro
sintetico, dove il rapporto d'aspetto massimo è 3 968,08 su una mediana quasi
identica (1,394), qui il massimo è circa 8,8 volte più alto — ma resta un
singolo valore estremo, non la descrizione di come sia fatta la mesh nel suo
insieme. Le aree quasi nulle sono ancora più rare: appena 13 triangoli sotto
1 µm², nessuno sotto 1 nm².

**Nessuna autointersezione.** Il filtro
`compute_selection_by_self_intersections_per_face` di pymeshlab, eseguito
sull'intera superficie, seleziona **0 triangoli su 426 600 (0,00%)**. La
superficie non si autointerseca in nessun punto misurabile da questo
controllo.

Non è stato possibile misurare un secondo controllo indipendente di
autointersezione: `open3d.geometry.TriangleMesh.is_self_intersecting()` (e con
esso `is_watertight()`, che lo richiama internamente) non ha terminato entro
600 s in primo piano, per due tentativi separati, ed è stato interrotto. Non è
un dato nascosto per comodità: è un limite dichiarato. Il controllo pymeshlab
sopra, più mirato e più veloce, resta comunque una risposta diretta alla
domanda del mandato («quante autointersezioni»), solo non doppiamente
verificata da una seconda libreria.

### Lettura

**La parte sulla taratura del parametro è confermata, e in modo più netto di
quanto il debito registrasse.** Il debito noto riferisce che ogni valore
provato fra 1,8 e 4,0 falliva, senza elencare quali né in quale numero. Questo
sweep li misura e ne aggiunge due molto più laschi, 6,0 e 12,0 — l'ultimo
quasi sette volte il predefinito, un vincolo praticamente inerte — e falliscono
in modo identico, stesso errore interno di TetGen, stesso punto di rottura
(`split_subface`). Se un vincolo raggio-spigolo così permissivo da accettare
elementi quasi arbitrariamente irregolari non basta a far convergere il
raffinamento, **`tet.min_ratio` è escluso come causa**: non è un problema di
taratura, per nessun valore ragionevole del parametro. Su questo punto la
diagnosi del debito regge, ed è ora una misura, non più un'inferenza da sei
soli valori vicini fra loro.

**La parte sulla «qualità della superficie» era vaga, e i numeri la precisano
in una direzione specifica.** «La qualità della superficie riparata è scarsa»
descrive male ciò che si misura qui. La superficie non è invasa da schegge
(99,75% dei triangoli ha rapporto d'aspetto sotto 100), non ha
autointersezioni misurabili, ed è un manifold di spigoli e vertici pulito,
con un'unica orientazione coerente su 639 900 spigoli interni controllati:
per quasi ogni criterio comune di qualità di mesh, `06_repaired.ply` non è
messa peggio del muro sintetico in modo drammatico. Il difetto che davvero
salta ai numeri è uno solo, preciso, e diverso da «qualità generica»: **la
superficie è rovesciata**. Le sue 426 600 facce puntano tutte, in modo
consistente, verso l'interno del volume che racchiudono, e il volume con
segno che ne risulta, −173 282 926,9 mm³, capovolge esattamente in
+173 282 926,9 mm³ se si inverte l'avvolgimento di ogni triangolo. Non è
un'inferenza dal solo segno del volume: la coerenza globale dell'avvolgimento
(zero spigoli incoerenti su 639 900) esclude che sia rumore o un mosaico di
patch mal orientate, e conferma che è un singolo difetto di orientazione
dell'intera superficie.

**Che cosa questo non dimostra.** Non è stato verificato — e non doveva
esserlo in questo lavoro, che misura e non ripara — se correggere
l'orientazione permetta a TetGen di convergere: resta un'ipotesi, per quanto
molto più precisa e più azionabile di «la qualità è scarsa». È altrettanto
possibile che l'inversione sia correlata ad altro (per esempio a come
MeshFix ha richiuso i 41 cammini di bordo aperti della Fase 1, di cui due
molto estesi) piuttosto che esserne la causa diretta del fallimento di
TetGen; il messaggio di TetGen non localizza il punto interno in cui si
arrende, quindi nessuna delle due letture è verificabile da qui.

**In sintesi: la diagnosi del debito è confermata nella sua metà negativa
(non è `tet.min_ratio`) e va precisata nella sua metà positiva.** Non è «la
qualità della superficie», espressione che i numeri non sostengono nel senso
comune del termine — schegge, autointersezioni, non-manifold. È un difetto
singolo, misurato con tre controlli indipendenti che convergono sullo stesso
punto (segno del volume, capovolgimento esatto sotto inversione, coerenza
globale dell'avvolgimento): la superficie riparata di `lab_frame.pcd` è
rovesciata. La prima cosa da provare in Fase 2, prima di toccare `min_ratio` o
il remeshing dello step 8, è correggere l'orientazione e rieseguire lo step 9
sulla stessa superficie.

### La prova: superficie raddrizzata e step 9 rieseguito

La prova indicata nel paragrafo precedente è stata eseguita subito dopo, ed è
il caso in cui vale la pena aver scritto l'ipotesi in forma falsificabile: il
risultato non conferma né smentisce, precisa.

Il metodo è minimo. Sulla copia di lavoro `runs/minratio_lab/06_repaired.ply`
— mai sull'archivio — l'avvolgimento di tutti i 426 600 triangoli è stato
capovolto scambiando due dei tre indici di ciascuna faccia, senza toccare né i
vertici né la connettività: la geometria è identica, cambia solo il verso. Il
volume con segno passa da −173 282 926,9 mm³ a +173 282 926,9 mm³, e il file
riletto da disco conferma il valore. Poi lo step 9 è stato rieseguito con
`--from-step 9`, come in tutte le misure di questo documento.

| Superficie | `min_ratio` | Esito |
|---|---|---|
| rovesciata (originale) | 1,8 – 12,0 | fallita a ogni valore, vedi tabella sopra |
| **raddrizzata** | 1,8 | fallita |
| **raddrizzata** | 4,0 | fallita |
| **raddrizzata** | 6,0 | fallita |
| **raddrizzata** | 8,0 | fallita |
| **raddrizzata** | 10,0 | fallita |
| **raddrizzata** | **12,0** | **riuscita** — 692 617 nodi, 2 230 860 tetraedri, 186,4 s |
| rovesciata (controllo, rieseguito) | 12,0 | fallita, stesso `split_subface` |

L'ultima riga è il controllo che regge tutto il resto: la stessa superficie
non raddrizzata, allo stesso `min_ratio` 12,0, con la stessa configurazione e
nella stessa cartella, fallisce. L'unica variabile fra la penultima riga e
l'ultima è il verso dei triangoli.

**L'orientazione è quindi necessaria ma non sufficiente.** Raddrizzarla non
basta da sola — a 1,8, il predefinito, il fallimento resta identico — ma senza
raddrizzarla non converge nemmeno il vincolo più lasco provato. Le due
condizioni servono entrambe, e il confine di convergenza sulla superficie
raddrizzata cade fra 10,0 e 12,0: un valore enorme, circa sette volte il
predefinito e sei volte quello del muro sintetico.

**Il modello che ne esce non è utilizzabile, ed è la parte più importante di
questo risultato.** La mesh converge, non ha elementi invertiti e produce un
deck completo, ma la mediana dell'angolo diedro minimo vale 25,33° contro i
38,26° del muro sintetico, e il minimo scende a 7,5 · 10⁻⁵ gradi: elementi
piatti al limite della degenerazione. L'insieme `BASE` raccoglie 420 nodi su
692 617, cioè un modello di fatto quasi non vincolato, che è il difetto già
registrato nel debito a proposito della tolleranza dei set. Aver ottenuto un
`.inp` non significa aver ottenuto un modello: significa aver misurato dove
sta il confine.

**Che cosa resta da spiegare.** Il fallimento a `min_ratio` ordinari
sopravvive alla correzione dell'orientazione, quindi c'è una seconda causa che
questa prova non tocca. I candidati misurati nella diagnosi sopra sono i 108
triangoli con rapporto d'aspetto oltre 1000 e i 13 di area quasi nulla: pochi
in frazione, ma `split_subface` è la subroutine con cui TetGen inserisce punti
su una faccia di bordo, ed è esattamente ciò che una scheggia estrema rende
mal condizionato. La prova successiva, in Fase 2, è abilitare il remeshing
isotropo dello step 8 — che esiste già ed è solo disabilitato — e rieseguire
lo step 9 a `min_ratio` ordinario su una superficie con l'orientazione
corretta e le schegge rimosse.

### La prova successiva: remeshing isotropo dello step 8

Il paragrafo precedente indicava come prova seguente l'abilitazione del
remeshing isotropo, già presente nella pipeline come step 8 e disabilitato per
predefinito. È stata eseguita, e il risultato è negativo in un modo che vale la
pena documentare per intero: non solo il remeshing non risolve, ma peggiora, e
il modo in cui peggiora dice qualcosa sull'ordine degli step.

Il punto di partenza è la superficie raddrizzata della prova precedente.
Abilitando `simplify.enabled` con `mode: remesh` e i parametri predefiniti, e
riprendendo da `--from-step 8`, la semplificazione porta la superficie da
426.600 a **89.772 triangoli** su 44.740 vertici, con una perdita di volume
racchiuso dello 0,48% — da 173.282.926,9 a 172.449.534,7 mm³. Fin qui è quanto
ci si aspetta da una semplificazione.

Lo step 9, però, fallisce a **ogni** valore di `min_ratio` provato, 1,8 · 2,5 ·
4,0 · 6,0 · 12,0, e fallisce in un punto interno di TetGen diverso da tutti
quelli visti finora: `recoversubfaces` invece di `split_subface`. Non è un
dettaglio di nomenclatura. `recoversubfaces` appartiene al recupero del bordo,
la fase in cui TetGen impone la superficie di ingresso alla triangolazione, e
viene **prima** del raffinamento di qualità. Fallire lì significa che il
vincolo raggio-spigolo non è nemmeno arrivato in gioco: ecco perché anche
12,0, che sulla superficie non semplificata convergeva, qui fallisce.

La diagnosi in sola lettura sulla superficie semplificata spiega il perché:

| grandezza | prima dello step 8 | dopo lo step 8 |
|---|---|---|
| triangoli | 426.600 | 89.772 |
| **autointersezioni** | **0** | **16** |
| manifold di spigoli e vertici | vero | vero |
| spigoli di bordo | 0 | 0 |
| spigolo mediano | 5,38 mm | 6,76 mm |

**Il remeshing ha introdotto sedici autointersezioni dove non ce n'era
nessuna.** È esattamente ciò che il recupero del bordo di TetGen non tollera, e
la superficie resta al tempo stesso chiusa e manifold — cioè supera ogni
controllo che la pipeline sappia fare.

A quel punto la prova naturale è riparare *dopo* aver semplificato, cosa che
la sequenza attuale non prevede: la riparazione è lo step 6 e la
semplificazione lo step 8, quindi nulla ricontrolla la superficie dopo averla
modificata. Applicando MeshFix alla superficie semplificata, fuori pipeline e
in sola lettura sul resto, i sedici triangoli autointersecanti spariscono
(89.772 → 89.754 triangoli, volume invariato allo 0,0003%, orientazione
conservata). Rieseguito lo step 9, il fallimento in `recoversubfaces`
scompare: TetGen torna a fallire in `split_subface`, cioè a superare il
recupero del bordo e a fermarsi nel raffinamento, e lo fa in 7 secondi contro
i minuti delle prove precedenti.

Ma continua a fallire, e stavolta **a ogni valore fra 1,8 e 12,0**, compreso
quel 12,0 che sulla superficie non semplificata convergeva. Il bilancio del
remeshing è quindi negativo su tutta la linea: rimuove un ostacolo che non era
quello bloccante e ne introduce uno nuovo, e la superficie da 89.754 triangoli
è per TetGen più difficile di quella da 426.600 da cui deriva.

**Che cosa se ne ricava, al netto del fallimento.** Primo, una gerarchia di
cause ormai misurata: l'orientazione è necessaria e verificata, le
autointersezioni introdotte dallo step 8 sono un ostacolo reale e rimovibile,
e sotto entrambe resta una terza causa che nessuna delle due prove tocca, che
si manifesta sempre come `split_subface` e che non cede nemmeno a un vincolo
di qualità inerte. Secondo, un difetto di progetto della sequenza: la
riparazione garantisce una superficie chiusa e senza autointersezioni allo
step 6, lo step 7 lo verifica, e poi lo step 8 la modifica senza che nulla
verifichi più nulla. Una semplificazione che rompe le garanzie della
riparazione è precisamente ciò che è appena successo, e la pipeline non ha
modo di accorgersene.

### La terza causa: l'invasione, non la qualità

Le due prove precedenti hanno rimosso due ostacoli reali e lasciato in piedi un
fallimento sempre identico, `split_subface`, insensibile a `min_ratio` fino a
12,0. Questa sezione lo spiega, e la spiegazione parte da un'osservazione che
avrebbe dovuto insospettire prima: **un fallimento che non cambia quando il
vincolo di qualità diventa inerte non può essere causato dal vincolo di
qualità.**

Nel raffinamento di Delaunay una faccia di bordo viene suddivisa per due motivi
distinti. Il primo è la qualità, ed è governato dal rapporto raggio-spigolo,
cioè da `min_ratio`. Il secondo è l'**invasione**: se un vertice cade dentro la
sfera diametrale di una faccia, quella faccia va spezzata comunque, qualunque
sia il vincolo di qualità. La suddivisione per invasione ricorre finché le
facce non scendono sotto la distanza locale fra lembi opposti della superficie.
Se in qualche punto quella distanza è minuscola, la ricorsione scende con lei
fino a dove l'aritmetica non regge più, e TetGen si arrende.

**La misura.** Lo spessore locale del materiale è stato misurato lanciando un
raggio verso l'interno dal baricentro di ciascuno dei 426 600 triangoli e
registrando la distanza del primo impatto sulla superficie opposta. È la scala
che il raffinamento deve risolvere in quel punto.

| spessore locale | `lab_frame` | `muro_generato` |
|---|---|---|
| 1° percentile | **8,5 mm** | ~1190 mm |
| 5° percentile | **23,4 mm** | ~1190 mm |
| mediana | 181,5 mm | 1203,9 mm |
| campioni sotto 5 mm | **1751** (0,41%) | nessuno |
| campioni sotto 1 mm | **628** (0,15%) | nessuno |

La mediana di 181,5 mm conferma che il muro scansionato è un solido di spessore
plausibile, vicino ai 176 mm misurati sul posto: non è una lamina. Ma lo 0,15%
della superficie ha dietro di sé meno di un millimetro di materiale, e il muro
sintetico non ha **nulla** sotto i 1190 mm. È una differenza di oltre tre
ordini di grandezza nella scala che il raffinamento deve risolvere.

Questi punti sottili non stanno sul bordo del lembo scansionato, dove ci si
aspetterebbe l'assottigliamento naturale di una superficie chiusa attorno a una
lastra: la loro distanza mediana dal perimetro del lembo è di 135 mm per i
campioni sotto 1 mm, contro 101 mm per l'insieme di tutti i campioni. Sono
strozzature interne, punti in cui la ricostruzione di Poisson ha fatto quasi
combaciare le due facce del muro.

**La prova.** L'ipotesi è verificabile con una variabile sola. L'opzione
`nobisect` di TetGen vieta la suddivisione delle facce di ingresso: se il
fallimento nasce lì, vietarla lo fa sparire; se nasce altrove, non cambia
nulla. Sulla stessa superficie, allo stesso `min_ratio` 1,8, nella stessa
chiamata a parte quel booleano:

| `nobisect` | esito |
|---|---|
| falso (comportamento attuale) | **fallito** in `split_subface`, dopo 72,0 s |
| **vero** | **riuscito** — 365 212 nodi, 1 607 146 tetraedri, 32,6 s |

La causa è quindi individuata: **il fallimento è nella suddivisione delle facce
di ingresso, guidata dall'invasione e non dalla qualità**, su una superficie la
cui scala locale scende sotto il millimetro in strozzature interne. Spiega
anche perché `min_ratio` era irrilevante, perché raddrizzare l'orientazione non
bastava, e perché il remeshing peggiorava: nessuno dei tre tocca la distanza
fra lembi opposti.

**Che cosa costa la leva, misurato e non supposto.** Con `nobisect` la
superficie di ingresso viene conservata esatta, senza punti aggiunti sul bordo.
Il volume del solido coincide con quello della superficie fino all'ultima cifra
(173 282 926,9485 mm³), e la qualità non peggiora — al contrario:

| | `lab_frame`, `nobisect` | `lab_frame`, via `min_ratio` 12,0 | `muro_generato`, `nobisect` | `muro_generato`, archiviato |
|---|---|---|---|---|
| nodi | 365 212 | 692 617 | 164 576 | 420 547 |
| tetraedri | 1 607 146 | 2 230 860 | 653 643 | 1 752 795 |
| tempo | 32,6 s | 186,4 s | 15,4 s | 44,6 s |
| invertiti | 0 | 0 | 0 | 0 |
| diedro minimo, mediana | **38,83°** | 25,33° | **38,68°** | 38,26° |

Sul muro sintetico, dove nulla era rotto, `nobisect` produce una mesh con 2,7
volte meno elementi, in un terzo del tempo, con mediana dell'angolo diedro
minimo leggermente migliore. Il prezzo sta nella coda: le schegge della
superficie di ingresso non vengono più suddivise e sopravvivono come facce di
tetraedri, quindi l'angolo diedro minimo assoluto scende a 4,8 · 10⁻⁴ gradi su
`lab_frame`. È una coda che esiste in ogni corsa documentata — l'archivio del
muro sintetico ha 2,5 · 10⁻³ gradi — ma qui è peggiore, e va tenuta d'occhio
perché sono gli elementi che rovinano il condizionamento del sistema.

**Che cosa resta da decidere.** `nobisect` non è ancora un parametro di
`config.py` e non è stato adottato: questa sezione lo misura, non lo introduce.
La scelta fra esporlo come opzione, renderlo il comportamento predefinito, o
lasciarlo fuori e affrontare invece le strozzature a monte — cioè in
ricostruzione, dove nascono — è una decisione di progetto per la Fase 2, non
una conseguenza automatica di questa misura.
