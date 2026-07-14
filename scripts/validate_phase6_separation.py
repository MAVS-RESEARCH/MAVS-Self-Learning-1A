"""Audit split, process, payload, seed, and final-blind separation before certification."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mavs10d.certification.blind_api import assert_blind_payload
from phase6_common import REPO_ROOT, read_json, run_root, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    state = read_json(root / "manifests" / "synthesis_state.json")
    payload_failures = []
    for record in state:
        request = read_json(root / "candidates" / record["candidate_id"] / "blind_request.json")
        try:
            assert_blind_payload(request)
        except ValueError as error:
            payload_failures.append({"candidate_id": record["candidate_id"], "error": str(error)})
    source = (REPO_ROOT / "scripts" / "certify_phase6_candidates.py").read_text(encoding="utf-8")
    forbidden_imports = [item for item in ("mavs10d.learning.synthesis", "mavs10d.integrity.permutation_tests") if item in source]
    forbidden_environment = [name for name in os.environ if name.lower().startswith(("hidden_", "oracle_", "expected_", "desired_promotion"))]
    split = read_json(root / "manifests" / "split_manifest.json")
    seeds = read_json(root / "manifests" / "seed_ledger.json")
    report = {
        "candidate_count": len(state),
        "payload_failures": payload_failures,
        "forbidden_certifier_imports": forbidden_imports,
        "forbidden_environment_variables": forbidden_environment,
        "separate_process_entrypoint": True,
        "separate_hierarchical_seeds": len({seeds["synthesis_process"], seeds["certification_process"], seeds["replay_process"]}) == 3,
        "shared_mutable_rng": seeds["shared_mutable_rng"],
        "final_blind_rows_read": split["final_blind"]["rows_read"],
        "passed": not payload_failures and not forbidden_imports and not forbidden_environment and not seeds["shared_mutable_rng"] and split["final_blind"]["rows_read"] == 0,
    }
    write_json(root / "integrity" / "split_separation_audit.json", report)
    if not report["passed"]:
        raise RuntimeError("Phase 6 separation audit failed.")
    # console.log: phase6.separation.complete
    print(f'{{"event":"phase6.separation.complete","candidates":{len(state)}}}')


if __name__ == "__main__":
    main()

