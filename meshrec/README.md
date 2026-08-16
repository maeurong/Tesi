# MeshRec

Pipeline riproducibile da nuvola di punti a modello FEM di muratura, sviluppata
come strumento della tesi. Sostituisce `MeshReconstructorPro`.

Spec: `../docs/superpowers/specs/2026-08-12-meshreconstructor-architettura-design.md`

## Requisiti

Python 3.12 e [uv](https://docs.astral.sh/uv/).

## Avvio

```bash
uv sync
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

## Avviare l'interfaccia

```bash
uv run meshrec serve lab.yaml
```

Il percorso della configurazione e' obbligatorio: e' la corsa su cui
l'interfaccia lavora, e senza non c'e' niente da mostrare. `--port` sceglie la
porta, `--no-browser` non apre il browser.

Le configurazioni gia' pronte nel repository sono `lab.yaml` (il caso studio),
`muro.yaml` (il muro sintetico) e `prova-interfaccia.yaml` (una corsa vuota, per
guardare l'interfaccia senza calcolare niente).

## Unità

Tutto il codice lavora in **mm, N, MPa, tonnellata, secondo**. Le densità sono
in t/mm³ (1800 kg/m³ = 1.8e-9) e la gravità vale 9810 mm/s².

## Stato

Fase 0 **completata**: scheletro, primitive geometriche, scrittura del deck
Abaqus e verifiche di fattibilità delle dipendenze esterne, incluso CalculiX
come solutore per il batch di Fase 5 (installato e verificato: scarto 1,34%
dalla soluzione analitica su una colonna sotto peso proprio). Esiti completi
in `docs/fase-0-esiti.md`.
