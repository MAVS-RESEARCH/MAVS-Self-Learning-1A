from __future__ import annotations

import pytest

from mavs10d.diagnostics.interactions import certify_interaction, enforce_interaction_status
from mavs10d.diagnostics.typed_channels import Influence, arbitrate


@pytest.mark.parametrize("channel", ["availability", "scope", "novelty", "conflict"])
def test_meta_channels_cannot_hard_veto(channel: str) -> None:
    influence = Influence("meta", channel, "L3", "REJECT", "meta", True)
    with pytest.raises(PermissionError, match="cannot directly"):
        influence.validate()


def test_typed_arbitration_uses_explanation_graph_not_additive_severity() -> None:
    safe = Influence("safe-witness", "safe", "L2", "ACCEPT", "benign_mechanism", True)
    result = arbitrate([safe])
    assert result["terminal_action"] == "ACCEPT"
    assert result["primary_causal_family"] == "benign_mechanism"
    assert result["additive_severity_used"] is False


def test_interaction_certificate_and_prohibition() -> None:
    certificate = certify_interaction(["a", "b"], "joint", ["scope"], counterfactual_passed=True, nonredundant=True, protected_regression=0.0)
    assert certificate.permits_terminal_influence()
    untested = certify_interaction(["a", "b"], "joint", ["scope"], counterfactual_passed=False, nonredundant=True, protected_regression=0.0)
    assert enforce_interaction_status(untested.status, True) == "observation_only"
    prohibited = certify_interaction(["a", "b"], "joint", ["scope"], counterfactual_passed=True, nonredundant=True, protected_regression=0.0, prohibited_patterns={frozenset({"a", "b"})})
    with pytest.raises(PermissionError, match="Prohibited"):
        enforce_interaction_status(prohibited.status, True)
