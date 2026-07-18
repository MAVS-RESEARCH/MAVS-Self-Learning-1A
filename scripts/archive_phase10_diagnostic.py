"""Preserve a rejected sealed Phase 10 run as immutable diagnostic evidence."""

from __future__ import annotations

import shutil
from pathlib import Path

from mavs10d.audit_v04.common import file_sha256, result_root, write_json


def main() -> None:
    root = result_root()
    seal = root / "SEALED"
    if not seal.is_file():
        raise RuntimeError("P10_DIAGNOSTIC_SOURCE_UNSEALED: archive requires a sealed rejected run")
    destination = root / "diagnostic_runs" / "rejected_5963890_postfreeze_contract_gap"
    if destination.exists():
        raise RuntimeError("P10_DIAGNOSTIC_ARCHIVE_EXISTS: append-only archive already exists")
    source_files = [path for path in sorted(root.rglob("*")) if path.is_file() and "diagnostic_runs" not in path.parts]
    entries = []
    for path in source_files:
        relative = path.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        entries.append({"path": relative.as_posix(), "bytes": target.stat().st_size, "sha256": file_sha256(target)})
    write_json(destination / "DIAGNOSTIC_ARCHIVE.json", {"schema_version": "1.0.0", "source_commit": "5963890bfdb9c8a3b986ed83d19d7cd2024f0325", "reason": "post-freeze literal contract gaps; not claim eligible", "file_count": len(entries), "files": entries, "immutable": True})
    # Phase 10 step: report rejected-run diagnostic preservation.
    print({"event": "phase10.diagnostic_archive.complete", "file_count": len(entries), "destination": destination.as_posix()})


if __name__ == "__main__":
    main()
