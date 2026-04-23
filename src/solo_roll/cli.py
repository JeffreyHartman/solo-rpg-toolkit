import argparse
import json
import os
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .charts import FateChartError, fate_check, load_fate_chart
from .quicksets import QuicksetDataError, QuicksetNotFoundError, run_quickset
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


def _cmd_meaning_pair(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    tables_arg = args.tables
    parts = [t.strip() for t in tables_arg.split(",") if t.strip()]
    if len(parts) != 2:
        print(f"error: --tables expects two comma-separated names, got {tables_arg!r}", file=sys.stderr)
        return 1
    action_name, desc_name = parts
    dice = _dice(args)
    try:
        action = roll_table(action_name, data_dir, dice)
        description = roll_table(desc_name, data_dir, dice)
    except TableNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except TableDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = {
        "action":      {"table": action["table"],      "roll": action["roll"],      "result": action["result"]},
        "description": {"table": description["table"], "roll": description["roll"], "result": description["result"]},
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_quickset(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        payload = run_quickset(args.id, data_dir, _dice(args))
    except QuicksetNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except QuicksetDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_roll(args: argparse.Namespace) -> int:
    dice_str = args.dice.lower()
    if not dice_str.startswith("d"):
        print(f"error: invalid dice '{args.dice}' — expected format dN (e.g. d10, d6)", file=sys.stderr)
        return 1
    try:
        sides = int(dice_str[1:])
    except ValueError:
        print(f"error: invalid dice '{args.dice}' — expected format dN (e.g. d10, d6)", file=sys.stderr)
        return 1
    if sides < 2:
        print(f"error: dice must have at least 2 sides, got {sides}", file=sys.stderr)
        return 1
    result = _dice(args).roll(1, sides)
    print(json.dumps({"dice": dice_str, "roll": result}, indent=2))
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

    p_pair = subparsers.add_parser("meaning-pair", help="Roll Mythic Meaning Tables (action + descriptor)")
    p_pair.add_argument("--tables", default="action1,descriptor1",
                        help="Comma-separated pair of table names (default action1,descriptor1)")
    _add_common_args(p_pair)
    p_pair.set_defaults(func=_cmd_meaning_pair)

    p_qs = subparsers.add_parser("quickset", help="Run a quickset chain")
    p_qs.add_argument("id", help="Quickset id, e.g. npc_profile")
    _add_common_args(p_qs)
    p_qs.set_defaults(func=_cmd_quickset)

    p_roll = subparsers.add_parser("roll", help="Roll a die (e.g. d10, d6, d100)")
    p_roll.add_argument("dice", help="Dice notation, e.g. d10")
    _add_common_args(p_roll)
    p_roll.set_defaults(func=_cmd_roll)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
