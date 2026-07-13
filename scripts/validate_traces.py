from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log, validate_trace_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MAVS 10D JSONL traces.")
    parser.add_argument("--input", required=True, help="Path to JSONL trace file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    # console.log: phase1.script.validate_traces.start
    console_log("phase1.script.validate_traces.start", input=str(input_path))
    result = validate_trace_file(input_path)
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        # console.log: phase1.script.validate_traces.failed
        console_log(
            "phase1.script.validate_traces.failed",
            input=str(input_path),
            errors=len(result.errors),
            records=result.record_count,
        )
        return 1
    # console.log: phase1.script.validate_traces.complete
    console_log(
        "phase1.script.validate_traces.complete",
        input=str(input_path),
        records=result.record_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

