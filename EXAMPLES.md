# Example Outputs & Interpretation Guide

This guide shows typical outputs from the framework and how to interpret them.

## Understanding the Output

### Standard Candidate Report

When you run an experiment, you'll see output like:

```
Candidate #1
distinct distances = 15
max distinct from a point = 4
no three collinear = True
energy = 0.234567
⌊n/2⌋ threshold = 4
verdict:
  #1082 set bound: 15 >= 4 -> True
  #1082 point bound: 4 >= 4 -> True
```

**What this means:**

- **distinct distances**: Total number of unique pairwise distances in the configuration. Higher is better (addresses Erdős #1082).
- **max distinct from a point**: Maximum number of distinct distances from any single point to all others. This relates to an alternative formulation of #1082.
- **no three collinear**: Whether the configuration respects the no-three-collinear constraint. Should be `True` for valid configurations.
- **energy**: Optimization objective value. Lower is better.
- **⌊n/2⌋ threshold**: For n points, Erdős #1082 conjectures at least ⌊n/2⌋ distinct distances. This is the bound to beat.

### Example: n=10

```
Running 20 candidate trials for n=10 dim=2 using seed type 'regular' and opt method 'anneal'...

Top candidate summary:

Candidate #1
distinct distances = 12
max distinct from a point = 5
no three collinear = True
energy = 0.189234
⌊n/2⌋ threshold = 5
verdict:
  #1082 set bound: 12 >= 5 -> True     ✓ Sets conjecture
  #1082 point bound: 5 >= 5 -> True    ✓ Point conjecture

Candidate #2
distinct distances = 12
max distinct from a point = 5
no three collinear = True
energy = 0.195612

Candidate #3
distinct distances = 11
max distinct from a point = 4
no three collinear = True
energy = 0.203456
verdict:
  #1082 set bound: 11 >= 5 -> True
  #1082 point bound: 4 >= 5 -> False    ✗ Fails point variant

Clusters by signature: 3 distinct groups among 20 candidates
  group 1: 8 configs, best distinct distances = 12
  group 2: 7 configs, best distinct distances = 11
  group 3: 5 configs, best distinct distances = 10
```

**Interpretation:**

- The best candidate achieves 12 distinct distances (well above the ⌊10/2⌋ = 5 threshold).
- Multiple distinct solutions exist (3 groups), suggesting non-uniqueness.
- Most trials converge to similar minima, indicating robust local structures.

## Clustering Results

The framework groups candidates by similarity:

```
Clusters by procrustes: 5 distinct groups among 20 candidates
  group 1: 6 configs, best distinct distances = 15
  group 2: 5 configs, best distinct distances = 14
  group 3: 4 configs, best distinct distances = 13
  group 4: 3 configs, best distinct distances = 12
  group 5: 2 configs, best distinct distances = 11
```

**What this shows:**

- **Number of groups**: Diversity of extremal structures. More groups = more distinct minimizers (relevant to Erdős #91).
- **Group sizes**: How frequently each structure appears. Larger groups indicate more stable/robust configurations.
- **Best distinct distances per group**: Each group's best achievement (configurations within groups are similar up to rotation/scaling).

## JSON Output Format

With `--save-json out/candidates.json`, you get:

```json
[
  {
    "distinct_distances": 15,
    "max_distinct_from_point": 5,
    "no_three_collinear": true,
    "energy": 0.234567,
    "points": [
      [0.123, 0.456],
      [0.789, -0.234],
      [-0.567, 0.890],
      ...
    ]
  },
  ...
]
```

Use this for further analysis:
- Load into NumPy for post-processing
- Visualize distance distributions
- Compare with theoretical bounds
- Export to research papers

## Visualizations

With `--plot-top 3`, PNG files are generated:

### 2D Plots

Scatter plots with labeled points:
- **Blue dots**: Point locations
- **Numbers**: Point indices (0 to n-1)
- **Title**: Configuration rank and n value

Interpret:
- **Circular/regular patterns**: Indicate symmetric structures
- **Clustered patterns**: Suggest hierarchy or substructures
- **Spread-out patterns**: Often maximize distances (higher distinctness)

### 3D Plots

Similar to 2D but in 3D space. Helpful for visualizing higher-dimensional behavior.

## Optimization Method Comparison

Run the same problem with different methods:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method anneal
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method hillclimb
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method direct
```

**Compare results:**
- **Simulated Annealing**: Good at escaping local minima; slower but higher quality.
- **Hill Climbing**: Fast and simple; prone to local minima.
- **Direct**: Explicitly optimizes distinct-distance count; sometimes misses energy optimizations.

## Seed Family Effects

Compare initialization strategies:

```bash
python src/erdos_distance_explorer.py --n 10 --trials 10 --steps 1000 --seed-type regular
python src/erdos_distance_explorer.py --n 10 --trials 10 --steps 1000 --seed-type lattice
python src/erdos_distance_explorer.py --n 10 --trials 10 --steps 1000 --seed-type uniform
```

**Expected differences:**
- **Regular**: Often finds highly symmetric solutions.
- **Lattice**: Grid-like structures; good for certain n values.
- **Uniform**: Unbiased; explores broader solution space.

## Interpreting Erdős #91: Multiple Minimizers

Erdős #91 asks: Are there ≥2 non-similar extremal configurations?

**Look for:**

1. **Multiple groups with same best distinct-distances count**:
   ```
   group 1: best distinct distances = 15
   group 2: best distinct distances = 15
   group 3: best distinct distances = 14
   ```
   Groups 1 & 2 are both minimizers—this suggests the answer is **YES**.

2. **Check if groups are truly non-similar**:
   - Use `--cluster-tol` to adjust sensitivity
   - Lower tolerance = stricter grouping (might split similar configs)
   - Higher tolerance = looser grouping (might merge different configs)

3. **Visual inspection**: Plot top candidates from different groups:
   ```bash
   python src/erdos_distance_explorer.py --n 12 --trials 50 --steps 2000 --plot-top 5
   ```
   Examine if the top 5 are clearly distinct or similar.

## Known Patterns for Small n

### n=4
- Expected minimum distinct distances: 3
- Often a square or rhombus

### n=5
- Expected minimum: 4
- Often a pentagon or irregular quadrilateral + center

### n=6
- Expected minimum: 5
- Hexagon or other symmetric arrangements

### n=7, 8, 9, 10
- Minima less well-studied
- Framework helps explore these!

## Checking Convergence

If results don't improve with more trials or steps:

1. **Increase `--steps`**: More optimization time per trial
2. **Try different `--opt-method`**: Methods have different convergence rates
3. **Increase `--trials`**: More random restarts find broader optima
4. **Adjust seed tolerance**: `--distance-tol` affects precision

Example:
```bash
# Conservative: fewer steps, more trials
python src/erdos_distance_explorer.py --n 12 --trials 50 --steps 1000

# Aggressive: more steps, same trials
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 5000
```

## Troubleshooting Unexpected Results

### All candidates have low distinct distances

- **Cause**: Optimization is over-fitting to collinearity penalty
- **Fix**: Reduce `--distance-tol` for stricter counting, or reduce collinearity penalty (modify code)

### No three collinear = False for best candidates

- **Cause**: Optimization sacrificed collinearity constraint for distinctness
- **Fix**: Increase lambda_col in energy_function (in code), or reduce --steps

### High variance between trials

- **Cause**: Solution landscape is rugged (many local minima)
- **Fix**: Use `--opt-method anneal` (better escape) or increase steps

## Next Steps

1. **Document your findings**: Save results with meaningful filenames
2. **Analyze patterns**: Look for symmetries, structural properties
3. **Compare with literature**: Check if results match known bounds
4. **Share discoveries**: Open an issue or discussion with interesting findings!

---

For more details, see the [README](README.md) and explore the code comments in `src/erdos_distance_explorer.py`.
