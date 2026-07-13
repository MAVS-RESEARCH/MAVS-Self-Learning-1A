"""Create one schema-valid Phase 2 failure-card record per terminal error."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def make_cards(run_id: str) -> dict[str, object]:
    schema = json.loads((REPO_ROOT / "schemas/phase2_failure_card.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    output = REPO_ROOT / "results/reports" / run_id / "failure_cards"
    output.mkdir(parents=True, exist_ok=True)
    cards_path = output / "phase2_failure_cards.jsonl"
    cards: list[dict] = []
    counts = {"unsafe_acceptance": 0, "false_rejection": 0}
    for generation in (1, 2, 3):
        frame = pd.read_parquet(REPO_ROOT / "results/raw" / run_id / "phase2" / f"generation_{generation}.parquet")
        hidden_payload = json.loads((REPO_ROOT / "results/manifests" / run_id / "phase2" / f"generation_{generation}/hidden_outcomes.json").read_text(encoding="utf-8"))
        hidden = {row["opportunity_id"]: row for row in hidden_payload["outcomes"]}
        failures = frame[frame["uar_error"] | frame["frr_error"]]
        for row in failures.to_dict(orient="records"):
            failure_type = "unsafe_acceptance" if bool(row["uar_error"]) else "false_rejection"
            outcome = hidden[row["opportunity_id"]]
            card = {
                "card_id": f"p2-g{generation}-{row['method_name']}-{row['trace_lineage_sha256'][:16]}",
                "run_id": run_id,
                "generation": generation,
                "method_name": str(row["method_name"]),
                "world_id": str(row["world_id"]),
                "step": int(row["step"]),
                "opportunity_id": str(row["opportunity_id"]),
                "failure_type": failure_type,
                "expected_action": "reject_or_escalate" if bool(row["unsafe"]) else "accept_or_escalate",
                "actual_action": str(row["decision"]),
                "visible_evidence": {key: _jsonable(row[key]) for key in ("evidence_status", "correlation_presence", "harmful_correlation", "safe_consistency", "danger_witness", "safe_witness", "ambiguity", "provenance_concentration", "independence", "source_compromise")},
                "hidden_mechanism_after_reveal": {"scenario_class": outcome["scenario_class"], "composition_id": outcome["composition_id"], "corruption_families": outcome["corruption_families"], "hidden_mechanism_hash": outcome["hidden_mechanism_hash"]},
                "specialist_state_hash": outcome["specialist_manifest_hash"],
                "diagnostic_trace": {"hard_veto": bool(row["hard_veto"]), "raw_correlation_only": bool(row["raw_correlation_only"]), "bounded_mitigation": float(row["bounded_mitigation"]), "counterfactual_decision": str(row["counterfactual_decision"]), "counterfactual_fragility": bool(row["counterfactual_fragility"]), "drop_one_fragility": float(row["drop_one_fragility"])},
                "immediate_containment": "quarantine trace and escalate equivalent evidence state",
                "suspected_cause": "unsafe evidence was insufficiently contained" if failure_type == "unsafe_acceptance" else "safe opportunity was terminally rejected",
                "trace_lineage_sha256": str(row["trace_lineage_sha256"]),
            }
            card["card_sha256"] = stable_hash(card)
            errors = list(validator.iter_errors(card))
            if errors:
                raise ValueError(f"Invalid Phase 2 failure card: {errors[0].message}")
            cards.append(card)
            counts[failure_type] += 1
    cards_path.write_text("".join(json.dumps(card, sort_keys=True, separators=(",", ":")) + "\n" for card in cards), encoding="utf-8", newline="\n")
    report = {"schema_version": "1.0.0", "run_id": run_id, "cards": len(cards), "counts": counts, "unique_trace_lineages": len({card["trace_lineage_sha256"] for card in cards}), "cards_sha256": file_sha256(cards_path)}
    (output / "phase2_failure_card_manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def _jsonable(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase2.cards.step01.start
    console_log("phase2.cards.step01.start", run_id=args.run_id)
    report = make_cards(args.run_id)
    # console.log: phase2.cards.step02.complete
    console_log("phase2.cards.step02.complete", **report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
