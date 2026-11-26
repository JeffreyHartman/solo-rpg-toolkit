"""The FlexTale Simple AI: each monster's turn rolls an action table and, for an attack, a target table.

`decide` appends the two mechanics cards and a `monster_decision` event for the ruleset to
resolve. The result text is read by keyword: "attack" attacks, "flee" flees, and any other
action is reported without a mechanical effect. A target text with "weak" or "lowest" picks
the member with the fewest HP, "strong" or "highest" the most, and anything else the first
member still standing.
"""
from pathlib import Path
from typing import Any

from ... import party
from ...errors import IllegalActionError
from ...registry import AUTO, CommandContext, Event, Registry
from .tabledata import card, roll

__all__ = ["register"]

ACTION_TABLE = "simple-ai-action"
TARGET_TABLE = "simple-ai-target"


def register(registry: Registry, data_dir: Path) -> None:
    def run(state: dict[str, Any], monster_id: str, ctx: CommandContext) -> list[Event]:
        return decide(state, monster_id, data_dir, ctx)

    registry.add_procedure(
        "simple_ai", lambda state, command, ctx: run(state, command["inputs"]["monster"], ctx), AUTO,
        label="Monster action", inputs={"monster": {"type": "string", "label": "Monster id"}},
    )
    registry.add_trigger("monster_turn", lambda state, event, ctx: run(state, event["monster"], ctx))


def decide(state: dict[str, Any], monster_id: str, data_dir: Path, ctx: CommandContext) -> list[Event]:
    combat = state.get("combat")
    monster = next((m for m in (combat or {}).get("monsters", []) if m["id"] == monster_id), None)
    if monster is None or monster["status"] != "alive":
        return []
    who = f"{monster['name']} {monster['id']}"
    action = roll(data_dir, ACTION_TABLE, ctx.dice)
    events = [card("simple-ai-action", action, who)]
    text = action["result"]
    kind = "attack" if "attack" in text.lower() else "flee" if "flee" in text.lower() else "other"
    decision: Event = {"type": "monster_decision", "monster": monster_id, "kind": kind, "action": text,
                       "target": None, "text": f"{who} chooses: {text}."}
    if kind == "attack":
        target = roll(data_dir, TARGET_TABLE, ctx.dice)
        events.append(card("simple-ai-target", target, who))
        decision["target"] = _pick_member(state, target["result"])
    return [*events, decision]


def _pick_member(state: dict[str, Any], text: str) -> str:
    members = party.standing(state)
    if not members:
        raise IllegalActionError("no party member is standing to be attacked")
    low = text.lower()
    if "weak" in low or "lowest" in low:
        return min(members, key=lambda m: m.get("hp", 0))["name"]
    if "strong" in low or "highest" in low:
        return max(members, key=lambda m: m.get("hp", 0))["name"]
    return members[0]["name"]
