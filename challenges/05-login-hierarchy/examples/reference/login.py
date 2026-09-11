"""Reference solution for challenge 05 (login-hierarchy) - a containment poset.

The containment hierarchy is a tree (a genuine poset): LogIn contains
{Main, Settings, Reports}; Reports contains {Report1, Report2}; LogOut is a
top-level leaf. The current state is always a leaf, and the projection is the
ancestor-closed set of active nodes - a down-set (order ideal) of the tree
(spec sec 2.3). So unlike the cycle cases the down-set/flag projection returns,
lifted from a chain to a tree. A cyclic navigation graph rides on top of the
tree, so we also check transition-legality. The fold reports anomalies.
"""
import csv
import os

# containment: each leaf mapped to its active node set, listed root-to-leaf
ANCESTORS = {
    "LogOut": ["LogOut"],
    "Main": ["LogIn", "Main"],
    "Settings": ["LogIn", "Settings"],
    "Report1": ["LogIn", "Reports", "Report1"],
    "Report2": ["LogIn", "Reports", "Report2"],
}
LEAVES = set(ANCESTORS)
# allowed leaf-to-leaf navigation (the statechart transitions)
LEGAL_NAV = {
    ("LogOut", "Main"),
    ("Main", "Settings"), ("Settings", "Main"),
    ("Main", "Report1"),
    ("Report1", "Report2"), ("Report2", "Report1"),
    ("Report1", "Main"), ("Report2", "Main"),
    ("Main", "LogOut"), ("Settings", "LogOut"),
    ("Report1", "LogOut"), ("Report2", "LogOut"),
}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    current, anomalies = {}, []
    prev, hi, seen = {}, {}, set()
    for r in events:
        sid, st, ts = r["session_id"], r["state"], r["ts"]
        if st not in LEAVES:
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
        if sid in prev and (prev[sid], st) not in LEGAL_NAV:
            anomalies.append((sid, "T2", f"{prev[sid]}->{st}"))
        prev[sid] = st
        current[sid] = st
    return current, anomalies


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "nav_log.csv"))
    current, anomalies = fold(events)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== current state ==")
    for sid, leaf in sorted(current.items()):
        active = ",".join(ANCESTORS[leaf])  # the ancestor-closed down-set, root-to-leaf
        lines.append(f"{sid} leaf={leaf} active={active}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
