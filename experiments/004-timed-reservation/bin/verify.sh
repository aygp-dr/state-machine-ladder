#!/bin/sh
# Experiment 004 gate. Self-contained; NOT wired into the ladder's root gate.
#   1. the challenge gate: the reference fold reproduces the pinned oracle;
#   2. spec/code agreement: every canonical table row the fold is built from
#      (reservation.py --tables) appears verbatim in proposed-spec-2.9.org;
#   3. verify the verifier: each mutant of the trace must make gate 1 FAIL.
# Zero findings, no warning tier. Exit 0 iff all three hold.
#
# Usage: experiments/004-timed-reservation/bin/verify.sh
set -u
EXP=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
CH="$EXP/challenge"
SPEC="$EXP/proposed-spec-2.9.org"
rc=0

echo "== 1. challenge gate =="
"$CH/bin/verify.sh" || rc=1

echo "== 2. spec/code table agreement =="
missing=$("$CH/examples/reference/run.sh" --tables | grep -v -e '^$' -e '^|-' |
  while IFS= read -r line; do grep -qxF -- "$line" "$SPEC" || echo "$line"; done)
if [ -z "$missing" ]; then
  echo "tables           PASS"
else
  echo "tables           FAIL (rows missing from $SPEC):"; printf '    %s\n' "$missing"; rc=1
fi

echo "== 3. negative test: every mutant must be killed =="
TMP=$(mktemp -d "${TMPDIR:-/tmp}/tr004.XXXXXX") || exit 2
trap 'rm -rf "$TMP"' EXIT INT TERM
# mutant <name> <sed-expression>: copy the challenge, mutate its trace, run its gate
mutant() {
  rm -rf "$TMP/c" && cp -R "$CH" "$TMP/c"
  f="$TMP/c/data/trace/reservation_log.csv"
  sed "$2" "$f" > "$f.new" && mv "$f.new" "$f"
  if cmp -s "$f" "$CH/data/trace/reservation_log.csv"; then
    printf '%-26s INVALID (mutation did not apply)\n' "$1"; rc=1; return
  fi
  if "$TMP/c/bin/verify.sh" >/dev/null 2>&1; then
    printf '%-26s SURVIVED (gate passed a wrong log)\n' "$1"; rc=1
  else
    printf '%-26s killed\n' "$1"
  fi
}
mutant drop-scheduler-expire  '/,RES-10,expire,scheduler,/d'
mutant flip-fencing-token     's/^\(2026-09-11T11:31:30Z,R2,RES-04,check_in,party,,,,\)3$/\12/'
mutant drop-compensation      '/,RES-06,reassign,operator,/d'
mutant forge-no-show-by-party 's/,RES-11,no_show,scheduler,/,RES-11,no_show,party,/'
mutant drop-late-binding      's/^\(2026-09-11T10:31:00Z,\)R2\(,RES-03,check_in,\)/\1R1\2/'

echo "== 4. purity: the fold takes no clock argument =="
if grep -nE 'datetime\.now|utcnow|time\.time|date\.today|^import time|^from time ' \
     "$CH/examples/reference/reservation.py"; then
  echo "purity           FAIL (the fold reads a clock)"; rc=1
else
  echo "purity           PASS"
fi

echo "------------------------------------"
[ "$rc" -eq 0 ] && echo "EXPERIMENT 004 PASS" || echo "EXPERIMENT 004 FAIL"
exit $rc
