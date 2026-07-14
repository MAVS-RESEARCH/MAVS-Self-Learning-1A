"""Name- and metadata-invariant diagnostic semantic identity."""

from __future__ import annotations

from typing import Any

from mavs10d.core.hashing import stable_hash
from mavs10d.diagnostics.ast import AST_VERSION, canonicalize_ast
from mavs10d.diagnostics.contracts import ExecutableDiagnostic


def semantic_payload(candidate: ExecutableDiagnostic) -> dict[str, Any]:
    candidate.validate()
    return {
        "ast_version": AST_VERSION,
        "expression_ast": canonicalize_ast(candidate.expression_ast),
        "parameters": dict(sorted(candidate.parameters.items())),
        "positive_scope_ast": canonicalize_ast(candidate.positive_scope_ast),
        "anti_scope_ast": canonicalize_ast(candidate.anti_scope_ast),
        "evidence_contract": candidate.evidence_contract,
        "influence_contract": candidate.influence_contract,
        "counterfactual_contract": candidate.counterfactual_contract,
    }


def semantic_hash(candidate: ExecutableDiagnostic) -> str:
    return stable_hash(semantic_payload(candidate))


def differs_only_by_nonsemantic_metadata(first: ExecutableDiagnostic, second: ExecutableDiagnostic) -> bool:
    return semantic_hash(first) == semantic_hash(second) and first.to_dict() != second.to_dict()
