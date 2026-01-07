# Algorithm Tournament and Analysis Tools

This directory contains comprehensive tools for investigating and comparing poker solving algorithms using multi-path exploration, backtracking, and adaptive strategies.

## Overview

The investigation implements three complementary approaches:

1. **Tournament Framework** (`algorithm_tournament.py`) - Systematic head-to-head comparison
2. **Path Search** (`path_search.py`) - Multi-path exploration with backtracking and pruning
3. **Adaptive Solver** - Dynamic algorithm switching based on convergence

## Quick Start

### Run Comprehensive Tournament

Compare all algorithm variants:
```bash
PYTHONPATH=python/src python -m cli.run_algorithm_tournament \
  --game kuhn \
  --mode comprehensive \
  --output-dir ./results
```

### Run Focused Analysis

Test specific algorithm family:
```bash
# CFR variants
PYTHONPATH=python/src python -m cli.run_algorithm_tournament \
  --game kuhn --mode focused --focus cfr

# Fictitious Play variants
PYTHONPATH=python/src python -m cli.run_algorithm_tournament \
  --game kuhn --mode focused --focus fp
```

### Run Parameter Sweep

Find optimal DCFR parameters:
```bash
PYTHONPATH=python/src python -m cli.run_algorithm_tournament \
  --game kuhn --mode parameter_sweep
```

### Run Adaptive Solver

Test dynamic algorithm switching:
```bash
PYTHONPATH=python/src python -m cli.run_algorithm_tournament \
  --game kuhn --mode adaptive --max-iterations 1600
```

## Tournament Modes

### `comprehensive`
- Tests all algorithm variants (CFR, FP, MCCFR)
- Provides complete performance comparison
- Saves results to JSON for analysis

### `focused`
- Tests specific algorithm family
- Options: `--focus cfr`, `--focus fp`, `--focus mccfr`
- Faster than comprehensive mode

### `parameter_sweep`
- Systematically tests DCFR parameters
- Sweeps alpha, beta, gamma values
- Identifies optimal configurations

### `adaptive`
- Dynamically switches between algorithms
- Monitors convergence and adapts strategy
- Tests algorithm selection heuristics

## Key Results

Based on comprehensive analysis of Kuhn poker:

### Winner: CFR+ with Linear Weighting and Alternating Updates
- **Final exploitability**: 0.000052 (after 1600 iterations)
- **Improvement**: 100x better than vanilla CFR
- **Convergence**: Excellent early and late-stage performance

### Top Algorithm Families:
1. **CFR+**: Best with alternating updates + linear weighting
2. **Fictitious Play**: Strong with optimistic + linear + alternating
3. **DCFR**: Good with α=2.5, β=0.0, γ=1.5
4. **MCCFR**: Competitive but requires more iterations

## Architecture

### AlgorithmTournament
Main tournament orchestrator that:
- Registers algorithm configurations
- Runs systematic comparisons
- Tracks exploitability over time
- Calculates convergence rates

### AlgorithmPathSearch
Intelligent exploration using:
- Multi-path branching
- Early pruning of unpromising paths
- Refinement of successful configurations
- Backtracking when needed

### AdaptiveSolver
Dynamic solver that:
- Evaluates multiple algorithms
- Switches to better performers
- Maintains algorithm history
- Adapts to convergence patterns

## Testing

Run the comprehensive test suite:
```bash
PYTHONPATH=python/src python python/tests/test_algorithm_tournament.py
```

Tests cover:
- Basic tournament functionality
- CFR/FP variant comparison
- Adaptive solver behavior
- Path search with backtracking
- Convergence analysis
- Leduc poker scaling

## Files

### Core Implementation
- `python/src/algorithms/algorithm_tournament.py` - Tournament framework
- `python/src/algorithms/path_search.py` - Multi-path search
- `python/src/cli/run_algorithm_tournament.py` - CLI tool
- `python/tests/test_algorithm_tournament.py` - Test suite

### Documentation
- `docs/algorithm_investigation_report.md` - Full investigation report
- `docs/algorithm_tournament_README.md` - This file

## Performance Tips

1. **For quick iterations**: Use focused mode on specific algorithm family
2. **For exhaustive search**: Use comprehensive mode with result saving
3. **For optimization**: Use parameter_sweep to fine-tune
4. **For production**: Use adaptive solver or top tournament performers

## Future Enhancements

- Extended analysis on Leduc and River Hold'em
- Hybrid approaches (sequential algorithm switching)
- Parallel algorithm evaluation
- Warm-starting strategies
- Learning-based parameter tuning

## Citation

If you use these tools in research, please cite the investigation report and reference the multi-path exploration methodology.
