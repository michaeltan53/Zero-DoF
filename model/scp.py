"""
SCP: Single-Crossing Prior and Oracle Hard Selector

Implements Chapter 3 theory:
- Def 3.2: Advantage difference Δ_{α,k} = FRR^g_k(α) - FRR^s_k(α)
- Def 3.3: SCP (single-crossing prior): Δ non-increasing sign pattern
- Def 3.4: Oracle π^orc(k) = argmin_{s,g} FRR^⋆_k(α)
- Thm 3.1 / Cor 3.1: SCP ⇒ Oracle has at-most-one-switch structure
"""

import numpy as np
from typing import List, Tuple, Optional


def advantage_difference(frr_s: float, frr_g: float) -> float:
    """
    Advantage difference (Def 3.2): Δ_{α,k} = FRR^g_k(α) - FRR^s_k(α).

    Δ > 0: semantic better (lower FRR); Δ < 0: geometric better.

    Args:
        frr_s: FRR^s_k(α) — semantic FRR at FAR≤α
        frr_g: FRR^g_k(α) — geometric FRR at FAR≤α

    Returns:
        Δ_{α,k}
    """
    return float(frr_g - frr_s)


def oracle_hard_selector(frr_s_k: float, frr_g_k: float) -> str:
    """
    Bin-wise optimal hard selector (Def 3.4): π^orc(k) ∈ argmin_{s,g} FRR^⋆_k(α).

    Args:
        frr_s_k: FRR^s_k(α)
        frr_g_k: FRR^g_k(α)

    Returns:
        's' (semantic) or 'g' (geometric)
    """
    return 's' if frr_s_k <= frr_g_k else 'g'


def oracle_sequence(
    frr_s: np.ndarray,
    frr_g: np.ndarray,
) -> List[str]:
    """
    Oracle decision sequence over all bins: π^orc(1), ..., π^orc(K).

    Args:
        frr_s: shape (K,) — FRR^s_k(α) per bin
        frr_g: shape (K,) — FRR^g_k(α) per bin

    Returns:
        List of 's' or 'g' of length K
    """
    return [
        oracle_hard_selector(float(frr_s[k]), float(frr_g[k]))
        for k in range(len(frr_s))
    ]


def advantage_difference_sequence(frr_s: np.ndarray, frr_g: np.ndarray) -> np.ndarray:
    """
    Advantage difference per bin: Δ_{α,k} for k=1..K.

    Args:
        frr_s: (K,) FRR^s_k(α)
        frr_g: (K,) FRR^g_k(α)

    Returns:
        (K,) Δ_{α,k}
    """
    return np.asarray(frr_g, dtype=float) - np.asarray(frr_s, dtype=float)


def check_scp_deterministic(delta: np.ndarray) -> bool:
    """
    Check if Δ sequence satisfies SCP (Def 3.3) in the deterministic setting.

    SCP: there exists k_c such that Δ_k ≥ 0 for k ≤ k_c and Δ_k ≤ 0 for k > k_c.
    Equivalently: the sign sequence (ignoring zeros) has at most one flip from + to -.

    Args:
        delta: (K,) Δ_{α,k}

    Returns:
        True if SCP holds (at most one cross from + to -)
    """
    d = np.asarray(delta).ravel()
    if d.size == 0:
        return True
    # Signs: +1 if >0, -1 if <0, 0 if ==0. Ignore zeros for cross count.
    sgn = np.sign(d)
    # Count crosses: + then - (or - then +). SCP allows at most one +→-.
    crosses = 0
    for i in range(len(sgn) - 1):
        if sgn[i] > 0 and sgn[i + 1] < 0:
            crosses += 1
        if crosses > 1:
            return False
    return True


def critical_index_from_delta(delta: np.ndarray) -> Optional[int]:
    """
    If SCP holds, return an index k_c such that low side chooses semantic,
    high side chooses geometric. Uses first k where Δ_k <= 0 as transition;
    if all Δ>0 return K; if all Δ<0 return 0.

    Args:
        delta: (K,) Δ_{α,k}

    Returns:
        k_c in 0..K (inclusive); None if SCP violated
    """
    if not check_scp_deterministic(delta):
        return None
    d = np.asarray(delta).ravel()
    for k in range(len(d)):
        if d[k] <= 0:
            return k
    return len(d)


def count_switches_in_oracle(pi: List[str]) -> int:
    """
    Count switches in Oracle (or any) hard decision sequence: s→g or g→s.

    Under SCP, for Oracle this is ≤ 1.

    Args:
        pi: list of 's' or 'g'

    Returns:
        number of adjacent (s,g) or (g,s) pairs
    """
    if len(pi) <= 1:
        return 0
    n = 0
    for i in range(len(pi) - 1):
        if pi[i] != pi[i + 1]:
            n += 1
    return n
