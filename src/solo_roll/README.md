# `solo-roll` — CLI internals and manual usage

`solo-roll` is the Python CLI that backs the dice-and-tables layer used by every skill in this repo. The skills call it for every random operation (dice rolls, table lookups, fate checks). You can also call it directly from a shell — useful for debugging, extending tables, or running a system that doesn't yet have a skill.

`solo-roll` and `solo-campaign` ship from the same package. Installing the repo with `uv tool install --editable .` puts both on PATH.

## Verify install

```bash
solo-roll table action1
```

JSON output → set.

## Subcommands

| Command | Purpose |
|---|---|
| `solo-roll table <name>` | Roll a single table (flat or nested, e.g. `elements/plottwist`) |
| `solo-roll meaning-pair` | Roll Mythic Meaning Tables (action + descriptor) in one call |
| `solo-roll fate-check --likelihood <key> --cf <1..9>` | Full Mythic fate check |
| `solo-roll quickset <id>` | Run a quickset chain (`npc_profile`, `location_profile`, `creature_profile`) |
| `solo-roll roll <dice>` | Raw dice (e.g. `d10`, `d6`, `d100`) |

Every subcommand accepts `--seed N` (reproducibility) and `--data DIR` (override data directory).

## Data layout

```
data/tables/<name>.json               # flat d-tables (action1, descriptor1, ...)
data/tables/elements/<name>.json      # specialized tables (plot twist, creature, etc.)
data/tables/mythic/<name>.json        # Mythic 2e tables (event-focus, optional actions/descriptions)
data/charts/mythic-fate.json          # Mythic 2e fate chart
data/quicksets/<id>.json              # multi-step chains
```

Add new tables by dropping a JSON file into `data/tables/` — no rebuild, no reinstall.

### Table format

Two formats — mutually exclusive:

- **Flat:** `{name, display_name, dice, source, entries: ["..."]}` — index by roll-1
- **Weighted:** `{name, display_name, dice, source, ranges: [{min, max, result}]}` — d100 lookups with non-uniform weights

Nested paths work: `data/tables/elements/plottwist.json` → `solo-roll table elements/plottwist`.

## Notes on Mythic 2e content

The **fate chart** values (`data/charts/mythic-fate.json`) match the Mythic 2e book exactly — yes thresholds and exceptional yes/no caps are computed by the same formulas the book uses.

The **event focus** d100 ranges (`data/tables/mythic/event-focus.json`) also match the book.

The **meaning tables** are intentionally left as placeholders. Tana Pigeon's Action / Description word lists are copyrighted. Populate `data/tables/mythic/actions.json` and `descriptions.json` from your book, then call:

```bash
solo-roll meaning-pair --tables mythic/actions,mythic/descriptions
```

Until then, `solo-roll meaning-pair` falls back to the bundled `action1`/`descriptor1` tables.

## Publishing your own skills

Each skill is a self-contained folder with a `SKILL.md` (frontmatter `name` and `description`) and supporting markdown files. To share one:

1. Zip the skill directory.
2. Recipients drop it into a campaign's `.claude/skills/` (project-local, recommended) or `~/.claude/skills/` (every project, more trigger collisions).

The trigger is the `description` field in frontmatter — write it so Claude Code knows when to activate.

Ideas for new skills (modular, can be combined):
- `une-npc-generator` — Universal NPC Emulator
- `pf2e-adventure-runner` — run published PF2e APs from converted markdown
- `golarion-world` — Pathfinder setting reference
- `westmarches-tracker` — shared-world bookkeeping for pseudo-group solo play
- `hex-crawl` — generate and track hex exploration
- `dungeon-stocker` — classic 1d6 dungeon room contents

## Manual install (Windows)

`solo-campaign` is Linux/macOS-first. For Windows, manually scaffold a campaign:

```powershell
$repo     = "C:\path\to\solo-rpg-toolkit"
$campaign = "C:\path\to\your\campaign"
$vault    = "C:\path\to\Obsidian\Solo"

# Copy template
Copy-Item -Recurse "$repo\example-campaign" $campaign

# Symlink desired skills (project-local)
New-Item -ItemType Directory -Force -Path "$campaign\.claude\skills" | Out-Null
New-Item -ItemType SymbolicLink -Path "$campaign\.claude\skills\ironsworn"      -Target "$repo\skills\ironsworn"
New-Item -ItemType SymbolicLink -Path "$campaign\.claude\skills\mythic-gme"     -Target "$repo\skills\mythic-gme"
New-Item -ItemType SymbolicLink -Path "$campaign\.claude\skills\solo-journaler" -Target "$repo\skills\solo-journaler"

# Vault subdirs
foreach ($sub in "Session Log","People","Places","Threads","Lore") {
    New-Item -ItemType Directory -Force -Path "$vault\$sub" | Out-Null
}
```

Then edit `$campaign\CLAUDE.md` — replace `[Campaign Name]`, the `PLAYER_VAULT_PATH` placeholder, and the `[Active Skills]` block with the skill list you symlinked.

(Symlinks on Windows require Developer Mode or admin shell. `Copy-Item -Recurse` works as fallback for the skills, but won't auto-update on repo edits.)
