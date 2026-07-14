"""Independent fail-closed Phase 6 audit with no synthesis/certification imports."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from phase6_common import REPO_ROOT, file_manifest, read_json, run_root, write_json


REQUIRED_CANDIDATE_FILES = {
    "candidate.json", "structure_search.parquet", "parameter_search.parquet", "semantic_identity.json",
    "behavioral_fingerprint.parquet", "operation_compliance.json", "perception_extension_witness.json",
    "blind_request.json", "independent_gate_vector.json", "certification_trace.parquet",
}
FORBIDDEN_BLIND = {"candidate_id", "candidate_name", "operation", "expected_outcome", "expected_class", "desired_promotion", "candidate_quality", "generator_truth", "curriculum", "generation", "hidden_world", "oracle_label", "target_promotion", "integrity_control", "certification_control"}


def stable(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical(node: dict[str, Any]) -> dict[str, Any]:
    operation = node["op"]
    if operation in {"feature", "parameter", "constant"}:
        return {key: node[key] for key in sorted(node)}
    if operation in {"and", "or", "add", "mul", "min", "max", "not", "sub", "clip"}:
        children = [canonical(child) for child in node.get("children", [])]
        if operation in {"and", "or", "add", "mul", "min", "max"}:
            flattened = []
            for child in children:
                flattened.extend(child.get("children", [])) if child.get("op") == operation else flattened.append(child)
            children = sorted(flattened, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        result = {key: node[key] for key in sorted(node) if key != "children"}
        result["children"] = children
        return result
    return {"op": operation, "left": canonical(node["left"]), "right": canonical(node["right"])}


def evaluate(node: dict[str, Any], bank: pd.DataFrame, parameters: dict[str, float]) -> np.ndarray:
    operation = node["op"]
    if operation == "feature": return bank[node["name"]].to_numpy(dtype=float)
    if operation == "parameter": return np.full(len(bank), float(parameters[node["name"]]))
    if operation == "constant": return np.full(len(bank), float(node["value"]))
    if operation in {"gte", "gt", "lte", "lt", "eq"}:
        left, right = evaluate(node["left"], bank, parameters), evaluate(node["right"], bank, parameters)
        return {"gte": np.greater_equal, "gt": np.greater, "lte": np.less_equal, "lt": np.less, "eq": np.equal}[operation](left, right)
    children = [evaluate(child, bank, parameters) for child in node.get("children", [])]
    if operation == "and": return np.logical_and.reduce([child.astype(bool) for child in children])
    if operation == "or": return np.logical_or.reduce([child.astype(bool) for child in children])
    if operation == "not": return ~children[0].astype(bool)
    if operation == "add": return np.add.reduce(children)
    if operation == "sub": return children[0] - children[1]
    if operation == "mul": return np.multiply.reduce(children)
    if operation == "min": return np.minimum.reduce(children)
    if operation == "max": return np.maximum.reduce(children)
    if operation == "clip": return np.clip(children[0], float(node.get("lower", 0.0)), float(node.get("upper", 1.0)))
    raise ValueError(operation)


def complexity(node: dict[str, Any]) -> int:
    children = list(node.get("children", [])) + [node[key] for key in ("left", "right") if isinstance(node.get(key), dict)]
    return 1 + sum(complexity(child) for child in children)


def blind_findings(value: Any, path: str = "$") -> list[str]:
    findings = []
    if isinstance(value, dict):
        for key, item in value.items():
            lower = key.lower()
            if lower in FORBIDDEN_BLIND or lower.startswith(("hidden_", "expected_")): findings.append(f"{path}.{key}")
            findings.extend(blind_findings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value): findings.extend(blind_findings(item, f"{path}[{index}]"))
    elif "phase6_evaluator_only_sentinel" in str(value).lower(): findings.append(path)
    return findings


def validate_json(instance: Any, schema_name: str) -> list[str]:
    schema_path = REPO_ROOT / "schemas" / "v04" / schema_name
    schema = read_json(schema_path)
    ast_schema = read_json(schema_path.parent / "diagnostic_ast.schema.json")
    registry = Registry().with_resource(ast_schema["$id"], Resource.from_contents(ast_schema))
    registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return [error.message for error in Draft202012Validator(schema, registry=registry).iter_errors(instance)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    findings: list[dict[str, Any]] = []
    schema_findings: list[dict[str, Any]] = []
    inventory = pd.read_parquet(root / "reports" / "candidate_inventory.parquet").to_dict(orient="records")
    bank = pd.read_parquet(root / "banks" / "certification_banks.parquet").sort_values(["bank", "case_id"], kind="stable").reset_index(drop=True)
    if len(inventory) != 40: findings.append({"gate": "candidate_count", "detail": len(inventory)})
    lifecycle = Counter(record["lifecycle"] for record in inventory)
    if lifecycle != Counter({"promoted": 20, "integrity_rejected": 10, "certification_rejected": 10}): findings.append({"gate": "lifecycle_reconciliation", "detail": dict(lifecycle)})
    operation_promotions = Counter(record["operation"] for record in inventory if record["lifecycle"] == "promoted")
    if len(operation_promotions) != 10 or set(operation_promotions.values()) != {2}: findings.append({"gate": "operation_strata", "detail": dict(operation_promotions)})
    for record in inventory:
        candidate_id = record["candidate_id"]
        directory = root / "candidates" / candidate_id
        actual_files = {path.name for path in directory.iterdir() if path.is_file()}
        if actual_files != REQUIRED_CANDIDATE_FILES: findings.append({"gate": "candidate_artifact_contract", "candidate_id": candidate_id, "detail": sorted(actual_files ^ REQUIRED_CANDIDATE_FILES)})
        candidate = read_json(directory / "candidate.json")
        errors = validate_json(candidate, "diagnostic_contract.schema.json")
        if errors: schema_findings.append({"candidate_id": candidate_id, "schema": "diagnostic_contract", "errors": errors})
        normalized = {"ast_version": "mavs-diagnostic-ast-v1", "expression_ast": canonical(candidate["expression_ast"]), "parameters": dict(sorted(candidate["parameters"].items())), "positive_scope_ast": canonical(candidate["positive_scope_ast"]), "anti_scope_ast": canonical(candidate["anti_scope_ast"]), "evidence_contract": candidate["evidence_contract"], "influence_contract": candidate["influence_contract"], "counterfactual_contract": candidate["counterfactual_contract"]}
        identity = read_json(directory / "semantic_identity.json")
        if stable(normalized) != identity["semantic_hash"]: findings.append({"gate": "independent_semantic_hash", "candidate_id": candidate_id})
        output = evaluate(candidate["expression_ast"], bank, candidate["parameters"]).astype(float)
        positive = evaluate(candidate["positive_scope_ast"], bank, candidate["parameters"]).astype(bool)
        anti = evaluate(candidate["anti_scope_ast"], bank, candidate["parameters"]).astype(bool)
        active = positive & ~anti & bank["evidence_available"].to_numpy(dtype=bool)
        lower, upper = float(candidate["influence_contract"]["minimum"]), float(candidate["influence_contract"]["maximum"])
        influence = np.where(active, np.clip(output, lower, upper), 0.0)
        stored = pd.read_parquet(directory / "behavioral_fingerprint.parquet")
        checks = [np.allclose(stored["raw_output"], output), np.array_equal(stored["discrete_output"], (output >= 0.5).astype(int)), np.array_equal(stored["positive_scope"], positive), np.array_equal(stored["anti_scope"], anti), np.array_equal(stored["active"], active), np.allclose(stored["terminal_influence"], influence)]
        if not all(checks): findings.append({"gate": "independent_behavioral_fingerprint", "candidate_id": candidate_id})
        structures = pd.read_parquet(directory / "structure_search.parquet")
        parameters = pd.read_parquet(directory / "parameter_search.parquet")
        if len(structures) < 2 or int(structures["selected"].sum()) != 1: findings.append({"gate": "structure_search_provenance", "candidate_id": candidate_id})
        if len(parameters) < 8 or int(parameters["selected"].sum()) != 1: findings.append({"gate": "parameter_search_provenance", "candidate_id": candidate_id})
        else:
            selected = parameters.loc[parameters["selected"], "parameters"].iloc[0]
            if stable(selected) != stable(candidate["parameters"]): findings.append({"gate": "selected_parameter_provenance", "candidate_id": candidate_id})
        request = read_json(directory / "blind_request.json")
        forbidden = blind_findings(request)
        if forbidden: findings.append({"gate": "blind_allowlist", "candidate_id": candidate_id, "detail": forbidden})
        gate_vector = read_json(directory / "independent_gate_vector.json")
        trace = pd.read_parquet(directory / "certification_trace.parquet")
        if stable(trace.to_dict(orient="records")) != gate_vector["supporting_trace_hash"]: findings.append({"gate": "gate_trace_hash", "candidate_id": candidate_id})
        if len(gate_vector["gates"]) != 15 or bool(gate_vector["all_passed"]) != all(gate["passed"] for gate in gate_vector["gates"].values()): findings.append({"gate": "gate_vector_recomputation", "candidate_id": candidate_id})
        if float(gate_vector["gates"]["complexity"]["value"]) != float(complexity(candidate["expression_ast"])): findings.append({"gate": "complexity_recomputation", "candidate_id": candidate_id})
        witness = read_json(directory / "perception_extension_witness.json")
        if record["lifecycle"] == "promoted" and not (witness["valid"] and witness["disjoint_reproduction"] and not witness["retained_regression"] and not witness["anti_scope_regression"]): findings.append({"gate": "perception_extension_witness", "candidate_id": candidate_id})
        if record["lifecycle"] == "promoted" and (candidate["integrity_control"] or candidate["certification_control"]): findings.append({"gate": "anti_gaming_promotion", "candidate_id": candidate_id})
    required_reports = ["template_collapse_report.json", "name_label_operation_permutation.json", "hidden_field_taint_report.json", "blind_api_schema_audit.json", "constant_noop_parent_identity_report.json", "gate_distribution_investigation.json", "split_separation_audit.json", "deterministic_replay_report.json"]
    for report_name in required_reports:
        report = read_json(root / "integrity" / report_name)
        if not report.get("passed", False): findings.append({"gate": report_name, "detail": report})
    for manifest_path in sorted((REPO_ROOT / "results" / "legacy").glob("*/legacy_manifest.json")):
        manifest = read_json(manifest_path)
        for entry in manifest["files"]:
            path = REPO_ROOT / entry["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if digest != entry["sha256"]: findings.append({"gate": "legacy_immutability", "detail": entry["path"]})
    console_entries = []
    for path in sorted(list((REPO_ROOT / "scripts").glob("*phase6*")) + [REPO_ROOT / "scripts" / "index_legacy_results.py"]):
        if not path.is_file(): continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if line.lstrip().startswith(("print", "console.log")):
                preceding = lines[number - 2].strip() if number >= 2 else ""
                console_entries.append({"file": path.relative_to(REPO_ROOT).as_posix(), "line": number, "comment_line": number - 1, "comment": preceding, "statement": line.strip()})
                if not preceding.startswith(("# console.log:", "// console.log:")): findings.append({"gate": "console_comment_adjacency", "detail": console_entries[-1]})
    schema_report = {"validated_candidates": len(inventory), "findings": schema_findings, "passed": not schema_findings}
    write_json(root / "integrity" / "schema_validation_report.json", schema_report)
    write_json(root / "reports" / "console_log_registry.json", {"entry_count": len(console_entries), "entries": console_entries, "passed": not any(item["gate"] == "console_comment_adjacency" for item in findings)})
    report = {"schema_version": "1.0.0", "run_id": args.run_id, "auditor_independence": {"imports_production_synthesis": False, "imports_production_certification": False, "independent_ast_evaluator": True, "independent_hashing": True}, "candidate_count": len(inventory), "lifecycle_counts": dict(lifecycle), "operation_promotions": dict(operation_promotions), "finding_count": len(findings) + len(schema_findings), "findings": findings + schema_findings, "status": "PASS" if not findings and not schema_findings else "FAIL", "artifact_manifest": file_manifest(root)}
    write_json(root / "reports" / "phase6_audit.json", report)
    audit_md = ["# Independent Phase 6 Audit", "", f"Status: **{report['status']}**", "", f"Candidates enumerated: {len(inventory)}", "", f"Findings: {report['finding_count']}", ""]
    (root / "reports" / "phase6_audit.md").write_text("\n".join(audit_md), encoding="utf-8")
    if report["status"] == "PASS":
        metrics = read_json(root / "reports" / "lifecycle_metrics.json")
        claims = ["# Phase 6 Claims", "", "Claim scope: executable diagnostic synthesis and anti-gaming integrity only.", "", f"- Independent audit: PASS with zero findings across {len(inventory)} candidates.", f"- Lifecycle: {metrics['promoted']} promoted, {metrics['integrity_rejected']} integrity rejected, {metrics['certification_rejected']} certification rejected, {metrics['quarantined']} quarantined.", "- Every promoted candidate has executable contracts, complete search provenance, an independently certified disjoint perception-extension witness, and deterministic replay evidence.", "- No Phase 7 runtime, multi-generation, or final blind claim is made.", ""]
        (root / "CLAIMS.md").write_text("\n".join(claims), encoding="utf-8")
    else:
        raise RuntimeError(f"Independent Phase 6 audit failed with {report['finding_count']} finding(s).")
    # console.log: phase6.audit.complete
    print(f'{{"event":"phase6.audit.complete","status":"{report["status"]}","findings":{report["finding_count"]}}}')


if __name__ == "__main__":
    main()
