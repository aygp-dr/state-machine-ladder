"""Reference solution for challenge 07 (lr-parser-fsm) - an LR(0) automaton.

The control is a finite automaton (states 0..8, from the Graphviz gallery yacc
LR automaton), but the machine carries a STATE STACK: the current control state
is the stack top, and a legal shift pushes the target state. So the real state
is (control state, stack), a pushdown machine - not finite (spec: challenge 08
register-machine foreshadowing). The fold reads each parse's token log in
arrival order, drives the stack, and reports anomalies; its printed output is
the oracle.
"""
import csv
import os

# Transition table: (state, label) -> next state.
TRANS = {
    (0, "SS(B)"): 2, (0, "SS(S)"): 1,
    (1, "S($end)"): 3,
    (2, "SS(b)"): 6, (2, "SS(a)"): 5, (2, "S(A)"): 4,
    (5, "S(b)"): 7, (5, "S(a)"): 5,
    (6, "S(b)"): 6, (6, "S(a)"): 5,
    (7, "S(b)"): 8, (7, "S(a)"): 5,
    (8, "S(b)"): 6, (8, "S(a)"): 5,
}
ACCEPTING = {0, 3, 4, 8}
ALPHABET = {label for (_, label) in TRANS}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    """Per-parse (control state, stack), plus anomalies. Never drops silently."""
    stacks, anomalies = {}, []
    hi, seen = {}, set()
    for r in events:
        pid, label, ts = r["parse_id"], r["label"], r["ts"]
        stack = stacks.setdefault(pid, [0])
        if label not in ALPHABET:
            anomalies.append((pid, "unknown_label", label))
            continue
        key = (pid, label, ts)
        if key in seen:
            anomalies.append((pid, "dup", label))
            continue
        seen.add(key)
        if not ts:
            anomalies.append((pid, "null_ts", label))
        elif hi.get(pid) and ts < hi[pid][0]:
            anomalies.append((pid, "I6", f"{hi[pid][1]} before {label}"))
        elif ts:
            hi[pid] = (ts, label)
        state = stack[-1]
        nxt = TRANS.get((state, label))
        if nxt is None:
            anomalies.append((pid, "T2", f"{state}:{label}"))
            continue
        stack.append(nxt)
    return stacks, anomalies


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "parse_log.csv"))
    stacks, anomalies = fold(events)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== result ==")
    for pid, stack in sorted(stacks.items()):
        state = stack[-1]
        accept = "yes" if state in ACCEPTING else "no"
        joined = ",".join(str(s) for s in stack)
        lines.append(f"{pid} state={state} accept={accept} stack={joined}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
