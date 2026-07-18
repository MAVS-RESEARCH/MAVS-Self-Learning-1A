"""Create track-level signed manifests before the independent audit."""

from __future__ import annotations

import subprocess

from mavs10d.core.hashing import file_sha256, stable_hash
from phase9_common import PHASE9_ROOT, REPO_ROOT, file_manifest, track_root, write_json


def main() -> None:
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()
    for track_id in ("paired_original_bank", "blind_bank"):
        root = track_root(track_id); excluded = {"SIGNED_MANIFEST.json", "reports/phase9_audit.json", "reports/artifact_manifest.json", "reports/console_log_registry.json"}; files = file_manifest(root, excluded)
        body = {"schema_version": "1.0.0", "track_id": track_id, "source_commit": source_commit, "bank_seal_sha256": file_sha256(PHASE9_ROOT / "BANKS_SEALED.json"), "file_count": len(files), "files": files, "claim_status": "diagnostic_only" if track_id == "paired_original_bank" else "provisional_until_phase10"}
        body["signature"] = stable_hash(body); write_json(root / "SIGNED_MANIFEST.json", body)
    # console.log: phase9.manifest.complete
    print('{"event":"phase9.manifest.complete","tracks":2,"signed":true}')


if __name__ == "__main__": main()

