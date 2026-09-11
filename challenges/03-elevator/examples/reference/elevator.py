"""Reference solution for challenge 03 (elevator) - a product state + request set.

State per car is (floor in 1..N, doors in {open,closed}) plus a set of pending
requests. Like the cycle case (spec sec 2.2) there is no sound wide-flag
projection; the view is the current product state plus the pending set, and the
invariants guard the physical rules. Each car starts at floor 1, doors closed,
no requests. The fold reports anomalies; its printed output is the oracle.
"""
import csv
import os

N = 4  # floors 1..N
EVENTS = {"press", "move", "open", "close", "serve"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def desc(ev, arg):
    return f"{ev}:{arg}" if arg else ev


def fold(events):
    cars, anomalies, seen, hi = {}, [], set(), {}

    def car(cid):
        return cars.setdefault(cid, {"floor": 1, "doors": "closed", "req": set()})

    for r in events:
        cid, ev, arg, ts = r["car_id"], r["event"], r["arg"], r["ts"]
        if ev not in EVENTS:
            anomalies.append((cid, "unknown_event", ev))
            continue
        key = (cid, ev, arg, ts)
        if key in seen:
            anomalies.append((cid, "dup", desc(ev, arg)))
            continue
        seen.add(key)
        if not ts:
            anomalies.append((cid, "null_ts", desc(ev, arg)))
        elif hi.get(cid) and ts < hi[cid]:
            anomalies.append((cid, "I6", desc(ev, arg)))
        elif ts:
            hi[cid] = ts
        s = car(cid)
        if ev == "press":
            s["req"].add(int(arg))
        elif ev == "move":
            f = int(arg)
            if s["doors"] == "open":
                anomalies.append((cid, "E-doors", desc(ev, arg)))
            if abs(f - s["floor"]) != 1:
                anomalies.append((cid, "E-teleport", f"{s['floor']}->{f}"))
            if f < 1 or f > N:
                anomalies.append((cid, "E-range", str(f)))
            s["floor"] = f
        elif ev == "open":
            s["doors"] = "open"
        elif ev == "close":
            s["doors"] = "closed"
        elif ev == "serve":
            f = int(arg)
            if s["floor"] == f and s["doors"] == "open" and f in s["req"]:
                s["req"].discard(f)
            else:
                anomalies.append((cid, "E-serve", str(f)))
    return cars, anomalies


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "elevator_log.csv"))
    cars, anomalies = fold(events)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== current state ==")
    for cid, s in sorted(cars.items()):
        pending = ",".join(map(str, sorted(s["req"]))) or "-"
        lines.append(f"{cid} floor={s['floor']} doors={s['doors']} pending={pending}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
