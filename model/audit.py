"""
Audit: Final Judgment and Compliance Clause
Deterministic audit that outputs Pass/Fail/Invalid status
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from .config import Config
from .ledger import Ledger
from .ucb import compute_far_ucb, compute_frr_ucb, compute_far_point_estimate, compute_frr_point_estimate


class AuditResult:
    """Result of audit execution."""
    
    def __init__(
        self,
        status: str,  # PASS, FAIL, INVALID
        breach_set: List[int],
        auth_wvc: Optional[Dict[int, float]] = None,
        bin_statistics: Optional[Dict[int, Dict[str, Any]]] = None,
        invalid_reason: Optional[str] = None,
        worst_bin_ucb_far: Optional[float] = None,
        covered_bins_ratio: Optional[float] = None,
    ):
        self.status = status
        self.breach_set = breach_set
        self.auth_wvc = auth_wvc or {}
        self.bin_statistics = bin_statistics or {}
        self.invalid_reason = invalid_reason
        self.worst_bin_ucb_far = worst_bin_ucb_far
        self.covered_bins_ratio = covered_bins_ratio
    
    def __repr__(self):
        return f"AuditResult(status={self.status}, breaches={len(self.breach_set)})"


class Audit:
    """
    Audit module that performs deterministic compliance checking.
    
    Implements rules R1-R4:
    R1: Threshold fixation (no test-time adjustment)
    R2: Bin determinism (no gerrymandering)
    R3: Coverage constraints
    R4: FAIL-SAFE auditability
    """
    
    def __init__(self, config: Config):
        """
        Initialize Audit with pre-committed Config.
        
        Args:
            config: Pre-committed configuration charter
        """
        self.config = config
    
    def run(self, ledger: Ledger) -> AuditResult:
        """
        Run audit on ledger.
        
        Args:
            ledger: Ledger containing test results
            
        Returns:
            AuditResult with status, breach_set, and statistics
        """
        # Check ledger integrity
        if len(ledger) == 0:
            return AuditResult(
                status='INVALID',
                breach_set=[],
                invalid_reason='Empty ledger'
            )
        
        # Compute bin statistics
        bin_stats = {}
        for k in range(self.config.K):
            bin_stats[k] = ledger.get_bin_statistics(k)
        
        # R3: Coverage constraints
        valid_bins = []
        indeterminate_bins = []
        
        for k in range(self.config.K):
            n_total = bin_stats[k]['n_total']
            if n_total < self.config.n_min:
                indeterminate_bins.append(k)
            else:
                valid_bins.append(k)
        
        indeterminate_ratio = len(indeterminate_bins) / self.config.K if self.config.K > 0 else 1.0
        coverage_ratio = len(valid_bins) / self.config.K if self.config.K > 0 else 0.0
        
        if indeterminate_ratio > self.config.indeterminate_threshold:
            return AuditResult(
                status='INVALID',
                breach_set=[],
                bin_statistics=bin_stats,
                invalid_reason=f'Too many indeterminate bins: {indeterminate_ratio:.2%} > {self.config.indeterminate_threshold:.2%}'
            )
        
        if coverage_ratio < self.config.coverage_threshold:
            return AuditResult(
                status='INVALID',
                breach_set=[],
                bin_statistics=bin_stats,
                invalid_reason=f'Insufficient coverage: {coverage_ratio:.2%} < {self.config.coverage_threshold:.2%}'
            )
        
        # Check FAR compliance for all valid bins
        breach_set = []
        worst_ucb_far = 0.0
        
        for k in valid_bins:
            stats = bin_stats[k]
            n_negatives = stats['n_negatives']
            n_false_accepts = stats['n_false_accepts']
            
            if n_negatives == 0:
                # No negative samples in this bin, skip FAR check
                continue
            
            # Compute UCB for FAR
            confidence_level = 1 - self.config.gamma_k[k]
            ucb_far = compute_far_ucb(n_negatives, n_false_accepts, confidence_level)
            
            # Check if UCB exceeds alpha
            if ucb_far > self.config.alpha:
                breach_set.append(k)
            
            worst_ucb_far = max(worst_ucb_far, ucb_far)
        
        # Determine status
        if len(breach_set) > 0:
            status = 'FAIL'
            auth_wvc = None  # Cannot report Auth-WVC if FAIL
        else:
            status = 'PASS'
            # Compute Auth-WVC (FRR upper bounds) for valid bins
            auth_wvc = {}
            for k in valid_bins:
                stats = bin_stats[k]
                n_positives = stats['n_positives']
                n_rejects = stats['n_rejects']
                
                if n_positives == 0:
                    auth_wvc[k] = 0.0  # No positives, FRR undefined
                    continue
                
                confidence_level = 1 - self.config.eta_k[k]
                ucb_frr = compute_frr_ucb(n_positives, n_rejects, confidence_level)
                auth_wvc[k] = ucb_frr
        
        # Add point estimates to bin statistics
        for k in valid_bins:
            stats = bin_stats[k]
            n_negatives = stats['n_negatives']
            n_positives = stats['n_positives']
            n_false_accepts = stats['n_false_accepts']
            n_rejects = stats['n_rejects']
            
            if n_negatives > 0:
                stats['far_point'] = compute_far_point_estimate(n_negatives, n_false_accepts)
            else:
                stats['far_point'] = 0.0
            
            if n_positives > 0:
                stats['frr_point'] = compute_frr_point_estimate(n_positives, n_rejects)
            else:
                stats['frr_point'] = 0.0
            
            # Compute UCBs for reporting
            if n_negatives > 0:
                confidence_level_far = 1 - self.config.gamma_k[k]
                stats['ucb_far'] = compute_far_ucb(n_negatives, n_false_accepts, confidence_level_far)
            else:
                stats['ucb_far'] = 0.0
            
            if n_positives > 0:
                confidence_level_frr = 1 - self.config.eta_k[k]
                stats['ucb_frr'] = compute_frr_ucb(n_positives, n_rejects, confidence_level_frr)
            else:
                stats['ucb_frr'] = 0.0
        
        return AuditResult(
            status=status,
            breach_set=breach_set,
            auth_wvc=auth_wvc,
            bin_statistics=bin_stats,
            worst_bin_ucb_far=worst_ucb_far,
            covered_bins_ratio=coverage_ratio
        )

    def generate_report_table(self, result: AuditResult) -> str:
        """
        Generate formatted audit report table (Table 6.1 format).
        
        Args:
            result: AuditResult from run()
            
        Returns:
            Formatted string table
        """
        lines = []
        lines.append("=" * 80)
        lines.append("Auth-WVC Compliance Audit Report")
        lines.append("=" * 80)
        lines.append("")
        
        # Header
        lines.append(f"{'k':<4} {'τ range':<20} {'n⁻':<8} {'m_FA':<8} {'FAR̂':<10} {'UCB_FAR':<12} {'≤α?'}")
        lines.append("-" * 80)
        
        # Bin rows
        for k in range(self.config.K):
            stats = result.bin_statistics.get(k, {})
            tau_min, tau_max = self.config.bins[k]
            tau_range = f"[{tau_min:.2f},{tau_max:.2f})"
            
            n_negatives = stats.get('n_negatives', 0)
            n_false_accepts = stats.get('n_false_accepts', 0)
            far_point = stats.get('far_point', 0.0)
            ucb_far = stats.get('ucb_far', 0.0)
            
            is_compliant = "✓" if ucb_far <= self.config.alpha else "✗"
            
            lines.append(
                f"{k:<4} {tau_range:<20} {n_negatives:<8} {n_false_accepts:<8} "
                f"{far_point:<10.4f} {ucb_far:<12.4f} {is_compliant}"
            )
        
        lines.append("-" * 80)
        lines.append("")
        
        # Summary
        lines.append("Audit Summary:")
        lines.append(f"  Status: {result.status}")
        lines.append(f"  α = {self.config.alpha:.4f}")
        lines.append(f"  δ_FAR = {self.config.delta_far:.4f}")
        lines.append(f"  K = {self.config.K}")
        lines.append(f"  cfg_hash = 0x{self.config.cfg_hash[:16]}...")
        lines.append(f"  |Breach_Set| = {len(result.breach_set)}")
        if result.breach_set:
            lines.append(f"  Breach bins: {result.breach_set}")
        if result.worst_bin_ucb_far is not None:
            lines.append(f"  worst-bin UCB_FAR = {result.worst_bin_ucb_far:.4f}")
        if result.covered_bins_ratio is not None:
            lines.append(f"  covered_bins_ratio = {result.covered_bins_ratio:.2%}")
        
        return "\n".join(lines)


def compute_fail_safe_reason_stats(ledger: Ledger) -> Dict[str, Dict[str, Any]]:
    """
    Compute FAIL-SAFE reason-code statistics from a Ledger.

    This is used for Fig 6.3 to demonstrate that reason_code is:
      - fully determined by (Config, observable guard metrics) at runtime, and
      - auditable afterwards by re-counting from Ledger alone.

    Returns:
        {
          scenario_key: {
             'N_total': int,
             'N_failsafe': int,
             'failsafe_rate': float,
             'reason_counts': {reason_code: count, ...},
          },
          ...
        }

    The caller is responsible for partitioning entries into scenarios
    (e.g., by prefixing sample_id or route_key); here we treat ledger-wide
    as a single scenario when used directly.
    """
    from collections import Counter

    total = len(ledger.entries)
    failsafe_entries = [e for e in ledger.entries if e.get('decision') == 'FAIL-SAFE']
    reason_counter = Counter()
    for e in failsafe_entries:
        meta = e.get('metadata') or {}
        rc = meta.get('reason_code') or 'UNKNOWN'
        reason_counter[rc] += 1
    N_failsafe = len(failsafe_entries)
    failsafe_rate = (N_failsafe / total) if total > 0 else 0.0
    return {
        'all': {
            'N_total': total,
            'N_failsafe': N_failsafe,
            'failsafe_rate': failsafe_rate,
            'reason_counts': dict(reason_counter),
        }
    }
