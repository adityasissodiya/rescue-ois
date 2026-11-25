"""Anonymize and check the review export (called by artifact/export_review.sh).

  check_export.py anonymize --root DIR --aux paper/build/main-anon.aux --bib paper/refs.bib
      Writes DIR/paper/refs.bib with only the entries the review build cites (no comments),
      and withholds the Git commit in DIR/experiments/results/manifest.json (the dirty flag
      and the source digest stay; no clean commit is invented).

  check_export.py check --root DIR --tarball DIR.tar.gz
      Fails (exit 1) if the export contains a forbidden file, lacks a required one, if any
      text file or the PDF contains an identifying string, if the PDF metadata names an
      author, or if the tarball carries user names, real time stamps or other files.

Identifying strings are collected at run time from the Git identities of this
repository, the author and acknowledgment files of the paper, the user's home directory,
login name and the repository path. They are never written into the export.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GENERIC_IDENTITIES = {"claude", "github", "noreply@anthropic.com", "noreply@github.com"}
FORBIDDEN_NAMES = {
    "dict.local.json",
    "email.md",
    "Hostile Commander Methodology.md",
    "migration.md",
    "authors.tex",
    "authors_meta.tex",
    "acks.tex",
    "private_snapshot.sh",
    "review_diff.sh",
}
FORBIDDEN_DIRS = {".git", ".venv", ".tools", "graphify-out", "cache", "history", "ste"}
FORBIDDEN_SUFFIXES = {".bundle", ".pem", ".key"}
REQUIRED = [
    "LICENSE",
    "README.md",
    "Makefile",
    "paper/main-anon.pdf",
    "spec/protocol.md",
]


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""


def identifying_tokens() -> tuple[set[str], set[str]]:
    """(words matched as whole words, strings matched anywhere); all lower case."""
    words: set[str] = set()
    strings: set[str] = set()
    for line in _git("log", "--all", "--format=%an%n%ae%n%cn%n%ce").splitlines():
        v = line.strip()
        if not v or v.lower() in GENERIC_IDENTITIES:
            continue
        if "@" in v:
            strings.add(v.lower())
            strings.add(v.split("@")[0].lower())
        else:
            words.add(v.lower())
            words.update(w.lower() for w in v.split() if len(w) > 3)
    m = re.search(
        r"[:/]([^/:]+)/[^/]+?(?:\.git)?$", _git("remote", "get-url", "origin").strip()
    )
    if m:
        words.add(m.group(1).lower())
    words.add(REPO.name.lower())  # the repository's own name
    authors = (REPO / "paper" / "authors.tex").read_text(encoding="utf-8")
    names = re.search(r"\\IEEEauthorblockN\{([^}]*)\}", authors)
    if names:
        for full in re.split(r",|\band\b", names.group(1)):
            full = full.strip()
            if full:
                words.add(full.lower())
                words.add(full.split()[-1].lower())  # surname
    for local, domain in re.findall(r"\\\{([^}]*)\\\}@([\w.]+)", authors):
        strings.add(domain.lower())
        for name in local.split(","):
            strings.add(f"{name.strip()}@{domain}".lower())
    strings.update({"lule{\\aa}", "luleå", "lulea"})
    acks = (REPO / "paper" / "acks.tex").read_text(encoding="utf-8")
    strings.update(n.lower() for n in re.findall(r"\b\d{4}-\d{5}\b|\b\d{9}\b", acks))
    words.update(
        w.lower() for w in re.findall(r"\b[A-Z][A-Za-z]+-?[A-Z][A-Za-z]+\b", acks)
    )
    words.update({"vinnova", "indtech", "stambanan"})
    home = os.path.expanduser("~")
    strings.update({home.lower(), str(REPO).lower(), str(REPO.parent).lower()})
    user = getpass.getuser()
    if len(user) >= 3:
        words.add(user.lower())
    return {w for w in words if len(w) >= 3}, {s for s in strings if len(s) >= 4}


def find_tokens(text: str, words: set[str], strings: set[str]) -> list[str]:
    low = text.lower()
    hits = [s for s in strings if s in low]
    for w in words:
        if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low):
            hits.append(w)
    return sorted(set(hits))


def anonymize(root: Path, aux: Path, bib: Path) -> None:
    cited: set[str] = set()
    for keys in re.findall(r"\\citation\{([^}]*)\}", aux.read_text(encoding="utf-8")):
        cited.update(k.strip() for k in keys.split(","))
    text = bib.read_text(encoding="utf-8")
    entries = {}
    for m in re.finditer(r"^@\w+\{([^,\s]+),.*?^\}\s*$", text, re.M | re.S):
        entries[m.group(1)] = m.group(0)
    missing = sorted(cited - set(entries))
    if missing:
        sys.exit(f"anonymize: cited keys not in {bib}: {missing}")
    out = root / "paper" / "refs.bib"
    out.write_text(
        "% Only the entries cited by the review build.\n\n"
        + "\n\n".join(entries[k] for k in sorted(cited))
        + "\n",
        encoding="utf-8",
    )
    man = root / "experiments" / "results" / "manifest.json"
    data = json.loads(man.read_text(encoding="utf-8"))
    if data.get("git_head"):
        data["git_head"] = "withheld for anonymous review"
    data["export_note"] = (
        "Review export. The Git commit is withheld for anonymity. "
        "git_seed_sources_dirty and source_tree_sha256 are as recorded by the run."
    )
    man.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"anonymize: {len(cited)} bibliography entries kept; manifest commit withheld"
    )


def check(root: Path, tarball: Path | None) -> int:
    words, strings = identifying_tokens()
    problems: list[str] = []
    files = sorted(p for p in root.rglob("*") if p.is_file())
    rel = [p.relative_to(root) for p in files]
    for r in REQUIRED:
        if not (root / r).is_file():
            problems.append(f"missing required file {r}")
    for p in rel:
        if p.name in FORBIDDEN_NAMES or p.suffix in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden file {p}")
        if FORBIDDEN_DIRS & set(p.parts[:-1]):
            problems.append(f"forbidden directory in {p}")
        if p.suffix == ".pdf" and str(p) != "paper/main-anon.pdf":
            problems.append(f"unexpected PDF {p}")
    for path, r in zip(files, rel, strict=True):
        if path.suffix == ".pdf":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"binary file {r}")
            continue
        for hit in find_tokens(text, words, strings):
            problems.append(f"identifying string in {r}: {hit!r}")
    pdf = root / "paper" / "main-anon.pdf"
    if pdf.is_file():
        info = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
        ).stdout
        body = subprocess.run(
            ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
        ).stdout
        if len(body.split()) < 1000:
            problems.append("PDF text could not be extracted for the check")
        if re.search(r"^Author:[ \t]*\S", info, re.M):
            problems.append("PDF metadata names an author")
        raw = pdf.read_bytes()
        for key in (b"PTEX.FileName", b"PTEX.Fullbanner"):
            if key in raw:
                problems.append(f"PDF carries {key.decode()}")
        for hit in find_tokens(info + "\n" + body, words, strings):
            problems.append(f"identifying string in the PDF: {hit!r}")
        if re.search(r"^\s*acknowledge?ments?\s*$", body, re.I | re.M):
            problems.append("PDF has an acknowledgment section")
    if tarball is not None:
        with tarfile.open(tarball) as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            names = sorted(m.name for m in members)
            want = sorted(str(Path(root.name) / r) for r in rel)
            if names != want:
                problems.append("tarball files differ from the export directory")
            for m in tf.getmembers():
                if m.uname or m.gname or m.uid or m.gid or m.mtime:
                    problems.append(f"tarball member {m.name} carries owner or time")
                    break
    print(
        f"check: {len(files)} files, {len(words) + len(strings)} identifying strings "
        f"tested, {len(problems)} problem(s)"
    )
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("anonymize")
    a.add_argument("--root", type=Path, required=True)
    a.add_argument("--aux", type=Path, required=True)
    a.add_argument("--bib", type=Path, required=True)
    c = sub.add_parser("check")
    c.add_argument("--root", type=Path, required=True)
    c.add_argument("--tarball", type=Path)
    args = ap.parse_args()
    if args.cmd == "anonymize":
        anonymize(args.root, args.aux, args.bib)
        return 0
    return check(args.root, args.tarball)


if __name__ == "__main__":
    sys.exit(main())
