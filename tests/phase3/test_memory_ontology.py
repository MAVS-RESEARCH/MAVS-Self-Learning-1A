from __future__ import annotations

import pytest

from mavs10d.governance.self_learning.memory import AppendOnlyTraceMemory, RetainedCounterexample, RetainedCounterexampleBank
from mavs10d.governance.self_learning.ontology import FailureFamily, FailureOntology


def _family(family_id: str, parents: tuple[str, ...] = ()) -> FailureFamily:
    return FailureFamily(
        family_id=family_id,
        semantic_definition=family_id,
        context_predicates={"domain": "synthetic"},
        observable_signature={"signal": 0.8},
        causal_hypotheses=("diagnostics",),
        severity_scale={"high": 1.0},
        permissible_responses=("escalate",),
        known_confounders=("masking",),
        confidence=0.8,
        status="provisional",
        parent_ids=parents,
        projections=("synthetic",),
        version=1,
    )


def test_append_only_memory_requires_decision_before_outcome() -> None:
    memory = AppendOnlyTraceMemory()
    with pytest.raises(ValueError, match="existing decision"):
        memory.append_outcome("missing", {"released_label": "safe"})
    decision = memory.append_decision({"trace_id": "trace-1", "action": "escalate"})
    outcome = memory.append_outcome("trace-1", {"released_label": "safe"})
    assert decision.sequence == 0 and outcome.sequence == 1
    assert memory.validate_chain()


def test_prefeedback_memory_rejects_evaluator_fields() -> None:
    memory = AppendOnlyTraceMemory()
    with pytest.raises(ValueError, match="evaluator-only"):
        memory.append_decision({"trace_id": "trace-1", "unsafe": True})


def test_retained_counterexamples_are_immutable_and_explicitly_superseded() -> None:
    bank = RetainedCounterexampleBank()
    first = RetainedCounterexample("c1", "t1", "f", "reject", "accept", {"x": 1.0}, True)
    second = RetainedCounterexample("c2", "t2", "f", "reject", "reject", {"x": 0.9}, True)
    bank.add(first)
    bank.add(second)
    bank.supersede("c1", "c2")
    assert [item.counterexample_id for item in bank.active()] == ["c2"]
    assert len(bank.all()) == 2


def test_contrast_candidate_index_uses_exact_validated_context_stratum() -> None:
    bank = RetainedCounterexampleBank()
    base = {"curriculum_id": "R01", "domain": "text_safety", "target_context": True}
    first = RetainedCounterexample("c1", "t1", "f", "reject", "accept", {**base, "generation": 1}, True)
    second = RetainedCounterexample("c2", "t2", "f", "reject", "accept", {**base, "generation": 2}, True)
    bank.add(first)
    bank.add(second)
    assert bank.contrast_candidates(second.visible_signature) == (second,)


def test_ontology_split_and_merge_preserve_genealogy() -> None:
    ontology = FailureOntology()
    ontology.add(_family("parent"), "seed")
    ontology.split("parent", (_family("left", ("parent",)), _family("right", ("parent",))), "semantic_conflation")
    ontology.merge(("left", "right"), _family("merged", ("left", "right")), "redundancy")
    operations = [item["operation"] for item in ontology.genealogy()]
    assert "split" in operations and "merge" in operations
    assert ontology.ontology_hash
