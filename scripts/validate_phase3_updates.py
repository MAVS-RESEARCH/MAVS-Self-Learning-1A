"""Validate Phase 3 proposal, certification, promotion, rejection, and rollback chains."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from make_phase3_cards import ARTIFACT_SCHEMAS  # type: ignore[import-not-found] # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    root = REPO_ROOT / "results/reports" / run_id / "phase3_cards"
    manifest = json.loads((root / "card_manifest.json").read_text(encoding="utf-8"))
    records: dict[str, list[dict[str, Any]]] = {}
    for name, schema_name in ARTIFACT_SCHEMAS.items():
        path = root / f"{name}.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        records[name] = rows
        schema = json.loads((REPO_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for index, row in enumerate(rows):
            for error in validator.iter_errors(row):
                errors.append(f"schema:{name}:{index}:{error.message}")
        entry = manifest["artifacts"][name]
        if entry["records"] != len(rows) or entry["sha256"] != file_sha256(path):
            errors.append(f"manifest_mismatch:{name}")
    proposals = {item["candidate_id"]: item for item in records["proposals"]}
    candidates = {item["candidate_id"]: item for item in records["candidates"]}
    certificates = {item["candidate_id"]: item for item in records["certifications"]}
    promotions = {item["candidate_id"]: item for item in records["promotions"]}
    rollbacks = {item["config_id"]: item for item in records["rollbacks"]}
    rejected = {item["candidate_id"]: item for item in records["rejected_candidates"]}
    if not (set(certificates) == set(proposals) == set(candidates)):
        errors.append("proposal_candidate_certification_chain_incomplete")
    if set(promotions) & set(rejected):
        errors.append("candidate_both_promoted_and_rejected")
    if set(promotions) | set(rejected) != set(certificates):
        errors.append("candidate_terminal_update_decision_incomplete")
    for candidate_id, promotion in promotions.items():
        certificate = certificates[candidate_id]
        if not certificate["passed"] or certificate["harmful"] or not certificate["truly_beneficial"]:
            errors.append(f"invalid_promotion:{candidate_id}")
        if promotion["certification_hash"] != certificate["certification_hash"]:
            errors.append(f"promotion_certificate_hash_mismatch:{candidate_id}")
        if promotion["config_id"] not in rollbacks or not rollbacks[promotion["config_id"]]["passed"]:
            errors.append(f"promotion_without_verified_rollback:{candidate_id}")
        unsigned = dict(promotion)
        decision_hash = unsigned.pop("decision_hash")
        if stable_hash(unsigned) != decision_hash:
            errors.append(f"promotion_decision_hash_mismatch:{candidate_id}")
    for candidate_id, rejection in rejected.items():
        certificate = certificates[candidate_id]
        if certificate["passed"] or rejection["retained_for_audit"] is not True:
            errors.append(f"invalid_rejection:{candidate_id}")
        if rejection["harmful"] != certificate["harmful"]:
            errors.append(f"rejection_harm_label_mismatch:{candidate_id}")
    if any(item["harmful"] for item in certificates.values() if item["passed"]):
        errors.append("harmful_candidate_promoted")
    if len(promotions) != 60 or len(rollbacks) != 60 or len(rejected) != 60 or len(certificates) != 120:
        errors.append("phase3_update_card_count_mismatch")
    operation_counts = Counter((item["effective_generation"], item["condition"], proposals[item["candidate_id"]]["operation"]) for item in promotions.values())
    for generation in (1, 2, 3):
        for condition in ("cumulative", "fresh"):
            operations = {operation for (gen, cond, operation), count in operation_counts.items() if gen == generation and cond == condition and count == 1}
            if len(operations) != 10:
                errors.append(f"operation_promotion_coverage:{generation}:{condition}")
    if len(records["genealogies"]) != 6:
        errors.append("genealogy_report_count_mismatch")
    if any(not item["retained_replay_passed"] or not item["rollback_target"] for item in records["consolidations"]):
        errors.append("uncertified_consolidation")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.validate_updates.step01.start
    console_log("phase3.validate_updates.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase3.validate_updates.step02.complete
    console_log("phase3.validate_updates.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
