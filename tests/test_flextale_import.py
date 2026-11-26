"""Tests for `flextale_import.import_flextale`, run on fake PDF text written for these tests.

The extractor is injected, so no PDF or `pdftotext` is involved.
"""
from pathlib import Path

import pytest

from solo_roll.flextale_import import default_output_dir, import_flextale, main
from solo_roll.rng import ScriptedDice
from solo_roll.tables import load_table, roll_table

PDF = Path("unused.pdf")

CONTEXT_TABLE = """\
Some intro text before the table.

FlexTable 1: QuickStart Test Hall

      A          B         C        D                         Outcome
    1-10       1-5       1-12     1-2                    Alpha
    11-19      6-15     13-19    3-20                    Beta
      20      16-20       20       -                     Gamma:
                                                         first extra line
                                                         second extra line

                30
"""


def fake_extractor(layout: str = "", raw: str = ""):
    def extract(pdf: Path, mode: str, first: int, last: int) -> str:
        return layout if mode == "layout" else raw
    return extract


def test_context_table_writes_one_loadable_table_per_context(tmp_path: Path):
    result = import_flextale(PDF, tmp_path, fake_extractor(layout=CONTEXT_TABLE))

    assert sorted(result.written) == [
        "quickstart/test-hall-a",
        "quickstart/test-hall-b",
        "quickstart/test-hall-c",
        "quickstart/test-hall-d",
    ]
    for name in result.written:
        assert load_table(name, tmp_path)["dice"] == "d20"


def test_context_columns_map_to_their_own_ranges(tmp_path: Path):
    import_flextale(PDF, tmp_path, fake_extractor(layout=CONTEXT_TABLE))

    # Context B: 1-5 Alpha, 6-15 Beta, 16-20 Gamma.
    assert roll_table("quickstart/test-hall-b", tmp_path, ScriptedDice([5]))["result"].startswith("Alpha")
    assert roll_table("quickstart/test-hall-b", tmp_path, ScriptedDice([6]))["result"].startswith("Beta")
    # Context D: 3-20 Beta; '-' means the row is absent.
    assert roll_table("quickstart/test-hall-d", tmp_path, ScriptedDice([20]))["result"].startswith("Beta")


def test_continuation_lines_join_the_outcome_and_page_numbers_do_not(tmp_path: Path):
    import_flextale(PDF, tmp_path, fake_extractor(layout=CONTEXT_TABLE))

    result = roll_table("quickstart/test-hall-a", tmp_path, ScriptedDice([20]))["result"]
    assert result == "Gamma: first extra line second extra line"


def _system_row(prefix: str, *cells: str) -> str:
    line = prefix.ljust(48)
    for col, cell in zip((48, 63, 72), cells):
        line = line.ljust(col) + cell
    return line.rstrip()


SYSTEM_TABLE = "\n".join([
    "FlexTable 2: QuickStart Test Check",
    "",
    _system_row("        A            B         C         D", "Alpha-Sys", "Beta", "Gamma Sys"),
    _system_row("       1-9          1-10      1-20      1-20", "10", "7", "+3 on roll"),
    _system_row("", "12", "9"),
    _system_row("", "14", "11"),
    _system_row("       10-20         -         -         -", "Easy:"),
    _system_row("", "Roll again with no bonus."),
    "",
])


def test_system_columns_become_one_table_per_system(tmp_path: Path):
    result = import_flextale(PDF, tmp_path, fake_extractor(layout=SYSTEM_TABLE))

    assert "quickstart/test-check-a-alpha-sys" in result.written
    assert "quickstart/test-check-a-gamma-sys" in result.written
    low = lambda system: roll_table(f"quickstart/test-check-a-{system}", tmp_path, ScriptedDice([3]))["result"]
    assert low("alpha-sys") == "10 / 12 / 14"
    assert low("beta") == "7 / 9 / 11"
    assert low("gamma-sys") == "+3 on roll"


def test_textual_band_applies_to_every_system(tmp_path: Path):
    import_flextale(PDF, tmp_path, fake_extractor(layout=SYSTEM_TABLE))

    for system in ("alpha-sys", "beta", "gamma-sys"):
        result = roll_table(f"quickstart/test-check-a-{system}", tmp_path, ScriptedDice([15]))["result"]
        assert result == "Easy: Roll again with no bonus."


