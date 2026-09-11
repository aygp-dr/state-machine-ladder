"""Reference solution for challenge 08 (register-machine controller).

SICP sec 5.1: a controller is a sequence of labelled instruction points over a
datapath of registers. The controller is a finite state machine; the datapath
(registers, arithmetic, a stack) makes the whole thing Turing-powerful.

Here we model the machine's EXECUTION TRACE as the log and fold it. Each run
is one controller execution. The fold checks control-flow legality (jumps land
on declared labels, branches only follow a test, nothing runs past halt) and
projects the final register file plus whether the machine halted.

Ops (arg format in parentheses):
  label  (arg=<name>)                  declares a control label
  assign (arg=<reg>=<int>)             write an integer to a register
  test   (arg=<cond>=<true|false>)     record a test outcome
  branch (arg=<label>)                 conditional jump; only after a test
  goto   (arg=<label>)                 unconditional jump
  halt   (arg empty)                   machine stops

The printed output is the oracle: an anomalies section and a final-state
section. The fold reports; it never drops silently without saying so.
"""
import csv
import os

OPS = {"label", "assign", "test", "branch", "goto", "halt"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def collect_labels(events):
    """First pass: every declared label, grouped by run."""
    labels = {}
    for r in events:
        if r["op"] == "label":
            labels.setdefault(r["run_id"], set()).add(r["arg"])
    return labels


def fold(events, labels):
    """Per run: final register file + halted flag, plus anomalies.

    Second pass over events in arrival order. Registers come from assign ops;
    a run halts when a halt op is applied. Control-flow legality is checked
    against the labels gathered in the first pass.
    """
    regs = {}       # run_id -> {reg: int}
    halted = {}     # run_id -> bool
    anomalies = []
    prev_op = {}    # run_id -> last applied op (for E-branch)
    hi = {}         # run_id -> highest ts seen
    seen = set()    # exact (run_id, op, arg, ts) tuples

    for r in events:
        rid, op, arg, ts = r["run_id"], r["op"], r["arg"], r["ts"]
        regs.setdefault(rid, {})
        halted.setdefault(rid, False)

        if op not in OPS:
            anomalies.append((rid, "unknown_op", op))
            continue

        key = (rid, op, arg, ts)
        if key in seen:
            anomalies.append((rid, "dup", f"{op}:{arg}"))
            continue
        seen.add(key)

        if halted[rid]:
            anomalies.append((rid, "E-halted", op))
            continue

        if not ts:
            anomalies.append((rid, "null_ts", op))
        elif hi.get(rid) and ts < hi[rid]:
            anomalies.append((rid, "I6", f"{op}:{arg}"))
        elif ts:
            hi[rid] = ts

        if op == "goto":
            if arg not in labels.get(rid, set()):
                anomalies.append((rid, "E-jump", arg))
        elif op == "branch":
            if prev_op.get(rid) != "test":
                anomalies.append((rid, "E-branch", ""))
            if arg not in labels.get(rid, set()):
                anomalies.append((rid, "E-jump", arg))
        elif op == "assign":
            reg, _, val = arg.partition("=")
            regs[rid][reg] = int(val)
        elif op == "halt":
            halted[rid] = True

        prev_op[rid] = op

    return regs, halted, anomalies


def fmt_regs(rf):
    if not rf:
        return "-"
    return ",".join(f"{k}={rf[k]}" for k in sorted(rf))


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "rm_log.csv"))
    labels = collect_labels(events)
    regs, halted, anomalies = fold(events, labels)

    lines = ["== anomalies =="]
    lines += [" ".join(x for x in v if x != "") for v in sorted(anomalies)]
    lines.append("== final state ==")
    for rid in sorted(regs):
        h = "yes" if halted[rid] else "no"
        lines.append(f"{rid} regs={fmt_regs(regs[rid])} halted={h}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
