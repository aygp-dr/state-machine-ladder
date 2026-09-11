"""Reference solution for challenge 04 (lamp-two-switch) - a reversible graph.

State = (wall, lamp) in {off,on}^2: BothOff, WallOff (wall off, lamp on),
LampOff (wall on, lamp off), On (both on). A legal toggle flips exactly one
switch, so the state graph is the hypercube Q2: strongly connected and
reversible, NOT a poset (spec sec 2.2). Illegal steps change two coordinates
(BothOff<->On, WallOff<->LampOff). The view is the current state plus
transition-legality; the fold reports anomalies and prints the oracle.
"""
import csv
import os

# coordinate encoding (wall, lamp); a legal step differs in exactly one coord
COORD = {"BothOff": (0, 0), "WallOff": (0, 1), "LampOff": (1, 0), "On": (1, 1)}
STATES = set(COORD)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def legal(a, b):
    (aw, al), (bw, bl) = COORD[a], COORD[b]
    return (aw != bw) + (al != bl) == 1


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    current, anomalies = {}, []
    prev, hi, seen = {}, {}, set()
    for r in events:
        lid, st, ts = r["lamp_id"], r["state"], r["ts"]
        if st not in STATES:
            anomalies.append((lid, "unknown_state", st))
            continue
        key = (lid, st, ts)
        if key in seen:
            anomalies.append((lid, "dup", st))
            continue
        seen.add(key)
        if not ts:
            anomalies.append((lid, "null_ts", st))
        elif hi.get(lid) and ts < hi[lid][0]:
            anomalies.append((lid, "I6", f"{hi[lid][1]} before {st}"))
        elif ts:
            hi[lid] = (ts, st)
        if lid in prev and not legal(prev[lid], st):
            anomalies.append((lid, "T2", f"{prev[lid]}->{st}"))
        prev[lid] = st
        current[lid] = st
    return current, anomalies


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "lamp_log.csv"))
    current, anomalies = fold(events)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== current state ==")
    lines += [f"{lid} {st}" for lid, st in sorted(current.items())]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
