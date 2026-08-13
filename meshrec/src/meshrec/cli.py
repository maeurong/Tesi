"""Riga di comando minima, non definitiva: serve a lavorare nelle Fasi 1 e 2.

L'interfaccia vera arriva in Fase 3. Qui non vive alcun valore predefinito:
tutto viene dal file di configurazione.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meshrec.core import pipeline
from meshrec.core.config import InputConfig, PipelineConfig, load_config, load_experiment, save_config


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
            "riparte dagli artefatti gia presenti nella cartella di elaborazione. "
            "Non verifica che siano stati prodotti con questa configurazione."
        ),
    )
    run_command.add_argument("--out-dir", type=Path, default=None)

    init_command = commands.add_parser("init", help="scrive una configurazione completa di esempio")
    init_command.add_argument("config", type=Path)
    init_command.add_argument("--input", type=Path, required=True, help="nuvola di partenza")

    sweep_command = commands.add_parser("sweep", help="esegue una griglia di candidati")
    sweep_command.add_argument("experiment", type=Path)

    verify_command = commands.add_parser(
        "sweep-verify", help="ricontrolla le impronte degli artefatti di un registro"
    )
    verify_command.add_argument("registry", type=Path)

    report_command = commands.add_parser("sweep-report", help="genera il report da un registro")
    report_command.add_argument("registry", type=Path)
    report_command.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "init":
        save_config(PipelineConfig(input=InputConfig(path=args.input)), args.config)
        print(f"configurazione scritta in {args.config}")
        return 0

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

    cfg = load_config(args.config)
    try:
        if args.from_step is not None:
            cfg.run.from_step = args.from_step
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
