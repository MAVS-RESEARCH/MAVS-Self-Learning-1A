"""Clean only an explicitly named, unsealed Phase 6 Version 0.4 run."""

from __future__ import annotations

import argparse
import shutil

from phase6_common import PHASE6_ROOT, run_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    target = run_root(args.run_id).resolve()
    root = PHASE6_ROOT.resolve()
    if target.parent != root:
        raise RuntimeError("Refusing cleanup outside the Phase 6 run root.")
    if (target / "SEALED").exists():
        raise RuntimeError("Refusing to clean a sealed Phase 6 run.")
    if target.exists():
        shutil.rmtree(target)
    # console.log: phase6.clean.named_run
    print(f'{{"event":"phase6.clean.named_run","run_id":"{args.run_id}"}}')


if __name__ == "__main__":
    main()

