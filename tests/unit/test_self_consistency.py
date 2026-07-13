from mavs10d.baselines.self_consistency import SelfConsistencyBaseline
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import trace_supports_mavs_fields

from tests.unit.baseline_test_utils import make_candidate, make_observation


def test_self_consistency_accepts_high_margin_safe_case() -> None:
    baseline = SelfConsistencyBaseline(
        MethodConfig(
            id="self_consistency",
            type="self_consistency",
            params={"k": 7, "min_margin": 0.25, "accept_threshold": 0.50, "perturbation": 0.0},
        )
    )
    baseline.reset(11)

    decision = baseline.decide(make_observation(), make_candidate(risk_proxy=0.10))

    assert decision.decision == "accept"
    assert decision.trace["diagnostic_values"]["baseline_details"]["margin"] == 1.0
    assert trace_supports_mavs_fields(decision.trace)


def test_self_consistency_escalates_low_margin_case() -> None:
    baseline = SelfConsistencyBaseline(
        MethodConfig(
            id="self_consistency",
            type="self_consistency",
            params={"k": 7, "min_margin": 1.1, "accept_threshold": 0.50, "perturbation": 0.10},
        )
    )
    baseline.reset(11)

    decision = baseline.decide(make_observation(), make_candidate(risk_proxy=0.50))

    assert decision.decision == "escalate"
    assert "self_consistency_low_margin" in decision.triggered_checks

