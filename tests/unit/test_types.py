from mavs10d.core.types import (
    CandidateAction,
    EpisodeTrace,
    GovernanceDecision,
    Observation,
    StepResult,
    mavs_trace_template,
    trace_supports_mavs_fields,
)


def test_dataclass_round_trip_serialization() -> None:
    obs = Observation(
        episode_id="ep",
        t=0,
        visible_state={"x": 1},
        prompt="prompt",
        risk_context={"risk": "smoke"},
    )
    candidate = CandidateAction(
        action_type="respond",
        content="content",
        confidence=0.8,
        specialist_outputs={"a": {"score": 0.7}},
        provenance={"source": "test"},
    )
    trace = mavs_trace_template()
    trace.update({"specialist_id": ["a"], "confidence": 0.8})
    decision = GovernanceDecision(
        decision="accept",
        risk_score=0.2,
        severity=0.2,
        rationale="test",
        triggered_checks=[],
        threshold=0.5,
        trace=trace,
    )
    result = StepResult(
        next_observation=obs,
        reward=1.0,
        unsafe_accepted=False,
        false_rejected=False,
        done=True,
        info={"done": True},
    )
    episode_trace = EpisodeTrace(
        run_id="run",
        config_hash="hash",
        git_commit="commit",
        environment_id="env",
        method_id="method",
        seed=1,
        episode_id="ep",
        step_id=0,
        observation=obs,
        candidate=candidate,
        decision=decision,
        step_result=result,
        hidden_label_hash="hidden",
        trace_complete=True,
        created_at_utc="2026-07-04T00:00:00+00:00",
        metadata={"phase": "phase1"},
    )

    restored = EpisodeTrace.from_dict(episode_trace.to_dict())

    assert restored == episode_trace
    assert trace_supports_mavs_fields(restored.decision.trace)

