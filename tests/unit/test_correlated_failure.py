import random

from mavs10d.core.config import EnvironmentConfig
from mavs10d.corruption.transforms import apply_transforms
from mavs10d.envs.correlated_collapse_env import CorrelatedCollapseEnv


def test_correlated_transforms_inject_all_shared_failure_channels() -> None:
    scenario = {
        "t": 10,
        "prompt": "base",
        "candidate_content": "candidate",
        "action_type": "text",
        "unsafe": False,
        "risk_score": 0.10,
        "visible_state": {},
        "transform_history": [],
    }
    transforms = [
        {"type": "shared_wrong_premise"},
        {"type": "shared_retrieval_context"},
        {"type": "shared_provenance_concentration", "level": 0.95},
        {"type": "shared_prompt_injection"},
        {"type": "shared_evidence_mask"},
        {"type": "shared_confidence_bias", "strength": 0.15},
        {"type": "shared_feature_corruption"},
    ]

    transformed = apply_transforms(scenario, transforms, random.Random(1))

    for key in [
        "shared_wrong_premise",
        "shared_retrieval_context",
        "shared_provenance_concentration",
        "shared_prompt_injection",
        "shared_evidence_mask",
        "shared_confidence_bias",
        "shared_feature_corruption",
    ]:
        assert transformed[key] is True
    assert transformed["unsafe"] is True
    assert transformed["evidence_visible"] is False
    assert transformed["provenance_concentration"] >= 0.95


def test_correlated_environment_marks_comparison_design() -> None:
    env = CorrelatedCollapseEnv(
        EnvironmentConfig(
            id="correlated_test",
            type="correlated_representation_collapse",
            params={"episode_steps": 4},
        )
    )
    obs = env.reset(5)

    assert obs.visible_state["comparison_design"] == "independent_vs_shared_representation_failure"
    assert obs.visible_state["failure_mode"] in {
        "independent_specialist_failure",
        "shared_representation",
    }
