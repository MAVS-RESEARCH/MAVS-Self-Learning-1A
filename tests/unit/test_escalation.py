from mavs10d.governance.escalation import (
    HardVetoResult,
    MitigationResult,
    final_decision_functional,
)


def test_hard_veto_overrides_bounded_mitigation() -> None:
    result = final_decision_functional(
        consensus=0.90,
        severity=0.40,
        threshold=0.60,
        mitigation=MitigationResult(
            strength=0.10,
            organs=["retrieval_recheck"],
            rationale="bounded mitigation available",
        ),
        hard_veto=HardVetoResult(active=True, reasons=["unsafe_tool_call"]),
    )

    assert result.decision == "reject"
    assert result.fallback_action == "reject_without_mitigation"
    assert "hard_veto:unsafe_tool_call" in result.triggered_checks

