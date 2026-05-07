"""
Trusted Shell (Chapter 5.3, Min-TCB)

Step(I_t, Config, H_{t-1}) -> (D_t, L_t, H_t):
- Monotonic lookup: omega_t = omega_lookup[bin_id]
- Envelope three-way decision: Phi <= t_low_env -> ACCEPT; Phi >= t_high -> REJECT; else FAIL-SAFE (UNCERTAIN)
- Guard override -> FAIL-SAFE with reason
- Ledger append with H_t = SHA256(cfg_hash || H_{t-1} || CanonicalJSON(L_t))
"""

import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from .config import Config
from .ledger import Ledger


def _canonical_json(obj: Dict[str, Any]) -> str:
    """Canonical JSON for deterministic hashing (sort_keys=True, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def envelope_decision(
    phi: float,
    bin_id: int,
    config: Config,
) -> Tuple[str, str]:
    """
    Three-way decision using envelope thresholds (Lemma 5.1).
    Phi is "anomaly score" (lower = more trustworthy). Accept iff Phi <= threshold.

    Args:
        phi: fusion/anomaly score for current frame
        bin_id: routed bin index k
        config: must have t_low_env, t_high (dict or getattr)

    Returns:
        (decision, reason_code): 'ACCEPT'|'REJECT'|'FAIL-SAFE', reason string
    """
    t_low_env = getattr(config, 't_low_env', None) or getattr(config, 'thresholds', {})
    t_high = getattr(config, 't_high', None) or getattr(config, 'thresholds', {})
    if isinstance(t_low_env, dict):
        t_low_k = t_low_env.get(bin_id, t_low_env.get('default', 0.4))
    else:
        t_low_k = 0.4
    if isinstance(t_high, dict):
        t_high_k = t_high.get(bin_id, t_high.get('default', 0.6))
    else:
        t_high_k = 0.6
    if phi <= t_low_k:
        return 'ACCEPT', 'ACCEPT'
    if phi >= t_high_k:
        return 'REJECT', 'REJECT'
    return 'FAIL-SAFE', 'UNCERTAIN'


def get_omega_for_bin(config: Config, bin_id: int) -> float:
    """I2: omega_t = omega_lookup[bin_id]. Returns 0..1."""
    omega_lookup = getattr(config, 'omega_lookup', None)
    if omega_lookup is not None and 0 <= bin_id < len(omega_lookup):
        return float(omega_lookup[bin_id])
    return getattr(config, 'thresholds', {}).get(bin_id, 0.5)


def step_with_ledger(
    config: Config,
    ledger: Ledger,
    sample_id: str,
    bin_id: int,
    phi: float,
    decision: str,
    reason_code: str,
    label: str,
    tau: Optional[float] = None,
    guard_triggered: bool = False,
    guard_metric: Optional[float] = None,
    fsm_state: str = 'NORMAL',
    route_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Append one frame to ledger with cfg_hash-bound chain (I5).
    L_t: seq, route_key, bin_id, omega_t, Phi_t, D_t, reason_code, guard_flag, FSM_state, label, ...

    Returns:
        (H_t, reason_code)
    """
    if not getattr(ledger, 'cfg_hash', '') and getattr(config, 'cfg_hash', None):
        ledger.cfg_hash = config.cfg_hash
    omega_t = get_omega_for_bin(config, bin_id)
    route_key = route_key or str(bin_id)
    tau_val = tau if tau is not None else (bin_id + 0.5) / max(config.K, 1)
    L_t = {
        'id': sample_id,
        'seq': len(ledger) + 1,
        'route_key': route_key,
        'bin_id': bin_id,
        'omega_t': omega_t,
        'Phi_t': phi,
        'D_t': decision,
        'reason_code': reason_code,
        'guard_triggered': guard_triggered,
        'guard_metric': guard_metric,
        'fsm_state': fsm_state,
        'tau': tau_val,
        'label': label,
    }
    H_t = ledger.add_entry_from_L_t(L_t)
    return H_t, reason_code


def apply_guard_override(decision: str, reason_code: str, guard_triggered: bool) -> Tuple[str, str]:
    """I4: If guard triggered, force FAIL-SAFE; reason in enum."""
    if guard_triggered:
        return 'FAIL-SAFE', reason_code if reason_code in ('GUARD_STEP', 'GUARD_DRIFT', 'GUARD_TIMEOUT', 'GUARD_UNKNOWN') else 'GUARD_UNKNOWN'
    return decision, reason_code
