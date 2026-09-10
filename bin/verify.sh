#!/bin/sh
# verify.sh — ladder runner. For each challenge that ships a reference solution
# (an oracle + at least one example run.sh), run its own gate and aggregate.
# A challenge with no reference is reported OPEN, not FAIL — the point is for
# someone to implement it.
#
# Usage: bin/verify.sh [challenge-dir ...]   (default: all challenges/*)
set -u
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
if [ "$#" -gt 0 ]; then DIRS="$*"; else DIRS=$(find "$ROOT/challenges" -mindepth 1 -maxdepth 1 -type d | sort); fi

pass=0; fail=0; open=0; rc=0
for d in $DIRS; do
  name=$(basename "$d")
  if [ -f "$d/examples/oracle-contract.txt" ] && \
     [ -n "$(find "$d/examples" -mindepth 2 -name run.sh 2>/dev/null)" ] && \
     [ -x "$d/bin/verify.sh" ]; then
    if "$d/bin/verify.sh" >/dev/null 2>&1; then
      printf '%-28s PASS\n' "$name"; pass=$((pass+1))
    else
      printf '%-28s FAIL\n' "$name"; fail=$((fail+1)); rc=1
    fi
  else
    printf '%-28s OPEN (no reference yet)\n' "$name"; open=$((open+1))
  fi
done
echo "--------------------------------------------------"
echo "PASS=$pass FAIL=$fail OPEN=$open"
exit $rc
