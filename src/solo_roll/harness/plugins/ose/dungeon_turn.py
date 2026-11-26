"""OSE dungeon turn for the harness: Search, Listen, Rest, the torch, and the wandering check.

The clock and the light come from `solo_roll.dungeon`. The wandering check is a
trigger on the `turn` event, so any procedure that takes time gets it.
"""
from pathlib import Path
from typing import Any

from ....dungeon import DungeonError, advance_clock, check_wandering
from ....tables import TableError, load_table, roll_table
from ... import party
from ...errors import IllegalActionError, PluginError
from ...registry import Action, CommandContext, Event

__all__ = [
    "DEFAULT_WANDERING",
    "dungeon_actions",
    "initial_dungeon",
    "light_trigger",
    "listen",
    "move_trigger",
    "rest",
    "search",
    "wandering_trigger",
]

DEFAULT_WANDERING = {"table": "ose/wandering-generic", "interval": 2, "die": 6, "chance": 1}
TORCH_TURNS = 6  # OSE: a torch burns for 1 hour, which is 6 turns
LIGHT_TURNS = {"torch": TORCH_TURNS, "lantern": 24}  # OSE: a lantern flask of oil burns for 4 hours

PROCEDURE_LABELS = {"search": "Search", "listen": "Listen at the door", "rest": "Rest"}


def initial_dungeon(wandering: dict[str, Any] | None) -> Any:
    def build(state: dict[str, Any]) -> dict[str, Any]:
        bearer = state["party"]["members"][0]["name"] if state["party"]["members"] else None
        return {
            "turn": 0,
            "level": 1,
            "room": None,
            "light": [{"kind": "torch", "bearer": bearer, "turns_left": TORCH_TURNS}],
            "turns_since_rest": 0,
            "wandering": wandering,
        }

    return build


def dungeon_actions(state: dict[str, Any]) -> list[Action]:
    return [
        {"id": name, "label": label, "command": {"type": "procedure", "name": name}}
        for name, label in PROCEDURE_LABELS.items()
    ]


def search(data_dir: Path):
    return lambda state, command, ctx: _roll_then_turn("search", "ose/searching", data_dir, state, ctx)


def listen(data_dir: Path):
    return lambda state, command, ctx: _roll_then_turn("listen", "ose/listen-at-door", data_dir, state, ctx)


def rest(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    return _take_turn(state, rest=True)


def move_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    """Moving between areas, or into a newly explored one, takes a dungeon turn."""
    return _take_turn(state, rest=False)


def wandering_trigger(data_dir: Path):
    def run(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
        try:
            report = check_wandering(state["dungeon"], data_dir, ctx.dice)
        except (DungeonError, TableError) as exc:
            raise PluginError(f"wandering check failed: {exc}") from exc
        if not report["checked"]:
            return []
        roll = report["check"]["roll"]
        config = state["dungeon"]["wandering"]
        interval = config.get("interval", 2)
        result = "Wandering monster" if report["encounter"] else "No encounter"
        events: list[Event] = [
            {
                "type": "mechanics",
                "procedure": "wandering_check",
                "dice": f"d{config.get('die', 6)}",
                "rolls": [roll],
                "total": roll,
                "result": result,
                "source": f"OSE wandering monsters: {report['check']['needs']}, every {interval} turns",
                "text": f"Wandering monster check: rolled {roll}, needs {report['check']['needs']}. {result}.",
            }
        ]
        if report["encounter"]:
            monster = report["monster"]["result"]
            events.append(
                {
                    "type": "wandering_encounter",
                    "monster": monster,
                    "distance_feet": report["distance_feet"],
                    "surprise": report["surprise"],
                    "reaction": report["reaction"]["result"],
                    "text": f"A wandering encounter: {monster}, {report['distance_feet']} feet away. "
                    f"Reaction: {report['reaction']['result']}.",
                }
            )
        return events

    return run


def light_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    """Answer a `light_requested` edit: the member's torch or lantern burns in the party's light."""
    kind = event["item"]
    if kind not in LIGHT_TURNS:
        raise IllegalActionError(f"OSE has no burn time for '{kind}' (known: {', '.join(LIGHT_TURNS)})")
    member = party.member(state, event["who"])
    source = {"kind": kind, "bearer": member["name"], "turns_left": LIGHT_TURNS[kind]}
    state["dungeon"]["light"].append(source)
    return [{"type": "light_lit", **source, "text": f"{member['name']}'s {kind} burns for {source['turns_left']} turns."}]


def _roll_then_turn(
    name: str, table: str, data_dir: Path, state: dict[str, Any], ctx: CommandContext
) -> list[Event]:
    try:
        rolled = roll_table(table, data_dir, ctx.dice)
        source = load_table(table, data_dir).get("source", table)
    except TableError as exc:
        raise PluginError(f"{name}: {exc}") from exc
    card: Event = {
        "type": "mechanics",
        "procedure": name,
        "dice": rolled["dice"],
        "rolls": rolled["rolls"],
        "total": rolled["roll"],
        "result": rolled["result"],
        "source": source,
        "text": f"{PROCEDURE_LABELS[name]}: rolled {rolled['roll']} on {rolled['dice']}. {rolled['result']}",
    }
    return [card, *_take_turn(state, rest=False)]


def _take_turn(state: dict[str, Any], rest: bool) -> list[Event]:
    try:
        payload = advance_clock(state["dungeon"], rest=rest)
    except DungeonError as exc:
        raise PluginError(str(exc)) from exc
    state["dungeon"] = payload["state"]
    text = f"Turn {payload['turn']}."
    if rest:
        text += " The party rests."
    elif payload["rest_due"]:
        text += " The party must rest."
    events: list[Event] = [
        {"type": "turn", "turn": payload["turn"], "rested": rest, "rest_due": payload["rest_due"], "text": text}
    ]
    for source in payload["light_expired"]:
        events.append(
            {"type": "light_out", **source, "text": f"{source['bearer']}'s {source['kind']} burns out."}
        )
    if payload["in_darkness"]:
        events.append({"type": "darkness", "text": "The party is in darkness."})
    return events
