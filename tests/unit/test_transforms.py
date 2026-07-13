import random

from mavs10d.corruption.transforms import apply_transforms


BASE_SCENARIO = {
    "prompt": "base prompt",
    "candidate_content": "candidate",
    "action_type": "text_response",
    "unsafe": False,
    "unsafe_reason": None,
    "risk_score": 0.10,
    "risk_domain": "test",
    "visible_state": {},
    "t": 0,
}


def test_transforms_are_deterministic_for_identical_seed() -> None:
    transforms = [
        {"type": "ambiguity_injection", "p": 1.0},
        {"type": "confidence_miscalibration", "strength": 0.10},
        {"type": "prompt_injection", "p": 1.0},
    ]

    first = apply_transforms(BASE_SCENARIO, transforms, random.Random(10))
    second = apply_transforms(BASE_SCENARIO, transforms, random.Random(10))

    assert first == second


def test_transforms_change_with_different_seed() -> None:
    transforms = [{"type": "ambiguity_injection", "p": 1.0}]

    first = apply_transforms(BASE_SCENARIO, transforms, random.Random(10))
    second = apply_transforms(BASE_SCENARIO, transforms, random.Random(11))

    assert first != second


def test_all_phase2_transform_types_apply_expected_fields() -> None:
    transforms = [
        {"type": "ambiguity_injection", "p": 1.0},
        {"type": "confidence_miscalibration", "strength": 0.10},
        {"type": "prompt_injection", "p": 1.0},
        {"type": "evidence_masking", "p": 1.0},
        {"type": "label_drift", "p": 1.0, "unsafe": True},
        {"type": "unsafe_tool_call_mutation", "p": 1.0},
        {"type": "hidden_instruction_insertion", "p": 1.0},
        {"type": "exfiltration_bait", "p": 1.0},
        {"type": "alert_severity_drift", "strength": 0.20},
        {"type": "residual_drift", "strength": 0.10},
        {"type": "shared_wrong_premise", "p": 1.0},
    ]

    result = apply_transforms(BASE_SCENARIO, transforms, random.Random(1))

    assert result["ambiguity"] is True
    assert result["miscalibrated_confidence"] is True
    assert result["prompt_injection"] is True
    assert result["evidence_visible"] is False
    assert result["label_drift"] is True
    assert result["dangerous_tool_call"] is True
    assert result["hidden_instruction"] is True
    assert result["protected_variable_leak"] is True
    assert result["alert_severity_drift"] is True
    assert result["residual_drift"] is True
    assert result["shared_wrong_premise"] is True
    assert result["unsafe"] is True
    assert len(result["transform_history"]) == len(transforms)

