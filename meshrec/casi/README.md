# Casi della tesi

Le configurazioni del caso studio, tenute qui e non alla radice: **non sono il
modo normale di avviare il programma**, sono i quattro casi con cui la pipeline
è stata tarata e misurata, e servono a rieseguirli.

Il modo normale è `uv run meshrec serve` senza argomenti: l'interfaccia si apre
sulla schermata d'ingresso e una corsa nasce da un file di punti.

| File | Che cos'è |
|---|---|
| `lab.yaml` | `lab_frame.pcd` ritagliato sul solo telaio (larghezza 290 mm in y). Base dello sweep `experiments/lab_crop/`. |
| `lab_telaio.yaml` | `lab_frame.pcd` col ritaglio esteso alle zapatas, misurato il 21/08/2026. È la corsa `runs/lab_telaio_v2/` della Fase 5. |
| `muro.yaml` | Il muro sintetico a geometria nota. Base dello sweep `experiments/muro/`. **Non gira così com'è su macOS**: vedi sotto. |
| `prova-interfaccia.yaml` | Banco di lavoro dell'interfaccia, non un risultato. |

## Percorsi

I percorsi dentro questi file — `input.path`, `run.out_dir` — sono relativi
alla **cartella da cui gira il programma** (`meshrec/`), non a questo file.
Vanno usati da lì:

```bash
uv run meshrec serve casi/lab_telaio.yaml
uv run meshrec sweep experiments/lab_crop/esperimento.yaml
```

`experiments/*/esperimento.yaml` li nomina con la stessa regola
(`base: casi/lab.yaml`).

## Un percorso da Windows, non ancora corretto

`muro.yaml` porta `path: ..\Nuvole di punti\muro_generato.ply`, con le barre
rovesciate: è stato scritto prima del trasloco su macOS del 16/08/2026. Su
questa macchina quel percorso **non esiste** — misurato: `exists()` è falso, e
il file vero è `../Nuvole di punti/muro_generato.ply`. Quindi
`uv run meshrec sweep experiments/muro/esperimento.yaml` oggi non parte.

Non è corretto qui di proposito: cambiare `input.path` cambia l'impronta della
base, e le impronte di questi quattro file sono state verificate identiche
prima e dopo lo spostamento in `casi/`. La correzione va fatta insieme alla
deriva già misurata fra le basi e i registri di sweep — espandendo oggi gli
esperimenti dalle basi, `experiments/lab_crop` combacia 0 righe su 11 e
`experiments/muro` 2 su 11 — non una alla volta.
