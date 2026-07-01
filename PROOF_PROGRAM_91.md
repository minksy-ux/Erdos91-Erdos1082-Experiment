# Proof Program for Erd\u0151s Problem #91

This document translates the current evidence into a path toward a true solution.

## Target Statement

Goal: prove that there exists N such that for every n >= N, the minimizer set for distinct distances in no-three-collinear planar n-point sets has at least two Euclidean similarity classes.

Current status in this repository:
- Strong computational witnesses for selected n.
- Exact objective certification for sampled candidates.
- No theorem over all sufficiently large n yet.

## Gap 1: Asymptotic Theorem for All Large n

Missing piece:
- A proof that the non-uniqueness phenomenon holds for every n beyond a threshold, not just tested n.

Required mathematical structure:
1. A structural description of minimizers (or near-minimizers) in a regime of large n.
2. A transfer principle that promotes finite verified patterns to all larger n.
3. A stability theorem: near-minimizers lie in a controlled geometric family.

Concrete plan:
1. Establish a constrained model class C_n capturing known extremal geometry (for example cyclic or near-cyclic templates with perturbation parameters).
2. Prove two distinct parameter branches in C_n both attain m_n for all large n.
3. Prove any minimizer outside C_n has objective strictly larger than m_n for large n.
4. Conclude at least two non-similar minimizers for all n >= N.

Immediate computational support tasks:
- Track candidate branch fingerprints across n and look for persistent branch continuation.
- Measure objective gaps between branch minima and best out-of-branch samples.
- Locate candidate threshold N where dual-branch behavior stabilizes.

## Gap 2: Exact Non-Similarity Certification

Missing piece:
- A rigorous argument that witness pairs are truly non-similar in the exact geometric sense.

What the current pipeline already gives:
- Shape-distance separation and signature mismatch, which are strong but numerical diagnostics.

Upgrade path to rigorous certification:
1. Use exact invariants under similarity that can be certified from exact arithmetic data.
2. For each witness pair, certify mismatch of at least one invariant that is provably similarity-invariant.
3. Produce machine-checkable certificates with interval or symbolic bounds.

Candidate invariant ladder (strongest first):
1. Exact multiset of normalized angle-based invariants.
2. Exact rank profile of Gram matrix up to scaling.
3. Certified mismatch in a canonical polynomial invariant tuple.
4. As fallback, interval-certified lower bound on Procrustes distance strictly above zero.

Practical implementation target in this repo:
- Extend witness payloads with certified invariant values and a proof object indicating which invariant separates A and B.

## Gap 3: Eliminating Unseen Minimizers

Missing piece:
- A guarantee that no unobserved configuration outside the explored search region beats or ties known witnesses in a way that destroys the conclusion.

Required argument type:
- Completeness or covering argument over configuration space modulo similarity.

Candidate rigorous strategies:
1. Branch-and-bound over normalized configuration space with interval bounds on objective.
2. Semialgebraic decomposition plus exact lower bounds per cell.
3. Certified epsilon-net covering modulo similarity with objective Lipschitz bounds.

Computational theorem template:
- For fixed n, partition normalized configuration space into cells.
- Certify lower bound L(cell) on distinct-distance objective for each cell.
- Show only cells containing known branches can attain m_n.
- Certify at least two non-similar minimizers among those cells.

This yields a per-n theorem, which can then be lifted via an asymptotic argument.

## Recommended Work Packages

WP1: Per-n rigorous certificates
- Deliverable: for each target n, a certificate bundle proving at least two non-similar minimizers at value m_n.
- Components: exact objective proofs, exact non-similarity invariant proofs, and local optimality checks.

WP2: Exhaustive exclusion engine
- Deliverable: certified branch-and-bound exclusions for all non-witness cells at each target n.
- Components: interval arithmetic bounds, pruning logs, machine-checkable proof traces.

WP3: Asymptotic lift
- Deliverable: proof that the dual-branch mechanism persists for all n >= N.
- Components: branch continuation lemma, stability lemma, exclusion lemma.

## Acceptance Criteria for a True Solution

The project can claim a true solution only when all are met:
1. Theorem over all n >= N with a complete proof.
2. Exact non-similarity certificate for each branch pair used in the theorem.
3. Completeness argument excluding unseen minimizers that could invalidate non-uniqueness.

## What This Repo Should Produce Next

Near-term artifacts to close the gap fastest:
1. A per-n formal certificate format with explicit proof objects.
2. A certified non-similarity checker based on exact invariants.
3. A bounded, auditable exclusion run for a first hard n (for example n=14 or n=26).
4. A draft theorem statement with hypotheses tied exactly to those certified artifacts.

These four artifacts bridge computational evidence to proof-grade mathematics.
