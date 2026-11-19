# Solo RPG Toolkit for Claude Code

Run a solo tabletop RPG session as a back-and-forth with Claude Code. The toolkit handles dice, oracles, scene tests, and dual-vault note-keeping; you bring the player.

## Quickstart

Three steps. Requires [`uv`](https://docs.astral.sh/uv/) and [`claude`](https://claude.com/claude-code).

```bash
# 1. Clone and install
git clone https://github.com/<you>/solo-rpg-toolkit.git ~/git/solo-rpg-toolkit
cd ~/git/solo-rpg-toolkit && uv tool install --editable .

# 2. Scaffold a campaign
solo-campaign "My Campaign" ~/rpg/my-campaign

# 3. Play
cd ~/rpg/my-campaign && claude
```

First message to the agent:

> *"Let's start a new Ironsworn campaign with Mythic GME on top. Walk me through character creation, then frame the opening scene."*

## OSE dungeon crawls

A second campaign shape, for running a published old-school dungeon with Claude
as referee rather than as an oracle:

```bash
solo-campaign ose "Barrowmaze" ~/rpg/barrowmaze --module "Barrowmaze Complete"
```

That scaffolds the referee harness, the OSE tables, an empty `dungeon/`, and an
empty `rules/` that you fill with the OSE procedure files. The toolkit does not
ship those files, because they quote the OSE books. The `solo-roll` CLI and the
hooks do not read `rules/`; the referee does. Three layers, kept apart on purpose:

- **Engine**, module- and system-neutral: the three hooks, the statusline, the
  `referee` subagent, the journaler skill, the output style.
- **System**, OSE but module-neutral: `rules/`, `data/tables/ose/`.
- **Module**, per-adventure: `dungeon/`, its own tables, and `module.md`.

`module.md` is the only file that names the adventure. Nothing about it is
hardcoded in `CLAUDE.md` or the output style.

Then convert the module into `dungeon/` against
[docs/dungeon-schema.md](docs/dungeon-schema.md). There is no generic
PDF-to-rooms converter, because every publisher lays out a page differently.
Write one script per module against the documented schema and the engine works
unchanged. `tools/extract_prose.py` dumps a page range of a multi-column PDF in
reading order and is the usual starting point.

### Why the referee cannot read the dungeon

A `PreToolUse` hook denies the main session any read under `dungeon/`, so the key
reaches it only through the `referee` subagent, which returns what the party
perceives and nothing else. This is deliberate: a session that has read a room
key cannot un-know the secret door forty turns later. The same reason drives
`solo-roll turn`, which runs the clock, the light, the rest counter and the
wandering check in one call, so no step can be skipped.

## What `solo-campaign` does

One command:
- Creates `~/rpg/my-campaign/` from `example-campaign/` template, with `CLAUDE.md`, `sessions/`, and a player vault in `playervault/`
- Symlinks selected skills into `~/rpg/my-campaign/.claude/skills/` — **project-local**, scoped to this campaign only (no cross-campaign trigger collisions)
- Creates `playervault/{Session Log,People,Places,Threads,Lore}` inside the campaign folder. Open that folder in Obsidian
- Verifies `solo-roll` is on PATH; runs `uv tool install --editable .` from the repo if not

Fails fast if the target campaign directory already exists. Relative paths are resolved to absolute ones.

### Picking skills per campaign

By default all skills install. Use `--skills` to pick a subset:

```bash
# Ironsworn only, no Mythic oracle layer
solo-campaign "Lite" ~/rpg/lite \
  --skills ironsworn,solo-journaler

# Pure freeform — no system skills triggering at all
solo-campaign "Free" ~/rpg/free --skills none
```

Available skills:
- `ironsworn` — system rules, moves, oracles
- `mythic-gme` — chaos factor, fate checks, scene tests, event focus
- `solo-journaler` — dual-vault note separation

## Tonight's first session — quick flow

Once you're in Claude Code with the campaign folder open:

1. **Character** — agent walks you through the template, asks about vows, writes `Character.md` into your player vault.
2. **World setup** — default is the Ironlands. If you want somewhere else, tell it.
3. **Opening scene** — agent runs a scene test (probably "as expected" since CF starts at 5), frames the scene.
4. **Play** — describe intent, agent tells you which move triggered, you roll dice and report results, agent narrates outcomes and rolls oracles. Say "fate check, X likelihood" or "roll on the Theme oracle" when you want.
5. **Wrap** — say "good stopping point." Agent writes both session logs (DM-side + player-facing) and updates the mythic state file.

## Optional: populate Mythic 2e meaning tables

The fate chart and event focus tables are pre-populated from the Mythic 2e book. The **meaning tables** (Action + Description word lists) ship as scaffolding only — those lists are copyrighted to Tana Pigeon / Word Mill Games. Drop your own `data/tables/mythic/actions.json` and `descriptions.json` from your book; otherwise the toolkit falls back to the bundled `action1`/`descriptor1` tables, which work fine but flavor differently.

## Windows

`solo-campaign` is Linux/macOS-first. For Windows manual setup, see [`src/solo_roll/README.md`](src/solo_roll/README.md#manual-install-windows).

## Going deeper

For manually using the `solo-roll` CLI, data layout, adding new tables, and publishing your own skills, see [`src/solo_roll/README.md`](src/solo_roll/README.md).

## License

Toolkit code: license as you see fit.

The **Ironsworn** rules content in `skills/ironsworn/` (moves, oracles) is by Shawn Tomkin, used under CC BY 4.0. Preserve attribution if you publish modifications.

**Mythic GME 2e** content is NOT included — only the mechanical scaffolding around it. You need your own copy of the book to populate the meaning tables.
