from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.runner import ExperimentRunner  # noqa: E402
from mavs10d.core.config import OutputConfig, load_experiment_config  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one MAVS 10D experiment.")
    parser.add_argument("--config", required=True, help="Path to experiment YAML.")
    parser.add_argument("--output", help="Optional trace-path override; inherited behavior is unchanged when omitted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # console.log: phase1.script.run_experiment.start
    console_log("phase1.script.run_experiment.start", config=args.config)
    runner = ExperimentRunner(repo_root=REPO_ROOT)
    if args.output:
        config = load_experiment_config(args.config)
        config = replace(config, outputs=OutputConfig(raw_traces=Path(args.output)))
        result = runner.run(config)
    else:
        result = runner.run_config_path(args.config)
    # console.log: phase1.script.run_experiment.complete
    console_log(
        "phase1.script.run_experiment.complete",
        output=str(result.output_path),
        records=result.records_written,
        config_hash=result.config_hash,
        git_commit=result.git_commit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

