# Erdős Distinct-Distance Experiment

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Overview

This repository is a **computational exploration framework** for classical discrete-geometry problems proposed by Paul Erdős, with a focus on understanding the structure of point configurations that minimize distinct distances.

### The Problems

- **Erdős #1082**: Do n points in the plane with no three collinear always determine at least ⌊n/2⌋ distinct distances? This is a fundamental open question in discrete geometry.
- **Erdős #91**: Are there at least two fundamentally different (non-similar) configurations that minimize the distinct-distance count for large n? This probes the uniqueness of extremal structures.
- **Higher dimensions**: Extensions to 3D and beyond, including rigidity-based filtering.

### Why This Matters

These problems connect discrete geometry to combinatorics, graph rigidity theory, and optimization. Understanding extremal point configurations has applications in sensor networks, crystallography, and computational geometry.

## Installation

### Prerequisites

- Python 3.8 or later
- pip package manager

### Setup

1. Clone the repository:

```bash
git clone https://github.com/minksy-ux/Erdos91-Erdos1082-Experiment.git
cd Erdos91-Erdos1082-Experiment
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

**Note**: For visualization features, ensure you have `matplotlib` installed (included in requirements).

## Repository Structure

```
src/
├── erdos_distance_explorer.py   # Main candidate generator and local search optimizer
├── graph_rigidity.py             # Rigidity analysis and graph-structure utilities
└── ...

requirements.txt                  # Python dependencies
README.md                        # This file
```

### Key Modules

- **`erdos_distance_explorer.py`**: The core engine for generating and optimizing point configurations. It:
  - Generates candidate point sets using multiple seed strategies (random, lattice, etc.)
  - Applies local search optimizations (hill climbing, simulated annealing, direct search)
  - Enforces soft no-three-collinear constraints
  - Counts distinct distances and groups candidates by similarity
  - Outputs JSON results and optional visualizations

- **`graph_rigidity.py`**: Utilities for rigidity analysis and graph filtering. This module provides a foundation for:
  - Computing rigidity matrices and analyzing degrees of freedom
  - Identifying structural properties of distance graphs
  - Future screening of candidates by rigidity constraints

## Quick Start

### Example 1: Small Experiment (2D, n=10)

```bash
python src/erdos_distance_explorer.py --n 10 --trials 16 --steps 2000
```

This runs 16 independent trials optimizing 10 points over 2000 optimization steps each. Output includes:
- Best distinct-distance count found
- Number of trial runs and convergence statistics
- Top-ranked configurations

### Example 2: Larger Experiment with Custom Clustering

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --seed-type lattice --cluster-by procrustes --cluster-tol 0.01
```

**Parameters explained:**
- `--n 12`: Optimize 12 points
- `--trials 20`: Run 20 independent trials
- `--steps 3000`: 3000 optimization steps per trial
- `--seed-type lattice`: Initialize from a lattice-based seed (vs. random)
- `--cluster-by procrustes`: Group similar configurations using Procrustes alignment
- `--cluster-tol 0.01`: Tolerance for grouping (lower = stricter)

### Example 3: Higher Dimensions

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --dim 3 --seed-type uniform --cluster-by shape
```

- `--dim 3`: Optimize in 3D space (default is 2D)
- `--cluster-by shape`: Use shape-based similarity (rotation/scale invariant)

### Example 4: Compare Optimization Methods

```bash
# Simulated annealing
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method anneal

# Hill climbing
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method hillclimb

# Direct search (SciPy minimize)
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method direct

# Direct search with stricter distance tolerance
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --opt-method direct --distance-tol 1e-5
```

These experiments let you benchmark which optimization strategy finds better minima for your parameter choices.

### Example 5: Save Results and Visualizations

```bash
python src/erdos_distance_explorer.py --n 12 --trials 20 --steps 3000 --save-json out/top_candidates.json --plot-top 3
```

- `--save-json`: Save top candidates to a JSON file for further analysis
- `--plot-top 3`: Generate scatter plots of the top 3 configurations

Output is saved to `out/top_candidates.json` and optional PNG visualizations in the output directory.

## Framework Goals

- **Generate and optimize** point sets that may minimize distinct distances
- **Enforce constraints** via soft no-three-collinear penalties
- **Compare configurations** by distinct-distance signatures and similarity measures
- **Provide a foundation** for rigidity-screened graph search pipelines
- **Explore trade-offs** between different optimization methods and seed families

## Results & Findings

*(To be updated as experiments conclude)*

- Current best distinct-distance count for n=12 in 2D: [To be filled]
- Largest n tested: [To be filled]
- Observations on minimizer uniqueness: [To be filled]

## Development Roadmap

### In Progress
- [ ] Gradient-based optimization methods (scipy.optimize + autograd)
- [ ] Exact similarity testing via alignment algorithms

### Planned
- [ ] Graph-level pipeline for rigidity-based candidate screening
- [ ] Scaling to higher dimensions (d ≥ 4) and larger n (≥ 20)
- [ ] Integration with SAT/CSP solvers for constraint hardening
- [ ] Comprehensive result database and statistical analysis

### Future Extensions
- Parallel trial execution for speedup
- Web interface for interactive exploration
- Integration with mathematical libraries (e.g., CGAL, Qhull via Python bindings)

## References & Background

- **Erdős distance problems**: Paul Erdős, "On sets of distances of n points," *American Mathematical Monthly*, 53(4), 1946.
- **Graph rigidity**: Rigidity theory in computational geometry (Laman conditions, rigidity matrices).
- **Distinct-distance bounds**: Frank de Bruijn & Paul Erdős work on graph realizations.

For a deeper dive, consult the discrete geometry literature on distance graphs and extremal configurations.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Questions & Support

For questions or issues:
- Open a [GitHub Issue](https://github.com/minksy-ux/Erdos91-Erdos1082-Experiment/issues)
- Check existing discussions for answers
- Review code comments in the main modules for implementation details
