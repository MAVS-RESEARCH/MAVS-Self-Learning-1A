from mavs10d.baselines.confidence_gate import ConfidenceGateBaseline
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import trace_supports_mavs_fields

from tests.unit.baseline_test_utils import make_candidate, make_observation


def test_confidence_gate_rejects_low_confidence() -> None:
    baseline = ConfidenceGateBaseline(
        MethodConfig(id="confidence", type="confidence_gate", params={"reject_below": 0.35, "escalate_below": 0.55})
    )
    decision = baseline.decide(make_observation(), make_candidate(confidence=0.20))

    assert decision.decision == "reject"
    assert "confidence_reject_gate" in decision.triggered_checks
    assert trace_supports_mavs_fields(decision.trace)


def test_confidence_gate_escalates_mid_confidence() -> None:
    baseline = ConfidenceGateBaseline(
        MethodConfig(id="confidence", type="confidence_gate", params={"reject_below": 0.35, "escalate_below": 0.55})
    )
    decision = baseline.decide(make_observation(), make_candidate(confidence=0.45))

    assert decision.decision == "escalate"
    assert "confidence_escalation_gate" in decision.triggered_checks

