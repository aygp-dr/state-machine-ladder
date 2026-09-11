"""Reference solution for challenge 09 (raft replicated state machine) - the capstone.

"A state machine is a deterministic function of its log." This challenge has
TWO folds that make that sentence literal:

(a) the *role FSM* over election/heartbeat events (follower/candidate/leader),
    a small state machine with an anomaly report, exactly like the earlier
    single-node challenges; and
(b) the *replicated state machine*: apply(committed_log) -> KV state. We fold
    the SAME totally-ordered committed log twice (two replicas) and assert the
    two projections are identical. Determinism is the whole point of Raft:
    replicate the log, apply it deterministically, and every replica agrees.

source (log) -> derivation (apply/fold) -> view (state), replicated.
"""
import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---- (A) role FSM ----------------------------------------------------------
ROLES = ["follower", "candidate", "leader"]
START_ROLE = "follower"
# (role, event) -> next role
LEGAL = {
    ("follower", "timeout"): "candidate",
    ("candidate", "win"): "leader",
    ("candidate", "timeout"): "candidate",
    ("candidate", "higher_term"): "follower",
    ("leader", "higher_term"): "follower",
    ("leader", "step_down"): "follower",
    ("follower", "recv_heartbeat"): "follower",
}
EVENTS = {ev for (_role, ev) in LEGAL}


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def role_fold(events):
    """final role per node + anomalies. Reports; never drops silently."""
    role, anomalies = {}, []
    hi, seen = {}, set()
    for r in events:
        nid, ev, ts = r["node_id"], r["event"], r["ts"]
        cur = role.get(nid, START_ROLE)
        if ev not in EVENTS:
            anomalies.append((nid, "unknown_event", ev))
            role[nid] = cur
            continue
        key = (nid, ev, ts)
        if key in seen:
            anomalies.append((nid, "dup", ev))
            continue
        seen.add(key)
        if not ts:
            anomalies.append((nid, "null_ts", ev))
        elif nid in hi and ts < hi[nid]:
            anomalies.append((nid, "I6", ev))
        elif ts:
            hi[nid] = ts
        nxt = LEGAL.get((cur, ev))
        if nxt is None:
            anomalies.append((nid, "T2", f"{cur}:{ev}"))
            role[nid] = cur  # illegal transition: do not change role
        else:
            role[nid] = nxt
    return role, anomalies


# ---- (B) replicated state machine ------------------------------------------
def apply_committed(committed):
    """apply a totally-ordered committed command log in idx order -> KV map."""
    state = {}
    for r in sorted(committed, key=lambda x: int(x["idx"])):
        op, k, v = r["op"], r["key"], r["val"]
        if op == "set":
            state[k] = v
        elif op == "del":
            state.pop(k, None)
    return state


def main():
    role_events = read_log(os.path.join(ROOT, "data", "trace", "role_log.csv"))
    role, anomalies = role_fold(role_events)

    committed = read_log(os.path.join(ROOT, "data", "trace", "committed_log.csv"))
    replica_a = apply_committed(committed)
    replica_b = apply_committed(committed)
    agree = "yes" if replica_a == replica_b else "no"

    lines = ["== role anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== node roles ==")
    lines += [f"{nid} role={role[nid]}" for nid in sorted(role)]
    lines.append("== applied state ==")
    lines += [f"key={k} val={v}" for k, v in sorted(replica_a.items())]
    lines.append(f"replicas_agree={agree}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
