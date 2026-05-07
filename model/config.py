"""
Config: Configuration Charter
Pre-commitment and hash-bound configuration for Auth-WVC contract
"""

import json
import hashlib
from typing import List, Dict, Any, Optional, Callable
import numpy as np


class Config:
    """
    Configuration Charter for Auth-WVC contract.
    
    All parameters affecting evaluation must be pre-committed and hash-locked.
    """
    
    def __init__(
        self,
        alpha: float = 0.01,
        delta: float = 0.05,
        delta_far: float = 0.025,
        delta_wvc: float = 0.025,
        bins: List[tuple] = None,
        binning_method: str = "equal_width",
        ucb_method: str = "clopper_pearson",
        thresholds: Dict[int, float] = None,
        n_min: int = 100,
        indeterminate_threshold: float = 0.20,
        coverage_threshold: float = 0.80,
        fail_safe_rules: Dict[str, Any] = None,
        tau_computation: Optional[Callable] = None,
        tau_params: Dict[str, Any] = None,
    ):
        """
        Initialize Config with pre-commitment parameters.
        
        Args:
            alpha: Target FAR upper bound (e.g., 0.01 for 1%)
            delta: Total confidence budget
            delta_far: Budget allocated for FAR compliance
            delta_wvc: Budget allocated for WVC (FRR) bounds
            bins: List of (tau_min, tau_max) tuples for bins
            binning_method: Method for binning ("equal_width", "equal_freq", "custom")
            ucb_method: UCB computation method (default: "clopper_pearson")
            thresholds: Dict mapping bin index to decision threshold
            n_min: Minimum samples per bin for valid evaluation
            indeterminate_threshold: Max fraction of bins that can be INDETERMINATE
            coverage_threshold: Minimum fraction of bins that must be valid
            fail_safe_rules: Rules for FAIL-SAFE triggering
            tau_computation: Function to compute tau from input features
            tau_params: Parameters for tau computation
        """
        assert delta_far + delta_wvc <= delta, "Budget split exceeds total delta"
        assert 0 < alpha < 1, "Alpha must be in (0, 1)"
        assert 0 < delta < 1, "Delta must be in (0, 1)"
        
        self.alpha = alpha
        self.delta = delta
        self.delta_far = delta_far
        self.delta_wvc = delta_wvc
        self.bins = bins or []
        self.binning_method = binning_method
        self.ucb_method = ucb_method
        self.thresholds = thresholds or {}
        self.n_min = n_min
        self.indeterminate_threshold = indeterminate_threshold
        self.coverage_threshold = coverage_threshold
        self.fail_safe_rules = fail_safe_rules or {}
        self.tau_computation = tau_computation
        self.tau_params = tau_params or {}
        
        # Compute number of bins
        self.K = len(self.bins) if self.bins else 0
        
        # Compute per-bin confidence levels
        self.gamma_k = [self.delta_far / self.K] * self.K if self.K > 0 else []
        self.eta_k = [self.delta_wvc / self.K] * self.K if self.K > 0 else []
        
        # Hash lock (computed after all parameters set)
        self.cfg_hash = None
        self._compute_hash()
    
    def _compute_hash(self):
        """Compute hash of configuration for integrity verification."""
        config_dict = self.to_dict()
        config_str = json.dumps(config_dict, sort_keys=True, default=str)
        self.cfg_hash = hashlib.sha256(config_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding non-serializable functions)."""
        d = {
            'alpha': self.alpha,
            'delta': self.delta,
            'delta_far': self.delta_far,
            'delta_wvc': self.delta_wvc,
            'bins': self.bins,
            'binning_method': self.binning_method,
            'ucb_method': self.ucb_method,
            'thresholds': self.thresholds,
            'n_min': self.n_min,
            'indeterminate_threshold': self.indeterminate_threshold,
            'coverage_threshold': self.coverage_threshold,
            'fail_safe_rules': self.fail_safe_rules,
            'tau_params': self.tau_params,
        }
        return d
    
    def assign_bin(self, tau: float) -> int:
        """
        Assign a tau value to a bin index.
        
        Args:
            tau: Strength coordinate value
            
        Returns:
            Bin index (0-indexed), or -1 if out of range
        """
        for k, (tau_min, tau_max) in enumerate(self.bins):
            if tau_min <= tau < tau_max or (k == len(self.bins) - 1 and tau == tau_max):
                return k
        return -1
    
    def get_threshold(self, bin_idx: int) -> float:
        """Get decision threshold for a bin."""
        return self.thresholds.get(bin_idx, self.thresholds.get('default', 0.5))
    
    def create_bins_equal_width(self, tau_min: float, tau_max: float, n_bins: int):
        """Create bins using equal width method."""
        bin_width = (tau_max - tau_min) / n_bins
        self.bins = [
            (tau_min + i * bin_width, tau_min + (i + 1) * bin_width)
            for i in range(n_bins)
        ]
        # Last bin includes upper bound
        self.bins[-1] = (self.bins[-1][0], tau_max)
        self.K = len(self.bins)
        self.gamma_k = [self.delta_far / self.K] * self.K
        self.eta_k = [self.delta_wvc / self.K] * self.K
        self._compute_hash()
    
    def create_bins_equal_freq(self, tau_values: np.ndarray, n_bins: int):
        """Create bins using equal frequency method."""
        percentiles = np.linspace(0, 100, n_bins + 1)
        tau_edges = np.percentile(tau_values, percentiles)
        self.bins = [
            (tau_edges[i], tau_edges[i + 1])
            for i in range(n_bins)
        ]
        self.K = len(self.bins)
        self.gamma_k = [self.delta_far / self.K] * self.K
        self.eta_k = [self.delta_wvc / self.K] * self.K
        self._compute_hash()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        # Remove non-serializable fields
        d = config_dict.copy()
        d.pop('tau_computation', None)
        return cls(**d)
    
    def __repr__(self):
        return f"Config(alpha={self.alpha}, delta={self.delta}, K={self.K}, hash={self.cfg_hash[:8]}...)"
