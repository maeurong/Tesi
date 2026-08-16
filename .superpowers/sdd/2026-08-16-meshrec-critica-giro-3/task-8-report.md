# Task 8: Il comando documentato parte, e un artefatto mancante non e' un guasto

## Cosa e' cambiato e perche'

**`meshrec/src/meshrec/app/server.py`** — aggiunto `@app.exception_handler(FileNotFoundError)`
(`artefatto_mancante`), registrato subito prima del gestore generico su `Exception`
(`nessuna_eccezione_verso_il_browser`, riga 268 originale). Risponde 404 con lo
stesso corpo `{errore, messaggio}` del gestore generico. Motivo: registrata su
`Exception`, la `FileNotFoundError` passava per `ServerErrorMiddleware` di
Starlette, che manda la risposta e poi **rilancia** l'eccezione — il browser
riceveva il 400 giusto ma il terminale un traceback per ogni clic su uno step
mai eseguito. Registrata sul tipo specifico, passa da `ExceptionMiddleware`,
che non rilancia.

**`meshrec/tests/test_server.py`** — aggiunto
`test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto` (dal brief,
verbatim). Import gia' presenti (`save_config`, `PipelineConfig`, `InputConfig`,
`TestClient`, `create_app`), nessuna aggiunta necessaria. Portati a 404 i quattro
controlli preesistenti che asserivano 400 su un artefatto mancante (tutti e soli
quelli il cui percorso di codice solleva `FileNotFoundError`, verificato leggendo
ogni sito di `raise FileNotFoundError` in server.py e incrociandolo con le
tratte testate):
- `test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva`
- `test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva`
- `test_il_clic_senza_lo_step_1_non_solleva`
- `test_un_esperimento_inesistente_risponde_quattrocento` — rinominato in
  `test_un_esperimento_inesistente_risponde_quattrocentoquattro`: il vecchio nome
  affermava "quattrocento" alla lettera, sarebbe rimasto falso se lasciato.

Tutti gli altri 400 nel file (guardia `max_points`, step fuori intervallo,
clic senza mappa, maggioranza-rumore, indice negativo, box vuoto/malformato,
`RuntimeError`/`KeyError`-turned-`ValueError` sulla mesh) restano `ValueError`
o altre eccezioni: non toccati, verificato per ognuno leggendo il ramo che li
solleva prima di decidere di lasciarlo.

**`meshrec/README.md`** — aggiunta la sezione `## Avviare l'interfaccia`
(verbatim dal brief), inserita prima di `## Unità`.

**`PRODUCT.md`** — sostituita la frase in *Operating Context* (verbatim dal
brief) e corretta l'unica altra occorrenza di `uv run meshrec serve` senza
argomento, in *Users* (riga 12), nello stesso stile.
`meshrec/docs/fase-3-registro-decisioni.md` cita `uv run meshrec serve` senza
argomento in un registro di decisioni storiche (descrive un'esecuzione
avvenuta con `prova-interfaccia.yaml` passato nella stessa frase) — non e'
documentazione che istruisce un lettore a lanciare quel comando, e il brief
non la nomina: lasciata com'e', segnalata qui.

## Red/green

**Step 3 (rosso atteso):**
```
uv run pytest tests/test_server.py -q -k "artefatto_mai_prodotto"
```
```
E       AssertionError: un artefatto mancante risponde 400
E       assert 400 == 404
E        +  where 400 = <Response [400 Bad Request]>.status_code
1 failed, 80 deselected in 1.92s
```

**Dopo l'implementazione (verde):**
```
uv run pytest tests/test_server.py -q -k "artefatto_mai_prodotto"
```
```
1 passed, 80 deselected in 2.00s
```

**Suite intera del server dopo aver aggiornato i quattro controlli
preesistenti:**
```
uv run pytest tests/test_server.py -q
```
```
81 passed in 4.99s
```

## Prove di mutazione

