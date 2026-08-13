# Fase 2 — Lo sweep a un asse per volta, e il fronte adottato

- **Data di esecuzione:** 13 agosto 2026
- **Ambiente:** Windows 11, stessa macchina delle misure di Fase 1
- **Corse:** due sweep indipendenti, dichiarati in `experiments/muro/esperimento.yaml`
  (corsa di riferimento `muro.yaml`, spessore noto 1245,7 mm) e
  `experiments/lab_crop/esperimento.yaml` (corsa di riferimento `lab.yaml`,
  spessore noto 176,0 mm)
- **Registri:** `experiments/muro/registro.jsonl`, `experiments/lab_crop/registro.jsonl`,
  con la vista tabellare in `experiments/muro/report.html` e `experiments/lab_crop/report.html`
- **Esito:** il fronte e' adottato su entrambe le corse. `meshrec/muro.yaml` porta
  `tet.nobisect: true`, `meshrec/lab.yaml` porta `surface.poisson_depth: 7`.

## 1. Che cosa e' stato misurato e come

Le due dichiarazioni d'esperimento condividono la forma: cinque assi,
`downsample.voxel_size`, `surface.poisson_depth`, `surface.density_quantile`,
`tet.min_ratio` e `tet.nobisect`, esplorati **un asse alla volta** a partire
dalla configurazione in vigore. Un fattoriale pieno su cinque assi a tre
livelli sarebbe 162 candidati per corsa; a un asse per volta, ciascuna corsa
ne misura **11** — la configurazione base piu' le variazioni non ridondanti
sui cinque assi (2+2+2+3+1 sopra la base, piu' la base stessa). Il metodo
sacrifica le interazioni fra assi per rendere la griglia eseguibile in ore
invece che in giorni, ed e' dichiarato come limite al punto 8.

`experiments/muro/esperimento.yaml` gira in **circa 5 minuti e 46 secondi**
con 4 processi in parallelo. `experiments/lab_crop/esperimento.yaml` gira in
**circa 15 minuti e 14 secondi** con **2** processi: il commento
nell'esperimento dichiara il motivo, memoria — sulla macchina restavano circa
9 GB liberi su 15,8 GB totali, e ogni candidato lavora su 6,3 milioni di punti
con un picco misurato di TetGen di 1,35 GB da solo; quattro candidati in volo
insieme (5,4 GB di solo TetGen, piu' il resto della pipeline) non lasciavano
margine.

Ogni riga di registro porta l'impronta del candidato (`fingerprint`), gli assi
variati rispetto alla base (`axes`), l'esito, le metriche complete e il
comando per riprodurla (`rerun`). Il fronte di Pareto e' marcato riga per riga
da `on_front: true`.

## 2. La verifica della misura di spessore, per prima

Prima di leggere qualunque risultato dello sweep va verificato che l'asse di
fedelta' — lo scarto fra lo spessore ricostruito e quello noto — sia
utilizzabile. Senza questa verifica la Fase 2 non sarebbe partita: e' il
controllo che rende l'asse di fedelta' un asse e non un numero arbitrario.

| corsa | spessore letto dalla nuvola sorgente | spessore noto | scarto |
|---|---|---|---|
| `muro` | 1204,48 mm | 1245,70 mm | **3,31%** |
| `lab_crop` | 175,26 mm | 176,00 mm | **0,42%** |

I due numeri misurano cose diverse. Lo spessore *letto* e' la distanza fra i
due modi dell'istogramma bimodale delle normali sulla nuvola sorgente — la
misura che l'asse di fedelta' usa come riferimento in ogni candidato dello
sweep, e che infatti resta costante entro corsa (`thickness_source` in ogni
riga del registro). Lo spessore *noto* e' l'ingombro dichiarato nella
generazione sintetica del muro o misurato sul posto per `lab_frame`. Il
criterio dichiarato in codice (`sweep.py`, `non_valido = scarto /
experiment.known_thickness > 0.05`) e' il **5%**: entrambe le corse restano
ben sotto, quindi l'asse di fedelta' e' verificato utilizzabile su entrambe.

## 3. Risultati

### `muro`

Sommario: **11 candidati**, **4 falliti (36,4%)**, **7 confrontabili**, fronte
di un solo candidato.

I quattro falliti, tutti con lo stesso `RefinementFailedError` a
`min_ratio=1,8` ma un punto interno di rottura diverso in TetGen:

| assi variati | punto di rottura interno di TetGen |
|---|---|
| `downsample.voxel_size = 18,25` | `split_subface` |
| `downsample.voxel_size = 35,0` | `removevertexbyflips` |
| `surface.poisson_depth = 7` | `split_subface` |
| `surface.poisson_depth = 9` | `recoversubfaces` |

I sette confrontabili, con i tre assi del fronte (errore di spessore,
tetraedri, frazione fuori vincolo raggio-spigolo) piu' le due metriche
riportate:

| assi variati | errore spessore [mm] | tetraedri | fuori vincolo | diedro min., mediana |
|---|---|---|---|---|
| base (in vigore) | 0,00 | 1.752.795 | 8,10% | 38,26° |
| `surface.density_quantile = 0,0` | 0,00 | 1.777.624 | 8,08% | 38,20° |
| `surface.density_quantile = 0,12` | 9,125 | 1.776.167 | 8,28% | 38,21° |
| `tet.min_ratio = 1,7` | 0,00 | 1.923.892 | 7,36% | 39,11° |
| `tet.min_ratio = 2,0` | 0,00 | 1.498.226 | 9,84% | 36,84° |
| `tet.min_ratio = 2,5` | 0,00 | 1.134.074 | 19,37% | 34,20° |
| **`tet.nobisect = true` — fronte** | **0,00** | **653.643** | **3,82%** | **38,68°** |

### `lab_crop`

Sommario: **11 candidati**, **1 fallito (9,1%)**, **10 confrontabili**, fronte
di un solo candidato.

L'unico fallito:

| assi variati | punto di rottura interno di TetGen |
|---|---|
| `tet.nobisect = false` | `split_subface` |

I dieci confrontabili:

| assi variati | errore spessore [mm] | tetraedri | fuori vincolo | diedro min., mediana |
|---|---|---|---|---|
| base (in vigore) | 2,385 | 1.607.146 | 9,55% | 38,83° |
| `downsample.voxel_size = 5,0` | 1,192 | 1.947.593 | 10,54% | 39,04° |
| `downsample.voxel_size = 15,0` | 1,192 | 245.916 | 7,36% | 38,61° |
| `surface.poisson_depth = 8` | 2,385 | 268.485 | 7,77% | 38,72° |
| `surface.density_quantile = 0,0` | 1,192 | 1.616.377 | 9,90% | 38,77° |
| `surface.density_quantile = 0,12` | 1,192 | 1.559.822 | 9,05% | 39,01° |
| `tet.min_ratio = 1,7` | 2,385 | 1.689.310 | 8,91% | 39,59° |
| `tet.min_ratio = 2,0` | 2,385 | 1.482.682 | 10,94% | 37,66° |
| `tet.min_ratio = 2,5` | 2,385 | 1.287.303 | 14,91% | 35,69° |
| **`surface.poisson_depth = 7` — fronte** | **1,192** | **50.630** | **6,84%** | **38,75°** |

Spessore ricostruito dal candidato di fronte: **174,07 mm**.

## 4. Le sorveglianze

Il codice porta due sorveglianze qualitative sull'esito complessivo dello
sweep (`check_sweep` in `sweep.py`), nessuna delle due tarata: un avviso se
piu' della meta' dei candidati fallisce, un avviso se il fronte contiene
tutti i confrontabili (segno che gli assi non discriminano).

Nessuna delle due e' scattata su nessuna delle due corse. La frazione di
falliti, 36,4% su `muro` e 9,1% su `lab_crop`, resta ben sotto la meta' in
entrambi i casi. Il fronte e' piu' piccolo dell'insieme dei confrontabili in
entrambi i casi — un candidato su sette per `muro`, un candidato su dieci per
`lab_crop` — quindi gli assi stanno discriminando fra le configurazioni, non
restituendo tutto indistintamente.

## 5. La scelta, con il criterio dichiarato

Su entrambe le corse il fronte ha **un solo candidato**: la decisione non e'
stata fra piu' candidati del fronte, ma se adottare quel candidato al posto
della configurazione in vigore. Il criterio dichiarato: si adotta il
candidato non dominato quando migliora almeno uno dei tre assi (errore di
spessore, tetraedri, frazione fuori vincolo) senza peggiorarne alcuno rispetto
alla configurazione in vigore — la stessa nozione di dominanza che
`pareto_front` applica per costruire il fronte stesso.

**Su `muro`, il fronte domina tutti e sei gli altri candidati confrontabili.**
`tet.nobisect = true` pareggia l'errore di spessore (0,00 mm ovunque tranne
`density_quantile = 0,12`, dove lo batte) e batte ogni altro candidato sia in
tetraedri sia in frazione fuori vincolo — dal confronto piu' vicino, la base
in vigore (1.752.795 tetraedri e 8,10% fuori vincolo contro 653.643 e 3,82%),
al piu' lontano, `min_ratio = 2,5` (19,37% fuori vincolo contro 3,82%).

**Su `lab_crop`, il fronte domina tutti e nove gli altri candidati
confrontabili**, con lo stesso schema: `surface.poisson_depth = 7` pareggia o
batte l'errore di spessore di ciascuno (1,192 mm contro 1,192 o 2,385 mm) e
batte ognuno sia in tetraedri sia in frazione fuori vincolo.

**Il numero che rende la scelta di `lab_crop` non ovvia** e' il costo in
tetraedri, non il beneficio: gli elementi passano da 1.607.146 (base) a
50.630, cioe' il modello adottato e' circa **trentadue volte piu' leggero**
(1.607.146 / 50.630 ≈ 31,7). Con un lato medio di circa 26 mm sopravvivono
ancora sei o sette elementi nello spessore del muro (174 mm) — pochi rispetto
alla base, ma non pochi al punto da rendere la mesh inutilizzabile per
un'analisi a volumi.

## 6. `nobisect`: la domanda della Fase 1 ha una risposta, ed e' negativa

`fase-1-min-ratio.md` chiudeva la questione di `tet.nobisect` con una domanda
aperta: la leva funziona, ma non era chiaro se fosse "la risposta giusta o
solo quella che funziona" — se cioe' una taratura diversa degli altri assi
potesse rendere `nobisect: false` di nuovo praticabile su `lab_frame.pcd`.

Questo sweep risponde, e la risposta e' negativa. L'unico candidato che prova
`tet.nobisect = false` su `lab_crop` — tutti gli altri assi alla
configurazione in vigore, che gia' porta `nobisect: true` — e' anche l'unico
candidato fallito della corsa, con lo stesso punto di rottura interno di
TetGen, `split_subface`, gia' documentato in Fase 1. Nessuna taratura a un
asse per volta di `downsample.voxel_size`, `surface.poisson_depth` o
`surface.density_quantile` rende evitabile quella leva: nei dieci candidati
confrontabili, tutti gli altri con `nobisect: true`, nessuno la aggira.

**E' un esito negativo documentato, non un fallimento della fase.** La
postilla necessaria: il metodo a un asse per volta non esclude che una
combinazione di piu' assi renda `nobisect: false` di nuovo praticabile — solo
che nessuna variazione di un asse singolo, fra quelle misurate qui, lo fa.

## 7. L'esito piu' importante per la tesi

Alla profondita' di Poisson 9 — quella con cui la Fase 1 aveva raggiunto il
deck su `lab_frame.pcd` prima di introdurre `nobisect` — lo spessore
ricostruito misurava **214,0 mm contro 176 mm reali**
(`fase-1-esiti-lab-frame.md`), un ispessimento del **21%**. L'errore
geometrico bidirezionale allora adottato come metrica di fedelta' restava a
**3,85 mm**: una distanza punto-superficie che un ispessimento simmetrico
lascia bassa, e che quindi non rivelava affatto l'ispessimento — era
**invisibile** a quella metrica.

Alla profondita' 7, il candidato ora adottato, lo spessore ricostruito e'
**174,07 mm**: praticamente lo spessore reale, non 214 mm. La metrica di
fedelta' adottata in Fase 1 era cieca proprio sull'errore sistematico che
governa la rigidezza di una muratura, e il nuovo asse di fedelta' introdotto
in questa fase lo rende visibile, con lo stesso scarto (1,19 mm) che compare
nella tabella del punto 3. Questo e' il
contributo di misura della Fase 2: non solo una configurazione migliore, ma
uno strumento che avrebbe segnalato l'errore che la Fase 1 non poteva vedere.

## 8. Che cosa questo lavoro non chiude

**(a) L'asse di fedelta' e' quantizzato.** Su `lab_crop` assume due soli
valori fra i confrontabili, **1,19 e 2,38 mm**, in rapporto esattamente
doppio (2,385 / 1,192 ≈ 2,00) — uno e due bin di un istogramma largo quanto
la spaziatura sorgente della nuvola, 1,1923 mm. Sul muro, con spaziatura
9,125 mm, tutte le varianti che non toccano la ricostruzione danno **0,00**
esatti, e quello zero **non significa ricostruzione perfetta**: significa
errore sotto la risoluzione della misura, che su questa nuvola e' larga quasi
un centimetro.

**(b) La griglia e' a un asse per volta.** Le interazioni fra assi — per
esempio se un `poisson_depth` piu' basso *insieme* a un `min_ratio` diverso
cambi la conclusione del punto 6 — non sono state misurate.

**(c) `simplify` e' rimasto fuori dagli assi.** Lo step 8 di remeshing
isotropo, gia' misurato in Fase 1 come peggiorativo su una configurazione
specifica (`fase-1-min-ratio.md`), non e' stato incluso nello sweep.

**(d) I debiti della Fase 1 che restano.** Nulla rivalida la superficie dopo
lo step 8; `FACE_FRONT` e `FACE_BACK` restano decorativi su scansione reale;
i nomi dei set restano convenzioni; il controllo dei dati con Abaqus resta
dovuto alla prima occasione di accesso a una licenza.

## 9. Dove vivono gli artefatti

`runs/muro/` e `runs/lab_crop/` restano le corse di riferimento della Fase 1,
non toccate da questo lavoro, e continuano a documentare i numeri di quella
fase.

Gli artefatti dei due candidati adottati stanno sotto `runs/sweep/`:

- muro, `tet.nobisect = true` — `runs/sweep/muro/83bbe93f7ce6/`
- `lab_crop`, `surface.poisson_depth = 7` — `runs/sweep/lab_crop/2e93bb805afe/`

La riga di registro corrispondente (impronta
`83bbe93f7ce6e0d4f70b6f077d1705158a37bd7083b55b09b4d57fa32b38100b` per
`muro`, `2e93bb805afee82d557badc3151dff7bea870d0896b9515e64366d4f3f3b596f` per
`lab_crop`) porta il comando `rerun` per riprodurre ciascuno da capo. Chi
rileggera' fra mesi parte dal registro, non da questo documento.
