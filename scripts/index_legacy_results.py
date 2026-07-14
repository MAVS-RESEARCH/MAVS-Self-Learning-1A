"""Create immutable indexed references for Phase 3-5 legacy evidence."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from mavs10d.core.hashing import file_sha256, git_commit_hash
from phase6_common import REPO_ROOT, write_json


LEGACY_GROUPS = {
    "phase3_20260713_template_harness": ["results/manifests/phase3_20260713", "results/checkpoints/phase3_20260713", "results/raw/phase3_20260713", "results/processed/phase3_20260713", "results/reports/phase3_20260713"],
    "phase4_original": ["results/manifests/phase4_authoritative", "results/raw/phase4_authoritative", "results/aggregates/phase4_authoritative", "results/reports/phase4_authoritative"],
    "phase5_original": ["results/manifests/phase5_authoritative", "results/raw/phase5_authoritative", "results/aggregates/phase5_authoritative", "results/figures/phase5_authoritative", "results/reports/phase5_authoritative"],
}


def git_blob(path: Path) -> str | None:
    result = subprocess.run(["git", "ls-files", "-s", "--", path.relative_to(REPO_ROOT).as_posix()], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout.split()[1] if result.stdout.strip() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    rows = []
    for logical_name, sources in LEGACY_GROUPS.items():
        files = []
        for source in sources:
            source_path = REPO_ROOT / source
            for path in sorted(source_path.rglob("*")) if source_path.exists() else []:
                if path.is_file():
                    files.append({"path": path.relative_to(REPO_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path), "git_blob_oid": git_blob(path), "lfs_oid": None})
        payload = {"schema_version": "1.0.0", "logical_namespace": logical_name, "storage_mode": "immutable_indexed_reference", "source_paths": sources, "code_commit": git_commit_hash(REPO_ROOT), "file_count": len(files), "files": files, "claim_classification": "Phase 3 validates deterministic lifecycle, certification plumbing, promotion, rejection, persistence, and rollback mechanics; it does not validate genuine differentiated diagnostic synthesis." if logical_name.startswith("phase3") else "original preserved evidence"}
        output = REPO_ROOT / "results" / "legacy" / logical_name / "legacy_manifest.json"
        write_json(output, payload)
        rows.append((logical_name, len(files), output.relative_to(REPO_ROOT).as_posix()))
    index = ["# Results Index", "", "Original result locations remain byte-identical. Legacy namespaces below are immutable indexed references with per-file checksums.", "", "| Namespace | Files | Manifest |", "|---|---:|---|"]
    index.extend(f"| `{name}` | {count} | `{manifest}` |" for name, count, manifest in rows)
    index.extend(["", "Revised Version 0.4 evidence is isolated under `results/perception_closure_v04/`.", ""])
    (REPO_ROOT / "results" / "RESULTS_INDEX.md").write_text("\n".join(index), encoding="utf-8")
    # console.log: phase6.legacy_index.complete
    print(f'{{"event":"phase6.legacy_index.complete","namespaces":{len(rows)}}}')


if __name__ == "__main__":
    main()