RAW = """\
Table 5: Simple AI Outcomes
D20 Outcome
01-12 Act One
13-19 Act Two
20 Act Three
Simple AI Targets
Table 6: Simple AI Targeting
D20 Outcome
01-10 Near
11-20 Far
Next section heading
"""


def test_simple_ai_tables_come_from_the_raw_text(tmp_path: Path):
    result = import_flextale(PDF, tmp_path, fake_extractor(raw=RAW))

    assert sorted(result.written) == ["quickstart/simple-ai-action", "quickstart/simple-ai-target"]
    assert roll_table("quickstart/simple-ai-action", tmp_path, ScriptedDice([13]))["result"] == "Act Two"
    assert roll_table("quickstart/simple-ai-target", tmp_path, ScriptedDice([11]))["result"] == "Far"


def test_table_with_a_gap_is_skipped_and_reported_without_a_file(tmp_path: Path):
    raw = "Table 6: Simple AI Targeting\nD20 Outcome\n01-10 Near\n12-20 Far\n"

    result = import_flextale(PDF, tmp_path, fake_extractor(layout=CONTEXT_TABLE, raw=raw))

    assert "quickstart/simple-ai-target" in result.skipped
    assert "11" in result.skipped["quickstart/simple-ai-target"]
    assert not (tmp_path / "tables" / "quickstart" / "simple-ai-target.json").exists()
    assert "quickstart/test-hall-a" in result.written


def test_default_output_dir_honors_xdg_data_home(tmp_path: Path):
    assert default_output_dir({"XDG_DATA_HOME": str(tmp_path / "xdg")}, tmp_path / "home") == (
        tmp_path / "xdg" / "solo-rpg-toolkit" / "flextale"
    )


def test_default_output_dir_falls_back_to_local_share(tmp_path: Path):
    assert default_output_dir({}, tmp_path / "home") == (
        tmp_path / "home" / ".local" / "share" / "solo-rpg-toolkit" / "flextale"
    )


def test_main_writes_to_the_output_argument_and_exits_zero(tmp_path: Path, capsys):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")
    out = tmp_path / "out"

    code = main([str(pdf), str(out)], extract=fake_extractor(layout=CONTEXT_TABLE), env={}, home=tmp_path)

    assert code == 0
    assert load_table("quickstart/test-hall-a", out)["dice"] == "d20"
    assert "4 tables written" in capsys.readouterr().out


def test_main_uses_the_default_folder_when_no_output_is_given(tmp_path: Path):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")
    env = {"XDG_DATA_HOME": str(tmp_path / "xdg")}

    main([str(pdf)], extract=fake_extractor(layout=CONTEXT_TABLE), env=env, home=tmp_path)

    assert (tmp_path / "xdg" / "solo-rpg-toolkit" / "flextale" / "tables" / "quickstart").is_dir()


def test_main_exits_one_and_names_the_table_when_one_is_skipped(tmp_path: Path, capsys):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")
    raw = "Table 6: Simple AI Targeting\nD20 Outcome\n01-10 Near\n12-20 Far\n"

    code = main([str(pdf), str(tmp_path / "out")], extract=fake_extractor(raw=raw), env={}, home=tmp_path)

    assert code == 1
    assert "quickstart/simple-ai-target" in capsys.readouterr().err


def test_main_exits_two_when_the_pdf_is_missing(tmp_path: Path, capsys):
    code = main([str(tmp_path / "none.pdf"), str(tmp_path / "out")], extract=fake_extractor(), env={}, home=tmp_path)

    assert code == 2
    assert "not found" in capsys.readouterr().err


def test_main_refuses_an_output_folder_inside_a_git_work_tree(tmp_path: Path, capsys):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    code = main([str(pdf), str(repo / "data")], extract=fake_extractor(layout=CONTEXT_TABLE), env={}, home=tmp_path)

    assert code == 2
    assert not (repo / "data").exists()
    assert "git" in capsys.readouterr().err
