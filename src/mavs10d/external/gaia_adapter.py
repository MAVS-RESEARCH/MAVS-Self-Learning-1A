from __future__ import annotations

from dataclasses import dataclass

from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class GAIAAdapterSpec:
    source_name: str
    category_labels: list[str]
    status: str
    data_policy: str


def build_gaia_adapter_spec() -> GAIAAdapterSpec:
    # console.log: phase4.external.gaia.build_spec
    console_log("phase4.external.gaia.build_spec")
    return GAIAAdapterSpec(
        source_name="GAIA",
        category_labels=["reasoning", "tool_use", "web_browsing", "multi_step_assistant"],
        status="metadata_scaffolding_only",
        data_policy="category and schema mapping only; no official validation or test data ingestion",
    )


def gaia_to_mavs_label(category: str) -> dict[str, str]:
    # console.log: phase4.external.gaia.map_category
    console_log("phase4.external.gaia.map_category", category=category)
    normalized = category.strip().lower().replace(" ", "_")
    return {
        "source_category": normalized,
        "mavs_task": "general_assistant_governance",
        "risk_family": normalized if normalized else "unmapped_gaia_category",
    }

