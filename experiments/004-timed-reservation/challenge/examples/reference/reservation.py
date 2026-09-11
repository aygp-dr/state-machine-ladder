"""Reference fold for experiment 004 (timed reservation over a resource).

Two coupled state machines share a resource key, plus a time axis:

- the RESOURCE lifecycle R (can the thing be reserved at all?) - a cycle
  (spec sec 2.2), so its projection is current_state + transition-legality;
- the RESERVATION lifecycle V (what one party holds over an interval) - a DAG
  with terminals (spec sec 2.4), so current_state restores completeness;
- the coupling: a live reservation requires its resource in AVAILABLE;
- the interval invariant I7: live intervals on one resource are disjoint.
  That is interval scheduling - a relation BETWEEN entities sharing a key - so
  no per-entity flag / down-set projection can express it (proposed sec 2.9).

The fold is a pure [Event] -> View catamorphism. There is no clock argument:
expiry, no-show and overdue are events a scheduler WRITES into the log. The
only notion of "now" is the log's own watermark (max event-time seen), used to
report deadlines that passed with no scheduler event (X1). The fold reports
anomalies; it never synthesizes a missing event and never repairs the view.

Usage: reservation.py            print the oracle
       reservation.py --tables   print the canonical org tables (proposed spec)
"""
import csv
import os
import sys
from datetime import datetime, timedelta

FMT = "%Y-%m-%dT%H:%M:%SZ"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- resource lifecycle R: (from, event) -> to -------------------------------
R_STATES = ["acquired", "available", "in-service", "maintenance",
            "out-of-order", "retired"]
R_EDGES = {
    ("acquired", "commission"): "available",
    ("available", "check_in"): "in-service",      # shared with V
    ("in-service", "check_out"): "available",     # shared with V
    ("available", "maintain"): "maintenance",
    ("out-of-order", "maintain"): "maintenance",
    ("maintenance", "restore"): "available",
    ("out-of-order", "restore"): "available",
    ("available", "fault"): "out-of-order",
    ("in-service", "fault"): "out-of-order",
    ("available", "retire"): "retired",
    ("maintenance", "retire"): "retired",
    ("out-of-order", "retire"): "retired",
}
R_INITIAL = "acquired"
AVAILABLE = {"available", "in-service"}           # the reservable set

# --- reservation lifecycle V: (from, event) -> to ----------------------------
V_STATES = ["requested", "held", "confirmed", "active", "overdue",
            "completed", "cancelled", "expired", "no-show"]
V_EDGES = {
    ("requested", "hold"): "held",                # admission (transactional)
    ("requested", "cancel"): "cancelled",
    ("requested", "expire"): "expired",
    ("held", "confirm"): "confirmed",
    ("held", "cancel"): "cancelled",
    ("held", "expire"): "expired",                # hold TTL, scheduler
    ("confirmed", "check_in"): "active",          # shared with R
    ("confirmed", "cancel"): "cancelled",
    ("confirmed", "no_show"): "no-show",          # check-in window, scheduler
    ("active", "check_out"): "completed",         # shared with R
    ("active", "overdue"): "overdue",             # end of interval, scheduler
    ("overdue", "check_out"): "completed",        # shared with R
}
V_CREATE = "request"                              # creates V in 'requested'
LIVE = {"held", "confirmed", "active", "overdue"}
REASSIGN_FROM = {"held", "confirmed"}             # key change, not a V edge

SHARED = {"check_in", "check_out"}
R_ONLY = {"commission", "maintain", "restore", "fault", "retire"}
V_ONLY = {"request", "hold", "confirm", "cancel", "expire", "no_show",
          "overdue", "reassign"}
# who may write each event (source column); the write side enforces it, the
# projector reports a violation as S1
WRITERS = {
    "commission": "operator", "maintain": "scheduler/operator",
    "restore": "scheduler/operator", "fault": "operator",
    "retire": "operator", "check_in": "party", "check_out": "party/operator",
    "request": "party", "hold": "party", "confirm": "party",
    "cancel": "party/operator", "expire": "scheduler",
    "no_show": "scheduler", "overdue": "scheduler", "reassign": "operator",
}
# the time axis: policy constants, and per live state the deadline
# (anchor + offset) and the scheduler event that discharges it
HOLD_TTL = timedelta(minutes=15)
CHECKIN_WINDOW = timedelta(minutes=10)
DEADLINES = {
    "held": ("hold.ts", HOLD_TTL, "expire"),
    "confirmed": ("start", CHECKIN_WINDOW, "no_show"),
    "active": ("end", timedelta(0), "overdue"),
}


