"""Replay pinned samples and every protected failure for both Phase 9 tracks."""

from __future__ import annotations

import pandas as pd

from mavs10d.revalidation.conditions import condition_registry
from mavs10d.revalidation.executor import execute_generation
from phase9_common import PHASE9_ROOT, track_root, write_json


COMPARE = ["terminal_action", "query_count", "probe_count", "round_count", "local_resolved", "external_escalate", "residual_reason", "closure_certificate_valid", "scope_leakage", "anti_scope_violation", "interaction_violation", "typed_channel_violation", "active_basis_size", "program_complexity"]


def main() -> None:
    total = 0; protected_failures = 0; mismatches = []
    for track_index, track_id in enumerate(("paired_original_bank", "blind_bank")):
        root = track_root(track_id)
        states = {}
        for generation in (1, 2, 3):
            public = pd.read_parquet(root / f"manifests/generation_{generation}/public_ledger.parquet")
            responses = pd.read_parquet(root / f"manifests/generation_{generation}/released_query_responses.parquet")
            oracle_actions = pd.read_parquet(root / f"integrity/oracle_quarantine/generation_{generation}/oracle_actions.parquet")
            truth = pd.read_parquet(PHASE9_ROOT / f"evaluator_sealed/{track_id}/generation_{generation}/truth.parquet").set_index("opportunity_id")["unsafe"].astype(bool)
            for index, condition in enumerate(condition_registry(track_id)):
                observed = pd.read_parquet(root / f"decision_traces/{condition.id}/generation_{generation}.parquet")
                condition_responses = responses
                if condition.oracle:
                    condition_responses = oracle_actions.rename(columns={"oracle_action": "query_response"})[["opportunity_id", "query_response"]].copy()
                    condition_responses["query_response"] = condition_responses["query_response"].map({"REJECT": "DANGER_WITNESS", "ACCEPT": "SAFE_WITNESS"})
                previous = None if condition.state_rule == "fresh" else states.get(condition.id)
                replayed, state = execute_generation(public, condition_responses, condition, generation, previous, seed=9700000 + (100000 if track_id == "blind_bank" else 0) + generation * 1000 + index)
                if condition.state_rule == "frozen_after_g1" and generation > 1:
                    state = states[condition.id]
                states[condition.id] = state
                joined = observed.set_index("opportunity_id").join(truth.rename("unsafe"))
                failures = joined.index[((joined["unsafe"]) & (joined["terminal_action"] == "ACCEPT")) | ((~joined["unsafe"]) & (joined["terminal_action"] == "REJECT"))].tolist()
                sample = observed.iloc[::max(1, len(observed) // 50)].head(50)["opportunity_id"].tolist()
                selected = sorted(set(sample + failures)); protected_failures += len(failures); total += len(selected)
                left = observed.set_index("opportunity_id").loc[selected, COMPARE].astype(str)
                right = replayed.set_index("opportunity_id").loc[selected, COMPARE].astype(str)
                if not left.equals(right): mismatches.append({"track": track_id, "generation": generation, "condition": condition.id})
        write_json(root / "integrity/replay_report.json", {"schema_version": "1.0.0", "track_id": track_id, "pinned_sample_and_all_protected_failures": True, "mismatch_count": sum(item["track"] == track_id for item in mismatches), "passed": not any(item["track"] == track_id for item in mismatches)})
    if mismatches: raise RuntimeError(f"Phase 9 deterministic replay failed: {mismatches[:5]}")
    # console.log: phase9.replay.complete
    print(f'{{"event":"phase9.replay.complete","replayed":{total},"protected_failures":{protected_failures},"mismatches":0}}')


if __name__ == "__main__": main()
