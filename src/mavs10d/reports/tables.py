from __future__ import annotations

from pathlib import Path

import pandas as pd

from mavs10d.core.trace_logging import console_log


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._\n"
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(_format_cell(row[column]) for column in frame.columns) + " |")
    return "\n".join([header, separator, *rows]) + "\n"


def write_report_tables(summary: pd.DataFrame, out_dir: str | Path) -> dict[str, Path]:
    # console.log: phase6.reports.tables.write.start
    console_log("phase6.reports.tables.write.start", rows=len(summary), out_dir=str(out_dir))
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    summary_csv = root / "summary_metrics.csv"
    summary_md = root / "summary_metrics.md"
    summary.to_csv(summary_csv, index=False)
    summary_md.write_text(dataframe_to_markdown(summary), encoding="utf-8")
    paths = {"summary_csv": summary_csv, "summary_md": summary_md}
    # console.log: phase6.reports.tables.write.complete
    console_log("phase6.reports.tables.write.complete", files=[str(path) for path in paths.values()])
    return paths


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")
