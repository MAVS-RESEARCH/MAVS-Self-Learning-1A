from __future__ import annotations

from pathlib import Path

import pandas as pd

from mavs10d.core.trace_logging import console_log

CLAIM_LIMITATIONS = (
    "No frontier-model claim.",
    "No industrial-scale claim.",
    "No universal robustness claim.",
    "No proof that MAVS solves correlated failure.",
    "No claim that MAVS beats all governance methods.",
)

REQUIRED_EXPERIMENT_RECORDS = {
    "E1": ("Dynamic corruption", 21600),
    "E2": ("Correlated failure", 16000),
    "E3": ("Governance baseline comparison", 100800),
    "E4": ("Ablation study", 230400),
    "E5": ("Stress schedule sweep", 14400),
}


def read_summary(path: str | Path) -> pd.DataFrame:
    # console.log: phase6.reports.markdown.read_summary.start
    console_log("phase6.reports.markdown.read_summary.start", path=str(path))
    summary_path = Path(path)
    if summary_path.suffix == ".parquet":
        frame = pd.read_parquet(summary_path)
    else:
        frame = pd.read_csv(summary_path)
    # console.log: phase6.reports.markdown.read_summary.complete
    console_log("phase6.reports.markdown.read_summary.complete", rows=len(frame))
    return frame


def write_final_readme(
    summary: pd.DataFrame,
    out_dir: str | Path,
    *,
    table_paths: dict[str, Path],
    figure_paths: list[Path],
    failure_card_count: int,
) -> Path:
    # console.log: phase6.reports.markdown.write.start
    console_log("phase6.reports.markdown.write.start", rows=len(summary), out_dir=str(out_dir))
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    execution_summary = _execution_summary(summary, failure_card_count)
    coverage_table = _coverage_table(summary)
    mavs_focus = _mavs_focus(summary)
    negative_results = _negative_results(summary)
    collapse_cases = _collapse_cases(summary)
    text = "\n".join(
        [
            "# MAVS Chapter 10D Dynamic Validation V1",
            "",
            "## Execution Status",
            "",
            execution_summary,
            "",
            "## Minimum Coverage",
            "",
            coverage_table,
            "",
            "## MAVS-GC Focus Rows",
            "",
            mavs_focus,
            "",
            "## Reproduction Commands",
            "",
            "```bash",
            "python scripts/run_experiment.py --config configs/experiments/correlated_failure.yaml",
            "python scripts/run_suite.py --suite configs/suites/dynamic_governance_v1.yaml",
            "python scripts/aggregate_results.py --input results/raw --out results/processed/summary.parquet",
            "python scripts/make_failure_cards.py --input results/raw --out results/reports/dynamic_validation_v1/failure_cards",
            "python scripts/make_report.py --summary results/processed/summary.parquet --out results/reports/dynamic_validation_v1",
            "```",
            "",
            "## Scope",
            "",
            "This report evaluates dynamic governance behavior from reproducible MAVS Chapter 10D traces. No training is performed during final execution; any trained model path must load already frozen Phase 5 artifacts only.",
            "",
            "## Produced Artifacts",
            "",
            f"- Summary CSV: `{table_paths.get('summary_csv')}`",
            f"- Summary Markdown: `{table_paths.get('summary_md')}`",
            f"- Figures: `{', '.join(str(path) for path in figure_paths)}`",
            f"- Failure card count: `{failure_card_count}`",
            "- Full detail remains in `summary_metrics.csv`, `summary_metrics.md`, and the failure-card directory.",
            "",
            "## Negative Results And Collapse Cases",
            "",
            negative_results,
            "",
            collapse_cases,
            "",
            "## Claim Limitations",
            "",
            *[f"- {item}" for item in CLAIM_LIMITATIONS],
            "",
        ]
    )
    readme.write_text(text, encoding="utf-8")
    # console.log: phase6.reports.markdown.write.complete
    console_log("phase6.reports.markdown.write.complete", path=str(readme))
    return readme


def _execution_summary(summary: pd.DataFrame, failure_card_count: int) -> str:
    # console.log: phase6.reports.markdown.execution_summary.start
    console_log("phase6.reports.markdown.execution_summary.start", rows=len(summary))
    if summary.empty:
        return "- No summary rows were available."
    total_steps = int(summary.get("step_count", pd.Series(dtype=float)).sum())
    total_episodes = int(summary.get("episode_count", pd.Series(dtype=float)).sum())
    total_required = sum(records for _, records in REQUIRED_EXPERIMENT_RECORDS.values())
    environment_count = int(summary["environment_family"].nunique()) if "environment_family" in summary else 0
    method_count = int(summary["method_id"].nunique()) if "method_id" in summary else 0
    trace_completeness = _weighted_average(summary, "trace_completeness", "step_count")
    audit_trace_completeness = _weighted_average(summary, "audit_trace_completeness", "step_count")
    status = "complete" if total_steps >= total_required else "incomplete"
    # console.log: phase6.reports.markdown.execution_summary.complete
    console_log(
        "phase6.reports.markdown.execution_summary.complete",
        status=status,
        required_records=total_required,
        actual_records=total_steps,
    )
    return "\n".join(
        [
            f"- Full minimum execution status: `{status}`.",
            f"- Required trace records: `{total_required}`.",
            f"- Aggregated trace records: `{total_steps}`.",
            f"- Episode rows: `{total_episodes}`.",
            f"- Dynamic environment families represented: `{environment_count}`.",
            f"- Method ids represented: `{method_count}`.",
            f"- Failure cards generated: `{failure_card_count}`.",
            f"- Weighted trace completeness: `{trace_completeness:.4f}`.",
            f"- Weighted audit-trace completeness: `{audit_trace_completeness:.4f}`.",
        ]
    )


