# Bridge Step Verification #91

## Transition Checks

| Transition | Status | Source witness | Target witness | Source checks ok | Target checks ok |
|---|---|:---:|:---:|:---:|:---:|
| 34->36 | blocked | False | False | False | False |
| 36->38 | blocked | False | False | False | False |
| 34->38 | certified | True | True | True | True |

## Exception Policy

- Endpoint witness requirements are waived when transition endpoints are in exceptional_indices: 36

- blockers for 34->36: missing target witness file for n=36
- blockers for 36->38: missing source witness file for n=36

## Pilot Result

- Certified pilot transition: 34->38
- This is the current machine-checkable finite bridge witness.
- Note: this pilot is a longer-step surrogate; n->n+2 remains open for this window.

