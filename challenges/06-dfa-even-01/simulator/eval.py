#!/usr/bin/env python3
"""Differential eval: the core.logic relation (gen.clj) is an independent oracle
for the reference. For each generated word, fold it through the reference's own
transition function and check the accept/reject verdict matches the relation's.
Usage: eval.py <words-file>  (lines: "accept <word>" / "reject <word>")
"""
import importlib.util
import os
import sys

REF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples", "reference", "dfa.py"))
spec = importlib.util.spec_from_file_location("dfa", REF)
dfa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dfa)


def accepts(word):
    st = dfa.START
    for ch in word:
        st = dfa.step(st, ch)
    return st == dfa.ACCEPT


def main(path):
    ok = bad = 0
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            label, word = (line.split() + [""])[:2]
            expected = label == "accept"
            got = accepts(word)
            if got == expected:
                ok += 1
            else:
                bad += 1
                print(f"MISMATCH word={word!r} relation={label} reference={'accept' if got else 'reject'}")
    print(f"eval: {ok} agree, {bad} mismatch")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
