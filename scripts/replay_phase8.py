"""Re-execute and hash-compare every deterministic Phase 8 result artifact."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mavs10d.core.hashing import file_sha256
from phase8_common import REPO_ROOT, run_root, write_json


EXCLUDED = {
    "integrity/replay_report.json",
    "reports/phase8_audit.json",
    "reports/console_log_registry.json",
    "reports/artifact_manifest.json",
    "SEALED",
}


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in EXCLUDED
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    before = snapshot(root)
    commands = [
        [sys.executable, "scripts/run_phase8_ablations.py", "--run-id", args.run_id],
        [sys.executable, "scripts/validate_phase8_isolation.py", "--run-id", args.run_id],
        [sys.executable, "scripts/aggregate_phase8.py", "--run-id", args.run_id],
    ]
    for command in commands:
        subprocess.run(command, cwd=REPO_ROOT, check=True)
    after = snapshot(root)
    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
    report = {
        "schema_version": "1.0.0", "run_id": args.run_id,
        "before_file_count": len(before), "after_file_count": len(after),
        "missing": missing, "added": added, "changed": changed,
        "command_count": len(commands), "passed": not missing and not added and not changed,
    }
    write_json(root / "integrity" / "replay_report.json", report)
    if not report["passed"]:
        raise RuntimeError(f"Phase 8 deterministic replay mismatch: {report}")
    # console.log: phase8.replay.complete
    print(f'{{"event":"phase8.replay.complete","files":{len(after)},"changed":0}}')


if __name__ == "__main__":
    main()
