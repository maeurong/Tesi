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
