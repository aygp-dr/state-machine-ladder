"""Regenerate proposed-spec.patch: splice the blocks of proposed-spec-2.9.org
into spec.org and emit a zero-context, purely additive unified diff.

For review only. This experiment never applies it. Apply with:
    git apply --unidiff-zero experiments/004-timed-reservation/proposed-spec.patch

The anchors are pinned to spec.org at spec-v2.8.0 (the current seal on main
when this experiment was rebased). If main moves again, re-anchor PLAN.

Usage (from the repo root):
    git show spec-v2.8.0:spec.org > "$TMPDIR/spec.org"
    python3 experiments/004-timed-reservation/bin/make-patch.py "$TMPDIR/spec.org" \
        > experiments/004-timed-reservation/proposed-spec.patch
"""
import difflib
import os
import sys

PROPOSAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "proposed-spec-2.9.org")

# (proposal section title prefix, spec.org anchor line prefix, where)
PLAN = [
    ("Status block", "- Version: =2.8.0=", "after"),
    ("sec 2.9 block", "** 2.8. Taxonomy at a glance", "before"),
    ("sec 2.8 row", "| replicated (2.7) |", "after"),
    ("sec 3.1 probes", "| E10 |", "after"),
    ("sec 3.2 rubric", "| follows a deliberate structure-class switch", "after"),
    ("sec 4 row", "| 9 | raft-replicated-sm |", "after"),
    ("sec 5 flow", "   every earlier challenge as a single-node instance", "after"),
    ("Seals ledger row", "| 1.1.0   |", "before"),
    ("Changelog entry", "- =2.8.0= (2026-09-11)", "before"),
]


def blocks(path):
    """top-level '* ' sections of the proposal -> trimmed body lines."""
    out, name = {}, None
    with open(path) as fh:
        for line in fh.read().split("\n"):
            if line.startswith("* "):
                name = line[2:]
                out[name] = []
            elif name is not None:
                out[name].append(line)
    for body in out.values():
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
    return out


def main(spec_path):
    with open(spec_path) as fh:
        old = fh.read().split("\n")
    props = blocks(PROPOSAL)
    inserts = {}  # index in old -> lines to insert before that index
    for title, anchor, where in PLAN:
        [body] = [b for t, b in props.items() if t.startswith(title)]
        hits = [i for i, line in enumerate(old) if line.startswith(anchor)]
        assert len(hits) == 1, (anchor, hits)
        at = hits[0] + (1 if where == "after" else 0)
        if title.startswith("sec 2.9"):
            body = body + [""]  # blank line before the 2.8 heading
        inserts.setdefault(at, []).extend(body)
    new = []
    for i, line in enumerate(old):
        new.extend(inserts.get(i, []))
        new.append(line)
    diff = list(difflib.unified_diff(old, new, "a/spec.org", "b/spec.org",
                                     n=0, lineterm=""))
    assert not [d for d in diff[2:] if d.startswith("-")], "not additive"
    print("\n".join(diff))


if __name__ == "__main__":
    main(sys.argv[1])
