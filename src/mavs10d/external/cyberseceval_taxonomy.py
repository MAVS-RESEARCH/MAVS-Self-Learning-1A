from __future__ import annotations

from mavs10d.core.trace_logging import console_log


CYBERSECEVAL_CATEGORY_MAP: dict[str, dict[str, str]] = {
    "phishing": {"mavs_task": "tool_use_security", "risk_family": "credential_theft"},
    "credential_theft": {"mavs_task": "tool_use_security", "risk_family": "credential_theft"},
    "malware": {"mavs_task": "cyber_triage", "risk_family": "malware_assistance"},
    "vulnerability_exploitation": {"mavs_task": "cyber_triage", "risk_family": "exploit_guidance"},
    "secure_code": {"mavs_task": "cyber_triage", "risk_family": "defensive_security"},
    "prompt_injection": {"mavs_task": "tool_use_security", "risk_family": "prompt_injection"},
}


def map_cyberseceval_category(category: str) -> dict[str, str]:
    # console.log: phase4.external.cyberseceval.map_category
    console_log("phase4.external.cyberseceval.map_category", category=category)
    key = category.strip().lower().replace(" ", "_")
    mapping = CYBERSECEVAL_CATEGORY_MAP.get(
        key,
        {"mavs_task": "cyber_triage", "risk_family": "unmapped_cyber_category"},
    )
    return {"source_category": key, **mapping}


def cyberseceval_task_families() -> list[str]:
    # console.log: phase4.external.cyberseceval.task_families
    console_log("phase4.external.cyberseceval.task_families")
    return sorted({item["mavs_task"] for item in CYBERSECEVAL_CATEGORY_MAP.values()})

