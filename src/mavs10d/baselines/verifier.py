"""Critique, judge, verifier-cascade, and bounded-debate tournament adapters."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class VerifierBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible verifier benchmark adaptation."""

