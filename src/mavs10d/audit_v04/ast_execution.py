"""Independent evaluator for canonical diagnostic ASTs."""

from __future__ import annotations

from typing import Any, Mapping


def execute(node: Mapping[str, Any], evidence: Mapping[str, Any], parameters: Mapping[str, float]) -> Any:
    op = node.get("op")
    if op == "feature":
        return evidence[node["name"]]
    if op == "parameter":
        return parameters[node["name"]]
    if op == "constant":
        return node["value"]
    if op in {"and", "or"}:
        values = [bool(execute(child, evidence, parameters)) for child in node["children"]]
        return all(values) if op == "and" else any(values)
    if op == "not":
        return not bool(execute(node["child"], evidence, parameters))
    left = execute(node["left"], evidence, parameters)
    right = execute(node["right"], evidence, parameters)
    if op == "gte":
        return left >= right
    if op == "gt":
        return left > right
    if op == "lte":
        return left <= right
    if op == "lt":
        return left < right
    if op == "eq":
        return left == right
    if op == "add":
        return left + right
    if op == "subtract":
        return left - right
    if op == "multiply":
        return left * right
    if op == "min":
        return min(left, right)
    if op == "max":
        return max(left, right)
    raise ValueError(f"P10_UNKNOWN_AST_OPERATION: {op}")


def complexity(node: Any) -> int:
    if isinstance(node, dict):
        return 1 + sum(complexity(value) for key, value in node.items() if key != "op")
    if isinstance(node, list):
        return sum(complexity(value) for value in node)
    return 0

