"""
Auditable Invariants (Chapter 5.1.3, Table 5.1)

I1: Threshold immutability (cfg_hash consistent; no runtime rewrite)
I2: Monotonic compliance (omega_lookup non-decreasing; omega_t = omega_lookup[bin_id])
I3: Decision replay (Replay(Config, Ledger) matches L_t)
I4: Fail-safe (exception -> FAIL-SAFE; reason in Config enum)
I5: Evidence integrity (H_t = SHA256(cfg_hash || H_{t-1} || CanonicalJSON(L_t)))
I6: Forced disclosure (report includes full Bin_Table; highlight breach bins)
"""

from typing import List, Tuple, Optional, Dict, Any
from .config import Config
from .ledger import Ledger
from .monotonic_gating import is_monotonic_non_decreasing
import hashlib
import json


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def check_I1_cfg_hash(config: Config, expected_cfg_hash: Optional[str] = None) -> Tuple[bool, str]:
    """
    I1: Threshold immutability. Assert cfg_hash is consistent; no runtime rewrite.
    If expected_cfg_hash given, must match config.cfg_hash.
    """
    current = getattr(config, 'cfg_hash', None)
    if not current:
        return False, 'I1: cfg_hash missing'
    if expected_cfg_hash is not None and current != expected_cfg_hash:
        return False, f'I1: CFG_HASH_MISMATCH (expected {expected_cfg_hash[:16]}..., got {current[:16]}...)'
    return True, 'I1: OK'


def check_I2_monotonic(config: Config, epsilon: Optional[float] = None) -> Tuple[bool, str]:
    """
    I2: omega_lookup[k+1] >= omega_lookup[k] - epsilon.
    """
    omega = getattr(config, 'omega_lookup', None)
    if omega is None:
        return True, 'I2: no omega_lookup (skip)'
    eps = epsilon if epsilon is not None else getattr(config, 'epsilon_monotonic', 0.0)
    import numpy as np
    w = np.asarray(omega).ravel()
    if len(w) <= 1:
        return True, 'I2: OK'
    for k in range(len(w) - 1):
        if w[k + 1] < w[k] - eps - 1e-9:
            return False, f'I2: monotonic violation at k={k} (omega[{k}]={w[k]:.4f}, omega[{k+1}]={w[k+1]:.4f})'
    return True, 'I2: OK'


def check_I5_chain(ledger: Ledger, config: Config) -> Tuple[bool, str]:
    """
    I5: Recompute hash chain with cfg_hash binding; must match ledger.hash_chain.
    """
    if len(ledger) == 0:
        return True, 'I5: OK (empty)'
    cfg_hash = getattr(config, 'cfg_hash', '') or getattr(ledger, 'cfg_hash', '')
    prev = ''
    # Early-exit: stop at first mismatch to model practical tamper detection cost
    for i, entry in enumerate(ledger.entries):
        entry_copy = {k: v for k, v in entry.items() if k != '_hash'}
        entry_str = _canonical_json(entry_copy)
        payload = cfg_hash + prev + entry_str
        H_t = hashlib.sha256(payload.encode()).hexdigest()
        if i >= len(ledger.hash_chain) or ledger.hash_chain[i] != H_t:
            return False, f'I5: CHAIN_BROKEN (mismatch at index {i})'
        prev = H_t
    # Extra length in stored chain is also invalid
    if len(ledger.hash_chain) != len(ledger.entries):
        return False, 'I5: CHAIN_BROKEN (chain length mismatch)'
    return True, 'I5: OK'


def check_I6_full_table(result_has_bin_table: bool, result_has_breach_highlight: bool) -> Tuple[bool, str]:
    """
    I6: Report must include full Bin_Table and highlight {k: UCB_k > alpha}.
    """
    if not result_has_bin_table:
        return False, 'I6: INVALID_REPORT (missing full Bin_Table)'
    if not result_has_breach_highlight:
        return False, 'I6: INVALID_REPORT (breach bins not highlighted)'
    return True, 'I6: OK'


def run_invariants_checks(
    config: Config,
    ledger: Ledger,
    audit_result_bin_table: bool = True,
    audit_result_breach_set: Optional[List[int]] = None,
) -> Dict[str, Tuple[bool, str]]:
    """
    Run I1, I2, I5, I6 checks (I3/I4 require full replay and guard logic; done in Audit).
    Returns dict invariant_id -> (passed, message).
    """
    out = {}
    ok, msg = check_I1_cfg_hash(config)
    out['I1'] = (ok, msg)
    ok, msg = check_I2_monotonic(config)
    out['I2'] = (ok, msg)
    ok, msg = check_I5_chain(ledger, config)
    out['I5'] = (ok, msg)
    ok, msg = check_I6_full_table(
        result_has_bin_table=audit_result_bin_table,
        result_has_breach_highlight=audit_result_breach_set is not None,
    )
    out['I6'] = (ok, msg)
    return out
