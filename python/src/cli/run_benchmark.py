from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from experiments.benchmark import AlgorithmBenchmark, create_standard_benchmark_suite
from games.kuhn import KuhnPoker
from games.leduc import LeducPoker


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Comprehensive benchmark comparing poker solving algorithms."
    )
    parser.add_argument(
        "--game",
        default="kuhn",
        choices=("kuhn", "leduc"),
        help="Game to benchmark on.",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=None,
        help="Target exploitability threshold for time-to-target metrics.",
    )
    parser.add_argument(
        "--checkpoints",
        type=int,
        nargs="+",
        default=[25, 50, 100, 200, 400, 800, 1600],
        help="Iteration checkpoints for evaluation.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=None,
        help="Specific algorithms to benchmark (default: all).",
    )
    args = parser.parse_args()

    games = {
        "kuhn": KuhnPoker(),
        "leduc": LeducPoker(),
    }
    
    game = games[args.game]
    print(f"Benchmarking algorithms on {args.game} poker")
    print(f"Checkpoints: {args.checkpoints}")
    if args.target:
        print(f"Target exploitability: {args.target}")
    print()

    benchmark = AlgorithmBenchmark(
        game,
        checkpoints=args.checkpoints,
        target_exploitability=args.target,
    )

    all_algorithms = create_standard_benchmark_suite(game)
    
    if args.algorithms:
        algorithms = {k: v for k, v in all_algorithms.items() if k in args.algorithms}
        if not algorithms:
            print(f"No matching algorithms found. Available: {list(all_algorithms.keys())}")
            return
    else:
        algorithms = all_algorithms

    benchmark.compare_algorithms(algorithms)
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    best = benchmark.get_best_algorithm()
    print(f"\nBest Solution Quality: {best.name}")
    print(f"  Final exploitability: {best.final_exploitability:.6f}")
    
    fastest = benchmark.get_fastest_algorithm()
    print(f"\nFastest Convergence: {fastest.name}")
    print(f"  Convergence rate: {fastest.convergence_rate:.8f}")
    
    efficient = benchmark.get_most_efficient_algorithm()
    print(f"\nMost Time-Efficient: {efficient.name}")
    print(f"  Total time: {efficient.total_time:.3f}s")
    
    recommended = benchmark.recommend_algorithm()
    print(f"\nOverall Recommendation: {recommended.name}")
    print(f"  Balanced score across all metrics")
    print(f"  Final exploitability: {recommended.final_exploitability:.6f}")
    print(f"  Convergence rate: {recommended.convergence_rate:.8f}")
    print(f"  Total time: {recommended.total_time:.3f}s")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
