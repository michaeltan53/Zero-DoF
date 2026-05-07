"""
Monotonic Gating (Principle 3.1, Chapter 3.4)

- W↑ = { ω ∈ [0,1]^K : ω_{k+1} ≥ ω_k, ∀k }
- Fusion: S_ω(X;k) = (1-ω_k) S_s(X) + ω_k S_g(X)
- Isotonic projection: project any ω̂ onto W↑ for compliance.
"""

import numpy as np
from typing import Union


def isotonic_projection(omega: np.ndarray) -> np.ndarray:
    """
    Project ω̂ onto W↑ (isotonic / monotone non-decreasing) via PAV.
    Uses scipy or a simple pool-adjacent-violators (PAV) implementation.

    The result ω↑ satisfies ω↑_{k+1} ≥ ω↑_k and minimizes (e.g. L2) distance
    to ω among all non-decreasing sequences in [0,1]^K. We clip to [0,1] after.

    Args:
        omega: (K,) estimated weights, any values

    Returns:
        ω↑ ∈ W↑, same shape, values in [0,1]
    """
    from scipy.stats import mstats
    y = np.asarray(omega, dtype=float).ravel()
    K = len(y)
    if K == 0:
        return y
    # mstats.mjci / isotonic regression in scipy: mstats.kruskal might not
    # give PAV. sklearn.isotonic.IsotonicRegression or manual PAV.
    # Prefer minimal deps: implement simple PAV for non-decreasing.
    out = _pool_adjacent_violators(y)
    return np.clip(out, 0.0, 1.0)


def _pool_adjacent_violators(y: np.ndarray) -> np.ndarray:
    """
    Pool-adjacent-violators algorithm for non-decreasing (isotonic) regression.
    Solves: min sum (z_i - y_i)^2 s.t. z_1 <= z_2 <= ... <= z_K.

    Args:
        y: (K,) observed values

    Returns:
        (K,) fitted non-decreasing values
    """
    y = np.asarray(y, dtype=float).ravel()
    n = len(y)
    if n <= 1:
        return y.copy()

    # Block representation: (value, count). Start with each point as its own block.
    values = list(y)
    count = [1] * n

    i = 0
    while i < len(values) - 1:
        if values[i] <= values[i + 1]:
            i += 1
            continue
        # Merge block i and i+1: replace with (weighted) mean
        total = values[i] * count[i] + values[i + 1] * count[i + 1]
        c = count[i] + count[i + 1]
        values[i] = total / c
        count[i] = c
        del values[i + 1]
        del count[i + 1]
        # Check backwards for more violations
        if i > 0:
            i -= 1
        # else stay at i=0

    # Expand blocks back to length-K array
    out = np.empty(n)
    idx = 0
    for v, c in zip(values, count):
        out[idx : idx + c] = v
        idx += c
    return out


def is_monotonic_non_decreasing(omega: np.ndarray) -> bool:
    """
    Check if ω ∈ W↑: ω_{k+1} ≥ ω_k for all k.
    O(K) deterministic check.

    Args:
        omega: (K,) weights

    Returns:
        True if monotone non-decreasing
    """
    w = np.asarray(omega).ravel()
    if w.size <= 1:
        return True
    return bool(np.all(w[1:] >= w[:-1] - 1e-12))


def weight_tv(omega: np.ndarray) -> float:
    """
    Total variation of weight sequence: sum |ω_{k+1} - ω_k|.
    Used as measure of oscillation / back-and-forth in gating.

    Args:
        omega: (K,) weights

    Returns:
        TV(ω)
    """
    w = np.asarray(omega).ravel()
    if w.size <= 1:
        return 0.0
    return float(np.sum(np.abs(w[1:] - w[:-1])))


def count_monotonic_violations(omega: np.ndarray) -> int:
    """
    Count violations of ω_{k+1} ≥ ω_k: sum_k 1[ω_{k+1} < ω_k].

    Args:
        omega: (K,) weights

    Returns:
        number of violations
    """
    w = np.asarray(omega).ravel()
    if w.size <= 1:
        return 0
    return int(np.sum(w[1:] < w[:-1]))


def fused_score(score_s: float, score_g: float, omega_k: float) -> float:
    """
    Fusion score at one bin (Principle 3.1):
    S_ω(X;k) = (1-ω_k) S_s(X) + ω_k S_g(X)

    Args:
        score_s: S_s(X) — semantic evidence
        score_g: S_g(X) — geometric evidence
        omega_k: ω_k — weight for geometric at this bin

    Returns:
        S_ω(X;k)
    """
    return (1.0 - omega_k) * score_s + omega_k * score_g


def fused_score_vectorized(
    score_s: np.ndarray,
    score_g: np.ndarray,
    omega: np.ndarray,
    bin_indices: np.ndarray,
) -> np.ndarray:
    """
    Fusion for many samples with per-sample bin assignment:
    S_ω(X_i;k_i) = (1-ω_{k_i}) S_s(X_i) + ω_{k_i} S_g(X_i)

    Args:
        score_s: (N,) semantic scores
        score_g: (N,) geometric scores
        omega: (K,) weights per bin
        bin_indices: (N,) bin index per sample, in [0, K-1]

    Returns:
        (N,) fused scores
    """
    s = np.asarray(score_s).ravel()
    g = np.asarray(score_g).ravel()
    b = np.asarray(bin_indices, dtype=int).ravel()
    w = np.asarray(omega).ravel()
    o = np.clip(w[np.clip(b, 0, len(w) - 1)], 0, 1)
    return (1 - o) * s + o * g
