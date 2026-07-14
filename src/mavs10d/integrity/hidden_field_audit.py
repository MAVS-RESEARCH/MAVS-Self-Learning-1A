"""Recursive hidden-field and evaluator-sentinel taint audit."""

from __future__ import annotations

from typing import Any, Mapping


def find_taint(value: Any, sentinel: str, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized.startswith("hidden_") or normalized in {"generator_truth", "oracle_label", "expected_class", "desired_promotion"}:
                findings.append(f"{path}.{key}")
            findings.extend(find_taint(item, sentinel, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_taint(item, sentinel, f"{path}[{index}]"))
    elif sentinel in str(value):
        findings.append(path)
    return findings


def audit_payloads(payloads: dict[str, Any], sentinel: str) -> dict[str, Any]:
    findings = {name: find_taint(payload, sentinel) for name, payload in payloads.items()}
    nonempty = {name: paths for name, paths in findings.items() if paths}
    return {"sentinel": sentinel, "payload_count": len(payloads), "findings": nonempty, "taint_count": sum(len(paths) for paths in nonempty.values()), "passed": not nonempty}

