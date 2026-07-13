"""Policy, schema, and tool-use rail adapters for the Phase 4 tournament."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class RailsBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible rail benchmark adaptation."""

