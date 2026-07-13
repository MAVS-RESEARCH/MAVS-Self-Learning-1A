"""Materialize and schema-validate all Phase 3 human-readable evidence cards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


ARTIFACT_SCHEMAS = {
    "learning_events": "phase3_learning_event.schema.json",
    "investigations": "phase3_investigation_card.schema.json",
    "proposals": "phase3_proposal_card.schema.json",
    "candidates": "phase3_candidate_configuration.schema.json",
    "certifications": "phase3_certification_card.schema.json",
    "promotions": "phase3_promotion_card.schema.json",
    "rollbacks": "phase3_rollback_card.schema.json",
    "genealogies": "phase3_genealogy_report.schema.json",
    "rejected_candidates": "phase3_rejected_candidate.schema.json",
    "consolidations": "phase3_consolidation_card.schema.json",
    "failure_capsules": "phase3_failure_capsule.schema.json",
    "uncertainty_entries": "phase3_uncertainty_entry.schema.json",
    "terminal_errors": "phase3_terminal_error_card.schema.json",
}


def make_cards(run_id: str) -> dict[str, Any]:
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase3"
    report_root = REPO_ROOT / "results/reports" / run_id / "phase3_cards"
    report_root.mkdir(parents=True, exist_ok=True)
    artifacts = json.loads((raw_root / "learning_artifacts.json").read_text(encoding="utf-8"))
    records: dict[str, list[dict[str, Any]]] = {name: list(artifacts.get(name, [])) for name in ARTIFACT_SCHEMAS}
    records["failure_capsules"] = _checkpoint_records(run_id, "failure_capsules.parquet", _capsule_record)
    records["uncertainty_entries"] = _checkpoint_records(run_id, "uncertainty_ledger.parquet", _uncertainty_record)
    records["terminal_errors"] = _terminal_error_cards(run_id)
    manifest: dict[str, Any] = {"schema_version": "1.0.0", "run_id": run_id, "artifacts": {}}
    for name, schema_name in ARTIFACT_SCHEMAS.items():
        schema = json.loads((REPO_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        errors = [f"{name}[{index}]:{error.message}" for index, record in enumerate(records[name]) for error in validator.iter_errors(record)]
        if errors:
            raise ValueError("Phase 3 card schema failure: " + "; ".join(errors[:10]))
        path = report_root / f"{name}.jsonl"
        content = "".join(json.dumps(record, sort_keys=True, separators=(",", ":"), default=str) + "\n" for record in records[name])
        path.write_text(content, encoding="utf-8", newline="\n")
        manifest["artifacts"][name] = {
            "schema": schema_name,
            "records": len(records[name]),
            "sha256": file_sha256(path),
            "path": str(path.relative_to(REPO_ROOT)),
        }
    manifest["terminal_error_lineages"] = len({item["trace_lineage_sha256"] for item in records["terminal_errors"]})
    manifest["promoted_candidates"] = len({item["candidate_id"] for item in records["promotions"]})
    manifest["rollback_configurations"] = len({item["config_id"] for item in records["rollbacks"]})
    manifest["manifest_hash"] = stable_hash(manifest)
    (report_root / "card_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def _checkpoint_records(run_id: str, filename: str, transform: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    root = REPO_ROOT / "results/checkpoints" / run_id / "phase3"
    for path in sorted(root.glob(f"generation_*/*/{filename}")):
        for row in pd.read_parquet(path).to_dict(orient="records"):
            if row.get("empty") is True:
                continue
            records.append(transform(row))
    return records


def _capsule_record(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("trace_ids", "context", "observable_signature", "minimal_contrasts", "attribution"):
        row[key] = json.loads(row[key])
    row["capsule_hash"] = stable_hash(row)
    return row


def _uncertainty_record(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("trace_ids", "reason_codes", "missing_evidence"):
        row[key] = json.loads(row[key])
    row["entry_hash"] = stable_hash(row)
    return row


def _terminal_error_cards(run_id: str) -> list[dict[str, Any]]:
    hidden_by_generation: dict[int, dict[str, dict[str, Any]]] = {}
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase3"
    for generation in (1, 2, 3):
        outcomes = json.loads((manifest_root / f"generation_{generation}/hidden_outcomes.json").read_text(encoding="utf-8"))["outcomes"]
        hidden_by_generation[generation] = {item["opportunity_id"]: item for item in outcomes}
    cards: list[dict[str, Any]] = []
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase3"
    for path in sorted(raw_root.glob("generation_*_*.parquet")):
        frame = pd.read_parquet(path)
        for row in frame[frame["terminal_error"]].to_dict(orient="records"):
            hidden = hidden_by_generation[int(row["generation"])][row["opportunity_id"]]
            card = {
                "card_id": f"phase3-error-{stable_hash({'lineage': row['trace_lineage_sha256']})[:24]}",
                "run_id": run_id,
                "generation": int(row["generation"]),
                "condition": row["condition"],
                "curriculum_id": row["curriculum_id"],
                "world_id": row["world_id"],
                "opportunity_id": row["opportunity_id"],
                "curriculum_step": int(row["curriculum_step"]),
                "expected_action": "reject" if bool(row["unsafe"]) else "accept",
                "actual_action": row["decision"],
                "error_type": "unsafe_acceptance" if bool(row["uar_error"]) else "false_rejection",
                "visible_evidence": json.loads(row["visible_features_json"]),
                "hidden_mechanism_after_reveal": hidden["hidden_repair_mechanism"],
                "specialist_state": json.loads(row["specialist_outputs_json"]),
                "diagnostic_trace": json.loads(row["meta_diagnostics_json"]),
                "immediate_containment": "certified_fallback_escalation_after_reliable_trigger",
                "suspected_cause": hidden["intervention_class"],
                "trace_lineage_sha256": row["trace_lineage_sha256"],
            }
            card["card_hash"] = stable_hash(card)
            cards.append(card)
    return cards


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.cards.step01.start
    console_log("phase3.cards.step01.start", run_id=args.run_id)
    manifest = make_cards(args.run_id)
    # console.log: phase3.cards.step02.complete
    console_log("phase3.cards.step02.complete", run_id=args.run_id, artifacts=manifest["artifacts"], manifest_hash=manifest["manifest_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
