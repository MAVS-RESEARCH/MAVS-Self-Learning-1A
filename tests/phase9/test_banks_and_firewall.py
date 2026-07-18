from __future__ import annotations

import inspect
from pathlib import Path

from mavs10d.core.hashing import file_sha256
from mavs10d.revalidation.banks import blind_generation, hidden_fields, original_generation
from mavs10d.revalidation.executor import execute_generation


ROOT = Path(__file__).resolve().parents[2]


def test_original_bank_is_exact_and_complete() -> None:
    bank = original_generation(1)
    source = ROOT / "results/manifests/phase5_authoritative/phase5/generation_1/world_ledger.parquet"
    assert len(bank.public) == 15_000
    assert bank.public["world_id"].nunique() == 300
    assert bank.source_identity["public_sha256"] == file_sha256(source)
    assert not (set(bank.public.columns) & hidden_fields())


def test_blind_bank_has_new_identity_and_native_separating_actions() -> None:
    original = original_generation(1)
    blind = blind_generation(1, (1_910_000, 1_910_299))
    assert len(blind.public) == len(original.public) == 15_000
    assert set(blind.public["opportunity_id"]).isdisjoint(original.public["opportunity_id"])
    assert set(blind.evaluator["raw_content_hash"]).isdisjoint(original.evaluator["raw_content_hash"])
    assert blind.evaluator["minimum_separating_action"].notna().all()
    assert not (set(blind.public.columns) & hidden_fields())


def test_participant_executor_has_no_truth_argument() -> None:
    parameters = set(inspect.signature(execute_generation).parameters)
    assert not parameters & {"truth", "unsafe", "hidden", "evaluator", "minimum_separating_action"}

