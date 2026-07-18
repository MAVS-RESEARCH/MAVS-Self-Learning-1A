"""Freeze every Phase 6-9 artifact and candidate linkage before audit analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import (
    REPO_ROOT,
    SCHEMA_VERSION,
    all_files,
    artifact_role,
    assert_clean_source_tree,
    binding_flags,
    config,
    environment_record,
    file_sha256,
    git_blob_oid,
    lfs_oid,
    relative,
    result_root,
    source_commit,
    stable_hash,
    write_json,
)


def build_input_index() -> dict[str, Any]:
    cfg = config()
    root = result_root()
    assert_clean_source_tree(allow_phase10_results=True)
    if root.exists() and (root / "SEALED").exists():
        raise RuntimeError("P10_RELEASE_ALREADY_FROZEN: post-freeze work requires a new namespace")
    roots = {phase: REPO_ROOT / path for phase, path in cfg["inputs"].items() if phase.startswith("phase")}
    artifacts: list[dict[str, Any]] = []
    for path in all_files(roots.values()):
        phase = next(key for key, phase_root in roots.items() if path.is_relative_to(phase_root))
        artifacts.append({
            "logical_role": artifact_role(path),
            "physical_path": relative(path),
            "byte_size": path.stat().st_size,
            "sha256": file_sha256(path),
            "schema_version": SCHEMA_VERSION,
            "bindings": binding_flags(path),
            "git_object_id": git_blob_oid(path),
            "lfs_object_id": lfs_oid(path),
            "claim_eligibility": "diagnostic_only" if phase in {"phase6", "phase7", "phase8"} or "paired_original_bank" in relative(path) else "phase10_gate_dependent",
            "legacy_current_status": "current_v04",
            "phase": int(phase.removeprefix("phase")),
        })
    p6 = roots["phase6"]
    candidates: list[dict[str, Any]] = []
    for directory in sorted((p6 / "candidates").iterdir()):
        if not directory.is_dir():
            continue
        candidate = __import__("json").loads((directory / "candidate.json").read_text(encoding="utf-8"))
        lifecycle = __import__("json").loads((p6 / "manifests" / "lifecycle_state.json").read_text(encoding="utf-8"))
        lifecycle_by_id = {item["candidate_id"]: item for item in lifecycle.get("candidates", lifecycle if isinstance(lifecycle, list) else [])}
        candidates.append({
            "candidate_id": candidate["candidate_id"],
            "operation": candidate["lineage"]["operation"],
            "raw_failure_evidence": candidate["lineage"]["triggering_contrast"],
            "minimal_contrast": candidate["lineage"]["triggering_contrast"],
            "ast": relative(directory / "candidate.json"),
            "parameters": relative(directory / "parameter_search.parquet"),
            "complete_search_trace": relative(directory / "structure_search.parquet"),
            "contracts": relative(directory / "candidate.json"),
            "semantic_identity": relative(directory / "semantic_identity.json"),
            "behavioral_fingerprint": relative(directory / "behavioral_fingerprint.parquet"),
            "operation_check": relative(directory / "operation_compliance.json"),
            "witness": relative(directory / "perception_extension_witness.json"),
            "independent_gate_vector": relative(directory / "independent_gate_vector.json"),
            "certification_trace": relative(directory / "certification_trace.parquet"),
            "lifecycle": lifecycle_by_id.get(candidate["candidate_id"], {}),
            "runtime_descendants": [relative(path) for path in sorted((roots["phase7"] / "programs").glob("*.json")) if candidate["candidate_id"] in path.read_text(encoding="utf-8", errors="ignore")],
            "phase9_descendant_root": relative(roots["phase9"]),
        })
    environment = environment_record()
    stratified_candidates = [
        item["candidate_id"] for item in candidates
        if item["candidate_id"].endswith(("-B", "-C", "-I"))
    ]
    if len(stratified_candidates) != cfg["audit_sample"]["candidate_spot_count"]:
        raise RuntimeError("P10_SAMPLE_STRATA_INCOMPLETE: expected B/C/I representative for every operation")
    sample_plan = {
        "schema_version": SCHEMA_VERSION,
        **cfg["audit_sample"],
        "frozen_before_audit": True,
        "candidate_ids": stratified_candidates,
    }
    index = {
        "schema_version": SCHEMA_VERSION,
        "source_commit": source_commit(),
        "artifact_count": len(artifacts),
        "candidate_count": len(candidates),
        "artifacts": artifacts,
        "candidates": candidates,
    }
    write_json(root / "manifests" / "environment_lock.json", environment)
    write_json(root / "manifests" / "seed_ledger.json", {"schema_version": SCHEMA_VERSION, "phase10_seed": cfg["audit_sample"]["seed"], "upstream_seed_artifacts": [a["physical_path"] for a in artifacts if "seed" in a["physical_path"].lower()]})
    write_json(root / "manifests" / "sample_plan.json", sample_plan)
    write_json(root / "manifests" / "input_artifact_index.json", index)
    marker = {
        "schema_version": SCHEMA_VERSION,
        "frozen": True,
        "source_commit": source_commit(),
        "input_artifact_index_sha256": file_sha256(root / "manifests" / "input_artifact_index.json"),
        "sample_plan_sha256": file_sha256(root / "manifests" / "sample_plan.json"),
        "environment_lock_sha256": file_sha256(root / "manifests" / "environment_lock.json"),
        "artifact_graph_sha256": stable_hash([(item["physical_path"], item["sha256"]) for item in artifacts]),
    }
    write_json(root / "manifests" / "INPUT_INDEX_FROZEN.json", marker)
    return {"artifact_count": len(artifacts), "candidate_count": len(candidates), **marker}
