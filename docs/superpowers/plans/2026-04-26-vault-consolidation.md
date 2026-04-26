# Vault Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the dual-vault (dm-notes + external Obsidian vault) into a single `playervault/` subfolder inside the campaign directory, eliminating duplication and making campaigns self-contained.

**Architecture:** Campaign root holds only operational/mechanical files (CLAUDE.md, mythic-state.md, sessions/). All narrative content lives in `./playervault/` which is the Obsidian vault. The `solo-journaler` skill rewrites to single-vault logic. The `solo-campaign` bootstrap stops creating external vault directories.

**Tech Stack:** Python 3.12, pytest, shutil, pathlib, Markdown skill files, Obsidian vault config JSON

---

## Spec

`docs/superpowers/specs/2026-04-26-vault-consolidation-design.md`

---

## File Map

**Delete:**
- `example-campaign/dm-notes/` (entire tree)

**Create:**
- `example-campaign/playervault/.obsidian/app.json`
- `example-campaign/playervault/.obsidian/core-plugins.json`
- `example-campaign/playervault/Session Log/.gitkeep`
- `example-campaign/playervault/People/.gitkeep`
- `example-campaign/playervault/Places/.gitkeep`
- `example-campaign/playervault/Threads/.gitkeep`
- `example-campaign/playervault/Lore/Truths/.gitkeep`
- `example-campaign/sessions/README.md`

**Modify:**
- `example-campaign/CLAUDE.md` — remove PLAYER_VAULT_PATH, update all path refs
- `skills/solo-journaler/SKILL.md` — full rewrite, single vault
- `src/solo_roll/campaign.py` — remove vault arg, internal vault creation, conditional mythic-state.md
- `tests/test_campaign.py` — update/delete vault-related tests, add new ones

**Migrate (ironsworn-test1, last task):**
- `/home/jeff/rpg/claude/ironsworn-test1/` — restructure in place

---

## Task 1: Restructure example-campaign template

**Files:**
- Delete: `example-campaign/dm-notes/` (entire tree)
- Create: `example-campaign/playervault/.obsidian/app.json`
- Create: `example-campaign/playervault/.obsidian/core-plugins.json`
- Create: `example-campaign/playervault/Session Log/.gitkeep`
- Create: `example-campaign/playervault/People/.gitkeep`
- Create: `example-campaign/playervault/Places/.gitkeep`
- Create: `example-campaign/playervault/Threads/.gitkeep`
- Create: `example-campaign/playervault/Lore/Truths/.gitkeep`
- Create: `example-campaign/sessions/README.md`

- [ ] **Step 1: Delete dm-notes tree**

```bash
rm -rf example-campaign/dm-notes
```

- [ ] **Step 2: Create playervault subdirs**

```bash
mkdir -p example-campaign/playervault/.obsidian
mkdir -p example-campaign/playervault/"Session Log"
mkdir -p example-campaign/playervault/People
mkdir -p example-campaign/playervault/Places
mkdir -p example-campaign/playervault/Threads
mkdir -p example-campaign/playervault/Lore/Truths
mkdir -p example-campaign/sessions
```

- [ ] **Step 3: Create .gitkeep files to preserve empty dirs**

```bash
touch "example-campaign/playervault/Session Log/.gitkeep"
touch example-campaign/playervault/People/.gitkeep
touch example-campaign/playervault/Places/.gitkeep
touch example-campaign/playervault/Threads/.gitkeep
touch example-campaign/playervault/Lore/Truths/.gitkeep
```

- [ ] **Step 4: Write .obsidian/app.json**

Write `example-campaign/playervault/.obsidian/app.json`:

```json
{}
```

- [ ] **Step 5: Write .obsidian/core-plugins.json**

Write `example-campaign/playervault/.obsidian/core-plugins.json`:

