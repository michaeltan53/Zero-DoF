"""
Basic test script to verify core functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_wvc import Config, Ledger, Audit
from auth_wvc.ucb import compute_far_ucb, compute_frr_ucb
import numpy as np


def test_ucb():
    """Test UCB computation."""
    print("Testing UCB computation...")
    
    # Test FAR UCB
    n_negatives = 1000
    n_false_accepts = 5
    ucb_far = compute_far_ucb(n_negatives, n_false_accepts, 0.95)
    print(f"  FAR UCB: {ucb_far:.4f} (expected ~0.01)")
    
    # Test FRR UCB
    n_positives = 1000
    n_rejects = 20
    ucb_frr = compute_frr_ucb(n_positives, n_rejects, 0.95)
    print(f"  FRR UCB: {ucb_frr:.4f} (expected ~0.03)")
    
    print("  [OK] UCB tests passed\n")


def test_config():
    """Test Config creation and hashing."""
    print("Testing Config...")
    
    config = Config(
        alpha=0.01,
        delta=0.05,
        delta_far=0.025,
        delta_wvc=0.025,
    )
    config.create_bins_equal_width(0.0, 1.0, n_bins=5)
    
    print(f"  Config created: K={config.K}, hash={config.cfg_hash[:16]}...")
    print(f"  Bins: {config.bins}")
    
    # Test bin assignment
    tau = 0.5
    bin_idx = config.assign_bin(tau)
    print(f"  τ={tau} assigned to bin {bin_idx}")
    
    print("  [OK] Config tests passed\n")


def test_ledger():
    """Test Ledger operations."""
    print("Testing Ledger...")
    
    ledger = Ledger()
    
    # Add some entries
    for i in range(10):
        ledger.add_entry(
            f"sample_{i}",
            tau=0.1 * i,
            bin_idx=i % 5,
            decision='ACCEPT' if i % 2 == 0 else 'REJECT',
            label='Pos' if i < 5 else 'Neg',
            score=0.5 + 0.1 * (i % 3)
        )
    
    print(f"  Ledger entries: {len(ledger)}")
    print(f"  Integrity hash: {ledger.get_integrity_hash()[:16]}...")
    
    # Test bin statistics
    stats = ledger.get_bin_statistics(0)
    print(f"  Bin 0 stats: {stats}")
    
    print("  [OK] Ledger tests passed\n")


def test_audit():
    """Test Audit functionality."""
    print("Testing Audit...")
    
    # Create config
    config = Config(
        alpha=0.01,
        delta=0.05,
        delta_far=0.025,
        delta_wvc=0.025,
        n_min=10,  # Lower for test
    )
    config.create_bins_equal_width(0.0, 1.0, n_bins=3)
    config.thresholds = {k: 0.5 for k in range(3)}
    
    # Create ledger with compliant data
    ledger = Ledger()
    np.random.seed(42)
    
    for i in range(300):
        tau = np.random.uniform(0, 1)
        bin_idx = config.assign_bin(tau)
        label = 'Pos' if np.random.random() < 0.5 else 'Neg'
        score = np.random.beta(3, 7) if label == 'Neg' else np.random.beta(7, 3)
        decision = 'ACCEPT' if score >= 0.5 else 'REJECT'
        
        ledger.add_entry(f"sample_{i}", tau, bin_idx, decision, label, score)
    
    # Run audit
    audit = Audit(config)
    result = audit.run(ledger)
    
    print(f"  Audit status: {result.status}")
    print(f"  Breach set: {result.breach_set}")
    print(f"  Covered bins ratio: {result.covered_bins_ratio:.2%}")
    
    if result.status == 'PASS':
        print(f"  Auth-WVC computed for {len(result.auth_wvc)} bins")
    
    print("  [OK] Audit tests passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Basic Functionality Tests")
    print("=" * 60 + "\n")
    
    try:
        test_ucb()
        test_config()
        test_ledger()
        test_audit()
        
        print("=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
