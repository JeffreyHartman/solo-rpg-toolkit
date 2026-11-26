# Solo RPG Toolkit — Repo Notes for Claude Code

You are working in the **toolkit source**, not a running campaign. When developing here you're modifying skills, the `solo-roll` CLI, the `solo-campaign` bootstrap, or the JSON data tables that back them.

If a user wants to **play** a session, they run `solo-campaign <name> <path>` to scaffold a campaign dir, then `claude` inside that dir — that campaign's `CLAUDE.md` is a different file.

## What this project is

A Python package plus Claude Code skills for solo tabletop RPGs:
- `solo-roll` — dice + table lookups + Mythic GME 2e fate chart math
- `solo-campaign` — scaffolds a fresh campaign folder, symlinks selected skills into `<campaign>/.claude/skills/` (project-local), creates Obsidian vault subdirs
- Skills under `skills/` — `ironsworn` (rules/moves/oracles), `mythic-gme` (fate/scene/event), `solo-journaler` (dual-vault notes)

Both CLIs ship from one package (`solo-roll` on PyPI naming, two `[project.scripts]` entries).

## Layout

```
src/solo_roll/        # Python package — both CLIs ship here
  cli.py              # `solo-roll` entry point (table, fate-check, meaning-pair, quickset, roll)
  campaign.py         # `solo-campaign` entry point + helpers
  rng.py              # DiceSource protocol + RandomDice + ScriptedDice
  tables.py           # JSON table loader + roll_table
  charts.py           # Fate chart math + fate_check
  quicksets.py        # Multi-step chain runner
data/
  tables/             # JSON d-tables (action1, descriptor1, elements/*, mythic/*)
  charts/             # Fate chart JSON
  quicksets/          # Multi-step chain definitions
skills/               # Claude Code skills (markdown only)
example-campaign/     # Template that solo-campaign copies
tests/                # pytest, all unit tests
docs/
  ROADMAP.md          # Sub-projects + checkboxes
  superpowers/        # specs/ and plans/ from brainstorming workflow
reference/            # Local-only PDFs + extracted markdown (gitignored)
```

## Dev workflow

### Run tests
```bash
pytest --tb=short -q       # all tests, terse output
pytest -v -k <pattern>     # specific tests
```

Approach is TDD: write failing test → run it (confirm fail) → implement minimum → confirm pass → commit. Frequent commits, one logical change each.

### Editable install during dev
```bash
uv tool install --editable . --reinstall
```
`src/solo_roll/` edits propagate without reinstall. After adding a new entry point, run with `--reinstall` to register it.

### Adding a table
Drop a JSON file into `data/tables/<name>.json`. Two formats — mutually exclusive:
- **Flat:** `{name, display_name, description, dice, source, entries: ["...", ...]}` — index by roll-1
- **Weighted:** `{name, display_name, description, dice, source, ranges: [{min, max, result}, ...]}` — used for d100 lookups with non-uniform weights

`description` is a one-line string explaining what the table covers. It is optional in the schema, but ship every new table with one — `solo-roll list` surfaces it as the table's user-facing summary, and the test suite asserts every shipped table has one.

No rebuild. No reinstall. `solo-roll table <name>` reads it directly. Nested paths work too: `data/tables/elements/plottwist.json` → `solo-roll table elements/plottwist`. Use `solo-roll list` (or `solo-roll list <prefix>`) to see what's available.

### Adding an OSE table
Same as any table, under `data/tables/ose/`. A 2d6 table uses `ranges`, not
`entries`, because 2d6 is not uniform; the loader rejects flat entries for any
multi-die spec. Pad the outermost bands past the natural range (`min: -20`,
`max: 30`) so a modifier still lands somewhere.

### Adding to the OSE campaign template
`templates/ose/` is the engine plus the OSE system layer. It must stay
module-neutral: nothing in `CLAUDE.md`, `rules/`, or the output style may name a
published adventure. Module specifics belong in the campaign's own `module.md`
and `dungeon/`. `docs/dungeon-schema.md` is the contract a per-module conversion
script writes against.

### Adding a fate chart likelihood
Edit `data/charts/mythic-fate.json` — add to `likelihoods` array and `thresholds` object. Update `KnownLikelihood` frozenset in `src/solo_roll/charts.py`.

### Adding a `solo-roll` subcommand
1. Add `_cmd_<name>(args)` handler in `src/solo_roll/cli.py`
2. Register parser in `main()` next to existing subcommands
3. Add tests in `tests/test_cli.py` using `subprocess.run(["solo-roll", ...])`

## Conventions

- **TDD** + frequent commits (one logical change per commit)
- Keep functions small, **inject paths/dependencies** for testability — don't have helpers reach for `Path.home()` or `__file__` inside; pass them in
- Tests use `tmp_path` and `monkeypatch` — no real filesystem state outside tmp
- **Don't add golden-value tests against seeded stdlib RNG** — those test CPython's `random`, not our code. Inject `ScriptedDice` with explicit values instead.
- Helpers raise typed exceptions (`CampaignError`, `FateChartError`, `TableNotFoundError`); only `main()` translates to exit codes
- JSON output for CLIs: 2-space indent, `json.dumps(payload, indent=2)`

## Big features go through superpowers

For non-trivial sub-projects (anything in `docs/ROADMAP.md`):
1. `/superpowers:brainstorming` → design spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
2. `/superpowers:writing-plans` → implementation plan in `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
3. `/superpowers:subagent-driven-development` → execute task-by-task with two-stage review
4. Merge to main with `git merge --ff-only feat/<branch>`, tag `v0.X.Y`

Worktrees go in `.worktrees/<feature>` (gitignored).

## What NOT to commit

- `reference/` — PDFs (Mythic 2e, etc.) and extracted book content. Copyrighted.
- `data/tables/mythic/actions.json`, `descriptions.json` — if populated from the Mythic 2e book, those word lists are copyrighted. Ship only scaffolding/empty files.
- `.worktrees/` — already in `.gitignore`
- Anything under `pdfs/` or `data/mythic2e.md`

## Current sub-project status

See `docs/ROADMAP.md`. As of `v0.2.0`: sub-projects 1 (core CLI), 2 (mythic skill rewrite), 3 (campaign bootstrap) shipped. Next: PDF→markdown pipeline, enhanced journaling, additional systems, distribution.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues and are managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels, each label string equal to its role name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and one `docs/adr/` at the repo root. See `docs/agents/domain.md`.
