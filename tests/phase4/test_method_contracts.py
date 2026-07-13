from __future__ import annotations

import inspect

import numpy as np

from mavs10d.baselines.phase4_base import decide_visible
from mavs10d.baselines.phase4_registry import load_operating_points


def test_every_non_oracle_point_executes_from_visible_features_only() -> None:
    fields = {
        name: np.asarray([0.2, 0.8])
        for name in (
            "risk_proxy confidence entropy margin uncertainty calibrated_risk conformal_pvalue disagreement variance "
            "mutual_information self_consistency provenance_quality evidence_available policy_conflict shift_score "
            "cost_preference context_risk certified_signal safe_witness danger_witness scope_validity rail_risk "
            "schema_guard_risk tool_guard_risk critique_risk judge_risk verifier_risk debate_risk review_conflict "
            "expert_risk source_model_risk safety_critic_risk random_key feedback_released feedback_reliability"
        ).split()
    }
    for point in load_operating_points():
        if point.oracle:
            continue
        actions, scores, thresholds = decide_visible(point, fields)
        assert actions.shape == scores.shape == thresholds.shape == (2,)
        assert set(actions.tolist()) <= {0, 1, 2}
    source = inspect.getsource(decide_visible)
    assert not any(token in source for token in ("hidden_outcomes", "catastrophic", "correct_action", "feedback_target"))
