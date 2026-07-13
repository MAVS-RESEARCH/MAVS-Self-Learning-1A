from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.reports.markdown import read_summary, write_final_readme  # noqa: E402
from mavs10d.reports.plots import write_metric_plots  # noqa: E402
from mavs10d.reports.tables import write_report_tables  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the MAVS Phase 6 final report.")
    parser.add_argument("--summary", required=True, help="Summary parquet or CSV path.")
    parser.add_argument("--out", required=True, help="Report output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # console.log: phase6.script.make_report.start
    console_log("phase6.script.make_report.start", summary=args.summary, out=args.out)
    summary = read_summary(args.summary)
    out_dir = Path(args.out)
    tables = write_report_tables(summary, out_dir)
    figures = write_metric_plots(summary, _figure_dir(out_dir))
    failure_dir = out_dir / "failure_cards"
    failure_count = len(list(failure_dir.glob("*.md"))) if failure_dir.exists() else 0
    readme = write_final_readme(
        summary,
        out_dir,
        table_paths=tables,
        figure_paths=figures,
        failure_card_count=failure_count,
    )
    # console.log: phase6.script.make_report.complete
    console_log("phase6.script.make_report.complete", readme=str(readme))
    return 0


def _figure_dir(out_dir: Path) -> Path:
    repo_report_root = REPO_ROOT / "results" / "reports"
    try:
        out_dir.resolve().relative_to(repo_report_root.resolve())
    except ValueError:
        return out_dir.parent / "figures"
    return REPO_ROOT / "results" / "figures"


if __name__ == "__main__":
    raise SystemExit(main())
