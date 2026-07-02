# Bridge Proof Obligations for Erdos #91

This document converts the current rung-4/rung-5 gap into explicit proof obligations.

## Purpose

Goal: move from finite certificates and bounded exclusion to a theorem-grade statement
for all sufficiently large n.

Current anchor artifacts:
- results/erdos91_witness_n14_formal_upgrade_v2.json
- results/erdos91_witness_n22.json
- results/erdos91_witness_n26_formal_upgrade.json
- results/erdos91_exclusion_n32_v1.json
- results/bridge_lemma_91.json
- results/asymptotic_signal_91.json

## Target Theorem Schema

There exists N such that for every n >= N, the minimizer set for #91 contains at
least two Euclidean similarity classes.

## Proof Obligations

O1. Finite-core branch identity
- Claim: a stable core family (currently symmetry_120) persists across anchor n.
- Evidence source: witness and stability JSON artifacts.
- Pass condition: no contradiction in certified invariants across anchors.
- Status: in-progress

O2. Local continuation step
- Claim: if branch hypotheses hold at n, they extend to n+2 (or a fixed step).
- Evidence source: bridge_lemma_91.md/json plus new continuation checks.
- Pass condition: a proved transfer statement with explicit hypotheses and constants.
- Status: open

O3. Uniform exclusion around anchors
- Claim: non-branch cells have objective strictly above m_n in a bounded window.
- Evidence source: exclusion reports and future cell decomposition logs.
- Pass condition: a machine-checkable lower bound L(cell) > m_n for all non-branch cells in the window.
- Status: open

O4. Window-to-window bootstrap
- Claim: continuation + exclusion imply propagation from [n0, n1] to [n1, n2].
- Evidence source: formal bridge script/document (to be added).
- Pass condition: one completed bootstrap from a certified base window.
- Status: open

O5. Density or asymptotic closure
- Claim: bootstrap reaches all n >= N.
- Evidence source: asymptotic_signal_91 and future density lemma artifact.
- Pass condition: explicit N plus proof that no terminal failure mode remains beyond N.
- Status: open

O6. Independent verification
- Claim: proof objects are replayable by an independent checker.
- Evidence source: verify_witness_proof_object.py + second verifier transcript.
- Pass condition: two independent verifiers agree on all theorem-critical artifacts.
- Status: open

## Highest-Impact Next Milestone

Milestone M1: complete O2 for one concrete bridge step and lock it with replayable checks.

Why this is highest impact:
- It is the first step that directly upgrades rung-4 from narrative to theorem mechanics.
- It enables O4 bootstrap structure; without O2, asymptotic closure cannot start.
- It can be audited and rerun in CI-style fashion.

## Execution Plan for M1

1. Define exact bridge hypotheses H(n) from existing witness invariants.
2. Formalize a transfer claim H(n) => H(n+2) with explicit constants/tolerances.
3. Add a machine-readable proof object for one tested transition (pilot: 22 -> 24 or 24 -> 26 when feasible).
4. Add a verifier command sequence and frozen transcript.

Current replay command:

```bash
python verify_bridge_step_91.py \
	--root . \
	--transitions 22:24,24:26,22:26 \
	--out-json results/bridge_step_hypothesis_91.json \
	--out-md results/bridge_step_verification_91.md
```

Current finite pilot outcome:
- 22->26 is certified as a machine-checkable bridge surrogate.
- 22->24 and 24->26 are blocked because n=24 currently has witness_found=false.
- Therefore the n->n+2 bridge remains open in this window, but the verification
	machinery and one finite transition are now live.

Transfer-composition replay command:

```bash
python verify_bridge_transfer_91.py \
	--schema bridge_transfer_schema_91.json \
	--step-hypothesis results/bridge_step_hypothesis_91.json \
	--asymptotic results/asymptotic_signal_91.json \
	--window 22:26:32 \
	--out-json results/bridge_transfer_proof_91.json \
	--out-md results/bridge_window_composition_91.md
```

Current transfer-composition outcome:
- transfer_lemma_status: surrogate-certified
- n_plus_2_status: blocked
- certified edge: 22->26
- blocked edges: 22->24, 24->26

Dual-track update after targeted n=24 sweeps:
- Strict track (required_core_family=symmetry_120): still blocks n->n+2.
- Family-flex track (required_core_family=any): certifies 22->24 and 24->26,
	and therefore certifies n->n+2 on the current tested window.

Conditional theorem track (family-flex) status:
- Window [22,26] (checked via 22->24 and 24->26): n+2-certified.
- Window [26,30] (checked via 26->28 and 28->30): blocked because n=28 and n=30
	currently have witness_found=false at shape_tol=0.006.
- Therefore the family-flex track is now a formal conditional program with one
	certified window and one explicit blocker window.

Replay commands for dual-track checks:

```bash
python verify_bridge_step_91.py \
	--root . \
	--transitions 22:24,24:26,22:26 \
	--hypothesis-id H91-bridge-step-v1-strict \
	--required-core-family symmetry_120 \
	--out-json results/bridge_step_hypothesis_91_strict.json \
	--out-md results/bridge_step_verification_91_strict.md \
	--strict

python verify_bridge_step_91.py \
	--root . \
	--transitions 22:24,24:26,22:26 \
	--hypothesis-id H91-bridge-step-v2-family-flex \
	--required-core-family any \
	--out-json results/bridge_step_hypothesis_91_family_flex.json \
	--out-md results/bridge_step_verification_91_family_flex.md \
	--strict
```

## Progress Metrics

Use these metrics to update closeness scores:
- M1 complete: theorem-level +8 to +12 points.
- O3 first certified window complete: theorem-level +6 to +10 points.
- O4 one successful bootstrap: theorem-level +10 to +15 points.
- O5 closure with explicit N: theorem-level +15 to +20 points.

## Current Read

Given current artifacts, the largest expected jump comes from M1 (O2 completion),
not from additional unconstrained search at nearby n.
