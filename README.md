# Solo RPG Toolkit for Claude Code

Run a solo tabletop RPG session as a back-and-forth with Claude Code. The toolkit handles dice, oracles, scene tests, and dual-vault note-keeping; you bring the player.

## Quickstart

Three steps. Requires [`uv`](https://docs.astral.sh/uv/) and [`claude`](https://claude.com/claude-code).

```bash
# 1. Clone and install
git clone https://github.com/<you>/solo-rpg-toolkit.git ~/git/solo-rpg-toolkit
cd ~/git/solo-rpg-toolkit && uv tool install --editable .

# 2. Scaffold a campaign
solo-campaign "My Campaign" ~/rpg/my-campaign --vault ~/Obsidian/Solo

# 3. Play
cd ~/rpg/my-campaign && claude
```

First message to the agent:

> *"Let's start a new Ironsworn campaign with Mythic GME on top. Walk me through character creation, then frame the opening scene."*

## What `solo-campaign` does

One idempotent command:
- Creates `~/rpg/my-campaign/` from `example-campaign/` template, with `CLAUDE.md` and `dm-notes/`
- Symlinks selected skills into `~/rpg/my-campaign/.claude/skills/` — **project-local**, scoped to this campaign only (no cross-campaign trigger collisions)
- Creates `~/Obsidian/Solo/{Session Log,People,Places,Threads,Lore}` if missing
- Verifies `solo-roll` is on PATH; runs `uv tool install --editable .` from the repo if not

Fails fast if the target campaign directory already exists. If you omit `--vault`, prompts interactively.

### Picking skills per campaign

By default all skills install. Use `--skills` to pick a subset:

```bash
# Ironsworn only, no Mythic oracle layer
solo-campaign "Lite" ~/rpg/lite --vault ~/Obsidian/Solo \
  --skills ironsworn,solo-journaler

# Pure freeform — no system skills triggering at all
solo-campaign "Free" ~/rpg/free --vault ~/Obsidian/Solo --skills none
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
