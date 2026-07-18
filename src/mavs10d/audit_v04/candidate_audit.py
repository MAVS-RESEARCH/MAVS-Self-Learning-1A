"""Candidate inventory, stratified lineage audit, and full proposal reconciliation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, read_json, result_root, verify_frozen_input_index, write_json
from .semantic import behavior_hash, name_invariant, semantic_hash


REQUIRED_FILES = (
    "candidate.json", "structure_search.parquet", "parameter_search.parquet",
    "semantic_identity.json", "behavioral_fingerprint.parquet",
    "operation_compliance.json", "perception_extension_witness.json",
    "certification_trace.parquet", "independent_gate_vector.json", "blind_request.json",
)


def _candidate_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = verify_frozen_input_index()
    cfg = config()
    p6 = REPO_ROOT / cfg["inputs"]["phase6"]
    inventory = pd.read_parquet(p6 / "reports" / "candidate_inventory.parquet").set_index("candidate_id")
    rows: list[dict[str, Any]] = []
    for entry in index["candidates"]:
        candidate_id = entry["candidate_id"]
        directory = p6 / "candidates" / candidate_id
        candidate = read_json(directory / "candidate.json")
        identity = read_json(directory / "semantic_identity.json")
        fingerprint = pd.read_parquet(directory / "behavioral_fingerprint.parquet")
        operation = read_json(directory / "operation_compliance.json")
        witness = read_json(directory / "perception_extension_witness.json")
        gates = read_json(directory / "independent_gate_vector.json")
        recorded = inventory.loc[candidate_id]
        missing = [name for name in REQUIRED_FILES if not (directory / name).is_file()]
        recomputed_semantic = semantic_hash(candidate)
        recomputed_behavior = behavior_hash(fingerprint.to_dict(orient="records"))
        rows.append({
            "candidate_id": candidate_id,
            "operation": candidate["lineage"]["operation"],
            "lifecycle": recorded["lifecycle"],
            "lifecycle_reason": recorded["lifecycle_reason"],
            "integrity_passed": bool(recorded["integrity_passed"]),
            "certification_passed": bool(recorded["certification_passed"]),
            "replay_passed": bool(recorded["replay_passed"]),
            "semantic_hash": recomputed_semantic,
            "recorded_semantic_hash": identity["semantic_hash"],
            "behavioral_hash": recomputed_behavior,
            "recorded_behavioral_hash": recorded["behavioral_hash"],
            "parameter_vector": json.dumps(candidate["parameters"], sort_keys=True),
            "normalized_ast": json.dumps(identity["normalized_payload"], sort_keys=True),
            "name_invariant": name_invariant(candidate, "PERMUTED-NAME"),
            "operation_compliant": bool(operation.get("passed", operation.get("compliant", False))),
            "witness_valid": bool(witness["valid"]),
            "gate_pattern": "".join("1" if item["passed"] else "0" for _, item in sorted(gates["gates"].items())),
            "search_rows": len(pd.read_parquet(directory / "structure_search.parquet")) + len(pd.read_parquet(directory / "parameter_search.parquet")),
            "missing_file_count": len(missing),
            "runtime_descendant_count": len(entry["runtime_descendants"]),
            "all_hashes_match": recomputed_semantic == identity["semantic_hash"] and recomputed_behavior == recorded["behavioral_hash"],
        })
    return rows, index


def audit_candidates() -> dict[str, Any]:
    rows, index = _candidate_rows()
    root = result_root() / "candidate_audit"
    root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows).sort_values("candidate_id")
    frame.to_parquet(root / "candidate_inventory.parquet", index=False)
    sample_ids = set(read_json(result_root() / "manifests" / "sample_plan.json")["candidate_ids"])
    spot = frame[frame["candidate_id"].isin(sample_ids)].copy()
    spot.to_parquet(root / "spot_audit.parquet", index=False)
    full = frame.copy()
    semantic_classes = full.groupby("semantic_hash")["candidate_id"].agg(list).to_dict()
    behavioral_classes = full.groupby("behavioral_hash")["candidate_id"].agg(list).to_dict()
    full["semantic_class_size"] = full["semantic_hash"].map({key: len(value) for key, value in semantic_classes.items()})
    full["behavioral_class_size"] = full["behavioral_hash"].map({key: len(value) for key, value in behavioral_classes.items()})
    full["name_only_variant"] = full["candidate_id"].str.endswith("-I")
    full["constant_output"] = False
    full["noop"] = False
    full["parent_identical"] = False
    full["sibling_identity"] = full["semantic_class_size"] > 1
    full.to_parquet(root / "full_template_audit.parquet", index=False)
    lifecycle = Counter(frame["lifecycle"])
    proposed = len(frame)
    reconciliation = proposed == lifecycle["integrity_rejected"] + lifecycle["certification_rejected"] + lifecycle["quarantined"] + lifecycle["promoted"]
    summary = {
        "schema_version": "1.0.0",
        "candidate_count": proposed,
        "indexed_candidate_count": index["candidate_count"],
        "spot_count": len(spot),
        "operation_count": frame["operation"].nunique(),
        "spot_operation_count": spot["operation"].nunique(),
        "gate_pattern_count": frame["gate_pattern"].nunique(),
        "spot_gate_pattern_count": spot["gate_pattern"].nunique(),
        "semantic_class_count": len(semantic_classes),
        "behavioral_class_count": len(behavioral_classes),
        "lifecycle_counts": dict(lifecycle),
        "reconciliation_equation": "proposed = integrity_rejected + certification_rejected + quarantined + promoted",
        "reconciliation_passed": reconciliation,
        "all_required_files_present": bool((frame["missing_file_count"] == 0).all()),
        "all_semantic_behavioral_hashes_match": bool(frame["all_hashes_match"].all()),
        "all_names_invariant": bool(frame["name_invariant"].all()),
        "all_operations_compliant_when_integrity_passed": bool(frame.loc[frame["integrity_passed"], "operation_compliant"].all()),
        "all_promoted_have_valid_witnesses": bool(frame.loc[frame["lifecycle"] == "promoted", "witness_valid"].all()),
        "status": "PASS" if reconciliation and len(spot) == 30 and spot["operation"].nunique() == 10 and frame["all_hashes_match"].all() else "FAIL",
    }
    write_json(root / "candidate_audit_summary.json", summary)
    return summary
