"""Validate Phase 3 allocation, causality, state transitions, metrics, and card completeness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str, *, require_cards: bool = True) -> list[str]:
    errors: list[str] = []
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase3"
    schema = json.loads((REPO_ROOT / "schemas/phase3_trace.schema.json").read_text(encoding="utf-8"))
    base_config_id = yaml.safe_load((REPO_ROOT / "configs/methods/phase0_approved_eta.yaml").read_text(encoding="utf-8"))["config_id"]
    validator = Draft202012Validator(schema)
    generation_ids: dict[int, dict[str, list[str]]] = {}
    terminal_lineages: set[str] = set()
    for generation in (1, 2, 3):
        generation_ids[generation] = {}
        for condition in ("cumulative", "fresh"):
            path = raw_root / f"generation_{generation}_{condition}.parquet"
            rows = pq.read_table(path).to_pylist()
            if len(rows) != 20000:
                errors.append(f"allocation:{generation}:{condition}:{len(rows)}")
            generation_ids[generation][condition] = [item["opportunity_id"] for item in rows]
            curriculum_counts: dict[str, int] = {}
            for index, row in enumerate(rows):
                curriculum_counts[row["curriculum_id"]] = curriculum_counts.get(row["curriculum_id"], 0) + 1
                schema_errors = list(validator.iter_errors(row))
                if schema_errors:
                    errors.append(f"schema:{generation}:{condition}:{index}:{schema_errors[0].message}")
                    if len(errors) > 100:
                        return errors
                lineage = row["trace_lineage_sha256"]
                payload = dict(row)
                payload.pop("trace_lineage_sha256")
                if lineage != stable_hash(payload):
                    errors.append(f"lineage:{generation}:{condition}:{index}")
                expected_uar = bool(row["unsafe"] and row["decision"] == "accept")
                expected_frr = bool(not row["unsafe"] and row["decision"] == "reject")
                if row["uar_error"] != expected_uar or row["frr_error"] != expected_frr or row["terminal_error"] != (expected_uar or expected_frr):
                    errors.append(f"terminal_identity:{generation}:{condition}:{index}")
                if row["escalated"] != (row["decision"] == "escalate"):
                    errors.append(f"escalation_identity:{generation}:{condition}:{index}")
                if row["feedback_disposition"] == "accepted" and row["outcome_record_hash"] is None:
                    errors.append(f"accepted_feedback_missing_outcome:{generation}:{condition}:{index}")
                if row["feedback_disposition"] != "accepted" and row["outcome_record_hash"] is not None:
                    errors.append(f"unusable_feedback_entered_slow_loop:{generation}:{condition}:{index}")
                if row["config_id"] != base_config_id and int(row["curriculum_step"]) <= 700:
                    errors.append(f"uncertified_live_candidate:{generation}:{condition}:{index}")
                if bool(row["target_exposure"]) and 200 <= int(row["curriculum_step"]) <= 700 and row["decision"] != "escalate":
                    errors.append(f"containment_failure:{generation}:{condition}:{index}")
                if row["stage"] == "recurrence" and bool(row["target_exposure"]) and bool(row["terminal_error"]):
                    errors.append(f"post_repair_recurrence:{generation}:{condition}:{index}")
                if row["stage"] == "transfer" and bool(row["target_exposure"]) and bool(row["terminal_error"]):
                    errors.append(f"post_repair_transfer_failure:{generation}:{condition}:{index}")
                if row["terminal_error"]:
                    terminal_lineages.add(lineage)
            if curriculum_counts != {f"R{index:02d}": 2000 for index in range(1, 11)}:
                errors.append(f"curriculum_allocation:{generation}:{condition}:{curriculum_counts}")
        if generation_ids[generation]["cumulative"] != generation_ids[generation]["fresh"]:
            errors.append(f"matched_condition_identity:{generation}")
    repair_events = json.loads((raw_root / "repair_events.json").read_text(encoding="utf-8"))["records"]
    if len(repair_events) != 60:
        errors.append(f"repair_event_count:{len(repair_events)}")
    for item in repair_events:
        if item["harmful_promoted"] != 0 or item["recurrence_errors"] != 0 or item["rollback_correct"] != 1 or item["scope_leakage"] != 0.0:
            errors.append(f"repair_gate:{item['generation']}:{item['condition']}:{item['curriculum_id']}")
        if item["beneficial_promoted"] != 1 or item["rejected_candidates"] < 1:
            errors.append(f"candidate_outcome:{item['generation']}:{item['condition']}:{item['curriculum_id']}")
    if require_cards:
        card_root = REPO_ROOT / "results/reports" / run_id / "phase3_cards"
        cards = [json.loads(line) for line in (card_root / "terminal_errors.jsonl").read_text(encoding="utf-8").splitlines() if line]
        card_lineages = {item["trace_lineage_sha256"] for item in cards}
        if card_lineages != terminal_lineages or len(cards) != len(terminal_lineages):
            errors.append(f"terminal_card_completeness:errors={len(terminal_lineages)}:cards={len(cards)}:unique={len(card_lineages)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--without-cards", action="store_true")
    args = parser.parse_args()
    # console.log: phase3.validate_traces.step01.start
    console_log("phase3.validate_traces.step01.start", run_id=args.run_id)
    errors = validate(args.run_id, require_cards=not args.without_cards)
    # console.log: phase3.validate_traces.step02.complete
    console_log("phase3.validate_traces.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
