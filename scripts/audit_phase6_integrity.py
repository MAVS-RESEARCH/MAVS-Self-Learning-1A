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
    children = list(node.get("children") or []) + [node[key] for key in ("left", "right") if isinstance(node.get(key), dict)]
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
    schema = {**schema, "$id": schema.get("$id", schema_path.as_uri())}
    registry = Registry().with_resource(ast_schema["$id"], Resource.from_contents(ast_schema))
    registry = registry.with_resource((schema_path.parent / "diagnostic_ast.schema.json").as_uri(), Resource.from_contents(ast_schema))
    registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return [error.message for error in Draft202012Validator(schema, registry=registry).iter_errors(instance)]


def plain(value: Any) -> Any:
    if isinstance(value, np.ndarray): return [plain(item) for item in value.tolist()]
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, dict): return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, list): return [plain(item) for item in value]
    return value


def strip_none(value: Any) -> Any:
    if isinstance(value, dict): return {key: strip_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list): return [strip_none(item) for item in value]
    return value


def objective(ast: dict[str, Any], parameters: dict[str, float], bank: pd.DataFrame) -> list[float]:
    output = evaluate(ast, bank, parameters).astype(float) >= 0.5
    unsafe = bank["unsafe"].to_numpy(dtype=bool)
    context = bank["context_match"].to_numpy(dtype=float)
    evidence = bank["evidence_available"].to_numpy(dtype=bool)
    active = (context >= float(parameters.get("scope_lower", 0.25))) & (context > float(parameters.get("anti_scope_upper", 0.10))) & evidence
    return [float(np.mean(active & ~output & unsafe)), float(np.mean(active & output & ~unsafe)), float(np.mean(~active)), float(np.mean(active & (context < 0.2))), float(np.var(output.astype(float))) * 0.01, float(complexity(ast))]


def operation_delta_passes(candidate: dict[str, Any]) -> bool:
    operation, payload = candidate["lineage"]["operation"], candidate["operation_payload"]
    if operation == "recalibrate": return canonical(payload["parent_expression_ast"]) == canonical(candidate["expression_ast"]) and payload["parent_parameters"] != candidate["parameters"] and bool(payload["fit_trace"]) and payload["protected_gain"] > 0
    if operation == "split": return len(payload["children"]) >= 2 and len({stable(canonical(child["expression_ast"])) for child in payload["children"]}) >= 2 and len(payload["separated_regimes"]) >= 2
    if operation == "merge": return len(payload["parent_programs"]) >= 2 and payload["redundancy_after"] < payload["redundancy_before"] and payload["protected_error_after"] <= payload["protected_error_before"]
    if operation == "add":
        parent = set(_feature_names(payload["parent_expression_ast"])); current = set(_feature_names(candidate["expression_ast"]))
        return bool(current - parent) and set(payload["new_dependencies"]) == current - parent and bool(payload["witness_id"])
    if operation == "scope_narrow": return (canonical(payload["parent_positive_scope_ast"]) != canonical(candidate["positive_scope_ast"]) or canonical(payload["parent_anti_scope_ast"]) != canonical(candidate["anti_scope_ast"])) and bool(payload["deactivated_neighbor_case_ids"]) and bool(payload["retained_case_ids"])
    if operation == "scope_expand": return canonical(payload["parent_positive_scope_ast"]) != canonical(candidate["positive_scope_ast"]) and bool(payload["new_region_case_ids"]) and set(payload["passed_suites"]) >= {"boundary", "anti_scope", "holdout", "disjoint_analogue"}
    if operation == "evidence_recovery":
        record = payload["acquisition_record"]; return record["status"] == "executed" and bool(record["consumed_feature"]) and bool(record["provenance"]) and record["cost"] >= 0 and record["realized_information_gain"] > 0
    if operation == "policy_interaction": return payload["before_relationship"] != payload["after_relationship"] and payload["after_relationship"]["authority"] in {"observation", "query", "soft", "terminal"} and bool(payload["counterfactual_obligation"])
    if operation == "configuration_specialization": return payload["mapping_before"] != payload["mapping_after"] and payload["mapping_before"]["fallback"] == payload["mapping_after"]["fallback"] and bool(payload["scope_proof_case_ids"])
    if operation == "retire": return payload["runtime_eligibility_before"] is True and payload["runtime_eligibility_after"] is False and set(payload["preserved_artifacts"]) >= {"lineage", "counterexamples", "evidence", "replay", "rollback"}
    return False


