"""
Ledger: Running Ledger (Fact Record)
Records minimal replayable fields for each sampling unit
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import hashlib
import json


def _canonical_json(obj: dict) -> str:
    """Canonical JSON for deterministic hashing (I5)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


class Ledger:
    """
    Running ledger that records facts for each sampling unit.
    
    Each entry records: (id, tau, bin_idx, decision, label)
    Chapter 5: optional cfg_hash-bound chain H_t = SHA256(cfg_hash || H_{t-1} || CanonicalJSON(L_t)).
    """
    
    def __init__(self, cfg_hash: Optional[str] = None):
        """
        Initialize empty ledger.
        cfg_hash: If set, hash chain uses I5 binding: H_t = SHA256(cfg_hash || H_{t-1} || L_t).
        """
        self.entries: List[Dict[str, Any]] = []
        self.hash_chain: List[str] = []
        self.cfg_hash = cfg_hash or ''
    
    def add_entry(
        self,
        sample_id: str,
        tau: float,
        bin_idx: int,
        decision: str,
        label: str,
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add an entry to the ledger.
        
        Args:
            sample_id: Unique identifier for sampling unit
            tau: Strength coordinate value
            bin_idx: Assigned bin index
            decision: Final decision (ACCEPT, REJECT, FAIL-SAFE)
            label: Ground truth label (Pos, Neg)
            score: Optional decision score
            metadata: Optional additional metadata
        """
        assert decision in ['ACCEPT', 'REJECT', 'FAIL-SAFE'], \
            f"Invalid decision: {decision}"
        assert label in ['Pos', 'Neg'], f"Invalid label: {label}"
        
        entry = {
            'id': sample_id,
            'tau': tau,
            'bin_idx': bin_idx,
            'decision': decision,
            'label': label,
            'score': score,
            'metadata': metadata or {}
        }
        
        self.entries.append(entry)
        
        # Update hash chain (I5): H_t = SHA256(cfg_hash || H_{t-1} || CanonicalJSON(entry))
        entry_str = _canonical_json(entry)
        prev_hash = self.hash_chain[-1] if self.hash_chain else ''
        payload = (self.cfg_hash or '') + prev_hash + entry_str
        new_hash = hashlib.sha256(payload.encode()).hexdigest()
        self.hash_chain.append(new_hash)
    
    def add_entry_from_L_t(self, L_t: Dict[str, Any]) -> str:
        """
        Chapter 5: Append one frame from L_t (Step output). Uses cfg_hash if set on Ledger.
        L_t must contain: id, bin_id, D_t, label, Phi_t;
        optional fields (all auditable from Config+Ledger and used for Fig 6.3):
          - tau
          - reason_code (enum)
          - guard_triggered (bool)
          - guard_metric (numeric trigger statistic, e.g., step-delta, drift-stat, timeout_ms)
          - fsm_state
          - omega_t
          - route_key

        Returns H_t (new chain head).
        """
        meta_keys = (
            'reason_code',
            'guard_triggered',
            'guard_metric',
            'fsm_state',
            'omega_t',
            'route_key',
        )
        self.add_entry(
            sample_id=L_t['id'],
            tau=L_t.get('tau', 0.0),
            bin_idx=L_t['bin_id'],
            decision=L_t['D_t'],
            label=L_t['label'],
            score=L_t.get('Phi_t'),
            metadata={k: L_t[k] for k in meta_keys if k in L_t},
        )
        return self.get_integrity_hash()
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert ledger to pandas DataFrame."""
        return pd.DataFrame(self.entries)
    
    def get_bin_statistics(self, bin_idx: int) -> Dict[str, int]:
        """
        Get statistics for a specific bin.
        
        Returns:
            Dictionary with counts: n_negatives, n_positives, n_false_accepts, n_rejects
        """
        bin_entries = [e for e in self.entries if e['bin_idx'] == bin_idx]
        
        n_negatives = sum(1 for e in bin_entries if e['label'] == 'Neg')
        n_positives = sum(1 for e in bin_entries if e['label'] == 'Pos')
        
        # False accepts: negatives that were ACCEPTED
        n_false_accepts = sum(
            1 for e in bin_entries 
            if e['label'] == 'Neg' and e['decision'] == 'ACCEPT'
        )
        
        # Rejects (for FRR): positives that were not ACCEPTED
        n_rejects = sum(
            1 for e in bin_entries
            if e['label'] == 'Pos' and e['decision'] != 'ACCEPT'
        )
        
        return {
            'n_negatives': n_negatives,
            'n_positives': n_positives,
            'n_false_accepts': n_false_accepts,
            'n_rejects': n_rejects,
            'n_total': len(bin_entries)
        }
    
    def get_integrity_hash(self) -> str:
        """Get final hash for integrity verification."""
        if not self.hash_chain:
            return ""
        return self.hash_chain[-1]
    
    def __len__(self):
        return len(self.entries)
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'Ledger':
        """Create Ledger from DataFrame."""
        ledger = cls()
        for _, row in df.iterrows():
            ledger.add_entry(
                sample_id=str(row['id']),
                tau=float(row['tau']),
                bin_idx=int(row['bin_idx']),
                decision=str(row['decision']),
                label=str(row['label']),
                score=row.get('score'),
                metadata=row.get('metadata', {})
            )
        return ledger

    @classmethod
    def from_export(
        cls,
        entries: List[Dict[str, Any]],
        hash_chain: List[str],
        cfg_hash: Optional[str] = None,
    ) -> 'Ledger':
        """
        Reconstruct Ledger from exported (Config + Ledger) only.
        Used for independent replay: third party loads exported data and re-runs Audit
        without access to the original system.
        """
        ledger = cls(cfg_hash=cfg_hash or '')
        ledger.entries = list(entries)
        ledger.hash_chain = list(hash_chain)
        return ledger
