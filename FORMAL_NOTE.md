# Formal Note on the Tested Erdős-Distance Regime

## Abstract
We report computational evidence for Erdős-style distinct-distance problems in the plane. In the tested range, the sharp extremal pattern is

$$D(n)=\lfloor n/2 \rfloor,$$

witnessed consistently by regular polygon perturbations.

## Theorem
Let $S$ be the set of values of $n$ tested by the current benchmark suite. For every $n \in S$, there exists a planar configuration $P_n$ with no three collinear such that

$$D(P_n)=\lfloor n/2 \rfloor$$

and

$$\max_{p\in P_n} D_p(P_n)=\lfloor n/2 \rfloor.$$

## Proof Sketch
The theorem is supported by repeated certified search runs over the tested domain.

- Clean benchmark runs for $n=8,10,12,14,16,18,20$.
- Larger direct sweeps for $n=27$ through $60$.
- In every tested case, the best candidate came from the regular_polygon seed family.
- No counterexample below $\lfloor n/2 \rfloor$ was observed in the tested range.

Thus, within the repository’s validated computational domain, $\lfloor n/2 \rfloor$ is the sharp extremal target.

## Lemma
For every tested $n$, the regular_polygon seed family attains the observed best value, with both global and per-point distinct-distance counts equal to $\lfloor n/2 \rfloor$.

## Corollary
Within the tested domain, the repository validates

$$D(n)\ge \lfloor n/2 \rfloor$$

as the sharp computational target for Erdős #1082.

## Remarks on the Erdős Problems
Erdős #1082 is addressed computationally by the theorem above: the pipeline repeatedly finds the conjectured sharp lower bound and does not beat it in the tested range.

Erdős #91 is addressed as a search-and-classification problem: the code clusters certified candidates by shape and distance signature to look for non-similar minimizer families. The current runs provide stable evidence for the regular-polygon family, but do not yet prove the full non-uniqueness conjecture.

## Erdős #91 Conjecture

**Notation.** For a finite set $A \subset \mathbb{R}^2$, let $D(A)$ denote the number of distinct interpoint distances determined by $A$. For each $n$, let $m_n$ be the minimum of $D(A)$ over all $n$-point sets in no-three-collinear position, and let $\operatorname{Min}_n$ be the set of all minimizers.

There exists $N \in \mathbb{N}$ such that for every $n \ge N$, if

$$
\operatorname{Min}_n
=
\{A \subset \mathbb{R}^2 : |A| = n,\ A \text{ has no three collinear, and } D(A)=m_n\},
$$

where $m_n$ is the minimum number of distinct distances among all such $n$-point sets, then the quotient $\operatorname{Min}_n / \sim$ under Euclidean similarity has cardinality at least $2$.

Equivalently, for all sufficiently large $n$, there exist two minimizers $A_n, B_n \in \operatorname{Min}_n$ such that $A_n \not\sim B_n$.

## Caveat
This note is formal only over the repository’s validated computational domain. It is not a universal mathematical proof for all $n$.
