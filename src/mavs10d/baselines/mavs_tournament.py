"""Frozen MAVS-lineage and full MAVS-SL tournament adapters."""

from mavs10d.baselines.phase4_base import FrozenTournamentMethod


class MAVSTournamentBaseline(FrozenTournamentMethod):
    """GovernanceMethod-compatible MAVS benchmark adapter over certified visible state."""

