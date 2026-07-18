"""Manifest signing, release verification, and immutable namespace freeze."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from jsonschema import validate

from .common import REPO_ROOT, SCHEMA_VERSION, assert_clean_source_tree, canonical_bytes, config, file_sha256, read_json, relative, result_root, source_commit, write_json


def _sign(private_key: Ed25519PrivateKey, path: Path, destination: Path) -> dict[str, Any]:
    signature = private_key.sign(path.read_bytes())
    record = {"schema_version": SCHEMA_VERSION, "algorithm": "ed25519", "signed_path": relative(path), "signed_sha256": file_sha256(path), "signature_base64": base64.b64encode(signature).decode("ascii")}
    write_json(destination, record)
    return record


def verify_signature(record_path: Path, public_key_path: Path) -> bool:
    record = read_json(record_path)
    public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
    if not isinstance(public_key, Ed25519PublicKey):
        return False
    signed_path = REPO_ROOT / record["signed_path"]
    if file_sha256(signed_path) != record["signed_sha256"]:
        return False
    public_key.verify(base64.b64decode(record["signature_base64"]), signed_path.read_bytes())
    return True


def _artifact_graph(root: Path) -> list[dict[str, Any]]:
    excluded = {"release_manifest.json", "SEALED"}
    return [{"path": relative(path), "bytes": path.stat().st_size, "sha256": file_sha256(path)} for path in sorted(root.rglob("*")) if path.is_file() and path.name not in excluded and "release/signatures" not in path.as_posix() and "diagnostic_runs" not in path.parts and path.name not in {"release_report.json", "release_report.md"}]


def freeze_release() -> dict[str, Any]:
    assert_clean_source_tree(allow_phase10_results=True)
    root = result_root()
    cfg = config()
    final_audit = read_json(root / "reports" / "phase10_audit.json")
    if final_audit["status"] != "PASS" or final_audit["finding_count"] != 0:
        raise RuntimeError("P10_UNRESOLVED_AUDIT_FINDINGS: release freeze denied")
    ledger = read_json(root / "claims" / "claim_ledger.json")
    if any(claim["status"] == "provisional" for claim in ledger["claims"]):
        raise RuntimeError("P10_PROVISIONAL_CLAIM: release freeze denied")
    index_path = REPO_ROOT / "results" / "RESULTS_INDEX.md"
    index_text = "\n".join([
        "# Results Index", "", "## Preserved legacy evidence", "",
        "- `results/legacy/phase3_20260713_template_harness/`", "- `results/legacy/phase4_original/`", "- `results/legacy/phase5_original/`", "",
        "## Perception Closure Version 0.4", "", "- Phase 6: sealed synthesis-integrity evidence", "- Phase 7: sealed live runtime evidence", "- Phase 8: sealed ablation evidence", "- Phase 9: sealed paired and blind three-generation evidence", "- Phase 10: audited release package", "",
        "Default Version 0.4 claims: `results/perception_closure_v04/phase10/claims/CLAIMS.md`", "",
    ])
    index_path.write_text(index_text, encoding="utf-8")
    snapshot = root / "release" / "RESULTS_INDEX.snapshot.md"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(index_path, snapshot)
    tag_record = {
        "schema_version": SCHEMA_VERSION, "tag": cfg["release_policy"]["external_tag"],
        "source_commit": source_commit(), "tag_binding_recorded": True,
        "external_tag_created": False, "external_tag_authorized": cfg["release_policy"]["external_tag_authorized"],
        "reason": "WorkPlan prohibits external tagging without separate user authorization.",
    }
    write_json(root / "release" / "tag_record.json", tag_record)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    signature_root = root / "release" / "signatures"
    signature_root.mkdir(parents=True, exist_ok=True)
    public_path = signature_root / "public_key.pem"
    public_path.write_bytes(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    graph = _artifact_graph(root)
    manifest = {
        "schema_version": SCHEMA_VERSION, "release_id": cfg["release_policy"]["release_id"],
        "source_commit": source_commit(), "audit_sha256": file_sha256(root / "reports" / "phase10_audit.json"),
        "claim_ledger_sha256": file_sha256(root / "claims" / "claim_ledger.json"),
        "environment_lock_sha256": file_sha256(root / "manifests" / "environment_lock.json"),
        "input_index_sha256": file_sha256(root / "manifests" / "input_artifact_index.json"),
        "results_index_sha256": file_sha256(index_path), "artifact_graph": graph,
        "public_key_sha256": file_sha256(public_path),
        "freeze_policy": cfg["release_policy"], "status": "FROZEN",
    }
    manifest_path = root / "release" / "release_manifest.json"
    write_json(manifest_path, manifest)
    validate(manifest, read_json(REPO_ROOT / "schemas" / "v04" / "release_manifest.schema.json"))
    signed_paths = {
        "release_manifest": manifest_path,
        "audit_manifest": root / "manifests" / "audit_manifest.json",
        "input_artifact_index": root / "manifests" / "input_artifact_index.json",
        "environment_lock": root / "manifests" / "environment_lock.json",
        "seed_ledger": root / "manifests" / "seed_ledger.json",
        "claim_ledger": root / "claims" / "claim_ledger.json",
        "phase10_audit": root / "reports" / "phase10_audit.json",
    }
    signature_paths = []
    for name, signed_path in signed_paths.items():
        signature_path = signature_root / f"{name}.sig.json"
        _sign(private_key, signed_path, signature_path)
        signature_paths.append(signature_path)
    private_key = None
    signature_status = all(verify_signature(path, public_path) for path in signature_paths)
    release_report = {"schema_version": SCHEMA_VERSION, "release_id": manifest["release_id"], "artifact_count": len(graph), "signature_count": len(signature_paths), "signatures_valid": signature_status, "private_key_persisted": False, "source_commit": source_commit(), "status": "PASS" if signature_status else "FAIL"}
    write_json(root / "reports" / "release_report.json", release_report)
    (root / "reports" / "release_report.md").write_text(f"# Phase 10 Release Report\n\nStatus: {release_report['status']}\n\nArtifacts: {len(graph)}\n\nSignatures valid: {signature_status}\n", encoding="utf-8")
    seal = {"schema_version": SCHEMA_VERSION, "release_id": manifest["release_id"], "source_commit": source_commit(), "audit_sha256": manifest["audit_sha256"], "release_manifest_sha256": file_sha256(manifest_path), "claim_ledger_sha256": manifest["claim_ledger_sha256"], "public_key_sha256": file_sha256(public_path), "signature_sha256": {path.name: file_sha256(path) for path in signature_paths}, "release_report_sha256": file_sha256(root / "reports" / "release_report.json"), "results_index_sha256": file_sha256(index_path), "artifact_graph_sha256": __import__("hashlib").sha256(canonical_bytes(graph)).hexdigest(), "status": "FROZEN", "post_freeze_namespace_required": True}
    write_json(root / "SEALED", seal)
    return release_report
