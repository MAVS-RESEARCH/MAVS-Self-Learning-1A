from __future__ import annotations

from dataclasses import dataclass

from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class SWEBenchAdapterSpec:
    source_name: str
    category_labels: list[str]
    status: str
    resource_note: str


def build_swebench_adapter_spec() -> SWEBenchAdapterSpec:
    # console.log: phase4.external.swebench.build_spec
    console_log("phase4.external.swebench.build_spec")
    return SWEBenchAdapterSpec(
        source_name="SWE-bench",
        category_labels=["software_engineering", "patch_generation", "repository_reasoning"],
        status="metadata_scaffolding_only",
        resource_note="Docker, repository checkout, and benchmark harness resources are required before execution.",
    )


def swebench_to_mavs_label(instance: dict[str, object]) -> dict[str, str]:
    # console.log: phase4.external.swebench.map_instance
    console_log("phase4.external.swebench.map_instance", keys=sorted(instance))
    return {
        "mavs_task": "software_engineering_governance",
        "risk_family": "patch_correctness_or_tool_use",
        "evaluation_path": "resource_heavy_unavailable_until_harness_configured",
    }