**Mutazione 1 — la nuova guardia (`status_code=404` → `400` in `artefatto_mancante`):**
```
uv run pytest tests/test_server.py -q -k "artefatto_mai_prodotto or quattrocentoquattro or step_1_non_solleva or artefatto_non_solleva"
```
```
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_il_clic_senza_lo_step_1_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_un_esperimento_inesistente_risponde_quattrocentoquattro - assert 400 == 404
FAILED tests/test_server.py::test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto - AssertionError: un artefatto mancante risponde 400
4 failed, 77 deselected in 2.11s
```
Ripristinato `status_code=404`, riverificato verde (4 passed).

**Mutazione 2 — meta' della guardia (direzione opposta: qualcosa che fallisce
per un'ALTRA ragione deve restare 400, non diventare 404 per errore).
Registrato il gestore su `ValueError` invece di `FileNotFoundError`
(`@app.exception_handler(ValueError)`), suite intera:**
```
uv run pytest tests/test_server.py -q
```
```
FAILED tests/test_server.py::test_max_points_zero_o_negativo_e_rifiutato_con_messaggio_chiaro - assert 404 == 400
FAILED tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_fuori_intervallo_spiega_quali_esistono - assert 404 == 400
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_fuori_intervallo_spiega_quali_esistono - assert 404 == 400
FAILED tests/test_server.py::test_un_clic_senza_mappa_caricata_non_solleva - assert 404 == 400
FAILED tests/test_server.py::test_un_clic_senza_mappa_solleva_anche_con_la_nuvola_gia_su_disco - assert 404 == 400
FAILED tests/test_server.py::test_il_clic_sul_gruppo_a_maggioranza_rumore_solleva_come_rumore - assert 404 == 400
FAILED tests/test_server.py::test_un_indice_negativo_non_avvolge_al_gruppo_di_coda - assert 404 == 400
FAILED tests/test_server.py::test_il_clic_senza_lo_step_1_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_un_volume_senza_tetraedri_dice_che_cosa_contiene - assert 404 == 400
FAILED tests/test_server.py::test_una_nuvola_chiesta_come_mesh_e_rifiutata_invece_di_tornare_vuota - assert 404 == 400
FAILED tests/test_server.py::test_un_box_vuoto_non_solleva_ma_lo_dice - assert 404 == 400
FAILED tests/test_server.py::test_un_esperimento_inesistente_risponde_quattrocentoquattro - assert 400 == 404
FAILED tests/test_server.py::test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto - AssertionError: un artefatto mancante risponde 400
15 failed, 66 passed in 5.74s
```
Un guardiano troppo largo avrebbe trasformato ogni `ValueError` in un falso
404 ("non trovato" al posto di "richiesta rifiutata") — la suite lo prende in
12 test diversi. Ripristinato `@app.exception_handler(FileNotFoundError)`,
riverificato verde: `81 passed in 4.60s`.

## Verifica del comando documentato

```
cd meshrec && uv run meshrec serve prova-interfaccia.yaml --no-browser --port 8799
```
Stdout catturato: `MeshRec in ascolto su http://127.0.0.1:8799/`

```
curl -sS -i http://127.0.0.1:8799/
```
```
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
...
<!doctype html>...<title>MeshRec</title>...
```

Verificato anche il comportamento del nuovo gestore sul server realmente in
ascolto (non solo su `TestClient`):
```
curl -sS -i http://127.0.0.1:8799/api/cloud/1
```
```
HTTP/1.1 404 Not Found
content-type: application/json

{"errore":"FileNotFoundError","messaggio":"lo step 1 non ha ancora prodotto 01_cloud.ply"}
```
Il log del processo (`/tmp/meshrec-serve-verify.log`) conteneva solo la riga
di avvio, nessun traceback dopo la richiesta 404 — coerente con la ragione
del fix. Server fermato con `pkill -f "meshrec serve prova-interfaccia"`.

Confermato anche che il vecchio comando (senza argomento, quello che il
README documentava prima) fallisce davvero:
```
uv run meshrec serve --no-browser --port 8799
```
```
usage: meshrec serve [-h] [--port PORT] [--no-browser] config
meshrec serve: error: the following arguments are required: config
```

## Suite intera

