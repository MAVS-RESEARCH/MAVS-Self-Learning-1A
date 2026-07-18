"""Freeze every Phase 6-9 artifact and candidate linkage before audit analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .common import (
    REPO_ROOT,
    SCHEMA_VERSION,
    all_files,
    artifact_role,
    assert_clean_source_tree,
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
        detected_schema = SCHEMA_VERSION
        if path.suffix.lower() == ".json" and path.stat().st_size < 20_000_000:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    detected_schema = str(payload.get("schema_version", SCHEMA_VERSION))
            except (json.JSONDecodeError, UnicodeDecodeError):
                detected_schema = "opaque-json"
        artifacts.append({
            "logical_role": artifact_role(path),
            "physical_path": relative(path),
            "byte_size": path.stat().st_size,
            "sha256": file_sha256(path),
            "schema_version": detected_schema,
            "git_object_id": git_blob_oid(path),
            "lfs_object_id": lfs_oid(path),
            "claim_eligibility": "diagnostic_only" if phase in {"phase6", "phase7", "phase8"} or "paired_original_bank" in relative(path) else "phase10_gate_dependent",
            "legacy_current_status": "current_v04",
            "phase": int(phase.removeprefix("phase")),
        })
    phase_bindings: dict[int, dict[str, Any]] = {}
    for phase_number in (6, 7, 8, 9):
        phase_artifacts = [item for item in artifacts if item["phase"] == phase_number]
        source_commits: set[str] = set()
        for item in phase_artifacts:
            item_path = Path(item["physical_path"])
            name = item_path.name.lower()
            if item_path.suffix.lower() == ".json" and ("manifest" in name or "audit" in name or item_path.parent.name.lower() == "manifests"):
                try:
                    payload = json.loads((REPO_ROOT / item["physical_path"]).read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        for key in ("source_commit", "code_commit", "git_commit", "code_sha"):
                            if isinstance(payload.get(key), str) and len(payload[key]) >= 7:
                                source_commits.add(payload[key])
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        configs = [(item["physical_path"], item["sha256"]) for item in phase_artifacts if any(token in Path(item["physical_path"]).name.lower() for token in ("config", "registry"))]
        governing_configs = [REPO_ROOT / "configs" / "phases" / f"phase{phase_number}.yaml"]
        if phase_number == 6:
            governing_configs.append(REPO_ROOT / "configs" / "perception_closure_v04" / "synthesis.yaml")
        elif phase_number == 7:
            governing_configs.extend(REPO_ROOT / "configs" / "perception_closure_v04" / name for name in ("runtime.yaml", "phase7_microbenchmarks.yaml"))
        elif phase_number == 8:
            governing_configs.extend(path for prefix in ("I", "P", "L") for path in sorted((REPO_ROOT / "configs" / "ablations").glob(f"{prefix}*.yaml")))
        elif phase_number == 9:
            governing_configs.extend(sorted((REPO_ROOT / "configs" / "perception_closure_v04" / "phase9").glob("*.yaml")))
        configs.extend((relative(path), file_sha256(path)) for path in governing_configs if path.is_file())
        configs = sorted(set(configs))
        seeds = [(item["physical_path"], item["sha256"]) for item in phase_artifacts if "seed" in Path(item["physical_path"]).name.lower()]
        environments = [(item["physical_path"], item["sha256"]) for item in phase_artifacts if "environment" in Path(item["physical_path"]).name.lower()]
        generators = [(item["physical_path"], item["sha256"]) for item in phase_artifacts if "generator" in Path(item["physical_path"]).name.lower()]
        manifests = [(item["physical_path"], item["sha256"]) for item in phase_artifacts if "manifest" in Path(item["physical_path"]).name.lower() or "audit" in Path(item["physical_path"]).name.lower() or Path(item["physical_path"]).parent.name.lower() == "manifests"]
        binding_payload = {
            "code_commits": sorted(source_commits),
            "config_artifacts": [{"physical_path": path, "sha256": digest} for path, digest in configs],
            "config_bindings_sha256": stable_hash(configs),
            "config_artifact_count": len(configs),
            "seed_artifacts": [{"physical_path": path, "sha256": digest} for path, digest in seeds],
            "seed_bindings_sha256": stable_hash(seeds),
            "seed_artifact_count": len(seeds),
            "environment_artifacts": [{"physical_path": path, "sha256": digest} for path, digest in environments],
            "environment_bindings_sha256": stable_hash(environments),
            "environment_artifact_count": len(environments),
            "generator_artifacts": [{"physical_path": path, "sha256": digest} for path, digest in (generators or manifests)],
            "generator_bindings_sha256": stable_hash({"code_commits": sorted(source_commits), "artifacts": generators or manifests}),
            "generator_artifact_count": len(generators or manifests),
            "data_artifact_graph_sha256": stable_hash([(item["physical_path"], item["sha256"]) for item in phase_artifacts]),
            "data_artifact_count": len(phase_artifacts),
        }
        phase_bindings[phase_number] = binding_payload | {"binding_record_sha256": stable_hash(binding_payload)}
    for item in artifacts:
        binding = phase_bindings[item["phase"]]
        item["bindings"] = {
            "phase_binding_record_sha256": binding["binding_record_sha256"],
            "code_commits": binding["code_commits"],
            "config_bindings_sha256": binding["config_bindings_sha256"],
            "seed_bindings_sha256": binding["seed_bindings_sha256"],
            "environment_bindings_sha256": binding["environment_bindings_sha256"],
            "generator_bindings_sha256": binding["generator_bindings_sha256"],
            "data_sha256": item["sha256"],
        }
    p6 = roots["phase6"]
    candidates: list[dict[str, Any]] = []
    for directory in sorted((p6 / "candidates").iterdir()):
        if not directory.is_dir():
            continue
        candidate = __import__("json").loads((directory / "candidate.json").read_text(encoding="utf-8"))
        lifecycle = __import__("json").loads((p6 / "manifests" / "lifecycle_state.json").read_text(encoding="utf-8"))
        lifecycle_rows = lifecycle if isinstance(lifecycle, list) else lifecycle.get("candidates", [])
        lifecycle_by_id = {item["candidate_id"]: item for item in lifecycle_rows}
        lifecycle_record = lifecycle_by_id.get(candidate["candidate_id"], {})
        promoted = lifecycle_record.get("lifecycle") == "promoted"
        phase9_assignments = sorted(path for path in roots["phase9"].glob("*_bank/candidate_cards/assignments/generation_*/*.json")) if promoted else []
        phase9_traces = sorted(path for path in roots["phase9"].glob("*_bank/decision_traces/*/generation_*.parquet")) if promoted else []
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
            "lifecycle": lifecycle_record,
            "promotion_rejection_quarantine": lifecycle_record.get("lifecycle"),
            "rollback_target": candidate["lineage"].get("rollback_target"),
            "runtime_use": {
                "phase7_trace_root": relative(roots["phase7"] / "traces") if promoted else None,
                "phase9_library_member": promoted,
                "phase9_assignment_count": len(phase9_assignments),
            },
            "consolidation_retirement_state": {
                "operation": candidate["lineage"]["operation"],
                "lifecycle": lifecycle_record.get("lifecycle"),
                "retirement_candidate": candidate["lineage"]["operation"] == "retire",
            },
            "runtime_descendants": [relative(path) for path in sorted((roots["phase7"] / "programs").glob("*.json")) if candidate["candidate_id"] in path.read_text(encoding="utf-8", errors="ignore")],
            "phase9_assignment_artifacts": [relative(path) for path in phase9_assignments],
            "descendant_traces": [relative(path) for path in phase9_traces],
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
        "phase_bindings": phase_bindings,
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
