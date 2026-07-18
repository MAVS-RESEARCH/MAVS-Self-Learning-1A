"""Compile, separate, preregister, and seal both Phase 9 banks before execution."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.revalidation.banks import blind_generation, hidden_fields, original_generation, public_identity
from mavs10d.revalidation.conditions import condition_manifest
from phase9_common import PHASE6_ROOT, PHASE7_ROOT, PHASE8_ROOT, PHASE9_ROOT, REPO_ROOT, dependency_lock, environment_lock, load_yaml, read_json, track_root, write_frame, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    phase = load_yaml("configs/phases/phase9.yaml")
    dependency = dependency_lock()
    legacy = read_json(REPO_ROOT / phase["banks"]["original_index"])
    indexed = {item["path"]: item["sha256"] for item in legacy["files"]}
    source_discrepancies: list[dict[str, object]] = []
    prior_identity = _prior_identity()
    blind_identity: list[dict[str, str]] = []
    for track_id in ("paired_original_bank", "blind_bank"):
        root = track_root(track_id)
        for directory in ("manifests", "checkpoints", "candidate_cards/library", "decision_traces", "ablation_results", "integrity", "summaries", "reports"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        write_json(root / "manifests/condition_registry.json", {"schema_version": "1.0.0", "track_id": track_id, "conditions": condition_manifest(track_id)})
        for generation in (1, 2, 3):
            bank = original_generation(generation) if track_id == "paired_original_bank" else blind_generation(generation, tuple(phase["banks"]["blind_seed_ranges"][generation]))
            manifest_dir = root / f"manifests/generation_{generation}"
            public_path = manifest_dir / "public_ledger.parquet"
            evaluator_dir = PHASE9_ROOT / f"evaluator_sealed/{track_id}/generation_{generation}"
            truth_path = evaluator_dir / "truth.parquet"
            write_frame(public_path, bank.public)
            write_frame(truth_path, bank.evaluator)
            evaluator_manifest = {
                "schema_version": "1.0.0", "track_id": track_id, "generation": generation,
                "truth_sha256": file_sha256(truth_path), "truth_fields": sorted(bank.evaluator.columns),
                "participant_access": False, "process_identity": f"phase9-{track_id}-evaluator",
            }
            evaluator_manifest["signature"] = stable_hash(evaluator_manifest)
            write_json(evaluator_dir / "evaluator_manifest.json", evaluator_manifest)
            body = {
                "schema_version": "1.0.0", "track_id": track_id, "generation": generation,
                "world_count": int(bank.public["world_id"].nunique()), "opportunity_count": int(len(bank.public)),
                "seed_min": int(bank.public["world_seed"].min()), "seed_max": int(bank.public["world_seed"].max()),
                "public_ledger_sha256": file_sha256(public_path), "public_fields": sorted(bank.public.columns),
                "evaluator_manifest_sha256": file_sha256(evaluator_dir / "evaluator_manifest.json"),
                "source_identity": bank.source_identity,
                "compiled_identity": public_identity(bank.public),
                "separation": {"forbidden_public_fields": sorted(hidden_fields()), "overlap": sorted(set(bank.public.columns) & hidden_fields()), "participant_final_access": False},
                "sealed_before_participant": True,
            }
            body["signature"] = stable_hash(body)
            write_json(manifest_dir / "generation_manifest.json", body)
            if body["separation"]["overlap"] or len(bank.public) != 15000 or bank.public["world_id"].nunique() != 300:
                raise RuntimeError(f"Invalid Phase 9 bank contract for {track_id} generation {generation}.")
            if track_id == "paired_original_bank":
                source_rel = bank.source_identity["public_source"]
                if indexed.get(source_rel) != bank.source_identity["public_sha256"]:
                    source_discrepancies.append({"generation": generation, "artifact": source_rel, "reason": "legacy_index_hash_mismatch"})
                for field in ("opportunity_ids_sha256", "world_sequence_sha256", "seed_sequence_sha256", "schedule_sha256", "public_content_sha256"):
                    if body["compiled_identity"][field] != bank.source_identity[field]:
                        source_discrepancies.append({"generation": generation, "artifact": field, "reason": "original_identity_mismatch"})
            else:
                blind_identity.extend(bank.evaluator[["raw_content_hash", "near_duplicate_signature"]].astype(str).to_dict(orient="records"))
        _copy_candidate_library(root)
        write_json(root / "integrity/environment.lock.json", environment_lock())
        write_json(root / "integrity/dependency_lock.json", dependency)
        write_json(root / "integrity/seed_ledger.json", {"schema_version": "1.0.0", "track_id": track_id, "ranges": phase["banks"]["blind_seed_ranges"] if track_id == "blind_bank" else {str(g): [930000 + 10000 * (g - 1), 930299 + 10000 * (g - 1)] for g in (1, 2, 3)}, "participant_namespace": f"phase9-{track_id}-participant"})
    overlaps = _overlap_report(prior_identity, blind_identity)
    write_json(PHASE9_ROOT / "blind_bank/integrity/preexecution_overlap_report.json", overlaps)
    write_json(PHASE9_ROOT / "paired_original_bank/integrity/original_bank_discrepancy_ledger.json", {
        "schema_version": "1.0.0", "checked_before_execution": True, "hash_discrepancies": source_discrepancies,
        "unavailable_original_artifacts": ["minimum_separating_action", "expected_separability"],
        "declared_extension": "Version 0.4 evaluator query contract derived before participant execution; original public ledgers are unchanged.",
        "silent_approximation": False, "passed": not source_discrepancies,
    })
    seal = {"schema_version": "1.0.0", "source_commit": args.source_commit, "dependency": dependency, "track_a_diagnostic_only": True, "track_b_provisional_until_phase10": True, "post_unseal_retuning": False, "participant_execution_started": False}
    seal["signature"] = stable_hash(seal)
    write_json(PHASE9_ROOT / "BANKS_SEALED.json", seal)
    if source_discrepancies or not overlaps["passed"]:
        raise RuntimeError("Phase 9 preexecution bank audit failed.")
    # console.log: phase9.compile.complete
    print('{"event":"phase9.compile.complete","tracks":2,"canonical_opportunities":90000,"banks_sealed":true}')


def _copy_candidate_library(root: Path) -> None:
    inventory = pd.read_parquet(PHASE6_ROOT / "reports/candidate_inventory.parquet")
    promoted = inventory.loc[inventory["lifecycle"] == "promoted", "candidate_id"].astype(str).tolist()
    for candidate_id in promoted:
        source = PHASE6_ROOT / "candidates" / candidate_id
        target = root / "candidate_cards/library" / candidate_id
        shutil.copytree(source, target, dirs_exist_ok=True)
    write_json(root / "candidate_cards/library_index.json", {"schema_version": "1.0.0", "source": PHASE6_ROOT.relative_to(REPO_ROOT).as_posix(), "candidate_ids": promoted, "candidate_count": len(promoted), "phase6_gate_continuity_required": True})


def _prior_identity() -> dict[str, set[str]]:
    exact: set[str] = set()
    near: set[str] = set()
    for path in [REPO_ROOT / "results/manifests/phase5_authoritative/phase5/generation_1/hidden_outcomes.json", REPO_ROOT / "results/manifests/phase5_authoritative/phase5/generation_2/hidden_outcomes.json", REPO_ROOT / "results/manifests/phase5_authoritative/phase5/generation_3/hidden_outcomes.json"]:
        rows = json.loads(path.read_text(encoding="utf-8"))["outcomes"]
        exact.update(str(row["raw_content_hash"]) for row in rows); near.update(str(row["near_duplicate_signature"]) for row in rows)
    for root in (PHASE6_ROOT, PHASE7_ROOT, PHASE8_ROOT):
        exact.add(stable_hash([root.relative_to(REPO_ROOT).as_posix()]))
    return {"exact": exact, "near": near}


def _overlap_report(prior: dict[str, set[str]], blind: list[dict[str, str]]) -> dict[str, object]:
    blind_exact = [item["raw_content_hash"] for item in blind]; blind_near = [item["near_duplicate_signature"] for item in blind]
    findings = {
        "prior_exact_overlap": len(set(blind_exact) & prior["exact"]), "prior_near_overlap": len(set(blind_near) & prior["near"]),
        "blind_exact_duplicates": len(blind_exact) - len(set(blind_exact)), "blind_near_duplicates": len(blind_near) - len(set(blind_near)),
    }
    return {"schema_version": "1.0.0", "checks": findings, "passed": all(value == 0 for value in findings.values())}


if __name__ == "__main__":
    main()
