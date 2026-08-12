# MeshRec

Pipeline riproducibile da nuvola di punti a modello FEM di muratura, sviluppata
come strumento della tesi. Sostituisce `MeshReconstructorPro`.

Spec: `../docs/superpowers/specs/2026-08-12-meshreconstructor-architettura-design.md`

## Requisiti

Python 3.12 e [uv](https://docs.astral.sh/uv/).

## Avvio

```bash
uv sync
uv run pytest                 # test del nucleo
uv run pytest -m feasibility  # verifiche sulle dipendenze esterne (Fase 0)
```

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
