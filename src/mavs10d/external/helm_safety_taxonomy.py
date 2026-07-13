from __future__ import annotations

from mavs10d.core.trace_logging import console_log


HELM_SAFETY_CATEGORY_MAP: dict[str, dict[str, str]] = {
    "violence": {"mavs_label": "physical_harm", "report_section": "safety.violence"},
    "fraud": {"mavs_label": "deception_or_fraud", "report_section": "safety.fraud"},
    "discrimination": {"mavs_label": "discrimination", "report_section": "safety.discrimination"},
    "sexual_content": {"mavs_label": "sexual_content", "report_section": "safety.sexual_content"},
    "harassment": {"mavs_label": "harassment", "report_section": "safety.harassment"},
    "deception": {"mavs_label": "deception_or_fraud", "report_section": "safety.deception"},
}


def map_helm_safety_category(category: str) -> dict[str, str]:
    # console.log: phase4.external.helm.map_category
    console_log("phase4.external.helm.map_category", category=category)
    key = category.strip().lower().replace(" ", "_")
    mapping = HELM_SAFETY_CATEGORY_MAP.get(
        key,
        {"mavs_label": "unknown_safety_category", "report_section": "safety.unmapped"},
    )
    return {"source_category": key, **mapping}


def helm_safety_report_sections() -> list[str]:
    # console.log: phase4.external.helm.report_sections
    console_log("phase4.external.helm.report_sections")
    return sorted({item["report_section"] for item in HELM_SAFETY_CATEGORY_MAP.values()})

