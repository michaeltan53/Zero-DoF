"""
AuditSCP: Statistical Test for Single-Crossing Prior (Chapter 3.5)

Implements:
- Def 3.5: Conservative CI for advantage difference [Δ^L_k, Δ^U_k]
  = [LCB^g_k - UCB^s_k,  UCB^g_k - LCB^s_k]
- Def 3.6: Sign state: + (semantic), - (geometric), 0 (uncertain)
- Rule 3.1: SCP_PASS ⟺ k_+ < k_-

Uses LCB/UCB for FRR^s_k, FRR^g_k (e.g. from Clopper-Pearson or MBB).
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AuditSCPResult:
    """Result of AuditSCP run."""
    scp_pass: bool
    k_plus: int      # last definite "+" bin index; 0 if none
    k_minus: int     # first definite "-" bin index; K+1 if none
    sign_states: List[str]   # '+', '-', '0' per bin
    delta_L: np.ndarray      # Δ^L_k
    delta_U: np.ndarray      # Δ^U_k
    n_uncertain: int         # count of "0" bins


def sign_state(delta_L_k: float, delta_U_k: float) -> str:
    """
    Sign state (Def 3.6):
    - '+' (semantic): Δ^L_k > 0
    - '-' (geometric): Δ^U_k < 0
    - '0' (uncertain): otherwise

    Args:
        delta_L_k: lower bound of advantage difference CI
        delta_U_k: upper bound of advantage difference CI

    Returns:
        '+', '-', or '0'
    """
    if delta_L_k > 0:
        return '+'
    if delta_U_k < 0:
        return '-'
    return '0'


def conservative_advantage_ci(
    lcb_s: float, ucb_s: float,
    lcb_g: float, ucb_g: float,
) -> Tuple[float, float]:
    """
    Conservative CI for advantage difference (Def 3.5):
    [Δ^L_k, Δ^U_k] = [LCB^g_k - UCB^s_k,  UCB^g_k - LCB^s_k]

    Covers Δ = FRR^g - FRR^s at the pre-committed confidence level.

    Args:
        lcb_s, ucb_s: [LCB^s_k, UCB^s_k] for FRR^s_k(α)
        lcb_g, ucb_g: [LCB^g_k, UCB^g_k] for FRR^g_k(α)

    Returns:
        (Δ^L_k, Δ^U_k)
    """
    delta_L = lcb_g - ucb_s
    delta_U = ucb_g - lcb_s
    return (float(delta_L), float(delta_U))


def run_audit_scp(
    lcb_s: np.ndarray,
    ucb_s: np.ndarray,
    lcb_g: np.ndarray,
    ucb_g: np.ndarray,
) -> AuditSCPResult:
    """
    Run AuditSCP (Rule 3.1): SCP_PASS ⟺ k_+ < k_-.

    k_+ = last bin index with sign '+'; 0 if no definite '+'
    k_- = first bin index with sign '-'; K+1 if no definite '-'

    SCP_PASS = True allows arbitrary "0" (uncertain) region but forbids
    definite reversal (e.g. + then - then +).

    Args:
        lcb_s, ucb_s: (K,) LCB and UCB for FRR^s_k(α)
        lcb_g, ucb_g: (K,) LCB and UCB for FRR^g_k(α)

    Returns:
        AuditSCPResult
    """
    K = len(lcb_s)
    lcb_s = np.asarray(lcb_s).ravel()
    ucb_s = np.asarray(ucb_s).ravel()
    lcb_g = np.asarray(lcb_g).ravel()
    ucb_g = np.asarray(ucb_g).ravel()
    assert lcb_s.shape == lcb_g.shape == (K,)

    delta_L = np.empty(K)
    delta_U = np.empty(K)
    states: List[str] = []

    for k in range(K):
        dL, dU = conservative_advantage_ci(
            float(lcb_s[k]), float(ucb_s[k]),
            float(lcb_g[k]), float(ucb_g[k]),
        )
        delta_L[k] = dL
        delta_U[k] = dU
        states.append(sign_state(dL, dU))

    # k_+ = last index with '+' (1-based in paper: "last + bin"); we use 0-based.
    # "若不存在取 0" → no definite +: k_+ = 0 in the sense that we set k_plus
    # so that condition k_+ < k_- works. Convention: k_plus = last "+" index,
    # or -1 if none. Then "k_+ < k_-" means: the last + is before the first -.
    # Paper: k_+ = last "+" index (or 0 if none), k_- = first "-" (or K+1).
    # So k_+ < k_-: the last + is strictly before the first -.
    k_plus = -1
    for k in range(K):
        if states[k] == '+':
            k_plus = k
    # Paper: "若不存在取 0" for k_+ — we use 0-based; "0" means no +. For
    # k_+ < k_-, if no + then k_plus=-1, and we need -1 < k_minus. If we set
    # k_plus=0 when none, then 0 < k_minus. The paper's "0" is "no such bin",
    # so we map: no + → k_plus = -1, and treat as "before any -", so we want
    # k_plus < k_minus. With k_minus=K+1 when no -, -1 < K+1 holds. With
    # k_minus=0 (first bin is -), -1 < 0 holds. So k_plus=-1 is fine.
    # For "k_+ < k_-" in 1-based: if k_+=0 (no +) and k_-=1, then 0<1. In
    # 0-based: k_plus=-1, k_minus=0 → -1<0. Good.

    k_minus = K  # first "-" index; K if none (K+1 in 1-based)
    for k in range(K):
        if states[k] == '-':
            k_minus = k
            break

    # SCP_PASS: k_+ < k_- (last + before first -; no definite reversal)
    scp_pass = k_plus < k_minus

    n_uncertain = sum(1 for s in states if s == '0')

    return AuditSCPResult(
        scp_pass=scp_pass,
        k_plus=k_plus,
        k_minus=k_minus,
        sign_states=states,
        delta_L=delta_L,
        delta_U=delta_U,
        n_uncertain=n_uncertain,
    )


def cross_count_from_signs(sign_states: List[str]) -> int:
    """
    Count crosses in sign sequence (ignoring '0'): +→- or -→+ transitions.

    For SCP we care about +→- crosses; under SCP the +→- count should be ≤ 1.
    This helper counts both directions for diagnostic (e.g. adversarial audit).

    Args:
        sign_states: list of '+', '-', '0'

    Returns:
        number of sign changes when skipping '0' (comparing consecutive non-0)
    """
    # Reduce to non-0 sequence and count adjacent differences
    reduced = [s for s in sign_states if s != '0']
    if len(reduced) <= 1:
        return 0
    c = 0
    for i in range(len(reduced) - 1):
        if reduced[i] != reduced[i + 1]:
            c += 1
    return c
