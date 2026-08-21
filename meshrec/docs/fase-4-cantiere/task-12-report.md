# Task 12 -- report

Stato: **DONE**

Commit:
- `6c37241` -- `feat(fase-4): confronto fra i tre modelli, insiemi parziali compresi`
- `7aa4895` -- `fix(fase-4): giro di correzione 1 -- segno positivo, escape, riga mancante, duplicati`

(worktree `fase-4-materiale`, branch `worktree-fase-4-materiale`)

## Giro di correzione 1 -- quattro rilievi del revisore, tutti riprodotti e corretti

Per ognuno: test TDD (RED), fix (GREEN), poi la mutazione dichiarata applicata davvero sul
sorgente, verificata che uccidesse il test giusto, ripristinata con `git checkout -- 
src/meshrec/core/report.py` (mai `git stash`, come richiesto).

1. **Il piu' serio -- cartella vuota classificata come as-built, in silenzio.**
   `confronta` distingueva l'as-built dal parametrico solo per assenza di `modello.json`, un
   segnale negativo che una cartella vuota (o una corsa parametrica fallita a meta') soddisfa
   allo stesso modo della corsa madre vera. Aggiunto il segno positivo: la corsa madre deve avere
   `12_wall.json` (`pipeline.WALL_FILENAME`) leggibile, altrimenti `confronta` solleva
   `ValueError` invece di produrre un modello fantasma con tutte le celle "non impostato".
   Aggravante chiusa insieme: `report.py` ora legge davvero `12_wall.json` (tramite `_legge_json`,
   non solo `.exists()`), quindi il docstring di `_tre_cartelle_finte` ("legge metrics.json,
   12_wall.json e modello.json") e' tornato vero invece di essere corretto per dire il falso.
   Test: `test_una_cartella_senza_modello_json_ne_12_wall_json_non_diventa_un_as_built_fantasma`.
   Mutazione: tolta la guardia (`chiave = "as-built"` incondizionato) -- uccisa,
   `Failed: DID NOT RAISE ValueError`.
   Verificato anche da riga di comando reale: `meshrec compare <cartella-vuota> --out x.html`
   esce con `ValueError: ... non e' una corsa valida: ne' modello.json ne' 12_wall.json si
   leggono ...` ed exit code 1.

2. **Escaping HTML incoerente.** Le celle (`volume`/`massa`/`scostamento_nuvola`/
   `gradi_di_liberta`), `qualita_righe`, `vincoli_righe` e ogni nota in
   `note_non_geometriche` -- compresa `nota_giunzioni`, testo libero letto da `modello.json` --
   entravano nell'HTML senza `html.escape`, mentre il resto del modulo lo applica sempre
   (`_tabella`, `report.py:323`). Avvolte tutte con `html.escape`.
   Test: `test_la_nota_delle_giunzioni_letta_da_un_json_esterno_si_scrive_con_l_escape_html`.
   Mutazione: tolto `html.escape` dalla riga delle note -- uccisa,
   `assert '<b>critico</b>' not in testo` falliva (il tag non era escapato).
   Verificato reale: iniettato `<script>alert(1)</script>` in un `nota_giunzioni` su disco e
   generato il report da CLI -- nel file compare solo `&lt;script&gt;alert(1)&lt;/script&gt;`,
   zero occorrenze di `<script>alert` crudo.

3. **`gradi_di_liberta` dichiarato confrontabile, mai mostrato.** Era il rilievo che avevo gia'
   segnalato io stessa come non bloccante nel giro precedente; il revisore lo ha confermato e
   chiesto di farlo accordare. Scelta: mostrarlo (l'informazione era gia' calcolata e utile,
   toglierla dalla dichiarazione avrebbe tolto un confronto legittimo). Aggiunta la riga al loop
   di rendering (`("volume", "massa", "scostamento_nuvola", "gradi_di_liberta")`).
   Test: `test_i_gradi_di_liberta_dichiarati_confrontabili_compaiono_nella_tabella`.
   Mutazione: tolta la quarta voce dal tuple -- uccisa,
   `assert '<th>gradi_di_liberta</th>' in testo` falliva.
   Verificato reale: la riga compare nell'HTML generato da CLI con nodi ed element_type per
   tutti e tre i modelli.

4. **Cartelle duplicate si sovrascrivevano in silenzio.** `presenti[chiave] = {...}` non
   controllava se `chiave` era gia' presente: due cartelle con lo stesso tipo (o due prive di
   `modello.json` ma con `12_wall.json` valido) facevano sparire la prima senza un fiato. Una
   guardia sola copre entrambi i rami (as-built e parametrico), scritta nel punto dove entrambi
   convergono -- non due guardie separate.
   Test: `test_due_cartelle_dello_stesso_tipo_si_segnalano_invece_di_sovrascriversi`.
   Mutazione: tolta la guardia sulla chiave duplicata -- uccisa,
   `Failed: DID NOT RAISE ValueError`.
   Verificato reale da CLI: due cartelle "estruso" -> `ValueError: due cartelle dichiarano lo
   stesso modello 'estruso': ...` ed exit code 1.

Suite dopo il giro di correzione: **533 passati** (529 del giro precedente + 4 nuovi), piu' **8
passati / 1 skipped** in `tests/feasibility -m feasibility` (invariato). Numeri letti da me, non
attesi a priori.

## File toccati

- `src/meshrec/core/report.py` -- `MODELLI`, `CONFRONTABILI`, `NOTE_STATICHE`, `_legge_json`,
  `_testo_vincoli`, `confronta`, `write_comparison_report`.
- `src/meshrec/cli.py` -- comando `compare`.
- `tests/materiale.py` -- `_tre_cartelle_finte` (D5: qui, non in `tests/test_report.py`, perche'
  `tests/` non e' un pacchetto).
- `tests/test_report.py` -- i 5 test del corpo (con D1/D3/D4 applicate) + 9 test nuovi (4 del
  primo giro, 4 del giro di correzione, 1 import `pytest`).
- `tests/test_cli.py` -- il test del comando `compare`.

## Le correzioni D1-D6 -- verificate nel codice, poi applicate

Ogni affermazione del blocco di correzioni e' stata riletta nei file citati prima di scrivere
codice, non presa per buona:

- **D1** (bloccante) -- confermato: `_numero` (`report.py:277`, gia' esistente) chiama
  `math.isnan(valore)` per primo e solleva `TypeError` su `None`. Sostituito `_numero` con
  `_testo` nel loop di `write_comparison_report`, come da brief.
- **D2** (chiuso a monte) -- confermato: `pipeline.genera_modello` (righe 202, 211-216) scrive
  gia' `scostamento_nuvola` con `rms`/`max`/`nota`. `confronta` non chiama
  `quality.vertex_deviation`, legge solo il campo.
- **D3** (serio) -- confermato: `quality.volume_metrics` (`quality.py:353-362`) non ha la chiave
  `min_ratio`, ha `radius_edge_ratio`. Rinominata la colonna dei tetraedri ovunque (codice,
  docstring di `CONFRONTABILI`, entrambi i test).
- **D4** (minore) -- applicato: l'asserzione spostata dentro il ciclo su `qualita.values()`,
  cercando `{"differenza", "delta", "scarto"}` fra le chiavi di ogni colonna; le quattro
  asserzioni su `CONFRONTABILI` restano, con la docstring che dichiara "sorveglia la costante,
  non un calcolo".
- **D5** (minore) -- preso subito il ripiego: `_tre_cartelle_finte` vive in `tests/materiale.py`,
  importata per nome da entrambi i file di test.
- **D6** (nuovo) -- confermato in `hexa.py:963-973`: `giunzioni`, `ties`,
  `nodi_dipendenti_legati`, `nodi_dipendenti_totali` sono quattro chiavi distinte dentro
  `modello["modello"]`. Aggiunta `confronta()["vincoli_giunzioni"]`: dizionario per modello,
  `"non applicabile"` per l'as-built (mai zero, mai "non generato"), le due coppie di numeri mai
  sommate ne' messe in rapporto. `nota_giunzioni` letta da `modello.json` (Task 10), non
  riscritta: sostituisce la voce statica che il corpo del brief avrebbe duplicato.

## Un settimo difetto, non coperto da D1-D6, trovato e corretto

Il corpo del brief legge lo scostamento dalla nuvola dell'as-built cosi':

```python
.get("07_surface_quality", {}).get("geometric_error", {}).get("cloud_to_mesh", {}).get("rms")
```

Verificato falso su due punti, con prova:

1. **Verso sbagliato.** I modelli parametrici misurano `scostamento_nuvola` con
   `quality.vertex_deviation` (`pipeline.py:202`). La docstring di quella funzione
   (`quality.py:458-464`) dice esplicitamente: *"riproduce esattamente il verso mesh_to_cloud
   [...] la misura che questa funzione non replica e' cloud_to_mesh"*. Leggere `cloud_to_mesh`
   per l'as-built e il verso opposto per i parametrici mette in colonna, sotto lo stesso nome,
   due misure diverse -- l'esatto errore che questo task esiste per evitare.
2. **Chiave sbagliata.** `geometric_error` restituisce le chiavi grezze di PyMeshLab, e la
   chiave e' `RMS` maiuscola, non `rms` (`quality.py:428`, confermato in `tests/test_quality.py:107`
   e altri quattro punti dello stesso file). Con la chiave minuscola il valore sarebbe sempre
   stato `None` in produzione, mentre la fixture del brief (che usava `"rms"` minuscolo) avrebbe
   fatto passare il test lo stesso -- proprio il tipo di asserzione-specchio contro cui il
   compito mette in guardia.

Corretto in `confronta()`: legge `geometric_error.mesh_to_cloud.RMS`. La fixture di
`tests/materiale.py` tiene `cloud_to_mesh` e `mesh_to_cloud` a valori diversi (4.9 e 3.1) apposta,
cosi' un ritorno all'errore non passa inosservato.

## Test

Suite completa (`uv run pytest tests -q --ignore=tests/feasibility`): letta io stessa,
**529 passati** (baseline 519 + 10 nuovi). `tests/feasibility -m feasibility`: **8 passati, 1
skipped** (invariato, fuori scope).

Dieci test nuovi:

**I 5 del corpo del brief** (con D1/D3/D4 gia' incorporate nelle asserzioni):
`test_il_confronto_di_tre_modelli_dice_quali_grandezze_lo_sono`,
`test_la_qualita_degli_elementi_sta_in_due_colonne_e_mai_in_una_differenza`,
`test_con_due_modelli_su_tre_il_confronto_dice_quale_manca`,
`test_con_un_modello_solo_il_confronto_diventa_una_scheda_e_lo_dichiara`,
`test_il_report_dichiara_le_tre_cose_che_non_derivano_dalla_geometria`,
`test_il_comando_compare_scrive_la_pagina_e_nomina_i_modelli_assenti` (in `test_cli.py`).

**4 di mia iniziativa**, per D1 (che il corpo non esercitava mai davvero) e per il settimo
difetto e D6 (che il brief non copriva con asserzioni):
`test_un_modello_json_piu_vecchio_senza_scostamento_nuvola_non_fa_crashare_il_report`,
`test_lo_scostamento_dell_as_built_legge_mesh_to_cloud_non_cloud_to_mesh`,
`test_i_vincoli_alle_giunzioni_sono_quattro_numeri_distinti_e_non_applicabili_per_l_as_built`,
`test_la_nota_delle_giunzioni_viene_letta_da_modello_json_non_riscritta`.

### Mutazioni applicate davvero, non solo dichiarate

Per ognuno dei 5 test nuovi/critici, la mutazione dichiarata nella docstring e' stata scritta
nel codice sorgente, eseguita, verificata che uccidesse il test, poi ripristinata:

| Test | Mutazione | Esito osservato |
|---|---|---|
| `test_un_modello_json_piu_vecchio...` | `_testo` -> `_numero` nel loop celle | `TypeError: must be real number, not NoneType` -- come previsto |
| `test_la_qualita_degli_elementi...` | chiave esaedri `scaled_jacobian` -> `differenza` | fallita, ma sull'asserzione `"scaled_jacobian" in qualita["estruso"]`, non su quella prevista in origine -- **docstring corretta di conseguenza** |
| `test_lo_scostamento_dell_as_built...` | tornato a `cloud_to_mesh`/`rms` | `assert None == 3.1` -- come previsto |
| `test_i_vincoli_alle_giunzioni...` | sommati `giunzioni`+`ties` in una chiave | `KeyError: 'giunzioni'`, ma sulla seconda asserzione, non sulla terza/quarta previste -- **docstring corretta** |
| `test_la_nota_delle_giunzioni...` | `nota_giunzioni` sostituita con stringa scritta in `report.py` | fallita sul confronto testuale, come previsto |

Due delle cinque docstring sono state corrette dopo la verifica, perche' la mutazione moriva su
un'asserzione diversa da quella prevista: riportato qui invece di lasciare la docstring a
raccontare una prova che non e' quella osservata.

## Verifica reale (non solo pytest)

`meshrec compare` eseguito davvero da riga di comando, fuori da pytest, su cartelle scritte da
`_tre_cartelle_finte` su disco:

- con 2 modelli su 3 (`as-built` + `estruso`): pagina scritta, `primitive` nominato e "non
  generato" in ogni colonna che gli appartiene, `scostamento_nuvola` a `3.1` per l'as-built (il
  verso corretto) e `6.2` per l'estruso, tabella qualita' con `radius_edge_ratio` e
  `scaled_jacobian` in righe separate, mai una `differenza`, tabella vincoli con
  `giunzioni 3, ties 2, nodi vincolati 18/24` per l'estruso e `non applicabile` per l'as-built,
  nota giunzioni dinamica in testa alla lista.
- con 1 modello solo: banner "scheda singola" presente.

## Preoccupazioni

Nessuna aperta. L'unica segnalata nel giro precedente (`gradi_di_liberta` dichiarato
confrontabile ma non mostrato) e' stata chiusa in questo giro di correzione: la riga ora compare
in tabella (vedi rilievo 3 sopra).