```json
{
  "file-explorer": true,
  "global-search": true,
  "switcher": true,
  "graph": true,
  "backlink": true,
  "canvas": true,
  "outgoing-link": true,
  "tag-pane": true,
  "footnotes": false,
  "properties": true,
  "page-preview": true,
  "daily-notes": true,
  "templates": true,
  "note-composer": true,
  "command-palette": true,
  "slash-command": false,
  "editor-status": true,
  "bookmarks": true,
  "markdown-importer": false,
  "zk-prefixer": false,
  "random-note": false,
  "outline": true,
  "word-count": true,
  "slides": false,
  "audio-recorder": false,
  "workspaces": false,
  "file-recovery": true,
  "publish": false,
  "sync": true,
  "bases": true,
  "webviewer": false
}
```

- [ ] **Step 6: Write sessions/README.md**

Write `example-campaign/sessions/README.md`:

```markdown
# Sessions

Mechanical session logs — rolls, oracle results, chaos factor shifts, reasoning.
One file per session: `YYYY-MM-DD.md`.

Player-facing narrative journals live in `../playervault/Session Log/`.
```

- [ ] **Step 7: Commit**

```bash
git add example-campaign/
git commit -m "feat(template): replace dm-notes with playervault + sessions at campaign root"
```

---

## Task 2: Rewrite example-campaign/CLAUDE.md

**Files:**
- Modify: `example-campaign/CLAUDE.md`

- [ ] **Step 1: Read current file**

Read `example-campaign/CLAUDE.md` to confirm content before overwriting.

- [ ] **Step 2: Write new CLAUDE.md**

Write `example-campaign/CLAUDE.md`:

```markdown
# Solo RPG Campaign — [Campaign Name]

You are the GM for a solo RPG campaign. Follow the loaded skills strictly.

## Configuration

```
SYSTEM: Ironsworn
ORACLE_LAYER: Mythic GME 2e
```

Player vault: `./playervault/` (Obsidian vault — open this folder in Obsidian)

## Active skills

This campaign uses:
[Active Skills]

Skills are symlinked into `.claude/skills/` of this campaign folder, so they're scoped to this campaign only. Reference the relevant SKILL.md files at session start.

## House rules

*(Add any campaign-specific overrides here. Examples:)*
- Player rolls their own dice and reports results; agent never secretly re-rolls.
- Scene tests are run at the top of every scene, no exceptions.
- When fate check and move result conflict, the move wins — Mythic is the pacing/oracle layer, not the resolution layer.

## Session start procedure

1. Read `./mythic-state.md` (if Mythic is active) and the most recent file in `./sessions/`.
2. Read the most recent file in `./playervault/Session Log/`.
3. Read `./playervault/Character.md` for current character state.
4. Give the player a 3-4 sentence recap of where things stand.
5. Ask what they want to do (or frame a follow-up scene if one is pending).
6. Run the scene test before narrating (if Mythic is active).

## Session end procedure

1. Write today's mechanical log to `./sessions/YYYY-MM-DD.md` with rolls, CF shifts, threads opened/closed, NPCs introduced, oracle reasoning.
2. Write today's player-facing journal to `./playervault/Session Log/YYYY-MM-DD.md` in the character's voice (or close narration). No mechanics, no meta.
3. Update NPC files, place files, thread files in `./playervault/`. Character sheet stats are updated live during play — at session end only update non-stat changes (bonds forged, assets advanced, experience spent).
4. Update `./mythic-state.md` with the new Chaos Factor (if Mythic is active).
5. End with: "Good stopping point. Picking up next time at [hook]."

## Starting a fresh campaign

If `./mythic-state.md` does not exist and Mythic is active, initialize it: CF 5, empty Threads List, empty Characters List.

1. Ask the player about setting (Ironlands default, or custom), their character concept, and their opening vow.
2. Walk them through `character-template.md` in the ironsworn skill.
3. Create `./playervault/Character.md` with starting stats, assets, and opening vow.
4. Frame the opening scene and play.
```

- [ ] **Step 3: Run tests to confirm no breakage**

```bash
pytest tests/test_campaign.py::test_resolve_repo_root_returns_dir_with_pyproject_and_example_campaign -v
```

Expected: PASS (test checks `example-campaign` dir exists, not its contents)

- [ ] **Step 4: Commit**

```bash
git add example-campaign/CLAUDE.md
git commit -m "feat(template): rewrite CLAUDE.md for single-vault layout"
```

---

## Task 3: Rewrite skills/solo-journaler/SKILL.md

