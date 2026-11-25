#!/usr/bin/env bash
# Make a private, restorable snapshot of this working tree, outside the repository.
#
# The snapshot has four parts:
#   history.bundle   every ref and commit (git bundle create --all)
#   worktree.tar.gz  every file of the working tree except .git and the caches listed
#                    below: tracked, modified, untracked AND ignored files (for example
#                    the private STE word list and the LaTeX build output)
#   MANIFEST.sha256  sha256 of every file inside worktree.tar.gz
#   CHECKSUMS.sha256 sha256 of the bundle, the tarball and the manifest
# plus STATE.txt (HEAD, branch, remotes, git status, exclusions), git-info-exclude (a copy
# of .git/info/exclude, which a bundle does not carry) and RESTORE.md.
#
# The snapshot can hold private material (internal email drafts, the ASD-derived word
# list). Keep the destination private; never put it in a review export.
#
# Usage: artifact/private_snapshot.sh <destination-directory>
# The destination must not exist yet. Exit status is nonzero on any failure,
# including a failed self-check (extract + compare against the working tree).
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <destination-directory>" >&2
  exit 2
fi
repo="$(git rev-parse --show-toplevel)"
dest="$1"
if [[ -e "$dest" ]]; then
  echo "refusing to overwrite existing $dest" >&2
  exit 2
fi
mkdir -p "$dest"
dest="$(cd "$dest" && pwd)"
case "$dest/" in
  "$repo"/*) echo "destination must be outside the repository" >&2; rm -rf "$dest"; exit 2 ;;
esac

cd "$repo"
# Caches that are regenerable and are left out on purpose. Recorded in STATE.txt.
excludes=(--exclude=./.git --exclude=./graphify-out/cache --exclude='__pycache__'
          --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.ruff_cache'
          --exclude='.venv' --exclude='.hypothesis')

{
  echo "snapshot_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repository: $repo"
  echo "head: $(git rev-parse HEAD)"
  echo "branch: $(git rev-parse --abbrev-ref HEAD)"
  echo "core.fileMode: $(git config core.fileMode || echo unset)"
  echo "remotes:"; git remote -v | sed 's/^/  /' 
  echo
  echo "## git status --porcelain=v1 --ignored -uall (graphify-out/cache collapsed)"
  git status --porcelain=v1 --ignored -uall | { grep -v '^?? graphify-out/cache/' || [[ $? -eq 1 ]]; }
  echo "?? graphify-out/cache/... ($(find graphify-out/cache -type f 2>/dev/null | wc -l) files, excluded below)"
  echo
  echo "## mode changes against HEAD (empty means none)"
  git diff --summary | { grep -E 'mode change' || [[ $? -eq 1 ]]; }
  echo
  echo "## excluded from worktree.tar.gz (regenerable caches)"
  for p in graphify-out/cache; do
    [[ -e "$p" ]] && echo "$p: $(find "$p" -type f | wc -l) files, $(du -sh "$p" | cut -f1)"
  done
  find . -path ./.git -prune -o \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \
       -o -name .venv -o -name .hypothesis \) -print | sed 's|^\./||'
} > "$dest/STATE.txt"

cp "$repo/.git/info/exclude" "$dest/git-info-exclude"
git bundle create "$dest/history.bundle" --all 2>/dev/null
git bundle verify "$dest/history.bundle" >/dev/null 2>&1

tar --sort=name "${excludes[@]}" -czf "$dest/worktree.tar.gz" .

# Manifest of the files inside the tarball, from an independent extraction.
check="$(mktemp -d)"
trap 'rm -rf "$check"' EXIT
tar -xzf "$dest/worktree.tar.gz" -C "$check"
(cd "$check" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$dest/MANIFEST.sha256"

# Self-check: the extracted tree equals the working tree, apart from the exclusions.
if ! diff -r -q --no-dereference -x .git -x __pycache__ -x '*.pyc' -x .pytest_cache \
     -x .ruff_cache -x .venv -x .hypothesis -x cache "$repo" "$check" >/dev/null; then
  # 'cache' is excluded by name only for graphify-out/cache; show any real difference.
  diff -r -q --no-dereference -x .git -x __pycache__ -x '*.pyc' -x .pytest_cache \
     -x .ruff_cache -x .venv -x .hypothesis -x cache "$repo" "$check" >&2 || [[ $? -eq 1 ]]
  echo "self-check FAILED: extracted snapshot differs from the working tree" >&2
  exit 1
fi
if [[ -d "$repo/graphify-out/cache" ]] && [[ -e "$check/graphify-out/cache" ]]; then
  echo "self-check FAILED: graphify-out/cache was not excluded" >&2
  exit 1
fi

# Full restore test: the documented procedure must reproduce git status and git diff.
head="$(git rev-parse HEAD)"
rt="$check/restore-test"
git clone -q --no-checkout "$dest/history.bundle" "$rt"
git -C "$rt" reset -q "$head"
cp "$dest/git-info-exclude" "$rt/.git/info/exclude"
tar -xzf "$dest/worktree.tar.gz" -C "$rt"
(cd "$rt" && sha256sum -c --quiet "$dest/MANIFEST.sha256")
st_live="$(git status --porcelain=v1 --ignored -uall | grep -v ' graphify-out/cache/' | sort)"
st_rest="$(git -C "$rt" status --porcelain=v1 --ignored -uall | grep -v ' graphify-out/cache/' \
           | grep -v '__pycache__' | sort)"
st_live="$(printf '%s\n' "$st_live" | grep -v '__pycache__')"
if [[ "$st_live" != "$st_rest" ]]; then
  diff <(printf '%s\n' "$st_live") <(printf '%s\n' "$st_rest") >&2 || [[ $? -eq 1 ]]
  echo "self-check FAILED: restored git status differs" >&2
  exit 1
fi
if [[ "$(git diff | sha256sum)" != "$(git -C "$rt" diff | sha256sum)" ]]; then
  echo "self-check FAILED: restored git diff differs" >&2
  exit 1
fi
echo "restore test: git status and git diff identical"

(cd "$dest" && sha256sum history.bundle worktree.tar.gz MANIFEST.sha256 STATE.txt \
   git-info-exclude > CHECKSUMS.sha256)

cat > "$dest/RESTORE.md" <<EOF
# Restoring this snapshot

1. Verify: \`cd <this directory> && sha256sum -c CHECKSUMS.sha256\`
2. History without a checkout (a checkout would bring back files that were deleted in
   the working tree): \`git clone --no-checkout history.bundle restored && cd restored\`
   then \`git reset -q $(git rev-parse HEAD)\` (sets the index only;
   \`git bundle list-heads history.bundle\` lists every ref in the bundle)
3. Local excludes (keeps the ASD word list out of commits):
   \`cp ../git-info-exclude .git/info/exclude\`
4. Working tree, including uncommitted, untracked and ignored files:
   \`tar -xzf ../worktree.tar.gz -C .\`
5. Check: \`sha256sum -c ../MANIFEST.sha256\` (all lines OK). \`git status\` now shows the
   same modified, deleted and untracked files as at snapshot time (STATE.txt).
6. The clone's origin is the bundle. STATE.txt records the original remotes.

Excluded caches are listed in STATE.txt; they are regenerable.
Private material inside: email drafts, methodology notes, paper/ste/dict.local.json
(ASD-derived; do not publish). Keep this directory private.
EOF
echo "snapshot written to $dest"
cat "$dest/CHECKSUMS.sha256"
