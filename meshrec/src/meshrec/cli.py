"""Riga di comando minima, non definitiva: serve a lavorare nelle Fasi 1 e 2.

L'interfaccia vera arriva in Fase 3. Qui non vive alcun valore predefinito:
tutto viene dal file di configurazione.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# `solve` e' leggero (numpy, e i moduli di questo pacchetto che non aprono
# nulla): `pipeline` no -- tira dentro open3d, gmsh e pymeshlab. Sta quindi nei
# rami che lo usano e non qui, come gia' fanno `sweep` e `report`. Non e' un
# vezzo: `meshrec dottore` esiste per dire che cosa manca, e un dottore che
# muore all'import di una dipendenza rotta e' inservibile proprio quando serve.
# Misurato: con `libgomp.so.1` assente, `import pipeline` fa cadere l'intera
# riga di comando con uno stack, `dottore` compreso.
from meshrec.core import solve
from meshrec.core.config import (
    AnalysisConfig,
    InputConfig,
    Material,
    PipelineConfig,
    RunConfig,
    load_config,
    load_experiment,
    save_config,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshrec", description="Da nuvola di punti a modello FEM")
    commands = parser.add_subparsers(dest="command", required=True)

    run_command = commands.add_parser("run", help="esegue la pipeline su un file di configurazione")
    run_command.add_argument("config", type=Path)
    run_command.add_argument(
        "--from-step",
        type=int,
        default=None,
        help=(
            "riparte dagli artefatti già presenti nella cartella di elaborazione. "
            "Non verifica che siano stati prodotti con questa configurazione."
        ),
    )
    run_command.add_argument("--to-step", type=int, default=None)
    run_command.add_argument(
        "--only-step",
        type=int,
        default=None,
        help="esegue soltanto questo step, riusando gli artefatti a monte",
    )
    run_command.add_argument("--out-dir", type=Path, default=None)

    init_command = commands.add_parser("init", help="scrive una configurazione completa di esempio")
    init_command.add_argument("config", type=Path)
    init_command.add_argument("--input", type=Path, required=True, help="nuvola di partenza")
    # Il materiale non ha predefiniti: la classe e i parametri meccanici sono
    # una decisione dell'operatore e vanno dichiarati qui, non ereditati in
    # silenzio da un valore scritto nel codice. Vedi `config.Material`.
    init_command.add_argument("--materiale", required=True, help="nome del materiale")
    init_command.add_argument("--young", type=float, required=True, help="modulo elastico [MPa]")
    init_command.add_argument(
        "--poisson", type=float, required=True, help="coefficiente di Poisson"
    )
    init_command.add_argument("--densita", type=float, required=True, help="densità [t/mm^3]")

    sweep_command = commands.add_parser("sweep", help="esegue una griglia di candidati")
    sweep_command.add_argument("experiment", type=Path)

    verify_command = commands.add_parser(
        "sweep-verify", help="ricontrolla le impronte degli artefatti di un registro"
    )
    verify_command.add_argument("registry", type=Path)

    report_command = commands.add_parser("sweep-report", help="genera il report da un registro")
    report_command.add_argument("registry", type=Path)
    report_command.add_argument("--out", type=Path, required=True)

    wall_command = commands.add_parser(
        "wall", help="ricalcola il solo prior geometrico sugli artefatti già presenti"
    )
    wall_command.add_argument("config", type=Path)

    solve_command = commands.add_parser(
        "solve", help="esegue il solo solutore sugli artefatti già presenti"
    )
    solve_command.add_argument("config", type=Path)

    model_command = commands.add_parser(
        "model", help="genera un modello parametrico come corsa figlia"
    )
    model_command.add_argument("config", type=Path)
    model_command.add_argument(
        "--tipo", choices=("estruso", "primitive"), required=True,
        help="estruso conserva sezione e fuori piombo misurati; primitive li raddrizza",
    )
    model_command.add_argument(
        "--out-dir", type=Path, default=None,
        help="cartella della corsa figlia; se omessa, quella della madre col suffisso del tipo",
    )

    compare_command = commands.add_parser(
        "compare", help="confronta le cartelle dei modelli generati dello stesso pezzo"
    )
    compare_command.add_argument("cartelle", type=Path, nargs="+")
    compare_command.add_argument("--out", type=Path, required=True)

    serve_command = commands.add_parser("serve", help="avvia il server locale e apre il browser")
    serve_command.add_argument(
        "config",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "configurazione da aprire. Se omessa, l'interfaccia si apre sulla "
            "schermata d'ingresso: le corse già in runs/ e una corsa nuova da "
            "un file di punti"
        ),
    )
    serve_command.add_argument("--port", type=int, default=None)
    serve_command.add_argument("--no-browser", action="store_true")

    # #144 lascia aperto se il controllo delle dipendenze sia una tratta del
    # server, un sottocomando, o entrambi (§8.3 del sequenziamento). Qui c'e' il
    # sottocomando: argparse e' gia' in casa e non costa nulla. La tratta, se la
    # si vorra', si aggiunge dove vive il server e leggera' la stessa
    # `solve.disponibilita`: la logica non e' qui, e' li'.
    dottore_command = commands.add_parser(
        "dottore",
        help="controlla che i solutori esterni ci siano e funzionino",
        description=(
            "Guarda i due solutori esterni: se ci sono, da dove, e se "
            "rispondono davvero. Un solutore che non c'è non è un errore "
            "finché non è quello scelto"
        ),
    )
    dottore_command.add_argument(
        "config",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "configurazione da cui leggere il solutore scelto e il suo "
            "percorso. Se omessa, nessuno dei due è scelto e si guarda "
            "soltanto che cosa è installato"
        ),
    )
    return parser


# I nomi dei due solutori incolonnati: il referto si legge per colonne, e senza
# allineamento la seconda riga non si confronta con la prima.
_LARGHEZZA_NOME = 10


def _referto(nome: str, voce: dict[str, object], esito: dict[str, object] | None) -> list[str]:
    """Le righe che un solutore merita: che cosa c'è, dove, e se risponde.

    Un solutore assente ha due vesti diverse a seconda che sia quello scelto o
    no, ed è il punto del comando: chi usa solo CalculiX non deve leggere
    OpenSees come un guasto da riparare.
    """
    margine = " " * (_LARGHEZZA_NOME + 1)
    etichetta = f"{nome:<{_LARGHEZZA_NOME}}"
    if not voce["disponibile"]:
        if voce["scelto"]:
            prima = f"{etichetta} MANCA    è il solutore scelto, e non si trova"
        else:
            prima = f"{etichetta} assente  non installato, e va bene se non lo usi"
        return [prima, margine + str(voce["motivo"])]
    dove = f"{voce['percorso']} ({voce['origine']})"
    if esito is None:
        return [f"{etichetta} presente {dove}"]
    if esito["funziona"]:
        return [f"{etichetta} ok       {dove}"]
    return [f"{etichetta} ROTTO    {dove}", margine + str(esito["motivo"])]


def _dottore(percorso_config: Path | None) -> int:
    """Il referto sui solutori, e il codice d'uscita che lo riassume.

    Chi ha scelto un solutore vuole sapere se **quello** funziona: gli altri
    sono informazione, non un difetto. Chi non ne ha scelto nessuno vuole
    sapere se può risolvere qualcosa, e la risposta è no soltanto se non ne
    funziona nemmeno uno.

    Si esegue il binario del solo solutore scelto. `solve.disponibilita` non
    avvia processi di proposito, e avviarli tutti per un referto renderebbe
    lento un comando che deve rispondere subito.
    """
    solutore = None
    if percorso_config is not None:
        cfg = load_config(percorso_config)
        # Il blocco `solutore` lo dichiara l'onda 0 della Fase 8. Finché non
        # c'è, una configurazione che non lo porta vale «nessun solutore
        # scelto», che è lo stesso stato del comando senza configurazione: il
        # referto esce lo stesso invece di cadere su un attributo mancante.
        solutore = getattr(cfg, "solutore", None)

    stato = solve.disponibilita(solutore)
    esito = solve.verifica(solutore) if solutore is not None else None

    print("MeshRec — solutori esterni")
    if solutore is None:
        print("nessun solutore scelto: leggo soltanto che cosa è installato")
    for nome, voce in stato.items():
        for riga in _referto(nome, voce, esito if voce["scelto"] else None):
            print(riga)

    if esito is not None:
        if esito["funziona"]:
            return 0
        print(f"\nil solutore scelto ({esito['solutore']}) non è utilizzabile.")
        return 1
    if any(voce["disponibile"] for voce in stato.values()):
        return 0
    print("\nnessuno dei due solutori è installato: non c'è niente con cui risolvere.")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "init":
        try:
            materiale = Material(
                name=args.materiale,
                young=args.young,
                poisson=args.poisson,
                density=args.densita,
            )
            save_config(
                PipelineConfig(
                    input=InputConfig(path=args.input),
                    analysis=AnalysisConfig(material=materiale),
                ),
                args.config,
            )
        except Exception as error:  # i domini stanno in pydantic, non in argparse
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(f"configurazione scritta in {args.config}")
        return 0

    if args.command == "dottore":
        try:
            return _dottore(args.config)
        except Exception as error:  # la riga di comando riporta il problema, non lo stack
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1

    if args.command == "sweep":
        from meshrec.core import sweep

        experiment = load_experiment(args.experiment)
        try:
            result = sweep.run_experiment(experiment, load_config(experiment.base))
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False, default=float))
        print(f"registro in {result['registry']}", file=sys.stderr)
        return 0

    if args.command == "sweep-verify":
        from meshrec.core import sweep

        esito = sweep.verify_registry(args.registry)
        print(json.dumps(esito, indent=2, ensure_ascii=False))
        stantie = [voce for voce in esito if voce["stale"]]
        if stantie:
            print(f"{len(stantie)} righe stantie", file=sys.stderr)
            return 1
        return 0

    if args.command == "sweep-report":
        from meshrec.core import report

        print(f"report in {report.write_report(args.registry, args.out)}")
        return 0

    if args.command == "wall":
        from meshrec.core import io, pipeline

        try:
            cfg = load_config(args.config)
            out = Path(cfg.run.out_dir)
            sorgente = out / pipeline.ARTIFACTS[2]
            if not sorgente.exists():
                raise FileNotFoundError(
                    f"manca {sorgente}: il prior misura la nuvola segmentata, che è "
                    "l'artefatto dello step 2. Esegui almeno fino a quello "
                    f"(`meshrec run {args.config} --to-step 2`) e riprova"
                )
            punti, _ = io.read_cloud(sorgente)
            spaziatura = io.mean_spacing(punti, cfg.input.spacing_sample, cfg.input.seed)
            esito = pipeline.calcola_prior(out, cfg, punti, spaziatura)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0

    if args.command == "solve":
        # Un'azione e non una ripresa, esattamente come `wall`. Lo step 13 non
        # si ottiene con `run --from-step 13`, e il tetto di `from_step` resta
        # 9 apposta: la ripresa serve a saltare lavoro geometrico costoso gia'
        # fatto, e la coda di `pipeline.run` dallo step 9 in giu' non ha
        # guardie per step, quindi una ripresa da 13 rifarebbe volume, deck e
        # prior invece di risolvere soltanto.
        from meshrec.core import pipeline

        try:
            cfg = load_config(args.config)
            deck = Path(cfg.run.out_dir) / pipeline.DECK_FILENAME
            if not deck.exists():
                raise FileNotFoundError(
                    f"manca {deck}: il solutore risolve il deck di calcolo, che è "
                    "l'artefatto dello step 11. Esegui almeno fino a quello "
                    f"(`meshrec run {args.config} --to-step 11`) e riprova"
                )
            # Prima di rileggere il maglio, che su una corsa vera costa: un
            # binario che non c'è si dichiara adesso, con dove prenderlo, e non
            # a metà corsa. `verifica` lo esegue davvero, perché «c'è» non è
            # «funziona» -- e non decide dal codice d'uscita, che su `ccx` vale
            # 201 quando tutto va bene.
            referto = solve.verifica(cfg.solutore)
            if not referto["funziona"]:
                raise RuntimeError(
                    f"il solutore scelto ({referto['solutore']}) non è utilizzabile: "
                    f"{referto['motivo']}"
                )
            esito = pipeline.risolvi_corsa(cfg)
        except Exception as error:  # la riga di comando riporta il problema, non lo stack
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0

    if args.command == "model":
        from meshrec.core import pipeline

        try:
            cfg = load_config(args.config)
            destinazione = args.out_dir
            if destinazione is None:
                madre = Path(cfg.run.out_dir)
                destinazione = madre.with_name(f"{madre.name}-{args.tipo}")
            esito = pipeline.genera_modello(cfg, args.tipo, destinazione)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(json.dumps(esito, indent=2, default=float, ensure_ascii=False))
        return 0

    if args.command == "compare":
        from meshrec.core import report

        try:
            percorso = report.write_comparison_report(args.cartelle, args.out)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(f"confronto in {percorso}")
        return 0

    if args.command == "serve":
        import threading
        import webbrowser

        import uvicorn

        from meshrec.app.server import create_app
        from meshrec.core.config import ServerConfig

        impostazioni = ServerConfig()
        if args.port is not None:
            impostazioni.port = args.port
        indirizzo = f"http://{impostazioni.host}:{impostazioni.port}/"
        if impostazioni.open_browser and not args.no_browser:
            # Dopo un secondo: uvicorn non e' ancora in ascolto al momento della
            # chiamata, e un browser aperto su una porta chiusa mostra un errore
            # invece dell'interfaccia.
            threading.Timer(1.0, webbrowser.open, args=(indirizzo,)).start()
        print(f"MeshRec in ascolto su {indirizzo}", file=sys.stderr)
        uvicorn.run(
            create_app(args.config), host=impostazioni.host, port=impostazioni.port, log_level="warning"
        )
        return 0

    from meshrec.core import pipeline

    try:
        cfg = load_config(args.config)
        # from_step e to_step si assegnano insieme, mai uno alla volta: con
        # validate_assignment=True ogni riga rivalida l'intero modello, e
        # nessun ordine e' sicuro. La configurazione sul disco puo' portare un
        # to_step piu' piccolo di quello chiesto, e allora from_step per primo
        # rompe; oppure un from_step piu' grande, lasciato da una corsa
        # precedente, e allora to_step per primo rompe. Chiedere lo step 2 con
        # from_step=4 sul disco falliva cosi', e il pannello non lo diceva.
        # L'unico stato che deve esistere e' quello finale.
        richiesti: dict[str, int] = {}
        if args.only_step is not None:
            richiesti = {"from_step": args.only_step, "to_step": args.only_step}
        else:
            if args.from_step is not None:
                richiesti["from_step"] = args.from_step
            if args.to_step is not None:
                richiesti["to_step"] = args.to_step
        if richiesti:
            cfg.run = RunConfig.model_validate({**cfg.run.model_dump(), **richiesti})
        if args.out_dir is not None:
            cfg.run.out_dir = args.out_dir
        metrics = pipeline.run(cfg)
    except Exception as error:  # la riga di comando riporta il problema, non lo stack
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(json.dumps(metrics, indent=2, default=float, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
