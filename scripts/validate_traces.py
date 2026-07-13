from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import (  # noqa: E402
    console_log,
    validate_self_learning_trace_file,
    validate_trace_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MAVS 10D JSONL traces.")
    parser.add_argument("--input", required=True, help="Path to JSONL trace file.")
    parser.add_argument("--contract", choices=("inherited", "self-learning"), default="inherited")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    event_prefix = "phase0.script.validate_traces" if args.contract == "self-learning" else "phase1.script.validate_traces"
    # console.log: phase0/phase1.script.validate_traces.start
    console_log(f"{event_prefix}.start", input=str(input_path), contract=args.contract)
    result = (
        validate_trace_file(input_path)
        if args.contract == "inherited"
        else validate_self_learning_trace_file(
            input_path, REPO_ROOT / "schemas/decision_trace.schema.json"
        )
    )
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        # console.log: phase0/phase1.script.validate_traces.failed
        console_log(
            f"{event_prefix}.failed",
            input=str(input_path),
            errors=len(result.errors),
            records=result.record_count,
        )
        return 1
    # console.log: phase0/phase1.script.validate_traces.complete
    console_log(
        f"{event_prefix}.complete",
        input=str(input_path),
        records=result.record_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

