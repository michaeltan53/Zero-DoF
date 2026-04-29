# Auth-WVC: From Vulnerable Promises to Auditable Security Claims

This repository implements **Chapter 4** (Auth-WVC), **Chapter 3/6** (SCP, monotonic gating, AuditSCP), and **Chapter 5/6** (contract compile, trusted shell, invariants; contract closure, risk transformation, auditability) of the research paper.

## Overview

The framework provides:
- **Ch4**: Rigid evaluation contracts, pre-commitment, Ledger, deterministic Audit, Auth-WVC curves
- **Ch3**: SCP, Oracle single-switch, AuditSCP (SCP_PASS), monotonic gating (W�? isotonic projection)
- **Ch5**: Compile �?Config (t_low_env, omega_lookup); Step �?Ledger (envelope decision, I5 hash chain); invariants I1–I6; Min-TCB (Trusted_Shell vs Untrusted_Core)
- **Ch6 (SCP)**: SCP existence, structured constraint (Table 1), ablation, adversarial structure audit
- **Ch6 (contract)**: Contract closure (Fig 6.1, Table 6.3), risk transformation (Fig 6.2, 6.3), auditability overhead and tamper detection (Fig 6.4, Table 6.4)
- **Ch6 (E4 LLM runtime safety)**: Track B online circuit breaker vs B1/B2, optional-stopping baseline table, and end-to-end multi-session aggregate table (Fig 6.5-1~6.5-4, Table 6.5/6.6)
- **CCS11 supplement**: strong architecture baselines, concrete multi-domain workload spec, benign utility/availability, sensitivity + structural ablation, adaptive attacker stress, statistical rigor table, cost decomposition + Min-TCB size, SCP expressiveness/coverage

## Project Structure

```
CCS/
├── auth_wvc/              # Core framework
�?  ├── config.py, ledger.py, audit.py, ucb.py   # Ch4
�?  ├── compile.py, trusted_shell.py, invariants.py  # Ch5
�?  ├── scp.py, audit_scp.py, monotonic_gating.py   # Ch3
├── docs/
�?  ├── ch3_theory.md, ch5_architecture.md
�?  ├── ch6_experiments.md, ch6_contract_experiments.md
├── experiments/
�?  ├── experiment_a_promise_gap.py, experiment_b_end_to_end_audit.py  # Ch4
�?  ├── experiment_scp_existence.py ... experiment_adversarial_audit.py # Ch6 SCP
�?  ├── experiment_contract_closure.py, experiment_risk_transformation.py,
�?  └── experiment_auditability_overhead.py  # Ch5/6 contract
├── run_all_experiments.py # Ch4 + Ch6 + Ch5/6
└── requirements.txt
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run All Experiments

```bash
python run_all_experiments.py
```

This runs **Ch4** (A, B), **Ch6** (SCP: 6.2�?.5), **Ch5/6** (contract: contract closure, risk transformation, auditability overhead), **Ch6 E4** (LLM runtime safety online circuit breaker), and the **CCS11 supplemental suite**.

### Run Individual Experiments

```bash
# Ch4
python experiments/experiment_a_promise_gap.py
python experiments/experiment_b_end_to_end_audit.py

# Ch6 (SCP)
python experiments/experiment_scp_existence.py
python experiments/experiment_structured_constraint.py
python experiments/experiment_ablation.py
python experiments/experiment_adversarial_audit.py

# Ch5/6 (contract)
python experiments/experiment_contract_closure.py
python experiments/experiment_risk_transformation.py
python experiments/experiment_auditability_overhead.py

# Ch6 (E4 LLM runtime safety)
python experiments/experiment_llm_runtime_safety.py

# Ch6 timeline visualization (Track A + closed-loop trace)
python experiments/experiment_track_a_collapse_timeline.py
python experiments/experiment_contract_audit_enforcement_timeline.py

# Ch6.x Track B instantiation on replayable LLM trajectories
python experiments/experiment_trackb_llm_instantiation.py

# CCS11 supplemental suite (strong baseline + utility + sensitivity + stress)
python experiments/experiment_ccs11_strong_suite.py

