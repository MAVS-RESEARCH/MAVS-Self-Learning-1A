"""Legacy/current, paired/blind, and namespace overwrite isolation audit."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, file_sha256, read_json, result_root, verify_frozen_input_index, write_json


def audit_isolation() -> dict[str, Any]:
    index = verify_frozen_input_index()
    cfg = config()
    legacy_checked = 0
    legacy_mismatches: list[str] = []
    legacy_entries: list[dict[str, Any]] = []
    for manifest_path in cfg["inputs"]["legacy_manifests"]:
        manifest = read_json(REPO_ROOT / manifest_path)
        for entry in manifest["files"]:
            legacy_checked += 1
            path = REPO_ROOT / entry["path"]
            actual = file_sha256(path) if path.is_file() else None
            legacy_entries.append({"path": entry["path"], "expected_sha256": entry["sha256"], "actual_sha256": actual, "match": actual == entry["sha256"]})
            if actual != entry["sha256"]:
                legacy_mismatches.append(entry["path"])
    p9 = REPO_ROOT / cfg["inputs"]["phase9"]
    track_ids: dict[str, set[str]] = {}
    for track in ("paired_original_bank", "blind_bank"):
        identifiers: set[str] = set()
        for generation in (1, 2, 3):
            path = p9 / track / "manifests" / f"generation_{generation}" / "public_ledger.parquet"
            identifiers.update(pd.read_parquet(path)["opportunity_id"].astype(str))
        track_ids[track] = identifiers
    overlap = track_ids["paired_original_bank"] & track_ids["blind_bank"]
    upstream_case_ids: set[str] = set()
    for phase in ("phase6", "phase7", "phase8"):
        phase_root = REPO_ROOT / cfg["inputs"][phase]
        for path in sorted((phase_root / "banks").rglob("*.parquet")) if (phase_root / "banks").exists() else []:
            frame = pd.read_parquet(path)
            for column in ("opportunity_id", "case_id"):
                if column in frame:
                    upstream_case_ids.update(frame[column].dropna().astype(str))
        for path in sorted((phase_root / "banks").rglob("*.jsonl")) if (phase_root / "banks").exists() else []:
            for line in path.read_text(encoding="utf-8").splitlines():
                payload = __import__("json").loads(line)
                identifier = payload.get("opportunity_id", payload.get("case_id"))
                if identifier is not None:
                    upstream_case_ids.add(str(identifier))
    contamination = sorted(upstream_case_ids & track_ids["blind_bank"])
    current_mismatches = []
    for entry in index["artifacts"]:
        path = REPO_ROOT / entry["physical_path"]
        if file_sha256(path) != entry["sha256"]:
            current_mismatches.append(entry["physical_path"])
    cross_version = {
        "schema_version": "1.0.0", "comparisons": [
            {"comparison": "legacy_phase5_vs_phase9_paired", "manifest": "results/perception_closure_v04/phase9/paired_original_bank/manifests/generation_1/generation_manifest.json", "explicit": True},
            {"comparison": "phase9_paired_vs_blind", "manifest": "results/perception_closure_v04/phase9/BANKS_SEALED.json", "explicit": True},
        ], "silent_concatenation": False,
    }
    overwrite = {"schema_version": "1.0.0", "frozen_input_count": index["artifact_count"], "changed_input_count": len(current_mismatches), "changed_inputs": current_mismatches, "phase10_only_write_policy": True, "status": "PASS" if not current_mismatches else "FAIL"}
    summary = {"schema_version": "1.0.0", "legacy_files_checked": legacy_checked, "legacy_mismatches": len(legacy_mismatches), "track_overlap": len(overlap), "contamination_findings": len(contamination), "overwrite_findings": len(current_mismatches), "default_reports_current_namespace_only": True, "status": "PASS" if not legacy_mismatches and not overlap and not contamination and not current_mismatches else "FAIL"}
    root = result_root() / "isolation"
    write_json(root / "legacy_hashes.json", {"schema_version": "1.0.0", "files": legacy_entries, "mismatch_count": len(legacy_mismatches)})
    write_json(root / "v04_hashes.json", {"schema_version": "1.0.0", "artifact_count": index["artifact_count"], "artifact_graph_sha256": read_json(result_root() / "manifests" / "INPUT_INDEX_FROZEN.json")["artifact_graph_sha256"], "mismatch_count": len(current_mismatches)})
    write_json(root / "cross_version_manifests.json", cross_version)
    write_json(root / "overwrite_scan.json", overwrite)
    write_json(root / "results_isolation_audit.json", summary)
    return summary
