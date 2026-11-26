"""OSE character generation: 3d6 down the line, class hit die, CON-modified HP."""
from .checks import CheckError
from .dice import parse_dice, roll_dice
from .rng import DiceSource

__all__ = ["ABILITIES", "CLASS_HIT_DICE", "CLASS_REQUIREMENTS", "CLASS_SAVES", "SAVES", "UNARMORED_AC", "ability_modifier", "roll_character"]

ABILITIES = ("STR", "INT", "WIS", "DEX", "CON", "CHA")

# Bard is Advanced Fantasy (Advanced Player's Tome p34); the rest are Classic Fantasy.
CLASS_HIT_DICE = {
    "Bard": "d6", "Cleric": "d6", "Dwarf": "d8", "Elf": "d6", "Fighter": "d8",
    "Halfling": "d6", "Magic-User": "d4", "Thief": "d4",
}

SAVES = ("death", "wands", "paralysis", "breath", "spells")

# Level 1 saving throw targets (OSE Classic Fantasy: Characters, class tables), in `SAVES` order.
# The Bard row (Advanced Fantasy) is the Thief row.
CLASS_SAVES = {
    "Bard": dict(zip(SAVES, (13, 14, 13, 16, 15))),
    "Cleric": dict(zip(SAVES, (11, 12, 14, 16, 15))),
    "Dwarf": dict(zip(SAVES, (8, 9, 10, 13, 12))),
    "Elf": dict(zip(SAVES, (12, 13, 13, 15, 15))),
    "Fighter": dict(zip(SAVES, (12, 13, 14, 15, 16))),
    "Halfling": dict(zip(SAVES, (8, 9, 10, 13, 12))),
    "Magic-User": dict(zip(SAVES, (13, 14, 13, 16, 15))),
    "Thief": dict(zip(SAVES, (13, 14, 13, 16, 15))),
}

UNARMORED_AC = 9
"""Descending armor class of a character with no armor (OSE Classic Fantasy: Characters)."""

# Minimum ability scores (OSE Classic Fantasy Characters, p10-13; Bard from
# Advanced Fantasy).
CLASS_REQUIREMENTS = {
    "Bard": {"DEX": 9, "INT": 9}, "Dwarf": {"CON": 9}, "Elf": {"INT": 9},
    "Halfling": {"CON": 9, "DEX": 9},
}

# OSE Classic Fantasy: Characters, p13. The same bands serve STR melee, WIS magic
# saves, DEX, and CON hit points. CHA reactions use a flatter spread.
MODIFIER_BANDS = ((3, 3, -3), (4, 5, -2), (6, 8, -1), (9, 12, 0),
                  (13, 15, 1), (16, 17, 2), (18, 18, 3))
CHA_REACTION_BANDS = ((3, 3, -2), (4, 5, -1), (6, 8, -1), (9, 12, 0),
                      (13, 15, 1), (16, 17, 1), (18, 18, 2))


def ability_modifier(score: int, ability: str = "STR") -> int:
    bands = CHA_REACTION_BANDS if ability.upper() == "CHA" else MODIFIER_BANDS
    for low, high, modifier in bands:
        if low <= score <= high:
            return modifier
    raise CheckError(f"ability score out of range: {score}")


def roll_character(dice: DiceSource, character_class: str = "Fighter") -> dict:
    if character_class not in CLASS_HIT_DICE:
        raise CheckError(
            f"unknown class '{character_class}' — "
            f"one of {', '.join(sorted(CLASS_HIT_DICE))}"
        )

    scores = {}
    for ability in ABILITIES:
        rolled = roll_dice(parse_dice("3d6"), dice)
        scores[ability] = rolled["total"]

    unmet = [f"{ability} {minimum} (rolled {scores[ability]})"
             for ability, minimum in CLASS_REQUIREMENTS.get(character_class, {}).items()
             if scores[ability] < minimum]

    hit_die = CLASS_HIT_DICE[character_class]
    hp_roll = roll_dice(parse_dice(hit_die), dice)["total"]
    con = ability_modifier(scores["CON"], "CON")
    return {
        "class": character_class,
        "hit_die": hit_die,
        "abilities": scores,
        # INT has no ability modifier in OSE, so it is not listed.
        "modifiers": {a: ability_modifier(s, a) for a, s in scores.items() if a != "INT"},
        "eligible": not unmet,
        "unmet_requirements": unmet,
        "hit_point_roll": hp_roll,
        "constitution_modifier": con,
        "hit_points": max(1, hp_roll + con),  # always at least 1 per Hit Die
    }
