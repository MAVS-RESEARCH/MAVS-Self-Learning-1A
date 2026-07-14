"""Execute Phase 6 structure/parameter synthesis and integrity pre-screening."""

from __future__ import annotations

import argparse
from collections import defaultdict

import pandas as pd

from mavs10d.core.hashing import git_commit_hash, stable_hash
from mavs10d.certification.blind_api import make_blind_request
from mavs10d.diagnostics.ast import AST_VERSION, feature_registry_payload
from mavs10d.diagnostics.behavioral_fingerprint import behavioral_hash, fingerprint_frame
from mavs10d.diagnostics.semantic_hash import semantic_hash, semantic_payload
from mavs10d.integrity.template_collapse import duplicate_classes, integrity_reason
from mavs10d.learning.operation_constraints import check_operation
from mavs10d.learning.synthesis import build_bank, synthesize_candidates
from phase6_common import REPO_ROOT, bank_hashes, environment_lock, load_config, run_root, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    config = load_config("configs/phases/phase6.yaml")
    synthesis_config = load_config("configs/perception_closure_v04/synthesis.yaml")
    root.mkdir(parents=True, exist_ok=False)
    bank = build_bank(config["seeds"]["certification"], config["split_sizes"]["certification_per_bank"])
    development = build_bank(config["seeds"]["development"], config["split_sizes"]["development"])
    candidates = synthesize_candidates(development, config["seeds"]["synthesis"], config["seeds"]["development"])
    if len(candidates) != config["candidate_budget"]:
        raise RuntimeError("Candidate budget was not exhausted exactly.")
    (root / "banks").mkdir(parents=True)
    bank.to_parquet(root / "banks" / "certification_banks.parquet", index=False)
    development.to_parquet(root / "banks" / "development.parquet", index=False)
    fingerprints = {item.candidate.candidate_id: fingerprint_frame(item.candidate, bank) for item in candidates}
    suite_hashes = bank_hashes(bank)
    classes = duplicate_classes([item.candidate for item in candidates], fingerprints)
    semantic_members: dict[str, list[str]] = defaultdict(list)
    behavioral_members: dict[str, list[str]] = defaultdict(list)
    for item in candidates:
        semantic_members[semantic_hash(item.candidate)].append(item.candidate.candidate_id)
        behavioral_members[behavioral_hash(fingerprints[item.candidate.candidate_id])].append(item.candidate.candidate_id)
    state = []
    for item in candidates:
        candidate = item.candidate
        directory = root / "candidates" / candidate.candidate_id
        directory.mkdir(parents=True)
        candidate_payload = candidate.to_dict()
        write_json(directory / "candidate.json", candidate_payload)
        pd.DataFrame(item.structure_trace).to_parquet(directory / "structure_search.parquet", index=False)
        pd.DataFrame(item.parameter_trace).to_parquet(directory / "parameter_search.parquet", index=False)
        semantic_id = semantic_hash(candidate)
        write_json(directory / "semantic_identity.json", {"schema_version": "1.0.0", "candidate_id": candidate.candidate_id, "grammar_version": AST_VERSION, "semantic_hash": semantic_id, "normalized_payload": semantic_payload(candidate), "excluded_identity_fields": ["candidate_id", "candidate_name", "operation", "proposal_order", "expected_outcome", "curriculum", "generation"]})
        fingerprints[candidate.candidate_id].to_parquet(directory / "behavioral_fingerprint.parquet", index=False)
        compliance = check_operation(candidate_payload)
        write_json(directory / "operation_compliance.json", compliance)
        write_json(directory / "blind_request.json", make_blind_request(candidate, suite_hashes, stable_hash({"incumbent": "phase3-retained-kernel"})))
        reason = integrity_reason(candidate, semantic_members[semantic_id], behavioral_members[behavioral_hash(fingerprints[candidate.candidate_id])], fingerprints[candidate.candidate_id])
        state.append({"candidate_id": candidate.candidate_id, "expected_lifecycle": item.expected_lifecycle, "semantic_hash": semantic_id, "behavioral_hash": behavioral_hash(fingerprints[candidate.candidate_id]), "integrity_passed": reason is None and compliance["passed"], "integrity_reason": reason if reason else (None if compliance["passed"] else compliance["reason_code"])})
    write_json(root / "manifests" / "run_manifest.json", {"schema_version": "1.0.0", "run_id": args.run_id, "phase": 6, "code_commit": git_commit_hash(REPO_ROOT), "grammar_version": AST_VERSION, "candidate_budget": len(candidates), "feature_registry": feature_registry_payload(), "phase7_executed": False})
    write_json(root / "manifests" / "split_manifest.json", {"development": {"rows": len(development), "hash": stable_hash(development.to_dict(orient="records"))}, "certification_banks": {"rows": len(bank), "hashes": bank_hashes(bank)}, "final_blind": {"access": "prohibited", "rows_read": 0}})
    write_json(root / "manifests" / "seed_ledger.json", {"synthesis_process": config["seeds"]["synthesis"], "development": config["seeds"]["development"], "certification_process": config["seeds"]["certification"], "replay_process": config["seeds"]["replay"], "permutation": config["seeds"]["permutation"], "shared_mutable_rng": False})
    write_json(root / "manifests" / "environment_lock.json", environment_lock())
    write_json(root / "manifests" / "synthesis_state.json", state)
    write_json(root / "manifests" / "effective_synthesis_config.json", synthesis_config)
    write_json(root / "integrity" / "semantic_duplicate_classes.json", {"classes": classes["semantic_classes"]})
    write_json(root / "integrity" / "behavioral_equivalence_classes.json", {"classes": classes["behavioral_classes"]})
    write_json(root / "integrity" / "template_collapse_report.json", {"template_classes": classes["template_classes"], "template_count": classes["template_count"], "minimum_required": 5, "collapsed": classes["collapsed"], "passed": not classes["collapsed"]})
    # console.log: phase6.synthesis.complete
    print(f'{{"event":"phase6.synthesis.complete","candidates":{len(candidates)}}}')


if __name__ == "__main__":
    main()