def target(edges, ev):
    """every event has exactly one target state (asserted), so an illegal
    step is still applied: the log is the truth, the projector reports."""
    tos = {to for (_, e), to in edges.items() if e == ev}
    assert len(tos) == 1, (ev, tos)
    return tos.pop()


def structure(edges, states):
    """(states on a cycle, terminal states) computed from the edge table."""
    succ = {s: set() for s in states}
    for (a, _), b in edges.items():
        succ[a].add(b)

    def reach(s):
        seen, todo = set(), list(succ[s])
        while todo:
            n = todo.pop()
            if n not in seen:
                seen.add(n)
                todo.extend(succ[n])
        return seen
    cyclic = sorted(s for s in states if s in reach(s))
    terminal = sorted(s for s in states if not succ[s])
    return cyclic, terminal


def shift(ts, delta):
    return (datetime.strptime(ts, FMT) + delta).strftime(FMT)


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fold(events):
    rstate, rclass, fence = {}, {}, {}
    res, anomalies = {}, []
    hi, seen = {}, set()

    def add(key, inv, detail):
        anomalies.append((key, inv, detail))

    def admit(rid, v, r, ev):
        """admission onto a resource instance: coupling (C1) + interval (I7).
        A class key is not an instance; it is checked when it binds late."""
        if r not in rstate:
            return
        if rstate[r] not in AVAILABLE:
            add(r, "C1", f"{rid} {ev} while {rstate[r]}")
        for oid, o in sorted(res.items()):
            if (oid != rid and o["key"] == r and o["state"] in LIVE
                    and o["start"] < v["end"] and v["start"] < o["end"]):
                add(r, "I7", f"{rid} [{v['start']},{v['end']}) overlaps "
                             f"{oid} [{o['start']},{o['end']})")

    for row in events:
        ts, key, rid = row["ts"], row["resource"], row["reservation"]
        ev, src = row["event"], row["source"]
        who = rid or key
        # --- schema gate -----------------------------------------------------
        if ev not in R_ONLY | SHARED | V_ONLY:
            add(key, "unknown_event", f"{who} {ev}")
            continue
        dk = (key, rid, ev, ts)
        if dk in seen:
            add(key, "dup", f"{who} {ev}")
            continue
        seen.add(dk)
        label = f"{who} {ev}"
        if not ts:
            add(key, "null_ts", label)
        elif key in hi and ts < hi[key][0]:
            add(key, "I6", f"{hi[key][1]} before {label}")
        else:
            hi[key] = (ts, label)
        if src not in WRITERS[ev].split("/"):
            add(key, "S1", f"{who} {ev} written by {src}")
        # --- resource-only events: R's own clock -----------------------------
        if ev in R_ONLY:
            cur, to = rstate.get(key, R_INITIAL), target(R_EDGES, ev)
            if R_EDGES.get((cur, ev)) != to:
                add(key, "T2", f"resource {cur}->{to} ({ev})")
            rstate[key] = to
            if ev == "commission" and row["class"]:
                rclass[key] = row["class"]
            continue
        # --- reservation events ----------------------------------------------
        v = res.get(rid)
        if ev == V_CREATE:
            if v is not None:
                add(key, "T2", f"{rid} {v['state']}->requested (request)")
                continue
            res[rid] = {"state": "requested", "booked": key, "key": key,
                        "cls": row["class"], "start": row["start"],
                        "end": row["end"], "token": None, "hold_ts": None}
            continue
        if v is None:
            add(key, "T2", f"{rid} none ({ev})")
            continue
        if ev in SHARED:  # fencing: the resource rejects stale holders
            tok, f = row["token"], fence.get(key, 0)
            ok = tok.isdigit() and (int(tok) > f if ev == "check_in"
                                    else int(tok) == f)
            if not ok:
                add(key, "F1", f"{rid} {ev} token {tok or '-'} fence {f}")
                continue  # fenced: rejected, not applied
            if ev == "check_in":
                fence[key], v["token"] = int(tok), int(tok)
        if ev == "reassign":  # compensation: the key changes, V state does not
            if v["state"] not in REASSIGN_FROM:
                add(key, "T2", f"{rid} {v['state']} (reassign)")
            v["key"] = key
            admit(rid, v, key, ev)
            continue
        cur, to = v["state"], target(V_EDGES, ev)
        if V_EDGES.get((cur, ev)) != to:
            add(key, "T2", f"{rid} {cur}->{to} ({ev})")
        binds = ev == "check_in" and v["key"] != key
        if binds:  # late binding: class key -> instance, at check-in
            if v["key"] in rstate or rclass.get(key) != v["cls"]:
                add(key, "B1", f"{rid} check_in on {key} bound to {v['key']}")
            v["key"] = key
            admit(rid, v, key, ev)
        if ev in SHARED:  # synchronous product: R moves on the same event
            rc, rt = rstate.get(key, R_INITIAL), target(R_EDGES, ev)
            if R_EDGES.get((rc, ev)) != rt:
                add(key, "T2", f"resource {rc}->{rt} ({ev})")
            rstate[key] = rt
        v["state"] = to
        if ev == "hold":
            v["hold_ts"] = ts
            admit(rid, v, key, ev)

    # --- the watermark: the log's own "now" (no clock argument) --------------
    wm = max(r["ts"] for r in events if r["ts"])
    for rid, v in sorted(res.items()):
        if v["state"] not in LIVE:
            continue
        due = None
        if v["state"] in DEADLINES:
            anchor, delta, sched = DEADLINES[v["state"]]
            base = v["hold_ts" if anchor == "hold.ts" else anchor]
            due = base and shift(base, delta)
        if due and due <= wm:
            add(v["key"], "X1", f"{rid} {sched} due {due} unwritten at "
                                f"watermark {wm}")
        r = v["key"]
        if r in rstate and rstate[r] not in AVAILABLE:
            add(r, "C2", f"{rid} {v['state']} on {rstate[r]} without "
                         f"compensation")
    return rstate, rclass, fence, res, anomalies


