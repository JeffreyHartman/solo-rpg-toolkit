import argparse
import json
import os
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .charts import FateChartError, fate_check, load_fate_chart
from .quicksets import QuicksetDataError, QuicksetNotFoundError, run_quickset
from .rng import DiceSource, RandomDice
from .tables import TableDataError, TableNotFoundError, load_table, roll_table


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


def _cmd_list(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    if not data_dir.exists():
        print(f"error: data dir not found: {data_dir}", file=sys.stderr)
        return 1
    tables_root = data_dir / "tables"
    entries: list[dict] = []
    if tables_root.exists():
        prefix = args.prefix.rstrip("/") if args.prefix else None
        for path in sorted(tables_root.rglob("*.json")):
            rel_name = path.relative_to(tables_root).with_suffix("").as_posix()
            if prefix is not None and rel_name != prefix and not rel_name.startswith(prefix + "/"):
                continue
            try:
                table = load_table(rel_name, data_dir)
            except (TableNotFoundError, TableDataError) as exc:
                print(f"warning: skipped {path}: {exc}", file=sys.stderr)
                continue
            if "entries" in table:
                count = len(table["entries"])
            else:
                count = sum(b["max"] - b["min"] + 1 for b in table["ranges"])
            entries.append({
                "name": rel_name,
                "display_name": table.get("display_name", table["name"]),
                "dice": table["dice"],
                "description": table.get("description"),
                "entry_count": count,
            })
    if args.json:
        print(json.dumps({"tables": entries}, indent=2))
        return 0
    _render_list_text(entries)
    return 0


def _render_list_text(entries: list[dict]) -> None:
    if not entries:
        return
    groups: dict[str, list[dict]] = {}
    for e in entries:
        group = e["name"].rsplit("/", 1)[0] if "/" in e["name"] else "(top-level)"
        groups.setdefault(group, []).append(e)
    ordered: list[str] = []
    if "(top-level)" in groups:
        ordered.append("(top-level)")
    ordered.extend(sorted(g for g in groups if g != "(top-level)"))
    for group in ordered:
        header = group if group == "(top-level)" else f"{group}/"
        print(header)
        members = groups[group]
        name_w = max(len(e["name"].rsplit("/", 1)[-1]) for e in members)
        display_w = max(len(e["display_name"]) for e in members)
        for e in members:
            short = e["name"].rsplit("/", 1)[-1]
            desc = e["description"] if e["description"] else "—"
            print(f"  {short:<{name_w}}  {e['dice']:<4}  {e['entry_count']:>3} entries  {e['display_name']:<{display_w}}  — {desc}")
        print()


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

    p_list = subparsers.add_parser("list", help="List available tables grouped by directory")
    p_list.add_argument("prefix", nargs="?", default=None,
                        help="Optional prefix to filter (e.g. 'elements' or 'mythic')")
    p_list.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of grouped text")
    p_list.add_argument("--data", type=str, default=None)
    p_list.set_defaults(func=_cmd_list)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
