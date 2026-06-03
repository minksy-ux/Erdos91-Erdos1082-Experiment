# Ray Benchmark Research Report (Reuse DB)

Date: 2026-06-28

Data source: results/ray_benchmark_reuse.db

## Benchmark Summaries (Exact Best Count)

| n | runs | mean_best_exact | std | ci95_low | ci95_high | min_best | max_best | run_tag |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8 | 2 | 28.000 | 0.000 | 28.000 | 28.000 | 28 | 28 | 20260628_232255 |
| 10 | 2 | 45.000 | 0.000 | 45.000 | 45.000 | 45 | 45 | 20260628_232255 |

## Best Certified Results Per n

| n | best_exact_set | avg_exact_set | best_exact_min_per_point | certified_rows |
|---:|---:|---:|---:|---:|
| 8 | 28 | 28.000 | 7 | 17 |
| 10 | 45 | 45.000 | 9 | 12 |

## Approximation Gap Diagnostics (exact - approximate)

| n | mean_gap | max_gap | min_gap | rows_with_exact |
|---:|---:|---:|---:|---:|
| 8 | 0.000 | 0 | 0 | 17 |
| 10 | 0.000 | 0 | 0 | 12 |

## #91 Family Evidence (Recent Rows)

| n | exact_distinct_sq | candidates | shape_families | signature_families | tol | run_tag |
|---:|---:|---:|---:|---:|---:|---|
| 8 | 28 | 5 | 5 | 5 | 0.0200 | 20260628_232446_n8_r0 |
| 10 | 45 | 6 | 6 | None | 0.0200 | 20260628_232255_n10_r1 |
| 10 | 45 | 6 | 6 | None | 0.0200 | 20260628_232255_n10_r0 |
| 8 | 28 | 6 | 6 | None | 0.0200 | 20260628_232255_n8_r1 |
| 8 | 28 | 6 | 6 | None | 0.0200 | 20260628_232255_n8_r0 |

## Interpretation

- Signature-family counts are now present for the new schema and can be compared against shape-family counts.
- Agreement between shape and signature counts can indicate genuine diversity; divergence indicates tolerance sensitivity.
