from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from algorithms.evaluation import exploitability


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single algorithm configuration."""
    name: str
    config: Dict[str, Any]
    exploitability_curve: List[float]
    checkpoints: List[int]
    total_time: float
    time_per_iteration: float
    final_exploitability: float
    convergence_rate: float
    time_to_target: float | None = None


class AlgorithmBenchmark:
    """Comprehensive benchmarking suite for poker solving algorithms.
    
    Compares multiple algorithms on the same problem with standardized
    metrics including convergence speed, time efficiency, and solution quality.
    """

    def __init__(
        self,
        game,
        checkpoints: List[int] | None = None,
        target_exploitability: float | None = None,
    ) -> None:
        self.game = game
        self.checkpoints = checkpoints or [25, 50, 100, 200, 400, 800, 1600]
        self.target_exploitability = target_exploitability
        self.results: List[BenchmarkResult] = []

    def benchmark_algorithm(
        self,
        name: str,
        trainer_factory: Callable,
        config: Dict[str, Any],
    ) -> BenchmarkResult:
        """Benchmark a single algorithm configuration."""
        trainer = trainer_factory()
        exploitability_curve = []
        checkpoint_list = []
        completed = 0
        time_to_target = None
        
        start_time = time.time()
        
        for checkpoint in self.checkpoints:
            iters_to_run = checkpoint - completed
            trainer.run(iters_to_run)
            completed = checkpoint
            
            profile = trainer.average_strategy_profile()
            exp_value = exploitability(self.game, profile)
            exploitability_curve.append(exp_value)
            checkpoint_list.append(checkpoint)
            
            # Check if we reached target
            if self.target_exploitability and exp_value <= self.target_exploitability and time_to_target is None:
                time_to_target = time.time() - start_time
        
        total_time = time.time() - start_time
        time_per_iter = total_time / completed if completed > 0 else 0.0
        final_exp = exploitability_curve[-1] if exploitability_curve else float('inf')
        
        # Calculate convergence rate
        if len(exploitability_curve) > 1:
            initial = exploitability_curve[0]
            final = exploitability_curve[-1]
            iters = checkpoint_list[-1] - checkpoint_list[0]
            convergence_rate = (initial - final) / iters if iters > 0 else 0.0
        else:
            convergence_rate = 0.0
        
        result = BenchmarkResult(
            name=name,
            config=config,
            exploitability_curve=exploitability_curve,
            checkpoints=checkpoint_list,
            total_time=total_time,
            time_per_iteration=time_per_iter,
            final_exploitability=final_exp,
            convergence_rate=convergence_rate,
            time_to_target=time_to_target,
        )
        
        self.results.append(result)
        return result

    def compare_algorithms(self, algorithms: Dict[str, tuple[Callable, Dict[str, Any]]]) -> None:
        """Benchmark multiple algorithms and compare results."""
        print("\n" + "=" * 80)
        print("ALGORITHM BENCHMARK COMPARISON")
        print("=" * 80)
        print(f"Game: {self.game.__class__.__name__}")
        print(f"Checkpoints: {self.checkpoints}")
        if self.target_exploitability:
            print(f"Target exploitability: {self.target_exploitability:.6f}")
        print()
        
        for name, (trainer_factory, config) in algorithms.items():
            print(f"Benchmarking {name}...", end=" ", flush=True)
            result = self.benchmark_algorithm(name, trainer_factory, config)
            print(f"Done! Final exp: {result.final_exploitability:.6f}")
        
        self.print_comparison()

    def print_comparison(self) -> None:
        """Print detailed comparison of all benchmarked algorithms."""
        if not self.results:
            print("No benchmark results to compare.")
            return
        
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)
        
        # Sort by final exploitability
        sorted_by_quality = sorted(self.results, key=lambda r: r.final_exploitability)
        
        print("\n--- Ranking by Solution Quality (Final Exploitability) ---")
        for rank, result in enumerate(sorted_by_quality, 1):
            print(f"{rank}. {result.name}: {result.final_exploitability:.6f}")
        
        # Sort by convergence rate
        sorted_by_convergence = sorted(self.results, key=lambda r: -r.convergence_rate)
        
        print("\n--- Ranking by Convergence Rate (Exp decrease per iteration) ---")
        for rank, result in enumerate(sorted_by_convergence, 1):
            print(f"{rank}. {result.name}: {result.convergence_rate:.8f}")
        
        # Sort by time efficiency
        sorted_by_time = sorted(self.results, key=lambda r: r.total_time)
        
        print("\n--- Ranking by Time Efficiency (Total time) ---")
        for rank, result in enumerate(sorted_by_time, 1):
            print(f"{rank}. {result.name}: {result.total_time:.3f}s")
        
        # Time to target (if applicable)
        if self.target_exploitability:
            results_with_target = [r for r in self.results if r.time_to_target is not None]
            if results_with_target:
                sorted_by_target = sorted(results_with_target, key=lambda r: r.time_to_target)
                print(f"\n--- Time to reach target ({self.target_exploitability:.6f}) ---")
                for rank, result in enumerate(sorted_by_target, 1):
                    print(f"{rank}. {result.name}: {result.time_to_target:.3f}s")
        
        # Detailed table
        print("\n--- Detailed Metrics ---")
        print(f"{'Algorithm':<30} {'Final Exp':<12} {'Conv Rate':<12} {'Time':<10} {'Time/Iter':<12}")
        print("-" * 80)
        for result in sorted_by_quality:
            print(
                f"{result.name:<30} "
                f"{result.final_exploitability:<12.6f} "
                f"{result.convergence_rate:<12.8f} "
                f"{result.total_time:<10.3f} "
                f"{result.time_per_iteration:<12.6f}"
            )
        
        # Convergence curves
        print("\n--- Exploitability Curves ---")
        print(f"{'Algorithm':<30}", end=" ")
        for checkpoint in self.checkpoints:
            print(f"{checkpoint:<10}", end=" ")
        print()
        print("-" * 80)
        
        for result in self.results:
            print(f"{result.name:<30}", end=" ")
            for exp_val in result.exploitability_curve:
                print(f"{exp_val:<10.6f}", end=" ")
            print()
        
        print("\n" + "=" * 80)

    def get_best_algorithm(self) -> BenchmarkResult:
        """Return the algorithm with the best final exploitability."""
        if not self.results:
            raise ValueError("No benchmark results available")
        return min(self.results, key=lambda r: r.final_exploitability)

    def get_fastest_algorithm(self) -> BenchmarkResult:
        """Return the algorithm with the fastest convergence."""
        if not self.results:
            raise ValueError("No benchmark results available")
        return max(self.results, key=lambda r: r.convergence_rate)

    def get_most_efficient_algorithm(self) -> BenchmarkResult:
        """Return the algorithm with the best time efficiency."""
        if not self.results:
            raise ValueError("No benchmark results available")
        return min(self.results, key=lambda r: r.total_time)

    def recommend_algorithm(self) -> BenchmarkResult:
        """Recommend best overall algorithm based on weighted metrics.
        
        Combines solution quality, convergence rate, and time efficiency
        into a single score.
        """
        if not self.results:
            raise ValueError("No benchmark results available")
        
        # Normalize metrics
        min_exp = min(r.final_exploitability for r in self.results)
        max_exp = max(r.final_exploitability for r in self.results)
        min_time = min(r.total_time for r in self.results)
        max_time = max(r.total_time for r in self.results)
        min_conv = min(r.convergence_rate for r in self.results)
        max_conv = max(r.convergence_rate for r in self.results)
        
        def score(result: BenchmarkResult) -> float:
            # Lower is better for exploitability and time
            # Higher is better for convergence rate
            exp_score = (result.final_exploitability - min_exp) / (max_exp - min_exp + 1e-10)
            time_score = (result.total_time - min_time) / (max_time - min_time + 1e-10)
            conv_score = (max_conv - result.convergence_rate) / (max_conv - min_conv + 1e-10)
            
            # Weighted combination (adjust weights as needed)
            return 0.5 * exp_score + 0.3 * time_score + 0.2 * conv_score
        
        return min(self.results, key=score)


def create_standard_benchmark_suite(game) -> Dict[str, tuple[Callable, Dict[str, Any]]]:
    """Create a standard suite of algorithms for benchmarking."""
    from algorithms.cfr import CFRConfig, CFRTrainer
    from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
    from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig
    from algorithms.hybrid_algorithms import (
        AdaptiveCFRConfig,
        AdaptiveCFRTrainer,
        HybridCFRFPConfig,
        HybridCFRFPTrainer,
        WarmStartConfig,
        WarmStartTrainer,
    )
    
    return {
        "CFR": (
            lambda: CFRTrainer(game, CFRConfig(use_plus=False, linear_weighting=False, alternating=False)),
            {"use_plus": False, "linear_weighting": False, "alternating": False},
        ),
        "CFR+": (
            lambda: CFRTrainer(game, CFRConfig(use_plus=True, linear_weighting=True, alternating=False)),
            {"use_plus": True, "linear_weighting": True, "alternating": False},
        ),
        "CFR+ (alt)": (
            lambda: CFRTrainer(game, CFRConfig(use_plus=True, linear_weighting=True, alternating=True)),
            {"use_plus": True, "linear_weighting": True, "alternating": True},
        ),
        "DCFR": (
            lambda: CFRTrainer(
                game,
                CFRConfig(use_plus=False, linear_weighting=False, alternating=False, use_dcfr=True, dcfr_alpha=1.5, dcfr_beta=0.0, dcfr_gamma=2.0),
            ),
            {"use_dcfr": True, "dcfr_alpha": 1.5, "dcfr_beta": 0.0, "dcfr_gamma": 2.0},
        ),
        "MCCFR": (
            lambda: ExternalSamplingMCCFRTrainer(game, MCCFRConfig(seed=7)),
            {"seed": 7},
        ),
        "FP": (
            lambda: FictitiousPlayTrainer(game, FPConfig(optimistic=False, linear_weighting=True, alternating=True)),
            {"optimistic": False, "linear_weighting": True, "alternating": True},
        ),
        "FP (opt)": (
            lambda: FictitiousPlayTrainer(game, FPConfig(optimistic=True, linear_weighting=True, alternating=True)),
            {"optimistic": True, "linear_weighting": True, "alternating": True},
        ),
        "Hybrid CFR+FP": (
            lambda: HybridCFRFPTrainer(game, HybridCFRFPConfig(switch_iteration=400)),
            {"switch_iteration": 400},
        ),
        "Adaptive CFR": (
            lambda: AdaptiveCFRTrainer(game, AdaptiveCFRConfig()),
            {"adaptive": True},
        ),
        "Warm-start": (
            lambda: WarmStartTrainer(game, WarmStartConfig(base_iterations=200, refinement_iterations=800)),
            {"base_iterations": 200, "refinement_iterations": 800},
        ),
    }
