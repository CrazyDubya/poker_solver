# Algorithm Investigation Framework

This module provides comprehensive tools for investigating and optimizing poker-solving algorithms through systematic exploration and benchmarking.

## Overview

The investigation framework implements a **multi-path branching methodology** that:
1. Explores algorithm parameter spaces systematically
2. Branches from best results to find optimal configurations
3. Benchmarks algorithms on standardized metrics
4. Discovers novel hybrid algorithm combinations

## Components

### `algorithm_explorer.py`
Multi-path branching exploration of algorithm variants.

**Key Features:**
- Systematic parameter sweeps for CFR, FP, MCCFR
- Branching from best configurations
- Convergence rate tracking
- Result persistence (JSON export)

**Usage:**
```python
from experiments.algorithm_explorer import AlgorithmExplorer
from games.kuhn import KuhnPoker

game = KuhnPoker()
explorer = AlgorithmExplorer(game)

# Explore CFR variants
explorer.explore_cfr_variants(target_iters=800)

# Explore FP variants
explorer.explore_fp_variants(target_iters=800)

# Branch from best results
explorer.branch_from_best(num_branches=10)

# Get recommendations
best = explorer.get_best_overall()
fastest = explorer.get_fastest_convergence()
efficient = explorer.get_most_efficient()

# Print summary
explorer.print_summary()

# Save results
explorer.save_results(Path("results.json"))
```

### `benchmark.py`
Comprehensive benchmarking suite for algorithm comparison.

**Key Features:**
- Side-by-side algorithm comparison
- Multiple ranking metrics (quality, speed, efficiency)
- Exploitability curves
- Time-to-target measurement
- Overall recommendation system

**Usage:**
```python
from experiments.benchmark import AlgorithmBenchmark, create_standard_benchmark_suite
from games.kuhn import KuhnPoker

game = KuhnPoker()
benchmark = AlgorithmBenchmark(
    game,
    checkpoints=[25, 50, 100, 200, 400, 800],
    target_exploitability=0.001,
)

# Run standard benchmark suite
algorithms = create_standard_benchmark_suite(game)
benchmark.compare_algorithms(algorithms)

# Get recommendations
best = benchmark.get_best_algorithm()
fastest = benchmark.get_fastest_algorithm()
efficient = benchmark.get_most_efficient_algorithm()
recommended = benchmark.recommend_algorithm()
```

## Command-Line Tools

### Exploration Tool
```bash
PYTHONPATH=python/src python -m cli.run_algorithm_exploration \
    --game kuhn \
    --iterations 800 \
    --explore cfr fp mccfr \
    --branch \
    --output results.json
```

**Options:**
- `--game`: Game to test on (kuhn, leduc)
- `--iterations`: Target iterations for experiments
- `--explore`: Algorithm families to explore (cfr, fp, mccfr, all)
- `--branch`: Enable branching from best results
- `--output`: JSON output file

### Benchmark Tool
```bash
PYTHONPATH=python/src python -m cli.run_benchmark \
    --game kuhn \
    --checkpoints 50 100 200 400 800 \
    --target 0.001 \
    --algorithms "CFR+" "Warm-start" "Adaptive CFR"
```

**Options:**
- `--game`: Game to benchmark on
- `--checkpoints`: Iteration checkpoints for evaluation
- `--target`: Target exploitability for time-to-target metrics
- `--algorithms`: Specific algorithms to benchmark (default: all)

## Novel Hybrid Algorithms

The framework includes three novel hybrid algorithms in `algorithms/hybrid_algorithms.py`:

### 1. Hybrid CFR+FP
Combines CFR's fast early convergence with FP's theoretical guarantees.

```python
from algorithms.hybrid_algorithms import HybridCFRFPTrainer, HybridCFRFPConfig

trainer = HybridCFRFPTrainer(
    game,
    HybridCFRFPConfig(switch_iteration=400)
)
trainer.run(800)
```

### 2. Adaptive CFR
Automatically tunes CFR parameters based on convergence monitoring.

