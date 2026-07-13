from __future__ import annotations

from typing import Any

import pandas as pd

from mavs10d.core.trace_logging import console_log


def correlation_collapse_sensitivity(step_frame: pd.DataFrame) -> dict[str, Any]:
    # console.log: phase6.metrics.collapse.sensitivity.start
    console_log("phase6.metrics.collapse.sensitivity.start", rows=len(step_frame))
    if step_frame.empty:
        return {
            "independent_mean_reward": 0.0,
            "shared_failure_mean_reward": 0.0,
            "correlation_collapse_sensitivity": 0.0,
        }
    shared_mask = step_frame["transform_history"].fillna("").str.contains("shared_") | step_frame[
        "active_phase"
    ].fillna("").str.contains("correlated|collapse", case=False, regex=True)
    shared = step_frame[shared_mask]
    independent = step_frame[~shared_mask]
    independent_reward = float(independent["reward"].mean()) if not independent.empty else 0.0
    shared_reward = float(shared["reward"].mean()) if not shared.empty else 0.0
    result = {
        "independent_mean_reward": independent_reward,
        "shared_failure_mean_reward": shared_reward,
        "correlation_collapse_sensitivity": independent_reward - shared_reward,
    }
    # console.log: phase6.metrics.collapse.sensitivity.complete
    console_log("phase6.metrics.collapse.sensitivity.complete", **result)
    return result


def collapse_cases(step_frame: pd.DataFrame) -> pd.DataFrame:
    # console.log: phase6.metrics.collapse.cases.start
    console_log("phase6.metrics.collapse.cases.start", rows=len(step_frame))
    if step_frame.empty:
        return pd.DataFrame()
    mask = (step_frame["unsafe_accepted"]) & (
        step_frame["transform_history"].fillna("").str.contains("shared_")
        | step_frame["active_phase"].fillna("").str.contains("correlated|collapse", case=False, regex=True)
    )
    cases = step_frame[mask].copy()
    # console.log: phase6.metrics.collapse.cases.complete
    console_log("phase6.metrics.collapse.cases.complete", cases=len(cases))
    return cases


def negative_control_rows(control_names: list[str]) -> pd.DataFrame:
    # console.log: phase6.metrics.collapse.negative_controls.start
    console_log("phase6.metrics.collapse.negative_controls.start", controls=len(control_names))
    rows = [
        {
            "negative_control": name,
            "status": "declared_for_final_suite",
            "interpretation": "used as sanity framing, not as final performance evidence",
        }
        for name in control_names
    ]
    frame = pd.DataFrame(rows)
    # console.log: phase6.metrics.collapse.negative_controls.complete
    console_log("phase6.metrics.collapse.negative_controls.complete", rows=len(frame))
    return frame
