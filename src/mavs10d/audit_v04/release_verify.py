"""Read-only verification of the complete frozen release graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import REPO_ROOT, file_sha256, read_json, relative, result_root, stable_hash
from .release import verify_signature


REQUIRED_ARTIFACTS = (
    "manifests/audit_manifest.json", "manifests/seed_ledger.json", "manifests/environment_lock.json",
    "manifests/input_artifact_index.json", "candidate_audit/candidate_inventory.parquet",
    "candidate_audit/spot_audit.parquet", "candidate_audit/full_template_audit.parquet",
    "certification/recomputed_gate_vectors.parquet", "certification/gate_mismatches.parquet",
    "permutation/challenge_manifest.json", "permutation/outcome_comparison.json",
    "taint/hidden_field_inventory.json", "taint/process_access_audit.json", "taint/memory_scan.json",
    "replay/sample_manifest.json", "replay/protected_failure_manifest.json", "replay/artifact_comparison.json",
    "trace/completeness.json", "trace/lineage.json", "trace/terminal_authority.json", "trace/residual_escalation.json",
    "isolation/legacy_hashes.json", "isolation/v04_hashes.json", "isolation/cross_version_manifests.json", "isolation/overwrite_scan.json",
    "claims/claim_ledger.json", "claims/CLAIMS.md", "claims/claim_source_map.json",
    "release/release_manifest.json", "release/tag_record.json", "release/RESULTS_INDEX.snapshot.md",
    "reports/phase10_audit.json", "reports/phase10_audit.md", "reports/reproducibility_report.md", "reports/release_report.md", "REPRODUCE.md", "SEALED",
)


def verify_release() -> dict[str, Any]:
    root = result_root()
    missing = [path for path in REQUIRED_ARTIFACTS if not (root / path).is_file()]
    seal = read_json(root / "SEALED")
    manifest_path = root / "release" / "release_manifest.json"
    manifest = read_json(manifest_path)
    public_key = root / "release" / "signatures" / "public_key.pem"
    signature_paths = sorted((root / "release" / "signatures").glob("*.sig.json"))
    signatures_valid = all(verify_signature(path, public_key) for path in signature_paths)
    graph_mismatches = []
    for entry in manifest["artifact_graph"]:
        path = REPO_ROOT / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["bytes"] or file_sha256(path) != entry["sha256"]:
            graph_mismatches.append(entry["path"])
    seal_checks = {
        "release_manifest": seal["release_manifest_sha256"] == file_sha256(manifest_path),
        "claim_ledger": seal["claim_ledger_sha256"] == file_sha256(root / "claims" / "claim_ledger.json"),
        "public_key": seal["public_key_sha256"] == file_sha256(public_key),
        "release_report": seal["release_report_sha256"] == file_sha256(root / "reports" / "release_report.json"),
        "results_index": seal["results_index_sha256"] == file_sha256(REPO_ROOT / "results" / "RESULTS_INDEX.md"),
        "artifact_graph": seal["artifact_graph_sha256"] == stable_hash(manifest["artifact_graph"]),
        "signatures": all(seal["signature_sha256"].get(path.name) == file_sha256(path) for path in signature_paths),
    }
    graph_paths = {entry["path"] for entry in manifest["artifact_graph"]}
    structural = {relative(root / "SEALED"), relative(manifest_path), relative(root / "reports" / "release_report.json"), relative(root / "reports" / "release_report.md"), relative(public_key), *(relative(path) for path in signature_paths)}
    authoritative_files = {relative(path) for path in root.rglob("*") if path.is_file() and "diagnostic_runs" not in path.parts}
    unindexed = sorted(authoritative_files - graph_paths - structural)
    ledger = read_json(root / "claims" / "claim_ledger.json")
    provisional = [claim["claim_id"] for claim in ledger["claims"] if claim["status"] == "provisional"]
    status = "PASS" if not missing and signatures_valid and not graph_mismatches and all(seal_checks.values()) and not unindexed and not provisional else "FAIL"
    return {"required_artifact_count": len(REQUIRED_ARTIFACTS), "missing_artifact_count": len(missing), "signature_count": len(signature_paths), "signatures_valid": signatures_valid, "graph_artifact_count": len(graph_paths), "graph_mismatch_count": len(graph_mismatches), "seal_checks": seal_checks, "unindexed_evidence_count": len(unindexed), "unindexed_evidence": unindexed, "provisional_claim_count": len(provisional), "status": status}

