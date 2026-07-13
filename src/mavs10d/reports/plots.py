from __future__ import annotations

from pathlib import Path

import pandas as pd

from mavs10d.core.trace_logging import console_log


def write_metric_plots(summary: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    # console.log: phase6.reports.plots.write.start
    console_log("phase6.reports.plots.write.start", rows=len(summary), out_dir=str(out_dir))
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths = [
        _write_bar_svg(summary, root / "unsafe_acceptance_rate.svg", "unsafe_acceptance_rate"),
        _write_bar_svg(summary, root / "mean_reward.svg", "mean_reward"),
    ]
    # console.log: phase6.reports.plots.write.complete
    console_log("phase6.reports.plots.write.complete", files=[str(path) for path in paths])
    return paths


def _write_bar_svg(summary: pd.DataFrame, path: Path, metric: str) -> Path:
    width = 900
    bar_height = 22
    gap = 8
    label_width = 260
    rows = summary[["method_id", metric]].dropna().head(30) if metric in summary else pd.DataFrame()
    height = max(120, 60 + len(rows) * (bar_height + gap))
    values = [float(value) for value in rows[metric]] if not rows.empty else [0.0]
    minimum = min(0.0, min(values))
    maximum = max(1.0, max(values))
    span = maximum - minimum if maximum != minimum else 1.0
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="32" font-family="Arial" font-size="18" fill="#111111">{metric}</text>',
    ]
    for index, (_, row) in enumerate(rows.iterrows()):
        y = 55 + index * (bar_height + gap)
        value = float(row[metric])
        bar_width = int((value - minimum) / span * (width - label_width - 80))
        label = str(row["method_id"])[:34]
        elements.append(f'<text x="24" y="{y + 16}" font-family="Arial" font-size="12" fill="#333333">{label}</text>')
        elements.append(f'<rect x="{label_width}" y="{y}" width="{max(2, bar_width)}" height="{bar_height}" fill="#2f6f73"/>')
        elements.append(f'<text x="{label_width + max(8, bar_width) + 8}" y="{y + 16}" font-family="Arial" font-size="12" fill="#111111">{value:.4f}</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")
    return path
