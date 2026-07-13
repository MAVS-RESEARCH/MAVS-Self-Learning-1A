"""Fail-closed Phase 4 seed, bank, participant-visibility, and retuning separation."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.baselines.phase4_base import decide_visible  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase4.yaml").read_text(encoding="utf-8"))
    if config["model_training"] != "none" or config["post_holdout_retuning"] is not False:
        errors.append("training_or_retuning_policy")
    phase4_ranges = [set(range(int(config["final_seed_ranges"][generation][0]), int(config["final_seed_ranges"][generation][1]) + 1)) for generation in (1, 2, 3)]
    if any(left & right for index, left in enumerate(phase4_ranges) for right in phase4_ranges[index + 1:]):
        errors.append("generation_seed_overlap")
    if any(seed < 900000 or seed > 999999 for values in phase4_ranges for seed in values):
        errors.append("outside_reserved_final_seed_range")
    root = REPO_ROOT / "results/manifests" / run_id / "phase4"
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest["canonical_opportunities"] != 75000 or run_manifest["selection_final_access"] is not False:
        errors.append("run_manifest_allocation_or_selection_access")
    if run_manifest["replay_counts_as_canonical"] is not False or run_manifest["post_holdout_retuning"] is not False:
        errors.append("replay_or_retuning_policy")
    ids: set[str] = set()
    forbidden = {"unsafe", "correct_action", "catastrophic_if_accepted", "irreversible_if_accepted", "hidden_regime", "feedback_target"}
    expected_resets = config["reset_mixtures"]
    for generation in (1, 2, 3):
        directory = root / f"generation_{generation}"
        body = json.loads((directory / "generation_manifest.json").read_text(encoding="utf-8"))["body"]
        table = pq.read_table(directory / "world_ledger.parquet", columns=None)
        if table.num_rows != 25000 or body["world_count"] != 500 or body["decisions_per_world"] != 50:
            errors.append(f"allocation:g{generation}")
        if forbidden & set(table.column_names):
            errors.append(f"hidden_visible:g{generation}")
        if body["reset_counts"] != {str(key): int(value) for key, value in expected_resets[generation].items()}:
            errors.append(f"reset_mix:g{generation}")
        values = set(table.column("opportunity_id").to_pylist())
        if ids & values:
            errors.append(f"opportunity_overlap:g{generation}")
        ids |= values
        if body["participant_final_access"] is not False or body["selection_bank_overlap"] != 0:
            errors.append(f"participant_access:g{generation}")
    participant_source = inspect.getsource(decide_visible)
    for token in ("unsafe", "correct_action", "catastrophic", "hidden_regime", "feedback_target", "hidden_outcomes"):
        if token in participant_source:
            errors.append(f"participant_source_forbidden:{token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase4.separation.step01.start
    console_log("phase4.separation.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase4.separation.step02.complete
    console_log("phase4.separation.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
