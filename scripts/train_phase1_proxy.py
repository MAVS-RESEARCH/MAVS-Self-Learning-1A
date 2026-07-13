"""Train and freeze the development-only Phase 1 CTTA source predictor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.training.phase1_proxy import train_phase1_proxy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "artifacts/models/phase1_ctta")
    args = parser.parse_args()
    # console.log: phase1.train_proxy.step01.start
    console_log("phase1.train_proxy.step01.start", output=str(args.output))
    manifest = train_phase1_proxy(args.output)
    # console.log: phase1.train_proxy.step02.complete
    console_log(
        "phase1.train_proxy.step02.complete",
        checkpoint_sha256=manifest["checkpoint_sha256"],
        selected_trial=manifest["selected_trial"],
        trial_count=len(manifest["trials"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
