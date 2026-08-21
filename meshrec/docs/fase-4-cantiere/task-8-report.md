# Task 8 — report: il telaio, le giunzioni tagliate, le superfici del *TIE

## Cosa è stato fatto

`hexa.py` riceve `Prisma`, `prisma_di`, `dentro`, `taglia_giunzioni`, `costruisci` in coda al file, seguendo alla lettera il codice del brief (già estratto ed eseguito nel setaccio del 20/08). Nessuna deviazione dal brief: il codice proposto era corretto contro le interfacce reali di `wall.Membratura`, `ModelConfig` e `abaqus.element_surface`, verificate a mano prima di scrivere (vedi sotto).

File toccati:
- `src/meshrec/core/hexa.py` — aggiunto `from dataclasses import dataclass`; in coda: `Prisma`, `prisma_di`, `dentro`, `_CAMPIONI_ASSE`, `_PASSI_BISEZIONE`, `_TOLLERANZA_CONTATTO`, `_bordo_del_solido`, `taglia_giunzioni`, `costruisci`.
- `tests/test_hexa.py` — aggiunti `_membratura_finta`, le costanti `COLONNA`/`TRAVE`/`QUOTA_TRAVE`/`ALTEZZA_COLONNA`/`LUNGHEZZA_TRAVE`/`ACCORCIAMENTO_ATTESO`, `_telaio_di_prova`, e otto test.

## Verifica delle interfacce prima di scrivere

