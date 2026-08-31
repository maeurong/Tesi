# MeshRec

Pipeline riproducibile da nuvola di punti a modello FEM di strutture in cemento
armato, sviluppata come strumento della tesi. Sostituisce `MeshReconstructorPro`.

Spec: `../docs/superpowers/specs/2026-08-12-meshreconstructor-architettura-design.md`

## Requisiti

Python 3.12 e [uv](https://docs.astral.sh/uv/).

## Avvio

Doppio clic su `MeshRec.command` (macOS) o `MeshRec.bat` (Windows), dentro
questa cartella. Oppure da riga di comando:

```bash
uv sync
uv run meshrec serve                   # apre il browser sulla schermata d'ingresso
```

I due launcher non chiedono nulla e non nominano nessun file: si spostano nella
propria cartella — i percorsi relativi del programma (`runs/`, `experiments/`,
`.cache/viewport`) sono risolti da lì — e avviano `meshrec serve` senza
argomenti. Un percorso passato a mano continua a valere:
`./MeshRec.command casi/lab_telaio.yaml` apre quel caso direttamente.

Senza argomenti l'interfaccia si apre su una schermata che elenca le corse già
presenti in `runs/` e permette di crearne una nuova da un file di punti
(`.pcd`, `.ply`, `.xyz`), indicandone il percorso su questa macchina. Non serve
scrivere a mano un `config.yaml`: nasce da lì, con ogni parametro al proprio
predefinito.

Il **materiale** non viene chiesto all'inizio e non viene indovinato: nome,
modulo elastico, coefficiente di Poisson e densità si dichiarano allo step 11,
che è il primo a pretenderli. Fino a lì la corsa attraversa tutta la geometria
senza. Gli step 11 e 13 si fermano con un messaggio finché non ci sono.

Le configurazioni del caso studio della tesi stanno in `casi/` e si aprono per
nome — `uv run meshrec serve casi/lab_telaio.yaml`. Vedi `casi/README.md`.

### Proteggere una corsa di riferimento

Una cartella di corsa che contiene un file vuoto chiamato `SOLA_LETTURA` si apre
e si guarda, ma le tratte che scrivono — eseguire uno step, ricalcolare il prior,
generare un modello, riscrivere la configurazione, ritagliare, scegliere un
cluster — si fermano dicendo perché. Serve a non riscrivere con un clic un
risultato che finisce in tesi.

**Va messo a mano dopo il clone: `runs/` è in `.gitignore`, quindi la sentinella
non viaggia col repository.**

```bash
touch runs/muro/SOLA_LETTURA runs/lab_crop/SOLA_LETTURA
```

```bash
uv run pytest                          # test del nucleo

uv sync --all-extras                   # installa anche gmsh (gruppo opzionale "feasibility")
uv run pytest -m feasibility           # verifiche sulle dipendenze esterne (Fase 0)
```

`uv sync` da solo **non installa** gli extra: `gmsh` sta nel gruppo opzionale
`feasibility` di `pyproject.toml`, quindi il suo test viene saltato senza
`--all-extras`.

### Salti attesi nelle prove di fattibilità

Su questa macchina, cinque verifiche, un salto è atteso e quattro no:

- `wildmeshing` **salta sempre**, per progetto: nessuna wheel disponibile per
  Windows, si è deciso il ripiego TetGen + PyMeshFix (vedi `docs/fase-0-esiti.md`).
- `pymeshfix`, `pymeshlab`, `gmsh`, CalculiX **devono passare**. Se uno di
  questi salta, la verifica **non** è stata eseguita e l'esito registrato in
  `docs/fase-0-esiti.md` non vale per questa run.
- CalculiX richiede l'eseguibile `ccx` nel `PATH` (su questa macchina:
  `C:\Users\mario\tools\PrePoMax v2.5.0\Solver`, già nel PATH utente).

### Verifica CalculiX

Il test di CalculiX (`tests/feasibility/test_calculix.py`) richiede
l'eseguibile `ccx` raggiungibile nel `PATH` di sistema; se assente, il test
viene saltato in modo pulito (`SKIPPED`), non fallisce. Per eseguirlo:

```bash
uv run pytest tests/feasibility/test_calculix.py -v -m feasibility
```

## Unità

Tutto il codice lavora in **mm, N, MPa, tonnellata, secondo**. Le densità sono
in t/mm³ (1800 kg/m³ = 1.8e-9) e la gravità vale 9810 mm/s².

## Stato

Fase 0 **completata**: scheletro, primitive geometriche, scrittura del deck
Abaqus e verifiche di fattibilità delle dipendenze esterne, incluso CalculiX
come solutore per il batch di Fase 5 (installato e verificato: scarto 1,34%
dalla soluzione analitica su una colonna sotto peso proprio). Esiti completi
in `docs/fase-0-esiti.md`.
