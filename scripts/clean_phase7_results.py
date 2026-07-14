"""Remove only one explicitly named, unsealed Phase 7 run."""

from __future__ import annotations

import argparse
import shutil

from phase7_common import run_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    if (root / "SEALED").exists():
        raise RuntimeError("Refusing to clean a sealed Phase 7 run.")
    if root.exists():
        shutil.rmtree(root)
    # console.log: phase7.clean.named_run
    print(f'{{"event":"phase7.clean.named_run","run_id":"{args.run_id}"}}')


if __name__ == "__main__":
    main()
