# Ray Benchmark Research Report

Date: 2026-06-28

Data source: results/ray_benchmark.db

## Benchmark Summaries (Exact Best Count)

| n | runs | mean_best_exact | std | ci95_low | ci95_high | min_best | max_best | run_tag |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8 | 2 | 28.000 | 0.000 | 28.000 | 28.000 | 28 | 28 | 20260628_231855 |
| 10 | 2 | 45.000 | 0.000 | 45.000 | 45.000 | 45 | 45 | 20260628_231855 |
| 12 | 2 | 66.000 | 0.000 | 66.000 | 66.000 | 66 | 66 | 20260628_231855 |

## Best Certified Results Per n

| n | best_exact_set | avg_exact_set | best_exact_min_per_point | certified_rows |
|---:|---:|---:|---:|---:|
| 8 | 28 | 28.000 | 7 | 60 |
| 10 | 45 | 45.000 | 9 | 60 |
| 12 | 66 | 66.000 | 11 | 60 |

## Approximation Gap Diagnostics (exact - approximate)

| n | mean_gap | max_gap | min_gap | rows_with_exact |
|---:|---:|---:|---:|---:|
| 8 | 0.000 | 0 | 0 | 60 |
| 10 | 0.000 | 0 | 0 | 60 |
| 12 | 0.000 | 0 | 0 | 60 |

## #91 Family Evidence (Recent Rows)

| n | exact_distinct_sq | candidates | shape_families | signature_families | tol | run_tag |
|---:|---:|---:|---:|---:|---:|---|
| 12 | 66 | 12 | 12 | NA | 0.0200 | 20260628_231855_n12_r1 |
| 12 | 66 | 12 | 12 | NA | 0.0200 | 20260628_231855_n12_r0 |
| 10 | 45 | 12 | 12 | NA | 0.0200 | 20260628_231855_n10_r1 |
| 10 | 45 | 12 | 12 | NA | 0.0200 | 20260628_231855_n10_r0 |
| 8 | 28 | 12 | 12 | NA | 0.0200 | 20260628_231855_n8_r1 |
| 8 | 28 | 12 | 12 | NA | 0.0200 | 20260628_231855_n8_r0 |

## Interpretation

- This run produced stable exact best counts for n=8,10,12 in the sampled regime.
- Exact per-point counts in best certified rows remain far above floor(n/2) for these n values.
- Approximation-gap statistics are essential for trust; rely on certified values for claims.
- Family counts are currently heuristic and tolerance-dependent; treat them as exploratory evidence for #91, not definitive classification.
