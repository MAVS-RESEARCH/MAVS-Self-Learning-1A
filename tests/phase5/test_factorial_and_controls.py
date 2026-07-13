from __future__ import annotations

import numpy as np

from mavs10d.ablations.factorial import DEFINING_WORDS, FACTORS, resolution_iv_design
from mavs10d.ablations.registry import AblationState
from mavs10d.transfer.controls import MEMORY_BYTES, checkpoint_for


def test_resolution_iv_design_is_balanced_orthogonal_and_complete() -> None:
    runs = resolution_iv_design()
    matrix = np.asarray([[run.levels[factor] for factor in FACTORS] for run in runs])
    assert len(runs) == 16
    assert min(map(len, DEFINING_WORDS)) == 4
    assert np.array_equal(matrix.sum(axis=0), np.zeros(6))
    assert np.array_equal(matrix.T @ matrix, np.eye(6) * 16)


def test_state_controls_are_bounded_and_answer_key_free() -> None:
    full = checkpoint_for(AblationState(), "A0", "cumulative", 3)
    raw = checkpoint_for(AblationState(persistence="raw_memory"), "A44", "cumulative", 3)
    matched = checkpoint_for(AblationState(memory_budget="matched_baseline"), "A49", "cumulative", 3)
    assert full.retained_bytes <= MEMORY_BYTES["mavs_sl"]
    assert raw.retained_bytes <= MEMORY_BYTES["bounded_raw"]
    assert matched.retained_bytes <= MEMORY_BYTES["matched_baseline"]
    assert full.raw_answer_keys == raw.raw_answer_keys == matched.raw_answer_keys == 0
    assert not full.future_manifest_access
