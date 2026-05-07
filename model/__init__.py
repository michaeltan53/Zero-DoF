"""
Auth-WVC: From Vulnerable Promises to Auditable Security Claims
Ch4 (Config, Ledger, Audit); Ch3 (SCP, monotonic gating, AuditSCP); Ch5 (compile, trusted shell, invariants).
"""

from .config import Config
from .ledger import Ledger
from .audit import Audit
from .ucb import compute_far_ucb, compute_frr_ucb, compute_frr_lcb
from .image_authenticator import ImageAuthenticator, DummyImageAuthenticator, TierATauComputer
from .image_loader import ImageDataset, ImageDataGenerator
from .compile import (
    compute_t_low_env,
    compile_omega_lookup,
    compile_thresholds_from_calibration,
    compile_config_extended,
    DEFAULT_REASON_CODES,
)
from .trusted_shell import (
    envelope_decision,
    get_omega_for_bin,
    step_with_ledger,
    apply_guard_override,
)
from .invariants import (
    check_I1_cfg_hash,
    check_I2_monotonic,
    check_I5_chain,
    check_I6_full_table,
    run_invariants_checks,
)
from .scp import (
    advantage_difference,
    oracle_hard_selector,
    oracle_sequence,
    advantage_difference_sequence,
    check_scp_deterministic,
    critical_index_from_delta,
    count_switches_in_oracle,
)
from .audit_scp import (
    run_audit_scp,
    AuditSCPResult,
    sign_state,
    conservative_advantage_ci,
    cross_count_from_signs,
)
from .monotonic_gating import (
    isotonic_projection,
    is_monotonic_non_decreasing,
    weight_tv,
    count_monotonic_violations,
    fused_score,
    fused_score_vectorized,
)

__all__ = [
    'Config', 'Ledger', 'Audit',
    'compute_far_ucb', 'compute_frr_ucb', 'compute_frr_lcb',
    'ImageAuthenticator', 'DummyImageAuthenticator', 'TierATauComputer',
    'ImageDataset', 'ImageDataGenerator',
    'compute_t_low_env', 'compile_omega_lookup', 'compile_thresholds_from_calibration',
    'compile_config_extended', 'DEFAULT_REASON_CODES',
    'envelope_decision', 'get_omega_for_bin', 'step_with_ledger', 'apply_guard_override',
    'check_I1_cfg_hash', 'check_I2_monotonic', 'check_I5_chain', 'check_I6_full_table',
    'run_invariants_checks',
    'advantage_difference', 'oracle_hard_selector', 'oracle_sequence',
    'advantage_difference_sequence', 'check_scp_deterministic',
    'critical_index_from_delta', 'count_switches_in_oracle',
    'run_audit_scp', 'AuditSCPResult', 'sign_state', 'conservative_advantage_ci',
    'cross_count_from_signs',
    'isotonic_projection', 'is_monotonic_non_decreasing', 'weight_tv',
    'count_monotonic_violations', 'fused_score', 'fused_score_vectorized',
]