# Reviewer-priority addenda pack
python experiments/experiment_ccs11_reviewer_addenda.py
```

## Core Components

### Config (Configuration Charter)

Pre-committed configuration that includes:
- Contract parameters: `α` (FAR target), `δ` (confidence budget)
- Bin definitions: Strength coordinate `τ` partitioning
- Thresholds: Decision thresholds per bin (from validation set)
- UCB method: Confidence bound computation method
- Coverage constraints: Minimum samples per bin, coverage thresholds

### Ledger (Running Ledger)

Records minimal replayable fields for each sampling unit:
- `id`: Sample identifier
- `τ`: Strength coordinate value
- `bin_idx`: Assigned bin index
- `decision`: Final decision (ACCEPT, REJECT, FAIL-SAFE)
- `label`: Ground truth (Pos, Neg)

### Audit (Final Judgment)

Deterministic audit that outputs:
- `status`: PASS / FAIL / INVALID
- `breach_set`: List of bins violating FAR �?α
- `auth_wvc`: FRR upper bounds (only if PASS)
- `bin_statistics`: Per-bin statistics

## Key Features

### Rigid Contract Semantics

1. **Uniformity (C1)**: FAR constraint must hold simultaneously for ALL bins
2. **Pre-commitment (C2)**: All parameters hash-locked before testing
3. **Finality (C3)**: Compliance determined solely by Audit output

### Audit Rules (R1-R4)

- **R1**: Threshold fixation (no test-time adjustment)
- **R2**: Bin determinism (no gerrymandering)
- **R3**: Coverage constraints (minimum samples, coverage thresholds)
- **R4**: FAIL-SAFE auditability (objective trigger conditions)

### Evidence Tiers

- **Tier-A**: Physical parameters, deterministic computation, system-agnostic
- **Tier-B**: Public estimators with error bounds (diagnostic only)
- **Tier-C**: Subjective or system-generated (no audit validity)

## Experiment A: Promise Gap

Demonstrates three common evaluation freedoms that can fake compliance:

1. **Selective Interval Reporting**: Hide tail bins that violate constraints
2. **Post-hoc Thresholding**: Adjust thresholds after seeing test data
3. **Non-pre-registered Filtering**: Filter samples to hide false accepts

The experiment shows that while these methods can produce "seemingly compliant" reports, Auth-WVC audit deterministically reveals violations.

## Experiment B: End-to-End Audit

Demonstrates the complete workflow:

1. **Pre-commit Config**: Hash-lock all parameters
2. **Generate Ledger**: Record test results
3. **Run Audit**: Deterministic compliance checking
4. **Report Auth-WVC**: FRR upper bounds (only if PASS)

## Output Figures and Tables

**Ch4**
- `experiments/fig6_1_promise_gap.png`, `experiments/fig6_2_auth_wvc.png`

**Ch6 (SCP)**  
fig1_scp_existence.png, table1_structured_constraint.txt, fig2_ablation.png, fig3_adversarial_audit.png

**Ch5/6 (contract)**  
fig6_1_contract_closure.png, table6_3_bin_table.txt, fig6_2_risk_transformation.png, fig6_3_fail_safe_reasons.png, fig6_4_audit_overhead.png, table6_4_tamper_detection.txt, table6_replay_consistency.txt

**Ch6 (E4 LLM runtime safety)**  
fig6_5_1_evidence_trajectory.png, fig6_5_2_av_fa_budget.png, fig6_5_3_early_intercept.png, fig6_5_4_clause_scaling.png, table6_5_1_overhead.txt, table6_5_2_ablation.txt, table6_5_3_clause_scaling.txt, table6_5_fa_wilson.txt, table6_5_b2_calibration.txt, table6_5_q0_calibration.txt, table6_5_trackb_baselines.txt, table6_6_e2e_aggregate.txt, artifacts_e4/config_e4.json, artifacts_e4/D0_traces.jsonl, artifacts_e4/D1_traces.jsonl

**Ch6 timeline visualization**
- fig6_6_track_a_collapse_timeline.png
- fig6_7_contract_audit_enforcement_timeline.png
- data/track_a_collapse.csv (auto-generated demo input if missing)
- data/representative_session_step.csv, data/representative_session_event.csv (auto-generated from artifacts_e4 if missing)

**Ch6.x Track B instantiation**
- table6_15_trackb_llm_feature_mapping.txt
- table6_15_trackb_clause_config.txt
- table6_15_trackb_llm_instantiation_summary.txt
- fig6_12_trackb_llm_clause_evidence.png

**CCS11 supplement**
- table6_7_workload_profile.txt
- table6_8_arch_baselines_per_domain.txt
- table6_8_benign_utility.txt
- table6_9_sensitivity_grid.txt
- table6_10_component_ablation.txt
- table6_11_adaptive_attacker_stress.txt
- fig6_11_adaptive_attacker_stress.png
- table6_12_statistics_rigour.txt
- table6_13_cost_tcb_breakdown.txt
- table6_14_scp_expressiveness.txt

**Reviewer addenda**
- table6_3_benign_availability_addendum.txt
- table6_2_dmono_benign_delta_addendum.txt
- table6_6_track_a_full_workload_breakdown.txt
- fig6_6_track_a_full_clause_family_cdf.png
- table6_4_witness_targeted_stress.txt
- table6_4_witness_transition_matrix.txt
- table6_4_latency_p50_cross_arch.txt
- fig6_4_cross_arch_latency_cdf.png
- table6_3_headline_metrics_note.txt
- table6_4_far_vt_cta_semantic_note.txt
- table6_4_latency_boundary_reconciliation.txt

## Citation

If you use this code, please cite the corresponding paper.

## License

[Specify license]


