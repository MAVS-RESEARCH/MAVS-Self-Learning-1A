"""Deterministically replay every Phase 6 candidate from blind executable artifacts."""

from __future__ import annotations

import argparse

import pandas as pd

from mavs10d.certification.blind_api import candidate_from_blind_request
from mavs10d.certification.gates import certification_trace, evaluate_gates, perception_extension_witness
from mavs10d.core.hashing import stable_hash
from phase6_common import read_json, run_root, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    bank = pd.read_parquet(root / "banks" / "certification_banks.parquet")
    state = read_json(root / "manifests" / "certification_state.json")
    records = []
    for record in state:
        directory = root / "candidates" / record["candidate_id"]
        request = read_json(directory / "blind_request.json")
        candidate = candidate_from_blind_request(request)
        expected_trace = pd.read_parquet(directory / "certification_trace.parquet")
        actual_trace = certification_trace(candidate, bank)
        witness = perception_extension_witness(candidate, actual_trace)
        actual_vector = evaluate_gates(candidate, actual_trace, witness, 630001)
        actual_vector["anonymous_semantic_id"] = request["anonymous_semantic_id"]
        expected_vector = read_json(directory / "independent_gate_vector.json")
        trace_equal = expected_trace.equals(actual_trace)
        gate_equal = stable_hash(expected_vector) == stable_hash(actual_vector)
        records.append({"candidate_id": record["candidate_id"], "trace_replayed": trace_equal, "gate_vector_replayed": gate_equal, "witness_replayed": bool(witness["valid"]) == bool(read_json(directory / "perception_extension_witness.json")["valid"]), "passed": trace_equal and gate_equal and bool(witness["valid"]) == bool(read_json(directory / "perception_extension_witness.json")["valid"])})
    report = {"candidate_count": len(records), "records": records, "passed_count": sum(item["passed"] for item in records), "failed_count": sum(not item["passed"] for item in records), "passed": all(item["passed"] for item in records)}
    write_json(root / "integrity" / "deterministic_replay_report.json", report)
    updated = [{**record, "replay_passed": next(item["passed"] for item in records if item["candidate_id"] == record["candidate_id"])} for record in state]
    write_json(root / "manifests" / "replay_state.json", updated)
    if not report["passed"]:
        raise RuntimeError("Candidate replay failed.")
    # console.log: phase6.replay.complete
    print(f'{{"event":"phase6.replay.complete","candidates":{len(records)}}}')


if __name__ == "__main__":
    main()

