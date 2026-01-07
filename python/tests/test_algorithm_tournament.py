"""
Tests for Algorithm Tournament Framework

Tests the multi-path algorithm comparison and search functionality.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from algorithms.algorithm_tournament import AlgorithmTournament, AdaptiveSolver
from algorithms.path_search import AlgorithmPathSearch
from games.kuhn import KuhnPoker
from games.leduc import LeducPoker


def test_tournament_basic():
    """Test basic tournament functionality."""
    print("\n" + "=" * 80)
    print("TEST: Basic Tournament")
    print("=" * 80)

    game = KuhnPoker()
    tournament = AlgorithmTournament(game, iterations=[25, 50, 100])

    # Add a few algorithms
    tournament.add_algorithm(
        "cfr",
        "cfr",
        {"use_plus": False, "linear_weighting": False, "alternating": False},
        "Vanilla CFR",
    )
    tournament.add_algorithm(
        "cfr+",
        "cfr",
        {"use_plus": True, "linear_weighting": False, "alternating": False},
        "CFR+",
    )

    result = tournament.run_tournament(verbose=True)

    # Verify results
    assert len(result.algorithms) == 2
    assert len(result.exploitability_matrix["cfr"]) == 3
    assert len(result.exploitability_matrix["cfr+"]) == 3
    assert result.winner in ["cfr", "cfr+"]
    assert result.winner_final_exp > 0

    print("\n✓ Basic tournament test passed")
    return True


def test_cfr_variants():
    """Test CFR variants tournament."""
    print("\n" + "=" * 80)
    print("TEST: CFR Variants Tournament")
    print("=" * 80)

    game = KuhnPoker()
    tournament = AlgorithmTournament(game, iterations=[50, 100])

    tournament.add_cfr_variants()

    result = tournament.run_tournament(verbose=True)

    # Verify we have multiple CFR variants
    assert len(result.algorithms) >= 5
    assert result.winner_final_exp < 0.1  # Should converge reasonably well

    print("\n✓ CFR variants test passed")
    return True


def test_fp_variants():
    """Test Fictitious Play variants tournament."""
    print("\n" + "=" * 80)
    print("TEST: Fictitious Play Variants Tournament")
    print("=" * 80)

    game = KuhnPoker()
    tournament = AlgorithmTournament(game, iterations=[50, 100])

    tournament.add_fp_variants()

    result = tournament.run_tournament(verbose=True)

    # Verify we have multiple FP variants
    assert len(result.algorithms) >= 4
    assert result.winner_final_exp < 0.1

    print("\n✓ FP variants test passed")
    return True


def test_adaptive_solver():
    """Test adaptive solver that switches algorithms."""
    print("\n" + "=" * 80)
    print("TEST: Adaptive Solver")
    print("=" * 80)

    game = KuhnPoker()
    solver = AdaptiveSolver(game, evaluation_interval=50, switch_threshold=1.5)

    # Add candidates
    from algorithms.cfr import CFRConfig, CFRTrainer
    from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer

    solver.add_algorithm_candidate(
        "cfr", lambda: CFRTrainer(game, CFRConfig(use_plus=False))
    )
    solver.add_algorithm_candidate(
        "cfr+", lambda: CFRTrainer(game, CFRConfig(use_plus=True))
    )
    solver.add_algorithm_candidate(
        "fp", lambda: FictitiousPlayTrainer(game, FPConfig(linear_weighting=True))
    )

    # Run adaptive solver
    profile = solver.run_adaptive(max_iterations=200, verbose=True)

    # Verify we got a strategy
    assert profile is not None
    assert len(profile) > 0
    assert len(solver.history) > 0

    print("\n✓ Adaptive solver test passed")
    return True


def test_path_search():
    """Test multi-path search with backtracking."""
    print("\n" + "=" * 80)
    print("TEST: Multi-Path Search")
    print("=" * 80)

    game = KuhnPoker()
    searcher = AlgorithmPathSearch(
        game,
        max_iterations_per_node=50,
        max_total_iterations=500,
        pruning_threshold=2.0,
    )

    best_path = searcher.search(max_depth=2, verbose=True)

    # Verify we found a path
    assert best_path is not None
    assert best_path.final_exploitability > 0
    assert len(best_path.nodes) > 0
    assert searcher.best_exploitability < float("inf")

    searcher.print_search_summary()

    print("\n✓ Path search test passed")
    return True


def test_convergence_comparison():
    """Test that different algorithms show expected convergence patterns."""
    print("\n" + "=" * 80)
    print("TEST: Convergence Comparison")
    print("=" * 80)

    game = KuhnPoker()
    tournament = AlgorithmTournament(game, iterations=[25, 50, 100, 200])

    # Add algorithms expected to have different convergence patterns
    tournament.add_algorithm(
        "cfr",
        "cfr",
        {"use_plus": False, "linear_weighting": False, "alternating": False},
    )
    tournament.add_algorithm(
        "cfr+_alt",
        "cfr",
        {"use_plus": True, "linear_weighting": False, "alternating": True},
    )
    tournament.add_algorithm(
        "fp_linear_alt",
        "fp",
        {"optimistic": False, "linear_weighting": True, "alternating": True},
    )

    result = tournament.run_tournament(verbose=True)

    # Check convergence rates
    for algo in result.algorithms:
        exp_values = result.exploitability_matrix[algo]
        # Exploitability should generally decrease
        assert exp_values[0] >= exp_values[-1]

        conv_rate = result.convergence_rates[algo]
        # Should have positive convergence rate
        assert conv_rate >= 0

    print("\n✓ Convergence comparison test passed")
    return True


def test_leduc_performance():
    """Test algorithms on Leduc poker (more complex game)."""
    print("\n" + "=" * 80)
    print("TEST: Leduc Poker Performance")
    print("=" * 80)

    game = LeducPoker()
    tournament = AlgorithmTournament(game, iterations=[50, 100])

    # Test a subset of algorithms on the more complex game
    tournament.add_algorithm(
        "cfr+",
        "cfr",
        {"use_plus": True, "linear_weighting": False, "alternating": False},
    )
    tournament.add_algorithm(
        "cfr+_alt",
        "cfr",
        {"use_plus": True, "linear_weighting": False, "alternating": True},
    )

    result = tournament.run_tournament(verbose=True)

    # Verify results are reasonable for Leduc
    assert result.winner_final_exp > 0
    # Leduc is harder, so exploitability will be higher than Kuhn
    assert result.winner_final_exp < 1.0  # Should still converge somewhat

    print("\n✓ Leduc performance test passed")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RUNNING ALGORITHM TOURNAMENT TEST SUITE")
    print("=" * 80)

    tests = [
        test_tournament_basic,
        test_cfr_variants,
        test_fp_variants,
        test_adaptive_solver,
        test_path_search,
        test_convergence_comparison,
        test_leduc_performance,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {test_func.__name__} FAILED: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
