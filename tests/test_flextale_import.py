"""Tests for `flextale_import.import_flextale`, run on fake PDF text written for these tests.

The extractor is injected, so no PDF or `pdftotext` is involved.
"""
import json
from pathlib import Path

import pytest

from solo_roll.flextale_import import (
    FlextaleImportError,
    default_output_dir,
    import_flextale,
    load_overrides,
    main,
)
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


GAP_RAW = "Table 6: Simple AI Targeting\nD20 Outcome\n01-10 Near\n12-20 Far\n"
TARGET = "quickstart/simple-ai-target"


def _fix(*ops: dict, table: str = TARGET) -> dict:
    return {table: list(ops)}


def test_add_op_fills_a_gap_so_the_table_loads(tmp_path: Path):
    overrides = _fix({"op": "add", "min": 11, "max": 11, "result": "Between"})

    result = import_flextale(PDF, tmp_path, fake_extractor(raw=GAP_RAW), overrides=overrides)

    assert result.skipped == {}
    assert roll_table(TARGET, tmp_path, ScriptedDice([11]))["result"] == "Between"
    assert roll_table(TARGET, tmp_path, ScriptedDice([12]))["result"] == "Far"


def test_set_op_corrects_an_overlap_and_trims_a_result(tmp_path: Path):
    raw = "Table 6: Simple AI Targeting\nD20 Outcome\n01-11 Near page 40\n11-20 Far\n"
    overrides = _fix(
        {"op": "set", "match": [1, 11], "max": 10, "result": "Near"},
    )

    result = import_flextale(PDF, tmp_path, fake_extractor(raw=raw), overrides=overrides)

    assert result.skipped == {}
    assert roll_table(TARGET, tmp_path, ScriptedDice([10]))["result"] == "Near"
    assert roll_table(TARGET, tmp_path, ScriptedDice([11]))["result"] == "Far"


def test_remove_op_drops_a_band(tmp_path: Path):
    raw = "Table 6: Simple AI Targeting\nD20 Outcome\n01-20 Whole\n05-06 Stray\n"

    result = import_flextale(
        PDF, tmp_path, fake_extractor(raw=raw), overrides=_fix({"op": "remove", "match": [5, 6]})
    )

    assert result.skipped == {}
    assert roll_table(TARGET, tmp_path, ScriptedDice([5]))["result"] == "Whole"


def test_replace_op_swaps_all_bands_and_can_create_a_missing_table(tmp_path: Path):
    bands = [{"min": 1, "max": 20, "result": "Only"}]
    overrides = {"quickstart/never-parsed": [{"op": "replace", "ranges": bands}]}

    result = import_flextale(PDF, tmp_path, fake_extractor(), overrides=overrides)

    assert result.written == ["quickstart/never-parsed"]
    assert roll_table("quickstart/never-parsed", tmp_path, ScriptedDice([7]))["result"] == "Only"


def test_override_that_leaves_a_table_broken_still_reports_it_skipped(tmp_path: Path):
    overrides = _fix({"op": "add", "min": 11, "max": 11, "result": "x"}, {"op": "add", "min": 12, "max": 12, "result": "y"})

    result = import_flextale(PDF, tmp_path, fake_extractor(raw=GAP_RAW), overrides=overrides)

    assert TARGET in result.skipped


def test_set_that_matches_no_band_raises(tmp_path: Path):
    with pytest.raises(FlextaleImportError, match="no band 3-4"):
        import_flextale(
            PDF, tmp_path, fake_extractor(raw=GAP_RAW),
            overrides=_fix({"op": "set", "match": [3, 4], "result": "x"}),
        )


def test_override_for_a_table_the_import_did_not_produce_raises(tmp_path: Path):
    with pytest.raises(FlextaleImportError, match="quickstart/nope"):
        import_flextale(
            PDF, tmp_path, fake_extractor(raw=GAP_RAW),
            overrides=_fix({"op": "add", "min": 1, "max": 1, "result": "x"}, table="quickstart/nope"),
        )


