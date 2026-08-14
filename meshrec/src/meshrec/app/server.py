"""Server locale: pilota il core, non lo reimplementa.

Ogni numero che serve viene da metrics.json o dalle funzioni di core; ogni
parametro che scrive passa dai modelli di config.py.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from meshrec.app.worker import Worker
from meshrec.core import pipeline, steps, sweep, viewport
from meshrec.core.config import PipelineConfig, ViewportConfig, load_config, save_config

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

# Mai dentro una cartella di corsa: runs/muro, runs/lab_crop, runs/sweep,
# experiments/muro ed experiments/lab_crop sono di sola lettura e contengono
# la tabella sperimentale della tesi. Percorso relativo come run.out_dir:
# risolto rispetto alla cartella da cui gira il server (meshrec/).
CACHE_DIR = Path(".cache/viewport")


def create_app(config_path: Path) -> FastAPI:
    """Applicazione legata a un file di configurazione, che e' la corsa corrente."""
    config_path = Path(config_path)
    app = FastAPI(title="MeshRec", docs_url=None, redoc_url=None)

    def corrente() -> PipelineConfig:
        return load_config(config_path)

    @app.exception_handler(Exception)
    async def nessuna_eccezione_verso_il_browser(_richiesta, errore: Exception):
        # Il contratto vale sulla tratta: nessun endpoint solleva verso il
        # browser. L'errore torna strutturato, con il tipo, perche'
        # l'interfaccia possa dirlo invece di mostrare una pagina bianca.
        return JSONResponse(
            status_code=400,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )

    @app.get("/")
    def interfaccia() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    @app.get("/ui/{nome:path}")
    def statico(nome: str) -> FileResponse:
        percorso = (UI_DIR / nome).resolve()
        if not percorso.is_relative_to(UI_DIR) or not percorso.is_file():
            raise FileNotFoundError(f"nessun file dell'interfaccia chiamato {nome}")
        return FileResponse(percorso)

    @app.get("/api/run")
    def stato_corsa() -> dict[str, object]:
        cfg = corrente()
        return {
            "out_dir": str(cfg.run.out_dir),
            "config_path": str(config_path),
            "steps": steps.run_state(cfg.run.out_dir, cfg),
        }

    @app.get("/api/config")
    def configurazione() -> dict[str, object]:
        return corrente().model_dump(mode="json")

    @app.put("/api/config")
    def scrivi_configurazione(nuova: PipelineConfig) -> dict[str, object]:
        # La validazione e' quella dei modelli: l'interfaccia non ne ha una
        # propria, e un valore fuori dominio non arriva mai alla pipeline.
        save_config(nuova, config_path)
        return nuova.model_dump(mode="json")

    @app.get("/api/metrics")
    def metriche() -> dict[str, object]:
        """Le metriche cosi' come stanno sul disco. L'interfaccia non ne calcola."""
        return sweep.leggi_metriche(corrente().run.out_dir)

    @app.get("/api/schema")
    def schema() -> dict[str, object]:
        """Quali parametri appartengono a quale step, con descrizione e dominio.

        Le descrizioni vengono dai modelli: sono le stesse che documentano il
        perche' di ogni predefinito misurato, e vanno mostrate accanto al
        campo invece di essere riscritte nell'interfaccia.
        """
        modelli = PipelineConfig.model_fields
        fuori: dict[str, object] = {}
        for numero, blocchi in steps.STEP_BLOCKS.items():
            campi: dict[str, object] = {}
            for blocco in blocchi:
                annidato = modelli[blocco].annotation
                campi[blocco] = {
                    nome: {
                        "description": campo.description or "",
                        # Un campo obbligatorio non ha predefinito: null, e non
                        # il sentinella di pydantic, che finirebbe a video come
                        # la stringa "PydanticUndefined" e somiglierebbe a un
                        # valore.
                        "default": (
                            None
                            if campo.is_required()
                            else campo.get_default(call_default_factory=True)
                        ),
                    }
                    for nome, campo in annidato.model_fields.items()
                }
            fuori[str(numero)] = {"blocchi": list(blocchi), "campi": campi}
        # Un predefinito puo' essere un Path, una tupla o un modello annidato:
        # non tutti sono serializzabili in JSON, e il pannello li mostra come
        # testo. default=str li rende senza inventarne il valore.
        return json.loads(json.dumps(fuori, default=str))

    lavoratore = Worker()

    # Le mappe dell'ultima decimazione servita, per step. Il ritaglio e la
    # selezione le rileggono: senza, agirebbero su indici che non esistono.
    mappe: dict[int, list] = {}

    @app.post("/api/step/{numero}")
    def esegui_step(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, numero)
        return {"avviato": numero, "fino_a": numero}

    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, 11)
        return {"avviato": numero, "fino_a": 11}

    @app.post("/api/cancel")
    def annulla() -> dict[str, object]:
        return {"annullato": lavoratore.cancel()}

    @app.get("/api/cloud/{numero}")
    def nuvola(numero: int, max_points: int | None = None) -> Response:
        """Punti decimati dello step richiesto, in binario Float32.

        Decima l'artefatto dello step chiesto e non un altro: servire al posto
        della nuvola dello step 2 quella dello step 3, che e' gia' piccola e
        pronta, mostrerebbe una nuvola diversa da quella su cui il ritaglio
        agisce.
        """
        if numero not in pipeline.ARTIFACTS:
            raise ValueError(
                f"lo step {numero} non esiste: gli step con una nuvola sono {sorted(pipeline.ARTIFACTS)}"
            )
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step {numero} non ha ancora prodotto {pipeline.ARTIFACTS[numero]}"
            )
        if max_points is not None and max_points <= 0:
            raise ValueError(f"max_points={max_points} non valido: atteso un intero positivo")
        budget = max_points if max_points is not None else ViewportConfig().max_points
        # decimate_file calcola la spaziatura al proprio interno, solo a
        # cache fredda: qui non si legge piu' la nuvola ne' si controlla la
        # cache in anticipo, perche' spacing_sample e seed sono gia' nella
        # sua chiave (vedi viewport.decimate_file).
        ridotti, gruppi, voxel = viewport.decimate_file(
            percorso, budget, cfg.input.spacing_sample, cfg.input.seed, CACHE_DIR
        )
        mappe[numero] = gruppi
        return Response(
            content=viewport.to_float32(ridotti),
            media_type="application/octet-stream",
            headers={
                "X-Points-Drawn": str(len(ridotti)),
                "X-Points-Total": str(sum(len(gruppo) for gruppo in gruppi)),
                "X-Voxel": f"{voxel:.6g}",
            },
        )

    @app.get("/api/mesh/{numero}")
    def mesh(numero: int) -> Response:
        """Vertici e facce in un solo corpo binario: prima i Float32 delle
        coordinate, poi gli Uint32 degli indici. I conteggi stanno nelle
        intestazioni, cosi' il browser sa dove tagliare.
        """
        if numero not in pipeline.ARTIFACTS:
            raise ValueError(
                f"lo step {numero} non esiste: gli step con un artefatto sono {sorted(pipeline.ARTIFACTS)}"
            )
        cfg = corrente()
        percorso = Path(cfg.run.out_dir) / pipeline.ARTIFACTS[numero]
        if not percorso.exists():
            raise FileNotFoundError(
                f"lo step {numero} non ha ancora prodotto {pipeline.ARTIFACTS[numero]}"
            )
        if percorso.suffix == ".vtu":
            import meshio

            griglia = meshio.read(percorso)
            tetraedri = griglia.cells_dict["tetra"]
            facce_tutte = np.vstack(
                [
                    tetraedri[:, list(combinazione)]
                    for combinazione in ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
                ]
            )
            # L'ordinamento serve solo a confrontare le facce e perde il verso.
            # return_index riporta la faccia originale, quindi l'orientamento
            # uscente dei quattro schemi qui sopra sopravvive al conteggio.
            _ordinate, primo, conteggi = np.unique(
                np.sort(facce_tutte, axis=1), axis=0, return_index=True, return_counts=True
            )
            # Una faccia che appartiene a un solo tetraedro sta sul contorno:
            # e' la stessa definizione che quality.boundary_edges applica agli
            # spigoli di una superficie.
            contorno = facce_tutte[primo[conteggi == 1]]
            # Solo i nodi che il contorno tocca: griglia.points porta anche
            # quelli interni, che nessun triangolo disegna, e X-Vertices
            # direbbe un numero che nessuna lettura sostiene.
            usati, rimappate = np.unique(contorno, return_inverse=True)
            vertici = griglia.points[usati]
            facce = rimappate.reshape(contorno.shape)
        else:
            import open3d as o3d

            triangolare = o3d.io.read_triangle_mesh(str(percorso))
            vertici = np.asarray(triangolare.vertices)
            facce = np.asarray(triangolare.triangles)
        if len(vertici) == 0:
            raise ValueError(f"{percorso.name} non contiene vertici")
        corpo = viewport.to_float32(vertici) + np.ascontiguousarray(facce, dtype="<u4").tobytes()
        return Response(
            content=corpo,
            media_type="application/octet-stream",
            headers={"X-Vertices": str(len(vertici)), "X-Triangles": str(len(facce))},
        )

    @app.get("/api/events")
    def eventi(max_eventi: int | None = None) -> StreamingResponse:
        """Avanzamento e log verso il browser. Una direzione sola, quindi SSE:
        WebSocket aggiungerebbe un secondo protocollo per traffico che va da
        una parte sola, e EventSource riconnette da solo."""

        def flusso():
            inviate = 0
            emesse = 0
            while True:
                cfg = corrente()
                stato = {
                    "in_corso": lavoratore.is_running(),
                    "step": lavoratore.step,
                    "exit_code": lavoratore.exit_code,
                    "annullato": lavoratore.annullato,
                    "da_secondi": lavoratore.da_secondi(),
                    "steps": steps.run_state(cfg.run.out_dir, cfg),
                }
                yield f"event: stato\ndata: {json.dumps(stato, default=str)}\n\n"
                emesse += 1
                righe = lavoratore.righe()
                for riga in righe[inviate:]:
                    yield f"event: riga\ndata: {json.dumps(riga)}\n\n"
                inviate = len(righe)
                if max_eventi is not None and emesse >= max_eventi:
                    return
                time.sleep(0.5)

        return StreamingResponse(flusso(), media_type="text/event-stream")

    return app
