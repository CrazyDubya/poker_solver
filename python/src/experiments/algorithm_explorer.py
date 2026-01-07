from __future__ import annotations

import itertools
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from algorithms.cfr import CFRConfig, CFRTrainer
from algorithms.evaluation import exploitability
from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig


@dataclass
class ExperimentResult:
    algorithm: str
    config: Dict[str, Any]
    exploitability_history: Dict[int, float]
    final_exploitability: float
    iterations: int
    time_elapsed: float
    convergence_rate: float


@dataclass
class ExperimentPath:
    """Represents a path through the algorithm parameter space."""
    path_id: str
    configs: List[Dict[str, Any]]
    results: List[ExperimentResult]
    best_result: ExperimentResult | None = None


class AlgorithmExplorer:
    """Multi-path branching algorithm explorer for poker solvers.
    
    This class implements a systematic exploration of algorithm variants,
    testing different configurations and parameter combinations to find
    optimal convergence properties for river poker solving.
    """

    def __init__(self, game, checkpoints: List[int] | None = None) -> None:
        self.game = game
        self.checkpoints = checkpoints or [25, 50, 100, 200, 400, 800, 1600]
        self.paths: List[ExperimentPath] = []
        self.all_results: List[ExperimentResult] = []

    def _run_experiment(
        self,
        trainer_factory: Callable,
        algo_name: str,
        config_dict: Dict[str, Any],
        target_iters: int,
    ) -> ExperimentResult:
        """Run a single experiment with given configuration."""
        trainer = trainer_factory()
        start_time = time.time()
        exploitability_history = {}
        completed = 0

        for checkpoint in self.checkpoints:
            if checkpoint > target_iters:
                break
            trainer.run(checkpoint - completed)
            completed = checkpoint
            profile = trainer.average_strategy_profile()
            exp_value = exploitability(self.game, profile)
            exploitability_history[checkpoint] = exp_value

        time_elapsed = time.time() - start_time
        final_exp = exploitability_history[completed]
        
        # Calculate convergence rate (exploitability decrease per iteration)
        if len(exploitability_history) > 1:
            checkpoints_list = sorted(exploitability_history.keys())
            initial = exploitability_history[checkpoints_list[0]]
            final = exploitability_history[checkpoints_list[-1]]
            iters = checkpoints_list[-1] - checkpoints_list[0]
            convergence_rate = (initial - final) / iters if iters > 0 else 0.0
        else:
            convergence_rate = 0.0

        return ExperimentResult(
            algorithm=algo_name,
            config=config_dict,
            exploitability_history=exploitability_history,
            final_exploitability=final_exp,
            iterations=completed,
            time_elapsed=time_elapsed,
            convergence_rate=convergence_rate,
        )

    def explore_cfr_variants(self, target_iters: int = 1600) -> List[ExperimentPath]:
        """Explore CFR algorithm variants with different configurations.
        
        Tests combinations of:
        - CFR vs CFR+ (regret matching variants)
        - Linear weighting vs uniform
        - Alternating vs simultaneous updates
        - DCFR with different discount parameters
        """
        paths = []
        
        # Path 1: Basic CFR variations
        path1_configs = []
        for use_plus in [False, True]:
            for linear in [False, True]:
                for alternating in [False, True]:
                    config_dict = {
                        "use_plus": use_plus,
                        "linear_weighting": linear,
                        "alternating": alternating,
                        "use_dcfr": False,
                    }
                    path1_configs.append(config_dict)
        
        path1 = ExperimentPath(path_id="cfr_basic", configs=path1_configs, results=[])
        for config_dict in path1_configs:
            config = CFRConfig(**config_dict)
            result = self._run_experiment(
                lambda: CFRTrainer(self.game, config),
                "cfr" if not config.use_plus else "cfr+",
                config_dict,
                target_iters,
            )
            path1.results.append(result)
        
        path1.best_result = min(path1.results, key=lambda r: r.final_exploitability)
        paths.append(path1)
        self.all_results.extend(path1.results)

        # Path 2: DCFR parameter sweep
        path2_configs = []
        alpha_values = [1.0, 1.5, 2.0, 3.0]
        beta_values = [0.0, 0.5, 1.0]
        gamma_values = [1.5, 2.0, 2.5]
        
        for alpha, beta, gamma in itertools.product(alpha_values, beta_values, gamma_values):
            config_dict = {
                "use_plus": False,
                "linear_weighting": False,
                "alternating": False,
                "use_dcfr": True,
                "dcfr_alpha": alpha,
                "dcfr_beta": beta,
                "dcfr_gamma": gamma,
            }
            path2_configs.append(config_dict)
        
        path2 = ExperimentPath(path_id="dcfr_sweep", configs=path2_configs, results=[])
        for config_dict in path2_configs:
            config = CFRConfig(**config_dict)
            result = self._run_experiment(
                lambda: CFRTrainer(self.game, config),
                "dcfr",
                config_dict,
                target_iters,
            )
            path2.results.append(result)
        
        path2.best_result = min(path2.results, key=lambda r: r.final_exploitability)
        paths.append(path2)
        self.all_results.extend(path2.results)

        self.paths.extend(paths)
        return paths

    def explore_fp_variants(self, target_iters: int = 1600) -> List[ExperimentPath]:
        """Explore Fictitious Play variants.
        
        Tests combinations of:
        - Optimistic vs standard FP
        - Linear weighting vs uniform
        - Alternating vs simultaneous best response
        """
        path_configs = []
        for optimistic in [False, True]:
            for linear in [False, True]:
                for alternating in [False, True]:
                    config_dict = {
                        "optimistic": optimistic,
                        "linear_weighting": linear,
                        "alternating": alternating,
                    }
                    path_configs.append(config_dict)
        
        path = ExperimentPath(path_id="fp_variants", configs=path_configs, results=[])
        for config_dict in path_configs:
            config = FPConfig(**config_dict)
            result = self._run_experiment(
                lambda: FictitiousPlayTrainer(self.game, config),
                "fp",
                config_dict,
                target_iters,
            )
            path.results.append(result)
        
        path.best_result = min(path.results, key=lambda r: r.final_exploitability)
        self.paths.append(path)
        self.all_results.extend(path.results)
        return [path]

    def explore_mccfr_variants(self, target_iters: int = 1600) -> List[ExperimentPath]:
        """Explore Monte Carlo CFR with different random seeds.
        
        Tests MCCFR convergence stability across multiple runs.
        """
        path_configs = []
        seeds = [7, 42, 123, 456, 789, 1337, 9999]
        
        for seed in seeds:
            config_dict = {"seed": seed}
            path_configs.append(config_dict)
        
        path = ExperimentPath(path_id="mccfr_seeds", configs=path_configs, results=[])
        for config_dict in path_configs:
            config = MCCFRConfig(**config_dict)
            result = self._run_experiment(
                lambda: ExternalSamplingMCCFRTrainer(self.game, config),
                "mccfr",
                config_dict,
                target_iters,
            )
            path.results.append(result)
        
        path.best_result = min(path.results, key=lambda r: r.final_exploitability)
        self.paths.append(path)
        self.all_results.extend(path.results)
        return [path]

    def get_best_overall(self) -> ExperimentResult:
        """Return the best result across all experiments."""
        if not self.all_results:
            raise ValueError("No experiments have been run yet")
        return min(self.all_results, key=lambda r: r.final_exploitability)

    def get_fastest_convergence(self) -> ExperimentResult:
        """Return the result with the fastest convergence rate."""
        if not self.all_results:
            raise ValueError("No experiments have been run yet")
        return max(self.all_results, key=lambda r: r.convergence_rate)

    def get_most_efficient(self) -> ExperimentResult:
        """Return the most time-efficient result (best exploitability per second)."""
        if not self.all_results:
            raise ValueError("No experiments have been run yet")
        return min(
            self.all_results,
            key=lambda r: r.final_exploitability * r.time_elapsed,
        )

    def branch_from_best(self, num_branches: int = 5) -> List[ExperimentPath]:
        """Branch from the best result to explore nearby configurations.
        
        This implements the "backing up and retraversing" mentioned in the problem,
        where we start from good configurations and explore variations.
        """
        if not self.all_results:
            raise ValueError("No experiments to branch from")
        
        best = self.get_best_overall()
        branches = []
        
        # Create variations of the best configuration
        base_config = best.config.copy()
        
        # Branch 1: Tweak numerical parameters slightly
        if "dcfr_alpha" in base_config:
            branch_configs = []
            alpha = base_config["dcfr_alpha"]
            beta = base_config["dcfr_beta"]
            gamma = base_config["dcfr_gamma"]
            
            # Explore nearby parameter space
            for alpha_delta in [-0.5, -0.25, 0.25, 0.5]:
                for gamma_delta in [-0.25, 0.25]:
                    new_config = base_config.copy()
                    new_config["dcfr_alpha"] = max(0.5, alpha + alpha_delta)
                    new_config["dcfr_gamma"] = max(1.0, gamma + gamma_delta)
                    branch_configs.append(new_config)
            
            path = ExperimentPath(
                path_id=f"branch_from_{best.algorithm}",
                configs=branch_configs,
                results=[],
            )
            
            for config_dict in branch_configs[:num_branches]:
                config = CFRConfig(**config_dict)
                result = self._run_experiment(
                    lambda: CFRTrainer(self.game, config),
                    best.algorithm,
                    config_dict,
                    self.checkpoints[-1],
                )
                path.results.append(result)
            
            if path.results:
                path.best_result = min(path.results, key=lambda r: r.final_exploitability)
                branches.append(path)
                self.paths.append(path)
                self.all_results.extend(path.results)
        
        # Branch 2: Toggle boolean parameters
        branch2_configs = []
        for key, value in base_config.items():
            if isinstance(value, bool):
                new_config = base_config.copy()
                new_config[key] = not value
                branch2_configs.append(new_config)
        
        if branch2_configs:
            path2 = ExperimentPath(
                path_id=f"branch_toggles_{best.algorithm}",
                configs=branch2_configs,
                results=[],
            )
            
            for config_dict in branch2_configs:
                if "dcfr_alpha" in config_dict:
                    config = CFRConfig(**config_dict)
                    trainer_factory = lambda: CFRTrainer(self.game, config)
                elif "seed" in config_dict:
                    config = MCCFRConfig(**config_dict)
                    trainer_factory = lambda: ExternalSamplingMCCFRTrainer(self.game, config)
                else:
                    config = FPConfig(**config_dict)
                    trainer_factory = lambda: FictitiousPlayTrainer(self.game, config)
                
                result = self._run_experiment(
                    trainer_factory,
                    best.algorithm,
                    config_dict,
                    self.checkpoints[-1],
                )
                path2.results.append(result)
            
            if path2.results:
                path2.best_result = min(path2.results, key=lambda r: r.final_exploitability)
                branches.append(path2)
                self.paths.append(path2)
                self.all_results.extend(path2.results)
        
        return branches

    def save_results(self, output_path: Path) -> None:
        """Save all experiment results to JSON."""
        data = {
            "paths": [
                {
                    "path_id": path.path_id,
                    "num_configs": len(path.configs),
                    "best_exploitability": path.best_result.final_exploitability if path.best_result else None,
                    "best_config": path.best_result.config if path.best_result else None,
                }
                for path in self.paths
            ],
            "all_results": [
                {
                    "algorithm": r.algorithm,
                    "config": r.config,
                    "final_exploitability": r.final_exploitability,
                    "iterations": r.iterations,
                    "time_elapsed": r.time_elapsed,
                    "convergence_rate": r.convergence_rate,
                    "exploitability_history": {str(k): v for k, v in r.exploitability_history.items()},
                }
                for r in self.all_results
            ],
            "summary": {
                "total_experiments": len(self.all_results),
                "best_overall": {
                    "algorithm": self.get_best_overall().algorithm,
                    "config": self.get_best_overall().config,
                    "exploitability": self.get_best_overall().final_exploitability,
                },
                "fastest_convergence": {
                    "algorithm": self.get_fastest_convergence().algorithm,
                    "config": self.get_fastest_convergence().config,
                    "convergence_rate": self.get_fastest_convergence().convergence_rate,
                },
                "most_efficient": {
                    "algorithm": self.get_most_efficient().algorithm,
                    "config": self.get_most_efficient().config,
                    "efficiency": self.get_most_efficient().final_exploitability * self.get_most_efficient().time_elapsed,
                },
            },
        }
        
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def print_summary(self) -> None:
        """Print a summary of all experiments."""
        print("\n" + "=" * 80)
        print("ALGORITHM EXPLORATION SUMMARY")
        print("=" * 80)
        print(f"\nTotal experiments run: {len(self.all_results)}")
        print(f"Total paths explored: {len(self.paths)}")
        
        print("\n--- Best Overall Performance ---")
        best = self.get_best_overall()
        print(f"Algorithm: {best.algorithm}")
        print(f"Config: {best.config}")
        print(f"Final Exploitability: {best.final_exploitability:.6f}")
        print(f"Iterations: {best.iterations}")
        print(f"Time: {best.time_elapsed:.2f}s")
        
        print("\n--- Fastest Convergence ---")
        fastest = self.get_fastest_convergence()
        print(f"Algorithm: {fastest.algorithm}")
        print(f"Config: {fastest.config}")
        print(f"Convergence Rate: {fastest.convergence_rate:.8f} exp/iter")
        print(f"Final Exploitability: {fastest.final_exploitability:.6f}")
        
        print("\n--- Most Time-Efficient ---")
        efficient = self.get_most_efficient()
        print(f"Algorithm: {efficient.algorithm}")
        print(f"Config: {efficient.config}")
        print(f"Efficiency Score: {efficient.final_exploitability * efficient.time_elapsed:.6f}")
        print(f"Time: {efficient.time_elapsed:.2f}s")
        
        print("\n--- Path Summaries ---")
        for path in self.paths:
            print(f"\nPath: {path.path_id}")
            print(f"  Configurations tested: {len(path.configs)}")
            if path.best_result:
                print(f"  Best exploitability: {path.best_result.final_exploitability:.6f}")
                print(f"  Best config: {path.best_result.config}")
        
        print("\n" + "=" * 80)
