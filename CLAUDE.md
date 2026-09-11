# CLAUDE.md - state-machine-ladder

## What Is This

A graded set of nine state machines, each posed as "reconstruct a view from a
log" (source-derivation-view, see `spec.org`). Challenge 01 is a worked, green
reference; 02-09 are open challenges to implement. `README.org` is canonical.

## Quick Reference

| command | does |
|---|---|
| `bin/verify.sh` | run every challenge with a reference; PASS/FAIL/OPEN |
| `bin/verify.sh challenges/NN-<name>` | verify one challenge |
| `bin/new-exercise -d <dir> -n <name> ...` | stamp a fresh challenge skeleton (spec §12) |

## Build & Test

```sh
bin/verify.sh          # expect: at least 01-order-lifecycle PASS; others OPEN
```

A challenge is *solved* when it has `examples/oracle-contract.txt`, an
`examples/<tag>-<lang>/run.sh`, and its own `bin/verify.sh` that passes.

## Conventions

- Every challenge is a source-derivation-view instance (`spec.org`): pure fold,
  shared fixtures in the challenge's `data/`, oracle-gated, re-tell not port.
- Pick the *right projection* for the structure S: a chain admits wide flags
  (down-sets); a cycle/reversible graph does not (use current-state +
  transition-legality); a poset restores down-sets; a DFA -> accept/reject.
- Documentation is org-mode; conventional commits, one logical step, stage by name.

## What NOT to Do

- Do not edit a challenge's fixtures or oracle to pass a check.
- Do not add CI/Docker/linters; references are single-file, stdlib-only.
- Do not commit generated fold outputs (`**/data/rebuilt/`).
- Do not mark a challenge *solved* without a reference that reproduces its oracle.
```
