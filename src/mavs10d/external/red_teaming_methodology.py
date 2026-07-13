from __future__ import annotations

from mavs10d.core.trace_logging import console_log


RED_TEAM_ATTACK_FAMILY_MAP: dict[str, dict[str, str]] = {
    "jailbreak": {
        "mavs_task": "text_safety_stream",
        "risk_family": "policy_bypass",
        "methodology_note": "adversarial prompt attempts to bypass policy constraints",
    },
    "prompt_injection": {
        "mavs_task": "tool_use_security",
        "risk_family": "instruction_hijacking",
        "methodology_note": "attacker-supplied instructions compete with trusted instructions",
    },
    "deception": {
        "mavs_task": "multi_agent_operations",
        "risk_family": "deceptive_alignment_or_false_premise",
        "methodology_note": "model behavior is probed for misleading or strategically false claims",
    },
    "data_exfiltration": {
        "mavs_task": "tool_use_security",
        "risk_family": "secret_or_credential_exposure",
        "methodology_note": "adversarial task attempts to extract protected data",
    },
    "correlated_failure": {
        "mavs_task": "correlated_representation_collapse",
        "risk_family": "shared_context_failure",
        "methodology_note": "multiple specialists are stressed by the same flawed representation",
    },
}


def map_red_team_attack_family(attack_family: str) -> dict[str, str]:
    # console.log: phase4.external.red_team.map_attack_family
    console_log("phase4.external.red_team.map_attack_family", attack_family=attack_family)
    key = attack_family.strip().lower().replace(" ", "_").replace("-", "_")
    mapping = RED_TEAM_ATTACK_FAMILY_MAP.get(
        key,
        {
            "mavs_task": "general_dynamic_governance",
            "risk_family": "unmapped_red_team_attack",
            "methodology_note": "category mapping only; no red-team transcript or official test data ingested",
        },
    )
    return {"source_attack_family": key, **mapping}


def red_team_methodology_protocol() -> dict[str, object]:
    # console.log: phase4.external.red_team.protocol
    console_log("phase4.external.red_team.protocol")
    return {
        "status": "methodology_scaffolding_only",
        "data_policy": "category and protocol mapping only; no official red-team transcripts ingested",
        "protocol_steps": [
            "define attack family",
            "separate development prompts from final prompts",
            "run adversarial attempts under fixed seeds",
            "record refusal, escalation, unsafe acceptance, and trace completeness",
            "report category-level outcomes without training on evaluation data",
        ],
        "supported_attack_families": sorted(RED_TEAM_ATTACK_FAMILY_MAP),
    }

