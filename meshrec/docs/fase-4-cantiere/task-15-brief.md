> ## LEGGI QUESTO PRIMA DEL RESTO — correzioni vincolanti del 20/08/2026
>
> Questo e' il documento di esito della fase: e' **il prodotto**, non un
> sottoprodotto. Chi lo leggera' fra mesi non avra' modo di verificare cio' che
> ci scrivi, quindi ogni affermazione falsa qui costa piu' di un difetto nel
> codice — il codice lo smentisce un test, il documento non lo smentisce nessuno.
>
> Il corpo qui sotto e' stato scritto il 18/08, **prima** che i Task 8-12
> venissero eseguiti, e in due punti dice cose che oggi sono false. Dove questa
> sezione e il corpo divergono, **vale questa**.
>
> ### G1 (SERIO) — `ccx` e' installato, e il deck e' stato verificato
>
> Il corpo dice, nei rischi dichiarati, che «Task 11 salta se `ccx` non e'
> installato, che al 18/08/2026 e' il caso». **E' falso.** Misurato oggi:
>
> ```
> $ which ccx
> /Users/mario/.local/bin/ccx
> $ ccx -v
> Version 2.22
> ```
>
> I controlli col solutore **girano e passano**: `tests/feasibility` da' 8
> passati e 1 saltato, e il saltato e' `wildmeshing`, non `ccx`.
>
> La formula «il deck esaedrico non e' stato verificato da alcun solutore su
> questa macchina» **non va scritta**. Resta valida solo per le macchine dove il
> controllo salta, e con essa la regola: **un controllo saltato non e' un
> controllo passato — ma un controllo passato non va raccontato come saltato.**
>
> ### G2 (SERIO) — il paragrafo sulla coerenza dei tipi era falso, e ora e' vero per un'altra ragione
>
> Il corpo afferma che «`wall.prior` restituisce sempre lo stesso dizionario, ed
> e' quello che `pipeline.calcola_prior` scrive, che `pipeline.genera_modello`
> rilegge e che `/api/wall` inoltra». Al 18/08 era falso in due punti:
> `genera_modello` non riusciva a rileggerlo (mancavano tre campi obbligatori
> della `Membratura`, e il riempimento nel JSON e' annidato, non piatto), e su
> geometria tagliata la tupla dei `ties` usciva sempre **vuota**.
>
> Entrambi sono stati chiusi — il primo nel Task 10, il secondo in sei giri di
> correzione del Task 8 — quindi oggi la frase e' vera. **Ma va riscritta**, non
> lasciata: era vera per caso e ora e' vera per costruzione, e il documento deve
> dire anche la riga che manca, cioe' che lo `scostamento_nuvola` che il Task 12
> legge da `modello.json` lo scrive il Task 10.
>
> ### G3 (MINORE) — i numeri hanno una fonte, e tre numeri simili non sono lo stesso numero
>
> Il corpo cita «34,39 secondi» e «circa 400 MB» senza fonte. Nel repository
> esistono almeno tre numeri diversi per grandezze dal nome uguale:
> `sweep.py:151` dice «la corsa completa piu' lenta documentata vale 134 s e il
> singolo step piu' lento 186 s»; `app.js:74` dice «uno step da 34 secondi».
> Verosimilmente si riferiscono a corse diverse — il muro contro `lab_crop` — ma
> **nessuno dei tre lo dice**, ed e' esattamente il difetto che il corpo stesso
> vieta alla propria riga 142 («ogni numero del documento va ricavato da una
> lettura e citato con la propria fonte»). Applica quella regola ai tuoi numeri.
>
> ### G4 — i fatti misurati oggi, da riportare
>
> Questi non li devi ricavare: sono stati misurati in questa sessione, e sono il
> contenuto del punto sul solutore. Riportali con la loro provenienza.
>
> | fatto | valore misurato |
> |---|---|
> | `ccx` | presente, versione 2.22 |
> | deck del telaio a quattro membrature risolto | `Job finished`, sistema di 31.674 equazioni fattorizzato |
> | `*TIE` dichiarati sul telaio | 4 su 4 giunzioni |
> | nodi dipendenti vincolati davvero | 55 su 79 |
> | avvisi `no tied MPC` prima delle correzioni | 61 |
> | dopo (regola «tocca» + tolleranza dal cuneo) | 24 |
>
> **Il limite dichiarato, che e' il punto piu' importante del documento.** I
> modelli parametrici hanno una mesh **non conforme** fra i blocchi: due
> membrature adiacenti sono meshate indipendentemente, ciascuna col passo della
> propria sezione, e i loro nodi sull'interfaccia non coincidono. Il `*TIE` lega
> quello che riesce, e una parte dei nodi dipendenti resta libera. Conseguenza da
> scrivere per esteso: **un modello parametrico e' piu' cedevole del vero**, e
> quella differenza **non viene dalla geometria** ma dal vincolo. Chi legge il
> confronto deve poterla distinguere, ed e' per questo che `modello.json` porta
> `giunzioni` e `ties` come numeri separati e `nodi_dipendenti_legati` accanto a
> `nodi_dipendenti_totali`.
>
> Va scritto anche cosa **non** e' stato fatto e perche', con il costo accanto:
> la mesh conforme fra i blocchi — che farebbe sparire i `*TIE` del tutto — e'
> stata valutata e scartata, perche' farla richiederebbe o un infittimento locale
> alle giunzioni (che l'utente ha escluso: meglio una mesh omogenea di un
> infittimento nelle zone di maggior sollecitazione) o la frammentazione dei
> volumi in gmsh, che rischia di far perdere gli esaedri — e senza esaedri la
> fase non ha piu' oggetto. E va scritto che allargare la tolleranza del solutore
> a 30 mm porterebbe gli avvisi da 24 a 8, **e che non e' stato fatto**: a quella
> scala la tolleranza e' dello stesso ordine del passo di mesh, il solutore
> legherebbe un nodo alla faccia piu' vicina che puo' non essere quella di
> contatto, e **un vincolo sbagliato e' peggio di un vincolo mancante** — quello
> mancante lo conta un numero e lo stampa il solutore, quello sbagliato non lo
> vede nessuno.
>
> ### G5 — il registro delle decisioni
>
> La fase ha prodotto **trentanove rulings numerati** — da A a AM — registrati
> in `progress.md` del workspace SDD, ciascuno con la propria ragione e il costo
> se sbagliato. **Quel file sparisce alla fine della fase**: quello che vale va
> travasato nel documento, come e' stato fatto per la Fase 3 in
> `docs/fase-3-registro-decisioni.md`.
>
> Te li ho gia' estratti, uno per riga con il numero di riga d'origine, in
> `.superpowers/sdd/2026-08-18-meshrec-fase-4-prior-telaio/rulings-fase-4.md`.
>
> **Non copiarli tutti.** Il criterio di selezione: porta quelli che cambiano
> **cio' che il programma fa** o **come va letto il suo risultato**; lascia fuori
> quelli di processo e di forma. Se un ruling e' stato poi emendato o revocato da
> uno successivo — succede almeno tre volte — porta l'esito finale e **di' che e'
> stato corretto**, perche' la correzione e' informativa quanto la decisione: dice
> a chi legge che quel punto e' stato guardato due volte.
>
> ### G7 (VINCOLANTE) — la corsa vera sulla scansione **non e' stata eseguita**, e va detto
>
> Il corpo del brief presuppone una corsa completa su `lab_frame.pcd`. **Non e'
> stata fatta**, e non puo' esserlo da qui: `meshrec/lab.yaml` punta a
> `../Nuvole di punti/lab_frame.pcd`, un percorso **relativo** che dal worktree
> isolato non risolve — il file vero sta in
> `/Users/mario/GitHub/Tesi/Nuvole di punti/lab_frame.pcd`, un livello sopra la
> radice del worktree. Verificato: il file c'e', ed e' 152 MB.
>
> **Non aggirarlo copiando la nuvola nel worktree e non lanciare la corsa.** Sono
> ore di calcolo su 152 MB, ed e' una spesa che decide l'utente, non tu.
>
> Quello che devi fare invece:
>
> - scrivi il documento con **tutto cio' che e' stato misurato davvero** — la
>   suite, i controlli col solutore, i banchi sintetici, il telaio a quattro
>   membrature — che e' molto;
> - **dichiara in modo esplicito** che la corsa end-to-end sulla scansione di
>   riferimento non e' stata eseguita in questa sessione, e perche';
> - riporta **il comando esatto** per eseguirla, con il percorso assoluto della
>   nuvola, cosi' che chi la lancera' non debba ricostruirlo;
> - **non scrivere alcun numero** che sarebbe potuto uscire solo da quella corsa.
>   Se il corpo del brief ne contiene (tempi, pesi degli artefatti, conteggi di
>   membrature sulla geometria vera), toglili o marcali come attesi e non
>   misurati, dicendo da dove viene l'attesa.
>
> E' la stessa regola che governa il punto sul solutore, applicata all'altro
> verso: **un controllo saltato non e' un controllo passato**, e un numero non
> misurato non e' un risultato.
>
> ### G6 — il debito della Fase 1 che nomina la Fase 4
>
> `docs/fase-1-debito.md:269-272` porta una voce che **nomina esplicitamente
> questa fase**:
>
> > «I nomi dei set di faccia sono convenzioni. `FACE_FRONT`, `FACE_BACK`,
> > `SIDE_LEFT` e `SIDE_RIGHT` non hanno una corrispondenza verificata con le
> > facce fisiche della scansione. Finche' i carichi sono il solo peso proprio la
> > cosa e' innocua; **diventa rilevante in Fase 4, con i carichi di pressione**.»
>
> Va aggiornata, e la risposta e' in due meta' che non vanno confuse:
>
> - **Chiusa:** la corrispondenza fra i numeri di faccia del solutore e le facce
>   fisiche **e' stata verificata**, e non con un controllo interno ma col
>   solutore vero. Il test `test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra`
>   scrive una pressione su S4 di un singolo esaedro e verifica che a muoversi
>   sia il lato fisico a x massimo. Era il Ruling M(b) della Fase 3: rompe il
>   cerchio, perche' un confronto interno sarebbe partito dalla stessa
>   trascrizione che voleva verificare.
> - **Aperta:** questo dice che la **tabella delle facce** e' giusta, non che i
>   **nomi dei set** corrispondano ai lati fisici del pezzo scansionato. Sono due
>   affermazioni diverse e la seconda resta non verificata.
>
> Scrivi entrambe le meta'. Chiudere la voce per intero sarebbe falso; lasciarla
> com'e' sarebbe ingiusto verso il lavoro fatto.
>
> ---

## Task 15: la corsa nuova sul provino, e il documento di esito

Qui — e **solo** qui — i numeri del provino sono legittimi: sono dati del caso, e vivono in un file di configurazione.

**Files:**
- Create: `meshrec/lab_telaio.yaml`
- Create: `meshrec/docs/fase-4-prior-telaio.md`
- Modify: `meshrec/docs/fase-4-materiale.md` (una riga di rimando)

**Interfaces:**
- Consumes: tutto quanto sopra.
- Produces: niente per il codice.

- [ ] **Step 1: Rendere raggiungibile la nuvola dal worktree**

Le nuvole sono escluse da git (`Nuvole di punti/` in `.gitignore`) e vivono solo nella copia di lavoro principale. Dalla radice del worktree:

```bash
ln -s "/Users/mario/GitHub/Tesi/Nuvole di punti" "Nuvole di punti"
ls -la "Nuvole di punti/lab_frame.pcd"
```

Il collegamento e' ignorato da git per la stessa regola che ignora la cartella, quindi non sporca nulla.

- [ ] **Step 2: Misurare il ritaglio nuovo, invece di indovinarlo**

Serve un ritaglio che **scenda al pavimento e si allarghi trasversalmente fino a comprendere le zapatas**: quello di `lab.yaml` (`crop_min` z = -480, y da -470 a -180) taglia sopra le zapatas ed e' largo 290 mm, mentre le zapatas sono larghe 700. Le corse `lab_crop` attuali restano valide per cio' che sono — il solo telaio sopra le zapatas — e **non vengono toccate**.

Da `meshrec/`:

```bash
uv run python -c "
import numpy as np
from meshrec.core import io
from meshrec.core.config import InputConfig
punti, metriche = io.load_cloud(InputConfig(path='../Nuvole di punti/lab_frame.pcd', scale=1000.0))
print('punti', len(punti), 'spaziatura', metriche['spacing'])
print('minimo', punti.min(axis=0))
print('massimo', punti.max(axis=0))
for asse, nome in enumerate('xyz'):
    quantili = np.percentile(punti[:, asse], [0.1, 1, 5, 50, 95, 99, 99.9])
    print(nome, np.round(quantili, 1))
"
```

Scegli `crop_min` e `crop_max` da questi numeri, non da quelli di `lab.yaml`, e annota nel documento del passo 8 da quale lettura vengono. Il ritaglio deve contenere le zapatas per intero: se il fondo della nuvola e' il pavimento, `crop_min[2]` sta **sopra** il pavimento e **sotto** la base delle zapatas, ed e' la quota di taglio di cui parla il § 4.4 della spec — la base del modello e' un taglio scelto, non una faccia del pezzo.

- [ ] **Step 3: Scrivere `lab_telaio.yaml`**

Parti da una copia di `lab.yaml`, cambia il ritaglio con i valori misurati al passo 2, porta `run.out_dir` a `runs/lab_telaio` (cartella nuova che nessun risultato precedente occupa) e aggiungi i due blocchi della Fase 4. I riscontri vengono dalla tavola `MURO 1` e sono dati del caso:

```yaml
wall:
  cell_factor: 4.0
  thickness_tolerance: 0.15
  min_cells: 12
  floor_angle_deg: 15.0
  floor_min_ratio: 0.10
  contour_tolerance: 5.0
  parallelism_deg: 5.0
  face_coverage: 0.5
  section_dispersion: 0.10
  union_tolerance: 0.02
  union_step_factor: 2.0
  # Riscontri dichiarati, dalla tavola MURO 1 (obra 0021, novembre 2021,
  # ing. Jose A. Barros Cabezas). Sono dati del caso e non del programma: su
  # una geometria mai vista queste tre voci restano null e il prior riporta
  # cio' che ha trovato senza inventare un'aspettativa.
  membrature_attese: 6
  sezioni_nominali:
    - [700.0, 250.0]   # zapata, x2
    - [250.0, 250.0]   # viga inferior
    - [172.0, 172.0]   # columna, x2
    - [140.0, 175.0]   # viga superior
  volume_atteso: 477700000.0   # 0,4777 m^3 in mm^3
model:
  element: C3D8I
  min_layers: 3
  target_size: null
  tie_name_prefix: GIUNZIONE
  lateral_nset: null
  lateral_pressure: null
```

Il blocco `analysis` conserva `CALCESTRUZZO_C25_30`, young 31500 MPa, poisson 0,2, densita' 2,5e-9 — con la stessa avvertenza gia' scritta in `fase-4-materiale.md`: **quei valori sono un'assunzione dell'operatore**, scelta su C25/30, non una misura ne' un dato di progetto, perche' la tavola non dichiara la classe del calcestruzzo.

- [ ] **Step 4: Eseguire la corsa madre**

```bash
uv run meshrec run lab_telaio.yaml
```

E' la corsa lunga: sulla scansione di riferimento il singolo step piu' lento dura 34,39 secondi e gli artefatti pesano circa 400 MB. Se uno step fallisce, `steps.json` dice quale ed e' li' che si guarda per primo.

- [ ] **Step 5: Leggere il prior e i suoi controlli**

```bash
uv run python -c "
import json
esito = json.load(open('runs/lab_telaio/12_wall.json', encoding='utf-8'))
print('regioni trovate:', esito['regioni_trovate'])
print('membrature accettate:', len(esito['membrature']))
for numero, m in enumerate(esito['membrature']):
    print(f'  {numero+1}: sezione {m[\"sezione\"][0]:.1f} x {m[\"sezione\"][1]:.1f}, '
          f'lunghezza {m[\"lunghezza\"]:.1f}, fuori piombo {m[\"fuori_piombo_deg\"]:.2f}')
for voce in esito['scartate']:
    print('  scartata', voce['regione'], voce['controlli_falliti'])
print('chiusura volume:', esito['chiusura_volume'])
print('riscontri:', esito['riscontri'])
"
```

**Qualunque numero esca, va scritto.** Se le membrature accettate non sono sei, il documento lo dice e dice quale controllo ha respinto le altre: un esito negativo documentato non e' un fallimento, ed e' la voce del progetto.

- [ ] **Step 6: Generare i due modelli e il confronto**

```bash
uv run meshrec model lab_telaio.yaml --tipo estruso
uv run meshrec model lab_telaio.yaml --tipo primitive
uv run meshrec compare runs/lab_telaio runs/lab_telaio-estruso runs/lab_telaio-primitive --out runs/lab_telaio/confronto.html
```

- [ ] **Step 7: La suite intera, un'ultima volta**

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS. Annota il conteggio finale di passati e saltati: e' un numero del documento.

- [ ] **Step 8: Scrivere `meshrec/docs/fase-4-prior-telaio.md`**

Deve contenere, nell'ordine:

1. **Che cosa gira e che cosa no.** Con i numeri veri della corsa del passo 5 e del confronto del passo 6.
2. **Perche' la fase ha cambiato nome.** Il prior non e' «due piani paralleli e uno spessore» ma «telaio di membrature prismatiche», e la premessa vecchia e' stata misurata falsa, non ipotizzata tale.
3. **Le membrature trovate contro la tavola.** Sezioni misurate accanto alle nominali, volume misurato accanto ai 0,4777 m³, con lo scarto. Se le membrature non sono sei, quale controllo ha respinto le altre e con quale numero.
4. **I tre controlli intrinseci, con il loro esito su questa corsa, e accanto lo stato del riempimento di sezione di ciascuna membratura** (`pieno` / `vuoto` / `non_verificabile`, con la sua affidabilita': Ruling J, il riempimento misura e dichiara, non scarta). Compresa la chiusura del volume, che e' quella che cerca il doppio conteggio alle giunzioni.
5. **L'elenco dei rulings**, ciascuno nella forma `Ruling: <cosa ho deciso> — <perche'> — <cosa costa se sbagliato>`. I sei di questo piano piu' quelli presi durante l'esecuzione.
6. **Che cosa la fase non fa**, con la ragione: nessun solutore (e' Fase 5), nessuna armatura (scelta dell'autore, il dato resta nella tavola), nessun tamponamento, nessuna riscrittura delle corse di riferimento, nessuna mesh conforme alle giunzioni (`*TIE` ora, multiblocco come via d'aggiornamento dichiarata).
7. **Lo stato del deck.** Se `ccx` non era installato: «il deck esaedrico non e' stato verificato da alcun solutore su questa macchina, perche' `ccx` non e' installato». **Mai** «il deck e' valido». Vale anche per Abaqus, per cui il progetto non ha licenza e su cui `PRODUCT.md` e' esplicito.
8. **Il ritaglio nuovo**, con la lettura da cui vengono le sue sei coordinate, e la riga che il § 4.4 chiede a lettere chiare: **la base del modello non esiste nel pezzo vero, e' dove abbiamo tagliato**.
9. **I limiti misurati**, se ne sono emersi: il soffitto del taglio alle giunzioni (accorciamento lungo l'asse, non operazione booleana), il soffitto della ricombinazione di gmsh (ordine canonico si', combinatoria no), la sottostima del rigonfiamento dove le celle sono grandi.

Ogni numero del documento va ricavato da una lettura e citato con la propria fonte.

- [ ] **Step 9: Il rimando in `fase-4-materiale.md`**

In coda al documento del materiale, una riga sola:

```markdown
Il resto della Fase 4 — il prior geometrico del telaio, i due modelli
parametrici e il confronto — sta in [`fase-4-prior-telaio.md`](fase-4-prior-telaio.md).
```

- [ ] **Step 10: Commit**

```bash
git add meshrec/lab_telaio.yaml meshrec/docs/fase-4-prior-telaio.md meshrec/docs/fase-4-materiale.md
git commit -m "docs(fase-4): la corsa sul telaio, gli esiti del prior e i rulings"
```

---

## Self-Review

**Copertura della spec.** § 1 e 1.1 nel documento del Task 15 (punti 2 e 7) e in `fase-4-materiale.md`, gia' scritto. § 2 punto 1 in Task 2 e 3; punto 2 in Task 7, 8 e 10; punto 3 in Task 5 e 10; punto 4 in Task 12. § 3.1 in Task 9 e 10 (un solo blocco in `run()`, i modelli come corse figlie). § 3.2 nella File Structure e nella ripartizione fra Task 2-3 (wall misura) e 7-8 (hexa costruisce). § 4.1 in Task 2. § 4.2 in Task 3. § 4.3 in Task 3, controlli intrinseci e riscontri dichiarati separati come chiede il vincolo di prodotto. § 4.4 in Task 15, passi 2 e 8. § 5 in Task 8 (Ruling 4). § 5.1 in Task 1 (`ModelConfig.element` e `min_layers`) e Task 7 (il vincolo imposto dal codice). § 5.2 in Task 8. § 6 in Task 5 e 10. § 6.1 in Task 11. § 7 in Task 12. § 7.1 in Task 12 e 13 (insiemi parziali, selezione come azione). § 8 distribuito: scomposizione in Task 2, sezioni e volume in Task 3, mesh esaedrica in Task 7, giunzioni in Task 3 e 8, superfici di elemento in Task 5, deck in Task 11, indipendenza dalla piattaforma in Task 2 e 7. § 9 in Task 13 e 14. § 10 in Task 15, punto 6.

**Segnaposti.** Nessun «TBD». Tre deleghe sono dichiarate come tali invece di essere nascoste, e ciascuna dice che cosa manca: l'attesa fra i due modelli in Task 14 Step 4, che se copiata com'e' non funziona ed e' scritto in grassetto; le classi CSS del Task 14 Step 7, per cui il sistema di design della Fase 3 e' gia' definito e vale come specifica; e i sei numeri del ritaglio in Task 15, che si misurano con il comando dato al passo 2 e non si possono conoscere prima, perche' la nuvola non e' nel repository.

**Coerenza dei tipi.** `wall.prior` restituisce sempre lo stesso dizionario, ed e' quello che `pipeline.calcola_prior` scrive, che `pipeline.genera_modello` rilegge e che `/api/wall` inoltra. `hexa.costruisci` restituisce sempre le sei chiavi `nodi, elementi, blocchi, superfici, ties, metriche`, e `ties` e' sempre una tupla di terne `(nome, dipendente, indipendente)`, che e' esattamente la forma che `write_inp` accetta. `abaqus.element_surface` restituisce sempre una lista di coppie `(elemento, numero)` 0-based sull'elemento e 1-based sul numero di faccia, ed e' quella che `surface_area` e `write_inp` consumano. Le due tabelle di faccia portano nomi diversi — `FACCE_TOPOLOGICHE` e `FACCE_DEL_SOLUTORE` — apposta, e il commento sopra la seconda dice perche' non vanno confuse. `element_volumes` e' il solo punto in cui il resto del programma si chiede quanti nodi ha un elemento.

**Rischi dichiarati.** Task 1 Step 11 dipende dalla rete per installare gmsh: se la rete manca, il piano si ferma li' e non prosegue a vuoto. Task 11 salta se `ccx` non e' installato, che al 18/08/2026 e' il caso: il piano prescrive la formula esatta con cui dichiararlo invece di lasciare che qualcuno scriva «verificato». Task 15 dipende da `lab_frame.pcd`, 152 MB fuori da git: il passo 1 crea il collegamento, e senza quel file la corsa non parte — non c'e' modo di aggirarlo, ed e' giusto cosi'.

---

## Assegnazione, sequenza e skill-gate

Per ogni task: quale subagente lo esegue, che cosa puo' girare in parallelo, e quale skill l'esecutore e' **obbligato** a invocare prima di chiudere.

| Task | Subagente | Skill obbligatoria | Skill-gate |
|---|---|---|---|
| 1 — Fondamenta, gmsh, blocchi, step 12 | `backend-engineer` | `superpowers:test-driven-development` | si |
| 2 — `wall.py`, scomposizione | `backend-engineer` | `superpowers:test-driven-development` | si |
| 3 — `wall.py`, misure e controlli | `backend-engineer` | `superpowers:test-driven-development` | si |
| 4 — `abaqus`/`quality` per tipo di elemento | `backend-engineer` | `superpowers:test-driven-development` | si |
| 5 — superfici di elemento, `*TIE`, carico | `backend-engineer` | `superpowers:test-driven-development` | si |
| 6 — Jacobiano scalato | `backend-engineer` | `superpowers:test-driven-development` | si |
| 7 — `hexa.py`, il prisma | `backend-engineer` | `superpowers:test-driven-development` | si |
| 8 — `hexa.py`, il telaio e le giunzioni | `backend-engineer` | `superpowers:test-driven-development` | si |
| 9 — step 12 in pipeline, `meshrec wall` | `backend-engineer` | `superpowers:test-driven-development` | si |
| 10 — corse figlie, `meshrec model` | `backend-engineer` | `superpowers:test-driven-development` | si |
| 11 — `ccx` legge il deck | `test-writer` | `tdd-guide` | si |
| 12 — confronto e report | `backend-engineer` | `superpowers:test-driven-development` | si |
| 13 — endpoint del server | `backend-engineer` | `superpowers:test-driven-development` | si |
| 14 — interfaccia | `frontend-engineer` | `impeccable` | si |
| 15 — corsa nuova e documento | `coder` | `documentation` | si |

**Sequenza.**

```
Task 1  (fondamenta: nessun altro task parte prima)
   |
   +-- GRUPPO A, in parallelo: Task 2  e  Task 4
   |                              |          |
   |                          Task 3      Task 5  e  Task 6  (in parallelo fra loro)
   |                              |          |
   +----------------------------- Task 7 ----+
                                     |
                                  Task 8
                                     |
                                  Task 9
                                     |
                    +---- Task 10 ---+
                    |                |
              Task 11          Task 12        (in parallelo fra loro)
                    |                |
                    +---- Task 13 ---+
                             |
                          Task 14
                             |
                          Task 15
```

- **Task 1 e' un cancello**: tocca `config.py`, `steps.py`, `sweep.py` e `pyproject.toml`, che tutto il resto legge. Nessun task parte prima che sia rivisto e chiuso.
- **Gruppo A parallelo — Task 2 e Task 4**: bersagli disgiunti. Task 2 scrive `wall.py`, `synth.py`, `test_wall.py`, `test_synth.py`; Task 4 scrive `abaqus.py`, `quality.py`, `test_abaqus.py`, `test_quality.py`. L'unico incrocio e' `abaqus.fix_sign`, che Task 2 rende pubblica e Task 4 non tocca: **Task 2 esegue quella rinomina, Task 4 no**, ed e' scritto in entrambi.
- **Task 3 dopo Task 2** (stesso file, `wall.py`). **Task 5 e Task 6 dopo Task 4** e in parallelo fra loro: Task 5 tocca solo `abaqus.py`, Task 6 solo `quality.py`.
- **Task 7 aspetta Task 1, 4 e 6** (usa `hex_volumes` e `scaled_jacobian`). **Task 8 dopo Task 7 e Task 5** (stesso file `hexa.py`, piu' `element_surface`).
- **Task 9 aspetta Task 3** (`wall.prior`). **Task 10 dopo Task 8 e Task 9**.
- **Task 11 e Task 12 in parallelo**: bersagli disgiunti, `tests/feasibility/` contro `report.py` piu' `cli.py`. Attenzione: entrambi non toccano `cli.py`? Task 12 si'. Task 11 no. Nessuna sovrapposizione.
- **Task 13 dopo Task 10 e Task 12**. **Task 14 dopo Task 13** (consuma i suoi endpoint). **Task 15 ultimo**: e' l'unico che fa girare la pipeline sul dato vero, e il documento cita numeri che prima non esistono.
- **Revisione fra un task e l'altro**: `code-reviewer` e `security-reviewer` in parallelo, in sola lettura, prima di ogni commit che chiude un task — come impone il ciclo standard del progetto. `security-reviewer` ha poco da fare qui (nessuna superficie di autenticazione, nessun input esterno oltre ai file gia' letti dalle fasi precedenti) e puo' essere saltato sui Task 2, 3, 6, 7, 8 e 11; resta obbligatorio sui Task 1, 5, 10, 13 e 14, che toccano rispettivamente la configurazione, la scrittura del deck, l'esecuzione di sottoprocessi e il markup.

**Perche' nessuno skill-gate e' falso.** Ogni task di questo piano scrive un test che deve fallire prima di esistere, e il ciclo TDD e' esattamente cio' che la skill impone: nessuno degli step qui e' un rename, una configurazione di una riga o una modifica meccanica. Il Task 15 e' l'unico senza codice nuovo, e li' la skill obbligatoria non e' il TDD ma `documentation`, perche' il suo prodotto e' un documento che qualcuno leggera' fra sei mesi per capire che cosa e' stato misurato e che cosa no.
