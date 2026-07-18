"""Fail-closed claim generation from audited gates only."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, file_sha256, read_json, result_root, write_json


STATUS_ORDER = {"falsified": 0, "unsupported": 1, "partially_supported": 2, "supported": 3}


def derive_status(required: list[str], gates: dict[str, bool], forced_status: str | None = None, integrity_gates: list[str] | None = None) -> str:
    if forced_status:
        return forced_status
    integrity_gates = integrity_gates or []
    if any(not gates.get(gate, False) for gate in integrity_gates):
        return "falsified"
    available = [gate for gate in required if gate in gates]
    if len(available) != len(required):
        return "unsupported"
    passed = sum(bool(gates[gate]) for gate in required)
    if passed == len(required):
        return "supported"
    if passed:
        return "partially_supported"
    return "falsified"


def generate_claims(gate_audit_path: str | None = None) -> dict[str, Any]:
    root = result_root()
    audit_path = root / "reports" / (gate_audit_path or "preclaim_gate_audit.json")
    audit = read_json(audit_path)
    gates = {key: bool(value) for key, value in audit["gates"].items()}
    cfg = config()
    p9 = REPO_ROOT / cfg["inputs"]["phase9"]
    blind = pd.read_parquet(p9 / "blind_bank" / "summaries" / "generation_summary.parquet")
    cumulative = blind[blind["condition_id"] == "v04_cumulative"].sort_values("generation")
    exposure = {
        "bank": "blind_bank", "generations": [1, 2, 3],
        "opportunities": int(cumulative["opportunity_count"].sum()),
        "unsafe_exposures": int(cumulative["unsafe_exposure_count"].sum()),
        "safe_exposures": int(cumulative["safe_exposure_count"].sum()),
        "uar": cumulative["uar"].tolist(), "frr": cumulative["frr"].tolist(),
        "residual_escalation": cumulative["residual_escalation_rate"].tolist(),
        "uar_one_sided_upper": cumulative["uar_one_sided_upper"].tolist(),
        "frr_one_sided_upper": cumulative["frr_one_sided_upper"].tolist(),
    }
    source_hashes = {
        "phase6_audit": file_sha256(REPO_ROOT / cfg["inputs"]["phase6"] / "reports" / "phase6_audit.json"),
        "phase7_audit": file_sha256(REPO_ROOT / cfg["inputs"]["phase7"] / "reports" / "phase7_audit.json"),
        "phase8_audit": file_sha256(REPO_ROOT / cfg["inputs"]["phase8"] / "reports" / "phase8_audit.json"),
        "phase9_audit": file_sha256(REPO_ROOT / cfg["inputs"]["phase9"] / "phase9_audit.json"),
        "phase10_preclaim_audit": file_sha256(audit_path),
    }
    registry = cfg["claim_gate_registry"]
    definitions = [
        ("executable_diagnostic_synthesis", "Executable differentiated diagnostic synthesis is supported for the audited Phase 6 grammar, operations, banks, and candidate lifecycle.", "Phase 6 candidate population and frozen certification banks"),
        ("perception_closure_runtime", "Perception Closure is supported on the declared finite Phase 7 and Phase 9 covered classes, subject to the recorded evidence and budget assumptions.", "Declared finite covered classes only"),
        ("three_generation_blind_transfer", "The audited blind three-generation bank supports cumulative perception-closure learning with protected errors and scope leakage remaining zero and burden improving relative to fresh learning.", "Sealed Phase 9 Track B; not general-domain deployment"),
        ("universal_zero_error", "No universal zero-error or zero-escalation claim is permitted outside the certified finite covered class.", "Outside the declared covered class"),
        ("deployment_readiness", "No production deployment-readiness claim is supported by these research banks.", "External operational environments"),
    ]
    claims: list[dict[str, Any]] = []
    integrity = ["input_integrity", "candidate_reconciliation", "certification_match", "permutation_invariance", "hidden_taint_zero", "result_isolation"]
    for claim_id, language, scope in definitions:
        rule = registry[claim_id if claim_id in registry else {"executable_diagnostic_synthesis": "executable_synthesis", "perception_closure_runtime": "perception_closure_runtime", "three_generation_blind_transfer": "three_generation_blind_transfer"}[claim_id]]
        required = list(rule["required"])
        status = derive_status(required, gates, rule.get("forced_status"), integrity if claim_id in {"executable_diagnostic_synthesis", "perception_closure_runtime", "three_generation_blind_transfer"} else [])
        claims.append({
            "claim_id": claim_id, "status": status, "required_gates": required,
            "gate_results": {gate: gates.get(gate, False) for gate in required},
            "supporting_or_failing_gates": [gate for gate in required if gates.get(gate, False)] if status == "supported" else [gate for gate in required if not gates.get(gate, False)],
            "exposure_counts_and_bounds": exposure if claim_id == "three_generation_blind_transfer" else {},
            "scope": scope, "artifact_hashes": source_hashes,
            "maximum_permitted_language": language,
        })
    ledger = {"schema_version": "1.0.0", "generated": True, "generator": "mavs10d.audit_v04.claims", "source_audit_sha256": file_sha256(audit_path), "claims": claims}
    write_json(root / "claims" / "claim_ledger.json", ledger)
    source_map = {"schema_version": "1.0.0", "claims": {claim["claim_id"]: {"status": claim["status"], "artifact_hashes": claim["artifact_hashes"], "gates": claim["gate_results"]} for claim in claims}}
    write_json(root / "claims" / "claim_source_map.json", source_map)
    lines = ["# MAVS Self-Learning Version 0.4 Audited Claims", "", "This file is generated from the Phase 10 claim ledger. Handwritten elevation is prohibited.", ""]
    for claim in claims:
        lines.extend([f"## {claim['claim_id']}", "", f"Status: `{claim['status']}`", "", claim["maximum_permitted_language"], "", f"Scope: {claim['scope']}", ""])
    (root / "claims" / "CLAIMS.md").write_text("\n".join(lines), encoding="utf-8")
    return {"claim_count": len(claims), "statuses": {claim["claim_id"]: claim["status"] for claim in claims}, "provisional_count": sum(claim["status"] == "provisional" for claim in claims), "status": "PASS"}