**Files:**
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Read current file**

Read `skills/solo-journaler/SKILL.md` before overwriting.

- [ ] **Step 2: Write new SKILL.md**

Write `skills/solo-journaler/SKILL.md`:

```markdown
---
name: solo-journaler
description: Use during any solo RPG session to maintain notes in the player vault at ./playervault/. Activates when new information is introduced — NPCs met, locations visited, vows made, threads opened, discoveries revealed — and at end of session to write session logs.
---

# Solo Journaler Skill

Single source of truth: `./playervault/` relative to campaign root. Open this folder in Obsidian between sessions.

## Vault structure

```
./playervault/
├── Character.md            # current character sheet state
├── Session Log/            # one file per session, ISO dated
│   └── 2026-04-26.md
├── People/                 # NPCs the character has met
│   └── Kesta Ulfhild.md
├── Places/                 # places the character has been or been told of
│   └── Stonebeck.md
├── Threads/                # active vows, mysteries the character is tracking
│   └── Find the Sister.md
└── Lore/                   # worldbuilding the character has learned
    └── Truths/
```

## Mechanical state (not in vault)

- `./mythic-state.md` — chaos factor, threads list, characters list (Mythic GME only; absent otherwise)
- `./sessions/YYYY-MM-DD.md` — mechanical session log: rolls, oracle results, CF shifts, reasoning

## Writing rules

### At the start of a session

1. Read `./sessions/` for the most recent mechanical log.
2. Read `./mythic-state.md` if Mythic is active.
3. Read `./playervault/Character.md` for current character state.
4. Recap for the player: where things stand, what hooks are open.

### During the session

When something note-worthy happens, write it inline — tell the player briefly, then continue:

> *"Adding Kesta to your People folder."*

Minimal skeleton during play. Flesh out at session end.

- New NPC met → create `./playervault/People/<Name>.md`
- New location → create `./playervault/Places/<Name>.md`
- Vow made or mystery opened → create `./playervault/Threads/<Name>.md`
- World lore established → add to `./playervault/Lore/`

### At the end of a session

1. Write `./sessions/YYYY-MM-DD.md` with: rolls made, oracle results, CF shifts, threads opened/closed, NPCs introduced, reasoning behind oracle interpretations.
2. Write `./playervault/Session Log/YYYY-MM-DD.md` — character journal, first person or close narration. No mechanics, no meta.
3. Update `./mythic-state.md` with new Chaos Factor (if Mythic active).
4. Update any People/Places/Threads files that changed this session.
5. Update `./playervault/Character.md` for non-stat changes (bonds forged, assets advanced, experience spent). Stats update live during play.

## What goes in the vault

Write what the **character** has seen, done, heard, or been told. Include the character's own speculation — labeled as such. Write in first person or close third.

Do NOT write oracle mechanics, roll results, chaos factor, or GM reasoning in vault files. Those belong in `./sessions/`.

## Linking conventions

Use Obsidian wikilinks in the vault: `[[Kesta Ulfhild]]`, `[[Stonebeck]]`, `[[Find the Sister]]`. Makes the vault navigable in Obsidian.

## Filename conventions

- Title case for proper nouns: `Kesta Ulfhild.md`, `The Old Road.md`
- ISO date for session logs: `2026-04-26.md`
- Lower-kebab for mechanical files: `mythic-state.md`, `2026-04-26.md`

## Example NPC file

`./playervault/People/Kesta Ulfhild.md`:

```markdown
# Kesta Ulfhild

- **Met**: 2026-04-26, at the smithy in [[Stonebeck]]
- **Appearance**: Older woman in furs, sharpening a blade when we arrived.
- **Demeanor**: Wary but not hostile. Watched our hands more than our faces.

## Known to [character name]

Knew my sister's name before I said it.

## Threads

