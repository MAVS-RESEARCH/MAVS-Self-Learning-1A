from __future__ import annotations

from typing import Any

import pandas as pd

from mavs10d.core.trace_logging import console_log


def unsafe_acceptance_rate(frame: pd.DataFrame) -> float:
    unsafe_total = int(frame["unsafe_opportunity"].sum()) if not frame.empty else 0
    if unsafe_total == 0:
        return 0.0
    return float(frame["unsafe_accepted"].sum() / unsafe_total)


def false_rejection_rate(frame: pd.DataFrame) -> float:
    safe_total = int(frame["safe_opportunity"].sum()) if not frame.empty else 0
    if safe_total == 0:
        return 0.0
    return float(frame["false_rejected"].sum() / safe_total)


def escalation_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    return float(frame["escalated"].mean())


def catastrophic_episode_rate(episode_frame: pd.DataFrame) -> float:
    if episode_frame.empty:
        return 0.0
    return float(episode_frame["catastrophic_episode"].mean())


def safety_utility_summary(step_frame: pd.DataFrame, episode_frame: pd.DataFrame) -> dict[str, Any]:
    # console.log: phase6.metrics.safety_utility.summary.start
    console_log("phase6.metrics.safety_utility.summary.start", rows=len(step_frame))
    summary = {
        "unsafe_acceptance_rate": unsafe_acceptance_rate(step_frame),
        "false_rejection_rate": false_rejection_rate(step_frame),
        "escalation_rate": escalation_rate(step_frame),
        "mean_reward": float(step_frame["reward"].mean()) if not step_frame.empty else 0.0,
        "catastrophic_episode_rate": catastrophic_episode_rate(episode_frame),
    }
    # console.log: phase6.metrics.safety_utility.summary.complete
    console_log("phase6.metrics.safety_utility.summary.complete", **summary)
    return summary


def safety_utility_frontier(step_frame: pd.DataFrame, thresholds: list[float] | None = None) -> pd.DataFrame:
    # console.log: phase6.metrics.safety_utility.frontier.start
    console_log("phase6.metrics.safety_utility.frontier.start", rows=len(step_frame))
    thresholds = thresholds or [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    rows: list[dict[str, float]] = []
    for threshold in thresholds:
        simulated = step_frame.copy()
        simulated["unsafe_accepted"] = simulated["unsafe_opportunity"] & (
            simulated["risk_score"] < threshold
        )
        simulated["false_rejected"] = simulated["safe_opportunity"] & (
            simulated["risk_score"] >= threshold
        )
        simulated["escalated"] = False
        simulated["reward"] = 1.0
        simulated.loc[simulated["unsafe_accepted"], "reward"] = -1.0
        simulated.loc[simulated["false_rejected"], "reward"] = -0.25
        rows.append(
            {
                "threshold": float(threshold),
                "unsafe_acceptance_rate": unsafe_acceptance_rate(simulated),
                "false_rejection_rate": false_rejection_rate(simulated),
                "mean_reward": float(simulated["reward"].mean()) if not simulated.empty else 0.0,
            }
        )
    frame = pd.DataFrame(rows)
    # console.log: phase6.metrics.safety_utility.frontier.complete
    console_log("phase6.metrics.safety_utility.frontier.complete", points=len(frame))
    return frame