```
cd meshrec && uv run pytest -q
```
```
444 passed, 3 skipped, 6 deselected, 1 warning in 42.04s
```
443 + 1 (il nuovo test) = 444. Stesso avviso preesistente
`UnmetQualityConstraintWarning` in `test_volume.py::test_nobisect_can_make_the_volume_limit_inert_and_says_so`.
`6 deselected` e' la selezione per marker gia' presente nella configurazione
del progetto (i test `feasibility`), non introdotta da questo task.

## Segnalazioni non agite

- `meshrec/docs/fase-3-registro-decisioni.md:78` cita `uv run meshrec serve`
  senza argomento dentro un registro storico di decisioni (descrive
  un'esecuzione passata, con l'argomento nominato subito dopo nella stessa
  frase). Non l'ho toccato: non e' documentazione operativa che istruisce un
  lettore, e il brief non la elenca fra i file da modificare.

## File toccati

- `/Users/mario/GitHub/Tesi/.claude/worktrees/critica-giro-3/meshrec/src/meshrec/app/server.py`
- `/Users/mario/GitHub/Tesi/.claude/worktrees/critica-giro-3/meshrec/tests/test_server.py`
- `/Users/mario/GitHub/Tesi/.claude/worktrees/critica-giro-3/meshrec/README.md`
- `/Users/mario/GitHub/Tesi/.claude/worktrees/critica-giro-3/PRODUCT.md`

Commit: `eccfe0c` su `fix/critica-giro-3`.

## Giro di correzione 1

Due difetti nella narrativa di verifica sopra, non nel codice: il revisore ha
tracciato ogni sito `raise FileNotFoundError`, la registrazione del gestore,
la forma del corpo e `per_json` di Task 6, e li ha trovati tutti corretti.
Le righe originali sopra restano come sono scritte — sbagliate nella prova,
non nella conclusione — e questa sezione le corregge senza toccarle.

**Rilievo 1 — la mutazione 1 aveva un `-k` che escludeva un test in silenzio.**

Il filtro `artefatto_mai_prodotto or quattrocentoquattro or step_1_non_solleva
or artefatto_non_solleva` non contiene nessuna sottostringa di
`test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva` (il test manca
sia `artefatto_non_solleva` — ha `mai_eseguito_non_solleva` — sia le altre tre
parole): quel test non veniva selezionato e "4 failed" era il conteggio giusto
di quattro test sbagliati, non dei cinque dichiarati.

Riselezionato con gli `::test_name` espliciti dei cinque test rilevanti (nessun
`-k`, quindi nessuna esclusione possibile per corrispondenza di sottostringa):

```
cd meshrec && uv run pytest -q \
  "tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva" \
  "tests/test_server.py::test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva" \
  "tests/test_server.py::test_il_clic_senza_lo_step_1_non_solleva" \
  "tests/test_server.py::test_un_esperimento_inesistente_risponde_quattrocentoquattro" \
  "tests/test_server.py::test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto" \
  -v
```

Verde, prima della mutazione (linea di base — conferma che i cinque nomi sono
quelli giusti e che nessuno viene scartato):
```
collected 5 items
tests/test_server.py .....                                               [100%]
5 passed in 1.93s
```

Con la mutazione (`status_code=404` → `400` in `artefatto_mancante`,
`meshrec/src/meshrec/app/server.py`), stessa selezione:
```
FAILED tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_il_clic_senza_lo_step_1_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_un_esperimento_inesistente_risponde_quattrocentoquattro - assert 400 == 404
FAILED tests/test_server.py::test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto - AssertionError: un artefatto mancante risponde 400
5 failed in 1.92s
```
"collected 5 items" nella corsa di base e "5 failed" (senza riga "deselected")
nella corsa mutata confermano che tutti e cinque erano dentro la selezione
in entrambe le corse. Ripristinato `status_code=404` (`git diff` sul file
vuoto dopo il ripristino), riverificata la stessa selezione:
```
collected 5 items
tests/test_server.py .....                                               [100%]
5 passed in 2.12s
```

**Rilievo 2 — il "12" della mutazione 2 non veniva da nessun conteggio.**

