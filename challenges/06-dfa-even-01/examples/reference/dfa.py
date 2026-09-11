"""Reference solution for challenge 06 (dfa-even-01) - a complete DFA.

The language is {strings over {0,1} with an even number of 0s and an even number
of 1s}. State = (parity of #0, parity of #1): EE, EO, OE, OO. Start and sole
accepting state is EE; reading 0 flips the 0-parity, reading 1 flips the
1-parity. Here the view collapses to a single bit, accept/reject, and the fold
IS the extended transition function delta* (spec sec 2.5) - a catamorphism over
the free monoid on the alphabet. The fold reports anomalies; its output is the
oracle.
"""
import csv
import os

# state = (p0, p1); E=0 even, O=1 odd
NAME = {(0, 0): "EE", (0, 1): "EO", (1, 0): "OE", (1, 1): "OO"}
START = (0, 0)
ACCEPT = (0, 0)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def step(state, sym):
    p0, p1 = state
    return (p0 ^ 1, p1) if sym == "0" else (p0, p1 ^ 1)


def read_log(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def main():
    events = read_log(os.path.join(ROOT, "data", "trace", "dfa_log.csv"))
    anomalies, st, seen, hi = [], {}, set(), {}
    for r in events:
        wid, sym, ts = r["word_id"], r["symbol"], r["ts"]
        st.setdefault(wid, START)
        if sym not in ("0", "1"):
            anomalies.append((wid, "unknown_symbol", sym)); continue
        key = (wid, sym, ts)
        if key in seen:
            anomalies.append((wid, "dup", sym)); continue
        seen.add(key)
        if not ts:
            anomalies.append((wid, "null_ts", sym))
        elif hi.get(wid) and ts < hi[wid][0]:
            anomalies.append((wid, "I6", f"{hi[wid][1]} before {sym}"))
        elif ts:
            hi[wid] = (ts, sym)
        st[wid] = step(st[wid], sym)
    lines = ["== anomalies =="]
    lines += [" ".join(map(str, v)) for v in sorted(anomalies)]
    lines.append("== result ==")
    for wid, s in sorted(st.items()):
        lines.append(f"{wid} state={NAME[s]} accept={'yes' if s == ACCEPT else 'no'}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