def _coverage_table(summary: pd.DataFrame) -> str:
    # console.log: phase6.reports.markdown.coverage_table.start
    console_log("phase6.reports.markdown.coverage_table.start", rows=len(summary))
    actual = {}
    if not summary.empty and {"experiment_code", "step_count"}.issubset(summary.columns):
        actual = summary.groupby("experiment_code")["step_count"].sum().astype(int).to_dict()
    rows = ["| Experiment | Scope | Required Records | Actual Records | Coverage | Status |", "| --- | --- | ---: | ---: | ---: | --- |"]
    for experiment_code, (scope, required_records) in REQUIRED_EXPERIMENT_RECORDS.items():
        actual_records = int(actual.get(experiment_code, 0))
        coverage = actual_records / required_records if required_records else 0.0
        status = "complete" if actual_records >= required_records else "incomplete"
        rows.append(
            f"| `{experiment_code}` | {scope} | {required_records} | {actual_records} | {coverage:.4f} | `{status}` |"
        )
    # console.log: phase6.reports.markdown.coverage_table.complete
    console_log("phase6.reports.markdown.coverage_table.complete", experiments=len(REQUIRED_EXPERIMENT_RECORDS))
    return "\n".join(rows)


def _mavs_focus(summary: pd.DataFrame) -> str:
    # console.log: phase6.reports.markdown.mavs_focus.start
    console_log("phase6.reports.markdown.mavs_focus.start", rows=len(summary))
    if summary.empty:
        return "- No MAVS-GC rows were available."
    mask = summary["method_id"].astype(str).str.contains("mavs_gc", regex=False)
    focus = summary[mask].copy()
    if focus.empty:
        return "- No MAVS-GC rows were available."
    ordered = focus.sort_values(["experiment_code", "environment_family", "method_id"])
    columns = [
        "experiment_code",
        "environment_family",
        "method_id",
        "seed_count",
        "step_count",
        "mean_reward",
        "unsafe_acceptance_rate",
        "false_rejection_rate",
        "escalation_rate",
        "correlation_collapse_sensitivity",
    ]
    available = [column for column in columns if column in ordered.columns]
    # console.log: phase6.reports.markdown.mavs_focus.complete
    console_log("phase6.reports.markdown.mavs_focus.complete", rows=len(ordered))
    return _compact_markdown_table(ordered[available], limit=20)


def _negative_results(summary: pd.DataFrame) -> str:
    if summary.empty or "unsafe_acceptance_rate" not in summary:
        return "- No summary rows were available."
    negative = summary[summary["unsafe_acceptance_rate"] > 0.0].copy()
    if negative.empty:
        return "- No unsafe-acceptance negative result appears in the aggregated summary."
    negative = negative.sort_values(["unsafe_acceptance_rate", "mean_reward"], ascending=[False, True])
    table = _compact_markdown_table(
        negative[
            [
                "experiment_code",
                "environment_family",
                "method_id",
                "unsafe_acceptance_rate",
                "false_rejection_rate",
                "mean_reward",
                "step_count",
            ]
        ],
        limit=12,
    )
    return "\n".join(
        [
            f"- Unsafe-acceptance negative-result rows: `{len(negative)}`.",
            "- Highest UAR rows:",
            "",
            table,
        ]
    )


def _collapse_cases(summary: pd.DataFrame) -> str:
    if summary.empty or "correlation_collapse_sensitivity" not in summary:
        return "- Correlated-collapse sensitivity was not available."
    collapse = summary[summary["correlation_collapse_sensitivity"] > 0.0].copy()
    if collapse.empty:
        return "- No positive correlated-collapse sensitivity was observed in the aggregate rows."
    collapse = collapse.sort_values("correlation_collapse_sensitivity", ascending=False)
    table = _compact_markdown_table(
        collapse[
            [
                "experiment_code",
                "environment_family",
                "method_id",
                "independent_mean_reward",
                "shared_failure_mean_reward",
                "correlation_collapse_sensitivity",
                "step_count",
            ]
        ],
        limit=12,
    )
    return "\n".join(
        [
            f"- Positive correlated-collapse sensitivity rows: `{len(collapse)}`.",
            "- Largest reward drops under shared/correlated conditions:",
            "",
            table,
        ]
    )


def _compact_markdown_table(frame: pd.DataFrame, *, limit: int) -> str:
    if frame.empty:
        return "_No rows._"
    visible = frame.head(limit)
    columns = [str(column) for column in visible.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in visible.iterrows():
        rows.append("| " + " | ".join(_format_cell(row[column]) for column in visible.columns) + " |")
    remaining = len(frame) - len(visible)
    if remaining > 0:
        truncation_cells = ["..."] + [f"{remaining} additional rows in summary_metrics.csv"] + [""] * (len(columns) - 2)
        rows.append("| " + " | ".join(truncation_cells) + " |")
    return "\n".join(rows)


def _weighted_average(frame: pd.DataFrame, value_column: str, weight_column: str) -> float:
    if value_column not in frame or weight_column not in frame:
        return 0.0
    weights = frame[weight_column].astype(float)
    total_weight = float(weights.sum())
    if total_weight == 0.0:
        return 0.0
    return float((frame[value_column].astype(float) * weights).sum() / total_weight)


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")
