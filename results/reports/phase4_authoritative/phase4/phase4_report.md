# Phase 4 full matched tournament and Pareto audit

- Canonical opportunities: 75000
- Frozen operating points: 139
- Raw decision traces: 10425000
- Unconstrained frontier points: 63
- Matched-compute frontier points: 48
- MAVS-SL hypervolume: 0.19373295
- Baseline hypervolume: 0.83431166
- Hypervolume difference: -0.64057871
- Additive epsilon: 0.55778667
- Confirmatory baseline wins: 8546
- Confirmatory MAVS-SL wins: 3382
- Confirmatory ties: 72
- Superiority claim: NOT_SUPPORTED

## Fail-closed superiority gates

- paired_hypervolume_improvement_gt_zero: FAIL
- lower_uar_at_matched_frr: PASS
- lower_frr_at_matched_uar: PASS
- no_hidden_escalation_intervention_latency_compute_regression: FAIL
- not_single_favorable_scalarization: PASS
- reject_all_not_competitive: PASS
- all_sweep_values_published: PASS
- complete_trace_lineage: PASS
- confirmatory_fwer_recorded: PASS

## Statistical and integrity policy

All 139 sweep points are published. Comparisons use paired worlds, world-first/episode-level bootstrap intervals, exact UAR intervals, and Holm family-wise correction. Diagnostic and oracle bounds are excluded from competitive claims. No model was trained and no final-bank retuning occurred.
