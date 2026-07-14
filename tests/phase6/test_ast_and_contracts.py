from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mavs10d.diagnostics.ast import ASTValidationError, ast_hash, canonicalize_ast, deserialize_ast, evaluate_ast, serialize_ast, validate_ast
from mavs10d.diagnostics.semantic_hash import semantic_hash
from mavs10d.learning.synthesis import build_bank, synthesize_candidates


def test_ast_type_illegal_missing_and_bounds_fail_closed() -> None:
    with pytest.raises(ASTValidationError): validate_ast({"op": "feature", "name": "opaque_name"})
    with pytest.raises(ASTValidationError): validate_ast({"op": "divide", "children": []})
    with pytest.raises(ASTValidationError): validate_ast({"op": "parameter", "name": "missing"}, {})
    with pytest.raises(ASTValidationError): validate_ast({"op": "clip", "children": [{"op": "constant", "value": 1.0}], "lower": 2.0, "upper": 1.0})
    with pytest.raises(ASTValidationError): validate_ast({"op": "and", "children": [{"op": "feature", "name": "risk_score"}, {"op": "constant", "value": True}]})
    with pytest.raises(ASTValidationError): evaluate_ast({"op": "feature", "name": "risk_score"}, {"risk_score": np.array([1.2])})


def test_canonical_commutativity_round_trip_and_evaluator_equivalence() -> None:
    first = {"op": "and", "children": [{"op": "gte", "left": {"op": "feature", "name": "risk_score"}, "right": {"op": "constant", "value": 0.5}}, {"op": "gte", "left": {"op": "feature", "name": "evidence_available"}, "right": {"op": "constant", "value": 0.5}}]}
    second = {"op": "and", "children": list(reversed(first["children"]))}
    assert canonicalize_ast(first) == canonicalize_ast(second)
    assert ast_hash(first) == ast_hash(second)
    features = {"risk_score": np.array([0.0, 1.0]), "evidence_available": np.array([1.0, 1.0])}
    assert np.array_equal(evaluate_ast(first, features), evaluate_ast(second, features))
    assert deserialize_ast(serialize_ast(first)) == canonicalize_ast(first)


def test_semantic_identity_ignores_documentary_name() -> None:
    bank = build_bank(620001, 8)
    candidate = synthesize_candidates(bank, 610001, 620001)[0].candidate
    renamed = replace(candidate, name="unrelated-documentary-name")
    assert semantic_hash(candidate) == semantic_hash(renamed)
