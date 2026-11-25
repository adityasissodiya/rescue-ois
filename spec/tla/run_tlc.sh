#!/usr/bin/env bash
# Run the bounded TLA+ model of seed-v0 (MandateSeed.tla) and check that every
# configuration gives its EXPECTED outcome:
#
#   MandateSeed.cfg           safety invariants hold            -> "No error has been found"
#   MandateSeed_handover.cfg  a handover is reachable           -> NoHandover is violated
#   MandateSeed_stall.cfg     the split-vote stall is reachable -> NoSplitStall is violated
#   MandateSeed_broken.cfg    O2 without its start guard        -> EpochOrder is violated
#
# Logs go to spec/tla/logs/<config>.log with absolute paths replaced by <repo>.
# The exit status is nonzero if a tool is missing, the jar does not match its pinned
# SHA-256, or any configuration gives a different outcome.
#
# Usage: spec/tla/run_tlc.sh [config.cfg ...]    (default: all four; the safety run
#        takes about 9 minutes with 4 workers). TLC_WORKERS sets the worker count.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
jar="$root/.tools/tla2tools-v1.7.4.jar"
jar_sha256="936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"

command -v java >/dev/null || { echo "run_tlc: java not found" >&2; exit 2; }
[[ -f "$jar" ]] || { echo "run_tlc: $jar missing; run 'make tla-tools'" >&2; exit 2; }
echo "$jar_sha256  $jar" | sha256sum --check --quiet - \
  || { echo "run_tlc: $jar does not match the pinned SHA-256" >&2; exit 2; }

declare -A expected=(
  [MandateSeed.cfg]="no-error"
  [MandateSeed_handover.cfg]="NoHandover"
  [MandateSeed_stall.cfg]="NoSplitStall"
  [MandateSeed_broken.cfg]="EpochOrder"
)
configs=("$@")
if [[ ${#configs[@]} -eq 0 ]]; then
  configs=(MandateSeed_handover.cfg MandateSeed_stall.cfg MandateSeed_broken.cfg MandateSeed.cfg)
fi

mkdir -p "$here/logs"
failures=0
for cfg in "${configs[@]}"; do
  want="${expected[$cfg]:-}"
  [[ -n "$want" ]] || { echo "run_tlc: unknown configuration $cfg" >&2; exit 2; }
  log="$here/logs/${cfg%.cfg}.log"
  meta="$(mktemp -d)"
  raw="$meta/tlc.out"
  echo "== $cfg (expected: $want)"
  set +e
  (cd "$here" && java -XX:+UseParallelGC -cp "$jar" tlc2.TLC \
     -workers "${TLC_WORKERS:-4}" -metadir "$meta/states" \
     -config "$cfg" MandateSeed.tla) > "$raw" 2>&1
  rc=$?
  set -e
  {
    echo "# configuration: $cfg"
    echo "# expected outcome: $want"
    echo "# tla2tools.jar sha256: $jar_sha256"
    echo "# java: $(java -version 2>&1 | head -n 1)"
    echo "# TLC exit status: $rc"
    python3 -I -c 'import sys
root, home, src = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(src, encoding="utf-8", errors="replace").read()
sys.stdout.write(text.replace(root, "<repo>").replace(home, "<home>"))' \
      "$root" "$HOME" "$raw"
  } > "$log"
  rm -rf "$meta"

  if [[ "$want" == "no-error" ]]; then
    if [[ $rc -eq 0 ]] && grep -q "Model checking completed. No error has been found." "$log"; then
      echo "   ok: no violation within the bounds ($(grep -o '[0-9,]* distinct states found' "$log" | tail -n 1))"
    else
      echo "   UNEXPECTED: exit $rc; see $log" >&2
      failures=$((failures + 1))
    fi
  else
    if [[ $rc -ne 0 ]] && grep -q "Invariant $want is violated" "$log"; then
      echo "   ok: $want is violated, as expected ($(grep -c '^State [0-9]*:' "$log") states in the trace)"
    else
      echo "   UNEXPECTED: exit $rc and no violation of $want; see $log" >&2
      failures=$((failures + 1))
    fi
  fi
done

if [[ $failures -ne 0 ]]; then
  echo "run_tlc: $failures configuration(s) gave an unexpected outcome" >&2
  exit 1
fi
echo "run_tlc: all ${#configs[@]} configuration(s) gave their expected outcome"
