import argparse
import json
import os
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .charts import FateChartError, fate_check, load_fate_chart
from .rng import DiceSource, RandomDice
from .tables import TableDataError, TableNotFoundError, roll_table


def _resolve_data_dir(cli_arg: str | None) -> Path:
    if cli_arg:
        return Path(cli_arg)
    env = os.environ.get("SOLO_ROLL_DATA")
    if env:
        return Path(env)
    user_override = Path.home() / ".config" / "solo-roll" / "data"
    if user_override.exists():
        return user_override
    return DEFAULT_DATA_DIR


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--data", type=str, default=None)


def _dice(args: argparse.Namespace) -> DiceSource:
    return RandomDice(seed=args.seed)


def _cmd_table(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        payload = roll_table(args.name, data_dir, _dice(args))
    except TableNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except TableDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_fate_check(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        chart = load_fate_chart(data_dir)
        payload = fate_check(args.likelihood, args.cf, chart, _dice(args))
    except FateChartError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-roll")
    parser.add_argument("--version", action="version", version=f"solo-roll {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False

    p_table = subparsers.add_parser("table", help="Roll a single table by name")
    p_table.add_argument("name", help="Table name, e.g. action1 or elements/plottwist")
    _add_common_args(p_table)
    p_table.set_defaults(func=_cmd_table)

    p_fate = subparsers.add_parser("fate-check", help="Mythic fate check")
    p_fate.add_argument("--likelihood", required=True)
    p_fate.add_argument("--cf", type=int, required=True)
    _add_common_args(p_fate)
    p_fate.set_defaults(func=_cmd_fate_check)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
