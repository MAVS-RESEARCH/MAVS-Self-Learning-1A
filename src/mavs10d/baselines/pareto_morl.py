"""Weighted, epsilon-constrained, IPRO-style, and preference-conditioned adapters."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class ParetoMORLBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible multi-objective benchmark adaptation."""

