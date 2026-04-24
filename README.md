# Solo RPG Toolkit for Claude Code

Modular skills for running solo tabletop RPGs in Claude Code. Each skill is self-contained — use what you want, ignore what you don't. Layer them: system (Ironsworn, PF2e, etc.) + oracle layer (Mythic GME) + note-taker.

## Install the `solo-roll` CLI

`solo-roll` is the Python CLI that backs the dice-and-tables layer used by every skill in this repo. Install it once via `uv tool`:

```bash
cd ~/git/solo-rpg-toolkit   # or wherever you cloned this
uv tool install --editable .
solo-roll table action1
```

If the last command prints JSON, you're set. Editable install means edits to `src/solo_roll/` take effect immediately — no reinstall while iterating.

### Subcommands

- `solo-roll table <name>` — roll a single table (flat or nested, e.g. `elements/plottwist`)
- `solo-roll meaning-pair` — roll Mythic Meaning Tables (action + descriptor) in one call
- `solo-roll fate-check --likelihood <key> --cf <1..9>` — full Mythic fate check
- `solo-roll quickset <id>` — run a quickset chain (`npc_profile`, `location_profile`, `creature_profile`)

Every subcommand accepts `--seed N` (reproducibility) and `--data DIR` (override data directory).

### Data layout

```
data/tables/<name>.json               # flat d-tables (action1, descriptor1, ...)
data/tables/elements/<name>.json      # specialized tables (plot twist, creature, etc.)
data/charts/mythic-fate.json          # Mythic 2e fate chart
data/quicksets/<id>.json              # multi-step chains
```

Add new tables by dropping a JSON file into `data/tables/` — no rebuild, no reinstall. See any existing file for the schema.

## Bootstrap a campaign with `solo-campaign`

Once `solo-roll` is installed (above — `solo-campaign` ships in the same package), one command scaffolds a fresh campaign:

```bash
solo-campaign "Bleak Winter" ~/rpg/bleak-winter --vault ~/Obsidian/Solo
```

What it does:
- Copies `example-campaign/` to `~/rpg/bleak-winter/` and substitutes the campaign name + vault path into the new `CLAUDE.md`
- Symlinks each skill (`ironsworn`, `mythic-gme`, `solo-journaler`) into `~/.claude/skills/` — edits in your repo propagate immediately
- Verifies `solo-roll` is on PATH; runs `uv tool install --editable .` from the repo if not
- Creates `~/Obsidian/Solo/{Session Log,People,Places,Threads,Lore}` if missing

If you omit `--vault`, the script prompts for the vault path interactively. Use `--skills-dir <path>` (or the `CLAUDE_SKILLS_DIR` env var) to override the default `~/.claude/skills/` location.

The script fails fast if the target campaign directory already exists — it never overwrites.

### Windows

`solo-campaign` is Linux/macOS-first. On Windows, use the manual setup at the bottom of this README (Copy-Item commands), then edit the new `CLAUDE.md` to set `PLAYER_VAULT_PATH`.

## What's in here

```
skills/
├── ironsworn/        # Ironsworn rules, moves, oracles (CC-BY, full tables)
├── mythic-gme/       # Mythic 2e mechanics (scaffolding; plug in your book's tables)
└── solo-journaler/   # Dual-vault notes — player's Obsidian vault vs. GM-only notes

example-campaign/      # Copy/rename this per campaign
├── CLAUDE.md          # Wires skills together, sets player vault path
└── dm-notes/          # Agent's private notes (CF, hidden NPC truths, etc.)
```

## Install (one-time)

Claude Code looks for skills in `~/.claude/skills/` (user-level, available everywhere) or `.claude/skills/` (project-level, scoped to one folder).

For these to be available across all your solo campaigns, go user-level:

