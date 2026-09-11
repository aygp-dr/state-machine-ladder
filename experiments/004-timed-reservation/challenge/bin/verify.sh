#!/bin/sh
# verify-the-verifier: run every examples/<tag>-<lang>/run.sh and diff its
# stdout against the canonical oracle contract. Zero findings = no warning tier;
# a gate is a tripwire, not a promotion mechanism (.meta/methodology.org).
#
# Usage:  bin/verify.sh [example-dir ...]
#         bin/verify.sh                 # all examples with a run.sh
#         bin/verify.sh examples/ot-haskell
set -u

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
CONTRACT="$ROOT/examples/oracle-contract.txt"
[ -f "$CONTRACT" ] || { echo "FATAL: missing $CONTRACT" >&2; exit 2; }

if [ "$#" -gt 0 ]; then
  DIRS="$*"
else
  DIRS=$(find "$ROOT/examples" -mindepth 2 -name run.sh -exec dirname {} \; | sort)
fi

pass=0; fail=0; rc=0
for d in $DIRS; do
  name=$(basename "$d")
  if [ ! -x "$d/run.sh" ]; then
    printf '%-16s SKIP (no run.sh)\n' "$name"; continue
  fi
  out=$("$d/run.sh" 2>"$d/.stderr")
  if [ "$out" = "$(cat "$CONTRACT")" ]; then
    printf '%-16s PASS\n' "$name"; pass=$((pass+1))
  else
    printf '%-16s FAIL\n' "$name"; fail=$((fail+1)); rc=1
    echo "--- diff (expected < / got >) ---"
    printf '%s\n' "$out" | diff "$CONTRACT" - | sed 's/^/    /'
    [ -s "$d/.stderr" ] && { echo "--- stderr ---"; sed 's/^/    /' "$d/.stderr"; }
  fi
  rm -f "$d/.stderr"
done

echo "------------------------------------"
echo "PASS=$pass FAIL=$fail"
exit $rc
