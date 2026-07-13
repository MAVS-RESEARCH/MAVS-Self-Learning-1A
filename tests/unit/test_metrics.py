import pandas as pd

from mavs10d.metrics.calibration import calibration_error
from mavs10d.metrics.collapse import correlation_collapse_sensitivity
from mavs10d.metrics.dynamic import adaptation_lag, recovery_lag, trace_completeness
from mavs10d.metrics.episode_metrics import episode_rows, iter_step_rows
from mavs10d.metrics.safety_utility import (
    false_rejection_rate,
    safety_utility_frontier,
    unsafe_acceptance_rate,
)


def test_phase6_metrics_cover_safety_utility_dynamic_and_collapse() -> None:
    frame = pd.DataFrame(list(iter_step_rows(_records())))
    episodes = episode_rows(frame)

    assert unsafe_acceptance_rate(frame) == 0.5
    assert false_rejection_rate(frame) == 0.5
    assert episodes["catastrophic_episode"].iloc[0] is True or bool(episodes["catastrophic_episode"].iloc[0])
    assert adaptation_lag(frame) == 1.0
    assert recovery_lag(frame) == 1.0
    assert trace_completeness(frame)["trace_completeness"] == 1.0
    assert calibration_error(frame, bins=2) >= 0.0
    assert correlation_collapse_sensitivity(frame)["correlation_collapse_sensitivity"] != 0.0
    frontier = safety_utility_frontier(frame, thresholds=[0.25, 0.75])
    assert list(frontier["threshold"]) == [0.25, 0.75]


def _records() -> list[dict[str, object]]:
    base = {
        "run_id": "run",
        "config_hash": "hash",
        "git_commit": "commit",
        "environment_id": "env",
        "environment_family": "tool_use_security",
        "method_id": "mavs_gc",
        "seed": 10000,
        "episode_id": "ep",
        "hidden_label_hash": "hidden",
        "trace_complete": True,
        "created_at_utc": "2026-07-04T00:00:00+00:00",
        "metadata": {"benchmark_set": "dynamic_governance_v1_final", "experiment_code": "E1"},
        "candidate": {"action_type": "tool_call", "confidence": 0.8, "specialist_outputs": {"a": {"score": 0.8}}},
        "observation": {"risk_context": {"environment_family": "tool_use_security"}},
    }
    trace = {
        "specialist_id": ["a"],
        "representation_hash": "r",
        "support_score": 0.8,
        "confidence": 0.8,
        "diagnostic_values": {},
        "raw_severity": 0.1,
        "normalized_severity": 0.1,
        "final_threshold": 0.5,
    }
    rows = []
    specs = [
        (0, "accept", 0.80, True, False, "correlated_failure", 0.6, "reject", ["shared_wrong_premise"]),
        (1, "reject", 0.90, False, False, "correlated_failure", 0.6, "reject", ["shared_wrong_premise"]),
        (2, "reject", 0.20, False, True, "recovery", 0.1, "accept", []),
        (3, "accept", 0.10, False, False, "recovery", 0.1, "accept", []),
    ]
    for step, decision, risk, unsafe_accepted, false_rejected, phase, level, expected, transforms in specs:
        record = dict(base)
        record.update(
            {
                "step_id": step,
                "decision": {
                    "decision": decision,
                    "risk_score": risk,
                    "severity": risk,
                    "threshold": 0.5,
                    "trace": trace,
                },
                "step_result": {
                    "reward": -1.0 if unsafe_accepted else (-0.25 if false_rejected else 1.0),
                    "unsafe_accepted": unsafe_accepted,
                    "false_rejected": false_rejected,
                    "info": {
                        "expected_decision": expected,
                        "active_phase": phase,
                        "corruption_level": level,
                        "environment_family": "tool_use_security",
                        "transform_history": [{"type": item} for item in transforms],
                    },
                },
            }
        )
        rows.append(record)
    return rows
