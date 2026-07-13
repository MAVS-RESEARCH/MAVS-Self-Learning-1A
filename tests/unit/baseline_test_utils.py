from mavs10d.core.types import CandidateAction, Observation


def make_observation(prompt: str = "benign prompt", t: int = 0) -> Observation:
    return Observation(
        episode_id="baseline_test_episode",
        t=t,
        visible_state={"test": True},
        prompt=prompt,
        risk_context={"active_phase": "unit_test", "corruption_level": 0.0},
        corruption_hint={"active_phase": "unit_test", "corruption_level": 0.0},
    )


def make_candidate(
    *,
    action_type: str = "text_response",
    content: str = "candidate response",
    confidence: float = 0.80,
    risk_proxy: float = 0.20,
    scores: list[float] | None = None,
) -> CandidateAction:
    score_values = scores if scores is not None else [0.80, 0.75, 0.78]
    return CandidateAction(
        action_type=action_type,
        content=content,
        confidence=confidence,
        specialist_outputs={
            f"specialist_{index}": {"score": score, "confidence": confidence}
            for index, score in enumerate(score_values)
        },
        provenance={
            "risk_proxy": risk_proxy,
            "hidden_risk_proxy": risk_proxy,
            "evidence_visible": True,
            "generator": "unit_test",
        },
    )

