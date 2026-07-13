"""Validator-stack adapter with explicit Phase 4 operating-point provenance."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class ValidatorsBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible validator benchmark adaptation."""

