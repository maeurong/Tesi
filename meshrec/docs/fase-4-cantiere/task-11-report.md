# Task 11 — rapporto

Commit: `8577a6c757ea6ed7d00812d7936276c0065c619d`, branch `worktree-fase-4-materiale`.
File toccato: `tests/feasibility/test_calculix.py` (unico file, come da brief riscritto).

## Cosa esisteva gia' (tabella del brief, confermata leggendo il file prima di toccarlo)

`test_calculix_solves_a_column_under_self_weight` (Fase 1, tetraedri C3D4),
`test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra` (Task 5,
esaedri C3D8I + `*SURFACE`/`*DSLOAD`), `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero`
(Task 8, `*TIE`) c'erano gia'. Non riscritti da zero, solo estesi.

## Step 1 — l'elenco degli avvisi noti

Aggiunta `AVVISI_NOTI = ("reading *STEP", "reading *OUTPUT")` e
`avvisi_inattesi(stdout, extra=())` in cima al file. Assert aggiunto dopo il
`returncode == 0` esistente nei tre test originali. Nel test dei `*TIE`
l'elenco e' esteso solo localmente con `extra=("no tied MPC",)`, come
richiesto, cosi' la soglia dedicata a quell'avviso resta l'unico giudice per
quel numero.

## Step 2 — eseguito e misurato (versione di `ccx`: **2.22**)

`uv run pytest tests/feasibility -m feasibility -q` con `ccx` in PATH
(`/Users/mario/.local/bin/ccx`):

```
8 passed, 1 skipped in 4.24s
```

Lo skip e' `test_ftetwild_meshes_a_punched_box` (wildmeshing, non c'entra con
`ccx`) — invariato rispetto a prima. I 4 test di `test_calculix.py` sono
passati tutti, codice di uscita di `ccx` **0 per ciascuno**.

Avvisi per deck, misurati (`process.stdout`, filtrati su `*WARNING`):

| test | avvisi stampati | fuori da `AVVISI_NOTI`? |
|---|---|---|
| `test_calculix_solves_a_column_under_self_weight` | `reading *STEP: parameter not recognized`, `reading *STEP. Card image:`, `reading *OUTPUT:`, `reading *OUTPUT . Card image:` | no |
| `test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra` | stessi 4, identici | no |
| `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero` | stessi 4 + **24** `*WARNING in gentiedmpc: no tied MPC` | no (24 sotto il tetto dichiarato di 30, stesso ordine di grandezza del giro 6 gia' documentato nel test) |
| `test_un_prisma_solo_di_mesh_prisma_e_letto_dal_solutore` (nuovo) | stessi 4 | no |

Nessun avviso fuori dall'elenco dichiarato e' comparso. Non e' stata
necessaria alcuna fermata del brief ("se compare un avviso non elencato,
fermati e riportalo"): non ne e' comparso nessuno di nuovo.

Card lette dal solutore, confermate dagli stessi avvisi: `*STEP` (con
`NAME=`, parametro scartato) e `*OUTPUT, FIELD` sono le uniche due card
scartate in silenzio su questi quattro deck — le stesse gia' note dal brief,
nessuna terza scoperta.

## Step 3 — il prisma singolo di `mesh_prisma`

Aggiunto `test_un_prisma_solo_di_mesh_prisma_e_letto_dal_solutore`: contorno
200x140 mm, `ModelConfig(target_size=40.0)` per forzare piu' esaedri e piu'
strati del default (`strati = round(800/40) = 20` invece dei 3 minimi),
materiale a tre numeri dichiarato nel test (young=1500.0, poisson=0.2,
density=1.8e-9 — non e' il provino di laboratorio). Vincolato alla base,
peso proprio di default di `write_inp`. Asserzioni: `returncode == 0`,
nessun `*ERROR`, nessun avviso inatteso, `model.dat` esiste. Tutte verificate
passare nella corsa dello Step 2.

**Nota su `from materiale import MATERIALE`:** non importato, come da brief —
verificato che l'unico materiale nel test e' dichiarato in loco.

## Mutation testing — dichiarato e applicato davvero

**Mutazione 1** (per l'assert `avvisi_inattesi` aggiunto a tutti e quattro i
test): inserita in `abaqus.write_inp` una card fittizia `*BOGUSCARD,
PARAM=1` subito dopo `*HEADING`, rieseguita l'intera suite feasibility.

Esito: **uccisa**. Tutti e 4 i test di `test_calculix.py` sono falliti, con
`ccx` che ha stampato `*WARNING in calinput. Card image cannot be
interpreted:` — un avviso non elencato, catturato da `avvisi_inattesi` in
ciascun test. Codice di produzione ripristinato subito dopo (verificato con
`grep BOGUSCARD` senza risultati e `git diff` vuoto su `abaqus.py`).

**Mutazione 2** (per l'assert `(tmp_path / "model.dat").exists()` del test
nuovo, isolata): tolto `print_nsets=("BASE",)` (nessuna card `*NODE PRINT`
scritta), rieseguito solo il nuovo test.

Esito: **sopravvissuta**. Il test e' passato comunque: `ccx` scrive comunque
un file `model.dat` anche senza alcuna richiesta di stampa nodale (contiene
solo intestazioni, nessuno spostamento). L'asserzione di sola esistenza del
file non basta da sola a provare che il solutore abbia scritto risultati —
lo fa insieme a `returncode == 0` e all'assenza di avvisi/errori, che nel
deck reale (`print_nsets=("BASE",)`, come committato) restano gli stessi
controlli degli altri tre test. Non ho rafforzato l'assert per farla
tornare rossa: la mutazione resta un limite noto della sola riga `.exists()`
presa in isolamento, non del test completo. Ripristinato `print_nsets=("BASE",)`
subito dopo, confermato via `git diff` prima del commit.

## Esiti finali misurati in questa sessione

- `ccx -v`: **Version 2.22**
- `uv run pytest tests/feasibility -m feasibility -q`: **8 passed, 1 skipped**
  (era 7 passati, 1 saltato prima di questo task — la differenza e' il nuovo
  test del prisma singolo)
- `uv run pytest -q` (suite principale, non comprende feasibility): **519
  passed, 9 deselected, 2 warnings** (i due warning sono preesistenti,
  `MembratureNonLegateWarning` e `UnmetQualityConstraintWarning`, non
  toccati da questo task)

## Gap fuori scope

- La mesh conforme multiblocco per i `*TIE` (zero avvisi per costruzione)
  resta la via d'aggiornamento non imboccata, come gia' documentato nel test
  esistente — non era nello scope di questo task.
- La debolezza dell'asserzione `.exists()` isolata (Mutazione 2) e' segnalata
  qui, non corretta: il brief chiedeva esattamente quelle quattro
  asserzioni, non di piu'.

Skill invocata: `tdd-guide` (generazione/estensione di test pytest e
ragionamento sulla qualita' della suite di feasibility).
