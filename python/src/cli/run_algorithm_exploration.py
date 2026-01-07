from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from experiments.algorithm_explorer import AlgorithmExplorer
from games.kuhn import KuhnPoker
from games.leduc import LeducPoker


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Systematic algorithm exploration using multi-path branching."
    )
    parser.add_argument(
        "--game",
        default="kuhn",
        choices=("kuhn", "leduc"),
        help="Game to use for testing.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=800,
        help="Target iterations for experiments.",
    )
    parser.add_argument(
        "--explore",
        nargs="+",
        default=["cfr", "fp", "mccfr"],
        choices=("cfr", "fp", "mccfr", "all"),
        help="Algorithm families to explore.",
    )
    parser.add_argument(
        "--branch",
        action="store_true",
        help="After initial exploration, branch from best results.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON file for results.",
    )
    args = parser.parse_args()

    if "all" in args.explore:
        args.explore = ["cfr", "fp", "mccfr"]

    games = {
        "kuhn": KuhnPoker(),
        "leduc": LeducPoker(),
    }
    
    game = games[args.game]
    print(f"Starting algorithm exploration on {args.game} poker")
    print(f"Target iterations: {args.iterations}")
    print(f"Exploring: {', '.join(args.explore)}")
    print()

    explorer = AlgorithmExplorer(game, checkpoints=[25, 50, 100, 200, 400, 800, 1600])

    if "cfr" in args.explore:
        print("=" * 80)
        print("EXPLORING CFR VARIANTS")
        print("=" * 80)
        cfr_paths = explorer.explore_cfr_variants(target_iters=args.iterations)
        for path in cfr_paths:
            print(f"\nPath: {path.path_id}")
            print(f"  Tested {len(path.results)} configurations")
            if path.best_result:
                print(f"  Best: {path.best_result.final_exploitability:.6f}")
                print(f"  Config: {path.best_result.config}")

    if "fp" in args.explore:
        print("\n" + "=" * 80)
        print("EXPLORING FICTITIOUS PLAY VARIANTS")
        print("=" * 80)
        fp_paths = explorer.explore_fp_variants(target_iters=args.iterations)
        for path in fp_paths:
            print(f"\nPath: {path.path_id}")
            print(f"  Tested {len(path.results)} configurations")
            if path.best_result:
                print(f"  Best: {path.best_result.final_exploitability:.6f}")
                print(f"  Config: {path.best_result.config}")

    if "mccfr" in args.explore:
        print("\n" + "=" * 80)
        print("EXPLORING MCCFR VARIANTS")
        print("=" * 80)
        mccfr_paths = explorer.explore_mccfr_variants(target_iters=args.iterations)
        for path in mccfr_paths:
            print(f"\nPath: {path.path_id}")
            print(f"  Tested {len(path.results)} configurations")
            if path.best_result:
                print(f"  Best: {path.best_result.final_exploitability:.6f}")
                print(f"  Config: {path.best_result.config}")

    if args.branch:
        print("\n" + "=" * 80)
        print("BRANCHING FROM BEST RESULTS")
        print("=" * 80)
        branches = explorer.branch_from_best(num_branches=10)
        for branch in branches:
            print(f"\nBranch: {branch.path_id}")
            print(f"  Tested {len(branch.results)} configurations")
            if branch.best_result:
                print(f"  Best: {branch.best_result.final_exploitability:.6f}")
                print(f"  Config: {branch.best_result.config}")

    explorer.print_summary()

    if args.output:
        explorer.save_results(args.output)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
