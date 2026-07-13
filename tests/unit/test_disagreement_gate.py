from mavs10d.baselines.disagreement_gate import DisagreementGateBaseline
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import trace_supports_mavs_fields

from tests.unit.baseline_test_utils import make_candidate, make_observation


def test_disagreement_gate_escalates_high_spread() -> None:
    baseline = DisagreementGateBaseline(
        MethodConfig(
            id="disagreement",
            type="disagreement_gate",
            params={"reject_threshold": 0.70, "escalate_threshold": 0.20},
        )
    )
    candidate = make_candidate(scores=[0.05, 0.95, 0.50], risk_proxy=0.20)

    decision = baseline.decide(make_observation(), candidate)

    assert decision.decision in {"escalate", "reject"}
    assert decision.triggered_checks
    assert trace_supports_mavs_fields(decision.trace)


def test_disagreement_gate_accepts_consistent_scores() -> None:
    baseline = DisagreementGateBaseline(
        MethodConfig(
            id="disagreement",
            type="disagreement_gate",
            params={"reject_threshold": 0.70, "escalate_threshold": 0.20},
        )
    )
    candidate = make_candidate(scores=[0.80, 0.82, 0.81], risk_proxy=0.20)

    decision = baseline.decide(make_observation(), candidate)

    assert decision.decision == "accept"

