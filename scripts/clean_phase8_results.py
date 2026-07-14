"""Delete one explicitly named unsealed Phase 8 run and nothing else."""

from __future__ import annotations

import argparse
import shutil

from phase8_common import PHASE8_ROOT, run_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id).resolve()
    phase_root = PHASE8_ROOT.resolve()
    if root.parent != phase_root:
        raise RuntimeError("Resolved cleanup target escaped the Phase 8 result namespace.")
    if (root / "SEALED").exists():
        raise RuntimeError("Refusing to clean a sealed Phase 8 run.")
    if root.exists():
        shutil.rmtree(root)
    # console.log: phase8.clean.named_run
    print(f'{{"event":"phase8.clean.named_run","run_id":"{args.run_id}"}}')


if __name__ == "__main__":
    main()
