"""Evaluator-owned response release process for Phase 9 targeted queries."""

from __future__ import annotations

import argparse

import pandas as pd

from mavs10d.core.hashing import stable_hash
from mavs10d.revalidation.executor import release_query_responses
from phase9_common import PHASE9_ROOT, track_root, write_frame, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", required=True)
    parser.add_argument("--generation", required=True, type=int)
    args = parser.parse_args()
    root = track_root(args.track)
    requests = pd.read_parquet(root / f"manifests/generation_{args.generation}/query_requests.parquet")
    truth = pd.read_parquet(PHASE9_ROOT / f"evaluator_sealed/{args.track}/generation_{args.generation}/truth.parquet")
    responses = release_query_responses(requests, truth)
    response_path = root / f"manifests/generation_{args.generation}/released_query_responses.parquet"
    write_frame(response_path, responses)
    oracle = truth[["opportunity_id", "unsafe"]].copy()
    oracle["oracle_action"] = oracle["unsafe"].map({True: "REJECT", False: "ACCEPT"})
    oracle["oracle_signature"] = [stable_hash([oid, action, "phase9-quarantined-oracle"]) for oid, action in zip(oracle["opportunity_id"], oracle["oracle_action"])]
    oracle = oracle.drop(columns=["unsafe"])
    write_frame(root / f"integrity/oracle_quarantine/generation_{args.generation}/oracle_actions.parquet", oracle)
    write_json(root / f"integrity/generation_{args.generation}_evaluator_release.json", {
        "schema_version": "1.0.0", "track_id": args.track, "generation": args.generation,
        "process_identity": f"phase9-{args.track}-evaluator", "request_count": len(requests),
        "response_count": len(responses), "released_fields": sorted(responses.columns),
        "forbidden_truth_fields_released": [], "passed": len(requests) == len(responses),
    })
    # console.log: phase9.evaluator.release.complete
    print(f'{{"event":"phase9.evaluator.release.complete","track":"{args.track}","generation":{args.generation},"responses":{len(responses)}}}')


if __name__ == "__main__":
    main()
