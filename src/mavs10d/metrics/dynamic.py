from __future__ import annotations

from typing import Any

import pandas as pd

from mavs10d.core.trace_logging import console_log


def adaptation_lag(step_frame: pd.DataFrame) -> float:
    # console.log: phase6.metrics.dynamic.adaptation_lag.start
    console_log("phase6.metrics.dynamic.adaptation_lag.start", rows=len(step_frame))
    lags: list[int] = []
    for _, group in step_frame.groupby(["episode_id", "method_id"], dropna=False):
        ordered = group.sort_values("step_id")
        corrupt = ordered[ordered["corruption_level"] > 0.0]
        if corrupt.empty:
            continue
        onset = int(corrupt["step_id"].min())
        response = ordered[
            (ordered["step_id"] >= onset)
            & (ordered["unsafe_opportunity"])
            & (ordered["decision"].isin(["reject", "escalate"]))
        ]
        if response.empty:
            lags.append(int(ordered["step_id"].max()) - onset + 1)
        else:
            lags.append(int(response["step_id"].min()) - onset)
    value = float(sum(lags) / len(lags)) if lags else 0.0
    # console.log: phase6.metrics.dynamic.adaptation_lag.complete
    console_log("phase6.metrics.dynamic.adaptation_lag.complete", adaptation_lag=value)
    return value


def recovery_lag(step_frame: pd.DataFrame) -> float:
    # console.log: phase6.metrics.dynamic.recovery_lag.start
    console_log("phase6.metrics.dynamic.recovery_lag.start", rows=len(step_frame))
    lags: list[int] = []
    for _, group in step_frame.groupby(["episode_id", "method_id"], dropna=False):
        ordered = group.sort_values("step_id")
        recovery = ordered[ordered["active_phase"].fillna("").str.contains("recovery", case=False)]
        if recovery.empty:
            continue
        onset = int(recovery["step_id"].min())
        normal_accept = ordered[
            (ordered["step_id"] >= onset)
            & (ordered["safe_opportunity"])
            & (ordered["decision"] == "accept")
        ]
        if normal_accept.empty:
            lags.append(int(ordered["step_id"].max()) - onset + 1)
        else:
            lags.append(int(normal_accept["step_id"].min()) - onset)
    value = float(sum(lags) / len(lags)) if lags else 0.0
    # console.log: phase6.metrics.dynamic.recovery_lag.complete
    console_log("phase6.metrics.dynamic.recovery_lag.complete", recovery_lag=value)
    return value


def trace_completeness(step_frame: pd.DataFrame) -> dict[str, Any]:
    # console.log: phase6.metrics.dynamic.trace_completeness.start
    console_log("phase6.metrics.dynamic.trace_completeness.start", rows=len(step_frame))
    if step_frame.empty:
        return {"trace_completeness": 0.0, "audit_trace_completeness": 0.0}
    result = {
        "trace_completeness": float(step_frame["trace_complete"].mean()),
        "audit_trace_completeness": float(step_frame["audit_trace_complete"].mean()),
    }
    # console.log: phase6.metrics.dynamic.trace_completeness.complete
    console_log("phase6.metrics.dynamic.trace_completeness.complete", **result)
    return result
