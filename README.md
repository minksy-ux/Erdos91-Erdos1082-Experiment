# Erdos Rigidity Explorer

A computational exploration framework for Erdos distinct-distance problems #91 and #1082.

This project currently combines geometric seeding, stochastic local optimization, distance-signature clustering, and rigidity-oriented graph utilities in a lightweight research prototype.

## Why this project

The goal is to generate strong computational evidence for difficult open questions in discrete geometry:

- Erdos #1082: whether n planar points with no three collinear must determine at least floor(n/2) distinct distances.
- Erdos #91: whether large n admits at least two non-similar minimizers for the distinct-distance count.

## Current capabilities

- Multi-seed candidate generation in 2D and 3D.
- Three optimization modes: hill climb, simulated annealing, and direct distinct-distance objective.
- Distinct-distance counting with tolerance control.
- No-three-collinear checks for 2D and 3D.
- Candidate clustering by exact distance signature, Procrustes distance, or shape similarity.
- JSON export and plotting for top candidates.

## Project layout

- src/erdos_distance_explorer.py: experiment runner and optimization pipeline.
- src/graph_rigidity.py: graph-level rigidity helpers and summary tools.
- src/verification/exact_verifier.py: exact symbolic certification for 2D candidates.
- src/utils/database.py: SQLite experiment tracking.
- run_experiments.py: structured multi-seed search runner with certification output.
- plots/: generated figures.
- out/: generated candidate exports.
- results/: SQLite experiment database.
- certified_configs/: exact certification JSON outputs.

## Quick start

Install in editable mode:

```bash
pip install -e .
```

Install with development tools:

```bash
pip install -e .[dev]
```

Install optional dashboard and parallel extras:

```bash
pip install -e .[dashboard,parallel]
```

Run a small experiment:

```bash
erdos-explore --n 10 --trials 16 --steps 2000
```

Equivalent direct module invocation:

```bash
python src/erdos_distance_explorer.py --n 10 --trials 16 --steps 2000
```

Try different methods and settings:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method anneal
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method hillclimb
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method direct --distance-tol 1e-5
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --dim 3 --seed-type uniform --cluster-by shape
```

Run the structured search pipeline:

```bash
python run_experiments.py --n 12 --trials 200 --steps 1500 --opt-method anneal --certify-top 5
```

Run distributed mode with Ray:

```bash
python run_experiments.py --n 12 --trials 500 --steps 1200 --mode ray --ray-cpus 4 --certify-top 5
```

Run strict exact-ranking mode (certify all trials, then rank by certified counts):

```bash
python run_experiments.py --n 12 --trials 120 --steps 400 --mode ray --ray-cpus 2 --certify-top 5 --exact-ranking-all
```

Run benchmark mode (repeated runs with confidence summary):

```bash
python run_experiments.py --n-list 8,10,12 --trials 60 --steps 250 --benchmark-runs 4 --certify-top 5 --exact-ranking-all
```

Launch interactive dashboard:

```bash
streamlit run dashboard.py
```

Save top candidates and plots:

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --save-json out/top_candidates.json --plot-top 3
```

## Development workflow

Run formatting, linting, and tests:

```bash
black src
ruff check src
pytest
```

## Exact certification and experiment tracking

The structured runner writes every trial to SQLite and certifies top candidates exactly:

- Database: results/erdos_experiments.db
- Certificates: certified_configs/n{n}_trial{trial}_rank{k}.json

Tracked exact fields include:

- exact distinct squared-distance count,
- exact min/max per-point distinct-distance counts,
- exact validity (no three collinear),
- approximate-vs-exact gap (visible in dashboard diagnostics).

Certification uses SymPy rationals plus mpmath precision to avoid floating-point false positives in distinct-distance counts and collinearity checks.
The runner reports both approximate (tolerance-based) and exact certified counts for top candidates; treat certified counts as authoritative when they differ.

The runner also stores:

- benchmark summaries (mean/std/95% CI for best exact counts),
- #91 family-evidence rows with estimated number of non-similar minimizer families among certified best candidates.

## Research roadmap

Planned extensions include:

- Rigidity-guided structured generation (Laman/Henneberg and pebble-game style filters).
- Exact symbolic certification for top candidates.
- Persistent-homology analysis for non-similarity evidence.
- Parallel large-scale search and reproducible benchmark suites.

## Contributing

Contributions are welcome in these directions:

- Better seed families and optimization objectives.
- Faster geometric predicates and clustering.
- Reproducible experiment scripts and benchmark reports.
- Rigidity and certification modules with tests.
