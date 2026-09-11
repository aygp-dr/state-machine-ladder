"""Reference solution for challenge 02 (traffic-light) - a cyclic FSM.

Structure S is the 3-cycle red -> green -> yellow -> red, which is NOT a poset,
so there is no sound wide-flag projection (spec sec 2.2). The view is the
current state plus a transition-legality check. The fold reads each signal's
log in arrival order and reports anomalies; its printed output is the oracle.
"""
import csv
import os

STATES = ["red", "green", "yellow"]
LEGAL = {("red", "green"), ("green", "yellow"), ("yellow", "red")}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    """current state per signal, plus anomalies. Reports; never drops silently."""
    current, anomalies = {}, []
    prev, hi, seen = {}, {}, set()
    for r in events:
        sid, st, ts = r["signal_id"], r["state"], r["ts"]
        if st not in STATES:
            anomalies.append((sid, "unknown_state", st))
            continue
        key = (sid, st, ts)
        if key in seen:
            anomalies.append((sid, "dup", st))
            continue
        seen.add(key)
        if not ts:
            anomalies.append((sid, "null_ts", st))
        elif hi.get(sid) and ts < hi[sid][0]:
            anomalies.append((sid, "I6", f"{hi[sid][1]} before {st}"))
        elif ts:
            hi[sid] = (ts, st)
        if sid in prev and (prev[sid], st) not in LEGAL:
            anomalies.append((sid, "T2", f"{prev[sid]}->{st}"))
        prev[sid] = st
        current[sid] = st
    return current, anomalies


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "signal_log.csv"))
    current, anomalies = fold(events)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== current state ==")
    lines += [f"{sid} {st}" for sid, st in sorted(current.items())]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
