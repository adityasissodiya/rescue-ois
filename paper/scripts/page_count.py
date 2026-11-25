"""Report the main-text page count of a built PDF and check its metadata.

Usage: python3 paper/scripts/page_count.py paper/build/main [--anonymous] [--limit 10]

The main text ends at the label `end-of-main-text` (after the conclusion, before the
acknowledgment, the references and the appendices). Exit status 1 if the main text is
longer than the limit, if the label is missing, or, with --anonymous, if the PDF metadata
names an author or carries pdfTeX file information.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", help="build path without extension, e.g. paper/build/main")
    ap.add_argument("--anonymous", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()
    aux, pdf = Path(args.base + ".aux"), Path(args.base + ".pdf")
    m = re.search(
        r"\\newlabel\{end-of-main-text\}\{\{[^}]*\}\{(\d+)\}",
        aux.read_text(encoding="utf-8", errors="replace"),
    )
    if not m:
        print(f"page_count: no end-of-main-text label in {aux}", file=sys.stderr)
        return 1
    main_pages = int(m.group(1))
    info = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
    ).stdout
    fields = dict(
        (k.strip(), v.strip())
        for k, v in (line.split(":", 1) for line in info.splitlines() if ":" in line)
    )
    total = int(fields["Pages"])
    print(
        f"{pdf}: main text {main_pages} pages (limit {args.limit}), "
        f"{total} pages in total including references and appendices"
    )
    ok = main_pages <= args.limit
    if not ok:
        print(f"page_count: main text exceeds {args.limit} pages", file=sys.stderr)
    if args.anonymous:
        author = fields.get("Author", "")
        raw = pdf.read_bytes()
        leaks = [k for k in (b"PTEX.FileName", b"PTEX.Fullbanner") if k in raw]
        if author or leaks:
            print(
                f"page_count: metadata leak: Author={author!r} {leaks}", file=sys.stderr
            )
            ok = False
        else:
            print(f"{pdf}: metadata has no author and no pdfTeX file information")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
