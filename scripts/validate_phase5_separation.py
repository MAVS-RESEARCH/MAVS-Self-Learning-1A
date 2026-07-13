"""Fail-closed Phase 5 seed, bank, leakage, attacker, and retuning separation."""

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

from mavs10d.ablations.engine import decide_visible  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.transfer.leakage import forbidden_source_tokens  # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase5.yaml").read_text(encoding="utf-8"))
    if config["model_training"] != "none" or config["post_holdout_retuning"] is not False:
        errors.append("training_or_retuning_policy")
    ranges = [set(range(int(config["final_seed_ranges"][generation][0]), int(config["final_seed_ranges"][generation][1]) + 1)) for generation in (1, 2, 3)]
    if any(left & right for index, left in enumerate(ranges) for right in ranges[index + 1:]):
        errors.append("generation_seed_overlap")
    prior_reserved = set(range(900000, 900500)) | set(range(910000, 910500)) | set(range(920000, 920500))
    if any(values & prior_reserved for values in ranges):
        errors.append("phase4_seed_overlap")
    root = REPO_ROOT / "results/manifests" / run_id / "phase5"
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest["canonical_opportunities"] != 45000 or run_manifest["canonical_per_generation"] != 15000:
        errors.append("canonical_allocation")
    if run_manifest["replays_count_as_canonical"] is not False or run_manifest["post_holdout_retuning"] is not False:
        errors.append("replay_or_retuning_policy")
    expected_strata = {str(key): int(value) for key, value in config["benchmark_strata"].items()}
    forbidden = {"unsafe", "correct_action", "catastrophic_if_accepted", "irreversible_if_accepted", "hidden_mechanism", "answer_key_hash"}
    opportunity_ids: set[str] = set()
    raw_hashes: set[str] = set()
    near_hashes: set[str] = set()
    for generation in (1, 2, 3):
        directory = root / f"generation_{generation}"
        body = json.loads((directory / "generation_manifest.json").read_text(encoding="utf-8"))["body"]
        table = pq.read_table(directory / "world_ledger.parquet")
        hidden = json.loads((directory / "hidden_outcomes.json").read_text(encoding="utf-8"))["outcomes"]
        if table.num_rows != 15000 or body["world_count"] != 300 or body["decisions_per_world"] != 50:
            errors.append(f"allocation:g{generation}")
        if forbidden & set(table.column_names):
            errors.append(f"hidden_visible:g{generation}")
        if body["benchmark_strata"] != expected_strata:
            errors.append(f"strata:g{generation}")
        expected_resets = {str(key): int(value) for key, value in config["reset_mixtures"][generation].items()}
        if body["reset_counts"] != expected_resets:
            errors.append(f"reset_mix:g{generation}")
        ids = set(table.column("opportunity_id").to_pylist())
        generation_raw = {row["raw_content_hash"] for row in hidden}
        generation_near = {row["near_duplicate_signature"] for row in hidden}
        if opportunity_ids & ids or raw_hashes & generation_raw or near_hashes & generation_near:
            errors.append(f"cross_generation_duplicate:g{generation}")
        opportunity_ids |= ids
        raw_hashes |= generation_raw
        near_hashes |= generation_near
        adversarial_worlds = int(expected_resets["adversarial"])
        if body["adversarial_probes"] != adversarial_worlds * int(config["attack"]["probes_per_adversarial_world"]):
            errors.append(f"attacker_budget:g{generation}")
        if body["participant_final_access"] is not False or body["post_holdout_retuning"] is not False:
            errors.append(f"participant_access:g{generation}")
    prior_ids: set[str] = set()
    prior_seeds: set[int] = set()
    for ledger_path in (REPO_ROOT / "results/manifests").glob("*/phase[1-4]/generation_*/world_ledger.parquet"):
        prior_table = pq.read_table(ledger_path)
        if "opportunity_id" in prior_table.column_names:
            prior_ids.update(str(value) for value in prior_table.column("opportunity_id").to_pylist())
        if "world_seed" in prior_table.column_names:
            prior_seeds.update(int(value) for value in prior_table.column("world_seed").to_pylist())
    if opportunity_ids & prior_ids:
        errors.append("prior_phase_opportunity_overlap")
    if set().union(*ranges) & prior_seeds:
        errors.append("prior_phase_seed_overlap")
    tokens = forbidden_source_tokens(inspect.getsource(decide_visible))
    if tokens:
        errors.extend(f"participant_source_forbidden:{token}" for token in tokens)
    if config["attack"]["generator"] == config["generator_implementations"][0]:
        errors.append("attacker_not_independent")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase5.separation.step01.start
    console_log("phase5.separation.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase5.separation.step02.complete
    console_log("phase5.separation.step02.complete", error_count=len(errors), errors=errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
