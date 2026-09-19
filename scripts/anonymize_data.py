#!/usr/bin/env python3
"""Scrub machine-identifying detail from JSONL evaluation artifacts.

For every input file, write a sibling `*.anon.jsonl` with:
- every nested `environment` block stripped of host_uname, host_cpu_model,
  host_mem_total_kb -- these name the author's workstation and contribute
  nothing a reader can act on;
- every string value with the local repo prefix replaced by a repo-relative path.

Keeps docker_compose_version, docker_server_version, host_cpu_count,
timestamp_iso, and `git_commit`.

`git_commit` was previously rewritten to REDACTED-FOR-DOUBLE-BLIND. WONS 2027 is
not double-blind, so that redaction bought no anonymity and cost the one thing
the artifact most needs: the tie from each published number back to the tree that
produced it. It is the traceability the paper's reproducibility section claims.
Do not reinstate it without a venue that actually requires it.

Usage:
    python3 paper/scripts/anonymize_data.py paper/data/*.jsonl

Run from the repo root. Output: `<input>.anon.jsonl` next to each input.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_PATH_PATTERNS = [
    re.compile(r"/media/[^/]+/[^/]+/rescue-ois/"),
    re.compile(r"/home/[^/]+/[^/]+/rescue-ois/"),
    re.compile(r"/home/[^/]+/rescue-ois/"),
]

ENV_DROP_KEYS = {"host_uname", "host_cpu_model", "host_mem_total_kb"}


def scrub_path_string(value: str) -> str:
    out = value
    for pat in REPO_PATH_PATTERNS:
        out = pat.sub("", out)
    return out


def scrub_environment(env: dict) -> dict:
    result = {}
    for k, v in env.items():
        if k in ENV_DROP_KEYS:
            continue
        if isinstance(v, str):
            result[k] = scrub_path_string(v)
        else:
            result[k] = walk(v)
    return result


def walk(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "environment" and isinstance(v, dict):
                out[k] = scrub_environment(v)
            elif isinstance(v, (dict, list)):
                out[k] = walk(v)
            elif isinstance(v, str):
                out[k] = scrub_path_string(v)
            else:
                out[k] = v
        return out
    if isinstance(node, list):
        return [walk(item) for item in node]
    if isinstance(node, str):
        return scrub_path_string(node)
    return node


def anonymize_file(src: Path) -> Path:
    if src.name.endswith(".anon.jsonl"):
        return src
    dst = src.with_suffix(".anon.jsonl") if src.suffix == ".jsonl" else src.with_name(
        src.name + ".anon"
    )
    if src.name.endswith(".audit.jsonl"):
        dst = src.with_name(src.name.replace(".audit.jsonl", ".audit.anon.jsonl"))
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.rstrip("\n")
            if not line:
                fout.write("\n")
                continue
            record = json.loads(line)
            fout.write(json.dumps(walk(record), separators=(", ", ": ")))
            fout.write("\n")
    return dst


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: anonymize_data.py FILE [FILE ...]", file=sys.stderr)
        return 2
    for arg in argv[1:]:
        src = Path(arg)
        if not src.is_file():
            print(f"skip: {src} not a file", file=sys.stderr)
            continue
        dst = anonymize_file(src)
        print(f"{src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
