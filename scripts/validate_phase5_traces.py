"""Stream-validate Phase 5 identities, lineage, and complete matched replay coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


REQUIRED = {
    "run_kind", "experimental_condition_id", "ablation_id", "condition", "generation",
    "opportunity_id", "world_id", "action", "unsafe", "accepted", "rejected", "escalated",
    "uar_error", "frr_error", "terminal_error", "catastrophic_interference",
    "config_hash", "ledger_sha256", "git_sha", "environment_hash", "registry_sha256",
    "trace_lineage_sha256", "trace_complete",
}


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    root = REPO_ROOT / "results/raw" / run_id / "phase5"
    manifest = json.loads((root / "tournament_manifest.json").read_text(encoding="utf-8"))
    total = 0
    for artifact in manifest["artifacts"]:
        generation = int(artifact["generation"])
        path = REPO_ROOT / artifact["trace"]
        parquet = pq.ParquetFile(path)
        missing = REQUIRED - set(parquet.schema_arrow.names)
        if missing:
            errors.append(f"schema:g{generation}:{sorted(missing)}")
            continue
        counts: Counter[tuple[str, str, str]] = Counter()
        rows = 0
        for batch in parquet.iter_batches(batch_size=100000, columns=sorted(REQUIRED)):
            data = batch.to_pydict()
            rows += batch.num_rows
            counts.update(zip(data["run_kind"], data["experimental_condition_id"], data["condition"]))
            for index in range(batch.num_rows):
                action = data["action"][index]
                unsafe = bool(data["unsafe"][index])
                run_kind = data["run_kind"][index]
                ablation_id = data["ablation_id"][index]
                if run_kind in {"ablation", "retention_replay"} and ablation_id not in {f"A{value}" for value in range(50)}:
                    errors.append(f"ablation_identity:g{generation}:{rows-batch.num_rows+index}")
                    return errors
                if action not in {"accept", "reject", "escalate"}:
                    errors.append(f"action:g{generation}:{rows-batch.num_rows+index}")
                    return errors
                if bool(data["uar_error"][index]) != (unsafe and action == "accept"):
                    errors.append(f"uar_identity:g{generation}:{rows-batch.num_rows+index}")
                    return errors
                if bool(data["frr_error"][index]) != ((not unsafe) and action == "reject"):
                    errors.append(f"frr_identity:g{generation}:{rows-batch.num_rows+index}")
                    return errors
                if sum((bool(data["accepted"][index]), bool(data["rejected"][index]), bool(data["escalated"][index]))) != 1:
                    errors.append(f"action_partition:g{generation}:{rows-batch.num_rows+index}")
                    return errors
                if not bool(data["trace_complete"][index]) or len(str(data["trace_lineage_sha256"][index])) != 64:
                    errors.append(f"lineage:g{generation}:{rows-batch.num_rows+index}")
                    return errors
        expected_points = 50 * 2 + 16 * 2 + 5 * 4 * 2 + (50 * 2 if generation > 1 else 0)
        if rows != 15000 * expected_points or len(counts) != expected_points or any(value != 15000 for value in counts.values()):
            errors.append(f"coverage:g{generation}:rows={rows}:points={len(counts)}")
        if file_sha256(path) != artifact["trace_sha256"]:
            errors.append(f"trace_hash:g{generation}")
        for card_key in ("terminal_cards", "promoted_update_cards"):
            card = REPO_ROOT / artifact[card_key]
            if not card.exists() or pq.ParquetFile(card).metadata.num_rows <= 0:
                errors.append(f"missing_or_empty_{card_key}:g{generation}")
        total += rows
    checkpoints = json.loads((root / "participant_checkpoints.json").read_text(encoding="utf-8"))
    if len(checkpoints) != 300 or any(card["raw_answer_keys"] != 0 or card["future_manifest_access"] for card in checkpoints):
        errors.append("participant_checkpoints")
    consolidation = json.loads((root / "consolidation_cards.json").read_text(encoding="utf-8"))
    if len(consolidation) != 200 or any(not card["change_hash"] or card["catastrophic_interference"] not in (0, 1) for card in consolidation):
        errors.append("consolidation_cards")
    if total != int(manifest["trace_rows"]):
        errors.append(f"total_trace_rows:{total}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase5.traces.step01.start
    console_log("phase5.traces.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase5.traces.step02.complete
    console_log("phase5.traces.step02.complete", error_count=len(errors), errors=errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
