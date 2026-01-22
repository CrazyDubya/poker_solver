#!/usr/bin/env python3
"""
Algorithm Tournament Runner

Comprehensive tournament framework for comparing poker solving algorithms
using multi-path branching and adaptive strategies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.algorithm_tournament import AdaptiveSolver, AlgorithmTournament
from algorithms.cfr import CFRConfig, CFRTrainer
from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig
from games.kuhn import KuhnPoker
from games.leduc import LeducPoker


def run_comprehensive_tournament(game, game_name: str, output_dir: Path | None = None) -> None:
    """Run comprehensive tournament with all algorithm variants."""
    print(f"\n{'=' * 80}")
    print(f"COMPREHENSIVE ALGORITHM TOURNAMENT: {game_name}")
    print(f"{'=' * 80}\n")

    tournament = AlgorithmTournament(game)

    # Add all CFR variants
    tournament.add_cfr_variants()

    # Add all FP variants
    tournament.add_fp_variants()

    # Add MCCFR variants
    tournament.add_mccfr_variants()

    # Run tournament
    result = tournament.run_tournament(verbose=True)

    # Print results
    tournament.print_results(result)

    # Save if output directory specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{game_name}_tournament_results.json"
        tournament.save_results(result, str(filepath))


def run_focused_tournament(
    game, game_name: str, focus: str, output_dir: Path | None = None
) -> None:
    """Run focused tournament on specific algorithm family."""
    print(f"\n{'=' * 80}")
    print(f"FOCUSED TOURNAMENT ({focus.upper()}): {game_name}")
    print(f"{'=' * 80}\n")

    tournament = AlgorithmTournament(game)

    if focus == "cfr":
        tournament.add_cfr_variants()
    elif focus == "fp":
        tournament.add_fp_variants()
    elif focus == "mccfr":
        tournament.add_mccfr_variants()
    else:
        raise ValueError(f"Unknown focus: {focus}")

    result = tournament.run_tournament(verbose=True)
    tournament.print_results(result)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{game_name}_{focus}_tournament_results.json"
        tournament.save_results(result, str(filepath))


def run_adaptive_solver(game, game_name: str, max_iterations: int = 1600) -> None:
    """Run adaptive solver that switches between algorithms."""
    print(f"\n{'=' * 80}")
    print(f"ADAPTIVE SOLVER: {game_name}")
    print(f"{'=' * 80}\n")

    solver = AdaptiveSolver(game, evaluation_interval=100, switch_threshold=1.3)

    # Add top performing algorithm candidates
    solver.add_algorithm_candidate(
        "cfr+_alt", lambda: CFRTrainer(game, CFRConfig(use_plus=True, alternating=True))
    )
    solver.add_algorithm_candidate(
        "cfr+_linear_alt",
        lambda: CFRTrainer(
            game, CFRConfig(use_plus=True, linear_weighting=True, alternating=True)
        ),
    )
    solver.add_algorithm_candidate(
        "dcfr_default",
        lambda: CFRTrainer(
            game,
            CFRConfig(use_dcfr=True, dcfr_alpha=1.5, dcfr_beta=0.0, dcfr_gamma=2.0),
        ),
    )
    solver.add_algorithm_candidate(
        "fp_linear_alt",
        lambda: FictitiousPlayTrainer(
            game, FPConfig(linear_weighting=True, alternating=True)
        ),
    )

    # Run adaptive solver
    final_profile = solver.run_adaptive(max_iterations=max_iterations, verbose=True)

    # Print history
    print(f"\n{'=' * 80}")
    print("Adaptive Solver History:")
    print(f"{'=' * 80}")
    for iters, algo, exp in solver.history:
        print(f"  Iteration {iters:4d}: {algo:<20} exp={exp:.6f}")
    print()


def run_parameter_sweep(game, game_name: str) -> None:
    """Run parameter sweep for DCFR to find optimal parameters."""
    print(f"\n{'=' * 80}")
    print(f"DCFR PARAMETER SWEEP: {game_name}")
    print(f"{'=' * 80}\n")

    tournament = AlgorithmTournament(game, iterations=[100, 400, 1600])

    # Sweep alpha values
    for alpha in [1.0, 1.5, 2.0, 2.5, 3.0]:
        tournament.add_algorithm(
            f"dcfr_a{alpha}",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": alpha,
                "dcfr_beta": 0.0,
                "dcfr_gamma": 2.0,
            },
            f"DCFR with alpha={alpha}",
        )

    # Sweep gamma values
    for gamma in [1.0, 1.5, 2.0, 2.5, 3.0]:
        tournament.add_algorithm(
            f"dcfr_g{gamma}",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": 1.5,
                "dcfr_beta": 0.0,
                "dcfr_gamma": gamma,
            },
            f"DCFR with gamma={gamma}",
        )

    # Sweep beta values
    for beta in [0.0, 0.25, 0.5, 0.75, 1.0]:
        tournament.add_algorithm(
            f"dcfr_b{beta}",
            "cfr",
            {
                "use_plus": False,
                "use_dcfr": True,
                "dcfr_alpha": 1.5,
                "dcfr_beta": beta,
                "dcfr_gamma": 2.0,
            },
            f"DCFR with beta={beta}",
        )

    result = tournament.run_tournament(verbose=True)
    tournament.print_results(result)


def run_hybrid_analysis(game, game_name: str) -> None:
    """Analyze hybrid approaches combining multiple algorithms."""
    print(f"\n{'=' * 80}")
    print(f"HYBRID ALGORITHM ANALYSIS: {game_name}")
    print(f"{'=' * 80}\n")

    # This would involve running different algorithms in sequence
    # or combining their strategies. For now, we'll document the concept.

    print("Hybrid approach concept:")
    print("1. Start with fast-converging FP for initial phase")
    print("2. Switch to CFR+ for refinement")
    print("3. Finish with DCFR for final optimization")
    print("\nThis requires additional implementation...")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run comprehensive algorithm tournaments and analysis"
    )
    parser.add_argument(
        "--game",
        default="kuhn",
        choices=["kuhn", "leduc", "all"],
        help="Game to test on",
    )
    parser.add_argument(
        "--mode",
        default="comprehensive",
        choices=[
            "comprehensive",
            "focused",
            "adaptive",
            "parameter_sweep",
            "hybrid",
        ],
        help="Tournament mode",
    )
    parser.add_argument(
        "--focus",
        default="cfr",
        choices=["cfr", "fp", "mccfr"],
        help="Focus for focused tournament",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save results",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1600,
        help="Maximum iterations for adaptive solver",
    )

    args = parser.parse_args()

    games = {}
    if args.game == "all":
        games["kuhn"] = KuhnPoker()
        games["leduc"] = LeducPoker()
    elif args.game == "kuhn":
        games["kuhn"] = KuhnPoker()
    elif args.game == "leduc":
        games["leduc"] = LeducPoker()

    for game_name, game in games.items():
        if args.mode == "comprehensive":
            run_comprehensive_tournament(game, game_name, args.output_dir)
        elif args.mode == "focused":
            run_focused_tournament(game, game_name, args.focus, args.output_dir)
        elif args.mode == "adaptive":
            run_adaptive_solver(game, game_name, args.max_iterations)
        elif args.mode == "parameter_sweep":
            run_parameter_sweep(game, game_name)
        elif args.mode == "hybrid":
            run_hybrid_analysis(game, game_name)


if __name__ == "__main__":
    main()