Lette prima di toccare `hexa.py`: `wall.Membratura` (dataclass a `wall.py:338`, campi coerenti con `_membratura_finta` del brief, incluso `esiti: dict = field(default_factory=dict)` non passato dall'helper — legittimo, ha un default), `config.ModelConfig` (campi `element`, `min_layers`, `target_size`, `tie_name_prefix`, `lateral_nset/pressure` — tutti quelli usati dal brief esistono), `abaqus.element_surface(elements, indici_nodo, element_type) -> list[tuple[int,int]]` (firma e contratto — solo facce coi nodi tutti nell'insieme — coerenti con l'uso in `costruisci`).

## I sedici test — valore atteso, provenienza, esito

Gli otto già presenti (non toccati, non ripetuti qui in dettaglio): tutti PASS, invariati.

I nuovi otto:

1. **`test_una_membratura_a_sezione_vuota_non_diventa_un_modello`**
   Atteso: `ValueError` con messaggio contenente `"vuoto"`.
   Provenienza: guardia del Ruling J in `costruisci`, che rifiuta ogni membratura con `riempimento_stato == "vuoto"` prima di costruire qualunque cosa — nessun numero, solo un controllo di stato.
   Esito: PASS — solleva come atteso.

2. **`test_una_membratura_non_verificabile_si_costruisce_lo_stesso`**
   Atteso: `len(esito["blocchi"]) == 1`.
   Provenienza: una sola membratura in ingresso → un solo blocco in uscita, per costruzione del ciclo `for numero, prisma in enumerate(tagliati)` in `costruisci`.
   Esito: PASS.

3. **`test_il_modello_primitive_raddrizza_l_asse_e_squadra_la_sezione`**
   Atteso: `estruso.asse == storto`, `primitive.asse == [0,0,1]`, entrambi i contorni a 4 vertici, i quattro lati del contorno `primitive` ortogonali a coppie consecutive.
   Provenienza: `prisma_di("estruso")` copia `membratura.asse`; `prisma_di("primitive")` copia `membratura.asse_ideale` (qui passato `[0,0,1]` esplicitamente nell'helper); il rettangolo di `primitive` è costruito per definizione con quattro angoli retti (min + assi coordinati locali).
   Esito: PASS.

4. **`test_il_modello_primitive_conserva_le_dimensioni_misurate`**
   Atteso: `np.ptp(primitive.contorno, axis=0) == [250.0, 175.0]`; `primitive.lunghezza == 900.0`; contorno diverso da quello rilevato.
   Provenienza: `np.ptp` sui vertici della sezione irregolare data in input dà esattamente 250 e 175 (differenza fra max e min di x e y rispettivamente — calcolo diretto, non letto dal codice); lunghezza passata invariata (900.0) perché `prisma_di` non la tocca.
   Esito: PASS.

5. **`test_l_appartenenza_a_un_prisma_e_esatta_sul_contorno_convesso`**
   Atteso: due punti interni dentro, tre punti esterni fuori, un punto a 0,5 mm dalla faccia y=0 fuori a tolleranza 0 e dentro a tolleranza 1,0.
   Provenienza: geometria dichiarata a mano contro `RETTANGOLO` (200×140) e `lunghezza=1000` — nessun valore letto dal codice sotto prova.
   Esito: PASS.

6. **`test_due_prismi_che_si_compenetrano_vengono_tagliati_sul_bordo_del_solido`**
   Atteso: `giunzioni[0]["accorciamento"] == 100.0` (= 1400 − 1300); `tagliati[0].lunghezza == 1300.0`; `tagliati[1].lunghezza == 1400.0`; somma dei volumi = `200·200·1300 + 300·200·1400` con `rel=1e-9`.
   Provenienza: l'accorciamento è la differenza dichiarata fra quota della trave e altezza della colonna; la lunghezza tagliata della colonna è per costruzione la quota della trave (l'origine della colonna è z=0); il volume atteso è la somma di due prodotti dimensione×dimensione×lunghezza, senza sottrazioni, perché dopo il taglio i due solidi non si sovrappongono.
   Eseguito a mano (fuori dalla suite, per verifica indipendente): residuo della bisezione misurato `-4.09e-12 mm` (brief dichiara 3,4e-12 mm — stesso ordine di grandezza, differenza plausibile per piattaforma/percorso in virgola mobile, non un difetto). Accorciamento misurato `100.00000000000409` — coincide con l'atteso entro `abs=1e-6`.
   Esito: PASS.

7. **`test_un_prisma_che_attraversa_un_altro_da_parte_a_parte_e_rifiutato`**
   Atteso: `ValueError` con messaggio contenente `"parte a parte"`.
   Provenienza: colonna alta 1600 attraversa la trave (che occupa 1300–1500) da parte a parte — entrambe le estremità del campionamento restano fuori dal prisma maggiore, quindi la guardia `not invaso[0] and not invaso[-1]` scatta.
   Esito: PASS.

8. **`test_il_telaio_costruito_dichiara_le_superfici_del_tie`**
   Atteso: elementi a 8 nodi, due blocchi, `ties` non vuoto, entrambe le superfici di ogni tie non vuote, `metriche["giunzioni"] == 1`, `metriche["accorciamenti"] == [100.0]`.
   Provenienza: due membrature che si incontrano in un solo punto → una sola giunzione; l'accorciamento è lo stesso del test 6.
   Verificato a mano, fuori dalla suite: superficie dipendente `GIUNZIONE_1_D` con **20 facce**, indipendente `GIUNZIONE_1_I` con **12 facce** — numeri identici a quelli dichiarati nel brief ("20 e 12 facce").
   Esito: PASS.

## Suite intera

`uv run pytest tests -q --ignore=tests/feasibility` → **487 passed** (479 base dichiarati nel task + 8 nuovi di questo task), 1 warning preesistente non correlato (`UnmetQualityConstraintWarning` in `test_volume.py`).

## Nessuna deviazione dal brief

Non ho trovato numeri che non tornassero, né geometrie che facessero altro da quanto il brief dichiara. L'unico scarto osservato — il residuo della bisezione (4,09e-12 mm misurato contro 3,4e-12 mm dichiarato) — resta nello stesso ordine di grandezza e sotto la soglia di `_ARROTONDAMENTO` (1e-6 mm) che il margine `_TOLLERANZA_CONTATTO` deve coprire; non è un difetto, è variazione di piattaforma/percorso in virgola mobile sullo stesso algoritmo.

## Segnalazione per il seguito (non in scope qui)

Il brief nota che "il Task 11 va esteso a un caso `*TIE` con criterio `'no tied MPC' not in stdout`": non è compito di questo task, lo riporto perché il brief lo marca esplicitamente come lavoro ancora da fare.

---

# Giro di correzione 1 di 5 (`task-8-fix-1.md`)

## Stato: DONE

## Cosa è stato fatto

Applicati tutti i rilievi A1–A4, B1–B4, B5–B6, B7 e due dei tre "rilievi minori" (import `abaqus` in testa al modulo — verificato nessun ciclo, `abaqus.py` non importa `hexa`; la somma O(n²) di `primo_elemento` sostituita con un contatore accumulato; docstring di `mesh_prisma` che dichiara la serialità obbligatoria). Non toccati, per restare nel perimetro del giro: la guardia su asse nullo in `dentro`/`_base_del_piano` e la verifica esplicita di convessità in `Prisma` — richiederebbero ciascuna un proprio test e allungano il giro senza essere fra i rilievi numerati; li segnalo qui invece di farli in silenzio.

File toccati: `src/meshrec/core/hexa.py`, `tests/test_hexa.py`.

## A1 — telaio senza legami: avvisa invece di uscire muto

Aggiunto `MembratureNonLegateWarning(UserWarning)` e, in `costruisci`, un insieme `connesse` popolato solo quando un `*TIE` viene davvero creato (non quando una giunzione geometrica esiste ma la superficie è vuota). `metriche["membrature_non_legate"] = len(non_legate)`; se `> 0`, `warnings.warn`. Nessuna soglia: lo stato "non legata" è binario (compare in `ties` o no), come richiesto da Ruling Z — non solleva.

Verificato a mano (colonna e trave a 0,1 mm di gioco, prima del test): `membrature_non_legate == 2`, un `MembratureNonLegateWarning` emesso, `ties == ()`. Provenienza: nessuna sovrapposizione lungo l'asse campionato → `taglia_giunzioni` non taglia nulla → nessuna giunzione → nessun tie possibile con due sole membrature.

## A2 — sovrapposizione d'angolo: guardia additiva

Aggiunta, solo quando la retta baricentrica non trova invasione, una scansione delle quattro rette dei vertici del contorno minore (stessa `dentro`, stessi `_CAMPIONI_ASSE`). Se una qualunque è invasa, `ValueError`. Nessuna modifica al ramo dove la baricentrica già trova invasione: la geometria del test originale (`test_due_prismi_che_si_compenetrano...`) e quella dell'attraversamento restano identiche, verificato dalla suite che passa invariata.

Riprodotto con la geometria del brief (colonna 400×400×1000, trave 100×100×500 a origine `[-400,-80,500]`): prima del fix, `taglia_giunzioni` tornava `giunzioni: []` silenziosamente; con il fix, solleva `ValueError` con `"sovrapposizione d'angolo"`.

## A3 — `giunzioni` e `ties` sono due campi distinti

`"giunzioni": len(giunzioni)` (era `len(ties)`), aggiunto `"ties": len(ties)`. Verificato che i due numeri coincidono nel caso buono (`test_il_telaio_costruito_dichiara_le_superfici_del_tie`, ora con entrambe le assert) e divergono quando `_TOLLERANZA_CONTATTO = 0.0` (`test_una_superficie_vuota_non_produce_un_tie`: `giunzioni == 1`, `ties == 0`).

## A4 — `primitive` squadra su `membratura.sezione`

`prisma_di("primitive")` ora legge `membratura.sezione` invece di `np.ptp(membratura.contorno, axis=0)`. Verificato in `wall.py` che `sezione` e `contorno` condividono la stessa base di piano (`e1, e2`) prima e dopo `semplifica_contorno` (`wall.py:433-508`), quindi il cambio è dimensionalmente corretto e non un confronto fra basi diverse. Fixture `_membratura_finta` ora accetta un parametro `sezione` esplicito (default = `ptp(contorno)`, invariato per i test che non lo passano); nuovo test che passa una `sezione` diversa dal `ptp` del contorno e verifica che `primitive` la usi.

## B1, B2 — le due guardie senza test

Aggiunti `test_un_prisma_interamente_contenuto_in_un_altro_e_rifiutato` e `test_una_superficie_vuota_non_produce_un_tie`. Per ciascuno ho applicato la mutazione indicata dal revisore (`if invaso[0] and invaso[-1]:` → `if False:`; `if superfici[nomi[0]] and superfici[nomi[1]]:` → `if True:`), rieseguito il test mirato, confermato il fallimento, e ripristinato il file con `diff` a conferma di nessuna differenza residua. Dettaglio nella tabella sotto.

## B3 — numeri corretti nel docstring del test di taglio

Ricalcolati in proprio (non copiati dal brief) sulla geometria del banco (colonna 200×200×1400, trave 300×200×1400 a quota 1300):
- volume senza taglio: `200²·1400 + 300·200·1400 = 140.000.000 mm³` contro il volume corretto `136.000.000 mm³` → eccesso `2,941%` (non 8,8%, che era il residuo dopo la cura, un'altra grandezza).
- accorciamento senza bisezione: fermandosi sull'ultimo campione libero, la colonna si accorcia a `1294,472` invece di `1300` → accorciamento `105,528` (non 94,5: fermarsi sul campione taglia *di più*, non di meno).
- volume senza bisezione: `200²·1294,472 + 300·200·1400 = 135.778.894,72 mm³`, in **difetto** dello `0,163%` rispetto al corretto (non in eccesso dello 0,16%).

Tutti e tre ricontrollati con un calcolo indipendente (non dall'esecuzione del revisore né dal brief originale) prima di scrivere il testo corretto.

## B4 — narrazione corretta sulla guardia dell'attraversamento

Il docstring e il commento nel codice ora dicono che senza la guardia si arriva a `passo[libero[-1] + 1]` con `libero[-1] == _CAMPIONI_ASSE - 1`, fuori dall'array dei campioni → `IndexError`, non un accorciamento di zero silenzioso. La guardia resta (un `IndexError` non è comunque una diagnosi utile per l'operatore).

## B5, B6 — numeri del banco tolti da `src/`

Rimossi da `hexa.py`: "sette millimetri" e "3,4e-12 mm" nel docstring di `_PASSI_BISEZIONE` (sostituiti con la ragione generale: 2^40 ≈ 1,1e12, qualunque intervallo fino al centimetro scende sotto 1e-11 mm); "20 e 12 facce" nel docstring di `_TOLLERANZA_CONTATTO`; "5,5 mm sul banco del telaio" nel docstring di `taglia_giunzioni` (sostituito con `lunghezza / (_CAMPIONI_ASSE - 1)`, la formula generale). `rg` su tutto `src/` per numeri del provino (1400, 1300, 200×200, 300×200, banco di prova): l'unico risultato è una riga preesistente in `synth.py:105` non toccata da questo giro, che nomina "banco di prova" come principio generale ("mai del codice") senza portare un numero — non è del tipo che B5/B6 vieta.

## B7 — fattore corretto: nove, non sei

Verificato con `passo_di_mesh` e `ModelConfig()`: sezione 1000×10 → passo 3,333 mm; sezione 90×90 → passo 30,0 mm; rapporto 9,0 (non sei). Commento in `costruisci` corretto con i due valori espliciti.

## I cinque test nuovi — mutazione dichiarata, applicata, verificata

| Test | Mutazione | Applicata? | Esito con la mutazione |
|---|---|---|---|
| `test_un_telaio_senza_legami_avvisa_invece_di_uscire_muto` (A1) | `if non_legate:` → `if False:` | Sì | `Failed: DID NOT WARN` |
| `test_una_sovrapposizione_d_angolo_che_la_baricentrica_non_vede_e_rifiutata` (A2) | `if vertice_invaso:` → `if False:` | Sì | `Failed: DID NOT RAISE ValueError` |
| `test_il_modello_primitive_squadra_sulla_sezione_misurata_non_sul_contorno` (A4) | `membratura.sezione` → `np.ptp(membratura.contorno, axis=0)` | Sì | `assert array([200., 140.]) == approx((210.0, 150.0))` fallita |
| `test_un_prisma_interamente_contenuto_in_un_altro_e_rifiutato` (B1) | `if invaso[0] and invaso[-1]:` → `if False:` | Sì | `IndexError: index 0 is out of bounds for axis 0 with size 0` (il codice prosegue oltre la guardia mancante e si schianta più avanti, invece di sollevare il `ValueError` atteso — comunque un fallimento del test) |
| `test_una_superficie_vuota_non_produce_un_tie` (B2) | `if superfici[nomi[0]] and superfici[nomi[1]]:` → `if True:` | Sì | `assert 1 == 0` (`ties` diventa 1 invece di 0) |

Verificata anche, per completezza, la mutazione di A3 (`"giunzioni": len(giunzioni)` → `"giunzioni": len(ties)`): non uccide `test_il_telaio_costruito_dichiara_le_superfici_del_tie` (lì `giunzioni == ties == 1`, la mutazione non cambia nulla) ma uccide `test_una_superficie_vuota_non_produce_un_tie` (`assert 0 == 1` fallita), che è il test dedicato a rendere visibile la divergenza fra i due campi. Tutte le mutazioni ripristinate subito dopo la verifica; `diff` contro la copia pre-mutazione conferma nessuna differenza residua.

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **492 passed** (487 base del task 8 + 5 test nuovi di questo giro), 3 warning: i due `MembratureNonLegateWarning` attesi (emessi da test che costruiscono deliberatamente membrature scollegate — non asseriti via `pytest.warns` perché non è quello l'oggetto di quei test) più 1 `UnmetQualityConstraintWarning` preesistente in `test_volume.py`, non correlato.

## Rilievi su cui non ho trovato disaccordo

Ho verificato in proprio ciascuno dei numeri "riprodotti dal coordinatore" prima di fidarmene (A2: sovrapposizione d'angolo confermata con `ValueError` reale; B1: contenimento confermato; B3: tutti e tre i numeri ricalcolati indipendentemente e coincidenti; B7: rapporto 9,0 confermato con `passo_di_mesh` reale). Nessuno mi è risultato falso: non ho trovato un quinto caso in cui il piano avesse torto.

## Commit

Un solo commit con `hexa.py` e `test_hexa.py` (codice e docstring insieme — nessuna ragione per separarli, le correzioni ai docstring sono minime e nello stesso file dei test che le motivano).

---

# Giro di correzione 2 di 5 (`task-8-fix-1.md`, coda)

## Stato: DONE

## Cosa è stato fatto

Sei dei sette punti della re-review sul giro 1 non richiedevano nulla (verificati dal coordinatore eseguendo, non da me in questo giro). Il settimo — l'ancoraggio del rettangolo `primitive`, Ruling AB — era un difetto residuo prescritto sbagliato nel giro 1 stesso: "tieni l'ancoraggio attuale (minimo del contorno) e cambia solo le due estensioni" è la combinazione peggiore, perché le estensioni vengono ora dai punti grezzi (`membratura.sezione`) mentre il minimo viene dal contorno già semplificato — due fonti diverse, e `semplifica_contorno` può togliere proprio il vertice che realizza il minimo grezzo.

File toccati: `src/meshrec/core/hexa.py`, `tests/test_hexa.py`.

## Verifica del bug prima di toccare codice

Riprodotto con `wall.semplifica_contorno` vera (non un mock), rettangolo 200×140 con una gobba di 5 mm sul lato x negativo:

```
grezzo ptp: (205.0, 140.0)
semplificato: [[0,0],[200,0],[200,140],[0,140]]  (minimo [0,0])
```

Coincide esattamente con i numeri del coordinatore (`grezzo x in [-5, 200]`, `sezione = (205, 140)`, `contorno semplificato x in [0, 200]`): con l'ancoraggio al minimo il rettangolo va da 0 a 205, inventando 5 mm dove il materiale finisce a 200 e non coprendo i 5 mm dove il materiale c'era davvero (`x in [-5, 200]`).

## Fix — Ruling AB emendato

`prisma_di("primitive")` ancora il rettangolo al centro del contorno (`(minimo + massimo) / 2`), non al minimo. Le estensioni restano da `membratura.sezione` (invariato dal giro 1 — quella parte del Ruling AB era corretta). Il commento in `prisma_di` è stato riscritto per spiegare anche perché l'ancoraggio è il centro, non solo perché le estensioni vengono da `sezione`.

Nessun numero introdotto in `src/`: la formula (`centro ± sezione/2`) è generale, nessun 200/140/205 nel sorgente.

## TDD

RED: nuovo test `test_il_modello_primitive_ancora_il_rettangolo_al_centro_non_al_minimo` — contorno pulito 200×140 (minimo `[0,0]`, centro `[100,70]`), `sezione` deliberatamente diversa `(210,150)` (stessa trappola di A4: se minimo e centro coincidessero il test non vedrebbe nulla). Eseguito prima del fix: fallisce con `assert array([0., 0.]) == approx([-5.0, -5.0])` — il codice vecchio ancora al minimo `[0,0]`, non al centro atteso.

GREEN: applicato il fix, stesso test passa; tutti i 23 test di `test_hexa.py` passano.

Mutazione dichiarata nel docstring del test applicata davvero: `centro = (min+max)/2` → `centro = min` (ripristinando l'ancoraggio vecchio). Uccide il test (`assert array([0., 0.]) == approx([-5.0, -5.0])`, stesso fallimento del RED). Ripristinato subito dopo; `diff` contro la copia pre-mutazione conferma nessuna differenza residua.

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **494 passed** (493 base di questo giro + 1 test nuovo), 2 warning: 1 `MembratureNonLegateWarning` atteso (`test_una_superficie_vuota_non_produce_un_tie`, invariato dal giro 1) + 1 `UnmetQualityConstraintWarning` preesistente in `test_volume.py`, non correlato.

## Rilievo su cui non ho trovato disaccordo

Il numero del coordinatore era corretto bit per bit (verificato con `wall.semplifica_contorno` reale, non riletto dal suo messaggio): non ho trovato un sesto caso in questa fase in cui il piano avesse torto — qui aveva ragione, ed era la sua stessa correzione precedente a sbagliare, come dichiarato.

## Commit

Un solo commit con `src/meshrec/core/hexa.py` e `tests/test_hexa.py`.

---

# Giro di correzione 3 di 5 (`task-8-fix-3.md`)

## Stato: DONE_WITH_CONCERNS

Nessun blocco: la correzione consegnata funziona, verificata, senza regressioni. `DONE_WITH_CONCERNS` perché il punto 3 (perché 4 giunzioni e solo 2 `*TIE`) resta una limitazione nota e documentata del metodo attuale di rilevazione delle superfici, non risolta — come esplicitamente richiesto dal brief ("non ti chiedo di forzarle a diventare quattro").

## Cosa è stato fatto

Il difetto: `hexa.costruisci` sollevava `ValueError` (sovrapposizione d'angolo) sul `TELAIO` reale di `tests/test_wall.py`. Causa reale: `taglia_giunzioni` sceglieva chi cede per sezione minore, e su una coppia del telaio questo sceglie il ruolo sbagliato — il montante entra nel traverso da sotto, e accorciare il traverso lungo il proprio asse non toglie quella sovrapposizione. La guardia d'angolo del Ruling Y (giro 1) faceva esattamente il suo lavoro, rendendo visibile l'errore invece di lasciarlo contare due volte il volume in silenzio.

File toccati: `src/meshrec/core/hexa.py`, `tests/test_hexa.py`.

## Verifica prima di implementare

Letta la patch sperimentale allegata (`/Users/mario/.claude/jobs/e87eb542/tmp/esperimento-asse-invaso.patch`) solo come misura, non applicata: confermava che il criterio giusto è "cede chi ha l'asse baricentrico invaso nell'altro", con una funzione annidata nel doppio ciclo. Riprodotto in proprio, con la pipeline vera di `wall.py` (`scarta_pavimento`, `scomponi`, `terna`, `misura`, `controlla` — gli stessi passi di `wall.prior`, non letti dal messaggio del coordinatore) sul `TELAIO` di `tests/test_wall.py`: confermate le quattro aree misurate (43188, 126870, 62735, 39484 mm², arrotondate) e il fatto che `costruisci` con il codice pre-fix solleva esattamente l'errore riportato.

Nessuno stash trovato nel worktree, nessuna modifica estranea nell'albero (verificato `git status`/`git stash list` prima di toccare qualunque cosa).

## Fix — Ruling AD

Nuova funzione `_asse_baricentrico_invaso(prisma, altro)` (estratta, non annidata, riusata due volte per coppia — una per verso) in `taglia_giunzioni`: per ogni coppia si campionano entrambi i versi; se uno solo dei due assi è invaso, quel prisma cede; se entrambi o nessuno lo sono, l'area resta lo spareggio deterministico (comportamento identico a prima in questi due casi, verificato dai 24 test che passano invariati). Il resto della funzione (bisezione, guardie di attraversamento/contenimento, guardia d'angolo del Ruling Y) non è stato toccato, solo i riferimenti a `tagliati[maggiore]` rinominati in `tagliati[maggiore_effettivo]` dove il ruolo può essere scambiato. Docstring di `taglia_giunzioni` riscritto per il nuovo criterio, col significato fisico dichiarato (una trave appoggiata su un pilastro accorcia il pilastro, non la trave).

## TDD

Test nuovo `test_il_telaio_a_quattro_membrature_si_costruisce_ruling_ad`: costruisce le membrature del `TELAIO` con la pipeline vera di `wall.py` (non `_membratura_finta`, perché con due soli prismi il criterio per area e quello per asse invaso coincidono sempre — il banco a due prismi non poteva vedere questo difetto) e verifica che `costruisci` non sollevi, con 4 blocchi, `giunzioni == 4`, `membrature_non_legate == 0`.

Eseguito con il fix: PASS. Mutazione dichiarata nel docstring applicata davvero (ripristinato il criterio per area, rimuovendo il confronto fra i due assi): il test muore con lo stesso `ValueError: ... sovrapposizione d'angolo ...` riportato dal coordinatore all'apertura del giro — la prova che il criterio vecchio è esattamente la causa. Ripristinato subito dopo; `diff` contro la copia pre-mutazione conferma nessuna differenza residua.

## Indagine (punto 3): perché 4 giunzioni e solo 2 `*TIE`

Non è un difetto del taglio. Misurato in questa sessione (script temporanei in `/tmp`, non nel repo), chiamando `hexa.costruisci` una sola volta e leggendo `nodi`/`elementi`/`blocchi` dal suo stesso risultato (per evitare di rimescolare mesh generate in chiamate separate):

- **GIUNZIONE_2** (montante sinistro dentro traverso inferiore): il lato dipendente trova nodi e facce (14 nodi, 6 facce); il lato indipendente (traverso inferiore, il prisma più grande e con passo di mesh più grosso, 113,33 mm) ha **zero** nodi dentro il montante tagliato. Causa: il contatto vero, sul contorno *come misurato* (che per il traverso inferiore non è un rettangolo pulito ma un poligono a sei vertici, con un rigonfiamento residuo della compenetrazione che `sample_frame_surface` lascia apposta nella nuvola), cade in una fascia più stretta del passo di mesh del lato più grande: nessun nodo della sua griglia, per costruzione, ci casca dentro.
- **GIUNZIONE_3** (montante destro dentro traverso superiore): qui il lato dipendente **ha** nodi (5) ma **zero facce**: nessuna faccia dell'esaedro ha tutti e quattro i vertici nell'insieme dei nodi a contatto — i nodi trovati sono pochi e non abbastanza contigui da coprire una faccia intera. Il lato indipendente invece ha 10 nodi e 4 facce.
- **GIUNZIONE_1** e **GIUNZIONE_4** (quelle che diventano `*TIE`): entrambi i lati hanno nodi e facce (5+4 e 3+8 rispettivamente).

Il meccanismo è lo stesso in entrambi i casi falliti: la rilevazione delle superfici a contatto confronta due mesh generate **indipendentemente**, ciascuna con il proprio passo (funzione della propria sezione, non della giunzione), contro il contorno esatto dell'altro prisma — esattamente il limite che il docstring di `costruisci` dichiara già ("la mesh conforme multiblocco resta la via d'aggiornamento"), qui osservato con numeri reali per la prima volta. Il taglio ha comunque tolto la doppia contabilità del volume in tutte e quattro le giunzioni (il suo unico compito): la mancanza di `*TIE` non rimette in dubbio quello.

**Non ho corretto nulla su questo punto**, come richiesto: ho scritto il meccanismo (generale, senza numeri del banco) nel commento sopra la costruzione delle superfici in `costruisci`, e riporto qui i numeri misurati per la decisione del coordinatore.

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **501 passed** (500 base di questo giro + 1 test nuovo), 2 warning: 1 `MembratureNonLegateWarning` atteso (test preesistente, invariato) + 1 `UnmetQualityConstraintWarning` preesistente in `test_volume.py`, non correlato.

## Rilievo su cui non ho trovato disaccordo

La diagnosi del coordinatore (causa: criterio di scelta del cedente, non la guardia d'angolo) e i suoi numeri (aree delle quattro membrature) sono risultati corretti alla riproduzione indipendente. Non ho trovato un settimo caso in questa fase in cui il piano avesse torto in questo giro.

## Commit

Un solo commit con `src/meshrec/core/hexa.py` e `tests/test_hexa.py`.

---

# Giro di correzione 4 di 5 (`task-8-fix-3.md`, seguito)

## Stato: DONE_WITH_CONCERNS

## Cosa è stato fatto

Implementato Ruling AE: la tolleranza di contatto usata in `costruisci` non è più solo `_TOLLERANZA_CONTATTO` (costante di modulo), ma `max(_TOLLERANZA_CONTATTO, giunzione["cuneo"])` per ciascuna giunzione. Il cuneo è calcolato in `taglia_giunzioni` da ogni vertice del contorno di chi cede sulla faccia di taglio, con bisezione lungo l'asse di chi cede fino al vero bordo di chi riceve (`_cuneo_vertice`), e vale il massimo sui vertici. Aggiunto `GiunzioneSenzaTieWarning` (avviso quando una giunzione tagliata non produce un `*TIE`, analogo a `MembratureNonLegateWarning`). Corretto il commento in `costruisci` che attribuiva la causa delle giunzioni senza `*TIE` al passo di mesh: la causa è il fuori squadra (il cuneo), non la discretizzazione — la vecchia attribuzione era sbagliata, come segnalato dal coordinatore.

File toccati: `src/meshrec/core/hexa.py`, `tests/test_hexa.py`.

## Root cause, verificato prima di scrivere il fix

Confermato (albero pulito, nessuno stash, nessuna modifica estranea, verificato prima di toccare qualunque cosa): il meccanismo è quello descritto — il taglio produce una faccia piana perpendicolare all'asse di chi cede, e se le due membrature non sono in squadra quella faccia non coincide con la superficie di chi riceve altrove nel contorno.

## Un problema reale trovato e risolto durante l'implementazione: la ricerca del cuneo doveva avere un limite

La prima versione di `_cuneo_vertice` cercava il bordo raddoppiando il passo senza alcun tetto. Su un vertice del telaio reale (giunzione montante destro / traverso superiore) questo ha prodotto un cuneo di **117,33 mm** — verificato due volte con metodi di ricerca diversi (campionamento uniforme e raddoppio), stesso risultato entrambe le volte, quindi non un artefatto di risoluzione. Un valore di quella scala è fisicamente implausibile per un fuori squadra di meno di un grado (che sugli altri vertici della stessa giunzione produce cunei sotto il millimetro): `dentro` lungo una retta non è monotona (il prisma ha un'estensione finita anche lungo `versore`, che non è il proprio asse), e la ricerca aveva agganciato un'invasione lontana e indipendente, non il cuneo vero.

Corretto limitando la ricerca a `4 × passo di _CAMPIONI_ASSE` (quel passo è già dichiarato altrove come la scala sotto cui sta qualunque giunzione): con questo limite tutti i cunei del telaio tornano a un ordine di grandezza fisicamente plausibile (sotto il millimetro), e i 25 test di `test_hexa.py` restano verdi.

## Requisito 2 — quante giunzioni diventano `*TIE`: misurato, non assunto

**Sul telaio a quattro membrature, con Ruling AE: `ties == 2`, invariato rispetto al giro 3** (non 3, non 4). Misurato con `hexa.costruisci` vero, non assunto. Le giunzioni 2 e 3 (nella numerazione di questa sessione) restano senza `*TIE`.

Indagando perché: sulla giunzione 2 (montante sinistro / traverso inferiore), tutti i vertici del contorno di chi cede risultano già dentro il volume di chi riceve (cuneo = 0 su tutti) — il problema lì non è un cuneo da fuori squadra ma, come già trovato nel giro 3, la mancanza di nodi mesh del lato indipendente (il membro grande, a passo di mesh più grosso) nella regione di contatto: un problema di risoluzione della mesh indipendente, non di geometria del taglio. Sulla giunzione 3, un solo vertice su sei richiede una ricerca (gli altri cinque sono già dentro); quel vertice, con il limite di ricerca principiato, non trova alcun bordo entro 4× il passo di campionamento e il suo contributo resta zero.

## Disaccordo con i numeri del coordinatore — segnalato, non forzato

I numeri per-giunzione riprodotti in questa sessione **non coincidono** con quelli riportati dal coordinatore (`cuneo per vertice [9.93, 9.93, 0.93, 1.59, 1.59, 0.93]` per la sua GIUNZIONE_1, `[1.29]` per la sua GIUNZIONE_3, eccetera): nella mia numerazione, la giunzione corrispondente a "montante destro / traverso inferiore" ha **tutti** i sei vertici già dentro (cuneo 0 su tutti), non sei valori distinti nell'intervallo 0,93–9,93 mm. Solo la GIUNZIONE_4 del coordinatore (0,42 mm) coincide quasi esattamente con la mia (0,429 mm).

Non ho forzato il codice per far tornare i suoi numeri. Ho verificato la mia implementazione in tre modi indipendenti (formula chiusa `100·tan(1°) = 1,7455 mm` su un banco sintetico costruito apposta, confermata a 10 cifre decimali; nessuna regressione sui 25 test; il caso limite del banco squadrato degenera davvero a zero). L'ipotesi più probabile è che la sua "prova grezza" (esplicitamente dichiarata tale, con una funzione annidata e zero test) numerasse le giunzioni diversamente o avesse un proprio limite di ricerca diverso dal mio — ma non l'ho potuto verificare, perché la patch sperimentale allegata non includeva il calcolo del cuneo, solo il cambio di criterio di Ruling AD. Segnalo la discrepanza qui invece di adattare la mia ricerca finché i numeri non tornassero uguali ai suoi: sarebbe stata esattamente la forma di errore che questa fase ha già corretto cinque volte.

## I quattro punti da consegnare

1. **Cuneo calcolato e usato come tolleranza**: fatto, `_cuneo_vertice` + `max(_TOLLERANZA_CONTATTO, giunzione["cuneo"])`. Via scelta: bisezione per vertice lungo l'asse di chi cede (come suggerito), con un limite di ricerca derivato dalla geometria (non un raggio a caso) per evitare di agganciare invasioni lontane — verificato che serve (117,33 mm senza limite, valori sotto il millimetro con il limite).
2. **Quante giunzioni diventano `*TIE`**: misurato, `ties == 2` (invariato). Riportato, non forzato a quattro.
3. **Avviso su giunzione senza `*TIE`**: `GiunzioneSenzaTieWarning`, con test dedicato e mutazione applicata e verificata.
4. **Commento corretto**: la causa non è più attribuita al passo di mesh nel commento sopra la costruzione delle superfici in `costruisci`; ora attribuita al fuori squadra (cuneo), con la correzione dichiarata esplicitamente nel testo.

## I due test nuovi — mutazione dichiarata, applicata, verificata

| Test | Mutazione | Applicata? | Esito con la mutazione |
|---|---|---|---|
| `test_il_cuneo_e_calcolato_dalla_geometria_e_allarga_le_facce_a_contatto` | `tolleranza = max(_TOLLERANZA_CONTATTO, giunzione["cuneo"])` → `tolleranza = _TOLLERANZA_CONTATTO` | Sì | Facce 20/9 → 9 (assert su 20 fallita: `assert 9 == 20`) |
| `test_una_superficie_vuota_non_produce_un_tie` (estensione, requisito 3) | `if giunzioni_senza_tie:` → `if False:` | Sì | `Failed: DID NOT WARN` |

Entrambe le mutazioni ripristinate subito dopo la verifica; `diff` contro la copia pre-mutazione conferma nessuna differenza residua in entrambi i casi.

L'assert `modello["metriche"]["ties"] == 2` aggiunto al test del giro 3 (`test_il_telaio_a_quattro_membrature_si_costruisce_ruling_ad`) non è un test nuovo con una propria mutazione dichiarata: è un blocco di regressione su un numero misurato, verificato per costruzione durante l'iterazione stessa (l'ho visto cambiare da "nessun assert" a "2" più volte mentre calibravo il limite di ricerca del cuneo).

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **502 passed** (501 base di questo giro + 1 test nuovo), 3 warning: 2 attesi (`GiunzioneSenzaTieWarning`, `MembratureNonLegateWarning`, entrambi da test che costruiscono deliberatamente quello scenario) + 1 `UnmetQualityConstraintWarning` preesistente in `test_volume.py`, non correlato.

## Nessun numero del provino in `src/`

Verificato con `git diff` mirato sulle righe aggiunte: nessun numero del telaio (1600, 1400, 300, 200, ecc.) è entrato in `hexa.py`. I numeri del banco sintetico usato per il test del cuneo (colonna 200×200, angolo 1°) stanno solo in `test_hexa.py`.

## Commit

Un solo commit con `src/meshrec/core/hexa.py` e `tests/test_hexa.py`.

---

# Giro di correzione 5 di 5 (`task-8-fix-3.md`, ultimo seguito)

## Stato: DONE_WITH_CONCERNS

## Cosa è stato fatto

1. **`abaqus.tie_surface`** (nuova funzione, accanto a `element_surface` che non è stata toccata): le coppie (elemento, faccia) di bordo il cui **baricentro** cade dentro l'altro solido, invece che i nodi tutti dentro. `dentro_altro` è geometria iniettata come funzione (punti → booleani), non un import di `hexa.Prisma`/`hexa.dentro`, per non creare un ciclo (`hexa.py` già importa `abaqus.py`). Riusa `boundary_faces` (non toccata) per il filtro sulle sole facce di pelle.
2. **`hexa.costruisci`** usa `tie_surface` al posto di `element_surface` per le superfici del `*TIE`, ristretto agli elementi del blocco (membratura) di ciascun ruolo D/I, con la tolleranza di Ruling AE invariata (`max(_TOLLERANZA_CONTATTO, giunzione["cuneo"])`).
3. Docstring aggiornati: la ragione fisica del criterio diverso in `tie_surface` (un vincolo è una questione di area sovrapposta, un carico di nodi nominati senza ambiguità); il commento in `costruisci` con la motivazione testuale dell'utente per il criterio scelto al posto dell'infittimento mesh (mesh omogenea vs. variazione di densità proprio dove le sollecitazioni sono massime).
4. Test aggiornati con i numeri **misurati**, non assunti: `ties == 4` sul telaio a quattro membrature (era 2), facce 20/12 sul banco a due prismi col cuneo (erano 20/9 col vecchio criterio per nodi).
5. Nuovo test `feasibility` con `ccx` vero sul telaio a quattro membrature.

File toccati: `src/meshrec/core/abaqus.py`, `src/meshrec/core/hexa.py`, `tests/test_abaqus.py`, `tests/test_hexa.py`, `tests/feasibility/test_calculix.py`.

## Il giro 4 è stato riconfermato corretto

Rilette le due mutazioni di Ruling AE (`max(...)` → costante, `if giunzioni_senza_tie` → `if False`) su questo codice: entrambe uccidono ancora i rispettivi test, riverificate in questa sessione (non solo fidandomi della riverifica del coordinatore).

## Requisito 2 — quante giunzioni diventano `*TIE`: misurato

**`ties == 4` su 4, come previsto dal coordinatore.** Misurato con `hexa.costruisci` vero: `nomi ties: ['GIUNZIONE_1', 'GIUNZIONE_2', 'GIUNZIONE_3', 'GIUNZIONE_4']`, facce per lato `D`/`I` — 12/4, 9/2, 5/8, 21/20 — che coincidono esattamente con i numeri "per baricentro" che il coordinatore aveva calcolato prima di dispacciare. Nessuna regressione sul banco a due prismi (requisito 4): i test esistenti passano invariati.

## Requisito 5 — l'avviso, aggiornato e col caso opposto

`test_il_telaio_a_quattro_membrature_si_costruisce_ruling_ad` aggiornato da `ties == 2` a `ties == 4`. Il caso opposto (una giunzione che resta senza `*TIE`) **esiste già**: `test_una_superficie_vuota_non_produce_un_tie` (tolleranza di contatto azzerata via monkeypatch) produce ancora una superficie vuota sotto il nuovo criterio, verificato che passa. Mutazione di `GiunzioneSenzaTieWarning` (`if giunzioni_senza_tie:` → `if False:`) riverificata in questa sessione sul codice nuovo: uccide il test.

## Requisito 6 — il controllo col solutore vero, e quello che ha trovato

**Il test `feasibility` esiste, gira, ed è rosso.** Non l'ho reso verde adattando la soglia o il criterio: è la scoperta che il requisito 6 chiedeva di fare.

Misurato con `ccx` vero sul deck del telaio a quattro membrature: `tie constraints: 4` (tutti e quattro registrati) ma **61 avvisi** `*WARNING in gentiedmpc: no tied MPC`, uno per ciascun nodo della superficie dipendente che non trova una faccia opposta entro la tolleranza interna di CalculiX ("no opposite master face found; in-face tolerance: 0.3838..."). Il job finisce comunque (`returncode == 0`), che è esattamente il modo di fallire in silenzio che questo controllo esiste per scoprire.

**Non è una regressione di questo giro.** Prima di scrivere il report ho confrontato: ripristinato temporaneamente (non con `git stash`, con una copia manuale del file, poi ripristinata e verificata con `diff` vuoto) il criterio per nodi del giro 4 sullo stesso telaio — `ties == 2` (come nel giro 4) ma **21 avvisi** `no tied MPC` sulle stesse due giunzioni che il controllo interno dichiarava legate. Il divario fra "la nostra superficie ha facce" (vero, per entrambi i criteri) e "CalculiX lega ogni nodo di quella superficie" (falso, per entrambi i criteri, su questo telaio) è precedente a Ruling AF e non introdotto da esso: semplicemente nessuno lo aveva ancora misurato sul telaio reale a quattro membrature — le uniche verifiche precedenti con `ccx` reale (giro 1) erano sul banco a due prismi, più semplice, dove il vincolo legava senza nodi falliti.

**Non ho tentato una correzione non richiesta.** La via più diretta sarebbe una card `POSITION TOLERANCE` sul `*TIE` in `abaqus.write_inp`, che oggi non esiste: cambiarla è una decisione (quale tolleranza, e se derivarla anche lei dal cuneo) che non rientra nello scopo dichiarato di questo giro, che era il criterio di selezione delle facce, non la card del vincolo. Segnalo la via, non la imbocco.

## Nessun numero del provino in `src/`

Verificato con `git diff` mirato: nessun numero del telaio in `abaqus.py` o `hexa.py`.

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **504 passed** (502 base di questo giro + 2 test nuovi in `test_abaqus.py`), 2 warning preesistenti/attesi, non correlati.

`uv run pytest tests/feasibility -m feasibility -q` → 6 passed, 1 skipped (dipendenza non presente), **1 failed** — il nuovo test, per la ragione sopra. Non incluso nella suite di default (`addopts = "-m 'not feasibility'"`), quindi il numero di 504 sopra non lo conta, come per gli altri test `feasibility` già esistenti.

## I quattro test nuovi — mutazione dichiarata, applicata, verificata

| Test | Mutazione | Applicata? | Esito con la mutazione |
|---|---|---|---|
| `test_la_superficie_del_tie_nomina_la_faccia_il_cui_baricentro_e_dentro` | criterio per baricentro → per nodi (tutti dentro) | Sì | `assert [] == [(0, 1)]` |
| `test_la_superficie_del_tie_non_include_una_faccia_interna_condivisa` | filtro sul bordo rimosso | Sì | `assert 12 == 10` |
| `test_una_superficie_vuota_non_produce_un_tie` (estensione, `GiunzioneSenzaTieWarning`, rivalidata) | `if giunzioni_senza_tie:` → `if False:` | Sì | `Failed: DID NOT WARN` |
| `test_il_cuneo_e_calcolato_dalla_geometria_e_allarga_le_facce_a_contatto` (numeri aggiornati, mutazione rivalidata) | `tolleranza = max(...)` → costante | Sì | facce 20/12 → 10/6 |

Il test `feasibility` non ha una mutazione dichiarata nel senso usuale (non è una singola riga di logica invertibile): la sua prova di validità è il confronto A/B col criterio del giro precedente sullo stesso telaio, riportato sopra, che mostra lo stesso sintomo con codice diverso — cioè che il test misura davvero il solutore e non un artefatto del criterio scelto in questo giro.

Tutte le mutazioni ripristinate subito dopo la verifica; `diff` contro la copia pre-mutazione conferma nessuna differenza residua in ogni caso.

## Rilievo su cui non ho trovato disaccordo

I numeri per-giunzione del coordinatore ("per baricentro": 12/4, 9/2, 5/8, 21/20) coincidono esattamente con quelli misurati in questa sessione. La sua causa dichiarata dell'errore del giro 4 (l'estremità sbagliata del prisma tagliato) è coerente con quanto osservato: nessun disaccordo trovato su questo punto in questo giro.

## Commit

Un solo commit con `src/meshrec/core/abaqus.py`, `src/meshrec/core/hexa.py`, `tests/test_abaqus.py`, `tests/test_hexa.py`, `tests/feasibility/test_calculix.py`.

---

# Giro di correzione 6 (Ruling AH)

## Stato: DONE

## Cosa è stato fatto

1. **`abaqus.tie_surface`** ha ora un parametro `tocca: bool = False`: se `True`, una faccia entra nella superficie anche se solo un suo nodo (non il baricentro) cade dentro l'altro solido. Usato solo sul lato **indipendente** (mesh più rada, facce più grandi che possono coprire solo in parte la zona di contatto); il lato dipendente resta a `tocca=False`, già giusto sulla faccia di taglio piana — misurato che scambiare i ruoli peggiora (esperimento B3 del coordinatore, non re-implementato: dichiarato come scartato nel docstring).
2. **`POSITION TOLERANCE`** sulla card `*TIE` in `abaqus.write_inp`: quarto elemento opzionale della tupla `ties`. Assente (tupla a 3 elementi) quando il valore calcolato è zero (banco squadrato) — mai scritta a zero esplicito, che per CalculiX non è neutro rispetto a "parametro assente".
3. In `hexa.taglia_giunzioni`, la tolleranza di posizione per giunzione è `estensione_del_contorno_di_chi_cede * |dot(versore_piccolo, versore_maggiore)|` — il prodotto scalare di due versori dà esattamente il seno dell'angolo di scostamento dalla perpendicolarità, senza bisogno di arcoseno.
4. `metriche["nodi_dipendenti_legati"]` / `["nodi_dipendenti_totali"]`: conteggio interno (non una lettura del solutore) di quanti nodi della superficie dipendente hanno un punto della superficie indipendente — la faccia intera, via `_distanza_punto_faccia` (nuovo helper: proiezione sul piano del quadrilatero, clampata al perimetro se la proiezione cade fuori) — entro la tolleranza di posizione.
5. Il test `feasibility` col solutore ora pretende `ties == 4` e avvisi `no tied MPC` sotto un tetto misurato (30, con margine sopra i 24 osservati), non più zero assoluto.

File toccati: `src/meshrec/core/abaqus.py`, `src/meshrec/core/hexa.py`, `tests/test_abaqus.py`, `tests/test_hexa.py`, `tests/feasibility/test_calculix.py`.

## Un errore di processo trovato e corretto durante il lavoro

La prima versione di `metriche["nodi_dipendenti_legati"]` era banale: contava "quanti nodi della superficie dipendente stanno in una faccia della superficie dipendente", che è per costruzione uguale al totale (ogni nodo di una faccia selezionata appartiene a quella superficie). Corretto confrontando invece i nodi dipendenti con la superficie **indipendente**. La prima correzione (distanza dal nodo indipendente più vicino) sottostimava pesantemente (5/79): i nodi del lato indipendente sono radi (mesh grossa), e un nodo dipendente può proiettarsi vicino al centro di una faccia indipendente lontano da ogni suo angolo. Corretto con una vera distanza punto-faccia (`_distanza_punto_faccia`), che ha portato la misura a 55/79 — molto vicina ai 55 nodi che il solutore vero lega effettivamente su questo stesso telaio (79 − 24 avvisi = 55), verificato di seguito.

## Requisito 2 — misurato, non assunto

Sul telaio a quattro membrature: `ties == 4` (invariato dal giro 5), tolleranze di posizione per giunzione 1,18–4,22 mm (misurate, non nel range 2–5 mm dichiarato dal coordinatore per coincidenza ma con la stessa formula). Facce D/I per giunzione: 12/16, 9/2, 5/18, 21/35.

## Requisito 6 — il solutore vero, di nuovo

Misurato con `ccx` reale sullo stesso telaio: `tie constraints: 4`, **24 avvisi** `no tied MPC` (contro i 61 del giro 5) — verificato che è una regressione se tolta (mutazione applicata: `tocca` disattivato sul lato I e `POSITION TOLERANCE` non scritta → 61 avvisi, sopra il tetto di 30 → test rosso come atteso; ripristinato, `diff` vuoto). Il proxy interno di `nodi_dipendenti_legati` (55/79) coincide quasi esattamente con quanto il solutore lega davvero (79 − 24 = 55): la stessa evidenza da due strade indipendenti (proiezione geometrica in `hexa.py` e log reale di CalculiX).

## Requisito 4 — il banco a due prismi

Non cambia esito: `test_il_telaio_costruito_dichiara_le_superfici_del_tie` passa invariato (asserisce solo che le superfici non siano vuote, non conteggi esatti). Il conteggio di facce sul lato indipendente cresce (era 12, ora 30 sul banco squadrato) per via di `tocca=True`, che è l'allargamento intenzionale di Ruling AH, non una regressione.

## I test nuovi — mutazione dichiarata, applicata, verificata

| Test | Mutazione | Applicata? | Esito con la mutazione |
|---|---|---|---|
| `test_la_superficie_del_tie_con_tocca_include_una_faccia_toccata_solo_a_un_nodo` | `if tocca:` → `if False:` | Sì | `assert (0, 1) in []` fallita |
| `test_il_tie_con_tolleranza_scrive_position_tolerance` | `tolleranza_card = ""` sempre | Sì | `POSITION TOLERANCE=3.5` assente dal testo |
| `test_il_cuneo_e_calcolato_dalla_geometria_e_allarga_le_facce_a_contatto` (numeri aggiornati) | `tolleranza = max(...)` → costante | Sì (rivalidata su codice nuovo) | facce 20/26 → 10/16 |
| `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero` (feasibility) | `tocca` disattivato + `POSITION TOLERANCE` non scritta | Sì | avvisi 24 → 61, sopra il tetto di 30 |

Tutte le mutazioni ripristinate subito dopo la verifica; `diff` contro la copia pre-mutazione conferma nessuna differenza residua in ogni caso.

## Un incidente di processo, corretto

Durante la verifica della mutazione di `POSITION TOLERANCE` ho ripristinato `abaqus.py` da un backup fatto **prima** di aver implementato quella stessa funzionalità (backup creato per una mutazione precedente, su `tocca`), cancellando per errore l'implementazione appena scritta insieme alla mutazione. Accorto subito confrontando l'output della suite (un test tornato a fallire con `too many values to unpack` invece del fallimento atteso della mutazione), ho rifatto l'implementazione da capo e da quel punto ho creato un backup fresco immediatamente prima di ogni mutazione, non riutilizzato fra passaggi diversi.

## Suite

`uv run pytest tests -q --ignore=tests/feasibility` → **507 passed** (504 base di questo giro + 3 test nuovi), 2 warning preesistenti/attesi, non correlati.

`uv run pytest tests/feasibility -m feasibility -q` → **7 passed, 1 skipped** (era 6 passed/1 failed/1 skipped prima di questo giro).

## Nessun numero del provino in `src/`

Verificato con `git diff` mirato sulle righe aggiunte in `hexa.py` e `abaqus.py`: nessuno dei numeri del telaio (1600, 1400, 300, 200, ecc.) è presente.

## Rilievo su cui non ho trovato disaccordo

I tre esperimenti diagnostici del coordinatore (superfici geometricamente giuste, causa nel lato indipendente a mesh rada, guadagno da POSITION TOLERANCE) e l'esito dell'esperimento B3 (scambiare i ruoli peggiora) sono risultati coerenti con quanto osservato in proprio in questo giro. Il tetto a 30 (non i suoi numeri specifici per tolleranza fissa 3/5/10/30 mm) è una scelta mia, dichiarata come tale nel docstring del test.

## Commit

Un solo commit con `src/meshrec/core/abaqus.py`, `src/meshrec/core/hexa.py`, `tests/test_abaqus.py`, `tests/test_hexa.py`, `tests/feasibility/test_calculix.py`.
