# Algorithm Investigation Report

## Executive Summary

This report presents a comprehensive investigation of poker solving algorithms using multi-path branching, backtracking, and refinement strategies. We analyzed variants of CFR, Fictitious Play, and Monte Carlo CFR to identify optimal configurations.

## Methodology

### Multi-Path Exploration Approach

We implemented three complementary strategies:

1. **Algorithm Tournament Framework** - Systematic comparison across iteration checkpoints
2. **Adaptive Solver** - Dynamic algorithm switching based on convergence  
3. **Path Search with Backtracking** - Tree-based exploration with pruning and refinement

## Results: Kuhn Poker

### Top 5 Performers (Exploitability after 1600 iterations):
1. **cfr+_linear_alt**: 0.000052 ⭐ WINNER (100x better than vanilla CFR)
2. **fp_opt_linear_alt**: 0.000121
3. **fp_opt**: 0.000234
4. **cfr+_alt**: 0.000313
5. **fp_linear_alt**: 0.001070

### Key Findings:
- **Alternating updates** provide the largest improvement
- **Linear weighting** helps across all algorithm families
- **CFR+** consistently outperforms vanilla CFR
- **Path search** found optimal configs with 6x fewer iterations

### DCFR Parameter Sweep:
- Best α (positive decay): 2.5
- Best γ (strategy decay): 1.5  
- Best β (negative decay): 0.0 (no negative decay)

## Recommendations

**For Production**: CFR+ with linear weighting and alternating updates
- Fastest convergence
- Lowest final exploitability
- 100x improvement over vanilla CFR

See full results in tournament JSON files.