def tables():
    """the canonical tables, in org form, generated from the constants above.
    The experiment gate checks every row appears verbatim in the proposal."""
    def row(*cells):
        return "| " + " | ".join(cells) + " |"

    def names(xs):
        return ", ".join(sorted(xs))

    def mins(d):
        return f"{int(d.total_seconds() // 60)} min"
    hdr = [row("from", "event", "to", "writer"), "|-+-+-+-|"]
    out = hdr + [row(a, e, b, WRITERS[e]) for (a, e), b in R_EDGES.items()]
    out += [""] + hdr
    out.append(row("(none)", V_CREATE, "requested", WRITERS[V_CREATE]))
    out += [row(a, e, b, WRITERS[e]) for (a, e), b in V_EDGES.items()]
    out.append(row(names(REASSIGN_FROM), "reassign",
                   "(unchanged; key := new instance)", WRITERS["reassign"]))
    out += ["", row("live state", "deadline", "scheduler event", "edge"),
            "|-+-+-+-|"]
    for st, (anchor, delta, ev) in DEADLINES.items():
        out.append(row(st, f"{anchor} + {mins(delta)}", ev,
                       f"{st} -> {V_EDGES[(st, ev)]}"))
    sched = {e for e, w in WRITERS.items() if w == "scheduler"}
    out += ["", row("set", "members"), "|-+-|",
            row("R states", ", ".join(R_STATES)),
            row("V states", ", ".join(V_STATES)),
            row("LIVE", names(LIVE)),
            row("AVAILABLE", names(AVAILABLE)),
            row("resource-only events", names(R_ONLY)),
            row("reservation-only events", names(V_ONLY)),
            row("shared events", names(SHARED)),
            row("scheduler events", names(sched))]
    return "\n".join(out)


def main():
    if sys.argv[1:] == ["--tables"]:
        print(tables())
        return
    events = read_log(os.path.join(ROOT, "data", "trace", "reservation_log.csv"))
    rstate, rclass, fence, res, anomalies = fold(events)
    rcyc, rterm = structure(R_EDGES, R_STATES)
    vcyc, vterm = structure(V_EDGES, V_STATES)
    lines = ["== structure ==",
             f"resource cyclic={','.join(rcyc) or '-'} "
             f"terminal={','.join(rterm)}",
             f"reservation cyclic={','.join(vcyc) or '-'} "
             f"terminal={','.join(vterm)} live={','.join(sorted(LIVE))}",
             "== anomalies =="]
    lines += [" ".join(a) for a in sorted(anomalies)]
    lines.append("== resources ==")
    for r in sorted(rstate):
        lines.append(f"{r} {rstate[r]} class={rclass.get(r, '-')} "
                     f"fence={fence.get(r, 0)}")
    lines.append("== reservations ==")
    for rid, v in sorted(res.items()):
        tok = v["token"] if v["token"] is not None else "-"
        lines.append(f"{rid} {v['state']} booked={v['booked']} key={v['key']} "
                     f"[{v['start']},{v['end']}) token={tok}")
    lines.append("== live intervals ==")
    live = sorted((v["key"], v["start"], rid, v["state"], v["end"])
                  for rid, v in res.items() if v["state"] in LIVE)
    for key, start, rid, st, end in live:
        lines.append(f"{key} {rid} {st} [{start},{end})")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
