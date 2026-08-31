# MeshRec

Da un rilievo fotogrammetrico di una struttura in cemento armato a un modello a
elementi finiti pronto per l'analisi, in modo riproducibile e documentabile.

Il percorso è di tredici passaggi — segmentazione della nuvola di punti,
ricostruzione della superficie, riempimento a tetraedri, esportazione del
modello, soluzione — e ogni passaggio salva i parametri con cui è stato eseguito
e le misure di qualità del proprio risultato.

## Dove guardare

- **[`meshrec/`](meshrec/)** — il programma. Requisiti, avvio, configurazioni del
  caso studio e verifiche di fattibilità: [`meshrec/README.md`](meshrec/README.md).
- **[`PRODUCT.md`](PRODUCT.md)** — a chi serve, che cosa deve fare, e i vincoli
  di prodotto che ne discendono.
- **[`docs/`](docs/)** — esiti delle fasi di sviluppo e ricerche di validazione.

## Avvio

Servono Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
cd meshrec
uv sync
uv run meshrec serve
```

Si apre nel browser l'elenco delle corse già eseguite, con la possibilità di
crearne una nuova da un file di punti (`.pcd`, `.ply`, `.xyz`). Su Windows e
macOS bastano i launcher `meshrec/MeshRec.bat` e `meshrec/MeshRec.command`.