- [[The Sister's Trail]]

## Last seen

[[Stonebeck]], morning of Session 1.
```

## Example session log (vault side)

`./playervault/Session Log/2026-04-26.md`:

```markdown
# Session — 2026-04-26

Arrived at [[Ashveil]] after a hard road. [[Ossian]] had walked out of [[The Eastern Wood]] on torn feet; [[Fen]] found him and was already tending him when I came down the track.

Whatever took the missing people from Ashveil — it mimics voices. It knows mine now. That's not something you forget.

[[Mara]] was steady when I told her about [[Cian]]. She extracted a promise: I tell her everything, not just what the Ring hears. Fair.

Cian is back, but he's not right.
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): rewrite for single-vault layout, no dm-notes split"
```

---

## Task 4: Write failing tests for campaign.py changes

**Files:**
- Modify: `tests/test_campaign.py`

This task rewrites the test file to reflect the new behavior. Tests are written first and will fail against the old `campaign.py`. The import of `_create_vault` is kept since the function stays (just with a different call site).

- [ ] **Step 1: Read the full current test file**

Read `tests/test_campaign.py` to have it in context.

- [ ] **Step 2: Update fake_template fixture**

The fixture must no longer create `dm-notes/` or put `PLAYER_VAULT_PATH` in CLAUDE.md. Change it to match the new template structure:

In `tests/test_campaign.py`, replace the `fake_template` fixture (lines 54–65):

```python
@pytest.fixture
def fake_template(tmp_path):
    template = tmp_path / "example-campaign"
    template.mkdir()
    (template / "CLAUDE.md").write_text(
        "# Solo RPG Campaign — [Campaign Name]\n\n"
        "Skills:\n[Active Skills]\n"
    )
    vault = template / "playervault"
    vault.mkdir()
    for sub in ("Session Log", "People", "Places", "Threads", "Lore"):
        (vault / sub).mkdir()
    (template / "sessions").mkdir()
    return template
```

- [ ] **Step 3: Update _create_campaign tests**

Remove `vault_path` positional arg from all `_create_campaign(...)` calls (it's the third arg — `Path("/vault/solo")`, `Path("/v")`, etc.). Also update `test_create_campaign_copies_template` to check `playervault/` instead of `dm-notes/`. Delete `test_create_campaign_substitutes_vault_path` entirely.

Replace lines 68–118:

```python
def test_create_campaign_copies_template(tmp_path, fake_template):
    target = tmp_path / "my-campaign"
    _create_campaign("My Campaign", target, fake_template, [])
    assert (target / "CLAUDE.md").is_file()
    assert (target / "playervault").is_dir()


def test_create_campaign_substitutes_name(tmp_path, fake_template):
    target = tmp_path / "my-campaign"
    _create_campaign("Bleak Winter", target, fake_template, [])
    text = (target / "CLAUDE.md").read_text()
    assert "Bleak Winter" in text
    assert "[Campaign Name]" not in text


def test_create_campaign_target_exists_raises(tmp_path, fake_template):
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(FileExistsError):
        _create_campaign("X", target, fake_template, [])


def test_create_campaign_substitutes_active_skills(tmp_path, fake_template):
    target = tmp_path / "c"
    _create_campaign("X", target, fake_template, ["ironsworn", "mythic-gme"])
    text = (target / "CLAUDE.md").read_text()
    assert "[Active Skills]" not in text
    assert "`ironsworn`" in text
    assert "`mythic-gme`" in text
    assert "`solo-journaler`" not in text


def test_create_campaign_active_skills_empty_renders_no_skills_note(tmp_path, fake_template):
    target = tmp_path / "c"
    _create_campaign("X", target, fake_template, [])
    text = (target / "CLAUDE.md").read_text()
    assert "[Active Skills]" not in text
    assert "no skills installed" in text
```

- [ ] **Step 4: Delete test_main_no_vault_non_tty_returns_1**

Delete the entire `test_main_no_vault_non_tty_returns_1` function (lines 405–412 in original file). The `--vault` arg is gone, so this test is obsolete.

- [ ] **Step 5: Update main() integration tests**

Remove `"--vault", str(vault)` args and vault path assertions. Add assertions for `playervault/` inside campaign and conditional `mythic-state.md`.

Replace lines 306–437 with:

```python
def test_main_happy_path_installs_skills_project_local(tmp_path, monkeypatch, capsys):
    """End-to-end: skills land at <campaign>/.claude/skills/, all skills installed by default."""
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )

    target = tmp_path / "my-campaign"

    rc = main(["Bleak Winter", str(target)])

    assert rc == 0
    assert (target / "CLAUDE.md").is_file()
    assert "Bleak Winter" in (target / "CLAUDE.md").read_text()
    assert (target / "playervault").is_dir()
    assert (target / "playervault" / "Session Log").is_dir()
    assert (target / "sessions").is_dir()
    skills_dir = target / ".claude" / "skills"
    assert skills_dir.is_dir()
    skill_names = {p.name for p in skills_dir.iterdir() if p.is_symlink()}
    assert skill_names == {"ironsworn", "ironsworn-truths", "mythic-gme", "solo-journaler"}

    out = capsys.readouterr().out
    assert "ready" in out
    assert str(target) in out


