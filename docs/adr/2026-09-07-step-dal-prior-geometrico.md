# ADR 2026-09-07 — STEP dal prior geometrico: prismi fusi in `occ`, accanto alla mesh esaedrica

Stato: proposto. Decisione di prodotto presa con Mario: `meshrec model` scrive
anche un file STEP della geometria; SAT è fuori (ACIS proprietario); `.vtu`
resta. Qui: fuse o N solidi, dove scrivere, come verificare. Repo `meshrec/`,
`main` a `cb6ef7e`.

## Contesto

`meshrec model --tipo estruso|primitive` (`cli.py:81-92`) costruisce un
prisma per membratura del prior (`hexa.prisma_di`, `hexa.py:276`: contorno
K×2 nel piano della sezione, `origine`, `asse`, `lunghezza`), li accorcia
alle giunzioni (`taglia_giunzioni`, `hexa.py:539`) e ne fa la mesh esaedrica
uno per uno con il kernel `gmsh.model.geo` (`mesh_prisma`, `hexa.py:188-200`),
legata da `*TIE`. `hexa.py:570-576` scarta la fusione booleana perché
frammenta i volumi e rischia di perdere gli esaedri: per la sola geometria
non conta.

Fatti misurati oggi (da `meshrec/`, `uv run python`, gmsh 4.15.2, scratchpad
`spike_step.py`):

- `gmsh.write("x.step")` scrive **AP214 CD** (`FILE_SCHEMA
  AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }`), unità mm per default; gmsh
  non espone l'AP da API (`Geometry.OCCSTEPSchemaIdentifier` cambia solo
  l'etichetta nell'header — researcher, da `GModelIO_OCC.cpp` e doc OCCT
  `write.step.schema`).
- `occ.fuse` di due box che si toccano su una faccia → **un** solido di
  volume 4 200 000 = somma esatta; un terzo box disgiunto resta un volume a
  sé: `fuse` rende 2 volumi, nessuna eccezione. Rilettura con
  `occ.importShapes` + `occ.getMass(3, tag)`: 2 volumi, masse identiche.
- Nel file finiscono solo entità `occ` di livello massimo, dopo
  `occ.synchronize()`; le entità `geo` non vengono scritte (researcher,
  `exportShapes`).
- Abaqus/CAE (doc 2017, unica primaria raggiungibile; 2023-25 in 403):
  legge AP203 e — per la pratica — AP214; «Part Filter» del dialogo STEP
  offre *combine into a single part* più *stitch*; solidi disgiunti combinati
  = una Part con regioni disconnesse. L'`.inp` entra come **orphan mesh
  part** separata: nessun legame automatico con la Part geometrica.

## Decisione

1. **Fusione in `occ` dei prismi *non tagliati*** (`prisma_di` per ogni
   membratura, prima di `taglia_giunzioni`): la booleana fa esattamente ciò
   che il taglio approssima — toglie la doppia contabilità dove i prismi si
   compenetrano — e non ha il soffitto del taglio (attraversamento e
   contenimento sollevano in `taglia_giunzioni`, `hexa.py:566-571`; in
   `fuse` sono casi normali). Prismi che non si toccano restano solidi
   distinti nello stesso file: la metrica riporta `solidi`, nessuna
   eccezione, e in CAE «combine into single part» li tiene insieme.
2. **Un file per corsa figlia**: `runs/<madre>-<tipo>/modello.step`, accanto
   a `modello.json` e a `wall_model.inp` (`pipeline.py:37, 198`). Il nome
   della costante segue `MODEL_FILENAME`: `MODEL_STEP_FILENAME =
   "modello.step"`.
3. **Costruzione diretta in coordinate globali**: punti `origine + u·e1 +
   v·e2` (`_base_del_piano`, `hexa.py:128`), `occ.addLine`/`addCurveLoop`/
   `addPlaneSurface`, `occ.extrude([(2, s)], *(asse · lunghezza))`. Niente
   `affineTransform`: il prisma nasce dove sta.
4. **Verifica come metrica, non come asserzione**: `esito["step"] = {"file",
   "solidi", "volume": Σ getMass, "volume_analitico": Σ area·lunghezza dei
   prismi *tagliati* (già in `mesh_prisma`, chiave `volume_analitico`),
   "scarto_relativo"}`. Nel telaio di laboratorio i due coincidono fino al
   cuneo del fuori piombo (`_cuneo_vertice`, `hexa.py:496`): il numero si
   mostra con il suo contraddittorio, come vuole PRODUCT.md, senza fingere
   un'uguaglianza che il taglio non promette. L'uguaglianza esatta (rel
   1e-9) è oracolo del **test** su prismi ortogonali sintetici.
5. **Rilettura nel test, non in produzione**: il test scrive, rilegge con
   `occ.importShapes`, conta i volumi e confronta `getMass` con l'analitico.
   In produzione basterebbe a raddoppiare il tempo per un numero già noto.

## Approcci confrontati

**A. Fuse in un solido (scelta).** Un pezzo, come il provino. Il tutor
partiziona in CAE se vuole le membrature. Costo: i prismi si fondono dove il
rilievo dice che si toccano — un gioco sotto la risoluzione dello scanner
li lascia separati, ed è ciò che `MembratureNonLegateWarning`
(`hexa.py:735`) già dichiara per la mesh; la metrica `solidi > 1` è lo
stesso segnale sul STEP.

**B. N solidi separati, nessuna booleana.** Più semplice di dieci righe, e
CAE li combina. Scartato: volumi compenetranti dove le membrature si
incontrano (doppia contabilità che `taglia_giunzioni` esiste per togliere),
e un tutor che deve fondere lui in CAE — con «stitch» che lavora sulle facce
libere, non sui solidi chiusi (researcher: inferenza, doc non copre).

**C. Fuse dei prismi già tagliati.** Stessa uscita di A sul telaio; si porta
dietro il soffitto del taglio (attraversamento/contenimento sollevano) senza
ragione, perché la booleana non ne ha bisogno. Scartato.

**AP242 o AP203 invece di AP214.** gmsh non lo espone; AP214 entra in CAE
(pratica diffusa, doc primaria cita AP203 e non nega gli altri). Non si
tocca; se il tutor lo rifiuta, la via è `Geometry.OCCSTEPSchemaIdentifier`
per l'etichetta — che è però una bugia sull'header — o un convertitore
esterno. Da verificare all'import reale (domanda aperta).

## Conseguenze

- `hexa.scrivi_step(prismi: list[Prisma], path: Path) -> dict` (~50 righe):
  `gmsh.initialize`/`finalize` come `mesh_prisma`; zero prismi →
  `ValueError` prima di `initialize`, nessun file; con un prisma solo nessun
  `fuse` (`fuse` vuole oggetto e strumento non vuoti); `synchronize` prima
  di `write`. Rende `{"solidi", "volume"}`.
- `pipeline.genera_modello` chiama `scrivi_step` dopo `costruisci` (che ha
  già rifiutato membrature vuote o assenti) e prima di `modello.json`, e
  registra `esito["step"]`. Se `scrivi_step` fallisce la corsa figlia ha già
  il deck: si solleva, non si scrive un `modello.json` che dice «step» senza
  file.
- `report.confronta` (`report.py:1200`) non legge il STEP: non è
  confrontabile con l'as-built, che un STEP non ce l'ha. Nessuna riga nuova.
- Un test di fattibilità non serve: gmsh è già dipendenza vera
  (`pyproject.toml:22`) e il test di unità scrive e rilegge il file.
