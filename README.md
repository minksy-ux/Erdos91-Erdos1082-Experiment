# Erdos91-Erdos1082-Experiment

This repository is a prototype exploration framework for the Erdős distinct-distance problems, especially:

- **Erdős #1082**: whether n points in the plane with no three collinear determine at least ⌊n/2⌋ distinct distances,
- **Erdős #91**: whether there are at least two non-similar minimizers of the distinct-distance count for large n,
- Related higher-dimensional variants and rigidity-based search heuristics.

## What is included

- `src/erdos_distance_explorer.py`: a candidate generator and local search prototype for point configurations, with distance-count and no-collinearity checks.
- `src/graph_rigidity.py`: a lightweight rigidity / graph-structure skeleton for future graph-based filtering and extremal candidate selection.
- `requirements.txt`: Python dependencies for numeric experiments.

## Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run a small experiment:

```bash
python src/erdos_distance_explorer.py --n 10 --trials 16 --steps 2000
```

3. Optionally choose different seed families and clustering methods:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --seed-type lattice --cluster-by procrustes --cluster-tol 0.01
```

4. Run higher-dimensional experiments:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --dim 3 --seed-type uniform --cluster-by shape
```

5. Compare optimization methods:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method anneal
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method hillclimb
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method direct
```

6. Save and visualize top candidates:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --save-json out/top_candidates.json --plot-top 3
```

6. Inspect the top candidates, cluster counts, and saved output paths.

## Goals of the framework

- generate and optimize point sets that may minimize distinct distances,
- enforce soft no-three-collinear constraints,
- compare candidate configurations by distinct-distance signatures,
- provide a base for later rigidity-screened graph search.

## Next steps

- extend the search engine with better optimization methods (gradient-based or simulated annealing),
- add exact similarity testing between candidate shapes,
- add a graph-level pipeline to screen candidate distance graphs by rigidity,
- scale the search to higher dimensions and larger n.
