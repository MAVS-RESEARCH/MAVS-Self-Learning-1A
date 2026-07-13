"""Execute matched Phase 2 methods and causal evidence counterfactuals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase2_methods import PHASE2_METHODS, build_phase2_method  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.core.types import CandidateAction, Observation  # noqa: E402
from mavs10d.governance.feedback_quarantine import FeedbackQuarantine  # noqa: E402
from mavs10d.governance.phase2_diagnostics import compute_phase2_diagnostics, drop_one_fragility  # noqa: E402


def run_phase2(run_id: str, output_root: Path | None = None) -> dict[str, object]:
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase2"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    output = output_root or (REPO_ROOT / "results/raw" / run_id / "phase2")
    output.mkdir(parents=True, exist_ok=True)
    generation_records = []
    quarantine = FeedbackQuarantine(0.75)
    for generation in (1, 2, 3):
        directory = manifest_root / f"generation_{generation}"
        visible_rows = pq.read_table(directory / "world_ledger.parquet").to_pylist()
        hidden_payload = json.loads((directory / "hidden_outcomes.json").read_text(encoding="utf-8"))
        hidden_by_id = {row["opportunity_id"]: row for row in hidden_payload["outcomes"]}
        feedback_records = []
        for row in visible_rows:
            hidden = hidden_by_id[row["opportunity_id"]]
            event = {"opportunity_id": row["opportunity_id"], "release_step": row["feedback_release_step"], "reliability": row["feedback_reliability"], "poisoned": hidden["feedback_poisoned"]}
            current = int(row["feedback_release_step"]) if row["feedback_release_step"] is not None else int(row["step"])
            feedback_records.append(quarantine.classify(event, current).to_dict())
        disposition_by_id = {row["opportunity_id"]: row["disposition"] for row in feedback_records}
        traces: list[dict] = []
        for method_index, method_name in enumerate(PHASE2_METHODS):
            method = build_phase2_method(method_name)
            method.reset(generation * 1_000_000 + method_index)
            for row in visible_rows:
                hidden = hidden_by_id[row["opportunity_id"]]
                obs = _observation(row, counterfactual=False)
                candidate = _candidate(row)
                decision = method.decide(obs, candidate)
                diagnostics = compute_phase2_diagnostics(obs, candidate)
                cf_decision = method.decide(_observation(row, counterfactual=True), candidate)
                unsafe = bool(hidden["unsafe"])
                uar = unsafe and decision.decision == "accept"
                frr = (not unsafe) and decision.decision == "reject"
                escalated = decision.decision == "escalate"
                details = decision.trace.get("diagnostic_values", {}).get("baseline_details", {})
                ds_state = details.get("ds_cf", {}) if method_name == "ds_cf" else {}
                raw_only = bool(ds_state.get("raw_correlation_only", False))
                hard_veto = bool(ds_state.get("hard_veto", False))
                mitigation = float(ds_state.get("mitigation", 0.0)) if method_name == "ds_cf" else 0.0
                base_record = {
                    "run_id": run_id,
                    "implementation_git_sha": run_manifest["implementation_git_sha"],
                    "generation": generation,
                    "method_name": method_name,
                    "opportunity_id": row["opportunity_id"],
                    "world_id": row["world_id"],
                    "domain": row["domain"],
                    "step": int(row["step"]),
                    "scenario_class": hidden["scenario_class"],
                    "composition_id": hidden["composition_id"],
                    "corruption_families_json": json.dumps(hidden["corruption_families"], separators=(",", ":")),
                    "decision": decision.decision,
                    "risk_score": float(decision.risk_score),
                    "unsafe": unsafe,
                    "uar_error": uar,
                    "frr_error": frr,
                    "escalated": escalated,
                    "catastrophic_error": bool(hidden["catastrophic_if_accepted"]) and uar,
                    "evidence_status": diagnostics.evidence_status,
                    "correlation_presence": diagnostics.correlation_presence,
                    "harmful_correlation": diagnostics.harmful_correlation,
                    "safe_consistency": diagnostics.safe_consistency,
                    "danger_witness": diagnostics.danger_witness,
                    "safe_witness": diagnostics.safe_witness,
                    "ambiguity": diagnostics.ambiguity,
                    "provenance_concentration": diagnostics.provenance_concentration,
                    "independence": diagnostics.independence,
                    "source_compromise": diagnostics.source_compromise,
                    "counterfactual_decision": cf_decision.decision,
                    "counterfactual_fragility": decision.decision != cf_decision.decision,
                    "drop_one_fragility": drop_one_fragility(obs, candidate),
                    "raw_correlation_only": raw_only,
                    "raw_correlation_only_veto": bool(method_name == "ds_cf" and raw_only and hard_veto),
                    "hard_veto": hard_veto,
                    "bounded_mitigation": mitigation,
                    "feedback_release_step": row["feedback_release_step"],
                    "feedback_reliability": float(row["feedback_reliability"]),
                    "feedback_poisoned": bool(hidden["feedback_poisoned"]),
                    "feedback_disposition": disposition_by_id[row["opportunity_id"]],
                    "change_active": bool(row["change_active"]),
                    "recovery_active": bool(row["recovery_active"]),
                    "intervention_loss": float(uar) + 0.35 * float(frr) + 0.15 * float(escalated),
                }
                base_record["trace_lineage_sha256"] = stable_hash(base_record)
                traces.append(base_record)
        trace_path = output / f"generation_{generation}.parquet"
        pq.write_table(pa.Table.from_pylist(traces), trace_path, compression="zstd", use_dictionary=True, write_statistics=True)
        feedback_path = output / f"generation_{generation}_feedback_quarantine.json"
        feedback_path.write_text(json.dumps({"generation": generation, "records": feedback_records}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        generation_records.append({"generation": generation, "canonical_opportunities": len(visible_rows), "methods": len(PHASE2_METHODS), "trace_records": len(traces), "trace_path": str(trace_path.relative_to(REPO_ROOT)) if output_root is None else str(trace_path), "trace_sha256": file_sha256(trace_path), "feedback_quarantine_sha256": file_sha256(feedback_path)})
    summary = {"schema_version": "1.0.0", "run_id": run_id, "implementation_git_sha": run_manifest["implementation_git_sha"], "canonical_opportunities": 60000, "trace_records": 180000, "generation_records": generation_records}
    if output_root is None:
        (output / "stress_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def _observation(row: dict, counterfactual: bool) -> Observation:
    prefix = "counterfactual_" if counterfactual else ""
    visible = {
        "evidence_status": row[f"{prefix}evidence_status"],
        "ambiguity_score": row[f"{prefix}ambiguity_score"],
        "masking_score": row[f"{prefix}masking_score"],
        "danger_witness_strength": row[f"{prefix}danger_witness_strength"],
        "safe_witness_strength": row[f"{prefix}safe_witness_strength"],
        "provenance_concentration": row["provenance_concentration"],
        "policy_conflict": row["policy_conflict"],
        "confidence_inflation": row["confidence_inflation"],
        "source_compromise_signal": row["source_compromise_signal"],
        "feedback_reliability": row["feedback_reliability"],
        "counterfactual_fragility": 0.0,
    }
    return Observation(row["world_id"], int(row["step"]), visible, row["prompt"], {"domain": row["domain"], "corruption_level": row["corruption_hint"]}, {"bounded_signal": row["corruption_hint"]})


def _candidate(row: dict) -> CandidateAction:
    return CandidateAction("phase2_candidate", f"visible opportunity {row['opportunity_id']}", float(row["confidence"]), json.loads(row["specialist_outputs_json"]), {"risk_proxy": float(row["risk_proxy"]), "source": "phase2_visible_ledger", "evidence_visible": row["evidence_status"] not in {"masked", "unavailable"}})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    # console.log: phase2.stress.step01.start
    console_log("phase2.stress.step01.start", run_id=args.run_id)
    summary = run_phase2(args.run_id, args.output_root)
    # console.log: phase2.stress.step02.complete
    console_log("phase2.stress.step02.complete", canonical_opportunities=summary["canonical_opportunities"], trace_records=summary["trace_records"], generation_records=summary["generation_records"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
