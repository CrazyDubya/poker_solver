from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from algorithms.cfr import CFRConfig, CFRTrainer
from algorithms.fictitious_play import FPConfig, FictitiousPlayTrainer
from algorithms.infoset import InfoSet


@dataclass
class HybridCFRFPConfig:
    """Hybrid algorithm that switches between CFR and FP.
    
    Uses CFR initially for fast convergence, then switches to FP
    for final refinement. This exploits CFR's rapid early progress
    and FP's theoretical convergence guarantees.
    """
    switch_iteration: int = 400
    cfr_config: CFRConfig | None = None
    fp_config: FPConfig | None = None


class HybridCFRFPTrainer:
    """Hybrid trainer that switches from CFR to Fictitious Play."""

    def __init__(self, game, config: HybridCFRFPConfig | None = None) -> None:
        self.game = game
        self.config = config or HybridCFRFPConfig()
        self.cfr_config = self.config.cfr_config or CFRConfig(use_plus=True, linear_weighting=True, alternating=True)
        self.fp_config = self.config.fp_config or FPConfig(optimistic=False, linear_weighting=True, alternating=True)
        
        self.cfr_trainer = CFRTrainer(game, self.cfr_config)
        self.fp_trainer: FictitiousPlayTrainer | None = None
        self.iteration = 0
        self.switched = False

    def run(self, iterations: int) -> None:
        """Run hybrid training for specified iterations."""
        target = self.iteration + iterations
        
        # Phase 1: CFR until switch point
        if not self.switched and self.iteration < self.config.switch_iteration:
            cfr_iters = min(iterations, self.config.switch_iteration - self.iteration)
            self.cfr_trainer.run(cfr_iters)
            self.iteration += cfr_iters
            iterations -= cfr_iters
            
            if self.iteration >= self.config.switch_iteration:
                self._switch_to_fp()
        
        # Phase 2: FP after switch point
        if self.switched and iterations > 0:
            self.fp_trainer.run(iterations)
            self.iteration += iterations

    def _switch_to_fp(self) -> None:
        """Transfer CFR strategy to FP trainer and switch algorithms."""
        self.switched = True
        self.fp_trainer = FictitiousPlayTrainer(self.game, self.fp_config)
        
        # Initialize FP with CFR's current average strategy
        cfr_profile = self.cfr_trainer.average_strategy_profile()
        
        # Warm-start FP with CFR results
        for key, action_probs in cfr_profile.items():
            actions = list(action_probs.keys())
            probs = [action_probs[a] for a in actions]
            
            # Try to map to player infosets
            for player in (0, 1):
                infoset = self.fp_trainer._get_infoset(player, key, actions)
                # Add initial strategy with weight
                infoset.add_strategy(probs, weight=float(self.config.switch_iteration))
        
        # Update total weights
        for player in (0, 1):
            self.fp_trainer.total_weight[player] = float(self.config.switch_iteration)

    def average_strategy_profile(self) -> Dict[str, Dict[str, float]]:
        """Return current average strategy."""
        if self.switched and self.fp_trainer:
            return self.fp_trainer.average_strategy_profile()
        return self.cfr_trainer.average_strategy_profile()


@dataclass
class AdaptiveCFRConfig:
    """Adaptive CFR that adjusts parameters based on convergence.
    
    Monitors exploitability and adapts learning parameters dynamically
    to accelerate convergence when stuck in plateaus.
    """
    initial_plus: bool = True
    initial_linear: bool = True
    initial_alternating: bool = True
    adaptation_frequency: int = 100
    plateau_threshold: float = 0.001


