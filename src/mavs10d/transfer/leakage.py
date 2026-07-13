"""Exact/near-duplicate and participant answer-key audit primitives."""

from __future__ import annotations

from collections.abc import Iterable


FORBIDDEN_PARTICIPANT_TOKENS = (
    "answer_key_hash", "hidden_outcomes", "correct_action", "catastrophic_if_accepted",
    "hidden_mechanism", "future_manifest", "raw_hidden_labels",
)


def exact_overlap(left: Iterable[str], right: Iterable[str]) -> set[str]:
    return set(left) & set(right)


def near_duplicate_overlap(left: Iterable[str], right: Iterable[str]) -> set[str]:
    return set(left) & set(right)


def forbidden_source_tokens(source: str) -> tuple[str, ...]:
    return tuple(token for token in FORBIDDEN_PARTICIPANT_TOKENS if token in source)