def test_main_creates_playervault_inside_campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target)])
    assert rc == 0
    vault = target / "playervault"
    assert vault.is_dir()
    for sub in ("Session Log", "People", "Places", "Threads", "Lore"):
        assert (vault / sub).is_dir(), f"missing playervault/{sub}"


def test_main_mythic_state_created_when_mythic_gme_in_skills(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "mythic-gme"])
    assert rc == 0
    assert (target / "mythic-state.md").is_file()
    content = (target / "mythic-state.md").read_text()
    assert "Chaos Factor" in content


def test_main_mythic_state_not_created_without_mythic_gme(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "ironsworn"])
    assert rc == 0
    assert not (target / "mythic-state.md").exists()


def test_main_sessions_dir_created(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target)])
    assert rc == 0
    assert (target / "sessions").is_dir()


def test_main_skills_subset_only_installs_chosen(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "mythic-gme,solo-journaler"])
    assert rc == 0
    skills_dir = target / ".claude" / "skills"
    names = {p.name for p in skills_dir.iterdir() if p.is_symlink()}
    assert names == {"mythic-gme", "solo-journaler"}
    text = (target / "CLAUDE.md").read_text()
    assert "`ironsworn`" not in text
    assert "`mythic-gme`" in text


def test_main_skills_none_installs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "none"])
    assert rc == 0
    skills_dir = target / ".claude" / "skills"
    assert skills_dir.is_dir()
    assert list(skills_dir.iterdir()) == []


def test_main_skills_unknown_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "ironsworn,bogus"])
    assert rc == 1
    assert not target.exists()
    err = capsys.readouterr().err
    assert "unknown skill" in err
    assert "bogus" in err


def test_main_target_exists_returns_1(tmp_path, capsys):
    existing = tmp_path / "existing"
    existing.mkdir()
    rc = main(["X", str(existing)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already exists" in err


def test_campaign_settings_written_when_ironsworn_selected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target)])
    assert rc == 0
    settings_file = target / ".claude" / "settings.json"
    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert data["statusLine"]["type"] == "command"
    assert "statusline.sh" in data["statusLine"]["command"]


