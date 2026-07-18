"""Remove only an unsealed Phase 9 namespace."""

from __future__ import annotations

import argparse
import shutil

from phase9_common import PHASE9_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-phase9", action="store_true", required=True)
    args = parser.parse_args()
    if not args.all_phase9:
        raise RuntimeError("Explicit Phase 9 scope is required.")
    if (PHASE9_ROOT / "SEALED").exists():
        raise RuntimeError("Refusing to clean sealed Phase 9 results.")
    if PHASE9_ROOT.exists():
        shutil.rmtree(PHASE9_ROOT)
    # console.log: phase9.clean.complete
    print('{"event":"phase9.clean.complete","scope":"phase9_only"}')


if __name__ == "__main__":
    main()

