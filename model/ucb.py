"""
Confidence Upper Bounds (UCB) Computation
Implements Clopper-Pearson exact confidence intervals for FAR and FRR
"""

import numpy as np
from scipy.stats import beta


def compute_far_ucb(n_negatives: int, n_false_accepts: int, confidence_level: float) -> float:
    """
    Compute FAR confidence upper bound using Clopper-Pearson exact method.
    
    Args:
        n_negatives: Number of negative samples (ground truth negatives)
        n_false_accepts: Number of false accepts (misclassified negatives)
        confidence_level: Confidence level (e.g., 0.95 for 95% UCB)
    
    Returns:
        Upper confidence bound for FAR
    """
    if n_negatives == 0:
        return 1.0  # No data, worst case
    
    if n_false_accepts == 0:
        # Clopper-Pearson: if x=0, UCB = 1 - (alpha/2)^(1/n)
        return 1.0 - (1 - confidence_level) ** (1.0 / n_negatives)
    
    if n_false_accepts >= n_negatives:
        return 1.0  # All are false accepts
    
    # Clopper-Pearson: Beta distribution quantile
    # UCB = Beta(1-alpha, x, n-x+1) where x = n_false_accepts
    ucb = beta.ppf(confidence_level, n_false_accepts + 1, n_negatives - n_false_accepts)
    return float(ucb)


def compute_frr_ucb(n_positives: int, n_rejects: int, confidence_level: float) -> float:
    """
    Compute FRR confidence upper bound using Clopper-Pearson exact method.
    
    Args:
        n_positives: Number of positive samples (ground truth positives)
        n_rejects: Number of rejects/fail-safe (non-accepts for positives)
        confidence_level: Confidence level (e.g., 0.95 for 95% UCB)
    
    Returns:
        Upper confidence bound for FRR
    """
    if n_positives == 0:
        return 1.0
    
    if n_rejects == 0:
        return 1.0 - (1 - confidence_level) ** (1.0 / n_positives)
    
    if n_rejects >= n_positives:
        return 1.0
    
    ucb = beta.ppf(confidence_level, n_rejects + 1, n_positives - n_rejects)
    return float(ucb)


def compute_far_point_estimate(n_negatives: int, n_false_accepts: int) -> float:
    """Compute point estimate of FAR."""
    if n_negatives == 0:
        return 0.0
    return n_false_accepts / n_negatives


def compute_frr_point_estimate(n_positives: int, n_rejects: int) -> float:
    """Compute point estimate of FRR."""
    if n_positives == 0:
        return 0.0
    return n_rejects / n_positives


def compute_frr_lcb(n_positives: int, n_rejects: int, confidence_level: float) -> float:
    """
    Compute FRR confidence lower bound (Clopper-Pearson).
    Pr(FRR >= LCB) >= 1 - confidence_level in the one-sided reading.
    Used for AuditSCP conservative interval: [LCB^s_k, UCB^s_k] etc.

    Args:
        n_positives: Number of positive samples
        n_rejects: Number of rejects
        confidence_level: One-sided level for the upper tail (e.g. 0.95)

    Returns:
        Lower confidence bound for FRR
    """
    if n_positives == 0:
        return 0.0
    if n_rejects == 0:
        return 0.0
    if n_rejects >= n_positives:
        return 1.0
    return float(beta.ppf(1.0 - confidence_level, n_rejects, n_positives - n_rejects + 1))
