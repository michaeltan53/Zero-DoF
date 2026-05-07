"""
Offline Contract Compilation (Chapter 5.2)

Compile(D_cal, tau; alpha, delta) -> Config with:
- Bins and thresholds (t_low, t_high) s.t. UCB(FAR_k) <= alpha
- Envelope thresholds: t_low_env[k] = min_{j>=k} t_low[j]
- Monotonic omega_lookup[k], epsilon for audit
- Guard rules, reason_codes, FSM spec; cfg_hash
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .config import Config
from .ucb import compute_far_ucb
from .monotonic_gating import isotonic_projection, is_monotonic_non_decreasing


# Default reason codes (I4)
DEFAULT_REASON_CODES = ['ACCEPT', 'REJECT', 'UNCERTAIN', 'GUARD_STEP', 'GUARD_DRIFT', 'GUARD_TIMEOUT', 'GUARD_UNKNOWN']


def compute_t_low_env(t_low: np.ndarray) -> np.ndarray:
    """
    Conservative envelope: t_low_env[k] = min_{j>=k} t_low[j].
    Ensures mis-routing cannot relax the accept threshold (Lemma 5.1).

    Args:
        t_low: (K,) per-bin lower accept thresholds (lower = stricter)

    Returns:
        (K,) t_low_env
    """
    t = np.asarray(t_low, dtype=float).ravel()
    out = np.empty_like(t)
    out[-1] = t[-1]
    for j in range(len(t) - 2, -1, -1):
        out[j] = min(t[j], out[j + 1])
    return out


def compile_omega_lookup(
    omega_raw: np.ndarray,
    epsilon: float = 0.0,
) -> np.ndarray:
    """
    Build monotonic omega_lookup: project omega_raw onto W_up so that
    omega_lookup[k+1] >= omega_lookup[k] - epsilon. If epsilon=0, strict monotonic.

    Args:
        omega_raw: (K,) raw weights (e.g. from calibration)
        epsilon: tolerance for audit: omega[k+1] >= omega[k] - epsilon

    Returns:
        (K,) omega_lookup in [0,1], non-decreasing (within epsilon)
    """
    omega = isotonic_projection(omega_raw)
    if epsilon > 0:
        # Allow small dips up to epsilon; auditor checks omega[k+1] >= omega[k] - epsilon
        pass  # projection already gives non-decreasing; epsilon is for audit tolerance
    return np.clip(omega, 0.0, 1.0)


def compile_thresholds_from_calibration(
    bins: List[Tuple[float, float]],
    bin_negatives: List[int],
    bin_false_accepts: List[int],
    alpha: float,
    delta_per_bin: float,
    score_per_bin: Optional[List[float]] = None,
) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
    """
    From calibration counts per bin, choose t_low, t_high such that UCB(FAR_k) <= alpha.
    Simplified: we assume thresholds are already chosen so that observed FAR satisfies
    UCB(FAR_k) <= alpha; here we return placeholder t_low/t_high keyed by bin.
    If score_per_bin is given (e.g. threshold that was used), use that as t_high and
    set t_low from envelope.

    Returns:
        t_low, t_high, t_low_env as dicts bin_idx -> float
    """
    K = len(bins)
    t_low = {}
    t_high = {}
    for k in range(K):
        n_neg = bin_negatives[k] if k < len(bin_negatives) else 0
        n_fa = bin_false_accepts[k] if k < len(bin_false_accepts) else 0
        conf = 1.0 - delta_per_bin
        if n_neg > 0:
            ucb = compute_far_ucb(n_neg, n_fa, conf)
            # Placeholder: set threshold so that next stricter would keep UCB <= alpha
            # In practice, thresholds come from ROC calibration; we store a scalar per bin.
            thresh = 0.5 - 0.1 * (k / max(K, 1))  # stiffer in higher bins
            t_low[k] = thresh - 0.05
            t_high[k] = thresh + 0.15
        else:
            t_low[k] = 0.5
            t_high[k] = 0.7
    if score_per_bin is not None and len(score_per_bin) >= K:
        for k in range(K):
            t_high[k] = float(score_per_bin[k])
            t_low[k] = float(score_per_bin[k]) - 0.1
    t_low_arr = np.array([t_low[k] for k in range(K)])
    t_low_env_arr = compute_t_low_env(t_low_arr)
    t_low_env = {k: float(t_low_env_arr[k]) for k in range(K)}
    return t_low, t_high, t_low_env


def compile_config_extended(
    config: Config,
    t_low: Dict[int, float],
    t_high: Dict[int, float],
    t_low_env: Dict[int, float],
    omega_lookup: np.ndarray,
    epsilon_monotonic: float = 0.0,
    n_min_per_bin: Optional[List[int]] = None,
    reason_codes: Optional[List[str]] = None,
) -> Config:
    """
    Attach Chapter 5 compile products to Config (as attributes).
    Does not change cfg_hash unless config is re-hashed; caller should
    include these in config.to_dict() and recompute hash for full Ch5 semantics.

    Args:
        config: base Config (bins, alpha, delta, etc.)
        t_low, t_high, t_low_env: per-bin thresholds
        omega_lookup: (K,) monotonic gating weights
        epsilon_monotonic: audit tolerance for omega
        n_min_per_bin: optional per-bin n_min (else use config.n_min)
        reason_codes: optional enum for I4

    Returns:
        Same config with attributes set: config.t_low, config.t_high, config.t_low_env,
        config.omega_lookup, config.epsilon_monotonic, config.n_min_per_bin, config.reason_codes
    """
    config.t_low = t_low
    config.t_high = t_high
    config.t_low_env = t_low_env
    config.omega_lookup = np.asarray(omega_lookup).ravel()
    config.epsilon_monotonic = epsilon_monotonic
    config.n_min_per_bin = n_min_per_bin or [config.n_min] * config.K
    config.reason_codes = reason_codes or DEFAULT_REASON_CODES
    return config