class AdaptiveCFRTrainer:
    """CFR trainer with adaptive parameter tuning.
    
    Automatically adjusts CFR+ vs CFR, linear weighting, and alternating
    modes based on convergence progress.
    """

    def __init__(self, game, config: AdaptiveCFRConfig | None = None) -> None:
        self.game = game
        self.config = config or AdaptiveCFRConfig()
        
        self.current_config = CFRConfig(
            use_plus=self.config.initial_plus,
            linear_weighting=self.config.initial_linear,
            alternating=self.config.initial_alternating,
        )
        
        self.trainer = CFRTrainer(game, self.current_config)
        self.iteration = 0
        self.last_check_iteration = 0
        self.last_exploitability = float('inf')
        self.exploitability_history: List[float] = []

    def run(self, iterations: int) -> None:
        """Run adaptive CFR training."""
        for _ in range(iterations):
            self.iteration += 1
            self.trainer.run(1)
            
            if self.iteration % self.config.adaptation_frequency == 0:
                self._adapt_parameters()

    def _adapt_parameters(self) -> None:
        """Adapt CFR parameters based on convergence rate."""
        from algorithms.evaluation import exploitability
        
        profile = self.trainer.average_strategy_profile()
        current_exp = exploitability(self.game, profile)
        self.exploitability_history.append(current_exp)
        
        if len(self.exploitability_history) < 2:
            self.last_exploitability = current_exp
            return
        
        # Calculate convergence rate
        improvement = self.last_exploitability - current_exp
        iters_elapsed = self.iteration - self.last_check_iteration
        convergence_rate = improvement / iters_elapsed if iters_elapsed > 0 else 0.0
        
        # Detect plateau (slow convergence)
        if abs(convergence_rate) < self.config.plateau_threshold:
            # Try switching strategies
            if not self.current_config.use_plus:
                # Switch to CFR+
                self.current_config = CFRConfig(
                    use_plus=True,
                    linear_weighting=True,
                    alternating=self.current_config.alternating,
                )
                self._rebuild_trainer()
            elif not self.current_config.alternating:
                # Try alternating
                self.current_config = CFRConfig(
                    use_plus=self.current_config.use_plus,
                    linear_weighting=self.current_config.linear_weighting,
                    alternating=True,
                )
                self._rebuild_trainer()
        
        self.last_exploitability = current_exp
        self.last_check_iteration = self.iteration

    def _rebuild_trainer(self) -> None:
        """Rebuild trainer with new config, preserving state."""
        old_infosets = self.trainer.infosets
        self.trainer = CFRTrainer(self.game, self.current_config)
        self.trainer.infosets = old_infosets
        self.trainer.iteration = self.iteration

    def average_strategy_profile(self) -> Dict[str, Dict[str, float]]:
        """Return current average strategy."""
        return self.trainer.average_strategy_profile()


@dataclass
class WarmStartConfig:
    """Configuration for warm-starting solvers with precomputed strategies."""
    base_iterations: int = 200
    refinement_iterations: int = 800


class WarmStartTrainer:
    """Two-phase trainer: quick initial solve + refined solve.
    
    Uses a fast approximate solver (MCCFR) for initial strategy,
    then refines with full CFR+ for accuracy.
    """

    def __init__(self, game, config: WarmStartConfig | None = None) -> None:
        self.game = game
        self.config = config or WarmStartConfig()
        self.phase = 1
        self.iteration = 0
        
        # Phase 1: Fast approximation
        from algorithms.mccfr import ExternalSamplingMCCFRTrainer, MCCFRConfig
        self.mccfr_trainer = ExternalSamplingMCCFRTrainer(game, MCCFRConfig(seed=42))
        
        # Phase 2: Refinement
        self.cfr_trainer: CFRTrainer | None = None

    def run(self, iterations: int) -> None:
        """Run warm-start training."""
        if self.phase == 1:
            # Run MCCFR for fast initial strategy
            iters_phase1 = min(iterations, self.config.base_iterations - self.iteration)
            if iters_phase1 > 0:
                self.mccfr_trainer.run(iters_phase1)
                self.iteration += iters_phase1
                iterations -= iters_phase1
            
            # Switch to refinement phase
            if self.iteration >= self.config.base_iterations:
                self._switch_to_refinement()
        
        if self.phase == 2 and iterations > 0:
            self.cfr_trainer.run(iterations)
            self.iteration += iterations

    def _switch_to_refinement(self) -> None:
        """Switch from MCCFR to CFR+ for refinement."""
        self.phase = 2
        self.cfr_trainer = CFRTrainer(
            self.game,
            CFRConfig(use_plus=True, linear_weighting=True, alternating=True),
        )
        
        # Warm-start CFR with MCCFR results
        mccfr_profile = self.mccfr_trainer.average_strategy_profile()
        
        for key, action_probs in mccfr_profile.items():
            actions = list(action_probs.keys())
            probs = [action_probs[a] for a in actions]
            
            infoset = self.cfr_trainer.infosets.get(key)
            if infoset is None:
                infoset = InfoSet(actions)
                self.cfr_trainer.infosets[key] = infoset
            
            # Initialize with warm-start weight
            for idx, prob in enumerate(probs):
                infoset.strategy_sum[idx] = prob * self.config.base_iterations

    def average_strategy_profile(self) -> Dict[str, Dict[str, float]]:
        """Return current average strategy."""
        if self.phase == 2 and self.cfr_trainer:
            return self.cfr_trainer.average_strategy_profile()
        return self.mccfr_trainer.average_strategy_profile()