def _feature_names(node: dict[str, Any]) -> list[str]:
    names = [str(node["name"])] if node.get("op") == "feature" else []
    for child in node.get("children") or []: names.extend(_feature_names(child))
    for key in ("left", "right"):
        if isinstance(node.get(key), dict): names.extend(_feature_names(node[key]))
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    findings: list[dict[str, Any]] = []
    schema_findings: list[dict[str, Any]] = []
    inventory = pd.read_parquet(root / "reports" / "candidate_inventory.parquet").to_dict(orient="records")
    bank = pd.read_parquet(root / "banks" / "certification_banks.parquet").sort_values(["bank", "case_id"], kind="stable").reset_index(drop=True)
    development = pd.read_parquet(root / "banks" / "development.parquet")
    schema_counts: Counter[str] = Counter()
    compiled_schemas = ["diagnostic_ast", "diagnostic_contract", "structure_search_trace", "parameter_search_trace", "semantic_identity", "behavioral_fingerprint", "perception_extension_witness", "blind_certification_request", "independent_gate_vector", "integrity_finding"]
    for schema_name in compiled_schemas:
        Draft202012Validator.check_schema(read_json(REPO_ROOT / "schemas" / "v04" / f"{schema_name}.schema.json"))
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
        schema_counts["diagnostic_contract"] += 1
        if errors: schema_findings.append({"candidate_id": candidate_id, "schema": "diagnostic_contract", "errors": errors})
        for ast_name in ("expression_ast", "positive_scope_ast", "anti_scope_ast"):
            ast_errors = validate_json(candidate[ast_name], "diagnostic_ast.schema.json")
            schema_counts["diagnostic_ast"] += 1
            if ast_errors: schema_findings.append({"candidate_id": candidate_id, "schema": "diagnostic_ast", "field": ast_name, "errors": ast_errors})
        normalized = {"ast_version": "mavs-diagnostic-ast-v1", "expression_ast": canonical(candidate["expression_ast"]), "parameters": dict(sorted(candidate["parameters"].items())), "positive_scope_ast": canonical(candidate["positive_scope_ast"]), "anti_scope_ast": canonical(candidate["anti_scope_ast"]), "evidence_contract": candidate["evidence_contract"], "influence_contract": candidate["influence_contract"], "counterfactual_contract": candidate["counterfactual_contract"]}
        identity = read_json(directory / "semantic_identity.json")
        identity_errors = validate_json(identity, "semantic_identity.schema.json")
        schema_counts["semantic_identity"] += 1
        if identity_errors: schema_findings.append({"candidate_id": candidate_id, "schema": "semantic_identity", "errors": identity_errors})
        if stable(normalized) != identity["semantic_hash"]: findings.append({"gate": "independent_semantic_hash", "candidate_id": candidate_id})
        output = evaluate(candidate["expression_ast"], bank, candidate["parameters"]).astype(float)
        positive = evaluate(candidate["positive_scope_ast"], bank, candidate["parameters"]).astype(bool)
        anti = evaluate(candidate["anti_scope_ast"], bank, candidate["parameters"]).astype(bool)
        active = positive & ~anti & bank["evidence_available"].to_numpy(dtype=bool)
        lower, upper = float(candidate["influence_contract"]["minimum"]), float(candidate["influence_contract"]["maximum"])
        influence = np.where(active, np.clip(output, lower, upper), 0.0)
        stored = pd.read_parquet(directory / "behavioral_fingerprint.parquet")
        for row_index, row in enumerate(stored.to_dict(orient="records")):
            row_errors = validate_json(plain(row), "behavioral_fingerprint.schema.json")
            schema_counts["behavioral_fingerprint"] += 1
            if row_errors: schema_findings.append({"candidate_id": candidate_id, "row": row_index, "schema": "behavioral_fingerprint", "errors": row_errors})
        checks = [np.allclose(stored["raw_output"], output), np.array_equal(stored["discrete_output"], (output >= 0.5).astype(int)), np.array_equal(stored["positive_scope"], positive), np.array_equal(stored["anti_scope"], anti), np.array_equal(stored["active"], active), np.allclose(stored["terminal_influence"], influence)]
        if not all(checks): findings.append({"gate": "independent_behavioral_fingerprint", "candidate_id": candidate_id})
        structures = pd.read_parquet(directory / "structure_search.parquet")
        parameters = pd.read_parquet(directory / "parameter_search.parquet")
        for row_index, row in enumerate(structures.to_dict(orient="records")):
            row = plain(row); row["expression_ast"] = strip_none(row["expression_ast"]); row_errors = validate_json(row, "structure_search_trace.schema.json")
            schema_counts["structure_search_trace"] += 1
            if row_errors: schema_findings.append({"candidate_id": candidate_id, "row": row_index, "schema": "structure_search_trace", "errors": row_errors})
            if not np.allclose(objective(row["expression_ast"], row["parameters"], development), row["objective_vector"], atol=1e-12, rtol=0.0): findings.append({"gate": "structure_objective_recomputation", "candidate_id": candidate_id, "row": row_index})
        for row_index, row in enumerate(parameters.to_dict(orient="records")):
            row = plain(row); row_errors = validate_json(row, "parameter_search_trace.schema.json")
            schema_counts["parameter_search_trace"] += 1
            if row_errors: schema_findings.append({"candidate_id": candidate_id, "row": row_index, "schema": "parameter_search_trace", "errors": row_errors})
            if not np.allclose(objective(candidate["expression_ast"], row["parameters"], development), row["objective_vector"], atol=1e-12, rtol=0.0): findings.append({"gate": "parameter_objective_recomputation", "candidate_id": candidate_id, "row": row_index})
        if len(structures) < 2 or int(structures["selected"].sum()) != 1: findings.append({"gate": "structure_search_provenance", "candidate_id": candidate_id})
        if len(parameters) < 8 or int(parameters["selected"].sum()) != 1: findings.append({"gate": "parameter_search_provenance", "candidate_id": candidate_id})
        else:
            selected = parameters.loc[parameters["selected"], "parameters"].iloc[0]
            if stable(selected) != stable(candidate["parameters"]): findings.append({"gate": "selected_parameter_provenance", "candidate_id": candidate_id})
        request = read_json(directory / "blind_request.json")
        request_errors = validate_json(request, "blind_certification_request.schema.json")
        schema_counts["blind_certification_request"] += 1
        if request_errors: schema_findings.append({"candidate_id": candidate_id, "schema": "blind_certification_request", "errors": request_errors})
        forbidden = blind_findings(request)
        if forbidden: findings.append({"gate": "blind_allowlist", "candidate_id": candidate_id, "detail": forbidden})
        gate_vector = read_json(directory / "independent_gate_vector.json")
        gate_errors = validate_json(gate_vector, "independent_gate_vector.schema.json")
        schema_counts["independent_gate_vector"] += 1
        if gate_errors: schema_findings.append({"candidate_id": candidate_id, "schema": "independent_gate_vector", "errors": gate_errors})
        trace = pd.read_parquet(directory / "certification_trace.parquet")
        if stable(trace.to_dict(orient="records")) != gate_vector["supporting_trace_hash"]: findings.append({"gate": "gate_trace_hash", "candidate_id": candidate_id})
        if len(gate_vector["gates"]) != 15 or bool(gate_vector["all_passed"]) != all(gate["passed"] for gate in gate_vector["gates"].values()): findings.append({"gate": "gate_vector_recomputation", "candidate_id": candidate_id})
        if float(gate_vector["gates"]["complexity"]["value"]) != float(complexity(candidate["expression_ast"])): findings.append({"gate": "complexity_recomputation", "candidate_id": candidate_id})
        witness = read_json(directory / "perception_extension_witness.json")
        witness_errors = validate_json(witness, "perception_extension_witness.schema.json")
        schema_counts["perception_extension_witness"] += 1
        if witness_errors: schema_findings.append({"candidate_id": candidate_id, "schema": "perception_extension_witness", "errors": witness_errors})
        compliance = read_json(directory / "operation_compliance.json")
        if not compliance.get("passed") or not operation_delta_passes(candidate): findings.append({"gate": "independent_operation_delta", "candidate_id": candidate_id})
        if record["lifecycle"] == "promoted" and not (witness["valid"] and witness["disjoint_reproduction"] and not witness["retained_regression"] and not witness["anti_scope_regression"]): findings.append({"gate": "perception_extension_witness", "candidate_id": candidate_id})
        if record["lifecycle"] == "promoted" and (candidate["integrity_control"] or candidate["certification_control"]): findings.append({"gate": "anti_gaming_promotion", "candidate_id": candidate_id})
    required_reports = ["template_collapse_report.json", "name_label_operation_permutation.json", "hidden_field_taint_report.json", "blind_api_schema_audit.json", "constant_noop_parent_identity_report.json", "gate_distribution_investigation.json", "split_separation_audit.json", "deterministic_replay_report.json"]
    for report_name in required_reports:
        report = read_json(root / "integrity" / report_name)
        if not report.get("passed", False): findings.append({"gate": report_name, "detail": report})
    process_access = read_json(root / "blind_outputs" / "process_access_audit.json")
    if process_access["forbidden_candidate_directories_opened"] or process_access["final_blind_opened"] or process_access["environment_quality_fields_read"] or process_access["imports_learning_synthesis"] or process_access["shared_mutable_state"]:
        findings.append({"gate": "blind_process_access", "detail": process_access})
    random_controls = pd.read_parquet(root / "integrity" / "random_equal_budget_proposal_controls.parquet")
    random_by_operation = random_controls.groupby("operation").size().to_dict()
    if len(random_controls) != 20 or set(random_by_operation.values()) != {2} or set(random_controls["equal_trial_budget"].unique()) != {8}:
        findings.append({"gate": "random_equal_budget_controls", "detail": {"rows": len(random_controls), "by_operation": random_by_operation}})
    pathology = read_json(root / "integrity" / "phase3_template_pathology_fixtures.json")
    if pathology["validates_differentiated_synthesis"] or not pathology["retained_in_phase6_integrity_benchmark"] or pathology["candidate_cards_indexed"] != 120:
        findings.append({"gate": "retained_phase3_pathology_fixtures", "detail": pathology})
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
    schema_counts["integrity_finding"] += len(findings)
    for finding_index, finding in enumerate(findings):
        normalized_finding = {"finding_id": f"P6-AUDIT-{finding_index:04d}", "severity": "error", "gate": str(finding.get("gate", "schema")), "candidate_ids": [finding["candidate_id"]] if finding.get("candidate_id") else [], "reason_code": str(finding.get("gate", "schema_failure")), "evidence": [json.dumps(finding, sort_keys=True, default=str)], "resolved": False}
        finding_errors = validate_json(normalized_finding, "integrity_finding.schema.json")
        if finding_errors: schema_findings.append({"schema": "integrity_finding", "finding": finding_index, "errors": finding_errors})
    schema_report = {"compiled_schemas": compiled_schemas, "validated_candidates": len(inventory), "validated_records_by_schema": dict(schema_counts), "total_validated_records": sum(schema_counts.values()), "findings": schema_findings, "passed": not schema_findings}
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
