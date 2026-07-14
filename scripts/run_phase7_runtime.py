"""Execute Phase 7 without loading auditor-only outcome fields."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from mavs10d.certification.persistent import certify_persistent_handoff
from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import PerceptionClosureRuntime
from mavs10d.learning.consolidation import consolidate_knowledge
from phase7_common import PHASE6_ROOT, load_yaml, read_json, read_jsonl, run_root, write_json


def parquet_safe(records: list[dict[str, Any]]) -> pd.DataFrame:
    normalized: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {}
        for key, value in record.items():
            row[key] = json.dumps(value, sort_keys=True, separators=(",", ":")) if isinstance(value, (dict, list, tuple)) else value
        normalized.append(row)
    return pd.DataFrame(normalized)


def write_frame(path: Path, records: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = parquet_safe(records)
    if frame.empty and columns:
        frame = pd.DataFrame(columns=columns)
    frame.to_parquet(path, index=False, compression="zstd")


def phase6_blind_material() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = PHASE6_ROOT / "candidates" / "P6-EVIDENCE-RECOVERY-A"
    return read_json(candidate / "blind_request.json"), read_json(candidate / "independent_gate_vector.json")


def build_persistence(results: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    successful: dict[str, list[Any]] = defaultdict(list)
    for result in results:
        if result.library_size == 20000 and result.trace["terminal_action"] in {"ACCEPT", "REJECT"} and result.trace["resolver_entered"]:
            signature = result.programs[0]["primary_causal_family"] if result.programs else result.queries_and_probes[-1]["target_contrast"].split(":", 1)[0]
            successful[signature].append(result)
    blind_request, gate_vector = phase6_blind_material()
    candidates: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for signature, grouped in sorted(successful.items()):
        if len(grouped) < 2:
            continue
        repeated = {
            "path_signature": signature,
            "replay_count": len(grouped),
            "protected_regression": 0.0,
            "scope_leakage": 0.0,
        }
        exact_phase6_reuse = signature == "masked_safe_evidence"
        certification = certify_persistent_handoff(blind_request, gate_vector, repeated) if exact_phase6_reuse else {
            "passed": False,
            "anonymous_semantic_id": "",
            "gate_count": 0,
            "reason": "local_path_not_yet_candidate_specifically_certified_by_phase6_blind_layer",
        }
        candidate_id = f"PK-{stable_hash({'signature': signature, 'cases': sorted(item.case_id for item in grouped)})[:20]}"
        candidate = {
            "candidate_id": candidate_id,
            "path_signature": signature,
            "case_ids": sorted(item.case_id for item in grouped),
            "replay_count": len(grouped),
            "blind_certification": certification,
            "candidate_specific_semantic_match": exact_phase6_reuse,
            "executable_semantic_id": blind_request["anonymous_semantic_id"] if exact_phase6_reuse else None,
            "local_success_grants_global_authority": False,
        }
        candidates.append(candidate)
        knowledge = consolidate_knowledge(
            candidate_id,
            candidate["case_ids"],
            {
                "kind": "query_policy" if all(not item.programs for item in grouped) else "closure_program",
                "semantic_distinction": signature,
                "positive_scope": [signature],
                "anti_scope": [f"not-{signature}"],
                "conditional_perception_gain": sum(sum(record["realized_contraction"] for record in item.queries_and_probes) for item in grouped) / len(grouped),
                "outperforms_parent": exact_phase6_reuse,
                "protected_regression": 0.0,
                "scope_leakage": 0.0,
                "shifted_prior": True,
            },
            certification,
            active_eligibility_count=0,
            active_cap=4,
        )
        actions.append(knowledge)
    return candidates, actions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    phase = load_yaml("configs/phases/phase7.yaml")
    runtime = PerceptionClosureRuntime(load_yaml("configs/perception_closure_v04/runtime.yaml"))
    cases = read_jsonl(root / "manifests" / "runtime_cases.jsonl")
    library_sizes = list(map(int, phase["microbenchmark"]["library_size_sweep"]))
    results = [runtime.resolve(case, library_size) for library_size in library_sizes for case in cases]

    rounds = [dict(record, library_size=result.library_size) for result in results for record in result.rounds]
    terminals = [dict(result.terminal_record, library_size=result.library_size) for result in results]
    queries = [dict(record, library_size=result.library_size) for result in results for record in result.queries_and_probes]
    escalations = [dict(result.escalation, library_size=result.library_size) for result in results if result.escalation]
    write_frame(root / "traces" / "perception_rounds.parquet", rounds)
    write_frame(root / "traces" / "terminal_decisions.parquet", terminals)
    write_frame(root / "traces" / "queries_and_probes.parquet", queries)
    write_frame(root / "traces" / "escalations.parquet", escalations)
    write_frame(root / "traces" / "perception_traces.parquet", [result.trace for result in results])
    closure_attempts = []
    for result in results:
        if not result.trace["resolver_entered"]:
            continue
        initial = result.initial_ambiguity_state
        if initial and initial["safe_count"] > 0 and initial["unsafe_count"] > 0:
            closure_attempts.append({"case_id": result.case_id, "library_size": result.library_size, "round_index": 0, "state_hash": initial["state_hash"], "passed": False, "reason": "hypothesis_not_terminally_homogeneous"})
        for record in result.rounds:
            if int(record["safe_count"]) > 0 and int(record["unsafe_count"]) > 0:
                closure_attempts.append({"case_id": result.case_id, "library_size": result.library_size, "round_index": int(record["round_index"]), "state_hash": record["after_state_hash"], "passed": False, "reason": "hypothesis_not_terminally_homogeneous"})
    write_frame(root / "traces" / "closure_attempts.parquet", closure_attempts)

    written_programs: set[str] = set()
    for result in results:
        for program in result.programs:
            if program["program_id"] not in written_programs:
                write_json(root / "programs" / f"{program['program_id']}.json", program)
                written_programs.add(program["program_id"])
        if result.hypotheses and not (root / "hypotheses" / f"{result.case_id}.json").exists():
            write_json(root / "hypotheses" / f"{result.case_id}.json", {"case_id": result.case_id, "initial_ambiguity_state": result.initial_ambiguity_state, "hypotheses": result.hypotheses})
        if result.certificate:
            write_json(root / "certificates" / "local" / f"{result.certificate['certificate_id']}.json", result.certificate)

    promotion_candidates, consolidation_actions = build_persistence(results)
    negative_records = []
    for result in results:
        if result.library_size == 20000:
            negative_records.extend(dict(record, case_id=result.case_id) for record in result.negative_knowledge)
    write_frame(root / "persistence" / "promotion_candidates.parquet", promotion_candidates)
    write_frame(root / "persistence" / "consolidation_actions.parquet", consolidation_actions)
    write_frame(root / "persistence" / "negative_knowledge.parquet", negative_records, ["case_id", "kind", "key", "detail"])
    write_json(root / "persistence" / "persistent_knowledge.json", {"records": consolidation_actions})
    interaction_certificates = {
        payload["certificate_id"]: payload
        for case in cases for action in case["actions"]
        for payload in action.get("interaction_certificate_payloads", [])
    }
    write_json(root / "integrity" / "interaction_certificates.json", {"certificates": list(interaction_certificates.values())})
    summary = {
        "case_executions": len(results),
        "unique_cases": len(cases),
        "library_sizes": library_sizes,
        "terminal_counts": dict(Counter(item.trace["terminal_action"] for item in results)),
        "round_count": len(rounds),
        "query_probe_program_count": len(queries),
        "external_escalation_count": len(escalations),
        "local_certificate_count": sum(result.certificate is not None for result in results),
        "persistent_candidate_count": len(promotion_candidates),
        "runtime_created_candidate_count": sum(bool(action.get("runtime_created", False)) for case in cases for action in case["actions"]),
    }
    write_json(root / "reports" / "runtime_execution_summary.json", summary)
    # console.log: phase7.runtime.complete
    print(f'{{"event":"phase7.runtime.complete","executions":{len(results)},"rounds":{len(rounds)},"escalations":{len(escalations)}}}')


if __name__ == "__main__":
    main()
