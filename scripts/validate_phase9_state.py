"""Validate every Phase 9 participant checkpoint against persistence rules and budgets."""

from __future__ import annotations

import argparse
import json

import jsonschema

from mavs10d.core.hashing import stable_hash
from mavs10d.revalidation.conditions import condition_registry
from phase9_common import REPO_ROOT, read_json, track_root, write_json


FORBIDDEN_TOKENS = {"unsafe", "correct_action", "minimum_separating_action", "query_response", "evaluator_truth", "final_metrics", "future_generation_manifest"}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--track", required=True); args = parser.parse_args()
    root = track_root(args.track); schema = read_json(REPO_ROOT / "schemas/v04/phase9_participant_state.schema.json"); findings = []
    for condition in condition_registry(args.track):
        checkpoints = []
        for generation in (1, 2, 3):
            path = root / f"checkpoints/generation_{generation}/{condition.id}.json"; item = read_json(path); checkpoints.append(item)
            try: jsonschema.validate(item, schema)
            except jsonschema.ValidationError as error: findings.append({"gate": "schema", "condition": condition.id, "generation": generation, "detail": error.message})
            serialized = json.dumps(item["state"], sort_keys=True).lower()
            leaked = sorted(token for token in FORBIDDEN_TOKENS if token in serialized)
            if leaked: findings.append({"gate": "hidden_taint", "condition": condition.id, "generation": generation, "tokens": leaked})
            if item["checkpoint_sha256"] != stable_hash(item["state"]): findings.append({"gate": "checkpoint_hash", "condition": condition.id, "generation": generation})
        if condition.state_rule == "fresh" and any(checkpoint["state_rule"] != "fresh" for checkpoint in checkpoints):
            findings.append({"gate": "fresh_reset_contract", "condition": condition.id})
        if condition.state_rule == "frozen_after_g1" and any(checkpoints[index]["checkpoint_sha256"] != checkpoints[0]["checkpoint_sha256"] for index in (1, 2)):
            findings.append({"gate": "frozen_after_g1", "condition": condition.id})
    report = {"schema_version": "1.0.0", "track_id": args.track, "checkpoint_count": len(condition_registry(args.track)) * 3, "findings": findings, "finding_count": len(findings), "status": "PASS" if not findings else "FAIL"}
    write_json(root / "integrity/participant_state_audit.json", report)
    if findings: raise RuntimeError(f"Phase 9 state audit failed with {len(findings)} findings.")
    # console.log: phase9.state.complete
    print(f'{{"event":"phase9.state.complete","track":"{args.track}","checkpoints":{report["checkpoint_count"]},"findings":0}}')


if __name__ == "__main__": main()
