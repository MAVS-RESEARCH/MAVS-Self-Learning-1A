from mavs10d.external.cyberseceval_taxonomy import map_cyberseceval_category
from mavs10d.external.gaia_adapter import build_gaia_adapter_spec, gaia_to_mavs_label
from mavs10d.external.helm_safety_taxonomy import map_helm_safety_category
from mavs10d.external.red_teaming_methodology import (
    map_red_team_attack_family,
    red_team_methodology_protocol,
)
from mavs10d.external.swebench_adapter import build_swebench_adapter_spec


def test_external_adapters_preserve_category_mappings_without_training_data() -> None:
    assert map_helm_safety_category("violence")["mavs_label"] == "physical_harm"
    assert map_cyberseceval_category("credential theft")["mavs_task"] == "tool_use_security"
    assert build_swebench_adapter_spec().status == "metadata_scaffolding_only"
    assert build_gaia_adapter_spec().data_policy.startswith("category and schema mapping only")
    assert gaia_to_mavs_label("multi step assistant")["risk_family"] == "multi_step_assistant"
    assert map_red_team_attack_family("prompt injection")["mavs_task"] == "tool_use_security"
    assert red_team_methodology_protocol()["status"] == "methodology_scaffolding_only"
