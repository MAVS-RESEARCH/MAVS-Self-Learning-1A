from __future__ import annotations

import pandas as pd

from mavs10d.metrics.phase8_integrity import deterministic_paired_interval, evaluate_terminal_records, paired_deltas


def test_terminal_metrics_recompute_protected_errors(phase7_truth) -> None:
    records = pd.DataFrame([
        {"case_id": row.case_id, "family": row.family, "terminal_action": row.expected_terminal, "external_escalate": int(row.expected_terminal == "ESCALATE"), "rounds": 0, "query_count": 0, "query_yield": 0.0, "scope_leakage": 0, "active_basis": 0, "irrelevant_activation": 0, "meta_hard_veto": 0, "uncertified_interaction": 0, "additive_severity_used": 0, "certificate_present": row.expected_terminal != "ESCALATE", "oracle_access": False}
        for row in phase7_truth.itertuples(index=False)
    ])
    _, metrics = evaluate_terminal_records(records, phase7_truth)
    assert metrics["uar"] == 0
    assert metrics["frr"] == 0
    assert metrics["closure_error"] == 0


def test_paired_deltas_use_reference_direction() -> None:
    assert paired_deltas({"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 1.0}) == {"x": 2.0, "y": -1.0}


def test_bootstrap_interval_is_deterministic() -> None:
    first = deterministic_paired_interval([0, 1, 1, 0], 123)
    second = deterministic_paired_interval([0, 1, 1, 0], 123)
    assert first == second
    assert first["n"] == 4
