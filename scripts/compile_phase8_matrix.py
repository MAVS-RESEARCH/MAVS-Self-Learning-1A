"""Freeze the preregistered Phase 8 matrix and its two shared banks."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import jsonschema
import pandas as pd

from mavs10d.ablations.v04_registry import AblationRegistry, REFERENCE_DEFAULTS
from mavs10d.core.hashing import file_sha256, stable_hash
from phase8_common import (
    PHASE7_ROOT, REPO_ROOT, environment_lock, load_yaml, phase7_dependency,
    read_json, read_jsonl, run_root, write_frame, write_json, write_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    root.mkdir(parents=True, exist_ok=True)
    phase = load_yaml("configs/phases/phase8.yaml")
    dependency = phase7_dependency()
    registry = AblationRegistry.from_directory(REPO_ROOT / "configs" / "ablations" / "v04")
    definition_schema = read_json(REPO_ROOT / "schemas" / "v04" / "ablation_definition.schema.json")
    for definition in registry:
        jsonschema.validate(definition.serializable(), definition_schema)

    phase7_cases = read_jsonl(PHASE7_ROOT / "manifests" / "runtime_cases.jsonl")
    phase7_truth = pd.read_parquet(PHASE7_ROOT / "manifests" / "auditor_truth.parquet")
    phase7_manifest = read_json(PHASE7_ROOT / "manifests" / "microbenchmark_manifest.json")
    if stable_hash(phase7_cases) != phase7_manifest["case_bank_hash"] or len(phase7_cases) != int(phase["locked_banks"]["phase7_case_count"]):
        raise RuntimeError("The sealed Phase 7 case bank does not match its locked manifest.")
    write_jsonl(root / "banks" / "phase7_runtime_cases.jsonl", phase7_cases)
    write_frame(root / "banks" / "phase7_auditor_truth.parquet", phase7_truth)

    phase4_path = REPO_ROOT / phase["locked_banks"]["phase4_trace"]
    legacy = read_json(REPO_ROOT / "results" / "legacy" / "phase4_original" / "legacy_manifest.json")
    indexed = {item["path"]: item for item in legacy["files"]}
    relative_phase4 = phase4_path.relative_to(REPO_ROOT).as_posix()
    if relative_phase4 not in indexed or file_sha256(phase4_path) != indexed[relative_phase4]["sha256"]:
        raise RuntimeError("The Phase 4 source trace is not the immutable indexed original.")
    required_columns = [
        "point_id", "generation", "opportunity_id", "world_id", "world_seed", "domain", "reset_type",
        "action", "risk_score", "threshold", "unsafe", "escalated", "ledger_sha256", "trace_complete",
    ]
    phase4 = pd.read_parquet(phase4_path, columns=required_columns)
    phase4 = phase4[phase4["point_id"] == phase["locked_banks"]["phase4_point_id"]].sort_values(["world_id", "opportunity_id"], kind="stable").reset_index(drop=True)
    if len(phase4) != int(phase["locked_banks"]["phase4_decision_count"]) or phase4["world_id"].nunique() != int(phase["locked_banks"]["phase4_world_count"]):
        raise RuntimeError("The Phase 4 pre-rerun selector did not reproduce the preregistered 500-world bank.")
    if not bool(phase4["trace_complete"].all()) or phase4["ledger_sha256"].nunique() != 1:
        raise RuntimeError("The Phase 4 pre-rerun bank lacks complete single-ledger trace provenance.")
    public_columns = [column for column in phase4.columns if column != "unsafe"]
    write_frame(root / "banks" / "phase4_pre_rerun_public.parquet", phase4[public_columns])
    write_frame(root / "banks" / "phase4_pre_rerun_auditor_truth.parquet", phase4.rename(columns={"opportunity_id": "case_id"})[["case_id", "unsafe"]].rename(columns={"unsafe": "truth_unsafe"}))

    shared_bank_manifest = {
        "schema_version": "1.0.0",
        "locked": True,
        "phase7": {
            "case_count": len(phase7_cases),
            "case_bank_hash": phase7_manifest["case_bank_hash"],
            "truth_hash": phase7_manifest["auditor_truth_hash"],
            "source_root": PHASE7_ROOT.relative_to(REPO_ROOT).as_posix(),
        },
        "phase4_pre_rerun": {
            "world_count": int(phase4["world_id"].nunique()),
            "decision_count": len(phase4),
            "source_path": relative_phase4,
            "source_sha256": file_sha256(phase4_path),
            "legacy_manifest_sha256": file_sha256(REPO_ROOT / "results" / "legacy" / "phase4_original" / "legacy_manifest.json"),
            "ledger_sha256": str(phase4["ledger_sha256"].iloc[0]),
            "claim_status": "diagnostic_pre_rerun_not_phase9_blind_claim",
        },
        "phase9_blind_bank_accessed": False,
    }
    write_json(root / "manifests" / "shared_bank_manifest.json", shared_bank_manifest)
    write_json(root / "manifests" / "matrix_manifest.json", registry.manifest())
    write_json(root / "manifests" / "phase7_dependency.json", dependency)
    write_json(root / "manifests" / "environment_lock.json", environment_lock())
    write_json(root / "manifests" / "seed_ledger.json", phase["seeds"])
    write_json(root / "manifests" / "run_manifest.json", {
        "schema_version": "1.0.0",
        "run_id": args.run_id,
        "phase": 8,
        "source_commit": environment_lock()["git_commit"],
        "matrix_hash": registry.manifest()["matrix_hash"],
        "shared_bank_manifest": "manifests/shared_bank_manifest.json",
        "result_namespace": root.relative_to(REPO_ROOT).as_posix(),
    })

    declared = {key: float(value) for key, value in phase["matched_budget"].items()}
    for definition in registry:
        target = root / "ablation_results" / definition.id
        target.mkdir(parents=True, exist_ok=True)
        write_json(target / "full_config.json", {
            "schema_version": "1.0.0", "condition_id": definition.reference_id,
            "group": definition.group, "semantic_config": REFERENCE_DEFAULTS[definition.group],
        })
        write_json(target / "ablation_config.json", definition.serializable() | {"semantic_config": definition.full_config()})
        write_json(target / "config_diff.json", {
            "schema_version": "1.0.0", "condition_id": definition.id,
            "reference_id": definition.reference_id, "normalized_diff": definition.normalized_diff(),
            "diff_count": len(definition.normalized_diff()), "single_factor_valid": len(definition.normalized_diff()) == (0 if definition.id == definition.reference_id else 1),
        })
        shutil.copyfile(root / "manifests" / "shared_bank_manifest.json", target / "shared_bank_manifest.json")
        write_json(target / "seed_ledger.json", phase["seeds"] | {"condition_offset": list(registry.manifest()["condition_ids"]).index(definition.id)})
        write_json(target / "matched_budget.json", {
            "schema_version": "1.0.0", "condition_id": definition.id, "reference_id": definition.reference_id,
            "declared": declared, "consumed": {key: 0.0 for key in declared}, "unused": declared,
            "matched": True, "mismatch_fields": [],
        })
    # console.log: phase8.compile.complete
    print(f'{{"event":"phase8.compile.complete","conditions":{len(list(registry))},"phase7_cases":{len(phase7_cases)},"phase4_decisions":{len(phase4)}}}')


if __name__ == "__main__":
    main()
