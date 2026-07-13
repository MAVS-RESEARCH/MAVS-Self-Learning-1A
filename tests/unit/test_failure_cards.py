import json
from pathlib import Path

from mavs10d.reports.failure_cards import failure_card_markdown, write_failure_cards


def test_failure_card_contains_required_phase6_fields(tmp_path: Path) -> None:
    record = _failure_record()

    card = failure_card_markdown(record, 1)

    assert "Episode id" in card
    assert "Corruption phase" in card
    assert "Expected decision" in card
    assert "Actual decision" in card
    assert "MAVS trace" in card
    assert "Proposed fix" in card

    raw = tmp_path / "raw.jsonl"
    raw.write_text(json.dumps(record) + "\n", encoding="utf-8")
    paths = write_failure_cards(raw, tmp_path / "cards")
    assert len(paths) == 1
    assert paths[0].read_text(encoding="utf-8").startswith("# Failure Card")


def _failure_record() -> dict[str, object]:
    return {
        "episode_id": "ep",
        "step_id": 1,
        "environment_id": "env",
        "method_id": "mavs",
        "decision": {
            "decision": "accept",
            "risk_score": 0.2,
            "threshold": 0.5,
            "trace": {"missing_evidence": 0.0},
        },
        "step_result": {
            "unsafe_accepted": True,
            "info": {
                "expected_decision": "reject",
                "active_phase": "correlated_failure",
                "unsafe_reason": "unsafe_tool_call",
            },
        },
        "candidate": {"specialist_outputs": {"a": {"score": 0.7}}},
    }
