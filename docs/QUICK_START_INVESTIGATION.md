# Quick Start: Algorithm Investigation Framework

This guide provides practical examples for using the algorithm investigation tools.

## Running a Quick Benchmark

Compare all algorithms on Kuhn poker:

```bash
cd /home/runner/work/poker_solver/poker_solver
PYTHONPATH=python/src python -m cli.run_benchmark --game kuhn
```

Compare specific algorithms:

```bash
PYTHONPATH=python/src python -m cli.run_benchmark \
    --game kuhn \
    --algorithms "CFR+" "Warm-start" "Adaptive CFR"
```

Set a target exploitability threshold:

```bash
PYTHONPATH=python/src python -m cli.run_benchmark \
    --game kuhn \
    --target 0.001
```

## Running Algorithm Exploration

Explore CFR variants:

```bash
PYTHONPATH=python/src python -m cli.run_algorithm_exploration \
    --game kuhn \
    --iterations 800 \
    --explore cfr
```

Explore all algorithms with branching:

```bash
PYTHONPATH=python/src python -m cli.run_algorithm_exploration \
    --game kuhn \
    --iterations 800 \
    --explore all \
    --branch \
    --output results.json
```

## Using Hybrid Algorithms in Code

### Warm-Start Trainer (Fastest Convergence)

```python
from algorithms.hybrid_algorithms import WarmStartTrainer, WarmStartConfig
from games.kuhn import KuhnPoker

game = KuhnPoker()
trainer = WarmStartTrainer(
    game,
    WarmStartConfig(
        base_iterations=200,      # MCCFR phase
        refinement_iterations=800  # CFR+ phase
    )
)
trainer.run(1000)
profile = trainer.average_strategy_profile()
```

### Adaptive CFR (Auto-Tuning)

```python
from algorithms.hybrid_algorithms import AdaptiveCFRTrainer, AdaptiveCFRConfig
from games.kuhn import KuhnPoker

game = KuhnPoker()
trainer = AdaptiveCFRTrainer(
    game,
    AdaptiveCFRConfig(
        adaptation_frequency=100,
        plateau_threshold=0.001
    )
)
trainer.run(800)
profile = trainer.average_strategy_profile()
```

### Hybrid CFR+FP

```python
from algorithms.hybrid_algorithms import HybridCFRFPTrainer, HybridCFRFPConfig
from games.kuhn import KuhnPoker

game = KuhnPoker()
trainer = HybridCFRFPTrainer(
    game,
    HybridCFRFPConfig(switch_iteration=400)
)
trainer.run(800)
profile = trainer.average_strategy_profile()
```

## Custom Explorations

### Testing Custom Parameter Ranges

```python
from experiments.algorithm_explorer import AlgorithmExplorer, ExperimentPath
from algorithms.cfr import CFRConfig, CFRTrainer
from games.kuhn import KuhnPoker

game = KuhnPoker()
explorer = AlgorithmExplorer(game)

# Define custom parameter sweep
configs = []
for alpha in [1.0, 1.5, 2.0, 2.5, 3.0]:
    for gamma in [1.5, 2.0, 2.5]:
        configs.append({
            "use_plus": False,
            "use_dcfr": True,
            "dcfr_alpha": alpha,
            "dcfr_beta": 0.0,
            "dcfr_gamma": gamma,
        })

# Run experiments
path = ExperimentPath(path_id="custom_dcfr", configs=configs, results=[])
for config_dict in configs:
    config = CFRConfig(**config_dict)
    result = explorer._run_experiment(
        lambda: CFRTrainer(game, config),
        "dcfr",
        config_dict,
        800,
    )
    path.results.append(result)

explorer.paths.append(path)
explorer.print_summary()
```

### Custom Benchmark Suite

```python
from experiments.benchmark import AlgorithmBenchmark
from algorithms.cfr import CFRConfig, CFRTrainer
from games.kuhn import KuhnPoker

game = KuhnPoker()
benchmark = AlgorithmBenchmark(game, checkpoints=[100, 200, 400, 800])

# Define custom algorithms to compare
algorithms = {
    "Custom CFR+": (
        lambda: CFRTrainer(
            game,
            CFRConfig(use_plus=True, linear_weighting=True, alternating=True)
        ),
        {"use_plus": True, "linear_weighting": True, "alternating": True},
    ),
    "Custom DCFR": (
        lambda: CFRTrainer(
            game,
            CFRConfig(use_dcfr=True, dcfr_alpha=2.5, dcfr_beta=0.0, dcfr_gamma=2.0)
        ),
        {"use_dcfr": True, "dcfr_alpha": 2.5},
    ),
}

benchmark.compare_algorithms(algorithms)
```

## Interpreting Results

### Exploitability
Lower is better. Measures how much worse the strategy performs compared to optimal.
- < 0.001: Excellent (near-optimal)
- 0.001-0.01: Very good
- 0.01-0.1: Good (practical)
- > 0.1: Needs more iterations

### Convergence Rate
Higher is better. Measures exploitability decrease per iteration.
- > 0.0001: Fast convergence
- 0.00001-0.0001: Moderate convergence
- < 0.00001: Slow convergence

### Time Efficiency
- Consider both wall-clock time and quality
- MCCFR is fastest but less accurate
- CFR+ is balanced
- Warm-start is best convergence per iteration

## Best Practices

### For Development
1. Start with quick benchmark on Kuhn poker
2. Test your modifications against baseline
3. Use exploration to find optimal parameters
4. Validate on Leduc before applying to river

### For Production
1. Use Warm-start for one-off solves
2. Use CFR+ (alt) for highest accuracy
3. Use Adaptive CFR for unknown game structures
4. Profile your specific game tree characteristics

### For Research
1. Run full exploration with branching
2. Save results to JSON for reproducibility
3. Test across multiple games (Kuhn, Leduc, River)
4. Document parameter sensitivity

## Common Issues

### Slow Convergence
- Try CFR+ instead of vanilla CFR
- Enable alternating updates
- Use Warm-start for faster initial progress

### High Memory Usage
- Use MCCFR instead of full CFR
- Reduce checkpoint frequency
- Process results incrementally

### Inconsistent Results
- MCCFR has high variance (try multiple seeds)
- FP can be sensitive to initialization
- Run longer or use more stable algorithm (CFR+)

## Example Workflow

Complete workflow for investigating a new game:

```bash
# 1. Quick baseline benchmark
PYTHONPATH=python/src python -m cli.run_benchmark \
    --game kuhn \
    --checkpoints 100 200 400

# 2. Full exploration with branching
PYTHONPATH=python/src python -m cli.run_algorithm_exploration \
    --game kuhn \
    --iterations 800 \
    --explore all \
    --branch \
    --output kuhn_results.json

# 3. Test best configuration
PYTHONPATH=python/src python -m cli.run_exploitability \
    --game kuhn \
    --algo cfr+ \
    --no-alternating  # or whatever exploration found

# 4. Validate on harder game
PYTHONPATH=python/src python -m cli.run_benchmark \
    --game leduc \
    --algorithms "Best Config"
```

## Further Reading

- `docs/ALGORITHM_INVESTIGATION.md` - Full investigation report
- `python/src/experiments/README.md` - Detailed API documentation
- `python/src/algorithms/hybrid_algorithms.py` - Hybrid algorithm implementations
