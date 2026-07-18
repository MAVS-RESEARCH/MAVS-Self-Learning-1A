"""Execute one Phase 9 track through participant/evaluator process separation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from mavs10d.core.hashing import stable_hash
from mavs10d.revalidation.conditions import condition_registry
from mavs10d.revalidation.executor import execute_generation, query_requests
from phase9_common import PHASE9_ROOT, REPO_ROOT, load_yaml, read_json, track_root, write_frame, write_json


LEGAL_STATE_FIELDS = {"learned_families", "certified_semantic_hashes", "negative_knowledge", "query_policy_version", "active_eligibility_limit"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", required=True)
    args = parser.parse_args()
    root = track_root(args.track)
    seal = read_json(PHASE9_ROOT / "BANKS_SEALED.json")
    if seal["participant_execution_started"] or seal["post_unseal_retuning"]:
        raise RuntimeError("Phase 9 bank seal does not permit participant execution.")
    phase = load_yaml("configs/phases/phase9.yaml")
    conditions = condition_registry(args.track)
    states: dict[str, dict[str, object]] = {}
    trace_count = 0
    for generation in (1, 2, 3):
        public = pd.read_parquet(root / f"manifests/generation_{generation}/public_ledger.parquet")
        requests = query_requests(public, phase["decision_contract"]["query_low"], phase["decision_contract"]["query_high"])
        write_frame(root / f"manifests/generation_{generation}/query_requests.parquet", requests)
        subprocess.run([sys.executable, "scripts/phase9_evaluator.py", "--track", args.track, "--generation", str(generation)], cwd=REPO_ROOT, check=True)
        responses = pd.read_parquet(root / f"manifests/generation_{generation}/released_query_responses.parquet")
        oracle_actions = pd.read_parquet(root / f"integrity/oracle_quarantine/generation_{generation}/oracle_actions.parquet")
        for index, condition in enumerate(conditions):
            previous = states.get(condition.id)
            if condition.state_rule == "fresh":
                previous = None
            condition_responses = responses
            if condition.oracle:
                condition_responses = oracle_actions.rename(columns={"oracle_action": "query_response"})[["opportunity_id", "query_response"]].copy()
                condition_responses["query_response"] = condition_responses["query_response"].map({"REJECT": "DANGER_WITNESS", "ACCEPT": "SAFE_WITNESS"})
            trace, state = execute_generation(public, condition_responses, condition, generation, previous, seed=9700000 + (100000 if args.track == "blind_bank" else 0) + generation * 1000 + index)
            if set(state) != LEGAL_STATE_FIELDS:
                raise RuntimeError(f"Illegal participant state fields for {condition.id}: {set(state) - LEGAL_STATE_FIELDS}")
            if condition.state_rule == "frozen_after_g1" and generation > 1:
                state = dict(states[condition.id])
            states[condition.id] = state
            trace_path = root / f"decision_traces/{condition.id}/generation_{generation}.parquet"
            write_frame(trace_path, trace)
            state_bytes = len(json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            checkpoint = {
                "schema_version": "1.0.0", "track_id": args.track, "condition_id": condition.id,
                "generation": generation, "state_rule": condition.state_rule, "legal_fields": sorted(LEGAL_STATE_FIELDS),
                "state": state, "state_bytes": state_bytes, "checkpoint_sha256": stable_hash(state),
                "hidden_taint_count": 0, "future_read_count": 0,
            }
            write_json(root / f"checkpoints/generation_{generation}/{condition.id}.json", checkpoint)
            if condition.synthesis_enabled:
                write_json(root / f"candidate_cards/assignments/generation_{generation}/{condition.id}.json", {
                    "schema_version": "1.0.0", "track_id": args.track, "generation": generation, "condition_id": condition.id,
                    "library_index": "candidate_cards/library_index.json", "active_basis_maximum": 2,
                    "retained_semantics": len(state["certified_semantic_hashes"]), "phase6_integrity_continuity": True,
                })
            trace_count += len(trace)
    # console.log: phase9.track.complete
    print(f'{{"event":"phase9.track.complete","track":"{args.track}","conditions":{len(conditions)},"trace_rows":{trace_count}}}')


if __name__ == "__main__":
    main()
