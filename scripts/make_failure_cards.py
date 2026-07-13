from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.reports.failure_cards import write_failure_cards  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create MAVS Phase 6 failure cards.")
    parser.add_argument("--input", required=True, help="Trace JSONL file or raw trace directory.")
    parser.add_argument("--out", required=True, help="Failure card output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # console.log: phase6.script.make_failure_cards.start
    console_log("phase6.script.make_failure_cards.start", input=args.input, out=args.out)
    paths = write_failure_cards(args.input, args.out)
    # console.log: phase6.script.make_failure_cards.complete
    console_log("phase6.script.make_failure_cards.complete", cards=len(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
