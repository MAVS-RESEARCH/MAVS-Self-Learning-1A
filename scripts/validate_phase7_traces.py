"""Validate Phase 7 schemas, action semantics, scope, counters, and hash links."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator

from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import assert_runtime_blindness
from mavs10d.resolution.closure import validate_residual_partition
from phase7_common import REPO_ROOT, read_json, read_jsonl, run_root, write_json


def decoded(row: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    result = dict(row)
    for field in fields & set(result):
        if isinstance(result[field], str):
            result[field] = json.loads(result[field])
    return result


def schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(read_json(REPO_ROOT / "schemas" / "v04" / name))


def errors(validator: Draft202012Validator, payload: dict[str, Any], identity: str) -> list[dict[str, Any]]:
    return [{"identity": identity, "path": ".".join(map(str, item.path)), "message": item.message} for item in validator.iter_errors(payload)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    findings: list[dict[str, Any]] = []
    cases = read_jsonl(root / "manifests" / "runtime_cases.jsonl")
    case_map = {item["case_id"]: item for item in cases}
    for case in cases:
        try:
            assert_runtime_blindness(case)
        except ValueError as error:
            findings.append({"gate": "runtime_blindness", "case_id": case["case_id"], "detail": str(error)})

    action_validator = schema("perception_action.schema.json")
    hypothesis_validator = schema("hypothesis.schema.json")
    ambiguity_validator = schema("ambiguity_state.schema.json")
    program_validator = schema("active_case_program.schema.json")
    certificate_validator = schema("local_closure_certificate.schema.json")
    trace_validator = schema("perception_trace.schema.json")
    residual_validator = schema("residual_escalation.schema.json")
    query_validator = schema("query_record.schema.json")
    persistent_validator = schema("persistent_knowledge.schema.json")
    schema_findings: list[dict[str, Any]] = []
    for case in cases:
        for action in case["actions"]:
            schema_findings.extend(errors(action_validator, action, action["action_id"]))
        for hypothesis in case["hypotheses"]:
            schema_findings.extend(errors(hypothesis_validator, hypothesis, hypothesis["hypothesis_id"]))
    for path in sorted((root / "hypotheses").glob("*.json")):
        payload = read_json(path)
        schema_findings.extend(errors(ambiguity_validator, payload["initial_ambiguity_state"], f"{path.name}:initial_ambiguity_state"))
    for path in sorted((root / "programs").glob("*.json")):
        schema_findings.extend(errors(program_validator, read_json(path), path.name))
    certificates = {}
    for path in sorted((root / "certificates" / "local").glob("*.json")):
        payload = read_json(path)
        certificates[payload["certificate_id"]] = payload
        schema_findings.extend(errors(certificate_validator, payload, path.name))
        if not payload["all_passed"] or not all(payload["obligations"].values()):
            findings.append({"gate": "closure_obligations", "certificate_id": payload["certificate_id"]})

    trace_frame = pd.read_parquet(root / "traces" / "perception_traces.parquet")
    traces = trace_frame.to_dict(orient="records")
    for trace in traces:
        schema_findings.extend(errors(trace_validator, trace, f"{trace['case_id']}:{trace['library_size']}"))
        stored_hash = trace.pop("trace_hash")
        recomputed = stable_hash(trace)
        trace["trace_hash"] = stored_hash
        if recomputed != stored_hash:
            findings.append({"gate": "trace_hash", "case_id": trace["case_id"], "library_size": trace["library_size"]})
        if trace["terminal_action"] in {"ACCEPT", "REJECT"} and trace["terminal_authorization"] not in certificates:
            findings.append({"gate": "terminal_authorization", "case_id": trace["case_id"]})
        if trace["terminal_action"] == "ESCALATE" and trace["external_escalation_count"] != 1:
            findings.append({"gate": "external_escalation_counter", "case_id": trace["case_id"]})
        if trace["terminal_action"] != "ESCALATE" and trace["external_escalation_count"] != 0:
            findings.append({"gate": "external_escalation_alias", "case_id": trace["case_id"]})

    query_fields = {"updated_fields"}
    query_rows = [decoded(item, query_fields) for item in pd.read_parquet(root / "traces" / "queries_and_probes.parquet").to_dict(orient="records")]
    for row in query_rows:
        schema_payload = {key: value for key, value in row.items() if key != "library_size"}
        schema_findings.extend(errors(query_validator, schema_payload, f"{row['case_id']}:{row['library_size']}:{row['round_index']}"))
    terminal_rows = pd.read_parquet(root / "traces" / "terminal_decisions.parquet").to_dict(orient="records")
    grouped_actions = Counter((item["case_id"], int(item["library_size"]), item["action_type"]) for item in query_rows)
    for terminal in terminal_rows:
        key = (terminal["case_id"], int(terminal["library_size"]))
        expected = {
            "QUERY": int(terminal["query_count"]),
            "PROBE": int(terminal["probe_count"]),
            "DIAGNOSTIC_PROGRAM": int(terminal["program_count"]),
        }
        for action_type, count in expected.items():
            if grouped_actions[(key[0], key[1], action_type)] != count:
                findings.append({"gate": "action_counter_separation", "case_id": key[0], "library_size": key[1], "action_type": action_type})

    residual_fields = {"untried_actions", "invalid_actions", "budget_ledger", "no_positive_path_proof"}
    escalation_rows = [decoded(item, residual_fields) for item in pd.read_parquet(root / "traces" / "escalations.parquet").to_dict(orient="records")]
    for row in escalation_rows:
        schema_payload = {key: value for key, value in row.items() if key != "library_size"}
        schema_findings.extend(errors(residual_validator, schema_payload, f"{row['case_id']}:{row['library_size']}"))
        if not validate_residual_partition(row):
            findings.append({"gate": "residual_partition", "case_id": row["case_id"]})
        stored_hash = row["record_hash"]
        content = {key: value for key, value in schema_payload.items() if key != "record_hash"}
        if stable_hash(content) != stored_hash:
            findings.append({"gate": "residual_hash", "case_id": row["case_id"]})

    round_fields = {"generated_action_ids", "action_findings", "budget_ledger"}
    rounds = [decoded(item, round_fields) for item in pd.read_parquet(root / "traces" / "perception_rounds.parquet").to_dict(orient="records")]
    scope_violations = []
    typed_violations = []
    interaction_violations = []
    interaction_payloads = read_json(root / "integrity" / "interaction_certificates.json")["certificates"]
    interaction_certificates = {item["certificate_id"]: item for item in interaction_payloads}
    for row in rounds:
        case = case_map[row["case_id"]]
        selected = next(item for item in case["actions"] if item["action_id"] == row["selected_action_id"])
        if not selected["positive_scope"] or selected["anti_scope"]:
            scope_violations.append({"case_id": row["case_id"], "action_id": selected["action_id"]})
        if selected["channel"] in {"availability", "scope", "novelty", "conflict"} and selected.get("requested_action") in {"ACCEPT", "REJECT"}:
            typed_violations.append({"case_id": row["case_id"], "action_id": selected["action_id"]})
        if selected["interaction_status"] in {"untested", "prohibited"} and selected["action_type"] == "DIAGNOSTIC_PROGRAM":
            interaction_violations.append({"case_id": row["case_id"], "action_id": selected["action_id"]})
        for certificate_id in selected.get("interaction_certificate_ids", []):
            certificate = interaction_certificates.get(certificate_id)
            if not certificate or certificate["status"] != "certified" or not certificate["counterfactual_passed"] or not certificate["nonredundant"] or float(certificate["protected_regression"]) != 0.0:
                interaction_violations.append({"case_id": row["case_id"], "action_id": selected["action_id"], "certificate_id": certificate_id})
        if row["additive_severity_used"]:
            typed_violations.append({"case_id": row["case_id"], "gate": "additive_severity"})
        required_round_fields = {"surviving_hypothesis_ids", "hypothesis_evidence_assessment", "typed_influence_graph", "interaction_certificate_ids", "positive_scope", "anti_scope", "result_available", "result_trusted", "result_provenance_valid", "library_search"}
        if not required_round_fields <= set(row):
            findings.append({"gate": "round_trace_completeness", "case_id": row["case_id"], "missing": sorted(required_round_fields - set(row))})

    findings.extend({"gate": "scope_activation", **item} for item in scope_violations)
    findings.extend({"gate": "typed_channel", **item} for item in typed_violations)
    findings.extend({"gate": "interaction_safety", **item} for item in interaction_violations)
    persistent_records = [decoded(item, {"positive_scope", "anti_scope", "lineage", "blind_certification"}) for item in pd.read_parquet(root / "persistence" / "consolidation_actions.parquet").to_dict(orient="records")]
    for record in persistent_records:
        schema_findings.extend(errors(persistent_validator, record, record["knowledge_id"]))
    findings.extend({"gate": "schema", **item} for item in schema_findings)
    write_json(root / "integrity" / "scope_activation.json", {"checked_rounds": len(rounds), "violations": scope_violations, "passed": not scope_violations})
    write_json(root / "integrity" / "typed_channels.json", {"checked_rounds": len(rounds), "hard_veto_violations": typed_violations, "additive_severity_used": False, "passed": not typed_violations})
    write_json(root / "integrity" / "interaction_safety.json", {"checked_rounds": len(rounds), "violations": interaction_violations, "passed": not interaction_violations})
    dependency = read_json(root / "manifests" / "phase6_dependency.json")
    promoted_ids = set(dependency["promoted_candidate_ids"])
    used_primitives = {primitive for case in cases for action in case["actions"] for primitive in action.get("primitive_ids", [])}
    unknown_primitives = sorted(used_primitives - promoted_ids)
    runtime_created = [action for case in cases for action in case["actions"] if action.get("runtime_created", False)]
    uncertified_runtime = [action["action_id"] for action in runtime_created if not action.get("phase6_integrity_passed", False)]
    continuity_passed = dependency["passed"] and not unknown_primitives and not uncertified_runtime
    write_json(root / "integrity" / "phase6_continuity.json", {"dependency": dependency, "used_phase6_primitives": sorted(used_primitives), "unknown_primitives": unknown_primitives, "runtime_created_candidate_count": len(runtime_created), "uncertified_runtime_candidate_count": len(uncertified_runtime), "passed": continuity_passed})
    if not continuity_passed:
        findings.append({"gate": "phase6_continuity", "unknown_primitives": unknown_primitives, "uncertified_runtime": uncertified_runtime})
    report = {
        "case_count": len(cases), "execution_count": len(traces), "round_count": len(rounds),
        "query_probe_program_count": len(query_rows), "certificate_count": len(certificates),
        "escalation_count": len(escalation_rows), "schema_findings": len(schema_findings),
        "finding_count": len(findings), "findings": findings, "passed": not findings,
    }
    write_json(root / "integrity" / "trace_validation.json", report)
    if findings:
        raise RuntimeError(f"Phase 7 trace validation failed with {len(findings)} finding(s).")
    # console.log: phase7.trace_validation.complete
    print(f'{{"event":"phase7.trace_validation.complete","executions":{len(traces)},"findings":0}}')


if __name__ == "__main__":
    main()
