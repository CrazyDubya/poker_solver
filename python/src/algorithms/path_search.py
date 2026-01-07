"""
Advanced Algorithm Path Traversal with Backtracking

This module implements a sophisticated multi-path search strategy for
finding optimal algorithm configurations. It explores different algorithm
paths, backtracks when necessary, and refines based on performance data.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from algorithms.cfr import CFRConfig, CFRTrainer
from algorithms.evaluation import exploitability
from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig


@dataclass
class SearchNode:
    """Node in the algorithm search tree."""

    algorithm_type: str
    config: Dict[str, Any]
    parent: Optional[SearchNode] = None
    children: List[SearchNode] = field(default_factory=list)
    exploitability: float = float("inf")
    iterations_used: int = 0
    depth: int = 0
    visited: bool = False
    pruned: bool = False


@dataclass
class SearchPath:
    """A complete path through the search tree."""

    nodes: List[SearchNode]
    total_iterations: int
    final_exploitability: float
    path_description: str


class AlgorithmPathSearch:
    """
    Multi-path search with backtracking for algorithm optimization.

    This implements a sophisticated search strategy that:
    1. Explores multiple algorithm configurations in parallel
    2. Backtracks from unpromising paths
    3. Refines successful paths with parameter tuning
    4. Branches to explore new configurations based on learned patterns
    """

    def __init__(
        self,
        game,
        max_iterations_per_node: int = 200,
        max_total_iterations: int = 2000,
        pruning_threshold: float = 2.0,
        exploration_factor: float = 0.3,
    ) -> None:
        """
        Initialize path search.

        Args:
            game: Game instance
            max_iterations_per_node: Iterations to spend evaluating each node
            max_total_iterations: Total iteration budget
            pruning_threshold: Prune paths with exp > best * threshold
            exploration_factor: Fraction of budget for exploration vs exploitation
        """
        self.game = game
        self.max_iterations_per_node = max_iterations_per_node
        self.max_total_iterations = max_total_iterations
        self.pruning_threshold = pruning_threshold
        self.exploration_factor = exploration_factor

        self.root = None
        self.best_path: Optional[SearchPath] = None
        self.best_exploitability = float("inf")
        self.all_paths: List[SearchPath] = []
        self.iterations_used = 0

    def _create_cfr_variants(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate CFR algorithm variants to explore."""
        variants = []

        # Basic variants
        variants.append(
            ("cfr_vanilla", {"use_plus": False, "linear_weighting": False, "alternating": False})
        )
        variants.append(
            ("cfr+", {"use_plus": True, "linear_weighting": False, "alternating": False})
        )
        variants.append(
            ("cfr+_linear", {"use_plus": True, "linear_weighting": True, "alternating": False})
        )
        variants.append(
            ("cfr+_alt", {"use_plus": True, "linear_weighting": False, "alternating": True})
        )
        variants.append(
            ("cfr+_linear_alt", {"use_plus": True, "linear_weighting": True, "alternating": True})
        )

        # DCFR variants
        for alpha in [1.0, 1.5, 2.0]:
            for gamma in [1.5, 2.0, 2.5]:
                name = f"dcfr_a{alpha}_g{gamma}"
                config = {
                    "use_plus": False,
                    "use_dcfr": True,
                    "dcfr_alpha": alpha,
                    "dcfr_beta": 0.0,
                    "dcfr_gamma": gamma,
                }
                variants.append((name, config))

        return variants

    def _create_fp_variants(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate Fictitious Play variants to explore."""
        variants = []

        # Basic FP variants
        for opt in [False, True]:
            for linear in [False, True]:
                for alt in [False, True]:
                    name_parts = ["fp"]
                    if opt:
                        name_parts.append("opt")
                    if linear:
                        name_parts.append("lin")
                    if alt:
                        name_parts.append("alt")
                    name = "_".join(name_parts)
                    config = {
                        "optimistic": opt,
                        "linear_weighting": linear,
                        "alternating": alt,
                    }
                    variants.append((name, config))

        return variants

    def _create_trainer(self, algorithm_type: str, config: Dict[str, Any]):
        """Create trainer from algorithm type and config."""
        if algorithm_type == "cfr":
            cfg = CFRConfig(**config)
            return CFRTrainer(self.game, cfg)
        elif algorithm_type == "fp":
            cfg = FPConfig(**config)
            return FictitiousPlayTrainer(self.game, cfg)
        elif algorithm_type == "mccfr":
            cfg = MCCFRConfig(**config)
            return ExternalSamplingMCCFRTrainer(self.game, cfg)
        else:
            raise ValueError(f"Unknown algorithm type: {algorithm_type}")

    def _evaluate_node(
        self, node: SearchNode, verbose: bool = False
    ) -> float:
        """
        Evaluate a search node by running its algorithm configuration.

        Returns the exploitability after max_iterations_per_node iterations.
        """
        if node.visited:
            return node.exploitability

        trainer = self._create_trainer(node.algorithm_type, node.config)
        trainer.run(self.max_iterations_per_node)

        profile = trainer.average_strategy_profile()
        exp = exploitability(self.game, profile)

        node.exploitability = exp
        node.iterations_used = self.max_iterations_per_node
        node.visited = True
        self.iterations_used += self.max_iterations_per_node

        if verbose:
            print(f"  Evaluated: {node.algorithm_type} at depth {node.depth}, exp={exp:.6f}")

        return exp

    def _should_prune(self, node: SearchNode) -> bool:
        """Decide if a node should be pruned based on its performance."""
        if self.best_exploitability == float("inf"):
            return False

        # Prune if significantly worse than best path
        if node.exploitability > self.best_exploitability * self.pruning_threshold:
            return True

        return False

    def _generate_refinements(self, node: SearchNode) -> List[SearchNode]:
        """
        Generate refinement nodes based on a parent node.

        This implements branching with new information: if a configuration
        performs well, we explore variations around it.
        """
        refinements = []

        if node.algorithm_type == "cfr":
            config = node.config.copy()

            # If CFR+ is working well, try variants
            if config.get("use_plus", False):
                # Try with/without linear weighting
                if not config.get("linear_weighting", False):
                    new_config = config.copy()
                    new_config["linear_weighting"] = True
                    refinements.append(
                        SearchNode(
                            algorithm_type="cfr",
                            config=new_config,
                            parent=node,
                            depth=node.depth + 1,
                        )
                    )

                # Try with alternating
                if not config.get("alternating", False):
                    new_config = config.copy()
                    new_config["alternating"] = True
                    refinements.append(
                        SearchNode(
                            algorithm_type="cfr",
                            config=new_config,
                            parent=node,
                            depth=node.depth + 1,
                        )
                    )

            # If DCFR is working, try nearby parameters
            if config.get("use_dcfr", False):
                alpha = config.get("dcfr_alpha", 1.5)
                gamma = config.get("dcfr_gamma", 2.0)

                # Try slightly different alpha
                for delta in [-0.5, 0.5]:
                    new_alpha = alpha + delta
                    if 0.5 <= new_alpha <= 3.0:
                        new_config = config.copy()
                        new_config["dcfr_alpha"] = new_alpha
                        refinements.append(
                            SearchNode(
                                algorithm_type="cfr",
                                config=new_config,
                                parent=node,
                                depth=node.depth + 1,
                            )
                        )

        elif node.algorithm_type == "fp":
            config = node.config.copy()

            # Try enabling features that are off
            if not config.get("optimistic", False):
                new_config = config.copy()
                new_config["optimistic"] = True
                refinements.append(
                    SearchNode(
                        algorithm_type="fp",
                        config=new_config,
                        parent=node,
                        depth=node.depth + 1,
                    )
                )

            if not config.get("linear_weighting", False):
                new_config = config.copy()
                new_config["linear_weighting"] = True
                refinements.append(
                    SearchNode(
                        algorithm_type="fp",
                        config=new_config,
                        parent=node,
                        depth=node.depth + 1,
                    )
                )

        return refinements

    def search(
        self, max_depth: int = 3, verbose: bool = True
    ) -> SearchPath:
        """
        Perform multi-path search with backtracking.

        Args:
            max_depth: Maximum depth to explore in search tree
            verbose: Whether to print progress

        Returns:
            Best path found
        """
        if verbose:
            print(f"Starting multi-path search (max_depth={max_depth})...")
            print(f"Budget: {self.max_total_iterations} total iterations\n")

        # Create root nodes for each major algorithm family
        root_nodes = []

        # Add CFR variants
        for name, config in self._create_cfr_variants():
            node = SearchNode(algorithm_type="cfr", config=config, depth=0)
            root_nodes.append((name, node))

        # Add FP variants
        for name, config in self._create_fp_variants():
            node = SearchNode(algorithm_type="fp", config=config, depth=0)
            root_nodes.append((name, node))

        # Add MCCFR
        root_nodes.append(
            (
                "mccfr",
                SearchNode(algorithm_type="mccfr", config={"seed": 7}, depth=0),
            )
        )

        if verbose:
            print(f"Generated {len(root_nodes)} root configurations to explore\n")

        # Exploration phase: evaluate all root nodes
        exploration_budget = int(self.max_total_iterations * self.exploration_factor)
        nodes_to_explore = []

        for name, node in root_nodes:
            if self.iterations_used >= exploration_budget:
                break

            exp = self._evaluate_node(node, verbose)

            if exp < self.best_exploitability:
                self.best_exploitability = exp
                self.best_path = SearchPath(
                    nodes=[node],
                    total_iterations=node.iterations_used,
                    final_exploitability=exp,
                    path_description=name,
                )

            # Add to exploration queue if not pruned
            if not self._should_prune(node):
                nodes_to_explore.append((name, node))

        if verbose:
            print(f"\nExploration complete. {len(nodes_to_explore)} promising paths.\n")
            print(f"Best so far: {self.best_exploitability:.6f}\n")

        # Exploitation phase: refine best paths
        nodes_to_explore.sort(key=lambda x: x[1].exploitability)

        for name, node in nodes_to_explore:
            if self.iterations_used >= self.max_total_iterations:
                break

            if node.depth >= max_depth:
                continue

            # Generate and evaluate refinements
            refinements = self._generate_refinements(node)

            if verbose and refinements:
                print(f"Refining {name} ({len(refinements)} variants)...")

            for refinement in refinements:
                if self.iterations_used >= self.max_total_iterations:
                    break

                exp = self._evaluate_node(refinement, verbose)

                if exp < self.best_exploitability:
                    self.best_exploitability = exp

                    # Build path description
                    path_nodes = []
                    current = refinement
                    while current is not None:
                        path_nodes.insert(0, current)
                        current = current.parent

                    self.best_path = SearchPath(
                        nodes=path_nodes,
                        total_iterations=sum(n.iterations_used for n in path_nodes),
                        final_exploitability=exp,
                        path_description=f"{name} -> refined",
                    )

                    if verbose:
                        print(f"  New best: {exp:.6f}")

        if verbose:
            print(f"\n{'=' * 80}")
            print("Search complete!")
            print(f"Total iterations used: {self.iterations_used}")
            print(f"Best exploitability: {self.best_exploitability:.6f}")
            print(f"Best path: {self.best_path.path_description}")
            print(f"{'=' * 80}\n")

        return self.best_path

    def print_search_summary(self) -> None:
        """Print summary of the search process."""
        print("Search Summary:")
        print(f"  Total iterations: {self.iterations_used}")
        print(f"  Best exploitability: {self.best_exploitability:.6f}")
        if self.best_path:
            print(f"  Best path depth: {len(self.best_path.nodes)}")
            print(f"  Path description: {self.best_path.path_description}")
