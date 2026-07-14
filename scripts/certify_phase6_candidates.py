"""Run blind behavior-only certification in an isolated child process."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from mavs10d.certification.blind_api import assert_blind_payload, candidate_from_blind_request
from mavs10d.certification.gates import certification_trace, evaluate_gates, perception_extension_witness
from phase6_common import read_json, run_root, write_json


def worker(root: Path, seed: int) -> None:
    bank = pd.read_parquet(root / "banks" / "certification_banks.parquet")
    queue = root / "blind_queue"
    output = root / "blind_outputs"
    for request_path in sorted(queue.glob("*.json")):
        request = json.loads(request_path.read_text(encoding="utf-8"))
        assert_blind_payload(request)
        candidate = candidate_from_blind_request(request)
        trace = certification_trace(candidate, bank)
        witness = perception_extension_witness(candidate, trace)
        vector = evaluate_gates(candidate, trace, witness, seed)
        vector["anonymous_semantic_id"] = request["anonymous_semantic_id"]
        destination = output / request["anonymous_semantic_id"]
        destination.mkdir(parents=True, exist_ok=True)
        trace.to_parquet(destination / "certification_trace.parquet", index=False)
        write_json(destination / "perception_extension_witness.json", witness)
        write_json(destination / "independent_gate_vector.json", vector)


def controller(root: Path, seed: int) -> None:
    queue = root / "blind_queue"
    outputs = root / "blind_outputs"
    queue.mkdir(exist_ok=False)
    outputs.mkdir(exist_ok=False)
    state = read_json(root / "manifests" / "synthesis_state.json")
    for record in state:
        request = read_json(root / "candidates" / record["candidate_id"] / "blind_request.json")
        assert_blind_payload(request)
        write_json(queue / f"{request['anonymous_semantic_id']}.json", request)
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker-root", str(root), "--seed", str(seed)], check=True)
    updated = []
    for record in state:
        directory = root / "candidates" / record["candidate_id"]
        request = read_json(directory / "blind_request.json")
        source = outputs / request["anonymous_semantic_id"]
        shutil.copy2(source / "certification_trace.parquet", directory / "certification_trace.parquet")
        witness = read_json(source / "perception_extension_witness.json")
        witness["candidate_id"] = record["candidate_id"]
        write_json(directory / "perception_extension_witness.json", witness)
        vector = read_json(source / "independent_gate_vector.json")
        write_json(directory / "independent_gate_vector.json", vector)
        updated.append({**record, "certification_passed": bool(vector["all_passed"]), "failed_certification_gates": [name for name, gate in vector["gates"].items() if not gate["passed"]]})
    write_json(root / "manifests" / "certification_state.json", updated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--worker-root")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    if args.worker_root:
        worker(Path(args.worker_root), args.seed)
        # console.log: phase6.certification.worker_complete
        print('{"event":"phase6.certification.worker_complete"}')
        return
    if not args.run_id:
        raise ValueError("--run-id is required in controller mode.")
    controller(run_root(args.run_id), args.seed)
    # console.log: phase6.certification.controller_complete
    print(f'{{"event":"phase6.certification.controller_complete","run_id":"{args.run_id}"}}')


if __name__ == "__main__":
    main()
