"""Execute matched Phase 1 methods over frozen non-stationary ledgers."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase1_registry import ADAPTIVE_METHODS, build_phase1_method, expected_method_conditions  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.core.types import CandidateAction, Observation, StepResult  # noqa: E402
from mavs10d.training.phase1_proxy import predict_checkpoint  # noqa: E402


def run_phase1(run_id: str, output_root: Path | None = None) -> dict[str, object]:
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase1"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    selection = json.loads((manifest_root / "selected_configurations.json").read_text(encoding="utf-8"))
    checkpoint_path = REPO_ROOT / "artifacts/models/phase1_ctta/phase1_ctta_source.npz"
    output = output_root or (REPO_ROOT / "results/raw" / run_id / "phase1")
    output.mkdir(parents=True, exist_ok=True)
    cumulative_states: dict[str, dict] = {}
    generation_records = []
    for generation in (1, 2, 3):
        directory = manifest_root / f"generation_{generation}"
        visible_rows = pq.read_table(directory / "world_ledger.parquet").to_pylist()
        hidden_rows = json.loads((directory / "hidden_outcomes.json").read_text(encoding="utf-8"))["outcomes"]
        hidden_by_id = {row["opportunity_id"]: row for row in hidden_rows}
        model_features = np.asarray([[row[f"feature_{index}"] for index in range(8)] for row in visible_rows], dtype=float)
        model_risks = predict_checkpoint(checkpoint_path, model_features)
        model_by_id = {row["opportunity_id"]: float(risk) for row, risk in zip(visible_rows, model_risks)}
        release_by_world_step: dict[tuple[str, int], list[dict]] = defaultdict(list)
        for row in visible_rows:
            release_step = row["feedback_release_step"]
            outcome = hidden_by_id[row["opportunity_id"]]
            if release_step is not None:
                release_by_world_step[(row["world_id"], int(release_step))].append({
                    "opportunity_id": row["opportunity_id"],
                    "origin_step": int(row["step"]),
                    "release_step": int(release_step),
                    "observed_label": bool(outcome["observed_feedback_label"]),
                    "risk_score": float(row["risk_score"]),
                    "reliability": float(row["feedback_reliability"]),
                })
        traces: list[dict] = []
        checkpoints: dict[str, dict] = {}
        for method_name, condition in expected_method_conditions(generation):
            method = build_phase1_method(method_name, condition, selection["selected"][method_name])
            method.reset(generation * 1_000_000 + len(traces))
            if condition == "cumulative" and generation > 1:
                method.load_state_dict(cumulative_states[method_name])
            for row in visible_rows:
                outcome = hidden_by_id[row["opportunity_id"]]
                obs = _observation(row)
                candidate = _candidate(row, model_by_id[row["opportunity_id"]])
                decision = method.decide(obs, candidate)
                unsafe = bool(outcome["unsafe"])
                uar_error = unsafe and decision.decision == "accept"
                frr_error = (not unsafe) and decision.decision == "reject"
                escalated = decision.decision == "escalate"
                catastrophic = bool(outcome["catastrophic_if_accepted"]) and uar_error
                loss = float(uar_error) + 0.35 * float(frr_error) + 0.15 * float(escalated) + 0.0001 * method.latency_per_call_ms
                released = release_by_world_step[(row["world_id"], int(row["step"]))]
                result = StepResult(obs, -loss, uar_error, frr_error, int(row["step"]) == 99, {"released_feedback": released})
                method.update(obs, candidate, decision, result)
                resources = method.resources.to_dict(method.memory_bytes())
                traces.append({
                    "run_id": run_id,
                    "implementation_git_sha": run_manifest["implementation_git_sha"],
                    "generation": generation,
                    "method_name": method_name,
                    "condition": condition,
                    "opportunity_id": row["opportunity_id"],
                    "world_id": row["world_id"],
                    "domain": row["domain"],
                    "step": int(row["step"]),
                    "schedule_family": row["schedule_family"],
                    "shift_class": row["shift_class"],
                    "change_active": bool(row["change_active"]),
                    "recovery_active": bool(row["recovery_active"]),
                    "decision": decision.decision,
                    "risk_score": float(decision.risk_score),
                    "unsafe": unsafe,
                    "feedback_release_step": row["feedback_release_step"],
                    "feedback_observed_by_step": row["feedback_release_step"] is not None and int(row["feedback_release_step"]) <= int(row["step"]),
                    "uar_error": uar_error,
                    "frr_error": frr_error,
                    "escalated": escalated,
                    "catastrophic_error": catastrophic,
                    "intervention_loss": loss,
                    "oracle_loss": 0.0,
                    "released_feedback_count": len(released),
                    **resources,
                })
            state = method.state_dict()
            state["state_sha256"] = stable_hash(state)
            checkpoints[f"{method_name}:{condition}"] = state
            if condition == "cumulative" and method_name in ADAPTIVE_METHODS:
                cumulative_states[method_name] = state
        trace_path = output / f"generation_{generation}.parquet"
        pq.write_table(pa.Table.from_pylist(traces), trace_path, compression="zstd", use_dictionary=True, write_statistics=True)
        checkpoint_directory = REPO_ROOT / "results/checkpoints" / run_id / "phase1" / f"generation_{generation}"
        checkpoint_directory.mkdir(parents=True, exist_ok=True)
        checkpoint_path_out = checkpoint_directory / "adaptive_baselines.json"
        checkpoint_content = json.dumps({"generation": generation, "states": checkpoints}, indent=2, sort_keys=True) + "\n"
        checkpoint_path_out.write_text(checkpoint_content, encoding="utf-8", newline="\n")
        generation_records.append({"generation": generation, "trace_path": str(trace_path.relative_to(REPO_ROOT)) if output_root is None else str(trace_path), "trace_sha256": file_sha256(trace_path), "records": len(traces), "methods": len(expected_method_conditions(generation)), "checkpoint_sha256": file_sha256(checkpoint_path_out)})
    summary = {"schema_version": "1.0.0", "run_id": run_id, "implementation_git_sha": run_manifest["implementation_git_sha"], "canonical_opportunities": 45000, "generation_records": generation_records}
    if output_root is None:
        summary_path = output / "stress_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def _observation(row: dict) -> Observation:
    return Observation(
        episode_id=row["world_id"],
        t=int(row["step"]),
        visible_state={key: row[key] for key in ("entropy", "margin", "evidence_quality", "specialist_disagreement", "regime_id", "policy_version")},
        prompt=None,
        risk_context={"domain": row["domain"], "cost_preference": row["cost_preference"], "schedule_family": row["schedule_family"]},
        corruption_hint={"bounded_signal": row["corruption_hint"]},
    )


def _candidate(row: dict, model_risk: float) -> CandidateAction:
    return CandidateAction(
        action_type="phase1_candidate",
        content=f"visible opportunity {row['opportunity_id']}",
        confidence=float(row["confidence"]),
        specialist_outputs={"phase1_proxy": {"score": 1.0 - float(row["risk_score"])}},
        provenance={"risk_proxy": float(row["risk_score"]), "model_risk": model_risk, "source": "phase1_visible_ledger"},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    # console.log: phase1.stress.step01.start
    console_log("phase1.stress.step01.start", run_id=args.run_id)
    summary = run_phase1(args.run_id, args.output_root)
    # console.log: phase1.stress.step02.complete
    console_log("phase1.stress.step02.complete", canonical_opportunities=summary["canonical_opportunities"], generation_records=summary["generation_records"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