```python
from algorithms.hybrid_algorithms import AdaptiveCFRTrainer, AdaptiveCFRConfig

trainer = AdaptiveCFRTrainer(
    game,
    AdaptiveCFRConfig(
        adaptation_frequency=100,
        plateau_threshold=0.001,
    )
)
trainer.run(800)
```

### 3. Warm-Start Trainer
Two-phase solver: fast MCCFR approximation → refined CFR+ solve.

```python
from algorithms.hybrid_algorithms import WarmStartTrainer, WarmStartConfig

trainer = WarmStartTrainer(
    game,
    WarmStartConfig(
        base_iterations=200,
        refinement_iterations=800,
    )
)
trainer.run(1000)
```

## Key Findings

Based on comprehensive testing on Kuhn poker:

### Best Solution Quality
- **CFR+ (alternating)**: 0.000141 exploitability
- **Adaptive CFR**: 0.000141 exploitability
- **CFR+ (alt) + DCFR**: 0.000102 exploitability (discovered via branching)

### Fastest Convergence
- **Warm-Start**: 0.00043077 exp/iter (10x faster than CFR+)
- **MCCFR**: 0.00015028 exp/iter
- **CFR+**: 0.00002807 exp/iter

### Most Time-Efficient
- **MCCFR**: 0.025s total
- **CFR**: 0.097s total
- **CFR+**: 0.109s total

## Recommendations

### For NLTH River Solving

**Production Use:**
- Warm-Start Trainer for fastest convergence
- CFR+ (alternating) for highest accuracy

**Research/Development:**
- Adaptive CFR for automatic tuning
- CFR+ + DCFR for best solution quality

**Real-Time Applications:**
- MCCFR for speed-critical scenarios
- Trade accuracy for 4-6x speedup

### Optimal Parameters

**DCFR:**
- α (alpha): 3.0
- β (beta): 0.0
- γ (gamma): 2.0

**Hybrid Switch Points:**
- CFR→FP: 400-600 iterations
- MCCFR→CFR+: 200-300 iterations

## Extending the Framework

### Adding New Algorithms

1. Implement algorithm following the standard interface:
```python
class MyAlgorithmTrainer:
    def __init__(self, game, config):
        self.game = game
        # ...
    
    def run(self, iterations: int):
        # Training logic
        pass
    
    def average_strategy_profile(self):
        # Return strategy
        return profile
```

2. Add to benchmark suite:
```python
from experiments.benchmark import create_standard_benchmark_suite

suite = create_standard_benchmark_suite(game)
suite["My Algorithm"] = (
    lambda: MyAlgorithmTrainer(game, config),
    config_dict,
)
```

### Adding New Exploration Paths

```python
class MyExplorer(AlgorithmExplorer):
    def explore_my_variants(self, target_iters: int):
        configs = [...]
        path = ExperimentPath(path_id="my_path", configs=configs, results=[])
        
        for config_dict in configs:
            result = self._run_experiment(
                lambda: MyTrainer(self.game, config_dict),
                "my_algo",
                config_dict,
                target_iters,
            )
            path.results.append(result)
        
        path.best_result = min(path.results, key=lambda r: r.final_exploitability)
        self.paths.append(path)
        self.all_results.extend(path.results)
        return [path]
```

## Output Format

### Exploration Results (JSON)
```json
{
  "paths": [
    {
      "path_id": "cfr_basic",
      "num_configs": 8,
      "best_exploitability": 0.000254,
      "best_config": {"use_plus": true, "linear_weighting": true}
    }
  ],
  "all_results": [...],
  "summary": {
    "total_experiments": 44,
    "best_overall": {...},
    "fastest_convergence": {...},
    "most_efficient": {...}
  }
}
```

## Performance Metrics

The framework tracks:
- **Final Exploitability**: Solution quality
- **Convergence Rate**: Exploitability decrease per iteration
- **Total Time**: Wall-clock execution time
- **Time per Iteration**: Average time per iteration
- **Time to Target**: Time to reach exploitability threshold
- **Exploitability Curves**: Full convergence history

## References

See `docs/ALGORITHM_INVESTIGATION.md` for detailed findings and recommendations.
