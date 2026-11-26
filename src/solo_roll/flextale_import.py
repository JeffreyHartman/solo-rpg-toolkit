"""Builds `solo_roll` table JSON from the text of the owner's FlexTale PDF.

`import_flextale` takes the PDF path and an output data folder, and writes
`<out>/tables/quickstart/<slug>-<context>.json`, which `load_table` reads with
`data_dir=<out>`. Text extraction is injected so tests never need a PDF.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .tables import TableError, load_table

Extractor = Callable[[Path, str, int, int], str]

SOURCE = "FlexTale Solo Adventuring Toolkit, QuickStart (imported by the owner)"
CONTEXTS = ("a", "b", "c", "d")

_RANGE = r"(?:\d+(?:-\d*)?|-)"
_ROW = re.compile(rf"^(\s*)({_RANGE})\s+({_RANGE})\s+({_RANGE})\s+({_RANGE})(?:\s+(\S.*))?$")
_TITLE = re.compile(r"^\s*FlexTable\s+\d+:\s*QuickStart\s+(\S.*?)\s*$")
_HEADER = re.compile(r"^(\s*)A(\s+)B(\s+)C(\s+)D(.*)$")


class FlextaleImportError(Exception):
    """Raised when the PDF cannot be read or the output folder is not allowed."""


@dataclass
class ImportResult:
    written: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)


@dataclass
class _Band:
    tokens: list[str]
    lines: list[tuple[int, str]]


@dataclass
class _Table:
    title: str
    pos_b: int = 0
    pos_d: int = 0
    systems: list[tuple[int, str]] = field(default_factory=list)
    bands: list[_Band] = field(default_factory=list)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _parse_layout(text: str) -> list[_Table]:
    tables: list[_Table] = []
    current: _Table | None = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        title = _TITLE.match(line)
        if title:
            current = _Table(title.group(1))
            tables.append(current)
            continue
        if current is None:
            continue
        header = _HEADER.match(line)
        if header:
            current.pos_b = len(header.group(1)) + 1 + len(header.group(2))
            current.pos_d = current.pos_b + 1 + len(header.group(3)) + 1 + len(header.group(4))
            tail_start = current.pos_d + 1
            tail = header.group(5)
            if not current.systems:
                current.systems = [
                    (tail_start + m.start(), m.group())
                    for m in re.finditer(r"\S+(?: \S+)*", tail)
                    if m.group() != "Outcome"
                ]
            continue
        row = _ROW.match(line)
        if row and len(row.group(1)) < current.pos_b:
            tokens = [row.group(n) for n in range(2, 6)]
            lines_of_band: list[tuple[int, str]] = []
            if row.group(6):
                lines_of_band.append((row.start(6), row.group(6)))
            for k, token in enumerate(tokens):
                if token != "-" and token.endswith("-") and i < len(lines):
                    tail_match = re.match(r"\s*(\d+)\s*(.*)$", lines[i])
                    if tail_match:
                        tokens[k] = token + tail_match.group(1)
                        if tail_match.group(2):
                            lines_of_band.append((tail_match.start(2), tail_match.group(2)))
                        i += 1
            current.bands.append(_Band(tokens, lines_of_band))
            continue
        if current.bands and line.strip() and line.strip() != "QuickStart":
            indent = len(line) - len(line.lstrip())
            if indent >= current.pos_d + 2:
                current.bands[-1].lines.append((indent, line.strip()))
    return tables


def _parse_range(token: str) -> tuple[int, int] | None:
    if token == "-":
        return None
    low, _, high = token.partition("-")
    return int(low), int(high or low)


def _table_payload(name: str, display: str, ranges: list[dict]) -> dict:
    return {
        "name": name,
        "display_name": display,
        "description": f"Imported from the owner's FlexTale PDF: {display}.",
        "dice": "d20",
        "source": SOURCE,
        "ranges": ranges,
    }


def _joined_text(band: _Band) -> str:
    return " ".join(text.strip() for _, text in band.lines)


def _system_values(band: _Band, systems: list[tuple[int, str]]) -> list[str]:
    """Splits a band's lines into one string per system column.

    Text that starts with a letter is a rule for every system, not a column of values.
    """
    if not band.lines:
        return [""] * len(systems)
    if re.match(r"[A-Za-z]", band.lines[0][1]):
        return [_joined_text(band)] * len(systems)
    cells: list[list[str]] = [[] for _ in systems]
    for col, text in band.lines:
        for chunk in re.finditer(r"\S+(?: \S+)*", text):
            start = col + chunk.start()
            nearest = min(range(len(systems)), key=lambda k: abs(systems[k][0] - start))
            cells[nearest].append(chunk.group())
    return [" / ".join(cell) for cell in cells]


def _context_tables(table: _Table) -> dict[str, dict]:
    slug = _slug(table.title)
    out: dict[str, dict] = {}
    columns: list[tuple[str, list[str]]]
    if table.systems:
        per_band = [_system_values(band, table.systems) for band in table.bands]
        columns = [
            (f"-{_slug(label)}", [values[k] for values in per_band])
            for k, (_, label) in enumerate(table.systems)
        ]
    else:
        columns = [("", [_joined_text(band) for band in table.bands])]
    for index, context in enumerate(CONTEXTS):
        for suffix, results in columns:
            ranges = []
            for band, result in zip(table.bands, results):
                span = _parse_range(band.tokens[index])
                if span is not None:
                    ranges.append({"min": span[0], "max": span[1], "result": result})
            name = f"quickstart/{slug}-{context}{suffix}"
            label = f"{table.title} (context {context.upper()}"
            label += f", {suffix[1:]})" if suffix else ")"
            out[name] = _table_payload(name, label, ranges)
    return out


_SIMPLE_AI = re.compile(r"Table\s+\d+:\s*Simple AI (Outcomes|Targeting)")
_SIMPLE_AI_NAMES = {"Outcomes": "simple-ai-action", "Targeting": "simple-ai-target"}
_SIMPLE_ROW = re.compile(r"^(\d+)(?:-(\d+))?\s+(\S.*?)\s*$")


def _simple_ai_tables(raw: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        match = _SIMPLE_AI.search(line)
        if not match:
            continue
        slug = _SIMPLE_AI_NAMES[match.group(1)]
        ranges = []
        for row_line in lines[i + 2:]:
            row = _SIMPLE_ROW.match(row_line.strip())
            if not row:
                break
            low = int(row.group(1))
            ranges.append({"min": low, "max": int(row.group(2) or low), "result": row.group(3)})
        name = f"quickstart/{slug}"
        out[name] = _table_payload(name, f"Simple AI {match.group(1)}", ranges)
    return out


def import_flextale(
    pdf: Path, out_dir: Path, extract: Extractor, first_page: int = 23, last_page: int = 65
) -> ImportResult:
    layout = extract(pdf, "layout", first_page, last_page)
    payloads: dict[str, dict] = {}
    for table in _parse_layout(layout):
        payloads.update(_context_tables(table))
    payloads.update(_simple_ai_tables(extract(pdf, "raw", first_page, last_page)))

    result = ImportResult()
    for name, payload in payloads.items():
        path = out_dir / "tables" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        try:
            load_table(name, out_dir)
        except TableError as exc:
            path.unlink()
            result.skipped[name] = str(exc)
        else:
            result.written.append(name)
    return result


def default_output_dir(env: Mapping[str, str], home: Path) -> Path:
    base = Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else home / ".local" / "share"
    return base / "solo-rpg-toolkit" / "flextale"


def pdftotext_extract(pdf: Path, mode: str, first: int, last: int) -> str:
    """Runs poppler's `pdftotext` on pages `first` to `last`; `mode` is "layout" or "raw"."""
    if shutil.which("pdftotext") is None:
        raise FlextaleImportError("pdftotext not found; install poppler-utils")
    done = subprocess.run(
        ["pdftotext", f"-{mode}", "-f", str(first), "-l", str(last), str(pdf), "-"],
        capture_output=True, text=True,
    )
    if done.returncode != 0:
        raise FlextaleImportError(f"pdftotext failed: {done.stderr.strip()}")
    return done.stdout


def _check_outside_git(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    for folder in (resolved, *resolved.parents):
        if (folder / ".git").exists():
            raise FlextaleImportError(f"refusing to write inside a git work tree: {folder}")


def main(
    argv: list[str] | None = None,
    extract: Extractor = pdftotext_extract,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="solo-flextale-import",
        description="Write the FlexTale QuickStart tables from your PDF as solo-roll table JSON.",
    )
    parser.add_argument("pdf", type=Path, help="path to the FlexTale Solo Adventuring Toolkit PDF")
    parser.add_argument(
        "out", type=Path, nargs="?",
        help="output data folder (default: $XDG_DATA_HOME/solo-rpg-toolkit/flextale)",
    )
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    out_dir = args.out or default_output_dir(env, home)
    try:
        if not args.pdf.is_file():
            raise FlextaleImportError(f"PDF not found: {args.pdf}")
        _check_outside_git(out_dir)
        result = import_flextale(args.pdf, out_dir, extract)
    except FlextaleImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{len(result.written)} tables written to {out_dir}")
    for name, reason in result.skipped.items():
        print(f"skipped {name}: {reason}", file=sys.stderr)
    return 1 if result.skipped else 0


if __name__ == "__main__":
    sys.exit(main())
