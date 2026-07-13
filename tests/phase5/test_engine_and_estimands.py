from __future__ import annotations

import inspect
import math

import numpy as np

from mavs10d.ablations.engine import decide_visible
from mavs10d.ablations.registry import AblationState
from mavs10d.metrics.transfer import (
    catastrophic_governance_interference, constrained_objective, forward_transfer,
    generation_improvement_slope, library_efficiency, time_to_diagnosis, time_to_recovery,
)
from mavs10d.transfer.leakage import forbidden_source_tokens


def test_engine_uses_only_visible_features_and_every_action_is_defined() -> None:
    fields = {name: np.asarray([0.2, 0.8, 0.5]) for name in (
        "risk_proxy certified_signal danger_witness provenance_quality safe_witness meta_novelty coverage_gap "
        "masking_signal counterfactual_stability adversarial_pressure correlation_signal feedback_released "
        "feedback_reliability policy_conflict abstract_similarity raw_similarity shift_score random_key "
        "uncertainty evidence_available scope_validity shared_representation step reset_match"
    ).split()}
    for state in (AblationState(), AblationState(escalation=False), AblationState(persistence="raw_memory")):
        actions, scores, thresholds, diagnostics = decide_visible(state, "cumulative", 2, fields)
        assert actions.shape == scores.shape == thresholds.shape == (3,)
        assert set(actions.tolist()) <= {0, 1, 2}
        assert set(diagnostics) == {"unknown", "inherited_eligible", "inherited_used", "proposal", "certified_update", "promoted_update", "scope_influence"}
    assert forbidden_source_tokens(inspect.getsource(decide_visible)) == ()


def test_transfer_estimands_define_edge_cases_without_imputation() -> None:
    assert constrained_objective(1.0, 0.0, 0.0, 0.0, 0.0) == 1.0
    assert math.isclose(forward_transfer(0.4, 0.1), 0.3)
    assert time_to_recovery([0.0, 0.0, 1.0, 1.0, 1.0], 0.6, 3) == 4.0
    assert math.isnan(time_to_diagnosis([False, False]))
    assert time_to_diagnosis([False, True]) == 2.0
    assert catastrophic_governance_interference(0, 10) == 0.0
    assert library_efficiency(0.2, 1048576) == 0.2
    assert generation_improvement_slope([0.1, 0.2, 0.3]) > 0
