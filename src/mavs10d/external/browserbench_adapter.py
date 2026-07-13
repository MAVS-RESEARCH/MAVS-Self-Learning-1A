from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, urlopen

from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class BrowserBenchAvailability:
    requested_repository: str
    available: bool
    selected_framing: str
    fallback_repository: str | None
    reason: str


def verify_browserbench_repository(
    repository_url: str = "https://github.com/web-arena-x/BrowserBench",
    timeout_seconds: float = 2.0,
) -> BrowserBenchAvailability:
    # console.log: phase4.external.browserbench.verify.start
    console_log("phase4.external.browserbench.verify.start", repository_url=repository_url)
    available = False
    reason = "not_checked"
    try:
        request = Request(repository_url, method="HEAD")
        with urlopen(request, timeout=timeout_seconds) as response:
            available = 200 <= int(response.status) < 400
            reason = f"http_status_{response.status}"
    except Exception as exc:  # pragma: no cover - network outcome is environment-dependent
        reason = f"unavailable:{type(exc).__name__}"
    selected = "BrowserBench" if available else "WebArena framing fallback"
    fallback = None if available else "https://github.com/web-arena-x/webarena"
    result = BrowserBenchAvailability(
        requested_repository=repository_url,
        available=available,
        selected_framing=selected,
        fallback_repository=fallback,
        reason=reason,
    )
    # console.log: phase4.external.browserbench.verify.complete
    console_log(
        "phase4.external.browserbench.verify.complete",
        available=result.available,
        selected_framing=result.selected_framing,
        reason=result.reason,
    )
    return result


def browserbench_to_mavs_label(task_category: str) -> dict[str, str]:
    # console.log: phase4.external.browserbench.map_category
    console_log("phase4.external.browserbench.map_category", task_category=task_category)
    return {
        "source_category": task_category,
        "mavs_task": "browser_interaction_governance",
        "risk_family": "tool_use_and_web_state",
    }

