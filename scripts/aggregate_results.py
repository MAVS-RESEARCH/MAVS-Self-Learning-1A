from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.calibration import calibration_error  # noqa: E402
from mavs10d.metrics.collapse import correlation_collapse_sensitivity  # noqa: E402
from mavs10d.metrics.dynamic import adaptation_lag, recovery_lag, trace_completeness  # noqa: E402
from mavs10d.metrics.episode_metrics import episode_rows, step_rows_from_input  # noqa: E402
from mavs10d.metrics.safety_utility import safety_utility_frontier, safety_utility_summary  # noqa: E402
from mavs10d.metrics.stats import metric_distribution, worst_case_episode  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate MAVS 10D JSONL traces into Phase 6 metrics.")
    parser.add_argument("--input", required=True, help="Trace JSONL file or directory.")
    parser.add_argument("--out", required=True, help="Summary output path, usually results/processed/summary.parquet.")
    return parser.parse_args()


def aggregate_results(input_path: str | Path, out_path: str | Path) -> pd.DataFrame:
    # console.log: phase6.script.aggregate.start
    console_log("phase6.script.aggregate.start", input=str(input_path), out=str(out_path))
    step_frame = step_rows_from_input(input_path)
    episode_frame = episode_rows(step_frame)
    summary = _summary_rows(step_frame, episode_frame)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_summary(summary, out)
    step_frame.to_csv(out.with_name("step_metrics.csv"), index=False)
    episode_frame.to_csv(out.with_name("episode_metrics.csv"), index=False)
    safety_utility_frontier(step_frame).to_csv(out.with_name("safety_utility_frontier.csv"), index=False)
    worst_case_episode(episode_frame).to_csv(out.with_name("worst_case_episodes.csv"), index=False)
    # console.log: phase6.script.aggregate.complete
    console_log("phase6.script.aggregate.complete", rows=len(summary), out=str(out))
    return summary


def _summary_rows(step_frame: pd.DataFrame, episode_frame: pd.DataFrame) -> pd.DataFrame:
    # console.log: phase6.script.aggregate.summary_rows.start
    console_log("phase6.script.aggregate.summary_rows.start", rows=len(step_frame))
    if step_frame.empty:
        return pd.DataFrame()
    group_cols = ["benchmark_set", "experiment_code", "environment_family", "method_id"]
    rows = []
    for keys, group in step_frame.groupby(group_cols, dropna=False):
        group_filter = (
            (episode_frame["benchmark_set"] == keys[0])
            & (episode_frame["experiment_code"] == keys[1])
            & (episode_frame["environment_family"] == keys[2])
            & (episode_frame["method_id"] == keys[3])
        )
        episodes = episode_frame[group_filter]
        summary = safety_utility_summary(group, episodes)
        summary.update(trace_completeness(group))
        summary["calibration_error"] = calibration_error(group)
        summary["adaptation_lag"] = adaptation_lag(group)
        summary["recovery_lag"] = recovery_lag(group)
        summary.update(correlation_collapse_sensitivity(group))
        reward_stats = metric_distribution(episodes["reward_mean"] if not episodes.empty else [])
        summary.update({f"reward_{key}": value for key, value in reward_stats.items()})
        summary.update(
            {
                "benchmark_set": keys[0],
                "experiment_code": keys[1],
                "environment_family": keys[2],
                "method_id": keys[3],
                "seed_count": int(group["seed"].nunique()),
                "step_count": int(len(group)),
                "episode_count": int(episodes["episode_id"].nunique()) if not episodes.empty else 0,
            }
        )
        rows.append(summary)
    frame = pd.DataFrame(rows)
    # console.log: phase6.script.aggregate.summary_rows.complete
    console_log("phase6.script.aggregate.summary_rows.complete", rows=len(frame))
    return frame


def _write_summary(summary: pd.DataFrame, out: Path) -> None:
    if out.suffix == ".parquet":
        summary.to_parquet(out, index=False)
    else:
        summary.to_csv(out, index=False)


def main() -> int:
    args = parse_args()
    aggregate_results(args.input, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