def test_campaign_settings_not_written_without_ironsworn(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    target = tmp_path / "c"
    rc = main(["X", str(target), "--skills", "none"])
    assert rc == 0
    settings_file = target / ".claude" / "settings.json"
    assert not settings_file.exists()
```

- [ ] **Step 6: Run tests to confirm they fail**

```bash
pytest tests/test_campaign.py -x -q 2>&1 | head -40
```

Expected: multiple failures — `_create_campaign` still takes `vault_path`, `--vault` still required, `playervault` doesn't exist yet, etc.

- [ ] **Step 7: Commit failing tests**

```bash
git add tests/test_campaign.py
git commit -m "test(campaign): update tests for single-vault layout (failing — implementation next)"
```

---

## Task 5: Update campaign.py

**Files:**
- Modify: `src/solo_roll/campaign.py`

- [ ] **Step 1: Read current campaign.py**

Read `src/solo_roll/campaign.py` in full before editing.

- [ ] **Step 2: Update _create_campaign signature and body**

Remove the `vault_path` parameter and the vault path substitution. The signature changes from:
`_create_campaign(name, target, vault_path, template_dir, selected_skills)` → `_create_campaign(name, target, template_dir, selected_skills)`.

Replace the `_create_campaign` function:

```python
def _create_campaign(
    name: str,
    target: Path,
    template_dir: Path,
    selected_skills: list[str],
) -> None:
    """Copy template_dir to target, substituting placeholders in CLAUDE.md."""
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    shutil.copytree(template_dir, target)
    claude_md = target / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text()
        text = text.replace("[Campaign Name]", name)
        text = text.replace("[Active Skills]", _format_active_skills(selected_skills))
        claude_md.write_text(text)
```

- [ ] **Step 3: Update _format_active_skills description for solo-journaler**

Replace the `descriptions` dict inside `_format_active_skills`:

```python
    descriptions = {
        "ironsworn": "system rules, moves, oracles",
        "mythic-gme": "chaos factor, fate checks, scene tests, event focus",
        "solo-journaler": "session journaling, vault note management",
    }
```

- [ ] **Step 4: Update VAULT_SUBDIRS and _create_vault**

`_create_vault` is now always called with an internal path (`target / "playervault"`). No signature change needed — just keep it as-is. The `.obsidian/` dir comes from the template copy, so `_create_vault` only needs to ensure content subdirs exist.

Confirm `VAULT_SUBDIRS` covers all needed subdirs:

```python
VAULT_SUBDIRS = ("Session Log", "People", "Places", "Threads", "Lore")
```

This is already correct — no change needed.

- [ ] **Step 5: Add _create_mythic_state helper**

Add this function after `_create_vault`:

```python
def _create_mythic_state(campaign_path: Path) -> None:
    """Bootstrap mythic-state.md at campaign root with CF 5 and empty lists."""
    (campaign_path / "mythic-state.md").write_text(
        "# Mythic State\n\n"
        "## Chaos Factor\n**Current: 5**\n\n"
        "## Current scene\n*(Set at start of each scene: \"Expected setup = [one sentence]\")*\n\n"
        "## Last scene outcome\n*(in control / out of control / mixed — used to adjust CF at scene end)*\n\n"
        "## Threads List\n"
        "*(Active story threads — problems, quests, unresolved tensions. Numbered for oracle rolls.)*\n\n"
        "1. \n\n"
        "## Characters List\n"
        "*(NPCs in play, including ones the player hasn't met. Numbered for oracle rolls.)*\n\n"
        "1. \n\n"
        "## CF History\n"
        "*(One line per session: date + CF start → CF end + reason)*\n"
    )
```

- [ ] **Step 6: Remove _prompt_vault_path**

Delete the entire `_prompt_vault_path` function:

```python
def _prompt_vault_path() -> Path:
    if not sys.stdin.isatty():
        raise CampaignError("--vault required when not interactive")
    raw = input("PLAYER_VAULT_PATH (path to Obsidian vault folder): ").strip()
    if not raw:
        raise CampaignError("vault path cannot be empty")
    return Path(raw).expanduser()
```

Also remove the `import sys` if it becomes unused — check first (it may still be used elsewhere).

- [ ] **Step 7: Update main()**

Remove `--vault` arg, remove `_prompt_vault_path` call, update `_create_campaign` call, add `_create_vault(target / "playervault")`, add conditional `_create_mythic_state`. Replace the entire `main()` function:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="solo-campaign",
        description="Scaffold a new solo RPG campaign folder.",
    )
    parser.add_argument("name", help="Display name for the campaign")
    parser.add_argument("path", help="Target campaign directory (must not exist)")
    parser.add_argument(
        "--skills", type=str, default=None, dest="skills",
        help="Comma-separated skill names to install "
             "(default: all). Use 'none' to install no skills.",
    )
    args = parser.parse_args(argv)

    repo_root = _resolve_repo_root()
    template_dir = repo_root / "example-campaign"
    skills_source = repo_root / "skills"

    if not template_dir.is_dir():
        print(
            f"error: toolkit install corrupt — example-campaign not found at {template_dir}",
            file=sys.stderr,
        )
        return 1

    target = Path(args.path).expanduser()
    if target.exists():
        print(f"error: {target} already exists", file=sys.stderr)
        return 1

    skills_target = target / ".claude" / "skills"

    try:
        available = _list_available_skills(skills_source)
        selected = _parse_skills_arg(args.skills, available)
        installed_names = selected if selected is not None else available
        _create_campaign(args.name, target, template_dir, installed_names)
        _install_skills(skills_source, skills_target, selected)
        _write_campaign_settings(target, installed_names)
        _ensure_solo_roll(repo_root)
        _create_vault(target / "playervault")
        if "mythic-gme" in installed_names:
            _create_mythic_state(target)
    except (CampaignError, FileExistsError, IsADirectoryError,
            OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"ready — run `claude` in {target}")
    return 0
```

- [ ] **Step 8: Check if sys is still needed**

`sys.stderr` is used in `main()`. Keep `import sys`.

- [ ] **Step 9: Run tests**

```bash
pytest tests/test_campaign.py -x -q
```

Expected: all tests PASS. If failures remain, diagnose and fix before committing.

- [ ] **Step 10: Run full test suite**

```bash
pytest --tb=short -q
```

Expected: all tests PASS.

- [ ] **Step 11: Commit**

```bash
git add src/solo_roll/campaign.py
git commit -m "feat(campaign): remove --vault arg, create playervault/ inside campaign, conditional mythic-state.md"
```

---

## Task 6: Update ROADMAP

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Read ROADMAP.md tail**

Read `docs/ROADMAP.md` to find where to insert sub-project 4.5 (between sub-projects 4 and 5).

- [ ] **Step 2: Insert sub-project 4.5 after sub-project 4 section**

Find the line `## Sub-project 5: Enhanced Journaling + Obsidian Vault` and insert before it:

```markdown
---

## Sub-project 4.5: Pre-published Adventure Support
Play published adventures with Claude as GM. Requires GM secrets (information the player hasn't read) and a dual-vault structure hidden from the player.

- [ ] Adventure extraction pipeline: PDF → structured markdown (encounter blocks, NPC sheets, location maps)
- [ ] Dual-vault restore: `dm-notes/` with hidden layer, player vault with only revealed content
- [ ] `solo-journaler` skill: dual-vault mode with public/hidden section splits
- [ ] GM secrets management: track what player has discovered vs. what remains hidden
- [ ] `solo-campaign` bootstrap flag: `--mode gm-secrets` creates dual-vault structure
- [ ] Test with one short published module (PF2e Beginner Box or similar OSR adventure)

```

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): add sub-project 4.5 pre-published adventure support"
```

---

## Task 7: Migrate ironsworn-test1

**Files (outside toolkit repo):**
- `/home/jeff/rpg/claude/ironsworn-test1/` — campaign to migrate

This task operates on the live campaign directory, not the toolkit repo. Steps are manual file operations. No automated tests.

- [ ] **Step 1: Copy player vault into campaign**

```bash
cp -r /home/jeff/rgp/claude/ironsworn-test1-playervault /home/jeff/rpg/claude/ironsworn-test1/playervault
```

- [ ] **Step 2: Verify copy**

```bash
ls /home/jeff/rpg/claude/ironsworn-test1/playervault/
```

Expected: `Character.md  Lore  People  Places  Session Log  Threads  .obsidian`

- [ ] **Step 3: Move mythic-state.md to campaign root**

```bash
mv /home/jeff/rpg/claude/ironsworn-test1/dm-notes/mythic-state.md \
   /home/jeff/rpg/claude/ironsworn-test1/mythic-state.md
