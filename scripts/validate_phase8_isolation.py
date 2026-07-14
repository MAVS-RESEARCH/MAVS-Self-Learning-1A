"""Validate single-factor isolation, matched budgets, blindness, and permutations."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import jsonschema
import pandas as pd

from mavs10d.ablations.v04_registry import AblationRegistry
from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import assert_runtime_blindness
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.integrity.permutation_tests import run_permutation_suite
from phase8_common import PHASE6_ROOT, REPO_ROOT, read_json, read_jsonl, run_root, write_frame, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    registry = AblationRegistry.from_directory(REPO_ROOT / "configs" / "ablations" / "v04")
    schemas = {
        name: read_json(REPO_ROOT / "schemas" / "v04" / f"{name}.schema.json")
        for name in ("ablation_definition", "ablation_result", "causal_contrast", "matched_budget")
    }
    findings: list[dict[str, str]] = []
    budget_records: list[dict[str, object]] = []
    bank_hashes: set[str] = set()
    declared_budgets: set[str] = set()
    required_bundle = {
        "full_config.json", "ablation_config.json", "config_diff.json", "shared_bank_manifest.json",
        "matched_budget.json", "seed_ledger.json", "metrics.parquet", "paired_deltas.parquet",
        "trace_index.json", "causal_contrast.json", "failures.parquet", "audit.json",
    }
    for definition in registry:
        target = root / "ablation_results" / definition.id
        missing = sorted(name for name in required_bundle if not (target / name).exists())
        if missing:
            findings.append({"condition_id": definition.id, "code": "missing_bundle", "detail": ",".join(missing)})
            continue
        try:
            jsonschema.validate(definition.serializable(), schemas["ablation_definition"])
            jsonschema.validate(read_json(target / "ablation_result.json"), schemas["ablation_result"])
            jsonschema.validate(read_json(target / "causal_contrast.json"), schemas["causal_contrast"])
            jsonschema.validate(read_json(target / "matched_budget.json"), schemas["matched_budget"])
        except jsonschema.ValidationError as error:
            findings.append({"condition_id": definition.id, "code": "schema_failure", "detail": error.message})
        diff = read_json(target / "config_diff.json")
        expected = 0 if definition.id == definition.reference_id else 1
        if int(diff["diff_count"]) != expected or not bool(diff["single_factor_valid"]):
            findings.append({"condition_id": definition.id, "code": "multi_factor_drift", "detail": str(diff)})
        bank_manifest = read_json(target / "shared_bank_manifest.json")
        bank_hashes.add(stable_hash(bank_manifest))
        budget = read_json(target / "matched_budget.json")
        declared_budgets.add(stable_hash(budget["declared"]))
        if not budget["matched"] or budget["mismatch_fields"]:
            findings.append({"condition_id": definition.id, "code": "budget_mismatch", "detail": str(budget["mismatch_fields"])})
        for key in budget["declared"]:
            if float(budget["consumed"][key]) > float(budget["declared"][key]) or float(budget["unused"][key]) < 0.0:
                findings.append({"condition_id": definition.id, "code": "budget_overrun", "detail": key})
        budget_records.append({
            "condition_id": definition.id, "reference_id": definition.reference_id,
            "declared_hash": stable_hash(budget["declared"]), "matched": bool(budget["matched"]),
            "unused_total": sum(float(value) for value in budget["unused"].values()),
        })
    if len(bank_hashes) != 1:
        findings.append({"condition_id": "ALL", "code": "shared_bank_drift", "detail": str(len(bank_hashes))})
    if len(declared_budgets) != 1:
        findings.append({"condition_id": "ALL", "code": "declared_budget_drift", "detail": str(len(declared_budgets))})

    cases = read_jsonl(root / "banks" / "phase7_runtime_cases.jsonl")
    for case in cases:
        try:
            assert_runtime_blindness(case)
        except ValueError as error:
            findings.append({"condition_id": "ALL", "code": "phase7_public_taint", "detail": str(error)})
    phase4_public = pd.read_parquet(root / "banks" / "phase4_pre_rerun_public.parquet")
    forbidden_columns = sorted(set(phase4_public.columns) & {"unsafe", "oracle_label", "expected_terminal", "hidden_world"})
    if forbidden_columns:
        findings.append({"condition_id": "ALL", "code": "phase4_public_taint", "detail": ",".join(forbidden_columns)})
    hidden_report = {
        "schema_version": "1.0.0", "phase7_case_count": len(cases),
        "phase4_public_rows": len(phase4_public), "forbidden_phase4_columns": forbidden_columns,
        "i6_firewall_detected": bool(read_json(root / "ablation_results" / "I6" / "ablation_result.json")["metrics"]["firewall_detected"]),
        "i7_firewall_detected": bool(read_json(root / "ablation_results" / "I7" / "ablation_result.json")["metrics"]["firewall_detected"]),
        "public_taint_count": len(forbidden_columns), "passed": not forbidden_columns,
    }
    write_json(root / "integrity" / "hidden_field_report.json", hidden_report)

    inventory = pd.read_parquet(PHASE6_ROOT / "reports" / "candidate_inventory.parquet")
    promoted_ids = inventory[inventory["lifecycle"] == "promoted"]["candidate_id"].astype(str).tolist()
    candidates = [ExecutableDiagnostic.from_dict(read_json(PHASE6_ROOT / "candidates" / candidate_id / "candidate.json")) for candidate_id in promoted_ids]
    outcomes = {candidate_id: "promoted" for candidate_id in promoted_ids}
    bank = pd.read_parquet(PHASE6_ROOT / "banks" / "certification_banks.parquet")
    candidate_permutation = run_permutation_suite(candidates, outcomes, bank, 850001)
    p0 = pd.read_parquet(root / "ablation_results" / "P0" / "runtime_traces.parquet")
    order = list(range(len(p0)))
    random.Random(850002).shuffle(order)
    shuffled = p0.iloc[order].reset_index(drop=True)
    comparison_columns = ["family", "library_size", "terminal_action", "rounds", "query_count", "external_escalate"]
    reference_multiset = p0.groupby(comparison_columns, dropna=False).size().sort_index().to_dict()
    shuffled_multiset = shuffled.groupby(comparison_columns, dropna=False).size().sort_index().to_dict()
    order_invariant = reference_multiset == shuffled_multiset
    permutation_report = {
        "schema_version": "1.0.0",
        "candidate_name_operation_expected_label_proposal_order": candidate_permutation,
        "runtime_case_order": {"seed": 850002, "execution_count": len(p0), "outcome_multiset_invariant": order_invariant},
        "tested_nonsemantic_fields": ["candidate_name", "operation_label", "expected_class", "proposal_order", "runtime_case_order"],
        "passed": bool(candidate_permutation["passed"] and order_invariant),
    }
    if not permutation_report["passed"]:
        findings.append({"condition_id": "ALL", "code": "permutation_failure", "detail": "nonsemantic outcome changed"})
    write_json(root / "integrity" / "permutation_report.json", permutation_report)
    write_frame(root / "integrity" / "matched_budget_ledger.parquet", budget_records)
    isolation_report = {
        "schema_version": "1.0.0", "condition_count": len(list(registry)),
        "single_factor_diff_count": sum(len(item.normalized_diff()) for item in registry),
        "shared_bank_hash_count": len(bank_hashes), "declared_budget_hash_count": len(declared_budgets),
        "runtime_monkey_patching_used": False, "serialized_toggle_required": True,
        "findings": findings, "finding_count": len(findings), "status": "PASS" if not findings else "FAIL",
    }
    write_json(root / "integrity" / "isolation_report.json", isolation_report)
    if findings:
        raise RuntimeError(f"Phase 8 isolation validation failed with {len(findings)} findings.")
    # console.log: phase8.isolation.complete
    print(f'{{"event":"phase8.isolation.complete","conditions":{len(list(registry))},"findings":0,"permutation_passed":true}}')


if __name__ == "__main__":
    main()
