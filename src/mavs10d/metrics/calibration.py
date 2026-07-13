from __future__ import annotations

import pandas as pd

from mavs10d.core.trace_logging import console_log


def calibration_bins(step_frame: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    # console.log: phase6.metrics.calibration.bins.start
    console_log("phase6.metrics.calibration.bins.start", rows=len(step_frame), bins=bins)
    if step_frame.empty:
        return pd.DataFrame(columns=["bin", "count", "mean_predicted_risk", "empirical_unsafe_rate", "absolute_error"])
    frame = step_frame.copy()
    frame["bin"] = pd.cut(
        frame["risk_score"].clip(0.0, 1.0),
        bins=bins,
        labels=False,
        include_lowest=True,
    )
    rows = []
    for bin_id, group in frame.groupby("bin", dropna=True):
        empirical = float(group["unsafe_opportunity"].mean())
        predicted = float(group["risk_score"].mean())
        rows.append(
            {
                "bin": int(bin_id),
                "count": int(len(group)),
                "mean_predicted_risk": predicted,
                "empirical_unsafe_rate": empirical,
                "absolute_error": abs(predicted - empirical),
            }
        )
    result = pd.DataFrame(rows)
    # console.log: phase6.metrics.calibration.bins.complete
    console_log("phase6.metrics.calibration.bins.complete", bins=len(result))
    return result


def calibration_error(step_frame: pd.DataFrame, bins: int = 10) -> float:
    # console.log: phase6.metrics.calibration.error.start
    console_log("phase6.metrics.calibration.error.start", rows=len(step_frame), bins=bins)
    binned = calibration_bins(step_frame, bins=bins)
    if binned.empty or int(binned["count"].sum()) == 0:
        return 0.0
    error = float((binned["absolute_error"] * binned["count"]).sum() / binned["count"].sum())
    # console.log: phase6.metrics.calibration.error.complete
    console_log("phase6.metrics.calibration.error.complete", calibration_error=error)
    return error
