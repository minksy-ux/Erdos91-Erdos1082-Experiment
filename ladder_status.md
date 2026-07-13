# Live Ladder Status

- version: 91
- next target: n=50 inductive window

## Rungs

| Level | Name | Status | n values | Strength |
|---:|---|---|---|---|
| 1 | Per-n certificates | complete | 14, 16, 18, 20, 22, 24, 26 | strict per-n |
| 2 | Bounded exclusion / local lemmas | complete | 32 | bounded exclusion |
| 3 | Pattern / recurrence discovery | partial | 14, 26, 32 | candidate mining |
| 4 | Inductive step for ranges of n | partial | 14, 22, 26, 32, 50 | bridge lemma |
| 5 | Asymptotic / density arguments | partial | 22, 32, 50 | full theorem |

## Gaps

- inductive bridge between 32 and 100
- density lower bound
- cell-level branch-and-bound pruning

## Fingerprints

- results/erdos91_exclusion_n32_v1.json: sha256:bb3c63cdd9f655a231f78aeeb46ed892e483a169cd0c44faea54c647194affd0 (manifest expected sha256:a37fc77acebd7cbcdc69d370f7d27a0a297308dcc053c528b1ae77ba355625ef)
- results/erdos91_witness_n14_formal_upgrade_v2.json: missing (expected sha256:1d436348a73324b78029fc7294fb466f10c65557ce912cf830016f8a0aa77a96)
- results/erdos91_witness_n26_formal_upgrade.json: missing (expected sha256:0301b19fa3bf92928a271faff800026ee3eac498aa3e6299ff904bf8d6841abb)

## Bridge Window Matrix

| Window | Strict status | Exception-aware status | Delta |
|---|---|---|---|
| 26->30->34 | n+2-certified | n+2-certified | same |
| 30->34->38 | n+2-certified | n+2-certified | same |
| 34->38->42 | surrogate-certified | n+2-certified-with-exceptions | changed |
| 38->42->46 | n+2-certified | n+2-certified-with-exceptions | changed |

