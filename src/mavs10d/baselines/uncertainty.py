"""Disagreement, variance, mutual-information, ensemble, and self-consistency adapters."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class UncertaintyBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible uncertainty benchmark adaptation."""

