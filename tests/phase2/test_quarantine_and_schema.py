from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from mavs10d.governance.feedback_quarantine import FeedbackQuarantine


ROOT = Path(__file__).resolve().parents[2]


def test_feedback_quarantine_distinguishes_all_dispositions() -> None:
    gate = FeedbackQuarantine(0.75)
    base = {"opportunity_id": "x", "release_step": 4, "reliability": 0.90, "poisoned": False}
    assert gate.classify(base, 3).disposition == "unreleased"
    assert gate.classify(base, 4).disposition == "accepted"
    assert gate.classify({**base, "reliability": 0.60}, 4).disposition == "quarantined"
    assert gate.classify({**base, "poisoned": True}, 4).disposition == "quarantined"
    assert gate.classify({**base, "release_step": None}, 4).disposition == "censored"


def test_phase2_schemas_are_valid() -> None:
    for name in ("phase2_trace.schema.json", "phase2_failure_card.schema.json"):
        Draft202012Validator.check_schema(json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8")))


def test_phase2_participant_sources_do_not_name_hidden_payloads() -> None:
    sources = [
        ROOT / "src/mavs10d/governance/ds_cf.py",
        ROOT / "src/mavs10d/governance/phase2_diagnostics.py",
        ROOT / "src/mavs10d/baselines/phase2_methods.py",
    ]
    forbidden = ("hidden_outcomes", "hidden_mechanism_hash", "catastrophic_if_accepted", "feedback_poisoned")
    assert all(token not in path.read_text(encoding="utf-8") for path in sources for token in forbidden)
