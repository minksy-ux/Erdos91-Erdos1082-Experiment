# Formal Invariants for Erdos #91 Certificates

This note defines equation-level similarity invariants used to strengthen per-n non-similarity certificates.

## Setup

Let

- P = {p_1, ..., p_n} subset R^2,
- Q = {q_1, ..., q_n} subset R^2,
- p_i, q_i represented in canonical sorted order after centering and normalization used by the pipeline.

A similarity map has the form

T(x) = s R x + t,

where s > 0, R in O(2), and t in R^2.

If Q = T(P), then all invariants below are equal between P and Q.

## Invariant 1: Normalized Squared-Distance Spectrum

Define

d_ij(P) = ||p_i - p_j||^2,

and let d_min(P) be the minimum positive d_ij(P).

Define the multiset

Delta(P) = { d_ij(P) / d_min(P) : 1 <= i < j <= n }.

Similarity action gives d_ij(T(P)) = s^2 d_ij(P), so ratios are unchanged.

## Invariant 2: Normalized Squared-Area Spectrum

For triples i < j < k define doubled signed area

A_ijk(P) = det(p_j - p_i, p_k - p_i),

and squared area term

a_ijk(P) = A_ijk(P)^2.

Let a_min(P) be the minimum positive a_ijk(P). Define

Alpha(P) = { a_ijk(P) / a_min(P) : 1 <= i < j < k <= n, a_ijk(P) > 0 }.

Under similarity, A_ijk scales by s^2 up to sign, so a_ijk scales by s^4. Ratios are invariant.

## Invariant 3: Centered Gram Eigenvalue Ratios

Let X(P) be the n x 2 matrix of centered coordinates (rows p_i - mean(P)).
Define

G(P) = X(P) X(P)^T.

Let lambda_1 >= lambda_2 > 0 be the positive eigenvalues of G(P).
Define

Lambda(P) = (lambda_1/lambda_1, lambda_2/lambda_1).

Under similarity, X -> s X R^T, so G -> s^2 G and eigenvalue ratios are invariant.

## Separation Principle

If any one of the following holds,

- Delta(P) != Delta(Q), or
- Alpha(P) != Alpha(Q), or
- Lambda(P) != Lambda(Q),

then P and Q are not similar.

This gives a mathematically valid contradiction test:

Q = T(P) implies Delta(P)=Delta(Q), Alpha(P)=Alpha(Q), Lambda(P)=Lambda(Q).

Therefore inequality of any invariant disproves similarity.

## How It Improves #91 Formal Progress

For a fixed n, a certificate pair (P,Q) with

1. equal exact objective m_n,
2. exact validity (no-three-collinear), and
3. at least one invariant mismatch above,

provides a stronger non-similarity witness than shape-distance-only evidence.

This still does not prove the asymptotic statement "for all n >= N", but it upgrades the per-n formal core used in WP1 of the proof program.
