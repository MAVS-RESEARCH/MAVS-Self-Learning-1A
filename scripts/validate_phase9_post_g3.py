"""Run retained-counterexample and rotating-scope challenges after G3 and before summaries."""

from __future__ import annotations

import pandas as pd

from mavs10d.revalidation.conditions import condition_registry
from mavs10d.revalidation.executor import execute_generation
from phase9_common import PHASE9_ROOT, read_json, track_root, write_frame, write_json


def main() -> None:
    total_retained = 0
    for track_id in ("paired_original_bank", "blind_bank"):
        root = track_root(track_id)
        condition = next(item for item in condition_registry(track_id) if item.id == "v04_cumulative")
        final_state = read_json(root / "checkpoints/generation_3/v04_cumulative.json")["state"]
        retained_rows = []
        for generation in (1, 2):
            public = pd.read_parquet(root / f"manifests/generation_{generation}/public_ledger.parquet")
            responses = pd.read_parquet(root / f"manifests/generation_{generation}/released_query_responses.parquet")
            replayed, _ = execute_generation(public, responses, condition, 3, final_state, seed=9700000 + (100000 if track_id == "blind_bank" else 0) + generation * 1000)
            truth = pd.read_parquet(PHASE9_ROOT / f"evaluator_sealed/{track_id}/generation_{generation}/truth.parquet")[["opportunity_id", "unsafe"]]
            joined = replayed.merge(truth, on="opportunity_id", validate="one_to_one")
            selected = joined.sort_values(["causal_family", "residual_reason", "opportunity_id"]).groupby(["causal_family", "residual_reason"], observed=True).head(1)
            retained_rows.append(selected)
        retained = pd.concat(retained_rows, ignore_index=True)
        unsafe = retained["unsafe"].astype(bool); safe = ~unsafe
        protected_errors = int((unsafe & (retained["terminal_action"] == "ACCEPT")).sum() + (safe & (retained["terminal_action"] == "REJECT")).sum())
        scope_leakage = int(retained["scope_leakage"].sum())
        write_frame(root / "integrity/retained_counterexample_traces.parquet", retained)
        write_json(root / "integrity/retained_counterexample_report.json", {
            "schema_version": "1.0.0", "track_id": track_id, "challenge_timing": "after_g3_before_summaries",
            "case_count": len(retained), "protected_error_count": protected_errors, "scope_leakage_count": scope_leakage,
            "final_checkpoint_reused": True, "passed": protected_errors == 0 and scope_leakage == 0,
        })
        total_retained += len(retained)
        g3 = pd.read_parquet(root / "decision_traces/v04_cumulative/generation_3.parquet")
        holdouts = []
        for domain in sorted(g3["domain"].unique()):
            outside = g3[g3["domain"] != domain]
            forbidden = int(outside["program_scope_key"].astype(str).str.startswith(domain + "|").sum())
            holdouts.append({"heldout_domain": domain, "outside_case_count": len(outside), "influential_out_of_scope_activation_count": forbidden, "passed": forbidden == 0})
        write_json(root / "integrity/rotating_scope_holdout_report.json", {
            "schema_version": "1.0.0", "track_id": track_id, "challenge_timing": "after_g3_before_summaries",
            "holdouts": holdouts, "passed": all(item["passed"] for item in holdouts),
        })
        if protected_errors or scope_leakage or not all(item["passed"] for item in holdouts):
            raise RuntimeError(f"Phase 9 post-G3 challenges failed for {track_id}.")
    # console.log: phase9.post_g3.complete
    print(f'{{"event":"phase9.post_g3.complete","tracks":2,"retained_cases":{total_retained},"findings":0}}')


if __name__ == "__main__":
    main()

