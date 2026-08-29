"""Sequenza degli step. E' l'unico modulo che conosce l'ordine.

Ogni step scrive il proprio artefatto numerato: la ripresa con `from_step`
ricarica l'artefatto precedente invece di rifare il lavoro.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from meshrec.core import abaqus, io, quality, repair, segment, solve, steps, surface, volume, wall
from meshrec.core.config import PipelineConfig, save_config

METRICS_FILENAME = "metrics.json"
METRICS_PARTIAL = "metrics.partial.json"
WALL_FILENAME = "12_wall.json"
# Il deck di calcolo dello step 11: il file che si importa in Abaqus o si da' a
# CalculiX, e che lo step 13 risolve senza copiarlo. Una costante perche' da
# adesso lo nomina anche il server, che lo consegna a chi lo chiede
# (`/api/deck`): scritto due volte, il giorno che cambia ne cambia una sola.
DECK_FILENAME = "wall_model.inp"


class _FermataRichiesta(Exception):
    """Uscita normale quando to_step e' raggiunto: non e' un errore.

    Serve perche' le guardie degli step hanno rami else di ripresa, che
    ricaricano artefatti a monte: spegnerle con una condizione su to_step
    farebbe scattare proprio quei rami sugli step che non si devono toccare.
    Interrompere il flusso e' l'unico modo che non tocca le guardie.
    """

ARTIFACTS: dict[int, str] = {
    1: "01_cloud.ply",
    2: "02_segmented.ply",
    3: "03_downsampled.ply",
    4: "04_normals.ply",
    5: "05_surface.ply",
    6: "06_repaired.ply",
    8: "08_simplified.ply",
    9: "09_volume.vtu",
    13: "13_solution.vtu",
}

# Tabelle esplicite da from_step all'artefatto da ricaricare, verificate a mano
# per ogni from_step da 2 a 9 (non solo il caso 1). Sostituiscono un calcolo
# con ARTIFACTS[min(from_step - 1, N)] che era sbagliato in due punti:
# - per from_step=8 chiedeva ARTIFACTS[7], che non esiste (KeyError);
# - per from_step=4..7 la nuvola di riferimento per l'errore geometrico dello
#   step 7 finiva per essere quella ridotta o normale, non quella segmentata.
# Una tabella e' piu facile da controllare a colpo d'occhio di un'espressione.

# Nuvola da ricaricare come ingresso dello step che riparte (usata anche solo
# per stimare la spaziatura quando lo step stesso legge il proprio artefatto).
_RESUME_POINTS: dict[int, int] = {2: 1, 3: 2, 4: 3, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4}

# Mesh (vertici/facce) da ricaricare come ingresso dello step che riparte.
# Lo step 7 non scrive un proprio artefatto (produce solo metriche), quindi
# from_step=8 riparte anch'esso dalla superficie riparata dello step 6.
# from_step=9 non e' qui: l'artefatto giusto dipende da cfg.simplify.enabled
# (vedi run()), perche' lo step 8 scrive 08_simplified.ply solo se abilitato.
_RESUME_MESH: dict[int, int] = {6: 5, 7: 6, 8: 6}


def _write_mesh(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(faces, dtype=np.int32)),
    )
    io.scrivi_atomico(path, lambda destinazione: o3d.io.write_triangle_mesh(str(destinazione), mesh))


def _read_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    import open3d as o3d

    mesh = o3d.io.read_triangle_mesh(str(path))
    vertices = np.ascontiguousarray(np.asarray(mesh.vertices), dtype=np.float64)
    faces = np.ascontiguousarray(np.asarray(mesh.triangles), dtype=np.int64)
    # open3d NON solleva su file assente: scrive un avviso su stderr e torna una
    # mesh vuota (misurato il 24/08/2026: "Read PLY failed: unable to open
    # file", zero vertici, nessuna eccezione). Senza questa guardia uno step
    # ripreso a monte inesistente girava su zero vertici, scriveva un artefatto
    # vuoto e lo registrava "riuscito": un successo falso, che e' peggio di un
    # errore perche' nessuno lo va a cercare. Simmetrica a io.read_cloud, che
    # la guardia ce l'ha gia'.
    #
    # Anche zero facce e non solo zero vertici: un .ply di soli punti si apre
    # senza errore e passerebbe la prima meta' del controllo, per poi far
    # girare la riparazione su una superficie che facce non ne ha.
    if len(vertices) == 0 or len(faces) == 0:
        # Non «file assente»: i due soli chiamanti passano da
        # `_ingresso_di_ripresa`, che il file inesistente lo intercetta prima
        # con un messaggio suo. Qui il file c'e' sempre, e dirlo assente
        # contraddirebbe la frase che lo avvolge.
        raise ValueError(
            f"nessuna superficie letta da '{path}': vuota o di formato non riconosciuto"
        )
    return vertices, faces


def _ingresso_di_ripresa(
    chiede: int, da: int, out: Path, leggi: Callable[[Path], tuple[np.ndarray, np.ndarray]]
) -> tuple[np.ndarray, np.ndarray]:
    """Ricarica l'artefatto dello step `da` come ingresso dello step `chiede`.

    Esiste per il messaggio, non per la lettura: `read_cloud` e `_read_mesh`
    nominano il FILE che manca, e chi guarda l'interfaccia ragiona per STEP.
    "nessun punto letto da '04_normals.ply'" non dice a nessuno che deve
    eseguire lo step 4 prima del 5.

    La sequenza resta consigliata e non imposta: qui si rifiuta e si dice cosa
    manca, mentre i bottoni dell'interfaccia restano cliccabili sempre.

    File assente e file illeggibile sono due messaggi diversi apposta. Dire
    "lo step 4 non ha ancora scritto" davanti a un artefatto che esiste ma e'
    troncato manderebbe a rieseguire uno step che e' gia' stato eseguito,
    senza spiegare perche' la prima volta non e' bastata.
    """
    percorso = out / ARTIFACTS[da]
    if not percorso.exists():
        raise ValueError(
            f"lo step {chiede} pretende {ARTIFACTS[da]}, che lo step {da} non ha ancora "
            f"scritto. Esegui prima lo step {da}, oppure «Esegui da qui in giù» "
            f"dallo step {da}"
        )
    try:
        return leggi(percorso)
    except (ValueError, OSError) as errore:
        raise ValueError(
            f"lo step {chiede} pretende {ARTIFACTS[da]}, che esiste ma non si legge "
            f"({errore}). Riesegui lo step {da}"
        ) from errore


def calcola_prior(
    out: Path, cfg: PipelineConfig, points: np.ndarray, spacing: float
) -> dict[str, object]:
    """Step 12: il prior geometrico, calcolato e scritto accanto agli altri artefatti.

    Sta in una funzione propria e non dentro `run()` perche' ha due chiamanti:
    la corsa intera e il comando `meshrec wall`, che ricalcola il solo prior
    sugli artefatti gia' presenti. Una seconda copia del calcolo sarebbe una
    seconda cosa da tenere allineata.
    """
    esito = wall.prior(points, cfg.segment, cfg.wall, spacing)
    io.scrivi_atomico(
        out / WALL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito


MODEL_FILENAME = "modello.json"


def _ricostruisci_membrature(prior: dict[str, object]) -> list:
    """Le `Membratura` del prior, per costruire un modello parametrico.

    Dodici dei quindici campi sono presi 1:1 dal dizionario per membratura che
    `wall.prior` scrive. Gli altri tre stanno annidati sotto
    `voce["riempimento"]`, il dizionario che `wall.riempimento` scrive: e' da
    li' che viene `riempimento_stato`, il campo su cui poggia la guardia del
    Ruling J in `hexa.costruisci`, che rifiuta di costruire un modello da una
    sezione dichiarata «vuota». Estratta come funzione propria perche' e'
    l'unico punto di questa mappatura, ed e' testabile da sola.
    """
    from meshrec.core.wall import Membratura

    return [
        Membratura(
            punti=np.arange(0),
            asse=np.asarray(voce["asse"], dtype=np.float64),
            origine=np.asarray(voce["origine"], dtype=np.float64),
            lunghezza=float(voce["lunghezza"]),
            sezione=tuple(voce["sezione"]),
            sezione_dispersione=tuple(voce["sezione_dispersione"]),
            contorno=np.asarray(voce["contorno"], dtype=np.float64),
            fuori_piombo_deg=float(voce["fuori_piombo_deg"]),
            asse_ideale=np.asarray(voce["asse_ideale"], dtype=np.float64),
            scarto_asse_deg=float(voce["scarto_asse_deg"]),
            rigonfiamento=np.zeros(0),
            volume=float(voce["volume"]),
            riempimento_sezione=float(voce["riempimento"]["valore"]),
            riempimento_stato=str(voce["riempimento"]["stato"]),
            densita_dispersione=float(voce["riempimento"]["densita_dispersione"]),
        )
        for voce in prior["membrature"]
    ]


def genera_modello(cfg: PipelineConfig, tipo: str, out_dir: Path) -> dict[str, object]:
    """Genera un modello parametrico come corsa figlia, nella propria cartella.

    I due modelli parametrici sono **generatori di mesh di volume alternativi a
    TetGen**: producono nodi ed elementi e rientrano negli step esistenti di
    metriche di volume ed esportazione. Non sono rami di `run()`, e la ragione
    e' che biforcarla raddoppierebbe la complessita' della funzione piu'
    delicata del progetto senza risparmiare nulla.

    La cartella figlia porta la stessa `config.yaml` della madre -- e' lo
    stesso esperimento, e la stessa impronta -- piu' un `modello.json` che dice
    di quale tipo e' e da quale corsa viene. La provenienza sta li' e non nella
    configurazione, perche' la scelta del modello e' un'azione e non un
    parametro di elaborazione.
    """
    from meshrec.core import hexa

    sorgente = Path(cfg.run.out_dir)
    percorso_prior = sorgente / WALL_FILENAME
    if not percorso_prior.exists():
        raise FileNotFoundError(
            f"manca {percorso_prior}: un modello parametrico si costruisce sul "
            "prior, e il prior è lo step 12. Esegui `meshrec wall` sulla stessa "
            "configurazione e riprova"
        )
    with percorso_prior.open(encoding="utf-8") as handle:
        prior = json.load(handle)

    membrature = _ricostruisci_membrature(prior)

    # Letta qui e non al punto d'uso, per la stessa ragione per cui il
    # save_config sta dopo `costruisci`: e' una lettura pura, e lasciata a valle
    # di `out.mkdir` faceva nascere la cartella figlia con dentro il solo
    # config.yaml ogni volta che il materiale non era dichiarato -- esattamente
    # lo stato che il commento qui sotto esiste per impedire.
    analisi = cfg.analisi_dichiarata(f"il modello parametrico «{tipo}»")

    out = Path(out_dir)

    # save_config solo dopo costruisci: se la generazione fallisce (sulla
    # nuvola vera fallisce, perche' il prior non accetta membrature), la
    # cartella figlia non deve nascere con dentro il solo config.yaml --
    # /api/compare la troverebbe (e' una directory) e la rifiuterebbe senza
    # ne' modello ne' corsa madre da leggere (vedi report.confronta).
    modello = hexa.costruisci(membrature, tipo, cfg.model)
    nodi = modello["nodi"]
    elementi = modello["elementi"]

    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")

    carico = None
    if cfg.model.lateral_nset is not None and cfg.model.lateral_pressure is not None:
        carico = (cfg.model.lateral_nset, float(cfg.model.lateral_pressure))

    export = abaqus.export_model(
        out / DECK_FILENAME,
        out / "wall_model.vtu",
        nodi,
        elementi,
        analisi,
        cfg.tet,
        reference=nodi,
        element_type=cfg.model.element,
        element_surfaces=modello["superfici"],
        ties=modello["ties"],
        pressure=carico,
    )

    # Lo scostamento dalla nuvola sorgente e' il perno del confronto (Task 12):
    # e' definito allo stesso modo per i tre modelli. Si misura qui, dove la
    # nuvola segmentata della madre e i nodi del modello sono entrambi a
    # portata; il confronto non ricalcola nulla.
    sorgente_nuvola, _ = io.read_cloud(sorgente / ARTIFACTS[2])
    scarti = quality.vertex_deviation(nodi, sorgente_nuvola)

    esito: dict[str, object] = {
        "tipo": tipo,
        "sorgente": str(sorgente),
        "modello": modello["metriche"],
        "blocchi": modello["blocchi"],
        "hexa": quality.hexa_metrics(nodi, elementi),
        "export": export,
        "scostamento_nuvola": {
            "rms": float(np.sqrt(np.mean(scarti ** 2))),
            "max": float(scarti.max()),
            "nota": "distanza punto-nuvola nei soli nodi: sottostima dove gli "
                    "elementi sono grandi, come dichiara quality.vertex_deviation",
        },
        "nota_giunzioni": (
            "*TIE fra superfici a contatto: le mesh di membrature adiacenti "
            "non combaciano nodo a nodo. E' una differenza fra i modelli che "
            "non deriva dalla geometria -- as-built monolitico, parametrici "
            "vincolati alle giunzioni -- e va letta accanto al confronto"
        ),
        "nota_armatura": (
            "modello a calcestruzzo omogeneo: l'armatura è fuori ambito per "
            "decisione dell'autore, non per dimenticanza, e il dato resta nel "
            "disegno. Un telaio in cemento armato modellato senza armatura non "
            "è il telaio vero"
        ),
    }
    io.scrivi_atomico(
        out / MODEL_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(esito, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    return esito


def run(cfg: PipelineConfig) -> dict[str, object]:
    """Esegue la pipeline e restituisce le metriche di ogni step.

    Dalla Fase 4 gli step di elaborazione sono dodici. Il dodicesimo e' il
    prior geometrico e chiude la corsa madre; non e' un punto di ripresa e non
    e' un ramo: i due modelli parametrici sono corse figlie con la propria
    cartella, non biforcazioni di questa funzione.

    Dalla Fase 5 c'e' un tredicesimo step, il solutore: legge il deck che lo
    step 11 ha scritto e vi applica `ccx`. E' parte del nucleo che questa
    funzione esegue per difetto -- `RunConfig.to_step` e' predefinito a 13 --
    per una decisione dell'utente presa all'apertura della fase: ogni corsa
    risolve e scrive spostamenti e tensioni accanto alle altre metriche, non
    e' un'azione a parte da richiedere. Resta pero' l'unico step che paga un
    processo esterno vero anziche' lavoro in-process: chi elabora molti
    candidati (lo sweep) non deve pagarlo per ciascuno, e per questo
    `sweep.run_candidate` chiede esplicitamente `--to-step 12` al
    sottoprocesso invece di ereditare questo predefinito (vedi `sweep.py`,
    che per la stessa ragione non lo richiede in `REQUIRED_STEPS`).

    `cfg.run.from_step` salta gli step precedenti e ricarica dal disco
    l'artefatto numerato che precede quello di ripartenza, secondo le tabelle
    `_RESUME_POINTS` e `_RESUME_MESH`. La ripresa si fida dell'operatore su un
    punto solo: non verifica che quegli artefatti siano stati prodotti con la
    configurazione corrente. Che esistano invece lo verifica, e se mancano
    solleva `ValueError` nominando lo step da eseguire prima
    (`_ingresso_di_ripresa`). Unica eccezione governata da `cfg`
    invece che dalla tabella: `from_step=9` ricarica `08_simplified.ply` se
    `cfg.simplify.enabled` e' vero, altrimenti `06_repaired.ply`, perche' lo
    step 8 scrive il proprio artefatto solo quando la semplificazione e'
    abilitata (predefinito: disabilitata). Se l'operatore riparte da 9 con
    `simplify.enabled=True` ma la corsa precedente non aveva scritto
    `08_simplified.ply` (per esempio perche' era disabilitata in quella
    corsa), la ripresa solleva `ValueError` invece di indovinare.

    La ripresa arriva fino allo step 9 (tetraedrizzazione): `RunConfig.from_step`
    e' vincolato a 9 (vedi `config.py`). Gli step 10 e 11 sono il calcolo delle
    metriche di volume e l'esportazione del deck, senza lavoro costoso da
    saltare, quindi vengono sempre rieseguiti, qualunque sia `from_step`.
    """
    out = Path(cfg.run.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out / "config.yaml")
    io.scarta_temporanei(out)
    impronte = steps.step_fingerprints(cfg)
    metrics: dict[str, object] = {}
    start = cfg.run.from_step
    stop = cfg.run.to_step
    # Lo step su cui il lavoro e' fermo in questo istante: serve al ramo di
    # fallimento, che deve dire quale step si e' rotto e non che la corsa
    # e' finita male in un punto imprecisato.
    in_corso = start
    # Vero solo se il flusso ha attraversato per intero il nucleo di
    # elaborazione geometrica che questa versione di run() esegue (oggi
    # 12_wall): si aggiorna da solo spostandosi con la riga che lo mette a
    # True, senza un numero da tenere sincronizzato a mano con cfg.run.to_step
    # altrove. Lo step 13 (solutore) e' un'azione in piu' che non ridefinisce
    # questa completezza: una corsa fermata a 12 (sweep, to_step=12 esplicito)
    # e una arrivata a 13 (predefinito) sono ugualmente complete per questo
    # flag -- la differenza fra le due e' se ha anche una soluzione.
    pipeline_completa = False

    def registra(numero: int, avvio: float, artefatto: str | None) -> None:
        steps.write_state(
            out, numero, impronte[numero], "riuscito", artefatto, time.monotonic() - avvio
        )

    try:
        if start <= 1:
            in_corso = 1
            avvio = time.monotonic()
            points, step_metrics = io.load_cloud(cfg.input)
            metrics["01_load"] = step_metrics
            io.write_cloud(out / ARTIFACTS[1], points)
            registra(1, avvio, ARTIFACTS[1])
            if stop <= 1:
                raise _FermataRichiesta
        else:
            points, _ = _ingresso_di_ripresa(start, _RESUME_POINTS[start], out, io.read_cloud)

        spacing = float(
            metrics.get("01_load", {}).get("spacing")
            or io.mean_spacing(points, cfg.input.spacing_sample, cfg.input.seed)
        )

        if start <= 2:
            in_corso = 2
            avvio = time.monotonic()
            points, step_metrics = segment.segment_cloud(points, cfg.segment, spacing)
            metrics["02_segment"] = step_metrics
            io.write_cloud(out / ARTIFACTS[2], points)
            source_cloud = points
            registra(2, avvio, ARTIFACTS[2])
            if stop <= 2:
                raise _FermataRichiesta
        elif start <= 7 or stop >= 12:
            # La nuvola segmentata (uscita dello step 2) ha DUE consumatori e
            # nessun altro: l'errore geometrico dello step 7 e il prior dello
            # step 12. La condizione li nomina entrambi invece di caricarla
            # sempre, e non e' una micro-ottimizzazione: caricarla quando non
            # gira nessuno dei due faceva FALLIRE una corsa che non ne aveva
            # bisogno. «Esegui solo lo step 9» in una cartella senza
            # 02_segmented.ply si fermava per un artefatto che quello step non
            # tocca -- ed e' proprio il caso che from_step == to_step esiste per
            # servire (config.py, RunConfig).
            #
            # `chiede` e' lo step che la consuma, non quello da cui la corsa
            # riparte. Nominare `start` produceva un consiglio che distrugge il
            # lavoro: «lo step 9 pretende 02_segmented.ply, esegui da qui in
            # giu' dallo step 2» riscrive gli artefatti dal 2 al 9, cioe'
            # proprio quelli su cui si stava iterando.
            source_cloud, _ = _ingresso_di_ripresa(
                7 if start <= 7 else 12, 2, out, io.read_cloud
            )

        if start <= 3:
            in_corso = 3
            avvio = time.monotonic()
            points, step_metrics = surface.downsample(points, cfg.downsample, spacing)
            metrics["03_downsample"] = step_metrics
            io.write_cloud(out / ARTIFACTS[3], points)
            registra(3, avvio, ARTIFACTS[3])
            if stop <= 3:
                raise _FermataRichiesta

        if start <= 4:
            in_corso = 4
            avvio = time.monotonic()
            normals, step_metrics = surface.estimate_normals(points, cfg.normals, spacing)
            metrics["04_normals"] = step_metrics
            io.write_cloud(out / ARTIFACTS[4], points, normals)
            registra(4, avvio, ARTIFACTS[4])
            if stop <= 4:
                raise _FermataRichiesta
        else:
            points, normals = _ingresso_di_ripresa(start, 4, out, io.read_cloud)

        if start <= 5:
            in_corso = 5
            avvio = time.monotonic()
            vertices, faces, step_metrics = surface.reconstruct(points, normals, cfg.surface)
            metrics["05_reconstruct"] = step_metrics
            _write_mesh(out / ARTIFACTS[5], vertices, faces)
            registra(5, avvio, ARTIFACTS[5])
            if stop <= 5:
                raise _FermataRichiesta
        elif start == 9:
            # lo step 8 scrive 08_simplified.ply solo se la semplificazione e'
            # abilitata: con from_step=9 la mesh valida a monte e' quella
            # dello step 8 se abilitata, altrimenti quella riparata dello
            # step 6 (predefinito), mai un ripiego generico sull'ultimo file
            # esistente.
            resume_from = 8 if cfg.simplify.enabled else 6
            vertices, faces = _ingresso_di_ripresa(start, resume_from, out, _read_mesh)
        else:
            vertices, faces = _ingresso_di_ripresa(start, _RESUME_MESH[start], out, _read_mesh)

        if start <= 6:
            in_corso = 6
            avvio = time.monotonic()
            vertices, faces, step_metrics = repair.repair_surface(vertices, faces, cfg.repair)
            metrics["06_repair"] = step_metrics
            _write_mesh(out / ARTIFACTS[6], vertices, faces)
            registra(6, avvio, ARTIFACTS[6])
            if stop <= 6:
                raise _FermataRichiesta

        if start <= 7:
            in_corso = 7
            avvio = time.monotonic()
            step_metrics = quality.surface_metrics(vertices, faces)
            step_metrics["geometric_error"] = quality.geometric_error(vertices, faces, source_cloud)
            metrics["07_surface_quality"] = step_metrics
            registra(7, avvio, None)
            if stop <= 7:
                raise _FermataRichiesta

        if start <= 8:
            in_corso = 8
            avvio = time.monotonic()
            vertices, faces, step_metrics = surface.simplify(vertices, faces, cfg.simplify)
            metrics["08_simplify"] = step_metrics
            if cfg.simplify.enabled:
                _write_mesh(out / ARTIFACTS[8], vertices, faces)
            registra(8, avvio, ARTIFACTS[8] if cfg.simplify.enabled else None)
            if stop <= 8:
                raise _FermataRichiesta

        in_corso = 9
        avvio = time.monotonic()
        nodes, tets, step_metrics = volume.tetrahedralize_with_metrics(vertices, faces, cfg.tet)
        metrics["09_tetrahedralize"] = step_metrics
        # Il tipo va dichiarato: `write_vtu` non lo indovina dal numero di
        # colonne, e il suo predefinito e' il lineare. Senza, un maglio
        # quadratico finirebbe scritto come `tetra` e meshio rifiuterebbe la
        # forma -- che e' il modo buono di sbagliare, ma solo perche' meshio
        # controlla.
        abaqus.write_vtu(out / ARTIFACTS[9], nodes, tets, element_type=cfg.tet.element)
        registra(9, avvio, ARTIFACTS[9])
        if stop <= 9:
            raise _FermataRichiesta

        in_corso = 10
        avvio = time.monotonic()
        metrics["10_volume_quality"] = quality.volume_metrics(nodes, tets, cfg.tet.reference_ratio)
        registra(10, avvio, None)
        if stop <= 10:
            raise _FermataRichiesta

        in_corso = 11
        avvio = time.monotonic()
        # `vertices` e' la superficie da cui la mesh di volume e' stata
        # generata: e' quella, e non i nodi del volume, a definire il sistema
        # di riferimento del modello (vedi abaqus.align_to_axes).
        metrics["11_export"] = abaqus.export_model(
            out / DECK_FILENAME,
            out / "wall_model.vtu",
            nodes,
            tets,
            cfg.analisi_dichiarata("lo step 11"),
            cfg.tet,
            reference=vertices,
            carichi=cfg.carichi,
            selettori=cfg.selettori,
        )
        registra(11, avvio, DECK_FILENAME)

        if stop <= 11:
            raise _FermataRichiesta

        in_corso = 12
        avvio = time.monotonic()
        # Il prior misura la nuvola segmentata e non la superficie ricostruita:
        # il rilievo e' il dato, e la ricostruzione di Poisson e' gia' una
        # interpretazione del rilievo. `source_cloud` e' esattamente l'uscita
        # dello step 2, che la ripresa ricarica quando riparte da piu' in la'.
        metrics["12_wall"] = calcola_prior(out, cfg, source_cloud, spacing)
        registra(12, avvio, WALL_FILENAME)
        pipeline_completa = True
        if stop <= 12:
            raise _FermataRichiesta

        in_corso = 13
        avvio = time.monotonic()
        # Il solutore legge il deck dello step 11, non una sua copia: se il
        # deck e' quello che l'analisi risolve, allora e' quello che il report
        # descrive e quello di cui il registro porta l'impronta. Le etichette
        # dei casi (casi_di_carico) vengono dalla stessa riga: e' l'ordine che
        # export_model ha scritto davvero nel deck, non una sua ricostruzione.
        metrics["13_solve"] = solve.risolvi(
            out, out / DECK_FILENAME, cfg.analisi_dichiarata("lo step 13"), nodes, tets,
            metrics["11_export"]["element_type"],
            casi_di_carico=metrics["11_export"]["casi_di_carico"],
            # Gia' calcolato allo step 11 (abaqus.constraint_plan_extent):
            # risolvi non ha i node_sets per ricalcolarlo, una sola origine.
            vincolo_in_pianta=metrics["11_export"]["constraint_plan_extent"],
            # `nodes` qui non e' allineato agli assi (export_model allinea
            # internamente e non restituisce i nodi allineati), mentre i campi
            # che risolvi legge dal .frd vengono dal deck allineato: la 4x4
            # dello step 11 e' cio' che permette di scriverli nello stesso
            # telaio dei punti del .vtu.
            trasformata=metrics["11_export"]["transform"],
        )
        registra(13, avvio, ARTIFACTS[13] if metrics["13_solve"]["eseguito"] else None)
    except _FermataRichiesta:
        # Fermata su richiesta: gli step chiesti sono stati eseguiti e il
        # risultato e' valido quanto quello di una corsa intera, per gli step
        # che comprende.
        pass
    except BaseException:
        # Registra il fallimento dello step su cui il lavoro era fermo, poi
        # rilancia intatto: la pipeline non ingoia mai un errore, si limita a
        # lasciarne traccia. BaseException e non Exception perche' anche
        # un'interruzione da tastiera lascia lo stato coerente.
        steps.write_state(out, in_corso, impronte[in_corso], "fallito", None, 0.0)
        raise
    finally:
        # Il parziale, non metrics.json: una corsa interrotta lascia intatto
        # l'ultimo risultato completo invece di sostituirlo con il proprio
        # frammento. Era il difetto per cui la Fase 2 ha dovuto costruire
        # is_complete per distinguerli.
        with (out / METRICS_PARTIAL).open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2, default=float, ensure_ascii=False)

    # Solo qui, cioe' solo se nessuna eccezione non gestita e' uscita dal try:
    # la corsa e' arrivata dove doveva arrivare.
    completa = start == 1 and pipeline_completa
    if completa:
        # Una corsa intera e' autoritativa: sostituisce, non fonde. E' il
        # percorso che lo sweep esegue, e la Fase 2 dipende dal fatto che una
        # cartella di candidato non erediti nulla.
        (out / METRICS_PARTIAL).replace(out / METRICS_FILENAME)
        return metrics

    precedenti: dict[str, object] = {}
    if (out / METRICS_FILENAME).exists():
        try:
            with (out / METRICS_FILENAME).open(encoding="utf-8") as handle:
                letto = json.load(handle)
            precedenti = letto if isinstance(letto, dict) else {}
        except (OSError, ValueError):
            # Un metrics.json illeggibile non fa fallire una corsa riuscita:
            # si riparte da quello che questa corsa ha misurato.
            #
            # ValueError e non json.JSONDecodeError, che ne e' una sottoclasse e
            # lascia scoperto UnicodeDecodeError -- sollevato dalla lettura del
            # file, prima del parse, su un byte non UTF-8. Qui la guardia esiste
            # proprio perche' una corsa RIUSCITA non deve fallire sulla
            # rilettura di cio' che c'era prima, e scritta stretta faceva
            # esattamente quello che era li' a impedire.
            precedenti = {}
    unite = dict(sorted({**precedenti, **metrics}.items()))
    io.scrivi_atomico(
        out / METRICS_FILENAME,
        lambda destinazione: destinazione.write_text(
            json.dumps(unite, indent=2, default=float, ensure_ascii=False), encoding="utf-8"
        ),
    )
    (out / METRICS_PARTIAL).unlink(missing_ok=True)
    return unite
