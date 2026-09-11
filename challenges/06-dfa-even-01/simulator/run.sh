#!/bin/sh
# Generate a corpus with the core.logic relation, then differentially eval the
# reference against it. Green = the reference agrees with the relation on every
# generated (valid and adversarial) word.
set -eu
D=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
clojure -M "$D/gen.clj" > "$D/.words.txt" 2>/dev/null
python3 "$D/eval.py" "$D/.words.txt"
rm -f "$D/.words.txt"
