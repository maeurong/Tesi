# Il materiale del provino di laboratorio

Data: 18/08/2026. Nasce all'apertura della Fase 4, dalla lettura della tavola
`muro_1.pdf`.

## Cosa e' il provino

La tavola `MURO 1` (obra 0021, novembre 2021, l'ingegnere firmatario) lo
dice per intero: `lab_frame.pcd` non e' un muro in muratura, e' un **telaio in
cemento armato** di sei membrature prismatiche.

| membratura | sezione [mm] | lunghezza [mm] | n. |
|---|---|---|---|
| Zapata | 700 x 250 | 700 | 2 |
| Viga inferior | 250 x 250 | 1300 | 1 |
| Columna | 172 x 172 | 1695 | 2 |
| Viga superior | 140 x 175 | 2090 | 1 |

Fuori tutto 2700 x 1945 mm. Volume di calcestruzzo dichiarato in tavola:
**0,4777 m³**. La `PARED` — il tamponamento in blocchi, spesso 90 mm — non fa
parte del modello, ed e' assente anche dal provino scansionato: nella campata
centrale la nuvola non ha punti fra z = -450 e z = +850 mm.

Le misure sulla nuvola piena concordano con la tavola: spessore delle colonne
~200 mm sui percentili grezzi contro i 172 nominali, con i 176 mm misurati sul
posto in mezzo; ~730 mm alla base, contro i 700 delle zapatas; ~278 mm nella
fascia centrale bassa, contro i 250 della viga inferior.

## Il difetto

`lab.yaml` e `prova-interfaccia.yaml` dichiaravano `MURATURA`, con modulo
elastico 1500 MPa e densita' 1,8e-9 t/mm³. Sono i valori predefiniti che
`config.Material` metteva da solo: nessuno li aveva scelti per questo provino.
Per un telaio in c.a. il modulo elastico e' piu' di venti volte maggiore.

Non era un difetto del codice — erano valori di configurazione — ma il codice
lo rendeva possibile in silenzio, ed e' quella la parte corretta.

## Cosa e' stato corretto

- `config.Material` non ha piu' alcun valore predefinito: nome, modulo, Poisson
  e densita' sono campi obbligatori, e `AnalysisConfig.material` con loro. Una
  configurazione senza materiale dichiarato non nasce.
- `meshrec init` chiede il materiale sulla riga di comando (`--materiale`,
  `--young`, `--poisson`, `--densita`) e si rifiuta di scrivere una
  configurazione senza.
- `lab.yaml` e `prova-interfaccia.yaml` dichiarano ora `CALCESTRUZZO_C25_30`,
  young 31500 MPa, poisson 0,2, densita' 2,5e-9 t/mm³. La tavola non dichiara la
  classe del calcestruzzo: **quei valori sono un'assunzione dell'operatore**,
  scelta su C25/30, non una misura ne' un dato di progetto.
- `muro.yaml` resta a `MURATURA`: e' il muro sintetico, e li' il materiale non
  contraddice nulla.

## Cosa NON e' stato corretto, e perche'

`runs/lab_crop/config.yaml` e le altre corse di riferimento **conservano il
materiale con cui sono state eseguite davvero**. Riscriverlo falsificherebbe la
provenienza: quel file dice cosa e' stato fatto, non cosa avremmo voluto fare.

La conseguenza va letta e non nascosta: le grandezze di quelle corse che
dipendono dal materiale non sono grandezze del provino.

- `11_export.mass` e' calcolata con densita' 1,8e-9 invece di 2,5e-9: la massa
  riportata vale il **72%** di quella corrispondente al calcestruzzo assunto.
- Nessuna corsa di riferimento contiene spostamenti o tensioni — la Fase 4 si
  ferma al deck e nessun solutore e' mai stato eseguito su questi modelli —
  quindi il modulo elastico sbagliato non ha finora prodotto alcun risultato
  meccanico errato. Quando la Fase 5 risolvera' i deck, lo fara' con le
  configurazioni corrette.

Le grandezze puramente geometriche di quelle corse — volume, aree, metriche di
qualita', errore rispetto alla nuvola, copertura dei set — non dipendono dal
materiale e restano valide.

### Il registro di sweep di `lab_crop` non e' piu' raggiungibile da `lab.yaml`

Il materiale entra nell'impronta di configurazione della Fase 2. Cambiarlo cambia
l'impronta della base: `2e93bb805afe` diventa `a041514ff2d4`. Le undici righe di
`experiments/lab_crop/registro.jsonl` portano tutte `"name": "MURATURA"` e
restano dov'erano, ma **non sono piu' derivabili dalla configurazione corrente**:
il fronte di Pareto adottato e' stato scelto con un materiale che non e' quello
del provino.

Non e' una perdita di dati e non tocca la scelta: lo sweep della Fase 2 varia
parametri **geometrici** — dimensione del voxel, profondita' di Poisson, soglie
di qualita' — e nessuno dei suoi assi dipende dal materiale, quindi il fronte
resta valido come scelta geometrica. Va pero' detto, perche' chi riesegue
`meshrec sweep` con `lab.yaml` oggi produce un'impronta diversa e non ritrova le
righe di allora.

Di conseguenza `lab.yaml` non punta piu' a `runs/sweep/lab_crop/2e93bb805afe`,
che era la cartella di un candidato di quello sweep: la sua uscita e' ora
`runs/lab_c25`, cartella nuova che nessun risultato precedente occupa. Nella
stessa occasione i separatori di percorso Windows dell'ingresso sono diventati
barre normali: su macOS `..\Nuvole di punti\lab_frame.pcd` e' un nome unico che
non risolve nulla, e una configurazione dichiarata corretta che non carica la
propria nuvola sarebbe corretta solo sulla carta.

## Il nome del materiale entra nel deck

Il nome viene interpolato in `*MATERIAL, NAME=...` e il deck e' scritto in ascii.
Finche' era un predefinito la cosa era innocua; ora arriva dalla riga di comando
o dallo yaml, quindi `Material.name` accetta soltanto `[A-Za-z0-9_.-]+`. Senza
quel vincolo un accento romperebbe l'esportazione **dopo** l'intera pipeline, e
un a capo scriverebbe card in piu' nel deck senza che nulla se ne accorga.

Il resto della Fase 4 — il prior geometrico del telaio, i due modelli
parametrici e il confronto — sta in [`fase-4-prior-telaio.md`](fase-4-prior-telaio.md).
