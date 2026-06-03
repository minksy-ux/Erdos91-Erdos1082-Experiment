# Installation Guide

Detailed instructions for setting up the Erdős Distance Experiment framework.

## System Requirements

- **Python**: 3.8 or later (3.10+ recommended)
- **OS**: Linux, macOS, or Windows
- **Disk space**: ~50 MB for repository + dependencies
- **RAM**: 2+ GB for n ≥ 15; 4+ GB for higher dimensions

## Step 1: Install Python

### macOS (with Homebrew)
```bash
brew install python@3.11
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv
```

### Windows
Download from [python.org](https://www.python.org/downloads/) and run the installer.
**Important**: Check "Add Python to PATH" during installation.

## Step 2: Clone the Repository

```bash
git clone https://github.com/minksky-ux/Erdos91-Erdos1082-Experiment.git
cd Erdos91-Erdos1082-Experiment
```

## Step 3: Create a Virtual Environment (Recommended)

A virtual environment isolates project dependencies from your system Python.

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Verify activation**: Your prompt should now show `(venv)` prefix.

## Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### What Gets Installed

- **numpy** (≥1.26): Numerical computing
- **scipy** (≥1.11): Scientific algorithms (optimization, distances)
- **matplotlib** (≥3.9): Visualization
- **networkx** (≥3.1): Graph algorithms (for future rigidity work)

## Step 5: Verify Installation

Run a quick test:

```bash
python src/erdos_distance_explorer.py --n 8 --trials 3 --steps 100
```

**Expected output:**
```
Running 3 candidate trials for n=8 dim=2 using seed type 'regular' and opt method 'anneal'...

Top candidate summary:

Candidate #1
distinct distances = 15
max distinct from a point = 4
no three collinear = True
energy = 0.123456
⌊n/2⌋ threshold = 4
...
```

If you see this output without errors, installation is successful!

## Troubleshooting

### "python: command not found"

Use `python3` instead of `python`:
```bash
python3 src/erdos_distance_explorer.py --n 8 --trials 3 --steps 100
```

Or create an alias:
```bash
alias python=python3
```

### "ModuleNotFoundError: No module named 'numpy'"

Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### "Matplotlib can't display plots" on headless systems

Plots are automatically saved to files with `--plot-top`. For interactive display, ensure an X11 server (Linux) or display manager (macOS/Windows) is available.

### Slow installation or dependency conflicts

Try upgrading pip and installing with a specific Python version:
```bash
python3.11 -m pip install --upgrade pip
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Optional: Development Setup

For contributing to the project:

```bash
# Install with development tools
pip install -r requirements.txt
pip install pytest black flake8  # Optional: testing and linting tools
```

## Deactivating the Virtual Environment

When done, deactivate the virtual environment:

```bash
deactivate
```

## Updating Dependencies

To update packages to latest compatible versions:

```bash
pip install --upgrade -r requirements.txt
```

## Next Steps

- Read the [README.md](README.md) for usage examples
- Check [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute
- Run experiments with different parameters (see README for examples)

## Getting Help

If installation issues persist:

1. Check [GitHub Issues](https://github.com/minksky-ux/Erdos91-Erdos1082-Experiment/issues) for similar problems
2. Open a new issue with your error message and system info
3. Include output of: `python --version` and `pip list`