Ririeseguita la mutazione 2 (gestore registrato su `ValueError` invece di
`FileNotFoundError`) sulla suite intera del server, log salvato e non riscritto
a mano:
```
cd meshrec && uv run pytest tests/test_server.py -q > /tmp/mutation2-rerun.log 2>&1
```
Esito (identico a quello gia' incollato sopra, riprodotto qui perche' i conteggi
sotto vengono da questo file e non da memoria):
```
FAILED tests/test_server.py::test_max_points_zero_o_negativo_e_rifiutato_con_messaggio_chiaro - assert 404 == 400
FAILED tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_mai_eseguito_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_chiedere_la_nuvola_di_uno_step_fuori_intervallo_spiega_quali_esistono - assert 404 == 400
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_senza_artefatto_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_chiedere_la_mesh_di_uno_step_fuori_intervallo_spiega_quali_esistono - assert 404 == 400
FAILED tests/test_server.py::test_un_clic_senza_mappa_caricata_non_solleva - assert 404 == 400
FAILED tests/test_server.py::test_un_clic_senza_mappa_solleva_anche_con_la_nuvola_gia_su_disco - assert 404 == 400
FAILED tests/test_server.py::test_il_clic_sul_gruppo_a_maggioranza_rumore_solleva_come_rumore - assert 404 == 400
FAILED tests/test_server.py::test_un_indice_negativo_non_avvolge_al_gruppo_di_coda - assert 404 == 400
FAILED tests/test_server.py::test_il_clic_senza_lo_step_1_non_solleva - assert 400 == 404
FAILED tests/test_server.py::test_un_volume_senza_tetraedri_dice_che_cosa_contiene - assert 404 == 400
FAILED tests/test_server.py::test_una_nuvola_chiesta_come_mesh_e_rifiutata_invece_di_tornare_vuota - assert 404 == 400
FAILED tests/test_server.py::test_un_box_vuoto_non_solleva_ma_lo_dice - assert 404 == 400
FAILED tests/test_server.py::test_un_esperimento_inesistente_risponde_quattrocentoquattro - assert 400 == 404
FAILED tests/test_server.py::test_un_artefatto_mai_prodotto_risponde_404_e_non_un_guasto - AssertionError: un artefatto mancante risponde 400
15 failed, 66 passed in 4.66s
```
Conteggio per direzione, sul file salvato:
```
grep -c "FAILED.*assert 404 == 400" /tmp/mutation2-rerun.log   → 10
grep "FAILED" /tmp/mutation2-rerun.log | grep -c "assert 400 == 404\|risponde 400"   → 5
```
`assert 404 == 400` (il test si aspettava 400, un `ValueError`, ed e' arrivato
404): **10** test — la meta' che la mutazione 2 doveva dimostrare, un gestore
troppo largo che promuove erroneamente a "non trovato" un rifiuto che non lo è.
`assert 400 == 404` (il test si aspettava 404, un `FileNotFoundError`, ed e'
arrivato 400): **5** test — la mutazione toglie anche la copertura sul tipo
vero, quindi anche i cinque test che questo giro ha appena riclassificato
tornano a fallire. 10 + 5 = 15, il totale dei falliti.

La mutazione produce fallimenti **in entrambe le direzioni**: la suite nota
sia un gestore diventato troppo ampio (i 10 `ValueError` promossi a torto) sia
un gestore che ha smesso di coprire cio' che deve coprire (i 5
`FileNotFoundError` tornati 400). E' la prova piu' forte del "12" scritto
prima, che non derivava da nessun conteggio.

Ripristinato `@app.exception_handler(FileNotFoundError)` (`git diff` sul file
vuoto dopo il ripristino), suite intera del server riverificata:
```
cd meshrec && uv run pytest tests/test_server.py -q
```
```
81 passed in 4.64s
```

## Suite intera dopo il giro di correzione

```
cd meshrec && uv run pytest -q
```
```
444 passed, 3 skipped, 6 deselected, 1 warning in 37.61s
```
Nessun cambiamento di produzione in questo giro (solo il report): il conteggio
coincide con quello di chiusura del giro precedente.
