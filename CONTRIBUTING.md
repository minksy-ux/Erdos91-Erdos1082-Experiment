# Contributing to Erdős Distance Experiment

Thank you for your interest in contributing! This document outlines guidelines and processes for contributing to the project.

## Getting Started

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/your-username/Erdos91-Erdos1082-Experiment.git
   cd Erdos91-Erdos1082-Experiment
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies** in development mode:
   ```bash
   pip install -r requirements.txt
   ```

## Code Style & Standards

- **Format**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- **Type hints**: Use Python type annotations where possible (see existing code for examples)
- **Docstrings**: Use clear docstrings for functions and modules
- **Comments**: Explain the "why", not the "what"
- **Line length**: Keep lines under 100 characters when feasible

Example:
```python
def my_function(points: Array2D, param: float = 1.0) -> float:
    """Brief description of what the function does.
    
    Args:
        points: An (n, dim) array of point coordinates.
        param: A hyperparameter controlling behavior.
    
    Returns:
        A scalar result.
    """
    # Implementation here
    pass
```

## Testing

- Test new features with representative examples
- If adding a new optimization method or seed family, verify it works with:
  ```bash
  python src/erdos_distance_explorer.py --n 8 --trials 5 --steps 500 --seed-type <your-type> --opt-method <your-method>
  ```
- Check output visually with `--plot-top 1` to ensure configurations look reasonable

## Areas for Contribution

### High-Priority
- [ ] Gradient-based optimization (scipy.optimize + autograd/JAX)
- [ ] Exact similarity testing (Kabsch algorithm refinements)
- [ ] Rigidity-based filtering using graph laplacians
- [ ] Parallel trial execution for speedup

### Medium-Priority
- [ ] Additional seed families (e.g., Voronoi-based, disk packing)
- [ ] Better collinearity enforcement (continuous penalty tuning)
- [ ] Statistical analysis tools (variance, convergence rates)
- [ ] Visualization improvements (3D rotation, distance histograms)

### Documentation
- Examples of using the framework as a library
- Tutorial notebooks for Jupyter
- Mathematical background on rigidity theory
- Performance benchmarking guide

## Submitting Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, descriptive commits:
   ```bash
   git commit -am "Add gradient-based optimization method"
   ```

3. **Push and open a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Describe your PR** with:
   - What problem does it solve?
   - How was it tested?
   - Any performance impacts?
   - References to related issues or papers

## Reporting Issues

When opening an issue:
- **Be specific**: Include the command you ran, expected vs. actual output
- **Include context**: Python version, OS, requirements versions
- **Minimal example**: Provide a minimal reproduction case if possible
- **Label appropriately**: Use labels like `bug`, `enhancement`, `documentation`

Example issue:
```
Title: Optimization diverges with dim=3 and seed-type='lattice'

Steps to reproduce:
python src/erdos_distance_explorer.py --n 10 --trials 2 --steps 100 --dim 3 --seed-type lattice

Expected: Candidates improve or stabilize
Actual: Distinct distances increase dramatically

Environment: Python 3.10, scipy 1.11.0, numpy 1.26.0
```

## Design Principles

Keep these principles in mind when contributing:

1. **Modularity**: Functions should be single-purpose and reusable
2. **Clarity**: Code should be self-documenting; prefer clarity over cleverness
3. **Flexibility**: Support multiple dimensions and optimization strategies
4. **Verifiability**: Results should be reproducible with fixed seeds
5. **Rigor**: Respect mathematical properties (e.g., no-three-collinear constraints)

## Questions?

Feel free to open a discussion or issue with the `question` label. We're happy to help!

Thanks for contributing to advancing our understanding of Erdős distance problems! 🎯
