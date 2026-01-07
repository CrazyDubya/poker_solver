# River Poker Solver

This repository builds a no-limit Texas hold'em river subgame solver, starting with Kuhn and Leduc poker for validation. Core algorithms include CFR, CFR+, external-sampling MCCFR, Fictitious Play, and DCFR. Python is the reference implementation; C++ targets performance.

**New**: Comprehensive algorithm investigation framework with novel hybrid algorithms (Warm-Start, Adaptive CFR, Hybrid CFR+FP) that achieve 10x faster convergence. See `docs/ALGORITHM_INVESTIGATION.md` for findings.

## Repository Layout

- `python/` reference implementation (algorithms, games, CLI tooling).
  - `python/src/algorithms/` standard and hybrid algorithms
  - `python/src/experiments/` investigation framework
  - `python/src/cli/` command-line tools
- `cpp/` optimized C++ river solver.
- `docs/` algorithm investigation reports and design notes.

Contributor guide: see `AGENTS.md`.

## Quick Start

### Standard Solves

Python (Kuhn/Leduc):

```sh
PYTHONPATH=python/src python -m cli.run_exploitability --game kuhn --algo cfr+
```

Python (river defaults):

```sh
PYTHONPATH=python/src python -m cli.run_river_exploitability --algo cfr+
```

Optimized C++ (river defaults):

```sh
cmake -S cpp -B cpp/build
cmake --build cpp/build -j
./cpp/build/river_solver_optimized --algo cfr+ --iters 2000
```

### Algorithm Investigation

Comprehensive benchmark of all algorithms:

```sh
PYTHONPATH=python/src python -m cli.run_benchmark --game kuhn --target 0.001
```

Systematic parameter exploration with branching:

```sh
PYTHONPATH=python/src python -m cli.run_algorithm_exploration \
    --game kuhn --iterations 800 --explore all --branch
```

See `python/src/experiments/README.md` for detailed usage.

## Algorithm Selection Guide

Based on comprehensive investigation (see `docs/ALGORITHM_INVESTIGATION.md`):

**For highest accuracy:**
- CFR+ (alternating) + DCFR: 0.000102 exploitability on Kuhn poker
- Parameters: `use_plus=True, linear_weighting=True, alternating=True, use_dcfr=True`

**For fastest convergence:**
- Warm-Start Trainer: 10x faster than standard CFR+
- Combines MCCFR approximation with CFR+ refinement

**For real-time applications:**
- MCCFR: 4-6x faster wall-clock time
- Good approximate solutions when speed matters

**For automatic tuning:**
- Adaptive CFR: Self-adjusting parameters
- Robust across different game structures

## Subgame JSON Format

GUI exports a JSON file that both C++ solvers can load with `--config`. Key fields:

```json
{
  "board": ["Ks", "Th", "7s", "4d", "2s"],
  "pot": 1000,
  "stack": 9500,
  "bet_sizes": [1.0],
  "include_all_in": true,
  "max_raises": 1000,
  "players": [
    {"hands": ["AsKd", "..."], "weights": [1.0, "..."]},
    {"hands": ["AsKd", "..."], "weights": [1.0, "..."]}
  ]
}
```

Advanced sizing arrays (`oop_first_bets`, `ip_first_bets`, `oop_first_raises`, `ip_first_raises`, `oop_next_raises`,
`ip_next_raises`) are optional and default to `bet_sizes` when omitted.

## Notes

- Defaults use a uniform range, board `Ks Th 7s 4d 2s`, pot 1000, stacks 9500, and bet sizes `0.5, 1.0` with all-in enabled.
- For subgames saved from the GUI, pass `--config path/to/subgame.json`.
