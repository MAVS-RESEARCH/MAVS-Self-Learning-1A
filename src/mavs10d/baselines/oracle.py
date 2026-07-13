"""Evaluator-only oracle diagnostic bounds, excluded from competitive claims."""

from __future__ import annotations

from typing import Iterable


def oracle_label_actions(labels: Iterable[bool]) -> tuple[str, ...]:
    return tuple("reject" if unsafe else "accept" for unsafe in labels)


def oracle_regime_actions(regimes: Iterable[str], dangerous_regimes: set[str]) -> tuple[str, ...]:
    return tuple("escalate" if regime in dangerous_regimes else "accept" for regime in regimes)


ORACLE_COMPETITIVE = False
