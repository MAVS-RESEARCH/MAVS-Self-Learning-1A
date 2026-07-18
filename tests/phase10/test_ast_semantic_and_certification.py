from __future__ import annotations

import copy

import pandas as pd

from mavs10d.audit_v04.ast_execution import complexity, execute
from mavs10d.audit_v04.certification import recompute_gate_values
from mavs10d.audit_v04.semantic import name_invariant, semantic_hash, template_signature


def candidate():
    return {
        "candidate_id": "A", "candidate_name": "alpha",
        "expression_ast": {"op": "gte", "left": {"op": "feature", "name": "risk"}, "right": {"op": "parameter", "name": "threshold"}},
        "parameters": {"threshold": 0.5},
        "positive_scope_ast": {"op": "gte", "left": {"op": "feature", "name": "scope"}, "right": {"op": "constant", "value": 0.5}},
        "anti_scope_ast": {"op": "lte", "left": {"op": "feature", "name": "scope"}, "right": {"op": "constant", "value": 0.1}},
        "evidence_contract": {"sources": ["risk", "scope"]}, "influence_contract": {"channel": "terminal"},
        "counterfactual_contract": {"causal_interventions": ["risk"]},
    }


def test_independent_ast_executes_comparison():
    assert execute(candidate()["expression_ast"], {"risk": 0.8}, {"threshold": 0.5}) is True


def test_independent_ast_complexity_is_structural():
    assert complexity(candidate()["expression_ast"]) == 3


def test_semantic_hash_excludes_names():
    assert name_invariant(candidate(), "RENAMED")


def test_semantic_hash_detects_parameter_change():
    changed = copy.deepcopy(candidate())
    changed["parameters"]["threshold"] = 0.6
    assert semantic_hash(candidate()) != semantic_hash(changed)


def test_semantic_hash_canonicalizes_commutative_children():
    first = candidate()
    first["expression_ast"] = {"op": "and", "children": [first["expression_ast"], first["positive_scope_ast"]]}
    second = copy.deepcopy(first)
    second["expression_ast"]["children"].reverse()
    assert semantic_hash(first) == semantic_hash(second)


def test_template_signature_ignores_literal_values_but_retains_structure():
    first = candidate()["expression_ast"]
    second = copy.deepcopy(first)
    second["right"]["name"] = "different_parameter"
    assert template_signature(first) == template_signature(second)


def test_gate_recomputation_uses_raw_trace():
    rows = []
    for bank in ["trigger", "retained", "anti_scope", "positive_scope_boundary", "adversarial", "nuisance_counterfactual", "causal_counterfactual"]:
        rows.append({"bank": bank, "case_id": bank, "active": bank != "anti_scope", "decision_error": False, "positive_scope": True, "evidence_available": True, "discrete_output": 1})
    frame = pd.DataFrame(rows)
    witness = {"valid": True}
    values = recompute_gate_values(candidate(), frame, witness)
    assert values["kernel"][1] and values["protected_error"][1] and values["replay"][1]