```

- [ ] **Step 4: Move sessions to campaign root**

```bash
mv /home/jeff/rpg/claude/ironsworn-test1/dm-notes/sessions \
   /home/jeff/rpg/claude/ironsworn-test1/sessions
```

- [ ] **Step 5: Review each DM NPC file for non-secret content to fold in**

Read each file in `dm-notes/npcs/` and compare with matching `playervault/People/` file. For each NPC, fold any non-secret flavor (description, demeanor, relationship details) into the player vault file if not already there. DM files for this campaign are `cadoc.md` (the PC), `fen.md`, `mara.md`, `ossian.md`, `cian.md`.

Note: `cadoc.md` is the player character DM notes — fold character summary, stats note, and key relationships section into `playervault/Character.md` if anything is missing.

For each of the 4 NPCs (Fen, Mara, Ossian, Cian): read both files, then update the player vault file if the DM file adds meaningful non-secret flavor. The player vault versions are already good — only add if genuinely additive.

- [ ] **Step 6: Create Campaign Notes in vault for cadoc.md content**

`cadoc.md` contains the scar hook, setting anchors, and background vow details. This is campaign lore, not GM secrets. Create `playervault/Lore/Campaign Notes.md`:

```markdown
# Campaign Notes

## The Scar

Cadoc's wound never fully heals — the Horror that gave it left something behind. What that means is still unknown; it reveals itself through play.

