from mavs10d.baselines.conformal import AdaptiveConformalBaseline, ConformalAbstentionBaseline
from mavs10d.baselines.reject_option import RejectOptionBaseline
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import StepResult, trace_supports_mavs_fields

from tests.unit.baseline_test_utils import make_candidate, make_observation


def test_static_conformal_refuses_update() -> None:
    baseline = ConformalAbstentionBaseline(
        MethodConfig(
            id="conformal_static",
            type="conformal_static",
            params={"conformal_path": "configs/baselines/conformal.yaml"},
        )
    )
    obs = make_observation()
    candidate = make_candidate(risk_proxy=0.90)
    threshold_before = baseline.threshold

    decision = baseline.decide(obs, candidate)
    baseline.update(obs, candidate, decision, _step_result())

    assert decision.decision == "reject"
    assert baseline.threshold == threshold_before
    assert decision.trace["diagnostic_values"]["baseline_details"]["refuses_update"] is True
    assert trace_supports_mavs_fields(decision.trace)


def test_adaptive_conformal_updates_threshold_window() -> None:
    baseline = AdaptiveConformalBaseline(
        MethodConfig(
            id="conformal_adaptive",
            type="conformal_adaptive",
            params={"conformal_path": "configs/baselines/conformal.yaml"},
        )
    )
    obs = make_observation()
    candidate = make_candidate(risk_proxy=0.90)

    decision = baseline.decide(obs, candidate)
    baseline.update(obs, candidate, decision, _step_result())

    assert baseline.update_count == 1
    assert len(baseline.scores) <= baseline.window
    assert "threshold_lag_signal" in decision.trace["diagnostic_values"]["baseline_details"]
    assert trace_supports_mavs_fields(decision.trace)


def test_adaptive_conformal_reset_restores_calibration_window() -> None:
    baseline = AdaptiveConformalBaseline(
        MethodConfig(
            id="conformal_adaptive",
            type="conformal_adaptive",
            params={"conformal_path": "configs/baselines/conformal.yaml"},
        )
    )
    obs = make_observation()
    candidate = make_candidate(risk_proxy=0.90)
    decision = baseline.decide(obs, candidate)
    baseline.update(obs, candidate, decision, _step_result())

    baseline.reset(42)

    assert baseline.update_count == 0
    assert list(baseline.scores) == baseline.calibration_scores


def test_reject_option_reports_threshold_sweep_and_updates_when_adaptive() -> None:
    baseline = RejectOptionBaseline(
        MethodConfig(
            id="reject_option",
            type="reject_option",
            params={
                "reject_threshold": 0.65,
                "escalate_threshold": 0.45,
                "adaptive": True,
                "adaptation_rate": 0.05,
                "threshold_sweep": [0.30, 0.50, 0.70],
            },
        )
    )
    obs = make_observation()
    candidate = make_candidate(risk_proxy=0.80)

    decision = baseline.decide(obs, candidate)
    baseline.update(obs, candidate, decision, _step_result(unsafe_accepted=True))

    assert decision.decision == "reject"
    assert "threshold_sweep" in decision.trace["diagnostic_values"]["baseline_details"]
    assert baseline.reject_threshold < 0.65
    assert trace_supports_mavs_fields(decision.trace)


def test_reject_option_reset_restores_adaptive_thresholds() -> None:
    baseline = RejectOptionBaseline(
        MethodConfig(
            id="reject_option",
            type="reject_option",
            params={
                "reject_threshold": 0.65,
                "escalate_threshold": 0.45,
                "adaptive": True,
                "adaptation_rate": 0.05,
            },
        )
    )
    obs = make_observation()
    candidate = make_candidate(risk_proxy=0.80)
    decision = baseline.decide(obs, candidate)
    baseline.update(obs, candidate, decision, _step_result(unsafe_accepted=True))

    baseline.reset(42)

    assert baseline.reject_threshold == 0.65
    assert baseline.escalate_threshold == 0.45


def _step_result(unsafe_accepted: bool = False) -> StepResult:
    return StepResult(
        next_observation=make_observation(t=1),
        reward=-1.0 if unsafe_accepted else 1.0,
        unsafe_accepted=unsafe_accepted,
        false_rejected=False,
        done=False,
        info={"active_phase": "unit_test"},
    )
