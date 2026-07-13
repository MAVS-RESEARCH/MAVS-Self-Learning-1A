"""Validate Phase 2 allocation, DS-CF semantics, causal traces, and card completeness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase2_methods import PHASE2_METHODS  # noqa: E402
from mavs10d.core.hashing import stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str, require_cards: bool = True) -> list[str]:
    errors: list[str] = []
    expected_columns = set(json.loads((REPO_ROOT / "schemas/phase2_trace.schema.json").read_text(encoding="utf-8"))["required"])
    total_failures = 0
    lineage: set[str] = set()
    for generation in (1, 2, 3):
        frame = pd.read_parquet(REPO_ROOT / "results/raw" / run_id / "phase2" / f"generation_{generation}.parquet")
        if len(frame) != 60000:
            errors.append(f"generation {generation}: expected 60,000 trace rows, observed {len(frame)}")
        if expected_columns - set(frame.columns):
            errors.append(f"generation {generation}: trace schema columns missing")
        if set(frame["method_name"]) != set(PHASE2_METHODS):
            errors.append(f"generation {generation}: method inventory mismatch")
        opportunity_hashes = set()
        for _, method in frame.groupby("method_name", sort=True):
            if len(method) != 20000:
                errors.append(f"generation {generation}: method did not receive 20,000 opportunities")
            opportunity_hashes.add(stable_hash(method["opportunity_id"].tolist()))
        if len(opportunity_hashes) != 1:
            errors.append(f"generation {generation}: matched opportunity identity failed")
        identities = frame["uar_error"].eq(frame["unsafe"] & frame["decision"].eq("accept")).all() and frame["frr_error"].eq(~frame["unsafe"] & frame["decision"].eq("reject")).all() and frame["escalated"].eq(frame["decision"].eq("escalate")).all()
        if not identities:
            errors.append(f"generation {generation}: metric identity failed")
        ds = frame[frame["method_name"].eq("ds_cf")]
        if int(ds["raw_correlation_only_veto"].sum()) != 0:
            errors.append(f"generation {generation}: raw correlation alone produced a DS-CF veto")
        invalid_hard = ds[ds["hard_veto"] & (~ds["danger_witness"] | ds["safe_witness"] | ds["harmful_correlation"].lt(0.50) | ~ds["decision"].eq("reject"))]
        if len(invalid_hard):
            errors.append(f"generation {generation}: hard veto conjunction violated")
        masked_accept = ds[ds["evidence_status"].isin(["masked", "unavailable"]) & ds["decision"].eq("accept")]
        if len(masked_accept):
            errors.append(f"generation {generation}: DS-CF accepted unavailable or masked evidence")
        poisoned = frame[frame["feedback_poisoned"] & frame["feedback_disposition"].ne("censored")]
        if bool(poisoned["feedback_disposition"].ne("quarantined").any()):
            errors.append(f"generation {generation}: poisoned released feedback escaped quarantine")
        if not {"absent", "unavailable"} <= set(ds["evidence_status"]):
            errors.append(f"generation {generation}: evidence absence/unavailability distinction missing")
        total_failures += int((frame["uar_error"] | frame["frr_error"]).sum())
        lineage.update(frame.loc[frame["uar_error"] | frame["frr_error"], "trace_lineage_sha256"].tolist())
    if require_cards:
        manifest_path = REPO_ROOT / "results/reports" / run_id / "failure_cards/phase2_failure_card_manifest.json"
        if not manifest_path.exists():
            errors.append("failure-card manifest missing")
        else:
            cards = json.loads(manifest_path.read_text(encoding="utf-8"))
            if cards["cards"] != total_failures or cards["unique_trace_lineages"] != len(lineage):
                errors.append("one-card-per-terminal-error completeness failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--without-cards", action="store_true")
    args = parser.parse_args()
    # console.log: phase2.validate_traces.step01.start
    console_log("phase2.validate_traces.step01.start", run_id=args.run_id)
    errors = validate(args.run_id, require_cards=not args.without_cards)
    # console.log: phase2.validate_traces.step02.complete
    console_log("phase2.validate_traces.step02.complete", errors=errors, error_count=len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
