import argparse
import json
import os
import re
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .character import roll_character
from .charts import FateChartError, fate_check, load_fate_chart
from .checks import CheckError, morale_check, surprise_check
from .dice import DiceError, parse_dice, roll_dice
from .dungeon import DungeonError, advance_turn, load_state, new_state, save_state
from .quicksets import QuicksetDataError, QuicksetNotFoundError, run_quickset
from .reveal import RevealError, hide, load_revealed, reveal
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
        payload = roll_table(args.name, data_dir, _dice(args), modifier=args.mod)
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
    try:
        spec = parse_dice(args.dice)
    except DiceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    payload = roll_dice(spec, _dice(args))
    payload["dice"] = re.sub(r"\s+", "", args.dice.lower())  # echo the caller's notation
    payload["roll"] = payload["total"]  # kept for callers written against dN output
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_turn(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    state_path = Path(args.state)
    try:
        if args.init:
            if state_path.exists() and not args.force:
                raise DungeonError(
                    f"{state_path} already exists; pass --force to overwrite it")
            state = new_state(level=args.level or 1)
            save_state(state_path, state)
            print(json.dumps({"initialised": str(state_path), "state": state}, indent=2))
            return 0
        state = load_state(state_path)
        payload = advance_turn(state, data_dir, _dice(args), rest=args.rest)
    except DungeonError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (TableNotFoundError, TableDataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not args.dry_run:
        save_state(state_path, payload["state"])
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_reveal(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    try:
        if args.hide:
            payload = hide(state_path, args.hide)
        elif args.ids:
            payload = reveal(state_path, Path(args.areas), args.ids)
        else:
            payload = {"revealed": load_revealed(state_path)}
    except RevealError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    dice = _dice(args)
    try:
        if args.kind == "surprise":
            payload = surprise_check(dice)
        elif args.kind == "morale":
            if args.target is None:
                print("error: morale needs --target <2-12>", file=sys.stderr)
                return 1
            payload = morale_check(args.target, dice, modifier=args.mod)
        else:
            payload = roll_table("ose/reaction", data_dir, dice, modifier=args.mod)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (TableNotFoundError, TableDataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_gen_character(args: argparse.Namespace) -> int:
    try:
        payload = roll_character(_dice(args), character_class=args.character_class)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
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
                # Bands may run past the dice range so a modifier still lands, so
                # count only the results the dice can reach unmodified.
                spec = parse_dice(table["dice"])
                count = len({
                    n for b in table["ranges"]
                    for n in range(max(b["min"], spec.minimum),
                                   min(b["max"], spec.maximum) + 1)
                })
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
    p_table.add_argument("--mod", type=int, default=0,
                         help="Modifier added to the roll, e.g. a CHA reaction adjustment")
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

    p_roll = subparsers.add_parser("roll", help="Roll dice (e.g. d20, 3d6, 1d8+1)")
    p_roll.add_argument("dice", help="Dice notation: dN, NdN, or NdN+M")
    _add_common_args(p_roll)
    p_roll.set_defaults(func=_cmd_roll)

    p_turn = subparsers.add_parser(
        "turn", help="Advance one OSE dungeon turn: clock, light, rest, wandering check")
    p_turn.add_argument("--state", default="state/clock.json",
                        help="Path to the dungeon clock file")
    p_turn.add_argument("--init", action="store_true",
                        help="Write a fresh clock file instead of advancing")
    p_turn.add_argument("--force", action="store_true",
                        help="With --init, overwrite an existing clock file")
    p_turn.add_argument("--rest", action="store_true",
                        help="Spend this turn resting and reset the rest counter")
    p_turn.add_argument("--level", type=int, default=None, help="Dungeon level, with --init")
    p_turn.add_argument("--dry-run", action="store_true",
                        help="Roll the turn without writing the new state")
    _add_common_args(p_turn)
    p_turn.set_defaults(func=_cmd_turn)

    p_reveal = subparsers.add_parser(
        "reveal", help="Show map areas in the fog-of-war viewer; no ids lists them")
    p_reveal.add_argument("ids", nargs="*", help="Area ids, e.g. 7 c2 s1")
    p_reveal.add_argument("--hide", nargs="+", default=None, metavar="ID",
                          help="Put these areas back under the fog")
    p_reveal.add_argument("--state", default="state/revealed.js",
                          help="Path to the reveal file the viewer polls")
    p_reveal.add_argument("--areas", default="map/areas.json",
                          help="Path to the viewer's area list, for validating ids")
    p_reveal.set_defaults(func=_cmd_reveal)

    p_check = subparsers.add_parser("check", help="Roll an OSE reaction, morale, or surprise check")
    p_check.add_argument("kind", choices=["reaction", "morale", "surprise"])
    p_check.add_argument("--target", type=int, default=None,
                         help="Morale score, 2-12, required for morale")
    p_check.add_argument("--mod", type=int, default=0, help="Situational modifier")
    _add_common_args(p_check)
    p_check.set_defaults(func=_cmd_check)

    p_gen = subparsers.add_parser("gen-character", help="Roll an OSE character, 3d6 down the line")
    p_gen.add_argument("--class", dest="character_class", default="Fighter",
                       help="Bard, Cleric, Dwarf, Elf, Fighter, Halfling, Magic-User, or Thief")
    _add_common_args(p_gen)
    p_gen.set_defaults(func=_cmd_gen_character)

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
