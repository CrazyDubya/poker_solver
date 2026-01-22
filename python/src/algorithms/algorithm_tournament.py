"""
Algorithm Tournament Framework

This module implements a comprehensive framework for comparing different poker
solving algorithms using a multi-path branching approach. It tests various
algorithm configurations, tracks convergence, and identifies optimal strategies.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from algorithms.cfr import CFRConfig, CFRTrainer
from algorithms.evaluation import exploitability
from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig


@dataclass
class AlgorithmConfig:
    """Configuration for an algorithm variant."""

    name: str
    algorithm_type: str
    config: Dict[str, Any]
    description: str = ""


@dataclass
class ConvergenceResult:
    """Results from running an algorithm to convergence."""

    algorithm_name: str
    iterations: int
    exploitability: float
    time_elapsed: float
    final_strategy: Dict[str, Dict[str, float]]


@dataclass
class TournamentResult:
    """Complete results from an algorithm tournament."""

    game_name: str
    algorithms: List[str]
    iterations_tested: List[int]
    exploitability_matrix: Dict[str, List[float]]  # algorithm -> exploitabilities
    time_matrix: Dict[str, List[float]]  # algorithm -> times
    convergence_rates: Dict[str, float]  # algorithm -> avg rate
    winner: str
    winner_final_exp: float


class AlgorithmTournament:
    """
    Tournament framework for comparing poker solving algorithms.

    Uses a multi-path approach to test different algorithm configurations
    and identify the best performing variants.
    """

    def __init__(self, game, iterations: List[int] | None = None) -> None:
        """
        Initialize tournament with a game and iteration checkpoints.

        Args:
            game: Game instance (KuhnPoker, LeducPoker, etc.)
            iterations: List of iteration counts to test at. Defaults to
                       [25, 50, 100, 200, 400, 800, 1600]
        """
        self.game = game
        self.iterations = iterations or [25, 50, 100, 200, 400, 800, 1600]
        self.algorithms: List[AlgorithmConfig] = []
        self.results: List[ConvergenceResult] = []

    def add_algorithm(
        self,
        name: str,
        algorithm_type: str,
        config: Dict[str, Any],
        description: str = "",
    ) -> None:
        """
        Add an algorithm variant to the tournament.

        Args:
            name: Display name for this variant
            algorithm_type: Type of algorithm (cfr, cfr+, dcfr, mccfr, fp)
            config: Configuration parameters
            description: Human-readable description
        """
        self.algorithms.append(
            AlgorithmConfig(
                name=name,
                algorithm_type=algorithm_type,
                config=config,
                description=description,
            )
        )

    def add_cfr_variants(self) -> None:
        """Add common CFR variants to the tournament."""
        # Vanilla CFR
        self.add_algorithm(
            "cfr",
            "cfr",
            {"use_plus": False, "linear_weighting": False, "alternating": False},
            "Vanilla CFR",
        )

        # CFR+ variants
        self.add_algorithm(
            "cfr+",
            "cfr",
            {"use_plus": True, "linear_weighting": False, "alternating": False},
            "CFR+ without linear weighting",
        )
        self.add_algorithm(
            "cfr+_linear",
            "cfr",
            {"use_plus": True, "linear_weighting": True, "alternating": False},
            "CFR+ with linear weighting",
        )
        self.add_algorithm(
            "cfr+_alt",
            "cfr",
            {"use_plus": True, "linear_weighting": False, "alternating": True},
            "CFR+ with alternating updates",
        )
        self.add_algorithm(
            "cfr+_linear_alt",
            "cfr",
            {"use_plus": True, "linear_weighting": True, "alternating": True},
            "CFR+ with linear weighting and alternating updates",
        )

        # DCFR variants with different parameters
        self.add_algorithm(
            "dcfr_default",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": 1.5,
                "dcfr_beta": 0.0,
                "dcfr_gamma": 2.0,
            },
            "DCFR with default parameters",
        )
        self.add_algorithm(
            "dcfr_aggressive",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": 2.0,
                "dcfr_beta": 0.5,
                "dcfr_gamma": 2.5,
            },
            "DCFR with more aggressive discounting",
        )
        self.add_algorithm(
            "dcfr_conservative",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": 1.0,
                "dcfr_beta": 0.0,
                "dcfr_gamma": 1.5,
            },
            "DCFR with conservative discounting",
        )

    def add_fp_variants(self) -> None:
        """Add Fictitious Play variants to the tournament."""
        self.add_algorithm(
            "fp",
            "fp",
            {"optimistic": False, "linear_weighting": False, "alternating": False},
            "Vanilla Fictitious Play",
        )
        self.add_algorithm(
            "fp_opt",
            "fp",
            {"optimistic": True, "linear_weighting": False, "alternating": False},
            "Optimistic FP",
        )
        self.add_algorithm(
            "fp_linear",
            "fp",
            {"optimistic": False, "linear_weighting": True, "alternating": False},
            "FP with linear weighting",
        )
        self.add_algorithm(
            "fp_alt",
            "fp",
            {"optimistic": False, "linear_weighting": False, "alternating": True},
            "FP with alternating updates",
        )
        self.add_algorithm(
            "fp_linear_alt",
            "fp",
            {"optimistic": False, "linear_weighting": True, "alternating": True},
            "FP with linear weighting and alternating",
        )
        self.add_algorithm(
            "fp_opt_linear_alt",
            "fp",
            {"optimistic": True, "linear_weighting": True, "alternating": True},
            "Optimistic FP with linear and alternating",
        )

    def add_mccfr_variants(self) -> None:
        """Add Monte Carlo CFR variants with different seeds."""
        for seed in [7, 42, 123]:
            self.add_algorithm(
                f"mccfr_seed{seed}",
                "mccfr",
                {"seed": seed},
                f"External Sampling MCCFR with seed {seed}",
            )

    def _create_trainer(self, algo_config: AlgorithmConfig):
        """Create a trainer instance from algorithm configuration."""
        if algo_config.algorithm_type == "cfr":
            config = CFRConfig(**algo_config.config)
            return CFRTrainer(self.game, config)
        elif algo_config.algorithm_type == "fp":
            config = FPConfig(**algo_config.config)
            return FictitiousPlayTrainer(self.game, config)
        elif algo_config.algorithm_type == "mccfr":
            config = MCCFRConfig(**algo_config.config)
            return ExternalSamplingMCCFRTrainer(self.game, config)
        else:
            raise ValueError(f"Unknown algorithm type: {algo_config.algorithm_type}")

    def run_algorithm(
        self, algo_config: AlgorithmConfig, verbose: bool = True
    ) -> Tuple[List[float], List[float], Dict[str, Dict[str, float]]]:
        """
        Run a single algorithm through all iteration checkpoints.

        Args:
            algo_config: Algorithm configuration to test
            verbose: Whether to print progress

        Returns:
            Tuple of (exploitabilities, times, final_strategy)
        """
        if verbose:
            print(f"  Running {algo_config.name}...", end="", flush=True)

        trainer = self._create_trainer(algo_config)
        exploitabilities = []
        times = []
        completed = 0
        final_strategy = None

        for target_iters in self.iterations:
            iters_to_run = target_iters - completed
            start_time = time.time()
            trainer.run(iters_to_run)
            elapsed = time.time() - start_time

            profile = trainer.average_strategy_profile()
            exp = exploitability(self.game, profile)

            exploitabilities.append(exp)
            times.append(elapsed)
            completed = target_iters
            final_strategy = profile

        if verbose:
            print(f" done. Final exp: {exploitabilities[-1]:.6f}")

        return exploitabilities, times, final_strategy

    def run_tournament(self, verbose: bool = True) -> TournamentResult:
        """
        Run the complete tournament with all registered algorithms.

        Args:
            verbose: Whether to print progress

        Returns:
            TournamentResult with complete performance data
        """
        if verbose:
            print(f"Starting tournament with {len(self.algorithms)} algorithms...")

        exp_matrix = {}
        time_matrix = {}
        convergence_rates = {}

        for algo_config in self.algorithms:
            exploitabilities, times, final_strategy = self.run_algorithm(
                algo_config, verbose
            )
            exp_matrix[algo_config.name] = exploitabilities
            time_matrix[algo_config.name] = times

            # Calculate convergence rate (improvement per iteration)
            if len(exploitabilities) >= 2:
                initial = exploitabilities[0]
                final = exploitabilities[-1]
                total_iters = self.iterations[-1]
                convergence_rates[algo_config.name] = (initial - final) / total_iters
            else:
                convergence_rates[algo_config.name] = 0.0

        # Find winner (lowest final exploitability)
        winner = min(exp_matrix.keys(), key=lambda k: exp_matrix[k][-1])
        winner_final_exp = exp_matrix[winner][-1]

        if verbose:
            print(f"\nTournament complete. Winner: {winner}")

        return TournamentResult(
            game_name=self.game.__class__.__name__,
            algorithms=list(exp_matrix.keys()),
            iterations_tested=self.iterations,
            exploitability_matrix=exp_matrix,
            time_matrix=time_matrix,
            convergence_rates=convergence_rates,
            winner=winner,
            winner_final_exp=winner_final_exp,
        )

    def print_results(self, result: TournamentResult) -> None:
        """Print formatted tournament results."""
        print(f"\n{'=' * 80}")
        print(f"Tournament Results: {result.game_name}")
        print(f"{'=' * 80}\n")

        # Print header
        print(f"{'Algorithm':<25}", end="")
        for iters in result.iterations_tested:
            print(f"{iters:>10}", end="")
        print(f"{'Conv Rate':>12}")

        # Print separator
        print("-" * 80)

        # Print each algorithm's results
        for algo_name in result.algorithms:
            exploitabilities = result.exploitability_matrix[algo_name]
            conv_rate = result.convergence_rates[algo_name]

            print(f"{algo_name:<25}", end="")
            for exp in exploitabilities:
                print(f"{exp:>10.6f}", end="")
            print(f"{conv_rate:>12.8f}")

        # Print winner
        print(f"\n{'=' * 80}")
        print(f"Winner: {result.winner} (final exploitability: {result.winner_final_exp:.6f})")
        print(f"{'=' * 80}\n")

    def save_results(self, result: TournamentResult, filepath: str) -> None:
        """Save tournament results to JSON file."""
        data = {
            "game_name": result.game_name,
            "algorithms": result.algorithms,
            "iterations_tested": result.iterations_tested,
            "exploitability_matrix": result.exploitability_matrix,
            "time_matrix": result.time_matrix,
            "convergence_rates": result.convergence_rates,
            "winner": result.winner,
            "winner_final_exp": result.winner_final_exp,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Results saved to {filepath}")


class AdaptiveSolver:
    """
    Adaptive solver that switches between algorithms based on convergence.

    This implements a multi-path branching strategy that tries different
    algorithms and adaptively switches to the best performing one.
    """

    def __init__(
        self,
        game,
        evaluation_interval: int = 100,
        switch_threshold: float = 1.5,
    ) -> None:
        """
        Initialize adaptive solver.

        Args:
            game: Game instance
            evaluation_interval: How often to evaluate and potentially switch
            switch_threshold: Switch if another algorithm is this many times better
        """
        self.game = game
        self.evaluation_interval = evaluation_interval
        self.switch_threshold = switch_threshold
        self.algorithm_configs = []
        self.current_trainer = None
        self.current_config = None
        self.history = []

    def add_algorithm_candidate(
        self, name: str, trainer_factory: Callable
    ) -> None:
        """Add an algorithm as a candidate for adaptive switching."""
        self.algorithm_configs.append((name, trainer_factory))

    def run_adaptive(
        self, max_iterations: int, target_exp: float | None = None, verbose: bool = True
    ) -> Dict[str, Dict[str, float]]:
        """
        Run adaptive solver that switches between algorithms.

        Args:
            max_iterations: Maximum total iterations
            target_exp: Stop if exploitability reaches this threshold
            verbose: Whether to print progress

        Returns:
            Final average strategy profile
        """
        if not self.algorithm_configs:
            raise ValueError("No algorithm candidates added")

        # Initialize with first algorithm
        current_name, trainer_factory = self.algorithm_configs[0]
        self.current_trainer = trainer_factory()
        self.current_config = current_name

        completed = 0

        if verbose:
            print(f"Starting adaptive solver with {len(self.algorithm_configs)} candidates")
            print(f"Initial algorithm: {current_name}\n")

        while completed < max_iterations:
            # Run current algorithm for evaluation_interval iterations
            iters_to_run = min(self.evaluation_interval, max_iterations - completed)
            self.current_trainer.run(iters_to_run)
            completed += iters_to_run

            # Evaluate current strategy
            profile = self.current_trainer.average_strategy_profile()
            current_exp = exploitability(self.game, profile)

            if verbose:
                print(
                    f"Iteration {completed}: {self.current_config} exp={current_exp:.6f}"
                )

            self.history.append((completed, self.current_config, current_exp))

            # Check if we've reached target
            if target_exp is not None and current_exp <= target_exp:
                if verbose:
                    print(f"\nReached target exploitability {target_exp}")
                break

            # Periodically evaluate switching to another algorithm
            if completed % (self.evaluation_interval * 3) == 0 and completed < max_iterations:
                best_alternative = None
                best_exp = current_exp

                # Test each alternative for a short run
                for name, trainer_factory in self.algorithm_configs:
                    if name == self.current_config:
                        continue

                    # Create fresh trainer and warm-start with current strategy if possible
                    test_trainer = trainer_factory()
                    test_trainer.run(self.evaluation_interval // 2)
                    test_profile = test_trainer.average_strategy_profile()
                    test_exp = exploitability(self.game, test_profile)

                    if test_exp < best_exp / self.switch_threshold:
                        best_alternative = (name, trainer_factory)
                        best_exp = test_exp

                # Switch if found better alternative
                if best_alternative is not None:
                    old_config = self.current_config
                    self.current_config = best_alternative[0]
                    self.current_trainer = best_alternative[1]()

                    if verbose:
                        print(
                            f"  -> Switching from {old_config} to {self.current_config} "
                            f"(exp: {current_exp:.6f} -> {best_exp:.6f})"
                        )

        return profile