## Setting Anchors

Iron-poor world. No iron weapons for common folk — copper knife, hunting spear, short bow. Bran (Cadoc's hound) is a working partner, not a pet. Cadoc knows the routes between circles better than almost anyone alive.

## Background

The disappearances at Ashveil are plural — multiple people taken, not just Cian. Cause confirmed during truths session: the eastern wood creature that mimics human voices. It lures people in.
```

- [ ] **Step 7: Check dm-notes/locations and dm-notes/threads**

```bash
ls /home/jeff/rpg/claude/ironsworn-test1/dm-notes/locations/
ls /home/jeff/rpg/claude/ironsworn-test1/dm-notes/threads/
```

These are likely empty (only READMEs). If content exists, fold into vault Places/ and Threads/ respectively.

- [ ] **Step 8: Delete dm-notes**

```bash
rm -rf /home/jeff/rpg/claude/ironsworn-test1/dm-notes
```

- [ ] **Step 9: Update ironsworn-test1 CLAUDE.md**

Read `/home/jeff/rpg/claude/ironsworn-test1/CLAUDE.md`, then update:

- Remove the `PLAYER_VAULT_PATH` line and the "Before first session" note below it
- Add `Player vault: ./playervault/` under Configuration
- Replace `dm-notes/mythic-state.md` → `./mythic-state.md` in session start procedure
- Replace `dm-notes/sessions/` → `./sessions/` in session start procedure
- Replace `$PLAYER_VAULT_PATH/` → `./playervault/` throughout
- Replace `dm-notes/sessions/YYYY-MM-DD.md` → `./sessions/YYYY-MM-DD.md` in session end procedure
- Update "Starting a fresh campaign" section: remove dm-notes refs, change mythic-state path
- Update solo-journaler description in active skills list from "dual-vault note separation" to "session journaling, vault note management"

- [ ] **Step 10: Verify final structure**

```bash
find /home/jeff/rpg/claude/ironsworn-test1 -not -path '*/.git/*' -not -path '*/.claude/*' | sort
```

Expected tree:
```
ironsworn-test1/
├── CLAUDE.md
├── mythic-state.md
├── sessions/
│   ├── README.md (if present)
│   └── 2026-04-26.md
└── playervault/
    ├── .obsidian/
    ├── Character.md
    ├── Session Log/
    │   └── 2026-04-26.md
    ├── People/
    │   ├── Cian.md, Fen.md, Mara.md, Ossian.md
    ├── Places/
    │   ├── (location files)
    ├── Threads/
    │   └── (thread files)
    └── Lore/
        ├── Campaign Notes.md
        └── Truths/
            └── (truth files)
```

- [ ] **Step 11: Delete old external vault**

```bash
rm -rf /home/jeff/rgp/claude/ironsworn-test1-playervault
```

- [ ] **Step 12: Commit toolkit changes**

```bash
cd /home/jeff/git/solo-rpg-toolkit
git add -A
git tag v0.3.0
```

Note: all toolkit commits were made in Tasks 1–6. This step just applies the version tag.

---

## Self-review Notes

- `_create_vault` is still exported and tested — no import breakage
- `_prompt_vault_path` is removed — any test importing it needs to remove that import (Task 4 handles this)
- `cadoc.md` content is folded into vault in Task 7 Step 6 — nothing discarded
- `.obsidian/` ships in template → gets copied by `shutil.copytree` → no code needed to create it
- `sessions/` dir is in both template (Task 1) and ensured idempotently by `_create_vault`-equivalent logic — actually `sessions/` comes from template copy only; no code creates it separately. This is fine: the template always has it.
