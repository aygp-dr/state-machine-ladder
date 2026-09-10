"""DD reference for the order-lifecycle instance (stamped by bin/new-exercise).

Same pattern as the picker reference, re-parameterized to the order chain
placed < paid < shipped < delivered. Its printed output is this instance's
oracle contract. Demonstrates spec.org: only STRUCTURE S and the names change;
the invariant logic, the schema-gate-before-state-gate order, the arrival-order
I6, and the sorted (id, inv, detail) output are all problem-independent.
"""
import csv
import os
from collections import OrderedDict

STATES = ["placed", "paid", "shipped", "delivered"]
PRED = {s: STATES[i - 1] if i else None for i, s in enumerate(STATES)}
DOMAIN = {"1", ""}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def path(*p):
    return os.path.join(ROOT, *p)


def read_trace(p):
    with open(p) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    seen, anomalies = OrderedDict(), []
    for r in events:
        oid, st, ts = r["order_id"], r["state"], r["ts"]
        if st not in STATES:
            anomalies.append((oid, "unknown_state", st))
            continue
        if not ts:
            anomalies.append((oid, "null_ts", st))
        seen.setdefault(oid, {})[st] = ts
    return seen, anomalies


def check_order(events):
    """I6: arrival order vs event-time straggler."""
    out, hi = [], {}
    for r in events:
        oid, st, ts = r["order_id"], r["state"], r["ts"]
        if st not in STATES or not ts:
            continue
        max_ts, max_st = hi.get(oid, (None, None))
        if max_ts and ts < max_ts:
            out.append((oid, "I6", f"{max_st} before {st}"))
        elif max_ts is None or ts >= max_ts:
            hi[oid] = (ts, st)
    return out


def project(seen, out_path):
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id"] + STATES)
        for oid, m in seen.items():
            w.writerow([oid] + ["1" if s in m else "" for s in STATES])


def check_projection(p):
    out, ids = [], set()
    with open(p) as fh:
        rows = list(csv.reader(fh))
    hdr, body = rows[0], rows[1:]
    for r in body:
        oid = r[0] if r else "?"
        if len(r) != len(hdr):
            out.append((oid, "I4", f"arity {len(r)}"))
            continue
        if oid in ids:
            out.append((oid, "I5", "duplicate"))
        ids.add(oid)
        flags = dict(zip(hdr[1:], r[1:]))
        bad = [v for v in flags.values() if v not in DOMAIN]
        if bad:
            out.append((oid, "I3", ",".join(bad)))
            continue
        if flags["placed"] != "1":
            out.append((oid, "I2", "no placed"))
        for s in STATES[1:]:
            if flags[s] == "1" and flags[PRED[s]] != "1":
                out.append((oid, "I1", f"{s} without {PRED[s]}"))
    return out


def section(title, findings):
    return [title] + [" ".join(map(str, v)) for v in sorted(findings)]


def main():
    lines = section("== broken projection ==",
                    check_projection(path("data", "broken", "order_state_flags.csv")))
    events = read_trace(path("data", "trace", "order_trace.csv"))
    seen, anomalies = fold(events)
    lines += section("== trace anomalies ==", anomalies + check_order(events))
    os.makedirs(path("data", "rebuilt"), exist_ok=True)
    project(seen, path("data", "rebuilt", "order_state_flags.csv"))
    lines += section("== rebuilt projection ==",
                     check_projection(path("data", "rebuilt", "order_state_flags.csv")))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