```bash
# macOS / Linux / WSL
mkdir -p ~/.claude/skills
cp -r skills/ironsworn ~/.claude/skills/
cp -r skills/mythic-gme ~/.claude/skills/
cp -r skills/solo-journaler ~/.claude/skills/
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path $HOME\.claude\skills | Out-Null
Copy-Item -Recurse skills\ironsworn $HOME\.claude\skills\
Copy-Item -Recurse skills\mythic-gme $HOME\.claude\skills\
Copy-Item -Recurse skills\solo-journaler $HOME\.claude\skills\
```

If you'd rather keep them project-local (useful while iterating — edit the skill and restart `claude`): put them at `.claude/skills/` inside the campaign folder instead.

## Per-campaign setup

1. Copy `example-campaign/` to wherever you want the campaign to live. Rename it.
   ```bash
   cp -r example-campaign ~/rpg/ironsworn-bleak-winter
   cd ~/rpg/ironsworn-bleak-winter
   ```
2. Open `CLAUDE.md` and edit:
   - `PLAYER_VAULT_PATH` → path to a folder inside your Obsidian vault for character-side notes. Create the folder if it doesn't exist.
3. *(Optional but recommended)* Open `skills/mythic-gme/meaning-tables.md` and populate the d100 Action and Description tables from your copy of the Mythic GME 2e book. Until you do, the toolkit will fall back to Ironsworn's Action/Theme oracle, which works fine but is slightly different in flavor. Same for `event-focus.md` — fill in the d100 percentage ranges from your book.
4. Launch Claude Code in the campaign folder:
   ```bash
   cd ~/rpg/ironsworn-bleak-winter
   claude
   ```
5. First message: "Let's start a new Ironsworn campaign with Mythic GME on top. Walk me through character creation, then frame the opening scene."

## Tonight's first session — quick flow

Once you're in Claude Code with the campaign folder open:

1. **Character** — agent walks you through the template, asks about vows, writes `Character.md` into your player vault.
2. **World setup** — default is the Ironlands. If you want somewhere else, tell it.
3. **Opening scene** — agent does a scene test (will probably come up "as expected" since CF starts at 5 and you haven't rolled yet), frames the scene.
4. **Play** — you describe intent, agent tells you which move is triggered, you roll physical or digital dice and report results, agent narrates outcomes and rolls oracles as needed. You say "fate check, X likelihood" or "roll on the Theme oracle" when you want.
5. **Wrap** — when you're done, tell the agent "good stopping point." It writes both session logs (DM-side + player-facing) and updates the mythic state file.

## Publishing your own skills

Each skill is a self-contained folder with a `SKILL.md` (with frontmatter `name` and `description`) and supporting markdown files. To share one:

1. Zip the skill directory.
2. Recipients drop it into their `~/.claude/skills/` and they're good.

Ideas for new skills (modular, can be combined):
- `une-npc-generator` — Universal NPC Emulator
- `pf2e-adventure-runner` — run published PF2e APs from markdown conversions
- `golarion-world` — worldbuilding reference for Pathfinder setting
- `westmarches-tracker` — shared-world bookkeeping for pseudo-group solo play
- `hex-crawl` — generate and track hex-crawl exploration
- `dungeon-stocker` — classic 1d6 dungeon room contents

The trigger is always the `description` field in frontmatter — write it so Claude Code knows when to activate your skill.

## Notes on what's in `mythic-gme/`

The **fate chart** is reproduced functionally (values match the mechanical logic of Mythic 2e). Double-check against your book if you want exact fidelity.

The **meaning tables** and detailed **event focus percentages** are intentionally left as placeholders. Those word lists are the creative content of Mythic 2e and belong to Tana Pigeon / Word Mill Games. Copy them from your book for personal use.

## License

Skills in this toolkit written by (you) — license as you see fit (MIT, CC-BY, whatever).

The **Ironsworn** rules content in `skills/ironsworn/` (moves, oracles) is by Shawn Tomkin, used under CC BY 4.0. If you publish modifications, preserve attribution.

**Mythic GME 2e** content is NOT included — only the mechanical scaffolding around it. You need your own copy of the book to populate the meaning/focus tables.
