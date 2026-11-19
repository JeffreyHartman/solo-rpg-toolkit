"""Dump a page range of a two-column PDF in reading order.

Lines are split into runs at gutter-sized gaps and runs are grouped into columns by
clustering their start positions, so text that shares a baseline across columns does
not bleed together.
"""
import argparse
import re
import subprocess
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/1999/xhtml}"
GUTTER = 15.0
COL_GAP = 25.0
LINE_GAP = 13.5


def repair_hyphenation(text):
    """Join "ac- tions" into "actions" without touching "1d6- 1" or "1- 3"."""
    return re.sub(r"([A-Za-z])- ([a-z])", r"\1\2", text)


ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("first", type=int)
ap.add_argument("last", type=int)
ap.add_argument("--marks", action="store_true", help="prefix each line with x and y")
ap.add_argument("--reflow", action="store_true",
                help="join hard-wrapped lines into paragraphs and repair hyphenation")
ap.add_argument("--single", action="store_true",
                help="one text column; sort by vertical position only")
ap.add_argument("--split", type=float, default=None,
                help="fixed column boundary; use on prose pages, where centered "
                     "headings would otherwise cluster into a column of their own")
args = ap.parse_args()

xml = subprocess.run(["pdftotext", "-bbox-layout", args.pdf, "-"],
                     capture_output=True, text=True, check=True).stdout
# Some PDFs emit a bare & or a control character inside a <word>, which is not
# well-formed XML.
xml = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", xml)
xml = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", xml)

for pno, page in enumerate(ET.fromstring(xml).iter(f"{NS}page"), start=1):
    if not args.first <= pno <= args.last:
        continue
    cells = []
    for line in page.iter(f"{NS}line"):
        words = [(float(w.get("xMin")), float(w.get("xMax")), w.text)
                 for w in line.iter(f"{NS}word") if w.text]
        if not words:
            continue
        y = float(line.get("yMin"))
        run = [words[0]]
        for w in words[1:]:
            if w[0] - run[-1][1] > GUTTER:
                cells.append((run[0][0], y, " ".join(t for _, _, t in run)))
                run = []
            run.append(w)
        cells.append((run[0][0], y, " ".join(t for _, _, t in run)))

    if args.single:
        def col(x):
            return 0
    elif args.split:
        def col(x):
            return 0 if x < args.split else 1
    else:
        lefts = []
        for x in sorted(c[0] for c in cells):
            if not lefts or x - lefts[-1] > COL_GAP:
                lefts.append(x)

        def col(x):
            return max(i for i, left in enumerate(lefts) if left <= x + 0.01)

    cells.sort(key=lambda c: (col(c[0]), c[1], c[0]))
    print(f"<<<PAGE {pno}>>>")
    if not args.reflow:
        for x, y, text in cells:
            print(f"[{x:6.1f} {y:6.1f}] {text}" if args.marks else text)
        continue

    out, cur, prev = [], [], None
    for x, y, text in cells:
        # A deeper indent continues a list item; a shallower one starts a block.
        if cur and (prev is None or y - prev > LINE_GAP or x < cur_x - 2.0):
            out.append(cur)
            cur = []
        if not cur:
            cur_x = x
        cur.append(text)
        prev = y
    if cur:
        out.append(cur)
    for para in out:
        joined = " ".join(para)
        joined = repair_hyphenation(joined)
        print(joined)
        print()