def test_unknown_op_raises(tmp_path: Path):
    with pytest.raises(FlextaleImportError, match="unknown op"):
        import_flextale(PDF, tmp_path, fake_extractor(raw=GAP_RAW), overrides=_fix({"op": "frob"}))


def test_load_overrides_rejects_bad_json_and_wrong_shape(tmp_path: Path):
    bad = tmp_path / "o.json"
    bad.write_text("{nope")
    with pytest.raises(FlextaleImportError, match="not valid JSON"):
        load_overrides(bad)
    bad.write_text("[]")
    with pytest.raises(FlextaleImportError, match="object"):
        load_overrides(bad)


def _run_main(tmp_path: Path, *extra: str, raw: str = GAP_RAW, overrides_text: str | None = None):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")
    out = tmp_path / "out"
    if overrides_text is not None:
        out.mkdir()
        (out / "overrides.json").write_text(overrides_text)
    return main([str(pdf), str(out), *extra], extract=fake_extractor(raw=raw), env={}, home=tmp_path), out


FIX_TEXT = json.dumps(_fix({"op": "add", "min": 11, "max": 11, "result": "Between"}))


def test_main_applies_overrides_json_from_the_output_folder(tmp_path: Path):
    code, out = _run_main(tmp_path, overrides_text=FIX_TEXT)

    assert code == 0
    assert roll_table(TARGET, out, ScriptedDice([11]))["result"] == "Between"


def test_main_overrides_flag_names_a_file_elsewhere(tmp_path: Path):
    elsewhere = tmp_path / "mine.json"
    elsewhere.write_text(FIX_TEXT)

    code, _ = _run_main(tmp_path, "--overrides", str(elsewhere))

    assert code == 0


def test_main_exits_two_when_the_named_overrides_file_is_missing(tmp_path: Path, capsys):
    code, _ = _run_main(tmp_path, "--overrides", str(tmp_path / "none.json"))

    assert code == 2
    assert "none.json" in capsys.readouterr().err


def test_main_exits_two_on_a_bad_override_op(tmp_path: Path, capsys):
    code, _ = _run_main(tmp_path, overrides_text=json.dumps(_fix({"op": "frob"})))

    assert code == 2
    assert "unknown op" in capsys.readouterr().err


COIN_LAYOUT = """\
FlexTable 3: QuickStart Treasure Low Coin

      A          B         C        D       OSR
    1-10       1-20      1-20     1-20      1d4 gp / 2d4 gp / 3d4 gp
    11-20        -         -        -       1d6 gp / 2d6 gp / 3d6 gp / 4d6 x 2 gp
"""
COIN_TABLE = "quickstart/treasure-low-coin-a-osr"


def _coin_import(tmp_path: Path, overrides=None):
    return import_flextale(PDF, tmp_path, fake_extractor(layout=COIN_LAYOUT), overrides=overrides)


def test_coin_band_that_fails_for_some_context_is_kept_and_flagged(tmp_path: Path):
    result = _coin_import(tmp_path)

    assert COIN_TABLE in result.written
    assert result.flagged[COIN_TABLE] == ["1-10"]


def test_coin_band_every_context_can_read_is_not_flagged(tmp_path: Path):
    ok = "1d4 gp / 2d4 gp / 3d4 gp / 4d4 gp"
    fix = {COIN_TABLE: [{"op": "set", "match": [1, 10], "result": ok}]}

    assert COIN_TABLE not in _coin_import(tmp_path, fix).flagged


def test_main_warns_about_a_flagged_coin_band_but_exits_zero(tmp_path: Path, capsys):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"")

    code = main([str(pdf), str(tmp_path / "out")], extract=fake_extractor(layout=COIN_LAYOUT), env={}, home=tmp_path)

    err = capsys.readouterr().err
    assert code == 0
    assert COIN_TABLE in err and "1-10" in err
