"""Lagrangian, safety-critic, and shielded safe-control adapters."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class SafeControlBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible safe-control benchmark adaptation."""

