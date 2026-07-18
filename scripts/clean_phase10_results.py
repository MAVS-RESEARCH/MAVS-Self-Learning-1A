"""Remove only an unsealed Phase 10 namespace."""

from __future__ import annotations

import shutil

from mavs10d.audit_v04.common import result_root


def main() -> None:
    root = result_root()
    if (root / "SEALED").exists():
        raise RuntimeError("P10_RELEASE_FROZEN: refusing to clean sealed Phase 10 results")
    if root.exists():
        shutil.rmtree(root)
    # Phase 10 step: report isolated namespace cleanup.
    print('{"event":"phase10.clean.complete","scope":"phase10_only"}')


if __name__ == "__main__":
    main()

