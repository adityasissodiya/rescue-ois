#!/usr/bin/env bash
# Build the review export of the SRDS seed from an ALLOWLIST, anonymize it, and check it.
#
#   artifact/out/review/        the exported tree
#   artifact/out/review.tar.gz  the same tree as a reproducible tarball (no user names,
#                               fixed time stamps)
#
# Never exported: Git history, email drafts and methodology notes, the seed prompt,
# private snapshots, downloaded third-party papers (research/cache/), graph caches
# (graphify-out/), the locally excluded STE dictionary (paper/ste/dict.local.json),
# author and acknowledgment files, the historical drafts and the legacy prototype.
# Run through `make export`, which first builds paper/build/main-anon.pdf.
# The exit status is nonzero on any failure, including a failed anonymity check.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"
out="artifact/out"
dest="$out/review"
pdf="paper/build/main-anon.pdf"
aux="paper/build/main-anon.aux"
[[ -f "$pdf" && -f "$aux" ]] || { echo "export: build $pdf first (make paper-anon)" >&2; exit 2; }

rm -rf "$dest" "$out/review.tar.gz"
mkdir -p "$dest"

# The allowlist: directories are copied with their files, minus caches.
allow=(
  LICENSE
  ruff-seed.toml
  requirements/seed.in
  requirements/seed.lock
  spec/protocol.md
  spec/tla/MandateSeed.tla
  spec/tla/MandateSeed.cfg
  spec/tla/MandateSeed_handover.cfg
  spec/tla/MandateSeed_stall.cfg
  spec/tla/MandateSeed_broken.cfg
  spec/tla/README.md
  spec/tla/run_tlc.sh
  spec/tla/summarize.py
  spec/tla/logs
  src/mandate
  sim
  experiments
  tests
  research/positioning.md
  research/claims.csv
  research/roadmap.md
  paper/main.tex
  paper/main-anon.tex
  paper/sections
  paper/generated
  paper/scripts/page_count.py
)
for p in "${allow[@]}"; do
  [[ -e "$p" ]] || { echo "export: allowlisted path $p is missing" >&2; exit 1; }
  mkdir -p "$dest/$(dirname "$p")"
  cp -R "$p" "$dest/$(dirname "$p")/"
done
find "$dest" \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -prune \
  -exec rm -rf {} +
find "$dest" -name '*.pyc' -delete

# Files written for the export.
cp artifact/README.md "$dest/README.md"
cp artifact/export.mk "$dest/Makefile"
cp "$pdf" "$dest/paper/main-anon.pdf"
.venv/bin/python artifact/check_export.py anonymize --root "$dest" --aux "$aux" \
  --bib paper/refs.bib

# A reproducible tarball: sorted names, numeric owner 0, fixed modification time.
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='@0' --format=gnu \
  -C "$out" -cf - review | gzip -n > "$out/review.tar.gz"

.venv/bin/python artifact/check_export.py check --root "$dest" --tarball "$out/review.tar.gz"
echo "export: $dest and $out/review.tar.gz ($(find "$dest" -type f | wc -l) files)"
