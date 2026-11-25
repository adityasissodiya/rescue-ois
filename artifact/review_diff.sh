#!/usr/bin/env bash
# Show every change of the SRDS seed pass against the private baseline ref
# refs/snapshots/pre-seed-2026-11-24: HEAD 3ebd585 plus the uncommitted working tree as it
# was before the pass, including untracked paper files. New untracked files are included;
# ignored files (for example paper/ste/dict.local.json) are not. The ref leaves out, by
# design, graphify-out/, email.md, the methodology notes and the task prompt; they are
# left out here too (the full private snapshot holds them, unchanged by the pass).
# The real index, HEAD and the working tree are not touched: the comparison uses a
# temporary index file.
#
# Usage: artifact/review_diff.sh                 # summary (--stat)
#        artifact/review_diff.sh --name-status    # one line per file
#        artifact/review_diff.sh -- paper/        # full diff of one path
#        artifact/review_diff.sh -p               # full diff of everything
set -euo pipefail

base="refs/snapshots/pre-seed-2026-11-24"
cd "$(git rev-parse --show-toplevel)"
git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
  || { echo "review_diff: $base not found (see research/migration.md)" >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export GIT_INDEX_FILE="$tmp/index"
git read-tree "$base"
git add -A -- . ':(exclude)graphify-out' ':(exclude)email.md' \
  ':(exclude)Hostile Commander Methodology.md' \
  ':(exclude)Claude_Code_SRDS_2027_Seed_Paper_Prompt.md'
if [[ $# -eq 0 ]]; then
  set -- --stat=120
fi
git diff --cached "$base" "$@"
