"""Candidate inventory, stratified lineage audit, and full proposal reconciliation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, read_json, result_root, verify_frozen_input_index, write_json
from .semantic import behavior_hash, name_invariant, semantic_hash, template_signature


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
        raw_unique = int(fingerprint["raw_output"].nunique(dropna=False))
        discrete_unique = int(fingerprint["discrete_output"].nunique(dropna=False))
        active_count = int(fingerprint["active"].astype(bool).sum())
        maximum_influence = float(fingerprint["terminal_influence"].abs().max())
        assignment_paths = [Path(path) for path in entry["phase9_assignment_artifacts"]]
        assignment_banks = {part for path in assignment_paths for part in path.parts if part in {"paired_original_bank", "blind_bank"}}
        assignment_generations = {part for path in assignment_paths for part in path.parts if part.startswith("generation_")}
        assignment_conditions = {path.stem for path in assignment_paths}
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
            "template_signature": template_signature(candidate["expression_ast"]),
            "name_invariant": name_invariant(candidate, "PERMUTED-NAME"),
            "operation_compliant": bool(operation.get("passed", operation.get("compliant", False))),
            "witness_valid": bool(witness["valid"]),
            "gate_pattern": "".join("1" if item["passed"] else "0" for _, item in sorted(gates["gates"].items())),
            "search_rows": len(pd.read_parquet(directory / "structure_search.parquet")) + len(pd.read_parquet(directory / "parameter_search.parquet")),
            "missing_file_count": len(missing),
            "runtime_descendant_count": len(entry["runtime_descendants"]),
            "phase9_assignment_count": len(entry["phase9_assignment_artifacts"]),
            "descendant_trace_count": len(entry["descendant_traces"]),
            "bank_coverage_count": len(assignment_banks),
            "generation_coverage_count": len(assignment_generations),
            "condition_coverage_count": len(assignment_conditions),
            "all_hashes_match": recomputed_semantic == identity["semantic_hash"] and recomputed_behavior == recorded["behavioral_hash"],
            "constant_output": raw_unique <= 1 or discrete_unique <= 1,
            "noop": active_count == 0 or maximum_influence == 0.0,
            "parent_identical": candidate.get("integrity_control") == "parent_identical",
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
    full["sibling_identity"] = full["semantic_class_size"] > 1
    full.to_parquet(root / "full_template_audit.parquet", index=False)
    lifecycle = Counter(frame["lifecycle"])
    proposed = len(frame)
    reconciliation = proposed == lifecycle["integrity_rejected"] + lifecycle["certification_rejected"] + lifecycle["quarantined"] + lifecycle["promoted"]
    p9 = REPO_ROOT / config()["inputs"]["phase9"]
    phase9_library_sets = [set(read_json(p9 / track / "candidate_cards" / "library_index.json")["candidate_ids"]) for track in ("paired_original_bank", "blind_bank")]
    promoted_ids = set(frame.loc[frame["lifecycle"] == "promoted", "candidate_id"])
    promoted = frame.loc[frame["lifecycle"] == "promoted"]
    expected_condition_coverage = int(promoted["condition_coverage_count"].max()) if len(promoted) else 0
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
        "spot_semantic_class_count": spot["semantic_hash"].nunique(),
        "spot_behavioral_class_count": spot["behavioral_hash"].nunique(),
        "spot_rejection_reasons": sorted(spot.loc[spot["lifecycle"] != "promoted", "lifecycle_reason"].unique().tolist()),
        "template_signature_count": frame["template_signature"].nunique(),
        "sibling_identity_count": int(full["sibling_identity"].sum()),
        "constant_output_count": int(frame["constant_output"].sum()),
        "noop_count": int(frame["noop"].sum()),
        "parent_identical_count": int(frame["parent_identical"].sum()),
        "name_only_count": int(frame["candidate_id"].str.endswith("-I").sum()),
        "lifecycle_counts": dict(lifecycle),
        "reconciliation_equation": "proposed = integrity_rejected + certification_rejected + quarantined + promoted",
        "reconciliation_passed": reconciliation,
        "all_required_files_present": bool((frame["missing_file_count"] == 0).all()),
        "all_semantic_behavioral_hashes_match": bool(frame["all_hashes_match"].all()),
        "all_names_invariant": bool(frame["name_invariant"].all()),
        "all_operations_compliant_when_integrity_passed": bool(frame.loc[frame["integrity_passed"], "operation_compliant"].all()),
        "all_promoted_have_valid_witnesses": bool(frame.loc[frame["lifecycle"] == "promoted", "witness_valid"].all()),
        "expected_phase9_condition_coverage": expected_condition_coverage,
        "all_promoted_cover_banks_generations_conditions": bool(
            (promoted["bank_coverage_count"] == 2).all()
            and (promoted["generation_coverage_count"] == 3).all()
            and (promoted["condition_coverage_count"] == expected_condition_coverage).all()
            and expected_condition_coverage > 0
            and (promoted["phase9_assignment_count"] > 0).all()
            and (promoted["descendant_trace_count"] > 0).all()
        ),
        "spot_covers_all_semantic_behavioral_classes": spot["semantic_hash"].nunique() == len(semantic_classes) and spot["behavioral_hash"].nunique() == len(behavioral_classes),
        "phase6_phase9_candidate_totals_reconcile": all(library == promoted_ids for library in phase9_library_sets),
        "all_forbidden_controls_rejected": bool(
            (~frame.loc[frame["constant_output"] | frame["noop"] | frame["parent_identical"] | frame["candidate_id"].str.endswith("-I"), "lifecycle"].eq("promoted")).all()
        ),
    }
    required = (
        reconciliation
        and proposed == index["candidate_count"]
        and len(spot) == 30
        and spot["operation"].nunique() == frame["operation"].nunique() == 10
        and summary["spot_covers_all_semantic_behavioral_classes"]
        and summary["spot_gate_pattern_count"] == summary["gate_pattern_count"]
        and set(summary["spot_rejection_reasons"]) == set(frame.loc[frame["lifecycle"] != "promoted", "lifecycle_reason"].unique())
        and summary["all_required_files_present"]
        and summary["all_semantic_behavioral_hashes_match"]
        and summary["all_names_invariant"]
        and summary["all_operations_compliant_when_integrity_passed"]
        and summary["all_promoted_have_valid_witnesses"]
        and summary["all_promoted_cover_banks_generations_conditions"]
        and summary["phase6_phase9_candidate_totals_reconcile"]
        and summary["all_forbidden_controls_rejected"]
        and summary["template_signature_count"] > 1
    )
    summary["status"] = "PASS" if required else "FAIL"
    write_json(root / "candidate_audit_summary.json", summary)
    return summary
